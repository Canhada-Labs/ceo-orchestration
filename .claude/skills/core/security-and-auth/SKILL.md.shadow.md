---
name: security-and-auth
description: Security architecture, authentication, authorization, and hardening for
  the {{PROJECT_NAME}}. Covers JWT+HMAC auth patterns, AES-256-GCM credential
  encryption, rate limiting design, OWASP Top 10 for Node.js/Hono, RLS policy design,
  timing-safe comparisons, API key lifecycle, input validation, CORS configuration,
  WebSocket auth, and proxy relay security. Use when reviewing or writing any code
  that touches authentication, authorization, credential storage, API key management,
  rate limiting, input validation, CORS, WebSocket security, proxy security, or any
  route that handles sensitive data or actions.
owner: Security Engineer (archetype)
---

# Security and Authentication

## Fail-Fast Rule

If any security invariant, validation, or precondition fails, **stop and
return a structured rejection**. Never degrade security silently. Never
skip auth checks "because it's internal." Never log secrets, even partially,
unless behind explicit masking. Never assume a route is unreachable.

## Known Vulnerabilities (ENGINE_AUDIT_2026-03-23.md)

These findings represent the current security posture. Every code change
in security-adjacent areas must be evaluated against this list.

### CRITICAL

| ID | File | Issue | Status |
|----|------|-------|--------|
| SEC-1 | routes/admin.ts:94 | AI_TRIGGER_KEY compared via `===` (timing oracle). Query param bypass of auth. | OPEN |
| SEC-2 | routes/core.ts:279 | Password comparison uses `!==` (not constant-time). | OPEN |

### HIGH

| ID | File | Issue | Status |
|----|------|-------|--------|
| SEC-3 | routes/mutations.ts (N endpoints) | ZERO auth visible. POST /records creates business-critical records. | OPEN |
| SEC-4 | routes/jobs.ts (N endpoints) | ZERO auth. POST /jobs/halt pauses background processing. | OPEN |
| SEC-5 | routes/automations.ts (N endpoints) | ZERO auth. POST /automations/pause stops scheduled automations. | OPEN |
| SEC-6 | routes/admin-actions.ts (N endpoints) | ZERO auth. POST /admin/circuit-breaker/trip halts all user-facing writes. | OPEN |
| SEC-7 | routes/sandbox.ts (N endpoints) | ZERO auth. | OPEN |
| SEC-8 | routes/workflows.ts (N endpoints) | ZERO auth. POST /workflows/start triggers workflow execution. | OPEN |
| SEC-9 | index.ts (WS upgrade) | WS data feed 100% unauthenticated (500 slots). | OPEN |
| SEC-10 | proxy/upstream-a-relay.ts | ZERO auth, ZERO connection limits, open to internet. | OPEN |
| SEC-11 | proxy-b/upstream-b-relay.ts | ZERO auth, ZERO connection limits, open to internet. | OPEN |

### MEDIUM

| ID | File | Issue | Status |
|----|------|-------|--------|
| SEC-12 | routes/user-exports.ts:140-256 | user_id from body without verifying caller IS the user. | OPEN |
| SEC-13 | routes/vendor-integration.ts:236-246 | Private key via HTTP header (e.g. `X-Vendor-PrivateKey`). Never accept cryptographic secrets via request headers. | OPEN |
| SEC-14 | routes/public-router-inline.ts:178 | CORS hardcoded `origin: "*"`. | OPEN |
| SEC-15 | supabase/functions/data-sync | CORS wildcard + zero inbound auth. | OPEN |
| SEC-16 | supabase/functions/data-sync/upstream.ts:49 | Auth token cached cross-user (module scope). | OPEN |

## Authentication Architecture

### Token Types

The engine uses three distinct authentication mechanisms:

1. **Admin JWT (HMAC-SHA256)** — in your auth module
   - Created via `POST /auth/login` (username + password).
   - Token format: `base64(payload).hmac_hex`.
   - TTL: 4 hours. No refresh — re-login required.
   - Verified via `verifyToken()` using `timingSafeEqual` on HMAC signature.
   - Used for: admin endpoints, debug, runtime config.

