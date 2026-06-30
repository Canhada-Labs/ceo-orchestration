---
name: pii-data-flow
description: Inventorying and governing personally identifiable information (PII) as it flows through a B2B SaaS under LGPD. Covers PII classification (sensitive, regular, public), dataflow mapping, egress tracking (third-party processors, backups, analytics), retention per classification, minimization strategy, and the audit views needed to satisfy Art. 37 Registro de Operações. Use when designing new services that touch user data, onboarding a third-party processor, planning analytics or backup, auditing a live system, or preparing a DPO report. Combines with data-schema-design (core) for PII-safe schemas and with consent-lifecycle (core) for consent propagation.
owner: Helena Silveira (PII Data-Flow Architect, domain persona)
secondary_owner: Theodora Nunes (Compliance Specialist, domain persona)
scope_tags: [pii, lgpd, dataflow, retention, audit]
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 2
risk_class: high
stack: []
context_budget_tokens: 600
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 4}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)pii|personal.?data|encrypt"}
---

# PII Data Flow

## Cardinal Rule

**You cannot govern what you cannot see.** The PII dataflow is a
first-class artifact — a map of *every* field that identifies a
person, *everywhere* it lives (primary DB, cache, search index,
backup, analytics, CRM, vendor integration). If the map doesn't
exist, the system is not compliant, regardless of how good the code is.

## PII classification (LGPD Art. 5)

| Class | Examples | Minimum controls |
|---|---|---|
| **Sensitive (Art. 5 II)** | CPF, race, religion, health, sexual orientation, political, biometric, genetic | encryption at rest + column-level access log + RLS + pseudonymization if used outside primary DB |
| **Regular PII** | name, email, phone, address, IP, device ID | encryption at rest + RLS + retention policy |
| **Pseudonymized** | hashed surrogate IDs | classified as PII if keyed lookup exists; non-PII only if re-identification is technically infeasible |
| **Public / non-PII** | aggregated analytics (cell >= k), company names | no PII controls required |

Sensitive PII triggers stricter retention (usually 5y max unless legal
obligation), mandatory RIPD, and DPO review before new processing.

## The PII dataflow map (deliverable)

For every PII field, the map records:

```yaml
# Example entry in pii-inventory.yaml
- field: users.cpf
  class: sensitive
  legal_basis: legal_obligation    # per LGPD Art. 7 V (fiscal requirements)
  purposes: [billing, tax-reporting]
  storage:
    - primary: {table: users, column: cpf, encryption: aes-256-gcm}
    - cache: none
    - search_index: none
    - backup: encrypted-s3 (retention 5y)
  egress:
    - vendor: stripe
      purpose: payment_processing
      contract: DPA signed 2025-11
      countries: [US]
      safeguards: SCC + supplementary measures
  retention_class: fiscal_5y
  deletion_path: anonymize_on_dsr
  owner: Billing Engineer
  dpo_review: 2026-01-15
```

Every new service that reads or writes a PII field MUST update the map
**in the same PR** as the code. No map update = VETO from DPO.

## Minimization (Art. 6 III)

Every PII field in every store must earn its keep. The test:

> "If this field were deleted tomorrow, which feature breaks — and is
> that feature worth the PII exposure?"

Apply at:

- **Schema design** — don't collect what you don't need
- **Analytics ingestion** — never send raw PII; pre-aggregate or pseudonymize at source
- **Logs** — NEVER log PII (even in debug). Log surrogate IDs
- **Error tracking** — scrub request bodies before forwarding to vendors
- **Third-party APIs** — send only the fields the vendor *needs*, not whatever
  you have

## Retention classes (default mapping)

| Class | Max retention | Triggers early deletion |
|---|---|---|
| `session` | 24 h | logout, revoked consent |
| `operational_90d` | 90 days | account closure |
| `billing_5y` | 5 years | DSR + legal hold exempt |
| `fiscal_5y` | 5 years (LGPD Art. 16 II — fiscal) | — |
| `legal_hold` | indefinite (documented case) | court order lift |
| `consent_event` | 10 years (compliance audit) | — |

Retention jobs run daily with a dry-run flag before enforcement. Any
retention-class override requires DPO sign-off.

## Egress tracking

Every third-party system that receives PII must be listed in the map
with:

1. **DPA (Data Processing Agreement)** in place
2. **Legal basis** for sharing (usually contract execution or legitimate interest)
3. **Country / jurisdiction** — international transfers need SCC + supplementary measures per LGPD Art. 33
4. **Fields actually sent** (not fields *accessible* — the map tracks what crosses the wire)
5. **Shutdown procedure** — how to stop the egress within 24 h if needed

## Logs (never PII)

Every logging call that touches a user row MUST use surrogate IDs:

```python
# ❌ leaks PII
log.info("user created", email=user.email, name=user.name)

# ✅ surrogate only
log.info("user created", user_id=str(user.id))
```

Enforcement:

- Lint rule: `log.*(.*user\.(email|name|cpf|phone))` flagged at build
- Pre-commit hook rejects matches
- Runtime: log forwarder scrubs known PII patterns before leaving the host

## Backup policy

Backups are PII storage. They MUST:

- Be encrypted at rest with a KMS-managed key
- Have a retention per the most conservative class in the backup
- Be exercised monthly (restore to staging)
- Have a documented redaction path for DSR deletion

If your backup keeps PII past the retention class, your retention policy
is not actually implemented.

## Anti-patterns

| ❌ Anti-pattern | ✅ Fix |
|---|---|
| "We'll map PII when we have time." | Map is created *before* the first migration lands |
| Analytics pipeline sends raw request bodies | Pipeline scrubs/pseudonymizes at source |
| Error tracker gets unredacted stack context | Pre-upload scrubber removes known patterns |
| Admin CLI can read any column | Column-level access log + RLS + elevation review |
| "It's just internal logs" | Internal logs are PII storage like any other |

## Integration with consent-lifecycle

When a user revokes consent for purpose P:

- The dataflow map tells you *every system* that processes the user for P
- The revocation propagation SLA (see consent-lifecycle) cascades per system
- Missing a downstream in the map = missing revocation = compliance failure

The map is the source of truth for "where does revocation have to
propagate."
