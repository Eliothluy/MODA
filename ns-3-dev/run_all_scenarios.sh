#!/bin/bash
# Run all 5 RSLAQ traffic scenarios (standalone mode)
set -e

NS3_DIR="/home/elioth/Documentos/artigo_jussi/ns-3-dev"
RESULTS_DIR="/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_rslaq"
SCENARIOS=("low_traffic" "normal" "congestion" "stressed" "insufficient_resources")

# Simulation parameters
SIM_TIME=10
SEED_BASE=42

mkdir -p "$RESULTS_DIR"
cd "$NS3_DIR"

echo "Starting RSLAQ batch simulations at $(date)"

i=0
for scenario in "${SCENARIOS[@]}"; do
    SEED=$((SEED_BASE + i))
    echo "============================================="
    echo "Running scenario: $scenario (simTime=${SIM_TIME}s, seed=${SEED})"
    echo "============================================="
    ./ns3 run "scratch/rslaq/rslaq-sim" -- \
        --scenario=$scenario \
        --simTime=$SIM_TIME \
        --seed=$SEED \
        --outputDir=$RESULTS_DIR 2>&1 | grep -E "(RESULTS|Throughput|Avg delay|PDR|TX/RX pkts|CSV)"
    echo ""
    i=$((i + 1))
done

echo "All scenarios complete at $(date). Results in: $RESULTS_DIR"
