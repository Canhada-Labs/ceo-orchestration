# PLAN-179 W3 / US11 — orphan-probe decision (D1 / D2 / D5)

> Scope: `.claude/scripts/context-budget.py`.
> Question: *"An orphan probe that stays is debt that LOOKS like coverage."*
> Decide, per probe: **CONSUME** (name the consumer) or **REMOVE** (delete the
> probe AND its test in the same change).
> Recorded 2026-08-18. Every number below is **measured**, with the command
> that produced it; nothing here is an estimate.

---

## 0. TL;DR

| Probe | Canonical audit twin | Emitters in repo | Observed emits | Verdict |
|-------|----------------------|------------------|----------------|---------|
| **D1** — auto-compaction policy | **LANDED** | 0 | 0 | **KEEP** as exported policy (consumer cannot exist here) |
| **D2** — summarize oldest outputs | **absent** | 0 | 0 | **REMOVE** — pending co-deletion of its test |
| **D5** — middle-out ladder | **LANDED** | 0 | 0 | **KEEP** as exported policy (consumer cannot exist here) |

The asymmetry is the whole finding: D1 and D5 are *half-landed* (the canonical
emit exists, the caller does not), while D2 is an orphan at **both** ends and
additionally carried a **false claim** about its own status.

---

## 1. What the three probes are

All three came from PLAN-133 Wave D. Each is a pure, side-effect-free decision
function plus an opt-in `--*-decision` CLI mode, default-OFF behind an env flag.

| Probe | Function(s) | CLI flag | Env flag |
|-------|-------------|----------|----------|
| D1 | `decide_compaction` | `--compact-decision` | `CEO_AUTO_COMPACT_THRESHOLD` |
| D2 | `decide_summarization` | `--summarize-decision` | `CEO_SUMMARIZE_OLDEST` |
| D5 | `decide_middle_out_degradation`, `apply_middle_out_degradation` | `--middle-out-decision` | `CEO_MIDDLE_OUT_DEGRADE` |

None of them compacts, summarizes, elides, emits, or writes. Each returns a
dict and stops. The side effects were always meant to be wired **by a host**.

---

## 2. Measurements

### 2.1 Who calls the decision functions

```
$ for s in decide_compaction decide_summarization decide_middle_out_degradation \
           apply_middle_out_degradation; do echo "=== $s"; \
    grep -rln "$s" --exclude-dir=.git . ; done
```

Raw output (all four are identical in shape):

```
.claude/hooks/_lib/audit_emit.py            <- a COMMENT, not a call (see 2.2)
.claude/scripts/context-budget.py           <- the definition itself
.claude/scripts/tests/test_context_budget.py<- the tests
(+ .claude/plans/PLAN-179/staged-w01/... — a staged copy of audit_emit.py)
```

`decide_summarization` returns only the last two lines: **no `audit_emit.py`
mention at all.**

Verified that the `audit_emit.py` hits are prose, not invocations:

```
$ grep -n "decide_compaction\|decide_middle_out_degradation\|apply_middle_out_degradation" \
    .claude/hooks/_lib/audit_emit.py
292:    # .claude/scripts/context-budget.py:decide_compaction (non-canonical).
305:    # .claude/scripts/context-budget.py:decide_middle_out_degradation /
306:    # apply_middle_out_degradation (non-canonical).
```

**Emitters in repo = 0 for all three probes.**

### 2.2 Which canonical audit surfaces are landed

```
$ for a in context_auto_compacted context_middle_out_degraded subagent_output_summarized; do
    echo "=== $a"; grep -rln "$a" --exclude-dir=.git --exclude-dir=PLAN-179 . ; done
```

```
=== context_auto_compacted
SPEC/v1/audit-log.schema.md
.claude/hooks/_lib/audit_emit.py
.claude/data/audit-registry.golden.txt
.claude/scripts/context-budget.py
(+ two frozen review transcripts under .claude/plans/)

=== context_middle_out_degraded
SPEC/v1/audit-log.schema.md
.claude/hooks/_lib/audit_emit.py
.claude/data/audit-registry.golden.txt
.claude/scripts/context-budget.py
(+ the same two frozen transcripts)

=== subagent_output_summarized
.claude/scripts/context-budget.py
```

Confirming counts:

```
$ grep -c "subagent_output_summar" .claude/hooks/_lib/audit_emit.py   -> 0
$ grep -c "context_auto_compacted" SPEC/v1/audit-log.schema.md        -> 4
$ grep -c "subagent_output_summarized" SPEC/v1/audit-log.schema.md    -> 0
$ grep -c "context_middle_out_degraded" SPEC/v1/audit-log.schema.md   -> 4
```

