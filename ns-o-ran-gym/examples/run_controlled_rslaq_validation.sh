#!/usr/bin/env bash
# Controlled RSLAQ validation campaign.
#
# Runs DDQN and SAC with the same interaction budget, plus optional ns-3
# baselines, while keeping paper-faithful defaults.

set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/home/elioth/Documentos/artigo_jussi}"
NS3_DIR="${NS3_DIR:-${REPO_ROOT}/ns-3-dev}"
GYM_DIR="${GYM_DIR:-${REPO_ROOT}/ns-o-ran-gym}"

RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
EXPERIMENT_LINE="${EXPERIMENT_LINE:-paper_faithful}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${GYM_DIR}/results_controlled/${EXPERIMENT_LINE}/${RUN_TAG}}"

SCENARIOS_INPUT="${SCENARIOS:-low_traffic normal congestion stressed insufficient_resources}"
SEEDS_INPUT="${SEEDS:-1 2 3 4 5}"
read -r -a SCENARIOS <<< "${SCENARIOS_INPUT}"
read -r -a SEEDS <<< "${SEEDS_INPUT}"

INTERACTION_STEPS="${INTERACTION_STEPS:-5000}"
EPISODE_STEPS="${EPISODE_STEPS:-100}"
EPISODES="$(python3 -c "import math; print(math.ceil(${INTERACTION_STEPS}/${EPISODE_STEPS}))")"

APP_START="${APP_START:-0.5}"
PERIOD_MS="${PERIOD_MS:-10}"
SIM_TIME="$(python3 -c "print(${APP_START} + (${EPISODE_STEPS} * ${PERIOD_MS}) / 1000.0 + 0.2)")"
CONSECUTIVE_OUTAGE_STEPS="${CONSECUTIVE_OUTAGE_STEPS:-5}"
WARMUP_STEPS="${WARMUP_STEPS:-5}"
SEED_CYCLE="${SEED_CYCLE:-999999}"

P_STA_STATIC_FRACTION="${P_STA_STATIC_FRACTION:-0.5}"
P_STA_WEIGHTS="${P_STA_WEIGHTS:-0.3333,0.4000,0.2667}"
REWARD_ALPHA="${REWARD_ALPHA:-0.3333}"
REWARD_BETA="${REWARD_BETA:-0.4000}"
REWARD_GAMMA="${REWARD_GAMMA:-0.2667}"

DDQN_BUFFER_SIZE="${DDQN_BUFFER_SIZE:-500}"
DDQN_BATCH_SIZE="${DDQN_BATCH_SIZE:-64}"
DDQN_LR="${DDQN_LR:-0.001}"
DDQN_GAMMA="${DDQN_GAMMA:-0.80}"
DDQN_EPS_START="${DDQN_EPS_START:-1.0}"
DDQN_EPS_MIN="${DDQN_EPS_MIN:-0.05}"
DDQN_EPS_DECAY="${DDQN_EPS_DECAY:-0.998}"
DDQN_TARGET_UPDATE="${DDQN_TARGET_UPDATE:-200}"

SAC_BUFFER_SIZE="${SAC_BUFFER_SIZE:-50000}"
SAC_BATCH_SIZE="${SAC_BATCH_SIZE:-256}"
SAC_LR="${SAC_LR:-0.001}"
SAC_GAMMA="${SAC_GAMMA:-0.99}"
SAC_TAU="${SAC_TAU:-0.005}"
SAC_ALPHA="${SAC_ALPHA:-0.1}"

RUN_BASELINES="${RUN_BASELINES:-1}"
BASELINE_MODES="${BASELINE_MODES:-pure_rr pure_pf pure_bcqi slice_weighted_pf}"

mkdir -p "${OUTPUT_ROOT}"

echo "RSLAQ controlled validation"
echo "  line:              ${EXPERIMENT_LINE}"
echo "  output:            ${OUTPUT_ROOT}"
echo "  scenarios:         ${SCENARIOS[*]}"
echo "  seeds:             ${SEEDS[*]}"
echo "  budget:            ${EPISODES} episodes x ${EPISODE_STEPS} steps = $((EPISODES * EPISODE_STEPS))"
echo "  simTime:           ${SIM_TIME}s"
echo "  P_STA fraction:    ${P_STA_STATIC_FRACTION}"
echo "  P_STA weights:     ${P_STA_WEIGHTS}"
echo "  reward weights:    ${REWARD_ALPHA},${REWARD_BETA},${REWARD_GAMMA}"

cd "${NS3_DIR}"
./ns3 build rslaq-sim

