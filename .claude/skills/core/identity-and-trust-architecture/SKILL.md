---
name: core-identity-and-trust-architecture
description: >
  Identity and trust doctrine for {{PROJECT_NAME}} — token lifecycle (JWT
  access <= 1h, mandatory refresh rotation), authorization patterns
  (RBAC/ABAC, scope-based, least privilege), service-to-service trust (mTLS,
  signed JWTs, no implicit trust), OAuth/OIDC pitfalls (PKCE, state parameter,
  callback validation, alg=none and audience-check defenses), and zero-trust
  principles. EXTENDS core/security-and-auth for the identity sub-domain. Use
  when designing or reviewing any code that issues, validates, rotates, or
  revokes credentials; assigns or escalates roles/scopes; brokers
  cross-service trust; integrates external IdPs; or touches RLS, ACL, or
  admin-impersonation paths. VETO authority is backed by the
  identity-trust-architect archetype. Identity is the perimeter — once trust
  is granted, every downstream component inherits it.
owner: Identity & Trust Architect (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-security-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 2
risk_class: high
stack: [typescript, node]
context_budget_tokens: 1400
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 2}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 2}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)identity|oauth|sso|trust"}
---

# Identity and Trust Architecture

Identity is the perimeter. Once a token is issued, a role is assigned, or a
service-to-service call is trusted, every downstream component inherits that
decision — silently, transitively, and usually without re-checking. Get it
wrong and the audit trail becomes fiction: the logs show "user X did Y"
when in fact "anyone holding a year-old refresh token did Y as user X."
This skill codifies the rules that prevent that drift. Violations of the
hard rules below are VETO-floor candidates: post-Wave-1c, the identity-trust-
architect archetype's sign-off becomes mandatory on any L3+ change touching
authentication, authorization, token issuance/validation, role hierarchy,
S2S trust, or external-IdP integration. In v1.14.0 (pre-Wave-1c), the
`identity-trust-architect` slug is NOT yet in
`_lib/agent_frontmatter.VETO_FLOOR_ROLES` — the atomic add lands in the
Wave 1c GPG sentinel ceremony alongside the corresponding agent file (per
S90 P0-01 invariant). Until that ceremony ships, identity changes route
through `security-engineer` (which IS VETO-floor) plus Owner gate.

## What This Skill Is (and isn't)

This skill **EXTENDS** `core/security-and-auth` for the identity sub-domain.
The parent skill covers the broader security posture (OWASP Top 10, CORS,
WebSocket auth, CSRF, RLS, rate limiting). This skill focuses tightly on
the **identity and trust** layer:

- **In scope:** token lifecycle (issuance, validation, rotation,
  revocation), authorization model design (RBAC/ABAC/ReBAC/scope-based),
  service-to-service trust (mTLS, signed tokens, mesh patterns), OAuth/
  OIDC flow hardening, role hierarchy + privilege escalation prevention,
  zero-trust principles, IdP integration pitfalls, session management,
  password/credential lifecycle (rotation, breach response).
- **Not in scope (deferred to parent skill):** transport-level CORS
  rules, network rate limiting, OWASP injection categories, RLS DDL,
  webhook HMAC verification, generic timing-safe comparison guidance.
- **Not in scope (deferred to siblings):** detection rules for identity
  abuse (`core/security-and-auth` §Detection-as-Code + threat-detection-
  engineer archetype), incident response when an identity is compromised
  (`core/incident-management` + incident-commander archetype), audit-
  log shape for identity events (`core/observability-and-ops`).

The archetype's VETO authority codifies this skill's doctrine into
production decisions. A merge that violates a hard rule below ships
only with explicit Owner override + ADR amendment + this skill's
amendment — not with a reviewer waiver.

## Threat Model

Identity systems face a specific adversary playbook. Every design
decision in this skill maps to one or more of the following threat
categories. A change that does not name which threat it mitigates (or
which compensating control it adds when the primary control regresses)
fails Pass-1 review.

| Threat | Concrete scenario | Primary defense | Compensating control |
|--------|-------------------|-----------------|----------------------|
| **Token theft** | Refresh token harvested from `localStorage` via XSS, then replayed for months | Short access TTL ≤ 1h + refresh rotation on use + refresh binding to device fingerprint | Anomaly detection on refresh-from-new-IP; revoke on password change |
| **Token replay** | Captured access token replayed after legitimate user logged out | Token binding (cnf claim) + per-token jti tracked in revocation list for window of TTL | Sliding-window monitor on (jti, IP) pairs; force re-auth on mismatch |
| **Privilege escalation (vertical)** | Read-scope key calls `POST /admin/*`; client-supplied role flag honored server-side | Server-side scope/role check from verified JWT claim; never trust client-supplied role | Periodic privilege-creep audit; alert on role changes outside change-window |
| **Privilege escalation (horizontal / IDOR)** | Authenticated user passes `user_id` in body to read another user's data | Resource ownership check: `auth.uid() == resource.owner_id` enforced server-side | RLS at DB layer (defense-in-depth); audit-log on cross-user reads |
| **Confused deputy** | Service A calls Service B with A's own credentials but on behalf of user U; B grants A's permissions, not U's | Token-exchange (RFC 8693) or on-behalf-of flow; B re-validates token has user U's scope, not A's | Trace-ID propagation + log review; alert on missing on-behalf-of claim |
| **Session fixation** | Attacker sets victim's session ID before login; victim authenticates, attacker now holds authenticated session | Rotate session ID on every privilege-level change (login, MFA-step-up, role-change) | Session-fingerprint mismatch detection; force re-auth on UA/IP discontinuity |
| **OAuth callback injection** | Attacker initiates OAuth flow, intercepts auth code via open redirector, redeems for victim's tokens | PKCE (code_verifier bound to session) + state parameter (CSRF + flow integrity) + strict redirect_uri allowlist | Single-use auth code; reject code redemption from IP that didn't initiate flow |
| **JWT validation bypass** | `alg=none` accepted by lazy verifier; missing audience check accepts tokens minted for a different service | Reject `alg=none`, require explicit alg allowlist (`RS256`/`ES256`); always verify `aud` and `iss` | Library version pinning + behavioral test-fixture for known-bad tokens |
| **Implicit S2S trust** | Service B trusts any caller from internal subnet; lateral-movement after one container compromise → cluster-wide RCE | mTLS or JWT-verified S2S regardless of network position; zero-trust default-deny | Service mesh sidecar enforcement; deny audit-log on plaintext internal calls |
| **Privilege creep / role explosion** | "Temporary" admin grant from 18 months ago still active; 47 distinct admin-flavored roles, no hierarchy | Time-bounded grants (auto-expire + renewal ticket); role hierarchy with composition, not flat enumeration | Quarterly access review; orphaned-grant detection job |
| **Refresh-token abuse** | Stolen refresh token used in parallel with legitimate user; both succeed because rotation isn't enforced | Refresh rotation on every use + breach detection on parallel-use of same refresh family | Force full re-auth on any rotation chain mismatch (RFC 6749 §10.4 "automatic detection") |
| **OAuth `prompt=none` silent re-auth abuse** | Attacker who can drop a request from victim's browser silently mints a fresh access token without user interaction | Validate session cookie + bind `prompt=none` to existing CSRF token + log silent re-auth events | Rate-limit silent re-auth per session; alert on burst patterns |

