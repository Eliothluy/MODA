"""
RSLAQ SLA-aware Reward Function.

Computes the reward based on per-slice KPIs and scenario-specific SLA targets,
strictly following the equations published in the RSLAQ paper:

- Equations 16, 17, 18: Optimization terms h_1 (eMBB), h_2 (URLLC), h_3 (MTC)
- Equation 8: Base reward with additive scheduler cost
- Equation 12: Terminal conditions (soft and outage SLA violations)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from .rslaq_slice_ids import get_num_slices, slice_name

# Default importance weights (omega_j in the paper)
ALPHA = 0.3333  # omega_0: eMBB
BETA = 0.4000   # omega_1: URLLC
GAMMA = 0.2667  # omega_2: MTC

# Epsilon for division-by-zero protection in Equation 17
EPSILON = 1e-6


SLA_BY_SCENARIO: Dict[str, Dict[str, Any]] = {
    "low_traffic": {
        "embb_min_throughput_mbps": 1.0,
        "embb_soft_max_throughput_mbps": 2.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 1.0,
    },
    "normal": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 10.0,
    },
    "congestion": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 20.0,
    },
    "stressed": {
        "embb_min_throughput_mbps": 20.0,
        "embb_soft_max_throughput_mbps": 25.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 20.0,
    },
    "insufficient_resources": {
        "embb_min_throughput_mbps": 20.0,
        "embb_soft_max_throughput_mbps": 25.0,
        "urllc_outage_bfs_bytes": 10000.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 20.0,
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
    Returns the cost of the scheduler.
    - RR (Round Robin): cost 1.0
    - PF (Proportional Fair): cost 2.0
    - BCQI (Best CQI): cost 2.0
    """
    mapping = {0: 1.0, 1: 2.0, 2: 2.0}  # RR, PF, BCQI
    return mapping.get(scheduler_id, 1.0)


def compute_rslaq_reward(
    metrics: Dict[int, Dict[str, Any]],
    scenario: str,
    action_info: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    step_count: int = 0,
) -> RewardResult:
    """
    Compute the SLA-aware reward for RSLAQ (paper-faithful implementation).

    Equations implemented:
        - Eq. 16: h_1 = normalized average throughput (eMBB)
        - Eq. 17: h_2 = 1 / (max_UE bfs(UE) + epsilon) (URLLC)
        - Eq. 18: h_3 = normalized throughput (MTC)
        - Eq. 8:  opt_reward = (alpha*h_1 + beta*h_2 + gamma*h_3) + (1/scheduler_cost)
        - Eq. 12: Terminal conditions (soft and outage)

    Args:
        step_count: Current step within the episode. Terminal conditions are
            suppressed during the warmup period to avoid false positives at
            simulation start.
    """
    if config is None:
        config = {}

    sla = SLA_BY_SCENARIO.get(scenario, SLA_BY_SCENARIO["normal"])
    warmup_steps = int(config.get("warmup_steps", 5))

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

    # ---- h_1: eMBB optimization term (Equation 16) ----
    embb_thr = float(embb_metrics.get("throughputMbps_sum", 0.0))
    embb_tx_bytes = float(embb_metrics.get("dTxBytes_sum", 0.0))
    target_thr = sla["embb_soft_max_throughput_mbps"]
    min_thr = sla["embb_min_throughput_mbps"]

    h_1 = min(embb_thr / target_thr, 1.0) if target_thr > 0 else 0.0

    # Only flag outage if there is actual demand (txBytes > 0) but throughput is insufficient.
    # If txBytes == 0, the slice has no traffic and outage is not meaningful.
    min_tx_bytes_for_outage = float(config.get("min_tx_bytes_for_outage", 1.0))
    if embb_thr < min_thr and embb_tx_bytes >= min_tx_bytes_for_outage:
        result.outage_flags[0] = True   # phi_0 = 1 (outage)

    # ---- h_2: URLLC optimization term (Equation 17) ----
    urllc_max_bfs = float(urllc_metrics.get("bufferBytes_max", 0.0))
    max_h2 = float(config.get("max_h2", 10.0))

    h_2 = 1.0 / (urllc_max_bfs + EPSILON)
    h_2 = min(h_2, max_h2)  # cap to avoid explosion when buffer is empty

    if urllc_max_bfs > sla["urllc_outage_bfs_bytes"]:
        result.outage_flags[1] = True   # phi_1 = 1 (outage)

    # ---- h_3: MTC optimization term (Equation 18) ----
    mtc_thr = float(mtc_metrics.get("throughputMbps_sum", 0.0))
    mtc_tdp = float(mtc_metrics.get("dLostPackets_sum", 0.0))
    mtc_target = sla["mtc_target_throughput"]
    mtc_max_tdp = sla["mtc_max_tdp"]

    h_3 = min(mtc_thr / mtc_target, 1.0) if mtc_target > 0 else 0.0

    if mtc_tdp >= mtc_max_tdp:
        result.outage_flags[2] = True   # phi_2 = 1 (outage)

    # ---- Base optimization reward (Equation 8) ----
    opt_reward = alpha * h_1 + beta * h_2 + gamma_val * h_3

    scheduler_id = action_info.get("scheduler_id", -1) if action_info else -1
    if scheduler_id >= 0:
        scheduler_cost_val = get_scheduler_cost(scheduler_id)
        opt_reward += (1.0 / scheduler_cost_val)

    # ---- Terminal conditions (Equation 12) ----
    # Suppress terminal conditions during warmup to avoid false positives
    # when FlowMonitor has not yet accumulated enough packets (especially
    # in low_traffic scenarios where inter-arrival time can exceed the
    # first few indication periods).
    in_warmup = step_count < warmup_steps

    outage_slices = [sid for sid, flag in result.outage_flags.items() if flag]
    soft_slices = [sid for sid, flag in result.soft_flags.items() if flag]

    if outage_slices and not in_warmup:
        weights_map = {0: alpha, 1: beta, 2: gamma_val}
        result.reward = -sum(weights_map[sid] for sid in outage_slices)
        result.terminated = True
    elif soft_slices and not in_warmup:
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
        "mtc_tdp": mtc_tdp,
        "outage_slices": outage_slices,
        "soft_slices": soft_slices,
        "action_info": action_info or {},
    }

    return result