# PLAN-171 W0 — censo de gates com controle positivo, lote 3/6 (S347)

> **Escopo.** Os 10 hooks de `R[10:20]` da partição determinística do §1.
> **Método (a regra do W0, herdada do lote 1).** Um gate só é VERDE quando
> existe um controle positivo que (i) passa na árvore como está e (ii)
> **FALHA quando o enforcement é removido**. A metade RED é obrigatória —
> um controle que continua verde sem o enforcement é `controle vácuo`.
> Para um hook OBSERVADOR (PostToolUse, que não pode bloquear), o
> «enforcement» medido é a OBSERVAÇÃO: o evento/`systemMessage`/veredito
> que o hook existe para produzir.
> Medido em 2026-09-05/06 numa worktree descartável (`git worktree add
> --detach`), um gate por vez, `git restore` entre cada um. Nenhuma edição
> na árvore viva.
>
> **Bases (parágrafo GERADO — nenhum sha digitado).** As linhas citadas
> VERBATIM foram capturadas em `HEAD = 5f7f24f`. As duas metades da tabela
> (9/9 verde, 9/9 vermelho) e a medição do Apêndice E foram
> medidas em `HEAD = 14892ab`, cada prova com baseline e mutante na MESMA
> worktree e no MESMO base — que é o que a comparação exige. Este relatório
> foi GERADO sobre `HEAD = 14892ab` (se o HEAD andar antes do land, re-rodar
> `gen-report.py` e re-pinar o sha256 no derivador — o que RE-EXECUTA a
> recusa abaixo). Entre a base das citações e essa, os commits são:
>
> ```
> 14892ab feat(PLAN-186 s344-land-combined p171-w0-lote2-fix): os 2 P1 achados DEPOIS do land do lote 2 fechados por MEDIÇÃO e por GERAÇÃO
> 3f8f4f0 feat(PLAN-186 s344-land-combined walkroot-followup-plan): o follow-up do walk-from-root nasce curado — os 2 P1 que derrubaram o land anterior fechados por DERIVACAO
> a2d0fad docs(PLAN-188 debate round-1): rodada 1 do debate L3 — 3 críticos (VP Eng, DevOps, Security) ADJUST 4/4/5 bloqueios, síntese RUN-ANOTHER-ROUND com 7 achados de consenso e 15 must-fix
> bb68edf feat(PLAN-186 s344-land-combined p188-plan-draft): PLAN-188 nasce com o INSTRUMENTO que produziu seus números e a saída congelada que ele cita
> 184a1a2 feat(PLAN-186 s344-land-combined p171-w0-lote2): lote 2/6 do censo W0 do PLAN-171 — 10 hooks registrados, cada um provado nas TRÊS metades
> a3425ba feat(PLAN-186 s344-land-combined walkroot-fix): a bateria COMPLETA de hooks volta a TERMINAR — a raiz do sistema vira caso opt-in
> ```
>
> e o gerador RECUSA emitir o relatório se qualquer arquivo que ele cita
> (os 31: `settings.json`, os três workflows, os hooks mutados e os
> módulos de teste dos controles) aparecer em
> `git diff --name-only 5f7f24f..HEAD`. Nenhum aparece.

## 1. A partição (determinística, computada — não digitada)

`L` = os ARQUIVOS de hook registrados em `.claude/settings.json`, em ordem
de primeira ocorrência (itera o objeto `hooks` na ordem do arquivo —
eventos, grupos, entradas; toma o basename `*.py` de cada `command`;
dedupe mantendo a primeira). Medido por `gen-count.py` sobre o `settings.json`: **|L| = 48** arquivos distintos em **49 registrações**.

Removidos os arquivos que o §1 do `lote-1-S345.md` já atribui — os seis
que aparecem em `L`: `check_canonical_edit.py`, `check_bash_safety.py`,
`check_agent_spawn.py`, `check_pair_rail.py`,
`check_anti_ceo_overhead.py`, `accel_dispatch.py` (o host do gate
`adequacy`). As outras três linhas do lote 1 — `adequacy_gate.py`,
`_lib/audit_emit.py`, `inject-agent-context.sh` — **não estão em `L`**
por não serem hooks registrados, como o próprio lote 1 diz na coluna de
registro.

Resta **|R| = 42**, na ordem de `L` — e a tabela abaixo tem exatamente 42 linhas `R[..]`, das quais **10** marcadas como deste lote (o gerador RECUSA emitir se qualquer um dos três números divergir). `lote 2 = R[0:10]`; **`lote 3 = R[10:20]` (este relatório)**; `lotes 4-6 = R[20:42]`.

| Índice | Arquivo | Lote |
|---|---|---|
| R[ 0] | `check_adversary.py` | lote 2 |
| R[ 1] | `check_plan_edit.py` | lote 2 |
| R[ 2] | `check_protocol_semver_cascade.py` | lote 2 |
| R[ 3] | `check_skill_patch_sentinel.py` | lote 2 |
| R[ 4] | `check_tier_policy.py` | lote 2 |
| R[ 5] | `check_arbitration_kernel.py` | lote 2 |
| R[ 6] | `check_scratchpad_access.py` | lote 2 |
| R[ 7] | `check_budget.py` | lote 2 |
| R[ 8] | `check_read_injection.py` | lote 2 |
| R[ 9] | `check_codex_filewrite.py` | lote 2 |
| R[10] | `check_cost_envelope.py` | **lote 3 (ESTE)** |
| R[11] | `check_worktree_writer.py` | **lote 3 (ESTE)** |
| R[12] | `check_config_protection.py` | **lote 3 (ESTE)** |
| R[13] | `check_ledger_checkpoint.py` | **lote 3 (ESTE)** |
| R[14] | `audit_log.py` | **lote 3 (ESTE)** |
| R[15] | `check_confidence_gate.py` | **lote 3 (ESTE)** |
| R[16] | `check_output_safety.py` | **lote 3 (ESTE)** |
| R[17] | `check_subagent_fabrication.py` | **lote 3 (ESTE)** |
| R[18] | `check_skill_reference_read.py` | **lote 3 (ESTE)** |
| R[19] | `check_output_secrets.py` | **lote 3 (ESTE)** |
| R[20] | `check_skill_bootstrap_post.py` | lotes 4-6 (devidos) |
| R[21] | `check_webfetch_injection.py` | lotes 4-6 (devidos) |
| R[22] | `check_mcp_response.py` | lotes 4-6 (devidos) |
| R[23] | `check_codex_response.py` | lotes 4-6 (devidos) |
| R[24] | `check_bash_canonical_forensic.py` | lotes 4-6 (devidos) |
| R[25] | `SessionStart.py` | lotes 4-6 (devidos) |
| R[26] | `turbo_sessionstart.py` | lotes 4-6 (devidos) |
| R[27] | `check_compact_pinning.py` | lotes 4-6 (devidos) |
| R[28] | `SessionEnd.py` | lotes 4-6 (devidos) |
| R[29] | `UserPromptSubmit.py` | lotes 4-6 (devidos) |
| R[30] | `Stop.py` | lotes 4-6 (devidos) |
| R[31] | `codex_review_user_code.py` | lotes 4-6 (devidos) |
| R[32] | `review_loop.py` | lotes 4-6 (devidos) |
| R[33] | `check_closeout_guard.py` | lotes 4-6 (devidos) |
| R[34] | `check_fluency_nudge.py` | lotes 4-6 (devidos) |
| R[35] | `check_precompact_continuity.py` | lotes 4-6 (devidos) |
| R[36] | `check_postcompact_reinject.py` | lotes 4-6 (devidos) |
| R[37] | `check_config_change.py` | lotes 4-6 (devidos) |
| R[38] | `check_subagent_start.py` | lotes 4-6 (devidos) |
| R[39] | `check_setup_verification.py` | lotes 4-6 (devidos) |
| R[40] | `check_directory_added.py` | lotes 4-6 (devidos) |
| R[41] | `check_notification.py` | lotes 4-6 (devidos) |

