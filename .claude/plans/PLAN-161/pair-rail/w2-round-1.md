# PLAN-161 W2 pack — codex pair-rail round 1 (2026-07-27)

Input: redacted brief + 37-file HEAD->staged diff (3128 lines) via codex exec --sandbox read-only.

## Verdict

REJECT

1. F1 [P1] .claude/scripts/ceo-boot.py:1888: The new zero-expected/zero-outcome branch marks `pair_rail` green even though the denominator is emitted by the rail being measured. A disabled/crashed hook or failed audit emission produces neither marker nor outcome and is therefore indistinguishable from inactivity; with a healthy `stop_review` event, the overall check can green a dead pair-rail. This weakens HEAD’s “silence is yellow” guard.

2. F2 [P1] .claude/scripts/ceo-boot.py:1870: Session correlation checks only whether a session has zero outcomes, not whether every expected invocation has a corresponding later outcome. One earlier healthy outcome masks any number of subsequent expected-but-dead invocations in the same session; `healthy > 0` then makes the row green. The denominator therefore does not detect partial rail death.

3. F3 [P1] .claude/workflows/council-audit.js:119: `artifact_sha256` is optional, accepts any string, and is ignored when deciding lane availability. A Grok result with no or malformed attestation remains `status:"ok"`, counts toward three-lane quorum, and can produce `CLEAN` at lines 478-480, so the claimed artifact attestation is not mechanically enforced.

4. F4 [P1] .claude/workflows/council-audit.js:249: The fixture-only `ARTIFACT_KEEP_DIR` hook is active in live runs without a fixture-mode guard. An inherited value can point into the repo or any writable directory; the block chmods that directory, deletes its existing `brief.tmp`/`brief.txt`, writes the brief there, and leaves `brief.txt` behind because the EXIT trap still cleans only the original `TDIR`. This violates read-only containment, “never the repo tree,” and the claim that only SIGKILL can strand artifact bytes.

5. F5 [P2] scripts/upgrade.sh:690: The sanitized manifest tempfile is assumed to be outside the target but is created under caller-controlled `TMPDIR`. If `TMPDIR` equals or lies beneath the target, `--dry-run` performs a target write—and a crash can leave it behind—despite the absolute write-nothing contract.

6. F6 [P2] scripts/upgrade.sh:1490: The purge path’s `mkdir -p` and subsequent `rm -f` at line 1495 are unguarded under global `set -e`. Permission errors, immutable files, or a race changing the candidate shape abort the whole upgrade, contradicting the documented advisory/fail-open guarantee that the scan never changes upgrade exit status.

7. F7 [P2] scripts/install.sh:1004: The shared exclusion predicate is applied only to each top-level `_lib` entry. A permitted directory such as `_lib/adapters` is then copied wholesale by `install_one`, including nested `__pycache__` directories or `*.pyc` files that `_framework_path_excluded` declares globally excluded. Fresh install, upgrade pruning, and manifest enumeration therefore still have divergent sets.

8. F8 [P2] .github/workflows/validate.yml:1301: The contention parser coerces arbitrary values with `float()` instead of validating a finite, non-negative JSON number. Schema-malformed values such as `true`, `"-1"`, or `"-Infinity"` become `<= 200` and authorize the third attempt; a passing third attempt can green the job despite a malformed probe, violating the fail-safe malformed-output contract.

9. F9 [P2] .claude/hooks/tests/test_codex_review_user_code.py:140: The newly added environment-sensitive tests use `monkeypatch.setenv` repeatedly and do not use `TestEnvContext` plus `mock.patch.dict`, violating the repository’s mandatory environment-isolation rule for tests.

10. F10 [P2] .claude/hooks/codex_review_user_code.py:228: Telemetry dedupe state is consumed immediately after calling the typed emitter, but `audit_emit._write_event` deliberately swallows write failures and returns no success indication. A dropped event is therefore recorded locally as emitted, and later retries of the same `(diff_sha256, outcome)` are permanently suppressed, reopening the C5 liveness signal gap.

## CEO triage (S279)

- F1 [P1] DISPUTED->REBUTTED: the pair_rail vacuous-green (zero expected +
  zero outcomes) is the PLAN-RATIFIED activity-conditioning semantics; the
  "signal only as trustworthy as the rail it observes" residual is recorded
  in PLAN-161 Clarifications (b) (debate round-1 consensus, accepted, "noted
  not fixed here"). No change; comment cites the clarification.
- F2 [P1] ACCEPTED (refined): per-session COUNT-DEFICIT pairing; terminal
  set = pair_rail_case + pair_rail_codex_unavailable (outage is accounted,
  not rail-death). Fixed in staged ceo-boot.py + liveness tests.
- F3 [P1] ACCEPTED: grok lane ok without 64-hex artifact_sha256 is DEMOTED
  to unavailable before quorum/verdict. Fixed in staged council-audit.js +
  demotion test.
- F4 [P1] ACCEPTED: ARTIFACT_KEEP_DIR removed from the live compose snippet
  (fixture never needed it).
- F5 [P2] ACCEPTED: TMPDIR-under-TARGET guard with /tmp fallback.
- F6 [P2] ACCEPTED: purge backup/delete per-candidate fail-open guards.
- F7 [P2] ACCEPTED: nested __pycache__/*.pyc prune after permitted _lib
  subdir copies in install.sh.
- F8 [P2] ACCEPTED: probe parser requires real finite non-negative number
  (bool excluded); proof matrix extended to 11 cases.
- F9 [P2] VERIFY-FIRST: run the repo env-hygiene gate on the staged tests;
  fix only if flagged (pre-existing file already used pytest monkeypatch).
- F10 [P2] REBUTTED-WITH-DOC: audit_emit._write_event exposes no success
  signal by kernel design (LLM06 fail-open); a dropped event suppresses only
  that (diff, outcome) pair. Residual documented at the dedupe consume site.
