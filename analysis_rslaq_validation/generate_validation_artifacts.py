#!/usr/bin/env python3
"""Generate RSLAQ validation artifacts from existing results only.

This script is intentionally read-only with respect to ns-3 and ns-o-ran-gym.
It writes only under analysis_rslaq_validation/.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis_rslaq_validation"
FIG = OUT / "figures"
TAB = OUT / "tables"

RESULTS = ROOT / "ns-o-ran-gym" / "results"
CONTROLLED_RESULTS = ROOT / "ns-o-ran-gym" / "results_controlled"
BASELINES = ROOT / "ns-3-dev" / "results_rslaq_network_only"

SCENARIOS = [
    "low_traffic",
    "normal",
    "congestion",
    "stressed",
    "insufficient_resources",
]

SLICES = {0: "eMBB", 1: "URLLC", 2: "MTC"}
BASELINE_METHODS = {
    "RR": "pure_rr",
    "PF": "pure_pf",
    "BCQI": "pure_bcqi",
    "Opt": "slice_weighted_pf",
}
DRL_METHODS = {"RSLAQ/DDQN": "ddqn", "SAC": "sac"}

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

UES = {"eMBB": 5, "URLLC": 5, "MTC": 10}
PKT_BYTES = {"eMBB": 1500, "URLLC": 50, "MTC": 100}


def ensure_dirs() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def cdf(values: pd.Series | np.ndarray | list[float]) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.array([]), np.array([])
    arr = np.sort(arr)
    y = np.arange(1, arr.size + 1) / arr.size
    return arr, y


def training_log(algo: str, scenario: str) -> pd.DataFrame:
    paths = [RESULTS / f"{algo}_{scenario}_seed1" / f"{algo}_training_log.csv"]
    if CONTROLLED_RESULTS.exists():
        paths.extend(CONTROLLED_RESULTS.glob(f"**/{algo}_{scenario}_seed*/{algo}_training_log.csv"))

    frames = []
    for path in sorted(set(paths)):
        df = read_csv(path)
        if df.empty:
            continue
        seed = 1
        marker = f"{algo}_{scenario}_seed"
        if marker in path.parent.name:
            try:
                seed = int(path.parent.name.split(marker, 1)[1])
            except ValueError:
                seed = 1
        df["algo"] = algo
        df["scenario"] = scenario
        df["seed"] = seed
        df["training_log_path"] = str(path)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def baseline_summary(mode: str, scenario: str) -> pd.DataFrame:
    path = BASELINES / f"scenario={scenario}" / f"mode={mode}" / "seed=1_run=1" / "summary.csv"
    df = read_csv(path)
    if not df.empty:
        df["method_mode"] = mode
        df["seed"] = 1
    return df


def baseline_timeseries(mode: str, scenario: str) -> pd.DataFrame:
    path = BASELINES / f"scenario={scenario}" / f"mode={mode}" / "seed=1_run=1" / "timeseries.csv"
    return read_csv(path)


def drl_kpm_files(algo: str, scenario: str) -> list[Path]:
    root = RESULTS / f"{algo}_{scenario}_seed1"
    if not root.exists():
        return []
    return sorted(root.glob("*/rslaq-kpms.txt"))


def drl_episode_kpis(algo: str, scenario: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ep, path in enumerate(drl_kpm_files(algo, scenario), start=1):
        df = read_csv(path)
        if df.empty:
            continue
        df["episode_proxy"] = ep
        df["sim_id"] = path.parent.name
        rows.append(df)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out["algo"] = algo
    out["scenario"] = scenario
    out["seed"] = 1
    return out


def drl_step_metrics(algo: str, scenario: str) -> pd.DataFrame:
    """Read per-step logs produced by the fixed RslaqEnv, if available."""
    paths: list[Path] = []
    paths.extend((RESULTS / f"{algo}_{scenario}_seed1").glob("*/step_metrics.csv"))
    if CONTROLLED_RESULTS.exists():
        paths.extend(CONTROLLED_RESULTS.glob(f"**/{algo}_{scenario}_seed*/**/step_metrics.csv"))

    frames = []
    for path in sorted(set(paths)):
        df = read_csv(path)
        if df.empty:
            continue
        df["algo"] = algo
        df["scenario"] = scenario
        df["step_log_path"] = str(path)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def aggregate_drl_by_episode(algo: str, scenario: str) -> pd.DataFrame:
    df = drl_episode_kpis(algo, scenario)
    if df.empty:
        return df
    grouped = []
    for (episode, sim_id, sid), g in df.groupby(["episode_proxy", "sim_id", "sliceId"]):
        grouped.append(
            {
                "episode": episode,
                "sim_id": sim_id,
                "slice": int(sid),
                "throughput_mbps": g["throughputMbps"].sum(),
                "dTxBytes_sum": g["dTxBytes"].sum(),
                "dRxBytes_sum": g["dRxBytes"].sum(),
                "plr_mean": g["plr"].mean(),
                "buffer_bytes_max": g["bufferBytes"].max(),
                "buffer_bytes_mean": g["bufferBytes"].mean(),
                "dLostPackets_sum": g["dLostPackets"].sum(),
                "rsh_mean_pct": g["resourceSharePct"].mean(),
            }
        )
    out = pd.DataFrame(grouped)
    out["algo"] = algo
    out["scenario"] = scenario
    out["seed"] = 1
    return out


def baseline_aggregate_by_timestamp(mode: str, scenario: str) -> pd.DataFrame:
    df = baseline_timeseries(mode, scenario)
    if df.empty:
        return df
    df = df[df["slice"].isin(["eMBB", "URLLC", "MTC"])].copy()
    grouped = []
    for (ts, sl), g in df.groupby(["timestamp_ms", "slice"]):
        grouped.append(
            {
                "timestamp_ms": ts,
                "slice_name": sl,
                "slice": {"eMBB": 0, "URLLC": 1, "MTC": 2}[sl],
                "throughput_mbps": g["thr_mbps"].sum(),
                "dTxBytes_sum": g["tx_bytes_delta"].sum(),
                "dRxBytes_sum": g["rx_bytes_delta"].sum(),
                "plr_mean": g["loss_pct_interval"].mean(),
                "buffer_bytes_max": pd.to_numeric(g["buffer_bytes"], errors="coerce").max(),
                "buffer_bytes_mean": pd.to_numeric(g["buffer_bytes"], errors="coerce").mean(),
                "dLostPackets_sum": g["dropped_packets_delta"].sum(),
                "rsh_mean_pct": g["rsh_configured_pct"].mean(),
            }
        )
    out = pd.DataFrame(grouped)
    out["mode"] = mode
    out["scenario"] = scenario
    out["seed"] = 1
    return out


def compute_outage_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []

    for scenario in SCENARIOS:
        sla = SLA[scenario]
        for label, mode in BASELINE_METHODS.items():
            agg = baseline_aggregate_by_timestamp(mode, scenario)
            if agg.empty:
                continue
            for sid, name in SLICES.items():
                s = agg[agg["slice"] == sid]
                samples = len(s)
                if samples == 0:
                    continue
                if sid == 0:
                    flags = (s["throughput_mbps"] < sla["embb_min"]) & (s["dTxBytes_sum"] >= 1)
                elif sid == 1:
                    flags = s["buffer_bytes_max"].fillna(0) > sla["urllc_bfs"]
                else:
                    flags = pd.Series([False] * samples)
                outage_count = int(flags.sum())
                rows.append(
                    {
                        "method": label,
                        "source": "baseline_timeseries",
                        "scenario": scenario,
                        "seed": 1,
                        "slice": name,
                        "samples": samples,
                        "outage_count": outage_count,
                        "outage_probability": outage_count / samples if samples else math.nan,
                    }
                )

        for label, algo in DRL_METHODS.items():
            step_df = drl_step_metrics(algo, scenario)
            if not step_df.empty:
                source = "drl_step_metrics"
                for seed, seed_df in step_df.groupby("seed"):
                    for sid, name in SLICES.items():
                        s = seed_df[seed_df["slice_id"] == sid]
                        samples = len(s)
                        if samples == 0:
                            continue
                        if sid == 0:
                            flags = (s["throughput_mbps"] < sla["embb_min"]) & (s["dTxBytes"] >= 1)
                        elif sid == 1:
                            flags = s["bufferBytes_max"].fillna(0) > sla["urllc_bfs"]
                        else:
                            flags = pd.Series([False] * samples)
                        outage_count = int(flags.sum())
                        rows.append(
                            {
                                "method": label,
                                "source": source,
                                "scenario": scenario,
                                "seed": int(seed),
                                "slice": name,
                                "samples": samples,
                                "outage_count": outage_count,
                                "outage_probability": outage_count / samples if samples else math.nan,
                            }
                        )
                continue

            agg = aggregate_drl_by_episode(algo, scenario)
            if agg.empty:
                continue
            for sid, name in SLICES.items():
                s = agg[agg["slice"] == sid]
                samples = len(s)
                if samples == 0:
                    continue
                if sid == 0:
                    flags = (s["throughput_mbps"] < sla["embb_min"]) & (s["dTxBytes_sum"] >= 1)
                elif sid == 1:
                    flags = s["buffer_bytes_max"].fillna(0) > sla["urllc_bfs"]
                else:
                    flags = pd.Series([False] * samples)
                outage_count = int(flags.sum())
                rows.append(
                    {
                        "method": label,
                        "source": "drl_final_kpm_snapshot",
                        "scenario": scenario,
                        "seed": 1,
                        "slice": name,
                        "samples": samples,
                        "outage_count": outage_count,
                        "outage_probability": outage_count / samples if samples else math.nan,
                    }
                )

    outage = pd.DataFrame(rows)
    reliability = outage.copy()
    reliability["reliability"] = 1.0 - reliability["outage_probability"]
    return outage, reliability


def build_metrics_summary(outage: pd.DataFrame, reliability: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for scenario in SCENARIOS:
        for algo in ["ddqn", "sac"]:
            df = training_log(algo, scenario)
            if df.empty:
                continue
            for seed, g in df.groupby("seed"):
                steps_total = int(pd.to_numeric(g["steps"], errors="coerce").fillna(0).sum())
                outage_total = int(pd.to_numeric(g["outage_count"], errors="coerce").fillna(0).sum())
                soft_total = int(pd.to_numeric(g["soft_count"], errors="coerce").fillna(0).sum())
                rewards = pd.to_numeric(g["total_reward"], errors="coerce").dropna()
                rows.append(
                    {
                        "method": "RSLAQ/DDQN" if algo == "ddqn" else "SAC",
                        "source": "training_log",
                        "scenario": scenario,
                        "seed": seed,
                        "episodes": len(g),
                        "steps_total": steps_total,
                        "interaction_budget": steps_total,
                        "reward_mean": rewards.mean(),
                        "reward_std": rewards.std(ddof=1) if len(rewards) > 1 else 0.0,
                        "reward_ci95": np.nan,
                        "outage_rate_from_training_log": outage_total / steps_total if steps_total else np.nan,
                        "soft_violation_rate_from_training_log": soft_total / steps_total if steps_total else np.nan,
                        "final_embb_thr_mean_mbps": pd.to_numeric(g["final_embb_thr"], errors="coerce").mean(),
                        "final_urllc_plr_mean_pct": pd.to_numeric(g["final_urllc_plr"], errors="coerce").mean(),
                        "final_mtc_lost_mean_packets": pd.to_numeric(g["final_mtc_lost"], errors="coerce").mean(),
                        "action_embb_mean_pct": pd.to_numeric(g["action_embb"], errors="coerce").mean(),
                        "action_urllc_mean_pct": pd.to_numeric(g["action_urllc"], errors="coerce").mean(),
                        "action_mtc_mean_pct": pd.to_numeric(g["action_mtc"], errors="coerce").mean(),
                        "notes": "controlled if sourced from results_controlled; otherwise legacy exploratory",
                    }
                )

        for label, mode in BASELINE_METHODS.items():
            df = baseline_summary(mode, scenario)
            if df.empty:
                continue
            for _, row in df.iterrows():
                rows.append(
                    {
                        "method": label,
                        "source": "ns3_baseline_summary",
                        "scenario": scenario,
                        "seed": 1,
                        "episodes": 0,
                        "steps_total": np.nan,
                        "interaction_budget": "not_drl",
                        "reward_mean": np.nan,
                        "reward_std": np.nan,
                        "reward_ci95": np.nan,
                        "outage_rate_from_training_log": np.nan,
                        "soft_violation_rate_from_training_log": np.nan,
                        "slice": row.get("slice"),
                        "throughput_mbps_mean": row.get("throughput_mbps_mean"),
                        "pdr_pct": row.get("pdr_pct"),
                        "plr_pct": row.get("plr_pct"),
                        "buffer_bytes_mean": row.get("buffer_bytes_mean"),
                        "rsh_real_pct_mean": row.get("rsh_real_pct_mean"),
                        "notes": "one ns-3 seed/run",
                    }
                )

    df = pd.DataFrame(rows)
    if not df.empty:
        rel = reliability[reliability["slice"].isin(["eMBB", "URLLC"])].pivot_table(
            index=["method", "scenario", "seed"],
            columns="slice",
            values="reliability",
            aggfunc="mean",
        ).reset_index()
        rel = rel.rename(columns={"eMBB": "reliability_embb", "URLLC": "reliability_urllc"})
        df = df.merge(rel, on=["method", "scenario", "seed"], how="left")
    return df


def low_traffic_audit() -> pd.DataFrame:
    rows = []
    scenario = "low_traffic"
    measured = {}
    for label, mode in BASELINE_METHODS.items():
        df = baseline_summary(mode, scenario)
        if df.empty:
            continue
        for _, row in df.iterrows():
            measured.setdefault(row["slice"], []).append(float(row["throughput_mbps_mean"]))
    for label, algo in DRL_METHODS.items():
        agg = aggregate_drl_by_episode(algo, scenario)
        if agg.empty:
            continue
        for sid, sl in SLICES.items():
            vals = agg[agg["slice"] == sid]["throughput_mbps"]
            if len(vals):
                measured.setdefault(sl, []).append(float(vals.mean()))

    for sl in ["eMBB", "URLLC", "MTC"]:
        offered = TRAFFIC_MBPS[scenario][sl]
        per_ue = offered / UES[sl]
        pkt = PKT_BYTES[sl]
        interval_ms = (pkt * 8 / (per_ue * 1e6)) * 1000 if per_ue > 0 else math.nan
        thr_meas = max(measured.get(sl, [math.nan]))
        if sl == "eMBB":
            sla_min = SLA[scenario]["embb_min"]
            sla_soft = SLA[scenario]["embb_soft"]
            if offered < sla_min and np.isfinite(thr_meas) and thr_meas <= offered * 1.25:
                status = "aparentemente infactivel"
            elif offered < sla_min:
                status = "erro provavel de unidade/configuracao"
            else:
                status = "factivel"
        elif sl == "URLLC":
            sla_min = "buffer <= 10000 bytes"
            sla_soft = "sem soft max"
            status = "inconclusivo por falta de metrica" if not np.isfinite(thr_meas) else "factivel"
        else:
            sla_min = "no-policy no artigo"
            sla_soft = "no-policy"
            status = "inconclusivo por falta de metrica"
        rows.append(
            {
                "scenario": scenario,
                "slice": sl,
                "ues": UES[sl],
                "packet_size_bytes": pkt,
                "per_ue_rate_mbps": per_ue,
                "packet_interval_ms_estimated": interval_ms,
                "trafego_oferecido_estimado_mbps": offered,
                "throughput_medido_mbps_max_observado": thr_meas,
                "sla_minimo": sla_min,
                "sla_maximo_soft": sla_soft,
                "nivel_medicao_throughput": "FlowMonitor/IP UDP rxBytes delta; DRL KPM usa dRxBytes por periodo",
                "status_fisico": status,
            }
        )
    return pd.DataFrame(rows)


def plot_reward(algo: str, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    for scenario in SCENARIOS:
        df = training_log(algo, scenario)
        if df.empty:
            continue
        ax.plot(df["episode"], pd.to_numeric(df["total_reward"], errors="coerce"), label=scenario, linewidth=1.6)
    ax.axhspan(-1e9, 0, color="#f2b8a0", alpha=0.25, label="reward negativo")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"Reward por cenario - {algo.upper()}")
    ax.set_xlabel("Episodio")
    ax.set_ylabel("Reward total do episodio")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    ax.text(
        0.01,
        0.02,
        "Reward negativo pode indicar outage/SLA hard ou recursos insuficientes; nao e prova isolada de superioridade.",
        transform=ax.transAxes,
        fontsize=8,
        va="bottom",
    )
    fig.tight_layout()
    fig.savefig(FIG / f"{filename}.png", dpi=300)
    fig.savefig(FIG / f"{filename}.pdf", dpi=300)
    plt.close(fig)


def cdf_data(method_label: str, scenario: str, metric: str) -> np.ndarray:
    if method_label in BASELINE_METHODS:
        agg = baseline_aggregate_by_timestamp(BASELINE_METHODS[method_label], scenario)
        if agg.empty:
            return np.array([])
        if metric == "embb_thr":
            return agg[agg["slice"] == 0]["throughput_mbps"].to_numpy()
        if metric == "mtc_thr":
            return agg[agg["slice"] == 2]["throughput_mbps"].to_numpy()
        if metric == "urllc_bfs_pct":
            vals = agg[agg["slice"] == 1]["buffer_bytes_max"].fillna(0) / SLA[scenario]["urllc_bfs"] * 100.0
            return vals.to_numpy()
    else:
        algo = DRL_METHODS[method_label]
        agg = aggregate_drl_by_episode(algo, scenario)
        if agg.empty:
            return np.array([])
        if metric == "embb_thr":
            return agg[agg["slice"] == 0]["throughput_mbps"].to_numpy()
        if metric == "mtc_thr":
            return agg[agg["slice"] == 2]["throughput_mbps"].to_numpy()
        if metric == "urllc_bfs_pct":
            vals = agg[agg["slice"] == 1]["buffer_bytes_max"].fillna(0) / SLA[scenario]["urllc_bfs"] * 100.0
            return vals.to_numpy()
    return np.array([])


def plot_fig6_cdf() -> None:
    methods = ["RR", "PF", "BCQI", "Opt", "SAC", "RSLAQ/DDQN"]
    colors = {
        "RR": "#4d4d4d",
        "PF": "#1f77b4",
        "BCQI": "#ff7f0e",
        "Opt": "#2ca02c",
        "SAC": "#9467bd",
        "RSLAQ/DDQN": "#d62728",
    }
    metrics = [
        ("embb_thr", "CDF throughput eMBB (Mbps)", "higher"),
        ("mtc_thr", "CDF throughput MTC (Mbps)", "higher"),
        ("urllc_bfs_pct", "CDF buffer URLLC (% SLA)", "lower"),
    ]
    fig, axes = plt.subplots(5, 3, figsize=(15, 18), sharey=True)
    for r, scenario in enumerate(SCENARIOS):
        for c, (metric, title, better) in enumerate(metrics):
            ax = axes[r, c]
            for method in methods:
                x, y = cdf(cdf_data(method, scenario, metric))
                if len(x):
                    ax.plot(x, y, label=method, color=colors[method], linewidth=1.3)
            if metric == "embb_thr":
                target = SLA[scenario]["embb_min"]
                ax.axvline(target, color="black", linestyle="--", linewidth=0.9)
                ax.axvspan(target, ax.get_xlim()[1], color="#ccebc5", alpha=0.18)
                ax.axvspan(ax.get_xlim()[0], target, color="#fbb4ae", alpha=0.14)
                ax.annotate("Better", xy=(0.86, 0.12), xytext=(0.66, 0.12), xycoords="axes fraction",
                            arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
            elif metric == "mtc_thr":
                target = SLA[scenario]["mtc_target"]
                ax.axvline(target, color="black", linestyle="--", linewidth=0.9)
                ax.axvspan(target, ax.get_xlim()[1], color="#ccebc5", alpha=0.18)
                ax.annotate("Better", xy=(0.86, 0.12), xytext=(0.66, 0.12), xycoords="axes fraction",
                            arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
            else:
                target = 100.0
                ax.axvline(target, color="black", linestyle="--", linewidth=0.9)
                ax.axvspan(ax.get_xlim()[0], target, color="#ccebc5", alpha=0.18)
                ax.axvspan(target, ax.get_xlim()[1], color="#fbb4ae", alpha=0.14)
                ax.annotate("Better", xy=(0.12, 0.12), xytext=(0.32, 0.12), xycoords="axes fraction",
                            arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
            if r == 0:
                ax.set_title(title, fontsize=10)
            if c == 0:
                ax.set_ylabel(f"{scenario}\nCDF")
            ax.grid(True, alpha=0.22)
            ax.set_ylim(0, 1.02)
            ax.tick_params(labelsize=8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=6, fontsize=9)
    fig.suptitle("Fig. 6 style - CDFs de KPIs RSLAQ (dados disponiveis)", y=0.995)
    fig.tight_layout(rect=[0, 0.035, 1, 0.985])
    fig.savefig(FIG / "fig6_cdf_rslaq_style.png", dpi=300)
    fig.savefig(FIG / "fig6_cdf_rslaq_style.pdf", dpi=300)
    plt.close(fig)


def plot_fig7_reliability(reliability: pd.DataFrame, include_insufficient: bool = False) -> None:
    scenarios = SCENARIOS if include_insufficient else [s for s in SCENARIOS if s != "insufficient_resources"]
    methods = ["Opt", "SAC", "RSLAQ/DDQN"]
    sub = reliability[
        reliability["scenario"].isin(scenarios)
        & reliability["method"].isin(methods)
        & reliability["slice"].isin(["eMBB", "URLLC"])
    ].copy()
    fig, ax = plt.subplots(figsize=(12, 5.5))
    width = 0.12
    x = np.arange(len(scenarios))
    offsets = {
        ("Opt", "eMBB"): -2.5 * width,
        ("Opt", "URLLC"): -1.5 * width,
        ("SAC", "eMBB"): -0.5 * width,
        ("SAC", "URLLC"): 0.5 * width,
        ("RSLAQ/DDQN", "eMBB"): 1.5 * width,
        ("RSLAQ/DDQN", "URLLC"): 2.5 * width,
    }
    colors = {"Opt": "#2ca02c", "SAC": "#9467bd", "RSLAQ/DDQN": "#d62728"}
    hatches = {"eMBB": "", "URLLC": "//"}
    for method in methods:
        for sl in ["eMBB", "URLLC"]:
            vals = []
            for scenario in scenarios:
                v = sub[(sub["scenario"] == scenario) & (sub["method"] == method) & (sub["slice"] == sl)]["reliability"]
                vals.append(float(v.mean()) if len(v) else np.nan)
            ax.bar(x + offsets[(method, sl)], vals, width, label=f"{method} {sl}", color=colors[method], hatch=hatches[sl], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    ax.set_ylabel("Reliability = 1 - P(k_out)")
    title = "Fig. 7 style - reliability/outage por cenario"
    if include_insufficient:
        title += " (diagnostico incluindo insufficient_resources)"
    ax.set_title(title)
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8, ncol=3)
    fig.tight_layout()
    suffix = "_including_insufficient" if include_insufficient else ""
    fig.savefig(FIG / f"fig7_reliability_rslaq_style{suffix}.png", dpi=300)
    fig.savefig(FIG / f"fig7_reliability_rslaq_style{suffix}.pdf", dpi=300)
    plt.close(fig)


def write_report(metrics: pd.DataFrame, outage: pd.DataFrame, reliability: pd.DataFrame, low: pd.DataFrame) -> None:
    def md_table(df: pd.DataFrame, cols: list[str], n: int = 20) -> str:
        if df.empty:
            return "_Sem dados._"
        return simple_markdown_table(df[cols].head(n))

    def simple_markdown_table(df: pd.DataFrame) -> str:
        if df.empty:
            return "_Sem dados._"
        cols = [str(c) for c in df.columns]
        lines = [
            "| " + " | ".join(cols) + " |",
            "| " + " | ".join(["---"] * len(cols)) + " |",
        ]
        for _, row in df.iterrows():
            vals = []
            for col in df.columns:
                val = row[col]
                if isinstance(val, float):
                    vals.append("" if math.isnan(val) else f"{val:.4g}")
                else:
                    vals.append(str(val).replace("\n", " "))
            lines.append("| " + " | ".join(vals) + " |")
        return "\n".join(lines)

    ddqn_steps = metrics[metrics["method"] == "RSLAQ/DDQN"][["scenario", "episodes", "steps_total"]].drop_duplicates()
    sac_steps = metrics[metrics["method"] == "SAC"][["scenario", "episodes", "steps_total"]].drop_duplicates()

    step_logs_available = any(CONTROLLED_RESULTS.glob("**/step_metrics.csv")) if CONTROLLED_RESULTS.exists() else False
    drl_reliability_source = "step_metrics.csv por step" if step_logs_available else "snapshots finais rslaq-kpms.txt legados"

    fidelity_rows = [
        ("Estado 4x4 [btx,bfs,rsh,tdp] x [slices,cell]", "fiel ao artigo", "rslaq_kpis.py constroi matriz 4x4 em modo paper; bfs usa bufferBytes real quando disponivel."),
        ("Normalizacao das features", "equivalente, mas adaptado ao ns-3", "Normalizacao por caps fixos: btx=200000 bytes/10 ms, buffer=100000 bytes, tdp=1000 packets, rsh=100%."),
        ("Espaco de acao DDQN 198", "fiel ao artigo quando include_scheduler=True", "Tabela discreta com 66 combinacoes x 3 schedulers; script DDQN habilita por padrao."),
        ("Uso de scheduler na acao", "corrigido no codigo; requer nova campanha", "rslaq-sim agora le a coluna algorithm do IPC e aplica RR/PF/BCQI por slice; resultados legados ainda sao anteriores a correcao."),
        ("P_STA 50/50", "fiel no Python; adaptado no ns-3", "P_STA aplicado em rslaq_action_spaces.py; C++ usa percentuais diretamente para evitar dupla aplicacao."),
        ("Pesos 0.3333/0.4000/0.2667", "fiel ao artigo", "Constantes em reward/action_spaces; C++ baseline usa 0.33/0.40/0.27."),
        ("SLAs por cenario", "parcialmente fiel", "Reward define min/soft eMBB e buffer URLLC; MTC e no-policy para outage, embora haja mtc_target para graficos/reward."),
        ("Funcao de recompensa", "equivalente, mas adaptado ao ns-3", "h1/h2/h3 e custo scheduler implementados; outage usa confirmacao consecutiva de 5 passos."),
        ("Terminal por outage", "equivalente, mas adaptado ao ns-3", "Hard outage termina apos warmup e streak consecutivo."),
        ("Terminal por soft SLA", "fiel ao artigo conforme codigo", "Soft eMBB gera reward 0 e termina apos warmup."),
        ("Reliability = 1 - P(k_out)", "calculado nesta validacao", "Tabelas outage_by_seed.csv e reliability_by_seed.csv."),
        ("insufficient_resources", "equivalente como diagnostico", "Incluido em treino e CDF; excluido da Fig. 7 principal e incluido em versao diagnostica."),
        ("SAC continuo com softmax/soma 1", "fiel/adaptado", "Ator tanh -> continuous_action_to_prb usa softmax e P_STA."),
        ("SAC escolhe scheduler", "divergente", "SAC envia apenas 3 dimensoes de PRB; scheduler no C++ IPC fica PF."),
        ("Mesmo orcamento SAC vs DDQN", "corrigido no protocolo; nao rerrodado aqui", "Novo run_controlled_rslaq_validation.sh usa mesmo numero de episodios e steps por episodio para DDQN e SAC."),
    ]
    fidelity = pd.DataFrame(fidelity_rows, columns=["item", "classificacao", "evidencia"])

    report = f"""# Relatorio de Validacao Cientifica RSLAQ/ns-3

