# workflows-fixes.patch — NOTES (ceremony 2, PLAN-162)

Consolidated fix for the 3 red scheduled workflows. Patch built and validated
in an overlay clone at HEAD `9c63750`; applies clean on a fresh
`git clone --local` of the live repo. **3 files changed, 55 insertions(+),
15 deletions(-).** No live-tree canonical file was touched.

---

## Edit 1 — `.github/workflows/tournament.yml` (step "Cost projection (dry-run gate)", ~line 122)

**Bug:** `2>&1 | tee projection.txt` merges the runner's stderr banner into
stdout ahead of the JSON document, so the follow-up
`json.load(open('projection.txt'))` dies with `JSONDecodeError line 2 col 1`.

**Before**
```yaml
            --budget-usd "$TOURNAMENT_BUDGET_USD" \
            2>&1 | tee projection.txt
```

**After**
```yaml
            --budget-usd "$TOURNAMENT_BUDGET_USD" \
            | tee projection.txt
```

Plus a 4-line NOTE comment above the extractor explaining why stderr is
deliberately not merged (it still reaches the job log directly). The leading
`|` rides the preceding backslash continuation — bash sees one pipeline;
`set -euo pipefail` semantics unchanged.

## Edit 2 — `.github/workflows/reality-ledger.yml` (step "Update or open GitHub issue (idempotent)", inserted before `if [ -n "$EXISTING" ]` at old line 157)

**Bug:** `gh issue create --label "reality-ledger,advisory"` hard-fails when
either label does not exist in the repo (fresh installation ships neither).

**Inserted** (with a 4-line comment):
```bash
gh label create "reality-ledger" --color "1D76DB" --force 2>/dev/null || true
gh label create "advisory" --color "FBCA04" --force 2>/dev/null || true
```

`--force` updates an existing label instead of erroring, so re-runs are
idempotent; `2>/dev/null || true` keeps label cosmetics from ever failing the
advisory step. (`gh label create --color` takes bare hex, no `#`.)

## Edit 3a — `.github/workflows/mutation-gate.yml` (checkout, lines 74-75)

**Bug:** stale checkout pin — the 4th "invisible red scheduled gate";
`supply-chain-watch` red since 2026-07-20.

**Before**
```yaml
        # SHA-pinned (PLAN-050 C12) — actions/checkout@v4.
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4
```

**After**
```yaml
        # SHA-pinned (PLAN-050 C12) — actions/checkout@v6.0.2.
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2 (repo standard)
```

`de0fac2e…` is the pin used by every other workflow in the repo (verified by
grep: chaos, coverage, release, perf-profile, translations-drift, tournament,
actionlint, adapter-live, benchmarks, `_README.md` §standard list).

## Edit 3b — mutation-gate.yml, step "compute kill-rate + AC2b superset check + AC4 enforce + AC5 row"

**Bug:** the step parsed `mutation-results-<mod>.txt` with
`killed[:\s]+(\d+)` / `survived[:\s]+(\d+)`. mutmut 2.x `results` output
NEVER prints a "killed: N" line, and its survivor header `Survived 🙁 (38)`
defeats the survived regex (emoji + parens between the word and the digits) —
so every leg computed 0/0 and reported `n/a`.

**Fix (exact to diagnosis):** parse `mutation-junit-<mod>.xml` (already
produced by the mutation-run step via `mutmut junitxml`) with
`xml.etree.ElementTree`: `tests` attr == total mutants, `failures` attr ==
survived mutants, `killed = total - survived`. Root-tag handling covers both
a bare `<testsuite>` root and the `<testsuites>` wrapper that mutmut 2.x's
`junit_xml` dependency actually emits (aggregate attrs on the wrapper, single
inner suite — either path yields the same numbers here). The
`jx.exists() and jx.stat().st_size` guard keeps a timed-out leg (absent or
truncated-to-empty XML) with `rate=None`, preserving the existing
partial/advisory path and the AC4 hard-fail for the enforce leg. `import re`
dropped (now unused); `os`/`sys`/`Path` retained (still used downstream).

**Known caveat (out of diagnosed scope, display-only):** on a *partial*
(timed-out) run, junit `tests` includes untested mutants with the default
`--untested-policy ignore`, so the advisory rate on a partial leg overcounts
killed. Harmless because: the row is already labeled `partial(...)`, AC4
hard-fails the enforce leg on any non-full coverage before the rate matters,
and advisory legs only warn. Flagged here per the S291
measurement-must-list-its-inputs lesson (`mutmut "100%" with 72/90 untested`
class).

## Edit 3c — mutation-gate.yml, step "redact artifact before upload" (~old lines 213-219)

