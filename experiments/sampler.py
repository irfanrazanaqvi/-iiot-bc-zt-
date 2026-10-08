"""Per-VM resource sampler: once a second, system CPU % and RSS of java (Besu) and python (gateway/harness) processes.
Usage: python3 experiments/sampler.py out.csv   (runs until killed)"""
import csv, sys, time
import psutil

fh = open(sys.argv[1], "w", newline="", buffering=1)
out = csv.writer(fh)
out.writerow(["t", "sys_cpu_pct", "besu_cpu_pct", "besu_rss_mb", "py_cpu_pct", "py_rss_mb"])
def procs(name):
    r = []
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            c = " ".join(p.info["cmdline"] or [])
            if name == "java" and p.info["name"] == "java" and "besu" in c: r.append(p)
            if name == "py" and p.info["name"].startswith("python") and ("gateway_multi" in c or "run_all" in c or "uvicorn" in c): r.append(p)
        except psutil.Error: pass
    return r
cache = {}
psutil.cpu_percent(None)
while True:
    time.sleep(1)
    row = [time.time(), psutil.cpu_percent(None)]
    for n in ("java", "py"):
        cpu = rss = 0.0
        for p in procs(n):
            try:
                if p.pid not in cache: cache[p.pid] = p; p.cpu_percent(None)
                cpu += cache[p.pid].cpu_percent(None); rss += p.memory_info().rss / 2**20
            except psutil.Error: pass
        row += [round(cpu, 1), round(rss, 1)]
    out.writerow(row); fh.flush()
