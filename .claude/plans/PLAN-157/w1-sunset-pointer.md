# PLAN-157 W1 sunset pointer (OQ2 — git-history-only deletion)

> **What this is.** PLAN-157 W1 removed four grandfathered squad trees from
> `.claude/skills/domains/`. Per Owner-ratified **OQ2**, the deletion is
> **git-history-only**: no tarball, no graveyard branch, no `archive/` copy.
> This document is the durable pointer to where the content lives in history.

## Recovery anchor

- **Final pre-deletion commit (parent of the W1 deletion commit):**
  `__LAND_SHA__`
  *(placeholder — the land script fills this with `git rev-parse HEAD`
  immediately before the deletion commit; if you are reading this in a
  landed tree and still see the placeholder, the land script skipped the
  fill step: use the parent of the commit that deleted the trees —
  `git log --diff-filter=D -1 --format=%H^ -- .claude/skills/domains/desktop`.)*

## What was deleted (squads → skills)

| Squad (roster entry) | Disposition | Skills removed |
|---|---|---|
| `desktop` | sunset | `windows-desktop-e2e` (+ `references/page-object-and-isolation.md`) |
| `dotnet` | sunset | `csharp-testing` |
| `architecture` | fold + sunset | `hexagonal-architecture`, `recsys-pipeline-architect` |
| `agents-meta` | fold + sunset | `dynamic-workflow-mode`, `loop-design-check` |

All four squads were PLAN-153 Wave D skills-only imports (S262, 2026-07-09,
`community`-posture per ADR-060). The fold artifacts for `architecture` and
`agents-meta` (content merged into surviving skills) are staged separately
under the W1 folds pack — this pointer covers only the tree deletions.

## How to recover

```sh
# Inspect a deleted skill:
git show __LAND_SHA__:.claude/skills/domains/desktop/skills/windows-desktop-e2e/SKILL.md

# Restore a whole squad tree into the working copy:
git checkout __LAND_SHA__ -- .claude/skills/domains/dotnet

# List everything that existed pre-deletion:
git ls-tree -r --name-only __LAND_SHA__ .claude/skills/domains/agents-meta
```

**Reopen gate.** Re-adding any of these squads is a new Owner-gated decision:
the roster cap is now `cap: 28` with zero headroom
(`.claude/policies/grandfather-cap.policy.yaml`, OQ3 cap := current), and
`sunset_reopen_window_days: 14` means a spawn with a matching
`dispatch_archetype_hint` inside 14 days trips the reopen alert
(`audit-query.py by-domain --check-reopen`).

Full per-file deletion list: `deletion-manifest.txt` (same directory).
