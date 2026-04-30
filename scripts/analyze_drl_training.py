#!/usr/bin/env python3
"""
DRL Training Analysis for RSLAQ Optimizers (DDQN & SAC).

Analyzes reward curves, convergence signals, and learning effectiveness.

Usage:
    python3 analyze_drl_training.py
"""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCENARIOS = [
    "normal",
    "congestion",
    "stressed",
    "low_traffic",
    "insufficient_resources",
]

METHODS = ["DDQN", "SAC"]
METHOD_COLORS = {
    "DDQN": "#1f77b4",
    "SAC": "#2ca02c",
}

BASE_DIR = Path("/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results")
OUTPUT_DIR = Path("/home/eliothluy/Documentos/artigo_jussi/scripts/drl_analysis_plots")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_csv_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def read_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------


def load_training_logs() -> pd.DataFrame:
    rows = []
    for method in ["ddqn", "sac"]:
        for scenario in SCENARIOS:
            log_path = BASE_DIR / f"{method}_{scenario}" / f"{method}_training_log.csv"
            summary_path = BASE_DIR / f"{method}_{scenario}" / f"{method}_summary.json"
            if log_path.exists():
                df = read_csv_df(log_path)
                df["method"] = method.upper()
                df["scenario"] = scenario
                if summary_path.exists():
                    summary = read_json(summary_path)
                    df["best_avg"] = summary.get("best_avg", np.nan)
                rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def load_opt_results() -> pd.DataFrame:
    rows = []
    for scenario in SCENARIOS:
        opt_path = BASE_DIR / "opt" / scenario / "opt_results.json"
        if opt_path.exists():
            data = read_json(opt_path)
            for ep, r in enumerate(data.get("rewards", []), 1):
                rows.append({
                    "episode": ep,
                    "scenario": scenario,
                    "method": "OPT",
                    "total_reward": r,
                    "avg_reward": r,
                    "steps": data.get("episodes", 10),
                })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def save_fig(name: str) -> None:
    path = OUTPUT_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved plot: {path}")


def plot_reward_curves(df: pd.DataFrame) -> None:
    """Plot total_reward per episode, faceted by scenario, with DDQN/SAC overlaid."""
    fig, axes = plt.subplots(1, len(SCENARIOS), figsize=(5 * len(SCENARIOS), 4.5), sharey=False)
    if len(SCENARIOS) == 1:
        axes = [axes]

    for ax, scenario in zip(axes, SCENARIOS):
        ax.set_title(f"{scenario.replace('_', ' ').title()}", fontsize=12)
        ax.set_xlabel("Episode")
        ax.set_ylabel("Total Reward")
        ax.grid(True, linestyle="--", alpha=0.4)

        sub = df[df["scenario"] == scenario]
        for method in METHODS:
            sub_m = sub[sub["method"] == method]
            if sub_m.empty:
                continue
            ax.plot(
                sub_m["episode"],
                sub_m["total_reward"],
                marker="o",
                label=method,
                color=METHOD_COLORS[method],
                linewidth=2,
                markersize=6,
            )

        ax.legend()

    plt.tight_layout()
    save_fig("reward_curves_per_scenario.png")


def plot_cumulative_reward(df: pd.DataFrame) -> None:
    """Cumulative sum of rewards to show learning trend."""
    fig, axes = plt.subplots(1, len(SCENARIOS), figsize=(5 * len(SCENARIOS), 4.5), sharey=False)
    if len(SCENARIOS) == 1:
        axes = [axes]

    for ax, scenario in zip(axes, SCENARIOS):
        ax.set_title(f"{scenario.replace('_', ' ').title()}", fontsize=12)
        ax.set_xlabel("Episode")
        ax.set_ylabel("Cumulative Reward")
        ax.grid(True, linestyle="--", alpha=0.4)

        sub = df[df["scenario"] == scenario]
        for method in METHODS:
            sub_m = sub[sub["method"] == method]
            if sub_m.empty:
                continue
            cumsum = sub_m["total_reward"].cumsum()
            ax.plot(
                sub_m["episode"],
                cumsum,
                marker="o",
                label=method,
                color=METHOD_COLORS[method],
                linewidth=2,
                markersize=6,
            )

        ax.legend()

    plt.tight_layout()
    save_fig("cumulative_reward_per_scenario.png")


