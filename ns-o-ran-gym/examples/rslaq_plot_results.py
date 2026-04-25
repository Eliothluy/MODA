import json
import os
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS_DIR = "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results"
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

SCENARIOS = [
    "low_traffic",
    "normal",
    "congestion",
    "stressed",
    "insufficient_resources",
]
SCENARIO_LABELS = {
    "low_traffic": "(a) Low traffic",
    "normal": "(b) Normal",
    "congestion": "(c) Congestion",
    "stressed": "(d) Stressed",
    "insufficient_resources": "(e) Insufficient",
}
METHOD_LABELS = {"opt": "Opt [22]", "ddqn": "RSLAQ (DDQN)", "sac": "SAC [27]"}
METHOD_COLORS = {"opt": "#d62728", "ddqn": "#e41a1c", "sac": "#9467bd"}


def load_results():
    results = {}
    for method, filename in [
        ("opt", "opt_all_results.json"),
        ("ddqn", "ddqn_all_results.json"),
        ("sac", "sac_all_results.json"),
    ]:
        path = os.path.join(RESULTS_DIR, filename)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = json.load(f)
        for scenario, scenario_data in data.items():
            if scenario not in results:
                results[scenario] = {}
            results[scenario][method] = {"train": scenario_data}
    return results


def smooth(data, window=10):
    if len(data) < window:
        return data
    return np.convolve(data, np.ones(window) / window, mode="valid").tolist()


