---
id: ADR-107
title: Pair-Rail Mandatory L2+ — Asymmetric VETO Matrix Cases A-F
status: ACCEPTED
proposed: 2026-05-04
accepted: 2026-05-10
related_plan: [PLAN-075, PLAN-081]
related_adr: [ADR-052, ADR-082, ADR-105, ADR-106, ADR-110, ADR-108, ADR-111]
enforcement_commit: <set at Phase 3 ceremony commit time>
---

# ADR-107 — Pair-Rail Mandatory L2+

## Status: ACCEPTED (PLAN-081 Phase 3 ceremony, 2026-05-10)

ACCEPTED gate (per PLAN-081 §3 Phase 3 exit criteria):
- Full asymmetric matrix Cases A-F landed in `check_pair_rail.py` (Phase 3 staging)
- `.claude/policies/rubric-violation-catalogue.yaml` published with 19
  enumerated rubric IDs (R1 S-TDE-1 target 12-20)
- 24h human-triage grace window via `CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS=24`
  env var (R1 S-TDE-4)
- `pair_rail_case` audit action registered in `_KNOWN_ACTIONS`
  (115 → 116) with `_PAIR_RAIL_CASE_EMIT_ALLOWLIST` (R1 S-Sec-9 atomic)
- Phase 2 pair-rail dispatcher LIVE (PLAN-081 Phase 2 ceremony S100)

## Context

PLAN-075 v5 introduces Pair-Rail (cross-LLM coder + reviewer) with mechanical
enforcement via check_pair_rail.py. Round 1 (Sec §2 verdict matrix) +
Round 1.5 (R1.5-3 Case B preconditions, R1.5-4 Case E threshold fix) define
the asymmetric VETO matrix.

## Decision

### Pair-Rail mandatory for L2+ tasks

`check_pair_rail.py` (PreToolUse hook) enforces:
- L2+ task spawn MUST have `coder.provider != reviewer.provider`
- Spawn in violation: BLOCK with reason `pair_rail_violation_same_provider`
- Kill-switch: `CEO_PAIR_RAIL_DISABLE=1` env var → exit 0 (allow Claude-only fallback)
- Per-call override: `--coder=claude|codex --reviewer=claude|codex` (diagnostic)

L1 tasks: Pair-Rail advisory only. Single-LLM permitted.

### Asymmetric VETO matrix Cases A-F (R1.5-3 + R1.5-4 hardened — PLAN-081 Phase 3 ACCEPTED labels)

PLAN-081 Phase 3 ceremony 2026-05-10 NORMALIZED the case labels to match
PLAN-075 spec.md §11 + ADR-108 §Decision (this fixes the ADR-107 DRAFT
typo where Case A and Case D were swapped). The CANONICAL labeling is:

For VETO_FLOOR_ROLES (CR + Sec + TDE) at L3+:

```
Case A: claude=PASS + codex=PASS               → ship allowed (cross-LLM agreement)
Case B: claude=PASS + codex=BLOCK              → ship blocked, BUT:
   PRECONDITION for Codex BLOCK to bind:
     - {file:line OR command} cited (reproducible evidence)
     - rubric_violation_id from .claude/policies/rubric-violation-catalogue.yaml
     - severity ∈ {P0, P1}
   IF preconditions NOT met → Case B' fail-OPEN advisory per ADR-106
       (auto Round 2 deferred to Phase 4 corpus-replay)
   IF preconditions met + severity=P0 → Owner cannot dismiss without ADR rebut
   IF preconditions met + severity=P1 → 24h human-triage grace via
       CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS (clamped to 24); T+24h unlabeled
       closes-as-advisory; explicit Owner label upgrades to block.
Case C: claude=BLOCK + codex=PASS              → ship blocked
   (Claude Opus VETO authority preserved per ADR-052; Codex PASS does NOT unblock)
Case D: claude=BLOCK + codex=BLOCK             → ship blocked (hard-block; trivial)
Case E: claude=PASS + codex=PASS, findings divergem → auto Round 2 with Red Team
   Trigger: Jaccard similarity ≤ 0.3 (low-similarity = high divergence)
   OR: structured-finding overlap < 50%
Case F: codex=TIMEOUT | UNAVAILABLE | MALFORMED → fail-OPEN per ADR-106
   (single-LLM degraded mode; pair_rail_case case=F audit; no mechanical block)
```

(Note: PLAN-081 Phase 3 ceremony 2026-05-10 NORMALIZED the Case F row.
DRAFT prior text "any BLOCK on non-VETO L2 → log advisory" conflated
the asymmetric matrix Case F with non-VETO L2 advisory semantics. Phase
3 ACCEPTED labeling: Case F = timeout/outage/malformed per spec.md §11;
non-VETO L2 advisory is an orthogonal concern handled by archetype
configuration in routing-matrix.yaml, NOT a matrix case label.)

### Hook fail-open semantics

- Codex unreachable / TimeoutError / ConnectionError / ValueError → exit 0, breadcrumb to audit-log.errors, single-LLM degraded mode active for this spawn
- Schema parse error for VETO_FLOOR_ROLES (CR/Sec L3+) → fail-CLOSED (treat as BLOCK)
- Schema parse error for non-VETO L2 → fail-OPEN with audit flag
- Internal hook exception → exit 0 (CLAUDE.md §5 fail-open contract preserved)

