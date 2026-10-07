# Evaluation / Results Generation

Scripts in this folder produced every figure and results table used in Section 7 of the
paper. Run in this order (from inside `evaluation/`):

```bash
pip install -r requirements.txt
python simulate_performance.py     # -> results/*.csv, results/results_misc.json
python gen_fig1_architecture.py    # -> figures/fig1_architecture.png
python gen_fig2_workflow.py        # -> figures/fig2_workflow.png
python gen_result_figures.py       # -> figures/fig3_latency.png ... fig6_security.png
```

## What each script does

| Script | Produces | Notes |
|---|---|---|
| `simulate_performance.py` | `results/results_perf.csv`, `results_centralized.csv`, `results_cpu_mem.csv`, `results_security.csv`, `results_misc.json` | Discrete-event simulation calibrated to the Besu QBFT parameters in `../network/genesis.json` (2 s block period, ~65,000 gas/access-decision tx, 30M gas block limit) and to measured-order-of-magnitude Besu/Fabric IoT benchmarking overheads reported in the literature (see paper refs [9],[11]). **This is a stand-in for live-network measurement** — see "Replacing simulation with real measurements" below. |
| `gen_fig1_architecture.py` | `figures/fig1_architecture.png` | Static architecture diagram (Figure 1 in the paper) — hand-drawn from the `contracts/` + `docker-compose.yml` design, not data-driven. |
| `gen_fig2_workflow.py` | `figures/fig2_workflow.png` | Sequence diagram of the continuous-verification flow (Figure 2) — mirrors `testbed/gateway.py`'s call sequence into `contracts/AccessControlManager.sol`. |
| `analyze_results.py` | `results/summary_stats.json` | Computes the headline means, gains and ranges quoted in the manuscript from the CSVs (standard library only). |
| `gen_result_figures.py` | `figures/fig3_latency.png` ... `fig6_security.png` | Reads the CSVs from `simulate_performance.py` and plots Figures 3-6. |

## Replacing simulation with real measurements

To regenerate `results/*.csv` from an actual running deployment instead of the simulation:

1. Bring up the real network and gateway per the top-level `README.md` (steps 1-6).
2. Run `../benchmark/latency_throughput_test.py` against your live gateway instead of
   `simulate_performance.py` — it writes a CSV in the same column layout
   (`concurrency, latency_mean_ms, latency_p50_ms, latency_p95_ms, throughput_rps, grant_rate`),
   so `gen_result_figures.py` works unmodified on real data.
3. For the CPU/memory figures, capture `docker stats` (or `cAdvisor`/`prometheus-node-exporter`)
   for the validator and gateway containers during the benchmark run and populate
   `results/results_cpu_mem.csv` in the same shape.
4. For the security/attack-scenario figure, drive the six scenarios in the paper's Table 2
   using `../testbed/device_simulator.py --malicious` and record grant/deny outcomes per
   scenario per architecture variant into `results/results_security.csv`.
