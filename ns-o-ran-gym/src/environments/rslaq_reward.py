"""
RSLAQ SLA-aware Reward Function.

Computes the reward based on per-slice KPIs and scenario-specific SLA targets.

Design decisions:
- Uses configurable SLA targets per scenario.
- Returns a dataclass with detailed information for debugging and logging.
- Outage (critical SLA violation) can optionally terminate the episode.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import numpy as np

from .rslaq_slice_ids import get_num_slices, slice_name

# Default importance weights for the reward components
ALPHA = 1.0 / 3.0  # eMBB
BETA = 1.0 / 3.0   # URLLC
GAMMA = 1.0 / 3.0  # MTC


SLA_BY_SCENARIO: Dict[str, Dict[str, Any]] = {
    "low_traffic": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,
    },
    "normal": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,
    },
    "congestion": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,
    },
    "stressed": {
        "embb_min_throughput_mbps": 20.0,
        "embb_soft_max_throughput_mbps": 25.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,
    },
    "insufficient_resources": {
        "embb_min_throughput_mbps": 20.0,
        "embb_soft_max_throughput_mbps": 25.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,
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


def compute_rslaq_reward(
    metrics: Dict[int, Dict[str, Any]],
    scenario: str,
    action_info: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> RewardResult:
    """
    Compute the SLA-aware reward for RSLAQ.

    Args:
        metrics: Aggregated metrics per slice (keys 0, 1, 2) and optionally cell (3).
                 Each slice dict should contain at least:
                 - throughputMbps_sum (float)
                 - plr_mean (float)   [used as bfs proxy]
                 - dLostPackets_sum (float) [used as tdp proxy]
                 - resourceSharePct_mean (float)
        scenario: Name of the scenario (must be a key in SLA_BY_SCENARIO).
        action_info: Optional dict with keys like 'prb_pct', 'scheduler_id'.
        config: Optional override dict with keys:
            - alpha, beta, gamma: component weights (default 1/3 each)
            - terminal_outage: bool (default False)
            - outage_penalty: float (default -sum(weights of violated slices))
            - soft_penalty: float (default 0.0)
            - scheduler_cost: float (default 1.0 for resource-only)

    Returns:
        RewardResult with detailed breakdown.
    """
    if config is None:
        config = {}

    sla = SLA_BY_SCENARIO.get(scenario, SLA_BY_SCENARIO["normal"])

    alpha = config.get("alpha", ALPHA)
    beta = config.get("beta", BETA)
    gamma_val = config.get("gamma", GAMMA)
    terminal_outage = config.get("terminal_outage", False)
    outage_penalty = config.get("outage_penalty", None)
    soft_penalty = config.get("soft_penalty", 0.0)
    scheduler_cost = config.get("scheduler_cost", 1.0)

    result = RewardResult()
    result.outage_flags = {sid: False for sid in range(get_num_slices())}
    result.soft_flags = {sid: False for sid in range(get_num_slices())}

    # Extract per-slice metrics (defaults to 0 if missing)
    embb_metrics = metrics.get(0, {})
    urllc_metrics = metrics.get(1, {})
    mtc_metrics = metrics.get(2, {})

    embb_thr = float(embb_metrics.get("throughputMbps_sum", 0.0))
    urllc_bfs = float(urllc_metrics.get("plr_mean", 0.0))   # proxy
    mtc_tdp = float(mtc_metrics.get("dLostPackets_sum", 0.0))  # proxy

    # ---- R_eMBB ----
    min_thr = sla["embb_min_throughput_mbps"]
    soft_max_thr = sla["embb_soft_max_throughput_mbps"]

    if embb_thr < min_thr:
        r_embb = 0.0
        result.outage_flags[0] = True
    else:
        r_embb = min(embb_thr / soft_max_thr, 1.0)

    # Soft violation: throughput above soft max is not penalized further (already clipped)
    if embb_thr > soft_max_thr:
        result.soft_flags[0] = True

    # ---- R_URLLC ----
    max_bfs = sla["urllc_max_bfs_pct"]
    if urllc_bfs <= max_bfs:
        r_urllc = 1.0
    else:
        # Exponential decay beyond SLA
        r_urllc = float(np.exp(-(urllc_bfs - max_bfs) * 0.5))
        if r_urllc < 0.5:
            result.outage_flags[1] = True

    # ---- R_MTC ----
    max_tdp = sla["mtc_max_tdp"]
    if mtc_tdp >= max_tdp:
        r_mtc = 0.0
        result.outage_flags[2] = True
    else:
        r_mtc = 1.0 - (mtc_tdp / max_tdp)

    # Base optimization reward
    opt_reward = alpha * r_embb + beta * r_urllc + gamma_val * r_mtc

    # Apply scheduler cost (resource-only = 1.0, so no change)
    opt_reward *= scheduler_cost

    # Determine final reward
    outage_slices = [sid for sid, flag in result.outage_flags.items() if flag]
    soft_slices = [sid for sid, flag in result.soft_flags.items() if flag]

    if outage_slices:
        if outage_penalty is None:
            # Default: negative sum of weights of violated slices
            weights_map = {0: alpha, 1: beta, 2: gamma_val}
            penalty = -sum(weights_map[sid] for sid in outage_slices)
        else:
            penalty = float(outage_penalty)
        result.reward = penalty
        result.terminated = terminal_outage
    elif soft_slices:
        result.reward = soft_penalty
        result.terminated = False
    else:
        result.reward = opt_reward
        result.terminated = False

    result.optimization_terms = {
        "r_embb": r_embb,
        "r_urllc": r_urllc,
        "r_mtc": r_mtc,
        "opt_reward": opt_reward,
    }

    result.debug_info = {
        "scenario": scenario,
        "embb_throughput": embb_thr,
        "urllc_bfs_proxy": urllc_bfs,
        "mtc_tdp_proxy": mtc_tdp,
        "outage_slices": outage_slices,
        "soft_slices": soft_slices,
        "action_info": action_info or {},
    }

    return result
