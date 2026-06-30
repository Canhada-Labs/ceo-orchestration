---
description: Run or advance a structured multi-round debate on a plan — /debate start|round2|round3|status PLAN-NNN
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TaskCreate, TaskUpdate, TaskList, Agent
---

# /debate — Multi-round plan debate orchestration

You are the CEO. A plan at `.claude/plans/PLAN-<NNN>-<slug>.md` needs
a structured debate. The full schema is at `.claude/plans/DEBATE-SCHEMA.md`
— read it before running this command.

> **Scope of the verdict (PLAN-134 W1):** debate is a **design-coherence
> check**, not a truth gate. A clean outcome is recorded as
> **`design-coherent`** (the label formerly written as "0-VETO") — it
> certifies the design is internally coherent across forced
> perspectives, NOT that it is externally true (same-LLM problem,
> PROTOCOL.md §Honest limitation). **Debate output does NOT authorize
> shipping** — only the verification cascade does: V0 plan-check →
> V1 deterministic → V2 Codex pair-rail (the **sole LLM truth gate**,
> fail-closed to the Owner) → V3 Owner GPG. See PROTOCOL.md
> §Verification cascade + DEBATE-SCHEMA.md §13.

The command has 4 sub-forms. The first token of `$ARGUMENTS` is the
sub-form; the second is the plan ID (`PLAN-003`, not a file path).

## Arguments received

`/debate $ARGUMENTS`

Parse `$ARGUMENTS` as `<sub-form> <PLAN-NNN> [extra]`:

- `/debate start PLAN-003 "[proposal blurb]"` — start round 1
- `/debate round2 PLAN-003` — advance to round 2
- `/debate round3 PLAN-003` — advance to round 3
- `/debate status PLAN-003` — report current state without modifying

Validation:
- `<sub-form>` must match `^(start|round2|round3|status)$`
- `PLAN-NNN` must match `^PLAN-[0-9]{3}$` (three digits, zero padded)
- The plan file `.claude/plans/PLAN-<NNN>-*.md` must exist (use Glob)
- Reject malformed input with a clear error

## Sub-form: `start`

1. Confirm the plan file exists. If not, stop and ask the Owner.
2. Create `.claude/plans/PLAN-<NNN>/debate/round-1/` if missing.
3. Write `round-1/proposal.md` containing:
   - A frontmatter block (`plan`, `round: 1`, `created_at`)
   - A ≤ 300-line distillation of the plan's thesis, scope, decisions,
     and open questions. Link back to the full plan file.
4. Pick **3 archetypes** for this debate. Default triad:
   - VP Engineering (skill: `architecture-decisions`)
   - Staff Security Engineer (skill: `security-and-auth`)
   - DevOps & Platform Engineer (skill: `devops-ci-cd`)
   For plans in a domain-specific area (e.g. fintech), swap one
   archetype for the domain specialist (e.g. Staff Quant with
   `financial-correctness-and-math`).
5. For each archetype, spawn an Agent with full persona + SKILL content
   + FILE ASSIGNMENT restricting write access to
   `.claude/plans/PLAN-<NNN>/debate/round-1/<archetype-slug>.md` only.
   Use `.claude/scripts/inject-agent-context.sh` to build the prompt.
   The task description MUST direct the agent to produce the 7-section
   critique format from DEBATE-SCHEMA.md §4:
   Verdict, Summary, Risks, Must-fix, Nice-to-have, Unseen,
   What I would NOT change.
6. Run the 3 spawns **in parallel** (zero file overlap, `isolation`
   default). Each Agent tool call includes:
   - description: "`<ArchetypeName>` debate round 1 on `PLAN-<NNN>`"
   - prompt: the injector-built full-context prompt
7. Wait for all 3 agents to return. Verify each wrote exactly one file.
8. Do NOT write `consensus.md` yet — that happens in `/debate round2`
   (or the operator can manually synthesize and move on).
9. Report to the Owner:
   - Which files now exist
   - Top-level verdicts (ACCEPT / ADJUST / REJECT) from each agent
   - Suggested next step: review the critiques, then run `/debate round2`

## Sub-form: `round2`

1. Confirm `round-1/` exists and has at least the proposal + 3 agent
   critique files. If not, stop — round 2 cannot run without round 1.