## 1. Resumo executivo

Esta validacao auditou a implementacao RSLAQ existente em `ns-3-dev` e `ns-o-ran-gym` e, apos autorizacao explicita, implementou correcoes de fidelidade a partir da Fase 2. Os artefatos numericos ainda usam os resultados disponiveis, salvo quando houver `results_controlled` gerado pela nova campanha.

Parecer de implementacao: **reproducao parcial corrigida, pendente de nova campanha estatistica**. O codigo agora cobre estado 4x4, pesos, P_STA no Python, DDQN com 198 acoes e aplicacao do scheduler vindo da acao. Os resultados legados continuam nao controlados para SAC vs DDQN.

## 2. Escopo e restricoes

- Alteracao autorizada em `ns-3-dev/scratch/rslaq/rslaq-sim.cc`: a coluna `algorithm` enviada pelo Python agora seleciona RR/PF/BCQI no scheduler slice-aware.
- Alteracoes em Python: logging por step, parametros de P_STA/pesos/reward, avaliacao DDQN com 198 acoes, script de campanha controlada.
- Artefatos de analise ficam em `analysis_rslaq_validation/`.
- Comparacoes SAC vs DDQN devem ser lidas como **exploratorias nao controladas**, pois os logs existentes usam orcamentos diferentes.

