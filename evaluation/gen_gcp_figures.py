import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys, pathlib
D=sys.argv[1].rstrip("/")+"/" if len(sys.argv)>1 else "evaluation/results_gcp/"
OUT=sys.argv[2].rstrip("/")+"/" if len(sys.argv)>2 else D+"figures/"
p=pd.read_csv(D+"perf_raw.csv"); s=pd.read_csv(D+"summary_security.csv"); sp=pd.read_csv(D+"summary_perf.csv")
N={"b0":"B0 no control","b1":"B1 static RBAC","b2":"B2 centralized ZT","b3":"B3 hardened ZT","bcz":"Proposed BC-ZT"}
C={"b0":"#888888","b1":"#C9A227","b2":"#B04A4A","b3":"#7A4AB0","bcz":"#1B3E7A"}
M={"b0":"o","b1":"s","b2":"^","b3":"v","bcz":"D"}
cs=[1,10,50,100,200]
# fig3 latency, granted only
fig,ax=plt.subplots(figsize=(5.2,3.6))
for a in N:
    d=p[(p.arch==a)&(p.granted==1)]
    p50=[d[d.concurrency==c].rtt_ms.median() for c in cs]; p95=[d[d.concurrency==c].rtt_ms.quantile(.95) for c in cs]
    ax.plot(cs,p50,marker=M[a],color=C[a],label=N[a]+" p50")
    ax.plot(cs,p95,color=C[a],ls="--",alpha=.7)
ax.set_yscale("log"); ax.set_xscale("log"); ax.set_xticks(cs); ax.set_xticklabels(cs)
ax.set_xlabel("Concurrent clients"); ax.set_ylabel("Latency of granted requests (ms)")
ax.text(0.02,0.97,"solid: p50, dashed: p95",transform=ax.transAxes,fontsize=7,va="top")
ax.legend(fontsize=7,loc="center left",bbox_to_anchor=(0.02,0.58)); ax.grid(alpha=.3,which="both")
plt.tight_layout(); plt.savefig(OUT+"fig3_latency.png",dpi=220,facecolor="white"); plt.close()
# fig4 throughput
fig,ax=plt.subplots(figsize=(5.2,3.6))
for a in N:
    d=sp[sp.arch==a].sort_values("concurrency") if "arch" in sp else None
    ax.plot(d.concurrency,d.thr_rps,marker=M[a],color=C[a],label=N[a])
ax.axhline(174.0,color="#1E6B33",ls=":",label="Eq. (5) ceiling, 174.0/s")
ax.set_yscale("log"); ax.set_xscale("log"); ax.set_xticks(cs); ax.set_xticklabels(cs)
ax.set_xlabel("Concurrent clients"); ax.set_ylabel("Throughput (requests/s)")
ax.legend(fontsize=7); ax.grid(alpha=.3,which="both")
plt.tight_layout(); plt.savefig(OUT+"fig4_throughput.png",dpi=220,facecolor="white"); plt.close()
# fig5 resources (bcz phases)
ph=pd.read_csv(D+"phases.csv"); S={h:pd.read_csv(D+f"sampler_{h}.csv") for h in ["c","v1","v2","v3","v4"]}
rows=[]
for c in cs:
    g=ph[(ph.arch=="bcz")&(ph.phase=="perf")&(ph.detail==f"c={c}")]
    r={"c":c}
    for h,sdf in S.items():
        m=pd.Series(False,index=sdf.index)
        for _,x in g.iterrows(): m|=(sdf.t>=x.t_start)&(sdf.t<=x.t_end)
        d=sdf[m]
        if h=="c": r["gw_cpu"]=d.py_cpu_pct.mean(); r["gw_rss"]=d.py_rss_mb.mean()
        else: r[h+"_cpu"]=d.besu_cpu_pct.mean(); r[h+"_rss"]=d.besu_rss_mb.mean()
    rows.append(r)
