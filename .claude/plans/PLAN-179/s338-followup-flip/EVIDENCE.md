# EVIDENCE — wave `179-followup-flip` (S338, 2026-09-01/02) — pack build (nao e o LAND)

Tudo abaixo foi MEDIDO nesta sessao (subagente do orquestrador night-s338),
na sombra `shadow-179fu` (worktree destacada em HEAD) e numa worktree de
CONTROLE descartada; a arvore viva nao foi tocada fora de
`.claude/plans/PLAN-179/s338-followup-flip/` (nenhum git add/commit/reset/
stash/checkout na arvore viva). Comandos exatos e numeros FINAIS — todos
re-medidos DEPOIS da ultima edicao do script (a sombra foi re-derivada do
zero antes da bateria final). HEAD moveu durante a construcao
(`dc72bf1` → `6160578` pacote S337 → `f0e98de` materiais fable51); os 5
paths do pack sao byte-identicos em `dc72bf1..f0e98de`
(`git diff --stat dc72bf1..HEAD -- <5 paths>` vazio) e o script verifica nos
dois HEADs.

## 0. Baseline pre-flip (o defeito, reproduzido) — `exp_baseline.py`, sombra em HEAD

Env `CLAUDE_SESSION_ID=env-divergent-id`, stdin `{"session_id": "payload-id"}`
para `SessionStart.main()` e `SessionEnd.main()` sob env isolado
(HOME/CLAUDE_PROJECT_DIR/CEO_AUDIT_LOG_* em tmp, sync mode). Cadeia gravada:

    first_run_wizard_dispatched | None              | signed
    session_start               | env-divergent-id  | signed   <- produtor legado env-first
    session_memory_delta_observed | payload-id       | signed   <- rail novo, payload-only
    session_end                 | env-divergent-id  | signed   <- produtor legado env-first
    session_start (sem ids)     | 20260902T013753   | signed   <- fallback timestamp
    session_end (env only)      | env-only-id       | signed   <- fallback env

`SessionEnd._session_start_ts("payload-id", proj)` = `(None, "none")`: o
consumidor payload-gated NAO ancora — o `start_unknown` do FOLLOWUP, ao vivo.
(Stop/UserPromptSubmit tem a MESMA linha env-first — censo em `rail-round-1.md`.)

## 1. Derivacao (script FINAL — 11 edicoes / 5 paths)

    python3 apply-179fu-flip.py --list-paths                 -> 5 paths (SessionStart, UserPromptSubmit, Stop, SessionEnd, test_session_end_memory_delta)
    python3 apply-179fu-flip.py --root <shadow> --check-only -> "11 edicao(oes) aplicaveis em 5 path(s); nada escrito" rc 0   (em dc72bf1 E em f0e98de)
    python3 apply-179fu-flip.py --root <shadow>              -> "11 edicao(oes) aplicadas em 5 path(s)" rc 0
    python3 apply-179fu-flip.py --root <shadow> --check-only -> RECUSADO ("ja contem 'PLAN-179-FOLLOWUP (S338)' — arvore ja patchada?") rc 1
    git -C <shadow> diff --numstat:
        16  10  .claude/hooks/SessionEnd.py
        12   2  .claude/hooks/SessionStart.py
        12   2  .claude/hooks/Stop.py
        12   2  .claude/hooks/UserPromptSubmit.py
       278  20  .claude/hooks/tests/test_session_end_memory_delta.py
    git -C <shadow> diff | shasum -a 256 -> ba5efe981865076e132f688b6b52741f8eb55ede877601cf6bb8ddc212dc021b  (sombra final; identico antes/depois da r2)
    git grep -c "PLAN-179-FOLLOWUP (S338)" HEAD -- <5 paths>  -> 0 (nao-vacuo)

