#!/usr/bin/env bash
# Run every RSLAQ network-only baseline over every traffic scenario.
#
# Defaults run one seed/run for a fast metric validation matrix:
#   5 scenarios x 10 baseline modes = 50 simulations.
#
# Override examples:
#   SIM_TIME=20 SEEDS="1 2 3" RUNS="1 2 3" ./run_all_scenarios.sh
#   BASELINE_MODES="pure_pf slice_weighted_pf psta_equal" ./run_all_scenarios.sh

set -Eeuo pipefail

SCENARIOS_INPUT="${SCENARIOS:-}"
BASELINE_MODES_INPUT="${BASELINE_MODES:-}"

NS3_DIR="${NS3_DIR:-/home/elioth/Documentos/artigo_jussi/ns-3-dev}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$NS3_DIR}"
RESULTS_DIR="$OUTPUT_ROOT/results_rslaq_network_only"
LOG_DIR="$RESULTS_DIR/_logs"
MANIFEST="$RESULTS_DIR/batch_manifest.csv"

SIM_TIME="${SIM_TIME:-10}"
APP_START="${APP_START:-0.4}"
DRAIN_TIME_SEC="${DRAIN_TIME_SEC:-0.2}"
PERIOD_MS="${PERIOD_MS:-10}"
TX_POWER="${TX_POWER:-43}"
TDD_PATTERN="${TDD_PATTERN:-D|D|8D|4GB|4U|U|U}"
RLC_MODE="${RLC_MODE:-um}"
SEEDS="${SEEDS:-1}"
RUNS="${RUNS:-1}"
STOP_ON_FAILURE="${STOP_ON_FAILURE:-0}"
BUILD_NS3="${BUILD_NS3:-1}"

SCENARIOS=(
    low_traffic
    normal
    congestion
    stressed
    insufficient_resources
)

BASELINE_MODES=(
    pure_rr
    pure_pf
    pure_bcqi
    slice_rr
    slice_pf
    slice_bcqi
    slice_weighted_pf
    slice_weighted_rr
    slice_weighted_bcqi
    psta_equal
)

if [[ -n "$SCENARIOS_INPUT" ]]; then
    read -r -a SCENARIOS <<< "$SCENARIOS_INPUT"
fi

if [[ -n "$BASELINE_MODES_INPUT" ]]; then
    read -r -a BASELINE_MODES <<< "$BASELINE_MODES_INPUT"
fi

read -r -a SEED_LIST <<< "$SEEDS"
read -r -a RUN_LIST <<< "$RUNS"

mkdir -p "$LOG_DIR"
cd "$NS3_DIR"

echo "Starting RSLAQ baseline matrix at $(date)"
echo "Results root : $RESULTS_DIR"
echo "Logs         : $LOG_DIR"
echo "Scenarios    : ${SCENARIOS[*]}"
echo "Baselines    : ${BASELINE_MODES[*]}"
echo "Seeds        : ${SEED_LIST[*]}"
echo "Runs         : ${RUN_LIST[*]}"
echo "Sim config   : simTime=${SIM_TIME}s appStart=${APP_START}s drain=${DRAIN_TIME_SEC}s period=${PERIOD_MS}ms rlcMode=${RLC_MODE}"
echo ""

if [[ "$BUILD_NS3" == "1" ]]; then
    echo "Building rslaq-sim..."
    ./ns3 build rslaq-sim
else
    echo "Skipping rslaq-sim build because BUILD_NS3=$BUILD_NS3"
fi

echo "scenario,baseline_mode,seed,run,status,result_dir,log_file,message" > "$MANIFEST"

total=$(( ${#SCENARIOS[@]} * ${#BASELINE_MODES[@]} * ${#SEED_LIST[@]} * ${#RUN_LIST[@]} ))
index=0
failures=0

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

for scenario in "${SCENARIOS[@]}"; do
    for baseline_mode in "${BASELINE_MODES[@]}"; do
        for seed in "${SEED_LIST[@]}"; do
            for run in "${RUN_LIST[@]}"; do
                index=$((index + 1))
                result_dir="$RESULTS_DIR/scenario=${scenario}/mode=${baseline_mode}/seed=${seed}_run=${run}"
                log_file="$LOG_DIR/${scenario}__${baseline_mode}__seed=${seed}_run=${run}.log"

                echo "[$index/$total] scenario=$scenario mode=$baseline_mode seed=$seed run=$run"

                if ./ns3 run "scratch/rslaq/rslaq-sim \
                    --scenario=${scenario} \
                    --baselineMode=${baseline_mode} \
                    --simTime=${SIM_TIME} \
                    --appStart=${APP_START} \
                    --drainTimeSec=${DRAIN_TIME_SEC} \
                    --periodMs=${PERIOD_MS} \
                    --seed=${seed} \
                    --run=${run} \
                    --txPower=${TX_POWER} \
                    --tddPattern=${TDD_PATTERN} \
                    --rlcMode=${RLC_MODE} \
                    --outputDir=${OUTPUT_ROOT}" > "$log_file" 2>&1; then

                    validation_message="$(validate_outputs "$result_dir")"
                    if [[ "$validation_message" == "ok" ]]; then
                        echo "$scenario,$baseline_mode,$seed,$run,ok,$result_dir,$log_file,$validation_message" >> "$MANIFEST"
                        grep -E "(RESULTS|Throughput|Avg delay|PDR|CSV outputs|WARNING:)" "$log_file" || true
                    else
                        failures=$((failures + 1))
                        echo "$scenario,$baseline_mode,$seed,$run,validation_failed,$result_dir,$log_file,$validation_message" >> "$MANIFEST"
                        echo "VALIDATION FAILED: $validation_message"
                        tail -n 40 "$log_file"
                        if [[ "$STOP_ON_FAILURE" == "1" ]]; then
                            exit 1
                        fi
                    fi
                else
                    failures=$((failures + 1))
                    echo "$scenario,$baseline_mode,$seed,$run,run_failed,$result_dir,$log_file,ns3_run_failed" >> "$MANIFEST"
                    echo "RUN FAILED. Last log lines:"
                    tail -n 60 "$log_file"
                    if [[ "$STOP_ON_FAILURE" == "1" ]]; then
                        exit 1
                    fi
                fi

                echo ""
            done
        done
    done
done

echo "Batch complete at $(date)"
echo "Manifest: $MANIFEST"
echo "Results : $RESULTS_DIR"

if (( failures > 0 )); then
    echo "Completed with $failures failed run(s) or validation error(s)."
    exit 1
fi

echo "All runs completed and metric files validated."
