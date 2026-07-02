---
plan: PLAN-152
round: 1
archetype: qa-architect
verdict: ADJUST_PROCEED
---

## Verdict
ADJUST_PROCEED. The plan is directionally sound, unusually well-verified, and
correctly refuses the two refuted findings. But Wave B — the test-safety-net
wave — carries four coupled test-strategy gaps that turn "CI green" into a claim
the plan cannot actually make. None are fatal; all are fixable at consensus.

## Summary
Wave B wires ~1377 never-run tests + a 183-site env-hygiene mass-edit in one
wave, gated by grep-for-presence Check lines. That is the exact finish-fullsuite
flake-class exposure the framework already has a lesson about. The `serial`
two-pass split (validate.yml:298-299) already exists and is the established CI
pattern, which makes the tests-07 deferral and the new-root flake exposure
cheaper to fix than the plan assumes — but also makes the omission of a serial
pass for the new roots a live defect, not a nicety.

## Risks (the CEO did not see)

- **R1 — "Green that lies" from the env-hygiene burn-down.** Mechanically
  wrapping 183 sites in `TestEnvContext` can neuter assertions: a test that
  relied on inheriting a real env var now runs isolated and its assertion goes
  vacuous while still passing. `check-test-env-hygiene.py` exiting 0 proves the
  scanner is satisfied (line 441 iterates roots), NOT that the migrated tests
  still test their behavior. A root-batched burn-down has no per-class review.
- **R2 — swarm→replay sequential-pollution ordering is reproduced by NO CI job.**
  `pytest.ini` documents the S228 polluter→victim guard and states swarm/tests
  is listed "BEFORE replay/tests so the ordering is exercised on every run" —
  but that is a *testpaths-ordering* artifact, and CI never runs bare pytest.
  release.yml:263 runs `replay/tests` in isolation; a new Wave-B job for
  swarm/tests in isolation means the documented regression repro runs nowhere.
- **R3 — 1377 tests wired under `-n auto` with zero serial markers.** All 8 dark
  roots have no `@pytest.mark.serial` (markers exist only in the already-wired
  `hooks/tests`/`scripts/tests`). Any timing/concurrency/shared-state test in
  the new roots flakes under xdist on first wiring, and the Check line
  (grep-the-workflow) will not catch it.

## Must-fix (blocking findings — cite evidence)

1. **Root `tests/` stays CI-dark after both items.** tests-02 edits only
   `pytest.ini` (Check: "collect-only count rises by 112" — a *local* number).
   tests-01's workflow root list is the 8 roots — it does NOT name bare `tests/`
   (plan line 91). CI never runs bare pytest (validate.yml always passes explicit
   paths: :298, :318, :1000). So the 3 security files that exist directly in
   `tests/` — `tests/test_codex_redact_fail_closed.py`,
   `tests/test_mcp_bearer_nonce_replay.py`, `tests/test_output_scan_llm03.py`
   (all confirmed present) — become locally-collectable but remain CI-dark. This
   fails Success-criterion "the 3 security root-tests collect + pass in CI"
   (plan line 210). FIX: tests-01's CI job must also run `tests/` root (or the
   plan must state the new job is bare-pytest/testpaths-driven — see Must-fix 4).

2. **tests-01 Check is a presence check, not an outcome check.** "workflow grep
   shows all 8 roots collected in CI" (plan line 91) proves the yaml string, not
   that the roots collect AND pass. With ~1377 first-time-run tests the base rate
   of an all-green first wiring is low. FIX: Check must be "the new job collects
   the expected count AND is green across ≥2 consecutive runs, with a quarantine
   lane for any root that flakes so it does not block the release tag."

3. **Fail-closed flips lack negative controls (discriminating-assertion gap).**
   error-handling-01 (`check_bash_safety.py` fail-CLOSED on `shlex.ValueError`,
   Check: `rm -rf ~ ";"` → block, plan line 82) and security-01 (cache symlink
   reject, Check: "symlinked/foreign-owned path rejected", plan line 83) each
   assert only the POSITIVE. Neither asserts the NEGATIVE: a benign unparseable
   command is not catastrophically over-blocked / a legitimate cache path is
   still accepted. Without the paired negative you cannot distinguish a correct
   fix from an over-block that bricks a legit session — precisely the CLAUDE.md
   §4 fail-open-doctrine tension the proposal raises as decision #5. FIX: every
   fail-open→fail-closed flip lands with a positive AND a negative test.

