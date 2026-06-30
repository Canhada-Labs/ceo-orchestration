---
plan_id: PLAN-EXAMPLE-IDS
title: "Add WebAuthn passkey authentication as primary factor with phishing-resistant MFA"
status: draft
owner: ceo
level: L3
squad: identity-systems
profile: core,identity-systems
created_at: 2026-05-10
---

# Example PLAN — Add WebAuthn passkey authentication as primary factor

> **This is an illustrative example**, not a real plan. It shows how the
> identity-systems squad coordinates on introducing a new authentication
> factor that touches the token lifecycle, key management, consent scope,
> and identity graph.
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/identity-systems/task-chains.yaml`

## 1. Problem

A B2B SaaS company currently uses password + TOTP as its MFA stack.
TOTP is phishable (real-time phishing toolkits like Evilginx can relay
TOTP codes). The security team has mandated a migration to phishing-
resistant MFA for all admin accounts, and the product team wants to offer
passkeys (WebAuthn / FIDO2) as a primary factor for all users. The
current OAuth 2.0 authorization server issues access tokens with a 60-
minute lifetime (too long). The existing session cookies do not have
SameSite attributes set.

Sources:
- Security team mandate: admin accounts must use phishing-resistant MFA
  by Q3 2026
- Pen test report (2026-Q1): access token lifetime flagged as critical
  finding; TOTP phishing demonstrated in lab environment
- Product roadmap: passkeys as primary factor for user-facing login, with
  optional password fallback for account recovery only

## 2. Scope

**In:**
- WebAuthn credential registration and authentication flow (primary factor)
- Access token lifetime reduction from 60 minutes to 15 minutes
- Refresh token rotation-on-use implementation (currently absent)
- Session cookie SameSite + HttpOnly audit and fix
- Phishing-resistant MFA enforcement for admin identities (FIDO2 hardware
  key OR device passkey, no TOTP fallback for admin roles)

**Out:**
- Password migration or password deprecation for non-admin users (deferred)
- Enterprise SSO WebAuthn integration (separate federation plan)
- Identity graph updates based on passkey credential (no PII-matching
  changes in this plan)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Protocol design | Sione Tuilagi | Token lifecycle spec (15-min access token, refresh rotation), session-cookie spec |
| P2 — Crypto implementation | Lena Hoffmann | WebAuthn credential storage, signing algorithm selection, key rotation plan |
| P3 — Consent review | Ayasha Morningstar | Consent scope for credential storage, cross-border authenticator data transfer |
| P4 — Privileged access | Sione Tuilagi | Admin phishing-resistant MFA enforcement policy, step-up auth for privileged roles |
| P5 — Implementation | Auth Engineer | WebAuthn RP implementation, token lifecycle code, cookie fix |
| P6 — Launch review | CEO + all VETO holders | Identity Architect + Auth Engineer + Compliance sign-off |

## 4. Risk axes and VETO holders

- **Sione Tuilagi (Identity Architect):** Access token lifetime at 60 minutes
  is a critical open finding. Passkey rollout must be bundled with token
  lifetime reduction to 15 minutes — these are not separate workstreams →
  BLOCK if access token lifetime is not reduced to 15 minutes as part of
  this plan (IDS-001). Admin roles must use phishing-resistant MFA with no
  TOTP fallback → BLOCK if TOTP remains as an admin MFA option post-launch
  (IDS-012).
- **Lena Hoffmann (Auth Engineer):** WebAuthn credential storage must use
  correct challenge nonces, origin validation, and RP ID binding. Session
  cookies must be corrected to include SameSite in this plan — not deferred
  → BLOCK if any session cookie is deployed without Secure + HttpOnly +
  SameSite (IDS-004). Refresh token rotation-on-use must be implemented
  before passkeys go live → BLOCK if refresh tokens still lack rotation
  (IDS-002).
- **Ayasha Morningstar (Compliance & Privacy Reviewer):** WebAuthn
  authenticators may store device biometrics; credential registration
  is a new processing activity under LGPD Art. 11 (biometric data is
  sensitive personal data) → BLOCK if credential registration does not
  have its own consent event with biometric processing purpose recorded,
  or if cross-border authenticator attestation data is not covered by an
  adequacy decision or SCCs (IDS-009).

## 5. Task chains invoked

- `identity-systems-new-auth-flow` — primary chain governing protocol
  selection → token lifecycle → crypto implementation → session cookies →
  consent review → security tests → launch VETO.
- `identity-systems-consent-flow-change` — triggered because WebAuthn
  credential storage is a new processing purpose (biometric data category
  under LGPD Art. 11) requiring a new consent event separate from the
  existing authentication consent. Chain governs consent event model →
  revocation path → graph impact (none in this plan) → propagation SLA.

## 6. Acceptance

- Access token lifetime reduced from 60 minutes to 15 minutes (IDS-001)
- Refresh token rotation-on-use implemented with family invalidation on
  reuse detection (IDS-002)
- WebAuthn: Authorization Code + PKCE confirmed for the browser flow
  (IDS-003); session cookies corrected to Secure + HttpOnly + SameSite
  (IDS-004)
- Signing algorithm: RS256 or EdDSA confirmed, HS256 not used for
  multi-party token verification (IDS-005)
- alg: none explicitly rejected in JWT validation path (IDS-006)
- Admin MFA: TOTP removed as fallback for any role in the privileged
  access group; hardware FIDO2 or device passkey mandatory (IDS-012)
- Consent: WebAuthn credential storage consent event recorded with
  biometric processing purpose, legal basis, and consent text version
  (IDS-009); cross-border attestation data transfer assessed (Ayasha sign-off)
- OWASP ASVS Level 2 security test suite passes before launch

## 7. Metrics

- Admin phishing simulation pass rate (baseline: 23% click rate on TOTP
  phishing sim; target: 0% post-WebAuthn enforcement)
- Refresh token family invalidation rate (any value above 0 in production
  indicates active token-reuse attacks being mitigated)
- **Access token introspection cache hit rate** (monitored post-launch;
  15-minute tokens will increase introspection volume — watch for latency
  regression)

## 8. References

- `.claude/skills/domains/identity-systems/skills/identity-graph-operator/SKILL.md`
- `.claude/skills/domains/identity-systems/task-chains.yaml` — `identity-systems-new-auth-flow`
- `.claude/skills/domains/identity-systems/task-chains.yaml` — `identity-systems-consent-flow-change`
- `.claude/skills/domains/identity-systems/pitfalls.yaml` — IDS-001, IDS-002, IDS-003, IDS-004, IDS-005, IDS-006, IDS-009, IDS-012