## 3. Metodologia

1. Auditoria somente leitura da estrutura, codigos Python, configuracoes e resultados.
2. Leitura dos baselines em `ns-3-dev/results_rslaq_network_only`.
3. Leitura dos logs em `ns-o-ran-gym/results/*_seed1`.
4. Calculo explicito de outage e reliability: `reliability = 1 - P(k_out)`.
5. Geracao de figuras estilo artigo com as metricas disponiveis, sem inventar metricas ausentes.
6. Novo protocolo controlado disponivel em `ns-o-ran-gym/examples/run_controlled_rslaq_validation.sh`.

## 4. Auditoria de unidades e metricas

Mapa de diretorios relevantes:

- `ns-3-dev/scratch/rslaq/rslaq-sim.cc`: simulador RSLAQ C++ lido apenas para auditoria.
- `ns-3-dev/results_rslaq_network_only/`: baselines RR/PF/BCQI/slice-aware/psta.
- `ns-o-ran-gym/src/environments/`: ambiente, KPIs, action spaces, reward.
- `ns-o-ran-gym/examples/`: scripts DDQN/SAC/eval/run_all.
- `ns-o-ran-gym/results/`: logs e snapshots de treino DDQN/SAC.
- `analysis_rslaq_validation/`: artefatos desta validacao.

