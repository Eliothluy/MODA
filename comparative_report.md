# Comparative Analysis: RSLAQ without Optimization vs. OPT

| Metric | Scenario | No-Opt | OPT | Delta |
|---|---|---|---|---|
| avg_throughput_mbps | normal | 1.2820 | 1.1730 | -8.50% |
| avg_throughput_mbps | congestion | 1.5209 | 1.3383 | -12.01% |
| avg_throughput_mbps | insufficient_resources | 1.2304 | 1.0473 | -14.89% |
| avg_throughput_mbps | low_traffic | 0.2081 | 0.2073 | -0.36% |
| avg_throughput_mbps | stressed | 1.4774 | 1.3383 | -9.41% |
| avg_delay_ms | normal | 842.9970 | 327.3542 | -61.17% |
| avg_delay_ms | congestion | 3174.8705 | 1180.3951 | -62.82% |
| avg_delay_ms | insufficient_resources | 3283.5756 | 1227.3719 | -62.62% |
| avg_delay_ms | low_traffic | 6.5412 | 6.9144 | +5.71% |
| avg_delay_ms | stressed | 3192.7807 | 1180.3951 | -63.03% |
| avg_pdr | normal | 0.8252 | 0.8170 | -0.99% |
| avg_pdr | congestion | 0.3394 | 0.3257 | -4.04% |
| avg_pdr | insufficient_resources | 0.3168 | 0.3024 | -4.56% |
| avg_pdr | low_traffic | 0.9997 | 0.9992 | -0.05% |
| avg_pdr | stressed | 0.3367 | 0.3257 | -3.27% |
| jain_throughput | normal | 0.3505 | 0.3620 | +3.30% |
| jain_throughput | congestion | 0.6780 | 0.6177 | -8.89% |
| jain_throughput | insufficient_resources | 0.7755 | 0.6653 | -14.20% |
| jain_throughput | low_traffic | 0.7590 | 0.7556 | -0.45% |
| jain_throughput | stressed | 0.6795 | 0.6177 | -9.10% |


## Per-Slice avg_throughput_mbps

| Slice | Scenario | No-Opt | OPT | Delta |
|---|---|---|---|---|
| eMBB | normal | 4.3046 | 3.8698 | -10.10% |
| eMBB | congestion | 3.2007 | 3.1014 | -3.10% |
| eMBB | insufficient_resources | 2.3501 | 2.3337 | -0.70% |
| eMBB | low_traffic | 0.0089 | 0.0070 | -21.35% |
| eMBB | stressed | 3.1057 | 3.1014 | -0.14% |
| URLLC | normal | 0.3118 | 0.3115 | -0.10% |
| URLLC | congestion | 0.3118 | 0.3115 | -0.10% |
| URLLC | insufficient_resources | 0.6237 | 0.6229 | -0.13% |
| URLLC | low_traffic | 0.3118 | 0.3115 | -0.10% |
| URLLC | stressed | 0.3118 | 0.3115 | -0.10% |
| MTC | normal | 0.2558 | 0.2554 | -0.16% |
| MTC | congestion | 1.2855 | 0.9701 | -24.53% |
| MTC | insufficient_resources | 0.9740 | 0.6162 | -36.74% |
| MTC | low_traffic | 0.2558 | 0.2554 | -0.16% |
| MTC | stressed | 1.2460 | 0.9701 | -22.14% |


## Per-Slice avg_delay_ms

| Slice | Scenario | No-Opt | OPT | Delta |
|---|---|---|---|---|
| eMBB | normal | 3355.9590 | 1292.7276 | -61.48% |
| eMBB | congestion | 4050.6882 | 1483.9996 | -63.36% |
| eMBB | insufficient_resources | 4251.1500 | 1558.4182 | -63.34% |
| eMBB | low_traffic | 11.1430 | 12.0290 | +7.95% |
| eMBB | stressed | 4079.1154 | 1483.9996 | -63.62% |
| URLLC | normal | 5.0120 | 5.0480 | +0.72% |
| URLLC | congestion | 5.0120 | 5.0840 | +1.44% |
| URLLC | insufficient_resources | 5.0110 | 5.1210 | +2.20% |
| URLLC | low_traffic | 5.0070 | 5.0040 | -0.06% |
| URLLC | stressed | 5.0040 | 5.0840 | +1.60% |
| MTC | normal | 5.5085 | 5.8206 | +5.67% |
| MTC | congestion | 4321.8909 | 1616.2483 | -62.60% |
| MTC | insufficient_resources | 4439.0708 | 1672.9743 | -62.31% |
| MTC | low_traffic | 5.0075 | 5.3124 | +6.09% |
| MTC | stressed | 4343.5018 | 1616.2483 | -62.79% |


## Per-Slice avg_pdr

| Slice | Scenario | No-Opt | OPT | Delta |
|---|---|---|---|---|
| eMBB | normal | 0.3019 | 0.2714 | -10.09% |
| eMBB | congestion | 0.1571 | 0.1522 | -3.09% |
| eMBB | insufficient_resources | 0.1154 | 0.1145 | -0.71% |
| eMBB | low_traffic | 1.0000 | 1.0000 | +0.00% |
| eMBB | stressed | 0.1524 | 0.1522 | -0.12% |
| URLLC | normal | 0.9996 | 0.9989 | -0.07% |
| URLLC | congestion | 0.9996 | 0.9989 | -0.07% |
| URLLC | insufficient_resources | 0.9996 | 0.9986 | -0.10% |
| URLLC | low_traffic | 0.9996 | 0.9989 | -0.07% |
| URLLC | stressed | 0.9996 | 0.9989 | -0.07% |
| MTC | normal | 0.9996 | 0.9989 | -0.07% |
| MTC | congestion | 0.1004 | 0.0758 | -24.52% |
| MTC | insufficient_resources | 0.0761 | 0.0481 | -36.74% |
| MTC | low_traffic | 0.9996 | 0.9989 | -0.07% |
| MTC | stressed | 0.0974 | 0.0758 | -22.14% |

