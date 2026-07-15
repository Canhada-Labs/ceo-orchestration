---
name: golang-services
description: >
  Production Go service patterns: the wiring that turns a correct package
  into a service that survives deploys, load, and 3 a.m. incidents. Covers
  the hardened net/http server shape (all four timeouts, no default
  client/server), middleware chains, graceful shutdown under SIGTERM with
  bounded drain, timeouts at every boundary (inbound, outbound, database),
  gRPC and JSON API structure, config and env wiring read once in main,
  structured logging with slog (request IDs, no secrets), liveness versus
  readiness probe semantics, OpenTelemetry traces and metrics on ingress
  and egress, and the standard service repo layout. Complements
  golang-patterns (code discipline) and golang-testing (proof): this skill
  owns the boundary between the binary and production. Use when scaffolding
  a Go service, wiring main.go, adding middleware or probes, setting any
  timeout, or reviewing service deployment readiness.
metadata:
  activation_triggers:
    - "scaffolding a new Go HTTP, gRPC, or worker service"
    - "wiring main.go: config, logger, server, shutdown"
    - "adding or reviewing middleware, health probes, or timeouts"
    - "setting up structured logging (slog) or OpenTelemetry"
    - "reviewing a Go service for deployment readiness"
    - "diagnosing dropped requests during deploys or restarts"
  paths:
    - "**/cmd/**/*.go"
    - "**/main.go"
    - "**/internal/handler/**"
    - "**/go.mod"
version: 1.0.0
risk_class: low
---

# Go Services

A Go service is a package with opinions about production attached. The
package logic follows `golang-patterns`; this skill owns everything at
the boundary: how the process starts, how it accepts and makes
requests, how it reports its health, what it logs, and — most
neglected — how it stops. The recurring theme: **every boundary gets a
deadline.** Go's zero values for timeouts mean *infinite*, and every
infinite timeout in production is an incident with a delay on it.

## When to Activate

Activate this skill for any of the following:

- Scaffolding a new Go service (HTTP, gRPC, or queue worker).
- Writing or reviewing `main.go` — config, wiring, lifecycle.
- Adding middleware, health endpoints, logging, or tracing.
- Setting or reviewing any timeout, anywhere.
- Diagnosing dropped requests during deploys, restarts, or overload.

## Server Shape

Never ship `http.ListenAndServe(addr, h)` — it uses a server with no
timeouts, which holds slow-client connections forever (Slowloris) and
lets one stuck handler pin a connection indefinitely. Construct the
server explicitly:

```go
srv := &http.Server{
    Addr:              ":8080",
    Handler:           mux,
    ReadHeaderTimeout: 5 * time.Second,  // Slowloris guard
    ReadTimeout:       10 * time.Second, // full request read
    WriteTimeout:      10 * time.Second, // handler + response write
    IdleTimeout:       60 * time.Second, // keep-alive reaping
}
```

Routing: the stdlib `http.ServeMux` (with Go 1.22+ method and wildcard
patterns: `mux.HandleFunc("GET /v1/stock/{sku}", h.stock)`) covers
most services. Reach for a router module only when you need something
it cannot do — middleware ecosystems are not a reason; middleware is
ten lines.

Handlers hang off a struct that carries injected dependencies — never
package globals:

```go
type Handler struct {
    store Store
    log   *slog.Logger
}

func (h *Handler) stock(w http.ResponseWriter, r *http.Request) {
    sku := r.PathValue("sku")
    n, err := h.store.Stock(r.Context(), sku)
    switch {
    case errors.Is(err, ErrSKUNotFound):
        http.Error(w, "unknown sku", http.StatusNotFound)
    case err != nil:
        h.log.ErrorContext(r.Context(), "stock lookup", "sku", sku, "err", err)
        http.Error(w, "internal error", http.StatusInternalServerError)
    default:
        writeJSON(w, http.StatusOK, stockResponse{SKU: sku, Count: n})
    }
}
```

Error responses never leak internals: log the wrapped error with
context, return a generic message and the right status code.

## Middleware Chains

Middleware is a function from `http.Handler` to `http.Handler`.
Compose explicitly — order is semantics:

```go
func chain(h http.Handler, mws ...func(http.Handler) http.Handler) http.Handler {
    for i := len(mws) - 1; i >= 0; i-- {
        h = mws[i](h)
    }
    return h
}

// Outermost first: recovery sees everything, auth runs before handlers.
handler := chain(mux, recoverPanic(log), requestID, logRequests(log), authenticate(keys))
```

The canonical set for a JSON API: panic recovery (log + 500, never let
one request kill the process), request-ID injection (generate if
absent, stamp response header and log fields), request logging
(method, path, status, duration — **never bodies**), auth. Each is a
dozen lines; resist importing a framework for them.

```go
func requestID(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        id := r.Header.Get("X-Request-Id")
        if id == "" {
            id = newID()
        }
        w.Header().Set("X-Request-Id", id)
        next.ServeHTTP(w, r.WithContext(withRequestID(r.Context(), id)))
    })
}
```

## Graceful Shutdown

The orchestrator sends SIGTERM, waits a grace period, then SIGKILLs.
Everything between those two signals is your responsibility. The
drain sequence: stop accepting new work, finish in-flight work under
a deadline *shorter than the grace period*, flush telemetry, exit.

```go
func run(ctx context.Context, srv *http.Server, log *slog.Logger) error {
    ctx, stop := signal.NotifyContext(ctx, syscall.SIGINT, syscall.SIGTERM)
    defer stop()

    errc := make(chan error, 1)
    go func() { errc <- srv.ListenAndServe() }()

    select {
    case err := <-errc:
        return fmt.Errorf("server: %w", err) // crashed on its own
    case <-ctx.Done():
        log.Info("shutdown: draining")
        // Grace period is 30s platform-side; drain in 20s, leave margin
        // for telemetry flush + exit.
        drainCtx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
        defer cancel()
        return srv.Shutdown(drainCtx)
    }
}
```

Ordering rules for multi-component services (HTTP + queue consumer +
worker pool): stop *intake* first (consumer), drain *workers* second,
shut the *HTTP server* down alongside, flush exporters last. Readiness
must flip to unready as draining begins so the load balancer stops
routing — `Shutdown` handles in-flight requests, but only readiness
stops new ones from arriving during propagation delay.

## Timeouts at Every Boundary

Inbound timeouts (the server block above) protect you from clients.
Outbound timeouts protect you from dependencies:

```go
// Never http.DefaultClient — its Timeout is zero (infinite).
client := &http.Client{Timeout: 5 * time.Second}

// Database pools: bound connections and their lifetimes.
db.SetMaxOpenConns(25)
db.SetMaxIdleConns(25)
db.SetConnMaxLifetime(5 * time.Minute)

// Per-call deadlines derive from the request context, so one slow
// dependency cannot outlive the request that asked for it.
ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
defer cancel()
row := db.QueryRowContext(ctx, query, sku)
```

Audit for **zeros, not absences**: a constructed-but-unset field is
the same infinite timeout as a missing one. Retries wrap timeouts,
never replace them — and retries need a budget (max attempts + backoff
+ only on idempotent operations), or a degraded dependency turns your
service into its own DDoS.

## Config and Env Wiring

Configuration is read **once, in `main`**, validated, and passed down
as a plain struct. Packages never read `os.Getenv` themselves — that
is package-level hidden state with extra steps.

```go
type Config struct {
    Addr         string
    DatabaseURL  string
    DrainTimeout time.Duration
}

func loadConfig() (Config, error) {
    cfg := Config{
        Addr:         envOr("ADDR", ":8080"),
        DatabaseURL:  os.Getenv("DATABASE_URL"),
        DrainTimeout: 20 * time.Second,
    }
    if cfg.DatabaseURL == "" {
        return Config{}, errors.New("DATABASE_URL is required")
    }
    return cfg, nil
}
```

Fail fast at startup on invalid config — a service that boots with a
bad config and fails on the first request passed its deploy check and
lied. Secrets arrive via env or mounted files from the platform's
secret store; they never appear in flags (visible in `ps`), logs, or
error messages.

## Structured Logging with slog

`log/slog` is the standard: JSON handler in production, key-value
fields, levels used sparingly.

```go
log := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))

log.InfoContext(ctx, "reconcile complete",
    "sku", sku,
    "count", n,
    "duration_ms", time.Since(start).Milliseconds(),
)
```