## 2. Oraculos de caminho (arvore viva, read-only)

    python3 .claude/hooks/check_canonical_edit.py --is-canonical <5 paths>
        .claude/hooks/SessionStart.py                         1
        .claude/hooks/UserPromptSubmit.py                     1
        .claude/hooks/Stop.py                                 1
        .claude/hooks/SessionEnd.py                           1
        .claude/hooks/tests/test_session_end_memory_delta.py  0
    _KERNEL_PATHS (check_arbitration_kernel.py, AnnAssign de 110 entradas, fnmatch):
        SessionStart.py ":218"  SessionEnd.py ":219"  Stop.py ":220"  UserPromptSubmit.py ":221" -> TODOS KERNEL; o teste nao
        git log -S: membros desde 9777a8d (v1.0.0) — o LAND arma CEO_KERNEL_OVERRIDE/_ACK no menor escopo
    .claude/governance/gate-scripts-manifest.txt (ADR-192, 9 membros): nenhum dos 5
    dist/ceo-plugin/hooks/*: gitignored (.gitignore:198), gerado por build-plugin.py — fora do patch

## 3. Bateria FINAL (sombra re-derivada em f0e98de, DEPOIS da ultima edicao)

    PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile <5 .py>                      -> OK
    PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
        .claude/hooks/tests/test_session_end_memory_delta.py \
        .claude/hooks/tests/test_SessionEnd.py .claude/hooks/tests/test_SessionStart.py \
        .claude/hooks/tests/test_audit_emit.py .claude/hooks/tests/test_audit_emit_api_contract.py \
        .claude/hooks/tests/test_audit_emit_async_flush.py .claude/hooks/tests/test_audit_emit_coverage.py \
        .claude/hooks/tests/test_audit_emit_plan088_canonical13.py \
        .claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py \
        .claude/hooks/tests/test_audit_hmac_rotation_scenarios.py .claude/hooks/tests/test_closeout_guard.py \
        .claude/hooks/tests/test_codex_audit_chain.py .claude/hooks/tests/test_codex_advisory_teeth.py \
        .claude/hooks/tests/test_codex_killswitch_teeth.py .claude/hooks/tests/test_escalation_signals.py \
        .claude/hooks/tests/test_lifecycle_edge_cases.py .claude/hooks/tests/test_session_end.py \
        .claude/hooks/tests/test_session_start.py .claude/hooks/tests/test_stop.py \
        .claude/hooks/tests/test_user_prompt_submit.py .claude/hooks/tests/test_user_prompt_submit_salt.py
        -> 551 passed, 2 xfailed in 457.49s (0:07:37)   rc 0
           (xfails PRE-EXISTENTES: test_audit_emit_async_flush.py:249 run=False; test_audit_emit_coverage.py:1595)
    ... test_session_end_memory_delta.py sozinho                                 -> 60 passed in 1.35s (52 em HEAD -> 60: +9 novos, -1 substituido em-lugar)
    python3 .claude/scripts/check-test-env-hygiene.py                            -> rc 0 "OK: test-env hygiene clean (337 flagged files, all allowlisted)"
    python3 .claude/scripts/check-hook-stdout-schema.py --repo <shadow> \
        --only SessionStart.py --only SessionEnd.py --only Stop.py --only UserPromptSubmit.py
        -> rc 0  "SessionEnd.py OK / SessionStart.py OK / Stop.py OK / UserPromptSubmit.py OK /
                  hook-stdout-schema: 4 wired script(s), 4 registration(s), 0 violation(s)"
    python3 .claude/scripts/check-active-hooks-executable.py                     -> rc 0 (93 refs present+executable)
    bash .claude/scripts/local/verify-counts.sh                                  -> rc 0 ("no drift detected"; cited ~15400)
    python3 .claude/scripts/check-claude-md-claims.py                            -> rc 0
    python3 .claude/scripts/check-installer-write-safety.py                      -> rc 0 (scripts/ intocado; baseline nao regenerado)
    Live-fire smoke de hooks: NAO existe runner dedicado em .claude/scripts (grep: so
    check-active-hooks-executable.py, check-hook-stdout-schema.py, hook-profiler.py);
    o mais proximo — check-hook-stdout-schema.py — EXECUTA os 4 hooks WIRED com
    fixtures (infra + behavioural) e saiu 0 acima. O V-block do LAND (a escrever)
    deve incluir esse step com --only nos 4 hooks.
    (Bateria intermediaria da versao de 3 paths, antes da r1: 514 passed / 2 xfailed
    em 19 arquivos — superada; registrada so para rastreabilidade.)

## 4. Controle positivo (script FINAL; os QUATRO hooks SEM o flip)

    worktree de controle em HEAD -> apply-179fu-flip.py -> git checkout -- <4 hooks>  (so o teste difere: +278/-20)
    pytest -k "TestProducerIdPrecedence or TestProducerConsumerAlignment or test_lifecycle_id_is_payload_first" -rA:
        FAILED TestSpecSurface::test_lifecycle_id_is_payload_first_in_all_four_producers
        FAILED TestProducerIdPrecedence::test_session_start_records_payload_id_under_divergent_env
        FAILED TestProducerIdPrecedence::test_prompt_submitted_records_payload_id_under_divergent_env
        FAILED TestProducerIdPrecedence::test_session_stop_records_payload_id_under_divergent_env
        FAILED TestProducerIdPrecedence::test_session_end_records_payload_id_under_divergent_env
        FAILED TestProducerConsumerAlignment::test_divergent_env_start_is_anchored_by_payload_gated_consumer
        FAILED TestProducerConsumerAlignment::test_divergent_env_end_segments_the_resume_window
        PASSED TestProducerIdPrecedence::test_env_id_is_the_fallback_when_payload_has_no_id         (preservacao — DEVE passar pre-flip)
        PASSED TestProducerIdPrecedence::test_timestamp_fallback_when_neither_carries_an_id          (preservacao — DEVE passar pre-flip)
        -> 7 failed, 2 passed
    arquivo inteiro no controle -> 7 failed, 53 passed (os 53 pre-existentes imoveis)
    Na sombra COM o flip: os mesmos 9 -> 9 passed (dentro dos 60).
    (Controle da versao de 3 paths, antes da r1: 5 failed / 2 passed — coerente.)
    A worktree de controle foi removida (`git worktree remove --force`).

## 5. Achado durante a construcao (curado no TESTE, nao no hook)

O 1o run do teste de start deu `outcome=absent` com `anchor_source=chain`: o
`ts` do wire e second-floor e o consumidor abre a janela no PROXIMO segundo
inteiro (`SessionEnd.py:828-829`, `start_ts += 1.0`). Debug (`dbg_startleg.py`):
`ts=...T01:45:49Z`, `parsed=…549.0`, `mtime=…549.594` ⇒ fora da janela por
contrato. Cura: o teste espera a fronteira no relogio REAL (<1,1 s, derivada
do `ts` da linha gravada) — mockar `time.time` testaria a costura. Re-derivado
e re-medido (secao 3).

## 6. Pair-rail (2 rodadas; comando de DENTRO da sombra)

`codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write" </dev/null`

    r1 (sombra de 3 paths, base dc72bf1): rc 0; diff sha e3725048f2a27f400341d9366c59948a9746342d839462829e3b72ac959b86b3 antes = depois -> TREE-INTACT
        1 P1 REAL: Stop.py/UserPromptSubmit.py seguiam env-first -> flip parcial fragmenta o ciclo de vida
        CURA: classe fechada por censo -> 4 produtores no patch (rail-round-1.md)
    r2 (sombra RE-DERIVADA de 5 paths, base f0e98de): rc 0; diff sha ba5efe98... antes = depois -> TREE-INTACT
        P1 da r1 NAO reaberto ("The functional tests pass"); 1 P1 de PROCESSO: sentinel Owner-signed ausente
        na sombra — por desenho (molde fable51 r1/r2 #2); sem cura no patch; sem r3 (rail-round-2.md)
    Ultimo veredito registrado: CHANGES-REQUESTED (processo).

## 7. Residuais / o que este pack NAO entrega

- SIGN/LAND/finalize da cerimonia (Owner GPG; KERNEL 4 ⇒ override no menor
  escopo; escopo do sentinel = 4 hooks + teste) — nao escritos por este
  subagente, por desenho do brief.
- Expansao de escopo dirigida pelo rail (2 → 4 hooks) — decisao final do
  Owner no SIGN; se recusada, as 2 EDITS de Stop/UserPromptSubmit e os 2
  testes correspondentes teriam de sair do script e TODOS os numeros
  re-medidos (nao ha variante suportada).
- Censo residual (fora do patch): `check_output_secrets.py:404-408` env-first
  (security-matcher); ~20 emits env-ONLY em `_lib/`/`check_bash_safety.py`.
- Flip do frontmatter/`[x]` do `PLAN-179-FOLLOWUP-...md` (commitado em
  `6160578`) — do orquestrador/Owner.
- Registro opcional da precedencia nas linhas v2.7 do SPEC (deny-Edit) —
  fora desta wave, compativel por construcao (varredura S337).
