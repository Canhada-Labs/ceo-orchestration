---
description: /fan-plan advisory bridge — parse a PLAN's [P?][USn][path] ACs and PROPOSE a read-only fan-out. ADVISORY ONLY; the Owner must confirm each spawn. Usage — /fan-plan <PLAN-NNN | AC-block>
argument-hint: "\"<PLAN-NNN id, or a pasted AC block>\""
---

# /fan-plan — Advisory-only fan-out proposer (PLAN-138 Wave B / ADR-151)

You are about to invoke the `/fan-plan` advisory bridge. Its output is
**ADVISORY ONLY** — it parses a plan's AC lines in the `[P?][USn][path]`
grammar (ADR-138) and PRINTS a *proposed* read-only fan-out grouping the
`[P]`-parallel ACs by file path. It **NEVER** auto-spawns and **NEVER**
invokes the harness fan-out primitives. The Owner (CEO) must explicitly
confirm each spawn before any hand-off happens.

## Honest enforcement boundary (read this)

`/fan-plan`'s "PROPOSE-only, never auto-spawn" contract rests on
**prompt-discipline this round** — it is documented here, not enforced by a
hook. This is **structurally weaker** than `/goap`, whose non-delegation is
hook-enforced (`check_agent_spawn.py` blocks any GOAP-tagged spawn lacking
`CEO_GOAP_CONFIRMED=1` + a `## GOAP CONFIRM` block). An optional follow-up
(`CEO_FANPLAN_CONFIRMED` spawn-hook parity) is deferred — see ADR-151 §B.6
+ PLAN-138 OQ-B. Until then: the model MUST NOT spawn from a `/fan-plan`
proposal without an explicit Owner instruction.

This advisory contract is anchored by:

1. **ADR-151** `fan-plan-advisory-bridge` declares the PROPOSE-only invariant.
2. **ADR-136-AMEND-1 §4.1** — the only permitted fan-out is read-only
   investigation; any write/canonical-edit/ceremony path runs sequentially
   through the Owner-GPG sentinel (`check_canonical_edit.py`) + `/debate`-VETO,
   never through a fan-out child.
3. **PLAN-110 anti-goal #1** — no `EXECUTE_COMMAND` auto-execution.

## Arguments received

The user invoked: `/fan-plan $ARGUMENTS`

## Argument contract

- `$ARGUMENTS` is either a `PLAN-NNN` id (resolve to
  `.claude/plans/PLAN-NNN-*.md`) OR a pasted AC block (lines in the
  `- [P?] [USn] [path] description` shape).
- ACs without `[P?]` default to `P1`; without `[USn]` are wave-level;
  without `[path]` have a null anchor (parser defaults — ADR-138 backward
  compat).

## Kill-switches

| Env var | Effect |
|---|---|
| `CEO_FANPLAN=0` | Disables `/fan-plan` entirely; the command prints a `fan_plan_disabled_by_env` notice and STOPS. |

## Procedure

### Step 1 — Parse the AC lines

```bash
# Single line (diagnostic):
python3 .claude/scripts/fan-plan-parser.py --line '- [P0] [US1] [src/x.py] do thing' --json
# Full-plan corpus scan (backward-compat self-check, ADR-138 g3):
python3 .claude/scripts/fan-plan-parser.py --scan-plans .claude/plans/ --json
```

For a `PLAN-NNN` argument, read the plan file and feed each AC line to the
parser. The parser is lenient (never raises); a malformed line degrades to
the defaults.

### Step 2 — Group by path + priority

Group the parsed ACs by their `[path]` anchor. ACs that share no `[path]`
and carry an explicit `[P0]/[P1]` are eligible to be PROPOSED as a parallel
read-only investigation group (one finder per path). This mirrors the
existing confined `audit-fanout` fan-out shape (ADR-136-AMEND-1 §4.1 +
§4.3 8-field returns) — it proposes nothing new beyond that shape.

### Step 3 — PRINT the proposal (then STOP)

Render a block of EXACTLY this shape (substitute the real numbers) and then
STOP. Do not act on it.

```
=== PROPOSED read-only fan-out (Owner must confirm each spawn) ===
Plan: PLAN-NNN  |  parallel groups: <G>  |  ACs: <K>

Group 1 — path: <path-a>   [P0,P1 ACs]
  - [P0] [US1] [<path-a>] <description>
  ...

COST ENVELOPE
  proposed agents: <N>  (audit-fanout shape floor: 8 finders + up to 8
    refuters + 1 synthesis = up to 17 agents)
  token envelope: order-of-magnitude <T> tokens (read-only investigation)
  MODEL CAVEAT: each proposed agent runs the SESSION model — opts.model is
    INERT for Workflow subagents (ADR-144 §S220 / PLAN-134 GATE-W0a), so a
    CEO Opus session fans out at Opus tier, NOT a downgraded/cheaper tier.

These spawns are NOT executed. The Owner must confirm each one.
=== END PROPOSAL (no spawns executed) ===
```

The `COST ENVELOPE` MUST include: (i) a numeric proposed-agent count, stating
the audit-fanout floor of **8 finders + up to 8 refuters + 1 synthesis = up
to 17 agents**; (ii) an order-of-magnitude token envelope; (iii) the explicit
inert-model caveat (the `MODEL CAVEAT` line above).

### Step 4 — Wait for explicit Owner confirmation

The command STOPS after printing the proposal. The Owner reviews it and
decides which (if any) groups to authorize. The model NEVER spawns from this
proposal on its own — the boundary is prompt-discipline this round (see the
honest-enforcement note above).

## Hard prohibition (the load-bearing invariant)

This command's body and any rendered proposal MUST NOT call the harness
fan-out primitives — i.e. it never calls the parallel-fan-out function nor
the single-agent-spawn function. The proposal is text only; it triggers zero
spawns. (A grep of the rendered proposal for those two primitive call-forms
returns nothing — this is asserted by the Wave B test.)

## Limitations (v1.47.0)

- **Advisory only.** No auto-spawn; prompt-discipline enforcement (weaker
  than `/goap`'s hook gate). See ADR-151 §B.6 / PLAN-138 OQ-B.
- **Cost is session-model tier.** `opts.model` is inert (ADR-144 §S220);
  the cost envelope reflects the session model, not a requested cheaper tier.
- **Parser is lenient.** Non-conforming AC lines degrade to defaults; the
  proposal is best-effort, not a contract.
