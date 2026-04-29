#!/usr/bin/env python3
"""
Comparative analysis: RSLAQ without optimization vs. with optimization (OPT).
Generates Markdown report and PNG charts.
"""

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path("/home/elioth/Documentos/artigo_jussi")
NO_OPT_DIR = BASE / "ns-3-dev" / "results_rslaq"
OPT_JSON = BASE / "ns-o-ran-gym" / "results" / "opt" / "opt_analysis_report.json"
OUT_MD = BASE / "comparative_report.md"
OUT_DIR = BASE  # PNGs saved next to report

SCENARIOS = ["normal", "congestion", "insufficient_resources", "low_traffic", "stressed"]

# ---------------------------------------------------------------------------
# Load no-opt data
# ---------------------------------------------------------------------------

def load_no_opt_scenario(scenario: str) -> dict[str, Any]:
    """Load CSVs for a scenario and compute per-UE aggregates."""
    slice_file = NO_OPT_DIR / f"rslaq_{scenario}_slice.csv"
    ue_file = NO_OPT_DIR / f"rslaq_{scenario}_ue.csv"

    slices = []
    with slice_file.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            slices.append({
                "slice": row["slice"],
                "tx_bytes": int(row["tx_bytes"]),
                "rx_bytes": int(row["rx_bytes"]),
                "tx_packets": int(row["tx_packets"]),
                "rx_packets": int(row["rx_packets"]),
                "lost_packets": int(row["lost_packets"]),
                "effective_lost_packets": int(row["effective_lost_packets"]),
                "throughput_mbps": float(row["throughput_mbps"]),
                "avg_delay_ms": float(row["avg_delay_ms"]),
                "pdr": float(row["pdr"]),
                "effective_pdr": float(row["effective_pdr"]),
            })

    ues = []
    with ue_file.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ues.append({
                "slice": row["slice"],
                "tx_bytes": int(row["tx_bytes"]),
                "rx_bytes": int(row["rx_bytes"]),
                "tx_packets": int(row["tx_packets"]),
                "rx_packets": int(row["rx_packets"]),
                "lost_packets": int(row["lost_packets"]),
                "effective_lost_packets": int(row["effective_lost_packets"]),
                "throughput_mbps": float(row["throughput_mbps"]),
                "avg_delay_ms": float(row["avg_delay_ms"]),
                "pdr": float(row["pdr"]),
                "effective_pdr": float(row["effective_pdr"]),
            })

    # global per-UE averages
    n_ue = len(ues)
    global_thr = sum(u["throughput_mbps"] for u in ues) / n_ue if n_ue else 0.0
    global_delay = sum(u["avg_delay_ms"] for u in ues) / n_ue if n_ue else 0.0
    global_pdr = sum(u["pdr"] for u in ues) / n_ue if n_ue else 0.0

    # Jain fairness across UEs
    thr_vals = [u["throughput_mbps"] for u in ues]
    jain = (sum(thr_vals) ** 2) / (len(thr_vals) * sum(t ** 2 for t in thr_vals)) if thr_vals and sum(t ** 2 for t in thr_vals) > 0 else 0.0

    # per-slice from UE aggregation
    slice_ue = {}
    for u in ues:
        slice_ue.setdefault(u["slice"], []).append(u)

    per_slice = {}
    for sname, ue_list in slice_ue.items():
        n = len(ue_list)
        per_slice[sname] = {
            "avg_throughput_mbps": sum(u["throughput_mbps"] for u in ue_list) / n,
            "avg_delay_ms": sum(u["avg_delay_ms"] for u in ue_list) / n,
            "avg_pdr": sum(u["pdr"] for u in ue_list) / n,
            "num_ue": n,
        }

    # Also pull RBG allocation summary from diagnostic report if available,
    # otherwise fall back to slice-level TX/RX as proxy.
    # We'll read the *_slice_alloc.csv for average allocated RBG.
    alloc_file = NO_OPT_DIR / f"{scenario}_slice_alloc.csv"
    if alloc_file.exists():
        with alloc_file.open() as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        # Group by slice name and average allocatedRbg where allocatedRbg > 0
        alloc_by_slice: dict[str, list[float]] = {}
        for r in rows:
            s = r.get("slice", "")
            if s:
                try:
                    alloc_by_slice.setdefault(s, []).append(float(r["allocatedRbg"]))
                except ValueError:
                    pass
        for sname, vals in alloc_by_slice.items():
            if vals:
                per_slice.setdefault(sname, {})
                per_slice[sname]["avg_allocated_rbg"] = sum(vals) / len(vals)

    return {
        "global": {
            "avg_throughput_mbps": global_thr,
            "avg_delay_ms": global_delay,
            "avg_pdr": global_pdr,
            "jain_throughput": jain,
        },
        "per_slice": per_slice,
        "num_ue": n_ue,
    }


# ---------------------------------------------------------------------------
# Load OPT data
# ---------------------------------------------------------------------------

