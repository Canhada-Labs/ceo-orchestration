# Codex pair-rail diff-review — S265 (2026-07-10) — 5 findings

Cross-model review of the uncommitted overlay diff (WF-154 + WF-155-A
output). These are the pair-rail catching REAL enforcement gaps — the
S254 silent-fail-open class the plans forbid. **BLOCKING: none of the
affected waves land until all five are fixed and the positive-control
replay re-run proves the fix.**

## P1 — PLAN-155 (the host-adapter linchpin; ENFORCED claims are false until fixed)

1. **Pass host event when emitting Codex decisions** —
   `wave-1/.claude/hooks/check_bash_safety.py:2808-2810` (+ the analogous
   canonical/plan/kernel emit paths). `codex.write_decision()` emits the
   Codex `hookSpecificOutput.permissionDecision` shape ONLY when it
   receives `event=` or `Decision.extra['hookEventName']`. These emit
   sites omit the event, so a block serializes as Claude-style top-level
   `{"decision":"block"}` — which on a Codex PreToolUse is foreign JSON =
   silent fail-open. **Every ENFORCED rail silently becomes ABSENT under
   codex.** This is THE linchpin defect.

2. **Parse Codex apply_patch content before plan checks** —
   `wave-1/.claude/hooks/check_plan_edit.py:851-854`. The adapter
   normalizes `apply_patch` to `Write`/`Edit` but carries the patch only
   in `tool_input['command']`/`apply_patch_ops` — never populates
   `content`/`old_string`/`new_string`. The plan-edit branch then sees
   `content == ''` and allows illegal PLAN status transitions.

3. **Check every Codex apply_patch path** —
   `wave-1/.claude/hooks/check_canonical_edit.py:1143-1150`. `apply_patch`
   can touch MULTIPLE files (adapter records them in
   `tool_input['apply_patch_paths']`), but the guard only checks
   `event.file_path` (unless MCP). A benign first op + a later op editing
   `.claude/hooks` is allowed — multi-file-patch canonical bypass.

## P2

4. **Distiller reads the always-on audit action, bypassing the observe
   kill-switch** — `PLAN-154 sent-f/.claude/scripts/distill-lessons.py:123-124`.
   `tool_lifecycle.record_post` emits `tool_call_lifecycle_recorded` to
   the audit log ALWAYS; the opt-in observe rail writes `.observe.jsonl`
   only when `CEO_LEARNING_OBSERVE=1`. The distiller keys on the
   always-on audit action → it can mint candidates from sessions that
   never opted in, violating the A12 zero-delta/kill-switch contract.
   **This is a PLAN-154 fix (constraint 9/A12).** Fix: distiller reads
   ONLY the opt-in `.observe.jsonl` store; with observe unset there must
   be zero candidate input (add a negative-control fixture: unset →
   distiller sees zero observations).

5. **Export CLAUDE_PROJECT_DIR in Codex hook commands** —
   `wave-2/templates/codex/hooks.json:8-9`. Commands set only
   `CEO_HOOK_ADAPTER`; Codex does not set `CLAUDE_PROJECT_DIR`. A session
   launched from a subdir makes hooks compute `repo_root` from the subdir
   → absolute paths elsewhere in the repo aren't recognized as protected.
   Fix: set `CLAUDE_PROJECT_DIR={{PROJECT_PATH}}` in every hook command
   (installer substitutes at render).

## Disposition

- P1 #1/#2/#3 + P2 #5: fixed in the PLAN-155 overlay by a targeted fix
  pass BEFORE WF-155-B; the Wave-1 subprocess positive-control replay is
  re-run and MUST now come back `permissionDecision: deny` for all three
  violation classes on the real codex wire (if the controls were green
  BEFORE this fix, they were vacuous — investigate and harden them, the
  S254 lesson).
- P2 #4: fixed in the PLAN-154 overlay (`distill-lessons.py` +
  negative-control fixture) before SENT-F is treated final; re-verify the
  scripts suite.
- ADR-161 §residuals gets a line: the host-adapter emit-shape correctness
  is proven by the subprocess positive-control, not by the adapter unit
  test alone (the unit test passed while the integration wire was wrong).

## Addendum — pre-ceremony diff review (2026-07-10, profiler)

A final `codex review --uncommitted` before the signing ceremony found 2
findings in `.claude/scripts/profile-opus-4-7.py` (PLAN-154 constraint-8
profiler — unguarded, in no sentinel scope). Both FIXED + verified (AST +
py_compile clean; profiler runs green rail-absent):

- **P2** — hook-latency gate could pass even when a profiled hook subprocess
  exits non-zero (the CompletedProcess was discarded → a crashing hook still
  recorded a small sample). Fix: capture returncode of seed AND timed runs →
  `entry_hook_failed` folds into `entry_passed` (+ `hook_failed` in output).
  Exactly the S254 vacuous-green class this profiler exists to prevent.
- **P3** — observe paired-row control (`on_paired >= iterations`) could pass
  with one unpaired warm row hiding behind the cold row's paired count
  (cold + 19 paired + 1 unpaired = 20). Fix: require `on_paired == on_rows`
  (every seeded row paired) AND `on_rows >= iterations`.
