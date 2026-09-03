Rail-Verdict: CHANGES-REQUESTED (1 P1 + 3 P2; 3 cured, 1 declared)

# Pair-rail round 1 — pack `cost-integration-v2` (S341)

Command, from inside the shadow:

```
codex exec review --uncommitted --skip-git-repo-check \
  -c sandbox_mode="workspace-write" </dev/null > codex-r1.txt 2>&1
```

Raw output: `codex-r1.txt` (603 KB, ends `DONE_RC=0`).

**TREE-INTACT.** `git -C <SHADOW> diff | shasum -a 256`
= `d986e101f2c8236726762e41380fca59c754a5f2eb60fd14716013cc90dfce86`
before and after the round; `git status --porcelain` unchanged (7 M + 1 ??).
The first launch of this round was killed by a 10-minute tool timeout after
the review had finished its checks but before it printed findings; it was
relaunched in the background against the same tree (same sha both times) and
ran to completion. Only the completed run is reported.

The round emitted a `Full review comments:` block — **not a clean round**.

---

## [P1] Stop env patches before restoring TestEnvContext
`.claude/scripts/tests/test_budget_summary.py:532` (also `:457`,
`test_ceo_cost_integration.py:237`)

> For `TestEnvContext` subclasses, `addCleanup` runs after `tearDown`:
> `super().tearDown()` first restores the ambient environment and deletes its
> temp tree, then this cleanup reinstalls the earlier sandbox snapshot.

**REAL — verified by measurement, not by reading.**
`controls/probe-r1-p1-cleanup-order.py` builds a minimal `TestEnvContext`
subclass with the reported pattern and reports the environment after the
class finishes:

```
ambient HOME before : /Users/<redacted>
HOME inside the test: /var/folders/.../ceo-hook-test-vzgxmrrz/home
HOME after teardown : /var/folders/.../ceo-hook-test-vzgxmrrz/home
leaked sandbox HOME : True
and it is deleted   : True
```

Every later test in the same process would run with `HOME` (and
`CLAUDE_PROJECT_DIR`, `CEO_AUDIT_*`) pointing at a directory that no longer
exists — the exact failure mode `TestEnvContext` exists to prevent, and one
the CLAUDE.md hook-test isolation rule forbids.

**CURED** (`_derive_v2d.py`, section 7): the three sites stop the
`patch.dict` in an explicit `tearDown()` *before* `super().tearDown()`, and
the `addCleanup` registration is removed. Order is commented as load-bearing
at each site.

**Positive control:** `controls/control-r1-revert.py --which p1` puts the
`addCleanup` back →
`SandboxTeardownOrderTests::test_base_restores_the_ambient_environment`
**FAILS** (1 failed, 5 passed); with the cure it is green inside the 138.

## [P2] Pass the captured clock to the audit rollup
`.claude/scripts/budget-summary.py:2190-2194`

> `_now` is used for the transcript cutoff, but this call omits `rollup`'s
> existing `now` argument, so `rollup()` captures a slightly later clock
> internally.

**REAL.** `rollup()` does take `now: Optional[datetime] = None`
(`budget-summary.py:594`), and v1's own D10 says "ONE wall clock for both
ledgers". v1 captured `_now`, used it for the transcripts cutoff, and never
handed it to `rollup()` — the decision was half-delivered.

**CURED:** `now=_now` is passed.
**Positive control:** `--which clock` removes it →
`OneWallClockTests::test_one_wall_clock_feeds_both_ledgers` **FAILS** with
`AssertionError: unexpectedly None : rollup() got no explicit clock`. The
test asserts the property, not the text: `rollup_now - transcripts_cutoff ==
timedelta(hours=24)` for `--since 24h`.

## [P2] Ignore audit-path env vars that budget-summary does not use
`.claude/scripts/budget-summary.py:2204-2208`

> When only `CEO_AUDIT_LOG_PATH` is set, `budget-summary.py` still reads its
> normal directory ... but `_tx_audit_pinned()` treats the ignored path
> variable as an override.

**REAL — measured on a clean env** (`env -i`, no explicit transcripts root):

| carriers set | `audit_dir` | transcripts block |
|---|---|---|
| none | `.../projects/-tmp-ceo-p2-proj` | `available: false — transcripts root does not exist` |
| `CEO_AUDIT_LOG_PATH` | `.../projects/-tmp-ceo-p2-proj` **(unchanged)** | `available: false — the audit source was pointed at an explicit path ...` |
| `CEO_AUDIT_LOG_DIR` | `/tmp/ceo-p2-proj` **(moved)** | same refusal — correct here |

Row 2 is the defect: the var moved nothing for this caller, and the PRIMARY
block was suppressed anyway. `ceo-cost.py:120-128` *does* honour
`CEO_AUDIT_LOG_PATH` ("wins all"), so the shared helper is right for that
caller and wrong for this one.

**CURED, D1-shaped** (the instrument keeps the predicate, the caller declares
its domain): `audit_source_is_pinned(path_arg, carriers=None)` defaults to
the full `AUDIT_PATH_ENV_CARRIERS`; `budget-summary` passes
`_AUDIT_ENV_CARRIERS = ("CEO_AUDIT_LOG_DIR",)` with `default_audit_dir()`
named as the reason. Deleting `CEO_AUDIT_LOG_PATH` from the shared constant
was rejected — it would break `ceo-cost.py`, which obeys it.

**Positive control:** `--which carrier` reverts the caller to the bare call →
`AuditCarrierTests::test_log_path_alone_does_not_pin_this_caller` **FAILS**
(`True is not false`). Three sibling tests keep the cure from becoming a
removal: the `CEO_AUDIT_LOG_DIR` leg still pins, an explicit `--audit-dir`
still pins, and the instrument's DEFAULT domain still reads both carriers.

## [P2] Register the new transcript-root environment variable
`.claude/scripts/ceo-cost-transcripts.py:671`

> This adds a public `CEO_*` control without updating
> `.claude/scripts/env-inventory.json`.

**REAL but DECLARED, not cured** — this is residual R1, inherited from v1 and
unchanged by these cures. Two reasons, both structural:

1. `.claude/scripts/env-inventory.json` is outside this pack's FILE
   ASSIGNMENT, and `env-inventory-check.py --generate` rewrites the WHOLE
   inventory, sweeping in five other waves' un-triaged drifts.
2. **The gate is already RED on the base commit** for five unrelated vars
   (`CEO_AUDIT_FAMILY_M4_REQUIRED`, `CEO_LEDGER_CHECKPOINT`,
   `CEO_LEDGER_CHECKPOINT_REQUIRED`, `CEO_LEDGER_WRITE_GATE_ENFORCE`,
   `CEO_SESSION_MEMORY_DELTA`). This pack changes the gate's COUNT (5 → 6),
   not its verdict.

Handed to the lander in DESIGN §Residuals R1: run the regeneration
deliberately, with those five drifts triaged, in the wave that owns that file.

---

## Not raised, and why that matters

The round did **not** re-raise the two findings this pack exists to cure
(A: silently dropped audit-side blocks; B: the unconditional ratified
override). Both cures were already in the reviewed tree.

## Battery after the cures

`138 passed` on the four test files (was 132 before section 7 — +1 P1 test,
+1 clock test, +4 carrier tests). Full battery in EVIDENCE.md §2.
