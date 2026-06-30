# Opus 4.7 operations playbook (PLAN-020 Phase 3 + Phase 4)

> **Audience:** CEO orchestrating ceo-orchestration framework on Opus 4.7
> (or downstream Anthropic models with similar adaptive-thinking +
> prompt-cache semantics).
>
> **Status:** Initial v1, Session 32 2026-04-17. Updated as production
> usage in 42ledger reveals new patterns.
>
> **Companion docs:**
> - `docs/opus-4-7-baseline.md` — Phase 0 baseline measurements
> - `docs/opus-4-7-phase6-report.md` — Phase 6 acceptance vs baseline
> - `ADR-050` — native subagents dual-rail
> - `ADR-051` — skill-by-reference expanded trust boundary

---

## §1. Effort matrix (Phase 3)

Opus 4.7 has adaptive thinking that consumes thinking-tokens
proportional to perceived task complexity. The framework gives the CEO
a 4-tier `/effort` slash command to bias the thinking budget. Use it
deliberately.

| Tier | When to use | Examples |
|------|-------------|----------|
| **`/effort low`** | Single-file edits, config tweaks, typo fixes | `fix typo in CLAUDE.md`; `bump VERSION to 1.5.0`; `add missing trailing newline` |
| **`/effort default`** | L2 multi-file contained work (DEFAULT — no slash needed) | `add a test for build_event v2.7`; `update task-chains.yaml`; `refactor one helper` |
| **`/effort high`** | L3+ multi-module, ADR decisions, debate rounds, security-domain work | `debate PLAN-020 round 2`; `design ADR-052`; `execute Phase 1 native subagents migration` |
| **`/effort max` + `ultrathink`** | Cross-cutting redesign, sprint planning, release-gate decisions | `plan Sprint 22`; `tag v2.0`; `respond to security incident postmortem` |

### When NOT to use

- **Inside spawn prompts** — REJECTED by `check_agent_spawn.py
  ::_has_effort_token`. Sub-agents inherit Anthropic default thinking
  budget. The CEO sets effort on its own driving turn; the spawned
  agents react.
- **Inside test-runner commands** — `/effort` only applies to LLM
  reasoning, not subprocess execution.
- **As a reflex** — escalating to `/effort high` for everything
  defeats the purpose. Default is the default.

### Drift-reset recipe (Performance Unseen #2)

Opus 4.7 adaptive thinking has a context-weight feedback loop. After
several `/effort high` turns in sequence, thinking-tokens-per-turn
trends upward even on simple tasks (the model "remembers" recent
high-effort context and assumes the next turn is similar).

Mitigation: between two `/effort high` blocks, insert a reset turn:

- **Option A (preferred):** `/clear` — drops conversation history,
  full reset. Use at session boundaries OR when switching domains.
- **Option B (lighter):** insert a synthetic `/effort low` turn (e.g.
  "list current branch" or any trivial query). Re-anchors the model
  to default budget without losing context.

Phase 0 item 2 (thinking-budget regression probe) will measure the
slope; if positive, this recipe is enforced via PROTOCOL.md amendment.

---

## §2. Cache discipline (Phase 4)

Anthropic's prompt cache has a 5-minute TTL. Cache hit cost is ~1/10
the cost of a cache miss. The framework's Gate-1 files are cache-
stable across sessions IFF not edited mid-session.

### Rule 1 — Gate files immutable mid-session

Do NOT edit `CLAUDE.md`, `PROTOCOL.md`, `.claude/team.md`,
`.claude/frontend-team.md`, or `.claude/skills/core/ceo-orchestration/
SKILL.md` during the working portion of a session.

**Exception:** the `closeout` ceremony at session end MAY edit
`CLAUDE.md` §6 (Current Work) + §CHANGELOG. This is the explicit
escape valve. Document the closeout in the commit message.

**Why:** any edit to these files invalidates the prompt cache for the
entire session, costing the gate-boot tokens (~44,786 estimated) on
the very next turn.