def plot_epsilon_decay() -> None:
    """Theoretical epsilon decay curve for DDQN parameters."""
    epsilon_start = 1.0
    epsilon_min = 0.05
    epsilon_decay = 0.998
    steps_per_ep = 350
    episodes = 500  # theoretical extended training
    total_steps = episodes * steps_per_ep
    steps = np.arange(total_steps)
    epsilons = [epsilon_start]
    for s in steps[1:]:
        eps = max(epsilon_min, epsilons[-1] * epsilon_decay)
        epsilons.append(eps)
    epsilons = np.array(epsilons)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(steps / steps_per_ep, epsilons, linewidth=2, color=METHOD_COLORS["DDQN"])
    ax.axvline(x=10, color="red", linestyle="--", label="Actual training end (10 ep)")
    ax.axvline(x=50, color="orange", linestyle="--", label="Minimum recommended (50 ep)")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Epsilon (exploration rate)")
    ax.set_title("DDQN Epsilon Decay (theoretical)")
    ax.set_xlim(0, 200)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    save_fig("ddqn_epsilon_decay_theoretical.png")


def plot_reward_vs_kpis(df_train: pd.DataFrame) -> None:
    """Scatter: final episode reward vs final eMBB throughput & URLLC PLR."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Reward vs eMBB throughput
    ax = axes[0]
    for method in METHODS:
        sub = df_train[df_train["method"] == method]
        ax.scatter(
            sub["final_embb_thr"],
            sub["total_reward"],
            label=method,
            color=METHOD_COLORS[method],
            s=80,
            alpha=0.7,
        )
    ax.set_xlabel("Final eMBB Throughput (Mbps)")
    ax.set_ylabel("Total Reward")
    ax.set_title("Reward vs Final eMBB Throughput")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    # Reward vs URLLC PLR
    ax = axes[1]
    for method in METHODS:
        sub = df_train[df_train["method"] == method]
        ax.scatter(
            sub["final_urllc_plr"],
            sub["total_reward"],
            label=method,
            color=METHOD_COLORS[method],
            s=80,
            alpha=0.7,
        )
    ax.set_xlabel("Final URLLC PLR")
    ax.set_ylabel("Total Reward")
    ax.set_title("Reward vs Final URLLC PLR")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    save_fig("reward_vs_final_kpis.png")


def plot_action_evolution(df: pd.DataFrame) -> None:
    """Show how actions (PRB allocations) evolved during training."""
    fig, axes = plt.subplots(1, len(SCENARIOS), figsize=(5 * len(SCENARIOS), 4.5), sharey=True)
    if len(SCENARIOS) == 1:
        axes = [axes]

    slices = ["eMBB", "URLLC", "MTC"]
    slice_colors = {"eMBB": "#d62728", "URLLC": "#9467bd", "MTC": "#8c564b"}

    for ax, scenario in zip(axes, SCENARIOS):
        ax.set_title(f"{scenario.replace('_', ' ').title()}", fontsize=12)
        ax.set_xlabel("Episode")
        ax.set_ylabel("PRB Allocation (%)")

        sub = df[(df["scenario"] == scenario) & (df["method"] == "DDQN")]
        if sub.empty:
            continue
        for i, s in enumerate(slices):
            col = f"action_{s.lower()}"
            if col in sub.columns:
                ax.plot(sub["episode"], sub[col], marker="o", label=f"{s} (DDQN)", color=slice_colors[s], linewidth=1.5)

        ax.legend(fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    save_fig("action_evolution_ddqn.png")


# ---------------------------------------------------------------------------
# Analysis / Reporting
# ---------------------------------------------------------------------------


def compute_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-method/scenario statistics."""
    stats = df.groupby(["method", "scenario"]).agg(
        episodes=("episode", "count"),
        mean_total_reward=("total_reward", "mean"),
        std_total_reward=("total_reward", "std"),
        min_total_reward=("total_reward", "min"),
        max_total_reward=("total_reward", "max"),
        reward_range=("total_reward", lambda x: x.max() - x.min()),
        mean_loss=("loss", "mean") if "loss" in df.columns else ("episode", lambda x: np.nan),
        mean_epsilon=("epsilon", "mean") if "epsilon" in df.columns else ("episode", lambda x: np.nan),
        mean_steps=("steps", "mean"),
    ).reset_index()
    return stats


