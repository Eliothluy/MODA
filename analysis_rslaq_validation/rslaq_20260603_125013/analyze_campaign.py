#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path("/home/elioth/Documentos/artigo_jussi")
CAMPAIGN = ROOT / "ns-o-ran-gym/results_controlled/rslaq_sla_resource_efficiency/20260603_125013"
OUT = ROOT / "analysis_rslaq_validation/rslaq_20260603_125013"
FIG = OUT / "figures"
TAB = OUT / "tables"
REPORT = OUT / "RELATORIO_ANALISE_RSLAQ_20260603_125013.md"

SCENARIOS = ["low_traffic", "normal", "congestion", "stressed", "insufficient_resources"]
SCENARIO_LABELS = {
    "low_traffic": "Low traffic",
    "normal": "Normal",
    "congestion": "Congestion",
    "stressed": "Stressed",
    "insufficient_resources": "Insufficient",
}
SLICES = ["eMBB", "URLLC", "MTC"]
SLICE_WEIGHTS = {"eMBB": 0.3333, "URLLC": 0.4, "MTC": 0.2667}
BASELINE_LABELS = {"pure_rr": "RR", "pure_pf": "PF", "pure_bcqi": "BCQI"}
METHOD_ORDER = [
    "RR",
    "PF",
    "BCQI",
    "DDQN-Paper",
    "DDQN-ResourceEff",
    "SAC-Paper",
    "SAC-ResourceEff",
    "Predictive-SAC",
]
METHOD_COLORS = {
    "RR": "#6b7280",
    "PF": "#2563eb",
    "BCQI": "#16a34a",
    "DDQN-Paper": "#dc2626",
    "DDQN-ResourceEff": "#f97316",
    "SAC-Paper": "#7c3aed",
    "SAC-ResourceEff": "#0d9488",
    "Predictive-SAC": "#111827",
}

# Reward/SLA thresholds used in the current RSLAQ implementation. They are not a
# complete 3GPP QoS table; they are the simulator-level SLA targets used here.
SLA_TARGETS = {
    "low_traffic": {"eMBB_thr_mbps": 10.0, "URLLC_buffer_bytes": 10000.0, "MTC_thr_mbps": 10.0},
    "normal": {"eMBB_thr_mbps": 10.0, "URLLC_buffer_bytes": 10000.0, "MTC_thr_mbps": 10.0},
    "congestion": {"eMBB_thr_mbps": 10.0, "URLLC_buffer_bytes": 10000.0, "MTC_thr_mbps": 20.0},
    "stressed": {"eMBB_thr_mbps": 20.0, "URLLC_buffer_bytes": 10000.0, "MTC_thr_mbps": 20.0},
    "insufficient_resources": {"eMBB_thr_mbps": 20.0, "URLLC_buffer_bytes": 10000.0, "MTC_thr_mbps": 20.0},
}

TRAFFIC_PROFILE_MBPS = {
    "low_traffic": {"eMBB": 5.0, "URLLC": 1.0, "MTC": 2.0},
    "normal": {"eMBB": 70.0, "URLLC": 1.0, "MTC": 2.0},
    "congestion": {"eMBB": 100.0, "URLLC": 1.0, "MTC": 100.0},
    "stressed": {"eMBB": 100.0, "URLLC": 1.0, "MTC": 100.0},
    "insufficient_resources": {"eMBB": 100.0, "URLLC": 2.0, "MTC": 100.0},
}

UE_PROFILE = {
    "low_traffic": {"eMBB": 2, "URLLC": 2, "MTC": 6},
    "normal": {"eMBB": 5, "URLLC": 5, "MTC": 10},
    "congestion": {"eMBB": 15, "URLLC": 10, "MTC": 35},
    "stressed": {"eMBB": 8, "URLLC": 12, "MTC": 20},
    "insufficient_resources": {"eMBB": 20, "URLLC": 10, "MTC": 40},
}


def ensure_dirs() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, **kwargs)
    except Exception as exc:
        print(f"WARN: failed to read {path}: {exc}")
        return pd.DataFrame()


def read_json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARN: failed to read {path}: {exc}")
        return {}


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def ci95(values: Iterable[float]) -> float:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) <= 1:
        return 0.0 if len(arr) == 1 else np.nan
    return 1.96 * arr.std(ddof=1) / math.sqrt(len(arr))


def pct_change(value: float, baseline: float, higher_is_better: bool = True) -> float:
    if not np.isfinite(value) or not np.isfinite(baseline) or baseline == 0:
        return np.nan
    raw = 100.0 * (value - baseline) / abs(baseline)
    return raw if higher_is_better else -raw


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.7,
            "figure.dpi": 120,
        }
    )


def savefig(fig: plt.Figure, name: str) -> None:
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def parse_drl_dir(name: str) -> tuple[str, str, int] | None:
    patterns = [
        (r"^ddqn_paper_(.+)_seed(\d+)$", "DDQN-Paper"),
        (r"^ddqn_resource_efficient_(.+)_seed(\d+)$", "DDQN-ResourceEff"),
        (r"^sac_paper_(.+)_seed(\d+)$", "SAC-Paper"),
        (r"^sac_resource_efficient_(.+)_seed(\d+)$", "SAC-ResourceEff"),
        (r"^predictive_sac_(.+)_seed(\d+)$", "Predictive-SAC"),
    ]
    for pattern, method in patterns:
        match = re.match(pattern, name)
        if match:
            return method, match.group(1), int(match.group(2))
    return None


def iter_drl_run_dirs() -> list[tuple[Path, str, str, int]]:
    runs = []
    for child in sorted(CAMPAIGN.iterdir()):
        if not child.is_dir():
            continue
        parsed = parse_drl_dir(child.name)
        if parsed is None:
            continue
        method, scenario, seed = parsed
        runs.append((child, method, scenario, seed))
    return runs


