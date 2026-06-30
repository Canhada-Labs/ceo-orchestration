---
id: ADR-135-AMEND-1
title: Federation contract — write-mode trust boundary + per-method RBAC + SPKI migration
status: ACCEPTED
proposed_at: 2026-05-20
accepted_at: 2026-05-20
proposed_by: CEO (S146 overnight prep — PLAN-099-FOLLOWUP Wave D prereq)
accepted_by: CEO (S148 — PLAN-099-FOLLOWUP v1.39.1 ship ceremony Phase 0b)
deciders: [CEO]
consulted: [identity-trust-architect, security-engineer, threat-detection-engineer, code-reviewer, qa-architect]
amends: ADR-135
related_plans: [PLAN-099, PLAN-099-FOLLOWUP, PLAN-102]
related_adrs: [ADR-126, ADR-129, ADR-129-AMEND-1, ADR-135, ADR-121, ADR-115, ADR-124, ADR-125]
risk_tier: C  # write-mode INCREASES blast radius vs ADR-135 read-only; remains Tier C
codex_validation:
  thread: 019e4662-cfc3-7bb1-899a-158ae3b3842e  # PLAN-099-FOLLOWUP final bundle R2 review (covers staged ADR-135-AMEND-1 body + 11-gate chain + RBAC matrix)
  verdict: ACCEPT (iter-4 clean; iter-3 ACCEPT-WITH-FIXES P2=1 resolved; iter-2 BLOCK P0=2/P1=1/P2=1 resolved; iter-1 BLOCK P0=4/P1=4/P2=1 resolved)
---

# ADR-135-AMEND-1 — Write-mode trust boundary

## §1. Amendment scope

ADR-135-AMEND-1 amends ADR-135 (federation contract MVP) in FOUR
places:

1. **§Part 2 — EXTENDED** with the write-mode authority model
   (per-method RBAC + per-peer granted scopes + revocation propagation).
2. **§Part 7 — UPDATED** to soften the "mechanical 405 on all non-GET"
   block: writes that match the per-method scope check are PERMITTED;
   non-GET methods WITHOUT a scope match still 405 + audit-emit. The
   mechanical block remains DEFAULT-OFF; scope grant is the explicit
   override.
3. **§Part 9 — NEW** — write-mode soak gate: 30d Tier-C operation +
   ≥1k successful audit-event pushes + zero unrecoverable RBAC errors
   before considering Tier-B promotion.
4. **§migration — NEW** — peers.yaml schema v1.x → v2.0 migration,
   90-day backward-compat window, BOTH SPKI + DER pins accepted.

The §Part 1 trust boundary, §Part 3 cert rotation policy, §Part 4
enable protocol, §Part 5 LAN bind gate, §Part 6 audit-chain stitching,
and §Part 8 cost-envelope remain UNCHANGED. The §Part 4 2-stage
sentinel composition is REUSED for the WRITE-ENABLE sentinel (see §3
below — third sentinel pair).

## §2. Write authority model (extends ADR-135 §Part 2)

### 2.1 — Per-method RBAC matrix

Each write endpoint is bound to ONE scope name. Each peer in
`peers.yaml[peer].scopes` declares the LIST of granted scope names.
A request is authorised iff:

1. The route maps to a single scope name (Part 7 §1 dispatcher mapping).
2. The peer's `scopes` list contains that scope name (case-sensitive
   exact match).
3. The request `X-CEO-Federation-Scope: <scope-name>` header matches
   the route's scope (defense-in-depth — prevents accidental scope
   widening via path-only check).
4. The request method matches the route's method (i.e. POST scope
   bound to POST endpoint).

The route mapping table (locked at this amendment; new routes require
an amend):

| Route                                | Method | Scope name              | Permitted side-effect          |
|--------------------------------------|--------|-------------------------|---------------------------------|
| `/federation/peer-register`          | POST   | `peer_register`         | Append entry to `peers.yaml` (Owner-sentinel-gated) |
| `/federation/audit-event`            | POST   | `audit_event_push`      | Append remote audit event to local audit-log |
| `/federation/audit-event/batch`      | POST   | `audit_event_push_batch` | Same as above, batched (≤100 events / request) |
| `/federation/peer-revoke`            | POST   | `peer_revoke`           | Mark `peers.yaml[peer].revoked: true` |

