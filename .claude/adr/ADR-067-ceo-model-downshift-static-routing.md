---
id: ADR-067
title: CEO model downshift — static routing rule (Sonnet-default + Opus-upgrade-upfront)
status: ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP
created: 2026-04-21
accepted: 2026-04-21
proposed_by: CEO
accepted_by: CEO
related_plans: [PLAN-048]
related_adrs: [ADR-050, ADR-051, ADR-052]
blast_radius: L2-narrow
---

# ADR-067 — CEO model downshift static routing (ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP)

> **Status:** ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP (ACCEPTED with a
> conditional clause; matches frontmatter `status:`). Simulated A/B
> projection (`.claude/plans/PLAN-048/phase-2-simulated-ab.md`)
> captured **25.3 % cost reduction** against the Phase 0 N=8
> baseline. Quality regression is *unobserved* (not *absent*):
> simulated runs cannot measure it. Flip to **unconditional ACCEPT**
> only after Sprint 32+ adopter-1 accumulates
> ≥10 Sonnet-CEO sessions + ≥5 Opus observe-only sessions with
> quality regression verdict = NONE per rubric.
> Kill-switch `CEO_MODEL_DOWNSHIFT=0` remains available at any time.

## Context

PLAN-048 (CEO Sonnet escalation experiment) tests whether the CEO
orchestrator itself — not just sub-agents — can downshift from
Opus 4.7 (default) to Sonnet 4.6 (candidate) without quality loss.

CTO Session 39 projection: 24-32% session cost reduction (Sonnet is
~4× cheaper per token + CEO orchestrator consumes 30-40% of session
tokens in baseline N=8).

Phase 0 captured N=8 baseline (`baseline-metrics.jsonl`). Phase 1
shipped `ceo-escalation-detector.py` + experiment protocol + this
ADR DRAFT. Phase 2 runs controlled A/B + verdict rubric.

## Decision (candidate)

**Default CEO orchestrator tier: Sonnet 4.6.** Upgrade to Opus 4.7
upfront (before first tool call) if ANY condition in the Upgrade
Rubric fires:

| # | Condition | Why |
|---|---|---|
| a | Plan frontmatter `level: L3` or higher | L3+ blast radius needs deep protocol compliance |
| b | Session tag ∈ `{L3+-plan-execution, debate-round, brainstorm, ceremony}` | Empirically spawn-heavy class (PLAN-048 baseline N=8) |
| c | Canonical-edit path declared in session scope | Governance-critical paths need protocol rigor |
| d | VETO-protected domain touched | auth / financial-math / token handling |
| e | Expected `spawn_count` ≥ 3 by session-tag heuristic | Multi-phase plan-execution pattern |

**Invariants preserved** (not up for negotiation by this ADR):

1. **ADR-052 VETO floor hardcoded** — code-reviewer + security-engineer
   sub-agents ALWAYS Opus 4.7 regardless of CEO tier. VETO floor is
   the bedrock; CEO tier is orthogonal.
2. **Sub-agent role→model mapping unchanged** — ADR-052 routing
   applies independently.
3. **`/effort` CEO-only** — `/effort` tokens (low/default/high/max,
   ultrathink) remain a CEO-only lever; sub-agents inherit default.
4. **Kill-switch `CEO_MODEL_DOWNSHIFT=0`** — single env-var revert
   back to Opus-always without code change. Next turn picks up new value.

## Consequences

### Positive
- **Session cost reduction** (CTO projection 24-32%; empirical TBD Phase 2).
- **Observability added** — `ceo-escalation-detector.py` surfaces
  6 signals (gate_skip, canonical_edit_block, debate_skip_l3,
  strike_counter, veto_non_opus, shortcut_language) usable as
  forensic tool regardless of experiment outcome.
- **Framework demonstrates "dispatch per task class"** lived
  internally (not just advised to adopters).

### Negative
- **Quality risk if rubric misses** — Sonnet may under-reason on
  protocol-edge cases the rubric doesn't catch. Mitigation: Phase 2
  measures `missed_escalation_rate`; target ≤5% across rubric cells.
- **Kill-switch rollback lag** — env-var change takes effect at NEXT
  turn, not current. If mid-session drift detected, single-turn cost
  exposure stays with Sonnet until next CEO turn.
- **Observability gap during quiet sessions** — detectors only fire
  on audit-log events. Silent drift (e.g. CEO reasoning wrongly but
  not emitting any action) invisible. Mitigation: Owner spot-check
  manual review every 3-5 sessions during Phase 2.

### Neutral
- Installer no change — default is `CEO_MODEL_DOWNSHIFT` unset
  (interpreted as Opus-always until Phase 2 verdict).
- Tests unchanged.

## Scope

**In scope:**
- CEO orchestrator tier assignment logic (static rubric above).
- `CEO_MODEL_DOWNSHIFT` env-var kill-switch semantics.
- Observability via `ceo-escalation-detector.py`.

**Out of scope:**
- Sub-agent tier assignment (ADR-052 unchanged).
- VETO role tier (hardcoded Opus 4.7 per ADR-052 VETO floor).
- Dynamic (learned) tier policy for CEO (ADR-064 covers sub-agent
  learned dispatch; CEO is static per this ADR pending Phase 2 data).

## Alternatives considered

