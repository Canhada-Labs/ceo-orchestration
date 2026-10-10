---
id: PLAN-171-FOLLOWUP-batch-approval
parent: PLAN-171
title: Cerimônia de aprovação em lote e contrato do veredito do rail (W1 e ADR da W1b do PLAN-171)
status: draft
created: 2026-10-10
owner: CEO
depends_on: [PLAN-171]
level: L3
tags: [governance, ceremony, pair-rail, followup]
---

## Context

O PLAN-171 fechou na W0 em 2026-10-10. Duas peças saíram dele sem entrega e
vêm para cá:

- **W1 — batch-approval** (PLAN-171 §2, §5 e §7). A prática já existe: packs
  staged, dry-run em clone e um script `OWNER-*` com UMA assinatura GPG sobre um
  manifesto sha256. Falta codificar o schema do approval-queue, o corpo da
  cerimônia em PROTOCOL/skill e o invariante anti-lote-parcial. O gate DEVE
  recusar conjunto ≠ manifesto (lição do fix-forward `8a178f5`: gate que aceita
  run parcial é vácuo). Cada item do lote carrega evidência de dry-run
  individual; o lote não dilui o escrutínio V3. A §5 do pai amplia a W1 com o
  formato de veredito de pin único `delta_manifest`, no lugar de uma allowlist
  enumerada.
- **ADR da W1b — economia de revisores** (PLAN-171 §5 e §7). ADR curto,
  aceito por cerimônia: Codex = único revisor bloqueante do rail; Grok = gatilho
  (desacordo Claude↔Codex, L4/SPEC/release, auditorias periódicas). A metade de
  docs da W1b já está satisfeita (caixa no pai). As duas peças ficam juntas
  porque ambas definem o contrato do veredito do rail.

Histórico que este plano herda: a S353 propôs entregar a W1 pelo toolkit do
PLAN-188. O PLAN-188 está congelado desde 2026-10-01, e a W1 segue pelo molde
por onda (decisão Q13-c da S361).

## Goal

Um lote de canônicos landa por UMA cerimônia que recusa conjunto ≠ manifesto,
com veredito de pin único, e o papel de cada revisor do rail está num ADR aceito.

## Items

### W1 — batch-approval  [P1]  (canônico: cerimônia por onda)
- Schema do approval-queue commitado.
- Gate anti-lote-parcial com controle positivo: recusa conjunto ≠ manifesto.
- Um lote real landado pela cerimônia nova, com veredito de pin único
  `delta_manifest`.

### W2 — ADR da economia de revisores  [P1]  (canônico: ADR + cerimônia)
- ADR curto com o papel de cada revisor; docs de rail passam a dizer o papel
  real do Grok.
- Reconciliar com a regra vigente antes de escrever (ver OQ-1).

## Open questions

- **OQ-1.** A premissa da W1b, de 2026-08-11, é «Codex = único revisor
  bloqueante». A regra de operação da S361 (`CLAUDE.md` §5) exige Codex E dois
  refutadores Claude na MESMA rodada para um canônico ficar pronto para
  assinatura. O ADR registra a regra nova, a antiga, ou as duas com escopo?
  Resposta do Owner antes de `reviewed`.
- **OQ-2.** O custo fica a firmar no refinamento. A síntese de fechamento da
  S363 estima 1,2–2,2 M tokens em 6–10 sessões para todo o resto do PLAN-171,
  sem divisão por item.

## Success criteria

- [ ] Gate anti-lote-parcial recusa conjunto ≠ manifesto, com controle positivo vermelho→verde.
  Check: o teste do gate, nomeado na wave
- [ ] Um lote real landado pela cerimônia nova, com veredito de pin único `delta_manifest`.
  Check: `git log` do land + o `.asc` sobre o manifesto
- [ ] ADR da economia de revisores `ACCEPTED`, com a OQ-1 respondida.
  Check: `grep -l 'economia de revisores' .claude/adr/ADR-*.md`
