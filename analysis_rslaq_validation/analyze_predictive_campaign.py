#!/usr/bin/env python3
"""Compare the controlled RSLAQ campaign with the predictive SAC campaign.

The script is read-only with respect to raw simulation results. It writes
derived tables, figures, and a Markdown report under the requested output
folder.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCENARIOS = [
    "low_traffic",
    "normal",
    "congestion",
    "stressed",
    "insufficient_resources",
]

SLICES = ["eMBB", "URLLC", "MTC"]

SLA = {
    "low_traffic": {"embb_min": 10.0, "embb_soft": 15.0, "urllc_bfs": 10000.0, "mtc_target": 10.0},
    "normal": {"embb_min": 10.0, "embb_soft": 15.0, "urllc_bfs": 10000.0, "mtc_target": 10.0},
    "congestion": {"embb_min": 10.0, "embb_soft": 15.0, "urllc_bfs": 10000.0, "mtc_target": 20.0},
    "stressed": {"embb_min": 20.0, "embb_soft": 25.0, "urllc_bfs": 10000.0, "mtc_target": 20.0},
    "insufficient_resources": {"embb_min": 20.0, "embb_soft": 25.0, "urllc_bfs": 10000.0, "mtc_target": 20.0},
}

BASELINE_LABELS = {
    "pure_rr": "RR",
    "pure_pf": "PF",
    "pure_bcqi": "BCQI",
    "slice_weighted_pf": "Opt",
}

METHOD_ORDER = ["RR", "PF", "BCQI", "Opt", "SAC", "RSLAQ/DDQN", "Predictive SAC"]
DRL_METHODS = ["SAC", "RSLAQ/DDQN", "Predictive SAC"]
METHOD_COLORS = {
    "RR": "#777777",
    "PF": "#3b82f6",
    "BCQI": "#22c55e",
    "Opt": "#f59e0b",
    "SAC": "#8b5cf6",
    "RSLAQ/DDQN": "#dc2626",
    "Predictive SAC": "#0891b2",
}


@dataclass
class ComparisonData:
    paper_config: dict
    predictive_config: dict
    forecaster_metrics: dict
    training: pd.DataFrame
    steps: pd.DataFrame
    baselines: pd.DataFrame


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, **kwargs)
    except Exception as exc:
        print(f"warn: failed to read {path}: {exc}")
        return pd.DataFrame()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"warn: failed to read {path}: {exc}")
        return {}


def ci95(values: Iterable[float]) -> float:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        return float("nan")
    return float(1.96 * arr.std(ddof=1) / math.sqrt(arr.size))


def cdf(values: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.array([]), np.array([])
    arr = np.sort(arr)
    return arr, np.arange(1, arr.size + 1) / arr.size


def parse_paper_dir(name: str) -> tuple[str, str, int] | None:
    match = re.match(r"^(ddqn|sac)_(.+)_seed(\d+)$", name)
    if not match:
        return None
    algo, scenario, seed = match.groups()
    if scenario not in SCENARIOS:
        return None
    method = "RSLAQ/DDQN" if algo == "ddqn" else "SAC"
    return method, scenario, int(seed)


def parse_predictive_dir(name: str) -> tuple[str, str, int] | None:
    match = re.match(r"^predictive_sac_(.+)_seed(\d+)$", name)
    if not match:
        return None
    scenario, seed = match.groups()
    if scenario not in SCENARIOS:
        return None
    return "Predictive SAC", scenario, int(seed)


def load_training(paper_root: Path, predictive_root: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for run_dir in sorted(paper_root.iterdir()):
        if not run_dir.is_dir():
            continue
        parsed = parse_paper_dir(run_dir.name)
        if parsed is None:
            continue
        method, scenario, seed = parsed
        algo = "ddqn" if method == "RSLAQ/DDQN" else "sac"
        path = run_dir / f"{algo}_training_log.csv"
        df = read_csv(path)
        if df.empty:
            continue
        df["method"] = method
        df["scenario"] = scenario
        df["seed"] = seed
        df["line"] = "paper_faithful"
        df["reward_total"] = pd.to_numeric(df["total_reward"], errors="coerce")
        df["reward_aux"] = np.nan
        df["source_file"] = str(path)
        frames.append(df)

    for run_dir in sorted(predictive_root.iterdir()):
        if not run_dir.is_dir():
            continue
        parsed = parse_predictive_dir(run_dir.name)
        if parsed is None:
            continue
        method, scenario, seed = parsed
        path = run_dir / "predictive_sac_training_log.csv"
        df = read_csv(path)
        if df.empty:
            continue
        df["method"] = method
        df["scenario"] = scenario
        df["seed"] = seed
        df["line"] = "predictive_forecaster_sac"
        df["reward_total"] = pd.to_numeric(df["base_reward"], errors="coerce")
        df["reward_aux"] = pd.to_numeric(df["shaped_reward"], errors="coerce")
        df["source_file"] = str(path)
        frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_steps(paper_root: Path, predictive_root: Path) -> pd.DataFrame:
    usecols = [
        "seed",
        "scenario",
        "episode",
        "step",
        "algo_mode",
        "slice_id",
        "slice",
        "throughput_mbps",
        "dTxBytes",
        "dRxBytes",
        "bufferBytes_mean",
        "bufferBytes_max",
        "plr_pct",
        "pdr_pct",
        "dLostPackets",
        "resourceSharePct",
        "action_embb",
        "action_urllc",
        "action_mtc",
        "scheduler_id",
        "scheduler_name",
        "reward",
        "outage_flag",
        "soft_flag",
        "terminated",
        "truncated",
        "sim_id",
    ]
    frames: list[pd.DataFrame] = []

    for root, parser, line_name in [
        (paper_root, parse_paper_dir, "paper_faithful"),
        (predictive_root, parse_predictive_dir, "predictive_forecaster_sac"),
    ]:
        for run_dir in sorted(root.iterdir()):
            if not run_dir.is_dir():
                continue
            parsed = parser(run_dir.name)
            if parsed is None:
                continue
            method, scenario, seed = parsed
            for path in sorted(run_dir.glob("*/step_metrics.csv")):
                df = read_csv(path, usecols=lambda c: c in usecols)
                if df.empty:
                    continue
                df["method"] = method
                df["scenario"] = scenario
                df["seed"] = seed
                df["line"] = line_name
                df["source_file"] = str(path)
                frames.append(df)

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    for col in [
        "throughput_mbps",
        "dTxBytes",
        "dRxBytes",
        "bufferBytes_mean",
        "bufferBytes_max",
        "plr_pct",
        "dLostPackets",
        "resourceSharePct",
        "action_embb",
        "action_urllc",
        "action_mtc",
        "reward",
    ]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["outage_flag_bool"] = out["outage_flag"].astype(str).str.lower().eq("true")
    out["soft_flag_bool"] = out["soft_flag"].astype(str).str.lower().eq("true")
    return out


def baseline_result_dirs(paper_root: Path) -> list[tuple[str, str, int, Path]]:
    manifest = paper_root / "baselines" / "results_rslaq_network_only" / "batch_manifest.csv"
    df = read_csv(manifest)
    if df.empty:
        return []
    dirs: list[tuple[str, str, int, Path]] = []
    for row in df[df["status"].astype(str).str.lower().eq("ok")].itertuples(index=False):
        method = BASELINE_LABELS.get(str(row.baseline_mode), str(row.baseline_mode))
        dirs.append((str(row.scenario), method, int(row.seed), Path(str(row.result_dir))))
    return dirs


def load_baselines(paper_root: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for scenario, method, seed, result_dir in baseline_result_dirs(paper_root):
        path = result_dir / "timeseries.csv"
        df = read_csv(path)
        if df.empty:
            continue
        df["scenario"] = scenario
        df["method"] = method
        df["seed"] = seed
        df["line"] = "ns3_baseline"
        df["source_file"] = str(path)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if out.empty:
        return out
    for col in ["thr_mbps", "tx_bytes_delta", "rx_bytes_delta", "buffer_bytes", "dropped_packets_delta"]:
        if col in out:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def load_data(paper_root: Path, predictive_root: Path) -> ComparisonData:
    return ComparisonData(
        paper_config=load_json(paper_root / "campaign_config.json"),
        predictive_config=load_json(predictive_root / "campaign_config.json"),
        forecaster_metrics=load_json(predictive_root / "forecaster" / "forecaster_metrics.json"),
        training=load_training(paper_root, predictive_root),
        steps=load_steps(paper_root, predictive_root),
        baselines=load_baselines(paper_root),
    )


def drl_distribution(data: ComparisonData, scenario: str, method: str, slice_name: str, metric: str) -> pd.Series:
    df = data.steps
    if df.empty:
        return pd.Series(dtype=float)
    g = df[(df["scenario"] == scenario) & (df["method"] == method) & (df["slice"] == slice_name)]
    if g.empty:
        return pd.Series(dtype=float)
    if metric == "throughput":
        return g["throughput_mbps"]
    if metric == "urllc_buffer_pct":
        return g["bufferBytes_max"] / SLA[scenario]["urllc_bfs"] * 100.0
    return pd.Series(dtype=float)


def baseline_distribution(data: ComparisonData, scenario: str, method: str, slice_name: str, metric: str) -> pd.Series:
    df = data.baselines
    if df.empty:
        return pd.Series(dtype=float)
    g = df[(df["scenario"] == scenario) & (df["method"] == method) & (df["slice"] == slice_name)]
    if g.empty:
        return pd.Series(dtype=float)
    if metric == "throughput":
        agg = g.groupby(["seed", "timestamp_ms"], as_index=False)["thr_mbps"].sum()
        return agg["thr_mbps"]
    if metric == "urllc_buffer_pct":
        valid = g[g["buffer_bytes"].fillna(-1) >= 0]
        if valid.empty:
            return pd.Series(dtype=float)
        agg = valid.groupby(["seed", "timestamp_ms"], as_index=False)["buffer_bytes"].max()
        return agg["buffer_bytes"] / SLA[scenario]["urllc_bfs"] * 100.0
    return pd.Series(dtype=float)


def plot_reward_by_method(training: pd.DataFrame, out_base: Path) -> None:
    if training.empty:
        return
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), sharex=True)
    axes = axes.ravel()
    for ax, scenario in zip(axes, SCENARIOS):
        for method in ["SAC", "RSLAQ/DDQN", "Predictive SAC"]:
            g = training[(training["scenario"] == scenario) & (training["method"] == method)]
            if g.empty:
                continue
            stat = g.groupby("episode")["reward_total"].agg(["mean", "std", "count"]).reset_index()
            x = stat["episode"].to_numpy(dtype=float)
            y = stat["mean"].to_numpy(dtype=float)
            err = 1.96 * stat["std"].fillna(0).to_numpy(dtype=float) / np.sqrt(stat["count"].clip(lower=1).to_numpy(dtype=float))
            ax.plot(x, y, label=method, color=METHOD_COLORS[method], linewidth=1.7)
            if stat["count"].max() >= 2:
                ax.fill_between(x, y - err, y + err, color=METHOD_COLORS[method], alpha=0.12)
        ax.axhline(0.0, color="#222222", linewidth=0.8)
        ax.set_title(scenario)
        ax.grid(True, alpha=0.22)
    axes[-1].axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.97, 0.08))
    fig.supxlabel("Episodio")
    fig.supylabel("Reward total")
    fig.suptitle("Reward por episodio - SAC, RSLAQ/DDQN e Predictive SAC", y=0.995)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def plot_predictive_forecast(training: pd.DataFrame, out_base: Path) -> None:
    df = training[training["method"] == "Predictive SAC"].copy()
    if df.empty or "forecast_outage_risk" not in df:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharex=True)
    for ax, col, title in [
        (axes[0], "forecast_outage_risk", "Risco predito de outage"),
        (axes[1], "forecast_soft_risk", "Risco predito de soft violation"),
    ]:
        for scenario in SCENARIOS:
            g = df[df["scenario"] == scenario]
            if g.empty:
                continue
            stat = g.groupby("episode")[col].agg(["mean", "std", "count"]).reset_index()
            x = stat["episode"].to_numpy(dtype=float)
            y = stat["mean"].to_numpy(dtype=float)
            err = 1.96 * stat["std"].fillna(0).to_numpy(dtype=float) / np.sqrt(stat["count"].clip(lower=1).to_numpy(dtype=float))
            ax.plot(x, y, label=scenario, linewidth=1.5)
            if stat["count"].max() >= 2:
                ax.fill_between(x, y - err, y + err, alpha=0.10)
        ax.set_title(title)
        ax.set_xlabel("Episodio")
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("Probabilidade media")
    axes[1].legend(fontsize=8, ncol=1)
    fig.suptitle("Sinais preditivos usados pelo Predictive SAC")
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def plot_action_allocations(steps: pd.DataFrame, out_base: Path) -> None:
    if steps.empty:
        return
    first_rows = steps[steps["slice_id"].astype(str).eq("0") | (steps["slice_id"] == 0)].copy()
    g = first_rows[first_rows["method"].isin(DRL_METHODS)]
    if g.empty:
        return
    stat = (
        g.groupby(["scenario", "method"])[["action_embb", "action_urllc", "action_mtc"]]
        .mean()
        .reset_index()
    )
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), sharey=True)
    axes = axes.ravel()
    slices = [("action_embb", "eMBB"), ("action_urllc", "URLLC"), ("action_mtc", "MTC")]
    x_base = np.arange(len(DRL_METHODS))
    for ax, scenario in zip(axes, SCENARIOS):
        scenario_stat = stat[stat["scenario"] == scenario].set_index("method").reindex(DRL_METHODS).fillna(0)
        bottom = np.zeros(len(DRL_METHODS))
        for col, label in slices:
            values = scenario_stat[col].to_numpy(dtype=float)
            ax.bar(x_base, values, bottom=bottom, label=label)
            bottom += values
        ax.set_title(scenario)
        ax.set_xticks(x_base)
        ax.set_xticklabels(DRL_METHODS, rotation=20, ha="right", fontsize=8)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.25)
    axes[-1].axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.96, 0.08))
    fig.supylabel("PRB configurado medio (%)")
    fig.suptitle("Distribuicao media de PRB por metodo")
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def plot_fig6(data: ComparisonData, out_base: Path) -> None:
    fig, axes = plt.subplots(5, 3, figsize=(13, 15), sharey=True)
    metrics = [
        ("eMBB", "throughput", "Throughput eMBB (Mbps)", "right"),
        ("MTC", "throughput", "Throughput MTC (Mbps)", "right"),
        ("URLLC", "urllc_buffer_pct", "Buffer URLLC / SLA (%)", "left"),
    ]
    for row, scenario in enumerate(SCENARIOS):
        for col, (slice_name, metric, xlabel, better) in enumerate(metrics):
            ax = axes[row, col]
            for method in METHOD_ORDER:
                if method in DRL_METHODS:
                    series = drl_distribution(data, scenario, method, slice_name, metric)
                else:
                    series = baseline_distribution(data, scenario, method, slice_name, metric)
                x, y = cdf(series)
                if x.size == 0:
                    continue
                ax.plot(x, y, label=method, linewidth=1.25, color=METHOD_COLORS.get(method))

            if metric == "throughput":
                target = SLA[scenario]["embb_min"] if slice_name == "eMBB" else SLA[scenario]["mtc_target"]
                ax.axvline(target, color="#111827", linestyle="--", linewidth=0.9)
                ax.axvspan(0, target, color="#fee2e2", alpha=0.22)
                ax.text(0.02, 0.86, "Outage", transform=ax.transAxes, fontsize=7)
                ax.text(0.70, 0.86, "SLA align", transform=ax.transAxes, fontsize=7)
            else:
                ax.axvline(100.0, color="#111827", linestyle="--", linewidth=0.9)
                right = ax.get_xlim()[1] if ax.get_xlim()[1] > 100 else 110
                ax.axvspan(100.0, right, color="#fee2e2", alpha=0.22)
                ax.text(0.02, 0.86, "SLA align", transform=ax.transAxes, fontsize=7)
                ax.text(0.70, 0.86, "Outage", transform=ax.transAxes, fontsize=7)
            if better == "right":
                ax.annotate("Better", xy=(0.88, 0.12), xytext=(0.62, 0.12), xycoords="axes fraction",
                            arrowprops={"arrowstyle": "->", "lw": 1.0}, fontsize=8)
            else:
                ax.annotate("Better", xy=(0.12, 0.12), xytext=(0.38, 0.12), xycoords="axes fraction",
                            arrowprops={"arrowstyle": "->", "lw": 1.0}, fontsize=8)
            ax.set_title(f"{scenario} - {xlabel}", fontsize=9)
            ax.set_xlabel(xlabel, fontsize=8)
            if col == 0:
                ax.set_ylabel("CDF", fontsize=8)
            ax.grid(True, alpha=0.22)
            ax.tick_params(labelsize=7)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(by_label.values(), by_label.keys(), loc="lower center", ncol=7, fontsize=8)
    fig.suptitle("CDFs RSLAQ-style com Predictive SAC", y=0.995)
    fig.tight_layout(rect=(0, 0.035, 1, 0.985))
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def paper_kpi_reliability_from_steps(steps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if steps.empty:
        return pd.DataFrame()
    for (method, scenario, seed, slice_name), g in steps.groupby(["method", "scenario", "seed", "slice"]):
        if slice_name == "eMBB":
            active = g[g["dTxBytes"].fillna(0) > 0]
            outage = active["throughput_mbps"] < SLA[scenario]["embb_min"]
            target = SLA[scenario]["embb_min"]
            unit = "throughput_mbps"
        elif slice_name == "URLLC":
            active = g[g["bufferBytes_max"].notna()]
            outage = active["bufferBytes_max"] > SLA[scenario]["urllc_bfs"]
            target = SLA[scenario]["urllc_bfs"]
            unit = "buffer_bytes"
        elif slice_name == "MTC":
            active = g[g["dLostPackets"].notna()]
            outage = active["dLostPackets"].fillna(0) > 0
            target = 0.0
            unit = "lost_packets_delta"
        else:
            continue
        samples = int(len(active))
        outage_rate = float(outage.mean()) if samples else float("nan")
        rows.append(
            {
                "metric_family": "paper_kpi",
                "method": method,
                "scenario": scenario,
                "seed": seed,
                "slice": slice_name,
                "samples": samples,
                "outage_rate": outage_rate,
                "reliability": 1.0 - outage_rate if np.isfinite(outage_rate) else float("nan"),
                "target": target,
                "target_unit": unit,
            }
        )
    return pd.DataFrame(rows)


def paper_kpi_reliability_from_baselines(ts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if ts.empty:
        return pd.DataFrame()
    for (method, scenario, seed, slice_name), g in ts.groupby(["method", "scenario", "seed", "slice"]):
        if slice_name == "eMBB":
            agg = g.groupby("timestamp_ms", as_index=False).agg(
                throughput_mbps=("thr_mbps", "sum"),
                tx_bytes=("tx_bytes_delta", "sum"),
            )
            active = agg[agg["tx_bytes"].fillna(0) > 0]
            outage = active["throughput_mbps"] < SLA[scenario]["embb_min"]
            target = SLA[scenario]["embb_min"]
            unit = "throughput_mbps"
        elif slice_name == "URLLC":
            valid = g[g["buffer_bytes"].fillna(-1) >= 0]
            active = valid.groupby("timestamp_ms", as_index=False)["buffer_bytes"].max()
            outage = active["buffer_bytes"] > SLA[scenario]["urllc_bfs"]
            target = SLA[scenario]["urllc_bfs"]
            unit = "buffer_bytes"
        elif slice_name == "MTC":
            active = g.groupby("timestamp_ms", as_index=False)["dropped_packets_delta"].sum()
            outage = active["dropped_packets_delta"].fillna(0) > 0
            target = 0.0
            unit = "lost_packets_delta"
        else:
            continue
        samples = int(len(active))
        outage_rate = float(outage.mean()) if samples else float("nan")
        rows.append(
            {
                "metric_family": "paper_kpi",
                "method": method,
                "scenario": scenario,
                "seed": seed,
                "slice": slice_name,
                "samples": samples,
                "outage_rate": outage_rate,
                "reliability": 1.0 - outage_rate if np.isfinite(outage_rate) else float("nan"),
                "target": target,
                "target_unit": unit,
            }
        )
    return pd.DataFrame(rows)


def internal_flag_reliability(steps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if steps.empty:
        return pd.DataFrame()
    for (method, scenario, seed, slice_name), g in steps.groupby(["method", "scenario", "seed", "slice"]):
        violation = g["outage_flag_bool"] | g["soft_flag_bool"]
        samples = int(len(g))
        violation_rate = float(violation.mean()) if samples else float("nan")
        rows.append(
            {
                "metric_family": "internal_flags",
                "method": method,
                "scenario": scenario,
                "seed": seed,
                "slice": slice_name,
                "samples": samples,
                "outage_rate": violation_rate,
                "reliability": 1.0 - violation_rate if np.isfinite(violation_rate) else float("nan"),
                "target": np.nan,
                "target_unit": "outage_or_soft_flag",
            }
        )
    return pd.DataFrame(rows)


def compute_reliability(data: ComparisonData) -> tuple[pd.DataFrame, pd.DataFrame]:
    paper_parts = [
        paper_kpi_reliability_from_steps(data.steps),
        paper_kpi_reliability_from_baselines(data.baselines),
    ]
    flag_rel = internal_flag_reliability(data.steps)
    paper_rel = pd.concat([p for p in paper_parts if not p.empty], ignore_index=True)
    return paper_rel, flag_rel


def plot_reliability(rel: pd.DataFrame, out_base: Path, title_suffix: str, include_insufficient: bool = True) -> None:
    if rel.empty:
        return
    scenarios = SCENARIOS if include_insufficient else [s for s in SCENARIOS if s != "insufficient_resources"]
    methods = ["Opt", "SAC", "RSLAQ/DDQN", "Predictive SAC"]
    slices = ["eMBB", "URLLC"]
    rows = []
    for scenario in scenarios:
        for method in methods:
            for slice_name in slices:
                g = rel[(rel["scenario"] == scenario) & (rel["method"] == method) & (rel["slice"] == slice_name)]
                rows.append(
                    {
                        "scenario": scenario,
                        "method": method,
                        "slice": slice_name,
                        "mean": g["reliability"].mean() if not g.empty else float("nan"),
                        "ci95": ci95(g["reliability"]) if not g.empty else float("nan"),
                    }
                )
    stat = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.9), sharey=True)
    width = 0.19
    x = np.arange(len(scenarios))
    offsets = np.linspace(-1.5 * width, 1.5 * width, len(methods))
    for ax, slice_name in zip(axes, slices):
        for i, method in enumerate(methods):
            g = stat[(stat["slice"] == slice_name) & (stat["method"] == method)].set_index("scenario").reindex(scenarios)
            values = g["mean"].to_numpy(dtype=float)
            errs = g["ci95"].to_numpy(dtype=float)
            ax.bar(x + offsets[i], values, width, label=method, color=METHOD_COLORS[method], yerr=errs, capsize=2)
        ax.set_title(f"Reliability {slice_name}")
        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, rotation=22, ha="right", fontsize=8)
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Reliability = 1 - P(violacao)")
    axes[1].legend(fontsize=8, loc="lower right")
    fig.suptitle(f"Reliability/outage por cenario - {title_suffix}")
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def metrics_summary(data: ComparisonData, paper_rel: pd.DataFrame, flag_rel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if not data.training.empty:
        for (method, scenario, seed), g in data.training.groupby(["method", "scenario", "seed"]):
            row = {
                "method": method,
                "scenario": scenario,
                "seed": seed,
                "episodes": int(g["episode"].nunique()),
                "steps_total": int(pd.to_numeric(g["steps"], errors="coerce").sum()) if "steps" in g else np.nan,
                "reward_mean": float(g["reward_total"].mean()),
                "reward_tail10_mean": float(g.tail(10)["reward_total"].mean()),
                "shaped_reward_mean": float(g["reward_aux"].mean()) if g["reward_aux"].notna().any() else np.nan,
                "outage_count_total": int(pd.to_numeric(g.get("outage_count", pd.Series(dtype=float)), errors="coerce").sum())
                if "outage_count" in g
                else np.nan,
                "soft_count_total": int(pd.to_numeric(g.get("soft_count", pd.Series(dtype=float)), errors="coerce").sum())
                if "soft_count" in g
                else np.nan,
            }
            rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    for rel, prefix in [(paper_rel, "paper"), (flag_rel, "flag")]:
        if rel.empty:
            continue
        pivot = rel.pivot_table(index=["method", "scenario", "seed"], columns="slice", values=["reliability", "outage_rate"])
        pivot.columns = [f"{prefix}_{metric}_{slice_name}" for metric, slice_name in pivot.columns]
        pivot = pivot.reset_index()
        out = out.merge(pivot, on=["method", "scenario", "seed"], how="left")
    return out


def method_scenario_summary(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    cols = [
        "reward_mean",
        "reward_tail10_mean",
        "steps_total",
        "paper_reliability_eMBB",
        "paper_reliability_URLLC",
        "paper_outage_rate_eMBB",
        "paper_outage_rate_URLLC",
        "flag_reliability_eMBB",
        "flag_reliability_URLLC",
        "flag_outage_rate_eMBB",
        "flag_outage_rate_URLLC",
    ]
    present = [c for c in cols if c in summary.columns]
    agg = summary.groupby(["method", "scenario"])[present].mean().reset_index()
    if {"paper_reliability_eMBB", "paper_reliability_URLLC"}.issubset(agg.columns):
        agg["paper_sla_score"] = agg[["paper_reliability_eMBB", "paper_reliability_URLLC"]].mean(axis=1)
    if {"flag_reliability_eMBB", "flag_reliability_URLLC"}.issubset(agg.columns):
        agg["flag_sla_score"] = agg[["flag_reliability_eMBB", "flag_reliability_URLLC"]].mean(axis=1)
    return agg


def compare_predictive_vs_rslaq(scenario_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario in SCENARIOS:
        pred = scenario_summary[(scenario_summary["scenario"] == scenario) & (scenario_summary["method"] == "Predictive SAC")]
        rslaq = scenario_summary[(scenario_summary["scenario"] == scenario) & (scenario_summary["method"] == "RSLAQ/DDQN")]
        if pred.empty or rslaq.empty:
            continue
        p = pred.iloc[0]
        r = rslaq.iloc[0]
        paper_delta = float(p.get("paper_sla_score", np.nan) - r.get("paper_sla_score", np.nan))
        flag_delta = float(p.get("flag_sla_score", np.nan) - r.get("flag_sla_score", np.nan))
        reward_delta = float(p.get("reward_mean", np.nan) - r.get("reward_mean", np.nan))
        paper_superior = bool(
            np.isfinite(paper_delta)
            and paper_delta > 0.01
            and p.get("paper_reliability_eMBB", -np.inf) >= r.get("paper_reliability_eMBB", np.inf) - 0.01
            and p.get("paper_reliability_URLLC", -np.inf) >= r.get("paper_reliability_URLLC", np.inf) - 0.01
        )
        flag_superior = bool(
            np.isfinite(flag_delta)
            and flag_delta > 0.01
            and p.get("flag_reliability_eMBB", -np.inf) >= r.get("flag_reliability_eMBB", np.inf) - 0.01
            and p.get("flag_reliability_URLLC", -np.inf) >= r.get("flag_reliability_URLLC", np.inf) - 0.01
        )
        rows.append(
            {
                "scenario": scenario,
                "paper_sla_delta_predictive_minus_rslaq": paper_delta,
                "flag_sla_delta_predictive_minus_rslaq": flag_delta,
                "reward_delta_predictive_minus_rslaq": reward_delta,
                "paper_kpi_supera_rslaq": paper_superior,
                "internal_flags_supera_rslaq": flag_superior,
                "interpretacao": (
                    "supera em KPI paper-style" if paper_superior else
                    "supera apenas nas flags internas" if flag_superior else
                    "nao supera RSLAQ/DDQN"
                ),
            }
        )
    return pd.DataFrame(rows)


def forecaster_loss_table(metrics: dict) -> pd.DataFrame:
    history = metrics.get("history", [])
    return pd.DataFrame(history)


def plot_forecaster_loss(metrics: dict, out_base: Path) -> None:
    df = forecaster_loss_table(metrics)
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(df["epoch"], df["train_loss"], label="train_loss", linewidth=1.6)
    if "val_loss" in df:
        ax.plot(df["epoch"], df["val_loss"], label="val_loss", linewidth=1.6)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("Treinamento do forecaster temporal")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def markdown_table(df: pd.DataFrame, floatfmt: str = ".4f") -> str:
    if df.empty:
        return "_Sem dados._\n"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |\n", "| " + " | ".join(["---"] * len(cols)) + " |\n"]
    for row in df.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("" if not np.isfinite(value) else format(value, floatfmt))
            else:
                values.append(str(value))
        out.append("| " + " | ".join(values) + " |\n")
    return "".join(out)


def write_report(
    data: ComparisonData,
    summary: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    winners: pd.DataFrame,
    out_dir: Path,
    paper_root: Path,
    predictive_root: Path,
) -> None:
    report = out_dir / "RELATORIO_ANALISE_PREDITIVA_RSLAQ.md"
    lines = []
    lines.append("# Analise comparativa RSLAQ vs Predictive SAC\n")
    lines.append(f"Campanha RSLAQ/SAC/DDQN base: `{paper_root}`.\n")
    lines.append(f"Campanha preditiva: `{predictive_root}`.\n")
    lines.append(f"Saida gerada em `{out_dir}`.\n\n")
    lines.append("## Escopo e criterios\n")
    lines.append("- Graficos e tabelas seguem a estrutura da pasta `controlled_20260514_175546`, adicionando `Predictive SAC`.\n")
    lines.append("- A avaliacao principal usa criterio SLA-first: eMBB e URLLC antes de reward.\n")
    lines.append("- Ha duas leituras de reliability: `paper_kpi`, recalculada a partir dos KPIs brutos com os limiares do artigo; e `internal_flags`, lida das flags de recompensa de cada campanha.\n")
    lines.append("- A campanha preditiva usa eMBB outage demand-aware; portanto `internal_flags` melhora o caso `low_traffic`, mas nao e estritamente a mesma metrica do paper-faithful.\n\n")
    lines.append("## Completude dos dados\n")
    train_counts = data.training.groupby(["method", "scenario"])["seed"].nunique().reset_index(name="seeds") if not data.training.empty else pd.DataFrame()
    lines.append(f"- Logs de treino combinados: {len(data.training)} linhas.\n")
    lines.append(f"- Arquivos `step_metrics.csv`: {data.steps['source_file'].nunique() if not data.steps.empty else 0}.\n")
    lines.append(f"- Arquivos baseline `timeseries.csv`: {data.baselines['source_file'].nunique() if not data.baselines.empty else 0}.\n")
    lines.append(markdown_table(train_counts))
    lines.append("\n")
    if data.forecaster_metrics:
        lines.append("## Forecaster temporal\n")
        lines.append(f"- Sequencias: `{data.forecaster_metrics.get('num_sequences')}`; treino: `{data.forecaster_metrics.get('train_sequences')}`; validacao: `{data.forecaster_metrics.get('val_sequences')}`.\n")
        lines.append(f"- Melhor loss: `{data.forecaster_metrics.get('best_loss')}`.\n\n")
    lines.append("## Resultado agregado por metodo/cenario\n")
    display_cols = [
        "method", "scenario", "reward_mean", "reward_tail10_mean",
        "paper_reliability_eMBB", "paper_reliability_URLLC", "paper_sla_score",
        "flag_reliability_eMBB", "flag_reliability_URLLC", "flag_sla_score",
    ]
    lines.append(markdown_table(scenario_summary[[c for c in display_cols if c in scenario_summary.columns]]))
    lines.append("\n")
    lines.append("## Predictive SAC supera RSLAQ/DDQN?\n")
    lines.append(markdown_table(winners))
    paper_wins = int(winners["paper_kpi_supera_rslaq"].sum()) if not winners.empty else 0
    flag_wins = int(winners["internal_flags_supera_rslaq"].sum()) if not winners.empty else 0
    lines.append("\n")
    lines.append(f"Conclusao quantitativa: em metrica `paper_kpi`, Predictive SAC supera RSLAQ/DDQN em {paper_wins}/{len(winners)} cenarios avaliados. Em `internal_flags`, supera em {flag_wins}/{len(winners)} cenarios.\n")
    if paper_wins == 0:
        lines.append("Conclusao: com a metrica paper-style recalculada dos KPIs brutos, a implementacao preditiva ainda nao supera o RSLAQ/DDQN de forma robusta. Ela melhora a logica operacional em cenarios de baixa demanda quando avaliada pelas flags internas demand-aware, mas isso nao e uma superacao direta do criterio original do artigo.\n")
    elif paper_wins < len(winners):
        lines.append("Conclusao: ha ganhos parciais, mas a superacao nao e uniforme em todos os cenarios. A proxima iteracao deve focar nos cenarios onde o delta paper-style ainda e negativo.\n")
    else:
        lines.append("Conclusao: Predictive SAC supera RSLAQ/DDQN nos cenarios avaliados pelo criterio SLA-first paper-style.\n")
    lines.append("\n## Observacoes tecnicas\n")
    lines.append("- `low_traffic` segue problemático no criterio paper-style porque o trafego eMBB oferecido e menor que o SLA minimo absoluto do artigo; a versao preditiva corrige essa interpretacao via demand-aware outage.\n")
    lines.append("- O reward da preditiva em `predictive_sac_training_log.csv` tem duas colunas: `base_reward` e `shaped_reward`; as figuras comparativas usam `base_reward` para aproximar a escala dos demais metodos.\n")
    lines.append("- `MTC` permanece como no-policy no desenho RSLAQ; por isso a decisao de superacao foi baseada em eMBB e URLLC.\n")
    lines.append("\n## Figuras geradas\n")
    for path in sorted((out_dir / "figures").glob("*.png")):
        lines.append(f"- `figures/{path.name}`\n")
    report.write_text("".join(lines), encoding="utf-8")


def write_metadata(out_dir: Path, paper_root: Path, predictive_root: Path) -> None:
    (out_dir / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "- Gerada analise comparativa com os resultados preditivos de 2026-05-18.\n"
        f"- Campanha base: `{paper_root}`.\n"
        f"- Campanha preditiva: `{predictive_root}`.\n"
        "- Geradas tabelas CSV, figuras PNG/PDF e relatorio Markdown.\n",
        encoding="utf-8",
    )
    (out_dir / "MODIFIED_FILES.md").write_text(
        "# Arquivos criados/modificados por esta analise\n\n"
        "- `analysis_rslaq_validation/analyze_predictive_campaign.py`\n"
        "- `analysis_rslaq_validation/predictive_20260518_132018/**`\n\n"
        "Arquivos de resultados brutos modificados: nenhum.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper_root", required=True, type=Path)
    parser.add_argument("--predictive_root", required=True, type=Path)
    parser.add_argument("--output_dir", required=True, type=Path)
    args = parser.parse_args()

    paper_root = args.paper_root.resolve()
    predictive_root = args.predictive_root.resolve()
    out_dir = args.output_dir.resolve()
    fig_dir = out_dir / "figures"
    table_dir = out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    data = load_data(paper_root, predictive_root)
    paper_rel, flag_rel = compute_reliability(data)
    summary = metrics_summary(data, paper_rel, flag_rel)
    scenario_summary = method_scenario_summary(summary)
    winners = compare_predictive_vs_rslaq(scenario_summary)

    data.training.to_csv(table_dir / "training_logs_combined.csv", index=False)
    data.steps.to_csv(table_dir / "step_metrics_combined_index.csv", index=False)
    paper_rel.to_csv(table_dir / "reliability_by_seed_paper_kpi.csv", index=False)
    flag_rel.to_csv(table_dir / "reliability_by_seed_internal_flags.csv", index=False)
    summary.to_csv(table_dir / "metrics_summary.csv", index=False)
    scenario_summary.to_csv(table_dir / "metrics_summary_by_method_scenario.csv", index=False)
    winners.to_csv(table_dir / "predictive_vs_rslaq_winners.csv", index=False)
    forecaster_loss_table(data.forecaster_metrics).to_csv(table_dir / "forecaster_loss_history.csv", index=False)

    plot_reward_by_method(data.training, fig_dir / "reward_sac_ddqn_predictive_by_scenario")
    plot_predictive_forecast(data.training, fig_dir / "predictive_forecast_risk_by_episode")
    plot_action_allocations(data.steps, fig_dir / "action_allocation_by_scenario")
    plot_fig6(data, fig_dir / "fig6_cdf_rslaq_style_with_predictive")
    plot_reliability(paper_rel, fig_dir / "fig7_reliability_paper_kpi_with_predictive", "paper_kpi", include_insufficient=True)
    plot_reliability(flag_rel, fig_dir / "fig7_reliability_internal_flags_with_predictive", "internal_flags", include_insufficient=True)
    plot_forecaster_loss(data.forecaster_metrics, fig_dir / "forecaster_loss")

    write_report(data, summary, scenario_summary, winners, out_dir, paper_root, predictive_root)
    write_metadata(out_dir, paper_root, predictive_root)

    print(f"output_dir={out_dir}")
    print(f"training_rows={len(data.training)}")
    print(f"step_rows={len(data.steps)}")
    print(f"baseline_rows={len(data.baselines)}")
    print(f"paper_rel_rows={len(paper_rel)}")
    print(f"flag_rel_rows={len(flag_rel)}")
    print(f"predictive_supera_paper_kpi={int(winners['paper_kpi_supera_rslaq'].sum()) if not winners.empty else 0}/{len(winners)}")
    print(f"predictive_supera_internal_flags={int(winners['internal_flags_supera_rslaq'].sum()) if not winners.empty else 0}/{len(winners)}")


if __name__ == "__main__":
    main()
