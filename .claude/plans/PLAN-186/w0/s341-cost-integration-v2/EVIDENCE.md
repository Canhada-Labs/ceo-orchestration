# EVIDENCE — pack `cost-integration-v2` (PLAN-186 W0, AC-1b) — S341

Base SHA: `ba15c718f8cb1ca37e8b909ddb321aa5bf78b1a9`
Shadow: `<scratchpad>/shadow-cost-integration-v2` (detached worktree at that SHA)
Pack: `<scratchpad>/packs/cost-integration-v2`

All paths below are relative to the shadow root; `<scratchpad>` stands for
this session's scratchpad directory (kept out of the file so nothing here
carries a personal absolute path into a commit).

---

## 0. Reproduction

```
$ git -C <repo> worktree add --detach <scratchpad>/shadow-cost-integration-v2 HEAD
HEAD is now at ba15c71 fix(PLAN-185-FOLLOWUP s340-doctor-fu7): ...

$ python3 apply-cost-integration-v2.py --root <SHADOW> --check-only
OK (check-only): 8 escrita(s) aplicavel(is).
  - .claude/scripts/tests/test_ceo_cost_integration.py
  - .claude/scripts/ceo-cost-transcripts.py
  - .claude/scripts/ceo-cost.py
  - .claude/scripts/budget-summary.py
  - .claude/scripts/tests/test_ceo_cost.py
  - .claude/scripts/tests/test_budget_summary.py
  - docs/cost-of-operation.md
  - .claude/scripts/tests/test_ceo_cost_transcripts.py

$ python3 apply-cost-integration-v2.py --root <SHADOW>
OK: 8 arquivo(s) escrito(s).
```

The refusal path is not decorative: the first epilog anchor in
`_derive_v2.py` was one line short of the real text, and the apply script
stopped the whole plan by NAME rather than writing 7 of 8 files —

```
RECUSA (1):
  - .claude/scripts/ceo-cost-transcripts.py: ancora ausente — '            "parses, its base input/output rates are used with ONE "\n '
nenhuma escrita realizada.
```

— cured by `_derive_v2c.py`, which re-derives that anchor from the file on
disk instead of from memory.

## 1. Oracle — every touched path is FREE

```
$ for p in <the 8 paths>; do python3 .claude/hooks/check_canonical_edit.py --is-canonical "$p"; done
.claude/scripts/ceo-cost-transcripts.py	0
.claude/scripts/ceo-cost.py	0
.claude/scripts/budget-summary.py	0
.claude/scripts/tests/test_ceo_cost_integration.py	0
.claude/scripts/tests/test_ceo_cost.py	0
.claude/scripts/tests/test_budget_summary.py	0
.claude/scripts/tests/test_ceo_cost_transcripts.py	0
docs/cost-of-operation.md	0
```

`canonical_paths` is EMPTY. No GPG ceremony is required for this pack.

## 2. Battery — run AFTER the last edit

The last edit to the shadow was the final `apply-cost-integration-v2.py
--root <SHADOW>` run, made on a freshly-reset worktree (`git checkout -- .`
+ `rm` of the untracked new test, `git status --porcelain` empty) after every
positive control in this file had been armed and disarmed. Everything in this
section ran after that -- including the gates, which is not a formality: the
round-2 [P1] was `check-test-env-hygiene.py` going rc 1 on an edit made after
an earlier, green, run of the same gate.

```
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
    .claude/scripts/tests/test_ceo_cost_integration.py \
    .claude/scripts/tests/test_ceo_cost.py \
    .claude/scripts/tests/test_budget_summary.py \
    .claude/scripts/tests/test_ceo_cost_transcripts.py
........................................................................ [ 50%]
......................................................................   [100%]
142 passed in 0.59s
```

(132 before the rail cures; +6 in round 1, +4 in round 2.)

(The task's battery names the first three files; the fourth is added because
v2 touches it — cure B replaces a test there that asserted the defect.)

```
$ python3 .claude/scripts/check-test-env-hygiene.py            ; rc=0
OK: test-env hygiene clean (337 flagged files, all allowlisted).

$ python3 .claude/scripts/check_contamination.py               ; rc=0
✓ No contamination outside allowed zones

$ bash .claude/scripts/validate-governance.sh                  ; rc=0
  Errors:   0
  Warnings: 65
PASS: Governance files validated.

$ python3 .claude/scripts/check-installer-write-safety.py      ; rc=0
OK: every blocking site is recorded in .../installer-write-safety-baseline.txt
```