D1 and D5 additionally have live dispatch-gate branches
(`audit_emit.py` lines 5172-5224) and closed-enum allowlists. D2 has none.

### 2.3 Have any of these events ever fired

```
$ python3 - ~/.claude/projects/ceo-orchestration/audit-log.jsonl <<'EOF'
   ... counts the six action names over every parsed line ...
EOF
events_parsed=7972 unparsable=0
  context_auto_compact_suppressed          0
  context_auto_compacted                   0
  context_middle_out_degrade_failed        0
  context_middle_out_degraded              0
  subagent_output_summarize_skipped        0
  subagent_output_summarized               0
```

**Zero of six, across 7 972 events.** The probes have never influenced anything.

### 2.4 The stale claim inside D2 (and D1/D5)

All three section headers pointed at staged Owner-GPG proposals:

```
.claude/plans/PLAN-133/staged/D1.proposal.md
.claude/plans/PLAN-133/staged/D2.proposal.md
.claude/plans/PLAN-133/staged/D5.proposal.md
```

```
$ ls .claude/plans/PLAN-133/staged/
ls: .claude/plans/PLAN-133/staged/: No such file or directory
$ ls .claude/plans/PLAN-133/
ls: .claude/plans/PLAN-133/: No such file or directory
```

For D1/D5 the pointer is merely **stale**: the proposals landed, so the text
should say "landed", not "staged". For D2 the sentence was **false in both
halves** — it asserted the emit "is CANONICAL (`.claude/hooks/_lib/audit_emit.py`)"
when the action name occurs nowhere in that file, and pointed at a staged file
that does not exist. This is the classic repo failure mode: *an instrument
whose question aged*. The comments are corrected in this change.

---

## 3. Per-probe verdict

### D1 — proactive auto-compaction · **KEEP as exported policy** (not coverage)

- **Consumer named:** a *host loop* that owns its own context-management step —
  i.e. an adopter's API/SDK harness that decides when to compact.
- **Does it exist?** No, and **it cannot exist inside Claude Code.** The
  harness owns compaction. The pinned hook schema
  (`.claude/data/hook-schema-2.1.220.json`) gives `PreCompact` **no
  `hookSpecificOutput` arm** (`_absent_arms_note` names it explicitly), so a
  hook can observe a compaction, or block it, but never *drive* one from a
  policy decision. Building the consumer would mean building an API request
  loop this framework deliberately does not have.
- **What would have to build it:** an adopter harness (or a future
  `run-skill-benchmark.py`-class API driver) that (i) tracks live
  `used_tokens`/`window_tokens`, (ii) calls `decide_compaction`, (iii) emits
  `context_auto_compacted` / `context_auto_compact_suppressed` via
  `emit_generic`. Steps (i) and (iii) exist; (ii)'s caller does not.
- **Why not REMOVE:** the canonical half is **landed** in three canonical
  surfaces (`audit_emit.py`, `SPEC/v1/audit-log.schema.md`,
  `.claude/data/audit-registry.golden.txt`). Deleting the decision half would
  leave a canonical emit whose documented producer no longer exists — trading
  one drift for a worse one, and touching canonical files requires an
  Owner-GPG ceremony that US11 does not authorise.
- **Debt made visible instead:** `probe_status()` now declares
  `verdict=keep_exported_policy`, `emitters_in_repo=0`, `observed_emits=0`.

### D2 — summarize oldest verbose outputs · **REMOVE (pending test co-deletion)**

- **Consumer named:** none — and none is buildable here. D2's whole point is
  routing an old verbose output to a **cheap model tier** for a digest. This
  framework's in-path code is stdlib-only and no-network by construction, so
  the digest call has nowhere to live.
- **No canonical anchor:** unlike D1/D5, `subagent_output_summarized` /
  `subagent_output_summarize_skipped` exist **only** in `context-budget.py`.
  Nothing outside this file would be orphaned by deleting it. This is the pure
  orphan of the three, and the one whose docstring actively misled.
- **Removal scope (non-canonical — no ceremony needed):**
  1. `.claude/scripts/context-budget.py` — the D2 section (env constants,
     `SummarizationPolicy`, `load_summarization_policy_from_env`,
     `_output_token_size`, `decide_summarization`, the `SUMM_*` constants),
     the `--summarize-decision` / `--output-sizes` / `--output-sizes-file`
     arguments, and the D2 fold-in branch in `_cli`;
  2. `.claude/scripts/tests/test_context_budget.py` — class
     `TestSummarizationPolicy` (lines 706-964 at time of writing, including
     the three `--summarize-decision` subprocess tests);
  3. cosmetic: the D2 lines in the module docstring `## Usage` block and the
     D1/D2/D5 mention in `.claude/commands/context-budget.md` §"Advisory-only
     contract".
