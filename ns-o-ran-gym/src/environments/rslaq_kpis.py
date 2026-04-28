"""
RSLAQ KPI Parser and Observation Builder.

Reads per-UE KPMs produced by ns-3 (rslaq-kpms.txt) and builds the
observation matrix used by the DRL agent.

Important Notes on Proxies:
----------------------------
- ``bfs`` (row 1) currently uses ``plr`` (packet loss ratio %) as a proxy
  for buffer status / backlog. This is an approximation.
- ``tdp`` (row 3) currently uses ``dLostPackets`` (delta lost packets) as a
  proxy for dropped/transmitted-dropped bytes. This is an approximation.

TODO(bfs-real): Replace plr proxy with real bufferSize/bufferStatus when
    ns-3 exports it in rslaq-kpms.txt.
TODO(tdp-real): Replace dLostPackets proxy with real dropped/transmitted
    dropped bytes when available.
"""

import csv
import glob
import os
from typing import Dict, Any
import numpy as np

from .rslaq_slice_ids import normalize_slice_id, get_num_slices

# Default normalization caps
DEFAULT_MAX_BTX = 200000.0  # bytes
DEFAULT_MAX_TDP = 1000.0    # packets (proxy)


def parse_kpm_file(
    kpm_path: str,
    last_timestamp: int = 0,
) -> Dict[int, Dict[str, Any]]:
    """
    Parse rslaq-kpms.txt and return aggregated metrics per slice + cell total.

    The ns-3 file format is expected to be CSV with columns:
        timestamp,ueImsi,sliceId,dTxBytes,dRxBytes,plr,resourceSharePct,dLostPackets,throughputMbps

    Args:
        kpm_path: Full path to the KPM file.
        last_timestamp: Only consider rows with timestamp >= this value.

    Returns:
        Dictionary with keys 0, 1, 2 (slices) and 3 (cell total).
        Each value is a dict with aggregated metrics:
            - dTxBytes_sum
            - dRxBytes_sum
            - plr_mean
            - resourceSharePct_mean
            - dLostPackets_sum
            - throughputMbps_sum
            - ue_count
    """
    slice_data: Dict[int, Dict[str, float]] = {
        0: {"dTxBytes_sum": 0.0, "dRxBytes_sum": 0.0, "plr_sum": 0.0,
            "resourceSharePct_sum": 0.0, "dLostPackets_sum": 0.0,
            "throughputMbps_sum": 0.0, "ue_count": 0.0},
        1: {"dTxBytes_sum": 0.0, "dRxBytes_sum": 0.0, "plr_sum": 0.0,
            "resourceSharePct_sum": 0.0, "dLostPackets_sum": 0.0,
            "throughputMbps_sum": 0.0, "ue_count": 0.0},
        2: {"dTxBytes_sum": 0.0, "dRxBytes_sum": 0.0, "plr_sum": 0.0,
            "resourceSharePct_sum": 0.0, "dLostPackets_sum": 0.0,
            "throughputMbps_sum": 0.0, "ue_count": 0.0},
    }

    latest_ts = last_timestamp

    if not os.path.exists(kpm_path):
        return _build_return_dict(slice_data, latest_ts)

    with open(kpm_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = int(row["timestamp"])
            except (KeyError, ValueError):
                continue
            if ts < last_timestamp:
                continue
            latest_ts = max(latest_ts, ts)

            try:
                raw_slice_id = int(row.get("sliceId", -1))
                slice_id = normalize_slice_id(raw_slice_id)
            except (ValueError, KeyError):
                continue

            if slice_id not in slice_data:
                continue

            sd = slice_data[slice_id]
            sd["dTxBytes_sum"] += float(row.get("dTxBytes", 0.0))
            sd["dRxBytes_sum"] += float(row.get("dRxBytes", 0.0))
            sd["plr_sum"] += float(row.get("plr", 0.0))
            sd["resourceSharePct_sum"] += float(row.get("resourceSharePct", 0.0))
            sd["dLostPackets_sum"] += float(row.get("dLostPackets", 0.0))
            sd["throughputMbps_sum"] += float(row.get("throughputMbps", 0.0))
            sd["ue_count"] += 1.0

    return _build_return_dict(slice_data, latest_ts)


def _build_return_dict(
    slice_data: Dict[int, Dict[str, float]],
    latest_ts: int,
) -> Dict[int, Dict[str, Any]]:
    """Build the aggregated return dict with averages and cell totals."""
    result: Dict[int, Dict[str, Any]] = {}
    cell = {
        "dTxBytes_sum": 0.0,
        "dRxBytes_sum": 0.0,
        "plr_mean": 0.0,
        "resourceSharePct_mean": 0.0,
        "dLostPackets_sum": 0.0,
        "throughputMbps_sum": 0.0,
        "ue_count": 0.0,
    }

    for sid in range(get_num_slices()):
        sd = slice_data[sid]
        n = sd["ue_count"]
        if n > 0:
            agg = {
                "dTxBytes_sum": sd["dTxBytes_sum"],
                "dRxBytes_sum": sd["dRxBytes_sum"],
                "plr_mean": sd["plr_sum"] / n,
                "resourceSharePct_mean": sd["resourceSharePct_sum"] / n,
                "dLostPackets_sum": sd["dLostPackets_sum"],
                "throughputMbps_sum": sd["throughputMbps_sum"],
                "ue_count": int(n),
            }
        else:
            agg = {
                "dTxBytes_sum": 0.0,
                "dRxBytes_sum": 0.0,
                "plr_mean": 0.0,
                "resourceSharePct_mean": 0.0,
                "dLostPackets_sum": 0.0,
                "throughputMbps_sum": 0.0,
                "ue_count": 0,
            }
        result[sid] = agg

        cell["dTxBytes_sum"] += agg["dTxBytes_sum"]
        cell["dRxBytes_sum"] += agg["dRxBytes_sum"]
        cell["dLostPackets_sum"] += agg["dLostPackets_sum"]
        cell["throughputMbps_sum"] += agg["throughputMbps_sum"]
        cell["ue_count"] += agg["ue_count"]

    # Cell-level averages for plr and rsh (weighted by ue_count or simple mean)
    total_ue = cell["ue_count"]
    if total_ue > 0:
        cell_plr_sum = sum(result[sid]["plr_mean"] for sid in range(get_num_slices()))
        cell_rsh_sum = sum(result[sid]["resourceSharePct_mean"] for sid in range(get_num_slices()))
        cell["plr_mean"] = cell_plr_sum / get_num_slices()
        cell["resourceSharePct_mean"] = cell_rsh_sum / get_num_slices()
    else:
        cell["plr_mean"] = 0.0
        cell["resourceSharePct_mean"] = 0.0

    result[3] = cell
    result["_latest_timestamp"] = latest_ts
    return result


def build_observation(
    kpi_dict: Dict[int, Dict[str, Any]],
    mode: str = "paper",
    max_btx: float = DEFAULT_MAX_BTX,
    max_tdp: float = DEFAULT_MAX_TDP,
) -> np.ndarray:
    """
    Build the observation matrix from parsed KPIs.

    Modes:
        - "paper": Returns (4, 4) matrix:
            rows: [btx, bfs, rsh, tdp]
            cols: [eMBB, URLLC, MTC, cell]
        - "debug": Returns (3, 5) legacy matrix for backward compatibility.

    Normalization:
        - btx (row 0): dTxBytes_sum / max_btx, clipped to [0, 1]
        - bfs (row 1): plr_mean / 100.0, clipped to [0, 1]
                     **PROXY: uses plr as buffer status approximation.**
        - rsh (row 2): resourceSharePct_mean / 100.0, clipped to [0, 1]
        - tdp (row 3): dLostPackets_sum / max_tdp, clipped to [0, 1]
                     **PROXY: uses lost packets as dropped bytes approximation.**

    Args:
        kpi_dict: Output from parse_kpm_file.
        mode: "paper" or "debug".
        max_btx: Cap for transmitted bytes normalization.
        max_tdp: Cap for lost packets normalization.

    Returns:
        np.ndarray of the requested shape.
    """
    if mode == "paper":
        obs = np.zeros((4, 4), dtype=np.float32)
        for col, sid in enumerate(range(get_num_slices())):
            metrics = kpi_dict.get(sid, {})
            obs[0, col] = _clip_norm(metrics.get("dTxBytes_sum", 0.0), max_btx)
            obs[1, col] = _clip_norm(metrics.get("plr_mean", 0.0), 100.0)
            obs[2, col] = _clip_norm(metrics.get("resourceSharePct_mean", 0.0), 100.0)
            obs[3, col] = _clip_norm(metrics.get("dLostPackets_sum", 0.0), max_tdp)

        # Cell column (index 3)
        cell = kpi_dict.get(3, {})
        obs[0, 3] = _clip_norm(cell.get("dTxBytes_sum", 0.0), max_btx * get_num_slices())
        obs[1, 3] = _clip_norm(cell.get("plr_mean", 0.0), 100.0)
        obs[2, 3] = _clip_norm(cell.get("resourceSharePct_mean", 0.0), 100.0)
        obs[3, 3] = _clip_norm(cell.get("dLostPackets_sum", 0.0), max_tdp * get_num_slices())
        return obs

    elif mode == "debug":
        # Legacy (3, 5): slices x [thr, btx, plr, rsh, lost]
        obs = np.zeros((3, 5), dtype=np.float32)
        for row, sid in enumerate(range(get_num_slices())):
            metrics = kpi_dict.get(sid, {})
            thr = metrics.get("throughputMbps_sum", 0.0)
            # rough normalization for throughput in debug mode
            obs[row, 0] = min(thr / 150.0, 1.0)
            obs[row, 1] = _clip_norm(metrics.get("dTxBytes_sum", 0.0), max_btx)
            obs[row, 2] = _clip_norm(metrics.get("plr_mean", 0.0), 100.0)
            obs[row, 3] = _clip_norm(metrics.get("resourceSharePct_mean", 0.0), 100.0)
            obs[row, 4] = _clip_norm(metrics.get("dLostPackets_sum", 0.0), max_tdp)
        return obs
    else:
        raise ValueError(f"Unknown observation mode: {mode}. Use 'paper' or 'debug'.")


def _clip_norm(value: float, cap: float) -> float:
    """Normalize value by cap and clip to [0, 1]."""
    if cap <= 0:
        return 0.0
    return float(np.clip(value / cap, 0.0, 1.0))
