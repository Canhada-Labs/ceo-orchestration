---
name: agent-evaluation
description: >
  Rigorous testing and benchmarking of LLM agents—covering behavioral contract
  verification, capability boundary probing, reliability metric collection, and
  production monitoring. The empirical reality is sobering: even top-ranked agents
  achieve below 50% on real-world task benchmarks such as SWE-bench Verified and GAIA
  (Jimenez et al., 2024; Mialon et al., 2023). Evaluation must be deterministic,
  version-pinned, and contamination-aware to produce claims that compound across
  releases. Use when: commissioning a new agent, upgrading an underlying model,
  detecting capability regression after a code change, or validating production health
  against a known-good canary set.
rewritten_at: 2026-05-07
rewrite_reason: voice_consistency
inspired_by:
  - source: sickn33/antigravity-awesome-skills/agent-evaluation.md@6003dc1acfedea34fa9051c408eb2fb508e08426
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
  - "**/benchmarks/**"
  - "**/canaries/**"
---

# Agent Evaluation

## Cardinal Rule

An agent benchmark that is not deterministic-replayable is not a benchmark; it is
anecdote-collection. Every evaluation claim MUST be reproducible from a fixed seed,
a version-pinned agent, and a frozen test fixture. If any of those three anchors is
absent, the result cannot be cited, compared, or gated in CI.

## Fail-Fast Rule

Stop evaluation immediately and declare the result invalid when any of the following
conditions is detected:

1. **Non-deterministic test infrastructure.** A test that cannot be replayed with
   identical inputs and produce a distribution within the known stochastic envelope
   of the model MUST NOT be merged into the evaluation corpus.
2. **No agent version pin.** If the model name, model version, system prompt hash, and
   tool-permission fingerprint are not recorded in the evaluation artifact, the result
   is unattributable and MUST be discarded.
3. **Train/eval contamination confirmed.** If the leakage detector returns a hit with
   similarity > 0.85 between any eval task and any training document, the affected
   tasks MUST be quarantined before scoring proceeds.
4. **Single-seed claim on stochastic output.** Any pass/fail claim derived from a single
   run over stochastic output is uninformative and MUST be re-run with n ≥ 10 before
   drawing conclusions.
