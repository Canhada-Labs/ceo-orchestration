---
name: _probe_missing_skill
description: PLAN-020 Phase 0 item 5 governance probe — verifies that `check_agent_spawn.py` BLOCKS dispatch via the native subagent rail when the spawn prompt has no skill content (neither `## SKILL CONTENT` inline NOR `## SKILL REFERENCE`). Expected hook output for any Task tool call dispatching this agent: `{"decision":"block","reason":"GOVERNANCE: missing_skill_content: ..."}`. If the hook ALLOWS this dispatch, native rail has a governance gap and Phase 1 is NO-GO.
version: anthropic-subagent-v1
tools: []
---

# _probe_missing_skill

This file exists ONLY to test that the framework's `check_agent_spawn.py`
hook correctly rejects native-rail spawns that lack skill content. It is
not a real agent and should never be invoked outside the Phase 0 native-
probe harness.

## Probe expectation

When the CEO (or any caller) issues a Task tool call referencing this
agent, the PreToolUse hook `check_agent_spawn.py` must emit:

```json
{"decision":"block","reason":"GOVERNANCE: <reason_code>: <detail>"}
```

The exact reason code may be `missing_skill_content` (inline path) or
`reference_missing` (reference path) — both are acceptable.

If the hook emits `{"decision":"allow"}`, the probe FAILS and Phase 1
is NO-GO per PLAN-020 §4 Phase 0 item 5.

## Why this matters

PLAN-019 P1-SEC-B hardened the inline `## SKILL CONTENT` 256-byte floor
+ fence/comment mask in `_has_skill_content`. PLAN-020 expands the
sentinel surface (Phase 2 adds `## SKILL REFERENCE` parallel path).
Native-rail dispatch must inherit equivalent or stricter discipline,
not bypass.

## Cleanup

This file is deleted in the Phase 0 closeout commit OR after Phase 1
recognition lands and the probe is moved into the test suite as a
`subprocess` harness invocation. It MUST NOT remain in main long-term.
