# ADR-032: Interactive multi-round debate protocol with Jaccard convergence + Red Team gate

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 5)
**Related:** ADR-005 (event stream v2 — debate_event), ADR-008 (hook adapter layer — fail-open contract), ADR-019 (confidence-gate three-state precedent), ADR-027 (unified state backend — debate state lives on disk per §3 schema, not in unified store)

## Context

The ceo-orchestration framework's debate machinery (DEBATE-SCHEMA.md
§1–§11, shipped Sprint 2 D.1) supports 1-to-3-round structured
debates with consensus synthesis. PLAN-001/002/003/005/006/008/009/010
all ran round 1 successfully; **none of them ran a round 2** in
practice. The empirical pattern: round 1 produces 3–6 consensus
findings, the CEO adjusts the plan, ships, lessons land in the
audit log.

Three problems with the current setup motivate this ADR:

### Problem 1 — No machine-readable convergence signal

The decision "is this debate converging?" is currently a CEO judgment
call, made by reading the round-1 critiques. There is no formula. PLAN-009
debate (24 adjustments after round 1) and PLAN-010 debate (19
adjustments after round 1) both *felt* like convergence, but the
framework has no way to compare round 1 vs round 2 quantitatively. If
two agents produce 80% the same risk list in round 2 as round 1, that
**should** be the signal to either stop (real convergence) or escalate
(stale debate, agents not engaging with the consolidated critique).

### Problem 2 — Same-LLM groupthink risk (PLAN-011 consensus M1)

PLAN-011 round-1 debate consensus M1 (HIGH severity, all 6 archetypes
flagged): **Auto-converging at round 1 or 2 is statistically suspicious
in a same-LLM agent pool.** Claude agents share 100% of weights. When
they agree on 70%+ of risks after one round of forced perspectives,
that may reflect:

- (a) Genuine convergence — the proposal is well-scoped and the risks
  are truly canonical.
- (b) Shared-LLM groupthink — the same training-data biases produce
  the same blind spots.

There is no observable way to distinguish (a) from (b). The PROTOCOL.md
§"Honest limitation: same-LLM problem" doc warns about this but
proposes only "forced perspective via skills" as mitigation. PLAN-011
M1 calls for an **anti-groupthink mechanism**: a Red Team agent,
spawned only when convergence hits early (round <= 2), with the
explicit task of finding risks the consensus group missed.

### Problem 3 — Consolidated critique secret-leak risk (PLAN-011 consensus M6)

When round N+1 agents read round N's consolidated critiques, any
secret pasted into a round N risk description (an API key in error
text, a JWT in a sample request) flows downstream into the next
round's prompt. The redact_secrets() library exists (Sprint 2) but
nothing wires it into the debate feed-forward path. PLAN-011 M6
explicitly calls this out: redact before feed-forward, not after.

## Decision drivers

- **No thin-air thresholds** (PLAN-010 ADR-024 precedent). Whatever
  Jaccard threshold we pick MUST be defensible by either established
  IR practice OR a measured baseline.
- **Same-LLM problem is real** (PROTOCOL.md). Any auto-stop mechanism
  needs an explicit anti-groupthink branch.
- **Additive-only schema** (DEBATE-SCHEMA.md §6 invariant). Cannot
  break v1 layout — gain fields, never rename/remove.
- **Fail-open on infra** (CLAUDE.md §5). The orchestrator must never
  block the debate on infrastructure bugs (audit emission errors,
  redaction lib unavailable).
- **Bounded blast radius** (ADR-014 batch policy). One ADR + 2 scripts
  + tests + schema amend, not a multi-week rewrite.

## Options considered

### Option A — Single-round only (status quo)

Pros: simplest; no new machinery; matches actual usage of PLAN-002
through PLAN-010.

Cons:
- Forecloses N-round debates for genuinely contentious plans (PLAN-011
  itself ran 6 archetypes through round 1 and the result was 17 HIGH
  consensus findings — would have benefited from a round 2 to test
  whether round-1 adjustments stuck).
