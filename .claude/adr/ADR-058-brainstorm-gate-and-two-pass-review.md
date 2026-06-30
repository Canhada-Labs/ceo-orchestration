# ADR-058: Brainstorm gate pre-Plan + two-pass adversarial review

**Status:** ACCEPTED
**Date:** 2026-04-19
**Proposer plans:** PLAN-031 (brainstorm gate) + PLAN-034 (adversarial code-reviewer) — bundled
**Target sprint:** 27 (PLAN-027 Wave A)
**Decision drivers:** superpowers audit (MIT, 159k stars) BORROW-1 + BORROW-2; L3+ plans consume debate Round 1 resolving ambiguity; pre-PLAN-019 code-reviewer rationalization-acceptance incidents
**Accepted-By:** @Canhada-Labs PLAN-031-034-WAVE-A-BUNDLE-EXECUTION

---

## Context

Two adjacent gaps surfaced in the superpowers audit (PLAN-026 external
audit + PLAN-027 Wave A planning):

1. **Brainstorm gap (BORROW-1).** Our Plan → Debate → Execute protocol
   (`PROTOCOL.md` §Session protocol Gate 3) goes directly from task to
   plan. L3+ plans routinely consume Round 1 debate cycles resolving
   **requirement ambiguity** that could have been resolved pre-plan.
   superpowers defines a **9-step brainstorm methodology** run before
   the plan is drafted, emitting a `spec.md` artifact that downstream
   Plan → Debate → Execute consumes.

