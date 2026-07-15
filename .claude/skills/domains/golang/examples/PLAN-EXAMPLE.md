---
id: PLAN-EXAMPLE-golang
title: Ship the "inventory-sync" Go service through the squad's four gates
status: draft
created: 2026-07-13
owner: CEO
sprint: example
tags: [golang, service-launch, example]
---

# PLAN-EXAMPLE — Ship the inventory-sync Go service

> Example plan demonstrating how the golang squad routes a new service
> through its three-VETO process. Not for execution. Used by adopters
> as a reference template when proposing a real Go service.

## 0. Thesis

Build `inventory-sync`, a Go service that consumes stock-level events
from a message queue, reconciles them against the catalog database
through a bounded worker pool, and exposes a small JSON API
(`GET /v1/stock/{sku}`, `GET /healthz`, `GET /readyz`). It replaces a
cron-based batch reconciler whose 15-minute staleness window causes
oversells.

This plan exists to demonstrate the squad's launch process end-to-end:
`golang-patterns` governs the implementation, `golang-testing` governs
the suite, `golang-services` governs the wiring, and the chain
`golang-ship-new-service` sequences the gates.

## 1. Phases + owners

| Phase | Owner | Approver | Output |
|---|---|---|---|
| 1. Skeleton + dependency budget | Renata Villaça (Head of Go Platform) | Renata Villaça | Approved layout + annotated go.mod |
| 2. Implementation | Tomasz Zieliński (Concurrency & Correctness Reviewer) | self (VETO) | Reviewed service code, vet/staticcheck clean |
| 3. Test suite | Priya Raghunathan (Testing & CI Gate Engineer) | self (VETO) | Race-clean CI lane + integration harness |
| 4. Reliability wiring | Callum McBride (Service Reliability Engineer) | self (VETO) | Shutdown drill log + probe documentation |
| 5. Deploy + canary | Renata Villaça (Head of Go Platform) | Owner (CEO) | 3 sign-offs + canary report |

## 2. Phase 1 — Skeleton + dependency budget

**Owner:** Renata Villaça

- Standard layout: `cmd/inventory-sync/main.go` (wiring only),
  `internal/handler/` (HTTP), `internal/service/` (reconciliation
  logic), `internal/store/` (catalog DB access), `internal/queue/`
  (consumer).
- Dependency budget: stdlib `net/http` for the API (no router
  framework — two routes), `golang.org/x/sync/errgroup` for the
  worker pool, one queue client, one DB driver. Each entry in
  `go.mod` annotated with its justification in the PR description.
- golangci-lint config inherited from the platform baseline
  (errcheck, govet, staticcheck, unused, ineffassign).

**Acceptance:** Skeleton PR approved; `go mod tidy` produces no diff;
no dependency present without a written justification.

## 3. Phase 2 — Implementation

**Owner:** Tomasz Zieliński

- Worker pool: fixed N workers draining a jobs channel; producer
  closes the channel on queue shutdown; `errgroup.WithContext` ties
  workers to one context so the first failure cancels the rest.
- Every goroutine's stop path documented in a one-line comment at
  the spawn site (who closes/cancels, and when).
- `ctx` first parameter on every store/queue/HTTP call; per-event
  processing deadline derived with `context.WithTimeout`.
- Errors wrapped with `%w` at each layer boundary
  (`reconcile sku %q: %w`); store returns sentinel
  `ErrSKUNotFound`; handler branches with `errors.Is`.
- No package-level mutable state: DB pool, queue client, and
  `slog.Logger` injected through struct fields built in `main()`.

**Acceptance:** `go vet ./...` and `staticcheck ./...` clean; review
checklist attached with zero open VETO triggers (GO-001..GO-006).

## 4. Phase 3 — Test suite

**Owner:** Priya Raghunathan

- Table-driven unit tests on reconciliation logic (happy path,
  stale event, unknown SKU, conflicting concurrent updates), each
  case a named subtest, `t.Parallel` where no state is shared.
- Handler tests via `httptest`: status codes, JSON shape, and the
  404-on-`ErrSKUNotFound` branch.
- Integration tests behind `//go:build integration`: real Postgres
  via testcontainers-go, exercising the store against actual SQL.
- Concurrency tests: cancellation mid-batch drains workers without
  leaking (goroutine count asserted with bounded polling — no
  `time.Sleep` synchronization anywhere in the suite).
- CI: `go test -race ./...` on the merge-gating lane; integration
  lane runs the tagged tests on a schedule + pre-deploy.

**Acceptance:** Merge lane green WITH `-race`; integration lane green
against a real Postgres container; zero sleeps in the suite
(`grep -rn "time.Sleep" --include='*_test.go'` returns only
explicitly-commented fake-clock cases, ideally none).

## 5. Phase 4 — Reliability wiring

**Owner:** Callum McBride

- `http.Server` with all four timeouts set (ReadHeaderTimeout 5s,
  ReadTimeout 10s, WriteTimeout 10s, IdleTimeout 60s).
- Outbound: DB pool with `SetConnMaxLifetime`/`SetMaxOpenConns`;
  queue client with a per-poll deadline.
- Graceful shutdown: SIGTERM → stop queue consumer → drain worker
  pool → `srv.Shutdown` under a 20s context (platform grace is
  30s) → flush OTel exporters → exit 0.
- Probes: `/healthz` liveness (process only), `/readyz` readiness
  (DB ping + queue connection), documented in the runbook.
- `slog` JSON logs with request IDs; a redaction test proves event
  payloads are logged as SKU + counts only, never full bodies.
- OTel traces on ingress (HTTP) and egress (DB, queue).

**Acceptance:** Shutdown drill log attached: under synthetic load,
SIGTERM completes all in-flight requests and exits within the grace
window with zero 5xx from dropped connections.

## 6. Phase 5 — Deploy + canary

**Owner:** Renata Villaça

- Go/no-go review across the three VETO sign-offs.
- Canary at 5% traffic for 24h: goroutine count flat, p99 within
  budget, zero race-detector findings in the canary's `-race`
  built variant (canary only; production build is race-off).
- Rollback path: previous image + config documented in the deploy
  ticket; the old cron reconciler stays enabled until the 24h
  canary passes.

**Acceptance:** Canary report filed; cron reconciler decommission
ticket created only after 7 clean days.

## 7. Open questions

1. Should the worker-pool size be configurable at runtime (SIGHUP
   reload) or fixed per deploy? Reliability preference: fixed —
   fewer moving parts.
2. Does the queue client's built-in retry interact safely with our
   per-event deadline, or do we need to disable one layer?
3. When the catalog DB is degraded, should `/readyz` flip within
   one probe period or dampen over three (thundering-herd trade-off)?

## 8. Rollback

- Deploy rollback: previous image + config, one command, documented
  in the ticket. The old cron reconciler remains as a warm fallback
  for the first week.
- Data rollback: reconciliation is idempotent (last-write-wins on
  event timestamps), so replaying the queue from the last checkpoint
  after rollback restores consistency without manual repair.