- **Why it is not executed in this change — stated plainly:** the authoring
  agent's FILE ASSIGNMENT covered `context-budget.py` but **not** the test
  file. "Delete the probe AND its test in the same change" is the correct
  rule, and half-executing it would turn a 144-green suite red — strictly
  worse than the debt it removes. The deletion is therefore **scoped and
  scheduled**, not silently dropped, and `probe_status()` records
  `verdict=remove_pending_test_codeletion` so the state cannot be mistaken for
  a decision to keep.

### D5 — middle-out degradation ladder · **KEEP as exported policy** (not coverage)

- **Consumer named:** the same absent host loop — specifically the component
  that *assembles* the context and discovers the overflow. Claude Code
  assembles its own context; this framework never sees the message list, so
  `apply_middle_out_degradation` has nothing to apply to.
- **Why not REMOVE:** identical to D1 — `context_middle_out_degraded` /
  `context_middle_out_degrade_failed` are landed canonical
  (`audit_emit.py` + SPEC v1 + golden registry). Removal is a ceremony.
- **Note on value:** D5 is the one probe with an independently useful pure
  transform (`apply_middle_out_degradation` elides a message middle, preserving
  head+tail). An adopter can use it standalone; that is exactly what "exported
  policy" means and why the KEEP is not just inertia.

---

## 4. What actually changed in `context-budget.py`

The change converts *implicit* debt into *declared* debt. It adds no behaviour,
gates nothing, and preserves the JSON contract.

1. **`PROBE_STATUS` + `probe_status()`** — a machine-readable record per probe:
   entrypoints, env flag, audit actions, `canonical_emit_landed`,
   `emitters_in_repo`, `observed_emits`, `verdict` (closed enum), the missing
   `consumer`, `why_not_removed`, and `removal_scope`.
2. **`build_inventory()`** gains an additive `"probe_status"` key and one extra
   honesty note. `schema` stays `context-budget.v1`; the existing shape test
   asserts key *presence* (`assertIn`), so additive keys are the established
   pattern here — `savings_top3` was added the same way in PLAN-153 Wave C.
3. **`_render_human()`** gains a `## decision-probe status` block, so a reader
   who never opens the JSON still sees "reference policy, NOT wired".
4. **`--probe-status`** prints the block and exits 0.
5. **Stale-claim corrections** in the D1/D2/D5 section comments (§2.4), with
   D2's false canonical claim called out explicitly rather than quietly
   rewritten.

### Verification run (commands + raw results)

```
$ python3 -m py_compile .claude/scripts/context-budget.py          -> EXIT=0
$ python3 .claude/scripts/context-budget.py --help                 -> EXIT=0 ("probe-status" present)
$ python3 .claude/scripts/context-budget.py --probe-status         -> EXIT=0
    probes:   ['D1', 'D2', 'D5']
    verdicts: ['keep_exported_policy',
               'remove_pending_test_codeletion',
               'keep_exported_policy']
$ python3 .claude/scripts/context-budget.py --json --top 2         -> EXIT=0
    schema = context-budget.v1
    all nine pinned keys present + savings_top3, notes, scanner_available, probe_status
$ CEO_AUTO_COMPACT_THRESHOLD=80 ... --compact-decision             -> EXIT=0, reason="compact"
$ CEO_SUMMARIZE_OLDEST=2 ...      --summarize-decision             -> EXIT=0, reason="selected"
$ CEO_MIDDLE_OUT_DEGRADE=40 ...   --middle-out-decision            -> EXIT=0, reason="failed"
$ python3 -m pytest .claude/scripts/tests/test_context_budget.py \
      .claude/scripts/tests/test_compaction_template.py -q
    BEFORE: 144 passed  (EXIT=0)
    AFTER:  144 passed  (EXIT=0)
$ python3 .claude/scripts/check_contamination.py                   -> EXIT=0
```

The script exposes no `--self-test`; the pytest module above is its test
surface, and it was run with a true exit code (no pipe), per the repo's
`pytest | tail` lesson.

---

## 5. Follow-ups this record hands off

1. **Execute the D2 deletion** with the test file in assignment (§3, D2,
   removal scope). One commit, both files.
2. **`.claude/commands/context-budget.md`** still advertises the D1/D2/D5
   probes as "opt-in modes" without saying they have no caller. It was outside
   assignment here; a one-paragraph amendment should point at `--probe-status`.
3. **If D1/D5 are ever to go**, it is an Owner-GPG ceremony spanning
   `audit_emit.py`, `SPEC/v1/audit-log.schema.md`,
   `.claude/data/audit-registry.golden.txt` and the tests — never a script edit.
4. **Do not "re-verify" the zero counts by re-reading this file.** Re-run the
   §2 commands; a count that ages is exactly the class this record corrects.
