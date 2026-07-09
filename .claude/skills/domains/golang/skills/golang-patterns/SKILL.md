---
name: golang-patterns
description: >
  Idiomatic Go engineering discipline: writing, reviewing, and refactoring
  Go so it stays boring, predictable, and easy to maintain. Covers the core
  Go proverbs (clear over clever, accept interfaces return structs, useful
  zero values), error-handling contracts (wrap with %w, sentinel + typed
  errors, errors.Is / errors.As, never silently drop), concurrency safety
  (worker pools, context-driven cancellation and timeout, errgroup,
  goroutine-leak avoidance, graceful shutdown), interface and package
  design (small consumer-side interfaces, no package-level mutable state,
  dependency injection), struct ergonomics (functional options, embedding),
  allocation-aware performance (preallocation, strings.Builder, sync.Pool),
  and the standard tooling gate (go vet, staticcheck, golangci-lint, race
  detector, gofmt/goimports). Use when authoring a new .go file, reviewing
  a Go pull request, designing a package or module boundary, wiring
  goroutines and channels, shaping an error path, or picking a lint gate.
metadata:
  activation_triggers:
    - "editing or creating a *.go file"
    - "editing go.mod or go.sum"
    - "designing a Go package, module, or interface boundary"
    - "reviewing or refactoring Go code"
    - "wiring goroutines, channels, context, or sync primitives"
    - "shaping a Go error path (wrapping, sentinel, typed errors)"
    - "choosing or configuring a Go lint/static-analysis gate"
  paths:
    - "**/*.go"
    - "**/go.mod"
    - "**/go.sum"
    - "**/.golangci.yml"
    - "**/.golangci.yaml"
version: 1.0.0
risk_class: low
source: affaan-m/ecc@81af4076 skills/golang-patterns/
license: MIT
---

# Go Patterns

Idiomatic Go for code that a reviewer can understand on the first read and
that behaves the same way at 3 a.m. under load as it did in review. The
governing bias is toward the obvious solution: Go rewards code that is
plain over code that is clever.

## When to Activate

Activate this skill for any of the following:

- Authoring a new `.go` file or a new package.
- Reviewing a Go pull request (structure pass and adversarial pass alike).
- Refactoring existing Go — especially error paths and goroutine wiring.
- Designing a package, module, or interface boundary.
- Introducing or tuning a lint / static-analysis gate.

## Guiding Principles

### Clear beats clever

Optimize for the reader, not the author. If a function needs a comment to
explain *what* it does (as opposed to *why*), it is usually too clever.
Return early, keep the happy path un-indented, and let error branches exit.

```go
// Prefer: linear, early-return, one obvious path.
func openLedger(path string) (*Ledger, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("open ledger %q: %w", path, err)
    }
    defer f.Close()
    return parseLedger(f)
}
```

### Make the zero value useful

Design a type so that a freshly declared `var x T` is already usable. This
removes an entire class of "forgot to call New" bugs. The stdlib is the
model: `var mu sync.Mutex`, `var buf bytes.Buffer`, and `var wg
sync.WaitGroup` all work with no constructor.

```go
// Useful zero value: an unlocked mutex and a zero count are ready to go.
type Meter struct {
    mu    sync.Mutex
    count int64
}

func (m *Meter) Tick() {
    m.mu.Lock()
    m.count++
    m.mu.Unlock()
}
```

The trap is a struct whose zero value contains a nil map or nil channel
that the methods then write to — that panics. If a field must be
initialized before use, give the type a constructor and document that the
zero value is not valid.

### Accept interfaces, return concrete types

Take the narrowest interface you actually use as a parameter; return the
concrete type you built. Returning an interface hides fields and methods
the caller may legitimately need, and forces speculative abstraction on
the provider side.

```go
// Accepts any source of bytes; hands back a concrete, fully-featured value.
func Load(src io.Reader) (*Report, error) {
    raw, err := io.ReadAll(src)
    if err != nil {
        return nil, fmt.Errorf("read report: %w", err)
    }
    return &Report{payload: raw}, nil
}
```

## Error Handling

Errors are ordinary values in Go, not exceptions. Handle them where they
occur, add context as they travel up, and never let one vanish silently.

### Wrap with context using %w

Wrap at each boundary the error crosses so the final message reads as a
trail. Use `%w` (not `%v`) so callers can still unwrap and inspect.

