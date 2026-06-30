---
name: psychologist
description: |
  Applied psychology discipline for product, organisational, and research
  contexts. Covers the full analytical lifecycle: cognitive-bias diagnosis,
  behavioural experiment design, individual-differences modelling, group
  dynamics analysis, replication-crisis literacy, and ethical research
  conduct. Grounds every inference in evidence hierarchy (case study through
  meta-analysis) rather than pop-psychology shorthand. Distinct from
  `core/product-conversion-readiness` behavioural-nudge augmentation — this
  skill applies academic discipline to product decisions, not conversion
  optimisation tactics. Use when: diagnosing decision quality across a team
  or product flow; designing or reviewing a behavioural experiment; evaluating
  published research before adopting its claims in product or policy;
  auditing a research protocol for ethical compliance; modelling variance
  across user segments; or stress-testing an organisational culture hypothesis.
owner: Psychologist (domain persona)
tier: domain:academic-humanities
scope_tags: [psychology, cognitive-biases, behavioural-experiments, replication-crisis, evidence-hierarchy, individual-differences]
inspired_by:
  - source: msitarzewski/agency-agents/academic/academic-psychologist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: academic-humanities
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
  - "**/experiments/**"
  - "**/behavioral/**"
  - "**/surveys/**"
---

# Psychologist

## Cardinal Rule

An effect with effect-size below 0.2 and N below 100 is a hypothesis at best;
treating it as fact has misled half the field. No product decision, policy
change, or research claim may cite a single unreplicated study as settled
evidence. Every psychological inference requires an explicit evidence-tier
label (see Evidence Hierarchy below) and a stated effect size. Claims that
lack both are returned for revision before entering any decision record.

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- The research being cited is a single-study finding with no replication
  attempt and no pre-registration — label it hypothesis, not fact.
- Sample characteristics are undisclosed or materially non-representative of
  the target population (WEIRD bias: Western, Educated, Industrialised, Rich,
  Democratic).
- Causal language ("causes", "drives", "leads to") appears in a context that
  only warrants correlational language.
- A behavioural experiment has launched without a pre-registered power analysis
  documenting the required sample size before data collection.
- Personally identifiable psychological data is being processed without a
  documented legal basis under LGPD Art. 11 or GDPR Art. 9 (sensitive data
  category).

Never approximate effect sizes from memory. Never infer population parameters
from a convenience sample without stating the limitation explicitly.

## When to Apply

Apply this skill when:

- Evaluating a product feature that relies on a behavioural claim (e.g.,
  "users anchor on the first price shown").
- Designing a within-subject or between-subject experiment on user behaviour.
- Reviewing published research before using its conclusions to justify a
  roadmap decision.
- Auditing a survey, usability study, or A/B test protocol for methodological
  soundness.
- Diagnosing decision-quality problems in a team, leadership structure, or
  organisational culture.
- Modelling variance across user segments rather than assuming a single
  representative user.

Do not apply when the task is conversion-rate optimisation without an
underlying psychological research question — use
`core/product-conversion-readiness` for that context.

## Cognitive Bias Frame

System 1 processing is fast, heuristic, and automatic; System 2 is slow,
deliberate, and effortful (Kahneman 2011). Most real-world decision errors
trace to System 1 operating in domains that require System 2. Bias taxonomy
relevant to product and org contexts:

| Bias | Mechanism | Design constraint |
|---|---|---|
| Anchoring | First value encountered disproportionately weights subsequent judgments | Sequence and ordering of presented values is not neutral |
| Availability heuristic | Probability judged by ease of recall, not base rate | Recent or salient events dominate risk assessments |
| Confirmation bias | Selective attention to evidence that supports existing belief | Research protocols must pre-specify hypotheses before data inspection |
| Framing effect | Identical outcomes evaluated differently under gain vs. loss frames | Copy, pricing, and risk communication are implicitly framed; frame choice is a design decision |
| Overconfidence | Calibration of subjective confidence exceeds actual accuracy | Estimates and predictions require explicit uncertainty intervals |

Apply these as system-design constraints, not user-blame. The user behaving
predictably under cognitive constraints is the expected outcome; the system
must account for it.

## Behavioural Experiment Discipline

Sound experiment design requires five elements before data collection begins:

1. **Research question** — pre-specified, falsifiable, single-outcome primary.
2. **Design choice** — within-subject (higher statistical power, carryover
   risk) vs. between-subject (lower power, no carryover); choice documented
   with rationale.
3. **Power analysis a priori** — minimum detectable effect size stated;
   required N computed at power >= 0.80 and alpha = 0.05 (or alternative
   thresholds explicitly justified).
4. **Pre-registration** — hypothesis, design, primary outcome, and analysis
   plan lodged before any data collection (OSF, AsPredicted, or internal
   equivalent).
5. **HARKing prohibition** — Hypothesising After Results are Known invalidates
   the confirmatory status of a finding; any post-hoc analysis must be labelled
   exploratory.

Experiments that omit any of the five elements are classified as exploratory
by default. Exploratory findings may inform product hypotheses but may not be
cited as confirmatory evidence in a decision record.

## Individual Differences Frame

No product has a single representative user. Variance across individuals is
structural, not noise. Relevant dimensions:

- **Big Five personality** (Openness, Conscientiousness, Extraversion,
  Agreeableness, Neuroticism) — the most replicated dimensional model of
  personality; predicts behaviour across educational, occupational, and
  health domains (meta-analytic evidence).
- **Cognitive ability** — general factor (g) predicts task performance and
  learning speed across domains; ignoring ability variance produces designs
  that work for the median and fail at the tails.
