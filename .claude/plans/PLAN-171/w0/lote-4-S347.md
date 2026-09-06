# PLAN-171 W0 — censo de gates com controle positivo, lote 4/6 (S347)

> **Escopo.** Os 10 hooks de `R[20:30]` da partição determinística do §1.
> **Método (a regra do W0, herdada dos lotes 1-3).** Um gate só é VERDE
> quando existe um controle positivo que (i) passa na árvore como está e
> (ii) **FALHA quando o enforcement é removido**. A metade RED é
> obrigatória — um controle que continua verde sem o enforcement é
> `controle vácuo`. Para um hook OBSERVADOR (PostToolUse / lifecycle,
> que não bloqueia ferramenta), o «enforcement» medido é a OBSERVAÇÃO —
> o evento, o `systemMessage` ou o `additionalContext` que o hook existe
> para produzir. A coluna «O que o controle prova» NOMEIA isso linha a
> linha, para que um `verde` não seja lido como «bloqueia».
> Herdado do lote 2: uma TERCEIRA metade, `git restore` + re-execução,
> porque no macOS um `.pyc` velho no `sys.pycache_prefix` falsifica a
> medição. Medido numa worktree descartável (`git worktree add
> --detach`), um gate por vez. Nenhuma edição na árvore viva.
>
> **Base (parágrafo GERADO — nenhum sha digitado).** As três metades de
> cada linha e todas as citações deste relatório foram medidas em
> `HEAD = 72910e9`, baseline e mutante na MESMA worktree e no MESMO base.
> O gerador RECUSA emitir se a fatia medida não for exatamente
> `R[20:30]` recomputado aqui a partir do `settings.json`, e RECUSA se
> qualquer arquivo que este relatório CITA (o `settings.json`, o
> relatório do lote 1, os 10 hooks medidos, os 10 módulos de teste dos
> controles e os 4 workflows) tiver mudado entre a base da medição e o
> `HEAD` vivo.
>
> Entre a base da medição e o `HEAD` vivo NO MOMENTO DA GERAÇÃO (`7036a03`) entraram 1 commit(s), nenhum tocando um arquivo citado — a lista é o que a recusa por conjunto citado examinou:
>
> ```
> 7036a03 docs(PLAN-175 debate round-1): rodada 1 do debate L3 — 3 críticos (VP Eng, QA, FinOps) ADJUS
> ```

## 1. A partição (determinística, computada — não digitada)

`L` = os ARQUIVOS de hook registrados em `.claude/settings.json`, em
ordem de primeira ocorrência (itera o objeto `hooks` na ordem do
arquivo — eventos, grupos, entradas; toma o basename `*.py` de cada
`command`; entradas `echo` inline não nomeiam arquivo e são puladas;
dedupe mantendo a primeira). Medido aqui, sobre o `settings.json` deste
`HEAD`: **15 eventos**, **50 entradas** de hook, das quais **49 nomeiam
um `*.py`** — a diferença, 1, é a entrada `echo` inline que não nomeia
arquivo. **|L| = 48** arquivos distintos.

Removidos os arquivos que o §1 do `lote-1-S345.md` já atribui. O
gerador lê a coluna de arquivos DAQUELE relatório: 8 nomes, dos quais
os **6** que aparecem em `L` são removidos — `check_canonical_edit.py`, `check_bash_safety.py`, `check_agent_spawn.py`, `check_pair_rail.py`, `check_anti_ceo_overhead.py`, `accel_dispatch.py`. Os outros 2 — `adequacy_gate.py`, `audit_emit.py` —
**não estão em `L`** por não serem hooks registrados, como o próprio
lote 1 diz na coluna de registro.

