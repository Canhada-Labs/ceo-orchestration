# SPEC v1 — hook-io.schema

> **Spec version:** 1.0.0-rc.1
> **Status:** normative

Defines the stdin payload each ceo-orchestration hook receives and the
stdout decision it emits. Matches the Claude Code hook contract today;
the Hook Adapter Layer (Phase 4) lets alternative IDEs map their own
payload shapes to this shared contract.

## Hook invocation

Hooks are registered in `.claude/settings.json` under one of:

- `hooks.PreToolUse.<Tool>` — fires BEFORE the tool executes; may block
- `hooks.PostToolUse.<Tool>` — fires AFTER the tool executes; never blocks

Each hook receives a single JSON payload on stdin, emits a single JSON
decision on stdout, and MUST exit 0 regardless of decision (Claude Code
reads the decision from stdout, not the exit code).

**Host-specific exit ABI (PLAN-156 Wave 2 — grok-scoped).** The rule
above is universal for Claude Code and OpenAI Codex, whose hosts read
the decision from stdout. Under **xAI Grok Build**
(`CEO_HOOK_ADAPTER=grok`) the shared shim (`_python-hook.sh`) additionally,
on BLOCKING events (grok `pre_tool_use`) ONLY:

1. **rewrites the decision vocabulary** `"block"` → `"deny"` on stdout —
   grok does not recognize `block` and fail-OPENs on it, *even with exit
   2* (empirically: block+exit-2 ⇒ the tool ran). This rewrite is the
   ENFORCEMENT mechanism on grok and is NOT disableable; and
2. **maps an emitted deny to exit 2** (belt-and-suspenders; grok's stdout
   JSON deny already blocks on its own, so exit 2 is secondary and is
   disableable via `CEO_HOOK_EXIT_MAP=0`). A crash with NO decision on
   stdout keeps the hook's own (fail-open) exit code — the
   INFRASTRUCTURE half of the fail-open doctrine is preserved.

This is adapter-SCOPED, not universal: exit 2 is an ACTIVE deny on Codex
PreToolUse (not inert), so remapping it there would change an observable
with zero enforcement gain — the mapping fires only under grok, and
Claude/Codex hooks remain byte-identical to the `exit 0 regardless`
contract above.

## Input payload (stdin)

```json
{
  "session_id": "<opaque string>",
  "tool_name": "Agent" | "Edit" | "Write" | "Bash" | "...",
  "tool_input": { "<tool-specific fields>": "..." },
  "tool_response": { "...": "..." }      // PostToolUse only
}
```

### Tool-specific `tool_input` fields (non-exhaustive)

| tool_name | fields |
|---|---|
| `Agent` | `description`, `prompt`, `subagent_type`, `run_in_background` |
| `Edit` | `file_path`, `old_string`, `new_string`, `replace_all` |
| `Write` | `file_path`, `content` |
| `Bash` | `command`, `description`, `timeout`, `run_in_background` |

## Output decision (stdout)

Exactly one JSON line:

```json
{"decision": "allow"}
```

or

```json
{"decision": "block", "reason": "<helpful string explaining why>"}
```

Optional fields:

```json
{
  "decision": "allow",
  "systemMessage": "<advisory to CEO, not blocking>"
}
```

- `decision` is the only mandatory field.
- `reason` is mandatory when `decision: "block"`.
- `systemMessage` is advisory and shown to the CEO without blocking.

## Fail-open contract

Every compliant hook MUST:

1. **Never exit non-zero** — Claude Code ignores exit codes; non-zero is a no-op
2. **Allow on internal error** — if the hook crashes, the best-effort recovery is to emit `{"decision":"allow"}` and log a breadcrumb
3. **Never block on infrastructure failure** — parse errors, missing files, lock timeouts MUST fail open
4. **Be silent when composable** — when multiple hooks share a matcher, only one should speak on stdout unless they explicitly coordinate

## Environment contract

Hooks MAY read these environment variables:

| Variable | Purpose |
|---|---|
| `CLAUDE_PROJECT_DIR` | Absolute path to the target project root |
| `CEO_AUDIT_LOG_*` | Audit log location overrides (see audit-log.schema) |
| `HOME` | User home directory (fallback for audit log location) |

Hooks MUST NOT assume any other environment variables exist.

## Version history

| SPEC version | Notes |
|---|---|
| 1.0.0-rc.1 | Initial contract extracted from Claude Code's hook JSON shape |
| 1.0.0 (PLAN-156 W2) | Grok-scoped exit ABI addendum: under `CEO_HOOK_ADAPTER=grok` the shim rewrites `block`→`deny` (enforcement) and maps emitted-deny→exit 2 (belt-and-suspenders, `CEO_HOOK_EXIT_MAP=0` disables) on blocking events; Claude/Codex unchanged (exit 0 regardless). SENT-GK-A. |
