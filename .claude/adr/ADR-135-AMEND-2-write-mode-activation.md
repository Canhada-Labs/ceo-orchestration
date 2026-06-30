---
id: ADR-135-AMEND-2
title: Federation write-mode ACTIVATION — default-OFF wiring + activation pre-conditions
status: PROPOSED
proposed_at: 2026-05-23
proposed_by: CEO (PLAN-112-FOLLOWUP-federation-wire-or-delete — S158 overnight package)
deciders: [CEO]
consulted: [identity-trust-architect, security-engineer, threat-detection-engineer, qa-architect]
amends: ADR-135-AMEND-1
related_plans: [PLAN-099, PLAN-099-FOLLOWUP, PLAN-112, PLAN-112-FOLLOWUP-federation-wire-or-delete]
related_adrs: [ADR-126, ADR-129, ADR-135, ADR-135-AMEND-1, ADR-121, ADR-125]
risk_tier: C  # write-mode remains Tier-C (default-OFF)
codex_validation:
  thread: PENDING  # to be filled by morning Codex pair-rail (AC18)
  verdict: PENDING
vote_trigger:
  # ADR-095 doctrine: event/data-volume gate — NO calendar dates
  # Promotion to ACCEPTED requires ALL of:
  # (1) At least one adopter activates write-mode (CEO_FEDERATION_WRITE_MODE=1)
  #     in a production environment AND reports success in GitHub issues
  # (2) Full federation test suite green (167 tests py3.9 + 171 tests py3.11)
  #     on ≥2 consecutive CI runs after the adopter activation event
  # (3) No P0/P1 security finding in the 11-gate chain for ≥30 live write
  #     operations logged in audit-log.jsonl
  trigger_type: event_and_data_volume
  adopter_production_activation_count_min: 1
  live_write_ops_min: 30
  ci_green_consecutive_runs_min: 2
  debate_round_required: false  # security-engineer + identity-trust-architect already consulted
---

# ADR-135-AMEND-2 — Write-mode ACTIVATION (default-OFF)

## §1. Why this amendment

ADR-135-AMEND-1 (ACCEPTED, S148) defined the write-mode trust boundary,
the 11-gate chain, the RBAC matrix, and the third (write-enable) sentinel
pair. But the wiring was never applied — `server.py` `do_POST` returned
an unconditional 405 and the 4 handlers / `scopes` / `rate_limit` /
`audit_chain_ext` modules were never imported by the request path
(PLAN-112 finding F-1.7 — "module-complete but production-unreachable",
F-7.10 — "ATT&CK emitters orphaned", F-5.8 — "90d cert deadletter").

This amendment records the **ACTIVATION** of write-mode and three
material corrections the activation work surfaced that AMEND-1 got wrong
or left implicit.

## §2. Activation model — default-OFF, two-layer

Write-mode is reachable ONLY when BOTH layers pass (fail-CLOSED on either):

- **Layer 0a — env master switch.** `CEO_FEDERATION_WRITE_ENABLED` must
  equal the exact string `"1"`. Unset / empty / `"0"` / `"true"` / any
  other value → write-mode OFF → `do_POST` returns 405 exactly as before.
  This is STRICTER than the read-mode kill-switch (`CEO_FEDERATION_ENABLED`
  accepts `1/true/TRUE`) — write activation is higher-blast-radius.
- **Layer 0b — write-enable GPG sentinel pair** (the third pair, per
  AMEND-1 §3): `.claude/data/federation/write-enabled.md{,.asc}` must pass
  the 2-stage `verify_enable_sentinel_pair` (verify_detached +
  is_valid_signer). This is ALSO Gate #8 in the per-request chain.

A default install ships with NEITHER → POST is unreachable. Activation is
an explicit Owner action (set the env + GPG-sign the write-enable
sentinel). This satisfies PLAN-112-FOLLOWUP AC1/AC5/AC7/AC14.

### §2.1 — CORRECTION: `ALLOWED_HTTP_METHODS` must NOT be flipped

AMEND-1 / the Wave-D blueprint instructed flipping
`ALLOWED_HTTP_METHODS = frozenset(("GET","POST"))` as a module constant.
**That is unsafe** — it would make POST reachable in a DEFAULT install
(violating default-OFF). The constant STAYS `("GET",)`. POST is admitted
PER-REQUEST by `_FederationHandler.parse_request` consulting
`_write_mode_active()` (Layer 0a AND Layer 0b). `WRITE_ALLOWED_HTTP_METHODS`
exists only for the `Allow:` response-header advertisement when write-mode
is active.

## §3. Mandatory activation pre-conditions (VETO-grade, from Wave A)

These are encoded as code + tests, not prose promises:

- **Revocation propagates <60s without restart** (P0-1). A reload-watcher
  re-parses `peers.yaml` (mtime+sha256 debounced) + refreshes
  `httpd.federation_peers` + re-runs cert-level revocation, on every write
  dispatch AND on a 5s poll thread (bounds the SLO under zero traffic).
  Denial holds at BOTH the SPKI/connection-accept layer (`_lookup_peer_record`
  refreshes before matching) AND Gate #7. Every reload emits
  `federation_peer_list_reloaded` (NEW action — §4) so the SLO is
  forensically observable. (R-IT-A/B/C.)
