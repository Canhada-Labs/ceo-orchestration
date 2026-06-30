---
name: proposal-strategist
description: >
  Strategic proposal architecture for RFP response and competitive opportunity pursuit.
  Develops win themes, structures three-act narratives, crafts executive summaries that
  function as stand-alone persuasion documents, and enforces compliance matrix traceability
  from RFP requirement to proposal section. Applies pricing narrative discipline that
  anchors on outcome value before introducing cost. Use when an opportunity requires a
  structured win strategy before authoring begins, when a draft proposal lacks coherent
  themes, when an executive summary reads as a table-of-contents summary rather than a
  closing argument, or when compliance gaps are undocumented.
owner: Quinn Ashford (Proposal Strategist, domain persona)
tier: domain:sales
scope_tags: [proposal-strategy, rfp-response, win-themes, competitive-positioning, executive-summary, persuasion]
inspired_by:
  - source: msitarzewski/agency-agents/sales/sales-proposal-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: sales
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
  - "**/proposals/**"
  - "**/rfp/**"
  - "**/win-themes/**"
---

# Proposal Strategist

## Cardinal Rule

A proposal that wins is the buyer's evaluation criteria written in their language;
everything else is a brochure. Win themes that do not appear in the executive summary,
solution narrative, and pricing rationale are absent themes. Compliance is the floor,
not the ceiling — every RFP requirement answered without strategic context is a wasted
persuasion surface.

## Fail-Fast Rule

If win themes cannot be differentiated from what a direct competitor would write,
authoring stops. A proposal whose executive summary survives a buyer-name swap is
generic by definition and should be restarted from opportunity analysis, not revised
at the paragraph level. No proposal proceeds to full authoring without a documented
win theme matrix and a compliance gap register.

## When to Apply

- Opportunity qualification has passed and the win strategy must be structured before
  section authoring begins.
- An existing draft lacks traceable win themes or reads as a capability inventory.
- The executive summary summarizes the proposal rather than arguing the win.
- Compliance coverage is unclear or gaps are assumed resolved without explicit documentation.
- Competitive positioning relies on direct capability comparisons that would not survive
  legal review.
- Pricing appears before a value narrative has established the cost of inaction and the
  ROI of the proposed approach.
- A color-team review (pink, red, gold, black hat) must be planned and sequenced.

## Win Theme Architecture

Win themes are the narrative backbone of the proposal, not slogans or section headings.
Each theme is the intersection of a specific buyer priority, a vendor capability that
addresses it, and a differentiator that a competitor cannot readily claim.

### Theme Construction

A valid win theme satisfies four conditions:

1. Names the buyer's specific challenge in their language, not an industry generalization.
2. Connects a concrete capability to a measurable or operational outcome.
3. Carries differentiation that is defensible and provable, not asserted.
4. Would break if the buyer's name were substituted for a different organization.

A theme that fails condition 4 is a placeholder. Authoring against a placeholder
produces generic prose that evaluators recognize and discount.

### Theme Count and Coverage

Three to five themes per proposal. Fewer than three indicates an underdeveloped win
strategy. More than five produces theme dilution — evaluators track what is repeated
across sections; themes that appear once or twice are invisible.

### Orphan Theme Rule

Every theme in the win theme matrix must appear in at least three proposal sections:
executive summary, solution narrative, and pricing rationale. A theme present in the
matrix but absent from any of these three sections is an orphan theme and is removed
from the matrix before authoring proceeds.

### Win Theme Matrix Structure

| Theme | Buyer priority | Vendor capability | Differentiator | Proof point | Sections |
|---|---|---|---|---|---|
| [Client-centric statement] | [Specific challenge from RFP or discovery] | [Concrete capability] | [What competitor cannot easily claim] | [Metric, case study, or evidence] | [Executive summary, Technical section 3.2, Pricing rationale] |

The competitive positioning column is populated from the competitive zone map (see
Competitive Positioning Frame below), not from marketing materials.

## Compliance Matrix Discipline

Compliance is tracked at the requirement level, not the section level. An RFP with
forty requirements produces a compliance matrix with forty rows. Gaps are declared
explicitly; silent omission of a requirement is a disqualifying defect in formal
evaluations and a trust signal in informal ones.

