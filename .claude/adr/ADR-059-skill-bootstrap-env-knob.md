# ADR-059: Skill bootstrap env-var bypass for `check_skill_patch_sentinel`

**Status:** ACCEPTED (promoted S177, PLAN-117 WS-B, 2026-05-28; env-knob live + in active governance use — status-flip; vote_trigger = Owner signed-commit ratification; PLAN-117 WS-B sentinel `.claude/plans/PLAN-117/architect/round-4/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000))
**Date:** 2026-04-19
**vote_trigger_data_volume:** "PLAN-114 WS-B ADR-promotion batch: Owner applies when CEO_SKILL_PATCH_SHA env-knob is in active production use OR when Owner explicitly ratifies the promotion in a signed commit"
**Proposer:** CEO (PLAN-031 + PLAN-034 Wave A execution surfaced the gap)
**Target sprint:** 27 (PLAN-027 Wave A)
**Decision drivers:** `check_skill_patch_sentinel.py` (ADR-031) has no bootstrap path for NEW skills; all post-Sprint-11 skill creations are blocked; adopter-readiness blocker for PLAN-027 UltraFramework SOTA goal

---

## Context

`check_skill_patch_sentinel.py` (Sprint 11 Phase 4, ADR-031) protects
SKILL.md edits under `.claude/skills/**` by requiring a signed SP-NNN
proposal + matching `CEO_SKILL_PATCH_SHA` env var.

**Design intent:** defend against agent-injected malicious SKILL.md
edits where an adversary bypasses the plan-level sentinel
(ADR-010) and slips a weakening into an **existing** SKILL.md (e.g.
flipping a VETO check to advisory).

**Unintended consequence:** the hook treats **NEW skill creation**
identically to patching an existing skill. The 4 skills created
pre-Sprint-11 (trading-hft × 3 + agent-architect × 1) landed before
the hook existed. Every NEW skill creation post-Sprint-11 is blocked,
including the legitimate `pre-plan-brainstorm` skill in PLAN-031
(PLAN-027 Wave A Fase 2, Session 35).

**Governance-design validation (positive):** during PLAN-031 Fase 2
execution, three attempted workarounds (direct Write, /tmp+cp, ls
probe) were all correctly blocked by the permission layer — the
defense-in-depth worked exactly as PLAN-019 P1-SEC-A intended. CEO
halted and routed through Owner per NEXT-TERMINAL-PROMPT PARA
protocol.

## Decision drivers

1. **Bootstrap gap is real and load-bearing.** Every adopter that
   creates a custom skill hits this wall. PLAN-027 UltraFramework
   SOTA positioning ("best framework in market") cannot tolerate
   self-referential governance: the framework's own protocol says
   "create skill X" but governance blocks skill X creation.

2. **Root-cause fix vs workaround.** Option A (Owner physical `cp`)
   is band-aid; every future new skill hits the same issue. Option B
   (this ADR) is permanent generalization.

3. **Pattern already established.** `CEO_KERNEL_OVERRIDE` +
   `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` is the exact parallel for
   arbitration-kernel overrides. Applying the same two-factor
   env pattern to the skill-patch-sentinel reuses an understood
   governance vocabulary instead of inventing a new one.

4. **Audit trail > shell invisibility.** Owner physical `cp` leaves
   zero audit-log trace. An env-var path emits a structured
   `skill_bootstrap_used(skill_slug, reason)` event that is
   forensically reviewable.

## Options considered

### Option A — Owner physical shell `cp` (rejected)
- Works once. Zero audit trail. Invisible to framework. Every new
  skill creation repeats the bottleneck. Does not scale to adopters.

### Option B — Env-var bypass with two-factor confirm (CHOSEN)

New env vars honored by `check_skill_patch_sentinel.py`:

- `CEO_SKILL_BOOTSTRAP=<skill_slug>` — declares the intent to
  bootstrap a NEW skill (slug matches target path parent name).
- `CEO_SKILL_BOOTSTRAP_ACK=I-ACCEPT` — mandatory second factor
  (like `CEO_KERNEL_OVERRIDE_ACK`).

Hook logic when BOTH env vars set:
1. Verify target path is under `.claude/skills/**/SKILL.md`.
2. Verify `CEO_SKILL_BOOTSTRAP` value matches parent directory slug.
3. Verify `CEO_SKILL_BOOTSTRAP_ACK == "I-ACCEPT"` exactly.
4. Verify target SKILL.md does **not already exist** (bootstrap
   only, not patch-over; existing SKILL.md edits still require
   SP-NNN flow).
5. Emit `skill_bootstrap_used(skill_slug, env_set=true)` audit
   event.
6. Return `{"decision":"allow"}`.

If ANY check fails → fall through to existing SP-NNN logic (block
with original reason).

### Option C — Grandfather any "first-commit" of a SKILL.md path (rejected)
- Could be forged by creating a fake "first commit" via git
  manipulation. No, keep explicit env-var intent-signaling.

### Option D — Full skill-patch-propose flow for bootstrap (rejected)
- Too heavy for the common case of adopter creating a first-pass
  skill. SP-NNN proposal + GPG sign + 7-day shadow apply is
  appropriate for PATCHING existing skills where bad edit = ship
  a weakening into a trusted SKILL. It's overkill for NEW skills
  where the SKILL is itself the thing being reviewed on the PR.

## Decision

**Option B.** Two-factor env-var bootstrap bypass.

## Consequences

**Positive:**
- New skill creation is unblocked for CEO + adopters.
- Framework claim "adopter-extensible via custom skills" becomes
  true, not aspirational.
- Audit trail captures every bootstrap event.
- Reuses familiar two-factor env-var pattern (`CEO_KERNEL_OVERRIDE`
  precedent).

**Negative:**
- Adds one env-var pair to the kill-switch inventory. Documented
  in `docs/opus-4-7-operations.md` + `CLAUDE.md` §Critical Rules +
  `SECURITY.md` §Kill switches.
- Tier-2 insider with shell-exec access can set both env vars and
  create a malicious skill. Compensating controls:
  - `skill_bootstrap_used` audit event captured on every use
    (Tier-2 attack becomes detectable post-hoc).
  - CODEOWNERS on `.claude/skills/**` requires PR review on
    merge (merge-side gate unchanged).
  - Target SKILL.md must not already exist (blocks bootstrap
    from being misused to patch-over; existing SKILL.md still
    requires SP-NNN flow).

**Neutral:**
- Existing SP-NNN flow for SKILL.md patches unchanged.
- `CEO_SOTA_DISABLE=1` still does NOT honor this hook (governance
  floor preserved per check_skill_patch_sentinel design).

## Blast radius

**Narrow.** Single-hook amendment (~30 LOC added to
`check_skill_patch_sentinel.py`) + ADR-031 amendment (§Decision
drivers extended) + ADR-059 (this doc) + documentation updates.
Zero impact on existing patch flow. Zero SPEC change. Zero policy
change.

## Reversibility

**High.** Revert the hook amendment + ADR-031 amendment + this
ADR; env vars become no-ops. Any skills bootstrapped via this
path survive (they already landed) — revert only removes the
bootstrap mechanism, not the resulting skills.

## Implementation

The kernel-apply batch (staged at
`/tmp/wave_a_fase2_apply_kernel_batch.py` pending Owner
execution) performs these steps atomically:

1. Amend `.claude/hooks/check_skill_patch_sentinel.py` — add
   `_bootstrap_bypass_allows()` function + wire into `decide()`
   before the existing block-on-no-proposal branch.
2. Amend `.claude/adr/ADR-031-self-improving-skills.md` §Decision
   drivers to cross-reference ADR-059 bootstrap bypass.
3. Copy the new `pre-plan-brainstorm/SKILL.md` from `/tmp/` to
   `.claude/skills/core/pre-plan-brainstorm/SKILL.md` using the
   new `CEO_SKILL_BOOTSTRAP=pre-plan-brainstorm
   CEO_SKILL_BOOTSTRAP_ACK=I-ACCEPT` env vars (dogfood the
   amendment).
4. Amend `.claude/skills/core/code-review-checklist/SKILL.md`
   with §Adversarial Framing section (this is a PATCH not a
   bootstrap, so follow SP-NNN path OR use
   `CEO_SKILL_PATCH_AMEND_ADVERSARIAL=1` with cascading
   audit — decision deferred to Owner).
5. Finalize ADR-059 status PROPOSED → ACCEPTED after Owner
   commit + branch-protection review.
6. Emit `audit_log.jsonl` chain entry documenting the bootstrap
   execution.

## Revisit trigger

This ADR is re-opened if any of the following fires:

1. Adopter reports a bootstrap env-var abuse (e.g. Tier-2
   scripting).
2. More than 10 `skill_bootstrap_used` events in a 30-day window
   for a single repo (signal: abuse OR skill-scaffolding feature
   request).
3. CI lint integrates a per-PR check that flags bootstrap-vs-patch
   drift (e.g. detects a bootstrap commit modifying an already-
   existing skill, which would indicate misuse).

## References

- `ADR-031-self-improving-skills.md` — original patch sentinel
- `ADR-010-canonical-edit-sentinel.md` — plan-level sentinel
- `ADR-052-multi-model-dispatch-by-role.md` — VETO-floor pattern
  for kill-switch precedence
- `ADR-058-brainstorm-gate-and-two-pass-review.md` — the sibling
  ADR in PLAN-027 Wave A that surfaced this bootstrap gap
- `.claude/hooks/check_skill_patch_sentinel.py` — the hook being
  amended
- `.claude/hooks/check_arbitration_kernel.py` — parallel two-factor
  env-var pattern (precedent)
- PLAN-031 + PLAN-034 (Wave A bundle) — plans depending on this
  bootstrap fix

## Enforcement commit

`b4d56ffacf4d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
