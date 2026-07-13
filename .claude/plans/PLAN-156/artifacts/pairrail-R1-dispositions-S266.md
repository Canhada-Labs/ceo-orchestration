# PLAN-156 — Codex pair-rail R1 (plan review) + disposições (S266)

Invocação: `codex exec review --uncommitted` (codex-cli 0.139.0) sobre o
draft do PLAN-156 + proposal do debate. Veredito R1: gaps de
governança/segurança a corrigir antes de aceitar como contrato de
execução. **3 findings, todos P2, todos ACEITOS e aplicados.**

| # | Finding (P2) | Disposição |
|---|---|---|
| 1 | Grok council lane usava hooks (fail-open) como sandbox — circular; exigir contenção read-only nativa/OS ou `STATUS: unavailable` | ACEITO — convergente com o must-fix do VP-Eng do debate R1. Wave 6 reescrita: OS-containment obrigatório no lane grok (gate = lacuna (e) do Wave 0), hooks profile só defense-in-depth, degradação 2-lane fail-loud. Mini threat model adicionado. |
| 2 | Wave 0 listava lacunae (a)-(e) mas o shard tem também flags não-confirmadas e o double-fire native+legacy | ACEITO — lacunae (f) `--cwd`/`--permission-mode` e (g) double-fire probe adicionadas ao Wave 0; coexistência forçada reconhecida como caso projetado (não só probe). |
| 3 | Plano L3 sem `spec.md`/`spec_ref` (ADR-058 / pre-plan-brainstorm) | ACEITO — spec escrita; `spec.md` é caminho ADR-010-guardado → draft verbatim em `PLAN-156/artifacts/spec-draft-S266.md`, `spec_ref:` no frontmatter, promoção canônica sob o sentinel do Wave 0. |

Ajustes adicionais do debate R1 (VP-Eng, ADJUST) aplicados no mesmo
passe: exit-2 wrap movido do dispatch Python para o **shim shell**
(cobre crash de interpretador/import/sinal) com positive-control
parametrizado por matcher no CI; base de contagem de audit actions =
golden live (320 no drafting), não constante; dependência W1→W6
desenhada; concessão registrada na spec: Wave 6 desliza para plano
próprio sem bloquear W0-W5 se o round 3 mantiver objeção.

R2 do pair-rail roda após o consenso do debate (round 2/3) sobre o
texto final do plano.
