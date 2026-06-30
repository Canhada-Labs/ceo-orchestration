---
id: ADR-135
title: Federation contract MVP — cross-machine trust boundary + 2-stage sentinel + audit-chain stitching
status: ACCEPTED
accepted_at: 2026-05-17
proposed_at: 2026-05-17
proposed_by: CEO (S134 — PLAN-099 Federation MVP Wave D.1)
deciders: [CEO]
consulted: [identity-trust-architect, security-engineer, threat-detection-engineer, code-reviewer]
related_plans: [PLAN-099, PLAN-089, PLAN-102]
related_adrs: [ADR-042, ADR-089, ADR-115, ADR-121, ADR-124, ADR-125, ADR-126, ADR-129]
risk_tier: C  # spendy-opt-in per ADR-125
slot_rationale: |
  ADR-126 §Part 3 ACCEPTED 2026-05-13 reserves ADR-130 for C3 model-exec
  sidecar + ADR-134 for C4 browser sidecar. ADR-131 SHIPPED PLAN-093
  (C5 dev-tools). ADR-132 reserved for PLAN-098 GOAP. ADR-133 reserved
  for PLAN-102 autonomous-loop opt-in. ADR-135 is the first available
  non-reserved monotonic slot for the federation-contract-mvp.
codex_validation:
  thread: <to-be-filled-at-promotion-time>
  verdict: <to-be-filled-at-promotion-time>
---

# ADR-135 — Federation contract MVP

## §1. Context

PLAN-099 ships the first cross-machine federation surface in
ceo-orchestration. The federation is a NEW trust boundary that the
existing in-repo ADRs do not cover: prior trust boundaries were
process-local (ADR-042 MCP handlers, ADR-048 cross-plan memory). A
cross-machine peer presenting a pinned cert is a NEW trust principal
class.

ADR-135 is **distinct from ADR-129**. ADR-129 governs the C1 crypto
capability class which federation USES. ADR-135 governs the federation
contract itself — the trust boundary, enable protocol, cert rotation
policy, and audit-chain stitching.

## §2. Decision

### Part 1 — Trust boundary

The federation introduces ONE new trust principal class: **peer-via-
DER-fingerprint**. A peer authenticates via:

1. mTLS handshake (TLSv1.3 minimum) presenting an X.509 cert in
   `peers.yaml[peer].peer_id_cert_fingerprint`.
2. Per-request HMAC-SHA256 binding using a per-peer secret in
   `peers.yaml[peer].hmac_secret_hex`.
3. RFC3339 timestamp + ≥128-bit nonce inside a ±30s server clock-skew
   window.

A peer is treated as a service-account with rotation policy (AC11):
max 90-day cert validity + SHA-256 CA pin + 14-day expiry warning +
M=2-of-N=3 quorum for peer-add (analogous to ADR-121 sentinel rotation).

The federation surface is **read-only in MVP** (AC15 mechanical method
allowlist + ADR-129 §Part 9 reservation). NO write endpoints. Write-mode
is PLAN-099-FOLLOWUP scope.

### Part 2 — Authority delegation

A peer's authority is **bounded** to:

- `GET /federation/identity` — read server's own DER fingerprint.
- `GET /federation/status` — read peer-id, uptime, opaque hash + count
  of last-event (NO content — R1 hardening).
- `GET /federation/audit-summary?since=<iso8601>` — read last-N audit
  events redacted via `redact_secrets` + `pii_redact_full` pipeline.

A peer CANNOT:

- Write any audit event server-side
- Modify peer registry (`peers.yaml` is kernel-guarded per ADR-129
  §Part 4)
- Trigger any side-effect beyond the audit emit on the request itself
- Be invoked from the PLAN-102 autonomous-loop path (AC18 import-graph
  denylist + `federation_autonomous_call_blocked` emit)

### Part 3 — Cert rotation policy

- **Max validity**: 90 days from `not_valid_before` to `not_valid_after`.
  CI gate fails any cert with >90-day validity window at peer-add time.
- **CA pin**: SHA-256 of issuing CA cert in
  `peers.yaml[peer].ca_pin_sha256`. CA pin survives cert rotation.
- **Revocation**: `peers.yaml[peer].revoked: true` blocklist field.
  Loaded fail-CLOSED on parse error.
- **Expiry warning**: 14-day audit `federation_cert_expiry_warned`.
- **Hot rotation**: M=2-of-N=3 cold-key quorum (analogous to ADR-121
  sentinel signer rotation pattern) for any peer-add.

### Part 4 — Enable protocol (2-stage detached-signature verification)

Federation startup REQUIRES a detached-signature Owner-GPG sentinel pair
REGARDLESS of bind. Each pair = (signed cleartext `.md`) + (detached
`.asc` signature):

1. **Enable pair (MANDATORY)**:
   - `.claude/data/federation/enabled.md`
   - `.claude/data/federation/enabled.md.asc`

2. **LAN pair (additional, REQUIRED when bind is non-loopback)**:
   - `.claude/data/federation/lan-enabled.md`
   - `.claude/data/federation/lan-enabled.md.asc`

