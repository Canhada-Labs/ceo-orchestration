---
name: testing-strategy
description: Testing strategy, patterns, and quality assurance for the project.
  Covers vitest patterns, external integration test design (mocking transport,
  simulating reconnect, checksum validation for streaming sources), domain math
  test design (boundary values, precision edge cases), E2E multi-process testing
  (IPC, worker lifecycle), route testing (auth verification, input validation),
  database test patterns (mocking data layer), chaos test framework design, test
  quality metrics (mutation testing, branch coverage), and CI integration. Use
  when writing tests, reviewing test quality, designing test strategies, setting
  up CI pipelines, or evaluating test coverage gaps.
owner: QA Architect (archetype)
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: low
stack: [pytest, jest]
context_budget_tokens: 1100
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 4}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 5}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: file-edit, glob: "**/test_*.py"}
  - {event: file-edit, glob: "**/*.test.{ts,tsx,js,jsx}"}
---

# Testing Strategy

> Examples use vitest, but the patterns apply to Jest, Mocha, pytest, Go testing,
> and any mainstream test runner.

## Current State

| Metric | Value | Assessment |
|--------|-------|-----------|
| Total tests | (measure) | Track passing/failing |
| Test files | (measure) | In `src/__tests__/` or equivalent |
| TypeScript errors | 0 target | `tsc --noEmit` clean |
| Framework | vitest 4.x | Fast, ESM-native |
| E2E multi-process tests | (measure) | Often a gap |
| Stress/chaos tests | (measure) | Often a gap |
| CI test execution | required | Tests must run before deploy |
| Mutation testing | (optional) | Verifies test quality |
| Branch coverage | (measure) | Should be tracked |

### Key Principle

> A passing test suite is not a quality signal unless the tests themselves
> are audited. Happy-path tests without error-path, auth, multi-process, and
> edge-case coverage can give a false sense of safety.

## Vitest Patterns for {{PROJECT_NAME}}

### Configuration

A minimal vitest setup lives in `package.json` scripts:

```json
{
  "test": "vitest run",
  "test:watch": "vitest --watch"
}
```

### Test File Conventions

```
src/__tests__/
  ├── {integration}.test.ts   — per-integration tests
  ├── {feature}.test.ts       — feature-specific tests
  ├── precision-*.test.ts     — numeric precision tests
  ├── {domain}-*.test.ts      — domain logic tests
  └── {workflow}-*.test.ts    — workflow tests
```

### Standard Test Structure

```typescript
import { describe, test, expect, beforeEach, afterEach, vi } from "vitest";

describe("ModuleName", () => {
  // Group by behavior, not by method
  describe("when receiving valid input", () => {
    test("updates local state", () => { ... });
    test("emits event", () => { ... });
    test("resets counter", () => { ... });
  });

  describe("when receiving out-of-order input", () => {
    test("buffers the event", () => { ... });
    test("does not emit", () => { ... });
  });

  describe("error handling", () => {
    test("rejects malformed message", () => { ... });
    test("recovers from integrity check failure", () => { ... });
  });
});
```

### Rules

1. **Test file naming:** `{module}.test.ts` in `src/__tests__/`.
2. **Describe blocks:** Group by scenario/behavior, not by function name.
3. **Test names:** Start with verb: "updates", "rejects", "recovers", "computes".
4. **No test interdependence.** Each test MUST be independently runnable.
5. **No network calls.** All external dependencies mocked.
6. **Run before every commit:** `npx vitest run` -- zero failures required.

## External Integration Test Design

### Current Coverage

Each external integration should have a dedicated test file. These typically test:
- Initial state + incremental update reconciliation
- Sort order verification (where applicable)
- Removal of empty/zero entries
- Input validation
- Identifier normalization (canonical forms)

### Mock Transport Pattern

