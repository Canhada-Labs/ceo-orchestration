---
name: hexagonal-architecture
description: >
  Ports & Adapters (hexagonal) design discipline for keeping business logic
  independent of frameworks, transport, and persistence. Covers the inward
  dependency rule, inbound/outbound port modelling, use-case orchestration with
  injected ports, edge adapters, the single composition root, per-boundary test
  strategy, a slice-by-slice strangler migration playbook, and the cross-language
  mapping of the same boundary rules onto TypeScript, Java, Kotlin, and Go layouts.
  Use when: standing up a new feature where testability and long-term change cost
  matter; refactoring a framework-heavy or layered service where domain logic is
  tangled with I/O; exposing one use case over multiple interfaces (HTTP, CLI,
  queue worker, cron); or swapping infrastructure (DB, third-party API, message
  bus) without rewriting business rules.
version: 1.0.0
inspired_by:
  - source: affaan-m/ecc/skills/hexagonal-architecture/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0b shape) ---
domain: architecture
priority: 8
risk_class: low
stack: []
context_budget_tokens: 900
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)hexagonal|ports?\\s*(&|and)\\s*adapters|clean architecture|dependency inversion|use[- ]case boundary|composition root"}
  - {event: file-edit, glob: "**/ports/**"}
  - {event: file-edit, glob: "**/adapters/**"}
  - {event: file-edit, glob: "**/use-cases/**"}
# --- K1 paths: native file-touch activation ---
paths:
  - "**/ports/**"
  - "**/adapters/**"
  - "**/use-cases/**"
  - "**/usecases/**"
  - "**/composition/**"
source: affaan-m/ecc@81af4076 skills/hexagonal-architecture/
license: MIT
---

# Hexagonal Architecture (Ports & Adapters)

## When to Activate

Read this skill when you are:

- building a new feature and want long-term maintainability and testability
  designed in from the first commit, not retrofitted;
- refactoring a layered or framework-heavy service where domain rules are
  entangled with HTTP handlers, ORM models, or SDK calls;
- driving the same use case from more than one interface — an HTTP route, a
  CLI, a queue consumer, a scheduled job — without duplicating logic;
- replacing an infrastructure dependency (database, external API, message bus)
  and want the business rules to survive the swap untouched.

The machine-first `activation_triggers` frontmatter is the canonical auto-load
rule; this section is its human-scannable mirror.

## The one rule everything else serves

**Dependencies point inward.** The core — domain rules and the use cases that
orchestrate them — never imports a framework, a driver, a transport type, or a
concrete client. The core depends only on *abstractions it owns* (ports).
Everything technology-specific lives at the edges (adapters) and depends on the
core, never the reverse.

If you remember nothing else: an entity or use case that `import`s an ORM row,
a web `Request`, or a vendor SDK has already broken the architecture.

## The pieces

| Piece | Responsibility | Knows about |
|---|---|---|
| **Domain model** | Entities, value objects, invariants — the business rules | Nothing external |
| **Use case** (application layer) | Orchestrates domain behaviour and workflow steps for one intent | Ports only |
| **Inbound port** | Contract for *what the application can do* (a command/query/use-case interface) | — |
| **Outbound port** | Contract for *what the application needs* (repository, gateway, publisher, clock, id-generator) | — |
| **Adapter** | Concrete implementation at an edge — HTTP controller, DB repository, queue consumer, SDK wrapper | Frameworks, drivers, protocols |
| **Composition root** | The single place that instantiates adapters and injects them into use cases | Everything, by design |

Outbound port *interfaces* belong to the application layer (or the domain, only
when the abstraction is genuinely domain-level). The *implementations* live in
infrastructure. That split is what lets you test the core with fakes and swap
the edge without touching the middle.

## How to build one

1. **Draw a use-case boundary.** Pick one intent. Give it an explicit input DTO
   and output DTO built from plain data — no transport wrappers (`req`, GraphQL
   `context`, job envelopes) cross this line.
2. **Name the side effects as outbound ports first.** Every persistence call,
   external request, and cross-cutting dependency (clock, id-generator, logger)
   becomes a port. Model *capabilities*, not technologies: `StockRepository`,
   not `PostgresStockTable`.
