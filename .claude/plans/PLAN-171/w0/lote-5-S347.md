# PLAN-171 W0 — censo de gates com controle positivo, lote 5/6 (S347)

> **Escopo.** A fatia `R[30:36]` da partição determinística do §1 — os
> 6 hooks REGISTRADOS que sobram depois do lote 1 e das fatias dos
> lotes 2, 3 e 4. **Método (a regra do W0):** um gate só é VERDE quando
> existe um controle positivo que (i) passa na árvore como está,
> (ii) **FALHA quando o enforcement é removido** e (iii) volta a passar
> depois do `git restore` — o **controle de restauração** introduzido
> pelo lote 2, sem o qual um `.pyc` velho no `sys.pycache_prefix` do
> macOS falsifica a medição. As três metades foram rodadas em
> `2026-09-06` numa worktree descartável (`git worktree add --detach`),
> um gate por vez, `git restore` entre cada um, com
> `PYTHONDONTWRITEBYTECODE=1` e `-p no:cacheprovider`. Nenhuma edição na
> árvore viva. **Bases:** as três metades foram medidas em
> `HEAD = db05586`, RE-RODADAS em `HEAD = 00839a6` (o land do
> lote 3) com veredito idêntico, e a metade verde foi RE-CONFIRMADA em
> `HEAD = faa6b061b874ce1b2a169778e829dd7dabcb237c` (o land do lote 4 + o closeout da S347) — `6 passed in 1.20s`.
> Entre a base da medição e essa última nenhum arquivo de hook, de
> teste, de `settings.json` ou de workflow mudou, o que é uma pergunta
> que o próprio repositório responde:
>
> ```
> $ git diff --name-only db05586 faa6b061b874ce1b2a169778e829dd7dabcb237c | grep -cE '^\.claude/hooks/|^\.claude/settings|^\.github/workflows/'
> 0
> ```
>
> Os números deste relatório são os da segunda rodada.

## 1. A partição (VERBATIM — saída do instrumento, não digitada)

`L` = os arquivos de hook REGISTRADOS em `.claude/settings.json` na ordem
de PRIMEIRA ocorrência (itera o objeto `hooks` na ordem do ARQUIVO —
eventos, grupos, entradas; toma o basename `*.py` nomeado por cada
`command`; comandos `echo` inline pulados; dedup mantendo a primeira).
`R` = `L` menos todo arquivo que o §1 do `lote-1-S345.md` já atribui
(coluna «arquivos» daquele relatório). As fatias são
`lote2 = R[0:10]`, `lote3 = R[10:20]`, `lote4 = R[20:30]`,
**`lote5 = R[30:36]` (esta)** e `lote6 = R[36:42]` — **disjuntas por
CONSTRUÇÃO da partição, não por acordo entre as pistas**.

