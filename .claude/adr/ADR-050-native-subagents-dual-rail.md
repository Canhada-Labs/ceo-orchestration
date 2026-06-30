# ADR-050: Native Subagents Dual-Rail

**Status:** ACCEPTED (flipped PLAN-025 Batch C — live per PLAN-020 Phase 1 commit 63d0db7 (5 native subagents + generate-dispatch.py shipped))
**Date:** 2026-04-17 (pre-authored during PLAN-020 Phase 0a per Q5 Owner default)
**Deciders:** CEO, VP Engineering, Principal Performance, Principal Security, DevOps
**Blast radius:** L3 (spawn dispatcher + upgrade.sh + CI matrix + new agents/ tree)
**Supersedes:** none
**Superseded by:** none

## Context

Claude Code 4.7 exposes a native subagent dispatch path via
`.claude/agents/<slug>.md` files with YAML frontmatter. The native
path uses Anthropic's prompt-cache lane dedicated to subagents,
which is materially cheaper per-spawn than the custom Spawn Protocol
(persona + skill content inline) the framework has shipped since
Sprint 1.

PLAN-020 Phase 0 measurement work establishes the magnitude of the
gap before we commit to the migration. Independent of cache savings,
the native path also encourages frontload-heavy agentic patterns
that 4.7 rewards (Opus 4.7 release notes + Boris thread + internal
analysis).

The custom Spawn Protocol is NOT broken — it works correctly,
enforces persona + skill + file-assignment trinity, blocks cosmetic
naming via `check_agent_spawn.py::_has_skill_content`. The question
is whether to add a parallel native rail and migrate the canonical
archetypes to it, while keeping custom available as fallback for
adopter-authored agents and emergency rollback.

PLAN-019 P1-SEC-B (Wave 2B) hardened `_has_skill_content` to a
256-byte floor + fence/comment mask. ADR-050 expands the surface but
**must not weaken** that floor. The native path's hook recognition
must enforce equivalent or stricter discipline.

## Decision

Ship a **dual-rail** dispatch model:

1. **Native rail.** Migrate 5 canonical archetypes as native subagents:
   - `code-reviewer.md`
   - `security-engineer.md`
   - `qa-architect.md`
   - `performance-engineer.md`
   - `devops.md`

2. **Custom rail.** All non-canonical archetypes (frontend leads, domain
   specialists, adopter-authored ad-hoc personas) continue to spawn via
   `inject-agent-context.sh` + `check_agent_spawn.py` inline-content
   path.

3. **Single decision point** (no per-turn judgment by CEO):
   - Archetype `X` dispatches as native IFF
     `.claude/agents/X.md` exists AND `CEO_NATIVE_SUBAGENTS != 0`.
   - Otherwise custom rail.
   - Auto-generated `.claude/agents/_dispatch.md` table is the single
     source of truth (lint-verified in CI, ungated by humans).

4. **Hook recognition.** `check_agent_spawn.py` extends `decide()` with
   native-path detection (frontmatter parse + persona/skill frontmatter
   keys present). Native path emits structured `{"decision":"allow"}`
   without requiring the inline `## SKILL CONTENT` sentinel — but
   ADR-051's `## SKILL REFERENCE` sentinel must be present and validated
   synchronously (skill content moves to file reference, not removed).

5. **upgrade.sh preservation.** New helper `upgrade_agents_canonical_only()`
   iterates ONLY the canonical-5 basenames during framework upgrade.
   Adopter-authored `.claude/agents/custom-*.md` are NEVER touched.
   Banner post-upgrade: `"PLAN-020 native-subagent rail installed; set
   CEO_NATIVE_SUBAGENTS=0 to opt out"`.

6. **CI dual-rail matrix.** `.github/workflows/validate.yml` adds
   `hook-tests-dual-rail` job with `CEO_NATIVE_SUBAGENTS: [0, 1]`
   matrix. Custom-rail regression catches at PR merge time, not
   production. Budget ≤45s extra wall-clock.

7. **Kill-switch precedence:**
   - `CEO_SOTA_DISABLE=1` overrides everything (sets
     `CEO_NATIVE_SUBAGENTS=0` effectively). Master kill.
   - `CEO_NATIVE_SUBAGENTS=0` falls back to custom rail per-archetype.
   - Default `CEO_NATIVE_SUBAGENTS=1` (opt-out). Per Q2 Owner answer
     Session 32 — Owner needs default-ON for adopter-1 consumption.
   - Failure mode for native rail: "fall back to custom rail," NEVER
     "block the session."

