#!/usr/bin/env bash
# Resume the paper campaign from where it stopped.
#
# Context
# -------
# The original `examples/run_all_scenarios.sh` campaign (RUN_TAG=20260626_122326)
# stopped partway through Phase 1 (baselines). Only the 7 heuristic/AQPS modes
# completed (105 runs, 1 failure). The 7 pure-scheduler / RSLAQ modes never ran,
# and Phases 2 (meta-heuristics) and 3 (meta-evaluation) were never started.
#
# This script:
#   1. Reuses the original OUTPUT_ROOT (same RUN_TAG).
#   2. Reads batch_manifest.csv to skip (scenario, mode, seed, run) already "ok".
#   3. Runs the missing baseline modes (pure schedulers + RSLAQ).
#   4. Optionally retries runs marked as failed in the manifest.
#   5. Runs Phase 2 (meta-heuristics) and Phase 3 (meta-evaluation).
#
# Usage
# -----
#   cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
#   bash examples/resume_campaign.sh
#
# Overrides (same names as run_all_scenarios.sh):
#   SCENARIOS="normal congestion" SEEDS="1 2 3" SIM_TIME=5 bash examples/resume_campaign.sh
#   RETRY_FAILED=0                    # do not retry previously failed runs
#   RUN_METAHEURISTICS=0               # skip Phase 2
#   RUN_META_EVALUATION=0              # skip Phase 3
#   MISSING_BASELINE_MODES="pure_rr pure_pf"  # override which baseline modes to (re)run

set -Eeuo pipefail

# ---------------------------------------------------------------------------
# Paths and run tag
# ---------------------------------------------------------------------------
REPO_ROOT="${REPO_ROOT:-/home/elioth/Documentos/artigo_jussi}"
NS3_DIR="${NS3_DIR:-${REPO_ROOT}/ns-3-dev}"
GYM_DIR="${GYM_DIR:-${REPO_ROOT}/ns-o-ran-gym}"

# Reuse the original run tag so all results land in the same campaign folder.
RUN_TAG="${RUN_TAG:-20260626_122326}"
OUTPUT_ROOT="${OUTPUT_ROOT:-${GYM_DIR}/results_controlled/heuristics_metaheuristics/${RUN_TAG}}"

# Phase 1 output root. The original run used "heuristics_ns3" (not the script
# default "baselines_ns3"), so we keep the same name to stay consistent.
BASELINE_OUTPUT_ROOT="${BASELINE_OUTPUT_ROOT:-${OUTPUT_ROOT}/heuristics_ns3}"
META_OUTPUT_ROOT="${META_OUTPUT_ROOT:-${OUTPUT_ROOT}/metaheuristics}"
META_EVAL_OUTPUT="${META_EVAL_OUTPUT:-${OUTPUT_ROOT}/meta_evaluation}"

RESULTS_DIR="${BASELINE_OUTPUT_ROOT}/results_rslaq_network_only"
LOG_DIR="${RESULTS_DIR}/_logs"
MANIFEST="${RESULTS_DIR}/batch_manifest.csv"

# ---------------------------------------------------------------------------
# Simulation parameters (must match the original run)
# ---------------------------------------------------------------------------
SIM_TIME="${SIM_TIME:-5}"
APP_START="${APP_START:-0.4}"
DRAIN_TIME_SEC="${DRAIN_TIME_SEC:-0.2}"
PERIOD_MS="${PERIOD_MS:-10}"
TX_POWER="${TX_POWER:-43}"
TDD_PATTERN="${TDD_PATTERN:-D|D|8D|4GB|4U|U|U}"
RLC_MODE="${RLC_MODE:-um}"

SCENARIOS="${SCENARIOS:-low_traffic normal congestion stressed insufficient_resources}"
SEEDS="${SEEDS:-1 2 3}"
RUNS="${RUNS:-1}"

# Modes that are MISSING from the original run (never executed).
# These are the pure schedulers + RSLAQ modes that the original
# run_all_scenarios.sh expected but did not produce.
MISSING_BASELINE_MODES="${MISSING_BASELINE_MODES:-pure_rr pure_bcqi pure_pf slice_weighted_pf slice_weighted_rr slice_weighted_bcqi psta_equal}"

# Retry runs that previously failed (status != ok in the manifest).
RETRY_FAILED="${RETRY_FAILED:-1}"

