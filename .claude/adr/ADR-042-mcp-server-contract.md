# ADR-042: MCP Server Contract

**Status:** ACCEPTED (flipped PLAN-025 Batch C — live per PLAN-013 Phase A (MCP server stdlib shipped))
**Date:** 2026-04-15
**Sprint:** 13 (PLAN-013 Phase 0 reservation + Phase A.3 full decision)
**Related:** ADR-002 (hooks package layout — `.claude/scripts/` discipline
discipline mirrors here), ADR-028 (multi-LLM canonical envelope — MCP
handler return shapes reuse it), ADR-035 (OTEL export — double-redact
boundary precedent applies to audit on handler invocation), ADR-040
(Live Adapter Activation Contract — `LiveCallPolicy` cost-cap inherited
by `spawn_agent` handler), ADR-041 (Transition Log Convention — this
ADR adopts the Transition Log appendix on activation), ADR-043 (SOC2
Audit Trail Mapping — this ADR's audit events are the source), ADR-044
(Formal Verification Pilot — MCP handler contract is a candidate
target for conformance-harness mapping).

## Context

PLAN-013 Phase A introduces a **Model Context Protocol (MCP) server**
enabling external clients (Cursor, IDE plugins, orchestration scripts)
to consume the framework's governance surface — skills, agents, audit
log, pitfalls, and **delegated spawns** — via a stable JSON-RPC contract
over stdio or HTTP. This is the framework's first inbound
public-boundary interface: external processes call in, the server
executes, audit events fire.

Three CRITICAL concerns were raised in PLAN-013 debate Round 1 and must
be locked **before Phase A kickoff** (Phase 0-blocker):

1. **Governance passthrough** (Staff Backend CRITICAL-1, VP Engineering
   HIGH-5, Security CRITICAL-1 — 3/5 agents). `PreToolUse` hooks only
   fire on Claude's own tool calls. External MCP clients invoking
   `spawn_agent` would bypass `check_agent_spawn.py` entirely unless the
   handler **explicitly** re-invokes the hook's decision function with
   an identical `PreToolUse` payload. Without this, Sprint 15 adoption
   ships a production-unsafe open door.
2. **Auth model** (Security CRITICAL-1, single-agent accepted per
   consensus §S1). A network-reachable server without declared auth
   ships an open relay. Even in an internal network, credentials +
   spawn authority + cost-cap bypass is a blast-radius L3 attack
   surface.
3. **Cost-cap inheritance** (Staff Backend CRITICAL-7 supplementary,
   accepted per consensus §S13). MCP `spawn_agent` invocations must
   inherit ADR-040 `LiveCallPolicy` ceilings ($0.50/spawn + $2.00/5min
   per plan) at the **adapter layer**, not as a handler-level opt-in.
   Otherwise external clients bypass budget governance entirely.

This stub reserves the ADR number and locks the §Auth + §Cost scope
as Phase 0-blockers per PLAN-013 items 0.1 + 0.5. The remaining
sections (Options considered, Decision, Consequences, Blast radius,
Transition Log) are completed in **Phase A.3** after the A.0
stdlib-vs-mcp-sdk spike (5 days) surfaces evidence for the tool choice.

## Decision drivers

- **Governance integrity** (PLAN-013 consensus §C2 CRITICAL): external
  invocations MUST re-enter `check_agent_spawn.decide()` with
  byte-identical `PreToolUse` payload shape. Hook block reasons on
  external call MUST equal hook block reasons on Claude-native call
  (byte-identity test fixture).
- **Default-deny posture** (PLAN-013 consensus §S1 Security): every
  handler deny path emits `mcp_handler_denied` audit event with
  `reason` + `handler` + `client_id` (hashed). Empty ACL = refuse all.
- **Cost ceiling inheritance** (PLAN-013 consensus §S13): `spawn_agent`
  handler calls through the same `LiveCallPolicy` that Claude-native
  spawns use — no parallel budget surface.
- **Auditability** (ADR-035 precedent): every handler invocation emits
  at least one audit event; zero silent handler activity. Double
  redaction applied (handler-parse boundary + `_lib/audit_emit.py`
  export boundary).
- **Stdlib-only default** (ADR-002): MCP transport layer prefers
  hand-rolled JSON-RPC 2.0 over `urllib` / `socketserver` unless the
  A.0 spike surfaces a blocker.
- **Protocol capability discovery** (PLAN-013 consensus §S4): 7th
  handler `server.capabilities` declares protocol version + handler
  list + feature flags, preventing client-side probing fragility.

## §Auth (Phase 0 — locked)

**Decision (auth): HMAC bearer + default-deny + per-handler ACL +
rate-limit + CORS default-deny + audit on denial.** Normative subset
below; full wire format in `SPEC/v1/mcp-server.schema.md` (Phase A.2).

### §Auth.1 Token model

- **Scheme:** HMAC-SHA256 bearer token in `Authorization: Bearer <t>`
  header (HTTP transport) or `authorization` JSON-RPC request param
  (stdio transport). Token format:
  `v1.<client_id_hex16>.<nonce_hex16>.<hmac_hex32>` where:
  - `client_id_hex16` identifies the caller (opaque 16-hex-char
    identifier; registered in `.claude/settings.json` key
    `mcp_client_registry`).
  - `nonce_hex16` is 128-bit random, rotated per-session by client.
  - `hmac_hex32` is `HMAC-SHA256(secret, client_id_hex16 + nonce_hex16 +
    request_timestamp_unix_ms)` truncated to 32 hex chars.
- **Shared secret** per client stored in
  `$CLAUDE_PROJECT_DIR/state/mcp_client_secrets/<client_id>.key`
  (600 perms, not in git; `_lib/state_store` managed). Rotation: 90-day
  hard max mirroring ADR-040 credential lifecycle.
- **Timestamp skew window:** ±60 seconds. Requests outside window
  deny with `mcp_handler_denied(reason=timestamp_skew)`.

### §Auth.2 Default-deny ACL

Every handler requires an **explicit ACL entry** in
`.claude/settings.json` key `mcp_client_registry.<client_id>.handlers`
= allowlist (array of handler names). Empty or missing allowlist =
refuse all handlers for that client. Supported handler names:

- `list_skills`, `get_skill`, `list_agents`, `list_pitfalls`,
  `get_audit_log`, `server.capabilities` (read-only — default-ok to
  grant broadly).
- `spawn_agent` (write + cost — requires explicit opt-in per client;
  inherits `LiveCallPolicy` per §Cost below).

No wildcard ACLs permitted; every handler listed by name. Violation
(wildcard, missing, empty) → deny with
`mcp_handler_denied(reason=acl_missing_handler)`.

### §Auth.3 Rate limit (token bucket per client)

Per-client token bucket, default values in
`.claude/settings.json` key `mcp_rate_limits.<client_id>`:

| Handler class | Rate (req/min) | Burst |
|---|---|---|
| Read-only (skills, agents, pitfalls, capabilities) | 60 | 10 |
| Audit-log read | 30 | 5 |
| `spawn_agent` | 6 | 2 |

Exceeding bucket → deny with `mcp_handler_denied(reason=rate_limit)`
+ `Retry-After: <seconds>` header (HTTP transport). Implementation:
stdlib-only fixed-window-with-refill in
`.claude/scripts/mcp-server/_rate_limit.py` (Phase A.1).

### §Auth.4 CORS default-deny

HTTP transport only (stdio transport ignores). Default
`Access-Control-Allow-Origin: (none)`; opt-in explicit per client
in `.claude/settings.json` key `mcp_client_registry.<client_id>.cors_origins`
= array of exact origins (no wildcards). Preflight `OPTIONS` without
matching `Origin` → 403 + `mcp_handler_denied(reason=cors_default_deny)`.

### §Auth.5 Audit on denial

Every deny path emits `mcp_handler_denied` with required fields
(schema in `SPEC/v1/audit-log.schema.md` amendment, Phase A.6):

```
{
  "ts": <iso8601>,
  "action": "mcp_handler_denied",
  "reason": "acl_missing_handler | rate_limit | timestamp_skew | cors_default_deny | auth_hmac_invalid | auth_token_malformed",
  "handler": "<handler_name>",
  "client_id": "<hashed16>",
  "transport": "http | stdio",
  "session_id": "<uuid>"
}
```

Redaction applied per §Audit hygiene below: token value NEVER in any
field; only `client_id` (already non-sensitive hex16).

### §Auth.6 Audit hygiene

- Token MUST NOT appear in any audit field, span attribute, log line,
  stack trace, or error message surfaced to client.
- Handler-parse boundary strips `Authorization` header before any
  dict reaches downstream callers (`_lib/audit_emit.py` then applies
  its own redact pass per ADR-035).
- Failed HMAC comparison uses `hmac.compare_digest` (constant-time);
  denial message is generic (`auth_hmac_invalid`) — no distinguishing
  between "wrong secret" vs "wrong client_id" vs "malformed".

## §Cost (Phase 0 — locked)

**Decision (cost): inherits ADR-040 `LiveCallPolicy` verbatim; no
parallel budget surface at MCP layer.**

### §Cost.1 `spawn_agent` inheritance

The `spawn_agent` handler path invokes
`_lib/adapters/live/_policy.LiveCallPolicy.enforce()` BEFORE emitting
`live_adapter_call_started`. All three ceilings apply:

| Knob | Source | Behaviour on breach |
|---|---|---|
| `MAX_SPEND_USD_PER_SPAWN = 0.50` | ADR-040 §3 | Deny with `mcp_handler_denied(reason=budget_hard_stop_per_spawn)` + `budget_hard_stop` event |
| `MAX_SPEND_USD_PER_PLAN_5MIN = 2.00` | ADR-040 §3 | Deny with `mcp_handler_denied(reason=budget_hard_stop_per_plan_5min)` + `budget_hard_stop` event |
| `MAX_ROUNDS (debate) = 5` | ADR-040 §3 | Deny with `mcp_handler_denied(reason=debate_max_rounds)` + `budget_hard_stop` event |

`plan_id` derivation for rate-window accounting: MCP requests carry
optional `plan_id` param; when absent, server derives from audit tail
per ADR-034 scratchpad M2 precedent (plan_id from most recent
`audit_log` entry of same `session_id`). No client-supplied `plan_id`
spoofing: server validates it exists in `.claude/plans/` or rejects
with `mcp_handler_denied(reason=plan_id_unknown)`.

### §Cost.2 Non-`spawn_agent` handlers

Read-only handlers (`list_skills`, `get_skill`, `list_agents`,
`list_pitfalls`, `get_audit_log`, `server.capabilities`) do NOT invoke
`LiveCallPolicy`. Their cost is bounded by §Auth.3 rate limits alone.

### §Cost.3 Circuit breaker independence

MCP server runs the SAME `_lib/adapters/live/_breaker.py` instance
used by Claude-native live paths. If the breaker is open per ADR-040
§2, MCP `spawn_agent` fails-fast in <50ms with
`mcp_handler_denied(reason=breaker_open)` — zero retry at MCP layer.

### §Cost.4 `CEO_SOTA_DISABLE` parity

`CEO_SOTA_DISABLE=1` short-circuits the MCP server entry point
(`.claude/scripts/mcp-server/server.py` main) before binding to port
or opening stdio pipe. Log `mcp_server_disabled_by_kill_switch` on
startup; exit 0. Mirrors ADR-040 §6 activation gate.

## Options considered

Three tool-choice options were evaluated. Options A and B are the
materially competing alternatives (hand-rolled stdlib vs vendored
SDK); Option C is the status-quo deferral. Evidence for A and B is
drawn from the Phase A.0 spike output
(`docs/research/mcp-sdk-vs-stdlib.md`, 619 LOC, completed 2026-04-15)
which resolved PLAN-013 Open question Q1. Evidence for C rejection is
drawn from PLAN-013 debate Round 1 consensus §C1 (5/5 agents flagged
D3 as under-specified Sprint-15 blocker).

### Option A — Hand-rolled stdlib JSON-RPC 2.0 over `http.server` + `urllib`

**Description.** Implement the MCP server transport, dispatcher, auth,
rate limit, and 7 handlers as a set of Python modules under
`.claude/scripts/mcp-server/`, using only the standard library
(`http.server`, `socketserver`, `json`, `hmac`, `hashlib`, `secrets`,
`urllib.parse`, `threading`). JSON-RPC 2.0 framing is parsed explicitly
per spec MUST rules; MCP protocol-level conventions (capability
announcement, method naming, error code ranges) are implemented to
match spec revision **2025-11-25** (pinned at Phase A kickoff). No
third-party PyPI packages added to the runtime closure.

**Pros:**
1. **Zero transitive dep surface** — adheres to ADR-002 stdlib-only
   discipline; framework runtime dep count remains 0, matching
   `.claude/hooks/_lib/` baseline (21 modules, all stdlib per
   `docs/research/mcp-sdk-vs-stdlib.md` §4.4).
2. **CVE blast-radius bounded to this repo** — per spike §1.3, zero
   CVEs in 2025-Q3→2026-Q2 window against stdlib `http.server`/`json`/
   `urllib` for JSON-RPC framing; any future CVE is patchable in one
   repo without downstream pin-chasing.
3. **Full wire-byte visibility** — we control every byte sent and
   received, which makes the byte-identity governance passthrough test
   (debate §C2 CRITICAL) trivially implementable: the handler's
   `PreToolUse` payload shape is constructed explicitly in our code.
4. **Spec-version pin is deliberate, not inherited** — upgrading to a
   new MCP spec revision requires an explicit ADR-044 amendment plus
   conformance test regen (per spike §3.4), preventing silent breakage
   from an SDK auto-upgrade.
5. **Secure-by-default enforceable from line 1** — we write the HMAC
   auth, origin check, localhost bind, and rate limit inline, avoiding
   the SDK ecosystem's recurring "default-off" anti-pattern (3 of 15
   CVEs per spike §1.4 are root-caused to this pattern).