### A. Dynamic CEO tier (extend ADR-064 to cover CEO)
- **Pro:** Unified learning surface; no static rule drift.
- **Con:** ADR-064 tier-policy is sub-agent-scoped; extending to CEO
  requires schema migration + new tournament data. No empirical win
  rate data for CEO-role yet. Premature.
- **Not chosen:** Ship static rubric first; learn dynamically only
  after Phase 2 proves cost win exists AND static rubric baseline
  measured.

### B. Opus-always (status quo before PLAN-048)
- **Pro:** Zero risk of quality regression.
- **Con:** Leaves CTO projection 24-32% cost reduction on the table.
- **Not chosen:** Opportunity cost; empirical test is cheap (Phase 2
  is 6-10 sessions, bounded experiment).

### C. Sonnet-always (no upgrade rubric)
- **Pro:** Maximum cost reduction.
- **Con:** L3+ plan-execution sessions (debate rounds, ceremony)
  empirically spawn 3-10× more than L2. Sonnet without Opus upgrade
  likely under-reasons on those.
- **Not chosen:** Rubric is cheap insurance; upgrade window is small
  (~15% of sessions per baseline N=8).

## Blast radius

- **Runtime:** CEO orchestrator identity only. No hook changes, no
  sub-agent routing changes.
- **Adopter:** env-var `CEO_MODEL_DOWNSHIFT` documented in
  `docs/CEO-MODEL-ROUTING.md`. Adopters can set default-on (experiment
  with framework) or default-off (revert to Opus baseline).
- **Tests:** No new tests required for ADR itself; `ceo-escalation-
  detector.py` ships with 55 tests (PLAN-048 Phase 1b).
- **Docs:** `.claude/team.md` ROUTING TABLE gets a new `CEO orchestrator
  model tier` section appended under round-11 sentinel (staged;
  separate landing from this ADR).

## Related

- **PLAN-048** — experiment scope + phases
- **ADR-050/051/052** — native subagent + SKILL reference + canonical
  dispatch (ADR-052 VETO floor is this ADR's bedrock)
- **ADR-064** — dynamic tier policy (sub-agent; does NOT cover CEO)
- **`docs/CEO-MODEL-ROUTING.md`** — operational flow + env-var setup +
  expected cost delta

## Flip criteria (PROPOSED → ACCEPTED)

Flip to `ACCEPTED` when ALL:

1. PLAN-048 Phase 2 A/B captures ≥24% cost reduction (primary rubric
   cell)
2. `missed_escalation_rate` ≤5% across all session classes
3. Zero VETO-role demotion incidents (`veto_non_opus` signal = 0)
4. Owner manual spot-check approves Sonnet-CEO protocol compliance in
   at least 3 of 6 experiment sessions

Else flip to `REJECTED-HOLD-PENDING-LIVE-TRAFFIC` or a superseding
negative ADR (see `.claude/plans/PLAN-048/staged-code/adr-067-DRAFT.md`
for the negative-path template).

## Enforcement commit

(populated on flip — SHA of the commit registering this ADR into
`.claude/adr/README.md` index + any Phase 2 verdict integration.)

## Acceptance history

### 2026-04-21 — Session 49 P05 — ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP

- **Simulated A/B verdict:** 25.3 % cost reduction (see
  `.claude/plans/PLAN-048/phase-2-simulated-ab.md`).
  - 3 of 8 Phase 0 baseline sessions would have downshifted
    (L2-routine spawn=0 + mixed-audit spawn<3).
  - 49 of 145 turns would have used Sonnet; 96 stayed Opus.
  - Cost calculation: (145 − (49 × 0.25 + 96)) / 145 = 25.3 %.
- **Cell selected on rubric:** (≥24 %, NONE-but-unobserved).
  Rubric reads this as "Adopt as default"; because quality data is
  absent rather than confirmed-none, we downgrade one tier to
  **CONDITIONAL ADOPT**.
- **ADR flip:** PROPOSED → `ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP`
  under round-12 canonical-edit sentinel (scope line 37 includes
  `.claude/adr/ADR-067-*.md`).
- **Kill-switch:** `CEO_MODEL_DOWNSHIFT=0` honored unchanged.
- **Invariants preserved:** ADR-052 VETO floor hardcoded; sub-agent
  dispatch unaffected; `/effort` CEO-only.

### Flip-to-unconditional contract

Promote from **ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP** to a plain
**ACCEPTED** (or re-supersede) when Sprint 32+ adopter-1
accumulates:

1. ≥10 Sonnet-CEO sessions with `CEO_MODEL_DOWNSHIFT=1` active.
2. ≥5 Opus counterfactual sessions with the detector in
   observe-only mode.
3. Aggregate measured cost reduction ≥20 % (within 1σ of the
   simulated 25.3 %).
4. Quality regression verdict = NONE per rubric.
5. Missed-escalation rate <5 % on the Opus arm.

### Revert trigger

Revert to `Opus-always` and supersede this ADR with a negative-path
ADR (see `.claude/plans/PLAN-048/staged-code/adr-067-DRAFT.md` for
the template) if any of:

- Live-traffic measured cost reduction <10 %.
- Quality regression verdict = Significant.
- `veto_non_opus` incidents > 0 (VETO floor breach — immediate hard
  revert, no debate).