2. Read all 3 round-1 critiques.
3. **Anonymize before synthesis** (PLAN-134 W1, DEBATE-SCHEMA.md §13.2):
   assign each critique a neutral label (`Critic-A`, `Critic-B`,
   `Critic-C`, …), strip persona and archetype names from the critique
   text, and record the label↔archetype mapping in
   `round-1/anonymization-map.md` (audit record). The synthesis step
   consumes ONLY the anonymized critique text — never the persona names.
4. Build `round-1/consensus.md` with the frontmatter contract and body
   structure from DEBATE-SCHEMA.md §5:
   - Consensus findings (2+ agents flagged)
   - Single-agent insights kept
   - Single-agent insights rejected / deferred
   - Plan adjustments (a § index, actual edits go in the plan file)
   - Round verdict: PROCEED | RUN-ANOTHER-ROUND | ESCALATE
5. Edit the plan file to apply any agreed adjustments from round 1.
   Use `Edit` tool with precise old/new strings.
6. If round verdict is PROCEED → stop here. Report to Owner. Plan
   moves to `status: reviewed`. No round 2 needed. PROCEED records the
   debate as `design-coherent` — it does NOT authorize shipping (the
   verification cascade does).
7. If round verdict is RUN-ANOTHER-ROUND:
   - Create `round-2/` directory
   - Spawn the 3 agents again (same archetypes — continuity matters).
     **Session continuity (PLAN-135 D4):** if the round-1 agents were
     named spawns, PREFER resuming them — `SendMessage` to the named
     spawn / the `persona → agentId` handle recorded in the plan
     scratchpad — over a cold re-spawn: the agent keeps its own round-1
     reasoning and you skip the full re-brief (re-briefing is the
     dominant cost driver of multi-round work). A cold re-spawn stays
     correct when you WANT fresh eyes. Either way the
     anonymize-before-synthesis protocol (DEBATE-SCHEMA.md §13.2) is
     unaffected — it governs critique TEXT at synthesis time, not spawn
     mechanics.
   - Each agent reads: the UPDATED plan file, `round-1/consensus.md`,
     all round-1 critiques, their SKILL.md
   - Each agent writes: `round-2/<archetype-slug>.md`
8. If round verdict is ESCALATE — stop, report to Owner, do not start
   round 2 automatically. Present the escalation per §Owner tie-breaks
   (AskUserQuestion doctrine) below.

## Sub-form: `round3`

Same pattern as `round2`:

1. Confirm `round-2/` is complete.
2. Anonymize the round-2 critiques (same `Critic-X` protocol; mapping in
   `round-2/anonymization-map.md`), then write `round-2/consensus.md`
   with the full frontmatter contract.
3. Apply any agreed adjustments to the plan file.
4. If verdict is PROCEED, stop.
5. If verdict is RUN-ANOTHER-ROUND, spawn round 3 agents.
6. After round 3 completes, write `round-3/synthesis.md` (NOT
   `consensus.md` — this is the final name per DEBATE-SCHEMA.md §6)
   with:
   - 3-round arc summary
   - Final plan deltas
   - Lessons for the debate process itself

## Sub-form: `status`

Report without modifying:

1. Confirm the plan file exists.
2. List all files under `.claude/plans/PLAN-<NNN>/debate/` (if the
   directory exists).
3. For each round directory, report:
   - Which agents have responded (files present)
   - Which agents are pending (expected but missing)
   - Whether consensus.md exists
4. If a consensus file exists, print its frontmatter `round_verdict`.
5. Suggest the next `/debate` sub-form to run.

## Session continuity for debates (PLAN-135 W4 D4)

- Record `persona → agentId` for every named debate spawn in the plan
  scratchpad (`/memory-scratchpad`). That ledger is what makes
  round-N+1 resumption (instead of a full re-brief) possible.
- A context-rich side investigation mid-debate (e.g. checking a
  critique's claim against the CEO's in-flight reasoning) is a `/fork`
  of the live session, NOT a cold spawn — the fork inherits the debate
  context for free.
- **Independence exception (never fork these):** the V2 Codex
  pair-rail truth gate and any independent adversarial verifier MUST
  start cold + cross-rail. Forking them from the CEO session would
  inherit the same blind spots the cascade exists to break
  (PROTOCOL.md §Honest limitation: same-LLM).
