# SPEC/v1/mcp-server.schema.md — MCP Server Contract

**Version:** 1.0.0-rc.1 (PLAN-013 Phase A.2, Sprint 13)
**Status:** PROPOSED (additive; extends ADR-042 MCP Server Contract)
**Authoritative source:** `.claude/scripts/mcp-server/server.py`
and companion modules (`auth.py`, `rate_limit.py`, `cost.py`,
`handlers/*.py`). SPEC is the grep-able field + behavior inventory
the implementation is tested against.

## 0. Purpose

ADR-042 §Auth + §Cost establish the governance contract every MCP
server implementation MUST obey. This document is the normative
companion: type constraints, closed-enum reason codes, handler
request/response shapes, and the cross-boundary contracts
(governance passthrough, cost inheritance, CEO_SOTA_DISABLE parity,
audit event mapping).

Companion documents:

- `adapters.schema.md` — hook adapter ABI (contract this re-uses
  for envelope types).
- `audit-log.schema.md` — event stream v2 — the 4 MCP events
  (`mcp_server_started`, `mcp_server_disabled_by_kill_switch`,
  `mcp_handler_invoked`, `mcp_handler_denied`) are registered here.
- `live-adapters-policy.schema.md` — `LiveCallPolicy` (inherited by
  `spawn_agent` handler per ADR-042 §Cost).
- ADR-042 — MCP Server Contract (authoritative §Auth + §Cost
  decisions).

---

## 1. Version + Status

| Field | Value |
|---|---|
| Schema version | 1.0.0-rc.1 |
| Schema status | PROPOSED |
| Protocol version | `2024-11-05` (Model Context Protocol spec) |
| Server version | `1.0.0-rc.1` (semver of `.claude/scripts/mcp-server/`) |
| Authoritative source | `.claude/scripts/mcp-server/server.py` |

SemVer-shaped. Within v1 all handler additions are MINOR-bump
additive only. Handler removal or param-shape breakage is MAJOR
bump (forbidden in v1 — Sprint 15+ would plan a v2 migration).

---

## 2. Transport

Two transports, selected via `CEO_MCP_TRANSPORT` env var (default
`http`).

### 2.1 HTTP transport

- **Path:** POST `/rpc` (no other paths routed).
- **Host:** `CEO_MCP_HOST` env var; default `127.0.0.1`.
  - `0.0.0.0` is REJECTED unless `CEO_MCP_ALLOW_PUBLIC=1` is
    explicitly set. Server silently rewrites to `127.0.0.1`
    otherwise.
- **Port:** `CEO_MCP_PORT` env var; default `9000`; validated
  `1 <= port <= 65535`; malformed → default.
- **Auth header:** `Authorization: Bearer <token>`.
- **Timestamp header:** `MCP-Timestamp-Ms` (integer milliseconds
  since epoch, UTC).
- **Session header:** `MCP-Session-Id` (UUID recommended; server
  generates one if absent).
- **Request body cap:** 1 MiB (slow-loris / DoS protection).
- **Response headers:**
  - `Content-Type: application/json; charset=utf-8`
  - `Cache-Control: no-store`
  - `X-Content-Type-Options: nosniff`
  - `Retry-After: <seconds>` on 429 rate-limit denials.
- **Status code mapping:**
  - 200 — success.
  - 400 — parse error / invalid request / bad Content-Length.
  - 401 — auth denial (any reason in {`auth_token_malformed`,
    `auth_hmac_invalid`, `timestamp_skew`}).
  - 403 — ACL or CORS denial.
  - 404 — path other than `/rpc`.
  - 429 — rate limit with `Retry-After` header.
  - 500 — internal error (handler exception caught).

### 2.2 stdio transport

- **Input:** newline-delimited JSON-RPC 2.0 envelopes from stdin.
- **Output:** newline-delimited JSON-RPC 2.0 responses to stdout.
- **Auth:** `params.authorization` (bearer token — no `Bearer `
  prefix) + `params.timestamp_ms` + optional `params.session_id`.
  These three fields are STRIPPED from `params` before the handler
  sees them (ADR-042 §Auth.6 hygiene).

### 2.3 CEO_SOTA_DISABLE parity

Before any transport setup, the server checks `CEO_SOTA_DISABLE=1`.
On match:

