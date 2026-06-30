---
id: ADR-129
title: C1 crypto capability class — stdlib ssl MVP + cryptography sidecar reserved
status: ACCEPTED
accepted_at: 2026-05-17
proposed_at: 2026-05-17
proposed_by: CEO (S134 — PLAN-099 Federation MVP Wave D.2)
deciders: [CEO]
consulted: [identity-trust-architect, security-engineer, threat-detection-engineer, code-reviewer]
related_plans: [PLAN-099, PLAN-089]
related_adrs: [ADR-042, ADR-089, ADR-115, ADR-121, ADR-124, ADR-125, ADR-126, ADR-135]
sidecar_capability_class: C1
class_label: crypto
risk_tier: C  # spendy-opt-in per ADR-125
codex_validation:
  thread: <to-be-filled-at-promotion-time>
  verdict: <to-be-filled-at-promotion-time>
---

# ADR-129 — C1 crypto capability class (stdlib ssl MVP)

## §1. Context

PLAN-099 ships the first cross-machine federation surface. Per ADR-126
§Part 3 (governed sidecar capability model), federation USES a C1 crypto
capability class. ADR-129 declares that class.

The C1 class spans every primitive that:

1. Generates / verifies cryptographic identity (cert / signature /
   fingerprint),
2. Establishes a trust boundary between disjoint processes / hosts via
   transport-layer cryptography,
3. Maintains a per-peer authentication secret (HMAC / shared key /
   bearer token) used to bind a request to a principal.

ADR-129 is intentionally narrow: **MVP scope is stdlib `ssl` + `hmac` +
`secrets` + `hashlib` only.** Real cryptographic-library surface
(`cryptography` package) is reserved for a follow-up C1 sidecar shipped
via PLAN-099-FOLLOWUP, gated on the §Key-floor waiver lift condition
documented below.

## §2. Decision

ADR-129 declares the C1 crypto capability class with the following
invariants. All invariants are governance-stable across ADR-129
amendments; only the §Key-floor waiver clause has a published LIFT
condition.

### Part 1 — Capability surface

The C1 class authorises ONE set of stdlib primitives for the MVP:

| Primitive             | Module        | Used by                       |
|-----------------------|---------------|-------------------------------|
| TLS handshake         | `ssl`         | server + client (mTLS)        |
| Cert ↔ DER conversion | `ssl`         | identity fingerprint          |
| SHA-256 hex digest    | `hashlib`     | DER fingerprint               |
| HMAC-SHA256           | `hmac`        | request-binding signature     |
| Constant-time compare | `hmac`        | signature + fingerprint match |
| Secure random bytes   | `secrets`     | nonce generation              |

NO third-party crypto package is permitted in the C1 MVP surface.
Specifically:

- `cryptography` ❌ (deferred to PLAN-099-FOLLOWUP)
- `PyJWT` ❌
- `nacl` ❌
- `pyOpenSSL` ❌

The stdlib-only constraint is enforced by `check-stdlib-only.py`
(PLAN-097 Wave B) extended to scan `.claude/hooks/_lib/federation/**/*.py`.

### Part 2 — Data access

Read-only certs at file paths declared in `peers.yaml`. NO write to
peer cert files at runtime — peer registration is an Owner ceremony.

### Part 3 — Network access

Outbound HTTPS to allowlisted peers ONLY (allowlist derived from
`peers.yaml` `peer_id_cert_fingerprint` entries). Inbound HTTPS bind
defaulted to loopback; non-loopback bind requires the LAN Owner-GPG
sentinel pair per ADR-135.

### Part 4 — Persistence

- `.claude/data/federation/peers.yaml` — peer-id allowlist (kernel-
  guarded path per ADR-116-AMEND-1).
- `.claude/data/federation/enabled.md{,.asc}` — enable sentinel pair.
- `.claude/data/federation/lan-enabled.md{,.asc}` — LAN sentinel pair.
- Audit-chain extension via `federation_*` events written to the
  existing audit-log.jsonl through `audit_emit`.

NO new persistent state stores; NO new database; NO secret cache at
rest. HMAC-secret rotation requires Owner peer-add ceremony.

### Part 5 — Audit mediation

ALL federation events MUST emit via `audit_emit.emit_*` brokered IPC
(the hasattr-guarded shim in `_lib/federation/server.py`). NO direct
file writes to audit-log. NO best-effort breadcrumb except in the
inline `_safe_emit` fallback path which is documented as a
defense-in-depth, NOT a primary observability surface.

