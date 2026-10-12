---
id: PLAN-186-FOLLOWUP-seat-fable51-row
parent: PLAN-186
title: "Resíduo da 4.ª linha do AC-1: assento `claude-fable-5-1`, 207 turnos medidos contra 660 publicados"
status: draft
created: 2026-10-12
owner: CEO
depends_on: [PLAN-186]
level: L2
budget_tokens: 60-120k (contexto do CEO; medição só de leitura sobre transcripts + 1 relatório)
budget_sessions: 1
context_risk: low
external_wait: "PLAN-SCHEMA §1.4: não entra em `executing` antes de o PLAN-186 ficar `done` (gatilho: `grep -m1 '^status:' .claude/plans/PLAN-186-orchestrator-operating-model.md` responde `status: done`). O PLAN-186 ainda depende de cerimônias GPG do Owner."
eta_calendar: "quando o PLAN-186 ficar `done` (max das esperas externas); ver a OQ-1 sobre o corpus"
tags: [finops, instrumento, ac-1, followup, plan-186]
---

# PLAN-186-FOLLOWUP-seat-fable51-row — a 4.ª linha da tabela do AC-1

## Context

**Linhagem (PLAN-SCHEMA §1.4, «parent shipped with explicit deferred AC items»).** O AC-1 do
PLAN-186 fechou `[x]` na S344 sobre os três modelos que o seu texto enumera. A 4.ª linha da
tabela citada ficou fora como resíduo declarado. Na S347 o Owner escolheu, verbatim, «Manter
(a), fechado (Recomendado)», com o efeito registrado em
`PLAN-186/debate/owner-decisions-S347.md:40`: «a 4.ª linha (assento `claude-fable-5-1`,
207×660) vira follow-up nomeado». Este arquivo é esse follow-up. Ele não reabre o AC-1.

**O resíduo, como está em disco:**

- O relatório publica, para o assento `claude-fable-5-1`, **660 turnos e USD 562,60**
  (`docs/research/s339-orchestrator-study/05-finops-routing.md:203`).
- O instrumento shipado, na janela fechada do próprio relatório, devolve **207 turnos** de
  assento para esse id, com 0 de 5 células iguais. Somando assento e subagente, o id chega a
  **494 turnos / USD 264,70**, ainda 166 turnos e USD 297,90 abaixo. Logo, a hipótese de
  rotulagem assento/subagente está refutada (Progress log do PLAN-186, entrada S344 do AC-1).
- Antes, na S339, a versão de então do instrumento, sem limite superior (só
  `2026-08-03T00:00Z` como limite inferior), mediu **295 turnos / USD 231,93**
  (`.claude/plans/PLAN-186/w0/instrument-S339.md` §4).

## Goal

Dizer, com medição reproduzível, por que a linha `claude-fable-5-1` do assento não
reproduz, ou declarar por escrito que a causa deixou de ser mensurável.

## Approach — três hipóteses, cada uma com um teste que a derruba

- **H1 — chave de dedup.** O relatório deduplica por `(requestId, apiBlockIndex, message.id)`;
  o instrumento, por `message.id`, com recuo para `requestId` + `uuid`. O
  `instrument-S339.md` §4 diz que 100 % do uso de `claude-fable-5-1` no assento mora nos 2
  arquivos mais novos do corpus, os únicos com `apiBlockIndex`. Já a docstring do instrumento
  (`.claude/scripts/ceo-cost-transcripts.py:78-81`) diz que `apiBlockIndex` não foi observado
  no esquema em disco. Os dois textos discordam. O teste conta os registros desse id nos
  arquivos de assento da janela sob as duas chaves.
- **H2 — a coluna de turnos da tabela publicada não fecha.** As 4 linhas somam
  8.248 + 4.968 + 660 + 169 = 14.045 turnos, e o total publicado é 14.148 (diferença de 103).
  As colunas de tokens e de USD fecham exatamente. Ou há turnos fora das 4 linhas, ou uma
  célula (a 660 ou o total) é erro de transcrição. O teste recompõe a contagem por modelo sob a reconstrução
  deliberada do defeito, que na S343 atingiu exatamente o total de 14.148.
- **H3 — o corpus mudou desde 2026-09-02.** Arquivos removidos ou reescritos entre a
  medição do relatório e as re-medições. `.claude/settings.json:861` declara
  `cleanupPeriodDays: 90`. O teste lista os arquivos de assento com registros de
  `claude-fable-5-1` na janela, com mtime, e os compara aos «2 arquivos mais novos» do
  `instrument-S339.md` §4.