NO other writes are permitted in v1.39.1. New routes land via
ADR-135-AMEND-2 (numbered post-amend).

### 2.2 — Authorisation evaluation order

The handshake/handler chain evaluates the following gates **in this
order**; any non-pass short-circuits to 4xx/5xx + audit:

1. mTLS handshake — same as ADR-135 §Part 1 (peer-pinned cert).
2. SPKI fingerprint match (per ADR-129-AMEND-1 §3); DER fallback during
   90d migration window.
3. HMAC + nonce + timestamp replay protection — same as PLAN-099 AC13.
4. Method allowlist — only methods bound to a scope (the §2.1 table)
   pass; everything else 405 + `federation_write_attempt_blocked`.
5. `X-CEO-Federation-Scope` header present + matches route's scope
   name → otherwise 400 + `federation_scope_denied`
   (`reason_code="scope_header_missing"`).
6. Peer's `scopes` list contains the scope name → otherwise 403 +
   `federation_write_endpoint_denied`
   (`reason_code="write_unauthorized"`, `gate_failed=6`).
7. Peer revoked? (`peers.yaml[peer].revoked: true`) → 403 +
   `federation_write_endpoint_denied`
   (`reason_code="peer_revoked"`, `gate_failed=7`).
8. Write-enable sentinel valid? (the third sentinel pair — §3 below) →
   otherwise 503 + `federation_write_disabled_sentinel_invalid`.
9. Rate-limit — per-route table §2.4 — exceeds → 429 +
   `federation_write_endpoint_denied`
   (`reason_code="rate_limit:<route>" | "per_peer_secondary" | "circuit_breaker:..."`,
   `gate_failed=9`).
10. Destructive-op authorisation gate — `peer_register` /
    `peer_revoke` additionally require a per-request
    Owner-co-signature sentinel (`X-CEO-Owner-Sigref: <sentinel-id>`
    header references a pre-staged Owner-signed sentinel under
    `.claude/data/federation/sentinels/<id>/` — see §3 below).
    Missing or invalid → 403 + `federation_write_endpoint_denied`
    (`reason_code="destructive_op_unauthorized:<sub-reason>"`,
    `gate_failed=10`).
11. Route handler executes; emits route-specific audit event
    (`federation_peer_registered` / `federation_audit_event_pushed` /
    `federation_peer_revoked_remote`).

### 2.3 — Revocation propagation

When a peer is revoked (locally OR via remote `/federation/peer-revoke`):

1. `peers.yaml` is atomically updated — `revoked: true`.
2. The next handshake from that peer fails at gate #7 above.
3. All other peers receive a `federation_peer_revoked_propagated` event
   on their next `/federation/audit-summary` fetch with `federation_origin =
   <revoked-peer-fpr>`.
4. Local cache invalidation is automatic — gate #7 re-parses
   `peers.yaml` on every handshake (ADR-121 §6 v1.x no-cache contract).

### 2.4 — Rate limits

Default write rate-limits (per (peer, route, source-ip-prefix) tuple).
The implementation at `_lib/federation/rate_limit.py` MUST match this
table VERBATIM (F-005 alignment — Wave E rate_limit.py is the
source-of-truth code; this ADR table is the source-of-truth contract):

| Route                                | Limit         | Window  | Notes |
|--------------------------------------|---------------|---------|-------|
| `/federation/peer-register`          | 1 / hour      | rolling | high-cost destructive |
| `/federation/peer-revoke`            | 5 / hour      | rolling | destructive op |
| `/federation/audit-event`            | 60 / minute   | rolling | high-volume legitimate path |
| `/federation/audit-event/batch`      | 6 / minute    | rolling | ≤100 events per request |

Per-peer-only **secondary** limiter (AC-LIM-2 follow-up from PLAN-099
MVP — REQUIRED by F-005): write requests are also bucketed by `(peer,)`
regardless of route OR source IP. Default secondary cap: **100 req /
hour TOTAL per peer** (sum across all 4 write routes). A compromised
peer rotating source IPs OR multiplexing routes cannot multiply
throughput. Both buckets (primary + secondary) MUST have ≥1 token to
permit the request; either bucket empty → 429 +
`federation_write_endpoint_denied` (`reason_code="rate_limit:<route>"`
for primary trip / `"rate_limit:per_peer_secondary"` for secondary).

