# ADR-004: Defer bash legacy hook removal (SUPERSEDED — removed in PLAN-006 Phase 6b)

**Status:** SUPERSEDED (2026-04-13) — legacy/ removed in Sprint 6


**Superseded-By:** Sprint 6 Phase 6b removal commit `32564cc` (2026-04-13); the "Gate B" alternative-removal criterion used by that commit is formalized in [ADR-014](./ADR-014-hook-migration-batch-policy.md) §Gate-B-amendment. No successor ADR replaces this one — the original problem (legacy bash fallback hooks) ceased to exist when the directory was deleted.

**Retirement-via-commit:** this ADR is an example of a "retired-via-commit" supersession: a deferral decision that resolves when the underlying condition (invariants 2/3/4 under Gate A + new Gate B) is met. See `check-adr-chain.py` §inline-retirement-note for the mechanical accept rule.
Phase 6b via Gate B (direct test). See §"Sprint 6 Phase 6b resolution"
at the bottom of this file.
**Date:** 2026-04-12 (original); 2026-04-13 (re-evaluated twice —
Sprint 5 defer, then Sprint 6 resolution)
**Decision drivers:**
- Invariant 3 (50+ Python-hooked spawns) not yet met — audit log has 4
- Invariant 4 (no stale legacy references) not yet met — 5 files reference legacy
- No reason to force removal before the sample-size gate is real

## Context

PLAN-002 §11-bis Q5 set three invariants that must hold before the bash
fallback hooks in `.claude/hooks/legacy/` could be deleted:

1. CI green continuously on both macOS and Linux from A.4 commit onward
2. `audit-log.errors` empty (no infrastructure errors)
3. ≥ 50 real Python-hooked spawns captured in `audit-log.jsonl`

PLAN-003 Item C staged the removal as CONDITIONAL on these invariants.
Sprint 3 added a fourth invariant (debate round 1 consensus S5): no
stale references to `.claude/hooks/legacy/` anywhere in CI/settings/docs.

`.claude/scripts/verify-sprint3-invariants.sh` checks invariants 2, 3,
and 4 mechanically (1 remains manual — CI history).

## Decision drivers

- **Sample size is real.** The 50-spawn threshold is not arbitrary. Before
  50 spawns, failure modes that show up 1-in-20 are still plausible. We
  don't have that many spawns yet — the audit log shows 4.
- **Stale references are concrete work.** Five files still mention
  legacy/: validate.yml, settings.json, settings.base.json, README.md,
  INSTALL.md. Cleaning them up is straightforward but requires the
  removal to be imminent, not speculative.
- **Legacy files are small and inert.** `.claude/hooks/legacy/*.sh`
  totals ~150 lines of shell that nothing executes (settings.json
  points at the Python path via `_python-hook.sh`). Keeping them one
  more sprint is low-cost.

## Options considered

### Option A: Remove now, handle residuals in Sprint 4

Pros: closes a Sprint 3 line item. Cons: violates the stated invariant
gate. The gate exists to prevent removing a safety net we still depend
on. Bypassing the gate for the sake of a closed checkbox is exactly
the failure mode the gate is meant to prevent.

### Option B: Defer to Sprint 4, write this ADR (CHOSEN)

Pros: honors the invariant contract. Gives Sprint 4 a clean plate —
when the audit log crosses 50 spawns and the stale refs are cleaned up,
the removal is a single commit. Cons: legacy/ keeps a modest bloat
cost for one sprint, mostly invisible.

### Option C: Lower the invariant threshold

Pros: technically closes Item C. Cons: retcon. Invariant thresholds
that get lowered to meet a deadline stop being invariants.

## Decision

**Option B** — defer. Item C remains OPEN in PLAN-003 and gets a
follow-up commit in Sprint 4 once all 4 invariants pass
`verify-sprint3-invariants.sh`.

The verify script itself SHIPS in Sprint 3 (this sprint) so the gate
is testable on every commit going forward.

## Consequences

- **Positive:** invariant contract holds. Sprint 4 opens with a concrete
  "remove legacy once this script exits 0" task. No ambiguity.
