# PLAN-171 W0 — censo de gates com controle positivo, lote 6/6 (S347)

> **Escopo.** A ÚLTIMA fatia da partição determinística do W0:
> `R[36:42]` — `check_postcompact_reinject.py`, `check_config_change.py`, `check_subagent_start.py`, `check_setup_verification.py`, `check_directory_added.py`, `check_notification.py`.
> **Método (a regra do W0):** um gate só é VERDE quando existe um
> controle positivo que (i) passa na árvore como está, (ii) **FALHA**
> **quando o enforcement é removido** e (iii) volta a passar depois do
> `git restore`. A metade RED é obrigatória — um controle que continua
> verde sem o enforcement é `controle vácuo`. A TERCEIRA metade é o
> **controle de restauração** herdado do lote 2: no macOS o bytecode
> vai para `sys.pycache_prefix`, e sem ela um `.pyc` velho falsifica a
> medição. Medido em 2026-09-06 numa worktree descartável
> (`git worktree add --detach`), um gate por vez, `git restore` entre
> cada um. **Nenhuma edição na árvore viva.** Base:
> `HEAD = 7036a0327681`.

**Deriva de base, MEDIDA.** O `HEAD` vivo no momento desta derivação é
`7f6b56477bb3`; a medição foi feita em `7036a0327681`. Entre os dois
mudaram **35** arquivo(s), dos quais **0** pertencem às classes de que
este censo depende (`.claude/settings*.json`, `.claude/hooks/**`,
`.github/workflows/**`). O comando que produz esses dois números
é `git diff --name-only <census_head> <HEAD>` filtrado por essas três
famílias — está no `EVIDENCE.md` do pack, com a saída crua.

## 1. A partição (determinística, computada — não digitada)

`L` = os arquivos de hook REGISTRADOS em `.claude/settings.json`, na
ordem de primeira ocorrência (iterando o objeto `hooks` na ordem do
arquivo — eventos, grupos, entradas; o basename `*.py` de cada
`command`; comandos `echo` inline pulados; dedupe mantendo a primeira
ocorrência). Dele saem os arquivos que o §1 do `lote-1-S345.md`
atribui (a linha que nomeia DOIS arquivos remove os dois). O resto,
`R`, mantém a ordem de `L`.

Medido por `gen-count.py` sobre o `settings.json`: **|L| = 48** arquivos distintos em **49 registrações** de hook `.py`.

Resta **|R| = 42**, na ordem de `L` — e a tabela abaixo tem exatamente 42 linhas `R[..]`, das quais **6** marcadas como deste lote (o gerador RECUSA emitir se qualquer um dos três números divergir). `lote 2 = R[0:10]`; `lote 3 = R[10:20]`; `lote 4 = R[20:30]`; `lote 5 = R[30:36]`; **`lote 6 = R[36:42]` (este relatório — a ÚLTIMA fatia)**.

| índice | arquivo | fatia |
|---|---|---|
| R[00] | `check_adversary.py` | lote 2 |
| R[01] | `check_plan_edit.py` | lote 2 |
| R[02] | `check_protocol_semver_cascade.py` | lote 2 |
| R[03] | `check_skill_patch_sentinel.py` | lote 2 |
| R[04] | `check_tier_policy.py` | lote 2 |
| R[05] | `check_arbitration_kernel.py` | lote 2 |
| R[06] | `check_scratchpad_access.py` | lote 2 |
| R[07] | `check_budget.py` | lote 2 |
| R[08] | `check_read_injection.py` | lote 2 |
| R[09] | `check_codex_filewrite.py` | lote 2 |
| R[10] | `check_cost_envelope.py` | lote 3 |
| R[11] | `check_worktree_writer.py` | lote 3 |
| R[12] | `check_config_protection.py` | lote 3 |
| R[13] | `check_ledger_checkpoint.py` | lote 3 |
| R[14] | `audit_log.py` | lote 3 |
| R[15] | `check_confidence_gate.py` | lote 3 |
| R[16] | `check_output_safety.py` | lote 3 |
| R[17] | `check_subagent_fabrication.py` | lote 3 |
| R[18] | `check_skill_reference_read.py` | lote 3 |
| R[19] | `check_output_secrets.py` | lote 3 |
| R[20] | `check_skill_bootstrap_post.py` | lote 4 |
| R[21] | `check_webfetch_injection.py` | lote 4 |
| R[22] | `check_mcp_response.py` | lote 4 |
| R[23] | `check_codex_response.py` | lote 4 |
| R[24] | `check_bash_canonical_forensic.py` | lote 4 |
| R[25] | `SessionStart.py` | lote 4 |
| R[26] | `turbo_sessionstart.py` | lote 4 |
| R[27] | `check_compact_pinning.py` | lote 4 |
| R[28] | `SessionEnd.py` | lote 4 |
| R[29] | `UserPromptSubmit.py` | lote 4 |
| R[30] | `Stop.py` | lote 5 |
| R[31] | `codex_review_user_code.py` | lote 5 |
| R[32] | `review_loop.py` | lote 5 |
| R[33] | `check_closeout_guard.py` | lote 5 |
| R[34] | `check_fluency_nudge.py` | lote 5 |
| R[35] | `check_precompact_continuity.py` | lote 5 |
| R[36] | `check_postcompact_reinject.py` | **lote 6 (ESTE)** |
| R[37] | `check_config_change.py` | **lote 6 (ESTE)** |
| R[38] | `check_subagent_start.py` | **lote 6 (ESTE)** |
| R[39] | `check_setup_verification.py` | **lote 6 (ESTE)** |
| R[40] | `check_directory_added.py` | **lote 6 (ESTE)** |
| R[41] | `check_notification.py` | **lote 6 (ESTE)** |

