---
plan_id: PLAN-EXAMPLE-SAS
title: "Launch Enterprise tier with dedicated database isolation and data-residency option"
status: draft
owner: ceo
level: L3
squad: saas-platforms
profile: core,saas-platforms
created_at: 2026-05-10
---

# Example PLAN — Launch Enterprise tier with dedicated database isolation and data-residency option

> **This is an illustrative example**, not a real plan. It shows how the
> SaaS platforms squad coordinates on introducing a new tenancy tier that
> changes the isolation model, touches shared infrastructure blast-radius,
> and introduces new entitlement and billing mechanics.
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/saas-platforms/task-chains.yaml`

## 1. Problem

A multi-tenant SaaS analytics platform currently operates a pooled-tenancy
model: all tenants share the same PostgreSQL cluster with RLS policies
enforcing row-level isolation. The Growth and Standard tiers have worked
well at this model. Several enterprise prospects have blocked on two issues:
(1) they require dedicated database isolation (their security team will not
accept RLS-only isolation for a SOC 2 Type II audit), and (2) some EU-based
prospects require data residency in the EU (all data stored in Frankfurt,
no replication to the US cluster). The current platform topology has no
per-tenant database provisioning capability and no EU region.

Sources:
- Sales pipeline: 6 enterprise deals blocked on isolation requirement;
  combined ACV $2.1M
- Security assessment (2026-Q1): pooled-tenancy RLS-only model scores
  "medium risk" for enterprise-regulated workloads under shared database
  failure modes
- Product-market fit interview: EU GDPR data residency is a deal-blocker
  for 3 of the 6 prospects

## 2. Scope

**In:**
- Dedicated PostgreSQL instance provisioning per Enterprise tenant
- Per-tenant database migration tooling (schema management, migration
  execution, rollback)
- EU region deployment (Frankfurt) with data-residency enforcement
  (no cross-region replication for residency-required tenants)
- Enterprise plan entitlement configuration (dedicated DB as an
  Enterprise-only feature)
- Per-tenant resource quotas for the dedicated DB tier (connection pool,
  query timeout, storage IOPS)
- Subscription state machine update: Growth → Enterprise upgrade path

**Out:**
- SOC 2 Type II certification scope change (separate compliance programme)
- Enterprise single-tenant Kubernetes cluster (deferred; dedicated DB
  is the isolation level agreed for this plan)
- EU data-residency for the Growth and Standard tiers (future plan)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Isolation analysis | Priyanka Mehta | Formal isolation analysis document for dedicated-DB tenancy model |
| P2 — Tenancy provisioning | Amara Nwosu | Per-tenant DB provisioning script, migration tooling, RLS removal for dedicated instances |
| P3 — Quota design | Cormac Sullivan | Per-tenant connection pool, query timeout, IOPS limits; EU region SLO targets |
| P4 — Entitlement + billing | Diego Paredes | Enterprise plan entitlement map, upgrade state machine, event-log extension |
| P5 — EU region deployment | SRE + Platform | Frankfurt region live, data-residency routing, replication blocked for residency tenants |
| P6 — Launch review | CEO + all VETO holders | Architect + SRE + Billing sign-off before first Enterprise customer migration |

## 4. Risk axes and VETO holders

- **Priyanka Mehta (Platform Architect):** Moving from pooled-tenancy to
  dedicated-per-tenant is a tenancy model change requiring a formal isolation
  analysis document before code is written → BLOCK if any Enterprise tenant
  is provisioned before the isolation analysis document is signed (SAS-004).
  Data-residency enforcement must be verified at both the application routing
  layer and the database replication configuration — data stored on the EU
  cluster must not replicate to the US cluster for residency-required tenants
  (SAS-001 extended to geographic isolation).
- **Cormac Sullivan (SRE Lead):** The dedicated-DB provisioning process
  creates a new shared-infrastructure component (the provisioner itself and
  the connection pool manager). Per-tenant quotas must be enforced as hard
  limits before any Enterprise tenant goes live → BLOCK if the provisioner
  does not enforce per-tenant connection pool maximums and query timeout hard
  limits (SAS-005). EU region deployment must have its own SLO targets and
  runbook before any EU customer data is written (SAS-007).
- **Diego Paredes (Plan & Billing Engineer):** The Enterprise upgrade from
  Growth must be recorded as an immutable subscription event before the
  dedicated DB is provisioned → BLOCK if the DB provisioning can be triggered
  without first recording the Growth → Enterprise subscription state
  transition in the event log (SAS-009). The dedicated-DB entitlement must
  not be grantable via admin toggle without an event-log entry (SAS-008).

## 5. Task chains invoked

- `saas-platforms-new-tenant-tier` — primary chain governing isolation
  analysis → tenancy provisioning → quota design → entitlement mapping →
  blast-radius assessment → cross-tenant isolation tests → launch VETO.
- `saas-platforms-subscription-plan-change` — triggered because the
  Enterprise tier introduces a new subscription state (Growth → Enterprise
  upgrade), a new dunning path for Enterprise customers (different grace
  period policy), and a new entitlement (dedicated DB, EU residency option).

## 6. Acceptance

- Isolation analysis document signed by Priyanka Mehta before first
  Enterprise tenant provisioning script is written (SAS-004)
- Per-tenant database isolation: RLS is removed from dedicated instances
  (it is redundant and potentially misleading when the DB is single-tenant);
  application-layer tenant_id filter remains for defence-in-depth (SAS-001)
- Cache keys: confirmed no cross-tenant cache entries exist in the shared
  cache layer for dedicated-DB tenants (SAS-002)
- Per-tenant quotas: connection pool maximum, query timeout, and IOPS limits
  enforced as hard limits in the connection pool manager (SAS-005)
- Circuit-breaker confirmed on the provisioner-to-DB synchronous call chain
  (SAS-006)
- EU region: data-residency routing verified — no cross-region replication
  for residency-required tenants; verified at the replication configuration
  level, not just the application routing level
- Subscription event log: Growth → Enterprise transition recorded as an
  immutable event before dedicated DB is provisioned (SAS-009)
- Entitlement: dedicated-DB feature not grantable via admin toggle without
  a logged, event-log-backed entitlement change (SAS-008)
- Cross-tenant isolation tests pass: attempted cross-tenant reads on
  dedicated-DB path return access-denied across all API, cache, and query paths

## 7. Metrics

- Enterprise tenant provisioning time (p95 target: under 10 minutes from
  subscription event to database-ready state)
- EU region SLO: 99.9% availability for EU dedicated-DB tenants, measured
  separately from US cluster (Cormac sets SLO targets pre-launch)
- **Per-tenant connection pool utilisation at p99** (monitored post-launch;
  any tenant consistently above 80% of pool ceiling triggers quota review
  before it hits the hard limit and affects their SLO)

## 8. References

- `.claude/skills/domains/saas-platforms/skills/salesforce-architect/SKILL.md`
- `.claude/skills/domains/saas-platforms/task-chains.yaml` — `saas-platforms-new-tenant-tier`
- `.claude/skills/domains/saas-platforms/task-chains.yaml` — `saas-platforms-subscription-plan-change`
- `.claude/skills/domains/saas-platforms/pitfalls.yaml` — SAS-001, SAS-002, SAS-004, SAS-005, SAS-006, SAS-008, SAS-009
