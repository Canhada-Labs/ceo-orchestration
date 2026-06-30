---
id: ADR-105
title: Multi-LLM Sub-Agent Rail — Coordinated Supersede of ADRs 084 + 085 + 096
status: ACCEPTED
proposed: 2026-05-04
related_plan: PLAN-075
supersedes: [ADR-084]
amends: [ADR-085, ADR-096]
related_adr: [ADR-052, ADR-082, ADR-093, ADR-103, ADR-106, ADR-107, ADR-108, ADR-109, ADR-110]
cap_consumed: false
accepted_at: 2026-05-09
accepted_by: S96-cont-2 v1.13.x patch
enforcement_commit: __FILLED_AT_COMMIT__
---

# ADR-105 — Multi-LLM Sub-Agent Rail — Coordinated Supersede

## Status: ACCEPTED — Phase 0A SPIKE-VERDICT.md GO (S96-cont-2 v1.13.x patch; Codex MCP gate confirmation #32)

## Context

ADR-084 (2026-04-27) ACCEPTED multi-adapter framework REFUSED with Claude-only thesis.
ADR-085 (same date) ratified Claude-only landscape.
ADR-096 (2026-04-29) declared vibecoder-only Claude-only by design.

All three under cost-bound assumptions (single $200 plan). Owner 2026-05-04
reports: $200 Anthropic + $200 OpenAI Pro plans active. Marginal cost ~zero.

Codex MCP exposed Claude Code 2026-05-04. GPT-5.5-codex empirical: parity with
Opus 4.7 on SWE-bench Verified, HumanEval+, LiveCodeBench. S75/S76/S79 baseline:
Codex CLI gate caught 4+5+1 P1s missed by 4 Claude archetypes + Code Reviewer.

Round 1 debate (2026-05-04): 5/5 archetypes flagged 4 BLOCKERS + 10 critical.
v4 incorporated. Round 1.5 Codex critique: GO-WITH-7-ADJUSTMENTS; v5 incorporated.

## Decision

**Coordinate-supersede 3 ADRs in single amendment:**

### ADR-084 — Selectively Unblocked (SUPERSEDED)

ADR-084 ACCEPTED state retained for **multi-adapter framework as full design**
(N providers, dynamic routing, ML-optimization). That premise remains REFUSED:
ADR-096 vibecoder-only stack does not justify it.

ADR-084 IS superseded for the **narrower scope**: Codex MCP as second sub-agent
provider in Tier B only. CEO Tier A remains Claude-only. Scope:
- Codex peer review at L3+ (Phase 4)
- Codex coder for narrow archetypes (Phase 5, conditional U2 pass)
- Cross-LLM VETO floor extends ADR-052 (ADR-108 PROPOSED, conditional U7)

### ADR-085 — Refined to Tier-Differentiated (AMENDED)

- **Tier A (CEO orchestrator)**: Claude-only, NON-NEGOTIABLE, structurally enforced via _probe_architect
- **Tier B (sub-agent provider)**: Claude + Codex peer rail (this ADR-105)

The "Claude-only thesis" continues to apply to Tier A and to all governance.
Does NOT apply to sub-agent execution.

### ADR-096 — Amended Risks (AMENDED)

ADR-096 §README §Risks gets one new bullet:

> "Codex MCP integration in Pair-Rail (PLAN-075/v1.13.0+) is a vibecoder-stack
> capability for the maintainer's personal stack. Adopters running ceo-orchestration
> in Tier 2/3/4 environments (small-team / regulated / enterprise) should set
> CEO_PAIR_RAIL_DISABLE=1 until validated against their threat model. Pair-Rail
> is NOT an adopter promise; it is opt-in for vibecoder mode."

## Cap disposition (ADR-093)

ADR-093 §per-plan-refusal-cap (≤2 refusals per plan): **NOT consumed**.
This ADR-105 is **re-acceptance with refined scope**, not a refusal.

ADR-093 §60d-moratorium: ALREADY superseded by ADR-103.

## Round 1 + Round 1.5 cross-LLM debate context

This ADR vetted via **two cross-LLM debate rounds** (the very mechanism Pair-Rail installs):

- Round 0 (Codex MCP): NO-GO on v1 mirror Pair-Rail; 6 forced adjustments → v3
- Round 1 (4 Claude archetypes + Codex): 5/5 NO-GO; 4 BLOCKERS + 10 critical → v4
- Round 1.5 (Codex review of v4): GO-WITH-7-ADJUSTMENTS → v5

Empirical: 4 Claude archetypes had partial overlap with Codex Round 0; Codex
Round 1 flagged unique cluster (capability matrix fallback). Codex Round 1.5
flagged 7 unique findings after v4 — confirming structural same-LLM bias even
at v4 stage. This is the pattern S75/S76/S79 documented and the rationale this
ADR resolves.

## Consequences

### Positive
- Cross-LLM peer review structural in Tier B (mitigates same-LLM bias)
- ADR-052 VETO floor preserved (Claude Opus authority); Codex peer adds advisory perspective
- Vibecoder-only stack preserved (ADR-096 Tier 1 caveat explicit)
- ADR-093 cap not consumed

### Negative
- New attack surface: Anthropic→OpenAI trust boundary
- New dependency: OpenAI Pro plan / API key rotation governance
- Hook coverage assimétrica residual (mitigated by ADR-106 + ADR-110)
- Adopter education burden (Tier 2/3/4 must opt out)

### Mitigation
- ADR-106 hook coverage choice (PostToolUse matcher extension; advisory)
- ADR-107 Pair-Rail mandatory L2+ + asymmetric VETO matrix
- ADR-108 (PROPOSED, conditional U7) — cross-LLM VETO floor
- ADR-109 — Codex SKILL re-hash protocol (U1 falsifiability)
- ADR-110 (PROPOSED, conditional U11) — pre-tool Codex enforcement
- ADR-077 redux: check_codex_response.py PostToolUse scanner

## Phase 0A Empirical Gate

This ADR remains DRAFT until Phase 0A spike emits SPIKE-VERDICT.md GO. If
spike NO-GO on ≥3 unknowns: ADR-105 reverts to PROPOSED-DRAFT; scope reduces
to Adversarial Codex Read-Only (PLAN-076 stub); ADRs 084+085+096 retain
ACCEPTED state unchanged.

## References

- PLAN-075 spec.md v5 §10 (capability matrix), §11 (asymmetric VETO matrix)
- ADR-084, ADR-085, ADR-096
- ADR-093 (cap disposition), ADR-103 (calendar gate purge), ADR-052 (VETO floor), ADR-082 (mitigated rail)
- S75/S76/S79 empirical baseline
- .claude/plans/PLAN-075/debate/round-1/consensus.md