def collect_training_summaries() -> pd.DataFrame:
    rows = []
    for run_dir, method, scenario, seed in iter_drl_run_dirs():
        summary_files = list(run_dir.glob("*_summary.json"))
        if not summary_files:
            continue
        data = read_json(summary_files[0])
        compute = data.get("compute", {})
        training = compute.get("training", {})
        xapp = compute.get("xapp_runtime", {})
        rows.append(
            {
                "method": method,
                "scenario": scenario,
                "seed": seed,
                "reward_mode": data.get("reward_mode"),
                "episodes": data.get("episodes"),
                "interaction_budget": data.get("interaction_budget") or training.get("interaction_budget"),
                "final_avg_100": data.get("final_avg_100"),
                "best_avg": data.get("best_avg"),
                "wall_time_s": training.get("wall_time_s"),
                "steps_per_second": training.get("steps_per_second"),
                "peak_rss_mb": training.get("peak_rss_mb"),
                "xapp_inference_ms_p95": xapp.get("inference_ms_p95"),
                "xapp_deadline_usage_pct": xapp.get("deadline_usage_pct"),
                "summary_path": str(summary_files[0]),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        for col in [
            "seed",
            "episodes",
            "interaction_budget",
            "final_avg_100",
            "best_avg",
            "wall_time_s",
            "steps_per_second",
            "peak_rss_mb",
            "xapp_inference_ms_p95",
            "xapp_deadline_usage_pct",
        ]:
            if col in df:
                df[col] = to_num(df[col])
    return df


def collect_step_metrics() -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, str, int, str], int]]:
    episode_rows = []
    slice_rows = []
    sim_episode: dict[tuple[str, str, int, str], int] = {}
    for run_dir, method, scenario, seed in iter_drl_run_dirs():
        for path in sorted(run_dir.rglob("step_metrics.csv")):
            df = read_csv(path)
            if df.empty:
                continue
            for col in [
                "episode",
                "step",
                "throughput_mbps",
                "bufferBytes_mean",
                "bufferBytes_max",
                "plr_pct",
                "pdr_pct",
                "resourceSharePct",
                "reward",
                "resource_efficiency",
                "need_allocation_match",
                "over_allocation",
                "under_allocation",
                "action_smoothness_penalty",
                "resource_efficient_shaping",
            ]:
                if col in df:
                    df[col] = to_num(df[col])
            if "sim_id" not in df:
                df["sim_id"] = path.parent.name
            if "slice" not in df and "slice_id" in df:
                df["slice"] = df["slice_id"].map({0: "eMBB", 1: "URLLC", 2: "MTC"})
            df["method"] = method
            df["scenario"] = scenario
            df["seed"] = seed
            df["source_file"] = str(path)

            episode_step = df.drop_duplicates(["episode", "step", "sim_id"])
            if not episode_step.empty:
                grouped = episode_step.groupby(["episode", "sim_id"], as_index=False).agg(
                    episode_reward=("reward", "sum"),
                    mean_step_reward=("reward", "mean"),
                    steps=("step", "nunique"),
                    outage_rate=("outage_flag", lambda s: pd.Series(s).astype(str).str.lower().eq("true").mean()),
                    soft_rate=("soft_flag", lambda s: pd.Series(s).astype(str).str.lower().eq("true").mean()),
                    resource_efficiency=("resource_efficiency", "mean"),
                    need_allocation_match=("need_allocation_match", "mean"),
                    over_allocation=("over_allocation", "mean"),
                    under_allocation=("under_allocation", "mean"),
                    shaping=("resource_efficient_shaping", "mean"),
                )
                grouped["method"] = method
                grouped["scenario"] = scenario
                grouped["seed"] = seed
                grouped["source_file"] = str(path)
                episode_rows.append(grouped)
                for _, row in grouped.iterrows():
                    if pd.notna(row.get("episode")):
                        sim_episode[(method, scenario, seed, str(row["sim_id"]))] = int(row["episode"])

            available = [
                c
                for c in [
                    "method",
                    "scenario",
                    "seed",
                    "episode",
                    "step",
                    "sim_id",
                    "slice",
                    "throughput_mbps",
                    "bufferBytes_mean",
                    "bufferBytes_max",
                    "plr_pct",
                    "pdr_pct",
                    "resourceSharePct",
                    "dLostPackets",
                    "resource_efficiency",
                    "need_allocation_match",
                    "over_allocation",
                    "under_allocation",
                    "resource_efficient_shaping",
                    "source_file",
                ]
                if c in df.columns
            ]
            slice_rows.append(df[available])
    episodes = pd.concat(episode_rows, ignore_index=True) if episode_rows else pd.DataFrame()
    slices = pd.concat(slice_rows, ignore_index=True) if slice_rows else pd.DataFrame()
    return episodes, slices, sim_episode


