# ADR-049: Policy Engine Dual-Path Deprecation

**Status:** ACCEPTED — shadow-only / flip DEFERRED. The policy engine, dispatcher, and 2 migrated hook policies shipped (Sprint 14 PLAN-014 Phase A), but they are NOT on the live PreToolUse path: `.claude/settings.json` still routes to the legacy Python hooks, and the Sprint-16 dispatcher-only flip (§Decision) was never scheduled or executed. Treat `_lib/policy_dispatch.py` + the YAML policies as a validated-but-inert shadow implementation, not the active governance path.
**Date:** 2026-04-17 (drafted during PLAN-019 Phase 3 Wave 3A P2-004/VP-F8)
**Deciders:** CEO, VP Engineering, Principal Security
**Blast radius:** L2 (governance dispatcher routing)

> **Note on ID adjacency:** this ADR (ADR-049) governs the **policy
> engine dual-path** deprecation. A separate decision with the
> adjacent ID [`ADR-049a`](ADR-049a-worktree-orchestration-policy.md)
> covers **worktree orchestration policy** — a structurally unrelated
> topic that landed in the same numeric neighborhood by drafting-order
> coincidence (PLAN-019 vs PLAN-050). Both are PRESERVED rather than
> renamed to keep git-blame stable (per `F-A-IDA-T-0010` PLAN-087 W-F
> housekeeping). When reading the ledger, treat the two ADRs as
> independent — they neither supersede nor amend each other.

## Context

Sprint 14 PLAN-014 Phase A delivered:
- `_lib/policy.py` — declarative policy engine (1487L, 81 unit tests).
- `_lib/policy_preprocessors.py` — per-hook derived-field computation.
- `_lib/policy_dispatch.py` — shadow-mode dispatcher routing tool-call
  events to either legacy Python hook OR YAML policy + preprocessor.
- 2 migrated hook policies: `bash-safety.policy.yaml` +
  `plan-edit.policy.yaml` with fixture byte-identity proven against
  legacy Python implementations (63 fixtures, 0 drift).

However, `.claude/settings.json` still routes PreToolUse events to the
LEGACY Python hooks (`check_bash_safety.py` + `check_plan_edit.py`).
The YAML policies + dispatcher are dead code in production today.

The dual-path state is intentional per ADJ-014 shadow-mode discipline:
during the 2-week validation window, both paths run and are compared
for drift. But the flip to dispatcher-only has not been scheduled, and
Sprint 15 / PLAN-015 adopter validation was pushed to after PLAN-019.

## Decision

Maintain dual-path through Sprint 15 adopter validation. Flip
`settings.json` to route via `policy_dispatch.py` (not legacy hooks) in
**Sprint 16** post adopter-1 validation, conditional on:

1. **Zero drift** observed across 2 weeks of adopter usage (audit-log
   `policy_drift` events must be zero).
2. **PLAN-018 audit findings** P1-SEC-A (canonical guards), P1-SEC-E
   (plan_edit matcher), F-CHAOS-1 (audit fallback) all closed in
   PLAN-019 (✓ confirmed 2026-04-17).
3. **Settings.json schema** supports the transition (matcher stays
   unchanged; only `command:` value changes from `_python-hook.sh
   check_*.py` to `_python-hook.sh policy_dispatch.py --hook=<name>`).
4. **Mutation-kill harness** still 100% on dispatcher path (currently
   kills 65/65 on YAML; should remain 65/65 post-flip or new
   mutations added as coverage grows).
5. **Rollback plan** documented: revert settings.json to legacy in
   <5min if any production regression.

## Consequences

**Positive:**
- Eliminates dead-code maintenance burden (2 hooks × 2 implementations
  = 4 artifacts to keep in sync currently).
- YAML policies become editable by non-Python contributors (future
  Sprint 17+ contributor onboarding).
- Unlocks PLAN-017 autonomous-loop pattern (needs single decision path
  for the rate-limit + audit interactions it introduces).

**Negative:**
- Breaking change for any adopter who wrote custom Python hooks.
  Migration path: `scripts/migrate-hooks-to-policies.py` (to be written
  at flip time).
- One-shot flip; dual-path cannot co-exist post-Sprint-16.

**Rollback:**
- `settings.json` revert takes <5min. Legacy .py hooks remain on disk
  through Sprint 17 (removed only after 90 days of green dispatcher
  in production).

## Revisit condition

If at Sprint 16 flip time, ANY of the 5 conditions above fail, defer
to Sprint 17 with explicit Owner sign-off. If Sprint 17 still fails,
re-draft this ADR as SUPERSEDED with a new dispatcher strategy.

## References

- ADJ-014 (PLAN-014 Phase A.4 shadow-mode dual-path discipline)
- [ADR-045](./ADR-045-policy-as-code-engine.md) — Sprint 14 engine design
- PLAN-018 audit VP-F8 (2026-04-17)
- PLAN-019 Phase 3 Wave 3A (DYN-ADR-049)
- PLAN-015 (adopter validation) — gating signal for flip
- PLAN-017 (autonomous-loop) — downstream consumer of the flip

## Enforcement commit

`4542fdb47745` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
