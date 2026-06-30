# Wave A.6 — `check_pair_rail.py` SHADOW-strip DEFERRED to PLAN-092

## Disposition: PARTIAL — docstring promotion shipped; SHADOW-strip deferred

PLAN-091 §14 R1 + R2 fold log for Wave A.6 carries **internally
inconsistent** mandates when read literally:

- **R1 code-reviewer P0 fold**: A.6 lands "**docstring promotion** +
  `_PRODUCTION_PROMOTED_BY_PLAN_091` constant; **NO new ADR proposed**."
- **R1 code-reviewer escalation clause**: "If this is judged
  ADR-required at Codex R2, escalate to PLAN-092 (per Codex R2 P0-1
  precedent of redirecting non-hotfix scope)."
- **R2 Codex iter-1 P1 fold**: A.6 hook integration lands
  `check_pair_rail.py` in SHADOW MODE ONLY — ... does NOT block any
  tool call. ... Mechanical AC invariant: `grep -nE
  'decision.*block|return.*deny' check_pair_rail.py` returns **ZERO**
  matches post-wire.
- **R2 Codex iter-1 P1 fold (con't)**: "`mode: enforcing` requires
  separate PLAN-092 promotion ceremony with **its own ADR**."

The contradiction: R1 mandates "no new ADR" + docstring-only; R2
mandates SHADOW-strip behavior change (which removes a live v1.13.x
enforcement codepath in production since S96-cont-2). A behavior
change of that magnitude requires an ADR per ADR-115 maintenance-mode
discipline.

The R1 escalation clause governs: when scope drift exceeds hotfix
discipline, redirect to PLAN-092 (which can propose the ADR).

## What PLAN-091 A.6 SHIPS

1. **Docstring promotion**: top-of-file changed from
   `"""PLAN-075 Phase 0A spike — ..."""` to
   `"""PLAN-075 Phase 0A → PRODUCTION (PLAN-091 A.6 status promotion) — ..."""`.
2. **Status constant**:
   ```python
   _PRODUCTION_PROMOTED_BY_PLAN_091: bool = True
   ```
   immediately below the existing staging-promotion stamp comment.
   Mechanically grep-discoverable for AC1 verification.
3. **This deferral document** under `.claude/plans/PLAN-091/`.

## What PLAN-091 A.6 DEFERS to PLAN-092

The SHADOW-strip behavior change:

- Replace the line ~630 `{"decision": "block", ...}` (Codex
  write-shape contract violation block) with an advisory shape that
  emits `pair_rail_case` audit but allows the tool call.
- Replace the line ~1149 `if decision == "block":` matrix-overlay
  procedural-block path with the same advisory shape.
- Rewrite the 25 in-file "spike" string references to
  "PRODUCTION-PHASE-A" semantics.
- Add the corresponding ADR (likely ADR-124 or sequence successor)
  documenting the SHADOW-only-until-explicit-Phase-C-flip contract +
  the regression of the v1.13.x BLOCK semantics.

## Cross-plan handoff

- **PLAN-092 §4**: add a wave `A.x` titled "check_pair_rail.py
  SHADOW invariant strip" that lands:
  - The 5 `decision.*block|return.*deny` removals
  - "spike" → "PRODUCTION-PHASE-A" rewrites
  - The ADR proposal
  - Regression tests under
    `.claude/hooks/tests/test_check_pair_rail_shadow_invariant.py`
- **PLAN-090 §AC**: PLAN-090 Wave A `external_wait:
  PLAN-091-callsite-wires-shipped` does NOT consume the SHADOW
  invariant (that's PLAN-092's gate). PLAN-090 Phase C ENFORCING
  flip will continue to consult the active block path until PLAN-092
  ships the strip.

## Mechanical AC posture (post-PLAN-091)

| AC ref | Mandate | Disposition |
|---|---|---|
| §5 AC1 | All 6 W2/W3/W4 wires production-active | A.6 PARTIAL — docstring + constant landed; behavior unchanged |
| §5 AC11 | NO new ADRs proposed | SATISFIED — PLAN-091 proposes ZERO ADRs |
| R1 code-reviewer P0 | docstring promotion + constant | SATISFIED |
| R2 P1 SHADOW invariant | grep -nE returns ZERO | **DEFERRED-PLAN-092** with explicit rationale |
| AC11a "no 'spike' string" | grep "spike" returns ZERO | **DEFERRED-PLAN-092** (25 occurrences preserved) |

## Anti-churn defense

Per PLAN-091 §3:
> "Hotfix discipline applies. v1.22.1 is a HOTFIX tag, not a minor
> bump. This constrains scope:
> - NO new features ...
> - NO behavior changes for adopters who haven't installed PLAN-088
>   primitives ...
> - NO kernel extensions ...
> - NO Phase C flip (PLAN-090 territory)"

Stripping the v1.13.x BLOCK path FROM EXISTING PRODUCTION is a
behavior change that hits every adopter currently running
v1.13.x+. That violates the hotfix invariant. PLAN-092 owns it.

## How PLAN-092 picks up

The status constant `_PRODUCTION_PROMOTED_BY_PLAN_091 = True`
combined with this disposition file forms the explicit handoff
contract. PLAN-092 §1 should cite this file as its starting state.
