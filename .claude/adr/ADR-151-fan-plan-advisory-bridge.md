---
id: ADR-151
title: /fan-plan advisory bridge — parse [P?][USn][path] ACs into a PROPOSE-only read-only fan-out
status: ACCEPTED
proposed_at: 2026-06-17
proposing_session: S240
accepted_at: 2026-06-17
accepting_session: S241
related_plans: [PLAN-138, PLAN-134, PLAN-110]
related_adrs: [ADR-138, ADR-136-AMEND-1, ADR-144, ADR-132, ADR-107]
risk_tier: B
debate_required: true
---

# ADR-151 — /fan-plan advisory bridge

**Status:** ACCEPTED (S241, 2026-06-17 — shipped + CI green in PLAN-138 Wave B)
**Enforcement commit:** `bbe279ea` (PLAN-138 Wave B — `/fan-plan` command + parser shipped; ADR-138 g1 Codex ≥3-iter ACCEPT; CI green)

**Enforcement boundary:** advisory PROPOSE-ONLY — `/fan-plan` parses AC
lines and PRINTS a proposed read-only fan-out plan; it NEVER calls
`parallel()`/`agent()` and never auto-spawns. No hook emits
`permissionDecision`; the parser is fail-open (lenient: warn, never raise).

## Context

`github/spec-kit` (baseline pin **v0.11.0**, 2026-06-16) structures every
task line in its `tasks.md` template with an optional priority prefix
`[P0]/[P1]/[P2]/[P3]`, an optional user-story group `[USn]`, and a file
anchor `[path]` (spec-kit `templates/commands/tasks.md`). ceo-orchestration
formalized that **text-only** AC-line convention in **ADR-138** (ACCEPTED,
S177) and explicitly reserved a parser for a follow-up under its
**§Future Work (RESERVED)** clause — gated on (g1) Codex ≥3-iter ACCEPT on
the parser, (g2) an Owner GPG-signed sentinel for any hook addition, and
(g3) a backward-compat re-test of all PLANs `001-109+` (i.e. the full
current corpus, enumerated at execution time — not a hardcoded count).

PLAN-138 Wave B is the round-2 spec-kit residual that picks up exactly this
reserved parser. The parser reads the `[P?][USn][path]` grammar (ADR-138
lines 54-70) and proposes grouping `[P]`-parallel ACs by path into a
**read-only** investigation fan-out — the only fan-out shape the framework
permits per **ADR-136-AMEND-1**:

- **§4.1 Read-only only.** `agent()`/`parallel()`/`pipeline()` are confined
  to investigation / audit / recon fan-out. Any write, canonical-path edit,
  Owner-GPG ceremony, or `audit_emit` write path runs sequentially through
  the Owner-GPG sentinel (`check_canonical_edit.py`) and `/debate`-VETO.
- **§4.3 Structured returns.** A `parallel()` return MUST carry the ADR-141
  8-field shard schema; a free-prose reducer is a governance violation.

