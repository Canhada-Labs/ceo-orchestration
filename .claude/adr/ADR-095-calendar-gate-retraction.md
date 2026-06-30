# ADR-095 — Calendar gate retraction (14d CI green + 30d no-retag)

## Status

ACCEPTED — Wave session 73 ceremony 2026-04-29 — Owner key 0000000000000000000000000000000000000000

## Date

2026-04-29

## Enforcement commit

Documentation-only / no enforcement commit (calendar gate retraction is procedural; enforcement is the absence of calendar tracking, observed via README + READINESS-STATUS doc updates).

## Context

`docs/READINESS-STATUS.md` and audit-v2 verdict.md (CTO Round-2)
defined six TRIAL-prerequisite gates:

1. **14-day CI green streak on `main`** (calendar-bound)
2. **30-day no-retag streak** (calendar-bound)
3. **emit_mcp_injection_finding shipped** — DONE Wave B
4. **Cost reporting accurate end-to-end** — DONE Wave B
5. **One refused-ADR retracted** — DONE (ADR-091 retracted, Wave C)
6. **Outside reviewer 1-page second opinion** — Owner-physical recruit

ADR-093 added a 7th calendar gate: **60-day refused-ADR moratorium**
(2026-04-27 → 2026-06-26).

Owner directive 2026-04-29 ("não vou esperar calendário"): close the
calendar-bound gates that are NOT structurally protective. Gates #1
(14d CI) + #2 (30d no-retag) measure release discipline empirically;
they delay TRIAL by ~5 weeks without changing what's true about the
framework today. Gate #6 (outside reviewer) is structural (independent
human eye) — kept. Gate #7 (60d moratorium ADR-093) is structural
(refusal-pattern brake) — kept.

This ADR retracts gates #1 + #2 only. The framework's TRIAL transition
becomes:

- gate #1 (14d CI green) — RETRACTED via this ADR
- gate #2 (30d no-retag) — RETRACTED via this ADR
- gate #3 (emit_mcp_injection_finding) — DONE Wave B
- gate #4 (cost reporting) — DONE Wave B
- gate #5 (refused-ADR retracted demo) — DONE Wave C
- gate #6 (outside reviewer) — KEPT (Owner-physical, no token path)
- gate #7 (60d moratorium ADR-093) — KEPT (structural protection)

After this ADR, the only remaining TRIAL blockers are gates #6 + #7.
Per ADR-096 (vibecoder-only positioning), TRIAL is **no longer a goal**
— the framework targets MAINTENANCE-MODE-VIBECODER, which does not
require external-evaluator gating.

## Decision drivers

