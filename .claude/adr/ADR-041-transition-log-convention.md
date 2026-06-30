# ADR-041: Transition Log Convention for State-Machine ADRs

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 12 (PLAN-012 Phase 0, single-agent finding §S7 accepted)
**Related:** ADR-007 (SPEC v1 + SemVer + RC policy — versioning precedent for
additive amendments), ADR-019 (confidence-gate three-state lifecycle —
first state-machine ADR in the framework, this convention's first client),
ADR-024 (perf baseline measure-then-gate — sibling), ADR-033 (budget
lifecycle — sibling), ADR-035 (OTEL export advisory → gate — sibling),
ADR-036 (output-safety flag → redact — sibling), ADR-037 (chaos advisory
→ blocking — sibling; most-recent state-machine ADR used as style
reference)

## Context

Six framework ADRs now describe **state-machine lifecycles** where a
subsystem ships in State 0 (advisory / measure-only), transitions to
State 1 on a published flip criterion, and optionally transitions to
State 2 on a second criterion. Each of those ADRs includes its own
ad-hoc transition-timeline table + flip-criteria table.

**The problem:** the tables drifted. ADR-024 uses "Date (target) /
Trigger"; ADR-037 uses "Target window / Trigger"; ADR-019 uses "Phase /
Date (target) / Action"; ADR-033 mixes "State / Date (target) / Trigger"
with a separate "Transition / Criterion / Metric / Window / Fallback"
table. When a flip actually happens in Sprint 12+ (the PRs that flip
output-safety flag→redact, chaos 0→1, budget 0→1, etc.), a reviewer
will want to audit **"what changed, when, with what evidence, signed
by whom"** across all 6 ADRs at once. Without a uniform row shape,
this is manual archaeology every time.

PLAN-012 debate round 1 single-agent finding §S7 (VP Engineering)
identified this gap as a governance smell. The CEO accepted the finding
per PROTOCOL.md §Debate rule ("if 1 agent flags a risk no one else saw,
the CEO evaluates and decides"). This ADR is the resolution.

## Decision drivers

- **Uniform audit trail.** Every state transition across all
  state-machine ADRs must record the same six fields, in the same
  column order, appended in the same location (ADR bottom), so that
  cross-ADR queries (`grep '^| 2026-' .claude/adr/ADR-*.md`) surface
  an entire-framework timeline in one shot.
- **Mechanical verifiability.** A Sprint 12 helper
  `check-flip-criteria-drift.py` (PLAN-012 Phase 2 deliverable) can
  parse the appendix format and assert that every flip PR added a
  row whose `PR-Ref` resolves. This is impossible when formats drift.
- **Additive only.** Per ADR-007 §SemVer — amendments never delete
  past entries. New rows are appended below existing rows in
  chronological order. If a historical row is wrong, the fix is a
  new row that annotates the error, not an edit of the old row.
- **Cross-ADR consistency > per-ADR expressiveness.** An ADR author
  who feels the six fields are insufficient should propose a new
  column in a follow-up ADR amendment (additive), not diverge silently.

## Options considered

### Option A — Free-form amendments (status quo, rejected)

Each ADR author picks whatever table shape suits that ADR's narrative.
ADR-024 uses "Date (target) / Trigger"; ADR-037 uses "State / Target
window / Trigger"; etc.

**Pros:** zero up-front standardization cost; each ADR optimized for
its own readability.
**Cons:** cross-ADR audit requires re-learning each format; mechanical
drift-checkers impossible to write; a Sprint-15 reviewer has to
re-derive the shape of each ADR's timeline from scratch.

**Rejected** — this is the problem we're solving.

### Option B — Transition Log appendix (CHOSEN)

Every state-machine ADR appends a `## Transition Log` section at the
bottom. Rows are chronological, fields are fixed (`Date | From-State
| To-State | Evidence-Link | PR-Ref | Signer`), and the appendix is
retroactively added to the 6 existing state-machine ADRs with an
empty first row ("_(empty — first flip pending per PLAN-012)_").

**Pros:**
- One mental model for all state-machine ADRs.
- Mechanical drift-checker is trivial to write (parse markdown table
  under `## Transition Log`, assert 6 columns, assert PR-Ref matches
  `#\d+` or a full URL).
- Atomicity: the amendment row lives **in the ADR it describes**, so a
  git-blame on the ADR file surfaces the transition history alongside
  the decision context.
- Owner can `grep -A 20 '^## Transition Log$' .claude/adr/*.md` to see
  the entire framework's state-machine timeline in one command.

**Cons:**
- Retroactive appendix adds ~15-20 lines to 6 existing ADRs (~100 LOC
  total). Small one-time cost.
- Ongoing per-amendment boilerplate: flip PRs must touch 3 things
  (settings.json default, regression test, ADR transition row).
  Acceptable — that boilerplate is the **point** (forced documentation).

**Chosen.**

### Option C — Separate state-machine change log file (rejected)

One `STATE-MACHINES.md` file tracks all transitions across ADRs. ADRs
reference it by pointer.

**Pros:** single file, easiest to grep.
**Cons:** splits atomicity — a git-blame on the ADR no longer shows
why it transitioned. Decision context (ADR body) and transition record
(separate file) drift independently. A future `rm` of
STATE-MACHINES.md would silently erase transition history without
touching the ADRs themselves. Splitting the source of truth in
governance-critical records is a well-known anti-pattern (cf. audit
log duplication).

**Rejected.**

## Decision

### 1. Convention (normative)

Every ADR that describes a **state lifecycle** (one or more transitions
between named states such as State 0 / State 1 / State 2, or
"advisory" / "blocking", or "flag" / "redact") MUST append a
`## Transition Log` section at the bottom of the file, immediately
before the `## References` section if one exists, otherwise as the
final section.

The section contains exactly one markdown table with the following
six columns, in this order:

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|

**Field semantics:**

- **Date** — ISO 8601 `YYYY-MM-DD` of the merge commit that flipped
  the state. Not the PR-open date; not the measurement-window end.
- **From-State** — canonical name used in the ADR body (e.g. `State 0`,
  `advisory`, `flag`).
- **To-State** — canonical name (e.g. `State 1`, `blocking`, `redact`).
- **Evidence-Link** — relative path or URL to the artifact that proves
  the flip criterion was met (e.g.
  `../../benchmarks/human-sample-calibration.md#row-2026-05-14` or a
  `audit-query.py otel-drops --since 14d` report committed under
  `docs/reports/`).
- **PR-Ref** — `#NNN` for a GitHub PR or the full URL. Must resolve
  to a merged PR, not a draft.
- **Signer** — Git identity of the Owner or delegated reviewer who
  approved the flip. Format: `<name> <email>` matching `.mailmap`.

### 2. Seed content (retroactive application)

The 6 existing state-machine ADRs (019, 024, 033, 035, 036, 037) get
the appendix with an empty placeholder row documenting that no flip
has happened yet:

```markdown
## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row
records a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| _(empty — first flip pending per PLAN-012)_ | | | | | |
```

When the first real flip happens, the Sprint-12+ PR that performs the
flip must replace the empty-placeholder row with a populated row (and
append additional rows below it in chronological order).

### 3. Amendment discipline (additive only)

- Transition Log rows are **append-only**. Never delete a row.
- If a historical row is wrong (e.g., a State 1→2 flip was later
  reverted), the correction is a **new row** below it (e.g.
  `2026-07-01 | State 2 | State 1 | docs/reports/rollback-.md | #312 |
  ...`), not an edit of the original.
- Column additions require a new ADR amendment (not a silent edit).
  The Sprint-12 drift-checker asserts exactly 6 columns; widening
  must update the checker too.

### 4. Cross-reference from flipping PRs

Every Sprint-12+ PR that performs a state-machine flip MUST:

1. Touch the owning ADR to append a Transition Log row.
2. Reference ADR-041 in the PR body (link + one-line rationale).
3. Pass the Sprint-12 Phase-2 `check-flip-criteria-drift.py` checker.

The flip is not merged until the row is present and the checker is
green. (Sprint-12 Phase-2 adds the checker to `validate.yml`.)

### 5. Scope (what this ADR does NOT mandate)

- Does NOT retrofit the Transition Log to non-state-machine ADRs
  (e.g. ADR-001, ADR-002, ADR-007). Those describe one-shot
  architectural decisions, not lifecycles.
- Does NOT replace the existing per-ADR "Flip criteria" or
  "Transition timeline" tables — those remain the **decision** record.
  The Transition Log is the **execution** record. Both coexist.
- Does NOT specify a workflow for SUPERSEDED ADRs (e.g. ADR-017). If
  an ADR gets superseded mid-lifecycle, the successor ADR inherits
  the Transition Log and appends a first row documenting the
  supersession (as if a state transition).

## Consequences

### Positive

- One format, six ADRs, and every future state-machine ADR. Cross-ADR
  timeline queries are a single `grep`.
- Mechanical drift-checker becomes feasible (Sprint-12 Phase 2).
- PR reviewers see the Transition Log row in-diff, forcing a
  conscious "what did we just flip" question every time.
- Evidence-Link is in the ADR: a git-blame on the evidence file
  surfaces the transition it justified without cross-repo lookups.
- Signer field codifies who approved each flip — clean audit trail
  for branch-protection + release-hold governance.

### Negative

- Every flip PR now touches 3 files minimum (settings.json, regression
  test, ADR Transition Log row). Slight boilerplate cost. Accepted
  tradeoff (the boilerplate IS the governance).
- Retroactive one-time cost of ~100 LOC appended across 6 ADRs. No
  behaviour change; docs-only amendment.
- If an author of a new state-machine ADR forgets the Transition Log
  appendix, it ships without one — until the first flip happens and
  the drift-checker rejects the flip PR. Mitigation: `architecture-
  decisions` skill MANTRA addition ("every lifecycle ADR needs a
  Transition Log") — addressed by Owner-signed canonical-edit patch
  (separate PR, out of scope here).

### Neutral

- Transition Log is a bottom-of-file appendix; existing ADR body
  content is byte-identical after the retroactive amendment.
- No new tooling shipped in this ADR. Sprint-12 Phase 2 ships the
  drift-checker; this ADR just establishes the format contract.

## Blast radius

**L2** — one new ADR (this file), 6 appendices (~15-20 lines each)
added to ADR-019, ADR-024, ADR-033, ADR-035, ADR-036, ADR-037. No
code changes. No workflow changes. No schema changes. No test
changes in this PR (Sprint-12 Phase-2 ships `check-flip-criteria-
drift.py` and its tests separately).

**Reversibility:** HIGH. Remove `## Transition Log` appendices from
the 7 affected ADRs and delete this file; behaviour is unchanged.
The convention has no runtime effect — it is a governance contract.

## References

- PLAN-012 §Debate consensus §S7 (this ADR's source).
- PLAN-012 §How to continue §"flip criterion window closes" — calls
  out the ADR-041 row requirement.
- PLAN-012 §Revert procedure — step 3 lists the Transition Log entry
  as mandatory on emergency-revert PRs.
- ADR-007 — SemVer + RC policy (additive amendment discipline).
- ADR-019 — confidence-gate lifecycle (first client).
- ADR-024 — perf baseline policy (sibling).
- ADR-033 — cost/budget enforcement (sibling).
- ADR-035 — OTEL export (sibling).
- ADR-036 — output-safety (sibling).
- ADR-037 — chaos testing (sibling, style reference).
- `.claude/skills/core/architecture-decisions/SKILL.md` — ADR format skill.

## Enforcement commit

`190bf644ad40` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