```typescript
import { vi, describe, test, expect } from "vitest";

// Mock transport message for integration testing
function createMockMessage(type: string, data: any): any {
  return JSON.stringify({ type, data });
}

describe("ThirdPartyAPIClient", () => {
  describe("incremental update application", () => {
    test("applies update to local state", () => {
      const state = createEmptyState();

      // Simulate initial snapshot
      applySnapshot(state, {
        primary: [["A", "1.5"], ["B", "2.0"]],
        secondary: [["C", "1.0"], ["D", "3.0"]],
        lastUpdateId: 100,
      });

      // Simulate incremental update
      applyUpdate(state, {
        p: [["A", "2.0"]],   // Update existing entry
        s: [["C", "0"]],     // Remove entry (size=0)
      });

      expect(state.primary.get("A")).toBe("2.0");
      expect(state.secondary.has("C")).toBe(false);
    });

    test("rejects update before snapshot", () => {
      const state = createEmptyState();
      state.snapshotLoaded = false;

      const result = applyUpdate(state, {
        p: [["A", "1.0"]],
        s: [],
      });

      // Should buffer, not apply
      expect(state.primary.size).toBe(0);
    });
  });
});
```

### Checksum Validation Tests

> Some streaming data sources provide a checksum (e.g., CRC32) with each
> update so clients can verify they haven't drifted from the authoritative
> state. When integrating such a source, test the checksum computation
> against known reference values.

```typescript
describe("Checksum validation", () => {
  test("signed checksum matches expected value", () => {
    const primary = [["A", "1"], ["B", "2.5"]];
    const secondary = [["C", "0.5"], ["D", "1.0"]];

    // Checksum format defined by the upstream source
    const checksumString = buildChecksumString(primary, secondary);
    const computed = computeSignedChecksum(checksumString);
    const expected = -1234567890; // Known expected value from fixture

    expect(computed).toBe(expected);
  });

  test("unsigned checksum handles trailing-zero normalization", () => {
    // Some sources strip trailing zeros before hashing
    // "50.50" -> "5050", "1.500" -> "15"
    const input = "5050015";
    const computed = computeUnsignedChecksum(input);

    expect(computed).toBe(expected_unsigned_value);
  });

  test("signed checksum uses source-specific level format", () => {
    // Document the exact input format required by the source
    const levels = buildChecksumInput(primary, secondary);
    const computed = computeSignedChecksum(levels);

    expect(computed).toBe(expected_signed_value);
  });
});
```

### Reconnect Simulation Tests

```typescript
describe("Transport reconnection", () => {
  test("buffers messages during reconnect", () => {
    const client = createClient("third-party-api");

    // Simulate connection drop
    client.simulateDisconnect();

    // Messages arrive during reconnect window
    client.simulateMessage(createUpdate(101));
    client.simulateMessage(createUpdate(102));

    // Reconnect + new snapshot
    client.simulateReconnect();
    client.simulateMessage(createSnapshot(200));

    // Buffered updates should be discarded (stale sequence)
    expect(client.getState()).toMatchObject({
      lastUpdateId: 200,
      snapshotLoaded: true,
    });
  });

  test("respects reconnect gate (max 3 per 10s)", () => {
    const gate = createReconnectGate({ maxPerWindow: 3, windowMs: 10000 });

    expect(gate.canReconnect()).toBe(true);  // 1st
    gate.recordReconnect();
    expect(gate.canReconnect()).toBe(true);  // 2nd
    gate.recordReconnect();
    expect(gate.canReconnect()).toBe(true);  // 3rd
    gate.recordReconnect();
    expect(gate.canReconnect()).toBe(false); // 4th -- blocked
  });
});
```

## Domain Math Test Design

### Boundary Value Tests

The principles below (boundary values, empty inputs, tiny values, huge values,
NaN/Infinity handling) apply universally. The specific function in the example
is domain-specific — substitute your own function.

```typescript
describe("weightedAverage computation", () => {
  test("single entry returns that value", () => {
    const entries = [{ value: "50000", weight: "1.0" }];
    expect(weightedAverage(entries).toString()).toBe("50000");
  });

  test("two equal-weight entries returns arithmetic mean", () => {
    const entries = [
      { value: "50000", weight: "1.0" },
      { value: "60000", weight: "1.0" },
    ];
    expect(weightedAverage(entries).toString()).toBe("55000");
  });

  test("zero total weight returns INSUFFICIENT_DATA", () => {
    const entries: any[] = [];
    const result = weightedAverage(entries);
    expect(result.state).toBe("INSUFFICIENT_DATA");
  });

  test("very small values preserve precision", () => {
    const entries = [
      { value: "0.00000001", weight: "100000000" },
      { value: "0.00000002", weight: "100000000" },
    ];
    const avg = weightedAverage(entries);
    expect(avg.toString()).toBe("0.000000015");
  });

  test("very large values do not overflow", () => {
    const entries = [
      { value: "99999999.99", weight: "99999999.99" },
    ];
    const avg = weightedAverage(entries);
    expect(avg.toString()).toBe("99999999.99");
  });
});
```