6. **Framework discipline signaling** — ceo-orchestration's value
   proposition is "mechanical governance over prompt politeness";
   adopting a heavy SDK for a protocol implementable in ~1000 LOC
   contradicts the discipline we market (spike §Verdict Rationale 3).

**Cons:**
1. **Hand-rolled test burden ~35–45 tests** — 30 JSON-RPC MUST edge
   cases (spike §2.1) + 5–6 governance-passthrough byte-identity tests
   (spike Q-A3.5) + transport/auth. Dense but in-budget (+70 test
   Phase A budget per spike §2.3; `_lib/contract.py` precedent at
   14.1 tests/100 LOC).
2. **Manual MCP spec tracking** — each future spec revision (spike
   §3.1: ~1 per 81 days, 100% breaking-change rate) requires
   deliberate ADR amendment rather than `pip install --upgrade`;
   introduces lag risk if we miss a revision announcement.
3. **No upstream feature free-riding** — if MCP ships resources,
   prompts, or sampling v2 features, we reimplement each rather than
   inheriting SDK support (reimplementation cost captured in §Trigger
   E revisit condition below).
4. **Divergence risk from Anthropic reference server** — behavioural
   equivalence is our acceptance bar, not byte-identity to the official
   SDK; a client that relies on SDK-specific quirks (serialization
   order, whitespace) may need to adapt.

