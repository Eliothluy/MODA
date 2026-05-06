# RSLAQ Diagnostic Report

**Scenario:** `congestion`
**Results directory:** `/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_rslaq`

## Summary

- Total UE mappings: **20**
- UE KPI rows: **20**
- Slice KPI rows: **3**
- Slice allocation records: **297**
- UE detail records: **10494**
- Unmapped RNTI records: **0**
- Errors: **0**
- Warnings: **45**

**Conclusion:** ⚠️ Checks passed with warnings.

## Slice KPIs

| Slice | TX pkts | RX pkts | FlowMonitor lost | Effective lost | Throughput Mbps | Reported PDR | Effective PDR | Avg delay ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| eMBB | 79995 | 12568 | 0 | 67427 | 16.0033 | 0.157100 | 0.157100 | 4050.6890 |
| URLLC | 23995 | 23985 | 0 | 10 | 1.5590 | 0.999600 | 0.999600 | 5.0120 |
| MTC | 1199990 | 120515 | 0 | 1079475 | 12.8549 | 0.100400 | 0.100400 | 4321.8900 |

## Slice Allocation Summary

| Slice | Records | Active rows | Demand rows | Total budget RBG | Total allocated RBG | Zero alloc with demand | Budget>0 but alloc=0 | Avg active UEs | Avg effective weight | Top reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| eMBB | 99 | 99 | 99 | 2283 | 2283 | 0 | 0 | 5.00 | 0.4455 | full_alloc:99 |
| URLLC | 99 | 49 | 49 | 1029 | 1029 | 0 | 0 | 2.47 | 0.1980 | no_active_ues:50, full_alloc:49 |
| MTC | 99 | 99 | 99 | 1935 | 1935 | 0 | 0 | 10.00 | 0.3565 | full_alloc:99 |

## TX/RX/Allocation Diagnosis

| Slice | Diagnosis |
|---|---|
| eMBB | Functional path: TX>0, RX>0, and allocatedRbg>0. |
| URLLC | Functional path: TX>0, RX>0, and allocatedRbg>0. |
| MTC | Functional path: TX>0, RX>0, and allocatedRbg>0. |

## UE/RNTI Mapping

| UE ID | IMSI | RNTI | Slice ID | Slice | IP | Port |
|---:|---:|---:|---:|---|---|---:|
| 1 | 1 | 1 | 0 | eMBB | 7.0.0.2 | 12001 |
| 2 | 2 | 2 | 0 | eMBB | 7.0.0.3 | 12002 |
| 3 | 3 | 3 | 0 | eMBB | 7.0.0.4 | 12003 |
| 4 | 4 | 4 | 0 | eMBB | 7.0.0.5 | 12004 |
| 5 | 5 | 5 | 0 | eMBB | 7.0.0.6 | 12005 |
| 6 | 6 | 21 | 1 | URLLC | 7.0.0.7 | 12006 |
| 7 | 7 | 22 | 1 | URLLC | 7.0.0.8 | 12007 |
| 8 | 8 | 23 | 1 | URLLC | 7.0.0.9 | 12008 |
| 9 | 9 | 24 | 1 | URLLC | 7.0.0.10 | 12009 |
| 10 | 10 | 25 | 1 | URLLC | 7.0.0.11 | 12010 |
| 11 | 11 | 26 | 2 | MTC | 7.0.0.12 | 12011 |
| 12 | 12 | 36 | 2 | MTC | 7.0.0.13 | 12012 |
| 13 | 13 | 37 | 2 | MTC | 7.0.0.14 | 12013 |
| 14 | 14 | 38 | 2 | MTC | 7.0.0.15 | 12014 |
| 15 | 15 | 39 | 2 | MTC | 7.0.0.16 | 12015 |
| 16 | 16 | 40 | 2 | MTC | 7.0.0.17 | 12016 |
| 17 | 17 | 45 | 2 | MTC | 7.0.0.18 | 12017 |
| 18 | 18 | 46 | 2 | MTC | 7.0.0.19 | 12018 |
| 19 | 19 | 47 | 2 | MTC | 7.0.0.20 | 12019 |
| 20 | 20 | 48 | 2 | MTC | 7.0.0.21 | 12020 |

## Warnings

