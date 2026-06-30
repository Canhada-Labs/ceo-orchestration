"""Generate the deterministic benign-traffic corpus + ATT&CK should-fire
fixtures for PLAN-112-FOLLOWUP-federation-wire-or-delete (R-TD-2/3).

Deterministic (seeded) so the FPR gate is reproducible. Output:
  - federation-benign-corpus.ndjson   (>=200 normal records per emitter class)
  - should-fire-t1499-storm.ndjson     (rate-limit storm)
  - should-fire-t1485-autorevoke.ndjson (breaker auto-revoke)
  - should-fire-t1565-tamper.ndjson    (audit-chain break)
  - should-not-fire-normal.ndjson       (benign control)
"""
from __future__ import annotations
import json
import random
import sys

OUT_FIXTURES = sys.argv[1]  # fixtures dir
OUT_CORPUS = sys.argv[2]    # corpus dir (PLAN-112-FOLLOWUP/fixtures)

rng = random.Random(0x5EED_F00D)

# Emitter classes whose FPR we bound:
#   - rate_limit token-bucket (T1499)         : route + peer + spaced timestamps
#   - circuit-breaker (T1485)                  : sub-threshold hit cadence
#   - backpressure (T1499 latency)             : sub-100ms p99 latencies
#   - audit-chain (T1565)                      : well-formed chained events
PEERS = ["peer-a", "peer-b", "peer-c", "peer-d"]
ROUTES = [
    "/federation/audit-event",
    "/federation/audit-event/batch",
    "/federation/peer-register",
    "/federation/peer-revoke",
]

# Per-route benign cadence well UNDER the ADR-135-AMEND-1 §2.4 caps:
#   audit-event 60/min, batch 6/min, register 1/hr, revoke 5/hr.
BENIGN_INTERVAL_SEC = {
    "/federation/audit-event": 2.0,        # 30/min — under 60
    "/federation/audit-event/batch": 15.0,  # 4/min — under 6
    "/federation/peer-register": 4000.0,    # ~0.9/hr — under 1
    "/federation/peer-revoke": 900.0,       # 4/hr — under 5
}

corpus = []
base_ts = 1_900_000_000.0

# rate_limit + breaker benign class: spaced requests per (peer, route).
for peer in PEERS:
    for route in ROUTES:
        interval = BENIGN_INTERVAL_SEC[route]
        t = base_ts + rng.random() * 100
        for _ in range(60):  # 60 per (peer,route) → 4*4*60 = 960 records
            corpus.append({
                "class": "rate_limit",
                "peer_id": peer,
                "route": route,
                "ip_prefix": "10.0.{0}.0".format(rng.randint(0, 8)),
                "ts": round(t, 3),
            })
            t += interval + rng.random() * (interval * 0.2)

# backpressure benign class: latencies well under 100ms.
for _ in range(300):
    corpus.append({
        "class": "backpressure",
        "latency_ms": rng.randint(1, 60),
        "ts": round(base_ts + rng.random() * 30, 3),
    })

with open(OUT_CORPUS + "/federation-benign-corpus.ndjson", "w") as fh:
    for rec in corpus:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")

# ---- should-NOT-fire control (a small benign sample, same shape) ----
with open(OUT_FIXTURES + "/should-not-fire-normal.ndjson", "w") as fh:
    t = base_ts
    for _ in range(30):
        fh.write(json.dumps({
            "class": "rate_limit", "peer_id": "peer-a",
            "route": "/federation/audit-event", "ip_prefix": "10.0.1.0",
            "ts": round(t, 3),
        }, sort_keys=True) + "\n")
        t += 3.0  # 20/min — under 60

# ---- should-fire T1499 storm: 300 audit-event reqs in ~9s ----
# audit-event cap = 60 burst + 1 token/sec refill. 300 reqs at 0.03s
# (≈33/sec) over ~9s consumes 300 tokens, refills only ~9 → ~230 denials,
# far more than the 3-hit breaker threshold → guaranteed trip.
with open(OUT_FIXTURES + "/should-fire-t1499-storm.ndjson", "w") as fh:
    t = base_ts
    for _ in range(300):
        fh.write(json.dumps({
            "class": "rate_limit", "peer_id": "attacker-1",
            "route": "/federation/audit-event", "ip_prefix": "203.0.113.0",
            "ts": round(t, 3),
        }, sort_keys=True) + "\n")
        t += 0.03

# ---- should-fire T1485 auto-revoke: >=3 rate-limit hits in 5min ----
# Burst register far over the 1/hr cap so >=3 hits land in the breaker
# window, tripping the auto-revoke.
with open(OUT_FIXTURES + "/should-fire-t1485-autorevoke.ndjson", "w") as fh:
    t = base_ts
    for _ in range(8):
        fh.write(json.dumps({
            "class": "rate_limit", "peer_id": "attacker-2",
            "route": "/federation/peer-register", "ip_prefix": "203.0.113.7",
            "ts": round(t, 3),
        }, sort_keys=True) + "\n")
        t += 10.0  # 8 in 80s — all but the first are over the 1/hr cap

# ---- should-fire T1565 tamper: an audit-log with a broken prev_hash ----
import hashlib
def canon_hash(ev):
    filtered = {k: v for k, v in ev.items()
                if k not in ("audit_chain_hash", "audit_chain_prev_hash",
                             "_timestamp_emitted")}
    canonical = json.dumps(filtered, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

with open(OUT_FIXTURES + "/should-fire-t1565-tamper.ndjson", "w") as fh:
    GENESIS = "0" * 64
    e1 = {"action": "x", "n": 1, "audit_chain_prev_hash": GENESIS}
    h1 = canon_hash(e1)
    e2 = {"action": "x", "n": 2, "audit_chain_prev_hash": h1}
    # e3 carries a WRONG prev_hash → chain break (tamper).
    e3 = {"action": "x", "n": 3, "audit_chain_prev_hash": "f" * 64}
    for e in (e1, e2, e3):
        fh.write(json.dumps(e, sort_keys=True) + "\n")

# count summary
print("benign corpus records:", len(corpus))
from collections import Counter
print("by class:", dict(Counter(r["class"] for r in corpus)))
