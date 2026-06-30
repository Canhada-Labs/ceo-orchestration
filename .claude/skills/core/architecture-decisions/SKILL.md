---
name: architecture-decisions
description: Architecture decision-making framework for {{PROJECT_NAME}}. Covers
  ADR (Architecture Decision Record) format, trade-off analysis matrices, dependency
  graph analysis, blast radius assessment, system boundary identification, scalability
  testing ("10x scale" rule), when to refactor vs rewrite, multi-process architecture
  patterns, and cross-cutting concern management. Use when evaluating changes that
  touch 3+ modules, planning new features, assessing refactoring proposals, reviewing
  system boundaries, or making decisions that will be hard to reverse. This is the
  VP Engineering archetype's operating manual for architectural governance.
owner: VP Engineering (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-software-architect.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/testing/testing-tool-evaluator.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: medium
stack: []
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: plan-opened}
  - {event: help-me-invoked, regex: "(?i)adr|architecture.?decision"}
---

# Architecture Decisions

## Fail-Fast Rule

If an architecture decision is irreversible and affects 3+ modules, **stop
and write an ADR first**. Never implement a cross-cutting change without
documenting the trade-offs. Never assume a "quick fix" to a structural
problem won't have cascading effects.

## The 10x Scale Rule

Every architecture decision must pass this test:
> "Does this scale to 10x the current number of integrations / users / events
> without a rewrite?"

If the answer is no, the architecture is wrong — even if it works today.

For a system with N upstream integrations across M pool workers, plan for 10·N:
- Pool workers may need to grow roughly linearly (resource allocation)
- IPC throughput grows linearly with the number of entities
- Memory footprint grows linearly — watch for per-entity overhead
- New integration quirks multiply combinatorially

## ADR Template

**Where ADRs live in this framework:** `.claude/adr/<ADR-NNN-slug>.md` —
see `.claude/adr/README.md` for naming, lifecycle, and the existing
records (`ADR-001` runtime state directory, `ADR-002` Python hooks
package layout, `ADR-003` branch protection replaces skill signing).
The existing ADRs are concrete examples to follow.

Every significant architecture decision gets recorded:

```markdown
# ADR-{NNN}: {Title}

## Status: PROPOSED | ACCEPTED | REJECTED | SUPERSEDED

## Context
What problem are we solving? Why now?

## Decision Drivers
- Driver 1 (e.g., latency budget)
- Driver 2 (e.g., memory constraint)

## Options Considered
### Option A: {Name}
- Pros: ...
- Cons: ...
- Risk: ...

### Option B: {Name}
- Pros: ...
- Cons: ...
- Risk: ...

## Decision
Option {X} because {rationale}.

## Consequences
### Positive
- ...
### Negative
- ...
### Neutral
- ...

## Blast Radius
Modules affected: {list}
Reversibility: HIGH | MEDIUM | LOW
```

## System Boundaries (example layout)

Every project has its own boundaries; the diagram below is a template. Fill in
with your actual boundaries and assign owners from your team archetypes.

```
┌──────────────────────────────────────────────────────┐
│ BOUNDARY 1: External APIs (upstream integrations)    │
│ Trust: ZERO. Validate everything.                    │
│ Owner archetype: Integration Engineer + API Engineer │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────┐
│ BOUNDARY 2: Worker Process ↔ Main Process            │
│ IPC: binary (hot) + JSON (control)                   │
│ Owner archetype: Real-Time Systems + Performance     │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────┐
│ BOUNDARY 3: Main Process ↔ Clients                   │
│ HTTP/WS/SSE. Auth required.                          │
│ Owner archetype: API Engineer + Security             │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────┐
│ BOUNDARY 4: Main Process ↔ Database                  │
│ PostgREST + RLS, or your ORM + access control.       │
│ Owner archetype: Data Engineer + Security            │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────┐
│ BOUNDARY 5: Main Process ↔ Mutation Workers          │
│ HTTP + HMAC auth or signed tokens.                   │
│ Owner archetype: API Engineer + Security             │
└──────────────────────────────────────────────────────┘
```

## Trade-Off Analysis Framework

For any decision with 2+ viable options:

| Dimension | Weight | Option A | Option B |
|-----------|--------|----------|----------|
| Latency impact | HIGH | Score 1-5 | Score 1-5 |
| Memory impact | HIGH | Score 1-5 | Score 1-5 |
| Complexity | MEDIUM | Score 1-5 | Score 1-5 |
| Reversibility | MEDIUM | Score 1-5 | Score 1-5 |
| Maintenance | LOW | Score 1-5 | Score 1-5 |
| Blast radius | HIGH | L1-L5 | L1-L5 |

