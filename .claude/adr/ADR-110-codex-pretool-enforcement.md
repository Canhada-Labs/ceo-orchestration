---
id: ADR-110
title: Codex Pre-Tool Enforcement Hook — Block Mechanism for Asymmetric VETO Matrix
status: ACCEPTED
proposed: 2026-05-04
gate: PLAN-075 Phase 0A U11 SPIKE-VERDICT.md outcome
gate_met_at: 2026-05-08
accepted_at: 2026-05-09
accepted_by: S96-cont-2 v1.13.x patch
enforcement_commit: __FILLED_AT_COMMIT__
related_plan: PLAN-075
related_adr: [ADR-077, ADR-082, ADR-105, ADR-106]
---

# ADR-110 — Codex Pre-Tool Enforcement Hook

## Status: ACCEPTED — Phase 1 hook landing complete (check_pair_rail.py at .claude/hooks/) AND Phase 0A U11 gate met (PostToolUse cannot block confirmed; staging/test_u11 21 tests GREEN)

ADR-110 PROPOSED was promoted to DRAFT 2026-05-08 (S96) after Phase 0A U11
SPIKE-VERDICT.md confirmed PostToolUse cannot block tool result delivery (per
SPEC/v1/hook-io.schema.md L14). Further DRAFT → ACCEPTED is gated on Phase 1
hook landing.

## Context

Round 1.5 Codex critique R1.5-1 surfaced: SPEC/v1/hook-io.schema.md L14 declares
PostToolUse hooks "never block" tool result delivery. Therefore
`check_codex_response.py` (ADR-106) cannot enforce — only advisory + audit.

But asymmetric VETO matrix Case B (PLAN-075 §11) requires **blocking** Codex
findings that meet preconditions {file:line + reproducible command + rubric
severity}. Without enforcement primitive, Case B is not mechanical.

## Decision (PROPOSED)

If Phase 0A U11 spike confirms PostToolUse cannot block in current Claude Code
runtime, **author** `.claude/hooks/check_codex_pretool.py` as PreToolUse hook
matched on `mcp__codex__codex|mcp__codex__codex-reply`.

`check_codex_pretool.py` responsibilities:
1. **Pre-flight egress redactor invocation** (sanity check before tool fires)
2. **Pre-flight prompt-body check**:
   - Verify FILE ASSIGNMENT manifest present in prompt body for workspace-write sandbox
   - Verify SKILL REFERENCE format compliant
   - Verify Codex spawn carries sufficient context for VETO_FLOOR_ROLES
3. **Block contract**:
   - Return JSON `{"decision":"block","reason":"..."}` on policy violation
   - Per SPEC/v1/hook-io.schema.md PreToolUse semantics: this DOES block tool dispatch
   - Codex never invoked when block fires
4. **Fail-open contract**:
   - Internal exception → exit 0 (allow); breadcrumb to audit-log.errors
   - Hook bug never blocks user session per ceo-orchestration §Critical Rules

Asymmetric VETO matrix Case B enforcement flow:
1. Codex Round 1 review fires via mcp__codex__codex
2. PostToolUse `check_codex_response.py` (ADR-106) parses verdict, emits advisory flag
3. **Next** mcp__codex__codex call (e.g. Codex Round 2 if disagreement) is gated by `check_codex_pretool.py` which reads prior advisory flags
4. If Round 1 emitted `pair_rail_block_codex_finding` advisory + Case B preconditions met, PreToolUse hook on subsequent governance-gate call BLOCKs ship until Owner-acknowledged

This is a **state-machine block**, not real-time block (PostToolUse limitation).
Honest characterization: enforcement is at next-gate, not at-source.

## Phase 0A U11 falsifiability

Test: dispatch `mcp__codex__codex`; assert `check_codex_response.py` runs
PostToolUse; **assert exit non-zero does NOT block tool result**.

If U11 confirms (expected): ADR-110 promotes to DRAFT; Phase 1 authors hook.
If U11 refutes (unexpected): PostToolUse can block; ADR-110 deferred; ADR-106
covers both advisory + enforcement.

## Consequences (if promoted)

### Positive
- Mechanical block primitive for Case B asymmetric VETO matrix
- State-machine flow honest about PostToolUse limitation
- Audit trail across pre/post hooks

### Negative
- +1 PreToolUse hook (~+44-64ms p95 per Codex call)
- State-machine complexity (advisory flags from PostToolUse consumed by next PreToolUse)
- Owner-acknowledge step required for Case B blocks

### Mitigation
- Hook overhead measured Phase 0A U3 (latency) + U11 (semantics)
- State-machine implemented in `check_codex_pretool.py` reading `audit-log.jsonl` recent advisory flags (last N entries)
- Owner-acknowledge: structured `audit-log.errors` entry + `CEO_PAIR_RAIL_ACK_<finding-id>=1` env var

## References

- SPEC/v1/hook-io.schema.md L14 (PostToolUse never-blocks contract)
- ADR-106 (codex MCP adapter + PostToolUse advisory)
- PLAN-075 spec.md v5 §11 Case B (asymmetric VETO matrix)
- Round 1.5 Codex critique R1.5-1
