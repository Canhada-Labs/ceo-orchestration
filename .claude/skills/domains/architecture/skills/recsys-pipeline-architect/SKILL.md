---
name: recsys-pipeline-architect
description: >
  Spec-and-scaffold discipline for composable recommendation, ranking, and feed
  pipelines built on the six-stage pattern Source → Hydrator → Filter → Scorer →
  Selector → SideEffect. Teaches why the stage order is fixed, what each stage
  owns, where parallelism is safe, the load-bearing trade-offs (single relevance
  score vs multi-action prediction with tunable weights; candidate isolation vs
  joint scoring; online vs offline vs hybrid serving), a filter/scorer cookbook,
  and an eight-step interview-to-scaffold workflow. Use when the task is "pick the
  top K items for a (user, context)": social feeds, content-CMS surfacing, RAG
  retrieval reranking, task/notification prioritisation, search reranking, or ad
  ranking — the plumbing AROUND a scoring function, not the model itself.
version: 1.0.0
inspired_by:
  - source: affaan-m/ecc/skills/recsys-pipeline-architect/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0b shape) ---
domain: architecture
priority: 8
risk_class: low
stack: []
context_budget_tokens: 850
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)recommend(ation|er)?|ranking pipeline|feed algorithm|for[- ]you feed|candidate pipeline|top[- ]?k items|rerank(er|ing)?"}
  - {event: file-edit, glob: "**/ranking/**"}
  - {event: file-edit, glob: "**/recommender/**"}
  - {event: file-edit, glob: "**/feed/**"}
# --- K1 paths: native file-touch activation ---
paths:
  - "**/ranking/**"
  - "**/recommender/**"
  - "**/recsys/**"
  - "**/feed/**"
  - "**/reranker/**"
source: affaan-m/ecc@81af4076 skills/recsys-pipeline-architect/
license: MIT
---

# Recsys Pipeline Architect

## When to Activate

Read this skill when the request is any variant of *"choose the best K items for
a given user and context"*:

- building a social/content feed, a personalised surface, or a "you might also
  like" rail;
- someone asks "how should I rank X" or describes a personalisation problem;
- there is already a scoring function (an ML model, an LLM judge, a heuristic)
  and what is missing is the plumbing around it — retrieval, enrichment,
  eligibility filtering, selection, and bookkeeping;
- migrating from a single relevance score to multi-objective ranking with
  tunable weights;
- wrapping a reranker for RAG retrieval, triaging notifications, or prioritising
  a task queue.

**Do NOT activate for** model-architecture work (transformer design, two-tower
retrieval, embedding training), pure training pipelines (the scoring function is
the caller's responsibility), or operating a deployed pipeline (monitoring,
autoscaling). This skill is the pipeline *around* the model, not the model.

The machine-first `activation_triggers` frontmatter is the canonical auto-load
rule; this section is its human-scannable mirror.

## The six stages

A ranking request flows through six composable stages, each with one job:

| # | Stage | Job | Concurrency |
|---|---|---|---|
| 1 | **Source** | Retrieve candidates from one or more origins | Parallel — sources fan out |
| 2 | **Hydrator** | Attach the metadata that later stages need to decide | Parallel — independent hydrators |
| 3 | **Filter** | Drop anything that must never be shown (blocked, expired, duplicate, ineligible) | Sequential — each filter sees fewer items |
| 4 | **Scorer** | Assign each survivor one or more scores | Sequential — later scorers read earlier scores |
| 5 | **Selector** | Sort by final score and take the top K | Single op |
| 6 | **SideEffect** | Cache served ids, log impressions, emit events, bump counters | Async — must never block the response |

### Why the order is fixed

- **Source before hydrate** — you must know which candidates exist before paying
  to enrich them.
- **Hydrate before filter** — most filters need attributes the source did not
  return (age, author, block state).
- **Filter before score** — scoring is the expensive stage; discard the
  ineligible before spending compute on them.
- **A scorer *chain*, not one scorer** — real systems compose ML scoring, then
  diversity reranking, then business rules; a single scorer cannot express that.
- **Select after score** — keeping selection separate keeps scoring
  deterministic and cacheable.
- **Side effects last and async** — bookkeeping must never sit in the user's
  latency path.

## Eight-step workflow when invoked

1. **Clarify the use case** in one round of three questions: what items are being
   ranked, what defines the input context, and what language/runtime is the
   target.
2. **Enumerate candidate sources** — usually an in-network set (followed / owned
   / subscribed) plus an out-of-network set (ML retrieval / trending /
   similar-to-liked).
3. **List required hydrations** — for every filter and scorer, name the datum it
   needs that the source did not provide.
4. **List the filters** — duplicate, self-authored, age, block/mute,
   already-served, eligibility. Cheap and universal filters go first.
