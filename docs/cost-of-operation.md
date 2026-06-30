# Cost of Operation

> What does it cost to run a project under `ceo-orchestration`?
> Spoiler: less than running an unstructured Claude Code session
> for the same work, because per-role model dispatch puts the cheap
> models on high-frequency fan-out and saves the expensive model for
> orchestration + critical VETOs.

## TL;DR — order of magnitude

A typical session that produces one PR-ready change with a code
review + security check + tests:

| Configuration | Per session | Per 50 sessions/month | Per 200 sessions/month |
|---------------|-------------|------------------------|-------------------------|
| **All-Opus** baseline (`CEO_MULTIMODEL_ENABLE=0`) | ~$1.23 | ~$62 | ~$246 |
| **Per-role dispatch** (genuine, all native) | ~$1.06 | ~$53 | ~$212 |
| **+ Cache hit** (warm gate-1, ~30% multi-turn savings) | ~$0.75 | ~$37 | ~$148 |
| **Mitigated rail default-on** (ADR-082, actual default) | ~$1.23 | ~$62 | ~$246 |

Computed at **Opus 4.8 ($5/$25 per Mtok)** — the current default-CEO /
VETO model. Note the "Mitigated rail default-on" row lands at **≈ the
all-Opus baseline**: under ADR-082, 4 of the 5 canonical archetypes
inherit the Opus CEO model, so the genuine per-role split (~$1.06) is
only realised if you disable mitigation. Numbers are rough. Real usage
varies by skill mix, plan complexity,
and how many debates you trigger. Use the
[`ceo-cost.py`](#measuring-cost) tool to measure your actual spend
on your audit log instead of trusting these estimates.

## ⚠ Mitigated dispatch — Opus rate inheritance disclosure (audit-v2 C3-P0-03)

> **PLAN-044 audit-v2 Wave B disclosure.** The "Per-role dispatch"
> row above assumes ADR-052 §Role-to-model distribution applies
> uniformly. **It does not at v1.11.0.** The actual default cost is
> closer to the new "Mitigated rail default-on" row.

Per **ADR-082** (PLAN-061 default-on, accepted 2026-04-27), only
**1 of the 5 canonical archetypes runs on the native rail** at
default settings: `code-reviewer`. The other 4 (`qa-architect`,
`performance-engineer`, `security-engineer`, `devops`) default
to **mitigated dispatch** — the harness re-routes the Task call
through `subagent_type=general-purpose` with the role's persona
injected via `## SKILL CONTENT`.

**Cost consequence:** the `general-purpose` sub-agent **inherits
the CEO model**, which is **Opus 4.8 by default** (not the
Sonnet/Haiku that ADR-052 maps these roles to). Every
`qa-architect / performance-engineer / security-engineer / devops`
spawn therefore bills at **Opus rates ($5/$25 per Mtok)**, not
the **$3/$15 Sonnet rates** suggested by the ADR-052 policy table.

A representative session that would cost ~$1.06 under genuine per-role
dispatch lands at ~$1.23 under the v1.11.0 default because ~75% of the
spawn fan-out routes through Opus by inheritance — and at Opus 4.8 the
Opus/Sonnet gap is small ($5/$25 vs $3/$15), so the inheritance penalty
is now modest (~16%, not the ~60% it was at Opus-4.7 rates).

### Why ADR-082 ships this default

The H4 rail anomaly (ADR-080) found that only `code-reviewer`
spawns are reliable on the native rail. Other archetypes empirically
exhibit higher fabrication rates on the native rail in some
release-channel + model combinations. ADR-082 trades cost for
correctness on those 4 archetypes by default.

### Override — restore native rail to all archetypes

```bash
# Force native rail for ALL archetypes (full ADR-052 honored).
# Cost reverts to ~$1.06/session; correctness reverts to whatever
# the H4 rail anomaly produces in your release channel.
export CEO_MITIGATION_DISABLE=1
```

Or per-spawn via the dispatcher CLI:

```bash
.claude/scripts/inject-agent-context.sh --dispatch=native qa-architect "<task>"
```

See `docs/CEO-MITIGATION-DISPATCH.md` for the full routing rule
and ADR-082 for the empirical rationale.

### What `code-reviewer` does

`code-reviewer` runs natively + at **Opus 4.8 by policy** (ADR-052
VETO floor), not by inheritance. The cost there is identical
under either rail. Only the other 4 canonicals see the Opus-by-
inheritance surprise.

## Inputs to the cost model

### Anthropic public pricing (2025-2026)

| Model | Input ($/M tokens) | Output ($/M tokens) | vs Opus 4-8 |
|-------|--------------------|----------------------|-------------|
| `claude-opus-4-8` (current flagship) | $5.00 | $25.00 | 1.0× |
| `claude-opus-4-7` (historical — retained for log replay) | $15.00 | $75.00 | 3.0× |
| `claude-sonnet-4-6` | $3.00 | $15.00 | 0.6× |
| `claude-haiku-4-5-20251001` | $1.00 | $5.00 | 0.2× |

Live-confirmed 2026-05-29 from https://www.anthropic.com/api (Opus 4.8 = $5/$25, Sonnet 4.6 = $3/$15, Haiku 4.5 = $1/$5). The prior Haiku row ($0.25/$1.25) propagated a stale rate from ADR-052 §Cost magnitude and underpriced Haiku 4x. Adopters with their own contractual
pricing should override the table via `CEO_PRICING_PATH=<json>` —
the `_lib/adapters/live/_cost.py` resolver picks it up.

### Per-role distribution (ADR-052 default)

| Agent | Model | Why |
|-------|-------|-----|
| **CEO orchestrator** (you, the chat session) | Opus 4.8 | Long context, L3+ decisions, debate synthesis |
| **code-reviewer** | Opus 4.8 | Merge VETO — false negative ships a bug |
| **security-engineer** | Opus 4.8 | Auth/crypto VETO — missed attack surface = incident |
| **qa-architect** | Sonnet 4.6 | Edge-case enumeration; bounded work; cost 0.6× vs Opus 4.8 |
| **performance-engineer** | Sonnet 4.6 | Metric analysis; deterministic; cost 0.6× vs Opus 4.8 |
| **devops** | Haiku 4.5 | Config edits + boilerplate; high-freq + low-novelty; cost ~5× cheaper than Opus 4.8 |

Domain agents (e.g. fintech `financial-correctness-and-math`) inherit
the CEO model unless the project's `team-personas.md` specifies a
`model:` override.

### Cache behavior

The gate-1 boot ceremony (CLAUDE.md + PROTOCOL.md + team.md +
frontend-team.md + ceo-orchestration SKILL.md) is **~44,786 tokens**.
Anthropic prompt caching gives ~90% read discount for cached prefix
on subsequent turns within the 5-minute TTL.

| Scenario | Cost impact |
|----------|-------------|
| First turn of a session (cold) | Full price for gate-1 boot |
| Subsequent turns within 5 min | ~90% savings on cached prefix (the gate-1 boot fits the cache window) |
| Cache miss (TTL expired or gate-1 invalidated) | Full price again |

**The cache discipline rule** (CLAUDE.md §0): never edit gate-1
files mid-session. Each mid-session edit costs ~44,786 tokens
re-charge on the next turn. See `docs/opus-4-7-operations.md` §2 for
the full discipline.

PLAN-020 Phase 6 measured **97.14% spawn-prompt savings** when
using `## SKILL REFERENCE` (Format B) vs inline `## SKILL CONTENT`
(Format A) on the canonical-5 archetypes. Replay benchmark fixture:
`replay-fixtures/plan-019-wave-2a.jsonl`. The 97.14% is an upper
bound; real workloads include ~10ms sub-agent Read cost + ~50
protocol tokens, so attribute "≥ 75% savings" in production.

## Per-session breakdown (typical CEO + canonical-5 work)

A representative session that produces one PR with code review +
security check + a test:

| Phase | Agent | Model | Tokens (in/out) | $ |
|-------|-------|-------|------------------|----|
| Gate-1 boot | CEO | Opus 4.8 | 27.3k / 0.5k | $0.15 |
| Plan + 1 spawn (turns 2-5) | CEO | Opus 4.8 | 30k / 5k | $0.28 |
| code-reviewer review | code-reviewer | Opus 4.8 | 8k / 3k | $0.12 |
| security-engineer audit | security-engineer | Opus 4.8 | 6k / 2k | $0.08 |
| qa-architect tests | qa-architect | Sonnet 4.6 | 12k / 5k | $0.11 |
| performance-engineer check | performance-engineer | Sonnet 4.6 | 5k / 1.5k | $0.04 |
| devops CI tweak | devops | Haiku 4.5 | 8k / 2k | $0.018 |
| CEO synthesis + commit drafting | CEO | Opus 4.8 | 25k / 6k | $0.28 |
| **Total** | | | | **~$1.06** |

(The `devops` row is $0.018, not the $0.005 shown before PLAN-130 —
that stale figure used the pre-PLAN-120 Haiku rate of $0.25/$1.25;
the live rate is $1/$5.)

Compare with **all-Opus** (every spawn forced into Opus 4.8 via
`CEO_MULTIMODEL_ENABLE=0` — the 3 cheap-model rows re-priced at Opus):

| Phase | Tokens (in/out) | $ |
|-------|------------------|----|
| Same workflow | Same | ~$1.23 |

That's only **~14% savings** from per-role dispatch alone — down from
the ~48% this doc claimed at Opus-4.7 rates. The margin collapsed
because Opus 4.8 ($5/$25) sits close to Sonnet ($3/$15): moving
`qa-architect` / `performance-engineer` off Opus now saves ~40% on
those rows, not the ~80% it saved at 4.7. **Cache** (~30% on multi-turn
sessions) and **skill-reference** token savings are unchanged and now
dominate the framework's cost advantage — see below.

> **Measured anchor (this framework's own dogfood).** `python3
> .claude/scripts/ceo-cost.py --since 30d --by-model` on this repo's
> audit log reports **$1.68 across 26 spawns** at Opus 4.8 rates (18
> Opus-4.8 / 2 Sonnet / 1 Haiku / 5 pre-ADR-052 untagged). Caveat: the
> framework is meta-work (governance plumbing), not representative app
> coding — the figure validates the *pricing math* (the Haiku row bills
> at $1/$5, e.g. $0.0078 for 1,565 output tokens), not the per-session
> *shape* above. Measure your own spend rather than trusting the
> illustrative table.

## Measuring cost

### Real-time per-session check

```bash
python3 .claude/scripts/ceo-cost.py --since 1h --by-model
```

Reads your `~/.claude/projects/<slug>/audit-log.jsonl` and aggregates
`tokens_in` / `tokens_out` per `model` field. Output:

```
since=1h  by_model

model                              spawns   in_tokens  out_tokens   cost_usd
claude-opus-4-8                         3      45,000       9,000     $0.45
claude-sonnet-4-6                       2      17,000       6,500     $0.15
claude-haiku-4-5-20251001               1       8,000       2,000     $0.018
                                        6      70,000      17,500     $0.62

ok
```

### Monthly rollup

```bash
python3 .claude/scripts/ceo-cost.py --since 30d --by-day
```

### JSON for monitoring

```bash
python3 .claude/scripts/ceo-cost.py --since 30d --format json | \
  jq '.totals.cost_usd'
```

Wire that into your monitoring dashboard for a continuous spend
signal.

### Honest limitation

The `tokens_*` fields in the audit log are populated by the
PostToolUse hook from Anthropic's `usage_metadata`. Three states
exist (per ADR-016):

| State | What `ceo-cost.py` does |
|-------|--------------------------|
| Field present + integer | Sum into totals |
| Field absent (pre-ADR-016 emitter) | Counted under `spawns_without_tokens` warning |
| Field present + null (modern emitter, unknown response) | Counted under `spawns_without_tokens` warning |

If `spawns_without_tokens > 0`, the cost estimate has a known lower
bound; the actual cost may be higher. The script emits a warning
banner in that case. Real cost from your Anthropic console is
authoritative.

## Cost kill switches

| Switch | Effect | Trade-off |
|--------|--------|-----------|
| `CEO_MULTIMODEL_ENABLE=0` | Force all canonical-5 into Opus 4.8 | +16% cost; recovers PLAN-020 baseline behavior. Use when you specifically need stronger reasoning across the board. |
| `CEO_SOTA_DISABLE=1` | Disable ALL PLAN-020/021 features (native subagents + skill reference + multi-model) | +100% cost (everything in Opus + inline prompts). Emergency fallback only. |
| `CEO_NATIVE_SUBAGENTS=0` | Force inline (custom) rail; native subagents off | Modest cost increase; loses ADR-050 benefits. |
| `CEO_SKILL_REFERENCE_MODE=0` | Force `## SKILL CONTENT` inline; disables Format B | Loses 97.14% spawn-prompt savings (PLAN-020 Phase 6). |

The kill-switch matrix is documented in
`docs/opus-4-7-operations.md` §Kill-switch precedence. The defaults
(`=1` everywhere) are the cheapest configuration that preserves
governance.

## Cost vs no-framework Claude Code

A "naive" Claude Code session without `ceo-orchestration` for the
same work would typically:

- Run all turns in Opus 4.8 (no per-role split) → +16% cost
- Re-include skill content in every spawn (no caching of references) → +60% per-spawn token cost
- Re-derive the team structure each session (no gate-1 stable cache) → +20% per-session cost

In practice, a `ceo-orchestration`-equipped session ends up costing
**~55-75% of the equivalent ad-hoc session** while producing
governance-traceable output. With Opus 4.8's compressed price ladder
the savings now come mostly from **cache + skill-reference token
discipline** (per-role dispatch alone is only ~14%) — discipline, not
magic. You still pay for the work, just less of it goes to the most
expensive model.

## Budget guardrails (optional)

If you want hard budget caps:

1. **Per-spawn cap** — `check_budget.py` rejects spawns whose
   estimated token cost exceeds the per-spawn limit (default 50k
   input). Override via `CEO_BUDGET_PER_SPAWN=<int>` or bypass via
   `CEO_BUDGET_BYPASS` (Owner-only, audit-logged via
   `budget_bypass_used` event).
2. **Per-plan cap** — same hook tracks running totals per
   `plan_id`. `budget_exceeded` event fires when crossed.
3. **Predictive budget** — `python3 .claude/scripts/budget-summary.py
   --plan PLAN-NNN` projects expected cost using Bayesian buckets
   from past plans of similar shape (ADR-047). Output banded as
   "$50-$100 (medium confidence)" not raw figures.

The budget infrastructure is opt-in and shipped fail-open by default
to avoid blocking sessions on infra heuristics. Adopters who need
hard caps configure them explicitly.

## Adopter cost expectations

For a real adopter (a single engineer using Claude Code as their
daily driver via `ceo-orchestration`):

| Usage pattern | Sessions/week | Approx monthly $ (USD) |
|---------------|---------------|--------------------------|
| Light (1-3 sessions/day, ~5 min each) | ~20 | ~$20 |
| Moderate (5-10 sessions/day, ~15 min each) | ~50 | ~$70 |
| Heavy (continuous use, multi-hour sessions) | ~100 | ~$290 |
| Team-of-3 sharing the framework | ~150 | ~$480 |

These are illustrative estimates at **Opus 4.8 rates** (≈40% of the
Opus-4.7-era figures this table used to show). Your mileage will
vary based on how many debates you run (debates = N parallel Opus
spawns, so they scale cost fastest) and how often the canonical-5 are
involved (critical-path code = more spawns). Measure with `ceo-cost.py`
rather than trusting the band.

## When the per-role split is wrong for you

If your work has any of these properties, override the defaults:

| Situation | Override |
|-----------|----------|
| Greenfield novel design needing strongest reasoning everywhere | `CEO_MULTIMODEL_ENABLE=0` (all-Opus); accept the +16% cost |
| Mostly DevOps + boilerplate; rare cross-cutting decisions | Edit canonical-5 frontmatter to push more agents to Haiku; preserve `code-reviewer` + `security-engineer` on Opus (always) |
| Deeply specialized domain (finance, medicine) where domain experts beat generalist Opus | Author domain personas with explicit `model:` field; bypass the canonical-5 split for that domain only |
| Cost-sensitive R&D with regression test coverage as safety net | Reduce CEO model to Sonnet via Claude Code's model picker; keep canonical-5 split for VETO quality |

The default split is calibrated for "general engineering work where
quality regressions are expensive". If your work has a different
cost/quality trade-off, override consciously.

## References

- ADR-052 — multi-model dispatch by role (the cost analysis)
- `docs/opus-4-7-operations.md` — operations guide (cache discipline + kill switches)
- `SPEC/v1/audit-log.schema.md` v2.7 + v2.8 — `tokens_*` + `model` field semantics
- `_lib/adapters/live/_cost.py` — cost resolver implementation
- `benchmarks/replay.py` + `replay-fixtures/plan-019-wave-2a.jsonl` — replay benchmark for spawn-prompt savings

Last reviewed: 2026-06-05 (Session 212 / PLAN-130 — full Opus 4.8 recompute: per-session table, TL;DR, and savings narrative restated ~48%→~14%; Haiku per-session row bug fixed $0.005→$0.018; "vs Opus" baseline column renormalised to 4.8; S211 staleness banner retired; measured `ceo-cost.py` anchor added). Prior review: 2026-05-29 (PLAN-120 WS-C pricing-currency refresh — Haiku 4.5 corrected to $1/$5; claude-opus-4-8 $5/$25 added as current flagship).