Resta **|R| = 42**, na ordem de `L`. `lote 2 = R[0:10]` (landado);
`lote 3 = R[10:20]` (landado); **`lote 4 = R[20:30]` — ESTE relatório**;
`lotes 5-6 = R[30:42]` (devidos).

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
| R[20] | `check_skill_bootstrap_post.py` | **lote 4 (ESTE)** |
| R[21] | `check_webfetch_injection.py` | **lote 4 (ESTE)** |
| R[22] | `check_mcp_response.py` | **lote 4 (ESTE)** |
| R[23] | `check_codex_response.py` | **lote 4 (ESTE)** |
| R[24] | `check_bash_canonical_forensic.py` | **lote 4 (ESTE)** |
| R[25] | `SessionStart.py` | **lote 4 (ESTE)** |
| R[26] | `turbo_sessionstart.py` | **lote 4 (ESTE)** |
| R[27] | `check_compact_pinning.py` | **lote 4 (ESTE)** |
| R[28] | `SessionEnd.py` | **lote 4 (ESTE)** |
| R[29] | `UserPromptSubmit.py` | **lote 4 (ESTE)** |
| R[30] | `Stop.py` | lotes 5-6 (devidos) |
| R[31] | `codex_review_user_code.py` | lotes 5-6 (devidos) |
| R[32] | `review_loop.py` | lotes 5-6 (devidos) |
| R[33] | `check_closeout_guard.py` | lotes 5-6 (devidos) |
| R[34] | `check_fluency_nudge.py` | lotes 5-6 (devidos) |
| R[35] | `check_precompact_continuity.py` | lotes 5-6 (devidos) |
| R[36] | `check_postcompact_reinject.py` | lotes 5-6 (devidos) |
| R[37] | `check_config_change.py` | lotes 5-6 (devidos) |
| R[38] | `check_subagent_start.py` | lotes 5-6 (devidos) |
| R[39] | `check_setup_verification.py` | lotes 5-6 (devidos) |
| R[40] | `check_directory_added.py` | lotes 5-6 (devidos) |
| R[41] | `check_notification.py` | lotes 5-6 (devidos) |

> A disjunção entre os lotes é por CONSTRUÇÃO — fatias de índices
> contíguos da MESMA lista —, não por acordo entre as sessões.

## 2. Tabela

Todos os 10 controles deste lote vivem em `.claude/hooks/tests/`, logo
a coluna de CI é a MESMA para as 10 linhas — `coverage.yml` job `coverage` (step l. 90 -> l. 102), `release.yml` job `release-gate` (step l. 388 -> l. 390), `validate.yml` job `hook-tests-dual-rail` (step l. 1588 -> l. 1594), `validate.yml` job `hook-tests-python-matrix` (step l. 1631 -> l. 1644).
Cada `step` foi resolvido por CONTEÚDO (o gerador sobe do comando
`pytest` até o `- name:` que o contém). E o crédito de um sítio NÃO é
inferido do caminho que ele passa: para cada um dos 9 sítios que citam
`.claude/hooks/tests/`, o instrumento RODA `pytest --collect-only` com
o `-m` DAQUELE sítio sobre os 10 node ids deste lote e conta quantos
são SELECIONADOS. Só **4** selecionam os 10; os outros 5 são os três
de `mutation-gate.yml`, que escondem um `-k`/`--collect-only` na linha
SEGUINTE, e as duas pernas `-m 'serial'` de `validate.yml`, que
devolvem `no tests collected (10 deselected)` — achado da rodada r2 do
rail, medido e curado aqui. Ver Apêndice E.

