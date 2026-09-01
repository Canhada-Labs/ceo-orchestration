# PROPOSED-PATCH — wave-179close (S335)

Patch: `W179CLOSE.patch` (derivado da sombra `shadow-179close` pelo
`finalize-179close.sh`; base declarada em `BASE-SHA.txt`).
Patch-sha256: 7993b84052441056f0992bdaaa74f8616a184faa58b5bce25d3a284d9f9c87e7

## Por path (18)

| path | oráculo | o que muda |
|---|---|---|
| `.claude/hooks/check_precompact_continuity.py` | CANÔNICO | US7 `_ledger_index()` (plan por PATHS do último commit, r1-C6; deadline re-checado e propagado ao `_git` — rails r1/r2) + US2b `_eta_advisory()` (η=887‰ inteiro, proveniência framework-trace declarada) |
| `.claude/hooks/check_postcompact_reinject.py` | CANÔNICO | pointer ESTRUTURAL do ledger com gate de SHAPE (path exato + sha hex; fora ⇒ drop — rail r2) |
| `.claude/hooks/SessionEnd.py` | CANÔNICO | US8 da spec assinada: delta stat-only, âncora chain(oldest-in-window, HMAC-verificada)→birthtime→none, sanitize NFKC-then-check + guardrail fail-closed, linha do operador, kill-switch 3-estados |
| `.claude/hooks/_lib/audit_emit.py` | CANÔNICO (KERNEL) | ação `session_memory_delta_observed` (330→331), emitter tipado, allowlist deny-by-default + enums TYPE-strict |
| `SPEC/v1/audit-log.schema.md` | CANÔNICO (deny-Edit) | linha da ação + linha v2.60 (birthtime-only e verify-before-consume documentados) |
| `.claude/data/audit-registry.golden.txt` | livre | regenerado (`# count: 331`) |
| `.claude/hooks/harness-noop-allowlist.txt` | livre (novo) | entrada gate-side do estado off (ADR-160 §7, exigência da spec §3) |
| `.claude/hooks/tests/test_session_end_memory_delta.py` | livre (novo) | 20 testes: §7 da spec + paridade de enums + controles r1/r2 (NFKC, âncora forjada, compact-restart, birthtime, scan incompleto, injeção semântica) |
| `.claude/hooks/tests/test_check_compaction_continuity.py` | livre | +14: US7 (git-fixture, AST escopado, tie-break), válvula (permille derivado), reinjector (título hostil nunca rende; shape path/sha) |
| `.claude/hooks/tests/test_audit_emit_api_contract.py` | livre | pin 331 + SHA re-derivado + símbolo público |
| `test_check_ledger_checkpoint / w5_scrub / codex_egress / plan163 / git_bypass` (5) | livres | pins 330→331 com linhagem completada (o 6º achado pela bateria integral) |
| `.claude/plans/PLAN-179-context-continuity-durable-state.md` | livre | frontmatter `done`+`completed_at`+`related_commits`; US1/US2b-valve/US7/US8 → `[x]`; AC(a) supersedido (r1-C3, ratificação 2026-08-31); registro S335 |
| `.claude/plans/PLAN-179/LEDGER.md` | livre | unidade wave-179close |
| `docs/CONTEXT-CONTINUITY-GUIDE.md` | livre | §2 pointer do ledger; §6 válvula (this-repo trace, no-claim) + delta de memória (a claim «writability only» morreria stale) |

## O que este patch NÃO faz

- Não escreve memória em hook nenhum (US8 é stat-only por contrato).
- Não muda `compaction_*` no wire (`pointer_count` intacto; índice vive no
  blob; títulos nunca chegam ao instruction stream).
- Não toca `scripts/` (ratchet do PLAN-185 não regenera).
- Não fecha AC-2/OQ-2 do 183 nem os FU-ADR-* — decisões do Owner.

## Evidência pré-assinatura (S335, sombra base cfab980)

- 9 suítes declaradas: **304 passed / 0 skipped**.
- Bateria completa hooks+_lib: **7775 passed / 1 flake de perf sob carga**
  (`test_case_a_p99_under_5ms`, verde isolado — classe conhecida).
- Registry: `OK: audit registry in sync`; golden idempotente; controle
  negativo por `--repo-root` derruba com a ação nomeada.
- Rails codex: r1 = 7 achados REAIS curados; r2 = 7 achados REAIS curados
  (2×P1 de injeção, âncora compact-restart + HMAC verify-before-consume,
  no-claim); registros em `rail-round-{1,2}.md`.
- `verify-counts.sh` na sombra: rc 0. ceremony-lint: 0 blockings.
