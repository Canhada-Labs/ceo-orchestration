# Flake test_waive_scoped_to_changed_paths — rail codex rodada 1 sobre 9af6114 (2026-08-26T20:50:52Z)

Rail-Verdict: REJECT (2 P1 no teste de regressão; curados pelo CEO no commit seguinte)

Full review comments:

- [P1] Avoid requiring full history in the live-repo test — .claude/scripts/tests/test_persona_demand_scan_window.py:325-326
  The validate and coverage jobs use the default depth-1 `actions/checkout` (`.github/workflows/validate.yml:48` and `.github/workflows/coverage.yml:41`) and both collect this test. Such a checkout exposes at most one commit—or zero here when the fetched PR head is a merge because of `--no-merges`—so requiring more than one makes CI fail even when `_since_arg` is correct. Use a temporary repository with controlled history or account for shallow checkouts.

- [P1] Make the 2h mechanism test date-independent — .claude/scripts/tests/test_persona_demand_scan_window.py:162-165
  During roughly the first five days of each month, the three-day-old commit lies before day 2 of the current month, while Git resolves `--since=2h` to that month's day 2; `subjects` is therefore empty and this assertion fails. Freeze Git's notion of the current time and choose fixture timestamps relative to that fixed date instead of relying on the wall calendar.
The runtime cutoff change is sound, but the newly added regression suite is not CI-safe. One test fails in the repository's depth-1 CI checkouts, and another fails periodically based on the calendar date.


## Curas (CEO, S329)

- P1 depth-1: `TestLiveRepoHorizon` (git log sobre o checkout vivo, exigia >1 commit) substituído por `TestControlledHistoryHorizon` (repo temporário com 3 commits de idades conhecidas + controle positivo do colapso). Provado em clone `--depth 1` (1 commit visível): 12 passed.
- P1 calendário: `test_bare_2h_is_read_as_a_day_of_month` pina a data das fixtures E o relógio do git (`GIT_TEST_DATE_NOW`, o gancho que o approxidate lê em vez de gettimeofday) no dia 15 do mês — vale em qualquer dia; `test_pinned_clock_is_honoured_by_git` é o self-check do pin (ano 2000 ⇒ tudo listado; sem pin ⇒ nada).

## Rodada 2 sobre d1817bc (2026-08-26T21:00:29Z)

Rail-Verdict: APPROVE

