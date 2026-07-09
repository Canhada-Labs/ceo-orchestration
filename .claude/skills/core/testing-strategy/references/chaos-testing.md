<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

