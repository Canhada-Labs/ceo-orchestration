---
plan_id: PLAN-EXAMPLE-PMD
title: "Launch TikTok Ads as net-new performance channel for DTC brand"
status: draft
owner: ceo
level: L3
squad: paid-media
profile: core,paid-media
created_at: 2026-05-10
---

# Example PLAN — Launch TikTok Ads as net-new performance channel for DTC brand

> **This is an illustrative example**, not a real plan. It shows
> how the paid-media squad coordinates on adding TikTok Ads to an existing
> paid-media programme that already runs Meta and Google Ads.
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`
> `.claude/skills/domains/paid-media/task-chains.yaml`

## 1. Problem

A DTC consumer goods brand has been running Meta and Google Ads for 3
years with strong ROAS on non-brand search and middle-funnel Meta. iOS
14.5 eroded Meta audience signals and the brand has not diversified
since. The growth team believes TikTok's younger demographic density
represents an incremental reach opportunity. No TikTok Ads account
exists. Attribution infrastructure is last-click, which already
double-counts between Meta and Google.

Sources:
- Meta Ads Manager: trailing-90-day performance report showing ROAS
  decline from 4.2 to 3.1 post-iOS 14.5
- Google Search Console: brand query volume trending flat (no organic lift)
- Market research: 35% of target audience (18-34 women, Brazil + US)
  identified TikTok as primary product discovery channel in survey

## 2. Scope

**In:**
- TikTok Ads account creation and campaign structure design
- Opening creative inventory (UGC-style, short-form, 4 variants per ad set)
- Pixel integration and consent-mode configuration
- Attribution plan update to include TikTok as tracked channel
- Incrementality test design to measure true TikTok lift vs. Meta

**Out:**
- Meta or Google Ads restructuring (separate effort, not in scope)
- Influencer partnership deals (separate commercial agreement track)
- Attribution model overhaul to data-driven (scoped separately per PMD-001)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — Platform scoring | Valentina Reyes | Audience-platform fit matrix score + structural recommendation |
| P2 — Attribution plan | Tomás Carvalho | Attribution plan with TikTok channel added, double-count risk documented |
| P3 — Consent audit | Rafaela Dias | Pixel implementation reviewed, consent-mode confirmed, ad copy pre-review |
| P4 — Creative production | Camila Nunes | 4 UGC-style variants per ad set, hook diversity brief |
| P5 — Campaign build | Valentina Reyes + Marcus Holt | Account structure, bid strategy, pacing targets configured |
| P6 — Launch review | CEO + all VETO holders | Compliance + RevOps + Creative Strategy sign-off |

## 4. Risk axes and VETO holders

- **Rafaela Dias (Compliance & Legal Reviewer):** TikTok pixel may fire on
  product pages that carry health-adjacent claims — consent-mode must be
  configured before pixel activates → BLOCK if pixel fires before affirmative
  consent on any page with health claims (PMD-012).
- **Tomás Carvalho (Revenue Operations Analyst):** Adding TikTok without a
  deduplication strategy will inflate reported conversions by combining with
  Meta last-click → BLOCK if attribution plan does not address TikTok +
  Meta cross-channel double-count before first dollar spends (PMD-002).
- **Valentina Reyes (Paid Social Strategist):** TikTok's algorithm needs
  minimum creative volume and a conversion event with enough signal → BLOCK
  if fewer than 4 creative variants per ad set at launch or if primary
  conversion event has fewer than 30 weekly events at account level (PMD-010,
  PMD-005 equivalent for TikTok).

## 5. Task chains invoked

- `paid-media-launch-new-channel` — primary chain governing the full
  pre-flight sequence: platform scoring → attribution → consent → creative
  → structure → launch VETO check.
- `paid-media-attribution-model-change` — triggered in parallel because
  adding TikTok requires updating the conversion-window documentation and
  double-count risk register (PMD-001, PMD-002). The attribution model
  itself is not being replaced, but the baseline documentation must be
  extended.
- `paid-media-creative-refresh-cycle` — skipped at launch (no fatigue yet);
  added to the post-launch 30-day plan with a scheduled first-refresh review
  at day 21.

## 6. Acceptance

- Audience-platform fit matrix score documented for TikTok before any spend
- Pixel consent-mode verified: no pre-consent tag fire on health-adjacent or
  sensitive pages (PMD-012)
- Attribution changelog updated: TikTok channel added, double-count risk
  documented, conversion windows specified (PMD-001)
- First-party list upload (if any Custom Audience): SHA-256 hashed before
  upload (PMD-004)
- Creative inventory: minimum 4 UGC-style variants per ad set, hook diversity
  confirmed (PMD-010)
- Smart Bidding / TikTok optimised CPM: not activated until 30 purchase events
  accumulated at account level (PMD-005 principle applied to TikTok)
- Incrementality test plan approved by Tomás Carvalho before first $5k spend

## 7. Metrics

- TikTok reported ROAS (with explicit double-count caveat)
- Incrementality lift test result (true ROAS incremental to existing channels)
- **Hook rate by variant at day 7 and day 21** (monitored post-launch;
  below 2% on any variant triggers PMD-011 review)
- Cost per acquisition vs. Meta benchmark at 30-day mark

## 8. References

- `.claude/skills/domains/paid-media/skills/paid-social-strategist/SKILL.md`
- `.claude/skills/domains/paid-media/skills/tracking-specialist/SKILL.md`
- `.claude/skills/domains/paid-media/task-chains.yaml` — `paid-media-launch-new-channel`
- `.claude/skills/domains/paid-media/pitfalls.yaml` — PMD-001, PMD-002, PMD-004, PMD-005, PMD-010, PMD-012
