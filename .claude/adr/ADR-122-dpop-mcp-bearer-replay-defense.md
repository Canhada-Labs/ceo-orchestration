---
id: ADR-122
title: R-031 — DPoP MCP bearer-replay defense (Defer-to-v2.0 path with §A spec preserved)
status: ACCEPTED
proposed_at: 2026-05-13
proposed_by: CEO (PLAN-090 Wave C — R1 6-archetype + R2 Codex MCP iter-3 ACCEPT 2026-05-13)
accepted_at: 2026-05-13
accepted_by: Owner @Canhada-Labs (0000000000000000000000000000000000000000) — PLAN-090 closeout ceremony S118 (v1.24.0)
chosen_scenario: B
chosen_scenario_rationale: 5-repo soak NOT-YET-STARTED (0/10 friction-count) per ADR-115 §v2.0 trigger doctrine; PLAN-083 v1.17.0 Wave 3 install validation deferred at S106 by Owner.
related_plans: [PLAN-084, PLAN-090, PLAN-100]
related_adrs: [ADR-042, ADR-052, ADR-064, ADR-090, ADR-115, ADR-117, ADR-118, ADR-124]
veto_floor: ADR-052 (security-engineer + identity-trust-architect + threat-detection-engineer)
codex_pair_rail: required (PLAN-090 R2 thread 019e212f-f85f-7fd2-a73a-29713ea9cc1f; cross-plan allocation thread 019e210c-8427-7e60-9d76-787636f0c834)
tags: [security, identity, mcp, dpop, rfc-9449, bearer-replay, v2-deferred]
authorization: PLAN-090 closeout ceremony
re_open_triggers:
  - CVE published against `loopback` MCP transports
  - Bearer token leak observed in audit log
  - 5-repo soak surfaces ANY replay attempt
  - Owner-friction count from 5-repo soak reaches >= 10
---

# ADR-122 — R-031 DPoP MCP bearer-replay defense

> **CHOSEN SCENARIO: §B — Defer-to-v2.0.** §A specification is preserved
> below verbatim so a future R-031 fire can land DPoP without
> re-debating the spec surface.

## §1. Context

Canonical roadmap (`.claude/plans/PLAN-084/canonical/evolution-roadmap.md`
line 283) tags R-031 as `deferred-to-v2.0`. R-031 covers cryptographic
proof-of-possession on MCP bearer tokens via DPoP per IETF RFC 9449.

ADR-115 (v2.0 trigger doctrine) requires ≥ 10 Owner-friction findings
from 5-repo soak to fire v2.0 plan-housing. PLAN-090 Wave C is therefore
a **decision gate**, not an implementation deliverable. The decision
chooses between:

- **§A — Ship-in-v1.x**: full DPoP per RFC 9449 §4-§7 + ~400 LoC + 60
  tests + JWT/EC-P256 conformance harness.
- **§B — Defer-to-v2.0**: explicit deferral; ship the friction-telemetry
  firing path so the trigger count is mechanically observable.

Wave C.1 soak-status audit
(`.claude/plans/PLAN-090/wave-c-soak-status.md`) found **soak count
0/10** at decision date 2026-05-13 — adopters_installed=0. The §B path
is therefore chosen mechanically.

## §A — Ship-in-v1.x (PRESERVED for future re-open)

> This section captures the full implementation spec the R1+R2 debate
> ratified. It is NOT executed in PLAN-090 — §B is chosen — but if any
> §re-open trigger fires, the next PLAN re-debating R-031 starts from
> this baseline.

### §A.1 — Scope (IDA P0 fold)

DPoP MUST cover **ALL MCP servers**, not Codex-only. Partial enablement
enables downgrade attacks: an attacker who can negotiate the un-DPoP
server bypasses the protection on the DPoP server by routing through
the weakest peer. Per-server enablement matrix in §A.2.

### §A.2 — Per-server enablement matrix

