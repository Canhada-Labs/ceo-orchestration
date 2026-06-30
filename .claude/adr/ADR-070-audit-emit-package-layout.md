---
id: ADR-070
title: audit_emit package layout — split mechanism for 1921-LoC monolith
status: RETRACTED
created: 2026-04-22
proposed_by: CEO + VP Engineering + Principal Performance (PLAN-051 Phase 2.5)
related_plans: [PLAN-051, PLAN-050]
related_adrs: [ADR-031, ADR-049a]
blast_radius: L3-wide (canonical-guarded path)
supersedes: none
superseded_by: none
gates_phase: PLAN-051 Phase 3
staged_for: .claude/adr/ADR-070-audit-emit-package-layout.md
staged_reason: Round-18 sentinel + per-Phase ACCEPT decision required.
retracted_at: 2026-05-20
retracting_session: S147
retracted_reason: see ADR-070-RETRACT-RATIONALE.md
---

# ADR-070 — audit_emit package layout

## Context

`.claude/hooks/_lib/audit_emit.py` is a 1921-LoC monolith carrying 89
canonical audit-action emitters + HMAC chain + redact-on-emit + payload
serialization + rotation logic. PLAN-050 Phase 1c attempted a
kernel-batch transactional split (monolith → `audit_emit_pkg/core.py +
emitters.py + shim`) and **failed at stage 4 isolated import test**:
`stage3_generate` copied the monolith's `_HOOKS_DIR =
Path(__file__).resolve().parent.parent` block verbatim into the
generated subpackage; in `audit_emit_pkg/core.py` that `parent.parent`
resolves to `_lib/` (not `hooks/`), breaking `from _lib import redact`
into the nonexistent `_lib/_lib/redact.py`. Auto-revert restored the
monolith intact (Session 56 commit `42c104a` preserved the 1921-LoC
file). Item DEFERRED-DESIGN to Sprint 32 / PLAN-051 Phase 3.

This ADR documents the trade-off matrix for the 3 candidate redesign
approaches and the decision drivers. Final approach selection happens
in PLAN-051 Phase 3 (post-ADR-070 ACCEPT) by VP Engineering + Principal
Performance Engineer per ADR authors.

## Options considered

### Approach 1 — Path-depth rewrite (in stage3_generate)

`stage3_generate` adds one extra `.parent` to the `_HOOKS_DIR` block
when relocating the path-resolution code from monolith to subpackage.
The generated `audit_emit_pkg/core.py` becomes:

```python
_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent  # → .claude/hooks/
sys.path.insert(0, str(_HOOKS_DIR))
from _lib import redact as _redact
```

**Trade-off matrix:**

| Axis | Score |
|------|-------|
| Latency | Best — no import-graph change; cold = monolith equivalent |
| Memory | Best — no extra `__init__` evaluation |
| Complexity | Lowest — surgical patch on stage3_generate (~5 LoC change) |
| Reversibility | High — single-commit revert restores monolith; auto-revert wrapper preserved |
| Maintenance | Medium — depth-aware code is fragile if package depth changes again |
| Blast radius | Smallest — only `audit_emit*` files touched |

### Approach 2 — Relative imports

`audit_emit_pkg/core.py` uses Python relative imports + a deliberate
shim that sets sys.path at package load:

```python
# audit_emit_pkg/__init__.py — minimal, sets path once
import sys
from pathlib import Path
_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent  # → hooks/
sys.path.insert(0, str(_HOOKS_DIR))

