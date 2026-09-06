# PLAN-171 W0 — censo de gates com controle positivo, lote 2/6 (S347)

> **Escopo.** Os 10 hooks REGISTRADOS de `R[0:10]`, onde `R` é a
> partição determinística do §1. O lote 3 roda **em paralelo** sobre
> `R[10:20]` e reporta em arquivo próprio — as duas fatias são
> disjuntas por construção da partição, não por acordo.
> **Método (a regra do W0):** um gate só é VERDE quando existe um
> controle positivo que (i) passa na árvore como está e (ii) **FALHA
> quando o enforcement é removido**. A metade RED é obrigatória — um
> controle que continua verde sem o enforcement é `controle vácuo`.
> Este lote acrescenta uma TERCEIRA metade obrigatória — o **controle de
> restauração** (§4): depois do `git restore`, o MESMO node id tem de
> voltar a VERDE. Sem ela a medição é falsificável por bytecode velho, e
> este lote mediu exatamente essa falsificação acontecendo.
> Medido em 2026-09-06 numa worktree descartável (`git worktree add
> --detach`), um gate por vez, `git restore` entre cada um. Nenhuma
> edição na árvore viva. **Bases (medido, não suposto):** As duas metades foram medidas em `HEAD = 5f7f24f466c337c49700aad806a6cc7433372c5e`; a derivação é aplicada sobre `HEAD = a3425ba9a1445c4d1a0f61b269039c3249ee7762`. O delta entre os dois, RESTRITO aos diretórios que este censo lê (`.claude/settings.json`, `.claude/hooks`, `.claude/scripts`, `pytest.ini`, `.github/workflows`), foi medido por `git diff --name-only` e tem **1** arquivo(s): `.claude/hooks/tests/test_session_start.py`. Nenhum deles é um dos dez hooks, dos dez controles, do `settings.json`, do `pytest.ini` ou de um workflow — logo a medição vale para a base da derivação. O SHA da worktree de censo, a limpeza dela ao fim das trinta execuções e o transcript exato deste `git diff` estão no §1b do `EVIDENCE.md`, escritos pelo PRÓPRIO driver do censo (`measured-at.json`), não digitados.

## 1. Partição (determinística, computada — não acordada)

`L` = os ARQUIVOS de hook registrados em `.claude/settings.json`, na
ordem de PRIMEIRA ocorrência (itera o objeto `hooks` na ordem do
ARQUIVO — eventos, grupos, entradas; toma o basename `*.py` de cada
`command`; comandos `echo` inline são pulados; deduplica mantendo a
primeira). `R` = `L` menos todo arquivo que o §1 de
`.claude/plans/PLAN-171/w0/lote-1-S345.md` já atribui (a coluna
«Arquivo(s)» daquele relatório, lida do próprio arquivo). **lote 2 =
`R[0:10]`** (este relatório); **lote 3 = `R[10:20]`** (em paralelo);
**lotes 4-6 = `R[20:42]`**, devidos.
`R` cobre os hooks REGISTRADOS e mais nada — o §5 declara, com
instrumento, o que fica de FORA dele e ainda é dívida do W0.

Saída VERBATIM do instrumento (`partition.py` do pack da sessão):

