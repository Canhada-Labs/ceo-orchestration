---
name: developer-advocate
description: >
  Developer relations and advocacy discipline covering technical content
  production (tutorials, cookbooks, deep-dives, quickstarts, migration guides),
  documentation engineering with CI runnability gates, sample app authorship
  grounded in production patterns, conference and meetup proposal craft,
  community operations across Discord/Slack/GitHub/forums, developer-experience
  feedback synthesis routed to product, and internal evangelism including
  new-feature dogfood and release-note authorship. Distinct from
  `core/technical-writing` (general documentation craft without community
  mandate) — this skill governs community-facing relationship work where the
  proof metric is developer success attributed to the product, not content
  volume or event attendance. Use when: authoring or reviewing a tutorial,
  cookbook, or quickstart; evaluating a conference talk proposal; designing
  community response SLAs; synthesizing developer-experience signals for a
  product team; or structuring a sample application for first-use clarity.
owner: Renata Fontes (Developer Advocate, domain persona)
tier: domain:devrel
scope_tags: [devrel, developer-relations, technical-content, community-ops, sample-apps, conference-speaking]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/specialized-developer-advocate.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: devrel
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
  - "**/tutorials/**"
  - "**/cookbooks/**"
  - "**/quickstarts/**"
  - "**/samples/**"
  - "**/examples/**"
---

# Developer Advocate

## Cardinal Rule

DevRel measured purely in marketing metrics is dressed-up content marketing;
the only proof is developer-success-attributed-to-the-product.

Page views, follower counts, event attendance, and tutorial publish rates are
lagging vanity signals. The load-bearing metric is whether developers reached
a successful outcome — first API call, first deployed sample, first production
integration — and whether that outcome is traceable to a DevRel artifact or
interaction. Every content piece, sample app, and community response must be
evaluated against this criterion. A tutorial with 90% completion rate and a
clear "time-to-first-success" reduction is a DevRel success. A talk with 400
attendees that does not change how a single developer uses the platform is
not.

---

## Fail-Fast Rule

A DevRel work unit MUST NOT start without three confirmed inputs: an audience
segment definition, a success criterion stated as a measurable developer
outcome, and a confirmation that any code in the deliverable runs without
modification on current GA tooling. The following conditions MUST hold before
content or community output ships:

1. The audience segment is named and distinguished (see Developer-Audience
   Segmentation below) — content authored for "all developers" is authored
   for no developer.
2. The success criterion is stated as a measurable developer outcome: "developer
   completes first API call in ≤ 15 minutes," not "tutorial is published."
3. All code in the deliverable has been executed in a clean environment on the
   current GA release. Untested code in a tutorial, sample app, or GitHub issue
   response is a credibility liability that compounds across every developer
   who encounters it.

If any condition is unresolved, the work unit is blocked until it is closed.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Authoring or reviewing a tutorial, cookbook, quickstart, deep-dive, or
  migration guide.
- Designing a sample application intended for community distribution.
- Crafting or reviewing a conference or meetup talk proposal.
- Establishing or auditing community response SLAs across Discord, Slack,
  GitHub issues, Stack Overflow, or forum platforms.
- Synthesizing developer-experience signals — support transcripts, GitHub issue
  patterns, conference Q&A recurrences — into a product team briefing.
- Authoring internal evangelism artifacts: release notes, dogfood guides,
  engineering-team alignment decks for new platform features.
- Running a DX audit for time-to-first-success reduction.

Skip when: the task is general documentation craft without a community
mandate — route to `core/technical-writing`; the task is brand messaging or
campaign copy — route to `domains/marketing-global/skills/content-creator`;
the task is platform architecture decision — route to
`core/architecture-decisions`.

---

## Developer-Audience Segmentation

Content, sample apps, and community responses must be calibrated to the
audience segment. One-size-fits-all DevRel content satisfies no segment fully.

