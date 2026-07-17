import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nsoran.scoring import (
    score_summary_rows_v2,
    SLICE_NAMES,
    V2_URLLC_DELAY_MS_MAX,
    V2_URLLC_PDR_MIN_PCT,
    V2_MTC_PDR_MIN_PCT,
)


def _row(slice, **kwargs):
    """A feasible row by default (all v2 hard constraints satisfied)."""
    base = {
        "slice": slice,
        "throughput_mbps_mean": "10",
        "sla_satisfaction_pct": "90",
        "offered_load_satisfaction_pct": "80",
        "pdr_pct": "95",
        "delay_ms_mean": "5",
        "delay_ms_p99": "5",
        "buffer_bytes_mean": "100000",
        "budget_utilization_pct_mean": "80",
    }
    base.update(kwargs)
    return base


def _feasible_case():
    return [
        _row("eMBB", offered_load_satisfaction_pct="85", pdr_pct="92", delay_ms_p99="40"),
        _row("URLLC", pdr_pct="95", delay_ms_p99="8"),
        _row("MTC", pdr_pct="88", delay_ms_p99="120"),
    ]


class ScoringV2Test(unittest.TestCase):
    def test_returns_float(self):
        self.assertIsInstance(score_summary_rows_v2(_feasible_case()), float)

    def test_missing_slices_returns_large_negative(self):
        self.assertLess(score_summary_rows_v2([_row("eMBB"), _row("URLLC")]), -1e8)

    def test_feasible_is_nonnegative(self):
        self.assertGreaterEqual(score_summary_rows_v2(_feasible_case()), 0.0)

    def test_infeasible_is_negative(self):
        # URLLC p99 well above the 10 ms deadline -> infeasible
        rows = _feasible_case()
        rows[1]["delay_ms_p99"] = str(V2_URLLC_DELAY_MS_MAX * 10)
        self.assertLess(score_summary_rows_v2(rows), 0.0)

    def test_feasible_always_beats_infeasible(self):
        feasible = _feasible_case()
        infeasible = _feasible_case()
        infeasible[2]["pdr_pct"] = "2"  # MTC starved
        self.assertGreater(
            score_summary_rows_v2(feasible), score_summary_rows_v2(infeasible)
        )

    def test_acid_case_sa_eval_0021_is_penalized(self):
        """The pathological weights [0.816,0.180,0.004] that scored HIGHEST under
        v1 (85.28) starve MTC (PDR=2.4%, delay=4479ms) — v2 must reject it."""
        acid = [
            _row("eMBB", throughput_mbps_mean="158.9", offered_load_satisfaction_pct="24",
                 pdr_pct="86.7", delay_ms_p99="1721"),
            _row("URLLC", throughput_mbps_mean="5.1", pdr_pct="80", delay_ms_p99="3.4"),
            _row("MTC", throughput_mbps_mean="1.5", offered_load_satisfaction_pct="2",
                 pdr_pct="2.4", delay_ms_p99="4479"),
        ]
        score = score_summary_rows_v2(acid)
        self.assertLess(score, 0.0)  # infeasible: MTC starved AND eMBB under target
        # And it must lose to a genuinely balanced feasible solution.
        self.assertGreater(score_summary_rows_v2(_feasible_case()), score)

    def test_worse_violation_scores_lower(self):
        """Monotonicity: a larger constraint violation yields a lower score."""
        mild = _feasible_case()
        mild[2]["pdr_pct"] = str(V2_MTC_PDR_MIN_PCT - 10)
        severe = _feasible_case()
        severe[2]["pdr_pct"] = str(V2_MTC_PDR_MIN_PCT - 40)
        self.assertGreater(
            score_summary_rows_v2(mild), score_summary_rows_v2(severe)
        )

    def test_urllc_pdr_constraint(self):
        rows = _feasible_case()
        rows[1]["pdr_pct"] = str(V2_URLLC_PDR_MIN_PCT - 20)
        self.assertLess(score_summary_rows_v2(rows), 0.0)


if __name__ == "__main__":
    unittest.main()