> Derivado por `gen-partition.py` (no pack da sessão), que lê o
> `settings.json` com `json.load` e itera na ordem do arquivo. Os dois
> packs paralelos desta noite (lote 2 e lote 3) são provavelmente
> disjuntos por CONSTRUÇÃO: fatias `R[0:10]` e `R[10:20]` da MESMA lista.

## 2. Tabela

Colunas 4 (`CI`) medidas nos workflows, não supostas — e cada linha citada aqui foi RESOLVIDA POR CONTEÚDO pelo gerador (`_grep1`, que recusa se o texto procurado não casar exatamente uma linha): os controles que vivem em `.claude/hooks/tests/` rodam no job `hook-tests-python-matrix` (step «Run hook + script tests on Python ${{ matrix.python-version }}», `validate.yml` l. 1631 → as duas pernas do comando, l. 1644 e 1646), no `hook-tests-dual-rail` (step l. 1588 → comandos l. 1594 e 1595), em `coverage.yml:102` e em `release.yml:390`. Os controles que vivem em `.claude/hooks/_lib/tests/` e `.claude/scripts/swarm/tests/` **NÃO rodam em nenhum desses**: rodam no job `validate`, step «Run v1.0.1 test roots (PLAN-152 tests-01)» (`validate.yml` l. 553). A distinção é medida — ver Apêndice D.

| # | Gate (arquivo) | Registro em `.claude/settings.json` (evento / matcher; linha do `"matcher"` → linha do `"command"`) | Workflow + step de CI | Controle positivo (node id) | Como está | Enforcement removido | Verdito |
|---|---|---|---|---|---|---|---|
| 1 | `check_cost_envelope.py` | `PreToolUse` / `Bash` (matcher l. 314 → command l. 318) | `validate` / tests-01 (`validate.yml:553`) roda `_lib/tests/test_cost_envelope.py` — **59 testes no arquivo**, dos quais 53 exercitam a BIBLIOTECA de aritmética (`_lib/cost_envelope.py`) e 6, na classe `TestDispatchDetect`, carregam o HOOK só para exercitar `_looks_like_swarm_dispatch`. **Nenhum step de nenhum workflow executa um controle DEMONSTRADO do BLOQUEIO** — nenhuma das medições do Apêndice E demonstra um, e o apêndice declara a fronteira dessa afirmação (ela fala de desfechos que MUDAM; um teste cujo desfecho não dependa do bloqueio ficaria invisível a ela) | **nenhum** para o caminho de bloqueio | — | — | **sem controle** |
| 2 | `check_worktree_writer.py` | `PreToolUse` / `Bash\|Edit\|Write\|MultiEdit` (matcher l. 326 → command l. 330) | `hook-tests-python-matrix` + dual-rail + `coverage.yml:102` + `release.yml:390` | `.claude/hooks/tests/test_worktree_writer.py::TestEnforcementBoundary::test_edit_into_main_checkout_denied` | PASS | **FAIL** (rc 1) | **verde** |
| 3 | `check_config_protection.py` | `PreToolUse` / `Edit\|Write\|MultiEdit` (matcher l. 338 → command l. 342) | idem #2 | `.claude/hooks/tests/test_check_config_protection.py::TestBlockExisting::test_existing_eslintrc_json_blocked` | PASS | **FAIL** (rc 1) | **verde** |
| 4 | `check_ledger_checkpoint.py` | `PreToolUse` / `Bash` (matcher l. 350 → command l. 354) | idem #2 | `.claude/hooks/tests/test_check_ledger_checkpoint.py::TestAdvisoryNeverBlocks::test_missing_ledger_advises_but_does_not_block` | PASS | **FAIL** (rc 1) | **verde** (advisory por desenho — o hook NUNCA seta `permissionDecision`; o enforcement medido é o `additionalContext` ADVISORY + o evento com `would_block=1`; chaves opt-in de bloqueio MEDIDAS no Apêndice G) |
| 5 | `audit_log.py` | `PostToolUse` / `Agent` (matcher l. 364 → command l. 368) | idem #2 | `.claude/hooks/tests/test_audit_log.py::TestAppendEntryIntegration::test_redacts_secrets_in_description` | PASS | **FAIL** (rc 1) | **verde** (observador: o caminho provado é o SCRUB de segredo antes da escrita do evento; chaves opt-in de bloqueio MEDIDAS no Apêndice G) |
| 6 | `check_confidence_gate.py` | `PostToolUse` / `Agent` (matcher l. 376 → command l. 380) | **`validate` / «Run v1.0.1 test roots (PLAN-152 tests-01)»** (`validate.yml:553`) — o controle vive em `_lib/tests/`, FORA do `hook-tests-python-matrix` | `.claude/hooks/_lib/tests/test_confidence_gate_class_block.py::TestDecideEnforce::test_enforce_blocks_high_class` | PASS | **FAIL** (rc 1) | **verde** — mas ver §3, achado 1 |
| 7 | `check_output_safety.py` | `PostToolUse` / `Agent` (matcher l. 388 → command l. 392) | idem #2 | `.claude/hooks/tests/test_check_output_safety.py::CheckOutputSafetyBasicTest::test_nfkc_full_width_attack_flagged_via_hook` | PASS | **FAIL** (rc 1) | **verde** (observador: emite `output_safety_flag`, saída PRESERVADA no modo `flag`; chaves opt-in de bloqueio MEDIDAS no Apêndice G) |
| 8 | `check_subagent_fabrication.py` (wrapper fino de `.claude/scripts/swarm/_subagent_fabrication.py`) | `PostToolUse` / `Agent` (matcher l. 400 → command l. 404) | **`validate` / tests-01** (`validate.yml:553`, que roda `.claude/scripts/swarm/tests`) | `.claude/scripts/swarm/tests/test_subagent_fabrication.py::TestCLIHookMode::test_hook_mode_fabrication_blocking_emits_systemmessage` | PASS | **FAIL** (rc 1) | **verde** (o controle exercita a BIBLIOTECA `_subagent_fabrication.py`, que é onde o mecanismo vive; o wrapper `check_subagent_fabrication.py` tem apenas testes de import/entry-point, o que este relatório declara em vez de disfarçar) |
| 9 | `check_skill_reference_read.py` | `PostToolUse` / `Read` (matcher l. 424 → command l. 428) | idem #2 | `.claude/hooks/tests/test_check_skill_reference_read_v2.py::ReconcileReadTests::test_mismatch_verdict_written` | PASS | **FAIL** (rc 1) | **verde** (observador: veredito `mismatch` sha-pinado vs sha lido; chaves opt-in de bloqueio MEDIDAS no Apêndice G) |
| 10 | `check_output_secrets.py` | DUAS registrações: `PostToolUse` / `""` (matcher l. 436 → command l. 440) **e** `PostToolUseFailure` / `""` (matcher l. 522 → command l. 526) | idem #2 | `.claude/hooks/tests/test_check_output_secrets.py::TestCheckOutputSecretsMainStringToolResponse::test_bash_string_with_secret_reaches_scanner` | PASS | **FAIL** (rc 1) | **verde** (observador: `systemMessage` `OUTPUT-SCAN`; chaves opt-in de bloqueio MEDIDAS no Apêndice G) |