| # | Gate (arquivo registrado) | Registro em `.claude/settings.json` (evento / matcher; linha do `"matcher"` → linha do `"command"`) | Controle positivo (node id) | O que o controle prova | Como está | Enforcement removido | Verdito |
|---|---|---|---|---|---|---|---|
| 1 | `.claude/hooks/check_skill_bootstrap_post.py` | `PostToolUse` / `Edit\|Write\|MultiEdit` (l. 448 → l. 452) | `.claude/hooks/tests/test_check_skill_bootstrap_post.py::TestRecentBootstrapEvent::test_event_in_window_detected` | detecção (correlação bootstrap↔SKILL.md dentro da janela) | 1 passed in 0.08s | **1 failed in 0.10s** | **verde** |
| 2 | `.claude/hooks/check_webfetch_injection.py` | `PostToolUse` / `WebFetch\|WebSearch` (l. 460 → l. 464) | `.claude/hooks/tests/test_webfetch_injection.py::TestWebFetchInjectionHookDetection::test_detects_harness_mimicry_in_webfetch_result` | observação entregue (banner advisory com family_counts) | 1 passed in 0.29s | **1 failed in 0.32s** | **verde** |
| 3 | `.claude/hooks/check_mcp_response.py` | `PostToolUse` / `mcp__.*` (l. 472 → l. 476) | `.claude/hooks/tests/test_check_mcp_response.py::CheckMcpResponseStrictModeTest::test_strict_mode_blocks_high_severity_finding` | BLOQUEIO na rota opt-in `CEO_MCP_SCANNER_MODE=strict` (medida LIGADA) | 1 passed in 0.27s | **1 failed in 0.30s** | **verde** |
| 4 | `.claude/hooks/check_codex_response.py` | `PostToolUse` / `mcp__codex__codex\|mcp__codex__codex-reply` (l. 484 → l. 488) | `.claude/hooks/tests/test_check_codex_response.py::TestScanInjectionBuckets::test_scan_injection_returns_correct_family_for_system_bracket` | detecção (família de injeção reportada pelo scanner) | 1 passed in 0.09s | **1 failed in 0.10s** | **verde** |
| 5 | `.claude/hooks/check_bash_canonical_forensic.py` | `PostToolUse` / `Bash` (l. 496 → l. 500) | `.claude/hooks/tests/test_bash_canonical_forensic.py::TestBashCanonicalForensic::test_scan_extracts_redirect_target` | detecção (alvo de escrita canônico extraído do texto do comando — a ENTRADA da observação forense) | 1 passed in 0.08s | **1 failed in 0.10s** | **verde** |
| 6 | `.claude/hooks/SessionStart.py` | `SessionStart` / *(sem matcher — evento de ciclo de vida)* (l. 536 → l. 540) | `.claude/hooks/tests/test_session_start.py::TestSessionStartInjectionWiring::test_poisoned_instructions_validate_emit_and_block` | observação da RECUSA (`instructions_blocked == 1` + evento `persistent_instructions_blocked` para um `.claude/instructions.md` envenenado). **NÃO** prova impedir carregamento: esta função nunca carrega o arquivo em nenhuma das versões | 1 passed in 0.09s | **1 failed in 0.12s** | **verde** |
| 7 | `.claude/hooks/turbo_sessionstart.py` | `SessionStart` / *(sem matcher — evento de ciclo de vida)* (l. 548 → l. 552) | `.claude/hooks/tests/test_turbo_sessionstart.py::test_selftest` | observação entregue (`hookSpecificOutput.additionalContext` com o banner de primeira execução) | 1 passed in 0.20s | **1 failed in 0.21s** | **verde** |
| 8 | `.claude/hooks/check_compact_pinning.py` | `SessionStart` / `compact` (l. 560 → l. 564) | `.claude/hooks/tests/test_plan179_integration.py::TestPinningPrimaryChannel::test_compact_source_returns_full_set_from_an_empty_world` | entrega do piso de governança pinado no SessionStart pós-compaction (canal PRIMÁRIO do PLAN-179 W1-b) | 1 passed in 0.15s | **1 failed in 0.18s** | **verde** |
| 9 | `.claude/hooks/SessionEnd.py` | `SessionEnd` / *(sem matcher — evento de ciclo de vida)* (l. 574 → l. 578) | `.claude/hooks/tests/test_session_end_memory_delta.py::TestSpecSurface::test_written_delta_counts_only` | observação produzida (delta de memória stat-only: `outcome`, `modified_count`, `index_modified`) | 1 passed in 0.11s | **1 failed in 0.12s** | **verde** |
| 10 | `.claude/hooks/UserPromptSubmit.py` | `UserPromptSubmit` / *(sem matcher — evento de ciclo de vida)* (l. 588 → l. 592) | `.claude/hooks/tests/test_user_prompt_submit.py::TestUserPromptSubmitDecide::test_decide_injection_prompt_advisory_banner` | observação entregue (banner advisory com redact_hits + injection_hits no smell-test do prompt) | 1 passed in 0.08s | **1 failed in 0.12s** | **verde** |

**Contagem (impressa por `gen-count.py` sobre ESTA tabela — Apêndice C):**
10 gates no lote; 10 com controle positivo PROVADO vermelho; 0 `controle vácuo`; 0 `sem controle`; 0 `sem-controle-por-design`; 0 `UNREGISTERED`. A partição do §1 tem 42 linhas `R[..]`, das quais 10 marcadas como deste lote, e o Apêndice B registra 10 metades vermelhas.
A terceira metade fechou em verde nas 10 linhas, e a worktree ficou limpa (`git status --porcelain` vazio) depois de cada restauração nas 10.

## 3. O detector de rota de bloqueio — e o zero que ele desmentiu

A nota de cerimônia manda, para cada linha ADVISORY/observadora, ou
MEDIR cada chave que faz o hook bloquear, ou PROVAR a ausência por
instrumento. O detector de quatro formas do `p171-w0-lote2-fix` foi
herdado e **ampliado em duas formas**, cada uma com controle positivo
(o instrumento RECUSA rodar se o controle sintético não disparar):

1. `getattr-<chave>` — `getattr(<x>, "decision", ...) == "block"`.
   **`SessionStart.py` consome o veredito do validador exatamente
   assim** (l. 380) e o detector herdado reportava ZERO construtos de
   bloqueio para ele. Um censo que tivesse confiado naquele zero teria
   publicado «sempre permite» para o hook que CONTABILIZA e EMITE a
   recusa de um `.claude/instructions.md` envenenado. Precisão paga na
   rodada r1 do rail: o construto é o consumo de um veredito de
   bloqueio, **não** um carregamento impedido — a própria função diz no
   docstring que «this function never loads it — the refusal is the
   contract; a separate loader would consume the `allow` verdicts»
   (`SessionStart.py` l. 350-351).
