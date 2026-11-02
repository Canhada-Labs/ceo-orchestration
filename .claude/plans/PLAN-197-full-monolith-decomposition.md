---
id: PLAN-197
title: Full monolith decomposition
status: done
created: 2026-11-01
completed_at: 2026-11-01
owner: CEO
depends_on: []
related_commits: [027895f1, 9c020955]
tags: [architecture, modularization, compatibility]
---

# PLAN-197: Full monolith decomposition

This retrospective records the decomposition integrated by the listed commits;
“full” names this plan and does not assert that all repository monoliths have
been decomposed. [ADR-202](../adr/ADR-202-kernel-and-hooks-modularization.md)
records the compatibility decision.

| Existing entry point | Extracted implementation |
| --- | --- |
| `.claude/hooks/_lib/audit_emit.py` | `.claude/hooks/_lib/_audit_emit_parts/` domain declarations |
| `.claude/hooks/check_agent_spawn.py` | `.claude/hooks/_lib/agent_spawn/` skill references and file assignments |
| `.claude/hooks/check_canonical_edit.py` | `.claude/hooks/_lib/canonical_edit/` paths, sentinels and session roots |
| `.claude/scripts/check-installer-write-safety.py` | `.claude/scripts/_installer_write_safety/` census components |
| `.claude/scripts/check_contamination.py` | `.claude/scripts/_contamination/` personal paths and term scan |
| `.claude/scripts/audit-query.py` | `.claude/scripts/_audit_query/` queries and reporting |

## Compatibility contract

- Existing entry paths remain usable. Component exports, including private
  seams declared in `__all__`, are installed on the facade where implemented;
  functions bound to facade globals observe patches at the historical seam.
- `audit_emit` reload creates fresh copied mutable declarations. The focused
  `test_audit_emit_modular_facade.py` checks captured payloads, patched public
  dispatch and private helpers, and reload behavior. The canonical-edit
  component tests exercise its module integration and import failure path.
- AST consumers need the source shape they actually inspect. `audit-query.py`
  retains named delegates for the read-API freeze guard; `audit_emit.py` keeps
  an `iter_events` delegate for that guard and the literal registry required
  by registry extraction. Extracted functions
  are not literally present as definitions in the facade AST: a reader that
  enumerates `emit_` definitions sees only those still in that file. Preserve
  or adapt each reader explicitly when moving symbols.
- Separate import-integrity work handles the canonical-edit entry point; this
  completed decomposition does not assert uniform failure behavior across
  all packages or a general integrity guarantee.