`check-installer-write-safety.py` is reported for completeness only: **this
pack touches no file under `scripts/`** — the four code paths are all under
`.claude/scripts/`, which that census does not cover. The rc-0 above is the
untouched baseline, not a property of this pack.

---

## 3. Cure A — positive control

**Control construction.** `controls/control-A-v1-apply.py` is the v1 apply
script with `PAYLOAD_DIR` repointed at v2's payload: the v1 EDITS (finding A
un-cured) applied over the v2 test file (the 7 new A tests present). That
reproduces the MECHANISM under review — the three v1 suppressions — rather
than a look-alike.

```
$ git checkout -- . && rm -f .claude/scripts/tests/test_ceo_cost_integration.py
$ python3 controls/control-A-v1-apply.py --root <SHADOW>
OK: 7 arquivo(s) escrito(s).

$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
    .claude/scripts/tests/test_ceo_cost_integration.py \
    -k "under_transcripts_is_named or env_requested_benchmarks or under_both_is_not_dropped"
...
>       self.assertIn("--native is an AUDIT-side cross-check", err)
E       AssertionError: '--native is an AUDIT-side cross-check' not found in ''
...
FAILED ...::test_benchmarks_under_transcripts_is_named_not_swallowed
FAILED ...::test_by_wave_under_transcripts_is_named_not_swallowed
FAILED ...::test_env_requested_benchmarks_is_also_named
FAILED ...::test_native_under_transcripts_is_named_not_swallowed
4 failed, 3 passed, 39 deselected in 0.20s
```

`not found in ''` is the refuter's claim reproduced in bytes: **empty
stderr**. The 3 that pass are the deliberate negative controls
(`*_under_both_is_not_dropped`) — they must be green on BOTH trees, because
under `--source both` nothing is dropped and no note may fire.

With the cure (final shadow), all 7 are green — they are inside the 142.

**The cured code** (`.claude/scripts/budget-summary.py`):

```python
    if source == "transcripts":
        if benchmarks_on:
            sys.stderr.write(
                "budget-summary: --benchmarks is an AUDIT-side "
                "co-report and is dropped under --source transcripts; "
                "use --source both or audit\n"
            )
        benchmarks_on = False
```

plus the same shape for `native_on`, and, in the branch that skips
`rollup()`, the `--by-wave` note. The predicate is `benchmarks_on` /
`native_on` — the RESOLVED opt-in — so `CEO_BUDGET_BENCHMARKS=1` is named
too, which `test_env_requested_benchmarks_is_also_named` pins.

---

## 4. Cure B — positive control

**Control construction.** `controls/control-B-revert-gate.py` puts the exact
S340 unconditional block back on top of the fully-applied v2 shadow, leaving
the new tests in place. It refuses unless the cured block is found exactly
once.

```
$ python3 controls/control-B-revert-gate.py --root <SHADOW>
controle B armado: override incondicional restaurado

$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
    .claude/scripts/tests/test_ceo_cost_transcripts.py \
    -k "default_table or in_tree_default or refreshed_default"
...
E  AssertionError: 'NOT needed' not found in 'parsed from .../cost-table.yaml
   + ratified correction (claude-sonnet-5 $2/$10, 2026-09-01, CLAUDE.md e47bf5d)'
...
FAILED ...::test_default_table_already_ratified_is_not_corrected
FAILED ...::test_default_table_with_stale_row_gets_the_ratified_correction
FAILED ...::test_in_tree_default_table_is_already_ratified
3 failed, 1 passed, 22 deselected in 0.16s
```

The failure message IS the finding: against the REAL in-tree
`cost-table.yaml` the S340 code prints `ratified correction (claude-sonnet-5
$2/$10 ...)` while the file already says 2.00 / 10.00 — a correction that
corrects nothing.

`test_refreshed_default_table_is_not_masked` is the 1 that passes: it
exercises the branch both versions share (parsed differs → correct). Kept as
coverage of the surviving branch, declared as R9 in DESIGN rather than
counted as proof.

**Before / after, measured on the shipped table** (`load_pricing(None)`,
`.source`):

```
BASE   : parsed from .../cost-table.yaml + ratified correction (claude-sonnet-5 $2/$10, 2026-09-01, CLAUDE.md e47bf5d)
SHADOW : parsed from .../cost-table.yaml + ratified correction NOT needed for claude-sonnet-5 (the file already carries the ratified rate)
```

The numeric table is identical in both (2.00 / 10.00) — the defect was never
a wrong price, it was a report claiming a fix it did not make, and an
overwrite that would mask the next legitimate refresh.

**The false prose, on base:**

- `.claude/scripts/ceo-cost-transcripts.py:56` — "the in-tree
  ``cost-table.yaml`` still carries the pre-intro $3/$15 row pending that
  pack's land"
