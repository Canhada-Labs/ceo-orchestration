---
name: parallelization-by-default
description: Detect decomposable tasks and dispatch <=6 sub-agents in parallel. Mandatory primitive per Owner velocity thesis. Activates when CEO would otherwise sequentially execute work a Sonnet/Haiku sub-agent could do equally well. Future canonical at .claude/skills/core/parallelization-by-default/SKILL.md.
owner: CEO (primitive — applies framework-wide)
domain: core
priority: 2
risk_class: low
context_budget_tokens: 3500
inactive_but_retained: false
repo_profile_binding:
  frontend:
    active: true
    priority: 2
  engine:
    active: true
    priority: 2
  fintech:
    active: true
    priority: 2
  trading-readonly:
    active: true
    priority: 2
  generic:
    active: true
    priority: 2
activation_triggers:
  - event: spawn-requested
  - event: plan-opened
  - event: session-boot
  - event: help-me-invoked
audit_action: parallelization_recommended
audit_volume_budget_per_hour: 50
---

# Parallelization By Default

> Velocity primitive. Mandatory under Owner thesis
> `feedback_owner_velocity_thesis.md`: *"sub-agent dispatch mandatory when CEO
> would do work a sub-agent does equally well."* Sequential CEO Opus execution
> of parallelizable work is the framework's primary failure mode.

## Fail-Fast Rule

If a task contains **>=3 independent items** with no inter-item dependency
cycle, CEO MUST dispatch sub-agents in parallel. Sequential CEO execution of
the same items is a velocity violation and SHOULD trigger the
`anti-ceo-overhead` hook (PLAN-083 sub-agent 0.5).

## When to invoke

CEO consults this skill at every decision point where work is non-trivial.
A task is **decomposable** (eligible for parallel dispatch) when ALL of:

1. **Item count >=3.** Two items is not worth dispatch overhead (sub-agent
   spin-up + prompt construction + result synthesis costs ~10-30s of
   wallclock). With three or more, the wallclock savings dominate.
2. **No inter-item dependency cycle.** Item B depending on Item A's output
   means serial. A DAG with independent leaves can still parallelize the
   leaves. Use sequential CEO only when the dependency graph is a chain.
3. **Each item fits in a single sub-agent prompt.** If one item would require
   the sub-agent itself to dispatch more sub-agents (recursive fan-out),
   split it into a sub-plan first; otherwise contention ceiling cascades.
4. **No shared-file write contention.** If two items would Edit/Write the
   same canonical path, they must be serialized (the canonical-guard kernel
   would block one anyway, and `check_canonical_edit.py` cannot resolve
   races between sub-agents).

If ANY criterion fails, dispatch sequentially or restructure the task.

## Decomposition algorithm (5 steps)

CEO follows this procedure when a candidate task arrives:

1. **Identify items.** Enumerate the unit-of-work atoms in the task. An atom
   is the smallest thing a single sub-agent prompt can deliver (one file +
   tests, one analysis report, one schema, one ceremony script).
2. **Group by dependency.** Build a DAG. Independent leaves = parallel
   batch. Chains = serial. Mixed = batch the leaves, then promote next
   layer once batch synthesizes.
3. **Assign tier per item.** Sonnet handles authoring + tests + analysis;
   Haiku handles redaction + format conversion + small mechanical edits;
   Opus reserved for cross-cutting design synthesis (rare in Wave 0+).
   Tier choice is a token-cost optimization; never assign Opus to work a
   Sonnet can do equally well.
4. **Write prompts.** Each sub-agent prompt MUST include: bounded goal,
   read-first list, staging output path, deliverable spec, constraints,
   report-back format. See `.claude/skills/core/parallelization-by-default/`
   future canonical examples or the PLAN-083 Wave 0a dispatch as reference.
5. **Dispatch in a single message.** All N sub-agent calls MUST go in the
   same assistant turn (multiple tool calls per message). Sub-agents spawned
   across multiple turns lose parallelism.

## Ceiling enforcement — max 6 parallel sub-agents

**Hard cap: N <= 6.** Per PLAN-083 Perf P0-1 measurement:

- The audit-log filelock (`_lib/filelock.py`) holds a single fcntl flock on
  `audit-log.jsonl`. Past ~6 concurrent emitters, p95 contention latency
  rises non-linearly (measured ~50ms at N=6, ~180ms at N=8, ~600ms at N=12).
- Git index lock similarly degrades when >6 sub-agents stage patches
  simultaneously to the same repo.
- Token-budget-guard (sub-agent 0.4 deliverable) cannot accurately tally
  spend across >6 in-flight sub-agents within the budget-check tick.

If a task decomposes to N > 6 items:

