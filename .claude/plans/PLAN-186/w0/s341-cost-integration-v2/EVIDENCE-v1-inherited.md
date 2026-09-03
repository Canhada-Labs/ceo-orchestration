# EVIDENCE — pack `cost-integration` (PLAN-186 W0, AC-1b) — S340

Base commit: `b6dce787651aaa9c06e842ce9d665cfb9d201ecd`
Shadow: `<scratchpad>/shadow-cost-integration` (detached worktree at base)
Pack: `<scratchpad>/packs/cost-integration/`

Every number below was produced **after the last edit** to the derivation
script, on a shadow re-derived from a clean worktree.

## 1. Derivation is reproducible and refuses re-application

```
git -C <repo> worktree add --detach <scratchpad>/shadow-cost-integration HEAD
python3 <pack>/apply-cost-integration.py --root <SHADOW>
  -> OK: 7 arquivo(s) escrito(s).
python3 <pack>/apply-cost-integration.py --root <SHADOW> --check-only
  -> RECUSA (30):  [1 new-file-exists + 29 "substituto JA PRESENTE"]  rc=1
python3 <pack>/apply-cost-integration.py --list-paths
  -> 7 paths
```

The already-applied guard does **not** rely on the anchor disappearing:
several edits append to their anchor, so only "the full replacement is
already present" separates a pristine tree from a patched one. Verified: the
first run on a clean tree is clean (no false refusals), the second refuses
all 29 edits.

## 2. Canonicality oracle — 100% free

```
python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>
```

| path | verdict |
|---|---|
| `.claude/scripts/ceo-cost.py` | 0 |
| `.claude/scripts/budget-summary.py` | 0 |
| `.claude/scripts/ceo-cost-transcripts.py` | 0 |
| `.claude/scripts/tests/test_ceo_cost.py` | 0 |
| `.claude/scripts/tests/test_budget_summary.py` | 0 |
| `.claude/scripts/tests/test_ceo_cost_integration.py` | 0 |
| `docs/cost-of-operation.md` | 0 |
| `.claude/plans/PLAN-186-orchestrator-operating-model.md` (AC flip) | 0 |

## 3. Battery — FINAL numbers (run after the last edit)

```
cd <SHADOW>
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  .claude/scripts/tests/test_ceo_cost_integration.py \
  .claude/scripts/tests/test_ceo_cost.py \
  .claude/scripts/tests/test_ceo_cost_stream.py \
  .claude/scripts/tests/test_budget_summary.py \
  .claude/scripts/tests/test_ceo_cost_transcripts.py
  -> 178 passed, 0 failed, 0 skipped   (rc=0)
```

Breakdown: 39 new (`test_ceo_cost_integration.py`) + 139 pre-existing
(13 ceo-cost + 36 ceo-cost-stream + 47 budget-summary + 23 transcripts, plus
their parametrisations). Zero pre-existing tests were deleted or relaxed.

Dependent suites (everything in the repo that mentions `ceo-cost` /
`budget-summary` / `cost-of-operation`):

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  .claude/hooks/tests/adapters/live/test_cost.py \
  .claude/scripts/tests/test_model_fleet_presence.py \
  .claude/scripts/tests/test_success_receipt.py \
  .claude/scripts/tests/test_a4_pricing_doctrine.py
  .claude/scripts/tests/test_check_docs_freshness.py \
  .claude/scripts/tests/test_check_canonical_doc_freshness.py \
  .claude/scripts/tests/test_check_doc_skill_paths.py
  -> 120 passed   (rc=0)
