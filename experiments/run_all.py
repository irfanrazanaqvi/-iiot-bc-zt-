"""Live comparison of four access-control architectures on one gateway and one Besu network.

Phases (all write raw per-request rows; statistics are computed afterwards by analyze.py):
  perf        closed-loop load sweep, repeated
  openloop    Poisson arrivals (mean gap 0.5 s), repeated
  security    attack scenarios A1-A7 plus a legitimate control, repeated
  revocation  time from revoking an identity to the first denied decision, 30 trials

Usage (repo root, gateway running, deployment_v2.json present):
  ADMIN_PRIVATE_KEY=0x.. python3 -m experiments.run_all --out results_run1 [--quick]
"""
import argparse, csv, json, os, random, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from eth_account import Account
from web3 import Web3

from experiments.common import all_ids, device_address, sign_request

ap = argparse.ArgumentParser()
ap.add_argument("--gateway", default="http://127.0.0.1:9000")
ap.add_argument("--out", default="results_run")
ap.add_argument("--archs", nargs="+", default=["b0", "b1", "b2", "b3", "bcz"])
ap.add_argument("--gateways", default="", help="comma separated gateway URLs for the scale-out test (first one is --gateway); empty = skip")
ap.add_argument("--scale-repeats", type=int, default=3)
ap.add_argument("--no-decay", action="store_true")
ap.add_argument("--perf-repeats", type=int, default=5)
ap.add_argument("--sec-repeats", type=int, default=10)
ap.add_argument("--open-repeats", type=int, default=3)
ap.add_argument("--rev-trials", type=int, default=30)
ap.add_argument("--quick", action="store_true", help="tiny smoke run")
A = ap.parse_args()
if A.quick:
    A.perf_repeats = A.sec_repeats = A.open_repeats = 1; A.rev_trials = 3

OUT = Path(A.out); OUT.mkdir(parents=True, exist_ok=True)
D = json.load(open(Path(__file__).with_name("deployment_v2.json")))
RPCS = os.environ.get("BESU_RPCS", "http://127.0.0.1:8545").split(",")
w3 = Web3(Web3.HTTPProvider(RPCS[0], request_kwargs={"timeout": 60}))
CHAIN = w3.eth.chain_id
AC = Web3.to_checksum_address(D["accessControl"])
admin = Account.from_key(os.environ["ADMIN_PRIVATE_KEY"])
idr = w3.eth.contract(address=D["identityRegistry"], abi=D["abis"]["identityRegistry"])
tm = w3.eth.contract(address=D["trustManager"], abi=D["abis"]["trustManager"])
_nl = threading.Lock(); _n = [w3.eth.get_transaction_count(admin.address, "pending")]
PLC = ("plc-line1/setpoint", "write")
HI = ("relay-feeder7/firmware", "write")
CLOSED = ("plc-line1/closed-window", "write")
NOPOL = ("plc-line2/setpoint", "write")
S = requests.Session()
S.mount("http://", requests.adapters.HTTPAdapter(pool_connections=300, pool_maxsize=300))


def chain_tx(fn, acct=None, gas=400000):
    acct = acct or admin
    with _nl:
        nonce = _n[0] if acct is admin else w3.eth.get_transaction_count(acct.address, "pending")
        tx = fn.build_transaction({"from": acct.address, "nonce": nonce, "gas": gas, "gasPrice": 0, "chainId": CHAIN})
        h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
        if acct is admin:
            _n[0] += 1
    return h


def chain_wait(h):
    return w3.eth.wait_for_transaction_receipt(h, timeout=60, poll_latency=0.1)


RETRIES = [0]
FAILS = []