Removidos de `L` por atribuição do lote 1: `check_canonical_edit.py`, `check_bash_safety.py`, `check_agent_spawn.py`, `check_pair_rail.py`, `check_anti_ceo_overhead.py`, `accel_dispatch.py`.

## 2. Tabela

| # | Gate | Arquivo(s) que implementam | Registro em `.claude/settings.json` (evento / matcher; par de linhas MEDIDO: linha do `matcher` → linha do `"command"` que nomeia o script) | Steps de CI que o COLETAM | Controle positivo (node id) | Como está | Enforcement removido | Restaurado | Verdito |
|---|---|---|---|---|---|---|---|---|---|
| 1 | postcompact-reinject | `.claude/hooks/check_postcompact_reinject.py` | `PostCompact` / `(matcher vazio)` (`settings.json`: matcher l. 680 → `command` l. 684) | 4 step(s) de CI, provados por coleção — Apêndice D | `.claude/hooks/tests/test_postcompact_reinject_no_exec_payload.py::TestFrozenPointerTemplate::test_fresh_poisoned_snapshot_emits_exactly_the_six_pointer_lines` | PASS | **FAIL** (rc 1) | PASS | **verde** |
| 2 | config-change | `.claude/hooks/check_config_change.py` | `ConfigChange` / `(matcher vazio)` (`settings.json`: matcher l. 694 → `command` l. 698) | 4 step(s) de CI, provados por coleção — Apêndice D | `.claude/hooks/tests/test_check_config_change.py::TestForbiddenKeyBlock::test_disable_all_hooks_blocks` | PASS | **FAIL** (rc 1) | PASS | **verde** |
| 3 | subagent-start | `.claude/hooks/check_subagent_start.py` | `SubagentStart` / `(matcher vazio)` (`settings.json`: matcher l. 708 → `command` l. 712) | 4 step(s) de CI, provados por coleção — Apêndice D | `.claude/hooks/tests/test_check_subagent_start.py::StartRecorderTests::test_records_start_keyed_by_hash` | PASS | **FAIL** (rc 1) | PASS | **verde** |
| 4 | setup-verification | `.claude/hooks/check_setup_verification.py` | `Setup` / `init` (`settings.json`: matcher l. 722 → `command` l. 726) | 4 step(s) de CI, provados por coleção — Apêndice D | `.claude/hooks/tests/test_env_persist_allowlist.py::SetupHookTest::test_exec_bit_check_flags_non_exec_registered_hook` | PASS | **FAIL** (rc 1) | PASS | **verde** |
| 5 | directory-added | `.claude/hooks/check_directory_added.py` | `DirectoryAdded` / `(matcher vazio)` (`settings.json`: matcher l. 736 → `command` l. 740) | 4 step(s) de CI, provados por coleção — Apêndice D | `.claude/hooks/tests/test_check_directory_added.py::TestValidShapeWritesRegistry::test_valid_event_recorded` | PASS | **FAIL** (rc 1) | PASS | **verde** |
| 6 | notification | `.claude/hooks/check_notification.py` | `Notification` / `(matcher vazio)` (`settings.json`: matcher l. 750 → `command` l. 754) | 4 step(s) de CI, provados por coleção — Apêndice D | `.claude/hooks/tests/test_check_notification.py::TestNoValueEcho::test_message_and_title_text_absent_from_log` | PASS | **FAIL** (rc 1) | PASS | **verde** |

