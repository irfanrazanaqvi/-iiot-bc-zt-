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
from web3 import Web3

from experiments.common import device_address, recover_signer
from experiments import central_store as CS
from experiments.central_store import CentralStore, Req, Admin, DECAY_UNIT, apply_admin

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
CS.CHAIN_ID[0] = CHAIN_ID
STORES = {"b2": CentralStore(False), "b3": CentralStore(True)}


def decide_b2(r: Req): return STORES["b2"].decide(r)
def decide_b3(r: Req): return STORES["b3"].decide(r)


# ------------------------------------------------------------------ B4 replicated centralized ZT (see below for the route)
import requests as _rq
B4_URLS = [u for u in os.environ.get("B4_REPLICAS", "").split(",") if u]
B4_SEED = os.environ.get("B4_SEED", "replica-dev")
B4_ADDRS = [Account.from_key(Web3.keccak(text=f"replica:{B4_SEED}:{i}")).address for i in range(len(B4_URLS))]
B4_QUORUM = 2 * ((len(B4_URLS) - 1) // 3) + 1 if B4_URLS else 0   # 3 of 4: tolerates one Byzantine replica


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
        return apply_admin(STORES[arch], op, a)
    if arch == "b4" and B4_URLS:
        idx = a.replicas or list(range(len(B4_URLS)))
        outs = list(_pool_b4.map(lambda i: _rq.post(f"{B4_URLS[i]}/admin/{op}", json=a.model_dump(), timeout=60).json(), idx))
        return outs[0]
    raise HTTPException(404, "no admin API for this architecture")


from concurrent.futures import ThreadPoolExecutor as _TPE
_pool_b4 = _TPE(8)


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
    t_in = time.time()
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
                t_built = time.time()
                s["w3"].eth.send_raw_transaction(raw)
                t_sent = time.time()
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
    t_done = time.time()
    st = {"build_ms": round((t_built - t_in) * 1000, 1), "send_ms": round((t_sent - t_built) * 1000, 1), "wait_ms": round((t_done - t_sent) * 1000, 1)}
    ev = s["ac"].events.AccessDecision().process_receipt(rc)
    if not ev:
        return False, "no-event", {"gas_used": rc["gasUsed"], **st}
    return bool(ev[0]["args"]["granted"]), ev[0]["args"]["reason"], {"gas_used": rc["gasUsed"], "block": rc["blockNumber"], **st}


ARCH = {"b0": decide_b0, "b1": decide_b1, "b2": decide_b2, "b3": decide_b3, "bcz": decide_bcz}


# ------------------------------------------------------------------ B4 route (async: fan-out to the replicas, signed quorum)
import asyncio
import httpx
from eth_account.messages import encode_defunct

_B4C = None
_B4LOCKS: dict = {}


def _verdict_digest(dev, r, granted, reason):
    return Web3.keccak(text=f"{dev}|{r.resource}|{r.action}|{r.nonce}|{granted}|{reason}")


async def _ask(i, r):
    global _B4C
    try:
        j = (await _B4C.post(f"{B4_URLS[i]}/decide", json=r.model_dump())).json()
        who = Account.recover_message(encode_defunct(primitive=_verdict_digest(device_address(r.device_id), r, bool(j["granted"]), j["reason"])), signature=j["sig"])
        if who != B4_ADDRS[i]:
            return None            # unsigned or wrongly signed verdict counts as no vote
        return bool(j["granted"]), j["reason"]
    except Exception:  # noqa: BLE001
        return None


@app.post("/b4/access-request")
async def access_request_b4(r: Req):
    """Replicated centralized ZT.  The request goes to every replica; the PEP grants only if at least B4_QUORUM replicas
    return a correctly signed 'granted'.  Requests of one device are ordered (a per-device lock held until every replica
    has answered) so all replicas apply the same sequence of nonces and rate-limit counts."""
    global _B4C
    t0 = time.time()
    if _B4C is None:
        _B4C = httpx.AsyncClient(timeout=20, limits=httpx.Limits(max_connections=4000, max_keepalive_connections=400))
    lock = _B4LOCKS.setdefault(r.device_id, asyncio.Lock())
    await lock.acquire()
    n = len(B4_URLS)
    tasks = [asyncio.create_task(_ask(i, r)) for i in range(n)]
    pending = set(tasks); grants = denies = 0; reasons: collections.Counter = collections.Counter(); verdict = None
    try:
        while pending and verdict is None:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for d in done:
                v = d.result()
                if v is None:
                    denies += 1; reasons["no-vote"] += 1
                elif v[0]:
                    grants += 1
                else:
                    denies += 1; reasons[v[1]] += 1
            if grants >= B4_QUORUM:
                verdict = (True, "granted")
            elif denies > n - B4_QUORUM:
                verdict = (False, reasons.most_common(1)[0][0] if reasons else "no-quorum")
    except Exception:
        lock.release(); raise

    async def _rel():
        try:
            await asyncio.gather(*pending, return_exceptions=True)
        finally:
            lock.release()
    asyncio.create_task(_rel())
    g, reason = verdict if verdict else (False, "no-quorum")
    return {"granted": g, "reason": reason, "latency_ms": (time.time() - t0) * 1000, "votes": f"{grants}g/{denies}d"}


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