def req(arch, dev, res_act=PLC, nonce=None, sig=None, base=None):
    """One access request.  A transport error (connection reset, timeout) is retried with a FRESH nonce and
    signature, so the retry is a new decision and not a replay; requests with a caller-supplied nonce (the
    replay attack) are never retried.  The round-trip time includes any retry."""
    given = nonce is not None
    t_first = time.time(); r = None
    for attempt in range(4):
        if not given:
            nonce, sig = sign_request(dev, AC, CHAIN, *res_act)
        try:
            r = S.post(f"{base or A.gateway}/{arch}/access-request", timeout=90,
                       json={"device_id": dev, "resource": res_act[0], "action": res_act[1], "nonce": nonce, "sig": sig}).json()
            break
        except (requests.ConnectionError, requests.Timeout, ValueError):
            RETRIES[0] += 1
            if given or attempt == 3:
                r = {"granted": False, "reason": "error"}
                break
            time.sleep(0.3 * (attempt + 1))
    r["rtt_ms"] = (time.time() - t_first) * 1000
    r["t_end"] = time.time()
    r["_nonce"], r["_sig"] = nonce, sig
    return r


def adm(arch, op, **kw):
    if arch in ("b1", "b2", "b3"):
        return S.post(f"{A.gateway}/{arch}/admin/{op}", json=kw, timeout=30).json()


def revoke(arch, dev):
    if arch == "bcz":
        return chain_tx(idr.functions.revokeDevice(device_address(dev)))
    adm(arch, "revoke", device_id=dev)


def evidence(arch, dev, delta, reason="anomalous-telemetry"):
    if arch == "bcz":
        chain_wait(chain_tx(tm.functions.reportEvidence(device_address(dev), delta, reason)))
    else:
        adm(arch, "evidence", device_id=dev, delta=delta)


class Rows:
    def __init__(self, name, fields):
        self.f = open(OUT / name, "w", newline=""); self.w = csv.DictWriter(self.f, fieldnames=fields); self.w.writeheader()
        self.lock = threading.Lock()
    def add(self, **kw):
        with self.lock:
            self.w.writerow(kw); self.f.flush()


PH = Rows("phases.csv", ["phase", "arch", "repeat", "detail", "t_start", "t_end"])
PERF = Rows("perf_raw.csv", ["arch", "repeat", "concurrency", "idx", "rtt_ms", "gw_ms", "granted", "reason", "gas_used", "t_end"])
OPEN = Rows("openloop_raw.csv", ["arch", "repeat", "idx", "rtt_ms", "gw_ms", "granted", "reason", "gas_used"])
SEC = Rows("security_raw.csv", ["arch", "repeat", "scenario", "role", "idx", "granted", "reason", "rtt_ms", "extra"])
REV = Rows("revocation_raw.csv", ["arch", "trial", "revocation_s", "timed_out"])
DECAY = Rows("decay_raw.csv", ["arch", "dev", "kind", "t_rel", "score", "pred", "granted", "expect_grant", "reason"])
SCALE = Rows("scale_raw.csv", ["gateways", "concurrency", "repeat", "idx", "rtt_ms", "granted", "reason", "gas_used", "t_end"])


def seed():
    ids = all_ids()
    for a in ("b1", "b2", "b3"):
        adm(a, "seed", ids=ids)


def phase_perf(arch, rep):
    levels = [(1, 30), (10, 100), (50, 300), (100, 500), (200, 1000)]
    if A.quick: levels = [(1, 6), (10, 20), (50, 60)]
    for c, n in levels:
        adm(arch, "reset")   # fresh rate-limit windows: a baseline that finishes a level in seconds must not be throttled by an earlier level
        t0 = time.time()
        with ThreadPoolExecutor(c) as ex:
            res = list(ex.map(lambda i: req(arch, f"device-{i % 200}"), range(n)))
        PH.add(phase="perf", arch=arch, repeat=rep, detail=f"c={c}", t_start=t0, t_end=time.time())
        for i, r in enumerate(res):
            PERF.add(arch=arch, repeat=rep, concurrency=c, idx=i, rtt_ms=round(r["rtt_ms"], 2), gw_ms=round(r.get("latency_ms", 0), 2),
                     granted=int(r["granted"]), reason=r["reason"], gas_used=r.get("gas_used", ""), t_end=r["t_end"])
        print(arch, "perf", rep, c, "mean", round(sum(r["rtt_ms"] for r in res) / n), "ms; grant", round(sum(r["granted"] for r in res) / n, 3), flush=True)


