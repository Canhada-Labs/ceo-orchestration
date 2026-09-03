# EVIDENCE — pack `memdelta-flake` (S340)

Base `ba15c718f8cb1ca37e8b909ddb321aa5bf78b1a9`. Shadow
`<scratchpad>/shadow-memdelta-flake` (detached HEAD). Every command below was
run from inside the shadow. Full transcripts: `battery.txt`, `control-log.txt`,
`codex-r1.txt`. Probe sources: `<scratchpad>/probe/`.

## A. The two routes to `names == []` (probe `probe_routes.py`)

```
production constants: scan=50ms anchor=100ms
healthy (production)       outcome=written        anchor_source=chain  modified=2 names=['MEMORY.md', 'zz-canary-topic.md']
route (a) scan starved     outcome=error          anchor_source=chain  modified=0 names=[]
route (b) anchor starved   outcome=start_unknown  anchor_source=none   modified=0 names=[]
```

Both budgets are wall-clock, so both must be injected; `outcome` +
`anchor_source` are the exact discriminant.

## B. Derivation of the opt-out set (NOT recalled)

A pytest plugin (`probe/budgetprobe2.py`) wraps `_memory_delta_observed` with
the cure's exact inner patch, applying it to **all** 32 observation call sites at
once. The failures ARE the opt-out set:

```
FAILED ...::TestSpecSurface::test_budget_exhaustion_is_not_written
FAILED ...::TestSpecSurface::test_slow_final_stat_is_error
2 failed, 58 passed in 1.40s
```

A first, WRONG derivation (plugin patching the module global from the OUTSIDE,
`probe/budgetprobe.py`) reported only ONE member — it could not see the test
whose own `mock.patch.object` would be overridden by an inner patch. The
derivation had to reproduce the cure's MECHANISM, not merely its effect.

## C. Positive controls (mechanism, not appearance)

`probe/slowrunner.py` simulates a loaded runner by SCALING the wall clock
`_memory_delta_observed` reads, scoped to the call — a slow RUNNER, not a
patched constant (a patched constant would share the mechanism the cure uses and
would prove nothing). `CEO_CTL=noanchor` forces the non-clock route instead.

### Control 1 — BEFORE the cure, clock ×20000

```
>       self.assertIn("zz-canary-topic.md", d["names"])
E       AssertionError: 'zz-canary-topic.md' not found in []
.claude/hooks/tests/test_session_end_memory_delta.py:1220: AssertionError
1 failed, 2 passed in 0.15s
```

Byte-identical to the CI failure on `ba15c71`. **RED reproduced.**

### Control 2 — BEFORE the cure, unresolved anchor (no clock involved)

```
E       AssertionError: 'zz-canary-topic.md' not found in []
.claude/hooks/tests/test_session_end_memory_delta.py:1220: AssertionError
1 failed, 2 passed in 0.12s
```

**The same message from a different cause** — this is defect B, demonstrated.

### Control 3 — AFTER the cure at the FIRST (60 s) budget, clock ×20000: REFUTED

```
E   AssertionError: 'error' != 'written'
E    : observacao DEGRADADA — as asercoes de wire abaixo passariam vacuamente; outcome='error' anchor_source='chain' files_count=2 modified_count=2 index_modified=True names=['MEMORY.md']
```

My own control refuted my first guess: 60 s was still starved at ×20000
(exhaustion inside the sanitizer loop — note `names` holds only 1 of 2). This is
why the shipped value is calibrated from a measurement, not chosen.

### Measurement that set the value (`probe/measure_obs.py`)

```
one observation, n=30: p50=0.331 ms  max=7.932 ms
  budget       50 ms -> survives a runner up to ~        6x slower (vs this machine's max)
  budget    60000 ms -> survives a runner up to ~     7564x slower (vs this machine's max)
  budget  3600000 ms -> survives a runner up to ~   453867x slower (vs this machine's max)
```

Production's ~6× margin sits inside this repo's documented CI drift
(hook p50 77 ms local vs 209→435 ms in CI). Shipped: `3600000`.

### Control 5 — BEFORE the cure, clock ×20000 (the refuting scale)

```
E       AssertionError: 'zz-canary-topic.md' not found in []
1 failed, 2 passed in 0.13s
```

### Control 6 — AFTER the cure (3600000 ms), SAME clock ×20000: immune

```
...                                                                      [100%]
3 passed in 0.11s
```

### Control 7 — AFTER the cure, unresolved anchor: still RED, now DIAGNOSABLE

```
E    : observacao DEGRADADA — as asercoes de wire abaixo passariam vacuamente; outcome='start_unknown' anchor_source='none' files_count=2 modified_count=0 index_modified=False names=[]
E    : observacao DEGRADADA — as asercoes de wire abaixo passariam vacuamente; outcome='start_unknown' anchor_source='none' files_count=2 modified_count=0 index_modified=False names=[]
2 failed, 1 passed in 0.15s
```