**Risk:** LOW. All four cons are maintenance-burden trade-offs, not
safety-compromising gaps; mitigation is in-budget (test count) or
mechanically enforced (ADR-041 transition log on spec revision).

**Evidence basis:** `docs/research/mcp-sdk-vs-stdlib.md` §1.3 (CVE
asymmetry), §2.1 (35 edge cases), §2.3 (LOC/test projections), §3.1
(spec velocity), §4.4 (baseline 0 deps), §Verdict (stdlib UPHELD on 3 of
4 Decision Drivers).

### Option B — Vendored Python `mcp` SDK (Anthropic official)

**Description.** Add `mcp>=1.23.0` (first version with CVE-2025-66416
DNS rebinding fix) to the framework's runtime dep set. Implement the
7 handlers as `@mcp.tool()` / `@mcp.resource()` decorators or
equivalent; the SDK handles JSON-RPC framing, transport (stdio /
Streamable HTTP / SSE), and capability negotiation. Framework code
delegates to `check_agent_spawn.decide()` for governance passthrough
inside the SDK's tool-handler callback.

**Pros:**
1. **Spec-conformance comes for free** — the SDK tracks MCP spec
   revisions; `pip install --upgrade mcp` moves us to the latest
   spec without hand-rolling framing changes.
2. **Ecosystem feature parity** — resources, prompts, sampling,
   elicitation, tool annotations all ship in the SDK; we inherit
   without implementing (spike §3.2 lists these as shipped in
   v1.23–v1.27).
