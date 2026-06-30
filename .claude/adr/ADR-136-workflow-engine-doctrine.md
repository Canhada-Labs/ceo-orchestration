---
id: ADR-136
title: Workflow-engine doctrine — spec-kit port study (SKIP recommended)
status: ACCEPTED
proposed_at: 2026-05-20
proposing_session: S147
accepted_at: 2026-06-17
accepting_session: S242
enforcement_commit: 9ab23cb6
related_plans: [PLAN-110]
related_adrs: [ADR-115, ADR-125, ADR-126, ADR-132]
risk_tier: A
debate_required: true
---

# ADR-136 — Workflow-engine doctrine

## Context

GitHub's `spec-kit` (v0.8.11+) ships a YAML-driven workflow engine at
`src/specify_cli/workflows/` with 10 step types (`command/prompt/shell/
gate/if/switch/while/do-while/fan-out/fan-in`), a 5-state machine
(`CREATED→RUNNING→{COMPLETED,PAUSED,FAILED,ABORTED}`), append-only
`log.jsonl` per run, expression engine (Jinja2-like with filters
`default/join/contains/map`), SHA256-hashed 1h-TTL catalog with env
override, and a CLI surface `specify workflow run|resume|status|list|
add|remove|search|info`. Documented at `workflows/ARCHITECTURE.md:
L289-L319` + `L327-L340` + `L384-L390` + `L413-L415`.

The closest sibling in ceo-orchestration is the **GOAP A* advisory**
planner (PLAN-098 + PLAN-105 instrumentation; ADR-132). GOAP is
advisory-only — it generates plans but never executes them. Ceremony
execution today is human-orchestrated: `apply-patches.py` + bash
ceremony scripts (e.g., `OWNER-CEREMONY-SHIP-v1.38.3.sh`) drive the
state machine implicitly via Phase 0 -> Phase G semantics.

The doctrinal question Wave F adjudicates: **should we port any
portion of spec-kit's workflow engine surface area?**

## Decision

**PROPOSED: SKIP** for v1.39.0.

Workflow automation is incompatible with our governance-as-text +
Owner-physical-gate + /debate-VETO doctrine. Concretely:

1. **Auto-execution conflicts with VETO**. spec-kit's
   `EXECUTE_COMMAND` semantics (`templates/commands/plan.md:L275-L303`,
   PLAN-110 Anti-Goal #1) allow command chaining without human
   intervention. Our Plan->Debate->Execute requires Owner physical
   gate (GPG sentinel) at every L3+ transition. A YAML state machine
   that drives execution forward without explicit Owner approval
   per phase weakens this moat.
2. **State persistence adds attack surface**. `state.json` + `log.jsonl`
   per run are new forgery + tampering vectors. Our existing
   `audit-log.jsonl` is kernel-managed (single writer); adopting
   spec-kit's per-run state files would split the audit trail across
   multiple files with no cross-file integrity binding.
3. **+2000 LoC + 30+ tests**. Cost-benefit at v1.39.0 is unfavorable.
   No current adopter has surfaced a need for fan-out/fan-in primitives
   beyond what Owner-paced sub-agent dispatch already provides.
4. **GOAP advisory + ceremony bash already covers happy path**.
   PLAN-098 + PLAN-105 give us advisory planning. `apply-patches.py`
   gives us deterministic + idempotent + testable execution. The
   only gap is automated resume after partial failure — and that gap
   is BEST filled by improving ceremony idempotency (already
   achieved per PLAN-104 + PLAN-105) rather than adopting a foreign
   engine.

If a future PLAN-NNN identifies a concrete adopter need (e.g.,
parallel fan-out across 10+ sub-agents with automated rendezvous),
ADAPT the gate-step pattern only as a new ceremony primitive — do
NOT port the full engine. That ADAPT decision would warrant its own
ADR + debate.

## Consequences

### Positive

- **Doctrinal purity preserved**. ceremony-as-bash + GPG-sentinel + VETO
  remains foundational.
- **Zero new attack surface**. No run-id forgery, no log tampering vectors.
- **Zero migration cost** for existing PLANs 001-109.
- **Continued portability**. Adopters running both spec-kit and
  ceo-orchestration can use spec-kit's workflow engine for artifact
  generation + ceo-orchestration for governance enforcement.

### Negative

- **No automated fan-out/fan-in primitive**. Continues to depend on
  Owner-paced sub-agent dispatch + manual aggregation.
- **No automated resume**. Partial-failure recovery requires manual
  intervention (re-run idempotent waves).
- **Adopter friction**. Users coming from spec-kit may expect a
  workflow engine and not find one. Mitigated by §References below.

### Neutral

- Future Owner-approved ceremony may revisit ADAPT (gate-step pattern
  only) at a separate PLAN-NNN.

## Alternatives Considered

### Alternative 1: ADOPT (full port)

Pros: workflow automation, fan-out/fan-in primitives, automated resume.
Cons: +2000 LoC, state persistence attack surface (run-id forgery, log
tampering), new Tier classification questions, doctrinal conflict with
/debate VETO. **REJECTED** — cost-benefit unfavorable; doctrinal
conflict unresolvable without weakening governance moat.

### Alternative 2: ADAPT (gate-step pattern only)

Pros: incremental, low-risk, surgical port. Limited scope.
Cons: limited immediate value; no current adopter need. **DEFERRED** to
future PLAN-NNN if concrete need surfaces. Not rejected outright.

### Alternative 3: SKIP (this ADR's recommendation)

Pros: zero risk, doctrinal purity, ceremony-as-bash continues to scale
within current Owner-pace ceiling. Cons: see Negative consequences.
**RECOMMENDED**.

## References

- spec-kit `workflows/ARCHITECTURE.md:L289-L319` — 10 step types + state machine
- spec-kit `workflows/ARCHITECTURE.md:L327-L340` — expression engine
- spec-kit `workflows/ARCHITECTURE.md:L384-L390` — log.jsonl per run
- spec-kit `workflows/ARCHITECTURE.md:L413-L415` — CLI surface
- PLAN-098 — GOAP A* advisory planning doctrine
- PLAN-105 — GOAP instrumentation wire-in
- ADR-132 — GOAP advisory-only planning doctrine
- ADR-125 §A — Tier-A defensibility
- PLAN-110 §6 Anti-Goal #1 (EXECUTE_COMMAND ban)
- PLAN-110 §6 Anti-Goal #3 (no workflow engine code in Wave F)
- `.claude/plans/PLAN-110/wave-f-research.md` — step-type mapping table

## Notes

**ACCEPTED (S242, 2026-06-17 — /ceo-boot ADR sweep).** Per S133 ADR-132 +
S140 ADR-019-AMEND-1 precedent, promotion to ACCEPTED required:

1. Codex MCP R2 ≥3-iter ACCEPT. — **satisfied**: Codex R-sweep ACCEPT, thread
   `019ed788` (S242), which accepted the SKIP decision's soundness.
2. Owner GPG-signed sentinel for promotion. — **satisfied**: the Owner-GPG
   ceremony commit applying this sweep is the signing artifact, mirroring the
   ADR-136-AMEND-1 (S228) promotion record where the Owner directive + ceremony
   commit stood in place of a dedicated sentinel path.
3. Separate ceremony bundle. — **satisfied**: the `staged/promote/` materialized
   bundle + `finish-adr-sweep.sh` (apply-with-rollback; dry-run GREEN) is it.

**Enforcement commit:** `9ab23cb6` (the ADR-136-AMEND-1 promotion that activated
the harness-native workflow primitives this base doctrine governs). The base SKIP
(do not port the YAML engine) is in force: no engine in the tree; the confined
`parallel()`/`pipeline()`/`phase()` primitives run in production workflows.