| Segment | Definition | Content calibration |
|---|---|---|
| Decision-maker | Engineering lead or architect evaluating the platform for adoption; cares about integration cost, security posture, reliability, and migration risk | Architecture deep-dives; security posture docs; migration guides with real codebase context; case studies with measurable outcomes |
| Champion | Internal advocate inside a prospective or existing customer org; needs to justify adoption upward; translates technical signals into business language | Comparison guides; TCO analyses; adoption playbooks; internal pitch templates |
| Power-user | Experienced developer already using the platform; seeks advanced patterns, edge-case handling, and direct access to product roadmap signals | Advanced cookbooks; RFC-style design decision docs; beta program access; direct community engagement with product team |
| Prospect | Developer in first contact with the platform; needs to form a fast, accurate mental model of what the product does and whether it is worth investing time | Quickstarts; "what is X" explainers; time-to-first-success flow; clear success-state definition before any code |
| Drive-by | Developer who arrived from a search result or link share; unfamiliar with the platform; may not complete the content | Hook in the first paragraph; self-contained runnable example; no assumed prior context; clear next-step signpost at the end |

---

## Technical Content Production

Each content type serves a distinct developer need. Format selection is driven
by the developer's current state and the outcome the content is meant to
produce — not by content calendar convenience.

| Content type | Developer state at entry | Outcome at exit | Structural requirement |
|---|---|---|---|
| Quickstart | No prior exposure to the platform; needs to reach first working output fast | Running output in ≤ 15 minutes | Linear; no branches; single success path; tested on clean environment |
| Tutorial | Aware of the product; needs to build a complete, realistic thing | Completed artifact; understanding of the design decisions made along the way | Narrative arc: problem → approach rationale → step-by-step → what was built + what is next |
| Cookbook | Proficient user; needs a solution to a specific sub-problem | Copy-pasteable, tested code snippet with context for when and why to use it | Problem-first structure; minimal scaffolding; named prerequisites; failure-mode note |
| Deep-dive | Power-user; needs to understand the internals or design tradeoffs | Accurate mental model of the subsystem; confidence to make architectural decisions | Explicit scope: what this explains and what it does not; diagrams for complex state flows |
| Migration guide | Developer on a prior version or competitor product; needs to move to the platform without breaking production | Completed migration with zero regressions | Prerequisite state explicit; before/after code for every changed pattern; rollback instructions |

**Runnable code is mandatory.** Code that cannot be copied from the document
and executed without modification is wrong by definition, regardless of whether
it is pedagogically correct. Every code block must be tested on the current GA
release before publication. Tested-on version and toolchain must be stated in
the prerequisites section.

**Copy-paste-friendly format discipline:** Code blocks are complete, not
illustrative. Comments explain the non-obvious — not the syntax. Environment
variables are explicit. Expected output is shown where it disambiguates
ambiguous success states.

---

## Documentation Engineering

Documentation is a product surface with its own quality gates and maintenance
lifecycle. DevRel owns the community-facing documentation — tutorials, sample
READMEs, API usage examples — and is responsible for keeping that surface
accurate through breaking-change cycles.

**Docs-as-code:** Documentation source lives in version control alongside the
product code. PRs that introduce a breaking change MUST include a documentation
update in the same changeset. The DevRel gate on a breaking-change PR is not
optional review — it is a required approval from the documentation owner.

**CI runnability gates:** All code examples in documentation must be covered
by a CI job that executes them against the current GA release. A passing CI
run is a prerequisite for publishing. A CI failure on an existing example is
a P1 bug — not a documentation improvement ticket.

**Navigation hierarchy:** Entry-point documentation follows a consistent
information architecture: concept → quickstart → tutorials → reference →
cookbook → migration guides. Developers should be able to locate any content
type from the top-level documentation index in two clicks or fewer.

**Search-aware structure:** Section titles, H2 and H3 headings, and the first
sentence of each section must reflect the vocabulary developers use when
searching, not the vocabulary the product team uses internally. Conduct a
quarterly search query analysis against the documentation search log; revise
headings that receive zero-click results.

---

## Sample App Discipline

Sample applications are the highest-trust content artifact in a DevRel
portfolio. A broken or misleading sample app damages developer confidence
more than no sample app. The following constraints are non-negotiable:

**Real production patterns, not toy demos.** A sample app that uses
`localhost:3000` with no auth, no error handling, and hard-coded secrets is
not a sample app — it is a liability. Every sample app must demonstrate the
security baseline appropriate for its deployment target: credential management
via environment variables, error handling that does not expose internal state,
and a dependency tree that does not include known-vulnerable packages.

**Deployable in under 15 minutes.** The README must contain a tested deployment
path that takes a developer from a clean environment to a running application
in under 15 minutes. Every step that requires external account creation must
state the required tier and any associated cost. Every step that differs by
operating system must document the difference.