Score: 5 = best, 1 = worst. Weighted sum decides.

## When to Refactor vs Rewrite

| Signal | Action |
|--------|--------|
| 1-3 fixes solve the problem | Fix. Don't refactor. |
| Same area breaks 3+ times | Refactor the module. |
| Fix requires touching 5+ files | Architecture problem. Write ADR. |
| "It works but I don't know why" | Rewrite with tests first. |
| Performance < 50% of budget | Profile → targeted optimization. |
| Performance < 10% of budget | Architecture is wrong. Redesign. |

## Dependency Analysis

Before approving any cross-cutting change:
1. List every file that imports the changed module
2. List every module that the changed module imports
3. Draw the dependency subgraph (who depends on whom)
4. Identify circular dependencies
5. Assess: if this module breaks, what else breaks?

## Current Architecture Invariants (NEVER violate)

1. **Main thread does NO heavy computation** — all CPU work in workers
2. **IPC is batched** — never send individual events, always batches
3. **Fast path bypasses the batch worker** — raw events reach main in ~50ms
4. **Low-priority entities skipped on fast path** — only HOT+WARM get fast delivery
5. **Per-entity state uses in-place mutation** — no object creation on hot path
6. **PubSub guarded by subscriber count** — skip serialize when nobody listens
7. **SharedArrayBuffer is display-only** — never for business-critical math
8. **Each adapter pool is independent** — one pool crash doesn't affect others

## Review Protocol

When reviewing an architecture proposal:
1. Does it pass the 10x scale rule?
2. What's the blast radius? (L1-L5)
3. Is it reversible? (can we undo in < 1 hour)
4. Does it violate any invariant above?
5. Does it add a new system boundary?
6. Does it change the data flow diagram?
7. Who else needs to review? (e.g. the financial-math specialist for numeric correctness, the security engineer for auth/crypto, the performance engineer for hot-path impact)

## Domain-Driven Design Reference

Domain modeling is a prerequisite for drawing system boundaries. Without
explicit bounded contexts, components grow entangled and ADRs reference
concepts the codebase and the business define differently.

### Bounded contexts as ADR candidates

Every context boundary is a potential ADR. When two sub-domains share a
concept that means different things to each (e.g., "Account" in billing vs.
"Account" in identity), that semantic clash must be captured before any
code crosses the boundary.

Rules:

- **One ubiquitous language per bounded context.** Terms used in code MUST
  match terms used in the product spec and business documentation for that
  context. If the code says `UserAccount` and the business says `Subscriber`,
  one is wrong.
- **Context mapping is strategic, not tactical.** The upstream/downstream
  relationship between two contexts — and whether an anti-corruption layer
  (ACL) is needed — belongs in an ADR, not a code comment.
- **Aggregate roots own invariants.** An aggregate root is the only entry
  point for mutations inside its boundary. NEVER reach inside an aggregate
  to mutate its children directly.

### CORRECT vs WRONG — ubiquitous language

```
# CORRECT
# Billing context: "Invoice" (amount in cents, VAT line items, issue date)
# The code model matches the business spec vocabulary exactly.
class Invoice:
    id: InvoiceId
    line_items: list[LineItem]
    issued_at: datetime

# WRONG
# Billing context uses "Invoice" but code says "Bill" or "PaymentRequest"
# — the mismatch means every code review requires a mental translation step
# and the spec/ADR will drift from the implementation silently.
class Bill:   # DO NOT use when the domain says "Invoice"
    ...
```

### Strategic vs tactical patterns

| Decision type | Mechanism |
|---|---|
| Context boundary + ownership | ADR (strategic — cross-cutting, hard to reverse) |
| Upstream/downstream relation, ACL, conformist | ADR (strategic) |
| Aggregate root, value object, domain event | Code + PR comment (tactical — reversible within the context) |
| Repository interface vs. direct ORM access | ADR if shared across contexts; PR comment if local |

### Anti-pattern: anemic domain model

An anemic domain model is a domain object that holds data but contains no
behavior — all business logic lives in service classes outside the object.
This is WRONG when the domain has invariants that must be enforced on every
mutation path.