### Precision Edge Cases

```typescript
describe("Decimal precision", () => {
  test("your decimal library's API surprises are pinned in tests", () => {
    // Example: a decimal library may not implement every method you expect.
    // Pin these surprises in a test so future upgrades catch regressions.
    const d = new Decimal("123.45");
    expect(typeof d.isFinite).toBe("undefined"); // or whatever applies
  });

  test("string-to-Decimal round-trip preserves precision", () => {
    const original = "0.123456789012345678";
    const decimal = new Decimal(original);
    expect(decimal.toString()).toBe(original);
  });

  test("Decimal never passes through Number", () => {
    // Enforce the invariant: Decimal -> Number -> Decimal loses precision
    const precise = "9007199254740993"; // Number.MAX_SAFE_INTEGER + 2
    const decimal = new Decimal(precise);
    const throughNumber = new Decimal(Number(precise));

    expect(decimal.toString()).toBe(precise);
    expect(throughNumber.toString()).not.toBe(precise); // PRECISION LOST
  });

  test("subtraction handles equal operands", () => {
    const a = new Decimal("50000");
    const b = new Decimal("50000");
    const diff = a.minus(b);
    expect(diff.toString()).toBe("0");
    // Domain invariant check (e.g., strict ordering)
    expect(a.gt(b)).toBe(false); // Equal = not strictly greater
  });

  test("identifier normalization produces canonical form", () => {
    // Upstream format vs. internal canonical form
    const external = "FOO-BAR";
    const canonical = normalizeIdentifier(external);
    expect(canonical).toBe("foo_bar");
  });
});
```

### Property-Based Tests (Recommended Addition)

```typescript
import fc from "fast-check";

describe("Domain invariants (property-based)", () => {
  test("sorted-descending stays sorted-descending", () => {
    fc.assert(fc.property(
      fc.array(fc.tuple(fc.float({ min: 0.01, max: 100000 }), fc.float({ min: 0.001, max: 1000 }))),
      (entries) => {
        const sorted = sortDesc(entries.map(([k, v]) => ({ key: k.toString(), value: v.toString() })));
        for (let i = 1; i < sorted.length; i++) {
          if (parseFloat(sorted[i].key) > parseFloat(sorted[i - 1].key)) return false;
        }
        return true;
      }
    ));
  });

  test("cumulative sum is monotonically non-decreasing", () => {
    fc.assert(fc.property(
      fc.array(fc.float({ min: 0.001, max: 1000 }), { minLength: 1, maxLength: 100 }),
      (values) => {
        const cumulative = computeCumulative(values);
        for (let i = 1; i < cumulative.length; i++) {
          if (cumulative[i] < cumulative[i - 1]) return false;
        }
        return true;
      }
    ));
  });

  test("weighted average lies between min and max input", () => {
    fc.assert(fc.property(
      fc.array(
        fc.record({
          value: fc.float({ min: 0.01, max: 100000 }),
          weight: fc.float({ min: 0.001, max: 1000 }),
        }),
        { minLength: 1, maxLength: 50 }
      ),
      (entries) => {
        const avg = weightedAverageFloat(entries); // float version for property testing
        const values = entries.map(e => e.value);
        return avg >= Math.min(...values) && avg <= Math.max(...values);
      }
    ));
  });
});
```

## E2E Multi-Process Testing

### What Needs Testing

Most non-trivial systems run as multiple processes or threads:
- Main process (gateway, HTTP, WS, SSE)
- Worker processes (pool workers, background jobs, analytics)
- Worker threads in the main process
- Separate service machines

Without multi-process tests, ZERO tests verify the inter-process
communication paths — and these are often where production bugs hide.

### IPC Test Design