| MCP server | Required | Notes |
|---|---|---|
| `codex` | yes | primary surface; PLAN-070 OAuth flow already binds bearer |
| `claude_ai_*` | yes | published-by-org tools; threat surface identical |
| `supabase` | yes | data-plane access; replay risk highest |
| every other registered MCP | yes | downgrade attack defense |

A new MCP server registration MUST include DPoP support before being
added to `.claude/settings.json :: mcpServers` per a static check that
fails-closed.

### §A.3 — DPoP proof validation (RFC 9449 §4.3)

A DPoP proof JWT MUST validate ALL of:

1. `typ` header == `"dpop+jwt"` (RFC 9449 §4.2).
2. `alg` header ∈ `{ES256, EdDSA, ES384, ES512, PS256, PS384, PS512}`
   ONLY. Reject `alg=none` AND `alg=HS*`. Parser-precedence is BEFORE
   signature verification (cannot be downgraded post-signature).
3. `jwk` header present AND signature verifies against the public key
   in `jwk`.
4. `htm` claim matches the HTTP method (uppercase).
5. `htu` claim matches the request URI (normalized — query/fragment
   removed).
6. `iat` claim within ± 60 s (recommended max-clock-skew per RFC).
7. `jti` claim unique within cache TTL window (nonce cache — see §A.4).
8. `ath` claim (for protected-resource access) ==
   `SHA256(access_token)` base64url-encoded (RFC 9449 §4.3 + §7).
9. `cnf.jkt` thumbprint on the access token MUST match the `jwk`
   thumbprint (key binding per RFC 9449 §6.1).
10. REJECT DPoP-bound tokens presented as plain `Bearer` (downgrade
    defense; RFC 9449 §7.1).

### §A.4 — Nonce cache (RFC 9449 §11.1)

- TTL ≤ 5 min per RFC.
- Eviction: LRU + TTL-only (no count-based eviction → no DoS attack
  via cache flush).
- Size bound: configurable, default 16 384 entries.
- Cache key: `(jti, iat)` tuple.

### §A.5 — Test vectors

- Source from IETF DPoP interop suite OR hand-rolled per RFC 9449
  §4.2 examples with deterministic timestamps + nonces (NO
  `time.time()` inside proof generation — R1 QA P1 fold).
- 60 tests minimum at
  `.claude/hooks/tests/test_mcp_dpop_signature.py` +
  `test_mcp_dpop_verification.py` +
  `test_mcp_dpop_conformance.py`.

### §A.6 — TLS exporter binding (NOT RFC 9449 §4.3)

R2 Codex iter-1 P0 fold: `cnf.x5t#S256` TLS exporter binding is **NOT**
part of RFC 9449 §4.3. Documented as **OPTIONAL non-RFC local
extension** in this §A.6 only (Anthropic-internal hardening). NOT
required for spec conformance.

### §A.7 — Audit action

`dpop_replay_detected` registered in `_KNOWN_ACTIONS` + bound to ATLAS
`AML.T0051` (Prompt Injection — closest peer for trust-chain attack).

## §B — Defer-to-v2.0 (CHOSEN)

> §B is the path PLAN-090 ships. Soak-status (0/10) does not satisfy
> the v2.0 trigger. The §re-open clauses provide a mechanical re-open
> path that does NOT require a friction count if a more direct threat
> surface lands.

### §B.1 — Loopback-reduced threat surface (5 invariants)

R1 security-engineer P0 fold + R2 Codex iter-1 P1 fold: the
"loopback-reduced" claim from
`evolution-roadmap.md` is UNSAFE without explicit invariant assertions.
This ADR therefore declares 5 invariants with grep-verifiable test
fixtures:

1. **MCP server binds to `127.0.0.1`** (NOT `0.0.0.0`).
   Test: `test_mcp_loopback_bind.py` asserts via `netstat`/`ss`
   snapshot at server boot.
