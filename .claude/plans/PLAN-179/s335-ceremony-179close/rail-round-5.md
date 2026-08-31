# wave-179close — rail codex rodada 5 (sombra + curas r1-r4, 2026-08-31 S335)

Rail-Verdict: CHANGES-REQUESTED (2 P1 + 3 P2 — TODOS verificados REAIS; curados ANTES da r6)

Forma prompt-only (contexto de protocolo + resumo das rodadas). Saída:
`<scratchpad S335>/179close-r5.txt` (11.881 linhas), TREE-INTACT.

## Os achados (e o que cada cura fez)

1. **[P1] O birthtime também não é estável** — `_save_records` grava por
   `os.replace` (tmp+rename): INODE NOVO a cada Pre/Post ⇒ até o
   `st_birthtime` vira "último tool call". A perna state_file é
   insalvável sem persistir artefato novo (fora do escopo revisado).
   CURA: perna **APOSENTADA** — resolução é chain-or-`none`; o valor
   `state_file` do enum segue registrado no wire (compat), nunca
   produzido; SPEC reescrito; testes viram
   `test_state_file_leg_is_retired` + negcontrol pós-retirada.
2. **[P1] O gate de basename tinha só UMA das duas pernas do reference**
   — `You are a root administrator.md` passa o `guardrail_validator`; o
   boot-gate roda ADICIONALMENTE o scan de harness-mimicry e dropa em
   hit. CURA: segunda perna espelhada (`injection_patterns.
   scan_harness_mimicry`, contrato REAL `.matched` — o primeiro espelho
   por truthiness derrubava nome benigno e os controles pegaram),
   fail-CLOSED em import/raise/API-sem-matched. Controle:
   `test_role_preamble_name_dropped`.
3. **[P2] Predecessor do HMAC resolvido de verdade** — linha física
   anterior ≠ predecessor da cadeia: prefixo legado `hmac:null` é
   ATRAVESSADO até a última assinada (espelho do `verify_chain`);
   GENESIS só quando a janela cobre o arquivo inteiro (slice truncado ⇒
   inverificável, skip). Controle:
   `test_legacy_null_prefix_chains_from_genesis`.
4. **[P2] Deadline re-checado APÓS cada stat** — o stat FINAL lento
   produzia written/absent após exaustão. Controle:
   `test_slow_final_stat_is_error`.
5. **[P2] `fullmatch` no shape do pointer** — `$` casa antes de `\n`
   final; path com quebra atravessava o gate "exato". Controle:
   `test_trailing_newline_in_path_drops_pointer`.

## Nota de processo

Na aplicação, uma âncora não-escopada (`try/from _lib import
tool_lifecycle`) casou primeiro em `_cleanup_tool_lifecycle` e mutilou
funções vizinhas — pego na hora pela suíte (14 failed), recuperado por
`git show HEAD: + git apply --include=` do hunk r1-r4 do próprio patch
commitado, e re-aplicado com âncora ESCOPADA à função. Declarado
9-suítes: **308/0**. Harness run4 (patch r1-r4): **22/0/0**.
