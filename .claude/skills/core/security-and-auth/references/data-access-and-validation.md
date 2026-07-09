<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/security-and-auth/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

