---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: DevOps Engineer (Principal)
generated_at: 2026-08-06T23:55:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- The two-oracle split (unit function + slow e2e) is the correct CI architecture.
  The proposal names it but does not wire it: the per-PR gate is unspecified,
  the new harness is absent from the path filter list, and the TSV is also
  absent. Every PR touching only these files skips the gate. That is the same
  unwired-test class as r10-F4, re-instantiated on the new surface.
- The harness requires git archive v1.2.0 (line 347) to exercise legacy_pristine
  rows. smoke-install.yml uses fetch-depth: 1 and only fetches the parity pin
  tag. Both legacy_pristine rows in the TSV (verified: 2 rows) produce
  HARNESS-ERR in CI today, not a real test result.
- The 61-row e2e at ~25 min would consume the entire remaining budget of the
  25-minute-capped smoke-install job (raised four times: 5->8->20->25 min).
  Without splitting the slow test into a nightly job, a fifth bump trades one
  convergence failure mode (11 rounds, no result) for another (timeout).

## Risks

- **R-DO1** SEVERITY: HIGH -- Path filter gap for new artifacts.
  scripts/tests/test-ownership-table.sh, scripts/tests/ownership_table.tsv,
  and docs/ownership-decision-table.md are absent from both pull_request and
  push path filter lists in .github/workflows/smoke-install.yml. A PR that
  ONLY modifies the TSV or harness does not trigger the gate. Impact: the table
  can drift from the callers it models with zero CI signal -- the exact failure
  mode the table was built to prevent.

- **R-DO2** SEVERITY: HIGH -- git archive v1.2.0 tag unavailable in CI.
  test-ownership-table.sh:347 calls: git -C REPO_ROOT archive v1.2.0 SPEC/v1
  The smoke-install job checks out with fetch-depth: 1 and fetches only the
  parity-e2e pin tag (smoke-install.yml:110-115). The v1.2.0 tag is absent.
  Both legacy_pristine rows (grep -c returns 2) emit return 1 inside
  _mutate_surface, increment ERR, and cause the harness to exit 2.
  They produce no test verdict; the suite reports a harness error.

- **R-DO3** SEVERITY: HIGH -- e2e budget exhausts the 25-minute CI ceiling.
  61 rows x CELL_TIMEOUT=60s gives a worst-case ~61 minutes. The proposal
  measures ~25 min in the non-TIMEOUT case -- which is the full remaining
  budget of the smoke-install job (last measured ~20-25 min per lines 83-93).
  Adding the full table run to this job almost certainly causes timeout on PRs
  touching scripts/_framework_manifest_set.sh (which is in the filter). The
  proposal names the unit/e2e split as mitigation but does not specify: what
  file holds the unit test, which CI step runs it, what path filter wires it,
  or whether the e2e is nightly-only or per-PR. Without that specification,
  the per-PR gate covers zero cells of the 61-row space.

- **R-DO4** SEVERITY: MEDIUM -- Section 5.7 FIFO hang has no documented
  operational recovery path. The proposal records the hang as recorded-not-patched
  per rule 2. From an ops standpoint: an adopter with a FIFO anywhere in their
  target tree will have upgrade.sh hang indefinitely. At that point: BAK_DIR
  has been created (upgrade.sh:799-801), the baseline manifest tempfile exists,
  but NO surface has been modified. The run is stalled with a partially-
  initialized work area. There is no documented recovery procedure in INSTALL.md
  and no timeout on _emit_deprecation_warnings.

- **R-DO5** SEVERITY: MEDIUM -- No W2 rollback story documented.
  W2 removes decision branches from install.sh and upgrade.sh. The root VERSION
  file is deliberately never refreshed (ADR-155-AMEND-1 sec 2), and
  .claude/.framework-version is one of the surfaces being refactored. An
  adopter on a bad W2 build may not be able to reliably determine their
  installed version from the standard path. The rollback procedure
  (upgrade.sh --pin prior-tag) must be stated and verified to remain
  semantically correct after the refactor.

- **R-DO6** SEVERITY: LOW -- Background watchdog goroutine leak.
  The fallback watchdog at test-ownership-table.sh:86-87 starts a subshell
  (sleep secs; kill -9 pid) stored in watch. On SIGINT to the test runner,
  the wait at line 91 is not reached and the sleep subprocess is orphaned
  until its timer expires. In a 61-row run with CELL_TIMEOUT=60, up to 61
  orphaned sleep processes could accumulate if the harness is killed mid-run.

## Must-fix (blocking)

