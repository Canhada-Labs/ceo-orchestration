---
name: carousel-growth-engine
description: >
  Cross-platform carousel post engineering — slide architecture, visual
  hierarchy, hook-to-payoff arc, and save-share mechanics across Instagram,
  LinkedIn, Twitter (X carousel / document), TikTok photo series, and
  Pinterest. Covers the 10–12 slide ceiling, one-idea-per-slide discipline,
  cover-slide-as-ad design, and the asymmetric value of saves versus likes
  in algorithm distribution. Use when: designing a carousel from scratch;
  auditing a carousel for structural or narrative weaknesses; adapting an
  existing carousel to a new platform's aspect ratio and character limits;
  running A/B tests on cover or payoff variants; or diagnosing low save
  rates on formats expected to produce reference-worthy content.
owner: Rafael Sousa (Carousel Strategist, domain persona)
tier: domain:marketing-global
scope_tags: [carousel-design, slide-architecture, visual-hierarchy, save-economy, multi-platform-carousel, document-format]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-carousel-growth-engine.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/carousels/**"
  - "**/slides/**"
---

# Carousel Growth Engine

## Cardinal Rule

A carousel that does not earn the swipe at slide 1 reaches 0% completion
regardless of payoff quality. The cover slide is not an introduction — it is
an advertisement for the rest of the deck. Its function is to create an
information gap specific enough that closing it requires swiping. A cover that
restates the topic without creating tension, or that frames the payoff as
optional ("you might find this useful"), will not produce swipe events at
scale. The entire save-share economy that follows slide 1 is contingent on
that first swipe. Design the cover before designing the deck.

---

## Fail-Fast Rule

A carousel MUST NOT be published if any of the following conditions hold:

1. The cover slide does not contain a hook that identifies a specific problem,
   claim, or information gap — generic topic labels ("5 things about X") are
   insufficient; the tension must be implicit or explicit.
2. Any individual slide contains more than one distinct idea; a slide that
   serves two purposes serves neither.
3. The total slide count exceeds 12; completion rate degrades non-linearly
   above 10 slides, and the payoff slide is deprioritized when preceded by
   cognitive overload.
4. The payoff slide (final slide or penultimate slide before CTA) delivers no
   concrete action, insight, or resolution — a summary of what was just shown
   is not a payoff.
5. The deck has not been validated against the target platform's aspect ratio
   before export; mismatched dimensions produce cropped text and broken visual
   hierarchy at render time.

Halt production and resolve before scheduling.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Designing a carousel post for Instagram, LinkedIn, Twitter (X), TikTok
  photo series, or Pinterest — from brief to final slide export.
- Auditing an existing carousel for narrative arc integrity, visual hierarchy
  failures, or platform-native format compliance.
- Adapting a carousel built for one platform to the dimension and copy
  constraints of another.
- Diagnosing low save rates or low completion rates on carousel formats that
  are expected to function as reference-worthy content.
- Running cover-slide or payoff-slide A/B variants to identify which hook
  framing or CTA structure performs best for a given audience.
- Establishing a reusable carousel template system with locked grid, type
  hierarchy, and color system for a brand or creator.

Skip when: the task is a single static image (no slide sequence involved);
the task is a Reels or short-form video (use
`domains/marketing-global/skills/tiktok-strategist` or
`domains/marketing-global/skills/instagram-curator`); or the task requires
paid carousel ad creative (paid format mechanics differ from organic carousel
distribution).

---

## Slide Architecture

### Ceiling and Density

The 10–12 slide ceiling is a completion-rate constraint, not a creativity
constraint. Platform analytics consistently show completion drop-off beginning
at slide 8 for casual discovery contexts and at slide 11–12 for high-intent
educational content. The ceiling is 12 as an absolute maximum; 7–10 slides
is the functional target range for most carousel types.

One idea per slide is non-negotiable. A slide that contains two parallel
points, two data references, or two sub-claims forces a reading hierarchy that
mobile viewers at scroll speed will not resolve. Split the slide. If splitting
produces too many slides, the architecture problem is upstream — the ideas
themselves require restructuring, not the slide layout.

### Cover Slide as Advertisement

The cover slide performs the function of a paid ad creative: it must stop the
scroll, communicate the value proposition, and create a desire for the
next frame — all within the first 300 ms of processing. Design constraints
that follow from this function:

- The hook text must be visible without zooming; headline type at a minimum
  equivalent to 32px at 1080×1080.
- The visual element (image, illustration, or typographic treatment) must
  support the hook, not compete with it; decorative background that reduces
  text contrast degrades performance.
- The cover slide must work as a standalone unit when displayed in a feed
  thumbnail or link preview — assume the viewer will only ever see slide 1.

### TOC Slides as Roadmap

For carousels above 7 slides targeting educational or reference content, a
slide 2 table of contents anchors the reader's expectation and reduces early
abandonment. The TOC slide should enumerate the payoffs the viewer will
receive, not the topics that will be covered — framed as outcomes, not
subjects.

### Payoff Slide as CTA

The payoff slide (typically the final content slide, followed optionally by
a CTA-only slide) must deliver the most concentrated value in the deck. It
should be designed as the slide most likely to be saved — a framework,
checklist, decision tree, or key takeaway that earns return reference. The
CTA that follows should direct to a single action, not a menu of options;
multiple CTAs on a closing slide split intent and reduce conversion.

---

## Hook-Development-Payoff Arc

### Cover Hook: Thesis and Curiosity

The cover hook operates on one of three mechanics: tension (a claim the viewer
wants to verify), pain point (a problem the viewer recognizes), or curiosity
gap (a pattern revealed partially, requiring the deck to complete it). Each
mechanic works; mixing more than one mechanic on a single cover weakens both.

A thesis hook states a position the viewer either agrees with strongly enough
to validate via swipe, or disagrees with strongly enough to contest via swipe.
Neutral statements do not produce either response. A curiosity-gap hook names
the gap explicitly and withholds the resolution. A pain-point hook names the
problem with enough specificity that the target audience recognizes it as
their own — generic pain points ("feeling overwhelmed") produce lower swipe
rates than specific ones ("spending 3 hours on content that gets 12 likes").

### Development Slides: Stepping Stones

Development slides (slides 2 through N−1) function as stepping stones from
the hook to the payoff. Each slide advances the argument by one unit — a data
point, a principle, an example, a counter-argument addressed — without
restating what the previous slide established. The development section fails
when slides begin repeating information in paraphrased form to fill the slide
count. If the argument has 5 steps, the deck has 5 development slides plus
cover and payoff. Do not inflate.

Formatting discipline within development slides: use one visual anchor per
slide (a single statistic, a labeled diagram, a short list of three items or
fewer). Text-heavy slides that require reading rather than scanning produce
completion drop-off regardless of content quality.

### Payoff: Action or Insight

The payoff slide provides either a concrete action (do this next, use this
framework, apply this decision rule) or a novel insight (the reason behind
the pattern, the principle that unifies the development slides, the
implication the viewer had not considered). A payoff that summarizes the
development is not a payoff — it is a recap, and it does not earn a save.

---

## Visual Hierarchy

### Typography Hierarchy

Every slide must establish a clear reading order through type size, weight,
and positioning. The primary message (headline or key statement) should be
processable in isolation — a viewer who reads only the headline of each slide
should be able to follow the arc of the argument. Supporting text provides
evidence or elaboration but is secondary in visual weight.

Hierarchy levels for carousel slides:
- Level 1: headline or key claim — largest size, highest contrast, positioned
  at optical center or top third.
- Level 2: supporting statement or data label — 60–70% of Level 1 size;
  subdued weight or reduced opacity.
- Level 3: attribution, footnote, or secondary context — minimal size, lowest
  contrast, positioned at bottom margin.

Never use more than two typefaces within a carousel. Typeface consistency
across all slides is a brand-recognition signal at thumbnail scale.

### Contrast and Legibility

Contrast ratio between text and background must meet a minimum of 4.5:1
(WCAG AA) for body text and 3:1 for large display text. This is a baseline,
not a creative floor — many carousel platforms render under variable ambient
light conditions; a contrast ratio of 7:1+ is the functional target for mobile
contexts. Test all text overlays on image backgrounds; image carousels with
photography backgrounds require a scrim or text panel to ensure legibility.

### Negative Space

Negative space is structural, not stylistic. A slide with zero negative space
compresses the visual hierarchy and eliminates the resting points the eye uses
to process content at scroll speed. Maintain a minimum margin of 8–10% of
slide width on all sides. Key information should not bleed to within 5% of
any slide edge — platform overlays, swipe indicators, and profile elements
encroach on the edges at render time.

### Consistent Grid

A grid system applied consistently across all slides in a carousel signals
production craft and reinforces brand identity. Define column structure, row
baselines, and margin constants before designing individual slides. All text
anchors, image crops, and iconographic elements should align to the grid.
Inconsistent element placement between slides creates visual noise at swipe
speed and undermines the coherence the carousel architecture requires.

---

## Platform-Native Variants

Each platform applies different aspect ratios, character limits, and rendering
behaviors. A carousel designed for one platform and republished without
adaptation will render with cropped text, collapsed captions, or broken visual
hierarchy on others.

| Platform | Aspect Ratio | Optimal Resolution | Caption Limit | Notes |
|---|---|---|---|---|
| Instagram | 1:1 or 4:5 | 1080×1080 or 1080×1350 | 2,200 chars | 4:5 crops more feed real estate; first slide most critical for save |
| LinkedIn | 4:5 or 1:1.294 | 1080×1350 or 1080×1400 | 3,000 chars | Document (PDF) format supported; LinkedIn carousels indexed as documents |
| Twitter (X) | 16:9 or 3:4 | 1200×675 or 900×1200 | 280 chars per tweet | Tweet thread with attached images; each tweet is its own unit |
| TikTok Photo | 9:16 | 1080×1920 | 2,200 chars | Photo series format; vertical full-bleed; no text in bottom 20% |
| Pinterest | 2:3 | 1000×1500 | 500 chars | Idea Pins support up to 20 pages; each page = one slide equivalent |

Platform-specific design constraints beyond dimensions:

- **Instagram**: save behavior is the primary signal; design for reference
  reusability, not one-time consumption.
- **LinkedIn**: document carousel format (PDF upload) enables download as
  a signal — high-value reference content earns document saves distinct from
  regular engagement.
- **Twitter (X)**: each slide must read as a standalone tweet image; the
  thread arc supplements but cannot substitute for per-slide independence.
- **TikTok**: no text within the bottom 20% of slide height — TikTok UI
  overlays (like/comment buttons, caption) obscure this zone.
- **Pinterest**: Idea Pins are indexed by Pinterest search; include keyword-
  rich text overlays for searchability in addition to aesthetic design.

---

## Save-Share Economics

### Save: "I Will Need This Later"

A save is a forward-looking behavior — the viewer identifies the content as
having future reference value and stores it for retrieval. Save-oriented
design means the carousel must function as a reference artifact: structured,
scannable, and dense with actionable information. Formats with the highest
intrinsic save rate: checklists, decision frameworks, comparison tables,
step-by-step processes with labeled steps, and curated resource lists.

The payoff slide is the save trigger. If the payoff slide delivers a framework
or decision tool dense enough to warrant re-consultation, save rate will reflect
it. If the payoff slide is a motivational statement or brand recall message,
save rate will be suppressed regardless of development quality.

### Share: "They Need This Now"

A share is a relationship-directed behavior — the viewer identifies the content
as relevant to a specific person or network and routes it there. Share-oriented
design means the carousel must contain a slide or statement the viewer can
use as a social signal: something that articulates their experience, validates
their position, or provides information that makes them appear informed or
helpful to their network.

Shares to Stories (Instagram, Facebook) extend organic reach beyond followers
without algorithm penalty. Shares via DM indicate high personal relevance.
Design at least one development slide with share-trigger intent — a counter-
intuitive framing, a specific data point, or a statement that validates a
professional identity the target audience holds.

### Designing for Both Simultaneously

Save and share are compatible objectives but serve different slide positions.
The payoff slide earns saves; middle development slides earn shares. A carousel
designed to optimize only for saves (dense, reference-heavy throughout) tends
to be too information-dense for share behavior. Design the development arc for
share triggers at slides 3–5; design the payoff for save retention. A carousel
that earns both signals receives multiplicative algorithmic distribution.

---

## Carousel A/B Testing

### Cover Variant Testing

Cover slide variants are the highest-leverage A/B test in carousel
optimization. A 10% improvement in swipe-through rate on the cover compounds
across all downstream slides. Test one variable per cover variant: hook
framing (tension vs. pain point vs. curiosity gap), visual treatment
(typographic-only vs. image-backed), or subject line length (long-form
headline vs. short punchy claim). Do not change multiple variables
simultaneously — attribution becomes impossible.

Minimum sample size before declaring a winner: 500 impressions per variant.
Below this threshold, engagement rate variance from audience sampling dominates
signal from the actual content difference.

### Payoff Slide Variants

Payoff slide testing identifies whether a framework, checklist, or key insight
produces higher save rates than a motivational CTA or narrative resolution.
Run payoff variants with cover held constant. Metrics: save rate (saves / reach)
is the primary signal; share rate is secondary. Do not use like rate as a proxy
for payoff effectiveness — likes do not indicate reference intent.

### Same Content, Multiple Aesthetics

Once a carousel narrative arc is validated (the argument structure earns
swipes and saves), test aesthetic variants with identical copy to identify
whether the visual system drives incremental performance. Aesthetic testing is
lower priority than hook and payoff testing — narrative structure has higher
variance contribution to outcome than visual treatment for most informational
carousels.

---

## Anti-Patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Text-wall slides with multiple paragraphs per slide | Scroll-speed processing cannot resolve multi-paragraph slides; completion rate collapses at first wall slide |
| Deck with no payoff slide — all content ends at the last development point | No concrete takeaway means no save trigger; the carousel is consumed and discarded |
| Repetition slides that paraphrase previous slides to fill slide count | Inflated slide count degrades completion rate; repetition signals low information density to the viewer |
| Decorative visual noise that reduces text contrast | Ornamental backgrounds or patterns that reduce contrast to below 4.5:1 make text illegible at thumbnail scale |
| Ignoring platform aspect ratio on export | Cropped text and broken visual hierarchy at render time; cover slide hook may be partially hidden |
| Weak cover hook — topic label instead of tension | "5 tips for productivity" is not a hook; it is a topic; it does not create the information gap that earns a swipe |
| Multiple CTAs on the closing slide | Split CTA intent reduces conversion; one action per closing slide |
| Designing development slides for reading, not scanning | Slides requiring 10+ second read time produce early abandonment; one visual anchor per slide maximum |

---

## Cross-References

- `domains/marketing-global/skills/instagram-curator` — Instagram-specific
  save-engine mechanics, format mix, and aesthetic coherence discipline;
  shares carousel design overlap but extends to Reels, Stories, and Feed.
- `domains/marketing-global/skills/linkedin-content-creator` — LinkedIn
  document carousel and thought-leadership content architecture; covers
  professional-positioning constraints specific to the LinkedIn algorithm.
- `domains/marketing-global/skills/content-creator` — cross-platform
  content creation discipline covering narrative architecture, audience
  research, and voice consistency; provides the upstream authoring frame
  within which carousel slide copy is produced.

---

## ADR Anchors

- **ADR-058** — Creative content authoring policy: house-voice rules
  (declarative prose, no emojis in framework artifacts, no 2nd-person
  address), maximum verbatim-match threshold with upstream sources, and
  structural inspiration attribution requirements. All content in this
  SKILL.md is original prose authored under ADR-058 constraints.
