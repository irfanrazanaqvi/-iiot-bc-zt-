"""One gateway (PEP), five access-control back ends, identical request path.

  /b0/...   no access control                      (grants everything)
  /b1/...   static role-based access control       (role table in memory; no trust, time, replay or rate checks)
  /b2/...   centralized zero trust                 (same decision logic as the contract, kept in SQLite)
  /b3/...   hardened centralized zero trust        (b2 + HMAC-protected state rows + hash-chained audit log)
  /bcz/...  proposed blockchain zero trust         (every decision is a transaction on Besu QBFT)

POST /{arch}/access-request  {device_id, resource, action, nonce, sig}
POST /{arch}/admin/{seed|revoke|evidence|tamper}   (b1, b2, b3 only; bcz admin goes on-chain from the harness)

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


# ------------------------------------------------------------------ B2 / B3 centralized ZT (same decision logic)
# B2: plain SQLite state.  B3: hardened centralized service, same logic plus (i) an HMAC over every identity and trust row
# under a key that lives only in this process, so a party that writes to the database file without the key is detected
# (fail closed, reason "state-integrity"), and (ii) a hash-chained, append-only audit log of every decision.
import hashlib, hmac as _hmac

DECAY_UNIT = [86400.0]   # seconds per decay step; shortened only by the trust-decay validation test


class CentralStore:
    def __init__(self, hardened: bool):
        self.h = hardened
        self.key = os.urandom(32)
        self.db = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
        self.lock = threading.Lock()
        self.last = "0" * 64
        self.db.executescript("""CREATE TABLE identity(addr TEXT PRIMARY KEY, active INT, mac TEXT);
