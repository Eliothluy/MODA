import os
import csv
import json
import numpy as np
from collections import defaultdict
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = "/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results_sensitivity"
FIGURES = os.path.join(RESULTS, "figures")
os.makedirs(FIGURES, exist_ok=True)

SLA_TARGETS = {
    1: {"min_throughput_mbps": 10.0},
    2: {"max_plr_pct": 3.0},
}

SCENARIOS = ["low_traffic", "normal", "congestion", "stressed"]
PSTA_VALUES = [0.1, 0.2, 0.4, 0.5, 0.6, 0.7]


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
            urllc_sat.append(1.0 if max_plr <= SLA_TARGETS[2]["max_plr_pct"] else 0.0)

    return {
        1: float(np.mean(embb_sat)) if embb_sat else 0.0,
        2: float(np.mean(urllc_sat)) if urllc_sat else 0.0,
    }


def extract_table7_data():
    table = {}
    for psta in PSTA_VALUES:
        psta_key = f"table7_psta{psta}"
        table[psta] = {}
        for sc in SCENARIOS:
            sc_dir = os.path.join(RESULTS, f"{psta_key}", sc)
            if not os.path.isdir(sc_dir):
                table[psta][sc] = {"embb": 0.0, "urllc": 0.0}
                continue

            subdirs = sorted(
                [
                    d
                    for d in os.listdir(sc_dir)
                    if os.path.isdir(os.path.join(sc_dir, d))
                ],
                key=lambda d: os.path.getmtime(os.path.join(sc_dir, d)),
            )
            embb, urllc = [], []
            for d in subdirs[-5:]:
                kpm = os.path.join(sc_dir, d, "rslaq-kpms.txt")
                if os.path.exists(kpm):
                    r = compute_reliability(kpm)
                    embb.append(r[1])
                    urllc.append(r[2])

            table[psta][sc] = {
                "embb": float(np.mean(embb)) if embb else 0.0,
                "urllc": float(np.mean(urllc)) if urllc else 0.0,
            }
    return table


def print_table7(table):
    print("\nTABLE VII: Reliability for different psta values")
    print(f"{'psta':>8s} | ", end="")
    for sc in SCENARIOS:
        print(f"{sc + ' eMBB':>15s} {sc + ' URLLC':>15s} | ", end="")
    print()
    print("-" * 140)

    for psta in PSTA_VALUES:
        print(f"{psta:>8.1f} | ", end="")
        for sc in SCENARIOS:
            d = table[psta][sc]
            print(f"{d['embb']:>15.3f} {d['urllc']:>15.3f} | ", end="")
        print()


def plot_table7(table):
    fig, axes = plt.subplots(1, 4, figsize=(18, 5), sharey=True)

    x = np.arange(len(PSTA_VALUES))
    w = 0.32
    c_embb = "#4472C4"
    c_urllc = "#ED7D31"

    for col, (sc, title) in enumerate(
        zip(SCENARIOS, ["Low traffic", "Normal", "Congestion", "Stressed"])
    ):
        ax = axes[col]
        embb_v = [table[psta][sc]["embb"] * 100 for psta in PSTA_VALUES]
        urllc_v = [table[psta][sc]["urllc"] * 100 for psta in PSTA_VALUES]

        ax.bar(
            x - w / 2,
            embb_v,
            w,
            label="eMBB",
            color=c_embb,
            edgecolor="black",
            linewidth=0.5,
        )
        ax.bar(
            x + w / 2,
            urllc_v,
            w,
            label="URLLC",
            color=c_urllc,
            edgecolor="black",
            linewidth=0.5,
        )

        ax.set_xticks(x)
        ax.set_xticklabels([f"{p}" for p in PSTA_VALUES], fontsize=9)
        ax.set_xlabel("p_sta", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Reliability (%)", fontsize=12)
    axes[0].legend(fontsize=9)

    fig.tight_layout(w_pad=2)
    fig.savefig(
        os.path.join(FIGURES, "table7_psta_sensitivity.pdf"),
        dpi=300,
        bbox_inches="tight",
    )
    fig.savefig(
        os.path.join(FIGURES, "table7_psta_sensitivity.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)
    print(f"Saved table7 figure to {FIGURES}")


def main():
    table = extract_table7_data()
    print_table7(table)
    plot_table7(table)


if __name__ == "__main__":
    main()