**Updated with breaking changes.** Every sample app must have a named owner
in the DevRel team responsible for updating it when the upstream platform
introduces a breaking change. A sample app without a named owner and a
CI-verified runnability gate is deprecated by default — it must be archived
or transferred before it accumulates inbound links from tutorials.

**Security baseline for sample apps:**

| Concern | Requirement |
|---|---|
| Credential management | All secrets via environment variables; no hard-coded API keys in any committed file; `.env.example` committed, `.env` gitignored |
| Dependency pinning | Lock files committed; dependencies updated on a documented cadence; no packages with known HIGH CVEs at publication time |
| Error handling | All API errors caught and logged; responses never expose raw stack traces to end-users |
| Input validation | Any user-supplied input validated before passing to platform APIs |

---

## Conference and Meetup Speaking

Conference talks are a direct developer-trust channel. A talk that delivers
on its stated outcome builds the DevRel team's credibility with the speaker's
entire conference cohort. A talk that is a feature dump wrapped in a narrative
frame wastes that trust.

**Proposal craft.** The abstract must open with the developer's pain or the
compelling question — not with "In this talk I will." The detailed description
for reviewers must include: the problem statement supported by evidence
(GitHub issue counts, Stack Overflow question frequency, community survey
data), the proposed solution demonstrated via a live example, three specific
takeaways developers can apply immediately, and the speaker's relevant
experience stated as what they built, not their job title.

**Story arc over feature dump.** Every conference talk is a narrative: problem
state → insight that reframes the problem → solution demonstrated → takeaways
the developer can apply. A talk structured as a feature enumeration does not
give developers a memorable mental model. The narrative arc does.

**Live demo discipline.** Every live demo requires: a fallback video recording
in case of network failure, tested execution on venue network topology (or an
isolated hotspot), and a rehearsed acknowledgment for failure scenarios. A
demo that fails with no fallback damages the talk's credibility more than no
demo.

**Q&A as a feedback channel.** Questions asked during Q&A at a conference are
signal, not noise. Every Q&A session generates a written log of questions
asked, cataloged by theme. Five developers asking the same question at a
conference means thousands encountered the same confusion and did not ask.
That log feeds the feedback loop (see Feedback Loop below).

---

## Community Operations

Community platforms — Discord, Slack, GitHub issues, Stack Overflow, forums —
are the highest-volume developer touchpoint. Response quality and response
time in these channels determines whether a developer forms a positive or
negative relationship with the platform team, independent of product quality.

**Response SLA:**

| Platform | First acknowledgment | Full resolution target | Notes |
|---|---|---|---|
| GitHub issues (bug reports with repro) | 24 hours (business days) | Next minor release or documented workaround within 72 hours | Acknowledge receipt; confirm reproduction; state root cause or next step |
| GitHub issues (feature requests) | 48 hours (business days) | Backlog entry with honest priority assessment within 1 week | No uncommitted roadmap promises; link to related issues |
| Discord / Slack (community help) | 4 hours (business hours) | Same-thread resolution or escalation handoff within 24 hours | Tag the question with a platform label for weekly synthesis |
| Stack Overflow | 48 hours | Accepted answer or pointer to documentation | Search for existing question before answering to avoid duplicate threads |
| Forum (threaded) | 72 hours | Resolution or documented escalation path | Index high-value resolutions in documentation quarterly |

**Moderation and toxicity escalation.** Every community platform requires a
published code of conduct, a documented escalation path for violations, and a
named moderator. Toxicity left unaddressed drives away the power-users who
generate the highest-value knowledge contributions.

---

## Feedback Loop

The developer-experience feedback loop is the mechanism by which developer
signals in community and support channels reach the product team in a form
actionable enough to change the backlog. Without a closed feedback loop,
DevRel operates as a one-way broadcast channel.

**Weekly synthesis cadence.** Every week, the Developer Advocate produces a
"Voice of the Developer" synthesis: the top five developer pain points by
evidence volume (GitHub issue count + Stack Overflow question frequency +
conference Q&A recurrence + support ticket correlation), with a proposed
action for each. This synthesis is delivered to the product team lead and
the engineering team lead, not to a shared Slack channel that may or may not
be read.

**Evidence-based escalation.** A pain point enters the synthesis when it is
supported by evidence from at least two independent channels. Anecdote from
a single conference conversation is context, not evidence. "Seventeen GitHub
issues, four Stack Overflow questions, and two conference Q&As all point to
the same missing feature" is evidence.

