---
id: ADR-109
title: Codex SKILL.md Re-Hash Protocol — Format B Compatibility for Cross-LLM
status: ACCEPTED
proposed: 2026-05-04
related_plan: PLAN-075
related_adr: [ADR-051, ADR-105, ADR-106]
accepted_at: 2026-05-08
accepted_by: S96
enforcement_commit: __FILLED_AT_COMMIT__
---

# ADR-109 — Codex SKILL.md Re-Hash Protocol

## Status: ACCEPTED — Phase 0A U1 gate met (30/30 format + 30/30 semantic accuracy)

## Context

ADR-051 specified Format B SKILL REFERENCE pattern: spawn prompt contains
`## SKILL REFERENCE @<path> sha256=<hex>`; sub-agent Reads file post-spawn;
PostToolUse observer `check_skill_reference_read.py` re-hashes for forensic.

Format B was designed against Claude sub-agents. Codex MCP unknown:
- Does Codex respect "Read this file" instruction?
- Does Codex compute SHA-256 correctly?
- Does Codex report it back in response?

Phase 0A U1 falsifies these. This ADR documents the protocol Codex MUST follow
to participate as Tier B sub-agent.

Round 1.5 Codex critique R1.5-7 hardened U1: N=10 with ≥80% threshold was too
weak for a mechanical (non-inferential) property. v5 raises U1 to N=30 with
100% accuracy required, split into U1a (format compliance) + U1b (semantic
accuracy).

## Decision

### Codex SKILL re-hash contract

Codex spawn prompt MUST contain:

```
## SKILL REFERENCE
@<repo-relative-path> sha256=<64-hex>

(Sub-agent: Read this file via the Read tool to load the full
<skill-name> skill. The PostToolUse observer check_skill_reference_read.py
will re-hash and emit a forensic breadcrumb. The skill content is
the authoritative source — this prompt only references it.

CODEX-SPECIFIC: in your response, INCLUDE the SHA-256 you computed
after Reading the file, in a section: ## SKILL VERIFICATION
sha256_computed=<hex>. The framework requires this for ADR-109 compliance.)
```

Codex response MUST contain:

```
## SKILL VERIFICATION
sha256_computed=<64-hex>
```

`check_codex_response.py` parses this section, compares to declared SHA in spawn prompt:
- Match: emit `skill_verification_passed` audit event
- Mismatch: emit `skill_verification_failed` audit event + advisory flag for next gate (ADR-106 / ADR-110)
- Missing section: emit `skill_verification_missing` + retry once with explicit instruction

### Phase 0A U1 acceptance (v5 hardened)

N=30 runs with valid Format B prompts (was N=10 v4 — Codex R1.5-7 hardening):
- **U1a Format compliance**: 100% on N=30 (mechanical property requires 0 fails)
- **U1b Semantic accuracy**: SHA matches actual file SHA on 100% of N=30
  - Match: Format B SUPPORTED for Codex
  - Any miss: Format B NOT SUPPORTED; Codex spawns ALWAYS use Format A inline

### Format A fallback for Codex

If Format B not supported (U1 any fail): all Codex spawns use Format A inline
(full SKILL.md content embedded). Cost: larger prompts (5-15k more per spawn).
Benefit: deterministic skill content delivery.

## Consequences

### Positive
- Format B SHA-pin invariant preserved structurally
- Falsifiable empirical gate (Phase 0A U1)
- Graceful degradation to Format A if Codex flunks
- v5 statistical power upgrade (N=30, 100% threshold)

### Negative
- Adds `## SKILL VERIFICATION` section to spawn prompts and Codex responses
- Format A fallback path means larger Codex prompts (token cost +)
- One more validation surface in `check_codex_response.py`

### Mitigation
- ADR-051 §Sentinel format pattern reused (no invention)
- Audit event types for verification ops added to AUDIT-LOG-SCHEMA v2.17
- Format A fallback documented as fallback_provider trigger in routing-matrix.yaml

## References

- ADR-051 (SKILL SHA-pin)
- PLAN-075 spec.md v5 §6 U1
- .claude/hooks/check_skill_reference_read.py (existing observer)