R=pd.DataFrame(rows); R.to_csv(D+"resources_bcz_perf.csv",index=False)
fig,(a1,a2)=plt.subplots(1,2,figsize=(7.6,3.2))
vc=R[[f"v{i}_cpu" for i in range(1,5)]]
a1.fill_between(cs,vc.min(axis=1),vc.max(axis=1),color="#1B3E7A",alpha=.2,label="validators (min-max)")
a1.plot(cs,vc.mean(axis=1),marker="o",color="#1B3E7A",label="validator mean")
a1.plot(cs,R.gw_cpu,marker="s",color="#B04A4A",label="gateway process")
a1.set_xscale("log"); a1.set_xticks(cs); a1.set_xticklabels(cs); a1.set_xlabel("Concurrent clients"); a1.set_ylabel("CPU of the process (% of one core)"); a1.legend(fontsize=7); a1.grid(alpha=.3)
vr=R[[f"v{i}_rss" for i in range(1,5)]]
a2.fill_between(cs,vr.min(axis=1),vr.max(axis=1),color="#1B3E7A",alpha=.2,label="validators (min-max)")
a2.plot(cs,vr.mean(axis=1),marker="o",color="#1B3E7A",label="validator mean")
a2.plot(cs,R.gw_rss,marker="s",color="#B04A4A",label="gateway process")
a2.set_xscale("log"); a2.set_xticks(cs); a2.set_xticklabels(cs); a2.set_xlabel("Concurrent clients"); a2.set_ylabel("Resident memory (MB)"); a2.legend(fontsize=7); a2.grid(alpha=.3)
plt.tight_layout(); plt.savefig(OUT+"fig5_cpumem.png",dpi=220,facecolor="white"); plt.close()
# fig6 security
sc=["A1","A2","A3","A4","A5","A6","A7","A8"]; lab=["A1 replay","A2 revoked","A3 flood","A4 lateral","A5 low trust","A6 window","A7 DB tamper","A8 host compr."]
fig,ax=plt.subplots(figsize=(7.2,3.4)); w=.16
for i,a in enumerate(N):
    v=[100*s[(s.arch==a)&(s.scenario==x)].denial.iloc[0] for x in sc]
    ax.bar(np.arange(8)+(i-2)*w,v,w,color=C[a],label=N[a])
    for j,y in enumerate(v):
        if y==0: ax.text(j+(i-2)*w,1.5,'0',ha='center',fontsize=6,color=C[a])
ax.set_xticks(range(8)); ax.set_xticklabels(lab,fontsize=7); ax.set_ylabel("Attacks denied (%)"); ax.set_ylim(0,112)
ax.legend(fontsize=7,ncol=5,loc="upper center"); ax.grid(alpha=.3,axis="y")
plt.tight_layout(); plt.savefig(OUT+"fig6_security.png",dpi=220,facecolor="white"); plt.close()
print(R.round(1).to_string())

# fig7 scale-out and decay
sc_=pd.read_csv(D+"scale_raw.csv")
ph2=ph[ph.phase=="scale"].copy()
ph2[["gateways","concurrency"]]=ph2.detail.str.extract(r"G=(\d+),c=(\d+)").astype(int)
cnt=sc_.groupby(["gateways","concurrency","repeat"]).size().rename("n").reset_index()
g=cnt.merge(ph2[["gateways","concurrency","repeat","t_start","t_end"]],on=["gateways","concurrency","repeat"])
g["rps"]=g.n/(g.t_end-g.t_start)
fig,ax=plt.subplots(figsize=(5.2,3.4))
for c,mk in [(200,"o"),(400,"s")]:
    q=g[g.concurrency==c].groupby("gateways").rps.agg(["mean","std","count"])
    ax.errorbar(q.index,q["mean"],yerr=2.26*q["std"]/np.sqrt(q["count"]),marker=mk,capsize=3,label=f"{c} clients")
ax.axhline(174.0,color="#1E6B33",ls=":",label="Eq. (5) ceiling")
ax.set_xticks([1,2,4]); ax.set_xlabel("Gateway processes"); ax.set_ylabel("Throughput (requests/s)"); ax.set_ylim(0,190)
ax.legend(fontsize=7); ax.grid(alpha=.3); plt.tight_layout(); plt.savefig(OUT+"fig7_scaleout.png",dpi=220,facecolor="white"); plt.close()
print(g.groupby(["gateways","concurrency"]).rps.mean().round(1))
