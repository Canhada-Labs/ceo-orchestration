---
name: korean-business
description: |
  Korea-specific business skill covering chaebol relationship navigation,
  poom-ui (품의) consensus-approval mechanics, PIPA (Personal Information
  Protection Act) and PIPC compliance, Fair Trade Act constraints on
  conglomerate conduct, hierarchical Confucian register calibration,
  military-service awareness in hiring, hwesik (회식) culture, vendor-
  onboarding ritual, and IP enforcement specifics. Use when: entering or
  advancing a commercial relationship with a Korean counterpart for the
  first time; evaluating PIPA lawful-basis or cross-border transfer
  obligations; navigating title-seniority protocol in a chaebol subsidiary;
  assessing hiring timelines affected by mandatory military service; or
  preparing a vendor-qualification package for a mid-cap or chaebol
  procurement team.
owner: Jae-won Park (Korean Business Navigator, domain persona)
tier: domain:i18n-business
scope_tags: [korea, korean-business, chaebol, pipa, hierarchical-register, hwesik, kfta]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/specialized-korean-business-navigator.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: i18n-business
priority: 8
risk_class: low
stack: []
context_budget_tokens: 500
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
  - "**/korea/**"
  - "**/pipa/**"
---

# Korean Business Navigator

## Cardinal Rule

Relationship precedes transaction. No commercial outcome is produced by
this skill without first assessing the current relationship stage
(stranger / acquaintance / trusted contact / partnership) and calibrating
all advice — timing, channel, register, and content — to that stage.
Advice that is technically correct but relationship-stage-mismatched
produces real-world damage. Every output is subject to the two-pass
review gate (ADR-058).

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- The counterpart's corporate type (chaebol subsidiary, mid-cap, SME,
  startup) and approximate hierarchy level of the primary contact are
  unknown; advice calibrated to the wrong entity type causes irreversible
  relationship damage.
- A PIPA-scoped data transfer (personal information of Korean residents
  to a non-domestic processor or controller) is under design without an
  identified lawful basis and PIPC compliance officer review.
- A hiring decision affecting a candidate in mandatory-service age range
  (18–28, male) omits military-service status from the timeline model,
  producing a false availability assumption.
- A negotiation sequence calls for a direct price discussion in the first
  or second meeting; this terminates relationship development in all Korean
  corporate contexts without exception.
- A vendor-qualification submission is being sent without a formal 소개
  (introducer referral); cold submissions to chaebol procurement units
  carry less than five percent acknowledgement rate.

Never substitute general East-Asian etiquette heuristics for Korea-
specific protocol; Japan, China, and Korea share surface similarities and
differ materially on hierarchy mechanics, drinking-culture obligations,
and IP enforcement posture.

## When to Apply

Apply this skill when:

- Initiating or advancing a B2B relationship with a Korean company and
  the counterpart has not been worked with before.
- Designing a poom-ui (품의) timeline for a procurement or partnership
  proposal and the realistic approval-chain duration must be estimated.
- Reviewing a draft contract for Korean counterparty for clauses that
  conflict with Korean Fair Trade Act (KFTA) restrictions on unfair
  subcontracting, superior-bargaining-position abuse, or exclusive-dealing
  arrangements involving chaebol affiliates.
- Evaluating whether personal-information processing in a Korea-market
  product satisfies PIPA and PIPC obligations (lawful basis, consent
  form language, cross-border transfer safeguards, data-subject rights).
- Preparing a workforce plan for a Korean subsidiary where male employees
  in the 18–28 age range may be subject to mandatory military service
  (의무 복무).
- Structuring an IP enforcement action in Korea — trademark, patent, or
  trade-secret — where procedural differences from US/EU practice affect
  the strategic sequence.

Do not apply this skill to general APAC market entry without Korea-
specific scope; route broad regional strategy to
`domains/i18n-business/skills/cultural-intelligence`.

## Chaebol Relationship Frame

Chaebol (재벌) are vertically integrated conglomerates. Working with a
chaebol subsidiary requires understanding that the subsidiary's procurement
authority is constrained by group-level policy, that senior decisions
escalate inside the approval chain well above the contact's title, and
that the relationship is evaluated at multiple hierarchy levels
simultaneously.

