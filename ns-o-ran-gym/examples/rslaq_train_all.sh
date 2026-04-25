#!/bin/bash
set -e

RESULTS="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results"
EXAMPLES="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/examples"
VENV="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/venv"

source "$VENV/bin/activate"

echo "============================================"
echo "RSLAQ Training Pipeline with NS-3"
echo "============================================"
echo "Results will be saved to: $RESULTS"
echo ""

mkdir -p "$RESULTS"

echo "[1/3] Running OPT baseline (fixed heuristic)..."
echo "  20 episodes x 150 steps x 5 scenarios"
python3 "$EXAMPLES/rslaq_train_opt.py" --scenario all --output "$RESULTS" --episodes 20 --max_steps 150

echo ""
echo "[2/3] Running DDQN (RSLAQ) training..."
echo "  20 episodes x 150 steps x 5 scenarios"
python3 "$EXAMPLES/rslaq_train_ddqn.py" --scenario all --output "$RESULTS" --episodes 20 --max_steps 150

echo ""
echo "[3/3] Running SAC training..."
echo "  20 episodes x 150 steps x 5 scenarios"
python3 "$EXAMPLES/rslaq_train_sac.py" --scenario all --output "$RESULTS" --episodes 20 --max_steps 150

echo ""
echo "============================================"
echo "Training complete! Results in $RESULTS"
echo "============================================"
