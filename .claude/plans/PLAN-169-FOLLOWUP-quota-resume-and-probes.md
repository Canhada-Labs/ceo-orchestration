---
id: PLAN-169-FOLLOWUP-quota-resume-and-probes
title: Quota-resume, probes W4.2.0 e marcador do 12º site
status: reviewed
reviewed_at: 2026-10-01
reviewed_by: "Owner - Q13 alínea (e), aceite em bloco das recomendações no chat da S361 (2026-10-01): OQ-1 e OQ-2 respondidas como no texto"
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
- **Janela real (Q13-e, resposta à OQ-2).** O trabalho longo que começa na S361 é
  a janela real de esgotamento para este critério. Cada esgotamento ocorrido nela
  é registrado de forma falsificável, e a evidência é a recusa literal do harness
  («session limit»), não o `used_pct` do sidecar (medido: `five_hour` = 35 % no
  instante de uma recusa; `CLAUDE.md` §5). Por ocorrência, registrar o `resets_at`
  lido antes da parada, o instante em que o trabalho retomou, quem retomou (o
  `autoContinueAtUsageLimit` nativo, citado em `CLAUDE.md` §4, ou outro caminho) e
  se algum turno se perdeu. Registrar também a versão do Claude Code
  (`claude --version`) no momento da parada e o estado efetivo do
  `autoContinueAtUsageLimit`, com a fonte: chave ausente em todos os settings vale
  como LIGADA por padrão, sujeita a gates de servidor; valor explícito, dizer de
  qual settings veio. Registrar ainda o caminho que bateu no limite (sessão
  principal ou agente de Workflow) e, se o trabalho não retomou, o motivo que o
  harness deu (no Workflow, o evento `workflow_rate_limit_wait` com
  `setting_off_while_waiting` ou `killswitch_while_waiting`). Desfechos declarados
  de antemão:
  - **(a) o nativo retoma sozinho:** o quota-resume próprio fica desnecessário e o
    AC-4 fecha com esse RESULTADO, sem construir o mecanismo. Os outros itens do
    AC-4 (kill-switches, gate de postura, doc, `env-inventory.json`) ficam sem
    objeto. Em 2026-10-01 o mecanismo próprio não existe no código (a busca por
    `quota.resume` e `quota_resume` em `.claude/hooks`, `.claude/scripts`, `docs`,
    `templates` e `scripts` devolve zero; `CEO_QUOTA_RESUME` só aparece em planos)
    e nenhum arquivo do repositório configura o nativo (fora dos planos, só o
    `CLAUDE.md` §4 o cita; chave ausente = ligada por padrão no CC 2.1.286, sujeita a
    gates de servidor não medidos — CC286-05 do planejamento S360). O nativo NÃO foi
    testado aqui.
  - **(b) o nativo não retoma, ou retoma errado:** o AC-4 segue aberto com essa
    evidência, que passa a justificar o mecanismo próprio. Isso vale só com o nativo
    efetivamente ligado. Se ele estiver desligado (configuração ou killswitch do
    servidor), registra-se um desfecho à parte, «nativo desligado». Esse desfecho não
    justifica o mecanismo próprio sem antes ligar o nativo e repetir o teste.
  - **(c) nenhum esgotamento durante a janela:** o AC-4 NÃO fecha por isso. Registra-se
    a ausência com as leituras de quota, e a escolha entre esperar outra ocorrência
    e declarar a impossibilidade volta ao Owner.

### AC-5 [P1] — Probes W4.2.0 (a–f)

- Registrados com evidência: um peer tenta induzir edição canônica via
  `SendMessage` ⇒ BLOQUEADO, com evento HMAC de campos whitelisted
  (checklist R-SEC9).
- Com `refuse`: nenhum turno nasce (controle positivo: com `accept`, nasce).
- Doutrina em ADR, incluindo a decisão sobre visibilidade de tentativas recusadas.

### AC-7 [P1] — Marcador do 12º site

- Controle plantado VERMELHO + bump real VERDE — as duas evidências (a perna verde já
  não é o bump 1.4.0: ver abaixo).
