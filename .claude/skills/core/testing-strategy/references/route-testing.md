<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->


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

