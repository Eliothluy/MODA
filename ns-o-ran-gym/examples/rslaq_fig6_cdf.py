import os
import csv
import json
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

BASELINES_DIR = "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results_baselines"
DRL_RESULTS = "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results"
OUTPUT_DIR = "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SCENARIOS = [
    "low_traffic",
    "normal",
    "congestion",
    "stressed",
    "insufficient_resources",
]
SCENARIO_LABELS = [
    "(a) Low traffic",
    "(b) Normal traffic",
    "(c) Congestion",
    "(d) Stressed",
    "(e) Insufficient resources",
]

SLA_EMBB_MIN = {
    "low_traffic": 10.0,
    "normal": 10.0,
    "congestion": 10.0,
    "stressed": 20.0,
    "insufficient_resources": 10.0,
}
SLA_URLLC_MAX_PLR = 3.0

ALGORITHMS = [
    ("rr", "RR", "#888888", "--", 1.0),
    ("pf", "PF", "#AAAAAA", "-.", 1.0),
    ("maxcqi", "BCQI", "#666666", ":", 1.0),
    ("opt", "Opt [22]", "#2196F3", "--", 1.2),
    ("sac", "SAC [27]", "#FF9800", "-.", 1.2),
    ("rslaq", "RSLAQ", "#D32F2F", "-", 2.5),
]


def load_baseline_data():
    fpath = os.path.join(BASELINES_DIR, "baseline_cdf_data.json")
    if not os.path.exists(fpath):
        print(f"WARNING: {fpath} not found. Run rslaq_run_baselines.py first.")
        return {}
    with open(fpath) as f:
        return json.load(f)


def load_drl_kpm_data(scenario, method, num_episodes=5):
    sc_dir = os.path.join(DRL_RESULTS, scenario)
    if not os.path.isdir(sc_dir):
        return {"embb_thr": [], "mtc_thr": [], "urllc_plr": []}

    subdirs = sorted(
        [d for d in os.listdir(sc_dir) if os.path.isdir(os.path.join(sc_dir, d))],
        key=lambda d: os.path.getmtime(os.path.join(sc_dir, d)),
    )
    n = len(subdirs)
    per_method = n // 3

    ranges = {
        "opt": (0, per_method),
        "rslaq": (per_method, 2 * per_method),
        "sac": (2 * per_method, n),
    }
    s, e = ranges[method]
    selected = subdirs[s:e][-num_episodes:]

    embb_thr, mtc_thr, urllc_plr = [], [], []

    for d in selected:
        kpm_path = os.path.join(sc_dir, d, "rslaq-kpms.txt")
        if not os.path.exists(kpm_path):
            continue

        ue_data = defaultdict(lambda: {"thr": [], "plr": []})
        with open(kpm_path) as f:
            for row in csv.DictReader(f):
                sid = int(row["sliceId"])
                ue = int(row["ueImsi"])
                thr = float(row["throughputMbps"])
                plr = float(row.get("plr", row.get("bufferStatusPct", "0.0")))
                ue_data[(sid, ue)]["thr"].append(thr)
                ue_data[(sid, ue)]["plr"].append(plr)

        for (sid, ue), vals in ue_data.items():
            mean_thr = float(np.mean(vals["thr"])) if vals["thr"] else 0.0
            mean_plr = float(np.mean(vals["plr"])) if vals["plr"] else 0.0
            if sid == 1:
                embb_thr.append(mean_thr)
            elif sid == 2:
                urllc_plr.append(mean_plr)
            elif sid == 3:
                mtc_thr.append(mean_thr)

    return {"embb_thr": embb_thr, "mtc_thr": mtc_thr, "urllc_plr": urllc_plr}


def get_metric_data(baseline_data, scenario, algorithm_key, metric):
    if algorithm_key in ("rr", "pf", "maxcqi"):
        key = f"{scenario}_{algorithm_key}"
        return baseline_data.get(key, {}).get(metric, [])
    else:
        return load_drl_kpm_data(scenario, algorithm_key).get(metric, [])


def compute_cdf(data):
    if len(data) == 0:
        return np.array([0.0]), np.array([0.0])
    sorted_data = np.sort(data)
    cdf = np.linspace(0, 1, len(sorted_data))
    return sorted_data, cdf


