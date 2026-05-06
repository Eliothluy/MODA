#!/bin/bash
# Run all GreenRAN scenarios for slice-aware-sim
# Results are saved in separate folders per scenario
set -e

NS3_DIR="/home/elioth/Documentos/artigo_jussi/ns-3-dev"
RESULTS_DIR="/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_greenran"
SCENARIOS=("greenran_low" "greenran_normal" "greenran_video_heavy" "greenran_mmtc_massive" "greenran_congestion" "greenran_night_energy")

SIM_TIME=10
SEED_BASE=42
WEIGHTS="0.8,0.2"

mkdir -p "$RESULTS_DIR"
cd "$NS3_DIR"

echo "Starting GreenRAN batch simulations at $(date)"

i=0
for scenario in "${SCENARIOS[@]}"; do
    SEED=$((SEED_BASE + i))
    OUTDIR="$RESULTS_DIR/$scenario"

    echo "============================================="
    echo "Running scenario: $scenario (simTime=${SIM_TIME}s, seed=${SEED})"
    echo "Results dir: $OUTDIR"
    echo "============================================="

    mkdir -p "$OUTDIR"
    ./ns3 run "scratch/our_paper/slice-aware-sim" -- \
        --scenario=$scenario \
        --simTime=$SIM_TIME \
        --seed=$SEED \
        --weights=$WEIGHTS \
        --EnableUlSliceScheduling=true \
        --outputDir="$OUTDIR" 2>&1 | grep -E "(GreenRAN|Throughput|Avg delay|PDR|TX/RX pkts|CSV|IPC|WARNING)"

    echo ""
    i=$((i + 1))
done

echo "All GreenRAN scenarios complete at $(date). Results in: $RESULTS_DIR"