3. **Broader community test coverage** — the SDK's own 200+ test suite
   exercises edge cases we might miss (per spike §2.4 reference to
   `json-rpc` PyPI).
4. **Potential for reduced LOC** — framework code shrinks by whatever
   the SDK encapsulates (estimated ~200–400 LOC of transport +
   dispatcher we'd otherwise write).

**Cons:**
1. **Supply-chain surface explodes 0 → ~45 packages** — direct deps
   (14) plus transitive walk (one-level: `anyio`, `httpx`, `pydantic`,
   `starlette`, `uvicorn`, `pyjwt[crypto]`, `jsonschema`, etc.) lands
   at ~45 packages per spike §4.3. Each is an independent CVE surface,
   dependency-confusion target, and SBOM-audit line item.
2. **Python SDK CVE history (9-month window): 3 High-severity GHSA
   advisories** — GHSA-9h52-p55h-vw2f (DNS rebinding off-by-default,
   = CVE-2025-66416), GHSA-3qhf-m339-9g5v (FastMCP validation → DoS),
   GHSA-j975-95f5-7wqh (Streamable HTTP transport → DoS), per spike
   §1.2. This is a high absolute count for a 15-month-old project.
3. **Upstream "default-off" security pattern** — 3 of 15 MCP CVEs
   (spike §1.4) share the root cause "DNS rebinding off by default";
   this contradicts PROTOCOL.md §Security's secure-by-default posture
   and ADR-035/ADR-036 empty-default-allowlist precedent.
4. **Heavy inherited CVE history from transitive deps** — `pydantic`
   (CVE-2024-3572 +), `cryptography` (extensive CVE history),
   `starlette` (CVE-2024-47874 +) all enter the framework's threat
   model unavoidably (spike §4.5).
5. **Governance-passthrough becomes fragile** — the SDK's internal
   hook points are not contracted in the MCP spec; a refactor between
   minor versions could invalidate our byte-identity passthrough test.
   Spike §Verdict Rationale 2 calls this out directly.
6. **ADR-002 reversal** — adopting the SDK requires an explicit
   ADR-002 amendment labeling this a permitted exception; the
   amendment itself is a separate decision ceremony not in PLAN-013
   Phase A scope.

**Risk:** HIGH. Con #1 + Con #2 together represent a material erosion
of the framework's secure-by-default value prop and expand the adopter
SBOM-audit surface (relevant for regulated-finance adopter adopter-1
per spike §4.5).

**Evidence basis:** `docs/research/mcp-sdk-vs-stdlib.md` §1.1 (CVE
table), §1.2 (GHSA advisories), §1.4 (defaults-off pattern), §4.1–4.5
(dep walk + supply-chain analysis).

### Option C — Defer MCP server to Sprint 14+

**Description.** Drop Phase A from PLAN-013 entirely; revisit MCP
server scope after Sprint 14 security hardening (PLAN-014) completes.
Sprint 13 still ships Phase B (EN docs), Phase C (threat model +
SOC2), Phase D (formal verification + red-team), Phase E (community
templates + landing + NPM sync).

**Pros:**
1. **Shorter Sprint 13 timeline** — 6.5w → ~4.5w if Phase A removed.
2. **Sprint 14 security work could inform MCP auth model** — threat
   model + SOC2 mapping may surface additional requirements (e.g.
   per-handler audit granularity beyond what §Auth.5 specifies).
3. **Lower Sprint 13 test budget pressure** — +70 tests budget frees
   for other phases.

**Cons:**
1. **Blocks Sprint 15 adopter-1 onboarding** — per PLAN-013 debate
   consensus §C1, IDE integration (Cursor MCP client) is required for
   the adopter validation loop; deferring MCP blocks the primary
   Sprint 15 acceptance criterion.
2. **Sprint 14 sequence invalidated** — PLAN-014 security hardening
   assumes MCP contract exists as a threat-model input; rearranging
   this creates cascading plan-replan overhead.
3. **Owner directive contradiction** — Owner Session 19 directive
   "fecha tudo aqui no máximo possível, estado da arte, antes de
   aplicar em adopter-1" explicitly absorbs original Sprint 14 Phase
   1/2/4/5 into PLAN-013; removing Phase A contradicts the intent of
   that absorption.
4. **No evidence from A.0 spike that deferral is needed** — the spike
   resolved feasibility; there is no blocker to implementation, only
   a choice between A and B.

**Risk:** MEDIUM. Schedule slip is recoverable but violates Owner
directive and cascades into PLAN-014/PLAN-015.

**Evidence basis:** PLAN-013 debate Round 1 consensus §C1; CLAUDE.md
§Current Work Owner directive; `.claude/plans/PLAN-013/progress-log.md`
Session 19 Owner Q9 decision.

### Trade-off matrix (Option A vs Option B)

Scores are 1–5 where **5 is best for ceo-orchestration's governance
posture** (lower supply-chain surface = higher score; shorter CVE
history = higher score; more spec-revision-resilience = higher score).
Blast radius is rated L1–L5 where **L1 is best** (smallest blast
radius); scores for the "Blast radius" row are therefore inverted
(5 − L_rating + 1, so L1→5, L5→1) so that higher remains better.

| Dimension                          | Weight | Stdlib (A) | mcp SDK (B) |
|------------------------------------|--------|-----------:|------------:|
| Transitive dep surface             | HIGH   |         5  |          1  |
| CVE history 6mo                    | HIGH   |         5  |          2  |
| Spec velocity tolerance            | HIGH   |         3  |          3  |
| Hand-rolled test burden            | MEDIUM |         3  |          5  |
| Protocol-revision resilience       | HIGH   |         4  |          3  |
| Adopter installation friction      | MEDIUM |         5  |          2  |
| Blast radius (L-scale inverted)    | HIGH   |      L2→4  |       L4→2  |

**Weighted sum** (HIGH = 3, MEDIUM = 2):

- **Option A (stdlib):** (5·3) + (5·3) + (3·3) + (3·2) + (4·3) + (5·2) + (4·3) = 15 + 15 + 9 + 6 + 12 + 10 + 12 = **79**.
- **Option B (SDK):** (1·3) + (2·3) + (3·3) + (5·2) + (3·3) + (2·2) + (2·3) = 3 + 6 + 9 + 10 + 9 + 4 + 6 = **47**.

**Winner: Option A (stdlib)**, margin **79 − 47 = 32 points (40%
weighted-sum advantage)**. Option B wins only on hand-rolled test
burden (where the SDK's own test coverage substitutes for ours); every
other dimension favors stdlib, with dep surface, CVE history, and
adopter friction all maximum-delta.

## Decision

**Option A chosen: hand-rolled stdlib JSON-RPC 2.0 over `http.server`
+ `urllib`.** All framework MCP server code lives in
`.claude/scripts/mcp-server/` and `_lib/mcp/` (if shared helpers
emerge), stdlib-only, Python ≥3.9, pinned to MCP spec revision
**2025-11-25** at Phase A kickoff.

**Rationale.** The A.0 spike
(`docs/research/mcp-sdk-vs-stdlib.md` §Verdict) resolved Open
question Q1 with stdlib UPHELD on 3 of 4 Decision Drivers and neutral
on the fourth. Specifically: (1) the Python SDK disclosed 3 High-
severity GHSA advisories within a 9-month window (spike §1.2), vs
zero CVEs against stdlib JSON-RPC framing in the same window (spike
§1.3); (2) the transitive-dep surface delta is 0 → ~45 packages
(spike §4.3), a material ADR-002 reversal requiring its own amendment
with no compelling blocker evidence; (3) MCP protocol velocity rates
EVOLVING with 100% breaking-change rate per revision (spike §3.1–3.3),
meaning vendoring imposes continuous regression risk rather than
stability dividend; and (4) the ~35–45-test hand-roll burden fits
comfortably within Phase A's +70-test budget (spike §2.3), with
`_lib/contract.py` precedent at 14.1 tests/100 LOC. The weighted
trade-off matrix above scores Option A at 79 vs Option B at 47, a
40% advantage driven primarily by dep surface + CVE history + adopter
installation friction dimensions.

**Revisit conditions (flip to Option B warranted if any ONE holds
over a 6-month observation window).** These are the operational
triggers that would reverse the evidence base underlying this decision:

- **Trigger A (spec converges):** MCP spec ships a revision
  explicitly labeled "stable, no breaking changes planned" and
  subsequently goes 6 months without a breaking revision. At that
  point, vendoring the validated reference implementation becomes
  lower risk than hand-rolling.
- **Trigger B (CVE asymmetry flips):** ceo-orchestration ships 3+
  CVEs against its own hand-rolled MCP JSON-RPC transport in 6
  months. At that point, hand-rolling has more CVEs than the SDK for
  the same window and the asymmetry argument reverses.
- **Trigger C (test burden over-runs):** JSON-RPC + MCP handler test
  count grows past 120 (= 3× the projected 40). At that point, the
  maintenance burden exceeds the SDK integration cost.
- **Trigger D (spec-conformance gap observed):** A real adopter's MCP
  client interop fails against our hand-rolled server because we
  missed a spec edge case. One such failure is a bug; three in 6
  months is a pattern requiring reconsideration.
- **Trigger E (ecosystem lock-in):** ≥2 of the top-5 MCP client
  implementations ship features that assume SDK-level abstractions
  (session replay, typed request builders, resources v2) we cannot
  trivially reproduce in stdlib.
- **Trigger F (Python stdlib deprecation):** Python stdlib deprecates
  `http.server` without a drop-in replacement, forcing reimplementation
  against a third-party HTTP library regardless; at that point the
  stdlib-only invariant is already broken and SDK adoption may become
  lower-cost.

Any trigger firing demands a new ADR amendment documenting the
evidence; no silent flip.

**Byte-identity governance passthrough contract.** Option A's chosen
implementation MUST preserve the framework's governance boundary
exactly as `PreToolUse` hooks enforce it on Claude-native calls. The
`spawn_agent` handler MUST construct a `PreToolUse` payload with
byte-identical field names, field order, and value serialization to
what Claude's native spawn invocation produces, then invoke
`check_agent_spawn.decide(payload)` directly (not a wrapper or a
reimplementation of the decision logic), and MUST propagate the
hook's block reason verbatim to the MCP client (same string,
serialized under the JSON-RPC error object's `data.reason` field).
A Wave 2 test fixture (`tests/integration/test_mcp_governance_passthrough.py`)
asserts byte-identity by comparing the JSON-serialized block reason
from a direct hook invocation against the block reason returned by an
equivalent MCP call, across all 3 agent-profile types (backend,
frontend, security). Failure mode: any divergence → CI blocking
error, not a warning — per PLAN-013 debate §C2 CRITICAL consensus
(3/5 agents: Staff Backend, VP Engineering, Security).

## Consequences

### Positive

1. **Stdlib safety preserved.** Framework runtime dep count remains
   0; the `_lib/` and `.claude/scripts/` layers both uphold ADR-002
   discipline. Adopter SBOM audits do not inherit MCP Python SDK
   transitive surface (~45 packages) or its CVE history.
2. **Spec-velocity resilience.** We control the JSON-RPC framing and
   MCP method dispatch; upgrading to a new spec revision is a
   deliberate ADR-041 transition-log event, not a silent `pip
   install --upgrade`. The 100% breaking-change rate observed in MCP
   spec revisions (spike §3.1) becomes a governance event rather than
   a production surprise.
3. **Governance integrity mechanically enforced.** `spawn_agent`
   handler wires directly into `check_agent_spawn.decide()`; the
   byte-identity test fixture (Wave 2) regresses on any divergence.
   External MCP clients (Cursor, IDE plugins) receive identical block
   reasons to Claude-native spawn attempts — a debate §C2 CRITICAL
   invariant now testable.
4. **Cost inheritance applies uniformly.** `LiveCallPolicy` ceilings
   (ADR-040 §3: $0.50/spawn, $2.00/plan/5min, MAX_ROUNDS=5 debate)
   bind at the adapter layer, not the MCP layer; MCP `spawn_agent`
   invocations inherit identically to Claude-native spawns. No
   parallel budget surface to desynchronize.
5. **ADR-002 discipline reinforcement.** This ADR is an additional
   evidence point that ADR-002 stdlib-only scales to non-trivial
   protocol surfaces (prior evidence: `_lib/adapters/live/` urllib
   against 4 providers per ADR-040 §Option 2). Cumulatively this
   reduces pressure to relax ADR-002 for future surfaces.
6. **CVE patch velocity localized.** Any CVE against our
   `.claude/scripts/mcp-server/` transport is patchable in one repo
   in one commit plus one ADR-041 transition-log row; no downstream
   pin-chasing, no adopter coordination, no PyPI version resolution.

### Negative

1. **Hand-rolled test burden ~35–45 tests.** Spike §2.3 projected
   50–80 tests for full scope (transport + handlers + auth +
   governance-passthrough); the in-budget target is the lower bound
   of that range. Phase A budget +70 absorbs this with ~25–35 tests
   headroom for Phase A.6 audit-event coverage and Phase A.7
   integration tests. Density will match or exceed the `_lib/contract.py`
   precedent (14.1 tests/100 LOC for protocol-contract code).
2. **Manual MCP spec tracking.** No auto-upgrade on new MCP spec
   revision (spike §3.1 cadence: ~1 per 81 days). Process: each new
   spec revision triggers a PLAN-NNN entry + ADR-042 amendment (new
   Transition Log row) + conformance-test regen, not a silent
   dependency bump. Mitigation: `docs/research/mcp-sdk-vs-stdlib.md`
   §3.4 pins our reference revision explicitly; Sprint 14+ red-team
   eval corpus includes a spec-regression smoke that surfaces if the
   pinned revision is more than 180 days stale.
3. **Potential reimplementation cost for Sprint 14+ complex features.**
   If MCP resources, prompts, sampling, or elicitation become
   adopter-required in Sprint 14+, we implement each feature manually
   rather than inheriting SDK support. Cost estimate: 100–300 LOC
   per feature depending on scope; each requires its own ADR
   amendment to ADR-042 or a successor ADR. If ≥2 of the top-5
   feature requests fit the SDK's abstraction exactly, revisit
   condition Trigger E fires.
4. **Divergence from any future Anthropic reference server.** Our
   implementation is semantically equivalent to the MCP spec but not
   byte-identical to the official SDK's wire output (e.g.
   serialization order of JSON keys, whitespace in error messages).
   Adopter MCP clients that depend on SDK-specific quirks may require
   adaptation. Mitigation: SPEC/v1/mcp-server.schema.md documents our
   wire format explicitly; adopters test against our fixture, not
   against SDK output.

### Neutral

1. **Additive SPEC v1 schema file.** `SPEC/v1/mcp-server.schema.md`
   (Phase A.2 deliverable) is a new file; no breaking changes to
   existing SPEC/v1 contracts. SPEC file count 16 → 17 after Phase
   A.2 lands.
2. **One new ADR number consumed (042).** Phase 0 already reserved
   ADR-042/043/044 together; no additional ADR-number pressure.
   ADR-043 (SOC2 Audit Trail Mapping) and ADR-044 (Formal
   Verification Pilot) remain reserved for PLAN-013 Phase C.4 and
   Phase D.4 respectively.
3. **Incremental memory footprint ~2–3 MB per running server process.**
   Stdlib `http.server` + ThreadingMixIn + JSON dispatch state is
   lightweight compared to the ~30–60 MB baseline of the Python SDK
   with pydantic/starlette/uvicorn loaded. Adopters running the MCP
   server as a sidecar to an IDE see this as a positive; it is
   categorized neutral here because baseline footprint is not a
   governance invariant.

## Blast radius

**Rating: L2** (new module tree, governance-preserving, additive-only
to existing state; no changes to running-framework behaviour when
`mcp_server_enabled = false`, which is the default).

### Modules created (new paths — Wave 2 scope)

- `.claude/scripts/mcp-server/server.py` — main entry point;
  `CEO_SOTA_DISABLE` kill-switch honored (§Cost.4), localhost-only
  bind, ThreadingHTTPServer, stdio alternative entry point deferred.
- `.claude/scripts/mcp-server/_rate_limit.py` — token-bucket rate
  limit per §Auth.3 (stdlib, fixed-window-with-refill).
- `.claude/scripts/mcp-server/auth.py` — HMAC verification per §Auth.1,
  origin check per §Auth.4, audit denial emit per §Auth.5.
- `.claude/scripts/mcp-server/cost.py` — `LiveCallPolicy` passthrough
  wrapper; delegates to `_lib/adapters/live/_policy.py`.
- `.claude/scripts/mcp-server/handlers/list_skills.py` — read-only.
- `.claude/scripts/mcp-server/handlers/get_skill.py` — read-only.
- `.claude/scripts/mcp-server/handlers/list_agents.py` — read-only;
  reads `.claude/team.md` via `_lib/team.load_names`.
- `.claude/scripts/mcp-server/handlers/list_pitfalls.py` — read-only;
  reads `.claude/pitfalls-catalog.yaml`.
- `.claude/scripts/mcp-server/handlers/get_audit_log.py` — read-only;
  tail-reads `~/.claude/projects/ceo-orchestration/audit-log.jsonl`
  with `_lib/filelock` guard.
- `.claude/scripts/mcp-server/handlers/spawn_agent.py` — write +
  cost; governance passthrough per §Decision byte-identity contract.
- `.claude/scripts/mcp-server/handlers/server_capabilities.py` —
  declares protocol version + handler list + feature flags per
  PLAN-013 consensus §S4 seventh-handler requirement.
- `SPEC/v1/mcp-server.schema.md` — SPEC file (Phase A.2).
- `.claude/scripts/mcp-server/tests/test_*.py` — ~35–45 unit tests
  (Wave 2).
- `tests/integration/test_mcp_governance_passthrough.py` — byte-
  identity integration test (Wave 2).
- `.github/workflows/mcp-smoke.yml` — CI smoke check (Wave 2). *(A
  dedicated `mcp-coverage.yml` was never shipped — the smoke workflow is
  what landed, and the mcp-server test roots enter the main CI matrix via
  `validate.yml` in v1.0.1 (PLAN-152 tests-01/tests-05); the general
  coverage gate lives in `coverage.yml`.)*

### Modules modified (already complete in Wave 0 — Phase 0 + Session 21)

- `_lib/audit_emit.py` — +10 events registered in `_KNOWN_ACTIONS`:
  `mcp_server_started`, `mcp_server_disabled_by_kill_switch`,
  `mcp_handler_invoked`, `mcp_handler_completed`,
  `mcp_handler_denied`, plus the 5 live-adapter events surfaced as
  Gap #3 in Session 20 progress-log (`live_adapter_call_started`,
  `live_adapter_call_completed`, `breaker_opened`, `breaker_closed`,
  `credential_rotation_due`).
