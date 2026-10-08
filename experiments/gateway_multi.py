"""One gateway (PEP), four access-control back ends, identical request path.

  /b0/...   no access control                      (grants everything)
  /b1/...   static role-based access control       (role table in memory; no trust, time, replay or rate checks)
  /b2/...   centralized zero trust                 (same decision logic as the contract, kept in SQLite)
  /bcz/...  proposed blockchain zero trust         (every decision is a transaction on Besu QBFT)

POST /{arch}/access-request  {device_id, resource, action, nonce, sig}
POST /{arch}/admin/{seed|revoke|evidence|tamper}   (b1 and b2 only; bcz admin goes on-chain from the harness)

Run (repo root):  GATEWAY_SEED=<any secret> uvicorn experiments.gateway_multi:app --port 9000
Env: BESU_RPCS=comma separated validator RPC URLs (default 127.0.0.1:8545..8548), GATEWAY_SIGNERS=64.
"""
import collections, itertools, json, os, sqlite3, threading, time
from pathlib import Path

import anyio
from eth_account import Account
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from web3 import Web3

from experiments.common import device_address, recover_signer

D = json.load(open(Path(__file__).with_name("deployment_v2.json")))
RPCS = os.environ.get("BESU_RPCS", ",".join(f"http://127.0.0.1:{8545 + i}" for i in range(4))).split(",")
W3S = [Web3(Web3.HTTPProvider(u, request_kwargs={"timeout": 60})) for u in RPCS]
w3 = W3S[0]
CHAIN_ID = w3.eth.chain_id
AC_ADDR = Web3.to_checksum_address(D["accessControl"])
POLICIES = {(r, a): (th, f, t) for r, a, th, f, t in D["policies"]}
MAXW, WINS = D["maxPerWindow"], D["windowSeconds"]

app = FastAPI(title="IIoT ZT gateway (multi-architecture)")
ERRORS = collections.Counter()


@app.on_event("startup")
async def _pool():
    anyio.to_thread.current_default_thread_limiter().total_tokens = 400


class Req(BaseModel):
    device_id: str
    resource: str
    action: str
    nonce: int = 0
    sig: str = "0x"


class Admin(BaseModel):
    ids: list[str] = []
    device_id: str = ""
    delta: int = 0


# ------------------------------------------------------------------ B0
def decide_b0(r: Req):
    return True, "granted", {}


# ------------------------------------------------------------------ B1 static RBAC
B1_ENROLLED: set[str] = set()
B1_PERMS = {("plc-line1/setpoint", "write"), ("plc-line1/closed-window", "write")}  # role "operator"


def decide_b1(r: Req):
    if r.device_id not in B1_ENROLLED:
        return False, "no-role", {}
    if (r.resource, r.action) not in B1_PERMS:
        return False, "role-denied", {}
    return True, "granted", {}


# ------------------------------------------------------------------ B2 centralized ZT (same logic, SQLite state)
_db = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
_dbl = threading.Lock()
_db.executescript("""CREATE TABLE identity(addr TEXT PRIMARY KEY, active INT);
CREATE TABLE trust(addr TEXT PRIMARY KEY, score INT, updated REAL);
CREATE TABLE nonce(k TEXT PRIMARY KEY);
CREATE TABLE win(addr TEXT PRIMARY KEY, start REAL, cnt INT);""")


