"""Shared helpers for the multi-architecture live experiments (gateway and load generator)."""
import secrets

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

R = 40  # spare identities per security/revocation pool (must match deploy_v2.js)


def all_ids():
    ids = [f"device-{i}" for i in range(200)] + [f"rev-{i}" for i in range(R)]
    for p in ("sec-rev", "sec-low", "sec-tam", "sec-flood", "sec-ctrl"):
        ids += [f"{p}-{i}" for i in range(R)]
    return ids


_acct_cache = {}


def device_account(device_id):
    """Device key = keccak256("devkey:" + id); stands in for the key held by the device's secure element."""
    if device_id not in _acct_cache:
        _acct_cache[device_id] = Account.from_key(Web3.keccak(text="devkey:" + device_id))
    return _acct_cache[device_id]


def device_address(device_id):
    return device_account(device_id).address


def request_digest(contract, chain_id, device, resource, action, nonce):
    r = Web3.keccak(text=resource)
    a = Web3.keccak(text=action)
    return Web3.solidity_keccak(["address", "uint256", "address", "bytes32", "bytes32", "uint256"],
                                [contract, chain_id, device, r, a, nonce])


def sign_request(device_id, contract, chain_id, resource, action, nonce=None):
    """Return (nonce, 0x-signature) as the device firmware would."""
    nonce = secrets.randbits(250) if nonce is None else nonce
    acct = device_account(device_id)
    d = request_digest(contract, chain_id, acct.address, resource, action, nonce)
    sig = acct.sign_message(encode_defunct(primitive=d)).signature.hex()
    return nonce, sig if sig.startswith("0x") else "0x" + sig


def recover_signer(contract, chain_id, device, resource, action, nonce, sig_hex):
    d = request_digest(contract, chain_id, device, resource, action, nonce)
    try:
        return Account.recover_message(encode_defunct(primitive=d), signature=sig_hex)
    except Exception:  # noqa: BLE001
        return None
