"""Live experiments against the real 4-validator Besu QBFT network + live/gateway_live.py.

Produces (in evaluation/results_live/):
  live_perf.csv        latency/throughput/grant-rate per concurrency level (via the gateway)
  live_cpu_mem.csv     CPU/memory of validator JVMs and the gateway during each level
  live_security.json   outcome of attack scenarios that the contracts can actually enforce
  live_misc.json       revocation trials, gas per decision, bytes per decision, block stats

Usage (repo root):  ADMIN_PRIVATE_KEY=0x.. python3 live/run_live_experiments.py
"""
import csv, json, os, statistics as st, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil, requests
from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "evaluation" / "results_live"
OUT.mkdir(parents=True, exist_ok=True)
D = json.load(open(ROOT / "deployment.json"))
GW = os.environ.get("GATEWAY_URL", "http://127.0.0.1:9000")
w3 = Web3(Web3.HTTPProvider(D["rpc"], request_kwargs={"timeout": 60}))
admin = Account.from_key(os.environ["ADMIN_PRIVATE_KEY"])
idr = w3.eth.contract(address=D["identityRegistry"], abi=D["abis"]["identityRegistry"])
tm = w3.eth.contract(address=D["trustManager"], abi=D["abis"]["trustManager"])
CHAIN = w3.eth.chain_id
_nl = threading.Lock()
_n = [w3.eth.get_transaction_count(admin.address, "pending")]
PLC = ("plc-line1/setpoint", "write")
RUN = str(int(time.time()))
SEC = "sec-revoked-" + RUN
LOW = "dev-lowtrust"


def addr(d):
    return Web3.to_checksum_address("0x" + Web3.keccak(text=d).hex()[-40:])


def admin_tx(fn):
    with _nl:
        tx = fn.build_transaction({"from": admin.address, "nonce": _n[0], "gas": 400000, "gasPrice": 0, "chainId": CHAIN})
        h = w3.eth.send_raw_transaction(admin.sign_transaction(tx).raw_transaction)
        _n[0] += 1
    return h


def wait(h):
    return w3.eth.wait_for_transaction_receipt(h, timeout=60, poll_latency=0.1)


def check(dev, res=PLC[0], act=PLC[1]):
    r = requests.post(f"{GW}/access-request", json={"device_id": dev, "resource": res, "action": act}, timeout=90).json()
    return r


class Sampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop = False
        self.v, self.g, self.vm, self.gm = [], [], [], []
        procs = list(psutil.process_iter(["cmdline"]))
        self.vp = [p for p in procs if p.info["cmdline"] and "java" in p.info["cmdline"][0] and "besu" in " ".join(p.info["cmdline"])]
        self.gp = [p for p in procs if p.info["cmdline"] and "live.gateway_live" in " ".join(p.info["cmdline"]) and "uvicorn" in " ".join(p.info["cmdline"])]
        for p in self.vp + self.gp:
            p.cpu_percent(None)

    def run(self):
        while not self.stop:
            time.sleep(1)
            try:
                self.v.append(sum(p.cpu_percent(None) for p in self.vp) / max(1, len(self.vp)))
                self.g.append(sum(p.cpu_percent(None) for p in self.gp))
                self.vm.append(sum(p.memory_info().rss for p in self.vp) / max(1, len(self.vp)) / 2**20)
                self.gm.append(sum(p.memory_info().rss for p in self.gp) / 2**20)
            except psutil.Error:
                pass


