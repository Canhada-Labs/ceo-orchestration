---
name: assessment-integrity
description: Engineering anti-cheat, proctoring, and grade-tamper resistance for K-12 and higher-ed assessment platforms. Covers question randomization, secure-browser integration, time-attack detection, grade audit trails (append-only), question-bank access control, proctoring governance with accessibility allowlist, and the double-grading invariant. Use when designing assessment delivery, gradebook writes, proctoring features, or question-bank tooling. Combines with security-and-auth (core) for RLS/RBAC and with state-machines-and-invariants (core) for grade-state transitions.
owner: Konstantin Ferreira (Assessment Integrity Engineer, domain persona)
secondary_owner: Jin-Soo Ramirez (Accessibility & Inclusion Engineer, domain persona)
tier: domain:edtech
scope_tags: [assessment, anti-cheat, proctoring, grades, audit-trail, question-bank]
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: edtech
priority: 8
risk_class: low
stack: []
context_budget_tokens: 600
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
  - "**/assessments/**"
  - "**/grades/**"
  - "**/gradebook/**"
  - "**/proctoring/**"
  - "**/question-bank/**"
  - "**/exams/**"
---

# Assessment Integrity

## Cardinal Rule

**A grade is a promise to a student's future. Append-only or it
didn't happen.** Every grade mutation is a new event with actor_id,
reason_code, previous_grade_id. The gradebook is a ledger, not a
spreadsheet.

## The four surfaces that must co-sign a grade

1. **Student attempt** — the raw answers + response timing + device fingerprint
2. **Rubric score** — auto-grade (MC, coded rubric) OR primary human grade
3. **Moderator score** (when required) — second grader for high-stakes
   assessments; must reconcile with rubric score within tolerance
4. **Audit trail** — append-only log of all four surfaces + every edit

If any surface is missing, the grade is provisional.

## Grade table schema (append-only)

```sql
CREATE TABLE grade_events (
  id                bigserial PRIMARY KEY,
  student_id        uuid NOT NULL,
  assessment_id     uuid NOT NULL,
  attempt_id        uuid NOT NULL,
  state             text NOT NULL,    -- 'rubric_scored' | 'moderator_scored' | 'teacher_override' | 'regrade_request' | 'final'
  score             numeric(6,3),     -- nullable until scored
  max_score         numeric(6,3) NOT NULL,
  rubric_version    text NOT NULL,
  actor_id          uuid NOT NULL,    -- who created this event
  actor_role        text NOT NULL,    -- 'auto_grader' | 'teacher' | 'moderator' | 'admin'
  reason_code       text,             -- required for teacher_override
  reason_note       text,             -- freeform, audit-viewable
  previous_event_id bigint REFERENCES grade_events(id),
  created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON grade_events (student_id, assessment_id, created_at DESC);
```

Rules:

1. **UPDATE forbidden.** Even clerical typo fixes are new events.
2. **Current grade = latest event per (student_id, assessment_id)** via view.
3. **`actor_id` is never NULL.** Automated regrades use a system
   actor with a known UUID.
4. **`reason_code` required** for `teacher_override` and
   `regrade_request`. No blank overrides.

## Question randomization

### What to randomize

- Question order (per-delivery, server-generated seed)
- Answer-option order (per-question, per-delivery)
- Numeric-parameter instances (e.g. "If x = {{a}} and y = {{b}}...")
  where `a, b` are drawn from a per-delivery seed

### What NOT to do

- Seed from `user_id`. Two students comparing "my Q3" can match.
- Seed from `timestamp` rounded to the minute. Concurrent students
  get the same order.
- Seed in the client. It's observable.

### Correct pattern

```python
def delivery_seed(attempt_id: uuid) -> bytes:
    # Stored server-side on attempt creation
    return secrets.token_bytes(32)

def ordered_questions(assessment, attempt):
    seed = attempt.delivery_seed
    rng = random.Random(seed)
    items = list(assessment.question_items)
    rng.shuffle(items)
    return items
```

