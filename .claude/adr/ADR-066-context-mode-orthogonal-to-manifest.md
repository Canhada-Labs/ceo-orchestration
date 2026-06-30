---
id: ADR-066
title: Context-mode as orthogonal capability to Manifest (not redundant)
status: ACCEPTED
created: 2026-04-21
accepted: 2026-04-21
proposed_by: CEO
accepted_by: CEO
related_plans: [PLAN-026, PLAN-046]
related_adrs: [ADR-062]
blast_radius: L2-narrow
---

# ADR-066 — Context-mode is orthogonal to Manifest

## Context

PLAN-026 SOTA external audit (Session 34, 2026-04-18) inicialmente
classificou `context-mode` (pattern de alexpate/awesome-context) como
overlap/redundante com o Manifest pattern (ADR-062 LightRAG sidecar
MCP). Re-auditoria Session 39 (PLAN-046 Cluster 1.2) revelou
mis-classification: context-mode é **preservação de contexto**
enquanto Manifest é **compressão de custo**. Ortogonais, não
redundantes.

## Decision

Adotar context-mode como capability ortogonal ao Manifest. Não se
substituem:

- **Manifest (ADR-062 LightRAG sidecar)** — semantic compression
  sobre corpus grande para reduzir token cost per turn. Output:
  compressed summary.
- **Context-mode** — preservação literal de slices críticos de
  contexto (ex: last-N messages, specific file patches) sem
  compression, com budget-aware truncation. Output: raw but
  bounded context.

Ambos podem (e frequentemente devem) operar simultaneamente no
mesmo session: Manifest para background corpus + context-mode
para hot-path slices.

## Consequences

**Positive:**
- Framework pode shippar ambos as capabilities independentemente
- Adopters escolhem per-session config (ambos ligados, só Manifest,
  só context-mode, ou nenhum)
- Sem ambiguidade de "qual usar quando"

**Negative:**
- 2 capabilities para documentar em adopter guide
- Potencial para double-spend de context budget se não bem
  configurado

## Blast radius

Documentação + roadmap. Nenhum code change imediato (PLAN-046
Cluster 1.2 é doc-only). Wave 2 do PLAN-046 implementa opt-in
context-mode em `.claude/hooks/_lib/context_mode.py` (future).

## Alternatives considered

1. **Merge into Manifest** — rejected: concerns diferentes, API
   seria confusa.
2. **Abandon context-mode** — rejected: gap real identificado no
   re-audit; ausência afeta quality em sessões long-horizon.

## Related

- PLAN-046 Cluster 1.2 — implementation roadmap
- ADR-062 — Manifest via LightRAG sidecar
- PLAN-026 — SOTA external audit (Session 34 original classification +
  Session 39 re-audit correction)

## Acceptance history

- **2026-04-21 Session 49 P04** — flipped `PROPOSED → ACCEPTED`.
  CEO-synthesis debate round-1 at
  `.claude/plans/PLAN-046/debate/round-1/ceo-synthesis.md` documents
  the trade-off analysis (3 options considered; Option A selected).
  Canonical edit landed under round-12 canonical-edit sentinel
  (ADR-066 path explicitly listed in
  `.claude/plans/PLAN-045/architect/round-12/approved.md` §Scope).
- **Blast radius at acceptance:** still L2-narrow. No code paths
  wired; capability is declared + documented in
  `docs/ecosystem-parity/cluster-1.2-context-mode.md`.
  Implementation is opt-in per-adopter (future PLAN-046 wave).

## Enforcement commit

`8fb5704fb703` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
