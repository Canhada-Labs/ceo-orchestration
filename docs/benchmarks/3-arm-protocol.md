# 3-arm benchmark protocol — treatment / control / placebo-terse

> **Purpose:** future benchmark comparisons of `ceo-orchestration`
> vs alternative orchestration approaches MUST use the 3-arm
> protocol defined here. Metodologia herdada de `caveman`
> (juliusbrussee/caveman — NOT imported as code, only protocol
> absorbed). Phase D deliverable of post-Sprint-32 roadmap.
>
> **Why 3 arms:** a 2-arm comparison (ceo-orchestration vs alt)
> cannot distinguish orchestration benefit from verbosity confound.
> The placebo arm isolates "framework discipline" from "longer
> prompts with more text."

## Arms

### Arm 1 — TREATMENT
`ceo-orchestration` full stack:
- CEO protocol active (Gate 1/2/3 session protocol)
- Named agents spawned per ROUTING TABLE with persona + skill
  loaded
- Canonical-edit sentinels + hook governance active
- Full instrumentation (audit-log, ceo-cost, injection scanners)

### Arm 2 — CONTROL
Comparable alternative orchestration OR bare LLM:
- CrewAI / LangGraph / OpenAI Agents SDK / MS Agent Framework /
  Google ADK / Semantic Kernel / Portkey — pick ONE per comparison
  (not all-at-once)
- OR bare Claude Code without ceo-orchestration skills
- Same model (Claude Opus 4.7) for fairness
- Same total compute budget (wall-clock OR token count, pre-declared)
- NO ceo-orchestration-specific artifacts (no skills/, no hooks/)

### Arm 3 — PLACEBO-TERSE
`ceo-orchestration` stack BUT with CEO protocol stripped to
prose-only:
- No Gate 1/2/3 session protocol (skip straight to task)
- Named-agent spawns with `## SKILL CONTENT` replaced by "be
  thorough about X" prose
- Hooks disabled (`CEO_AUDIT_LOG_DISABLE=1` + equivalent) — observer
  quiescence
- Same verbosity / boilerplate overhead as treatment arm, BUT no
  skill checklists, no sentinel discipline, no observability

**Placebo purpose:** isolates "framework discipline effect"
(skills as checklists, sentinels as enforcement, observability as
feedback) from "longer prompts effect" (more tokens, more context,
more imperative-phrasing). A benefit observed only in
Treatment-vs-Control but not Treatment-vs-Placebo-Terse is likely
a **verbosity artifact**, not a framework benefit.

## Workload requirements

Each benchmark workload MUST:

1. **Be quantitatively scorable** with a pre-declared scoring
   function (no post-hoc metric shifting)
2. **Have a ground truth** independent of the arms being compared
3. **Be reproducible** — same input + same seeds → same output
   within ±5% tolerance
4. **Run ≥10 iterations per arm** for percentile reporting
5. **Publish per-iteration raw data** in JSON (not just aggregates)

Workloads that fit:
- SWE-bench-lite subset (3-5 tasks, pinned seeds, Docker
  `--network=none`)
- Custom swarm-coordinator workloads (N-parallel tournament
  best-of-N; per PLAN-017 scaffolding)
- Bug-reproduction fidelity (given issue description, measure
  fixture generation accuracy)
- Code-review finding density + precision (per PLAN-034
  adversarial reviewer)

Workloads that DO NOT fit:
- Unstructured "judge 1-10 how good this looks" (no ground truth)
- Marketing-style demo reels (not repeatable)
- Single-arm showcases ("framework did X" with no comparison)

## Compute budget

Per PLAN-051 §B5 refusal (ADR-075), benchmark execution carries
**paid-service risk**. The protocol requires:

- **Pre-declared budget per arm** (USD cap OR token cap)
- **Hard kill on budget exceed** (coordinator.py enforces)
- **Owner authorization** required before running any arm with
  non-zero paid services (Anthropic Console / OpenAI / Gemini
  API costs)
- **NO `pip install` at benchmark time** — deps pinned in lock
  file shipped separately
- **Sandboxed execution** per scaffold `docs/benchmarks/sprint-32-fairness-protocol.md`
  (Docker `--network=none`, tmpfs workspace, digest-pinned images)

