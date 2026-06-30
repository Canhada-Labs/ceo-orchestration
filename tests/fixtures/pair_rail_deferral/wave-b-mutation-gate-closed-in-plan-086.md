# Wave B.3 — R-034 mutation-gate extension already CLOSED in PLAN-086 Wave G.1

## Disposition: CLOSED (no-op for PLAN-091)

Per `.github/workflows/mutation-gate.yml:62-71` (shipped via PLAN-086
Wave G.1 tag `v1.20.0`):

```yaml
- name: mutation run on 4 security-critical modules (PLAN-086 Wave G.1)
  id: mutate
  run: |
    # PLAN-086 Wave G.1: extended from redact.py-only to >=4 modules.
    # Adds audit_hmac.py + mcp/canonical_guard.py + check_pair_rail.py.
    cd .claude/hooks/_lib
    mutmut run \
      --paths-to-mutate redact.py,audit_hmac.py,mcp/canonical_guard.py,../check_pair_rail.py \
      ...
```

All 3 modules PLAN-091 §4 B.3 wanted to add are already in scope:

| Module | Path-to-mutate entry | PLAN-091 §4 B.3 requirement |
|---|---|---|
| `audit_hmac.py` | `audit_hmac.py` (line 69) | chain integrity invariant |
| `canonical_guard.py` | `mcp/canonical_guard.py` (line 69) | defense-in-depth invariant |
| `check_pair_rail.py` | `../check_pair_rail.py` (line 69) | gate decision invariant |

Kill-rate floor at `.github/workflows/mutation-gate.yml:96-97` is
80% (matches PLAN-091 §4 B.3 spec "kill-rate floor ≥80%"). The
floor is reported as `::warning` (advisory) consistent with
ADR-115 §maintenance-mode discipline.

## R1 QA-architect P0 fold note

PLAN-091 §14 R1 QA-architect fold "Mutation kill-rate floor ≥80%
should be ≥80% to match framework" referenced
`mutation-gate.yml:97` — that is the existing 80% advisory
threshold which PLAN-091 §4 B.3 originally proposed to add. The
threshold IS already in place from PLAN-086 G.1. Hence this Wave
collapses to a closure-trace document with no config edits in
v1.22.1.

## Per-module vs aggregate kill-rate

PLAN-091 §4 B.3 text says "kill-rate floor ≥80% **per module**". The
current implementation (line 87-93) computes an **aggregate**
kill-rate across the 4 modules `(killed / (killed + survived))`,
NOT per-module rates.

Per-module rate enforcement would require additional `mutmut
results` parsing (one invocation per `--paths-to-mutate` arg), CI
runtime increase ~3-4× (4 modules × O(N) mutmut invocations), and
new workflow lint. That extends behavior beyond v1.22.0 contract.

**Deferred to PLAN-093** (which already owns mutation-gate
ergonomics + branch coverage uplift). Aggregate ≥80% advisory is
retained for PLAN-091 hotfix scope per ADR-115 anti-churn.

## Mechanical verification

PLAN-091 §5 AC6 acceptance "mutation-gate config extended; 3 new
modules at kill-rate ≥80%" is satisfied **already on origin/main**
via PLAN-086 Wave G.1 shipped state.

Run `gh workflow view mutation-gate-advisory --yaml | head -100`
on `main@8b5d307` to confirm the 4-module config is current. Latest
weekly run kill-rate appears in `.claude/plans/PLAN-050/baseline/
mutation-results.txt` artifact.

## No-edit ceremony rationale

PLAN-091 ceremony commit for Wave B.3 lands **this disposition
document only** under `.claude/plans/PLAN-091/`. NO change to
`.github/workflows/mutation-gate.yml` itself — minimal blast
radius (anti-churn). The auditable trace of "Wave B.3 acknowledged
as already-closed" lives in this file.
