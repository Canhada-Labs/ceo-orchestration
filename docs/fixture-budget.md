# Fixture corpus budget & hygiene

> **Status:** active (PLAN-019 Perf-P2-006)
> **Owner:** `@Canhada-Labs`
> **Enforced by:** advisory in `.claude/scripts/check-fixture-budget.py` (stdlib, optional)
> **Related ADR:** (none — this is a working-code hygiene doc, not an architectural decision)

## 1. Why a budget

Test fixtures grow. What starts as one `sample_event.json` becomes a
tree of 400 files as every hook accumulates a payload for every case
it ever shipped. Left unbounded, fixture corpora:

- **Inflate the repo clone size** — a 50 MB fixture set adds a
  perceptible pause to `git clone` and forces LFS discussions that
  aren't necessary.
- **Slow pytest collection** — pytest's fixture-discovery step
  walks every directory under the test root. A corpus with
  thousands of files costs observable wall clock on every CI run.
- **Hide duplication** — copy-pasted fixtures across hooks become
  drift when the canonical-envelope schema evolves. A budget forces
  engineers to pause and check "do I already have this fixture?"
- **Obscure intent** — a 5-line fixture is read at a glance; a
  5000-line fixture is opaque. The budget forces fixture authors to
  trim noise and keep payloads representative + minimal.

## 2. Budget targets (soft + hard)

| Scope | Soft cap | Hard cap | Rationale |
|---|---:|---:|---|
| Any single fixture file | 16 KB | 256 KB | One canonical envelope or one audit-log row is <1 KB; 16 KB holds a multi-event sequence. 256 KB upper bound rejects accidentally-checked-in dumps. |
| Per-hook fixtures directory (`.claude/hooks/tests/fixtures/<hook>/`) | 256 KB | 1 MB | Each hook owns adapter-in + adapter-out samples; 1 MB accommodates ~1000 typical fixtures before signaling bloat. |
| Per-script fixtures directory (`.claude/scripts/tests/fixtures/<script>/`) | 256 KB | 1 MB | Same rationale as hooks. |
| Policy fixtures (`.claude/policies/fixtures/`) | 256 KB | 1 MB | Policy conformance fixtures rarely exceed 100 kb; 1 MB accommodates full-coverage mutation fixtures. |
| Integration fixtures (`tests/integration/fixtures/`) | 256 KB | 2 MB | E2E fixtures can bundle multi-file configurations (settings.json + claude.md + a skill). |
| Total repo fixture footprint | 4 MB | 10 MB | Cumulative ceiling across the tree. 10 MB is the break-even point where `git clone` latency starts to show. |

**As of 2026-04-17** (PLAN-019 snapshot):
- `.claude/hooks/tests/fixtures/` → 260 KB
- `.claude/scripts/tests/fixtures/` → 428 KB
- `.claude/policies/fixtures/` → 40 KB
- `tests/integration/fixtures/` → 12 KB
- **Total:** ~740 KB → well inside soft cap

## 3. What counts as a "fixture"

- Any file under `tests/fixtures/` or `*/tests/fixtures/` / `*/fixtures/`.
- Any file the tests read via `Path(...).read_bytes()` /
  `read_text()` whose content is not source code.
- JSON / JSONL / YAML / textual input payloads.

**NOT** a fixture:
- Snapshot / golden outputs (those are also fixtures but tracked
  under the same budget — they all count).
- Generated fixture content (fixture-generator scripts OK; the
  corpus output must still fit under the cap).
- Images / binary blobs (reject: no image fixtures in this repo;
  if you need one, open an ADR first).

## 4. Hygiene discipline

### 4.1 Retire fixtures when the hook retires

When a hook is removed or replaced, its fixtures MUST be removed in
the SAME PR (not "later"). A stale fixture directory under a
removed hook is a smell — it suggests the removal was incomplete.

### 4.2 Favour fixture generators for large sets

If a test needs 100 similar payloads (e.g. all OWASP-basics
prompts), prefer a **generator** (`tests/_gen_fixtures.py`) over
100 checked-in files. The generator runs at test-time (fast,
stdlib-only) and keeps the repo diff reviewable. Only check in
fixtures when the exact bytes matter (e.g. byte-identity fixtures
for `_lib/testing.py::BYTE_IDENTITY_FIXTURES`).

### 4.3 Review fixture diffs carefully

Fixture diffs are harder to review than source code diffs. When
adding a fixture, include a one-line comment at the top or in the
corresponding test explaining what the fixture exercises. Reviewers
should push back on unexplained fixture additions.

### 4.4 Prune before optimising

If a fixture directory is nearing its soft cap, first audit for:
- Duplicate fixtures (two tests reading the same payload under
  different names).
- Overly-verbose fixtures (a 16 KB JSON where 1 KB would suffice).
- Stale fixtures (referenced by no test — `git grep` confirms).

Only after pruning, if the directory still overflows, discuss with
the CEO whether the scope warrants expanding the cap.

## 5. Enforcement mechanism

### 5.1 Advisory check (post-PLAN-019)

Post-PLAN-019 Phase 4, a `.claude/scripts/check-fixture-budget.py`
script will walk the fixture directories and emit warnings when any
cap is exceeded. Wired as an **advisory** step in `validate.yml`
(no `|| true` flip; exit 0 on soft overflow with warning, exit 1
on hard-cap overflow). Sprint 16+ may promote soft-cap overflows
to hard-fail per skill hygiene mandate.

### 5.2 CI hard gate

The **total repo fixture footprint hard cap (10 MB)** is a CI
hard-fail at all times — no soft-cap grace. The rationale is
concrete (10 MB = break-even for `git clone` latency), the measurement
is trivial (`du -sb` the fixture roots), and the cost of policing is
amortised.

## 6. Exception policy

Exceptions to the budget require:
1. An ADR entry explaining the unique need (e.g. a fuzz corpus for
   a parser).
2. The exceptional fixture is isolated to its own subdirectory so
   accounting stays clean.
3. The ADR lists the retirement condition (e.g. "remove when fuzz
   coverage covered by mutation harness").

See `.claude/adr/README.md` for ADR template.

## 7. See also

- `.claude/skills/core/performance-engineering/SKILL.md` — perf
  discipline, includes fixture corpus as one budget dimension.
- `.claude/skills/core/testing-strategy/SKILL.md` — fixture
  authorship patterns.
- `.claude/plans/PLAN-019/progress.md` — delivery tracking.