The seed is bound to the attempt (not the user). Within the same
attempt, re-renders are deterministic. Across attempts, it changes.

## Time-attack detection

Capture during the attempt, not after:

- **Per-question reaction time** (first-paint → first-keystroke)
- **Paste events** (keyboard vs. clipboard vs. programmatic)
- **Focus-change events** (tab-switch, window-blur, screen-share-start)
- **Answer-change history** within a question (revisits, flip-flops)
- **Keystroke timing histogram** (not keystrokes themselves — privacy)
- **Network reconnect events** (suspicious disconnect windows)

Store aggregates + a sample of raw events in the attempt-log. Raw
events retained per retention policy, not indefinitely.

**Do NOT reconstruct these post-hoc.** If the client didn't capture
it, it's gone. Ship the capture code BEFORE the assessment feature
goes live.

## Proctoring governance (privacy ↔ integrity trade-off)

Proctoring is a privacy cost incurred to gain integrity confidence.
Minimize the cost:

| Proctoring mode | Privacy cost | When it earns its keep |
|---|---|---|
| No proctoring | Zero | Low-stakes formative assessment |
| Lockdown browser only | Low | Medium-stakes; open-notes discouraged |
| Webcam + screen-share recording | High | High-stakes credentialing |
| Live remote proctor + recording | Very high | Credentialing where the recording IS the evidence |

Regardless of mode:

- **Retention ≤ regulatory minimum** (EDTECH-011). 30-90 days typical;
  longer only when under active dispute with documented hold.
- **Encryption at rest.** AES-256 standard; column-level key per
  customer/district where possible.
- **Access log on every read.** Who viewed this student's recording,
  when, for what reason.
- **Assistive-tech allowlist** (EDTECH-013). Before flagging
  "suspicious behavior," check the student's accommodation profile.

## Question-bank access control

Question banks are the crown jewels. One leak invalidates a cycle.

### Invariants

- **Plaintext question bank NEVER leaves production.** Dev/staging
  uses a seed bank with synthetic questions (EDTECH-012).
- **Read access** is per-role: question-authors see authored items;
  assessment-deliverers see items at delivery time only (server-side
  render); analytics see item-IDs + performance stats, never item text.
- **Export** (for reviewers) is watermarked + access-logged + expires.
- **Bulk download** requires two-person approval.

## Double-grading invariant

For high-stakes human-graded items:

```
|rubric_score - moderator_score| ≤ tolerance  OR  moderation_committee_review_required
```

Reconciliation:

1. Rubric grader scores within rubric.
2. Moderator grades independently (blind to rubric score).
3. If delta > tolerance (typically 10% of max), item goes to
   moderation committee (third grader). Final score is committee's.
4. **All three scores retained.** Never discard the dissenting scores
   — they're the audit trail if a student challenges.

## Integrity checklist for every assessment feature

- [ ] **Grade table append-only?** (EDTECH-008)
- [ ] **Randomization seed per-delivery, server-generated?** (EDTECH-009)
- [ ] **Time-attack telemetry captured live?** (EDTECH-010)
- [ ] **Proctoring retention ≤ regulatory minimum, encrypted?** (EDTECH-011)
- [ ] **Question bank plaintext absent from non-prod?** (EDTECH-012)
- [ ] **Assistive-tech allowlist checked before flagging?** (EDTECH-013)
- [ ] **Reason code required for teacher overrides?**
- [ ] **Double-grade delta reconciliation path?**
- [ ] **Access log on proctoring artifact reads?**
- [ ] **Bulk question-bank operations require two-person approval?**

## References

- `.claude/skills/domains/edtech/skills/student-data-privacy/SKILL.md`
- `.claude/skills/domains/edtech/skills/learning-analytics/SKILL.md`
- `.claude/skills/core/security-and-auth/SKILL.md`
- `.claude/skills/core/state-machines-and-invariants/SKILL.md`
- NIST SP 800-53 AU-family (audit logging)
- IMS Global Caliper Analytics (event model for edtech telemetry)