```
# WRONG — anemic model, invariants enforced nowhere
class Order:
    items: list[OrderItem]
    total: Decimal

class OrderService:
    def add_item(self, order: Order, item: OrderItem) -> None:
        order.items.append(item)          # no invariant check
        order.total += item.price         # no constraint validation

# CORRECT — invariants live in the aggregate root
class Order:
    _items: list[OrderItem]

    def add_item(self, item: OrderItem) -> None:
        if len(self._items) >= MAX_ITEMS_PER_ORDER:
            raise OrderLimitExceeded(MAX_ITEMS_PER_ORDER)
        self._items.append(item)
        # total is derived, not stored separately
```

## Tool and Library Evaluation Rubric

Every new dependency is a long-term commitment. Evaluate before adopting;
re-evaluate on a cadence after adoption. The rubric below applies to any
third-party library, framework, or infrastructure tool.

### Scoring axes (rate each 1–5, 5 = favorable)

| Axis | What to measure | Weight |
|------|----------------|--------|
| Security posture | CVE history, disclosure policy, signed releases, dependency chain depth | HIGH |
| Ecosystem health | Downstream adoption count, corporate backer vs. community-only, forks activity | MEDIUM |
| Maintenance signal | Commit recency, issue response latency, breaking-change cadence, semver discipline | HIGH |
| Lock-in cost | Proprietary API surface, data format portability, migration complexity if ejected | HIGH |
| Learning curve | Time-to-first-working-prototype for a mid-level engineer unfamiliar with the tool | LOW |

Adoption gates (apply by axis weight; the weights are gate priorities,
not numeric multipliers):

- HIGH-weight axes (security, maintenance, lock-in): MUST score ≥ 4.
- MEDIUM-weight axes (ecosystem): MUST score ≥ 3.
- LOW-weight axes (learning curve): score ≥ 2 acceptable.

If any HIGH-weight axis scores ≤ 3, REJECT or require explicit Owner
override with a documented mitigation in the ADR. Tradeoffs are not
absolved by averaging across axes.

### Reversibility tiers

Classify the candidate before scoring. Tier determines how much due diligence
is required.

| Tier | Definition | ADR required? | Re-evaluation cadence |
|------|-----------|---------------|-----------------------|
| **Drop-in** | Can be swapped for another implementation in ≤1 day; no data format lock-in | No | At major version bumps |
| **Embedded** | Permeates call sites or data models; migration cost 1–4 weeks | Yes (≤200 LoC ADR) | 12 months or on major version |
| **Infrastructure-coupled** | Owns a data store, protocol, or deployment surface; ejection cost > 1 month | Yes + security review | 6 months |

NEVER adopt an infrastructure-coupled dependency without a written exit
strategy in the ADR. "We'll figure it out" is not an exit strategy.

### Decision artifact

For Embedded and Infrastructure-coupled candidates, produce a small ADR
(target ≤200 LoC) using the template in this skill. Include:

```markdown
## Dependency: {name} v{version}
## Reversibility tier: Drop-in | Embedded | Infrastructure-coupled
## Exit strategy: {how we remove it if needed, in concrete steps}
## Re-evaluation date: {YYYY-MM-DD}
## Score summary:
| Axis | Score | Notes |
|------|-------|-------|
| Security posture | N/5 | ... |
| Ecosystem health | N/5 | ... |
| Maintenance signal | N/5 | ... |
| Lock-in cost | N/5 | ... |
| Learning curve | N/5 | ... |
| HIGH-axis gates (security / maintenance / lock-in) | pass / fail | all three MUST score ≥ 4 |
| MEDIUM-axis gate (ecosystem) | pass / fail | MUST score ≥ 3 |
| LOW-axis (learning curve) | informational | recorded for context; no minimum gate (a low score is a budget signal for onboarding/training, not a rejection signal) |
| Decision | ADOPT / DEFER / REJECT | with explicit rationale if any HIGH-axis gate fails |
```

### Anti-patterns

- **Adopting because it is popular.** Popularity is an ecosystem-health
  signal, not a security or reversibility signal. Measure all axes.
- **Skipping re-evaluation.** A library that scored 4.2 at adoption can
  score 2.8 eighteen months later (maintainer abandonment, CVE accumulation,
  API churn). Set a calendar reminder at adoption time.
- **Treating the default package manager choice as a decision.** Transitive
  dependencies require the same reversibility classification as direct ones
  when they own a data format or protocol surface.
