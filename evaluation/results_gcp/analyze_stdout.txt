## Load sweep (closed loop; mean over repeats, 95% CI)

| Arch | Conc. | Mean (ms) | ±CI | p50 | p95 | Max | Req/s | ±CI | Grant | Err |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 no access control | 1 | 4.0 | 0.3 | 3.9 | 4.8 | 9.7 | 245.0 | 16.6 | 1.0 | 0.0 |
| B0 no access control | 10 | 41.6 | 1.7 | 41.2 | 63.7 | 88.8 | 231.52 | 10.89 | 1.0 | 0.0 |
| B0 no access control | 50 | 220.8 | 187.0 | 161.3 | 654.0 | 1458.1 | 198.58 | 79.43 | 1.0 | 0.0 |
| B0 no access control | 100 | 294.0 | 319.6 | 184.0 | 1019.5 | 2181.2 | 194.87 | 82.56 | 1.0 | 0.0 |
| B0 no access control | 200 | 336.5 | 291.3 | 192.2 | 1376.5 | 3589.8 | 192.46 | 71.85 | 1.0 | 0.0 |
| B1 static RBAC | 1 | 4.0 | 0.1 | 4.0 | 4.6 | 5.0 | 245.32 | 9.24 | 1.0 | 0.0 |
| B1 static RBAC | 10 | 41.6 | 1.0 | 41.5 | 64.6 | 81.2 | 230.26 | 3.84 | 1.0 | 0.0 |
| B1 static RBAC | 50 | 164.3 | 10.1 | 150.9 | 309.3 | 439.5 | 216.88 | 8.06 | 1.0 | 0.0 |
| B1 static RBAC | 100 | 205.3 | 63.3 | 157.5 | 472.9 | 932.1 | 216.73 | 7.6 | 1.0 | 0.0 |
| B1 static RBAC | 200 | 235.1 | 16.2 | 151.1 | 614.4 | 1059.4 | 212.61 | 5.92 | 1.0 | 0.0 |
| B2 centralized ZT | 1 | 5.8 | 0.2 | 5.6 | 6.5 | 13.7 | 171.44 | 6.0 | 0.4 | 0.0 |
| B2 centralized ZT | 10 | 45.1 | 4.7 | 41.3 | 77.1 | 164.5 | 211.84 | 19.8 | 0.4 | 0.0 |
| B2 centralized ZT | 50 | 167.8 | 18.1 | 152.1 | 343.5 | 540.3 | 194.53 | 5.77 | 0.467 | 0.0 |
| B2 centralized ZT | 100 | 177.4 | 19.2 | 121.9 | 445.2 | 764.7 | 194.97 | 5.53 | 0.48 | 0.0 |
| B2 centralized ZT | 200 | 238.9 | 24.6 | 141.4 | 667.9 | 1304.7 | 185.89 | 5.67 | 0.368 | 0.0 |
| Proposed BC-ZT | 1 | 2008.8 | 33.4 | 1980.1 | 2090.1 | 3362.2 | 0.5 | 0.01 | 1.0 | 0.0 |
| Proposed BC-ZT | 10 | 2010.8 | 12.2 | 1998.9 | 2142.1 | 3878.0 | 4.89 | 0.22 | 1.0 | 0.0 |
| Proposed BC-ZT | 50 | 2448.5 | 116.8 | 2273.9 | 4023.9 | 4452.1 | 18.34 | 2.05 | 1.0 | 0.0 |
| Proposed BC-ZT | 100 | 3827.4 | 145.9 | 3858.0 | 4809.8 | 5262.0 | 24.68 | 0.44 | 1.0 | 0.0 |
| Proposed BC-ZT | 200 | 4892.0 | 441.9 | 5108.6 | 6575.4 | 7612.8 | 37.59 | 3.54 | 1.0 | 0.0 |

## Random arrivals (Poisson, mean gap 0.5 s)

| Arch | Requests | Mean (ms) | ±CI | p50 | p95 | Max | Grant |
|---|---|---|---|---|---|---|---|
| B0 no access control | 300 | 5.2 | 0.4 | 4.8 | 6.3 | 16.9 | 1.0 |
| B1 static RBAC | 300 | 5.0 | 0.2 | 4.9 | 6.0 | 8.7 | 1.0 |
| B2 centralized ZT | 300 | 6.8 | 0.3 | 6.6 | 8.4 | 12.0 | 0.927 |
| Proposed BC-ZT | 300 | 1755.6 | 289.9 | 1716.7 | 2667.5 | 3359.1 | 1.0 |

## Attack denial rate (Wilson 95% CI over pooled requests)

| Scenario | B0 no access control | B1 static RBAC | B2 centralized ZT | Proposed BC-ZT |
|---|---|---|---|---|
| A1 | 0.0% [0.0%, 1.9%] | 0.0% [0.0%, 1.9%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A2 | 0.0% [0.0%, 1.9%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A3 | 0.0% [0.0%, 1.0%] | 0.0% [0.0%, 1.0%] | 100.0% [99.0%, 100.0%] | 100.0% [99.0%, 100.0%] |
| A4 | 0.0% [0.0%, 1.9%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A5 | 0.0% [0.0%, 1.9%] | 0.0% [0.0%, 1.9%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A6 | 0.0% [0.0%, 1.9%] | 0.0% [0.0%, 1.9%] | 100.0% [98.1%, 100.0%] | 100.0% [98.1%, 100.0%] |
| A7 | 0.0% [0.0%, 1.9%] | 0.0% [0.0%, 1.9%] | 0.0% [0.0%, 1.9%] | 100.0% [98.1%, 100.0%] |

Mean over scenarios: B0 no access control 0.0%; B1 static RBAC 28.6%; B2 centralized ZT 85.7%; Proposed BC-ZT 100.0%

Fisher exact p, proposed vs centralized ZT: A1: 1, A2: 1, A3: 1, A4: 1, A5: 1, A6: 1, A7: 1.94e-119

Legitimate control, false-deny rate: B0 no access control 0.0%, B1 static RBAC 0.0%, B2 centralized ZT 0.0%, Proposed BC-ZT 0.0%

## Revocation latency (submit revoke -> first denied decision)

| Arch | Trials | Mean (s) | ±CI | SD | Min | Max | Timed out |
|---|---|---|---|---|---|---|---|
| B1 static RBAC | 30 | 0.007 | 0.0 | 0.001 | 0.006 | 0.009 | 0 |
| B2 centralized ZT | 30 | 0.007 | 0.0 | 0.001 | 0.007 | 0.011 | 0 |
| Proposed BC-ZT | 30 | 3.505 | 0.355 | 0.952 | 1.861 | 4.179 | 0 |

## Chain

- gas_per_granted_decision: 85819.63772020725
- block_gas_limit: 30000000
- max_tx_in_block: 171
- bytes_per_tx: 831.7623914707242
- block_period_s: 2.0
- capacity_tx_per_block: 349
- capacity_decisions_per_s: 174.5