if [[ "${RUN_BASELINES}" == "1" ]]; then
    echo "[baselines] Running ns-3 baseline matrix"
    SCENARIOS="${SCENARIOS[*]}" \
    SEEDS="${SEEDS[*]}" \
    RUNS="1" \
    BASELINE_MODES="${BASELINE_MODES}" \
    SIM_TIME="${SIM_TIME}" \
    APP_START="${APP_START}" \
    PERIOD_MS="${PERIOD_MS}" \
    OUTPUT_ROOT="${OUTPUT_ROOT}/baselines" \
    "${NS3_DIR}/run_all_scenarios.sh"
fi

cd "${GYM_DIR}"

for scenario in "${SCENARIOS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        echo "[DDQN] scenario=${scenario} seed=${seed}"
        python3 examples/rslaq_train_ddqn.py \
            --scenario "${scenario}" \
            --episodes "${EPISODES}" \
            --seed "${seed}" \
            --seed_cycle "${SEED_CYCLE}" \
            --simTime "${SIM_TIME}" \
            --appStart "${APP_START}" \
            --periodMs "${PERIOD_MS}" \
            --max_steps "${EPISODE_STEPS}" \
            --ntsr "${EPISODE_STEPS}" \
            --observation_mode paper \
            --action_mode discrete \
            --consecutive_outage_steps "${CONSECUTIVE_OUTAGE_STEPS}" \
            --warmup_steps "${WARMUP_STEPS}" \
            --buffer_size "${DDQN_BUFFER_SIZE}" \
            --batch_size "${DDQN_BATCH_SIZE}" \
            --lr "${DDQN_LR}" \
            --gamma "${DDQN_GAMMA}" \
            --epsilon_start "${DDQN_EPS_START}" \
            --epsilon_min "${DDQN_EPS_MIN}" \
            --epsilon_decay "${DDQN_EPS_DECAY}" \
            --target_update "${DDQN_TARGET_UPDATE}" \
            --p_sta_static_fraction "${P_STA_STATIC_FRACTION}" \
            --p_sta_weights "${P_STA_WEIGHTS}" \
            --reward_alpha "${REWARD_ALPHA}" \
            --reward_beta "${REWARD_BETA}" \
            --reward_gamma "${REWARD_GAMMA}" \
            --output "${OUTPUT_ROOT}/ddqn_${scenario}_seed${seed}"

        echo "[SAC] scenario=${scenario} seed=${seed}"
        python3 examples/rslaq_train_sac.py \
            --scenario "${scenario}" \
            --episodes "${EPISODES}" \
            --seed "${seed}" \
            --seed_cycle "${SEED_CYCLE}" \
            --simTime "${SIM_TIME}" \
            --appStart "${APP_START}" \
            --periodMs "${PERIOD_MS}" \
            --max_steps "${EPISODE_STEPS}" \
            --observation_mode paper \
            --action_mode continuous \
            --consecutive_outage_steps "${CONSECUTIVE_OUTAGE_STEPS}" \
            --warmup_steps "${WARMUP_STEPS}" \
            --buffer_size "${SAC_BUFFER_SIZE}" \
            --batch_size "${SAC_BATCH_SIZE}" \
            --lr "${SAC_LR}" \
            --gamma "${SAC_GAMMA}" \
            --tau "${SAC_TAU}" \
            --alpha "${SAC_ALPHA}" \
            --p_sta_static_fraction "${P_STA_STATIC_FRACTION}" \
            --p_sta_weights "${P_STA_WEIGHTS}" \
            --reward_alpha "${REWARD_ALPHA}" \
            --reward_beta "${REWARD_BETA}" \
            --reward_gamma "${REWARD_GAMMA}" \
            --output "${OUTPUT_ROOT}/sac_${scenario}_seed${seed}"
    done
done

cat > "${OUTPUT_ROOT}/campaign_config.json" <<EOF
{
  "experiment_line": "${EXPERIMENT_LINE}",
  "run_tag": "${RUN_TAG}",
  "scenarios": "${SCENARIOS[*]}",
  "seeds": "${SEEDS[*]}",
  "episodes": ${EPISODES},
  "episode_steps": ${EPISODE_STEPS},
  "interaction_budget": $((EPISODES * EPISODE_STEPS)),
  "sim_time": ${SIM_TIME},
  "app_start": ${APP_START},
  "period_ms": ${PERIOD_MS},
  "p_sta_static_fraction": ${P_STA_STATIC_FRACTION},
  "p_sta_weights": "${P_STA_WEIGHTS}",
  "reward_weights": "${REWARD_ALPHA},${REWARD_BETA},${REWARD_GAMMA}"
}
EOF

echo "Controlled campaign complete: ${OUTPUT_ROOT}"
