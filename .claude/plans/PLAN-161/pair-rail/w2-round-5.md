# PLAN-161 W2 pack — codex pair-rail round 5 (2026-07-27)

## Verdict

REJECT

1. **[P1] F2 still false-greens an older terminal for the same file.** Every `pair_rail_case` unconditionally adds terminal credit before aggregate bucket comparison. An old Case A for `(session S, file X)` followed by a dead expected review for the same bucket yields `expected=1, terminal=1`; with a healthy Stop rail, the overall verdict is GREEN. Terminals must consume only an already-outstanding expectation, or carry an invocation ID. `.claude/plans/PLAN-161/staged/.claude/scripts/ceo-boot.py:1923`, `:1932`, `:1965`.

2. **[P2] F9 is only partially fixed.** The tests use `mock.patch.dict`, but remain free pytest functions without `TestEnvContext`, leaving real `HOME`/`CLAUDE_PROJECT_DIR`, inherited `CEO_*`, and `sys.path` unisolated. This still violates the mandatory contract. `.claude/plans/PLAN-161/staged/.claude/hooks/tests/test_codex_review_user_code.py:15`, `:28`, `:216`; `AGENTS.md:24`.

3. **[P2] The claimed U3 ancestor-symlink red-first probe is absent.** The checked-in E.3 oracle seeds only a symlink leaf inside an ordinary excluded tree. It never makes `.claude/hooks` an ancestor symlink, places an external empty subdirectory behind it, and triggers an unrelated authorized purge so the `rmdir` sweep executes. Thus the Round 4 regression is not load-bearing in CI. `scripts/tests/test-upgrade-exclusions.sh:271`, `:342`.
## CEO triage — 3 findings (F12/F13/F14/F3/U3-code confirmed fixed across rounds):
- F2 [P1] 5th refinement — the terminal fix: move from COUNTING to per-INVOCATION correlation ID. check_pair_rail generates review_id=os.urandom(8).hex(), emits it in BOTH review_expected and pair_rail_case; classifier pairs by review_id (an expected id with no matching case = outstanding dead review = deficit). Count fallback only for id-less legacy events. This is what codex flagged as the right approach in r4.
- F9 [P2] mock.patch.dict alone leaves HOME/CLAUDE_PROJECT_DIR/sys.path unisolated -> wrap in TestEnvContext (AGENTS.md mandate).
- U3 [P2] the r4 ancestor-symlink purge probe was scratchpad-only -> fold as E.3d into the tracked test-upgrade-exclusions.sh (RED on HEAD).