- `SPEC/v1/audit-log.schema.md` — +10 rows matching the above.
- `.github/CODEOWNERS` — +5 entries for `.claude/scripts/mcp-server/`,
  `SPEC/v1/mcp-server.schema.md`, `docs/mcp-cursor-setup.md`,
  `tests/integration/test_mcp_*.py`, `.github/workflows/mcp-*.yml`
  (completed Phase 0).

### Modules referenced (read-only dependencies)

- `_lib/adapters/live/_policy.py` — `LiveCallPolicy.enforce()` called
  by `handlers/spawn_agent.py` per §Cost.1.
- `_lib/adapters/live/_breaker.py` — circuit breaker state consulted
  per §Cost.3.
- `_lib/adapters/live/_cost.py` — spawn-cost tracking per §Cost.1
  rate-window accounting.
- `check_agent_spawn.decide()` — governance passthrough per §Decision
  byte-identity contract.
- `_lib/team.py::load_names` — for `list_agents` handler.
- `_lib/audit_emit.py` — event emission for all handler invocations.
- `_lib/filelock.py` — audit-log tail read in `get_audit_log`.

### Reversibility: MEDIUM

- **Immediate disable:** set `CEO_SOTA_DISABLE=1` — server refuses
  to bind, logs `mcp_server_disabled_by_kill_switch`, exits 0; zero
  impact on running framework. Reversal time: seconds.
