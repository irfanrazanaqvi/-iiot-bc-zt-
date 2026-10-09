"""Statistics for the live four-architecture comparison.  Usage: python3 experiments/analyze.py <results_dir>

Writes <dir>/summary.json, <dir>/tables.md and several CSVs.  Only needs pandas, numpy, scipy.
Confidence intervals: 95 % t-intervals over repeats for latency/throughput/revocation; Wilson intervals
on pooled request counts for denial rates.  Tests: Mann-Whitney U on per-request latency, Fisher's exact
test on pooled denial counts (proposed vs centralized ZT).
"""
import json, math, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

D = Path(sys.argv[1])
NAMES = {"b0": "B0 no access control", "b1": "B1 static RBAC", "b2": "B2 centralized ZT", "b3": "B3 hardened ZT", "bcz": "Proposed BC-ZT"}
meta = json.load(open(D / "meta.json"))
out, md = {}, []


def tci(x):
    x = np.asarray(x, float)
    if len(x) < 2:
        return (float(x.mean()), float("nan"))
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))
    return float(x.mean()), float(h)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0, c - h), min(1, c + h)


# ---------------------------------------------------------------- performance sweep
perf = pd.read_csv(D / "perf_raw.csv"); ph = pd.read_csv(D / "phases.csv")
pp = ph[ph.phase == "perf"].copy(); pp["c"] = pp.detail.str.replace("c=", "").astype(int)
rows = []
for (arch, c), g in perf.groupby(["arch", "concurrency"]):
    reps = []
    for rep, gr in g.groupby("repeat"):
        t = pp[(pp.arch == arch) & (pp.c == c) & (pp.repeat == rep)].iloc[0]
        gg = gr[gr.granted == 1]
        reps.append(dict(gmean=gg.rtt_ms.mean() if len(gg) else float('nan'), mean=gr.rtt_ms.mean(), p95=gr.rtt_ms.quantile(.95), thr=len(gr) / (t.t_end - t.t_start),
                         err=(gr.reason == "error").mean(), grant=gr.granted.mean()))
    r = pd.DataFrame(reps)
    m, mh = tci(r["mean"]); th, thh = tci(r.thr); gm, gmh = tci(r.gmean.dropna()) if r.gmean.notna().any() else (float('nan'), float('nan'))
    gd = g[g.granted == 1].rtt_ms
    rows.append(dict(arch=arch, concurrency=c, repeats=len(r), mean_ms=round(m, 1), mean_ci=round(mh, 1), p50_ms=round(g.rtt_ms.median(), 1),
                     p95_ms=round(g.rtt_ms.quantile(.95), 1), max_ms=round(g.rtt_ms.max(), 1), thr_rps=round(th, 2), thr_ci=round(thh, 2),
                     grant=round(r.grant.mean(), 3), err=round(r.err.mean(), 3),
                     g_mean_ms=round(gm, 1), g_mean_ci=round(gmh, 1), g_p50_ms=round(gd.median(), 1) if len(gd) else None, g_p95_ms=round(gd.quantile(.95), 1) if len(gd) else None))
