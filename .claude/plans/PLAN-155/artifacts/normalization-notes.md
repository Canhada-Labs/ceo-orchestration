# PLAN-155 Wave 1 — Codex hook wire → NormalizedEvent normalization notes

Companion to the recorded fixtures at
`staged/wave-1/.claude/hooks/tests/fixtures/adapters/codex/in/*.json`
(17 fixtures, ≥2 per consumed event, every one recorded from live
codex-cli 0.139.0 sessions; `_meta.codex_cli_version` = `codex-cli 0.139.0`
verbatim from `codex --version`; lab absolute paths rewritten to
`/tmp/codex-lab`, all other bytes verbatim).

## Observed input wire (stdin JSON, snake_case)

Common fields on EVERY event:

| Codex field | Type | Notes |
|---|---|---|
| `session_id` | uuid string | maps → NormalizedEvent.session_id |
| `transcript_path` | abs path | rollout JSONL under `$CODEX_HOME/sessions/…` |
| `cwd` | abs path | workspace root of the session |
| `hook_event_name` | PascalCase enum | `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStart`, `SubagentStop` all observed live; `PermissionRequest`/`PreCompact`/`PostCompact` registered but never fired under `codex exec` (exec runs `permission_mode: bypassPermissions`, no compaction triggered) |
| `model` | string | e.g. `gpt-5.5` |
| `permission_mode` | string | `bypassPermissions` observed under exec |
| `turn_id` | uuid string | absent on SessionStart; present on all turn-scoped events |

Event-specific fields observed:

- **SessionStart**: `source: "startup"`.
- **UserPromptSubmit**: `prompt: "<full user prompt>"`.
- **PreToolUse**: `tool_name`, `tool_input` (object), `tool_use_id`
  (`call_…`). Observed `tool_name` values: `Bash`
  (`tool_input: {"command": "<full shell string>"}`), `apply_patch`
  (`tool_input: {"command": "*** Begin Patch\n*** Add File: … / *** Update File: …\n…*** End Patch\n"}`),
  `spawn_agent` (`tool_input: {"message": "...", "agent_type": "default"}`).
- **PostToolUse**: same as PreToolUse + `tool_response` — a plain STRING
  (Bash: raw output; apply_patch: `"Exit code: 0\nWall time: …\nOutput:\n…"`),
  not an object.
- **Stop**: `stop_hook_active` (bool loop-guard; `true` on re-entry after a
  block), `last_assistant_message`.
- **SubagentStart**: `agent_id`, `agent_type` (`"default"`).
- **SubagentStop**: `agent_id`, `agent_type`, `agent_transcript_path`,
  `stop_hook_active`, `last_assistant_message`.

## Normalization sketch (`read_event`, host mode)

- `hook_event_name` → NormalizedEvent.event (same PascalCase vocabulary as
  the Claude wire — no renames needed for the 6 consumed events).
- `tool_name` mapping: `Bash` → `Bash` (command in `tool_input.command`,
  full string, same as Claude); **`apply_patch` → `Edit`/`Write`
  semantics**: the patch BODY must be parsed for
  `*** Add File: <path>` (→ Write-new), `*** Update File: <path>`
  (→ Edit), `*** Delete File: <path>`, `*** Move to: <path>` headers; one
  patch may touch MANY files → normalized event must carry the full path
  LIST (guard denies if ANY path is guarded). There is no
  per-file structured field on the wire — the raw patch text in
  `tool_input.command` is all we get.
- `spawn_agent` → normalized spawn-tool event (NEW fact: collab spawns are
  PreToolUse-interceptable and deny-able; see
  `subagentstart-transcript.md` §B).
- `mcp__…` MCP tool names: not exercised in this lab (no MCP server in the
  scratch repo) — matcher reserved, fixture gap named in open issues.