### 2.5 — Destructive-op gating

`/federation/peer-register` and `/federation/peer-revoke` are CLASSIFIED **destructive
operations** under MITRE ATT&CK T1485 (Data Destruction — the
`peer_revoke` path mutates the trust-root surface). The gating
(§2.2 gate #10):

- A per-request Owner-co-signature sentinel — a small file at
  `.claude/data/federation/sentinels/<request-id>/approval.md` +
  `.asc` signed by the Owner GPG key, pre-staged BEFORE the request
  is issued. The `<request-id>` is the value sent in the
  `X-CEO-Owner-Sigref` header.
- The sentinel is verified via the same `verify_detached` +
  `is_valid_signer` 2-stage composition as the enable sentinels.
- Sentinels are SINGLE-USE — enforced via filesystem-atomic
  claim/consume semantics (TOCTOU-resistant on POSIX same-FS):
  1. **Step 1a (atomic claim — `.md`)**: `os.rename(sentinel_path,
     sentinel_path + ".inflight")` — atomic on POSIX same-FS.
     Concurrent claims race here: only one wins; others receive
     `FileNotFoundError` → server responds 409 Conflict
     (audit `federation_sentinel_consumed_replay` with
     `reason_code: sentinel_inflight_collision` — folded onto the
     existing single-use action; see §6 table).
  1b. **Step 1b (atomic claim — `.asc`)**: `os.rename(sentinel_path + ".asc",
     sentinel_path + ".asc.inflight")`. If this fails after step 1a
     succeeded, the handler MUST reverse-rename the `.md.inflight`
     back to `.md` (best-effort recovery) and respond 500 with
     audit `federation_sentinel_consumed_replay` +
     `reason_code: sentinel_asc_claim_failed`. The `.md` rename in
     step 1a is the canonical claim point (it gates the race);
     `.asc` rename is secondary but MUST succeed for verification
     in step 2.
  2. **Step 2 (verify .inflight pair)**: load the `.md.inflight`
     content + `.asc.inflight` signature; run 2-stage verify; check
     `signed_at` timestamp against now() — refuse if older than 24h
     TTL with `federation_sentinel_ttl_expired`.
  3. **Step 3 (process)**: route handler executes (gate #11 in
     §2.2). Audit emit at start + end.
  4. **Step 4 (atomic consume — both files)**:
     `os.rename(sentinel_path + ".inflight",
     sentinel_path + ".consumed-<request-id>")` AND
     `os.rename(sentinel_path + ".asc.inflight",
     sentinel_path + ".asc.consumed-<request-id>")` — both atomic.
     Order: `.md` first (canonical), then `.asc`. A crash between
     the two leaves a recoverable state (the `.consumed-*` `.md`
     marks the request done; the orphaned `.asc.inflight` is
     reaped by the housekeeping pass).
- Replay attempts after step 4 fail at step 1 (file already moved
  to `.consumed-*`) with `federation_sentinel_consumed_replay`.
- **Honest-scope caveat**: a replay window exists BETWEEN steps 2-4
  (post-verify, pre-consume). If the server crashes mid-handler an
  attacker who already possesses the `.inflight` content cannot
  re-trigger because the original `<sentinel-id>.md` was already
  moved at step 1 — i.e. the BREAK-IN-WINDOW is closed by step 1's
  atomic rename. The remaining residual is: an in-flight handler
  may legitimately complete OR crash; recovery semantics on crash
  are deferred to follow-up (Wave E.5 test surfaces the crash path).
- Sentinel TTL: 24h from `signed_at` timestamp inside the cleartext
  `.md` — enforced at step 2 (ctime check refuses if older).

## §3. Write-enable sentinel pair (THIRD pair)

Beyond the Enable + LAN sentinel pairs from ADR-135 §Part 4, write-mode
REQUIRES a THIRD pair, REGARDLESS of bind:

- `.claude/data/federation/write-enabled.md`
- `.claude/data/federation/write-enabled.md.asc`

Verification uses the SAME 2-stage composition (Stage-1
`verify_detached` against Owner allowlist + Stage-2 `is_valid_signer`
ADR-121 lifecycle check). Without the third pair valid, ALL writes
fail at gate #8 with `federation_write_disabled_sentinel_invalid`. The
master `CEO_FEDERATION_WRITE_ENABLED=0` env-var is the THIRD layer
override and the natural-default-OFF position.

Why a separate write sentinel (vs reusing Enable):
- Operational distinction — Owner can enable federation read-only
  without enabling writes. Read-only ≠ write-mode is a meaningful
  operational divide.
- Audit forensics — the write-enable sentinel ceremony has its own
  `sentinel_signer_quorum_attempted` audit trail.
- Kill-switch granularity — disabling writes alone (revoke
  `write-enabled.md.asc`) leaves the read federation operational.

## §4. Kill-switch chain extension (extends ADR-129 §Part 8)

PLAN-099-FOLLOWUP extends the 6-layer chain with TWO write-specific
layers, BEFORE the existing layers run:

0a. **`CEO_FEDERATION_WRITE_ENABLED=0`** env var (master write-disable).
0b. **Write-enable sentinel** (§3 above) — 2-stage verify fail-CLOSED.

Then the existing 6 layers run:

1. `CEO_FEDERATION_ENABLED=0` env var.
2. Enable sentinel pair.
3. SIGTERM→SIGKILL.
4. cgroups/ulimit.
5. Supervisor watchdog.
6. Coordinator counter.

The complete chain is therefore 8 layers (0a + 0b + 1..6). Removing
ANY one of the first three (0a, 0b, 1) fully disables writes; layer 2
disables reads + writes. Layers 3-6 are runtime enforcement.

## §5. Migration (peers.yaml v1.x → v2.0)

### 5.1 — Field additions

```yaml
# v2.0 peer entry (PLAN-099-FOLLOWUP) — NEW + LEGACY fields side-by-side
peers:
  - peer_id: peer-east-01
    # NEW (Wave B.2 + Wave C.1)
    peer_id_spki_fingerprint: "<64-hex>"     # primary pin (PLAN-099-FOLLOWUP)
    scopes: ["audit_event_push"]             # NEW — write authorisation
    # LEGACY (kept during 90d migration window)
    peer_id_cert_fingerprint: "<64-hex>"     # full-cert DER (PLAN-099 MVP)
    ca_pin_sha256: "<64-hex>"
    not_valid_after: "2026-08-17T00:00:00Z"
    not_valid_before: "2026-05-17T00:00:00Z"
    revoked: false
    hmac_secret_hex: "<64-hex>"
    # NEW (Wave B.3)
    key_floor_verified_at: "2026-05-20T00:00:00Z"   # set by cert_inspector
```

### 5.2 — Backward-compat invariants

During the 90-day migration window:

- A peer row MAY have ONLY `peer_id_cert_fingerprint` (legacy v1.x).
  Server accepts via DER fallback.
- A peer row MAY have BOTH `peer_id_spki_fingerprint` AND
  `peer_id_cert_fingerprint` (migrated row).
- A peer row MAY have ONLY `peer_id_spki_fingerprint` (new v2.0 install).
- A peer row MUST have AT LEAST ONE of the two fingerprint fields. A
  row with neither is REJECTED at parse time with
  `federation_peer_invalid_no_fingerprint`.

### 5.3 — Migration tool

`tools/migrate-peers-yaml.py` (stdlib) — reads v1.x `peers.yaml`,
calls `cert_inspector.inspect()` on each peer's pinned cert (if
available), and emits a v2.0 row with both fingerprints. Idempotent.
Schema details in
`.claude/plans/PLAN-099-FOLLOWUP/peers-yaml-schema-migration.md`.