**Contagem (contada por `gen-count.py` sobre a tabela ACIMA — uma linha plantada muda estes números; ver Apêndice C):** 6 gates no lote; **6** com controle positivo PROVADO vermelho E restaurado verde; **0** `controle vácuo`; **0** `sem controle`; **0** `sem-controle-por-design`; **0** `UNREGISTERED`.

**Como ler a coluna 4:** cada registro é um PAR — a linha `"matcher"`
e, quatro linhas abaixo, a linha `"command"` que nomeia o script. As
duas são citadas porque a linha do script SOZINHA não mostra o matcher.
Os 6 eventos desta fatia são de CICLO DE VIDA (`PostCompact`, `ConfigChange`, `SubagentStart`, `Setup`, `DirectoryAdded`, `Notification`):
5 têm `"matcher": ""` — o evento não tem superfície de ferramenta
para casar — e `Setup` filtra (`init`).
Números de linha envelhecem: o texto-âncora de cada par está no
`EVIDENCE.md` do pack, derivado por `json.load` + varredura do arquivo.

## 3. 5 dos 6 gates desta fatia são OBSERVADORES — e isso foi medido

5 das 6 linhas são classificadas ADVISORY **nos limites do detector**
**e do probe declarados abaixo** — nunca como um fato incondicional
sobre o hook. Nelas o controle positivo assere um mecanismo de
OBSERVAÇÃO (o §4 diz qual, por linha), não o bloqueio de uma
ferramenta. Chamar um gate de «advisory» sem medir todo
switch que o faz bloquear é exatamente o defeito que o lote 2 pagou
depois do land, então esta fatia herda o instrumento e roda as três
derivações antes de usar a palavra (`measure-optin.py`, saída bruta em
`payload/optin-measurement.json`; detalhe por hook no Apêndice E):

| # | Gate | construtos de BLOQUEIO das formas procuradas | switches ENCONTRADOS pelo detector estático (consumidos ∪ documentados) | rodadas do probe (`—` = linha sem probe) | rodadas que BLOQUEARAM | como a linha se descarrega |
|---|---|---|---|---|---|---|
| 1 | postcompact-reinject | 0 | 3 | 7 | 0 | sem-construto-de-bloqueio + probe dinâmico |
| 2 | config-change | 3 | 2 | — | — | medido-no-apêndice-B |
| 3 | subagent-start | 0 | 3 | 5 | 0 | sem-construto-de-bloqueio + probe dinâmico |
| 4 | setup-verification | 0 | 6 | 11 | 0 | sem-construto-de-bloqueio + probe dinâmico |
| 5 | directory-added | 0 | 2 | 3 | 0 | sem-construto-de-bloqueio + probe dinâmico |
| 6 | notification | 0 | 2 | 5 | 0 | sem-construto-de-bloqueio + probe dinâmico |

**A coluna dos switches é ESTÁTICA.** Ela conta as env `CEO_`/
`CLAUDE_` que o detector encontra no arquivo (consumidas por getter
reconhecido ∪ citadas no docstring) — **não** switches que foram
sondados. Quem foi sondado está na coluna «rodadas do probe»: a
linha com construto de bloqueio não roda probe (`—`), porque se
descarrega pelo controle positivo do Apêndice B; as demais rodam
uma rodada sem switch mais uma por par (switch, valor).

O probe carrega seu PRÓPRIO controle positivo — o mesmo runner e o
mesmo classificador contra um hook que BLOQUEIA
(`.claude/hooks/check_config_protection.py`): sem ele, «nenhum bloqueio observado»
não vale nada. Ele voltou `BLOCK` (rc 0), e o instrumento RECUSA
escrever a saída se não voltar.

**Limite declarado do detector:** ele lê o ARQUIVO do hook, sem seguir
`import`, e exige chave E valor LITERAIS no construto. «Zero
construtos» é um fato derivado sobre AQUELAS FORMAS NAQUELE ARQUIVO —
nunca prova de que nenhuma configuração faz o hook bloquear.

## 4. O que este lote NÃO afirma

- Não afirma que o controle cobre TODO o gate: cada linha prova UM
  mecanismo, e QUAL mecanismo está declarado por linha no campo
  `proves` do `red-half.json` (ao lado da mutação que o estabelece):
  - linha 1 (postcompact-reinject): a EMISSÃO da observação (o bloco de pointers do `additionalContext`).
  - linha 2 (config-change): a DECISÃO de bloqueio advisory.
  - linha 3 (subagent-start): a GRAVAÇÃO do sidecar de spawn (a observação).
  - linha 4 (setup-verification): a EMISSÃO do achado exec-bit (a observação).
  - linha 5 (directory-added): a ESCRITA do root no registro de sessão (a observação).
  - linha 6 (notification): o SCRUB de não-eco (hash em vez do corpo) — **não** que a observação seja emitida.
  Nenhuma delas prova a superfície inteira do hook.