```
$ python3 partition.py <ROOT>
events=15 registrations=50 |L|=48
lote1_files_in_report=8 -> check_canonical_edit.py,check_bash_safety.py,check_agent_spawn.py,check_pair_rail.py,check_anti_ceo_overhead.py,adequacy_gate.py,accel_dispatch.py,audit_emit.py
removed_from_L=6 -> check_canonical_edit.py,check_bash_safety.py,check_agent_spawn.py,check_pair_rail.py,check_anti_ceo_overhead.py,accel_dispatch.py
|R|=42
R[00] check_adversary.py                         lote2
R[01] check_plan_edit.py                         lote2
R[02] check_protocol_semver_cascade.py           lote2
R[03] check_skill_patch_sentinel.py              lote2
R[04] check_tier_policy.py                       lote2
R[05] check_arbitration_kernel.py                lote2
R[06] check_scratchpad_access.py                 lote2
R[07] check_budget.py                            lote2
R[08] check_read_injection.py                    lote2
R[09] check_codex_filewrite.py                   lote2
R[10] check_cost_envelope.py                     lote3
R[11] check_worktree_writer.py                   lote3
R[12] check_config_protection.py                 lote3
R[13] check_ledger_checkpoint.py                 lote3
R[14] audit_log.py                               lote3
R[15] check_confidence_gate.py                   lote3
R[16] check_output_safety.py                     lote3
R[17] check_subagent_fabrication.py              lote3
R[18] check_skill_reference_read.py              lote3
R[19] check_output_secrets.py                    lote3
R[20] check_skill_bootstrap_post.py              lote4
R[21] check_webfetch_injection.py                lote4
R[22] check_mcp_response.py                      lote4
R[23] check_codex_response.py                    lote4
R[24] check_bash_canonical_forensic.py           lote4
R[25] SessionStart.py                            lote4
R[26] turbo_sessionstart.py                      lote4
R[27] check_compact_pinning.py                   lote4
R[28] SessionEnd.py                              lote4
R[29] UserPromptSubmit.py                        lote4
R[30] Stop.py                                    lote5  <== MINE
R[31] codex_review_user_code.py                  lote5  <== MINE
R[32] review_loop.py                             lote5  <== MINE
R[33] check_closeout_guard.py                    lote5  <== MINE
R[34] check_fluency_nudge.py                     lote5  <== MINE
R[35] check_precompact_continuity.py             lote5  <== MINE
R[36] check_postcompact_reinject.py              lote6
R[37] check_config_change.py                     lote6
R[38] check_subagent_start.py                    lote6
R[39] check_setup_verification.py                lote6
R[40] check_directory_added.py                   lote6
R[41] check_notification.py                      lote6
```

## 2. Tabela

| # | Gate | Arquivo | Registro em `.claude/settings.json` (evento / matcher; par de linhas MEDIDO) | Workflow + step de CI | Controle positivo (node id) | Como está | Enforcement removido | Verdito |
|---|------|---------|------------------------------------------------------|------------------------|-----------------------------|-----------|----------------------|---------|
| 1 | Stop | `.claude/hooks/Stop.py` | `Stop` / matcher vazio (`settings.json`: matcher l. 602 → `command` l. 606) | `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests com `CEO_NATIVE_SUBAGENTS`…» (l. 1588) **e** job `hook-tests-python-matrix`, step «Run hook + script tests on Python …» (l. 1631); também `coverage.yml:102` | `.claude/hooks/tests/test_stop.py::TestStopStaleLocks::test_release_stale_locks_releases_old` | PASS (`1 passed in 0.08s`) | **FAIL** (rc 1, `1 failed in 0.09s`) | **verde** (advisory por MEDIÇÃO — Apêndice E) |
| 2 | codex-review-user-code | `.claude/hooks/codex_review_user_code.py` | `Stop` / matcher vazio (`settings.json`: matcher l. 614 → `command` l. 618) | `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests com `CEO_NATIVE_SUBAGENTS`…» (l. 1588) **e** job `hook-tests-python-matrix`, step «Run hook + script tests on Python …» (l. 1631); também `coverage.yml:102` | `.claude/hooks/tests/test_codex_review_user_code.py::test_selftest_passes` | PASS (`1 passed in 0.22s`) | **FAIL** (rc 1, `1 failed in 0.25s`) | **verde** |
| 3 | review-loop | `.claude/hooks/review_loop.py` | `Stop` / matcher vazio (`settings.json`: matcher l. 626 → `command` l. 630) | `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests com `CEO_NATIVE_SUBAGENTS`…» (l. 1588) **e** job `hook-tests-python-matrix`, step «Run hook + script tests on Python …» (l. 1631); também `coverage.yml:102` | `.claude/hooks/tests/test_review_loop.py::test_selftest` | PASS (`1 passed in 0.85s`) | **FAIL** (rc 1, `1 failed in 0.33s`) | **verde** |
| 4 | closeout-guard | `.claude/hooks/check_closeout_guard.py` | `Stop` / matcher vazio (`settings.json`: matcher l. 638 → `command` l. 642) | `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests com `CEO_NATIVE_SUBAGENTS`…» (l. 1588) **e** job `hook-tests-python-matrix`, step «Run hook + script tests on Python …» (l. 1631); também `coverage.yml:102` | `.claude/hooks/tests/test_closeout_guard.py::TestCloseoutGuard::test_pending_finish_script_fires` | PASS (`1 passed in 0.09s`) | **FAIL** (rc 1, `1 failed in 0.10s`) | **verde** (advisory por MEDIÇÃO — Apêndice E) |
| 5 | fluency-nudge | `.claude/hooks/check_fluency_nudge.py` | `SubagentStop` / matcher vazio (`settings.json`: matcher l. 652 → `command` l. 656) | `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests com `CEO_NATIVE_SUBAGENTS`…» (l. 1588) **e** job `hook-tests-python-matrix`, step «Run hook + script tests on Python …» (l. 1631); também `coverage.yml:102` | `.claude/hooks/tests/test_check_fluency_nudge.py::IntegrationMainTests::test_main_nudges_on_many_markers_short_output` | PASS (`1 passed in 0.07s`) | **FAIL** (rc 1, `1 failed in 0.10s`) | **verde** (advisory por MEDIÇÃO — Apêndice E) |
| 6 | precompact-continuity | `.claude/hooks/check_precompact_continuity.py` | `PreCompact` / matcher vazio (`settings.json`: matcher l. 666 → `command` l. 670) | `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests com `CEO_NATIVE_SUBAGENTS`…» (l. 1588) **e** job `hook-tests-python-matrix`, step «Run hook + script tests on Python …» (l. 1631); também `coverage.yml:102` | `.claude/hooks/tests/test_check_compaction_continuity.py::TestPreCompactSnapshot::test_snapshot_written_to_scratchpad` | PASS (`1 passed in 0.17s`) | **FAIL** (rc 1, `1 failed in 0.19s`) | **verde** (advisory por MEDIÇÃO — Apêndice E) |