## Hard Rules

These rules are **VETO-floor candidates**. The mechanical VETO authority
materializes only after Wave 1c lands the `identity-trust-architect` agent
file + frozenset entry atomically (see `wave-1c-veto-floor-matrix.md`).
**In v1.14.0 (pre-Wave-1c)**, violations route through `security-engineer`
+ Owner gate (the `security-engineer` archetype is the active VETO authority
for identity surface until Wave 1c lands). **Post-Wave-1c**, a merge that
violates any rule below requires explicit Owner override + ADR amendment +
this skill's amendment — not a reviewer waiver. Each rule cites the threat
it closes.

1. **Access tokens TTL ≤ 1 hour.** Long-lived access tokens turn one-shot
   theft into persistent compromise. Closes: token theft, token replay.
   Reference: ADR-052 §VETO_FLOOR_ROLES (identity-trust-architect).
2. **Refresh tokens MUST rotate on every use.** Each redemption invalidates
   the previous refresh and issues a new one (RFC 6749 §10.4 "automatic
   detection of token reuse"). Parallel use of two members of the same
   rotation chain → revoke entire family + force re-auth. Closes: refresh-
   token abuse, token theft.
3. **Refresh tokens MUST be bound** to either device fingerprint, client
   ID + secret, or DPoP/mTLS proof-of-possession. A bearer-only refresh
   is the same as a long-lived access token. Closes: token theft.
4. **JWT verification MUST reject `alg=none`** and MUST use an explicit
   allowlist of allowed algorithms (typically `RS256` or `ES256`).
   `HS256` is acceptable only for symmetric-key contexts where issuer
   and verifier are the same trust boundary. Closes: JWT validation
   bypass.
5. **JWT verification MUST validate `aud` (audience), `iss` (issuer), and
   `exp` (expiry).** Missing any of these = token from any other system
   in your ecosystem could be replayed against this service. Closes:
   JWT validation bypass, confused deputy.
6. **Authorization decisions MUST read role/scope from the verified
   token**, never from the request body, query string, header, or
   client-supplied form field. Closes: privilege escalation (vertical).
7. **Resource access MUST verify ownership server-side** —
   `caller.uid == resource.owner.uid` for user-owned data, regardless
   of what the client sent. Closes: privilege escalation (horizontal /
   IDOR).
8. **Service-to-service calls MUST authenticate** via mTLS, signed JWT,
   or signed HMAC-on-canonical-body. Network position (internal subnet,
   same VPC, same cluster) is NOT authentication. Closes: implicit S2S
   trust, lateral movement.
9. **OAuth public clients MUST use PKCE** (RFC 7636). Confidential
   clients SHOULD use PKCE (defense-in-depth). The implicit flow is
   forbidden — deprecated by OAuth 2.1. Closes: OAuth callback
   injection.
10. **OAuth flows MUST validate the `state` parameter** server-side
    against the session that initiated the flow. Closes: OAuth CSRF,
    callback injection.
11. **OAuth `redirect_uri` MUST be matched against an exact allowlist.**
    Wildcard, prefix-match, and substring-match all enable open
    redirector → token theft chains. Closes: OAuth callback injection.
12. **Session IDs MUST rotate on privilege change** — login, logout,
    MFA step-up, role change, password reset. Closes: session
    fixation.
13. **Privilege grants MUST be time-bounded** with explicit expiry +
    renewal ticket. "Temporary" admin without an expiry timestamp is a
    finding. Closes: privilege creep.
14. **Default deny for authorization.** Missing policy = no access. Roles
    are additive composition over a deny-by-default base; explicit deny
    must override implicit allow. Closes: privilege escalation
    (vertical).
15. **Identity-system changes are VETO-floor candidates.** Any change to
    token issuance, validation, refresh, revocation, role hierarchy, scope
    definitions, or S2S trust mechanism requires `identity-trust-architect`
    sign-off **post-Wave-1c**; **pre-Wave-1c** (v1.14.0), `security-engineer`
    + Owner gate cover this surface. Reviewer waiver insufficient in either
    state. Reference: ADR-052 amendment shipped via PLAN-074 Wave 1b
    (architectural record); frozenset add lands atomically in Wave 1c
    (mechanical enforcement).

## Token Lifecycle

The token lifecycle is the single most consequential design surface in
identity. Get any of issuance, validation, rotation, or revocation
wrong and every downstream control inherits the failure.

### Issuance

```typescript
type TokenPair = { accessToken: string; refreshToken: string; refreshJti: string; familyId: string };

// CORRECT — short-TTL access + bound refresh; JTIs generated BEFORE signing.
// `existingFamilyId` distinguishes initial issuance (creates family) from
// rotation issuance (extends existing family chain — see rotateRefreshToken).
async function issueTokenPair(
  user: User,
  deviceFingerprint: string,
  existingFamilyId?: string,        // undefined = initial; defined = rotation
  presetRefreshJti?: string,        // CAS pre-claim: rotation passes the
                                    // already-swapped JTI; initial leaves undef
): Promise<TokenPair> {
  // Both JTIs generated as variables BEFORE signing — JWTs are encoded
  // strings, you cannot read claim values back from `signJWT(...)`'s return.
  const accessJti = crypto.randomUUID();
  const refreshJti = presetRefreshJti ?? crypto.randomUUID();
  const familyId = existingFamilyId ?? crypto.randomUUID();

  const accessToken = await signJWT({
    sub: user.id,
    aud: AUD_API,                  // Hard rule #5
    iss: ISS_AUTH,
    exp: nowSeconds() + 60 * 60,   // Hard rule #1: ≤ 1h
    iat: nowSeconds(),
    jti: accessJti,                // pre-generated; tracked in revocation list if needed
    scope: user.scopes.join(" "),  // server-set, never client-supplied
    cnf: { jkt: hashThumbprint(deviceFingerprint) }, // Hard rule #3
  }, JWT_PRIVATE_KEY, { algorithm: "RS256" }); // Hard rule #4

  const refreshToken = await signJWT({
    sub: user.id,
    aud: AUD_REFRESH,
    iss: ISS_AUTH,
    exp: nowSeconds() + 30 * 24 * 60 * 60, // 30d MAX
    iat: nowSeconds(),
    jti: refreshJti,                // pre-generated; identifies this rotation chain member
    family: familyId,               // Hard rule #2: rotation chain — preserved across rotations
    cnf: { jkt: hashThumbprint(deviceFingerprint) }, // Hard rule #3
  }, JWT_PRIVATE_KEY, { algorithm: "RS256" });

  if (existingFamilyId === undefined) {
    // Initial issuance: create the family record. Rotation callers update
    // the existing family's activeJti themselves after this returns.
    await db.refreshFamily.create({
      id: familyId,
      userId: user.id,
      deviceFingerprint: hashThumbprint(deviceFingerprint),
      activeJti: refreshJti,        // use the variable, NOT refreshToken.jti (string can't dot-access)
      createdAt: now(),
    });
  }

  return { accessToken, refreshToken, refreshJti, familyId };
}

// WRONG — long-lived access + unbound refresh
async function issueTokenPair_BAD(user: User): Promise<TokenPair> {
  const accessToken = await signJWT({
    sub: user.id,
    role: user.role,                          // role embedded but no aud
    exp: nowSeconds() + 30 * 24 * 60 * 60,    // 30d access — VIOLATES #1
  }, SECRET, { algorithm: "HS256" });
  const refreshToken = crypto.randomBytes(32).toString("hex"); // bearer; VIOLATES #3
  return { accessToken, refreshToken };
}
```

### Validation

```typescript
// CORRECT — strict alg allowlist + aud/iss/exp + cnf check
async function verifyAccessToken(
  token: string,
  expectedAud: string,
  presentedDeviceFingerprint: string,
): Promise<JWTClaims> {
  const { header, payload } = await jwt.verify(token, JWT_PUBLIC_KEY, {
    algorithms: ["RS256"],          // Hard rule #4: explicit allowlist
    audience: expectedAud,          // Hard rule #5
    issuer: ISS_AUTH,               // Hard rule #5
    // exp/nbf checked by library
  });

  // Hard rule #3: confirm device binding
  if (payload.cnf?.jkt !== hashThumbprint(presentedDeviceFingerprint)) {
    throw new UnauthorizedError("token_binding_mismatch");
  }

  // Revocation list (jti → revoked_at). Optional for short-TTL access,
  // mandatory for refresh.
  if (await revocationList.has(payload.jti)) {
    throw new UnauthorizedError("revoked");
  }

  return payload;
}

// WRONG — accepts alg=none + missing aud/iss
async function verifyAccessToken_BAD(token: string): Promise<JWTClaims> {
  // Library default may accept alg=none if not constrained — VIOLATES #4
  return jwt.decode(token); // not even verifying signature
}
```

### Rotation

```typescript
// CORRECT — single-use refresh, breach detection on chain conflict
async function rotateRefreshToken(
  presentedRefresh: string,
  presentedDeviceFingerprint: string,
): Promise<TokenPair> {
  const claims = await verifyRefreshToken(presentedRefresh, presentedDeviceFingerprint);
  const family = await db.refreshFamily.findById(claims.family);

  if (!family || family.userId !== claims.sub) {
    throw new UnauthorizedError("family_unknown");
  }

  // Hard rule #2: parallel use of same family = breach.
  // The check + revoke + update MUST be atomic — two concurrent redemptions
  // of the same active refresh token can both pass a non-transactional check
  // before either update fires. Use compare-and-swap (UPDATE ... WHERE
  // activeJti = ?) inside a transaction so exactly ONE redemption wins.
  const newRefreshJti = crypto.randomUUID();
  const claimedActiveJti = claims.jti;

  // Atomic compare-and-swap: claim the rotation slot for THIS redemption.
  // If activeJti has already moved on, swappedRows = 0 and we treat it as breach.
  const swappedRows = await db.refreshFamily.compareAndSwap({
    where: { id: claims.family, activeJti: claimedActiveJti },
    set: { activeJti: newRefreshJti, rotatedAt: now() },
  });

  if (swappedRows === 0) {
    // Either family unknown, owner mismatch, OR another redemption already
    // claimed the slot — in all cases, breach posture: revoke + alert.
    const family = await db.refreshFamily.findById(claims.family);
    if (family) {
      await revokeFamily(family.id);
      await audit.emit({
        kind: "refresh_chain_breach",
        severity: "high",
        userId: family.userId,
        familyId: family.id,
        presentedJti: claims.jti,
        activeJti: family.activeJti,
      });
    }
    throw new UnauthorizedError("rotation_chain_breach");
  }

  // We won the CAS. Issue new pair WITHIN the same family chain
  // (existingFamilyId preserves the family ID; issueTokenPair will NOT
  // create a new family record). The newRefreshJti we used in the CAS MUST
  // be the same one signed into the new refresh JWT — so we generate it
  // BEFORE the CAS and pass it in.
  const next = await issueTokenPair(
    await db.user.findById(claims.sub),
    presentedDeviceFingerprint,
    claims.family,                   // CRITICAL: preserve the family chain
    newRefreshJti,                   // CRITICAL: pre-claimed JTI from CAS above
  );
  return next;
}

// WRONG — refresh reusable; no chain detection
async function rotateRefreshToken_BAD(presentedRefresh: string): Promise<TokenPair> {
  const claims = jwt.decode(presentedRefresh);  // unverified
  return issueTokenPair_BAD(await db.user.findById(claims.sub));
  // Old refresh still valid; attacker with stolen copy gets perpetual access.
}
```

### Revocation

Revocation is the lever that closes a breach. If you cannot revoke a
token within the access-TTL window, the breach window is unbounded.

| Trigger | What revokes | Latency requirement |
|---------|--------------|---------------------|
| User-initiated logout | Current session's refresh family + access jti | < access TTL (≤ 1h) |
| Password change | All refresh families for user; force re-auth on all devices | Immediate (push revocation list) |
| Detected breach (chain mismatch, anomaly) | Affected refresh family + alert | Immediate (synchronous in rotate path) |
| User account deactivation | All sessions + API keys + service grants | Immediate; subsequent calls return 401 |
| Stolen device | All refresh families bound to that device fingerprint | < 5 min from report |

### Access vs refresh TTL ratios

The access/refresh ratio is a deliberate trade-off, not an arbitrary
default. The framework's calibration:

| Profile | Access TTL | Refresh TTL | When to use |
|---------|------------|-------------|-------------|
| **High-assurance** (admin, money-flow, custody) | 5 min | 4h | Privileged consoles, admin APIs |
| **Standard** (most user-facing APIs) | 15-60 min | 7-30d | SaaS dashboards, API clients |
| **Long-lived client** (mobile, native, IoT) | 60 min (HARD CAP) | 90d | Low-friction reauth needs — never exceed 60 min on access |
| **Service-to-service** | 5-15 min | N/A — re-mint via client_credentials per call window | Inter-service trust |

Access TTL > 1h is **exception-class** under Hard Rule #1. It requires an
Owner-signed ADR explicitly waiving the rule for the specific surface; token
binding (`cnf` claim) + short revocation propagation latency are the
**minimum** mitigations the ADR must enforce, NOT a substitute for the rule.
The default is and remains ≤ 1h. Adopters considering >1h should instead
restructure: shorter access + faster refresh + token binding gives the same
UX without the security-budget concession.

## Authorization Patterns

### Principle of Least Privilege (default)

Every grant is the smallest scope that completes the user's task.
"Just give them admin so it works" is the most expensive line in the
incident postmortem.

### RBAC — Role-Based Access Control

```typescript
// CORRECT — role hierarchy with composition, server-side enforcement
type Role = "viewer" | "editor" | "admin" | "owner";

const ROLE_HIERARCHY: Record<Role, ReadonlySet<Permission>> = {
  viewer: new Set(["read"]),
  editor: new Set(["read", "write"]),
  admin: new Set(["read", "write", "delete", "manage_users"]),
  owner: new Set(["read", "write", "delete", "manage_users", "billing", "transfer_ownership"]),
};

function hasPermission(role: Role, perm: Permission): boolean {
  return ROLE_HIERARCHY[role].has(perm);
}

// Authorization check — Hard rule #6 (read role from verified token)
app.post("/users/:id/delete", async (c) => {
  const claims = c.get("jwtClaims"); // already verified by middleware
  if (!hasPermission(claims.role, "manage_users")) {
    return c.json({ error: "forbidden" }, 403);
  }
  // Hard rule #7: server-side ownership check
  const target = await db.user.findById(c.req.param("id"));
  if (target.tenantId !== claims.tenantId) {
    return c.json({ error: "forbidden" }, 403);
  }
  return deleteUser(target);
});

// WRONG — role from request body; no tenant check
app.post("/users/:id/delete", async (c) => {
  const { role } = await c.req.json();          // VIOLATES #6
  if (role === "admin") return deleteUser(...); // attacker sets role:admin
});
```

### ABAC — Attribute-Based Access Control

When RBAC's flat-role model collapses (10+ roles, frequent role-
explosion requests), shift to ABAC: decisions read attributes (user
+ resource + environment) against a policy.

