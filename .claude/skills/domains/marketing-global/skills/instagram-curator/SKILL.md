---
name: instagram-curator
description: >
  Instagram strategy discipline covering Reels-led growth, Carousel
  save-engine mechanics, Stories community loops, and Feed permanence
  architecture. Enforces aesthetic coherence (palette, typography,
  composition) as brand identity over trend-chasing, treats saves and
  shares as primary algorithm signals above likes, and applies
  nano/micro/mid-tier creator partnership selection based on audience
  alignment rather than follower reach. Use when: auditing or
  designing a multi-format content mix, calibrating posting cadence,
  evaluating creator partnership fit, building a hashtag strategy, or
  diagnosing aesthetic drift and engagement decline on an Instagram
  presence.
owner: Isabela Ferreira (Instagram Curator, domain persona)
tier: domain:marketing-global
scope_tags: [instagram, reels, carousel, stories, save-economy, aesthetic-coherence, creator-partnerships]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-instagram-curator.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: marketing-global
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
  - "**/instagram/**"
  - "**/reels/**"
  - "**/stories/**"
---

# Instagram Curator

## Cardinal Rule

Aesthetic coherence is a compound asset — each post either builds or
erodes the visual identity the account has accumulated. A single
off-brand post does not reset the identity, but a drift pattern across
two to three weeks signals that the curatorial frame has loosened.
Before publishing any piece of content, confirm it passes three tests:
palette alignment, typographic consistency, and compositional
conventions match the established grid. Trend-responsive content is
acceptable; trend-driven identity abandonment is not. The brand
identity is the durable asset; the trend is the distribution vehicle.

---

## Fail-Fast Rule

Content MUST NOT be published if any of the following conditions hold:

1. The post deviates from the established color palette without a
   documented grid refresh decision.
2. A Reel uses audio that conflicts with the brand tone (e.g.,
   aggressive or ironic audio applied to a premium or care-focused brand).
3. A creator partnership post lacks a disclosure label compliant with
   FTC guidelines (US) or ANPD-LGPD obligations (Brazil) — disclosure
   is a legal requirement, not a stylistic choice.
4. A carousel's first slide does not contain a hook strong enough to
   produce a swipe-forward action; a carousel that is not swiped does
   not save.
5. A hashtag set exceeds 10 tags or contains obvious spam clusters
   (100M+ posts with no niche targeting logic).

Halt publication and resolve before scheduling. Queue-stuffing into a
non-compliant calendar accelerates reach suppression.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Designing or auditing a multi-format content mix (Reels / Carousel /
  Stories / Feed) for a brand or creator account.
- Calibrating or diagnosing posting cadence against platform algorithm
  requirements.
- Evaluating the aesthetic coherence of an existing grid or proposing
  a grid refresh.
- Selecting creator partnership tiers (nano, micro, mid) and evaluating
  audience alignment fit.
- Building or auditing a hashtag strategy (research, pruning, refresh).
- Diagnosing engagement decline — distinguishing reach suppression,
  save-economy weakness, and content-mix imbalance as causal categories.
- Structuring a Stories sequence for community loop or product awareness.

Skip when: the task is Instagram paid advertising (use
`domains/marketing-global/skills/social-media-strategist` for paid
strategy); the channel is TikTok (use
`domains/marketing-global/skills/tiktok-strategist`); or the task is
a cross-platform content calendar without Instagram-specific format
requirements.

---

## Format Mix Discipline

The four Instagram formats serve distinct algorithmic and audience
functions. Treating them as interchangeable degrades both reach and
community depth.

### Reels — Primary Growth Engine

Reels receive the highest organic distribution weight in the Instagram
algorithm for accounts below 100K followers. Their function is
discovery — reaching audiences who do not yet follow the account.

Content direction:
- Hook visible within the first 1.5 seconds, no cold-start.
- Duration 15–30 seconds for maximum completion rate on informational
  content; 30–60 seconds for tutorial or demonstration formats.
