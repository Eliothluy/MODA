"""Shared KPI scoring for RSLAQ slice summary rows.

Used by both the offline meta-heuristic search and the post-search evaluation
so that baselines, heuristics, and meta-heuristics are ranked by the same
score function.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Sequence


SLICE_NAMES = ("eMBB", "URLLC", "MTC")


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, "", "NA"):
            return default
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return min(max(value, lo), hi)


def normalize_weights(values: Sequence[float]) -> list[float]:
    clean = [max(float(v), 0.0) for v in values[:3]]
    if len(clean) < 3:
        clean.extend([0.0] * (3 - len(clean)))
    total = sum(clean)
    if total <= 0.0:
        return [1.0 / 3.0] * 3
    return [v / total for v in clean]


def format_weights(weights: Sequence[float]) -> str:
    normalized = normalize_weights(weights)
    first = round(normalized[0], 6)
    second = round(normalized[1], 6)
    third = round(1.0 - first - second, 6)
    if third < 0.0:
        rounded = normalize_weights([first, second, max(third, 0.0)])
    else:
        rounded = [first, second, third]
    return ",".join(f"{weight:.6f}" for weight in rounded)


def read_summary(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as handle:
        return list(csv.DictReader(handle))


def score_summary_rows(rows: Iterable[dict[str, str]]) -> float:
    by_slice = {row.get("slice", ""): row for row in rows}
    if not all(name in by_slice for name in SLICE_NAMES):
        return -1e9

    sla = []
    offered = []
    pdr = []
    util = []
    for name in SLICE_NAMES:
        row = by_slice[name]
        sla.append(clamp(safe_float(row.get("sla_satisfaction_pct")) / 100.0))
        offered.append(clamp(safe_float(row.get("offered_load_satisfaction_pct")) / 100.0))
        pdr.append(clamp(safe_float(row.get("pdr_pct")) / 100.0))
        util_value = safe_float(row.get("budget_utilization_pct_mean"), 50.0)
        util.append(clamp(util_value / 100.0))

    mean_sla = sum(sla) / len(sla)
    min_sla = min(sla)
    mean_offered = sum(offered) / len(offered)
    mean_pdr = sum(pdr) / len(pdr)
    mean_util = sum(util) / len(util)

    urllc = by_slice["URLLC"]
    mtc = by_slice["MTC"]
    embb = by_slice["eMBB"]

    urllc_delay_ms = safe_float(urllc.get("delay_ms_mean"))
    # URLLC delay SLA violation. The URLLC latency budget is 10 ms; the penalty
    # saturates at 30 ms (well past the URLLC viability threshold), so the
    # divisor is 20 ms. The previous /200.0 made the penalty negligible across
    # the observed operating range (e.g. 14.864 ms -> -0.6 pts), letting the
    # optimizer accept solutions that openly violate the 10 ms target.
    urllc_delay_penalty = clamp((urllc_delay_ms - 10.0) / 20.0)

    mtc_thr = safe_float(mtc.get("throughput_mbps_mean"))
    mtc_starvation_penalty = max(0.0, 1.0 - sla[2])
    if mtc_thr <= 1e-9:
        mtc_starvation_penalty += 0.5

    embb_buffer = safe_float(embb.get("buffer_bytes_mean"))
    embb_buffer_penalty = 0.05 * clamp(embb_buffer / 5_000_000.0)

    score = 100.0 * (
        0.35 * mean_sla
        + 0.20 * min_sla
        + 0.20 * mean_offered
        + 0.15 * mean_pdr
        + 0.10 * mean_util
    )
    score -= 25.0 * urllc_delay_penalty
    score -= 40.0 * mtc_starvation_penalty
    score -= 100.0 * embb_buffer_penalty
    return score