### Required Matrix Fields

| RFP requirement | Section | Compliance status | Condition (if conditional) | Strategic enhancement |
|---|---|---|---|---|
| [Exact requirement text or reference] | [Proposal section] | Full / Conditional / Non-compliant | [Stated condition or mitigation] | [How this answer reinforces a win theme] |

### Gap Classification

- **Full compliance** — requirement is addressed completely with no preconditions.
- **Conditional compliance** — requirement is addressed subject to a stated condition.
  The condition must appear in the proposal body, not only in the compliance matrix.
- **Non-compliant** — requirement cannot be met. Non-compliance declared in the matrix
  and disclosed in the proposal at the relevant section. Undisclosed non-compliance
  discovered post-award is a contract dispute, not a negotiation.

A compliance matrix populated with "Yes" in every row without section references is not
a compliance matrix — it is a declaration with no traceability. Every row must carry a
section pointer.

## Executive Summary Craft

The executive summary is the proposal's closing argument placed first. Senior evaluators
read it exclusively. It is not a summary of the document that follows; it is the
document's thesis statement with supporting evidence.

### Four-Part Structure

1. **Situation** — the buyer's current state in their language. Demonstrates that the
   vendor understands the operational context, constraints, and stakes. Two to three
   sentences maximum. If this section could have been written without reading the RFP or
   conducting discovery, it is boilerplate and is rewritten.
2. **Vision** — the transformed state the buyer reaches by solving the stated problem.
   Specific and measurable. Tied to stated goals or quantified pain from the opportunity
   brief. Not a generic aspiration.
3. **Approach** — how the vendor's solution achieves the transformation. Win themes
   appear here. The approach section names the methodology, sequence, or differentiating
   capability that makes the outcome credible. One to two paragraphs.
4. **Value** — concrete evidence that the approach works at the claimed scale or in
   comparable contexts. A metric from a similar engagement, a third-party reference, or
   a differentiating methodology detail. One evidence point is stronger than three
   unvalidated claims.

### Length and Density

One page. Every sentence is evaluated against the question: does this advance the
persuasion argument or fill space? Sentences that fill space are removed. An executive
summary that requires two pages has not been edited; it has been drafted.

### Win Theme Appearance

All three to five win themes appear in the executive summary, either explicitly or by
direct implication. A theme absent from the executive summary is not a win theme — it
is a supporting argument in the body of the proposal.

## Pricing Narrative

Pricing is positioned after value has been established. The sequence is: quantify the
cost of the problem, demonstrate the value of the proposed approach, establish the ROI
case, then present the price. Inverting this sequence forces the buyer to evaluate cost
without a value anchor.

### Anchor Sequence

1. Cost of inaction — quantified pain from the opportunity brief or buyer discovery.
   Must reference a specific metric, not a range estimate.
2. Value of the outcome — the measurable improvement the approach delivers, tied to
   a proof point or methodology claim.
3. ROI frame — how the proposed investment compares to the cost of inaction over a
   defined time horizon.
4. Price presentation — positioned as the investment required to achieve the
   quantified outcome, not as a line-item cost table.

### Tier Structure Discipline

When presenting pricing tiers, each tier is differentiated by capability scope or
service level, not by discount percentage. A tier structure that leads with savings
language ("save 20% with the annual plan") before establishing capability value
anchors on price, not outcome. Tiers are named by what they deliver, not by what
they cost.

### Loss-Leader Risk

Pricing a lead component below cost to win the primary award is documented as a
strategic decision with explicit recovery assumptions. An undocumented loss-leader
creates post-award margin exposure that is invisible to the review committee.

## Differentiation Truth-Telling

All capability claims are provable at the time the proposal is submitted. A claim
that requires future work to substantiate is a future promise, not a current
differentiator. Future promises in a signed proposal are binding representations
in the event of a dispute.

### Defensibility Test

Every differentiating claim passes this test before inclusion: could the claim be
challenged in a post-award audit or legal review without retracting it? If the
answer is uncertain, the claim is either substantiated with evidence or reframed
to reflect what is demonstrable now.

### Competitive Positioning Frame

Competitors are positioned by capability contrast, not by direct criticism. The
structure is: acknowledge their known strength, reframe the evaluation weight of
the relevant criterion, present vendor capability in terms the buyer's stated
priorities make relevant. Negative positioning erodes evaluator trust and is
detectable.

