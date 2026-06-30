---
name: tiktok-strategist
description: >
  TikTok platform strategy discipline covering algorithm-aware content framing,
  hook-first scripting, watch-time optimization, trend velocity capture, and
  monetisation discipline. Applies For You Page signal mechanics, retention
  curve diagnostics, and trend half-life analysis to produce content plans
  grounded in completion-rate data rather than reach assumptions. Use when:
  designing a TikTok content calendar, diagnosing low completion rates,
  evaluating trend fit versus brand coherence, scripting hook structures for
  short-form video, setting posting-cadence policy by audience timezone, or
  calibrating the original-versus-trend content ratio for a given account stage.
owner: Valentina Cruz (TikTok Strategist, domain persona)
tier: domain:marketing-global
scope_tags: [tiktok, short-video, algorithm-strategy, watch-time, hook-craft, trend-velocity]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-tiktok-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/tiktok/**"
---

# TikTok Strategist

## Cardinal Rule

Watch-time completion is the primary ranking signal on TikTok; reach and
follower count are outputs, not inputs. Every content decision MUST be
evaluated against its projected effect on completion rate before any
other metric is considered. A video that accumulates 50 000 views at
18% completion is algorithmically damaging; a video with 3 000 views at
85% completion seeds future distribution. Reporting impression volume
without completion-rate context is misleading and MUST NOT be presented
as a performance summary.

---

## Fail-Fast Rule

A TikTok video MUST NOT proceed to posting if the first three seconds
lack a declared hook pattern. Hooks are not optional opening lines;
they are the mechanism by which the algorithm decides whether to extend
initial distribution. Before any video is finalized, the following gates
MUST pass: (1) the opening frame contains a pattern interrupt — visual
or verbal — that creates unresolved curiosity or stated payoff; (2) the
audio hook aligns with the visual hook rather than competing with it;
(3) the promised payoff is delivered before the video ends, not in a
follow-up post or pinned comment. If any gate fails, the video requires
rescript before scheduling.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Designing or auditing a TikTok content calendar requiring algorithm-aware
  sequencing and cadence decisions.
- Diagnosing a drop in completion rate, watch-time average, or For You Page
  distribution for an active account.
- Evaluating whether a trending audio or challenge is a fit for an account's
  established content identity.
- Scripting hook architectures — opening frame, pattern interrupt, payoff
  promise — for short-form vertical video.
- Setting or revising posting-cadence policy based on audience timezone and
  platform distribution windows.
- Calibrating the original-versus-trend ratio for accounts in the growth,
  maintenance, or pivot stage.
- Advising on comment engagement strategy — pinned comment as second hook,
  reply-with-video mechanics, community loop activation.

---

## Algorithm Frame

The TikTok For You Page distributes content through successive audience
cohorts. The algorithm promotes a video to the next cohort only when the
prior cohort's engagement signals exceed internal thresholds.

**Signal density hierarchy (descending weight):**

1. Watch-time completion — percentage of video watched to end; rewatches
   multiply the contribution.
2. Engagement velocity — likes, comments, and shares accumulated in the
   first 30–60 minutes after posting.
3. Profile visits and follows triggered by the video — signals audience
   conversion intent.
4. Shares to external platforms — treated as high-intent endorsement.
5. Sound saves and effects used — platform-specific retention signals.

**Completion as primary metric:**

Target completion rate benchmarks by video length:

| Duration | Minimum viable completion | Strong signal threshold |
|----------|--------------------------|------------------------|
| 7–15 s   | 70%                      | 90%+                   |
| 16–30 s  | 55%                      | 75%+                   |
| 31–60 s  | 40%                      | 60%+                   |
| 61–120 s | 30%                      | 50%+                   |
| 2–3 min  | 20%                      | 40%+                   |

Videos below minimum viable completion for their duration bracket MUST be
treated as distribution-suppressed and excluded from performance averages
used to set future targets.

---

## Hook Architecture

The first three seconds of a TikTok video determine whether the algorithm
extends initial distribution. Hook architecture has three components that
MUST be present in every scripted video.

**3-second commit:**

The opening frame must contain a stated or implied question, conflict,
or payoff promise that creates an unresolved narrative tension. The viewer
must have a reason to stay before the context of the video is established.
Formats that satisfy this gate: a surprising claim, a visible unfinished
action, a stated number that demands explanation, or a named contradiction.

**Pattern interrupt:**

A sudden shift in visual pace, audio character, or on-screen text in the
first three seconds disrupts passive scroll behavior. Effective interrupts
include: cut-on-action into a visually distinct environment; silence
followed by sharp sound; text that contradicts the visual frame. The
interrupt must not be random — it must be semantically connected to the
payoff promise.

**Payoff-promise-proof structure:**

After the 3-second hook, the video must follow a structured arc:

- Promise: state explicitly what the viewer will receive by watching
  to the end.
- Proof: deliver the core claim with sufficient specificity to be
  verifiable — not general assertion.
- Completion reward: the final frame or line must provide a closing
  signal that does not abruptly cut, as abrupt endings lower rewatch
  probability.

---

## Watch-Time Optimization

Retention curve diagnostics are the primary feedback mechanism for
optimizing watch-time. TikTok Analytics provides a per-second audience
retention graph for each video; this graph MUST be reviewed before
any script revision is proposed.

**Retention curve interpretation:**

| Curve shape          | Diagnosis                                      | Intervention                                  |
|----------------------|------------------------------------------------|-----------------------------------------------|
| Sharp drop 0–3 s     | Hook failure                                   | Rescript opening frame entirely               |
| Gradual slope 3–15 s | Pacing too slow; insufficient mid-reveal       | Add secondary hook at 5–7 s                   |
| Cliff at midpoint    | Promised payoff felt delivered early           | Restructure proof section; delay reveal       |
| Flat then cliff end  | Content holds but no loop signal               | Add loop-friendly ending phrase or visual cue |
| Flat throughout      | Strong content; optimise for rewatch           | End on ambiguity or "part 2" hook             |

**Loop-friendly endings:**

A loop-ending video ends in a way that makes the replay feel intentional
rather than accidental. Techniques: the final frame visually echoes the
opening frame; the closing line resolves to the opening question; audio
cuts exactly to the original beat. Loop signals increase rewatch rate,
which compounds completion contribution to the algorithm.

**Mid-reveal technique:**

Splitting the primary payoff across two moments in the video — a partial
reveal at 40% and the full reveal at 80–90% — sustains retention
through the mid-section where most drop-off occurs. This requires the
script to withhold a single high-value detail until the second reveal
point.

---

## Trend Strategy

TikTok trends have a quantifiable half-life. Adopting a trend at peak
saturation produces the same algorithmic outcome as producing generic
content; the distribution gain from trend association is exhausted when
the sound or format is ubiquitous.

**Trend half-life reference table:**

| Trend type             | Peak-to-saturation window | Entry window for distribution gain |
|------------------------|--------------------------|-------------------------------------|
| Trending audio (major) | 4–10 days                | Days 1–4 post peak discovery        |
| Trending audio (niche) | 7–21 days                | Days 1–8                            |
| Visual format / meme   | 3–7 days                 | Days 1–3                            |
| Hashtag challenge      | 5–14 days                | Days 1–5                            |
| Narrative template     | 10–30 days               | Days 3–12                           |

**Original-versus-trend ratio:**

Accounts in growth phase (under 50K followers): 40% original formats,
60% trend participation. Accounts in maintenance phase (50K–500K):
60% original, 40% trend. Accounts in authority phase (500K+): 70–80%
original; trend participation reserved for trend types that align with
established content identity.

**Trend-fatigue detection:**

A trend is saturated when the following signals are observable: the
sound appears in more than three vertically distinct content categories
simultaneously; the top-performing videos on that sound are older than
the trend's expected half-life; engagement-rate averages on trend-tagged
content have dropped below category baseline by more than 15 percentage
points. At saturation, trend adoption MUST be blocked for the current
period.

---

## Posting Cadence

Posting cadence affects distribution independently of content quality
because the algorithm weights recency when initializing distribution
tests for each cohort.

**Cadence windows by audience timezone:**

For audiences concentrated in UTC−5 to UTC−3 (Americas): primary
windows are 06:00–09:00 and 19:00–22:00 local; secondary window
12:00–14:00. For audiences in UTC+0 to UTC+2 (Europe/Africa): primary
windows 07:00–10:00 and 18:00–21:00 local. For UTC+7 to UTC+9
(Asia-Pacific): primary windows 08:00–11:00 and 20:00–23:00 local.
Mixed or unknown audiences: default to UTC 12:00 for broadest initial
distribution.

**Consistency versus velocity:**

Consistent posting at lower frequency outperforms irregular high-volume
posting for accounts below 100K followers. The minimum viable cadence
for algorithmic account health is 4 posts per week. Exceeding 3 posts
per day risks intra-day distribution cannibalization: the algorithm
does not guarantee full cohort testing for multiple same-day posts from
the same account. If daily volume exceeds 3, subsequent posts MUST have
distinct content angles to avoid audience fatigue detection.

---

## Comment Engagement

Comments are a second-order distribution signal and a community
compounding mechanism. Comment strategy MUST be treated as a content
layer, not a moderation task.

**Top-pinned comment as second hook:**

The pinned comment is the first piece of creator-authored text that
viewers read after the caption. It MUST function as a second hook: pose
a question that extends the video's central tension, add a fact withheld
from the video, or invite a specific viewpoint. Generic affirmations
("thanks for watching") in the pinned comment are wasted signal surface.

**Reply-with-video:**

Responding to a high-engagement comment with a new video that directly
addresses the comment produces a content chain with pre-established
audience interest. This format MUST be applied when a comment generates
more than 30 replies or 200 likes, as it signals latent demand for
extension content.

**Community loop activation:**

Direct questions in the caption or in the mid-video CTA that invite
category-specific responses (not generic "comment below") increase
comment velocity in the first hour, which contributes to engagement
velocity scoring. Community loop questions MUST be answerable in
one to three words to reduce friction.

---

## Anti-patterns

| Anti-pattern                     | Failure mode                                                   | Correct behaviour                                              |
|----------------------------------|----------------------------------------------------------------|----------------------------------------------------------------|
| Ad-style copy as hook            | Viewer pattern-matches to ad and scrolls past within 1 s      | Use curiosity gap or conflict framing; no brand logos in frame 1 |
| Hashtag spray (15+ tags)         | No measurable reach lift; signals low-quality post metadata   | Use 3–5 targeted hashtags: 1 brand, 1–2 niche, 1 trending if fit |
| Watermarked cross-post           | TikTok algorithm suppresses CapCut/Reels watermarks in FYP    | Export without watermark; re-edit natively if repurposing      |
| Trend chase without brand fit    | Trend association costs brand coherence; follower churn rises | Apply trend-fatigue detection and fit scoring before adoption  |
| Completion sacrifice for length  | Longer video with low completion damages account distribution | Cut to minimum length that preserves the payoff structure      |
| Comment ignoring in first hour   | Engagement velocity drops; algorithm reads low creator intent | Monitor and reply to first 10 comments within 30 min of post  |
| Posting during off-peak windows  | Initial cohort too small; video never enters growth loop      | Adhere to timezone-calibrated posting windows                  |
| Caption as transcript excerpt    | Captions read as duplicate content; no additional hook value  | Caption must add information absent from the video itself      |

---

## Cross-References

- `domains/marketing-global/skills/instagram-curator` — Reels overlap,
  cross-platform adaptation protocol, visual identity consistency across
  short-video formats.
- `domains/marketing-global/skills/social-media-strategist` — Multi-platform
  content calendar coordination, audience segmentation across channels,
  platform-specific tone calibration.
- `domains/marketing-global/skills/content-creator` — Long-form to
  short-form repurposing strategy, narrative structure for video content,
  editorial calendar integration.

---

## ADR Anchors

- **ADR-058** — Creative authorship and structural-inspiration licensing
  policy; governs `inspired_by` attribution requirements for domain skill
  files derived from upstream open-source agent corpora.
