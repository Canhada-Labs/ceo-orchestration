# ADR-023: Docs-as-code freshness enforcement lifecycle

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 10 (PLAN-010 Phase 3)
**Related:** ADR-019 (confidence gate enforcement lifecycle — 3-state pattern
this ADR mirrors), ADR-021 (e2e harness contract), ADR-024 (perf baseline)

## Context

Sprint 10's "perfeccionismo" pass noticed that markdown references across
`CLAUDE.md`, `CLAUDE_FULL.md`, `README.md`, `docs/**`, `.claude/adr/*`,
`.claude/plans/PLAN-*`, and `.claude/skills/**` drift silently when files
are moved or renamed. There is no CI signal today; drift compounds until
a human notices a 404.

PLAN-010 Phase 3 ships `.claude/scripts/check-docs-freshness.py` — a
stdlib-only, pragmatic markdown scanner. Fenced code blocks, inline code
spans, YAML frontmatter, and HTML comments are excluded. External URLs
(scheme://...) and anchor-only refs (`#section`) are ignored. A fixture
corpus of 10 edge-case `.md` files exercises the scanner.

The question ADR-023 answers: **how do we go from advisory to blocking
without breaking a happy main branch the first time a rename lands?**

## Decision drivers

- **Machinery, not activation.** Sprint 10 ships the scanner + CI step;
  Sprint 11 flips the switch based on measured signal (0 broken refs on
  main for two consecutive CI runs).
- **False-positive-to-allowlist over false-negative-to-missed-bug.** Until
  enforcement flips, the scanner is allowed to under-detect in weird
  markdown rather than block legitimate changes on parser edge cases.
- **Own the allowlist.** Every allowlist entry has an Owner (declared in
  the file header) and a quarterly review cadence. A silent-forever
  allowlist is the same anti-pattern as advisory-forever CI.
- **Mirror ADR-019.** The 3-state lifecycle (advisory-CLI →
  advisory-workflow → blocking-workflow, with an optional State 3 hook)
  is copied deliberately. Lessons from the confidence gate apply.

## Decision

### 1. Three-state lifecycle

```
    Sprint 10           Sprint 11 (conditional)     Sprint 12+ (optional)
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│  State 1       │───▶│  State 2       │───▶│  State 3       │
│  advisory      │    │  blocking      │    │  PreToolUse    │
│  CLI + CI step │    │  CI step       │    │  hook          │
│                │    │                │    │                │
│ continue-on-   │    │ exit=1 fails   │    │ Edit/Write     │
│ error: true    │    │ validate job   │    │ checks ref     │
│ exit code     │    │                 │    │ existence      │
│ surfaced in    │    │                │    │ before commit  │
│ $GITHUB_STEP_  │    │                │    │                │
│ SUMMARY        │    │                │    │                │
└────────────────┘    └────────────────┘    └────────────────┘
```

**Sprint 10 ships State 1.** `.github/workflows/validate.yml` invokes
`python3 .claude/scripts/check-docs-freshness.py --format=text`.
Output is captured in `$GITHUB_STEP_SUMMARY` so reviewers see it
without digging into logs.

**Sprint 14 flips State 1 -> State 2 (blocking).** PLAN-014 Phase E.2
verified 0 broken refs across 5+ consecutive main pushes (2026-04-15).
`continue-on-error: true` removed from validate.yml. See Transition Log.

**State 1 → State 2 exit criterion (normative):**

> 0 broken refs across 2 consecutive CI runs on `main`.

Two runs, not one, so a merge race that lands a rename + doc fix in
quick succession does not trip enforcement mid-cut. When met, a Sprint
11 PR removes `continue-on-error: true` and this ADR moves to SUPERSEDED
with a successor ADR documenting the transition.

**State 2 → State 3 (optional):** if post-enforcement doc drift still
slips through (e.g., an Edit tool rename silently orphans refs between
merge and CI), a PreToolUse hook on Edit/Write may be added. Not
committed in this ADR; covered by a future ADR iff justified by data.

### 2. Scanner contract

- **Input surface (default globs):**
  `CLAUDE.md`, `CLAUDE_FULL.md`, `README.md`, `docs/**/*.md`,
  `.claude/adr/*.md`, `.claude/plans/PLAN-*.md`, `.claude/skills/**/*.md`
  (overridable via `--glob`).
- **Exclusions (hardcoded):** any path under `tests/fixtures/`. Fixtures
  are intentionally broken.
- **Ignored targets:**
  - Scheme URLs (`^[a-z][a-z0-9+.\-]*:`): http, https, ftp, mailto,
    javascript, etc.
  - Anchor-only refs (`#...`).
  - Empty targets.
  - Allowlisted targets (exact-match, fragment-stripped).
- **Resolved targets:** relative to the containing file; URL-decoded;
  both decoded and raw forms probed (some repos carry literal `%20`).
  Fragment + query stripped before existence check.
- **Output modes:** `text` (human, default) + `json` (machine). JSON
  schema: `{scanned_files: int, broken_count: int, broken: [{file,
  line, col, target, resolved}]}`.
- **Exit codes:** 0 clean, 1 broken refs found (advisory in State 1 /
  blocking in State 2), 2 usage/arg error.

### 3. Allowlist contract

`docs/docs-freshness-allowlist.txt`:

- Header MUST contain `# owner: @<owner>` and
  `# quarterly review: every 90 days`.
- One target per line; `#` comments OK; blank lines OK.
- Exact match against the `[text](target)` target as it appears in
  markdown (fragment + query stripped). No globbing.
- Quarterly review (next entry lives in `docs/ROADMAP.md`): Owner
  revisits the file; stale entries are removed; entries that correspond
  to files that now exist are deleted.

Initial state at Phase 3 ship: empty (real-repo scan of 110 files
returned 0 broken refs).

### 4. Rollback signal

If State 2 enforcement blocks a legitimate branch more than once in
a sprint, flip `continue-on-error: true` back on in the same PR,
open an issue tagged `docs-freshness-fp`, and bounce back to State 1
until the scanner edge case is fixed. Do not grow the allowlist as
the rollback tool — that is debt, not a fix.

## Consequences

### Positive

- Doc drift becomes a visible CI signal from day one.
- The 3-state lifecycle gives reviewers a named predecessor ADR when
  Sprint 11 writes the flip ADR — no retcon.
- Fixture corpus (10 `.md` edge cases) documents what the scanner does
  and does NOT catch.

### Negative

- The scanner is intentionally pragmatic, not a full CommonMark parser.
  Weird markdown constructs (reference-style links, nested emphasis inside
  link text) may under-detect or over-detect. State 1's `continue-on-error`
  absorbs this risk.
- One more CI step per PR. Runtime is O(files × links); on the current
  surface (~110 files, ~500 links) scan is <1s.

### Neutral

- No new runtime dependency — stdlib only.
- No hook surface change (Sprint 10 ships CI-side only; State 3 would
  be Sprint 12+ IFF justified).

## Blast radius

**L2** — one new script (~300 LOC) + tests (~200 LOC) + 10 fixture
files + one allowlist + one ADR + one workflow step.

**Reversibility:** HIGH. Removing the CI step is one-line YAML edit.
The scanner itself is useful as a local pre-commit even without CI.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row records
a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| 2026-04-15 | 1 (advisory-CI) | 2 (blocking-CI) | `check-docs-freshness.py` 0 broken refs across 5+ consecutive main pushes (commits acc5638..78ae44b) | PLAN-014 Phase E.2 | DevOps (automated via PLAN-014 E.1-E.4) |

## References

- PLAN-010 §Phase 3 + §C8 (fixture-first) + §C14 (allowlist owner + review)
- ADR-019 — 3-state enforcement lifecycle (confidence gate, exact pattern
  mirrored here)
- ADR-021 — e2e harness contract (Phase 1, shares `validate.yml` step surface)
- ADR-020 — supersede-not-amend convention (if Sprint 11 flips State 2)
- CLAUDE.md §Critical Rules (advisory CI stays advisory until measured)

## Enforcement commit

`05d8d333c07d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