```

NOT run: the whole `.claude/scripts/tests` directory — it exceeded a 10-minute
wall in this environment. The selection above is the mechanically-derived set
(`grep -rl` for the three names across `.claude/scripts/tests`,
`.claude/hooks/tests`, `tests`), not a hand-picked one.

## 4. Corpus gates (run on the final shadow)

| gate | rc | note |
|---|---|---|
| `check-test-env-hygiene.py` | **0** | `OK: clean (337 flagged files, all allowlisted)` |
| `check-ceremony-script.py` | 0 | same on base |
| `check-claude-md-claims.py` | 0 | |
| `check-staleness.py` | 0 | only the pre-existing PLAN-183 stranded warning |
| `check-docs-drift.py` | 0 (advisory) | `WARN: 70 drift(s)` — **identical count on base** |
| `env-inventory-check.py --check` | **1** | `ENV-DRIFT: 6` vs **`ENV-DRIFT: 5` on the BASE tree** — see residual R1 |

The hygiene gate caught a real defect mid-build: three bare `os.environ[...]`
writes. It was rerun to rc=0 only after the cure. (The first read of it was
masked by a `| tail` — the last command determines the exit; re-run captured
`RC=1` explicitly.)

## 5. Positive controls (RED -> GREEN)

The whole new test file was copied, UNCHANGED, into a second disposable
worktree at the base commit (`<scratchpad>/pc-base`) with **no source
changes**:

```
cd <scratchpad>/pc-base
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  .claude/scripts/tests/test_ceo_cost_integration.py
  -> 37 failed, 2 passed   (rc=1)     [RED]
```

Same file on the derived shadow:

```
  -> 39 passed   (rc=0)               [GREEN]
```

The 2 that are green on base are declared, not hidden:
`test_bad_source_exits_2` (base argparse rejects `--source` as an unknown
option, so it also exits 2 — right answer, wrong reason) and
`test_bare_invocation_defaults_do_not_crash` (asserts no crash). Every test
that asserts the new behaviour is RED on base.

Per-cure positive controls inside that run:
- `test_incomplete_scan_is_declared_not_swallowed` — plants a truncated JSON
  line in the synthetic corpus; RED on base (no `collect`), GREEN with the
  cure, and asserts BOTH the `incomplete` flag and the rendered
  `INCOMPLETE SCAN` / `LOWER BOUND` text.
- `test_clean_scan_declares_nothing` — the negative half: a clean corpus
  prints no warning (so the warning is not unconditional).
- `test_plan_id_suppresses_transcripts_under_both` /
  `test_plan_id_with_explicit_transcripts_is_a_named_refusal` — RED on base.
- `test_cross_project_pairing_is_refused` /
  `test_env_audit_override_also_triggers_the_pairing_check` /
  `test_transcripts_only_is_never_suppressed_by_the_pairing` — the three
  halves of the r2/r3 cross-project rule, including the NEGATIVE one that
  proves the rule does not over-fire.
- `test_assistant_line_without_usage_is_counted` — plants a drifted assistant
  record (no `usage` object at all) and asserts the counter AND the warning.
- `test_stream_with_transcripts_source_is_refused` /
  `test_stream_under_both_warns_but_runs`;
  `test_validate_memory_claim_refused_under_transcripts` /
  `test_memory_claim_block_names_its_ledger_under_both` /
  `test_memory_claim_block_unchanged_under_audit` (the last one is the
  byte-compat half).

## 6. CLI byte-compatibility of the instrument

`ceo-cost-transcripts.py`'s `main()` was refactored onto `transcript_rollup()`.
Both trees run against the SAME fixed synthetic corpus:

```
python3 <TREE>/.claude/scripts/ceo-cost-transcripts.py \
  --project-dir <scratchpad>/txfixt --since 3650d          # text
python3 <TREE>/.claude/scripts/ceo-cost-transcripts.py \
  --project-dir <scratchpad>/txfixt --since 3650d --json --by day
