# PLAN-171 W0 — censo de gates com controle positivo, lote 1/6 (S345)

> **Escopo.** Os 10 gates nomeados no §7 «Runbook sessão 1» do PLAN-171:
> canonical-edit, bash-safety, agent-spawn, pair-rail, overhead,
> adequacy, audit-emit, injector, sentinel-unlock, credential-leak.
> **Método (a regra do W0):** um gate só é VERDE quando existe um
> controle positivo que (i) passa na árvore como está e (ii) **FALHA
> quando o enforcement é removido**. A metade RED é obrigatória — um
> controle que continua verde sem o enforcement é `controle vácuo`.
> Medido em 2026-09-05 numa worktree descartável (`git worktree add
> --detach`), um gate por vez, `git restore` entre cada um. Nenhuma
> edição na árvore viva. **Bases:** as linhas citadas VERBATIM neste
> relatório foram capturadas em `HEAD = 2f6cde1`; as duas metades foram
> RE-RODADAS em `HEAD = de42dfb` com veredito idêntico (10/10 verde,
> 10/10 vermelho). Entre os dois bases entraram apenas documentos de
> debate do PLAN-186 — nenhum arquivo de hook, de teste, de settings ou
> de workflow —, o que está medido no §5b do EVIDENCE do pack.

## 1. Tabela