**Approval-chain duration by entity type:**

| Entity type | Poom-ui duration | Notes |
|-------------|-----------------|-------|
| SME (< 300 employees) | 3–6 weeks | Contact may have direct approval authority |
| Mid-cap | 6–10 weeks | 2–3 approval tiers above primary contact |
| Chaebol subsidiary | 10–16 weeks | Group-level ratification common for >₩100M |
| Startup (< Series B) | 1–3 weeks | Western-influenced; hierarchy still applies |

**Poom-ui stage signals:**

- Contact requests detailed pricing, scope, and delivery timeline:
  internal approval document (품의서) drafting has begun.
- Contact says "상부에서 검토 중입니다" (upper management is reviewing):
  the approval chain is moving; do not accelerate follow-up.
- Silence of 5–10 days after a meeting at chaebol: internal discussion
  is normal; do not interpret as disinterest.
- Contact goes quiet after requesting references and case studies: the
  approval document was not approved; a graceful re-entry in 60–90 days
  is appropriate.

**Title-addressing rules:**

All Korean titles take the honorific suffix 님 (nim) in direct address.
Titles used in external business contact from most to least senior:
회장님 (Chairman), 사장님 (CEO/President), 부사장님 (VP), 전무님
(Senior Managing Director), 상무님 (Managing Director), 이사님
(Director), 부장님 (General Manager), 차장님 (Deputy Manager),
과장님 (Manager), 대리님 (Assistant Manager). Using a counterpart's
given name before they invite it is relationship-damaging in all chaebol
and mid-cap contexts without exception.

## PIPA Compliance

Korea's Personal Information Protection Act (PIPA, 개인정보 보호법) and
its enforcement authority PIPC (Korea Personal Information Protection
Commission) impose obligations that differ from GDPR in structure and
enforcement posture.

**Key PIPA obligations:**

- **Lawful basis:** Collection requires one of: (a) data-subject consent
  with granular separate-consent checkboxes per purpose; (b) statutory
  obligation; (c) vital interest; (d) public-task basis. Legitimate-
  interest processing (GDPR Art. 6(1)(f)) does not have a direct Korean
  equivalent; consent is the default commercial basis.
- **Consent language:** Consent forms must state the items collected,
  purpose, retention period, third-party recipients (named, not generic),
  and the right to refuse with consequences disclosed. Bundled consent
  for multiple purposes is prohibited; each purpose requires a separate
  checkbox.
- **Cross-border transfer:** Personal data of Korean residents transferred
  to a foreign processor or controller requires either (a) PIPC
  adequacy recognition of the destination country, (b) contractual
  safeguards meeting PIPC standard clauses, or (c) explicit data-
  subject consent to the specific transfer.
- **Data-subject rights:** Inspection, correction, deletion, and
  processing-suspension rights must be exercisable via a documented
  channel; response deadline is 10 days from request.
- **Breach notification:** PIPC notification is required within 72 hours
  of discovering a breach affecting 1,000 or more data subjects.
- **DPO equivalent:** Companies processing sensitive information or
  operating at scale above PIPC thresholds must designate a Privacy
  Officer (개인정보 보호책임자) registered with PIPC.

Any data-architecture decision involving Korean resident data is routed
through `core/compliance-lgpd` for LGPD parallel-obligation analysis
where the same dataset spans Korean and Brazilian residents.

## Hierarchical Register Discipline

Korean has a formal speech register (존댓말, jondaemal) and an informal
register (반말, banmal). In all initial B2B interactions and throughout
the first three meetings, formal register is mandatory. Switching to
informal register before the counterpart initiates it is presumptuous
and relationship-damaging. The counterpart initiating 반말 is an explicit
trust signal and may be reciprocated.

**Written communication register by stage:**

| Stage | Channel | Register signal |
|-------|---------|----------------|
| First contact | Email or KakaoTalk | Full formal; open with 안녕하세요 + title + 님 |
| Acquaintance (2–3 meetings) | KakaoTalk preferred | Formal; light sentence-final softeners acceptable |
| Trusted contact | KakaoTalk, phone | Semi-formal; follow counterpart lead |
| Partnership | Any | Follow counterpart; match their register, never exceed informality |

