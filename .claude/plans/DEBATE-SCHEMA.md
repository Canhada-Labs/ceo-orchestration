---
id: DEBATE-SCHEMA
title: Multi-round debate — directory layout, round semantics, consensus contract
status: accepted
created: 2026-04-11
owner: CEO
depends_on: [PLAN-002, PLAN-SCHEMA]
---

# Debate Schema — How multi-round debate is structured on disk

> This document is the contract for multi-round plan debates. It defines
> the directory layout, round semantics, agent output format, consensus
> file format, and the `/debate` slash command entry points.
>
> **Why this exists:** PLAN-002 §1 thesis — "debate needs structure
> before it needs depth". Round 1 on PLAN-001 and PLAN-002 both worked
> well as ad-hoc synthesis directly inside the plan file, but that
> approach does not scale past one round. Three rounds without a file
> layout and a slash command is chaos. One round with a schema is a
> foundation we can extend.
>
> **Demotion (PLAN-134 W1):** debate is a **design-coherence check**,
> not a truth gate — see §13. A clean outcome is recorded as
> `design-coherent` (formerly "0 VETO") and never authorizes shipping;
> only the verification cascade does (PROTOCOL.md §Verification
> cascade), with the Codex pair-rail as the sole LLM truth gate.

---

## 1. When to run a debate

Debate is mandatory for **L3+ blast radius** plans (touches 3+ modules,
changes a contract between producers and consumers, or affects shared
state). See `PROTOCOL.md` §"Plan → Debate → Execute".

Debate is optional but recommended for **L2** plans that cross skill
boundaries (e.g. a frontend feature that needs backend schema changes).

Debate is **not** run for **L1** plans (single-file fixes, config
tweaks, documentation edits, typo fixes).

## 2. Round semantics

A debate has **1 or more rounds** (no hard maximum). Each round has the
same structure but agents build on the output of previous rounds.

| Round | Agents read | Agents write | CEO writes |
|---|---|---|---|
| **1** | the plan (proposal), their own SKILL.md | their critique | `round-1/consensus.md` synthesizing round 1 |
| **2** | round-1/consensus.md, all round-1 critiques, their own SKILL.md | a revised critique that responds to the consensus | `round-2/consensus.md` |
| **N (3+)** | previous consensus.md, all previous critiques | a revised position | `round-N/consensus.md` or (on final round) `round-N/approved.md` |

**Each round spawns the same 3–6 agents** (same archetypes, potentially
different personas if team.md is updated mid-debate). 6 archetypes were
used in PLAN-113 Wave A debate with a `design-coherent` outcome
(recorded at the time as "0 VETO" — re-labeled per §13.1); 3 is a
reasonable minimum.

**Minimum:** 1 round. One round is already valuable because it runs
forced-perspective critiques in parallel.

**Typical:** 1–2 rounds for L3 plans; 3–6 rounds for L4+ plans with
cross-cutting concerns or security implications (PLAN-112, PLAN-113).
Continue until all archetypes reach ACCEPT or ADJUST_PROCEED with no
blocking findings.

**Final artifact:** the last round produces `approved.md` (not
`consensus.md`) under the `architect/` directory (see §3). If an impasse
persists past round 3, escalate to the Owner — something is wrong with
the plan.

## 3. Directory layout

A plan that uses multi-round debate creates a sibling subdirectory:

```
.claude/plans/
├── PLAN-003-something.md               # the plan file
└── PLAN-003/                           # sibling subdirectory (debate + artifacts)
    └── architect/
        ├── round-1/
        │   ├── proposal.md             # CEO's initial proposal (≤ 300 lines)
        │   ├── vp-engineering.md       # agent critique
        │   ├── security-engineer.md    # agent critique
        │   ├── devops-engineer.md      # agent critique
        │   └── consensus.md            # CEO synthesis of round 1
        ├── round-2/
        │   ├── vp-engineering.md       # agents read round-1/consensus.md + critiques
        │   ├── security-engineer.md
        │   ├── devops-engineer.md
        │   └── consensus.md            # CEO synthesis of round 2
        └── round-N/                    # final round (N ≥ 1; actual practice 3–6)
            └── approved.md             # Owner-signed approval — terminal artifact
```

