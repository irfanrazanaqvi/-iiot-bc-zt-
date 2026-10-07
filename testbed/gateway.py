"""
NOTE: reference sketch only. It assumes an unlocked node account and treats receipt.status as the decision;
Besu has no unlocked accounts and checkAccess returns its verdict via an event. Use live/gateway_live.py,
which signs locally and reads the AccessDecision event (this is what the live experiments used).

Zero-Trust Gateway (Policy Enforcement Point, PEP).

Sits at the OT/IT boundary between IIoT devices and protected resources. It never makes
a trust decision itself -- for every request it calls into the on-chain Policy Decision
Point (AccessControlManager.checkAccess) and enforces whatever the blockchain returns.
This is the component whose behaviour is measured for Section 7 (latency, throughput,
authorization accuracy).

Run: uvicorn gateway:app --host 0.0.0.0 --port 9000
"""

import os
import time

from fastapi import FastAPI
from pydantic import BaseModel
from web3 import Web3

RPC_URL = os.environ.get("BESU_RPC_URL", "http://127.0.0.1:8545")
ACCESS_CONTROL_ADDRESS = os.environ.get("ACCESS_CONTROL_ADDRESS", "0x0000000000000000000000000000000000000000")
IDENTITY_REGISTRY_ADDRESS = os.environ.get("IDENTITY_REGISTRY_ADDRESS", "0x0000000000000000000000000000000000000000")

ACCESS_CONTROL_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "device", "type": "address"},
            {"internalType": "string", "name": "resource", "type": "string"},
            {"internalType": "string", "name": "action", "type": "string"},
        ],
        "name": "checkAccess",
        "outputs": [{"internalType": "bool", "name": "granted", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
access_control = w3.eth.contract(address=Web3.to_checksum_address(ACCESS_CONTROL_ADDRESS), abi=ACCESS_CONTROL_ABI)
sender = w3.eth.accounts[0] if w3.is_connected() else None

app = FastAPI(title="IIoT Zero-Trust Gateway")


class AccessRequest(BaseModel):
    device_id: str          # maps to the device's on-chain address (mock-mapped for the demo)
    resource: str
    action: str


DEVICE_ADDRESS_MAP: dict[str, str] = {}  # populate at enrollment time; demo uses deterministic mock addresses


def resolve_device_address(device_id: str) -> str:
    if device_id not in DEVICE_ADDRESS_MAP:
        # Deterministic mock mapping for the testbed only -- in production this comes from
        # the enrollment/attestation flow in IdentityRegistry.
        DEVICE_ADDRESS_MAP[device_id] = Web3.to_checksum_address(
            "0x" + Web3.keccak(text=device_id).hex()[-40:]
        )
    return DEVICE_ADDRESS_MAP[device_id]


@app.post("/access-request")
def access_request(req: AccessRequest):
    t0 = time.time()
    device_addr = resolve_device_address(req.device_id)

    try:
        tx = access_control.functions.checkAccess(device_addr, req.resource, req.action).transact({"from": sender})
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        granted = receipt.status == 1
    except Exception as e:  # noqa: BLE001
        return {"granted": False, "error": str(e), "latency_ms": (time.time() - t0) * 1000}

    return {
        "granted": granted,
        "device": device_addr,
        "resource": req.resource,
        "action": req.action,
        "tx_hash": tx.hex(),
        "latency_ms": (time.time() - t0) * 1000,
    }


@app.get("/health")
def health():
    return {"connected_to_besu": w3.is_connected()}
