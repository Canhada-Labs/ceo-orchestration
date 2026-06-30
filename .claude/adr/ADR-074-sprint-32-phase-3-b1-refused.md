---
id: ADR-074
title: Sprint 32 Phase 3 B1 (audit_emit split v2) — REFUSED via technical-infeasibility
status: ACCEPTED
created: 2026-04-24
accepted_at: 2026-04-24
accepted_via: Round-20 sentinel (19102f1 promote) + Round-22 precision amendment
proposed_by: CEO (Session 59 execution)
co_signers: [VP Engineering (architecture validity), Principal Security Engineer (no-regression)]
related_plans: [PLAN-051]
related_adrs: [ADR-070]
blast_radius: L3 (closure artifact)
supersedes: none
superseded_by: none
closes_item: PLAN-051 §2 B1 (audit_emit split v2)
refused_taxonomy: (a) technical-infeasibility
enforcement_commit: 19102f1
round_22_amendment: SHA-naming precision per PLAN-058 audit C-P0-03 (invariant is `_KNOWN_ACTIONS` identity SHA, not raw file bytes)
---

# ADR-074 — Sprint 32 Phase 3 B1 REFUSED via technical-infeasibility

## Context

PLAN-051 §2 item B1 (`audit_emit.py` split v2, gated on ADR-070)
attempts the transactional refactor of the 1921-LoC monolith at
`.claude/hooks/_lib/audit_emit.py` into a `audit_emit_pkg/` package
with `core.py` + `emitters.py` + thin shim.

ADR-070 documented a 3-approach trade-off matrix. Phase 3 §2-strike
rule (PLAN-051 line 260–263) specifies that 2 consecutive failures
of the split escalate B1 to `refused via ADR` under taxonomy reason
(a) technical-infeasibility, with monolith preserved intact.

This ADR records the 2-strike escalation with root causes and
evidence.

## Attempts

### Attempt 1 — Session 56 (2026-04-22), v1 generator

`kernel-batch-phase-1c.py` (442 LoC) applied Approach 1 heuristic:
monolith AST-split into package via `_classify_top_level` +
unparse. Failed at stage 4 isolated import.

**Root cause:** `stage3_generate` copied the monolith's
```python
_HOOKS_DIR = Path(__file__).resolve().parent.parent
```
block verbatim into `audit_emit_pkg/core.py`. For the monolith at
`.claude/hooks/_lib/audit_emit.py`, `parent.parent` resolves to
`hooks/`. For the package at `.claude/hooks/_lib/audit_emit_pkg/core.py`,
`parent.parent` resolves to `_lib/` — wrong depth by one. The
follow-up `from _lib import redact` then tries to resolve
`_lib/_lib/redact.py`, which does not exist.

**Auto-revert** (Session 56 commit `42c104a`) restored the monolith
intact. Item deferred to PLAN-051 per `blockers.md §#6`.

### Attempt 2 — Session 59 (2026-04-24), v2 generator

`.claude/plans/PLAN-051/staged-code/kernel-batch-phase-1c-v2.py`
(~400 LoC) applied ADR-070 Approach 2 (relative imports). Fixes:

1. **Path-depth bug eliminated** — generator drops the `_HOOKS_DIR`
   assign + `sys.path.insert` `if` block from `core.py` entirely
   (dead code under relative imports).
2. **Import ordering bug eliminated** — all `from _lib import X`
   ImportFrom nodes rewritten to `from .. import X` (level=2
   relative). Works independent of sys.path state.
3. **Private re-export** — `__init__.py` + shim explicitly
   re-export all 24 `_CORE_NAMES` private names (Python `*` skips
   underscore-prefixed by default).
4. **Shim as PEP 562 proxy** — shim uses `__getattr__` + custom
   `types.ModuleType` subclass with `__setattr__` forwarding to
   the live `_core` module.