```typescript
// CORRECT — ABAC policy via OPA / Cedar / casbin
const policy = `
  permit (
    principal.role == "editor",
    action == "write",
    resource.tenant_id == principal.tenant_id,
    resource.created_at >= now() - duration("30d"),
    environment.time_of_day in ["business_hours"]
  );
`;
// Engine evaluates; service consumes allow/deny only.
```

### Scope-Based (OAuth 2.0)

```typescript
// CORRECT — scope-based for API clients
function requireScope(...required: string[]): Middleware {
  return async (c, next) => {
    const claims = c.get("jwtClaims");
    const granted = (claims.scope || "").split(" ");
    for (const r of required) {
      if (!granted.includes(r)) return c.json({ error: "insufficient_scope" }, 403);
    }
    await next();
  };
}

app.post("/v1/withdrawals", requireScope("withdraw:write"), withdrawHandler);
app.get("/v1/withdrawals", requireScope("withdraw:read"), listHandler);
```

### Role hierarchy: composition, not flat enumeration

A 47-role flat list is a privilege-creep symptom. Roles compose:

```
owner ⊃ admin ⊃ editor ⊃ viewer
                 │
                 └── billing-admin (orthogonal capability)
```

When a stakeholder requests a new role, ask: "is this a hierarchy
extension or an orthogonal capability?" If neither, the request is
likely permission-shaped — use a permission flag, not a new role.