2. **API Keys (HMAC-SHA256)** — `POST /admin/api-keys`
   - Stored hashed in Supabase (`api_keys` table).
   - Custom expiry (no fixed TTL). Per-tier rate limiting.
   - Used for: public API v1, feeds/RSS, webhooks.
   - Verification: constant-time HMAC comparison.

3. **Third-party credentials (AES-256-GCM)** — in your config/secrets module
   - Upstream service API keys encrypted at rest with AES-256-GCM.
   - Key derivation: PBKDF2 with 100K iterations + HKDF.
   - Web Crypto API — keys never exported from CryptoKey objects.
   - Used for: upstream integration calls, user data sync.

### Auth Middleware Pattern

```typescript
// CORRECT — explicit auth check at route level
app.post("/records", (c) => {
  if (!requireAuth(c)) return c.json({ error: "Unauthorized" }, 401);
  // ... handler
});

// CORRECT — silent auth for conditional data gating
app.get("/public-data", (c) => {
  const isPro = requireAuth(c, /* silent */ true);
  const data = isPro ? fullData : limitedData;
  return c.json(data);
});

// WRONG — no auth on sensitive endpoint (SEC-3 through SEC-8)
app.post("/records", (c) => {
  // Missing auth check entirely
  return createRecord(c);
});
```

### Rules for Adding New Routes

1. **Every route that mutates state MUST have `requireAuth(c)` as first line.**
2. **Every route that returns user-specific data MUST verify the caller IS the user.**
3. **Routes that use third-party credentials MUST additionally verify those credentials exist and are valid.**
4. **Public read-only routes MAY skip auth but MUST have rate limiting.**
5. **Admin routes MUST use admin auth (not just any valid token).**

## Timing-Safe Comparisons

### The Problem

String comparison via `===` or `!==` short-circuits on first mismatch.
An attacker can measure response time to determine how many characters
matched, progressively guessing the correct value.

### The Fix

```typescript
import { timingSafeEqual } from "crypto";

// CORRECT — constant-time comparison
function verifySecret(provided: string, expected: string): boolean {
  const a = Buffer.from(provided);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false; // length leak is acceptable
  return timingSafeEqual(a, b);
}

// WRONG — timing oracle (SEC-1, SEC-2)
if (queryParam === AI_TRIGGER_KEY) { ... }    // SEC-1
if (password !== adminPass) { ... }           // SEC-2
```

### Where to Apply

- Token verification (already correct in `auth.ts`)
- API key comparison
- Webhook signature verification (already correct in Stripe handler)
- AI trigger key comparison (SEC-1: currently vulnerable)
- Password comparison (SEC-2: currently vulnerable)
- Any secret comparison in request handling

## Credential Encryption (AES-256-GCM)

### Storage Pattern

```typescript
// Encrypt: plaintext → { iv, ciphertext, tag }
// Key derivation: PBKDF2(password, salt, 100000, SHA-256) → HKDF → AES key
// Decrypt: { iv, ciphertext, tag } + key → plaintext

// Database columns: api_key_enc, api_secret_enc, passphrase_enc
// NEVER store plaintext columns (api_key, api_secret) alongside encrypted
// The audit found auto-trader-manager.ts reading plaintext columns
// when data was stored encrypted — caused silent credential failures
```

### Rules

1. **Always use `_enc` suffixed columns.** Never read plaintext columns.
2. **IV must be unique per encryption.** Use `crypto.randomBytes(12)`.
3. **Never log decrypted credentials.** Use partial masking: `key.slice(0,4) + "***"`.
4. **Key material must never leave CryptoKey objects** (Web Crypto constraint).
5. **Credential rotation:** new encryption with new IV, overwrite old ciphertext.

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

## Supabase RLS Policy Design

### Current State

- 49 tables with RLS active and correct policies.
- Exception: `prediction_tables.sql` uses `FOR ALL USING (true)` — acceptable
  only for ephemeral/recreatable data.
- 16 tables have no DDL at all (disaster recovery risk).

### RLS Rules

