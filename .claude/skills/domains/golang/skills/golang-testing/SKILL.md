---
name: golang-testing
description: >
  Go testing workflow that keeps suites deterministic, parallel-safe, and
  honest about what they prove. Covers table-driven tests with named
  subtests, the stdlib-testing-versus-testify decision, test doubles
  (fakes over mocks, never mock what you don't own), httptest for HTTP
  handlers and clients, golden files behind an -update flag, fuzz targets
  for parser-shaped code, t.Parallel and race-detector discipline, the
  unit-versus-integration split (build tags, testing.Short,
  testcontainers-go), benchmark hygiene, and the flake-avoidance rules
  (no sleep-based synchronization, fake clocks, deterministic ordering).
  Complements golang-patterns: that skill writes the code, this one proves
  it. Use when authoring or reviewing any *_test.go file, wiring go test
  into CI, triaging a flaky or racy test, or adding fuzz or benchmark
  coverage to a Go module.
metadata:
  activation_triggers:
    - "editing or creating a *_test.go file"
    - "writing table-driven tests or subtests"
    - "reproducing or fixing a flaky Go test"
    - "wiring go test into CI (race detector, coverage, build tags)"
    - "adding fuzz targets or benchmarks to a Go module"
    - "choosing between stdlib testing, testify, and hand-rolled fakes"
    - "standing up integration tests (httptest, testcontainers-go)"
  paths:
    - "**/*_test.go"
    - "**/testdata/**"
    - "**/go.mod"
version: 1.0.0
risk_class: low
---

# Go Testing

A Go test suite earns trust two ways: it fails when the code is wrong,
and it passes for the same reason every time. Everything in this skill
serves those two properties. The governing bias matches the rest of the
squad: boring, explicit tests that a reviewer can audit on the first
read — a green suite that proves nothing is worse than a red one.

## When to Activate

Activate this skill for any of the following:

- Authoring or reviewing any `*_test.go` file.
- Wiring `go test` into CI — race detector, coverage, integration lanes.
- Triaging a flaky test or a race-detector firing.
- Adding fuzz targets or benchmarks.
- Choosing the test-double strategy for an external dependency.

## Table-Driven Tests and Subtests

The default shape for Go unit tests: a slice of named cases, one loop,
`t.Run` per case. Names appear in failure output and can be targeted
with `go test -run 'TestParse/empty_input'`.

```go
func TestParseQuantity(t *testing.T) {
    tests := []struct {
        name    string
        in      string
        want    int
        wantErr error
    }{
        {name: "plain integer", in: "42", want: 42},
        {name: "empty input", in: "", wantErr: ErrEmpty},
        {name: "negative rejected", in: "-3", wantErr: ErrNegative},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := ParseQuantity(tt.in)
            if !errors.Is(err, tt.wantErr) {
                t.Fatalf("ParseQuantity(%q) error = %v, want %v", tt.in, err, tt.wantErr)
            }
            if got != tt.want {
                t.Errorf("ParseQuantity(%q) = %d, want %d", tt.in, got, tt.want)
            }
        })
    }
}
```

Rules that keep tables honest:

- **Name every case** with what makes it distinct, not `case1`.
- **Assert errors with `errors.Is`/`errors.As`**, never string matching
  — the same contract production code follows.
- **`t.Fatalf` for preconditions, `t.Errorf` for verdicts**: fail fast
  when continuing would panic; accumulate when more signal helps.
- **Keep cases orthogonal.** A case that only re-proves another case's
  behavior is noise; delete it.

## Assertions: stdlib vs testify

Stdlib `if got != want { t.Errorf(...) }` is the default — zero
dependencies, no DSL to learn. `testify` earns its import in modules
with heavy struct comparison (`assert.Equal` diffs nested structs) or
where `require` improves flow. If adopted, keep the discipline:

- `require.*` for preconditions (aborts the subtest), `assert.*` for
  verdicts (continues). Mixing them randomly hides failures.
- Never `assert.True(t, x == y)` — it reports `false` with no diff.
  Use `assert.Equal(t, want, got)`.

For deep comparisons without testify, `google/go-cmp` with
`cmp.Diff(want, got)` printed on mismatch is the cleanest failure
output in the ecosystem. Pick one comparison idiom per module.

## Test Doubles: Fakes Over Mocks

Don't mock what you don't own. A hand-written mock of a third-party
client freezes your misunderstanding of that client into the suite.
Instead:

- **Own the interface.** Production code depends on a small
  consumer-side interface (`golang-patterns`); tests implement it with
  a fake — a real, if simplified, implementation.
- **Real boundaries get real doubles.** HTTP dependencies get
  `httptest.Server`; databases get testcontainers-go or an in-memory
  fake behind your own store interface.

```go
// A fake is a working implementation with test-controlled behavior.
type fakeStore struct {
    mu    sync.Mutex
    items map[string]int
    err   error // inject failures per test
}

func (f *fakeStore) Stock(ctx context.Context, sku string) (int, error) {
    if f.err != nil {
        return 0, f.err
    }
    f.mu.Lock()
    defer f.mu.Unlock()
    n, ok := f.items[sku]
    if !ok {
        return 0, ErrSKUNotFound
    }
    return n, nil
}
```

Expectation-style mocks (gomock, testify/mock) are a last resort for
verifying *interaction* ("was Close called exactly once?") — not for
simulating behavior. A suite full of `EXPECT()` chains tests the
implementation's call sequence, which makes every refactor a test
failure.

## HTTP Testing with httptest

Handlers are tested directly with `httptest.NewRecorder`; clients are
tested against `httptest.NewServer`. Neither opens a real port fight
or needs network access.

```go
func TestStockHandler_NotFound(t *testing.T) {
    h := NewHandler(&fakeStore{items: map[string]int{}})
    req := httptest.NewRequest(http.MethodGet, "/v1/stock/missing-sku", nil)
    rec := httptest.NewRecorder()

    h.ServeHTTP(rec, req)

    if rec.Code != http.StatusNotFound {
        t.Fatalf("status = %d, want %d", rec.Code, http.StatusNotFound)
    }
}

func TestClient_RetriesOn503(t *testing.T) {
    var calls int32
    srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if atomic.AddInt32(&calls, 1) == 1 {
            w.WriteHeader(http.StatusServiceUnavailable)
            return
        }
        fmt.Fprint(w, `{"ok":true}`)
    }))
    defer srv.Close()

    c := NewClient(srv.URL, WithRetries(1))
    if err := c.Ping(context.Background()); err != nil {
        t.Fatalf("Ping() = %v, want nil", err)
    }
}
```

Test the error branches (timeouts, 5xx, malformed JSON) — the happy
path is the branch least likely to break.

## Golden Files

For large or structured output (rendered templates, serialized
reports), compare against a checked-in `testdata/` file and regenerate
only behind an explicit flag:

```go
var update = flag.Bool("update", false, "rewrite golden files")

func TestRenderReport(t *testing.T) {
    got := RenderReport(sampleData()) // MUST be deterministic
    golden := filepath.Join("testdata", "report.golden")
    if *update {
        if err := os.WriteFile(golden, got, 0o644); err != nil {
            t.Fatal(err)
        }
    }
    want, err := os.ReadFile(golden)
    if err != nil {
        t.Fatal(err)
    }
    if !bytes.Equal(got, want) {
        t.Errorf("RenderReport mismatch:\n%s", cmp.Diff(string(want), string(got)))
    }
}
```

Two hard rules: the generator must be deterministic — **sort anything
derived from a map** (map iteration order is randomized by design) —
and a golden regeneration is reviewed like code, never rubber-stamped.

## Fuzzing

Any function that parses untrusted input deserves a fuzz target. The
fuzzer finds the inputs your table never imagined.

```go
func FuzzParseQuantity(f *testing.F) {
    f.Add("42")
    f.Add("")
    f.Add("-3")
    f.Fuzz(func(t *testing.T, in string) {
        n, err := ParseQuantity(in)
        if err == nil && n < 0 {
            t.Errorf("ParseQuantity(%q) = %d with nil error; negative must error", in, n)
        }
    })
}
```

Fuzz assertions are invariants ("never panics", "err==nil implies
valid"), not exact outputs. Run `go test -fuzz=FuzzParseQuantity
-fuzztime=30s` locally or on a scheduled lane; corpus files that find
bugs get committed under `testdata/fuzz/` as permanent regressions.

## Parallelism and the Race Detector

- `go test -race ./...` runs on every merge-gating CI lane. Removing
  it to make a suite green is a gate violation, not an optimization.
- A `-race` failure is a bug until proven environmental. "Flaky" is a
  diagnosis that requires evidence, not a label that dismisses one.
- `t.Parallel()` tests must not share mutable state: no package
  globals, no shared fixture structs, no `os.Chdir`. `t.Setenv`
  deliberately panics under `t.Parallel` — that panic is the guardrail
  working, not an obstacle.
- Use `t.Cleanup` instead of `defer` for teardown that subtests or
  helpers register; it runs in the right order even with parallelism.
- Pre-Go-1.22 modules must pin loop variables (`tt := tt`) before
  parallel subtests capture them — the classic all-cases-test-the-last-
  row bug.

## Unit vs Integration Split

Keep the default `go test ./...` fast and hermetic; let integration
tests be real but explicitly requested:

```go
//go:build integration

func TestStore_Postgres(t *testing.T) {
    ctx := context.Background()
    pg, err := postgres.Run(ctx, "postgres:16-alpine")
    if err != nil {
        t.Fatal(err)
    }
    t.Cleanup(func() { _ = pg.Terminate(ctx) })
    // ... exercise the real store against real SQL
}
```

- Build tags (`//go:build integration`) or `testing.Short()` guards
  keep the lanes separate; CI runs `-short` on merges and the full
  tagged suite pre-deploy and on schedule.
- testcontainers-go gives each test a real Postgres/Redis/Kafka in a
  throwaway container — real SQL dialect, real transactions, no
  shared state between runs.
- An in-memory fake behind your own interface covers business-logic
  tests; the tagged suite proves the real implementation honors the
  same contract (run the same test functions against both when
  practical).

## Benchmark Hygiene

Benchmarks lie unless you control what they measure:

```go
func BenchmarkRender(b *testing.B) {
    data := sampleData() // setup OUTSIDE the timed region
    b.ReportAllocs()
    b.ResetTimer()
    var sink []byte // prevent the compiler eliminating the call
    for i := 0; i < b.N; i++ {
        sink = RenderReport(data)
    }
    _ = sink
}
```

- Setup before `b.ResetTimer()`; per-iteration allocation in the loop
  poisons the number.
- `b.ReportAllocs()` always — allocs/op regressions are the earliest
  performance signal.
- Keep a sink so the compiler cannot dead-code-eliminate the work.
- Compare with `benchstat` over ≥10 runs (`-count=10`); a single run's
  delta is noise, not a result.

## Flake Avoidance

Flakes are determinism bugs. The recurring causes and their fixes:

| Cause | Fix |
|---|---|
| `time.Sleep` as synchronization | Wait on a channel the code under test closes/sends on; or poll with a bounded deadline helper |
| Real clocks in timeout logic | Inject a clock interface; tests use a fake they advance explicitly |
| Map iteration order in output | Sort before asserting or serializing |
| Shared ports | `httptest` picks its own; never hardcode `:8080` in a test |
| Test-order dependence | Every test builds its own fixture; verify with `go test -shuffle=on` |
| Goroutines outliving the test | Assert goroutine counts with bounded polling, or use a leak detector in `TestMain` |

The sleep rule is absolute: a sleep long enough to be reliable is too
slow, and a sleep fast enough to be quick is unreliable. There is no
correct constant.

## CI Gate

The merge-gating lane for any Go module:

```bash
gofmt -l .                                   # formatting (fails on output)
go vet ./...                                 # suspicious constructs
staticcheck ./...                            # deeper static analysis
go test -race -shuffle=on -count=1 ./...     # unit suite: raced, shuffled, uncached
go test -tags=integration ./... # pre-deploy + scheduled lane (real deps)
```

`-count=1` defeats the test cache on gating lanes; `-shuffle=on`
surfaces order dependence before it ships.

## Anti-Patterns

| Anti-pattern | Why it hurts | Do instead |
|---|---|---|
| `time.Sleep` to wait for a goroutine | Flaky under load, slow when padded | Channel signal or bounded polling |
| Removing `-race` to green a lane | Ships the race; the gate exists for exactly this moment | Fix the race; escalate if scaffolding-only |
| Mocking a third-party client | Freezes a guess about its behavior into the suite | Own the interface; fake it, or httptest the wire |
| `assert.True(t, a == b)` | Failure output says `false`, nothing else | `assert.Equal` / `cmp.Diff` |
| Golden files regenerated without review | Silently blesses a regression | `-update` flag + reviewed diff |
| Asserting on map-ordered output | Randomized by design; flakes eventually | Sort before comparing |
| One giant `TestEverything` | No isolation, no targeting, first failure hides the rest | Table-driven subtests |
| Skipped test with no linked issue | A permanent hole dressed as a pause | `t.Skip` with issue link, or delete with rationale |
| Benchmarks without `ReportAllocs`/sink | Compiler eliminates work; allocs invisible | Hygiene block above |
| Integration tests in the default lane | Slow, env-dependent merges | Build tags / `-short` split |

**Bottom line:** a test is a claim about behavior with evidence
attached. Deterministic evidence, or it isn't evidence.

## Changelog

- **1.0.0** — Initial release. Table-driven tests and subtests,
  assertion discipline (stdlib/testify/go-cmp), fakes-over-mocks
  doctrine, httptest patterns, golden files, fuzzing, parallelism and
  race-detector rules, unit-vs-integration split (build tags,
  testcontainers-go), benchmark hygiene, flake-avoidance table, CI
  gate, and an anti-patterns table.
