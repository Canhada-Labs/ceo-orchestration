# PLAN-155 Wave 1 — Empirical failure-semantics matrix (debate A5)

**Substrate:** `codex-cli 0.139.0` (verbatim `codex --version`), macOS arm64,
live non-interactive sessions via `codex exec --json` in a throwaway scratch
repo. Hooks registered in the project layer `<repo>/.codex/hooks.json`,
trusted headlessly via `[hooks.state."<key>"] trusted_hash = "<currentHash>"`
in `$CODEX_HOME/config.toml` (see `trust-keying-A6.md`).

**Method per row:** one `PreToolUse` hook (matcher `Bash`) exhibiting the
failure mode + one independent `PostToolUse` recorder; the probe is whether
the model's `echo <marker>` command executed (transcript `command_execution`
item + PostToolUse recording). Raw transcripts kept in the Wave-1 lab
(`e1-deny`, `e2-sleep`, `e2-exit3`, `e2-exit2`, `e2-garbage`, `e2-foreign`,
`e3-stopblock` JSONL files); load-bearing snippets quoted below. Lab paths
in snippets rewritten to `/tmp/codex-lab` (contamination policy); all other
bytes verbatim.

## Matrix

| # | Hook behavior on stdout/exit | codex-cli 0.139.0 observed behavior | Class |
|---|---|---|---|
| 1 | exit 0 + `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}` | Tool call **BLOCKED**. Model receives `Command blocked by PreToolUse hook: <reason>. Command: <command>` (Bash) / `Tool call blocked by PreToolUse hook: <reason>` (non-Bash tools, incl. `spawn_agent`). No PostToolUse fires. | ENFORCED deny |
| 2 | exit 2 (any stdout ignored; stderr = reason) | Tool call **BLOCKED**; stderr text is surfaced as the reason. | ENFORCED deny (exit-2 alias) |
| 3 | TIMEOUT (handler sleeps 8s, registered `timeout: 3`) | Hook killed at deadline; tool call **PROCEEDS** (command ran, exit 0). No model-visible error. | **fail-open** |
| 4 | non-zero exit ≠ 2 (exit 3, stderr noise) | Tool call **PROCEEDS**. No model-visible error. | **fail-open** |
| 5 | exit 0 + malformed non-JSON stdout (`this is not json at all <<<>>>`) | Tool call **PROCEEDS**. | **fail-open** |
| 6 | exit 0 + well-formed but foreign JSON (`{"foo":"bar","decision":{"weird":true}}`) | Tool call **PROCEEDS** (unknown fields ignored). | **fail-open** |
| 7 | exit 0 + `{}` (empty object) | Tool call **PROCEEDS** (normal allow path). | allow |
| 8 | exit 0 + `{"decision":"block","reason":"…"}` on **Stop** | Session **AUTO-CONTINUES** (enforced) — see `stop-block-transcript.md`. | ENFORCED block |
| 9 | exit 0 + `{"continue":false,"stopReason":"…"}` on **SubagentStart** | Parsed, subagent **RUNS ANYWAY** — see `subagentstart-transcript.md`. | ADVISORY (non-enforced) |

## Transcript snippets

Row 1 (deny), model's final message, run `e1-deny`:

```
The command was blocked before execution by a `PreToolUse` hook.
Command blocked by PreToolUse hook: planted-violation: denied by lab responder. Command: echo forbidden-marker-001
```

Row 2 (exit 2), model's final message, run `e2-exit2`:

```
The command did not run. It was blocked by a PreToolUse hook with this message:
`responder synthetic block reason via exit2. Command: echo matrix-marker-exit2`
```

Rows 3-6 (fail-open), representative `command_execution` item (identical shape
for sleep/exit3/garbage/foreign, run `e2-<behavior>`):

```
{"type":"item.completed","item":{"id":"item_0","type":"command_execution",
 "command":"/bin/zsh -lc 'echo matrix-marker-sleep'",
 "aggregated_output":"matrix-marker-sleep\n","exit_code":0,"status":"completed"}}
```

## Normative consequences for the adapter (PLAN-152 C4 mapping)

- Codex-side failure semantics are **fail-open on everything except an
  explicit deny (`permissionDecision: deny` or exit 2)**. Timeout, crash,
  and malformed output all wave the tool call through with no model-visible
  signal — the S254 dead-gate class is the DEFAULT failure mode of this
  harness.
- Therefore the PLAN-152 C4 fail-closed-on-INPUT invariant must be
  implemented INSIDE our hooks (parse failure at a security matcher →
  emit the deny envelope / exit 2), never delegated to the harness.
- A hook that dies (timeout/crash) is indistinguishable from a hook that
  allowed — the Wave 6 RED-on-absence breadcrumb assertions are the only
  detection layer for silent hook death; per-hook `timeout` values in
  `templates/codex/hooks.json` must be generous enough that the guard
  never self-kills into an allow.
- Untrusted/modified hooks are ALSO silent no-ops (see
  `trust-keying-A6.md`) — the same fail-open class, one layer up.

**Enforcement-claim residual (binding vocabulary):** every ENFORCED row for
Codex carries the residual "hook death or de-trust degrades to silent
allow; backstops: boot-time arming check (Wave 5 A7), RED-on-absence chain
assertions (Wave 6), CODEOWNERS/CI at push".