def mark_late_training(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "episode" not in df:
        return df
    df = df.copy()
    max_ep = df.groupby(["method", "scenario", "seed"])["episode"].transform("max")
    df["late_training"] = df["episode"] >= np.maximum(1, np.floor(max_ep * 0.8))
    return df


def collect_drl_slice_alloc(sim_episode: dict[tuple[str, str, int, str], int]) -> pd.DataFrame:
    rows = []
    for run_dir, method, scenario, seed in iter_drl_run_dirs():
        for path in sorted(run_dir.rglob("slice_alloc.csv")):
            df = read_csv(path)
            if df.empty:
                continue
            for col in [
                "timestamp_ms",
                "slice",
                "configured_weight",
                "budget_rbg",
                "allocated_rbg",
                "total_allocated_rbg",
                "rsh_real_pct",
                "budget_utilization_pct",
                "unused_budget_pct",
                "allocation_fidelity_pct",
                "active_ues",
                "has_demand",
            ]:
                if col in df:
                    df[col] = to_num(df[col])
            sim_id = path.parent.name
            for parent in path.parents:
                if re.fullmatch(r"[0-9a-fA-F-]{36}", parent.name):
                    sim_id = parent.name
                    break
            df["sim_id"] = sim_id
            df["method"] = method
            df["scenario"] = scenario
            df["seed"] = seed
            df["episode"] = sim_episode.get((method, scenario, seed, str(sim_id)), np.nan)
            if "slice" in df:
                df["slice"] = df["slice"].map({0: "eMBB", 1: "URLLC", 2: "MTC"}).fillna(df["slice"].astype(str))
            rows.append(df)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return mark_late_training(out)


def collect_baseline_summary() -> pd.DataFrame:
    rows = []
    base_root = CAMPAIGN / "baseline_ns3/results_rslaq_network_only"
    for path in sorted(base_root.rglob("summary.csv")):
        df = read_csv(path, na_values=["NA", "nan", ""])
        if df.empty:
            continue
        scenario = None
        mode = None
        seed = None
        for part in path.parts:
            if part.startswith("scenario="):
                scenario = part.split("=", 1)[1]
            elif part.startswith("mode="):
                mode = part.split("=", 1)[1]
            elif part.startswith("seed="):
                match = re.match(r"seed=(\d+)_run=(\d+)", part)
                if match:
                    seed = int(match.group(1))
        df["scenario"] = scenario or df.get("scenario")
        df["baseline_mode"] = mode or df.get("baseline_mode")
        df["method"] = df["baseline_mode"].map(BASELINE_LABELS).fillna(df["baseline_mode"])
        df["seed"] = seed
        df["source"] = "baseline"
        df["source_file"] = str(path)
        rows.append(df)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    numeric_cols = [c for c in out.columns if c not in {"scenario", "baseline_mode", "method", "slice", "source", "source_file"}]
    for col in numeric_cols:
        out[col] = to_num(out[col])
    return out


def summarize_drl_network(slice_metrics: pd.DataFrame) -> pd.DataFrame:
    if slice_metrics.empty:
        return pd.DataFrame()
    df = mark_late_training(slice_metrics)
    late = df[df["late_training"]].copy()
    if late.empty:
        late = df.copy()
    grouped = late.groupby(["method", "scenario", "seed", "slice"], as_index=False).agg(
        throughput_mbps_mean=("throughput_mbps", "mean"),
        throughput_mbps_p50=("throughput_mbps", "median"),
        throughput_mbps_p95=("throughput_mbps", lambda s: s.quantile(0.95)),
        pdr_pct=("pdr_pct", "mean"),
        plr_pct=("plr_pct", "mean"),
        buffer_bytes_mean=("bufferBytes_mean", "mean"),
        buffer_bytes_p95=("bufferBytes_mean", lambda s: s.quantile(0.95)),
        resource_share_pct_mean=("resourceSharePct", "mean"),
        resource_efficiency=("resource_efficiency", "mean"),
        need_allocation_match=("need_allocation_match", "mean"),
        over_allocation=("over_allocation", "mean"),
        under_allocation=("under_allocation", "mean"),
        shaping=("resource_efficient_shaping", "mean"),
        samples=("throughput_mbps", "size"),
    )
    grouped["source"] = "DRL-late-training"
    return grouped


def normalize_baseline_for_common_compare(baseline: pd.DataFrame) -> pd.DataFrame:
    if baseline.empty:
        return pd.DataFrame()
    out = baseline.copy()
    rename = {
        "rsh_real_pct_mean": "resource_share_pct_mean",
        "buffer_bytes_mean": "buffer_bytes_mean",
    }
    out = out.rename(columns=rename)
    for col in ["throughput_mbps_mean", "pdr_pct", "plr_pct", "delay_ms_mean", "delay_ms_p95", "jitter_ms_mean"]:
        if col not in out:
            out[col] = np.nan
    out["source"] = "baseline"
    return out


def target_for_slice(scenario: str, slice_name: str) -> float:
    if slice_name == "eMBB":
        return SLA_TARGETS.get(scenario, {}).get("eMBB_thr_mbps", 10.0)
    if slice_name == "MTC":
        return SLA_TARGETS.get(scenario, {}).get("MTC_thr_mbps", 10.0)
    return TRAFFIC_PROFILE_MBPS.get(scenario, {}).get("URLLC", 1.0)


def compute_network_score(common: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if common.empty:
        return pd.DataFrame(), pd.DataFrame()
    df = common.copy()
    df["target_thr_mbps"] = [target_for_slice(s, sl) for s, sl in zip(df["scenario"], df["slice"])]
    df["throughput_satisfaction"] = np.minimum(df["throughput_mbps_mean"] / df["target_thr_mbps"], 1.0)
    df["pdr_score"] = df["pdr_pct"] / 100.0
    df["plr_score"] = 1.0 - (df["plr_pct"] / 100.0)
    df["plr_score"] = df["plr_score"].clip(0, 1)
    df["buffer_score"] = np.nan
    mask_urllc = df["slice"].eq("URLLC") & df.get("buffer_bytes_mean", pd.Series(np.nan, index=df.index)).notna()
    if mask_urllc.any():
        target_buffer = df.loc[mask_urllc, "scenario"].map(lambda s: SLA_TARGETS[s]["URLLC_buffer_bytes"])
        df.loc[mask_urllc, "buffer_score"] = np.exp(-df.loc[mask_urllc, "buffer_bytes_mean"] / target_buffer)
    df["delay_score"] = np.nan
    if "delay_ms_p95" in df:
        # URLLC receives the strictest latency proxy; eMBB/MTC are interpreted more leniently.
        delay_target = df["slice"].map({"URLLC": 10.0, "eMBB": 100.0, "MTC": 100.0})
        df["delay_score"] = np.exp(-df["delay_ms_p95"] / delay_target)
    score_cols = ["throughput_satisfaction", "pdr_score", "plr_score"]
    df["qos_score_slice"] = df[score_cols].mean(axis=1, skipna=True)
    df.loc[mask_urllc, "qos_score_slice"] = df.loc[mask_urllc, ["pdr_score", "plr_score", "buffer_score"]].mean(
        axis=1, skipna=True
    )
    baseline_latency_mask = df["source"].eq("baseline") & df["delay_score"].notna()
    df.loc[baseline_latency_mask, "qos_score_with_latency"] = df.loc[
        baseline_latency_mask, ["qos_score_slice", "delay_score"]
    ].mean(axis=1, skipna=True)
    df["qos_score_with_latency"] = df["qos_score_with_latency"].fillna(df["qos_score_slice"])
    df["slice_weight"] = df["slice"].map(SLICE_WEIGHTS).fillna(1 / 3)
    score = df.groupby(["method", "scenario", "seed", "source"], as_index=False).apply(
        lambda g: pd.Series(
            {
                "network_score": np.average(g["qos_score_slice"], weights=g["slice_weight"]),
                "network_score_with_latency_when_available": np.average(g["qos_score_with_latency"], weights=g["slice_weight"]),
                "throughput_satisfaction": np.average(g["throughput_satisfaction"], weights=g["slice_weight"]),
                "pdr_score": np.average(g["pdr_score"], weights=g["slice_weight"]),
                "plr_score": np.average(g["plr_score"], weights=g["slice_weight"]),
            }
        )
    )
    if isinstance(score.index, pd.MultiIndex):
        score = score.reset_index(drop=True)
    ranking = score.groupby(["method", "source"], as_index=False).agg(
        network_score_mean=("network_score", "mean"),
        network_score_ci95=("network_score", ci95),
        network_score_latency_mean=("network_score_with_latency_when_available", "mean"),
        throughput_satisfaction_mean=("throughput_satisfaction", "mean"),
        pdr_score_mean=("pdr_score", "mean"),
        plr_score_mean=("plr_score", "mean"),
        runs=("network_score", "count"),
    )
    ranking = ranking.sort_values("network_score_mean", ascending=False)
    return df, score, ranking


def agg_mean_ci(df: pd.DataFrame, group_cols: list[str], value_col: str) -> pd.DataFrame:
    return df.groupby(group_cols, as_index=False).agg(
        mean=(value_col, "mean"), ci95=(value_col, ci95), count=(value_col, "count")
    )


def plot_convergence(episodes: pd.DataFrame) -> None:
    if episodes.empty:
        return
    df = episodes.copy()
    df = df.sort_values(["method", "scenario", "seed", "episode"])
    df["episode_reward_smooth"] = df.groupby(["method", "scenario", "seed"])["episode_reward"].transform(
        lambda s: s.rolling(window=10, min_periods=1).mean()
    )
    summary = agg_mean_ci(df, ["scenario", "method", "episode"], "episode_reward_smooth")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=False)
    axes = axes.ravel()
    for idx, scenario in enumerate(SCENARIOS):
        ax = axes[idx]
        subset = summary[summary["scenario"].eq(scenario)]
        for method in METHOD_ORDER:
            m = subset[subset["method"].eq(method)].sort_values("episode")
            if m.empty:
                continue
            color = METHOD_COLORS.get(method, None)
            x = m["episode"].to_numpy(dtype=float)
            y = m["mean"].to_numpy(dtype=float)
            err = m["ci95"].to_numpy(dtype=float)
            ax.plot(x, y, label=method, color=color, linewidth=1.8)
            ax.fill_between(x, y - err, y + err, color=color, alpha=0.10)
        ax.set_title(SCENARIO_LABELS[scenario])
        ax.set_xlabel("Episode")
        ax.set_ylabel("Episode reward, rolling mean 10")
    axes[-1].axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", ncol=2, frameon=False)
    fig.suptitle("DRL convergence by scenario")
    savefig(fig, "01_drl_convergence_rewards")


def plot_final_rewards(summaries: pd.DataFrame) -> None:
    if summaries.empty:
        return
    methods = [m for m in METHOD_ORDER if m in summaries["method"].unique()]
    scenarios = [s for s in SCENARIOS if s in summaries["scenario"].unique()]
    fig, axes = plt.subplots(len(scenarios), 1, figsize=(12, 2.5 * len(scenarios)), sharex=True)
    if len(scenarios) == 1:
        axes = [axes]
    for ax, scenario in zip(axes, scenarios):
        data = [summaries[(summaries["scenario"].eq(scenario)) & (summaries["method"].eq(m))]["final_avg_100"].dropna() for m in methods]
        bp = ax.boxplot(data, tick_labels=methods, patch_artist=True, showmeans=True)
        for patch, method in zip(bp["boxes"], methods):
            patch.set_facecolor(METHOD_COLORS.get(method, "#94a3b8"))
            patch.set_alpha(0.45)
        ax.set_ylabel("Final avg reward")
        ax.set_title(SCENARIO_LABELS[scenario])
        ax.tick_params(axis="x", rotation=25)
    fig.suptitle("Training reward final_avg_100 by method")
    savefig(fig, "02_final_reward_distribution")


def plot_metric_by_slice(common: pd.DataFrame, metric: str, ylabel: str, name: str, higher_is_better: bool = True) -> None:
    if common.empty or metric not in common:
        return
    df = common.dropna(subset=[metric]).copy()
    if df.empty:
        return
    methods = [m for m in METHOD_ORDER if m in df["method"].unique()]
    x = np.arange(len(SCENARIOS))
    width = 0.8 / max(1, len(methods))
    fig, axes = plt.subplots(1, 3, figsize=(17, 5), sharey=False)
    for ax, slice_name in zip(axes, SLICES):
        subset = df[df["slice"].eq(slice_name)]
        grouped = agg_mean_ci(subset, ["scenario", "method"], metric)
        for i, method in enumerate(methods):
            m = grouped[grouped["method"].eq(method)].set_index("scenario").reindex(SCENARIOS)
            offset = (i - (len(methods) - 1) / 2) * width
            ax.bar(
                x + offset,
                m["mean"],
                width=width,
                yerr=m["ci95"],
                label=method,
                color=METHOD_COLORS.get(method, "#94a3b8"),
                alpha=0.82,
                capsize=2,
            )
        ax.set_title(slice_name)
        ax.set_xticks(x)
        ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS], rotation=30, ha="right")
        ax.set_ylabel(ylabel)
        if not higher_is_better:
            ax.set_ylim(bottom=0)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.suptitle(ylabel)
    fig.subplots_adjust(bottom=0.24)
    savefig(fig, name)