**Stages 1–5 all GREEN.** Preflight ✓, parse ✓, generate ✓
(core.py 344 LoC, emitters.py 577 LoC, __init__.py 17 LoC, shim
audit_emit.py ~30 LoC). Stage 4 isolated imports: 6 subtests
pass (shim forward, package submodule import, public emitter
callable, `_KNOWN_ACTIONS` count = 89, etc.). Stage 5 atomic
swap OK.

**Stage 6 FAIL: 29 tests regressed (out of 2517 baseline).**
Root causes identified in 3 clusters:

#### Cluster A — State-mutation through module bindings (14 tests)

Monolith has module-level mutable globals (`_FALLBACK_NOTIFIED`,
env-sensitive config via `_rotate_threshold()` read at load time,
etc.) mutated by functions via `global` declarations. Post-split,
state lives in `audit_emit_pkg.core`; the shim's bound names
(`audit_emit._FALLBACK_NOTIFIED`) reflect the BINDING-TIME copy
and are stale after core mutates its global.

**PEP 562 `__getattr__` proxy fixes READS**, but adding attributes
to shim's `__dict__` via the proxy-populating re-export breaks the
isolation (stale copies shadow the live `core` state).

Example failure:
```
test_audit_emit.py::TestAuditFallbackPath::test_fallback_banner_dedups_across_writes
  → expects banner to fire exactly once; shim's stale _FALLBACK_NOTIFIED
    causes core.function to double-fire OR skip entirely depending on test order
```

Tests that set `audit_emit._FALLBACK_NOTIFIED = False` expecting
state reset: 2 occurrences.

Tests that rely on `importlib.reload(audit_emit)` to reset
env-sensitive state (e.g., `test_audit_emit_rotation.py` lines
39, 82, 118, 137): 4+ occurrences. Reload of shim does not
cascade to `core`; adding cascade introduces infinite-recursion
risk when core's reload triggers shim re-evaluation.

#### Cluster B — `mock.patch("_lib.audit_emit.X")` contract (12 tests)

`unittest.mock.patch` uses `setattr` to install the mock and
`delattr` on `__exit__` to remove it. `mock.patch`'s `is_local`
flag checks whether the attribute is locally in the target's
`__dict__`. For the PEP 562 shim, `emit_generic` is reached via
`__getattr__`, NOT directly in `__dict__` → `is_local=False` →
`delattr` path fires on undo → `AttributeError: emit_generic`.

Affected: every test using `patch("_lib.audit_emit.emit_generic",
mock)` or similar idiom. Count: 12.

Fix would require pre-populating shim `__dict__` with all public
names (to make `is_local=True`), but that re-introduces Cluster A
staleness because shim `__dict__` caches initial binding.

#### Cluster C — `_FALLBACK_NOTIFIED` as module global (1 test seed, 11 reachable)

Test `test_check_arbitration_kernel` cluster (11 failures in full
suite, all PASS when run isolated) shares ordering dependency
with `audit_emit_pkg.core` first-import timing. The kernel hook
imports `audit_emit` indirectly; when the shim loads first with
one environment, then a later test reloads with altered env, the
kernel hook's cached `audit_emit` reference desyncs from the
test's expectations.

## Options considered for remediation

### Option 1 — Module-level shared-state object

Introduce `audit_emit_pkg.state` module holding all mutable
globals as mutable attributes. Rewrite every `global _X` in
`core.py` to `state._X`. Shim forwards reads to `state` too.

**Why refused:** requires modifying ALL 50 public emitters +
`_KNOWN_ACTIONS` + 24 private functions to reference
`state.X` instead of directly scoped globals. This touches the
monolith at nearly every line, effectively re-monolithizing state
into a new single-file module (`state.py`). Net effect: split on
paper, monolith in behavior. Violates PLAN-051 §Anti-goals:
"NÃO otimizar marginalmente — scope no mínimo-viável por item."

### Option 2 — Test rewrite

Update 27+ failing tests to reference `audit_emit.audit_emit_pkg.core.X`
instead of `audit_emit.X` for state globals, and
`patch("_lib.audit_emit_pkg.core.X")` instead of
`patch("_lib.audit_emit.X")`.