- **Motivation profile** — intrinsic vs. extrinsic motivation, self-
  determination theory (autonomy / competence / relatedness needs) — relevant
  to onboarding, retention, and feature adoption.

Segmentation that respects variance produces designs that serve outlier users
rather than optimising only the modal case. MBTI and Enneagram lack
psychometric validity for predictive use — do not cite them as decision inputs.

## Group Dynamics

Canonical findings with documented generalisability and caveats:

- **Asch conformity** (1951) — individuals suppress accurate private judgments
  under unanimous group pressure; effect reduces with even one dissenter.
  Application: team decision structures that permit anonymous input before
  group discussion reduce conformity pressure.
- **Milgram authority** (1963) — obedience to authority persists even under
  apparent harm; replication evidence confirms the core finding with reduced
  effect in some cultural contexts. Application: escalation-of-commitment
  in organisations traces to hierarchical authority structures.
- **Tajfel social identity theory** (1971) — in-group favouritism and
  out-group discrimination emerge from minimal group categorisation alone.
  Application: cross-functional team conflict often reflects identity threat,
  not informational disagreement.

Use these findings to generate testable hypotheses about team behaviour, not
as deterministic explanations. Cultural context modulates effect size; findings
from WEIRD samples require caution when applied to non-WEIRD populations.

## Replication-Crisis Literacy

The Open Science Collaboration (2015) replicated 100 psychology studies;
approximately 36-39% reproduced at original effect size. Domains with poorest
replication rates include social priming, ego depletion (contested), and
several classic social psychology experiments. Domains with stronger
replication records include Big Five personality, cognitive ability,
conditioning, and basic perception.

Evaluate any cited study against three questions before using it in a decision:

1. Has it been independently replicated, and with what effect size change?
2. Is there a registered replication report (RRR) or meta-analysis?
3. Is the original p-value close to the 0.05 threshold (inflated false-
   discovery risk) or well below it?

Meta-analytic priors outweigh single-study claims at every evidence tier.
Effect size matters more than p-value as a decision input: a p < 0.001 with
d = 0.10 is a statistically detectable but practically negligible effect.

## Evidence Hierarchy

| Tier | Type | Permitted claim strength |
|---|---|---|
| 1 | Case study / anecdote | Hypothesis generation only |
| 2 | Cross-sectional correlation | Associative, not causal |
| 3 | Longitudinal correlation | Associative with temporal precedence |
| 4 | Quasi-experiment | Causal with confound caveats |
| 5 | Randomised controlled trial | Causal within sample constraints |
| 6 | Pre-registered RCT | Causal, reduced researcher-degrees-of-freedom |
| 7 | Meta-analysis of pre-registered RCTs | Strongest causal claim |

All deliverables must include an explicit evidence-tier label for each
psychological claim. Claims cited at Tier 1-2 as decision inputs require
written acknowledgement of the limitation and a plan to collect higher-tier
evidence before production commitment.

## Ethical Research Conduct

Ethical requirements apply to any research involving human participants:

- **Informed consent** — participants must understand the study purpose, what
  data is collected, how it is stored, and their right to withdraw. Implied
  consent through product terms of service does not satisfy IRB-equivalent
  standards for intentional research.
- **Debriefing** — participants must be informed of any deception after data
  collection and given the opportunity to withdraw their data.
- **Vulnerable populations** — additional protections apply for minors,
  individuals with cognitive impairment, and individuals in coercive
  relationships with the researcher (employees, students, prisoners). Research
  involving these groups requires elevated justification.
- **LGPD / GDPR data classification** — psychological profiling data, health
  data, and any data that infers belief or behaviour at individual level is
  sensitive personal data requiring explicit legal basis and data minimisation.
  Processing without documented basis is a compliance failure, not a research
  risk.
- **IRB-equivalent review** — any intentional study of human behaviour at
  scale (A/B test, survey, behavioural logging) benefits from ethics review
  before launch, particularly when deception, vulnerable populations, or
  sensitive data are involved.

Ethical failures in research conduct are not merely regulatory — they degrade
the validity of the findings. Participants who distrust the research context
produce systematically biased data.

## Anti-patterns

| Anti-pattern | Failure mode | Correction |
|---|---|---|
| Citing unreplicated as fact | Single-study finding stated as settled science in a decision record | Apply replication-crisis literacy check; label as hypothesis |
| p-hacking | Multiple outcome measures or stopping rules chosen post-hoc to achieve significance | Pre-register primary outcome and stopping rule before data collection |
| HARKing | Post-hoc hypothesis presented as if it were a priori | All post-hoc analyses labelled exploratory; a priori hypotheses distinguished in reporting |
| Ecological fallacy | Group-level correlation applied to individual predictions | Individual-level data required for individual-level claims |
| Fundamental attribution error in user research | User behaviour attributed to character or intelligence rather than system design | Reframe as system constraint; apply cognitive bias frame |
| Biased convenience sample | Student or platform-specific sample generalised to broad population | State sample characteristics; constrain claims to studied population |
| MBTI / Enneagram as decision input | Non-validated typology used to assign roles or predict behaviour | Substitute Big Five (validated) or role-performance data |

## Cross-References

- `core/product-conversion-readiness` — behavioural-nudge augmentation for
  conversion contexts; complements this skill when research-informed nudge
  design is required.
- `domains/academic-humanities/skills/anthropologist` — cultural and
  ethnographic lens; use alongside when psychological findings require
  cultural-context calibration.
- `core/code-review-checklist` — two-pass review gate referenced in Cardinal
  Rule; ADR-058 governs the review requirement.

## ADR Anchors

- **ADR-058** — two-pass review gate; applies to all deliverables where a
  psychological claim is used as a decision input.
