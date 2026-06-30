# Wave A.7 — AC7-AC11 production callsite wires DEFERRED to PLAN-093

## Disposition: PARTIAL — substantive wires deferred to Tier-5/post-hotfix

PLAN-091 §4 A.7 originally scoped:

1. SessionStart Tier-S list extension to 18 checks (AC11a)
2. first-run-wizard auto-spawn callsite (AC11b)
3. 4 SEMI-13 graceful-degradation emit wires (AC11d expansion)
4. AC10 4-persona coverage runtime check wired into ceo-boot

R1 code-reviewer P0 fold acknowledged: "`first-run-wizard.py`
production callsite undefined; A.7 needs file:line target before
wave kickoff" — DEFERRED to execution-time.

## What PLAN-091 actually SHIPS (vs originally scoped)

| Item | Scope | Disposition |
|---|---|---|
| Tier-S 16th check | A.1 tier_policy_misrouting_24h | **SHIPPED (commit e8e23a5)** |
| Tier-S 17th + 18th | A.7 part 1 | **DEFERRED-PLAN-093** (no underlying implementations to register) |
| first-run-wizard callsite | A.7 part 2 | **DEFERRED-PLAN-093** (callsite target undefined) |
| 4 SEMI-13 emit wires | A.7 part 3 | **DEFERRED-PLAN-093** (AC11d expansion belongs to a separate plan) |
| AC10 persona coverage runtime | A.7 part 4 | **DEFERRED-PLAN-093** (ceo-boot extension is its own ceremony) |
| mcp_routing callsite | A.4 | **SHIPPED (commit 5d23729)** |
| specialization_promoted callsite | A.5 | **SHIPPED (commit 5d23729)** |
| /effort thinking callsite | A.3 | **SHIPPED (commit fed57ae)** |
| Tier-policy Tier-S check | A.1 | **SHIPPED (commit e8e23a5)** |

## Empirical gap evidence

Production-callsite audit on the 7 PLAN-088 canonical-13 emit events
that lack a non-self caller (run on `worktree-plan-091-bg` at
commit `95b437e`):

| Action | Non-self callsites | Disposition |
|---|---|---|
| `first_run_wizard_dispatched` | 0 | DEFERRED-PLAN-093 |
| `pair_rail_phase_advanced` | 0 | DEFERRED-PLAN-093 (Phase C flip = PLAN-090) |
| `cookbook_pattern_advised` | 0 | DEFERRED-PLAN-092 (cookbook real-wire) |
| `cache_discipline_alerted` | 0 | DEFERRED-PLAN-093 |
| `batch_dispatched` | 0 | DEFERRED-PLAN-090 (BatchClaudeLiveAdapter) |
| `tier_policy_misrouting_advised` | 0 | DEFERRED-PLAN-093 (the Tier-S check emits via Tier-S registry, not this action) |
| `estimate_calibrator_pipeline_run` | 1 | PLAN-088 W6 already wired |

These 6 gap rows would each require a non-trivial callsite design
(first-run-wizard restructure, Phase-C transition logic, cookbook
recommendation engine, cache-discipline detection rule, batch
adapter, etc.). Per ADR-115 §maintenance-mode anti-churn discipline
and PLAN-091 §3 hotfix invariant ("NO new features"), these
substantive wires belong in PLAN-092 (cookbook real-wire) +
PLAN-093 (Tier-5 broader infrastructure) + PLAN-090 (Phase C +
batch).

## Cross-plan handoff

- **PLAN-090 §4**: owns `batch_dispatched` callsite + Phase C
  ENFORCING flip (which fires `pair_rail_phase_advanced`).
  PLAN-090 Wave A `external_wait: PLAN-091-callsite-wires-shipped`
  is satisfied by the wires PLAN-091 DID land (A.1 + A.3 + A.4 +
  A.5 + A.6 docstring promotion). The remaining canonical-13
  callsites are NOT a precondition for PLAN-090 Wave A.
- **PLAN-092 §4**: owns `cookbook_pattern_advised` real-wire (per
  S114-post Codex R2 P0-1 cross-plan allocation finding —
  cookbook SEMI-11 redirected from PLAN-088 W3.2 to PLAN-092).
- **PLAN-093 §4** (Tier-5 finalization): owns the remaining 4
  callsites (`first_run_wizard_dispatched` + `cache_discipline_
  alerted` + `tier_policy_misrouting_advised` direct emit +
  Tier-S 17th/18th checks).

## Mechanical AC posture (post-PLAN-091)

| AC ref | Mandate | Disposition |
|---|---|---|
| §5 AC3 | PLAN-088 AC7-AC11 production wires re-verified | A.7 PARTIAL — only A.4+A.5+A.3 wires landed; remaining 6 deferred |
| §5 AC11 | NO new ADRs proposed | SATISFIED |

## Anti-churn defense

PLAN-091 ships **6 net-new production callsites** in v1.22.1
(A.1 Tier-S check + A.3 /effort auto-inject + A.4 mcp_routing
spawn-hook + A.5 specialization_promoted spawn-hook + A.6
docstring/constant + Tier-S registry assert bump). That is the
maximum scope a HOTFIX tag can absorb without crossing into
minor-bump territory (v1.23.0 = PLAN-089; v1.24.0 = PLAN-090).

The 6 deferred wires are NOT regressions — they were never live
in v1.22.0. They are FUTURE wires that PLAN-092 + PLAN-093 will
land alongside the substantive infrastructure each requires
(cookbook recommendation engine, first-run-wizard restructure,
cache discipline detection, etc.).

## How PLAN-093 picks up

PLAN-093 §1 should cite this file + `.claude/plans/PLAN-091/
wave-a-pair-rail-defer.md` as its starting state. The combined
deferred surface (A.6 SHADOW-strip + A.7 6 callsites + R-035
branch coverage + R-036 property-based tests) forms the PLAN-093
Tier-5 finalization scope.
