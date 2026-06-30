---
plan_id: PLAN-EXAMPLE-I18N
title: "Launch Brazilian Portuguese locale with financial-sector regulatory copy"
status: draft
owner: ceo
level: L3
squad: i18n-business
profile: core,i18n-business
created_at: 2026-05-10
---

# Example PLAN — Brazilian Portuguese Locale Launch (Regulated Market)

> **This is an illustrative example**, not a real plan. It shows
> how the i18n-business squad coordinates on a locale launch that
> touches all three VETO scopes: locale key management (Amara),
> regulated-market financial copy (Dr. Tanaka), and ICU pipeline
> integrity (Nadia).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/government/examples/`

## 1. Problem

The product is expanding into Brazil, requiring a `pt-BR` locale with
full ICU format parity across web and mobile, and with BACEN-compliant
financial disclaimer copy on all investment-adjacent screens. The existing
`pt` (European Portuguese) locale cannot be reused without cultural and
regulatory adaptation.

Sources:
- Product: 3 screen surfaces with financial disclaimers (investment summary,
  fee disclosure, risk warning)
- Regulatory: BACEN Resolution 4.878/2020 — mandatory risk-warning language
  for retail financial products
- Platform scope: web (React/i18next), iOS (NSLocalizedString), Android
  (string resources)

## 2. Scope

**In:**
- `pt-BR` locale launch across web, iOS, Android
- ICU plural rule wiring for Brazilian Portuguese (same as `pt`, but cultural
  number/date formatting differs)
- BACEN-compliant disclaimer copy for 3 screen surfaces
- Fallback chain: `pt-BR` → `pt` → `en` (with explicit config, not implicit)
- Cultural review: date format (DD/MM/YYYY), currency (R$ BRL), thousand
  separator (`.`), decimal separator (`,`)

**Out:**
- `pt-PT` (European Portuguese) — existing locale, separate lifecycle
- Marketing copy adaptation (handled by marketing-global squad in parallel)
- Backend-only string changes (no regulated copy on server-side strings)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Key coverage audit | Amara Osei-Bonsu | Full key inventory for pt-BR; fallback chain config; identify gaps vs pt (I18N-003) |
| P2 — ICU pipeline wiring | Nadia Reyes | CLDR pt-BR plural rules; date/number ICU patterns (I18N-008); platform parity check |
| P3 — Regulatory copy | Dr. Yuki Tanaka | BACEN disclaimer review; cultural format review; formality register (I18N-009) |
| P4 — TMS onboarding | Sofia Petrov | Vendor assignment; glossary version; string freeze date communicated (I18N-004) |
| P5 — QA | Pascal Diallo | Pseudo-locale build (I18N-012); native-speaker review; RTL not applicable but layout test for long strings |
| P6 — Launch review | CEO + all VETO holders | Amara + Nadia + Dr. Tanaka sign-off |

## 4. Risk axes and VETO holders

- **Amara Osei-Bonsu (Localization Lead):** Silent key fallback to `en` or
  `pt` on any missing `pt-BR` key → BLOCK if coverage diff shows gaps not
  explicitly declared as intentional fallback (I18N-003).
- **Dr. Yuki Tanaka (Cultural Consultant):** BACEN-non-compliant disclaimer
  copy → BLOCK if regulatory review has not confirmed compliance; cultural
  date/number format mismatch → BLOCK if hard-coded format strings detected
  (I18N-008, I18N-009).
- **Nadia Reyes (i18n Engineer):** ICU plural or argument format violation →
  BLOCK if any ternary plural or positional argument detected in pt-BR strings
  (I18N-005, I18N-006).

## 5. Task chains invoked

- `i18n-business-launch-new-locale` — primary chain for full locale onboarding
- `i18n-business-regulated-market-copy-update` — invoked for each of the 3
  BACEN-regulated screen surfaces (investment summary, fee disclosure,
  risk warning)
- `i18n-business-locale-key-refactor` — skipped (no existing keys being
  renamed in this launch)

## 6. Acceptance

- `pt-BR` locale listed in supported-locales manifest with explicit fallback
  chain declared (I18N-003)
- All ICU message arguments named, not positional (I18N-006)
- Date format `DD/MM/YYYY`, currency `R$ N.NNN,NN` rendered via ICU patterns,
  not hard-coded strings (I18N-008)
- BACEN disclaimer copy reviewed and approved by Dr. Tanaka; legal sign-off
  documented (I18N-009)
- Pseudo-locale build passes CI with zero untranslated fallback strings (I18N-012)
- Native-speaker QA sign-off by Pascal for all 3 disclaimer screens
- No string concatenation building user-facing sentences (I18N-007)

## 7. Metrics

- Locale coverage: 100% of keys translated before launch (zero fallback leakage)
- TMS delivery SLA: all strings reviewed within 5 business days of freeze
- **Disclaimer accuracy rate** (monitored post-launch via user feedback
  and periodic regulatory spot-check)

## 8. References

- `.claude/skills/domains/i18n-business/skills/cultural-intelligence/SKILL.md`
- `.claude/skills/domains/i18n-business/skills/language-translator/SKILL.md`
- `.claude/skills/domains/i18n-business/task-chains.yaml` — `i18n-business-launch-new-locale`
- `.claude/skills/domains/i18n-business/task-chains.yaml` — `i18n-business-regulated-market-copy-update`
- BACEN Resolution 4.878/2020 — retail financial risk-warning requirements
