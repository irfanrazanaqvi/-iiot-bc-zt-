"""
Benchmark harness for Section 6 (Experimental Methodology) / Section 7 (Results).

Drives concurrent access-request load against the ZT Gateway and records, per request:
  - end-to-end latency (device -> gateway -> smart contract -> receipt)
  - grant/deny outcome (for authorization-accuracy metrics)
  - wall-clock throughput (requests/sec) at increasing concurrency levels

Outputs a CSV that scripts/plot_results.py turns into the latency/throughput figures.

Usage:
  python latency_throughput_test.py --gateway-url http://localhost:9000 \
      --concurrency 1 5 10 20 50 --requests-per-level 200 --out results.csv
"""

import argparse
import csv
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def single_request(gateway_url, device_id, resource, action):
    payload = {"device_id": device_id, "resource": resource, "action": action}
    t0 = time.time()
    try:
        resp = requests.post(f"{gateway_url}/access-request", json=payload, timeout=10)
        latency_ms = (time.time() - t0) * 1000
        granted = resp.json().get("granted", False)
        return latency_ms, granted, resp.status_code
    except requests.RequestException:
        return (time.time() - t0) * 1000, False, 0


def run_level(gateway_url, concurrency, n_requests, resource, action):
    latencies, grants, statuses = [], [], []
    start = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(single_request, gateway_url, f"device-{i % concurrency}", resource, action)
            for i in range(n_requests)
        ]
        for f in as_completed(futures):
            lat, granted, status = f.result()
            latencies.append(lat)
            grants.append(granted)
            statuses.append(status)
    elapsed = time.time() - start
    throughput = n_requests / elapsed if elapsed > 0 else 0

    return {
        "concurrency": concurrency,
        "n_requests": n_requests,
        "throughput_rps": round(throughput, 3),
        "latency_mean_ms": round(statistics.mean(latencies), 2),
        "latency_p50_ms": round(statistics.median(latencies), 2),
        "latency_p95_ms": round(sorted(latencies)[int(0.95 * len(latencies)) - 1], 2),
        "latency_max_ms": round(max(latencies), 2),
        "grant_rate": round(sum(grants) / len(grants), 3),
        "error_rate": round(sum(1 for s in statuses if s not in (200,)) / len(statuses), 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway-url", default="http://localhost:9000")
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 5, 10, 20, 50])
    parser.add_argument("--requests-per-level", type=int, default=200)
    parser.add_argument("--resource", default="plc-line1/setpoint")
    parser.add_argument("--action", default="write")
    parser.add_argument("--out", default="results.csv")
    args = parser.parse_args()

    rows = []
    for c in args.concurrency:
        print(f"Running concurrency={c} ...")
        row = run_level(args.gateway_url, c, args.requests_per_level, args.resource, args.action)
        print(row)
        rows.append(row)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Results written to {args.out}")


if __name__ == "__main__":
    main()
