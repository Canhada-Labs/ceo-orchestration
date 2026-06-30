---
name: podcast-strategist
description: >
  Podcast production and growth discipline covering show concept architecture,
  episode structure engineering, guest relations protocols, audio production
  standards, multi-platform distribution mechanics, and monetisation integrity.
  Enforces audience-first concept framing over host-first angle selection,
  applies loudness and noise-floor targets as hard production gates, and gates
  all monetisation decisions on editorial-independence preservation. Use when:
  designing or repositioning a podcast show concept; structuring an episode
  outline for a guest interview or solo format; auditing audio production
  quality against loudness targets; selecting or rebalancing a distribution
  platform mix; diagnosing low listen-through-rate or completion-rate trends;
  evaluating a sponsorship or membership proposition against editorial-
  independence criteria; or building a guest pipeline and release-consent
  workflow.
owner: Renata Solis (Podcast Strategist, domain persona)
tier: domain:marketing-global
scope_tags: [podcast-production, episode-architecture, audio-production, podcast-distribution, audience-growth, monetisation]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-podcast-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/podcast/**"
  - "**/podcasts/**"
  - "**/episodes/**"
---

# Podcast Strategist

## Cardinal Rule

A podcast show earns listener retention by delivering a specific, repeatable
value in a consistent format at a predictable cadence. Show concept, episode
architecture, and production quality are not aesthetic choices — they are
structural contracts with the audience. Breaking any of the three (concept
drift, format inconsistency, erratic cadence) degrades the trust that drives
completion rates and subscription compounding. The unit of competitive advantage
in audio is cumulative listen-through time, not episode count or download
spikes. Every production decision must be evaluated against whether it increases
or decreases that cumulative time.

---

## Fail-Fast Rule

Production MUST NOT begin on an episode or series without three confirmed
inputs: a defined audience segment, a confirmed show angle that compounds over
time rather than decays, and an audio environment that meets the noise-floor
threshold. The following conditions MUST hold before any episode enters
recording:

1. The target audience segment is named with a documented consumption context
   (commute, background, focused listening) and a specific unresolved tension
   the episode addresses — not a topic category.
2. The show angle has been tested against the decay criterion: an angle that
   requires novelty to sustain (trending news, current events reaction) decays;
   an angle anchored in durable tension or durable aspiration compounds. A
   decaying angle is not a show concept — it is an editorial calendar.
3. The recording environment has passed a noise-floor check: ambient noise
   measured below -60 dBFS in the recording space before any guest or host
   speaks. Environments that fail this threshold require treatment before
   scheduling.

If any gate is unresolved, the episode is blocked.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Designing a new podcast show concept from brief or audience research.
- Repositioning an existing show that has experienced audience plateau or
  completion-rate decline.
- Structuring a guest-interview episode outline including pre-recording brief
  and question architecture.
- Auditing a delivered audio file for loudness target compliance, noise-floor
  threshold, and voice intelligibility.
- Selecting or rebalancing a distribution platform mix based on discoverability
  mechanics per platform.
- Diagnosing listen-through-rate or completion-rate decline and identifying
  structural episode causes.
- Evaluating a sponsorship, platform ad-network, or membership monetisation
  proposition for editorial-independence risk.
- Building or auditing a guest pipeline, release-consent workflow, or post-
  recording approval protocol.

Skip when: the task is exclusively written content strategy — route to
`domains/marketing-global/skills/content-creator`; the task is short-form
video repurposing of audio content — route to
`domains/marketing-global/skills/video-optimization-specialist`; the task
is platform-agnostic social distribution of episode clips — route to
`domains/marketing-global/skills/social-media-strategist`.

---

## Show Concept Architecture

Show concept is audience-first, not host-first. The most common podcast
positioning failure is building a concept around the host's existing knowledge
domain or professional identity rather than around a specific unresolved tension
the target audience carries. A host-first concept produces a show that is easy
to start and difficult to grow; an audience-first concept produces a show that
is difficult to start and structurally compound.

### Angle Selection Criterion

Classify every candidate show angle against two vectors before committing:

| Vector | Compounds | Decays |
|---|---|---|
| Primary driver | Durable audience tension or aspiration | Novelty, trend proximity, current events |
| Longevity signal | 100-episode corpus is imaginable from brief | Requires ongoing external events to sustain |
| Differentiation | Rooted in host POV or format constraint | Rooted in topic adjacency to other shows |
| Risk | Slow start, strong retention | Fast start, audience churn at novelty ceiling |

Select the compounding angle. If no compounding angle is identifiable from the
current brief, the show concept requires further audience research before
production commitment.

### Format Consistency Constraint

Format — episode length range, segment structure, host-to-guest ratio, interview
versus solo ratio — must be defined and held across a minimum of twelve
consecutive episodes before any deviation is evaluated. Listeners build listening
habits against format predictability. Format inconsistency before habit formation
prevents habit formation; it does not signal creative variety. Deviations after
twelve episodes must be framed explicitly as intentional exceptions, not
undeclared format drift.

---

## Episode Structure

Every episode requires a defined structural contract before recording begins.
The default frame is: cold open, hook, body, and call to action.

### Structure by Duration Frame

| Frame | Cold Open | Hook | Body | Call to Action |
|---|---|---|---|---|
| 30 min | 0-90 s | 90 s-3 min | 3-27 min | 27-30 min |
| 60 min | 0-90 s | 90 s-4 min | 4-56 min | 56-60 min |
| 90 min | 0-90 s | 90 s-4 min | 4-86 min | 86-90 min |

**Cold open:** a single scene, data point, or claim that establishes the stakes
without requiring the audience to already care about the topic. The cold open
earns the right to deliver the host introduction and episode framing; it does
not begin with them.

**Hook:** the explicit statement of what the episode will deliver and why the
target audience should stay for it. The hook is a promise, not a topic
announcement. "Today we discuss revenue operations" is a topic announcement.
"By the end of this episode you will have a diagnostic framework for identifying
the single bottleneck in your revenue cycle" is a promise.

**Body segmentation:** episodes longer than 30 minutes require a retention anchor
every 8-12 minutes inside the body. A retention anchor is a contrast, a
counterintuitive finding, a story beat, or a direct listener engagement prompt
— not a recap of what was just said. Recaps do not sustain attention; they
signal to the listener that the information density is about to drop.

**Call to action:** a single, specific action with a completion time under three
minutes. Multiple simultaneous calls to action produce zero conversion. If more
than one action is worth requesting, sequence them across episodes rather than
stacking them in one outro.

---

## Guest Relations

Guest quality is the primary variable in interview-format episode performance.
Quality is not defined by guest status or audience size — it is defined by
specificity of experience and willingness to speak to concrete outcomes rather
than general frameworks.

### Pre-Recording Protocol

Before any guest is booked into a recording slot, three steps are mandatory:

1. **Research brief:** a document delivered to the guest at least 72 hours before
   recording that covers the show's audience profile, the specific territory the
   episode will explore, and the two or three primary questions the host intends
   to anchor the conversation. The brief is not a list of every question — it is
   a framing document. Guests who receive no brief default to prepared talking
   points; guests who receive a framing document default to genuine conversation.

2. **Recording window confirmation:** confirm the recording window, technical
   setup requirements, and backup recording method in the same message as the
   brief. Remote recording requires each participant to record a local track
   (the host's feed and the guest's feed as independent files) rather than
   relying on a single mixed capture. Local tracks preserve audio quality and
   enable independent post-production correction.

3. **Release-form acknowledgment:** the guest must confirm understanding of the
   show's editorial scope, publication timeline, and the terms under which the
   episode will be released before recording begins. Release consent is not
   obtained at the end of a recording session — it is obtained before it starts.

### Never Ambush

A guest must not be asked a question on a topic that was not covered in the
pre-recording brief if the question could reasonably cause the guest reputational
exposure, professional risk, or discomfort. "Never ambush" is not a courtesy
rule — it is an editorial-integrity rule. An ambush question that extracts a
reaction rather than a considered view produces content that misrepresents the
guest's position and damages the show's long-term guest pipeline.

---

## Audio Production Standards

Audio quality is a floor, not a differentiator. Listeners will not credit good
audio as a reason to subscribe; they will reject bad audio as a reason to
unsubscribe. The production standard must be set at the minimum level that
eliminates audio as a variable in completion-rate analysis.

### Loudness and Noise-Floor Targets

| Parameter | Target | Rejection Threshold |
|---|---|---|
| Integrated loudness (stereo delivery) | -16 LUFS | Outside -14 to -18 LUFS |
| Integrated loudness (mono delivery) | -19 LUFS | Outside -17 to -21 LUFS |
| True peak ceiling | -1 dBTP | Above -1 dBTP |
| Noise floor (recording environment) | Below -60 dBFS | Above -55 dBFS |

Delivery to Apple Podcasts, Spotify, and YouTube normalization pipelines assumes
files that conform to these targets. Files that exceed the true peak ceiling
introduce clipping artifacts after platform normalization. Files that fall below
the loudness floor produce listener fatigue through voluntary volume adjustment.

### Voice Intelligibility Test

Before final export, apply a mono-compatibility check: sum the stereo mix to
mono and confirm no cancellation artifacts appear in the voice frequency range
(300 Hz - 3500 Hz). A voice that is audible in stereo but cancels in mono fails
distribution in environments where mono playback is the norm (in-car, portable
speaker, phone speaker without headphones).

### Mastering Chain Order

The standard mastering chain for podcast audio applies in this order: noise
reduction, equalization, compression, limiting, loudness normalization. Applying
loudness normalization before limiting allows the limiter ceiling to be violated
by subsequent normalization. Applying compression before equalization shapes
frequency content after dynamic decisions have already been made — this is
acceptable for voice-only content but suboptimal when music beds are present.

---

## Distribution Platform Mix

RSS is the distribution infrastructure. One RSS feed generates syndication to
all RSS-compatible platforms. Manual upload is required only for platforms that
do not accept external RSS imports. The platform mix decision is not an audience
reach question — it is a discoverability mechanics question.

### Platform Discoverability Mechanics

| Platform | Primary Discovery Path | Chapter Markers | Transcript SEO |
|---|---|---|---|
| Apple Podcasts | Editorial curation, search, subscriber notification | Supported | Show notes only |
| Spotify | Algorithmic recommendation, search, curated playlists | Supported | Full transcript indexing supported |
| YouTube | Search, algorithmic recommendation, subscriber feed | Supported via chapters | Auto-caption; manual transcript preferred |
| RSS (all others) | Aggregator search, subscriber sync | Aggregator-dependent | Show notes pass-through |

**Chapter markers:** implement chapter markers on every episode regardless of
episode length. Chapters serve two functions — listener navigation within a
single session, and discoverability on platforms that surface chapter-level
content in search results. A chapter marker without a descriptive label (not
"Part 1" or "Section 2") provides zero discoverability value.

**Transcript SEO:** a human-reviewed transcript published in show notes provides
the highest SEO signal available for a podcast episode. Auto-generated
transcripts contain sufficient errors in technical vocabulary, proper nouns,
and low-frequency terms to reduce rather than increase ranking confidence for
those specific terms. Auto-generated transcripts are acceptable as a fallback;
they are not equivalent to a reviewed transcript for discoverability purposes.

---

## Discoverability and Retention Metrics

### Metric Hierarchy

| Metric | Type | Signal |
|---|---|---|
| Completion rate | Leading | Episode-level content quality; identifies structural drop-off |
| Listen-through rate | Leading | Show-level retention; identifies concept and format durability |
| Subscribe rate (per episode) | Leading | Episode's conversion of new listeners to returning listeners |
| Downloads per episode (30-day) | Lagging | Audience size benchmark; not a content quality signal |
| Average downloads per episode (trailing 90 days) | Lagging | Show growth trajectory |

Completion rate and listen-through rate are the operative metrics for production
decisions. A high download count with a low completion rate indicates a strong
distribution or title mechanic that is not matched by episode content — the
show is acquiring curiosity, not building retention. A low download count with
a high completion rate indicates a show that retains the audience it reaches but
has not yet scaled distribution. The correct intervention for each case is
different; treating both cases with more promotion is incorrect for the first
and appropriate only for the second.

### Drop-Off Diagnosis

When completion rate drops below 50% on a specific episode, locate the timestamp
where the drop-off concentration is highest in the platform analytics. Map that
timestamp to the episode structure. Common structural causes: body segment that
lacks a retention anchor, a transition between topics that was not bridged for
the listener, a call to action placed mid-episode that signals the episode is
effectively over, or a guest or solo section that shifted to an abstraction level
the target audience cannot track. Address the structural cause before re-
evaluating the topic selection.

---

## Monetisation Discipline

### Monetisation Path Selection

| Path | When it works | Editorial-independence risk |
|---|---|---|
| Direct sponsorship (host-read) | Show has 5,000+ consistent downloads per episode; host uses the product | High if frequency exceeds one sponsor per episode segment |
| Platform ad-network | Show is below direct sponsorship threshold; prioritises revenue over ad relevance | Medium; ad content is not host-controlled |
| Membership / subscription | Show has demonstrated listener loyalty (>40% listen-through rate over 90 days); exclusive content is genuinely differentiated | Low if membership content is additive; high if core content is withheld |

Select the monetisation path that matches the show's current audience metrics.
Applying direct sponsorship mechanics before a show has demonstrated the audience
volume that makes sponsorships commercially viable to a potential partner produces
rejection and signals inexperience to the market.

### Editorial-Independence Constraint

Sponsorship integration must not alter episode topic selection, guest selection,
or the claims made about the sponsor's category in non-sponsored episodes. The
test: if the show's editorial team could not cover the sponsor's category
critically in a non-sponsored episode without creating an implicit conflict, the
sponsorship arrangement compromises editorial independence. Compromised editorial
independence is detectable by long-term listeners before it is acknowledged
internally; it is the primary driver of podcast audience attrition from shows
that reach the growth phase and then plateau.

A sponsor who requires approval rights over episode content, topic selection, or
guest selection is requesting editorial control, not sponsorship placement. That
arrangement is not a sponsorship — it is a content production contract and must
be disclosed accordingly.

---

## Anti-Patterns

| Anti-pattern | Description | Correction |
|---|---|---|
| Host-first concept | Show positioned around the host's identity, credentials, or knowledge domain rather than an audience tension | Reframe the concept around the specific unresolved tension the target audience carries; the host is the delivery mechanism, not the product |
| Bad audio tolerance | Publishing episodes with noise floors above -55 dBFS, loudness outside target range, or audible compression artifacts | Apply the production standard as a hard gate before scheduling; never publish a file that has not passed the loudness and noise-floor check |
| Irregular cadence | Varying publishing schedule based on production readiness rather than a fixed release window | Batch-record and maintain a minimum two-episode inventory buffer so that publishing cadence is decoupled from recording availability |
| Sponsorship overload | More than two sponsor integrations per episode, or host-read ads for products the host has no direct experience with | Limit to one integration per episode segment; decline sponsorships for products that cannot be represented through genuine first-person experience |
| Stacked calls to action | Multiple simultaneous calls to action in a single outro (subscribe, review, follow, sign up, visit) | One call to action per episode; sequence additional actions across consecutive episodes |
| Guest ambush | Asking a guest an unbrieved question on a topic that carries reputational or professional risk | Cover all territory in the pre-recording brief; no undisclosed topic areas during recording |

---

## Cross-References

- `domains/marketing-global/skills/content-creator` — anchor content authoring,
  repurposing matrix design, narrative architecture. Route when the task is
  written derivative production from podcast episodes rather than podcast
  production itself.
- `domains/marketing-global/skills/social-media-strategist` — distribution
  strategy for episode clips, quote cards, and short-form derivatives across
  social platforms. Route when the task is channel-specific social distribution
  of podcast-derived assets.
- `domains/marketing-global/skills/video-optimization-specialist` — short-form
  video production and platform-specific optimization for episode clips published
  to YouTube Shorts, Reels, or TikTok. Route when the task is video-format
  repurposing of audio content.

---

## ADR Anchors

- **ADR-058** (Brainstorm gate pre-Plan + two-pass adversarial review): the
  brainstorm gate discipline maps directly to this skill's show concept
  architecture gates. Before a show concept enters production commitment, the
  audience segment, angle-decay test, and noise-floor pre-check serve as the
  podcast equivalent of ADR-058's spec artifact. The two-pass adversarial review
  pattern applies to episode outlines: the first pass evaluates structural
  completeness (cold open, hook, retention anchors, single call to action); the
  second pass reads specifically for guest-ambush risk, editorial-independence
  conflicts, and monetisation-integrity violations.
