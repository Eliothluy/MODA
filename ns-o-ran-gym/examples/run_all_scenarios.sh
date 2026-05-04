#!/bin/bash
# RSLAQ Training Script — All Scenarios, Single Seed
# Based on seed_cycle=50 analysis: seed 3 (eps 101-150) had best UE geometry (reward 546.0).
# Runs both SAC and DDQN on all 5 scenarios with fixed seed, 300 episodes each.
#
# Usage:
#   cd /home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym
#   bash examples/run_all_scenarios.sh

set -euo pipefail

REPO_ROOT="/home/eliothluy/Documentos/artigo_jussi"
NS3_DIR="${REPO_ROOT}/ns-3-dev"
GYM_DIR="${REPO_ROOT}/ns-o-ran-gym"
RESULTS_DIR="${GYM_DIR}/results"

# ── Seed ──────────────────────────────────────────────────
# seed_cycle=99999 keeps seed fixed across all episodes.
# Seed 3 had the best UE geometry in prior seed_cycle=50 analysis.
FIXED_SEED=3
SEED_CYCLE=99999

# ── Training ──────────────────────────────────────────────
EPISODES=300
SIM_TIME=10.0
APP_START=0.5
PERIOD_MS=10
MAX_STEPS=$(python3 -c "print(int((${SIM_TIME} - ${APP_START}) * 1000 / ${PERIOD_MS}))")
CONSECUTIVE_OUTAGE_STEPS=5

# ── SAC hyperparameters ───────────────────────────────────
SAC_BUFFER_SIZE=50000
SAC_BATCH_SIZE=256
SAC_LR=0.001
SAC_GAMMA=0.99
SAC_TAU=0.005
SAC_ALPHA=0.1

# ── DDQN hyperparameters ──────────────────────────────────
DDQN_BUFFER_SIZE=50000
DDQN_BATCH_SIZE=256
DDQN_LR=0.001
DDQN_GAMMA=0.99
DDQN_EPS_START=1.0
DDQN_EPS_MIN=0.01
DDQN_EPS_DECAY=0.995
DDQN_TARGET_UPDATE=100

# ── Scenarios ─────────────────────────────────────────────
SCENARIOS=(
    "low_traffic"
    "normal"
    "congestion"
    "stressed"
    "insufficient_resources"
)

echo "============================================"
echo "RSLAQ — All Scenarios | Single Seed (${FIXED_SEED})"
echo "============================================"
echo "Seed:        ${FIXED_SEED} (fixed)"
echo "Episodes:    ${EPISODES}"
echo "Max steps:   ${MAX_STEPS}  (sim=${SIM_TIME}s, period=${PERIOD_MS}ms)"
echo "Outage win:  ${CONSECUTIVE_OUTAGE_STEPS} steps"
echo "Results:     ${RESULTS_DIR}/"
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
    echo "[BUILD] ns-3 binary found at ${NS3_BIN}"
fi

# 2. Create results directory
mkdir -p "${RESULTS_DIR}"

cd "${GYM_DIR}"

# ──────────────────────────────────────────────────────────
# 3. SAC & DDQN — Per Scenario (parallel)
# ──────────────────────────────────────────────────────────
for scenario in "${SCENARIOS[@]}"; do
    echo ""
    echo "============================================"
    echo "Scenario: ${scenario} | SAC + DDQN (parallel)"
    echo "============================================"

    echo "  [SAC]  Starting... (output: sac_${scenario}_seed${FIXED_SEED})"
    python3 examples/rslaq_train_sac.py \
        --scenario "${scenario}" \
        --episodes "${EPISODES}" \
        --seed "${FIXED_SEED}" \
        --seed_cycle "${SEED_CYCLE}" \
        --simTime "${SIM_TIME}" \
        --appStart "${APP_START}" \
        --periodMs "${PERIOD_MS}" \
        --max_steps "${MAX_STEPS}" \
        --observation_mode paper \
        --action_mode continuous \
        --consecutive_outage_steps "${CONSECUTIVE_OUTAGE_STEPS}" \
        --buffer_size "${SAC_BUFFER_SIZE}" \
        --batch_size "${SAC_BATCH_SIZE}" \
        --lr "${SAC_LR}" \
        --gamma "${SAC_GAMMA}" \
        --tau "${SAC_TAU}" \
        --alpha "${SAC_ALPHA}" \
        --output "${RESULTS_DIR}/sac_${scenario}_seed${FIXED_SEED}" &

    echo "  [DDQN] Starting... (output: ddqn_${scenario}_seed${FIXED_SEED})"
    python3 examples/rslaq_train_ddqn.py \
        --scenario "${scenario}" \
        --episodes "${EPISODES}" \
        --seed "${FIXED_SEED}" \
        --seed_cycle "${SEED_CYCLE}" \
        --simTime "${SIM_TIME}" \
        --appStart "${APP_START}" \
        --periodMs "${PERIOD_MS}" \
        --max_steps "${MAX_STEPS}" \
        --observation_mode paper \
        --action_mode discrete \
        --consecutive_outage_steps "${CONSECUTIVE_OUTAGE_STEPS}" \
        --buffer_size "${DDQN_BUFFER_SIZE}" \
        --batch_size "${DDQN_BATCH_SIZE}" \
        --lr "${DDQN_LR}" \
        --gamma "${DDQN_GAMMA}" \
        --epsilon_start "${DDQN_EPS_START}" \
        --epsilon_min "${DDQN_EPS_MIN}" \
        --epsilon_decay "${DDQN_EPS_DECAY}" \
        --target_update "${DDQN_TARGET_UPDATE}" \
        --output "${RESULTS_DIR}/ddqn_${scenario}_seed${FIXED_SEED}" &

    echo "  Waiting for both to finish..."
    wait
    echo "  [${scenario}] Done."
done

echo ""
echo "============================================"
echo "Training Complete!"
echo "============================================"
echo "Results:"
for scenario in "${SCENARIOS[@]}"; do
    echo "  ${RESULTS_DIR}/sac_${scenario}_seed${FIXED_SEED}"
    echo "  ${RESULTS_DIR}/ddqn_${scenario}_seed${FIXED_SEED}"
done
