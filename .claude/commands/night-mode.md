---
description: Owner-invoked autonomy posture toggle — hands you the exact command to arm acceptEdits for the NEXT session, reversibly and audited — /night-mode on|off|status
argument-hint: "on|off|status"
allowed-tools: Read
---

# /night-mode — Owner autonomy posture toggle (PLAN-165)

Usage: `/night-mode on`, `/night-mode off`, or `/night-mode status`.

Arms or disarms a per-machine autonomy posture: `on` sets
`permissions.defaultMode: "acceptEdits"` in the gitignored
`.claude/settings.local.json` overlay; `off` restores the snapshotted
prior value. The tracked `.claude/settings.json` (the published
fail-closed default, `defaultMode: "manual"`) is **never touched**. All
logic lives in `.claude/scripts/night-mode.py`.

## ⛔ This command does NOT run the toggle — you do

**Owner-ratified OQ1-redo (2026-08-03): arming or disarming the autonomy
posture is a HUMAN action.** The model rail does not flip the posture of
your next session; a human at the keyboard does.

**What actually enforces this, without overclaiming** (codex S292 r7 P1 —
the earlier wording said "denies every model-rail invocation", which is
false and measurably so):

- **Closed, both rails:** Edit/Write of the writer, the overlay and the
  marker (`.claude/settings.json` deny + `_CANONICAL_GUARDS`, which the
  Bash rail keys off). A tool write or a shell redirect cannot touch them.
- **Best-effort, not a boundary:** `check_bash_safety`
  (`_e4_check_posture_toggle_invocation`, PLAN-165 NF-08) blocks the
  invocation shapes a STATIC shell parse can recognise — and static
  parsing of bash is not complete. A RENAMED INTERPRETER
  (`./zz-interp .claude/scripts/night-mode.py on`) is measured to pass
  both the matcher and the script's self-path guard, because the script
  that ends up running IS the canonical one
  (`nf08-invocation-guard-NOTES.md` §7 residual 5).
- **Therefore:** a session with broad Bash permission can still arm the
  next session's posture. These controls raise the cost and make the
  honest path obvious; they do not make it impossible. The real perimeter
  is the CURRENT session's `defaultMode` + Bash allowlist.

Reading the script and its state (cat/grep/git) stays open.

So this command is a **teleprompter, not a driver**. Claude's whole job
here is to hand you one line to run yourself.

### How Claude must respond

1. Parse the first token of `$ARGUMENTS` as the subcommand. Accept
   case-insensitive `on` / `off` / `status`. Default (no argument) =
   `status`. Reject any other token with a short usage line — do not
   guess.
2. Print the matching command from the sections below, prefixed with
   `!` so the operator can run it on the human rail of this session
   (the `!` prefix executes in the terminal, not through the model's
   Bash tool). A terminal outside Claude Code works identically.
3. Print the one-line reminder that goes with that subcommand.
4. **Stop.** Do not call Bash. Do not "helpfully" verify by running the
   script. If the operator pastes the output back, read it and explain
   it — that is the whole loop.

## Next-session semantics (the whole point)

Settings are read at **session start**. The toggle therefore takes
effect on the **next** session, never the current one:

> Turn it on before you go to sleep → the overnight session starts in
> `acceptEdits` → turn it off in the morning.

The currently running governed session never changes posture under the
operator. If you need autonomy *now*, start a new session after `on`.

## `on` — arm night mode

Command for the operator to run:

```
! python3 .claude/scripts/night-mode.py on
```

Reminder to print with it:
`night-mode: takes effect on the NEXT session; run /night-mode off in the morning.`

The script (single writer — direct Edit/Write of the overlay is denied
by policy):

1. Merge-writes `permissions.defaultMode: "acceptEdits"` into
   `.claude/settings.local.json` (lock → atomic temp+`os.replace` →
   read-back; malformed existing JSON is fail-CLOSED: non-zero exit,
   file untouched).
2. Snapshots the prior value **create-only** into the marker so a
   double `on` can never make the weak posture the thing `off`
   "restores".
3. Writes the marker+snapshot file `.claude/state/night-mode.json`
   (gitignored via `.claude/state/`) with timestamp, hostname, and the
   mode it wrote.
4. Emits the `night_mode_toggled` audit action (HMAC-chained).

`on` twice is an idempotent no-op (exit 0). The script **refuses to run
when `CI` is set** — this is an operator/local-machine control only.

## `off` — disarm night mode

```
! python3 .claude/scripts/night-mode.py off
```

Restores the snapshotted `defaultMode` (or removes the key if none
existed), then removes the marker — reverse order of `on`, so a crash
in between is detectable, never silent. `off` twice is an idempotent
no-op (exit 0). Takes effect on the next session.

The marker is validated as a **whole document** before any of its fields
is acted on (version, `mode_written`, both booleans, `prev_value` against
a closed set derived from the harness's real `--permission-mode` enum,
and the `created_file`/`prev_present` consistency rule). Anything that a
healthy `on` could not have written is fail-CLOSED: exit 2, overlay
untouched, marker left in place as evidence. `bypassPermissions` and
`acceptEdits` are **never** restorable values.