1. Emit `mcp_server_disabled_by_kill_switch` audit event.
2. Write `[mcp-server] CEO_SOTA_DISABLE=1 — server disabled. Exiting 0.`
   to stderr.
3. Return exit code 0 without binding a port or opening stdio pipes.

This mirrors ADR-040 §6 activation gate — the kill-switch is a
global, single-flip safety net.

### 2.4 Startup observability

After kill-switch check passes, the server emits
`mcp_server_started` with fields:

| Field | Value |
|---|---|
| `transport` | `"http"` \| `"stdio"` |
| `host` | loopback-or-explicit (empty string for stdio) |
| `port` | integer (0 for stdio) |
| `version` | `"1.0.0-rc.1"` (server version) |
| `handlers_count` | `7` |

---

## 3. Auth

Normative decisions come from ADR-042 §Auth.1-§Auth.6. The schema
below is the grep-able type inventory.

### 3.1 Token format

```
v1.<client_id_hex16>.<nonce_hex16>.<hmac_hex32>
```

Regex: `^v1\.([0-9a-f]{16})\.([0-9a-f]{16})\.([0-9a-f]{32})$`.

- `client_id_hex16` — 16 lowercase hex chars, registered in
  `.claude/settings.json` key `mcp_client_registry`.
- `nonce_hex16` — 128-bit randomness, 16 lowercase hex chars,
  rotated per-request (not per-session).
- `hmac_hex32` — truncated 32 hex chars of
  `HMAC-SHA256(secret, client_id + nonce + timestamp_ms)`.

### 3.2 HMAC compute

```python
body = (client_id + nonce + str(timestamp_ms)).encode("ascii")
hmac_hex = hmac.new(secret, body, hashlib.sha256).hexdigest()[:32]
```

- Use `hmac.compare_digest` for verification (constant-time).
- `timestamp_ms` MUST be integer milliseconds since epoch — no
  floats, no commas, no padding.
- Denial message is generic (`auth_hmac_invalid`); no oracle
  distinguishing wrong-secret from wrong-client_id from malformed-MAC.

### 3.3 Shared secret storage

File: `$CLAUDE_PROJECT_DIR/state/mcp_client_secrets/<client_id>.key`

- Permissions: 0600 exactly (any other perms → fail-closed).
- Size: [16, 4096] bytes (reject empty, reject oversized).
- Must be a regular file; symlinks are rejected.
- Path-traversal defense: `client_id` is regex-validated before
  path construction; `resolved_target.relative_to(resolved_base)`
  enforces no `..` escape.

### 3.4 Client registry schema

In `.claude/settings.json`:

```yaml
mcp_client_registry:
  <client_id_hex16>:
    handlers:                 # REQUIRED, non-empty list of allowlisted methods
      - list_skills
      - get_skill
      - ...
    cors_origins:             # OPTIONAL, HTTP transport only; exact-match list
      - "https://cursor.example/"
    description:              # OPTIONAL, documentation only
      "Cursor IDE plugin"
```

Empty or missing `handlers` = refuse all requests.
Wildcard (`"*"`) in `handlers` = refuse all (no wildcard accepted).
`cors_origins` missing or empty = no HTTP origins allowed.
Wildcard in `cors_origins` = rejected.

### 3.5 Rate-limit overrides schema

```yaml
mcp_rate_limits:
  <client_id_hex16>:
    readonly:      {rpm: 60, burst: 10}
    audit_read:    {rpm: 30, burst: 5}
    spawn:         {rpm: 6, burst: 2}
```

Defaults (used when override absent or malformed):

| Handler class | Handlers | Default rpm | Default burst |
|---|---|---|---|
| `readonly` | `list_skills`, `get_skill`, `list_agents`, `list_pitfalls`, `server.capabilities` | 60 | 10 |
| `audit_read` | `get_audit_log` | 30 | 5 |
| `spawn` | `spawn_agent` | 6 | 2 |

Negative or zero values fall back to defaults. No cross-class
aggregation — each class has an independent bucket.

### 3.6 Timestamp skew window

`|timestamp_ms - now_ms| <= 60_000` (±60 seconds).

Requests outside window → `timestamp_skew` deny (ADR-042 §Auth.1).

### 3.7 Audit hygiene

Token value MUST NEVER appear in:

- Any audit event field.
- Any log line (stderr/stdout outside successful JSON responses).
- Any exception message propagated to the JSON-RPC error envelope.
- Any synthesized adapter field (`tool_name`, `session_id`, etc.).

