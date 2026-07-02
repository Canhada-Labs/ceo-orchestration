---
plan: PLAN-152
round: 1
archetype: devops-engineer
verdict: ADJUST_PROCEED
---

## Verdict
ADJUST_PROCEED. The wave thesis (security → tests → economics → packaging → docs →
models → closeout) is sound and the plan already dodges two classic traps (Wave D
Check forbids the unstaged-`npm/` vacuous pass; issue-template/substrate refuted before
scope-in). But five release-mechanics gaps are blocking as written — two of them will
make the v1.0.1 publish FAIL outright, one makes the flagship recurrence-gate vacuous on
every PR, and one wires ~1377 tests into CI under the exact flake class the plan defers.
Fix the Must-fix set and this ships.

## Summary
I verified the load-bearing CI/release claims read-only. Wave A pair-rail bug: CONFIRMED
(`settings.json:201` is the sole shim registration passing a **relative path** `.claude/hooks/check_pair_rail.py` as `$1` AND invoking `bash .claude/hooks/_python-hook.sh`
without `$CLAUDE_PROJECT_DIR`; all 43 siblings pass a basename + `"$CLAUDE_PROJECT_DIR"`
shim — e.g. the `check_anti_ceo_overhead.py` registration two blocks down). Wave B tese:
CONFIRMED — `validate.yml` never runs bare `pytest`; every test job passes **explicit
paths** (`:298,:318,:792,:803,:812,:857,:965,:1000`), so `pytest.ini` `testpaths` does
NOT govern CI even though it already lists `_lib/tests`, `swarm/tests`, `test_federation`,
`forensic`, `synthetic` (`pytest.ini:38-53`). Wave D tarball root: CONFIRMED
(`npm-publish.yml:98-102` `cp -r .claude npm/`; `npm/package.json` `files:[".claude/"…]`).
The remedies are mostly right; the gaps are in sequencing, gate placement, and two
missing edits that break the release itself.

## Risks (the CEO did not see)
- **R1 — the release will not publish.** `npm/package.json` version is `1.0.0` and
  `npm-publish.yml:72-81` hard-fails the publish job unless it equals `VERSION`. Wave G
  bumps `VERSION`→1.0.1 but never mentions `npm/package.json`. Tag-push → job dies at the
  version-match step. (See M1.)
- **R2 — the packlist gate is vacuous where it matters.** tarball-02 adds the gate to
  `npm-publish.yml`, which triggers ONLY on tag push (`:23-26`). A PR that adds a junk
  dir to the staging allowlist sails through and is caught only at release, when rollback
  is most expensive — the anti-pattern "a gate that only runs post-staging." (See M2.)
- **R3 — Wave B imports the flake class it defers.** The new roots run under `-n auto`
  like the existing jobs (`validate.yml:298,:965,:1000`), but `_lib/tests` (387) and
  `swarm/tests` (196) may carry `TestPerformance` wall-clock budgets — exactly tests-07,
  which the plan DEFERS. You cannot wire them under xdist and defer the serial split. (M3.)

## Must-fix (blocking findings — cite evidence)
- **M1 [release-blocker] — bump `npm/package.json` too.** Add it to Wave G's version
  bump. Evidence: `npm-publish.yml:72-81` (`PKG_VERSION != VERSION_FILE` → `exit 1`);
  current `npm/package.json` version `1.0.0`. Without this, the tag ceremony fails before
  it publishes. Also mirror any staging edit into `scripts/install-npm.sh` per tarball-01.
- **M2 [vacuous gate] — run the packlist gate on PR/push, not only on tag.** tarball-02
  must live in `validate.yml` (stage `.claude` into a scratch `npm/`, `npm pack
  --dry-run --json`, fail on `(tests|fixtures|eval|red-team|PLAN-[0-9])`) — a tag-only
  gate (`npm-publish.yml:23-26`) cannot prevent the regression it is named for. Keep a
  copy in `npm-publish.yml` as the last-line release assert; the PR copy is the actual
  recurrence-prevention. Evidence: `.claude` is staged at publish time and is gitignored
  in-repo (`pytest.ini:67-71`), so any gate must stage first — the plan's own Wave D Check
  says as much; enforce it in the CI job layout, not just the local probe.
