# DESIGN — pack `cost-integration-v2` (PLAN-186 W0, AC-1b) — S341

Base: `ba15c718f8cb1ca37e8b909ddb321aa5bf78b1a9` (HEAD at build time).
Every path is oracle-**0** (free); this pack is NOT an Owner GPG ceremony.

**v2 is v1 plus the two cures the refuter asked for, plus six the pair-rail
found on top of them.** The v1 design and evidence are kept verbatim next to
this file (`DESIGN-cost-integration-v1-inherited.md`,
`EVIDENCE-v1-inherited.md`); decisions D1–D10 and residuals R1–R5 stand
unrevised. This file describes only what v2 adds, and how it was derived.

Derivation, not hand-patching: `apply-cost-integration-v2.py` is v1's script
with three EDIT entries rewritten and sections 6, 7 and 8 appended, produced
by six refusing patchers kept next to it (`_derive_v2.py` … `_derive_v2f.py`,
applied in that order). Each refuses on a missing, ambiguous or
already-applied anchor and writes nothing on refusal; the shadow was reset to
a clean HEAD worktree and re-derived from scratch before every measurement.
`_derive_v2c.py` exists BECAUSE that property held: the first epilog anchor
in `_derive_v2.py` was written from memory and stopped one line short of the
file, and the apply script refused by NAME (`ancora ausente`) rather than
writing 7 of 8 files.

Sites: 7 from v1 + `.claude/scripts/tests/test_ceo_cost_transcripts.py`
(new in v2 — see cure B), = **8 touched paths**, all oracle-0.

---

## Cure A — an AUDIT-side block dropped under `--source transcripts` is
## dropped by NAME

**The finding (refuter, [P2] REAL).** In v1, `--source transcripts` set
`benchmarks_on = False` and `native_on = False` and skipped `rollup()`
entirely — so `--benchmarks`, `--native` and `--by-wave` vanished with
**rc 0 and an empty stderr**, while the two suppressions immediately below
in the same function (`CEO_NATIVE_COST_DISABLE`, `--plan-id`) each wrote a
named stderr line. The pack's own r1–r3 rounds had established the opposite
rule everywhere else it applied it (D6, D8, D9): *named refusal, never
silently swallowed*. v1 shipped the rule with a hole in the middle of the
function that states it.

**The cure.** One stderr line per dropped block, in the adjacent style,
emitted only when the block was actually REQUESTED:

| flag / env | where | line |
|---|---|---|
| `--benchmarks`, `CEO_BUDGET_BENCHMARKS=1` | after `benchmarks_on` is computed | `--benchmarks is an AUDIT-side co-report and is dropped under --source transcripts; use --source both or audit` |
| `--native`, `CEO_BUDGET_NATIVE=1` | after `native_on` is computed | `--native is an AUDIT-side cross-check and is dropped under --source transcripts; ...` |
| `--by-wave` | in the branch that skips `rollup()` | `--by-wave shapes the AUDIT rollup and is dropped under --source transcripts (the transcript corpus has no wave field); ...` |

Three decisions inside the cure:

- **The predicate is the resolved opt-in, not the flag.** Both co-reports
  have two doors (the flag and an env var). A note keyed on
  `args.benchmarks` alone would still swallow `CEO_BUDGET_BENCHMARKS=1`;
  keying it on `benchmarks_on` — the value the code actually acts on —
  cannot. `test_env_requested_benchmarks_is_also_named` is that door.
- **rc stays 0.** These are additive co-reports, so the shape is
  *suppress + say so* (the `CEO_NATIVE_COST_DISABLE` / `--plan-id` shape),
  not the *refuse* shape (rc 2) that v1 reserved for the cases where the
  printed number would be WRONG (`--plan-id` + transcripts,
  `--validate-memory-claim` + transcripts, `--stream` + transcripts).
- **One reason, named, per run.** The transcripts check sits BEFORE the
  `CEO_NATIVE_COST_DISABLE` check, so `--source transcripts` +
  `CEO_NATIVE_COST_DISABLE=1` prints the transcripts reason only. Both are
  true; the one printed is the one that fired first, and it is deterministic.

**Not fired where nothing is dropped.** Three control tests assert the notes
are ABSENT under `--source both` for the same three flags — a note that
fires when the block is still rendered would be a new defect, not a cure.