Client_id is passed through `hash_client_id()` (SHA-256 prefix 16
hex chars) before appearing in audit events.

---

## 4. Error model

### 4.1 JSON-RPC 2.0 core codes

| Code | Name | Scenario |
|---|---|---|
| `-32700` | Parse error | Invalid JSON body. |
| `-32600` | Invalid Request | Missing `jsonrpc`, `method`, or wrong types. |
| `-32601` | Method not found | `method` is not a registered handler. |
| `-32602` | Invalid params | Malformed params dict / list rejected. |
| `-32603` | Internal error | Handler exception caught. |

### 4.2 Application codes (reserved -32000 to -32099)

| Code | Reason | Scenario |
|---|---|---|
| `-32001` | Auth | `auth_token_malformed` / `auth_hmac_invalid` |
| `-32002` | ACL | `acl_missing_handler` |
| `-32003` | Rate limit | `rate_limit` |
| `-32004` | CORS | `cors_default_deny` |
| `-32005` | Timestamp | `timestamp_skew` |
| `-32006` | Budget | (reserved; budget denies return as `result`, not error) |

### 4.3 Closed enum of deny reasons

All reasons that may appear in `mcp_handler_denied.reason`:

1. `auth_token_malformed`
2. `auth_hmac_invalid`
3. `timestamp_skew`
4. `acl_missing_handler`
5. `cors_default_deny`
6. `rate_limit`
7. `governance_block` — spawn_agent governance denied
8. `budget_hard_stop_per_spawn` — spawn_agent cost ceiling per-spawn
9. `budget_hard_stop_per_plan_5min` — spawn_agent cost ceiling per-plan
10. `debate_max_rounds` — reserved, surfaces via audit when debate
    invoked indirectly
11. `breaker_open` — circuit breaker open (ADR-042 §Cost.3, live
    adapter layer when wired Sprint 14+)
12. `plan_id_unknown` — `plan_id` param refers to a plan not found in
    `.claude/plans/`
13. `internal_error` — handler exception path
14. `skill_not_found` / `skill_too_large` / `invalid_params` —
    handler-specific JSON-RPC error messages

Consumer tests assert EVERY reason the server emits is in this set.
New reasons require a SPEC MINOR bump AND an ADR-042 amendment.

### 4.4 Error envelope shape

```json
{
  "jsonrpc": "2.0",
  "id": <request_id>,
  "error": {
    "code": <int>,
    "message": "<reason string>"
  }
}
```

- `error.message` is the closed-enum reason string (no free-text
  exception text per §3.7 hygiene).
- `data` field omitted in v1 (reserved for future MINOR extension).

---

## 5. Rate limit

Token-bucket per `(client_id, handler_class)`. Thread-safe via
`threading.Lock`. In-memory per-process — no Redis, no memcached.

### 5.1 Handler class mapping

| Handler | Class |
|---|---|
| `list_skills` | `readonly` |
| `get_skill` | `readonly` |
| `list_agents` | `readonly` |
| `list_pitfalls` | `readonly` |
| `server.capabilities` | `readonly` |
| `get_audit_log` | `audit_read` |
| `spawn_agent` | `spawn` |

### 5.2 Token bucket semantics

- Capacity == `burst` (initial token count).
- Refill rate == `rpm / 60` tokens per second (continuous, not
  discrete tick).
- `try_consume(cost=1)` returns `(bool allowed, int retry_after_ms)`.
- Retry-After computation: on deny,
  `retry_after_ms = ceil((cost - tokens) / rate_per_s * 1000)`
  (minimum 1 ms when non-zero).

HTTP transport maps `retry_after_ms` → `Retry-After: <seconds>`
(ceiling division — minimum 1 second).

### 5.3 Bucket scope

One bucket per (client_id, handler_class) pair, memoized for the
process lifetime. Server restart clears state (intentional — the
framework does not require rate-limit durability; reboot is
recovery).

---

## 6. Revocation

Client revocation procedure:

1. Remove `<client_id>` from `.claude/settings.json` key
   `mcp_client_registry`.
2. Optionally delete
   `state/mcp_client_secrets/<client_id>.key` (belt-and-braces).
3. Optionally restart the server (not strictly required — the
   registry is re-read per request).