## Service-to-Service Trust

Network position is not authentication. The internal-subnet-implies-
trust pattern was the root cause of dozens of high-profile breaches
where one compromised container produced cluster-wide impact.

### mTLS pattern

```yaml
# Service mesh (e.g. Istio, Linkerd) enforces mTLS by default
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict-mtls
  namespace: production
spec:
  mtls:
    mode: STRICT  # reject any plaintext call
```

Every pod-to-pod call is mutually authenticated by the sidecar. Service
identity is the SPIFFE ID (`spiffe://cluster.local/ns/prod/sa/payment-svc`),
not the source IP.

### Signed JWT pattern (no mesh)

```typescript
// CORRECT — service-to-service with signed JWT
async function callDownstream(endpoint: string, body: unknown): Promise<Response> {
  const s2sToken = await signS2SJWT({
    iss: SERVICE_IDENTITY,
    aud: endpoint,
    exp: nowSeconds() + 5 * 60,         // short-lived; re-mint per call
    iat: nowSeconds(),
    jti: crypto.randomUUID(),
  }, SERVICE_PRIVATE_KEY, { algorithm: "ES256" });
  return fetch(endpoint, {
    headers: { Authorization: `Bearer ${s2sToken}` },
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Receiving service:
async function verifyS2SCaller(token: string, expectedAud: string): Promise<S2SClaims> {
  const claims = await jwt.verify(token, ISSUER_KEYSTORE, {
    algorithms: ["ES256"],
    audience: expectedAud,
    issuer: ALLOWED_INTERNAL_ISSUERS, // explicit allowlist
  });
  if (!ALLOWED_S2S_CALLERS.has(claims.iss)) {
    throw new UnauthorizedError("s2s_caller_not_allowlisted");
  }
  return claims;
}
```