- **Soft removal:** set `mcp_server_enabled = false` in
  `.claude/settings.json`; server never starts. No audit events emit
  from MCP path. Reversal time: seconds.
- **Full module removal:** `git rm -rf .claude/scripts/mcp-server/`
  + revert `SPEC/v1/mcp-server.schema.md` + revert 10 audit event
  rows in `_lib/audit_emit.py::_KNOWN_ACTIONS` + revert SPEC audit-
  log rows + revert CODEOWNERS entries + revert this ADR's Status
  to SUPERSEDED with a pointer to the superseding ADR. Estimate: ~4
  hours of deliberate work. **No destructive migrations required**
  — MCP server owns no persistent state beyond audit log entries
  (which remain valid history).

### 10x scale pass: YES

- Read-only handlers at §Auth.3 rate limits (60 req/min per client)
  × 10 adopter clients = 600 rpm aggregate. Stdlib
  `ThreadingHTTPServer` benchmarked locally at >1000 rps for
  small JSON responses (spike §2.4 context). Projected headroom ≥4×
  at 10× adopter count.
- `spawn_agent` at 6 req/min × 10 clients = 60 rpm aggregate;
  `LiveCallPolicy` $2.00/plan/5min ceiling binds before the MCP
  layer does. Scale-out is gated by adapter cost, not transport.