Arquivos de configuracao de cenario:

- `ns-o-ran-gym/src/environments/scenario_configurations/rslaq_use_case.json`
- Definicoes efetivas de trafego RSLAQ em `ns-3-dev/scratch/rslaq/rslaq-sim.cc` (somente leitura): taxas por slice e tamanhos de pacote.

Arquivos de treino:

- `ns-o-ran-gym/examples/rslaq_train_ddqn.py`
- `ns-o-ran-gym/examples/rslaq_train_sac.py`
- `ns-o-ran-gym/examples/run_all_scenarios.sh`
- `ns-o-ran-gym/examples/rslaq_eval_policy.py`

Arquivos de reward:

- `ns-o-ran-gym/src/environments/rslaq_reward.py`
- `ns-o-ran-gym/src/environments/rslaq_action_spaces.py` para P_STA e transformacao de acoes.

Metricas disponiveis:

- Throughput: `thr_mbps` baseline, `throughputMbps` DRL KPM, `throughput_mbps_mean` summary. Unidade: Mbps.
- Bytes transmitidos/recebidos: `tx_bytes_delta`, `rx_bytes_delta`, `dTxBytes`, `dRxBytes`, `rx_bytes_total`, `tx_bytes_total`. Unidade: bytes.
- Buffer: `buffer_bytes`, `bufferBytes`. Unidade: bytes, lido do scheduler DL.
- Dropped/lost: `dropped_packets_delta`, `dLostPackets`. Unidade: packets, nao bytes.
- PLR/PDR: `loss_pct_interval`, `plr`, `pdr_pct`, `plr_pct`. Unidade: porcentagem.
- PRB/resource share: `rsh_configured_pct`, `resourceSharePct`, `rsh_real_pct_mean`. Unidade: porcentagem.
- Reward/outage/soft/action: logs DDQN/SAC por episodio.
- Scheduler: baselines por `baseline_mode`; a acao DDQN inclui scheduler no Python, mas a aplicacao IPC atual usa PF fixo.

