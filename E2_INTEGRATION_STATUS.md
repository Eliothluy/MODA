# E2 Control Test Guide

## Status

### What's Working ✅

| Component | Status | Connection |
|-----------|--------|------------|
| e2term | ✅ Running | 10.0.2.10:36422 |
| e2mgr | ✅ Running | 10.0.2.11 |
| db (Redis) | ✅ Running | 10.0.2.12:6379 |
| sample-xapp-24 | ✅ Running | 10.0.2.24:4200 (TCP) |
| ns-3-dev | ✅ Built | `/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/` |
| oran-interface | ✅ Built | ns-3.46 CMake |
| e2sim-dev | ✅ Installed | `/home/eliothluy/Documentos/artigo_jussi/oran-e2sim/e2sim/` |
| ns-o-ran-ns3-mmwave-oran | ⚠️ Not built | waf/CMake config incomplete |

### E2 Interface Capabilities

**KPM Service Model (E2SM-KPM)** ✅:
- Reports MAC metrics from ns-3 to RIC
- Examples: `macPduUe`, `rlcBufferOccup`, `prbUtilizationDl`

**RC Service Model (E2SM-RC)** ⚠️:
- Receives RIC Control messages
- CURRENT ACTIONS:
  - Action ID 6: DRB split ratio control
  - Action ID 1: Handover control
- MISSING: No MAC slicing/PRB allocation control

## Testing the Integration

### Option 1: Monitor E2 Traffic

Check that KPM Indications are flowing from ns-3 to e2term:

```bash
# Terminal 1: Watch RIC
sg docker -c "docker logs -f e2term 2>&1 | grep -E 'E2|gnb|RIC|Indication'"
```

Expected output:
- E2 Setup Request from ns-3
- E2 Setup Response (from e2term)
- E2 Subscription Request from xApp
- E2 Subscription Response
- E2SM-KPM Indication messages (periodic KPMs from ns-3)

### Option 2: Check xApp Logs

Verify RSLAQ xApp is receiving messages:

```bash
# Terminal 2: Watch xApp
sg docker -c "docker logs -f sample-xapp-24 2>&1 | grep -E 'ric.*indication|kpm|metric'"
```

Expected output:
- E2SM-KPM Indication messages decoded
- DDQN inference logs (observations, Q-values, actions)
- TCP connections on port 4200

### Option 3: Send E2 Control from xApp

To test E2 Control reception, run this from xApp container:

```python
# Inside sample-xapp-24 container
cd /home/sample-xapp
python3 << 'EOF'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("127.0.0.1", 4200))
msg = b"E2SM-RC-Format1\x00\x01"  # Action ID 1 (Handover) with no params
s.send(msg)
s.close()
EOF
```

This sends an E2 Control message (Action ID 1: Handover) to the E2Termination in ns-3.
Expected result in e2term logs: "RIC Control Received" message showing Action ID 1.

## Architecture Notes

### E2 Message Flow

```
┌──────────────┐
│  ns-3 (E2 Agent) │
│  sends KPM Indications │
└──────────────┬─────────┘
       ▼
┌──────────────┐
│  e2term (SCTP) │
└──────────────┬─────────┘
       ▼
┌──────────────┐
│  e2mgr (TCP) │
└──────────────┬─────────┘
       ▼
┌──────────────┐
│  sample-xapp-24 │
│  (RSLAQ DDQN) │
└──────────────┬─────────┘
       ▼
┌──────────────┐
│  E2Termination │
│  (in ns-3)    │
└──────────────┬─────────┘
       ▼
Decodes KPM → Calls DDQN → Sends E2 Control → E2Termination decodes → MAC Scheduler
```

### RC Service Model Extension (Future Work)

To enable RQSLAQ MAC slicing control via E2, need to:

1. Add Control Action ID 10 (Slice PRB Quota) in `ric-control-function-description.cc`
2. Modify `nr-rl-mac-scheduler-ofdma.cc` to register callback
3. Add parameter extraction in simulation callback
4. Update E2 Setup to include ORAN-WG3-RIC-Service-Model:MACSlicingControl

**File to modify**:
- `/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/contrib/oran-interface/model/ric-control-function-description.cc`
- `/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/contrib/nori/model/nr-rl-mac-scheduler-ofdma.cc`
- `/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/contrib/oran-interface/model/kpm-function-description.cc` (update RAN Function ID from 300 to include slicing)

**Current RAN Function ID**:
- ID 300 is currently used by RC Service Model
- Should either add a new ID (e.g., 301) or update 300 to include slicing actions

## Current Limitations

1. ns-o-ran-ns3-mmwave-oran doesn't have proper CMake build setup
2. Test scenario needs to be in scratch directory but scratch isn't configured for cmake build
3. RC Service Model lacks MAC control actions

## What We Have

All the infrastructure is in place and working:
- ✅ RIC platform (e2term, e2mgr, db)
- ✅ RSLAQ xApp (DDQN agent) running
- ✅ E2 Interface in ns-3-dev with KPM support
- ✅ ORAN interface built and registered

The missing piece is E2 **Control for MAC scheduling**, which would require extending the RC Service Model as described above.
