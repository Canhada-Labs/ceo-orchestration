---
id: PLAN-179-FOLLOWUP
title: "Residuais da wave-179close (rails r6+r8): precedencia de id do produtor do session_start; entrega do harness-noop-allowlist.txt ao adopter"
status: done
created: 2026-08-31
completed_at: 2026-09-04
executing_at: 2026-09-02   # retroativo: os 3 ACs executaram na cerimônia wave-179fu (land 8efe09b, 2026-09-02, GPG do Owner); o self-gate reviewed→executing cai neste commit de fechamento (PLAN-SCHEMA:404-406)
reviewed_at: 2026-09-04
reviewed_by: "Owner (S344, item 2 da lista de abertura — os 3 ACs [x] ja landaram em 8efe09b/b6dce78; flip draft→reviewed ratificado com o Owner presente)"
related_commits: [2bda673, 8efe09b, b6dce78, de35103]   # 2bda673 materiais da cerimônia wave-179fu; 8efe09b LAND (GPG do Owner) — os 2 ACs P1 e a expansão 2→4 produtores; b6dce78 pack sonnet5-fu; de35103 flip draft→reviewed (S344)
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

- [x] `[P1][US1][.claude/hooks/SessionStart.py]` O produtor do
      `session_start` passa a resolver o id **payload-first** (payload >
      env > fallback de timestamp), espelhando a precedencia do
      `SessionEnd.py::main` (rail r3 P2-b da wave-179close) — mesma
      justificativa: o SPEC exige o id "threaded from the harness event" e
      o env e spoofable. Check: teste de unidade com env divergente do
      payload prova que o evento gravado carrega o id do PAYLOAD.
      — ⚠ S337 (achado da varredura P2, abaixo): o produtor LEGADO do
      `session_end` (`SessionEnd.py:1203-1206`) é env-first TAMBÉM, e o
      consumidor do US8 lê o `session_end` pelo id do PAYLOAD
      (`SessionEnd.py:600`) para segmentar a janela no último fim
      verificado. Flipar só o `SessionStart` deixa essa perna cega quando
      env≠payload: a wave deve flipar OS DOIS produtores no mesmo patch, e o
      teste de integração do item seguinte deve cobrir start E end. A
      redação "espelhando a precedência do `SessionEnd.py::main`" acima
      está errada como referência — o `main` legado é `env or payload`; a
      precedência-modelo é a do rail novo (`payload_sid`, `:1202`).
      — ✅ S340 (2026-09-02): pago pela cerimônia wave-179fu, land
      `8efe09b` (GPG do Owner). Censo do rail r1: a classe tinha QUATRO
      produtores legados (SessionStart, UserPromptSubmit, Stop,
      SessionEnd), não dois — a assinatura ratificou a expansão 2→4.
- [x] `[P1][US1][.claude/hooks/tests/test_session_end_memory_delta.py]`
      Teste de integracao produtor→consumidor: com env divergente, o
      `session_start` gravado pelo produtor payload-first E ancorado pelo
      consumidor payload-gated (`anchor_source=chain`) — o caso que hoje
      degrada para `start_unknown` passa a resolver.
      — ✅ S340 (2026-09-02): pago pela cerimônia wave-179fu, land
      `8efe09b` (GPG do Owner). Censo do rail r1: a classe tinha QUATRO
      produtores legados (SessionStart, UserPromptSubmit, Stop,
      SessionEnd), não dois — a assinatura ratificou a expansão 2→4.
- [x] `[P2][US1]` Varredura dos DEMAIS consumidores de `session_start` na
      cadeia (grep por leitores do action) para confirmar que nenhum
      depende da grafia env-first do produtor antes do flip.
      — ✅ S337 (2026-09-01): executada, read-only, sem cerimônia. Veredito:
      **nenhum consumidor depende da grafia env-first**; um é PREJUDICADO
      por ela hoje (`codex-advisory-teeth.py`) e passa a alinhar com o flip;
      e a varredura achou o SEGUNDO produtor env-first (`session_end`
      legado) que o flip precisa levar junto — registro completo abaixo.

## Registro de execução — P2, varredura dos consumidores (S337, 2026-09-01)

Método: `grep -rn session_start .claude/hooks .claude/scripts scripts
templates SPEC` excluindo `tests/` e `.md`, depois leitura de cada sítio
(como o id é usado, e o que muda quando o produtor do `session_start` passar
de env-first para payload-first). `dist/` não foi varrido separadamente —
são espelhos gerados por `scripts/build-plugin.py` e acompanham os canônicos.

