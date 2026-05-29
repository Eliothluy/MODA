# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research workspace for implementing RSLAQ (Robust SLA-driven 6G O-RAN QoS xApp) with deep reinforcement learning. The workspace consists of two coupled projects:

1. **ns-3-dev/** - C++ network simulator with custom 5G-LENA extensions for RSLAQ
2. **ns-o-ran-gym/** - Python Gymnasium package (published as `nsoran`) providing RL environments

The core innovation is online reinforcement learning training where Python spawns the ns-3 simulator, with synchronization via POSIX semaphores and CSV files for KPI/action exchange.

## Architecture

### Synchronous RL Training Pattern

The ns-3/Python interface follows this flow:
1. ns-3 simulation runs for one step (`periodMs`, typically 10ms)
2. KPIs written to `rslaq-kpms.txt` in the simulation output directory
3. Python RL agent signaled via POSIX semaphore
4. Agent computes action based on KPIs
5. Action written to `rslaq_actions_for_ns3.csv`
6. Simulation reads action and continues

### Key Components

**ns-3 Side (`ns-3-dev/scratch/rslaq/`):**
- `rslaq-sim.cc` - Main simulation script, defines 5G topology (remoteHost -> P2P -> PGW -> gNB -> UEs)
- `rslaq-mac-scheduler.cc/h` - Custom slice-aware MAC scheduler that partitions RBG/PRB budget by slice weights

**Python Side (`ns-o-ran-gym/src/environments/`):**
- `rslaq_env.py` - Main Gymnasium environment coordinating the simulation loop
- `rslaq_reward.py` - Reward function implementation with two modes
- `rslaq_kpis.py` - KPI computation and parsing
- `rslaq_action_spaces.py` - Action space definitions (discrete DDQN, continuous SAC)
- `rslaq_predictive.py` - Predictive models for URLLC traffic
- `rslaq_slice_ids.py` - Slice ID mapping utilities

### Slice Configuration

Canonical slice IDs (0-based everywhere current code controls):
- `0 = eMBB` (Enhanced Mobile Broadband)
- `1 = URLLC` (Ultra-Reliable Low Latency Communications)
- `2 = MTC` (Massive Machine-Type Communications)

UEs are assigned to slices by contiguous ID ranges. Each slice has a UDP downlink flow from remoteHost, with destination port used to map FlowMonitor results back to UE and slice.

### 5G Topology

Single-cell topology: `remoteHost -> 100Gbps P2P -> PGW/EPC -> 1 NR gNB -> static NR UEs`

PHY profile: 3.55 GHz, 100 MHz, numerology `mu=1` (30 kHz SCS), 3GPP UMi channel, panel-like gNB antenna, isotropic UE antennas.

### Reward Modes

Two reward modes are implemented in `rslaq_reward.py`:

1. **`reward_mode="paper"`** - Faithful implementation of the RSLAQ paper
   - Weights: `alpha=0.3333, beta=0.4000, gamma=0.2667`
   - `h_1`: normalized average eMBB throughput
   - `h_2`: `exp(-normalized URLLC max buffer)`
   - `h_3`: normalized average MTC throughput
   - Terminal SLA logic: confirmed outage gives negative reward `-sum(slice_weights)`

2. **`reward_mode="resource_efficient"`** - User's resource-optimization contribution
   - Adds shaping on top of paper reward using active demand, PRB allocation match, over/under-allocation, served fraction, and action smoothness

## Build Commands

### ns-3 Simulator (C++)
```bash
cd ns-3-dev
./ns3 configure --enable-examples --enable-tests
./ns3 build rslaq-sim
```

The ns-3 project uses a custom wrapper around CMake with Waf-like API.

### Python Package
```bash
cd ns-o-ran-gym
hatch build
pip3 install dist/*.tar.gz
```

Or install the published version: `pip3 install nsoran`

## Testing

### Python Tests
```bash
cd ns-o-ran-gym
python3 -m pytest tests/test_rslaq_action_spaces.py tests/test_rslaq_slice_ids.py tests/test_rslaq_kpis.py tests/test_rslaq_reward.py
```

Note: `pyproject.toml` does not declare `torch` or `pytest` as dependencies. PyTorch (>=2.2) and pytest must be installed separately for training and some tests.

Avoid `tests/test_check_env.py` and `tests/test_time_ts.py` for local testing as they hardcode `/workspace/` paths.

### ns-3 Tests
```bash
cd ns-3-dev
./test.py
```

## Running Simulations

### Standalone ns-3 Baseline
```bash
cd ns-3-dev
./ns3 run "scratch/rslaq/rslaq-sim --scenario=normal --baselineMode=pure_pf --simTime=5 --outputDir=/tmp/rslaq"
```

### Fast Baseline Matrix
```bash
cd ns-3-dev
SCENARIOS="normal" BASELINE_MODES="pure_pf" SEEDS="1" RUNS="1" SIM_TIME=5 ./run_all_scenarios.sh
```

### RL Training Entry Points
Located in `ns-o-ran-gym/examples/`:
- `rslaq_train_ddqn.py` - DDQN training (discrete action space, 198 actions with scheduler)
- `rslaq_train_sac.py` - SAC training (continuous action space)
- `rslaq_train_predictive_sac.py` - Predictive SAC training

### Controlled Validation Campaign
```bash
cd ns-o-ran-gym
SCENARIOS="normal" SEEDS="1" RUN_BASELINES=0 RUN_DDQN=1 RUN_PAPER_SAC=0 RUN_RESOURCE_EFFICIENT_SAC=0 INTERACTION_STEPS=100 EPISODE_STEPS=100 bash examples/run_controlled_rslaq_validation.sh
```

## Traffic Profiles

Five profiles defined in `InitScenarios()`:
- `low_traffic`
- `normal`
- `congestion`
- `stressed`
- `insufficient_resources`

Each profile defines per-slice UE counts, total downlink rates, and packet sizes.

## Scheduling Algorithms

- `pure_rr`, `pure_pf`, `pure_bcqi` - Native 5G-LENA schedulers
- `slice_*`, `slice_weighted_*`, `psta_equal`, `slice_custom` - Use `RslaqMacScheduler`, which partitions RBG/PRB budget by slice weights and redistributes from inactive slices

## Runtime Contracts

### P_STA Formula
Implemented in Python action conversion: `p_final = static_fraction * weights + (1 - static_fraction) * p_opt`

Default weights: `0.3333, 0.4000, 0.2667`

### Action File Format
`rslaq_actions_for_ns3.csv` columns:
- Column 1: `sliceId`
- Column 2: `dedicatedPRB`
- Column 5: scheduler algorithm (when present)

Header may be present; C++ parser handles both.

## CLI Gotchas

- `run_training.sh` is stale - use current `rslaq_train_*.py` argparse options instead
- Current training scripts disable P_STA with `--no-apply-p-sta` (no `--apply_p_sta False` option)
- DDQN defaults to `action_mode=discrete`, `include_scheduler=True` (198 actions), or 66 actions with scheduler disabled
- SAC defaults to `action_mode=continuous` and `reward_mode=paper`
- Use `--reward_mode resource_efficient` for the resource-efficient reward variant
- `observation_mode=paper` is production path with shape `(4, 4)`; `debug` uses `(3, 5)`

## Output Structure

### Baseline Output
`<outputDir>/results_rslaq_network_only/scenario=<scenario>/mode=<baselineMode>/seed=<seed>_run=<run>/`

Contains: `timeseries.csv`, `slice_alloc.csv`, `summary.csv`, `metadata.json`

Pure baseline modes (`pure_rr`, `pure_pf`, `pure_bcqi`) have header-only `slice_alloc.csv` as `RslaqMacScheduler` is not active.

### Python Training Output
Defaults to `ns-o-ran-gym/results/`
Controlled campaigns: `ns-o-ran-gym/results_controlled/<experiment_line>/<run_tag>/`

## Scientific Context

- The baseline research target is implementing the reward function from the RSLAQ paper inside the ns-3-based simulator (not the original MATLAB simulator)
- Treat `reward_mode="paper"` as the RSLAQ paper-faithful baseline
- Treat `reward_mode="resource_efficient"` as the user's proposed resource-efficiency contribution
- Do not mix metrics or conclusions without specifying which mode produced them