---
plan: PLAN-152
round: 1
archetype: vp-engineering
skill: architecture-decisions
verdict: ADJUST_PROCEED
generated_at: 2026-07-01
---

## Verdict

ADJUST_PROCEED. The thesis (wave-order by blast radius; zero silently-dropped
findings) is correct and the findings are real and well-evidenced. But three
ceremony-boundary miscalls and one release-scope gap are blocking: they must be
fixed before `draft → reviewed`, because two of them silently change the size
of the run and one leaves a stated success-criterion unmet.

## Summary

- Fixes a real, live security regression set on a public release; structure is sound.
- Strong on accounting discipline (§Accepted / §Deferred pointers, §Do NOT re-flag).
- Weak on ceremony-boundary correctness (Wave B and Wave C mislabeled) and on
  scope realism — there is no cut line, and the actual guarded-edit count is far
  larger than the wave labels imply.

## Risks (the CEO did not see)

1. **Wave B is not "no ceremony".** `check_canonical_edit.py:182` guards
   `.github/workflows/*.yml` (tests-01 edits `validate.yml`, tests-04 edits
   `coverage.yml`) and `.claude/hooks/_lib/**/*.py` (:142-ish) guards
   `_lib/tests/**` — the matcher's `**` = zero-or-more segments
   (`check_canonical_edit.py:610-620`), so all 128 `_lib/tests` env-hygiene edits
   are canonical. Memory confirms "`_lib/tests/` IS guarded". Wave B therefore
   carries ~130 ceremony-scoped edits, not zero.
2. **The 3 security root-tests never reach CI under the current items** — tests-02
   only touches `pytest.ini`, which no CI job reads (all name explicit paths).
3. **The fail-closed flip (error-handling-01) can brick benign sessions** — every
   shlex-unparseable command would block, and the Check does not test that.

## Must-fix (blocking findings — cite evidence)

- **MF-1 — reclassify Wave B ceremony (SEVERITY: HIGH).** Wave-table says
  "Ceremony? no", but: `.github/workflows/*.yml` is guarded
  (`check_canonical_edit.py:182`) → tests-01 (`validate.yml`) + tests-04
  (`coverage.yml`) need the sentinel; `.claude/hooks/_lib/**/*.py` is guarded and
  the segment matcher expands `**` across `tests/` (`check_canonical_edit.py:610-620`;
  memory lesson `feedback-test-canonicality-and-env-hygiene-for-new-tests`) → the
  128 `_lib/tests` burndown edits are all canonical. Fix: add `validate.yml`,
  `coverage.yml`, and `.claude/hooks/_lib/tests/**` to the sentinel Scope, AND
  move the `_lib/tests` env-hygiene burndown to a follow-on (it is the bulk of the
  183 and the least release-critical item) OR batch it under one scoped sentinel
  with an explicit cost note. `swarm/tests` + `mcp-server/tests` + `detectors/tests`
  are NOT guarded (verified: no `.claude/scripts/**` glob in `_CANONICAL_GUARDS`) —
  those 55 land direct.

- **MF-2 — Wave C over-classifies the workflow edits (SEVERITY: MEDIUM).**
  error-handling-03 marks `.claude/workflows/{audit-fanout,nightly-hygiene,eval-baseline-n20}.js`
  as "CANONICAL (workflows) → ceremony", but `.claude/workflows/*.js` is NOT in
  `_CANONICAL_GUARDS` — the only `.js` guard is
  `.claude/plans/PLAN-*/corpus/locked/**/*.js` (`check_canonical_edit.py:~221`), and
  the plan's own §Approach ceremony list omits workflows (internal contradiction).
  Fix: these null-guard edits land DIRECT (drop them from ceremony scope, save the
  round-trips). If workflows *should* be guarded, that is governance-04
  kernel-matcher territory — already deferred — not a v1.0.1 in-wave call.

- **MF-3 — the security root-tests stay CI-dark (SEVERITY: HIGH; unmet success
  criterion).** The 3 tests are in root `tests/*.py`
  (`tests/test_codex_redact_fail_closed.py`, `test_mcp_bearer_nonce_replay.py`,
  `test_output_scan_llm03.py`). No CI job runs bare `pytest` (which alone reads
  `testpaths`): every invocation names explicit paths (`validate.yml:298,318,792,857`;
  `coverage.yml:100,130`). tests-01's wired-root list is tests/SUBDIRS
  (`test_federation`,`forensic`,`synthetic`) + `_lib/tests`,`swarm`,`mcp-server`,
  `detectors`,`predict-budget` — root `tests/` (top-level `*.py`) is in NEITHER
  tests-01 NOR a CI job. Success-criterion "3 security root-tests collect + pass in
  CI" is not achieved. Fix: tests-01 must add root `tests/` (top-level) to a CI job,
  not only `pytest.ini`.

- **MF-4 — fail-closed flip needs a false-positive Check (SEVERITY: HIGH;
  CLAUDE.md §4 tension).** Today `check_bash_safety.py:1212-1215` does
  `if not tokens: continue` — unparseable subcommand skipped. A blanket fail-CLOSED
  blocks EVERY shlex-`ValueError` command, incl. benign `echo it's fine`
  (unbalanced `'`). The Check asserts only `rm -rf ~ ";"` → block; it does not
  assert a benign unparseable command still ALLOWs. Fix: take the plan's stated
  "(or re-scan raw text)" branch — regex-scan the raw subcommand for destructive
  patterns without tokenizing — and make the Check discriminate:
  `echo it's fine` ALLOWs AND `rm -rf ~ ";"` blocks.

