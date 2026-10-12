## Load sweep (closed loop; mean over repeats, 95% CI)

| Arch | Conc. | Mean (ms) | ±CI | p50 | p95 | Max | Req/s | ±CI | Grant | Err | Granted-only p50 | p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B2 centralized ZT | 1 | 5.1 | 0.8 | 4.9 | 6.5 | 14.2 | 195.07 | 31.08 | 1.0 | 0.0 | 4.9 | 6.5 |
| B2 centralized ZT | 10 | 35.2 | 3.7 | 34.3 | 52.5 | 67.0 | 267.23 | 30.13 | 1.0 | 0.0 | 34.3 | 52.5 |
| B2 centralized ZT | 50 | 120.6 | 21.0 | 113.0 | 236.2 | 369.1 | 277.39 | 32.23 | 1.0 | 0.0 | 113.0 | 236.2 |
| B2 centralized ZT | 100 | 131.6 | 16.7 | 106.9 | 285.7 | 453.4 | 281.59 | 14.21 | 1.0 | 0.0 | 106.9 | 285.7 |
| B2 centralized ZT | 200 | 161.7 | 11.4 | 114.8 | 389.5 | 724.6 | 283.04 | 1.94 | 1.0 | 0.0 | 114.8 | 389.5 |
| B3 hardened ZT | 1 | 4.0 | 1.1 | 3.9 | 5.2 | 6.9 | 252.23 | 68.46 | 1.0 | 0.0 | 3.9 | 5.2 |
| B3 hardened ZT | 10 | 31.1 | 1.9 | 30.8 | 43.9 | 56.3 | 302.35 | 21.91 | 1.0 | 0.0 | 30.8 | 43.9 |
| B3 hardened ZT | 50 | 112.9 | 16.3 | 105.0 | 209.4 | 331.2 | 302.74 | 6.55 | 1.0 | 0.0 | 105.0 | 209.4 |
| B3 hardened ZT | 100 | 129.3 | 16.4 | 110.1 | 265.8 | 488.6 | 299.61 | 18.85 | 1.0 | 0.0 | 110.1 | 265.8 |
| B3 hardened ZT | 200 | 151.6 | 36.6 | 109.3 | 359.6 | 665.5 | 308.15 | 8.4 | 1.0 | 0.0 | 109.3 | 359.6 |
| B4 replicated ZT (4 replicas, quorum 3) | 1 | 339.5 | 11.6 | 333.1 | 345.5 | 699.5 | 2.95 | 0.1 | 1.0 | 0.0 | 333.1 | 345.5 |
| B4 replicated ZT (4 replicas, quorum 3) | 10 | 368.5 | 15.3 | 341.6 | 673.0 | 706.5 | 26.1 | 1.04 | 1.0 | 0.0 | 341.6 | 673.0 |
| B4 replicated ZT (4 replicas, quorum 3) | 50 | 2181.3 | 95.0 | 1754.9 | 5018.1 | 8237.8 | 21.47 | 0.55 | 0.998 | 0.0 | 1746.5 | 5004.8 |
| B4 replicated ZT (4 replicas, quorum 3) | 100 | 4080.2 | 205.0 | 3591.3 | 8984.7 | 17911.1 | 21.73 | 2.53 | 1.0 | 0.0 | 3591.3 | 8984.7 |
| B4 replicated ZT (4 replicas, quorum 3) | 200 | 7676.4 | 79.7 | 7200.7 | 16133.1 | 30063.6 | 23.27 | 1.6 | 1.0 | 0.0 | 7200.7 | 16133.1 |
| Proposed BC-ZT | 1 | 1979.6 | 39.8 | 1969.4 | 2078.3 | 2163.9 | 0.51 | 0.01 | 1.0 | 0.0 | 1969.4 | 2078.3 |
| Proposed BC-ZT | 10 | 2010.6 | 20.6 | 1979.4 | 2206.5 | 2261.6 | 4.97 | 0.05 | 1.0 | 0.0 | 1979.4 | 2206.5 |
| Proposed BC-ZT | 50 | 2984.2 | 3248.2 | 2327.9 | 7105.0 | 9957.0 | 16.82 | 13.65 | 1.0 | 0.0 | 2327.9 | 7105.0 |
| Proposed BC-ZT | 100 | 3842.1 | 319.8 | 3902.7 | 4475.7 | 4774.8 | 25.53 | 1.75 | 1.0 | 0.0 | 3902.7 | 4475.7 |
| Proposed BC-ZT | 200 | 5096.7 | 137.4 | 5226.2 | 6701.6 | 8780.4 | 35.93 | 2.86 | 1.0 | 0.0 | 5226.2 | 6701.6 |