- **Batch.** Run the first 6 in parallel; synthesize; run the next batch.
  PLAN-083 Wave 1 §5.3 follows this pattern (batch 1 of 6 + batch 2 of 3).
- **Never override.** There is no `CEO_PARALLEL_CAP=10` env var. Past 6 is a
  protocol violation that the `anti-ceo-overhead` hook MAY block (consult
  sub-agent 0.5 deliverable spec for hook scope).

CEO MUST emit `parallelization_recommended` audit event at dispatch time with
the resolved batch size; values >6 indicate a bug in this skill's caller.

## Anti-patterns — concrete CEO-overhead violations to AVOID

These are real failure modes from prior sessions (S94/S100/S101 cluster):

1. **Sequential SKILL.md reads.** "I need to understand 10 skills before
   Wave 0 dispatch" -> CEO Reads them one at a time (10 turns, ~80k tokens
   of Opus context). Correct: dispatch 1 Sonnet sub-agent with
   `glob: .claude/skills/core/*/SKILL.md` to summarize all 10 in 1 turn
   (~15k tokens of Sonnet).
2. **Serial schema authoring.** "Author 3 schemas (repo-profile + secret-
   patterns + skill-binding)" -> CEO writes all three in successive turns
   (~120k Opus tokens, ~30min wallclock). Correct: dispatch 3 Sonnet
   sub-agents in single message (~60k Sonnet, ~10min wallclock).
3. **Serial validation across repos.** "Smoke-test framework on 5 demo
   repos" -> CEO runs each clone+install+smoke serially. Correct: dispatch
   5 Sonnet sub-agents in parallel (PLAN-083 Wave 3 §5.5 pattern).
4. **CEO reading staging output.** "Sub-agent finished, let me Read all 6
   patch files" -> 6 sequential Reads (~40k Opus tokens). Correct:
   `cat .claude/plans/PLAN-083/staging/wave-0a/*/*.patch | head -2000`
   single Bash call, or dispatch a synthesis sub-agent.
5. **Mid-batch synthesis premature.** "Sub-agent 0.1 finished, let me
   process its output before 0.2-0.7a finish" -> breaks parallelism. CEO
   waits for the full batch then synthesizes once.

## Audit emit hint

Action name: `parallelization_recommended` (snake_case, no `_emit` suffix,
matches `_lib/audit_emit.py` `_KNOWN_ACTIONS` convention).

Emitted by CEO at every dispatch decision (parallel or sequential). Fields:

- `recommended` (bool) — whether parallel dispatch was chosen
- `n_items` (int) — count of decomposable items detected
- `n_dispatched` (int) — actual batch size (always <= 6)
- `reason` (str) — short tag: `parallel_chosen` | `serial_dependency_chain` |
  `serial_shared_file_write` | `serial_single_item` | `batched_overflow`

Volume budget: **<=50/hr** per AC5c in PLAN-083 §6. Rationale: at one
dispatch decision per ~5min of CEO active work, 50/hr is generous; exceeding
indicates a hot loop or unbounded recursion in the caller.

## When NOT to dispatch parallel

- **Two items.** Dispatch overhead exceeds wallclock saving.
- **Single sequential task** (e.g. write one schema). No items to split.
- **Cross-cutting design synthesis** where Opus context across the full
  problem is the reason CEO exists. Example: deciding the architecture for
  a new sub-system. Decomposition would lose the synthesis surface.
- **Shared-file write paths.** Two sub-agents both editing
  `.claude/policies/grandfather-cap.policy.yaml` will conflict; serialize
  or hand to CEO.

## Reference

