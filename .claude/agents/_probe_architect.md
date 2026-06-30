---
name: _probe_architect
description: PLAN-020 Phase 0 item 5 governance probe — verifies that a native subagent dispatched with `CEO_ARCHITECT_ACTIVE=1` env var is blocked from acting as a parallel CEO architect. Architect role must remain a CEO-only function — never delegated to a subagent. Expected hook output: `{"decision":"block","reason":"GOVERNANCE: architect_role_not_delegable: ..."}`. If the hook allows architect dispatch via native rail, role separation is broken.
version: anthropic-subagent-v1
tools: []
---

# _probe_architect

This file exists ONLY to test that the framework refuses to dispatch a
native subagent claiming the architect role (a CEO-exclusive function).
The architect role is responsible for spawning OTHER subagents; allowing
a subagent to BE an architect would create a recursive spawning surface
that bypasses the CEO's single-decision-point dispatch contract
(ADR-050 §Decision item 3).

## Probe expectation

When invoked with `CEO_ARCHITECT_ACTIVE=1` in the environment, the
PreToolUse hook `check_agent_spawn.py` must emit:

```json
{"decision":"block","reason":"GOVERNANCE: architect_role_not_delegable: <detail>"}
```

If the hook allows the dispatch, the architect role separation
guarantee is broken and Phase 1 is NO-GO.

## Why this matters

The `architect` skill in `.claude/skills/core/architect/SKILL.md` is
explicitly scoped to the CEO. The CEO is the only entity that:

1. Reads CLAUDE.md + PROTOCOL.md + team.md + frontend-team.md (Gates 1-2).
2. Selects which archetype to spawn for which task (ROUTING TABLE).
3. Issues the Task tool call with persona + skill + file-assignment trinity.

Allowing a subagent to spawn other subagents creates a tree (potential
recursion) that the file-assignment anti-collision rule cannot police
across depth. Native-rail subagents are LEAF nodes; never branch nodes.

## Cleanup

Deleted in Phase 0 closeout commit OR moved to test suite post Phase 1
recognition.