> **Historical note:** early plans (PLAN-001–PLAN-030) used `debate/` as the
> subdirectory name and `consensus.md` as the per-round artifact. Current
> practice (PLAN-100+) uses `architect/` with `round-N/approved.md` as the
> terminal artifact and Owner GPG signature on the approval file. Both layouts
> are accepted by `validate_governance_fast.py` (it does not descend into
> `PLAN-NNN/` subdirs).

**Naming invariants:**

- The plan file is `PLAN-<NNN>-<slug>.md` under `.claude/plans/`.
- The artifact subdirectory is `PLAN-<NNN>/` (matching the NNN).
- Within it, `architect/` (current practice) or `debate/` (legacy) holds rounds.
- Round directories are `round-1/`, `round-2/`, … — no zero-padding.
- Agent critique files are `<archetype-kebab-case>.md`, matching the
  archetype slugs in `team.md` (or the domain personas file).
- Intermediate round files: `consensus.md` (synthesis) or per-round critique.
- `anonymization-map.md` (per round, PLAN-134 W1) records the
  `Critic-X` ↔ archetype mapping used for anonymized synthesis (§13.2).
  It is NOT an agent critique file.
- Terminal artifact: `approved.md` (current) or `synthesis.md` (legacy).
- The `examples/` subdirectory under `.claude/plans/` may hold non-plan
  fixtures (see Item D.2 fixture and PLAN-SCHEMA.md §1 naming rule).

## 4. Agent critique file format

Every agent critique file in `round-N/<archetype>.md` follows this
structure:

```markdown
---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (persona name if team.md has one)
generated_at: 2026-04-11T14:30:00Z
---

## Verdict

ADJUST | REJECT | ACCEPT — one-word overall position.

## Summary (≤ 3 bullets)

- What's the plan trying to do
- Where I think it's strong
- Where I think it's weak

## Risks

Ordered list, most severe first. Each with:
- Risk ID (e.g. R-VP1, R-SEC2)
- Severity: LOW | MEDIUM | HIGH | CRITICAL
- Description: 1–3 sentences
- Mitigation: 1–3 sentences (concrete change to the plan)

## Must-fix (blocking)

Numbered list. Items the CEO MUST address before `status` moves from
`draft` to `reviewed`. If an agent marks nothing as must-fix, their
verdict must be ACCEPT.

## Nice-to-have (advisory)

Numbered list. Items the CEO may defer to a later sprint.

## Unseen by the original plan

Numbered list. Issues the plan does not mention at all. These carry
extra weight because they reveal blind spots.

## What I would NOT change

Things the plan does well. Defends a correct choice from being
"improved" into a regression.
```

Strict structure lets the CEO mechanically merge critiques in the
consensus file. Agents may add free-form sections at the end but the
7 required headers above are non-negotiable.

## 5. Consensus file format

`round-N/consensus.md` has a frontmatter contract (Architect U7 debate
finding) + structured body. **Synthesis input is anonymized** (PLAN-134
W1): the synthesizer consumes critiques labeled `Critic-A/B/C…` with
persona names stripped — see §13.2 for the protocol and the
`anonymization-map.md` audit record.

```markdown
---
plan: PLAN-003
round: 1
rounds_synthesized: [round-1]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
decisions_revised_in_plan:
  - "§5.1 — cost cap now hardcoded in runner"
  - "§7.A.3 — rotation threshold added"
synthesized_at: 2026-04-11T15:00:00Z
synthesized_by: CEO
---

## Consensus findings (2+ agents flagged)

Numbered list. Each with:
- Finding ID (e.g. C1, C2, ...)
- Which agents flagged it (by archetype)
- Agreed severity
- Agreed mitigation
- Where it lands in the plan (§ reference)

## Single-agent insights kept

Numbered list. Each with the agent and rationale for accepting.

## Single-agent insights rejected / deferred

Numbered list. Each with the agent, reason for rejecting, and (if
deferred) which future sprint picks it up.

## Plan adjustments

Inline summary of every `§` that was changed in the plan file. The
actual edits live in the plan file itself; this section is an index.

## Round verdict

PROCEED | RUN-ANOTHER-ROUND | ESCALATE-TO-OWNER

- PROCEED (or ADJUST_PROCEED) → plan moves from `draft` to `reviewed`, execution starts
- RUN-ANOTHER-ROUND → CEO spawns round N+1
- ESCALATE-TO-OWNER → the plan has a decision the CEO cannot resolve
  alone (e.g. two agents have opposing blocking verdicts that can't
  be reconciled). Owner decides.
```

## 6. Final approval file (terminal round)