- Per-client token bucket state is O(N_clients) memory; 100 clients
  at ~1 KiB state per bucket = ~100 KiB. Fits in process memory
  trivially.
- No re-architecture required for 10× load; only rate-limit tuning
  via `.claude/settings.json` `mcp_rate_limits` (per-client override
  already supported per §Auth.3).

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row
records a state transition triggered by a Phase A deliverable landing
or a production enablement.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| 2026-04-15 | (absent) | ADR stub reserved + §Auth + §Cost locked | PLAN-013 Phase 0 item 0.1 + 0.5 | Phase 0 commit `78ae44b` | CEO |
| 2026-04-15 | ADR stub reserved | Phase A.3 §Options/§Decision/§Consequences/§Blast radius fully written + Option A (stdlib) UPHELD per A.0 spike 2026-04-15 | `.claude/plans/PLAN-013/progress-log.md` Session 21 + `docs/research/mcp-sdk-vs-stdlib.md` §Verdict | (pending session commit) | CEO |
| _(Phase A.3 accept via PR merge pending — flips Status PROPOSED → ACCEPTED)_ | | | | | |

## References

- PLAN-013 §Items Phase 0 (0.1, 0.5) — this ADR's Phase 0 scope.
- PLAN-013 §Items Phase A (A.1–A.7) — full ADR completion.
- PLAN-013 debate Round 1 consensus §C2 CRITICAL (governance
  passthrough) + §S1 CRITICAL (auth model) + §S13 HIGH (cost-cap
  inheritance) + §S4 HIGH (7th handler).
- ADR-002 — hooks package layout + `.claude/scripts/` discipline.
- ADR-028 — canonical envelope (handler return shapes).
- ADR-035 — OTEL double-redaction boundary precedent.
- ADR-040 — `LiveCallPolicy` inheritance source.
- ADR-041 — Transition Log appendix format.
- ADR-043 — SOC2 audit trail mapping (this ADR's events are input).
- ADR-044 — Formal Verification Pilot (MCP contract candidate target).
- `SPEC/v1/mcp-server.schema.md` — companion schema (Phase A.2).
- `SPEC/v1/audit-log.schema.md` — event registration (Phase A.6).
- `docs/research/mcp-sdk-vs-stdlib.md` — A.0 spike output (Phase A.0).
- `.claude/scripts/mcp-server/**` — implementation (Phase A.1, A.4–A.7).

## Enforcement commit

`78ae44b0bb8a` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
