# DESIGN — pack `memdelta-flake` (S340)

Base `ba15c718f8cb1ca37e8b909ddb321aa5bf78b1a9`. One touched path, FREE by the
oracle:

```
$ python3 .claude/hooks/check_canonical_edit.py --is-canonical \
      .claude/hooks/tests/test_session_end_memory_delta.py
.claude/hooks/tests/test_session_end_memory_delta.py	0
```

No production file is edited. `.claude/hooks/SessionEnd.py` is a KERNEL path and
this pack does not touch it — see §3.

## 0. The failure

`ba15c71` turned main RED in `hook-tests-dual-rail (0)` with ONE failure out of
6942 passing, in a 704 s job:

```
TestWireContract::test_no_paths_on_the_wire
AssertionError: 'zz-canary-topic.md' not found in []
```

The test is not wrong — that `assertIn` is the anti-vacuum canary that guards
the three `assertNotIn` checks below it, and it is the assertion that fired. Two
defects are in the INSTRUMENT around it.

## 1. Defect A — the positive control inherited production's wall clock

`_memory_delta_observed` caps its work with two budgets measured by
`time.monotonic()` — WALL clock, not CPU:

| constant | value | what it caps |
|---|---|---|
| `_MEMORY_DELTA_SCAN_BUDGET_MS` | 50 | the stat pass over the memory dir |
| `_MEMORY_DELTA_ANCHOR_BUDGET_MS` | 100 | the HMAC-verifying chain reverse-scan |

**Two independent routes reach `names == []`**, both measured (probe
`probe_routes.py`, output verbatim in EVIDENCE §A):

| route | starved | `outcome` | `anchor_source` | `names` |
|---|---|---|---|---|
| healthy | — | `written` | `chain` | 2 names |
| (a) | scan budget | `error` | `chain` | `[]` |
| (b) | anchor budget | `start_unknown` | `none` | `[]` |

Route (b) is the one the brief attributed to "unresolved anchor" generically: the
anchor can be unresolved *because its own 100 ms wall budget blew*. So curing
only the scan budget would have left the more expensive channel (HMAC over the
log) open. **Both are injected.**

**Calibration, measured not guessed.** One full observation (2 topics + signed
anchor), n=30 on this machine: **p50 0.331 ms, max 7.932 ms**. Production's
50 ms therefore survives a runner only **~6×** slower than the worst local
observation — inside this repo's own documented drift envelope (hook p50 77 ms
local vs 209→435 ms in CI, CLAUDE.md §S327). The CI red is fully explained; it
is not a mystery flake.

My first value (60 s, ~7.5k×) was **REFUTED by my own positive control** at a
×20000 clock (EVIDENCE §C, control 3): the guard fired with
`outcome='error' … names=['MEMORY.md']` — exhaustion *inside the sanitizer
loop*. Shipped value: `_TEST_WALL_BUDGET_MS = 3600000` (~450,000× headroom),
which stays 6 orders of magnitude below the mocked-clock sentinel.

### Where the seam belongs: `_DeltaBase`, not `TestWireContract`

Derived, not asserted: `_memory_delta_observed(` appears **once** in the whole
1513-line file — inside `_DeltaBase._observe`. It is the single call site for all
32 observation call sites. A flake caused by runner load is a property of every
observation, not of the wire tests, so a fix living in
`TestWireContract._emit_captured` would leave 30 other observations carrying a
failure mode they never meant to exercise. The seam is `_observe`.

`budget_ms=None` means "the caller owns the clock". That opt-out set was
**DERIVED, not recalled**: I applied the cure's exact inner-patch shape over the
whole file with a pytest plugin and read off the failures (EVIDENCE §B):

- `test_slow_final_stat_is_error` — sleeps 80 ms against the real 50 ms cap.
  Robust in the safe direction: a loaded runner only makes `sleep > budget`
  *more* true.
- `test_budget_exhaustion_is_not_written` — patches the constant to `-1`, so an
  inner injection would silently override its subject.

