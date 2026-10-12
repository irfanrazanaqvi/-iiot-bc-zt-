"""One B4 replica: a hardened centralized decision store (B3 logic) behind a small HTTP API, with its own state, its own
integrity key, and its own signing key.  Every verdict is signed so that the PEP can require a quorum of valid signatures.

  CHAIN_ID=<id> REPLICA_INDEX=<i> B4_SEED=<seed> uvicorn experiments.replica:app --host 0.0.0.0 --port 9100

POST /decide  {device_id, resource, action, nonce, sig}  ->  {granted, reason, sig}
POST /admin/{op}  (seed, revoke, evidence, reset, decay_unit, score, tamper, tamper_host, byzantine)
`byzantine` (delta=1) models a replica whose host was taken over: it signs 'granted' for everything.
"""
import os

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import FastAPI
from web3 import Web3

from experiments.central_store import Admin, CentralStore, Req, apply_admin
from experiments.common import device_address

IDX = int(os.environ.get("REPLICA_INDEX", "0"))
SEED = os.environ.get("B4_SEED", "replica-dev")
KEY = Account.from_key(Web3.keccak(text=f"replica:{SEED}:{IDX}"))
S = CentralStore(True)
BYZ = [False]
app = FastAPI(title=f"B4 replica {IDX}")


def _sign(r: Req, granted: bool, reason: str):
    d = Web3.keccak(text=f"{device_address(r.device_id)}|{r.resource}|{r.action}|{r.nonce}|{granted}|{reason}")
    s = KEY.sign_message(encode_defunct(primitive=d)).signature.hex()
    return s if s.startswith("0x") else "0x" + s


@app.post("/decide")
def decide(r: Req):
    g, reason, _ = S.decide(r)
    if BYZ[0]:
        g, reason = True, "granted"   # compromised replica: forges a grant (and signs it with its own, genuine key)
    return {"granted": g, "reason": reason, "sig": _sign(r, g, reason)}


@app.post("/admin/{op}")
def admin(op: str, a: Admin):
    if op == "byzantine":
        BYZ[0] = bool(a.delta)
        return {"ok": True}
    return apply_admin(S, op, a)


@app.get("/health")
def health():
    return {"replica": IDX, "address": KEY.address}
