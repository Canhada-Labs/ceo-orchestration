---
name: consent-lifecycle
description: Consent as an auditable state machine for Brazilian LGPD and equivalent regimes. Covers consent event schema (grant, revoke, expire, re-up), per-purpose granularity, downstream propagation windows, consent replay for audit, revocation SLAs, and the invariants every consent mutation must preserve. Use when designing signup flows, consent banners, preference centers, data-subject-request handlers, or any change that alters the consent graph. Combines with state-machines-and-invariants (core) for the transition rules and with pii-data-flow (core) for downstream reach.
owner: Rafael Menezes (Consent Lifecycle Engineer, domain persona)
secondary_owner: Theodora Nunes (Compliance Specialist, domain persona)
scope_tags: [consent, lgpd, state-machine, audit]
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 3
risk_class: high
stack: []
context_budget_tokens: 600
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 7}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)consent|opt.?in|opt.?out"}
---

# Consent Lifecycle

## Cardinal Rule

**Consent is a state machine with append-only events, not a boolean
on a user row.** Every grant, revoke, expire, and re-up is a separate
event. The *current state* is derived from the event stream. Deriving
vs. mutating is the difference between passing an audit and losing it.

## The minimum consent event schema

```sql
CREATE TABLE consent_events (
  id              bigserial PRIMARY KEY,
  user_id         uuid NOT NULL,
  purpose         text NOT NULL,       -- 'marketing', 'analytics', 'third_party_share:<vendor>', ...
  state           text NOT NULL,       -- 'granted' | 'revoked' | 'expired' | 'renewed'
  legal_basis     text NOT NULL,       -- 'consent' | 'legitimate_interest' | 'legal_obligation' | ...
  source          text NOT NULL,       -- 'signup' | 'preference_center' | 'admin_override' | 'dsr' | 'ttl_expire'
  actor_id        uuid,                -- who made the change (user themselves, admin, system)
  created_at      timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz,         -- NULL for indefinite
  evidence        jsonb NOT NULL,      -- IP, user-agent, signed ToS hash, form version, etc.
  previous_event_id bigint REFERENCES consent_events(id)
);
CREATE INDEX ON consent_events (user_id, purpose, created_at DESC);
```

Rules:

1. **Append-only.** `UPDATE consent_events` is forbidden. Corrections
   create a new event with `source = 'correction'` referencing the
   incorrect one via `previous_event_id`.
2. **Per-purpose granularity.** One consent per purpose, never a
   catch-all. "Marketing email" and "marketing SMS" are distinct
   purposes if a user can opt into one without the other.
3. **Legal basis is always recorded** — not every data handling is
   consent-based. LGPD Art. 7 enumerates the 10 legal bases.
4. **Evidence is mandatory.** At minimum: IP, user-agent, form version,
   signed hash of the text the user consented to.

## Current-state derivation (read model)

```sql
CREATE VIEW consent_current AS
SELECT DISTINCT ON (user_id, purpose)
  user_id, purpose, state, legal_basis, created_at, expires_at
FROM consent_events
WHERE state IN ('granted', 'revoked', 'expired', 'renewed')
ORDER BY user_id, purpose, created_at DESC;
```

The app reads from `consent_current`, never from `consent_events` directly.

## Revocation propagation SLA

When a user revokes consent for purpose P, downstream systems MUST
drop the user from P within a defined window:

| Downstream | SLA | Enforcement |
|---|---|---|
| Transactional DB caches | immediate (< 1 min) | cache invalidation event |
| Email queue | 15 min | queue consumer checks consent before send |
| CRM / third-party sync | 24 h | daily reconciliation job |
| Analytics pipelines | 24 h | ETL joins with current consent state |
| Cold backups | next retention cycle (documented) | backup retention policy |

Every downstream system that processes PII MUST publish its revocation
SLA to the `pii-data-flow` map (see that skill).

## Consent expiry (re-up)

For consent that has an expiry (common for marketing after inactivity):

- At `expires_at - 7 days`: queue a re-up notification
- At `expires_at`: auto-emit `state: 'expired'` event; downstream drops
- The user may re-grant via preference center; emits `state: 'renewed'`

Never silently extend expiry without a new explicit event.

## Admin override (rare, audited)

An admin may revoke consent on a user's behalf (e.g., fraud, account
closure). This MUST:

1. Emit event with `source: 'admin_override'` + `actor_id` of the admin
2. Record the operational reason in `evidence.reason`
3. Trigger an alert to the DPO queue (review within 7 days)

Admin override is NEVER a silent mutation.

## DSR interaction

On Data Subject Request for "delete my data":

- Emit `revoked` for all purposes (history preserved)
- Trigger the anonymization/deletion job per retention policy
- Retain `consent_events` for the user — they are the audit trail
  showing consent was properly revoked before deletion

Consent events survive user data deletion. Anonymize `user_id` to a
hashed surrogate when the user is deleted, keeping the audit chain.

## Anti-patterns

| ❌ Anti-pattern | ✅ Fix |
|---|---|
| `UPDATE users SET marketing_consent = false` | `INSERT INTO consent_events (purpose, state) VALUES ('marketing', 'revoked')` |
| "Consent to everything" at signup via single checkbox | Per-purpose checkboxes, each with its own text + version |
| Consent implied from continued use | Explicit event only; no silent opt-in |
| Revocation takes effect "eventually" without SLA | SLA per downstream; audit shows compliance |
| Admin changing user consent without audit trail | `source: 'admin_override' + actor_id + reason` mandatory |

## Integration tests (non-negotiable)

- Grant → revoke → read current state = revoked
- Revoke → wait `N` → downstream email queue drops user
- Expired consent at T+ttl auto-emits expire event
- DSR deletion preserves consent event history under hashed surrogate
- Admin override without `actor_id` is rejected by the API

## Debate round 1 input (squad bootstrap)

This skill was bootstrapped as part of Sprint 4 Phase 8 (squad lgpd-heavy-saas).
Reviewed by Theodora Nunes (compliance veto) and Mira Okafor (DPO veto).
No external lighthouse adopter yet.
