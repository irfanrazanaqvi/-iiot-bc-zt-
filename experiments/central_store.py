"""Centralized zero-trust decision store shared by B2/B3 (inside the gateway) and the B4 replicas.

B2: plain SQLite state.  B3: hardened (HMAC over every identity and trust row under a key held only by the decision
process, plus a hash-chained audit log).  The same decision logic as the AccessControlManager contract.
"""
import hashlib, hmac as _hmac, json, os, sqlite3, threading, time
from pathlib import Path

from pydantic import BaseModel
from web3 import Web3

from experiments.common import device_address, recover_signer

D = json.load(open(Path(__file__).with_name("deployment_v2.json")))
AC_ADDR = Web3.to_checksum_address(D["accessControl"])
POLICIES = {(r, a): (th, f, t) for r, a, th, f, t in D["policies"]}
MAXW, WINS = D["maxPerWindow"], D["windowSeconds"]
CHAIN_ID = [int(os.environ.get("CHAIN_ID", "0"))]   # set by the gateway from the RPC, or by CHAIN_ID for a replica


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
    replicas: list[int] = []   # B4 only: subset of replicas the operation applies to (empty = all)


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
            if recover_signer(AC_ADDR, CHAIN_ID[0], dev, r.resource, r.action, r.nonce, r.sig) != dev:
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


def apply_admin(S_, op, a):
    """One administrative operation on one store (shared by the gateway admin route and the B4 replicas)."""
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
