# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository implements **RSLAQ** (Robust SLA-driven 6G O-RAN QoS xApp) - a deep reinforcement learning (DRL) system for slice-aware resource allocation in 5G/6G O-RAN networks. The project combines:

- **ns-3-dev**: Network simulator with 5G-LENA (CTTC) modules and custom RSLAQ MAC scheduler
- **ns-O-RAN-Gym**: Gymnasium environment for online reinforcement learning training
- **DRL Agents**: DDQN, SAC, and OPT algorithms for dynamic slice resource allocation

## Architecture

### High-Level Components

1. **ns-3-dev/** - ns-3 network simulator with 5G-LENA
   - `scratch/rslaq/rslaq-mac-scheduler.cc/h` - Custom slice-aware MAC scheduler
   - `scratch/rslaq/rslaq-sim.cc` - Main simulation script with 5 traffic scenarios
   - `contrib/nr/` - 5G-LENA module (CTTC)

2. **ns-O-RAN-Gym/** - Python RL environment
   - `src/nsoran/` - Base environment classes
     - `ns_env.py` - Abstract base class `NsOranEnv`
     - `action_controller.py` - Writes agent actions to shared files
     - `datalake.py` - SQLite wrapper for KPMs (Key Performance Metrics)
   - `src/environments/` - Specific environments
     - `rslaq_env.py` - RSLAQ DRL environment with SLA-based reward function
   - `examples/` - Training scripts for DDQN, SAC, and OPT

### Communication Protocol (IPC)

The system uses **POSIX semaphores** and **CSV files** for online DRL training:

- **Semaphores**: Synchronize between ns-3 (C++) and Python agent
  - `g_semMetricsReady`: Signals when ns-3 has written new KPMs
  - `g_semControl`: Signals when agent has written new actions
- **CSV Files**: Exchange metrics and actions every 10ms (frame duration)
  - `rslaq_actions_for_ns3.csv`: Agent actions read by ns-3
  - `rslaq-kpms.txt`: KPMs written by ns-3

### Slice Scheduler Logic

The `RslaqMacScheduler` implements slice-aware RBG (Resource Block Group) allocation:

- **3 Slices**: eMBB (enhanced Mobile Broadband), URLLC (Ultra-Reliable Low Latency), MTC (Massive Machine Type Communications)
- **Weights**: `ω_j` (configured by operator or DRL agent) → `p_j` (effective weights, renormalized for active slices only)
- **Intra-slice scheduling**: PF (Proportional Fair), RR (Round Robin), or BCQI (Best CQI) per slice
- **RBG allocation**: Budget `B_j = floor(totalRBGs × p_j)` per active slice

### RNTI Mapping

UE RNTIs are assigned dynamically by 5G-LENA during RRC connection setup. The scheduler maps RNTIs to slices via:
- `GetSliceIndexForRnti(uint16_t rnti)` - Returns slice ID for a given RNTI
- UEs are partitioned by ID ranges: eMBB (1-5), URLLC (6-10), MTC (11-20) by default
- Unmapped RNTIs are logged to `rslaq_unmapped_rntis.csv`

## Build Commands

### ns-3 (C++)

```bash
cd ns-3-dev

# Configure with examples and tests enabled
./ns3 configure --enable-examples --enable-tests

# Build specific target (faster for development)
./ns3 build rslaq-sim

# Build everything (first time)
./ns3 build

# Run tests
./test.py
```

### ns-O-RAN-Gym (Python)

```bash
cd ns-o-ran-gym

# Build and install
hatch build
pip3 install dist/*.tar.gz

# Or install from PyPI
pip3 install nsoran

# Run tests
python -m pytest tests/
```

## Running Simulations

### Standalone Simulation (No DRL Agent)

```bash
cd ns-3-dev

# Run single scenario
./ns3 run "scratch/rslaq/rslaq-sim" -- --scenario=normal --simTime=10

# Run all 5 scenarios
./run_all_scenarios.sh
```

### With DRL Agent (Online Training)

```bash
cd ns-o-ran-gym

# Train all algorithms (OPT, DDQN, SAC)
./run_training.sh

# Train single algorithm
python3 examples/rslaq_train_ddqn.py --scenario all --output results --episodes 20 --max_steps 150
```

### Available Scenarios

| Scenario | eMBB | URLLC | MTC | Description |
|----------|------|-------|-----|-------------|
| `low_traffic` | 50 Kbps | 1 Mbps | 2 Mbps | Minimal load |
| `normal` | 70 Mbps | 1 Mbps | 2 Mbps | Balanced traffic |
| `congestion` | 100 Mbps | 1 Mbps | 100 Mbps | Full congestion |
| `stressed` | 100 Mbps | 1 Mbps | 100 Mbps | Different SLA targets |
| `insufficient_resources` | 100 Mbps | 2 Mbps | 100 Mbps | Resource scarcity |

### Simulation Parameters

Key command-line options for `rslaq-sim`:
- `--scenario`: Scenario name or number (1-5)
- `--simTime`: Simulation time in seconds (default: 4.0)
- `--seed`: RNG seed (default: 1)
- `--weights`: Slice weights (default: `0.3333,0.4000,0.2667`)
- `--embbUes`, `--urllcUes`, `--mtcUes`: Number of UEs per slice
- `--tddPattern`: TDD pattern (default: `D|D|D|D|D|D|D|D|D|D`)
- `--periodMs`: KPM collection period in ms (default: 10)

## Output Files

### ns-3 Simulation Results

Located in `ns-3-dev/results_rslaq/`:
- `*_slice_alloc.csv` - Per-slice RBG allocation per scheduling slot
- `*_ue_detail.csv` - Per-UE metrics (throughput, delay, PDR)
- `*_slice.csv` - Aggregated slice-level summary
- `rslaq_stats_timeseries.csv` - Time series throughput per UE

### DRL Training Results

Located in `ns-o-ran-gym/results/`:
- `training.log` - Training progress log
- Model checkpoints for each algorithm

## Key Files

| File | Purpose |
|------|---------|
| `ns-3-dev/scratch/rslaq/rslaq-mac-scheduler.cc` | Slice-aware scheduler implementation |
| `ns-3-dev/scratch/rslaq/rslaq-sim.cc` | Main simulation script |
| `ns-o-ran-gym/src/environments/rslaq_env.py` | RL environment for RSLAQ |
| `ns-o-ran-gym/src/nsoran/ns_env.py` | Base environment class |
| `DOCUMENTACAO_RSLAQ_SCHEDULER.md` | Portuguese technical documentation |

## Important Implementation Notes

1. **RBG Notching**: The scheduler correctly handles the DL notched RBG mask. When allocating, use `availableRbgIds[logicalIdx]` to get the actual RBG ID.

2. **RNTI Assignment**: RNTIs are assigned by 5G-LENA during RRC connection, not sequentially. Always query `ueDev->GetRrc()->GetRnti()` after `AttachToClosestGnb()`.

3. **Weight Renormalization**: Effective weights `p_j` are computed only for slices with active demand (buffer > 0). The last active slice receives the remainder.

4. **Uplink Not Slice-Aware**: Currently only downlink scheduling implements slice-aware allocation.

5. **Single gNB**: Current topology supports only 1 gNB. Multi-cell scenarios require RNTI mapping adaptations.

6. **P_STA Decomposition**: Final resource allocation is `p_final = P_STA + p_opt * 0.5`, where `P_STA` is static (50%) and `p_opt` is from DRL agent (50%).

## Debugging

Enable detailed scheduler logging:

```bash
NS_LOG="RslaqMacScheduler=level_debug" ./ns3 run "scratch/rslaq/rslaq-sim" -- --scenario=normal
```

Key log messages:
- `Active RNTIs seen` - Lists all RNTIs in current slot
- `Active UEs per slice` - Count of active UEs per slice
- `RBG budgets` - Configured and effective weights, RBG budgets
- `Slice X: allocated Y/Z RBGs` - Allocation result per slice
- `RNTI X not found in any slice!` - Warning for unmapped RNTI
