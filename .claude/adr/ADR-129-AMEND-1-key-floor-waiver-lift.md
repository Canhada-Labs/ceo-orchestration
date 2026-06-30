---
id: ADR-129-AMEND-1
title: C1 crypto capability class — lift §Key-floor-waiver + introduce SPKI pin + 90d key rotation cycle
status: ACCEPTED
proposed_at: 2026-05-20
accepted_at: 2026-05-20
proposed_by: CEO (S146 overnight prep — PLAN-099-FOLLOWUP Wave B prereq)
accepted_by: CEO (S148 — PLAN-099-FOLLOWUP v1.39.1 ship ceremony Phase 0a)
deciders: [CEO]
consulted: [identity-trust-architect, security-engineer, threat-detection-engineer, code-reviewer]
amends: ADR-129
related_plans: [PLAN-099, PLAN-099-FOLLOWUP, PLAN-089]
related_adrs: [ADR-126, ADR-129, ADR-135, ADR-135-AMEND-1, ADR-121, ADR-124, ADR-125]
risk_tier: C  # mirrors ADR-129; amendment does not change tier
codex_validation:
  thread: 019e4662-cfc3-7bb1-899a-158ae3b3842e  # PLAN-099-FOLLOWUP final bundle R2 review (covers staged ADR-129-AMEND-1 body)
  verdict: ACCEPT (iter-4 clean; iter-3 ACCEPT-WITH-FIXES P2=1 resolved; iter-2 BLOCK P0=2/P1=1/P2=1 resolved; iter-1 BLOCK P0=4/P1=4/P2=1 resolved)
---

# ADR-129-AMEND-1 — Lift §Key-floor-waiver + SPKI pin + 90d key rotation

## §1. Amendment scope

ADR-129-AMEND-1 amends ADR-129 (C1 crypto capability class) in THREE
narrow places:

1. **§Part 7 §Key-floor-waiver — REMOVED.** The waiver shipped with the
   PLAN-099 MVP read-only release on the explicit understanding that a
   C1 crypto sidecar (PLAN-099-FOLLOWUP) would introduce
   `cryptography.x509.load_pem_x509_certificate(...).public_key()`
   inspection. That sidecar lands with this amendment. The waiver is no
   longer needed and is mechanically inconsistent with write-mode
   (ADR-135-AMEND-1).
2. **§Part 9 §Reservation — UPDATED.** Removes "write-mode" and
   "Tier B / A promotion" from the reservation list. Both lift via
   PLAN-099-FOLLOWUP. The `cryptography` package surface remains
   sidecar-fenced (not promoted to core).
3. **§Part 10 — NEW.** Adds the **90-day key rotation cycle** as a
   binding lifecycle invariant; removes the dependency on the §Part 7
   waiver-driven Owner-physical advisory check.

ALL OTHER §Parts of ADR-129 stand as accepted (Part 1 capability
surface, Part 2 data access, Part 3 network access, Part 4 persistence,
Part 5 audit mediation, Part 6 SBOM, Part 8 kill-switch chain).

## §2. Reinstated AC1 invariant

Original PLAN-099 AC1 invariant (programmatic per-cert key-floor
verification at peer-add via `cryptography.x509.load_pem_x509_certificate
(...).public_key()`) is REINSTATED. PLAN-099-FOLLOWUP Wave B adds the
mechanical enforcement (Tooling: `_lib/federation/cert_inspector.py`).

Floor rules (locked at this amendment; changes require a further
amendment):

| Key class | Floor | Source |
|---|---|---|
| RSA       | ≥ 2048 bits | NIST SP 800-131A Rev. 2 |
| EC        | P-256 / P-384 / Ed25519 | RFC 8422 + RFC 8032 |
| DSA       | REJECTED | NIST SP 800-131A Rev. 2 (deprecated) |
| Signature | SHA-256+; MD5 / SHA-1 REJECTED | NIST SP 800-57 Rev. 5 |

These rules live in `cert_inspector.RSA_MIN_BITS`,
`cert_inspector.EC_ALLOWED_CURVES`, `cert_inspector.DSA_ALLOWED`, and
`_WEAK_SIG_ALGORITHMS`. The Wave B test suite asserts each rule on the
adversarial cert fixtures.

## §3. SPKI fingerprint replaces DER fingerprint (primary pin)

ADR-129 §Part 2 + §Part 4 are READ-UPDATED (no §Part renumbering):