- **ATT&CK detection is reachable + FP-bounded** (P0-2). The real
  `rate_limit.py` is wired at Gate #9 (default-DENY on exception — no gate
  fails OPEN). T1499 storm / backpressure, T1485 auto-revoke, T1565 tamper
  fire from the production path. FPR ≤15% per emitter class is gated against
  a committed ≥200-record/class benign corpus. T1485 auto-revoke is proven
  bounded-TTL + non-cross-peer (anti self-DoS). (R-TD-1/2/3.)
- **Gate #3 is SPLIT, not reordered** (R-SE-a). The non-mutating
  timestamp-window preflight runs before the body read; the MUTATING nonce
  commit (`ReplayCache.check_and_record`) runs ONLY after HMAC verify —
  so a forged/replayed request never poisons the nonce ring.
- **11-gate chain tested against real fixtures, full HTTP integration,
  kill-switch walk** (P0-3/P0-4). See PLAN-112-FOLLOWUP §5 AC5/AC6/AC17.

## §4. CORRECTION: the `_safe_emit` no-op trap (R-TD-1)

AMEND-1 assumed the Wave-D/E `federation_*` audit emitters were live once
Wave F.2 registered them in `_KNOWN_ACTIONS`. They were NOT: the
federation modules' `_safe_emit` looked up `emit_<action>` (a NAMED
wrapper). Only the 10 PLAN-099-MVP actions have named wrappers; the ~14
Wave-F.2 write-mode actions are dispatched via `emit_generic` and have NO
named wrapper. So `_safe_emit` SILENTLY NO-OPED every storm/tamper/denial
emit — dead detection that passes any HTTP-status-only test green.

**Fix:** `_safe_emit` in all 4 federation modules now falls back to
`emit_generic(action, **fields)` when no named wrapper exists. Verified:
`emit_generic("federation_message_storm_detected", …)` writes a real
chained audit record. Tests assert the EMITTED record (via an
`emit_generic` spy), not the HTTP status.

## §5. NEW audit action — `federation_peer_list_reloaded`

P0-1 requires a forensic marker per reload. `federation_peer_list_reloaded`
is NOT in `_KNOWN_ACTIONS` and MUST be registered via kernel-override at
ship (count 255→256; contract SHA rebaseline). Fields:
`peer_count` (int), `reload_reason` (closed enum:
`content_changed` / `parse_error_kept_last_good`), `source_path` (str≤128),
plus the standard `session_id`/`project` identity. See the W7 registration
spec in the staging package.

## §6. Write-mode action classification (Codex R1-WIRE)

Of the Wave-F.2 `federation_*` actions, classify:

- **Covered-by-WIRE** (gain a real production emitter in this plan):
  `federation_peer_registered`, `_peer_revoked_remote`,
  `_audit_event_pushed`, `_audit_event_pushed_batch`, `_scope_denied`,
  `_write_endpoint_denied`, `_write_disabled_sentinel_invalid`,
  `_message_storm_detected`, `_audit_log_backpressure`, `_tamper_detected`,
  `_cert_validity_window_too_large`, `_event_action_blocked`,
  `_peer_registered_collision`, `_peer_invalid_no_fingerprint`,
  `_pin_legacy_used`, `_spki_fingerprint_mismatch`, + NEW
  `_peer_list_reloaded`.
- **RESERVED — outside this WIRE's scope** (key-rotation / key-floor
  features, not write-mode dispatch): `federation_hmac_secret_rotated`,
  `federation_key_floor_rejected`, `federation_key_floor_stale`. These are
  marked RESERVED with this doc note — NOT silent ghosts. They belong to a
  future key-rotation feature; their presence in `_KNOWN_ACTIONS` is
  retained so the contract is stable.

## §7. F-5.8 — 90-day cert validity window enforced

`peer_register._validate_peer_body` now parses `not_valid_before` /
`not_valid_after`, rejects a window > `MAX_CERT_VALIDITY_DAYS` (90), and
the handler emits `federation_cert_validity_window_too_large`. The ghost
action becomes a real producer.

## §8. Decision

PROPOSED. On Owner GPG-signed acceptance at ship: status → ACCEPTED-AMENDED
(or ACCEPTED). The activation remains Tier-C default-OFF; promotion to
Tier-B still requires AMEND-1 §Part 9 soak (30d + ≥1k pushes + zero
unrecoverable RBAC errors).

## §9. Residual / known-gap (honest)

- **Scopes/allowlist wiring through `load_peers`** is INCOMPLETE — see
  PLAN-112-FOLLOWUP NOTES.md "REMAINING". `load_peers` does not yet parse
  `scopes` / `audit_event_push_allowlist` into PeerRecord, so a registered
  peer cannot exercise a granted scope at runtime until that parse is added.
  Gate #6 therefore default-DENIES every peer today (fail-CLOSED — safe, but
  means write-mode is not yet end-to-end functional for a real adopter). The
  dispatcher + RBAC plumbing is correct; the peers.yaml parse is the missing
  link. Tracked as the top REMAINING item.
- **Full mTLS HTTPS integration test** (P0-4 gold path) is specified but not
  delivered as a passing test in this package (needs generated cert chains);
  the delivered integration tests drive the real handler methods directly +
  the real rate_limit/audit_chain_ext modules. See NOTES.md.