- Carry the request ID into every log line via a context-aware
  handler or explicit field — correlation is the whole point.
- **Never log secrets, tokens, or full request/response bodies** at
  any level, including debug. Log identifiers and sizes, not payloads.
- ERROR means a human should eventually look; WARN means degraded but
  handled; INFO is state transitions, not per-item chatter inside
  loops (that's a metric, not a log line).

## Health and Readiness

Two probes, two meanings — conflating them causes restart storms:

- **Liveness (`/healthz`)** answers "is this process wedged?" It
  checks the process only — no dependencies. If it fails, the
  orchestrator restarts the pod; a liveness probe that pings the
  database converts every DB blip into a fleet-wide restart loop.
- **Readiness (`/readyz`)** answers "should traffic route here?" It
  verifies dependencies (DB ping, queue connection) and flips to
  unready during startup warmup and shutdown drain. Failing readiness
  removes the pod from rotation without restarting it.

```go
mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
    w.WriteHeader(http.StatusOK) // process is up; that is the whole check
})
mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    if err := db.PingContext(ctx); err != nil {
        http.Error(w, "db unavailable", http.StatusServiceUnavailable)
        return
    }
    w.WriteHeader(http.StatusOK)
})
```

## Observability

Wire OpenTelemetry at the boundaries — ingress (HTTP/gRPC middleware)
and egress (instrumented HTTP client, DB wrapper) — so every request
produces a trace whose spans cross service boundaries via propagated
headers. The minimum metric set for any service: request rate, error
rate, duration histogram (RED), plus goroutine count and heap from the
runtime — a monotonically climbing goroutine count is the earliest
visible symptom of the leak class `golang-patterns` guards against.
Expose `/debug/pprof` on a **separate internal port**, never the
public listener.

## Service Repo Layout

```text
service/
├── cmd/inventory-sync/main.go   # wiring ONLY: config, deps, run()
├── internal/
│   ├── handler/                 # transport: HTTP/gRPC handlers, middleware
│   ├── service/                 # business logic (no transport imports)
│   └── store/                   # persistence behind an interface
├── go.mod
└── go.sum
```

`main.go` builds dependencies and calls a `run(ctx, cfg) error` that
is testable end-to-end; it contains no business logic. The dependency
arrow points inward: `handler → service → store`, and `service` never
imports `handler`. gRPC services follow the same shape with the
generated stubs in their own package and the same probe/shutdown/
timeout obligations (`grpc.Server.GracefulStop`, keepalive params,
health service registered).

## Anti-Patterns

| Anti-pattern | Why it hurts | Do instead |
|---|---|---|
| `http.ListenAndServe(addr, h)` | No timeouts: Slowloris, pinned connections | Explicit `http.Server` with all four timeouts |
| `http.DefaultClient` for outbound calls | Zero timeout = infinite hang on a sick dependency | Constructed client with `Timeout` or per-call ctx |
| Exiting on SIGTERM without draining | Drops in-flight requests on every deploy | `signal.NotifyContext` + `srv.Shutdown` under bounded ctx |
| Liveness probe checking dependencies | DB blip becomes a restart storm | Liveness = process only; readiness = dependencies |
| `os.Getenv` scattered through packages | Hidden config surface; untestable | Read once in `main`, pass a Config struct |
| Logging request bodies or tokens | Secret leakage into log storage | Log IDs, sizes, durations — never payloads |
| Per-request `fmt.Println` debugging left in | Unstructured noise; no correlation | `slog` with request-ID field |
| pprof on the public listener | Debug surface exposed to the internet | Separate internal port |
| Retries without a budget on non-idempotent calls | Amplifies outages; duplicates writes | Bounded retries + backoff, idempotent ops only |
| Business logic in `main.go` | Untestable wiring/logic tangle | `run()` + internal packages |

**Bottom line:** the package makes the service correct; the boundary
makes it survivable. Set every timeout, drain every shutdown, split
the probes, and log like the transcript will be read during an
incident — because it will.

## Changelog

- **1.0.0** — Initial release. Hardened server shape, middleware
  chains, graceful shutdown ordering, boundary timeouts (inbound,
  outbound, DB), config wiring, slog discipline, liveness/readiness
  semantics, OpenTelemetry boundaries, service repo layout, and an
  anti-patterns table.