Granularidade temporal:

- Baseline `timeseries.csv`: por UE e timestamp, periodo de indicacao de 10 ms.
- Baseline `summary.csv`: media final por slice por seed/run.
- DRL `step_metrics.csv`: quando gerado pela versao corrigida, uma linha por slice/step/simulacao.
- DRL legado `rslaq-kpms.txt`: snapshot sobrescrito por episodio/simulacao, por UE no ultimo passo disponivel.
- DRL `*_training_log.csv`: por episodio.
- Seeds existentes para RSLAQ: seed 1 apenas.

## 5. Fidelidade ao artigo

{simple_markdown_table(fidelity)}

## 6. Resultados por cenario

Resumo de treino DDQN:

{md_table(ddqn_steps, ["scenario", "episodes", "steps_total"], 10)}

Resumo de treino SAC:

{md_table(sac_steps, ["scenario", "episodes", "steps_total"], 10)}

Resumo principal de reliability:

{md_table(reliability[reliability["slice"].isin(["eMBB", "URLLC"])], ["method", "scenario", "seed", "slice", "samples", "outage_probability", "reliability"], 40)}

## 7. Comparacao baseline vs DDQN vs SAC

Os baselines RR/PF/BCQI/Opt legados usam uma seed/run de ns-3 e nao tem reward DRL. DDQN e SAC legados tem logs por episodio, mas somente seed 1. A comparacao SAC vs DDQN existente **nao e controlada**. O novo script `run_controlled_rslaq_validation.sh` corrige esse protocolo, mas os resultados estatisticos so passam a ser conclusivos apos a campanha multi-seed.

