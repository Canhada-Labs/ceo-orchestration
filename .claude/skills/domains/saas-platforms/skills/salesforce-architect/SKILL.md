---
name: salesforce-architect
description: Salesforce platform architecture — Sales / Service / Marketing /
  Experience / Commerce Cloud selection, declarative-first / programmatic-when-justified
  discipline, governor limit budget management, data model design (standard object
  reuse, custom objects, Master-Detail vs Lookup vs Junction), Apex + LWC + Flow
  trade-offs, integration pattern selection (REST / Bulk / Streaming API / Platform
  Events / CDC), and authorisation-model design (profiles / permission sets / OWD
  sharing rules). Use when designing a new Salesforce org, evaluating multi-cloud
  architecture, authoring an ADR for a major platform decision, reviewing data model
  for scalability, selecting integration patterns by volume and latency, or governing
  an automation layer that mixes Flow, Apex, and third-party tools.
owner: Salesforce Architect (domain persona)
tier: domain:saas-platforms
scope_tags: [salesforce, apex, lightning-web-components, flow, governor-limits, multi-cloud, integration-patterns]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/specialized-salesforce-architect.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: saas-platforms
priority: 6
risk_class: medium
stack: [php, typescript, salesforce]
context_budget_tokens: 700
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: true, priority: 6}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: true, priority: 6}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/*.cls"
  - "**/*.trigger"
  - "**/force-app/**"
  - "**/lwc/**"
  - "**/flows/**"
---

# Salesforce Architecture

Salesforce exposes a platform with an enormous declarative surface, tight
governor limits, and a data model that cannot be refactored cheaply after
go-live. The architecture discipline here is not about feature demonstrations —
it is about choosing the right layer, budgeting the right limits, and proving
that the org handles 10× today's volume without a redesign.

## Cardinal Rule

If a declarative tool can deliver the requirement, code is technical debt by
construction; declarative-first is platform discipline, not stylistic
preference. Flow is the declarative destination — Process Builder and Workflow
Rules are deprecated paths, not alternatives. Apex enters the picture only when
Flow cannot guarantee bulk-safe execution of complex branching logic or when
performance profiling on real data volumes shows the declarative path consumes
> 80% of a governor budget.

## Fail-Fast Rule

Halt design and escalate to Owner before writing any implementation plan if ANY:

1. The data model has not been baselined — objects, cardinality, and sharing
   model must be agreed before any automation or integration work begins.
2. Governor limit headroom for the trigger-happy paths has not been calculated
   from real or representative data volumes — not estimated from a sandbox
   with 50 records.
3. The integration design has no failure path — every outbound callout without
   retry logic, circuit-break, and dead-letter handling is a silent data-loss
   vector.
4. PII fields exist or are planned without a documented encryption / masking
   strategy (Shield Platform Encryption or field-level custom encryption; data
   residency requirements resolved).
5. A View All or Modify All permission is on the table without documented
   business justification and a compensating audit control.

