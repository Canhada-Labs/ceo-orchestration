# Pre-Plan Brainstorm — CHECKLIST

> **Usage:** binary-pass rubric used by debate Round 1 to verify that a
> pre-plan brainstorm artifact (`spec.md`) conforms to the 9-step
> methodology. A missing step fails the brainstorm; debate Round 1
> reports the gap back to the CEO instead of consuming consensus cycles
> on the underlying ambiguity.

## Per-step binary rubric

### Step 1 — Stakeholder mapping

- [ ] At least ONE stakeholder named (Owner counts).
- [ ] Each stakeholder entry includes BOTH concern and signal.
- [ ] No stakeholder placeholder left as `TBD` / `TODO` / `...`.

### Step 2 — Success criteria

- [ ] At least ONE falsifiable statement.
- [ ] Each statement written as a pass/fail test (grep / assert / CI step).
- [ ] No "works correctly" / "behaves as expected" / "clean" phrasing.

### Step 3 — Anti-goals

- [ ] At least ONE anti-goal written.
- [ ] Each anti-goal cites WHY it is out of scope (not just "not doing").

### Step 4 — Constraints

- [ ] Technical constraint listed (or `none` explicitly).
- [ ] Legal constraint listed (or `none` explicitly).
- [ ] Time constraint listed (or `none` explicitly).
- [ ] Budget constraint listed (or `none` explicitly).

### Step 5 — Assumptions

- [ ] At least ONE assumption listed.
- [ ] Each assumption tagged `provable-now` OR `accepted-on-faith`.

### Step 6 — Known unknowns

- [ ] List exists (empty-list is NOT acceptable — the honest answer is
      always at least one).

### Step 7 — Tradeoff mapping

- [ ] Two axes named.
- [ ] Three alternative designs plotted.
- [ ] Residual risk annotated per point.

### Step 8 — Preferred outcomes

- [ ] Best case written.
- [ ] Expected case written.
- [ ] Worst case written AND confirmed recoverable.

### Step 9 — Spec artifact

- [ ] `spec.md` file exists at `.claude/plans/PLAN-NNN/spec.md`.
- [ ] All 9 required headings present.
- [ ] `Open questions for Owner` section exists (empty-list acceptable,
      explicit "none" required).

## Failure handling

If ANY checkbox above fails during debate Round 1 validation:

1. Debate Round 1 prompt emits `## BRAINSTORM GAP` section naming the
   missing/malformed step(s).
2. Consensus artifact records `brainstorm_incomplete: true`.
3. CEO re-runs the `pre-plan-brainstorm` skill for the missing step(s)
   before debate Round 2 proceeds.

## Kill-switch handling

If `CEO_BRAINSTORM_GATE=0` is set:

- All checks above are skipped.
- Debate Round 1 does NOT validate a `spec.md` artifact.
- `spec_ref:` frontmatter field becomes optional (was: required for L3+).
- Audit-log emit `brainstorm_gate_skipped(plan_id, reason=env_disable)`.

## Legitimate skip scenarios (no strike)

- L1-L2 plans per plan frontmatter `level:` field.
- Plans with `skip_brainstorm: true` in frontmatter (Owner-approved).
- Emergency hotfix plans (status `hotfix` in frontmatter, time-boxed).
