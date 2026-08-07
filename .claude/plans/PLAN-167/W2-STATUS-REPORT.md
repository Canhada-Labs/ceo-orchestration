# PLAN-167 — status report, morning of 2026-08-07

**This is the §6.10 deliverable, not a pack.** The plan says: if the map does
not close 100% or the run stalls, the deliverable becomes the REPORT — the
table, the map, and what remains — never a partial pack. A partial signed
pack is worse than no pack, so nothing here is presented for signature.

**Nothing needs your GPG key this morning.** Every artifact below is free
surface and already committed. The canonical work is staged in a clone and
has not touched the live tree.

---

## What is done and proven

| Wave | State | Evidence |
|---|---|---|
| W0.1 table doc | ✅ | `docs/ownership-decision-table.md` |
| W0.2 TSV | ✅ | 61 rows, now **15 columns** after the round-1 ratification |
| W0.3 e2e harness | ✅ | real scripts, zero mock, per-cell timeout, escape tripwire |
| W0.4 baseline map | ✅ | **50 green / 11 red**, every red attributed to a real defect |
| W0.5 commit | ✅ | `a09427f`, exactly 5 paths (gate verified) |
| W1 debate | ✅ | 3 ADJUST, 0 VETO, `design-coherent` — `4fd4ba2` |
| W1 consensus C1 | ✅ | `fault` is a real column; `legacy_pristine_partial` a real value |
| W2 decision function | ✅ | **unit oracle 59 PASS / 0 FAIL**, 2 counted exclusions |
| W2.2 caller refactor | ◐ | observers + **shadow run** done; the swap itself is the gap |
| W3 codex rail | ❌ | not started |
| W4 pack | ❌ | not built, by design |

## The shadow run — W2.2 measured instead of guessed

Rather than swap the live decision path on an unverified assumption, the
function was run in **shadow mode** against the real callers: it observes the
nine dimensions, records what it would decide, and does **not** act. The
clone's suite then returned `50 green / 11 red` — byte-identical to the live
tree, confirming the instrumentation is inert.

The unit oracle already proved the function matches the TABLE, and the e2e
proved the callers match the table. Neither proved the function matches what
the callers **observe**, and that is the gap a direct swap would have crossed
blind.

| Outcome | Count | Meaning |
|---|---:|---|
| agree | 17 | the function reproduces the live outcome — the swap is behaviour-preserving here |
| diverge | 2 | the W2.2 work list |
| never reached | 10 | the caller returned before the observation point |

**Divergence 1 — `OWN-0082`: the function is right and the live code is
wrong.** Flag-only continuity: ownership is claimed but the rewrite emits no
record. The row is already red in the baseline; the function encodes the fix.

**Divergence 2 — `OWN-0030`: a defect in the MODEL, not in either
implementation.** `prior_record` never said whether it means the raw manifest
or the sanitized one, and the two disagree exactly on the symlink-traversal
rows. Written up as §5.4c. This is the shape that survives eleven rounds of
review: every branch reads *a* manifest, each reads a defensible one, and no
branch is individually wrong.

**The 10 unreached rows decompose cleanly**, and the decomposition matters:
eight are `install_*` rows that never invoke the upgrade path at all — those
need the same treatment on `install.sh` — while two are genuinely blocked.
`OWN-0024` aborts earlier under its injected fault, and `OWN-0025` is killed
by the scanner hang before control ever arrives. **That is §5.7 confirmed a
second time, from a different direction**: the guard cannot be reached, so no
end-to-end result about it means anything.

## Why the swap itself was not attempted overnight

It rewrites the decision paths of `install.sh` and `upgrade.sh` — two
canonical scripts that **every adopter executes**. The remaining window was
not enough to do it and verify it, and an unverified refactor of the
distribution surface is precisely the thing that should not be rushed to
meet a clock. The decision logic it depends on is finished and proven, so
the work is now mechanical rather than exploratory.

---

## What the table found that eleven review rounds did not

The plan predicted the table would pay for itself. It did, before the
refactor even started.

1. **A proven out-of-tree write.** `OWN-0034`: the root pointer is written
   with `cat >`, which follows an adopter's leaf symlink and writes
   **outside the target tree**. `spec` and `marker` both acquired a
   leaf-symlink guard during the S296 rounds; `protocol` never did. This is
   the S238 data-loss class, demonstrated in live fire, not hypothesised.
2. **The FIFO hang is not where anyone looked.** It is not in the marker
   route — it is in a tree-walking scanner that runs *before* any refresh.
   Consequence: the existing special-file guards are **unreachable**, so a
   green suite proves nothing about them.
3. **Dead code posing as a guarantee.** The continuity line inside the
   ancestor-symlink guard can never fire: the relpath sanitizer drops the
   record at load time, before the check runs. The fix is to delete it —
   making it fire would breach the ADR-155 provenance fence.
4. **Three of five pruning rules the plan asserted were wrong.** One would
   have deleted the still-open r11-F1 cell from the space entirely.
5. **`HASH_TARGET` is never correct** across all 61 rows — and it is the
   generator's default when no override is passed.
6. **The finding count was wrong.** 35 literal findings, not 24. The
   acceptance criterion demanded enumeration rather than a count, which is
   the only reason this surfaced.

## What the debate found — including against my own proposal

