# Results Summary — Paper-to-File Mapping

Every quantitative table and figure in the current manuscript (ACS-format version of *A
Blockchain-Based Zero-Trust Architecture for Secure Industrial Internet of Things (IIoT)*)
traces to a file in this repository. Numbering below follows the ACS manuscript
(Arabic figure numbers, Roman table numbers).

## Headline results (regenerate with `python evaluation/analyze_results.py`)

| Metric | B0 No ACL | B1 Static RBAC | B2 Centralized ZT | Proposed BC-ZT |
|---|---|---|---|---|
| Mean correct-denial rate, A1-A6 | 3.5 % | 56.2 % | 85.0 % | **95.6 %** |
| Proposed gain, mean (per-scenario range) | +92.1 pp (86.4-96.0) | +39.4 pp (32.6-46.6) | +10.6 pp (1.4-15.7) | — |

Proposed architecture: mean latency 1.03-1.07 s, p95 1.91-1.96 s, max 2.07 s across 1-200
concurrent devices; throughput 0.49 req/s (1 device) to 96.9 req/s (200); validator CPU
7.3 % -> 91.8 %, gateway CPU 3.8 % -> 97 %; revocation 3.02 s mean (sd 0.52, 2.20-3.76 s, 30
trials); ~380 B of ledger per decision. Centralized baseline (B2): ~21 ms latency.
These are point estimates from one seeded simulation run (seed 42), with no confidence
intervals or significance tests.

## Mapping

| Paper item | Content | Source file | Regenerate with |
|---|---|---|---|
| Table I | Comparison with related proposals | Written from literature review; not data-generated | — |
| Table II | Attack scenarios A1-A6 | Written in manuscript; exercised by `testbed/device_simulator.py --malicious` | — |
| Table III | Manufacturing vs. substation deployments | Policy enforced by `scripts/configure_policies.js` (theta = 40 / 70) | `scripts/configure_policies.js` |
| Table IV | Software/hardware environment | `docker-compose.yml`, `hardhat.config.js`, `testbed/requirements.txt` | — |
| Table V | Denial rate by scenario and architecture | `evaluation/results/results_security.csv` | `evaluation/simulate_performance.py` |
| Table VI | Load sweep (latency, throughput, CPU) | `results_perf.csv`, `results_cpu_mem.csv` | `evaluation/simulate_performance.py` |
| Fig. 1 | Architecture diagram | `evaluation/figures/fig1_architecture.png` | `evaluation/gen_fig1_architecture.py` |
| Fig. 2 | Continuous-verification workflow | `evaluation/figures/fig2_workflow.png` | `evaluation/gen_fig2_workflow.py` |
| Fig. 3 | Attack-denial rate by scenario | `evaluation/figures/fig6_security.png` (file name is historical) | `evaluation/gen_result_figures.py` |
| Fig. 4 | Latency vs. concurrency | `evaluation/figures/fig3_latency.png` | `evaluation/gen_result_figures.py` |
| Fig. 5 | Throughput vs. concurrency | `evaluation/figures/fig4_throughput.png`, `results_centralized.csv` | `evaluation/gen_result_figures.py` |
| Fig. 6 | CPU/memory vs. concurrency | `evaluation/figures/fig5_cpumem.png` | `evaluation/gen_result_figures.py` |
| Revocation, storage | Time-to-revocation, ledger growth | `results_misc.json` (`revocation`, `storage`) | `evaluation/simulate_performance.py` |
| Eq. (1)-(5) | Trust decay, re-anchoring, grant predicate, latency, capacity | `contracts/TrustManager.sol`, `contracts/AccessControlManager.sol`; capacity modeled in `simulate_performance.py` | — |
| Derived headline numbers | Means, gains, ranges | `evaluation/results/summary_stats.json` | `evaluation/analyze_results.py` |

## Live-network measurements

`evaluation/results_live/` and `live/README.md` hold measurements from a real Besu QBFT network (single run, 2-vCPU host). They differ from the simulation in places (closed-loop latency ~2.0 s vs ~1.0 s; measured gas 48.8k vs 65k assumed; revocation 4.0 s vs 3.0 s; throughput limited by the host). Prefer these where they disagree.

## IMPORTANT: what is simulated vs. what is real Besu output

- **Real, runnable Besu/Solidity/Python code**: `network/`, `contracts/`, `scripts/`, `testbed/`, `benchmark/`. These deploy and run against an actual 4-node Hyperledger Besu QBFT network.
- **Simulated (not live-network) numbers**: everything under `evaluation/results/` comes from `evaluation/simulate_performance.py`, a discrete-event simulation calibrated to Besu's documented parameters (2 s block period, ~65,000 gas/access-decision tx, 30M gas block limit) rather than a multi-day physical deployment. The manuscript discloses this in its Methodology (Section VI) and Limitations (Section VIII).

## Replacing simulated numbers with real measurements

1. Bring the live network up and configure both policies:
   ```bash
   docker compose up -d
   npm install && npx hardhat compile
   DEPLOYER_PRIVATE_KEY=<key> npm run deploy      # prints 3 contract addresses
   ACCESS_CONTROL_ADDRESS=<addr> npx hardhat run scripts/configure_policies.js --network besu
   ```
2. Start the gateway (`testbed/gateway.py`) and a device fleet (`testbed/device_simulator.py`).
3. Replace `evaluation/simulate_performance.py`'s output with real output from
   `benchmark/latency_throughput_test.py` — same CSV columns, so
   `evaluation/gen_result_figures.py` works unmodified (see `evaluation/README.md`).
4. The current manuscript reports no significance tests. To add them, run each configuration
   for >=10 independent trials with different seeds and compute Welch's t-test / Mann-Whitney U
   (e.g., with `scipy.stats`) plus confidence intervals on the resulting distributions.

## Reproducing every figure/table from scratch (simulation path)

```bash
cd evaluation
pip install -r requirements.txt
python simulate_performance.py      # -> results/*.csv, results/results_misc.json
python gen_fig1_architecture.py     # -> figures/fig1_architecture.png
python gen_fig2_workflow.py         # -> figures/fig2_workflow.png
python gen_result_figures.py        # -> figures/fig3_latency.png ... fig6_security.png
```

This regenerates every number and image referenced in the table above, deterministically
(seeded, `random.seed(42)` in `simulate_performance.py`).