# Phase toggles
RUN_BASELINES="${RUN_BASELINES:-1}"
RUN_METAHEURISTICS="${RUN_METAHEURISTICS:-1}"
RUN_META_EVALUATION="${RUN_META_EVALUATION:-1}"
BUILD_NS3="${BUILD_NS3:-1}"

# Meta-heuristic parameters (same defaults as run_all_scenarios.sh)
META_METHOD="${META_METHOD:-all}"
META_ITERATIONS="${META_ITERATIONS:-4}"
META_POPULATION="${META_POPULATION:-6}"
META_MUTATION_STRENGTH="${META_MUTATION_STRENGTH:-0.12}"
META_INTRA_ALGO="${META_INTRA_ALGO:-PF}"
META_RANDOM_SEED="${META_RANDOM_SEED:-2026}"
META_SEED="${META_SEED:-1}"
META_RUN="${META_RUN:-1}"

# RSLAQ reference weights (for slice_weighted_* modes)
RSLAQ_REFERENCE_WEIGHTS="${RSLAQ_REFERENCE_WEIGHTS:-0.3333,0.4000,0.2667}"

mkdir -p "${LOG_DIR}"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
echo "============================================"
echo "Resume paper campaign (RUN_TAG=${RUN_TAG})"
echo "============================================"
echo "Output root         : ${OUTPUT_ROOT}"
echo "Baseline results    : ${RESULTS_DIR}"
echo "Metaheuristics root : ${META_OUTPUT_ROOT}"
echo "Meta-eval root      : ${META_EVAL_OUTPUT}"
echo "Scenarios           : ${SCENARIOS}"
echo "Seeds               : ${SEEDS}"
echo "Runs                : ${RUNS}"
echo "SIM_TIME            : ${SIM_TIME}"
echo "Missing baseline    : ${MISSING_BASELINE_MODES}"
echo "Retry failed runs   : ${RETRY_FAILED}"
echo "Run baselines       : ${RUN_BASELINES}"
echo "Run metaheuristics   : ${RUN_METAHEURISTICS}"
echo "Run meta-evaluation : ${RUN_META_EVALUATION}"
echo ""

# ---------------------------------------------------------------------------
# Build ns-3 (once)
# ---------------------------------------------------------------------------
if [[ "${BUILD_NS3}" == "1" ]]; then
    echo "[BUILD] Building rslaq-sim..."
    cd "${NS3_DIR}"
    ./ns3 build rslaq-sim
    echo "[BUILD] Done."
    echo ""
else
    echo "[BUILD] Skipping (BUILD_NS3=${BUILD_NS3})"
fi

# ---------------------------------------------------------------------------
# Helper: check if a (scenario, mode, seed, run) is already "ok" in manifest
# ---------------------------------------------------------------------------
is_completed() {
    local scenario="$1" mode="$2" seed="$3" run="$4"
    # Look for a line in the manifest with status "ok" for this combo.
    grep -F ",${scenario},${mode},${seed},${run},ok," "${MANIFEST}" 2>/dev/null | grep -q .
}

is_failed() {
    local scenario="$1" mode="$2" seed="$3" run="$4"
    # Look for a line with status != ok (run_failed or validation_failed).
    grep -F ",${scenario},${mode},${seed},${run}," "${MANIFEST}" 2>/dev/null \
        | grep -vE ",ok," | grep -q .
}

# ---------------------------------------------------------------------------
# Helper: validate outputs of a single run (mirrors run_all_scenarios.sh)
# ---------------------------------------------------------------------------
validate_outputs() {
    local result_dir="$1"
    local required=(
        "$result_dir/timeseries.csv"
        "$result_dir/slice_alloc.csv"
        "$result_dir/summary.csv"
        "$result_dir/metadata.json"
    )
    local path
    for path in "${required[@]}"; do
        if [[ ! -s "$path" ]]; then
            echo "missing_or_empty: $path"
            return 1
        fi
    done
    if ! head -n 1 "$result_dir/timeseries.csv" | grep -q "loss_pct_interval,buffer_bytes"; then
        echo "invalid timeseries.csv header"
        return 1
    fi
    if ! head -n 1 "$result_dir/slice_alloc.csv" | grep -q "rsh_real_pct"; then
        echo "invalid slice_alloc.csv header"
        return 1
    fi
    if ! head -n 1 "$result_dir/summary.csv" | grep -q "buffer_bytes_mean.*rsh_real_pct_mean"; then
        echo "invalid summary.csv header"
        return 1
    fi
    if ! grep -q '"baseline_mode"' "$result_dir/metadata.json"; then
        echo "invalid metadata.json"
        return 1
    fi
    echo "ok"
    return 0
}