```go
func loadConfig(path string) (*Config, error) {
    raw, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("read config %q: %w", path, err)
    }
    var cfg Config
    if err := json.Unmarshal(raw, &cfg); err != nil {
        return nil, fmt.Errorf("decode config %q: %w", path, err)
    }
    return &cfg, nil
}
```

Wrap with lowercase, colon-separated context and no trailing punctuation,
so wrapped messages compose cleanly (`read config "x": decode config "x":
unexpected end of JSON input`).

### Sentinel errors and typed errors

Use a sentinel (`errors.New`) when callers only need to recognize a
condition. Use a typed error when callers need structured detail.

```go
var (
    ErrNotFound  = errors.New("not found")
    ErrConflict  = errors.New("conflict")
)

// Typed error carries fields the caller can branch on.
type FieldError struct {
    Field  string
    Reason string
}

func (e *FieldError) Error() string {
    return fmt.Sprintf("field %s: %s", e.Field, e.Reason)
}
```

### Inspect with errors.Is and errors.As

Never compare wrapped errors with `==` or match on `err.Error()` strings —
both break the moment someone adds a wrap. Use `errors.Is` for sentinels
and `errors.As` for typed errors.

```go
func classify(err error) string {
    if errors.Is(err, ErrNotFound) {
        return "404"
    }
    var fe *FieldError
    if errors.As(err, &fe) {
        return "422:" + fe.Field
    }
    return "500"
}
```

### Never drop an error silently

Discarding an error with `_` is a claim that failure is impossible or
irrelevant. That claim is almost always wrong. When an error genuinely
does not matter (best-effort cleanup), make the discard explicit and
comment why.

```go
// Deliberate best-effort close; the write already succeeded and was flushed.
_ = tmp.Close()
```

Everything else must be checked and either handled or returned.

## Concurrency

Concurrency in Go is cheap to start and expensive to get wrong. The rule
that prevents most incidents: every goroutine must have a defined way to
stop, and every channel operation must have a defined way not to block
forever. "Don't communicate by sharing memory; share memory by
communicating."

### Context for cancellation and deadlines

Pass `context.Context` as the first parameter of any function that does
I/O or can block. Derive a timeout for outbound calls and always `defer
cancel()` to release the timer.

```go
func fetch(ctx context.Context, url string) ([]byte, error) {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return nil, fmt.Errorf("build request: %w", err)
    }
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("get %s: %w", url, err)
    }
    defer resp.Body.Close()
    return io.ReadAll(resp.Body)
}
```

Context belongs in the call chain, never stored in a struct field.

### Worker pool

Bound concurrency with a fixed set of workers draining a jobs channel. The
producer closes `jobs`; workers exit when the range ends; a WaitGroup
gates the close of `results`.

```go
func run(jobs <-chan Job, results chan<- Result, workers int) {
    var wg sync.WaitGroup
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for j := range jobs { // exits when jobs is closed
                results <- handle(j)
            }
        }()
    }
    wg.Wait()
    close(results) // safe: all senders have returned
}
```

### errgroup for fan-out with a shared failure

When several goroutines must all succeed and the first failure should
cancel the rest, `golang.org/x/sync/errgroup` (an official extension
package, not stdlib) ties them to one context.

```go
func fetchAll(ctx context.Context, urls []string) ([][]byte, error) {
    g, ctx := errgroup.WithContext(ctx)
    out := make([][]byte, len(urls))
    for i, u := range urls {
        i, u := i, u // pin the loop variables (pre-Go 1.22 requirement)
        g.Go(func() error {
            b, err := fetch(ctx, u)
            if err != nil {
                return err // cancels ctx for the siblings
            }
            out[i] = b
            return nil
        })
    }
    if err := g.Wait(); err != nil {
        return nil, err
    }
    return out, nil
}
```

### Avoid goroutine leaks

A goroutine blocked forever on a send or receive is a leak that
accumulates until the process dies. Give a spawned goroutine a buffered
channel or a `select` on `ctx.Done()` so it can always make progress or
give up.

```go
// The buffer lets the goroutine finish even if no one is left to receive;
// the select lets it abandon the send when the caller has moved on.
func result(ctx context.Context, q Query) <-chan Row {
    ch := make(chan Row, 1)
    go func() {
        row, err := query(q)
        if err != nil {
            return
        }
        select {
        case ch <- row:
        case <-ctx.Done():
        }
    }()
    return ch
}
```

### Graceful shutdown

