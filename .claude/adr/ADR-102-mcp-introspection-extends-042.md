# ADR-102 — MCP introspection tools extending ADR-042

**Status:** ACCEPTED
**Date:** 2026-05-05
**Enforcement commit:** `317c824` (PLAN-070 ceremony S85, v1.13.0 GA)
**Decision drivers:**

- ADR-042 (ACCEPTED 2026-04-15, PLAN-013 Phase A) defines the MCP Server Contract over JSON-RPC stdio. Server already runs in production. PLAN-070 needed to add introspection tools (governance audit, canonical-edit guard, kill-switch) WITHOUT a new MCP contract or new transport.
- Codex Round 3 cross-LLM gate (ADR-095 §gate-#6) caught a P0 BLIND SPOT all 4 Claude same-LLM passes missed: external MCP clients (Cursor / Codex CLI / `helmor` pattern) bypass Claude's `PreToolUse` hook entirely. A Layer A (intra-Claude hook matcher) without a Layer B (server-side middleware) leaves canonical paths unguarded for any external client.
- Sec MF-3 6-field allowlist contract for audit emits (`tool_name`, `target_path`, `reason`, `timestamp`, `session_id`, `project`) to prevent side-channel leakage of unbounded text.
- Stdlib-only at runtime (PLAN-070 §5; ADR-085 Claude-only positioning).

## Context

PLAN-068 v1 originally proposed a new MCP contract for introspection. Round 1 debate identified collision with ADR-042 (already-ACCEPTED MCP Server Contract). PLAN-070 was lifted from PLAN-068 Track-3 with the explicit reframing: **extend** ADR-042's contract surface with new introspection tools, do not create a parallel contract.

Three architectural questions had to be answered:

1. **Where does the canonical-edit guard live?** Claude's `PreToolUse` hook (Layer A) catches `Edit/Write/MultiEdit/NotebookEdit` but not `mcp__*` tools (per `feedback_custom_mcp_tools_governance_gap.md`, S81-tris). External clients also bypass Claude entirely.
2. **What is the audit allowlist for the new emit actions?** New `mcp_canonical_guard_allowed/blocked` emits must not leak unbounded text (LLM06 side-channel guard).
3. **What is the kill-switch contract?** A runtime-disabled MCP server must fail clean without exposing handlers.

## Decision drivers

- ADR-042 mandate: stdio-only transport; no HTTP; no new contract for extensions.
- ADR-051 governance: canonical paths must remain guarded across all dispatch surfaces.
- ADR-052 veto floor: Security and Code-Review hold supreme veto on auth/canonical-edit changes; Sec held VETO across PLAN-070 R1+R2+R3 until 6 conditions lifted.
- ADR-095 §gate-#6 mandate: every L4 plan touching governance MUST pass cross-LLM Codex re-pass. PLAN-070 R3 Codex gate caught NG-06 (Layer B necessity) that 4 Claude passes missed.
- ADR-098: audit emits must be hasattr-guarded so the script works in adopter installs that haven't run the v1.12.0 canonical ceremony yet.
- ADR-100: trusted dependencies — stdlib-only at runtime.

## Options considered

### Option A: Layer A only (intra-Claude hook matcher)

Extend `check_canonical_edit.py` with `mcp__*` matcher; rely on branch protection + CODEOWNERS + Claude's `PreToolUse` hook.

- **(+)** Minimal surface; reuses existing hook infrastructure.
- **(+)** Fail-OPEN safe — if matcher misfires, branch protection still catches downstream.
- **(−)** External MCP clients (Cursor, Codex CLI, helmor) bypass `PreToolUse` entirely.
- **(−)** Defense-in-depth violation: a single layer at the wrong trust boundary.

### Option B: Layer B only (server-side middleware)

`_lib/mcp/canonical_guard.py` invoked from `audit-mcp/server.py` dispatch.py pre-handler middleware. Skip the hook matcher.

- **(+)** Universal — every MCP handler is guarded regardless of caller.
- **(+)** Fail-CLOSED at the right boundary (server-side).
- **(−)** Misses tool calls that don't reach the MCP server (intra-Claude direct edits via custom MCP tools that bypass server-side middleware via different IPC).
- **(−)** Doesn't surface the block to the user inside Claude until it's too late.

### Option C: Layer A + Layer B (defense-in-depth)

Both. Layer A for intra-Claude UX (fail-OPEN, fast feedback). Layer B for inter-process external (fail-CLOSED, universal). Single source of truth via shared `_CANONICAL_GUARDS` patterns + sentinel verification logic.

- **(+)** Catches all five known attack classes (intra-Claude, external client direct, external via Codex CLI, helmor pattern, future MCP transport variant).
- **(+)** Each layer at its appropriate trust boundary.
- **(+)** Codex Round 3 cross-LLM gate explicitly identified Option C as the only design that closes NG-06.
- **(−)** Two implementations — drift risk if patterns aren't shared.
- **(−)** ~998 LoC for `canonical_guard.py` (Codex apply_patch envelope + unified diff + JSON Patch RFC 6902 + repo_root anchor + traversal/symlink escape + authoritative-key gating).

## Decision

**Adopt Option C** — Layer A + Layer B with shared `_CANONICAL_GUARDS` source of truth.

### Layer A — `check_canonical_edit.py` matcher extension

Match condition: `(tool_name.startswith("mcp__") OR tool_name in {"Edit","Write","MultiEdit","NotebookEdit"}) AND params contains path-shaped key (path/file_path/target/uri)`. AND-of-both gate prevents false-positives on read-only MCP tools (e.g. `mcp__codex__codex` no-file-path call, `mcp__supabase__execute_sql`).

Fail-OPEN OK at this layer — Layer B catches what slips through.

### Layer B — `_lib/mcp/canonical_guard.py` middleware

Server-side middleware invoked from `dispatch.py` pre-handler for every MCP handler whose response touches the filesystem OR whose handler arguments include path-shaped params. Recognizes:

- Codex `apply_patch` envelope (incl. `*** Move to:` directive + colon-optional variants)
- Unified diff format
- JSON Patch RFC 6902 (`json.loads` decode of body string)
- Plain path arguments

Resolution rules:

- `repo_root` anchor — refuse paths that escape the project tree
- `is_relative_to` traversal/symlink escape detection
- Authoritative-key gating (R5-01) — `apply_patch` resolves to `patch` before bare `diff`; corrupt binary / `{}` / `""` all resolve to `(paths=[], parsed=False)` → block (fail-CLOSED)

Fail-CLOSED universal: any parse failure, any escape attempt, any unrecognized envelope → return `{"decision": "block"}`.

Public API:

```python
def check_mcp_call(tool_name: str, params: dict) -> dict:
    """Returns {"decision": "allow"|"block", "reason": str}."""
```

### Audit emit allowlist (Sec MF-3 contract)

Two new audit actions registered in `audit_emit._KNOWN_ACTIONS`:

- `mcp_canonical_guard_allowed`
- `mcp_canonical_guard_blocked`

Per-action allowlist conforms to Sec MF-3 6-field contract: `tool_name`, `target_path`, `reason`, `timestamp`, `session_id`, `project`. Auxiliary fields (`reason_code`, `file_path`, `sentinel`, `error`, token fields, HMAC fields, `ts`) currently included pending PLAN-076 Onda A item #4 tightening to the literal 6-field contract.

### Kill-switch runtime contract

`audit-mcp/server.py` first-line check (before any handler dispatch, before any imports beyond `os`/`sys`):

```python
import os, sys
if os.environ.get("CEO_SOTA_DISABLE") == "1":
    try:
        from _lib.audit_emit import emit_generic
        emit_generic("mcp_server_disabled_by_kill_switch",
                     reason="CEO_SOTA_DISABLE=1")
    except Exception:
        pass
    sys.exit(0)
```

Tested via `test_kill_switch.py` subprocess invocation; assert exit code 0; assert audit-log contains `mcp_server_disabled_by_kill_switch` event; assert no JSON-RPC handshake attempted.

### Transport remains stdio-only

PLAN-070 is STDIO-only per ADR-042 §Transport.1. HTTP is explicit out-of-scope. `CEO_MCP_TRANSPORT=http` env var is not recognized; if set, server refuses + emits `mcp_server_disabled_by_kill_switch`. Negative integration test (`test_no_http_transport.py`) asserts this behavior.

## Consequences

**Positive (+):**

- Defense-in-depth across all five known attack classes (intra-Claude, external client direct, Codex CLI, helmor pattern, future MCP transport variant).
- Single source of truth via shared `_CANONICAL_GUARDS` patterns — drift risk is mechanical, not semantic.
- Codex Round 6 ACCEPT verdict (24 unique cross-LLM findings vs 0 same-LLM; ADR-095 §gate-#6 confirmation #12).
- Hasattr-guarded audit emits work in pre-canonical-ceremony adopter installs.

**Negative (−):**

- Two implementations of canonical-guard logic (`check_canonical_edit.py` Layer A + `_lib/mcp/canonical_guard.py` Layer B). Mitigation: shared `_CANONICAL_GUARDS` import; integration test `test_layer_ab_parity.py` deferred to PLAN-076 Onda B.
- ~998 LoC Layer B middleware adds maintenance surface. Mitigation: covered by ≥30 unit tests. ~~+ 11 tmpdir-test-design tests reactivated under PLAN-076 Onda B item #2~~ **STRIKE — false claim per PLAN-076 §4.2 finding D (S87 Wave 1 Agent D + Codex MCP cross-LLM gate confirmation, PLAN-076 fork (f) call #1): zero `tmpdir-test-design` markers exist in codebase. Aspirational doc-drift, not real test inventory.**
- Audit allowlist currently includes auxiliary fields beyond the Sec MF-3 6-field contract (R6-01 P2 residual). Closure tracked under PLAN-076 Onda A item #4.

**Neutral (~):**

- Adopters who never wire the MCP server pay zero runtime cost (Layer A matcher is also a no-op for non-MCP tool calls; Layer B is only invoked when the MCP server runs).
- HTTP transport remains future work; no signal value lost by deferring.

## Blast radius

**L3+** — touches ADR-042 (extends), ADR-051 (governance), ADR-052 (veto floor wiring), ADR-095 (cross-LLM gate evidence), ADR-098 (audit emit register pattern). Two new modules (`_lib/mcp/canonical_guard.py` + `mcp-smoke.yml` CI gate) plus audit-action allowlist amendment.

## References

- PLAN-070 (parent — `MCP introspection tools extending ADR-042`, status `done` 2026-05-05)
- PLAN-076 (followup — caveat closeout including allowlist tightening, tier_policy_cli reconciliation; ~~11 skipped tests reactivation~~ **STRIKE — NO-OP per §4.2 finding D**)
- PLAN-070/round-4/codex-mcp-r6-cross-llm.md (FINAL ACCEPT verdict)
- PLAN-070/staging/canonical_guard.py (Layer B implementation, ~998 LoC)
- PLAN-070/staging/check_canonical_edit_layer_a.patch (Layer A matcher extension)
- PLAN-070/round-4/security-engineer-r4.md (Sec architectural ACCEPT-CONDITIONAL with R6-01 P2 deferred)
- `feedback_custom_mcp_tools_governance_gap.md` (S81-tris origin trace for Layer A necessity)
- ADR-042 (extended by this ADR)
- ADR-051 (canonical-edit governance)
- ADR-052 (Sec/CR veto floor)
- ADR-095 §gate-#6 (cross-LLM mandate)
- ADR-098 (hasattr-guarded audit emit pattern)
- ADR-100 (trusted-dependencies re-affirm — stdlib-only)
