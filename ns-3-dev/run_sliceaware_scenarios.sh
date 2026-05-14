#!/bin/bash
# Run all GreenRAN scenarios for slice-aware-sim
# Results are saved in separate folders per scenario
set -e

NS3_DIR="/home/elioth/Documentos/artigo_jussi/ns-3-dev"
RESULTS_DIR="/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_sliceaware_scenarios"
SCENARIOS=("greenran_low" "greenran_normal" "greenran_video_heavy" "greenran_congestion" "greenran_night_energy" "greenran_balanced")

SIM_TIME=15
SEED_BASE=42

mkdir -p "$RESULTS_DIR"
cd "$NS3_DIR"
./ns3 build GreenRan-slice

LOG_FILE="$RESULTS_DIR/run_$(date +%Y%m%d_%H%M%S).log"
echo "Starting GreenRAN batch simulations at $(date)" | tee "$LOG_FILE"

SEED=$SEED_BASE
for scenario in "${SCENARIOS[@]}"; do
    OUTDIR="$RESULTS_DIR/$scenario"
    SCENARIO_LOG="$OUTDIR/${scenario}_console.log"

    echo "" | tee -a "$LOG_FILE"
    echo "=============================================" | tee -a "$LOG_FILE"
    echo "Running scenario: $scenario (simTime=${SIM_TIME}s, seed=${SEED})" | tee -a "$LOG_FILE"
    echo "Results dir: $OUTDIR" | tee -a "$LOG_FILE"
    echo "=============================================" | tee -a "$LOG_FILE"

    mkdir -p "$OUTDIR"

    ./ns3 run "scratch/our_paper/GreenRan-slice" -- \
        --scenario="$scenario" \
        --simTime=$SIM_TIME \
        --seed=$SEED \
        --EnableUlSliceScheduling=true \
        --enableDrlControl=false \
        --enablePosixSync=false \
        --outputDir="$OUTDIR" 2>&1 | tee "$SCENARIO_LOG"

    if [ $? -eq 0 ]; then
        echo "[OK] $scenario completed successfully." | tee -a "$LOG_FILE"
    else
        echo "[FAIL] $scenario failed! Check $SCENARIO_LOG" | tee -a "$LOG_FILE"
    fi
done

echo "" | tee -a "$LOG_FILE"
echo "All scenarios complete at $(date)." | tee -a "$LOG_FILE"
echo "Results in: $RESULTS_DIR" | tee -a "$LOG_FILE"
