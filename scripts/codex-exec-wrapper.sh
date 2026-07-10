#!/usr/bin/env bash
# codex-exec-wrapper.sh — headless `codex exec` audit-chain bracket.
#
# PLAN-155 Wave 4-C (SENT-CX-B / ADR-161). Unguarded surface (scripts/).
#
# ## What it does
#
# Wraps a headless `codex exec <args...>` invocation and brackets it with two
# audit-chain entries so the run lands in the HMAC chain even when Codex's own
# `.codex/hooks.json` lifecycle hooks are NOT firing:
#
#   1. BEFORE the run: pipes a synthetic SessionStart codex envelope to
#      audit_log.py (CEO_HOOK_ADAPTER=codex) -> a `session_start` boot row.
#   2. AFTER the run: pipes a synthetic Stop codex envelope to audit_log.py
#      (CEO_HOOK_ADAPTER=codex, CEO_CODEX_TURN_SOURCE=wrapper) -> a
#      `codex_turn_ended` backstop row with source="wrapper".
#
# Both bracket rows share one wrapper-generated session id, so a run whose
# in-session hooks never fired still produces a coherent 2-row chain segment.
#
# ## Why it exists
#
# Under codex-cli 0.139 an untrusted or unwired hook is a SILENT no-op — no
# execution, no stderr, exit 0 (PLAN-155 Wave 1 `trust-keying-A6.md`). A
# `codex exec` run in that state would leave ZERO trace in the audit chain,
# indistinguishable from "no activity". This wrapper guarantees a turn-level
# bracket regardless of hook trust state.
#
# ## Residuals (named — do not oversell)
#
# - **Wrapper-bypass residual.** This only brackets runs invoked THROUGH the
#   wrapper. A `codex exec` run started directly (not via this script) AND
#   without trusted `.codex` hooks lands NOTHING — absence of rows is not
#   evidence of absence of activity (the same completeness bound as the
#   degradation page). Backstops: the installer's post-install arming check
#   (Wave 5, debate A7), CODEOWNERS/CI at push.
# - **Per-tool completeness residual.** The wrapper sees only session start +
#   end, NOT individual tool calls. Per-tool `codex_tool_recorded` rows come
#   from Codex's PostToolUse `*` hook (when trusted); the wrapper does not and
#   cannot synthesize them. Per-tool completeness stays bounded by Codex's
#   partial shell interception.
# - **Bracket-vs-in-session session-id skew.** When Codex's own hooks DO fire,
#   their rows carry Codex's real session_id; the wrapper brackets carry the
#   wrapper's generated id. Both are valid chain entries (the HMAC chain links
#   by prev_hmac, not by session_id); a reader correlates by wall-clock order.
#
# ## Usage
#
#   scripts/codex-exec-wrapper.sh --sandbox workspace-write "do the thing"
#
# All arguments are forwarded verbatim to `codex exec`. The wrapper exits with
# codex's own exit code. Fail-open: a failed bracket append NEVER changes the
# codex exit code (audit is observability, not a gate).
#
# stdlib only (bash + python3 for JSON/uuid). shellcheck -S warning clean.

set -u

# --- locate the framework root (this script lives in <root>/scripts/) --------
_SELF="${BASH_SOURCE[0]}"
# Resolve one level of symlink without relying on GNU readlink -f (macOS ships
# BSD readlink). Best-effort; falls back to the literal path.
if [ -L "$_SELF" ]; then
  _link="$(readlink "$_SELF" 2>/dev/null || true)"
  if [ -n "$_link" ]; then
    case "$_link" in
      /*) _SELF="$_link" ;;
      *)  _SELF="$(dirname "$_SELF")/$_link" ;;
    esac
  fi
fi
_SCRIPT_DIR="$(cd "$(dirname "$_SELF")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$_SCRIPT_DIR/.." && pwd)}"

HOOK_SHIM="$ROOT/.claude/hooks/_python-hook.sh"
AUDIT_HOOK="audit_log.py"

# Pick a python3 for the tiny envelope generator (the hook itself is resolved
# by the shim). Fall back gracefully.
PY="python3"
command -v "$PY" >/dev/null 2>&1 || PY="python"

# Generate a wrapper-scoped session id (uuid4). If python is somehow absent,
# degrade to an epoch-nanoseconds id so bracketing still emits.
if command -v "$PY" >/dev/null 2>&1; then
  WRAP_SID="$("$PY" -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || true)"
fi
[ -n "${WRAP_SID:-}" ] || WRAP_SID="wrapper-$(date +%s)-$$"

# --- helper: feed a synthetic codex host envelope to audit_log.py ------------
# $1 = hook_event_name (SessionStart|Stop). Extra JSON fields via stdin builder.
_emit_bracket() {
  event_name="$1"
  turn_source="${2:-}"
  # Build the envelope with python for correct JSON escaping. Emits {} + exit 0
  # to stdin of the audit hook. The hook reads the codex host wire (top-level
  # hook_event_name) and appends via _lib.audit_emit.
  envelope="$(
    "$PY" - "$event_name" "$WRAP_SID" "$ROOT" <<'PYEOF'
import json, sys
event_name, sid, cwd = sys.argv[1], sys.argv[2], sys.argv[3]
d = {
    "session_id": sid,
    "cwd": cwd,
    "hook_event_name": event_name,
    "permission_mode": "bypassPermissions",
}
if event_name == "SessionStart":
    d["source"] = "startup"
elif event_name == "Stop":
    d["stop_hook_active"] = False
    d["last_assistant_message"] = ""
print(json.dumps(d))
PYEOF
  )" || return 0

  # Invoke the audit hook via the shim if present, else direct python3. Any
  # failure is swallowed (fail-open): the bracket must never break the run.
  if [ -f "$HOOK_SHIM" ]; then
    printf '%s' "$envelope" | \
      env CEO_HOOK_ADAPTER=codex \
          CLAUDE_PROJECT_DIR="$ROOT" \
          ${turn_source:+CEO_CODEX_TURN_SOURCE="$turn_source"} \
          bash "$HOOK_SHIM" "$AUDIT_HOOK" >/dev/null 2>&1 || true
  else
    printf '%s' "$envelope" | \
      env CEO_HOOK_ADAPTER=codex \
          CLAUDE_PROJECT_DIR="$ROOT" \
          ${turn_source:+CEO_CODEX_TURN_SOURCE="$turn_source"} \
          "$PY" "$ROOT/.claude/hooks/$AUDIT_HOOK" >/dev/null 2>&1 || true
  fi
}

# --- bracket + run -----------------------------------------------------------
_emit_bracket "SessionStart" ""

if command -v codex >/dev/null 2>&1; then
  codex exec "$@"
  rc=$?
else
  echo "codex-exec-wrapper: 'codex' not found on PATH" >&2
  rc=127
fi

_emit_bracket "Stop" "wrapper"

exit "$rc"
