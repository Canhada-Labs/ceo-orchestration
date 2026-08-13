---
plan: PLAN-178
round: 1
created_at: 2026-08-13
---

# PLAN-178 — Proposta para debate round 1

Plano completo: `.claude/plans/PLAN-178-mast-audit-substrate-adoption.md`
Referências: `.claude/plans/PLAN-178/research-S305.md`
Evidência W0 (já executado): `.claude/plans/PLAN-178/mast-coverage-table.md`

## Tese

A pesquisa S305 (academia vs framework) mostrou que o framework já
implementa a versão forte da maioria das arquiteturas multi-agente da
literatura; os gaps reais são quatro e cabem num plano L2/L3 curto. O
W0 (auditoria MAST-14 + injeção inter-agente, read-only) JÁ RODOU e
produziu 6 coberto / 10 parcial / 4 gap + 7 achados transversais.
Este debate cobre o Gate 3 para as waves EXECUTÁVEIS (W1-W3) e o lote
de curas derivado do W0.

## Escopo em debate

1. **W1 — adoção de substrato 2026** (cada item com probe live-fire
   primeiro):
   - W1.1 migrar 1 fan-out piloto para Workflow determinístico, GATED
     em positive control de `check_agent_spawn` no caminho Workflow
     (se não disparar → gap, migração bloqueada).
   - W1.2 cost-attribution nativa consumida pelo agent-budget (duas
     fontes lado a lado por 1 janela; switch só após divergência <10%).
   - W1.3 scoped permissions nativas em spawns [L3 — toca settings] —
     candidata a fechar o achado P1 "FILE ASSIGNMENT não é capability
     em write-time" (INJ-4) mais barato que hook novo.
   - W1.4 nested subagents + agent teams: ESTUDO read-only (teams
     full-mesh FORA — MAST + lição S284).
2. **W2 — regras derivadas**: critic fresco por retry nos re-passes
   Claude-side (cura do gap EXTRA-3.4); barra-por-exemplar para
   superfícies de prosa; fronteiras registradas (sem double-booking
   com PLAN-172).
3. **W3 — estudo dreaming/curadoria de memória** vs PLAN-154
   (read-only; ativação = decisão do Owner).
4. **Lote de curas W0** (a decisão deste debate é O QUE entra e em que
   ordem):
   - C1 [P1] FILE ASSIGNMENT: fazer o hook cumprir a claim de
     CLAUDE.md:88 (enforce no spawn) — e avaliar enforcement
     write-time (ou delegar ao W1.3).
   - C2 [P2] fence + cap do ingest in-harness nos consumidores de
     Workflow (audit-fanout.js:142,190-196; nightly-hygiene) — mesmo
     padrão do council.
   - C3 [P2] lint de vacuidade: todo `check_*` do ceo-boot precisa de
     caminho red alcançável + positive control (caso vivo:
     check_tier_a_spec_version_drift, ceo-boot.py:1017).
   - C4 [P3] drift de referência ceo-boot.py:240 (_lesson_render_safe
     → _validate_boot_lesson).
   - C5 [decisão por item] armar ou não os detectores advisory
     (CEO_CONFIDENCE_ENFORCE, CEO_SUBAGENT_FABRICATION_BLOCK,
     CEO_VERIFY_AFTER_EDIT_BLOCK, CEO_SPAWN_TOOL_SCOPE,
     CEO_SPAWN_OVERLAP_GUARD, CEO_UNICODE_HARDBLOCK).

## Decisões já tomadas (não re-litigar)

- Teams full-mesh NÃO entra (MAST: coordenação = 79% das falhas;
  lição S284 clobber).
- Números de literatura só em research-S305.md (doutrina §3/PLAN-172).
- Dono único: cascata→172/176; context-reframe→175; best-of-N
  gate→172 §2.
- INJ-3 (memória compartilhada) permanece risco aceito ADR-089; o
  debate só decide se o gatilho de reabertura ganha o vetor
  escrita-mesmo-plano.
- Owner autorizou trabalho pré-rc.4 (S305); freeze relaxado por
  decisão dele.

## Open questions para os críticos

- OQ-1: C1 — enforce no spawn (barato, fecha a claim) vs enforcement
  write-time (fecha INJ-4 de verdade, mais caro) vs W1.3 nativo?
  Sequência?
- OQ-2: C5 — quais detectores armar primeiro, com que critério de
  falso-positivo?
- OQ-3: W1.1 — qual fan-out piloto? (candidato: re-pass de release;
  alternativa: audit-fanout já é Workflow — o piloto seria outro)
- OQ-4: emendas de W2 são advisory-até-ratificação — precisam de
  cerimônia própria ou PR normal basta?
