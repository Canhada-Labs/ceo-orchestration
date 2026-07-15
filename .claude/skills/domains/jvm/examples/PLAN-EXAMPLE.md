---
id: PLAN-EXAMPLE-jvm
title: Add idempotent order creation to the checkout service
status: draft
created: 2026-07-13
owner: CEO
sprint: example
tags: [jvm, spring-boot, api-design, example]
---

# PLAN-EXAMPLE — Idempotent order creation on the checkout service

> Example plan demonstrating how the jvm squad routes a new endpoint
> through its three-VETO process (API contract, data path, test
> coverage). Not for execution. Used by adopters as a reference
> template when proposing a real endpoint change.

## 0. Thesis

Add `POST /api/orders` to the Spring Boot checkout service with
idempotent creation keyed on a client-supplied `Idempotency-Key`
header. Retried submissions (mobile clients on flaky networks) must
not create duplicate orders. The change touches all three squad
skills: a new public contract (`springboot-patterns`), a new table +
unique constraint and a transactional insert path
(`java-coding-standards`, Persistence section), and a full pyramid of
tests including a concurrency race check (`jvm-testing`).

This plan exists to demonstrate the squad's endpoint process
end-to-end.

## 1. Phases + owners

| Phase | Owner | Approver | Output |
|---|---|---|---|
| 1. API contract | Priya Raghunathan (Service & API Architect) | self (VETO) | Contract sketch + DTOs |
| 2. Data path + migration | Tomasz Zieliński (Language & Persistence Steward) | self (VETO) | Reversible migration + fetch plan |
| 3. Test pyramid | Kofi Mensah-Addo (Test & Release Engineer) | self (VETO) | Green suite incl. race test |
| 4. Production readiness | Marta Krüger (Production Reliability Engineer) | Priya Raghunathan | Timeouts + dashboard panel |
| 5. Release | Beatriz Fontoura (Head of JVM Platform) | Owner (CEO) | Merged PR with 3 VETO sign-offs |

## 2. Phase 1 — API contract

**Owner:** Priya Raghunathan

- Define request/response records with Bean Validation:
  `CreateOrderRequest(@NotEmpty List<@Valid OrderLine> lines, ...)`,
  `OrderResponse(UUID id, OrderStatus status, Instant createdAt)`.
- Semantics: first submission with a given `Idempotency-Key` returns
  `201 Created`; a retry with the same key and same payload returns
  `200 OK` with the original body; same key with a *different* payload
  returns `409 Conflict` (RFC 7807 problem detail).
- Missing `Idempotency-Key` header → `400` with a problem detail
  naming the header.
- No entity crosses the controller boundary; errors flow through the
  existing `@RestControllerAdvice`.

**Acceptance:** Contract sketch (DTO records + status table) attached
to the PR description; no breaking change to existing order-read
endpoints.

## 3. Phase 2 — Data path + migration

**Owner:** Tomasz Zieliński

- Flyway migration `V27__orders_idempotency.sql`: new
  `order_idempotency` table `(key text primary key, order_id uuid not
  null references orders(id), request_hash text not null, created_at
  timestamptz not null)`. Purely additive — reversible by dropping the
  table in a later, separate migration once unused.
- Insert path: service method `@Transactional` — insert the
  idempotency row and the order in one transaction; rely on the
  primary-key constraint to lose the race, catch the constraint
  violation, and re-read the winner's order. No remote I/O inside the
  transaction (payment notification moves to an after-commit outbox).
- `request_hash` compares retried payloads to detect the `409` case.
- Read path for the retry hit uses a DTO projection (no entity graph
  needed) — fetch plan stated in the PR.

**Acceptance:** Migration reviewed reversible and additive; Hibernate
SQL logging on the new path shows exactly the expected statements (no
N+1); constraint-race behavior documented in the service Javadoc.

## 4. Phase 3 — Test pyramid

**Owner:** Kofi Mensah-Addo

- Unit (JUnit 5 + Mockito): hash comparison logic, conflict
  classification, after-commit outbox handoff.
- Slice `@WebMvcTest`: `201` happy path, `200` retry, `409` mismatch,
  `400` missing header — all four statuses asserted with problem-
  detail bodies.
- Slice `@DataJpaTest` + Testcontainers (Postgres 16, `Replace.NONE`):
  constraint violation on duplicate key; projection query shape.
- Integration `@SpringBootTest` + Testcontainers: two concurrent
  submissions with the same key (`CompletableFuture` pair, no sleeps —
  latch-synchronized start) produce exactly one order row; loser
  receives the winner's response.
- All new tests parallel-safe: unique idempotency keys per test via
  the test-data builder; shared static container.

**Acceptance:** CI green; failing paths covered at every layer; the
concurrency test passes a 50-run local soak.

## 5. Phase 4 — Production readiness

**Owner:** Marta Krüger

- Outbox dispatcher (new outbound call) gets an explicit timeout and
  bounded retry with backoff; interrupt flag restored on backoff
  interruption.
- Metrics: counter `orders_idempotent_hits_total` (tags: outcome =
  created|replayed|conflict); existing latency histogram extended to
  the new endpoint.
- Structured logs carry the idempotency key (opaque, non-PII) for
  support traceability.
- Pool impact reviewed: one extra insert per order — no HikariCP
  change; connection-wait metric watched for one week post-release.

**Acceptance:** Timeout/retry table + dashboard panel linked in the
PR; no PII in the new log fields.

## 6. Phase 5 — Release

**Owner:** Beatriz Fontoura

- Confirm the three VETO sign-offs (Phases 1–3) and the reliability
  review (Phase 4) are recorded on the PR.
- No new dependency added (outbox uses the existing scheduler) — no
  EOL/CVE delta.
- Merge; monitor the `conflict` outcome rate for the first week — a
  non-trivial rate means a client is misusing the key and gets a
  partner-facing note, not a server-side workaround.

**Acceptance:** PR merged with all approvals recorded; week-one
monitoring note filed.

## 7. Open questions

1. Key retention: purge `order_idempotency` rows after 30 days, or
   keep indefinitely for audit? (Steward + Reliability to propose.)
2. Should the `409` payload include the original request hash to help
   partners debug, or is that an information leak? (Architect call.)
3. Quarkus checkout-adjacent services: adopt the same header contract
   now or when they next touch orders?

## 8. Rollback

- The endpoint is new — rollback is redeploying the previous release.
  The migration is additive, so the schema needs no rollback; the
  unused table is dropped by a later cleanup migration only after the
  code release is confirmed stable.
- If the constraint-race handling misbehaves under load, the endpoint
  can be disabled at the gateway while the fix ships; existing order
  paths are untouched.