- Não afirma nada sobre a EXECUÇÃO condicional do CI. O Apêndice D
  atribui **4** job(s) distintos a cada controle (`coverage.yml`/`coverage`, `release.yml`/`release-gate`, `validate.yml`/`hook-tests-dual-rail`, `validate.yml`/`hook-tests-python-matrix`);
  **2 deles** — os de `validate.yml` (`hook-tests-dual-rail`, `hook-tests-python-matrix`) — carregam
  `if: vars.CEO_SOTA_DISABLE != '1'` (l. 1567, l. 1602). O gate existe; um
  admin do repo pode desligar ESSES dois por variável, e essa condição
  não foi exercitada aqui. Os demais jobs têm condições próprias que
  este pack NÃO mediu.
- A coluna «Steps de CI que o COLETAM» foi derivada por COLEÇÃO: os
  alvos de pytest de cada step são replicados com `--collect-only`, e
  o step só conta se o node id APARECE no conjunto coletado. Os
  seletores `-m`/`-k` do step são REPLAYADOS também, com as expressões
  `${{ matrix.* }}` expandidas pelos valores declarados no próprio
  workflow. Seletor dos steps que SOBREVIVEM ao replay: `-m 'not serial'`.
  **Medido:** 2 step(s) COLETAM o alvo mas o próprio seletor
  DESELECIONA todos os 6 controles desta fatia, em TODAS as
  expansões de matriz (`matrix.filter=canonical_guard`, `matrix.filter=hmac`, `matrix.filter=pair_rail`, `matrix.filter=redact`) — logo NÃO executam nenhum deles e
  saíram da contagem de steps:
  `mutation-gate.yml` job `mutate`, step «AC2a — fail fast if the leg filter selects 0 tests» (l. 105), seletor `-k "${{ matrix.filter }} and not spool_drain"`.
  `mutation-gate.yml` job `mutate`, step «baseline test run (leg filter)» (l. 117), seletor `-k "${{ matrix.filter }} and not spool_drain"`.
  O que continua NÃO afirmado: a EXECUÇÃO condicional do job (o `if:`
  do `CEO_SOTA_DISABLE` acima) e que o par `hook-tests-dual-rail` + `hook-tests-python-matrix` cubra o conjunto
  inteiro.
- A metade RED foi obtida removendo o enforcement do jeito MÍNIMO
  (Apêndice B); ela prova que o controle enxerga aquele mecanismo, não
  que o mecanismo é completo.
- Nenhuma linha herda dívida: as três dívidas do AC-9 do PLAN-169 já
  foram auditadas e declaradas não-herdadas no §2 do `lote-1-S345.md`.

## 5. Esta é a ÚLTIMA fatia — e o que o W0 ainda deve DEPOIS dela

`R[36:42]` é a última fatia por índice: `lote 2 = R[0:10]`,
`lote 3 = R[10:20]`, `lote 4 = R[20:30]`, `lote 5 = R[30:36]`,
`lote 6 = R[36:42]`. **Ser a última NÃO quer dizer que `R` já esteja
coberto:** a cobertura só fecha quando os SEIS relatórios existirem, e
nenhum deles falta em disco (medido logo abaixo).

Estado MEDIDO de `.claude/plans/PLAN-171/w0/` no momento desta
derivação (`os.listdir`, não memória): `lote-1-S345.md`, `lote-2-S347.md`, `lote-3-S347.md`, `lote-4-S347.md`, `lote-5-S347.md`.
Descontando o relatório DESTE pack (o do lote 6, que a derivação
acrescenta), não falta nenhum outro.
Que os lotes ausentes estejam rodando em paralelo é o que o briefing
desta lane diz — **não** é algo que este pack meça.

**O que o W0 ainda deve, depois deste pack:** (i) nenhum relatório de lote;
(ii) nenhuma linha de `Registro de execução` — todo relatório em disco já tem a sua
(MEDIDO sobre o plano VIVO: os lotes com entrada datada na seção
`Registro de execução` são 1, 2, 3, 4, 5, contra os relatórios em disco 1, 2, 3, 4, 5);
(iii) a consolidação dos seis num veredito único de W0; e (iv) as
dívidas que os relatórios JÁ em disco declaram, MEDIDAS abaixo.
Nenhuma das quatro é entregue por este pack.

**Dívidas já declaradas pelos relatórios em disco** (varredura das
linhas de tabela pelos veredictos do método — `sem controle`,
`controle vácuo`, `sem-controle-por-design`, `UNREGISTERED`):
- `lote-3-S347.md` → `check_cost_envelope.py`: **sem controle**.

