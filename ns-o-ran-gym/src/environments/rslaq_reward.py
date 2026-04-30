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
import warnings
import numpy as np

from .rslaq_slice_ids import get_num_slices, slice_name

# Default importance weights for the reward components (Paper weights)
ALPHA = 0.3333  # eMBB
BETA = 0.4000   # URLLC
GAMMA = 0.2667  # MTC


SLA_BY_SCENARIO: Dict[str, Dict[str, Any]] = {
    "low_traffic": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,  # Legacy (used only if mtc_is_no_policy=False)
        "mtc_target_throughput": 5.0,  # Target for No-Policy mode (Mbps)
    },
    "normal": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 10.0,
    },
    "congestion": {
        "embb_min_throughput_mbps": 10.0,
        "embb_soft_max_throughput_mbps": 15.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 20.0,
    },
    "stressed": {
        "embb_min_throughput_mbps": 20.0,
        "embb_soft_max_throughput_mbps": 25.0,
        "urllc_max_bfs_pct": 3.0,
        "mtc_max_tdp": 1000.0,
        "mtc_target_throughput": 20.0,
    },
    "insufficient_resources": {
        "embb_min_throughput_mbps": 20.0,
        "embb_soft_max_throughput_mbps": 25.0,
        "urllc_max_bfs_pct": 3.0,
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
    Returns the cost of the scheduler (inverse of the benefit).
    Values from the paper:
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
) -> RewardResult:
    """
    Compute the SLA-aware reward for RSLAQ.

    Args:
        metrics: Aggregated metrics per slice (keys 0, 1, 2) and optionally cell (3).
                 Each slice dict should contain at least:
                 - throughputMbps_sum (float)
                 - plr_mean (float)   [used as bfs proxy if use_real_bfs=False]
                 - bufferBytes_mean (float) [used as real bfs if use_real_bfs=True]
                 - dLostPackets_sum (float) [used as tdp proxy]
                 - resourceSharePct_mean (float)
        scenario: Name of the scenario (must be a key in SLA_BY_SCENARIO).
        action_info: Optional dict with keys like 'prb_pct', 'scheduler_id'.
        config: Optional override dict with keys:
            - alpha, beta, gamma: component weights (default paper weights)
            - terminal_outage: bool (default False)
            - outage_penalty: float (default -sum(weights of violated slices))
            - soft_penalty: float (default 0.0)
            - mtc_is_no_policy: bool (default True) - MTC is No-Policy (no outage)
            - use_real_bfs: bool (default False) - Use real buffer for URLLC
            - max_buffer_bytes: float (default 100000.0) - Max buffer for normalization
            - suppress_proxy_warning: bool (default False) - Suppress URLLC proxy warning

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
    mtc_is_no_policy = config.get("mtc_is_no_policy", True)
    use_real_bfs = config.get("use_real_bfs", False)
    max_buffer_bytes = config.get("max_buffer_bytes", 100000.0)
    suppress_proxy_warning = config.get("suppress_proxy_warning", False)

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
    elif embb_thr > soft_max_thr:
        # Soft violation: throughput acima do máximo soft gera reward = 0
        r_embb = 0.0
        result.soft_flags[0] = True
    else:
        # Dentro do range [min_thr, soft_max_thr]
        r_embb = min(embb_thr / soft_max_thr, 1.0)

    # ---- R_URLLC ----
    if use_real_bfs:
        # Usar buffer real (em bytes, normalizado)
        urllc_bfs_bytes = float(urllc_metrics.get("bufferBytes_mean", 0.0))
        # Normalizar para 0-1 baseado no threshold
        urllc_bfs_normalized = urllc_bfs_bytes / max_buffer_bytes

        if urllc_bfs_normalized <= 0.03:  # 3% threshold
            r_urllc = 1.0
        else:
            # Exponential decay: quanto maior o buffer, menor a recompensa
            r_urllc = float(np.exp(-(urllc_bfs_normalized - 0.03) * 5.0))
            # Outage se buffer for muito grande
            if urllc_bfs_normalized > 0.10:  # 10% threshold de outage
                result.outage_flags[1] = True
    else:
        # Modo legado: usa PLR como proxy (com WARNING)
        if not suppress_proxy_warning:
            warnings.warn(
                "URLLC using PLR as proxy for buffer status. "
                "This is NOT faithful to the paper. Set use_real_bfs=True for paper mode."
            )
        max_bfs = sla["urllc_max_bfs_pct"]
        if urllc_bfs <= max_bfs:
            r_urllc = 1.0
        else:
            # Exponential decay beyond SLA
            r_urllc = float(np.exp(-(urllc_bfs - max_bfs) * 0.5))
            if r_urllc < 0.5:
                result.outage_flags[1] = True

    # ---- R_MTC (No-Policy slice) ----
    if mtc_is_no_policy:
        # MTC is No-Policy: no outage, only optimization
        mtc_target = sla.get("mtc_target_throughput", 10.0)
        r_mtc = float(mtc_metrics.get("throughputMbps_sum", 0.0)) / mtc_target
        r_mtc = min(r_mtc, 1.0)  # Cap at 1.0
        # Do NOT set outage_flags[2] = True
    else:
        # Legacy mode: MTC pode gerar outage
        max_tdp = sla.get("mtc_max_tdp", 1000.0)
        if mtc_tdp >= max_tdp:
            r_mtc = 0.0
            result.outage_flags[2] = True
        else:
            r_mtc = 1.0 - (mtc_tdp / max_tdp)

    # Base optimization reward
    opt_reward = alpha * r_embb + beta * r_urllc + gamma_val * r_mtc

    # Apply scheduler cost according to paper: RR=1, PF=2, BCQI=2
    # The paper divides by cost: opt_reward * (1 / scheduler_cost)
    scheduler_id = action_info.get("scheduler_id", -1) if action_info else -1
    if scheduler_id >= 0:
        scheduler_cost_val = get_scheduler_cost(scheduler_id)
        opt_reward *= (1.0 / scheduler_cost_val)  # Apply cost multiplier

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
