# Results summary (GCP run, 5 architectures, single pass)

Source: `evaluation/results_gcp/` (`tables.md` has every table; raw CSVs included). Figures: `evaluation/results_gcp/figures/` (regenerate with `python3 evaluation/gen_gcp_figures.py evaluation/results_gcp evaluation/results_gcp/figures`).

Setup: Besu 24.7.0 QBFT, 4 validators (us-central1, europe-west1, asia-south1, asia-southeast1; e2-standard-2), client e2-standard-4 in europe-west1, 2 s blocks. Architectures: B0 grant-all, B1 static RBAC, B2 centralized ZT (SQLite), B3 hardened centralized ZT (HMAC rows + hash-chained audit), BC-ZT (on-chain).

## Security (attack requests denied, %)
| | B0 | B1 | B2 | B3 | BC-ZT |
|---|---|---|---|---|---|
| A1 replay | 0 | 0 | 100 | 100 | 100 |
| A2 revoked | 0 | 100 | 100 | 100 | 100 |
| A3 flood | 0 | 0 | 100 | 100 | 100 |
| A4 lateral | 0 | 100 | 100 | 100 | 100 |
| A5 low trust | 0 | 0 | 100 | 100 | 100 |
| A6 time window | 0 | 0 | 100 | 100 | 100 |
| A7 trust-store tamper | 0 | 0 | 0 | 100 | 100 |
| A8 host compromise | 0 | 0 | 0 | 0 | 100 |
| mean | 0 | 25 | 75 | 87.5 | 100 |

A8 vs B2/B3: 10/10 vs 0/10 repeats, Fisher p = 1.1e-5. A8 is by construction (attacker lacks monitor-role key on chain). No false denies of legitimate controls.

## Performance
- BC-ZT closed-loop latency 1.997 s (1 client) to 4.67 s (200); open loop mean 1.73 s; baselines 4-6 ms at 1 client.
- BC-ZT throughput 39.0 req/s at 200 clients (Eq. 5 ceiling 174.0/s; 86,152 gas/decision, 348 tx/block, max observed block 343). Baselines 220-246 req/s (harness-limited).
- Revocation: BC-ZT 3.50 s; B1-B3 7-8 ms.
- Trust decay: stored score equals the stepwise law in 100 % of samples (tau = 6 s test); 12/12 decisions correct for B2, B3, BC-ZT.
- Scale-out (400 clients): 1 gateway 45.5, 2 gateways 56.0, 4 gateways 54.0 req/s; plateau cause not isolated.
- Ledger: 776 bytes/decision (~67 MB/day at 1 decision/s).

## Caveats
Single deployment on cloud VMs (plus one supplementary run); replicated baseline B4 is our own implementation with one admin path (no BFT database/TEE baseline); A5 evidence is injected, not telemetry-derived; B3 code in the run had an unlocked audit append (6 error rows of 9,650 in the sweep), fixed in the repo afterwards.

## Offline studies (simulation, no chain; `experiments/offline_calibration.py`, `evaluation/results_offline/`)
- Decay sensitivity (kappa, tau, theta, attestation interval): with the deployed kappa=2, tau=1 day, a silently compromised device (score 90) stays authorized 11 days at theta=70 (26 days at theta=40); tau=6 h gives 66 h (156 h) with no false denies when healthy devices attest at least every 6 h, but 74 % false denies if they attest only daily.
- Telemetry-derived evidence (synthetic vibration telemetry, EWMA detector, -20 trust per alarm, at most one per 60 s): at limit 5 sigma a 3-sigma mean shift is detected in 100 % of trials (median 195 s), device denied about 200-360 s after onset; 0.2 false alarm reports per device-day (2-6 % of healthy device-days denied); slow drift (1 sd/hour) detected in only 10 %.
- Assumptions are synthetic; these are simulations, not measurements.

## Supplementary run (`evaluation/results_gcp_supp/`; B2, B3, B4, BC-ZT on a fresh deployment, client e2-standard-8; 0 failed phases)
- B4 replicated centralized ZT (4 replicas on the validator VMs, grant only on >=3 signed granted verdicts, fail closed): denial 100 % in A1-A8, 100 % in A8b (two replica hosts compromised), 0 % in A8c (three). B2/B3/BC-ZT reproduced the first run's denial rates in every scenario.
- Latency (median, ms) at 1/10/50/100/200 clients: B3 4/31/105/110/109; B4 333/342/1747/3591/7201; BC-ZT 1969/1979/2328/3903/5226. Throughput at 200 clients: B3 308, B4 23.3, BC-ZT 35.9 req/s (B4 plateau ~22 req/s not isolated). Revocation: B3 0.006 s, B4 0.83 s, BC-ZT 3.43 s. Two legitimate B4 requests denied for lack of quorum (no-vote), fail-closed.
- Direct chain probe (pre-signed txs to one validator, 30 s each), offered -> committed/s: 20->19.9, 40->38.9, 60->48.1, 80->65.1, 120->37.3 (2,478 of 3,600 not included), 160->17.3 (3,907 of 4,800 not included). Eq. 5 ceiling 173.5/s not reached. Cause of loss under overload untested (transaction-pool limit is a candidate).
- Gateway scale-out at 400 clients: 1/2/4 gateways 54.5/41.8/51.7 req/s; stage timing (build+sign / send / wait, ms): 580/435/5094, 178/356/8129, 40/281/6517 -> the wait for the block dominates, not the gateway.
- Not captured: inter-region ping table. Trust-decay and A1-A7 for B0/B1 were not re-run (first run covers them).
- Figure: `python3 evaluation/gen_supp_figures.py evaluation/results_gcp_supp evaluation/results_gcp_supp/figures`.