### Confused-deputy mitigation: Token Exchange (RFC 8693)

When Service A receives a request from User U, then calls Service B
on behalf of U, B must NOT grant A's permissions; it must grant U's.

```typescript
// CORRECT — A exchanges U's access token for an on-behalf-of token
// scoped to B, then calls B with that token. B sees user_id=U + scope
// derived from U's grant.
const obo = await tokenExchange({
  grant_type: "urn:ietf:params:oauth:grant-type:token-exchange",
  subject_token: userAccessToken,
  subject_token_type: "urn:ietf:params:oauth:token-type:access_token",
  audience: SERVICE_B,
});
await fetch(SERVICE_B_URL, { headers: { Authorization: `Bearer ${obo.access_token}` } });

// WRONG — A calls B with A's own service credentials, body says user_id=U
// → B grants A's permissions but logs as user U. Confused deputy.
```

## OAuth/OIDC Pitfalls

OAuth/OIDC is where most identity breaches happen — not in the abstract
protocol, but in the seven-paragraph footnote each implementer ignores.

### PKCE (RFC 7636) — mandatory for public clients

PKCE prevents authorization-code interception. The `code_verifier` MUST stay
on the side that ultimately redeems the code. Two architectures, two storage
strategies — DO NOT mix them.

#### Example A — SPA with BFF (Backend-For-Frontend) — PREFERRED

The BFF generates and stores the verifier server-side, tied to a pending-auth
session. The browser never sees the verifier; it only carries an HttpOnly
session cookie.

```typescript
// BFF /auth/login — server-side verifier generation + storage
app.get("/auth/login", async (c) => {
  const codeVerifier = base64UrlEncode(crypto.randomBytes(32));
  const codeChallenge = base64UrlEncode(
    crypto.createHash("sha256").update(codeVerifier).digest()
  );
  const csrfToken = crypto.randomUUID();
  // Verifier stored server-side, keyed by session ID:
  await pendingAuthStore.set(c.session.id, {
    codeVerifier,                            // never leaves the BFF
    csrfToken,
    expiresAt: Date.now() + 5 * 60 * 1000,   // 5-min pending window
  });
  return c.redirect(`${AUTH_URL}?` + new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: BFF_CALLBACK_URL,          // BFF endpoint, not browser
    response_type: "code",
    scope: "openid profile",
    state: csrfToken,                         // Hard rule #10
    code_challenge: codeChallenge,            // Hard rule #9
    code_challenge_method: "S256",
  }));
});

// BFF /auth/callback — server-side redemption with stored verifier
app.get("/auth/callback", async (c) => {
  const { code, state } = c.req.query();
  const pending = await pendingAuthStore.get(c.session.id);
  if (!pending || state !== pending.csrfToken) {
    return c.json({ error: "state_mismatch" }, 400);
  }
  const tokens = await fetch(TOKEN_ENDPOINT, {
    method: "POST",
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: BFF_CALLBACK_URL,
      client_id: CLIENT_ID,
      code_verifier: pending.codeVerifier,    // server-stored, never browser
    }),
  });
  await pendingAuthStore.delete(c.session.id);
  // Tokens stay on BFF; browser only learns of the established session
  await sessionStore.set(c.session.id, { tokens, userId: /* ... */ });
  return c.redirect("/app");
});
```

#### Example B — SPA without backend (residual XSS risk acknowledged)

For SPAs that genuinely cannot have a BFF, the browser must hold the verifier.
This is the next-best option — NOT the recommended one. Document the residual
risk explicitly and consider migrating to a BFF.