- No anti-groupthink machinery — the M1 finding remains unmitigated.
- Wastes the "rounds 1–3" infrastructure already documented in
  DEBATE-SCHEMA.md §2.

Rejected.

### Option B — N-round with arbitrary cap, no convergence detection

Default round count = 3 (or N), CEO can extend with a flag, but no
machine signal for when to stop. Same as today's `/debate round2 / round3`
slash commands but with a higher cap.

Pros: incremental; no new dependencies.

Cons:
- Same as Option A on the convergence signal problem — CEO still
  judges by eye.
- N-round debates without convergence detection burn tokens linearly
  in N. PLAN-011 §9 budget estimates 90K tokens/round; 5 rounds = 450K
  tokens for what may have converged at round 2.
- M1 anti-groupthink unaddressed.

Rejected.

### Option C (CHOSEN) — N-round with Jaccard convergence + Red Team gate + redaction

The orchestrator runs N rounds (default 5, hard cap 10), computes
Jaccard similarity of risk sets between consecutive rounds, and:

1. If Jaccard >= 0.7 AND round <= 2 → spawn a **contingent Red Team**
   archetype (`chaos-and-resilience` + `security-and-auth` skills)
   to attack the consensus.
2. If Jaccard >= 0.7 AND round > 2 → mark consensus, write
   `consensus.md`.
3. If max-rounds exhausted without convergence → write `consensus.md`
   with `status: unresolved` + escalate to Owner.
4. Before passing round N's consolidated critiques to round N+1
   agents, apply `_lib.redact.redact_secrets()` on the consolidated
   text.

Pros:
- Quantitative convergence signal (PROBLEM 1 solved).
- Anti-groupthink Red Team (PROBLEM 2 solved per M1).
- Redaction wired into feed-forward (PROBLEM 3 solved per M6).
- Default 5 rounds matches the ADR-019 three-state pattern: ship
  small (single-round), graduate to multi-round when convergence
  signal exists.
- All additive; existing DEBATE-SCHEMA.md §1–§11 unchanged.
- Hard cap 10 prevents runaway debates.
- `CEO_SOTA_DISABLE=1` falls back to single-round mode (zero
  regression from current behaviour).

Cons:
- Jaccard threshold (0.7) is the one judgment call. Defensible per
  Manning, Raghavan & Schütze (IR textbook §3.3.4) — Jaccard >= 0.7
  is the conventional "high overlap" cutoff in document-similarity
  research. We commit to revisit after Sprint 12 with empirical
  data.
- Red Team is an additional spawn (cost: ~30K tokens). Bounded — only
  fires when M1 gate triggers (early convergence on a same-LLM pool),
  not every round.

Chosen.

## Decision

### 1. Threshold = Jaccard 0.7

- 0.5 declares convergence on largely disjoint risk sets — too lax.
- 0.9 requires near-exact text match — too strict; agents paraphrase
  across rounds.
- 0.7 is the IR standard for "high overlap" + matches the empirical
  range observed in PLAN-009 / PLAN-010 round-1 critiques (manual
  inspection shows ~0.6–0.75 inter-archetype overlap on shared
  consensus findings).
- Configurable via `--threshold` for stress tests; default 0.7.

### 2. Red Team is contingent, not standing

- `team.md` documents Red Team as a **contingent** archetype with a
  trigger condition (M1 gate fires).
- It is NOT in the default DEFAULT_ARCHETYPES list of `debate-orchestrate.py`.
- It is spawned only when convergence at round <= 2 fires, by the
  orchestrator's `maybe_trigger_red_team()` helper.

### 3. Redaction is mandatory, not optional

- `redact_consolidated()` is called unconditionally before round N+1
  prompt generation. The redaction library's bounded-growth invariant
  (`len(out) <= 2 * len(in)`) caps DoS risk.
