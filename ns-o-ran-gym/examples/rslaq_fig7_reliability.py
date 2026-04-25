import os
import csv
import numpy as np
from collections import defaultdict
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results"
FIGURES = os.path.join(RESULTS, "figures")
os.makedirs(FIGURES, exist_ok=True)

SLA_TARGETS = {
    1: {"min_throughput_mbps": 10.0},
    2: {"max_bfs_pct": 3.0},
}

SCENARIOS = ["low_traffic", "normal", "congestion", "stressed"]
SCENARIO_TITLES = ["Low traffic", "Normal traffic", "Congestion", "Stressed"]
METHOD_ORDER = ["opt", "sac", "ddqn"]
METHOD_LABELS = ["Opt", "SAC", "RSLAQ"]


def compute_reliability(kpm_path):
    rows = []
    with open(kpm_path) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    if not rows:
        return {1: 0.0, 2: 0.0}

    ts_data = defaultdict(lambda: defaultdict(lambda: {"thr": 0.0, "plr": [], "n": 0}))
    for row in rows:
        ts = int(row["timestamp"])
        sid = int(row["sliceId"])
        d = ts_data[ts][sid]
        if sid == 1:
            d["thr"] += float(row["throughputMbps"])
            d["n"] += 1
        elif sid == 2:
            plr_col = row.get("plr", row.get("bufferStatusPct", "0.0"))
            d["plr"].append(float(plr_col))
            d["n"] += 1

    embb_sat, urllc_sat = [], []
    for ts in sorted(ts_data.keys()):
        d1 = ts_data[ts][1]
        if d1["n"] > 0:
            mean_thr = d1["thr"] / d1["n"]
            embb_sat.append(
                1.0 if mean_thr >= SLA_TARGETS[1]["min_throughput_mbps"] else 0.0
            )
        d2 = ts_data[ts][2]
        if d2["n"] > 0:
            max_plr = max(d2["plr"]) if d2["plr"] else 100.0
            urllc_sat.append(1.0 if max_plr <= SLA_TARGETS[2]["max_bfs_pct"] else 0.0)

    return {
        1: float(np.mean(embb_sat)) if embb_sat else 0.0,
        2: float(np.mean(urllc_sat)) if urllc_sat else 0.0,
    }


def extract_data():
    data = {}
    for sc in SCENARIOS:
        data[sc] = {}
        sc_dir = os.path.join(RESULTS, sc)
        if not os.path.isdir(sc_dir):
            continue
        subdirs = sorted(
            [d for d in os.listdir(sc_dir) if os.path.isdir(os.path.join(sc_dir, d))],
            key=lambda d: os.path.getmtime(os.path.join(sc_dir, d)),
        )
        n = len(subdirs)
        per_method = n // 3
        ranges = {
            "opt": (0, per_method),
            "ddqn": (per_method, 2 * per_method),
            "sac": (2 * per_method, 3 * per_method),
        }

        for method in METHOD_ORDER:
            s, e = ranges[method]
            embb, urllc = [], []
            for d in subdirs[s:e][-5:]:
                kpm = os.path.join(sc_dir, d, "rslaq-kpms.txt")
                if os.path.exists(kpm):
                    r = compute_reliability(kpm)
                    embb.append(r[1])
                    urllc.append(r[2])
            data[sc][method] = {
                "embb": float(np.mean(embb)) * 100 if embb else 0.0,
                "urllc": float(np.mean(urllc)) * 100 if urllc else 0.0,
            }
    return data


def plot_fig7(data):
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.5), sharey=True)

    x = np.arange(len(METHOD_ORDER))
    w = 0.32
    c_embb = "#4472C4"
    c_urllc = "#ED7D31"

    for col, (sc, title) in enumerate(zip(SCENARIOS, SCENARIO_TITLES)):
        ax = axes[col]
        embb_v = [data[sc][m]["embb"] for m in METHOD_ORDER]
        urllc_v = [data[sc][m]["urllc"] for m in METHOD_ORDER]

        bars1 = ax.bar(
            x - w / 2,
            embb_v,
            w,
            label="Reliability for eMBB",
            color=c_embb,
            edgecolor="black",
            linewidth=0.5,
        )
        bars2 = ax.bar(
            x + w / 2,
            urllc_v,
            w,
            label="Reliability for URLLC",
            color=c_urllc,
            edgecolor="black",
            linewidth=0.5,
        )

        for bar in list(bars1) + list(bars2):
            h = bar.get_height()
            if h > 5:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    h + 1.5,
                    f"{h:.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )

        ax.set_xticks(x)
        ax.set_xticklabels(METHOD_LABELS, fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylim(0, 105)
        ax.yaxis.set_major_locator(plt.MultipleLocator(20))
        ax.yaxis.set_minor_locator(plt.MultipleLocator(10))
        ax.grid(axis="y", which="major", linestyle="-", alpha=0.3)
        ax.grid(axis="y", which="minor", linestyle=":", alpha=0.2)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Reliability (%)", fontsize=12)
    axes[0].legend(fontsize=9, loc="upper right", framealpha=0.9)

    fig.tight_layout(w_pad=2)
    fig.savefig(
        os.path.join(FIGURES, "fig7_reliability.pdf"), dpi=300, bbox_inches="tight"
    )
    fig.savefig(
        os.path.join(FIGURES, "fig7_reliability.png"), dpi=300, bbox_inches="tight"
    )
    plt.close(fig)
    print(f"Saved fig7_reliability to {FIGURES}")


def main():
    data = extract_data()

    print("=== Reliability Data (%) ===")
    for sc in SCENARIOS:
        print(f"\n  [{sc}]")
        for method, label in zip(METHOD_ORDER, METHOD_LABELS):
            d = data[sc][method]
            print(f"    {label:6s}: eMBB={d['embb']:.1f}%  URLLC={d['urllc']:.1f}%")

    plot_fig7(data)


if __name__ == "__main__":
    main()
