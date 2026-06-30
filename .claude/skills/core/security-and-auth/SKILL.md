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
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-security-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/engineering/engineering-threat-detection-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 1
risk_class: high
stack: [typescript, node, python]
context_budget_tokens: 1400
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 2}
  engine: {active: true, priority: 1}
  fintech: {active: true, priority: 1}
  trading-readonly: {active: true, priority: 1}
  generic: {active: true, priority: 3}
activation_triggers:
  - {event: file-edit, glob: "**/auth/**"}
  - {event: file-edit, glob: "**/.env*"}
  - {event: help-me-invoked, regex: "(?i)auth|jwt|oauth|rate.?limit"}
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

Benchmark runs per quarter (advisory in Sprint 2; strict in Sprint 3+) via
`python3 .claude/scripts/run-skill-benchmark.py .claude/skills/core/security-and-auth/benchmarks/owasp-llm-top-10.yaml --floor 0.7 --strict`.
The `--floor 0.7` flag gates aggregate score; `--strict` fails the run on
any individual scenario below the floor (without `--strict`, failed
scenarios pass the run if aggregate ≥ 0.7). Control scenarios (must NOT
flag) are scored binary today — 1.0 if uncaught, 0.0 if false-positive;
the YAML's `control_threshold: 0.85` is metadata reserved for stricter
runner scoring (Sprint 3+) and is NOT enforced by the runner currently.
Manual inspection of any failed positive AND any false-positive control
is required regardless of CLI exit code. (NOTE: this corrects a
pre-existing canonical-content bug where the documented invocation used
non-existent `--skill` / `--benchmark` flags; see PLAN-074 Wave 1a fix-pack.)

## Threat-Model Worksheet — adversary-first design pass

A threat-model worksheet is a pre-implementation artifact, not a
post-implementation audit. The goal is to enumerate what an attacker
gains by abusing each new component before code lands. Every L3+
change touching auth, money flow, KYC, custody, withdrawal, or admin
authority MUST attach a worksheet to its plan or PR — the security
archetype's Pass-1 review will reject the change otherwise.

### Six adversary-lens questions (run in order)

1. **What does the attacker want?** — credit balance, withdrawal
   authority, PII export, market manipulation, denial of one tenant
2. **Where is the cheapest entry point?** — public endpoint, leaked
   API key, compromised partner, SSRF reflector, social-engineered
   support ticket
3. **What capability does the entry point grant?** — read-only,
   write-with-limits, admin-equivalent, key-material exposure
4. **What is the blast radius if that capability is held for one
   hour?** — single account, one tenant, all paying tenants, custody
   keys, regulator reporting
5. **What is the detection latency in the current monitoring posture?**
   — under 1 min, under 1 hour, next business day, never
6. **What compensating control degrades gracefully if the primary
   control fails?** — second-factor on withdraw, signed audit chain,
   manual approval over threshold, kill-switch on volume anomaly

### STRIDE rows for the canonical fintech surfaces

The framework's STRIDE schema covers six adversary categories. Use
this table as the starting matrix for any payment, custody, or KYC
endpoint; copy it into the plan and add domain-specific rows.