def plot_resource_efficiency(resource_df: pd.DataFrame) -> None:
    if resource_df.empty:
        return
    metrics = [
        ("resource_efficiency", "Resource efficiency"),
        ("need_allocation_match", "Need/allocation match"),
        ("over_allocation", "Over-allocation"),
        ("under_allocation", "Under-allocation"),
    ]
    df = resource_df.copy()
    methods = [m for m in METHOD_ORDER if m in df["method"].unique()]
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    axes = axes.ravel()
    for ax, (metric, title) in zip(axes, metrics):
        if metric not in df:
            ax.axis("off")
            continue
        grouped = agg_mean_ci(df.dropna(subset=[metric]), ["method"], metric).set_index("method").reindex(methods)
        ax.bar(
            np.arange(len(methods)),
            grouped["mean"],
            yerr=grouped["ci95"],
            color=[METHOD_COLORS.get(m, "#94a3b8") for m in methods],
            alpha=0.82,
            capsize=3,
        )
        ax.set_title(title)
        ax.set_xticks(np.arange(len(methods)))
        ax.set_xticklabels(methods, rotation=25, ha="right")
    fig.suptitle("Resource-efficient reward diagnostics, late training")
    savefig(fig, "06_resource_efficiency_diagnostics")


def plot_slice_allocation(alloc: pd.DataFrame) -> None:
    if alloc.empty or "rsh_real_pct" not in alloc:
        return
    df = alloc[alloc.get("late_training", True)].dropna(subset=["rsh_real_pct"]).copy()
    if df.empty:
        return
    grouped = df.groupby(["method", "scenario", "slice"], as_index=False)["rsh_real_pct"].mean()
    methods = [m for m in METHOD_ORDER if m in grouped["method"].unique()]
    fig, axes = plt.subplots(len(methods), 1, figsize=(10, max(3, 2.2 * len(methods))))
    if len(methods) == 1:
        axes = [axes]
    for ax, method in zip(axes, methods):
        pivot = (
            grouped[grouped["method"].eq(method)]
            .pivot_table(index="slice", columns="scenario", values="rsh_real_pct", aggfunc="mean")
            .reindex(index=SLICES, columns=SCENARIOS)
        )
        im = ax.imshow(pivot.to_numpy(dtype=float), cmap="YlGnBu", vmin=0, vmax=100, aspect="auto")
        ax.set_title(method)
        ax.set_xticks(np.arange(len(SCENARIOS)))
        ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS], rotation=25, ha="right")
        ax.set_yticks(np.arange(len(SLICES)))
        ax.set_yticklabels(SLICES)
        for i in range(len(SLICES)):
            for j in range(len(SCENARIOS)):
                val = pivot.iloc[i, j]
                if pd.notna(val):
                    ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=axes, label="Real allocated share (%)")
    fig.suptitle("Slice resource allocation by method and scenario")
    savefig(fig, "07_slice_allocation_heatmap")