2. Nomes de variável ligados a uma CONSTANTE de módulo
   (`_KILL_SWITCH_ENV = "CEO_EXTENDED_LIFECYCLE"`). Os três hooks de
   ciclo de vida desta fatia leem o kill-switch assim, e a varredura
   só-por-getter devolvia conjunto de env VAZIO para os três.

Resultado medido (Apêndice F traz a tabela completa, com as linhas):
**2** dos 10 arquivos carregam construto de bloqueio das formas
procuradas — `check_mcp_response.py`, `SessionStart.py`. Cada um deles TEM medição dinâmica nesta tabela (o
instrumento recusa emitir se um construto ficar sem controle rodado).
Os outros 8 não têm nenhum: o `verde` deles é observação, não bloqueio.

**Limite declarado do detector (o COMPLEMENTO das tabelas do
Apêndice F, não uma lista de rotas cegas escrita de memória):** ele lê
o ARQUIVO do hook sem seguir `import`, exige chave E valor LITERAIS no
próprio construto, e só conhece as chaves de decisão `"decision": "block"`, `"permissionDecision": "deny"`. Uma decisão
montada indiretamente, ou vinda de um módulo importado, está fora do
alcance — zero construtos é um fato sobre ESSAS formas NESTE arquivo,
nunca uma prova de que nenhuma configuração faz o hook bloquear.

## 4. O que este lote NÃO afirma

- Não afirma nada sobre `R[30:42]` — os lotes 5-6 seguem devidos.
- Não afirma que o controle cobre TODO o hook: cada linha prova UM
  caminho, e a coluna «O que o controle prova» diz qual. Em particular,
  quatro linhas provam a DETECÇÃO (o mecanismo que decide que há algo a
  observar) e não a EMISSÃO do evento de auditoria — nenhum teste do
  roster afirma a emissão para elas, e isso é uma lacuna do CORPUS,
  medida aqui, não um defeito introduzido por este relatório.
- A metade RED foi obtida removendo o enforcement do jeito MÍNIMO
  (Apêndice B): ela prova que o controle enxerga aquele mecanismo, não
  que o mecanismo é completo.
- A EXECUÇÃO em CI é condicional: os dois jobs de `validate.yml` e o
  `release-gate` carregam `if: vars.CEO_SOTA_DISABLE != '1'` (Apêndice
  E). O gate existe; essa condição não foi exercitada aqui.

## Apêndice A — metade «como está» (10/10 verde)

Cada linha rodou o SEU node id isoladamente, com o mirror de bytecode
purgado antes de cada execução (`sys.pycache_prefix` = `<HOME>/Library/Caches/com.apple.python`, com o
`$HOME` redigido pelo gerador — o arquivo landado não carrega caminho
pessoal):

```
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_check_skill_bootstrap_post.py::TestRecentBootstrapEvent::test_event_in_window_detected
1 passed in 0.08s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_webfetch_injection.py::TestWebFetchInjectionHookDetection::test_detects_harness_mimicry_in_webfetch_result
1 passed in 0.29s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_check_mcp_response.py::CheckMcpResponseStrictModeTest::test_strict_mode_blocks_high_severity_finding
1 passed in 0.27s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_check_codex_response.py::TestScanInjectionBuckets::test_scan_injection_returns_correct_family_for_system_bracket
1 passed in 0.09s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_bash_canonical_forensic.py::TestBashCanonicalForensic::test_scan_extracts_redirect_target
1 passed in 0.08s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_session_start.py::TestSessionStartInjectionWiring::test_poisoned_instructions_validate_emit_and_block
1 passed in 0.09s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_turbo_sessionstart.py::test_selftest
1 passed in 0.20s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_plan179_integration.py::TestPinningPrimaryChannel::test_compact_source_returns_full_set_from_an_empty_world
1 passed in 0.15s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_session_end_memory_delta.py::TestSpecSurface::test_written_delta_counts_only
1 passed in 0.11s
$ python3 -m pytest -q --no-header -p no:cacheprovider \
    .claude/hooks/tests/test_user_prompt_submit.py::TestUserPromptSubmitDecide::test_decide_injection_prompt_advisory_banner
1 passed in 0.08s
```

## Apêndice B — metade RED, gate a gate