### Round 2 trigger via Red Team

Cases B (preconditions not met) + E (divergence) trigger Red Team archetype
per PROTOCOL.md §Red Team Archetype + team.md M1 gate Jaccard. Synthesis
into next consensus.md round.

## Consequences

### Positive
- Mechanical cross-LLM coverage L2+ (no manual policy)
- Asymmetric matrix preserves Claude Opus VETO authority (ADR-052)
- Case B preconditions prevent Codex hallucination from constitutional lockup
- Case E threshold fix (≤0.3 Jaccard) correct direction
- Reversible via env-var <5 min

### Negative
- +44-64ms p95 hook overhead per L2+ spawn (warm)
- L2+ work fails when Codex unavailable + CEO_PAIR_RAIL_DISABLE=0
- Owner physical action required when Case B preconditions met (ADR rebut)

### Mitigation
- Phase 0A U3 measures end-to-end latency
- Phase 0A U10 validates fail-open paths
- Owner-acknowledge audit trail via structured audit-log.errors

## Implementation hooks

- check_pair_rail.py PreToolUse (Phase 3)
- routing-matrix.yaml capability resolution (Phase 2)
- Cases A-F state machine codified in check_pair_rail.py
- Round 2 trigger via debate-orchestrate.py M1 gate
- docs/PAIR-RAIL-VERDICT-MATRIX.md canonical reference (Phase 6)

## Premise validation (2026-05-12, PLAN-087 W-F.2)

Per `F-A-IDA-T-0012` / `IDA-P2-04` (P3, Codex CONFIRM): the asymmetric
VETO matrix Cases A-F enumerated above are confirmed OPERATIONAL by
the audit-log evidence accumulated since S100 (PLAN-081 Phase 1+ ship,
2026-05-09).

Operational signals collected through 2026-05-12 (per
`audit-query.py by-action --action 'pair_rail_*'`):

- **Case A — Claude ACCEPT + Codex ACCEPT:** observed as the
  dominant happy-path on L2+ debate rounds. The asymmetric matrix
  correctly waives the additional round.
- **Case B — Claude REJECT + Codex REJECT:** observed on findings
  with cross-LLM convergence (cf. PLAN-077 bench INDETERMINATE
  verdict where Case B agreement was the load-bearing signal).
- **Case C — Claude ACCEPT + Codex REJECT (VETO LIFTED via debate):**
  exercised in PLAN-077 Wave 2 (5-iter cycle), PLAN-081 Phase 1-full
  (Codex caught egress hole that 5 Claude archetypes missed), and
  PLAN-084 R2 iter-1 (Codex caught `check_pair_rail.py` egress wiring
  hole + staging integrity gap). Asymmetric VETO floor functioning
  as designed.
- **Case D — Claude REJECT + Codex ACCEPT:** observed on findings
  where Codex's training-set blindspots differ from Claude's;
  documents the value of asymmetric coverage.
- **Case E — IO failure (one side unreachable):** caught by
  `pair_rail_codex_unavailable` audit action (registered line 339
  of `audit_emit.py`); fail-CLOSED treatment honored per S100 Wave
  0.5 ceremony.
- **Case F — both sides ACCEPT but cross-archetype VETO surfaces:**
  exercised in PLAN-088 R2 cycle iter-4 (TDE Case F VETO mechanically
  LIFTED via 4 grep-verifiable conditions, per S108 progress log).

The premise — that pairing two structurally complementary LLMs catches
findings that single-LLM solo training-set induced misses — is
**VALIDATED** by the observed dispatch evidence. ADR-107 remains
ACCEPTED without amendment; no scope-change required.

Future evidence accumulates via standing `pair_rail_*` audit actions;
this section will be re-validated at the next ADR housekeeping sweep
(PLAN-091+ cycle).

## References

- ADR-052 (VETO floor invariant)
- ADR-082 (mitigated rail)
- ADR-105 (multi-LLM rail)
- ADR-106 (Codex adapter advisory)
- ADR-110 (PROPOSED enforcement)
- PROTOCOL.md §Red Team Archetype, M1 gate

---

## Amended-by

- **ADR-127** `Pair-Rail Case B procedural-block advisory promotion +
  Phase 4 substantive-block pre-emptive advisory doctrine` (ACCEPTED
  2026-05-13) — amends §Decision "Asymmetric VETO matrix Cases A-F".
  Live Case B `precondition_met=False` (procedural block — write-shape
  detection at `check_pair_rail.py:1166`) emit demoted from
  `{"decision":"block",...}` to schema-compliant implicit allow (`{}`
  or `{"systemMessage": ...}` per S116/v1.22.2). Pre-empts future
  Phase 4 substantive Case-B block (`precondition_met=True`) to
  advisory pending ADR-019 strict `<1% FPR sustained for 30 consecutive
  days` revival evidence in a new amendment ADR + plan. Cases C/D
  doctrinal clauses preserved as doctrine (unreachable at PreToolUse).
  See `.claude/adr/ADR-127-pair-rail-advisory-promotion.md`.
