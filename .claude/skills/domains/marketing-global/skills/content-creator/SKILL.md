---
name: content-creator
description: >
  Cross-platform content creation discipline covering narrative architecture,
  distribution-aware editing, repurposing matrix design, audience research
  methodology, and voice consistency enforcement. Generalist content authoring
  as opposed to platform-specific specialisation. Applies the problem-tension-
  resolution arc as the primary structural frame, enforces segmentation-first
  audience analysis, and gates all production decisions on format-audience fit
  rather than format preference. Use when: authoring or reviewing long-form
  articles, video scripts, or email sequences; designing a repurposing plan for
  existing assets; auditing content for voice drift; evaluating whether a content
  piece serves a defined audience segment with a defined intent; or establishing
  a voice document for a brand or persona.
owner: Isabela Monteiro (Content Creator, domain persona)
tier: domain:marketing-global
scope_tags: [content-creation, narrative-architecture, repurposing-matrix, audience-research, voice-consistency, cross-platform]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-content-creator.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/content/**"
  - "**/articles/**"
  - "**/newsletters/**"
  - "**/blog/**"
---

# Content Creator

## Cardinal Rule

Content earns audience attention by delivering a concrete outcome — a decision
clarified, a concept understood, a problem solved — in the least number of words
the argument requires. Length is not a proxy for depth. A 200-word piece that
answers the reader's actual question outperforms a 2,000-word piece that
demonstrates the author's knowledge of adjacent topics. Every sentence must
either advance the argument or be cut. Audience time is the scarcest input in
content production; treat every editorial choice as an allocation of that
resource.

---

## Fail-Fast Rule

Content MUST NOT be published without a defined audience segment, a defined
intent, and a defined success signal — all three confirmed before the first
draft is written. Publishing without these three gates produces output volume,
not content strategy. The following conditions MUST hold before production
begins:

1. The target audience segment is named with at least one pain, one aspiration,
   and one vocabulary preference documented — not inferred from analytics
   alone (see Audience Research Discipline below).
2. The intent is classified: awareness, consideration, conversion, retention,
   or advocacy — not "general interest."
3. The success signal is defined as a measurable proxy — scroll depth, conversion
   event, share rate, time-on-page, or reply rate — not impressions or reach
   alone.

If any gate is unresolved, production is blocked until it is closed.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Authoring or reviewing a long-form article, white paper, case study, or
  newsletter issue.
- Writing or structuring a video script, podcast outline, or webinar narrative.
- Designing a repurposing plan that converts one anchor asset into channel-native
  derivatives.
- Auditing an existing content piece for voice drift, narrative incoherence, or
  audience mismatch.
- Building or revising a brand voice document that defines tone register, reading
  level, and persona guardrails.
- Evaluating whether an editorial calendar is structured around audience intent
  or around production convenience.
- Writing email sequences, onboarding copy, or in-product content where voice
  consistency is load-bearing.

Skip when: the task is exclusively technical SEO (keyword research, backlink
analysis, technical audit) — route to `domains/marketing-global/skills/seo-specialist`;
the task is platform-specific paid distribution — route to paid-media domain;
or the task is growth-loop instrumentation — route to
`domains/marketing-global/skills/growth-hacker`.

---

## Audience Research Discipline

Segmentation precedes demographics. Knowing that a segment is "25-34-year-old
urban professionals" is less actionable than knowing the specific pain the
segment is trying to resolve this week, the aspiration they are privately
pursuing, and the vocabulary they use when they describe both. Demographic
data describes who; behavioral and psychographic data describes why; only the
why drives content decisions.

### Research Inputs Ranked by Signal Quality

| Tier | Input | Use |
|---|---|---|
| T1 | Direct interviews (6+ per segment) | Pain vocabulary, mental models, purchase triggers |
| T2 | Support and sales call transcripts | Actual language used under pressure |
| T3 | Community threads, forums, reviews | Unsolicited sentiment; language when no one is selling |
| T4 | Behavioral analytics (session depth, exit pages) | Confirms or refutes; NEVER leads |
| T5 | Demographic analytics | Context only; never the primary audience signal |

T4 and T5 analytics confirm hypotheses; they do not generate them. An editorial
brief built on analytics without T1-T3 inputs is built on measurement artifacts,
not audience understanding.

### Audience Profile Minimum Required Fields

Before any content brief is approved, the audience profile MUST include:

- Named segment identifier (not "general audience" or "our users").
- Primary pain: the specific friction the segment is actively trying to reduce.
- Primary aspiration: the outcome state they are privately seeking.
- Vocabulary sample: 5-10 terms the segment uses to describe the problem in
  their own words — drawn from T1-T3, never from the brand's own copy.
- Content consumption context: when and where the segment encounters this
  content type (commute, deep-work block, research phase).
- Competing attention: what else is the segment reading or watching on this
  topic; what has already failed to hold their attention and why.

Assuming vocabulary from analytics or brand copy is the most common audience
research failure mode. If the vocabulary sample was not sourced from T1-T3
inputs, it is a hypothesis — label it as such and validate before scaling
production around it.

---

## Narrative Architecture

Every content piece, regardless of format or length, requires a structural
arc. The default frame is problem-tension-resolution: establish the problem
the audience already recognizes (not the problem the brand wants to talk
about), introduce the tension that prevents easy resolution, and deliver the
resolution with enough specificity that the reader can act on it or evaluate
it against their situation.

### Structural Principles

**Specific beats universal.** "Revenue teams lose deals because procurement
extends cycles by an average of 34 days" is a usable claim. "Sales is getting
harder" is ambient noise. Specificity is the mechanism by which an argument
distinguishes itself from the background. If a sentence could be cut and the
remaining text would read the same, cut it.

**One idea per piece.** A content piece that attempts to deliver three insights
delivers none of them at depth. A defined single claim, argued fully, with
evidence and a clear takeaway, outperforms a listicle of related claims. The
single-idea discipline is also the mechanism that drives repurposing fidelity:
a 2,000-word piece built around one idea generates 8-12 channel-native pieces
with coherent through-lines; a 2,000-word piece built around seven ideas
generates seven unrelated fragments.

**Lead with the insight, not the backstory.** The opening sentence must deliver
the claim or the tension, not a preamble about the topic's importance or the
author's qualifications. Readers decide whether to continue reading within the
first 30 words. Backstory, context-setting, and credential signaling belong in
the body if they belong anywhere.

### Opening Patterns That Fail

The following opening constructions are anti-patterns. They signal that the
piece has not yet identified its actual argument:

- "In today's fast-paced digital landscape..." — generic framing, no claim.
- "Content marketing is more important than ever..." — obvious and unactionable.
- "As a [role], you know that..." — assumes shared context that may not exist.
- "There are many factors to consider..." — hedged non-start.

Replace with: the specific problem, a contrarian claim, a data point that
reframes a common assumption, or the resolution stated upfront with the
argument to follow.

---

## Format Selection

Format follows audience, not preference. The correct format for a piece is
determined by three variables: the intent of the piece (awareness, consideration,
conversion, retention), the consumption context of the target segment (scrolling
feed, deep-read session, active search), and the complexity of the argument
(whether the claim requires sustained reading or is self-contained in one
encounter).

### Format-to-Intent Mapping

| Format | Best intent fit | Consumption context | Complexity ceiling |
|---|---|---|---|
| Long-form article / white paper | Consideration, retention | Deep-read; active search | High — multi-step argument |
| Short-form post (social) | Awareness | Feed scroll; passive encounter | Low — single claim |
| Video script (2-10 min) | Awareness, consideration | Lean-back; commute | Medium — sequential argument |
| Email sequence | Consideration, conversion, retention | Deliberate attention; inbox session | Medium-high — relationship arc |
| Podcast / audio | Awareness, consideration | Background; commute | Medium — conversational arc |
| Visual / infographic | Awareness | Quick scan; passive share | Low — reference or comparison |

Choosing long-form for an awareness-intent piece addressed to a scroll-context
audience is a format error. Choosing a short-form post for a high-complexity
argument targeted at a consideration-stage segment is equally a format error.
Mismatch between format and intent produces content that underperforms regardless
of writing quality.

---

## Repurposing Matrix

One anchor asset produces 8-12 channel-native derivatives when the repurposing
process is structured. The operative constraint is channel-native rewrite, not
cross-post. Copying the same text across channels is distribution, not
repurposing; it delivers the same content to potentially overlapping audiences
and produces no incremental value.

### Repurposing Hierarchy

Start with the anchor asset — a long-form article, a recorded presentation, a
research report, or a deep interview. The anchor must be built around a single
claim (see Narrative Architecture) or repurposing coherence breaks.

From one anchor, the standard derivative map:

| Derivative | Channel-native requirement | Production note |
|---|---|---|
| 3-5 thread posts (LinkedIn / X) | Each thread is one sub-argument from the anchor, rewritten for feed context | Do NOT lift paragraphs verbatim; restate for audience and velocity |
| 2-3 short-form videos (90s) | One claim per video; visual hook in first 3s; no reliance on audio alone | Script separately — anchor prose does not translate to video cadence |
| 1 email issue | Narrative frame + single CTA; longer reading block tolerated | Recontextualize anchor claim in relationship frame |
| 1-2 data visualization assets | Extract the single most counterintuitive data point | Build around the delta, not the full dataset |
| 1 podcast episode outline | Conversation version of the anchor claim; allows disagreement | Producer must introduce tension that the article resolved cleanly |
| 1 Q&A or FAQ derivative | Extract the 3-5 implied questions the anchor answers | Useful for search-intent derivatives and onsite content |

### Audience Overlap Detection

Before scheduling derivatives, map audience overlap across channels. Deploying
the same claim to an audience that already received the anchor in a different
format produces diminishing returns and signals low content breadth. Overlap
detection requires knowing the segmentation of each channel's actual audience
— not the platform's user base — and scheduling derivatives to reach segments
that did not encounter the anchor.

---

## Voice Consistency

Voice is the pattern of decisions a content operation makes consistently:
which words to prefer, which sentence structures to avoid, what reading level
to target, which topics to decline, and what persona the content projects
collectively. Voice is not style — style varies by format and intent; voice
is invariant.

### Voice Document Requirements

A voice document MUST be produced before content production scales beyond one
author. A voice document that is not tested against live content is a brand
aspiration, not an operational constraint. The minimum required sections:

- **Tone register**: select two to four adjectives from a defined list (not
  invented), then document the specific behaviors each adjective requires and
  prohibits. Adjectives without behavioral anchors are decorative.
- **Reading level target**: specify a Flesch-Kincaid grade level range (not
  "clear and simple"). Grade 8-10 is the standard B2B business content range.
  Variation above or below that range requires explicit justification.
- **Vocabulary preferences and prohibitions**: list 10-20 specific word choices
  the brand makes (preferred) and 10-20 it avoids (prohibited). Include reason
  for each prohibition — without a reason, the prohibition will not survive
  author turnover.
- **Persona guardrails**: define what the brand's content persona does not do —
  does not make claims without evidence, does not use first-person superlatives,
  does not take positions on topics outside its defined authority domain.

### Voice Drift Detection

Voice drift occurs when content published under the same brand or author
persona diverges from the established tone register across a content batch.
Drift is not stylistic variation — it is structural: the reading level shifted
by more than two grade points, prohibited vocabulary appeared, or the claim
confidence register changed (from measured to superlative or vice versa). Audit
for voice drift at minimum once per quarter on a random sample of 10-15 pieces
published in that period.

---

## SEO and AEO Frame

Content and search intent alignment is a prerequisite for organic distribution,
not a post-production optimization pass. Search intent classification (navigational,
informational, commercial, transactional) must inform the content brief before
writing begins, not be retrofitted after the piece is drafted.

### Intent-to-Structure Mapping

Informational intent requires depth and structure: the piece must satisfy the
query fully without requiring additional searches. Commercial intent requires
comparison structure and concrete differentiation criteria. Transactional intent
requires the answer first and the argument second.

Entity-aware structure means the piece names, defines, and contextualizes the
primary entity and its relationships to adjacent entities in a way that allows
a language model or structured parser to extract the semantic frame without
ambiguity. This is not keyword stuffing; it is precision in how claims are
stated.

For technical SEO depth — structured data implementation, crawl optimization,
page-speed impact, canonical tagging — route to
`domains/marketing-global/skills/seo-specialist`. This skill covers content
architecture and intent alignment; technical implementation is out of scope.

### AEO (Answer Engine Optimization)

As retrieval-augmented search surfaces become primary discovery channels, content
structure determines whether a piece is cited as a source. AEO requirements:

- State the direct answer to the implied question within the first 100 words of
  the relevant section.
- Use headers as indexable claims, not topic labels. "Five distribution mistakes"
  is a topic label; "Distribution failures occur most often in the first 72 hours
  after publish" is an indexable claim.
- Cite sources for data claims with publication year. Undated claims are excluded
  from citation by retrieval systems.

---

## Distribution Discipline

The 3:1 rule: for every one hour spent creating content, allocate three hours
to distribution. Most content operations invert this ratio — they optimize for
production volume and under-invest in ensuring the content reaches the segments
it was built for. Production without distribution is storage.

### Distribution Activities Required Per Piece

- **Owned channels** (email list, community): publish immediately on release.
  Owned audiences have the highest engagement probability and require no
  algorithm mediation.
- **Earned channels** (organic social, SEO): schedule and publish per platform-
  native timing windows. Platform-specific timing data is available from each
  platform's analytics — anchor to the specific account's historical engagement
  window, not generic industry benchmarks.
- **First-hour engagement**: respond to all comments, shares, and replies within
  the first 60 minutes of publishing. Platform algorithms weight first-hour
  engagement signals heavily in feed distribution. Ignoring first-hour engagement
  in favor of passive monitoring is a common distribution failure.
- **Amplification routing**: identify 3-5 individuals or accounts for whom the
  content is genuinely useful and share it directly. This is not broadcast; it
  is targeted delivery.

### Algorithm-Aware Timing

Platform distribution algorithms vary by content type and change on a rolling
basis. The reliable signal is account-specific historical data, not published
platform guidance. Review the account's analytics quarterly to confirm whether
the timing model is still accurate. When in doubt, publish in the first half of
the audience's primary active window — it is better to be early in a window
than to miss it attempting to hit a precise optimal moment.

---

## Anti-Patterns

| Anti-pattern | Description | Correction |
|---|---|---|
| AI slop | Publishing LLM-generated drafts without editorial re-authoring — detectable by hedging density, generic framing, and absence of specific claims | Every piece requires a human editorial pass that rewrites at least 30% of the draft; if less than 30% required rewriting, the brief was too generic |
| Voice drift | Content published under one brand or persona but reading as authored by a different register — reading level shift, prohibited vocabulary, inconsistent claim confidence | Quarterly voice audit on random sample; voice document with behavioral anchors |
| Format chasing | Choosing a format because a competitor or trend uses it, not because it matches the audience's consumption context for this intent | Return to format-intent-context matrix; document the evidence that this format fits this segment at this stage |
| Derivative repackage | Copying text from one channel to another without rewriting for channel-native context | Channel-native rewrite is mandatory; cross-post is not repurposing |
| Cadence fetish | Publishing on a fixed schedule regardless of whether the piece meets quality and audience-fit gates | Publishing cadence is subordinate to quality gate; a delayed piece that answers a defined audience question outperforms an on-schedule piece that does not |
| Insight-free SEO | Writing to rank for a keyword without delivering a usable insight to the ranking audience | Define the user's specific question first; keyword selection follows from intent mapping, not from search volume alone |

---

## Cross-References

- `domains/marketing-global/skills/seo-specialist` — technical SEO depth,
  structured data, crawl optimization, backlink strategy. Route when the task
  requires implementation-level search work beyond content architecture.
- `domains/marketing-global/skills/social-media-strategist` — platform-specific
  distribution strategy, community management, algorithm-specific production
  decisions. Route when the task is platform mechanics rather than content
  authorship.
- `domains/marketing-global/skills/growth-hacker` — conversion rate optimization,
  growth-loop instrumentation, A/B test framework design. Route when the task
  is performance optimization on existing content rather than authorship of new
  content.

---

## ADR Anchors

- **ADR-058** (Brainstorm gate pre-Plan + two-pass adversarial review): the
  brainstorm gate discipline for pre-production brief validation maps directly
  to this skill's audience profile and intent gates. Before a content piece
  enters production, the audience profile minimum required fields (see Audience
  Research Discipline) serve as the content equivalent of ADR-058's spec artifact.
  The two-pass adversarial review pattern applies to voice consistency audits:
  the first pass reads for argument coherence; the second pass reads specifically
  for voice drift, prohibited vocabulary, and format-intent mismatch.