**Como ler a coluna 4:** cada registro é um par — a linha `"matcher"` e,
quatro linhas abaixo, a linha `"command"` que nomeia o script. As duas
são citadas porque a linha do script SOZINHA não mostra o matcher. Os
seis registros desta fatia têm **matcher vazio** (`""`): são eventos de
CICLO DE VIDA (`Stop`, `SubagentStop`, `PreCompact`), que não filtram por
ferramenta. Números de linha envelhecem — eles saem de
`dump-registrations.py` sobre o `settings.json` da base, nunca digitados.

**Caveat de CI (herdado do lote 1, re-verificado aqui):** os seis
controles vivem em `.claude/hooks/tests/`, logo os **6** rodam nos DOIS
jobs — `hook-tests-dual-rail` e `hook-tests-python-matrix` — e também no
`coverage.yml:102`. (No lote 1 esse não era o caso: o controle do
injector vive em `.claude/scripts/tests/` e fica FORA do dual-rail.) Os
dois jobs carregam `if: vars.CEO_SOTA_DISABLE != '1'` (`validate.yml`
l. 1567 e l. 1602): um admin do repo pode desligá-los por variável. O
gate existe; a EXECUÇÃO dele é condicional, e essa condição não foi
exercitada aqui.

**Contagem (PRODUZIDA pelos comandos do Apêndice D sobre a tabela deste
próprio arquivo, numa 2.ª passada do gerador — rail r1 P1-3):**
6 gates no lote; 6 com controle positivo PROVADO vermelho E restaurado verde; 0 `controle vácuo`; 0 `sem controle`; 0 `sem-controle-por-design`; 0 `UNREGISTERED`.

## 3. O que este lote NÃO afirma

