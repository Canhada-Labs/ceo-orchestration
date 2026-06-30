---
name: core-llm-routing-and-finops
description: LLM routing and cost-governance doctrine for {{PROJECT_NAME}}. Covers
  model-tier floor rules (Opus / Sonnet / Haiku per role), cost-envelope gates, burn-rate
  monitoring, per-plan token budgets, parent-inheritance trap detection, and routing
  decision protocols. Use when authoring a plan, dispatching a sub-agent, estimating
  compute cost for a phase, reviewing token-usage reports, or evaluating tier-policy
  changes. This is the LLM FinOps Architect archetype's operating manual for the
  cognitive layer that complements the mechanical hook check_tier_policy.py
  (ADR-064). Cost is a quality dimension, not a separate concern.
owner: LLM FinOps Architect (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/testing/testing-tool-evaluator.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/engineering/engineering-software-architect.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/specialized/specialized-model-qa.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 5
risk_class: medium
stack: []
context_budget_tokens: 1200
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 7}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: true, priority: 8}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)llm.?routing|finops|token.?budget"}
---

# LLM Routing and FinOps

## Opening commitment

Cost is a quality dimension, not a separate concern. A plan that "works"
but burns ten times the necessary budget has shipped a defect — the
defect happens to live in the dispatch graph rather than in the code,
but it produces the same kind of regret (post-hoc surprise, hard to
reverse, accountable to the same Owner). This skill teaches the LLM
FinOps Architect how to reason about routing choices so cost is treated
as a first-class invariant alongside correctness, security, and
performance.

The rule that anchors everything below: **a wrong-tier dispatch is a
finding with severity equal to the worst case it enables.** Routing
`code-reviewer` to Sonnet on a security-touching diff is not a cost
optimization — it is a CRITICAL governance violation that bypasses
ADR-052's VETO floor. Routing a one-shot fixture generator to Opus is
not safety — it is a MINOR cost finding that, repeated across 30
spawns per session, becomes a MAJOR budget regression.

## What This Skill Is (and isn't)

This skill is the **cognitive layer** for routing and cost decisions.
It complements but does not replace the mechanical enforcement.

| Concern | Mechanism | Layer | Reference |
|---|---|---|---|
| VETO floor for `code-reviewer` / `security-engineer` is hard-pinned to Opus | Canonical agent files (`.claude/agents/<slug>.md`) carry `model: claude-opus-4-8` frontmatter; `check_agent_spawn.py` PreToolUse Agent matcher validates that file at spawn; agent files are canonical-guarded so downgrade requires Owner-signed sentinel; `_lib.agent_frontmatter.VETO_FLOOR_ROLES` + `VETO_FLOOR_MODEL` constants are the shared source of truth; `check_tier_policy.py` (PreToolUse Edit\|Write\|MultiEdit) enforces tier discipline at canonical-edit time | mechanical | ADR-064 §Decisions 2 + ADR-052 §Role-to-model distribution |
| `general-purpose` dispatch sub-agents inherit parent model unless `model:` param set | NO mechanical gate — operator discipline | cognitive (THIS SKILL) | `feedback_subagent_model_routing.md` always-on rule |
| Promote / demote of a role's tier requires statistical power gate (n≥30, gap≥25pp) | `learn.py` aggregator + sigchain + Owner signature | mechanical | ADR-064 §Decisions 3-4 |
| Choosing the right archetype for a task in the first place | Routing decision protocol (see §Routing Decision Protocol below) | cognitive (THIS SKILL) | `.claude/team.md` ROUTING TABLE |
| Per-plan token budget declared in plan frontmatter | `budget_tokens:` field + audit-log roll-up via `/agent budget` | cognitive declaration → mechanical comparison | PLAN-SCHEMA.md + `/agent budget` skill |
| Burn-rate monitoring during a long session | Operator math + audit-log query | cognitive (THIS SKILL) | Google SRE Handbook ch. 4 + 5 |

The skill does NOT:

- Override `VETO_HARDCODE` (anyone proposing to do so writes an ADR
  amendment first; the SKILL body documents that this is the doctrine,
  not the policy artifact).
- Replace the tier-policy CLI / artifact (`ceo-tier-policy` per
  ADR-064). That tool is the empirical learning loop; this skill is the
  reasoning playbook agents use when authoring plans, dispatching
  workers, and reviewing budget regressions.
- Decide pricing for a SaaS LLM provider. The skill consumes the public
  Anthropic price card (ADR-052 §Cost magnitude) and updates when the
  card changes. New providers require a new skill or extension.

## Model Tier Floor (Hard Rules)

The framework runs Opus, Sonnet, and Haiku in defined roles. The floor
rules below are non-negotiable without an Owner-signed ADR amendment.
"Floor" = minimum acceptable model; an explicit upgrade is always
allowed, an explicit downgrade is not.

### The full role-to-model floor table

