---
name: advanced-evaluation
description: >
  Production-grade patterns for LLM-as-judge evaluation systems, covering approach
  selection (direct scoring, pairwise comparison, reference-based, G-Eval, and
  Constitutional), systematic bias mitigation (position swap-symmetry, verbosity
  length-control, self-enhancement separation, order randomization), calibration
  against human ground truth with inter-rater agreement thresholds, rubric design
  with falsifiable criteria, statistical discipline for sample sizing and
  confidence intervals, and automated pipeline architecture with drift detection.
  Use when: building automated quality assessment pipelines, comparing model
  outputs at scale, validating fine-tune regressions, establishing score baselines
  before A/B prompt tests, auditing evaluation systems for systematic bias, or
  designing inter-rater calibration protocols.
rewritten_at: 2026-05-07
rewrite_reason: voice_consistency
inspired_by:
  - source: sickn33/antigravity-awesome-skills/advanced-evaluation.md@6003dc1acfedea34fa9051c408eb2fb508e08426
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: community
priority: 8
risk_class: low
stack: []
context_budget_tokens: 600
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
  - "**/evals/**"
  - "**/evaluation/**"
  - "**/judges/**"
  - "**/rubrics/**"
---

# Advanced Evaluation

## Cardinal Rule

Every judge MUST be calibrated against human ground truth before deployment. An
uncalibrated judge measures configuration noise and model-to-model preference rather
than task-relevant quality. Calibration is not optional hardening — it is the
definitional prerequisite that distinguishes an evaluation system from a scoring
simulator. No judge scores from an uncalibrated system may be used to drive model
selection, fine-tune decisions, or production gating.

---

## Fail-Fast Rules

These conditions MUST trigger immediate halt. Do not attempt evaluation output when
any rule below fires.

1. **No rubric, no evaluation.** A criterion without defined score levels and
   falsifiable pass/fail boundaries produces uninterpretable variance. Reject and
   request rubric completion before invoking any judge.

