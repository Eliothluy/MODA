#!/bin/bash
# Run all 5 RSLAQ traffic scenarios (standalone mode)
set -e

NS3_BIN="/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/build/scratch/ns3.46-rslaq-simulation-mac-slicing-default"
NS3_DIR="/home/eliothluy/Documentos/artigo_jussi/ns-3-dev"
RESULTS_DIR="/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/results_rslaq"
SCENARIOS=("low_traffic" "normal" "congestion" "stressed" "insufficient_resources")

# Simulation parameters
SIM_TIME=10
SEED_BASE=42

mkdir -p "$RESULTS_DIR"

i=0
for scenario in "${SCENARIOS[@]}"; do
    SEED=$((SEED_BASE + i))
    echo "============================================="
    echo "Running scenario: $scenario (simTime=${SIM_TIME}s, seed=${SEED})"
    echo "============================================="
    "$NS3_DIR/ns3" run "scratch/rslaq-simulation-mac-slicing" -- --scenario=$scenario --simTime=$SIM_TIME --seed=$SEED --outputDir=$RESULTS_DIR 2>&1 | grep -E "(RESULTS|Throughput|Avg delay|PDR / PLR|TX / RX pkts|CSV)"
    echo ""
    i=$((i + 1))
done
echo "All scenarios complete. Results in: $RESULTS_DIR"
