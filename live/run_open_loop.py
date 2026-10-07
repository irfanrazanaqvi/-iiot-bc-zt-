"""Open-loop latency test: requests arrive at random times (Poisson, mean gap 0.5 s), independent of
when earlier requests finish -- the way periodic IIoT devices actually behave. The closed-loop sweep in
run_live_experiments.py fires each request right after the previous reply, which phase-locks the
client to block boundaries and always waits ~one full 2 s block.

Usage: python3 live/run_open_loop.py   (needs live/gateway_live.py running)
"""
import json, random, statistics as st, threading, time
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "evaluation" / "results_live"
random.seed(42)
N, MEAN_GAP = 200, 0.5
res = []


def one(i):
    r = requests.post("http://127.0.0.1:9000/access-request",
                      json={"device_id": f"device-{i % 200}", "resource": "plc-line1/setpoint", "action": "write"}, timeout=90).json()
    res.append(r)


ths = []
for i in range(N):
    t = threading.Thread(target=one, args=(i,)); t.start(); ths.append(t)
    time.sleep(random.expovariate(1 / MEAN_GAP))
for t in ths:
    t.join()
lat = sorted(r["latency_ms"] for r in res)
out = {"n": N, "mean_arrival_gap_s": MEAN_GAP, "latency_mean_ms": round(st.mean(lat), 1), "latency_p50_ms": round(st.median(lat), 1),
       "latency_p95_ms": round(lat[int(.95 * N) - 1], 1), "latency_max_ms": round(lat[-1], 1),
       "grant_rate": round(sum(r["granted"] for r in res) / N, 3)}
json.dump(out, open(OUT / "live_openloop.json", "w"), indent=1)
print(out)