When the final round completes, the CEO writes `round-N/approved.md`
(current practice) instead of `round-N/consensus.md`. It summarizes the
full debate arc, records the Owner's ratification, and links back to the
plan's adjusted sections. Legacy plans used `round-3/synthesis.md` for
the same purpose.

```markdown
---
plan: PLAN-003
rounds_completed: 3
final_verdict: PROCEED | ESCALATE-TO-OWNER
synthesized_at: 2026-04-11T18:00:00Z
synthesized_by: CEO
---

## 3-round arc summary

- Round 1: what the 3 agents found → N consensus findings, M adjustments
- Round 2: which concerns persisted after round-1 adjustments → N' more
- Round 3: final position of each agent + whether convergence happened

## Final plan deltas

Enumerated list of every section in the plan file that changed as a
result of the 3-round debate.

## Lessons for the debate process itself

If anything about the process itself should change (e.g. an archetype
shouldn't have been in the debate, a new archetype should be added for
future plans, a new required header in the critique format), capture
it here. Feeds PLAN-003+ meta-improvements.
```

## 7. Slash command — `/debate`

The `/debate` slash command (shipped in Sprint 2 D.2) is the operator
entry point. It has 4 sub-forms:

### `/debate start <PLAN-NNN> "[short proposal]"`

- Creates `.claude/plans/PLAN-<NNN>/debate/round-1/proposal.md`
- CEO spawns 3 agents (archetypes chosen by the CEO based on the plan's
  scope — typically VP Engineering + Staff Security + DevOps, but
  domain-specific plans pull from the domain team-personas)
- Each agent reads: the plan file + `round-1/proposal.md` + their own
  SKILL.md + `team.md`
- Each agent writes: `round-1/<archetype-slug>.md`

### `/debate round2 <PLAN-NNN>`

- CEO writes `round-1/consensus.md` synthesizing round 1
- Spawns 3 agents again
- Each agent reads: `round-1/consensus.md` + all round-1 critiques +
  their SKILL.md
- Each agent writes: `round-2/<archetype-slug>.md`

### `/debate round3 <PLAN-NNN>`

- CEO writes `round-2/consensus.md`
- Spawns 3 agents again
- Each agent reads: `round-2/consensus.md` + all round-2 critiques +
  their SKILL.md
- Each agent writes: `round-3/<archetype-slug>.md`
- CEO writes `round-3/synthesis.md` with the final adjusted plan

### `/debate status <PLAN-NNN>`

- Reports the current round, list of agents that have responded, list
  pending, and the last consensus verdict

## 8. Agent spawn protocol during debate

Every debate agent spawn MUST follow `PROTOCOL.md` §"Spawn Protocol":

1. File assignment — the agent CAN write only its own
   `round-N/<archetype>.md` file; all other paths are FORBIDDEN
2. Persona loaded from `team.md` (or domain personas)
3. Skill loaded from the archetype's primary skill
4. Full `## AGENT PROFILE` + `## SKILL CONTENT` + `## FILE ASSIGNMENT`
   sections in the prompt
5. `check_agent_spawn.py` hook verifies the compliance before the spawn
   actually runs

Debate spawns are no exception to the hook. If a debate spawn is blocked,
the CEO fixes the prompt before retrying — the hook is the mechanical
enforcement layer and must not be bypassed.

## 9. Cost and budget

Per PLAN-002 §3 Q2:

- Each round = 3 agents × ~30K tokens (full SKILL.md + plan + previous
  consensus) = ~90K tokens per round
- 3 rounds = ~270K tokens maximum per debate
- No enforced token ceiling — 1M context absorbs it; quality > economy

## 10. Examples

See `.claude/plans/examples/debate-round-1/` for a fully-populated
round-1 fixture with real-looking content (not lorem ipsum). The
fixture references a fake plan ID `example` that lives under
`.claude/plans/examples/` — outside the `PLAN-<NNN>-<slug>.md`
namespace per PLAN-SCHEMA.md §1.

## 11. Sprint 2 debate round 1 on PLAN-002 (reference implementation)

PLAN-002 itself ran a round 1 debate on 2026-04-11. The output was
captured inline in `PLAN-002-sprint-2-hardening.md` §8 + §15 rather
than split into separate files. That was a pragmatic choice for a
one-off debate on a 1100-line plan where the round-1 consensus was
the only round planned. For future plans that will run 2+ rounds, the
on-disk layout in §3 above is the canonical structure.

