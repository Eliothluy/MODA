#!/bin/bash
source /home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/venv/bin/activate
cd /home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym

RESULTS="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results"
EXAMPLES="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/examples"

mkdir -p "$RESULTS"

echo "[1/3] OPT baseline starting at $(date)" >> "$RESULTS/training.log"
python3 "$EXAMPLES/rslaq_train_opt.py" --scenario all --output "$RESULTS" --episodes 20 --max_steps 150 >> "$RESULTS/training.log" 2>&1
echo "[1/3] OPT baseline done at $(date)" >> "$RESULTS/training.log"

echo "[2/3] DDQN training starting at $(date)" >> "$RESULTS/training.log"
python3 "$EXAMPLES/rslaq_train_ddqn.py" --scenario all --output "$RESULTS" --episodes 20 --max_steps 150 >> "$RESULTS/training.log" 2>&1
echo "[2/3] DDQN training done at $(date)" >> "$RESULTS/training.log"

echo "[3/3] SAC training starting at $(date)" >> "$RESULTS/training.log"
python3 "$EXAMPLES/rslaq_train_sac.py" --scenario all --output "$RESULTS" --episodes 20 --max_steps 150 >> "$RESULTS/training.log" 2>&1
echo "[3/3] SAC training done at $(date)" >> "$RESULTS/training.log"

echo "All training complete at $(date)" >> "$RESULTS/training.log"
