# ADR-014: Hook Adapter Migration Batch Policy

## Status: ACCEPTED (2026-04-13)


**Supersedes (partial):** [ADR-004](./ADR-004-defer-bash-legacy-removal.md) §Sprint 6 Phase 6b — this ADR's "Gate B (direct test)" amendment (R-VP7 consensus item K9) is what unlocked the legacy/ removal without invariant 3 organic-spawn satisfaction. ADR-004 remains the canonical record of the deferral history; this ADR carries the reusable Gate B pattern forward.
## Context

ADR-008 (Hook Adapter Layer) shipped the contract + Claude adapter in
Sprint 4 Phase 4 as refactor-only additive work. ADR-008 §Options Option B
("Ship contract + rewire all 4 hooks in one commit") was **explicitly
rejected** with rationale: "~400 LOC across 4 hooks; high regression
risk; 168 tests must all verify behavior preserved under a refactor
that's hidden inside `decide()` rewrites."

ADR-008 §"What the contract does NOT ship" also declared: "Hook rewiring
(deferred to Sprint 5; each hook migrates independently)."

PLAN-006 Sprint 6 now reverses both deferrals: migrates **6 hooks**
(the original 4 plus `check_read_injection.py` + `check_canonical_edit.py`
added in Sprint 5) in a single phase. The blast radius is larger than
ADR-008 considered, and the reversal needs its own decision record.

**PLAN-006 debate round 1** (2026-04-13) verdict 3/3 ADJUST flagged this
as Must-fix #2 (VP Engineering R-VP2):

> "ADR-008 §'What the contract does NOT ship' explicitly scopes OUT
> 'hook rewiring'. The plan migrates all 6 hooks in a single phase,
> which is exactly Option B that ADR-008 rejected. The plan escalates
> from 4 to 6 hooks and reverses the 'each hook migrates independently'
> stance without writing the ADR. Per the architecture-decisions skill
> 'Fail-Fast Rule': irreversible + 3+ modules → ADR FIRST."

This ADR settles the decision before any Phase 1 commit lands.

## Decision Drivers

- **Rollback atomicity.** A broken migration must be revertible per-hook,
  not "revert 6 commits".
- **Review latency.** A single 400+ LOC PR is harder to review than
  6 × 50-100 LOC PRs.
- **Test signal.** Each hook's byte-identity fixture (new in PLAN-006
  Phase 1 pre-work) must pass ON THE COMMIT that migrates that hook —
  not "eventually on a merge commit".
- **Mixed-mode support.** If hook N migrates but hook N+1 is blocked,
  the intermediate state must be valid (some hooks via contract,
  others via raw stdin).
- **Contract completeness.** ADR-008's contract lacks `phase`
  distinction (R-SB1: `_lib/adapters/claude.py:51` hardcodes
  PreToolUse). Extending the contract is pre-work that must land
  BEFORE any hook migrates.

## Options Considered

### Option A: Migrate all 6 hooks in one commit

- **Pros:** single PR, one review pass, single CI gate.
- **Cons:** 6× the regression surface of ADR-008's rejected Option B;
  rollback = revert a 400+ LOC commit; any one hook's byte drift blocks
  the whole PR; mixed-mode never exists as a deliberate state.

### Option B: Migrate 1 hook per commit (chosen)

- **Pros:** per-hook rollback is `git revert <sha>`; each commit is
  small enough for meaningful review; byte-identity test fails per-hook
  with clear attribution; mixed-mode intermediate state is explicit
  and supported.
- **Cons:** 6 commits + 1 pre-work commit = 7 commits in one phase;
  each commit must keep all tests green including byte fixtures for
  both migrated-and-not-yet-migrated hooks.

### Option C: Split across Sprints 6 and 7 (3 + 3)

- **Pros:** lower per-sprint risk; each sprint has time for post-merge
  observation.
- **Cons:** doubles the mixed-mode window; Gemini adapter (Sprint 6
  Phase 2a) stays speculative longer; prolongs `_lib.payload` vs.
  `NormalizedEvent` duality ADR-008 Consequences §Negative flagged.

## Decision

**Option B.** 1 hook per commit, all 6 in Sprint 6, preceded by 1
pre-work commit that extends the contract.

### Commit order (low-risk → high-risk)

1. Phase 1 pre-work commit: `phase` parameter + PostToolUse fixture +
   per-hook byte-identity fixtures + `test_hook_byte_fidelity` +
   `test_fail_open_contract`
2. `check_bash_safety.py` (simplest, pure-PreToolUse)
3. `check_canonical_edit.py` (simple, PreToolUse)
4. `check_plan_edit.py` (PreToolUse, uses `_lib/plan_frontmatter`)
5. `check_read_injection.py` (PreToolUse, uses `_lib/redact`)
6. `check_agent_spawn.py` (most complex rules)
7. `audit_log.py` (**PostToolUse** — exercises new `phase` path)