Para cada linha: mutação ANCORADA (o instrumento recusa se a âncora não
ocorrer exatamente uma vez) → MESMO node id → `git restore` → MESMO
node id outra vez.

A mutação de cada linha vai INTEIRA e sem truncar (rail r1 [P2]: numa
célula de tabela truncada duas mutações apareciam como «só espaço em
branco» e como «igual à original», e o leitor não conseguia
reproduzi-las). `texto muda` e `AST muda` são MEDIDOS pelo instrumento
— uma mutação de espaço em branco imprimiria `False` em `AST muda`.

| # | Arquivo | Ocorrências da âncora | texto muda | AST muda | Enforcement removido | Restaurado |
|---|---|---|---|---|---|---|
| 1 | `check_skill_bootstrap_post.py` | 1 | True | True | 1 failed in 0.10s | 1 passed in 0.08s |
| 2 | `check_webfetch_injection.py` | 1 | True | True | 1 failed in 0.32s | 1 passed in 0.29s |
| 3 | `check_mcp_response.py` | 1 | True | True | 1 failed in 0.30s | 1 passed in 0.27s |
| 4 | `check_codex_response.py` | 1 | True | True | 1 failed in 0.10s | 1 passed in 0.09s |
| 5 | `check_bash_canonical_forensic.py` | 1 | True | True | 1 failed in 0.10s | 1 passed in 0.08s |
| 6 | `SessionStart.py` | 1 | True | True | 1 failed in 0.12s | 1 passed in 0.10s |
| 7 | `turbo_sessionstart.py` | 1 | True | True | 1 failed in 0.21s | 1 passed in 0.20s |
| 8 | `check_compact_pinning.py` | 1 | True | True | 1 failed in 0.18s | 1 passed in 0.16s |
| 9 | `SessionEnd.py` | 1 | True | True | 1 failed in 0.12s | 1 passed in 0.11s |
| 10 | `UserPromptSubmit.py` | 1 | True | True | 1 failed in 0.12s | 1 passed in 0.08s |

As mutações, verbatim (`-` = a âncora, `+` = o que a substitui):

```diff
# 1 .claude/hooks/check_skill_bootstrap_post.py
-def _recent_bootstrap_event(
-    repo_root: Path, skill_slug: str, window_s: float = 5.0
-) -> Optional[float]:
+def _recent_bootstrap_event(
+    repo_root: Path, skill_slug: str, window_s: float = 5.0
+) -> Optional[float]:
+    return None
# 2 .claude/hooks/check_webfetch_injection.py
-    sys.stdout.write(_emit_allow(system_message=msg) + "\n")
+    sys.stdout.write(_emit_allow() + "\n")
# 3 .claude/hooks/check_mcp_response.py
-{"decision": "block", "reason": reason}
+{"decision": "allow", "reason": reason}
# 4 .claude/hooks/check_codex_response.py
-def _scan_injection(text: str) -> List[Tuple[str, int]]:
+def _scan_injection(text: str) -> List[Tuple[str, int]]:
+    return []
# 5 .claude/hooks/check_bash_canonical_forensic.py
-def _scan_command_targets(command: str) -> List[str]:
-    """Extract write-shape target paths from a Bash command string."""
+def _scan_command_targets(command: str) -> List[str]:
+    """Extract write-shape target paths from a Bash command string."""
+    return []
# 6 .claude/hooks/SessionStart.py
-        if getattr(verdict, "decision", "allow") == "block":
+        if False:
# 7 .claude/hooks/turbo_sessionstart.py
-        output = {"hookSpecificOutput": hook_specific}
+        output = {}
# 8 .claude/hooks/check_compact_pinning.py
-    if not isinstance(source, str) or source != _COMPACT_SOURCE:
-        return {}
+    if True:
+        return {}
# 9 .claude/hooks/SessionEnd.py
-def _memory_delta_observed(repo_root: Path, session_id: str) -> Dict[str, object]:
+def _memory_delta_observed(repo_root: Path, session_id: str) -> Dict[str, object]:
+    return {}
# 10 .claude/hooks/UserPromptSubmit.py
-        if redact_hits > 0 or total_injection_hits > 0:
+        if False:
```

Primeira linha `E ` de cada falha (a asserção que o controle perdeu
quando o enforcement saiu):

