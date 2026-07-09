---
name: executive-summary
description: |
  Executive summary authoring discipline covering Pyramid Principle
  (Minto SCQ), one-page architecture, decision-enabling structure,
  audience-aware compression, and the never-bury-bad-news rule. Applies
  answer-first sequencing, cognitive-economy writing, and named-owner
  recommendation framing to all outputs. Distinct from
  `domains/sales/skills/proposal-strategist` (persuasion-to-close
  focus) and `domains/business-support/skills/analytics-reporter`
  (data-narrative focus). Use when: converting a lengthy analysis or
  briefing into a board-ready one-page summary; structuring a decision
  memo for C-suite consumption; compressing a multi-team status report
  for executive review; or authoring a risk or incident summary that
  must be readable in under three minutes.
owner: Camille Renard (Executive Summary Specialist, domain persona)
tier: domain:business-support
scope_tags: [executive-summary, pyramid-principle, decision-support, one-page-summary, audience-compression]
inspired_by:
  - source: msitarzewski/agency-agents/support/support-executive-summary-generator.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
  - source: affaan-m/ecc/skills/competitive-report-structure@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: business-support
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
  - "**/memos/**"
  - "**/briefs/**"
  - "**/summaries/**"
source: affaan-m/ecc@81af4076 skills/competitive-report-structure/
license: MIT
---

# Executive Summary

## Cardinal Rule

An executive summary that requires the reader to read the supporting
document is not a summary; the summary IS the deliverable. Every output
produced under this skill must be independently interpretable — context,
decision, recommendation, and risk communicated completely within the
one-page boundary, without reference to appendices or source material
for the reader to reach a conclusion. All outputs are subject to the
two-pass review gate (ADR-058).

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- No decision or action is identified; the requester cannot articulate
  what a reader must decide or do after reading.
- The source material contains unresolved contradictions in key figures
  or scope that would require the reader to adjudicate ambiguity.
- The audience tier is unspecified and cannot be inferred from context,
  making compression level undefined.
- The one-page ceiling would be breached even with maximum compression,
  and no secondary format (two-page exception) has been authorised.
- Risk or bad-news content is present in the source but the requester
  has instructed that it be omitted or minimised.

Never produce a summary over an unresolved factual contradiction. Never
omit material risk at requester direction.

## When to Apply

Apply when: converting a detailed analysis, audit, or status report into
a board-ready one-page summary; drafting a decision memo for a C-suite
reader; compressing a multi-team update for executive review; authoring
a risk, incident, or post-mortem summary; or preparing investor-facing
business updates.

Do not apply to proposal documents with commercial intent (route to
`domains/sales/skills/proposal-strategist`), data-narrative reports
with exploratory findings (route to
`domains/business-support/skills/analytics-reporter`), or financial
board packs with multi-quarter P&L content (route to
`domains/finance-accounting/skills/financial-analyst`).

## Pyramid Principle

The Minto Situation-Complication-Question-Answer (SCQ) structure governs
all outputs. The answer appears first, not last. The supporting argument
exists to defend a conclusion already stated, not to build toward one.

**Situation:** the stable, agreed-upon context the reader already
accepts. No new information; no controversy. One to two sentences.

**Complication:** the change, problem, or tension that makes the
situation unstable and demands action. This is where urgency lives.

**Question:** the implicit question the complication raises in the
reader's mind — what should we do? — stated explicitly only when the
audience needs orientation.

**Answer:** the thesis — the recommendation, decision, or conclusion —
stated in the opening sentence of the summary body. Every subsequent
paragraph defends or contextualises the answer; nothing contradicts it.

Inverted-pyramid sequencing applies to every H2 section within the
summary: the most important sentence is always first. Readers who stop
after the first sentence of any section must still have understood the
section's core contribution.

## One-Page Architecture

The one-page ceiling is a hard constraint, not a guideline. Exceeding
it signals that prioritisation has failed, not that the content is
unusually complex.

Standard quadrant layout for a decision memo:

| Quadrant | Content | Word budget |
|---|---|---|
| Decision required | One-sentence statement of what must be decided and by when | 20–30 |
| Context | SCQ Situation + Complication in compressed form | 50–75 |
| Options and recommendation | 2–3 options with a named preferred option; rationale in one sentence per option | 80–120 |
| Risks and next step | Top 2 risks to the recommendation; single named next action with owner and date | 50–75 |

