<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

