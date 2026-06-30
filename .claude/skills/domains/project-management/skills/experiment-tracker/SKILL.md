---
name: experiment-tracker
description: >
  Product and growth experiment lifecycle manager covering hypothesis
  registry, experiment-design quality assurance, in-flight monitoring,
  results synthesis, learnings library, and experiment-fatigue detection.
  Operationalises growth-hacker experiment discipline at PM cadence,
  enforcing power analysis, guardrail metrics, pre-committed kill-switch
  criteria, and mutual-exclusion configuration. Use when a task involves
  designing or reviewing an A/B test, managing concurrent experiment
  portfolios, synthesising statistical results, or building an
  organisational learnings archive for growth and product teams.
owner: Priya Nallan (Experiment Tracker, domain persona)
tier: domain:project-management
scope_tags: [experiment-tracking, hypothesis-registry, experiment-design-qa, results-synthesis, learnings-library]
inspired_by:
  - source: msitarzewski/agency-agents/project-management/project-management-experiment-tracker.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: project-management
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
  - "**/experiments/**"
  - "**/ab-tests/**"
  - "**/hypotheses/**"
  - "**/learnings/**"
---

# Experiment Tracker

## Cardinal Rule

An experiment without a pre-registered hypothesis, primary metric, and
sample-size calculation is not an experiment — it is a post-hoc
rationalisation waiting to happen.
Every decision to ship, kill, or iterate must trace back to criteria
committed before the first data point was collected.
Retroactively changing success criteria to fit observed data invalidates
the inference and corrupts the learnings library.

## Fail-Fast Rule

Stop the design if the team cannot state a falsifiable hypothesis in one
sentence before any implementation begins.
If no primary metric can be isolated from confounders introduced by
concurrent experiments, resolve the mutual-exclusion configuration first.
Launching under ambiguous assignment is a contamination event, not an
acceptable risk.

## When to Apply

Apply this skill when the task is one or more of:

- Registering or reviewing a new experiment in the hypothesis registry.
- Conducting a design-QA gate before experiment launch.
- Monitoring an in-flight experiment and deciding whether to act on
  interim data.
- Synthesising results and computing statistical validity after runtime.
- Adding or retrieving entries from the organisational learnings library.
- Auditing the experiment portfolio for fatigue, overlap, or mutual-
  exclusion violations.

## Hypothesis Registry

The registry is the single source of truth for all experiments, past and
present. No experiment runs without a registry entry.

Minimum required fields per entry:

| Field | Requirement |
|---|---|
| `id` | Unique slug: `EXP-<YYYY>-<NNN>` |
| `hypothesis` | One sentence: "If [change], then [metric] will [direction] by [magnitude] because [mechanism]." |
| `primary_metric` | One metric with pre-committed success threshold |
| `guardrail_metrics` | At least one metric that triggers abort if it degrades beyond threshold |
| `sample_size_per_variant` | Computed from power analysis (see Experiment-Design QA) |
| `min_runtime_days` | Calendar floor; cannot be shortened post-launch |
| `owner` | Named accountable PM or analyst |
| `status` | `draft` / `approved` / `running` / `complete` / `archived` |

Entries must be committed before engineering implementation begins.
A hypothesis amended after launch is a new experiment; the original entry
must be archived as superseded and a new entry opened.

## Experiment-Design QA

The design-QA gate is mandatory before any experiment transitions from
`draft` to `approved`.

Power analysis requirements:

1. Baseline conversion rate or metric mean established from production
   data covering at least fourteen days with no overlapping test traffic.
2. Minimum detectable effect (MDE) set to the smallest business-meaningful
   change, not the smallest statistically detectable change.
3. Power ≥ 0.80; significance level α ≤ 0.05. Two-sided test unless a
   directional hypothesis is pre-registered with written justification.
4. Sample size per variant computed from (1), (2), and (3).
5. Estimated runtime derived from daily eligible-traffic volume; must
   cover at least one full weekly cycle.

