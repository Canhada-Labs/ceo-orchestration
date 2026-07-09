---
name: dynamic-workflow-mode
description: Design task-local harnesses, eval gates, and reusable-skill extraction for the case where an agent can generate or adapt its own workflow instead of only following a fixed command flow. Turns "the agent invents a harness" into a disciplined system — a temporary harness for one-off work, a shared skill for repeated work, observable checkpoints for teamwork, and an eval gate plus a human merge gate before anything autonomous. Use when a task needs a custom loop, evaluator, crawler, fixture generator, or watcher, when several agents need the same repeatable process that is not yet a skill, or when a workflow needs durable handoff artifacts and operator sign-off before merge.
version: 1.0.0
risk_class: low
metadata:
  domain: agents-meta
  audit_action: dynamic_harness_designed
  activation_triggers:
    - {event: help-me-invoked, regex: "(?i)dynamic.?workflow|task.?local.?harness|harness.?per.?task|adaptive.?(workflow|harness)|custom.?(loop|evaluator|harness)|reusable.?skill.?extract|eval.?gate"}
    - {event: plan-opened, regex: "(?i)harness|fixture.?generator|watcher|control.?pane|status.?board|handoff.?artifact"}
    - {event: spawn-requested, regex: "(?i)harness|evaluator|crawler|watcher|dynamic.?workflow"}
source: affaan-m/ecc@81af4076 skills/dynamic-workflow-mode/
license: MIT
---

# Dynamic Workflow Mode

> **Premise.** Sometimes the cheapest correct move is not to follow a fixed
> command — it is to let the agent generate a small, task-local *harness*: a
> throwaway loop, evaluator, or watcher scoped to one job. That power is only
> safe with discipline. This skill sets the contract: build a harness only when
> it is cheaper and safer than driving the steps by hand, gate it with a
> task-specific eval, keep the checkpoints observable, and never skip the human
> merge gate.

## When to Activate

**Load this skill when:**
- A task would benefit from a custom loop, evaluator, crawler, fixture
  generator, watcher, or local dashboard — not just a one-shot command.
- Several agents need the same repeatable process, but the process is not yet
  captured as a shared skill.
- A workflow spans more than one session and needs durable handoff artifacts,
  eval evidence, or operator approval before merge.

**Do not load it for:**
- A genuine one-shot task → keep it inline; do not invent a harness.
- Work already covered by an existing skill or slash command → use that.
- Wiring recurrence or cron → that is `/loop` and `/schedule` (host-harness
  built-ins — Claude Code ships them; they are the mechanism layer, not
  framework commands under `.claude/commands/`);
  and whether the loop's *goal* is right is `loop-design-check`.

## Core contract — what every harness must declare

Generate a task-local harness only when the harness is cheaper and safer than
manually driving the same steps. When you do, it must state:

- **Objective** — the outcome it owns, and the outcome it explicitly does *not*
  own.
- **Inputs** — files, URLs, prompts, data sources, the credentials policy, and
  any user-supplied constraints.
- **Outputs** — commits, reports, screenshots, status files, or checkpoint
  snapshots.
- **Eval** — at least one pass/fail check tied to the task, not merely "it ran."
- **Handoff** — a short artifact that tells the next operator what happened,
  what is blocked, and how to resume.

## Decision tree — how much harness does this deserve?

1. **One-shot task** → keep it inline. Do not invent a harness.
2. **Repeated task, changing inputs** → build a task-local harness under a temp
   or plan-local working area (for this framework: `PLAN-NNN/` scratch or the
   session scratchpad — never a canonical path).
3. **Repeated task across teammates or repos** → extract the pattern into a
   shared skill.
4. **Task with external state, queueing, or approvals** → add observable
   checkpoints *before* adding more automation.
5. **Task with a safety risk** → add an eval gate and a human merge gate before
   any autonomous execution.

## Task-local harness template

Fill this before writing any code:

```markdown
# Task-Local Harness

Objective:
- Ships:
- Does NOT ship:

Inputs:
- Repo or workspace:
- External systems:
- Credentials policy:

Loop:
1. Discover current state.
2. Generate or update the smallest useful artifact.
3. Run the eval check.
4. Record status + handoff.
5. Stop on a failed gate, unclear ownership, or an unsafe external action.

Eval:
- Command:
- Expected pass signal:
- Failure owner:

Handoff:
- Status:
- Evidence:
- Next action:
```

## Promote to a shared skill only when it earns it

Turn a task-local harness into a shared skill only when **at least two** of
these hold:

- The same workflow shows up across multiple sessions, repos, or teams.
- The workflow needs specific language, tool, or safety sequencing.
- Failures repeat because operators skip a gate or lose context.
- The workflow has a stable input/output contract.
- The workflow benefits from a shared status board or team handoff.

When extracting, write the skill first as `SKILL.md`; add a slash-command shim
only if a legacy entry surface is still required. In this framework a new skill
is canonical-guarded — it lands through the import gate and `/skill-review`, not
by direct write.

## Observable checkpoints (the "control pane")

A dynamic harness becomes team-usable only when it exposes its state. Whenever a
task spans more than one session, record these checkpoints in a durable place —
in this framework, the plan file, plan-scoped `memory-scratchpad`, the task
board, and the HMAC audit log, rather than scattered untracked notes:

- **Plan** — objective, owner, acceptance criteria, risky external systems.
- **Queue** — work items, assigned role, branch/worktree, dependency edges.
- **Run** — active harness, current loop step, latest eval result, token/cost
  signal if available.
- **Gate** — test results, screenshots, security review, merge readiness.
- **Handoff** — what is done, what failed, what needs a human decision.

Prefer the framework's existing state surfaces (plan lifecycle, scratchpad,
audit log) over inventing a private store; a checkpoint no teammate can read is
not a checkpoint.

## Eval gates — pick the cheapest reliable one

Every dynamic harness needs a task-specific eval. Do not call a workflow
reusable until another teammate can rerun its eval.

| Work type | Eval gate |
|---|---|
| Code feature | focused test + lint + coverage + one integration path |
| UI / dashboard | browser smoke with a screenshot + overflow/error check |
| Agent workflow | fixture transcript or seeded work item with expected routing |
| Research / content | source-neutral brief + claim checklist + publish-ready outline |
| Integration | dry-run command + config validation + no-secret scan |

## Anti-patterns

- Generating scripts that hide the real decision logic from the operator.
- Treating "dynamic workflow" as permission to skip tests.
- Producing one-off docs when a shared skill or a status artifact is the real
  deliverable.
- Running multiple agents with no ownership, merge gate, or conflict policy.
- Letting raw private data leak into public docs or committed artifacts.

## Output standard

Close every dynamic-workflow task with:

- The harness or skill path.
- The eval command(s) and their result.
- The checkpoint / handoff artifact path.
- The next reusable-extraction candidate, if any.

## Changelog

- **1.0.0** — Initial house-format authoring. Task-local-harness discipline:
  core contract (objective/inputs/outputs/eval/handoff), 5-branch decision tree,
  harness template, shared-skill promotion rule, observable checkpoints mapped
  to framework state surfaces (plan lifecycle, `memory-scratchpad`, task board,
  audit log), per-work-type eval-gate table, anti-patterns, output standard.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=9fa5a68074d56dc144798500e74ac1f1deaa21cfd4d60142cd9c6ff7600ef915