| # | Gate | Arquivo(s) que implementam | Registro em `.claude/settings.json` (evento / matcher; par de linhas MEDIDO: linha do `matcher` → linha do `"command"` que nomeia o script) | Workflow + step de CI | Controle positivo (node id) | Como está | Enforcement removido | Verdito | Herança AC-9 |
|---|------|----------------------------|--------------------------------------------------------|------------------------|-----------------------------|-----------|----------------------|---------|---------------|
| 1 | canonical-edit | `.claude/hooks/check_canonical_edit.py` | `PreToolUse` / `Edit\|Write\|MultiEdit\|mcp__.*` (`settings.json`: matcher l. 184 → `command` l. 188) | `validate.yml` job `hook-tests-python-matrix`, step «Run hook + script tests on Python …» (l. 1644/1646); também `hook-tests-dual-rail` e `coverage.yml:102` | `.claude/hooks/tests/test_check_canonical_edit.py::CheckCanonicalEditTest::test_canonical_path_without_sentinel_blocks` | PASS | **FAIL** (rc 1) | **verde** | nada a herdar |
| 2 | bash-safety | `.claude/hooks/check_bash_safety.py` | `PreToolUse` / `Bash` (`settings.json`: matcher l. 148 → `command` l. 152) | idem #1 | `.claude/hooks/tests/test_check_bash_safety.py::TestDecideCommand::test_blocks_rm_rf` | PASS | **FAIL** (rc 1) | **verde** | nada a herdar |
| 3 | agent-spawn | `.claude/hooks/check_agent_spawn.py` | `PreToolUse` / `Agent` (`settings.json`: matcher l. 136 → `command` l. 140) | idem #1 | `.claude/hooks/tests/test_check_agent_spawn.py::TestDecide::test_blocks_named_spawn_without_skill` | PASS | **FAIL** (rc 1) | **verde** | nada a herdar |
| 4 | pair-rail | `.claude/hooks/check_pair_rail.py` (arm bloqueante = `CodexPinMismatch`, ADR-182) | `PreToolUse` / `Edit\|Write\|MultiEdit` (`settings.json`: matcher l. 280 → `command` l. 284) | idem #1; `mutation-gate.yml:71-73` muta este módulo | `.claude/hooks/tests/test_check_pair_rail_payload_pin.py::TestDecideBlocksOnPinMismatch::test_decide_returns_block_on_mismatch` | PASS | **FAIL** (rc 1) | **verde** | C.2 CLOSED pelo 169 |
| 5 | overhead | `.claude/hooks/check_anti_ceo_overhead.py` | `PreToolUse` / `Agent\|Bash\|Edit\|Write\|MultiEdit\|Read\|Glob\|Grep\|WebFetch\|WebSearch\|NotebookEdit\|TodoWrite\|Task\|mcp__.*` (`settings.json`: matcher l. 302 → `command` l. 306) | idem #1 | `.claude/hooks/tests/test_anti_ceo_overhead.py::AdversarialFixturesTest::test_positive_fixtures_all_block` | PASS | **FAIL** (rc 1) | **verde** | C.3/F.4 CLOSED pelo 169 |
| 6 | adequacy | `.claude/hooks/adequacy_gate.py`, despachado por `.claude/hooks/accel_dispatch.py` | **não tem registro próprio**; entra pelo host `accel_dispatch.py` — `PostToolUse` / `Edit\|Write\|MultiEdit` (`settings.json`: matcher l. 508 → `command` l. 512). Opt-in: silencioso sem `CEO_ADEQUACY_GATE=1` | idem #1 | `.claude/hooks/tests/test_adequacy_gate.py::test_weak_tests_flag_and_file_untouched` | PASS | **FAIL** (rc 1) | **verde** (advisory por desenho: sinaliza, não bloqueia) | nada a herdar |
| 7 | audit-emit | `.claude/hooks/_lib/audit_emit.py` (guarda ghost-action: `else` default-deny em `emit_generic`, l. 7827-7831) | biblioteca — **sem registro de hook**, consumida pelos hooks registrados | idem #1 (`.claude/hooks/tests/`); asserção de `_KNOWN_ACTIONS` também no step «Audit registry drift (SPEC ⇆ code)» (`validate.yml:592-593`) | `.claude/hooks/tests/test_audit_emit_ghost_action_guard.py::TestDefaultDenyGuard::test_synthetic_unbranched_action_default_deny` | PASS | **FAIL** (rc 1) | **verde** (default-deny: descarta os kwargs do chamador, não bloqueia a ferramenta) | nada a herdar |
| 8 | injector | `.claude/scripts/inject-agent-context.sh` (fail-closed `exit 3`, l. 903) | script de operador — **sem registro de hook** | `validate.yml` job `hook-tests-python-matrix` (l. 1644/1646, inclui `.claude/scripts/tests/`); `coverage.yml:132`; `release.yml:393`. **Não** roda no `hook-tests-dual-rail` | `.claude/scripts/tests/test_inject_agent_context_exact_resolution.py::ExactResolutionLadderTest::test_unknown_name_fails_closed_exit_3` | PASS | **FAIL** (rc 1) | **verde** | C.1 CLOSED pelo 169 |
| 9 | sentinel-unlock | `.claude/hooks/check_canonical_edit.py` (`_pinned_sentinel_digests`, `_unlock_trusted_text`) | herda o registro de #1 | idem #1 | `.claude/hooks/tests/test_canonical_edit_plan162_findings.py::S2AnchorTrustRoundTwoTest::test_p1_3_control_malformed_digest_fails_closed` | PASS | **FAIL** (rc 1) | **verde** | nada a herdar |
| 10 | credential-leak | `.claude/hooks/check_bash_safety.py::_check_credential_leak` (l. 906) | herda o registro de #2 | idem #1 | `.claude/hooks/tests/test_check_bash_safety.py::TestMainCredentialLeakAudit::test_main_blocks_credential_leak` | PASS | **FAIL** (rc 1) | **verde** | nada a herdar |

**Como ler as linhas da coluna 4 (precisão paga na refutação):** cada
registro em `.claude/settings.json` é um par — a linha `"matcher"` e,
quatro linhas abaixo, a linha `"command"` que nomeia o script. As duas
são citadas porque a linha do script SOZINHA não mostra o matcher.
Números de linha envelhecem: o texto-âncora de cada uma está medido no
`EVIDENCE.md` do pack (§6), derivado por `json.load` + varredura do
arquivo, nunca digitado.