- **Não classifica por leitura de docstring.** O P1 que o
  `lote-2-fix` pagou foi exatamente esse: três hooks foram chamados
  «advisory — SEMPRE allow» e um deles BLOQUEIA sob env var opt-in.
  Aqui a classe de cada arquivo é MEDIDA — Apêndice E conta os
  construtos de bloqueio e lista os env gates lidos. Resultado:
  **2 de 6 são bloqueantes** (`codex_review_user_code.py`, cujo
  bloqueio é opt-in por `CEO_CODEX_USER_REVIEW_BLOCK=1`, e
  `review_loop.py`, que bloqueia sob `CEO_REVIEW_LOOP=1` — **os DOIS
  são opt-in**, medido no fonte, não lido no docstring); os outros 4 têm ZERO
  construtos de bloqueio nas quatro formas varridas.
- **Não afirma que o controle cobre TODO o gate.** Cada linha prova UM
  caminho de enforcement — o bloqueio, o efeito ou a observação nomeada
  na coluna «mutação» do Apêndice B —, não a superfície inteira do hook.
- **Não afirma nada sobre o resto do roster.** Falta o lote 6
  (`R[36:42]`, 6 hooks); os lotes 1-4 já estão medidos em relatórios
  próprios no mesmo diretório.
- **Não re-roda o gate em produção.** O que está medido é o par
  (registro, controle), com a mutação mínima como prova de que o
  controle ENXERGA o mecanismo — não que o mecanismo é completo.

## Apêndice A — metade VERDE «como está» (6/6)

Os 6 node ids numa invocação, lidos de um arquivo para não depender de
word-splitting do shell (`node-ids.txt` vive no pack da sessão e é, por
construção, o MESMO conjunto do Apêndice B — o campo `node` do
`red-half.json`):

```
$ xargs python3 -m pytest -q --no-header -p no:cacheprovider < node-ids.txt
6 passed in 1.25s
```

## Apêndice B — metade VERMELHA, gate a gate

Para cada linha: `git restore` → mutação mínima → **mesmo** node id →
`git restore`. Todas as 6 retornaram `rc 1`.

| # | Gate | Mutação mínima aplicada (contagem de âncora EXIGIDA; o instrumento RECUSA se divergir) — e o que ela mata | Resultado |
|---|------|--------------------------------------------------------------|-----------|
| 1 | Stop | '    released = 0\n    try:\n' -> '    return 0\n    released = 0\n    try:\n' (x1) — mata SÓ a liberação de locks obsoletos; `_emit_session_stop` continua sendo chamado e o controle escolhido NÃO o exercita | `1 failed in 0.09s` |
| 2 | codex-review-user-code | 'return {"decision": "block", "reason": msg}' -> 'return _allow(msg)' (x2) — mata os DOIS sítios de bloqueio (o Stop deixa de ser barrado sob `CEO_CODEX_USER_REVIEW_BLOCK=1`) | `1 failed in 0.25s` |
| 3 | review-loop | '"decision": "block",' -> '"decision": "allow",' (x1) — mata o único sítio de bloqueio (o Stop deixa de ser barrado sob `CEO_REVIEW_LOOP=1`) | `1 failed in 0.33s` |
| 4 | closeout-guard | '        messages.append("Owner GPG ceremony pending: " + ", ".join(pending))' -> '        pass' (x1) — mata a linha «Owner GPG ceremony pending:» do `systemMessage` | `1 failed in 0.10s` |
| 5 | fluency-nudge | '    sys.stdout.write(_emit_allow(system_message=msg) + "\\n")' -> '    sys.stdout.write(_emit_allow() + "\\n")' (x1) — mata SÓ o argumento da mensagem `ARTIFACT-PARADOX-NUDGE`; `_emit_fluency_nudge_audit` roda ANTES e o controle NÃO o exercita | `1 failed in 0.10s` |
| 6 | precompact-continuity | '                store.set(SCRATCHPAD_KEY, store_value)' -> '                pass' (x1) — mata a escrita do blob `compaction_continuity` no scratchpad do plano | `1 failed in 0.19s` |

Registro cru das 6 rodadas: `red-half.json` no pack da sessão
(`gate`, `neuter`, `node`, `rc_green`, `rc_red`, `rc_restored`, `tail_*`).

