#!/usr/bin/env python3
"""Analyze one controlled RSLAQ validation campaign.

The script is read-only with respect to ns-3 and ns-o-ran-gym results. It writes
derived tables, figures, and a short report under the requested output folder.
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

SCENARIO_LABELS = {
    "low_traffic": "low_traffic",
    "normal": "normal",
    "congestion": "congestion",
    "stressed": "stressed",
    "insufficient_resources": "insufficient_resources",
}

SLICES = ["eMBB", "URLLC", "MTC"]
SLICE_IDS = {"eMBB": 0, "URLLC": 1, "MTC": 2}

SLA = {
    "low_traffic": {"embb_min": 10.0, "embb_soft": 15.0, "urllc_bfs": 10000.0, "mtc_target": 10.0},
    "normal": {"embb_min": 10.0, "embb_soft": 15.0, "urllc_bfs": 10000.0, "mtc_target": 10.0},
    "congestion": {"embb_min": 10.0, "embb_soft": 15.0, "urllc_bfs": 10000.0, "mtc_target": 20.0},
    "stressed": {"embb_min": 20.0, "embb_soft": 25.0, "urllc_bfs": 10000.0, "mtc_target": 20.0},
    "insufficient_resources": {"embb_min": 20.0, "embb_soft": 25.0, "urllc_bfs": 10000.0, "mtc_target": 20.0},
}

TRAFFIC_MBPS = {
    "low_traffic": {"eMBB": 5.0, "URLLC": 1.0, "MTC": 2.0},
    "normal": {"eMBB": 70.0, "URLLC": 1.0, "MTC": 2.0},
    "congestion": {"eMBB": 100.0, "URLLC": 1.0, "MTC": 100.0},
    "stressed": {"eMBB": 100.0, "URLLC": 1.0, "MTC": 100.0},
    "insufficient_resources": {"eMBB": 100.0, "URLLC": 2.0, "MTC": 100.0},
}

BASELINE_LABELS = {
    "pure_rr": "RR",
    "pure_pf": "PF",
    "pure_bcqi": "BCQI",
    "slice_weighted_pf": "Opt",
}

METHOD_ORDER = ["RR", "PF", "BCQI", "Opt", "SAC", "RSLAQ/DDQN"]
METHOD_COLORS = {
    "RR": "#777777",
    "PF": "#3b82f6",
    "BCQI": "#22c55e",
    "Opt": "#f59e0b",
    "SAC": "#8b5cf6",
    "RSLAQ/DDQN": "#dc2626",
}


@dataclass
class CampaignData:
    config: dict
    training: pd.DataFrame
    drl_steps: pd.DataFrame
    baselines: pd.DataFrame
    baseline_summary: pd.DataFrame


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, **kwargs)
    except Exception as exc:
        print(f"warn: failed to read {path}: {exc}")
        return pd.DataFrame()


def ci95(values: Iterable[float]) -> float:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 5:
        return float("nan")
    return float(1.96 * arr.std(ddof=1) / math.sqrt(arr.size))


def cdf(values: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.array([]), np.array([])
    arr = np.sort(arr)
    return arr, np.arange(1, arr.size + 1) / arr.size


def parse_algo_dir(name: str) -> tuple[str, str, int] | None:
    match = re.match(r"^(ddqn|sac)_(.+)_seed(\d+)$", name)
    if not match:
        return None
    algo, scenario, seed = match.groups()
    if scenario not in SCENARIOS:
        return None
    return algo, scenario, int(seed)


def load_config(campaign_path: Path) -> dict:
    config_path = campaign_path / "campaign_config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text())


def load_training(campaign_path: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for algo_dir in sorted(campaign_path.iterdir()):
        parsed = parse_algo_dir(algo_dir.name)
        if parsed is None or not algo_dir.is_dir():
            continue
        algo, scenario, seed = parsed
        path = algo_dir / f"{algo}_training_log.csv"
        df = read_csv(path)
        if df.empty:
            continue
        df["algo"] = algo
        df["method"] = "RSLAQ/DDQN" if algo == "ddqn" else "SAC"
        df["scenario"] = scenario
        df["seed"] = seed
        df["source_file"] = str(path)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_drl_steps(campaign_path: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
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
    for algo_dir in sorted(campaign_path.iterdir()):
        parsed = parse_algo_dir(algo_dir.name)
        if parsed is None or not algo_dir.is_dir():
            continue
        algo, scenario, seed = parsed
        for path in sorted(algo_dir.glob("*/step_metrics.csv")):
            df = read_csv(path, usecols=lambda c: c in usecols)
            if df.empty:
                continue
            df["algo"] = algo
            df["method"] = "RSLAQ/DDQN" if algo == "ddqn" else "SAC"
            df["scenario"] = scenario
            df["seed"] = seed
            df["source_file"] = str(path)
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    for col in ["throughput_mbps", "dTxBytes", "dRxBytes", "bufferBytes_mean", "bufferBytes_max"]:
        if col in out:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def baseline_result_dirs(campaign_path: Path) -> list[tuple[str, str, int, Path]]:
    manifest = campaign_path / "baselines" / "results_rslaq_network_only" / "batch_manifest.csv"
    df = read_csv(manifest)
    dirs: list[tuple[str, str, int, Path]] = []
    if df.empty:
        return dirs
    ok = df[df["status"].astype(str).str.lower().eq("ok")].copy()
    for row in ok.itertuples(index=False):
        mode = str(row.baseline_mode)
        method = BASELINE_LABELS.get(mode, mode)
        dirs.append((str(row.scenario), method, int(row.seed), Path(str(row.result_dir))))
    return dirs


def load_baselines(campaign_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    timeseries_frames: list[pd.DataFrame] = []
    summary_frames: list[pd.DataFrame] = []
    for scenario, method, seed, result_dir in baseline_result_dirs(campaign_path):
        ts_path = result_dir / "timeseries.csv"
        ts = read_csv(ts_path)
        if not ts.empty:
            ts["scenario"] = scenario
            ts["method"] = method
            ts["seed"] = seed
            ts["source_file"] = str(ts_path)
            timeseries_frames.append(ts)
        summary_path = result_dir / "summary.csv"
        summary = read_csv(summary_path)
        if not summary.empty:
            summary["scenario"] = scenario
            summary["method"] = method
            summary["seed"] = seed
            summary["source_file"] = str(summary_path)
            summary_frames.append(summary)
    ts_out = pd.concat(timeseries_frames, ignore_index=True) if timeseries_frames else pd.DataFrame()
    sm_out = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    if not ts_out.empty:
        for col in ["thr_mbps", "tx_bytes_delta", "rx_bytes_delta", "buffer_bytes", "dropped_packets_delta"]:
            if col in ts_out:
                ts_out[col] = pd.to_numeric(ts_out[col], errors="coerce")
    return ts_out, sm_out


def load_campaign(campaign_path: Path) -> CampaignData:
    baseline_timeseries, baseline_summary = load_baselines(campaign_path)
    return CampaignData(
        config=load_config(campaign_path),
        training=load_training(campaign_path),
        drl_steps=load_drl_steps(campaign_path),
        baselines=baseline_timeseries,
        baseline_summary=baseline_summary,
    )


def drl_distribution(data: CampaignData, scenario: str, method: str, slice_name: str, metric: str) -> pd.Series:
    if data.drl_steps.empty:
        return pd.Series(dtype=float)
    df = data.drl_steps
    g = df[(df["scenario"] == scenario) & (df["method"] == method) & (df["slice"] == slice_name)]
    if g.empty:
        return pd.Series(dtype=float)
    if metric == "throughput":
        return g["throughput_mbps"]
    if metric == "urllc_buffer_pct":
        return g["bufferBytes_max"] / SLA[scenario]["urllc_bfs"] * 100.0
    return pd.Series(dtype=float)


def baseline_distribution(data: CampaignData, scenario: str, method: str, slice_name: str, metric: str) -> pd.Series:
    if data.baselines.empty:
        return pd.Series(dtype=float)
    df = data.baselines
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


def plot_reward_by_scenario(training: pd.DataFrame, method: str, out_base: Path) -> None:
    if training.empty:
        return
    df = training[training["method"] == method].copy()
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for scenario in SCENARIOS:
        g = df[df["scenario"] == scenario]
        if g.empty:
            continue
        stat = (
            g.groupby("episode")["total_reward"]
            .agg(["mean", "std", "count"])
            .reset_index()
            .sort_values("episode")
        )
        y = stat["mean"].to_numpy(dtype=float)
        x = stat["episode"].to_numpy(dtype=float)
        err = 1.96 * stat["std"].fillna(0).to_numpy(dtype=float) / np.sqrt(stat["count"].clip(lower=1).to_numpy(dtype=float))
        ax.plot(x, y, label=scenario, linewidth=1.8)
        if stat["count"].max() >= 5:
            ax.fill_between(x, y - err, y + err, alpha=0.12)
    ax.axhline(0.0, color="#222222", linewidth=0.9)
    ymin, ymax = ax.get_ylim()
    if ymin < 0:
        ax.axhspan(ymin, 0, color="#fee2e2", alpha=0.35, label="reward < 0")
    ax.set_title(f"Reward por episodio - {method}")
    ax.set_xlabel("Episodio")
    ax.set_ylabel("Reward total")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def plot_reward_comparison(training: pd.DataFrame, out_base: Path) -> None:
    if training.empty:
        return
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), sharex=True)
    axes = axes.ravel()
    for ax, scenario in zip(axes, SCENARIOS):
        for method in ["RSLAQ/DDQN", "SAC"]:
            g = training[(training["scenario"] == scenario) & (training["method"] == method)]
            if g.empty:
                continue
            stat = g.groupby("episode")["total_reward"].agg(["mean", "std", "count"]).reset_index()
            x = stat["episode"].to_numpy(dtype=float)
            y = stat["mean"].to_numpy(dtype=float)
            err = 1.96 * stat["std"].fillna(0).to_numpy(dtype=float) / np.sqrt(stat["count"].clip(lower=1).to_numpy(dtype=float))
            ax.plot(x, y, label=method, color=METHOD_COLORS[method], linewidth=1.7)
            if stat["count"].max() >= 5:
                ax.fill_between(x, y - err, y + err, color=METHOD_COLORS[method], alpha=0.12)
        ax.axhline(0.0, color="#222222", linewidth=0.8)
        ax.set_title(scenario)
        ax.grid(True, alpha=0.22)
    axes[-1].axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.97, 0.08))
    fig.supxlabel("Episodio")
    fig.supylabel("Reward total")
    fig.suptitle("Reward DDQN vs SAC - mesmo orcamento configurado", y=0.995)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def draw_better_arrow(ax: plt.Axes, direction: str) -> None:
    if direction == "right":
        ax.annotate("Better", xy=(0.88, 0.12), xytext=(0.62, 0.12), xycoords="axes fraction",
                    arrowprops={"arrowstyle": "->", "lw": 1.0}, fontsize=8)
    else:
        ax.annotate("Better", xy=(0.12, 0.12), xytext=(0.38, 0.12), xycoords="axes fraction",
                    arrowprops={"arrowstyle": "->", "lw": 1.0}, fontsize=8)


def plot_fig6(data: CampaignData, out_base: Path) -> None:
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
                if method in ["SAC", "RSLAQ/DDQN"]:
                    series = drl_distribution(data, scenario, method, slice_name, metric)
                else:
                    series = baseline_distribution(data, scenario, method, slice_name, metric)
                x, y = cdf(series)
                if x.size == 0:
                    continue
                ax.plot(x, y, label=method, linewidth=1.4, color=METHOD_COLORS.get(method))

            if metric == "throughput":
                target = SLA[scenario]["embb_min"] if slice_name == "eMBB" else SLA[scenario]["mtc_target"]
                ax.axvline(target, color="#111827", linestyle="--", linewidth=0.9)
                ax.axvspan(0, target, color="#fee2e2", alpha=0.22)
                ax.text(0.02, 0.86, "Outage", transform=ax.transAxes, fontsize=7)
                ax.text(0.72, 0.86, "SLA align", transform=ax.transAxes, fontsize=7)
            else:
                ax.axvline(100.0, color="#111827", linestyle="--", linewidth=0.9)
                ax.axvspan(100.0, ax.get_xlim()[1] if ax.get_xlim()[1] > 100 else 110, color="#fee2e2", alpha=0.22)
                ax.text(0.02, 0.86, "SLA align", transform=ax.transAxes, fontsize=7)
                ax.text(0.72, 0.86, "Outage", transform=ax.transAxes, fontsize=7)
            draw_better_arrow(ax, better)
            ax.set_title(f"{SCENARIO_LABELS[scenario]} - {xlabel}", fontsize=9)
            ax.set_xlabel(xlabel, fontsize=8)
            if col == 0:
                ax.set_ylabel("CDF", fontsize=8)
            ax.grid(True, alpha=0.22)
            ax.tick_params(labelsize=7)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(by_label.values(), by_label.keys(), loc="lower center", ncol=6, fontsize=8)
    fig.suptitle("CDFs RSLAQ-style - campanha controlada paper_faithful", y=0.995)
    fig.tight_layout(rect=(0, 0.035, 1, 0.985))
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def seed_reliability_from_drl(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame()
    for (method, scenario, seed, slice_name), g in df.groupby(["method", "scenario", "seed", "slice"]):
        if slice_name == "eMBB":
            active = g[g["dTxBytes"].fillna(0) > 0]
            target = SLA[scenario]["embb_min"]
            outage = active["throughput_mbps"] < target
            unit = "throughput_mbps"
        elif slice_name == "URLLC":
            active = g[g["bufferBytes_max"].notna()]
            target = SLA[scenario]["urllc_bfs"]
            outage = active["bufferBytes_max"] > target
            unit = "buffer_bytes"
        elif slice_name == "MTC":
            active = g[g["dLostPackets"].notna()]
            target = 0.0
            outage = active["dLostPackets"].fillna(0) > 0
            unit = "lost_packets_delta"
        else:
            continue
        samples = int(len(active))
        outage_rate = float(outage.mean()) if samples else float("nan")
        rows.append(
            {
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


def seed_reliability_from_baselines(ts: pd.DataFrame) -> pd.DataFrame:
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
            if valid.empty:
                rows.append(
                    {
                        "method": method,
                        "scenario": scenario,
                        "seed": seed,
                        "slice": slice_name,
                        "samples": 0,
                        "outage_rate": float("nan"),
                        "reliability": float("nan"),
                        "target": SLA[scenario]["urllc_bfs"],
                        "target_unit": "buffer_bytes",
                    }
                )
                continue
            active = valid.groupby("timestamp_ms", as_index=False)["buffer_bytes"].max()
            outage = active["buffer_bytes"] > SLA[scenario]["urllc_bfs"]
            target = SLA[scenario]["urllc_bfs"]
            unit = "buffer_bytes"
        elif slice_name == "MTC":
            agg = g.groupby("timestamp_ms", as_index=False)["dropped_packets_delta"].sum()
            outage = agg["dropped_packets_delta"].fillna(0) > 0
            active = agg
            target = 0.0
            unit = "lost_packets_delta"
        else:
            continue
        samples = int(len(active))
        outage_rate = float(outage.mean()) if samples else float("nan")
        rows.append(
            {
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


def compute_reliability(data: CampaignData) -> pd.DataFrame:
    parts = [seed_reliability_from_drl(data.drl_steps), seed_reliability_from_baselines(data.baselines)]
    parts = [p for p in parts if not p.empty]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def plot_reliability(rel: pd.DataFrame, out_base: Path, include_insufficient: bool) -> None:
    if rel.empty:
        return
    scenarios = SCENARIOS if include_insufficient else [s for s in SCENARIOS if s != "insufficient_resources"]
    methods = ["Opt", "SAC", "RSLAQ/DDQN"]
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
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    width = 0.23
    x = np.arange(len(scenarios))
    for ax, slice_name in zip(axes, slices):
        for i, method in enumerate(methods):
            g = stat[(stat["slice"] == slice_name) & (stat["method"] == method)].set_index("scenario").reindex(scenarios)
            values = g["mean"].to_numpy(dtype=float)
            errs = g["ci95"].to_numpy(dtype=float)
            ax.bar(x + (i - 1) * width, values, width, label=method, color=METHOD_COLORS[method], yerr=errs, capsize=2)
        ax.set_title(f"Reliability {slice_name}")
        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, rotation=22, ha="right", fontsize=8)
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Reliability = 1 - P(k_out)")
    axes[1].legend(fontsize=8, loc="lower right")
    title = "Reliability/outage por cenario"
    if include_insufficient:
        title += " (diagnostico incluindo insufficient_resources)"
    fig.suptitle(title)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def metrics_summary(data: CampaignData, rel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    if not data.training.empty:
        for (method, scenario, seed), g in data.training.groupby(["method", "scenario", "seed"]):
            rows.append(
                {
                    "method": method,
                    "scenario": scenario,
                    "seed": seed,
                    "episodes": int(g["episode"].nunique()),
                    "steps_total": int(g["steps"].sum()) if "steps" in g else np.nan,
                    "interaction_budget_configured": data.config.get("interaction_budget", np.nan),
                    "reward_mean": float(g["total_reward"].mean()),
                    "reward_std": float(g["total_reward"].std(ddof=1)) if len(g) > 1 else np.nan,
                    "soft_count_total": int(g["soft_count"].sum()) if "soft_count" in g else np.nan,
                    "outage_count_total": int(g["outage_count"].sum()) if "outage_count" in g else np.nan,
                }
            )
    if not data.baseline_summary.empty:
        for (method, scenario, seed), g in data.baseline_summary.groupby(["method", "scenario", "seed"]):
            row = {
                "method": method,
                "scenario": scenario,
                "seed": seed,
                "episodes": 1,
                "steps_total": int(data.baselines[(data.baselines["method"] == method) & (data.baselines["scenario"] == scenario) & (data.baselines["seed"] == seed)]["timestamp_ms"].nunique())
                if not data.baselines.empty
                else np.nan,
                "interaction_budget_configured": np.nan,
                "reward_mean": np.nan,
                "reward_std": np.nan,
                "soft_count_total": np.nan,
                "outage_count_total": np.nan,
            }
            rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty or rel.empty:
        return out
    pivot = rel.pivot_table(index=["method", "scenario", "seed"], columns="slice", values=["reliability", "outage_rate"])
    pivot.columns = [f"{metric}_{slice_name}" for metric, slice_name in pivot.columns]
    pivot = pivot.reset_index()
    return out.merge(pivot, on=["method", "scenario", "seed"], how="left")


def low_traffic_audit(data: CampaignData) -> pd.DataFrame:
    rows = []
    scenario = "low_traffic"
    combined = []
    if not data.drl_steps.empty:
        combined.append(
            data.drl_steps[data.drl_steps["scenario"] == scenario][["method", "seed", "slice", "throughput_mbps"]].copy()
        )
    if not data.baselines.empty:
        ts = data.baselines[data.baselines["scenario"] == scenario].copy()
        if not ts.empty:
            agg = ts.groupby(["method", "seed", "timestamp_ms", "slice"], as_index=False)["thr_mbps"].sum()
            agg = agg.rename(columns={"thr_mbps": "throughput_mbps"})
            combined.append(agg[["method", "seed", "slice", "throughput_mbps"]])
    measurements = pd.concat(combined, ignore_index=True) if combined else pd.DataFrame()
    for slice_name in SLICES:
        measured = measurements[measurements["slice"] == slice_name]["throughput_mbps"] if not measurements.empty else pd.Series(dtype=float)
        sla_min = SLA[scenario]["embb_min"] if slice_name == "eMBB" else np.nan
        sla_soft = SLA[scenario]["embb_soft"] if slice_name == "eMBB" else (SLA[scenario]["urllc_bfs"] if slice_name == "URLLC" else SLA[scenario]["mtc_target"])
        offered = TRAFFIC_MBPS[scenario][slice_name]
        if slice_name == "eMBB" and offered < SLA[scenario]["embb_min"]:
            status = "erro provável de unidade/configuração"
        elif measured.empty:
            status = "inconclusivo por falta de métrica"
        elif np.nanmax(measured) >= (sla_min if np.isfinite(sla_min) else 0):
            status = "factível"
        else:
            status = "aparentemente infactível"
        rows.append(
            {
                "scenario": scenario,
                "slice": slice_name,
                "offered_traffic_estimated_mbps": offered,
                "throughput_measured_mean_mbps": float(measured.mean()) if not measured.empty else np.nan,
                "throughput_measured_max_mbps": float(measured.max()) if not measured.empty else np.nan,
                "sla_min": sla_min,
                "sla_soft_or_max": sla_soft,
                "physical_status": status,
                "notes": "eMBB offered traffic is 5 Mbps while paper SLA minimum is 10 Mbps" if slice_name == "eMBB" else "",
            }
        )
    return pd.DataFrame(rows)


def write_report(
    data: CampaignData,
    rel: pd.DataFrame,
    summary: pd.DataFrame,
    low: pd.DataFrame,
    out_dir: Path,
    campaign_path: Path,
) -> None:
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

    report = out_dir / "RELATORIO_ANALISE_CAMPANHA_CONTROLADA.md"
    lines = []
    lines.append("# Analise da campanha controlada RSLAQ paper_faithful\n")
    lines.append(f"Campanha analisada: `{campaign_path}`.\n")
    lines.append("## Escopo\n")
    lines.append("- Nenhum arquivo do ns-3 foi modificado por esta analise.\n")
    lines.append("- Foram lidos apenas logs existentes da campanha controlada e baselines contidos na propria pasta.\n")
    lines.append(f"- Saida gerada em `{out_dir}`.\n")
    lines.append("## Configuracao da campanha\n")
    for key, value in data.config.items():
        lines.append(f"- `{key}`: `{value}`\n")
    lines.append("## Completude dos dados\n")
    train_counts = data.training.groupby(["method", "scenario"])["seed"].nunique().reset_index(name="seeds") if not data.training.empty else pd.DataFrame()
    step_files = data.drl_steps["source_file"].nunique() if not data.drl_steps.empty else 0
    baseline_runs = data.baselines["source_file"].nunique() if not data.baselines.empty else 0
    lines.append(f"- Logs de treino: {len(data.training)} linhas; seeds por metodo/cenario: {train_counts.to_dict(orient='records')}.\n")
    lines.append(f"- Arquivos `step_metrics.csv`: {step_files}.\n")
    lines.append(f"- Arquivos `timeseries.csv` de baseline: {baseline_runs}.\n")
    lines.append("## Principais resultados\n")
    if not summary.empty:
        top = (
            summary.groupby(["method", "scenario"])
            .agg(
                reward_mean=("reward_mean", "mean"),
                rel_embb=("reliability_eMBB", "mean"),
                rel_urllc=("reliability_URLLC", "mean"),
                outage_embb=("outage_rate_eMBB", "mean"),
                outage_urllc=("outage_rate_URLLC", "mean"),
            )
            .reset_index()
        )
        lines.append(markdown_table(top))
        lines.append("\n")
    lines.append("## Low traffic\n")
    if not low.empty:
        lines.append(markdown_table(low))
        lines.append("\n")
    lines.append("Interpretacao: no `low_traffic`, o trafego oferecido eMBB estimado e 5 Mbps, abaixo do SLA minimo paper-faithful de 10 Mbps. Portanto falha de eMBB nesse cenario deve ser tratada como incompatibilidade de unidade/configuracao ou alvo fisicamente inalinhado com a carga oferecida, nao como prova isolada de incapacidade do algoritmo.\n")
    lines.append("## Reliability/outage\n")
    if not rel.empty:
        stat = (
            rel[rel["slice"].isin(["eMBB", "URLLC"])]
            .groupby(["method", "scenario", "slice"])
            .agg(reliability_mean=("reliability", "mean"), reliability_std=("reliability", "std"), outage_rate_mean=("outage_rate", "mean"), seeds=("seed", "nunique"))
            .reset_index()
        )
        lines.append(markdown_table(stat))
        lines.append("\n")
    lines.append("## Validade cientifica\n")
    lines.append("- DDQN e SAC usam o mesmo orcamento configurado da campanha (`interaction_budget=5000`), mas os steps efetivos por episodio variam por termino antecipado.\n")
    lines.append("- Reward nao foi usado isoladamente como conclusao; as tabelas incluem reliability e outage por slice.\n")
    lines.append("- URLLC dos baselines e calculado quando `buffer_bytes` esta presente na serie temporal; quando ausente, o valor fica `NaN` e nao foi inventado.\n")
    lines.append("- `insufficient_resources` aparece em figura diagnostica separada de reliability.\n")
    lines.append("## Figuras\n")
    for name in [
        "reward_ddqn_by_scenario",
        "reward_sac_by_scenario",
        "reward_ddqn_vs_sac_controlled",
        "fig6_cdf_rslaq_style",
        "fig7_reliability_rslaq_style",
        "fig7_reliability_rslaq_style_including_insufficient",
    ]:
        lines.append(f"- `figures/{name}.png` e `figures/{name}.pdf`\n")
    report.write_text("".join(lines), encoding="utf-8")


def write_changelog(out_dir: Path, campaign_path: Path) -> None:
    (out_dir / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "- Criado script de analise dedicado para campanha controlada paper_faithful.\n"
        f"- Entrada analisada: `{campaign_path}`.\n"
        "- Geradas tabelas CSV, figuras PNG/PDF a 300 dpi e relatorio markdown.\n"
        "- Nenhum arquivo de ns-3 foi modificado.\n",
        encoding="utf-8",
    )
    (out_dir / "MODIFIED_FILES.md").write_text(
        "# Arquivos criados/modificados por esta analise\n\n"
        "- `analysis_rslaq_validation/analyze_controlled_campaign.py` (novo script de analise)\n"
        "- `analysis_rslaq_validation/controlled_20260514_175546/**` (artefatos derivados)\n\n"
        "Arquivos do ns-3 modificados: nenhum.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign_path", required=True, type=Path)
    parser.add_argument("--output_dir", required=True, type=Path)
    args = parser.parse_args()

    campaign_path = args.campaign_path.resolve()
    out_dir = args.output_dir.resolve()
    fig_dir = out_dir / "figures"
    table_dir = out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    data = load_campaign(campaign_path)
    rel = compute_reliability(data)
    summary = metrics_summary(data, rel)
    low = low_traffic_audit(data)

    data.training.to_csv(table_dir / "training_logs_combined.csv", index=False)
    if not rel.empty:
        rel.to_csv(table_dir / "reliability_by_seed.csv", index=False)
        rel[["method", "scenario", "seed", "slice", "samples", "outage_rate", "target", "target_unit"]].to_csv(
            table_dir / "outage_by_seed.csv", index=False
        )
    summary.to_csv(table_dir / "metrics_summary.csv", index=False)
    low.to_csv(table_dir / "low_traffic_audit.csv", index=False)

    plot_reward_by_scenario(data.training, "RSLAQ/DDQN", fig_dir / "reward_ddqn_by_scenario")
    plot_reward_by_scenario(data.training, "SAC", fig_dir / "reward_sac_by_scenario")
    plot_reward_comparison(data.training, fig_dir / "reward_ddqn_vs_sac_controlled")
    plot_fig6(data, fig_dir / "fig6_cdf_rslaq_style")
    plot_reliability(rel, fig_dir / "fig7_reliability_rslaq_style", include_insufficient=False)
    plot_reliability(rel, fig_dir / "fig7_reliability_rslaq_style_including_insufficient", include_insufficient=True)

    write_report(data, rel, summary, low, out_dir, campaign_path)
    write_changelog(out_dir, campaign_path)

    print(f"output_dir={out_dir}")
    print(f"training_rows={len(data.training)}")
    print(f"drl_step_rows={len(data.drl_steps)}")
    print(f"drl_step_files={data.drl_steps['source_file'].nunique() if not data.drl_steps.empty else 0}")
    print(f"baseline_timeseries_files={data.baselines['source_file'].nunique() if not data.baselines.empty else 0}")
    print(f"reliability_rows={len(rel)}")


if __name__ == "__main__":
    main()
