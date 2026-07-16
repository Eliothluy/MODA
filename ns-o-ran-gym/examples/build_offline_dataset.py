#!/usr/bin/env python3
"""Consolidate meta-heuristic evaluation data into a Parquet dataset for offline RL.

Reads all candidate.json sidecars (+ metadata.json + summary.csv) from the
finalized scenarios folder and produces a single Parquet file with columns:
  - State (context): scenario one-hot, num_ues, offered_load, packet_size
  - Action: w_embb, w_urllc, w_mtc
  - Reward: score (filtered: crashes with score=-1e6 discarded)
  - Auxiliary metrics: delay_urllc, pdr, sla, throughput

Usage:
    cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
    .venv-dashboard/bin/python examples/build_offline_dataset.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path("/home/elioth/Documentos/artigo_jussi")
DATA_ROOT = REPO_ROOT / "resultados_cenarios_finalizados_20260715"
META_ROOT = DATA_ROOT / "metaheuristics"
OUTPUT_PARQUET = DATA_ROOT / "offline_dataset.parquet"

SCENARIOS = ["low_traffic", "normal", "congestion", "stressed"]
SEEDS = [1, 2, 3]
SLICE_ORDER = ["eMBB", "URLLC", "MTC"]

# Cache metadata per scenario (it's the same across seeds/modes within a scenario)
_metadata_cache: dict[str, dict] = {}


def load_scenario_metadata(scenario: str) -> dict:
    """Load network state features from a metadata.json in the scenario."""
    if scenario in _metadata_cache:
        return _metadata_cache[scenario]
    # Find any metadata.json in this scenario
    candidates = list((META_ROOT / f"scenario={scenario}").rglob("metadata.json"))
    if not candidates:
        # Fallback: heuristics_ns3
        candidates = list((DATA_ROOT / "heuristics_ns3/results_rslaq_network_only" /
                           f"scenario={scenario}").glob("*/metadata.json"))
    if not candidates:
        raise FileNotFoundError(f"No metadata.json found for scenario {scenario}")
    meta = json.loads(candidates[0].read_text(encoding="utf-8"))
    _metadata_cache[scenario] = meta
    return meta


def extract_state_features(scenario: str) -> dict:
    """Extract network-state features that define the 'context' for the bandit."""
    meta = load_scenario_metadata(scenario)
    # metadata.json uses dicts keyed by slice name, not lists
    nues = meta.get("num_ues_per_slice", {})
    if isinstance(nues, dict):
        nues_e = nues.get("eMBB", 0)
        nues_u = nues.get("URLLC", 0)
        nues_m = nues.get("MTC", 0)
    else:
        nues_e = nues[0] if len(nues) > 0 else 0
        nues_u = nues[1] if len(nues) > 1 else 0
        nues_m = nues[2] if len(nues) > 2 else 0
    load = meta.get("offered_load_mbps_per_slice", {})
    if isinstance(load, dict):
        load_e = load.get("eMBB", 0)
        load_u = load.get("URLLC", 0)
        load_m = load.get("MTC", 0)
    else:
        load_e = load[0] if len(load) > 0 else 0
        load_u = load[1] if len(load) > 1 else 0
        load_m = load[2] if len(load) > 2 else 0
    pkt = meta.get("packet_size_bytes_per_slice", {})
    if isinstance(pkt, dict):
        pkt_e = pkt.get("eMBB", 0)
        pkt_u = pkt.get("URLLC", 0)
        pkt_m = pkt.get("MTC", 0)
    else:
        pkt_e = pkt[0] if len(pkt) > 0 else 0
        pkt_u = pkt[1] if len(pkt) > 1 else 0
        pkt_m = pkt[2] if len(pkt) > 2 else 0
    total_ues = meta.get("num_ues", nues_e + nues_u + nues_m)
    return {
        "num_ues_total": int(total_ues),
        "num_ues_embb": int(nues_e),
        "num_ues_urllc": int(nues_u),
        "num_ues_mtc": int(nues_m),
        "offered_load_embb": float(load_e),
        "offered_load_urllc": float(load_u),
        "offered_load_mtc": float(load_m),
        "pkt_size_embb": int(pkt_e),
        "pkt_size_urllc": int(pkt_u),
        "pkt_size_mtc": int(pkt_m),
    }


def load_summary_metrics(eval_dir: Path, scenario: str, seed: int) -> dict:
    """Load auxiliary metrics from summary.csv inside an eval directory."""
    summary = (eval_dir / "results_rslaq_network_only" / f"scenario={scenario}" /
               "mode=slice_custom" / f"seed={seed}_run=1" / "summary.csv")
    if not summary.exists():
        return {}
    try:
        import csv
        with summary.open() as f:
            rows = {r["slice"]: r for r in csv.DictReader(f)}
        result = {}
        for sl in SLICE_ORDER:
            r = rows.get(sl, {})
            result[f"delay_{sl.lower()}_mean"] = float(r.get("delay_ms_mean", 0))
            result[f"pdr_{sl.lower()}"] = float(r.get("pdr_pct", 0))
            result[f"sla_{sl.lower()}"] = float(r.get("sla_satisfaction_pct", 0))
            result[f"thr_{sl.lower()}"] = float(r.get("throughput_mbps_mean", 0))
        result["throughput_total"] = sum(result.get(f"thr_{sl.lower()}", 0) for sl in SLICE_ORDER)
        result["sla_min"] = min(result.get(f"sla_{sl.lower()}", 100) for sl in SLICE_ORDER)
        return result
    except Exception:
        return {}


def main() -> None:
    sys.path.insert(0, str(REPO_ROOT / "ns-o-ran-gym/src"))
    rows = []
    skipped_crash = 0
    skipped_missing = 0

    for scenario in SCENARIOS:
        state_features = extract_state_features(scenario)
        print(f"[{scenario}] state features: {state_features}")
        for seed in SEEDS:
            evals_dir = META_ROOT / f"scenario={scenario}/seed={seed}/metaheuristic_search/evals"
            if not evals_dir.exists():
                print(f"  seed {seed}: no evals dir, skipping")
                continue
            for sidecar in sorted(evals_dir.glob("*/candidate.json")):
                try:
                    p = json.loads(sidecar.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    skipped_missing += 1
                    continue
                score = float(p.get("score", -1e6))
                if score <= -1e5:  # crash-tolerated eval
                    skipped_crash += 1
                    continue
                weights = p.get("weights", [0, 0, 0])
                row = {
                    "scenario": scenario,
                    "seed": seed,
                    "method": p.get("method", "?"),
                    "eval_id": p.get("evaluation_id", 0),
                    "w_embb": float(weights[0]) if len(weights) > 0 else 0,
                    "w_urllc": float(weights[1]) if len(weights) > 1 else 0,
                    "w_mtc": float(weights[2]) if len(weights) > 2 else 0,
                    "score": score,
                }
                row.update(state_features)
                # Auxiliary metrics
                metrics = load_summary_metrics(sidecar.parent, scenario, seed)
                row.update(metrics)
                rows.append(row)

    df = pd.DataFrame(rows)
    print(f"\nTotal rows: {len(df)} | skipped crashes: {skipped_crash} | skipped missing: {skipped_missing}")
    print(f"Scenarios: {sorted(df['scenario'].unique())}")
    print(f"Score range: {df['score'].min():.2f} to {df['score'].max():.2f}")
    print(f"Score mean: {df['score'].mean():.2f} +/- {df['score'].std():.2f}")

    # One-hot encode scenario
    for sc in SCENARIOS:
        df[f"is_{sc}"] = (df["scenario"] == sc).astype(int)

    df.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"\nParquet saved: {OUTPUT_PARQUET} ({OUTPUT_PARQUET.stat().st_size / 1024:.0f} KB)")
    print(f"Columns ({len(df.columns)}): {list(df.columns)}")


if __name__ == "__main__":
    main()
