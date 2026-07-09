<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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