# audit_emit_pkg/core.py — uses relative imports for sibling modules
from .emitters import emit_action_v2  # within the package
from _lib import redact as _redact  # cross-package (via __init__ shim)
```

**Trade-off matrix:**

| Axis | Score |
|------|-------|
| Latency | Medium — `__init__.py` evaluation adds ~0.5-1ms cold; warm cached |
| Memory | Medium — package object overhead ~few KB |
| Complexity | Medium — explicit shim + relative imports + consumer migration |
| Reversibility | High — git revert restores monolith |
| Maintenance | Higher — more idiomatic Python; package layout extensible |
| Blast radius | Medium — package boundary change visible to hook consumers |

### Approach 3 — PYTHONPATH reliance (breaking change)

Abandon the self-contained `_HOOKS_DIR` path-fixup pattern entirely.
The hook runner (`_python-hook.sh` shim) sets `PYTHONPATH` at process
launch. `audit_emit_pkg/core.py` does plain `from _lib import redact`
without any path manipulation.

**Trade-off matrix:**

| Axis | Score |
|------|-------|
| Latency | Best for hook boot — PYTHONPATH amortized across runner; no per-import path compute |
| Memory | Best — no in-Python sys.path mutation per module |
| Complexity | Highest — requires `_python-hook.sh` change + ADR + feature flag for adopter migration |
| Reversibility | Medium — feature-flagged but breaks adopter installations that bypass `_python-hook.sh` |
| Maintenance | Best long-term — clean separation of concerns; no recursive path-fixup |
| Blast radius | Largest — touches `_python-hook.sh` (kernel-canonical); affects every adopter installation |

## Decision

**Decision deferred to PLAN-051 Phase 3 execution.** This ADR PROPOSES
the trade-off matrix; the winning approach is selected by VP Eng +
Principal Perf at Phase 3 kickoff using the matrix above.

**Tie-breaker rule:** lowest LoC delta + zero breaking consumers wins
by default; Approach 3 only if Approaches 1 and 2 both fail their
acceptance gates (perf gate, behavioral redaction test, regression
budget).

## Decision drivers

1. **Hook-consumer contract stability.** Every hook in `.claude/hooks/`
   imports from `_lib/audit_emit.py`. Changing the import path requires
   consumer migration. Approach 1 has zero consumer impact; Approach 2
   has shim-mediated zero impact; Approach 3 has explicit migration.

2. **Canonical-edit discipline (ADR-031).** All approaches edit
   `_lib/audit_emit.py` AND create new subpackage files. Both touch
   canonical scope. Round-18 sentinel must cover both monolith
   modification + subpackage creation.

3. **Auto-revert behavior.** Session 56's auto-revert protected the
   monolith when Approach-1-precursor failed. Phase 3 implementation
   MUST exercise auto-revert proactively (kill a test import, confirm
   revert fires) per Security adjustment + QA staging-rehearsal.

4. **Performance gates** (Performance Risk #1 in PLAN-051 consensus):
   - p95 warm `import audit_emit` delta ≤ +1.5ms vs Phase 0.5 baseline
     (0.304ms warm p95 → ≤ 1.804ms post-split)
   - p95 cold delta ≤ +5ms
   - Hook boot-to-emit p95 delta ≤ +3ms

   Approach 3 best meets these; Approach 1 nearly identical to monolith;
   Approach 2 worst due to `__init__` eval.

5. **Behavioral redaction invariant** (Security P0 in PLAN-051
   consensus): all 3 approaches MUST preserve `from _lib import redact`
   behavior. The Session 56 root-cause was a SILENT REDACTION FAILURE
   waiting to happen; the behavioral test (`test_redact_before_emit_
   behavioral.py`, 19 secret families × 3 payload shapes) is a Phase 3
   acceptance gate independent of approach.

## Consequences

### Positive (per Approach selection)

- Approach 1: minimal risk; ships monolith→package with smallest blast
  radius; preserves all current behavior.
- Approach 2: more idiomatic; allows future package extensibility.
- Approach 3: cleanest long-term; eliminates self-contained path-fixup
  hack pattern.

### Negative / Accepted trade-offs

- **All approaches:** add one new package boundary; new failure modes
  (partial import / cache shadow / wrong `redact` binding) require new
  test discipline (covered by Phase 3 Acceptance).
- **All approaches:** invalidate the "single-file audit_emit.py
  invariant" sunset declared in PLAN-051 §6.1 if approach succeeds.
- **Approach 3 only:** breaking change requires v2.0.0 SemVer bump (ties
  to ADR-073 SemVer criteria).

### Refused-via-ADR fallback

Per PLAN-051 Phase 3 §2-strike rule: if 2 successive approaches fail
(per acceptance criteria), B1 closes `refused via ADR` taxonomy reason
(a) technical-infeasibility. Monolith stays intact; contract test
preserved for future retry.

## Blast radius

**L3-wide.** Touches:
- `.claude/hooks/_lib/audit_emit.py` (canonical guard)
- `.claude/hooks/_lib/audit_emit_pkg/` (new directory if approach 1/2)
- `.claude/hooks/_python-hook.sh` (canonical guard, only if approach 3)
- `.claude/plans/PLAN-050/kernel-batch-phase-1c.py` (refactor)
- `.claude/hooks/tests/test_audit_emit_api_contract.py` (existing pin)
- New: `.claude/hooks/tests/test_redact_before_emit_behavioral.py`
- New: `.claude/hooks/tests/test_audit_emit_module_import_equivalence.py`
- All hooks importing `from _lib.audit_emit import ...` (approach 3 only)

## Dual co-sign (PLAN-051 §3.1 — ADRs that gate execution)

- **VP Engineering:** ✅ co-author (architecture decision)
- **Principal Performance Engineer:** ✅ co-author (perf gate definitions)
- **Principal Security Engineer:** ✅ reviewed (behavioral redaction
  invariant + supply-chain integrity); VETO-conditional on Phase 3
  Acceptance behavioral test

## Lifecycle

- **PROPOSED-STAGED** (this commit) — Phase 2.5 draft
- **PROPOSED canonical** — round-18 promote (`git mv` adr-drafts → adr/)
- **ACCEPTED** — Phase 3 execution kickoff selects approach; ADR
  amended with `chosen_approach: 1|2|3` + accepted_by line
- **SUPERSEDED** if Phase 3 reveals approach-not-listed via deeper
  investigation (would require Round 2 debate)

## References

- PLAN-050 Session 56 root-cause memory `project_plan_050_session_56.md`
- PLAN-050 `blockers.md §#6` (DEFERRED-DESIGN remediation contract)
- PLAN-050 `kernel-batch-phase-1c.py` (existing transactional scaffold)
- PLAN-050 `test_audit_emit_api_contract.py` (5/5 byte-identity SHA `4082e9b33778e2c9d6c6ce5170c54eee2d8a4a3ebdb34cb3f7762d6c6c54b53a`)
- ADR-031 canonical-edit sentinel chain
- PLAN-051 §Phase 3 Acceptance (8 mandatory bullets)
- PLAN-051 baselines/perf-snapshot.json (Phase 0.5 numeric floor)

## Enforcement commit

**Enforcement commit:** to be populated post-Phase-3-execute with the
commit SHA that promotes `audit_emit_pkg/` canonical (or with the
`refused via ADR` ADR if 2-strike rule fires). Pre-Phase-3,
enforcement is advisory — this ADR is the trade-off matrix.
