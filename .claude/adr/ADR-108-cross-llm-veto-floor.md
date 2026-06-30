---
id: ADR-108
title: Cross-LLM VETO Floor — Extends ADR-052
status: ACCEPTED
proposed: 2026-05-04
accepted: 2026-05-10
gate: PLAN-075 Phase 0A U7 rubric pass at >= Opus baseline (gap <=5pp) + U9b FP rate <=15% blocking
gate_met_at: 2026-05-09
enforcement_commit: <set at Phase 3 ceremony commit time>
related_plan: [PLAN-075, PLAN-081]
related_adr: [ADR-052, ADR-105, ADR-107, ADR-111]
---

# ADR-108 — Cross-LLM VETO Floor

## Status: ACCEPTED (PLAN-081 Phase 3 ceremony, 2026-05-10)

ACCEPTED gate (per PLAN-081 §3 Phase 3 exit criteria + §4 ADR transitions):
- Phase 0A U7 SPIKE-VERDICT MET (gap=0pp on N=20 v3 synthetic corpus,
  PLAN-075 SPIKE-VERDICT.md)
- Phase 0A U9b SPIKE-VERDICT MET (FP=0% on framework-specific governance
  patterns, PLAN-075 SPIKE-VERDICT.md)
- Phase 3 asymmetric matrix landed in `check_pair_rail.py:_decide_with_matrix()`
- §Operational labeling protocol per R1 S-TDE-3 (`audit-query.py fp-rate`
  aggregator deferred to Phase 6; Phase 3 records label-able events via
  `pair_rail_case`)
- Severity P0/P1 mechanism per R1 S-TDE-4 (24h human-triage grace via
  `CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS=24`; T+24h unlabeled P1 closes-as-
  advisory; P0 binds immediately)

## Context

ADR-052 §Model-ID-bump-process line 138-149 mandates: canonical-5 rubric pass
+ replay benchmark + ADR with evidence + audit schema bump for ANY model
participating in VETO floor. SWE-bench external benchmark insufficient.

PLAN-075 v5 ADR-107 codifies asymmetric VETO matrix Cases A-F. Case B
("PASS + BLOCK → ship blocked") materially extends VETO floor to Codex IF
preconditions met. ADR-052 §Model-ID-bump-process therefore activates.

## Decision (ACCEPTED)

Codex peer participates in the VETO floor at L3+ for CR + Sec archetypes
under the asymmetric matrix per ADR-107 §Cases A-F:

- **Case A (both PASS)**: dispatch proceeds; cross-LLM agreement records
  in audit-log via `pair_rail_case`.
- **Case B (Claude PASS + Codex BLOCK)**: ship blocked IFF preconditions
  met — `{file:line cited + rubric_violation_id ∈
  rubric-violation-catalogue.yaml + severity ∈ (P0, P1)}`. Without
  preconditions: Case B' fail-OPEN advisory per ADR-106. Owner cannot
  dismiss a met-precondition Case B without ADR rebut.
- **Case C (Claude BLOCK + Codex PASS)**: Claude Opus VETO authority
  preserved per ADR-052. Codex PASS does NOT unblock.
- **Case D (both BLOCK)**: hard-block; escalate.
- **Case E (divergent, Jaccard ≤ 0.3)**: flag for human review; allow
  with systemMessage warning.
- **Case F (timeout / outage)**: fail-OPEN per ADR-106 hook semantics.

## Operational labeling protocol (R1 S-TDE-3 + S-TDE-4)

### Severity P0/P1 mechanism

`rubric-violation-catalogue.yaml` declares each rubric ID's
`severity_default ∈ {P0, P1}`. Catalogue authoring discipline:
- P0 = mechanically-blocking (Case-B with P0 → block immediately)
- P1 = human-triage-required (Case-B with P1 → 24h grace via
  `CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS=24` env)

Owner labeling protocol via `audit-query.py label` (Phase 6 deliverable):
- Case-B P1 events not labeled within 24h window → close-as-advisory
  (NOT block). Asymmetric: P0 mechanically binds; P1 requires explicit
  Owner upgrade-to-block within grace window.
- Owner labels: `fp` (false-positive — Codex was wrong; close as advisory),
  `tp` (true-positive — block stands), `triage_pending` (extends grace by
  24h; max 1 extension before mechanical close-as-advisory).

### FP-rate aggregator (Phase 6 deliverable)

`audit-query.py fp-rate --window-days 30` reads `audit-log-labels.jsonl`
HMAC-chained label store + computes:
- `fp_rate_lower_bound`: 95% Wilson lower bound
- `fp_rate_upper_bound`: 95% Wilson upper bound
- `case_b_total`, `case_b_labeled_fp`, `case_b_unlabeled` counts

If `fp_rate_30d > 30%` per `disable_predicate_eval.py` evaluation, the
`fp_rate_30d_above_30pct` predicate fires for affected archetypes,
disabling the pair-rail for those archetypes (matrix `disable_predicates`
fires). This is the **post-hoc reopen criterion** for ADR-108 → reopen
ceremony triggers, pair-rail demoted to advisory-only, new plan drafted.

### Sec dissent (R1 C6) — recorded

R1 Security Engineer dissented on N-of-M relaxation (Pass-1 strict 15/15
+ Pass-2 retry 1 fixture for transient infra). 4-of-5 archetypes
(CR/QA/Perf/TDE) endorsed the 2-pass-with-triage compromise. Resolution
adopted: forensic artifact emitted on manual triage path (NOT silent
override). Sec dissent preserved in this ADR + PLAN-081 §13 + Phase 4
ADR-111 §Operational.

## References

- ADR-052 (VETO floor invariant)
- ADR-105 (multi-supersede 084+085+096)
- ADR-106 (Codex MCP adapter PostToolUse advisory)
- ADR-107 (asymmetric VETO matrix Cases A-F)
- ADR-111 (locked corpus governance — Phase 4)
- PLAN-075 spec.md v5 §6 U7 + U9b + §11 asymmetric matrix
- PLAN-081 §3 Phase 3 + §4 ADR transitions
- `.claude/policies/rubric-violation-catalogue.yaml` (19 enumerated IDs)
- `.claude/plans/PLAN-020/rubrics/code-reviewer.yaml`
- `.claude/plans/PLAN-020/rubrics/security-engineer.yaml`

---

## Amended-by

- **ADR-127** `Pair-Rail Case B procedural-block advisory promotion +
  Phase 4 substantive-block pre-emptive advisory doctrine` (ACCEPTED
  2026-05-13) — amends §Decision Case B (Claude PASS + Codex BLOCK)
  "ship blocked IFF preconditions met" clause to advisory-emit-only
  for both `precondition_met=False` (procedural) and future Phase 4
  `precondition_met=True` (substantive) paths. §Operational labeling
  protocol (`fp`/`tp`/`triage_pending` via `audit-query.py label`) +
  §FP-rate aggregator (`fp_rate_30d_above_30pct` predicate) preserved
  unchanged — both continue as data-collection scaffold for PLAN-100
  confidence-gate FPR-class block-mode evidence baseline. ADR-052
  archetype-level VETO authority unaffected. See
  `.claude/adr/ADR-127-pair-rail-advisory-promotion.md`.