perf_t = pd.DataFrame(rows); perf_t.to_csv(D / "summary_perf.csv", index=False)
out["perf"] = rows
md.append("## Load sweep (closed loop; mean over repeats, 95% CI)\n")
md.append("| Arch | Conc. | Mean (ms) | ±CI | p50 | p95 | Max | Req/s | ±CI | Grant | Err | Granted-only p50 | p95 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    md.append(f"| {NAMES[r['arch']]} | {r['concurrency']} | {r['mean_ms']} | {r['mean_ci']} | {r['p50_ms']} | {r['p95_ms']} | {r['max_ms']} | {r['thr_rps']} | {r['thr_ci']} | {r['grant']} | {r['err']} | {r['g_p50_ms']} | {r['g_p95_ms']} |")

# ---------------------------------------------------------------- open loop
op = pd.read_csv(D / "openloop_raw.csv"); orows = []
for arch, g in op.groupby("arch"):
    rm = g.groupby("repeat").rtt_ms.mean(); m, h = tci(rm)
    orows.append(dict(arch=arch, n=len(g), mean_ms=round(m, 1), ci=round(h, 1), p50_ms=round(g.rtt_ms.median(), 1), p95_ms=round(g.rtt_ms.quantile(.95), 1),
                      max_ms=round(g.rtt_ms.max(), 1), grant=round(g.granted.mean(), 3)))
out["openloop"] = orows
a, b = op[op.arch == "bcz"].rtt_ms, op[op.arch == "b2"].rtt_ms
if len(a) and len(b):
    out["openloop_test_bcz_vs_b2"] = dict(mannwhitney_p=float(stats.mannwhitneyu(a, b).pvalue), median_diff_ms=float(a.median() - b.median()))
md.append("\n## Random arrivals (Poisson, mean gap 0.5 s)\n\n| Arch | Requests | Mean (ms) | ±CI | p50 | p95 | Max | Grant |\n|---|---|---|---|---|---|---|---|")
for r in orows:
    md.append(f"| {NAMES[r['arch']]} | {r['n']} | {r['mean_ms']} | {r['ci']} | {r['p50_ms']} | {r['p95_ms']} | {r['max_ms']} | {r['grant']} |")

# ---------------------------------------------------------------- security
sec = pd.read_csv(D / "security_raw.csv"); out["security_transport_errors_excluded"] = int((sec.reason == "error").sum()); sec = sec[sec.reason != "error"]; atk = sec[sec.role == "attack"].copy()
lim = meta["deployment"]["maxPerWindow"]
res = []
for (arch, sc), g in atk.groupby(["arch", "scenario"]):
    if sc == "A3":   # only the requests beyond the permitted rate count as attack traffic
        per = []; K = N = 0
        for rep, gr in g.groupby("repeat"):
            excess = len(gr) - lim
            if excess <= 0:
                continue
            denied = int((1 - gr.granted).sum()); k = min(denied, excess)
            per.append(k / excess); K += k; N += excess
    else:
        per = [float(1 - gr.granted.mean()) for _, gr in g.groupby("repeat")]; K = int((1 - g.granted).sum()); N = len(g)
    if N == 0:
        continue
    p, lo, hi = wilson(K, N)
    res.append(dict(arch=arch, scenario=sc, denied=K, n=N, denial=round(p, 3), lo=round(lo, 3), hi=round(hi, 3), repeats=len(per), reps_full=int(sum(1 for x in per if x >= 0.999))))
sec_t = pd.DataFrame(res); sec_t.to_csv(D / "summary_security.csv", index=False)
out["security"] = res
scs = sorted(sec_t.scenario.unique()); md.append("\n## Attack denial rate (Wilson 95% CI over pooled requests)\n")
md.append("| Scenario | " + " | ".join(NAMES[a] for a in ["b0", "b1", "b2", "b3", "bcz"] if a in set(sec_t.arch)) + " |\n|---|" + "---|" * len(set(sec_t.arch)))
for sc in scs:
    cells = []
    for a in ["b0", "b1", "b2", "b3", "bcz"]:
        r = sec_t[(sec_t.arch == a) & (sec_t.scenario == sc)]
        if len(r): r = r.iloc[0]; cells.append(f"{r.denial:.1%} [{r.lo:.1%}, {r.hi:.1%}]")
    md.append(f"| {sc} | " + " | ".join(cells) + " |")
means = {a: float(sec_t[sec_t.arch == a].denial.mean()) for a in set(sec_t.arch)}
out["security_mean_denial"] = means
md.append("\nMean over scenarios: " + "; ".join(f"{NAMES[a]} {v:.1%}" for a, v in sorted(means.items())))
tests = {}
for other in ("b2", "b3"):
    if other not in set(sec_t.arch):
        continue
    for sc in scs:
        x = sec_t[(sec_t.arch == "bcz") & (sec_t.scenario == sc)]; y = sec_t[(sec_t.arch == other) & (sec_t.scenario == sc)]
        if len(x) and len(y):
            x, y = x.iloc[0], y.iloc[0]
            tests[f"{sc}_vs_{other}"] = dict(
                pooled_p=float(stats.fisher_exact([[x.denied, x.n - x.denied], [y.denied, y.n - y.denied]])[1]),
                repeat_level_p=float(stats.fisher_exact([[x.reps_full, x.repeats - x.reps_full], [y.reps_full, y.repeats - y.reps_full]])[1]),
                bcz_repeats_fully_denied=f"{x.reps_full}/{x.repeats}", other_repeats_fully_denied=f"{y.reps_full}/{y.repeats}")
out["security_fisher"] = tests
md.append("\nFisher exact, proposed vs centralized (repeat-level is the valid unit; pooled treats requests as independent):\n")
md.append("| Scenario | vs | proposed repeats fully denied | other repeats fully denied | repeat-level p | pooled p |\n|---|---|---|---|---|---|")
for k, v in tests.items():
    sc, o = k.split("_vs_")
    md.append(f"| {sc} | {NAMES[o]} | {v['bcz_repeats_fully_denied']} | {v['other_repeats_fully_denied']} | {v['repeat_level_p']:.3g} | {v['pooled_p']:.3g} |")
ctrl = sec[sec.scenario == "CTRL"]; fd = {a: float(1 - g.granted.mean()) for a, g in ctrl.groupby("arch")}
out["control_false_deny"] = fd
md.append("\nLegitimate control, false-deny rate: " + ", ".join(f"{NAMES[a]} {v:.1%}" for a, v in sorted(fd.items())))
for sc_ in ("A7", "A8"):
    out[f"{sc_}_bcz_tamper_outcomes"] = sec[(sec.scenario == sc_) & (sec.arch == "bcz")].extra.value_counts().to_dict()
out["denial_reasons_A7_A8"] = {f"{a_}/{s_}": g_.reason.value_counts().to_dict() for (a_, s_), g_ in atk[atk.scenario.isin(["A7", "A8"])].groupby(["arch", "scenario"])}

# ---------------------------------------------------------------- revocation
rv = pd.read_csv(D / "revocation_raw.csv"); rrows = []
for arch, g in rv.groupby("arch"):
    x = g.revocation_s.values; m, h = tci(x)
    rrows.append(dict(arch=arch, trials=len(x), mean_s=round(m, 3), ci=round(h, 3), sd=round(float(x.std(ddof=1)), 3), min=float(x.min()), max=float(x.max()), timed_out=int(g.timed_out.sum())))
out["revocation"] = rrows
md.append("\n## Revocation latency (submit revoke -> first denied decision)\n\n| Arch | Trials | Mean (s) | ±CI | SD | Min | Max | Timed out |\n|---|---|---|---|---|---|---|---|")
for r in rrows:
    md.append(f"| {NAMES[r['arch']]} | {r['trials']} | {r['mean_s']} | {r['ci']} | {r['sd']} | {r['min']} | {r['max']} | {r['timed_out']} |")

# ---------------------------------------------------------------- chain: gas, block capacity, bytes/decision
gas = perf[(perf.arch == "bcz") & (perf.reason == "granted")].gas_used.astype(float)
bl = pd.DataFrame(meta["blocks"]); blt = bl[bl.tx > 0]
chain = dict(gas_per_granted_decision=float(gas.mean()) if len(gas) else None,
             block_gas_limit=int(bl.gas_limit.iloc[-1]) if len(bl) else None,
             max_tx_in_block=int(blt.tx.max()) if len(blt) else None,
             bytes_per_tx=float((blt["size"] / blt.tx).mean()) if len(blt) else None,
             block_period_s=float(np.median(np.diff(bl.ts))) if len(bl) > 2 else None)
if chain["gas_per_granted_decision"]:
    chain["capacity_tx_per_block"] = int(chain["block_gas_limit"] // chain["gas_per_granted_decision"])
    chain["capacity_decisions_per_s"] = chain["capacity_tx_per_block"] / 2.0
out["chain"] = chain
md.append("\n## Chain\n\n" + "\n".join(f"- {k}: {v}" for k, v in chain.items()))

# ---------------------------------------------------------------- trust-decay validation (Eq. 1, decay unit shortened to 6 s)
if (D / "decay_raw.csv").exists():
    dc = pd.read_csv(D / "decay_raw.csv"); drows = []
    md.append("\n## Trust-decay validation (score vs Eq. 1; decision before/after crossing theta)\n\n| Arch | Samples | Score == Eq. 1 | Max abs deviation | Steps seen | Decisions correct |\n|---|---|---|---|---|---|")
    for arch, g in dc.groupby("arch"):
        s = g[g.kind == "sample"].copy(); s["score"] = s.score.astype(float); s["pred"] = s.pred.astype(float)
        d = g[g.kind != "sample"]
        steps = sorted(s.score.unique(), reverse=True)
        row = dict(arch=arch, samples=len(s), exact=round(float((s.score == s.pred).mean()), 3), max_dev=float((s.score - s.pred).abs().max()),
                   distinct_scores=[int(x) for x in steps], decisions=len(d), decisions_correct=int((d.granted == d.expect_grant).sum()))
        drows.append(row)
        md.append(f"| {NAMES[arch]} | {row['samples']} | {row['exact']:.1%} | {row['max_dev']} | {row['distinct_scores']} | {row['decisions_correct']}/{row['decisions']} |")
    out["decay"] = drows

# ---------------------------------------------------------------- gateway scale-out for BC-ZT
if (D / "scale_raw.csv").exists():
    sc_ = pd.read_csv(D / "scale_raw.csv"); sp = ph[ph.phase == "scale"].copy(); srows = []
    sp["G"] = sp.detail.str.extract(r"G=(\d+)")[0].astype(int); sp["c"] = sp.detail.str.extract(r"c=(\d+)")[0].astype(int)
    md.append("\n## Gateway scale-out (BC-ZT, closed loop)\n\n| Gateways | Clients | Req/s | ±CI | Mean latency (ms) | p95 | Grant |\n|---|---|---|---|---|---|---|")
    for (G, c), g in sc_.groupby(["gateways", "concurrency"]):
        thr, lat = [], []
        for rep, gr in g.groupby("repeat"):
            t_ = sp[(sp.G == G) & (sp.c == c) & (sp["repeat"] == rep)].iloc[0]; thr.append(len(gr) / (t_.t_end - t_.t_start)); lat.append(gr.rtt_ms.mean())
        tm_, th_ = tci(thr); lm_, _ = tci(lat)
        srows.append(dict(gateways=int(G), concurrency=int(c), req_s=round(tm_, 1), ci=round(th_, 1), mean_ms=round(lm_, 0), p95_ms=round(g.rtt_ms.quantile(.95), 0), grant=round(g.granted.mean(), 3)))
        md.append(f"| {G} | {c} | {tm_:.1f} | {th_:.1f} | {lm_:.0f} | {g.rtt_ms.quantile(.95):.0f} | {g.granted.mean():.3f} |")
    out["scale"] = srows

# ---------------------------------------------------------------- resource usage per phase (if samplers ran)
samples = {}
for f in sorted(D.glob("sampler_*.csv")):
    if f.stat().st_size < 10:
        continue
    s = pd.read_csv(f); host = f.stem.replace("sampler_", ""); levels = []
    for _, t in pp[pp.arch == "bcz"].iterrows():
        w = s[(s.t >= t.t_start) & (s.t <= t.t_end)]
        if len(w): levels.append(dict(c=int(t.c), repeat=int(t["repeat"]), sys_cpu=float(w.sys_cpu_pct.mean()), besu_cpu=float(w.besu_cpu_pct.mean()),
                                      besu_rss=float(w.besu_rss_mb.mean()), py_cpu=float(w.py_cpu_pct.mean()), py_rss=float(w.py_rss_mb.mean())))
    if levels:
        L = pd.DataFrame(levels).groupby("c").mean(numeric_only=True).drop(columns="repeat").round(1); samples[host] = L.reset_index().to_dict("records")
        L.to_csv(D / f"summary_resources_{host}.csv")
out["resources"] = samples

json.dump(out, open(D / "summary.json", "w"), indent=1, default=str)
open(D / "tables.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