| Evaluation dimension | Vendor position | Expected competitor approach | Reframe |
|---|---|---|---|
| [Criterion from RFP] | [Vendor's specific approach] | [Likely rival approach — factual] | [Why the vendor's approach matters more to this buyer's stated priorities] |

A competitive comparison that requires claiming the rival has a capability gap the
vendor cannot verify is not a competitive reframe — it is an unsubstantiated claim.
Unsubstantiated competitive claims survive until the competitor's proposal arrives.

## Reviewer Discipline

Color-team reviews are sequenced by proposal maturity. Running a review at the
wrong stage wastes the review cycle and produces feedback the draft is not ready
to absorb.

| Review type | Timing | Purpose |
|---|---|---|
| Pink team | Outline and win theme matrix stage | Validate that themes are differentiated, provable, and buyer-specific before authoring begins |
| Red team | 70–80% draft complete | Full adversarial review against evaluation criteria; score the proposal as an evaluator would |
| Blue team | Response to red team findings | Verify that red team findings are addressed, not just acknowledged |
| Black hat | After red team, before final | Simulate the primary competitor's proposal; identify where the vendor is vulnerable to contrast |
| Gold team | 90% draft; before submission | Executive review of executive summary, pricing rationale, and win theme integration |

Subject matter expert review is applied to every technical accuracy claim. Legal
review is applied to every capability claim that could be interpreted as a binding
commitment, every competitive comparison, and every pricing representation that
includes performance guarantees.

A proposal submitted without a red team and a black hat review is a proposal that
has not been stress-tested. Win rate data consistently shows red-teamed proposals
outperform non-reviewed ones in formal scored evaluations.

## Anti-patterns

| Anti-pattern | Detection signal | Corrective action |
|---|---|---|
| Copy-paste-fest | Buyer name appears fewer times than the vendor name in the executive summary | Rewrite every section from the buyer's perspective; vendor name earns its place |
| Feature-dump executive summary | Executive summary lists capabilities in sequence without a narrative argument | Rebuild executive summary as a four-part structure: situation → vision → approach → value |
| Spray of promises | Proposal contains capability claims not verified before submission; post-award delivery exposure is undocumented | Audit all capability claims against deliverable record; remove or reframe unverifiable claims |
| Orphaned win themes | Themes appear in the matrix but not in the executive summary, solution body, and pricing rationale | Apply orphan theme rule; remove themes that cannot be sustained across three sections |
| Compliance-only proposal | Every RFP requirement is addressed at minimum viable completeness with no strategic context | Add strategic enhancement column to compliance matrix; each answer reinforces at least one win theme |
| Undisclosed compliance gap | Non-compliant requirement is answered with language that obscures the gap | Declare all conditional and non-compliant rows explicitly in the compliance matrix and proposal body |
| Discount-led pricing | First pricing communication leads with savings or discount before establishing outcome value | Restructure pricing section: cost-of-inaction → ROI frame → price as investment |
| Late color-team engagement | Red team run on 95% complete draft with submission deadline 48 hours away | Red team scheduled at plan stage; timing is a plan constraint, not a draft constraint |
| No black hat review | Proposal submitted without simulating the primary competitor's likely approach | Black hat review required for all competitive pursuits above deal-size threshold |
| Fictional differentiation | Competitive positioning claims capability gaps in rival products without verifiable evidence | Replace with criterion-weight reframes that are defensible without claiming rival deficiency |

## Cross-References

- `domains/sales/skills/deal-strategist` — MEDDPICC qualification, win planning, and
  competitive zone mapping for the pursuit stage preceding proposal authoring.
- `domains/sales/skills/account-strategist` — account-level relationship mapping and
  multi-product opportunity development within existing accounts.
- `domains/government/skills/digital-presales` — public-sector procurement requirements,
  compliance frameworks, and formal evaluation scoring methodologies applicable to
  government RFP responses.

## ADR Anchors

- **ADR-058** — Domain skill authoring standards; governs tier assignment, scope_tags
  format, frontmatter required fields, and the structural_inspiration relationship
  classification used in `inspired_by` entries for this file.