| Leitor | Onde | Como usa o id | Efeito do flip |
|---|---|---|---|
| `SessionEnd._session_start_ts` (US8 memory-delta) | `SessionEnd.py:386-620` | payload-gated: casa `session_start` (`:618`) **e** `session_end` (`:600`) pelo id do PAYLOAD | beneficiário — hoje degrada para `start_unknown` quando env≠payload |
| `SessionEnd.py::main`, produtor LEGADO do `session_end` | `SessionEnd.py:1203-1206` | **env-first** (`CLAUDE_SESSION_ID` > payload) — espelho do `SessionStart:559` atual | **ACHADO:** o `session_end` é lido pelo payload id em `:600`; flipar só o start deixa a segmentação cega quando env≠payload. Os dois produtores flipam JUNTOS (item 1, ⚠ acima). Não é o caso da r12 (ali o flip parcial quebrou start↔end; aqui o par inteiro muda de grafia) |
| `scripts/codex-advisory-teeth.py` | `:73`, `:180-215` | agrupa por `session_id`: `session_start` (boot) × `agent_spawn`/`codex_*` (atividade); RED-on-absence do boot | atividade é PAYLOAD-id (`audit_log.py:597`, `:1414`); o boot da via Claude é env-first ⇒ hoje um FALSO `boot_breadcrumb_absence` quando env≠payload. O flip ALINHA (cura colateral), não quebra |
| `audit_log.py` (adapter codex) → `emit_session_start` | `audit_log.py:1414`, `:1443` | 2º PRODUTOR do `session_start`; id do evento do adapter (payload) | já payload-first; após o flip os dois produtores têm a MESMA grafia |
| `_lib/swarm_circuit_breaker` B.4/B.5 + `scripts/swarm/loop_runner.py` | `:51`, `:117-135`; `:234-269` | presença do action numa janela de tempo; nunca lê o id | inerte |
| `.claude/scripts/ceo-escalation-detector.py` | `:163-178`, `:222-255` | particiona por `session_id` (sessão com mais eventos ou `--session-id`); `detect_gate_skip` lê `files_read` no `session_start` — anotação que nenhum produtor emite (advisory por construção) | hoje o boot env-first pode cair FORA da partição da sessão; o flip o traz para dentro — sem regressão |
| `check_closeout_guard._session_start_head` | `:44-52` | **não é leitor da cadeia**: HEAD do git no início da sessão (env / state file) — colisão de nome | inerte |
| `_lib/adapters/grok.py:166`; `_lib/spool_writer.reconcile_journal_at_session_start`; `scripts/codex-exec-wrapper.sh:13` | — | mapeamento de fase; nome de função; invoca o produtor codex | inertes |
| `SPEC/v1/audit-log.schema.md:245` | — | `session_start` (v2.7) = `action, session_id, ts, event_schema`, SEM regra de precedência; só a v2.60 exige "threaded from the harness event, no silent default" | o flip é compatível com o SPEC; registrar a precedência na linha v2.7 é opcional e CANÔNICO (fora desta varredura) |

**Conclusão:** o flip do item 1 é seguro do lado dos consumidores e obrigatório
nos DOIS produtores legados (`SessionStart.py:559-561` e
`SessionEnd.py:1203-1206`), com o `payload_sid` do rail novo intocado. O
item 2 ganha uma perna: `session_end` gravado payload-first E consumido em
`:600` como âncora de segmentação.

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

## Fechamento (S345, 2026-09-04 — noite autônoma, sem GPG: só escrituração)

- Os três ACs estão `[x]` e landados: P1/US1 (produtor payload-first) e o
  teste de integração produtor→consumidor pela cerimônia `wave-179fu`
  (materiais `2bda673`, LAND `8efe09b` assinado pelo Owner em 2026-09-02; o censo
  do rail r1 expandiu a classe de 2 para 4 produtores legados), e a varredura
  P2 (S337, read-only). O item 2 foi RETIRADO na r14 da wave-179close (o
  artefato saiu do patch). Nada resta a executar.
- Ciclo de vida: `draft → reviewed` em `de35103` (S344, Owner presente);
  `reviewed → executing → done` neste commit, pelo Edit tool com o hook
  `check_plan_edit.py` validando cada transição; `executing_at` é retroativo
  à data do land (`8efe09b`, 2026-09-02).
- Residual herdado (inalterado): a trava do consumidor
  (`test_divergent_env_id_never_anchors`) permanece; o SPEC v2.7 do
  `session_start` não registra a precedência (opcional, canônico, fora deste
  plano).