```
check_skill_bootstrap_post.py      E           AssertionError: unexpectedly None
check_webfetch_injection.py        E       AssertionError: 'systemMessage' not found in {}
check_mcp_response.py              E       AssertionError: 'allow' != 'block'
check_codex_response.py            E       AssertionError: False is not true
check_bash_canonical_forensic.py   E       AssertionError: '.claude/team.md' not found in []
SessionStart.py                    E       AssertionError: 0 != 1
turbo_sessionstart.py              E       AssertionError: Traceback (most recent call last):
check_compact_pinning.py           E       AssertionError: unexpectedly None : the PRIMARY pinning channel emitted nothing
SessionEnd.py                      E       KeyError: 'outcome'
UserPromptSubmit.py                E       AssertionError: 'advisory' not found in ''
```

Registro cru das 10 linhas: `payload/census.json` (`asis`, `red`,
`restored`, `neuter_old`, `neuter_new`, `porcelain_after_restore`).

## Apêndice C — contagem derivada, não digitada

A linha de contagem do §2 é impressa por `gen-count.py` sobre ESTE
arquivo. O discriminante é o node id (`::`), que só existe nas linhas
da tabela do §2 — a tabela do Apêndice B também é numerada, e um
`^\| [0-9]+ \|` sozinho casaria as duas.

As linhas abaixo NÃO foram escritas à mão: elas são a lista
`SHELL_EQUIV` do próprio `gen-count.py`, e o `gen-evidence.py` RODA cada
uma contra o relatório entregue e recusa se alguma discordar da
derivação em Python. A quarta coluna do §2 já mostrou por que isso
importa: um `grep '1 failed in'` sem o `grep -v '::'` devolve **20**,
porque cada linha do §2 também cita `1 failed in` na coluna
«Enforcement removido».

```
# linhas da tabela do §2 (o node id é o discriminante)
grep -cE '^\| [0-9]+ \|.*::' <relatório>
# verdito verde
grep -E '^\| [0-9]+ \|.*::' <relatório> | grep -c '[*][*]verde[*][*]'
# controle vácuo
grep -E '^\| [0-9]+ \|.*::' <relatório> | grep -c 'vácuo'
# sem controle
grep -E '^\| [0-9]+ \|.*::' <relatório> | grep -v 'sem-controle-por-design' | grep -c 'sem controle'
# sem-controle-por-design
grep -E '^\| [0-9]+ \|.*::' <relatório> | grep -c 'sem-controle-por-design'
# UNREGISTERED
grep -E '^\| [0-9]+ \|.*::' <relatório> | grep -c 'UNREGISTERED'
# metades vermelhas do Apêndice B — o `grep -v '::'` é obrigatório: sem ele as linhas do §2, que citam `1 failed in` na coluna «Enforcement removido», dobram a contagem
grep -E '^\| [0-9]+ \|' <relatório> | grep -v '::' | grep -c '1 failed in'
# linhas da partição do §1
grep -cE '^\| R\[ *[0-9]+\] \|' <relatório>
# linhas marcadas como deste lote
grep -E '^\| R\[ *[0-9]+\] \|' <relatório> | grep -c 'lote 4 (ESTE)'
```

O controle NEGATIVO de `gen-count.py`: uma linha plantada na tabela do
§2 muda o número impresso — comando e saída no `EVIDENCE.md` do pack.

## Apêndice D — os registros em `.claude/settings.json`, medidos

Cada registro é um PAR — a linha `"matcher"` e a linha `"command"`
que nomeia o script. A varredura crua é limitada ao objeto `hooks` por
contagem de chaves, porque `settings.json` carrega outras chaves
`"command"` (o `statusLine`) que não são registro de hook; o
pareamento é posicional e o instrumento ABORTA se o número de entradas
parseadas não bater com o número de linhas cruas.

| Arquivo | Evento | Matcher | l. `matcher` | l. `command` | `timeout` |
|---|---|---|---|---|---|
| `check_skill_bootstrap_post.py` | `PostToolUse` | `Edit|Write|MultiEdit` | 448 | 452 | 5 |
| `check_webfetch_injection.py` | `PostToolUse` | `WebFetch|WebSearch` | 460 | 464 | 5 |
| `check_mcp_response.py` | `PostToolUse` | `mcp__.*` | 472 | 476 | 5 |
| `check_codex_response.py` | `PostToolUse` | `mcp__codex__codex|mcp__codex__codex-reply` | 484 | 488 | 5 |
| `check_bash_canonical_forensic.py` | `PostToolUse` | `Bash` | 496 | 500 | 5 |
| `SessionStart.py` | `SessionStart` | *(vazio)* | 536 | 540 | 5 |
| `turbo_sessionstart.py` | `SessionStart` | *(vazio)* | 548 | 552 | 5 |
| `check_compact_pinning.py` | `SessionStart` | `compact` | 560 | 564 | 5 |
| `SessionEnd.py` | `SessionEnd` | *(vazio)* | 574 | 578 | 5 |
| `UserPromptSubmit.py` | `UserPromptSubmit` | *(vazio)* | 588 | 592 | 5 |