Hipótese proposta na triagem e **não adotada**: «rótulo de modelo do sidecar ×
`message.model`». O sidecar `agent-<id>.meta.json` só existe para subagentes
(`ceo-cost-transcripts.py:1039`), e o modelo de um turno de assento vem de `message.model`
(`:585`). A linha em questão é de assento.

## Items

### W0 — medição só de leitura (bloqueada pelo §1.4 até o PLAN-186 ficar `done`; ver OQ-1)

- [ ] W0.1 Rodar a receita exata do instrumento shipado e registrar o bucket
  `assento | claude-fable-5-1` (turnos e as 5 classes de token):
  `python3 .claude/scripts/ceo-cost-transcripts.py --since-at 2026-08-03T00:00:00Z --until 2026-09-02T12:55:05.807Z --by role,model --json`.
  Check: a mesma linha rodada 2× com saída byte a byte idêntica (`cmp` dos dois JSON).
- [ ] W0.2 Teste de H1: contar, nos arquivos de assento da janela, os registros com
  `message.model` = `claude-fable-5-1` sob a chave do relatório e sob a do instrumento; dizer
  quantos registros carregam `apiBlockIndex`.
  Check: script stdlib só de leitura em `PLAN-186-FOLLOWUP-seat-fable51-row/w0/`, rodado 2× com saída idêntica, mais um controle positivo com um registro sintético duplicado por bloco de conteúdo.
- [ ] W0.3 Teste de H2: contagem de turnos por modelo sob a reconstrução deliberada do
  defeito (chave do relatório + first-write-wins), comparada célula a célula com a tabela
  publicada.
  Check: a soma por modelo da reconstrução reproduz o total 14.148, e a diferença na linha `claude-fable-5-1` fica escrita como número.
- [ ] W0.4 Teste de H3: inventário dos arquivos de assento com `claude-fable-5-1` na janela
  (nome do arquivo, mtime, contagem de registros), sem corpo de transcript.
  Check: `python3 .claude/scripts/check_contamination.py` rc 0 sobre o relatório (nenhum path pessoal; diretório do projeto escrito como `<project-slug>`).
- [ ] W0.5 Relatório `PLAN-186-FOLLOWUP-seat-fable51-row/w0/seat-fable51-row-<sessão>.md`
  com o veredito por hipótese (confirmada / refutada / não mensurável) e o comando de cada
  número.
  Check: `python3 .claude/scripts/check-staleness.py` rc 0 e `bash .claude/scripts/validate-governance.sh --fast` PASS depois do commit do relatório.

## Open questions

- OQ-1 (Owner, aberta em 2026-10-12): o §1.4 impede este follow-up de executar antes de o
  PLAN-186 ficar `done`, e o PLAN-186 ainda depende de cerimônias GPG. Os transcripts da
  janela (2026-08-03 → 2026-09-02) envelhecem sob o `cleanupPeriodDays: 90` do
  `.claude/settings.json`. Quando um arquivo é apagado, a medição dele deixa de ser possível.
  Opções: (a) esperar o §1.4 e aceitar a perda possível do corpus, declarada; (b) rodar a W0
  como item do PLAN-186 (o bullet de re-derivação da W0 do pai é o precedente) e manter este
  arquivo só como registro; (c) outra. Sem decisão neste texto.

## How to continue

Primeira mensagem de uma sessão futura: «Leia `PLAN-186-FOLLOWUP-seat-fable51-row.md`.
Confira o status do PLAN-186 e a resposta do Owner à OQ-1. Se a W0 estiver liberada, rode
W0.1 a W0.5 na ordem, só leitura, e publique o relatório com o comando de cada número.»

## Success criteria

- [ ] Cada uma das hipóteses H1–H3 tem veredito escrito, com o comando que o reproduz.
- [ ] A causa da diferença 660 × 207 está nomeada, ou o relatório declara, com o
  inventário da W0.4, que ela deixou de ser mensurável.
- [ ] O AC-1 do PLAN-186 recebe uma linha datada que aponta para o relatório; o AC segue `[x]`.

## Progress log

- 2026-10-12 (S363): follow-up criado em `draft`, pela decisão 4.4 da S347, no pacote livre
  `P186-TXT` do PLAN-186. Nenhuma medição executada.