| Category                | Surface attacked          | Concrete fintech scenario                                              | Required defense (this framework's pattern)                                      |
|-------------------------|---------------------------|------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| Spoofing identity       | Token issuance            | Replayed JWT after laptop theft; forged refresh token                  | Short TTL + bind refresh to device fingerprint + revoke on password change       |
| Tampering data          | Withdrawal request body   | Modified `amount` after signature, modified `destination` after KYC    | HMAC over canonicalized body, NOT the parsed JSON object; idempotency key gate   |
| Repudiation             | Admin trigger of payouts  | Operator denies authorizing a $50K payout; no immutable record         | Signed action log w/ chained hashes (ADR-055 §audit-log HMAC chain)              |
| Information disclosure  | Error responses on /login | Distinct messages reveal "user exists" vs "wrong password"             | Single generic 401 + side-channel mitigation (constant-time + uniform delay)     |
| Denial of service       | Pricing-update fanout     | Attacker subscribes 10K WS clients, forces fan-out backlog             | Per-IP and per-tier subscription cap + 4MB force-close ceiling (see PubSub row)  |
| Elevation of privilege  | Read-only API key on KYC  | Read-scope key used to call `POST /admin/kyc-override`                 | Server-side role check from JWT scope claim, never client-supplied role          |

### Worked example — POST /v1/withdrawals (fintech canonical)

The withdrawal endpoint is the canonical fintech worked example
because it carries every category at once. Treat the worksheet below
as the minimum bar for any equivalent action (transfer, redemption,
custody-key-rotation, regulator export).

```
Endpoint: POST /v1/withdrawals
Caller: API key (tier=pro+) OR admin JWT
Mutation: debits user balance, queues payout to external rail

What the attacker wants
  Withdraw funds to attacker-controlled destination

Cheapest entry point
  (1) Phished customer API key, OR
  (2) Replay of legitimate request after MITM on customer integration

Capability if obtained
  Move balance up to per-tier daily withdraw cap (currently uncapped on pro)

Blast radius (one hour, no detection)
  All available balance of compromised account drained;
  cross-account contagion if same key has been pasted into multiple tenants

Detection latency (current posture)
  Median 4 hours (volume-anomaly batch job); SEV1 trigger requires
  customer ticket (~30 min after first reconciliation cycle)

STRIDE row coverage
  Spoofing            HMAC binds key to request body; refresh of stolen
                      key requires email-confirmation factor
  Tampering           Idempotency key + body-HMAC enforced server-side
  Repudiation         Action-log chain entry per withdraw_request_v1
  Info disclosure     Error responses generic; detailed reason via /v1/
                      withdrawals/:id behind owner-scope only
  DoS                 Per-key 60/min, per-account 5/min, per-destination 1/min
  Privilege elevation Server-side scope check; admin override requires
                      separate admin JWT, NOT scope-flag flip on API key

Compensating controls
  - Daily withdraw cap per-tier; admin lifts on documented ticket
  - Velocity rule: >3 withdraws to new destinations in 24h triggers
    SEV2 page + freeze pending review (manual unfreeze)
  - Signed action-log chain replayed nightly; mismatch → SEV1 page
  - Withdraw to new destination = 24h hold + email confirm + SMS step-up

Residual risk accepted
  Compromised-key-with-known-destination-in-history scenario;
  not mitigated by the new-destination hold. Accept until
  device-fingerprint binding ships (out of PLAN-074 scope; tracked
  in a follow-up plan to be opened post-v1.12.0).
```

### Coverage rules

1. **Every L3+ plan MUST attach a worksheet.** The security archetype
   rejects the plan at Pass-1 if missing.
2. **Every STRIDE row MUST cite a defense already in this skill** OR
   a tracked plan that adds one. "We will add later" without a plan
   ID = reject.
3. **The "blast radius (one hour)" line MUST be quantified.** "Some
   accounts" is not an answer. Pick a number; if you cannot, the
   capability assessment is incomplete.
4. **The "detection latency" line MUST cite a real alert or
   dashboard.** If the answer is "never" the worksheet itself becomes
   a P0 finding before the change ships.
5. **Residual risk MUST be named explicitly** with an acceptance
   owner (Owner or Security archetype) and a linked plan ID for the
   eventual closure.

## Detection-as-Code — runbook for security alerts

Preventive controls are necessary but never sufficient — every
deployed control eventually has a bypass that ships ahead of the
patch. The Detection-as-Code (DaC) pipeline catches that bypass via
log-pattern alerts mapped to MITRE ATT&CK techniques, with rules
under version control and continuous regression-tested against
attacker-replay fixtures.

### Pipeline shape

```
detections/<technique-id>/<rule-id>.yaml
    │
    ├── version-controlled in git
    ├── peer-reviewed via PR
    ├── compiled to target SIEM in CI (Sigma → SPL/KQL/EQL)
    ├── replayed against attacker-fixture corpus in CI
    └── deployed to SIEM via main-branch CD (no console edits, ever)
```

Console-edited rules are forbidden — they bypass review, they erode
the audit trail, and they desynchronize prod from git. If the SIEM
console allows direct edit, the IAM grant for that role is itself
the finding.

### Required metadata on every detection rule

A rule without metadata is a rule the SOC will silence within a
quarter. The framework requires the following fields at minimum:

| Field                 | Purpose                                                    | Reject if missing |
|-----------------------|------------------------------------------------------------|-------------------|
| `rule_id` (UUID)      | Stable cross-SIEM identifier; survives compilation         | yes               |
| `mitre_attack`        | At least one technique ID (e.g. `T1110.003`)               | yes               |
| `severity`            | informational / low / medium / high / critical             | yes               |
| `data_source`         | Which log stream the rule consumes                         | yes               |
| `false_positive_note` | Documented benign scenarios this rule will hit             | yes               |
| `validation_fixture`  | Path to attacker-replay sample that MUST trigger the rule  | yes               |
| `last_validated_utc`  | ISO timestamp of most recent CI fixture pass               | yes               |
| `kill_chain_phase`    | Where in the kill chain this rule sits                     | recommended       |
| `owner_archetype`     | Who triages the alert (typically `security-engineer`)      | recommended       |

### Tuning targets

The pipeline is graded on signal quality, not rule count. Three
operational thresholds are non-negotiable:

| Metric                              | Target                  | Action when out of bound                            |
|-------------------------------------|-------------------------|-----------------------------------------------------|
| False-positive rate per rule        | ≤ 15% (rolling 30-day)  | Tune allowlist, narrow logsource, or retire rule    |
| Time-to-triage on critical alert    | ≤ 10 min during waking  | Re-prioritize rule severity, page on schedule       |
| Alert-to-incident conversion        | ≥ 25% (rolling quarter) | Below this, the rule trains the SOC to ignore alerts|
| Coverage of MITRE techniques used by sector adversaries | ≥ 60% on critical kill-chain phases | Detection-roadmap escalation |

A rule that fires 50 times a day with three true positives is worse
than no rule at all — it consumes an analyst hour and produces alert
fatigue that bleeds into the rules that matter. Retire it or fix it
within one tuning cycle.

### CI replay fixture format

Every rule MUST ship with at least one attacker-replay fixture that
the rule WOULD fire on. CI replays the fixture nightly and on every
rule edit. A rule whose fixture stops triggering is a regression and
the build fails.

```yaml
# fixtures/T1110.003-credential-stuffing/sample-01.yaml
fixture_id: cs-sample-01
technique: T1110.003
rule_under_test: f8a2-credstuff-burst
description: |
  Replays 50 login failures from one IP within 60 seconds against
  unique usernames; rule must fire with severity=high.
expected_outcome:
  rule_fires: true
  severity: high
  enrichment_present: ["source_ip", "user_count", "time_window"]
log_events:
  - { ts: "2026-05-06T14:00:00Z", event: login_failed, ip: 203.0.113.5, user: a@example.com }
  - { ts: "2026-05-06T14:00:01Z", event: login_failed, ip: 203.0.113.5, user: b@example.com }
  # ... 48 more
```

### Anti-patterns specific to detection rules

| Anti-Pattern                                 | Why It's Wrong                                                 | Correct Approach                                          |
|----------------------------------------------|----------------------------------------------------------------|-----------------------------------------------------------|
| Indicator-of-compromise (IOC) regex on IP    | Attacker rotates infrastructure within hours                   | Behavioral pattern (process tree, command-line shape)     |
| Rule deployed without fixture                | Rule may already be broken; nobody knows until breach          | CI gate fails the build if `validation_fixture` missing   |
| Severity=critical on every rule              | Page-fatigue; SOC silences the channel                         | Severity matches blast-radius of the technique, not author worry |
| Missing MITRE mapping                        | Cannot reason about coverage; cannot prioritize                | Mapping required; field validated in CI                   |
| Console hot-fix during incident              | Change desyncs from git; lost on next deploy                   | Open PR even mid-incident; hot-fix via expedited review   |
| Disabling rule "temporarily" without ticket  | Temporarily becomes permanent; control silently absent         | Disable requires ticket + 7-day auto-reenable             |
| Same finding alerted from three rules        | Duplicate pages; analyst confusion                             | Deconfliction layer suppresses overlap; one canonical rule|

## Proof-of-Exploitability — the show-don't-claim discipline

Severity inflation is the most common pattern in security review:
every finding feels critical when you're the one who found it.
The framework's counter is mechanical — every reported vulnerability
ships with a reproducible exploit artifact (curl invocation, test
case, script, or unit test) before the severity field is filled in.
A finding without a PoC is not a finding — it is a hypothesis, and
hypotheses sit at severity `informational` until evidence arrives.

### Why the rule exists

Three distinct failure modes converge on the same defense:

1. **Reviewer-bias inflation.** A reviewer who finds a missing input
   check feels the urgency of a real attack. Without a PoC, the
   urgency translates directly to severity, and the queue fills
   with "criticals" that compete for attention with actual breaches.
2. **Theoretical-attack drift.** A class of vulnerability that is
   exploitable in textbook terms is often unreachable in this code
   path because of an upstream guard. The PoC requirement forces
   the reviewer to walk the path end-to-end before claiming impact.
3. **Patch validation gap.** A fix declared "done" without a PoC
   replay has no proof the fix actually closes the path. The same
   PoC that demonstrated the bug becomes the regression test that
   proves the patch.

### What counts as a PoC

A PoC must be **reproducible by another engineer in under five
minutes** with no privileged setup beyond the standard dev
environment. The format depends on the surface:

| Surface                      | PoC format                                                          | Acceptance criteria                                  |
|------------------------------|---------------------------------------------------------------------|------------------------------------------------------|
| HTTP API endpoint            | `curl` or `httpie` command with full headers and body               | Reviewer pastes, sees the security-relevant response  |
| Web UI / browser-side bug    | Step-by-step replay with screenshot OR Playwright fixture           | Replay reproduces in fresh browser session           |
| Authentication flow          | Two paired calls (credential capture + replay) in a script          | Demonstrates the bypass without real PII             |
| Cryptographic weakness       | Unit test in the project's test harness asserting the bad property  | `pytest` or stack-equivalent; runs in CI             |
| Race / timing flaw           | Reproducer script with explicit thread/process ordering             | Reproduction rate ≥ 50% over 20 runs                 |
| Configuration weakness       | Diff of misconfig + log line showing the consequence                | Misconfig + consequence both verifiable from clone   |
| Theoretical / intuition only | Not a finding — file as backlog hypothesis at severity informational| n/a                                                  |

### Severity gate, anchored to PoC

The framework's severity scale is anchored to what the PoC actually
demonstrates, NOT to the reviewer's worst-case framing.

| Severity     | Required PoC demonstration                                                        |
|--------------|-----------------------------------------------------------------------------------|
| critical     | Unauthenticated remote action with data-exfil OR money-flow OR custody-key path  |
| high         | Authenticated user gains data or capability they should not have                 |
| medium       | Information leak that meaningfully aids the next stage of attack                 |
| low          | Defense-in-depth gap; alone does not produce impact                              |
| informational| Best-practice deviation; no PoC available; tracked in backlog                    |

A reviewer who claims `critical` without a PoC at the
unauthenticated-RCE level has misclassified — re-grade or supply
the PoC. Severity inflation without evidence is itself a reviewer
defect logged in the post-review notes (mirrors the fluency-bias
defense in `code-review-checklist`).

### PoC bundle structure on a finding

Every finding written into a security review report or vulnerability
ticket carries a fixed structure. The PoC field is mandatory; "TBD"
is not a valid value.

```markdown
## Finding SEC-NN — <one-line title>

**Severity:** critical | high | medium | low | informational
**File:** path/to/file.ts:LINE
**MITRE/OWASP mapping:** A01 / LLM06 / T1212 (where applicable)
**Affected versions:** <version-or-commit-range>

### Impact (what the attacker achieves)
<2-4 sentences; quantified blast radius: tenants, accounts, $-amount-bound>

### PoC (reproducible by another engineer)
<curl block / script / pytest case / Playwright fixture>

### Why current controls do not stop it
<the specific guard that should exist; the path that bypasses it>

### Remediation (copy-paste-ready)
<diff or replacement code; cite the existing pattern in this skill>

### Regression test
<the same PoC promoted to a CI-runnable case; merge gate prevents return>
```

### Disclosure discipline

The same PoC discipline applies to outbound disclosure:

1. **Internal first.** Findings against this codebase or its
   adopters never go to a public channel before the patch ships
   AND the upstream PoC is sanitized (real tokens scrubbed, real
   user IDs replaced with fixtures).
2. **Coordinated against third-party.** A finding in a vendor
   library follows that vendor's responsible disclosure policy;
   the framework's own writeup is published only after the vendor's
   patch lands or the disclosure window expires.
3. **No customer data in PoC.** Even sanitized, the PoC must not
   embed actual customer identifiers — replace with `acct_test_*`
   fixtures from the test harness. A leaked PoC that contains a
   real user ID is itself a SEV2 incident under §incident-management.

### Anti-patterns to reject

| Anti-Pattern                                              | Why It's Wrong                                                 | Correct Approach                                  |
|-----------------------------------------------------------|----------------------------------------------------------------|---------------------------------------------------|
| Severity field set before PoC is written                  | Severity becomes anchored to the reviewer's first impression   | Write PoC first; severity is read from impact     |
| "Theoretically exploitable; no time to reproduce"         | Theoretical findings consume queue depth and never close       | File at severity informational; no further action |
| PoC that depends on `localhost` admin bypass              | Demonstrates dev-env path, not prod path                       | Reproduce against staging or sanitized prod-clone |
| Patched without re-running the PoC                        | Patch may have shifted the path, not closed it                 | Replay PoC; result must be the secure response    |
| PoC contains real customer data                           | Disclosure becomes its own incident                            | Replace with fixtures; document the substitution  |
| Two findings share a PoC but neither cites the other      | Duplicate work; remediations diverge                           | One canonical finding; the second cites it        |
| Severity downgrade without re-examining the PoC           | Quiet deflation undoes the severity discipline                 | Downgrade requires PoC delta + named acceptor     |