def plot_baseline_latency(baseline: pd.DataFrame) -> None:
    if baseline.empty or "delay_ms_p95" not in baseline:
        return
    df = baseline.dropna(subset=["delay_ms_p95"]).copy()
    if df.empty:
        return
    methods = [m for m in ["RR", "PF", "BCQI"] if m in df["method"].unique()]
    x = np.arange(len(SCENARIOS))
    width = 0.8 / max(1, len(methods))
    fig, axes = plt.subplots(1, 3, figsize=(17, 5), sharey=False)
    for ax, slice_name in zip(axes, SLICES):
        subset = df[df["slice"].eq(slice_name)]
        grouped = agg_mean_ci(subset, ["scenario", "method"], "delay_ms_p95")
        for i, method in enumerate(methods):
            m = grouped[grouped["method"].eq(method)].set_index("scenario").reindex(SCENARIOS)
            offset = (i - (len(methods) - 1) / 2) * width
            ax.bar(
                x + offset,
                m["mean"],
                width=width,
                yerr=m["ci95"],
                label=method,
                color=METHOD_COLORS.get(method, "#94a3b8"),
                alpha=0.82,
                capsize=2,
            )
        ax.axhline(10 if slice_name == "URLLC" else 100, color="#ef4444", linestyle="--", linewidth=1, label="Proxy target")
        ax.set_yscale("log")
        ax.set_title(slice_name)
        ax.set_xticks(x)
        ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS], rotation=30, ha="right")
        ax.set_ylabel("Delay p95 (ms, log)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.suptitle("Baseline latency vs 3GPP-inspired service expectations")
    fig.subplots_adjust(bottom=0.24)
    savefig(fig, "08_baseline_latency_3gpp_proxy")


def plot_network_score(score: pd.DataFrame) -> None:
    if score.empty:
        return
    grouped = agg_mean_ci(score, ["scenario", "method"], "network_score")
    methods = [m for m in METHOD_ORDER if m in grouped["method"].unique()]
    x = np.arange(len(SCENARIOS))
    width = 0.8 / max(1, len(methods))
    fig, ax = plt.subplots(figsize=(15, 5.5))
    for i, method in enumerate(methods):
        m = grouped[grouped["method"].eq(method)].set_index("scenario").reindex(SCENARIOS)
        offset = (i - (len(methods) - 1) / 2) * width
        ax.bar(
            x + offset,
            m["mean"],
            width=width,
            yerr=m["ci95"],
            color=METHOD_COLORS.get(method, "#94a3b8"),
            label=method,
            alpha=0.82,
            capsize=2,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIOS], rotation=20, ha="right")
    ax.set_ylabel("Composite network score (0-1)")
    ax.set_ylim(0, 1.05)
    ax.set_title("QoS/SLA composite score from common available metrics")
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    savefig(fig, "09_network_composite_score")