- Audio selection must align with brand tone AND have current trending
  signal; combining both doubles distribution probability.
- Captions written for silent viewing (text overlay) and spoken
  comprehension simultaneously.

Ratio guidance: 4–7 Reels per week for accounts in active growth
phase; 2–3 per week for accounts in maintenance phase. Below 2 per
week, the Reels algorithm deprioritizes the account in the Explore tab.

### Carousel — Save Engine

Carousels are the highest-save format on Instagram. The algorithm
interprets a save as a high-quality engagement signal — stronger than
a like, comparable to a share. Carousels that generate saves compound
reach over time through re-recommendation.

Content direction:
- Slide 1: hook that creates information tension requiring resolution.
- Slides 2–7: value delivery in digestible increments; one idea per
  slide.
- Slide 8–10: CTA that directs to a specific action (save for later,
  share, profile visit).
- Carousels for educational content, how-to sequences, comparison
  frameworks, and list formats outperform single images by 3–5× in
  save rate.

Ratio guidance: 3–5 carousels per week. Carousels below 5 slides
rarely achieve save-bait mechanics; above 10 slides, completion rate
drops and the save signal weakens proportionally.

### Stories — Community Layer

Stories function as the relationship maintenance channel. They address
existing followers rather than new audiences, sustaining community
depth and direct engagement frequency.

Content direction:
- Daily cadence minimum (1–3 frames per day); gaps beyond 48 hours
  reduce the Stories placement prominence for followers.
- Interactive elements (polls, sliders, question boxes, quizzes) in
  at least 30% of Stories frames — interaction extends the algorithmic
  display window for the next Stories sequence.
- Behind-the-scenes, process content, and ephemeral offers are
  native to Stories; do not repurpose Feed or Reels thumbnails without
  adapting format and aspect ratio (9:16, full bleed).
- Highlights as persistent archive: curate by topic, not chronology;
  each Highlight cover must match the grid aesthetic system.

### Feed Posts — Permanence and First Impression

Feed posts form the permanent visual record that new visitors evaluate
when deciding to follow. A grid that lacks coherence or communicates
an unclear niche performs poorly at converting profile visits to
follows regardless of Reels-driven traffic volume.

Content direction:
- Single images for product, portrait, and editorial content where the
  entire message is contained in one frame.
- Grid planning at the 9-post level minimum; no single post should be
  approved without confirming its row and column context.
- Feed posts have lower algorithmic amplification than Reels but retain
  their profile-page presence indefinitely — visual quality floor is
  higher for Feed than for ephemeral formats.

---

## Aesthetic Coherence

Aesthetic coherence is not decoration — it is brand recognition
architecture. A consistent visual identity produces faster recognition
at scroll speed (where content is processed in under 300 ms) and
builds the implicit trust that drives save and follow behavior.

### Palette Governance

- Define a core palette of 3–5 hex values: one primary, one or two
  secondary, one accent, one neutral.
- Every post must contain at minimum the primary or neutral; the accent
  appears sparingly (≤20% of posts) to preserve its visual weight.
- Seasonal or campaign-specific palette extensions require a documented
  override — the core palette resumes post-campaign.

```
Core palette structure:
  primary   — dominant brand color (appears in >70% of posts)
  secondary — supporting color(s) for contrast and pairing
  accent    — high-contrast call-out color, used sparingly
  neutral   — background or text base (white, off-white, dark neutral)
```

### Typography Standards

- One display typeface for headlines and callouts.
- One body typeface for supporting text (distinct weight class from
  display).
- Font pairings must remain constant across all formatted content
  types; ad-hoc typeface substitutions fracture visual identity.
- Text weight and size must remain legible at mobile thumbnail scale
  (roughly 80×80 px preview).

### Composition Conventions

- Subject placement consistent across content type (e.g., centered for
  product, rule-of-thirds for lifestyle, full-bleed for editorial).
- Negative space used deliberately; crowded compositions compress
  visual hierarchy and reduce recognition speed.
