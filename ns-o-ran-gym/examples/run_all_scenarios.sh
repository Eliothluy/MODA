#!/bin/bash
# RSLAQ Training Script — All Scenarios Sequentially
# Reproduces paper setup: 50% P_STA + 50% DRL (apply_p_sta=True)
#
# Usage:
#   cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
#   bash examples/run_all_scenarios.sh

set -euo pipefail

REPO_ROOT="/home/eliothluy/Documentos/artigo_jussi"
NS3_DIR="${REPO_ROOT}/ns-3-dev"
GYM_DIR="${REPO_ROOT}/ns-o-ran-gym"
RESULTS_DIR="${GYM_DIR}/results"

EPISODES=350
SEED_CYCLE=50
SIM_TIME=10.0
APP_START=0.5
PERIOD_MS=10
# Compute max_steps automatically to align with simTime and appStart
MAX_STEPS=$(python3 -c "print(int((${SIM_TIME} - ${APP_START}) * 1000 / ${PERIOD_MS}))")
CONSECUTIVE_OUTAGE_STEPS=5

SCENARIOS=(
    "low_traffic"
    "normal"
    "congestion"
    "stressed"
    "insufficient_resources"
)

echo "============================================"
echo "RSLAQ — All Scenarios Training"
echo "============================================"
echo "Episodes:    ${EPISODES}"
echo "Seed cycle:  ${SEED_CYCLE}"
echo "Max steps:   ${MAX_STEPS}"
echo "Sim time:    ${SIM_TIME}s"
echo "Period:      ${PERIOD_MS}ms"
echo "Outage win:  ${CONSECUTIVE_OUTAGE_STEPS} steps (${CONSECUTIVE_OUTAGE_STEPS}0ms)"
echo "Results:     ${RESULTS_DIR}"
echo ""

# 1. Check ns-3 binary
NS3_BIN="${NS3_DIR}/build/scratch/rslaq/rslaq-sim"
if [[ ! -x "${NS3_BIN}" ]]; then
    echo "[BUILD] ns-3 binary not found. Building rslaq-sim ..."
    cd "${NS3_DIR}"
    ./ns3 configure --enable-examples --enable-tests
    ./ns3 build rslaq-sim
    echo "[BUILD] Done."
else
    echo "[BUILD] ns-3 binary found."
fi

# 2. Create results directory
mkdir -p "${RESULTS_DIR}"

cd "${GYM_DIR}"

# 3. SAC — per scenario
echo ""
echo "============================================"
echo "[1/2] SAC Training — Per Scenario"
echo "============================================"
for scenario in "${SCENARIOS[@]}"; do
    echo ""
    echo "--- SAC | Scenario: ${scenario} ---"
    python3 examples/rslaq_train_sac.py \
        --scenario "${scenario}" \
        --episodes "${EPISODES}" \
        --seed_cycle "${SEED_CYCLE}" \
        --simTime "${SIM_TIME}" \
        --appStart "${APP_START}" \
        --periodMs "${PERIOD_MS}" \
        --max_steps "${MAX_STEPS}" \
        --observation_mode paper \
        --action_mode continuous \
        --consecutive_outage_steps "${CONSECUTIVE_OUTAGE_STEPS}" \
        --output "${RESULTS_DIR}/sac_${scenario}"
done

# 4. DDQN — per scenario
echo ""
echo "============================================"
echo "[2/2] DDQN Training — Per Scenario"
echo "============================================"
for scenario in "${SCENARIOS[@]}"; do
    echo ""
    echo "--- DDQN | Scenario: ${scenario} ---"
    python3 examples/rslaq_train_ddqn.py \
        --scenario "${scenario}" \
        --episodes "${EPISODES}" \
        --seed_cycle "${SEED_CYCLE}" \
        --simTime "${SIM_TIME}" \
        --appStart "${APP_START}" \
        --periodMs "${PERIOD_MS}" \
        --max_steps "${MAX_STEPS}" \
        --observation_mode paper \
        --action_mode discrete \
        --consecutive_outage_steps "${CONSECUTIVE_OUTAGE_STEPS}" \
        --output "${RESULTS_DIR}/ddqn_${scenario}"
done

echo ""
echo "============================================"
echo "Training Complete!"
echo "============================================"
echo "Results saved to: ${RESULTS_DIR}"
echo ""
echo "Directory structure:"
ls -1 "${RESULTS_DIR}"