def export_tables(
    summaries: pd.DataFrame,
    episodes: pd.DataFrame,
    drl_network: pd.DataFrame,
    baseline: pd.DataFrame,
    common_slice: pd.DataFrame,
    score: pd.DataFrame,
    ranking: pd.DataFrame,
    alloc: pd.DataFrame,
    drl_vs_baseline: pd.DataFrame,
) -> None:
    tables = {
        "drl_training_summaries.csv": summaries,
        "drl_episode_convergence.csv": episodes,
        "drl_late_network_by_run_slice.csv": drl_network,
        "baseline_network_by_run_slice.csv": baseline,
        "common_network_by_run_slice_scored.csv": common_slice,
        "network_scores_by_run.csv": score,
        "method_ranking_overall.csv": ranking,
        "drl_vs_baseline_by_scenario.csv": drl_vs_baseline,
        "drl_slice_allocation_late.csv": alloc[alloc.get("late_training", True)].copy() if not alloc.empty else alloc,
    }
    for name, df in tables.items():
        if df is not None and not df.empty:
            df.to_csv(TAB / name, index=False)


def format_num(value: float, digits: int = 3) -> str:
    if value is None or not np.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def markdown_table(df: pd.DataFrame, cols: list[str], max_rows: int = 20) -> str:
    if df.empty:
        return "No data."
    work = df[cols].head(max_rows).copy()
    headers = list(work.columns)
    rows = []
    rows.append("| " + " | ".join(headers) + " |")
    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in work.iterrows():
        values = []
        for col in headers:
            value = row[col]
            if isinstance(value, float):
                values.append(format_num(value, 3))
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def compare_resource_vs_paper(score: pd.DataFrame) -> pd.DataFrame:
    if score.empty:
        return pd.DataFrame()
    rows = []
    pairs = [("DDQN-ResourceEff", "DDQN-Paper"), ("SAC-ResourceEff", "SAC-Paper"), ("Predictive-SAC", "SAC-ResourceEff")]
    for scenario in SCENARIOS:
        s = score[score["scenario"].eq(scenario)]
        for challenger, base in pairs:
            c = s[s["method"].eq(challenger)]["network_score"].mean()
            b = s[s["method"].eq(base)]["network_score"].mean()
            rows.append(
                {
                    "scenario": scenario,
                    "comparison": f"{challenger} vs {base}",
                    "challenger_score": c,
                    "baseline_score": b,
                    "delta_pct": pct_change(c, b, higher_is_better=True),
                }
            )
    return pd.DataFrame(rows)


def compare_drl_vs_baseline(score: pd.DataFrame) -> pd.DataFrame:
    if score.empty:
        return pd.DataFrame()
    rows = []
    for scenario in SCENARIOS:
        s = score[score["scenario"].eq(scenario)]
        drl = s[s["source"].eq("DRL-late-training")]
        base = s[s["source"].eq("baseline")]
        if drl.empty or base.empty:
            continue
        best_drl = (
            drl.groupby("method", as_index=False)["network_score"]
            .mean()
            .sort_values("network_score", ascending=False)
            .iloc[0]
        )
        best_base = (
            base.groupby("method", as_index=False)["network_score"]
            .mean()
            .sort_values("network_score", ascending=False)
            .iloc[0]
        )
        pf_score = base[base["method"].eq("PF")]["network_score"].mean()
        rows.append(
            {
                "scenario": scenario,
                "best_drl_method": best_drl["method"],
                "best_drl_score": best_drl["network_score"],
                "best_baseline_method": best_base["method"],
                "best_baseline_score": best_base["network_score"],
                "gap_to_best_baseline_pct": pct_change(best_drl["network_score"], best_base["network_score"], True),
                "pf_baseline_score": pf_score,
                "gap_to_pf_pct": pct_change(best_drl["network_score"], pf_score, True),
            }
        )
    return pd.DataFrame(rows)