> **1M-window recalibration (2026-06-15, PLAN-137 A4).** The ~44,786
> gate-boot figure is an *absolute* token count over the actual Gate-1
> files (4-char/token heuristic, `docs/opus-4-7-baseline.md`) — it is
> the **same in any window** and is NOT a 200k-era number. What the 1M
> window changes is the *fraction*: ~44.8k is ≈22% of a 200k window but
> only ≈4.5% of a 1M window. The discipline therefore re-anchors on the
> **cache-COST** axis (a miss re-bills ~44.8k input at the full rate),
> NOT on context-pressure — at 1M the gate prefix no longer crowds the
> working budget, so do not treat "I'm low on context" as the reason to
> avoid mid-session Gate-1 edits. The reason is dollars-per-miss, and
> that reason is window-independent.

### Rule 2 — Prefer longer sessions over many short ones

A 2-hour session with warm cache is materially cheaper than 4× 30-min
sessions with 4× cold boots. Anthropic cache TTL is **5 minutes** —
gap-free session time is what matters. A coffee break > 4 min risks
cache eviction.

**Operational:**
- Don't context-switch mid-task; finish or checkpoint first.
- If you must step away > 4 min, expect cache miss on return; budget
  accordingly.
- Use `/loop` with a timer for genuinely-recurring work (keeps cache warm).

### Rule 3 — Parallel spawns same turn

Debate round-N spawns issued in the SAME turn (parallel `Task` tool
calls) hit cache 1× (shared system prompt context). 3 agents in 3
sequential turns with user turns in between may hit cache 3× IF TTL
expired between turns.

**Operational:**
- Issue debate-round agents as parallel `Task` calls in a single turn.
- Issue verification agents (Code Reviewer + Security + QA) in a single
  turn after implementation.
- Avoid the pattern: "spawn one, wait for response, spawn next"
  unless dependencies require sequence.

### Sub-session gap measurement

Phase 0 item 8 captures `python3 -c 'pass'` floor (~23ms p50). Phase
0 future enhancement: histogram of time-between-user-turns from audit
log. If P50 gap > 4 min, Rule 2 violation is the dominant cost driver
and Phase 4 Rule 2 enforcement becomes "first thing to fix."

---

## §2-bis. Model distribution strategy (PLAN-021 ADR-052)

PLAN-021 introduces **per-role model dispatch** for the 5 canonical-5
native subagents. Opus 4.7 stays locked on the orchestrator (main
CEO thread — this conversation). Spawned canonical-5 workers dispatch
to Sonnet or Haiku per role, with critical VETO holders preserved
in Opus.

### Role-to-model distribution

| Agent slug | Model | Role criticality | Rationale |
|-----------|-------|------------------|-----------|
| `code-reviewer` | **Opus 4.7** | CRITICAL (merge VETO) | False negative ships a bug. Strongest reasoning justified. |
| `security-engineer` | **Opus 4.7** | CRITICAL (auth/crypto VETO) | Attack surface miss = incident. Strongest reasoning mandatory. |
| `qa-architect` | **Sonnet 4.6** | IMPORTANT | Edge-case enumeration + test design. Sonnet matches Opus on bounded work. |
| `performance-engineer` | **Sonnet 4.6** | IMPORTANT | Metric analysis + bottleneck ID. Deterministic; Sonnet excellent. |
| `devops` | **Haiku 4.5** | HIGH-FREQUENCY | Config edits + boilerplate + lint fixes. Low novelty; Haiku 10× faster + 60× cheaper. |

### Cost math (Anthropic public pricing 2025-2026)

| Model | Input $/M | Output $/M | vs Opus |
|-------|-----------|------------|---------|
| Opus 4.7 | 15 | 75 | 1.0× |
| Sonnet 4.6 | 3 | 15 | 0.2× |
| Haiku 4.5 | 0.25 | 1.25 | 0.017× |

Typical 500k-token session all-Opus ≈ $7.50. Post-dispatch ≈ $3.63 →
**~52% cost reduction** with zero regression on security + code review
gates.

### Opt-in / opt-out (ADR-052 §Kill switches)