**Register enforcement in group channels:**

In any KakaoTalk group chat containing Korean counterparts, formal Korean
is required regardless of individual-relationship depth. Sending English
in a Korean group chat signals an expectation that the Korean speakers
accommodate the sender; this is a hierarchy inversion and damages
position. English is acceptable in one-on-one direct messages once the
relationship supports it.

## Hiring and Military-Service Awareness

Mandatory military service (의무 복무) applies to Korean male citizens
generally between ages 18 and 28. Active-service duration is 18–21
months depending on branch. Supplemental reserve obligations (예비군)
extend to age 40 for 2–4 days per year.

**Workforce-planning implications:**

- Hiring timelines for male candidates in the 18–28 range require
  confirmation of military-service status: completed, in-progress, or
  deferred. An in-progress or imminent service obligation produces a
  workforce availability gap of 18–21 months.
- Candidates who have completed service frequently carry a rank equivalent
  (병장, sergeant, being the most common completion grade) that Korean
  colleagues treat as a social-seniority signal in early team dynamics.
- Roles requiring security clearance may be constrained by service-branch
  history. Verify clearance eligibility before staffing security-
  sensitive positions.
- Equal-opportunity frameworks (particularly for foreign subsidiaries
  operating in Korea) must not treat military-service status as a
  disqualifying factor; it is a legally protected class indicator.

## Hwesik Culture

Hwesik (회식) — company dining and drinking gatherings — is a regular
team-cohesion mechanism in Korean corporate culture. Attendance is a
professional obligation, not a social option. Declining repeatedly marks
the decliner as a team outsider and impairs internal relationship capital.

**Protocol obligations:**

- Pour for counterparts before pouring for oneself; use two hands or one
  hand supported at the wrist when pouring for a senior.
- Accept the first serving with both hands; take at least one sip before
  setting the glass down; flat refusal of the first serving is disruptive.
- After the first round, moderation is accepted; the phrase "한 잔만 더"
  (just one more) is more graceful than a flat stop.
- The most senior person present opens the meal (chopsticks first); wait
  for that signal before eating.
- Payment: the most senior present typically pays for the first venue
  (1차). A junior offering to pay for a later stop (2차, 3차) or the
  following day's coffee is the appropriate reciprocity gesture.
- Designated-driver norms are increasing in Korean corporate culture;
  non-drinkers who attend and participate in the social dimension without
  consuming alcohol are accepted in progressive companies; at traditional
  chaebol this tolerance is lower.

## Relationship Building and Vendor Partnership Ritual

Vendor onboarding in mid-cap and chaebol contexts follows a defined
ritual sequence. Deviating from the sequence by accelerating or skipping
stages produces a perception of pressure, reducing the counterpart's
internal willingness to champion the vendor through the approval chain.

**Ritual sequence:**

1. **소개 (Sojae — Introduction):** A warm introduction from a mutual
   contact of equivalent or superior standing to the target. Cold outreach
   to chaebol procurement without a 소개 carries an acknowledgement rate
   below five percent. The introducer's social capital is partially
   transferred to the introduced party; protect the introducer's
   reputation throughout.
2. **첫 미팅 (First Meeting):** Listen more than pitch. Ask about the
   counterpart's challenges. Do not discuss pricing. Bring printed
   materials with company profile and reference cases.
3. **내부 검토 (Internal Review — 2–4 weeks):** Provide materials the
   contact can circulate internally without requesting access. The contact
   is the internal champion; equip them, do not manage around them.
4. **품의서 요청 (Approval-document Request):** The contact requests
   specific scope, pricing, and timeline detail; this is the first moment
   pricing discussion is appropriate.
5. **결재 라인 (Approval Chain):** Wait. One status inquiry per week
   maximum. "상부에서 검토 중입니다" means the process is active.
6. **계약 (Contract):** Legal review, company seal (도장), execution.
   Contracts rarely fall apart at this stage; the approval chain is the
   true decision gate.

**Proof engagement strategy:**

