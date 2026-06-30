---
name: dpo-reporting
description: Data Protection Officer reporting discipline for Brazilian LGPD compliance. Covers the Registro de Operações (Art. 37), Relatório de Impacto à Proteção de Dados (RIPD, Art. 38), Data Subject Request response SLAs and tooling, incident notification to ANPD within the 72-hour window (Art. 48), and the signed-trail artifacts auditors expect. Use when designing the DPO dashboard, wiring DSR endpoints, writing incident playbooks, or preparing for an ANPD audit. Combines with compliance-lgpd (core) for the legal framework and with consent-lifecycle + pii-data-flow (core) for the underlying data.
owner: Mira Okafor (DPO Engineer, domain persona)
secondary_owner: Theodora Nunes (Compliance Specialist, domain persona)
scope_tags: [lgpd, dpo, dsr, incident, audit]
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: high
stack: []
context_budget_tokens: 600
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 8}
  engine: {active: true, priority: 7}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 8}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)dpo|data.?protection|breach"}
---

# DPO Reporting

## Cardinal Rule

**Every DSR is a deadline. Every incident is a stopwatch. Every
disclosure has a signed trail.** Anything less is a report you can't
defend, a deadline you missed, or an incident you'll regret.

## The four DPO deliverables

| Deliverable | Source | Cadence | Audience |
|---|---|---|---|
| **Registro de Operações (Art. 37)** | pii-inventory + consent_events + processing log | continuous; snapshot quarterly | ANPD on request; internal DPO |
| **RIPD (Art. 38)** | RIPD template per processing activity | before launching new processing; reviewed yearly | internal DPO; ANPD on request |
| **DSR response log** | DSR endpoint telemetry | continuous | requesting user + DPO |
| **Incident notification** | incident response runbook | within 72 h of confirmed incident | ANPD + affected users |

## DSR response SLAs

| DSR type (LGPD Art. 18) | SLA | Notes |
|---|---|---|
| Acesso (confirm + copy) | 15 calendar days | Extendable once by 15d with justification |
| Correção | 15 calendar days | — |
| Anonimização / bloqueio / eliminação | 15 calendar days | Subject to legal retention holds |
| Portabilidade | 15 calendar days | Machine-readable format (JSON or CSV) |
| Informação sobre compartilhamentos | 15 calendar days | From pii-inventory egress map |
| Informação sobre recusa de consentimento | 15 calendar days | Explain consequences of refusal |
| Revogação de consentimento | 24 h propagation (internal SLA; LGPD is "without undue delay") | Cascades per consent-lifecycle |

**The clock starts when the request lands in the DSR queue**, not when
someone reads it. Queue ingestion time is the stopwatch start.

## DSR endpoint design

A DSR endpoint must:

1. **Authenticate the requester** — must be the data subject, verified
   via account + step-up (2FA, email loop). Impersonation defeats the
   whole regime.
2. **Rate limit per user** — e.g., 3 requests per 30 days per type.
   Prevents enumeration-style abuse.
3. **Log the request with signed timestamp** — cryptographic timestamp
   when the request enters the queue. This is the SLA stopwatch start.
4. **Produce a machine-readable response** (for portabilidade) — JSON
   or CSV, with a versioned schema.
5. **Redact third-party PII** — if user A's record mentions user B, B's
   fields must be redacted from A's export.
6. **Return a request ID** — the user uses it to track status; the DPO
   uses it for audit.

```
POST /api/dsr
  Authorization: Bearer <user-token>
  Body: {type: "acesso" | "correção" | ..., purpose: "optional", ...}
  Response: {request_id, status: "queued", eta_days: 15}

GET /api/dsr/<id>
  Response: {request_id, status, submitted_at, completed_at?, download_url?}
```

## The Registro de Operações

A single source of truth for "what processing do we do, on whose data,
for what purpose, with what legal basis, retained for how long, shared
with whom."

