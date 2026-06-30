---
name: public-api-design
description: Designing and implementing public-facing APIs with versioning,
  self-service API key management, per-tier rate limiting, consumer-facing
  documentation, developer onboarding, and SDK patterns. Use when building
  API key self-service (user generates own keys in /settings), implementing
  rate limiting with sliding windows or token buckets, versioning REST or
  WebSocket APIs (v1 prefix), creating developer portals or quickstart
  guides, designing error response contracts, or planning deprecation
  policies. Also use when converting admin-only API key systems to
  user-facing self-service, building API usage dashboards, or implementing
  webhook delivery for external consumers. Even if the user just mentions
  "API keys", "developer portal", "rate limits per plan", "public API",
  or "API documentation", use this skill.
owner: Staff Backend Engineer (archetype)
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: medium
stack: []
context_budget_tokens: 800
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 7}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: file-edit, glob: "**/openapi.{yaml,yml,json}"}
  - {event: help-me-invoked, regex: "(?i)api.?design|openapi|rest"}
---

# Public API Design

## Fail-Fast Rule

If authentication fails, **return immediately** with a structured error.
Never leak internal error details, stack traces, or database schemas in
public API responses. Never serve stale or partial data without explicit
quality flags. API consumers make automated trading decisions — wrong
data is worse than no data.

## Cardinal Rule

**The public API is a product, not an endpoint.** It needs versioning,
documentation, rate limits, error contracts, deprecation policy, and
developer experience design — not just working routes. An undocumented
API with no error contract is a support ticket generator.

## Architecture: Admin Keys vs User Keys

{{PROJECT_NAME}} currently has `api-keys.ts` with admin-only key management.
The public API requires a second layer: **user self-service keys**.

```
┌─────────────────────────────────┐
│         API Key Types            │
├─────────────────────────────────┤
│                                  │
│  Admin Keys (existing)           │
│  ├── Managed via /admin panel    │
│  ├── Full access (read/write)    │
│  ├── Created by the Owner only   │
│  └── Stored in AdminConfig       │
│                                  │
│  User Keys (new)                 │
│  ├── Self-service via /settings  │
│  ├── Scoped by user's tier       │
│  ├── Rate limited per tier       │
│  ├── Stored in Supabase          │
│  └── Tied to user_id via RLS     │
│                                  │
└─────────────────────────────────┘
```

### Key Differences

| Property | Admin Keys | User Keys |
|----------|-----------|-----------|
| Storage | Engine in-memory (AdminConfig) | Supabase `user_api_keys` table |
| Creation | Admin panel only | Self-service in /settings |
| Scope | All endpoints | Tier-limited endpoints |
| Rate limit | Per-key (admin-set) | Per-tier (automatic) |
| Validation | Engine-local | Engine queries Supabase (cached) |
| Prefix | `adm_` | `usr_` |
| Max keys | Unlimited | Per tier (free: 0, pro: 3, institutional: 10) |

## API Versioning

### URL Prefix Strategy

```
/api/v1/resources              ← public, versioned
/api/v1/resources/:id          ← public, versioned
/api/v1/resources/:id/events   ← public, versioned
/internal/...                  ← internal (frontend), unversioned
/admin/...                     ← admin, unversioned
```

**Rule**: All public API endpoints live under `/api/v1/`. Internal endpoints
used by the frontend remain unversioned. This allows breaking changes to the
public API without affecting the frontend.

### Versioning Contract

- **v1 stability guarantee**: No breaking changes within v1. New fields can
  be added (additive), but existing fields never removed or renamed.
- **Deprecation**: Minimum 90 days notice before removing a v1 endpoint.
  Add `Sunset` header with deprecation date.
- **New version**: When breaking changes are needed, introduce `/api/v2/`
  and keep v1 running for 90 days.

```typescript
// Deprecation header middleware
function deprecationHeader(sunset: string) {
  return async (c: Context, next: Next) => {
    await next();
    c.header('Sunset', sunset);
    c.header('Deprecation', 'true');
    c.header('Link', '</api/v2/markets>; rel="successor-version"');
  };
}
```

## User Self-Service API Keys

### Supabase Schema

```sql
CREATE TABLE public.user_api_keys (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL CHECK (char_length(name) BETWEEN 2 AND 64),
  key_hash text NOT NULL UNIQUE,
  key_prefix text NOT NULL,  -- first 12 chars for display: "usr_a3f1..."
  permissions text NOT NULL DEFAULT 'read' CHECK (permissions IN ('read')),
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  expires_at timestamptz,
  revoked_at timestamptz,
  request_count bigint NOT NULL DEFAULT 0,
  CONSTRAINT max_keys_per_user CHECK (true)  -- enforced in application
);

CREATE INDEX idx_user_api_keys_hash ON public.user_api_keys(key_hash);
CREATE INDEX idx_user_api_keys_user ON public.user_api_keys(user_id);

-- RLS: users see only their own keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own keys"
  ON public.user_api_keys FOR ALL
  USING (auth.uid() = user_id);

-- RLS: service_role can update usage stats
CREATE POLICY "Service updates usage"
  ON public.user_api_keys FOR UPDATE
  USING (true)
  WITH CHECK (true);
```