### Per-commit acceptance gates

Each migration commit MUST:
- Keep all 231 existing hook tests green
- Keep `test_hook_byte_fidelity[<hook>]` green for THIS hook's fixture
- Keep `test_fail_open_contract[<hook>]` green for THIS hook
- Keep byte fixtures of all yet-unmigrated hooks green (mixed-mode)
- Replace direct `sys.stdin.read()` + `print(json.dumps(...))` with
  `read_event()` / `write_decision()`

### Mixed-mode support guarantee

During the rollout window (commits 2-7), the repository is always in
a valid state. Specifically:
- Migrated hooks use the adapter contract
- Unmigrated hooks use `_lib/payload.parse_stdin` and direct print
- Both paths coexist in the same Python environment with no shared
  mutable state
- `CEO_HOOK_ADAPTER=claude` is the default; unset env-var works
  identically; both adapter-using and non-adapter-using hooks
  honor fail-open on malformed stdin

### Rollback command per hook

```
git revert <sha>                  # per-hook commit
pytest .claude/hooks/tests/       # confirm green
git push
```

No multi-hook revert chain is needed. If hook N migration is reverted,
hooks N+1..6 continue on their current path (migrated or not).

## Consequences

### Positive

- **Atomic per-hook rollback.** A regression in `check_agent_spawn`
  migration does not force reverting `check_bash_safety` migration.
- **Reviewable commits.** Each commit is ~50-100 LOC + a paired
  byte-fixture test — small enough for meaningful review.
- **Mixed-mode is explicit.** The README / docs/adapters.md document
  that some hooks may be on either path during rollout.
- **Byte fixtures force discipline.** `test_hook_byte_fidelity` fails
  if stdout drifts by a newline or key reorder. ADR-008 §Decision
  line 111 ("Observable output MUST remain byte-identical") is now
  enforced mechanically.

### Negative

- **6 migration commits + 1 pre-work** = 7 commits in Phase 1.
  Historical velocity (Sprint 5 shipped 8 commits across 7 phases)
  suggests this consumes significant sprint budget. Mitigated by
  Phase 0 (ADR) being small and hooks being serial (low per-hook time).
- **Mixed-mode doubles test surface.** `test_hook_byte_fidelity` runs
  for all 6 fixtures on every commit — the fixtures for not-yet-migrated
  hooks must match the pre-migration baseline (captured in pre-work
  commit). If the baseline itself was wrong, the first hook migration
  exposes it.

### Neutral

- Phase 1 phase gate becomes "all 6 migration commits + pre-work merged
  on main". Phase 2a / Phase 3 / Phase 5b open PRs only after this gate.

## Blast Radius

- `.claude/hooks/_lib/contract.py` (EXTENDED — phase parameter)
- `.claude/hooks/_lib/adapters/claude.py` (EXTENDED — phase dispatch)
- `.claude/hooks/_lib/adapters/gemini.py` (NEW stub — Phase 2a)
- `.claude/hooks/tests/fixtures/adapters/claude/in/post_audit_event.json` (NEW)
- `.claude/hooks/tests/fixtures/normalized/post_audit_event.json` (NEW)
- `.claude/hooks/tests/fixtures/hooks/<hook>/{in,out}.bytes` (NEW, 6 hooks × 2 files)
- `.claude/hooks/tests/test_hook_byte_fidelity.py` (NEW)
- `.claude/hooks/tests/test_fail_open_contract.py` (NEW)
- `.claude/hooks/check_bash_safety.py` (MIGRATED)
- `.claude/hooks/check_canonical_edit.py` (MIGRATED)
- `.claude/hooks/check_plan_edit.py` (MIGRATED)
- `.claude/hooks/check_read_injection.py` (MIGRATED)
- `.claude/hooks/check_agent_spawn.py` (MIGRATED)
- `.claude/hooks/audit_log.py` (MIGRATED — PostToolUse)
- `.github/workflows/smoke-install.yml` (paths filter extended to
  `.claude/hooks/**` for Sprint 6 duration)

**Reversibility:** HIGH per-hook via `git revert`. MEDIUM for the
Phase 1 pre-work commit (reverting the contract extension un-migrates
`audit_log.py`'s phase handling; mitigated by reverting in reverse
order: hook 6 first, then pre-work).

## References

- ADR-008 — Hook Adapter Layer foundation (§Options Option B rejection
  now superseded for Sprint 6 scope)
- PLAN-006 §Phase 0, §Phase 1 pre-work, §Phase 1 migrations
- PLAN-006/debate/round-1/vp-engineering.md §R-VP1, §R-VP2
- PLAN-006/debate/round-1/staff-backend-engineer.md §R-SB1
- PLAN-006/debate/round-1/consensus.md §C1, §C2

## Enforcement commit

`5398f1b81014` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
