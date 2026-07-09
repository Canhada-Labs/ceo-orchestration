<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/security-and-auth/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

## Rate Limiting Design

### Current Implementation (typical auth module)

- **Login rate limiting:** Per-IP, 5 attempts before lockout.
- **Progressive lockout:** 5min base, doubles per lockout cycle (max 30min).
- **Stale record cleanup:** 5min interval, records older than 10min deleted.
- **IP detection:** `fly-client-ip` header (PaaS-provided, e.g. Fly.io; not spoofable) with
  `x-forwarded-for` fallback.

### Rate Limiting Layers

| Layer | Scope | Where | Notes |
|-------|-------|-------|-------|
| Login brute force | Per-IP | auth.ts | Progressive lockout |
| API key per-tier | Per-key per-tier | api-v1 routes | free:100/day, pro:1K, enterprise:unlimited |
| AI chat | Per-user per-tier | ai routes | free:5, pro:50, enterprise:500 |
| WS connections | Global | index.ts | 500 data feed + 50 dashboard |
| PubSub backpressure | Per-client | pubsub.ts | 1MB skip, 4MB force-close |

### Missing Rate Limiting (audit gaps)

- Mutation routes: no rate limiting at all (SEC-3 to SEC-8)
- Proxy relays: no connection limits (SEC-10, SEC-11)
- Data-sync edge functions: no rate limiting (SEC-15)

## CORS Configuration

### Current State

```typescript
// WRONG — overly permissive (SEC-14)
cors({ origin: "*" })

// CORRECT — explicit allowed origins
cors({
  origin: [
    "https://{{DOMAIN}}",
    "https://www.{{DOMAIN}}",
    "https://app.{{DOMAIN}}",
  ],
  credentials: true,
  allowMethods: ["GET", "POST", "PUT", "DELETE"],
  allowHeaders: ["Authorization", "Content-Type"],
})
```

### Rules

1. **Never use `origin: "*"` with `credentials: true`.**
2. **List explicit origins.** Use env var for flexibility.
3. **Proxy relays MUST have CORS restricted to the main backend URL only.**
4. **Supabase Edge Functions MUST validate origin against allowlist.**
5. **Preflight caching:** Set `maxAge: 86400` for OPTIONS responses.

## WebSocket Security

### Current State (SEC-9)

WS data feed (`index.ts:1993-2010`) accepts all connections with zero
authentication. 500 slots available to anyone.

### Required Pattern

```typescript
// Phase 1: Auth on upgrade
server.upgrade(req, {
  data: {
    token: new URL(req.url).searchParams.get("token"),
    ip: getClientIP(req),
  },
});

// Phase 2: Verify in open handler
ws.on("open", () => {
  if (!verifyToken(ws.data.token)) {
    ws.close(4001, "Unauthorized");
    return;
  }
  // Tier-based channel access
});
```

### WS Security Checklist

- [ ] Auth on connection upgrade (token in query param or first message)
- [ ] Per-IP connection limiting
- [ ] Per-user connection limiting (post-auth)
- [ ] Message size limits (prevent memory exhaustion)
- [ ] Heartbeat enforcement (detect zombie connections)
- [ ] Channel-level authorization (tier gating)
- [ ] Rate limiting on subscribe/unsubscribe messages

## Proxy Relay Security (SEC-10, SEC-11)

### Current State

Both `proxy/upstream-a-relay.ts` and `proxy-b/upstream-b-relay.ts` are
open to the entire internet with zero authentication and zero connection
limits. Anyone who discovers the URL gets a free WS proxy.

### Required Pattern

```typescript
// 1. Shared secret between main backend and relay
const RELAY_SECRET = process.env.RELAY_AUTH_SECRET;

// 2. Verify on WS upgrade
server.upgrade(req, {
  headers: req.headers,
  data: {
    authorized: req.headers.get("x-relay-auth") === RELAY_SECRET,
  },
});

// 3. Reject unauthorized
if (!ws.data.authorized) {
  ws.close(4001, "Unauthorized");
  return;
}

// 4. Connection limiting
const MAX_RELAY_CONNECTIONS = 10;
if (activeConnections >= MAX_RELAY_CONNECTIONS) {
  ws.close(4008, "Too many connections");
  return;
}
```

