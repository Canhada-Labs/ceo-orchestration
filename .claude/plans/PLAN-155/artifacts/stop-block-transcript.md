# PLAN-155 Wave 1 — Stop-hook `decision:block` enforcement transcript (debate A5)

**Verdict: ENFORCED on codex-cli 0.139.0.** A Stop hook returning
`{"decision":"block","reason":"…"}` does NOT let the session stop: codex
auto-continues the turn, feeds the reason to the model, and re-fires the
Stop hook (with `stop_hook_active: true`) when the model tries to stop
again. The pair-rail capability-matrix row can move from "PARTIAL, pending
Stop-block verification" to **verified stop-time enforcement** (the
kill-the-session residual stands unchanged).

## Setup

- `codex-cli 0.139.0`, live run `e3-stopblock` via
  `codex exec --json --sandbox workspace-write` in the scratch lab repo.
- Stop hook (stateful, count file): on invocation 1 emits
  `{"decision":"block","reason":"STOP GATE: before stopping you must run the shell command: echo stop-gate-ran"}`;
  on invocation ≥2 emits `{}`.
- Independent PreToolUse/PostToolUse recorders confirm what actually ran.
- User prompt: `Reply with the single word: done` (no command requested).

## Observed sequence (live)

1. Model replied `done` and tried to stop.
2. Stop hook invocation #1 — recorded stdin (sanitized paths, otherwise verbatim):

```json
{"session_id": "019f4a07-...", "turn_id": "019f4a07-...",
 "hook_event_name": "Stop", "model": "gpt-5.5",
 "permission_mode": "bypassPermissions",
 "stop_hook_active": false, "last_assistant_message": "done"}
```

   Hook stdout: `{"decision":"block","reason":"STOP GATE: before stopping you must run the shell command: echo stop-gate-ran"}`

3. Session did NOT stop. The model ran the demanded command — transcript
   `command_execution` item:

```
"command":"/bin/zsh -lc 'echo stop-gate-ran'"  → exit_code 0
```

   (PreToolUse + PostToolUse recordings for `echo stop-gate-ran` exist in
   the same run — the continuation was a real tool-executing turn, not a
   cosmetic message.)

4. Stop hook invocation #2 — stdin now carried the loop guard:

```json
{"hook_event_name": "Stop", "stop_hook_active": true,
 "last_assistant_message": "done", ...}
```

   Hook stdout `{}` → session stopped, `codex exec` exit 0.

Hook-state counter after the run: `2` invocations. Marker `stop-gate-ran`
appears in the transcript's executed-command output.

## Notes for Wave 6 (inverted pair-rail)

- `stop_hook_active: true` is the harness-provided loop guard — the Wave 6
  Stop rail must consult it (or its own review-record check) to terminate
  the block loop, mirroring the Claude Code pattern.
- `last_assistant_message` is available at Stop time for review-context.
- Residual unchanged: killing the `codex` process abandons the Stop gate —
  the git pre-push backstop remains the teeth for that path; and this was
  verified under `codex exec` (headless); the TUI path is expected
  equivalent but was not exercised here.
