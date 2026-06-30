---
id: ADR-072
title: Test discovery via conftest.py — sys.path.insert retirement (97 sites retired in tests/)
status: ACCEPTED
created: 2026-04-22
proposed_by: CEO + Principal QA + Principal Performance (PLAN-051 Phase 2.5)
accepted_at: 2026-04-24
accepted_via: Round-20 sentinel + Phase 7 retirement commit 7412ef6 (soak 7→3 days per Owner directive 2026-04-24 recorded in PLAN-051 §Phase 7 amendment)
related_plans: [PLAN-051, PLAN-050]
related_adrs: [ADR-031]
blast_radius: L3-wide (escalated from L2 per VP Engineering — 97-file mass edit; canonical-edit via sentinel not required since tests/*.py are not canonical-guarded, but soak discipline applied per §Phase 7)
supersedes: none
superseded_by: none
gates_phase: PLAN-051 Phase 7
---

# ADR-072 — Test discovery via conftest.py

## Context

`hooks/tests/conftest.py` was created in PLAN-050 Session 56 (commit
`42c104a`) under round-17 sentinel. It enables pytest root-discovery
for `.claude/hooks/_lib/*` modules without per-test `sys.path.insert(0,
...)` boilerplate.

**Current state:**
- conftest.py is on disk and pytest collects it.
- 107 `sys.path.insert(...)` call sites remain in `hooks/tests/*.py`
  (Code Reviewer grep-verified vs 91 plan-stated baseline).
- Active 7-day soak window: 2026-04-22 → 2026-04-29.
- Soak validates conftest.py introduces no new flakes before mass
  retirement.

PLAN-051 Phase 7 retires the 107 call sites IF soak completes green.

## Options considered

### Option A (DEFAULT — proposed) — Retire 107 sites if soak green

- Remove 107 `sys.path.insert(...)` statements from `hooks/tests/*.py`
- conftest.py absorbs via pytest root-dir discovery
- conftest.py MUST be **import-free at module scope** (no `from _lib
  import X` at top); all setup via fixtures
- Static check: `grep -nE "^(from|import) " conftest.py` returns only
  stdlib imports

### Option B (FALLBACK) — Refuse if soak breaks

- Roll back conftest.py via single-commit revert
- ADR-072 flips PROPOSED → refused (taxonomy reason (a) technical-
  infeasibility OR (b) cost-exceeds-benefit per observed flake data)
- Refused-ADR skeleton pre-drafted at `adr-drafts/ADR-072-refused-
  skeleton.md` ready to flip on day-of
- 107 `sys.path.insert` sites remain as-is

### Option C (REJECTED) — Partial retirement

- Removing ~50 of 107 sites pilot-style
- Rejected: half-state increases cognitive load + governance complexity
  more than full retirement; partial is worst-of-both-worlds

## Decision

**Conditional decision:** Option A IF Phase 7 soak gate (2026-04-29)
passes per `PLAN-051/soak-policy.md`; Option B otherwise.

**Soak policy** (QA Risk #4 — committed at `.claude/plans/PLAN-051/
soak-policy.md`):

- 0 **new** flakes in conftest-affected tests during 7-day window
- ≤2 **pre-existing** flakes tolerated IF they also appeared in
  pre-soak (Phase 0.5) baseline
- Any new flake in conftest-affected tests → resets soak (new 7-day
  window)
- Diagnostic step required BEFORE refused-flip: ≥1 hypothesis + 1
  targeted test
- Soak status tracked daily in `PLAN-051/soak-log.md`

## Decision drivers

1. **Discovery contract change.** Moving from explicit per-module
   `sys.path.insert` (module-local intent) to implicit pytest rootdir
   conftest (framework-wide intent) is a **System Boundary change**
   (skill §System Boundaries — Test Harness ↔ Hook Modules) requiring
   ADR per skill §When to Refactor vs Rewrite.

2. **VP Engineering blast-radius escalation.** 107 files = 18× the skill
   threshold for "ADR mandatory" (5+ files). Originally categorized
   L2 in PLAN-051 §2; consensus Cluster 1 escalated to L3.

3. **Adopter-facing impact.** `install.sh` ships `templates/` that may
   include conftest.py in adopter-facing test scaffold. Discovery-
   contract change propagates to adopter installations. Documented in
   §Consequences.

4. **Performance gate** (Performance Risk #4):
   - pytest collection time p95 delta ≤ +5% vs Phase 0.5 baseline
   - pytest full suite wall-clock p95 delta ≤ +5%
   - per-test-file import cost p95 delta ≤ +2ms
   - conftest.py import-free at module scope

5. **Reversibility.** Single-commit revert of conftest.py + restore of
   107 `sys.path.insert` from git history. Round-18 promote includes
   the revert script as a `PLAN-051/scripts/revert-conftest-mass-edit.sh`
   ready-to-run artifact.

## Consequences

### Positive (if Option A succeeds)
- 107 call sites removed = ~107 LoC reduction in tests/
- Lower barrier to writing new tests (no boilerplate import path
  required)
- conftest.py becomes the single source of test-discovery truth
- pytest idiomatic pattern adopted

### Positive (if Option B fires)
- No regression risk on existing 2517/5 hook test baseline
- ADR-031 canonical-edit discipline preserved
- Refused outcome documented per taxonomy

### Negative / Accepted trade-offs
- **All adopter installations downstream** must rebase to conftest.py
  pattern at v1.9.0+ (or stay on v1.8.0). Documented in CHANGELOG +
  install.sh --verify --pre-upgrade-check.
- Test-discovery debugging now requires understanding pytest rootdir
  semantics (vs explicit `sys.path.insert` line that was self-documenting).
- conftest.py becomes a critical-path file (changes affect every test);
  must remain in canonical-guard scope per ADR-031.

## Blast radius

**L3-wide.** Touches:
- `.claude/hooks/tests/conftest.py` (existing — canonical-guard)
- 107 `.claude/hooks/tests/*.py` files (mass `sed`/`awk` removal of
  `sys.path.insert(...)` lines)
- `templates/.claude/hooks/tests/conftest.py` (adopter template — if
  exists; verify in Phase 7)
- `install.sh` (potentially: conftest.py copy logic if templated)
- `validate-governance.sh` (potentially: add static check for conftest
  import-free invariant)

## Dual co-sign (PLAN-051 §3.1)

- **Principal QA Architect:** ✅ co-author (soak-policy + flake
  interpretation rule per QA Risk #4)
- **Principal Performance Engineer:** ✅ co-author (perf gates for
  retirement per Performance Risk #4)
- **VP Engineering:** ✅ co-signed (L2 → L3 escalation rationale per
  skill §When to Refactor vs Rewrite)
- **Principal Security Engineer:** ✅ reviewed (no new attack surface;
  static check for conftest import-free covers shadow-import concern)

## Lifecycle

- **PROPOSED-STAGED** (this commit) — Phase 2.5 draft
- **PROPOSED canonical** — round-18 promote
- **ACCEPTED** — Phase 7 execute on 2026-04-29+ if soak green
- **REFUSED** — Phase 7 fallback if soak breaks; refused-skeleton
  flips to ACCEPTED
- **SUPERSEDED** if future ADR migrates to plugin-based discovery (e.g.
  pytest-rootdir-config) — would require new debate

## References

- PLAN-050 Session 56 commit `42c104a` (conftest.py canonical promote)
- PLAN-051 §Phase 7 Acceptance + soak-policy.md
- PLAN-051 baselines/perf-snapshot.json (sys_path_insert_call_sites: 107)
- PLAN-051 Round 1 debate consensus.md Cluster 1 (L3 escalation)
- ADR-031 canonical-edit sentinel chain
- skill `architecture-decisions` §When to Refactor vs Rewrite

## Enforcement commit

**Enforcement commit:** `7412ef6` — Phase 7 C2 mechanical retirement
landing 2026-04-24 (Session 59 cont). 97 `sys.path.insert` lines
removed from `.claude/hooks/tests/` + 54 orphan `if str(X) not in
sys.path:` blocks cleaned; 2 PRESERVED (scripts/-targeting inserts
in `test_emit_architect_outcome.py`); hook suite 2517/5 baseline
preserved byte-identical; `validate-governance.sh` 0 errors / 6
warnings PASS. Soak window 7→3 days per Owner directive 2026-04-24
(PLAN-051 §Phase 7 amended; audit trail preserved in plan +
soak-log.md). ACCEPTED via Round-20 sentinel approved.md
(`.claude/plans/PLAN-051/architect/round-20/`, GPG-signed by
0000000000000000000000000000000000000000).
