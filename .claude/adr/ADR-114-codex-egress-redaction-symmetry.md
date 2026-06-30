---
id: ADR-114
title: Codex MCP egress redaction symmetry across ALL callsites
status: ACCEPTED
proposed_at: 2026-05-12
proposed_by: CEO (PLAN-084 Wave 0.5 per R1 Sec-P0-2 + R2 CODEX-P0-1 expansion)
related_plans: [PLAN-081, PLAN-084]
related_adrs: [ADR-107, ADR-108, ADR-111]
supersedes: []
authorization: PLAN-084 wave-0-approved.md sentinel
---

# ADR-114 — Codex MCP egress redaction symmetry

## Context

PLAN-081 (Pair-Rail Multi-LLM) shipped INGRESS sanitization for Codex
MCP responses via `check_codex_response.py` PostToolUse. That closed
the in-bound attack vector (Codex output → framework).

The OUTBOUND vector remained partially-open until PLAN-084 R1 Sec-P0-2
flagged it: framework prompts sent to Codex contain source code fragments,
evidence quotes, secrets potentially embedded in file contents (audit-log
HMAC keys, sentinel signer fingerprints, configuration tokens). Sending
these to a third-party LLM = CWE-200/201 information exposure.

R1 Sec-P0-2 proposed wiring `_lib/codex_egress_redact.redact()` at the
single egress callsite `codex_invoke.py:invoke_codex()`. R2 CODEX-P0-1
(iter-1) flagged that fix as INCOMPLETE — `check_pair_rail.py:325-363`
contains another Codex egress path via `subprocess.run(input=prompt)`
that R1 Sec-P0-2 missed.

## Decision

Implement `redact_outgoing()` in `_lib/codex_egress_redact.py` as a
mirror of `redact()` (which is currently ingress-only). Wire it at
ALL Codex / external-LLM egress callsites:

1. `.claude/scripts/codex_invoke.py:invoke_codex()` — Pair-Rail dispatcher
2. `.claude/hooks/check_pair_rail.py:_invoke_codex_review()` line 325-363 — LIVE Pair-Rail review path
3. `.claude/hooks/_lib/adapters/codex.py:make_invoke_command()` callers
4. Any direct `mcp__codex__codex` / `mcp__codex__codex-reply` invocation from scripts or skills
5. Wave D.2 proposal-pair generator at write time to `claude-vs-codex-debate-D.yaml`

Register audit action `pair_rail_outgoing_redaction_applied` in
`_KNOWN_ACTIONS` (Wave 0.8) with 4-source S100 L6 atomicity.

**Mandatory regression tests** (R2 CODEX-P0-1 strict enforcement):

- `test_codex_invoke_redacts_outgoing_prompt`
- `test_check_pair_rail_redacts_outgoing_prompt`
- `test_codex_egress_callsite_coverage` — AST-based enumeration test
  that walks all `subprocess.run`, `_codex.make_invoke_command`,
  `mcp__codex__*` invocations across the codebase; fails if any
  callsite reaches a Codex/external-LLM API without prior
  `redact_outgoing()` invocation in the same function scope.

## Consequences

- AC9 (Codex egress redaction symmetry) becomes mechanically verifiable
  via the AST coverage test
- Adds ~50-100ms latency per Codex egress (acceptable per Perf-NTH)
- Closes CWE-200/201 vector across the framework (defense-in-depth
  on top of ADR-107/108 trust boundary)

## Authorization

Canonical-guarded file edits gated by sentinel
`.claude/plans/PLAN-084/wave-0-approved.md` with Scope:
- `.claude/hooks/_lib/codex_egress_redact.py`
- `.claude/hooks/check_pair_rail.py`
- `.claude/scripts/codex_invoke.py` (not canonical-guarded but covered for traceability)