```typescript
describe("IPC: Worker Process -> Main Process", () => {
  test("message delivers state to main", async () => {
    // Spawn worker process in test mode
    const worker = await spawnTestWorkerProcess();
    const main = createTestMainProcess();

    // Inject a mock event into worker
    worker.injectEvent("source-a", "entity-1", mockPayload);

    // Wait for IPC delivery
    const received = await main.waitForEvent("source-a:entity-1", 5000);

    expect(received).toBeDefined();
    expect(received.items.length).toBeGreaterThan(0);
    expect(received.source).toBe("source-a");

    await worker.shutdown();
  });

  test("enriched message delivers processed payload", async () => {
    const worker = await spawnTestWorkerProcess();
    const main = createTestMainProcess();

    worker.injectEvent("source-a", "entity-1", mockPayload);

    // Wait for enriched version (slower path)
    const enriched = await main.waitForEnrichedEvent("source-a:entity-1", 10000);

    expect(enriched.quality).toBeDefined();
    expect(enriched.summary).toBeDefined();

    await worker.shutdown();
  });

  test("IPC channel failure triggers restart", async () => {
    const worker = await spawnTestWorkerProcess();
    const main = createTestMainProcess();

    // Kill IPC channel
    worker.breakIPCChannel();

    // Main should detect and restart worker
    const restarted = await main.waitForWorkerRestart(15000);
    expect(restarted).toBe(true);

    await worker.shutdown();
  });
});
```

### Worker Lifecycle Tests

```typescript
describe("Worker lifecycle", () => {
  test("Worker restarts on crash", async () => {
    const w = await spawnWorker();

    // Simulate crash
    w.terminate();

    // Should auto-restart
    await waitFor(() => w.isAlive(), 5000);
    expect(w.isAlive()).toBe(true);
  });

  test("Worker process respects max restart limit", async () => {
    const worker = await spawnTestWorkerProcess({ maxRestarts: 3 });

    // Crash 3 times
    for (let i = 0; i < 3; i++) {
      worker.crash();
      await waitFor(() => worker.isAlive(), 5000);
    }

    // 4th crash should not restart
    worker.crash();
    await sleep(5000);
    expect(worker.isAlive()).toBe(false);
  });
});
```

## Route Testing

### Auth Verification Tests

```typescript
describe("Route auth verification", () => {
  // Every privileged route must have auth tests
  const privilegedRoutes = [
    { method: "POST", path: "/resource/create" },
    { method: "POST", path: "/resource/delete" },
    { method: "POST", path: "/admin/circuit-breaker/trip" },
    { method: "POST", path: "/workflow/pause" },
    { method: "POST", path: "/risk/circuit-breaker/trip" },
    { method: "POST", path: "/workflow/start" },
  ];

  for (const route of privilegedRoutes) {
    test(`${route.method} ${route.path} requires authentication`, async () => {
      const res = await app.request(route.path, {
        method: route.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      // Should reject unauthenticated request
      expect(res.status).toBe(401);
    });

    test(`${route.method} ${route.path} rejects invalid token`, async () => {
      const res = await app.request(route.path, {
        method: route.method,
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer invalid.token.here",
        },
        body: JSON.stringify({}),
      });

      expect(res.status).toBe(401);
    });
  }
});
```

### Input Validation Tests

```typescript
describe("Input validation", () => {
  test("rejects non-string identifier", async () => {
    const res = await authenticatedRequest("POST", "/resource/create", {
      id: 12345,  // Should be string
      type: "standard",
      quantity: "1.0",
    });
    expect(res.status).toBe(400);
  });

  test("rejects negative quantity", async () => {
    const res = await authenticatedRequest("POST", "/resource/create", {
      id: "abc",
      type: "standard",
      quantity: "-1.0",
    });
    expect(res.status).toBe(400);
  });

  test("rejects unknown type", async () => {
    const res = await authenticatedRequest("POST", "/resource/create", {
      id: "abc",
      type: "nonexistent",
      quantity: "1.0",
    });
    expect(res.status).toBe(400);
  });

  test("rejects invalid enum value", async () => {
    const res = await authenticatedRequest("POST", "/resource/create", {
      id: "abc",
      type: "standard",
      mode: "sideways", // Must be one of a fixed set
      quantity: "1.0",
    });
    expect(res.status).toBe(400);
  });
});
```

## Database Test Patterns

### Mock Data Layer

