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
Single deployment on cloud VMs; no replicated/BFT centralized baseline; A5 evidence is injected, not telemetry-derived; B3 code in the run had an unlocked audit append (6 error rows of 9,650 in the sweep), fixed in the repo afterwards.
