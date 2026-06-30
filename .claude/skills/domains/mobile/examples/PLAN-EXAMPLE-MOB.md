---
plan_id: PLAN-EXAMPLE-MOB
title: "Coordinate cross-platform auth token schema migration and App Store release"
status: draft
owner: ceo
level: L3
squad: mobile
profile: core,mobile
created_at: 2026-05-10
---

# Example PLAN — Auth Token Schema Migration (Cross-Platform Coordinated)

> **This is an illustrative example**, not a real plan. It shows
> how the mobile squad coordinates on a cross-platform API contract
> change that touches all three VETO scopes: cross-platform contract
> governance (Santiago), iOS App Store compliance (Yui), and Android
> Play Store compliance (Damilola).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`

## 1. Problem

The auth service is migrating from JWT tokens with 1-hour expiry and a
single `scope` string field to a new token format with 15-minute access
tokens, a separate refresh token stored in a dedicated endpoint, and a
`scopes` array (breaking the existing string field). The new format also
adds device fingerprinting to the refresh grant to support suspicious-
login detection. Both iOS and Android clients consume the token directly.

Sources:
- Auth service: new token format with breaking schema change (string → array)
- iOS client: consumes `scope` string in the session manager
- Android client: consumes `scope` string in OkHttp interceptor
- 78% of active users are on a mobile app version that cannot parse the
  new `scopes` array format without crashing

## 2. Scope

**In:**
- New auth token schema: `access_token` (15min), `refresh_token` endpoint,
  `scopes` array replacing `scope` string
- iOS client update: parse `scopes` array, store `refresh_token` in
  Keychain (not UserDefaults), implement token refresh flow
- Android client update: update OkHttp interceptor, store `refresh_token`
  in Android Keystore, update ProGuard rules for new auth classes
- Coordinated backend deployment: ship mobile clients first, reach >80%
  adoption, then cut over backend to new token format
- App Store and Play Store submissions for both updated clients

**Out:**
- Auth service PKCE implementation (separate security initiative)
- Session management UI (separate product feature)
- Web client token migration (separate frontend team)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Contract analysis | Santiago Reyes | Versioning strategy; old-client backward-compatibility plan (MOB-001) |
| P2 — iOS implementation | Yui Nakamura | `scopes` array parsing; `refresh_token` in Keychain; PrivacyInfo review (MOB-007) |
| P3 — Android implementation | Damilola Adeyemi | OkHttp interceptor; Keystore for `refresh_token`; ProGuard audit (MOB-010, MOB-009) |
| P4 — QA cross-platform | Priya Singh | Old client against new backend (graceful degradation); new client regression on min-supported devices (MOB-012) |
| P5 — App Store submissions | Beatrix Hoffmann | iOS + Android phased rollout with crash-rate gate (MOB-011) |
| P6 — Adoption monitoring | Santiago Reyes | Monitor until >80% active users on new client before backend cutover (MOB-003) |
| P7 — Backend cutover | Auth team + Santiago | Backend token format switch with Santiago sign-off on adoption gate |
| P8 — Launch review | CEO + all VETO holders | Santiago + Yui + Damilola sign-off |

## 4. Risk axes and VETO holders

- **Santiago Reyes (Mobile Architect):** `scope` → `scopes` is a breaking
  schema change → BLOCK if backend cutover begins before >80% of active
  users are on the new mobile clients (MOB-003). Old client on new backend
  must degrade gracefully → BLOCK if old iOS or Android client crashes or
  silently logs users out when it receives the new token format (MOB-001).
- **Yui Nakamura (iOS Engineer):** `refresh_token` must be stored in
  Keychain, not UserDefaults → BLOCK if any iOS code stores the refresh
  token outside the Keychain (MOB-007). PrivacyInfo.xcprivacy unchanged
  (no new privacy APIs) — but App Store submission checklist still required
  (MOB-005, MOB-006).
- **Damilola Adeyemi (Android Engineer):** `refresh_token` must be stored
  in Android Keystore → BLOCK if stored in SharedPreferences (MOB-010).
  ProGuard rules touching the new auth interceptor must be audited →
  BLOCK if any `-keep` rule is added without security review of the
  affected class (MOB-009).

## 5. Task chains invoked

- `mobile-api-contract-change` — primary chain for the schema migration
  and coordinated deployment sequencing
- `mobile-app-store-release` — for both iOS and Android phased rollout
  submissions
- `mobile-security-posture-change` — invoked for the Keychain/Keystore
  storage change and ProGuard/R8 audit

## 6. Acceptance

- Old iOS/Android client (78% of active users) degrades gracefully when
  receiving new token format — tested on physical device (MOB-001)
- Backend cutover does not begin until >80% of active users are on the
  new client versions (MOB-003)
- iOS `refresh_token` stored in Keychain with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`
  — no UserDefaults usage for any auth credential (MOB-007)
- Android `refresh_token` stored in Android Keystore (hardware-backed
  on supported devices) — no SharedPreferences usage (MOB-010)
- Android ProGuard/R8 rules for new auth interceptor classes audited by
  Damilola before merge (MOB-009)
- Both iOS and Android clients submitted with phased rollout: 1% → crash-rate
  gate → 10% → gate → 50% → 100% (MOB-011)
- Physical device regression test passed on minimum-supported devices for
  both platforms (MOB-012)

## 7. Metrics

- Client adoption rate: dashboard tracking % of active users on new client
  (gate at 80% before backend cutover)
- Crash rate at each phased rollout gate (target: ≤ baseline +0.5%)
- **Token refresh success rate** (monitored post-cutover — tracks whether
  the 15-minute access token + refresh flow is working for all users)

## 8. References

- `.claude/skills/domains/mobile/skills/mobile-app-builder/SKILL.md`
- `.claude/skills/domains/mobile/task-chains.yaml` — `mobile-api-contract-change`
- `.claude/skills/domains/mobile/task-chains.yaml` — `mobile-app-store-release`
- `.claude/skills/domains/mobile/task-chains.yaml` — `mobile-security-posture-change`
- Apple Developer Documentation: Keychain Services — kSecAttrAccessibleWhenUnlockedThisDeviceOnly
- Android Developers: Android Keystore System hardware-backed key guarantees