**Caveat de CI declarado (precisão paga na revisão):** os controles
NÃO rodam todos nos dois jobs. `hook-tests-python-matrix` roda os
**10** (ele inclui `.claude/scripts/tests/`); `hook-tests-dual-rail`
roda **9** — o controle do injector (#8) vive em
`.claude/scripts/tests/` e está FORA daquele job, como a própria linha
8 diz. Os dois carregam `if: vars.CEO_SOTA_DISABLE != '1'`
(`validate.yml` l. 1567 e l. 1602, logo abaixo dos cabeçalhos de job em
1566 e 1601): um admin do repo pode desligá-los por variável. O gate
existe; a EXECUÇÃO dele é condicional, e essa condição não foi
exercitada aqui.

**Contagem (derivada por comando — ver Apêndice C):** 10 gates no lote;
10 com controle positivo PROVADO vermelho; 0 `controle vácuo`;
0 `sem controle`; 0 `sem-controle-por-design`; 0 `UNREGISTERED` no
sentido de «gate que deveria estar em `settings.json` e não está»
(3 linhas — #6, #7, #8 — não têm registro PRÓPRIO e a coluna diz por quê:
host `accel_dispatch`, biblioteca, script de operador).

## 2. Herança do AC-9 do PLAN-169 — as três dívidas de S294

O §5 do PLAN-171 nomeia três dívidas e manda herdar **apenas o que o
fechamento do 169 declarar não-feito**. O fechamento declara AC-9
`[x]` e as quatro dívidas `C.*` CLOSED, com evidência de disco:

| Dívida S294 (como o PLAN-171 §5 a nomeia) | Dono | Estado no texto do 169 | Herdado pelo W0? |
|---|---|---|---|
| `pair-rail-gate.sh` inexecutável | **PLAN-169 AC-9** (C.2 / F.5) | CLOSED — «Cura foi rota de auth, não `chmod`»; `pair-rail-gate.sh:64-83` (Gate 1 = API key OU login; Gate 2 pulado na rota login); a frase «evidência DINÂMICA: ambas as rotas PASS nesta máquina» é CITAÇÃO do próprio 169 (linha C.2, «§Progress log S299»), **não** uma medição deste lote — o W0 auditou o REGISTRO, não re-rodou o gate | **NÃO** |
| injector persona fuzzy | **PLAN-169 AC-9** (C.1) | CLOSED — `inject-agent-context.sh:798-805` (escada EXATA, 4 degraus) e `:903` (`exit 3` fail-closed) | **NÃO** |
| `overhead-ack` não cobre Write | **PLAN-169 AC-9** (C.3 / F.4) | CLOSED — «A memória estava errada; o fix foi no canal e na doc, NÃO na classificação de tool»; arquivos que a fecham, nomeados pelo PRÓPRIO 169 na linha C.3 (l. 1664): `docs/TROUBLESHOOTING.md` e `docs/TROUBLESHOOTING.pt-BR.md` (W2.4 — a ENTREGA, que era o defeito) e `.claude/hooks/check_anti_ceo_overhead.py` no commit `e5ce982` (W3.3 — o canal). O W0 auditou o REGISTRO: não re-exercitou `CEO_OVERHEAD_ACK` num `Write` — o controle do §1 prova o BLOQUEIO, não a rota de override | **NÃO** |

Resultado: **zero dívidas herdadas** neste lote. Sem posse dupla — o
W0 AUDITOU e a auditoria bate com o registro de entrega do 169.

Limite honesto declarado pelo próprio 169 na linha C.3: o hit advisory
do overhead **não é auditado** (exige cerimônia de whitelist de
`audit_emit`) — follow-up já nomeado LÁ, não aqui.

## 3. O que este lote NÃO afirma

- Não afirma nada sobre o resto do roster: `verify-counts.sh` mede
  `hook_py = 59` scripts no disco, `registered = 48` distintos em
  `registrations = 50` registrações, sobre 15 eventos. Faltam os
  **lotes 2-6**.
- Não afirma que o controle cobre TODO o gate: cada linha prova UM
  caminho de *enforcement* — bloqueio, recusa, flag ou scrub —, não
  a superfície inteira do hook. Onde esse caminho NÃO é o bloqueio
  de uma ferramenta, a coluna «Verdito» do §1 o NOMEIA: a linha 6
  (adequacy) sinaliza e deixa o arquivo intocado; a linha 7
  (audit-emit) faz *default-deny* — descarta os kwargs do chamador
  antes de escrever o evento. As outras oito provam bloqueio ou
  recusa (`rc 1`, ou `exit 3` no injector).
- `check_pair_rail.py` é **advisory por desenho** fora do arm
  `CodexPinMismatch` (o teste-régua `test_no_block_decision_assignments_in_pair_rail_module`
  fixa EXATAMENTE um literal de bloqueio no módulo). Os gates
  BLOQUEANTES do pair-rail no trem de release são outros dois arquivos
  — `.github/scripts/validate-pair-rail-verdict.py` (`release.yml:754`)
  e `.claude/scripts/local/_release_tag_guard.py` — e ficam para o
  lote 2.
- A metade RED foi obtida removendo o enforcement do jeito MÍNIMO
  (Apêndice B); ela prova que o controle enxerga aquele mecanismo, não
  que o mecanismo é completo.

## 4. Efeito colateral MEDIDO do flip de status

O flip `reviewed → executing` troca as linhas que o
`check-staleness.py` emite para este plano — todas ADVISORY (`rc 0`
antes e depois):

- **antes:** 1 linha — `plan_stranded_dispatch_failed (25d > 7d)`
  («parado em `reviewed` >7d sem transição para `executing`»).
- **depois:** 2 linhas — `plan_executing_stalled (25d > 14d)` e
  `plan_stranded_paperclip_in_progress (15d > 1d)`.

As duas rodadas estão QUOTADAS no Apêndice E (comando + saída, antes e
depois), e o `rc 0` citado ali é o do PRÓPRIO checker — ele roda para um
arquivo e o `rc` é impresso antes de qualquer filtro, justamente para
não reportar o status do `grep`.

**As TRÊS idades vêm de três lugares diferentes — e nenhuma é
`executing_at`** (medido, não suposto; uma rodada de revisão derrubou
uma primeira versão desta explicação que atribuía as duas primeiras à
mesma variável):

| Linha | Onde a idade é calculada | Campo |
|---|---|---|
| `plan_stranded_dispatch_failed (25d)`, ANTES | `check_plan_edit.py:574` (`now_unix - reviewed_unix`), via `_check_stranded` → `detect_stranded` modo 8.1 | `reviewed_at` |
| `plan_executing_stalled (25d)`, DEPOIS | `check-staleness.py:203` (`age_days = (now - created).days`) | `created` |
| `plan_stranded_paperclip_in_progress (15d)`, DEPOIS | `detect_stranded` modo 8.2 | dias desde o último commit que tocou o plano |

Os dois `25d` COINCIDEM porque este plano tem `created: 2026-08-11` **e**
`reviewed_at: 2026-08-11` — duas datas iguais no frontmatter, não uma
variável reaproveitada. Nenhuma das três idades é auditada por este
lote; o que está medido aqui é a PROCEDÊNCIA de cada uma.

Consequência que o relatório declara em vez de disfarçar: a frase de
`impact` que a regra imprime DEPOIS do flip — «plan has been executing
for >14 days without transition» — é **falsa para este plano**, que
está em `executing` desde hoje; ela mede idade de `created`, não tempo
de execução. Isso é um limite do checker (advisory, `rc 0`), não algo
que este lote conserte, e não é inferência: as duas capturas estão no
Apêndice E. Que a linha `paperclip` suma no primeiro commit que tocar o
plano é o que a própria regra diz na sua linha `remediation` («either
ship a commit …»), também quotada lá.

## Apêndice A — baseline «como está» (10/10 verde)

Comando (os 10 node ids numa invocação, lidos de um arquivo para não
depender de word-splitting do shell):

```
xargs python3 -m pytest -q --no-header -p no:cacheprovider < node-ids.txt
```

`node-ids.txt` tem UMA linha por node id e é derivado do campo `node`
do `red-half.json` — logo, o conjunto que passou aqui é, por
construção, o MESMO que foi ao vermelho no Apêndice B. Que essas dez
linhas são exatamente as dez da coluna «Controle positivo» do §1 é
provado por um `diff` que sai `IDENTICAL` — comando e saída no
Apêndice C.

Saída verbatim da rodada final (a mesma captura que o `EVIDENCE.md` §4
do pack embute — os dois não podem divergir em silêncio):

```
10 passed, 1 warning in 4.49s
```

## Apêndice B — metade RED, gate a gate

Para cada linha: `git restore` → mutação mínima → **mesmo** node id →
`git restore`. Todas as dez retornaram `rc 1` / `1 failed`.

| # | Gate | Mutação mínima aplicada | Resultado |
|---|------|--------------------------|-----------|
| 1 | canonical-edit | `"decision": "block"` → `"decision": "allow"` (1 ocorrência) em `check_canonical_edit.py` | `1 failed in 0.29s` (rc 1) |
| 2 | bash-safety | `return Decision(allow=True)` inserido como 1.º statement de `decide_command` (`check_bash_safety.py:3818`) | `1 failed in 0.11s` (rc 1) |
| 3 | agent-spawn | `return Decision(allow=True)` inserido como 1.º statement de `decide` (`check_agent_spawn.py:2373`) | `1 failed in 0.11s` (rc 1) |
| 4 | pair-rail | `"decision": "block"` → `"decision": "allow"` (1 ocorrência) em `check_pair_rail.py` | `1 failed in 0.12s` (rc 1) |
| 5 | overhead | `"decision": "block"` → `"decision": "allow"` (2 ocorrências) em `check_anti_ceo_overhead.py` | `1 failed in 0.10s` (rc 1) |
| 6 | adequacy | `if rate < THRESHOLD:` → `if False:` em `adequacy_gate.py` | `1 failed in 3.54s` (rc 1) |
| 7 | audit-emit | `audit_emit.py:7828` `        event = {"action": action}` → `        pass` (mata o default-deny) | `1 failed in 0.10s` (rc 1) |
| 8 | injector | `inject-agent-context.sh:903` `  exit 3` → `  exit 0` | `1 failed in 0.39s` (rc 1) |
| 9 | sentinel-unlock | `return (set(), True)` → `return (set(), False)` em `_pinned_sentinel_digests` (mata o fail-closed de digest malformado) | `1 failed in 0.46s` (rc 1) |
| 10 | credential-leak | `return None` inserido como 1.º statement de `_check_credential_leak` (`check_bash_safety.py:906`) | `1 failed in 0.12s` (rc 1) |

Registro cru das dez rodadas: `red-half.json` no pack da sessão
(`gate`, `neuter`, `node`, `rc`, `tail` por linha).

## Apêndice C — contagem derivada, não digitada

A linha de contagem do §1 sai de comandos sobre a PRÓPRIA tabela deste
arquivo. Cuidado medido: `^\| [0-9]+ \|` sozinho casa **20** linhas —
a tabela do §1 E a do Apêndice B, ambas numeradas. O discriminante é o
node id (`::`), que só existe nas linhas do §1; simetricamente,
`rc 1` aparece nas DUAS tabelas e `1 failed in` só no Apêndice B:

```
grep -cE '^\| [0-9]+ \|.*::' .claude/plans/PLAN-171/w0/lote-1-S345.md                 # 10  (linhas do §1)
grep -cE '^\| [0-9]+ \|.*::.*\*\*verde\*\*' .claude/plans/PLAN-171/w0/lote-1-S345.md      # 10  (verdito verde)
grep -cE '^\| [0-9]+ \|.*::.*vácuo' .claude/plans/PLAN-171/w0/lote-1-S345.md          # 0
grep -cE '^\| [0-9]+ \|.*::.*sem controle' .claude/plans/PLAN-171/w0/lote-1-S345.md   # 0
grep -cE '^\| [0-9]+ \|.*1 failed in' .claude/plans/PLAN-171/w0/lote-1-S345.md        # 10  (Apêndice B: dez REDs)
```

E a ligação entre a tabela e o conjunto que REALMENTE rodou — comando e
saída, não afirmação (`node-ids.txt` é o arquivo que alimentou o
`xargs` do Apêndice A e sai do campo `node` do `red-half.json`; ambos
vivem no pack da sessão):

```
$ sed -n '/^## 1\./,/^## 2\./p' .claude/plans/PLAN-171/w0/lote-1-S345.md \
    | grep -E '^\| [0-9]+ \|' \
    | grep -oE '\.claude/[^ `|]*tests/[^ `|]+::[A-Za-z0-9_:]+' | sort > /tmp/from-table.txt
$ sort node-ids.txt > /tmp/from-run.txt
$ diff /tmp/from-run.txt /tmp/from-table.txt && echo IDENTICAL
IDENTICAL
$ wc -l < /tmp/from-table.txt
      10
```

(O `grep -oE` exige `tests/` no caminho de propósito: sem isso a linha
10 contribuiria com `check_bash_safety.py::_check_credential_leak`, que
é a FUNÇÃO citada na coluna de arquivos, não um node id — medido, 11
linhas em vez de 10.)

Saída medida na derivação final: ver `EVIDENCE.md` do pack.

## Apêndice D — o que o lote consumiu como INPUT (rastreável)

- `.claude/plans/PLAN-171-governance-imports-provenance.md` §5, §6, §7.
- `.claude/plans/PLAN-169-closure-and-cross-session-evolution.md`
  l. 114-118 (as duas «verdades» da memória refutadas), l. 1395-1400
  (AC-9 `[x]`), l. 1662-1665 (linhas C.1-C.4 CLOSED), l. 1694-1695
  (F.4/F.5 CLOSED).
- `.claude/settings.json` (registro por evento/matcher).
- `.github/workflows/validate.yml`, `coverage.yml`, `release.yml`,
  `mutation-gate.yml` (quem executa).

## Apêndice E — o efeito colateral do §4, com comando e saída

Cada metade são DOIS comandos de propósito: o checker escreve num
arquivo e o `rc` impresso é o DELE; o filtro roda depois. Uma linha
única `checker | grep` reportaria o status do `grep`, não o do checker
— defeito apontado numa rodada de revisão e curado aqui.

**ANTES** (árvore SEM a derivação — o plano ainda em `reviewed`):

```
$ python3 .claude/scripts/check-staleness.py > /tmp/p171-stal-before.txt 2>&1 ; echo rc=$?
rc=0
$ grep -A4 -F 'plan       PLAN-171' /tmp/p171-stal-before.txt
  [stranded ] plan       PLAN-171
    rule: plan_stranded_dispatch_failed (25d > 7d)
    impact:      plan parked in 'reviewed' >7d with no transition to executing — likely dispatch failed silently (mode 8.1)
    remediation: wake Owner: either dispatch executing run or abandon/refuse the plan
    path:        .claude/plans/PLAN-171-governance-imports-provenance.md
```

**DEPOIS** (árvore COM a derivação aplicada):

```
$ python3 .claude/scripts/check-staleness.py > /tmp/p171-stal-after.txt 2>&1 ; echo rc=$?
rc=0
$ grep -A4 -F 'plan       PLAN-171' /tmp/p171-stal-after.txt
  [degraded ] plan       PLAN-171
    rule: plan_executing_stalled (25d > 14d)
    impact:      plan has been executing for >14 days without transition
    remediation: ship next phase or roll to 'done'/'abandoned'
    path:        .claude/plans/PLAN-171-governance-imports-provenance.md
--
  [stranded ] plan       PLAN-171
    rule: plan_stranded_paperclip_in_progress (15d > 1d)
    impact:      plan claims to be executing but no commit has touched it in >24h — paperclip-style stranded run (mode 8.2)
    remediation: either ship a commit, mark `## Abandonment reason` and transition to abandoned, or investigate dispatched-run failure
    path:        .claude/plans/PLAN-171-governance-imports-provenance.md
```

(O `-F 'plan       PLAN-171'` casa a linha de CABEÇALHO do achado e **não**
a linha `path:` — discriminante medido: sem ele, o `-A4` a partir do
`path:` arrasta o começo do bloco do plano SEGUINTE (PLAN-183 na árvore de
hoje) para dentro da captura. Com o cabeçalho como âncora a saída carrega
SOMENTE os blocos do PLAN-171, e o `--` entre eles é o separador que o
próprio `grep` imprime entre grupos não contíguos; as capturas cruas completas estão
no pack da sessão — `raw/staleness-before.txt` para a metade ANTES, e
a seção `check-staleness.py` da captura de bateria da derivação FINAL
para a metade DEPOIS; o `EVIDENCE.md` do pack cita essa captura pelo
nome que ela tem na derivação entregue.)