- PLAN-083 §5.1 Wave 0a row 0.1 (this skill's authorship lineage)
- PLAN-083 §3 thesis (velocity-by-default mandate)
- Pinned memory `feedback_owner_velocity_thesis.md`
- PLAN-083 §13 risk register row "Wave 0a velocity primitives don't actually
  speed up Wave 1-3" — anti-ceo-overhead hook is the mitigation
- ADR-046 sub-agent dispatch protocol (file-assignment-per-agent + result-
  contract)

## Task-Local Harness Discipline — folded from `dynamic-workflow-mode` (PLAN-157 W1)

Dispatch answers "who does the work in parallel"; this section answers "does
the work deserve a custom harness at all" — the case where an agent generates
a small task-local loop, evaluator, crawler, fixture generator, or watcher
instead of following a fixed command flow (distilled from the sunset
agents-meta squad's `dynamic-workflow-mode` skill; full text in git history).

**Decision tree — how much harness does this deserve?**

1. One-shot task → keep it inline; do not invent a harness.
2. Repeated task, changing inputs → task-local harness in a plan-local or
   scratchpad working area — never a canonical path.
3. Repeated task across teammates or repos → extract into a shared skill.
4. Task with external state, queueing, or approvals → add observable
   checkpoints (plan file, plan-scoped scratchpad, task board, audit log)
   before adding more automation.
5. Task with a safety risk → eval gate + human merge gate before anything
   autonomous.

**Core contract** — every harness declares five fields before any code:
Objective (what it owns and what it explicitly does NOT own); Inputs (files,
URLs, data sources, credentials policy); Outputs (commits, reports, status
files, checkpoints); Eval (at least one pass/fail check tied to the task, not
merely "it ran"); Handoff (what happened, what is blocked, how to resume).

**Eval gate per work type:** code feature → focused test + lint + one
integration path; UI/dashboard → browser smoke + screenshot + overflow/error
check; agent workflow → fixture transcript or seeded work item with expected
routing; research/content → claim checklist + publish-ready outline;
integration → dry-run + config validation + no-secret scan. A workflow is not
reusable until another teammate can rerun its eval.

**Promote to a shared skill only when at least two of:** the same workflow
recurs across sessions/repos/teams; it needs specific tool or safety
sequencing; failures repeat because operators skip a gate; it has a stable
input/output contract; it benefits from a shared status board or handoff. A
new skill is canonical-guarded — it lands through the import gate and
`/skill-review`, never by direct write.

**Anti-patterns:** scripts that hide the real decision logic from the
operator; treating "dynamic workflow" as permission to skip tests; one-off
docs when a shared skill or status artifact is the real deliverable; multiple
agents with no ownership, merge gate, or conflict policy; private data
leaking into committed artifacts.

## Loop Design + Review (judgment layer) — folded from `loop-design-check` (PLAN-157 W1)

Dispatch and harness are the mechanism layer; this is the judgment layer —
whether a repeating goal-seeking loop should exist, whether its goal is
machine-decidable, and whether it can run away (distilled from the sunset
agents-meta squad's `loop-design-check` skill; full text in git history).

**Two-level feedback red line.** Execution feedback — measure distance from
the literal goal and grind it to zero — belongs to the machine. Judgment
feedback — whether the goal itself is right, whether it should change,
whether to stop — belongs to the human/Owner: in this framework the
Owner-flipped plan lifecycle, the canonical-guard sentinel, the pair-rail,
and escalate-to-Owner. A loop that bypasses those has removed its own
top-level feedback.

**Build gate (4 conditions; any miss = veto):** (1) the task repeats weekly
or more often; (2) verification can be automated; (3) the token budget can
absorb the iteration; (4) the agent has tools that actually run the work and
observe the result. Miss any one → do not build a loop.

**Machine-decidable goal (five points; the loop lives or dies here):**
(1) done-criterion machine-verifiable — one command returns a verdict;
(2) boundary conditions defined alongside it — "what it must NOT do" is the
Goodhart antibody; (3) failure fallback — retry cap N, then escalate to a
human; (4) the goal is layered so a partial result is legible;
(5) prefer reconciliation over assertion — anchor to an external fact
(golden sample, upstream total, tie-out): "all tests pass" can be gamed;
"diff vs the reference < 0.01" cannot.

**Loop types:** clear "done" test → servo (stops on reaching the goal); no
endpoint, keep maintaining a state → regulator (never stops; a dead-band
suppresses noise); periodic sampling with a stop condition → regulator with
an exit; "must happen on time" → wrap either in the scheduler.

**Plan/build/judge iron rules:** the judge is independent — never the same
agent as Build (the pair-rail principle: the author is never the sole
reviewer); the judge is deterministic (pytest, a reconciliation diff, a real
diff — never "looks right"); Build may not weaken the acceptance conditions
to pass; three failed retries → escalate to a human. Add damping — a retry
cap, a hard stop, and a human at the last switch; negative feedback with no
damping oscillates (the loop spins in place, burning tokens).

**Review checklist (a hit on any row = send the loop back):**

| # | Failure mode | Antibody |
|---|---|---|
| 1 | Goal is a correct-sounding platitude → spins, burns tokens | replace with a decidable result condition |
| 2 | "Verification" is "looks ok" / the judge is the defendant | reconcile + exit-code rules + independent judge |
| 3 | Gates only on "all tests pass" → agent deletes the tests | done-criterion + boundary together |
| 4 | Counts on the agent asking mid-run → it will not | front-load every clarification before launch |
| 5 | Bloated context + stale memory → the faster it loops, the more it errs | layered memory + periodic hygiene sweep |

**Three red lines — violate any and the loop may not go automatic:** the
"done" cell is flipped by a human (the loop is the worker, not the acceptance
officer); responsibility does not transfer (anything whose failure you cannot
afford must not receive the loop's authority automatically); the more
self-improving the loop, the STRICTER the human review — the gate sits before
the action, exactly as kernel/self-modification routes through the sentinel +
Owner, never through the loop itself.