### 5.4 — Migration close (data-volume-driven, not calendar-driven)

The migration window closes when both:

- ≥80% of registered peer rows have a non-empty
  `peer_id_spki_fingerprint`, AND
- ≥30 days since the v2.0 schema first landed in `peers.yaml` of any
  adopter install (gated on first non-empty `spki` field in any
  registry).

When both are met, ADR-129-AMEND-2 + ADR-135-AMEND-2 (a JOINT amend
pair) REMOVE the DER fallback. Not scoped for PLAN-099-FOLLOWUP — these
amends land via PLAN-099-FOLLOWUP-NEXT after the soak.

Per ADR-095 no-calendar-gates doctrine — the 30-day floor is a CONTRACT
not a calendar gate; the 80% threshold is the data-volume driver.

## §6. New audit actions

PLAN-099-FOLLOWUP Wave B/C/D/E introduces NEW audit actions; this ADR
documents the contract they must conform to (the actual `_KNOWN_ACTIONS`
registration is gated under kernel-override per ADR-116):

| Action                                          | Wave | Scope |
|-------------------------------------------------|------|-------|
| `federation_audit_event_pushed`                 | D.1  | /federation/audit-event success (single) |
| `federation_audit_event_pushed_batch`           | D.1  | /federation/audit-event/batch success |
| `federation_audit_log_backpressure`             | E.1  | T1499 p99 latency trip |
| `federation_cert_validity_window_too_large`     | B.4  | >90d cert reject |
| `federation_event_action_blocked`               | E.3  | audit_event_push_allowlist deny |
| `federation_hmac_secret_rotated`                | B.4  | Wave B.4 rotation tool |
| `federation_key_floor_rejected`                 | B.2  | cert_inspector reject |
| `federation_key_floor_stale`                    | B.2  | key_floor_verified_at expired |
| `federation_message_storm_detected`             | E.1  | T1499 circuit-breaker trip |
| `federation_peer_invalid_no_fingerprint`        | B.2  | peers.yaml row missing both pins |
| `federation_peer_registered`                    | D.1  | /federation/peer-register success |
| `federation_peer_registered_collision`          | D.2  | peer_id already exists |
| `federation_peer_revoked_remote`                | D.1  | /federation/peer-revoke success |
| `federation_pin_legacy_used`                    | C.2  | DER fallback during 90d migration |
| `federation_scope_denied`                       | D.2  | gate #5 fail — `reason_code` carries sub-cause |
| `federation_spki_fingerprint_mismatch`          | C.2  | handshake gate fail |
| `federation_tamper_detected`                    | E.1  | T1565 audit-chain hash break / HMAC mismatch |
| `federation_write_disabled_sentinel_invalid`    | D.2  | gate #8 fail (sentinel missing OR invalid) |
| `federation_write_endpoint_denied`              | D.2  | gates #6/#7/#9/#10 multiplexer — `reason_code` + `gate_failed` carry context |