- ⚠️ UE 1: effective_pdr=0.157100, expected=0.157135
- ⚠️ UE 1: reported lost_packets=0, effective_lost_packets=13485. Use effective_lost_packets for diagnostics.
- ⚠️ UE 2: effective_pdr=0.157100, expected=0.157135
- ⚠️ UE 2: reported lost_packets=0, effective_lost_packets=13485. Use effective_lost_packets for diagnostics.
- ⚠️ UE 3: effective_pdr=0.157000, expected=0.157010
- ⚠️ UE 3: reported lost_packets=0, effective_lost_packets=13487. Use effective_lost_packets for diagnostics.
- ⚠️ UE 4: effective_pdr=0.157100, expected=0.157135
- ⚠️ UE 4: reported lost_packets=0, effective_lost_packets=13485. Use effective_lost_packets for diagnostics.
- ⚠️ UE 5: effective_pdr=0.157100, expected=0.157135
- ⚠️ UE 5: reported lost_packets=0, effective_lost_packets=13485. Use effective_lost_packets for diagnostics.
- ⚠️ UE 6: effective_pdr=0.999600, expected=0.999583
- ⚠️ UE 6: reported lost_packets=0, effective_lost_packets=2. Use effective_lost_packets for diagnostics.
- ⚠️ UE 7: effective_pdr=0.999600, expected=0.999583
- ⚠️ UE 7: reported lost_packets=0, effective_lost_packets=2. Use effective_lost_packets for diagnostics.
- ⚠️ UE 8: effective_pdr=0.999600, expected=0.999583
- ⚠️ UE 8: reported lost_packets=0, effective_lost_packets=2. Use effective_lost_packets for diagnostics.
- ⚠️ UE 9: effective_pdr=0.999600, expected=0.999583
- ⚠️ UE 9: reported lost_packets=0, effective_lost_packets=2. Use effective_lost_packets for diagnostics.
- ⚠️ UE 10: effective_pdr=0.999600, expected=0.999583
- ⚠️ UE 10: reported lost_packets=0, effective_lost_packets=2. Use effective_lost_packets for diagnostics.
- ⚠️ UE 11: reported lost_packets=0, effective_lost_packets=107927. Use effective_lost_packets for diagnostics.
- ⚠️ UE 12: effective_pdr=0.100500, expected=0.100543
- ⚠️ UE 12: reported lost_packets=0, effective_lost_packets=107934. Use effective_lost_packets for diagnostics.
- ⚠️ UE 13: effective_pdr=0.100500, expected=0.100476
- ⚠️ UE 13: reported lost_packets=0, effective_lost_packets=107942. Use effective_lost_packets for diagnostics.
- ⚠️ UE 14: effective_pdr=0.100400, expected=0.100434
- ⚠️ UE 14: reported lost_packets=0, effective_lost_packets=107947. Use effective_lost_packets for diagnostics.
- ⚠️ UE 15: effective_pdr=0.100400, expected=0.100368
- ⚠️ UE 15: reported lost_packets=0, effective_lost_packets=107955. Use effective_lost_packets for diagnostics.
- ⚠️ UE 16: effective_pdr=0.100200, expected=0.100234
- ⚠️ UE 16: reported lost_packets=0, effective_lost_packets=107971. Use effective_lost_packets for diagnostics.
- ⚠️ UE 17: effective_pdr=0.100400, expected=0.100426
- ⚠️ UE 17: reported lost_packets=0, effective_lost_packets=107948. Use effective_lost_packets for diagnostics.
- ⚠️ UE 18: effective_pdr=0.100400, expected=0.100426
- ⚠️ UE 18: reported lost_packets=0, effective_lost_packets=107948. Use effective_lost_packets for diagnostics.
- ⚠️ UE 19: effective_pdr=0.100400, expected=0.100368
- ⚠️ UE 19: reported lost_packets=0, effective_lost_packets=107955. Use effective_lost_packets for diagnostics.
- ⚠️ UE 20: effective_pdr=0.100400, expected=0.100426
- ⚠️ UE 20: reported lost_packets=0, effective_lost_packets=107948. Use effective_lost_packets for diagnostics.
- ⚠️ Slice eMBB: effective_pdr=0.157100, expected=0.157110
- ⚠️ Slice eMBB: reported lost_packets=0, effective_lost_packets=67427. Use effective_lost_packets for diagnostics.
- ⚠️ Slice URLLC: effective_pdr=0.999600, expected=0.999583
- ⚠️ Slice URLLC: reported lost_packets=0, effective_lost_packets=10. Use effective_lost_packets for diagnostics.
- ⚠️ Slice MTC: effective_pdr=0.100400, expected=0.100430
- ⚠️ Slice MTC: reported lost_packets=0, effective_lost_packets=1079475. Use effective_lost_packets for diagnostics.

## Information

- Loaded 20 UE mappings
- Loaded 20 UE KPI rows
- Loaded 3 slice KPI rows
- Loaded 297 slice allocation records
- Loaded 10494 UE detail records
- Loaded 0 unmapped RNTI records
- Check UE -> Slice aggregation
- Check slice RBG allocation for slices with RX > 0
- Slice MTC: RX>0 and allocatedRbg=1935 (OK)
- Slice URLLC: RX>0 and allocatedRbg=1029 (OK)
- Slice eMBB: RX>0 and allocatedRbg=2283 (OK)
- Check UE detail coverage for RNTIs with RX > 0
- RNTIs with RX>0: 20
- RNTIs with rbgAllocated>0 in ue_detail: 20
- Check RNTI mapping coverage
- Check explicit unmapped RNTIs
- No unmapped RNTIs found (OK)
- Check effective loss and PDR metrics
- Build slice allocation summary
- Diagnose TX/RX/allocation per slice
- eMBB: Functional path: TX>0, RX>0, and allocatedRbg>0.
- URLLC: Functional path: TX>0, RX>0, and allocatedRbg>0.
- MTC: Functional path: TX>0, RX>0, and allocatedRbg>0.