**Why refused:** violates the **implicit contract** preserved by
`test_audit_emit_api_contract.py` — test surface uses `audit_emit.*`
as the public namespace. Rewriting tests to use internal package
paths makes the SHIM structure leak into test code, which is
exactly what the "transparent refactor" invariant of Phase 3 was
supposed to avoid. Touching 27 tests is also ~3× original effort
estimate (budget was 1.5–2 dev-days; Option 2 is 4–6).

### Option 3 — Abandon Approach 2, try Approach 3 (PYTHONPATH)

Delegates path-fixup to `_python-hook.sh`. State-mutation issue
(Clusters A + C) is orthogonal to path resolution and would
persist regardless of approach.

**Why refused:** root cause is state semantics, not path. Approach
3 also touches kernel-canonical `_python-hook.sh` (larger blast
radius than 1/2) without addressing the actual failure cause.

## Decision

**REFUSED** per PLAN-051 §3.1 taxonomy reason
**(a) technical-infeasibility**:

- **N attempts exhausted**: 2 strikes fired per Phase 3 acceptance
  §2-strike rule (Session 56 v1 + Session 59 v2).
- **Root cause identified**: module-level mutable state coupled
  to test contract via `mock.patch` + `importlib.reload` +
  direct `_X` mutation. The monolith's design entangles state
  lifecycle with module identity; splitting into a package with
  transparent shim breaks the `mock.patch` contract and state-read
  semantics.
- **Fix would require violating an invariant §6**: Option 1
  re-monolithizes state (defeats split); Option 2 rewrites test
  contracts (breaks implicit transparency invariant); Option 3
  orthogonal to root cause.

**Monolith at `.claude/hooks/_lib/audit_emit.py` preserved intact**
(1921 LoC byte-identical; 89 actions; `_KNOWN_ACTIONS` identity SHA
`4082e9b3...` = `SHA256(sorted(_KNOWN_ACTIONS))` — the action-list
identity, NOT the raw file byte-SHA; 2517/5 tests green in baseline).
No changes shipped to canonical paths.

**Evidence retained** at:
- `.claude/plans/PLAN-051/staged-code/kernel-batch-phase-1c-v2.py`
  (Attempt 2 generator, preserved for future retry)
- `.claude/plans/PLAN-050/kernel-batch-phase-1c.py`
  (Attempt 1 generator, preserved for historical reference)

## Consequences

### Positive

- Sprint 32 closure unblocked: Phase 3 B1 closes definitively.
- Monolith works as shipped in v1.9.0 / v1.9.1 GA; production
  impact: zero.
- `test_audit_emit_api_contract.py` 5/5 green in current state
  (`_KNOWN_ACTIONS` identity SHA `4082e9b3...` preserved) — contract
  invariant preserved.
- Both generator artefacts preserved as evidence for future
  retry attempts (if adopter demand justifies re-exploration
  with dedicated state-module redesign).

### Negative / Accepted

- **Sunset declaration in PLAN-051 §6.1 NOT taken**: the
  "single-file audit_emit.py invariant" remains in force.
- **Maintenance cost**: monolith stays 1921 LoC. Emitter edits
  still happen in a single large file. Cost accepted — Sprint
  32 is closure.
- **Future retry path unblocked**: if a future adopter requests
  split (or a new Python feature like PEP 688 module-level
  descriptors lands), re-opening B1 with a dedicated state-module
  redesign (Option 1 formalized) is available. ADR-074 will be
  superseded by that work's ADR.

## Invariant posture post-refusal

**Preserved (§6 invariants):**
- Monolith integrity (`_KNOWN_ACTIONS` identity SHA `4082e9b3...`; action-list identity, not raw file bytes)
- `_KNOWN_ACTIONS` count = 89
- 50 public emitter surface (`test_audit_emit_api_contract.py`
  _EXPECTED_PUBLIC_SYMBOLS 48 + 2 private)
