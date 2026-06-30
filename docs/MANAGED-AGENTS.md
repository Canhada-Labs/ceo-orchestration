# Managed Agents — Primitive Mapping + Governance Boundary (K4-lite)

> **Status: DOC-ONLY.** This document ships NO code lane. It maps the
> framework's local primitives onto Anthropic's Managed Agents (beta)
> primitives, states the billing model, and sketches the ONE pattern that
> makes cloud delegation governable (custom-tools-as-local-gate). The full
> `cloud-delegate` lane (a `/delegate` command, audit-bridge, generated
> environments/policies) is a **FUTURE plan, gated on the PLAN-134 W4
> hook-parity probe** — nothing in this document is implemented today.
>
> Source: PLAN-135 W3 item K4-lite; harvest `research/HARVEST-REPORT.md` §K4.

---

## ⚠️ The central warning — cloud sessions sit OUTSIDE the local governance perimeter

Every guarantee this framework makes is enforced by the **local** rail:
PreToolUse/PostToolUse hooks, the canonical-edit sentinel, spawn governance,
FILE ASSIGNMENT confinement, the HMAC-chained audit log, and the Owner GPG
ceremony. A Managed Agents session executes its tools in an
**Anthropic-hosted container** on the provider side of the API boundary.
None of the local rail traverses that boundary:

- **No hook evaluates** a cloud tool call. `check_canonical_edit.py`,
  `check_bash_safety.py`, `check_agent_spawn.py` — structurally absent.
- **No audit-log entry is written.** The session emits its own Events
  stream (SSE), but nothing lands in `audit-log.jsonl` unless a local
  bridge ingests it (future lane, not built).
- **No FILE ASSIGNMENT confinement.** The cloud container's filesystem is
  not partitioned by the framework; in multiagent sessions all agents
  **share the container and filesystem**, which breaks FILE ASSIGNMENT
  isolation by construction — hence the harvest rule: *multiagent in the
  cloud only for read-only work*.
- **No Owner ceremony** between the agent and its writes inside the
  container. The only governable write channel back to a repo is a PR
  (which lands in the normal Owner GPG ceremony).

Treat a cloud session exactly like the API-side `mcp_servers` connector in
`docs/threat-model.md` §MCP-connector-bypasses-rail: **rail-ungoverned by
default**. Same normative consequence: never satisfy a VETO, ceremony gate,
or ADR-145 cross-model review with output produced by an ungoverned cloud
session.

---

## 1. Primitive mapping table

| Local framework primitive | Managed Agents primitive | Mapping notes |
|---|---|---|
| **Archetype** (team.md persona: name, skills, VETO scope, spawn prompt) | **Agent** (`/v1/agents` — persisted, versioned: `model`, `system`, `tools`, `mcp_servers`, `skills`) | Both are reusable, versioned behavior definitions referenced by ID at run time. An Agent version pin ≈ the byte-identity discipline on spawn prompts. What does NOT map: VETO authority (a cloud Agent has no VETO standing — see warning above). |
| **Saved workflow** (`.claude/workflows/*.js` — one governed run with confinement) | **Session** (`/v1/sessions` — one stateful run of an Agent inside an Environment) | Both are the per-run unit: create, drive, observe, archive. A workflow's ADR-136-AMEND-1 confinement (agents write NO files) has no cloud equivalent — the session container is freely writable by the agent. |
| **Audit log** (`audit-log.jsonl`, HMAC-chained, closed-enum actions) | **Events** (`/v1/sessions/{id}/events` — SSE stream + paginated list: `agent.tool_use`, `agent.message`, `span.model_request_end` w/ `model_usage`, …) | Same role: forensic trail of who-did-what. Different trust class: Events are provider-attested, not HMAC-chained by the local key, and are NOT in the local log until an audit-bridge ingests them (future lane: new closed-enum actions + SPEC). |
| **FILE ASSIGNMENT** (per-agent write scope, hook-enforced) | **Environment** (`/v1/environments` — container template: `networking: unrestricted\|limited`, `allowed_hosts`, packages) | Weakest analogy of the four, and deliberately so: an Environment confines the **container** (egress, packages), not per-agent file scopes inside it. `networking: limited` + `allowed_hosts` is the egress analog of the PLAN-133 egress allowlist; there is no per-path write confinement. |

Supporting primitives (no single local equivalent):

| Cloud primitive | Closest local concept | Note |
|---|---|---|
| **Files** (`/v1/files`, `mount_path`, outputs in `/mnt/session/outputs/`) | Plan artifact layout (`.claude/plans/PLAN-NNN/…`) | Future lane mounts artifacts in the canonical plan layout. |
| **Vaults** (`mcp_oauth` / `environment_variable` — secret substituted at egress; sandbox sees an opaque placeholder) | ADR-040 credential handling + `redact_secrets()` | This is the **agent-blind-at-egress** tier — ranked ABOVE redact > scan in the hierarchy the threat-model §containment layers names as the gold tier the local framework does not ship. |
| **Outcome** (`user.define_outcome` + gradeable rubric, iterate→grade loop) | PLAN-SCHEMA §13 `Check:` lines | Future lane generates Outcome rubrics verbatim from §13 Check blocks. |
| **Scheduled deployments** (cron-fired sessions) | `/loop` + nightly-hygiene workflow | Future `/delegate schedule` (weekly hygiene waking the Owner with a report). |