Sprint 3+ debates SHOULD use the on-disk layout. The inline-in-plan
approach is deprecated after Sprint 2.

---

## 12. N-round formal semantics (Sprint 11 amendment, ADR-032)

Sprint 2 §2 defined a 1-to-3-round model; Sprint 11 generalizes this to
an **N-round** model with convergence-based termination. The v1 layout
in §3 is unchanged (additive-only); only the progression semantics grow.

### 12.1 Round indexing and caps

- Rounds are **1-indexed**: `round-1/`, `round-2/`, `round-3/`, ...
- **Default max rounds: 5** (`--max-rounds 5` in `debate-orchestrate.py`).
- **HARD cap: 10.** The orchestrator refuses `--max-rounds > 10` at
  argparse time. Past 10 rounds the debate has failed — escalate to
  Owner. Any flag value in `[1, 10]` is legal; the default `5` is the
  sweet spot per ADR-032 Decision Drivers.
- **Minimum: 1 round.** Single-round debate still valid (the original
  PLAN-001 / PLAN-002 pattern), explicitly retained for back-compat
  + as the `CEO_SOTA_DISABLE=1` fallback mode.

### 12.2 Convergence (Jaccard similarity)

Between each pair of consecutive rounds N-1 and N (N >= 2), the
orchestrator computes the **Jaccard similarity** of the risk sets:

    Jaccard(R_{N-1}, R_N) = |R_{N-1} ∩ R_N| / |R_{N-1} ∪ R_N|

Where `R_k` is the union of normalized risk bullets from every agent
critique file in round k. "Risk bullet" = a line starting with `- `
under a `## Risks` heading. Normalization strips ID prefixes (`R-VP1:`,
`C1:`, ...), punctuation, and collapses whitespace. See
`.claude/scripts/debate-converge.py` §Algorithm.

- **Threshold: 0.7** (default; overridable via `--threshold`).
- `Jaccard >= 0.7` → **converged**.
- `Jaccard < 0.7` → **not converged**.

### 12.3 Red Team contingent archetype (M1 anti-groupthink gate)

If convergence is detected at **round N <= 2**, the orchestrator
**MUST** spawn a Red Team archetype BEFORE marking consensus. The
rationale is the same-LLM problem: Claude agents that agree in 1–2
rounds might be genuinely converging OR sharing a training-blindspot.
The Red Team attacks the consensus, not the proposal.

- Red Team archetype: `red-team`
- Primary skill: `chaos-and-resilience`
- Secondary skill: `security-and-auth`
- Output file: `round-<N+1>/red-team.md`
- **CONTINGENT**: the Red Team is not a standing team member. It is
  spawned only when the M1 gate fires. See `.claude/team.md`
  §Red Team Archetype (contingent).
- The Red Team critique counts toward consensus — its findings are
  synthesized into the subsequent consensus.md alongside the six
  standard archetypes.

If convergence is detected at **round N > 2**, the Red Team is NOT
required — by round 3+, agents have been exposed to multiple
consolidated critiques and groupthink signal is weaker. The
orchestrator marks consensus and writes `round-N/consensus.md`.

### 12.4 Unresolved consensus (max-rounds exhausted)

If `round_num >= max_rounds` and convergence is still not met:
- Orchestrator writes `round-<max_rounds>/consensus.md` with
  `status: unresolved`, `final_jaccard: <number>`, and an explicit
  Escalation-required body.
- Audit event `debate_event` with `phase: consensus` is emitted.
- Owner intervention required — the plan has a decision the CEO
  cannot resolve via debate alone.

### 12.5 Redaction contract (M6 — secret hygiene)

**Before** feeding round N's consolidated critiques into round N+1
agents' prompts, the orchestrator **MUST** apply
`_lib.redact.redact_secrets()` to the concatenated critique text.
This closes the failure mode where an agent accidentally pastes an
API key into a risk description, and the orchestrator would
otherwise propagate it downstream.

Implementation: `debate-orchestrate.py::redact_consolidated(text)`
calls `redact_secrets(text, max_chars=0)` (no truncation; bounded
growth invariant still caps output at 2x input). Output is wrapped
in a fenced block under the heading
`## Previous round consolidated critiques (redacted)` in each
round N+1 agent prompt.

### 12.6 Back-compat with v1 (§1–§11)

- §3 directory layout unchanged.
- §4 agent critique file format unchanged.
- §5 consensus file format unchanged; §12.4 adds a `status: unresolved`
  frontmatter variant.