Additional gate criteria:

- Guardrail metrics defined with abort thresholds (absolute or relative
  degradation, not directional preference).
- Kill-switch criteria stated explicitly: which metric moving in which
  direction by what magnitude triggers immediate halt.
- Segmentation pre-defined if segment-level analysis is planned;
  post-hoc segmentation without pre-registration inflates false-discovery
  rate.
- Mutual-exclusion configuration verified: no user can be simultaneously
  enrolled in another experiment whose treatment affects the same
  interaction path.

An experiment that fails any gate criterion must return to `draft` with
written remediation notes. Partial approval is not permitted.

## In-Flight Monitoring

Monitoring discipline prevents peeking bias, which inflates the false-
positive rate far above the nominal α.

Daily checks (automated dashboard):

- Sample ratio mismatch (SRM): assignment counts per variant must match
  the configured split ratio within a tolerance of ±1 percentage point.
  An SRM greater than this tolerance indicates instrumentation failure
  and requires a pause.
- Guardrail metric status: alert if any guardrail metric moves beyond
  its abort threshold.
- Data-pipeline health: ingestion lag, deduplication completeness.

Weekly checks (analyst review):

- Primary metric trajectory — for situational awareness only.
- Estimated days remaining to planned runtime.

Prohibited actions during runtime:

- **No peek-and-decide.** Calling a winner or loser before the
  pre-committed runtime and sample size are reached, even if p < 0.05,
  is invalid inference. The only exception is a guardrail abort.
- **No runtime extension without re-power.** If the primary metric has
  not moved after the planned runtime, a neutral result is a valid
  result. Extending to "give it more time" without a formal protocol
  (e.g. sequential testing with pre-specified extension rules) introduces
  optional stopping bias.
- **No treatment changes post-launch.** Any change to variant
  configuration after launch creates a mixed-treatment artefact; archive
  the experiment and open a new registry entry.

## Results Synthesis

Statistical analysis requirements:

1. Run the pre-committed test (t-test, z-test, Mann-Whitney, or other
   as registered at design-QA time). Changing the test post-hoc requires
   written justification and peer sign-off.
2. Report effect size and confidence interval alongside p-value.
   A p-value alone is not a results summary.
3. Assess practical significance: an effect that is statistically
   significant but smaller than the MDE is a neutral result for shipping
   decisions.
4. Per-segment analysis is valid only for segments pre-registered at
   design time. Flag any post-hoc segment finding as exploratory and
   hypothesis-generating, never confirmatory.
5. If multiple primary metrics were registered (rare — requires written
   justification at design-QA), apply Bonferroni or Benjamini-Hochberg
   correction and report adjusted p-values.

Results summary format (required for registry update):

```
Experiment: <id> — <name>
Decision: SHIP | KILL | ITERATE (with one-line rationale)
Primary metric: [observed delta] [CI lower, upper], p=[value]
Effect vs MDE: [above / at / below] threshold
Guardrail metrics: [all PASS | list any triggered]
Segment heterogeneity: [notable findings or NONE]
```

## Learnings Library

Every experiment with status `complete` must produce a learnings artefact
before the entry is archived.

Required fields:

| Field | Content |
|---|---|
| `hypothesis_tested` | Verbatim from registry |
| `result` | CONFIRMED / REFUTED / INCONCLUSIVE (with effect and CI) |
| `decision` | SHIP / KILL / ITERATE |
| `causal_mechanism` | Proposed explanation for the observed effect or null |
| `follow_up_hypotheses` | Zero or more new registry-ready hypotheses generated |
| `searchable_tags` | Domain, surface, user-segment, metric-family |

The library must be searchable by domain and metric family so that future
experiment designers can retrieve prior evidence before registering
similar hypotheses. Duplicate-hypothesis detection is a primary library
use case: registering a hypothesis already tested with a REFUTED result
wastes capacity and inflates the portfolio false-positive rate via
independent-rediscovery bias.