Effect: next request from that client returns
`auth_hmac_invalid` (registry lookup fails → generic denial, no
oracle). Every subsequent request emits `mcp_handler_denied` with
`reason=auth_hmac_invalid`.

Cache considerations: `load_client_registry()` does NOT cache — it
re-reads `settings.json` per request. This is fine at the handler
scale (microseconds) and ensures revocation takes effect
immediately without a restart.

---

## 7. Deprecation

90-day sunset policy for any handler removal or param-shape change.

### 7.1 Deprecation workflow

1. PR that marks a handler deprecated:
   - Adds `DEPRECATED_YYYY_MM_DD: str` module-level constant to the
     handler module.
   - Bumps SPEC MINOR — registers the deprecation in §9 History.
   - Amends ADR-042 Transition Log appendix with the deprecation
     date.
2. Server continues serving the handler for 90 calendar days.
3. Removal PR deletes the module + unregisters from `HANDLERS`
   dict in `server.py`.
4. SPEC MAJOR bump IFF the deprecated handler was load-bearing for
   existing adopters; otherwise MINOR bump.

### 7.2 Sunset audit event

On server startup, if any handler is within 30 days of its removal
date, server emits `mcp_handler_deprecated_warning` (reserved; not
yet implemented — Sprint 14+).

---

## 8. Versioning

### 8.1 Server version field

`SERVER_VERSION` constant in `server.py` and
`server_capabilities.py`. Reported via `server.capabilities` result
in `server_version` field. Tracks SemVer of the MCP server
implementation — independent from framework `VERSION`
(`1.4.0-rc.1`) and MCP protocol version (`2024-11-05`).

### 8.2 Protocol version field

`PROTOCOL_VERSION` constant in `server_capabilities.py`
(`"2024-11-05"`). Reported via `server.capabilities` result in
`protocol_version` field. Tracks the Model Context Protocol spec
release this server implements.

### 8.3 Additive-only handler contracts

Within v1, every handler param / result shape change is additive:

- **New optional param** — OK (clients omitting it get prior
  behavior).
- **New result field** — OK (clients tolerate unknown fields per
  JSON-RPC 2.0 convention).
- **Removing a param** — MAJOR bump (forbidden in v1).
- **Removing a result field** — MAJOR bump (forbidden in v1).
- **Changing param type** — MAJOR bump (forbidden in v1).

---

## 9. History

### 9.1 Handler inventory (7 handlers at v1.0.0-rc.1)

| Handler | Class | Params | Result |
|---|---|---|---|
| `list_skills` | readonly | `{}` | `{skills: [{tier, slug, description}], total}` |
| `get_skill` | readonly | `{tier, slug, domain?}` | `{tier, slug, domain?, description, content}` |
| `list_agents` | readonly | `{}` | `{archetypes: [{tier, name, skill_primary, skill_secondary}], total}` |
| `list_pitfalls` | readonly | `{domain?}` | `{pitfalls: [...], total, domain?}` |
| `get_audit_log` | audit_read | `{limit?, action_filter?, since?}` | `{events: [...], truncated, total_returned}` |
| `spawn_agent` | spawn | `{agent_name?, description, prompt, plan_id?}` | `{allowed, block_reason?, result?}` |
| `server.capabilities` | readonly | `{}` | `{protocol_version, server_version, handlers, feature_flags}` |

### 9.2 Governance passthrough contract (spawn_agent CRITICAL)

Per PLAN-013 debate Round 1 consensus §C2 CRITICAL (3 of 5 agents
flagged): external MCP `spawn_agent` invocations MUST re-enter the
EXACT SAME decision function that Claude-native PreToolUse hooks
invoke.

#### Contract

- Handler imports `check_agent_spawn` (top-level hook module) —
  literal `import check_agent_spawn` grep-able in
  `.claude/scripts/mcp-server/handlers/spawn_agent.py`.
- Handler calls `check_agent_spawn.decide(description=..., prompt=...,
  names_regex=team.load_names(project_dir))` — the SAME invocation
  shape as `check_agent_spawn.main()`.
- On deny (`decision.allow == False`), handler returns
  `{"allowed": False, "block_reason": decision.reason, "result": None}`
  — the `block_reason` string is byte-identical to what
  Claude-native Agent tool invocations see.

#### Byte-identity test fixture (Wave 2 D responsibility)

`tests/integration/test_mcp_governance_parity.py` MUST assert:

```python
native_decision = check_agent_spawn.decide(
    description="Staff Backend Engineer: implement foo",
    prompt="Do the thing.",
    names_regex=team.load_names(FIXTURE_DIR),
)
mcp_result = spawn_agent_handler.handle(
    {"description": "...", "prompt": "Do the thing."},
    ctx={"project_dir": FIXTURE_DIR, ...},
)
assert mcp_result["allowed"] == native_decision.allow
assert mcp_result["block_reason"] == native_decision.reason
```

Any divergence fails CI.

### 9.3 Budget passthrough contract (spawn_agent)

Per ADR-042 §Cost.1 and PLAN-013 consensus §S13:

- After governance passes, handler consults `LiveCallPolicy` via
  `cost.check_spawn_budget(estimated_usd, spawn_tracker, plan_tracker)`.
- On budget deny returns
  `{"allowed": False, "block_reason": "BUDGET: <reason>"}` with
  `reason` in `{budget_hard_stop_per_spawn,
  budget_hard_stop_per_plan_5min}`.
- Trackers are NOT mutated by the handler (it's a pre-flight check).
  Real charge accrual is Sprint 14+ when live adapter dispatch is
  wired.

---

## 10. Backward-compat

Within SPEC v1:

- Adding a new handler is always safe (MINOR bump).
- Adding a new optional param is safe (MINOR bump).
- Adding a new result field is safe (MINOR bump).
- Adding a new closed-enum deny reason is MINOR bump AND
  requires ADR-042 amendment.
- Removing ANY field / param / handler is MAJOR bump AND
  requires SPEC v2 with a migration ADR. Forbidden within v1.

Clients MUST tolerate unknown fields in responses (forward-compat
per JSON-RPC 2.0 spec). Server MUST tolerate unknown fields in
params (additive compat).

---

## 11. Deprecation window

Minimum 90 calendar days between a handler being marked deprecated
(see §7) and its removal. Rationale: MCP clients (Cursor plugins,
IDE integrations, external tooling) may have independent release
cadences — 90 days covers one quarterly release cycle.

### 11.1 Deprecation announcement

Announcement vectors:
1. `DEPRECATED_YYYY_MM_DD` module constant in the handler module.
2. ADR-042 Transition Log appendix (mandatory per ADR-041).
3. SPEC §9 History row with deprecation date.
4. Startup `mcp_handler_deprecated_warning` audit event when a
   handler is within 30 days of removal (reserved for Sprint 14+).

### 11.2 Removal commit

Removal requires:
- ADR-042 amendment recording the removal date + justification.
- SPEC MINOR or MAJOR bump (see §7.1 for choice criterion).
- `HANDLERS` dict entry removed in `server.py`.
- Handler module deleted from `handlers/` subtree.
- Byte-identity test fixture for that handler deleted from
  `tests/integration/`.

---

## 12. Referenced by

- ADR-042 — MCP Server Contract (authoritative §Auth + §Cost
  decisions; this SPEC is the grep-able companion).
- ADR-040 — `LiveCallPolicy` (inherited by `spawn_agent`).
- ADR-041 — Transition Log Convention (ADR-042 records its
  transitions via this format).
- ADR-043 — SOC2 Audit Trail Mapping (MCP events are input to the
  control map).
- ADR-044 — Formal Verification Pilot (MCP handler contract is a
  candidate target for conformance-harness mapping).
- `SPEC/v1/adapters.schema.md` — ABI that `_lib/adapters/claude.py`
  obeys; MCP consumes its `NormalizedEvent` type indirectly via
  `check_agent_spawn.decide()`.
- `SPEC/v1/audit-log.schema.md` — event stream v2 (registers the 4
  MCP events).
- `SPEC/v1/live-adapters-policy.schema.md` — `LiveCallPolicy`
  contract (inherited by `spawn_agent` cost check).
- `docs/mcp-cursor-setup.md` — adopter-facing setup guide
  (Phase A.7 deliverable).

## 13. Changelog

- **1.0.0-rc.1** (2026-04-15, PLAN-013 Phase A.2): initial
  publication. 7 handlers, 14 deny reasons, 2 transports, 4 audit
  events. ADR-042 §Auth + §Cost locked in PLAN-013 Phase 0;
  implementation landed Phase A.1; this SPEC is the Phase A.2
  companion.