| Role / archetype | Model floor | Tier-policy enforcement | Rationale | Reference |
|---|---|---|---|---|
| `code-reviewer` | `claude-opus-4-8` (HARDCODE) | Agent file frontmatter (canonical-guarded edit) + `check_agent_spawn.py` Agent-matcher validation + `_constants.VETO_HARDCODE` shared constant + `check_tier_policy.py` Edit\|Write\|MultiEdit matcher for canonical-edit tier discipline | Merge VETO — false negative ships a bug; ADR-058 adversarial framing demands strongest reasoning | ADR-052 §Role-to-model · ADR-064 §Decisions 2 |
| `security-engineer` | `claude-opus-4-8` (HARDCODE) | Same multi-layer defense as code-reviewer (agent-file-frontmatter + agent-spawn-validate + tier-policy-canonical-edit) | Auth/crypto VETO — missed attack surface = incident; same-LLM-bias mitigation requires Opus floor | ADR-052 · ADR-064 |
| `vp-engineering` / `architect` / debate Round N synthesizer | `claude-opus-4-8` (advisory floor) | Operator discipline (no mechanical hook) | L3+ multi-step reasoning; cross-archetype synthesis | `team.md` §Backend archetypes · ADR-058 |
| `incident-commander` (Wave 1c) | `claude-opus-4-8` (advisory floor) | Operator discipline (Wave 1c VETO_FLOOR_ROLES expansion candidate) | Live-incident cognitive load; coordination across 3+ archetypes; calibration against under-call risk | PLAN-074 mechanism-selection §2 |
| `identity-trust-architect` (Wave 1c) | `claude-opus-4-8` (advisory floor) | Operator discipline (Wave 1c VETO_FLOOR_ROLES expansion candidate) | Authentication / session / trust-boundary architecture is VETO-adjacent — a wrong call cascades to security incidents | PLAN-074 mechanism-selection §10 |
| `llm-finops-architect` (Wave 1c) | `claude-sonnet-4-6` (default) — Opus only when adversarial / governance-critical | NO VETO-floor (cost ≠ security per Wave 1c matrix); operator discipline | This skill's own loader. Cost analysis is bounded, doctrine-anchored work; Sonnet matches Opus quality on per-plan budget reasoning. Escalate to Opus only when the analysis turns adversarial (e.g., tournament-evidence dispute, post-incident burn-rate forensics) — name the escalation reason in the dispatch prompt | PLAN-074 mechanism-selection §3 · `wave-1c-veto-floor-matrix.md` (Owner ratified `llm-finops-architect = NO`) |
| `qa-architect` — adversarial / mutation / regression | `claude-opus-4-8` | Operator discipline | Adversarial test design demands strongest reasoning even when nominally non-VETO | `feedback_subagent_model_routing.md` |
| `qa-architect` — fixture generation / mechanical enumeration | `claude-sonnet-4-6` | Operator discipline | Bounded mechanical work; Sonnet matches Opus quality | `feedback_subagent_model_routing.md` |
| `performance-engineer` — architecture / trade-off | `claude-opus-4-8` | Operator discipline | Cross-cutting reasoning | `feedback_subagent_model_routing.md` |
| `performance-engineer` — measurement / profiling | `claude-sonnet-4-6` | Operator discipline | Mechanical metric extraction | `feedback_subagent_model_routing.md` |
| `devops` — CI/CD / workflows / hardening | `claude-sonnet-4-6` | Operator discipline | Security surface non-trivial; Haiku evidence absent | ADR-052 originally mapped Haiku, lifted to Sonnet floor by `feedback_subagent_model_routing.md` empirical evidence |
| `financial-correctness` / `monetization-and-billing` | `claude-opus-4-8` | Operator discipline (financial VETO-eligible per Owner directive) | Monetary correctness; same severity as security VETO | `feedback_subagent_model_routing.md` |
| `compliance-lgpd` / `dpo-reporting` | `claude-opus-4-8` | Operator discipline (legal VETO-eligible) | Legal liability surface; redaction correctness | `feedback_subagent_model_routing.md` |
| `state-machines-and-invariants` / `data-schema-design` | `claude-opus-4-8` | Operator discipline | Migration risk; correctness-critical | `feedback_subagent_model_routing.md` |
| `chaos-and-resilience` / `public-api-design` | `claude-sonnet-4-6` | Operator discipline | Bounded design surface | `feedback_subagent_model_routing.md` |
| `growth-and-launch` / `product-conversion-readiness` | `claude-sonnet-4-6` | Operator discipline | Content-heavy, marketing prose | `feedback_subagent_model_routing.md` |
| `terse-mode` / `observability-and-ops` (listings) | `claude-sonnet-4-6` | Operator discipline | Mechanical aggregation | `feedback_subagent_model_routing.md` |
| `general-purpose` — PoC reproducer / mechanical script | `claude-sonnet-4-6` | Operator discipline (CRITICAL: parent-inheritance trap, see §Anti-Patterns) | Bounded; Haiku not yet tournament-validated for this profile | `feedback_subagent_model_routing.md` empirical S79+S80 |
| `general-purpose` — anything else | `claude-sonnet-4-6` MINIMUM (Opus when in doubt) | Operator discipline | Default-safe upgrade; Haiku NEVER without empirical tournament evidence | `feedback_subagent_model_routing.md` + ADR-063 |
| Any archetype lacking a row above | `claude-sonnet-4-6` | Operator discipline pending tournament | Fallback floor; promote to Opus for any VETO-adjacent work | ADR-063 §Tournament-driven default |

### Three rules of the floor

1. **Haiku is allowed only with empirical tournament evidence**
   (n≥30/cell, gap≥25pp, statistical power per ADR-064 §Decisions 3).
   "I think Haiku will be fine" is not evidence. The current
   tournament corpus does not yet validate Haiku for any archetype in
   the framework — Sonnet is the lowest tier in active use as of
   v1.14.0.
