#!/usr/bin/env python3
"""Re-score cached meta-heuristic evaluations against the current scoring.py.

When the scoring function (src/nsoran/scoring.py) changes, the scores stored in
the per-eval ``candidate.json`` sidecars become stale. Re-running the ns-3
simulations would waste the CPU already invested; this script instead
re-derives the score directly from each eval's persisted ``summary.csv`` and
rewrites the sidecar in place, preserving every other field (method,
evaluation_id, weights, result_dir, log_file).

Usage:
    PYTHONPATH=src python3 examples/rescore_cache.py [--output_root PATH] [--dry-run]

Exit code 0 on success; non-zero if any summary.csv is missing or unreadable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nsoran.scoring import read_summary, score_summary_rows  # noqa: E402

DEFAULT_OUTPUT_ROOT = (
    Path(__file__).resolve().parents[1]
    / "results_controlled"
    / "heuristics_metaheuristics"
    / "20260626_122326"
    / "metaheuristics"
)


def find_eval_dirs(root: Path) -> list[Path]:
    """Return all ``*_eval_*`` directories under ``root`` that hold a sidecar."""
    sidecars = sorted(root.rglob("candidate.json"))
    return [s.parent for s in sidecars]


def find_summary(eval_dir: Path) -> Path | None:
    """Locate the ``summary.csv`` produced by the ns-3 run inside ``eval_dir``."""
    matches = list(eval_dir.rglob("summary.csv"))
    return matches[0] if matches else None


def rescore_one(eval_dir: Path, *, dry_run: bool) -> tuple[float, float, str | None]:
    """Re-score one eval. Returns (old_score, new_score, error_or_None)."""
    sidecar = eval_dir / "candidate.json"
    summary = find_summary(eval_dir)
    if summary is None:
        return 0.0, 0.0, "summary.csv not found under eval dir"
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return 0.0, 0.0, f"cannot read sidecar: {exc}"

    old_score = float(payload.get("score", 0.0))
    try:
        rows = read_summary(summary)
        new_score = score_summary_rows(rows)
    except Exception as exc:  # noqa: BLE001 - surface any scoring failure
        return old_score, 0.0, f"scoring failed: {exc}"

    if not dry_run:
        payload["score"] = new_score
        sidecar.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return old_score, new_score, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output_root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root containing scenario=*/seed=*/metaheuristic_search/evals/",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    args = parser.parse_args()

    eval_dirs = find_eval_dirs(args.output_root)
    if not eval_dirs:
        print(f"[rescore] no candidate.json sidecars under {args.output_root}")
        return 1

    print(f"[rescore] {len(eval_dirs)} eval dirs under {args.output_root}")
    print(f"[rescore] dry_run={args.dry_run}")

    changed = 0
    errors = 0
    delta_sum = 0.0
    max_abs_delta = 0.0
    sample_changes: list[tuple[str, float, float]] = []

    for eval_dir in eval_dirs:
        old, new, err = rescore_one(eval_dir, dry_run=args.dry_run)
        rel = eval_dir.name
        if err is not None:
            errors += 1
            print(f"  [ERROR] {rel}: {err}")
            continue
        delta = new - old
        if abs(delta) > 1e-9:
            changed += 1
            delta_sum += delta
            if abs(delta) > max_abs_delta:
                max_abs_delta = abs(delta)
            if len(sample_changes) < 10:
                sample_changes.append((rel, old, new))

    print("")
    print(f"[rescore] processed : {len(eval_dirs)}")
    print(f"[rescore] changed   : {changed}")
    print(f"[rescore] errors    : {errors}")
    if changed:
        print(f"[rescore] mean delta: {delta_sum / changed:+.4f} pts")
        print(f"[rescore] max |delta|: {max_abs_delta:.4f} pts")
        print("[rescore] sample changes (rel, old -> new):")
        for rel, old, new in sample_changes:
            print(f"    {rel:20s} {old:9.4f} -> {new:9.4f}  ({new - old:+.4f})")
    if args.dry_run:
        print("[rescore] DRY RUN - no files written")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
