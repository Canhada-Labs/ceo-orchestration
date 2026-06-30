---
name: receiving-review
description: Use when receiving code-review feedback or a critique — from the
  Owner, the Codex pair-rail, a debate archetype, or any reviewer — and deciding
  whether to implement, clarify, or push back. Use when tempted to agree with a
  suggestion before verifying it, when a reviewer claims a bug, when feedback asks
  to "implement properly" or add a feature, or when a suggestion would weaken a
  security control.
owner: CEO (cross-cutting discipline — applies to every archetype and the CEO)
# Pattern inspired by obra/superpowers `receiving-code-review` (MIT, release
# v5.1.0, HEAD f2cbfbe). Full attribution + decision record: ADR-140. The
# structured `inspired_by:` field is omitted intentionally — its validator
# requires a 40-hex commit SHA, and only the short SHA is on record.
# --- smart-loading fields (PLAN-083 Wave 0a) ---
domain: core
priority: 2
risk_class: low
stack: []
context_budget_tokens: 1200
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 2}
  engine: {active: true, priority: 2}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 2}
  generic: {active: true, priority: 2}
activation_triggers:
  - {event: review-received}
  - {event: help-me-invoked, regex: "(?i)receiv|feedback|push.?back|critique|review.?comment"}
---

# Receiving Review

## Role

This is the **receiving** half of the review discipline. The giving half —
how to author a review — lives in `code-review-checklist` and ADR-058. This
skill governs how the CEO or any agent **responds** to a review, a critique,
or feedback, whether it comes from the Owner, the Codex pair-rail, a debate
archetype, or an external reviewer.

The failure mode it prevents is **sycophancy**: agreeing because agreement is
socially smooth, not because the feedback is correct for this codebase.
Performative agreement followed by a wrong change is worse than reasoned
pushback. Technical rigor over social comfort.

## The discipline (in order)

1. **Read the whole thing without reacting.** Do not start replying — or
   editing — mid-feedback. Read every item first.
2. **Restate the technical requirement in your own words** (or ask, if it is
   genuinely ambiguous). If you cannot restate what the reviewer is asking
   for, you cannot evaluate it.
3. **Verify against codebase reality.** A claim is not true because a reviewer
   stated it. Grep / read / run the code. A reviewer who says "this has a SQL
   injection" about a parameterized query is **wrong**, and the correct
   response is to verify and say so — not to "fix" safe code.
4. **Evaluate: is it sound for THIS codebase?** A suggestion can be correct in
   general and wrong here (conflicts with an ADR, a documented constraint, the
   stdlib-only rule, an invariant). General correctness is not local
   correctness.
5. **Respond with a technical acknowledgment or a reasoned pushback.** Both are
   first-class outcomes. "You're right, verified at `file:line`, fixing" and
   "Verified — the query is parameterized, no change needed, here's why" are
   both good. Neither requires praise.
6. **Implement per item.** Each clear item proceeds on its own. Only a
   *genuinely* ambiguous item is held for clarification — and holding one
   unclear NIT must **never** block N clear CRITICALs. Do not deadlock the
   whole batch behind a single unclear point (CR-MF4).

## Forbidden: performative agreement

Do not open a response with praise or gratitude as a reflex:

- ❌ "You're absolutely right!"
- ❌ "Great point!"
- ❌ "Thank you for catching that!"
- ❌ "Excellent feedback!"

These signal nothing technical and prime auto-acceptance. State the technical
finding directly. If the reviewer is right, say *what* is right and *where you
verified it*. Acknowledgment is a verified fact (`confirmed at file:line`),
not a compliment.

## YAGNI check on "do it properly" suggestions

When feedback says "implement this properly", "add a config knob", "make it
extensible", or "handle the general case", apply YAGNI: build what THIS change
needs, not a speculative generalization. A reviewer asking for an unused
endpoint, a flag with one caller, or a framework for a one-off is a suggestion
to **push back on**, not silently expand scope to satisfy. Cite the concrete
need or decline.

## Security carve-out (never auto-accepted)

> **Any feedback that would weaken a security control re-enters the VETO gate —
> regardless of who suggested it** (Owner, Codex, or any archetype).

"Reasoned pushback" cuts both ways: it lets you decline a wrong critique, but
it **never** lets you accept a security regression because a high-authority
reviewer asked for it. If a suggestion would remove an auth check, relax input
validation, downgrade a crypto choice, broaden a scope grant, weaken redaction,
or disable a governance hook, route it through the `security-and-auth` /
`identity-and-trust-architecture` VETO holders before implementing — even if
the Owner proposed it. Surface the trade-off; do not quietly comply.

## Applies to the Codex pair-rail too

When the Codex pair-rail returns BLOCK / ACCEPT-WITH-FIXES, apply the same
discipline: verify each finding against the code before implementing. Codex is
strong at catching false factual premises (see
[[feedback-codex-validates-reality-debate-validates-design]]), but a Codex
finding is still a claim to verify, not an order to obey. Fix what is real;
push back (in the reply thread) on what is not, with evidence.

## Anti-patterns

- Editing files while still reading the feedback.
- Replying "You're absolutely right" and then making a change you never verified.
- Holding all feedback hostage to one ambiguous item.
- Expanding scope to satisfy a "make it extensible" comment with no real caller.
- Accepting a security-weakening change because the Owner or Codex proposed it.

## Relationship to other governance

- **Giving side:** `code-review-checklist` + the `code-reviewer` archetype +
  `/debate` (ADR-058 BORROW-2).
- **This (receiving) side:** ADR-140, and the PROTOCOL.md §Receiving review clause.
- **Verification doctrine:** the same-LLM mitigations in PROTOCOL.md §Honest
  limitation (verify against code, fluency is a red flag) are the *why* behind
  step 3.