2. **NO CORS bypass + Fetch-Metadata + Origin validation.** Asserts:
   - `Access-Control-Allow-Origin` not `*`
   - `Sec-Fetch-Site: same-origin|none` required on stateful routes
   - `Origin:` header matches expected allow-list (CSRF defense even
     on loopback — browser-to-localhost simple-request abuse vector).
3. **NO DNS rebinding** — `Host:` header validation tested.
4. **POSIX permissions on `~/.codex/auth.json`** mode `0600` + owner
   = `$USER`. Prevents same-user-no-su localhost-attacker read.
   (Narrowed platform model — env-secrecy claim was overclaimed;
   revoked cross-user defense.)
5. **CSRF-token required on every stateful route** (POST/PUT/DELETE);
   test asserts unauthenticated cross-origin POST is REJECTED with
   403.

### §B.2 — Threat-velocity override (re-open triggers)

R1 IDA P1 fold: §B MUST re-open BEYOND friction-count. Any of these →
R-031 fires regardless of soak progress:

- CVE published against `loopback` MCP transports
- Bearer token leak observed in audit log
- 5-repo soak surfaces ANY replay attempt
- Owner-friction count from 5-repo soak reaches ≥ 10

Re-open materializes as a new PLAN (likely PLAN-100+) consuming §A as
the implementation baseline.

### §B.3 — Firing path (TDE P0 fold + R2 Codex iter-2 P1 fold)

R1 TDE P0 fold caught: §B "friction count" is a paper metric without
a firing path. R2 Codex iter-2 P1 fold elevated this to an acceptance
gate. PLAN-090 Wave C therefore ships:

- `mcp_bearer_friction_observed` audit action registered in
  `_KNOWN_ACTIONS` (verify via grep).
- `_lib/mcp_bearer_friction.py` callsite-emitter (~40 LoC) consulted
  at MCP auth-failure path + replay-attempt detection.
- `.claude/scripts/audit-query.py` extended with `mcp-friction-count`
  sub-command for trigger aggregation (24h + 7d + 30d windows;
  separate `replay_attempt_count` row for re-open detection).
- `.claude/hooks/tests/test_mcp_bearer_friction_emit.py` (~5 tests)
  asserting real bearer-friction conditions increment the counter.

Without these, ADR-122 §B is unsigned advisory. With them, the trigger
condition is mechanically observable.

### §B.4 — Decision artifacts

- `chosen_scenario: B` in this ADR's frontmatter.
- `friction_count_at_decision_date: 0`
- `decision_date: 2026-05-13`
- `adopters_installed: 0`
- Sentinel: `.claude/plans/PLAN-090/architect/round-1/approved.md`
  (with detached `.asc`) covers ADR-122 acceptance per the canonical-
  edit ceremony chain of custody.

## §C — Audit event surface

| Action | ATLAS | When |
|---|---|---|
| `mcp_bearer_friction_observed` | (none — telemetry; consider `AML.T0048` if downgrade attempt detected) | every MCP auth-failure / nonce-repeat / 403 |

Field allowlist (Sec MF-3): `action`, `ts`, `session_id`, `project`,
`mcp_server`, `failure_reason`, `replay_suspected`, `event_schema`,
`tokens_*`, `hmac`, `hmac_error`.

## §D — Cost (under §B)

- Implementation: ~40 LoC `_lib/mcp_bearer_friction.py` + ~20 LoC
  audit_emit additions + ~30 LoC audit-query sub-command + ~5 tests
  = ~95 LoC net-new.
- Test suite: ~5 tests at `test_mcp_bearer_friction_emit.py`.
- Sub-agent dispatches: 0 (CEO solo).
- Owner-physical: 0 additional GPG (single sentinel covers all
  PLAN-090 canonical edits).

## §E — Sunset

This ADR is automatically superseded when:

- A re-open trigger fires AND a new PLAN lands DPoP implementation
  consuming §A as the baseline. The new ADR cites this ADR as
  `supersedes: ADR-122`.
- ADR-115 v2.0 trigger fires (soak count ≥ 10) and v2.0 plan-housing
  lands. R-031 graduates to in-scope at that point.