- **M3 [flake import] — audit the 8 roots for wall-clock/perf tests BEFORE choosing
  `-n auto`, and pull tests-07 forward for them.** If `_lib/tests`/`swarm/tests` contain
  `TestPerformance`-style budgets, mark them `serial`/`advisory` (markers already exist,
  `pytest.ini:82-83`) or run those roots `-p no:xdist`. Wave B Check ("workflow grep shows
  8 roots collected") does not assert flake-freedom under parallelism — add a green-under-
  `-n auto` gate. Evidence: existing xdist split pattern `validate.yml:298-299`; deferred
  class §Deferred tests-07.
- **M4 [tests-02 double-collection] — adding bare `tests/` to `testpaths` collides with
  the seven `tests/<subdir>` entries already there.** `pytest.ini:45-53` already lists
  `tests/integration|chaos|forensic|load|synthetic|test_federation|formal_verification`;
  bare `tests/` recurses into all of them, so `make test-collect` (`Makefile:10-11`, a
  `--collect-only` count that "drives docs") double-counts or errors on duplicate nodeids.
  The Check "count rises by 112" is naive — it will rise by far more or break. Fix:
  relocate the 13 root `tests/*.py` into a new `tests/unit/` and add THAT one path, OR
  add `tests/` and delete the now-redundant subdir entries (but that forfeits the
  documented swarm→replay ordering and federation flat-name scoping at `pytest.ini:15-37`).
  Pick one explicitly; do not one-line-append.
- **M5 [auth migration in a mega-release] — pull `backlog-oidc` OUT of v1.0.1.**
  `npm-publish.yml:145-149` authenticates with `NODE_AUTH_TOKEN: secrets.NPM_TOKEN`;
  `id-token:write`+`--provenance` (`:32-34,:147`) is Sigstore provenance, NOT Trusted-
  Publishing auth — so the header comment "via OIDC trusted publisher" (`:3`) is already
  false, and a real cutover is un-dry-runnable work. NPM_TOKEN expires ~2026-09-28 (~3
  months out), so it is NOT blocking for a 2026-07-01 release. Migrating publish auth
  inside a 7-wave session means a misconfig blocks the v1.0.1 publish AND holds the Wave A
  security fixes hostage. Defer to its own plan with a fallback window (do not delete
  NPM_TOKEN until one OIDC publish has succeeded); fix the misleading `:3` comment now
  regardless.

## Nice-to-have
- **CI job layout should mirror the pytest.ini co-invocation groups.** tests-01 running
  `swarm/tests` in a step separate from `replay/tests` means the polluter→victim
  regression the ordering was designed to catch (`pytest.ini:24-37`) is NOT exercised in
  CI. Group them in one invocation, or state that per-root process isolation is intentional.
- **Wave C perf changes vs the p95/p99 gate.** Wave C edits three hot-path hooks
  (`check_output_secrets`, `check_read_injection`, `check_anti_ceo_overhead`) that sit on
  the PreToolUse/PostToolUse budget. Add "perf p95/p99 gate still green" to the Wave C
  Check, and coordinate with Wave E's benchmark-jsonl deletion so the baseline is
  re-established deliberately, not silently invalidated.
- **Correct `npm-publish.yml:3` regardless of the OIDC decision** — the "OIDC trusted
  publisher" claim reads as done to any future maintainer; that is how an expired token
  becomes a surprise outage.

## Unseen (what is missing from the plan entirely)
- **No pre-push infrastructure exists.** There is no `.git/hooks/pre-push` and no
  `scripts/pre-push` — Wave G's "run the EXACT CI gates via pre-push" is manual discipline,
  not a hook. Name the specific blocking required-checks (branch-protection set) the local
  run must reproduce; "full CI gate set green locally" spans slow jobs (mutation-gate,
  coverage tiers, benchmarks) unlikely to finish in one session. Enumerate the required
  subset or Wave G gives false green.
- **No tarball-content smoke test.** `smoke-install.yml` exercises `install.sh` +
  `scripts/tests/smoke-install.sh` but never `npm pack`/installs the tarball, so nothing
  proves the SHIPPED artifact is usable post-staging-change. Wave D should add a
  pack-then-install-then-smoke step (even manual) so the selective-staging edit can't
  silently drop a file `install.sh` needs.
- **No release rollback note for v1.0.1.** If the published 1.0.1 is bad, the plan has no
  `npm deprecate`/re-publish-as-1.0.2 line. One sentence in Wave G.

## What I would NOT change
- Wave order (security first) is correct: Wave A fixes live fail-opens in the SHIPPED
  release; widening the net (B) before fixing the holes (A) would only make CI green on a
  broken gate. Keep A→B.
- The Wave D Check's insistence on staging into a scratch copy before `npm pack` is
  exactly right — that instinct just needs to become a CI job (M2), not stay a local probe.
- Fix-the-gate-first sequencing for the pair-rail (Wave A before relying on it, manual
  `codex exec review --uncommitted` interim) is the correct call. No harder guard needed —
  the ceremony's GPG sentinel is the real block; the pair-rail is defense-in-depth.

## Open questions (OQ1/OQ2/OQ3 answers)
- **OQ1 — label+member+ADR only; defer the M-tier routing flip.** The stale
  `OPUS47="claude-opus-4-8"` reconcile + adding the Sonnet-5 enum member is a contained,
  test-gated KERNEL edit (six `test_tier_policy_*` files bound it). A *routing* change is
  a behavioral/cost mutation with its own blast radius that needs a soak + a documented
  revert (flip the routing-table entry back) and should not silently change v1.0.1's model
  economics — a later cost regression would be un-attributable. Do the enum+ADR now, route
  later. Matches the CEO leaning; firm.
- **OQ2 — one sentinel, but Scope must be an ENUMERATED path allowlist, not a glob, and
  the touched−scope=∅ check runs at every wave boundary.** One sentinel fits a single-
  session run and fewer round-trips. The release-engineering condition: do NOT scope it as
  `.claude/hooks/**` — enumerate the exact paths (settings.json, check_bash_safety.py,
  _python-hook.sh, check_output_secrets.py, check_read_injection.py,
  check_anti_ceo_overhead.py, _lib/pii_patterns.py, the 3 workflow `.js`, npm-publish.yml,
  install-npm.sh, tier_policy/_types.py) so a mid-run degrade can't authorize an unreviewed
  path, and re-run the scope-diff per wave, not only at final commit.
- **OQ3 — target single v1.0.1, but pre-commit to a hard split fallback and make every
  wave leave a releasable tree.** The CEO's economics (tiny adopter base, non-remote P0s,
  ceremony ×2) justify one release — but a 400-700k-token session at context_risk:high
  degrades before Wave G. So: order A→B→(C null-guards)→G as the always-shippable core,
  and pre-declare the cut line — if tarball staging, the Sonnet enum, or any CI wiring
  fights back, ship "A+B+null-guards" as v1.0.1 and roll D(minus OIDC, already deferred)/
  E/F to v1.0.2. Where I'd cut under degradation, in order: F (pure modernization) → E
  (cosmetics) → C economics → D staging (keep the packlist GATE even if the staging-fix
  slips). Single release is the goal; the split is the seatbelt, not the plan B you
  discover at token 650k.