2. **Calibration gap detected.** If the judge-vs-human agreement metric (Cohen's
   kappa or Krippendorff's alpha) falls below 0.60 on the calibration set, the
   judge is unfit for the task. Stop, diagnose bias class, revise rubric or judge
   prompt, recalibrate.

3. **Judge-equals-generator for self-enhancement-sensitive criteria.** When the
   model under test is the same model instance as the judge, and the criterion is
   subjective (tone, style, persuasiveness, clarity), self-enhancement bias
   invalidates the result. Halt and substitute a distinct judge model.

4. **Sample size below power floor.** Evaluation conclusions drawn from fewer than
   30 samples per condition lack the statistical power to distinguish signal from
   noise (α=0.05, β=0.20, medium effect size). Report as indicative-only with
   explicit sample-size warning; never use as a gating decision.

5. **Single-pass pairwise used without swap.** A pairwise result produced by one
   ordering of responses is corrupted by position bias (Zheng et al., 2023,
   NeurIPS). Discard and re-run with swap-symmetry protocol.

6. **Criteria conflation.** A rubric criterion that measures two or more distinct
   properties (e.g. "accuracy and clarity") MUST be split before scoring. Combined
   criteria produce uninterpretable inter-criterion disagreements.

7. **Downstream action gated on low-confidence verdict.** Any verdict with
   judge-reported confidence below 0.60 or inter-pass inconsistency MUST be
   escalated to human review rather than used as an automated gate.

---

## When to Apply

Activate this skill when the task requires systematic, repeatable quality measurement
of LLM outputs. Concrete activation conditions:

- Constructing an automated evaluation pipeline for an LLM-powered product feature
- Comparing candidate models or prompt variants before production deployment
- Establishing a regression baseline prior to fine-tuning so drift is detectable
- Auditing an existing evaluation system for known bias patterns
- Designing or reviewing rubrics for human annotation campaigns
- Determining whether automated scores correlate with human judgments at acceptable
  levels before replacing manual review
- Implementing an A/B test where the outcome variable is output quality rather than
  a binary behavioral signal

Skip when: the evaluation task requires domain-specific expert knowledge that no
general-purpose LLM can reliably simulate (medical diagnosis, legal precedent,
actuarial judgment), the output being evaluated is code behavior rather than text
quality (use test execution instead), or the corpus is fewer than 15 samples
(descriptive statistics only, no inferential claims).

---

## LLM-as-Judge Approach Selection

| Approach | Primary Use Case | Calibration Requirement | Known Biases | Output Type |
|---|---|---|---|---|
| **Direct Scoring** | Objective criteria with ground truth (factual accuracy, format compliance, instruction following) | Inter-rater kappa ≥ 0.65 on 30+ items | Scale-drift, level-boundary ambiguity | Scalar + justification |
| **Pairwise Comparison** | Preference-based quality (tone, style, persuasiveness, helpfulness) | Position-consistency rate ≥ 0.80 | Position bias, verbosity bias, self-enhancement | Winner + confidence |
| **Reference-Based** | Summarization, translation, grounded generation where a gold reference exists | ROUGE/BERTScore correlation with human ≥ 0.70 | Reference-over-fit, paraphrase blindness | Similarity scalar |
| **G-Eval** (Liu et al., 2023, EMNLP) | Multi-dimensional NLG quality (fluency, coherence, consistency, relevance) | Per-dimension human correlation ≥ 0.65 | Fluency conflation with factuality | Weighted composite |
| **Constitutional** (Bai et al., 2022, Anthropic) | Safety and alignment; iterative critique-revision cycles | Human preference match ≥ 75% on adversarial set | Principle ordering effects, self-critique leniency | Pass/Fail per principle |

**Selection heuristic:**
- Ground truth available → Direct Scoring or Reference-Based
- No ground truth; preference-sensitive → Pairwise Comparison with swap-symmetry
- Multi-dimensional NLG (fluency, coherence, consistency, relevance) → G-Eval
- Safety/alignment gating → Constitutional with adversarial calibration set

---

## Bias Mitigation Discipline

### Position Bias

**Mechanism:** In pairwise evaluation, LLM judges assign higher win rates to
responses appearing in the first position, independent of content quality. Wang et
al. (2023, arXiv 2305.17926) measured first-position preference rates of 58-72%
across judge models tested.

**Mitigation — swap-symmetry protocol:**
1. Pass 1: Response A in position 1, Response B in position 2. Record verdict
   and confidence.
2. Pass 2: Response B in position 1, Response A in position 2. Record verdict
   and confidence. Map the result back to original labels.
3. Consistency check: If Pass 1 and Pass 2 agree (same winner after label mapping),
   accept verdict with averaged confidence.
4. If passes disagree: return TIE, set confidence = 0.50, flag for human review.

### Verbosity Bias

**Mechanism:** Judges preferentially score longer responses higher regardless of
marginal quality contribution. Longer responses signal apparent effort and
thoroughness, conflating length with correctness.

**Mitigation:**
- Embed explicit length-neutrality instruction in judge prompt: "Response length is
  not a quality signal. Evaluate only the accuracy, relevance, and clarity of the
  content, not its extent."
- For direct scoring: add a separate "conciseness" criterion rather than letting
  length bleed into other dimensions.
- For production judges: monitor score-vs-length correlation in calibration set;
  a Pearson r > 0.25 is evidence of uncorrected verbosity bias.

### Self-Enhancement Bias

**Mechanism:** A model rates its own outputs higher than outputs from other
generators, even when human judges rate the outputs equivalently. This is a
structural conflict of interest, not a prompt-engineering problem.

**Mitigation:**
- MUST use a distinct model for judge and generator when the criterion is subjective.
- When using the same model family (e.g., Opus 4 judging Opus 4 output), document
  the limitation explicitly in the evaluation report and treat scores as lower-bound
  estimates of relative quality.
- For cross-model benchmarks, use a model from a different provider as judge (e.g.,
  GPT-4o judging Claude output, or vice versa).

### Order Bias in Multi-Criterion Scoring

**Mechanism:** Criteria listed first in a rubric anchor subsequent scores. A
response that scores poorly on Criterion 1 receives systematically lower scores on
later criteria regardless of their independence.

**Mitigation:**
- Randomize criterion order across evaluation runs when criteria are independent.
- For sequential criteria (e.g., step 1 must pass for step 2 to be meaningful),
  use staged scoring with explicit dependency declaration in the rubric.

---

## Calibration Against Human Ground Truth

### Minimum Protocol

1. **Construct calibration set:** minimum 30 items (n≥50 recommended for
   multi-class criteria), stratified across quality levels to prevent ceiling/floor
   effects.
2. **Annotator pool:** minimum 3 independent human annotators per item. Resolve
   disagreements via majority vote; flag items with zero majority for adjudication.
3. **Compute agreement:** use Cohen's kappa (κ) for two-annotator or categorical
   settings; Krippendorff's alpha (α) for ordinal scales or panels of three or more.
4. **Thresholds:**
   - κ or α ≥ 0.80: Strong agreement — judge is fit for automated gating
   - κ or α 0.60–0.79: Moderate agreement — fit for advisory scoring; not gating
   - κ or α < 0.60: Insufficient agreement — judge is unfit; halt deployment

### Calibration Failure Diagnosis

When calibration falls below threshold, diagnose before retrying:

| Failure Pattern | Likely Cause | Remediation |
|---|---|---|
| Low agreement on all criteria | Rubric boundary ambiguity | Rewrite level descriptions with anchoring examples |
| Low agreement on one criterion only | Criterion conflation | Split into two independent criteria |
| High agreement on easy items, low on hard | Missing edge-case guidance | Add explicit edge-case section to rubric |
| Judge consistently high vs human | Verbosity or leniency bias | Add explicit strictness instruction + length-neutrality |
| Judge consistently low vs human | Harshness calibration error | Review scale anchors; add positive exemplars |

### Calibration Freshness

Calibration decays as task distribution shifts. Re-calibrate when:
- Prompt templates change materially
- The domain corpus shifts (e.g., new product vertical onboarded)
- Judge model version is updated
- Human annotation guidelines are revised

---

## Evaluation Pipeline Architecture

A production evaluation pipeline requires five stages executed in order. Skipping
stages or merging them produces scores that cannot be debugged when calibration
drifts.

```
Stage 1: Input Sampling
  - Stratified sample from production distribution
  - Minimum batch size: 30 per condition
  - Log sampling seed for reproducibility

Stage 2: Judge Invocation
  - Load rubric + criteria weights from versioned store
  - Apply bias mitigation (swap protocol for pairwise;
    criterion-order randomization for direct)
  - Invoke judge with chain-of-thought requirement
  - Capture raw output + token usage + latency

Stage 3: Score Aggregation
  - Parse structured output (JSON); reject malformed
  - Apply per-criterion weights to composite score
  - Flag low-confidence verdicts (< 0.60) for escalation

Stage 4: Confidence Intervals
  - Bootstrap 95% CI on mean score across batch
  - Report interval, not point estimate, in dashboards
  - Flag overlapping intervals as "inconclusive" before
    model selection decisions

Stage 5: Drift Detection
  - Compare this run's per-criterion means to rolling
    28-day baseline
  - Alert when any criterion drifts > 0.5 scale points
    (absolute) from baseline
  - Log judge-judge agreement between this run and
    previous run on shared canary set
```

### Infrastructure Invariants

- Rubrics and criteria weights MUST be versioned alongside evaluation code.
  An unversioned rubric change invalidates all historical comparisons.
- Judge prompt templates MUST be stored in version control, not in application
  configuration files or runtime environment variables.
- Every evaluation run MUST log: model name + version, rubric version, sampling
  seed, timestamp, per-item raw outputs, and aggregate statistics.
- Evaluation infrastructure MUST be logically isolated from the generation
  infrastructure it evaluates. Shared dependencies introduce confounds.

---

## Rubric Design

### Required Rubric Fields

Every rubric criterion MUST contain all five fields. An incomplete rubric is an
unvalidated rubric.

| Field | Required Content | Failure Mode if Absent |
|---|---|---|
| `criterion_name` | Short, unambiguous label (≤5 words) | Confusion when multiple criteria share semantic overlap |
| `criterion_description` | One-sentence definition of what is measured and what is excluded | Over-broad scoring; dimension conflation |
| `scale_definition` | Anchored description for every scale level (not just endpoints) | Score calibration drift across runs |
| `edge_cases` | At least two examples of ambiguous inputs with explicit guidance | High inter-rater variance on hard cases |
| `weight` | Numeric weight relative to other criteria in the rubric (sum = 1.0) | Unintended score composition when aggregating |

### Falsifiability Requirement

Every rubric criterion MUST be falsifiable: there MUST exist a response that scores
at each level. A criterion where all realistic responses score 4/5 is not a
criterion — it is noise. Validate falsifiability by running five representative
responses through the rubric manually before deployment.

### Domain Adaptation

Generic rubrics produce lower calibration than domain-adapted ones. Adapt by:
- Using domain-specific terminology in level descriptions
- Anchoring "Score 5" descriptions to exemplary domain outputs, not platitudes
- Including domain-specific failure modes in edge-case sections (e.g., for medical
  accuracy: "clinical terminology correct but dosage unstated → Score 3 not Score 5")

### Strictness Calibration

Three strictness modes; choose explicitly, document in rubric header:

- **Lenient (iteration phase):** Score 3/5 = acceptable for continued development;
  suitable for early-stage prompt iteration where overly harsh scoring discards
  viable directions.
- **Balanced (production baseline):** Score 3/5 = meets minimum bar; Score 4–5
  required for deployment gates.
- **Strict (safety-critical):** Score 4/5 = minimum acceptable; any Score 1–3
  triggers mandatory human review regardless of batching logic.

---

## Statistical Discipline

### Sample Size and Power

Minimum sample sizes for inferential claims (α=0.05, β=0.20):

| Comparison Type | Small Effect (d=0.2) | Medium Effect (d=0.5) | Large Effect (d=0.8) |
|---|---|---|---|
| Two-condition mean comparison | 394 per condition | 64 per condition | 26 per condition |
| Pairwise win-rate (H₀: 50%) | 385 total pairs | 63 total pairs | 25 total pairs |
| Pre/post with correlation | Depends on r; compute via G*Power | — | — |

For most evaluation comparisons (medium effect expected), 64+ samples per condition
is the minimum for valid inferential claims. Analyses on fewer samples MUST be
labeled "exploratory" and MUST NOT drive deployment decisions.

### Confidence Intervals

Always report 95% bootstrap confidence intervals on aggregate scores, not point
estimates alone. Bootstrap protocol:
1. Resample with replacement from the evaluation batch (B=10,000 iterations).
2. Compute the statistic (mean score, win rate) for each bootstrap sample.
3. Report the 2.5th and 97.5th percentiles as the confidence interval.

An evaluation that reports "Model A scores 0.72 vs Model B scores 0.68" without
confidence intervals is uninterpretable: the interval may span both values.

### Multiple Comparison Correction

When evaluating across k criteria simultaneously, apply Bonferroni correction
(α_adjusted = 0.05 / k) or Benjamini-Hochberg false discovery rate control
when k > 5. Failure to correct inflates false-positive finding rates in proportion
to the number of criteria tested.

### Effect Size Reporting

Statistical significance is not practical significance. ALWAYS report:
- Cohen's d for mean score comparisons
- Odds ratio or relative risk for win-rate comparisons
- Contextualize against rubric scale: a statistically significant 0.1/5.0 score
  difference is practically negligible for most deployment decisions.

---

## Production Monitoring

### Canary Set Protocol

Maintain a fixed canary set of 50+ items whose ground-truth scores are established
from calibration. Run every production evaluation batch against the canary set in
parallel. Purpose: detect judge drift before it contaminates production scores.

**Alert thresholds for canary set:**

| Metric | Warning Threshold | Critical Threshold |
|---|---|---|
| Per-criterion mean drift from baseline | > 0.25 scale points | > 0.5 scale points |
| Position-consistency rate (pairwise) | < 0.85 | < 0.75 |
| Confidence score mean | < 0.70 | < 0.60 |
| Judge-vs-human kappa on canary | Drops > 0.10 from last calibration | Drops > 0.20 |

### Judge-Judge Agreement Drift

For pipelines using multiple judge models or ensemble scoring, track pairwise
judge-judge agreement across runs. A ≥ 0.10 drop in agreement on the same
corpus is a leading indicator of prompt drift, model version change, or rubric
interpretation shift.

### Alert Response Protocol

1. **Warning threshold crossed:** log alert, continue production scoring, schedule
   rubric review within 48h.
2. **Critical threshold crossed:** halt production gating decisions, escalate to
   human review, require re-calibration before resuming automated gates.
3. **Unexplained score jump (> 1 standard deviation from rolling mean):** treat
   as data anomaly; inspect whether a judge model version update occurred, whether
   rubric was edited without version bump, or whether corpus distribution shifted.

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Practice |
|---|---|---|
| **Scoring without chain-of-thought justification** | Scores without evidence grounding cannot be debugged; reliability degradation of 15–25% reported vs CoT-first approaches | Require explicit evidence citation and reasoning BEFORE the numeric score in every judge prompt |
| **Single-pass pairwise comparison** | Position bias corrupts results; first-position win rate inflated to 58–72% across judge models (Wang et al., 2023) | Always apply swap-symmetry: two passes with inverted ordering; TIE on inconsistency |
| **Overloaded criteria (one criterion, multiple properties)** | Conflated dimensions produce uninterpretable inter-rater disagreements and incoherent score distributions | One criterion = one measurable, falsifiable property; split before scoring |
| **Deploying a judge calibrated on a different task distribution** | Calibration decays with distribution shift; a judge calibrated on factual Q&A is unreliable for creative writing tone | Re-calibrate whenever domain, prompt template, or judge model changes materially |
| **Reporting point estimates without confidence intervals** | 0.72 vs 0.68 is uninterpretable without knowing interval overlap; conflates statistical significance with practical difference | Always report 95% bootstrap CI alongside mean; flag overlapping intervals as inconclusive |
| **Using judge-equals-generator for subjective criteria** | Self-enhancement bias structurally inflates same-model scores; not correctable by prompting alone | Mandate distinct model for judge and generator when criterion is subjective; document limitation when unavoidable |
| **Underpowered evaluations driving deployment gates** | n < 30 per condition lacks power for medium effects (α=0.05); false negatives and false positives both elevated | Enforce minimum n per condition from power analysis before treating results as gateable |
| **Missing edge-case guidance in rubrics** | Annotators diverge most on ambiguous cases; variance aggregates in evaluation pipelines | Require explicit edge-case section with at least two ambiguous examples and resolution guidance |

---

## Cross-References

- `.claude/skills/core/ai-llm-orchestration/SKILL.md` — multi-model routing,
  judge model selection by task type, cost-model tradeoffs for evaluation-at-scale
- `.claude/skills/core/code-review-checklist/SKILL.md` — two-pass review protocol
  applicable to rubric design review; adversarial framing for bias detection
- `.claude/skills/domains/community/skills/agent-evaluation/SKILL.md` — evaluation
  of agentic task completion (tool-use, multi-step reasoning) as distinct from
  single-response quality assessment
- `.claude/skills/domains/community/skills/agentic-actions-auditor/SKILL.md` —
  security analysis patterns applicable to evaluation pipeline threat modeling
  (env-var injection into judge prompts; eval-of-judge-output vectors)

---

## ADR Anchors

ADRs below are verifiable at `.claude/adr/` and encode governance decisions that
constrain or shape evaluation practice in this framework.

- **ADR-058** (`ADR-058-brainstorm-gate-and-two-pass-review.md`) — Two-pass review
  mandate: every architectural decision requires an adversarial second pass. This
  applies directly to rubric design (first pass: draft criteria; second pass:
  falsifiability and bias audit) and to judge selection (first pass: approach
  selection; second pass: bias profile review).

- **ADR-095** (`ADR-095-calendar-gate-retraction.md`) — Cross-LLM gate discipline:
  calibration rounds using multiple model archetypes as independent judges catch
  systematic issues that same-LLM self-review misses. The empirical pattern encoded
  in ADR-095 §gate-#6 is directly applicable to multi-judge evaluation pipelines:
  use models from distinct provider lineages as co-judges for high-stakes evaluation
  decisions.

- **ADR-052** (`ADR-052-multi-model-dispatch-by-role.md`) — Model-routing by role:
  judge model selection MUST follow the same dispatch discipline as task-agent
  selection. High-stakes evaluation (security, safety, compliance) requires Opus-tier
  judges; advisory scoring allows Sonnet-tier. Self-enhancement bias risk is one of
  the rationale inputs for this routing constraint.