2. **Upgrades are free; downgrades require ceremony.** Routing a
   `qa-architect` mechanical task to Opus is wasteful but legal.
   Routing a `code-reviewer` named-archetype dispatch to Sonnet is
   blocked at the agent-file boundary: `.claude/agents/code-reviewer.md`
   declares `model: claude-opus-4-8` and Claude Code substitutes that
   model at spawn — overriding requires editing the canonical agent
   file, which is sentinel-guarded. Attempting the same downgrade from
   a `general-purpose` rail (where no agent file resolves the role) is
   not pre-blocked by any current hook — it is a CRITICAL audit-log
   retrospective finding, and a known governance gap when MCP custom
   tools route around the standard `Agent` matcher (see
   `feedback_custom_mcp_tools_governance_gap.md`).
3. **VETO floor is a sentinel, not a default.** When the floor table
   above lists a model for a role, that is the *minimum*. The CEO MAY
   route any role to Opus; the CEO MAY NOT route a `claude-opus-4-8`
   row to anything below Opus without an Owner-signed ADR amendment.

### What "advisory floor" means versus "HARDCODE"

- **HARDCODE** = three-layer mechanical defense (constants module +
  apply.py independent literal + PreToolUse hook). Bypass requires
  modifying canonical-guarded files with an Owner GPG sentinel and an
  ADR amendment. Currently: `code-reviewer` and `security-engineer`
  only.
- **Advisory floor** = operator discipline plus audit-log retroactive
  detection. Bypass produces no PreToolUse block but DOES produce a
  retrospective finding when the audit-log query notices a wrong-tier
  spawn for that role. The Wave 1c VETO-adjacent roles
  (`incident-commander`, `identity-trust-architect`,
  `threat-detection-engineer`) are advisory-Opus in v1.14.0 and
  candidates for HARDCODE promotion in a future ADR amendment.
  `llm-finops-architect` is NOT VETO-adjacent (cost ≠ security per
  `wave-1c-veto-floor-matrix.md`) — it defaults to Sonnet, escalates
  to Opus only on adversarial dispatches.

## Cost-Envelope Gates

Every plan declares a token budget and is monitored against burn rate
during execution. Cost is the third leg of the iron triangle alongside
correctness (test gates) and time (calendar buffer).

### Per-plan budget declaration

Plans declare in frontmatter:

```yaml
---
id: PLAN-NNN
budget_tokens: 1_500_000   # total expected (CEO + sub-agent fan-out)
budget_usd_estimate: 8.50  # informational; computed from tokens × tier mix
calendar_buffer_days: 0    # default; non-zero requires ADR cite per
                           # feedback_calendar_gates_invented.md
---
```

The `budget_tokens` field is a contract with the Owner. Crossing it
mid-plan triggers an escalation (see §Escalation thresholds). Plans
without a budget field default to a `BLOCKED` review verdict from the
LLM FinOps Architect at Phase 0 — the absence of the number is the
finding.

### Burn-rate math (Google SRE Handbook ch. 5)

Burn rate translates token consumption into "fraction of budget per
unit of progress." It is the single most actionable metric during long
sessions.

```
burn_rate = (tokens_consumed_so_far / budget_tokens) /
            (work_completed_fraction)
```

Where `work_completed_fraction` is the ratio of completed phases /
checkpoints to the plan total. A burn rate > 1.0 means the plan is
projected to overshoot; > 2.0 means the plan is projected to consume
twice its budget at completion.

The Google SRE escalation thresholds adapt directly:

| Burn rate | Window | Action |
|---|---|---|
| ≥ 14.4× over 1h window | Fast-burn — operator pauses, re-estimates, may abort phase | Page-equivalent: surface to Owner immediately |
| ≥ 6× over 6h window | Medium-burn — operator escalates at next phase boundary | Ticket-equivalent: log in plan body §Cost-overrun; CEO summarizes at Phase wrap |
| ≥ 1.5× over 24h window | Slow-burn — flag at session closeout | Memory note: append to `project_current_state.md` |
| < 1.0× sustained | Healthy | Continue; consider tightening budget for similar future plans |