- **MF-5 — no cut line (SEVERITY: MEDIUM; SKILL mantra).** Budget 400-700k,
  `context_risk: high`, 7 waves, ~10 base guarded ceremony edits + (MF-1) up to
  ~130 more guarded test edits, each interleaved with MANUAL Codex review (auto
  pair-rail is dead until Wave A lands). No §Degradation section names what to cut
  on degradation. Fix: declare the release floor — A + B(core) + D + G mandatory;
  C / E / F / `_lib/tests` burndown are documented cut-on-degrade candidates
  (→ v1.0.2). See OQ3.

## Nice-to-have

1. tarball-01 says "mirror in BOTH kernel-guarded stagers" but the only blanket
   copy is `npm-publish.yml:98-100` (`cp -r "$src" npm/` over `.claude`); tarball
   contents = that Stage step + `package.json:9-13 files:[".claude/"]`. Confirm
   `install-npm.sh` actually stages the tree before treating it as a second mirror
   target — otherwise that edit is a phantom.
2. Wave F "reconcile the `OPUS47` label" is ambiguous: renaming the member
   `MODEL_ID.OPUS47` is a breaking ref-sweep; fixing the docstrings
   (`_types.py:12,41,94`) is trivial. The name is deliberately stable per the
   `R-CR R2-2` note at `_types.py:41`. Disambiguate to comment-fix only. See OQ1.
3. Make explicit that Wave A edits are canonical (`settings.json` etc.) yet the
   auto pair-rail cannot review its own repair (circular) → Wave A rides on MANUAL
   Codex review; state it so the operator does not skip it.

## Unseen (what is missing from the plan entirely)

1. **No kill-switch for the fail-closed flip.** A hot-path fail-open→fail-closed on
   EVERY bash command should ship behind an env toggle (default-on) so a bricking
   regression is disabled without a redeploy. Neither Wave A nor §Success mentions
   a flag or revert path.
2. **No per-wave rollback note.** For a release touching the security kernel, each
   ceremony wave should name its revert commit / disable path.
3. **A-before-B safety is asserted, never justified.** It IS safe — Wave A's blast
   is covered by the already-CI-wired `.claude/hooks/tests/`, not by the CI-dark
   roots B wires — but the plan should say so, since decision #1 explicitly asks it.

## What I would NOT change

- Wave order A→G by blast radius: correct. Live security fail-opens first;
  packaging (a live PUBLIC data leak) before cosmetics; closeout last.
- Wave D Check line is exemplary: it notes `npm/` is unstaged in-repo so a naive
  `npm pack` passes vacuously, and mandates staging into a scratch copy first
  (`npm-publish.yml:93` Stage step is CI-only). Keep it verbatim.
- The "every finding accounted for" discipline (§Accepted / §Deferred pointers,
  §Do NOT re-flag) — keep; it is what stops silent drops.
- Deferring governance-04 (kernel-matcher expansion) + governance-07 (NotebookEdit)
  to a follow-on: correct — those are ADR-scale kernel changes, not v1.0.1.

## Open questions (OQ1/OQ2/OQ3 answers)

- **OQ1 (Sonnet-5):** Agree with label+member+ADR now, routing deferred — with one
  refinement: do NOT rename `MODEL_ID.OPUS47` (breaking ref-sweep, zero benefit;
  the name is a stable identifier per `_types.py:41`). "Reconcile" = fix the
  docstrings at `_types.py:12,41,94` + ADD the Sonnet-5 member. An unrouted member
  earns its KERNEL ceremony only alongside the envelope ADR, which co-lands cheaply.
  The routing flip is a cost decision with its own soak → v1.0.2.

- **OQ2 (ceremony batching):** ONE sentinel, but its Scope must be an EXPLICIT file
  allowlist — the ~10 guarded files in A/C/D/F plus (per MF-1) `validate.yml`,
  `coverage.yml`, and `.claude/hooks/_lib/tests/**` if the burndown stays in — NOT
  a broad glob like `.claude/hooks/**`. One signing round-trip honors the Owner's
  single-run directive (Owner is the sole Wave-0 human); the enumerated scope keeps
  per-wave blast-radius tightness; the `touched−scope=∅` pre-commit check (memory
  lesson) is the guardrail against drift.

- **OQ3 (single vs split):** Lean SPLIT-AS-PRIMARY, not fallback. Ship
  A + B(core, minus the `_lib/tests` burndown) + D as **v1.0.1** — the security
  fail-opens, their CI net, and the tarball (a LIVE public exposure shipping
  red-team-corpus + internal PLAN files). Ship C / E / F + the `_lib/tests`
  env-hygiene burndown as **v1.0.2**. Rationale: D is as urgent as A (public data
  leak); C/E/F are quality/modernization with no external-exposure pressure; and
  the 128-guarded-edit burndown alone can exhaust one session (MF-1/MF-5). If the
  Owner insists on a single v1.0.1, then A + B(core) + D + G is the hard floor and
  everything else is explicitly cut-on-degrade.