def phase_open(arch, rep):
    rnd = random.Random(1000 + rep); n = 40 if A.quick else 100; res = [None] * n; ths = []
    def one(i): res[i] = req(arch, f"device-{(i * 7 + rep) % 200}")
    t0 = time.time()
    for i in range(n):
        t = threading.Thread(target=one, args=(i,)); t.start(); ths.append(t); time.sleep(rnd.expovariate(1 / 0.5))
    for t in ths: t.join()
    PH.add(phase="openloop", arch=arch, repeat=rep, detail="", t_start=t0, t_end=time.time())
    for i, r in enumerate(res):
        OPEN.add(arch=arch, repeat=rep, idx=i, rtt_ms=round(r["rtt_ms"], 2), gw_ms=round(r.get("latency_ms", 0), 2),
                 granted=int(r["granted"]), reason=r["reason"], gas_used=r.get("gas_used", ""))


def burst(arch, dev, res_act=PLC, n=20, workers=10, **kw):
    """n independent requests sent concurrently (each with its own fresh nonce)."""
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda _: req(arch, dev, res_act, **kw), range(n)))


def log(arch, rep, scen, role, rs, extra=""):
    for i, r in enumerate(rs):
        SEC.add(arch=arch, repeat=rep, scenario=scen, role=role, idx=i, granted=int(r["granted"]), reason=r["reason"], rtt_ms=round(r["rtt_ms"], 1), extra=extra)


