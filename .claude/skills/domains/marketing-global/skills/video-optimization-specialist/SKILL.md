---
name: video-optimization-specialist
description: >
  Long-form video discipline — YouTube-first, with application to
  IG-Reels long-cuts and TikTok Stories — covering title and thumbnail
  optimisation as a coupled pair, retention curve diagnostics, watch-time
  architecture, A/B testing for packaging variants, end-screen and cards
  strategy, and SEO-grounded discovery. Distinct from `tiktok-strategist`,
  which governs the short-form completion-rate game; this skill governs
  the long-form retention game where Average View Duration and binge
  architecture are the primary algorithmic levers. Use when: designing
  or auditing a YouTube content strategy, diagnosing retention cliff
  patterns, scripting watch-time pacing for videos over three minutes,
  building thumbnail iteration cycles, structuring end-screen binge chains,
  or evaluating keyword research for video discoverability.
owner: Marcus Alden (Video Optimization Specialist, domain persona)
tier: domain:marketing-global
scope_tags: [youtube, long-form-video, retention-curve, thumbnail-testing, watch-time, video-discoverability]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-video-optimization-specialist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/youtube/**"
  - "**/videos/**"
  - "**/thumbnails/**"
---

# Video Optimization Specialist

## Cardinal Rule

Average View Duration is the primary algorithmic lever for long-form video.
YouTube's recommendation engine evaluates absolute watch time — minutes
delivered per impression — above raw view count or CTR. A ten-minute video
watched to 80% completion signals more value than a twenty-minute video
watched to 20%. Every structural decision — title, thumbnail, hook length,
pacing cadence, chapter placement — MUST be evaluated against its projected
effect on AVD before any other metric is applied. Reporting view count or
CTR without AVD context is incomplete and MUST NOT be used as a standalone
performance summary.

---

## Fail-Fast Rule

A video MUST NOT be published without verifying the title-thumbnail pair
as a single unit. Title and thumbnail are co-dependent packaging: a strong
thumbnail with a weak title produces curiosity without context; a strong
title with a weak thumbnail produces context without click signal. Both
components MUST satisfy their individual gates AND the combined test: does
the pair, read together in under two seconds, make an unambiguous promise
that the video can keep? If the pair fails this test at review, packaging
MUST be revised before scheduling. Publishing with unvalidated packaging
and relying on post-publish impressions to detect failure wastes the
first-48-hour velocity window that YouTube weights most heavily.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Designing or auditing a YouTube content strategy that requires algorithm-
  aware packaging, retention architecture, or discovery mechanics.
- Diagnosing a retention cliff, low AVD, or suppressed impression share
  on an active channel.
- Scripting or reviewing the hook structure of a video longer than three
  minutes where pacing across the full duration must be deliberate.
- Building a thumbnail iteration cycle using the YouTube Test and Compare
  feature or third-party A/B tooling.
- Structuring end-screen binge chains or card sequences to extend session
  time after video completion.
- Evaluating keyword research and chapter metadata for video discoverability
  in YouTube Search and Browse.
- Advising on playlist architecture or series structure for long-form
  content libraries.

---

## Title and Thumbnail Architecture

Title and thumbnail function as a CTR-driving pair; they MUST be designed
together and MUST NOT be iterated independently.

**Title gates:**

A title passes when it satisfies all four conditions: (1) it contains a
primary keyword phrase that matches the search intent of the target
audience; (2) it creates a curiosity gap, a stated benefit, or a named
contrast — one dominant mechanism, not a combination; (3) it fits in
sixty characters so it renders without truncation on mobile; (4) the
implied promise is one the video can deliver in full before the end
screen.

**Thumbnail gates:**

A thumbnail passes when: (1) the primary subject is identifiable at
96 × 54 pixels — the size at which YouTube renders mobile suggestions;
(2) on-screen text, if present, uses no more than four words and a
minimum 36pt equivalent at full resolution; (3) the colour contrast
between foreground and background exceeds a 4:1 ratio; (4) the visual
and the title, read together, form a complete micro-story without
redundancy — the thumbnail must add information the title omits.

**Iteration cycle:**

After the initial publish, packaging variants MUST be queued for
the YouTube Test and Compare feature (minimum two thumbnail variants
per test). The test window requires at least 2 000 impressions per
variant to produce a statistically meaningful CTR difference. Replace
the losing variant; do not retire the control until the challenger has
sustained the CTR delta over a 72-hour window.

---

## Hook Discipline

The first fifteen seconds of a long-form video are the retention
determinant. Unlike short-form, where the three-second commit governs
FYP distribution, long-form retention is evaluated against a graph
that penalises drop-off in the first 30% of the video most severely.

**Payoff promise:**

The opening must state, visually or verbally, exactly what the viewer
will gain by watching to the end. The promise must be specific enough
to be falsifiable: "I will show you the three steps" is a promise; "let
me share some thoughts" is not. Vague hooks depress early retention and
signal to the algorithm that the packaging over-promised.

**Curiosity gap:**

After the payoff promise, the hook must withhold the mechanism — the
specific method or reveal — long enough to establish context but not
so long that the viewer infers the answer. The standard structure: state
the problem, name the result, defer the method. The method arrives at
or after the one-minute mark on videos over eight minutes.

**Fake-pivot prohibition:**

A hook that promises a resolution and then pivots to unrelated context
before delivering any signal is a fake-pivot. Fake-pivots produce a
retention cliff at 30–45 seconds that is algorithmically indistinguishable
from a low-quality video. Fake-pivots MUST NOT appear in scripted content;
if detected in a retention audit, the hook MUST be rewritten as a
condition of the next upload.

---

## Retention Curve Optimisation

The YouTube Studio retention graph provides a per-second audience drop-off
curve for every video. Retention curve review MUST precede any script
revision or packaging change.

**Graph diagnostic table:**

| Curve shape                   | Diagnosis                                      | Intervention                                           |
|-------------------------------|------------------------------------------------|--------------------------------------------------------|
| Sharp drop 0–15 s             | Hook failure or packaging-content mismatch     | Rewrite opening 15 s; audit title-thumbnail alignment  |
| Gradual slope 15–60 s         | Context too long; value delivery too slow      | Move primary payoff signal before 60 s                 |
| Cliff at 20–35% duration      | Mid-section has no secondary hook              | Insert partial reveal or chapter transition at cliff   |
| Cliff at 50–60% duration      | Viewer inferred full resolution before end     | Restructure proof section; reserve key detail for end  |
| Rewatch spike at one moment   | High-value moment identified by audience       | Promote as clip; use timestamp in description          |
| Flat then cliff near end      | Strong content; end screen pacing too abrupt   | Add 30 s resolution + bridge to next suggested video   |

**Intro length benchmark:**

For videos over eight minutes, the intro — context-setting before the
first value delivery — MUST be under 90 seconds. For videos between
three and eight minutes, the intro ceiling is 45 seconds. Intros that
exceed these thresholds without an embedded secondary hook produce a
retention cliff at the boundary.

---

## Watch-Time Architecture

The target for long-form content is 50% or above Average View Duration
across the video library. Architecture decisions that affect AVD operate
at three levels: pacing per minute, visual variety cadence, and chapter
sequencing.

**Pacing per minute:**

Each minute of a long-form video must contain one of the following
structural events to prevent attention decay: a new claim introduced,
a contradiction or complication surfaced, a visual or tonal shift, or
a partial resolution that resets the curiosity gap. Videos that run a
single explanatory thread for more than 90 consecutive seconds without
a structural event will register a consistent slope in the retention
graph at that interval.

**Visual variety cadence:**

On-screen content MUST change at minimum every 30 seconds for tutorials
and explainers. Acceptable change events: cut to B-roll, on-screen
graphic, text callout, scene transition, or presenter angle change.
Static talking-head video that exceeds 45 consecutive seconds without
a visual change is a confirmed source of retention drop in long-form
content across all topic categories.

**Chapter sequencing:**

Chapters must be ordered to sustain forward tension, not to achieve
logical completeness. If the most compelling chapter is the fourth,
promote its premise into the hook and structure earlier chapters as
prerequisites that build anticipation for the fourth, not as standalone
sections that stand before it by convention.

---

## End-Screen and Cards Strategy

End-screens and cards extend session time by directing viewers to the
next video or playlist before the session terminates. Session extension
is a first-order ranking signal for the suggested algorithm.

**End-screen architecture:**

The end-screen zone begins at the 20-second mark before the video
conclusion. MUST contain: one best-for-viewer video selection (YouTube
algorithm choice enabled) AND one creator-specified video that continues
the content thread the viewer just watched. Generic channel subscription
CTAs in the end-screen zone without a specific video target are wasted
surface.

**Series structure:**

Videos with defined series relationships MUST be grouped in a named
playlist and the end-screen of each video in the series MUST link to
the next episode. Unstructured playlists — thematic collections without
sequential narrative — produce lower average session depth than series
playlists by a measurable margin because viewers lack the expectation of
sequential payoff.

**Binge architecture:**

A channel builds binge architecture when at least 30% of its videos
contain explicit verbal bridges to a specific follow-on video in the
final 90 seconds. The bridge must name the destination ("the next video
covers the second technique") rather than offering a generic invitation
("check out the playlist"). Named bridges convert at higher rates than
generic CTAs because they re-establish a payoff promise for the next
unit of attention.

**Cards strategy:**

Cards MUST be placed at moments of peak retention — rewatch spikes or
the top of the retention curve plateau — not at low-retention valleys
where the audience is already partially disengaged. A card placed at
a cliff accelerates the exit; a card placed at a peak captures viewers
at their highest engagement. Card timing MUST be audited against the
retention graph, not placed by convention at 30% intervals.

---

## A/B Testing Framework

Packaging variants — thumbnail and title permutations — are the highest-
leverage A/B tests available in long-form video because packaging drives
CTR, which initiates all subsequent retention and AVD measurement.

**Test design:**

Run one variable at a time: either a thumbnail variant with the title
held constant, or a title variant with the thumbnail held constant.
Testing both simultaneously prevents attribution of CTR delta to either
variable. Each test requires a minimum of 2 000 impressions per variant
before declaring a result.

**First-3-day window:**

YouTube allocates its highest impression share to a video in the first
72 hours after publication. A/B tests that begin at publish and conclude
within this window capture the audience segment most likely to convert to
subscribers and influence the sustained recommendation share. Tests
initiated after day 3 operate on a reduced impression pool and produce
slower convergence.

**Statistical significance threshold:**

Declare a winner only when the CTR delta between variants exceeds 0.5
percentage points and has held for 72 consecutive hours of active testing
(minimum 1 000 impressions per variant per 24-hour period). Declaring
winners on fewer than 1 000 impressions per variant produces false
positives that replace a performing packaging with an under-tested one.

**Title variant types to test:**

Curiosity-gap titles versus benefit-led titles are the most reliably
distinct test pairs; curiosity-gap tends to outperform in discovery
(Browse and Suggested) while benefit-led tends to outperform in Search.
The dominant traffic source for the channel determines which variant
class to default when resources allow only one title.

---

## SEO and Discovery

Video discoverability operates on two distinct ranking systems: YouTube
Search (query-intent matching) and Browse/Suggested (behavioural
affinity matching). A video optimised for one system is not automatically
optimised for the other.

**Description strategy:**

The first two lines of the description are rendered in search snippets
before the fold. These lines MUST contain the primary keyword phrase,
a secondary synonym phrase, and the core value proposition of the video.
Auto-generated descriptions from transcript tools MUST NOT be used
without manual revision; they rarely front-load keyword density and
produce descriptions that are indistinguishable from boilerplate.

**Chapter metadata:**

Chapters, declared via timestamps in the description, enable YouTube to
surface individual chapter segments in Google Video search results.
Every video over five minutes MUST include chapters. Chapter titles MUST
be keyword-conscious, not conversational summaries; "How to fix render
errors" outperforms "Fixing the errors I mentioned" for chapter-level
search indexing.

**Keyword research protocol:**

Keyword research for each video MUST be performed against the specific
niche of the video, not the channel's general topic. Tools that surface
search volume and competition at the YouTube-native level (not web search
proxies) MUST be used. Auto-generated keyword lists from general-purpose
SEO tools are advisory inputs, not direct tag lists; every tag applied
MUST be reviewed for channel-topic relevance before publishing.

---

## Anti-patterns

| Anti-pattern                          | Failure mode                                                                     | Correct behaviour                                                               |
|---------------------------------------|----------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| Clickbait without payoff              | Audience infers mismatch; dislike ratio rises; YouTube reduces recommendation share | Title and thumbnail promise MUST match video content exactly                   |
| Ignoring CTR below 4%                 | Low CTR suppresses impression allocation; video never enters growth loop         | Diagnose packaging failure before attributing to topic or content quality       |
| No thumbnail iteration                | Single thumbnail locks in suboptimal CTR indefinitely                            | Queue A/B test within 24 hours of publish using Test and Compare                |
| Padded runtime to meet monetisation   | AVD percentage drops as padding is detected; algorithmic ranking penalises ratio | Cut to minimum runtime that delivers the full promised value without padding    |
| Broken playlist structure             | Viewers exit after one video; session depth collapses; suggested algorithm weakens | Every series video MUST link forward; playlists MUST have sequential logic     |
| Auto-generated descriptions published | Boilerplate descriptions reduce keyword density; search indexing weakens         | Manual description review is non-negotiable for every upload                   |
| Generic end-screen CTAs               | "Subscribe and like" without video destination wastes session extension window   | Always specify a named destination video in the verbal bridge and end-screen    |

---

## Cross-References

- `domains/marketing-global/skills/tiktok-strategist` — Short-form
  completion-rate mechanics, hook architecture for vertical video, trend
  velocity strategy; governs the FYP distribution model distinct from
  YouTube's AVD-weighted ranking.
- `domains/marketing-global/skills/podcast-strategist` — Long-form audio
  content architecture, episode structure, and listener retention patterns;
  structural parallels with watch-time sequencing and binge mechanics.
- `domains/marketing-global/skills/content-creator` — Long-form to
  short-form repurposing strategy, editorial calendar integration, and
  narrative structure that feeds video scripting upstream.

---

## ADR Anchors

- **ADR-058** — Creative authorship and structural-inspiration licensing
  policy; governs `inspired_by` attribution requirements for domain skill
  files derived from upstream open-source agent corpora.
