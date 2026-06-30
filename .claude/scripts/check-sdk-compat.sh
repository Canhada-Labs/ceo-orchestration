#!/bin/bash
# check-sdk-compat — advisory CI gate for Claude Code CLI version pin.
#
# Reads claude --version (or $CLAUDE_VERSION env override) and compares
# against the tested-against / known-incompatible matrices in
# SPEC/v1/claude-sdk-compat.md.
#
# Behavior:
#   - claude binary not in PATH → silent skip exit 0
#   - listed-green version → exit 0 with INFO line
#   - unlisted version → exit 0 with WARN line (fail-open)
#   - listed-red version → exit 1 with ERROR line (fail-closed)
#   - malformed version output → exit 0 with WARN line (fail-open)
#
# CI usage (advisory):
#   bash .claude/scripts/check-sdk-compat.sh || true   # never block CI
#
# Adopter usage (strict):
#   bash .claude/scripts/check-sdk-compat.sh           # exit 1 stops build

set -uo pipefail

# Tested-against matrix (major.minor floors).
GREEN_VERSIONS=("1.0" "1.1" "1.2" "1.3" "1.4" "2.0" "2.1")

# Known-incompatible matrix.
RED_VERSIONS=()

# Resolve CLAUDE_VERSION (env override beats binary).
CLAUDE_VERSION="${CLAUDE_VERSION:-}"

if [ -z "$CLAUDE_VERSION" ]; then
  if ! command -v claude >/dev/null 2>&1; then
    echo "INFO: claude binary not in PATH; skipping SDK compat check."
    exit 0
  fi
  # Try to extract version from claude --version output. Anthropic CLI
  # output format may evolve; we accept both "claude/1.4.0" and "1.4.0"
  # patterns and tolerate stderr/stdout mixing.
  RAW_OUTPUT="$(claude --version 2>&1 || true)"
  CLAUDE_VERSION="$(printf '%s' "$RAW_OUTPUT" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
fi

if [ -z "$CLAUDE_VERSION" ]; then
  echo "WARN: could not parse Claude Code CLI version (output unrecognized)."
  echo "      treating as unlisted; CI advisory continues."
  exit 0
fi

# Extract major.minor for matrix comparison (strip patch).
MAJOR_MINOR="$(printf '%s' "$CLAUDE_VERSION" | cut -d. -f1-2)"

# Check known-incompatible first (red beats green).
for v in "${RED_VERSIONS[@]:-}"; do
  if [ -n "$v" ] && [ "$MAJOR_MINOR" = "$v" ]; then
    echo "ERROR: Claude Code CLI version $CLAUDE_VERSION is known-incompatible."
    echo "       See SPEC/v1/claude-sdk-compat.md §Known-incompatible matrix."
    echo "       Upgrade or downgrade to a listed-green version."
    exit 1
  fi
done

# Check listed-green.
for v in "${GREEN_VERSIONS[@]}"; do
  if [ "$MAJOR_MINOR" = "$v" ]; then
    echo "INFO: Claude Code CLI version $CLAUDE_VERSION (matrix $v) is listed-green."
    exit 0
  fi
done

# Unlisted — fail-open.
echo "WARN: Claude Code CLI version $CLAUDE_VERSION (matrix $MAJOR_MINOR) is unlisted."
echo "      Framework was not tested against this version; please verify behavior."
echo "      File an issue if you confirm it works — we'll update the matrix."
echo "      See SPEC/v1/claude-sdk-compat.md."
exit 0