def load_sweep():
    levels = [(1, 30), (5, 50), (10, 100), (20, 200), (50, 300), (100, 500), (200, 1000)]
    rows, cm = [], []
    for c, n in levels:
        s = Sampler(); s.start(); t0 = time.time()
        with ThreadPoolExecutor(c) as ex:
            res = list(ex.map(lambda i: check(f"device-{i % 200}"), range(n)))
        el = time.time() - t0; s.stop = True; s.join(2)
        lat = sorted(r["latency_ms"] for r in res)
        rows.append(dict(concurrency=c, n_requests=n, latency_mean_ms=round(st.mean(lat), 2), latency_p50_ms=round(st.median(lat), 2),
                         latency_p95_ms=round(lat[int(.95 * n) - 1], 2), latency_max_ms=round(lat[-1], 2), throughput_rps=round(n / el, 2),
                         grant_rate=round(sum(r["granted"] for r in res) / n, 3),
                         error_rate=round(sum(r.get("reason") == "error" for r in res) / n, 3),
                         gas_per_decision=int(st.mean(r.get("gas_used", 0) for r in res))))
        cm.append(dict(concurrency=c, validator_cpu_pct=round(st.mean(s.v or [0]), 1), validator_mem_mb=round(st.mean(s.vm or [0]), 1),
                       gateway_cpu_pct=round(st.mean(s.g or [0]), 1), gateway_mem_mb=round(st.mean(s.gm or [0]), 1)))
        print(rows[-1], flush=True)
    for name, data in (("live_perf.csv", rows), ("live_cpu_mem.csv", cm)):
        with open(OUT / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    return rows


def security():
    out = {}

    def rate(rs):
        return {"denial_rate": round(sum(not r["granted"] for r in rs) / len(rs), 3), "n": len(rs), "reasons": sorted({r["reason"] for r in rs})}

    wait(admin_tx(idr.functions.registerDevice(addr(SEC), Web3.keccak(text="pk"), "sensor", "fw1")))
    assert check(SEC)["granted"]
    wait(admin_tx(idr.functions.revokeDevice(addr(SEC))))
    out["A2_revoked_device"] = rate([check(SEC) for _ in range(20)])
    with ThreadPoolExecutor(100) as ex:
        fl = list(ex.map(lambda i: check(f"attacker-{i}"), range(300)))
    out["A3_flood_unenrolled"] = rate(fl)
    out["A4_lateral_nopolicy"] = rate([check("device-1", "plc-line2/setpoint") for _ in range(20)])
    out["A4_lateral_hightier"] = rate([check("device-1", "relay-feeder7/firmware") for _ in range(20)])
    wait(admin_tx(tm.functions.reportEvidence(addr(LOW), -30, "anomalous-telemetry")))
    out["A5_low_trust"] = rate([check(LOW) for _ in range(20)])
    out["A5_control_legit"] = rate([check("dev-ok") for _ in range(20)])
    out["A6_time_window"] = rate([check("device-2", "plc-line1/night-only") for _ in range(20)])
    out["not_testable_live"] = "A1 replay: AccessControlManager has no signature/nonce verification, so replay is not enforced on-chain in this prototype."
    json.dump(out, open(OUT / "live_security.json", "w"), indent=1)
    print(out, flush=True)
    return out


def revocation(trials=30):
    ts = []
    for k in range(trials):
        d = f"rev-{int(time.time())}-{k}"
        wait(admin_tx(idr.functions.registerDevice(addr(d), Web3.keccak(text="pk"), "sensor", "fw1")))
        assert check(d)["granted"]
        t0 = time.time()
        admin_tx(idr.functions.revokeDevice(addr(d)))
        first = {}

        def one():
            r = check(d)
            if not r["granted"] and "t" not in first:
                first["t"] = time.time()

        while "t" not in first and time.time() - t0 < 30:
            threading.Thread(target=one, daemon=True).start()
            time.sleep(0.2)
        ts.append(round(first.get("t", t0 + 30) - t0, 2))
        print("revocation", k, ts[-1], flush=True)
    return ts


if __name__ == "__main__":
    if os.environ.get("SKIP_SWEEP"):
        perf = [dict(r) for r in csv.DictReader(open(OUT / "live_perf.csv"))]
    else:
        perf = load_sweep()
    sec = security()
    rev = revocation()
    n = w3.eth.block_number
    blks = [w3.provider.make_request("eth_getBlockByNumber", [hex(i), False])["result"] for i in range(max(1, n - 600), n)]
    sizes = [(int(b["size"], 16), len(b["transactions"])) for b in blks if len(b["transactions"]) > 0]
    misc = {"revocation": {"trials": len(rev), "mean_s": round(st.mean(rev), 2), "stdev_s": round(st.stdev(rev), 2),
                           "min_s": min(rev), "max_s": max(rev), "samples": rev},
            "max_tx_in_block_observed": max(t for _, t in sizes),
            "mean_gas_per_decision": perf[-1]["gas_per_decision"],
            "mean_block_bytes_per_tx": round(st.mean(b / t for b, t in sizes), 1),
            "block_gas_limit": int(blks[-1]["gasLimit"], 16), "validators": 4, "client": w3.client_version}
    json.dump(misc, open(OUT / "live_misc.json", "w"), indent=1)
    print(misc)
