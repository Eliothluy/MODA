# AGENTS.md

Compact instructions for AI agents working in the RSLAQ repository.

## Project Layout

This repo contains **two independent sub-projects** that communicate only at runtime via POSIX IPC:

- `ns-3-dev/` — C++ network simulator (standard ns-3 with 5G-LENA). Entrypoint: `scratch/rslaq/rslaq-sim.cc`.
- `ns-o-ran-gym/` — Python Gymnasium RL environment. Entrypoint package: `nsoran`. Build tool: `hatch`.

## Build & Install

### ns-3 (C++)
```bash
cd ns-3-dev
./ns3 configure --enable-examples --enable-tests
./ns3 build rslaq-sim        # incremental
./ns3 build                  # first time / full
./test.py                    # run ns-3 test suite
```

### Python Environment
```bash
cd ns-o-ran-gym
hatch build
pip3 install dist/*.tar.gz
python -m pytest tests/      # run Python tests
```

## Running Simulations

### Standalone (no agent)
```bash
cd ns-3-dev
./ns3 run "scratch/rslaq/rslaq-sim" -- --scenario=normal --simTime=10
./run_all_scenarios.sh       # batch all 5 scenarios
```

### Online DRL Training (Python spawns ns-3)
The Python environment launches ns-3 as a subprocess and synchronizes via POSIX semaphores + CSV files (`rslaq-kpms.txt`, `rslaq_actions_for_ns3.csv`) every 10 ms.

**Single algorithm:**
```bash
cd ns-o-ran-gym
python3 examples/rslaq_train_ddqn.py --scenario normal --ns3_path ../ns-3-dev ...
python3 examples/rslaq_train_sac.py --scenario normal --ns3_path ../ns-3-dev ...
```

**Full benchmark (all scenarios, SAC + DDQN in parallel):**
```bash
cd ns-o-ran-gym
bash examples/run_all_scenarios.sh
```
This script auto-builds ns-3 if the binary is missing.

## Critical Gotchas

- **P_STA double-application**: Both `RslaqEnv` (Python) and `rslaq-sim` (C++) can apply the static/dynamic weight decomposition (`p_final = P_STA + p_opt * 0.5`). If both are enabled, weights are applied twice. The benchmark scripts pass `--apply_p_sta False` to Python so ns-3 owns the math.
- **Action mode mismatch**: `RslaqEnv` supports `action_mode="continuous"` (SAC) and `"discrete"` (DDQN). The training script must match the mode or the agent will send malformed actions.
- **Observation mode**: Use `"paper"` (4x4 matrix) for production runs; `"debug"` is legacy.
- **RNTI mapping**: UEs are mapped to slices by UE ID ranges (eMBB 1-5, URLLC 6-10, MTC 11-20), but actual RNTIs are assigned dynamically by 5G-LENA during RRC setup. Unmapped RNTIs are logged to `rslaq_unmapped_rntis.csv`.
- **Weight renormalization**: Effective weights `p_j` are computed only for slices with active demand (buffer > 0). The last active slice receives the remainder.
- **Uplink is not slice-aware**: Only downlink scheduling implements slice-aware RBG allocation.
- **Topology**: Single gNB only. Multi-cell scenarios require RNTI mapping changes.
- **RBG notching**: When allocating, use `availableRbgIds[logicalIdx]` to get the actual RBG ID, not the raw loop index.

## Debugging

Enable scheduler debug logging:
```bash
NS_LOG="RslaqMacScheduler=level_debug" ./ns3 run "scratch/rslaq/rslaq-sim" -- --scenario=normal
```

Key log markers:
- `Active RNTIs seen`
- `Active UEs per slice`
- `RBG budgets`
- `Slice X: allocated Y/Z RBGs`
- `RNTI X not found in any slice!`

## Scenario Names

| Name | Description |
|------|-------------|
| `low_traffic` | Minimal load |
| `normal` | Balanced traffic |
| `congestion` | Full congestion |
| `stressed` | Different SLA targets |
| `insufficient_resources` | Resource scarcity |

In ns-3 CLI you may pass either the name or the number `1-5`.

## Output Locations

- `ns-3-dev/results_rslaq/` — per-slice CSVs and UE timeseries from standalone runs.
- `ns-o-ran-gym/results/` — training logs and model checkpoints from Python runs.

## References

- `CLAUDE.md` — Detailed architecture, IPC protocol, and scheduler logic.
- `DOCUMENTACAO_RSLAQ_SCHEDULER.md` — Portuguese technical documentation.