## Apêndice C — controle de RESTAURAÇÃO (a 3.ª metade)

Sem esta terceira rodada, um vermelho poderia vir de bytecode velho e não
da mutação. O que está registrado é a SEQUÊNCIA OBSERVADA — verde →
vermelho → verde — para os 6: o vermelho aparece com a mutação presente
e desaparece com ela ausente, na mesma árvore e no mesmo node id. O
relatório afirma essa sequência, **não exclusividade causal** (rail r1
P2-6): o único artefato retido é a linha final do pytest, e
`PYTHONDONTWRITEBYTECODE=1` impede a ESCRITA de bytecode, não a leitura
de um cache pré-existente.

| # | Gate | 1.ª metade (como está) | 3.ª metade (depois do `git restore`) |
|---|------|------------------------|---------------------------------------|
| 1 | Stop | `1 passed in 0.08s` | `1 passed in 0.07s` |
| 2 | codex-review-user-code | `1 passed in 0.22s` | `1 passed in 0.21s` |
| 3 | review-loop | `1 passed in 0.85s` | `1 passed in 0.84s` |
| 4 | closeout-guard | `1 passed in 0.09s` | `1 passed in 0.09s` |
| 5 | fluency-nudge | `1 passed in 0.07s` | `1 passed in 0.08s` |
| 6 | precompact-continuity | `1 passed in 0.17s` | `1 passed in 0.16s` |

## Apêndice D — contagem derivada, não digitada

A linha de contagem do §2 sai de comandos sobre a PRÓPRIA tabela deste
arquivo. Cuidado medido (herdado do lote 1): `^\| [0-9]+ \|` sozinho casa
as linhas do §2 E as dos Apêndices B e C, todas numeradas. O
discriminante é o node id (`::`), que só existe nas linhas do §2:

```
grep -cE '^\| [0-9]+ \|.*::' .claude/plans/PLAN-171/w0/lote-5-S347.md                # 6  (linhas do §2)
grep -cE '^\| [0-9]+ \|.*::.*\*\*verde\*\*' .claude/plans/PLAN-171/w0/lote-5-S347.md   # 6  (verdito verde)
grep -cE '^\| [0-9]+ \|.*::.*vácuo' .claude/plans/PLAN-171/w0/lote-5-S347.md         # 0
grep -cE '^\| [0-9]+ \|.*::.*sem controle' .claude/plans/PLAN-171/w0/lote-5-S347.md  # 0
grep -cE '^\| [0-9]+ \|.*::.*sem-controle-por-design' .claude/plans/PLAN-171/w0/lote-5-S347.md  # 0
grep -cE '^\| [0-9]+ \|.*::.*UNREGISTERED' .claude/plans/PLAN-171/w0/lote-5-S347.md  # 0
grep -cE '^\| [0-9]+ \|.*\(x[0-9]+\).*1 failed in' .claude/plans/PLAN-171/w0/lote-5-S347.md  # 6  (Apêndice B)
```

**Cuidado NOVO, pago pelo rail r1 (P1-1):** `1 failed in` aparece nas
DUAS tabelas — a célula «Enforcement removido» do §2 cita a mesma cauda
do pytest que o Apêndice B. Sem discriminante o comando devolve **12**,
não 6. O discriminante é `(xN)`, a contagem de âncora exigida, que só
existe na coluna de mutação do Apêndice B.

Os SEIS números da linha de contagem do §2 saem dos seis primeiros
comandos, um por número — e o gerador os EXECUTA sobre o documento
montado antes de escrever a linha, em vez de re-imprimir variáveis.

Os sete comandos acima rodam sobre este arquivo já commitado: se um
número citado aqui divergir do que o comando imprime na árvore, o
comando é a autoridade e o relatório está errado.

## Apêndice E — a classe de cada hook, MEDIDA (não lida no docstring)