5. **Design the scorer chain** — primary (ML/LLM) → combiner (multi-action with
   weights) → diversity reranker → business rules.
6. **Define the selector** — sort descending by final score and take top K, or a
   stratified mix (e.g. an in-network / out-of-network ratio).
7. **Define the side effects** — cache served ids, emit impression events, update
   counters, log analytics — all fire-and-forget.
8. **Generate a runnable scaffold** in the target stack. No pseudocode standing
   in for code.

## Trade-offs to surface explicitly (never default silently)

### Single score vs multi-action prediction

- **Single score** — one model predicts relevance. Changing behaviour means
  retraining.
- **Multi-action** — predict `P(action)` for several actions (read, like, share,
  skip, report) and combine them with weights at serving time. Changing behaviour
  means changing weights — no retraining. Weights can be negative to penalise
  outcomes you want less of. Recommend this when the product expects to re-tune
  often.

### Candidate isolation vs joint scoring

- **Isolated** — each candidate is scored independently. Deterministic, cacheable.
  This is the default.
- **Joint** — candidates attend to each other during scoring (e.g. a transformer
  over the batch). More expressive, but non-deterministic across batches and
  harder to cache. Reach for it only with a specific reason, such as explicit
  batch-aware diversity.

### Online vs offline vs hybrid

- **Online (request-time)** — the pipeline runs per request; budget ~100–300 ms.
  The default.
- **Offline (pre-computed batch)** — the pipeline runs periodically and results
  are cached; lower latency, lower freshness.
- **Hybrid** — retrieve candidates offline, rank online.

## Filter and scorer cookbook

**Filters** (order cheap-and-universal first, expensive-and-personal last):
deduplicate by id/content-hash; drop self-authored; drop stale by age; drop
blocked/muted authors; drop already-served (needs the served-id cache);
eligibility/policy checks last.

**Scorers** (composed in sequence): weighted sum over multi-action predictions
(the combiner); a diversity reranker such as maximal-marginal-relevance that
trades a little relevance for less redundancy; a per-position debias term; and
hard business rules applied as final multipliers or vetoes.

## Hard rules

1. **Never invent benchmark numbers.** "How much faster?" → "it depends on the
   workload; measure it yourself."
2. **Attribute the pattern honestly.** The six-stage shape was popularised by the
   open-sourced "For You" ranking algorithm (Apache-2.0,
   `github.com/xai-org/x-algorithm`). Credit the pattern; the code here is an
   independent reimplementation.
3. **No trademark or brand borrowing.** Do not name the artifact "For You" or
   describe it as a clone of a named product. The pattern is free; the brand is
   not. Prefer neutral names: "candidate pipeline", "feed pipeline", "ranking
   pipeline", "recsys pipeline".
4. **Surface every trade-off.** Multi-action vs single, isolation vs joint,
   online vs offline — present the choice, never pick silently.
5. **The scaffold must actually run.** No pseudocode dressed up as code.
6. **Filter order is load-bearing.** Cheap before expensive, universal before
   user-specific.
7. **Side effects never block.** Wrap them fire-and-forget — goroutines, un-awaited
   promises, asyncio tasks — so they cannot enter the response latency path.

## Anti-patterns

- Scoring before filtering — burns compute on candidates that get dropped anyway.
- Synchronous side effects — cache writes or impression emits blocking the
  response.
- One flat "relevance" score when the product must balance several objectives
  (engagement vs safety vs diversity vs ads).
- Joint scoring as the default — non-deterministic, cache-hostile, and it does
  not compose cleanly with downstream reranking stages.
- Shipping "illustrative" pseudocode — the scaffold has to run and pass its tests.

## Checklist

Before a pipeline design is done, confirm:

- Every stage is present and in canonical order (Source → Hydrator → Filter →
  Scorer → Selector → SideEffect); none folded into another.
- Filters run before scorers, and filters are ordered cheap/universal first.
- Each hydration is justified by a downstream filter or scorer that needs it.
- The scorer chain is explicit — primary, combiner, diversity, business rules —
  not one flat relevance number when the product has multiple objectives.
- The single-vs-multi-action, isolation-vs-joint, and online-vs-offline choices
  were surfaced to the user, not defaulted silently.
- Every side effect is fire-and-forget and cannot enter the response latency path.
- The pattern is attributed honestly and no product brand is borrowed for naming.
- The generated scaffold runs and passes its own tests — no pseudocode.

## Changelog

- **1.0.0** — Initial authored version. Six-stage Source→Hydrator→Filter→Scorer→
  Selector→SideEffect pattern with order rationale, the eight-step
  interview-to-scaffold workflow, the three load-bearing trade-offs, a
  filter/scorer cookbook, hard rules (including honest pattern attribution and
  no-trademark discipline), and anti-patterns.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=8c14fe696dcffd5bbd7c628b230804cb090ec0015165cf94cd9e5f01fdb3e98f