**Bug:** `python3 .claude/scripts/backup-audit.py --redact "$SRC" || true` —
backup-audit.py has **no `--redact` flag**, so the call failed on every run
and `|| true` swallowed it: the artifact was uploaded **unredacted** on every
scheduled run.

**Fix:** inline `python3 - "$SRC" <<'PY'` that does
`sys.path.insert(0, ".claude/hooks/_lib")`, imports `redact_secrets` from the
canonical `redact.py` (stdlib-only module — safe standalone import), and
rewrites the `.txt` in place with `max_chars=0` (no preview truncation).
**No `|| true`:** an actual redaction failure (import error, IO error,
redactor exception) exits non-zero and fails the step — fail-closed. A
missing file (timed-out leg produced no txt) is handled *inside* the script
as a success print, so `if: always()` legs without artifacts stay green.

**Known caveat:** `redact_secrets` is whitespace-collapsing by contract
(docstring invariant), so the redacted txt artifact becomes a single
collapsed line. Nothing parses that txt anymore (Edit 3b moved the kill-rate
source to the junit XML); it is a human-readable advisory artifact only. The
junit XML itself is uploaded unredacted — unchanged from the prior step's
scope (it contains mutant diffs of public source, and redacting it was never
part of the old step either).

---

## Validations run (all in the overlay / fresh clone, never the live tree)

| Check | Invocation | Result |
|---|---|---|
| YAML parse ×3 | `yaml.safe_load` on each edited file (pyyaml present locally) | `yaml OK` ×3 |
| actionlint (pre-patch overlay) | `actionlint tournament.yml reality-ledger.yml mutation-gate.yml` | **0 findings** (actionlint also shellchecks `run:` blocks — shellcheck at `/opt/homebrew/bin/shellcheck`) |
| shellcheck -S warning, modified blocks only | 3 run blocks extracted via pyyaml, `${{ … }}` → `GHEXPR`, `#!/bin/bash` header | **ALL CLEAN** (tournament-costproj.sh 1018c, ledger-issue.sh 2986c, mutgate-redact.sh 858c) |
| compute script, behavioral (verbatim heredoc extracted from the edited file with awk) | 4 fixture cases | case1 `<testsuites>` 38/90 survived, full, enforce → **exit 1**, row `redact\|52/90\|57.8%\|yes\|full` ✔; case2 5/90 → **exit 0**, `94.4%` ✔; case3 empty XML + partial, advisory → **exit 0**, `::warning`, row `hmac\|0/0\|n/a\|no\|partial(0/?)` ✔; case4 empty XML + partial, enforce → **exit 1** AC4 hard-fail ✔ |
| redact inline script, behavioral | run byte-identical from overlay root against a txt containing `token=sk-ant-…` | exit 0, `[REDACTED]` in place, `grep -c sk-ant-` → 0; missing-file path exit 0 with "nothing to redact" |
| stderr-unmerge concept | banner-on-stderr + JSON-on-stdout through `\| tee projection.txt` then `json.load` | `projected_usd=1.23` — parse OK |
| Patch integrity | `git diff > workflows-fixes.patch` (128 lines); fresh `git clone --local` at `9c63750`; `git apply --check` | **CLEAN** |
| Post-apply re-validation | `git apply` in the fresh clone → actionlint ×3 + yaml ×3 | **0 findings / yaml OK ×3** |

## Apply instructions (CEO / ceremony)

```
git apply .claude/plans/PLAN-162/ceremony-2-staged/workflows-fixes.patch
```

Built against `9c63750`. Touches only `.github/workflows/{tournament,reality-ledger,mutation-gate}.yml`.

---

# APPENDIX — Codex r2 fold: malformed JUnit is an UNREPORTED rate, not a crash (P2)

> "The producer runs `mutmut junitxml > ... || true`, so a failed or
> interrupted export can leave a NON-EMPTY but MALFORMED XML file. `ET.parse`
> then raises and fails even advisory legs before they can emit the intended
> partial warning and leg row. Catch parse/value errors and leave `rate` unset
> so the existing AC4/advisory handling decides the outcome."

## 1. Confirmed behaviorally, and the damage is worse than "fails"

The compute step's Python heredoc was extracted from `mutation-gate.yml` and
run as a subprocess against fixture trees — 11 cases, 7 of them the
pre-existing behaviour, 4 the new vectors. Before the fix:

```
[FAIL] truncated_advisory   rc=1 (want 0) row=False
[FAIL] truncated_enforce    rc=1 (want 1) row=False
[FAIL] garbage_advisory     rc=1 (want 0) row=False
[FAIL] garbage_enforce      rc=1 (want 1) row=False
xml.etree.ElementTree.ParseError: unclosed token: line 1, column 22
```