- §7 slash command `/debate round2 / round3 / status` unchanged — the
  orchestrator CLI `debate-orchestrate.py` is an alternative entry point
  for automated multi-round flows.
- §9 cost estimate: N rounds × ~90K tokens/round. Past 5 rounds, opt
  into `--max-rounds` explicitly.

### 12.7 Audit events

Per round, the orchestrator emits at minimum:
- One `debate_event` with `phase: start` (before any agent files).
- One `debate_event` per agent with `phase: agent-done`,
  `agent: <slug>`, `artifact_path: round-<N>/<slug>.md`.
- If Red Team fires: one `debate_event` with `phase: agent-done`,
  `agent: red-team`, `artifact_path: round-<N+1>/red-team.md`.
- At consensus (round > 2 convergence OR max-rounds exhaust): one
  `debate_event` with `phase: consensus`,
  `artifact_path: round-<N>/consensus.md`,
  `consensus_adjustments_count: <int>`.

All audit emission is fail-open per `audit_emit.py` contract.

### 12.8 CEO_SOTA_DISABLE fallback (S4)

When `CEO_SOTA_DISABLE=1`, `debate-orchestrate.py` operates in
**single-round mode**: only round 1 is generated, no convergence check,
no Red Team gate. This is the safety valve for environments where
the multi-round machinery is not wanted (CI previews, ephemeral
worktrees, a roll-back scenario). The fallback matches the PLAN-001 /
PLAN-002 single-round-debate pattern exactly.

### 12.9 Additive-only contract

Per ADR-032 §Decision, this schema may GAIN fields in v1 but may not
RENAME or REMOVE. Consumers tolerate unknown fields. A future v2
rev-bump is required if convergence semantics change (e.g. switching
from Jaccard to cosine similarity).

---

## 13. Debate demotion — design-coherence check + anonymized synthesis (PLAN-134 W1)

Per PLAN-134 W1 (research 2510.07517): same-LLM archetype agreement
measures **internal coherence**, not external truth. This section is
additive (per §12.9) and re-scopes what a debate verdict MEANS. It does
not change the layout (§3), critique format (§4), or round semantics
(§2, §12).

### 13.1 What a debate verdict certifies

- A debate that ends with no blocking findings is recorded as
  **`design-coherent`** — the label formerly written as "0 VETO" /
  "0-VETO". Historical artifacts keep the old label; new consensus /
  approval files use `design-coherent`.
- `design-coherent` certifies that the design is internally coherent
  under forced perspectives (§4). It does NOT certify external truth —
  all archetypes are the same LLM (PROTOCOL.md §Honest limitation;
  `feedback-codex-validates-reality-debate-validates-design`).
- **Debate output does NOT authorize shipping.** Shipping is authorized
  only by the verification cascade (PROTOCOL.md §Verification cascade):
  V0 plan-check → V1 deterministic verification (tests / hooks / CI) →
  V2 Codex pair-rail — the **sole LLM truth gate**, fail-closed to the
  Owner (no Codex verdict → escalate, never self-approve) → V3 Owner
  GPG ceremony. A `design-coherent` debate satisfies V0 only; it never
  skips, weakens, or substitutes for V1–V3.

### 13.2 Anonymized synthesis (anti-halo)

Before any synthesis/judge step (the CEO writing `consensus.md`,
`approved.md`, or `synthesis.md`):

1. Assign each critique a neutral label `Critic-A`, `Critic-B`,
   `Critic-C`, … (one per archetype; assignment order is arbitrary).
2. Strip persona and archetype names from the critique text handed to
   the synthesizer — the synthesizer prompt consumes ONLY the
   anonymized text, so findings are weighed on content, not on which
   persona said them.
3. Record the mapping in `round-N/anonymization-map.md` for audit:

```markdown
---
plan: PLAN-003
round: 1
labels:
  Critic-A: vp-engineering
  Critic-B: security-engineer
  Critic-C: devops-engineer
---
```

4. The consensus file may reference findings by `Critic-X` label;
   auditors resolve identities via the map. On-disk critique files keep
   their `<archetype-slug>.md` names (§3) — anonymization applies to
   the synthesizer's INPUT, not to the stored artifacts.
5. `anonymization-map.md` is a non-critique file: convergence and
   consolidation tooling (`debate-converge.py`, `debate-orchestrate.py`)
   excludes it from the agent-critique set.