```
    events=15 registrations=50 |L|=48
    lote1_files_in_report=8 -> check_canonical_edit.py,check_bash_safety.py,check_agent_spawn.py,check_pair_rail.py,check_anti_ceo_overhead.py,adequacy_gate.py,accel_dispatch.py,audit_emit.py
    removed_from_L=6 -> check_canonical_edit.py,check_bash_safety.py,check_agent_spawn.py,check_pair_rail.py,check_anti_ceo_overhead.py,accel_dispatch.py
    |R|=42
    R[00] check_adversary.py                       lote2
    R[01] check_plan_edit.py                       lote2
    R[02] check_protocol_semver_cascade.py         lote2
    R[03] check_skill_patch_sentinel.py            lote2
    R[04] check_tier_policy.py                     lote2
    R[05] check_arbitration_kernel.py              lote2
    R[06] check_scratchpad_access.py               lote2
    R[07] check_budget.py                          lote2
    R[08] check_read_injection.py                  lote2
    R[09] check_codex_filewrite.py                 lote2
    R[10] check_cost_envelope.py                   lote3
    R[11] check_worktree_writer.py                 lote3
    R[12] check_config_protection.py               lote3
    R[13] check_ledger_checkpoint.py               lote3
    R[14] audit_log.py                             lote3
    R[15] check_confidence_gate.py                 lote3
    R[16] check_output_safety.py                   lote3
    R[17] check_subagent_fabrication.py            lote3
    R[18] check_skill_reference_read.py            lote3
    R[19] check_output_secrets.py                  lote3
    R[20] check_skill_bootstrap_post.py            lote4-6
    R[21] check_webfetch_injection.py              lote4-6
    R[22] check_mcp_response.py                    lote4-6
    R[23] check_codex_response.py                  lote4-6
    R[24] check_bash_canonical_forensic.py         lote4-6
    R[25] SessionStart.py                          lote4-6
    R[26] turbo_sessionstart.py                    lote4-6
    R[27] check_compact_pinning.py                 lote4-6
    R[28] SessionEnd.py                            lote4-6
    R[29] UserPromptSubmit.py                      lote4-6
    R[30] Stop.py                                  lote4-6
    R[31] codex_review_user_code.py                lote4-6
    R[32] review_loop.py                           lote4-6
    R[33] check_closeout_guard.py                  lote4-6
    R[34] check_fluency_nudge.py                   lote4-6
    R[35] check_precompact_continuity.py           lote4-6
    R[36] check_postcompact_reinject.py            lote4-6
    R[37] check_config_change.py                   lote4-6
    R[38] check_subagent_start.py                  lote4-6
    R[39] check_setup_verification.py              lote4-6
    R[40] check_directory_added.py                 lote4-6
    R[41] check_notification.py                    lote4-6
```

Os dois números que importam e de onde vêm: `|L| = 48` arquivos
distintos em 50 registrações sobre 15 eventos (derivado do
`settings.json`, mesma aritmética que o `verify-counts.sh` publica); o
lote 1 nomeia 8 arquivos, dos quais **6** estão em `L` — os outros dois
(`adequacy_gate.py`, `audit_emit.py`) não são hooks registrados e por
isso não estavam em `L` para serem removidos. `|R| = 48 − 6 = 42`.

## 2. Tabela

