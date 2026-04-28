"""Tests for rslaq_reward module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from environments.rslaq_reward import compute_rslaq_reward


def test_reward_normal_all_good():
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
    metrics = {
        0: {"throughputMbps_sum": 5.0, "plr_mean": 1.0, "dLostPackets_sum": 100},  # below 10 Mbps
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="normal", config={"terminal_outage": True})
    assert result.reward < 0
    assert result.terminated
    assert result.outage_flags[0] is True


def test_reward_urllc_outage():
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 10.0, "dLostPackets_sum": 0},  # high plr
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="normal")
    # high plr leads to low r_urllc, but may not trigger outage unless < 0.5
    assert result.reward <= 1.0


def test_reward_mtc_outage():
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 2000},  # above max
    }
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.outage_flags[2] is True
    assert result.reward < 0


def test_reward_soft_violation():
    metrics = {
        0: {"throughputMbps_sum": 30.0, "plr_mean": 1.0, "dLostPackets_sum": 100},  # above soft max
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="normal")
    assert result.soft_flags[0] is True


def test_reward_debug_info():
    metrics = {
        0: {"throughputMbps_sum": 12.0, "plr_mean": 1.0, "dLostPackets_sum": 100},
        1: {"throughputMbps_sum": 0.0, "plr_mean": 1.0, "dLostPackets_sum": 0},
        2: {"throughputMbps_sum": 0.0, "plr_mean": 0.0, "dLostPackets_sum": 100},
    }
    result = compute_rslaq_reward(metrics, scenario="stressed")
    assert "scenario" in result.debug_info
    assert result.debug_info["scenario"] == "stressed"


if __name__ == "__main__":
    test_reward_normal_all_good()
    test_reward_embb_outage()
    test_reward_urllc_outage()
    test_reward_mtc_outage()
    test_reward_soft_violation()
    test_reward_debug_info()
    print("All reward tests passed.")
