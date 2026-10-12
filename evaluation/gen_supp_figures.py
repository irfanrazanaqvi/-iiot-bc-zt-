"""Figure for the supplementary GCP run: (a) direct chain probe, (b) B4 vs BC-ZT latency.
python3 evaluation/gen_supp_figures.py evaluation/results_gcp_supp evaluation/results_gcp_supp/figures"""
import sys, pathlib, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
D = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "evaluation/results_gcp_supp")
O = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else D / "figures"); O.mkdir(parents=True, exist_ok=True)
pr = pd.read_csv(D / "probe_raw.csv"); p = pd.read_csv(D / "perf_raw.csv")
fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.2))
a.plot(pr.rate, pr.rate, ls=":", color="#888888", label="offered = committed")
a.plot(pr.rate, pr.committed_in_window / pr.send_span_s, marker="o", color="#1B3E7A", label="committed during the send window")
a.axhline(173.5, color="#1E6B33", ls="--", lw=1, label="Eq. (5) ceiling, 173.5/s")
a.set_xlabel("Offered load (tx/s, no gateway)"); a.set_ylabel("Committed (tx/s)"); a.set_ylim(0, 190)
a.set_title("(a) direct chain probe", fontsize=8); a.legend(fontsize=6.5, loc="upper left"); a.grid(alpha=.3)
cs = [1, 10, 50, 100, 200]
for arch, lab, c, m in (("b3", "B3 hardened ZT", "#7A4AB0", "v"), ("b4", "B4 replicated ZT", "#C9A227", "s"), ("bcz", "BC-ZT", "#1B3E7A", "D")):
    d = p[(p.arch == arch) & (p.granted == 1)]
    b.plot(cs, [d[d.concurrency == k].rtt_ms.median() for k in cs], marker=m, color=c, label=lab)
b.set_xscale("log"); b.set_yscale("log"); b.set_xticks(cs); b.set_xticklabels(cs)
b.set_xlabel("Concurrent clients"); b.set_ylabel("Median latency (ms)"); b.set_title("(b) latency, supplementary run", fontsize=8)
b.legend(fontsize=6.5); b.grid(alpha=.3, which="both")
plt.tight_layout(); plt.savefig(O / "fig7_probe.png", dpi=220, facecolor="white")
