---
name: Kill Switches
description: Kill-switch and circuit-breaker engineering for HFT systems — independence from order paths, cancel-all flow correctness, position-flatten guarantees, panic dashboards, and termination SLAs.
trigger: Any change touching cancel-all, panic-flatten, circuit-breaker, drawdown limit, position limit, or order-rate throttle code paths. Pair with `order-routing` (cancel-on-disconnect) and `latency-budgets` (kill-path budget).
inspired_by:
  - source: affaan-m/ecc/skills/llm-trading-agent-security/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
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
source: affaan-m/ecc@81af4076 skills/llm-trading-agent-security/
license: MIT
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
- Bringing an autonomous / LLM-driven agent tier under kill coverage

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

## Autonomous / LLM-driven order sources

When a strategy tier's order flow is produced by an autonomous or
LLM-driven agent holding wallet or execution authority, the threat model
sharpens: a bad tool path or an injected instruction turns directly into
asset loss, on a path with no human in the loop to hesitate. This skill's
**core principle already covers it** — a real kill/limit control is
independent of the order-placement path. An LLM agent is simply an
*untrusted* order source, and the risk layer must sit BELOW it,
un-bypassable by anything the agent emits (including text the agent was
talked into). Treat the following as independent, layered controls; no
single one is sufficient.

1. **Untrusted-input hygiene — injected text is a financial attack.**
   External data that reaches an execution-capable prompt (token names,
   pair labels, social / news feeds, on-chain memo or calldata fields,
   webhook payloads) is attacker-reachable. A prompt injection here can
   drive the agent to size, place, redirect, or *suppress* orders —
   including talking it out of firing a kill. Sanitize or quarantine
   external data before it enters the decision context; never splice raw
   feed / on-chain text into an order-emitting prompt. High-signal
   patterns to screen for: instruction-override phrasing ("ignore prior
   instructions", "new directive") and unsolicited transfer / approve /
   send-to-address directives embedded in data. Treat this filter as
   advisory defense-in-depth — it is bypassable and is NOT the
   load-bearing control.

2. **Hard spend / notional limits, enforced independently of model
   output.** A max-single-transaction and max-rolling-window notional cap
   the agent cannot raise or route around — the spend-side analogue of a
   position limit. Enforce it in a process / store separate from the
   agent, the same independence rule this skill applies to the kill path
   and its audit trail. A limit the model can argue past is theater.

3. **Pre-send simulation as a fire-before-harm gate.** Simulate the
   transaction (`eth_call` / static call) and require an explicit expected
   bound (`min_amount_out` or equivalent); reject on divergence before
   signing. A *missing* expected-output bound is itself a defect — refuse
   to send rather than send blind.

4. **Circuit breaker on consecutive losses / windowed drawdown.** Halt
   and require manual re-arm on N consecutive losses or a windowed PnL
   breach — the same shape as the Global kill ("refuse new orders until
   manual re-arm"). An invalid or zero baseline (e.g. `hour_start ≤ 0`)
   must halt, never divide-by-zero into a bad ratio.

5. **Wallet / blast-radius isolation.** Point the agent at a dedicated
   hot wallet funded with only the current session's working capital;
   never at a primary treasury. Keys come from env or a secret manager,
   never from code or logs. This is the per-venue-kill principle applied
   to key custody — it bounds what a hijacked or injected agent can lose.

6. **Audit-log every decision, not just executed sends.** Blocked,
   simulated-and-rejected, and injection-flagged attempts must be recorded
   to the same durable, order-path-independent store this skill requires
   for kill-fire events. If the only trace is successful sends, the
   incident review is blind to exactly the attempts that mattered.

MEV protection, private-mempool routing, and per-strategy deadlines are
adjacent execution-quality controls; they belong to the `order-routing`
and `latency-budgets` skills — cross-reference rather than duplicate here.

### Agent-tier kill checklist (in addition to the standard kill-path checklist)

- [ ] Spend / notional cap enforced in a process independent of the agent
- [ ] External data sanitized before entering the execution-capable prompt
- [ ] Transactions simulated with a mandatory expected-output bound before send
- [ ] Circuit breaker halts on drawdown / consecutive loss / invalid baseline
- [ ] Dedicated session hot wallet; keys from env or secret manager (never code / logs)
- [ ] Every agent decision audit-logged (blocked + rejected + injected, not only sends)

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

## Changelog

- **PLAN-153 Wave G (SP-032, 2026-07-09):** autonomous/LLM-agent kill-switch doctrine folded in (clean-room ADAPT; provenance in frontmatter/NOTICE).
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=2c78314618e48f928a02e6e45b30f1a9528de045d526256622d4798658ffb197
