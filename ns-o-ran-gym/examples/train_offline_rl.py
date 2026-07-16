#!/usr/bin/env python3
"""Offline RL training for slice weight optimization.

Trains 3 neural policies from the consolidated Parquet dataset:
  1. DDQN-offline: Q-regression over discretized action space (66 simplex bins)
  2. SAC-offline:  Behavioral cloning of top-K candidates (actor MLP with softmax)
  3. PPO-offline:  Reward-weighted regression (policy gradient without Bellman)

The data does NOT form an MDP (no next_state), so these are trained as
contextual-bandit / supervised policies, not with TD-learning.

Usage:
    cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
    .venv-dashboard/bin/python examples/train_offline_rl.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

REPO_ROOT = Path("/home/elioth/Documentos/artigo_jussi")
DATA_ROOT = REPO_ROOT / "resultados_cenarios_finalizados_20260715"
PARQUET_PATH = DATA_ROOT / "offline_dataset.parquet"
MODELS_DIR = REPO_ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

# State features (input to all models)
STATE_COLS = [
    "num_ues_total", "num_ues_embb", "num_ues_urllc", "num_ues_mtc",
    "offered_load_embb", "offered_load_urllc", "offered_load_mtc",
    "pkt_size_embb", "pkt_size_urllc", "pkt_size_mtc",
    "is_low_traffic", "is_normal", "is_congestion", "is_stressed",
]
ACTION_COLS = ["w_embb", "w_urllc", "w_mtc"]
SCENARIOS = ["low_traffic", "normal", "congestion", "stressed"]

# Training config
EPOCHS = 300
LR = 1e-3
BATCH_SIZE = 128
TRAIN_SPLIT = 0.8  # 80% train, 20% test (by scenario-seed group)
SEED = 42
DEVICE = torch.device("cpu")


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------
def load_and_split(parquet_path: Path) -> tuple[dict, dict, pd.DataFrame]:
    """Load Parquet, normalize, split train/test by (scenario, seed) groups."""
    df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(df)} rows from {parquet_path.name}")

    # Normalize state features to [0,1] using min-max
    state_df = df[STATE_COLS].copy()
    state_min = state_df.min()
    state_max = state_df.max()
    state_range = (state_max - state_min).replace(0, 1)
    state_norm = (state_df - state_min) / state_range

    actions = df[ACTION_COLS].values.astype(np.float32)
    scores = df["score"].values.astype(np.float32)

    # Split by (scenario, seed) — ensures no leakage
    rng = np.random.RandomState(SEED)
    groups = df.groupby(["scenario", "seed"]).size().reset_index()[["scenario", "seed"]].values
    rng.shuffle(groups)
    n_train = int(len(groups) * TRAIN_SPLIT)
    train_groups = set(tuple(g) for g in groups[:n_train])

    group_keys = list(zip(df["scenario"], df["seed"]))
    train_mask = np.array([g in train_groups for g in group_keys])

    X_train = state_norm.values[train_mask].astype(np.float32)
    X_test = state_norm.values[~train_mask].astype(np.float32)
    A_train = actions[train_mask]
    A_test = actions[~train_mask]
    R_train = scores[train_mask]
    R_test = scores[~train_mask]

    train = {"X": X_train, "A": A_train, "R": R_train, "df": df[train_mask].reset_index(drop=True)}
    test = {"X": X_test, "A": A_test, "R": R_test, "df": df[~train_mask].reset_index(drop=True)}

    norm_params = {"min": state_min.to_dict(), "range": state_range.to_dict()}
    print(f"Train: {len(X_train)} rows | Test: {len(X_test)} rows")
    print(f"Train score: {R_train.mean():.2f} +/- {R_train.std():.2f}")
    print(f"Test  score: {R_test.mean():.2f} +/- {R_test.std():.2f}")
    return train, test, df


# ---------------------------------------------------------------------------
# Discretized action table for DDQN-offline
# ---------------------------------------------------------------------------
def build_simplex_actions(step: float = 0.1) -> np.ndarray:
    """Generate all weight vectors on the 3-simplex with given step."""
    actions = []
    n = int(round(1.0 / step))
    for i in range(n + 1):
        for j in range(n + 1 - i):
            k = n - i - j
            actions.append([i * step, j * step, k * step])
    return np.array(actions, dtype=np.float32)


def nearest_action_index(weights: np.ndarray, action_table: np.ndarray) -> int:
    """Find the index of the nearest discretized action."""
    dists = np.sum((action_table - weights) ** 2, axis=1)
    return int(np.argmin(dists))


# ---------------------------------------------------------------------------
# Model 1: DDQN-offline (Q-regression)
# ---------------------------------------------------------------------------
class QNet(nn.Module):
    def __init__(self, state_dim: int, n_actions: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(),
            nn.Linear(128, n_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def train_ddqn_offline(train: dict, test: dict, action_table: np.ndarray) -> dict:
    """Train Q-network by regression: Q(state, action_idx) -> score."""
    print("\n=== DDQN-offline (Q-regression) ===")
    n_actions = len(action_table)
    state_dim = train["X"].shape[1]

    # Map continuous actions to nearest discrete index
    train_aidx = np.array([nearest_action_index(a, action_table) for a in train["A"]])
    test_aidx = np.array([nearest_action_index(a, action_table) for a in test["A"]])

    model = QNet(state_dim, n_actions).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    X_t = torch.tensor(train["X"], device=DEVICE)
    aidx_t = torch.tensor(train_aidx, device=DEVICE, dtype=torch.long)
    R_t = torch.tensor(train["R"], device=DEVICE)

    best_test_score = -np.inf
    best_state = None
    loss_history = []

    for epoch in range(EPOCHS):
        model.train()
        # Predict Q for all actions, gather the ones matching the data
        q_all = model(X_t)
        q_pred = q_all.gather(1, aidx_t.unsqueeze(1)).squeeze(1)
        loss = F.mse_loss(q_pred, R_t)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        loss_history.append(loss.item())

        if (epoch + 1) % 50 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1}: loss={loss.item():.2f}")

    # Save
    model_path = MODELS_DIR / "ddqn_offline.pt"
    torch.save({"state_dict": model.state_dict(), "state_dim": state_dim,
                "n_actions": n_actions, "action_table": action_table,
                "state_cols": STATE_COLS, "loss_history": loss_history}, model_path)
    print(f"  Saved: {model_path}")

    # Final eval: predicted weights per scenario
    model.eval()
    with torch.no_grad():
        X_test_t = torch.tensor(test["X"], device=DEVICE)
        best_aidx = model(X_test_t).argmax(dim=1).cpu().numpy()
    pred_weights = action_table[best_aidx]

    return {"model_path": str(model_path), "pred_weights_test": pred_weights,
            "test_df": test["df"].reset_index(drop=True)}


# ---------------------------------------------------------------------------
# Model 2: SAC-offline (behavioral cloning of top-K)
# ---------------------------------------------------------------------------
class ActorNet(nn.Module):
    def __init__(self, state_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(),
            nn.Linear(128, 3),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.net(x)
        return F.softmax(logits, dim=-1)  # ensures simplex

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward(x)


def train_sac_offline(train: dict, test: dict) -> dict:
    """Behavioral cloning: train actor to predict weights of top-K candidates."""
    print("\n=== SAC-offline (behavioral cloning top-K) ===")
    state_dim = train["X"].shape[1]

    # Select top-K candidates per scenario (top 20% by score)
    df_train = train["df"].copy()
    top_k_list = []
    for sc in df_train["scenario"].unique():
        sub = df_train[df_train["scenario"] == sc]
        threshold = sub["score"].quantile(0.80)
        top_k_list.append(sub[sub["score"] >= threshold])
    top_df = pd.concat(top_k_list)
    print(f"  Top-K candidates: {len(top_df)} (from {len(df_train)} train rows)")

    X_top = train["X"][top_df.index.values]
    A_top = train["A"][top_df.index.values]

    X_t = torch.tensor(X_top, device=DEVICE)
    A_t = torch.tensor(A_top, device=DEVICE)

    model = ActorNet(state_dim).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    loss_history = []

    for epoch in range(EPOCHS):
        model.train()
        pred = model(X_t)
        loss = F.mse_loss(pred, A_t)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        loss_history.append(loss.item())
        if (epoch + 1) % 50 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1}: loss={loss.item():.6f}")

    model_path = MODELS_DIR / "sac_offline.pt"
    torch.save({"state_dict": model.state_dict(), "state_dim": state_dim,
                "state_cols": STATE_COLS, "loss_history": loss_history}, model_path)
    print(f"  Saved: {model_path}")

    model.eval()
    with torch.no_grad():
        X_test_t = torch.tensor(test["X"], device=DEVICE)
        pred_weights = model(X_test_t).cpu().numpy()

    return {"model_path": str(model_path), "pred_weights_test": pred_weights,
            "test_df": test["df"].reset_index(drop=True)}


# ---------------------------------------------------------------------------
# Model 3: PPO-offline (reward-weighted regression)
# ---------------------------------------------------------------------------
class PolicyNet(nn.Module):
    """Gaussian policy with softmax output for simplex constraint."""
    def __init__(self, state_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(),
        )
        self.mean_head = nn.Linear(128, 3)
        self.log_std = nn.Parameter(torch.zeros(3))

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.net(x)
        mean = self.mean_head(h)
        log_std = self.log_std.expand_as(mean).clamp(-3, 0)
        return mean, log_std

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        mean, _ = self.forward(x)
        return F.softmax(mean, dim=-1)


def train_ppo_offline(train: dict, test: dict) -> dict:
    """Reward-weighted regression: maximize sum(exp(reward/tau) * log_pi(a|s))."""
    print("\n=== PPO-offline (reward-weighted regression) ===")
    state_dim = train["X"].shape[1]

    X_t = torch.tensor(train["X"], device=DEVICE)
    A_t = torch.tensor(train["A"], device=DEVICE)
    R_t = torch.tensor(train["R"], device=DEVICE)

    # Normalize rewards to [0,1] for weighting
    R_min, R_max = R_t.min(), R_t.max()
    R_norm = (R_t - R_min) / (R_max - R_min + 1e-8)
    # Weights: exp(reward / tau) — temperature controls focus on high-reward
    tau = 0.1
    weights = torch.exp(R_norm / tau)
    weights = weights / weights.sum()

    model = PolicyNet(state_dim).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    loss_history = []

    n = len(X_t)
    for epoch in range(EPOCHS):
        model.train()
        mean, log_std = model(X_t)
        std = torch.exp(log_std)
        # Gaussian log-likelihood (pre-softmax, then project to simplex)
        # Use Dirichlet-like loss: treat softmax(mean) as concentration
        pred_weights = F.softmax(mean, dim=-1)
        # Weighted MSE toward observed actions (reward-weighted)
        mse = ((pred_weights - A_t) ** 2).sum(dim=1)
        loss = (weights * mse).mean()

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        loss_history.append(loss.item())
        if (epoch + 1) % 50 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1}: weighted_loss={loss.item():.6f}")

    model_path = MODELS_DIR / "ppo_offline.pt"
    torch.save({"state_dict": model.state_dict(), "state_dim": state_dim,
                "state_cols": STATE_COLS, "loss_history": loss_history}, model_path)
    print(f"  Saved: {model_path}")

    model.eval()
    with torch.no_grad():
        X_test_t = torch.tensor(test["X"], device=DEVICE)
        pred_weights = model.predict(X_test_t).cpu().numpy()

    return {"model_path": str(model_path), "pred_weights_test": pred_weights,
            "test_df": test["df"].reset_index(drop=True)}


# ---------------------------------------------------------------------------
# Evaluation helper
# ---------------------------------------------------------------------------
def evaluate_predictions(results: dict, df_full: pd.DataFrame) -> dict:
    """For each model, compute predicted weights per test scenario and compare
    the Q/score proxy to the best meta-heuristic score."""
    summary = {}
    test_df = results["test_df"]
    pred_w = results["pred_weights_test"]

    for sc in test_df["scenario"].unique():
        mask = test_df["scenario"].values == sc
        if mask.sum() == 0:
            continue
        # Predicted weights: average over test rows of this scenario
        avg_pred = pred_w[mask].mean(axis=0)
        # Best meta-heuristic score for this scenario (ground truth)
        best_meta = df_full[df_full["scenario"] == sc]["score"].max()
        # Mean predicted weights
        summary.setdefault(sc, {})["avg_pred_weights"] = avg_pred.tolist()
        summary[sc]["best_meta_score"] = float(best_meta)
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("Loading data...")
    train, test, df_full = load_and_split(PARQUET_PATH)
    action_table = build_simplex_actions(step=0.1)
    print(f"Discretized actions: {len(action_table)} bins")

    results_ddqn = train_ddqn_offline(train, test, action_table)
    results_sac = train_sac_offline(train, test)
    results_ppo = train_ppo_offline(train, test)

    # Evaluate
    print("\n" + "=" * 70)
    print("EVALUATION: predicted weights per scenario (test set)")
    print("=" * 70)
    all_metrics = {}
    for name, res in [("DDQN", results_ddqn), ("SAC", results_sac), ("PPO", results_ppo)]:
        print(f"\n--- {name} ---")
        summ = evaluate_predictions(res, df_full)
        all_metrics[name] = summ
        for sc in sorted(summ.keys()):
            w = summ[sc]["avg_pred_weights"]
            best = summ[sc]["best_meta_score"]
            print(f"  {sc:<18}: pred weights=[{w[0]:.3f}, {w[1]:.3f}, {w[2]:.3f}] | best meta score={best:.2f}")

    # Save metrics
    metrics_path = MODELS_DIR / "metrics.json"
    with metrics_path.open("w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\nMetrics saved: {metrics_path}")


if __name__ == "__main__":
    main()