A long-lived server should drain in-flight work on SIGINT/SIGTERM rather
than dropping connections. Trap the signal, then `Shutdown` under a bounded
context.

```go
func serve(srv *http.Server) error {
    stop := make(chan os.Signal, 1)
    signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

    errc := make(chan error, 1)
    go func() { errc <- srv.ListenAndServe() }()

    select {
    case err := <-errc:
        return err
    case <-stop:
        ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()
        return srv.Shutdown(ctx)
    }
}
```

Always run tests and CI for concurrent code with `-race`; the detector
catches data races that are invisible in normal runs.

## Interface and Package Design

### Keep interfaces small and define them at the consumer

An interface should name the behavior a caller needs, usually one to three
methods. Declare it in the package that *consumes* it, not the package that
implements it — that keeps the provider free of interfaces it does not use
and lets each consumer ask for exactly what it needs.

```go
package billing

// billing states the storage it needs; the concrete store lives elsewhere
// and never imports this interface.
type accountStore interface {
    Account(ctx context.Context, id string) (*Account, error)
    Save(ctx context.Context, a *Account) error
}

type Service struct{ store accountStore }

func NewService(s accountStore) *Service { return &Service{store: s} }
```

Compose small interfaces (`io.ReadWriteCloser` is three one-method
interfaces) rather than declaring wide ones up front.

### Discover optional behavior with a type assertion

When a value *might* support extra behavior, probe for it instead of
widening the required interface.

```go
func writeAll(w io.Writer, p []byte) error {
    if _, err := w.Write(p); err != nil {
        return err
    }
    if f, ok := w.(interface{ Flush() error }); ok {
        return f.Flush()
    }
    return nil
}
```

### Package layout and naming

Package names are short, lowercase, single words, and never stutter with
their exported identifiers (`http.Server`, not `http.HTTPServer`; avoid a
`user` package exporting `UserService`). A conventional layout:

```text
project/
├── cmd/app/main.go     # entry point; wiring only
├── internal/           # code no other module may import
│   ├── handler/        # transport (HTTP, gRPC)
│   ├── service/        # business logic
│   └── store/          # persistence
├── pkg/                # code intended for external import (use sparingly)
├── go.mod
└── go.sum
```

### No package-level mutable state; inject dependencies

A package-level `var db *sql.DB` populated in `init()` is untestable,
racy, and hides ordering requirements. Hold dependencies in a struct and
pass them in.

```go
// Injected: each test builds its own Server with a fake store.
type Server struct {
    store accountStore
    log   *slog.Logger
}

func NewServer(store accountStore, log *slog.Logger) *Server {
    return &Server{store: store, log: log}
}
```

## Struct Ergonomics

### Functional options for open-ended construction

When a constructor has more than a couple of optional knobs, variadic
option functions beat a growing parameter list or a config struct full of
zero values. Callers set only what they care about; defaults live in one
place.

```go
type Client struct {
    timeout time.Duration
    retries int
}

type Option func(*Client)

func WithTimeout(d time.Duration) Option { return func(c *Client) { c.timeout = d } }
func WithRetries(n int) Option           { return func(c *Client) { c.retries = n } }

func NewClient(opts ...Option) *Client {
    c := &Client{timeout: 10 * time.Second, retries: 3} // defaults
    for _, opt := range opts {
        opt(c)
    }
    return c
}

// NewClient(WithTimeout(30*time.Second))
```

### Embedding for composition

Embed a type to promote its methods onto the outer type. Prefer this over
building a parallel method set that just forwards calls — but embed only
when the promoted surface genuinely belongs to the outer type.

```go
type auditLog struct{ prefix string }

func (a auditLog) Event(msg string) { fmt.Printf("[%s] %s\n", a.prefix, msg) }

type Worker struct {
    auditLog // Worker.Event is promoted from the embedded auditLog
    id string
}
```

## Allocation-Aware Performance

Reach for these only where a profile (`pprof`) or a hot loop justifies it;
premature micro-optimization is its own anti-pattern. When it matters:

- **Preallocate slices and maps when the final size is known.** `make([]T,
  0, n)` avoids the log-n regrowth-and-copy cycle that `append` on a nil
  slice performs.

  ```go
  out := make([]Result, 0, len(items))
  for _, it := range items {
      out = append(out, process(it))
  }
  ```

