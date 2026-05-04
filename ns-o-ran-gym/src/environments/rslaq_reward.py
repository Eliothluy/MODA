"""
RSLAQ SLA-aware Reward Function.

Computes the reward based on per-slice KPIs and scenario-specific SLA targets,
strictly following the equations published in the RSLAQ paper (IEEE TMC 2026):

- Equations 16: h_1 = (1/|Λ1|) * Σ thr(UE) normalized by max achievable rate (eMBB)
- Equation 17: h_2 = exp(-max_UE bfs(UE) / norm) (URLLC)
- Equation 18: h_3 = (1/|Λ3|) * Σ thr(UE) normalized by max achievable rate (MTC)
- Equation 8:  ropt = alpha*h_1 + beta*h_2 + gamma*h_3 + 1/scheduler_cost
- Equation 12: Terminal conditions (soft and outage SLA violations)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .rslaq_slice_ids import get_num_slices, slice_name

# Default importance weights (omega_j in the paper, Eq. 8)
# Priorities [2, 1, 3] for [eMBB, URLLC, MTC] → weights [0.33, 0.40, 0.27]
ALPHA = 0.3333  # omega_0: eMBB
BETA = 0.4000   # omega_1: URLLC
GAMMA = 0.2667  # omega_2: MTC

# Default max achievable rate per UE for throughput normalization (Mbps)
# Paper: "all elements must be normalized (e.g., we use maximum
# achievable rates for the throughput normalization)."
DEFAULT_MAX_ACHIEVABLE_THR_MBPS = 150.0

# SLA targets per scenario (matching Table V in the paper)
SLA_BY_SCENARIO: Dict[str, Dict[str, Any]] = {
    "low_traffic": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 10.0,
        # MTC is No-Policy in all paper scenarios (Table V)
        "mtc_no_policy": True,
    },
    "normal": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 10.0,
        "mtc_no_policy": True,
    },
    "congestion": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 20.0,
        "mtc_no_policy": True,
    },
    "stressed": {
        "embb_min_throughput_mbps": 20.0,
        "embb_soft_max_throughput_mbps": 25.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 20.0,
        "mtc_no_policy": True,
    },
    "insufficient_resources": {
        "embb_min_throughput_mbps": 20.0,
        "embb_soft_max_throughput_mbps": 25.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 20.0,
        "mtc_no_policy": True,
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


def get_scheduler_cost(scheduler_id: int) -> float:
    """
    Returns the cost of the scheduler (Eq. 9 in the paper).

    - RR (Round Robin): cost 1.0
    - PF (Proportional Fair): cost 2.0
    - BCQI (Best CQI): cost 2.0
    """
    mapping = {0: 1.0, 1: 2.0, 2: 2.0}
    return mapping.get(scheduler_id, 1.0)


def _evaluate_outage_conditions(
    metrics: Dict[int, Dict[str, Any]],
    sla: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[int, bool]:
    """
    Evaluate instantaneous outage conditions for each slice (paper Eq. 13-14).

    eMBB: P(thr per slice < k_11) where k_11 = min throughput
    URLLC: P(bfs per UE > k_12) where k_12 = max buffer occupancy
    MTC: No outage condition (no-policy slice in paper Table V)

    Returns a dict {slice_id: bool} where True means the slice meets
    the instantaneous outage condition in this step.
    """
    flags: Dict[int, bool] = {0: False, 1: False, 2: False}

    embb = metrics.get(0, {})
    urllc = metrics.get(1, {})

    # eMBB outage (Eq. 13): throughput below minimum AND demand exists
    embb_thr = float(embb.get("throughputMbps_sum", 0.0))
    embb_tx = float(embb.get("dTxBytes_sum", 0.0))
    min_tx = float(config.get("min_tx_bytes_for_outage", 1.0))
    if embb_thr < sla["embb_min_throughput_mbps"] and embb_tx >= min_tx:
        flags[0] = True

    # URLLC outage (Eq. 14): buffer exceeds threshold
    urllc_max_bfs = float(urllc.get("bufferBytes_max", 0.0))
    if urllc_max_bfs > sla["urllc_outage_bfs_bytes"]:
        flags[1] = True

    # MTC is No-Policy in paper Table V → no outage condition
    # (slice 2 is always False)

    return flags


def _evaluate_soft_conditions(
    metrics: Dict[int, Dict[str, Any]],
    sla: Dict[str, Any],
) -> Dict[int, bool]:
    """
    Evaluate instantaneous soft SLA conditions (paper Eq. 15).

    eMBB: P(max thr per slice > k_21) where k_21 = soft max throughput
    URLLC: No soft condition defined in paper for URLLC
    MTC: No-Policy → no soft condition
    """
    flags: Dict[int, bool] = {0: False, 1: False, 2: False}

    embb = metrics.get(0, {})

    # eMBB soft (Eq. 15): throughput exceeds soft max → wasteful overallocation
    embb_thr = float(embb.get("throughputMbps_sum", 0.0))
    soft_max = sla.get("embb_soft_max_throughput_mbps")
    if soft_max is not None and embb_thr > soft_max:
        flags[0] = True

    return flags


def compute_rslaq_reward(
    metrics: Dict[int, Dict[str, Any]],
    scenario: str,
    action_info: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    step_count: int = 0,
    kpi_history: Optional[List[Dict[int, Dict[str, Any]]]] = None,
) -> RewardResult:
    """
    Compute the SLA-aware reward for RSLAQ following the paper.

    Equations implemented:
        - Eq. 16: h_1 = per-UE avg throughput / max achievable rate (eMBB)
        - Eq. 17: h_2 = exp(-max_bfs / bfs_norm) (URLLC)
        - Eq. 18: h_3 = per-UE avg throughput / max achievable rate (MTC)
        - Eq. 8:  opt_reward = (alpha*h_1 + beta*h_2 + gamma*h_3) + (1/scheduler_cost)
        - Eq. 12: Terminal conditions (soft and outage)

    Paper says: "all elements must be normalized (e.g., we use maximum
    achievable rates for the throughput normalization)."
    "h_2 = exp(-max_UE bfs(UE))" with bfs normalized.

    Args:
        step_count: Current step within the episode. Terminal conditions are
            suppressed during the warmup period.
    """
    if config is None:
        config = {}

    sla = SLA_BY_SCENARIO.get(scenario, SLA_BY_SCENARIO["normal"])
    warmup_steps = int(config.get("warmup_steps", 5))
    consecutive_outage_steps = int(config.get("consecutive_outage_steps", 5))

    alpha = config.get("alpha", ALPHA)
    beta = config.get("beta", BETA)
    gamma_val = config.get("gamma", GAMMA)

    result = RewardResult()
    result.outage_flags = {sid: False for sid in range(get_num_slices())}
    result.soft_flags = {sid: False for sid in range(get_num_slices())}

    # Extract per-slice metrics (defaults to 0 if missing)
    embb_metrics = metrics.get(0, {})
    urllc_metrics = metrics.get(1, {})
    mtc_metrics = metrics.get(2, {})

    # ---- Normalization parameters ----
    max_achievable = float(config.get(
        "max_achievable_thr_mbps", DEFAULT_MAX_ACHIEVABLE_THR_MBPS
    ))
    bf_norm = float(config.get(
        "bfs_normalization_bytes", sla["urllc_outage_bfs_bytes"]
    ))

    # ---- h_1: eMBB optimization term (Eq. 16) ----
    # Paper: h_1 = (1/|Λ1|) * Σ thr(UE) normalized by max achievable rate
    embb_thr = float(embb_metrics.get("throughputMbps_sum", 0.0))
    embb_ue_count = float(embb_metrics.get("ue_count", 1))
    avg_embb_thr = embb_thr / max(embb_ue_count, 1.0)
    h_1 = min(avg_embb_thr / max_achievable, 1.0) if max_achievable > 0 else 0.0

    # ---- h_2: URLLC optimization term (Eq. 17) ----
    # Paper: h_2 = exp(-max_UE bfs(UE) / normalization)
    urllc_max_bfs = float(urllc_metrics.get("bufferBytes_max", 0.0))
    normalized_bfs = urllc_max_bfs / bf_norm if bf_norm > 0 else urllc_max_bfs
    h_2 = math.exp(-normalized_bfs)

    # ---- h_3: MTC optimization term (Eq. 18) ----
    # Paper: h_3 = (1/|Λ3|) * Σ thr(UE) normalized by max achievable rate
    mtc_thr = float(mtc_metrics.get("throughputMbps_sum", 0.0))
    mtc_ue_count = float(mtc_metrics.get("ue_count", 1))
    avg_mtc_thr = mtc_thr / max(mtc_ue_count, 1.0)
    h_3 = min(avg_mtc_thr / max_achievable, 1.0) if max_achievable > 0 else 0.0

    # ---- Base optimization reward (Eq. 8) ----
    # ropt = alpha*h_1 + beta*h_2 + gamma*h_3 + 1/cost(sch)
    opt_reward = alpha * h_1 + beta * h_2 + gamma_val * h_3

    scheduler_id = action_info.get("scheduler_id", -1) if action_info else -1
    if scheduler_id >= 0:
        scheduler_cost_val = get_scheduler_cost(scheduler_id)
        opt_reward += (1.0 / scheduler_cost_val)

    # ---- Terminal conditions (Eq. 12) ----
    # Outage: -Σ(φ_j * ω_j), terminate
    # Soft: 0 reward, terminate
    # Otherwise: ropt
    #
    # Paper uses probabilistic vrsla_ij per timestep (Eq. 10-11).
    # Since we have 1 sample per timestep (10ms) and reliability=100%,
    # the instantaneous check is equivalent. Consecutive-period
    # confirmation filters simulator jitter (HARQ), which is a practical
    # addition beyond the paper.

    in_warmup = step_count < warmup_steps

    # Evaluate instantaneous conditions
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

    # Soft conditions are instantaneous (no consecutive confirmation needed,
    # as over-allocation is deterministic, not jitter-prone)
    if not in_warmup:
        for sid in range(get_num_slices()):
            if current_soft_conditions[sid]:
                result.soft_flags[sid] = True

    outage_slices = [sid for sid, flag in result.outage_flags.items() if flag]
    soft_slices = [sid for sid, flag in result.soft_flags.items() if flag]

    if outage_slices:
        # Eq. 12: r = -Σ(φ_j * ω_j), terminal
        weights_map = {0: alpha, 1: beta, 2: gamma_val}
        result.reward = -sum(weights_map[sid] for sid in outage_slices)
        result.terminated = True
    elif soft_slices:
        # Eq. 12: r = 0, terminal (soft SLA violation)
        result.reward = 0.0
        result.terminated = True
    else:
        result.reward = opt_reward
        result.terminated = False

    result.optimization_terms = {
        "h_1_embb": h_1,
        "h_2_urllc": h_2,
        "h_3_mtc": h_3,
        "opt_reward": opt_reward,
    }

    result.debug_info = {
        "scenario": scenario,
        "embb_throughput": embb_thr,
        "urllc_bufferBytes_max": urllc_max_bfs,
        "mtc_throughput": mtc_thr,
        "mtc_tdp": float(mtc_metrics.get("dLostPackets_sum", 0.0)),
        "outage_slices": outage_slices,
        "soft_slices": soft_slices,
        "action_info": action_info or {},
        "avg_embb_thr_per_ue": avg_embb_thr,
        "avg_mtc_thr_per_ue": avg_mtc_thr,
        "normalized_bfs": normalized_bfs,
    }

    return result
