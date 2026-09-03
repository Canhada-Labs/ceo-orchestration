Rail-Verdict: CHANGES-REQUESTED (2 P1 + 4 P2; 3 cured, 3 declared)

# Pair-rail round 2 — pack `cost-integration-v2` (S341)

Reviewed tree: the r1 cures applied on a freshly-reset shadow.
Raw output: `codex-r2.txt` (ends `DONE_RC=0`).

**TREE-INTACT.** `git -C <SHADOW> diff | shasum -a 256`
= `4b1f0ac1ee6a07a7b0d388a18e87bdd19d36093e6e119e74acabc930c21e9920`
before and after; `git status --porcelain` unchanged (7 M + 1 ??).

Not a clean round: a `Full review comments:` block with 2 [P1] and 4 [P2].

---

## [P1] Replace direct environment assignments with patch.dict
`.claude/scripts/tests/test_ceo_cost_integration.py:817` (also 823, 831, 848)

**REAL, and it is MY r1 cure generating the next finding** — the class this
round flags is `AuditCarrierTests`, added in round 1 to close the carrier
[P2]. Verified by running the gate itself, AFTER that edit:

```
$ python3 .claude/scripts/check-test-env-hygiene.py ; echo rc=$?
  files with violations: 338 (allowlisted: 337)
  NEW violations: 4
FAIL: new test-env hygiene violations (not in allowlist):
  .../test_ceo_cost_integration.py:817: env-write — os.environ['CEO_AUDIT_LOG_PATH']
  .../test_ceo_cost_integration.py:823: env-write — os.environ['CEO_AUDIT_LOG_PATH']
  .../test_ceo_cost_integration.py:831: env-write — os.environ['CEO_AUDIT_LOG_DIR']
  .../test_ceo_cost_integration.py:848: env-write — os.environ['CEO_AUDIT_LOG_PATH']
rc=1
```

That rc is the whole lesson of the round. The same gate had printed
`OK: test-env hygiene clean (337 flagged files, all allowlisted)` earlier in
this build — **before** section 7 existed. A battery run before the last edit
is not a battery, and the second run is the one that counts.

**CURED:** every env change in `AuditCarrierTests` now goes through a nested
`patch.dict`; only `os.environ.pop` remains (the gate does not flag pops, and
`patch.dict` cannot delete a key — the pops are undone by the same context
manager). Two dead helpers left over from the first draft
(`_summary_json`, `_no_explicit_root`) were removed with it.

**Positive control:** the pre-cure class IS the control, measured above:
gate rc **1** with 4 named NEW violations. After the cure, `rc=0`,
`337 flagged, all allowlisted` — re-run after the last edit (EVIDENCE §2).

## [P1] Detect legacy audit fallback before pairing ledgers
`.claude/scripts/ceo-cost.py:1428`

> `_tx_audit_pinned(args.log)` returns false even if `default_log_path()`
> selected `_rp.legacy_state_dir()` because the scoped audit log was absent.

**REAL.** `ceo-cost.default_log_path()` documents a fourth resolution step —
"Legacy pre-migration `~/.claude/projects/<legacy-literal>/audit-log.jsonl`
(sanctioned READER fallback)" — reached with **no carrier set at all**
(`ceo-cost.py:160-176`). The transcripts resolver meanwhile returns THIS
project's corpus. The D8 guard, which asks only about carriers, waves the
pairing through: one project's legacy audit history printed beside another
project's transcripts.

**CURED, by changing the QUESTION rather than adding a case.** The guard
asked "did anyone name a path?"; it now also asks "did the path we RESOLVED
leave this project?":

```python
def _audit_path_is_out_of_project(resolved: Path) -> bool:
    try:
        return Path(resolved).resolve().parent != _rp.runtime_state_dir().resolve()
    except Exception:
        return False
```

OR-ed into `audit_override`. Fail-soft on an unresolvable path (degrades to
the previous behaviour rather than suppressing the primary block).

**Positive control:** `controls/control-r1-revert.py --which legacy` removes
the OR →
`LegacyAuditFallbackTests::test_legacy_fallback_refuses_the_pairing`
**FAILS** with `True is not false : a legacy/out-of-project audit log was
paired with this project's transcripts`.

The first draft of that test was WEAK and was re-derived (`_derive_v2f.py`):
without the cure it reported `available: false — transcripts root does not
exist`, i.e. the un-cured tree never reached the pairing at all — the control
was comparing two refusals with different reasons. The test now materialises
a real corpus at the AMBIENT resolver's root first, so the un-cured tree
publishes `available: true` (a genuine pairing) and the cured one refuses it.
Existence is not reachability. Three sibling tests keep the cure aimed: the
predicate is false for an in-project path, true for an outside one, and
`test_in_project_log_keeps_the_primary_block` proves a scoped log still
renders the primary block (a blanket suppression would pass without it).

## [P2] Point monitoring at the transcript total
`docs/cost-of-operation.md:286-287`

**REAL and self-contradictory within one page**: the section this pack adds
says the transcripts source is the one to quote for spend, and sixty lines
later the monitoring recipe pipes `jq '.totals.cost_usd'` — the SECONDARY
audit estimate, the very number the new section says reads `$0.00` on months
that cost four figures.

**CURED:** the recipe now shows both, PRIMARY first
(`jq '.transcripts.totals.usd'`), and says in prose which one to wire up and
why. Prose-only change, verified by reading; no test.

---

## Declared, not cured

### [P2] Count non-dict usage as an incomplete turn — `ceo-cost-transcripts.py:482-491`
An assistant line carrying `"usage": null` passes the substring prefilter,
`_extract_record()` returns `None`, and no counter moves — so `incomplete`
can stay `false` while a turn is dropped. This is v1's **D7** surface (the
`assistant_without_usage` counter added in v1's r3, itself after a live-corpus
measurement of 0 occurrences). Widening D7 a fourth time is a measurement
question, not a text fix: the honest cure counts the class and re-measures
against the live corpus, which is a wave of its own. **R10.**

### [P2] Label the memory-validation source in JSON — `budget-summary.py:2011-2016`
v1's **D9** added the "which ledger did I validate" line to `format_human()`
only; `--json` serialises the unchanged verdict. Real asymmetry. Curing it
changes the JSON SHAPE of a governance check that other consumers read, which
is a compatibility decision for whoever owns the claim band — v1 already
declined to re-point the validator for the same reason. **R11.**

### [P2] Register `CEO_COST_TRANSCRIPTS_DIR` in `env-inventory.json`
Unchanged from round 1: outside FILE ASSIGNMENT, `--generate` rewrites the
whole inventory, and the gate is **already RED on base** for five unrelated
vars. This pack moves the count 5 → 6, not the verdict. **R1**, handed to the
lander.

## Battery after the cures

`142 passed` on the four test files. `check-test-env-hygiene.py` rc **0**,
`check_contamination.py` rc **0**, `validate-governance.sh` `Errors: 0`,
`check-installer-write-safety.py` rc **0** — all re-run after the last edit.