---

## 2. Billing model

- **Beta surface.** All Managed Agents endpoints require the beta header
  `anthropic-beta: managed-agents-2026-04-01` (official SDKs set it
  automatically on `client.beta.{agents,environments,sessions,…}` calls).
- **Two meters, not one:** a per-**session-hour** rate for the hosted
  container (harvest figure: **~$0.08/session-hour** — verify against the
  current provider pricing page before budgeting; this doc does not claim
  ledger-grade economics) **plus standard token costs** for all model
  inference inside the session (drawn from the org's normal ITPM/OTPM
  limits; per-request usage is visible on `span.model_request_end
  .model_usage` events).
- Consequence for the framework's cost discipline: a cloud delegation has
  a **wall-clock cost floor** even when idle-ish — long-lived sessions are
  not free the way an idle local terminal is. Any future `/delegate` lane
  must put session-hours in the same plan cost ledger as tokens
  (`/agent budget` bucket #3 per the harvest).

---

## 3. Custom-tools-as-local-gate (pattern sketch — NOT implemented)

The one mechanism that lets a cloud session participate in local governance
**without** the rail crossing the API boundary: make every privileged
action a **custom tool**, so the provider pauses and the local side executes.

How the provider side behaves (API contract, verified against the
Managed Agents reference):

1. The Agent declares privileged actions as `type: "custom"` tools
   (e.g. `run_gated_command`, `request_owner_decision`) — **no
   implementation lives in the cloud**.
2. When the cloud agent invokes one, the session emits
   `agent.custom_tool_use` on the Events stream and goes **`idle` with
   `stop_reason.type: "requires_action"`** — the cloud loop is blocked.
3. The **local bridge** (the process holding the SSE stream under the
   Owner's API key) receives the request and runs it through the LOCAL
   rail: hook chain evaluates the concrete command/edit, audit-log entry
   is emitted, and anything Owner-gated lands in the Owner queue/ceremony.
4. Only after local governance allows (or the Owner approves) does the
   bridge reply with `user.custom_tool_result`; a denial returns
   `is_error: true` with the governance reason, and the session resumes.

Properties that make this the load-bearing pattern (key item of the K4
harvest: *without this, delegation = governance bypass*):

- The gate is **pull, not push** — the cloud side cannot execute the
  privileged action itself; it can only ask. The local bridge is a client
  holding an authenticated stream, not a listening endpoint.
- Credentials stay host-side (or vault-side, agent-blind): the container
  never holds the secret needed for the privileged action.
- The same shape covers Owner decisions: a `request_owner_decision` custom
  tool is the cloud analog of an AskUserQuestion escalation (K10).
- Honest limit: everything NOT declared as a custom tool (bash inside the
  container, file writes to the workspace, `unrestricted` egress) remains
  ungoverned. The pattern gates the actions you enumerate — it does not
  retrofit the perimeter.

---

## 4. The future `cloud-delegate` lane (NOT this document, NOT shipped)

Deferred design points recorded from the harvest so the future plan starts
from the ratified shape — **gated on the PLAN-134 W4 hook-parity probe**:

- READ-ONLY heavy offload first (the 101-agent-audit class; nightly runs).
- `networking: limited` Environments **derived from** the PLAN-133 egress
  allowlist; `permission_policy` generated from the local posture.
- Outcomes generated verbatim from PLAN-SCHEMA §13 `Check:` lines.
- Audit-bridge ingesting the Events SSE into the local audit-log (new
  closed-enum actions + SPEC change — its own ceremony).
- Artifacts via Files mounted in the canonical plan layout; the ONLY write
  channel back = PR (lands in the Owner GPG ceremony).
- Vaults for credentials, with the **agent-blind-at-egress > redact >
  scan** hierarchy documented against ADR-040.
- Cloud multiagent restricted to read-only work (shared sandbox breaks
  FILE ASSIGNMENT confinement).
- `/delegate schedule` (weekly hygiene report waking the Owner) + adopter
  pricing line in `docs/provider-pricing.md`.

## References

- `docs/threat-model.md` — §Harness-vs-hook containment map (egress-
  substitution as gold tier) + §MCP-connector-bypasses-rail (the decision
  rule this doc extends to cloud sessions)
- `.claude/adr/ADR-040-live-adapter-activation-contract.md` — credential
  hierarchy anchor
- `.claude/plans/PLAN-135/research/HARVEST-REPORT.md` §K4 — source harvest
- PLAN-134 W4 — hook-parity probe that gates the cloud-delegate lane