Total target: 200–300 words. Hard ceiling: 350 words. Visual hierarchy:
decision required at top; risks and next step at bottom. No footnotes,
no appendix references, no jargon glossaries within the one-page body.

## Decision-Enabling Structure

A summary without a decision is a report. The decision-enabling
structure enforces six elements in every output:

1. **Decision required** — the specific choice the reader must make,
   framed as an action verb plus object: "Approve the Q3 budget
   reallocation", not "Regarding the budget".
2. **Context** — the minimum background needed to evaluate the decision;
   no more.
3. **Options** — two to four mutually exclusive paths; do-nothing is
   always an explicit option and is never tacitly assumed.
4. **Recommendation** — the preferred option, named explicitly, with a
   one-sentence rationale grounded in the decision criteria.
5. **Risks** — the top two risks to the recommended option, quantified
   or bounded where possible.
6. **Next step** — one concrete action, one named owner, one date.

Missing any element constitutes an incomplete output. "Further
analysis required" is not a recommendation; "the team will review" is
not a next step.

## Audience-Aware Compression

Compression depth is calibrated to audience tier:

**CEO / founder (60-second skim):** decision statement + recommendation
+ single risk + next step only. No options table. No supporting
rationale unless the decision is reversible. Maximum 150 words.

**Board / investor (5-minute read):** full decision-enabling structure
with options. Quantified risks. Named owners. Maximum 300 words. No
jargon unexplained within the text.

**Functional leader (10-minute detail):** decision-enabling structure
plus a three-to-five-row findings table. May include a secondary
supporting section (methodology note or data provenance). Maximum 400
words, two-page exception permitted with prior authorisation.

Audience tier must be identified before drafting begins. When the
summary will circulate across multiple tiers, calibrate to the most
senior reader; functional-leader detail belongs in an appendix, not
the summary body.

## Never-Bury-Bad-News

Material risk, negative findings, and adverse outcomes appear in the
opening of the relevant section — never at the end, never in a
footnote, never softened by framing the positive first. The sequence
"here are our wins, and by the way, we have a problem" is prohibited.

Bad news that is structurally minimised erodes trust faster than the
bad news itself. Executives who discover buried risk after the fact
lose confidence in subsequent summaries from the same author. Trust
rebuilt after a concealment event costs more than trust maintained by
transparent disclosure in the first instance.

If the summary's recommendation carries a risk that makes a reasonable
reader question whether the recommendation is sound, that risk is
stated prominently, not buried. The role of this skill is to enable
informed decisions, not to construct a persuasive case for a
predetermined outcome.

## Cognitive-Economy Discipline

Every word in the summary must earn its place against the decision.

- **Quantify over qualify:** "revenue declined 18% QoQ to $4.2M" is
  admissible; "revenue was significantly lower" is not.
- **Concrete over abstract:** "the migration deadline is 30 June" is
  admissible; "the timeline is tight" is not.
- **Noun over adjective:** "a $1.2M cost overrun" is admissible; "a
  major cost overrun" is not.
- **Active voice:** "the CFO must approve by 15 May" is admissible;
  "approval is required" obscures ownership and is not admissible.
- **Jargon gate:** technical terminology is permitted only when the
  named audience tier is confirmed expert. When audience expertise is
  mixed, the plain-language equivalent is used.

