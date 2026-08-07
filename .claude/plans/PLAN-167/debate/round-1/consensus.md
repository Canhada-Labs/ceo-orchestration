---
plan: PLAN-167
round: 1
rounds_synthesized: [round-1]
agents_considered: [qa-architect, security-engineer, devops]
decisions_revised_in_plan:
  - "doc §5.5 — INV-3 added: an execution failure never advances the record"
  - "doc §5.4b — escape tripwire; OWN-0034 proven to write OUTSIDE the target"
  - "C2 amended — the ABORT split is adopted, the inherits-hash_source clause is struck"
  - "C3 ratified — legacy_pristine_partial becomes a live_content value; fault becomes a 15th column"
  - "§W2 gains W2.0 — scanner positive control before any TIMEOUT row may count as green"
  - "§W4 gains the CI wiring (canonical: smoke-install.yml lands via the ceremony, not the live tree)"
synthesized_at: 2026-08-06T23:50:00Z
synthesized_by: CEO
---

# Round 1 consensus — PLAN-167

Three critiques, three **ADJUST**, **zero VETO**. No agent rejected the
model; all three attacked its edges, which is the outcome the round was
designed to produce.

Recorded as **design-coherent**. That is not authorization to ship: the
verification cascade (V2 Codex pair-rail, V3 Owner GPG) is what authorizes,
and neither has run.

## Consensus findings (2+ agents flagged)

**C1 — `note`-as-dimension must close BEFORE any function is written.**
Flagged by qa-architect (must-fix 1, 2) and security-engineer (must-fix 2).
Agreed severity: **HIGH, blocking W2.**
A decision function cannot read prose, and the document itself already says
leaving `fault=` in free text is "the one option that should not survive".
Two rows (`OWN-0018`, `OWN-0020`) currently have identical nine-tuples and
opposite expected pairs, so no implementation can satisfy both.
**Resolution (CEO, both agents' preferred shape):**
- `live_content` gains **`legacy_pristine_partial`** — a tree carrying an
  entry the fingerprint cannot inventory. It is not "pristine with a note";
  it is a distinct observable, and it resolves to the **preserve** side
  (ADR-155-AMEND-1 §4: a partial inventory must never certify).
- `fault` becomes a **real 15th column**, not a directive in prose.
  qa-architect offered dropping those rows as the lower-friction path;
  **rejected** on security-engineer's ground: the fault rows are the
  backup-failure *safety* cells, and dropping them drops coverage of a
  data-loss path. A column is cheap; a hole is not.

**C2 — the decision/execution split is adopted, its `hash_source` clause is
struck.** Flagged by security-engineer (must-fix 1); qa-architect's must-fix
3 is the same concern from the verification side.
Agreed severity: **HIGH, blocking.**
The proposal said an `ABORT_SURFACE` "inherits the verdict's `hash_source`".
That would record a delivery **that did not happen** — the framework
claiming bytes it never wrote, which is the over-claiming direction
ADR-155-AMEND-1 §3 explicitly forbids. The split itself is sound and is
kept; the clause is replaced by **INV-3**, which now appears verbatim in
`docs/ownership-decision-table.md` §5.5 and must appear verbatim in ADR-190:

> **INV-3 — an execution failure never advances the record.** A caller
> handed `DELIVER` or `REFRESH` that cannot complete it leaves the manifest
> describing the world as it actually is; the record after a failed attempt
> equals the record before it.

**C3 — the new artifacts are not wired into CI.** Flagged by devops
(must-fix 1, 2, 3); qa-architect's must-fix 3 is the same class one layer
down (a test that cannot reach what it asserts).
Agreed severity: **HIGH.** Verified literally: `grep -c` returns 0 for all
three new paths in `.github/workflows/smoke-install.yml`, and that file uses
`fetch-depth: 1`, which produces a checkout with no tags — so the harness's
`git archive v1.2.0` cannot run there.
**This is the same class as finding r10-F4**, which was itself "a test the
only CI execution of which was skipped". The table caught its own ancestor.
**Resolution:** all CI changes land in the **W4 staged pack**, never in the
live tree — `.github/workflows/*.yml` is canonical-guarded (plan §3).

## Single-agent insights kept

1. **security-engineer must-fix 3 — the harness was blind to out-of-tree
   writes.** Verified and **already fixed during the round**: the fixture's
   foreign file is now a tripwire digested before and after each run, and
   any change yields status `ESCAPE`, which outranks the verdict comparison.
   Positive control: `OWN-0034` now reports `ESCAPE`. Negative control:
   `OWN-0044` (a correctly-preserved symlink) does not.
   **This promoted a finding**: the missing leaf-symlink guard on the
   pointer is no longer a hardening gap, it is a **demonstrated out-of-tree
   write** — the S238 class.
2. **security-engineer must-fix 4 — `hash_source` becomes required and
   fail-closed** for the three conditional surfaces: a conditional-surface
   record with no declared `hash_source` is not emitted, plus a named NOTE.
   Kept because §3.4 already showed `HASH_TARGET` is never correct across
   61 rows while being the permissive default. **Scope is load-bearing**:
   target-hashing of the broader rendered install tree is LEGITIMATE and
   stays — over-widening exactly there caused the r8-F1 P1 regression.
3. **qa-architect must-fix 3 — staged verification for the TIMEOUT rows.**
   A scanner fix that merely moves the blocking point downstream would turn
   three rows green without exercising the guards they claim to cover.
   Adopted as a new plan step **W2.0**: a standalone scanner probe must exit
   0 on a FIFO-bearing tree *before* any TIMEOUT row counts as green.
4. **devops must-fix 3 — name the per-PR gate.** Adopted: the unit oracle
   is `scripts/tests/test-ownership-verdict-unit.sh`, wired per-PR; the
   61-row e2e stays nightly. Without this the per-PR gate covers zero cells
   between nightly runs.

## Single-agent insights rejected / deferred

1. **qa-architect's option (b) for OQ-7** (drop the `fault` rows as
   out-of-scope) — **rejected**, see C1. Those are the safety cells.
2. **devops's alternative for the missing tag** (a harness fallback emitting
   `HARNESS-SKIP` so the suite exits 0) — **rejected**. A suite that goes
   green by skipping the rows it cannot run is the vacuous-gate class this
   repo has been bitten by before. The harness already fails loudly with the
   remedy in its message; CI fetches the tag.
3. **security-engineer must-fix 6** (completeness/uniqueness oracle, plus
   the missing `skip=self × edited` cells) — **deferred to W2**, not
   dropped. It is additive coverage and does not block the specification.

## Plan adjustments

- `§W0.2` — TSV schema goes to **15 columns** (`fault` added).
- `§W2` — new first step **W2.0** (scanner positive control).
- `§W2` — the unit oracle is named and wired per-PR.
- `§W4` — CI wiring added to the staged pack (canonical surface).
- `docs/ownership-decision-table.md` §5.4b, §5.5 (INV-3) — already applied.

## Round verdict

**PROCEED** — with C1 and C2 landing as table/spec changes *before* the
first line of `_ownership_verdict()` is written. No agent raised a VETO and
no two critiques conflict; the disagreements were between an agent and the
proposal, and every one resolved on evidence rather than on preference.

Recorded as `design-coherent`. Shipping remains gated on V2 + V3.