# ---------------------------------------------------------------------------
# Helper: run a single ns-3 simulation
# ---------------------------------------------------------------------------
run_single() {
    local scenario="$1" mode="$2" seed="$3" run="$4"
    local result_dir="${RESULTS_DIR}/scenario=${scenario}/mode=${mode}/seed=${seed}_run=${run}"
    local log_file="${LOG_DIR}/${scenario}__${mode}__seed=${seed}_run=${run}.log"

    echo "  scenario=${scenario} mode=${mode} seed=${seed} run=${run}"

    cd "${NS3_DIR}"
    if ./ns3 run "scratch/rslaq/rslaq-sim \
        --scenario=${scenario} \
        --baselineMode=${mode} \
        --simTime=${SIM_TIME} \
        --appStart=${APP_START} \
        --drainTimeSec=${DRAIN_TIME_SEC} \
        --periodMs=${PERIOD_MS} \
        --seed=${seed} \
        --run=${run} \
        --txPower=${TX_POWER} \
        --tddPattern=${TDD_PATTERN} \
        --rlcMode=${RLC_MODE} \
        --outputDir=${BASELINE_OUTPUT_ROOT}" > "$log_file" 2>&1; then

        local validation_message
        validation_message="$(validate_outputs "$result_dir")"
        if [[ "$validation_message" == "ok" ]]; then
            echo "$scenario,$mode,$seed,$run,ok,$result_dir,$log_file,$validation_message" >> "$MANIFEST"
            echo "    -> OK"
        else
            echo "$scenario,$mode,$seed,$run,validation_failed,$result_dir,$log_file,$validation_message" >> "$MANIFEST"
            echo "    -> VALIDATION FAILED: $validation_message"
            tail -n 20 "$log_file"
        fi
    else
        echo "$scenario,$mode,$seed,$run,run_failed,$result_dir,$log_file,ns3_run_failed" >> "$MANIFEST"
        echo "    -> RUN FAILED (see $log_file)"
        tail -n 20 "$log_file"
    fi
    echo ""
}

