# wave 179-followup-flip — rail codex rodada 1 (sombra base dc72bf1, 2026-09-02 S338)

Rail-Verdict: CHANGES-REQUESTED (1 P1 — verificado REAL por censo; curado ANTES da r2 com expansao de escopo DIRIGIDA PELO RAIL: 3 → 5 paths)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretorio da sombra `shadow-179fu`
(3 paths: SessionStart.py, SessionEnd.py, test_session_end_memory_delta.py),
stdin `</dev/null`. Saida bruta: `codex-r1.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-followup-flip/`] (6.223 linhas; rc 0).
Snapshot sha256 de `git diff` antes/depois:
`e3725048f2a27f400341d9366c59948a9746342d839462829e3b72ac959b86b3` nos dois
lados ⇒ **TREE-INTACT**. O bloco de achados veio sob `Review comment:` (o
rail corrente nao emite `VERDICT:` nem `Full review comments:`; rodada limpa
= ausencia de bloco de comentarios).

## O achado (e o que a cura fez)

1. **[P1, REAL] «Flip every lifecycle producer atomically»**
   (`SessionEnd.py:1206-1208` na sombra). Claim: com `CLAUDE_SESSION_ID` ≠
   payload — exatamente o caso que a wave mira — `session_start`/`session_end`
   passam a ser payload-scoped enquanto `UserPromptSubmit.py:311-314`
   (`prompt_submitted`) e `Stop.py:187-190` (`session_stop`) seguem env-first;
   leitores que particionam por `session_id` (ex.
   `ceo-escalation-detector.py:174-178`) omitiriam parte do MESMO ciclo de
   vida. Sugestao do rail: flipar os produtores restantes atomicamente, OU
   manter o id do US8 separado do id legado.

   **Verificacao (contra o codigo, nao a fe):** `Stop.py:187-191` e
   `UserPromptSubmit.py:311-315` lidos — MESMA forma
   `(env or getattr(event,"session_id","") or "") or <timestamp>`;
   `ceo-escalation-detector.py:163-178` lido — `auto_detect_recent_session`
   escolhe o `session_id` com mais eventos e `filter_by_session` filtra por
   igualdade. **Censo mecanico** de TODO sitio `CLAUDE_SESSION_ID` em
   `.claude/hooks` (nao-teste) e `.claude/scripts`: a classe «produtor de
   ciclo de vida env-first» tem EXATAMENTE 4 membros (SessionStart, SessionEnd,
   Stop, UserPromptSubmit); todos os sitios de id-threading mais novos ja sao
   payload-first (`check_canonical_edit.py:3068-3071`, `check_notification.py:98-103`,
   `check_pair_rail.py:1707-1711`, `codex_review_user_code.py:347`,
   `check_codex_stop_review.py:683-685`); e `check_anti_ceo_overhead.py:166`
   chaveia o record do tool_lifecycle pelo id do EVENTO ⇒ o flip tambem alinha
   `SessionEnd._cleanup_tool_lifecycle(session_id)` com os records que ele
   apaga. Correcao de premissa do rail: o ciclo de vida JA estava fragmentado
   sob divergencia (toda a familia PreToolUse/PostToolUse e o delta US8 sao
   payload-id; so os 4 lifecycle eram env-id) — o flip parcial REDUZIA a
   fragmentacao mas deixava 2 produtores do lado errado. A varredura P2 da
   S337 so procurou LEITORES de `session_start`; os produtores irmaos ficaram
   fora dela.

   **Decisao / CURA:** a segunda rota do rail (manter o id do US8 separado) e
   o status quo que o FOLLOWUP rejeita (o produtor TEM de gravar sob o id que
   o consumidor le). Cura pela primeira rota — flip dos QUATRO produtores no
   MESMO patch — porque (a) a classe e fechada e medida (4 membros, forma
   identica), (b) a justificativa do AC (SPEC «threaded from the harness
   event»; env spoofable) vale igual para `prompt_submitted`/`session_stop`,
   (c) doutrina do repo: patch ramo-a-ramo gera a proxima regressao
   ([[feedback-branch-local-patching-induces-regressions]]) e rail acha a
   classe / censo fecha ([[feedback-rail-finds-the-class-census-closes-it]]),
   (d) os 4 sao KERNEL — uma cerimonia em vez de duas. `apply-179fu-flip.py`
   ganha 2 edicoes (Stop.py, UserPromptSubmit.py — mesma linha, mesmo
   comentario), o lock estrutural cobre os 4 `main()`, e
   `TestProducerIdPrecedence` ganha os testes de linha gravada para
   `prompt_submitted` e `session_stop` (+ fallbacks sobre os 4). **Expansao de
   escopo em relacao ao brief (2 hooks) — declarada aqui, no DESIGN, no
   PROPOSED e no retorno estruturado para veto do Owner no SIGN.**

## Residual do censo (FORA do patch, nomeado)

- `check_output_secrets.py:404-408` (`env or parsed.session_id or ""`) e
  env-first, mas e security-matcher PostToolUse, nao produtor de ciclo de
  vida — outra classe de risco; `check_agent_spawn.py:425` e os ~20 emits
  `session_id=os.environ.get("CLAUDE_SESSION_ID","")` em `_lib/` e
  `check_bash_safety.py` sao env-ONLY (sem payload em escopo) — atribuicao
  best-effort, nao precedencia. Registrados para decisao do Owner; nao
  entram nesta wave.

## Verificacao das claims

Arquivos lidos: `Stop.py:160-215`, `UserPromptSubmit.py:270-340`,
`ceo-escalation-detector.py:160-180`, `check_anti_ceo_overhead.py:166`,
`_lib/tool_lifecycle.py:313-333`; censo por script sobre 58 arquivos com
`CLAUDE_SESSION_ID`. Nenhum teste existente afirma env-first para Stop ou
UserPromptSubmit (grep em `hooks/tests`: o unico lock era o da r12 P2-b, ja
invertido nesta wave). Pos-cura: sombra re-derivada do zero e bateria
re-medida — ver `rail-round-2.md` e `EVIDENCE.md`.
