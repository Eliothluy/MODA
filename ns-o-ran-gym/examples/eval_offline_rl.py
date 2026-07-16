#!/usr/bin/env python3
"""Evaluate trained offline RL models against meta-heuristic ground truth.

Loads the 3 trained models (DDQN, SAC, PPO) and, for each scenario, predicts
optimal weights and compares them to:
  - Best meta-heuristic candidate (ground truth)
  - Fixed RSLAQ weights [0.33, 0.40, 0.27] (baseline)
  - Equal weights [0.33, 0.33, 0.33]

Generates a comparison table and a summary figure.

Usage:
    cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
    .venv-dashboard/bin/python examples/eval_offline_rl.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

REPO_ROOT = Path("/home/elioth/Documentos/artigo_jussi")
DATA_ROOT = REPO_ROOT / "resultados_cenarios_finalizados_20260715"
MODELS_DIR = REPO_ROOT / "models"
FIG_DIR = REPO_ROOT / "figuras_overleaf"

STATE_COLS = [
    "num_ues_total", "num_ues_embb", "num_ues_urllc", "num_ues_mtc",
    "offered_load_embb", "offered_load_urllc", "offered_load_mtc",
    "pkt_size_embb", "pkt_size_urllc", "pkt_size_mtc",
    "is_low_traffic", "is_normal", "is_congestion", "is_stressed",
]
SCENARIOS = ["low_traffic", "normal", "congestion", "stressed"]
SCENARIO_LABELS = {"low_traffic": "Low Traffic", "normal": "Normal",
                    "congestion": "Congestion", "stressed": "Stressed"}
DEVICE = torch.device("cpu")


# --- model architectures (must match train_offline_rl.py) ---
class QNet(torch.nn.Module):
    def __init__(self, state_dim, n_actions):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(state_dim, 128), torch.nn.ReLU(),
            torch.nn.Linear(128, 128), torch.nn.ReLU(),
            torch.nn.Linear(128, n_actions),
        )
    def forward(self, x):
        return self.net(x)


class ActorNet(torch.nn.Module):
    def __init__(self, state_dim):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(state_dim, 128), torch.nn.ReLU(),
            torch.nn.Linear(128, 128), torch.nn.ReLU(),
            torch.nn.Linear(128, 3),
        )
    def forward(self, x):
        return F.softmax(self.net(x), dim=-1)


class PolicyNet(torch.nn.Module):
    def __init__(self, state_dim):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(state_dim, 128), torch.nn.ReLU(),
            torch.nn.Linear(128, 128), torch.nn.ReLU(),
        )
        self.mean_head = torch.nn.Linear(128, 3)
        self.log_std = torch.nn.Parameter(torch.zeros(3))
    def forward(self, x):
        h = self.net(x)
        return F.softmax(self.mean_head(h), dim=-1)


def load_model(path: Path, model_type: str):
    ckpt = torch.load(path, map_location=DEVICE, weights_only=False)
    state_dim = ckpt["state_dim"]
    if model_type == "ddqn":
        model = QNet(state_dim, ckpt["n_actions"])
        model.load_state_dict(ckpt["state_dict"])
        return model, ckpt.get("action_table")
    elif model_type == "sac":
        model = ActorNet(state_dim)
        model.load_state_dict(ckpt["state_dict"])
        return model, None
    elif model_type == "ppo":
        model = PolicyNet(state_dim)
        model.load_state_dict(ckpt["state_dict"])
        return model, None
    raise ValueError(f"Unknown model type: {model_type}")


def predict_weights(model, model_type: str, state: np.ndarray, action_table=None) -> np.ndarray:
    """Predict weights for a batch of states."""
    model.eval()
    x = torch.tensor(state, dtype=torch.float32, device=DEVICE)
    with torch.no_grad():
        if model_type == "ddqn":
            q = model(x)
            idx = q.argmax(dim=1).cpu().numpy()
            return action_table[idx]
        elif model_type == "sac":
            return model(x).cpu().numpy()
        elif model_type == "ppo":
            return model(x).cpu().numpy()


def build_state_for_scenario(scenario: str, df: pd.DataFrame, norm_params: dict) -> np.ndarray:
    """Build a normalized state vector for a given scenario (averaged)."""
    sub = df[df["scenario"] == scenario]
    if sub.empty:
        return None
    raw = sub[STATE_COLS].mean().values.astype(np.float32)
    # Normalize using stored params
    mins = np.array([norm_params["min"][c] for c in STATE_COLS])
    ranges = np.array([norm_params["range"][c] for c in STATE_COLS])
    norm = (raw - mins) / ranges
    return norm.reshape(1, -1)


def find_nearest_score(weights: np.ndarray, df: pd.DataFrame, scenario: str) -> float:
    """Find the score of the nearest candidate in the dataset (proxy evaluation)."""
    sub = df[df["scenario"] == scenario]
    if sub.empty:
        return float("nan")
    w_cols = ["w_embb", "w_urllc", "w_mtc"]
    dist = ((sub[w_cols].values - weights) ** 2).sum(axis=1)
    nearest_idx = dist.argmin()
    return float(sub.iloc[nearest_idx]["score"])


def main() -> None:
    sys.path.insert(0, str(REPO_ROOT / "ns-o-ran-gym/src"))
    df = pd.read_parquet(DATA_ROOT / "offline_dataset.parquet")

    # Compute normalization params from full dataset
    state_df = df[STATE_COLS]
    norm_params = {
        "min": state_df.min().to_dict(),
        "range": (state_df.max() - state_df.min()).replace(0, 1).to_dict(),
    }

    # Load models
    models = {}
    for name, mtype, path_key in [("DDQN", "ddqn", "ddqn_offline.pt"),
                                   ("SAC", "sac", "sac_offline.pt"),
                                   ("PPO", "ppo", "ppo_offline.pt")]:
        path = MODELS_DIR / path_key
        if path.exists():
            model, atab = load_model(path, mtype)
            models[name] = (model, mtype, atab)
            print(f"Loaded {name} from {path}")

    # Fixed baselines
    BASELINES = {
        "RSLAQ fixed [0.33,0.40,0.27]": np.array([0.3333, 0.4000, 0.2667]),
        "Equal [0.33,0.33,0.33]": np.array([0.3333, 0.3333, 0.3333]),
    }

    # Evaluate
    print("\n" + "=" * 90)
    print("COMPARISON: predicted weights -> nearest dataset score")
    print("=" * 90)
    print(f"{'Scenario':<16} {'Method':<28} {'w_eMBB':>7} {'w_URLLC':>8} {'w_MTC':>7} {'Proxy score':>12}")
    print("-" * 90)

    results = []
    for sc in SCENARIOS:
        state = build_state_for_scenario(sc, df, norm_params)
        if state is None:
            continue
        best_meta = df[df["scenario"] == sc]["score"].max()

        # Meta-heuristic ground truth
        best_row = df[df["scenario"] == sc].nlargest(1, "score").iloc[0]
        print(f"{sc:<16} {'Best meta-heuristic':<28} {best_row['w_embb']:>7.3f} {best_row['w_urllc']:>8.3f} {best_row['w_mtc']:>7.3f} {best_meta:>12.2f}")
        results.append({"scenario": sc, "method": "Best meta-heur.", "w_embb": best_row["w_embb"],
                        "w_urllc": best_row["w_urllc"], "w_mtc": best_row["w_mtc"], "score": best_meta})

        # Fixed baselines
        for bname, bw in BASELINES.items():
            bscore = find_nearest_score(bw, df, sc)
            print(f"{'':<16} {bname:<28} {bw[0]:>7.3f} {bw[1]:>8.3f} {bw[2]:>7.3f} {bscore:>12.2f}")
            results.append({"scenario": sc, "method": bname, "w_embb": bw[0],
                            "w_urllc": bw[1], "w_mtc": bw[2], "score": bscore})

        # Trained models
        for mname, (model, mtype, atab) in models.items():
            pred_w = predict_weights(model, mtype, state, atab)[0]
            pscore = find_nearest_score(pred_w, df, sc)
            print(f"{'':<16} {mname+'-offline':<28} {pred_w[0]:>7.3f} {pred_w[1]:>8.3f} {pred_w[2]:>7.3f} {pscore:>12.2f}")
            results.append({"scenario": sc, "method": f"{mname}-offline", "w_embb": pred_w[0],
                            "w_urllc": pred_w[1], "w_mtc": pred_w[2], "score": pscore})
        print()

    # Save results
    res_df = pd.DataFrame(results)
    res_df.to_csv(MODELS_DIR / "evaluation_comparison.csv", index=False)
    print(f"Saved: {MODELS_DIR / 'evaluation_comparison.csv'}")

    # Generate figure: bar chart of scores per scenario
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    methods = res_df["method"].unique()
    x = np.arange(len(SCENARIOS))
    width = 0.13
    colors = {"Best meta-heur.": "#2ca02c", "RSLAQ fixed [0.33,0.40,0.27]": "#7f7f7f",
              "Equal [0.33,0.33,0.33]": "#bcbd22", "DDQN-offline": "#1f77b4",
              "SAC-offline": "#d62728", "PPO-offline": "#9467bd"}
    for i, method in enumerate(methods):
        vals = []
        for sc in SCENARIOS:
            row = res_df[(res_df["scenario"] == sc) & (res_df["method"] == method)]
            vals.append(row["score"].values[0] if len(row) > 0 else 0)
        ax.bar(x + i * width, vals, width, label=method,
               color=colors.get(method, "gray"), alpha=0.85, edgecolor="black", linewidth=0.5)
    ax.set_xticks(x + width * (len(methods) / 2 - 0.5))
    ax.set_xticklabels([SCENARIO_LABELS[sc] for sc in SCENARIOS])
    ax.set_ylabel("Proxy score (nearest dataset candidate)")
    ax.set_title("Offline DRL vs. meta-heuristics vs. fixed baselines")
    ax.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    fig_path = FIG_DIR / "fig15_offline_drl_comparison.png"
    fig.savefig(fig_path, dpi=300, bbox_inches="tight")
    print(f"Figure saved: {fig_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
