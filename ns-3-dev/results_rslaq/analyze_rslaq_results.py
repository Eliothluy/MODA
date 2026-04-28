#!/usr/bin/env python3
"""
RSLAQ Results Analysis and Consistency Checker

Analyzes RSLAQ simulation results and performs consistency checks between:
- UE/RNTI mapping
- UE-level FlowMonitor KPIs
- Slice-level FlowMonitor KPIs
- MAC scheduler slice allocation logs
- MAC scheduler UE detail logs
- Unmapped RNTI logs

Usage:
    python3 analyze_rslaq_results.py <scenario_name> [results_dir]

Example:
    python3 analyze_rslaq_results.py low_traffic results_rslaq
    python3 analyze_rslaq_results.py normal ns-3-dev/results_rslaq
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


DEFAULT_SLICE_ID_TO_NAME = {
    0: "eMBB",
    1: "URLLC",
    2: "MTC",
}


class RslaqAnalyzer:
    """Analyzer for RSLAQ simulation results."""

    def __init__(self, scenario: str, results_dir: str = "."):
        self.scenario = scenario
        self.results_dir = Path(results_dir)

        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

        self.ue_mapping: Dict[int, Dict[str, Any]] = {}
        self.rnti_to_ue: Dict[int, int] = {}
        self.slice_id_to_name: Dict[int, str] = dict(DEFAULT_SLICE_ID_TO_NAME)
        self.slice_name_to_id: Dict[str, int] = {
            v: k for k, v in self.slice_id_to_name.items()
        }

        self.ue_kpis: Dict[int, Dict[str, Any]] = {}
        self.slice_kpis: Dict[str, Dict[str, Any]] = {}
        self.slice_alloc: List[Dict[str, Any]] = []
        self.ue_detail: List[Dict[str, Any]] = []
        self.unmapped_rntis: List[Dict[str, Any]] = []

        self._scenario_mismatch_counts: Counter[str] = Counter()
        self._scenario_mismatch_examples: Dict[str, Tuple[str, str]] = {}

        self.slice_alloc_summary: Dict[str, Dict[str, Any]] = {}
        self.tx_rx_alloc_diagnosis: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Robust parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @classmethod
    def _get_str(cls, row: Dict[str, Any], key: str, default: str = "") -> str:
        value = cls._clean(row.get(key, default))
        return value if value != "" else default

    @classmethod
    def _get_int(cls, row: Dict[str, Any], key: str, default: int = 0) -> int:
        value = cls._clean(row.get(key, ""))
        if value == "":
            return default
        try:
            return int(float(value))
        except ValueError:
            return default

    @classmethod
    def _get_float(cls, row: Dict[str, Any], key: str, default: float = 0.0) -> float:
        value = cls._clean(row.get(key, ""))
        if value == "":
            return default
        try:
            return float(value)
        except ValueError:
            return default

    @classmethod
    def _get_bool(cls, row: Dict[str, Any], key: str, default: bool = False) -> bool:
        value = cls._clean(row.get(key, ""))
        if value == "":
            return default
        return value.lower() in {"1", "true", "yes", "y", "sim"}

    @staticmethod
    def _safe_div(num: float, den: float, default: float = 0.0) -> float:
        return num / den if den else default

    @staticmethod
    def _read_csv(file_path: Path) -> Iterable[Dict[str, Any]]:
        with open(file_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row

    def _record_scenario_mismatch(self, file_name: str, row_scenario: str) -> None:
        self._scenario_mismatch_counts[file_name] += 1
        if file_name not in self._scenario_mismatch_examples:
            self._scenario_mismatch_examples[file_name] = (row_scenario, self.scenario)

    def _check_row_scenario(self, file_name: str, row: Dict[str, Any]) -> None:
        if "scenario" not in row:
            return

        row_scenario = self._get_str(row, "scenario")
        if row_scenario and row_scenario != self.scenario:
            self._record_scenario_mismatch(file_name, row_scenario)

    def _finalize_scenario_mismatch_checks(self) -> None:
        for file_name, count in self._scenario_mismatch_counts.items():
            actual, expected = self._scenario_mismatch_examples[file_name]
            self.errors.append(
                f"{file_name}: {count} row(s) have scenario='{actual}' "
                f"but expected='{expected}'"
            )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_all(self) -> bool:
        """Load all scenario CSV files."""
        success = True

        required_files = {
            "mapping": self.results_dir / f"{self.scenario}_ue_rnti_mapping.csv",
            "ue_kpis": self.results_dir / f"rslaq_{self.scenario}_ue.csv",
            "slice_kpis": self.results_dir / f"rslaq_{self.scenario}_slice.csv",
        }

        optional_files = {
            "slice_alloc": self.results_dir / f"{self.scenario}_slice_alloc.csv",
            "ue_detail": self.results_dir / f"{self.scenario}_ue_detail.csv",
            "unmapped": self.results_dir / f"{self.scenario}_unmapped_rntis.csv",
        }

        for _, file_path in required_files.items():
            if not file_path.exists():
                self.errors.append(f"Missing required file: {file_path}")
                success = False

        if not success:
            return False

        self._load_ue_mapping(required_files["mapping"])
        self._load_ue_kpis(required_files["ue_kpis"])
        self._load_slice_kpis(required_files["slice_kpis"])

        if optional_files["slice_alloc"].exists():
            self._load_slice_alloc(optional_files["slice_alloc"])
        else:
            self.warnings.append(f"Missing optional file: {optional_files['slice_alloc']}")

        if optional_files["ue_detail"].exists():
            self._load_ue_detail(optional_files["ue_detail"])
        else:
            self.warnings.append(f"Missing optional file: {optional_files['ue_detail']}")

        if optional_files["unmapped"].exists():
            self._load_unmapped_rntis(optional_files["unmapped"])
        else:
            self.warnings.append(f"Missing optional file: {optional_files['unmapped']}")

        self._finalize_scenario_mismatch_checks()
        self._derive_slice_maps_from_mapping()

        return True

    def _derive_slice_maps_from_mapping(self) -> None:
        """Derive slice ID/name maps from the UE mapping file."""
        for info in self.ue_mapping.values():
            self.slice_id_to_name[int(info["sliceId"])] = str(info["sliceName"])

        self.slice_name_to_id = {
            name: sid for sid, name in self.slice_id_to_name.items()
        }

    def _load_ue_mapping(self, file_path: Path) -> None:
        file_name = file_path.name

        for row in self._read_csv(file_path):
            self._check_row_scenario(file_name, row)

            ue_id = self._get_int(row, "ueId", default=-1)
            if ue_id < 0:
                self.warnings.append(f"{file_name}: skipped row with invalid ueId: {row}")
                continue

            rnti = self._get_int(row, "rnti", default=-1)
            slice_id = self._get_int(row, "sliceId", default=-1)
            slice_name = self._get_str(row, "sliceName", default=f"Slice{slice_id}")

            self.ue_mapping[ue_id] = {
                "scenario": self._get_str(row, "scenario", default=self.scenario),
                "imsi": self._get_int(row, "imsi", default=0),
                "rnti": rnti,
                "sliceId": slice_id,
                "sliceName": slice_name,
                "ip": self._get_str(row, "ip", default=""),
                "port": self._get_int(row, "port", default=0),
            }

            if rnti >= 0:
                if rnti in self.rnti_to_ue:
                    self.errors.append(
                        f"{file_name}: duplicate RNTI {rnti} for UE {ue_id}; "
                        f"already mapped to UE {self.rnti_to_ue[rnti]}"
                    )
                self.rnti_to_ue[rnti] = ue_id

        self.info.append(f"Loaded {len(self.ue_mapping)} UE mappings")

    def _load_ue_kpis(self, file_path: Path) -> None:
        file_name = file_path.name

        for row in self._read_csv(file_path):
            self._check_row_scenario(file_name, row)

            ue_id = self._get_int(row, "ue_id", default=-1)
            if ue_id < 0:
                self.warnings.append(f"{file_name}: skipped row with invalid ue_id: {row}")
                continue

            tx_packets = self._get_int(row, "tx_packets")
            rx_packets = self._get_int(row, "rx_packets")

            effective_lost_packets = self._get_int(
                row,
                "effective_lost_packets",
                default=max(0, tx_packets - rx_packets),
            )
            effective_pdr = self._get_float(
                row,
                "effective_pdr",
                default=self._safe_div(rx_packets, tx_packets),
            )

            self.ue_kpis[ue_id] = {
                "scenario": self._get_str(row, "scenario", default=self.scenario),
                "slice": self._get_str(row, "slice", default="UNKNOWN"),
                "tx_bytes": self._get_int(row, "tx_bytes"),
                "rx_bytes": self._get_int(row, "rx_bytes"),
                "tx_packets": tx_packets,
                "rx_packets": rx_packets,
                "lost_packets": self._get_int(row, "lost_packets"),
                "effective_lost_packets": effective_lost_packets,
                "throughput_mbps": self._get_float(row, "throughput_mbps"),
                "avg_delay_ms": self._get_float(row, "avg_delay_ms"),
                "pdr": self._get_float(row, "pdr"),
                "effective_pdr": effective_pdr,
            }

        self.info.append(f"Loaded {len(self.ue_kpis)} UE KPI rows")

    def _load_slice_kpis(self, file_path: Path) -> None:
        file_name = file_path.name

        for row in self._read_csv(file_path):
            self._check_row_scenario(file_name, row)

            slice_name = self._get_str(row, "slice", default="UNKNOWN")
            tx_packets = self._get_int(row, "tx_packets")
            rx_packets = self._get_int(row, "rx_packets")

            effective_lost_packets = self._get_int(
                row,
                "effective_lost_packets",
                default=max(0, tx_packets - rx_packets),
            )
            effective_pdr = self._get_float(
                row,
                "effective_pdr",
                default=self._safe_div(rx_packets, tx_packets),
            )

            self.slice_kpis[slice_name] = {
                "scenario": self._get_str(row, "scenario", default=self.scenario),
                "tx_bytes": self._get_int(row, "tx_bytes"),
                "rx_bytes": self._get_int(row, "rx_bytes"),
                "tx_packets": tx_packets,
                "rx_packets": rx_packets,
                "lost_packets": self._get_int(row, "lost_packets"),
                "effective_lost_packets": effective_lost_packets,
                "throughput_mbps": self._get_float(row, "throughput_mbps"),
                "avg_delay_ms": self._get_float(row, "avg_delay_ms"),
                "pdr": self._get_float(row, "pdr"),
                "effective_pdr": effective_pdr,
            }

        self.info.append(f"Loaded {len(self.slice_kpis)} slice KPI rows")

    def _load_slice_alloc(self, file_path: Path) -> None:
        file_name = file_path.name

        for row in self._read_csv(file_path):
            self._check_row_scenario(file_name, row)

            self.slice_alloc.append({
                "callId": self._get_int(row, "callId"),
                "timeMs": self._get_int(row, "timeMs"),
                "scenario": self._get_str(row, "scenario", default=self.scenario),
                "slot": self._get_str(row, "slot", default="NA"),
                "bwpId": self._get_str(row, "bwpId", default="NA"),
                "beamId": self._get_str(row, "beamId", default="NA"),
                "sliceId": self._get_int(row, "sliceId", default=-1),
                "configuredWeight": self._get_float(row, "configuredWeight"),
                "effectiveWeight": self._get_float(row, "effectiveWeight"),
                "activeUes": self._get_int(row, "activeUes"),
                "beamSym": self._get_int(row, "beamSym"),
                "hasDemand": self._get_bool(row, "hasDemand"),
                "budgetRbg": self._get_int(row, "budgetRbg"),
                "allocatedRbg": self._get_int(row, "allocatedRbg"),
                "reason": self._get_str(row, "reason", default=""),
                "rntis": self._get_str(row, "rntis", default=""),
            })

        self.info.append(f"Loaded {len(self.slice_alloc)} slice allocation records")

    def _load_ue_detail(self, file_path: Path) -> None:
        file_name = file_path.name

        for row in self._read_csv(file_path):
            self._check_row_scenario(file_name, row)

            self.ue_detail.append({
                "callId": self._get_int(row, "callId"),
                "timeMs": self._get_int(row, "timeMs"),
                "scenario": self._get_str(row, "scenario", default=self.scenario),
                "slot": self._get_str(row, "slot", default="NA"),
                "bwpId": self._get_str(row, "bwpId", default="NA"),
                "beamId": self._get_str(row, "beamId", default="NA"),
                "sliceId": self._get_int(row, "sliceId", default=-1),
                "rnti": self._get_int(row, "rnti", default=-1),
                "bufQueueSize": self._get_int(row, "bufQueueSize"),
                "dlTbSizeBefore": self._get_int(row, "dlTbSizeBefore"),
                "hasDemand": self._get_bool(row, "hasDemand"),
                "demandPassed": self._get_bool(row, "demandPassed"),
                "rbgAllocated": self._get_int(row, "rbgAllocated"),
                "uniqueRbgs": self._get_int(row, "uniqueRbgs"),
                "tbSizeBytes": self._get_int(row, "tbSizeBytes"),
                "mcs": self._get_int(row, "mcs"),
                "reason": self._get_str(row, "reason", default=""),
            })

        self.info.append(f"Loaded {len(self.ue_detail)} UE detail records")

    def _load_unmapped_rntis(self, file_path: Path) -> None:
        file_name = file_path.name

        for row in self._read_csv(file_path):
            self._check_row_scenario(file_name, row)

            rnti = self._get_int(row, "rnti", default=-1)
            if rnti < 0:
                continue

            self.unmapped_rntis.append({
                "callId": self._get_int(row, "callId"),
                "timeMs": self._get_int(row, "timeMs"),
                "scenario": self._get_str(row, "scenario", default=self.scenario),
                "rnti": rnti,
                "reason": self._get_str(row, "reason", default=""),
            })

        self.info.append(f"Loaded {len(self.unmapped_rntis)} unmapped RNTI records")

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check_consistency(self) -> bool:
        """Run all consistency and diagnostic checks."""
        self._check_ue_slice_aggregation()
        self._check_slice_rbg_allocation_for_rx()
        self._check_ue_detail_coverage_for_rx()
        self._check_rnti_mapping_coverage()
        self._check_unmapped_rntis()
        self._check_effective_metrics()
        self._summarize_slice_alloc()
        self._diagnose_tx_rx_allocation()
        return not self.errors

    def _check_ue_slice_aggregation(self) -> None:
        """Check whether sum of UE KPIs matches slice KPIs."""
        self.info.append("Check UE -> Slice aggregation")

        slice_sums: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "tx_bytes": 0,
            "rx_bytes": 0,
            "tx_packets": 0,
            "rx_packets": 0,
            "lost_packets": 0,
            "effective_lost_packets": 0,
        })

        for _, kpis in self.ue_kpis.items():
            slice_name = str(kpis["slice"])
            for metric in slice_sums[slice_name]:
                slice_sums[slice_name][metric] += int(kpis.get(metric, 0))

        for slice_name, slice_kpi in self.slice_kpis.items():
            if slice_name not in slice_sums:
                self.warnings.append(f"Slice {slice_name}: no UE rows found")
                continue

            for metric in ["tx_bytes", "rx_bytes", "tx_packets", "rx_packets"]:
                ue_sum = slice_sums[slice_name][metric]
                slice_val = int(slice_kpi.get(metric, 0))
                if ue_sum != slice_val:
                    self.errors.append(
                        f"Slice {slice_name}: {metric} mismatch "
                        f"(UE sum={ue_sum}, slice={slice_val})"
                    )

            ue_eff_lost_sum = slice_sums[slice_name]["effective_lost_packets"]
            slice_eff_lost = int(slice_kpi.get("effective_lost_packets", 0))
            if ue_eff_lost_sum != slice_eff_lost:
                self.warnings.append(
                    f"Slice {slice_name}: effective_lost_packets mismatch "
                    f"(UE sum={ue_eff_lost_sum}, slice={slice_eff_lost})"
                )

    def _check_slice_rbg_allocation_for_rx(self) -> None:
        """Slices with RX > 0 should have at least one RBG allocation."""
        self.info.append("Check slice RBG allocation for slices with RX > 0")

        slices_with_rx = {
            name for name, kpis in self.slice_kpis.items()
            if int(kpis.get("rx_packets", 0)) > 0
        }

        total_alloc_by_slice = self._total_allocated_rbg_by_slice_name()

        for slice_name in sorted(slices_with_rx):
            total_alloc = total_alloc_by_slice.get(slice_name, 0)
            if total_alloc <= 0:
                self.errors.append(
                    f"Slice {slice_name}: RX={self.slice_kpis[slice_name]['rx_packets']} "
                    f"but no allocatedRbg found in slice_alloc"
                )
            else:
                self.info.append(
                    f"Slice {slice_name}: RX>0 and allocatedRbg={total_alloc} (OK)"
                )

    def _check_ue_detail_coverage_for_rx(self) -> None:
        """RNTIs with RX > 0 should appear in UE detail with allocation."""
        self.info.append("Check UE detail coverage for RNTIs with RX > 0")

        rntis_with_rx: Set[int] = set()
        for ue_id, kpis in self.ue_kpis.items():
            if int(kpis.get("rx_packets", 0)) > 0 and ue_id in self.ue_mapping:
                rntis_with_rx.add(int(self.ue_mapping[ue_id]["rnti"]))

        rntis_with_alloc: Set[int] = {
            int(d["rnti"]) for d in self.ue_detail
            if int(d.get("rnti", -1)) >= 0 and int(d.get("rbgAllocated", 0)) > 0
        }

        missing = rntis_with_rx - rntis_with_alloc
        if missing:
            self.errors.append(
                f"RNTIs with RX>0 but no rbgAllocated>0 in ue_detail: {sorted(missing)}"
            )

        self.info.append(f"RNTIs with RX>0: {len(rntis_with_rx)}")
        self.info.append(f"RNTIs with rbgAllocated>0 in ue_detail: {len(rntis_with_alloc)}")

    def _check_rnti_mapping_coverage(self) -> None:
        """All RNTIs in UE detail should exist in mapping."""
        self.info.append("Check RNTI mapping coverage")

        rntis_in_detail: Set[int] = {
            int(d["rnti"]) for d in self.ue_detail
            if int(d.get("rnti", -1)) >= 0
        }
        rntis_in_mapping: Set[int] = set(self.rnti_to_ue.keys())

        unmapped_in_detail = rntis_in_detail - rntis_in_mapping
        if unmapped_in_detail:
            self.errors.append(
                f"RNTIs in ue_detail but not in mapping: {sorted(unmapped_in_detail)}"
            )

    def _check_unmapped_rntis(self) -> None:
        """Check explicit unmapped RNTI file."""
        self.info.append("Check explicit unmapped RNTIs")

        if not self.unmapped_rntis:
            self.info.append("No unmapped RNTIs found (OK)")
            return

        unique_rntis = sorted({int(row["rnti"]) for row in self.unmapped_rntis})
        self.warnings.append(f"Unmapped RNTIs found: {unique_rntis}")

    def _check_effective_metrics(self) -> None:
        """Validate effective lost packets and effective PDR for UE and slice KPIs."""
        self.info.append("Check effective loss and PDR metrics")

        for ue_id, kpis in self.ue_kpis.items():
            self._check_effective_metrics_for_row(
                label=f"UE {ue_id}",
                tx=int(kpis.get("tx_packets", 0)),
                rx=int(kpis.get("rx_packets", 0)),
                reported_lost=int(kpis.get("lost_packets", 0)),
                effective_lost=int(kpis.get("effective_lost_packets", 0)),
                reported_pdr=float(kpis.get("pdr", 0.0)),
                effective_pdr=float(kpis.get("effective_pdr", 0.0)),
            )

        for slice_name, kpis in self.slice_kpis.items():
            self._check_effective_metrics_for_row(
                label=f"Slice {slice_name}",
                tx=int(kpis.get("tx_packets", 0)),
                rx=int(kpis.get("rx_packets", 0)),
                reported_lost=int(kpis.get("lost_packets", 0)),
                effective_lost=int(kpis.get("effective_lost_packets", 0)),
                reported_pdr=float(kpis.get("pdr", 0.0)),
                effective_pdr=float(kpis.get("effective_pdr", 0.0)),
            )

    def _check_effective_metrics_for_row(
        self,
        label: str,
        tx: int,
        rx: int,
        reported_lost: int,
        effective_lost: int,
        reported_pdr: float,
        effective_pdr: float,
    ) -> None:
        expected_lost = max(0, tx - rx)
        expected_pdr = self._safe_div(rx, tx)

        if effective_lost != expected_lost:
            self.warnings.append(
                f"{label}: effective_lost_packets={effective_lost}, "
                f"expected={expected_lost}"
            )

        if abs(effective_pdr - expected_pdr) > 1e-6:
            self.warnings.append(
                f"{label}: effective_pdr={effective_pdr:.6f}, "
                f"expected={expected_pdr:.6f}"
            )

        if reported_lost != expected_lost:
            self.warnings.append(
                f"{label}: reported lost_packets={reported_lost}, "
                f"effective_lost_packets={expected_lost}. "
                "Use effective_lost_packets for diagnostics."
            )

        if abs(reported_pdr - expected_pdr) > 1e-4:
            self.warnings.append(
                f"{label}: reported pdr={reported_pdr:.6f}, "
                f"rx/tx={expected_pdr:.6f}"
            )

    # ------------------------------------------------------------------
    # Derived summaries and diagnosis
    # ------------------------------------------------------------------

    def _slice_name_from_id(self, slice_id: int) -> str:
        return self.slice_id_to_name.get(slice_id, f"Slice{slice_id}")

    def _total_allocated_rbg_by_slice_name(self) -> Dict[str, int]:
        totals: Dict[str, int] = defaultdict(int)
        for row in self.slice_alloc:
            slice_name = self._slice_name_from_id(int(row["sliceId"]))
            totals[slice_name] += int(row.get("allocatedRbg", 0))
        return dict(totals)

    def _summarize_slice_alloc(self) -> None:
        """Build summary stats for slice allocation records."""
        self.info.append("Build slice allocation summary")

        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in self.slice_alloc:
            grouped[self._slice_name_from_id(int(row["sliceId"]))].append(row)

        summary: Dict[str, Dict[str, Any]] = {}

        for slice_name, rows in grouped.items():
            records = len(rows)
            demand_rows = sum(1 for r in rows if bool(r.get("hasDemand", False)))
            active_rows = sum(1 for r in rows if int(r.get("activeUes", 0)) > 0)
            total_budget = sum(int(r.get("budgetRbg", 0)) for r in rows)
            total_alloc = sum(int(r.get("allocatedRbg", 0)) for r in rows)
            zero_alloc_with_demand = sum(
                1 for r in rows
                if bool(r.get("hasDemand", False)) and int(r.get("allocatedRbg", 0)) == 0
            )
            budget_no_alloc = sum(
                1 for r in rows
                if int(r.get("budgetRbg", 0)) > 0 and int(r.get("allocatedRbg", 0)) == 0
            )
            avg_active_ues = self._safe_div(
                sum(int(r.get("activeUes", 0)) for r in rows),
                records,
            )
            avg_effective_weight = self._safe_div(
                sum(float(r.get("effectiveWeight", 0.0)) for r in rows),
                records,
            )
            reasons = Counter(str(r.get("reason", "")) for r in rows)

            summary[slice_name] = {
                "records": records,
                "active_rows": active_rows,
                "demand_rows": demand_rows,
                "total_budget": total_budget,
                "total_alloc": total_alloc,
                "zero_alloc_with_demand": zero_alloc_with_demand,
                "budget_no_alloc": budget_no_alloc,
                "avg_active_ues": avg_active_ues,
                "avg_effective_weight": avg_effective_weight,
                "reasons": reasons,
            }

        self.slice_alloc_summary = summary

    def _diagnose_tx_rx_allocation(self) -> None:
        """Classify per-slice behavior based on TX/RX and RBG allocation."""
        self.info.append("Diagnose TX/RX/allocation per slice")

        total_alloc_by_slice = self._total_allocated_rbg_by_slice_name()

        for slice_name, kpis in self.slice_kpis.items():
            tx = int(kpis.get("tx_packets", 0))
            rx = int(kpis.get("rx_packets", 0))
            total_alloc = int(total_alloc_by_slice.get(slice_name, 0))

            if tx == 0 and rx == 0:
                diagnosis = (
                    "No traffic observed. Check application setup only if this was unexpected."
                )
                self.tx_rx_alloc_diagnosis[slice_name] = diagnosis
                self.info.append(f"{slice_name}: {diagnosis}")
                continue

            if tx > 0 and rx > 0 and total_alloc > 0:
                diagnosis = (
                    "Functional path: TX>0, RX>0, and allocatedRbg>0."
                )
                self.tx_rx_alloc_diagnosis[slice_name] = diagnosis
                self.info.append(f"{slice_name}: {diagnosis}")
                continue

            if tx > 0 and rx > 0 and total_alloc == 0:
                diagnosis = (
                    "Instrumentation issue: TX>0 and RX>0, but no RBG allocation "
                    "was recorded in slice_alloc."
                )
                self.tx_rx_alloc_diagnosis[slice_name] = diagnosis
                self.errors.append(f"{slice_name}: {diagnosis}")
                continue

            if tx > 0 and rx == 0 and total_alloc == 0:
                diagnosis = (
                    "Scheduler-side failure: TX>0, RX=0, and allocatedRbg=0. "
                    "The slice has traffic but did not receive MAC resources."
                )
                self.tx_rx_alloc_diagnosis[slice_name] = diagnosis
                self.errors.append(f"{slice_name}: {diagnosis}")
                continue

            if tx > 0 and rx == 0 and total_alloc > 0:
                diagnosis = (
                    "Post-scheduler failure: TX>0, RX=0, but allocatedRbg>0. "
                    "Investigate MAC/RLC/PHY/HARQ/FlowMonitor path."
                )
                self.tx_rx_alloc_diagnosis[slice_name] = diagnosis
                self.errors.append(f"{slice_name}: {diagnosis}")
                continue

            diagnosis = (
                f"Unclassified state: tx={tx}, rx={rx}, allocatedRbg={total_alloc}."
            )
            self.tx_rx_alloc_diagnosis[slice_name] = diagnosis
            self.warnings.append(f"{slice_name}: {diagnosis}")

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(self) -> str:
        """Generate Markdown diagnostic report."""
        lines: List[str] = []

        lines.append("# RSLAQ Diagnostic Report")
        lines.append("")
        lines.append(f"**Scenario:** `{self.scenario}`")
        lines.append(f"**Results directory:** `{self.results_dir}`")
        lines.append("")

        self._append_summary(lines)
        self._append_slice_kpis(lines)
        self._append_slice_alloc_summary(lines)
        self._append_tx_rx_alloc_diagnosis(lines)
        self._append_ue_mapping(lines)
        self._append_messages(lines)

        return "\n".join(lines)

    def _append_summary(self, lines: List[str]) -> None:
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Total UE mappings: **{len(self.ue_mapping)}**")
        lines.append(f"- UE KPI rows: **{len(self.ue_kpis)}**")
        lines.append(f"- Slice KPI rows: **{len(self.slice_kpis)}**")
        lines.append(f"- Slice allocation records: **{len(self.slice_alloc)}**")
        lines.append(f"- UE detail records: **{len(self.ue_detail)}**")
        lines.append(f"- Unmapped RNTI records: **{len(self.unmapped_rntis)}**")
        lines.append(f"- Errors: **{len(self.errors)}**")
        lines.append(f"- Warnings: **{len(self.warnings)}**")
        lines.append("")

        if self.errors:
            lines.append("**Conclusion:** ❌ Consistency/diagnostic errors found.")
        elif self.warnings:
            lines.append("**Conclusion:** ⚠️ Checks passed with warnings.")
        else:
            lines.append("**Conclusion:** ✅ All consistency checks passed.")
        lines.append("")

    def _append_slice_kpis(self, lines: List[str]) -> None:
        lines.append("## Slice KPIs")
        lines.append("")
        lines.append(
            "| Slice | TX pkts | RX pkts | FlowMonitor lost | Effective lost | "
            "Throughput Mbps | Reported PDR | Effective PDR | Avg delay ms |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

        ordered = ["eMBB", "URLLC", "MTC"]
        slice_names = ordered + sorted([s for s in self.slice_kpis if s not in ordered])

        for slice_name in slice_names:
            if slice_name not in self.slice_kpis:
                continue
            k = self.slice_kpis[slice_name]
            lines.append(
                f"| {slice_name} "
                f"| {int(k.get('tx_packets', 0))} "
                f"| {int(k.get('rx_packets', 0))} "
                f"| {int(k.get('lost_packets', 0))} "
                f"| {int(k.get('effective_lost_packets', 0))} "
                f"| {float(k.get('throughput_mbps', 0.0)):.4f} "
                f"| {float(k.get('pdr', 0.0)):.6f} "
                f"| {float(k.get('effective_pdr', 0.0)):.6f} "
                f"| {float(k.get('avg_delay_ms', 0.0)):.4f} |"
            )

        lines.append("")

    def _append_slice_alloc_summary(self, lines: List[str]) -> None:
        lines.append("## Slice Allocation Summary")
        lines.append("")

        if not self.slice_alloc_summary:
            lines.append("_No slice allocation records loaded._")
            lines.append("")
            return

        lines.append(
            "| Slice | Records | Active rows | Demand rows | Total budget RBG | "
            "Total allocated RBG | Zero alloc with demand | Budget>0 but alloc=0 | "
            "Avg active UEs | Avg effective weight | Top reasons |"
        )
        lines.append(
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
        )

        ordered = ["eMBB", "URLLC", "MTC"]
        slice_names = ordered + sorted([
            s for s in self.slice_alloc_summary if s not in ordered
        ])

        for slice_name in slice_names:
            if slice_name not in self.slice_alloc_summary:
                continue

            s = self.slice_alloc_summary[slice_name]
            reasons = s["reasons"]
            top_reasons = ", ".join(
                f"{reason}:{count}" for reason, count in reasons.most_common(5)
            )

            lines.append(
                f"| {slice_name} "
                f"| {s['records']} "
                f"| {s['active_rows']} "
                f"| {s['demand_rows']} "
                f"| {s['total_budget']} "
                f"| {s['total_alloc']} "
                f"| {s['zero_alloc_with_demand']} "
                f"| {s['budget_no_alloc']} "
                f"| {s['avg_active_ues']:.2f} "
                f"| {s['avg_effective_weight']:.4f} "
                f"| {top_reasons} |"
            )

        lines.append("")

    def _append_tx_rx_alloc_diagnosis(self, lines: List[str]) -> None:
        lines.append("## TX/RX/Allocation Diagnosis")
        lines.append("")

        if not self.tx_rx_alloc_diagnosis:
            lines.append("_No diagnosis generated._")
            lines.append("")
            return

        lines.append("| Slice | Diagnosis |")
        lines.append("|---|---|")

        ordered = ["eMBB", "URLLC", "MTC"]
        slice_names = ordered + sorted([
            s for s in self.tx_rx_alloc_diagnosis if s not in ordered
        ])

        for slice_name in slice_names:
            if slice_name not in self.tx_rx_alloc_diagnosis:
                continue
            lines.append(
                f"| {slice_name} | {self.tx_rx_alloc_diagnosis[slice_name]} |"
            )

        lines.append("")

    def _append_ue_mapping(self, lines: List[str]) -> None:
        lines.append("## UE/RNTI Mapping")
        lines.append("")
        lines.append("| UE ID | IMSI | RNTI | Slice ID | Slice | IP | Port |")
        lines.append("|---:|---:|---:|---:|---|---|---:|")

        for ue_id in sorted(self.ue_mapping):
            m = self.ue_mapping[ue_id]
            lines.append(
                f"| {ue_id} "
                f"| {m.get('imsi', 0)} "
                f"| {m.get('rnti', -1)} "
                f"| {m.get('sliceId', -1)} "
                f"| {m.get('sliceName', '')} "
                f"| {m.get('ip', '')} "
                f"| {m.get('port', 0)} |"
            )

        lines.append("")

    def _append_messages(self, lines: List[str]) -> None:
        if self.errors:
            lines.append("## Errors")
            lines.append("")
            for msg in self.errors:
                lines.append(f"- ❌ {msg}")
            lines.append("")

        if self.warnings:
            lines.append("## Warnings")
            lines.append("")
            for msg in self.warnings:
                lines.append(f"- ⚠️ {msg}")
            lines.append("")

        if self.info:
            lines.append("## Information")
            lines.append("")
            for msg in self.info:
                lines.append(f"- {msg}")
            lines.append("")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze RSLAQ simulation results and check consistency."
    )
    parser.add_argument(
        "scenario",
        help="Scenario name, e.g., low_traffic, normal, congestion, stressed",
    )
    parser.add_argument(
        "results_dir",
        nargs="?",
        default=".",
        help="Directory containing CSV results. Default: current directory.",
    )
    parser.add_argument(
        "--report-name",
        default=None,
        help="Optional report file name. Default: <scenario>_diagnostic_report.md",
    )
    args = parser.parse_args()

    analyzer = RslaqAnalyzer(args.scenario, args.results_dir)

    if not analyzer.load_all():
        report = analyzer.generate_report()
        print(report)
        return 1

    analyzer.check_consistency()
    report = analyzer.generate_report()

    report_name = args.report_name or f"{args.scenario}_diagnostic_report.md"
    report_path = Path(args.results_dir) / report_name
    report_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nReport saved to: {report_path}")

    return 1 if analyzer.errors else 0


if __name__ == "__main__":
    sys.exit(main())