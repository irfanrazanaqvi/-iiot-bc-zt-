# Results Summary — Paper-to-File Mapping

Every quantitative table and figure in the manuscript (*A Blockchain-Based Zero-Trust
Architecture for Secure Industrial Internet of Things (IIoT)*) traces to a specific file in
this repository. Use this page to find, regenerate, or replace any number in the paper.

| Paper item | Content | Source file | Regenerate with |
|---|---|---|---|
| Table 1 | Comparative analysis (20 studies) | Written directly in the manuscript from literature review; not data-generated | — |
| Table 2 | Attack scenarios A1-A6 | Written in manuscript; exercised by `testbed/device_simulator.py --malicious` | — |
| Table 3 | Manufacturing use case actors | Written in manuscript; policy enforced by `scripts/configure_policies.js` (θ=40) | `scripts/configure_policies.js` |
| Table 4 | Substation use case actors | Written in manuscript; policy enforced by `scripts/configure_policies.js` (θ=70) | `scripts/configure_policies.js` |
| Table 5 | Formal-model notation | Written in manuscript, matches constants in `contracts/TrustManager.sol` and `evaluation/simulate_performance.py` | — |
| Table 6 | Software/hardware environment | Matches `docker-compose.yml`, `hardhat.config.js`, `testbed/requirements.txt` | — |
| Table 7 | Evaluation baselines B0-B2 | B2 (centralized) simulated in `evaluation/simulate_performance.py::simulate_centralized()` | `evaluation/simulate_performance.py` |
| Table 8 / Fig. 3 / Fig. 4 | Latency & throughput vs. concurrency | `evaluation/results/results_perf.csv`, `evaluation/results/results_centralized.csv` | `evaluation/simulate_performance.py` then `evaluation/gen_result_figures.py` |
| Fig. 5 | CPU/memory vs. concurrency | `evaluation/results/results_cpu_mem.csv` | `evaluation/simulate_performance.py` then `evaluation/gen_result_figures.py` |
| Fig. 6 | Attack denial rate by architecture | `evaluation/results/results_security.csv` | `evaluation/simulate_performance.py` then `evaluation/gen_result_figures.py` |
| Table 9 | On-chain storage growth | `evaluation/results/results_misc.json` (`storage` key) | `evaluation/simulate_performance.py` |
| §7.8 Revocation | Time-to-revocation (mean/σ/range) | `evaluation/results/results_misc.json` (`revocation` key) | `evaluation/simulate_performance.py` |
| Table 10 | Statistical significance | Computed by hand from the above CSVs in the manuscript; not scripted here | See "Adding real statistical tests" below |
| Fig. 1 | Architecture diagram | `evaluation/figures/fig1_architecture.png` | `evaluation/gen_fig1_architecture.py` |
| Fig. 2 | Continuous-verification workflow | `evaluation/figures/fig2_workflow.png` | `evaluation/gen_fig2_workflow.py` |
| Eq. (1)-(6) | Formal model | Directly implemented in `contracts/TrustManager.sol` (decay, evidence) and `contracts/AccessControlManager.sol` (decision predicate); Eq. (4)-(6) modeled in `evaluation/simulate_performance.py` | — |

## IMPORTANT: what is simulated vs. what is real Besu output

- **Real, runnable Besu/Solidity/Python code**: `network/`, `contracts/`, `scripts/`, `testbed/`, `benchmark/`. These deploy and run against an actual 4-node Hyperledger Besu QBFT network.
- **Simulated (not live-network) numbers**: everything under `evaluation/results/` comes from `evaluation/simulate_performance.py`, a discrete-event simulation calibrated to Besu's documented parameters (2 s block period, ~65,000 gas/access-decision tx, 30M gas block limit) rather than a multi-day physical deployment. The paper discloses this explicitly in Section 7.1 and Section 9 (Threats to Validity).

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
4. For Table 10 (statistical significance), run each configuration for ≥10 independent
   trials and compute Welch's t-test / Mann-Whitney U (e.g., with `scipy.stats`) on the
   resulting distributions, applying a Holm correction as described in Section 6.7.

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