```typescript
// Browser /login — Web Crypto API (NOT Node crypto), verifier + state both
// stored in sessionStorage (XSS-exposed; see residual-risk note below)
async function startLogin(): Promise<void> {
  // Web Crypto: getRandomValues for entropy, subtle.digest for SHA-256
  const verifierBytes = new Uint8Array(32);
  crypto.getRandomValues(verifierBytes);
  const codeVerifier = base64UrlEncodeUint8(verifierBytes);

  const challengeBuf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(codeVerifier),
  );
  const codeChallenge = base64UrlEncodeUint8(new Uint8Array(challengeBuf));

  // State must also be browser-generated and persisted alongside verifier
  const stateBytes = new Uint8Array(16);
  crypto.getRandomValues(stateBytes);
  const stateToken = base64UrlEncodeUint8(stateBytes);

  // BOTH verifier AND state held in sessionStorage (single-use, browser-bound)
  sessionStorage.setItem("pkce_verifier", codeVerifier);
  sessionStorage.setItem("oauth_state", stateToken);

  window.location.href = `${AUTH_URL}?` + new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: BROWSER_CALLBACK_URL,        // browser route (not BFF)
    response_type: "code",
    scope: "openid profile",
    state: stateToken,                          // Hard rule #10 (browser-bound)
    code_challenge: codeChallenge,              // Hard rule #9
    code_challenge_method: "S256",
  });
}

// Browser /callback — validate state BEFORE redemption (browser-bound check)
async function handleCallback(returnedCode: string, returnedState: string): Promise<void> {
  const expectedState = sessionStorage.getItem("oauth_state");
  sessionStorage.removeItem("oauth_state");     // single-use

  if (!expectedState || returnedState !== expectedState) {
    // Hard rule #10 — equivalent of server-side state validation, scoped to browser
    throw new Error("oauth_state_mismatch");
  }

  const codeVerifier = sessionStorage.getItem("pkce_verifier");
  sessionStorage.removeItem("pkce_verifier");   // single-use
  if (!codeVerifier) throw new Error("missing_pkce_verifier");

  const tokens = await fetch(TOKEN_ENDPOINT, {
    method: "POST",
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code: returnedCode,
      redirect_uri: BROWSER_CALLBACK_URL,
      client_id: CLIENT_ID,
      code_verifier: codeVerifier,              // proves possession
    }),
  });
  // CRITICAL: tokens now live in browser memory/storage — XSS = full account takeover
}
```

**Residual risk (Example B):** `sessionStorage` is exposed to ANY same-origin
JavaScript. A single XSS finding compromises the entire authentication. The
attacker reads the verifier (during login flow) or the resulting tokens
(post-redemption) without any further escalation. This is the architectural
cost of running an SPA without a backend; if the application surface justifies
it (e.g. a static-site widget with read-only public data), accept it
explicitly and limit token scopes accordingly. Otherwise, **introduce a BFF
and use Example A.**

### State parameter — CSRF + flow integrity

```typescript
// CORRECT — state bound to session, validated on callback
app.get("/auth/login", async (c) => {
  const csrf = crypto.randomUUID();
  await sessionStore.set(c.session.id, { pendingAuthState: csrf });
  return c.redirect(`${AUTH_URL}?state=${csrf}&...`);
});

app.get("/auth/callback", async (c) => {
  const { state, code } = c.req.query();
  const session = await sessionStore.get(c.session.id);
  if (state !== session?.pendingAuthState) {  // Hard rule #10
    return c.json({ error: "state_mismatch" }, 400);
  }
  await sessionStore.update(c.session.id, { pendingAuthState: null });
  return redeemCode(code);
});

// WRONG — state ignored on callback (CSRF wide open)
app.get("/auth/callback", async (c) => {
  const { code } = c.req.query();           // VIOLATES #10
  return redeemCode(code);
});
```

### redirect_uri exact-match allowlist

```typescript
// CORRECT — exact match only
const ALLOWED_REDIRECTS = new Set([
  "https://app.example.com/auth/callback",
  "https://staging.example.com/auth/callback",
  "http://localhost:3000/auth/callback", // dev only; gate by NODE_ENV
]);

function validateRedirect(uri: string): boolean {
  return ALLOWED_REDIRECTS.has(uri);
}

// WRONG — any of these enable token theft via open redirector
function validateRedirect_BAD1(uri: string) {
  return uri.startsWith("https://example.com/"); // attacker.com/example.com/...
}
function validateRedirect_BAD2(uri: string) {
  return new URL(uri).hostname.endsWith("example.com"); // evil.example.com
}
function validateRedirect_BAD3(uri: string) {
  return uri.includes("example.com"); // attacker.com?redir=example.com
}
```

### Token validation hardening checklist

A reviewer MUST tick every box for every JWT verification path:

- [ ] `alg` parameter is in an explicit allowlist (no `none`)
- [ ] `aud` is checked against this service's expected audience
- [ ] `iss` is checked against an explicit issuer allowlist
- [ ] `exp` is checked (library default; verify the library does this)
- [ ] `nbf` is checked if present
- [ ] `iat` is sanity-checked (not in the future, not absurdly old)
- [ ] Signature is verified with the **issuer's** public key (looked
      up by `kid`), not a key the token specifies
- [ ] `kid` does NOT permit URL fetch from token-controlled URI
      (`jku`/`x5u` headers MUST be ignored or restricted to allowlist)
- [ ] Critical (`crit`) header members are understood; reject unknown
- [ ] Token-binding claim (`cnf`) is verified if expected

### OAuth flow selection guide

| Client type | Flow | Token storage | Notes |
|-------------|------|---------------|-------|
| Web app, has backend | Authorization Code + PKCE | Server-side session + HttpOnly cookies | Standard for SaaS |
| **SPA with BFF** (preferred) | Authorization Code + PKCE via BFF | Tokens stay on BFF; browser holds HttpOnly session cookie only | PKCE Example A above; verifier never leaves BFF |
| **SPA without backend** | Authorization Code + PKCE direct | `sessionStorage` (XSS-exposed; document residual risk) | PKCE Example B above; consider migrating to BFF |
| Native / mobile | Authorization Code + PKCE + system browser | Platform secure storage (Keychain/Keystore) | Use AppAuth or platform-native |
| Backend service | Client Credentials | Encrypted secret store + short-lived token cache | S2S; no user identity |
| IoT / device | Device Authorization (RFC 8628) | Device-paired credential | User confirms on second device |
| Implicit flow | **NEVER** | n/a | Removed in OAuth 2.1 |
| Resource Owner Password | **NEVER** (except legacy migration) | n/a | Anti-pattern by design |

## WRONG / CORRECT Examples

### 1. JWT validation: alg=none and missing audience

```typescript
// WRONG — accepts any token, including alg=none forgeries
function verify_BAD(token: string): Claims {
  return jwt.decode(token); // no signature check, no aud, no iss
}

// CORRECT — strict allowlist + aud + iss + exp
function verify(token: string): Claims {
  return jwt.verify(token, PUBLIC_KEY, {
    algorithms: ["RS256"],
    audience: "https://api.example.com",
    issuer: "https://auth.example.com",
  });
}
```

