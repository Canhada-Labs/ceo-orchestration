---
name: public-procurement
description: Public-sector procurement engineering — bid confidentiality until award, contractor vetting against debarment lists, conflict-of-interest declarations, audit trails for every contract decision, and set-aside compliance. Federal FAR / DFARS patterns with state/local equivalents (state procurement codes, local small-business ordinances). Use when designing RFP-publication, bid-intake, bid-opening, evaluation, award, or contract-administration subsystems. The "why not the lowest bid?" audit trail is load-bearing — every award decision must survive a protest.
owner: Senator Rafael Hoelzle (Procurement Integrity Officer, domain persona)
secondary_owner: Darius Okonkwo (Public Records Engineer, domain persona)
tier: domain:government
scope_tags: [procurement, far, dfars, debarment, conflict-of-interest, set-aside, bid-confidentiality, audit-trail]
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
  - "**/procurement/**"
  - "**/bids/**"
  - "**/awards/**"
  - "**/contracts/**"
  - "**/rfp/**"
---

# Public Procurement Integrity

## Cardinal Rule

**Every procurement decision must survive a bid protest.** That
means: bid confidentiality preserved until award, vendors vetted
against debarment lists at decision time, every decision-maker has
an active COI declaration on file, and the reasoning — especially
"why NOT the lowest bid" — is logged with the decider and timestamp.

## The procurement lifecycle (the bits software touches)

```
Market research -> RFP published -> Q&A period -> bids received
       |                                              |
       |                                              v
       |                                        Bid sealed box
       |                                   (encrypted until open)
       |                                              |
       v                                              v
Requirements     Solicitation                 Public bid opening
definition        package                   (scheduled time -
                  (SOW/SOO/PWS)              no peeking)
                                                     |
                                                     v
                                              Technical evaluation
                                              (scored by panel,
                                               COI cleared)
                                                     |
                                                     v
                                              Cost evaluation
                                              (vendor vetting -
                                               SAM.gov debarment
                                               check)
                                                     |
                                                     v
                                              Source selection
                                              decision memo
                                              (why this vendor)
                                                     |
                                                     v
                                              Award notice -
                                              losers debriefed
                                                     |
                                                     v
                                              Protest window
                                              (typically 10 days
                                               federal; varies
                                               state/local)
```

## Bid confidentiality — the ledger version

### Invariants

1. **Bids MUST be encrypted at rest from submission until scheduled
   bid-opening time.** Any agency employee (including procurement
   officers) who can decrypt a bid before bid-opening is a leak
   surface. Time-based key release or sealed-bid service is the
   control.
2. **Log lines MUST NOT emit bid amounts before bid-opening.**
   Observability breadcrumbs that include `bid_total=$127,450`
   from the intake workflow are a disclosure. Log bid receipt as
   an event with vendor ID + submission timestamp; log the amount
   only after opening.
3. **No premature viewing.** Access logs on the bid store MUST
   flag any read before the bid-opening timestamp. A false positive
   is an audit event worth investigating.
4. **Post-award**: winning bid becomes largely public (with trade-secret
   (b)(4) redactions); losing bids stay more protected but are
   discoverable on FOIA with heavier redaction.

### Code-level pattern

```python
def record_bid(bid: Bid, rfp: RFP) -> None:
    if rfp.bid_open_at > now():
        # Encrypt with time-released key; store ciphertext only.
        ciphertext = seal_until(bid.serialize(), until=rfp.bid_open_at)
        bid_store.put(rfp.id, bid.vendor_id, ciphertext)
        # Audit log - no amount, no content detail.
        emit_audit("bid_received", rfp_id=rfp.id, vendor_id=bid.vendor_id)
    else:
        raise ProcurementError("bid received after bid-opening")
```

## Contractor vetting — debarment + exclusion

- **SAM.gov Exclusions (federal)** lists debarred, suspended, and
  otherwise-excluded entities. Check at: proposal receipt, pre-award,
  AND at contract modification. Excluded entity = cannot receive
  federal funds.
- **State debarment lists** exist in most states; pattern mirrors
  SAM.gov but separate databases.
- **Parent/subsidiary resolution**: a debarred parent often taints
  subsidiaries. Vendor vetting checks the full corporate tree, not
  just the named entity.
- **Responsibility determination**: beyond debarment, the contracting
  officer makes a "responsibility" finding (past performance,
  financial resources, integrity). This is a documented decision,
  not a vibe.

## Conflict-of-interest (COI) machinery

### Personal COI

- **Every decision-maker in the procurement chain** (requirements
  author, evaluation panel member, source selection authority,
  contracting officer) MUST have a current financial-disclosure
  form on file BEFORE participating. "Current" typically means
  within the last 12 months.
- **Specific-matter COI**: if a decision-maker has a financial
  interest in the outcome (stock in bidder, family member employed
  by bidder, prospective employment), they recuse.