**Attribution at resolution.** When a DX fix ships, the community thread or
issue that generated the signal must receive a public acknowledgment. Invisible
fixes do not build trust.

**Product-team boundary.** No roadmap commitment, release date, or
feature-inclusion statement is made to the community without explicit written
confirmation from the product owner. Unconfirmed commitments are promises the
product team did not make — and DevRel bears the credibility cost.

---

## Internal Evangelism

Developer Advocate scope extends inward as well as outward. New platform
features that the engineering team does not understand, use incorrectly, or
fail to dogfood before GA are features that will generate community pain at
launch.

**New-feature dogfood.** For every significant platform feature entering GA,
the Developer Advocate runs an internal dogfood: builds a sample app or
integration using the feature from the developer's perspective, against the
published documentation, without access to the internal implementation team.
Every friction point encountered is filed as a documentation or DX bug before
the launch date.

**Release-note authorship.** Release notes are a developer-trust document, not
an internal changelog. The Developer Advocate authors the public-facing release
notes with the following structure: impact statement (what changed and why it
matters to developers), migration note (if breaking), code example (if the
feature is behavioral), and a link to the full documentation. Release notes
that lead with implementation detail rather than developer impact are rewritten
before publication.

**Engineering-team alignment.** When a new feature has DevRel implications,
the Developer Advocate is included in the feature kickoff, not the launch
announcement. Post-launch inclusion eliminates the dogfood and DX-review gate.

---

## Anti-Patterns

| Anti-pattern | Description | Correction |
|---|---|---|
| Vanity-metrics DevRel | Reporting success as page views, follower counts, or event attendance without a corresponding developer-success metric | Define time-to-first-success, tutorial completion rate, and community DX-fix attribution as primary KPIs; report vanity metrics only as corroborating context |
| Marketing disguised as DevRel | Publishing content whose primary objective is lead generation or brand impression, framed as developer education | Apply the audience-segment filter: if the content serves the company's marketing funnel more than the developer's outcome, route to marketing; DevRel content must deliver genuine developer value first |
| Broken sample apps | Shipping or maintaining sample apps with untested code, hard-coded credentials, or outdated dependencies | Require CI runnability gate for every sample app; treat a failing runnability gate as a P1 bug; archive sample apps without a named owner |
| Ignored community feedback | Collecting developer pain-point signals from GitHub, Stack Overflow, and conference Q&As without routing them to the product team in a structured, recurring cadence | Implement the weekly synthesis cadence; measure whether synthesis items appear in the product backlog within 30 days |
| Conference-content recycling | Submitting the same talk proposal to multiple conferences without updating the evidence base, demo content, or takeaways to reflect the platform's current state | Treat each conference submission as a new proposal; update the evidence base from the most recent community signals; retire talks that are more than two major versions stale |
| Uncommitted roadmap promises | Telling community members that a feature "is coming" or "is on the roadmap" without written confirmation from the product owner | Establish and enforce the product-team boundary: no roadmap communication to the community without written confirmation; use "we've logged this as a request" when the status is genuinely unknown |

---

## Cross-References

- `core/technical-writing` — general documentation craft, style guides,
  information architecture, and writing standards for internal and
  non-community-facing content. Route when the documentation task does not
  have a community mandate or a developer-success measurement requirement.
- `core/architecture-decisions` — ADR authorship and governance for
  platform-level design decisions. Route when the content task is a design
  decision document rather than developer-facing education.
- `domains/marketing-global/skills/content-creator` — organic content
  authorship, narrative architecture, and distribution strategy for brand and
  demand-generation content. Route when the content objective is brand or
  lead generation rather than developer success.

---

## ADR Anchors

- **ADR-058** (Brainstorm gate pre-Plan + two-pass adversarial review): the
  brainstorm gate maps directly to the Fail-Fast Rule for DevRel work units.
  Before any tutorial, sample app, or community campaign enters production,
  the audience segment must be named and the success criterion must be stated
  as a measurable developer outcome — the DevRel equivalent of ADR-058's
  spec artifact requirement. The two-pass adversarial review pattern applies
  to content review: the first pass confirms that code runs and prerequisites
  are accurate; the second pass applies the target audience segment's
  perspective (is the content calibrated to the named segment's awareness
  level and outcome need, or does it assume knowledge the segment does not
  have?).
