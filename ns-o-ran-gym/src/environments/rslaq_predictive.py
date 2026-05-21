"""Predictive helpers for RSLAQ experiments.

This module keeps the predictive data pipeline independent from ``RslaqEnv``.
It consumes the existing per-step ``step_metrics.csv`` logs and builds compact
temporal windows that can be used both for offline forecaster training and for
online state augmentation during SAC training.
"""

from __future__ import annotations

import csv
import glob
import os
from dataclasses import dataclass
from typing import Iterable, List, Sequence

import numpy as np
import torch
import torch.nn as nn

from .rslaq_kpis import (
    DEFAULT_MAX_BTX,
    DEFAULT_MAX_BUFFER_BYTES,
    DEFAULT_MAX_TDP,
)


SCENARIOS = [
    "low_traffic",
    "normal",
    "congestion",
    "stressed",
    "insufficient_resources",
]

OBS_DIM = 16
ACTION_DIM = 3
RISK_DIM = 6
SCENARIO_DIM = len(SCENARIOS)
FEATURE_DIM = OBS_DIM + ACTION_DIM + 1 + RISK_DIM + SCENARIO_DIM
FORECAST_DIM = RISK_DIM + OBS_DIM


@dataclass(frozen=True)
class StepFrame:
    """One environment step reconstructed from three per-slice log rows."""

    sim_id: str
    scenario: str
    seed: int
    episode: int
    step: int
    obs: np.ndarray
    action: np.ndarray
    reward: float
    outage_flags: np.ndarray
    soft_flags: np.ndarray


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _clip_norm(value: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return float(np.clip(value / cap, 0.0, 1.0))


def scenario_one_hot(scenario: str) -> np.ndarray:
    vec = np.zeros(SCENARIO_DIM, dtype=np.float32)
    if scenario in SCENARIOS:
        vec[SCENARIOS.index(scenario)] = 1.0
    return vec


def rows_to_observation(rows: Sequence[dict]) -> np.ndarray:
    """Build the same 4x4 paper-style observation from step log rows."""
    obs = np.zeros((4, 4), dtype=np.float32)
    slice_rows = {int(row["slice_id"]): row for row in rows}

    for sid in range(3):
        row = slice_rows.get(sid, {})
        obs[0, sid] = _clip_norm(_safe_float(row.get("dTxBytes")), DEFAULT_MAX_BTX)
        obs[1, sid] = _clip_norm(
            _safe_float(row.get("bufferBytes_mean")), DEFAULT_MAX_BUFFER_BYTES
        )
        obs[2, sid] = _clip_norm(_safe_float(row.get("resourceSharePct")), 100.0)
        obs[3, sid] = _clip_norm(_safe_float(row.get("dLostPackets")), DEFAULT_MAX_TDP)

    dtx_total = sum(_safe_float(row.get("dTxBytes")) for row in slice_rows.values())
    buffer_mean = np.mean(
        [_safe_float(row.get("bufferBytes_mean")) for row in slice_rows.values()]
    )
    rsh_mean = np.mean(
        [_safe_float(row.get("resourceSharePct")) for row in slice_rows.values()]
    )
    lost_total = sum(_safe_float(row.get("dLostPackets")) for row in slice_rows.values())

    obs[0, 3] = _clip_norm(dtx_total, DEFAULT_MAX_BTX * 3)
    obs[1, 3] = _clip_norm(buffer_mean, DEFAULT_MAX_BUFFER_BYTES * 3)
    obs[2, 3] = _clip_norm(rsh_mean, 100.0)
    obs[3, 3] = _clip_norm(lost_total, DEFAULT_MAX_TDP * 3)
    return obs


def rows_to_frame(rows: Sequence[dict]) -> StepFrame:
    """Convert the three rows for one step into a compact frame."""
    if len(rows) < 3:
        raise ValueError(f"expected at least 3 slice rows, got {len(rows)}")
    first = rows[0]
    by_slice = {int(row["slice_id"]): row for row in rows}

    action = np.array(
        [
            _safe_float(first.get("action_embb")) / 100.0,
            _safe_float(first.get("action_urllc")) / 100.0,
            _safe_float(first.get("action_mtc")) / 100.0,
        ],
        dtype=np.float32,
    )
    outage = np.array(
        [_as_bool(by_slice.get(sid, {}).get("outage_flag")) for sid in range(3)],
        dtype=np.float32,
    )
    soft = np.array(
        [_as_bool(by_slice.get(sid, {}).get("soft_flag")) for sid in range(3)],
        dtype=np.float32,
    )

    return StepFrame(
        sim_id=str(first.get("sim_id", "")),
        scenario=str(first.get("scenario", "")),
        seed=_safe_int(first.get("seed")),
        episode=_safe_int(first.get("episode")),
        step=_safe_int(first.get("step")),
        obs=rows_to_observation(rows),
        action=action,
        reward=_safe_float(first.get("reward")),
        outage_flags=outage,
        soft_flags=soft,
    )


def frame_to_feature(frame: StepFrame) -> np.ndarray:
    reward_scaled = (np.clip(frame.reward, -1.0, 2.0) + 1.0) / 3.0
    return np.concatenate(
        [
            frame.obs.reshape(-1),
            frame.action,
            np.array([reward_scaled], dtype=np.float32),
            frame.outage_flags,
            frame.soft_flags,
            scenario_one_hot(frame.scenario),
        ]
    ).astype(np.float32)


def frames_to_target(future_frames: Sequence[StepFrame]) -> np.ndarray:
    outage_risk = np.max([frame.outage_flags for frame in future_frames], axis=0)
    soft_risk = np.max([frame.soft_flags for frame in future_frames], axis=0)
    obs_mean = np.mean([frame.obs.reshape(-1) for frame in future_frames], axis=0)
    return np.concatenate([outage_risk, soft_risk, obs_mean]).astype(np.float32)


def load_step_frames(csv_path: str) -> List[StepFrame]:
    """Load all step frames from one ``step_metrics.csv`` file."""
    grouped: dict[tuple[int, int], list[dict]] = {}
    with open(csv_path, "r", newline="") as f:
        for row in csv.DictReader(f):
            key = (_safe_int(row.get("episode")), _safe_int(row.get("step")))
            grouped.setdefault(key, []).append(row)

    frames = []
    for key in sorted(grouped):
        rows = sorted(grouped[key], key=lambda row: _safe_int(row.get("slice_id")))
        if len(rows) >= 3:
            frames.append(rows_to_frame(rows[:3]))
    return frames


def find_step_metric_files(source_root: str, limit_files: int | None = None) -> list[str]:
    files = sorted(glob.glob(os.path.join(source_root, "**", "step_metrics.csv"), recursive=True))
    if limit_files is not None and limit_files > 0:
        files = files[:limit_files]
    return files


def build_forecast_sequences(
    source_root: str,
    sequence_len: int = 8,
    horizon: int = 5,
    limit_files: int | None = None,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Build ``(X, y, meta)`` arrays from a campaign result directory."""
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    meta: list[dict] = []

    for path in find_step_metric_files(source_root, limit_files=limit_files):
        frames = load_step_frames(path)
        if len(frames) < sequence_len + horizon:
            continue
        features = [frame_to_feature(frame) for frame in frames]
        for end_idx in range(sequence_len - 1, len(frames) - horizon):
            future = frames[end_idx + 1 : end_idx + 1 + horizon]
            xs.append(np.stack(features[end_idx - sequence_len + 1 : end_idx + 1]))
            ys.append(frames_to_target(future))
            meta.append(
                {
                    "source": path,
                    "sim_id": frames[end_idx].sim_id,
                    "scenario": frames[end_idx].scenario,
                    "seed": frames[end_idx].seed,
                    "episode": frames[end_idx].episode,
                    "step": frames[end_idx].step,
                }
            )

    if not xs:
        return (
            np.zeros((0, sequence_len, FEATURE_DIM), dtype=np.float32),
            np.zeros((0, FORECAST_DIM), dtype=np.float32),
            meta,
        )
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32), meta


class TemporalKpiForecaster(nn.Module):
    """Small GRU forecaster for near-future SLA risk and normalized KPIs."""

    def __init__(
        self,
        input_dim: int = FEATURE_DIM,
        hidden_dim: int = 64,
        output_dim: int = FORECAST_DIM,
        num_layers: int = 1,
        dropout: float = 0.0,
    ):
        super().__init__()
        effective_dropout = dropout if num_layers > 1 else 0.0
        self.gru = nn.GRU(
            input_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=effective_dropout,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, hidden = self.gru(x)
        logits = self.head(hidden[-1])
        return torch.sigmoid(logits)


def empty_feature(scenario: str = "normal") -> np.ndarray:
    frame = StepFrame(
        sim_id="",
        scenario=scenario,
        seed=0,
        episode=0,
        step=0,
        obs=np.zeros((4, 4), dtype=np.float32),
        action=np.array([1 / 3, 1 / 3, 1 / 3], dtype=np.float32),
        reward=0.0,
        outage_flags=np.zeros(3, dtype=np.float32),
        soft_flags=np.zeros(3, dtype=np.float32),
    )
    return frame_to_feature(frame)


def forecast_from_history(
    model: TemporalKpiForecaster,
    history: Iterable[np.ndarray],
    sequence_len: int,
    scenario: str,
    device: torch.device | str = "cpu",
) -> np.ndarray:
    """Run the forecaster using left-padding when the history is short."""
    items = [np.asarray(item, dtype=np.float32) for item in history]
    pad = [empty_feature(scenario)] * max(0, sequence_len - len(items))
    window = (pad + items)[-sequence_len:]
    x = torch.as_tensor(np.stack(window), dtype=torch.float32, device=device).unsqueeze(0)
    model.eval()
    with torch.no_grad():
        return model(x).detach().cpu().numpy().reshape(-1).astype(np.float32)
