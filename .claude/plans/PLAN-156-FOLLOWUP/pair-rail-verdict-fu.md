# PLAN-156-FOLLOWUP — pair-rail per-file verdicts (staged pack, pre-ceremony)

- **Reviewer:** codex-cli 0.144.1 (`codex exec --sandbox read-only`, staged-vs-canonical diff pipe)
- **Date:** 2026-07-13 (S272)
- **Input:** the 7 changed files of the F1–F7 staged pack
- **Advisory only** — the decision is the CEO's; the Owner signs the sentinels
  ([[feedback-pair-rail-clean-round-not-proof]]). Stopping criterion: every file
  APPROVE, each REJECT folded and re-reviewed.

## Round 1 — 4 APPROVE / 3 REJECT

```text
FILE: .claude/hooks/_lib/codex_egress_redact.py — APPROVE
FILE: .claude/commands/council.md — APPROVE
FILE: .claude/hooks/check_canonical_edit.py — APPROVE
FILE: scripts/_grok_harness.sh — APPROVE
FILE: .claude/workflows/council-audit.js — REJECT — Missing scope still falls back to whole-repo egress.
FILE: .claude/hooks/_python-hook.sh — REJECT — Malformed deny-bearing hook output is not actually blocked on grok.
FILE: templates/grok/pre-push-review-gate.sh — REJECT — Oracle-failure fallback can still accept sidecar fingerprints.
OVERALL: REJECT
```

**All three verified against the code and folded:**

1. **council-audit.js** — `args.scope` missing → `'.'` = the WHOLE REPO goes to
   the external vendor lanes. This is the second half of the very S270 bug the
   plan exists to fix (F7 corrected the invocation layer; the workflow's silent
   default survived). Now **fail-CLOSED**: a missing/blank scope throws; fixture
   mode keeps its scope-free path.
2. **_python-hook.sh** — the shim re-emitted the hook's raw stdout BEFORE
   parsing the decision. On grok the stdout JSON is the PRIMARY block, so a
   malformed deny-bearing payload reached grok as garbage (fails open) leaving
   only the secondary exit-2 rail — turning belt-and-suspenders into one strap.
   Now: **parse first, emit second**; an unparseable-but-deny-bearing payload
   emits a well-formed `{"decision":"deny"}` (original preserved on stderr) and
   exits 2. The INFRASTRUCTURE fail-open half is untouched.
3. **pre-push-review-gate.sh** — under oracle degradation the gate still allowed
   **sidecar** acceptance keyed on a COARSE fingerprint — exactly the
   collision-prone value the security VETO forbade (review-reuse). Now degraded
   mode is **trailer-only**.

## Rounds 2–6 — the gate, four more fail-open findings

The gate needed five rounds. Every finding was verified in the code before
folding; each carries a regression test (parity suite 11/11):

| Round | Finding (all fail-OPEN) | Fix + test |
|---|---|---|
| R2 | Coarse fallback OMITTED `templates/`, `.grok/`, `.codex/`, `AGENTS.md`, `requirements.toml` — the egress + kill-switch + distribution surfaces. A degraded push touching only those classified an EMPTY set → exit 0. "Over-triggers = fail-CLOSED" was simply false. | Coarse arm is now a **superset** of the oracle's first segments. `CoarseSupersetInvariantTest` **parses the case block out of the gate** and asserts containment (teeth: against the pre-fix gate it reports `['.codex','.grok','templates']`). |
| R3 | `_changed_paths_in_range` used the **endpoint diff** for existing branches: an edit+revert range nets to empty → exit 0, while the intermediate commit still carries the unreviewed canonical edit to the remote. | **Per-commit union everywhere.** `test_reverted_canonical_edit_in_range_still_gates` (fixture asserts the endpoint diff IS empty, then asserts the gate blocks). |
| R4 | New-branch arm used `git rev-list <local> --not --all`; `--all` includes the local ref being pushed, **self-subtracting the range to empty** → first push of a branch with canonical edits sailed through. (Pre-existing, made critical by R3 making the union the only path source.) | `--not --remotes`. Empirically confirmed: `--not --all` → 0 commits, `--not --remotes` → 2. `test_new_branch_first_push_still_gates`. |
| R5 | Both `git diff-tree` calls lacked `--root`, so a **root commit** (no parent) emitted no paths — a first push whose root commit adds canonical files passed. | `--root` on both. `test_root_commit_canonical_paths_are_classified`. |
| R6 | — | **APPROVE.** |

## Net result

| File | Verdict |
|---|---|
| `.claude/hooks/_lib/codex_egress_redact.py` | APPROVE (r1) |
| `.claude/commands/council.md` | APPROVE (r1) |
| `.claude/hooks/check_canonical_edit.py` | APPROVE (r1) |
| `scripts/_grok_harness.sh` | APPROVE (r1) |
| `.claude/workflows/council-audit.js` | APPROVE (r2, after fold) |
| `.claude/hooks/_python-hook.sh` | APPROVE (r2, after fold) |
| `templates/grok/pre-push-review-gate.sh` | APPROVE (r6, after four folds) |

**7/7 APPROVE.** The ceremony may proceed (`land-followup.sh`, dry-run green:
preflight + both segments + 4553-test canonical post-apply pass).

## Note for the record

The gate took five rounds because F5's own fix (aggregate fingerprint parity)
opened a new class of blind spot in the RANGE COMPUTATION — a class no debate
critic named, because all three reasoned about *which paths are canonical*
(classification) and none about *which commits the gate even looks at*. This is
the second S272 confirmation of [[feedback-livefire-catches-what-fixtures-miss]]
in a new key: the fixture suite was green after every one of these five defects.