- **Negative:** `.claude/hooks/legacy/` continues to ship in the source
  repo (already excluded from target installs since PLAN-003 I-4). Minor
  shellcheck bypass entry in CI stays. README/INSTALL keep a pointer
  line.
- **Neutral:** if the framework stops dogfooding itself before Sprint 4
  lands (e.g. abandonment), the bash fallbacks never get deleted. The
  file still works; no harm.

## Blast radius

L2 — affects CI config, settings, docs, and one directory. No runtime
path change since the Python hooks are already the only active path.

## Next action (Sprint 4)

1. Run `bash .claude/scripts/verify-sprint3-invariants.sh` — expect exit 0.
2. Clean stale refs:
   - `.github/workflows/validate.yml` — drop the `-path '*/legacy/*'` shellcheck prune
   - `.claude/settings.json` — drop the `_comment` referencing legacy
   - `templates/settings/settings.base.json` — same
   - `README.md`, `INSTALL.md` — drop the Sprint 3 transition paragraph
3. `git rm -r .claude/hooks/legacy/`
4. Update ADR-004 status: SUPERSEDED by the removal commit SHA.
5. Close PLAN-003 Item C.

## Sprint 5 Phase 3 re-evaluation (2026-04-13)

PLAN-005 Phase 3 was a conditional gate to delete `.claude/hooks/legacy/`
if `verify-sprint3-invariants.sh` exited 0. As of commit `b8d5911`:

- Invariant 2 (audit-log.errors empty): PASS
- Invariant 3 (≥ 50 spawns in audit log): **FAIL** — currently at 18
- Invariant 4 (no stale legacy refs): PASS (cleaned in Phase 0)

Per the original gate contract and the memory rule
`feedback_conditional_gates.md` ("conditional gates beat closed
checkboxes — when invariants fail, write ADR and defer; don't retcon
thresholds"), Phase 3 is **deferred to Sprint 6**.

Stale refs are now clean, so when invariant 3 crosses 50 spawns, the
removal becomes a single `git rm -r .claude/hooks/legacy/` commit.

## Sprint 6 Phase 6b resolution (2026-04-13)

PLAN-006 debate round 1 consensus K9 (R-VP7) amended this ADR with an
**alternative Gate B (direct test)**: if invariant 3 persistently
fails but legacy/ can be removed WITHOUT breaking any test, the
removal is safe regardless of organic spawn count.

### Gate A re-run (Sprint 6 Phase 6b)

- Invariant 2 (audit-log.errors empty): **FAIL** — 45 lines (all
  test-induced by `test_fail_open_contract.py` running 4 malformed
  payloads × 6 hooks = 24 per test run × ~2 runs)
- Invariant 3 (≥ 50 spawns in audit log): **PASS** — 65 spawns
- Invariant 4 (no stale legacy refs): PASS

Invariant 2 failing on test-induced noise is not a production signal.

### Gate B (direct test — ADR-014 amendment)

Procedure:
1. `mv .claude/hooks/legacy /tmp/legacy-removed-<ts>` (backup, reversible)
2. `python3 -m unittest discover -s .claude/hooks/tests` → 303 green
3. `python3 -m unittest discover -s .claude/scripts/tests` → 234 green

Both test suites pass with legacy/ absent. Gate B PASSES.

### Decision

**Remove `.claude/hooks/legacy/`** via Sprint 6 Phase 6b commit. The
direct-test gate is the stronger signal: if removing a directory
breaks nothing, the safety net it provided was already defunct. The
invariant 3 spawn-count gate served its purpose (proving the Python
hooks were exercised at least 50 times); Sprint 6's intensive
debate + migration pushed invariant 3 over the line naturally.

Sprint 6 Phase 6b commit: removes the directory + updates this ADR
status to SUPERSEDED.

### Gate B becomes reusable

Future conditional-removal ADRs should include a direct-test gate as
the primary removal criterion. Organic-traffic invariants (like
spawn count) are weak signals about specific-path safety; direct
tests are strong signals.

## Enforcement commit

`67ace0afa99a` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