- Aspect ratio discipline: Feed 4:5 or 1:1; Reels 9:16; Carousel
  slides 1:1 or 4:5 (consistent within a carousel, never mixed).

---

## Save-Share Economy

The Instagram algorithm weights engagement signals in the following
approximate priority order for organic reach distribution: saves >
shares > comments > likes > impressions. A content strategy optimized
for likes is misaligned with the distribution mechanics.

### Save-Bait Mechanics

Content earns saves when it is reference-worthy — the viewer expects
to return to the content later. High-save formats:
- Instructional carousels with frameworks or checklists.
- Comparison tables that aid a future decision.
- Resource lists (tools, references, templates) with immediate
  practical value.
- Aesthetic inspiration posts that viewers want to reference for their
  own projects.

### Share-Driven Hook Construction

Content earns shares when it articulates something the viewer wishes
they had said, or that precisely describes their experience or
aspiration. Share triggers:
- Statements that feel identity-affirming for the target audience
  (professional identity, lifestyle, values).
- Contrarian or counter-intuitive framings that the viewer wants their
  network to see.
- Specific, practical knowledge that makes the sharer appear informed
  or helpful.

Shares to Stories (the primary share mechanism) extend reach to the
sharer's audience without algorithm penalty. Shares to DMs indicate
high relevance and contribute to engagement score.

---

## Posting Cadence

Cadence requirements vary by account phase and primary growth objective.
These are minimum floors; volume above these levels is appropriate for
accounts with sufficient content production capacity.

| Format | Growth Phase | Maintenance Phase |
|---|---|---|
| Reels | 4–7 per week | 2–3 per week |
| Carousels | 3–5 per week | 1–2 per week |
| Stories | Daily (1–3 frames) | Daily (1–2 frames) |
| Feed Posts | 3–5 per week | 1–2 per week |

Cadence consistency outperforms cadence volume. An account that posts
5 Reels in week 1 and 0 in week 2 will underperform an account that
posts 3 Reels consistently every week. The algorithm scores consistency
as a reliability signal for recommendation placement.

Timing optimization: post Reels and Carousels during the account's
peak-audience window (identifiable in Instagram Insights under
"Most active times"). Stories can be posted throughout the day as
ephemeral content; timing is less critical for Stories than for Feed
and Reels.

---

## Creator Partnerships

Creator partnerships must be evaluated on audience alignment first,
follower count second. A nano-creator with 3K followers and 8%
engagement in the precise target demographic delivers more conversion
signal than a mid-tier creator with 200K followers and 1.2% engagement
in a tangential audience.

### Tier Reference

| Tier | Follower Range | Typical Engagement Rate | Primary Use Case |
|---|---|---|---|
| Nano | 1K–10K | 5–12% | Hyperlocal, niche community, trial partnerships |
| Micro | 10K–100K | 3–8% | Vertical authority, product category expertise |
| Mid | 100K–500K | 1–4% | Broader awareness within vertical; brand validation |
| Macro / Mega | 500K+ | 0.5–2% | Mass awareness; high cost; rarely cost-efficient for niche brands |

For most brand-building campaigns, a portfolio of 5–10 micro-creators
outperforms a single macro-creator at equivalent budget due to
audience specificity and trust differential.

### Selection Criteria

Before approving a creator partnership, verify:

1. Audience demographics (location, age, gender) match the target
   customer profile — request screenshot of Insights.
2. Content tone and visual style are compatible with brand palette and
   voice standards.
3. Prior brand partnership history does not include direct competitors
   or brands with incompatible values.
4. Engagement quality: scan most recent 10 posts; flag if comment
   section is dominated by generic praise ("amazing!", "love this!")
   without substantive interaction — indicates engagement-pod activity
   or inauthentic growth.
5. Disclosure history: the creator demonstrates consistent use of
   #ad, #publicidade, or equivalent disclosure labels on paid content.

### Disclosure Compliance

All paid or gifted creator content MUST carry disclosure labels
compliant with the applicable jurisdiction:

- **FTC (United States)**: #ad or #sponsored in the caption body,
  above the fold, not buried in hashtag clusters; or Instagram's
  "Paid Partnership" label enabled.
- **ANPD-LGPD (Brazil)**: disclosure requirement mirrors FTC intent;
  CONAR Resolution 46/2023 mandates clear and conspicuous identification
  of commercial content; `#publi` or `#publicidade` accepted.
- Platform-native "Paid Partnership" label does not substitute for
  caption disclosure when targeting Brazilian audiences under CONAR
  standards — use both.

Non-compliant disclosure is a legal exposure for both the brand and
the creator. Contracts MUST specify disclosure requirements and grant
approval rights to verify compliance before publication.

---

## Hashtag Discipline

Hashtags contribute to discovery via keyword indexing, not viral
amplification. The current Instagram algorithm weights account-level
relevance signals and content quality above hashtag volume. Hashtag
abuse (30 tags, irrelevant clusters) triggers reach suppression.

### Construction Rules

- **Volume**: 5–10 hashtags per post. More than 10 shows diminishing
  returns and signals spam behavior to the classifier.
- **Mix**: one brand hashtag (account-owned or campaign-specific),
  two to three niche hashtags (10K–500K posts, high content relevance),
  one to two mid-range hashtags (500K–5M posts, vertical category),
  zero to one broad hashtag (5M+ posts) — broad tags dilute signal.
- **Consistency**: brand hashtag appears on every post; niche hashtags
  are rotated to prevent pattern-lock and test which clusters drive
  profile visits.
- **Never**: avoid hashtag sets copied from other accounts without
  audience-alignment analysis; avoid purchasing hashtag research lists
  without verifying freshness (hashtag velocity changes quarterly).

---

## Anti-Patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Posting identical content across Instagram and TikTok without format adaptation | Aspect ratio, audio, and caption length norms differ; cross-posted content is flagged as low-effort and suppressed |
| Chasing trending audio that conflicts with brand tone | Short-term reach spike at the cost of audience confusion and aesthetic erosion |
| Measuring content performance by likes alone | Likes are the weakest algorithm signal; optimizing for likes produces content that does not grow reach |
| Irregular cadence (burst-then-silence) | Algorithm deprioritizes accounts with inconsistent posting patterns; consistency floor is more important than volume ceiling |
| Using 30 hashtags in every post | Volume-based hashtag strategy is outdated; 5–10 targeted tags outperform blanket sets under current classifiers |
| Publishing creator content without disclosure review | Legal exposure under FTC and ANPD-LGPD; platform penalty risk includes content removal and account demotion |
| Evaluating creator fit by follower count alone | Follower count is a vanity metric; engagement rate and audience alignment are the material signals |
| Designing carousels with a weak Slide 1 hook | A carousel that is not swiped does not save; all save-engine mechanics depend on Slide 1 producing a swipe |
| Treating Stories as a secondary channel | Stories sustain community depth and relationship frequency; deprioritizing Stories accelerates follower churn |
| Approving a Feed post without 9-post grid context | Individual post quality cannot substitute for grid-level coherence; isolated approval breaks the permanence architecture |

---

## Cross-References

- `domains/marketing-global/skills/tiktok-strategist` — short-form
  video strategy for TikTok; shares format discipline overlap with
  Reels but diverges on algorithm mechanics, sound culture, and
  discovery architecture.
- `domains/marketing-global/skills/social-media-strategist` — cross-
  platform content orchestration, channel mix decisions, and paid
  social integration.
- `domains/marketing-global/skills/content-creator` — content
  production craft: copywriting, visual direction, and format-specific
  production standards applicable across Instagram formats.

---

## ADR Anchors

- **ADR-058** — Creative content authoring policy: house-voice rules
  (declarative prose, no emojis in framework artifacts, no 2nd-person
  address), maximum verbatim-match threshold with upstream sources,
  and structural inspiration attribution requirements. All content in
  this SKILL.md is original prose authored under ADR-058 constraints.