**Why these thresholds:** the framework treats budget exhaustion the
same way an SRE treats SLO error-budget exhaustion — finite resource,
multi-window detection, asymmetric responses keyed to the time scale
of the leak. The structure (multi-window + multi-burn-rate alerting)
is adapted from Google's SRE Workbook ch. "Alerting on SLOs"
(https://sre.google/workbook/alerting-on-slos/). The specific
14.4× / 6× / 1.5× ratios paired with 1h / 6h / 24h windows are the
**framework's adapted internal thresholds** for per-plan token-budget
burn — calibrated to wall-clock cadence of CEO sessions, not lifted
verbatim from any single Workbook example. Adopters MAY tune these
ratios per project (document the override in plan body §Cost-overrun).

### Escalation thresholds (concrete actions)

When burn rate fires:

1. **Fast-burn (≥14.4× / 1h)** — CEO halts the next dispatch. Operator
   updates the plan body with a `## Budget overshoot — pause` block
   citing the specific tokens-consumed / fraction-completed numbers,
   pings Owner via the natural session pause, and proposes one of:
   trim scope, re-route to lower tier where compatible with floor
   table, abort phase.
2. **Medium-burn (≥6× / 6h)** — CEO continues but notes the burn at
   the next phase boundary in the plan body. Re-estimates remaining
   phases at observed cost-per-phase, not the original budget's
   cost-per-phase.
3. **Slow-burn (≥1.5× / 24h)** — CEO flags at session closeout in
   the CHANGELOG entry ("plan ran ~Nx over budget; cause: ..."). No
   mid-session interruption; this is post-hoc tuning data.

### Token accounting per tier (for budget estimation)

From ADR-052 §Cost magnitude (public Anthropic price card, valid
2025-2026; refresh on every ADR-064 amendment):

| Model | Input $/M tokens | Output $/M tokens | vs Opus baseline |
|---|---|---|---|
| Opus 4.8 | $5 | $25 | 1.0× |
| Sonnet 4.6 | $3 | $15 | 0.6× |
| Haiku 4.5 | $1 | $5 | 0.2× |

Output tokens dominate for reasoning workloads (5× the input rate);
input tokens dominate for read-heavy / context-loading workloads.
Estimate accordingly:

- **Reasoning-heavy plan** (debate rounds, synthesizer turns, long
  CEO turns): assume output ≈ 30% of total tokens, input ≈ 70%.
  Effective $/M ≈ `0.7 × $input + 0.3 × $output` ≈ `$3.5 + $7.5`
  ≈ `$11/M Opus` / `$6.6/M Sonnet` / `$2.2/M Haiku`.
- **Mechanical-fanout plan** (fixture generation, file scaffolding,
  search-and-replace): assume output ≈ 10% of total. Effective
  $/M ≈ `$7 Opus` / `$4.2 Sonnet` / `$1.4 Haiku`.

Mixed-tier plans use a weighted average. A 200k-Opus + 200k-Sonnet +
100k-Haiku reasoning-heavy plan estimates at:

```
0.20M Opus   × $11/M  = $2.20   (200k reasoning-heavy)
0.20M Sonnet × $6.6/M = $1.32   (200k)
0.10M Haiku  × $2.2/M = $0.22   (100k)
                        ------
                        $3.74 / 500k tokens = $0.00748 per kilo-token
```

A pure-Opus version of the same plan: `500k × $11/M = $5.50`.
The mix-and-floor savings on this 500k plan are ~32% versus pure Opus
(down from ~52% at Opus-4.7 rates) — Opus 4.8's compressed price ladder
shrinks the gain from moving work off Opus. Most of the remaining
savings of ADR-052's multi-model dispatch come from the high-frequency
mechanical fan-out NOT counted in the 500k figure.

## Routing Decision Protocol

Use this flowchart before EVERY dispatch. Every step has a default
that errs on the side of the floor table; every override requires
named justification.

```
START dispatch decision
  │
  ├─ Q1. Is the role on the VETO_HARDCODE table (code-reviewer,
  │      security-engineer)?
  │      ├─ YES → model = "opus" (hard-pinned; hook will block any
  │      │       attempt at downgrade — no override path exists in
  │      │       v1.14.0).
  │      └─ NO  → continue
  │
  ├─ Q2. Is the role on the advisory-floor table for Opus
  │      (vp-engineering, architect, incident-commander,
  │      identity-trust-architect, threat-detection-engineer, the
  │      financial / compliance / state-machines / data-schema
  │      cluster)?  Note: llm-finops-architect is NOT on this list
  │      — it defaults to Sonnet per Wave 1c matrix.
  │      ├─ YES → model = "opus" by default. Downgrade to Sonnet
  │      │       requires THREE conditions met (see §Sonnet-downgrade
  │      │       carve-out below) AND named in the dispatch prompt.
  │      └─ NO  → continue
  │
  ├─ Q3. Is the work adversarial / multi-step / cross-cutting
  │      (debate Round N, mutation testing, novel test design,
  │      architectural trade-off, root-cause analysis)?
  │      ├─ YES → model = "opus". Adversarial reasoning is
  │      │       Opus-floor regardless of nominal archetype.
  │      └─ NO  → continue
  │
  ├─ Q4. Is the work bounded / mechanical / well-scoped (fixture
  │      generation, file scaffolding, lint fixes, search-and-replace,
  │      mechanical enumeration, profile data extraction)?
  │      ├─ YES → model = "sonnet". Sonnet handles bounded work at
  │      │       Opus quality, ~1.7× cost reduction (Opus 4.8).
  │      └─ NO  → escalate to Opus default; bounded-mechanical claim
  │              requires explicit scope statement.
  │
  ├─ Q5. Has the candidate Haiku tier been tournament-validated for
  │      THIS task type (n≥30, gap≥25pp per ADR-064 §Decisions 3)?
  │      ├─ YES → model = "haiku" allowed.
  │      └─ NO  → Haiku FORBIDDEN. Fall back to Sonnet.
  │
  └─ DISPATCH with explicit `model:` parameter — NEVER omit it.
     Omitting `model:` triggers parent inheritance per
     `feedback_subagent_model_routing.md` and silently routes
     general-purpose dispatches to the CEO's tier (almost always
     Opus, almost always wrong).
```

### Sonnet-downgrade carve-out for advisory-floor roles

The advisory-floor Opus default may downgrade to Sonnet ONLY when ALL
three of these hold:

- The work is bounded (one specific output artifact, scope ≤ 200 lines
  of code or ≤ one document).
- The work is non-adversarial (no debate Round N, no mutation testing,
  no security review, no cross-archetype synthesis).
- The dispatch prompt explicitly names the carve-out: `Downgrade
  rationale: <one sentence; cite the specific bounded scope>`.

A dispatch that fails any of the three rolls back to Opus default. The
named-rationale requirement prevents drift from "we'll downgrade when
it's clearly OK" to "we'll downgrade when we feel like saving money,
which is always" — a pattern the framework has documented before
under feedback_calendar_gates_invented.md (different domain, same
operator-drift mechanism).

## WRONG / CORRECT Examples

Six dispatch scenarios. Each pair shows the violation and the
corrected form. The pattern is always: name the role, name the work,
name the model, name the rationale.

### Example 1 — Parent inheritance trap (the most common bug)

```python
# WRONG — no model param, sub-agent silently inherits CEO Opus
Agent({
    subagent_type: "general-purpose",
    description: "Generate test fixtures for the new endpoint",
    prompt: "PERSONA: QA Architect ..."
})
# Effect: Sonnet-floor mechanical work routed to Opus. ~1.7× cost at
# Opus 4.8 (was ~5× at Opus-4.7). S80 empirical (4.7 rates) measured
# ~$15-20/session wasted; materially less at Opus 4.8.
```

```python
# CORRECT — explicit model param
Agent({
    subagent_type: "general-purpose",
    model: "sonnet",  # MANDATORY — bounded fixture generation
    description: "Generate test fixtures for the new endpoint",
    prompt: "PERSONA: QA Architect ...\n"
            "Work scope: bounded mechanical enumeration; Sonnet floor."
})
```

### Example 2 — Code-reviewer downgrade attempt (mechanical defense via agent file)

```python
# WRONG — code-reviewer is VETO_FLOOR_ROLES + VETO_HARDCODE
Agent({
    subagent_type: "code-reviewer",
    model: "sonnet",  # ← OPERATOR-supplied; does NOT itself drive the hook
    description: "Review the new auth handler"
})
# Effect: When subagent_type resolves to .claude/agents/code-reviewer.md,
# Claude Code uses THAT file's `model: claude-opus-4-8` frontmatter — the
# operator's `model: "sonnet"` argument is overridden by the agent file
# (or rejected as inconsistent, depending on Claude Code's resolution
# semantics in the current version). The agent file is canonical-guarded,
# so downgrading the VETO floor requires:
#   1. Editing .claude/agents/code-reviewer.md (sentinel-required)
#   2. ADR amendment to ADR-052 §VETO_FLOOR_ROLES
#   3. Owner GPG sentinel signing the canonical edit
# A reviewer who attempted this dispatch from a `general-purpose` rail
# (where no agent file resolves the archetype) gets a CRITICAL audit
# finding retrospectively when the audit-log query flags the wrong-tier
# claim.
```

```python
# CORRECT — Opus floor honored
Agent({
    subagent_type: "code-reviewer",
    model: "opus",
    description: "Review the new auth handler",
    prompt: "PERSONA: Staff Code Reviewer ..."
})
```

### Example 3 — Mechanical work over-routed to Opus

```python
# WRONG — Opus default for purely mechanical search-and-replace
Agent({
    subagent_type: "general-purpose",
    model: "opus",
    description: "Rename `tier_policy` to `tier_policy_cli` across staging"
})
# Effect: ~1.7× over-spend on bounded mechanical work at Opus 4.8
# (was ~5× at Opus-4.7). MINOR finding;
# repeated across a session, becomes MAJOR.
```

```python
# CORRECT — Sonnet for bounded mechanical
Agent({
    subagent_type: "general-purpose",
    model: "sonnet",
    description: "Rename `tier_policy` to `tier_policy_cli` across staging",
    prompt: "Bounded scope: literal symbol rename. Stop after files in "
            "staging/ subtree are renamed and tests still import."
})
```

### Example 4 — Advisory-floor Opus role downgraded without carve-out

```python
# WRONG — incident-commander is advisory Opus floor; downgrade
# without naming the three-condition carve-out
Agent({
    subagent_type: "general-purpose",
    model: "sonnet",
    description: "Triage the production incident",
    prompt: "PERSONA: Incident Commander ..."
})
# Effect: incident triage is multi-archetype synthesis (sec + perf +
# devops coordination). Sonnet floor here is operator drift; not
# mechanically blocked but produces a retroactive audit finding.
```

```python
# CORRECT — Opus floor honored for incident triage
Agent({
    subagent_type: "general-purpose",
    model: "opus",
    description: "Triage the production incident",
    prompt: "PERSONA: Incident Commander ...\n"
            "Tier rationale: live-incident multi-archetype synthesis; "
            "Opus floor per llm-routing-and-finops §Model Tier Floor."
})
```

### Example 5 — Speculative Haiku without tournament evidence

```python
# WRONG — Haiku without empirical evidence
Agent({
    subagent_type: "general-purpose",
    model: "haiku",
    description: "Summarize the audit log into a CHANGELOG entry"
})
# Effect: silent quality regression. Haiku has not been tournament-
# validated (ADR-063) for any archetype in v1.14.0. Even mechanical
# summarization showed >25pp gap in the last evaluation pass.
# CRITICAL finding: speculative cost optimization.
```

```python
# CORRECT — Sonnet floor (the lowest validated tier in v1.14.0)
Agent({
    subagent_type: "general-purpose",
    model: "sonnet",
    description: "Summarize the audit log into a CHANGELOG entry",
    prompt: "Bounded scope: CHANGELOG summary; Sonnet floor per "
            "llm-routing-and-finops §Model Tier Floor (Haiku not "
            "tournament-validated)."
})
```

### Example 6 — Plan with no budget declared

```yaml
# WRONG — plan frontmatter without budget
---
id: PLAN-NNN
status: draft
related_adrs: [ADR-052]
---
```

```yaml
# CORRECT — plan with budget envelope and calendar buffer rationale
---
id: PLAN-NNN
status: draft
related_adrs: [ADR-052, ADR-064]
budget_tokens: 1_500_000
budget_usd_estimate: 8.50
calendar_buffer_days: 0   # vibecoder-only per ADR-096; no soak window
                          # required absent external adopters
tier_mix_estimate:
  opus: 0.40   # CEO + debate Round N + 2 VETO-floor archetypes
  sonnet: 0.60
  haiku: 0.0   # Baseline 0% — tournament evidence absent in v1.14.0;
               # raise to >0 ONLY if a per-archetype tournament citation
               # is included in tier_mix_rationale below.
tier_mix_rationale: |
  CEO turns + debate synthesis = Opus.
  Fixture generation + observability listings + llm-finops-architect = Sonnet.
  Haiku share: 0% in baseline (no tournament evidence yet);
  reserved for post-PLAN-077 when bench corpus validates.
---
```

## Anti-Patterns

Six recurring failure modes the LLM FinOps Architect blocks at Phase
0 plan review. Each anti-pattern has been observed in a recorded
session; the remediation is the named control, not a vibe.

### A1. The "all-Opus by default" reflex

**Symptom:** every dispatch, regardless of work shape, is routed to
Opus because "Opus is safest." The CEO never reaches into Sonnet
even for bounded mechanical work.

**Why it happens:** the operator conflates "VETO-floor" with "default
for everything." The floor table specifies a *minimum* for specific
roles, not a *default for all roles*.

**Cost:** session burn rate higher than necessary. At Opus 4.8 the
all-Opus-vs-per-role gap is ~14% per session — the ~$7.50→~$3.63 / 500k
"~52% reduction" this guidance used to cite was at Opus-4.7 rates and no
longer holds (Opus 4.8 sits close to Sonnet). The bigger wins now come
from cache + skill-reference discipline, with zero quality regression on
VETO gates; see docs/cost-of-operation.md.

**Remediation:** the routing decision protocol §Q4 — bounded
mechanical work routes to Sonnet by default. The CEO that defaults
to Opus everywhere is in violation of ADR-052 even if no individual
dispatch is wrong.

### A2. The "all-Haiku savings hunt"

**Symptom:** the operator notices Haiku is 5× cheaper than Opus and
attempts to route everything Haiku can possibly handle to Haiku.

**Why it happens:** cost-card pricing is so asymmetric that the
operator over-weights the cost dimension and under-weights quality.

**Cost:** quality regression on tasks where Haiku has not been
tournament-validated. The empirical n=20 matrix (PLAN-060 S62) showed
that on tasks LSe than n≥30/cell power, Haiku surfaced silent quality
regression in ~12% of cases — not a session-killing rate, but each
miss carries the cost of a re-do plus the original Haiku spend.

**Remediation:** routing decision protocol §Q5 — Haiku is FORBIDDEN
for any task without a tournament-validated row. Sonnet is the
lowest tier in active framework use as of v1.14.0.

### A3. The parent-inheritance trap (most common bug)

**Symptom:** dispatches via `subagent_type: "general-purpose"` omit
the `model:` parameter. The sub-agent silently inherits whatever the
parent CEO is running (almost always Opus 4.8).

**Why it happens:** the dispatch ergonomics make `model:` look
optional. The mitigated rail (ADR-082) routes around the H4 anomaly
by collapsing all custom-archetype dispatches to `general-purpose`,
losing per-archetype model routing in the process.

**Cost:** S79+S80 audit-log analysis (at Opus-4.7 rates) showed 21 of
26 spawns over a 30-day window were Opus-by-inheritance, ~$15-20 USD per
session wasted on bounded mechanical fan-out that should have been
Sonnet. At Opus 4.8 the same misrouting wastes materially less — Opus is
only ~1.7× Sonnet, not ~5× — but the routing discipline still matters.

**Remediation:** `feedback_subagent_model_routing.md` is an always-on
rule. EVERY dispatch via `general-purpose` MUST set `model:`
explicitly. The LLM FinOps Architect's Phase 0 review checks for this
in the plan's dispatch graph.

### A4. The "future-proofing" bigger-model creep

**Symptom:** an archetype's floor is raised to Opus on the rationale
that "the next iteration will need it anyway."

**Why it happens:** the operator anticipates future scope expansion
and pre-pays for headroom that may never materialize.

**Cost:** sustained over-spend on every dispatch of that archetype
until the future scope arrives (which it often doesn't, or arrives
in a different shape that doesn't actually need Opus).

**Remediation:** floor changes go through ADR amendments. "We MIGHT
need it" is not amendment-grade evidence; tournament data with
n≥30/cell IS. The LLM FinOps Architect rejects floor-raise proposals
that lack empirical justification.

### A5. The missing-budget plan

**Symptom:** a plan ships with no `budget_tokens:` field in
frontmatter, or with a clearly-vibecoded round number ("1M tokens
should be enough").

**Why it happens:** operator skips estimation because "the work is
hard to predict" — which is true, AND not a reason to skip.

**Cost:** no detection mechanism for budget overshoot until session
closeout, by which point a 5× overshoot is sunk cost. Pre-ADR-064 the
framework had no budget gate at all and saw recurring 2-3× plan
overshoots.

**Remediation:** plan-frontmatter check at draft-review enforces
`budget_tokens:` presence. Estimation rubric in §Token accounting per
tier above. A round-number budget without tier-mix breakdown gets a
MAJOR finding, not a pass.

### A6. The model-mismatch for VETO-adjacent work

**Symptom:** an advisory-floor VETO-adjacent role (incident-commander,
identity-trust-architect, threat-detection-engineer) is routed to Sonnet
on a piece of work that, on inspection, is structurally adversarial.
Note: `llm-finops-architect` is **NOT** VETO-adjacent (cost ≠ security per
`wave-1c-veto-floor-matrix.md`) — its Sonnet default is correct, not a
downgrade; escalate to Opus for adversarial dispatches via named-reason
prompt only.

**Why it happens:** the operator confuses "advisory floor = optional"
with "advisory floor = downgrade-by-default." Advisory floor means
the *minimum*; downgrade requires the §Sonnet-downgrade carve-out
three-condition gate.

**Cost:** silent quality regression on VETO-adjacent reasoning. The
framework documents this for `code-reviewer` historically (Round-23
phantom-approval rate ~35% pre-PLAN-058); the same shape applies to
advisory-floor archetypes whose work is adversarial-without-being-
nominally-VETO.

**Remediation:** the routing protocol §Sonnet-downgrade carve-out is
a three-condition AND gate. Failing any one of the three rolls back
to the Opus floor. Named-rationale dispatch prompts make the
deviation auditable post-hoc.

## Acceptance Criteria

What the LLM FinOps Architect's Phase 0 plan review checks before
issuing `APPROVED` on a plan that has dispatch implications:

1. **Plan frontmatter declares `budget_tokens:`** with a non-round-
   number estimate AND a `tier_mix_estimate` block decomposing the
   budget across Opus / Sonnet / Haiku shares. Round-number budgets
   without breakdown = MAJOR finding.
2. **Every dispatch in the plan body cites a model justification**
   in the prompt (one line; references the floor table row OR the
   §Sonnet-downgrade carve-out three-condition gate). Missing
   justification = MAJOR finding for VETO-floor and advisory-floor
   roles, MINOR finding for general-purpose mechanical work.
3. **Burn-rate measurement points are scheduled** at the plan's
   phase boundaries. Plans that span > 4 hours without an interim
   burn-rate check = MINOR finding (process debt; will become MAJOR
   if the plan overshoots).
4. **No Haiku dispatch without a tournament-evidence citation** —
   reference to a tournament report ID + cell n + gap_pp. Haiku
   without citation = CRITICAL finding (speculative cost optimization
   = quality regression in disguise).
5. **All `code-reviewer` and `security-engineer` dispatches use Opus.**
   For named-archetype dispatches, this is enforced via the canonical
   agent file's `model: claude-opus-4-8` frontmatter (which Claude Code
   substitutes at spawn) plus `check_agent_spawn.py` validating that
   frontmatter against `_lib.agent_frontmatter.VETO_FLOOR_MODEL`; the
   agent file is canonical-guarded so downgrade requires Owner GPG
   sentinel + ADR amendment. `check_tier_policy.py` enforces tier
   discipline on canonical-edit operations (Edit\|Write\|MultiEdit) — it
   is the file-edit-time defense, NOT a dispatch-time gate. Finding a
   plan that routes these archetypes to a non-Opus model = either the
   author has misunderstood the floor, the dispatch came from a
   `general-purpose` rail (not pre-blocked but caught retrospectively),
   or an MCP-tool bypass per `feedback_custom_mcp_tools_governance_gap.md`.
   Either way, BLOCKER finding.
6. **Per-archetype model param is explicit operator discipline on every
   dispatch via `general-purpose`.** Omission = MAJOR finding by the
   always-on rule `feedback_subagent_model_routing.md`, detected
   **retrospectively via audit-log query** — there is no current
   PreToolUse mechanical gate on Agent dispatches that inspects the
   structured `model` field. The framework's tier-policy enforcement
   uses two distinct mechanisms:

   - **Named-archetype dispatches** (`subagent_type: "code-reviewer"`,
     `subagent_type: "security-engineer"`, etc.): the model floor is
     enforced by the AGENT FILE FRONTMATTER. `check_agent_spawn.py`
     (registered PreToolUse matcher `Agent`) validates that
     `.claude/agents/<slug>.md` declares `model: claude-opus-4-8` (and,
     post-Wave-1c, `veto_floor: true`). Because agent files are
     canonical-guarded (sentinel-required edit), an attempt to
     downgrade a VETO-floor archetype's model requires Owner-signed
     ADR amendment + sentinel ceremony. **The dispatch's literal
     `model:` argument does NOT itself participate in the hook decision
     — Claude Code substitutes the agent file's model at runtime.**
   - **`general-purpose` dispatches** (no agent file resolves the
     archetype): the operator's `model:` argument is the only signal
     the framework gets. There is no mechanical PreToolUse gate that
     reads this field today; enforcement is **operator discipline +
     audit-log retrospective detection** (the wrong-tier dispatch
     surfaces post-hoc when an audit-log query notices a CEO-claimed
     archetype role with a Sonnet/Haiku floor where Opus was required).

   `check_tier_policy.py` is registered against `Edit|Write|MultiEdit`
   only and enforces tier discipline at canonical-edit time — it does
   NOT fire on Agent dispatches.

   The Agent tool accepts the shorthand values `"sonnet" | "opus"
   | "haiku"` (per Claude Code CLI). The tier-floor table above lists
   canonical IDs (`claude-sonnet-4-6` / `claude-opus-4-8` /
   `claude-haiku-4-5-20251001`) because that is the value that ends up
   in agent files + audit log. Examples in this skill use shorthand
   (matches actual dispatch syntax). A dispatch missing the structured
   `model:` field on a `general-purpose` call silently inherits the
   parent model (parent-inheritance trap, ADR-082) — this is the
   single largest source of wrong-tier audit findings in S79+S80.

   **Future hardening (out of scope for Wave 1b):** a PreToolUse mechanical
   gate that inspects `model:` on `general-purpose` dispatches against
   the description-extracted archetype claim is a candidate for a
   future ADR + plan. Until that ships, treat Hard Rule 6 as advisory
   + retrospective.
7. **Calendar-buffer days are 0 OR cite a specific ADR / mechanical
   gate.** Generic "soak window" / "best practice" / "settle period"
   = MAJOR finding per `feedback_calendar_gates_invented.md`. The
   framework is vibecoder-only per ADR-096; absent external adopters,
   no calendar buffer is justified by default.
8. **Cost-overrun escalation is named.** The plan body specifies
   what the operator does at each burn-rate threshold (fast / medium
   / slow) so the response is encoded BEFORE the burn rate fires,
   not improvised under pressure.

A plan failing any of 1, 2, 4, 5, 6 holds `BLOCKED`. A plan failing
3, 7, or 8 holds `APPROVED WITH CONDITIONS` — the conditions being
the missing artifacts plus a named owner and trigger that closes
each one.

## Related Skills

- `core/architecture-decisions` — when a new tier-policy rule
  introduces a hook change, an ADR amendment is required (ADR-064
  §Open items). The LLM FinOps Architect coordinates with VP
  Engineering on amendments.
- `core/incident-management` — the incident-commander archetype is
  advisory Opus floor. Cost reasoning during a live incident is
  secondary; quality reasoning dominates. This skill is the cost-
  reasoning manual that complements the incident manual.
- `core/code-review-checklist` — dispatch-graph review at Phase 0 is
  a structural code review; the same severity rubric applies. A
  parent-inheritance bug in a plan's dispatch graph is a MAJOR
  finding even though no source code is involved.
- `core/security-and-auth` — security-engineer role is HARDCODE
  Opus floor (ADR-052 + ADR-064). This skill states the rule; that
  skill states the work the rule applies to.
- `core/observability-and-ops` — burn-rate measurement consumes
  the audit-log query results; that skill teaches the listing
  conventions, this skill teaches the math.

## References

- `.claude/adr/ADR-052-multi-model-dispatch-by-role.md` — original
  per-role dispatch decision; tier mapping; cost magnitude card.
- `.claude/adr/ADR-064-dynamic-tier-policy-learned-dispatch.md` —
  policy artifact + statistical power gate + sigchain + 3-layer
  VETO defense + this skill's cost-envelope rules link back here.
- `.claude/adr/ADR-063-agent-eval-empirical-dispatch-validation.md` —
  empirical evidence pipeline that feeds the tier-policy learner.
- `.claude/adr/ADR-082-l7c-mitigation-default-on.md` — why
  general-purpose dispatch is the rail of choice; explains the
  parent-inheritance trap mechanism.
- `.claude/adr/ADR-096-vibecoder-only-by-design.md` —
  why calendar-buffer days default to 0; absence of external
  adopters removes the soak-window justification.
- MEMORY rule `feedback_subagent_model_routing.md` — always-on
  rule that the LLM FinOps Architect references at every plan
  review and every dispatch.
- MEMORY rule `feedback_calendar_gates_invented.md` — always-on
  rule that prevents speculative calendar-buffer inflation.
- MEMORY rule `feedback_custom_mcp_tools_governance_gap.md` —
  why the HARDCODE floor still has a known bypass via custom MCP
  tools (gap closure pending pre-MCP-wiring ADR amendment).
- Google SRE Handbook ch. 5 §Multi-Window, Multi-Burn-Rate Alerts —
  the source of the 14.4× / 6× / 1.5× thresholds adapted to
  per-plan token budgets.
- `.claude/scripts/tier_policy_cli/` — the operational tooling
  package this skill's doctrine governs (CLI: `ceo-tier-policy
  derive | apply | verify | rotate | migrate | sigchain-rotate`
  + 5 more sub-commands per ADR-064).
- `.claude/hooks/check_agent_spawn.py` — PreToolUse Agent-matcher
  hook that validates agent file frontmatter against
  `VETO_FLOOR_ROLES` + `VETO_FLOOR_MODEL` at spawn time.
- `.claude/hooks/check_tier_policy.py` — PreToolUse
  Edit\|Write\|MultiEdit matcher that enforces tier-policy at
  canonical-edit time (does NOT fire on Agent dispatches).
- `/agent budget` skill — token-rollup query for any plan or
  time window; the burn-rate math above consumes its output.