Ten new audit actions are registered in `_KNOWN_ACTIONS` via
kernel-override `CEO_KERNEL_OVERRIDE=PLAN-099-WAVE-D-AUDIT-EMIT-EXTENSION`
+ `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (ADR-116 contract):

1. `federation_connection_accepted`
2. `federation_connection_rejected`
3. `federation_connection_replay_suspected`
4. `federation_cert_expiry_warned`
5. `federation_cert_rotated`
6. `federation_cert_revoked`
7. `federation_write_attempt_blocked`
8. `federation_lan_bind_denied`
9. `federation_autonomous_call_blocked`
10. `federation_enable_sentinel_invalid`

All ten are Sec MF-3 caller-field whitelisted (deny-by-default).
ATT&CK technique bindings: T1071.001 + T1573 + T1556.

### Part 6 — SBOM

Stdlib only:

- `ssl` (Python ≥3.9)
- `hmac` / `hashlib` (Python ≥3.9)
- `secrets` (Python ≥3.6)
- `http.server` + `http.client` (Python ≥3.9)
- `ipaddress` (Python ≥3.9)

NO compiled extension required beyond CPython's bundled OpenSSL.

### Part 7 — §Key-floor waiver (S129 iter-3 P0a fold — explicit governance change)

For MVP scope, programmatic per-cert key-floor verification (`ed25519`
/ `P-256` / `RSA-2048+` floor) is FORMALLY WAIVED.

**Rationale**: Python's stdlib `ssl.SSLContext` does NOT expose
primitives for inspecting cert public-key parameters. `SSLContext`
controls cipher-suite negotiation and handshake protocol version, but
it cannot inspect the public-key parameters of presented peer certs.

**Waiver scope (narrow)**:

1. Read-only endpoints only.
2. Tier C default-OFF (CEO_FEDERATION_ENABLED=0 by default).
3. Owner-provisioned certs at install-time per the operational runbook.
4. R-key-floor-soft + AC-LIM-1 explicitly document the limitation.
5. CI / install-time advisory check via
   `openssl x509 -text -in peer.pem | grep "Public Key Algorithm"`.

**Waiver LIFT condition**: A C1 crypto sidecar shipped via
PLAN-099-FOLLOWUP introduces
`cryptography.x509.load_pem_x509_certificate(...).public_key()`
inspection at peer-add time. Once that sidecar ships and binds, a future ADR-129 amendment
(plan-housed under PLAN-099-FOLLOWUP) deletes this §waiver clause and
reinstates the original AC1 invariant.

**Until that ADR-129 amendment lands**: MVP CANNOT promote to write-mode and
CANNOT promote to Tier B / Tier A — the Tier C lock is enforced by the
§Kill-switch chain below.

### Part 8 — Kill-switch chain (R1 P0-4; S129 iter-2 GPG-real fold)

The C1 MVP enforces a 6-layer chain (NOT a single env var):

1. `CEO_FEDERATION_ENABLED=0` env var (master).
2. Owner-GPG enable sentinel `.claude/data/federation/enabled.md.asc`
   verified via real `gpg --verify`; fail-CLOSED on bad-sig /
   wrong-key / expired-signer / parse-error (ADR-121 verifier pattern).
3. SIGTERM → SIGKILL escalation (30s grace) on operator-initiated stop.
4. cgroups / ulimit fallback (kernel-level enforcement).
5. Supervisor watchdog — parent process polls server liveness.
6. Coordinator-owned counter — `audit_emit` calls = expected count
   (drift detector for emit-tampering).

Failure modes that MUST trigger fail-CLOSED:

- Missing / expired cert
- Unknown DER-fingerprint (`peer_id_cert_fingerprint` not in
  `peers.yaml`)
- `peers.yaml` parse error
- Sentinel GPG-verify failure (either stage)
- Bind-loopback resolution failure (e.g., DNS unreachable for the bind
  host)

### Part 9 — Reservation

`cryptography`-backed key-floor verification + `ed25519` /
`secp256r1` signature derivation + WRITE-mode endpoints + Tier B / A
promotion: ALL reserved for PLAN-099-FOLLOWUP. ADR-129 itself
governs ONLY the stdlib MVP and the C1 class boundary.

## §3. Consequences

### Positive

- Federation cross-machine MVP ships under a narrow, auditable
  capability class.
- Owner GPG sentinel chain is the SINGLE choke-point — no env-var-only
  enable.
- Stdlib-only constraint keeps SBOM minimal + makes adopter installs
  predictable.

### Negative

- No programmatic key-floor verification at handshake. Operational
  burden shifts to Owner ceremony at peer-add (R-key-floor-soft).
- DER-fingerprint rotation invalidates the pin (vs SPKI which survives
  cert rotation). Operational cost recorded in AC11 90-day cycle.

### Reversal

Concrete operational rollback path (NO new ADR required; the
kill-switch chain in §Part 8 is the canonical disable):

1. Set ``CEO_FEDERATION_ENABLED=0`` (master kill — instant).
2. Set ``CEO_SIDECAR_C1_CRYPTO_STDLIB_SSL_MVP_ENABLED=0`` (alias).
3. Remove ``.claude/data/federation/enabled.md.asc`` (Stage-1
   sentinel fail-CLOSED on next start).
4. Optional: empty ``peers.yaml`` (the server will start with zero
   accepted peers — full effective disable without bringing the
   process down).
5. Optional: revoke peer certs via ``peers.yaml[peer].revoked: true``.
6. Tag a patch release documenting the rollback scope.

If a fatal flaw surfaces that demands a doctrinal change (not just
an operational disable), a future ADR-129 amendment (housed under
PLAN-099-FOLLOWUP) supersedes the relevant §Parts. The amendment
is post-hoc documentation; the operational rollback above runs
FIRST.

## §4. References

**Internal shorthand resolution** (Codex iter-1 P2 fold — ACCEPTED
ADR stands alone):

- ``R-key-floor-soft`` — PLAN-099 §6 risk entry documenting that
  MVP does NOT programmatically enforce per-cert key floor.
- ``AC-LIM-1`` — PLAN-099 §4 acknowledged-limitation entry for the
  same governance waiver.
- ``AC1`` — PLAN-099 §4 acceptance criterion governing TLS handshake
  invariants (subject to the §Part 7 §Key-floor-waiver above).
- ``AC11`` — PLAN-099 §4 acceptance criterion for the 90-day cert
  rotation discipline.

**ADR cross-references**:

- ADR-126 §Part 3 — Governed sidecar capability model (ADR-126
  reserves ADR-130 for C3 model-exec; ADR-131 SHIPPED for C5).
- ADR-121 — sentinel signer registry (Stage-2 expiry/revocation gate).
- ADR-042 §Auth — MCP handler auth surface (analogous trust boundary
  for in-process tools).
- ADR-089 — kernel-path enumeration pattern (Wave A.4 pattern for
  federation kernel-path extension).
- ADR-115 — post-audit-SOTA maintenance doctrine (constrains scope of
  PLAN-099 to MVP-honest read-only).

## §Codex MCP gate trail

Codex R2 promotion review thread: `019e387d-2606-7b80-9afc-ff439a2096e4`
(gpt-5.2), running in parallel to the bundle review thread
`019e3787-1e26-76b0-b083-39aa4a34ecb2` which converged 4-iter ACCEPT
on the PLAN-099 v1.32.0 ship.

Promotion-specific trail:

- **iter-1**: ACCEPT-WITH-FIXES — 5 P0 + 1 P1 + 1 P2 findings on the
  canonical ADR text (broken `ADR-NNN-AMEND-1` literal references,
  §Reversal not a real rollback path, §Part 9-bis reference without
  matching Part, manifest schema drift vs ADR-126 §Part 4 canonical
  5-block shape, internal shorthand without resolution).
- **iter-2**: **ACCEPT** — 0 P0 + 1 P1 + 2 P2. All iter-1 findings
  folded into this promotion. P1 (placeholder trail marker) +
  P2#1 (boundary_test full §Part 5 triad scope) + P2#2 (commit-msg
  "functional change" phrasing) addressed before Owner handoff.

This promotion folds the iter-1 P0+P1+P2 findings as canonical doctrine
fixes (§Reversal rewrite + AMEND-1 literal removal + §Part 9-bis
removal + internal shorthand glossary in §References). The sidecar
manifest at `.claude/sidecars/c1-crypto/stdlib-ssl-mvp/manifest.json`
was rewritten to the canonical 5-block schema (`sidecar` /
`isolation` / `dependencies` / `governance` / `install`) shipped
in-place ahead of this promotion ceremony.

Reviewed-by: CEO (S134 promotion ceremony, post-PLAN-099 v1.32.0 ship).