`row=False` is the part the finding understates. The step died BEFORE writing
`leg-<mod>.row`, so the aggregate job did not merely see "n/a" — it lost the
leg entirely. The `truncated_enforce` case also exits 1 either way, but with
no `::error::` annotation and no summary line, so a real enforce failure and
a crashed parse were indistinguishable in the run log.

Two malformed shapes were used, both of which `> file || true` can actually
produce: a TRUNCATED document (exporter killed mid-write, e.g. by the same
timeout that sets `coverage.flag=partial`) and a TRACEBACK written to stdout
by a failing exporter.

## 2. The fix

`ET.parse` and the two `int()` calls are wrapped, catching
`ET.ParseError`, `ValueError` and `OSError`:

- `ParseError` — the malformed document (the finding).
- `ValueError` — a well-formed document whose `tests`/`failures` are not
  integers. Same class: the file exists but does not answer the question.
- `OSError` — the file exists but cannot be read.
- `TypeError` is deliberately NOT caught: that would mean this code is wrong,
  not the input.

The handler RESETS `killed`/`survived`/`total` to 0 as well as `rate` to
`None`. Without the reset a partially-parsed document could leave a real
number in `killed` and have it printed in the leg row as `killed/total`,
which reads as a measurement rather than as an absence — the S291 lesson
about estimators that report a plausible subset instead of an error.

It also prints a specific `::warning::` naming the exception, so "unreported"
is distinguishable from "the leg timed out", which is the other way `rate`
ends up `None`.

Everything downstream is unchanged: `rate is None` is a state both legs
already handle — advisory warns and still writes its row, enforce hard-fails
via AC4.

## 3. Verification

| check | result |
|---|---|
| red-first | **7/11** cases pass (the 4 malformed vectors traceback, no row) |
| after the fix | **11/11** cases pass |
| re-extracted from the APPLIED patch in a clean clone | **11/11** |
| malformed advisory row content | `MOD\|0/0\|n/a\|no\|partial(0/?)` — an honest "unreported", not a fake measurement |
| malformed advisory output | two warnings: the specific `ParseError` diagnostic, then the pre-existing `produced no kill-rate` advisory |
| malformed enforce | exit 1 with `::error::redact leg did not report a kill-rate` — AC4, as designed |
| `actionlint` | OK on all three touched workflows |
| `test_ceo_boot_sched_red.py` (the only suite that reads these workflows) | **23 passed** |
| `git apply --check` on `main` @ `9c63750` | OK |

The 7 pre-existing cases (good XML, `<testsuites>` root, absent XML in both
legs, empty XML, below-floor enforce) were kept as the regression half — they
pass before and after, which is what makes the 4 new rows meaningful.

## 4. Concern for the Owner

The harness that proves this (`extract_compute.py` + `run_compute_cases.py`,
in the session scratchpad) is throwaway: it re-extracts the heredoc from the
YAML by regex and runs it. There is no permanent test in the repo pinning the
compute step's behaviour, so the next edit to that heredoc has nothing to
break. Worth a small `scripts/tests/` harness if the Owner wants this class
gated rather than reviewed — it is the same "scheduled gate red and nobody
notices" family that produced this ticket in the first place.

---

# APPENDIX 2 — Codex r3 fold: failing the redaction STEP is not fail-closed (P1)

Round 3 of the cross-vendor review, against `workflows-fixes.patch:103-113`
(Edit 3c, the "redact artifact before upload" step):

> "If importing the redactor, reading the file, or rewriting it fails, this
> script exits nonzero but leaves the ORIGINAL file intact; the following
> upload step has `if: always()` and still uploads that UNREDACTED file.
> Failing the redaction step alone is not fail-closed — upload must be
> conditioned on success or the source must be removed/quarantined on error."

The finding is correct and it lands on MY r1 fix. Edit 3c's own note claimed
"Fail-closed: a redaction failure MUST fail this step, so there is no
`|| true`" — which conflated *the step goes red* with *the secret stays in*.
Those are different properties, and only the second one matters here: the
uploader four lines below runs `if: always()`, so the red step and the leaked
artifact happen in the same run. Third instance this session of the same
class — a control that reports failure while the thing it guards proceeds.

## 1. Red control — the pre-fix script, measured

`test_redact_failclosed.py` (session scratchpad) runs the heredoc EXACTLY as
the workflow does: a subprocess, path as `argv[1]`, inside a scratch tree
carrying a fake `.claude/hooks/_lib/redact.py`, so the breakage arrives
through the import the way a real one would. Against the r1 script:

```
OK happy_path_redacts_in_place
XX redactor_raises_source_removed          rc=1 exists=True leftovers=['mutation-results-hooks.txt']
XX import_syntaxerror_source_removed       rc=1 exists=True leftovers=['mutation-results-hooks.txt']
XX redactor_missing_source_removed         rc=1 exists=True leftovers=['mutation-results-hooks.txt']
XX redactor_symbol_missing_source_removed  rc=1 exists=True leftovers=['mutation-results-hooks.txt']
OK missing_file_is_not_a_failure
OK no_redacted_tempfile_left_behind
FAILS=4 / 7
```

`rc=1 exists=True` is the finding in two fields: the step fails, and the
unredacted file is still sitting where `upload-artifact` will find it.

## 2. The fix — two independent rails, and one hazard folded in

**Rail 1 (primary): the source is REMOVED on any failure** — import, read,
redact or write. That outcome does not depend on the uploader's `if:`
expression, which is what makes it a rail rather than an agreement between
two steps that a later edit can quietly break. `quarantine()` unlinks, prints
a `::error::`, and exits 1.

**Rail 2 (independent): a separate `quarantine unredacted results` step**
gated on `steps.redact.outcome != 'success'`. This covers the case rail 1
structurally cannot — the process never reaching its own error handler
(OOM-kill, step timeout).

Deliberately NOT done: gating the upload step itself. That would also drop
`leg-*.row`, and the r2 fix in Appendix 1 exists precisely so a broken leg
reports "unreported" to the aggregate instead of vanishing from it. Closing
this finding by re-opening that one is not a fix.

**Folded in beyond the finding:** the write is now TEMP-THEN-REPLACE, not
in-place. `Path.write_text` truncates before writing, so a crash mid-write
left a SHORT file whose surviving prefix was still unredacted — a partial
leak that both rails above would have called a success. `os.replace` is
atomic: the file is either fully redacted or absent.

## 3. Verification — same harness, the overlay AND the applied patch

```
FAILS=0 / 7   (extracted from wf-overlay/.github/workflows/mutation-gate.yml)
FAILS=0 / 7   (extracted from a clean clone @9c63750 with the patch applied)
```

The 3 pre-existing rows (happy path, missing file, no temp file) pass before
and after — they are the regression half that makes the 4 new rows mean
something. `redact_secrets` is keyword-only in `max_chars`
(`_lib/redact.py:120`); the call site was already correct and is unchanged.

Patch scope is unchanged: `mutation-gate.yml` only. `reality-ledger.yml` and
`tournament.yml` regenerate to the SAME blobs as the r2 patch (`926323d`,
`d72a583`) — the check that this fold did not widen the diff.

## 4. Concern for the Owner

Rail 2 reads `steps.redact.outcome`, which requires the `id: redact` added in
this fold. If someone later renames or removes that `id`, the expression
silently evaluates to empty, `'' != 'success'` is TRUE, and the quarantine
step runs on EVERY leg — deleting the results file from successful runs too.
That fails SAFE (no leak; the artifact just loses one of three files) but it
is noisy and would read as a mutation-gate bug rather than a workflow bug.
The Appendix-1 concern still stands and now covers this step too: there is no
permanent test in the repo pinning either heredoc's behaviour.

---

# Appendix 2 — Codex S292 round 4 fold (mutation-gate kill-rate, 2x P2)

Round 4 returned two P2s against `mutation-gate.yml`. They are independent
bugs with the same consequence: **the gate reported a kill-rate it had not
measured**, and the enforcing leg could pass its 80% floor on it.

## 1. P2 — a FAILED mutmut run was scored from the restored cache

`.mutmut-cache` is restored by `actions/cache`, and `mutmut junitxml` reads
that DB, not this run. The old branch wrote `full` for every exit code except
124, so a run that died early (import error, missing dep, OOM) still exported
last week's mutants and the leg scored them as this run's result.

### The trap that had to be avoided

The obvious fix — treat `RC != 0` as failure — would have painted **every leg
red**. mutmut's exit code is a BIT MASK, verified against the installed
mutmut 2.5.1 (`compute_exit_code()` in `mutmut/__init__.py`):

```
0 = all killed   1 = FATAL ERROR   2 = survivors   4 = timeouts   8 = suspicious
                 (bit-ORed together)
```

A healthy redact leg sits near 96%, i.e. it has survivors, i.e. it exits **2**
on every green run. This was checked before writing the fix, not after.

### The classifier