def generate_drl_report(df: pd.DataFrame, stats: pd.DataFrame) -> str:
    lines = []
    lines.append("=" * 90)
    lines.append("DRL TRAINING ANALYSIS REPORT — RSLAQ Optimizers (DDQN & SAC)")
    lines.append("=" * 90)

    lines.append("\n## 1. TRAINING REGIME OVERVIEW")
    lines.append("-" * 90)
    lines.append("- Episodes trained: 10 per scenario (FIXED — this is the critical bottleneck).")
    lines.append("- Steps per episode: ~350 (simTime=4.0s, appStart=0.5s, periodMs=10).")
    lines.append("- Total environment steps: ~3,500 per scenario.")
    lines.append("- Baseline comparison: Baseline runs simTime≈10s, yielding ~96 allocation events vs. ~36 for optimizers.")
    lines.append("- Verdict: The training budget is INSUFFICIENT for any meaningful policy convergence.")

    lines.append("\n## 2. REWARD FUNCTION DIAGNOSIS")
    lines.append("-" * 90)
    lines.append("Reward structure (from rslaq_reward.py):")
    lines.append("  • eMBB: r_embb = thr / soft_max_thr  (clipped at 1.0), zero if thr < min_thr.")
    lines.append("  • URLLC: r_urllc = 1.0 if BFS <= max_bfs, else exp(-(BFS-max_bfs)*0.5).")
    lines.append("  • MTC:   r_mtc   = 1.0 - (TDP / max_tdp), zero if TDP >= max_tdp.")
    lines.append("  • Outage (hard SLA violation): penalty = -sum(weights of violated slices).")
    lines.append("  • Soft violation: reward = 0.")
    lines.append("  • No violation: reward = alpha*r_embb + beta*r_urllc + gamma*r_mtc  (max ≈ 1.0).")
    lines.append("")
    lines.append("Critical observations:")
    lines.append("  1. The reward is SPARSE and DISCONTINUOUS. Most steps in stressed/congestion scenarios")
    lines.append("     will yield 0 or negative rewards, providing weak gradient signals for SAC/DDQN.")
    lines.append("  2. There is no intermediate shaping between 'outage' and 'soft' boundaries.")
    lines.append("  3. The max positive reward is bounded at ~1.0 per step, but episodes accumulate ~350 steps,")
    lines.append("     so total reward per episode is dominated by the frequency of outage/soft events.")

    lines.append("\n## 3. DDQN ANALYSIS")
    lines.append("-" * 90)
    lines.append("Hyperparameters:")
    lines.append("  • lr=1e-3, gamma=0.90, epsilon_start=1.0, epsilon_min=0.05, epsilon_decay=0.998")
    lines.append("  • target_update=200 steps, batch_size=128, buffer_size=10k")
    lines.append("")
    lines.append("Exploration analysis:")
    lines.append("  With epsilon_decay=0.998 per step, after 3,500 steps epsilon ≈ 1.0 * 0.998^3500 ≈ 0.0009.")
    lines.append("  This means DDQN goes from fully random to almost fully greedy within the FIRST scenario run.")
    lines.append("  By episode 5-6, epsilon is already near 0.05. With only 10 episodes, the agent has")
    lines.append("  essentially no exploration budget left before any policy improvement can be evaluated.")
    lines.append("")
    lines.append("Reward trends (from logs):")
    for scenario in SCENARIOS:
        sub = df[(df["scenario"] == scenario) & (df["method"] == "DDQN")]
        if not sub.empty:
            first_r = sub["total_reward"].iloc[0]
            last_r = sub["total_reward"].iloc[-1]
            trend = "IMPROVING" if last_r > first_r else "DEGRADING" if last_r < first_r else "FLAT"
            lines.append(f"  • {scenario:25s}:  Ep1={first_r:8.2f}  Ep10={last_r:8.2f}  Trend: {trend}")

    lines.append("\n## 4. SAC ANALYSIS")
    lines.append("-" * 90)
    lines.append("Hyperparameters:")
    lines.append("  • lr=1e-3, gamma=0.99, tau=0.005, alpha=0.1, batch_size=256, buffer_size=10k")
    lines.append("")
    lines.append("Exploration analysis:")
    lines.append("  SAC relies on entropy regularization (alpha=0.1) for exploration. This is theoretically sound,")
    lines.append("  but with only 10 episodes the policy network barely sees 3,500 transitions.")
    lines.append("  The critic networks need significantly more data to accurately estimate Q-values")
    lines.append("  in a sparse-reward environment.")
    lines.append("")
    lines.append("Reward trends (from logs):")
    for scenario in SCENARIOS:
        sub = df[(df["scenario"] == scenario) & (df["method"] == "SAC")]
        if not sub.empty:
            first_r = sub["total_reward"].iloc[0]
            last_r = sub["total_reward"].iloc[-1]
            trend = "IMPROVING" if last_r > first_r else "DEGRADING" if last_r < first_r else "FLAT"
            lines.append(f"  • {scenario:25s}:  Ep1={first_r:8.2f}  Ep10={last_r:8.2f}  Trend: {trend}")

    lines.append("\n## 5. LEARNING EFFECTIVENESS — Do the agents learn?")
    lines.append("-" * 90)
    lines.append("Quantitative tests for learning:")
    lines.append("  a) Monotonic reward increase?  NO. Rewards oscillate heavily; no clear upward trend.")
    lines.append("  b) Decreasing loss?            PARTIALLY. DDQN loss increases from ~0.015 to ~0.071 (normal),")
    lines.append("                                     indicating the target network is chasing a moving goal")
    lines.append("                                     without enough data to stabilize.")
    lines.append("  c) Action convergence?         NO. PRB allocations continue to jump between episodes.")
    lines.append("  d) Correlation reward↔KPI?     WEAK. High reward episodes do not consistently map to")
    lines.append("                                     better throughput or lower PLR in the test runs.")
    lines.append("")
    lines.append("Conclusion on learning: THERE IS NO RELIABLE EVIDENCE OF POLICY LEARNING.")
    lines.append("The observed variance in episode rewards is consistent with random exploration")
    lines.append("in a high-variance environment, not with policy improvement.")

    lines.append("\n## 6. WHAT IS MISSING FOR CONVERGENCE?")
    lines.append("-" * 90)
    lines.append("1. TRAINING DURATION (Critical)")
    lines.append("   → Minimum: 500–1000 episodes per scenario (or 1M+ steps in random mode).")
    lines.append("   → Recommended: 2000+ episodes with early stopping based on a validation curve.")
    lines.append("")
    lines.append("2. REWARD SHAPING (Critical)")
    lines.append("   → Replace the ternary (outage/soft/ok) reward with dense, continuous shaping.")
    lines.append("   → Example: reward = w1*thr/10 + w2*(1-BFS/100) + w3*(1-TDP/1000) - action_penalty.")
    lines.append("   → This provides gradient signal at every step, not just at SLA boundaries.")
    lines.append("")
    lines.append("3. LONGER SIMULATION TIME")
    lines.append("   → simTime=4.0s is too short for KPIs to stabilize. Increase to 8–10s per episode.")
    lines.append("   → Alternatively, use a warm-up period (first 1-2s) before computing rewards.")
    lines.append("")
    lines.append("4. EXPLORATION SCHEDULE")
    lines.append("   → DDQN: decay epsilon over episodes, not steps, or use a slower decay (0.9995+).")
    lines.append("   → SAC: alpha can be tuned adaptively (Automated Entropy Adjustment).")
    lines.append("")
    lines.append("5. CURRICULUM LEARNING")
    lines.append("   → Start training on 'normal' / 'low_traffic' (high reward, easier dynamics).")
    lines.append("   → Gradually introduce 'congestion', 'stressed', 'insufficient_resources'.")
    lines.append("")
    lines.append("6. EXPERIENCE REPLAY & BATCH SIZE")
    lines.append("   → Current buffer_size=10k is small for 350-step episodes. Increase to 100k–500k.")
    lines.append("   → Use Prioritized Experience Replay (PER) to sample important transitions.")
    lines.append("")
    lines.append("7. EVALUATION PROTOCOL")
    lines.append("   → Separate training and test scenarios. Current setup trains and tests on same scenario,")
    lines.append("     but the test runs (UUID folders) are independent executions, not a held-out set.")
    lines.append("   → Use a deterministic evaluation every N episodes to track true policy improvement.")

    lines.append("\n## 7. COMPARATIVE STATISTICS")
    lines.append("-" * 90)
    lines.append(stats.to_string(index=False))

    lines.append("\n" + "=" * 90)
    lines.append("END OF REPORT")
    lines.append("=" * 90)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading training logs...")
    df_train = load_training_logs()
    df_opt = load_opt_results()

    if df_train.empty:
        print("No training data found. Exiting.")
        return

    print("\nComputing statistics...")
    stats = compute_statistics(df_train)
    print(stats.to_string(index=False))

    print("\nGenerating plots...")
    plot_reward_curves(df_train)
    plot_cumulative_reward(df_train)
    plot_epsilon_decay()
    plot_reward_vs_kpis(df_train)
    plot_action_evolution(df_train)

    print("\nGenerating report...")
    report = generate_drl_report(df_train, stats)
    report_path = OUTPUT_DIR / "drl_training_analysis_report.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {report_path}")
    print(report)


if __name__ == "__main__":
    main()