1. **Every table MUST have RLS enabled.**
2. **Default deny:** No policy = no access (PostgreSQL default with RLS on).
3. **User isolation:** `USING (auth.uid() = user_id)` for user-owned data.
4. **Service role bypass:** `service_role` key bypasses RLS — use only from
   trusted backend, never from client.
5. **SECURITY DEFINER functions MUST set `search_path`** to prevent path
   injection (3 functions currently missing this).

### Policy Pattern

```sql
-- User can only read their own data
CREATE POLICY "user_read_own" ON user_profiles
  FOR SELECT USING (auth.uid() = id);

-- User can update their own data
CREATE POLICY "user_update_own" ON user_profiles
  FOR UPDATE USING (auth.uid() = id);

-- Service role can do anything (backend only)
-- (Implicit via service_role_key bypassing RLS)
```

## Input Validation Patterns

### Route-Level Validation

```typescript
// CORRECT — validate before processing
app.post("/records", (c) => {
  const body = await c.req.json();

  // Type validation
  if (typeof body.entity !== "string" || typeof body.kind !== "string") {
    return c.json({ error: "Invalid input types" }, 400);
  }

  // Enum validation
  if (!["create", "update"].includes(body.kind)) {
    return c.json({ error: "Invalid kind" }, 400);
  }

  // Numeric validation
  try {
    const amount = new Decimal(body.amount);
    if (amount.lte(0)) throw new Error("non-positive");
  } catch {
    return c.json({ error: "Invalid amount" }, 400);
  }

  // Enum/whitelist validation for source
  if (!VALID_SOURCES.has(body.source)) {
    return c.json({ error: "Unknown source" }, 400);
  }
});

// WRONG — trusting user input (SEC-12)
const { user_id } = await c.req.json();
// Must verify: authenticated user's ID === user_id from body
```

### Injection Prevention

| Vector | Defense | Status |
|--------|---------|--------|
| SQL injection | PostgREST parameterized (no raw SQL) | SAFE |
| XSS | JSON responses only (no HTML rendering) | SAFE |
| Prototype pollution | `council.ts` has guard, `client.ts` missing | PARTIAL |
| Prompt injection | Regex-only detection (bypassable via Unicode) | WEAK |
| CSV formula injection | `reports-exports.ts` outputs JSON, but CSV export lacks `=` prefix guard | PARTIAL |
| Path traversal | No file system operations from user input | SAFE |

## API Key Lifecycle

### Creation

```
POST /admin/api-keys
  → Generate random key
  → Hash with HMAC-SHA256
  → Store hash + metadata (tier, expiry, owner) in Supabase
  → Return plaintext key ONCE (never stored)
```

### Verification

```
Request with X-API-Key header
  → Extract key
  → HMAC hash the key
  → Look up hash in Supabase
  → Verify: not expired, not revoked, tier matches endpoint
  → Apply per-tier rate limits
```

### Revocation

```
DELETE /admin/api-keys/:id
  → Mark as revoked in DB (soft delete for audit trail)
  → Immediately reject future requests with that key
```

## OWASP Top 10 Checklist for {{PROJECT_NAME}}

