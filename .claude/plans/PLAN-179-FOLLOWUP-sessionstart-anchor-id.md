---
id: PLAN-179-FOLLOWUP
title: "Residuais da wave-179close (rails r6+r8): precedencia de id do produtor do session_start; entrega do harness-noop-allowlist.txt ao adopter"
status: draft
created: 2026-08-31
related_commits: []
owner: CEO
depends_on: [PLAN-179]
level: L3
budget_tokens: "40-80k (wave canonica de 1 path + testes; molde = cerimonia de kernel-member da wave-179close)"
budget_sessions: 1
context_risk: low
external_wait: "assinatura GPG do Owner (SessionStart.py e hook canonico)"
eta_calendar: "1 cerimonia, sem urgencia — a degradacao atual e SEGURA (start_unknown, nunca janela errada)"
tags: [governanca, hooks, sessionend, ancora, followup, canonico]
---

# PLAN-179-FOLLOWUP — precedencia de id do produtor do `session_start`

> **Lineage (PLAN-SCHEMA §1.4 — "parent shipped with explicit deferred AC
> items").** Achado REAL do pair-rail r6 da wave-179close (P2, registrado em
> `.claude/plans/PLAN-179/s335-ceremony-179close/rail-round-6.md`): o
> PLAN-179 fecha `done` com este residual declarado. Este followup NAO abre
> escopo novo — e o veiculo do alinhamento producer-side que a r6 mandou e a
> cerimonia recusou fazer inline por estar FORA do conjunto revisado.

## O defeito (verificado em codigo na r6)

`SessionStart.py:559-561` resolve o id **env-first**
(`CLAUDE_SESSION_ID` > payload) ao gravar o evento `session_start` na
cadeia; o consumidor do US8 (`SessionEnd._session_start_ts`) e
**payload-gated por decisao de seguranca** (rails r3/r4 da wave-179close:
env e agent-spoofable e NUNCA ancora — enfraquecer isso re-entra o gate de
VETO de seguranca). Quando os dois ids divergem, o start foi gravado sob um
id que o consumidor legitimamente recusa ⇒ toda sessao divergente reporta
`outcome=start_unknown` / `anchor_source=none`.

A degradacao e SEGURA (o hook prefere nao saber a inventar janela — nunca
um falso `written`), e a trava de consumo esta testada
(`test_divergent_env_id_never_anchors`). O que este followup entrega e o
alinhamento do PRODUTOR, unica direcao compativel com a doutrina.

## AC

- [ ] `[P1][US1][.claude/hooks/SessionStart.py]` O produtor do
      `session_start` passa a resolver o id **payload-first** (payload >
      env > fallback de timestamp), espelhando a precedencia do
      `SessionEnd.py::main` (rail r3 P2-b da wave-179close) — mesma
      justificativa: o SPEC exige o id "threaded from the harness event" e
      o env e spoofable. Check: teste de unidade com env divergente do
      payload prova que o evento gravado carrega o id do PAYLOAD.
- [ ] `[P1][US1][.claude/hooks/tests/test_session_end_memory_delta.py]`
      Teste de integracao produtor→consumidor: com env divergente, o
      `session_start` gravado pelo produtor payload-first E ancorado pelo
      consumidor payload-gated (`anchor_source=chain`) — o caso que hoje
      degrada para `start_unknown` passa a resolver.
- [ ] `[P2][US1]` Varredura dos DEMAIS consumidores de `session_start` na
      cadeia (grep por leitores do action) para confirmar que nenhum
      depende da grafia env-first do produtor antes do flip.

## Item 2 — RETIRADO na r14 (o artefato saiu do patch)

> **Status: WITHDRAWN (rail r14, S336).** A r14 provou que a entrada era
> INERTE para o propósito declarado (o comando registrado é um hook real
> — a heurística constant-emitter do gate nunca dispara sobre ele; o
> próprio comentário do arquivo admitia) e que o waiver de substring
> abria bypass do ADR-158 §2 (um comando substituído por
> `printf 'SessionEnd.py disabled'` passaria calado). O
> `harness-noop-allowlist.txt` foi REMOVIDO do patch da wave-179close;
> não há mais nada a entregar. O texto abaixo fica como registro
> histórico do achado r8 que o motivou.

## [HISTÓRICO — retirado] entrega do `harness-noop-allowlist.txt` ao adopter (rail r8 P2-a)

Achado REAL da r8, registrado em
`.claude/plans/PLAN-179/s335-ceremony-179close/rail-round-8.md`:
`install_hooks_selective()` (`scripts/install.sh`) copia apenas `*.sh` e
`*.py` do top-level de `.claude/hooks/` — o `harness-noop-allowlist.txt`
(novo nesta wave, e o UNICO `.txt` do diretorio) nunca chega ao adopter.
O consumidor `check_harness_config.py` VIAJA (e `.py`), entao um adopter
que ative `CEO_SESSION_MEMORY_DELTA=0` teria a rota de waiver (b) do
gate indisponivel ⇒ preflight vermelho-falso. `scripts/install.sh` esta
FORA do conjunto revisado pela cerimonia wave-179close (alarga-lo pos-rail
assinaria superficie nao-revisada), e entrega de artefato e o dominio da
maquinaria delivery-routes (PLAN-183) — proximo do trem ratificado.

- retirado: `(P1)(US2)(scripts/install.sh)` Entregar o allowlist no install
      (glob consciente OU rota em `scripts/delivery-routes.tsv` — decidir
      pelo mecanismo do PLAN-183 W1; localizadores literais migram no
      MESMO patch). Check: smoke-install prova o arquivo no target.
- retirado: `(P1)(US2)(scripts/upgrade.sh)` Mesma entrega no upgrade (hash-gate
      da familia D1). Check: e2e de upgrade prova o arquivo entregue.
- retirado: `(P2)(US2)` Residual DECLARADO ate landar: adopter com o
      kill-switch em `off` e o gate harness-config rodando ve
      vermelho-falso; workaround documentavel = criar o txt a mao ou
      marker `_comment` (rota (a) do gate).

## Restricoes

- `SessionStart.py` e hook canonico: a wave exige sentinel + assinatura
  GPG do Owner (cerimonia propria, molde wave-179close).
- A trava do consumidor (`test_divergent_env_id_never_anchors`) NAO pode
  ser relaxada por esta wave — o alinhamento e no produtor; o consumidor
  payload-gated fica como esta.
- Item 2 nao mexe em `check_harness_config.py` nem no allowlist em si —
  so na ENTREGA; o conteudo do txt e da wave-179close assinada.
