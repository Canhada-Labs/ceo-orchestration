# Pacote E — rail codex rodada 1 (shadow-E, 2026-08-26T20:16:12Z)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E (base b07be9b + diff U3)
Achados: 0 P1, 3 P2 (curas despachadas ao agente u3-upgrade-hooks-derived-writer por SendMessage 17:35)

Full review comments:

- [P2] Preserve explicit falsy hook containers — scripts/upgrade.sh:2600-2608
  When an adopter has explicit `"hooks": null` or an event value of `null`/`false`, these branches classify it as absent (`== null` and `// []`) and replace it with template arrays. This contradicts the stated behavior of preserving and naming non-object/non-array structures; distinguish missing keys with `has(...)` before applying defaults.

- [P2] Wire the lifecycle-hook end-to-end test into CI — .claude/plans/PLAN-169/s329-ceremony-E/DESIGN-E.md:176-180
  The new end-to-end test is not referenced by any workflow: `smoke-install.yml` has no execution step for it and neither path list includes the shell file, so E.1–E.9 never run in CI. The repository explicitly documents that these tests run only there and that “unwired = no test” ([smoke-install.yml:30-34](.github/workflows/smoke-install.yml#L30-L34)); add the invocation and path filters in this patch.

- [P2] Count duplicates before collapsing registration keys — scripts/tests/test-upgrade-lifecycle-hooks-derived.sh:297-300
  If the merge appends a duplicate registration, E.2h still succeeds because `_keyset` has already emitted `sorted(set(out))` at line 132; `uniq -d` therefore receives an already deduplicated file and is always empty. Use a multiplicity-preserving key stream for this assertion; the Python unit test's `_keyset`-based duplicate count has the same blind spot.
The merge can overwrite explicit non-array hook structures despite its preservation contract. Its new end-to-end coverage is also CI-dark, and one duplicate-detection assertion is vacuous.

