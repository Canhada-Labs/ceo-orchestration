# Skill Authoring Tutorial

> Walk-through for adding a new skill to the framework. By the end of
> this tutorial, you will have authored a hypothetical
> `observability-and-metrics` skill, registered it in the skill
> inventory, routed it via the team file, and added a benchmark
> fixture for it.

> **Before you write:** confirm that a **skill** is actually the right
> mechanism for the rule/knowledge you're encoding. See
> `docs/MECHANISM-SELECTION.md` for the decision matrix — skills are
> reusable checklists, NOT enforcement. Rules that must be un-bypassable
> belong in hooks, cross-cutting architectural choices belong in ADRs,
> named personas belong in `team.md`. Choosing the wrong mechanism is
> the single most common cause of governance drift.

> **Skills are checklists, not vibes.** A great skill tells an agent
> what to verify, what patterns to use, what anti-patterns to flag.
> A bad skill is a wall of narrative the agent reads and forgets. The
> best examples in this repo: `code-review-checklist`,
> `security-and-auth`, `financial-correctness-and-math`.

## Anatomy of a skill

```
.claude/skills/<tier>/<skill-slug>/
├── SKILL.md               # required — the skill content
├── SKILL-frontend.md      # optional — frontend-specific variant
└── examples/              # optional — concrete code examples cited from SKILL.md
```

Three tiers exist:

| Tier | Path | When to use |
|------|------|-------------|
| **Core** (universal) | `.claude/skills/core/<slug>/` | Applies to any backend/full-stack project |
| **Frontend** (universal) | `.claude/skills/frontend/<slug>/` | Applies to any frontend project |
| **Domain** | `.claude/skills/domains/<domain>/skills/<slug>/` | Specific to a vertical (fintech, healthcare, etc.) |

For our `observability-and-metrics` example, the right tier is
**core** — observability concerns apply to any backend.

## SKILL.md frontmatter contract

Per `SPEC/v1/skill-frontmatter.schema.md`, every SKILL.md needs:

```yaml
---
name: <slug>                       # required, kebab-case, must match dirname
description: <one-paragraph>       # required, used in routing + auto-inventory
owner: <archetype name>            # optional, but recommended
trigger: <when-to-use prose>       # optional, helps the CEO route correctly
paths: ["<glob>", ...]             # optional (PLAN-135 K1): auto-activation globs —
                                   #   the skill surfaces when a touched file's
                                   #   repo-relative path matches one (fnmatch)
context: fork                      # optional (PLAN-135 K1): run the skill in a
                                   #   forked context — use on heavy analytic
                                   #   skills; enum: fork | main (default main)
---
```

The `description` lands in `team.md` SKILL MAP comments and is
consumed by `generate-skill-inventory.sh` for the always-on inventory
in `.claude/skills/core/ceo-orchestration/SKILL.md`. Keep it
descriptive and one paragraph (no line breaks).

`paths:` is the K1 auto-activation surface: if present it MUST be a
non-empty list of non-empty glob strings (lint rule `LINT-FM-40`), e.g.
`paths: ["src/payments/**", "**/billing/**"]` on a fintech skill — the
capability announces itself when payment-shaped code is touched, without
the author ever invoking the skill. `context:` MUST be `fork` or `main`
(lint rule `LINT-FM-41`); declare `fork` on heavy analytic skills so
their output doesn't pollute the main window. `/architect` skill
proposals emit `paths:` by default. Deterministic activation probe:
`.claude/plans/PLAN-135/research/probe_k1_paths_activation.sh`.

## Step 1 — Plan the skill

Before writing any markdown, answer five questions in writing
(scratchpad, plan file, or just your terminal):

1. **What archetype owns this skill?** Look at
   `.claude/team.md`'s archetype list. Pick one. If no archetype
   fits, you may need a new archetype — that's a bigger change
   (touch `team.md` ROUTING TABLE + agent-metrics.md).
2. **What problem does it solve?** One sentence. If you can't, the
   skill isn't ready.
3. **What patterns does it teach?** Concrete recipes, not slogans.
4. **What anti-patterns does it flag?** The "don't do this and
   here's why" section is what makes a skill a checklist not an
   essay.
