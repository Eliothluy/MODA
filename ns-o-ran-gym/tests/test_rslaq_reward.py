"""Tests for rslaq_reward module."""

import sys
import os
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from environments.rslaq_reward import compute_rslaq_reward, get_scheduler_cost


def test_reward_normal_all_good():
    """Test positive reward when all slices meet SLA."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.reward > 0
    assert not result.terminated
    assert not any(result.outage_flags.values())


def test_reward_embb_outage():
    """Test negative reward when eMBB below minimum."""
    metrics = {
        0: {"throughputMbps_sum": 5.0, "plr_mean": 1.0, "dLostPackets_sum": 100},  # below 10 Mbps
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="normal", config={"terminal_outage": True})
    assert result.reward < 0
    assert result.terminated
    assert result.outage_flags[0] is True


def test_reward_urllc_outage_proxy():
    """Test URLLC outage using PLR proxy."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 10.0, "dLostPackets_sum": 0},  # high plr
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="normal", config={"use_real_bfs": False})
    # high plr leads to low r_urllc, but may not trigger outage unless < 0.5
    assert result.reward <= 1.0


def test_reward_urllc_outage_real_bfs():
    """Test URLLC outage using real buffer."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "bufferBytes_mean": 20000.0, "dLostPackets_sum": 0},  # > 10%
        2: {"throughputMbps_sum": 0.0, "bufferBytes_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(
        metrics,
        scenario="normal",
        config={"use_real_bfs": True, "max_buffer_bytes": 100000.0}
    )
    # 20000 / 100000 = 0.2 > 0.10, should trigger outage
    assert result.outage_flags[1] is True


def test_reward_mtc_no_policy_no_outage():
    """Test that MTC No-Policy mode doesn't generate outage."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 9999},  # many lost packets
    }
    result = compute_rslaq_reward(metrics, scenario="normal", config={"mtc_is_no_policy": True})
    # MTC should NOT be in outage in No-Policy mode
    assert not result.outage_flags.get(2, True)


def test_reward_mtc_legacy_outage():
    """Test that MTC legacy mode can generate outage."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 2000},  # above max
    }
    result = compute_rslaq_reward(metrics, scenario="normal", config={"mtc_is_no_policy": False})
    # MTC should be in outage in legacy mode
    assert result.outage_flags[2] is True
    assert result.reward < 0


def test_reward_soft_violation():
    """Test eMBB soft violation generates reward 0."""
    metrics = {
        0: {"throughputMbps_sum": 30.0, "plr_mean": 1.0, "dLostPackets_sum": 100},  # above soft max
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="normal", config={"soft_penalty": 0.0})
    assert result.soft_flags[0] is True
    # Soft violation should generate reward = soft_penalty (0.0)
    assert result.reward == 0.0


def test_reward_debug_info():
    """Test debug info in result."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="stressed")
    assert "scenario" in result.debug_info
    assert result.debug_info["scenario"] == "stressed"


def test_scheduler_cost():
    """Test scheduler cost function."""
    assert get_scheduler_cost(0) == 1.0  # RR
    assert get_scheduler_cost(1) == 2.0  # PF
    assert get_scheduler_cost(2) == 2.0  # BCQI
    assert get_scheduler_cost(99) == 1.0  # unknown defaults to 1.0


def test_reward_with_scheduler_cost():
    """Test reward includes scheduler cost."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    # RR (cost 1.0)
    result_rr = compute_rslaq_reward(
        metrics, scenario="normal", action_info={"scheduler_id": 0}
    )
    # PF (cost 2.0) - should be half the reward
    result_pf = compute_rslaq_reward(
        metrics, scenario="normal", action_info={"scheduler_id": 1}
    )
    # RR reward should be higher than PF reward (since PF has higher cost)
    assert result_rr.reward > result_pf.reward


def test_proxy_warning():
    """Test that proxy warning is raised when using PLR as buffer."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        compute_rslaq_reward(metrics, scenario="normal", config={"use_real_bfs": False})
        # Should have warning about proxy
        assert len(w) == 1
        assert "proxy" in str(w[0].message).lower()

    # No warning when suppressed
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        compute_rslaq_reward(
            metrics, scenario="normal",
            config={"use_real_bfs": False, "suppress_proxy_warning": True}
        )
        assert len(w) == 0

    # No warning when using real buffer
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        compute_rslaq_reward(
            metrics, scenario="normal",
            config={"use_real_bfs": True, "suppress_proxy_warning": False}
        )
        assert len(w) == 0


def test_optimization_terms():
    """Test optimization_terms are correctly computed."""
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert "r_embb" in result.optimization_terms
    assert "r_urllc" in result.optimization_terms
    assert "r_mtc" in result.optimization_terms
    assert "opt_reward" in result.optimization_terms
    # All components should be between 0 and 1
    assert 0 <= result.optimization_terms["r_embb"] <= 1
    assert 0 <= result.optimization_terms["r_urllc"] <= 1
    assert 0 <= result.optimization_terms["r_mtc"] <= 1


if __name__ == "__main__":
    test_reward_normal_all_good()
    test_reward_embb_outage()
    test_reward_urllc_outage_proxy()
    test_reward_urllc_outage_real_bfs()
    test_reward_mtc_no_policy_no_outage()
    test_reward_mtc_legacy_outage()
    test_reward_soft_violation()
    test_reward_debug_info()
    test_scheduler_cost()
    test_reward_with_scheduler_cost()
    test_proxy_warning()
    test_optimization_terms()
    print("All reward tests passed.")