```
124            -> partial   (GNU timeout: the existing soft-cap path)
<=15 and even  -> full      (a COMPLETED run; bit 0 clear)
otherwise      -> failed    (bit 0 = mutmut's own fatal flag; >15 is not a
                             mutmut code at all: 127 not-found, 137 OOM, 143 TERM)
```

Behavioral test over all 16 mutmut codes plus 124/126/127/137/143/255:
**22/22 correct**. On `failed` the exporter is not invoked at all, and the
compute step refuses to read a junit even if one reaches the workspace — two
independent rails, same reason as the r3 redaction fix. The leg still emits its
row (the r2 fix: a broken leg reports "unreported", it does not vanish).

## 2. P2 — unresolved mutants were counted as KILLED

`killed = total - survived` counts every mutant mutmut did NOT resolve as
killed. Worse, the workflow called `mutmut junitxml` with no policy flags, and
both `--suspicious-policy` and `--untested-policy` default to `ignore`, which
renders an UNRESOLVED mutant as a testcase with no failure/error/skip element
— that is, as a PASS, that is, as killed.

### Measured, on mutmut 2.5.1, one deliberately capped run

```
mutmut results  ->  Survived (1), Untested/skipped (10)

junitxml variant                                    tests  fail  err  skip
default (what the workflow called)                     25     1    0     0
--suspicious-policy=error --untested-policy=error      22     1    8     0
```

The default XML carries `errors=0` while ten mutants went untested: **the
information is not in the file**. So the two halves of this fix are not
alternatives, they are both required:

| junitxml variant | `total - survived` | `total - survived - errors - skipped` |
|---|---|---|
| default | 96.0% | 96.0% (inert — nothing to subtract) |
| with error policies | 95.5% | **59.1%** |

The right-hand column is a paired comparison over the SAME file: two formulas,
one input.

Unresolved mutants stay in the DENOMINATOR on purpose. Dividing by the resolved
set instead would let a leg that resolved three mutants and killed three of
them report 100%; keeping `total` whole means an unresolved mutant can only
ever LOWER the rate, which is the direction a floor gate must fail in.

## 3. Verification

Twelve behavioral cases, run against the step body **extracted from the shipped
YAML** (not a copy), in a throwaway workspace with synthetic junit documents:

```
r4 workflow    ->  12/12 pass
pre-r4 (staged) ->   4/12 pass
```

The eight pre-r4 failures are the point. Two of them are not cosmetic:

- `C6` — the ENFORCE leg **passed** at a reported 96% whose true rate is 66%
  (100 mutants, 4 survived, 30 unresolved). The 80% floor was clearable with a
  rate inflated by mutants nobody tested.
- `B1` — a failed run with a stale junit present reported **99.0%**.

Regression rows (malformed junit, absent junit, empty junit) pass before and
after; two more fail pre-r4 only on the new sixth column, which is expected.

Shellcheck `-S warning` (the CI severity) is clean on all 8 extracted run
blocks. The workflow parses as YAML; job and step structure unchanged.
`git apply --check` passes against a clean `--local` clone of `main`.

## 4. Surface change

The AC5 table gains an `unresolved` column and a `run-failed` coverage value,
and the machine-readable `leg-<mod>.row` gains a sixth field. Producer and
consumer are in the same workflow run and both are updated here; a repo-wide
grep found no other consumer of either format.

## 5. Concerns for the Owner

1. **This can turn the redact leg red — and if it does, that is a TRUE red.**
   The gate's reported 96.7% was computed by the inflating formula. The real
   rate is 96.7% minus whatever fraction of mutants is unresolved. There is
   16.7pp of headroom over the 80% floor; if the real unresolved fraction
   exceeds that, the next scheduled run hard-fails. That is the gate finally
   measuring what it always claimed to measure, but it should not arrive as a
   surprise at 04:17 UTC on a Monday.
2. **Still no permanent test in the repo** pinning either heredoc's behaviour.
   The 12 cases live in the session scratchpad, like the r3 redaction cases
   before them. Appendix 1's concern stands and now covers three steps.
3. **Pre-existing, NOT fixed here (deliberately):** line 84 of
   `mutation-gate.yml` says `SHA-pinned actions/cache@v4.2.0` while the pin two
   lines below is `27d5ce7f...  # v5.0.5`. It is on `main` already (a Dependabot
   bump moved the pin and left the comment), it is outside this round's three
   findings, and folding an unrelated edit into a signed ceremony patch is
   exactly what scope discipline forbids. Worth a follow-up: a stale
   version claim next to a supply-chain pin is the class `supply-chain-watch`
   exists to catch.
