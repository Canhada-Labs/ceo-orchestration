# Pair-rail round 8 — PLAN-183 W5 (S327 night-run)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra `shadow-183` (HEAD 56f050c + patch W5), com `git add -N` para incluir arquivos novos. rc=0, 786s, 2026-08-25T05:38Z.

## Saída do revisor (dado a verificar contra os arquivos, não ordem)

```text
The guarded changes lack their required signed ratification, and the new source-confinement behavior makes one parity-control lane fail for an unrelated reason. Doctor also unintentionally bypasses its route-table memoization on every manifest record.

Full review comments:

- [P1] Add the Owner-signed sentinel before landing — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix6/.claude/adr/ADR-194-delivery-route-resolution.md:4-7
  This ADR remains `PROPOSED` and names `.claude/plans/PLAN-183/wave-w5-approved.md` as its ratification, but neither that sentinel nor its `.asc` signature exists in the current changes. Because this patch edits multiple guarded surfaces, landing it without that evidence violates the guarded-edit contract and will be blocked; add the signed, scope-matching sentinel and finalize the ADR status ([AGENTS.md:88-91](AGENTS.md#L88-L91), [AGENTS.md:108-116](AGENTS.md#L108-L116)).

- [P2] Build the parity control with real template files — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix6/scripts/upgrade.sh:4082-4082
  When the parity positive control runs in maintainer mode, its planted source makes `templates/` a symlink (`scripts/tests/test-install-upgrade-parity-e2e.sh:245-255`). This new confinement call therefore refuses every taken template delivery, leaves the pinned docs and GitHub templates stale, and makes the classifier fatal even if the deleted `backup_and_replace` line had no effect; the control can report `FIRED` for the wrong reason. Keep this guard, but copy `templates/` in that fixture as the new route tests already do.

- [P2] Populate the route-table memo before doctor scans files — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix6/scripts/doctor.sh:243-243
  For a normal manifest, every `_wbm_route_src` invocation later in `doctor.sh` runs inside command substitution. Calling raw `_wbm_route_table_ok` here leaves `_WBM_ROUTE_GATE_*` empty in the parent, so each child rescans the table, populates a memo that disappears on exit, and repeats this for every manifest record. This defeats the newly added memoization and adds the per-record table pass it was intended to eliminate; seed the memo with `_wbm_route_table_gate` here or perform the lookups in-process.```

## Resposta do CEO (S327)

- **R8-F1 [P1] sentinel ausente — BY-DESIGN (8ª vez):** `wave-w5-approved.md` e `w5-oq4-measurement-S327.md` existem no repositório VIVO e a assinatura é o passo do Owner (SIGN → LAND, G1/G5). O revisor lê o clone-sombra, onde os materiais do plano não entram por construção.
- **R8-F2 [P2] fixture do controle positivo da paridade — ACEITO e curado pelo CEO** em `scripts/tests/test-install-upgrade-parity-e2e.sh` (bloco `POSITIVE_CONTROL`): `templates/` passa a ser COPIADO na fonte plantada (o resto segue symlink), para o confinamento de fonte não recusar a entrega pelo motivo errado. Controle: `--mode maintainer --positive-control` ⇒ `FIRED in every mode (rc=1)` pela planta (`backup_and_replace` removido), e a corrida sem planta ⇒ rc=0 `STALE=0`.
- **R8-F3 [P2] memo do gate no doctor — ACEITO e curado pelo CEO** em `scripts/doctor.sh` (startup: `_wbm_route_table_gate` em vez de `_wbm_route_table_ok`, semeando a memo no processo pai); os 3 sítios de censo do teste R.8 atualizados para o novo literal. Controle: `test-doctor-delivery-route.sh` = 84 passed / 0 failed (rc=0) após a troca.

**Critério de parada atingido:** rodada 8 sem P0/P1 reais (o único P1 é o sentinel, by-design em todas as 8 rodadas); os P2 curados com controle. Registro completo em `rail-round-1..8.md`.