| OWASP | {{PROJECT_NAME}} Status | Key File(s) |
|-------|----------------|-------------|
| A01: Broken Access Control | WEAK — N mutation endpoints unprotected | routes/mutations-*.ts |
| A02: Cryptographic Failures | GOOD — AES-256-GCM, HMAC-SHA256, PBKDF2 | auth.ts, config.ts |
| A03: Injection | GOOD — PostgREST, no raw SQL, JSON only | All routes |
| A04: Insecure Design | PARTIAL — proxy relays, WS unauth | proxy/*.ts, index.ts |
| A05: Security Misconfiguration | WEAK — CORS wildcard, defaults in dev | public-router-inline.ts |
| A06: Vulnerable Components | OK — small prod dep set, vitest dev only | package.json |
| A07: Auth Failures | WEAK — timing oracles, password not persisted | auth.ts, routes/admin.ts |
| A08: Data Integrity | GOOD — HMAC webhooks, signed tokens | auth.ts, stripe handler |
| A09: Logging Failures | GOOD — structured logging, IP masking | structured-log.ts |
| A10: SSRF | LOW RISK — no user-supplied URLs fetched | — |

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| `===` for secret comparison | Timing oracle | `timingSafeEqual` |
| Auth in "most" routes | One miss = full bypass | Auth middleware on route group |
| CORS `origin: "*"` | Allows any origin to call API | Explicit origin allowlist |
| Logging full API keys | Credential leak in logs | `key.slice(0,4) + "***"` |
| User ID from request body | Horizontal privilege escalation | Extract from verified JWT |
| Proxy without auth | Free infrastructure for attackers | Shared secret + conn limit |
| WS without auth on upgrade | Unauthenticated access to all channels | Verify token before accepting |
| `catch {}` on auth errors | Silently passes invalid auth | Always return 401/403 |
| Hardcoded secrets in source | Leak via git history | Env vars with bootstrap validation |
| Password change in memory only | Lost on restart (SEC-27) | Persist to Supabase |

## 20. Benchmarks

This skill has a measurable benchmark suite at
`.claude/skills/core/security-and-auth/benchmarks/owasp-basics.yaml`
(14 scenarios: 10 positive OWASP Top 10 + 4 precision controls).

Run locally:
```
python3 .claude/scripts/run-skill-benchmark.py \
    .claude/skills/core/security-and-auth/benchmarks/owasp-basics.yaml \
    --json
```

The benchmark runs each scenario 3× (median-of-3) at `temperature=0`
against `claude-haiku-4-5-20251001` and scores against `must_flag_tags`
+ `must_suggest_keywords` + `must_identify_severity`. Control scenarios
are scored on PRECISION (must NOT flag the listed tags at MEDIUM+).

CI mode is advisory in Sprint 2 (soft-fail + `$GITHUB_STEP_SUMMARY`
annotation). Sprint 3 tightens to an absolute floor. Sprint 4 adds
regression gating against `main`'s last-known-good score.

Scenario edit policy: any change to code samples, expected tags, or
severity bumps the scenario's `version:` and carries a `validated_by:
YYYY-MM-DD` line. CODEOWNERS gates the benchmark YAML.
## OWASP LLM Top 10 (2024) — inference-path rubric

> Cross-ref: full rubric + framework-defense mapping at
> `docs/OWASP-LLM-TOP-10.md`. Benchmark fixtures at
> `benchmarks/owasp-llm-top-10.yaml` (14 positive + 6 control
> scenarios, model_baseline_version = claude-opus-4-7).

When reviewing LLM-adjacent code, the security specialist MUST
verify each of the 10 categories:

| ID | Category | First-pass audit question |
|----|----------|---------------------------|
| LLM01 | Prompt injection | Does untrusted input reach a prompt concatenated with system instructions without separator/pre-scan/escape? |
| LLM02 | Insecure output handling | Is LLM output piped to an HTML / shell / SQL sink without sanitization? |
| LLM03 | Training-data poisoning | Is a fine-tune pinned by hash + behavioral regression test before hot-path? |
| LLM04 | Model DoS | Is there a per-caller rate limit + per-request max-token clamp + cumulative budget? |
| LLM05 | Supply chain | Is every MCP server pinned (SHA + signature), not `npx -y`? |
| LLM06 | Sensitive info disclosure | Is PII / secrets absent from prompt + logs + retrieved content? |
| LLM07 | Insecure plugin design | Does every spawned agent carry `## SKILL CONTENT` or `## SKILL REFERENCE`? Tool scopes least-privilege? |
| LLM08 | Excessive agency | Is destructive tool authority kill-switched + dry-run-able + human-confirmed? |
| LLM09 | Overreliance | Is the merge gate re-verifying via CI, not accepting agent "tests pass" self-report? (PROTOCOL §Artifact Paradox) |
| LLM10 | Model theft | Is the prompt library redacted before export to external sinks? |

Failure to audit any category = reviewer strike (ADR-031 §Review
discipline).

Benchmark runs per quarter via
`.claude/scripts/run-skill-benchmark.py --skill security-and-auth
--benchmark owasp-llm-top-10`. Pass threshold 0.7, control threshold
0.85 (stricter than owasp-basics).
