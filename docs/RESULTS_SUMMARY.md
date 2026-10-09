# Results Summary: paper-to-file mapping

The manuscript's results come from one distributed run on Google Cloud (`cloud/gcp_run.sh`):
four Besu QBFT validators in us-central1, europe-west1, asia-south1, asia-southeast1, and one client VM
(gateway + load generator) in europe-west1, all e2-standard-2. Four architectures are measured through the same
gateway: B0 no access control, B1 static RBAC, B2 centralized zero trust (same checks as the contract, SQLite),
and the proposed BC-ZT (`AccessControlManagerV2`). Raw data and analysis are in `evaluation/results_gcp/`.

## Headline results

| Metric | B0 | B1 | B2 centralized ZT | Proposed BC-ZT |
|---|---|---|---|---|
| Attack requests denied, mean of A1-A7 | 0.0 % | 28.6 % | 85.7 % | **100 %** |
| A1-A6 | 0 % | 33.3 % | 100 % | 100 % |
| A7 trust-store tampering (repeats denied) | 0/10 | 0/10 | 0/10 | **10/10** (Fisher p = 1.1e-5) |
| Median latency, granted, 1 client | 3.9 ms | 4.0 ms | 5.6 ms | 1,980 ms |
| Median latency, granted, 200 clients | 192 ms | 151 ms | 110 ms | 5,109 ms (p95 6,575) |
| Throughput at 200 clients | 192/s | 213/s | 186/s | 37.6/s (Eq. 5 ceiling 174.5/s) |
| Open-loop mean latency (Poisson, 0.5 s gap) | 5.2 ms | 5.0 ms | 6.8 ms | 1,756 ms |
| Revocation (revoke call to first denial) | n/a | 7 ms | 7 ms | 3.5 s (1.9-4.2) |
| False-deny rate, legitimate control | 0 % | 0 % | 0 % | 0 % |

On A1-A6 the proposed design and the centralized service are identical (100 %, Fisher p = 1). The only security
difference measured is A7, and it depends on the threat model (the attacker can write to the trust store but holds no
authorized chain key). Costs of BC-ZT: ~2 s per decision, 3.5 s revocation, 832 B and 85,820 gas per decision
(about 72 MB/day at one decision per second), 349 decisions per block at most.

## Mapping

| Paper item | Source file | Regenerate with |
|---|---|---|
| Table I | literature review | n/a |
| Table II | attack scenarios A1-A7, `experiments/run_all.py` | n/a |
| Table III | policies theta = 40 / 70, `experiments/deploy_v2.js` | n/a |
| Table IV | `cloud/vm_setup.sh`, `cloud/gcp_run.sh` | n/a |
| Table V, Fig. 3 | `evaluation/results_gcp/summary_security.csv`, `security_raw.csv` | `experiments/analyze.py` |
| Table VI, Fig. 4 | `perf_raw.csv` (granted requests only: p50, p95) | `evaluation/gen_gcp_figures.py` |
| Table VII, Fig. 5 | `summary_perf.csv`, `resources_bcz_perf.csv` (from `sampler_*.csv` + `phases.csv`) | `evaluation/gen_gcp_figures.py` |
| Table VIII | `openloop_raw.csv`, `revocation_raw.csv`, `summary.json` | `experiments/analyze.py` |
| Fig. 6 | `resources_bcz_perf.csv` | `evaluation/gen_gcp_figures.py` |
| Eq. (5) numbers | `summary.json` -> `chain` (gas 85,820; 349 tx/block; 174.5/s) | `experiments/analyze.py` |

Figures: `evaluation/results_gcp/figures/`. Fig. 1 and Fig. 2 are unchanged (`evaluation/figures/`).

## Caveats that apply to this data (also in the paper)

* One deployment, five repeats (sweep), ten repeats (attacks), 30 revocation trials; intervals are between repeats.
* BC-ZT was measured in a second pass after a gateway fix (parallel receipt lookup via the same-region validator);
  B0-B2 come from the first pass (`run1_raw/`, `run2_raw/` are in the original archive; merged by `experiments/merge_runs.py`).
* B2 is rate limited in the load sweep (20 requests per device per 60 s; it ran faster than the window), grant rate
  37-48 %. Latency is therefore reported for granted requests only.
* The baselines' throughput (~190-245 req/s) is the single-process gateway, not the policy engines.
* A2: in 3 of 10 repeats the legitimate request before the revocation was denied (state left from the first pass). Attack
  requests are unaffected.
* A7 holds because B2 keeps its state in an unprotected SQLite file; a hardened or replicated centralized service was not evaluated.
* Trust decay (Eq. 1) is implemented but its effect over time was not measured; A5 applies negative evidence directly.

## Older material

`evaluation/results/` (seeded discrete-event simulation) and `evaluation/results_live/`, `live/` (single-host sandbox run)
are kept for history. They are **not** used in the current manuscript and should not be cited.
