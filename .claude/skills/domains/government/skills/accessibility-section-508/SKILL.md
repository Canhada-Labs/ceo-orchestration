---
name: accessibility-section-508
description: Section 508 + WCAG 2.1 AA compliance for public-sector software. Covers VPAT authoring, screen-reader verification (NVDA/JAWS/VoiceOver), keyboard-only flows, color contrast, captions, ARIA labeling, focus indicators, and reduced-motion respect. In government procurement contexts a failing Section 508 check is a legal block — not an aspirational polish pass. Use when designing any citizen-facing or employee-facing UI, any procurement-responsive RFP response, or any VPAT refresh. Cross-references core `accessibility-and-wcag` but is Section-508-specific and carries VETO weight because of procurement consequences.
owner: Linh Abernathy (Government A11y Engineer, domain persona)
secondary_owner: Darius Okonkwo (Public Records Engineer, domain persona)
tier: domain:government
scope_tags: [accessibility, section-508, wcag, vpat, procurement-block, public-sector]
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
  - "**/ui/**"
  - "**/components/**"
  - "**/accessibility/**"
  - "**/vpat/**"
---

# Accessibility — Section 508 (+ WCAG 2.1 AA)

## Cardinal Rule

**In government, Section 508 non-compliance is a procurement block,
not a polish item.** A federal agency cannot buy or renew a contract
for software that fails VPAT. State and local increasingly mirror the
federal rule. Treat 508 as you would a security gate: shippable only
when green.

## What "Section 508" actually means in 2026

- **Revised Section 508 standards (2017 refresh)** incorporate WCAG
  2.0 Level A + AA by reference. Most agencies have practically moved
  to WCAG 2.1 AA expectations in RFP language. A conservative baseline
  is WCAG 2.1 AA, with an eye toward WCAG 2.2 for new builds.
- **VPAT (Voluntary Product Accessibility Template)** is the vendor's
  self-reported conformance document. VPAT 2.4 Rev 508 is the current
  US-procurement format. VPATs older than ~12 months are considered
  stale by most agency procurement offices.
- **"Functional performance criteria"** (Chapter 3) require that
  users with a given disability can perform the task WITHOUT a
  particular ability (e.g. without vision, without hearing, without
  color perception, without fine motor control, without speech).

## Procurement impact (why this carries VETO)

| Scenario | Consequence |
|---|---|
| RFP requires Section 508 conformance, VPAT says "does not support" | Bid disqualified (federal); heavy negotiation or exclusion (state/local) |
| Post-award discovery that deployed product fails 508 | Contract cure period; in severe cases, rescission and reprocurement |
| Public-facing portal fails 508 | Potential DOJ settlement (ADA Title II for state/local); reputational cost + mandated remediation schedule |

Ship-blocking, not ship-annoying.

## Pre-merge Section 508 checklist (domain VETO trigger)

All items MUST pass before the A11y Engineer signs off:

- [ ] **Keyboard-only**: every interactive element reachable + operable
      via keyboard. Tab order matches visual order. No keyboard traps.
      Skip-to-main link at top.
- [ ] **Focus indicator**: visible focus ring on every focusable
      element, 3:1 contrast minimum against adjacent colors; NEVER
      removed via `outline: 0` without a replacement.
- [ ] **Screen reader pass**: manual smoke on NVDA + JAWS (Windows)
      OR VoiceOver (macOS/iOS). Page landmarks announced; form
      labels read; error messages announced via `aria-live` or
      role="alert"; dynamic content updates announced.
- [ ] **Color contrast**: 4.5:1 for normal text, 3:1 for large text
      (≥18pt or ≥14pt bold), 3:1 for UI components + graphical objects
      (WCAG 1.4.11). Run automated check AND manual verify.
- [ ] **Color independence**: no information conveyed by color alone.
      Required fields have an asterisk or "(required)" label, not just
      red. Error states have an icon + text, not just red border.
- [ ] **Captions + transcripts**: every video has accurate captions
      (not auto-generated-only); prerecorded audio has a transcript;
      live broadcasts have live captions. No muted autoplay with
      critical info.
