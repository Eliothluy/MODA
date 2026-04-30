#!/usr/bin/env python3
"""
Compare baseline RSLAQ results against DRL optimizers (DDQN, SAC, OPT).

Generates trade-off plots for throughput, PDR, and resource allocation
across scenarios and slices.

Usage:
    python3 compare_baseline_vs_optimizers.py
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

SLICES = ["eMBB", "URLLC", "MTC"]
METHODS = ["Baseline", "DDQN", "SAC", "OPT"]
METHOD_COLORS = {
    "Baseline": "#7f7f7f",
    "DDQN": "#1f77b4",
    "SAC": "#2ca02c",
    "OPT": "#ff7f0e",
}

BASELINE_DIR = Path("/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/results_rslaq")
OPTIMIZER_DIR = Path("/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/results")
OUTPUT_DIR = Path("/home/eliothluy/Documentos/artigo_jussi/scripts/comparison_plots")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", newline="") as f:
        return list(csv.DictReader(f))


def sum_allocated_rbg(rows: List[Dict[str, Any]], slice_name_map: Dict[int, str]) -> Tuple[Dict[str, int], int]:
    """Sum allocatedRbg per slice from slice_alloc rows and count unique time intervals."""
    totals: Dict[str, int] = defaultdict(int)
    unique_times = set()
    for r in rows:
        sid = int(r.get("sliceId", -1))
        name = slice_name_map.get(sid, f"Slice{sid}")
        totals[name] += int(r.get("allocatedRbg", 0))
        unique_times.add(int(r.get("timeMs", 0)))
    num_events = len(unique_times) if unique_times else 1
    return dict(totals), num_events


# ---------------------------------------------------------------------------
# Baseline loaders
# ---------------------------------------------------------------------------


def load_baseline(scenario: str) -> Dict[str, Dict[str, Any]]:
    """Load baseline slice KPIs and allocations for a scenario."""
    slice_file = BASELINE_DIR / f"rslaq_{scenario}_slice.csv"
    alloc_file = BASELINE_DIR / f"{scenario}_slice_alloc.csv"

    slice_data: Dict[str, Dict[str, Any]] = {}
    for r in read_csv_rows(slice_file):
        name = r["slice"]
        slice_data[name] = {
            "throughput_mbps": float(r["throughput_mbps"]),
            "pdr": float(r["pdr"]),
            "effective_pdr": float(r["effective_pdr"]),
            "avg_delay_ms": float(r["avg_delay_ms"]),
            "tx_bytes": int(float(r["tx_bytes"])),
            "rx_bytes": int(float(r["rx_bytes"])),
            "tx_packets": int(float(r["tx_packets"])),
            "rx_packets": int(float(r["rx_packets"])),
            "lost_packets": int(float(r["lost_packets"])),
        }

    # Build slice id -> name map from mapping file
    mapping_file = BASELINE_DIR / f"{scenario}_ue_rnti_mapping.csv"
    slice_name_map: Dict[int, str] = {0: "eMBB", 1: "URLLC", 2: "MTC"}
    if mapping_file.exists():
        for r in read_csv_rows(mapping_file):
            sid = int(r.get("sliceId", -1))
            sname = r.get("sliceName", "")
            if sid >= 0 and sname:
                slice_name_map[sid] = sname

    alloc_rows = read_csv_rows(alloc_file) if alloc_file.exists() else []
    alloc_totals, num_events = sum_allocated_rbg(alloc_rows, slice_name_map)

    for s in slice_data:
        slice_data[s]["allocated_rbg"] = alloc_totals.get(s, 0)
        slice_data[s]["allocated_rbg_rate"] = alloc_totals.get(s, 0) / num_events
        slice_data[s]["num_alloc_events"] = num_events

    return slice_data


# ---------------------------------------------------------------------------
# Optimizer loaders
# ---------------------------------------------------------------------------


def compute_optimizer_metrics(uuid_path: Path, scenario: str) -> Dict[str, Dict[str, Any]]:
    """Read timeseries + allocation for a single optimizer run."""
    ts_file = uuid_path / "rslaq_stats_timeseries.csv"
    alloc_file = uuid_path / f"{scenario}_slice_alloc.csv"

    ts_rows = read_csv_rows(ts_file)

    # Per-slice collections
    slice_thr_per_ts: Dict[str, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
    slice_pdr_vals: Dict[str, List[float]] = defaultdict(list)
    slice_bfs_vals: Dict[str, List[float]] = defaultdict(list)

    for r in ts_rows:
        s = r["slice"]
        ts = int(r["timestamp_ms"])
        thr = float(r["thr_mbps"])
        slice_thr_per_ts[s][ts] += thr
        slice_pdr_vals[s].append((100.0 - float(r["effective_lost_pcts"])) / 100.0)
        slice_bfs_vals[s].append(float(r["bfs_pct"]))

    slice_data: Dict[str, Dict[str, Any]] = {}
    for s in SLICES:
        thr_ts = slice_thr_per_ts.get(s, {})
        throughput = sum(thr_ts.values()) / len(thr_ts) if thr_ts else 0.0
        pdr_vals = slice_pdr_vals.get(s, [])
        pdr = sum(pdr_vals) / len(pdr_vals) if pdr_vals else 0.0
        bfs_vals = slice_bfs_vals.get(s, [])
        bfs = sum(bfs_vals) / len(bfs_vals) if bfs_vals else 0.0
        slice_data[s] = {
            "throughput_mbps": throughput,
            "pdr": pdr,
            "bfs_pct": bfs,
        }

    # Allocations
    # Need slice id -> name map. Try to infer from mapping file if present.
    mapping_file = uuid_path / f"{scenario}_ue_rnti_mapping.csv"
    slice_name_map: Dict[int, str] = {0: "eMBB", 1: "URLLC", 2: "MTC"}
    if mapping_file.exists():
        for r in read_csv_rows(mapping_file):
            sid = int(r.get("sliceId", -1))
            sname = r.get("sliceName", "")
            if sid >= 0 and sname:
                slice_name_map[sid] = sname

    alloc_rows = read_csv_rows(alloc_file) if alloc_file.exists() else []
    alloc_totals, num_events = sum_allocated_rbg(alloc_rows, slice_name_map)
    for s in slice_data:
        slice_data[s]["allocated_rbg"] = alloc_totals.get(s, 0)
        slice_data[s]["allocated_rbg_rate"] = alloc_totals.get(s, 0) / num_events
        slice_data[s]["num_alloc_events"] = num_events

    return slice_data


def aggregate_optimizer_runs(scenario: str, method: str) -> Dict[str, Dict[str, Any]]:
    """Average metrics across all UUID folders for a method+scenario."""
    if method == "DDQN":
        method_dir = OPTIMIZER_DIR / f"ddqn_{scenario}"
    elif method == "SAC":
        method_dir = OPTIMIZER_DIR / f"sac_{scenario}"
    elif method == "OPT":
        method_dir = OPTIMIZER_DIR / "opt" / scenario
    else:
        raise ValueError(f"Unknown method: {method}")

    if not method_dir.exists():
        return {}

    # Find UUID folders (ignore .pt, .json, .csv at top level)
    uuid_dirs = [
        p for p in method_dir.iterdir()
        if p.is_dir() and (p / "rslaq_stats_timeseries.csv").exists()
    ]

    if not uuid_dirs:
        return {}

    runs: List[Dict[str, Dict[str, Any]]] = []
    for uuid_path in uuid_dirs:
        try:
            run_data = compute_optimizer_metrics(uuid_path, scenario)
            runs.append(run_data)
        except Exception as e:
            print(f"Warning: failed to process {uuid_path}: {e}")

    if not runs:
        return {}

    # Average per slice
    aggregated: Dict[str, Dict[str, Any]] = {}
    for s in SLICES:
        aggregated[s] = {}
        for metric in ["throughput_mbps", "pdr", "bfs_pct", "allocated_rbg", "allocated_rbg_rate"]:
            vals = [run[s].get(metric, 0.0) for run in runs if s in run]
            aggregated[s][metric] = float(np.mean(vals)) if vals else 0.0
            aggregated[s][f"{metric}_std"] = float(np.std(vals)) if vals else 0.0

    return aggregated


# ---------------------------------------------------------------------------
# Main data assembly
# ---------------------------------------------------------------------------


def build_comparison_df() -> pd.DataFrame:
    rows = []
    for scenario in SCENARIOS:
        # Baseline
        baseline = load_baseline(scenario)
        for s in SLICES:
            if s not in baseline:
                continue
            rows.append({
                "scenario": scenario,
                "method": "Baseline",
                "slice": s,
                **baseline[s],
            })

        # Optimizers
        for method in ["DDQN", "SAC", "OPT"]:
            agg = aggregate_optimizer_runs(scenario, method)
            for s in SLICES:
                if s not in agg:
                    continue
                rows.append({
                    "scenario": scenario,
                    "method": method,
                    "slice": s,
                    **agg[s],
                })

    df = pd.DataFrame(rows)
    # Ensure numeric types
    for col in ["throughput_mbps", "pdr", "bfs_pct", "allocated_rbg", "allocated_rbg_rate", "avg_delay_ms"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def save_fig(name: str) -> None:
    path = OUTPUT_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved plot: {path}")


def plot_grouped_bars(
    df: pd.DataFrame,
    metric: str,
    ylabel: str,
    filename: str,
    ylim: Tuple[float, float] | None = None,
) -> None:
    """Grouped bar chart: one group per (scenario, slice), bars per method."""
    scenarios = SCENARIOS
    n_scenarios = len(scenarios)
    n_slices = len(SLICES)
    n_methods = len(METHODS)

    fig, axes = plt.subplots(1, n_scenarios, figsize=(4.5 * n_scenarios, 5), sharey=True)
    if n_scenarios == 1:
        axes = [axes]

    bar_width = 0.18
    x = np.arange(n_slices)

    for ax, scenario in zip(axes, scenarios):
        ax.set_title(scenario.replace("_", " ").title(), fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels(SLICES)
        ax.set_xlabel("Slice")
        if ylim:
            ax.set_ylim(ylim)

        for i, method in enumerate(METHODS):
            sub = df[(df["scenario"] == scenario) & (df["method"] == method)]
            vals = [sub[sub["slice"] == s][metric].values[0] if len(sub[sub["slice"] == s]) > 0 else 0 for s in SLICES]
            offset = (i - n_methods / 2 + 0.5) * bar_width
            ax.bar(x + offset, vals, bar_width, label=method, color=METHOD_COLORS[method])

        if scenario == scenarios[0]:
            ax.set_ylabel(ylabel)
            ax.legend()

    plt.tight_layout()
    save_fig(filename)


def plot_tradeoff_scatter(
    df: pd.DataFrame,
    x_metric: str,
    y_metric: str,
    xlabel: str,
    ylabel: str,
    filename: str,
) -> None:
    """Scatter plot: each point is a slice under a method, faceted by scenario."""
    scenarios = SCENARIOS
    n_scenarios = len(scenarios)
    fig, axes = plt.subplots(1, n_scenarios, figsize=(4.5 * n_scenarios, 5), sharex=True, sharey=True)
    if n_scenarios == 1:
        axes = [axes]

    for ax, scenario in zip(axes, scenarios):
        ax.set_title(scenario.replace("_", " ").title(), fontsize=11)
        ax.set_xlabel(xlabel)
        if scenario == scenarios[0]:
            ax.set_ylabel(ylabel)

        sub = df[df["scenario"] == scenario]
        for method in METHODS:
            sub_m = sub[sub["method"] == method]
            xs = sub_m[x_metric].values
            ys = sub_m[y_metric].values
            ax.scatter(xs, ys, label=method, color=METHOD_COLORS[method], s=100, alpha=0.8)
            # Annotate slice names
            for _, row in sub_m.iterrows():
                ax.annotate(row["slice"], (row[x_metric], row[y_metric]), fontsize=7, alpha=0.7)

        ax.legend(fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    save_fig(filename)


def plot_total_throughput(df: pd.DataFrame) -> None:
    """Stacked/grouped bar of total throughput per scenario."""
    total_df = df.groupby(["scenario", "method"])["throughput_mbps"].sum().reset_index()

    scenarios = SCENARIOS
    n_scenarios = len(scenarios)
    fig, ax = plt.subplots(figsize=(max(6, 1.2 * n_scenarios), 5))

    bar_width = 0.18
    x = np.arange(n_scenarios)

    for i, method in enumerate(METHODS):
        vals = [total_df[(total_df["scenario"] == s) & (total_df["method"] == method)]["throughput_mbps"].values[0] if len(total_df[(total_df["scenario"] == s) & (total_df["method"] == method)]) > 0 else 0 for s in scenarios]
        offset = (i - len(METHODS) / 2 + 0.5) * bar_width
        ax.bar(x + offset, vals, bar_width, label=method, color=METHOD_COLORS[method])

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", " ").title() for s in scenarios])
    ax.set_ylabel("Total Throughput (Mbps)")
    ax.set_title("Total Throughput per Scenario")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    save_fig("total_throughput_per_scenario.png")


def plot_total_allocated_rbg(df: pd.DataFrame) -> None:
    """Grouped bar of total avg allocated RBG per 100 ms per scenario."""
    total_df = df.groupby(["scenario", "method"])["allocated_rbg_rate"].sum().reset_index()

    scenarios = SCENARIOS
    n_scenarios = len(scenarios)
    fig, ax = plt.subplots(figsize=(max(7, 1.4 * n_scenarios), 5))

    bar_width = 0.18
    x = np.arange(n_scenarios)

    for i, method in enumerate(METHODS):
        vals = [total_df[(total_df["scenario"] == s) & (total_df["method"] == method)]["allocated_rbg_rate"].values[0] if len(total_df[(total_df["scenario"] == s) & (total_df["method"] == method)]) > 0 else 0 for s in scenarios]
        offset = (i - len(METHODS) / 2 + 0.5) * bar_width
        ax.bar(x + offset, vals, bar_width, label=method, color=METHOD_COLORS[method])

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", " ").title() for s in scenarios], rotation=15, ha="right")
    ax.set_ylabel("Total Avg Allocated RBG per 100 ms")
    ax.set_title("Total Avg Allocated RBG per 100 ms per Scenario")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    save_fig("total_allocated_rbg_rate_per_scenario.png")


def generate_report(df: pd.DataFrame) -> None:
    """Print a textual summary table."""
    print("\n" + "=" * 80)
    print("COMPARISON REPORT: Baseline vs DDQN vs SAC vs OPT")
    print("=" * 80)

    for scenario in SCENARIOS:
        print(f"\nScenario: {scenario.upper()}")
        sub = df[df["scenario"] == scenario]
        pivot = sub.pivot_table(index="slice", columns="method", values=["throughput_mbps", "pdr", "allocated_rbg"])
        print(pivot.to_string())

    print("\n" + "=" * 80)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Building comparison dataset...")
    df = build_comparison_df()

    if df.empty:
        print("No data found. Exiting.")
        return

    generate_report(df)

    print("\nGenerating plots...")
    plot_grouped_bars(df, "throughput_mbps", "Throughput (Mbps)", "throughput_per_slice.png")
    plot_grouped_bars(df, "pdr", "Packet Delivery Ratio (PDR)", "pdr_per_slice.png", ylim=(0, 1.05))
    plot_grouped_bars(df, "allocated_rbg_rate", "Avg Allocated RBG per 100 ms", "allocated_rbg_rate_per_slice.png")
    plot_total_throughput(df)
    plot_total_allocated_rbg(df)

    plot_tradeoff_scatter(df, "throughput_mbps", "pdr", "Throughput (Mbps)", "PDR", "tradeoff_throughput_vs_pdr.png")
    plot_tradeoff_scatter(df, "throughput_mbps", "allocated_rbg_rate", "Throughput (Mbps)", "Avg Allocated RBG per 100 ms", "tradeoff_throughput_vs_rbg_rate.png")

    print(f"\nAll plots saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
