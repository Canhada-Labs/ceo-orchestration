---
id: PLAN-169-FOLLOWUP-quota-resume-and-probes
title: Quota-resume, probes W4.2.0 e marcador do 12º site
status: draft
created: 2026-09-15
owner: CEO
depends_on: [PLAN-169]
---

## Context

O PLAN-169 fechou `done` em 2026-09-15 com o GA v1.4.0 publicado (AC-8). Três
critérios do plano-pai NÃO tinham relação com o trem de release e seguiam
abertos; migram para cá em vez de segurar o fechamento de um plano cuja razão de
existir — publicar v1.3.0 e v1.4.0 — está cumprida.

## Goal

Fechar os três critérios remanescentes do PLAN-169 com a evidência que cada um
exige.

## Items

### AC-4 [P1] — Quota-resume

- Probes W4.1.0 registrados; simulação com job ÚNICO no horário efetivo
  (`resets_at + ≥120s`, minuto ∉ {:00, :30}) + live-fire real **OU** registro
  falsificável de por que não foi possível.
- Kill-switches provados: `CEO_QUOTA_RESUME=0` e `CEO_SOTA_DISABLE=1`.
- O gate de postura lê a postura EFETIVA; a doc promete exatamente o que o teste
  provou; envs novas entram em `env-inventory.json` no MESMO commit.

### AC-5 [P1] — Probes W4.2.0 (a–f)

- Registrados com evidência: um peer tenta induzir edição canônica via
  `SendMessage` ⇒ BLOQUEADO, com evento HMAC de campos whitelisted
  (checklist R-SEC9).
- Com `refuse`: nenhum turno nasce (controle positivo: com `accept`, nasce).
- Doutrina em ADR, incluindo a decisão sobre visibilidade de tentativas recusadas.

### AC-7 [P1] — Marcador do 12º site

- Controle plantado VERMELHO + bump 1.4.0 real VERDE — as duas evidências.
- Nota: o bump real do GA correu em 2026-09-15 e foi **no-op** (VERSION já
  estava em 1.4.0, quatro oráculos limpos), o que satisfaz a perna verde apenas
  se a evidência do no-op for aceita como tal; o controle vermelho continua por
  produzir.

## Open questions

- **OQ-1.** AC-7 pode fechar com a evidência do bump no-op do corte do GA, ou
  exige um bump real com mudança de versão (o que só acontece na 1.4.1)?
- **OQ-2.** AC-4 exige live-fire de quota, que depende de uma janela real de
  esgotamento. Vale esperar a próxima ocorrência natural ou registrar a
  impossibilidade?

## How to continue

> Ler este arquivo e o PLAN-169 (`done`) para o contexto dos três critérios.
> Responder OQ-1 e OQ-2. Nenhum dos três está no caminho crítico de release.

## Success criteria

- [ ] AC-4 fechado com evidência ou impossibilidade registrada de forma falsificável
- [ ] AC-5 fechado com controle positivo e negativo
- [ ] AC-7 fechado com as duas evidências (ou OQ-1 resolvida)
