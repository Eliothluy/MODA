"""Tests for rslaq_reward module (paper-faithful implementation)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from environments.rslaq_reward import (
    compute_rslaq_reward,
    get_scheduler_cost,
    ALPHA,
    BETA,
    GAMMA,
    EPSILON,
)


def _good_metrics():
    """Metrics where all slices meet SLA targets."""
    return {
        0: {"throughputMbps_sum": 12.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "bufferBytes_max": 500.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 5.0, "dLostPackets_sum": 50},
    }


def test_all_slices_meet_sla():
    """Test positive reward when all slices meet SLA."""
    result = compute_rslaq_reward(_good_metrics(), scenario="normal")
    assert result.reward > 0
    assert not result.terminated
    assert not any(result.outage_flags.values())
    assert not any(result.soft_flags.values())


def test_embb_outage_below_min():
    """Test outage when eMBB below minimum throughput (Equation 12)."""
    metrics = _good_metrics()
    metrics[0]["throughputMbps_sum"] = 5.0  # below 10 Mbps min
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.outage_flags[0] is True
    assert result.terminated
    assert result.reward == -ALPHA


def test_urllc_uses_buffer_max_not_plr():
    """Test that URLLC uses bufferBytes_max, not PLR (Equation 17)."""
    metrics = _good_metrics()
    # Add plr_mean — should be ignored
    metrics[1]["plr_mean"] = 999.0
    # Set a small bufferBytes_max
    metrics[1]["bufferBytes_max"] = 100.0
    result = compute_rslaq_reward(metrics, scenario="normal")
    # h_2 should be 1/(100 + epsilon), not based on plr
    expected_h2 = 1.0 / (100.0 + EPSILON)
    assert abs(result.optimization_terms["h_2_urllc"] - expected_h2) < 1e-9
    assert not result.outage_flags[1]


def test_urllc_outage_buffer_exceeds_threshold():
    """Test URLLC outage when bufferBytes_max exceeds threshold (Equation 17)."""
    metrics = _good_metrics()
    metrics[1]["bufferBytes_max"] = 15000.0  # > 10000.0 threshold
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.outage_flags[1] is True
    assert result.terminated
    assert result.reward == -BETA


def test_urlcc_h2_inverse_formula():
    """Test that h_2 = 1 / (bufferBytes_max + epsilon) (Equation 17)."""
    metrics = _good_metrics()
    metrics[1]["bufferBytes_max"] = 2500.0
    result = compute_rslaq_reward(metrics, scenario="normal")
    expected = 1.0 / (2500.0 + EPSILON)
    assert abs(result.optimization_terms["h_2_urllc"] - expected) < 1e-9


def test_embb_h1_normalized_capped():
    """Test h_1 = min(throughput / target, 1.0) (Equation 16)."""
    metrics = _good_metrics()
    # normal scenario: target = 15.0
    metrics[0]["throughputMbps_sum"] = 12.0
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert abs(result.optimization_terms["h_1_embb"] - (12.0 / 15.0)) < 1e-9

    # At target: should be exactly 1.0
    metrics[0]["throughputMbps_sum"] = 15.0
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.optimization_terms["h_1_embb"] == 1.0

    # Above target: capped at 1.0, no violation (exceeding target is good)
    metrics[0]["throughputMbps_sum"] = 20.0
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.optimization_terms["h_1_embb"] == 1.0
    assert not result.soft_flags[0]
    assert not result.outage_flags[0]


def test_mtc_h3_normalized_capped():
    """Test h_3 = min(throughput / target, 1.0) (Equation 18)."""
    metrics = _good_metrics()
    # normal scenario: mtc_target = 10.0
    metrics[2]["throughputMbps_sum"] = 5.0
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert abs(result.optimization_terms["h_3_mtc"] - 0.5) < 1e-9

    # At target
    metrics[2]["throughputMbps_sum"] = 10.0
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.optimization_terms["h_3_mtc"] == 1.0


def test_mtc_outage_tdp():
    """Test MTC outage when TDP >= max_tdp (Equation 18)."""
    metrics = _good_metrics()
    metrics[2]["dLostPackets_sum"] = 1000.0  # >= max_tdp (1000)
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.outage_flags[2] is True
    assert result.terminated
    assert result.reward == -GAMMA


def test_mtc_no_outage_tdp_below_max():
    """Test MTC no outage when TDP < max_tdp."""
    metrics = _good_metrics()
    metrics[2]["dLostPackets_sum"] = 500.0  # < 1000 max
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert not result.outage_flags[2]


def test_embb_above_target_no_violation():
    """Test that eMBB exceeding target does NOT trigger soft violation."""
    metrics = _good_metrics()
    metrics[0]["throughputMbps_sum"] = 30.0  # above soft_max (15.0 for normal)
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert not result.soft_flags[0]
    assert not result.outage_flags[0]
    assert not result.terminated
    assert result.reward > 0


def test_outage_reward_negative_weighted_sum():
    """Test outage reward = -sum(phi_j * omega_j) (Equation 12)."""
    metrics = _good_metrics()
    # Trigger outage on both eMBB and URLLC
    metrics[0]["throughputMbps_sum"] = 5.0   # below min → outage
    metrics[1]["bufferBytes_max"] = 15000.0   # above threshold → outage
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.outage_flags[0] is True
    assert result.outage_flags[1] is True
    expected_penalty = -(ALPHA + BETA)
    assert abs(result.reward - expected_penalty) < 1e-9
    assert result.terminated


def test_outage_all_three_slices():
    """Test outage on all three slices."""
    metrics = _good_metrics()
    metrics[0]["throughputMbps_sum"] = 5.0      # eMBB outage
    metrics[1]["bufferBytes_max"] = 15000.0      # URLLC outage
    metrics[2]["dLostPackets_sum"] = 1000.0      # MTC outage
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert all(result.outage_flags.values())
    expected_penalty = -(ALPHA + BETA + GAMMA)
    assert abs(result.reward - expected_penalty) < 1e-9
    assert result.terminated


def test_scheduler_cost():
    """Test scheduler cost function."""
    assert get_scheduler_cost(0) == 1.0  # RR
    assert get_scheduler_cost(1) == 2.0  # PF
    assert get_scheduler_cost(2) == 2.0  # BCQI
    assert get_scheduler_cost(99) == 1.0  # unknown defaults to 1.0


def test_scheduler_cost_adds_not_multiplies():
    """Test that scheduler cost is added, not multiplied (Equation 8)."""
    metrics = _good_metrics()

    result_no_scheduler = compute_rslaq_reward(
        metrics, scenario="normal", action_info=None
    )
    result_rr = compute_rslaq_reward(
        metrics, scenario="normal", action_info={"scheduler_id": 0}
    )
    result_pf = compute_rslaq_reward(
        metrics, scenario="normal", action_info={"scheduler_id": 1}
    )

    # RR cost=1.0, so 1/1.0 = 1.0 added
    diff_rr = result_rr.reward - result_no_scheduler.reward
    assert abs(diff_rr - 1.0) < 1e-9

    # PF cost=2.0, so 1/2.0 = 0.5 added
    diff_pf = result_pf.reward - result_no_scheduler.reward
    assert abs(diff_pf - 0.5) < 1e-9


def test_no_scheduler_no_cost_term():
    """Test that without scheduler, no cost term is added."""
    metrics = _good_metrics()

    result_no_action = compute_rslaq_reward(metrics, scenario="normal")
    result_no_scheduler = compute_rslaq_reward(
        metrics, scenario="normal", action_info={"scheduler_id": -1}
    )

    # Both should have the same reward (no scheduler cost added)
    assert abs(result_no_action.reward - result_no_scheduler.reward) < 1e-9

    # Verify it's just the weighted sum of h terms
    terms = result_no_action.optimization_terms
    expected = ALPHA * terms["h_1_embb"] + BETA * terms["h_2_urllc"] + GAMMA * terms["h_3_mtc"]
    assert abs(result_no_action.reward - expected) < 1e-9


def test_optimization_terms_keys():
    """Test optimization_terms has correct keys."""
    result = compute_rslaq_reward(_good_metrics(), scenario="normal")
    assert "h_1_embb" in result.optimization_terms
    assert "h_2_urllc" in result.optimization_terms
    assert "h_3_mtc" in result.optimization_terms
    assert "opt_reward" in result.optimization_terms


def test_reward_debug_info():
    """Test debug info in result."""
    result = compute_rslaq_reward(_good_metrics(), scenario="stressed")
    assert "scenario" in result.debug_info
    assert result.debug_info["scenario"] == "stressed"
    assert "urllc_bufferBytes_max" in result.debug_info
    assert "mtc_tdp" in result.debug_info


if __name__ == "__main__":
    test_all_slices_meet_sla()
    test_embb_outage_below_min()
    test_urllc_uses_buffer_max_not_plr()
    test_urllc_outage_buffer_exceeds_threshold()
    test_urlcc_h2_inverse_formula()
    test_embb_h1_normalized_capped()
    test_mtc_h3_normalized_capped()
    test_mtc_outage_tdp()
    test_mtc_no_outage_tdp_below_max()
    test_embb_above_target_no_violation()
    test_outage_reward_negative_weighted_sum()
    test_outage_all_three_slices()
    test_scheduler_cost()
    test_scheduler_cost_adds_not_multiplies()
    test_no_scheduler_no_cost_term()
    test_optimization_terms_keys()
    test_reward_debug_info()
    print("All reward tests passed.")