```typescript
import { vi } from "vitest";

// Mock the database client for unit tests
function createMockDb() {
  const mockData = new Map<string, any[]>();

  return {
    from: (table: string) => ({
      select: (columns?: string) => ({
        eq: (col: string, val: any) => ({
          data: (mockData.get(table) || []).filter(row => row[col] === val),
          error: null,
        }),
        single: () => ({
          data: (mockData.get(table) || [])[0] || null,
          error: null,
        }),
      }),
      insert: (rows: any[]) => ({
        data: rows,
        error: null,
      }),
      upsert: (rows: any[]) => ({
        data: rows,
        error: null,
      }),
      delete: () => ({
        eq: (col: string, val: any) => ({
          data: null,
          error: null,
        }),
      }),
    }),
    // Seed test data
    _seed: (table: string, rows: any[]) => mockData.set(table, rows),
    _clear: () => mockData.clear(),
  };
}

describe("Database persistence", () => {
  const mockDb = createMockDb();

  beforeEach(() => {
    mockDb._clear();
  });

  test("upserts record correctly", async () => {
    const writer = createDbWriter(mockDb);

    await writer.upsertRecord({
      source: "source-a",
      id: "abc",
      payload: { primary: [["A", "1.0"]], secondary: [["B", "0.5"]] },
    });

    // Verify the write format
    const written = mockDb.from("records").select().data;
    expect(written).toHaveLength(1);
    expect(written[0].source).toBe("source-a");
  });

  test("handles database error gracefully", async () => {
    const errorDb = {
      ...mockDb,
      from: () => ({
        upsert: () => ({ data: null, error: { message: "Connection refused" } }),
      }),
    };

    const writer = createDbWriter(errorDb);

    // Should not throw, should log error
    await expect(writer.upsertRecord(mockRecord)).resolves.not.toThrow();
  });
});
```

### Row-Level Security / Access Control Testing

```typescript
describe("Access control policies", () => {
  test("user can only read own records", async () => {
    // Use anon/user key (RLS enforced)
    const { data, error } = await dbAsUser
      .from("user_profiles")
      .select("*")
      .eq("id", OTHER_USER_ID);

    expect(data).toHaveLength(0); // Policy blocks cross-user read
  });

  test("service role bypasses access control", async () => {
    // Use service_role key (RLS bypassed)
    const { data, error } = await dbAsService
      .from("user_profiles")
      .select("*")
      .eq("id", OTHER_USER_ID);

    expect(data).toHaveLength(1); // Service role can read any user
  });
});
```

## Chaos Test Framework Design

### Purpose

Chaos tests intentionally inject failures to verify the system's
resilience mechanisms work correctly. If you have zero chaos tests,
your claims about fault tolerance are unverified.

### Test Categories

```typescript
describe("Chaos: IPC failure", () => {
  test("system recovers from IPC channel drop", async () => {
    const system = await startFullSystem();

    // Verify healthy baseline
    expect(await system.getRecordCount()).toBeGreaterThan(0);

    // Inject failure: kill IPC channel
    system.breakIPCChannel();

    // Wait for detection + recovery
    await waitFor(() => system.getWorkerRestartCount() > 0, 30000);

    // Verify recovery
    expect(await system.getRecordCount()).toBeGreaterThan(0);

    await system.shutdown();
  });
});

describe("Chaos: Memory pressure", () => {
  test("system handles high message rate without OOM", async () => {
    const system = await startFullSystem();

    // Flood with messages (10x normal rate)
    system.setMessageRate(10);

    // Run for 60s
    await sleep(60000);

    // Check memory stayed bounded
    const memory = system.getMemoryUsage();
    expect(memory.heapUsed).toBeLessThan(4 * 1024 * 1024 * 1024); // 4GB

    // Check no messages were lost silently
    const dropCount = system.getDropCount();
    // Drops are OK if logged -- silent loss is not
    expect(system.getDropLogCount()).toBe(dropCount);

    await system.shutdown();
  });
});

describe("Chaos: Upstream disconnect", () => {
  test("reconnects after simultaneous disconnect of all upstreams", async () => {
    const system = await startFullSystem();

    // Disconnect all upstreams simultaneously
    system.disconnectAllUpstreams();

    // Wait for reconnect gate to allow reconnections
    await sleep(15000);

    // At least a majority of upstreams should have reconnected
    const connected = system.getConnectedUpstreamCount();
    expect(connected).toBeGreaterThanOrEqual(Math.floor(system.getUpstreamCount() / 2));

    await system.shutdown();
  });
});

describe("Chaos: Database outage", () => {
  test("system stays functional during database outage", async () => {
    const system = await startFullSystem();

    // Block database connections
    system.blockDatabase();

    // System should still serve cached data
    await sleep(30000);
    const records = await system.getRecordCount();
    expect(records).toBeGreaterThan(0);

    // Health should be degraded, not dead
    const health = await system.getHealth();
    expect(health.status).toBe("DEGRADED");

    // Unblock and verify recovery
    system.unblockDatabase();
    await sleep(10000);
    const healthAfter = await system.getHealth();
    expect(healthAfter.status).toBe("OK");

    await system.shutdown();
  });
});
```