5. **What can a benchmark prove about this skill?** Even an informal
   "test if the agent catches X" thought experiment.

For our example: **observability-and-metrics**

1. Owner: VP Operations (or a dedicated "Observability Engineer"
   if your team has one).
2. Problem: developers add features without metrics, then can't
   debug production incidents.
3. Patterns: structured logging, p50/p95/p99 latency capture, error
   budget tracking, dashboard-as-code.
4. Anti-patterns: print statements, manual log scraping, dashboards
   only the original author can read.
5. Benchmark: feed the agent a code change that adds an HTTP
   endpoint with no metrics. Check if it flags the missing metric
   instrumentation.

## Step 2 — Create the skill file

```bash
mkdir -p .claude/skills/core/observability-and-metrics
$EDITOR .claude/skills/core/observability-and-metrics/SKILL.md
```

Use this scaffold (and replace placeholders):

```markdown
---
name: observability-and-metrics
description: Observability engineering for production services — structured logging, percentile-based latency capture, error-budget tracking, metric naming conventions, and dashboard-as-code. Use when designing a new service, reviewing observability of an existing service, debugging a production incident, or auditing whether a feature can be operated.
owner: VP Operations (archetype)
trigger: New service launch, post-incident review, observability audit, or any feature that introduces a new external dependency.
---

# Observability & Metrics

## Role

The agent loading this skill is responsible for ensuring **every
production change is observable**. Operational maturity isn't an
afterthought; it's a precondition for the merge.

## Operational invariants (must be true after the change)

1. Every external call (HTTP, DB, cache, queue) has a latency metric
   with explicit p50/p95/p99 buckets.
2. Every error path increments a counter with a `reason` label
   (closed enum, not free-form text).
3. Every business event (signup, purchase, escalation) emits a
   structured log with a stable schema.
4. No new dashboard panel without an alert rule.
5. No alert rule without a runbook (runbook = `docs/INCIDENT-RESPONSE.md` style).

## Patterns to apply

### Latency capture

[concrete code example — language-agnostic pseudo-code]

### Error counting with reason labels

[concrete example]

### Structured logging vs print statements

[concrete recipe]

## Anti-patterns to flag

| Anti-pattern | Why it breaks production |
|--------------|---------------------------|
| `console.log("ok")` | Unsearchable, no level, no context |
| `time.time() - start` ad-hoc latency | No percentiles, no aggregation |
| Free-form error messages | Cardinality explosion in metrics backend |
| Dashboards without alerts | False sense of security |
| Alerts without runbooks | Pages without action |

## Checklist (paste into PR body)

- [ ] Latency metric for every new external call (p50/p95/p99 buckets)
- [ ] Error counter with closed-enum `reason` label
- [ ] Structured log for every business event
- [ ] Dashboard panel created OR existing panel updated
- [ ] Alert rule created with associated runbook section
- [ ] Sample query documented in PR description

## When NOT to apply this skill

- Internal-only scripts (no production runtime)
- One-shot data migrations (no ongoing operation)
- Test fixtures (no observability needed)

## References (project-specific examples)

- `docs/audit-dashboard.md` — example of dashboard-as-code in this repo
- `_lib/otel/bounded_exporter.py` — example of metric instrumentation
- `docs/INCIDENT-RESPONSE.md` — runbook pattern this skill enforces
```

Three rules for the body:

1. **Operational invariants come first.** What MUST be true. The
   agent reads this once and refers back.
2. **Patterns are concrete.** Show the code shape; don't describe it
   abstractly.
3. **Anti-patterns are flag-able.** Each one tells the agent
   "look for this and reject it".

## Step 3 — Regenerate the skill inventory

The `ceo-orchestration` SKILL.md has an auto-generated section
listing every skill. Regenerate after adding (or removing) a skill:

```bash
bash .claude/scripts/generate-skill-inventory.sh
```

