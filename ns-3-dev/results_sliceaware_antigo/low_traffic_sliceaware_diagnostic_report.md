# SliceAware Diagnostic Report

**Scenario:** `low_traffic`
**Results directory:** `/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_sliceaware`

## Summary

- Total UE mappings: **20**
- UE KPI rows: **20**
- Slice KPI rows: **3**
- Slice allocation records: **297**
- UE detail records: **52668**
- Unmapped RNTI records: **0**
- Errors: **0**
- Warnings: **12**

**Conclusion:** :warning: Checks passed with warnings.

## Slice KPIs

| Slice | TX pkts | RX pkts | FlowMonitor lost | Effective lost | Throughput Mbps | Reported PDR | Effective PDR | Avg delay ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| eMBB | 3995 | 3995 | 0 | 0 | 5.0870 | 1.000000 | 1.000000 | 3.1650 |
| URLLC | 23995 | 23990 | 0 | 5 | 1.5594 | 0.999800 | 0.999800 | 3.0550 |
| MTC | 23990 | 23990 | 0 | 0 | 2.5589 | 1.000000 | 1.000000 | 3.0570 |

## Slice Allocation Summary

| Slice | Records | Active rows | Demand rows | Total budget RBG | Total allocated RBG | Max cumul RBG | Zero alloc w/ demand | Budget>0 but alloc=0 | Avg active UEs | Avg effective weight | Top reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| eMBB | 99 | 20 | 20 | 2650 | 2650 | 113138 | 0 | 0 | 1.01 | 0.3333 | no_active_ues_guaranteed:79, full_alloc:20 |
| URLLC | 99 | 94 | 94 | 19148 | 19148 | 975628 | 0 | 0 | 4.75 | 0.4000 | full_alloc:94, no_active_ues_guaranteed:5 |
| MTC | 99 | 47 | 47 | 4536 | 4536 | 230328 | 0 | 0 | 4.75 | 0.2667 | no_active_ues_guaranteed:52, full_alloc:47 |

## TX/RX/Allocation Diagnosis

| Slice | Diagnosis |
|---|---|
| eMBB | Functional path: TX>0, RX>0, and cumulAllocRbg=113138. |
| URLLC | Functional path: TX>0, RX>0, and cumulAllocRbg=975628. |
| MTC | Functional path: TX>0, RX>0, and cumulAllocRbg=230328. |

## UE/RNTI Mapping

| UE ID | IMSI | RNTI | Slice ID | Slice | IP | Port |
|---:|---:|---:|---:|---|---|---:|
| 1 | 1 | 1 | 0 | eMBB | 7.0.0.2 | 12001 |
| 2 | 2 | 2 | 0 | eMBB | 7.0.0.3 | 12002 |
| 3 | 3 | 3 | 0 | eMBB | 7.0.0.4 | 12003 |
| 4 | 4 | 4 | 0 | eMBB | 7.0.0.5 | 12004 |
| 5 | 5 | 5 | 0 | eMBB | 7.0.0.6 | 12005 |
| 6 | 6 | 6 | 1 | URLLC | 7.0.0.7 | 12006 |
| 7 | 7 | 7 | 1 | URLLC | 7.0.0.8 | 12007 |
| 8 | 8 | 8 | 1 | URLLC | 7.0.0.9 | 12008 |
| 9 | 9 | 9 | 1 | URLLC | 7.0.0.10 | 12009 |
| 10 | 10 | 10 | 1 | URLLC | 7.0.0.11 | 12010 |
| 11 | 11 | 11 | 2 | MTC | 7.0.0.12 | 12011 |
| 12 | 12 | 12 | 2 | MTC | 7.0.0.13 | 12012 |
| 13 | 13 | 21 | 2 | MTC | 7.0.0.14 | 12013 |
| 14 | 14 | 22 | 2 | MTC | 7.0.0.15 | 12014 |
| 15 | 15 | 23 | 2 | MTC | 7.0.0.16 | 12015 |
| 16 | 16 | 24 | 2 | MTC | 7.0.0.17 | 12016 |
| 17 | 17 | 25 | 2 | MTC | 7.0.0.18 | 12017 |
| 18 | 18 | 26 | 2 | MTC | 7.0.0.19 | 12018 |
| 19 | 19 | 27 | 2 | MTC | 7.0.0.20 | 12019 |
| 20 | 20 | 28 | 2 | MTC | 7.0.0.21 | 12020 |

## Warnings

- :warning: UE 6: effective_pdr=0.999800, expected=0.999792
- :warning: UE 6: reported lost_packets=0, effective_lost_packets=1. Use effective_lost_packets for diagnostics.
- :warning: UE 7: effective_pdr=0.999800, expected=0.999792
- :warning: UE 7: reported lost_packets=0, effective_lost_packets=1. Use effective_lost_packets for diagnostics.
- :warning: UE 8: effective_pdr=0.999800, expected=0.999792
- :warning: UE 8: reported lost_packets=0, effective_lost_packets=1. Use effective_lost_packets for diagnostics.
- :warning: UE 9: effective_pdr=0.999800, expected=0.999792
- :warning: UE 9: reported lost_packets=0, effective_lost_packets=1. Use effective_lost_packets for diagnostics.
- :warning: UE 10: effective_pdr=0.999800, expected=0.999792
- :warning: UE 10: reported lost_packets=0, effective_lost_packets=1. Use effective_lost_packets for diagnostics.
- :warning: Slice URLLC: effective_pdr=0.999800, expected=0.999792
- :warning: Slice URLLC: reported lost_packets=0, effective_lost_packets=5. Use effective_lost_packets for diagnostics.

## Information

- Loaded 20 UE mappings
- Loaded 20 UE KPI rows
- Loaded 3 slice KPI rows
- Loaded 297 slice allocation records
- Loaded 52668 UE detail records
- Loaded 0 unmapped RNTI records
- Check UE -> Slice aggregation
- Check slice RBG allocation for slices with RX > 0
- Slice MTC: RX>0 and cumulAllocRbg=230328 (OK)
- Slice URLLC: RX>0 and cumulAllocRbg=975628 (OK)
- Slice eMBB: RX>0 and cumulAllocRbg=113138 (OK)
- Check UE detail coverage for RNTIs with RX > 0
- RNTIs with RX>0: 20
- RNTIs with rbgAllocated>0 in ue_detail: 20
- Check RNTI mapping coverage
- Check explicit unmapped RNTIs
- No unmapped RNTIs found (OK)
- Check effective loss and PDR metrics
- Build slice allocation summary
- Diagnose TX/RX/allocation per slice
- eMBB: Functional path: TX>0, RX>0, and cumulAllocRbg=113138.
- URLLC: Functional path: TX>0, RX>0, and cumulAllocRbg=975628.
- MTC: Functional path: TX>0, RX>0, and cumulAllocRbg=230328.