- Post-crash mid-debate: `claude --continue` restores the
  CONVERSATION; `/resume PLAN-NNN` restores the PLAN. The debate dir
  on disk is the ground truth for round state — `/debate status`
  re-derives it. See `docs/CHEAT-SHEET.md` §Session continuity.

## Spawn compliance

**CRITICAL:** every agent spawn MUST go through
`.claude/hooks/check_agent_spawn.py` (the spawn hook). Use
`.claude/scripts/inject-agent-context.sh` to build the prompt — it
generates the `## AGENT PROFILE` + `## SKILL CONTENT` +
`## FILE ASSIGNMENT` sections that the hook requires.

If a spawn is blocked by the hook, the CEO FIXES THE PROMPT, never
bypasses the hook. Bypassing the spawn hook for debate would be the
exact failure mode PLAN-001 existed to prevent.

## File assignment for debate agents

Every debate spawn includes a FILE ASSIGNMENT section restricting the
agent's write access to **exactly one file**:

    .claude/plans/PLAN-<NNN>/debate/round-<N>/<archetype-slug>.md

Every other path is FORBIDDEN. The agent may READ the plan file,
previous consensus files, other agent critiques, their own SKILL.md,
and any file in the repo — but can WRITE only their own critique file.

This prevents two agents from stomping each other's critiques during
parallel execution (PROTOCOL.md §Spawn Protocol anti-collision rule).

## Audit events emission

At every debate phase, emit a `debate_event` so `audit-query.py debate`
can surface activity without scraping the plan subdir. The emitter is
fail-open: if it errors, the debate still proceeds.

Run one of these Bash calls at each phase:

```bash
# Phase: start of a new round (before spawning agents)
python3 .claude/scripts/debate-emit.py start PLAN-<NNN> <ROUND> \
    --artifact .claude/plans/PLAN-<NNN>/debate/round-<ROUND>/proposal.md || true

# Phase: one agent's critique landed
python3 .claude/scripts/debate-emit.py agent-done PLAN-<NNN> <ROUND> \
    --agent <archetype-slug> \
    --artifact .claude/plans/PLAN-<NNN>/debate/round-<ROUND>/<archetype-slug>.md || true

# Phase: consensus synthesis complete
python3 .claude/scripts/debate-emit.py consensus PLAN-<NNN> <ROUND> \
    --artifact .claude/plans/PLAN-<NNN>/debate/round-<ROUND>/consensus.md \
    --consensus-adjustments <N> || true
```

- `start`: once per round, at the beginning, before spawning agents.
- `agent-done`: once per agent, after their critique file is verified.
- `consensus`: once per round, after `consensus.md` is written and
  any plan adjustments applied. `<N>` is the count of entries in the
  "Plan adjustments" section of the consensus doc.

The `|| true` suffix keeps this advisory — audit emission errors never
block the debate.

## Owner tie-breaks (AskUserQuestion doctrine — PLAN-135 K10)

When a debate needs the Owner to break a tie — an ESCALATE round
verdict, 2+ VETOs, or critics deadlocked on mutually exclusive designs —
present the decision with the `AskUserQuestion` tool as **structured
multiple-choice**, not open prose: 2–4 mutually exclusive options, each
with a one-line consequence, and exactly one marked **"(Recomendado)"**
with the CEO's reasoning attached. After the Owner picks, log the
selected option's decision text **verbatim** into the plan's OQ section
(date + selected option), so the tie-break is quotable and auditable
instead of reconstructed from chat prose. The same doctrine governs OQ
ratifications and wave go/no-go decisions — see the ceo-orchestration
SKILL §Decision framework. Open-ended escalations with no enumerable
option set stay free-form; the doctrine applies only when the choice set
is closed.

## Output on any sub-form

Always report to the Owner:

- What was created/modified
- Which files agents wrote
- Top-level verdicts — a clean debate is reported as `design-coherent`
  (NOT "approved" / "0-VETO"), with the reminder that shipping is
  authorized only by the verification cascade (V2 Codex truth gate +
  V3 Owner GPG), never by the debate itself
- The next recommended action
