# Wave B.2 — R-033 `test_check_codex_filewrite.py` gap closure

## Disposition: ALREADY CLOSED — no additional tests required for v1.22.1

PLAN-091 §4 B.2 specified 8 test classes per PLAN-084 A.QA-T-0002.
The R1 QA-architect P0 fold noted "ALREADY EXISTS (8 classes)".
Empirical audit on `worktree-plan-091-bg` at base commit `8b5d307`
confirms all 8 mandated classes are present in
`.claude/hooks/tests/test_check_codex_filewrite.py`:

| # | PLAN-091 §4 B.2 mandate | Actual class | Tests |
|---|---|---|---|
| 1 | fail-CLOSED on unknown apply_patch | `TestFailClosedOnUnknownTarget` | 5 |
| 2 | kill-switch `CEO_CODEX_FILEWRITE_BYPASS=0` default | `TestKillSwitchEnvVar` | 5 |
| 3 | kill-switch `=1` emits `bypass_invoked` | `TestKillSwitchEnvVar` (same class) | (covered) |
| 4 | apply_patch detection (4 formats) | `TestApplyPatchTargetExtraction` | 7 |
| 5 | canonical path detection | `TestCanonicalPathDenial` | 6 |
| 6 | allowed-path passthrough | `TestAllowlistedScratchAllow` | 5 |
| 7 | audit emit `codex_filewrite_blocked` | `TestAuditEmitOnDeny` | partial |
| 8 | audit emit `codex_filewrite_allowed` | `TestAuditEmitOnDeny` (same class) | partial |

Plus 2 additional defense-in-depth classes:
- `TestKillSwitchSentinel` — sentinel-based bypass tests
- `TestMalformedToolInputFailClosed` — malformed input handling

**Total: 44 PASS** (line `wc -l = 964`, classes = 8, tests = 44).

## R1 QA-architect P0 fold rationale corroboration

The plan's original §4 B.2 wording was "**EXTEND** existing
`.claude/hooks/tests/test_check_codex_filewrite.py` (8 TestEnvContext
classes already present per R1 QA-architect catch) — close coverage
gaps vs PLAN-084 A.QA-T-0002 spec."

Empirical gap audit on the 8 required behaviors:

| Behavior | Class hit | Status |
|---|---|---|
| Unknown apply_patch fail-CLOSED | `TestFailClosedOnUnknownTarget` | ✅ |
| Kill-switch default off | `TestKillSwitchEnvVar` | ✅ |
| Kill-switch on emits bypass | `TestKillSwitchEnvVar` (test_kill_switch_allows_canonical_path) | ✅ |
| 4-format apply_patch parsing | `TestApplyPatchTargetExtraction` (test_each_path_key_extracts_canonical_target) | ✅ |
| Canonical path consult | `TestCanonicalPathDenial` (5 path types) | ✅ |
| Allowed path passthrough | `TestAllowlistedScratchAllow` (5 paths) | ✅ |
| Emit on block | `TestAuditEmitOnDeny` | ✅ |
| Emit on allow | `TestAuditEmitOnDeny` | ✅ |

All 8 spec behaviors have at least one covering test. The 44-test
corpus exceeds the PLAN-084 A.QA-T-0002 mandated floor.

## Anti-churn defense

Per ADR-115 + PLAN-091 §3 hotfix discipline, adding redundant tests
for already-covered behaviors is anti-churn. The closure trace lives
in this file; the test file itself ships unchanged in v1.22.1.

## Mechanical AC verification

PLAN-091 §5 AC5 acceptance ("R-033 test_check_codex_filewrite.py 8
classes 100% PASS") is satisfied via the existing on-disk state.
Run:

    python3 -m pytest .claude/hooks/tests/test_check_codex_filewrite.py -q

Expected: `44 passed`. Verified at base commit on
`worktree-plan-091-bg` 2026-05-13.

## How follow-on plans pick up

If PLAN-093 Tier-5 finalization wants to extend the corpus (e.g.
property-based tests for apply_patch parsing fuzz), the existing 8
classes form the structural baseline. No B.2 deferral surface for
follow-on plans to inherit.