## Scoring

Each run emits a result row with:

```json
{
  "arm": "treatment|control|placebo_terse",
  "workload_id": "<stable-id>",
  "seed": <int>,
  "iteration": <int>,
  "outcome_metric_primary": <float>,
  "outcome_metric_secondary": <float>,
  "wall_clock_ms": <int>,
  "tokens_in": <int>,
  "tokens_out": <int>,
  "cost_usd": <float>,
  "adapter": "claude-opus-4-7|...",
  "git_sha": "<sha>",
  "framework_version": "v1.10.0",
  "provenance": {
    "hardware": {"cpu": "...", "ram_gb": <int>},
    "os": "darwin 25.4.0 | linux-gnu 6.x",
    "python": "3.11.x",
    "timestamp_utc": "2026-04-24T18:20:00Z"
  }
}
```

## Reporting requirements

Per cell (`arm × workload_id`):

- **N ≥ 10** iterations published
- **median, p50, p95, p99, stddev** for `outcome_metric_primary`
- **Separate cold from warm** (cold = first iteration per
  seed-arm-workload)
- **NO "best of 3"** — all N runs included
- **Omit cells with N < 10** with footnote "insufficient samples
  for honest reporting"
- **Independent verifier step**: second operator re-runs 1
  workload × 3 seeds; match-within-tolerance ±5% on p95 required
  before publish

## Anti-goals (protocol integrity)

- **NO cherry-picking** seeds or iterations post-hoc
- **NO changing scorer after arm runs** (scoring function
  locked at workload commit time)
- **NO "internal-only" results** (if published, must include
  independent-verifier column; if not published with verifier, do
  NOT publish at all)
- **NO all-3-arms-run-by-same-operator** (control + placebo-terse
  require independent operators OR automated runners to avoid
  implementation-bias toward treatment)
- **NO pre-print marketing** ("our framework achieves X%") without
  full JSON artifacts

## When to invoke this protocol

- Any head-to-head comparison published externally
  (blog post, landing page, arxiv-style report)
- Any adopter-facing claim of "X% faster than Y" or
  "solves Z problems that Y doesn't"
- Any ADR proposing to sunset an alternative approach on
  empirical grounds

**Specifically NOT required for:**
- Internal correctness tests (use unit tests + integration tests)
- Debug runs during development
- Single-arm demos for teaching framework concepts

## Historical precedents

- **PLAN-044 (Session 39, 2026-04-20)**: full SOTA audit used
  12-agent parallel read-only survey of 11 ecosystem repos. That
  was AUDIT methodology (read-only, qualitative gap analysis),
  NOT benchmark (quantitative comparison). Protocol here is for
  the latter.
- **PLAN-051 §B5 (Session 59, 2026-04-24)**: head-to-head
  benchmarks REFUSED via ADR-075 (taxonomy (a) technical-
  infeasibility — no comparable public harness for swarm-
  coordinator workload). This protocol DOES NOT reopen B5; it
  provides the methodological foundation for FUTURE benchmark
  invocations when adopter demand materializes with a concrete
  comparable workload.
- **Caveman repo** (juliusbrussee/caveman): 3-arm structure
  absorbed as methodology. NOT imported as code. ADR for credit
  attribution not required (methodology, not code).

## Lifecycle

- **Status:** STABLE 2026-04-24 (Phase D of post-Sprint-32 roadmap)
- **Next revision:** if ecosystem develops standardized
  orchestration benchmarks (e.g. SWE-bench-orchestration) that
  invalidate or extend this protocol
- **Revision mechanism:** ADR proposing amendments +
  debate-orchestrate Round 1 across archetypes

## References

- `docs/benchmarks/sprint-32-fairness-protocol.md` (Sprint 32
  pre-registration scaffold, preserved post-B5 refusal)
- `docs/benchmarks/manifest.schema.json` (JSON Schema pin)
- `.claude/scripts/swarm/_benchmark_replay.py` (Sprint 32
  scaffold, reusable)
- `.claude/scripts/swarm/_replay_tournament.py` (NaN/Inf
  defensive scoring)
- ADR-075 (benchmark refusal, post-Sprint-32 methodological
  foundation)
- `memory/project_post_sprint_32_roadmap.md` (Fase D reference)