`/fan-plan` is therefore a **bridge**: it turns an AC block into a *proposal*
for the existing, confined fan-out machinery (the `audit-fanout` workflow
shape) — it does not introduce a new engine (PLAN-110 anti-goal #3) and it
does not auto-execute (anti-goal #1).

## Decision drivers

- **ADR-138 §Future Work (RESERVED).** The parser is the explicitly reserved
  follow-up; this ADR records the g1/g2/g3 acceptance contract it must meet.
- **ADR-136-AMEND-1 §4.1 (read-only confinement) + §4.3 (8-field structured
  returns).** Any fan-out the bridge proposes must stay inside this
  confinement — investigation only, schema-bound returns, never a write path.
- **ADR-144 §S220 (opts.model INERT for Workflow subagents).** With the
  global subagent override at `inherit`, a per-call `opts.model` is silently
  ignored: a fanned-out subagent runs the **session** model, not a requested
  downgraded tier. PLAN-134 GATE-W0a confirmed this empirically (verdict
  FAIL: `opts.model` had no measurable effect). This is the cost-envelope
  driver — the bridge cannot promise a cheaper tier.
- **ADR-132 (advisory-only planner doctrine) + ADR-107 (pair-rail mandatory
  L2+).** `/fan-plan` follows the `/goap` advisory-only precedent; its parser
  is L2 and gated by the Codex pair-rail (g1).

## Options considered

### Option 1 — Auto-spawning fan-out command (REJECTED)

Parse the AC block and directly call `parallel()` over the `[P]`-parallel
groups. **Rejected** — violates PLAN-110 anti-goal #1 (no `EXECUTE_COMMAND`
auto-execution) and removes the Owner from the spawn loop. The whole point of
ADR-136-AMEND-1 §4.1 is that the Owner-GPG sentinel and `/debate`-VETO are
not bypassable by a fan-out child; an auto-spawning bridge would route around
the human checkpoint.

### Option 2 — Advisory PROPOSE-ONLY bridge, prompt-enforced (RECOMMENDED)

Parse the AC block, PRINT a `PROPOSED read-only fan-out (Owner must confirm
each spawn)` block with a cost envelope, then STOP. The command body never
calls `parallel()`/`agent()`. Non-auto-spawn rests on **prompt-discipline**
this round (see §Consequences negative). **Recommended** — lowest blast
radius, satisfies the ADR-138 reserved-parser intent, imports no anti-goal,
keeps the Owner in the loop.

### Option 3 — Advisory bridge + a NEW `CEO_FANPLAN_CONFIRMED` spawn-hook
(DEFERRED)

Add hook-enforced parity with `/goap`'s `CEO_GOAP_CONFIRMED` gate in
`check_agent_spawn.py`. **Deferred** — a new governance hook is itself an
ADR-138 g2 event (Owner GPG sentinel) and widens PLAN-138's scope; recorded
as the optional follow-up in §Consequences and PLAN-138 OQ-B.

## Decision

Adopt **Option 2**: ship `/fan-plan` as an **advisory PROPOSE-ONLY bridge**.

- A stdlib-only, py3.9-safe, **ReDoS-safe** parser (`fan-plan-parser.py`)
  reads the `[P?][USn][path]` grammar per ADR-138, lenient (warn, never
  raise), with defaults priority→`P1`, story→`null`, path→`null`. It can
  scan the full plan corpus by parsed numeric id (g3 backward-compat).
- A `/fan-plan` command (`commands/fan-plan.md`, modeled on `commands/goap.md`)
  invokes the parser and PRINTS a proposed read-only fan-out grouping
  `[P]`-parallel ACs by path, **including a COST ENVELOPE** that states the
  proposed agent count and the inert-model caveat (per ADR-144 §S220), then
  STOPS. It never calls `parallel()`/`agent()`.
- Kill-switch `CEO_FANPLAN=0` disables the command.

### Acceptance contract (ADR-138 g1/g2/g3)

- **g1** — Codex pair-rail ≥3-iter ACCEPT on the parser code (recorded at
  PLAN-138 execution, V2).
- **g2** — Owner GPG-signed sentinel for the canonical/cache-stable edits
  (PLAN-138 V3 ceremony).
- **g3** — the parser re-tests ALL plans `001-current` (the full enumerated
  corpus on disk, not a hardcoded floor) with zero raised exceptions and zero
  rejected lines (lenient backward-compat).

## Consequences

### Positive

- Picks up ADR-138's reserved parser as an advisory, reversible addition.
- Reuses the existing confined `audit-fanout` fan-out shape (ADR-136-AMEND-1)
  — no new engine, no anti-goal imported.
- Keeps the Owner in the spawn loop; the cost envelope makes the
  inert-model reality (`opts.model` ignored → session-model tier) explicit at
  the point of proposal.

### Negative (recorded honestly)

- **`opts.model` is EMPIRICALLY INERT for Workflow subagents** (ADR-144 §S220
  + PLAN-134 GATE-W0a FAIL). A proposed fan-out therefore runs the **session
  model** — the bridge **cannot promise a downgraded tier**. A `/fan-plan`
  proposed from a CEO Opus session fans out at Opus tier; the cost envelope
  states this so the Owner is not misled into expecting Haiku-tier pricing.
- **Non-auto-spawn rests on PROMPT-DISCIPLINE ONLY.** Unlike `/goap`, whose
  non-delegation is hook-enforced (`check_agent_spawn.py` blocks any
  GOAP-tagged spawn lacking `CEO_GOAP_CONFIRMED=1` + a `## GOAP CONFIRM`
  block), `/fan-plan`'s "PROPOSE-only, never auto-spawn" boundary is
  **structurally weaker** — it is a contract in the command prompt, not a
  hook gate. An optional deferred follow-up would add
  `CEO_FANPLAN_CONFIRMED` spawn-hook parity in `check_agent_spawn.py`; it is
  NOT shipped this round because a new governance hook is itself an ADR-138 g2
  event and widens scope (see Option 3 + PLAN-138 OQ-B).

### Neutral

- PROPOSED status only — ship the code, leave the ADR PROPOSED, promote in a
  dedicated ceremony (PLAN-138 OQ1 default, ADR-136/137 precedent).
- The parser is lenient by design: malformed AC lines degrade to defaults,
  never block.

## Blast radius

**L2.** Adds one advisory command (`commands/fan-plan.md`), one stdlib-only
parser script (`scripts/fan-plan-parser.py`), one test file, and this ADR.
No hook is added or modified this round; no `permissionDecision` is emitted;
no canonical guard is weakened. The parser is read-only over the plan corpus.
A revert removes the command + parser + ADR with no migration. The only
governance surface touched is the cache-stable command/skill inventory count,
reconciled in PLAN-138 Wave V under the Owner GPG ceremony.

## References

- ADR-138 §Future Work (RESERVED) — the reserved parser this ADR implements
- ADR-136-AMEND-1 §4.1 (read-only confinement) + §4.3 (8-field returns)
- ADR-144 §S220 (opts.model inert for Workflow subagents) + PLAN-134 GATE-W0a
- ADR-132 (advisory-only planner doctrine) — `/goap` precedent
- PLAN-138 Wave B (B.1-B.6) + OQ-B (enforcement strength)
- spec-kit v0.11.0 `templates/commands/tasks.md` — `[P?][USn][path]` grammar
