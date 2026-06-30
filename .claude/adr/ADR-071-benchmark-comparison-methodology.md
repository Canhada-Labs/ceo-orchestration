---
id: ADR-071
title: Benchmark comparison methodology — Nível 2 (offline + public baselines)
status: ACCEPTED
created: 2026-04-22
accepted_at: 2026-04-22
accepted_via: Round-19 sentinel (84a4977 promote) + PLAN-058 Round-23 frontmatter flip (F-CR-02 residual closure)
proposed_by: CEO + VP Engineering + Principal QA Architect (PLAN-051 Phase 2.5)
related_plans: [PLAN-051, PLAN-017, PLAN-032]
related_adrs: [ADR-063, ADR-073]
blast_radius: L2-contained (docs + benchmark scaffold; no canonical hook changes)
supersedes: none
superseded_by: none
gates_phase: PLAN-051 Phase 5
enforcement_commit: 84a4977
accepting_session: S147
---

# ADR-071 — Benchmark comparison methodology

## Context

PLAN-051 Phase 5 (B5 — head-to-head benchmarks vs Devin/Codex/Karpathy)
needs a falsifiable, defensible measurement methodology. Owner
clarified 2026-04-22 (during PLAN-051 open-question #2 response): zero
external API connections; the framework competes only against publicly
published vendor scores. This ADR formalizes that decision and the
fairness protocol.

Owner mental model rationale (relevant context):
- Don't trust running competitor code (rivals' repos auditing security
  was already a concern in Session 55 wondelai analysis).
- Public baselines (Devin 13.9% / Aider 26.3% / etc on SWE-bench
  leaderboard) are immutable, unidirectional reads of markdown.
- Honest disclaimer: framework's differentiator is governance + multi-
  agent orchestration, NOT pure single-shot capability. SWE-bench
  measures the latter; we don't compete on the former axis without
  honest framing.

## Options considered

### Option A (REJECTED) — Live API to vendor systems

- Run our tasks against Devin / Codex / Cognition APIs
- Requires credentials, $$ subscription, data egress to vendors
- Introduces system boundary (framework → vendor APIs) per skill
  §Review Protocol Q5
- Vendor sees inputs/outputs of every run
- Owner explicitly rejected 2026-04-22 ("não confio nos códigos deles")

### Option B (ACCEPTED) — Nível 2: offline + public baselines

- Run SWE-bench-lite locally (open-source dataset, Docker images
  pinned by SWE-bench maintainers — not vendor-provided)
- Score: % issues resolved by our framework end-to-end
- Comparison: pulled from SWE-bench public leaderboard (markdown
  unidirectional read)
- Plus 3 internal differentiator metrics (mutation kill-rate, OWASP
  block-rate, governance overhead %) where vendors don't publish
  comparable numbers — honest "n/p" in those cells
- No connection to vendor systems; no credential required

### Option C (REJECTED) — Nível 3: full benchmark suite + adversarial

- SWE-bench full + Verified + microbench + adversarial OWASP battery
- ~$1k+ tokens, ~100h+ wall-clock, ~5 dev-days
- Justified later (post-v1.9.0 + adopter feedback) if needed; not
  Sprint 32 scope per PLAN-051 §3 anti-goals

## Decision

**Adopt Option B (Nível 2).** Phase 5 executes:

1. **Pre-registration artifact** — `docs/benchmarks/sprint-32-fairness-
   protocol.md` committed BEFORE any result collection. Header includes:
   scorer rule / NaN-Inf-timeout rule / seed discipline / task list /
   pre-registered expected metric.

2. **SWE-bench-lite execution** — local, Docker-isolated:
   - Dataset: official SWE-bench-lite (300 issues subset)
   - Docker images: pinned by digest from SWE-bench maintainers
   - **Sandbox:** ephemeral container, `--network=none`, RO source
     mount, tmpfs `/workspace`
   - **No `pip install` at benchmark time** — deps pinned upfront via
     hash-locked requirements

3. **Measurement methodology** (mandatory in every cell):
   - N ≥ 10 runs per task
   - Report median, p50, p95, p99, stddev (NOT average alone)
   - Separate cold (first run) from warm (runs 2..N)
   - `work_latency_ms` vs `git_overhead_ms` separation preserved
     (already in `_benchmark_replay.py`)
   - Disclose hardware + OS + Python + git versions in header
   - Cell with N < 10 → OMITTED with footnote (no dishonest reporting)
   - NO "best of 3" — all N runs published in JSON artifact

4. **Comparison source** — `https://www.swebench.com/` leaderboard
   markdown + cited vendor papers/blog posts. Each comparison cell
   includes upstream version + date (SWE-bench versions rotate).

5. **Independent verifier step** — second CEO spawn (or general-purpose
   agent) re-runs 1 task × 3 seeds; match-within-tolerance ±5% on p95
   required before publish.

6. **JSON Schema pin** — `docs/benchmarks/manifest.schema.json` locks
   the `_benchmark_replay.py` manifest format.
   `test_benchmark_replay_manifest_schema.py` validates the example.

