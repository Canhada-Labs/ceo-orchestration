<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/security-and-auth/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

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