1. Add path filters for the three new artifacts to smoke-install.yml.
   Both pull_request and push filter lists must include:
     scripts/tests/test-ownership-table.sh
     scripts/tests/ownership_table.tsv
     docs/ownership-decision-table.md
   A PR updating the table or harness without this fix silently skips the gate.
   This is the unwired-test class that r10-F4 (ledger sec 8) was meant to
   permanently close. Fix: two additions to an existing list in one CI file.

2. Fetch v1.2.0 in the CI workflow before the ownership table step runs.
   Preferred form (mirrors the parity-pin fetch at smoke-install.yml:110-115):
     - name: Fetch the legacy_pristine tag (v1.2.0)
       run: |
         git fetch --no-tags --depth 1 origin +refs/tags/v1.2.0:refs/tags/v1.2.0
         git rev-parse --verify refs/tags/v1.2.0
   Alternative: add a harness fallback emitting HARNESS-SKIP (not ERR) when the
   tag is absent, so the suite exits 0 rather than 2. The choice is the Owner.

3. Specify the per-PR CI gate for the unit oracle before W1 is approved.
   The proposal describes a millisecond unit oracle but names no file, no CI
   step, and no path filter for it. W1 approval must include at minimum: the
   filename (e.g., scripts/tests/test-ownership-verdict-unit.sh), the
   smoke-install.yml step that runs it, and the path-filter entry that wires
   it. If the unit oracle is not wired per-PR, the per-PR gate covers zero
   cells of the 61-row space between nightly runs.

## Nice-to-have (advisory)

- Add operational recovery guidance to INSTALL.md Upgrade flow section:
  If upgrade hangs immediately after printing the backup line, check for special
  files (FIFOs, sockets) with: find TARGET -type p -o -type s
  Remove them before rerunning. Closes R-DO4 without a code change in W2.

- Fix the R-DO6 watchdog leak: add trap in the fallback body to kill watch
  on INT/TERM inside _run_with_timeout. One-liner change.

- Document the W2 rollback procedure in the commit message or RELEASE.md:
  Rollback: upgrade.sh --pin prior-tag restores the previous decision branch
  implementation; _ownership_verdict is not part of the public CLI contract.

## Unseen by the original plan

1. docs/ownership-decision-table.md is not in path filters (distinct from R-DO1
   which covers the harness and TSV). The document is the reasoning layer; the
   TSV is the value layer. A PR that updates one without the other is the drift
   vector the document was written to prevent. Neither file is in smoke-install.yml.

2. The unit test does not yet exist as a named artifact. Its absence is expected
   at W1 (it is a W2 deliverable). What is not safe to defer: leaving its CI
   path and step name unspecified at W1 approval time. The canonical path
   decision affects the path filter addition and possibly a _CANONICAL_GUARDS
   entry. Resolving it at W2 merge time creates a window with zero per-PR
   coverage of the decision cells.

3. Unguarded tree-walking readers in upgrade.sh beyond _emit_deprecation_warnings.
   Section 5.7 states the family sweep is broader: every tree-walking reader
   invoked during an upgrade is in scope. The proposal does not enumerate them.
   The following command before W2 gives a concrete count:
     grep -n "find.*-print\|find.*-type\|while.*read.*find" scripts/upgrade.sh
   If additional unguarded readers exist, they carry the same blast radius.

## What I would NOT change

- The _run_with_timeout fallback strategy (background kill group) is correct for
  macOS where no system timeout(1) exists. The gtimeout probe is the right first
  check. Do not replace with a perl-based workaround or hard coreutils dependency.

- The single-target-path fixture design (harness comments 190-193) is load-bearing.
  The canonical pointer digest in PROTOCOL.md is stable only because every row
  runs at the same path. Do not parallelize rows at different paths; the
  HASH_CANONICAL_POINTER classifier would silently fail on every protocol row.

- stat -f pct-m || stat -c pct-Y at harness line 141 is the correct portable
  fallback pair for macOS/Linux mtime. Do not collapse to a single GNU invocation.

- The decision to put _ownership_verdict() in the already-guarded
  scripts/_framework_manifest_set.sh (vs a new library file) is correct under
  the governance constraint. The file is already in the path filters (line 12).
  Adding the function there does not create a new CI wiring gap; only the test
  file and TSV do.

- R-10 equivalence-class wildcards are the right trade-off. Raw product at
  ~24,000 tuples at ~25s/cell is approximately 7 days of CI. The asterisk
  convention plus the obligation to split any dimension that turns out to matter
  is sound governance. Do not remove it in favor of complete coverage.

