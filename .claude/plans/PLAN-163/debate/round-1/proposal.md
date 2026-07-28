---
plan: PLAN-163
round: 1
created_at: 2026-07-27
---

# PLAN-163 — Proposal (round 1)

Full plan: `.claude/plans/PLAN-163-substrate-uplift.md`

## Thesis

O framework está reconciliado com o substrato em **Claude Code 2.1.198**
(ledger) / 2.1.202 (verificação de schema), mas o CLI instalado é **2.1.220**
e desde junho a Anthropic lançou a família Claude 5 completa (Fable 5 já
adotado; **Sonnet 5** 30/06; **Opus 5** 24/07). Este plano reconcilia a janela
2.1.199–2.1.220 e adota o que beneficia o framework — com ênfase pedida pelo
Owner em **velocidade e paralelização de agentes** — em 6 threads e uma única
cerimônia canônica.

## Evidência-base (verificada)

- Verbatim CHANGELOG (4 claims criticas re-verificadas na fonte):
  - 2.1.214: "Fixed hooks with exit code 2 not blocking as documented when
    the hook's stdout JSON fails schema validation" → direção fail-closed;
    risco agora é block espúrio de hook com stdout fora de schema.
  - 2.1.212: Task tool `mode` deprecado/ignorado; subagente herda permission
    mode do pai.
  - 2.1.200: permission mode "default"→"Manual" (ambos aceitos).
  - 2.1.198: subagentes rodam em background por default.
- Inventário file:line do repo (agente repo-inventory S281): availableModels
  sem opus-5/sonnet-5; VETO floor allowlist {opus-4-8, fable-5}; cap interno
  N≤6 (PLAN-083, contenção flock) vs fan-outs de 8; zero uso de agent
  teams/fast mode; nenhum gate de versão de CLI no install/upgrade (advisory
  by design via substrate-watch).
- Skill claude-api 2.1.220: opus-5 $5/$25 drop-in, bucket de rate-limit
  separado, xhigh; sonnet-5 tokenizer +30%; fast mode Opus 5/4.8 apenas;
  opus-4-1 retira 2026-08-05.

## Decisões propostas (draft, a debater)

1. **T1 Model refresh**: availableModels/parity/cost/routing += opus-5 e
   sonnet-5; VETO_FLOOR_ALLOWED += opus-5 (ADR-149 amend); debate/arch →
   opus-5; advisory PERMANECE sonnet-4-6 até re-baseline do tokenizer
   (sonnet-5 vira permitido já); fix de 4 scripts com default opus-4-7 stale
   + team.md:589; deprecations refresh (opus-4-1!); ADR-181.
2. **T2 Conformidade de hooks**: oracle novo `hook-stdout-schema-check`
   (44 hooks, caminhos allow E block — o fix 2.1.214 pune JSON inválido com
   block espúrio); re-extração de schema do binário 2.1.220 e diff vs
   2.1.202; prova de independência do `mode`; probe do MCP auto-background
   >2min vs matchers mcp__codex__*.
3. **T3 Novos eventos**: hook novo `check_directory_added.py` (audit-only
   default; hardblock opt-in) — mudança de perímetro via /add-dir hoje é
   invisível à governança; wiring `Notification` (agent_needs_input/
   agent_completed) alimentando telemetria de liveness. settings 46→48
   registrations (canônico).
4. **T4 Paralelização/velocidade**: re-medição da contenção flock do
   audit-log no substrato 2.1.220 (que ficou 7×/79× mais eficiente em
   tool-rounds/transcript) → decidir cap 6→8 pelo NÚMERO; ADR de doutrina
   async-subagent (default async + caps nativos 20/200/depth-3); pin
   conservador CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1 até probe provar
   cobertura do spawn-guard em depth≥2; re-verificar Workflow opts.model.
5. **T5 Ledger/pins**: substrate-watch → 2.1.220 + SDKs; pin codex
   0.144.1→0.144.6 via cerimônia ADR-111 + re-record de fixtures + checklist
   ADR-161; grok probe; defaultMode "manual"; novas settings de postura
   expostas comentadas nos templates.
6. **T6 Docs/counts**: doc datado de adoção de substrato; fast-mode guidance;
   verify-counts + COMMAND-SKILL-HOOK-MAP regen; CLAUDE.md só no closeout.

## Open questions (candidatas a tie-break do Owner)

- OQ1 profundidade do refresh Opus 5 (allowlist-only vs refresh completo de
  routing/fallback/VETO-floor). Draft: completo.
- OQ2 advisory default → sonnet-5 agora vs pós re-baseline de tokenizer.
  Draft: permitir já, migrar default só pós-medição.
- OQ3 nesting depth: pin=1 vs depth-3 com probe. Draft: pin=1.
- OQ4 agent teams/SendMessage: adotar vs documentar postura. Draft: documentar.
- OQ5 settings de postura (disableAutoMode, strictAllowlist) nos templates:
  forçar vs expor comentado. Draft: expor comentado.
- OQ6 fast mode: guidance no ACCELERATORS.md vs silêncio. Draft: guidance.

## Sequência

W0 debate → W1 red-first (oracle hooks, diff de schema, medição flock,
probes) → W2 edits mecânicos não-canônicos → W3 pack canônico (settings,
hooks novos, ADRs, pin codex) via staged + pair-rail + cerimônia GPG →
W4 closeout (ledger, docs, counts, Validate).