---

## Cure B — the "ratified correction" stops correcting nothing

**The finding (refuter, [P2] REAL — the S340 residual).**
`_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE` overwrote the parsed
`claude-sonnet-5` row UNCONDITIONALLY whenever `--pricing` was left at its
default, and appended `+ ratified correction (claude-sonnet-5 $2/$10, ...)`
to the `source` string every time. Since `b6dce78` the in-tree
`cost-table.yaml` (lines 110–112) **already carries 2.00 / 10.00**, so:

- today it is a numeric no-op that still prints a correction in every
  report — a fix that fixed nothing;
- tomorrow it silently masks a legitimate refresh of the table;
- and two prose sites (module docstring ~line 56, `--help` epilog ~line 940)
  asserted as fact that the in-tree file "still carries the pre-intro $3/$15
  row pending that pack's land" — **false since `b6dce78`**.

**The cure — gate, do not delete.** Deleting the override was the other route
offered. It is rejected: the override is the mechanism that keeps a stale
`cost-table.yaml` from repricing every Sonnet-5 report by +50 %, and it is
the ONLY place the ratified rate is asserted against the file. What was wrong
was not its existence but its unconditionality. So:

```
for mid in sorted(_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE):
    if _override_is_a_no_op(table.get(mid), override):   # parsed == ratified
        noop.append(mid); continue
    table[mid] = dict(override); applied.append("<mid> -> $<in>/$<out>")
```

and the `source` string now says which of the two happened:

- differs → `+ ratified correction (claude-sonnet-5 -> $2/$10; 2026-09-01, CLAUDE.md e47bf5d)`
- matches → `+ ratified correction NOT needed for claude-sonnet-5 (the file already carries the ratified rate)`

Decisions inside the cure:

- **The rate in the message is DERIVED from the override dict** (`$%g/$%g`
  over `input_per_mtok` / `output_per_mtok`), not recalled as the literal
  `$2/$10`. A second grafia of the ratified number in a format string is the
  exact drift that produced this finding one layer up.
- **`_override_is_a_no_op` fails toward APPLYING.** Missing row, non-numeric
  value, `bool` — any of them returns `False`, so the override still lands.
  A guard that swallowed the correction on a malformed row would trade a
  cosmetic defect for a pricing defect.
- **Tolerance is `1e-9`, not `==`.** The values come out of a mini-YAML
  parser as floats; exact equality on `2.00` happens to hold today and is
  not a property worth depending on.
- **Both prose sites are rewritten** to state what is true after `b6dce78`
  (the file already carries the row; the correction is conditional and
  currently a no-op) rather than a re-dated version of the same claim.

**The test that ties prose to tree.**
`test_in_tree_default_table_is_already_ratified` calls `load_pricing(None)`
against the REAL shipped `cost-table.yaml` and asserts the no-op branch. The
day someone legitimately edits that row, this test goes red and points at the
two prose sites that would then be wrong again. The three behavioural tests
next to it use a SYNTHETIC default table (`mock.patch.object(cct,
"_SCRIPT_DIR", ...)` — `_SCRIPT_DIR` is read at call time), so the *behaviour*
of the branch is not hostage to what the repo's table says today.

**The test v2 had to replace.** `test_load_pricing_default_applies_ratified_
sonnet5_override` (`test_ceo_cost_transcripts.py:160` on base) asserted
`assertIn("ratified correction", ...)` against the real default table — i.e.
it asserted the defect. Left alone it would have gone red on the cure. It is
replaced by the four tests above, which is why v2 touches an 8th path (and
why the battery adds that file). `from unittest import mock` is added to that
file's imports (it had none).

---

## Cures the pair-rail added (rounds 1 and 2)

The rail reviews the WHOLE uncommitted diff, so it also read the inherited v1
surface. Six findings were verified against the tree and cured; four were
verified and declared. Detail, measurements and per-cure positive controls in
`rail-round-1.md` / `rail-round-2.md`.