The other 58 tests passed unchanged. The three tests that mock `time.monotonic`
keep their teeth either way: they starve the CLOCK, not the constant. That
coupling is now pinned by `test_injected_budget_cannot_outrun_the_mocked_clock`,
which derives their `1e9` sentinel from their own source via `ast` (with an
anti-vacuum `assertTrue(sentinels)` so a rename cannot make the bound vacuous).

This weakens no assertion. The budget is a CAP, not a sleep: raising it lengthens
no run and removes a variable no test here intends to exercise.

## 2. Defect B — the failure was not diagnosable from the log

`'zz-canary-topic.md' not found in []` is produced **identically** by routes (a)
and (b) (EVIDENCE §C, controls 1 and 2 — byte-identical messages from two
different causes). `_delta_diag()` renders the discriminant:

```
outcome='start_unknown' anchor_source='none' files_count=2 modified_count=0 index_modified=False names=[]
```

No path and no slug in the message: those two are asserted ABSENT from the wire
in this same file, and a failure message is not the place to reintroduce them.

The guard also moved **upstream**: `_emit_captured` now refuses to hand a
degraded observation to the wire assertions, so the diagnosis appears at the
point of degradation instead of three assertions later. Both wire tests inherit
it (control 7: 2 failed, each naming the route).

## 3. Decision on the production timeout path — INTENDED, and pinned

The brief asks whether `out["names"]` being left `[]` on the budget-blown return
is a bug. **It is intended, and stronger than intended: copying `modified` there
would be a security regression.**

Evidence from the source, not from the docstring alone:

- `names` is not a view of `modified`. It is the **sanitized projection** built
  by a *later* loop through `_sanitize_memory_basename`, which drops hostile,
  NFKC-compat, role-preamble and injection-shaped basenames (many tests in
  `TestSpecSurface` exercise that gate). At the entry-loop deadline that loop has
  not run, so `[]` is the TRUE sanitized set.
- Production is already internally consistent: the *name-loop* deadline check
  DOES copy the names accepted so far (`out["names"] = names`), because by then
  they are sanitized. Only the pre-sanitizer returns leave `[]`.
- The docstring's "partial COUNTS, plural" (rail r6 P2-e) says counts on purpose.

Pinned by the new `test_budget_exhaustion_leaves_names_empty_not_raw`, which
asserts the key is PRESENT, `names == []`, and — anti-vacuum — that at least one
entry was already collected as modified (`modified_count >= 1`), so a
well-meant future "fix" that projects `modified` into `names` turns RED.

No production edit. Nothing in this pack asks the Owner to change `SessionEnd.py`.

## 4. Declared false-negative surface

- A runner >450,000× slower than this machine still starves the pass. The
  failure then NAMES the outcome, so it is diagnosable rather than mute. There
  is no wall-clock-free formulation available without editing the KERNEL.
- The injected budget cannot rescue a NON-clock degradation (unresolved anchor,
  chain gap): by design, control 7 stays RED. The cure makes such a failure
  legible, not invisible.
- `budget_ms=None` is a convention, not an enforced contract: a third test could
  adopt it and silently reinherit the 50 ms cap. It would not be vacuous —
  those tests assert `outcome == "error"`, which fails loudly if exhaustion
  stops firing — but it is a convention, and the docstring names the two
  legitimate holders so a third is a conscious act.
- The derivation of the opt-out set is a snapshot of `ba15c71`. A NEW
  budget-dependent test added later is not detected by any gate; the battery is
  the only detector.

## 5. Shape of the change

`+230 / -13` in one file, 9 anchored edits, all applied by
`apply-memdelta-flake.py --root <tree>` (plans every anchor before writing;
refuses on missing / ambiguous / already-applied). Two new tests, +2 imports
(`typing.Optional`, `textwrap`), one new module constant, one new `_DeltaBase`
helper. 60 → 62 tests.
