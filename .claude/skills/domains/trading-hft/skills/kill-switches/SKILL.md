---
name: Kill Switches
description: Kill-switch and circuit-breaker engineering for HFT systems — independence from order paths, cancel-all flow correctness, position-flatten guarantees, panic dashboards, and termination SLAs.
trigger: Any change touching cancel-all, panic-flatten, circuit-breaker, drawdown limit, position limit, or order-rate throttle code paths. Pair with `order-routing` (cancel-on-disconnect) and `latency-budgets` (kill-path budget).
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: trading-hft
priority: 1
risk_class: high
stack: [python, cpp]
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: true, priority: 2}
  generic: {active: false, priority: 10}
activation_triggers:
  - {event: file-edit, regex: "(?i)kill.?switch|cancel.?all|panic.?flatten|circuit.?breaker"}
  - {event: help-me-invoked, regex: "(?i)kill.?switch|risk.?limit|drawdown"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/kill-switch/**"
  - "**/circuit-breaker/**"
  - "**/risk-limits/**"
  - "**/cancel-all/**"
---

# Kill Switches — Trading-HFT skill

> Owned by **Yara Bensoussan** (Kill-Switch Operator). VETO holder
> on any change touching the cancel / flatten / circuit-breaker
> paths.

## When to load this skill

- Adding or modifying any cancel-all / position-flatten code path
- Designing a new circuit breaker or risk limit
- Reviewing a kill-switch drill outcome
- Onboarding a new venue / strategy that needs kill coverage
- Investigating an incident where a kill switch failed to fire

## Core principle

**Every system has exactly one true kill switch.** The rest are theater
unless they are independent of the order-placement path AND can fire
within their documented SLA AND have been tested against simulated
failure modes (network partition, exchange outage, software hang).

A kill switch is real if and only if:

1. It does not depend on the same database / queue / cache as the
   order-placement path (no shared single-point-of-failure).
2. It can fire within the documented termination SLA (typically
   ≤ 1 second to first cancel, ≤ 5 seconds to last position).
3. It has been drilled within the last 30 days (paper or live).
4. It has an audit trail showing every fire event with operator,
   trigger, and outcome.

## Mandatory kill-switch tiers

Every HFT system MUST have at minimum:

- **Per-strategy kill** — disable a single strategy without affecting others
- **Per-symbol kill** — halt trading in a symbol across all strategies
- **Per-venue kill** — sever connection to a venue (last resort: rip
  the cable / fail the FIX session)
- **Global kill** — flatten all positions, cancel all orders, refuse
  new orders until manual re-arm

The global kill MUST be wired to a physical button or equivalent
out-of-band trigger (HTTP endpoint with a separate auth path is
acceptable for cloud venues).

## Anti-patterns to detect

- **Kill path queries the same Postgres as orders.** If the database
  is the failure mode, the kill cannot fire.
- **Cancel-all loops over `SELECT * FROM open_orders` then sends one
  cancel per row.** Use a venue-side mass-cancel API; if not
  available, batch.
- **Kill switch behind a feature flag.** The flag CAN'T be changed
  during the incident — it must always be active.
- **Position-flatten that retries on every error indefinitely.** Use
  a bounded retry with escalation to the next tier (per-symbol →
  per-venue → global).
- **Kill audit trail in the same database as orders.** Use a separate
  durable store (append-only file + sidecar, or a separate DB).

## Termination SLAs (illustrative — adjust per system)

| Tier | First cancel | Last cancel | Last flatten |
|---|---|---|---|
| Per-strategy | 100 ms | 500 ms | 2 s |
| Per-symbol | 200 ms | 800 ms | 3 s |
| Per-venue | 50 ms | 200 ms | 1 s |
| Global | 500 ms | 2 s | 5 s |

Each PR that touches a kill path MUST cite the affected SLA and
provide measurement evidence.

## Drill cadence

- **Per-strategy:** drill weekly per strategy
- **Per-symbol:** drill monthly per top-volume symbol
- **Per-venue:** drill quarterly per venue (paper)
- **Global:** drill quarterly (paper); annually (live, off-hours)

Drills produce a report card (pass / partial / fail) stored alongside
the audit trail. Three consecutive partials → escalate to CEO; any
fail → freeze new feature work until kill is restored.

## Output checklist (every kill-path PR)

- [ ] Documented termination SLA for the affected path
- [ ] Independence from order-path infra verified (no shared DB / cache / queue)
- [ ] Drill plan attached (how to verify in production)
- [ ] Audit trail captures who fired the kill, why, and outcome
- [ ] No new feature flag gating the kill
- [ ] Cancel batch / mass-cancel API used (no row-by-row)
- [ ] Latency budget for the cancel hot path met (`latency-budgets` skill)

## References

- ADR-013 (this squad)
- `order-routing` skill (cancel-on-disconnect is the venue-side pair)
- `latency-budgets` skill (cancel hot-path budget is a first-class budget)
- Universal `chaos-and-resilience` skill (drill methodology)