- snake_case on the wire vs the Claude adapter's camelCase-ish fields:
  `session_id`/`transcript_path`/`cwd`/`hook_event_name`/`tool_name`/
  `tool_input`/`tool_response`/`tool_use_id` are byte-identical to Claude
  Code's PreToolUse/PostToolUse stdin vocabulary — the codex host wire is
  deliberately Claude-compatible ("ClaudeHooksEngine" is the literal
  upstream type name). Divergences to encode in the adapter: `turn_id`
  (codex extension), `agent_id`/`agent_type` (vs Claude's session-scoped
  subagent fields), `tool_response` always-string, `permission_mode`
  value `bypassPermissions` under exec, `source` on SessionStart.

## Decision egress (`write_decision`, host mode) — codex-accepted shapes

- PreToolUse deny (verified blocking):
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "<reason>"}}`
  — model sees `Command blocked by PreToolUse hook: <reason>. Command: <cmd>`
  (Bash) / `Tool call blocked by PreToolUse hook: <reason>` (other tools).
- PreToolUse allow: `{}` or `permissionDecision: "allow"`.
- Exit 2 + stderr = deny alias (verified) — our adapter emits the JSON
  envelope; exit 2 is the fallback for catastrophic paths.
- Stop block (verified auto-continue):
  `{"decision": "block", "reason": "<instruction to the model>"}`.
- SubagentStart context injection (verified end-to-end):
  `{"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": "<text>"}}`.
- SubagentStart `{"continue": false}`: parsed, NON-enforcing (ADVISORY).
- Anything else (foreign JSON, garbage, non-2 exit, timeout): silent allow
  (see `failure-semantics-matrix.md`).

## Expected normalized-output sketches per fixture

| fixture | expected normalization |
|---|---|
| `pre_tool_use.bash.echo.json` / `.compound.json` | event=PreToolUse, tool=Bash, command string passthrough |
| `pre_tool_use.apply_patch.add-file.json` | event=PreToolUse, tool=Write-equivalent, paths=[`notes.txt`], patch verb=Add |
| `pre_tool_use.apply_patch.update-file.json` | event=PreToolUse, tool=Edit-equivalent, paths=[`notes.txt`], patch verb=Update |
| `pre_tool_use.spawn_agent.json` | event=PreToolUse, tool=spawn_agent, message+agent_type surfaced for spawn-protocol check |
| `post_tool_use.bash.json` / `.apply_patch.json` | event=PostToolUse, tool_response as opaque string payload for audit append |
| `session_start.startup.*.json` | event=SessionStart, source=startup → boot breadcrumb + hash re-check trigger |
| `stop.plain.json` | event=Stop, stop_hook_active=false → review-gate eligible |
| `stop.stop-hook-active.json` | event=Stop, stop_hook_active=true → loop-guard: do NOT re-block unconditionally |
| `subagent_start.default.*.json` | event=SubagentStart → additionalContext injection path (ADVISORY continue) |
| `subagent_stop.*.json` | event=SubagentStop, agent_transcript_path available for chain append |
| `user_prompt_submit.*.json` | event=UserPromptSubmit, prompt passthrough |

## Registration surface pinned (for `templates/codex/hooks.json`)

- Project layer `<repo>/.codex/hooks.json`
  (`{"hooks": {"<Event>": [{"matcher": "...", "hooks": [{"type": "command", "command": "<string>", "timeout": <sec>}]}]}}`)
  — VERIFIED live driving hooks. `[hooks]` tables in
  `<repo>/.codex/config.toml` and `$CODEX_HOME/hooks.json` also verified;
  ship exactly one (hooks.json). `timeout` in SECONDS, default 600, min
  clamped to 1. Matchers: `*`/omitted = all; exact `A|B` alternation; else
  regex. `UserPromptSubmit`/`Stop` accept no matcher (ignored).
  `async`/`prompt`/`agent` handler types are declared-but-unsupported on
  0.139 ("not supported yet" discovery warnings).
- The hook command is run via the user shell (`/bin/zsh -lc` observed for
  model commands; hook argv split observed working with plain
  `python3 <abs path> <arg>` command strings).
- Two gates before a project hook fires: project dir trust
  (`projects."<path>".trust_level`) AND per-hook trust hash — see
  `trust-keying-A6.md`.