| # | Gate (hook) | Arquivo | Registro em `.claude/settings.json` (evento / matcher; par de linhas MEDIDO) | Workflow + step de CI | Controle positivo (node id) | Como está | Enforcement removido | Restaurado | Verdito | O que o controle prova |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | adversary | `.claude/hooks/check_adversary.py` | `PreToolUse` / `Bash` (`settings.json`: matcher l. 160 → `command` l. 164) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_adversary_live.py::CheckAdversaryE2E::test_deny_rule_blocks_when_enforced` | PASS (`1 passed in 0.34s`) | **FAIL** (rc 1, `1 failed in 0.33s`) | PASS (`1 passed in 0.31s`) | **verde** | bloqueia o comando quando a regra é `deny` **e** o enforcement está LIGADO (`CEO_ADVERSARY`). A rota `ask` e a rota advisory-off têm testes próprios e **não** foram medidas aqui |
| 2 | plan-edit | `.claude/hooks/check_plan_edit.py` | `PreToolUse` / `Edit\|Write\|MultiEdit` (`settings.json`: matcher l. 172 → `command` l. 176) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_plan_edit.py::TestTransitions::test_draft_to_executing_blocked` | PASS (`1 passed in 0.08s`) | **FAIL** (rc 1, `1 failed in 0.09s`) | PASS (`1 passed in 0.08s`) | **verde** | bloqueia transição ilegal de status de plano |
| 3 | protocol-semver-cascade | `.claude/hooks/check_protocol_semver_cascade.py` | `PreToolUse` / `Edit\|Write\|MultiEdit` (`settings.json`: matcher l. 196 → `command` l. 200) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_protocol_semver_cascade.py::TestProtocolSemverCascadeHook::test_b_edit_protocol_without_adr_amend_warns` | PASS (`1 passed in 0.25s`) | **FAIL** (rc 1, `1 failed in 0.27s`) | PASS (`1 passed in 0.25s`) | **verde** | **advisory por desenho** — o enforcement é a OBSERVAÇÃO (`additionalContext` com o WARN), nunca um bloqueio |
| 4 | skill-patch-sentinel | `.claude/hooks/check_skill_patch_sentinel.py` | `PreToolUse` / `Edit\|Write\|MultiEdit` (`settings.json`: matcher l. 208 → `command` l. 212) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_skill_patch_sentinel.py::CheckSkillPatchSentinelTest::test_direct_skill_md_edit_without_proposal_blocks` | PASS (`1 passed in 0.26s`) | **FAIL** (rc 1, `1 failed in 0.20s`) | PASS (`1 passed in 0.26s`) | **verde** | bloqueia edição de `SKILL.md` sem proposta SP-NNN |
| 5 | tier-policy | `.claude/hooks/check_tier_policy.py` | `PreToolUse` / `Edit\|Write\|MultiEdit` (`settings.json`: matcher l. 220 → `command` l. 224) | `validate.yml` job `integration-tests` (l.1224), step «Run tier_policy_cli tests (VETO-floor + adversarial)» (l.1259; comando l.1263). **Não** roda no `hook-tests-python-matrix` nem no `hook-tests-dual-rail` (nenhum dos dois fixa `.claude/scripts/tier_policy_cli/tests`), nem no `coverage.yml`, nem no `release.yml` | `.claude/scripts/tier_policy_cli/tests/test_check_tier_policy_hook.py::CheckTierPolicyHookTests::test_veto_file_without_sentinel_blocked` | PASS (`1 passed in 0.07s`) | **FAIL** (rc 1, `1 failed in 0.09s`) | PASS (`1 passed in 0.08s`) | **verde** | bloqueia edição de agente VETO sem sentinel (VETO floor) |
| 6 | arbitration-kernel | `.claude/hooks/check_arbitration_kernel.py` | `PreToolUse` / `Edit\|Write\|MultiEdit\|mcp__.*` (`settings.json`: matcher l. 232 → `command` l. 236) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_arbitration_kernel.py::CheckArbitrationKernelTest::test_kernel_governance_hook_blocks` | PASS (`1 passed in 0.26s`) | **FAIL** (rc 1, `1 failed in 0.20s`) | PASS (`1 passed in 0.25s`) | **verde** | bloqueia edição de path do kernel de governança sem override válido |
| 7 | scratchpad-access | `.claude/hooks/check_scratchpad_access.py` | `PreToolUse` / `Bash` (`settings.json`: matcher l. 244 → `command` l. 248) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_scratchpad_access.py::TestCrossPlanGate::test_cross_plan_blocked` | PASS (`1 passed in 0.08s`) | **FAIL** (rc 1, `1 failed in 0.09s`) | PASS (`1 passed in 0.09s`) | **verde** | bloqueia acesso cross-plan ao scratchpad |
| 8 | budget | `.claude/hooks/check_budget.py` | `PreToolUse` / `Agent` (`settings.json`: matcher l. 256 → `command` l. 260) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_budget.py::TestMainEndToEnd::test_over_cap_emits_warning` | PASS (`1 passed in 0.09s`) | **FAIL** (rc 1, `1 failed in 0.10s`) | PASS (`1 passed in 0.08s`) | **verde** | **advisory por desenho** — SEMPRE allow; o enforcement é a OBSERVAÇÃO (`systemMessage` `BUDGET WARNING` + evento `budget_exceeded`) |
| 9 | read-injection | `.claude/hooks/check_read_injection.py` | `PreToolUse` / `Read` (`settings.json`: matcher l. 268 → `command` l. 272) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_read_injection.py::CheckReadInjectionTest::test_malicious_file_allows_with_system_message` | PASS (`1 passed in 0.27s`) | **FAIL** (rc 1, `1 failed in 0.28s`) | PASS (`1 passed in 0.27s`) | **verde** | **advisory por desenho** — SEMPRE allow; o enforcement é a OBSERVAÇÃO (`systemMessage` nomeando a família de injeção) |
| 10 | codex-filewrite | `.claude/hooks/check_codex_filewrite.py` | `PreToolUse` / `mcp__codex__codex\|mcp__codex__codex-reply` (`settings.json`: matcher l. 291 → `command` l. 295) | `validate.yml` job `hook-tests-python-matrix` (l.1601), step «Run hook + script tests on Python …» (l.1631; comandos l.1644/1646); também `hook-tests-dual-rail` (l.1566, comandos l.1594/1595); `coverage.yml:102`; `release.yml:390` | `.claude/hooks/tests/test_check_codex_filewrite.py::TestCanonicalPathDenial::test_hook_source_file_blocked` | PASS (`1 passed in 0.22s`) | **FAIL** (rc 1, `1 failed in 0.24s`) | PASS (`1 passed in 0.22s`) | **verde** | bloqueia escrita do codex MCP em path canônico |

**Como ler a coluna 4:** cada registro é um par — a linha `"matcher"`
e, quatro linhas abaixo, a linha `"command"` que nomeia o script; a
linha do script SOZINHA não mostra o matcher. Os dez hooks deste lote
têm **exatamente uma** registração cada (derivado do `settings.json`,
não digitado). Números de linha envelhecem — o `EVIDENCE.md` do pack
guarda a derivação COMPLETA (§7: evento, matcher, `command` e o par de
linhas, para os dez, impressos por `json.load` + varredura).

**Caveat de CI declarado:** os controles NÃO rodam todos nos mesmos
jobs. Nove vivem em `.claude/hooks/tests/` e rodam em quatro lugares
(`hook-tests-python-matrix`, `hook-tests-dual-rail`, `coverage.yml`,
`release.yml`). O décimo — o do VETO floor (`tier-policy`) — vive em
`.claude/scripts/tier_policy_cli/tests/` e roda em **um** só lugar: o
step `integration-tests` do `validate.yml`. `.claude/scripts/tier_policy_cli/tests`
ESTÁ nos `testpaths` do `pytest.ini`, então uma rodada de suíte inteira
o coleta; nenhum job de hook o pina. Os três jobs citados do
`validate.yml` carregam `if: vars.CEO_SOTA_DISABLE != '1'` — um admin
do repo pode desligá-los por variável. O gate existe; a EXECUÇÃO dele é
condicional, e essa condição não foi exercitada aqui.
Cada uma destas afirmações de configuração está QUOTADA com comando e
saída no §7b do `EVIDENCE.md` (as invocações `pytest` de cada job, os
`testpaths` do `pytest.ini`, as linhas `if:` e os quatro legs do
`mutation-gate.yml`); referência de linha sozinha não prova inclusão, e
esse era um achado de rail.

**Contagem (derivada por comando — ver Apêndice C):** 10 gates no lote;
10 com controle positivo PROVADO vermelho E provado verde de novo após
restauração; 0 `controle vácuo`; 0 `sem controle`; 0
`sem-controle-por-design`; 0 `UNREGISTERED` (todos os dez são, por
construção da partição, hooks registrados em `settings.json`).

## 3. O que este lote NÃO afirma

- Não afirma nada sobre `R[10:42]`: faltam os lotes 3 (em paralelo,
  relatório próprio) e 4-6. E não afirma que fechar `R` fecha o W0 —
  ver §5.
- Não afirma que o controle cobre TODO o gate: cada linha prova UM
  caminho de *enforcement*, não a superfície inteira do hook. Onde esse
  caminho não é o bloqueio de uma ferramenta, a última coluna do §2 o
  NOMEIA — três linhas são **advisory por desenho**
  (`protocol-semver-cascade`, `budget`, `read-injection`): elas sempre
  permitem, e o que o controle prova é que a OBSERVAÇÃO é emitida.
- Não afirma que o gate roda em produção: prova que o CÓDIGO produz a
  saída de enforcement especificada — **recusa** nas sete linhas
  bloqueantes, **saída advisory** (`systemMessage` / `additionalContext`)
  nas três advisory-por-desenho — e que o teste enxerga essa saída. Um
  matcher que nunca casa em campo passaria neste censo; isso é medição
  de outra wave.
- A metade RED foi obtida removendo o enforcement do jeito MÍNIMO
  (Apêndice B); ela prova que o controle enxerga aquele mecanismo, não
  que o mecanismo é completo.
- O `adversary` tem o enforcement gated por `CEO_ADVERSARY`; o controle
  roda com enforce LIGADO (o node id diz `when_enforced`). A rota
  advisory-off tem teste próprio e não foi auditada aqui.

## 4. Defeito de MEDIÇÃO encontrado e curado dentro do próprio lote

A primeira derivação deste censo produziu 10/10 verde — e estava
**errada por um instante**. Reproduzido, com comando e saída, no
Apêndice D: depois da mutação-e-restauração da linha `tier-policy`, o
MESMO node id passou a FALHAR com a árvore comprovadamente limpa
(`git status --porcelain` vazio, `grep` mostrando `"block"` no fonte) —
porque no macOS o bytecode não vai para um `__pycache__` local e sim
para `sys.pycache_prefix`
(`~/Library/Caches/com.apple.python/<caminho absoluto>`), e a mutação
usada (`"block"` → `"allow"`) tem **exatamente o mesmo tamanho em
bytes** do original: o `.pyc` da versão neutralizada continuou válido
para o carregador depois do `restore`.

Consequências, ambas aplicadas nesta derivação:

1. o driver do censo roda cada metade com `PYTHONDONTWRITEBYTECODE=1`;
2. o driver **purga** o espelho de bytecode daquela worktree sob
   `sys.pycache_prefix` ANTES de cada uma das três execuções — a
   variável `PYTHONDONTWRITEBYTECODE` impede a ESCRITA, não a LEITURA de
   um `.pyc` que já existia, então sem a purga a isolação seria
   decorativa;
3. toda linha ganha uma TERCEIRA execução — o **controle de
   restauração** — e o verdito `verde` exige `as-is PASS` **e**
   `removido FAIL` **e** `restaurado PASS`.

Limite declarado do item 3 (apontado numa rodada de rail): o controle de
restauração **não** é um detector universal de bytecode velho. O
`restore` muda o mtime do fonte e pode, ele mesmo, invalidar o `.pyc`
que a metade RED aceitou — nesse caso a restauração passa e o defeito
não aparece. Quem fecha o buraco é o item 2 (a purga antes de CADA
execução); o item 3 é a rede de segurança que pega o caso concreto
reproduzido no Apêndice D, não uma garantia geral.

Isto não é um defeito do repositório: é um defeito de INSTRUMENTO, da
mesma família que o W0 existe para caçar. Fica registrado porque
qualquer lote futuro que mute e restaure arquivos herda o risco.

## 5. O que a partição NÃO cobre — o RESTO, declarado

O AC do W0 no PLAN-171 (l. 170-172) pede «100% dos **hooks**», não
«100% dos hooks REGISTRADOS». `L` sai do `.claude/settings.json`, logo
`R` **não esgota** o universo do W0: os lotes 3-6 fecham `R`, e depois
disso o W0 ainda deve o conjunto abaixo. Foi um achado de rodada de
rail — a primeira versão deste relatório dizia «lotes 4-6 = o resto» e
com isso apagava esses gates em silêncio. Derivado por instrumento
(`remainder.py`), não lembrado:

```
    hooks_on_disk=59 registered_in_settings=48 unregistered=11
      (a) .claude/hooks/adequacy_gate.py
      (a) .claude/hooks/auto_boot.py
      (a) .claude/hooks/check_codex_stop_review.py
      (a) .claude/hooks/check_harness_config.py
      (a) .claude/hooks/check_tier_policy_misrouting_24h.py
      (a) .claude/hooks/emit_architect_outcome.py
      (a) .claude/hooks/latency_report.py
      (a) .claude/hooks/policy_dispatch.py
      (a) .claude/hooks/route.py
      (a) .claude/hooks/turbo_profile.py
      (a) .claude/hooks/verify_after_edit.py
      (b) check_harness_config.py executed by .github/workflows/validate.yml:1137
      (c) check_codex_stop_review.py registered in templates/codex/hooks.json:98 (campo `command`, nao `statusMessage`)
      (c) validate-pair-rail-verdict.py — DEFERIDO pelo lote-1-S345.md (§3), fora de L porque nao e hook registrado
      (c) _release_tag_guard.py — DEFERIDO pelo lote-1-S345.md (§3), fora de L porque nao e hook registrado