def plot_fig6(baseline_data):
    fig, axes = plt.subplots(
        len(SCENARIOS), 3, figsize=(18, 20), sharey="row", squeeze=False
    )

    col_titles = [
        "Throughput for eMBB (Mbps)",
        "Throughput for MTC (Mbps)",
        "PLR for URLLC (%)",
    ]
    col_metrics = ["embb_thr", "mtc_thr", "urllc_plr"]

    for row_idx, (sc, sc_label) in enumerate(zip(SCENARIOS, SCENARIO_LABELS)):
        for col_idx, (metric, col_title) in enumerate(zip(col_metrics, col_titles)):
            ax = axes[row_idx, col_idx]
            all_vals = []

            for algo_key, algo_label, color, ls, lw in ALGORITHMS:
                data = get_metric_data(baseline_data, sc, algo_key, metric)
                all_vals.extend(data)
                x, y = compute_cdf(data)
                ax.plot(
                    x,
                    y,
                    label=algo_label,
                    color=color,
                    linestyle=ls,
                    linewidth=lw,
                    alpha=0.9,
                )

            p99 = np.percentile(all_vals, 99) if all_vals else 10

            if col_idx == 0:
                target = SLA_EMBB_MIN[sc]
                ax.axvline(target, color="black", linestyle="--", linewidth=1.2)
                ax.axvspan(0, target, alpha=0.08, color="red")
                ax.axvspan(target, target * 1.5, alpha=0.06, color="#7B1FA2")
                xmax = max(target * 2.0, p99 * 1.15, 25)
                ax.set_xlim(0, xmax)
            elif col_idx == 2:
                ax.axvline(
                    SLA_URLLC_MAX_PLR, color="black", linestyle="--", linewidth=1.2
                )
                ax.axvspan(SLA_URLLC_MAX_PLR, 100, alpha=0.08, color="red")
                ax.axvspan(0, SLA_URLLC_MAX_PLR, alpha=0.06, color="#7B1FA2")
                ax.set_xlim(0, max(p99 * 1.2, SLA_URLLC_MAX_PLR * 3, 5))
            else:
                ax.set_xlim(0, max(p99 * 1.15, 15))

            ax.set_ylim(0, 1.05)
            ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
            ax.grid(True, which="minor", alpha=0.15, linestyle=":", linewidth=0.3)
            ax.minorticks_on()
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            if row_idx == 0:
                ax.set_title(col_title, fontsize=13, fontweight="bold", pad=10)
            if row_idx == len(SCENARIOS) - 1:
                xlabel = "PLR (%)" if col_idx == 2 else "Throughput (Mbps)"
                ax.set_xlabel(xlabel, fontsize=11)
            if col_idx == 0:
                ax.set_ylabel(f"{sc_label}\n\nCDF", fontsize=11)
            else:
                ax.set_ylabel("CDF", fontsize=10)

    target_line = plt.Line2D(
        [], [], color="black", linestyle="--", linewidth=1.2, label="Target KPI"
    )
    outage_patch = plt.Rectangle((0, 0), 1, 1, alpha=0.15, color="red", label="Outage")
    align_patch = plt.Rectangle(
        (0, 0), 1, 1, alpha=0.10, color="#7B1FA2", label="SLA Align"
    )
    algo_handles = []
    for _, label, color, ls, lw in ALGORITHMS:
        algo_handles.append(
            plt.Line2D([], [], color=color, linestyle=ls, linewidth=lw, label=label)
        )

    all_handles = algo_handles + [target_line, outage_patch, align_patch]
    fig.legend(
        handles=all_handles,
        labels=[h.get_label() for h in all_handles],
        loc="upper center",
        ncol=9,
        fontsize=10,
        frameon=True,
        framealpha=0.95,
        edgecolor="black",
        bbox_to_anchor=(0.5, 1.02),
    )

    fig.tight_layout(rect=[0, 0, 1, 0.96], h_pad=2.5, w_pad=2.0)
    fig.savefig(os.path.join(OUTPUT_DIR, "fig6_cdf.pdf"), dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(OUTPUT_DIR, "fig6_cdf.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved fig6_cdf to {OUTPUT_DIR}")


def main():
    baseline_data = load_baseline_data()
    if not baseline_data:
        print("ERROR: No baseline data. Run rslaq_run_baselines.py first.")
        return

    print("=== Baseline data loaded ===")
    for key in sorted(baseline_data.keys()):
        d = baseline_data[key]
        print(
            f"  {key}: eMBB={len(d.get('embb_thr', []))}, "
            f"MTC={len(d.get('mtc_thr', []))}, URLLC={len(d.get('urllc_plr', []))}"
        )

    plot_fig6(baseline_data)


if __name__ == "__main__":
    main()