## 8. Figuras reproduzidas no estilo do artigo

Geradas:

- `figures/reward_ddqn_by_scenario.png` e `.pdf`
- `figures/reward_sac_by_scenario.png` e `.pdf`
- `figures/fig6_cdf_rslaq_style.png` e `.pdf`
- `figures/fig7_reliability_rslaq_style.png` e `.pdf`
- `figures/fig7_reliability_rslaq_style_including_insufficient.png` e `.pdf`

Figuras D/E de sensibilidade `P_STA` e prioridade invertida nao foram geradas porque os resultados existentes so cobrem `P_STA=0.5` e pesos padrao. Gera-las exigiria novos experimentos/alteracoes de configuracao DRL; isso fica para a Linha B.

## 9. Analise do cenario low_traffic

{simple_markdown_table(low)}

Leitura tecnica: no C++ lido somente para auditoria, `low_traffic` configura eMBB com 5 Mbps agregados para 5 UEs, pacote de 1500 bytes, aproximadamente 1 Mbps por UE e intervalo estimado de 12 ms por pacote. O SLA minimo eMBB do reward e 10 Mbps por slice. Como o throughput medido e goodput IP/UDP via FlowMonitor (`rxBytes` delta), nao ha evidencia de que retransmissoes ou bytes de controle estejam inflando a metrica. Assim, para eMBB em `low_traffic`, a incompatibilidade entre carga oferecida e SLA minimo e uma conclusao de auditoria de unidade/configuracao, nao uma suposicao previa.

