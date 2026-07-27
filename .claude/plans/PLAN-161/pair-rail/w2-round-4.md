# PLAN-161 W2 pack — codex pair-rail round 4 (2026-07-27)

## Verdict

REJECT

1. **[P1] F2 still permits a false-green missing outcome.** All `pair_rail_case` events become terminal credits regardless of whether they follow an expected marker. An older/pre-land Case A in session S can therefore offset a later `pair_rail_review_expected` whose hook dies before emitting its case: aggregate counts are 1:1, no deficit is detected, and the healthy case makes the row green. Terminal events must only consume an already-outstanding expectation, or use an invocation correlation ID. `.claude/plans/PLAN-161/staged/.claude/scripts/ceo-boot.py:1901`, `:1928`.

2. **[P1] U3 cleanup can traverse an ancestor symlink and remove directories outside the target.** The cleanup checks only whether the nominated tree leaf is a symlink. With an ancestor such as `.claude/hooks` preserved via `--skip`, `find "$TARGET/.claude/hooks/tests"` resolves through it. If an authorized purge in any other tree makes the global purge count positive, the subsequent `rmdir` pass can remove empty directories in the external symlink target. This violates the documented no-follow contract. `.claude/plans/PLAN-161/staged/scripts/upgrade.sh:1685`, `:1689`, `:1692`.

3. **[P2] The claimed F3 executable injection regression test is absent.** Scenario K only compares the rendered `N=` line to an expected string and checks that raw interpolation is absent. It never runs `bash -n`, executes the rendered shell block, or asserts that the injected command did not run, contrary to the Round 3 disposition. `.claude/plans/PLAN-161/staged/scripts/tests/test-council-fixture.mjs:431`, `:435`, `:442`.

4. **[P2] New hook tests violate the mandatory environment-isolation contract.** They mutate process environment through `monkeypatch.setenv` without `TestEnvContext` and `mock.patch.dict`, including the auto-review and session fallback cases. AGENTS.md requires that exact isolation pattern for hook tests. `.claude/plans/PLAN-161/staged/.claude/hooks/tests/test_codex_review_user_code.py:140`, `:154`, `:164`, `:188`, `:294`; `AGENTS.md:24`.
## CEO triage — all 4 ACCEPTED (fix-round-4):
- F2 [P1] 4th refinement: aggregate per-session count pairing lets an OLD completed case offset a NEW dead review. Fix: correlate deficit per (session, file_path_hash_prefix) bucket — different-file buckets no longer cross-mask. Adds file_path_hash to pair_rail_review_expected (schema+golden re-cut, count stays 321).
- F2/U3 [P1] ancestor-symlink traversal in the U3 purge scan/rmdir (same class as r3 F11a, different code path). Fix: per-component symlink check from TARGET to leaf; skip any tree with a symlinked ancestor.
- F3 [P2] scenario K only string-compares. Fix: real bash -n + execute + marker-absence + shq-bypass counter-proof.
- F9 [P2] env-hygiene: convert new hook-test env mutations to mock.patch.dict (AGENTS.md convention) — removes the re-raised objection.