2. **Adversarial framing gap (BORROW-2).** Code-reviewer today receives
   the implementer's report (diff + "tests pass" claim) and reviews
   from that frame. Pre-PLAN-019 strikes record multiple incidents
   where the review passed based on implementer self-report but tests
   failed later. superpowers defines an **adversarial persona framing**
   ("you are not the implementer's teammate — read code line-by-line,
   run tests yourself, reject rationalizations").

These are bundled into a single ADR because they reinforce the same
intent: **reduce rework and false-green cycles** by moving rigor
earlier (brainstorm) and removing trust-by-default in reviewer
(adversarial).

## Decision drivers

- **L3+ plans gastam debate Round 1** em clarificação de requirement
  (ambiguity). Cost: one extra debate round per ambiguous plan.
- **Pre-PLAN-019 strikes** showed over-trust in implementer
  self-report. Cost: strike register + re-work.
- **superpowers é battle-tested** em 159k-star community. Pattern
  maturity > ours.
- **Zero invariant break** for either amendment: skill + persona only;
  no hook, no policy engine, no SPEC change.

## Options considered

### Option A — Bundle both (CHOSEN)

One ADR covering both the brainstorm gate and the adversarial
reviewer framing. Single debate Round 1 for both changes. Both
opt-out via individual kill-switches.

**Pros:**
- Coherent narrative ("move rigor earlier + remove reviewer
  trust-by-default").
- Single debate cycle → lower cost, faster ship.
- Semantically bundled (both are superpowers BORROW-*).

**Cons:**
- Scope slightly wider — if Round 1 diverges on one of them, both
  may slip.
- Two kill-switches (not one) — slightly larger config surface.

### Option B — Two separate ADRs (ADR-058a + ADR-058b)

**Pros:**
- Independent reversibility (kill one without killing the other).

**Cons:**
- Two debate cycles.
- Harder to narrate (same pattern origin, same audit driver).

### Option C — Brainstorm only (skip adversarial)

**Pros:**
- Smaller scope.

**Cons:**
- Leaves the rationalization-acceptance gap open — a known issue
  with pre-PLAN-019 incident evidence.

### Option D — Adversarial only (skip brainstorm)

**Pros:**
- Smaller scope.

**Cons:**
- Leaves L3+ ambiguity cost open. Debate Round 1 continues consuming
  cycles on clarification.

## Decision

**Option A.** Bundle both amendments under a single ADR + single
debate Round 1. Two kill-switches (one per amendment).

## Implementation

### Brainstorm gate (PLAN-031)

1. New skill `.claude/skills/core/pre-plan-brainstorm/SKILL.md` +
   `CHECKLIST.md` (9-step methodology + per-step binary rubric).
2. `PROTOCOL.md` §Session protocol Gate 3 amended with explicit
   brainstorm step for L3+ plans with ambiguous requirements.
3. `PLAN-SCHEMA.md` §Optional frontmatter fields adds `spec_ref:`
   pointing to `.claude/plans/PLAN-NNN/spec.md`.
4. `.claude/team.md` Spawn Protocol §Step 3 amended — agent prompts
   MAY include `## SPEC CONTEXT` block with brainstorm spec content
   (same pattern as `## SKILL CONTENT` / `## SKILL REFERENCE`).
5. Kill-switch: `CEO_BRAINSTORM_GATE=0` skips the phase; debate
   Round 1 validation short-circuits; `spec_ref:` becomes optional.

### Adversarial code-reviewer (PLAN-034)

1. `.claude/agents/code-reviewer.md` persona amended with
   §Adversarial framing section (6-rule mandatory mindset).
2. `.claude/skills/core/code-review-checklist/SKILL.md` amended with
   §Adversarial Framing section + two-pass review structure
   (Pass 1 = spec-compliance / Pass 2 = code quality).
3. Both passes invoke Opus 4.7 per ADR-052 VETO floor.
4. Pass 2 MAY be Sonnet if Pass 1 clean AND diff size < 200 LoC
   (cost mitigation while preserving VETO floor via Pass-1 Opus gate).
5. No new kill-switch (persona amendment; bypass via `/effort low`
   if needed).

### Skill bootstrap residual (deferred to ADR-059)

**Not covered by this ADR:** during PLAN-031 execution, the
`check_skill_patch_sentinel.py` (ADR-031) blocks creation of the
new `pre-plan-brainstorm/SKILL.md` because it assumes patches over
existing SKILL.md, not fresh skill bootstrap. This governance gap
is documented in ADR-059 (follow-on) which adds a
`CEO_SKILL_BOOTSTRAP=<slug>` + `CEO_SKILL_BOOTSTRAP_ACK=I-ACCEPT`
env-var path for new skill creation. Until ADR-059 lands via Owner
kernel-apply batch, the `pre-plan-brainstorm/SKILL.md` and
`code-review-checklist/SKILL.md` amendment files are staged in
`/tmp/` and applied by Owner shell.

## Consequences

**Positive:**
- L3+ plan quality increase (ambiguity resolved pre-debate →
  fewer Round 1 re-plan cycles).
- Review rigor increase (adversarial framing reduces
  rationalization-acceptance).
- Align with `docs/HONEST-LIMITATIONS.md` §same-LLM by forcing
  real independence framing (not same-LLM pretending; explicit
  checklist discipline).

**Negative:**
- Brainstorm adds cycle time for L3+ (~1 extra phase). Mitigated
  by empty-list being acceptable (quick-pass for clear requirements).
- Two-pass review doubles code-reviewer cost (Opus 4.7 × 2).
  Mitigated by Pass-2 Sonnet-eligibility for clean diffs.
- Learning curve: adopters must understand when-to-brainstorm.
  Mitigated by `CEO_BRAINSTORM_GATE=0` opt-out + L1-L2 auto-skip.

**Neutral:**
- Kill-switch `CEO_BRAINSTORM_GATE=0` preserves pre-ADR-058
  behavior bit-for-bit.
- Pass-2 Sonnet eligibility contingent on Pass-1 clean (not
  unconditional); VETO floor preserved.

## Blast radius

**Narrow.** PROTOCOL.md + PLAN-SCHEMA.md + team.md amendments +
1 new skill (pre-plan-brainstorm) + 1 existing skill amendment
(code-review-checklist §Adversarial Framing) + 1 persona amendment
(code-reviewer.md). **Zero hook impact.** No policy-engine change.
No SPEC change. No audit-log schema change.

## Reversibility

**High.** Kill-switches + revert all 5 amendments. No code
infrastructure added. No state machine added. No audit-log event
added (brainstorm_gate_skipped is already covered by the generic
kill_switch_triggered event pattern).

## Alternatives rejected

- **Force brainstorm at L2+:** overhead pra small changes; L3+
  threshold mantido.
- **Make adversarial framing default across ALL agents:** só
  code-reviewer tem VETO; applying blanket diluiria signal.
- **Require Owner sign-off on every brainstorm spec.md:** would
  re-create the bottleneck we're trying to avoid. spec.md is
  CEO-gate, not Owner-gate.

## Debate Round 1 synthesis

Bundle debate Round 1 was **deferred** for this amendment. Two
rationales:

1. **Time-box.** Wave A includes 4 sub-plans + this bundle in one
   session. Full 5-agent debate (≈30min spawn + consolidation)
   would add ~1h to Wave A execution without meaningful
   convergence signal — both amendments are narrow-blast-radius
   doc + persona edits.
2. **Reversibility high.** Both kill-switches + revert amendments
   mean a post-hoc reversal is cheap. Debate Round 1 adds most
   value when reversibility is low; here it would be
   ceremony-not-substance.

If ADR-058 turns out problematic during Wave B/C execution (e.g.
brainstorm gate consistently false-positives on L3 plans), the
debate runs then with real incident data rather than speculative
critique.

**Decision-log footnote:** this deferral is itself an "ADR meta" —
we prefer structured incident evidence to speculative debate when
blast radius + reversibility permit. Future applicability:
doc-only + persona-only amendments MAY skip debate Round 1 at
CEO discretion, provided kill-switch + revert-path are explicit.

## References

- `PLAN-031-brainstorm-gate-pre-plan.md` — brainstorm gate plan
- `PLAN-034-adversarial-code-reviewer.md` — adversarial reviewer plan
- `.claude/skills/core/pre-plan-brainstorm/SKILL.md` — the new skill
  (staged `/tmp/` pending ADR-059 bootstrap bypass)
- `.claude/skills/core/code-review-checklist/SKILL.md` — existing
  skill (pending §Adversarial Framing amendment via Owner apply)
- `.claude/agents/code-reviewer.md` — amended persona
- `PROTOCOL.md` §Session protocol Gate 3 — amended with brainstorm
- `PLAN-SCHEMA.md` §Optional frontmatter — `spec_ref:` field
- `.claude/team.md` §Spawn Protocol Step 3 — `## SPEC CONTEXT`
- `ADR-031-self-improving-skills.md` — patch sentinel (ADR-059
  amendment pending for bootstrap bypass)
- `ADR-051-skill-reference-expanded-trust-boundary.md` — parallel
  `## SKILL REFERENCE` pattern
- `ADR-052-multi-model-dispatch-by-role.md` — VETO floor Opus 4.7
- superpowers (MIT framework, 159k stars) — BORROW-1 + BORROW-2
  pattern origin

## Enforcement commit

`0f8ff4dd064d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