## Test Quality Metrics

### Mutation Testing

Mutation testing modifies source code (mutants) and verifies that tests
catch the change. A surviving mutant means tests are too weak.

```bash
# Using Stryker for mutation testing
npx stryker run --mutate "<path/to/domain-math>"  # e.g. lib/pricing.ts
```

Priority targets for mutation testing:
1. Core domain logic (invariant enforcement)
2. Numeric comparison and validation
3. Aggregation / computation functions
4. Signal / decision generation
5. Authentication and authorization logic

**Target mutation score: >= 80% for critical modules.**

### Branch Coverage

```bash
# Generate coverage report
npx vitest run --coverage

# Coverage targets
# Critical/domain modules: >= 90% branch
# External integrations: >= 80% branch
# Routes: >= 70% branch (many are thin wrappers)
# Overall: >= 75% branch
```

### Planted-bug behavioral evals (reviewer / skill validation)

Mutation testing measures whether *unit tests* catch injected faults. The same
idea validates a **reviewer or a skill**: feed it a diff containing a KNOWN,
deliberately-planted bug and assert that the reviewer flags it — at the right
severity. If a "Staff Code Reviewer" skill cannot catch a planted SQL injection
or a plaintext-password store, the skill is not doing its job, no matter how
fluent its prose.

This is a distinct class from coverage/mutation: it tests **judgement quality**,
not code-path coverage. Author the planted-bug set against your real threat
model (for this framework: OWASP LLM Top-10 + A07/A09 — SQLi, plaintext
credentials, secret-in-logs, secret-exfil via audit-log side-channel,
non-constant-time secret compare, LLM01 prompt-injection). Anchor severity to a
PoC: a planted bug with a working exploit path is Critical. Always pair the
positives with a **clean control** (a correct diff) so the eval catches a
reviewer that flags everything (a false-positive-prone reviewer is as useless as
a blind one).

Worked example: `.claude/skills/core/code-review-checklist/benchmarks/code-review-checklist.yaml`
carries planted-bug scenarios (`REVIEW-BENCH-008..013`) plus a clean
`CTRL-REVIEW-004` control, run advisory via
`run-skill-benchmark.py --skip-if-no-key`. Note the scorer has no
"refused-to-approve" verdict — these evals assert the reviewer **flags** the
bug (`must_flag_tags` at Critical); an explicit approval-refusal assertion would
be its own eval-code item with QA + Security sign-off.

### Test Quality Checklist

| Criterion | Description | Target |
|-----------|-------------|--------|
| Mutation score | % of mutants killed | >= 80% (critical modules) |
| Branch coverage | % of code branches tested | >= 75% overall |
| Error path coverage | Tests that verify error handling | >= 50% of try/catch blocks |
| Edge case coverage | Boundary values, empty inputs, max values | Every critical function |
| Negative testing | Tests that verify rejection of bad input | Every public endpoint |
| Determinism | Tests pass/fail consistently (no flaky) | 100% deterministic |

## CI Integration

### Anti-Pattern

```yaml
# BROKEN -- no tests
- checkout
- deploy  # Deploys untested code to production
```

### Required Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    needs: typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npx vitest run --reporter=verbose
      - run: npx vitest run --coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  deploy:
    runs-on: ubuntu-latest
    needs: [typecheck, test]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        # Replace with your platform's deploy step. Examples:
        #   Fly.io:   uses: superfly/flyctl-actions/setup-flyctl@master
        #             run: flyctl deploy --remote-only
        #             env: FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        #   Vercel:   uses: amondnet/vercel-action@v25
        #   Railway:  uses: bervProject/railway-deploy@main
        #   AWS ECS:  uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        #   Cloud Run: uses: google-github-actions/deploy-cloudrun@v2
        run: echo "configure your deploy step"
