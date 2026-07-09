<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