- [ ] **Form labels + ARIA**: every input has a programmatic label
      (`<label for>`, `aria-label`, or `aria-labelledby`). Error
      messages linked via `aria-describedby`. Required fields have
      `aria-required="true"`.
- [ ] **Accessible name matches visible text**: WCAG 2.5.3 — the
      accessible name (what screen readers announce) starts with or
      contains the visible text. `aria-label="Submit"` on a button
      visibly labeled "Send" is a failure.
- [ ] **Motion + animation**: honors `prefers-reduced-motion`. No
      auto-playing motion >5s. No flashing content >3 Hz (seizure
      risk, WCAG 2.3.1).
- [ ] **Zoom + reflow**: page works at 200% zoom without horizontal
      scroll on 1280px viewport (WCAG 1.4.10 Reflow).
- [ ] **Timing**: any session timeout under 20 hours has a warning
      modal with "extend" option (WCAG 2.2.1). Adjustable or
      extendable unless the timing is essential (exam, auction).
- [ ] **Language declared**: `<html lang>` set; language changes
      within content marked with `lang` attribute.

## Common 508 failures found in government software

1. **Custom controls without ARIA role** — a `<div>` that acts like a
   button is a checkbox to nobody. Either use `<button>` or give the
   div role="button", `tabindex="0"`, and keyboard handlers for
   Enter + Space.
2. **"Skip to main content" link styled `display:none`** — removes
   it from the keyboard flow. Use a visually-hidden class that
   reveals on focus.
3. **Modal traps focus but never returns it** — when modal closes,
   focus should return to the triggering element.
4. **Icon buttons with no accessible name** — `<button><svg/></button>`
   announces as "button" with no label. Add `aria-label`.
5. **PDF forms without tags** — a scanned PDF is inaccessible by
   default. Use tagged PDFs or HTML forms. Agency should reject
   untagged PDFs from vendors.
6. **Session timeout with no warning** — exam / benefits / license
   renewal workflows kick users with cognitive disabilities who need
   more time. Warning + extend option is mandatory.
7. **Color-only required-field indicator** — red asterisk with no
   "required" text fails color-independence.
8. **Video without captions** — procurement-blocker. Auto-generated
   captions are a starting draft, not compliance.

## VPAT authoring discipline

- One VPAT per product per year minimum (stale = >12 months).
- VPAT conformance levels: "Supports", "Partially Supports", "Does
  Not Support", "Not Applicable". NEVER mark "Supports" on a
  criterion without verified manual testing. "Partially Supports"
  requires a remediation plan with target date.
- VPAT authored by engineering + accessibility SME together; legal
  review before delivery to agency.
- Remediation backlog for any "Partially Supports" tracked in
  project management with agency-visible due dates.

## Reduced-motion respect

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

This applies to page-load animations, hero banners, auto-scrolling
carousels, parallax effects, and any decorative motion. Functional
motion (video playback on user request) stays as-is.

## Testing stack (minimum viable)

- **Automated**: axe-core or Pa11y in CI. Catches ~30-40% of issues.
- **Manual screen reader**: NVDA (free, Windows) + VoiceOver (macOS)
  on a monthly rotation per shipping squad. JAWS if an agency
  requires it contractually.
- **Manual keyboard-only**: engineer unplugs mouse for the session,
  completes each primary user path end-to-end.
- **Contrast checker**: browser devtools or Stark plugin.
- **Real user testing**: at least annually, paid session with
  disabled users across vision, motor, cognitive, hearing dimensions.

## References

- Revised Section 508 standards (36 CFR Part 1194)
- WCAG 2.1 AA (W3C Recommendation)
- VPAT 2.4 Rev 508 template (ITI)
- DOJ ADA Title II final rule on web/mobile accessibility (2024)
- `.claude/skills/frontend/accessibility-and-wcag/SKILL.md` (core
  accessibility reference — this skill is the government-specific
  overlay with VETO authority)
- `.claude/skills/domains/government/skills/public-procurement/SKILL.md`
  (procurement context — VPAT is a bid artifact)