### 2. Long-lived token vs rotated refresh

```typescript
// WRONG — 30-day access token; one theft = month-long compromise
const access = jwt.sign({ sub: u.id }, SECRET, { expiresIn: "30d" });

// CORRECT — 1h access + rotated refresh + binding
const { access, refresh } = await issueTokenPair(u, deviceFingerprint);
// access exp = 1h; refresh rotates on use; refresh bound to device.
```

### 3. Authorization from request body vs from token

```typescript
// WRONG — attacker sets is_admin in body
app.post("/admin/action", async (c) => {
  const { is_admin } = await c.req.json();   // VIOLATES Hard rule #6
  if (is_admin) return doAdminThing();
});

// CORRECT — read from verified JWT claim
app.post("/admin/action", async (c) => {
  const claims = c.get("jwtClaims");
  if (claims.role !== "admin") return c.json({ error: "forbidden" }, 403);
  return doAdminThing();
});
```

### 4. Horizontal privilege escalation (IDOR)

```typescript
// WRONG — trusts user_id from body
app.get("/users/:id/orders", async (c) => {
  return c.json(await db.orders.findByUser(c.req.param("id"))); // VIOLATES #7
});

// CORRECT — server-side ownership check
app.get("/users/:id/orders", async (c) => {
  const claims = c.get("jwtClaims");
  if (c.req.param("id") !== claims.sub && !hasPermission(claims.role, "view_others")) {
    return c.json({ error: "forbidden" }, 403);
  }
  return c.json(await db.orders.findByUser(c.req.param("id")));
});
```

### 5. OAuth callback injection via state-parameter neglect

```typescript
// WRONG — state ignored; attacker initiates flow with their own state,
// tricks victim into completing it; tokens deposit in attacker's session.
app.get("/auth/callback", (c) => redeemCode(c.req.query("code")));

// CORRECT — state bound to session and validated
app.get("/auth/callback", async (c) => {
  const session = await sessionStore.get(c.session.id);
  if (c.req.query("state") !== session?.pendingAuthState) {
    return c.json({ error: "state_mismatch" }, 400);
  }
  return redeemCode(c.req.query("code"));
});
```

### 6. Implicit S2S trust based on internal network position

```typescript
// WRONG — internal subnet implies trust
app.post("/internal/charge", async (c) => {
  if (!isInternalIP(c.req.header("x-forwarded-for"))) {  // VIOLATES #8
    return c.json({ error: "external" }, 403);
  }
  return charge(await c.req.json());
});

// CORRECT — JWT-verified S2S regardless of network position
app.post("/internal/charge", async (c) => {
  const auth = c.req.header("authorization");
  if (!auth?.startsWith("Bearer ")) return c.json({ error: "unauth" }, 401);
  const claims = await verifyS2SCaller(auth.slice(7), "https://billing.internal");
  if (!ALLOWED_S2S_CALLERS.has(claims.iss)) return c.json({ error: "unauth" }, 401);
  return charge(await c.req.json());
});
```

### 7. God-role vs scoped permissions

```typescript
// WRONG — single "admin" role grants everything; one stolen admin = total compromise
const ROLES = { admin: ["*"] };

// CORRECT — composable scopes
const ROLES: Record<string, Set<Permission>> = {
  user: new Set(["read:own"]),
  billing_admin: new Set(["read:any", "write:billing"]),
  ops_admin: new Set(["read:any", "write:config"]),
  super_admin: new Set(["read:any", "write:any", "manage:roles"]),
};
// Stolen billing_admin can leak invoices but not flip configs or grants.
```

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Long-lived access tokens (TTL > 1h) | One-shot theft → persistent compromise; revocation latency unbounded | Access TTL ≤ 1h + rotated refresh |
| Bearer-only refresh (no binding) | Equivalent to long-lived access; theft = perpetual session | Bind refresh to device fingerprint, mTLS, or DPoP |
| Refresh token reuse permitted | Stolen + legitimate parallel use both succeed | Single-use refresh + chain-mismatch detection (RFC 6749 §10.4) |
| `alg=none` accepted by verifier | Any forged token passes signature check | Explicit alg allowlist (`RS256`/`ES256`); reject `none` |
| Missing `aud` check | Tokens for service B replayed against service A | Verify `aud` matches this service every call |
| Missing `iss` check | Tokens minted by any IdP in your ecosystem accepted | Issuer allowlist verified against discovered keys |
| God-role pattern | One stolen admin credential = total compromise | Role hierarchy + scope composition; least privilege |
| Implicit S2S trust by network position | Lateral movement after one container compromise = cluster-wide RCE | mTLS or signed JWT + caller allowlist |
| Privilege creep / "temporary" admin | "Temporary" becomes permanent; quarterly review surfaces stale grants | Time-bounded grants with auto-expire + renewal ticket |
| Role explosion (47 admin-flavored roles) | Composition lost; reviewers approve grants without context | Role hierarchy + orthogonal-capability flags |
| Authorization from request body | Trivial vertical privilege escalation | Read role/scope from verified JWT claim |
| Resource access without ownership check | IDOR — horizontal privilege escalation | `caller.uid == resource.owner_id` server-side |
| OAuth implicit flow | Tokens in URL fragment leak via referer/history | Authorization Code + PKCE |
| OAuth state parameter ignored | CSRF + callback injection | State bound to session, validated on callback |
| `redirect_uri` substring/prefix match | Open redirector → token theft chain | Exact-match allowlist |
| Session ID stable across login | Session fixation: attacker pre-sets ID, victim authenticates | Rotate session ID on every privilege-level change |
| `jku` / `x5u` honored from token | Token controls its own key fetch URL → trivial bypass | Ignore or restrict to allowlist of trusted URIs |
| Same JWT secret across environments | Dev compromise → prod token forgery | Per-environment key + rotation policy |
| Identity changes shipped without VETO sign-off | One reviewer waiver = entire perimeter compromised | **Pre-Wave-1c:** security-engineer VETO + Owner gate. **Post-Wave-1c:** identity-trust-architect VETO (ADR-052 amendment in PLAN-074 Wave 1b; frozenset add in Wave 1c) |