def _score(addr, now):
    row = _db.execute("SELECT score, updated FROM trust WHERE addr=?", (addr,)).fetchone()
    if not row:
        return 50
    days = int((now - row[1]) // 86400)
    return max(0, row[0] - 2 * days)


def decide_b2(r: Req):
    now = time.time()
    dev = device_address(r.device_id)
    pol = POLICIES.get((r.resource, r.action))
    with _dbl:
        if not pol:
            return False, "no-policy", {}
        row = _db.execute("SELECT active FROM identity WHERE addr=?", (dev,)).fetchone()
        if not row or not row[0]:
            return False, "identity-invalid", {}
        if recover_signer(AC_ADDR, CHAIN_ID, dev, r.resource, r.action, r.nonce, r.sig) != dev:
            return False, "bad-signature", {}
        k = f"{dev}:{r.nonce}"
        if _db.execute("SELECT 1 FROM nonce WHERE k=?", (k,)).fetchone():
            return False, "replay", {}
        _db.execute("INSERT INTO nonce VALUES(?)", (k,))
        w = _db.execute("SELECT start, cnt FROM win WHERE addr=?", (dev,)).fetchone()
        start, cnt = (w if w else (0.0, 0))
        if now >= start + WINS:
            start, cnt = now, 0
        cnt += 1
        _db.execute("INSERT OR REPLACE INTO win VALUES(?,?,?)", (dev, start, cnt))
        if cnt > MAXW:
            return False, "rate-limited", {}
        th, f, t = pol
        if _score(dev, now) < th:
            return False, "insufficient-trust", {}
        hour = int(now // 3600) % 24
        if f != t:
            ok = (f <= hour < t) if f < t else (hour >= f or hour < t)
            if not ok:
                return False, "outside-time-window", {}
    return True, "granted", {}


@app.post("/{arch}/admin/{op}")
def admin(arch: str, op: str, a: Admin):
    if arch == "b1":
        if op == "seed":
            B1_ENROLLED.update(a.ids)
        elif op == "revoke":
            B1_ENROLLED.discard(a.device_id)
        # evidence / tamper: static RBAC has no trust state, nothing to change
        return {"ok": True}
    if arch == "b2":
        with _dbl:
            if op == "seed":
                _db.executemany("INSERT OR REPLACE INTO identity VALUES(?,1)", [(device_address(i),) for i in a.ids])
            elif op == "revoke":
                _db.execute("UPDATE identity SET active=0 WHERE addr=?", (device_address(a.device_id),))
            elif op == "evidence":
                dev = device_address(a.device_id); now = time.time()
                s = max(0, min(100, _score(dev, now) + a.delta))
                _db.execute("INSERT OR REPLACE INTO trust VALUES(?,?,?)", (dev, s, now))
            elif op == "tamper":   # insider with write access to the store sets the trust score directly
                _db.execute("INSERT OR REPLACE INTO trust VALUES(?,?,?)", (device_address(a.device_id), 100, time.time()))
        return {"ok": True}
    raise HTTPException(404, "no admin API for this architecture")


# ------------------------------------------------------------------ BCZ proposed (Besu QBFT)
AC_ABI = D["abis"]["accessControl"]
SEED = os.environ.get("GATEWAY_SEED", "dev-seed")
POOL = []
for i in range(int(os.environ.get("GATEWAY_SIGNERS", "64"))):
    acct = Account.from_key(Web3.keccak(text=f"{SEED}:{i}"))
    wi = W3S[i % len(W3S)]
    POOL.append({"acct": acct, "lock": threading.Lock(), "w3": wi, "ac": wi.eth.contract(address=AC_ADDR, abi=AC_ABI),
                 "nonce": wi.eth.get_transaction_count(acct.address, "pending")})
_rr = itertools.count()
WAIT: dict = {}
_wl = threading.Lock()


def _watcher():
    """One thread follows the chain head and releases requests whose transaction was mined."""
    last = w3.eth.block_number
    while True:
        try:
            head = w3.eth.block_number
            for n in range(last + 1, head + 1):
                for h in w3.provider.make_request("eth_getBlockByNumber", [hex(n), False])["result"]["transactions"]:
                    with _wl:
                        w = WAIT.get(bytes.fromhex(h[2:]))
                    if w:
                        w[1] = w3.eth.get_transaction_receipt(h)
                        w[0].set()
            last = max(last, head)
        except Exception as e:  # noqa: BLE001
            ERRORS["watcher:" + str(e)[:60]] += 1
        time.sleep(0.1)


threading.Thread(target=_watcher, daemon=True).start()


def decide_bcz(r: Req):
    dev = device_address(r.device_id)
    s = POOL[next(_rr) % len(POOL)]
    sig = bytes.fromhex(r.sig[2:])
    waiter = None
    for attempt in range(3):
        with s["lock"]:
            try:
                tx = s["ac"].functions.checkAccess(dev, r.resource, r.action, r.nonce, sig).build_transaction(
                    {"from": s["acct"].address, "nonce": s["nonce"], "gas": 600000, "gasPrice": 0, "chainId": CHAIN_ID})
                raw = s["acct"].sign_transaction(tx).raw_transaction
                h = Web3.keccak(raw)
                waiter = [threading.Event(), None]
                with _wl:
                    WAIT[bytes(h)] = waiter
                s["w3"].eth.send_raw_transaction(raw)
                s["nonce"] += 1
                break
            except Exception as e:  # noqa: BLE001
                ERRORS[str(e)[:80]] += 1
                s["nonce"] = s["w3"].eth.get_transaction_count(s["acct"].address, "pending")
                if attempt == 2:
                    raise
    if not waiter[0].wait(40):
        with s["lock"]:
            s["nonce"] = s["w3"].eth.get_transaction_count(s["acct"].address, "pending")
        with _wl:
            WAIT.pop(bytes(h), None)
        raise TimeoutError("receipt timeout")
    with _wl:
        rc = WAIT.pop(bytes(h))[1]
    ev = s["ac"].events.AccessDecision().process_receipt(rc)
    if not ev:
        return False, "no-event", {"gas_used": rc["gasUsed"]}
    return bool(ev[0]["args"]["granted"]), ev[0]["args"]["reason"], {"gas_used": rc["gasUsed"], "block": rc["blockNumber"]}


ARCH = {"b0": decide_b0, "b1": decide_b1, "b2": decide_b2, "bcz": decide_bcz}


@app.post("/{arch}/access-request")
def access_request(arch: str, r: Req):
    t0 = time.time()
    try:
        g, reason, extra = ARCH[arch](r)
        return {"granted": g, "reason": reason, "latency_ms": (time.time() - t0) * 1000, **extra}
    except Exception as e:  # noqa: BLE001
        return {"granted": False, "reason": "error", "error": str(e)[:200], "latency_ms": (time.time() - t0) * 1000}


@app.get("/health")
def health():
    return {"connected": w3.is_connected(), "block": w3.eth.block_number, "errors": dict(ERRORS)}