def load_opt_data() -> dict[str, Any]:
    with OPT_JSON.open() as fh:
        data = json.load(fh)
    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pct_diff(new: float, old: float) -> str:
    if old == 0:
        return "N/A"
    d = (new - old) / old * 100
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.2f}%"


def fmt(v: float | None, decimals: int = 4) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}"


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def main() -> None:
    no_opt = {s: load_no_opt_scenario(s) for s in SCENARIOS}
    opt = load_opt_data()

    lines = []
    lines.append("# Comparative Analysis: RSLAQ without Optimization vs. OPT\n")
    lines.append("| Metric | Scenario | No-Opt | OPT | Delta |")
    lines.append("|---|---|---|---|---|")

    global_metrics = ["avg_throughput_mbps", "avg_delay_ms", "avg_pdr", "jain_throughput"]
    for metric in global_metrics:
        for scenario in SCENARIOS:
            old = no_opt[scenario]["global"].get(metric, 0.0)
            new = opt.get(scenario, {}).get("global", {}).get(metric, {}).get("mean", 0.0)
            if new is None:
                new = 0.0
            lines.append(f"| {metric} | {scenario} | {fmt(old)} | {fmt(new)} | {pct_diff(new, old)} |")

    lines.append("\n")

    # Per-slice tables
    slices = ["eMBB", "URLLC", "MTC"]
    slice_metrics = ["avg_throughput_mbps", "avg_delay_ms", "avg_pdr"]
    for metric in slice_metrics:
        lines.append(f"## Per-Slice {metric}\n")
        lines.append("| Slice | Scenario | No-Opt | OPT | Delta |")
        lines.append("|---|---|---|---|---|")
        for sname in slices:
            for scenario in SCENARIOS:
                old = no_opt[scenario]["per_slice"].get(sname, {}).get(metric, 0.0)
                new = (
                    opt.get(scenario, {})
                    .get("per_slice", {})
                    .get(sname, {})
                    .get("ue", {})
                    .get(metric, {})
                    .get("mean", 0.0)
                )
                if new is None:
                    new = 0.0
                lines.append(f"| {sname} | {scenario} | {fmt(old)} | {fmt(new)} | {pct_diff(new, old)} |")
        lines.append("\n")

    # Write Markdown
    OUT_MD.write_text("\n".join(lines))
    print(f"Report written to {OUT_MD}")

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------
    x = np.arange(len(SCENARIOS))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    old_vals = [no_opt[s]["global"]["avg_throughput_mbps"] for s in SCENARIOS]
    new_vals = [opt[s]["global"]["avg_throughput_mbps"]["mean"] for s in SCENARIOS]
    ax.bar(x - width / 2, old_vals, width, label="No-Opt")
    ax.bar(x + width / 2, new_vals, width, label="OPT")
    ax.set_ylabel("Avg Throughput (Mbps)")
    ax.set_title("Global Average Throughput per UE")
    ax.set_xticks(x)
    ax.set_xticklabels(SCENARIOS, rotation=15, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "comparison_throughput.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    old_vals = [no_opt[s]["global"]["avg_delay_ms"] for s in SCENARIOS]
    new_vals = [opt[s]["global"]["avg_delay_ms"]["mean"] for s in SCENARIOS]
    ax.bar(x - width / 2, old_vals, width, label="No-Opt")
    ax.bar(x + width / 2, new_vals, width, label="OPT")
    ax.set_ylabel("Avg Delay (ms)")
    ax.set_title("Global Average Delay per UE")
    ax.set_xticks(x)
    ax.set_xticklabels(SCENARIOS, rotation=15, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "comparison_delay.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    old_vals = [no_opt[s]["global"]["avg_pdr"] for s in SCENARIOS]
    new_vals = [opt[s]["global"]["avg_pdr"]["mean"] for s in SCENARIOS]
    ax.bar(x - width / 2, old_vals, width, label="No-Opt")
    ax.bar(x + width / 2, new_vals, width, label="OPT")
    ax.set_ylabel("Avg PDR")
    ax.set_title("Global Average PDR per UE")
    ax.set_xticks(x)
    ax.set_xticklabels(SCENARIOS, rotation=15, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "comparison_pdr.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    old_vals = [no_opt[s]["global"]["jain_throughput"] for s in SCENARIOS]
    new_vals = [opt[s]["global"]["jain_throughput"]["mean"] for s in SCENARIOS]
    ax.bar(x - width / 2, old_vals, width, label="No-Opt")
    ax.bar(x + width / 2, new_vals, width, label="OPT")
    ax.set_ylabel("Jain's Fairness Index")
    ax.set_title("Throughput Fairness (Jain Index)")
    ax.set_xticks(x)
    ax.set_xticklabels(SCENARIOS, rotation=15, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "comparison_jain.png", dpi=150)
    plt.close(fig)

    print(f"Charts saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
