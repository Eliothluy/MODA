#!/bin/bash
# GreenRAN Training Script — All Scenarios, Single Seed
# Runs SAC + DDQN in parallel for every GreenRAN scenario.
#
# Usage:
#   cd /home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym
#   bash examples/run_all_greenran_scenarios.sh

set -euo pipefail

REPO_ROOT="/home/eliothluy/Documentos/artigo_jussi"
NS3_DIR="${REPO_ROOT}/ns-3-dev"
GYM_DIR="${REPO_ROOT}/ns-o-ran-gym"
RESULTS_DIR="${GYM_DIR}/results_greenran"
CONFIG_JSON="${GYM_DIR}/src/environments/scenario_configurations/greenran_use_case.json"

# ── Seed ──────────────────────────────────────────────────
FIXED_SEED=3
SEED_CYCLE=99999

# ── Training ──────────────────────────────────────────────
SAC_EPISODES=300
DDQN_EPISODES=50

# GreenRAN uses periodMs=100 (see greenran_use_case.json).
# appStart is fixed at 0.5s in GreenRan-slice.cc.
PERIOD_MS=100
APP_START=0.5
CONSECUTIVE_OUTAGE_STEPS=5

# SAC: longer episodes to observe steady-state behaviour
SAC_SIM_TIME=10.0
SAC_MAX_STEPS=$(python3 -c "print(int((${SAC_SIM_TIME} - ${APP_START}) * 1000 / ${PERIOD_MS}))")

# DDQN: need enough steps for ntsr=100 with periodMs=100
# 100 steps * 100 ms = 10s  →  simTime must be >= 10.5s
DDQN_SIM_TIME=12.0
DDQN_NTSR=100
DDQN_MAX_STEPS=$(python3 -c "print(int((${DDQN_SIM_TIME} - ${APP_START}) * 1000 / ${PERIOD_MS}))")

# ── SAC hyperparameters ───────────────────────────────────
SAC_BUFFER_SIZE=50000
SAC_BATCH_SIZE=256
SAC_LR=0.001
SAC_GAMMA=0.99
SAC_TAU=0.005
SAC_ALPHA=0.1

# ── DDQN hyperparameters ──────────────────────────────────
DDQN_BUFFER_SIZE=128
DDQN_BATCH_SIZE=32
DDQN_LR=0.001
DDQN_GAMMA=0.80
DDQN_EPS_START=1.0
DDQN_EPS_MIN=0.05
DDQN_EPS_DECAY=0.998
DDQN_TARGET_UPDATE=200

# ── Scenarios (must match InitGreenRanScenarios in GreenRan-slice.cc) ──
SCENARIOS=(
    "greenran_low"
    "greenran_normal"
    "greenran_video_heavy"
    "greenran_congestion"
    "greenran_night_energy"
    "greenran_balanced"
)

echo "============================================"
echo "GreenRAN — All Scenarios | Single Seed (${FIXED_SEED})"
echo "============================================"
echo "Config JSON: ${CONFIG_JSON}"
echo "Seed:        ${FIXED_SEED} (fixed)"
echo "SAC:         ${SAC_EPISODES} eps × ${SAC_MAX_STEPS} steps"
echo "DDQN:        ${DDQN_EPISODES} eps × ${DDQN_NTSR} steps (ntsr)"
echo "Results:     ${RESULTS_DIR}/"
echo ""

# 1. Check ns-3 binary (non-optimized build path used by GreenRanEnv)
NS3_BIN=$(find "${NS3_DIR}/build/scratch" -name "*GreenRan-slice*" -type f -executable | head -n 1 || true)
if [[ -z "${NS3_BIN}" ]]; then
    echo "[BUILD] ns-3 binary for GreenRan-slice not found. Building ..."
    cd "${NS3_DIR}"
    ./ns3 configure --enable-examples --enable-tests
    ./ns3 build GreenRan-slice
    NS3_BIN=$(find "${NS3_DIR}/build/scratch" -name "*GreenRan-slice*" -type f -executable | head -n 1)
    echo "[BUILD] Done. Binary: ${NS3_BIN}"
else
    echo "[BUILD] ns-3 binary found at ${NS3_BIN}"
fi

# 2. Ensure results directory exists
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
    python3 examples/greenran_train_sac.py \
        --scenario "${scenario}" \
        --config "${CONFIG_JSON}" \
        --episodes "${SAC_EPISODES}" \
        --seed "${FIXED_SEED}" \
        --seed_cycle "${SEED_CYCLE}" \
        --simTime "${SAC_SIM_TIME}" \
        --periodMs "${PERIOD_MS}" \
        --max_steps "${SAC_MAX_STEPS}" \
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
    python3 examples/greenran_train_ddqn.py \
        --scenario "${scenario}" \
        --config "${CONFIG_JSON}" \
        --episodes "${DDQN_EPISODES}" \
        --seed "${FIXED_SEED}" \
        --seed_cycle "${SEED_CYCLE}" \
        --simTime "${DDQN_SIM_TIME}" \
        --periodMs "${PERIOD_MS}" \
        --max_steps "${DDQN_MAX_STEPS}" \
        --ntsr "${DDQN_NTSR}" \
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