7. **3 internal differentiator metrics** (we publish, vendors don't):
   - Mutation kill-rate on swarm coordinator (40/40 target post-Phase 4)
   - OWASP LLM Top 10 mechanically blocked count (per PLAN-039 rubric)
   - Governance overhead % (cost of debate/VETO/gates vs raw single-
     agent baseline same model)

8. **NO internal-disclaimer fallback** — if Phase 5 cannot achieve
   independently-verifiable methodology (e.g., independent verifier
   disagrees by >5%), Phase 5 closes `refused via ADR` taxonomy reason
   (a) "no comparable public harness for our differentiator", NOT a
   "publish-internal-with-disclaimer" path (Code Reviewer Risk #4
   accepted).

9. **Results redacted** via `_lib.redact` before publish (defense-in-
   depth even though benchmark inputs are public dataset).

## Decision drivers

1. **Owner directive 2026-04-22:** zero connection to vendor systems.
   Drives Option A rejection.
2. **Same-LLM bias mitigation** (PROTOCOL.md §Honest limitation):
   independent-verifier step (different CEO spawn) is the only honest
   countermeasure to "author benchmarks own framework".
3. **Pre-registration discipline** (QA Risk #3): publish protocol BEFORE
   results to prevent post-hoc protocol-shopping.
4. **Honest framing** (Code Reviewer Risk #4 accepted): SWE-bench is
   single-shot bug-fix; we expect to lose vs Aider on pure capability
   ($/% efficiency); we publish that loss honestly + the 3 metrics
   where we lead.
5. **v2.0.0 binding** (per ADR-073): the benchmark methodology
   determines whether v2.0.0 marketing claims are defensible. Wrong
   methodology → reputational damage at tag time.

## Consequences

### Positive
- Defensible, falsifiable, reproducible benchmark numbers.
- Honest about where framework competes (governance + multi-agent) vs
  where it doesn't (raw capability shootout).
- Independent verifier mitigates same-LLM bias as much as possible.

### Negative / Accepted trade-offs
- ~$200-600 in Claude API tokens for SWE-bench-lite full run.
- ~50h wall-clock for one complete pass.
- Likely shows framework "loses" SWE-bench-lite to Aider on pure %
  resolved (because Aider uses smaller models with lighter governance).
  Honest disclosure required.
- Independent verifier step doubles cost on the verifier-task slice.
- 3 internal metrics will have "n/p" entries for vendors → must be
  honestly framed as "we publish, they don't" not as "we beat them".

## Blast radius

**L2-contained.** Touches:
- `docs/benchmarks/sprint-32-fairness-protocol.md` (new pre-registration)
- `docs/benchmarks/sprint-32-head-to-head.md` (new public results doc)
- `docs/benchmarks/manifest.schema.json` (new JSON Schema pin)
- `.claude/scripts/swarm/tests/test_benchmark_replay_manifest_schema.py`
  (new schema-validation test)
- `.claude/scripts/swarm/_benchmark_replay.py` (existing scaffold;
  Phase 5 wires real run; possible minor edits)
- No canonical hook changes
- No SPEC schema changes

## Dual co-sign (PLAN-051 §3.1)

- **VP Engineering:** ✅ co-author (mechanism selection per skill
  §Review Protocol Q7 — public-baseline mechanism chosen)
- **Principal QA Architect:** ✅ co-author (fairness protocol design,
  pre-registration, independent verifier — per QA Risk #3)
- **Principal Security Engineer:** ✅ reviewed (sandbox per Security
  Risk #3 — `--network=none`, hash-pinned deps, no `pip install` at
  runtime, redact-before-publish)

## Lifecycle

- **PROPOSED-STAGED** (this commit) — Phase 2.5 draft
- **PROPOSED canonical** — round-18 promote
- **ACCEPTED** — Phase 5 execution kickoff (commits the
  pre-registration protocol artifact)
- **SUPERSEDED** if Owner reverses Option A/C decision (would require
  Round 2 debate per PROTOCOL.md §Debate)

## References

- PLAN-051 §Phase 5 Acceptance (full mandatory bullets list)
- PLAN-051 Round 1 debate consensus.md Cluster 4 (4-agent agreement)
- ADR-063 (tournament framework foundation)
- ADR-073 (SemVer bump criteria — depends on Phase 5 outcome for
  v2.0.0 framing)
- `.claude/scripts/swarm/_benchmark_replay.py` (Session 54 scaffold)
- `.claude/scripts/swarm/_replay_tournament.py` (Session 55 bridge)
- SWE-bench public leaderboard: https://www.swebench.com/
- PLAN-039 (OWASP LLM Top 10 rubric — feeds 1 of 3 internal metrics)

## Enforcement commit

**Enforcement commit:** to be populated post-Phase-5-execute with the
commit SHA of the pre-registration artifact `sprint-32-fairness-
protocol.md` (which is the gate that binds Phase 5 results to this
methodology). Pre-Phase-5, enforcement is advisory.