def phase_security(arch, rep):
    t0 = time.time(); k = rep
    N = 5 if A.quick else 20
    # A1 replay: capture one valid request, resend it verbatim
    dev = f"device-{(k * 3) % 200}"; first = req(arch, dev)
    log(arch, rep, "A1", "legit-first", [first])
    log(arch, rep, "A1", "attack", burst(arch, dev, PLC, N, nonce=first["_nonce"], sig=first["_sig"]))
    # A2 revoked identity keeps trying
    dev = f"sec-rev-{k}"; log(arch, rep, "A2", "legit-first", [req(arch, dev)])
    h = revoke(arch, dev)
    if h: chain_wait(h)
    log(arch, rep, "A2", "attack", burst(arch, dev, PLC, N))
    # A3 flood from an enrolled device: 3x the permitted rate in a burst
    dev = f"sec-flood-{k}"; total = 3 * D["maxPerWindow"] if not A.quick else 8
    with ThreadPoolExecutor(10) as ex: fl = list(ex.map(lambda _: req(arch, dev), range(total)))
    log(arch, rep, "A3", "attack", fl, extra=f"limit={D['maxPerWindow']};total={total}")
    # A4 lateral movement: resource without policy, and a higher-tier resource below its trust threshold
    dev = f"device-{(k * 3 + 1) % 200}"
    log(arch, rep, "A4", "attack", burst(arch, dev, NOPOL, N // 2 or 1) + burst(arch, dev, HI, N // 2 or 1))
    # A5 compromised sensor: negative evidence drives trust below theta
    dev = f"sec-low-{k}"; evidence(arch, dev, -30)
    log(arch, rep, "A5", "attack", burst(arch, dev, PLC, N))
    # A6 access outside the permitted time window
    dev = f"device-{(k * 3 + 2) % 200}"
    log(arch, rep, "A6", "attack", burst(arch, dev, CLOSED, N))
    # A7 store tampering: low-trust device, then someone with write access to the trust store (but not the
    #    on-chain owner/monitor key) tries to raise its score
    dev = f"sec-tam-{k}"; evidence(arch, dev, -30)
    ok = ""
    if arch == "bcz":
        atk = Account.create()
        try:
            rc = chain_wait(chain_tx(tm.functions.reportEvidence(device_address(dev), 70, "forged"), acct=atk))
            ok = f"tamper_tx_status={rc['status']}"
        except Exception as e:  # noqa: BLE001
            ok = "tamper_rejected:" + str(e)[:60]
    else:
        adm(arch, "tamper", device_id=dev); ok = "tamper_applied"
    log(arch, rep, "A7", "attack", burst(arch, dev, PLC, N), extra=ok)
    # A8 decision-host compromise: the attacker controls the machine that runs the decision service and so holds
    #    everything on it (database, integrity key, gateway signing keys), and tries to raise a low-trust device's score
    dev = f"sec-host-{k}"; evidence(arch, dev, -30)
    ok = ""
    if arch == "bcz":
        seed = os.environ.get("GATEWAY_SEED")
        atk = Account.from_key(Web3.keccak(text=f"{seed}:0")) if seed else Account.create()   # a real gateway signing key
        try:
            rc = chain_wait(chain_tx(tm.functions.reportEvidence(device_address(dev), 70, "forged"), acct=atk))
            ok = f"tamper_tx_status={rc['status']};gateway_key={bool(seed)}"
        except Exception as e:  # noqa: BLE001
            ok = "tamper_rejected:" + str(e)[:60]
    else:
        adm(arch, "tamper_host", device_id=dev); ok = "tamper_applied"
    log(arch, rep, "A8", "attack", burst(arch, dev, PLC, N), extra=ok)
    # control: a legitimate device issuing a normal number of requests must be granted
    dev = f"sec-ctrl-{k}"
    log(arch, rep, "CTRL", "legit", burst(arch, dev, PLC, N))
    PH.add(phase="security", arch=arch, repeat=rep, detail="", t_start=t0, t_end=time.time())
    print(arch, "security", rep, "done", flush=True)


def phase_rev(arch):
    if arch == "b0": return
    for k in range(A.rev_trials):
        dev = f"rev-{k}"
        if not req(arch, dev)["granted"]:
            print("WARNING: identity", dev, "was already revoked or unusable; trial skipped (fresh deployment needed)", flush=True)
            continue
        t0 = time.time(); revoke(arch, dev); first = {}
        def one():
            r = req(arch, dev)
            if not r["granted"] and "t" not in first: first["t"] = r["t_end"]
        while "t" not in first and time.time() - t0 < 30:
            threading.Thread(target=one, daemon=True).start(); time.sleep(0.2 if arch == "bcz" else 0.01)
        time.sleep(1.0 if arch == "bcz" else 0.1)
        REV.add(arch=arch, trial=k, revocation_s=round(first.get("t", t0 + 30) - t0, 3), timed_out=int("t" not in first))
        print(arch, "revocation", k, round(first.get("t", t0 + 30) - t0, 3), flush=True)


DECAY_UNIT_S = 6      # one "day" of decay shortened to 6 s for the validation test (contract and B2/B3 alike)
DECAY_T0, DECAY_STEP = 50, 2   # default score and kappa of the deployed contracts


def blk_ts(bn):
    return int(w3.provider.make_request("eth_getBlockByNumber", [hex(bn), False])["result"]["timestamp"], 16)


def phase_decay(arch):
    """Validate the decay law (Eq. 1): a score re-anchored at t_last must fall by kappa per elapsed decay unit.
    Samples the score every second for ~50 s on 6 devices; also checks the access decision before and after the crossing
    of theta = 40 (predicted at 6 units = 36 s)."""
    if arch == "bcz":
        chain_wait(chain_tx(tm.functions.setDecayUnit(DECAY_UNIT_S)))
    else:
        adm(arch, "decay_unit", delta=DECAY_UNIT_S)
    try:
        def one(k):
            dev = f"dec-{k}"; addr = device_address(dev)
            if arch == "bcz":
                rc = chain_wait(chain_tx(tm.functions.reportEvidence(addr, DECAY_T0 - tm.functions.getScore(addr).call(), "decay-anchor")))
                t_last = blk_ts(rc["blockNumber"])
            else:
                adm(arch, "evidence", device_id=dev, delta=DECAY_T0 - adm(arch, "score", device_id=dev)["score"]); t_last = time.time()
            t0 = time.time(); done = set()
            while True:
                if arch == "bcz":
                    bn = w3.eth.block_number; now = blk_ts(bn)
                    sc = tm.functions.getScore(addr).call(block_identifier=bn)
                else:
                    now = time.time(); sc = adm(arch, "score", device_id=dev)["score"]
                rel = now - t_last
                pred = max(0, DECAY_T0 - DECAY_STEP * int(rel // DECAY_UNIT_S)) if rel >= 0 else DECAY_T0
                DECAY.add(arch=arch, dev=dev, kind="sample", t_rel=round(rel, 2), score=sc, pred=pred, granted="", expect_grant="", reason="")
                for tag, at in (("pre", 30), ("post", 42)):
                    if tag not in done and time.time() - t0 >= at - 2:   # the decision is mined ~2 s later
                        done.add(tag); r = req(arch, dev)
                        DECAY.add(arch=arch, dev=dev, kind="decision_" + tag, t_rel=round(time.time() - t0, 2), score="", pred="", granted=int(r["granted"]),
                                  expect_grant=int(tag == "pre"), reason=r["reason"])
                if time.time() - t0 > 46: break
                time.sleep(1.0)
        with ThreadPoolExecutor(6) as ex: list(ex.map(one, range(6)))
        print(arch, "decay done", flush=True)
    finally:
        if arch == "bcz": chain_wait(chain_tx(tm.functions.setDecayUnit(86400)))
        else: adm(arch, "decay_unit", delta=0)


def phase_scale():
    """Closed-loop load against BC-ZT through 1, 2 and 4 gateway processes (each with its own signing accounts)."""
    gws = [g for g in A.gateways.split(",") if g]
    levels = [(1, 200), (2, 200), (4, 200), (1, 400), (2, 400), (4, 400)] if not A.quick else [(1, 40), (2, 40)]
    for G, c in levels:
        if G > len(gws): continue
        for rep in range(A.scale_repeats if not A.quick else 1):
            n = c * 5 if not A.quick else 40
            t0 = time.time()
            with ThreadPoolExecutor(c) as ex:
                res = list(ex.map(lambda i: req("bcz", f"scl-{(rep * n + i) % 1000}", base=gws[i % G]), range(n)))
            PH.add(phase="scale", arch="bcz", repeat=rep, detail=f"G={G},c={c}", t_start=t0, t_end=time.time())
            for i, r in enumerate(res):
                SCALE.add(gateways=G, concurrency=c, repeat=rep, idx=i, rtt_ms=round(r["rtt_ms"], 2), granted=int(r["granted"]), reason=r["reason"],
                          gas_used=r.get("gas_used", ""), t_end=r["t_end"])
            print("scale G", G, "c", c, "rep", rep, "req/s", round(n / (time.time() - t0), 1), flush=True)


def guarded(fn, *a):
    """Run one phase; a failure is logged and the run continues with the next phase."""
    try:
        fn(*a)
    except Exception as e:  # noqa: BLE001
        import traceback
        FAILS.append(f"{fn.__name__}{a}: {type(e).__name__}: {str(e)[:120]}")
        print("PHASE FAILED:", FAILS[-1], flush=True); traceback.print_exc()
        time.sleep(5)


if __name__ == "__main__":
    seed()
    meta = {"started": time.time(), "args": vars(A), "deployment": {k: D[k] for k in ("accessControl", "maxPerWindow", "windowSeconds", "closedWindow")},
            "client_version": w3.client_version, "block_start": w3.eth.block_number}
    for arch in A.archs:
        for rep in range(A.perf_repeats): guarded(phase_perf, arch, rep)
        for rep in range(A.open_repeats): guarded(phase_open, arch, rep)
        for rep in range(A.sec_repeats): guarded(phase_security, arch, rep)
        guarded(phase_rev, arch)
    if A.gateways and "bcz" in A.archs: guarded(phase_scale)
    if not A.no_decay:
        for arch in A.archs:
            if arch in ("b2", "b3", "bcz"): guarded(phase_decay, arch)
    n = w3.eth.block_number
    blocks = [w3.provider.make_request("eth_getBlockByNumber", [hex(i), False])["result"] for i in range(max(1, meta["block_start"]), n)]
    meta["blocks"] = [{"n": int(b["number"], 16), "size": int(b["size"], 16), "tx": len(b["transactions"]), "gas_used": int(b["gasUsed"], 16),
                       "gas_limit": int(b["gasLimit"], 16), "ts": int(b["timestamp"], 16)} for b in blocks]
    meta["finished"] = time.time(); meta["retries"] = RETRIES[0]; meta["phase_failures"] = FAILS
    json.dump(meta, open(OUT / "meta.json", "w"))
    print("done ->", OUT, "| retries:", RETRIES[0], "| failed phases:", len(FAILS), flush=True)
