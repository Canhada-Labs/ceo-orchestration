# ADR-010: Canonical-edit sentinel for meta-agent drafts

**Status:** ACCEPTED
**Date:** 2026-04-13
**Sprint:** 5 Phase 7
**Related:** ADR-005 (event stream), ADR-009 (squad contract)

## Context

PLAN-005 Phase 7 (B.3) introduces the **Agent Architect** meta-agent —
a slash command (`/architect <domain-brief>`) that drafts the 5-artifact
bundle (team-personas, pitfalls, skill-selection, personas roster,
rationale) for a candidate new squad based on a brief from the Owner.

The meta-agent's drafts must NOT directly mutate canonical paths
(`team.md`, `frontend-team.md`, `pitfalls-catalog.yaml`, `skills/**/SKILL.md`).
Without a guardrail, a misaligned brief could rewrite the framework's
governance contracts in a single session.

## Decision drivers

- **Drafts vs canonical.** The Architect emits files into a sandboxed
  plan subdir (`.claude/plans/PLAN-NNN/architect/round-1/`). Adopters
  review the drafts; only after Owner sign-off do contents migrate
  to canonical paths.
- **Sentinel signature.** Adopting a draft into canonical paths
  requires an Owner-signed sentinel file
  (`approved.md`) co-located in the bundle dir. The sentinel carries
  a literal `Approved-By: @<owner> <commit-sha>` line.
- **Mechanical enforcement.** A new PreToolUse hook
  (`check_canonical_edit.py`) inspects Edit/Write/MultiEdit calls
  against canonical paths; it BLOCKS unless the matching sentinel
  exists with a valid signature.
- **Recursion prevention.** The Architect MUST NOT spawn another
  Architect within the same session; `check_agent_spawn.py` detects
  the recursion via env var `CEO_ARCHITECT_ACTIVE`.

## Decision

Ship four pieces in Sprint 5 Phase 7:

1. `/architect <domain-brief>` slash command + Agent-Architect SKILL.md
2. `architect-bundle-validate.py` — validates draft bundle shape
3. `check_canonical_edit.py` PreToolUse hook — sentinel enforcement
4. `check_agent_spawn.py` extension — recursion guard

### Sentinel format

```markdown
---
plan: PLAN-NNN
round: 1
type: architect-sentinel
---

Approved-By: @<owner-handle> <commit-sha-of-bundle-PR>
Approved-At: 2026-04-13T15:30:00Z
Scope:
  - .claude/skills/domains/<squad>/team-personas.md
  - .claude/skills/domains/<squad>/pitfalls.yaml
  - ...
```

The hook reads the sentinel, parses the `Scope:` block, and allows
edits to those exact paths. Edits outside the declared scope are
blocked even with a valid sentinel.

### Canonical paths guarded (locked in v1)

- `.claude/team.md`
- `.claude/frontend-team.md`
- `.claude/pitfalls-catalog.yaml`
- `.claude/skills/**/SKILL.md`
- `.claude/skills/domains/**/team-personas.md`
- `.claude/skills/domains/**/pitfalls.yaml`
- `.claude/skills/domains/**/skills/**/SKILL.md`

`PROTOCOL.md`, `CLAUDE.md`, and `ADR-*.md` are NOT guarded. They are
Owner-authored governance docs; bringing them under the sentinel adds
blast radius without addressing a meta-agent attack vector (per Owner
decision logged in PLAN-005 §9 Q3 default).

### Amendment 2026-04-14 — Sprint 9 additions (PLAN-009 C1.0 / C1.1)

Per PLAN-009 A22 and A14:

- `.claude/**/conftest.py` added to the sentinel list. Rationale: the
  Sprint 9 confidence-gate hook invokes `pytest --collect-only` during
  claim verification, which imports `conftest.py`. An agent-tampered
  conftest would execute under the gate's privileges before verification
  completes. Blocking conftest edits behind the sentinel closes that
  escalation path (defense-in-depth for A3 pytest-argv hardening).
- `.claude/hooks/check_confidence_gate.py` added to the sentinel list
  (the new Sprint 9 hook itself).
- The existing `.claude/scripts/lessons.py`,
  `.claude/scripts/prune-lessons.py`, `.claude/scripts/lesson-restore.py`,
  and (Sprint 9 Phase 5) `.claude/scripts/lesson_ranker.py` are ALSO
  explicitly covered here — edits to any of them must come through a
  sentinel-approved Architect bundle.

Full amended list (v1.1):

- `.claude/team.md`
- `.claude/frontend-team.md`
- `.claude/pitfalls-catalog.yaml`
- `.claude/skills/**/SKILL.md`
- `.claude/skills/domains/**/team-personas.md`
- `.claude/skills/domains/**/pitfalls.yaml`
- `.claude/skills/domains/**/skills/**/SKILL.md`
- `.claude/**/conftest.py` *(added Sprint 9)*
- `.claude/hooks/check_confidence_gate.py` *(added Sprint 9)*
- `.claude/scripts/lessons.py` *(explicit Sprint 9)*
- `.claude/scripts/prune-lessons.py` *(explicit Sprint 9)*
- `.claude/scripts/lesson-restore.py` *(explicit Sprint 9)*
- `.claude/scripts/lesson_ranker.py` *(added Sprint 9 Phase 5)*

### Recursion guard

`check_agent_spawn.py` checks the env var `CEO_ARCHITECT_ACTIVE`:

- The `/architect` command sets `CEO_ARCHITECT_ACTIVE=1` before
  spawning the Architect.
- If `check_agent_spawn.py` sees a spawn whose persona matches
  `Agent Architect` AND `CEO_ARCHITECT_ACTIVE=1` is in the
  environment, the spawn is BLOCKED with reason code
  `architect_recursion`.

### Sentinel-enforcement hook deferral path

Per PLAN-005 §3 Phase 7, the sentinel-enforcement hook MAY slip to
Sprint 6 if Phases 5+6 overran. Result for this Sprint 5: shipped
in-sprint (no slip needed).

## Consequences

### Positive

- Meta-agent drafts are sandboxed by design.
- Adopting a draft into canonical paths leaves an Owner-signed audit
  trail.
- Recursion is impossible — no Architect-spawning-Architect loops.
- Bundle validator catches malformed drafts before review wastes time.

### Negative

- Adds one PreToolUse hook to the dogfood `settings.json` (slight
  CPU cost on every Edit/Write call). Mitigated by paths-filter:
  the hook short-circuits `decision: allow` if the touched path is
  not in the canonical guard list.
- Sentinel discipline relies on the Owner reviewing the bundle. The
  hook can only verify the signature, not the wisdom of the change.

### Neutral

- The sentinel format is a Markdown frontmatter convention; future
  tooling MAY parse it but isn't required to.

## Blast radius

L2:
- New `.claude/hooks/check_canonical_edit.py` (PreToolUse Edit/Write/MultiEdit)
- New `.claude/hooks/tests/test_check_canonical_edit.py`
- Extension to `check_agent_spawn.py` for recursion guard
- New `.claude/scripts/architect-bundle-validate.py`
- New `.claude/skills/core/agent-architect/SKILL.md`
- New `.claude/commands/architect.md`
- Settings.json wire-up (Edit matcher → check_canonical_edit.py)

**Reversibility:** HIGH — the hook can be removed by deleting the
settings.json stanza; the script + skill files are inert when not
invoked.

## References

- PLAN-005 §3 Phase 7 + §9 Q3
- ADR-005 (event stream — sentinel could emit `veto_triggered` events)
- ADR-009 (squad contract — Architect helps draft new squads)

## Enforcement commit

`414cf213f904` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