This walks `.claude/skills/core/`, `.claude/skills/frontend/`, and
`.claude/skills/domains/*/skills/`, extracts `name:` and
`description:` from each SKILL.md frontmatter, and writes the
listing between the `<!-- BEGIN/END AUTO-GENERATED SKILL INVENTORY -->`
markers.

CI in `validate.yml` runs the same generator and diffs against the
committed file. Forgetting this step fails CI.

## Step 4 — Add to the routing table

Open `.claude/team.md` and:

1. Add the skill to the **SKILL MAP** table for the owning archetype.
2. Add a row to the **ROUTING TABLE** that maps a work type to
   spawning that archetype with this skill loaded.

For our example, in `team.md`:

```markdown
### SKILL MAP — Core

| Archetype | Primary skill | Secondary |
| ... | ... | ... |
| **VP Operations** | `observability-and-ops` | `observability-and-metrics` |   ← NEW
```

```markdown
### ROUTING TABLE

| Work type | Agent archetype | Skill to load | Approver |
| ... | ... | ... | ... |
| Observability instrumentation | **VP Operations** | `observability-and-metrics` | VP Operations |   ← NEW
```

If your skill is owned by an existing archetype, you only add the
ROUTING TABLE row.

## Step 5 — Add a benchmark (optional but encouraged)

Benchmarks live at `docs/benchmarks/<skill>.yaml` and follow the
schema in `SPEC/v1/benchmarks.schema.md` (or look at
`docs/benchmarks/owasp-basics.yaml` for a concrete example).

Two parts:

- **Positive cases** — situations where the skill's checklist
  should fire. The agent's response is scored against expected
  catches.
- **Control cases** — situations where the skill should NOT fire
  (false-positive guardrail).

Example structure:

```yaml
benchmark_id: observability-and-metrics-v1
skill: observability-and-metrics
positive_cases:
  - id: missing-latency-metric-on-http-call
    prompt: |
      Review this code:
      <paste code that adds an HTTP fetch without latency capture>
    expected_findings:
      - "missing latency metric"
      - "no percentile buckets"
  - id: free-form-error-message
    prompt: |
      <code that does throw new Error(`failed for ${userId}: ${err.message}`)>
    expected_findings:
      - "high-cardinality error"
control_cases:
  - id: test-fixture-no-instrumentation-needed
    prompt: |
      Review this test fixture:
      <paste test that intentionally has no metrics>
    expected_findings: []
```

Run via:

```bash
python3 .claude/scripts/run-skill-benchmark.py observability-and-metrics
```

The runner is async, deterministic (temp=0), median-of-3, and
reports pass-rate per case + overall.

## Step 6 — Verify governance

```bash
bash .claude/scripts/validate-governance.sh
```

Should pass. The validator checks:

- Skill referenced in team.md exists on disk
- SKILL.md frontmatter parses with required fields
- Skill name in frontmatter matches directory name
- No tier-boundary violation (core skills don't reference
  domain-specific code in their `src/...` examples)

## Step 7 — Verify your skill loads correctly in a spawn

```bash
bash .claude/scripts/inject-agent-context.sh \
  "VP Operations" \
  "review the observability of <path/to/some-service>"
```

The output includes the persona block + your new SKILL.md content +
file assignment placeholder + task. Confirm the skill content is
present and complete.

For native subagents (canonical-5 archetypes), use Format B
reference mode:

```bash
bash .claude/scripts/inject-agent-context.sh \
  "code-reviewer" \
  "review the observability changes in <path>" \
  --mode=reference
```

The reference mode outputs `## SKILL REFERENCE` sentinel with
SHA-256 hash-pin per ADR-051.

## Step 8 — Submit

Two paths:

### A. Adopter-side skill (lives in your project, never upstreamed)

If the skill is specific to your project / domain / company:

1. Place under `.claude/skills/domains/<your-domain>/skills/`
   (NOT under `core/` or `frontend/`, which are the framework's
   namespace).
2. Commit normally; framework upgrades via `upgrade.sh` will not
   touch your domain skills (per ADR-052 §Adopter override
   behavior).

### B. Upstream skill (proposed for inclusion in the framework)

If the skill is universal enough to ship to other adopters:

