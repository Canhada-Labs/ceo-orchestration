The proposed provenance route invalidates the reviewed-parent trust boundary, and the release-scope change already breaks an existing regression test. The release notes and advisory evidence are also incomplete.

Full review comments:

- [P0] Re-run the rc.4 review instead of moving its parent — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-177/repass-rc4-advisory-preparent/NOTA.md:13-18
  The proposed commit X contains `release.sh`, `CHANGELOG.md`, runner, and evidence changes that the t6 re-pass did not review. Changing `parent_sha` from `5af2cd7` to X while preserving the old transcript and input hashes makes the delta guard start after those changes and falsely treat them as reviewed; this is the exact main-advanced bypass the reviewed-parent invariant prevents. Re-run the re-pass against X and regenerate all bound verdict evidence instead.

- [P1] Update the exact release-scope regression — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/local/release.sh:79-79
  Changing `RELEASE_SCOPE` leaves `test_tag_annotation_carries_the_whole_train_and_no_stale_release` expecting the old `PLAN-169 W0-W2 (ADRs 184 -> 190)` string. Running `test_release_bump_sites.py` now fails with 1 failed / 145 passed, so CI remains red until the exact expected live scope is updated without weakening the assertion.

- [P1] Document the other shipped PLAN-178 behavior — /Users/joaocanhada/canhada-labs/ceo-orchestration/CHANGELOG.md:20-23
  The rc.4 candidate also contains PLAN-178 W1.2's user-visible native usage cross-check for `/agent-budget` (`451b659`) and Lote A's `ceo-boot` behavior (`0149c6c`), but the revised summary and sole PLAN-178 section describe only spawn acceptance contract v2. Users following the signed release pointer therefore receive incomplete notes despite this changelog's stated contract to record user-visible command and hook behavior.

- [P2] Add the advisory round claimed by the note — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-177/repass-rc4-advisory-preparent/NOTA.md:44-45
  The note states that `codex-advisory-r2.md` reviewed the changelog cure, but that file is absent from the untracked directory. Committing this state would leave the provenance claiming a review artifact that does not exist, with no verdict covering the newly added changelog content.