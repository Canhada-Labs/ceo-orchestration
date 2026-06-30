---
id: PLAN-LGPD-EXAMPLE
title: Example — Add marketing email consent + propagation pipeline
status: executing
created: 2026-04-12
owner: CEO
depends_on: []
related_commits: []
sprint: example
tags: [lgpd, example, consent, marketing]
---

# PLAN-LGPD-EXAMPLE — Marketing email consent + propagation

> **This is an example plan shipped with the lgpd-heavy-saas squad.**
> It is not a real plan for this framework repo. It demonstrates how the
> squad's personas, skills, pitfalls, and task-chains collaborate on a
> realistic LGPD work unit. Adopters can reuse it as a template.

## Thesis

Add opt-in marketing email consent to the signup flow, implement the
per-purpose event log, and wire the revocation propagation to three
downstream systems (email queue, CRM sync, analytics ingest).

## Legal basis: **consent (LGPD Art. 7 I)**.
RIPD filed (LGPD-016): residual risk **low** (email-only, not sensitive PII).

## Phases

### Phase 1 — Schema + consent event

**Owner:** Rafael Menezes + Bram Voss

Files:
- `supabase/migrations/NNNN_consent_events.sql` — the append-only table
  (schema from `consent-lifecycle` skill §"minimum consent event schema")
- `supabase/migrations/NNNN_consent_current_view.sql` — derived view
- `src/consent/model.ts` — typed accessors

Acceptance: `SELECT * FROM consent_current WHERE user_id = X AND purpose = 'marketing'`
returns latest state with O(1) lookup. Grant → revoke → read shows revoked.

**Pitfalls enforced:** LGPD-001 (no boolean), LGPD-002 (per-purpose), LGPD-008 (RLS check).

### Phase 2 — Signup UI

**Owner:** Growth Engineer + Rafael Menezes

Files:
- `app/signup/consent-section.tsx` — per-purpose checkboxes with versioned text
- `app/signup/api/consent.ts` — POST /api/consent endpoint emitting consent events

Acceptance: unchecked boxes do NOT emit `granted` events. Text version
hashed into `evidence`. Form version recorded.

**Pitfalls:** LGPD-002 (granularity — marketing-email distinct from marketing-sms).

### Phase 3 — Propagation workers (3 downstreams)

**Owner:** Helena Silveira + Rafael Menezes

Files:
- `workers/email-queue-consent.ts` — consumer of consent_events; drops
  user from pending send queue on revoke (SLA: 15 min)
- `workers/crm-sync-consent.ts` — daily reconciliation job against the CRM
  (SLA: 24 h)
- `workers/analytics-consent.ts` — filters ingestion pipeline by consent
  state (SLA: 24 h)

Acceptance: revoke event → worker triggers within SLA → downstream state
confirms absence. Integration test produces a revoke and asserts each
downstream reflects it within the SLA window.

**Pitfalls:** LGPD-003 (SLA publication — each worker logs its SLA on
startup), LGPD-006 (surrogate user_id only in logs).

### Phase 4 — DSR wiring

**Owner:** Mira Okafor

Files:
- `app/api/dsr/consent.ts` — POST consent revocation via DSR;
  stopwatch logs
- `app/api/dsr/access.ts` — ensures export includes consent_events
  with surrogate user_id (LGPD-012 — no third-party PII)

Acceptance: POST /api/dsr with type=revogação emits consent event within
24 h; GET /api/dsr/<id> shows status.

**Pitfalls:** LGPD-010 (auth + rate limit), LGPD-011 (stopwatch = queue ingest).

### Phase 5 — Registro + RIPD

**Owner:** Theodora Nunes + Mira Okafor

Files:
- `compliance/registro.yaml` — PA-042 marketing email entry
- `compliance/ripd/PA-042-marketing-email.md` — full RIPD with residual
  risk = low

Acceptance: `registro.yaml` regenerates clean; RIPD reviewed + signed.

**Pitfalls:** LGPD-015 (generated from sources, not spreadsheet), LGPD-016 (RIPD = launch blocker).

## Success criteria

- [ ] 5 downstream SLAs documented, 3 workers pass integration tests
- [ ] DSR endpoint authenticated + rate limited + stopwatch-logged
- [ ] Registro entry PA-042 present and generated; RIPD signed
- [ ] `pii-inventory.yaml` updated with new consent_events table
- [ ] Integration tests: grant → revoke → all 3 downstreams drop within SLA
- [ ] Logs audit: no PII in any log line (LGPD-006)
- [ ] Staff Code Reviewer + DPO + Compliance approve merge

## How to continue

> "Resume PLAN-LGPD-EXAMPLE. Check phase status in each file's HEAD
> commit. Run integration tests. If green, transition status to 'done'
> and update the Registro."