3. **Write the use case as pure orchestration.** It receives its ports via
   constructor/arguments, checks application-level invariants, coordinates the
   domain, and returns plain data. No mapping, no protocol, no SQL.
4. **Build adapters at the edge.** An inbound adapter translates protocol input
   into the use-case input DTO and the output back to the protocol. An outbound
   adapter maps the port contract onto a concrete API/ORM/query. Mapping lives
   in adapters — never leaks inward.
5. **Wire it in one composition root.** Instantiate adapters, inject them into
   use cases, in a single auditable module. Centralised wiring is what keeps
   hidden service-locators and global singletons out of the core.
6. **Test per boundary** (see the test section below).

## Dependency flow

```text
Client (HTTP / CLI / Worker)
        │  calls
        ▼
Inbound Adapter ──▶ Use Case (application) ──▶ Domain Model
                        │ depends on
                        ▼
                   Outbound Port (interface)
                        ▲ implements
                        │
Outbound Adapter ──▶ DB / External API / Queue
```

Read the arrows: adapters know the application; the application knows only its
ports and the domain; the domain knows nothing outside itself.

## Suggested module layout (feature-first)

Organise by feature, then by boundary — not by technical layer at the top:

```text
src/features/reservations/
  domain/                 # Reservation, ReservationPolicy  (pure rules)
  application/
    ports/
      inbound/            # ReserveStock (use-case contract)
      outbound/           # StockRepository, EventPublisher, Clock
    use-cases/            # ReserveStockUseCase
  adapters/
    inbound/http/         # reserveStockRoute
    outbound/
      sql/                # SqlStockRepository
      broker/             # BrokerEventPublisher
  composition/            # reservationsContainer  (the wiring)
```

## Worked example (Python, stdlib-typed)

The language is incidental — the boundaries are the point. Ports are protocols;
the use case depends only on them; adapters live elsewhere and implement them.

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Protocol

# ---- domain (pure rules, no imports outward) ----
@dataclass(frozen=True)
class Reservation:
    sku: str
    quantity: int
    confirmation_id: Optional[str] = None

    @staticmethod
    def open(sku: str, quantity: int) -> "Reservation":
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        return Reservation(sku=sku, quantity=quantity)

    def confirm(self, confirmation_id: str) -> "Reservation":
        # returns a NEW value; never mutates in place
        return Reservation(self.sku, self.quantity, confirmation_id)

# ---- outbound ports (contracts the app needs) ----
class StockRepository(Protocol):
    def available(self, sku: str) -> int: ...
    def save(self, reservation: Reservation) -> None: ...

class ConfirmationIds(Protocol):
    def next(self) -> str: ...

# ---- inbound DTOs ----
@dataclass(frozen=True)
class ReserveStockInput:
    sku: str
    quantity: int

@dataclass(frozen=True)
class ReserveStockOutput:
    sku: str
    confirmation_id: str

# ---- use case: pure orchestration over ports ----
class ReserveStockUseCase:
    def __init__(self, stock: StockRepository, ids: ConfirmationIds) -> None:
        self._stock = stock
        self._ids = ids

    def execute(self, cmd: ReserveStockInput) -> ReserveStockOutput:
        reservation = Reservation.open(cmd.sku, cmd.quantity)
        if self._stock.available(cmd.sku) < reservation.quantity:
            raise ValueError("insufficient stock")   # application-level invariant
        confirmed = reservation.confirm(self._ids.next())
        self._stock.save(confirmed)
        return ReserveStockOutput(sku=confirmed.sku,
                                  # confirm() returns a Reservation whose
                                  # confirmation_id is guaranteed non-None;
                                  # the checker cannot see that invariant.
                                  confirmation_id=confirmed.confirmation_id)  # type: ignore[arg-type]
```

The outbound adapter (`SqlStockRepository`) implements `StockRepository` against
a real driver and does all row-mapping; the inbound adapter (an HTTP route)
parses the request into `ReserveStockInput` and serialises `ReserveStockOutput`.
The composition root is the only code that names both concretes:

```python
def build_reserve_stock(deps) -> ReserveStockUseCase:
    return ReserveStockUseCase(
        stock=SqlStockRepository(deps.db),
        ids=UuidConfirmationIds(),
    )