- **The `ABORT_SURFACE` clause was dangerous.** I proposed that an execution
  failure "inherits the verdict's `hash_source`". That records a delivery
  **that did not happen** — the framework claiming bytes it never wrote,
  the over-claiming direction ADR-155-AMEND-1 §3 forbids. Now **INV-3**.
- **The harness was blind to the damage it was built to detect.** It
  compared only the target, so a write escaping through a symlink was
  invisible. Tripwire armed; that is how finding 1 above became provable.
- **The new tests were not wired into CI** — same class as r10-F4, the
  finding about a test whose only CI execution was skipped.

## What I got wrong, and how it was caught

Five defects in my own instrument, four of which produced a confident green
or red that meant nothing:

| # | Defect | Would have caused |
|---|---|---|
| 1 | one source for both install-base and upgrade | 16 false reds → "fixing" 16 non-bugs |
| 2 | `install_fresh` extracted a base | a rerun testing under a fresh label |
| 3 | symlink repointed on every row | **green** rows "proving" LINK preservation with a *redirected* link |
| 4 | guard leaking a non-zero exit | a row silently not running |
| 5 | backup-presence as a refresh signal | preserve-with-snapshot misread as refresh |

The lesson generalises beyond this plan: the S296 loop is usually described
as branch-local patching, and that is true but incomplete. **The deeper
problem was measuring with an instrument nobody audited.** A cartesian space
punishes a loose instrument exactly as it punishes loose code.

---

## W2.3 was attempted, regressed 24 cells, and was reverted

`50 green / 11 red` → **`26 green / 35 red`**. Twenty-four previously-green
cells broke: 13 `marker`, 11 `spec`. Reverted to the coherent W2.2 state;
the failing map is kept as `evidence/W2.3-FAILED-map.txt`.

**The cause was mine, and it was a sequencing error.** W2.3 makes the
generator fail-closed: a conditional surface that declares no `hash_source`
is not recorded. That is correct — and it assumes **every caller declares one
on every delivery path**. I had refactored exactly one caller (`spec`, on the
upgrade side) and wired install's declaration only to the continuity path. So
a fresh install delivered the surfaces and declared nothing, and the
fail-closed branch correctly declined to record them.

The plan's wave order exists for this: W2.2 converts **all** the callers,
then W2.3 changes the generator. I ran W2.3 with one of three callers
converted, which is not a partial step toward the goal — it is an incoherent
intermediate state that no amount of debugging would have made green.

**Two things went right, and they are why this cost 25 minutes rather than a
morning:**
1. The failure was **loud and immediate**. Fail-closed did exactly its job:
   an undeclared ownership claim became "no record" rather than a silently
   wrong one. The dangerous version of this bug records the wrong digest and
   surfaces months later as an overwritten adopter file.
2. **The table caught it.** 24 cells changed status the moment the change
   landed. Under the S296 regime this would have been one review round
   noticing one symptom — the shape of loop the whole plan exists to break.

### What W2.3 needs before it can land

1. Refactor the `marker` and `protocol` callers the way `spec` was done.
2. Declare `hash_source` on **every** delivery path, not only continuity —
   including fresh install, where the surfaces are genuinely delivered.
3. Only then make the generator fail-closed.
4. Keep `FMS_LINK_PATHS` (see below).

## A second instruction in the plan that is half wrong

§W2.3 says `FMS_HASH_ROOT_PATHS` **and** `FMS_LINK_PATHS` are "removed —
replaced, not added". Only the first half survives contact:

- **`FMS_HASH_ROOT_PATHS` is genuinely subsumed.** It exists to confine a
  global switch to the continuity paths, and an explicit per-surface
  `hash_source` says the same thing directly. It goes.
- **`FMS_LINK_PATHS` is not.** It encodes **INV-2** — LINK serialization may
  cover only paths that were already LINK records — and its blast radius is
  the **whole enumeration**, not the three conditional surfaces. It is what
  stops an adopter's own symlink inside `.claude/hooks/` from being promoted
  into a framework delivery record. Nothing in the three-surface decision
  space covers that path, so removing it would reopen the r10-F2 defect.

This is the third plan instruction to fail verification (after the three
pruning rules in §4.1 and the clone-from-HEAD step). The pattern is
consistent and worth naming: **the plan is reliable about the shape of the
work and unreliable about specific mechanics**, because the mechanics were
written from memory of the S296 sessions rather than re-derived from the
code. Verify each one before executing it.

## Recommended next steps

1. **W2.2** — refactor the two callers to observe → call → execute. The
   function is proven; wiring is mechanical. Clone path is recorded in the
   plan §9.
2. **W2.0 first** (qa-architect's must-fix): a standalone scanner probe must
   exit 0 on a FIFO-bearing tree *before* any TIMEOUT row counts as green —
   otherwise a fix that merely moves the blocking point downstream turns
   three rows green without exercising the guards they claim to cover.
3. **W3** codex rail on the TABLE, hard cap of 4 rounds.
4. **W4** pack, then your signature.

## Decisions waiting for you (none blocking tonight's work)

- **OQ-9** — `OMIT_RECORD` may not be an independent verdict; it is
  `PRESERVE_UNOWNED` observed where a prior record existed. Reconciled to
  one rule for now. Combined with the `ABORT_SURFACE` split this would take
  the enum from six verdicts to four.
- **Security must-fix 4** — make `hash_source` required and fail-closed for
  the three conditional surfaces. Scope is load-bearing: target-hashing of
  the broader rendered tree is legitimate and must stay; over-widening
  exactly there caused the r8-F1 P1 regression.