| round | finding | cure | control |
|---|---|---|---|
| r1 [P1] | `addCleanup` runs AFTER `tearDown`, so a cleanup-stopped `patch.dict` re-installs the sandbox snapshot on top of the ambient env — HOME left at a deleted dir (measured) | 3 sites stop the patch in an explicit `tearDown()` before `super().tearDown()` | `--which p1` |
| r1 [P2] | `_now` captured but never passed to `rollup()` — v1's own D10 half-delivered | `now=_now` | `--which clock` |
| r1 [P2] | `CEO_AUDIT_LOG_PATH` suppressed budget-summary's PRIMARY block although `default_audit_dir()` ignores it (measured: `audit_dir` identical) | `audit_source_is_pinned(..., carriers=...)`; the caller declares its domain | `--which carrier` |
| r2 [P1] | the carrier tests wrote `os.environ` directly — `check-test-env-hygiene.py` rc 1, 4 NEW violations | nested `patch.dict` everywhere | the gate itself (rc 1 → rc 0) |
| r2 [P1] | `default_log_path()`'s LEGACY fallback sets no carrier, so the D8 pairing guard passed a cross-project pair | the guard also asks whether the RESOLVED path left this project | `--which legacy` |
| r2 [P2] | `docs/cost-of-operation.md`'s monitoring recipe piped the SECONDARY total sixty lines after declaring the PRIMARY authoritative | both shown, PRIMARY first, with the reason | prose |

Two of these are worth naming as lessons rather than line items:

- **My r1 cure produced the r2 [P1].** `AuditCarrierTests` closed the carrier
  finding and broke a hard-fail gate in the same edit. The gate had printed
  `OK` earlier in the build — before that class existed. A battery run before
  the last edit is not a battery.
- **The first r2 [P1] test was a weak control.** Without the cure it reported
  `available: false — transcripts root does not exist`: the un-cured tree
  never reached the pairing, so the control compared two refusals rather than
  a pairing against its refusal. Re-derived (`_derive_v2f.py`) to materialise
  a real corpus at the ambient root first; the un-cured tree now publishes
  `available: true` and the control is a discriminant. Existence is not
  reachability.

## What v2 does NOT change

The refuter's three [P3]s are OUT of scope by instruction and are declared
as residuals, not silently absorbed:

- **R6 — the ~90-line loader block is duplicated verbatim** in `ceo-cost.py`
  and `budget-summary.py` (v1 D1 says only the loader may be per-caller
  because of the hyphenated filename; the block around it drifted into a
  copy). A shared `_lib` seam is a structural change, not a cure.
- **R7 — the CLI counter** in the surfaces that cite a number of scripts /
  flags was not re-derived for the new flags.
- **R8 — `docs/agent-budget.md`** does not mention `--source`.

Plus everything v1 already declared: R1 (`env-inventory.json` drift —
`CEO_COST_TRANSCRIPTS_DIR` makes the ALREADY-RED gate count 6 new instead of
5), R2 (`ceo-boot.py`'s `cost_24h_usd` still sums the audit log), R3
(`check-function-length.py` is advisory and both cured functions grew again),
R4 (two of the new tests are green on base for a shape-agnostic reason).

New in v2, from the rail: **R10** — an assistant line carrying
`"usage": null` passes the substring prefilter and is dropped without moving
any counter, so `incomplete` can stay `false` (v1's D7 surface; widening it a
fourth time is a live-corpus measurement, not a text fix). **R11** — v1's D9
"which ledger did I validate" annotation is added by `format_human()` only,
so `--json --validate-memory-claim` serialises an unlabelled verdict; curing
it changes the JSON shape of a governance check and belongs to whoever owns
the claim band.

Also new in v2: **R9 — `test_refreshed_default_table_is_not_masked` is GREEN under
the positive control**, because it exercises the branch both versions share
(parsed differs → correct). It is kept as coverage of the surviving branch,
and it is named here rather than counted as proof of the cure. The three
tests that ARE bound to the cure go red under the control.

From pair-rail round 3 (which returned NO [P1]), declared rather than
cured because the 3-round cap left no round to review a last-minute cure:
**R12** — `ceo-cost.main()` still reads and aggregates the audit ledger
under `--source transcripts`, so a malformed audit row can take down a
report that never asked for it (`budget-summary` already skips its
rollup). **R13** — the shared transcripts block renders no `--since`
label, so a transcripts-only report shows a total without its window.
The exact change for each is in `rail-round-3.md`.

## AC flip handed to the lander

Unchanged from v1: `.claude/plans/PLAN-186-orchestrator-operating-model.md`,
the AC-1b line (anchor in the structured return).
