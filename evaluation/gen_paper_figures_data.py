"""Data figures of the paper (Figs. 3-7), academic style, 600 dpi. Run from the repo root:
   python3 evaluation/gen_paper_figures_data.py"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np, pandas as pd
from paper_style import *
R = pathlib.Path(__file__).resolve().parent
G, S, O = R / "results_gcp", R / "results_gcp_supp", R / "results_offline"
CS = [1, 10, 50, 100, 200]

# ---- Fig. 3: attacks denied (heat table) ------------------------------------------------------
sec = pd.read_csv(G / "summary_security.csv"); sec4 = pd.read_csv(S / "summary_security.csv")
rows = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A8b", "A8c"]
names = ["A1 replay", "A2 revoked device", "A3 flooding", "A4 lateral move", "A5 low trust", "A6 time window",
         "A7 store tampering", "A8 host takeover", "A8b two hosts", "A8c three hosts"]
cols = ["b0", "b1", "b2", "b3", "b4", "bcz"]
M = np.full((len(rows), len(cols)), np.nan)
for j, a in enumerate(cols):
    src = sec4 if a == "b4" else sec
    for i, r in enumerate(rows):
        d = src[(src.arch == a) & (src.scenario == r)]
        if len(d): M[i, j] = 100 * d.denial.iloc[0]
fig, ax = plt.subplots(figsize=(W1, 2.15)); ax.grid(False)
cmap = mpl.colors.LinearSegmentedColormap.from_list("d", ["#F4F4F4", "#9CC3E0", "#0072B2"])
ax.imshow(np.ma.masked_invalid(M), cmap=cmap, vmin=0, vmax=100, aspect="auto")
for i in range(len(rows)):
    for j in range(len(cols)):
        v = M[i, j]
        if np.isnan(v):
            ax.text(j, i, "n/a", ha="center", va="center", color=MUTED, fontsize=6)
        else:
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.8, color="white" if v > 60 else INK, fontweight="bold" if v == 100 else "normal")
ax.set_xticks(range(len(cols))); ax.set_xticklabels(["B0", "B1", "B2", "B3", "B4", "BC-ZT"])
ax.xaxis.tick_top(); ax.set_yticks(range(len(rows))); ax.set_yticklabels(names)
ax.set_xticks(np.arange(-.5, len(cols), 1), minor=True); ax.set_yticks(np.arange(-.5, len(rows), 1), minor=True)
ax.grid(which="minor", color="white", linewidth=1.2, linestyle="-"); ax.tick_params(which="both", length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.axhline(7.5, color=INK, lw=0.5); ax.axvline(3.5, color=INK, lw=0.5, ls=(0, (2, 2)))
cb = fig.colorbar(plt.cm.ScalarMappable(norm=mpl.colors.Normalize(0, 100), cmap=cmap), ax=ax, orientation="horizontal", fraction=0.05, pad=0.04, aspect=30)
cb.set_label("Attack requests denied (%)", fontsize=6.8); cb.set_ticks([0, 25, 50, 75, 100]); cb.outline.set_linewidth(0.4); cb.ax.tick_params(labelsize=6)
fig.subplots_adjust(left=0.33, right=0.96, top=0.92, bottom=0.14)
save(fig, "fig3_security")

# ---- Fig. 4: latency ---------------------------------------------------------------------------
sp = pd.read_csv(G / "summary_perf.csv"); p = pd.read_csv(G / "perf_raw.csv")
fig, ax = plt.subplots(figsize=(W1, 2.12))
for a in ["b0", "b1", "b2", "b3", "bcz"]:
    lab, c, m, ls, _ = ARCH[a]; d = p[(p.arch == a) & (p.granted == 1)]
    p50 = [d[d.concurrency == k].rtt_ms.median() for k in CS]; p95 = [d[d.concurrency == k].rtt_ms.quantile(.95) for k in CS]
    ax.plot(CS, p50, marker=m, color=c, ls="-", lw=1.4 if a == "bcz" else 0.9, label=lab, mfc="white" if a in ("b0", "b3") else c, mew=0.8)
    ax.plot(CS, p95, color=c, ls=(0, (3, 2)), lw=0.7, alpha=.9)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(CS); ax.set_xticklabels(CS); ax.minorticks_off()
ax.set_xlabel("Concurrent clients"); ax.set_ylabel("Latency of granted requests (ms)"); ax.set_ylim(2, 1.2e4)
h = [plt.Line2D([], [], color="#333", lw=1.2), plt.Line2D([], [], color="#333", lw=0.8, ls=(0, (3, 2)))]
leg1 = ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, columnspacing=1.0, handlelength=1.8)
ax.add_artist(leg1); ax.legend(h, ["median", "95th percentile"], loc="lower right", fontsize=6.2, handlelength=2)
fig.subplots_adjust(left=0.16, right=0.98, top=0.80, bottom=0.17); save(fig, "fig4_latency")

# ---- Fig. 5: throughput ------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(W1, 2.12))
for a in ["b0", "b1", "b2", "b3", "bcz"]:
    lab, c, m, ls, _ = ARCH[a]; d = sp[sp.arch == a].sort_values("concurrency")
    ax.errorbar(d.concurrency, d.thr_rps, yerr=d.thr_ci, marker=m, color=c, lw=1.4 if a == "bcz" else 0.9, capsize=1.5, elinewidth=0.5,
                mfc="white" if a in ("b0", "b3") else c, mew=0.8, label=lab)
ax.axhline(174.0, color="#1E6B33", ls=(0, (1, 1.5)), lw=0.9); ax.text(2.6, 112, "Eq. (5) bound, 174 req/s", color="#1E6B33", fontsize=6.2)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(CS); ax.set_xticklabels(CS); ax.minorticks_off()
ax.set_xlabel("Concurrent clients"); ax.set_ylabel("Throughput (requests/s)"); ax.set_ylim(0.3, 2200)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, columnspacing=1.0, handlelength=1.8)
fig.subplots_adjust(left=0.16, right=0.98, top=0.80, bottom=0.17); save(fig, "fig5_throughput")

# ---- Fig. 6: chain probe and B4 comparison (two narrow panels) ---------------------------------
pr = pd.read_csv(S / "probe_raw.csv"); ps = pd.read_csv(S / "perf_raw.csv")
fig, (a, b) = plt.subplots(1, 2, figsize=(W1, 2.1), gridspec_kw={"wspace": 0.45})
com = pr.committed_in_window / pr.send_span_s
a.plot([0, 170], [0, 170], color=MUTED, lw=0.7, ls=(0, (1, 1.5)), label="committed = offered")
a.plot(pr.rate, com, color=ARCH["bcz"][1], marker="D", markersize=3, label="committed")
a.axhline(173.5, color="#1E6B33", ls=(0, (4, 2)), lw=0.9, label="Eq. (5) bound")
a.annotate("peak 65.1", xy=(80, 65.1), xytext=(92, 92), fontsize=5.6, arrowprops=dict(arrowstyle="-", lw=0.5, color=INK))
a.set_xlim(0, 170); a.set_ylim(0, 200); a.set_xticks([0, 40, 80, 120, 160]); a.set_xlabel("Offered load (tx/s, no gateway)"); a.set_ylabel("Committed (tx/s)")
a.legend(loc="upper left", bbox_to_anchor=(0.0, 0.88), handlelength=1.4, fontsize=5.4, labelspacing=0.3); panel(a, "(a)", -0.02, 1.0)
for k in ["b3", "b4", "bcz"]:
    lab, c, m, ls, _ = ARCH[k]; d = ps[(ps.arch == k) & (ps.granted == 1)]
    b.plot(CS, [d[d.concurrency == x].rtt_ms.median() for x in CS], marker=m, markersize=3, color=c, label=lab.replace(" (proposed)", ""), mfc="white" if k == "b3" else c, mew=0.8)
b.set_xscale("log"); b.set_yscale("log"); b.set_xticks(CS); b.set_xticklabels(CS); b.minorticks_off(); b.tick_params(axis="x", labelsize=5.6)
b.set_xlabel("Concurrent clients"); b.set_ylabel("Median latency (ms)"); b.set_ylim(2, 3e4)
b.legend(loc="upper left", handlelength=1.4, fontsize=5.4, labelspacing=0.3); panel(b, "(b)", -0.02, 1.0)
fig.subplots_adjust(left=0.115, right=0.99, top=0.90, bottom=0.2); save(fig, "fig6_probe")

# ---- Fig. 7: offline calibration (two narrow panels) -------------------------------------------
S1 = pd.read_csv(O / "decay_sensitivity.csv"); S2 = pd.read_csv(O / "telemetry_evidence.csv")
fig, (a, b) = plt.subplots(1, 2, figsize=(W1, 2.15), gridspec_kw={"wspace": 0.45})
for E, mk, c in ((1, "o", "#0072B2"), (6, "s", "#B36B00"), (24, "^", "#B05A8C")):
    d = S1[(S1.theta == 70) & (S1.E_h == E)]
    a.scatter(d.time_to_deny_h / 24, 100 * d.false_deny, marker=mk, s=9, color=c, alpha=.85, linewidths=0, label=f"every {E} h")
dep = S1[(S1.kappa == 2) & (S1.tau_h == 24) & (S1.theta == 70)]
a.scatter(dep.time_to_deny_h / 24, 100 * dep.false_deny, s=45, facecolors="none", edgecolors=INK, linewidths=0.8, label="deployed")
a.set_xscale("log"); a.set_xlim(0.09, 60); a.set_xlabel("Days to deny a silent compromise"); a.set_ylabel("Healthy requests denied (%)")
a.legend(loc="center right", fontsize=5.2, handletextpad=0.1, labelspacing=0.3, borderaxespad=0.1, title="attestation", title_fontsize=5.2); panel(a, "(a)", -0.02, 1.0)
for mode, mk, c, lab in zip(["mean shift +3 sd", "variance x3", "drift 1 sd/hour"], ["o", "s", "^"], ["#0072B2", "#D55E00", "#009E73"], ["mean +3 SD", "variance $\\times$3", "drift"]):
    d = S2[S2["mode"] == mode].sort_values("L"); x = np.maximum(d.false_reports_per_device_day, 0.02)
    b.plot(x, 100 * d.detect_rate, marker=mk, markersize=3, color=c, label=lab)
    if mode == "mean shift +3 sd":
        for xi, yi, L in zip(x, 100 * d.detect_rate, d.L): b.annotate(f"L={L:g}", (xi, yi), textcoords="offset points", xytext=(1, -8), fontsize=4.8, color=MUTED)
b.set_xscale("log"); b.set_xlim(0.015, 90); b.set_xlabel("False alarms per device-day"); b.set_ylabel("Attacks detected (%)"); b.set_ylim(-3, 108)
b.legend(loc="center", bbox_to_anchor=(0.40, 0.52), handlelength=1.2, fontsize=5.2, labelspacing=0.3); panel(b, "(b)", -0.02, 1.0)
fig.subplots_adjust(left=0.11, right=0.99, top=0.90, bottom=0.2); save(fig, "fig7_offline")
print("done")
