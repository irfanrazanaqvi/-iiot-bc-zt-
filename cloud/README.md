# Distributed run on Google Cloud

Four Besu QBFT validators in four regions (Iowa, Belgium, Mumbai, Singapore) and one client VM
(gateway + load generator + analysis) in Belgium. The same gateway serves four architectures, so the
comparison is run side by side on identical hardware:

| Path | Architecture |
|---|---|
| `/b0` | no access control |
| `/b1` | static role-based access control (in-memory role table) |
| `/b2` | centralized zero trust: same decision logic as the contract (signature, nonce, rate limit, trust, time window) in SQLite |
| `/bcz` | proposed: `AccessControlManagerV2` on the Besu network |

## Run it (Google Cloud Shell)

```bash
git clone https://github.com/irfanrazanaqvi/-iiot-bc-zt-.git && cd -- -iiot-bc-zt-
MODE=quick bash cloud/gcp_run.sh     # smoke test, about 15 minutes
bash cloud/gcp_run.sh                # full run, roughly 60-70 minutes
cloudshell download ~/results_gcp.tgz
```

The script creates the VMs, runs everything, analyzes the data, and deletes the VMs when it exits
(`KEEP=1` keeps them; delete them yourself afterwards to stop charges).
It needs about 10 vCPUs of quota (4 x e2-standard-2 validators + 1 x e2-standard-2 client); override with
`VT=` / `CT=` machine types if your trial quota is lower.

## What is measured

* `perf_raw.csv`: closed-loop sweep at 1, 10, 50, 100, 200 clients, 5 repeats per architecture.
* `openloop_raw.csv`: Poisson arrivals, mean gap 0.5 s, 100 requests x 3 repeats.
* `security_raw.csv`: A1 replay, A2 revoked identity, A3 flood by an enrolled device, A4 lateral movement,
  A5 compromised sensor, A6 time window, A7 trust-store tampering, plus a legitimate control; 10 repeats.
* `revocation_raw.csv`: 30 trials (time from the revoke call to the first denied decision).
* `sampler_*.csv`: CPU and memory per VM, aligned to the phases in `phases.csv`.
* `summary.json`, `tables.md`, `summary_*.csv`: means with 95 % confidence intervals, Wilson intervals for denial
  rates, Mann-Whitney and Fisher tests (`experiments/analyze.py`).

## Local replication (no cloud)

```bash
live/start_besu_native.sh /tmp/besu2
DEPLOYER_PRIVATE_KEY=0x<key> node experiments/deploy_v2.js
GATEWAY_SEED=x uvicorn experiments.gateway_multi:app --port 9000 &
ADMIN_PRIVATE_KEY=0x<key> python3 -m experiments.run_all --out results_local --quick
python3 experiments/analyze.py results_local
```

## If the run is interrupted

`cloud/gcp_rescue.sh` resumes on the still-running VMs: it keeps finished architectures, re-runs the unfinished ones
(always BC-ZT), merges with `experiments/merge_runs.py`, analyzes, downloads, and deletes the VMs. The published results
were produced this way (all four architectures in a first pass; BC-ZT re-run after the receipt-lookup fix).

## Known caveats of the data

* B2 hits its 20-requests-per-60-s limiter in the load sweep (it finishes each level inside one window), so its grant
  rate there is 37-48 %; compare latency on granted requests only.
* In the A2 test of BC-ZT, the legitimate request before the revocation was denied in repeats 0-2 (state left over from
  the first pass); attack requests are unaffected.
* Baseline throughput is bounded by the one-process gateway, not by the policy engines.
