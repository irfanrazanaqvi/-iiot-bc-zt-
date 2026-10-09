# Distributed run on Google Cloud

Four Besu QBFT validators in four regions (Iowa, Belgium, Mumbai, Singapore) and one client VM
(e2-standard-4: up to four gateway processes + load generator + analysis) in Belgium. The same gateway serves five architectures, so the
comparison is run side by side on identical hardware:

| Path | Architecture |
|---|---|
| `/b0` | no access control |
| `/b1` | static role-based access control (in-memory role table) |
| `/b2` | centralized zero trust: same decision logic as the contract (signature, nonce, rate limit, trust, time window) in SQLite |
| `/b3` | hardened centralized ZT: B2 plus HMAC-protected state rows (key only in the decision process) and a hash-chained audit log |
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
It needs about 12 vCPUs of quota (4 x e2-standard-2 validators + 1 x e2-standard-4 client; europe-west1 holds 6 of them); override with
`VT=` / `CT=` machine types if your trial quota is lower.

## What is measured

* `perf_raw.csv`: closed-loop sweep at 1, 10, 50, 100, 200 clients, 5 repeats per architecture.
* `openloop_raw.csv`: Poisson arrivals, mean gap 0.5 s, 100 requests x 3 repeats.
* `security_raw.csv`: A1 replay, A2 revoked identity, A3 flood by an enrolled device, A4 lateral movement,
  A5 compromised sensor, A6 time window, A7 trust-store tampering (database write without the integrity key), A8 decision-host compromise (attacker holds every secret on the decision host, including the gateway signing keys), plus a legitimate control; 10 repeats.
* `decay_raw.csv`: validation of the trust-decay law (decay unit shortened to 6 s): score sampled every second against Eq. (1), and decisions before/after the threshold crossing (B2, B3, BC-ZT).
* `scale_raw.csv`: BC-ZT throughput through 1, 2 and 4 gateway processes at 200 and 400 clients.
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

* Cloud Shell disconnected: the run keeps going on the client VM. Reopen Cloud Shell and run `bash cloud/gcp_collect.sh`; it re-attaches, waits for the run to finish, collects the results, and deletes the VMs.
* Run failed part-way: `cloud/gcp_rescue.sh` resumes on the still-running VMs, keeps finished architectures, re-runs the unfinished ones, merges with `experiments/merge_runs.py`, analyzes, downloads, and deletes the VMs.

The published results (`evaluation/results_gcp/`) come from one clean pass: all five architectures, every phase completed with no retry, restart, or discarded run.

## Known caveats of the data

* Baseline throughput is bounded by the one-process gateway and the shared client VM, not by the policy engines.
* The measured B3 code had an unlocked audit-log append (decision and audit insert were not one atomic step), which produced 6 gateway-error rows out of 9,650 in the load sweep. It is fixed in `experiments/gateway_multi.py` after the run; the attack results contain no error rows.
* A8 follows from the design (the attacker lacks the monitor-role key on chain); A5 evidence is injected, not telemetry-derived.
* The cause of the BC-ZT throughput plateau (about 55 req/s with 2-4 gateways) is not isolated.
* Single deployment on cloud VMs; no replicated or fault-tolerant centralized baseline was evaluated.