### Key Generation (Engine Endpoint)

```typescript
import { randomBytes, createHash } from 'crypto';

const USER_KEY_PREFIX = 'usr_';
const MAX_KEYS_PER_TIER: Record<string, number> = {
  free: 0,
  pro: 3,
  institutional: 10,
};

// POST /api/v1/keys
app.post('/api/v1/keys', authMiddleware, async (c) => {
  const userId = c.get('userId');
  const tier = c.get('tier');
  const { name } = await c.req.json();

  // Check tier allows API keys
  const maxKeys = MAX_KEYS_PER_TIER[tier] ?? 0;
  if (maxKeys === 0) {
    return c.json({
      error: 'tier_insufficient',
      message: 'API keys require a Pro or Institutional subscription',
      upgrade_url: '/settings#billing',
    }, 403);
  }

  // Check key count limit
  const { count } = await supabase
    .from('user_api_keys')
    .select('id', { count: 'exact', head: true })
    .eq('user_id', userId)
    .is('revoked_at', null);

  if ((count ?? 0) >= maxKeys) {
    return c.json({
      error: 'key_limit_reached',
      message: `Your plan allows ${maxKeys} active keys`,
      current: count,
      max: maxKeys,
    }, 409);
  }

  // Generate key
  const rawBytes = randomBytes(32);
  const rawKey = USER_KEY_PREFIX + rawBytes.toString('hex');
  const keyHash = createHash('sha256').update(rawKey).digest('hex');
  const keyPrefix = rawKey.substring(0, 16) + '...';

  // Store hash (never the raw key)
  await supabase.from('user_api_keys').insert({
    user_id: userId,
    name: name.trim().substring(0, 64),
    key_hash: keyHash,
    key_prefix: keyPrefix,
    permissions: 'read',
  });

  // Return raw key ONCE — never stored, never retrievable
  return c.json({
    raw_key: rawKey,
    name,
    key_prefix: keyPrefix,
    warning: 'Copy this key now. It cannot be retrieved again.',
  });
});
```

### Key Validation with Cache

```typescript
// Cache validated keys for 60s to avoid hammering Supabase
const keyCache = new Map<string, { userId: string; tier: string; expiresAt: number }>();
const KEY_CACHE_TTL = 60_000;

async function validateUserApiKey(rawKey: string): Promise<{
  userId: string;
  tier: string;
} | null> {
  if (!rawKey.startsWith(USER_KEY_PREFIX)) return null;

  const keyHash = createHash('sha256').update(rawKey).digest('hex');

  // Check cache
  const cached = keyCache.get(keyHash);
  if (cached && cached.expiresAt > Date.now()) {
    return { userId: cached.userId, tier: cached.tier };
  }

  // Query Supabase
  const { data: key } = await supabase
    .from('user_api_keys')
    .select('user_id, revoked_at, expires_at')
    .eq('key_hash', keyHash)
    .single();

  if (!key) return null;
  if (key.revoked_at) return null;
  if (key.expires_at && new Date(key.expires_at) < new Date()) return null;

  // Get user tier
  const { data: profile } = await supabase
    .from('profiles')
    .select('tier')
    .eq('id', key.user_id)
    .single();

  const tier = profile?.tier ?? 'free';
  const result = { userId: key.user_id, tier };

  // Cache
  keyCache.set(keyHash, { ...result, expiresAt: Date.now() + KEY_CACHE_TTL });

  // Update usage stats (async, non-blocking)
  supabase.from('user_api_keys')
    .update({
      last_used_at: new Date().toISOString(),
      request_count: supabase.rpc('increment_key_usage', { hash: keyHash }),
    })
    .eq('key_hash', keyHash)
    .then(() => {});  // fire and forget

  return result;
}
```

## Rate Limiting

### Sliding Window Counter (Redis-Free)

For {{PROJECT_NAME}}'s scale (~500 concurrent users max), an in-memory sliding
window counter is sufficient. No Redis needed yet.