## 10. Analise de reliability/outage

Outage foi calculado com as mesmas regras observaveis no reward:

- eMBB: throughput agregado do slice abaixo de `embb_min` quando ha demanda (`dTxBytes >= 1`).
- URLLC: `bufferBytes_max > 10000`.
- MTC: no-policy para outage, conforme implementacao.

Para baselines, a amostra e por timestamp de 10 ms. Para DRL, a fonte atual e: **{drl_reliability_source}**. As tabelas `outage_by_seed.csv` e `reliability_by_seed.csv` explicitam a coluna `source`.

## 11. Ablations

Linha A paper-faithful: pesos originais, `P_STA=0.5`, SLAs originais implementados, soft terminal e DDQN com 198 acoes aplicando scheduler no ns-3.

Linha B ns-3-calibrada/ablation: suportada por argumentos (`--p_sta_static_fraction`, `--p_sta_weights`, `--reward_alpha`, `--reward_beta`, `--reward_gamma`). Recomendacao: rodar ao menos 5 seeds com mesmo orcamento DDQN/SAC, e entao testar SLAs recalibrados apenas se a incompatibilidade de carga oferecida for documentada por cenario.

## 12. Limitacoes

- Resultados legados ainda tem apenas seed 1 para RSLAQ/DDQN, SAC e baselines RSLAQ.
- Sem IC 95% para metricas principais, pois ha menos de 5 seeds.
- Sem tempo de treino/inferencia nos logs existentes.
- Logs novos por step corrigem a falta de outage por slice; resultados legados ainda nao.
- Scheduler escolhido pela acao DDQN foi corrigido no caminho IPC, mas resultados legados foram gerados antes dessa correcao.
- `low_traffic` tem carga eMBB oferecida abaixo do SLA minimo eMBB.

