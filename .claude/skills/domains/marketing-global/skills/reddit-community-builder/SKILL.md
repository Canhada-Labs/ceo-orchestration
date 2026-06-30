---
name: reddit-community-builder
description: Reddit community participation and brand presence — subreddit-specific
  norms, mod relations, AMA discipline, value-first contribution, and anti-self-promotion
  compliance. Covers subreddit research, 9:1 contribution ratio, karma-threshold
  awareness, downvote-brigade triage, and per-sub flair governance. Use when planning
  a brand's Reddit entry, authoring posts or comments for community contribution,
  coordinating an AMA, managing a mod relationship, or triaging a downvote event.
owner: Reddit Community Builder (domain persona)
tier: domain:marketing-global
scope_tags: [reddit, subreddit-norms, ama-protocol, mod-relations, value-first, anti-self-promo]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-reddit-community-builder.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/reddit/**"
  - "**/ama/**"
---

# Reddit Community Builder

## Cardinal Rule

If a brand's only function on a subreddit is promoting its own product,
the community has identified the account before the second post lands.
Every contribution must provide value that stands on its own merits,
independent of any affiliation with the brand.

## Fail-Fast Rule

Stop community activity and escalate to strategy review when any of
the following conditions hold:

- A post is removed by moderators within 24 hours of submission for
  violating subreddit rules — the subreddit's norms were insufficiently
  researched before the post was made.
- The account's post-to-comment ratio exceeds 1:3 in a given 30-day
  window — the participation pattern has shifted from contribution to
  broadcasting.
- A moderator issues a warning without a prior rule violation — the
  tone or framing of contributions is misread as promotional even when
  content is not.
- A subreddit's karma threshold requirement is not met — posting before
  building karma within the community violates the sub's implicit entry
  contract.

## When to Apply

Apply this skill when:

- Designing a brand's first-entry strategy for a target subreddit.
- Authoring posts or comments intended as community contributions.
- Coordinating an AMA session with a subject-matter expert or founder.
- Managing an existing moderator relationship or responding to a
  moderation action.
- Triaging a downvote event or hostile thread mentioning the brand.
- Selecting which subreddits to engage based on ICP fit.

Do NOT apply to paid Reddit advertising (Promoted Posts) — that belongs
to a paid-media profile. Do NOT apply to brand-crisis legal escalations
— those require a dedicated incident commander protocol.

## Subreddit Norms Frame

Before the first contribution to any subreddit:

1. Read at minimum three months of top and controversial posts, all
   pinned/sticky posts, the sidebar rules, and the wiki if present.
   This is not optional — it is the only reliable mechanism for
   detecting unstated norms that supplement the written rules.
2. Note the dominant post formats (link posts vs self-posts vs image
   ratios), average comment depth, and the flair schema. Non-compliant
   flair is a visible marker of an outsider account.
3. Identify the sub's karma threshold for posting, if enforced. Verify
   whether the threshold applies to subreddit-specific karma or
   site-wide karma — the two are not interchangeable.
4. Map the active moderators by username-pattern (not personal identity).
   Note their stated specializations, the sub's mod-message policy, and
   whether flair requests are handled via modmail or a pinned thread.
5. Identify whether the sub operates on a ban-first or warn-first
   enforcement culture by reviewing the moderation history visible in
   removed-post flairs and ban explanations in public threads.

## Contribution Discipline

Reddit's community standard is a 9:1 ratio: nine value-adding
contributions for each single piece of content that references the
brand, its product, or any URL the brand controls. Inversion of this
ratio — one value-add post followed by nine self-referential posts —
is the single most reliable signal of a promotional account and
triggers shadow restrictions or bans in well-moderated communities.

Contribution types that constitute the nine:

- Answering technical or domain questions with complete, sourced
  responses that do not reference the brand.
- Sharing third-party resources, research, or tooling that addresses
  a documented community pain point.
- Providing constructive feedback on another member's project, post,
  or proposal without unsolicited product mentions.
- Curating a summary or synthesis of community discussion that adds
  interpretive value.

Content that counts toward the one:

- Any post or comment that names the brand, links to a brand-controlled
  domain, or describes a product feature as a solution.
- Any post that invites the community to an event the brand is hosting.

The ratio is computed over rolling 30-day windows, not per-session.

## AMA Protocol

An AMA (Ask Me Anything) is the highest-leverage direct-engagement
format on Reddit and also the highest-risk. Non-compliance with the
protocol damages the brand's standing in the community more severely
than most individual post failures.

Pre-AMA requirements:

1. Select the subject-matter expert (SME) based on demonstrated domain
   depth, not organizational seniority alone. The community will detect
   a figurehead without domain knowledge within the first five questions.
2. Obtain moderator approval via modmail before scheduling. Provide the
   SME's credentials, the proposed topic scope, and the intended
   disclosure language. Do not announce the AMA publicly before mod
   confirmation.
3. Prepare a disclosure statement that identifies the SME's affiliation
   with the brand in the first sentence of the AMA post. The disclosure
   must appear before any topic framing.
4. Verify that the SME can sustain a 2-4 hour active reply window on
   the scheduled day. An AMA with a 40% question-response rate is
   perceived as worse than no AMA.

During the AMA:

- Reply within the 2-4 hour active window to all substantive questions,
  including hostile or skeptical ones.
- Do not use canned or pre-drafted answers verbatim. Verbatim reuse is
  detectable via phrasing uniformity and signals PR management rather
  than genuine participation.
- Acknowledge unanswerable questions explicitly rather than ignoring
  them. "I cannot speak to that publicly at this time" is acceptable.
  Non-response is not.

Post-AMA:

- Return within 24-48 hours to address any questions that were missed
  during the live window, prioritizing those with upvotes.
- Do not delete the AMA post after it concludes. Deletion signals
  regret and is archived by the community regardless.

## Mod Relations

Moderators control the community's enforcement environment. Adversarial
or transactional treatment of moderators compounds rule violations.

Engagement norms:

- Contact moderators via modmail, not direct message, for all
  rule-clarification or flair-request inquiries. Direct message
  bypasses the mod team's shared record.
- Flair requests must cite the specific rule or wiki entry that creates
  ambiguity — a request without a cited basis reads as entitlement.
- After a post removal, wait 24 hours before submitting a modmail
  inquiry about the removal reason. Immediate contact is read as
  pressure.

Rule-violation recovery:

- Acknowledge the violation explicitly in the modmail response. Do not
  contest the removal on procedural grounds unless the post was removed
  in clear violation of the sub's own stated rules.
- Offer a revised version of the content that addresses the stated
  removal reason. Asking for clarification without offering a correction
  extends the cycle.

Ban-appeal protocol:

- A ban appeal must be submitted to the sub's modmail, not to Reddit
  admins, unless the ban was issued by Reddit's spam or safety systems.
- Appeals that cite the account's prior positive contribution history
  are more effective than appeals that contest the specific violation.
- If a ban appeal is denied, accept the outcome. Repeated appeals are
  logged and reduce the probability of reinstatement.

## Crisis Response

Not all negative signals on Reddit represent a crisis. Distinguishing
a downvote brigade from legitimate criticism determines the response.

Downvote brigade characteristics:

- Vote velocity is disproportionate to comment engagement — hundreds
  of downvotes with few or no substantive comments.
- The downvoting pattern originates from a single thread elsewhere that
  linked to the post with hostile framing.
- The post's content addresses a topic with pre-existing community
  polarization unrelated to the brand.

Response: do not respond to the vote count. Post visibility adjustments
in well-moderated subs are handled by moderators. Responding to the
vote pattern draws attention to it.

Legitimate criticism characteristics:

- Multiple independent users raise the same substantive concern in
  separate comment threads.
- The criticism references verifiable facts about the brand's product,
  behavior, or prior statements.
- Moderators have not removed the criticism or classified it as
  brigading.

Response to legitimate criticism:

- Acknowledge the concern in a reply within the same thread within
  four hours of the first high-upvote comment raising it.
- Do not delete the original post. Deletion is archived via third-party
  services and read as admission of fault without resolution.
- The edit window for a post is effectively unlimited, but edits to
  the body of an AMA or community post must be marked as edits with a
  timestamp. Unmarked edits that alter the original meaning are treated
  as deception.

## Subreddit Selection

Subreddit selection criteria in priority order:

1. ICP alignment: the sub's dominant demographic, problem set, and
   vocabulary must overlap with the brand's target audience. A 50,000-
   member sub where 80% of posts are within the ICP problem domain
   outperforms a 2,000,000-member general sub where 2% of posts are
   relevant.
2. Moderation quality: active moderation indicates a community that
   values norms compliance. Poorly moderated subs accumulate low-quality
   content that reduces signal value of participation.
3. Karma threshold feasibility: verify whether the threshold can be
   reached organically within the planned engagement timeline without
   fabricated participation.
4. Growth trajectory: a sub growing at 5% monthly provides more
   first-mover advantage than a mature sub with stable membership and
   entrenched established accounts.

Reject subs where the top posts by upvote count are consistently
self-promotional, where the moderator team has not been active in
the past 30 days, or where the sub's stated purpose conflicts with
the brand's disclosure obligations.

## Anti-patterns

| Anti-pattern | Description | Consequence |
|---|---|---|
| Corporate voice | Formal prose, passive constructions, brand-speak in comments | Identified as promotional account; downvoted on detection |
| Link spam | Posting brand URLs in multiple threads within a 7-day window without establishing prior comment presence | Automatic spam filter trigger; permanent shadow restriction in many subs |
| Fake-question seeding | Creating or coordinating posts that appear to be genuine user questions but are designed to introduce the brand as the answer | Permanent ban on detection; community broadcast of the violation |
| Engagement farming | Posting polls, "hot takes," or controversy-baiting threads designed to generate comment volume rather than inform | Post removed; reputational damage disproportionate to upvote gain |
| Unsolicited DM outreach | Contacting subreddit members via private message after they post in a relevant thread | Violation of Reddit anti-spam policy; reported to site admins |
| Paid-mod abuse | Offering or providing consideration to moderators in exchange for preferential treatment of posts or removal of negative content | Platform-level violation; ban of associated accounts |
| Delete-and-repost | Removing a post after downvote or criticism and reposting it to reset the vote count | Community detects the pattern; subsequent posts treated with preemptive hostility |

## Cross-References

- `domains/marketing-global/skills/twitter-engager` — channel-specific
  engagement norms for short-form text platforms; apply when presence
  spans both Reddit and X/Twitter.
- `domains/marketing-global/skills/content-creator` — long-form content
  strategy and editorial discipline; apply when Reddit participation
  drives traffic to owned content assets.
- `domains/marketing-global/skills/social-media-strategist` — cross-
  channel orchestration and brand voice governance; apply when Reddit
  is one channel within a multi-platform presence.

## ADR Anchors

- **ADR-058** — creative-rewrite drop policy for domain skill authoring;
  this skill is authored under the structural-inspiration relationship
  and does not reproduce upstream prose.
