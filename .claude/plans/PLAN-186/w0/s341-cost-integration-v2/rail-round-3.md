Rail-Verdict: CHANGES-REQUESTED (0 P1, 3 P2; all DECLARED — round cap reached)

# Pair-rail round 3 — pack `cost-integration-v2` (S341)

Reviewed tree: the r1 + r2 cures applied on a freshly-reset shadow.
Raw output: `codex-r3.txt` (ends `DONE_RC=0`).

**TREE-INTACT.** `git -C <SHADOW> diff | shasum -a 256`
= `b750919aa8e72e50c2b6bb37234d9d635319e759cd625f06dee91e5449fcbf30`
before and after; `git status --porcelain` unchanged (7 M + 1 ??).

**No [P1].** Round 1 had one, round 2 had two; round 3 has none. Every
finding cured in rounds 1 and 2 stayed cured — in particular, this round did
NOT re-raise the env-hygiene violation that my own r1 cure introduced, nor
the legacy-fallback pairing, nor either of the two findings this pack exists
to close (A: silently dropped audit-side blocks; B: the unconditional
ratified override).

**All three [P2] are DECLARED, not cured — the round cap is the reason, and
it is a rule, not a shrug.** The task caps the rail at 3 rounds. A cure
written now would ship with no round reviewing it, which is precisely the
class that produced round 2 (my round-1 cure broke a hard-fail gate) and
precisely the risk v1 declared as its R5. Each is verified below and handed
to the lander with the exact change.

---

## [P2] Skip audit aggregation in transcripts-only mode — `ceo-cost.py:1428-1430`

> When `--source transcripts` is selected and an audit log exists, this
> branch only bypasses the missing-log error; the code still reads and
> aggregates that unrequested ledger.

**REAL.** `ceo-cost.main()` guards only the *not found* case
(`if not paths and source != "transcripts"`) and then runs `discover_logs`,
`read_entries` and `aggregate` unconditionally. Two consequences, and the
second is the one that matters: a malformed audit row can raise out of
`aggregate()` and take down a report that never asked for the audit ledger.
`budget-summary.py` already skips its `rollup()` entirely under
`--source transcripts` — the two callers are asymmetric.

**R12, handed to the lander.** The change is a control-flow restructure of
`ceo-cost.main()` (skip discovery, pricing and aggregation; synthesise the
empty `agg` the renderers expect), and the renderers' behaviour with an
absent `agg` needs its own tests. Not a line fix.

## [P2] Preserve the requested window in transcript-only output — `ceo-cost-transcripts.py:872-875`

> Human reports for `--since 1h` and `--since 30d` contain no metadata
> identifying their reporting window.

**REAL, and it is the same FAMILY as cure A** — a number rendered without the
qualifier that makes it mean something. Under `--source transcripts` both
callers return right after the shared block, and that block carries no
`since` label, while both pre-existing standalone renderers do.

**R13, handed to the lander.** Deliberately not cured at the cap: the fix
edits `render_block()`, which is the ONE surface all three callers share (D1),
and the pack's regression oracle is a frozen-bytes comparison of rendered
output. Changing rendered bytes on the last round, with no round left to
review either the change or the re-frozen literal, trades a labelling defect
for a regression risk on the property that makes `--source audit` provable.
The change itself is small — thread the caller's `--since` string into
`collect()`/`render_block()` and print it beside the banner — and it should
carry a test that `--since 1h` and `--since 30d` render different windows.

## [P2] Add the new environment knob to the canonical inventory — `ceo-cost-transcripts.py:668-671`

Raised in all three rounds. Unchanged: **R1**. `.claude/scripts/env-inventory.json`
is outside this pack's FILE ASSIGNMENT, `env-inventory-check.py --generate`
rewrites the WHOLE inventory (sweeping in five other waves' un-triaged
drifts), and **the gate is already RED on the base commit** for five
unrelated vars (`CEO_AUDIT_FAMILY_M4_REQUIRED`, `CEO_LEDGER_CHECKPOINT`,
`CEO_LEDGER_CHECKPOINT_REQUIRED`, `CEO_LEDGER_WRITE_GATE_ENFORCE`,
`CEO_SESSION_MEMORY_DELTA`). This pack moves the gate's COUNT from 5 to 6,
not its verdict. The lander (or the wave that owns that file) should
regenerate deliberately with those five triaged.

---

## Round summary across the three rounds

| round | P1 | P2 | cured | declared |
|---|---|---|---|---|
| 1 | 1 | 3 | 3 | 1 (R1) |
| 2 | 2 | 4 | 3 | 3 (R1, R10, R11) |
| 3 | 0 | 3 | 0 | 3 (R1, R12, R13) |

Six cures, each with a positive control that fails without it (table in
EVIDENCE §5). The two findings the refuter sent me for — A and B — were never
re-raised by any round.

## Battery on the reviewed tree

`142 passed`; `check-test-env-hygiene.py` rc 0, `check_contamination.py`
rc 0, `validate-governance.sh` `Errors: 0`, `check-installer-write-safety.py`
rc 0. Nothing was edited after that battery: the shadow the rail reviewed IS
the delivered shadow.
