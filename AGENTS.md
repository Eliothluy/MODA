# AGENTS.md - RSLAQ

Quick reference for RSLAQ (Robust SLA-driven O-RAN QoS xApp) implementation in NS-3/5G-LENA.

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `ns-3-dev/` | NS-3.46 with NR module, NORI scheduler |
| `ns-o-ran-gym/` | Python DRL environment (gymnasium) |
| `nori/` | Original NORI source (reference only) |
| `colosseum-near-rt-ric/` | RIC platform (e2term, e2mgr, Redis) |

## Build

```bash
cd /home/eliothluy/Documentos/artigo_jussi/ns-3-dev

# Configure (run once after clean)
./ns3 configure

# Build (parallel)
./ns3 build -j 10
```

## Run Simulation

```bash
cd /home/eliothluy/Documentos/artigo_jussi/ns-3-dev

# Standalone (no DRL)
./ns3 run "scratch/rslaq-simulation-mac-slicing -- --scenario=normal --simTime=4"

# IPC mode (DRL integration, requires simId)
./ns3 run "scratch/rslaq-simulation-mac-slicing -- --simId=test123 --indicationPeriodicity=10 --simTime=3"
```

Scenarios: `low_traffic`, `normal`, `congestion`, `stressed`, `insufficient_resources`

## Python DRL Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -e /home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym
pip install gymnasium posix-ipc numpy pandas typing-extensions==4.12.0
```

## Key Files

| File | Purpose |
|------|---------|
| `ns-3-dev/contrib/nori/model/nr-rl-mac-scheduler-ofdma.cc` | NORI scheduler with slice-aware PRB allocation |
| `ns-3-dev/scratch/rslaq-simulation-mac-slicing.cc` | Main simulation with IPC |
| `ns-o-ran-gym/src/environments/rslaq_env.py` | RSLAQ gym environment |

## Common Issues

- **Build fails on oran-interface**: Module disabled (renamed to `oran-interface.disabled-backup`)
- **IPC timeout**: Ensure simId matches between NS-3 and Python
- **Gym import error**: Use `typing-extensions==4.12.0`

## E2 Integration (Colosseum RIC)

```bash
# Check KPM flow
sg docker -c "docker logs -f e2term 2>&1 | grep -E 'E2|Indication'"

# Check xApp
sg docker -c "docker logs -f sample-xapp-24 2>&1 | grep -E 'ric.*indication'"
```

E2 status: KPM working, RC partial (handover, DRB split), MAC slicing control not implemented.

## Python IPC Protocol

- Semaphores: `/sem_metrics_<simId>`, `/sem_control_<simId>`
- Files: `rslaq-kpms.txt` (NS-3→Python), `rslaq_actions_for_ns3.csv` (Python→NS-3)