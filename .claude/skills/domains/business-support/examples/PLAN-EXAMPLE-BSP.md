---
plan_id: PLAN-EXAMPLE-BSP
title: "Integrate CRM health-score data into ticketing system with automated escalation"
status: draft
owner: ceo
level: L3
squad: business-support
profile: core,business-support
created_at: 2026-05-10
---

# Example PLAN — CRM Health-Score Integration with Escalation Triggers

> **This is an illustrative example**, not a real plan. It shows
> how the business-support squad coordinates on a feature that
> touches all three VETO scopes: escalation policy change (Camille),
> ticketing data integration (Kwame), and customer-facing communication
> templates (Ingrid).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`

## 1. Problem

The support team wants to automatically escalate tickets from customers
whose CRM health score drops below a threshold (at-risk customers), routing
them to a dedicated enterprise support queue with a tighter SLA. Currently,
at-risk customer tickets enter the general queue and are indistinguishable
from standard tickets. Two enterprise customers churned in the past quarter
citing slow support response times.

Sources:
- CRM (Salesforce): customer health score + contract tier + ARR
- Ticketing system (Zendesk): ticket queue, routing rules, SLA configuration
- Support portal: customer-facing SLA commitments page

## 2. Scope

**In:**
- Salesforce → Zendesk webhook: push customer health score and tier on ticket
  creation and on health-score change
- New Zendesk routing rule: if health_score < 40 AND tier = enterprise,
  route to `enterprise-priority` queue with 1-hour SLA
- New Zendesk custom field: `customer_health_score` (integer, updated by webhook)
- Updated SLA breach notification template for the enterprise-priority queue

**Out:**
- Changes to the CRM health scoring methodology (Customer Success scope)
- Customer-facing health score display (separate product initiative)
- Tier-1 customer automatic escalation (ARR threshold excludes SMB)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Schema + PII review | Kwame Asante | New `customer_health_score` field with retention class + deletion path (BSP-005) |
| P2 — Webhook design | Kwame Asante | Idempotent Salesforce→Zendesk webhook with deduplication (BSP-006) |
| P3 — Routing rule | Camille Fontaine | Shadow period + 48h replay on new routing logic (BSP-001, BSP-004) |
| P4 — SLA alignment | Camille + Ingrid | Confirm 1-hour SLA matches enterprise contract terms (BSP-002) |
| P5 — Template update | Ingrid Hoffmann | SLA breach notification for enterprise-priority queue (BSP-009, BSP-010) |
| P6 — Analytics coverage | Anika Johansson | Dashboard: enterprise-priority queue SLA compliance, health-score distribution |
| P7 — Launch review | CEO + all VETO holders | Camille + Kwame + Ingrid sign-off |

## 4. Risk axes and VETO holders

- **Camille Fontaine (Support Operations Lead):** New routing rule could
  misroute tickets if the health-score webhook is delayed → BLOCK if
  shadow period shows >2% unexpected routing vs expected (BSP-001, BSP-004).
- **Kwame Asante (Tier-2/3 Engineer):** `customer_health_score` field
  treated as PII-adjacent (correlates to specific customer business data) →
  BLOCK if no retention class or deletion path is declared (BSP-005);
  BLOCK if webhook lacks idempotency (BSP-006).
- **Ingrid Hoffmann (Customer Success Manager):** 1-hour SLA must match the
  contractual enterprise SLA — not assumed, verified → BLOCK if contract
  SLA differs from configured SLA (BSP-002); BLOCK if breach notification
  template obscures breach fact (BSP-010).

## 5. Task chains invoked

- `business-support-escalation-policy-change` — for the new routing rule and
  SLA threshold configuration
- `business-support-new-ticketing-integration` — for the Salesforce→Zendesk
  webhook and new custom field
- `business-support-kb-content-lifecycle` — invoked to update the enterprise
  support KB article explaining the new escalation process for agents

## 6. Acceptance

- `customer_health_score` field has declared retention class and deletion
  path (GDPR/LGPD DSR path tested) (BSP-005)
- Idempotency: 5 duplicate webhook events result in 1 field update per
  ticket (BSP-006)
- 48-hour routing replay shows ≤2% divergence from expected enterprise-priority
  routing (BSP-004)
- Enterprise contract SLA (1-hour response) matches Zendesk configured SLA
  exactly — verified against 3 enterprise contracts (BSP-002)
- SLA breach notification template explicitly states SLA commitment that
  was missed (BSP-010)
- API key for Salesforce integration scoped to read ticket + write custom
  field only — no admin scope (BSP-008)

## 7. Metrics

- Enterprise-priority queue first-response time (target: ≤60 min, 95th pctile)
- SLA breach rate for enterprise-priority queue (target: <2%)
- **Churn rate for at-risk customers** (monitored quarterly — primary
  success metric for the initiative)

## 8. References

- `.claude/skills/domains/business-support/skills/support-responder/SKILL.md`
- `.claude/skills/domains/business-support/skills/analytics-reporter/SKILL.md`
- `.claude/skills/domains/business-support/task-chains.yaml` — `business-support-escalation-policy-change`
- `.claude/skills/domains/business-support/task-chains.yaml` — `business-support-new-ticketing-integration`
- GDPR Article 17 — right to erasure (applies to customer_health_score field)