- **Recusal is logged**: who recused, what decision, which
  alternative decision-maker took over. Post-hoc discovery of
  unrecused COI is a protest goldmine.

### Organizational COI (OCI)

- A contractor that wrote the SOW may be excluded from bidding on
  the work it specified (biased-ground-rules OCI).
- A contractor providing advisory services may be excluded from
  related procurements (unequal-access-to-information OCI).
- OCI mitigation plans are documented artifacts.

### Code-level enforcement

```python
def assign_evaluator(panel_id, person_id, rfp_id):
    coi = get_coi_disclosure(person_id)
    if not coi or coi.filed_at < now() - timedelta(days=365):
        raise ProcurementError("COI disclosure stale or missing")
    if person_id in get_recusals(rfp_id):
        raise ProcurementError("person recused on this RFP")
    # Check declared interests against bidder list
    for bidder in get_bidders(rfp_id):
        if coi.has_financial_interest_in(bidder):
            raise ProcurementError(f"undeclared COI with {bidder}")
    return assign(panel_id, person_id)
```

## "Why not the lowest bid?" — the award rationale log

Every award decision MUST produce a source selection decision document
that captures:

- Decision-maker identity + title
- Evaluation panel members + their scoring (signed off individually)
- Technical evaluation summary per bidder
- Price evaluation summary per bidder
- **Trade-off rationale** — particularly if a higher-priced bidder
  was selected (best-value procurement). "The $1.2M bid was selected
  over the $950K bid because technical score 92 vs 68 and past
  performance rating Exceptional vs Satisfactory."
- Date, signature, COI attestations current

This document IS the protest defense. A missing or hand-wavy
rationale is a sustained protest.

## Set-aside and socioeconomic compliance

- **Small-business set-asides**: portion of contracts reserved for
  small businesses (federal: various size standards per NAICS code).
  Automated size verification against SAM.gov registration.
- **Socioeconomic categories**: 8(a), WOSB (women-owned), SDVOSB
  (service-disabled veteran-owned), HUBZone. Each has distinct
  eligibility verified at award.
- **Recertification**: a contractor's size/socio status can change
  mid-contract. Long-term IDIQs require periodic recertification.
- State/local may have **minority-owned, veteran-owned, local
  preference** programs with their own rules.

Software that routes set-aside procurements MUST NOT award to a
contractor who lost eligibility between registration and award.

## Audit trail schema sketch

```sql
CREATE TABLE procurement_decisions (
    id UUID PRIMARY KEY,
    rfp_id UUID NOT NULL,
    decision_type TEXT NOT NULL,  -- 'panel_assignment', 'bid_opening', 'award', ...
    decided_by UUID NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL,
    justification_text TEXT NOT NULL,  -- required non-empty
    coi_attestation_id UUID NOT NULL,  -- MUST be current
    supersedes_decision_id UUID,       -- if a reversal
    protest_relevant BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE coi_disclosures (
    id UUID PRIMARY KEY,
    person_id UUID NOT NULL,
    filed_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    declared_interests JSONB NOT NULL
);

CREATE TABLE debarment_checks (
    id UUID PRIMARY KEY,
    vendor_id UUID NOT NULL,
    rfp_id UUID NOT NULL,
    source TEXT NOT NULL,  -- 'SAM.gov', 'state-X-list', ...
    check_at TIMESTAMPTZ NOT NULL,
    result TEXT NOT NULL,   -- 'clear', 'excluded', 'under-review'
    raw_response_sha TEXT NOT NULL
);
```

## Pre-merge checklist (domain VETO trigger)

- [ ] **Bid ciphertext stored; no pre-opening decrypt path?**
- [ ] **No bid amount emitted in logs pre-opening?**
- [ ] **SAM.gov (or state equivalent) debarment check at proposal,
      pre-award, and contract-mod time?**
- [ ] **Parent-company corporate tree considered in debarment check?**
- [ ] **Every decision-maker has current COI disclosure on file?**
- [ ] **Recusal handling: log who recused and who replaced them?**
- [ ] **Award rationale persisted with trade-off explanation?**
- [ ] **Set-aside eligibility verified at award, not just registration?**
- [ ] **Protest window notification sent to losers?**
- [ ] **Audit log is append-only; no UPDATE on procurement_decisions?**

## References

- Federal Acquisition Regulation (FAR, 48 CFR Chapter 1)
- DFARS (48 CFR Chapter 2) — Defense supplements
- SAM.gov Exclusions database
- 18 USC §208 (federal conflict of interest statute)
- 41 USC §2101-2107 (Procurement Integrity Act)
- GAO bid protest jurisdiction (4 CFR Part 21)
- `.claude/skills/domains/government/skills/foia-and-records/SKILL.md`
  (bid records retention + (b)(4) trade-secret intersection)