## Random arrivals (Poisson, mean gap 0.5 s)

| Arch | Requests | Mean (ms) | ±CI | p50 | p95 | Max | Grant |
|---|---|---|---|---|---|---|---|
| B2 centralized ZT | 300 | 5.4 | 0.8 | 5.1 | 7.3 | 14.4 | 1.0 |
| B3 hardened ZT | 300 | 5.3 | 0.2 | 5.2 | 6.2 | 10.4 | 1.0 |
| B4 replicated ZT (4 replicas, quorum 3) | 300 | 347.1 | 9.3 | 333.0 | 371.6 | 771.3 | 0.997 |
| Proposed BC-ZT | 300 | 1752.1 | 227.7 | 1739.8 | 2651.6 | 3133.5 | 1.0 |

## Attack denial rate (Wilson 95% CI over pooled requests)

| Scenario | B2 centralized ZT | B3 hardened ZT | B4 replicated ZT (4 replicas, quorum 3) | Proposed BC-ZT |
|---|---|---|---|---|
| A1 | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A2 | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A3 | 100.0% [99.0%, 100.0%] | 100.0% [99.0%, 100.0%] | 100.0% [99.0%, 100.0%] | 100.0% [99.0%, 100.0%] |
| A4 | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A5 | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A6 | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A7 | 0.0% [0.0%, 1.9%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A8 | 0.0% [0.0%, 1.9%] | 0.0% [0.0%, 1.9%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A8b | n/a | n/a | 100.0% [98.1%, 100.0%] | n/a |
| A8c | n/a | n/a | 0.0% [0.0%, 1.9%] | n/a |

Mean over scenarios: B2 centralized ZT 75.0%; B3 hardened ZT 87.5%; B4 replicated ZT (4 replicas, quorum 3) 100.0%; Proposed BC-ZT 100.0%

Fisher exact, proposed vs centralized (repeat-level is the valid unit; pooled treats requests as independent):

| Scenario | vs | proposed repeats fully denied | other repeats fully denied | repeat-level p | pooled p |
|---|---|---|---|---|---|
| A1 | B2 centralized ZT | 10/10 | 10/10 | 1 | 1 |
| A2 | B2 centralized ZT | 10/10 | 10/10 | 1 | 1 |
| A3 | B2 centralized ZT | 10/10 | 10/10 | 1 | 1 |
| A4 | B2 centralized ZT | 10/10 | 10/10 | 1 | 1 |
| A5 | B2 centralized ZT | 10/10 | 10/10 | 1 | 1 |
| A6 | B2 centralized ZT | 10/10 | 10/10 | 1 | 1 |
| A7 | B2 centralized ZT | 10/10 | 0/10 | 1.08e-05 | 1.94e-119 |
| A8 | B2 centralized ZT | 10/10 | 0/10 | 1.08e-05 | 1.94e-119 |
| A1 | B3 hardened ZT | 10/10 | 10/10 | 1 | 1 |
| A2 | B3 hardened ZT | 10/10 | 10/10 | 1 | 1 |
| A3 | B3 hardened ZT | 10/10 | 10/10 | 1 | 1 |
| A4 | B3 hardened ZT | 10/10 | 10/10 | 1 | 1 |
| A5 | B3 hardened ZT | 10/10 | 10/10 | 1 | 1 |
| A6 | B3 hardened ZT | 10/10 | 10/10 | 1 | 1 |
| A7 | B3 hardened ZT | 10/10 | 10/10 | 1 | 1 |
| A8 | B3 hardened ZT | 10/10 | 0/10 | 1.08e-05 | 1.94e-119 |
| A1 | B4 replicated ZT (4 replicas, quorum 3) | 10/10 | 10/10 | 1 | 1 |
| A2 | B4 replicated ZT (4 replicas, quorum 3) | 10/10 | 10/10 | 1 | 1 |
| A3 | B4 replicated ZT (4 replicas, quorum 3) | 10/10 | 10/10 | 1 | 1 |
| A4 | B4 replicated ZT (4 replicas, quorum 3) | 10/10 | 10/10 | 1 | 1 |
| A5 | B4 replicated ZT (4 replicas, quorum 3) | 10/10 | 10/10 | 1 | 1 |
| A6 | B4 replicated ZT (4 replicas, quorum 3) | 10/10 | 10/10 | 1 | 1 |
| A7 | B4 replicated ZT (4 replicas, quorum 3) | 10/10 | 10/10 | 1 | 1 |
| A8 | B4 replicated ZT (4 replicas, quorum 3) | 10/10 | 10/10 | 1 | 1 |

Legitimate control, false-deny rate: B2 centralized ZT 0.0%, B3 hardened ZT 0.0%, B4 replicated ZT (4 replicas, quorum 3) 0.0%, Proposed BC-ZT 0.0%

## Revocation latency (submit revoke -> first denied decision)

| Arch | Trials | Mean (s) | ±CI | SD | Min | Max | Timed out |
|---|---|---|---|---|---|---|---|
| B2 centralized ZT | 30 | 0.006 | 0.0 | 0.001 | 0.005 | 0.008 | 0 |
| B3 hardened ZT | 30 | 0.006 | 0.0 | 0.001 | 0.005 | 0.008 | 0 |
| B4 replicated ZT (4 replicas, quorum 3) | 30 | 0.829 | 0.021 | 0.057 | 0.725 | 0.901 | 0 |
| Proposed BC-ZT | 30 | 3.426 | 0.373 | 0.999 | 1.851 | 4.149 | 0 |

## Chain

- gas_per_granted_decision: 86388.31986183074
- block_gas_limit: 30000000
- max_tx_in_block: 343
- bytes_per_tx: 758.8703515916853
- block_period_s: 2.0
- capacity_tx_per_block: 347
- capacity_decisions_per_s: 173.5

## Trust-decay validation (score vs Eq. 1; decision before/after crossing theta)

| Arch | Samples | Score == Eq. 1 | Max abs deviation | Steps seen | Decisions correct |
|---|---|---|---|---|---|

## Gateway scale-out (BC-ZT, closed loop)

| Gateways | Clients | Req/s | ±CI | Mean latency (ms) | p95 | Grant |
|---|---|---|---|---|---|---|
| 1 | 400 | 54.5 | 1.7 | 6819 | 9682 | 1.000 |
| 2 | 400 | 41.8 | 16.5 | 9052 | 24784 | 1.000 |
| 4 | 400 | 51.7 | 4.4 | 7205 | 10056 | 1.000 |

## Direct chain probe (pre-signed transactions at a fixed offered rate; no gateway)

| Offered (tx/s) | Sent | Committed in window | Committed/s | Committed total | Max block tx | Mean block tx | Latency p50 (s) | p95 | Not included |
|---|---|---|---|---|---|---|---|---|---|
| 20 | 600 | 600 | 19.9 | 600 | 44 | 40.0 | 1.05 | 1.95 | 0 |
| 40 | 1200 | 1171 | 38.9 | 1200 | 86 | 75.0 | 1.04 | 1.95 | 0 |
| 60 | 1800 | 1448 | 48.1 | 1800 | 343 | 180.0 | 2.2 | 8.46 | 0 |
| 80 | 2400 | 1961 | 65.1 | 2400 | 343 | 240.0 | 2.54 | 9.04 | 0 |
| 120 | 3600 | 1122 | 37.3 | 1122 | 343 | 280.5 | 1.84 | 6.95 | 2478 |
| 160 | 4800 | 521 | 17.3 | 893 | 212 | 148.8 | 13.89 | 34.19 | 3907 |

## Gateway stage timing, BC-ZT scale-out (mean ms: build+sign, send, wait for block, total round trip)

| Gateways | Clients | Build+sign | Send | Wait for block | Round trip |
|---|---|---|---|---|---|
| 1 | 400 | 580 | 435 | 5094 | 6819 |
| 2 | 400 | 178 | 356 | 8129 | 9052 |
| 4 | 400 | 40 | 281 | 6517 | 7205 |