**Arquivos de hook que `L` não alcança, medido:** `L` é o roster de
`settings.json` (48 arquivos). Em `.claude/hooks/` existem hoje **59**
arquivos `*.py`, logo **11** deles não são registrados por
`settings.json` e ficam FORA de `R` por construção — entre eles `adequacy_gate.py`, `auto_boot.py`, `check_codex_stop_review.py`, `check_harness_config.py`, `check_tier_policy_misrouting_24h.py`, `emit_architect_outcome.py`, ….
Um gate pode ser executado por CI ou registrado noutro registry sem
aparecer em `L`; o §5 do `lote-2-S347.md` é onde essa classe está
declarada. Fechar os seis lotes NÃO fecha essa classe.

**O que a partição não alcança, e a exceção que o lote 1 já abriu.**
`L` é o roster de `settings.json` e nada além: gates que não são hooks
registrados — scripts de CI (`.github/scripts/*`), guards de release e
os `.claude/scripts/*` de operador — estão FORA de `L` e portanto fora
de toda fatia `R[i:j]`. Isso **não** é o mesmo que dizer que nenhum
lote os cobriu: o lote 1 NÃO foi definido por esta partição (ele veio
do §7 «Runbook sessão 1» do PLAN-171) e a sua linha 8 audita
`.claude/scripts/inject-agent-context.sh`, que é exatamente um script
de operador. O que os lotes 2-6 declaram é que a partição `R` não os
alcança — não que ninguém os tenha auditado.

## Apêndice A — baseline «como está» (6/6 verde)

Os 6 node ids da coluna «Controle positivo» do §2, numa invocação, lidos
de um arquivo para não depender de word-splitting do shell:

```
xargs python3 -m pytest -q --no-header -p no:cacheprovider < node-ids.txt
```

`node-ids.txt` sai do campo `node` do `red-half.json` — logo o conjunto
que passou aqui é, por construção, o MESMO que foi ao vermelho no
Apêndice B. A saída verbatim está no `EVIDENCE.md` do pack.

## Apêndice B — as três metades, gate a gate

Para cada linha: `git restore` → **como está** → mutação mínima →
**MESMO** node id → `git restore` → **MESMO** node id outra vez.

| # | Gate | Mutação mínima aplicada | Como está | Enforcement removido | Restaurado |
|---|------|--------------------------|-----------|----------------------|------------|
| 1 | postcompact-reinject | `-     pointers = _build_pointers(plan_id, snapshot, age_s)` <br> `+     pointers = []` | 1 passed in 0.13s (rc 0) | **1 failed in 0.13s** (rc 1) | 1 passed in 0.12s (rc 0) |
| 2 | config-change | `-     return {"decision": "block", "reason": _block_reason(forbidden)}` <br> `+     return {}` | 1 passed in 0.09s (rc 0) | **1 failed in 0.11s** (rc 1) | 1 passed in 0.09s (rc 0) |
| 3 | subagent-start | `-         entries[_agent_key(agent_id)] = entry` <br> `+         pass` | 1 passed in 0.09s (rc 0) | **1 failed in 0.11s** (rc 1) | 1 passed in 0.09s (rc 0) |
| 4 | setup-verification | `-         if not (st.st_mode & 0o100):  # S_IXUSR` <br> `+         if False:  # S_IXUSR` | 1 passed in 0.08s (rc 0) | **1 failed in 0.11s** (rc 1) | 1 passed in 0.08s (rc 0) |
| 5 | directory-added | `-         roots.append(new_root)` <br> `+         pass` | 1 passed in 0.08s (rc 0) | **1 failed in 0.10s** (rc 1) | 1 passed in 0.09s (rc 0) |
| 6 | notification | `-         message_sha256_prefix=_message_prefix(event.get("message")),` <br> `+         message_sha256_prefix=str(event.get("message") or ""),` | 1 passed in 0.09s (rc 0) | **1 failed in 0.11s** (rc 1) | 1 passed in 0.09s (rc 0) |

Registro cru das 18 rodadas: `red-half.json` no pack (`gate`, `path`,
`neuter_old`, `neuter_new`, `neuter_diff`, `node`, e o `rc` + a última
linha de saída das TRÊS metades).

## Apêndice C — contagem derivada, não digitada

A linha de contagem do §2 sai de comandos sobre a PRÓPRIA tabela
deste arquivo, e os números abaixo são MEDIDOS sobre o documento
montado, não digitados. Discriminante medido (a mesma armadilha
do lote 1): `^\| [0-9]+ \|` sozinho casa **todas** as tabelas
numeradas do arquivo — hoje 18 linhas: 6 no §2, 6 no §3, 6 no
Apêndice B. O que separa o §2 é o node id (`::`);
simetricamente `1 failed in` só existe no Apêndice B.