- **Perna VERDE (resposta à OQ-1, Q13-e): resolvida pelos bumps reais da 1.4.1 e
  da 1.4.2.** Os dois trocaram a versão e levaram o marcador junto: `9e9840b2`
  (2026-09-18, `release: v1.4.1`, 1.4.0 → 1.4.1) e `9b5b1b40` (2026-09-28,
  `release: v1.4.2`, 1.4.1 → 1.4.2) alteram `.claude/.framework-version` ao lado
  dos demais arquivos de bump (12 arquivos em cada commit), e as tags `v1.4.1` e
  `v1.4.2` existem. O bump do GA 1.4.0, de 2026-09-15, foi **no-op** (VERSION já
  estava em 1.4.0, quatro oráculos limpos) e deixa de ser a evidência da perna
  verde.
- **Perna VERMELHA: falta produzir, como teste livre e persistente.** A W2.6 do
  PLAN-169 já provou um controle TRANSITÓRIO (marcador dessincronizado em 9.9.9 ⇒
  `rc=1` nomeando o site; restaurado ⇒ `rc=0`; desplantado no mesmo commit;
  progress log da W2.6 e ledger E.1 em
  `.claude/plans/PLAN-169-closure-and-cross-session-evolution.md`), mas não deixou
  teste que se reexecute. Falta um teste que plante o marcador dessincronizado numa
  árvore descartável e prove o vermelho do oráculo REAL: a entrada
  `.claude/.framework-version` de `VERSION_SITES` em
  `.claude/scripts/local/verify-counts.sh`, pelo molde `VERIFY_COUNTS_ROOT` de
  `.claude/scripts/tests/test_verify_counts_remediation.py`. Não serve o oráculo
  stub da fixture `synth` de `.claude/scripts/tests/test_release_bump_sites.py`, e
  nunca se planta no `.claude/.framework-version` vivo. Antes de escrever, confirme
  com o oráculo `--is-canonical` o path escolhido para o teste.

## Open questions

- **OQ-1.** AC-7 pode fechar com a evidência do bump no-op do corte do GA, ou
  exige um bump real com mudança de versão (o que só acontece na 1.4.1)?
- **OQ-2.** AC-4 exige live-fire de quota, que depende de uma janela real de
  esgotamento. Vale esperar a próxima ocorrência natural ou registrar a
  impossibilidade?

**Respostas do Owner (2026-10-01, S361; aceite em bloco das recomendações no chat, Q13 alínea (e)):**

- **OQ-1 — RESPONDIDA.** O AC-7 não precisa mais do bump no-op do GA 1.4.0: os bumps
  reais da 1.4.1 e da 1.4.2 já trocaram a versão e são a perna verde. Falta só o
  controle vermelho persistido, um teste livre (detalhe no item AC-7).
- **OQ-2 — RESPONDIDA.** O trabalho longo da S361 é a janela real de esgotamento
  do AC-4, registrada de forma falsificável (nem esperar uma ocorrência natural
  qualquer, nem registrar a impossibilidade de saída). Se o auto-continue nativo
  tornar o quota-resume próprio desnecessário, isso é o RESULTADO do AC-4 (detalhe
  no item AC-4).

## How to continue

> Ler este arquivo e o PLAN-169 (`done`) para o contexto dos três critérios.
> OQ-1 e OQ-2 estão respondidas (acima). Dois próximos passos: escrever o teste do
> controle vermelho do AC-7 (livre) e registrar a janela do AC-4 durante o trabalho
> longo. O AC-5 segue aberto e sem passo livre neste trabalho longo: a primeira
> perna dele (o bloqueio via `SendMessage`) depende de o PreToolUse disparar para
> essa ferramenta, o que com a configuração atual não acontece (PLAN-186, AC-15,
> resposta parcial de 2026-09-03). Medir a hookabilidade exige um matcher
> temporário em `.claude/settings.json`, que entra por cerimônia. Nenhum dos três
> critérios está no caminho crítico de release.

## Success criteria

- [ ] AC-4 fechado com evidência ou impossibilidade registrada de forma falsificável
- [ ] AC-5 fechado com controle positivo e negativo
- [ ] AC-7 fechado com as duas evidências (perna verde resolvida pela OQ-1 com os
      bumps 1.4.1/1.4.2; falta o controle vermelho persistido, um teste livre)

## Progress log

- 2026-10-01 (S361): `status: draft → reviewed` por decisão do Owner (Q13 alínea
  (e), aceite em bloco das recomendações no chat). OQ-1 e OQ-2 respondidas e
  dobradas nos itens AC-4 e AC-7. Nenhum item executado ainda.