Os 10 arquivos desta fatia têm **uma** registração cada — nenhum é
`UNREGISTERED` e nenhum entra por host de despacho.

## Apêndice E — quem EXECUTA os controles (derivado dos workflows)

A coluna `selecionados` NÃO é leitura da expressão: é o resultado de
rodar `pytest --collect-only` com o `-m` daquele sítio sobre os 10 node
ids deste lote.

| Workflow | Job | `if:` do job | Step (linha) | Linha do `pytest` | `-m` | Estreitamento | selecionados |
|---|---|---|---|---|---|---|---|
| `coverage.yml` | `coverage` | *(nenhum)* | Run hook tests under coverage (subprocess capture, parallel) (l. 90) | l. 102 | — | *(nenhum)* | **10/10** |
| `mutation-gate.yml` | `mutate` | *(nenhum)* | AC2a — fail fast if the leg filter selects 0 tests (l. 102) | l. 105 | — | -k (subconjunto por expressão) | ***não medível fora da CI — -k (subconjunto por expressão)*** |
| `mutation-gate.yml` | `mutate` | *(nenhum)* | baseline test run (leg filter) (l. 115) | l. 117 | — | -k (subconjunto por expressão) | ***não medível fora da CI — -k (subconjunto por expressão)*** |
| `mutation-gate.yml` | `mutate` | *(nenhum)* | mutation run (single module, narrowed runner) (l. 121) | l. 130 | — | -k (subconjunto por expressão) | ***não medível fora da CI — -k (subconjunto por expressão)*** |
| `release.yml` | `release-gate` | `if: vars.CEO_SOTA_DISABLE != '1'` | Hook test suite (all 168+ tests) (l. 388) | l. 390 | — | *(nenhum)* | **10/10** |
| `validate.yml` | `hook-tests-dual-rail` | `if: vars.CEO_SOTA_DISABLE != '1'` | Run hook tests with CEO_NATIVE_SUBAGENTS=${{ matrix.native_subagents }} (l. 1588) | l. 1594 | `not serial` | *(nenhum)* | **10/10** |
| `validate.yml` | `hook-tests-dual-rail` | `if: vars.CEO_SOTA_DISABLE != '1'` | Run hook tests with CEO_NATIVE_SUBAGENTS=${{ matrix.native_subagents }} (l. 1588) | l. 1595 | `serial` | *(nenhum)* | **0/10** |
| `validate.yml` | `hook-tests-python-matrix` | `if: vars.CEO_SOTA_DISABLE != '1'` | Run hook + script tests on Python ${{ matrix.python-version }} (l. 1631) | l. 1644 | `not serial` | *(nenhum)* | **10/10** |
| `validate.yml` | `hook-tests-python-matrix` | `if: vars.CEO_SOTA_DISABLE != '1'` | Run hook + script tests on Python ${{ matrix.python-version }} (l. 1631) | l. 1646 | `serial` | *(nenhum)* | **0/10** |

Leitura: **4** sítios selecionam e executam os 10 controles deste lote
(`coverage.yml`:102, `release.yml`:390, `validate.yml`:1594, `validate.yml`:1644). Os outros 5 **não** provam nada sobre eles: `mutation-gate.yml`:105 (não medível fora da CI — -k (subconjunto por expressão)); `mutation-gate.yml`:117 (não medível fora da CI — -k (subconjunto por expressão)); `mutation-gate.yml`:130 (não medível fora da CI — -k (subconjunto por expressão)); `validate.yml`:1595 (-m 'serial' seleciona 0/10); `validate.yml`:1646 (-m 'serial' seleciona 0/10).

Os JOBS continuam sendo 4, porque cada um deles roda os controles pela
sua perna que os seleciona — o que a rodada r2 do rail derrubou foi a
contagem por COMANDO, não a por job.

## Apêndice F — detector de rota de bloqueio, hook a hook

Formas procuradas (a tabela é o instrumento se descrevendo; o limite
do §3 é o COMPLEMENTO dela):