- `peers.yaml[peer].peer_id_spki_fingerprint` is the NEW PRIMARY pin
  (64-hex SubjectPublicKeyInfo SHA-256).
- `peers.yaml[peer].peer_id_cert_fingerprint` (full-cert DER SHA-256
  per PLAN-099 MVP) becomes the LEGACY pin, accepted alongside SPKI
  during the 90-day migration window (Wave B.2 / Wave C.1
  `peers.yaml` schema migration v1.x → v2.0).
- Server prefers SPKI when both are present; falls back to DER for
  unmigrated adopter installs.

Migration window properties:

- BOTH `peer_id_spki_fingerprint` AND `peer_id_cert_fingerprint`
  accepted in the same `peers.yaml` row during the soak.
- Adopters MAY commit only SPKI (new installs) OR only DER (legacy
  installs) OR both (preferred during migration).
- The soak gate is **data-volume-driven**, NOT calendar-driven (per
  ADR-095): the gate closes when ≥80% of registered peers have at
  least one SPKI-pin commit. After that, DER fallback is removed via
  a follow-up amendment (planned: ADR-129-AMEND-2 under
  PLAN-099-FOLLOWUP-NEXT).

**Why SPKI over DER for v1.39.1+?** A peer cert rotation (e.g., the
90-day rollover) changes the full-cert DER bytes but does NOT change
the SubjectPublicKeyInfo if the underlying key material is preserved.
The original MVP DER pin had the operational cost that every cert
rotation re-pinned every peer — a synchronisation hazard. SPKI
survives cert rotation.

## §4. §Part 10 — 90d key rotation cycle (NEW)

The amendment introduces a **mandatory 90-day key rotation cycle**
across the federation surface:

### 4.1 — Peer cert validity

Peer certs MUST have `not_valid_after - not_valid_before ≤ 90 days`.
Enforcement points (Wave B.4):

1. `peer-add` ceremony — `cert_inspector.inspect()` returns a report
   with `not_after_iso - not_before_iso > 90d` → REJECT with audit
   `federation_cert_validity_window_too_large`.
2. CI gate (`.github/workflows/validate.yml`) — any peer cert
   declared in `peers.yaml` whose declared `not_valid_after - now()`
   exceeds 90 days → CI fail.

### 4.2 — Sentinel signer rotation

The Owner-GPG enable + LAN sentinel signing keys follow ADR-121 §2:

- Hot-key max age: 12 months
- Cold-keys: 60 months (M=2-of-N=3 quorum)

PLAN-099-FOLLOWUP does NOT amend ADR-121. The 90d window in §4.1 is
the PEER cert cycle, not the SENTINEL signer cycle. The §Part 10 §4.2
clause exists to make this distinction unambiguous (Codex iter-1 P0
correction surface — prior drafts conflated the two).

### 4.3 — HMAC secret rotation

Per-peer `hmac_secret_hex` in `peers.yaml` rotates jointly with cert
rotation (same 90d window). The Wave B.4 ceremony script regenerates
both atomically:

```
python3 .claude/scripts/rotate-peer.py --peer <peer-id> \
    --new-cert peer.pem --new-key peer.key
```

The script:
1. Calls `cert_inspector.inspect()` on the new cert.
2. Verifies the SPKI matches the configured `peer_id_spki_fingerprint`
   (rotation-survives invariant test).
3. Generates a fresh `hmac_secret_hex` via `secrets.token_hex(32)`.
4. Atomically writes `peers.yaml.tmp` + fsync + rename → `peers.yaml`.
5. Emits `federation_cert_rotated` + `federation_hmac_secret_rotated`.

### 4.4 — Revocation propagation

`peers.yaml[peer].revoked: true` is read fail-CLOSED at every handshake
(no caching) and propagates within one handshake of the YAML edit.
This matches the ADR-121 §6 v1.x no-cache contract.

## §5. Dependencies (NEW)

ADR-129-AMEND-1 introduces ONE external dependency to the framework
(fenced under the C1 crypto-mvp sidecar):

| Dependency       | Pin              | Used by                       | Sidecar manifest |
|------------------|------------------|-------------------------------|------------------|
| `cryptography`   | `>=42.0,<44.0`   | `cert_inspector.py`           | `.claude/sidecars/c1-crypto/cryptography-mvp/manifest.json` |

Pin rationale:

- **42.0 floor**: stable `rfc7958` PEM bundle support; `_utc`
  validity-window accessors avoid the deprecation warning on naive
  datetimes shipped in 41.x.
