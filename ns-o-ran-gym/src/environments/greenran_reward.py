"""
GreenRAN SLA-aware Reward Function.

Computes the reward based on per-slice KPIs and scenario-specific SLA targets
adapted to the GreenRAN slice profiles:

- VIDEO_EMBB (slice 0): high DL throughput, low delay, high PDR
- SENSOR_MMTC (slice 1): sporadic UL, focus on low buffer/latency proxy and PDR
- GENERIC_EMBB (slice 2): mixed DL+UL throughput, moderate delay/PDR

KPIs used (all from rslaq-kpms.txt):
    - throughputMbps_sum  → throughput bonification
    - bufferBytes_max     → latency/congestion proxy (exp decay)
    - plr_mean            → packet-loss / PDR proxy
    - dLostPackets_sum    → absolute loss penalty

The reward is a weighted sum of normalized slice objectives minus
violation penalties.  Terminal conditions trigger on hard SLA breaches
(e.g. throughput below minimum, PLR above threshold, buffer above limit).
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .greenran_slice_ids import get_num_slices, slice_name

# Importance weights [VIDEO_EMBB, SENSOR_MMTC, GENERIC_EMBB]
# VIDEO and GENERIC are both eMBB-like; SENSOR is mMTC monitoring
ALPHA = 0.40   # omega_0: VIDEO_EMBB
BETA = 0.25    # omega_1: SENSOR_MMTC
GAMMA = 0.35   # omega_2: GENERIC_EMBB

# Throughput normalization caps (Mbps) — used for h_1 / h_3 scaling
DEFAULT_MAX_THR_MBPS = 150.0

# Buffer normalization (bytes) for h_2 exp decay
DEFAULT_BUFFER_NORM_BYTES = 10000.0

# Default PLR threshold (%) above which we start penalising
DEFAULT_PLR_THRESHOLD = 5.0

# ---------------------------------------------------------------------------
# SLA configurations per GreenRAN scenario (approximated from C++ defaults)
# ---------------------------------------------------------------------------
SLA_BY_SCENARIO: Dict[str, Dict[str, Any]] = {
    "greenran_low": {
        "video_min_throughput_mbps": 40.0,
        "video_soft_max_throughput_mbps": 55.0,
        "sensor_max_buffer_bytes": 8000.0,
        "sensor_plr_threshold": 5.0,
        "generic_min_throughput_mbps": 15.0,
        "generic_soft_max_throughput_mbps": 25.0,
        "generic_plr_threshold": 3.0,
    },
    "greenran_normal": {
        "video_min_throughput_mbps": 60.0,
        "video_soft_max_throughput_mbps": 80.0,
        "sensor_max_buffer_bytes": 10000.0,
        "sensor_plr_threshold": 5.0,
        "generic_min_throughput_mbps": 80.0,
        "generic_soft_max_throughput_mbps": 110.0,
        "generic_plr_threshold": 3.0,
    },
    "greenran_video_heavy": {
        "video_min_throughput_mbps": 100.0,
        "video_soft_max_throughput_mbps": 130.0,
        "sensor_max_buffer_bytes": 10000.0,
        "sensor_plr_threshold": 5.0,
        "generic_min_throughput_mbps": 90.0,
        "generic_soft_max_throughput_mbps": 130.0,
        "generic_plr_threshold": 3.0,
    },
    "greenran_congestion": {
        "video_min_throughput_mbps": 100.0,
        "video_soft_max_throughput_mbps": 130.0,
        "sensor_max_buffer_bytes": 15000.0,
        "sensor_plr_threshold": 8.0,
        "generic_min_throughput_mbps": 200.0,
        "generic_soft_max_throughput_mbps": 260.0,
        "generic_plr_threshold": 5.0,
    },
    "greenran_night_energy": {
        "video_min_throughput_mbps": 40.0,
        "video_soft_max_throughput_mbps": 55.0,
        "sensor_max_buffer_bytes": 8000.0,
        "sensor_plr_threshold": 5.0,
        "generic_min_throughput_mbps": 5.0,
        "generic_soft_max_throughput_mbps": 12.0,
        "generic_plr_threshold": 3.0,
    },
    "greenran_balanced": {
        "video_min_throughput_mbps": 60.0,
        "video_soft_max_throughput_mbps": 80.0,
        "sensor_max_buffer_bytes": 10000.0,
        "sensor_plr_threshold": 5.0,
        "generic_min_throughput_mbps": 100.0,
        "generic_soft_max_throughput_mbps": 135.0,
        "generic_plr_threshold": 3.0,
    },
}


@dataclass
class RewardResult:
    reward: float = 0.0
    terminated: bool = False
    truncated: bool = False
    outage_flags: Dict[int, bool] = field(default_factory=dict)
    soft_flags: Dict[int, bool] = field(default_factory=dict)
    optimization_terms: Dict[str, float] = field(default_factory=dict)
    debug_info: Dict[str, Any] = field(default_factory=dict)


def _evaluate_outage_conditions(
    metrics: Dict[int, Dict[str, Any]],
    sla: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[int, bool]:
    """
    Evaluate instantaneous hard-outage conditions per slice.

    VIDEO_EMBB: throughput < min OR plr > threshold
    SENSOR_MMTC: buffer > max OR plr > threshold
    GENERIC_EMBB: throughput < min OR plr > threshold
    """
    flags: Dict[int, bool] = {0: False, 1: False, 2: False}

    video = metrics.get(0, {})
    sensor = metrics.get(1, {})
    generic = metrics.get(2, {})

    min_tx = float(config.get("min_tx_bytes_for_outage", 1.0))

    # VIDEO_EMBB outage
    video_thr = float(video.get("throughputMbps_sum", 0.0))
    video_plr = float(video.get("plr_mean", 0.0))
    video_tx = float(video.get("dTxBytes_sum", 0.0))
    if (video_thr < sla["video_min_throughput_mbps"] and video_tx >= min_tx) or \
       (video_plr > sla.get("video_plr_threshold", DEFAULT_PLR_THRESHOLD)):
        flags[0] = True

    # SENSOR_MMTC outage
    sensor_buffer = float(sensor.get("bufferBytes_max", 0.0))
    sensor_plr = float(sensor.get("plr_mean", 0.0))
    if (sensor_buffer > sla["sensor_max_buffer_bytes"]) or \
       (sensor_plr > sla["sensor_plr_threshold"]):
        flags[1] = True

    # GENERIC_EMBB outage
    generic_thr = float(generic.get("throughputMbps_sum", 0.0))
    generic_plr = float(generic.get("plr_mean", 0.0))
    generic_tx = float(generic.get("dTxBytes_sum", 0.0))
    if (generic_thr < sla["generic_min_throughput_mbps"] and generic_tx >= min_tx) or \
       (generic_plr > sla.get("generic_plr_threshold", DEFAULT_PLR_THRESHOLD)):
        flags[2] = True

    return flags


def _evaluate_soft_conditions(
    metrics: Dict[int, Dict[str, Any]],
    sla: Dict[str, Any],
) -> Dict[int, bool]:
    """
    Evaluate instantaneous soft SLA conditions (wasteful over-allocation).

    VIDEO_EMBB: throughput > soft max
    GENERIC_EMBB: throughput > soft max
    SENSOR_MMTC: no soft condition (no-policy-like for mMTC)
    """
    flags: Dict[int, bool] = {0: False, 1: False, 2: False}

    video = metrics.get(0, {})
    generic = metrics.get(2, {})

    video_thr = float(video.get("throughputMbps_sum", 0.0))
    soft_max_video = sla.get("video_soft_max_throughput_mbps")
    if soft_max_video is not None and video_thr > soft_max_video:
        flags[0] = True

    generic_thr = float(generic.get("throughputMbps_sum", 0.0))
    soft_max_generic = sla.get("generic_soft_max_throughput_mbps")
    if soft_max_generic is not None and generic_thr > soft_max_generic:
        flags[2] = True

    return flags


def compute_greenran_reward(
    metrics: Dict[int, Dict[str, Any]],
    scenario: str,
    action_info: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    step_count: int = 0,
    kpi_history: Optional[List[Dict[int, Dict[str, Any]]]] = None,
) -> RewardResult:
    """
    Compute the SLA-aware reward for GreenRAN.

    Structure:
        - h_1: VIDEO_EMBB throughput / max_cap  (saturado em 1.0)
        - h_2: exp(-max_sensor_buffer / norm)    (latência/congestão proxy)
        - h_3: GENERIC_EMBB throughput / max_cap (saturado em 1.0)
        - Base: alpha*h_1 + beta*h_2 + gamma*h_3
        - Penalidade PLR: -lambda_plr * mean(plr_i / 100)
        - Terminal: outage por N passos consecutivos ou soft violation
    """
    if config is None:
        config = {}

    sla = SLA_BY_SCENARIO.get(scenario, SLA_BY_SCENARIO["greenran_normal"])
    warmup_steps = int(config.get("warmup_steps", 5))
    consecutive_outage_steps = int(config.get("consecutive_outage_steps", 5))

    alpha = config.get("alpha", ALPHA)
    beta = config.get("beta", BETA)
    gamma_val = config.get("gamma", GAMMA)
    lambda_plr = config.get("lambda_plr", 0.5)
    buffer_norm = config.get("buffer_norm_bytes", DEFAULT_BUFFER_NORM_BYTES)
    max_thr_cap = config.get("max_thr_mbps", DEFAULT_MAX_THR_MBPS)

    result = RewardResult()
    result.outage_flags = {sid: False for sid in range(get_num_slices())}
    result.soft_flags = {sid: False for sid in range(get_num_slices())}

    video_metrics = metrics.get(0, {})
    sensor_metrics = metrics.get(1, {})
    generic_metrics = metrics.get(2, {})

    # ---- h_1: VIDEO_EMBB throughput term ----
    video_thr = float(video_metrics.get("throughputMbps_sum", 0.0))
    video_ue_count = float(video_metrics.get("ue_count", 1))
    avg_video_thr = video_thr / max(video_ue_count, 1.0)
    h_1 = min(avg_video_thr / max_thr_cap, 1.0) if max_thr_cap > 0 else 0.0

    # ---- h_2: SENSOR_MMTC buffer/latency proxy ----
    sensor_max_buffer = float(sensor_metrics.get("bufferBytes_max", 0.0))
    normalized_buffer = sensor_max_buffer / buffer_norm if buffer_norm > 0 else sensor_max_buffer
    h_2 = math.exp(-normalized_buffer)

    # ---- h_3: GENERIC_EMBB throughput term ----
    generic_thr = float(generic_metrics.get("throughputMbps_sum", 0.0))
    generic_ue_count = float(generic_metrics.get("ue_count", 1))
    avg_generic_thr = generic_thr / max(generic_ue_count, 1.0)
    h_3 = min(avg_generic_thr / max_thr_cap, 1.0) if max_thr_cap > 0 else 0.0

    # ---- Base optimization reward ----
    opt_reward = alpha * h_1 + beta * h_2 + gamma_val * h_3

    # ---- PLR penalty (PDR proxy) ----
    plr_penalty = 0.0
    for sid in range(get_num_slices()):
        m = metrics.get(sid, {})
        plr = float(m.get("plr_mean", 0.0))
        plr_penalty += plr / 100.0
    plr_penalty = lambda_plr * (plr_penalty / max(get_num_slices(), 1))

    base_reward = opt_reward - plr_penalty

    # ---- Terminal conditions ----
    in_warmup = step_count < warmup_steps

    current_outage_conditions = _evaluate_outage_conditions(metrics, sla, config)
    current_soft_conditions = _evaluate_soft_conditions(metrics, sla)

    # Consecutive-period confirmation for outage
    history = kpi_history if kpi_history is not None else []
    for sid in range(get_num_slices()):
        if current_outage_conditions[sid]:
            streak = 1
            for past_metrics in reversed(history):
                past_conditions = _evaluate_outage_conditions(past_metrics, sla, config)
                if past_conditions[sid]:
                    streak += 1
                else:
                    break
            if streak >= consecutive_outage_steps and not in_warmup:
                result.outage_flags[sid] = True

    if not in_warmup:
        for sid in range(get_num_slices()):
            if current_soft_conditions[sid]:
                result.soft_flags[sid] = True

    outage_slices = [sid for sid, flag in result.outage_flags.items() if flag]
    soft_slices = [sid for sid, flag in result.soft_flags.items() if flag]

    if outage_slices:
        weights_map = {0: alpha, 1: beta, 2: gamma_val}
        result.reward = -sum(weights_map[sid] for sid in outage_slices)
        result.terminated = True
    elif soft_slices:
        result.reward = 0.0
        result.terminated = True
    else:
        result.reward = base_reward
        result.terminated = False

    result.optimization_terms = {
        "h_1_video": h_1,
        "h_2_sensor": h_2,
        "h_3_generic": h_3,
        "opt_reward": opt_reward,
        "plr_penalty": plr_penalty,
        "base_reward": base_reward,
    }

    result.debug_info = {
        "scenario": scenario,
        "video_throughput": video_thr,
        "sensor_bufferBytes_max": sensor_max_buffer,
        "generic_throughput": generic_thr,
        "video_plr": float(video_metrics.get("plr_mean", 0.0)),
        "sensor_plr": float(sensor_metrics.get("plr_mean", 0.0)),
        "generic_plr": float(generic_metrics.get("plr_mean", 0.0)),
        "outage_slices": outage_slices,
        "soft_slices": soft_slices,
        "action_info": action_info or {},
        "avg_video_thr_per_ue": avg_video_thr,
        "avg_generic_thr_per_ue": avg_generic_thr,
        "normalized_buffer": normalized_buffer,
    }

    return result
