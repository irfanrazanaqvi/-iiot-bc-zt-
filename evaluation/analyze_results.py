"""Derive the headline numbers quoted in the manuscript directly from results/*.csv.

Run from inside evaluation/:  python analyze_results.py
Writes results/summary_stats.json and prints a short report. Pure standard library.
All values come from a single seeded simulation run (seed 42): point estimates,
no confidence intervals or significance tests.
"""
import csv, json, statistics as st
from pathlib import Path

R = Path(__file__).parent / "results"
sec = list(csv.DictReader(open(R / "results_security.csv")))
cols = list(sec[0].keys())[1:]            # B0, B1, B2, Proposed
perf = list(csv.DictReader(open(R / "results_perf.csv")))
cpu = list(csv.DictReader(open(R / "results_cpu_mem.csv")))
cen = list(csv.DictReader(open(R / "results_centralized.csv")))
misc = json.load(open(R / "results_misc.json"))

f = lambda row, k: float(row[k])
mean = {c: round(st.mean(f(r, c) for r in sec) * 100, 1) for c in cols}
prop = cols[-1]
gain = {}
for c in cols[:-1]:
    d = [(f(r, prop) - f(r, c)) * 100 for r in sec]
    gain[c] = {"mean_pp": round(st.mean(d), 1), "min_pp": round(min(d), 1), "max_pp": round(max(d), 1)}

out = {
    "seed": 42,
    "mean_denial_rate_pct": mean,
    "proposed_gain_pp_per_scenario": gain,
    "latency_mean_ms_range": [min(f(r, "latency_mean_ms") for r in perf), max(f(r, "latency_mean_ms") for r in perf)],
    "latency_p95_ms_range": [min(f(r, "latency_p95_ms") for r in perf), max(f(r, "latency_p95_ms") for r in perf)],
    "latency_max_ms": max(f(r, "latency_max_ms") for r in perf),
    "throughput_rps": {perf[0]["concurrency"]: f(perf[0], "throughput_rps"), perf[-1]["concurrency"]: f(perf[-1], "throughput_rps")},
    "grant_rate_range": [min(f(r, "grant_rate") for r in perf), max(f(r, "grant_rate") for r in perf)],
    "centralized_latency_mean_ms_range": [min(f(r, "latency_mean_ms") for r in cen), max(f(r, "latency_mean_ms") for r in cen)],
    "centralized_max_throughput_rps": max(f(r, "throughput_rps") for r in cen),
    "validator_cpu_pct": [f(cpu[0], "validator_cpu_pct"), f(cpu[-1], "validator_cpu_pct")],
    "gateway_cpu_pct": [f(cpu[0], "gateway_cpu_pct"), f(cpu[-1], "gateway_cpu_pct")],
    "revocation": misc["revocation"],
    "max_tx_per_block": misc["max_tx_per_block"],
}
(R / "summary_stats.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
