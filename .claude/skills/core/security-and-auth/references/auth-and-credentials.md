<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/security-and-auth/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

