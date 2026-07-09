---
name: loop-design-check
description: Design a goal-oriented agent loop and review it for the ways loops fail — spinning and burning tokens, Goodhart-gaming the verifier, or driving a wrong answer to completion. Two actions — (1) WRITE a loop — gate whether it should exist at all, define a machine-decidable goal, pick the loop type, pick a skeleton, add damping; (2) REVIEW a loop — run it past five failure modes plus decidability, boundaries, fallback, judge-independence, and the red lines that keep the last switch with a human. Use when you are about to hand a repeating task to an autonomous loop, or you already have one and worry it will spin, cheat, or run a wrong answer to the end. This is the judgment layer that sits above the mechanism-layer loop tooling (the host harness's `/loop` and `/schedule` built-ins); it decides whether the goal is right and whether the loop can run away, not how to wire the plumbing.
version: 1.0.0
risk_class: low
metadata:
  domain: agents-meta
  audit_action: loop_design_reviewed
  activation_triggers:
    - {event: help-me-invoked, regex: "(?i)design.{0,12}loop|write.{0,8}(a|an)?.{0,4}loop|agent.?loop|goal.?oriented.?loop|decidable.?goal|plan.?build.?judge|loop.?review|runaway.?loop|will.?it.?(spin|run.?away)"}
    - {event: plan-opened, regex: "(?i)autonomous.?(loop|agent)|self.?improving.?loop|nightly.?(fix|green|keeper)|write.?test.?fix.?loop"}
    - {event: spawn-requested, regex: "(?i)loop|servo|regulator|verifier|judge.?agent"}
source: affaan-m/ecc@81af4076 skills/loop-design-check/
license: MIT
---

# Loop Design + Review

> **Premise.** A model is feed-forward: prompt in, tokens out, with no built-in
> pull toward a goal across turns. To make it *behave* like a goal-seeking
> system you wrap a feedback loop around it. This skill helps you **write** that
> loop so it converges, and **review** an existing one so it does not run away.
> It is the judgment layer — separate from the mechanism-layer tooling
> (the host harness's `/loop` / `/schedule` built-ins, `/goap`,
> `parallelization-by-default`) that wires the
> plumbing.

## When to Activate

**Load this skill when:**
- You are about to hand a *repeating* task to an agent that runs over and over
  (write→test, test→fix, fix→verify, reconcile→report).
- You already have a loop and suspect it spins in place, games its own check,
  or commits a wrong answer instead of stopping to ask.
- A plan proposes anything "autonomous" or "self-improving" that acts without
  an Owner at the last switch.

**Do not load it for:**
- A one-off task → just do the task; do not wrap a loop around it.
- A plain timer or poll → that is `/loop`; no design work needed.
- *How to wire the loop architecture* (recurrence, cron, recovery, fan-out) →
  that is the mechanism layer (`/loop`, `/schedule`, `parallelization-by-default`).
  This skill covers only "is the goal right, and will it run away."

## Red-line premise: two levels of feedback

A durable loop separates two feedback levels and never lets the machine own the
top one.

| Level | Owner | What it does |
|---|---|---|
| **Execution** (low) | machine / agent | Measures distance from the literal goal and grinds it to zero. The machine is strong here. |
| **Judgment** (high) | **the human / Owner** | Decides whether the goal itself is right, whether it should change, whether to stop. The machine cannot step outside its own loop to question its goal. |

A thermostat can drive the room toward 26 °C, but it cannot decide that 26 is
the *wrong* target the day you have a fever — it just grinds toward the number
it was handed. **What to aim at today is always the human's call.** Hand
judgment, sign-off, or the final switch to the machine and you have removed the
high-level feedback: it now sprints, fast and hard, toward a goal no one is
questioning.

In this framework the high-level feedback is concrete: the Owner-flipped plan
lifecycle, the canonical-guard sentinel, the cross-model pair-rail
(`cross-llm-pair-review` — author is never sole reviewer), and escalate-to-Owner.
A loop that bypasses those has removed its own top-level feedback.

---

## Action 1 — Write a loop (5 steps)

### Step 0 · Subtract first — should this loop exist at all? (4-condition gate; any miss = veto)

1. the task repeats weekly or more often;
2. verification can be automated;
3. the token budget can absorb the iteration;
4. the agent has tools that actually *run the work and observe the result*.

Miss any one → **do not build a loop.** Do it by hand, or restructure the task.

> What blocks most people is not "can I write a loop," it is "does this repo
> deserve one." A repo that deserves a loop already has a reconciliation
> baseline (a golden sample, an upstream total, a tie-out), a test suite, and a
> guard. A repo that does not deserve a loop will only have its errors
> amplified by one.

### Step 1 · Define a *machine-decidable* goal (the hard part — the loop lives or dies here)

The whole loop rides on the comparator's "is it done yet?" The comparator can
only work if the exit condition can be judged yes/no **by a machine, with no
taste involved.**

- **Bad — vague:** "make it good," "write it sharper." The comparator cannot
  judge, so it either never passes (stuck retrying, burning tokens) or guesses
  (passes and blocks at random).
- **Good — decidable:** "all 96 unit tests green AND a change-list produced,"
  "module-02 fields filled, pytest passes, business logic untouched." One check
  settles it; the loop converges.

**Five-point goal framework:**
1. **Done-criterion is machine-verifiable** — one command returns a verdict.
2. **Boundary conditions defined alongside the done-criterion** — "what it must
   NOT do." Missing boundaries are a license to cheat (the Goodhart antibody).
3. **Failure fallback exists** — a retry cap N, then escalate to a human.
4. **The goal is layered**, so a partial result is legible, not all-or-nothing.
5. **Prefer reconciliation over assertion.** Anchor the done-criterion to an
   external fact (golden sample, upstream total, financial tie-out) before your
   own assertions. "All tests pass" can be gamed — loosen asserts, fake mocks,
   swallow exceptions. "diff vs the reference < 0.01" cannot.

> **Self-check:** read the goal to someone who does not know the domain — can
> they run one command and tell whether it is done? If not, it is not decidable
> enough. Go back.

### Step 2 · Pick the loop type

| Your task | Loop type | How it stops |
|---|---|---|
| Has a clear "done" test (write→done, a batch processed) | **servo** (closed-loop toward a goal) | stops on reaching the goal |
| No endpoint; must keep maintaining a state (inventory alert, scheduled health check) | **regulator** (thermostat, `/loop`-style) | never stops; acts only on change — a dead-band suppresses noise |
| Periodic sampling, stop on a condition (watch a PR until CI is green) | **regulator with an exit** | stops when the exit condition holds |
| Must "ensure something happens on time" | wrap either of the above in `/schedule` | cron fires it |

> Rule of thumb: clear "done" test → servo; must keep maintaining with no
> endpoint → regulator; must happen on time → wrap a regulator in `/schedule`.

### Step 3 · Pick a skeleton

**Maintenance type (tend something that already exists) → doc-driven dispatch.**
The loop is not "run a fixed check on a timer," it is "read a state doc on a
timer, and dispatch only when the doc changed." The doc is the task queue, the
state machine, and the human interface at once (in this framework, a
plan file plus plan-scoped `memory-scratchpad`). Three disciplines:

1. The problem column is human-write-only; the result column is loop-write-only;
   **state advances one-way and never rolls back.**
2. **The exit code is final** — if the script says exit 1, the script wins.
3. State advances only as far as "awaiting verification" — **the "done" cell is
   flipped by a human.** The loop is the worker, not the acceptance officer.

**Greenfield type (build from scratch) → plan / build / judge, three roles.**

| Role | Does | Key constraint |
|---|---|---|
| **Plan** | break the goal into a spec + **decidable acceptance conditions** | acceptance must be script-judgeable |
| **Build** | write to the spec | **must not edit the acceptance conditions** |
| **Judge** | run acceptance **independently**; pass → stop, fail → return the failure reason to Build | **independent + deterministic** |

Three iron rules, all of which bet on the judge:
1. **The judge must be independent** — not the same agent as Build. Grading your
   own homework always inflates. This is the same principle as the framework's
   pair-rail: the author is never the sole reviewer.
2. **Deterministic rules** — pytest, a reconciliation diff, a type check, a
   real diff. Never "looks right."
3. **Build may not weaken the acceptance conditions to pass.** Three failed
   retries → escalate to a human.

### Step 4 · Add damping (against oscillation / runaway)

A retry cap, a hard stop, and a human at the last switch are damping. **Negative
feedback with no damping oscillates** — the loop spins in place, burning tokens,
making no progress (the classic "spin in the same rut forever").

### Step 5 · Land in three stages (do not go fully automatic on day one)

1. **Run it once by hand** — this forces you to state exactly how the judge
   decides. →
2. **Harden into a skill or sub-agent dispatch** — a driver loops, dispatching
   plan/build/judge. →
3. **Hang it on `/schedule`** for full automation, only once stages 1–2 held.

---

## Action 2 — Review a loop (checklist = five failure modes)

Run the loop past each row. **A hit on any one row means this loop will
misfire — send it back.** These are gotchas learned by failure; they are worth
more than any list of positive rules.

| # | Failure mode | Review question (a hit = red) | Antibody |
|---|---|---|---|
| 1 | Goal is a correct-sounding platitude → **spins, burns money** | Can the exit condition be machine-judged yes/no, or is it "manage it well"? | Replace with a decidable result condition (Action 1 · Step 1) |
| 2 | "Verification" is "check if it looks ok" → **agent confidently says fine and stops** | Is the judge the defendant itself? Does verification rest on "looks right"? | Reconcile + exit-code rules + independent judge |
| 3 | (worst) Only gates on "all tests pass" → **agent deletes the tests** | Is there a boundary ("what it must NOT do"), or only a done-criterion? | Done-criterion **+ boundary** together |
| 4 | Counts on the agent asking mid-run → **it will not; it runs the wrong answer to the end** | Is there any "clarify only at runtime" point? | **Front-load every clarification;** settle it once before launch |
| 5 | Bloated context + stale memory → **the faster it loops, the more it errs** | Are the docs and memory it depends on fresh? Who maintains them? | Layered memory + a periodic lint/hygiene sweep |

**Plus three red lines — violate any and the loop is not allowed to go automatic:**

- **Keep judgment with the human.** Acceptance / the "done" cell is flipped by a
  human. The loop is not the acceptance officer.
- **Responsibility does not transfer.** Anything whose failure you cannot afford
  — merging the wrong PR, publishing the wrong thing, moving money — **must not
  hand its authority to the loop automatically.**
- **The more "self-improving" the loop, the *stricter* the human review it
  needs** — not looser. A loop that rewrites its own rules is too fast to
  intercept after the fact, so the human's judgment must sit **before the
  action** as a hard gate, never as a post-hoc patch. This is the same reasoning
  the framework applies to self-modification: kernel/self-editing changes route
  through the sentinel + Owner, not the loop.

---

## Worked example — reviewing a "nightly green-keeper" loop

You want a loop that runs every night and fixes whatever tests are failing.

- **Naive goal:** "make all tests pass." Step-1 self-check fails immediately —
  this is exactly the bait for failure mode #3.
- **Decidable goal (fixed):** "all tests green **AND** no test file deleted or
  weakened **AND** coverage not lowered **AND** a change-list produced." The
  boundary now lives alongside the done-criterion.
- **Type:** servo with a retry cap of 3 (Step 2 + Step 4).
- **Skeleton:** plan / build / judge — the **judge is CI run independently**,
  never the fixing agent (Step 3).

Now run the review checklist, and it catches what the naive version misses:

- **#3 hit** → the naive "all tests pass" lets the agent delete a failing test
  to "win." Fixed by the boundary "no test file deleted or weakened."
- **#2 hit** → if the fixing agent also judged its own fix, it would pass
  itself. Fixed by "judge = independent CI, deterministic."
- **#4 hit** → at 2 a.m. the agent will not stop to ask about an ambiguous fix;
  it commits a guess. Fixed by front-loading: ambiguous fixes are left for the
  human, not guessed.
- **Red line** → the loop opens a PR but **does not auto-merge**; the human
  flips the last switch (responsibility does not transfer).

The naive loop and the reviewed loop differ by four lines of constraint — and
that is the difference between "wakes you to a deleted test suite" and "wakes
you to a clean PR."

---

## One-line close

> The hard part of a loop is not "can I write a loop," it is **defining a goal a
> machine can reconcile** — decidable, bounded, reconciliation-based. Keep the
> controller deterministic and external; keep judgment and the standard with the
> human; the system tends toward entropy, so maintain it. A loop only rewards
> someone who has already thought it through — count on it to think for you and
> it will happily think wrong, with you, at scale.

> **Lineage.** The execution-vs-judgment split is the two-level feedback of
> classical cybernetics (Wiener). The plan/build/judge separation is standard
> agent-loop engineering. This skill is the judgment layer only; for the
> mechanism layer (recurrence, cron, recovery) use `/loop` and `/schedule`.

## Changelog

- **1.0.0** — Initial house-format authoring. Judgment-layer loop design +
  review doctrine: 4-condition build gate, machine-decidable goal framework,
  servo/regulator typing, plan/build/judge skeleton with independent judge,
  damping, staged landing, five-failure-mode review checklist, three red lines,
  green-keeper worked example. Anchored to host-harness built-ins (`/loop`,
  `/schedule` — Claude Code ships these) and framework mechanisms
  (pair-rail, sentinel, escalate-to-Owner).
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=d29bfe81fd54782ad1edf92c0524a1dc9549ee5639200d1be3816f073afb3b04