- `.claude/scripts/ceo-cost-transcripts.py:630` — "the in-tree file still
  carries the pre-intro $3/$15 row pending the sonnet5-pricing-fu pack's
  land"

Refuted by the tree itself, `.claude/scripts/cost-table.yaml:110-112`:

```yaml
  claude-sonnet-5:
    input_per_mtok: 2.00
    output_per_mtok: 10.00
```

Both sites are rewritten by this pack.

---

## 5. Cures the pair-rail added, and their controls

Three rounds ran. Rounds 1 and 2 each returned a `Full review comments:`
block; six findings were verified against the tree and cured, four verified
and declared. Full measurements per finding in `rail-round-1.md` and
`rail-round-2.md`; the verdict is the first line of each file, and
TREE-INTACT is asserted by comparing `git -C <SHADOW> diff | shasum -a 256`
before and after each round (r1 `d986e101…`, r2 `4b1f0ac1…`, r3
`b750919a…` — unchanged across each round).

`controls/control-r1-revert.py --which <p1|clock|carrier|legacy>` reverts one
cure at a time on an already-applied shadow and refuses unless the cured text
is found exactly once. Measured, one run per cure:

| cure | control | result |
|---|---|---|
| r1 [P1] stop the patch before the base teardown | `--which p1` | `SandboxTeardownOrderTests::test_base_restores_the_ambient_environment` FAILED (1 failed, 5 passed) |
| r1 [P2] one wall clock | `--which clock` | `OneWallClockTests` FAILED — `unexpectedly None : rollup() got no explicit clock` |
| r1 [P2] carrier domain | `--which carrier` | `AuditCarrierTests::test_log_path_alone_does_not_pin_this_caller` FAILED — `True is not false` |
| r2 [P1] legacy fallback | `--which legacy` | `LegacyAuditFallbackTests::test_legacy_fallback_refuses_the_pairing` FAILED — `True is not false : a legacy/out-of-project audit log was paired with this project's transcripts` |
| r2 [P1] env-hygiene | the gate itself | pre-cure `rc=1`, 4 NEW violations named; post-cure `rc=0` |

The r1 [P1] measurement that started it, from
`controls/probe-r1-p1-cleanup-order.py` on the reviewed tree:

```
HOME after teardown : /var/folders/.../ceo-hook-test-vzgxmrrz/home
leaked sandbox HOME : True
and it is deleted   : True
```

Two of these deserve to be read as lessons, not line items:

1. **The r1 carrier cure produced the r2 env-hygiene [P1].** The gate had
   printed `OK: test-env hygiene clean` earlier in this build — before the
   class that broke it existed. The rc that counts is the one after the last
   edit.
2. **The first r2 [P1] test was a weak control.** Un-cured it reported
   `available: false — transcripts root does not exist`: the tree never
   reached the pairing, so the control compared two refusals instead of a
   pairing against its refusal. Re-derived (`_derive_v2f.py`) to materialise a
   real corpus at the ambient root first. Existence is not reachability.

## 6. Residuals

Carried from v1: R1 (`env-inventory.json` — the gate is already RED on base
for 5 unrelated vars; this pack makes it 6), R2 (`ceo-boot.py`
`cost_24h_usd` still sums the audit log), R3 (`check-function-length.py`
advisory), R4 (2 of the new tests are green on base for a shape-agnostic
reason), R5 (v1's r3 cures never got a 4th round).

New, from the refuter's [P3]s, OUT of scope by instruction:
R6 (the ~90-line loader block is duplicated verbatim across the two
callers), R7 (CLI counter not re-derived for the new flags), R8
(`docs/agent-budget.md` does not mention `--source`).

New, from this pack: R9 (`test_refreshed_default_table_is_not_masked` is
green under the B control — see §4).

New, from the rail, verified and DECLARED rather than cured (reasons in
`rail-round-2.md`): R10 (an assistant line with `"usage": null` is dropped
without moving a counter, so `incomplete` can stay `false` — v1's D7 surface,
and widening it a fourth time is a live-corpus measurement), R11 (v1's D9
ledger annotation is added by `format_human()` only, so
`--json --validate-memory-claim` serialises an unlabelled verdict — curing it
changes the JSON shape of a governance check), R12 (`ceo-cost.main()` still
aggregates the audit ledger under `--source transcripts`) and R13 (the
shared transcripts block renders no `--since` label). R12/R13 come from
round 3, which returned NO [P1]; they are declared rather than cured
because the 3-round cap left nothing to review a last-minute cure —
`rail-round-3.md` carries the exact change for each.
