---
plan_id: PLAN-EXAMPLE-PMG
title: "Manage a mid-program scope expansion request for a regulated enterprise feature"
status: draft
owner: ceo
level: L3
squad: project-management
profile: core,project-management
created_at: 2026-05-10
---

# Example PLAN — Mid-Program Scope Expansion with Enterprise Commitment

> **This is an illustrative example**, not a real plan. It shows
> how the project-management squad coordinates on a high-pressure
> scope change request that touches all three VETO scopes: delivery
> commitment (Renata), program dependency cascade (Marcus), and risk
> register integrity (Yara).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`

## 1. Problem

The enterprise sales team has received a request from a strategic account
(ARR $850K) to include a custom compliance export feature in the Q3
release, 6 weeks before the planned launch date. The account has stated
they will not renew without the feature. The feature was not in the
original Q3 scope. Engineering estimates 3-4 weeks of work. Two other
cross-squad dependencies are due in the same window.

Sources:
- Sales: verbal commitment made to the account ("we'll see what we can do")
- Engineering: 3-4 week estimate, requires API team dependency
- Program dependency graph: API team has existing Q3 commitment for a
  different squad (Squad B) due week 10

## 2. Scope

**In:**
- Scope change control process for the compliance export feature
- Trade-off analysis: what is deferred from Q3 to accommodate the feature
- Cross-program dependency impact on Squad B's API team dependency
- Risk register update for new schedule and dependency risks
- Executive status report update reflecting program impact

**Out:**
- Technical design of the compliance export feature (core engineering)
- Account renewal negotiation (Sales and CSM)
- Contract amendment for the new feature (legal scope)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Request intake | Renata Souza | Scope change request documented; engineering estimate confirmed in writing |
| P2 — Cascade analysis | Marcus Webb | Dependency graph impact: Squad B API team slot conflict identified (PMG-003) |
| P3 — Risk register | Yara Al-Hassan | 2 new risks registered: schedule compression + API team contention (PMG-005) |
| P4 — Trade-off document | Renata Souza | 2 Q3 features deferred; trade-off presented to sales and account (PMG-001) |
| P5 — Sign-off | All VETO holders | Renata + Marcus + Yara written sign-off; account accepts trade-off |
| P6 — Sprint replan | Priscilla Ng | Sprint goals updated; unplanned-work ratio tracked (PMG-011) |
| P7 — Status report | Marcus Webb | Executive RAG status updated to AMBER reflecting compression (PMG-008) |

## 4. Risk axes and VETO holders

- **Renata Souza (Senior PM):** Scope added without a documented trade-off
  → BLOCK if any Q3 feature is not explicitly designated as deferred in
  writing, accepted by the requester (PMG-001). External commitment before
  engineering sign-off → BLOCK — the sales team's verbal "we'll see what
  we can do" must not escalate to a written commitment before the trade-off
  is agreed (PMG-002).
- **Marcus Webb (Program Manager):** API team now has two competing
  commitments in week 10 → BLOCK if program status is reported GREEN while
  API team contention is unresolved (PMG-008); BLOCK if Squad B's dependency
  is not explicitly renegotiated before the compliance export work begins
  (PMG-003).
- **Yara Al-Hassan (Risk Coordinator):** Two new risks (schedule compression,
  API contention) must be registered before any commitment is made to the
  account → BLOCK if risks are not in the risk register with probability and
  impact scores (PMG-005).

## 5. Task chains invoked

- `project-management-scope-change-control` — primary chain for processing
  the compliance export feature request
- `project-management-program-risk-review` — triggered immediately by the
  scope change request to update risk register before any external commitment
- `project-management-retrospective-cycle` — skipped (mid-sprint; will be
  invoked at end of sprint to capture scope management lessons)

## 6. Acceptance

- Written change order exists: compliance export added + 2 features deferred,
  with requester sign-off on the trade-off (PMG-001)
- No external commitment made before engineering sign-off obtained (PMG-002)
- Squad B API team dependency renegotiated with explicit written commitment
  from the API team lead (PMG-003)
- 2 new risks registered (schedule compression, API contention) with owners
  and mitigation plans (PMG-005)
- Program RAG status reflects AMBER for Q3 scope compression; no GREEN
  reported while API contention is open (PMG-008)
- Sprint goal updated to reflect actual achievable scope; unplanned-work
  tracking tag applied to compliance export tickets (PMG-011)

## 7. Metrics

- Q3 release on-time delivery (adjusted scope)
- Account renewal confirmed (lagging — owned by Sales, not PM)
- **Program schedule variance** (monitored weekly: actual delivery date vs
  Q3 target, tracked until the release ships)

## 8. References

- `.claude/skills/domains/project-management/skills/project-shepherd/SKILL.md`
- `.claude/skills/domains/project-management/skills/experiment-tracker/SKILL.md`
- `.claude/skills/domains/project-management/task-chains.yaml` — `project-management-scope-change-control`
- `.claude/skills/domains/project-management/task-chains.yaml` — `project-management-program-risk-review`