- **Default (CEO_MULTIMODEL_ENABLE unset):** multi-model ACTIVE.
- **Opt-out:** `export CEO_MULTIMODEL_ENABLE=0` — all canonical-5 spawns
  inherit CEO model (all-Opus fallback, PLAN-020 baseline).
- **Master kill:** `export CEO_SOTA_DISABLE=1` — overrides everything;
  all PLAN-020 + PLAN-021 features OFF; custom rail + inline only.

### Adopter override per agent

Edit `.claude/agents/<slug>.md` frontmatter `model:` field. Framework
upgrade via `scripts/upgrade.sh` preserves adopter overrides (checks
file diff before replacing; backups in `.claude-upgrade.bak/`).

Example — force `devops` into Opus for a high-assurance context:

```yaml
---
name: devops
description: ...
version: anthropic-subagent-v1
tools: [Read, Grep, Glob, Bash]
model: claude-opus-4-7    # was: claude-haiku-4-5-20251001
---
```

### Future model-family bump (Opus 5 / Sonnet 5 / Haiku 5)

ADR-052 §Model ID bump process specifies a 4-step recipe:

1. Benchmark new model on `.claude/plans/PLAN-020/rubrics/` archetype
   rubrics. Pass rate ≥ current baseline.
2. Run `benchmarks/replay.py` on `plan-019-wave-2a.jsonl` fixture.
   Spawn-prompt delta must not regress.
3. Author ADR-NNN referencing ADR-052 + benchmark evidence.
4. Update frontmatter `model:` fields per agent + audit-log schema
   bump if new `usage_metadata` fields.

No silent in-place upgrades. Every model-family bump is gated by
benchmark + ADR.

### Audit-log trail (v2.8)

`audit-log.jsonl` captures the `model` field per spawn entry (ADR-052
additive schema). Enables forensic correlation: if a Sonnet-routed
review misses a bug in production, query:

```bash
.claude/scripts/audit-query.py spawn-history --model claude-sonnet-4-6 --recent 50
```

to see which spawns used the questionable rail. Superior to black-box
routing frameworks that don't expose model choice.

## §2-tris. Per-plan token budget doctrine (1M window — PLAN-137 A4)

> **Recalibrated 2026-06-15 (PLAN-137 item A4).** The compaction
> triggers and per-plan `budget_tokens:` bands below were authored in
> the 200k-context era and silently carried forward. They are now
> rescaled to the **1M context window** that Opus 4.6/4.7/4.8, Sonnet
> 4.6, and Fable 5 all expose. Haiku 4.5 is the exception — its window
> is **200K, not 1M** — so Haiku-tier arcs keep the 200K-era ceiling
> (see multiplier #1 below). This section is **doctrine only**: it does
> NOT change `check_budget.py`. That hook's caps
> (`DEFAULT_MAX_PLAN_TOKENS = 1_000_000`, `MAX_TOKENS_CEILING =
> 10_000_000`) are already 1M-correct and stay untouched — they are
> retrospective State-0 advisory and never block.

### Pricing-gate precondition — GREEN

Rescaling a per-plan budget band upward is only safe if the larger
window bills at the **same per-token rate** — a band raised on a wrong
pricing assumption silently lets a run burn many× the intended budget.

**As of 2026-06-15 that gate is GREEN.** Anthropic prices the full 1M
window at the flat standard rate for every current-generation CEO-tier
model — there is **no long-context (>200K) premium**. The dated, sourced
confirmation artifact is `docs/provider-pricing.md` → section
**"Long-context (1M window) pricing — premium check"** (live-verified
2026-06-15 against `https://platform.claude.com/docs/en/about-claude/pricing`).
Do not rescale these bands again on a future model bump without
re-confirming that section is still GREEN.

### Recalibrated compaction triggers

Autocompact urgency scales with the working window, not the absolute
prefix. In the 200k era a plan crossing ~150-300k was already
"autocompact likely"; in a 1M window that same plan occupies ≈15-30% and
is comfortable. New trigger doctrine (×5 the old thresholds, mirroring
the 200k→1M window ratio):

| Signal | 200k-era threshold (old) | 1M-window threshold (new) | Rationale |
|---|---|---|---|
| "Plan is getting large — consider a checkpoint" | ~150k | **~750k** | Same ~15% window fraction; the soft nudge fires at the same *proportion* of the window. |
| "Autocompact likely this session — split or summarize" | ~300k | **~1.5M → cap at the 1M window** | At 1M, a single session physically cannot exceed the window, so the real signal is "approaching the 1M ceiling" (≥~850k working tokens), i.e. plan to checkpoint before the hard wall rather than before a phantom 300k autocompact. |
| "Multi-session — split across sessions up front" | >500k | **>1.5M** (i.e. genuinely exceeds one 1M window) | A plan whose honest estimate exceeds one full window must be decomposed; below ~1M it fits one warm session. |

> One-line takeaway: the 200k-era "300k = autocompact" reflex is **stale
> in a 1M window**. Don't pre-emptively compact a 300k plan — at 1M it
> is a Small/Medium arc with ~700k of headroom.

### Recalibrated per-plan `budget_tokens:` bands

These are the planning bands the CEO uses to answer "does this fit one
session?" (the `plan-tokens.py` / `budget_tokens:` doctrine, ADR-081
§Session capacity reference). The old bands were a 200k-window ladder;
the 1M ladder ×5's each rung (the gate-boot ~44.8k prefix is now a
rounding error against the rung sizes, so it drops out of the band math):

