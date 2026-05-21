#!/usr/bin/env bash
# Controlled RSLAQ validation campaign.
#
# Runs three comparable lines over the same scenarios/seeds/budget:
#   1) network-only ns-3 baselines, without DRL optimization;
#   2) SAC with the paper-faithful RSLAQ reward;
#   3) SAC with the resource-efficient reward contribution.
#
# DDQN can still be enabled with RUN_DDQN=1 for legacy comparisons.

set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/home/elioth/Documentos/artigo_jussi}"
NS3_DIR="${NS3_DIR:-${REPO_ROOT}/ns-3-dev}"
GYM_DIR="${GYM_DIR:-${REPO_ROOT}/ns-o-ran-gym}"

RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
EXPERIMENT_LINE="${EXPERIMENT_LINE:-rslaq_sla_resource_efficiency}"
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

RESOURCE_EFFICIENCY_WEIGHT="${RESOURCE_EFFICIENCY_WEIGHT:-0.20}"
NEED_MATCH_WEIGHT="${NEED_MATCH_WEIGHT:-0.15}"
WASTE_PENALTY_WEIGHT="${WASTE_PENALTY_WEIGHT:-0.25}"
UNDER_ALLOCATION_PENALTY_WEIGHT="${UNDER_ALLOCATION_PENALTY_WEIGHT:-0.10}"
ACTION_SMOOTHNESS_WEIGHT="${ACTION_SMOOTHNESS_WEIGHT:-0.05}"
RESOURCE_DYNAMIC_NEED_WEIGHT="${RESOURCE_DYNAMIC_NEED_WEIGHT:-0.75}"
RESOURCE_WASTE_DEADBAND="${RESOURCE_WASTE_DEADBAND:-0.03}"

RUN_BASELINES="${RUN_BASELINES:-1}"
RUN_DDQN="${RUN_DDQN:-0}"
RUN_PAPER_SAC="${RUN_PAPER_SAC:-1}"
RUN_RESOURCE_EFFICIENT_SAC="${RUN_RESOURCE_EFFICIENT_SAC:-1}"
BASELINE_MODES="${BASELINE_MODES:-pure_rr pure_pf pure_bcqi}"

mkdir -p "${OUTPUT_ROOT}"

cat <<EOF
RSLAQ controlled validation
  line:              ${EXPERIMENT_LINE}
  output:            ${OUTPUT_ROOT}
  scenarios:         ${SCENARIOS[*]}
  seeds:             ${SEEDS[*]}
  budget:            ${EPISODES} episodes x ${EPISODE_STEPS} steps = $((EPISODES * EPISODE_STEPS))
  simTime:           ${SIM_TIME}s
  P_STA fraction:    ${P_STA_STATIC_FRACTION}
  P_STA weights:     ${P_STA_WEIGHTS}
  reward weights:    ${REWARD_ALPHA},${REWARD_BETA},${REWARD_GAMMA}
  baselines:         ${RUN_BASELINES} (${BASELINE_MODES})
  DDQN paper:        ${RUN_DDQN}
  SAC paper:         ${RUN_PAPER_SAC}
  SAC contribution:  ${RUN_RESOURCE_EFFICIENT_SAC}
  contribution w:    eff=${RESOURCE_EFFICIENCY_WEIGHT}, match=${NEED_MATCH_WEIGHT}, waste=${WASTE_PENALTY_WEIGHT}, under=${UNDER_ALLOCATION_PENALTY_WEIGHT}, smooth=${ACTION_SMOOTHNESS_WEIGHT}
EOF

cd "${NS3_DIR}"
./ns3 build rslaq-sim

if [[ "${RUN_BASELINES}" == "1" ]]; then
    echo "[baseline_ns3] Running pure ns-3 baseline matrix"
    SCENARIOS="${SCENARIOS[*]}" \
    SEEDS="${SEEDS[*]}" \
    RUNS="1" \
    BASELINE_MODES="${BASELINE_MODES}" \
    SIM_TIME="${SIM_TIME}" \
    APP_START="${APP_START}" \
    PERIOD_MS="${PERIOD_MS}" \
    OUTPUT_ROOT="${OUTPUT_ROOT}/baseline_ns3" \
    "${NS3_DIR}/run_all_scenarios.sh"
fi

cd "${GYM_DIR}"

run_ddqn_paper() {
    local scenario="$1"
    local seed="$2"
    echo "[DDQN paper] scenario=${scenario} seed=${seed}"
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
        --output "${OUTPUT_ROOT}/ddqn_paper_${scenario}_seed${seed}"
}

run_sac() {
    local reward_mode="$1"
    local label="$2"
    local scenario="$3"
    local seed="$4"

    echo "[SAC ${label}] scenario=${scenario} seed=${seed} reward=${reward_mode}"
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
        --reward_mode "${reward_mode}" \
        --resource_efficiency_weight "${RESOURCE_EFFICIENCY_WEIGHT}" \
        --need_match_weight "${NEED_MATCH_WEIGHT}" \
        --waste_penalty_weight "${WASTE_PENALTY_WEIGHT}" \
        --under_allocation_penalty_weight "${UNDER_ALLOCATION_PENALTY_WEIGHT}" \
        --action_smoothness_weight "${ACTION_SMOOTHNESS_WEIGHT}" \
        --resource_dynamic_need_weight "${RESOURCE_DYNAMIC_NEED_WEIGHT}" \
        --resource_waste_deadband "${RESOURCE_WASTE_DEADBAND}" \
        --output "${OUTPUT_ROOT}/sac_${label}_${scenario}_seed${seed}"
}

for scenario in "${SCENARIOS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        if [[ "${RUN_DDQN}" == "1" ]]; then
            run_ddqn_paper "${scenario}" "${seed}"
        fi
        if [[ "${RUN_PAPER_SAC}" == "1" ]]; then
            run_sac "paper" "paper" "${scenario}" "${seed}"
        fi
        if [[ "${RUN_RESOURCE_EFFICIENT_SAC}" == "1" ]]; then
            run_sac "resource_efficient" "resource_efficient" "${scenario}" "${seed}"
        fi
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
  "run_baselines": ${RUN_BASELINES},
  "baseline_modes": "${BASELINE_MODES}",
  "run_ddqn": ${RUN_DDQN},
  "run_paper_sac": ${RUN_PAPER_SAC},
  "run_resource_efficient_sac": ${RUN_RESOURCE_EFFICIENT_SAC},
  "p_sta_static_fraction": ${P_STA_STATIC_FRACTION},
  "p_sta_weights": "${P_STA_WEIGHTS}",
  "reward_weights": "${REWARD_ALPHA},${REWARD_BETA},${REWARD_GAMMA}",
  "resource_efficient_reward": {
    "resource_efficiency_weight": ${RESOURCE_EFFICIENCY_WEIGHT},
    "need_match_weight": ${NEED_MATCH_WEIGHT},
    "waste_penalty_weight": ${WASTE_PENALTY_WEIGHT},
    "under_allocation_penalty_weight": ${UNDER_ALLOCATION_PENALTY_WEIGHT},
    "action_smoothness_weight": ${ACTION_SMOOTHNESS_WEIGHT},
    "resource_dynamic_need_weight": ${RESOURCE_DYNAMIC_NEED_WEIGHT},
    "resource_waste_deadband": ${RESOURCE_WASTE_DEADBAND}
  }
}
EOF

echo "Controlled campaign complete: ${OUTPUT_ROOT}"