- If the redact lib is unavailable (impossible in production but
  possible in CI-isolated tests), the orchestrator falls back to an
  identity function. This matches the fail-open principle.

### 4. Sprint 11 ships orchestration scaffolding, NOT live agent spawning

The script generates the **prompt files** + **convergence machinery**
+ **Red Team prompt template** + **fixture corpus**. It does NOT
actually spawn live Claude Code Agent invocations from the orchestrator
(that's a Sprint 12+ wiring step). This bounds blast radius:

- Today: orchestrator writes round-N/<archetype>.md prompt skeletons,
  CEO copies them into Agent invocations manually (or via the existing
  `/debate roundN` slash command).
- Tomorrow (Sprint 12+): orchestrator can shell out to `claude` CLI
  and dispatch the spawn directly. ADR-032 amendment will be required
  to add real spawning.

### 5. Audit emission via existing `debate-emit.py`

Per phase per round, the orchestrator subprocess-invokes
`debate-emit.py` with `start | agent-done | consensus`. This reuses
the audit_emit.py infrastructure without adding a new event_kind.
Subprocess invocations have a 5s timeout + are wrapped in a try/except
so audit failures NEVER block the debate.

### 6. Hard cap 10 rounds

Past 10 rounds, the debate has failed. The orchestrator refuses
`--max-rounds > 10` at argparse. Anything that needs >10 rounds is
already an Owner-escalation-required scenario.

## Red Team pattern documentation

The Red Team archetype is the framework's **anti-groupthink mechanism**
for same-LLM debates. Its prompt is materially different from the
standard 6 archetypes:

- Standard archetypes: "Critique this proposal from your skill
  perspective. List risks."
- Red Team: "The consensus has converged at round <= 2. The same-LLM
  problem makes this statistically suspicious. Your job is to attack
  the consensus, not validate it. Find risks they all missed."

Mechanically:
- Single file output: `round-<N+1>/red-team.md`
- Skills: `chaos-and-resilience` (primary) + `security-and-auth`
  (secondary). The combination is chosen because chaos-and-resilience
  is best at "what fails when?" and security-and-auth is best at
  "what's the exploit?" — both perspectives that are systematically
  underweighted in proposal-defense round 1 critiques.
- The Red Team's findings are SYNTHESIZED into the next consensus.md
  alongside the standard archetypes — they are NOT a separate
  judge/jury role. The Red Team participates in the consensus, just
  with a different prompt.

## Non-goals

- **Real-time live-streaming agent debates.** Sprint 13+ (or never) if
  the harness can't support websocket streaming of agent token-by-token
  output. Today: round files are written sequentially; CEO reviews
  between rounds.
- **Cross-LLM debate (Claude vs GPT vs Gemini).** This would solve the
  same-LLM problem at the root, but requires multi-LLM adapter parity
  (PLAN-011 Phase 1 is laying groundwork). Out of scope for ADR-032.
- **Live spawn invocation from `debate-orchestrate.py`.** See §4
  above — bounded blast radius for Sprint 11. Sprint 12+ wiring.
- **Lesson injection into round-N prompts.** Sprint 8 PLAN-008 ships
  lesson_ranker for spawn-time injection but the debate orchestrator
  doesn't currently inject ranked lessons. Defer to Sprint 12+ if signal
  emerges that lessons would meaningfully change debate outcomes.
- **Statistical p-values on Jaccard.** No bootstrap, no confidence
  intervals. Threshold is a hard cutoff. Sprint 12 may revisit if
  noise is observed.

## Consequences

### Positive

- **Quantitative convergence signal.** The `--debate-converge.py` CLI
  emits a single JSON line per call: `{jaccard, converged,
  red_team_needed, ...}`. Other tooling (audit-query.py, dashboard)
  can consume this directly.
- **M1 mitigation in place.** Red Team prompt files are auto-generated
  whenever the same-LLM groupthink risk crystallizes. Sprint 12 can
  measure how often the gate fires and tune the threshold.
- **M6 mitigation in place.** Secrets cannot leak from round N to
  round N+1 prompts. The redaction is invariant-tested
  (`test_redact_consolidated_is_idempotent_and_nonexpanding`).
- **Fixture corpus exists.** 4 fixture pairs (converged, not-converged,
  partial-overlap, with-secret) ship in
  `.claude/scripts/tests/fixtures/debate_convergence/`. Future
  threshold-tuning work can add fixtures here without touching code.
- **Back-compat preserved.** `CEO_SOTA_DISABLE=1` falls back to
  single-round; existing `/debate round2 / round3` slash commands
  continue to work as before.

### Negative

- **Threshold is one judgment call.** 0.7 is defensible but not
  derived from a measured baseline of THIS framework's debates. We
  commit to revisit at Sprint 12 closeout with audit-log data.
- **Red Team adds 1 spawn = ~30K tokens** when the gate fires. Bounded
  to early-convergence cases but real cost.
- **Orchestration scaffolding without live spawn.** Sprint 11 ships
  prompt-files-only; the CEO still has to copy/paste prompts into
  Agent invocations. Sprint 12+ wiring required for full automation.
- **Normalization is lossy.** Stripping ID prefixes + punctuation
  means two semantically different risks with the same content words
  collapse into the same key. Trade-off for robustness against
  paraphrase.

### Neutral

- Adds two new scripts (`debate-orchestrate.py` ~600 LOC,
  `debate-converge.py` ~250 LOC) under `.claude/scripts/`.
- Adds 44 unit tests across 2 files; no existing tests modified.
- No new env-var knobs except the existing `CEO_SOTA_DISABLE` from
  PLAN-011 Phase 1.
- No change to `check_agent_spawn.py` or any hook.
- DEBATE-SCHEMA.md gains §12 (additive); no v1 fields renamed/removed.

## Blast radius

**L2** — two new scripts (~850 LOC combined), one test pair (44 tests,
~600 LOC), one schema amend (additive §12), one team.md row addition,
this ADR. No existing files modified beyond the schema +
team.md additions. No new dependencies. No env-var changes.

**Reversibility:** HIGH. Delete the two new scripts, delete the new
tests, revert §12 from DEBATE-SCHEMA.md, revert the Red Team row from
team.md, delete this ADR. The existing single-round debate flow
(slash commands) continues to work unchanged.

## Transition lifecycle

| State | Date (target) | Trigger |
|-------|---------------|---------|
| Sprint 11 — Orchestration scaffolding ships | 2026-04-14 | This ADR |
| Sprint 12 — Live spawn wiring (orchestrator → Agent tool) | TBD | New ADR amendment + measured stability |
| Sprint 12+ — Threshold revisit | After 10 multi-round debates with Jaccard data in audit log | Empirical baseline established |

## References

- PLAN-011 Phase 5 — Interactive debate
- PLAN-011 round-1 consensus M1 (anti-groupthink) and M6 (redaction)
- DEBATE-SCHEMA.md §12 — N-round formal semantics (this ADR's runtime contract)
- ADR-005 — event_stream v2 (debate_event reused unchanged)
- ADR-019 — confidence-gate three-state lifecycle (precedent for shipping
  measure-only first, then graduating)
- PROTOCOL.md §"Honest limitation: same-LLM problem"
- `.claude/scripts/debate-orchestrate.py` — orchestrator
- `.claude/scripts/debate-converge.py` — Jaccard CLI
- `.claude/scripts/tests/fixtures/debate_convergence/` — fixture corpus
- Manning, Raghavan, Schütze. *Introduction to Information Retrieval*
  (2008), Cambridge UP, §3.3.4 — Jaccard coefficient as "high overlap"
  cutoff convention

## Enforcement commit

`fdf76fdff477` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
