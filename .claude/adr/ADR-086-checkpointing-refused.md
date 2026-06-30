# ADR-086 — Phase checkpointing REFUSED — audit-log + memory cover the use case

## Status

ACCEPTED — Wave A re-ceremony 2026-04-27 — round-21 sentinel — Owner key 0000000000000000000000000000000000000000

## Context

PLAN-056 Phase 4 originally proposed 3-5 dev-dias to ship phase
checkpointing — explicit `checkpoint(state) → resume(state)` API
mirroring LangGraph's checkpointing capability. Trigger was the
Session 60 landscape audit identifying checkpointing as 1 of 3 real
gaps.

Owner directive Session 67 (Claude-only depth-over-breadth) reframes
this as a gap that is **already filled by existing infrastructure
under a different name**.

## Existing checkpoint-equivalents in ceo-orchestration

| Mechanism | What it captures | When it fires |
|---|---|---|
| `audit-log.jsonl` | Every tool call + agent spawn + governance event with full inputs/outputs (post-redaction) + HMAC chain | PostToolUse hook — automatic |
| `~/.claude/projects/<slug>/memory/*.md` | Per-type memory (user/feedback/project/reference) | CEO writes during session per memory protocol |
| `.claude/plans/PLAN-NNN/...` | Plan state, audit findings, debate consensus, staged code | CEO writes per plan lifecycle |
| `.claude/plans/PLAN-NNN/architect/round-N/approved.md` + `.asc` | Owner-signed authorization for canonical edits | Owner ceremony |
| `git history` | Every commit with full diff + commit message | Per commit |

A LangGraph-style "checkpoint(graph_state)" call would write a
duplicate of state already captured by audit-log + memory + plan
files + git. Specific examples of resume-from-checkpoint patterns
already covered:

- **Resume after CLI restart**: memory files reload automatically
  (per CLAUDE.md Gate 1); plan files in `.claude/plans/` are
  durable git artifacts; CEO reads `git log` for last-state context.
- **Resume after debate Round-1 across sessions**: `consensus.md`
  in `audit/round-N/` is the durable checkpoint.
- **Resume after Phase A → Phase B in multi-phase plan**: plan file
  `status:` field + `executing_at:` timestamp + commit history.
- **Resume after Owner ceremony interruption**: sentinel `.asc` file
  + staged-code dir state are durable.

## Decision

**REFUSE PLAN-056 Phase 4 (phase checkpointing)** with reason
`(b) cost-exceeds-benefit` per refused-ADR taxonomy.

Specifically:

1. No new `checkpoint(state) → resume(state)` API.
2. No new state-machine module for inter-phase resume.
3. Reaffirm existing infrastructure as canonical:
   - `audit-log.jsonl` is **the** event ledger.
   - `memory/*.md` is **the** cross-session knowledge store.
   - Plan files in `.claude/plans/` are **the** workflow state.
   - `git history` is **the** commit-level state.
4. Document this resolution in `docs/STATE-RECOVERY.md` (new doc-only
   shipped under PLAN-056 Phase 6 closeout) explaining the resume
   patterns operators use today.

## Consequences

### Positive

- 3-5 dev-dias removed from roadmap permanently.
- No new state-machine surface area to maintain.
- Existing infrastructure (audit-log + memory + plans + git) gains
  documented status as the canonical state-recovery story.
- `docs/STATE-RECOVERY.md` becomes a positive deliverable that
  adopters can read instead of feeling there's an unfilled gap.

### Negative

- LangGraph users coming to ceo-orchestration may expect explicit
  `graph.checkpoint()` API and find it absent.
  - Mitigation: `STATE-RECOVERY.md` shows which artifact answers
    each resume question.
- Future Claude harness updates that introduce native checkpoint
  primitives may make this ADR obsolete.
  - Mitigation: ADRs are revisable; if Anthropic ships
    `Claude.checkpoint()`, this ADR can be amended.

### Neutral

- No code change today (refusal is positional). Documentation update
  in `docs/STATE-RECOVERY.md` is the only deliverable.

## Alternatives considered

### A. Implement minimal checkpoint API as compat-layer (REJECTED)

Cost ~3-5 dev-dias. Rejected because:
- Wraps audit-log + memory + plan files in a different surface API.
- Adds maintenance burden.
- Claude-only directive: framework is opinionated; we don't add
  speculative compat shims.

### B. Defer to PLAN-058+ (REJECTED)

Indefinite deferral leaves the question open. Better to refuse
explicitly with positive framing.

### C. Document existing patterns only (CHOSEN — see Decision)

This is what's shipped: `STATE-RECOVERY.md` documents the existing
patterns, no new code. Acceptance criterion: an adopter reading
`STATE-RECOVERY.md` can find the artifact answering each of:
"resume across CLI restart", "resume mid-debate", "resume
mid-ceremony", "resume mid-phase-execute".

## Enforcement commit

To be filled in at Session 67 D5 closeout (this ADR's promotion
+ `docs/STATE-RECOVERY.md` land in same commit batch).

## References

- ADR-085 — Framework landscape Claude-only (this ADR is part of
  the closeout)
- PLAN-056 Phase 4 — original proposal (refused via this ADR)
- `docs/STATE-RECOVERY.md` — companion documentation deliverable
- `audit-log.jsonl` schema (`SPEC/v1/audit-log.schema.md`)
- Memory protocol (`CLAUDE.md` §Memory section)