- **Time-based gates measure stability across calendar time, not
  correctness today.** A 14-day green streak proves CI is stable
  under cadence; a 30-day no-retag streak proves release discipline.
  Both are properties of project maintenance over time, not artifacts
  in the code. Code-correctness gates (#3, #4, #5) are already DONE.
- **Owner directive 2026-04-29.** Aligned with the framework's
  vibecoder-only positioning (ADR-096). External evaluator readiness
  is no longer a goal.
- **ADR-093 60d moratorium NOT retracted.** ADR-093 specifically
  brakes the "refuse-via-ADR" pattern that audit-v2 caught
  (Sessions 60-67 generated 9 refusal ADRs in 4 days). Owner
  directive aligns with ADR-093 ("code tudo que faltou" = the
  opposite of refusing more work). ADR-093 stays.
- **Outside reviewer gate (#6) NOT retracted.** Same-LLM problem
  (PROTOCOL.md §Honest limitation) is a real audit blind spot.
  External human review remains structurally valuable even in
  vibecoder-only positioning. Path: when Owner has time, recruit.
  Without 1-page external review, the framework's claims are
  self-validated only — same-LLM bias undisclosed to evaluators.
- **No `--no-verify` / `--no-gpg` shortcuts.** This ADR is itself
  Owner-signed via sentinel ceremony — the retraction is held to
  the same governance standard as any canonical edit.

## Options considered

### Option A — Retract all 7 calendar gates

Rejected. ADR-093 60d moratorium is structural protection against the
specific failure mode audit-v2 documented; retracting it 2 days in
re-creates the exact pattern. Outside reviewer gate (#6) addresses
same-LLM bias, which doesn't disappear with positioning change.

### Option B — Retract gates #1 + #2 only (CHOSEN)

Closes the time-based discipline gates. Keeps structural gates
(refusal moratorium, outside reviewer). Aligns with vibecoder-only
positioning (ADR-096) without abandoning audit-v2's actual fixes.

### Option C — Wait out the calendar (original plan)

Rejected per Owner directive 2026-04-29.

### Option D — Retract via narrative without ADR

Rejected — violates the closure-honesty rule (ADR-092). A calendar
gate is a published commitment in `docs/READINESS-STATUS.md`;
retraction must be ADR-formal.

## Decision

**Option B.** Two-part rule:

### Part 1 — Retract gate #1 (14d CI green streak)

`docs/READINESS-STATUS.md` §"Calendar gates dominant" updated:

  - 14d CI green streak: ~~Day 2/14, clears 2026-05-12~~ → **retracted
    via ADR-095 (2026-04-29)**

Rationale appended: time-based discipline gate retracted in
vibecoder-only positioning (ADR-096). CI stability remains
empirically observable (CHANGELOG cadence) but no longer gates
verdict transitions.

### Part 2 — Retract gate #2 (30d no-retag streak)

`docs/READINESS-STATUS.md` §"Calendar gates dominant" updated:

  - 30d no-retag streak: ~~Day 1/30, clears 2026-05-28~~ → **retracted
    via ADR-095 (2026-04-29)**

Rationale appended: vibecoder-only positioning means re-tag cadence
is informal. ADR-093 60d moratorium covers the refusal-pattern brake
that "no-retag" was an indirect proxy for.

### Part 3 — Verdict transition

`docs/READINESS-STATUS.md` overall verdict transitions:

  - From: **TRIAL-PENDING-SOAK** (earliest TRIAL date 2026-06-26)
  - To: **MAINTENANCE-MODE-VIBECODER** (TRIAL no longer a goal)

The framework is declared done for vibecoder-only positioning per
ADR-096. TRIAL → ADOPT path remains AVAILABLE (gates #6 + #7 still
defined) but no longer scheduled.

### Part 4 — ADR-093 + outside reviewer NOT retracted

ADR-093 60-day refusal moratorium (Day 2/60, clears 2026-06-26)
remains structural protection. Owner directive ("code tudo que
faltou pra terminar") aligns with ADR-093 — the moratorium prohibits
NEW refusal ADRs, not new code or feature ADRs.

Outside reviewer gate (#6) remains structural — addresses same-LLM
bias documented in PROTOCOL.md §Honest limitation. Recruitment is
Owner-physical and not bound to a calendar.

## Consequences

**Positive (+):**
- Closes 2 of 7 TRIAL gates in tokens, today.
- `docs/READINESS-STATUS.md` no longer publishes calendar countdowns
  that won't graduate the framework anyway (per ADR-096).
- Honest framing: the framework is what it is today, not what it
  promises to be in 5 weeks.
- Aligns with vibecoder-only positioning (ADR-096).

**Negative (-):**
- External evaluators reading old `docs/READINESS-STATUS.md` snapshots
  will see calendar gates that are no longer enforced. Mitigation:
  this ADR + READINESS-STATUS update + CHANGELOG explicitly note the
  retraction.
- Removes implicit "stability proof" that 14d CI green provided.
  Mitigation: CHANGELOG cadence + commit log are still observable.

**Neutral (~):**
- Gates #3, #4, #5 (code-correctness) remain DONE.
- Gate #7 (ADR-093) remains active.
- Gate #6 (outside reviewer) remains active.

## Blast radius

L3+. Touches:
- This ADR
- `docs/READINESS-STATUS.md` (verdict + gate-list update)
- `CHANGELOG.md` (entry referencing this ADR)
- `CLAUDE.md` §6 (current state — handoff implications)

## Compliance checklist

| Item | Verification |
|---|---|
| Gate #1 (14d CI) retracted in READINESS-STATUS | grep `retracted via ADR-095` in `docs/READINESS-STATUS.md` |
| Gate #2 (30d no-retag) retracted in READINESS-STATUS | same |
| ADR-093 NOT retracted | `.claude/adr/ADR-093-*.md` Status remains ACCEPTED |
| Outside reviewer gate NOT retracted | gate #6 still in READINESS-STATUS |
| Verdict transitions to MAINTENANCE-MODE-VIBECODER | `docs/READINESS-STATUS.md` §Verdict |
| CHANGELOG entry references this ADR | `CHANGELOG.md` 2026-04-29 |
| ADR file landed via Owner sentinel ceremony | `.claude/plans/PLAN-044/architect/round-5/approved.md` declares this path |

## Related decisions

- ADR-093 — 60-day refused-ADR moratorium (NOT retracted)
- ADR-096 — Vibecoder-only by design (companion ADR)
- ADR-097 — Function-length advisory-permanent (companion)
- audit-v2 verdict.md — original 6-gate TRIAL prerequisite list
- `docs/READINESS-STATUS.md` — gate tracking (updated)
