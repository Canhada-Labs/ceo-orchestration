---
id: ADR-106
title: Codex MCP Adapter Contract + Hook Coverage Mechanism
status: ACCEPTED
proposed: 2026-05-04
related_plan: PLAN-075
related_adr: [ADR-077, ADR-051, ADR-082, ADR-105, ADR-110]
accepted_at: 2026-05-09
accepted_by: S96-cont-2 v1.13.x patch
enforcement_commit: __FILLED_AT_COMMIT__
---

# ADR-106 — Codex MCP Adapter Contract + Hook Coverage

## Status: ACCEPTED — Phase 1 narrow-promotion landed (check_pair_rail.py + audit_emit pair_rail_* registered)

## Context

PLAN-075 introduces Codex MCP as Tier B sub-agent provider. Three hook coverage
options considered Round 1:

(a) Extend .claude/settings.json PostToolUse matcher to mcp__codex__* + new check_codex_response.py
(b) CEO-side Python shim as ONLY way to invoke Codex
(c) Accept asymmetric coverage explicitly

Round 1.5 Codex critique R1.5-1 + R1.5-2: SPEC/v1/hook-io.schema.md L14 declares
PostToolUse "never blocks". Therefore PostToolUse cannot enforce — only
**scanner+audit advisory**. If block needed (Case B asymmetric VETO matrix),
ADR-110 PROPOSED introduces pre-tool hook.

## Decision

**Option (a) chosen for ADVISORY scanning + audit. ADR-110 PROPOSED for
enforcement (Phase 0A U11 spike gates ADR-110 promotion to DRAFT).**

Rationale:
- Consistent with existing pattern (check_mcp_response.py, check_webfetch_injection.py)
- settings.json matcher mechanically tested
- No invention; reuses ADR-077 redux pattern
- Option (b) cannot enforce against direct mcp__codex__codex calls
- Option (c) accepts gap as feature; rejected per Sec T-1 P0
- PostToolUse as scanner = right primitive; **enforcement gate separate** (ADR-110)

## Adapter Contract

`.claude/hooks/_lib/adapters/codex.py` MUST conform to `SPEC/v1/adapters.schema.md`.
If schema incompatible, bump SPEC v2 with explicit ADR amendment.

ABI:
- `read_event(stream) -> Event`
- `write_decision(decision: Decision, stream) -> None`
- `emit_decision(decision: Decision) -> None`
- `extract_skill_reference(prompt: str) -> Optional[SkillRef]`

KNOWN_ADAPTERS: `["claude", "codex"]` (was `["claude"]`)

## Hook Mechanism

### .claude/settings.json extension (advisory scanner)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "mcp__codex__codex|mcp__codex__codex-reply",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/_python-hook.sh check_codex_response.py"
          }
        ]
      }
    ]
  }
}
```

### check_codex_response.py responsibilities (advisory only)

1. **Ingress injection scan** (Sec T-1, ADR-077 redux):
   - Scan Codex output for harness_mimicry from _lib/injection_patterns.py
   - Scan for <system-reminder> tags, raw shell command suggestions
   - On detection: append injection_blocked audit; rewrite output neutralized. Cannot block tool result delivery via PostToolUse (per SPEC L14); flag goes to next ingestion-gate hook
2. **Schema validation** (Sec adjustment 4, U5):
   - `{ verdict: "PASS|BLOCK", findings: [...], confidence: 0-1, provider: "codex", model: "gpt-5.5-codex" }`
   - VETO_FLOOR_ROLES: emit advisory flag pair_rail_codex_schema_invalid
   - Non-VETO L2: emit pair_rail_advisory
3. **Audit emit** (Sec adjustment 8):
   - agent_provider="codex" + mcp_call_id + parent_pair_id + prompt_sha256 + response_sha256 from Claude harness side
   - HMAC-chain via audit_hmac.py
   - Reject self-reported agent_provider from sub-agent prompt body (forgery mitigation)
4. **Fail-open contract**:
   - Internal exception → exit 0, breadcrumb to audit-log.errors
   - Per SPEC L14: PostToolUse never blocks regardless

### Block enforcement (separate — ADR-110)

If Phase 0A U11 confirms PostToolUse cannot block, ADR-110 PROPOSED authors
check_codex_pretool.py (PreToolUse mcp__codex__codex) which **can** block.
ADR-110 promotion gate: U11 SPIKE-VERDICT.md outcome.

## Egress redactor

`_lib/codex_egress_redact.py` invoked by codex_invoke.py unconditionally
BEFORE MCP call. Strips:
- $HOME / $CLAUDE_PROJECT_DIR absolute paths (LGPD PII per S80 R9)
- audit-log.jsonl payload echoes
- GPG key fingerprints (16+ hex)
- key=value secret patterns (reuse secret_patterns.py)
- Codex / OpenAI key patterns (sk-proj- / sk-)

1 mutation fixture (mutations/leak-pii-to-codex.diff) added to _FROZEN_BASELINE.

## Sandbox modes

| Phase | Default sandbox | Rationale |
|---|---|---|
| Phase 0A spike | read-only | Safety-first |
| Phase 1 review-only | read-only | Codex never writes |
| Phase 4 mechanical promotion | read-only | All review tasks |
| Phase 5 coder (conditional) | workspace-write (gated U2 + check_codex_filewrite.py) | Coder writes; deny-list canonical |

## Approval policy

`approval-policy: never`. Codex never prompts user. Hook layer + ADR-110 (when active) is the gate.

## Consequences

### Positive
- Real mechanical advisory + audit on Codex outputs
- Pattern consistent with ADR-077 redux response
- Audit trail complete via Claude harness PostToolUse
- Egress redactor closes Sec T-2 P0
- Honest separation: advisory (PostToolUse) vs enforcement (ADR-110 PreToolUse pending U11)

### Negative
- +1 hook (~+44-64ms p95 warm; +200-300ms cold per DIM-15)
- Adapter ABI may force SPEC v2 bump
- Asymmetric coverage during Phase 0A (advisory active; enforcement pending U11)

### Mitigation
- Hook overhead measured Phase 0A U3 + U11
- ABI fork decision documented Phase 0B finalization
- ADR-110 promotes after U11 confirms enforcement primitive needed

## References

- ADR-077 (WebFetch injection precedent), ADR-051 (SKILL SHA-pin), ADR-082 (mitigated rail)
- ADR-110 (codex pre-tool enforcement, PROPOSED)
- PLAN-075 spec.md v5 §11 (asymmetric VETO matrix)
- SPEC/v1/hook-io.schema.md L14 (PostToolUse never-blocks contract)
- .claude/hooks/check_mcp_response.py, .claude/hooks/_lib/injection_patterns.py
