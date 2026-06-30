#!/bin/bash
# check-contamination.sh — thin wrapper around check_contamination.py
#
# Sprint 3 Item E.2 (per debate consensus R-VP2): the Python
# implementation lives in `check_contamination.py`, sharing the
# file-walking + allowlist machinery with check-tier-boundaries via
# .claude/hooks/_lib/file_walker.py. This wrapper exists so the CI
# workflow step and any existing docs that invoke the .sh path keep
# working without change. Sprint 4+ may retire the wrapper.
#
# Exit codes are preserved:
#   0 — clean
#   1 — contamination found
#   2 — fatal error (git not available, etc.)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "FATAL: python3 not found" >&2
  exit 2
fi

exec python3 "$REPO_ROOT/.claude/scripts/check_contamination.py" "$@"