- **Build strings with `strings.Builder`, not `+=` in a loop.** Each `+=`
  allocates a new backing string; `Builder` grows one buffer. For a simple
  join, `strings.Join` is clearer still.

  ```go
  var b strings.Builder
  for i, p := range parts {
      if i > 0 {
          b.WriteByte(',')
      }
      b.WriteString(p)
  }
  s := b.String()
  ```

- **Reuse short-lived buffers with `sync.Pool`** on genuinely hot paths.
  Always reset the object before returning it, and treat pooled contents as
  garbage on retrieval.

  ```go
  var bufPool = sync.Pool{New: func() any { return new(bytes.Buffer) }}

  func render(p []byte) []byte {
      b := bufPool.Get().(*bytes.Buffer)
      defer func() { b.Reset(); bufPool.Put(b) }()
      b.Write(p)
      return append([]byte(nil), b.Bytes()...) // copy out before returning
  }
  ```

## Tooling Gate

Go's toolchain is the first reviewer. Wire these into CI so no unformatted
or obviously-defective code merges.

```bash
gofmt -l .            # fails if any file is unformatted
goimports -w .        # order + prune imports
go vet ./...          # suspicious constructs
staticcheck ./...     # deeper static analysis
golangci-lint run     # aggregate meta-linter
go test -race ./...   # tests under the race detector
go mod tidy           # keep go.mod/go.sum minimal and correct
```

A pragmatic `.golangci.yml` baseline:

```yaml
linters:
  enable:
    - errcheck      # unchecked errors
    - govet
    - ineffassign   # assignments that are never used
    - staticcheck
    - unused
    - misspell
    - unconvert     # redundant conversions
    - unparam       # unused function params
issues:
  exclude-use-default: false
```

## Go Proverbs (quick reference)

| Proverb | In practice |
|---|---|
| Clear is better than clever | Write the obvious version; delete the clever one. |
| Errors are values | Handle, wrap, and return them; do not panic across boundaries. |
| Accept interfaces, return structs | Narrow input contract, concrete output. |
| Make the zero value useful | `var x T` should work, or ship a constructor. |
| Don't communicate by sharing memory | Coordinate goroutines with channels and context. |
| The bigger the interface, the weaker the abstraction | One- to three-method interfaces at the consumer. |
| A little copying beats a little dependency | Do not add a module for ten lines. |
| gofmt's style is no one's favorite, yet gofmt is everyone's friend | Format unconditionally; never argue layout. |
| Return early | Keep the happy path at the left margin. |

## Anti-Patterns

| Anti-pattern | Why it hurts | Do instead |
|---|---|---|
| `result, _ := doThing()` | Silently swallows failures; corrupts state downstream | Check the error; return or handle it |
| `panic(err)` for ordinary failures | Crashes the process; unrecoverable across API boundaries | Return the error as a value |
| Comparing errors by string or `==` on wrapped errors | Breaks the instant someone adds a wrap | `errors.Is` / `errors.As` |
| `context.Context` stored in a struct | Hides lifecycle; leaks cancellation scope | Pass `ctx` as the first parameter |
| Naked returns in a long function | Reader cannot tell what is returned | Name returns only in tiny functions, or return explicitly |
| Unbuffered send in a spawned goroutine with no `select` | Leaks the goroutine forever if the receiver is gone | Buffer the channel or `select` on `ctx.Done()` |
| Package-level mutable state set in `init()` | Untestable, racy, order-dependent | Inject dependencies through a struct |
| Mixing value and pointer receivers on one type | Inconsistent mutation semantics; `go vet` copy-lock warnings | Pick one receiver style per type |
| Returning an interface from a constructor | Hides fields the caller needs; forces speculative abstraction | Return the concrete type |
| String concatenation with `+=` in a hot loop | O(n²) allocations | `strings.Builder` or `strings.Join` |

**Bottom line:** Go code should be boring in the best sense — predictable,
consistent, and legible on the first read. When two designs tie, choose the
simpler one.

## Changelog

- **1.0.0** — Initial release. Idiomatic Go patterns: guiding principles,
  error handling (wrapping, sentinel/typed errors, `errors.Is`/`As`),
  concurrency (context, worker pool, errgroup, leak avoidance, graceful
  shutdown), interface/package design, struct ergonomics (functional
  options, embedding), allocation-aware performance, tooling gate, proverbs
  quick reference, and an anti-patterns table.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=5cd544aa1c0deb5897433fc2dd84dcdfbc1fa0a00bf8ebdceadb9117b08cbd57