ATT&CK bindings (Wave E): T1499 + T1485 + T1565 + T1556 + T1071.001 +
T1573.

**Action count delta**: this amendment touches **20 audit actions** beyond the
PLAN-099 v1.32.0 baseline (+19 net-new `_KNOWN_ACTIONS` entries;
`federation_cert_rotated` already exists from PLAN-099 MVP S134 and is
field-shape-superseded in-place at Wave F.2; `_KNOWN_ACTIONS` 235 → 254).
The 5 multi-gate failure surfaces are collapsed into the
`federation_write_endpoint_denied`
canonical multiplexer (gates #6/#7/#9/#10) plus `federation_scope_denied`
(gate #5) plus `federation_write_disabled_sentinel_invalid` (gate #8) —
each carrying `reason_code` + (where relevant) `gate_failed` to preserve
forensic granularity. NO non-canonical action names are permitted in
the emit-call sites — the Wave F.2 kernel-override sentinel
`PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` registers EXACTLY the 20 actions in
this table. Plan AC counts + the contract test rebaseline MUST match
this table.

## §7. Dependencies (extends ADR-129-AMEND-1 §5)

This amendment introduces NO new framework-level dependencies beyond
those declared by ADR-129-AMEND-1 §5 (`cryptography>=42.0,<44.0` —
sidecar-fenced).

The federation server + client modules continue to import only:

- Python stdlib (per ADR-002).
- `_lib/federation/cert_inspector.py` — STDLIB-ONLY bridge.
  Subprocess-invokes the C1 crypto sidecar at
  `.claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/cert_inspector.py`
  per ADR-126 §Part 1 + §Part 2. Core never imports `cryptography`
  directly; the sidecar is the SOLE legitimate importer. Inter-process
  IPC is argv (cert path) + stdout (JSON report) + stderr (error).
- Other `_lib/` siblings.

## §8. Soak gate to Tier-B promotion (§Part 9 NEW)

Per ADR-125 Tier C → Tier B requirements, write-mode ships Tier C
default-OFF and MAY promote to Tier B only after:

1. **≥30 days** of operation in the wild (data-volume floor — at
   least 1k successful `/federation/audit-event` pushes across ≥3 distinct
   peer pairs).
2. **Zero unrecoverable RBAC errors** during the soak. Specifically,
   `federation_write_endpoint_denied` events with
   `reason_code` starting `"destructive_op_unauthorized:"` count = 0
   OR every instance has a paired Owner-acknowledged forensic record
   (test-mode validation; gate #10 + Owner co-sign sentinel coverage).
3. **Zero peer registry corruption events** during the soak —
   `federation_peer_invalid_no_fingerprint` count must stay 0
   post-migration window.

Tier-B promotion lands via ADR-135-AMEND-2 + a dedicated plan
(PLAN-099-FOLLOWUP-2; speculative scope). Tier-A promotion is NOT
on any roadmap — federation write-mode does not become "always-on"
without a new top-level doctrinal ADR.

## §9. Cross-references

- ADR-135 — original federation contract MVP (amended by THIS amend)
- ADR-129-AMEND-1 — SPKI pin + key-floor lift (JOINT amend)
- ADR-126 §Part 4 — manifest schema (cryptography-mvp sidecar conforms)
- ADR-121 — sentinel signer rotation (reused for write-enable + per-
  request Owner co-sign sentinels)
- ADR-115 — post-audit-SOTA maintenance (constrains scope of follow-up)
- ADR-095 — no calendar gates (the 90d migration soak is
  data-volume-driven per §5.4)
- ADR-064 — LLM-FinOps cost-envelope (write surface cost in §Part 8
  of ADR-135 still bounded; rate-limits in §2.4 above prevent run-away)
- PLAN-102 — autonomous-loop opt-in: AC18 import-graph denylist
  EXTENDS to write endpoints; autonomous-loop MUST NOT invoke
  `/federation/peer-register` or `/federation/audit-event` or `/federation/peer-revoke`. Verified by
  Wave E.3 extension test.

## §10. Reversal

If write-mode produces an operational problem (e.g., RBAC matrix gap
discovered post-ship):

1. `CEO_FEDERATION_WRITE_ENABLED=0` (master kill — instant).
2. Remove `.claude/data/federation/write-enabled.md.asc` (next start
   fail-CLOSED at gate #8 for ALL writes).
3. Set every peer's `scopes: []` in `peers.yaml` (empty scopes =
   read-only — same as PLAN-099 MVP).
4. Tag patch release noting the rollback.

The reversal preserves the read federation surface (PLAN-099 MVP).
A doctrinal rollback (i.e. reintroducing the ADR-135 §Part 7
"all-non-GET-blocked" mechanical block) requires ADR-135-AMEND-2.

## §11. Acceptance criteria (for this amendment)

- AC-AMEND-1: ADR-135 §Part 2 EXTENDED with RBAC matrix matching §2.1
  table above.
- AC-AMEND-2: ADR-135 §Part 7 UPDATED with scope-gate exception path.
- AC-AMEND-3: ADR-135 §Part 9 ADDED (soak gate to Tier-B per §8).
- AC-AMEND-4: ADR-135 §migration ADDED (peers.yaml v1.x → v2.0 per §5).
- AC-AMEND-5: PLAN-099-FOLLOWUP Wave D ships the 4 write endpoints
  conforming to the §2 RBAC matrix; Wave E ships ATT&CK detection +
  sentinels per §6.
- AC-AMEND-6: 20 audit actions per §6 land via kernel-override
  `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` (+19 net-new entries
  + 1 in-place field-shape rewrite of federation_cert_rotated;
  `_KNOWN_ACTIONS` 235 → 254).
- AC-AMEND-7: AC18 (autonomous-loop import-graph denylist) EXTENDED to
  the 4 write endpoints; verified by Wave E.3 test.
- AC-AMEND-8: Codex MCP R2 promotion 3-iter ACCEPT (per ADR-129 /
  ADR-135 precedent S134).

## §Codex MCP gate trail

<to-be-filled-at-promotion-time>

Reviewed-by: <pending> (PLAN-099-FOLLOWUP promotion ceremony).