Each pair is verified via a TWO-STAGE composition:

```python
# Stage 1 — cryptographic GOODSIG + VALIDSIG + allowlist check
ok, fpr, reason = verify_detached(
    signed_md,
    signed_md_asc,
    allowlist_fprs=[OWNER_FPR_00000000_NORMALISED],
)
if not ok:
    emit("federation_enable_sentinel_invalid", reason=reason)
    return False  # fail-CLOSED

# Stage 2 — ADR-121 signer expiry/revocation check
signer_ok, signer_reason = is_valid_signer(fpr, ...)
if not signer_ok:
    emit("federation_enable_sentinel_invalid", reason=f"signer_invalid:{signer_reason}")
    return False  # fail-CLOSED
```

Both stages MUST pass. Stage 1 covers gpg-binary-missing / bad-sig /
wrong-key / missing-files / parse-error. Stage 2 covers signer-expiry /
signer-revocation per ADR-121.

**API correction note**: `_lib/gpg_verify.verify_detached(...)` returns
a `(ok, fpr, reason)` tuple and does NOT raise. The "GpgVerifyError"
wording from prior drafts was incorrect.

### Part 5 — Non-loopback bind gate (AC3 LAN gate)

ALL non-loopback binds gate via `ipaddress.ip_address(bind).is_loopback`
on the resolved address. Hostnames resolving non-loopback (e.g.,
`local.example` → `192.168.1.50`) are gated. IPv6 `::` / `::0` /
unspecified are gated (counted as non-loopback by stdlib convention).

Reject set explicitly enumerated: any address where
`not addr.is_loopback` triggers `federation_lan_bind_denied` UNLESS the
LAN pair (Part 4 §2) is present and BOTH stages verify.

### Part 6 — Audit-chain stitching

When a node consumes another node's `/audit-summary`, each remote event
is tagged client-side with:

- `federation_origin: <peer_id_cert_fingerprint>` — origin attribution
- `fed_correlation_id: <opaque-id>` — cross-node correlation propagated
  via `X-CEO-Federation-Correlation-Id` header

The local audit-log includes the tagged remote events alongside local
emits. Investigators can trace any event back to the originating node
via grep on `federation_origin`.

### Part 7 — Mechanical write blocking

Method dispatcher rejects all non-GET methods (POST/PUT/PATCH/DELETE/
OPTIONS/HEAD) with HTTP 405 + audit
`federation_write_attempt_blocked`. The block is a mechanical filter
at request-dispatch BEFORE route matching — NOT a documentation
convention.

### Part 8 — Cost-envelope manifest

Per ADR-064, the federation surface emits a cost-envelope manifest at
`.claude/sidecars/c1-crypto/stdlib-ssl-mvp/manifest.json` per ADR-126
§Part 4 schema:

- Cert generation cost: ~$0 (self-signed via openssl)
- Storage cost: <1 KB per peer
- Audit-chain extension cost: bounded by remote `/audit-summary`
  fetch frequency × event-redaction CPU
- 30-day soak budget: <$1 per node-pair

## §3. Consequences

### Positive

- Single, auditable cross-machine trust boundary with explicit
  fail-CLOSED on every error path.
- 2-stage sentinel composition makes the enable surface tamper-evident
  to both cryptographic forgery AND signer-expiry / revocation.
- Read-only-MVP scope makes the trust expansion incremental: the next
  blast-radius increase (write-mode) requires a separate ADR amendment.

### Negative

- 2 Owner-GPG sentinel pairs (4 sentinel files) increase the install
  ceremony cost. Mitigated by gpg-agent caching → single-passphrase
  ceremony post-first-sign.
- 90-day cert rotation cycle adds operational overhead. Mitigated by
  hot-rotation M=2-of-N=3 quorum pattern (ADR-121 analogy).
- DER fingerprint rotation invalidates the pin (vs SPKI which survives).
  Migration to SPKI requires C1 sidecar shipped via PLAN-099-FOLLOWUP.

### Reversal

If a fatal flaw surfaces in the federation surface:

1. Set `CEO_FEDERATION_ENABLED=0` master kill (instant).
2. Remove `enabled.md` sentinel (next start fail-CLOSED).
3. Tag patch release with peers.yaml empty + revocation of all certs.

Operational reversal does NOT require a new ADR — the kill-switch
chain (ADR-129 §Part 8) is sufficient. If a doctrinal change is
required (e.g., redefining the trust boundary), a future ADR-135
amendment under PLAN-099-FOLLOWUP documents the scope post-hoc.

## §4. References

- ADR-129 — C1 crypto capability class (the primitive contract
  federation USES).
- ADR-126 §Part 3 — governed sidecar capability model + ADR slot
  reservation table.
- ADR-121 — sentinel signer registry (Stage-2 expiry/revocation gate
  used by Part 4 §2).
- ADR-089 — kernel-path enumeration pattern (Wave E in-repo paths
  pattern).
- ADR-042 §Auth — analogous trust boundary for in-process MCP handlers.
- ADR-115 — post-audit-SOTA maintenance doctrine.

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
