---
id: PLAN-141
title: Make mcp-smoke ruff step tolerant of the absent PLAN-070 staging tree
status: done
created: 2026-06-18
reviewed_at: 2026-06-18
completed_at: 2026-06-18
related_commits: ["599d2cc4381081aca5c6f5a2423fb548bbd5d8f4"]
created_by: "CEO (S244 — CI pendency triage)"
completed_by: "CEO (S245 — status closeout; implementation landed S244)"
owner: CEO
depends_on: []
related_adrs:
  - ADR-010                        # canonical-edit sentinel ceremony — gates this workflow edit
risk_tier: A                       # single CI step made fail-soft; no production code; no gate weakened
target_tag: v1.47.0                # tentative
budget_tokens: 5-10k
budget_sessions: 1
context_risk: low
---

# PLAN-141 — Make the mcp-smoke ruff step tolerant of the absent PLAN-070 staging tree

> **One-line goal:** `mcp-smoke.yml` runs `ruff check` directly over
> `.claude/plans/PLAN-070/staging/*.py`, which the clean-room migration omitted.
> Lint only the staging files that still exist so the smoke run does not
> hard-fail when its path-filter triggers.

## 0. Provenance & honest framing

S244 CI-pendency triage. Of the 3 workflows flagged as referencing deleted-plan
artifacts (coverage/PLAN-093, mcp-smoke/PLAN-070, mutation-gate/PLAN-050), only
mcp-smoke has a real hard-fail: `parse-coverage.py` already skips an absent
`--baseline-md` (coverage), and mutation-gate already guards with
`baseline_f.exists()`. So this PLAN touches ONLY mcp-smoke.

## 1. Root cause

`.github/workflows/mcp-smoke.yml` (~lines 180-185) runs, under `set -euo
pipefail`:

    ruff check --select=E,F,W,I --line-length=100 \
      .claude/plans/PLAN-070/staging/canonical_guard.py \
      .claude/plans/PLAN-070/staging/test_canonical_guard.py \
      .claude/plans/PLAN-070/staging/test_layer_a_mcp_matcher.py

Those staging files were a PRE-PROMOTION copy. The live Layer-B code was promoted
long ago to `.claude/hooks/_lib/mcp/canonical_guard.py` (1140 lines, evolved) and
its tests to `.claude/hooks/tests/` (which the same workflow already runs, lines
204/216). The staging tree is vestigial and the clean-room omitted it, so the
ruff step hard-fails when the workflow's path-filter (check_canonical_edit.py /
mcp/**) triggers.

## 2. Fix (fail-soft, no quality loss)

Lint only the staging files that exist; if none do, print a skip note and
continue. This removes NO real coverage — the live `_lib/mcp/canonical_guard.py`
is already linted/tested/mutation-covered elsewhere. We do NOT re-migrate the
staging tree (it would reintroduce a stale, duplicated copy of code that already
lives, evolved, at the canonical path).

## 3. Why a canonical ceremony

`.github/workflows/*.yml` matches `check_canonical_edit.py` `_CANONICAL_GUARDS`,
so the edit requires an Owner-signed sentinel (ADR-010). Not a kernel path; no
`CEO_KERNEL_OVERRIDE` needed.

## 4. Validation

`actionlint -shellcheck="-S error" .github/workflows/mcp-smoke.yml` clean +
dry-run the bash array logic locally (no staging files present → prints the skip
note, exit 0; with a dummy file present → ruff runs on it).