def plot_fig5_training(results):
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, scenario in enumerate(SCENARIOS):
        ax = axes[idx]
        if scenario not in results:
            continue
        for method in ["ddqn", "sac"]:
            if method in results[scenario]:
                t = results[scenario][method].get("train", {})
                rewards = t.get("rewards", [])
                if rewards:
                    smoothed = smooth(rewards, 5)
                    ax.plot(
                        range(len(smoothed)),
                        smoothed,
                        label=METHOD_LABELS[method],
                        linewidth=1.5,
                        color=METHOD_COLORS[method],
                    )

        opt_data = results[scenario].get("opt", {}).get("train", {})
        opt_avg = opt_data.get("avg_reward", None)
        if opt_avg is not None:
            ax.axhline(
                y=opt_avg,
                color=METHOD_COLORS["opt"],
                linestyle="--",
                label=f"{METHOD_LABELS['opt']} (avg={opt_avg:.2f})",
                alpha=0.7,
            )

        ax.set_xlabel("Episode", fontsize=10)
        ax.set_ylabel("Total Reward", fontsize=10)
        ax.set_title(SCENARIO_LABELS[scenario], fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[5].axis("off")
    fig.suptitle("Fig 5: Training Reward Convergence (NS-3)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(
        os.path.join(FIGURES_DIR, "fig5_training_rewards.pdf"),
        dpi=300,
        bbox_inches="tight",
    )
    fig.savefig(
        os.path.join(FIGURES_DIR, "fig5_training_rewards.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)
    print("  Saved fig5_training_rewards")


def plot_bar_comparison(results):
    fig, axes = plt.subplots(1, 5, figsize=(22, 5))

    methods = ["opt", "ddqn", "sac"]
    x = np.arange(len(methods))
    w = 0.6

    for col, scenario in enumerate(SCENARIOS):
        vals = []
        for m in methods:
            if m == "opt":
                d = results.get(scenario, {}).get("opt", {}).get("train", {})
                vals.append(d.get("avg_reward", 0))
            else:
                d = results.get(scenario, {}).get(m, {}).get("train", {})
                vals.append(d.get("best_avg", 0))

        colors = [METHOD_COLORS[m] for m in methods]
        labels = [METHOD_LABELS[m] for m in methods]
        bars = axes[col].bar(x, vals, w, color=colors, edgecolor="black", linewidth=0.5)
        axes[col].set_xticks(x)
        axes[col].set_xticklabels(labels, fontsize=7, rotation=30)
        axes[col].set_ylabel("Best Avg Reward", fontsize=9)
        axes[col].set_title(SCENARIO_LABELS[scenario], fontsize=10)
        axes[col].grid(True, alpha=0.2, axis="y")

        for bar, val in zip(bars, vals):
            axes[col].text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + 0.3,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=7,
            )

    fig.suptitle("Fig 6: RSLAQ Performance vs Baselines (NS-3)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(
        os.path.join(FIGURES_DIR, "fig6_performance.pdf"), dpi=300, bbox_inches="tight"
    )
    fig.savefig(
        os.path.join(FIGURES_DIR, "fig6_performance.png"), dpi=300, bbox_inches="tight"
    )
    plt.close(fig)
    print("  Saved fig6_performance")


def plot_step_rewards(results):
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, scenario in enumerate(SCENARIOS):
        ax = axes[idx]
        if scenario not in results:
            continue
        for method in ["ddqn", "sac"]:
            t = results[scenario].get(method, {}).get("train", {})
            rewards = t.get("rewards", [])
            if rewards:
                s = smooth(rewards, 3)
                ax.plot(
                    range(len(s)),
                    s,
                    label=METHOD_LABELS[method],
                    linewidth=1.2,
                    color=METHOD_COLORS[method],
                    alpha=0.8,
                )

        opt_t = results[scenario].get("opt", {}).get("train", {})
        opt_step = opt_t.get("step_rewards", [])
        if opt_step:
            s = smooth(opt_step, 3)
            ax.plot(
                range(len(s)),
                s,
                label=METHOD_LABELS["opt"],
                linewidth=1.2,
                color=METHOD_COLORS["opt"],
                alpha=0.8,
                linestyle="--",
            )

        ax.set_xlabel("Episode", fontsize=10)
        ax.set_ylabel("Avg Reward per Episode", fontsize=10)
        ax.set_title(SCENARIO_LABELS[scenario], fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[5].axis("off")
    fig.suptitle("Fig 7: Reward per Episode (NS-3)", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(
        os.path.join(FIGURES_DIR, "fig7_episode_rewards.pdf"),
        dpi=300,
        bbox_inches="tight",
    )
    fig.savefig(
        os.path.join(FIGURES_DIR, "fig7_episode_rewards.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)
    print("  Saved fig7_episode_rewards")


def plot_summary_table(results):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis("off")

    header = ["Scenario", "OPT [22]", "RSLAQ (DDQN)", "SAC [27]"]
    rows = []
    for sc in SCENARIOS:
        opt_v = results.get(sc, {}).get("opt", {}).get("train", {}).get("avg_reward", 0)
        ddqn_v = results.get(sc, {}).get("ddqn", {}).get("train", {}).get("best_avg", 0)
        sac_v = results.get(sc, {}).get("sac", {}).get("train", {}).get("best_avg", 0)
        rows.append(
            [SCENARIO_LABELS[sc], f"{opt_v:.2f}", f"{ddqn_v:.2f}", f"{sac_v:.2f}"]
        )

    table = ax.table(cellText=rows, colLabels=header, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)

    for i in range(len(header)):
        table[0, i].set_facecolor("#40466e")
        table[0, i].set_text_props(color="white", fontweight="bold")

    fig.suptitle("Table: Average Reward Comparison (NS-3)", fontsize=14)
    fig.tight_layout()
    fig.savefig(
        os.path.join(FIGURES_DIR, "table_summary.pdf"), dpi=300, bbox_inches="tight"
    )
    fig.savefig(
        os.path.join(FIGURES_DIR, "table_summary.png"), dpi=300, bbox_inches="tight"
    )
    plt.close(fig)
    print("  Saved table_summary")


def main():
    results = load_results()
    print(f"Loaded results for: {list(results.keys())}")
    plot_fig5_training(results)
    plot_bar_comparison(results)
    plot_step_rewards(results)
    plot_summary_table(results)
    print(f"\nAll figures saved to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
