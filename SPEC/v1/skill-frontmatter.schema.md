# SPEC v1 — skill-frontmatter.schema

> **Spec version:** 1.1.0
> **Status:** normative

Every `SKILL.md` file in a compliant ceo-orchestration installation
MUST have a YAML frontmatter block matching this contract.

## Minimum required fields

```yaml
---
name: <display name or kebab-case slug>
description: <one-paragraph description of the skill>
owner: <archetype name | persona name | "CEO">
---
```

## Optional fields (recognized by the registry)

```yaml
secondary_owner: <archetype>       # additional VETO holder
tier: <core | frontend | domain:<name>>   # derived from path if absent
veto: <VETO statement>             # informational
tags: [<tag>, <tag>, ...]          # not yet consumed; reserved
scope_tags: [<tag>, <tag>, ...]    # Sprint 5+ (reserved)
requires: [<skill-id>, ...]        # Sprint 5+ (reserved)
forbids: [<skill-id>, ...]         # Sprint 5+ (reserved)
deprecated_in: "X.Y.Z"             # if scheduled for removal
removed_in: "X.Y.Z"                # required if deprecated_in set
paths: ["<glob>", ...]             # PLAN-135 K1: auto-activation globs — if present,
                                   #   MUST be a NON-EMPTY list of non-empty glob
                                   #   strings (fnmatch semantics against the
                                   #   repo-relative path of a touched file);
                                   #   lint: LINT-FM-40
context: <fork | main>             # PLAN-135 K1: execution context — `fork` runs the
                                   #   skill in a forked (isolated) context (heavy
                                   #   analytic skills); `main` = explicit default
                                   #   (inline). Absence == main; lint: LINT-FM-41
```

## Auto-activation semantics (`paths:` — PLAN-135 K1)

- A skill carrying `paths:` SHOULD be surfaced/announced when a touched
  file's repo-relative path matches ≥1 of its globs (Python `fnmatch`).
- Globs are matched against repo-relative paths (no leading `./`).
- `paths:` coexists with the smart-loading field
  `activation_triggers: [{event: file-edit, glob: ...}]` (PLAN-083);
  `paths:` is the portable, harness-native surface, `activation_triggers`
  the in-house smart-loading layer. Validators MUST accept both.
- `/architect` skill proposals emit `paths:` by default
  (agent-architect SKILL §What the meta-agent emits).

## Canonical skill ID

The **directory name** is the stable skill identifier, independent of
the `name:` field. Frontend skills may use display names in `name:`
("Code Quality & TypeScript"); the directory slug
(`code-quality-and-typescript`) is the stable ID used by the registry,
hooks, and task chains.

## Path → tier mapping

| Path prefix | Tier |
|---|---|
| `.claude/skills/core/<slug>/SKILL.md` | `core` |
| `.claude/skills/frontend/<slug>/SKILL.md` | `frontend` |
| `.claude/skills/domains/<domain>/skills/<slug>/SKILL.md` | `domain:<domain>` |

## Parser tolerance

- YAML folded scalars (multi-line descriptions with indented continuations) MUST be supported
- Additional fields MUST NOT cause parse failures
- Absence of any optional field MUST NOT cause errors

Reference parser: `.claude/scripts/registry.py` (stdlib-only, ~50 LOC).

## Version history

| SPEC version | Notes |
|---|---|
| 1.0.0-rc.1 | Initial formal contract extracted from existing convention |
| 1.1.0 | PLAN-135 W3 K1: optional `paths:` (auto-activation globs, LINT-FM-40) + `context:` (enum `fork`\|`main`, LINT-FM-41); auto-activation semantics section |
