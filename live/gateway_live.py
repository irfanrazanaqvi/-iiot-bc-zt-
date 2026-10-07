"""Live ZT gateway (PEP) against the real Besu QBFT network.

Differences from testbed/gateway.py (which assumes an unlocked node account and treats
receipt.status==1 as 'granted'):
  * signs transactions locally with GATEWAY_PRIVATE_KEY (Besu has no unlocked accounts),
  * assigns nonces under a lock so hundreds of requests can be in flight at once,
  * reads the real decision from the AccessDecision event in the mined receipt,
  * runs requests on a large thread pool so concurrency up to 200 is actually exercised.

Run:  GATEWAY_PRIVATE_KEY=0x.. uvicorn live.gateway_live:app --port 9000   (from repo root)
"""
import collections, itertools, json, os, threading, time
from pathlib import Path

import anyio
from eth_account import Account
from fastapi import FastAPI
from pydantic import BaseModel
from web3 import Web3

D = json.load(open(Path(__file__).with_name("deployment.json")))
# Besu caps each node's HTTP RPC at 80 active connections, so signer i talks to validator i % 4
# (ports 8545..8548) -- the way separate edge gateways would each attach to a nearby validator.
RPCS = os.environ.get("BESU_RPCS", ",".join(f"http://127.0.0.1:{8545 + i}" for i in range(4))).split(",")
W3S = [Web3(Web3.HTTPProvider(u, request_kwargs={"timeout": 60})) for u in RPCS]
w3 = W3S[0]
ac = w3.eth.contract(address=D["accessControl"], abi=D["abis"]["accessControl"])
CHAIN_ID = w3.eth.chain_id
# A pool of PEP signer accounts (one per gateway worker) spreads in-flight transactions across
# senders; Besu limits how many pending transactions a single sender may hold.
SEED = os.environ["GATEWAY_PRIVATE_KEY"]
POOL = []
for i in range(int(os.environ.get("GATEWAY_SIGNERS", "64"))):
    a = Account.from_key(Web3.keccak(text=f"{SEED}:{i}"))
    wi = W3S[i % len(W3S)]
    POOL.append({"acct": a, "lock": threading.Lock(), "w3": wi, "ac": wi.eth.contract(address=D["accessControl"], abi=D["abis"]["accessControl"]),
                 "nonce": wi.eth.get_transaction_count(a.address, "pending")})
_rr = itertools.count()
ERRORS = collections.Counter()

app = FastAPI(title="IIoT ZT Gateway (live)")


@app.on_event("startup")
async def _pool():
    anyio.to_thread.current_default_thread_limiter().total_tokens = 400


class Req(BaseModel):
    device_id: str
    resource: str
    action: str


def device_address(device_id: str) -> str:
    return Web3.to_checksum_address("0x" + Web3.keccak(text=device_id).hex()[-40:])


WAIT = {}   # tx hash -> [Event, receipt]
_wl = threading.Lock()


def _watcher():
    """One thread follows the chain head and releases waiting requests when their tx is mined,
    instead of 200 threads each polling the RPC (which starved the 2-vCPU test host)."""
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


def wait_receipt(h, _w3):
    ev = threading.Event()
    with _wl:
        WAIT[bytes(h)] = [ev, None]
    return ev, h


def decide(device_id, resource, action):
    dev = device_address(device_id)
    s = POOL[next(_rr) % len(POOL)]
    WAITER = None
    for attempt in range(3):
        with s["lock"]:
            try:
                tx = s["ac"].functions.checkAccess(dev, resource, action).build_transaction(
                    {"from": s["acct"].address, "nonce": s["nonce"], "gas": 300000, "gasPrice": 0, "chainId": CHAIN_ID})
                raw = s["acct"].sign_transaction(tx).raw_transaction
                WAITER = wait_receipt(Web3.keccak(raw), None)
                s["w3"].eth.send_raw_transaction(raw)
                s["nonce"] += 1
                break
            except Exception as e:  # noqa: BLE001
                ERRORS[str(e)[:80]] += 1
                s["nonce"] = s["w3"].eth.get_transaction_count(s["acct"].address, "pending")  # resync, retry
                if attempt == 2:
                    raise
    ev_, h = WAITER
    if not ev_.wait(30):
        with s["lock"]:   # a stuck tx would wedge this signer's later nonces: resync from the chain
            s["nonce"] = s["w3"].eth.get_transaction_count(s["acct"].address, "pending")
        WAIT.pop(bytes(h), None)
        raise TimeoutError("receipt timeout")
    rc = WAIT.pop(bytes(h))[1]
    ev = s["ac"].events.AccessDecision().process_receipt(rc)
    granted = bool(ev[0]["args"]["granted"]) if ev else False
    reason = ev[0]["args"]["reason"] if ev else "no-event"
    return granted, reason, h.hex(), rc["gasUsed"], rc["blockNumber"]


@app.post("/access-request")
def access_request(r: Req):
    t0 = time.time()
    try:
        g, reason, h, gas, blk = decide(r.device_id, r.resource, r.action)
        return {"granted": g, "reason": reason, "tx_hash": h, "gas_used": gas, "block": blk,
                "latency_ms": (time.time() - t0) * 1000}
    except Exception as e:  # noqa: BLE001
        return {"granted": False, "reason": "error", "error": str(e)[:200], "latency_ms": (time.time() - t0) * 1000}


@app.get("/health")
def health():
    return {"connected": w3.is_connected(), "block": w3.eth.block_number}


@app.get("/stats")
def stats():
    return dict(ERRORS)