```typescript
interface RateLimitBucket {
  tokens: number;
  lastRefill: number;
}

const TIER_RATE_LIMITS: Record<string, { rpm: number; burst: number }> = {
  free:          { rpm: 30,  burst: 5 },
  pro:           { rpm: 120, burst: 20 },
  institutional: { rpm: 600, burst: 50 },
};

class SlidingWindowRateLimiter {
  private buckets = new Map<string, RateLimitBucket>();
  private cleanupInterval: ReturnType<typeof setInterval>;

  constructor() {
    // Cleanup stale entries every 5 minutes
    this.cleanupInterval = setInterval(() => {
      const now = Date.now();
      for (const [key, bucket] of this.buckets) {
        if (now - bucket.lastRefill > 120_000) {
          this.buckets.delete(key);
        }
      }
    }, 300_000);
  }

  check(key: string, tier: string): { allowed: boolean; remaining: number; resetMs: number } {
    const limits = TIER_RATE_LIMITS[tier] ?? TIER_RATE_LIMITS.free;
    const now = Date.now();
    const windowMs = 60_000;

    let bucket = this.buckets.get(key);
    if (!bucket) {
      bucket = { tokens: limits.rpm, lastRefill: now };
      this.buckets.set(key, bucket);
    }

    // Refill tokens based on elapsed time
    const elapsed = now - bucket.lastRefill;
    const refill = Math.floor((elapsed / windowMs) * limits.rpm);
    if (refill > 0) {
      bucket.tokens = Math.min(limits.rpm, bucket.tokens + refill);
      bucket.lastRefill = now;
    }

    if (bucket.tokens <= 0) {
      const resetMs = windowMs - elapsed;
      return { allowed: false, remaining: 0, resetMs };
    }

    bucket.tokens--;
    return { allowed: true, remaining: bucket.tokens, resetMs: 0 };
  }
}
```

### Rate Limit Middleware

```typescript
const rateLimiter = new SlidingWindowRateLimiter();

function rateLimitMiddleware(c: Context, next: Next) {
  const tier = c.get('tier') ?? 'free';
  const key = c.get('userId') ?? c.req.header('cf-connecting-ip') ?? 'anon';
  const limits = TIER_RATE_LIMITS[tier];

  const result = rateLimiter.check(key, tier);

  // Always set rate limit headers
  c.header('X-RateLimit-Limit', String(limits.rpm));
  c.header('X-RateLimit-Remaining', String(result.remaining));

  if (!result.allowed) {
    c.header('Retry-After', String(Math.ceil(result.resetMs / 1000)));
    return c.json({
      error: 'rate_limit_exceeded',
      message: `Rate limit: ${limits.rpm} requests/minute for ${tier} tier`,
      retry_after_ms: result.resetMs,
      upgrade_url: tier === 'free' ? '/settings#billing' : undefined,
    }, 429);
  }

  return next();
}
```

## Error Response Contract

### Standard Error Shape

Every public API error follows this shape. No exceptions.

```typescript
interface ApiError {
  error: string;           // machine-readable code (snake_case)
  message: string;         // human-readable explanation
  status: number;          // HTTP status code
  request_id?: string;     // for support debugging
  retry_after_ms?: number; // for rate limits
  upgrade_url?: string;    // for tier-gated features
  docs_url?: string;       // link to relevant docs
}
```

### Standard Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `invalid_api_key` | 401 | Key missing, malformed, or revoked |
| `expired_api_key` | 401 | Key past expiration date |
| `tier_insufficient` | 403 | Feature requires higher tier |
| `rate_limit_exceeded` | 429 | Too many requests |
| `pair_not_found` | 404 | Requested pair doesn't exist |
| `exchange_not_found` | 404 | Requested exchange doesn't exist |
| `data_stale` | 503 | Data available but exceeds staleness threshold |
| `exchange_degraded` | 503 | Exchange connection is degraded |
| `internal_error` | 500 | Unexpected server error (no details leaked) |
| `validation_error` | 400 | Invalid request parameters |

### Error Middleware

```typescript
function publicApiErrorHandler(err: Error, c: Context): Response {
  const requestId = crypto.randomUUID().substring(0, 8);

  // Never leak internals
  console.error(`[${requestId}] Public API error:`, err);

  if (err instanceof ApiError) {
    return c.json({
      error: err.code,
      message: err.message,
      status: err.status,
      request_id: requestId,
    }, err.status);
  }

  // Unknown errors → generic 500
  return c.json({
    error: 'internal_error',
    message: 'An unexpected error occurred',
    status: 500,
    request_id: requestId,
  }, 500);
}
```

## Public API Endpoints (v1)

### Subset of Internal API

Not all 780+ internal endpoints become public. Public API is a curated subset:

| Public Endpoint | Internal Source | Tier |
|----------------|----------------|------|
| `GET /api/v1/resources` | `/resources` | free |
| `GET /api/v1/resources/:id` | `/resources/:id` | free (basic fields), pro (full), institutional (full + metadata) |
| `GET /api/v1/resources/:id/detail` | `/resources/:id/detail` | pro |
| `GET /api/v1/events` | `/events/recent` | pro |
| `GET /api/v1/analytics/:id` | `/analytics/:id` | pro (24h), institutional (30d) |
| `GET /api/v1/metadata` | `/metadata` | free |
| `WS /api/v1/ws` | `/ws` | pro (limited channels), institutional (all) |

