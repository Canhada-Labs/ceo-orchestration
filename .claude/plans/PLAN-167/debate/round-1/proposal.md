---
plan: PLAN-167
round: 1
created_at: 2026-08-06T23:20:00Z
---

# PLAN-167 round 1 — proposal

Full plan: `.claude/plans/PLAN-167-ownership-decision-table.md`
Model under debate: `docs/ownership-decision-table.md`
Truth file: `scripts/tests/ownership_table.tsv` (61 rows)
Baseline: `scripts/tests/ownership-baseline-map.txt` (50 green / 11 red)
W2 draft of the function: see §5 below.

## 1. Thesis

The install/upgrade ownership logic for three conditional surfaces —
root `PROTOCOL.md`, the `SPEC/v1` contract tree, and the
`.claude/.framework-version` marker — is a **nine-dimensional decision
space implemented as `if` branches spread across three canonical
scripts**. Branches encode contradictory answers to the same question and
nothing detects it.

This is not a hypothesis. In S296 a cross-model review rail ran **11
consecutive rounds** on this logic: **35 literal findings**, roughly half
of the later ones being **regressions caused by the previous round's
fix**, with no convergence. The 45-check e2e stayed green throughout — it
covers 8 scenarios.

**Proposal:** make the space explicit (a table), make the decision a
single pure function, make the table the test suite, and point the review
rail at the TABLE rather than at the diff.

## 2. What W0 already delivered (committed, free surface)

| Artifact | Content |
|---|---|
| `docs/ownership-decision-table.md` | 9 dimensions, 11 named pruning rules with reasons, disposition ledger for all 35 findings |
| `scripts/tests/ownership_table.tsv` | 61 rows, the single source of truth |
| `scripts/tests/test-ownership-table.sh` | e2e: real scripts, zero mock, per-cell timeout |
| `scripts/tests/ownership-baseline-map.txt` | 50 green / 11 red — every red attributed to a real defect |

### 2.1 Findings the table produced that 11 review rounds did not

1. **Three of the five pruning rules the plan itself declared "already
   known" are false** (doc §4.1). One would have deleted the still-open
   r11-F1 cell from the space entirely.
2. **`_refresh_protocol_pointer` lacks the non-regular-destination and
   leaf-symlink guards** that `spec` and `marker` both acquired (§5.1).
   It is the one surface written with `cat >`.
3. **The FIFO does not hang in the marker route.** It hangs in a
   tree-walking scanner that runs *before* any refresh (§5.7). Proved in
   isolation with positive and negative controls. Consequence: the
   existing special-file guards are **masked** — no e2e can reach them,
   so green there proves nothing.
4. **The continuity line inside the ancestor-symlink guard is dead code**
   (§5.8): the relpath sanitizer drops the record at load time, before
   the check runs.
5. **`HASH_TARGET` is never the correct answer** across 61 rows — and it
   is the generator's default when no override is supplied.

## 3. The enum under debate (draft)

**Verdict:** `DELIVER` · `REFRESH` · `PRESERVE_OWNED` · `PRESERVE_UNOWNED`
· `OMIT_RECORD` · `ABORT_SURFACE`

**Hash source:** `HASH_TARGET` · `HASH_SOURCE` · `HASH_PRIOR_RECORD` ·
`HASH_CANONICAL_POINTER` · `HASH_NONE` · `LINK_RECORD`

The outcome of a cell is the **pair**. Every one of the 35 findings was a
cell whose pair was wrong.

## 4. Two inconsistencies committed ON PURPOSE

Writing the decision function exposed these. Resolving them unilaterally
would pre-decide what this debate exists to settle.

1. **The table disagrees with itself about `OMIT_RECORD`.** Some rows with
   a prior record expect `OMIT_RECORD`; others with a prior record expect
   `PRESERVE_UNOWNED`. 61 hand-written rows never had to agree; a function
   has to.
2. **`OWN-0018` and `OWN-0020` have identical dimensions and opposite
   outcomes**, separated only by prose in the `note` column.

## 5. The W2 proposal — three claims to attack

### C1. `OMIT_RECORD` is not an independent verdict (OQ-9)
Every `OMIT_RECORD` row is a row that would read `PRESERVE_UNOWNED` had no
prior record existed. `prior_record` is already a column. If this holds,
the verdict enum loses a member — and a redundant enum member is precisely
where two branches disagree about which one applies.

### C2. `ABORT_SURFACE` is not a verdict, it is an execution failure
A failed backup is not a property of the nine dimensions; it is the
**caller failing to carry out a verdict it was given**. Proposed split:

```
decision  -> _ownership_verdict()   pure, total, unit-testable
execution -> the caller, which may fail and must say so
```

If accepted, **OQ-1 and OQ-2 dissolve**: `ABORT_SURFACE` becomes the
failure mode of `REFRESH`/`DELIVER` and inherits their `hash_source`.

Combined with C1 this leaves **four verdicts**, not six.

### C3. Prose in `note` is load-bearing and must become values (OQ-7)
The `note` column already carries `fault=` and would need `extra=`. A
decision function cannot read prose. Proposal: `live_content` gains
`legacy_pristine_partial` (a tree carrying an entry the fingerprint cannot
hash), and `fault` either becomes a real column or its rows leave scope.

### Proposed signature and home

```
_ownership_verdict <surface> <prior_record> <live_type> <live_content> \
                   <source_has> <mode> <ceremony> <operation> <skip_requested>
# stdout: "<VERDICT> <HASH_SOURCE>"
```

Pure: no filesystem, no globals, no environment. Home:
`scripts/_framework_manifest_set.sh` (**already** canonical-guarded).

A new library file would be a NEW canonical path, requiring a
`_CANONICAL_GUARDS` entry and therefore a **kernel ceremony**. Preference
for the existing library stands absent a reasoned veto; **a veto escalates
to the Owner in the morning and does not become an overnight kernel
ceremony.**

### Why purity is the point
The same TSV then drives **two** oracles: a unit one in milliseconds
(does the DECISION match the model?) and the existing e2e in ~25 minutes
(do the callers OBSERVE correctly and EXECUTE the verdict?). They fail for
different reasons and both are needed. S296 had only the slow one, at one
cell per ~40-minute round — a loop too long to converge in.

## 6. Remaining open questions

`OQ-3` version reporting under an external-target `--pin` downgrade ·
`OQ-4` splitting the overloaded `FMS_PROTOCOL_HASH` ·
`OQ-5` where the function lives (see above) ·
`OQ-6` should `install` honour `--skip` ·
`OQ-8` does the table cover readers or only writers.

Full text in `docs/ownership-decision-table.md` §6.

## 7. Anti-goal

This is **not** "fix the 4 open findings from round 11". Fixing branch by
branch **is** the loop. Those four become table rows like the other 31.