```

Swap `SqlStockRepository` for an in-memory fake in a test, or for a different
store in production — the use case and domain do not change a line.

## Same rules, other ecosystems

Only syntax and wiring style change; the boundary rules are invariant.

- **TypeScript / JavaScript** — ports as `interface`/`type` in
  `application/ports/*`; use cases as classes/functions with
  constructor/argument injection; adapters split `inbound/` vs `outbound/`;
  composition as an explicit factory/container module (no hidden globals).
- **Java** — packages `domain`, `application.port.in`, `application.port.out`,
  `application.usecase`, `adapter.in`, `adapter.out`; ports as interfaces;
  use cases as plain classes (a DI annotation is optional, not required);
  wiring in a config/manual class, kept out of domain and use-case code.
- **Kotlin** — mirror the Java split; ports as interfaces; use cases with
  constructor injection (Koin/Dagger/Spring/manual); composition as module
  definitions or dedicated wiring functions — avoid service locators.
- **Go** — packages `internal/<feature>/{domain,application,ports,adapters}`;
  ports as small interfaces owned by the *consuming* application package; use
  cases as structs with interface fields plus explicit `New…` constructors;
  wire in `cmd/<app>/main.go` or a dedicated wiring package.

## Testing, by boundary

- **Domain tests** — exercise entities/value objects as pure rules. No mocks,
  no framework bootstrap.
- **Use-case unit tests** — drive orchestration with in-memory fakes for the
  outbound ports; assert business outcomes *and* the port interactions.
- **Outbound adapter contract tests** — write one shared contract suite at the
  port level and run it against every adapter implementing that port.
- **Inbound adapter tests** — verify protocol mapping in both directions
  (payload → use-case input, and output/error → protocol response).
- **Adapter integration tests** — run against real infrastructure for
  serialisation, schema/query behaviour, retries, and timeouts.
- **End-to-end tests** — cover the critical journeys through inbound adapter →
  use case → outbound adapter.
- **Refactor safety** — add characterization tests *before* extraction; keep
  them until the new boundary is proven behaviour-equivalent.

## Migrating a tangled service (strangler, not rewrite)

1. Pick one vertical slice — a single endpoint or job — with frequent change pain.
2. Extract a use-case boundary with explicit input/output types.
3. Introduce outbound ports around the existing infrastructure calls.
4. Move orchestration out of the controller/service into the use case.
5. Keep the old adapter, but make it *delegate* to the new use case.
6. Add tests around the new boundary (unit + adapter integration).
7. Repeat slice by slice. Never a big-bang rewrite.

Supporting tactics: wrap legacy internals behind an outbound port *before*
replacing them (facade first); centralise wiring early so new dependencies
cannot leak inward (composition freeze); prioritise high-churn, low-blast-radius
flows first; keep a reversible route/toggle per migrated slice until production
behaviour is verified.

## Anti-patterns

- Domain entities importing ORM models, web-framework types, or SDK clients.
- Use cases reading straight from `req`/`res` or queue metadata.
- Returning raw database rows from a use case with no domain/application mapping.
- Adapters calling each other directly instead of flowing through use-case ports.
- Wiring scattered across many files behind hidden global singletons.

## Checklist

- Domain and use-case layers import only internal types and ports.
- Every external dependency is a named outbound port.
- Validation happens at boundaries: inbound adapter *and* use-case invariants.
- Transformations are immutable — return new values, don't mutate shared state.
- Errors are translated across boundaries (infra error → application/domain error).
- The composition root is explicit and auditable in one place.
- Use cases run under simple in-memory fakes for every port.
- Refactors start from one vertical slice with behaviour-preserving tests.
- Language and framework specifics stay in adapters, never in domain rules.

## Changelog

- **1.0.0** — Initial authored version. Ports & Adapters boundary discipline,
  inward dependency rule, six-step build recipe, feature-first layout, a
  stdlib-typed Python worked example, cross-language mapping (TS/Java/Kotlin/Go),
  per-boundary test strategy, strangler migration playbook, anti-patterns, and
  checklist.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=51961d215977506006df1a0b3bc2543531046e9b1f8a2646ada07688b49e7934