### Response Envelope

All public API responses use a consistent envelope:

```typescript
interface ApiResponse<T> {
  data: T;
  meta: {
    request_id: string;
    timestamp: string;      // ISO 8601
    tier: string;           // requester's tier
    cached: boolean;        // whether response is from cache
    data_age_ms?: number;   // age of underlying market data
    truncated?: boolean;    // if depth was tier-limited
    full_depth_available?: boolean;  // hint for upgrade
  };
}
```

Example:

```json
{
  "data": {
    "id": "RES-42",
    "name": "Example Resource",
    "attributes": { "status": "active", "count": 17 },
    "source_count": 6
  },
  "meta": {
    "request_id": "a3f1b2c4",
    "timestamp": "2026-02-24T14:30:00.000Z",
    "tier": "free",
    "cached": false,
    "data_age_ms": 230,
    "truncated": true,
    "full_depth_available": true
  }
}
```

## Developer Portal — Quickstart

### Minimum Viable Developer Portal

The developer portal is a page at `/developers` with:

1. **Quickstart** (3 steps: get key → first request → parse response)
2. **Authentication** (X-API-Key header)
3. **Rate limits per tier** (table)
4. **Endpoint reference** (from OpenAPI spec, consumer-facing subset)
5. **Code examples** (curl, Python, JavaScript, TypeScript)
6. **Error codes** (table)
7. **Changelog** (versioned, dated)

### Quickstart Example

```markdown
## Quick Start

### 1. Get an API Key
Sign up at [{{DOMAIN}}/signup](/signup), then go to
[Settings → API Keys](/settings#api-keys) to generate your key.

### 2. Your First Request
```bash
curl -H "X-API-Key: usr_YOUR_KEY_HERE" \
  https://{{DOMAIN}}/api/v1/resources
```

### 3. Parse the Response
```python
import requests

resp = requests.get(
    "https://{{DOMAIN}}/api/v1/resources/RES-42",
    headers={"X-API-Key": "usr_YOUR_KEY_HERE"}
)
data = resp.json()
first_item = data["data"]["attributes"]
print(f"Resource status: {first_item}")
```
```

## WebSocket API (Public)

### Authentication via First Message

```typescript
// Client connects to wss://{{DOMAIN}}/api/v1/ws
// First message must be auth:
ws.send(JSON.stringify({
  type: 'auth',
  api_key: 'usr_...',
}));

// Server responds:
{ type: 'auth_ok', tier: 'pro', channels: ['books', 'stats', ...] }
// or
{ type: 'auth_error', error: 'invalid_api_key' }
```

### Channel Access per Tier

| Channel | Free | Pro | Institutional |
|---------|------|-----|---------------|
| books | ✅ (5 levels, 15s delay) | ✅ (20 levels, real-time) | ✅ (full, real-time) |
| stats | ✅ | ✅ | ✅ |
| trades | ❌ | ✅ | ✅ |
| arb | ❌ | ✅ | ✅ |
| alerts | ❌ | ✅ | ✅ |
| candles | ❌ | ✅ | ✅ |
| regimes | ❌ | ❌ | ✅ |
| books_delta | ❌ | ❌ | ✅ |

## Testing Checklist

1. **Key generation**: Pro user creates key → receives raw key → can authenticate
2. **Key limit**: Pro user with 3 keys tries to create 4th → 409 error
3. **Free user blocked**: Free user tries to create key → 403 with upgrade URL
4. **Rate limiting**: Send 31 requests in 1 minute as free → 429 on 31st
5. **Rate limit headers**: Every response includes X-RateLimit-Limit and Remaining
6. **Tier depth limiting**: Free gets 5 levels, Pro gets 20, Institutional gets full
7. **Error contract**: Every error matches ApiError shape
8. **Version prefix**: All public endpoints under /api/v1/
9. **Key revocation**: Revoked key → 401 immediately (cache cleared)
10. **WS auth**: Connect without auth message → disconnect after 5s timeout

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| API key in query string | Logged in access logs, browser history | X-API-Key header only |
| Same rate limit for all tiers | No monetization incentive | Per-tier limits |
| Leaking internal error messages | Security risk + confusing | Structured error codes |
| No request_id in errors | Can't debug support tickets | Always include request_id |
| Unversioned public endpoints | Breaking changes break clients | /api/v1/ prefix |
| Full depth to free tier | No reason to upgrade | Tier-limited depth |
| Key validation without cache | Supabase query per request | 60s cache with TTL |
| User key stored as plaintext | Security risk | SHA-256 hash only |
| Rate limit in frontend only | Bypassable | Engine enforces |
| No Sunset header on deprecation | Clients break without notice | 90 days minimum |
