<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/security-and-auth/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