The cure deliberately does NOT hide a non-clock degradation. Route (b) is now
identifiable from the log alone, and the guard fires at the point of
degradation (inside `_emit_captured`) instead of three assertions later — both
wire tests inherit it.

## D. Battery — run AFTER the last edit to a shipped byte

The last change to the derivation script was the budget recalibration
`60000 → 3600000`; the shadow was re-derived from the script, then this battery
ran, then the rail. Nothing shipped changed afterwards (only pack `.md` files).

```
=== B1: PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_session_end_memory_delta.py
62 passed in 1.39s

=== B2: CEO_NATIVE_SUBAGENTS=0 (the CI job that went RED)
62 passed in 0.70s

=== B3: sibling suite test_check_compaction_continuity.py
57 passed in 3.35s

=== B4: python3 .claude/scripts/check-test-env-hygiene.py
OK: test-env hygiene clean (337 flagged files, all allowlisted).
rc=0

=== B5: python3 .claude/scripts/check-test-audit-isolation.py
OK: no unsafe subprocess spawn + no stray stale audit_emit copy (PLAN-119 WS-C/WS-D2).
rc=0

=== B6: the two new tests, by name
2 passed, 60 deselected in 0.12s

=== B7: confinement — files changed in the shadow
 M .claude/hooks/tests/test_session_end_memory_delta.py
 1 file changed, 230 insertions(+), 13 deletions(-)
```

60 → 62 tests. Exactly one file touched, and it is FREE by the oracle:

```
$ python3 .claude/hooks/check_canonical_edit.py --is-canonical \
      .claude/hooks/tests/test_session_end_memory_delta.py
.claude/hooks/tests/test_session_end_memory_delta.py	0
```

## E. Reproducibility of the derivation

```
=== B8: apply the script to a pristine copy of the HEAD file and compare bytes
OK check-only: 9 edicoes aplicaveis, 0 arquivo(s) novo(s)
BYTE-IDENTICAL: HEAD + script == the shadow under review
af77c84688d4ce39b0be296ed7c973f7d4330c16119b80a657b67beac61e87c0 test_session_end_memory_delta.py
af77c84688d4ce39b0be296ed7c973f7d4330c16119b80a657b67beac61e87c0 test_session_end_memory_delta.py
```

Re-running the script on the already-applied shadow REFUSES by name (no
best-effort second application):

```
REFUSE: ancora JA APLICADA em .claude/hooks/tests/test_session_end_memory_delta.py (substituto presente): 'from pathlib import Path\nfrom unittest import mock\n'
rc=1
```

## F. Pair-rail

One round, `Rail-Verdict: APPROVE`, TREE-INTACT
(`b0bc473ecc6434ee31f983bae6d1acd1e2aaa130a1f712837949cf35b860ae76` before and
after). Details and the false-green near-miss (`timeout(1)` does not exist on
macOS; rc 127 produced an empty review file that would have read as clean) in
`rail-round-1.md`.

## G. Untrusted content encountered

No file, tool output or codex output contained instructions addressed to me. The
only near-miss worth naming is a grep artifact: codex's exploration output quotes
`.claude/plans/PLAN-179-FOLLOWUP-sessionstart-anchor-id.md:66`, whose text
includes the literal `[P1][US1][...]` of a landed AC. It is a checkbox in a plan,
not a finding, and it is recorded as such in `rail-round-1.md`.

## CEO refutation — S341 (the refuter agent hung; the CEO refuted by hand)

Fresh detached worktree at `ba15c71`; pack applied via the derivation script only.

| tree | production budgets starved to 0 (synthetic infinitely-slow runner) | failures |
|---|---|---|
| `ba15c71` (no pack) | yes | **23** (includes the CI red `test_no_paths_on_the_wire`) |
| pack, 9 edits (builder) | yes | **3** — all `TestSpecSurface` anchor tests |
| pack, 10 edits (CEO extension) | yes | **0** |

The 3 residuals call `SessionEnd._session_start_ts(` DIRECTLY — 13 such call
sites in the file (`grep -c`) — and `_session_start_ts` owns
`_MEMORY_DELTA_ANCHOR_BUDGET_MS`. The `_observe` seam never sees them.
Cure: patch ONLY the anchor budget in `_DeltaBase.setUp` (`addCleanup`).

The first attempt patched BOTH budgets in setUp and broke
`test_slow_final_stat_is_error` (1 failed / 61 passed): that test sleeps 80 ms
on purpose and NEEDS the production 50 ms scan budget, opting out via
`_observe(budget_ms=None)` — an opt-out that a setUp patch silently overrides.
Narrowed to the anchor budget: 62/62 normal, 62/62 starved.

Re-derivation check: the 10-edit output of the script is byte-identical
(`cmp`) to the hand-refuted tree. `--check-only` after apply refuses with rc 1.
`check-test-env-hygiene.py`: clean.