**Contagem (contada por `gen-count.py` sobre a tabela ACIMA — uma linha plantada muda estes números; ver Apêndice C):** 10 gates no lote; **9** com controle positivo PROVADO vermelho;
**0** `controle vácuo`;
**1** `sem controle`;
**0** `sem-controle-por-design`;
**0** `UNREGISTERED`.

Nenhum desses números é literal no gerador: `gen-count.py` os conta na
tabela ACIMA, com controle vermelho no Apêndice C. O `sem controle` é a
linha #1 (`check_cost_envelope.py`); os 10 gates têm registro próprio em
`settings.json` (a linha #10 tem dois), logo `UNREGISTERED` = 0.

## 3. Os dois achados que o lote paga

**Achado 1 — o controle óbvio do `check_confidence_gate` é um teste
PULADO.** `.claude/hooks/tests/test_check_confidence_gate.py::TestDecide::test_fail_with_enforce_blocks`
tem a forma de um controle positivo (monta payload de falha, exige
`assertFalse(d.allow)`), e a suíte o reporta como `s` — não como `.`:

```
$ python3 -m pytest -q --no-header -p no:cacheprovider -rs \
    .claude/hooks/tests/test_check_confidence_gate.py::TestDecide::test_fail_with_enforce_blocks
s                                                                        [100%]
=========================== short test summary info ============================
SKIPPED [1] .claude/hooks/tests/test_check_confidence_gate.py:66: ADR-019-AMEND-1 retired broad enforce — see test_confidence_gate_class_block.py
1 skipped in 0.08s
```

A citação é do NÓ NOMEADO — rodado sozinho — e não do arquivo: uma rodada
do módulo inteiro imprime TRÊS linhas `SKIPPED`, e citar a errada foi
exatamente o defeito que uma refutação pegou neste relatório. As três, com
o arquivo inteiro:

```
$ python3 -m pytest -q --no-header -p no:cacheprovider -rs \
    .claude/hooks/tests/test_check_confidence_gate.py
SKIPPED [1] .claude/hooks/tests/test_check_confidence_gate.py:286: ADR-019-AMEND-1 retired broad enforce — see test_confidence_gate_class_block.py
SKIPPED [1] .claude/hooks/tests/test_check_confidence_gate.py:316: ADR-019-AMEND-1 retired broad enforce — see test_confidence_gate_class_block.py
SKIPPED [1] .claude/hooks/tests/test_check_confidence_gate.py:66: ADR-019-AMEND-1 retired broad enforce — see test_confidence_gate_class_block.py
36 passed, 3 skipped in 0.37s
```

Os três `@unittest.skip` carregam o MESMO motivo (ADR-019-AMEND-1
aposentou o enforce amplo) e os três têm forma de controle do bloqueio:
`test_fail_with_enforce_blocks` (l. 66), `test_exit1_enforce1_blocks` e
`test_block_reason_template`. Nenhum deles pode ir a vermelho.

Um teste pulado NUNCA vai a vermelho, logo não é controle: é exatamente
a classe «gate vermelho invisível» que motiva o W0. O `@unittest.skip`
aponta para o substituto certo, e é ESSE que a tabela usa
(`_lib/tests/test_confidence_gate_class_block.py`, provado vermelho). O
que fica registrado é a REGRA: quando um controle candidato mora no
módulo homônimo do hook, checar `-rs` antes de chamá-lo de controle.

**Achado 2 — `check_cost_envelope.py` BLOQUEIA e nenhuma medição
demonstra um controle desse bloqueio.** O hook emite `{"decision": "block", ...}`
(`check_cost_envelope.py:281`) quando a janela de custo estoura. Existem
59 testes em `.claude/hooks/_lib/tests/test_cost_envelope.py` — 53
exercitando a BIBLIOTECA de aritmética (`_lib/cost_envelope.py`: matriz de
caps, `would_breach`, `check_and_record`, filelock, rollover) e 6 na classe
`TestDispatchDetect`, que carrega o hook só para exercitar
`_looks_like_swarm_dispatch`. Nenhum dos 59 toca o caminho de bloqueio. Medido com a suíte INTEIRA do `pytest.ini`,
rodada duas vezes com `-ra` (todo desfecho não-passante nomeado): apagar a
emissão do bloqueio produz TRÊS diferenças de desfecho, e as três são
disposadas por IDENTIDADE — dois budgets de perf advisory do rail de
lifecycle e um gate de literal de versão em `npm/`; para nenhum dos três a
evidência demonstra um controle do bloqueio (`grep` de conteúdo: 0 menções
ao envelope de custo em cada arquivo). O Apêndice E declara a fronteira do que essa medição
pode fechar (o que EXECUTA) e o que não pode (desfechos pulados; um
`XFAIL` que permaneça `XFAIL`). Verdito: `sem controle` — e NÃO `sem-controle-por-design`: o hook é DEFAULT-OFF
(`CEO_SWARM` unset ⇒ allow), o que reduz a exposição, mas nem o PLAN-171
nem um ADR declaram que o caminho de bloqueio dispensa controle. É
follow-up, não conserto deste lote (que é um censo, não uma reescrita).

## 4. O que este lote NÃO afirma

- Não afirma nada sobre `R[0:10]` (lote 2, paralelo esta noite) nem
  sobre `R[20:42]` (lotes 4-6, devidos).
- Não afirma que o controle cobre TODO o gate: cada linha prova UM
  caminho — bloqueio, recusa, scrub, evento ou veredito —, nunca a
  superfície inteira do hook. Onde o caminho não é o bloqueio de uma
  ferramenta, a coluna «Verdito» o NOMEIA.
- A metade RED foi obtida removendo o enforcement do jeito MÍNIMO
  (Apêndice B); ela prova que o controle enxerga aquele mecanismo, não
  que o mecanismo é completo.
- Os dois jobs de CI citados carregam `if: vars.CEO_SOTA_DISABLE != '1'`
  (`validate.yml` l. 1567 e l. 1602): o gate existe; a EXECUÇÃO dele é
  condicional, e essa condição não foi exercitada aqui (caveat herdado
  do lote 1, re-verificado nas mesmas linhas).
- Este pack **não edita** `.claude/plans/PLAN-171-governance-imports-provenance.md`.
  O «Registro de execução» do plano é escrito pelo lote 2 esta noite; a
  linha de log do lote 3 é DEVIDA ao próximo pack do W0.

## Apêndice A — baseline «como está» (9/9 verde)

Os node ids vêm de `node-ids.txt`, derivado do campo `node` do
`red-half.json` — logo o conjunto que passou aqui é, por construção, o
MESMO que foi ao vermelho no Apêndice B. A linha #1 não entra: não há
node id para entrar.

```
$ xargs python3 -m pytest -q --no-header -p no:cacheprovider < node-ids.txt
9 passed in 0.48s
```

## Apêndice B — metade RED, gate a gate

Para cada linha: `git restore` → mutação mínima → **mesmo** node id →
`git restore`. Todas as nove retornaram `rc 1`.

| # | Gate (arquivo mutado) | Mutação mínima aplicada (diff literal, do registro cru) | Resultado |
|---|---|---|---|
| 2 | `check_worktree_writer.py` | `-     return _is_inside(target, main_checkout)` / `+     return False` | `1 failed in 0.09s` (rc 1) |
| 3 | `check_config_protection.py` | `-     return _contract.block(reason)` / `+     return _contract.allow()` | `1 failed in 0.09s` (rc 1) |
| 4 | `check_ledger_checkpoint.py` | `-             "additionalContext": additional_context,` / `+             "additionalContext": "",` | `1 failed in 0.22s` (rc 1) |
| 5 | `audit_log.py` | `-     desc_preview = _redact.redact_secrets(description)` / `+     desc_preview = description` | `1 failed in 0.10s` (rc 1) |
| 6 | `check_confidence_gate.py` | `-         blocking = _classify_blocking_claims(payload, tiers)` / `+         blocking = []` | `1 failed in 0.09s` (rc 1) |
| 7 | `check_output_safety.py` | `+     return` | `1 failed in 0.22s` (rc 1) |
| 8 | `_subagent_fabrication.py` | `-                 sys.stdout.write(json.dumps({` / `-                     "systemMessage": msg,` / `-                 }))` / `+                 pass` | `1 failed in 0.10s` (rc 1) |
| 9 | `check_skill_reference_read.py` | `-             verdict = "mismatch"` / `+             verdict = "match"` | `1 failed in 0.09s` (rc 1) |
| 10 | `check_output_secrets.py` | `-     return _emit_observe(` / `+     return _emit_observe()` / `-         system_message=(` / `-             f"OUTPUT-SCAN: {total} finding(s) in {tool_name} output "` / `-             f"(top: {top_label}) — advisory, see audit-log"` / `-         )` / `-     )` | `1 failed in 0.10s` (rc 1) |

**A mutação tem de remover o MECANISMO, não renomear uma string.** A
primeira mutação da linha 10 trocava o prefixo do `systemMessage`
(`OUTPUT-SCAN` → `(neutered)`) e deixava intactos a varredura, o evento de
auditoria e o próprio aviso: o controle ia a vermelho porque o teste casa
o TEXTO, não porque a observação sumisse — uma rodada de MECANISMO do rail
(que re-executou o mutante e leu a saída) rejeitou exatamente isso. A
mutação vigente SUPRIME a observação (`_emit_observe(system_message=…)` →
`_emit_observe()`): o `systemMessage` que este observador existe para
emitir deixa de existir — e isso não é afirmado, é REPLAYADO, na mesma
moeda que a rodada de rail usou para derrubar a versão anterior:

```
# mesmo hook, mesmo payload, worktree descartável:
# intacto -> mutante (return _emit_observe()) -> git restore
intact    systemMessage=True   chaves=['continue', 'systemMessage']
           stdout: {"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}
mutant    systemMessage=False  chaves=['continue']
           stdout: {"continue": true}
restored  systemMessage=True   chaves=['continue', 'systemMessage']
           stdout: {"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}
veredito: observação SUPRIMIDA
```

A regra que fica, e que vale para todo o W0: se o
controle pode ir a vermelho por uma renomeação, ele prova sensibilidade a
palavra, não enforcement. As outras oito mutações são de mecanismo por
construção — inverter uma fronteira, trocar `block` por `allow`, esvaziar
a lista de claims bloqueantes, remover o scrub, suprimir a escrita do
evento, inverter o veredito de reconciliação — e cada uma está impressa
por inteiro na tabela acima, do registro cru.

Registro cru das nove rodadas: `red-half.json` no pack da sessão
(`gate`, `path`, `neuter_old`, `neuter_new`, `neuter_diff`, `node`, `rc`,
`tail` por linha), produzido por `red-half.py`, que aplica a mutação por
âncora com contagem esperada 1 e recusa se a âncora não for única. A
coluna «Mutação» acima é GERADA desse registro (`gen-report.py`), não
digitada — a versão digitada descrevia uma INSERÇÃO enquanto o registro
guardava só a última linha do contexto, e uma rodada de rail pegou a
discrepância.

## Apêndice C — contagem derivada, não digitada

A linha de contagem do §2 sai de comandos sobre a PRÓPRIA tabela
deste arquivo — e os números abaixo são MEDIDOS sobre o documento
montado, não digitados (uma rodada de mecanismo pegou o `# 19`
digitado envelhecendo no instante em que o Apêndice G nasceu).
Discriminante medido (mesma armadilha do lote 1): `^\| [0-9]+ \|`
sozinho casa **todas** as tabelas numeradas do arquivo — hoje 29
linhas: 10 no §2, 9 no Apêndice B, 10 no Apêndice G. O que separa o §2 é o node id (`::`);
simetricamente `1 failed in` só existe no Apêndice B.

```
grep -cE '^\| [0-9]+ \|' .claude/plans/PLAN-171/w0/lote-3-S347.md   # 29  (todas as tabelas numeradas do arquivo)
grep -cE '^\| [0-9]+ \|.*::' .claude/plans/PLAN-171/w0/lote-3-S347.md   # 9  (linhas do §2 COM node id)
grep -cE '^\| [0-9]+ \|.*\*\*verde\*\*' .claude/plans/PLAN-171/w0/lote-3-S347.md   # 9  (veredito verde)
grep -cE '^\| [0-9]+ \|.*\*\*sem controle\*\*' .claude/plans/PLAN-171/w0/lote-3-S347.md   # 1  (veredito sem controle)
grep -cE '^\| [0-9]+ \|.*controle vácuo' .claude/plans/PLAN-171/w0/lote-3-S347.md   # 0  (veredito controle vácuo)
grep -cE '^\| [0-9]+ \|.*1 failed in' .claude/plans/PLAN-171/w0/lote-3-S347.md   # 9  (linhas do Apêndice B)
```

9 verde + 1 sem controle = 10 = |lote 3|. As saídas medidas estão
no `EVIDENCE.md` do pack, geradas por `gen-evidence.sh` sobre a
derivação FINAL — nenhum número acima foi digitado.

**E a linha de contagem do §2 é IMPRESSA por instrumento, não escrita.**
`gen-count.py` conta as linhas da tabela do §2 (escopadas à seção, para a
tabela numerada do Apêndice B não vazar) e tabula UM vocabulário de
vereditos; uma linha da tabela que não case nenhum veredito do vocabulário
é RECUSA, nunca zero silencioso. O mesmo instrumento re-deriva `|L|`, as
registrações e `|R|` do `settings.json` e RECUSA emitir se a tabela do §1
não tiver exatamente `|R|` linhas nem exatamente 10 marcadas como deste
lote. Controle VERMELHO da derivação (`--plant` planta uma linha em CADA
tabela; os dois blocos derivados TÊM de se mover):

```
$ python3 gen-count.py --doc .claude/plans/PLAN-171/w0/lote-3-S347.md
$ python3 gen-count.py --doc .claude/plans/PLAN-171/w0/lote-3-S347.md --plant
```

As duas saídas, e o `diff` entre elas, estão no `EVIDENCE.md` do pack.

E a ligação entre a tabela e o conjunto que REALMENTE rodou:

```
$ sed -n '/^## 2\./,/^## 3\./p' .claude/plans/PLAN-171/w0/lote-3-S347.md \
    | grep -E '^\| [0-9]+ \|' \
    | grep -oE '\.claude/[^ `|]*tests/[^ `|]+::[A-Za-z0-9_:]+' | sort > /tmp/from-table.txt
$ sort node-ids.txt > /tmp/from-run.txt
$ diff /tmp/from-run.txt /tmp/from-table.txt && echo IDENTICAL
IDENTICAL
```

## Apêndice D — quem executa o quê (medido nos workflows)

```
$ sed -n '556,580p' .github/workflows/validate.yml   # step tests-01 do job `validate` — AS DUAS pernas
          cd "$GITHUB_WORKSPACE"
          python3 -m pytest \
            tests/unit \
            .claude/hooks/_lib/tests \
            .claude/scripts/swarm/tests \
            .claude/scripts/replay/tests \
            tests/test_federation \
            .claude/scripts/mcp-server/tests \
            .claude/scripts/detectors/tests \
            .claude/scripts/predict-budget/tests \
            tests/forensic \
            tests/synthetic \
            -n auto -m 'not serial' --strict-markers --tb=no -q
          python3 -m pytest \
            tests/unit \
            .claude/hooks/_lib/tests \
            .claude/scripts/swarm/tests \
            .claude/scripts/replay/tests \
            tests/test_federation \
            .claude/scripts/mcp-server/tests \
            .claude/scripts/detectors/tests \
            .claude/scripts/predict-budget/tests \
            tests/forensic \
            tests/synthetic \
            -m 'serial' --strict-markers --tb=no -q

$ sed -n '1644,1648p' .github/workflows/validate.yml # job `hook-tests-python-matrix` — AS DUAS pernas
          python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ \
            -n auto -m 'not serial' --strict-markers --tb=no -q
          python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ \
            -m 'serial' --strict-markers --tb=no -q
          echo "Tests green on Python ${{ matrix.python-version }}"

$ sed -n '1594,1595p' .github/workflows/validate.yml # job `hook-tests-dual-rail` — AS DUAS pernas
          python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q
          python3 -m pytest .claude/hooks/tests/ -m 'serial' --strict-markers --tb=no -q

$ sed -n '102p' .github/workflows/coverage.yml
          python3 -m pytest .claude/hooks/tests -q --tb=short

$ sed -n '390p' .github/workflows/release.yml
        run: python3 -m pytest .claude/hooks/tests -q --tb=short
```

As duas pernas importam — e a afirmação vale para os TRÊS steps do
`validate.yml` acima (tests-01, matrix, dual-rail), não para os de
`coverage.yml` e `release.yml`, cujos comandos citados não têm perna de
marcador nenhuma (rodam sem `-m`, logo também sem subtração): cada um dos
três roda `-m 'not serial'` E DEPOIS `-m 'serial'`, então a marca `serial`
não subtrai nada do conjunto executado. Citar só a primeira perna faria a
coluna «CI» afirmar mais do que o comando mostra — defeito apontado numa
rodada de rail e curado aqui.

Onde vivem os controles das linhas 6 e 8 — busca EXAUSTIVA, todos os
workflows, não uma amostra:

```
$ grep -rn '_lib/tests\|swarm/tests' .github/workflows/
.github/workflows/validate.yml:548:      # co-located immediately AFTER swarm/tests to reproduce the S228
.github/workflows/validate.yml:559:            .claude/hooks/_lib/tests \
.github/workflows/validate.yml:560:            .claude/scripts/swarm/tests \
.github/workflows/validate.yml:571:            .claude/hooks/_lib/tests \
.github/workflows/validate.yml:572:            .claude/scripts/swarm/tests \
```

Cinco linhas, UM arquivo — quatro delas argumentos de `pytest` (as duas
pernas do MESMO step, `tests-01` do job `validate`) e a quinta um
COMENTÁRIO (`validate.yml:548`), que não executa nada. Logo:
`.claude/hooks/_lib/tests` e `.claude/scripts/swarm/tests` não aparecem em
nenhum outro job — nem na matriz de Python, nem no
dual-rail, nem no coverage, nem no release.

## Apêndice E — o que a medição da linha 1 demonstra (e o que não)

Duas metades. Primeiro, o hook BLOQUEIA (o literal existe):

```
$ sed -n '281p' .claude/hooks/check_cost_envelope.py
    _emit_decision({"decision": "block", "reason": reason})
```

Segundo — e esta é a metade que TRÊS rodadas de rail obrigaram a refazer —
apagar esse bloqueio não derruba nada que sobreviva ao escrutínio. As
versões descartadas e POR QUÊ, porque a forma do erro é a lição:

1. `pytest -k cost_envelope`: `-k` seleciona por PALAVRA no node id, não
   por o que o teste exercita — um controle com outro nome ficaria entre os
   deselecionados.
2. Corpus inteiro, comparando só linhas `FAILED`: cego a um desfecho
   reportado como XFAIL/XPASS.
3. Corpus inteiro com `-rxXs`: **a sonda ficou cega à classe que precisava
   vigiar** — `-r` SUBSTITUI o default `-rfE` do pytest, então aquela
   captura não tinha linha `FAILED` nenhuma. (Mantida como verificação
   cruzada: `raw/outcomes-diff.txt`.)

O instrumento FINAL é `outcome-probe2.sh`: UMA worktree descartável, UM
base, AS DUAS pernas do `pytest.ini`, `-ra` (que reporta TODO desfecho
não-passante: `FAILED`, `ERROR`, `SKIPPED`, `XFAIL`, `XPASS`), rodadas
baseline → mutante → `git restore`, com os conjuntos NOMEADOS comparados.

**BASELINE** (árvore intacta) e **MUTANTE**
(`_emit_decision({"decision": "block", "reason": reason})` →
`_emit_decision({})`, UMA ocorrência, aplicada por script com contagem
esperada 1):

```
baseline: 14542 passed, 149 skipped, 9 xfailed, 1 xpassed, 36 warnings in 308.03s (0:05:08) / 1010 passed, 9 skipped, 14700 deselected, 1 xfailed, 5 xpassed in 206.66s (0:03:26)
mutante:  1 failed, 14541 passed, 149 skipped, 9 xfailed, 1 xpassed, 36 warnings in 305.04s (0:05:05) / 1010 passed, 9 skipped, 14700 deselected, 3 xfailed, 3 xpassed in 206.21s (0:03:26)
```

Classes nomeadas — baseline `SKIPPED 132, XFAIL 10, XPASS 6`; mutante `FAILED 1, SKIPPED 132, XFAIL 12, XPASS 4`.

O `diff` COMPLETO dos conjuntos nomeados (nada omitido):

```
0a1
> FAILED .claude/scripts/tests/test_release_bump_sites.py::test_npm_docs_carry_no_bare_version_literal
137a139,140
> XFAIL .claude/hooks/tests/test_tool_lifecycle_observe.py::TestObservePerf::test_observe_write_path_under_2ms_p99
> XFAIL .claude/hooks/tests/test_tool_lifecycle_perf.py::TestLifecyclePerf::test_in_process_pair_logic_under_2ms_p99
146,147d148
< XPASS .claude/hooks/tests/test_tool_lifecycle_observe.py::TestObservePerf::test_observe_write_path_under_2ms_p99 ADVISORY in-process perf budget (PLAN-154 item 1 / A3). The record_pre+record_post hot path WITH the observe rail enabled (one extra O_APPEND write of a ~120-byte closed row, emit MOCKED) targets the same p99 < 2ms as the base rail. Under heavy concurrent pytest load the wall-clock budget can be missed; solo it XPASSes. strict=False so an XPASS never fails CI. NOT a strict gate by design.
< XPASS .claude/hooks/tests/test_tool_lifecycle_perf.py::TestLifecyclePerf::test_in_process_pair_logic_under_2ms_p99 ADVISORY in-process perf budget (PLAN-125 WS-1 / MF-PERF-4). The record_pre+record_post hot-path logic (per-session JSON read-modify-write under the cheap filelock + enum mapping, emit MOCKED) targets p99 < 2ms. Under heavy concurrent pytest load (4000+ tests + integration/formal subprocess churn) the wall-clock budget can be missed; solo it XPASSes. strict=False so an XPASS is reported but NEVER fails CI. NOT a strict gate by design.
diff rc=1
```

**As 3 diferenças, uma a uma — disposadas por IDENTIDADE, que é o que a
pergunta exige.** Um teste cujo DESFECHO dependa do bloqueio muda de
desfecho quando o bloqueio some, e portanto apareceria NESTE diff — é essa
a implicação, e só ela: um teste cujo desfecho NÃO dependa do bloqueio
(por exemplo um `XFAIL` que continue `XFAIL`) não aparece, e sobre ele a
medição nada diz. Os nodes que aparecem são três, todos NOMEADOS acima.
Sobre eles, uma evidência de CONTEÚDO — não de nome, e não de assertiva:

```
$ grep -cE 'cost_envelope|check_cost_envelope|CEO_SWARM|cost envelope' <cada um dos três arquivos>
.claude/hooks/tests/test_tool_lifecycle_observe.py -> 0
.claude/hooks/tests/test_tool_lifecycle_perf.py -> 0
.claude/scripts/tests/test_release_bump_sites.py -> 0
```

- `.claude/hooks/tests/test_tool_lifecycle_observe.py::TestObservePerf::test_observe_write_path_under_2ms_p99`
  e `.claude/hooks/tests/test_tool_lifecycle_perf.py::TestLifecyclePerf::test_in_process_pair_logic_under_2ms_p99`:
  budgets de perf ADVISORY `strict=False` do rail de lifecycle. O que eles
  medem está no próprio texto de `reason` citado na saída: p99 do caminho
  `record_pre`+`record_post` com `emit` MOCKADO. Nenhum dos dois arquivos
  contém MENÇÃO ao envelope de custo (o `grep` acima, sobre o conteúdo, dá
  0). Zero casamentos estabelecem a ausência dos padrões buscados, e nada
  além disso: não excluem uma assertiva INDIRETA via helper ou fixture.
  A afirmação que esta evidência sustenta é a mais fraca — **estas
  evidências não demonstram que estes nodes sejam controles do bloqueio**.
  Moveram-se
  de `XPASS` para `XFAIL`; os textos deles dizem «Under heavy concurrent
  pytest load the wall-clock budget can be missed; solo it XPASSes.
  strict=False so an XPASS never fails CI. NOT a strict gate by design», e
  na sonda cruzada `raw/outcomes-diff.txt` — OUTRO par de rodadas — o node
  `.claude/hooks/tests/test_tool_lifecycle_observe.py::TestObservePerf::test_observe_write_path_under_2ms_p99`
  se move na direção OPOSTA. Isso é consistente com variabilidade de carga
  e NÃO é prova de que a mutação não contribuiu: o relatório não afirma
  causa. A disposição não depende disso.
- `.claude/scripts/tests/test_release_bump_sites.py::test_npm_docs_carry_no_bare_version_literal`:
  um gate sobre literais de versão em `npm/`; também com 0 menções ao
  envelope de custo no `grep` acima. E ele **falha com a árvore INTACTA** — está na
  captura de baseline de uma rodada anterior deste mesmo apêndice, sem
  mutação nenhuma:

```
FAILED .claude/scripts/tests/test_verify_counts_remediation.py::TestE9F10RecurrenceGuards::test_real_repo_passes_new_gates
FAILED .claude/scripts/tests/test_release_bump_sites.py::test_npm_docs_carry_no_bare_version_literal
3 failed, 14539 passed, 149 skipped, 9 xfailed, 1 xpassed, 36 warnings in 1077.16s (0:17:57)
........................................................................ [ 98%]
.......sssss....                                                         [100%]
1010 passed, 9 skipped, 14700 deselected, 2 xfailed, 4 xpassed in 211.64s (0:03:31)
```

  e, rodado sozinho na árvore intacta, PASSA:

```
$ python3 -m pytest -q --no-header .claude/scripts/tests/test_release_bump_sites.py::test_npm_docs_carry_no_bare_version_literal
.                                                                        [100%]
1 passed in 0.09s
```

  Ou seja: seu desfecho depende do contexto de execução, não só da árvore.
  Isso não PROVA que a mutação não contribuiu para a falha desta rodada —
  o relatório não faz essa afirmação. A disposição é a mesma das duas
  anteriores, e na mesma força: estas evidências não demonstram que este
  node seja um controle do bloqueio.

**O conjunto `SKIPPED`: o que ele é, e o limite que impõe.** As linhas
`SKIPPED` do resumo do pytest são ENTRADAS AGREGADAS
(`SKIPPED [n] <local>: <motivo>`), não node ids: são 132 entradas no
baseline e 132 no mutante, somando 158 e 158 desfechos pulados —
exatamente os `149 + 9` e `149 + 9` das linhas de totais. Entradas idênticas
portanto NÃO estabelecem que o conjunto de NODES pulados é o mesmo; o que
estabelecem é que nenhuma entrada de skip surgiu, sumiu ou mudou de
motivo. Nenhuma delas cita `cost_envelope` (0 ocorrências). E o limite
maior, declarado: teste por mutação só fala de código que EXECUTA — um
teste pulado nunca poderia ir a vermelho, então esta prova não afirma
NADA sobre o conteúdo dos 158 desfechos pulados.

**Conclusão, com a fronteira exata.** Entre os testes que EXECUTAM em
alguma raiz coletada pelo `pytest.ini`, **esta medição não demonstra
NENHUM controle positivo do bloqueio do `check_cost_envelope.py`**: as
únicas diferenças de desfecho entre a árvore intacta e a mutante são três
nodes nomeados, e para nenhum dos três a evidência demonstra um controle
do bloqueio. O que a
medição NÃO pode fechar, e não fecha: um `XFAIL` que permanecesse `XFAIL`
poderia, em tese, ter trocado de causa; e os desfechos pulados não
executam. Por isso a linha 1 é `sem controle` — «nenhum controle
demonstrado por estas medições» — e não `controle vácuo` (não há controle
a qualificar).

## Apêndice G — existe chave que faz esta linha BLOQUEAR? (medido)

A pergunta que o censo deve por linha ADVISORY/OBSERVADORA não é
«o hook bloqueia hoje?» e sim «existe uma CHAVE que o faz bloquear, e ela
foi medida?». Um relatório anterior deste W0 chamou uma linha de «sempre
allow» tendo o hook uma chave opt-in de bloqueio nunca medida; esta seção
é a resposta mecânica, produzida por `measure-optin.py` (no pack da
sessão) sobre uma worktree descartável em `HEAD = a2d0fad`.

**Instrumento, em três derivações.** (1) ESTÁTICA por AST + varredura de
texto: toda variável `CEO_`/`CLAUDE_` que o módulo CONSOME por um getter
reconhecido, toda que ele liga a uma constante de módulo (`X_ENV = "CEO_…"`
— é assim que `check_ledger_checkpoint.py` nomeia a sua), toda que a
docstring MENCIONA, e todo construto de bloqueio das formas procuradas:

- `call-block` — chamada `*.block(...)` (AST)
- `dict-decision` — dicionário literal com `"decision": "block"` (AST, multilinha e aninhado inclusive)
- `cmp-decision` — comparação com literal — `<x>.get("decision") == "block"` ou `<x>["decision"] == "block"` (AST)
- `text-decision` — varredura de texto de reforço: `"decision"` seguido de `"block"` na mesma linha (pega o que o AST não parseie)
- `dict-permissionDecision` — dicionário literal com `"permissionDecision": "deny"` (AST, multilinha e aninhado inclusive)
- `cmp-permissionDecision` — comparação com literal — `<x>.get("permissionDecision") == "deny"` ou `<x>["permissionDecision"] == "deny"` (AST)
- `text-permissionDecision` — varredura de texto de reforço: `"permissionDecision"` seguido de `"deny"` na mesma linha (pega o que o AST não parseie)

(2) DINÂMICA para todo hook com ZERO construtos: o hook roda de ponta a
ponta sobre um payload, uma vez sem chave e uma vez por par (chave, valor),
e cada saída é classificada. (3) CRUZAMENTO para todo hook COM construtos:
o controle da própria linha, já provado VERMELHO no Apêndice B, é
localizado no registro cru — ou o hook é declarado NÃO-MEDIDO com a seção
que o diz.

**Controle positivo do PROBE.** «Nenhum bloqueio observado» só vale se o
classificador conseguir VER um bloqueio. O mesmo runner e o mesmo
classificador, contra um hook que bloqueia (`check_config_protection.py`, sobre um `.eslintrc.json`
EXISTENTE criado no sandbox), retornam:

```
{"decision": "block", "reason": "BLOCKED: Write would modify the existing linter/formatter config '.eslintrc.json' (<SANDBOX>/cwd/.eslintrc.json) — fix the code, not the config. An agent should not relax a project's linter/formatter gate to make it pass — change the offending code instead. If this edit is a legitimate config change, use t
```

Veredito do controle: **BLOCK** (rc 0). Sem isso, o instrumento RECUSA
escrever sua saída.

| # | Hook | Chaves `CEO_`/`CLAUDE_` encontradas | Construtos de bloqueio (forma@linha) | Como a linha se desincumbe | Probe |
|---|---|---|---|---|---|
| 1 | `check_cost_envelope.py` | `CEO_PLAN_ID`, `CEO_SWARM`, `CEO_SWARM_CLASS`, `CEO_SWARM_ESTIMATED_SPAWN_CENTS`, `CEO_SWARM_ESTIMATE_CENTS`, `CLAUDE_PROJECT_DIR` | text-decision@46, dict-decision@281 | declarado-não-medido | — |
| 2 | `check_worktree_writer.py` | `CEO_ASSIGNED_WORKTREE`, `CEO_PARALLEL_WRITER`, `CEO_WS3_APPLY_OK`, `CLAUDE_PROJECT_DIR` | text-decision@92, call-block@665, call-block@683, call-block@698, call-block@704, call-block@709, call-block@721, call-block@752 | medido-no-apêndice-B | — |
| 3 | `check_config_protection.py` | `CEO_CONFIG_PROTECTION`, `CEO_CONFIG_PROTECTION_ADVISORY`, `CLAUDE_PROJECT_DIR` | text-decision@98, call-block@324, call-block@344 | medido-no-apêndice-B | — |
| 4 | `check_ledger_checkpoint.py` | `CEO_LEDGER_CHECKPOINT`, `CEO_LEDGER_CHECKPOINT_REQUIRED`, `CEO_SOTA_DISABLE`, `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`, `CLAUDE_PROJECT_DIR` | **0** | sem-construto-de-bloqueio + probe dinâmico | 9 execuções, **0** com bloqueio |
| 5 | `audit_log.py` | `CEO_AUDIT_LOG_`, `CEO_AUDIT_LOG_DIR`, `CEO_AUDIT_LOG_ERR`, `CEO_AUDIT_LOG_LOCK`, `CEO_AUDIT_LOG_PATH`, `CEO_AUDIT_LOG_ROTATE_BYTES`, `CEO_CODEX_TURN_SOURCE`, `CEO_DISPATCH_ARCHETYPE_HINT`, `CEO_GROK_TURN_SOURCE`, `CEO_HOOK_ADAPTER`, `CLAUDE_PROJECT_DIR` | **0** | sem-construto-de-bloqueio + probe dinâmico | 11 execuções, **0** com bloqueio |
| 6 | `check_confidence_gate.py` | `CEO_CONFIDENCE_BYPASS`, `CEO_CONFIDENCE_ENFORCE`, `CEO_CONFIDENCE_GATE_PRODUCER_PAIR_DISABLED`, `CLAUDE_PROJECT_DIR` | call-block@342 | medido-no-apêndice-B | — |
| 7 | `check_output_safety.py` | `CEO_OUTPUT_SAFETY_MODE`, `CEO_SOTA_DISABLE`, `CLAUDE_PROJECT_DIR` | **0** | sem-construto-de-bloqueio + probe dinâmico | 5 execuções, **0** com bloqueio |
| 8 | `check_subagent_fabrication.py` | `CEO_SUBAGENT_FABRICATION_BLOCK`, `CEO_SUBAGENT_FABRICATION_DEBUG` | **0** | sem-construto-de-bloqueio + probe dinâmico | 5 execuções, **0** com bloqueio |
| 9 | `check_skill_reference_read.py` | `CEO_AUDIT_LOG_ERR`, `CEO_AUDIT_LOG_PATH`, `CEO_SKILL_READ_STATE_DIR`, `CEO_SKILL_READ_V2`, `CLAUDE_PROJECT_DIR` | **0** | sem-construto-de-bloqueio + probe dinâmico | 3 execuções, **0** com bloqueio |
| 10 | `check_output_secrets.py` | `CEO_OUTPUT_SCAN`, `CEO_OUTPUT_SCAN_DEDUP`, `CEO_OUTPUT_SCAN_LLM10`, `CEO_OUTPUT_SCAN_TELEMETRY`, `CEO_OUTPUT_SCAN_UNICODE`, `CEO_TOOL_LIFECYCLE`, `CLAUDE_PROJECT_DIR`, `CLAUDE_SESSION_ID` | **0** | sem-construto-de-bloqueio + probe dinâmico | 15 execuções, **0** com bloqueio |

**Detalhe por linha probada.**

**Linha 4 — `check_ledger_checkpoint.py`.** Matriz completa (9 execuções, 0 delas com saída além do allow nu):

| Switch | Valor | rc | Veredito | stdout (truncado) |
|---|---|---|---|---|
| `(nenhum)` | `—` | 0 | **no-block** | `{}` |
| `CEO_LEDGER_CHECKPOINT` | `1` | 0 | **no-block** | `{}` |
| `CEO_LEDGER_CHECKPOINT` | `0` | 0 | **no-block** | `{}` |
| `CEO_LEDGER_CHECKPOINT_REQUIRED` | `1` | 0 | **no-block** | `{}` |
| `CEO_LEDGER_CHECKPOINT_REQUIRED` | `0` | 0 | **no-block** | `{}` |
| `CEO_SOTA_DISABLE` | `1` | 0 | **no-block** | `{}` |
| `CEO_SOTA_DISABLE` | `0` | 0 | **no-block** | `{}` |
| `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` | `1` | 0 | **no-block** | `{}` |
| `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` | `0` | 0 | **no-block** | `{}` |

**Linha 5 — `audit_log.py`.** Matriz completa (11 execuções, 0 delas com saída além do allow nu):

| Switch | Valor | rc | Veredito | stdout (truncado) |
|---|---|---|---|---|
| `(nenhum)` | `—` | 0 | **no-block** | `` |
| `CEO_AUDIT_LOG_ROTATE_BYTES` | `1` | 0 | **no-block** | `` |
| `CEO_AUDIT_LOG_ROTATE_BYTES` | `0` | 0 | **no-block** | `` |
| `CEO_CODEX_TURN_SOURCE` | `1` | 0 | **no-block** | `` |
| `CEO_CODEX_TURN_SOURCE` | `0` | 0 | **no-block** | `` |
| `CEO_DISPATCH_ARCHETYPE_HINT` | `1` | 0 | **no-block** | `` |
| `CEO_DISPATCH_ARCHETYPE_HINT` | `0` | 0 | **no-block** | `` |
| `CEO_GROK_TURN_SOURCE` | `1` | 0 | **no-block** | `` |
| `CEO_GROK_TURN_SOURCE` | `0` | 0 | **no-block** | `` |
| `CEO_HOOK_ADAPTER` | `1` | 0 | **no-block** | `` |
| `CEO_HOOK_ADAPTER` | `0` | 0 | **no-block** | `` |

**Linha 7 — `check_output_safety.py`.** Matriz completa (5 execuções, 0 delas com saída além do allow nu):

| Switch | Valor | rc | Veredito | stdout (truncado) |
|---|---|---|---|---|
| `(nenhum)` | `—` | 0 | **no-block** | `{}` |
| `CEO_OUTPUT_SAFETY_MODE` | `flag` | 0 | **no-block** | `{}` |
| `CEO_OUTPUT_SAFETY_MODE` | `redact` | 0 | **no-block** | `{}` |
| `CEO_SOTA_DISABLE` | `1` | 0 | **no-block** | `{}` |
| `CEO_SOTA_DISABLE` | `0` | 0 | **no-block** | `{}` |

**Linha 8 — `check_subagent_fabrication.py`.** Matriz completa (5 execuções, 1 delas com saída além do allow nu):

| Switch | Valor | rc | Veredito | stdout (truncado) |
|---|---|---|---|---|
| `(nenhum)` | `—` | 0 | **no-block** | `` |
| `CEO_SUBAGENT_FABRICATION_BLOCK` | `1` | 0 | **no-block** | `{"systemMessage": "\u26a0\ufe0f  SUB-AGENT FABRICATION DETECTED (qa-architect, sha8=88e5cbc8): tool_call_json\u00d71. Response may contain hallucinate` |
| `CEO_SUBAGENT_FABRICATION_BLOCK` | `0` | 0 | **no-block** | `` |
| `CEO_SUBAGENT_FABRICATION_DEBUG` | `1` | 0 | **no-block** | `` |
| `CEO_SUBAGENT_FABRICATION_DEBUG` | `0` | 0 | **no-block** | `` |

**Linha 9 — `check_skill_reference_read.py`.** Matriz completa (3 execuções, 0 delas com saída além do allow nu):

| Switch | Valor | rc | Veredito | stdout (truncado) |
|---|---|---|---|---|
| `(nenhum)` | `—` | 0 | **no-block** | `{}` |
| `CEO_SKILL_READ_V2` | `1` | 0 | **no-block** | `{}` |
| `CEO_SKILL_READ_V2` | `0` | 0 | **no-block** | `{}` |

**Linha 10 — `check_output_secrets.py`.** Matriz completa (15 execuções, 13 delas com saída além do allow nu):

| Switch | Valor | rc | Veredito | stdout (truncado) |
|---|---|---|---|---|
| `(nenhum)` | `—` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_OUTPUT_SCAN` | `1` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_OUTPUT_SCAN` | `0` | 0 | **no-block** | `{"continue": true}` |
| `CEO_OUTPUT_SCAN_DEDUP` | `1` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_OUTPUT_SCAN_DEDUP` | `0` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_OUTPUT_SCAN_LLM10` | `1` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_OUTPUT_SCAN_LLM10` | `0` | 0 | **no-block** | `{"continue": true}` |
| `CEO_OUTPUT_SCAN_TELEMETRY` | `1` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_OUTPUT_SCAN_TELEMETRY` | `0` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_OUTPUT_SCAN_UNICODE` | `1` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_OUTPUT_SCAN_UNICODE` | `0` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_TOOL_LIFECYCLE` | `1` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CEO_TOOL_LIFECYCLE` | `0` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CLAUDE_SESSION_ID` | `1` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |
| `CLAUDE_SESSION_ID` | `0` | 0 | **no-block** | `{"continue": true, "systemMessage": "OUTPUT-SCAN: 1 finding(s) in Bash output (top: LLM06_sensitive_info=1) — advisory, see audit-log"}` |

**Isolação, verificada e não assumida.** Cada execução roda com `HOME` e
toda a família `CEO_AUDIT_LOG_*` redirecionados para um diretório
temporário. A verificação NÃO é o tamanho do log vivo — outras sessões da
máquina escrevem nele enquanto o probe roda (medido: 5.068 bytes de
tráfego alheio numa rodada) — e sim o MARCADOR: linhas do log vivo
contendo o `session_id` do probe, 0 antes e 0 depois (delta **0**).

**Chaves excluídas do probe dinâmico (declaradas, não escondidas).**

- `CEO_AUDIT_LOG_DIR` — carrier de path da PRÓPRIA isolação do probe
- `CEO_AUDIT_LOG_ERR` — carrier de path da PRÓPRIA isolação do probe
- `CEO_AUDIT_LOG_LOCK` — carrier de path da PRÓPRIA isolação do probe
- `CEO_AUDIT_LOG_PATH` — carrier de path da PRÓPRIA isolação do probe
- `CEO_SKILL_READ_STATE_DIR` — carrier de path de estado, não chave de decisão
- `CLAUDE_PROJECT_DIR` — carrier de path (raiz do projeto) exigido pelo probe

Além dessas, nomes terminados em `_` são fragmentos de curinga de docstring
(`CEO_AUDIT_LOG_*`), não nomes de variável, e não são setados.

**Limites, que são o complemento do instrumento.** O detector estático olha
o ARQUIVO do hook e não segue `import`: um bloqueio montado numa
biblioteca importada (é o caso do wrapper da linha 8) não aparece como
construto — por isso a linha 8 é probada dinamicamente, que é o que
alcança a biblioteca. A varredura exige chave E valor LITERAIS
(``"decision": "block"` / `"permissionDecision": "deny"``), logo uma decisão montada por variável escapa. E o probe fala do
payload e da matriz de valores que ele rodou: para as linhas cujo produto
é um EVENTO de auditoria (não um `systemMessage`), «saída além do allow
nu» é o sensor errado e a coluna diz apenas o que viu — a prova de que o
caminho ativo funciona é o controle da própria linha no Apêndice B. Nenhuma
destas medições afirma que nenhuma configuração pode fazer o hook
bloquear; afirmam que NESTAS formas, NESTES arquivos e NESTA matriz de
chaves, 48 execuções produziram 0 bloqueios.

**Resultado.** 6 hooks probados dinamicamente, 48 execuções, **0**
bloqueios; 1 hook(s) com construto de bloqueio declarado NÃO-MEDIDO (linha 1 do §2 e Achado 2: o caminho de bloqueio existe (`check_cost_envelope.py:281`) e NENHUMA medição deste pack demonstra um controle dele — o veredito da linha é `sem controle`.).

## Apêndice F — o que o lote consumiu como INPUT (rastreável)

- `.claude/plans/PLAN-171-governance-imports-provenance.md` §5, §6, §7.
- `.claude/plans/PLAN-171/w0/lote-1-S345.md` §1 (a coluna «Arquivo(s)»
  que define a subtração da partição) e a forma da tabela + apêndices.
- `.claude/settings.json` (registro por evento/matcher, lido com
  `json.load` na ordem do arquivo).
- `.github/workflows/validate.yml`, `coverage.yml`, `release.yml`
  (quem executa).
- `pytest.ini` (`testpaths`) — para saber o que `-k` varre.
