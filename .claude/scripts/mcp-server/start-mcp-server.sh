#!/usr/bin/env bash
# start-mcp-server.sh — documented launch entry-point for the MCP server.
#
# PLAN-113 Phase B / Wave W6. Before this script the only way to run
# `.claude/scripts/mcp-server/server.py` was a bare `python server.py`
# invocation with no version guard and no documented entry-point. This
# launcher resolves a compatible Python interpreter (>=3.9, matching the
# framework floor in ADR-002) and execs the server.
#
# ## Why not route through _python-hook.sh?
#
# `.claude/hooks/_python-hook.sh` is a *hook invoker*: its first positional
# arg must be a hook-script name *relative to the hooks dir*, and it execs
# `$FOUND_PY $HOOKS_DIR/$1`. It cannot launch an arbitrary file outside the
# hooks dir. So this launcher reuses that shim's *interpreter-resolution
# intent* (newest `python3.x` >= 3.9, else `python3`) but execs server.py
# directly.
#
# ## Usage
#
#     .claude/scripts/mcp-server/start-mcp-server.sh [server args...]
#
# The server itself is configured via environment variables (see the
# module docstring in server.py): CEO_SOTA_DISABLE, CEO_MCP_TRANSPORT,
# CEO_MCP_HOST, CEO_MCP_PORT, CEO_MCP_ALLOW_PUBLIC, CLAUDE_PROJECT_DIR.
# Examples:
#
#     # default: HTTP transport on 127.0.0.1:9000
#     .claude/scripts/mcp-server/start-mcp-server.sh
#
#     # stdio transport
#     CEO_MCP_TRANSPORT=stdio .claude/scripts/mcp-server/start-mcp-server.sh
#
#     # disabled by kill-switch (exits 0)
#     CEO_SOTA_DISABLE=1 .claude/scripts/mcp-server/start-mcp-server.sh
#
# server.py currently takes no CLI arguments (config is env-driven), but
# any args passed to this launcher are forwarded to it via "$@" so a future
# argparse on the server keeps working without touching this script.
#
# Host-specific service definitions (systemd unit, launchd plist) are
# intentionally NOT shipped here — they belong in host provisioning, not
# in the portable framework.

set -euo pipefail

# Resolve this script's own directory (symlink-safe via pwd -P).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SERVER_PY="${SCRIPT_DIR}/server.py"

if [ ! -f "${SERVER_PY}" ]; then
  echo "[start-mcp-server] ERROR: server.py not found at ${SERVER_PY}" >&2
  exit 1
fi

# Minimum Python version (ADR-002 / _python-hook.sh floor).
MIN_MAJOR=3
MIN_MINOR=9

# Preferred interpreters, newest first; mirrors _python-hook.sh CANDIDATES.
CANDIDATES=(
  "python3.13"
  "python3.12"
  "python3.11"
  "python3.10"
  "python3.9"
  "python3"
)

version_ok() {
  # Args: MAJOR MINOR. Returns 0 if >= MIN, else 1.
  local major="$1" minor="$2"
  if [ "${major}" -lt "${MIN_MAJOR}" ]; then
    return 1
  fi
  if [ "${major}" -eq "${MIN_MAJOR}" ] && [ "${minor}" -lt "${MIN_MINOR}" ]; then
    return 1
  fi
  return 0
}

FOUND_PY=""
for candidate in "${CANDIDATES[@]}"; do
  if command -v "${candidate}" >/dev/null 2>&1; then
    read -r py_major py_minor < <(
      "${candidate}" -c 'import sys; print(sys.version_info[0], sys.version_info[1])' 2>/dev/null
    )
    if [ -n "${py_major:-}" ] && version_ok "${py_major}" "${py_minor}"; then
      FOUND_PY="${candidate}"
      break
    fi
  fi
done

if [ -z "${FOUND_PY}" ]; then
  cat >&2 <<EOF
[start-mcp-server] ERROR: No Python >= ${MIN_MAJOR}.${MIN_MINOR} found.
The MCP server requires Python ${MIN_MAJOR}.${MIN_MINOR}+ (ADR-002). Install one:

  macOS:   brew install python@3.12
  Ubuntu:  sudo apt install python3.12
  Fedora:  sudo dnf install python3.12

Then restart your shell so PATH picks up the new interpreter.
EOF
  exit 3
fi

# Exec replaces this shell so signals (SIGINT/SIGTERM) reach the server
# directly and the process tree stays flat.
exec "${FOUND_PY}" "${SERVER_PY}" "$@"