- PEP 562 shim + state-module redesign deferred; no new invariant
  introduced by this refusal

**Declared sunsets CANCELLED:**
- PLAN-051 §6.1 "single-file audit_emit.py invariant → replaced
  by audit_emit_pkg/ package" — **remains in force**.
- PLAN-051 §6.1 "monolith SHA as audit-emit public-API identity
  → replaced by package contract test" — **remains in force**.

**v2.0.0 SemVer bump criterion (ADR-073):** no breaking API
changes; Sprint 32 closes at `v1.10.0` (minor, per ADR-073
§Decision drivers) OR `v1.9.2` (patch) depending on accumulated
non-breaking changes. See Phase 8 closeout ADR for final tag
decision.

## Dual co-sign (§3.1 — refused-ADR hard requirement)

- **VP Engineering** (architecture validity): ✅ Refusal preserves
  monolith + zero production impact. Two attempts exhausted under
  Phase 3 §2-strike rule. Neither remediation Option (1, 2, 3) fits
  closure scope without violating an invariant. Co-sign granted.
- **Principal Security Engineer** (no-regression): ✅ Monolith
  byte-identical to v1.9.1 baseline. No new failure modes
  introduced. `test_redact_before_emit_behavioral.py` (ADR-070
  acceptance, Phase 3 §236) deferred — applies when split ships;
  under refusal, redaction invariant remains tested by existing
  2517/5 hook suite. Supply-chain integrity unchanged. Co-sign
  granted.

## Refused-ADR ceiling check (§3.1 cap)

PLAN-051 §3.1 caps refused items at ≤3/11. Post-ADR-074:

| Item | Status | Evidence |
|------|--------|----------|
| A1 warnings | done | Round-19 (commit `84a4977`) |
| A2 VERSION | done | `b8aca55` + `5f8993b` |
| A3 v1.9.0 GA | done | `c01feec` (tag `v1.9.0`) + `5f8993b` (retag `v1.9.1`) |
| **B1 audit_emit split v2** | **refused (ADR-074)** | this ADR |
| B2 ADR-049a ACCEPTED | done | `563b239` |
| B3 mutation budget | done | `5f47cbd` + `d93eb87` |
| B4 harness mapping | done | `23954d7` |
| B5 benchmarks | TBD | Phase 5 decision (may refuse per §3.1 (a)) |
| B6 kill-switch final | done | `8f28bc2` |
| C1 wondelai SKIP | done | ADR-069 canonical via round-19 |
| C2 conftest retirement | TBD | 2026-04-29 soak gate |

**Refused count: 1/11** (well under cap of 3). If B5 also refuses,
count → 2/11 (still under cap). C2 outcome depends on 2026-04-29
soak result.

## References

- PLAN-051 §2 item B1 (audit_emit split v2)
- PLAN-051 §3.1 Refused-ADR taxonomy
- PLAN-051 Phase 3 §2-strike rule (lines 260–263)
- PLAN-051 §6 Invariants preservados / §6.1 Invariant deltas
- ADR-070 (trade-off matrix, 3 approaches)
- ADR-073 (SemVer bump criteria; v2.0.0 criterion now unmet)
- `.claude/plans/PLAN-051/staged-code/kernel-batch-phase-1c-v2.py`
  (Attempt 2 generator — evidence)
- `.claude/plans/PLAN-050/kernel-batch-phase-1c.py`
  (Attempt 1 generator — evidence)
- `.claude/hooks/tests/test_audit_emit_api_contract.py`
  (5/5 green, `_KNOWN_ACTIONS` identity SHA `4082e9b3...` preserved)
- `memory/project_plan_050_session_56.md` (Attempt 1 failure)
- `memory/project_plan_051_session_59_phase_3_b1_refused.md`
  (Attempt 2 failure — this session's execution log)

## Enforcement commit

**Enforcement commit:** to be populated by the commit that lands
this ADR + updates PLAN-051 `ledger.md` row B1 = refused.