```

Três famílias, e por que cada uma escapa de `L`: **(a)** arquivo de hook
no disco SEM registração no `settings.json` (11 de 59); **(b)** gate que
um step de CI executa DIRETAMENTE, sem evento de hook —
`check_harness_config.py`; **(c)** gate registrado em OUTRO registry
(`templates/codex/hooks.json`, o trilho Codex — e o instrumento lê o
campo `command`, NUNCA o `statusMessage`: uma rodada de rail pegou este
mesmo relatório reportando como «registrado» um script que só era citado
na mensagem de status) ou nomeado como diferido
pelo próprio lote 1: os dois validadores BLOQUEANTES do trem de release
(`.github/scripts/validate-pair-rail-verdict.py` e
`.claude/scripts/local/_release_tag_guard.py`), que o §3 do
`lote-1-S345.md` mandou para «o lote 2». **Este lote NÃO os cobre** — a
fatia dele é `R[0:10]` por definição da partição, e esses dois não estão
em `R` porque não são hooks registrados. A dívida fica NOMEADA aqui em
vez de desaparecer entre dois documentos.

## Apêndice A — baseline «como está» (10/10 verde)

Os dez node ids numa invocação, lidos de um arquivo (`node-ids.txt`,
derivado do campo `node` do `red-half.json` — logo o conjunto que passa
aqui é, por construção, o MESMO que foi ao vermelho no Apêndice B):

```
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  xargs python3 -m pytest -q --no-header -p no:cacheprovider < node-ids.txt
10 passed in 1.26s
```

## Apêndice B — metade RED, gate a gate

Para cada linha: `git restore` → mutação mínima → **mesmo** node id →
`git restore` → **mesmo** node id de novo (controle de restauração).
Todas as dez retornaram `rc 1` na metade RED e `rc 0` na restauração.
A última coluna é a linha `E` do pytest — a asserção que de fato falhou.
Ela existe porque `rc != 0` sozinho **não** prova que o controle viu o
mecanismo: um erro de coleta ou uma exceção qualquer dá o mesmo `rc`
(defeito apontado numa rodada de rail e curado no driver, que hoje
extrai e grava a linha `E` em `red-half.json`). As dez são
`AssertionError` nomeando exatamente o enforcement removido —
`'allow' != 'block'`, `True is not false`, `'systemMessage' not found`.

| # | Gate | Mutação mínima aplicada | Resultado | Asserção que FALHOU (linha `E` do pytest) |
|---|------|--------------------------|-----------|---|
| 1 | adversary | `.claude/hooks/check_adversary.py` — `if decision == "deny":` → `if False:` (1 ocorrência(s)) | `1 failed in 0.33s` (rc 1) | `E       AssertionError: None != 'block'` |
| 2 | plan-edit | `.claude/hooks/check_plan_edit.py` — `if new_status not in allowed:` → `if False:` (1 ocorrência(s)) | `1 failed in 0.09s` (rc 1) | `E       AssertionError: True is not false` |
| 3 | protocol-semver-cascade | `.claude/hooks/check_protocol_semver_cascade.py` — `additional = warn + ("\n\n" + report if report else "")` → `additional = ""` (1 ocorrência(s)) | `1 failed in 0.27s` (rc 1) | `E       AssertionError: 'PROTOCOL.md' not found in ''` |
| 4 | skill-patch-sentinel | `.claude/hooks/check_skill_patch_sentinel.py` — `{"decision": "block", "reason": reason}, ensure_ascii=False` → `{"decision": "allow", "reason": reason}, ensure_ascii=False` (1 ocorrência(s)) | `1 failed in 0.20s` (rc 1) | `E       AssertionError: 'allow' != 'block'` |
| 5 | tier-policy | `.claude/hooks/check_tier_policy.py` — `{"decision": "block", "reason": reason}, ensure_ascii=False` → `{"decision": "allow", "reason": reason}, ensure_ascii=False` (1 ocorrência(s)) | `1 failed in 0.09s` (rc 1) | `E       AssertionError: 'allow' != 'block'` |
| 6 | arbitration-kernel | `.claude/hooks/check_arbitration_kernel.py` — `{"decision": "block", "reason": reason}, ensure_ascii=False` → `{"decision": "allow", "reason": reason}, ensure_ascii=False` (1 ocorrência(s)) | `1 failed in 0.20s` (rc 1) | `E       AssertionError: 'allow' != 'block'` |
| 7 | scratchpad-access | `.claude/hooks/check_scratchpad_access.py` — `allow=False,` → `allow=True,` (1 ocorrência(s)) | `1 failed in 0.09s` (rc 1) | `E       AssertionError: True is not false` |
| 8 | budget | `.claude/hooks/check_budget.py` — `if tokens_used <= max_plan_tokens:` → `if True:` (1 ocorrência(s)) | `1 failed in 0.10s` (rc 1) | `E       AssertionError: 'systemMessage' not found in {}` |
| 9 | read-injection | `.claude/hooks/check_read_injection.py` — `sys.stdout.write(_emit_allow(system_message=msg) + "\n")` → `sys.stdout.write(_emit_allow(system_message=None) + "\n")` (1 ocorrência(s)) | `1 failed in 0.28s` (rc 1) | `E       AssertionError: 'systemMessage' not found in {}` |
| 10 | codex-filewrite | `.claude/hooks/check_codex_filewrite.py` — `"decision": "block",` → `"decision": "allow",` (3 ocorrência(s)) | `1 failed in 0.24s` (rc 1) | `E       AssertionError: 'allow' != 'block'` |

Registro cru das dez rodadas: `red-half.json` no pack da sessão
(`gate`, `neuter_*`, `node`, `asis_rc`, `red_rc`, `restored_rc`, tails).

## Apêndice C — contagem derivada, não digitada

A linha de contagem do §2 sai de comandos sobre a PRÓPRIA tabela deste
arquivo. Cuidado herdado do lote 1: `^\| [0-9]+ \|` sozinho casa as
DUAS tabelas numeradas (§2 e Apêndice B). O discriminante é o node id
(`::`), que só existe nas linhas do §2. A contagem do Apêndice B usa o
discriminante SIMÉTRICO: a coluna de asserção, cuja célula começa com a
letra `E` do pytest e vem depois de `(rc 1)` — isso só existe no
Apêndice B, porque as linhas do §2 escrevem `rc 1,` com vírgula. Contar
as duas tabelas com o MESMO padrão e rotular o resultado como se fosse
do Apêndice B foi um defeito de rótulo pego numa rodada de rail:

```
grep -cE '^\| [0-9]+ \|.*::' .claude/plans/PLAN-171/w0/lote-2-S347.md                # 10
grep -cE '^\| [0-9]+ \|.*::.*\*\*verde\*\*' .claude/plans/PLAN-171/w0/lote-2-S347.md   # 10
grep -cE '^\| [0-9]+ \|.*::.*vácuo' .claude/plans/PLAN-171/w0/lote-2-S347.md         # 0
grep -cE '^\| [0-9]+ \|.*::.*sem controle' .claude/plans/PLAN-171/w0/lote-2-S347.md  # 0
grep -cE '^\| [0-9]+ \|.*\(rc 1\) \| `E ' .claude/plans/PLAN-171/w0/lote-2-S347.md  # 10
```

As saídas medidas na derivação FINAL estão no `EVIDENCE.md` do pack.

## Apêndice D — o defeito de medição do §4, com comando e saída

```
$ git -C <CENSUS-WT> status --porcelain    # (vazio: árvore limpa)
$ grep -c '"decision": "block", "reason": reason' .claude/hooks/check_tier_policy.py
1
$ PYTHONPATH=. python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/scripts/tier_policy_cli/tests/test_check_tier_policy_hook.py::CheckTierPolicyHookTests::test_veto_file_without_sentinel_blocked
E       AssertionError: 'allow' != 'block'
1 failed in 0.09s
$ python3 -c "import sys;print(sys.pycache_prefix)"
/Users/<USER>/Library/Caches/com.apple.python
$ find ~/Library/Caches/com.apple.python/<CENSUS-WT> -name '*.pyc' | wc -l
      52
$ find ~/Library/Caches/com.apple.python/<CENSUS-WT> -name '*.pyc' -delete
$ PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q --no-header \
    -p no:cacheprovider <mesmo node id>
1 passed in 0.08s
```

## Apêndice E — o que o lote consumiu como INPUT (rastreável)

- `.claude/plans/PLAN-171-governance-imports-provenance.md` §5, §6, §7.
- `.claude/plans/PLAN-171/w0/lote-1-S345.md` §1 (a coluna «Arquivo(s)»,
  lida pelo instrumento da partição — é ela que define o que sai de `L`).
- `.claude/settings.json` (registro por evento/matcher, lido por `json.load`).
- `pytest.ini` (`testpaths`, para saber o que uma suíte inteira coleta).
- `.github/workflows/validate.yml`, `coverage.yml`, `release.yml`
  (quem executa). `mutation-gate.yml` foi lido e **não** muta nenhum
  dos dez módulos deste lote (os quatro legs são `redact`,
  `audit_hmac`, `canonical_guard`, `check_pair_rail`).