| Tier | 200k-era range (old) | 1M-window range (new) | Risk / guidance |
|---|---|---|---|
| Trivial | <50k | **<250k** | low — single warm session, no checkpoint needed |
| Small | 50-150k | **250-750k** | low — one session |
| Medium | 150-300k | **750k-1M** | medium — one session but checkpoint before the 1M wall |
| Large | 300-500k | **1M-1.5M** | high — split into 2 sessions (exceeds one window) |
| Multi-session | >500k | **>1.5M** | high — decompose into ≥2 plans up front |

> **Rationale (one line per rescale):** each rung is the old rung ×5,
> the same multiple as the 200k→1M window growth, so a plan that was
> "Medium / fits one session" stays "Medium / fits one session" in
> absolute *fraction-of-window* terms — the doctrine's meaning is
> preserved, only the raw token numbers move with the window.

> **ADR-081 cross-reference (do NOT edit ADR-081 from here).** The
> canonical session-capacity table lives in `ADR-081` §"Session capacity
> reference (Opus 4.7, 1M context)". Its rows still read the 200k-era
> ladder (Trivial <50k … Multi-session >500k) and its Large-tier note
> "(autocompact likely)" at 300-500k is a 200k-era artifact. ADR-081 is
> canonical-guarded; this doc is the **operational** rescale and ADR-081
> should be amended at a future closeout/ADR-bump to match these rungs.
> Until then, when the two disagree, **these 1M bands are the live
> doctrine** and ADR-081's numbers are the grandfathered legacy.

### Three non-classic spend multipliers the band doctrine MUST honor

The flat-rate gate covers the classic >200K *context* premium (gone).
It does NOT cover these three, each of which multiplies spend at 1M
scale (kept in sync with `docs/provider-pricing.md` → Long-context
section, multipliers 1-3):

1. **Haiku 4.5 window = 200K, not 1M.** A 1M-token plan band cannot be
   applied to a Haiku-tier arc — over-200K requests on Haiku **error**
   rather than over-bill. Cap Haiku budgets at its real **200K** window.
   (This is why "200K" still appears legitimately in the doctrine.)
2. **Fast mode (Opus-only premium lane).** The fast-mode premium applies
   across the full window, including requests over 200K input. Opus
   4.6/4.7 fast = $30/$150 (6× base); Opus 4.8 fast = $10/$50 (2× base).
   A 1M run under fast mode multiplies hard — budget it as
   `base × fast-factor`. (Fast mode is not available with the Batch API,
   and the framework routes nothing through it today; see
   `docs/provider-pricing.md` → "Fast mode" section.)
3. **`inference_geo:"us"` data residency = 1.1×** on all token
   categories (Opus 4.6 / Sonnet 4.6 and later). Default global routing
   bills at standard rates.

