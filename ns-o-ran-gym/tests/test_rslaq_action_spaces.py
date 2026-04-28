"""Tests for rslaq_action_spaces module."""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from environments.rslaq_action_spaces import (
    build_discrete_action_table,
    continuous_action_to_prb,
    discrete_action_to_prb,
)


def test_discrete_table_size():
    table = build_discrete_action_table(step=0.1, include_scheduler=False)
    assert len(table) == 66, f"Expected 66 actions, got {len(table)}"


def test_discrete_table_sum():
    table = build_discrete_action_table(step=0.1, include_scheduler=False)
    for entry in table:
        p0, p1, p2 = entry
        assert abs(p0 + p1 + p2 - 1.0) < 1e-6, f"Action {entry} does not sum to 1.0"


def test_continuous_sums_to_100():
    for _ in range(10):
        raw = np.random.uniform(-1, 1, size=3)
        prb = continuous_action_to_prb(raw)
        assert abs(prb.sum() - 100.0) < 0.1, f"Sum {prb.sum()} != 100.0"
        assert prb.shape == (3,)


def test_discrete_prb_sums_to_100():
    table = build_discrete_action_table(step=0.1, include_scheduler=False)
    for idx in range(len(table)):
        prb, sch = discrete_action_to_prb(idx, table)
        assert abs(prb.sum() - 100.0) < 0.1, f"Action {idx} sum {prb.sum()} != 100.0"
        assert sch == -1


def test_discrete_scheduler_table():
    table = build_discrete_action_table(step=0.1, include_scheduler=True)
    assert len(table) == 198, f"Expected 198 actions, got {len(table)}"
    for entry in table:
        assert len(entry) == 4
        p0, p1, p2, sch = entry
        assert sch in {0, 1, 2}
        assert abs(p0 + p1 + p2 - 1.0) < 1e-6


if __name__ == "__main__":
    test_discrete_table_size()
    test_discrete_table_sum()
    test_continuous_sums_to_100()
    test_discrete_prb_sums_to_100()
    test_discrete_scheduler_table()
    print("All action_spaces tests passed.")
