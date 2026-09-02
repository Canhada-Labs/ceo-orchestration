# PROPOSED-PATCH (DRAFT) — wave `179-followup-flip` (S338, PLAN-179-FOLLOWUP AC item 1 + rail r1)

Patch: derivado da sombra `shadow-179fu` pela aplicacao de
`apply-179fu-flip.py` (11 edicoes, 5 paths). Base: HEAD no momento do
finalize — verificado em `dc72bf1` (inicio da S338) e `f0e98de` (HEAD
corrente); os 5 paths sao byte-identicos entre os dois. O finalize/LAND da
cerimonia (a escrever pelo orquestrador/Owner) prova `HEAD + script ==
patch` byte a byte em cada path.
Patch-sha256: TO-FILL-AT-FINAL-PATCH (o `.patch` e produzido pelo finalize;
`git -C <shadow> diff | shasum -a 256` da sombra FINAL =
`ba5efe981865076e132f688b6b52741f8eb55ede877601cf6bb8ddc212dc021b`, identico
antes e depois da r2 — TREE-INTACT)

## Por path (5)

| path | oraculo `--is-canonical` | KERNEL (`_KERNEL_PATHS`) | ADR-192 | o que muda |
|---|---|---|---|---|
| `.claude/hooks/SessionStart.py` | **1 CANONICO** | **SIM** (`:218`, desde v1.0.0) | nao | `main()`: `session_id` resolve PAYLOAD-first — `(getattr(event,"session_id","") or "") or os.environ.get("CLAUDE_SESSION_ID","")`, timestamp fallback inalterado; comentario compartilhado de 10 linhas (+12/−2) |
| `.claude/hooks/UserPromptSubmit.py` | **1 CANONICO** | **SIM** (`:221`) | nao | `main()`: idem, forma `( ... ) or <timestamp>`; produtor de `prompt_submitted` (+12/−2) — **rail r1** |
| `.claude/hooks/Stop.py` | **1 CANONICO** | **SIM** (`:220`) | nao | `main()`: idem; produtor de `session_stop` (+12/−2) — **rail r1** |
| `.claude/hooks/SessionEnd.py` | **1 CANONICO** | **SIM** (`:219`) | nao | `main()`: `session_id = (payload_sid or os.environ.get("CLAUDE_SESSION_ID","")) or <timestamp>`; o comentario r12 P2-b e reescrito para a precedencia nova; `payload_sid` e `payload_session_id=payload_sid` INTOCADOS (+16/−10) |
| `.claude/hooks/tests/test_session_end_memory_delta.py` | 0 livre | nao | nao | imports `ast`/`inspect`/`io` + `import SessionStart`/`Stop`/`UserPromptSubmit`; helpers `_run_hook_main` (dirige o `main()` real: stdin JSON + env via `mock.patch.dict`, `None` = var ausente) e `_session_id_operands` (operandos do `or` por AST); `_DeltaBase._chain_rows`; docstring da trava `test_divergent_env_id_never_anchors` (consumidor INALTERADO); `test_lifecycle_id_mirrors_sessionstart_env_first` → `test_lifecycle_id_is_payload_first_in_all_four_producers` (INVERTIDO em-lugar, estrutural, 4 hooks); classes novas `TestProducerIdPrecedence` (6: as 4 actions gravam o id do PAYLOAD sob env divergente; fallback env ×4; fallback timestamp ×4) e `TestProducerConsumerAlignment` (2: start ancorado pelo consumidor payload-gated = `chain`/`written`; end segmenta a janela do resume = `chain`/`absent`) (+278/−20) |

## O que este patch NAO faz

- Nao toca `SessionEnd._session_start_ts` nem `decide()`: o consumidor
  segue payload-gated; a trava `test_divergent_env_id_never_anchors` fica.
- Nao toca o rail novo (`payload_sid`, sem fallback) nem `audit_emit.py`,
  `SPEC/v1`, `settings*.json`, `scripts/`, `dist/` (gitignored).
- Nao relaxa nenhum teste: o unico teste removido e o lock da precedencia
  que esta wave troca, substituido em-lugar pelo lock inverso e mais forte.
- Nao muda comportamento alem da precedencia (fallbacks env e timestamp
  preservados e testados nos 4 produtores).
- Nao toca `check_output_secrets.py` (env-first, mas security-matcher — outra
  classe; residual declarado em `rail-round-1.md`).
- Nao flipa o frontmatter/`[x]` do `PLAN-179-FOLLOWUP-...md` (commitado em
  `6160578`) — do orquestrador/Owner.

## Evidencia pre-assinatura (S338, sombra base f0e98de, script final)

- Arquivo tocado sozinho: **60 passed**; bateria declarada de 21 arquivos:
  ver `EVIDENCE.md` §3 (numeros finais, medidos DEPOIS da ultima edicao).
- Controle positivo (4 hooks em HEAD + testes novos): **7 failed / 2 passed**
  — RED exatamente {lock estrutural, start/prompt/stop/end gravam payload
  id, start ancorado, end segmenta}; GREEN {fallback env, fallback
  timestamp}. Arquivo inteiro no controle: 7 failed / 53 passed.
- Gates: ver `EVIDENCE.md` §3 (env-hygiene, hook-stdout-schema `--only` ×4,
  active-hooks, verify-counts, claims, ratchet, `py_compile` 5/5).
- Reprodutibilidade: `--check-only` em HEAD = 11 aplicaveis; aplicado =
  11/5; re-aplicacao = RECUSADO (arvore intocada); marcador 0× em HEAD nos
  5 paths.
- Rail codex: r1 = 1 P1 REAL (→ classe fechada nos 4 produtores); r2 = ver
  `rail-round-2.md` / `codex-r2.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-followup-flip/`] (TREE-INTACT medido por sha256 do diff
  antes/depois de cada rodada).
