# Live Besu QBFT experiments

These results were measured on a **real 4-validator Hyperledger Besu 24.7.0 QBFT network** (2 s block period,
30,000,000 block gas limit, `evmVersion=london`), with the three Solidity contracts deployed on it and every
decision issued as a real signed transaction through `live/gateway_live.py` (the PEP). They complement the
seeded simulation in `evaluation/results/`.

**Test host:** one cloud sandbox with **2 vCPUs / 7 GB RAM** running all four validator JVMs (700 MB heap each),
the gateway, and the load generator together. Absolute throughput and CPU are therefore a lower bound for
what dedicated hardware would give. Single run per configuration, no confidence intervals.

## Reproduce
```bash
live/start_besu_native.sh                      # 4 validators without Docker (needs Java 21)
npm install
RPC_URL=http://127.0.0.1:8545 DEPLOYER_PRIVATE_KEY=0x<key> node live/deploy_live.js 200
GATEWAY_PRIVATE_KEY=0x<key> uvicorn live.gateway_live:app --port 9000 &
ADMIN_PRIVATE_KEY=0x<deployer key> python3 live/run_live_experiments.py
python3 live/run_open_loop.py
```
(`pip install fastapi uvicorn web3 psutil requests`.)

## Load sweep (closed loop: each worker sends its next request when the previous reply arrives)
| Conc. | Requests | Mean (ms) | p50 | p95 | Max | Throughput (req/s) | Grant rate | Errors | Validator CPU % | Gateway CPU % |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 30 | 1953.36 | 1992.88 | 2033.93 | 2108.48 | 0.51 | 1.0 | 0.0 | 8.9 | 0 |
| 5 | 50 | 1971.97 | 1962.77 | 2088.8 | 2163.26 | 2.52 | 1.0 | 0.0 | 14.8 | 5.2 |
| 10 | 100 | 1985.24 | 1975.23 | 2258.74 | 2390.81 | 5.01 | 1.0 | 0.0 | 17.1 | 8.2 |
| 20 | 200 | 1984.64 | 1964.68 | 2412.51 | 2650.44 | 9.96 | 1.0 | 0.0 | 24.6 | 13.7 |
| 50 | 300 | 2302.92 | 2196.81 | 3722.35 | 4296.64 | 20.77 | 1.0 | 0.0 | 38.9 | 24.0 |
| 100 | 500 | 3643.23 | 3657.0 | 5466.89 | 6008.81 | 25.94 | 1.0 | 0.0 | 37.1 | 30.0 |
| 200 | 1000 | 6432.76 | 6392.7 | 8682.71 | 9480.12 | 29.24 | 1.0 | 0.0 | 37.8 | 35.0 |

Closed-loop latency sits at about 2.0 s because every worker's next request lands just after a block was sealed
and waits a full block period. Under **random (Poisson) arrivals** that look like real periodic devices
(200 requests, mean gap 0.5 s) latency is **mean 1241.1 ms, p50 1333.8 ms,
p95 2079.9 ms, max 2257.9 ms**, grant rate 1.0.

Throughput saturated near 26-29 req/s at 100-200 concurrent clients on this 2-vCPU host with zero errors;
latency rose to 3.6 s (100) and 6.4 s (200) most likely from queueing in the single Python gateway process and CPU
contention on the shared host (not isolated here); the chain itself was not full: blocks held at most 165 decision transactions.

## Security scenarios the contracts can enforce (live)
| Scenario | Outcome (denial rate, n) | On-chain reason |
|---|---|---|
| A2 revoked device continues | 100% (n=20) | identity-invalid |
| A3 flood by unenrolled identities | 100% (n=300) | identity-invalid |
| A4 lateral move (resource without policy) | 100% (n=20) | no-policy |
| A4 lateral move (higher-tier resource, theta=70, score 50) | 100% (n=20) | insufficient-trust |
| A5 compromised sensor (trust driven below theta) | 100% (n=20) | insufficient-trust |
| Control: legitimate device | 0% (n=20) | granted |
| A6 outside permitted time window | 100% (n=20) | outside-time-window |

A1 (replay) is **not** testable: `AccessControlManager` verifies no signature or nonce, so replay is not
enforced on-chain in this prototype. Flooding (A3) is only "denied" because the flooders are unenrolled; the
contracts have no rate limiting, so a flood by enrolled devices would be granted.

## Other measurements
- Gas per decision: **48833** (granted); about 36,600 for a denial. The simulation assumed 65,000.
- Capacity from Eq. (5) with the measured gas: floor(30,000,000 / 48,833) = 614 decisions per block, about 307 per second at B = 2 s.
- Revocation (30 trials): time from submitting the revoke transaction until the first denied decision was received by the client:
  **mean 4.04 s (sd 0.06, range 3.9-4.12)**. This is about two block periods: one for the revoke transaction, one for the next decision.
- Ledger bytes per decision transaction (block size / transactions): about 882.2 B (the simulation assumed 380 B per event).

Raw files: `evaluation/results_live/live_perf.csv`, `live_cpu_mem.csv`, `live_security.json`, `live_misc.json`, `live_openloop.json`.
