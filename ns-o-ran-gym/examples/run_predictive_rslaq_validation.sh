#!/usr/bin/env bash
# Predictive RSLAQ validation campaign.
#
# Trains a temporal KPI forecaster from an existing paper-faithful campaign,
# runs predictive SAC with the same interaction budget, and compares results.

set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/home/elioth/Documentos/artigo_jussi}"
NS3_DIR="${NS3_DIR:-${REPO_ROOT}/ns-3-dev}"
GYM_DIR="${GYM_DIR:-${REPO_ROOT}/ns-o-ran-gym}"

RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
EXPERIMENT_LINE="${EXPERIMENT_LINE:-predictive_forecaster_sac}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${GYM_DIR}/results_controlled/${EXPERIMENT_LINE}/${RUN_TAG}}"

BASELINE_ROOT="${BASELINE_ROOT:-${GYM_DIR}/results_controlled/paper_faithful/20260514_175546}"
FORECAST_SOURCE_ROOT="${FORECAST_SOURCE_ROOT:-${BASELINE_ROOT}}"

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

FORECAST_SEQUENCE_LEN="${FORECAST_SEQUENCE_LEN:-8}"
FORECAST_HORIZON="${FORECAST_HORIZON:-5}"
FORECASTER_EPOCHS="${FORECASTER_EPOCHS:-30}"
FORECASTER_BATCH_SIZE="${FORECASTER_BATCH_SIZE:-256}"
FORECASTER_LR="${FORECASTER_LR:-0.001}"
FORECASTER_HIDDEN_DIM="${FORECASTER_HIDDEN_DIM:-64}"
FORECASTER_LIMIT_FILES="${FORECASTER_LIMIT_FILES:-0}"

SAC_BUFFER_SIZE="${SAC_BUFFER_SIZE:-50000}"
SAC_BATCH_SIZE="${SAC_BATCH_SIZE:-256}"
SAC_LR="${SAC_LR:-0.001}"
SAC_GAMMA="${SAC_GAMMA:-0.99}"
SAC_TAU="${SAC_TAU:-0.005}"
SAC_ALPHA="${SAC_ALPHA:-0.1}"
RISK_PENALTY="${RISK_PENALTY:-0.5}"
SOFT_PENALTY="${SOFT_PENALTY:-0.2}"

mkdir -p "${OUTPUT_ROOT}"

echo "RSLAQ predictive validation"
echo "  line:              ${EXPERIMENT_LINE}"
echo "  output:            ${OUTPUT_ROOT}"
echo "  baseline:          ${BASELINE_ROOT}"
echo "  forecast source:   ${FORECAST_SOURCE_ROOT}"
echo "  scenarios:         ${SCENARIOS[*]}"
echo "  seeds:             ${SEEDS[*]}"
echo "  budget:            ${EPISODES} episodes x ${EPISODE_STEPS} steps = $((EPISODES * EPISODE_STEPS))"
echo "  simTime:           ${SIM_TIME}s"
echo "  forecast:          seq=${FORECAST_SEQUENCE_LEN}, horizon=${FORECAST_HORIZON}"
echo "  penalties:         outage=${RISK_PENALTY}, soft=${SOFT_PENALTY}"

cd "${NS3_DIR}"
./ns3 build rslaq-sim

cd "${GYM_DIR}"

FORECASTER_DIR="${OUTPUT_ROOT}/forecaster"
python3 examples/rslaq_train_forecaster.py \
    --source_root "${FORECAST_SOURCE_ROOT}" \
    --output "${FORECASTER_DIR}" \
    --sequence_len "${FORECAST_SEQUENCE_LEN}" \
    --forecast_horizon "${FORECAST_HORIZON}" \
    --hidden_dim "${FORECASTER_HIDDEN_DIM}" \
    --epochs "${FORECASTER_EPOCHS}" \
    --batch_size "${FORECASTER_BATCH_SIZE}" \
    --lr "${FORECASTER_LR}" \
    --limit_files "${FORECASTER_LIMIT_FILES}"

FORECASTER_CHECKPOINT="${FORECASTER_DIR}/forecaster_best.pt"

for scenario in "${SCENARIOS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        echo "[Predictive SAC] scenario=${scenario} seed=${seed}"
        python3 examples/rslaq_train_predictive_sac.py \
            --scenario "${scenario}" \
            --episodes "${EPISODES}" \
            --seed "${seed}" \
            --seed_cycle "${SEED_CYCLE}" \
            --simTime "${SIM_TIME}" \
            --appStart "${APP_START}" \
            --periodMs "${PERIOD_MS}" \
            --max_steps "${EPISODE_STEPS}" \
            --observation_mode paper \
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
            --risk_penalty "${RISK_PENALTY}" \
            --soft_penalty "${SOFT_PENALTY}" \
            --forecaster_checkpoint "${FORECASTER_CHECKPOINT}" \
            --sequence_len "${FORECAST_SEQUENCE_LEN}" \
            --output "${OUTPUT_ROOT}/predictive_sac_${scenario}_seed${seed}"
    done
done

python3 examples/compare_rslaq_campaigns.py \
    --baseline_root "${BASELINE_ROOT}" \
    --predictive_root "${OUTPUT_ROOT}" \
    --output "${OUTPUT_ROOT}/comparison"

cat > "${OUTPUT_ROOT}/campaign_config.json" <<EOF
{
  "experiment_line": "${EXPERIMENT_LINE}",
  "run_tag": "${RUN_TAG}",
  "baseline_root": "${BASELINE_ROOT}",
  "forecast_source_root": "${FORECAST_SOURCE_ROOT}",
  "scenarios": "${SCENARIOS[*]}",
  "seeds": "${SEEDS[*]}",
  "episodes": ${EPISODES},
  "episode_steps": ${EPISODE_STEPS},
  "interaction_budget": $((EPISODES * EPISODE_STEPS)),
  "sim_time": ${SIM_TIME},
  "app_start": ${APP_START},
  "period_ms": ${PERIOD_MS},
  "forecast_sequence_len": ${FORECAST_SEQUENCE_LEN},
  "forecast_horizon": ${FORECAST_HORIZON},
  "risk_penalty": ${RISK_PENALTY},
  "soft_penalty": ${SOFT_PENALTY},
  "p_sta_static_fraction": ${P_STA_STATIC_FRACTION},
  "p_sta_weights": "${P_STA_WEIGHTS}",
  "reward_weights": "${REWARD_ALPHA},${REWARD_BETA},${REWARD_GAMMA}",
  "demand_aware_embb_outage": true
}
EOF

echo "Predictive campaign complete: ${OUTPUT_ROOT}"