| id da forma | o que casa |
|---|---|
| `call-block` | chamada `*.block(...)` (AST) |
| `dict-decision` | dicionário literal com `"decision": "block"` (AST) |
| `cmp-decision` | comparação `<x>.get("decision") == "block"` / `<x>["decision"] == "block"` (AST) |
| `getattr-decision` | comparação `getattr(<x>, "decision", ...) == "block"` (AST — forma NOVA no lote 4) |
| `text-decision` | varredura de texto: `"decision"` seguido de `"block"` na mesma linha |
| `dict-permissionDecision` | dicionário literal com `"permissionDecision": "deny"` (AST) |
| `cmp-permissionDecision` | comparação `<x>.get("permissionDecision") == "deny"` / `<x>["permissionDecision"] == "deny"` (AST) |
| `getattr-permissionDecision` | comparação `getattr(<x>, "permissionDecision", ...) == "deny"` (AST — forma NOVA no lote 4) |
| `text-permissionDecision` | varredura de texto: `"permissionDecision"` seguido de `"deny"` na mesma linha |

Controle positivo do próprio detector (módulo sintético; o instrumento
RECUSA rodar se algum destes for zero): `dict-decision` = 1, `getattr-decision` = 1, constantes de env = 1, getters de env = 1.

| Arquivo | Construtos de bloqueio (forma @ linha) | `CEO_*`/`CLAUDE_*` consumidos (getter) | ligados a constante de módulo | medição dinâmica |
|---|---|---|---|---|
| `check_skill_bootstrap_post.py` | **nenhum** | `CLAUDE_PROJECT_DIR` | `CEO_SKILL_BOOTSTRAP_POST` | *(sem construto — nada a medir)* |
| `check_webfetch_injection.py` | **nenhum** | `CEO_WEBFETCH_INJECTION_SCAN`, `CLAUDE_PROJECT_DIR` | — | *(sem construto — nada a medir)* |
| `check_mcp_response.py` | `text-decision`@13, `dict-decision`@65 | `CEO_MCP_SCANNER_DISABLE`, `CEO_MCP_SCANNER_MODE` | — | `test_strict_mode_blocks_high_severity_finding` → **verde** |
| `check_codex_response.py` | **nenhum** | `CEO_BOOT_DEBUG`, `CEO_CODEX_REVIEW_OBSERVE`, `CLAUDE_PROJECT_DIR` | — | *(sem construto — nada a medir)* |
| `check_bash_canonical_forensic.py` | **nenhum** | `CLAUDE_PROJECT_DIR` | — | *(sem construto — nada a medir)* |
| `SessionStart.py` | `getattr-decision`@380 | `CEO_PROJECT_STATE_DIR`, `CLAUDE_PROJECT_DIR`, `CLAUDE_SESSION_ID` | `CEO_EXTENDED_LIFECYCLE` | `test_poisoned_instructions_validate_emit_and_block` → **verde** |
| `turbo_sessionstart.py` | **nenhum** | `CEO_AUTO_BOOT`, `CLAUDE_PROJECT_DIR` | — | *(sem construto — nada a medir)* |
| `check_compact_pinning.py` | **nenhum** | `CEO_CONSTRAINT_PINNING` | — | *(sem construto — nada a medir)* |
| `SessionEnd.py` | **nenhum** | `CEO_AUDIT_LOG_DIR`, `CEO_AUDIT_LOG_PATH`, `CEO_VALUE_DASHBOARD_AUTO`, `CLAUDE_PROJECT_DIR`, `CLAUDE_SESSION_END_REASON`, `CLAUDE_SESSION_ID` | `CEO_AUDIT_TOKENS_AUTO`, `CEO_EXTENDED_LIFECYCLE`, `CEO_SESSION_MEMORY_DELTA` | *(sem construto — nada a medir)* |
| `UserPromptSubmit.py` | **nenhum** | `CEO_OPTIMIZER`, `CLAUDE_PROJECT_DIR`, `CLAUDE_SESSION_ID` | `CEO_EXTENDED_LIFECYCLE`, `CEO_PROMPT_INJECTION_SCAN` | *(sem construto — nada a medir)* |

Nota medida sobre `check_mcp_response.py`: o construto `text-decision`
da linha 13 está dentro do DOCSTRING do módulo (a varredura de texto é
cega a contexto, por desenho — ela existe para pegar o que o AST não
parseia). O construto executável é o `dict-decision` da linha 65, e é
ele que a medição dinâmica muta.

Sobre os kill-switches: eles DESLIGAM o hook, não o fazem bloquear —
são a rota oposta à procurada aqui, e estão listados por transparência
(um censo que ignore `CEO_EXTENDED_LIFECYCLE` não sabe dizer em que
configuração as linhas de ciclo de vida deste lote sequer rodam).

## Apêndice G — o que o W0 ainda deve

- `lotes 5-6 = R[30:42]` — 12 hooks registrados sem censo.
- A lacuna de corpus do §4: nenhum teste do roster afirma a EMISSÃO do
  evento de auditoria para as linhas cujo controle prova só a detecção.