- **44.0 ceiling**: 44.0 is unreleased at draft time. We gate every
  major-version bump through a 30-day release-window soak (Wave F.3)
  before adoption.

The `boundary_test.py` for the cryptography-mvp sidecar (Wave A.4)
asserts that `cryptography` is imported ONLY from
`.claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/` (the
canonical sidecar tree per ADR-126 §Part 2). Core
(`.claude/hooks/_lib/`) remains stdlib-only per ADR-126 §Part 1 +
ADR-002; the bridge at `_lib/federation/cert_inspector.py`
subprocess-invokes the sidecar via stdlib-only IPC (argv + stdout)
and contains ZERO `cryptography` imports. All other paths attempting
to import `cryptography` are CI-blocked via the existing
`check-stdlib-only.py` (extended assertion: ZERO matches under
`.claude/hooks/`, `.claude/scripts/`, `.claude/policies/`, `SPEC/`,
`.github/workflows/`).

## §6. Cross-references

- ADR-129 — original C1 crypto capability class (amended by THIS amend)
- ADR-129-AMEND-1 §3 ↔ ADR-135-AMEND-1 §migration — the SPKI pin
  introduction is a JOINT amendment; both ADRs must reach ACCEPTED
  together to flip the federation surface from DER to SPKI primary.
- ADR-135 — federation contract MVP (amended by ADR-135-AMEND-1)
- ADR-121 — sentinel signer rotation policy (UNCHANGED; §Part 10 §4.2
  explicitly preserves the 12mo/60mo cycle).
- ADR-126 §Part 4 — manifest.json schema (the cryptography-mvp
  manifest conforms).
- ADR-095 — no calendar gates doctrine (the 90-day window is a
  CONTRACT not a calendar gate; the WAIVER lift is data-volume-driven
  per §3 above).
- PLAN-099-FOLLOWUP §8 — execution scaffold for this amendment.

## §7. Reversal

If the lift produces an operational problem (e.g., a vendor cert that
issuers actually cannot reissue within 90d), the reversal path is:

1. Set `CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=0` — instant
   sidecar disable; `cert_inspector` then refuses to lift the floor
   on the cryptography path (still uses openssl fallback for the
   inspect contract, but does not enforce floor unless cryptography
   present).
2. Re-pin to DER-fingerprint primary by reverting
   `peers.yaml[peer].peer_id_spki_fingerprint` back to empty / absent.
3. Tag a patch release noting the rollback.

A doctrinal rollback (i.e. reinstating the §Part 7 waiver) requires a
NEW ADR (ADR-129-AMEND-2 or similar) and Codex R2 ACCEPT — the §Part 7
waiver text is REMOVED, not deprecated, by THIS amendment.

## §8. Acceptance criteria (for this amendment)

- AC-AMEND-1: ADR-129 §Part 7 §Key-floor-waiver clause REMOVED (verified
  by grep — no "Key-floor-waiver" string remains in the final ADR-129
  body).
- AC-AMEND-2: ADR-129 §Part 9 §Reservation list updated; "write-mode"
  and "Tier B / A promotion" REMOVED from reservation.
- AC-AMEND-3: ADR-129 §Part 10 ADDED with the §4.1 - §4.4 clauses
  above.
- AC-AMEND-4: cert inspection delivered as bridge + sidecar pair per
  ADR-126 §Part 1 + §Part 2 — bridge at
  `.claude/hooks/_lib/federation/cert_inspector.py` (stdlib-only;
  subprocess-invokes sidecar) AND sidecar at
  `.claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/cert_inspector.py`
  (cryptography importer). Both implement `inspect()` +
  `enforce_key_floor()` matching §2 floor rules. Floor enforcement
  rejects Ed448 (NOT in the §2 floor table) — future expansion via
  ADR-129-AMEND-2.
- AC-AMEND-5: `peers.yaml` schema v2.0 accepts both
  `peer_id_spki_fingerprint` AND `peer_id_cert_fingerprint`.
- AC-AMEND-6: cryptography-mvp sidecar manifest at
  `.claude/sidecars/c1-crypto/cryptography-mvp/manifest.json` conforms
  to ADR-126 §Part 4 schema.
- AC-AMEND-7: Codex MCP R2 promotion 3-iter ACCEPT pattern (per ADR-129
  / ADR-135 precedent S134).

## §Codex MCP gate trail

<to-be-filled-at-promotion-time>

Reviewed-by: <pending> (PLAN-099-FOLLOWUP promotion ceremony).