> **Net for the band doctrine:** budget a 1M-token plan as
> `tokens × base rate`, then layer the 1.1× (US residency) or the
> fast-mode factor **only if** those flags are set. There is no surprise
> >200K tier underneath, so the upward rescale of the bands above is safe
> on the flat-rate assumption, conditional on these three multipliers.

## §3. Spawn rail selection

PLAN-020 Phase 1 + Phase 2 introduced two spawn formats:

| Format | When to use | Cost |
|--------|-------------|------|
| **`## SKILL CONTENT` (inline)** | Non-canonical archetype OR adopter-authored persona OR skill body small (<2 KB) | Full skill body in every spawn prompt; no Read tool call needed |
| **`## SKILL REFERENCE` (PLAN-020 Phase 2)** | Canonical-5 archetype (code-reviewer, security-engineer, qa-architect, performance-engineer, devops) OR skill body large (>5 KB) | ~96 bytes for sentinel; sub-agent does 1 Read tool call (~10ms + 50 protocol tokens); but cache amortization is much better |

**Default:** the `inject-agent-context.sh` helper picks `inline` unless
`--mode=reference` is passed.

**For canonical-5 archetypes:** always pass `--mode=reference`. Phase
2 measurement projects ~25.2% per-spawn savings.

**For non-canonical archetypes (frontend leads, domain specialists,
ad-hoc):** keep `inline` until the archetype skills stabilize + are
Owner-signed.

**Kill switches:**
- `CEO_SOTA_DISABLE=1` — master kill, forces `inline` always
- `CEO_SKILL_REFERENCE_MODE=0` — disable reference mode specifically
- `CEO_NATIVE_SUBAGENTS=0` — disable native rail dispatch

---

## §4. Working with `/effort` and the spawn protocol together

Common workflow for L3+ work (e.g. PLAN-020 itself):

```
[CEO turn — /effort high]
1. Read CLAUDE.md, PROTOCOL.md, plan
2. Decide which agents to spawn
3. Issue parallel Task calls (5 native agents in 1 turn)

[Wait for all responses — same turn]

[CEO turn — /effort high]
4. Synthesize agent outputs
5. Decide adjustments
6. Update plan / write code / commit
```

**Anti-pattern:**

```
[CEO turn — /effort low]  ← wrong for L3+ work
1. Spawn 1 agent
[wait]
[CEO turn — /effort low]  ← still wrong
2. Spawn next agent based on first
[wait]
...
```

This sequential pattern:
- Loses cache amortization (2× the spawn cost)
- Underbuds CEO's own thinking on L3 task
- Adds wall-clock latency from sequential dependency

---

## §5. Quick reference card

```
SCENARIO                          | EFFORT  | RAIL
---------------------------------|---------|----------
fix typo                         | low     | inline
add 1 test                       | default | inline
refactor 3 files                 | default | inline
spawn 1 code reviewer            | default | reference (canonical-5)
debate round (5 agents parallel) | high    | reference (all canonical-5)
design new ADR                   | high    | inline (CEO-direct, no spawn)
plan a sprint                    | max     | (no spawn yet — plan first)
respond to security incident     | max     | inline (CEO acts directly)
```

---

## §6. Verification + drift detection

The framework instruments + verifies these rules:

- **`check_agent_spawn.py::_has_effort_token`** — rejects `/effort`
  in spawn prompts (Phase 3 enforcement).
- **`audit_log.py` v2.7** — captures `usage_metadata.thinking_tokens`
  per turn, enabling drift regression analysis.
- **`docs/opus-4-7-baseline.md`** — baseline measurements.
- **`docs/opus-4-7-phase6-report.md`** — pre-vs-post Phase 6 numbers.
- **`profile-opus-4-7.py --smoke`** — CI gate, runs every PR.

If you observe perceived slowness or unexpected token costs, the first
diagnostic is:

```bash
# Pull recent audit-log entries with cache info
.claude/scripts/audit-query.py spawn-history --recent 20 --include cache_coverage,thinking_tokens
```

If `cache_coverage` < 0.6 or `thinking_tokens` per turn trends up, you
have a real cache or drift problem. Otherwise it's perception.