```yaml
# registro.yaml (example)
version: "2026.Q1"
controller: {name: "Acme SaaS Ltda.", cnpj: "..."}
dpo: {name: "Mira Okafor", email: "dpo@acme.io", contact: "..."}
processing_activities:
  - id: "PA-001"
    name: "Account management"
    purpose: "Provide SaaS services to the user"
    legal_basis: "contract_execution"  # LGPD Art. 7 V
    data_categories: [name, email, password_hash, org_id]
    retention: billing_5y
    sharing: []
    security: "encryption_at_rest, RLS, 2FA"
    dpo_review: "2026-01-15"
  - id: "PA-002"
    name: "Marketing email"
    purpose: "..."
    legal_basis: "consent"
    ...
```

Regenerate on every processing-activity change. Version with the
quarter (`2026.Q1`, `2026.Q2`) so audits can trace to a point in time.

## RIPD (Art. 38)

Required before launching a *new* processing activity that poses
"high risk" to data subjects:

1. **Describe the processing** — purpose, legal basis, categories, retention
2. **Identify risks** — unauthorized access, excessive retention, re-identification, discrimination
3. **Mitigations** — encryption, access controls, DPA, audit
4. **Residual risk rating** — low / medium / high; high requires DPO + Owner sign-off
5. **Data subject impact** — what happens to users if the risk materializes
6. **Review date** — annual minimum

Template at `templates/RIPD-template.md` (not shipped in Sprint 4).

## Incident notification (Art. 48)

If a personal data incident occurs (breach, unauthorized access,
accidental disclosure), the controller MUST notify ANPD and affected
users **within 72 hours of confirmation**. The stopwatch starts when
the *security team confirms* the incident, not when support fields
the first user complaint.

### Incident playbook

```
T+0h  Detection  → enter incident queue; notify DPO + Security on-call
T+1h  Triage     → classify (confirmed / suspected / false alarm)
                   if confirmed: the 72-h clock starts NOW
T+12h Containment → stop ongoing leakage; preserve forensic state
T+24h Impact assessment → affected users, data categories, duration,
                           root cause draft
T+48h Draft notification → to ANPD + users
T+60h Legal review     → DPO + external counsel sign-off
T+72h Submit           → ANPD notification filed; user notifications sent
T+7d  Retrospective    → RCA, permanent fix, policy update
T+30d Post-mortem      → written report, shared with DPO + Owner
```

Every step has a timestamped log entry in the incident tracker. The
tracker produces the ANPD submission from its own data — no copy-paste.

### What ANPD expects in the notification (Art. 48 §1)

- Nature of the affected data
- Data subjects involved (approximate count + characterization)
- Technical and security measures used for protection
- Risks related to the incident
- Mitigation measures already applied
- Timeline of events with timestamps

## Anti-patterns

| ❌ Anti-pattern | ✅ Fix |
|---|---|
| DSR email inbox handled by support manually | DSR endpoint + queue + SLA tracking |
| "72-h clock starts when we tell leadership" | Stopwatch starts at confirmed incident time; log shows it |
| RIPD written after launch | RIPD is a launch blocker for new high-risk processing |
| Registro is a spreadsheet someone updates quarterly | `registro.yaml` in-repo, PR-reviewed, generated from sources |
| "We haven't had any incidents" | A playbook that's never been rehearsed has never worked |

## Integration with the rest of the squad

- **pii-data-flow** — the map is the input to the Registro. Map drift = Registro drift.
- **consent-lifecycle** — DSR "revogação" triggers the consent event;
  the stopwatch for propagation starts on the DSR confirmation.
- **security-and-auth** (core) — the incident playbook invokes the security runbooks for containment and forensics.

## Rehearsals

The incident playbook is rehearsed **twice a year minimum**. A synthetic
incident is injected; the team runs the full 72-h flow; the RCA
produces a real post-mortem. Playbooks that aren't rehearsed fail in
production.