5. **Human-evaluation kappa below threshold.** If inter-rater agreement (Cohen's kappa)
   across at least two independent raters falls below 0.6, the rating instrument is
   unreliable and MUST be recalibrated before scores are recorded.
6. **Benchmark published after agent training cutoff—not verified.** If the benchmark's
   release date predates the agent's training cutoff by fewer than 90 days, assume
   possible contamination and run a per-task contamination probe before accepting results.

## When to Apply

Activate this skill when:

- A new agent is being commissioned and capability boundaries are unknown
- An underlying foundation model has been upgraded or swapped
- A system prompt or tool-permission list has changed and regression risk is non-trivial
- Observed production failure rates have drifted above the established alert threshold
- A downstream team requests evidence of agent capability before integration
- Release governance requires benchmark parity with a prior version before tagging

Skip when: the task is purely model training evaluation (loss, perplexity, BLEU); the
goal is fairness or bias auditing; the evaluation target is a standalone classification
model rather than an agentic loop.

## Agent Capability Frame

Five dimensions structure agent capability. Each dimension has a characteristic failure
mode and a testable observable.

| Dimension | What it measures | Canonical test signal | Characteristic failure |
|---|---|---|---|
| Planning | Multi-step goal decomposition and sequencing | Fraction of tasks where the agent produces a correct plan before acting | Myopic single-step responses; loops; premature tool invocation |
| Tool use | Correct selection, parameterisation, and interpretation of available tools | Tool-call accuracy rate; error recovery after bad tool return | Hallucinated tool names; malformed parameters; ignoring tool errors |
| Multi-step reasoning | Maintaining correct intermediate state across ≥ 3 reasoning steps | Task completion on benchmarks with chained sub-goals (AgentBench, GAIA) | State corruption at step N+1; forgetting prior steps |
| Self-correction | Detecting and recovering from its own errors mid-task | Pass rate after deliberate error injection at step 2 of a 5-step task | No recovery; compounding errors; infinite retry loops |
| Context management | Operating correctly as context length grows toward the model window limit | Accuracy curves binned by context fill fraction (0-25%, 25-50%, 50-75%, 75-100%) | Accuracy cliff at 50%+ fill; ignoring early-turn instructions |

Evaluation suites MUST cover all five dimensions. A suite that only measures final-task
pass rate produces a scalar that conflates all five sources of failure and cannot guide
targeted improvement.

## Benchmark Selection Discipline

Select benchmarks based on the capability dimension being measured, the known
contamination risk, and the version-pin availability. The table below documents eight
benchmarks in scope for agent evaluation.

| Benchmark | Primary capability | Known limitation | Leakage risk | Citation |
|---|---|---|---|---|
| SWE-bench Verified | Tool use + multi-step reasoning (real GitHub issues) | Requires full repo checkout; expensive to run | High — GitHub issues publicly indexed | Jimenez et al., 2024 |
| HumanEval+ | Code generation, basic tool use (unit-test pass) | Narrow domain (Python functions); no planning | Medium — canonical solutions widely reproduced | Liu et al., 2023 |
| MBPP+ | Code generation, short-horizon reasoning | Beginner-level tasks; ceiling near current SOTA | Medium — problems from introductory courses | Austin et al., 2021; Liu et al., 2023 |
| MMLU | Knowledge retrieval across 57 domains | Static MCQ; no agentic loop; no tool use | High — 5-year public exposure; heavily fine-tuned against | Hendrycks et al., 2021 |
| GPQA Diamond | Expert-level reasoning (PhD-calibre science problems) | Expert knowledge required; low inter-rater agreement | Low — problems deliberately esoteric | Rein et al., 2023 |
| MATH | Multi-step mathematical reasoning | Narrow domain; no external tool use | Medium — problems from competition archives | Hendrycks et al., 2021 |
| GAIA | Real-world multi-step agentic tasks (web, code, files) | Human-in-loop annotation; slow to expand | Low — recently released (2023); diverse modalities | Mialon et al., 2023 |
| AgentBench | Multi-environment agent performance (OS, DB, KV, web) | Requires sandboxed environments; high infra cost | Low — environments partially synthetic | Liu et al., ICLR 2024 |

Benchmarks MUST be cited with year and paper authors in any evaluation report. Citing
only a benchmark name without provenance is insufficient for external reproducibility.

Never select benchmarks solely for prestige or name recognition. Benchmark selection
MUST be justified by the capability dimension under test and the known leakage profile.
When leakage risk is High, run a per-task contamination probe before accepting results
as evidence.

## Behavioral Testing

### Input Perturbation

Perturbation testing probes whether the agent's observed capability is robust to
surface-level variation in input that should not change the correct answer.

Four perturbation classes cover the most common failure modes:

- **Typographic**: introduce common typos (transposition, deletion, substitution) at a
  2% character error rate over the task prompt
- **Paraphrase**: rephrase the task instruction while preserving semantic content
- **Format shift**: change the presentation of the same task (list → paragraph, table →
  CSV, numbered → bulleted)
- **Noise injection**: prepend or append semantically irrelevant content of length 10%
  of the original task

For each perturbation class, generate N ≥ 5 variants per original task. Record the pass
rate delta between original and perturbed. A delta greater than 15 percentage points
indicates brittle surface-form sensitivity that MUST be documented as a capability gap.

### Capability Boundary Probing

Boundary probing identifies the task complexity threshold above which the agent
transitions from reliable to unreliable. Structure the probe as a ladder:

1. Establish a passing baseline at the simplest task formulation
2. Increase task complexity by one dimension at a time (more steps, longer context,
   additional tool dependency, higher ambiguity)
3. Record the first level at which pass rate drops below 0.6
4. Report the capability boundary as a structured label:
   `{dimension}: reliable below {threshold_description}, unreliable above`

### Failure-Mode Taxonomy

Classify every observed failure into exactly one of the following categories. Mixed
failures belong to the dominant cause.

| Category | Definition | Example |
|---|---|---|
| `planning_error` | Task decomposition is structurally wrong before any tool is called | Agent attempts to write the code before reading the spec |
| `tool_misuse` | Correct tool selected but parameterised incorrectly | `read_file` called with a path that was never established |
| `state_corruption` | Agent's mental model of prior steps diverges from reality | Agent concludes a file was modified when no write occurred |
| `context_overflow` | Agent ignores or confabulates information present in earlier context | Forgets a constraint stated at turn 1 when answering at turn 8 |
| `hallucination` | Agent asserts a fact or tool return value not grounded in actual observations | Invents a passing test suite before running the tests |
| `loop` | Agent enters a retry or reflection loop without making progress | Re-reads the same file 6 times without change |
| `refusal` | Agent declines a task within its intended scope | Safety classifier over-fires on a legitimate code-review task |

## Reliability Metrics

The following four metrics form the minimum reporting surface for any agent evaluation.
Additional metrics are additive; these four MUST always be present.

**Success rate** — fraction of tasks where the agent produces an output that satisfies
the ground-truth acceptance criterion within the permitted step budget. Report as a
point estimate with a 95% Wilson score confidence interval. Never report a single-run
scalar without confidence bounds.

**Wall-time distribution** — collect p50, p90, and p99 latency across all task
executions. Report separately for tasks that succeed and tasks that fail; failure paths
often have different latency profiles (timeouts, retry loops) that average masking hides.

**Token cost per task** — total input + output tokens consumed, summed across all model
calls in a single task execution. Report mean ± standard deviation. This is the primary
cost-envelope signal for production budget gating. Flag any task where token cost
exceeds 3× the population mean as a potential runaway path.

**Error-type distribution** — breakdown of failures by the failure-mode taxonomy above.
A distribution dominated by a single category indicates a targeted improvement path.
A uniform distribution across all categories indicates systemic incapacity.

## Replay Discipline

Deterministic replayability is the hard prerequisite for any evaluation claim that will
be cited in a regression gate, release note, or capability comparison.

The following four controls MUST be in place before an evaluation run is recorded:

1. **Seed fixation.** Where the model API supports a seed parameter, set it to a fixed
   integer and record the value. Where the API does not support seed, record temperature
   and document that exact determinism is not achievable, then compensate with n ≥ 10
   runs and report the distribution.

2. **Agent version pin.** Record: model name, model version or API snapshot identifier,
   system prompt SHA-256, and tool-permission set as a sorted list. Any change to any of
   these four values invalidates comparability with prior runs and MUST trigger a new
   baseline.

3. **Fixture freeze.** Evaluation tasks MUST be stored as version-controlled frozen
   fixtures. Tasks stored only as live API calls or mutable database records are not
   fixtures — they are observations. Fixtures MUST be immutable from the moment the
   evaluation run begins.

4. **Runtime container hash.** Record the container image SHA or virtual environment
   lock file hash for the execution environment. Undocumented dependency upgrades between
   runs have caused apparent performance changes that were attributable to a library
   version rather than the agent.

Replay artifacts MUST be stored alongside the evaluation report, not in a separate
system. An evaluation report without its replay artifact is incomplete.

## Test Set Hygiene

Train/eval contamination is the most common source of inflated capability claims in
published agent benchmarks. The following controls are non-negotiable.

**Three-set partition.** Evaluation data MUST be partitioned into three disjoint sets:

- *Train set* — data used in fine-tuning or few-shot examples in the system prompt
- *Eval set* — data used for scoring capability claims
- *Canary set* — held-out data used only for production drift detection (never for
  training or evaluation)

No task document may appear in more than one set. Partitioning MUST be verified by
exact-match deduplication on the task instruction text before any evaluation run.

**Per-task contamination probe.** For each benchmark task, run the following probe
before including it in the eval set:

```python
# Contamination probe — run ONCE per task, result recorded in fixture metadata
def probe_contamination(agent, task_input: str, expected_output: str) -> dict:
    """
    Supply the first half of the task input and check whether the agent
    completes it in a way that matches the expected output with high similarity.
    High similarity (>0.85) indicates the agent has likely seen this task.
    """
    partial = task_input[: len(task_input) // 2]
    completion = agent.complete(f"Continue: {partial}")
    tail = task_input[len(task_input) // 2 :]
    similarity = jaccard_similarity(completion, tail)
    return {
        "task_id": task_input[:40],
        "similarity": similarity,
        "verdict": "CONTAMINATED" if similarity > 0.85 else "CLEAN",
    }
```

Tasks with a CONTAMINATED verdict MUST be replaced with newly authored tasks before
scoring.

**RAG leakage check.** If the agent under evaluation uses a retrieval system, verify
that the retrieval index does not contain documents drawn from the eval set. Index
queries using representative task inputs and inspect the top-3 retrieved documents for
semantic overlap with ground-truth answers.

## Production Monitoring

Production monitoring tracks three signals against thresholds established from the
canary set at release time.

**Canary set drift.** Run the canary set on a fixed schedule (daily for high-volume
agents; weekly for low-volume). Record success rate and token cost per task. Alert when
either metric deviates by more than 10 percentage points from the release-time baseline
on two consecutive measurement cycles.

**Cost-per-task budget.** Establish a token budget per task category at release time.
Alert when the rolling 7-day average cost-per-task for any category exceeds 1.5× the
release baseline. Runaway cost growth is an early indicator of planning loops or
context degradation before task success rates drop noticeably.

**Failure-mode classification.** Maintain a running count of production failures
classified by the failure-mode taxonomy. Alert when any single category accounts for
more than 40% of all failures in a 7-day window; a spike in a single category indicates
a targeted regression rather than general capability drift.

Alert thresholds MUST be reviewed at every major model upgrade. A threshold calibrated
against a prior model version is not automatically valid for the new version.

## Inter-rater Agreement

Human evaluation is required when the acceptance criterion cannot be automated (open-
ended generation quality, soft correctness, alignment with policy intent). The following
protocol governs human evaluation to ensure reproducibility.

**Minimum sample.** Human-scored samples MUST total n ≥ 30 per evaluation condition.
Below n = 30, confidence intervals are too wide to support comparative claims.

**Rating instrument.** The rating rubric MUST be defined and frozen before raters see
any outputs. Post-hoc rubric adjustment is forbidden; it introduces rater bias and
invalidates inter-rater statistics.

**Kappa threshold.** Compute Cohen's kappa across all rater pairs before computing
aggregate scores. If kappa < 0.6, the rating instrument is ambiguous. MUST recalibrate
with a joint calibration session (raters score 10 shared items together, discuss
disagreements, then re-score independently). Accept results only when kappa ≥ 0.6.

**Calibration cycle.** Each new rater cohort MUST complete the calibration session
described above before scoring live evaluation items. Prior-cohort calibration does not
transfer.

**LLM-as-judge caveats.** Using a second LLM as an automated rater is operationally
attractive but introduces same-provider bias: models from the same training lineage tend
to rate each other's outputs higher than human raters do. When the evaluating LLM is
from the same provider as the agent under test, report this explicitly and apply at
least one human spot-check on a 10% sample. This is the cross-LLM gate rationale
documented in ADR-095.

## Anti-Patterns

| Anti-pattern | Why it fails | Correct practice |
|---|---|---|
| Cherry-picked benchmark | Selecting the benchmark where the agent performs best post-hoc and presenting it as representative capability | Benchmark selection MUST be declared before evaluation runs; any post-hoc addition requires explicit rationale |
| No version pin on agent | Results cannot be attributed to a specific model state; upgrades silently break comparability | Record model name, model version or snapshot ID, system prompt SHA-256, and tool-permission set in every evaluation artifact |
| Train/eval contamination | Eval tasks that appeared in training inflate scores by providing memorised rather than reasoned answers | Run per-task contamination probes; maintain strict three-set partition; replace contaminated tasks before scoring |
| Single-seed claim | A single run on a stochastic model is a sample of one; variance is invisible | Run n ≥ 10; report success rate with Wilson score 95% CI |
| Metric gaming | Agent optimises for the specific metric (e.g. maximising token count for a verbosity metric) rather than underlying task quality | Use multi-dimensional evaluation; rotate metrics; include adversarial variants that penalise the gaming strategy |
| Production score substitution | Using production A/B test lift as a substitute for offline benchmark evaluation | Production lift measures user behaviour change, not agent capability; both are necessary; neither substitutes for the other |
| Benchmark-only evaluation | Reporting only benchmark scores without a canary set for production monitoring | Establish canary set at release time; run it on schedule; alert on drift |
| LLM-as-judge without same-provider disclosure | Using the same-provider LLM as both agent and judge without disclosing the potential bias | Disclose provider relationship; apply human spot-check on 10% sample; consider cross-provider judge when the evaluation is adversarial |

## Regression Gate Protocol

A regression gate blocks deployment when an evaluation result falls below an established
baseline. Gates are only as reliable as the evaluation discipline behind them.

The following protocol governs regression gating in CI:

1. **Baseline commitment.** At each release, record the evaluation results for the
   version being shipped as the immutable baseline. Store as a version-controlled JSON
   artifact alongside the model version pin and fixture hash.

2. **Gate condition.** A candidate release MUST meet all of the following before
   promotion:
   - Success rate ≥ baseline success rate − 3 percentage points (statistical tolerance
     for same-model variance)
   - No new failure-mode category exceeding 15% of total failures that was absent or
     below 5% in the baseline run
   - Token cost per task ≤ 1.3× baseline (prevents silent cost regressions)

3. **Override protocol.** Owner-authorised overrides of a failed gate MUST be recorded
   with a written rationale and an issue filed to close the gap before the next release.
   Unrecorded overrides are governance violations.

4. **Canary-set continuity.** The canary set used in the gate MUST be the same fixture
   set used at baseline. Substituting a new canary set invalidates the regression
   signal. If the canary set must be rotated (e.g., benchmark contamination discovered),
   run both the old and new sets simultaneously for one release cycle to establish
   continuity.

## Cross-References

- `core/ai-llm-orchestration` — architectural patterns for the multi-agent loops that
  this skill evaluates; evaluation design should mirror the loop topology
- `core/code-review-checklist` — two-pass review doctrine applicable to evaluation
  artifacts (test fixture review, scoring rubric review); ADR-058 anchor
- `core/llm-routing-and-finops` — token cost budgets established at evaluation time feed
  directly into the routing and cost-envelope governance in this skill
- `domains/community/skills/advanced-evaluation` — extends this skill with advanced
  statistical methods (power analysis, bootstrap CI, Bayesian updating) for large-scale
  evaluation studies
- `domains/community/skills/agentic-actions-auditor` — security posture review for
  agents running in CI/CD contexts; run alongside this skill when the agent under
  evaluation has write access to a repository or deployment pipeline

## ADR Anchors

- **ADR-052** — Model routing governance: establishes the VETO floor requiring Opus-tier
  models for code-review and security evaluation tasks. Applies when this skill is
  invoked to evaluate a security agent or perform a scoring pass that constitutes a code
  review.
- **ADR-058** — Two-pass review doctrine: evaluation artifacts (test fixtures, scoring
  rubrics, benchmark selection rationale) require a separate authoring and review pass
  before being promoted to the frozen corpus. The author-then-review separation prevents
  the same cognitive frame from both constructing and validating the evaluation.
- **ADR-095** — Cross-LLM gate empirical pattern: the LLM-as-judge same-provider bias
  documented in the Inter-rater Agreement section above has been observed empirically
  across multiple evaluation cycles in this framework. When using an automated judge,
  prefer a cross-provider model. ADR-095 §gate-#6 documents the confirmation cadence.