```
grep -cE '^\| [0-9]+ \|' .claude/plans/PLAN-171/w0/lote-6-S347.md   # 18  (todas as tabelas numeradas do arquivo)
grep -cE '^\| [0-9]+ \|.*::' .claude/plans/PLAN-171/w0/lote-6-S347.md   # 6  (linhas do §2 COM node id)
grep -cE '^\| [0-9]+ \|.*\*\*verde\*\*' .claude/plans/PLAN-171/w0/lote-6-S347.md   # 6  (veredito verde)
grep -cE '^\| [0-9]+ \|.*\*\*sem controle\*\*' .claude/plans/PLAN-171/w0/lote-6-S347.md   # 0  (veredito sem controle)
grep -cE '^\| [0-9]+ \|.*controle vácuo' .claude/plans/PLAN-171/w0/lote-6-S347.md   # 0  (veredito controle vácuo)
grep -cE '^\| [0-9]+ \|.*1 failed in' .claude/plans/PLAN-171/w0/lote-6-S347.md   # 6  (linhas do Apêndice B)
grep -cE '^\| R\[' .claude/plans/PLAN-171/w0/lote-6-S347.md   # 42  (linhas da tabela de partição do §1)
```

6 verde + 0 vácuo + 0 sem controle = 6 = |lote 6|. As saídas
medidas estão no `EVIDENCE.md` do pack, geradas por
`gen-evidence.py` sobre a derivação FINAL — nenhum número acima
foi digitado.

## Apêndice D — quem COLETA o quê (medido nos workflows)