1. Open a PR against this repo with the SKILL.md + benchmark.
2. CI runs `validate.yml` (governance + tests), `coverage.yml`,
   and the skill benchmark.
3. The PR triggers the skill-patch sentinel chain (`SP-NNN`) per
   ADR-031. The framework Owner signs off; the patch lands under
   the canonical-edit guard.
4. The next MINOR release (per `VERSIONING.md`) ships your skill
   to all adopters.

If your skill could become a new VETO domain (e.g. "PHI handling"
in healthcare, "kill switch" in HFT), discuss the routing change
with the Owner before opening the PR — adding a VETO is a bigger
governance commitment than adding a skill.

## Skill design heuristics (from real PRs that landed and didn't)

### What landed

- **Operational invariants up top.** "After this change, X is true"
  beats "remember to do X".
- **Closed-enum anti-patterns.** A table of named anti-patterns is
  searchable and review-able.
- **Concrete code shapes.** Pseudo-code with the right structure
  beats abstract description.
- **A benchmark from day 1.** A skill with a benchmark gets reviewed
  faster.

### What didn't

- **Skills that paraphrase upstream Anthropic guidance.** Don't
  duplicate Claude best-practice — link to it instead.
- **Skills that pad SKILL.md to look comprehensive.** Reviewers
  delete padding mercilessly. A 100-line skill that says exactly
  what to verify beats a 500-line skill that hedges.
- **Skills with no clear archetype owner.** If no archetype owns
  it, it's not actionable.
- **Skills that overlap an existing skill.** Either extend the
  existing one or carve out a clearly separate scope.

## Reference templates

The cleanest skill examples to crib from:

| Skill | Why it's a good template |
|-------|---------------------------|
| `code-review-checklist` | Severity classification + universal checklist + per-domain checklists |
| `security-and-auth` | Operational invariants up top + concrete pattern recipes + anti-pattern table |
| `testing-strategy` | Patterns + anti-patterns + when-NOT-to-apply section |
| `chaos-and-resilience` | Domain-bounded scope + clear archetype owner |
| `state-machines-and-invariants` | Strong "must be true" invariants section |

Open one of these alongside your new skill and mirror its structure.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Forgot to regenerate inventory | `validate-governance.sh` fails on diff | `bash .claude/scripts/generate-skill-inventory.sh` |
| Description spans multiple lines | YAML parse error | Single paragraph, no line breaks in frontmatter |
| Skill name ≠ directory name | `validate-governance.sh` errors | Make them match (kebab-case both) |
| Skill content too generic | Benchmark scores < 0.6 | Add concrete invariants + anti-patterns |
| Skill ships in `core/` but references domain code | `check-tier-boundaries.py` fails | Move references to `examples/` or to a domain skill |
| Skill PR has no benchmark | Reviewer asks for one | Add `docs/benchmarks/<skill>.yaml`; even one case is enough to start |

## What changes after your skill lands

- It appears in the auto-generated inventory in
  `.claude/skills/core/ceo-orchestration/SKILL.md`.
- The CEO consults it via the routing table when matching work
  types.
- `inject-agent-context.sh` includes it in spawn prompts when the
  archetype is involved.
- `audit_log.py` records `skill: <your-slug>` in every spawn that
  loaded it (`SPEC/v1/audit-log.schema.md` §required fields).
- The skill becomes part of the framework's permanent contract until
  explicitly retired (skill retirement is rare; skills are additive).

## References

- `SPEC/v1/skill-frontmatter.schema.md` — frontmatter contract
- `SPEC/v1/audit-log.schema.md` — `skill` field semantics
- `.claude/skills/core/ceo-orchestration/SKILL.md` — auto-generated inventory
- `bash .claude/scripts/generate-skill-inventory.sh` — inventory regenerator
- `bash .claude/scripts/inject-agent-context.sh` — spawn-prompt builder
- `.claude/team.md` — SKILL MAP + ROUTING TABLE (where to register)
- `docs/CONTRIBUTING.md` — broader contribution conventions

Last reviewed: 2026-04-18 (Session 33 / PLAN-022 Phase 6).