Varredura de quatro formas de recusa sobre o fonte de cada arquivo
(`measure-blocking.py`), mais os env gates que o arquivo lê:

| Arquivo | `"decision":"block"` | `"permissionDecision":"deny"` | `"continue": False` | `sys.exit(2)` | Classe MEDIDA | Env gates lidos (`*` = via CONSTANTE de módulo) |
|---|---|---|---|---|---|---|
| `Stop.py` | 0 | 0 | 0 | 0 | advisory (zero construtos de bloqueio) | `CEO_EXTENDED_LIFECYCLE`\* |
| `codex_review_user_code.py` | 2 | 0 | 0 | 0 | bloqueante | `CEO_CODEX_USER_REVIEW`, `CEO_CODEX_USER_REVIEW_AUTO`, `CEO_CODEX_USER_REVIEW_BLOCK`, `CEO_REVIEW_LOOP_STATE` |
| `review_loop.py` | 1 | 0 | 0 | 0 | bloqueante | `CEO_REVIEW_LOOP`\*, `CEO_REVIEW_LOOP_STATE` |
| `check_closeout_guard.py` | 0 | 0 | 0 | 0 | advisory (zero construtos de bloqueio) | `CEO_CLOSEOUT_GUARD`, `CEO_SESSION_START_HEAD` |
| `check_fluency_nudge.py` | 0 | 0 | 0 | 0 | advisory (zero construtos de bloqueio) | `CEO_AUDIT_LOG_DIR`, `CEO_FLUENCY_NUDGE`, `CEO_SUBAGENT_LIFECYCLE`, `CEO_SUBAGENT_LIFECYCLE_STATE_DIR`, `CEO_SUBAGENT_TRANSCRIPT_ROOT` |
| `check_precompact_continuity.py` | 0 | 0 | 0 | 0 | advisory (zero construtos de bloqueio) | `CEO_COMPACTION_CONTINUITY`, `CEO_CONTEXT_PROGRESS_FLOOR_TOKENS`\*, `CEO_STATUSLINE_SIDECAR` |

Leitura: `codex_review_user_code.py` tem DOIS sítios de bloqueio, ambos
guardados por `CEO_CODEX_USER_REVIEW_BLOCK=1` — sem a variável ele
ADVERTE; com ela, BLOQUEIA. `review_loop.py` é também **opt-in**:
`review_loop.py:42` define `_KILL_SWITCH_ENV = "CEO_REVIEW_LOOP"` e
`:200` faz `decide()` devolver `{}` quando a variável não é `"1"` —
o próprio selftest a LIGA antes de exercitar o bloqueio. A versão
anterior deste parágrafo dizia «bloqueia por padrão»; era falso, e o
rail r1 (P1-2) a derrubou citando as duas linhas. A coluna «Env gates
lidos» marca com `*` os nomes que o fonte passa por CONSTANTE de módulo
e não por literal — antes do P1-5 o instrumento não os via, e `Stop.py`
aparecia sem nenhum gate quando lê `CEO_EXTENDED_LIFECYCLE`. Os outros quatro não têm nenhuma das
quatro formas: a metade VERMELHA deles prova um EFEITO (liberação de
lock, escrita de snapshot) ou uma OBSERVAÇÃO nomeada
(`systemMessage`), que é o que o método do W0 pede de um hook
observador.

## Apêndice F — o que o lote consumiu como INPUT (rastreável)

- `.claude/plans/PLAN-171-governance-imports-provenance.md` §5, §6, §7.
- `.claude/plans/PLAN-171/w0/lote-1-S345.md` §1 (a coluna de arquivos que
  define o conjunto removido de `L`) e seu Apêndice C (a forma da
  contagem derivada).
- `.claude/settings.json` (registro por evento/matcher, via `json.load`).
- `.github/workflows/validate.yml`, `coverage.yml` (quem executa);
  `mutation-gate.yml` foi lido e **não** muta nenhum dos 6 arquivos
  desta fatia.