# ---------------------------------------------------------------------------
# Phase 1: Complete missing baselines
# ---------------------------------------------------------------------------
if [[ "${RUN_BASELINES}" == "1" ]]; then
    echo "============================================"
    echo "Phase 1: Completing missing baselines"
    echo "============================================"

    # Ensure manifest exists (it should, but be safe).
    if [[ ! -f "$MANIFEST" ]]; then
        echo "scenario,baseline_mode,seed,run,status,result_dir,log_file,message" > "$MANIFEST"
    fi

    read -r -a SCENARIO_LIST <<< "$SCENARIOS"
    read -r -a MODE_LIST <<< "$MISSING_BASELINE_MODES"
    read -r -a SEED_LIST <<< "$SEEDS"
    read -r -a RUN_LIST <<< "$RUNS"

    total_missing=$(( ${#SCENARIO_LIST[@]} * ${#MODE_LIST[@]} * ${#SEED_LIST[@]} * ${#RUN_LIST[@]} ))
    count=0
    skipped=0
    failed_retry=0

    for scenario in "${SCENARIO_LIST[@]}"; do
        for mode in "${MODE_LIST[@]}"; do
            for seed in "${SEED_LIST[@]}"; do
                for run in "${RUN_LIST[@]}"; do
                    count=$((count + 1))
                    echo "[$count/$total_missing]"

                    if is_completed "$scenario" "$mode" "$seed" "$run"; then
                        echo "  SKIP (already ok): $scenario / $mode / seed=$seed run=$run"
                        skipped=$((skipped + 1))
                        echo ""
                        continue
                    fi

                    run_single "$scenario" "$mode" "$seed" "$run"
                done
            done
        done
    done

    echo "Phase 1 missing-baselines summary: ran $((count - skipped)) new, skipped ${skipped} already-ok."

    # Optionally retry previously failed runs (from the original campaign).
    if [[ "${RETRY_FAILED}" == "1" ]]; then
        echo ""
        echo "--------------------------------------------"
        echo "Retrying previously failed runs"
        echo "--------------------------------------------"

        # Collect all (scenario, mode, seed, run) that appear in the manifest
        # with status != ok.  We re-scan the whole manifest.
        # Use a temp file to avoid subshell issues.
        local_failed_list="${LOG_DIR}/.retry_list.$$"
        : > "$local_failed_list"
        awk -F, 'NR>1 && $5!="ok" {print $1" "$2" "$3" "$4}' "$MANIFEST" >> "$local_failed_list"

        retry_total=0
        retry_ok=0
        while read -r f_scenario f_mode f_seed f_run; do
            [[ -z "$f_scenario" ]] && continue
            retry_total=$((retry_total + 1))
            echo "[retry ${retry_total}] ${f_scenario} / ${f_mode} / seed=${f_seed} run=${f_run}"
            # Remove the old failed line so we don't get duplicates.
            grep -vF ",${f_scenario},${f_mode},${f_seed},${f_run}," "$MANIFEST" > "${MANIFEST}.tmp" || true
            mv "${MANIFEST}.tmp" "$MANIFEST"
            run_single "$f_scenario" "$f_mode" "$f_seed" "$f_run"
            if is_completed "$f_scenario" "$f_mode" "$f_seed" "$f_run"; then
                retry_ok=$((retry_ok + 1))
            fi
        done < "$local_failed_list"
        rm -f "$local_failed_list"
        echo "Retry summary: ${retry_ok}/${retry_total} recovered."
    fi

    echo ""
    echo "Phase 1 complete. Manifest: ${MANIFEST}"
else
    echo "[SKIP] Phase 1 (baselines) disabled by RUN_BASELINES=${RUN_BASELINES}"
fi

# ---------------------------------------------------------------------------
# Phase 2: Offline meta-heuristic search (PSO, GA, SA, hybrid)
# ---------------------------------------------------------------------------
if [[ "${RUN_METAHEURISTICS}" == "1" ]]; then
    echo ""
    echo "============================================"
    echo "Phase 2: Offline meta-heuristic search"
    echo "============================================"
    cd "${GYM_DIR}"
    echo "[META] method=${META_METHOD} scenarios=\"${SCENARIOS}\" seeds=\"${SEEDS}\""
    echo "[META] iterations=${META_ITERATIONS} population=${META_POPULATION} intra_algo=${META_INTRA_ALGO}"

    python3 examples/run_rslaq_metaheuristics.py \
        --method "${META_METHOD}" \
        --scenarios "${SCENARIOS}" \
        --seeds "${SEEDS}" \
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
        --output_root "${META_OUTPUT_ROOT}"
else
    echo "[SKIP] Phase 2 (meta-heuristics) disabled by RUN_METAHEURISTICS=${RUN_METAHEURISTICS}"
fi

# ---------------------------------------------------------------------------
# Phase 3: Meta-heuristic evaluation
# ---------------------------------------------------------------------------
if [[ "${RUN_META_EVALUATION}" == "1" ]]; then
    echo ""
    echo "============================================"
    echo "Phase 3: Meta-heuristic evaluation"
    echo "============================================"
    cd "${GYM_DIR}"

    python3 examples/run_meta_evaluation.py \
        --search_root "${META_OUTPUT_ROOT}" \
        --output_root "${META_EVAL_OUTPUT}" \
        --ns3_dir "${NS3_DIR}" \
        --intra_algo "${META_INTRA_ALGO}" \
        --sim_time "${SIM_TIME}" \
        --app_start "${APP_START}" \
        --drain_time "${DRAIN_TIME_SEC}" \
        --period_ms "${PERIOD_MS}" \
        --tx_power "${TX_POWER}" \
        --tdd_pattern "${TDD_PATTERN}" \
        --rlc_mode "${RLC_MODE}" \
        --run "${META_RUN}"
else
    echo "[SKIP] Phase 3 (meta-evaluation) disabled by RUN_META_EVALUATION=${RUN_META_EVALUATION}"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo "Resume campaign complete"
echo "============================================"
echo "Baselines output      : ${RESULTS_DIR}"
echo "Meta-heuristics output: ${META_OUTPUT_ROOT}"
echo "Meta-evaluation output: ${META_EVAL_OUTPUT}"
echo ""
echo "Final manifest status:"
if [[ -f "$MANIFEST" ]]; then
    total=$(tail -n +2 "$MANIFEST" | wc -l)
    ok=$(grep -c ",ok," "$MANIFEST" || true)
    failed=$(tail -n +2 "$MANIFEST" | grep -vc ",ok," || true)
    echo "  Total runs in manifest : ${total}"
    echo "  OK                    : ${ok}"
    echo "  Failed                : ${failed}"
fi
