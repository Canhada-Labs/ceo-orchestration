# SPEC v1 — plan.schema

> **Normative source:** `.claude/plans/PLAN-SCHEMA.md`
> **Spec version:** 1.0.0-rc.1
> **Status:** stable within v1 MAJOR (additive changes only)

This file mirrors the authoritative schema. It exists here so that
third parties can consume the plan-file contract without depending on
the repo layout of ceo-orchestration itself.

## Canonical content

The authoritative specification is at
`.claude/plans/PLAN-SCHEMA.md` in the source repo. Any divergence
between this file and the source is a bug — report it against this
SPEC version.

## Summary (normative)

Plan files live at `.claude/plans/PLAN-<NNN>-<slug>.md` with:

- YAML frontmatter: `id`, `title`, `status`, `created`, `owner`, `depends_on`
- Lifecycle state machine: `draft → reviewed → executing → done` + `abandoned` terminal + `refused` terminal (per ADR-092). Reopen transition `done → executing` allowed via `reopen_via:` ADR + `reopen_trigger:` field (per ADR-092 honest-deferral framework, enforced by `check_plan_edit.py`).
- Body sections: `## Context`, `## Goal`, `## Approach`/`## Thesis`, `## Items`, `## Open questions`, `## How to continue`, `## Success criteria`
- Subdirectory `PLAN-<NNN>/` for debate transcripts (see `debate.schema.md`)
- Subdirectory namespace also reserves `examples/` for non-plan fixtures and `archive/` for retired plans

## Version history

| SPEC version | Source commit | Notes |
|---|---|---|
| 1.0.0-rc.1 | Sprint 4 opening | Initial published contract |

For the full normative text, read `.claude/plans/PLAN-SCHEMA.md`.