A halted design emits one line ("Architecture blocked — condition #N — resume
after team resolves") and zero implementation tickets.

## When to Apply

This skill governs design decisions in any of the following situations:

- **New org setup** — cloud selection, org strategy (single vs multi-org),
  sandbox strategy, DevOps pipeline before any production traffic.
- **Multi-cloud addition** — adding Service, Marketing, or Experience Cloud to
  an existing Sales Cloud org; unified data model and API-budget implications
  must be re-evaluated.
- **Integration design** — connecting Salesforce to an external system for the
  first time or replacing an existing integration pattern.
- **Data model change** — adding a custom object, changing a Master-Detail
  relationship, or redesigning a sharing model on an object with > 100k records.
- **Automation layer review** — any mix of Flows, Process Builders, Workflow
  Rules, Apex triggers touching the same object; overlap analysis and governor
  budget audit required.
- **Security or compliance review** — field-level security audit, sharing
  model review, or regulatory requirement (GDPR / LGPD / SOC 2) affecting
  record visibility and PII handling.
- **Org health triage** — governor limit exceptions in production logs, slow
  page loads attributable to automation chains, or recurring deployment failures.

## Cloud Selection

Cloud selection precedes data model design. Starting with the wrong cloud
generates technical debt that is expensive to migrate. The governing question is:
which business process does this org primarily serve, and what are the capability
gaps if the "default" cloud is chosen alone?

| Cloud | Primary capability | Non-obvious gaps |
|-------|--------------------|-----------------|
| Sales Cloud | Opportunity management, pipeline forecasting, activity capture | Service entitlements, omni-channel routing, marketing journeys are separate licenses |
| Service Cloud | Case management, entitlement SLAs, omni-channel routing, field service | Sales pipeline forecasting is limited; FSL is a separate license |
| Marketing Cloud | Email / SMS / push journeys, audience segmentation, advertising | Transactional email at scale requires separate Messaging SKU; data extensions are not sObjects |
| Experience Cloud | Customer / partner / employee portals with Community licenses | External user licensing is per-login or member, not Salesforce internal seats |
| Commerce Cloud | B2C / B2B storefront, cart, checkout, order management | Separate stack (Salesforce B2C = Demandware origin); limited native CRM integration without connector middleware |

Never start a multi-cloud conversation with "we'll just use Sales Cloud and add
the rest later" — the integration cost between Marketing Cloud and the core
platform (API-based, not native sObject, separate data storage) is a first-class
architectural decision, not a backlog item.

## Declarative-First Discipline

The automation layer has a preferred order from highest to lowest governance
overhead:

```
Flow (destination)
  └── Process Builder (deprecated — migrate to Flow)
        └── Workflow Rule (deprecated — migrate to Flow)
              └── Apex Trigger (only when Flow cannot safely handle)
```

Process Builder is **deprecated** by Salesforce as of Spring '23. Workflow
Rules are **deprecated** as of Summer '23. New automations MUST be built as
Flows. Existing Process Builders and Workflow Rules are a migration backlog item
that should be quantified and time-boxed.

Flow selection within the Flow builder:

- **Record-triggered Flow** — replaces Workflow Rule + Process Builder for
  most record automation. Runs before-save (no DML cost for field updates) or
  after-save. Prefer before-save for field updates to save DML headroom.
- **Scheduled Flow** — batch operations at a scheduled time; replaces
  scheduled Apex for simple field-update scenarios.
- **Screen Flow** — guided UI processes embedded in page layouts or Experience
  pages; replaces Visualforce for simple multi-step data entry.
- **Auto-launched Flow** — invocable by Apex, REST API, or other Flows; the
  reusable subflow building block.

Apex enters the picture when: complex data transformations require iteration
over collections with conditional branching that generates > 5 decision elements
in a Flow (maintainability threshold), callouts with custom retry logic are
needed, or bulkification cannot be guaranteed by the declarative layer.

## Governor Limit Awareness

Governor limits are per-transaction hard stops. Hitting a limit at runtime
silently rolls back the transaction and throws an uncatchable
`LimitException`. The architecture budget must stay below 80% on any code
path the trigger fires in bulk (200 records per DML batch).

| Limit | Synchronous | Asynchronous |
|-------|-------------|--------------|
| SOQL queries | 100 | 200 |
| SOQL rows returned | 50,000 | 50,000 |
| DML statements | 150 | 150 |
| DML rows | 10,000 | 10,000 |
| CPU time | 10,000 ms | 60,000 ms |
| Heap size | 6 MB | 12 MB |
| Callouts | 100 | 100 |
| Future calls (per invocation) | 50 | n/a |

Bulk-safe Apex pattern (mandatory; no exceptions):

```apex
// WRONG — one SOQL per record
trigger AccountTrigger on Account (before insert) {
    for (Account a : Trigger.new) {
        List<Contact> contacts = [SELECT Id FROM Contact WHERE AccountId = :a.Id]; // governor bomb
    }
}

// CORRECT — collect, query once, process in memory
trigger AccountTrigger on Account (before insert) {
    AccountTriggerHandler.handleBeforeInsert(Trigger.new);
}

public class AccountTriggerHandler {
    public static void handleBeforeInsert(List<Account> accounts) {
        Set<Id> ids = new Map<Id, Account>(accounts).keySet();
        Map<Id, List<Contact>> contactsByAccount = new Map<Id, List<Contact>>();
        for (Contact c : [SELECT Id, AccountId FROM Contact WHERE AccountId IN :ids]) {
            if (!contactsByAccount.containsKey(c.AccountId)) {
                contactsByAccount.put(c.AccountId, new List<Contact>());
            }
            contactsByAccount.get(c.AccountId).add(c);
        }
        // process contactsByAccount in memory
    }
}
```

One trigger per object. No business logic in triggers — triggers delegate to
handler classes. This is non-negotiable; a trigger with business logic inline
cannot be unit-tested in isolation.

## Data Model Design

The data model is the most expensive thing to change post-go-live. Get it right
first. Standard objects carry built-in reporting, process templates, and
AppExchange compatibility — a custom object recreating Account, Contact, or
Opportunity is almost always wrong.

Standard object reuse checklist:

| Business entity | Correct standard object | Wrong choice |
|----------------|------------------------|--------------|
| Company / organisation | Account | Custom Company__c |
| Individual person (customer) | Contact / Person Account | Custom Customer__c |
| Sales deal | Opportunity | Custom Deal__c |
| Support ticket | Case | Custom Ticket__c |
| Marketing campaign | Campaign | Custom Campaign__c |

Relationship type selection:

- **Master-Detail** — child record cannot exist without the parent; roll-up
  summary fields are available; ownership and sharing are inherited from parent;
  deleting the master cascades. Use when the child has no independent meaning.
- **Lookup** — child record can exist without the parent; no roll-up summaries
  (workaround: Flow or Apex); sharing is independent. Use when the child has
  independent business meaning or the relationship is optional.
- **Junction object (many-to-many)** — two Master-Detail relationships on a
  custom object. Use when the relationship itself carries attributes (e.g., a
  `ContactRole` between a Contact and an Opportunity).

Sharing model design (establish before any data import):

1. Set Organisation-Wide Defaults (OWD) to the most restrictive access
   justified by the business. "Public Read/Write" on Opportunity is almost
   always wrong for an org with territory-based selling.
2. Open access up through Sharing Rules (criteria-based or ownership-based)
   rather than relaxing OWD.
3. Role Hierarchy grants upward access; use it for manager-subordinate visibility
   where transitive upward access is acceptable.
4. Manual Shares and Apex Managed Sharing for record-level exceptions.

Large data volume (LDV) considerations activate when any single object exceeds
one million records: skinny tables (read-only index projection reducing heap
reads), selective filter indexes, archive strategy (BigObjects or external
archive), and chunked async processing.

## Apex + LWC + Flow Trade-offs

Each layer owns a distinct concern. Mixing layers without justification produces
a maintenance surface no single developer can reason about.

| Concern | Owner | Justification required to diverge |
|---------|-------|------------------------------------|
| Record automation | Flow | Flow cannot handle bulk collection iteration safely |
| UI / user interaction | LWC | Standard page layouts or Screen Flow are insufficient |
| Complex business logic | Apex | Flow maintainability threshold exceeded (> 5 decisions, > 3 object types per transaction) |
| External system callout | Apex (with retry / DLQ) | Never do synchronous callouts from triggers on bulk-capable paths |
| Reusable UI component | LWC | Always; no Visualforce for new development |

Testing requirements by layer:

- **Apex** — minimum 75% line coverage enforced by platform; architecture
  standard is 90%+ with positive + negative + bulk (200-record) test cases.
  No `@isTest SeeAllData=true` except for rare cases with documented reason.
- **LWC** — Jest unit tests for every wire adapter, every imperative Apex call
  mock, and every custom event. Component test coverage must include error states.
- **Flow** — Flow debugging and `FlowTestCoverage` API tests. Fault paths must
  be tested; an unhandled fault in a record-triggered Flow generates a runtime
  error emailed to the admin — not a user-visible message.

## Integration Patterns

Integration pattern selection is determined by volume, latency tolerance, and
ordering requirements. REST API is not the default for everything.

| Pattern | Use when | Volume ceiling | Latency | Ordering |
|---------|----------|---------------|---------|---------|
| REST API (SOAP is deprecated) | Real-time, low-volume, interactive requests | < 1,000 records/call | Synchronous | Not guaranteed |
| Bulk API 2.0 | High-volume data loads / extracts | Up to 100M records/job | Async (minutes) | Not guaranteed |
| Streaming API (PushTopic / Generic) | Server-push CRM Analytics or legacy; legacy only | Low volume | Near-real-time | Not guaranteed |
| Platform Events | Business event bus; cross-system decoupled publish/subscribe | High (100K/day standard) | Near-real-time | Not guaranteed per subscriber |
| Change Data Capture (CDC) | Data sync when field-level change history needed | Object transaction volume | Near-real-time | Sequenced per object |

Platform Events vs CDC decision:

- **Platform Events** — use for "something happened" (business events with a
  custom payload). Custom schema. Producer controls the payload shape.
  72-hour replay window. Correct when the external system needs application-
  level events, not raw field changes.
- **CDC** — use for "something changed" (data synchronisation where field-level
  change tracking matters). Mirrors sObject fields. 3-day retention. Correct
  for data replication pipelines where the consumer needs to know which specific
  fields changed.

Every integration pattern involving outbound callouts requires:

1. **Retry logic** — exponential back-off with jitter, maximum 3 retries.
2. **Circuit breaker** — stop sending if the downstream is returning consistent
   5xx; resume after a back-off window.
3. **Dead-letter queue** — failed messages land in a custom `IntegrationError__c`
   object (or equivalent) with payload, error, timestamp, and retry count.
   Silent discard is never acceptable.
4. **Idempotency** — re-sending a message must not create duplicate records.
   Use external ID fields and `upsert` semantics.

## Authorisation + Sharing Discipline

Least-privilege is the default. Every escalation above the OWD must be
documented with a business justification and reviewed at the access-model
cadence (minimum annually).

| Layer | Scope | Rule |
|-------|-------|------|
| Profiles | Baseline object / field / tab access for a job function | One profile per job function; never clone Standard User repeatedly |
| Permission Sets | Additive grants above the profile baseline | Use for role-based additions; stack Permission Set Groups for complex combinations |
| Permission Set Groups | Bundle of permission sets for a persona | Assign to users; never assign individual permission sets when a group exists |
| OWD | Record visibility floor for all users | Start restrictive; open up through sharing rules |
| Sharing Rules | Criteria or ownership-based access grants | Use instead of relaxing OWD |
| Role Hierarchy | Upward visibility for managers | Ensure the hierarchy reflects real reporting lines; phantom roles are a governance debt |

**View All** and **Modify All** on any object are administrative superpowers.
Granting them to a non-admin user requires: documented business case, Owner
approval, a compensating audit log review cadence, and review in the next
access certification cycle. Granting them to a profile used by more than one
person requires an ADR.

## Anti-patterns

| Anti-pattern | Why it fails | Correct approach |
|-------------|--------------|-----------------|
| Apex when Flow suffices | Unnecessary code surface; test overhead; harder to change by admins | Build in Flow; only escalate when governor budget or complex branching justifies it |
| Hard-coded IDs in Apex | IDs differ across orgs and sandboxes; deployment breaks silently | Store IDs in Custom Metadata, Custom Labels, or query by DeveloperName |
| Governor-limit denial ("we'll optimise later") | Governor exceptions roll back the entire transaction; production failures are not a backlog item | Budget limits during design; proof by running the bulk-safe test (200-record trigger) before merging |
| Recreating standard objects | Loses platform-native reporting, process templates, AppExchange app compatibility | Extend standard objects with custom fields; use record types for sub-type variation |
| View All / Modify All escalation without justification | Exposes all records of the object to the grantee; bypasses territory, OWD, and sharing rules | Scope access via Permission Set + Sharing Rules; use Named Credentials for integration users |
| SOQL inside loops | Each loop iteration consumes one of the 100 synchronous SOQL queries; 201 records = LimitException | Collect IDs, single query outside the loop, process results in a map |
| Multiple triggers per object | Execution order is undefined; handlers interfere | One trigger per object; all logic in handler classes; use a trigger framework (FFLIB or equivalent) |
| Process Builder / Workflow Rule for new automation | Deprecated tools; Salesforce investment is in Flow; mixed-layer automation chains generate unpredictable order-of-execution bugs | Build in Flow from the start; schedule existing PB/WF migration |
| Synchronous callout from bulk trigger | 200 records × 1 callout each = 200 callouts; synchronous callouts from triggers are disallowed by the platform | Use Platform Events or Queueable Apex for async callout fan-out |

## Cross-References

- `core/security-and-auth` — authentication + authorisation patterns applicable
  to Connected App OAuth flows, Named Credentials, and Shield encryption design.
- `core/architecture-decisions` — ADR format and governance; every significant
  Salesforce platform decision (cloud selection, data model schema, integration
  pattern) produces an ADR.
- `domains/sales/skills/pipeline-analyst` — pipeline metrics, forecast category
  semantics, and territory model; informs Opportunity object design and sharing
  rule cardinality.

## ADR Anchors

- **ADR-058** (Brainstorm Gate and Two-Pass Review) — every Salesforce
  platform decision (cloud selection, data model change, integration
  pattern, sharing-rule update) is subject to two-pass adversarial
  review before org-level apply.
- **ADR-060 amendment §Bulk creative-authoring path** — anchors this
  skill's tier, scope_tags, and `inspired_by` relationship conventions.
