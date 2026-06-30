---
name: foia-and-records
description: FOIA (5 USC §552) compliance engineering — records lifecycle, retention schedules, redaction audit trails, and request fulfillment. State equivalents (state sunshine laws, public records acts) follow the same pattern with tighter SLAs. Covers retention classification, tombstoning vs hard delete, exemption-based redaction with legal basis, requester-identity confidentiality, SLA clock machinery, and the "default open" posture for public records. Use when designing any records-producing subsystem, any retention policy, any redaction tool, or any FOIA request-intake workflow.
owner: Yewande Crossland (FOIA Compliance Officer, domain persona)
secondary_owner: Darius Okonkwo (Public Records Engineer, domain persona)
tier: domain:government
scope_tags: [foia, public-records, retention, redaction, transparency, records-management]
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: government
priority: 8
risk_class: medium
stack: []
context_budget_tokens: 700
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/records/**"
  - "**/retention/**"
  - "**/redaction/**"
  - "**/foia/**"
---

# FOIA & Public Records

## Cardinal Rule

**Public records are default-open; the burden of withholding is on
the agency, per record, per exemption.** Software that treats records
as private-by-default and opens them on request is inverted.
Software that treats records as public-by-default and redacts with
logged legal basis is correct.

## The nine FOIA exemptions (5 USC §552(b))

| # | Exemption | Typical applicability |
|---|---|---|
| (b)(1) | National security (classified) | Defense/intel |
| (b)(2) | Internal agency rules/practices (Low 2 + High 2) | Rare for most agencies |
| (b)(3) | Specifically exempted by other statute | Narrow; cite the statute |
| (b)(4) | Trade secrets / confidential commercial | Vendor submissions, contract bids |
| (b)(5) | Deliberative process / attorney-client / attorney work product | Internal drafts, legal memos |
| (b)(6) | Personal privacy (unwarranted invasion) | Personnel, medical, benefits |
| (b)(7) | Law enforcement records (A-F sub-categories) | Investigations |
| (b)(8) | Financial institutions examination | Bank regulators |
| (b)(9) | Geological/geophysical (oil wells) | Niche |

For most agency software the hot exemptions are **(b)(4)**, **(b)(5)**,
**(b)(6)**, and occasionally **(b)(7)**. Every redaction MUST be
labeled with its exemption number + brief legal basis note.

## Records lifecycle (the machinery)

```
created -> classified -> active -> retention-elapsed -> disposition
                                                              |
                           +----------------------------------+
                           |                                  |
                           v                                  v
                        destroyed                         transferred
                      (tombstoned,                       (to NARA or
                     not hard-deleted                    state archive)
                      if a FOIA request
                      is pending)
```

### Hard invariants

1. **Every record has a retention classification** set at creation
   time. "We'll classify it later" = permanent classification of
   "unknown" = audit finding. Use the agency's records schedule
   (NARA GRS or agency-specific).
2. **Retention clock starts from the correct event.** "Date of
   last action" vs "date of closure" vs "date of creation" matters.
   Classify by event type, not by record age alone.
3. **"Deleted" MUST mean tombstoned + audit-logged.** A hard DELETE
   that loses the existence record breaks FOIA accountability. The
   tombstone records: record_id, creation_date, destruction_date,
   retention_schedule_cited, authorized_by, destruction_method.
4. **If a FOIA request is pending on the record, destruction is
   frozen** regardless of retention schedule. Call this the "FOIA
   litigation hold". Automated purge pipelines MUST consult the
   hold list before deleting.
5. **Email and chat are records.** Agency employees generating
   correspondence about official business are creating records.
   Pretending otherwise does not survive discovery.

## Redaction — the thing that actually trips software up

### Wrong way (every agency has done this once)

- Black rectangle overlaid on PDF — underlying text still selectable,
  copyable, and searchable. Redaction is cosmetic.
- CSS `display: none` on sensitive fields in HTML — View Source reveals all.
- Image downscaled "enough" to be unreadable — super-resolution ML
  recovers it.

### Correct way

- **True pixel redaction** on images/PDFs: re-rasterize after
  applying an opaque mask; drop the original text layer; strip
  EXIF and document metadata.
- **Text redaction**: replace with `[REDACTED (b)(6) — personal privacy]`
  at the data layer, not just the rendering layer. The redacted value
  is NOT retrievable via the API for audiences who should not see it.
- **Audit trail per redaction**: record_id, field_id (or bbox for
  image), exemption_applied, legal_basis_note, redacted_by,
  redacted_at, reviewed_by. Auditor can reconstruct every decision.
- **Dual-layer storage**: unredacted + redacted are both first-class
  records. Access control determines which version a requester
  sees. NEVER overwrite the unredacted; destruction follows its
  own schedule.

## Requester identity confidentiality

- **The requester's identity is their own private matter.** In most
  cases the subject of a record has NO right to know who asked for
  it. Software that notifies "John, Jane just requested your file"
  is a privacy breach dressed as a feature.
- Exceptions exist (e.g. Privacy Act access to your own file reveals
  who you are to yourself, trivially). But the default is
  requester-identity is not disclosed to record subjects.
- This propagates to logs, analytics, and webhooks. A FOIA request's
  submitter email does NOT belong in the record's audit trail except
  in a restricted-access field.

## SLA clock mechanics

- **Federal FOIA baseline**: 20 working days to determine (not to
  deliver). Extended 10 working days for "unusual circumstances".
- **State sunshine laws**: usually 3-10 business days, varying
  heavily. Some states have hard hour limits (e.g. Texas: "prompt").
- **Clock starts on receipt of a perfected request** (specific
  enough records + requester contact + fee commitment if applicable).
  An underspecified request does NOT start the clock — engineering
  MUST surface whether the request is perfected.
- **Clock tolled** by: fee disputes, requester clarification requests,
  litigation hold under other law. Tolling events MUST be logged with
  start/end timestamps.

## Schema sketch

```sql
CREATE TABLE records (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    record_type TEXT NOT NULL,
    retention_schedule_id UUID REFERENCES retention_schedules(id),
    retention_start_event TEXT NOT NULL,  -- e.g. 'closure', 'creation'
    retention_start_at TIMESTAMPTZ NOT NULL,
    public_posture TEXT NOT NULL CHECK (public_posture IN
        ('public', 'foia-reviewable', 'classified', 'exempt-pending-review')),
    tombstoned_at TIMESTAMPTZ,  -- NULL while active
    tombstone_reason TEXT,
    tombstone_authorized_by UUID,
    foia_hold BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE redactions (
    id UUID PRIMARY KEY,
    record_id UUID REFERENCES records(id),
    field_or_bbox TEXT NOT NULL,
    exemption TEXT NOT NULL,  -- '(b)(6)', '(b)(4)', ...
    legal_basis TEXT NOT NULL,
    applied_by UUID NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL,
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ
);

CREATE TABLE foia_requests (
    id UUID PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL,
    perfected_at TIMESTAMPTZ,  -- NULL until clarified
    requester_identity_hash TEXT NOT NULL,  -- restricted lookup
    scope_description TEXT NOT NULL,
    sla_deadline_at TIMESTAMPTZ,
    tolled_from TIMESTAMPTZ,
    tolled_reason TEXT,
    closed_at TIMESTAMPTZ,
    closure_disposition TEXT
);
```

## Pre-merge checklist (domain VETO trigger)

- [ ] **Retention classification set at record creation?**
- [ ] **Retention clock anchored to the correct event?**
- [ ] **"Deleted" path tombstones + audit-logs; no hard DELETE?**
- [ ] **FOIA litigation hold consulted before any purge?**
- [ ] **Every redaction carries exemption + legal basis + actor?**
- [ ] **Redaction happens at data layer, not only render layer?**
- [ ] **Requester identity NOT disclosed to record subject?**
- [ ] **SLA clock logic handles perfection + tolling correctly?**
- [ ] **Email/chat retention captured if in scope?**
- [ ] **Destruction path verifies no pending FOIA touches record?**

## References

- 5 USC §552 (Federal FOIA)
- 36 CFR Chapter XII (NARA records management)
- NARA General Records Schedule (GRS)
- DOJ OIP FOIA guidance (annually updated)
- `.claude/skills/domains/government/skills/public-procurement/SKILL.md`
  (vendor-submitted trade secrets — (b)(4) intersection)
