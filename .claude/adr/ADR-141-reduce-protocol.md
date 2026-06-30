---
id: ADR-141
title: Evidence-bound REDUCE protocol for swarm fan-out — Kimi-inspired, internally grounded
status: ACCEPTED
date: 2026-05-27
related: [ADR-058, ADR-052, ADR-108, ADR-104, ADR-055]
accepted_at: 2026-05-28
accepting_session: S177
authorization: PLAN-117 WS-B sentinel `.claude/plans/PLAN-117/architect/round-4/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
---

# ADR-141: Evidence-bound REDUCE protocol for swarm fan-out

**Status:** ACCEPTED (S177, 2026-05-28)
**Date:** 2026-05-27
**Enforcement commit:** `fa9a5c4` (PLAN-115 Batch-3 — REDUCE protocol doc + worker return-status contract, S170)
(`docs/triage-reduce-protocol.md` + the `core/ai-llm-orchestration`
cross-link + the `team.md` §Worker return-status contract). Tier-1 metrics are
derivable now from audit-log timestamps; Tier-2 metrics require the 8-field
schema wired as typed `audit_emit` events (future work) — until then they are
documented as NOT-yet-measured to avoid a false-green._
**Decision drivers:** the REDUCE step is the laundering risk in fan-out;
PLAN-113 reopened 4 laundered drops; PLAN-114 found ~57% stale findings; the
"+2 sweeps" deferral trigger for this doctrine has already fired.

## Context

The S163 session analyzed the Moonshot "Kimi Agent Swarm" (reported as K2.6,
~300 parallel sub-agents trained via PARL — these external specifics were NOT
independently verified; see §Attribution) against this framework and asked
whether to adopt a swarm architecture. The Codex pair-rail (thread `019e5f6b`) **converged** on
the verdict: **NOT a new SOTA architecture for us.** Kimi optimizes
embarrassingly-parallel, low-error-cost workloads; this framework operates at
the opposite end — coupled, high-error-cost mutations over shared state (the
repo), where one wrong canonical edit is a governance incident. Write-path
parallelism here is **dependency-graph-bound**, not agent-count-bound.

The one worth-importing kernel is the **REDUCE** step. We already run the safe
MAP half (PLAN-112/113 fan out 8–31 shards with evidence pointers + an
author/reviewer split + Codex anti-laundering). What was implicit and
unspecified is the REDUCE contract: how the reducer adversarially verifies shard
outputs against evidence instead of merging summaries.

When this doctrine was first sketched (S163), the framework convention (ADR
README) was to defer a dedicated ADR until a pattern recurs in **+2 sweeps**.
That trigger has now fired: PLAN-112 and PLAN-113 are two independent sweeps
that both depended on exactly this REDUCE discipline (PLAN-113's anti-laundering
pass reopened 4 laundered drops). The ADR is therefore no longer premature.

## Decision drivers

- The REDUCE step is the single laundering point in any fan-out.
- Empirical: PLAN-113 reopened 4 laundered drops; PLAN-114 found ~57% of a 307
  backlog stale → verification must scale by risk + drop-rate, not fan-out.
- Same-model shards share correlated blind spots (ADR-052/108 same-LLM problem).
- A float in an HMAC-covered emit raises `CanonicalJsonError`; `audit_emit`
  fail-opens (writes `hmac=null` + `hmac_error`, breadcrumbs to `audit-log.errors`)
  → the event persists but loses HMAC coverage (S164 class) — the schema's
  `confidence` must be integer basis-points.

## Options considered

### Option A: Standalone reference doc + ADR-141 (CHOSEN)

`docs/triage-reduce-protocol.md`, cross-linked from `core/ai-llm-orchestration`,
backed by this ADR. **No new core skill** (no count bump).

- **Pros:** lightest form; discoverable; does not bloat the 549-line,
  security-owned `ai-llm-orchestration` SKILL.md (which already carries a
  stale-metric apology) nor add a second count ceremony.
- **Cons:** a doc is not auto-loaded as a skill — relies on the cross-link.

### Option B: Fold into `ai-llm-orchestration`

- **Cons:** worsens that skill's CSO/length problem; entangles a new doctrine
  with an already-overloaded skill. **Rejected** (Wave A Q5).

### Option C: Full core skill `triage-reduce-protocol`

- **Cons:** a second count-bump ceremony (core 42→43, total 151→152) for content
  that is reference doctrine, not an archetype operating manual. Deferred — the
  Owner may promote later if it earns skill-level activation.

## Decision

Adopt the **evidence-bound REDUCE protocol** as a standalone reference doc
(`docs/triage-reduce-protocol.md`), cross-linked from `core/ai-llm-orchestration`
and paired MAP-side with the `team.md` worker return-status contract (WS-C). The
protocol mandates an 8-field shard-output schema (with redaction +
integer-basis-point `confidence`), a reducer rule (no evidence-free
accept/drop; security/canonical require independent cross-rail review),
two-tier metrics (Tier-1 derivable now, Tier-2 needs schema wiring), four
failure modes each with a concrete mitigation (shard-size/straggler sub-rules;
≥40% drop-density two-pass reducer; `scan_harness_mimicry` quarantine), and the
hard anti-pattern that an evidence-free summary merge is a governance failure.
**PARL is imported as instrumentation only** (critical-path accounting +
serial-collapse detection) — not a bigger swarm and not training.

## Consequences

- **(+)** Closes the REDUCE-side gap with an auditable, evidence-bound contract;
  pairs with WS-C to give both halves of map-reduce swarm orchestration.
- **(+)** Encodes the S164 float-in-HMAC lesson into the schema (basis-points).
- **(−)** Tier-2 metrics are not yet wired (typed `audit_emit` events) — honestly
  flagged as future work, not claimed as live.
- **(~)** Reference-doc form (not a skill) → discoverability depends on the
  cross-link, accepted to avoid a premature second count ceremony.

## Blast radius

**L3+** — cross-cutting orchestration doctrine touching a new doc, a core-skill
cross-link, `team.md`, and the framework ADR/count surface (ADR 151→152).

## Attribution (AC-E4)

The Moonshot "Kimi Agent Swarm" (K2.6 / PARL) is cited as **inspiration only**
(ADR-058 attribution style). The protocol's load-bearing claims trace to
**internal precedent** — the PLAN-112/113 fan-out + anti-laundering and the
S164/S167 burndown — not to the external analysis. External Kimi URLs and a
plan-filename-with-line-numbers cited during S163 were **NOT independently
verified** and are deliberately not referenced as fact in any shipped artifact.
Analysis record + Codex convergence: memory `reference-kimi-agent-swarm-analysis-s163`
(thread `019e5f6b`). PLAN-113 remains the living experiment — this ADR
forward-specifies the contract; it does not reopen or retro-audit PLAN-113.
