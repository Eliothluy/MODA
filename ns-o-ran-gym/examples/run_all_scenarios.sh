#!/usr/bin/env bash
# RSLAQ network-only campaign: online heuristics plus offline meta-heuristics.
#
# This runner intentionally does not execute DRL training lines. DDQN, SAC, and
# predictive SAC are disabled here so this script can be used for baseline
# heuristic/meta-heuristic data generation.
#
# Usage:
#   cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
#   bash examples/run_all_scenarios.sh
#
# Useful overrides:
#   SCENARIOS="normal congestion" SEEDS="1 2 3" SIM_TIME=10 bash examples/run_all_scenarios.sh
#   RUN_HEURISTICS=0 RUN_METAHEURISTICS=1 META_ITERATIONS=8 META_POPULATION=10 bash examples/run_all_scenarios.sh

set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/home/elioth/Documentos/artigo_jussi}"
NS3_DIR="${NS3_DIR:-${REPO_ROOT}/ns-3-dev}"
GYM_DIR="${GYM_DIR:-${REPO_ROOT}/ns-o-ran-gym}"

RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${GYM_DIR}/results_controlled/heuristics_metaheuristics/${RUN_TAG}}"
HEURISTIC_OUTPUT_ROOT="${HEURISTIC_OUTPUT_ROOT:-${OUTPUT_ROOT}/heuristics_ns3}"
META_OUTPUT_ROOT="${META_OUTPUT_ROOT:-${OUTPUT_ROOT}/metaheuristics}"

RUN_HEURISTICS="${RUN_HEURISTICS:-1}"
RUN_METAHEURISTICS="${RUN_METAHEURISTICS:-1}"
BUILD_NS3="${BUILD_NS3:-1}"

SCENARIOS="${SCENARIOS:-low_traffic normal congestion stressed insufficient_resources}"
SEEDS="${SEEDS:-1 2 3}"
RUNS="${RUNS:-1}"

SIM_TIME="${SIM_TIME:-10}"
APP_START="${APP_START:-0.4}"
DRAIN_TIME_SEC="${DRAIN_TIME_SEC:-0.2}"
PERIOD_MS="${PERIOD_MS:-10}"
TX_POWER="${TX_POWER:-43}"
TDD_PATTERN="${TDD_PATTERN:-D|D|8D|4GB|4U|U|U}"
RLC_MODE="${RLC_MODE:-um}"

HEURISTIC_MODES="${HEURISTIC_MODES:-slice_demand_greedy slice_sla_greedy slice_least_waste slice_qos_mixed slice_random_vine slice_meta_risk_elastic slice_aqps}"

META_METHOD="${META_METHOD:-all}"
META_ITERATIONS="${META_ITERATIONS:-4}"
META_POPULATION="${META_POPULATION:-6}"
META_MUTATION_STRENGTH="${META_MUTATION_STRENGTH:-0.12}"
META_INTRA_ALGO="${META_INTRA_ALGO:-PF}"
META_RANDOM_SEED="${META_RANDOM_SEED:-2026}"
META_SEED="${META_SEED:-1}"
META_RUN="${META_RUN:-1}"

mkdir -p "${OUTPUT_ROOT}"

echo "============================================"
echo "RSLAQ heuristics + meta-heuristics campaign"
echo "============================================"
echo "Output root      : ${OUTPUT_ROOT}"
echo "Scenarios        : ${SCENARIOS}"
echo "Seeds            : ${SEEDS}"
echo "Runs             : ${RUNS}"
echo "Run heuristics   : ${RUN_HEURISTICS}"
echo "Run metaheur     : ${RUN_METAHEURISTICS}"
echo "Heuristic modes  : ${HEURISTIC_MODES}"
echo "Meta method      : ${META_METHOD}"
echo "Meta iterations  : ${META_ITERATIONS}"
echo "Meta population  : ${META_POPULATION}"
echo "DRL              : disabled"
echo ""

if [[ "${BUILD_NS3}" == "1" ]]; then
    echo "[BUILD] Building rslaq-sim..."
    cd "${NS3_DIR}"
    ./ns3 build rslaq-sim
else
    echo "[BUILD] Skipping ns-3 build because BUILD_NS3=${BUILD_NS3}"
fi

if [[ "${RUN_HEURISTICS}" == "1" ]]; then
    echo ""
    echo "============================================"
    echo "Running online heuristic baselines"
    echo "============================================"
    cd "${NS3_DIR}"
    OUTPUT_ROOT="${HEURISTIC_OUTPUT_ROOT}" \
    BUILD_NS3=0 \
    SCENARIOS="${SCENARIOS}" \
    BASELINE_MODES="${HEURISTIC_MODES}" \
    SEEDS="${SEEDS}" \
    RUNS="${RUNS}" \
    SIM_TIME="${SIM_TIME}" \
    APP_START="${APP_START}" \
    DRAIN_TIME_SEC="${DRAIN_TIME_SEC}" \
    PERIOD_MS="${PERIOD_MS}" \
    TX_POWER="${TX_POWER}" \
    TDD_PATTERN="${TDD_PATTERN}" \
    RLC_MODE="${RLC_MODE}" \
    ./run_all_scenarios.sh
else
    echo "[SKIP] Online heuristics disabled by RUN_HEURISTICS=${RUN_HEURISTICS}"
fi

if [[ "${RUN_METAHEURISTICS}" == "1" ]]; then
    echo ""
    echo "============================================"
    echo "Running offline meta-heuristic searches"
    echo "============================================"
    cd "${GYM_DIR}"
    read -r -a SCENARIO_LIST <<< "${SCENARIOS}"
    for scenario in "${SCENARIO_LIST[@]}"; do
        echo "[META] scenario=${scenario} method=${META_METHOD}"
        python3 examples/run_rslaq_metaheuristics.py \
            --method "${META_METHOD}" \
            --scenario "${scenario}" \
            --seed "${META_SEED}" \
            --run "${META_RUN}" \
            --random_seed "${META_RANDOM_SEED}" \
            --iterations "${META_ITERATIONS}" \
            --population "${META_POPULATION}" \
            --mutation_strength "${META_MUTATION_STRENGTH}" \
            --intra_algo "${META_INTRA_ALGO}" \
            --sim_time "${SIM_TIME}" \
            --app_start "${APP_START}" \
            --drain_time "${DRAIN_TIME_SEC}" \
            --period_ms "${PERIOD_MS}" \
            --tx_power "${TX_POWER}" \
            --tdd_pattern "${TDD_PATTERN}" \
            --rlc_mode "${RLC_MODE}" \
            --ns3_dir "${NS3_DIR}" \
            --output_root "${META_OUTPUT_ROOT}/scenario=${scenario}"
    done
else
    echo "[SKIP] Meta-heuristics disabled by RUN_METAHEURISTICS=${RUN_METAHEURISTICS}"
fi

echo ""
echo "============================================"
echo "Campaign complete"
echo "============================================"
echo "Heuristics output     : ${HEURISTIC_OUTPUT_ROOT}/results_rslaq_network_only"
echo "Meta-heuristics output: ${META_OUTPUT_ROOT}"