Filler phrases ("it is important to note", "in order to", "as mentioned
above") are struck on the first pass. The two-pass review gate (ADR-058)
enforces this.

## Recommendation Discipline

A recommendation must be actionable, named, and dated. The three
criteria are jointly necessary; any one missing renders the item a
suggestion, not a recommendation.

- **Actionable:** the reader can execute it without further
  interpretation. "Reduce headcount in the logistics function by 12%
  through attrition over two quarters" is actionable. "Consider
  headcount optimisation" is not.
- **Named owner:** a specific role or individual, not a team or
  department. "CFO" is a named owner. "Finance" is not.
- **Dated:** a specific calendar date or bounded period. "By 30 June"
  is dated. "In the near term" is not.

Where multiple recommendations appear, they are ranked by urgency and
impact. Labelling conventions: Critical (blocks a decision or legal
obligation), High (material impact within 30 days), Medium (material
impact within 90 days). No more than one Critical item per summary; if
more than one Critical item exists, the summary scope is too broad.

## Decision-Grade Reporting

When the summary sits atop a structured analysis — a competitive study, a
benchmark, a technical audit, or a multi-option evaluation — the one-page
mechanics above still hold, and four additional disciplines keep the summary
driving a decision rather than documenting the work. (The underlying analysis is
typically produced under `domains/business-support/skills/analytics-reporter`;
this skill compresses its findings into the decision.)

1. **Decision-first, methodology last.** Open with the three-to-five findings
   that change what the reader does — where the subject is strong, where it is
   exposed, and the top two-to-three moves — written so a reader who reads only
   the summary knows what to do. How the analysis was run (weights, rubrics,
   sample, scope) belongs in an appendix, never the opening. Where a single
   visual resolves the decision faster than a paragraph, lead with it, within
   the one-page ceiling.
2. **Asserted vs. proven.** Every load-bearing claim carries its provenance: is
   it *proven* (measured, sourced, independently verifiable) or *asserted*
   (inference, single source, estimate)? A one-line verification note per major
   claim, with the sources behind it in the appendix, is what makes the summary
   auditable and defensible. A decision made on an asserted claim dressed as a
   proven one is the failure this discipline exists to prevent — it is the
   provenance complement to the Cognitive-Economy quantify-over-qualify rule.
3. **No false composite.** When findings span multiple dimensions — cost, risk,
   capability, time — do not collapse them into one blended score or a single
   status dot. Averaging distinct dimensions hides the asymmetry the decision
   turns on: an option that is cheap-but-slow and one that is fast-but-costly can
   average to the same number while demanding opposite decisions. Report the
   dimensions separately and state plainly where the subject leads and where it
   trails.
4. **Close on forcing-questions.** If the summary feeds a decision or alignment
   meeting, end with the specific questions that force a choice — which option,
   which risk to accept, which gap to close versus concede — not a recap. A close
   that invites admiration of the analysis ("as the data shows...") wastes the
   meeting; a close that names the pending decision runs it.

## Anti-patterns

| Anti-pattern | Symptom | Correction |
|---|---|---|
| Thesis-buried | Recommendation appears in the final paragraph after extensive context | Move recommendation to first sentence; restructure as SCQ |
| Jargon-soup | Three or more unexplained acronyms or domain terms in the opening paragraph | Apply jargon gate; expand or replace with plain-language equivalent |
| No-recommendation | Summary ends with "the team will continue to monitor" or equivalent | Identify and state the specific decision and recommended option |
| Vanity-data | Metrics included that do not bear on the decision (e.g., team headcount in a budget summary) | Remove; every metric must trace to a decision criterion |
| Hidden-bad-news | Risk or adverse finding appears after positive findings or in a footnote | Lead with risk in its section; promote from footnote to body |
| Scope-creep | Summary exceeds 350 words or covers more than one primary decision | Scope to one decision; move secondary decisions to separate summaries |
| Methodology-first | Summary opens by explaining how the analysis was run before stating what it found | Move the top findings to the opening sentence; methodology to the appendix |
| False-composite | Multi-dimensional findings collapsed into one blended score or status dot that hides asymmetry | Report the dimensions separately; name where the subject leads and where it trails |
| Analysis-admiration | Summary closes by recapping the work instead of forcing the pending decision | End with the specific choice the reader must make; forcing-questions, not a recap |

## Cross-References

Related skills within this framework:

- `domains/business-support/skills/analytics-reporter` — data-narrative
  reports and exploratory findings that feed the summary-authoring
  context.
- `domains/sales/skills/proposal-strategist` — persuasion-to-close
  documents where the primary goal is commercial commitment rather
  than decision enablement.
- `domains/finance-accounting/skills/financial-analyst` — board-pack
  financial content and variance analysis that may be compressed into
  an executive summary under this skill.

## ADR Anchors

- **ADR-058** — two-pass review gate; applies to all outputs produced
  under this skill. First pass: content completeness and decision
  structure. Second pass: cognitive-economy and jargon gate.

## Changelog

- **PLAN-153 Wave G (SP-039, 2026-07-09):** decision-grade reporting discipline folded in (clean-room ADAPT; provenance in frontmatter/NOTICE).
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=0e69d05f23abb6b12b1b9c2fc94d402a8feb04e21d17ea6101d0d18344ba31aa