8. **ENABLE_NATIVE_SUBAGENTS** module-level constant in
   `check_agent_spawn.py` toggled via env var. Phase 1 commit revert
   = single-line flip to `False`. Does NOT conflict with Phase 2
   (`ENABLE_SKILL_REFERENCE_MODE`) because each phase has its own
   constant.

## Consequences

**Positive:**

- Cache hit on canonical-archetype spawns reduces per-spawn token cost
  materially (magnitude TBD by Phase 0 measurement; expected ≥20%
  reduction on canonical-5 reference-rail spawns per §6 sub-targets).
- Frontload-heavy agentic patterns (matching 4.7 strengths) become
  the default path for the most-spawned archetypes.
- `_dispatch.md` auto-generation eliminates per-turn judgment ambiguity
  (DevOps must-fix #2 — single decision point).
- CI matrix catches custom-rail regressions before merge, not in
  production (DevOps must-fix #6).
- upgrade.sh preservation means adopters with custom agents never lose
  their work on framework upgrade (DevOps must-fix #3).
- Kill-switch precedence is testable + documented (DevOps must-fix
  #1 — kill-switch matrix in PLAN-020 §6a).

**Negative:**

- Two dispatch paths to maintain. Mitigated by canonical-5 scope (5
  archetypes only); other archetypes never see native rail churn.
- Anthropic native-subagent API surface may evolve. Mitigated by
  `version: "anthropic-subagent-v1"` frontmatter version-lock; if
  Anthropic introduces v2, ADR-052 amends.
- Hook recognition logic is more complex. Mitigated by Phase 0 item 5
  native-hook probe (3 governance probes; 0/3 = Phase 1 NO-GO).
- A/B harness adds CI cost. Mitigated by ≥20 tasks/archetype/rail
  budget — runs only on `validate.yml` PR triggers, not push.

**Trade-offs explicitly accepted:**

- We do NOT optimize for Opus 4.6 fallback. Native subagent path is
  4.7+ specifically. Adopters on 4.6 set `CEO_NATIVE_SUBAGENTS=0`
  (custom rail, no regression).
- We do NOT migrate all archetypes. Canonical-5 only because they are
  the highest-frequency spawns (per audit-log historical data).
- We do NOT remove the custom rail entirely. Custom rail is fallback
  + extension surface for adopter-specific personas.

## Acceptance for ADR-050 closure

(Tracked in PLAN-020 §10 Success criteria — A4 rubric pass rate +
A1 test suite + benchmark sub-targets.)

- [ ] Native rail spawn produces non-null `tokens_in`/`tokens_out`
      in audit log (additive `rail: native|custom` discriminator
      schema bump v2.7).
- [ ] 5 canonical-5 native agent files exist with valid frontmatter +
      pass `actionlint` YAML frontmatter step.
- [ ] `_dispatch.md` auto-generated on validate-governance.sh; manual
      edits caught by CI lint.
- [ ] Kill-switch matrix (PLAN-020 §6a) covers all 4 toggle combinations
      tested in CI.
- [ ] upgrade.sh preserves adopter `.claude/agents/custom-*.md` —
      tested in `tests/integration/test_upgrade_preserves_custom_agents.py`.
- [ ] A/B rubric pass rate ≥ Phase 0 baseline, 1-sided 90% CI lower
      bound ≥ (baseline − 5pp), N ≥ 20 per archetype per rail.

## References

- PLAN-020 §4 Phase 1 (native subagents dual-rail design)
- PLAN-020 §6.1 Q2 Owner answer (default=1 opt-out)
- PLAN-020 §6a Kill-switch matrix
- ADR-051 (skill-by-reference; native rail uses reference sentinel)
- DevOps debate critique §S1 must-fix #2 (single decision point)
- VP Engineering debate critique §S1 must-fix #1 (ADR renumber 049→050)
- Performance debate critique §S1 must-fix #6 (decomposition table)
- Phase 0 item 5 (native-hook probe gate; 0/3 = Phase 1 NO-GO)

## Enforcement commit

`3917fec1bfd9` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