## Experiment-Fatigue Detection

Experiment fatigue occurs when users are enrolled in enough simultaneous
experiments that their behaviour is distorted by treatment overload rather
than by any individual treatment.

Controls:

- **Per-customer experiment-volume cap.** The maximum number of
  simultaneous experiment enrolments per user is defined in the
  experiment platform configuration. Default ceiling: three concurrent
  enrolments per user across all surfaces. Raising the cap requires
  owner sign-off and a written justification in the platform config
  history.
- **Mutual-exclusion layers.** Experiments affecting the same interaction
  surface (checkout flow, onboarding sequence, pricing display) must be
  placed in mutually exclusive layers. Users are assigned to at most one
  experiment per layer.
- **Holdout groups.** Maintain a global holdout (minimum 5% of
  eligible traffic) never enrolled in any experiment. Use for cumulative
  effect measurement and as a sanity check on the experiment platform
  itself.
- **Portfolio review cadence.** At least once per quarter, review active
  experiments for layer saturation and cap violations before approving
  new launches.

## Decision Discipline

Decision criteria must be committed at design-QA time and must not be
changed after launch.

Decision logic:

| Condition | Decision |
|---|---|
| Primary metric ≥ MDE, p ≤ α, no guardrail triggered | SHIP |
| Primary metric < MDE regardless of p-value | KILL or ITERATE |
| Guardrail metric triggered during runtime | KILL (immediate) |
| SRM detected and unresolved | INCONCLUSIVE — invalidate, re-run |
| Primary metric inconclusive, follow-up hypothesis available | ITERATE (new registry entry) |

ITERATE is not a hedge against a KILL decision. An experiment whose
primary metric moved in the wrong direction is a KILL; learnings from
it may inform a new hypothesis, but the original experiment is over.

## Anti-patterns

| Anti-pattern | Why it fails | Correct approach |
|---|---|---|
| Peek-and-extend | Multiple looks inflate false-positive rate above α; stopping when p < 0.05 is peeking even once | Pre-commit runtime and sample size; use sequential testing protocol if early stopping is required |
| No power calculation | Underpowered experiments produce inconclusive results at planned runtime; overpowered experiments waste traffic longer than needed | Run power analysis at design time using production baseline and pre-committed MDE |
| Missing guardrail metrics | A winning primary metric can mask user-experience degradation (latency, error rate, engagement drop) | Define at least one guardrail per experiment; block approval gate until present |
| Overlapping experiments uncontrolled | Unresolved mutual-exclusion means measured effects contain noise from multiple treatments | Verify layer assignment and mutual-exclusion configuration before approval |
| Library not updated | Organisational knowledge is lost; future teams re-run refuted experiments | Learnings artefact is mandatory before archiving; treat missing artefacts as open work items |
| Post-hoc segmentation | Splitting results across unanticipated segments inflates false-discovery rate and generates spurious findings | Pre-register segments; label any post-hoc segment finding as exploratory only |
| Retroactive criteria change | Changing success thresholds after seeing results invalidates the inference and erodes stakeholder trust | Treat criteria as immutable after design-QA approval; amendments require a new experiment entry |

## Cross-References

- `domains/marketing-global/skills/growth-hacker` — upstream experiment
  design discipline and growth-loop hypothesis patterns that feed the
  hypothesis registry.
- `domains/community/skills/agent-evaluation` — evaluation methodology
  applicable to model or algorithm A/B experiments (treatment assignment,
  scoring rubric, inter-rater reliability).
- `domains/community/skills/advanced-evaluation` — extended statistical
  evaluation protocols (effect-size families, sequential testing, causal
  inference) for complex or high-stakes experiments.

## ADR Anchors

- **ADR-058** — brainstorm gate and two-pass adversarial review; applies
  to experiment design documents produced by this skill before the
  design-QA gate is opened.