```

### CI Rules

1. **Tests MUST pass before deploy.** No exceptions.
2. **TypeScript MUST compile cleanly.** Zero errors.
3. **Coverage MUST NOT decrease** on PR (fail if coverage drops).
4. **Deploy is blocked** until both typecheck and test jobs succeed.
5. **PR checks:** typecheck + test run on every PR.
6. **Main branch:** typecheck + test + deploy.

## Test Patterns by Module

### External Integration Tests

| What to Test | Example | Priority |
|-------------|---------|----------|
| Snapshot processing | Parse and store initial state | HIGH |
| Incremental update | Apply update to existing state | HIGH |
| Sequence validation | Detect and handle gaps | HIGH |
| Checksum verification | Validate integrity (where supported) | HIGH |
| Empty-entry removal | Zero/empty value removes entry | HIGH |
| Sort order | Deterministic ordering of outputs | HIGH |
| Identifier normalization | Upstream format to canonical | HIGH |
| Reconnect handling | Discard stale data after reconnect | MEDIUM |
| Rate limit handling | Backoff on 429 response | MEDIUM |
| Connection lifecycle | Connect, subscribe, disconnect | MEDIUM |

### Domain Math Tests

| What to Test | Example | Priority |
|-------------|---------|----------|
| Basic computation | Known inputs, hand-computed result | HIGH |
| Edge cases | Empty, single entry, huge values | HIGH |
| Subtraction / differences | Normal, zero, inverted | HIGH |
| Estimation against known data | Deterministic fixtures | HIGH |
| Decimal precision | String round-trip, no Number conversion | HIGH |
| Rounding modes | Explicit mode per function | HIGH |
| Cumulative sums | Monotonic non-decreasing | MEDIUM |
| Signal detection | True positive, true negative | MEDIUM |
| Fee / cost calculation | Parameterized by config | MEDIUM |

### Route Tests

| What to Test | Example | Priority |
|-------------|---------|----------|
| Auth required | 401 without token | CRITICAL |
| Auth valid token | 200 with valid token | HIGH |
| Auth expired token | 401 with expired token | HIGH |
| Input validation | 400 on bad input | HIGH |
| Tier gating | 403 for insufficient tier | HIGH |
| Rate limiting | 429 after limit exceeded | MEDIUM |
| CORS headers | Correct origin in response | MEDIUM |

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Test only happy path | Misses error handling bugs | Test error paths and edge cases |
| Mock everything | Tests pass but system broken | Integration tests for critical paths |
| Test implementation, not behavior | Breaks on refactor | Test inputs and outputs |
| Shared mutable state between tests | Flaky, order-dependent | Fresh setup per test |
| `expect(true).toBe(true)` | Vacuous truth | Assert specific values from computation |
| Skipping flaky tests | Hidden failures | Fix the flake or delete the test |
| No tests for auth | Privileged routes ship unauthed | Every route MUST have auth test |
| Testing in production only | Typo deploys to prod | CI runs tests before deploy |
| `any` in test types | Hides type mismatches | Use proper types in tests too |
| Testing private methods | Couples to implementation | Test via public interface |
## Adopter Note — Runner Framing + Example Biases (PLAN-044 P0-12)

This skill's top portability note ("Examples use vitest, but
the patterns apply to Jest, Mocha, pytest, Go testing, and
any mainstream test runner") is honest — but several
subsections below carry originating-project biases that are
worth naming explicitly for fresh adopters:

- §Current State table lists `Framework: vitest 4.x`,
  `src/__tests__/` location, and `TypeScript errors: 0
  target / tsc --noEmit clean`. Replace with your runner,
  your test-file location, and your typecheck tool before
  citing in review.
- §External integration test design references `mocking
  transport, simulating reconnect, checksum validation for
  streaming sources` — that is the originating ingestion-
  engine's test shape. Your integration-test shape may be
  HTTP-mocking, fixture-replay, or sandbox-environment.
- §Domain math tests reference `boundary values, precision
  edge cases` — universal when your domain has math, but
  the originating-project examples come from financial-
  instrument pricing. Substitute your own domain's
  boundary cases.
- §E2E multi-process tests (IPC, worker lifecycle) assume
  Node's cluster/worker model. On other runtimes the
  equivalent is different (Python multiprocessing, Go
  goroutine test harnesses, JVM test containers).

The patterns (mocking at the transport seam, asserting on
observable state not private calls, mutation testing to
verify test quality, CI-runs-tests-before-deploy) all
transfer. The tool names and file paths do not.