### `off --discard-snapshot` — recovery from a refusal

```
! python3 .claude/scripts/night-mode.py off --discard-snapshot
```

The sanctioned exit from **every** fail-closed refusal above: it removes
the local `defaultMode` override **and** the marker *without* honoring
`prev_value`, printing exactly what it discarded. A refusal must never
leave the posture armed with no way to disarm it.

- It also disarms the **armed-without-marker** state, where plain `off`
  is a no-op (crash between the two writes, or a hand-deleted marker).
- It removes **one key, never a file** — an overlay carrying your other
  settings survives with `defaultMode` stripped.
- It is still fail-CLOSED on a malformed overlay (it must rewrite that
  file; repair the JSON by hand first).
- The next session resolves the project layer's ratified posture. If you
  wanted a specific prior value back, set it yourself after recovering —
  discard deliberately does not trust the snapshot it just threw away.

## `status` — report resolved posture

```
! python3 .claude/scripts/night-mode.py status
```

Prints:

- the **resolved** `permissions.defaultMode` per layer, via
  `_lib/effective_config.resolve_settings()` — the same resolver the
  tamper tripwires use, with layer provenance (which layer won:
  project vs local);
- the marker's age and contents (when armed, by whom/where);
- whether the marker and the resolved configuration **agree**.

Truth comes from the resolver, not the marker. The marker is
decoration.

`status` is read-only, and it is denied to the model rail anyway: the
invocation guard keys off the *script*, not the subcommand, because a
permissive carve-out driven by argv parsing is exactly the shape the
fail-closed doctrine rejects. Claude does have a model-rail read of the
same fact — **`/ceo-boot`'s advisory night-mode banner is
resolver-derived** and needs no subprocess. Use that when Claude needs
to *know* the posture; use `! … status` when you want the full report.

## Escape valve — real bypass is NOT this command

Night-mode tops out at `acceptEdits`. It never writes
`bypassPermissions` — that value trips the `settings_tamper_tripwires`
red in `/ceo-boot` by design, in any layer (PLAN-165 D1). If you truly
need a full-bypass session, the honest path is one-shot and explicit:

```
claude --permission-mode bypassPermissions   # one session, explicit, ephemeral
```

No persistent state, no tripwire collision, nothing for morning-you to
forget. Never route bypass through night-mode.

## Acceptance invariant — tracked tree stays clean

After any subcommand, `git status --porcelain` must be empty (AC-1).
Both files the toggle touches are gitignored:
`.claude/settings.local.json` and `.claude/state/night-mode.json`. If
the tree is dirty after a toggle, something wrote outside the contract
— stop and investigate before committing anything.

## Troubleshooting

- **"Claude refused to run it for me"** — by design (OQ1-redo). Run the
  `!` line yourself; paste the output back if you want it read.
- **"I ran `on` but the session still prompts"** — the toggle is
  next-session; the running session keeps its boot posture. Start a
  new session.
- **Marker and settings disagree** (e.g. crash between the two writes,
  or the overlay was hand-edited): `status` reports the disagreement
  instead of picking a side. If the marker is **gone** but the overlay is
  still armed, plain `off` is a no-op — run
  `off --discard-snapshot` to strip the override, then `on` again if you
  still want night mode. Never "fix" it by running `off` then `on` in
  that state: `on` would snapshot the armed value.
- **`off` refuses with "not a healthy night-mode marker"** — the marker
  is gitignored, unguarded state and something outside night-mode wrote
  it (a tampered `prev_value` such as `bypassPermissions` or
  `acceptEdits`, a non-boolean field, a wrong `version`, or an
  inconsistent `created_file`/`prev_present` pair). Validation is
  fail-CLOSED: the overlay is untouched and the marker is kept as
  evidence. Recover with:

  ```
  ! python3 .claude/scripts/night-mode.py off --discard-snapshot
  ```

  This removes the override and the marker without honoring the
  snapshot, and prints what it discarded. Keep a copy of the marker
  first if you want to investigate who wrote it — the PostToolUse audit
  log records tool writes to it.
- **Non-zero exit with a parse diagnostic** — your existing
  `settings.local.json` is malformed JSON. The script will not rewrite
  or "repair" it (fail-closed on input). Fix the JSON by hand, re-run.
- **Refused under CI** — expected: night-mode is operator/local only.
- **What actually applies?** — trust `status`'s layer provenance line;
  it uses the official resolver, not a re-implementation.

## Exit codes

- 0 — success (including idempotent no-ops)
- non-zero — refused (CI set), malformed input, tampered/invalid marker,
  or read-back mismatch; the settings file and marker are left in a
  diagnosable state. Any refusal is recoverable with
  `off --discard-snapshot` — no refusal can strand the posture armed.
