#!/bin/bash
# Resume run_all_scenarios.sh from SAC normal onward.
# Does NOT edit the original script.

set -euo pipefail

REPO_ROOT="/home/elioth/Documentos/artigo_jussi"
NS3_DIR="${REPO_ROOT}/ns-3-dev"
GYM_DIR="${REPO_ROOT}/ns-o-ran-gym"
RESULTS_DIR="${GYM_DIR}/results"

EPISODES=10
MAX_STEPS=350
SIM_TIME=10.0
APP_START=0.5
PERIOD_MS=10
APPLY_P_STA="True"

cd "${GYM_DIR}"

# SAC — remaining scenarios (normal onward)
echo ""
echo "============================================"
echo "[RESUME] SAC Training — From normal onward"
echo "============================================"
for scenario in normal congestion stressed insufficient_resources; do
    echo ""
    echo "--- SAC | Scenario: ${scenario} ---"
    python3 examples/rslaq_train_sac.py \
        --scenario "${scenario}" \
        --episodes "${EPISODES}" \
        --simTime "${SIM_TIME}" \
        --appStart "${APP_START}" \
        --periodMs "${PERIOD_MS}" \
        --max_steps "${MAX_STEPS}" \
        --observation_mode paper \
        --action_mode continuous \
        --apply_p_sta "${APPLY_P_STA}" \
        --output "${RESULTS_DIR}/sac_${scenario}"
done

# DDQN — all scenarios
echo ""
echo "============================================"
echo "[RESUME] DDQN Training — All Scenarios"
echo "============================================"
for scenario in low_traffic normal congestion stressed insufficient_resources; do
    echo ""
    echo "--- DDQN | Scenario: ${scenario} ---"
    python3 examples/rslaq_train_ddqn.py \
        --scenario "${scenario}" \
        --episodes "${EPISODES}" \
        --simTime "${SIM_TIME}" \
        --appStart "${APP_START}" \
        --periodMs "${PERIOD_MS}" \
        --max_steps "${MAX_STEPS}" \
        --observation_mode paper \
        --action_mode discrete \
        --apply_p_sta "${APPLY_P_STA}" \
        --output "${RESULTS_DIR}/ddqn_${scenario}"
done

echo ""
echo "============================================"
echo "Resume Complete!"
echo "============================================"
ls -1 "${RESULTS_DIR}"