| Controle | Vive em | Job + step que o COLETA e cujo seletor `-m`/`-k` NÃO o deseleciona (ambos replayados) |
|---|---|---|
| `test_postcompact_reinject_no_exec_payload.py` | `.claude/hooks/tests` | `coverage.yml` job `coverage`, step «Run hook tests under coverage (subprocess capture, parallel)» (l. 102); `release.yml` job `release-gate`, step «Hook test suite (all 168+ tests)» (l. 390); `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests with CEO_NATIVE_SUBAGENTS=${{ matrix.native_subagents }}» (l. 1594); `validate.yml` job `hook-tests-python-matrix`, step «Run hook + script tests on Python ${{ matrix.python-version }}» (l. 1644) |
| `test_check_config_change.py` | `.claude/hooks/tests` | `coverage.yml` job `coverage`, step «Run hook tests under coverage (subprocess capture, parallel)» (l. 102); `release.yml` job `release-gate`, step «Hook test suite (all 168+ tests)» (l. 390); `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests with CEO_NATIVE_SUBAGENTS=${{ matrix.native_subagents }}» (l. 1594); `validate.yml` job `hook-tests-python-matrix`, step «Run hook + script tests on Python ${{ matrix.python-version }}» (l. 1644) |
| `test_check_subagent_start.py` | `.claude/hooks/tests` | `coverage.yml` job `coverage`, step «Run hook tests under coverage (subprocess capture, parallel)» (l. 102); `release.yml` job `release-gate`, step «Hook test suite (all 168+ tests)» (l. 390); `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests with CEO_NATIVE_SUBAGENTS=${{ matrix.native_subagents }}» (l. 1594); `validate.yml` job `hook-tests-python-matrix`, step «Run hook + script tests on Python ${{ matrix.python-version }}» (l. 1644) |
| `test_env_persist_allowlist.py` | `.claude/hooks/tests` | `coverage.yml` job `coverage`, step «Run hook tests under coverage (subprocess capture, parallel)» (l. 102); `release.yml` job `release-gate`, step «Hook test suite (all 168+ tests)» (l. 390); `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests with CEO_NATIVE_SUBAGENTS=${{ matrix.native_subagents }}» (l. 1594); `validate.yml` job `hook-tests-python-matrix`, step «Run hook + script tests on Python ${{ matrix.python-version }}» (l. 1644) |
| `test_check_directory_added.py` | `.claude/hooks/tests` | `coverage.yml` job `coverage`, step «Run hook tests under coverage (subprocess capture, parallel)» (l. 102); `release.yml` job `release-gate`, step «Hook test suite (all 168+ tests)» (l. 390); `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests with CEO_NATIVE_SUBAGENTS=${{ matrix.native_subagents }}» (l. 1594); `validate.yml` job `hook-tests-python-matrix`, step «Run hook + script tests on Python ${{ matrix.python-version }}» (l. 1644) |
| `test_check_notification.py` | `.claude/hooks/tests` | `coverage.yml` job `coverage`, step «Run hook tests under coverage (subprocess capture, parallel)» (l. 102); `release.yml` job `release-gate`, step «Hook test suite (all 168+ tests)» (l. 390); `validate.yml` job `hook-tests-dual-rail`, step «Run hook tests with CEO_NATIVE_SUBAGENTS=${{ matrix.native_subagents }}» (l. 1594); `validate.yml` job `hook-tests-python-matrix`, step «Run hook + script tests on Python ${{ matrix.python-version }}» (l. 1644) |

Os 6 controles desta fatia vivem TODOS em `.claude/hooks/tests/` — um único diretório —
e cada um é COLETADO pelo MESMO conjunto de 4 step(s) de CI —
«coletado» e não «executado»: o replay honra os ALVOS de pytest E os
seletores `-m`/`-k` do step, mas não a condição `if:` do job nem o
ambiente do runner — aparecer aqui é condição NECESSÁRIA para o step
rodar o controle, não suficiente. Os steps cujo seletor deseleciona
a fatia inteira estão nomeados no §4 e ficam FORA desta tabela.
Contraste com o lote 1, onde a linha do injector vivia em
`.claude/scripts/tests/` e ficava FORA do `hook-tests-dual-rail`: aqui
os dois jobs de `validate.yml` (`hook-tests-dual-rail`, `hook-tests-python-matrix`) coletam
os 6.

## Apêndice E — a medição de opt-in, hook a hook

Formas de BLOQUEIO procuradas pelo detector (a tabela de chaves de
decisão do instrumento, não prosa):

- chamada `*.block(...)` (AST)
- dicionário literal com `"decision": "block"` (AST, multilinha e aninhado inclusive)
- comparação com literal — `<x>.get("decision") == "block"` ou `<x>["decision"] == "block"` (AST)
- varredura de texto de reforço: `"decision"` seguido de `"block"` na mesma linha (pega o que o AST não parseie)
- dicionário literal com `"permissionDecision": "deny"` (AST, multilinha e aninhado inclusive)
- comparação com literal — `<x>.get("permissionDecision") == "deny"` ou `<x>["permissionDecision"] == "deny"` (AST)
- varredura de texto de reforço: `"permissionDecision"` seguido de `"deny"` na mesma linha (pega o que o AST não parseie)

### `.claude/hooks/check_postcompact_reinject.py`

- construtos de BLOQUEIO das formas procuradas, neste arquivo: **0**.
- por FORMA (todas, inclusive as zeradas): `call-block` ×0; `cmp-decision` ×0; `cmp-permissionDecision` ×0; `dict-decision` ×0; `dict-permissionDecision` ×0; `text-decision` ×0; `text-permissionDecision` ×0.
- env `CEO_`/`CLAUDE_` que o módulo CONSOME por getter reconhecido: `CEO_COMPACTION_CONTINUITY`, `CEO_CONSTRAINT_PINNING`.
- env que o docstring MENCIONA: `CEO_COMPACTION_CONTINUITY`, `CEO_CONSTRAINT_PINNING`, `CLAUDE_SESSION_ID`.
- descarga: **sem-construto-de-bloqueio + probe dinâmico** — 7 rodada(s) fim-a-fim (sem switch, e cada
  par switch×valor), **0** classificada(s) como BLOCK.

### `.claude/hooks/check_config_change.py`

- construtos de BLOQUEIO das formas procuradas, neste arquivo: **3**.
- por FORMA (todas, inclusive as zeradas): `call-block` ×0; `cmp-decision` ×0; `cmp-permissionDecision` ×0; `dict-decision` ×1; `dict-permissionDecision` ×0; `text-decision` ×2; `text-permissionDecision` ×0.
- env `CEO_`/`CLAUDE_` que o módulo CONSOME por getter reconhecido: `CEO_CONFIG_CHANGE_GUARD`, `CLAUDE_PROJECT_DIR`.
- env que o docstring MENCIONA: `CEO_CONFIG_CHANGE_GUARD`.
- descarga: **medido-no-apêndice-B** — node id `.claude/hooks/tests/test_check_config_change.py::TestForbiddenKeyBlock::test_disable_all_hooks_blocks`, rc 1 (`1 failed in 0.11s`), lido do
  `red-half.json` (a MESMA fonte do Apêndice B; o gerador
  RECUSA emitir se o snapshot do `measure-optin.py` apontar
  para outro node id ou outro `rc`).

### `.claude/hooks/check_subagent_start.py`

- construtos de BLOQUEIO das formas procuradas, neste arquivo: **0**.
- por FORMA (todas, inclusive as zeradas): `call-block` ×0; `cmp-decision` ×0; `cmp-permissionDecision` ×0; `dict-decision` ×0; `dict-permissionDecision` ×0; `text-decision` ×0; `text-permissionDecision` ×0.
- env `CEO_`/`CLAUDE_` que o módulo CONSOME por getter reconhecido: `CEO_AUDIT_LOG_DIR`, `CEO_SUBAGENT_LIFECYCLE`, `CEO_SUBAGENT_LIFECYCLE_STATE_DIR`.
- env que o docstring MENCIONA: `CEO_AUDIT_LOG_DIR`, `CEO_SUBAGENT_LIFECYCLE`, `CEO_SUBAGENT_LIFECYCLE_STATE_DIR`.
- descarga: **sem-construto-de-bloqueio + probe dinâmico** — 5 rodada(s) fim-a-fim (sem switch, e cada
  par switch×valor), **0** classificada(s) como BLOCK.

### `.claude/hooks/check_setup_verification.py`

- construtos de BLOQUEIO das formas procuradas, neste arquivo: **0**.
- por FORMA (todas, inclusive as zeradas): `call-block` ×0; `cmp-decision` ×0; `cmp-permissionDecision` ×0; `dict-decision` ×0; `dict-permissionDecision` ×0; `text-decision` ×0; `text-permissionDecision` ×0.
- env `CEO_`/`CLAUDE_` que o módulo CONSOME por getter reconhecido: `CEO_SETUP_VERIFICATION`, `CLAUDE_ENV_FILE`, `CLAUDE_PROJECT_DIR`.
- env que o docstring MENCIONA: `CEO_GIT_BYPASS_ALLOW`, `CEO_KERNEL_OVERRIDE`, `CEO_SETUP_VERIFICATION`, `CEO_TURBO`, `CLAUDE_ENV_FILE`.
- descarga: **sem-construto-de-bloqueio + probe dinâmico** — 11 rodada(s) fim-a-fim (sem switch, e cada
  par switch×valor), **0** classificada(s) como BLOCK.

### `.claude/hooks/check_directory_added.py`

- construtos de BLOQUEIO das formas procuradas, neste arquivo: **0**.
- por FORMA (todas, inclusive as zeradas): `call-block` ×0; `cmp-decision` ×0; `cmp-permissionDecision` ×0; `dict-decision` ×0; `dict-permissionDecision` ×0; `text-decision` ×0; `text-permissionDecision` ×0.
- env `CEO_`/`CLAUDE_` que o módulo CONSOME por getter reconhecido: `CEO_DIRECTORY_ADDED_GUARD`, `CLAUDE_PROJECT_DIR`.
- env que o docstring MENCIONA: `CEO_DIRECTORY_ADDED_GUARD`.
- descarga: **sem-construto-de-bloqueio + probe dinâmico** — 3 rodada(s) fim-a-fim (sem switch, e cada
  par switch×valor), **0** classificada(s) como BLOCK.

### `.claude/hooks/check_notification.py`

- construtos de BLOQUEIO das formas procuradas, neste arquivo: **0**.
- por FORMA (todas, inclusive as zeradas): `call-block` ×0; `cmp-decision` ×0; `cmp-permissionDecision` ×0; `dict-decision` ×0; `dict-permissionDecision` ×0; `text-decision` ×0; `text-permissionDecision` ×0.
- env `CEO_`/`CLAUDE_` que o módulo CONSOME por getter reconhecido: `CEO_NOTIFICATION_TELEMETRY`, `CLAUDE_SESSION_ID`.
- env que o docstring MENCIONA: `CEO_NOTIFICATION_TELEMETRY`, `CLAUDE_SESSION_ID`.
- descarga: **sem-construto-de-bloqueio + probe dinâmico** — 5 rodada(s) fim-a-fim (sem switch, e cada
  par switch×valor), **0** classificada(s) como BLOCK.

## Apêndice F — o que o lote consumiu como INPUT (rastreável)

- `.claude/plans/PLAN-171-governance-imports-provenance.md` §5, §6, §7.
- `.claude/plans/PLAN-171/w0/lote-1-S345.md` §1 (a atribuição que define
  o conjunto removido de `L`) e §2 (as dívidas do AC-9, já auditadas).
- `.claude/settings.json` (registro por evento/matcher/linha).
- os workflows em que a derivação por coleção acertou (`.github/workflows/coverage.yml`, `.github/workflows/release.yml`, `.github/workflows/validate.yml`)
  — a varredura leu TODOS os `*.yml`/`*.yaml` de
  `.github/workflows/`, não só esses.
- `.claude/hooks/` e `.claude/hooks/tests/` (os seis hooks e os seis
  controles).