For a new relationship where trust is not yet established, a bounded
engagement (two to three weeks, fixed deliverable, fixed price) framed
as mutual evaluation reduces the counterpart's perceived commitment risk.
The proof engagement is the sales pitch; over-delivery is the expected
posture. Full-engagement pricing is not discussed during the proof period.

## IP and Enforcement Specifics

Korean IP enforcement differs from US and EU practice in procedural
sequence and strategic implications.

**Patent:** The Korean Intellectual Property Office (KIPO) first-to-file
system means patent applications should be filed in Korea before any
public disclosure. Provisional applications are not available; utility-
model registration (실용신안) provides a faster lower-cost protection
path for incremental innovations.

**Trademark:** Identical or confusingly similar marks to a registered
Korean mark are rejected regardless of prior use. Trademark squatting is
prevalent for foreign brands entering Korea; pre-entry search and
registration is mandatory before any public Korea market presence.

**Trade secret:** Korea's Unfair Competition Prevention and Trade Secret
Protection Act (부정경쟁방지 및 영업비밀보호에 관한 법률) provides civil
and criminal remedies. Criminal prosecution of trade-secret theft by
former employees is more frequently pursued in Korea than in most EU
jurisdictions; document control and departure-audit protocols are
operationally important.

**Fair Trade Act constraints:** Chaebol group conduct is subject to
Korea Fair Trade Act (KFTA) restrictions on unfair subcontracting
(하도급법), superior-bargaining-position abuse, and exclusive-dealing
arrangements. Contracts with chaebol affiliates should be reviewed for
clauses that the KFTC has previously sanctioned as coercive; most
commonly: retroactive discount demands, unilateral delivery-condition
changes, and intellectual-property assignment without compensation.

## Anti-patterns

| Anti-pattern | Consequence | Correct Approach |
|--------------|-------------|-----------------|
| Cold outreach to chaebol procurement | < 5% acknowledgement rate; no re-entry path | Obtain 소개 from a contact of equivalent standing before any outreach |
| Requesting a decision timeline at the first meeting | Signals ignorance of poom-ui; counterpart disengages | Accept the poom-ui timeline; ask only what information is needed to prepare the approval document |
| Bypassing primary contact to reach their superior | Relationship-ending for the primary contact; marks the sender as untrustworthy | Work exclusively through the entry-point contact regardless of their apparent seniority |
| Introducing pricing before the second meeting | Reduces vendor to transactional commodity status | Follow the vendor-ritual sequence; pricing discussion is appropriate only when the contact requests it |
| Interpreting silence after a meeting as rejection | Premature disengagement or excessive follow-up that exhausts counterpart goodwill | Allow 5–10 days at SME / 10–14 days at chaebol before a single status inquiry |
| Using informal register before it is offered | Perceived as disrespectful; damages trust with senior stakeholders present | Default to 존댓말 in all initial contact; mirror register shift only after counterpart initiates |
| Substituting GDPR analysis for PIPA compliance | PIPC enforcement action; separate-consent requirement missed | Apply PIPA obligation analysis independently; GDPR adequacy recognition does not imply PIPA compliance |
| Treating hwesik attendance as optional | Team-outsider status; reduced internal advocacy for the vendor or colleague | Attend first-invitation hwesik; moderation after the first serving is accepted |
| Omitting military-service status from hiring timeline | False availability assumptions cause project-staffing gaps | Confirm service status for all male candidates age 18–28 before committing to availability dates |
| Filing trademark after Korea public launch | Mark squatting or prior-registration rejection | Register trademark with KIPO before any public Korea market presence |

## Cross-References

- `core/compliance-lgpd` — parallel personal-data obligations for
  datasets that span Korean and Brazilian residents; PIPA and LGPD share
  consent-granularity requirements but differ in lawful-basis structure
- `domains/i18n-business/skills/cultural-intelligence` — broad
  cross-cultural communication frame for multi-market contexts where
  Korea-specific depth is not required

## ADR Anchors

- **ADR-058** — two-pass review gate: all relationship-stage assessments,
  PIPA compliance evaluations, and vendor-qualification documents produced
  under this skill are subject to adversarial second-pass review before
  being treated as final outputs.
