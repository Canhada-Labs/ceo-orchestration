<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