4. **New CI-job invocation style is unspecified, and it decides three things.**
   The plan never says whether the Wave-B job runs bare `pytest` (testpaths) or
   explicit paths. That single choice determines: (a) whether root `tests/` runs
   (Must-fix 1), (b) whether the two-pass `not serial`/`serial` split is applied
   to the new roots (R3), (c) whether swarm→replay ordering is preserved (R2).
   FIX: state it explicitly. If explicit-paths: replicate the two-pass split for
   the new roots and co-locate `replay/tests` after `swarm/tests`. If bare-pytest:
   note it double-collects the already-run roots and pulls heavy `tests/load` +
   `tests/chaos` into default collection.

## Nice-to-have

- **Pull tests-07 into Wave B (it is cheap now).** The deferral rationale
  ("add a serial marker in a CI hardening pass") is stale: the serial two-pass is
  already the CI pattern (validate.yml:299), so marking the offending
  `TestPerformance` is one line and immediately routes it to the serial pass.
  Deferring keeps a known microbench-under-load flake live. Fold it in, and add a
  Wave-B step: "audit the 8 new roots for timing/concurrency tests; mark them
  `serial` before wiring."
- **Batch the env-hygiene burn-down by violation-class, not by root.** One
  reviewed transform per class (`os.environ[...]=` → `TestEnvContext` subclass +
  `mock.patch.dict`, the documented canonical form) + a mutation spot-check that
  a sample migrated test still FAILS when its under-test behavior is broken.

## Unseen (missing from the plan entirely)

- No flake-soak / quarantine policy for first-time-wired roots — so one flaky
  root blocks the whole v1.0.1 tag at Wave G with no escape lane.
- No semantic-preservation check on the 183-site migration (R1) — the plan
  measures the scanner, never the tests' discriminating power.
- No CI wall-clock budget note: +1377 tests changes job duration; if any job
  carries a timeout this is unaddressed.
- tests-02 adds bare `tests/` to testpaths while the subdirs
  (`tests/integration`, `tests/chaos`, `tests/load`, `tests/forensic`,
  `tests/synthetic`, `tests/test_federation`, `tests/formal_verification`) are
  already listed — the entries become redundant; prefer replacing them with bare
  `tests/` to keep one source of truth.

## What I would NOT change

- The two refutations (tests-06 xfail-never-runs; dead-code-05 trading escape
  hatch) are correct — do not re-flag.
- Correctly omitting `replay/tests`, `tests/chaos`, `tests/load` from the dark
  list: release.yml:263 + chaos.yml:78/87 cover them. (R2 is about *ordering*,
  not re-adding replay.)
- tarball-01's "run the staging loop FIRST" Check (plan line 107) correctly
  pre-empts the vacuous-pass trap — good instinct, keep it verbatim.
- The `serial` two-pass architecture itself is sound; extend it, do not replace.

## Open questions (OQ1/OQ2/OQ3 answers)

- **OQ1 — label+member+ADR now, routing flip deferred: AGREE, with one test
  guard.** Adding a `MODEL_ID` member + reconciling the stale
  `OPUS47="claude-opus-4-8"` label is a closed-enum KERNEL edit whose blast
  radius is the 6 `test_tier_policy_*` suites — low if the member only widens the
  set. The routing flip is a behavioral/cost change that needs its own eval+soak.
  QA add: the enum edit must ship with a regression test pinning *current*
  M-tier routing UNCHANGED, so reconciling the stale label cannot silently
  repoint a route. Member now; routing later.

- **OQ2 — one PLAN-152 sentinel, but only if the scope-diff gate is a hard,
  tested gate.** From a verifiability lens, one sentinel with an enumerated Scope
  + a `touched−scope=∅` check is the testable invariant; per-wave sentinels
  multiply the surface where the Scope can be authored wrong. The hazard is that
  one broad Scope is a wide standing authorization across a `context_risk: high`
  single session — if the operator degrades, out-of-scope edits slip. So: one
  sentinel is fine *iff* the touched−scope check is run mechanically (not
  eyeballed) and is itself exercised by a dry-run that deliberately touches an
  out-of-scope path and asserts a block.

- **OQ3 — I lean SPLIT (A as v1.0.1, C–F as v1.0.2), against the CEO's lean —
  because Wave B is the flake magnet and should not gate the security release.**
  Wave A is small, surgical, and independently shippable; Wave B introduces the
  entire 1377-test + 183-edit flake/"green-that-lies" risk surface. In the single
  run the tag happens at Wave G, *after* B — so if B stalls, the shipped-broken
  P0 security fixes sit on main un-released. Splitting decouples the security
  RELEASE from the test-hardening risk. If the Owner keeps it single, at minimum
  promote the plan's "split as mid-run fallback" to a firm rule: **tag v1.0.1
  after Wave A is green; Wave B may not block that tag.** (Per PROTOCOL §Debate
  rule 2, flagging this as a convergence candidate.)
