<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