```

- text: `TEXT-CLI-IDENTICAL` after dropping the `tempo de execucao` line and
  normalising the worktree path inside the `pricing:` line (the only diff was
  `/pc-base/` vs `/shadow-cost-integration/` in that path).
- json: `JSON-CLI-IDENTICAL` after dropping `elapsed_s` and normalising the
  same path.

## 7. `--source audit` byte-for-byte regression

`FROZEN_AUDIT_TEXT` in the test file was captured by running the **base**
tree's `ceo-cost.py` on the fixture:

```
python3 <pc-base>/.claude/scripts/ceo-cost.py --log <fixt>/audit-log.jsonl --since all
```

`test_source_audit_is_byte_identical_to_frozen` asserts
`stdout == FROZEN_AUDIT_TEXT + "\n"` on the derived tree. It is RED on base
only because `--source` does not parse there; the frozen bytes themselves
came FROM base.
`test_json_audit_shape_unchanged` pins the audit-mode JSON to exactly
`["by_day","by_model","by_session","by_skill","totals"]` — no new keys.
For `budget-summary`, `test_source_audit_equals_untouched_rollup_rendering`
asserts `main(--source audit) stdout == format_human(rollup(...)) + "\n"` and
`test_json_audit_shape_has_no_new_keys` asserts neither `source` nor
`transcripts` appears.

## 8. Live figures on this machine (the point of the pack)

```
cd <SHADOW>
CLAUDE_PROJECT_DIR=<repo> python3 .claude/scripts/ceo-cost.py --since 24h
CLAUDE_PROJECT_DIR=<repo> python3 .claude/scripts/ceo-cost.py --since 30d
CLAUDE_PROJECT_DIR=<repo> python3 .claude/scripts/budget-summary.py summary --since 30d
```

**24h** — corpus: 68 assento + 697 subagent files (the live corpus grows
while the pack is built; two 24h readings taken ~2 h apart are shown where
they differ).

| source | result |
|---|---|
| TRANSCRIPTS (primary) | 1,518 turns · 35,995 in · 1,763,331 out · 317,749,101 cache-read · 16,989,893 cache-write · **$334.58** (earlier reading: 1,304 turns, $318.12) |
| AUDIT LOG (secondary) | 0 spawns · 0 in · 0 out · **$0.00** |

24h by role: assento 202 turns / $157.48 · subagent 1,316 turns / $177.10.

**30d**

| source | result |
|---|---|
| TRANSCRIPTS (primary) | 30,820 turns · 411,475 in · 34,544,378 out · 9,165,601,960 cache-read · 278,052,570 cache-write · **$10,625.59** |
| AUDIT LOG (secondary) | 75 events across 5 rotation files, **no priced cost rows** |

30d by role: assento 13,089 turns / **$7,291.57** (68.6%) · subagent 17,731
turns / $3,334.02 (31.4%) — i.e. the seat, which the audit log cannot see at
all, is ~69% of the spend.
30d by model: fable-5 $6,031.08 (56.8%), opus-5 $4,082.83 (38.4%),
fable-5-1 $345.00 (3.2%), opus-4-8 $104.86, sonnet-5 $53.56,
sonnet-4-6 $7.60, haiku-4-5 $0.07.

`budget-summary summary --since 30d` reports the same primary total (a few
minutes apart, so a few turns higher) above its unchanged `FinOps summary`
block; measured earlier in the build at $10,592.69 / 30,691 turns against
`ceo-cost`'s $10,592.22 / 30,688. One model id in the corpus, `<synthetic>` (148 turns
over 30d), is absent from every pricing table: it is reported with its token
totals and priced $0 with a named warning, never guessed.

## 9. Pair-rail

| round | verdict | tree | findings |
|---|---|---|---|
| 1 | CHANGES-REQUESTED | TREE-INTACT (`37e164e3…`) | 2 P1 + 3 P2, all REAL; 4 cured, 1 (env-inventory) out of scope |
| 2 | CHANGES-REQUESTED | TREE-INTACT (`c5514df9…`) | 2 P1 + 4 P2, all REAL; 5 cured, env-inventory repeats |
| 3 | CHANGES-REQUESTED | TREE-INTACT (`f6a59351…`) | 2 P1 + 4 P2, all REAL; 5 cured, env-inventory repeats |

The rail is capped at 3 rounds by the task. The r3 cures were made after
that round and were therefore NOT reviewed by a 4th — declared in
`rail-round-3.md`. Each round ran on a shadow **re-derived from the script**,
never on a tree hand-patched between rounds. Two of the r3 findings named
defects that my own r2 cures had introduced (`audit_override` suppressing
transcripts-only output; a `tearDown` without `super()` after the
`TestEnvContext` conversion) — the rail caught the fix-of-the-fix class both
times.

Raw transcripts: `codex-r1.txt`, `codex-r2.txt`. Codex output is treated as
DATA — every finding was verified against the files on disk before being
acted on.