CREATE TABLE trust(addr TEXT PRIMARY KEY, score INT, updated REAL, mac TEXT);
CREATE TABLE nonce(k TEXT PRIMARY KEY);
CREATE TABLE win(addr TEXT PRIMARY KEY, start REAL, cnt INT);
CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, h TEXT);""")

    def mac(self, *f):
        return _hmac.new(self.key, "|".join(map(str, f)).encode(), hashlib.sha256).hexdigest() if self.h else ""

    def put_identity(self, addr, active):
        self.db.execute("INSERT OR REPLACE INTO identity VALUES(?,?,?)", (addr, active, self.mac("id", addr, active)))

    def put_trust(self, addr, score, updated, forge=None):
        self.db.execute("INSERT OR REPLACE INTO trust VALUES(?,?,?,?)", (addr, score, updated, forge if forge is not None else self.mac("tr", addr, score, updated)))

    def score(self, addr, now):
        row = self.db.execute("SELECT score, updated, mac FROM trust WHERE addr=?", (addr,)).fetchone()
        if not row:
            return 50
        if self.h and not _hmac.compare_digest(row[2], self.mac("tr", addr, row[0], row[1])):
            return None   # integrity failure
        return max(0, row[0] - 2 * int((now - row[1]) // DECAY_UNIT[0]))

    def audit(self, dev, r, granted, reason):
        if self.h:
            self.last = hashlib.sha256((self.last + f"{dev}|{r.resource}|{r.action}|{granted}|{reason}").encode()).hexdigest()
            self.db.execute("INSERT INTO audit(h) VALUES(?)", (self.last,))

    def decide(self, r: Req):
        with self.lock:   # decision and audit append are one atomic step (the audit chain must be ordered)
            g, reason = self._decide(r)
            self.audit(r.device_id, r, g, reason)
        return g, reason, {}

    def _decide(self, r: Req):
        now = time.time()
        dev = device_address(r.device_id)
        pol = POLICIES.get((r.resource, r.action))
        if True:
            if not pol:
                return False, "no-policy"
            row = self.db.execute("SELECT active, mac FROM identity WHERE addr=?", (dev,)).fetchone()
            if self.h and row and not _hmac.compare_digest(row[1], self.mac("id", dev, row[0])):
                return False, "state-integrity"
            if not row or not row[0]:
                return False, "identity-invalid"
            if recover_signer(AC_ADDR, CHAIN_ID, dev, r.resource, r.action, r.nonce, r.sig) != dev:
                return False, "bad-signature"
            k = f"{dev}:{r.nonce}"
            if self.db.execute("SELECT 1 FROM nonce WHERE k=?", (k,)).fetchone():
                return False, "replay"
            self.db.execute("INSERT INTO nonce VALUES(?)", (k,))
            w = self.db.execute("SELECT start, cnt FROM win WHERE addr=?", (dev,)).fetchone()
            start, cnt = (w if w else (0.0, 0))
            if now >= start + WINS:
                start, cnt = now, 0
            cnt += 1
            self.db.execute("INSERT OR REPLACE INTO win VALUES(?,?,?)", (dev, start, cnt))
            if cnt > MAXW:
                return False, "rate-limited"
            th, f, t = pol
            s = self.score(dev, now)
            if s is None:
                return False, "state-integrity"
            if s < th:
                return False, "insufficient-trust"
            hour = int(now // 3600) % 24
            if f != t:
                ok = (f <= hour < t) if f < t else (hour >= f or hour < t)
                if not ok:
                    return False, "outside-time-window"
        return True, "granted"


STORES = {"b2": CentralStore(False), "b3": CentralStore(True)}


def decide_b2(r: Req): return STORES["b2"].decide(r)
def decide_b3(r: Req): return STORES["b3"].decide(r)


@app.post("/{arch}/admin/{op}")
def admin(arch: str, op: str, a: Admin):
    if arch == "b1":
        if op == "seed":
            B1_ENROLLED.update(a.ids)
        elif op == "revoke":
            B1_ENROLLED.discard(a.device_id)
        # evidence / tamper: static RBAC has no trust state, nothing to change
        return {"ok": True}
    if arch in STORES:
        S_ = STORES[arch]
        with S_.lock:
            if op == "decay_unit":
                DECAY_UNIT[0] = float(a.delta) if a.delta > 0 else 86400.0
            elif op == "reset":   # clear rate-limit windows and nonces between load levels
                S_.db.execute("DELETE FROM win"); S_.db.execute("DELETE FROM nonce")
            elif op == "seed":
                for i in a.ids:
                    S_.put_identity(device_address(i), 1)
            elif op == "revoke":
                S_.put_identity(device_address(a.device_id), 0)
            elif op == "evidence":
                dev = device_address(a.device_id); now = time.time()
                s = S_.score(dev, now)
                s = max(0, min(100, (50 if s is None else s) + a.delta))
                S_.put_trust(dev, s, now)
            elif op == "score":
                return {"ok": True, "score": S_.score(device_address(a.device_id), time.time())}
            elif op == "tamper":       # writes the database file directly: no key, so no valid MAC
                S_.put_trust(device_address(a.device_id), 100, time.time(), forge="00" * 32)
            elif op == "tamper_host":  # the decision host is compromised: the attacker holds the key too
                S_.put_trust(device_address(a.device_id), 100, time.time())
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


from concurrent.futures import ThreadPoolExecutor

# The watcher follows the chain through the validator nearest to the gateway (WATCH_RPC), and fetches the
# receipts of each block in parallel, so the lookup cost is one short round trip per block and not one
# long-distance round trip per transaction.
WW = Web3(Web3.HTTPProvider(os.environ.get("WATCH_RPC", RPCS[0]), request_kwargs={"timeout": 60}))
_rx = ThreadPoolExecutor(32)


def _release(h):
    key = bytes.fromhex(h[2:])
    with _wl:
        w = WAIT.get(key)
    if not w:
        return
    for k in range(5):
        try:
            w[1] = WW.eth.get_transaction_receipt(h); w[0].set(); return
        except Exception as e:  # noqa: BLE001
            ERRORS["receipt:" + str(e)[:50]] += 1; time.sleep(0.05 * (k + 1))


def _watcher():
    """One thread follows the chain head and releases requests whose transaction was mined."""
    last = WW.eth.block_number
    while True:
        try:
            head = WW.eth.block_number
            for n in range(last + 1, head + 1):
                for h in WW.provider.make_request("eth_getBlockByNumber", [hex(n), False])["result"]["transactions"]:
                    _rx.submit(_release, h)
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


ARCH = {"b0": decide_b0, "b1": decide_b1, "b2": decide_b2, "b3": decide_b3, "bcz": decide_bcz}


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