## 13. Parecer cientifico final

Classificacao: **reproducao parcial corrigida, estatisticamente inconclusiva ate nova campanha**.

A implementacao agora cobre os pontos estruturais centrais do RSLAQ no codigo, incluindo scheduler na acao DDQN. Ainda nao deve ser classificada como reproducao fiel completa com evidencia estatistica enquanto a campanha controlada multi-seed nao for executada e analisada.
"""

    (OUT / "RELATORIO_VALIDACAO_CIENTIFICA_RSLAQ_NS3.md").write_text(report, encoding="utf-8")


def write_changelog_and_modified() -> None:
    changelog = """# Changelog

## Validacao RSLAQ/ns-3

- Aplicada correcao autorizada no IPC do ns-3 para consumir `algorithm` e aplicar RR/PF/BCQI na acao DDQN.
- Adicionado logging por step (`step_metrics.csv`) no `RslaqEnv`.
- Adicionados parametros de P_STA e pesos de reward aos scripts DDQN/SAC/eval.
- Corrigida avaliacao DDQN para usar 198 acoes quando scheduler esta habilitado.
- Criado script de campanha controlada multi-seed com mesmo orcamento DDQN/SAC.
- Criada pasta `analysis_rslaq_validation/`.
- Geradas tabelas de resumo, outage, reliability e auditoria low_traffic a partir de resultados existentes.
- Geradas figuras estilo artigo em PNG/PDF.
- Gerado relatorio cientifico final.
"""
    modified = """# Modified Files

Arquivos modificados:

- `ns-3-dev/scratch/rslaq/rslaq-sim.cc`
- `ns-o-ran-gym/src/environments/rslaq_env.py`
- `ns-o-ran-gym/examples/rslaq_train_ddqn.py`
- `ns-o-ran-gym/examples/rslaq_train_sac.py`
- `ns-o-ran-gym/examples/rslaq_eval_policy.py`
- `analysis_rslaq_validation/generate_validation_artifacts.py`

Arquivos novos/criados:

- `analysis_rslaq_validation/generate_validation_artifacts.py`
- `analysis_rslaq_validation/RELATORIO_VALIDACAO_CIENTIFICA_RSLAQ_NS3.md`
- `analysis_rslaq_validation/CHANGELOG.md`
- `analysis_rslaq_validation/MODIFIED_FILES.md`
- `analysis_rslaq_validation/tables/metrics_summary.csv`
- `analysis_rslaq_validation/tables/reliability_by_seed.csv`
- `analysis_rslaq_validation/tables/outage_by_seed.csv`
- `analysis_rslaq_validation/tables/low_traffic_audit.csv`
- `analysis_rslaq_validation/figures/reward_ddqn_by_scenario.png`
- `analysis_rslaq_validation/figures/reward_ddqn_by_scenario.pdf`
- `analysis_rslaq_validation/figures/reward_sac_by_scenario.png`
- `analysis_rslaq_validation/figures/reward_sac_by_scenario.pdf`
- `analysis_rslaq_validation/figures/fig6_cdf_rslaq_style.png`
- `analysis_rslaq_validation/figures/fig6_cdf_rslaq_style.pdf`
- `analysis_rslaq_validation/figures/fig7_reliability_rslaq_style.png`
- `analysis_rslaq_validation/figures/fig7_reliability_rslaq_style.pdf`
- `analysis_rslaq_validation/figures/fig7_reliability_rslaq_style_including_insufficient.png`
- `analysis_rslaq_validation/figures/fig7_reliability_rslaq_style_including_insufficient.pdf`
- `ns-o-ran-gym/examples/run_controlled_rslaq_validation.sh`

Registro pre-edicao:

- `git status --short` antes da criacao desta pasta ja mostrava alteracoes pre-existentes em `ns-o-ran-gym/results_greenran/...`; elas nao foram tocadas por esta validacao.
"""
    (OUT / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (OUT / "MODIFIED_FILES.md").write_text(modified, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    outage, reliability = compute_outage_tables()
    metrics = build_metrics_summary(outage, reliability)
    low = low_traffic_audit()

    metrics.to_csv(TAB / "metrics_summary.csv", index=False)
    outage.to_csv(TAB / "outage_by_seed.csv", index=False)
    reliability.to_csv(TAB / "reliability_by_seed.csv", index=False)
    low.to_csv(TAB / "low_traffic_audit.csv", index=False)

    plot_reward("ddqn", "reward_ddqn_by_scenario")
    plot_reward("sac", "reward_sac_by_scenario")
    plot_fig6_cdf()
    plot_fig7_reliability(reliability, include_insufficient=False)
    plot_fig7_reliability(reliability, include_insufficient=True)
    write_report(metrics, outage, reliability, low)
    write_changelog_and_modified()

    print("Generated validation artifacts under", OUT)


if __name__ == "__main__":
    main()