## Acceptance Criteria

This checklist is enforced by the active VETO authority for the identity
surface: **`security-engineer` + Owner gate pre-Wave-1c (v1.14.0)**, and
**`identity-trust-architect` post-Wave-1c** once the agent file +
`VETO_FLOOR_ROLES` frozenset entry land atomically per the Wave 1c sentinel.
The reviewer checks (verbatim) the following before sign-off — a missing
answer = ADJUST, an incorrect answer = SOFT REJECT, a hard-rule violation =
VETO.

### Token lifecycle

- [ ] Access token TTL ≤ 1 hour. Exceptions require an Owner-signed ADR
      explicitly waiving Hard Rule #1 for the named surface; token binding
      + revocation latency ≤ 60s are the **minimum** ADR-mandated mitigations,
      NOT a self-service substitute for the rule.
- [ ] Refresh token rotation on every use is implemented and tested
- [ ] Refresh token is bound (device fingerprint / mTLS / DPoP /
      client_id+secret); bearer-only refresh is rejected
- [ ] Refresh-chain breach detection (parallel use of same family) is
      wired; revoke + audit-log on mismatch
- [ ] Revocation propagation latency is documented and measured

### Token validation

- [ ] Verifier uses explicit alg allowlist; `alg=none` is rejected
- [ ] `aud`, `iss`, `exp` are validated on every verification path
- [ ] Public key lookup is by `kid` against issuer keystore;
      `jku`/`x5u` are ignored or allowlisted
- [ ] Token binding (`cnf`) is verified if expected

### Authorization

- [ ] Role/scope read from verified token, not from request body
- [ ] Resource ownership check (`caller.uid == resource.owner_id`)
      server-side for user-owned data
- [ ] Default-deny default; missing policy = no access
- [ ] No god-role; permissions composed from least-privilege primitives
- [ ] Time-bounded grants where applicable (admin, support-impersonate)

### Service-to-service

- [ ] No network-position-implies-trust patterns; mTLS or signed JWT
- [ ] On-behalf-of flow correct for cross-user calls (no confused
      deputy)
- [ ] Caller allowlist documented and tested

### OAuth/OIDC

- [ ] PKCE used for all public clients; state validated **server-side for
      backend/BFF flows** (Example A) **OR browser-bound for backendless SPAs
      with documented residual XSS risk** (Example B)
- [ ] `redirect_uri` exact-match allowlist; no substring/prefix
- [ ] Implicit flow not used; ROPC not used (legacy migration only)
- [ ] Token-validation hardening checklist (this skill §Token validation
      hardening checklist) ticked

### Documentation + audit

- [ ] Threat-model worksheet (§Threat Model + parent skill §Threat-Model
      Worksheet) attached to plan/PR
- [ ] Identity events (issuance, rotation, revocation, role change,
      privilege-escalation attempt) emitted to audit log
- [ ] Detection rules (handed off to threat-detection-engineer) cover
      the threats this change introduces

### VETO triggers (any one = block merge until resolved)

1. Hard-rule violation without ADR amendment + this skill amendment
2. Missing token validation step (alg/aud/iss/exp/binding)
3. Authorization decision sourced from client-controlled input
4. New S2S call without authentication (network-position-only)
5. OAuth flow without PKCE + state validation
6. Token TTL > 1h without an Owner-signed ADR exception waiving Hard
   Rule #1 (compensating controls alone are insufficient — the ADR is mandatory)
7. Stable session ID across privilege change

## Related Skills

- **Parent: `core/security-and-auth`** — broader OWASP / CORS / WS auth /
  RLS / threat-model worksheet / detection-as-code / proof-of-
  exploitability discipline. This skill is the identity sub-domain
  specialization; a finding that touches both must cite both.
- **Sibling: `core/observability-and-ops`** — audit-log shape for
  identity events; SIEM ingestion contract; metrics for token-issuance/
  rotation/revocation rates and refresh-chain-breach alerts.
- **Sibling: `core/incident-management`** — runbook for credential-
  compromise incidents (revoke families → force re-auth → rotate
  signing keys → notify affected users); incident-commander archetype
  drives execution.
- **Sibling: `core/public-api-design`** — API key lifecycle, scope
  vocabulary, rotation cadence on public-facing endpoints.
- **Cross: `core/compliance-lgpd` / `domains/fintech/*`** — regulatory
  duties triggered by identity-system changes (consent records, KYC
  re-verification windows, regulator notification thresholds).
- **Cross: `core/state-machines-and-invariants`** — token-lifecycle
  state machine (issued → active → rotated → revoked → expired) is
  exactly the invariant-system patterns codified there.

## References

- ADR-052 §VETO_FLOOR_ROLES — pre-Wave-1c contains only `code-reviewer`
  + `security-engineer`; the PLAN-074 Wave 1c amendment patch
  (staged at `.claude/plans/PLAN-074/staging/wave-1b/_artifacts/
  adr-052-amendment.patch`) registers `identity-trust-architect`
  alongside those, but only LANDS atomically with the agent file in the
  Wave 1c GPG sentinel ceremony (per S90 P0-01 invariant). Until then
  identity changes escalate through `security-engineer` + Owner gate.
- RFC 6749 §10.4 — refresh-token rotation breach detection
- RFC 7636 — PKCE for OAuth public clients
- RFC 7519 — JWT structure + claim semantics
- RFC 8693 — Token Exchange (on-behalf-of, confused-deputy mitigation)
- RFC 8725 — JWT BCP (algorithm allowlist, validation pitfalls)
- OWASP ASVS §V2 (Authentication) + §V3 (Session Management) +
  §V4 (Access Control)
- OAuth 2.0 Security BCP (RFC 9700 / draft-ietf-oauth-security-topics)
- Parent skill: `.claude/skills/core/security-and-auth/SKILL.md`
- Inspiration: `msitarzewski/agency-agents` engineering-security-engineer
  @ `783f6a72bfd7f3135700ac273c619d92821b419a` (MIT)
