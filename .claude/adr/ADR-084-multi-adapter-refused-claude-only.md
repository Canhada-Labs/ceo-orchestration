# ADR-084 — PLAN-057 multi-adapter expansion REFUSED — Claude-only by design

## Status

SUPERSEDED — by ADR-105 (Multi-LLM Sub-Agent Rail, 2026-05-04). Original ACCEPTED at Wave A re-ceremony 2026-04-27 — round-21 sentinel — Owner key 0000000000000000000000000000000000000000. ADR-105 reversed the Claude-only stance when marginal cost for multi-LLM became ~zero and Codex MCP demonstrated GPT-5.5-codex parity.

**Superseded-By:** ADR-105

## Context

PLAN-057 was drafted Session 60 (2026-04-24) as L3 expansion shipping
3 new adapters (Gemini, OpenAI, Local) + 1 refused-ADR (Sandbox).
Estimated 18-25 dev-dias + 2 sprints. The trigger was the Session 60
landscape audit revealing 100% of mainstream orchestrators
(CrewAI, LangGraph, MS Agent Framework, OpenAI Agents SDK, Google ADK,
Semantic Kernel, Portkey) are model-agnostic; ceo-orchestration
appeared to be in "model-agnostic parcial" gap.

### What changed (Session 67 Owner directive, 2026-04-27)

Owner reframed the framework's positioning explicitly:

> "meu foco é puro no claude da antropic, pode deixar plano de outras
>  ias para outro momento, vamos terminar o ceo orchestration e deixar
>  SOTA para o claude. Tem que ser o melhor orchestrator do claude"

This is a **strategic positioning decision**, not a scope cut for
deadline reasons. The claim is:

- ceo-orchestration is **THE Claude-only orchestrator**.
- Multi-LLM agnosticism is a feature *for orchestrators that target
  enterprise CTOs choosing among providers*. ceo-orchestration's
  thesis is that depth of integration with one vendor (Anthropic
  Claude + Claude Code harness + MCP + Agent SDK + permissions
  + hooks + signed sentinels) **outperforms breadth across vendors**
  for the specific use case of governed agentic engineering work.
- 14 of our 22 capabilities (per Session 60 matrix) are **already
  Claude-stack-specific** (canonical-edit sentinel, hook governance,
  permission gates, MCP scanner, Skill protocol, debate per
  ADR-058, audit HMAC chain, conformance TLA+, etc.). Adding
  Gemini + OpenAI + Local adapters would either:
  - (a) drop those 14 capabilities for non-Claude paths (loses
    differentiation), OR
  - (b) reimplement them per-vendor (3-4× maintenance burden, no
    proven uplift, vendor-specific bugs cross-pollinate).

Both options weaken the SOTA claim.

## Decision

**REFUSE PLAN-057 entirely** with reason `(b) cost-exceeds-benefit`
per the refused-ADR taxonomy (PLAN-051 §3.1).

Specifically:

1. **Delete `.claude/hooks/_lib/adapters/gemini.py` stub** — it has
   never had a real implementation. Keeping a dead stub signals
   uncertainty about the Claude-only thesis. Source of truth is
   `.claude/hooks/_lib/adapters/claude.py` (production).
2. **Retire ADR-054 cross-adapter fixtures pattern** — without
   multi-adapter, fixture parity infrastructure is unused. ADR-054
   stays as historical record but acceptance criteria becomes
   "single adapter (Claude)".
3. **Update README + GOVERNANCE.md** to state Claude-only as a
   design decision (not a gap), citing this ADR.
4. **Memory pointer** `memory/project_framework_landscape_2026_04_27.md`
   updated with the Claude-only thesis (Session 67 amendment).

### What ceo-orchestration IS (positive framing)

- The most opinionated **Claude orchestrator** available.
- Deep integration with: Claude Code CLI hooks, MCP, permission_mode,
  signed sentinels, audit-log HMAC, TLA+ conformance harness, skill
  protocol, debate-per-ADR-058, governance via Owner-signed sentinels.
- Designed for engineering teams who choose Claude and want
  production governance + dogfooding + SOTA.
- Surface area trade: **breadth (multi-LLM) traded for depth
  (Claude-stack-specific guardrails + provenance + governance)**.

### What it is NOT

- Not a Portkey / LiteLLM / OpenAI-agnostic router.
- Not a vendor-comparison sandbox.
- Not a generic LLM workflow engine.

## Consequences

### Positive

- Narrative is sharp: "Claude-only orchestrator with the deepest
  governance integration available". Easier to position.
- Maintenance burden remains 1-vendor (Anthropic Claude). No
  cross-vendor bug surface.
- All 14 Claude-specific capabilities are first-class without
  per-vendor reimplementation.
- Removes 18-25 dev-dias from roadmap permanently.
- Owner directive matches reality: 100% of dogfood and 100% of
  test coverage runs on Claude — adding adapters would have been
  speculative, not validated.

### Negative

- Adopters who want Gemini/OpenAI must use a different orchestrator.
  This is acceptable; the framework is opinionated.
- 1 of 5 capabilities-in-paridade gap (model-agnostic) becomes a
  permanent intentional gap. README and adopter docs must say so
  clearly.
- ADR-054 cross-adapter fixtures pattern is unused. Historical
  record only.

### Neutral

- Existing `claude.py` adapter remains the production path (no
  change). Removal of `gemini.py` stub is a single-file deletion.

## Alternatives considered

### A. Ship Gemini-only (Phase 1 of PLAN-057) (REJECTED)

Cost ~5-7 dev-dias. Rejected because:
- Half-step that adds complexity without resolving multi-LLM thesis.
- Gemini stub has never been validated; building it now means new
  contract surface to maintain.
- Adopter audience asking for Gemini specifically is hypothetical
  (no concrete adopter request).

### B. Defer entire PLAN-057 indefinitely (REJECTED)

"Defer" leaves the question open. Better to refuse explicitly so
adopters and future-CEO know the framework's positioning is
intentional Claude-only.

### C. Build adapter-pattern infrastructure without specific vendors (REJECTED)

Just abstraction, no concrete second adapter. Rejected: YAGNI;
abstraction without 2nd consumer is speculative.

## Enforcement commit

To be filled in at Session 67 closeout (this ADR's promotion to
canonical path lands in the same commit as the gemini.py stub
deletion + README/GOVERNANCE.md updates).

## References

- PLAN-057 — Multi-adapter plan (refused via this ADR)
- ADR-054 — Cross-adapter fixtures (status note: unused post-refusal)
- PLAN-051 §3.1 — Refused-ADR taxonomy (this ADR uses reason `b`)
- PLAN-056 — Framework Landscape closeout (sister deliverable
  Session 67; updates Claude-only narrative in compat matrix)
- Memory `project_framework_landscape_2026_04_27.md` — landscape
  with Claude-only thesis amendment.