def write_report(
    summaries: pd.DataFrame,
    episodes: pd.DataFrame,
    baseline: pd.DataFrame,
    common_slice: pd.DataFrame,
    score: pd.DataFrame,
    ranking: pd.DataFrame,
    resource_compare: pd.DataFrame,
    drl_vs_baseline: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# Analise RSLAQ SLA + Resource Efficiency - campanha 20260603_125013")
    lines.append("")
    lines.append("## Escopo")
    lines.append("")
    lines.append(f"- Entrada: `{CAMPAIGN}`")
    lines.append(f"- Saida: `{OUT}`")
    lines.append("- DRL analisado: DDQN paper, DDQN resource_efficient, SAC paper, SAC resource_efficient e Predictive SAC.")
    lines.append("- Baseline analisado: ns-3 puro com RR, PF e BCQI em `baseline_ns3/results_rslaq_network_only`.")
    lines.append("- Para KPIs de rede em DRL, usei os ultimos 20% dos episodios de cada seed como fase final de aprendizado.")
    lines.append("- Recompensas de modos diferentes nao foram usadas como metrica unica de QoS; o ranking principal usa KPIs comuns de rede/SLA.")
    lines.append("")
    lines.append("## Dados carregados")
    lines.append("")
    lines.append(f"- Summaries DRL: {len(summaries)} execucoes.")
    lines.append(f"- Episodios DRL reconstruidos de `step_metrics.csv`: {len(episodes)} episodios/simulacoes.")
    lines.append(f"- Linhas baseline por slice: {len(baseline)}.")
    lines.append(f"- Linhas comuns pontuadas por slice: {len(common_slice)}.")
    lines.append("")
    if not summaries.empty:
        coverage = summaries.groupby(["method", "scenario"]).size().reset_index(name="runs")
        lines.append("### Cobertura DRL")
        lines.append("")
        lines.append(markdown_table(coverage.sort_values(["scenario", "method"]), ["method", "scenario", "runs"], max_rows=100))
        lines.append("")
    lines.append("## Ranking de QoS/SLA")
    lines.append("")
    if not ranking.empty:
        display = ranking.copy()
        for col in ["network_score_mean", "network_score_ci95", "network_score_latency_mean", "throughput_satisfaction_mean", "pdr_score_mean", "plr_score_mean"]:
            display[col] = display[col].map(lambda v: format_num(v, 3))
        lines.append(markdown_table(display, ["method", "source", "network_score_mean", "network_score_ci95", "runs"], 20))
    else:
        lines.append("Sem ranking calculavel.")
    lines.append("")
    lines.append("Interpretacao: o score fica entre 0 e 1 e combina satisfacao de throughput, PDR e PLR com pesos por slice. Para URLLC em DRL, o buffer e usado como proxy de latencia quando disponivel. Para baselines, a latencia aparece separadamente porque os logs DRL nao possuem delay/jitter.")
    lines.append("")
    lines.append("## Comparacao resource-efficient")
    lines.append("")
    if not resource_compare.empty:
        show = resource_compare.copy()
        show["challenger_score"] = show["challenger_score"].map(lambda v: format_num(v, 3))
        show["baseline_score"] = show["baseline_score"].map(lambda v: format_num(v, 3))
        show["delta_pct"] = show["delta_pct"].map(lambda v: format_num(v, 2))
        lines.append(markdown_table(show.dropna(subset=["delta_pct"]), ["scenario", "comparison", "challenger_score", "baseline_score", "delta_pct"], 100))
    else:
        lines.append("Sem pares suficientes para comparacao.")
    lines.append("")
    lines.append("## Comparacao direta com baseline")
    lines.append("")
    if not drl_vs_baseline.empty:
        show = drl_vs_baseline.copy()
        for col in ["best_drl_score", "best_baseline_score", "gap_to_best_baseline_pct", "pf_baseline_score", "gap_to_pf_pct"]:
            show[col] = show[col].map(lambda v: format_num(v, 3))
        lines.append(
            markdown_table(
                show,
                [
                    "scenario",
                    "best_drl_method",
                    "best_drl_score",
                    "best_baseline_method",
                    "best_baseline_score",
                    "gap_to_best_baseline_pct",
                    "pf_baseline_score",
                    "gap_to_pf_pct",
                ],
                20,
            )
        )
    else:
        lines.append("Sem cenarios com DRL e baseline simultaneamente.")
    lines.append("")
    lines.append("## Aprendizado das DRLs")
    lines.append("")
    if not summaries.empty:
        summary_agg = summaries.groupby("method", as_index=False).agg(
            final_avg_100_mean=("final_avg_100", "mean"),
            final_avg_100_ci95=("final_avg_100", ci95),
            best_avg_mean=("best_avg", "mean"),
            steps_per_second_mean=("steps_per_second", "mean"),
            xapp_p95_ms_mean=("xapp_inference_ms_p95", "mean"),
            runs=("final_avg_100", "count"),
        )
        show = summary_agg.sort_values("final_avg_100_mean", ascending=False).copy()
        for col in show.columns:
            if col.endswith("mean") or col.endswith("ci95"):
                show[col] = show[col].map(lambda v: format_num(v, 3))
        lines.append(markdown_table(show, list(show.columns), 20))
    lines.append("")
    lines.append("Nota metodologica: `final_avg_100` e comparavel dentro do mesmo reward_mode. Entre `paper` e `resource_efficient`, a comparacao cientificamente mais segura e via KPIs de rede e SLA, pois a recompensa foi redefinida.")
    lines.append("")
    lines.append("## Baseline e QoS 3GPP")
    lines.append("")
    lines.append("Parametros de rede do cenario usado na campanha: 1 gNB NR, UEs estaticos, 3.55 GHz, 100 MHz, numerologia mu=1, canal 3GPP UMi, trafego downlink UDP por slice. Os perfis de carga usados no simulador foram:")
    lines.append("")
    profile_rows = []
    for scenario in SCENARIOS:
        for slice_name in SLICES:
            profile_rows.append(
                {
                    "scenario": scenario,
                    "slice": slice_name,
                    "ues": UE_PROFILE[scenario][slice_name],
                    "offered_load_mbps": TRAFFIC_PROFILE_MBPS[scenario][slice_name],
                    "sla_target": target_for_slice(scenario, slice_name),
                }
            )
    lines.append(markdown_table(pd.DataFrame(profile_rows), ["scenario", "slice", "ues", "offered_load_mbps", "sla_target"], max_rows=100))
    lines.append("")
    lines.append("3GPP/QoS: eMBB deve priorizar throughput agregado; URLLC deve priorizar confiabilidade, baixa latencia e buffer baixo; MTC deve priorizar grande quantidade de dispositivos com baixo trafego unitario. Nesta campanha, DRL registra throughput/PDR/PLR/buffer/alocacao, mas nao registra delay/jitter, portanto os graficos de latencia 3GPP sao somente para baselines RR/PF/BCQI.")
    lines.append("")
    lines.append("## Graficos gerados")
    lines.append("")
    figures = [
        ("01_drl_convergence_rewards.png", "Convergencia das DRLs por cenario usando reward por episodio."),
        ("02_final_reward_distribution.png", "Distribuicao do reward final por metodo e cenario."),
        ("03_qos_throughput_by_slice.png", "Throughput por slice, DRL final vs baselines."),
        ("04_qos_pdr_by_slice.png", "PDR por slice, DRL final vs baselines."),
        ("05_qos_plr_by_slice.png", "PLR por slice, DRL final vs baselines."),
        ("06_resource_efficiency_diagnostics.png", "Diagnosticos especificos da recompensa resource_efficient."),
        ("07_slice_allocation_heatmap.png", "Alocacao real de recursos por slice nas DRLs."),
        ("08_baseline_latency_3gpp_proxy.png", "Latencia p95 dos baselines em escala log."),
        ("09_network_composite_score.png", "Score composto de QoS/SLA por cenario."),
    ]
    for fig_name, desc in figures:
        status = "OK" if (FIG / fig_name).exists() else "NA"
        lines.append(f"- `{fig_name}`: {desc} Status: {status}.")
    lines.append("")
    lines.append("## Principais leituras")
    lines.append("")
    if not ranking.empty:
        best = ranking.iloc[0]
        lines.append(f"- Melhor score medio geral: `{best['method']}` com score {format_num(best['network_score_mean'], 3)}.")
    if not drl_vs_baseline.empty:
        wins = int((drl_vs_baseline["gap_to_best_baseline_pct"] > 0).sum())
        lines.append(f"- Cenarios em que a melhor DRL supera o melhor baseline: {wins} de {len(drl_vs_baseline)}.")
    if not resource_compare.empty:
        valid = resource_compare.dropna(subset=["delta_pct"])
        if not valid.empty:
            positive = valid[valid["delta_pct"] > 0]
            lines.append(f"- Comparacoes resource-efficient com ganho positivo: {len(positive)} de {len(valid)} pares avaliaveis.")
    if not baseline.empty and "delay_ms_p95" in baseline:
        urllc_delay = baseline[baseline["slice"].eq("URLLC")].groupby("method")["delay_ms_p95"].mean().sort_values()
        if not urllc_delay.empty:
            lines.append(f"- Menor delay p95 medio para URLLC nos baselines: `{urllc_delay.index[0]}` com {format_num(urllc_delay.iloc[0], 2)} ms.")
    if not summaries.empty and "xapp_inference_ms_p95" in summaries:
        p95 = summaries.groupby("method")["xapp_inference_ms_p95"].mean().sort_values()
        if not p95.empty:
            lines.append(f"- Menor latencia p95 media de decisao xApp: `{p95.index[0]}` com {format_num(p95.iloc[0], 3)} ms.")
    lines.append("")
    lines.append("## Limitacoes")
    lines.append("")
    lines.append("- A comparacao DRL vs baseline usa os KPIs disponiveis em comum; delay e jitter nao existem nos `step_metrics.csv` das DRLs.")
    lines.append("- O desempenho de rede DRL foi estimado pela fase final do treinamento, nao por uma avaliacao offline deterministica separada da politica final.")
    lines.append("- Algumas execucoes possuem multiplos diretorios `sim_id`; o script reconstruiu episodios a partir de `step_metrics.csv` e removeu duplicacao por slice no reward.")
    lines.append("- Os baselines cobrem tambem `stressed` e `insufficient_resources`; as DRLs desta campanha podem ter cobertura incompleta nesses cenarios dependendo dos summaries existentes.")
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_dirs()
    apply_style()
    summaries = collect_training_summaries()
    episodes, slice_metrics, sim_episode = collect_step_metrics()
    episodes = mark_late_training(episodes)
    slice_metrics = mark_late_training(slice_metrics)
    alloc = collect_drl_slice_alloc(sim_episode)
    baseline = collect_baseline_summary()
    drl_network = summarize_drl_network(slice_metrics)
    baseline_common = normalize_baseline_for_common_compare(baseline)
    common_cols = sorted(set(drl_network.columns).union(set(baseline_common.columns)))
    common = pd.concat(
        [drl_network.reindex(columns=common_cols), baseline_common.reindex(columns=common_cols)],
        ignore_index=True,
    )
    common_slice, score, ranking = compute_network_score(common)
    resource_compare = compare_resource_vs_paper(score)
    drl_vs_baseline = compare_drl_vs_baseline(score)

    export_tables(summaries, episodes, drl_network, baseline, common_slice, score, ranking, alloc, drl_vs_baseline)
    plot_convergence(episodes)
    plot_final_rewards(summaries)
    plot_metric_by_slice(common, "throughput_mbps_mean", "Throughput mean (Mbps)", "03_qos_throughput_by_slice")
    plot_metric_by_slice(common, "pdr_pct", "PDR (%)", "04_qos_pdr_by_slice")
    plot_metric_by_slice(common, "plr_pct", "PLR (%)", "05_qos_plr_by_slice", higher_is_better=False)
    plot_resource_efficiency(drl_network)
    plot_slice_allocation(alloc)
    plot_baseline_latency(baseline)
    plot_network_score(score)
    write_report(summaries, episodes, baseline, common_slice, score, ranking, resource_compare, drl_vs_baseline)

    manifest = {
        "campaign": str(CAMPAIGN),
        "output": str(OUT),
        "tables": sorted(p.name for p in TAB.glob("*.csv")),
        "figures": sorted(p.name for p in FIG.glob("*.png")),
        "report": str(REPORT),
    }
    (OUT / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
