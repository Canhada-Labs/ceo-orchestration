#!/usr/bin/env bash
# scan-injection-strict.sh — Fail-on-match wrapper around scan-injection.py.
#
# Context (PLAN-080 Phase 0b — M2-CDX-6):
#   scan-injection.py is advisory-only: it always exits 0, even when
#   prompt-injection patterns are detected. This wrapper converts that
#   advisory signal into an ERROR-tier gate suitable for use in
#   validate-governance.sh and CI pipelines.
#
# Usage:
#   scan-injection-strict.sh <file-or-directory>
#   CEO_SCAN_INJECTION_DEBUG=1 scan-injection-strict.sh <file-or-directory>
#
# Exit codes:
#   0 — no injection patterns matched (PASS)
#   1 — at least one match found (FAIL) or error condition (see below)
#
# Environment:
#   CEO_SCAN_INJECTION_DEBUG=1   Enable verbose output (match details to stderr)
#
# Canonical target: .claude/scripts/scan-injection-strict.sh
# This staging copy lives at: .claude/plans/PLAN-080/staging/phase-0b/scripts/

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Locate repo root by walking up from SCRIPT_DIR until we find CLAUDE.md.
# This makes the script relocatable: works from both the canonical install
# path (.claude/scripts/) and the staging path (plans/PLAN-NNN/staging/.../scripts/).
_find_repo_root() {
    local dir="$1"
    while [[ "${dir}" != "/" ]]; do
        if [[ -f "${dir}/CLAUDE.md" ]]; then
            printf '%s' "${dir}"
            return 0
        fi
        dir="$(dirname "${dir}")"
    done
    return 1
}

REPO_ROOT="$(_find_repo_root "${SCRIPT_DIR}")" || {
    printf 'ERROR: could not find repo root (no CLAUDE.md in any parent of %s)\n' "${SCRIPT_DIR}" >&2
    exit 1
}
SCAN_PY="${REPO_ROOT}/.claude/scripts/scan-injection.py"
DEBUG="${CEO_SCAN_INJECTION_DEBUG:-0}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_log() {
    printf '%s\n' "$*" >&2
}

_debug() {
    if [[ "${DEBUG}" == "1" ]]; then
        printf '[scan-injection-strict] %s\n' "$*" >&2
    fi
}

_usage() {
    printf 'Usage: %s <file-or-directory>\n' "$(basename "${BASH_SOURCE[0]}")" >&2
    printf '  CEO_SCAN_INJECTION_DEBUG=1 for verbose output\n' >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
if [[ $# -ne 1 ]]; then
    _usage
fi

TARGET="${1}"

# Empty / missing input
if [[ -z "${TARGET}" ]]; then
    _log "ERROR: empty target argument"
    _usage
fi

if [[ ! -e "${TARGET}" ]]; then
    _log "ERROR: path not found: ${TARGET}"
    _usage
fi

# Verify scan-injection.py exists
if [[ ! -f "${SCAN_PY}" ]]; then
    _log "ERROR: scan-injection.py not found at expected path:"
    _log "       ${SCAN_PY}"
    _log "Ensure the ceo-orchestration framework is properly installed."
    exit 1
fi

# ---------------------------------------------------------------------------
# Build file list (single file or directory)
# ---------------------------------------------------------------------------
declare -a FILES=()
if [[ -f "${TARGET}" ]]; then
    FILES=("${TARGET}")
elif [[ -d "${TARGET}" ]]; then
    while IFS= read -r -d '' f; do
        FILES+=("${f}")
    done < <(find "${TARGET}" -type f \( -name "*.yaml" -o -name "*.yml" -o -name "*.md" \) -print0)
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
    _debug "No scannable files found under ${TARGET} — PASS (empty input)"
    exit 0
fi

# ---------------------------------------------------------------------------
# Scan each file
# ---------------------------------------------------------------------------
OVERALL_FAIL=0

for f in "${FILES[@]}"; do
    _debug "Scanning: ${f}"

    # Run scan-injection.py with JSON output; capture stdout
    JSON_OUT="$(python3 "${SCAN_PY}" --json "${f}" 2>/dev/null)" || {
        _log "ERROR: scan-injection.py failed for ${f}"
        exit 1
    }

    # Extract matched field using jq if available, else pure-bash substring
    MATCHED="false"
    if command -v jq >/dev/null 2>&1; then
        MATCHED="$(printf '%s' "${JSON_OUT}" | jq -r '.matched')"
    else
        # Pure-bash extraction: look for "matched":true (with optional spaces)
        if printf '%s' "${JSON_OUT}" | grep -q '"matched"[[:space:]]*:[[:space:]]*true'; then
            MATCHED="true"
        fi
    fi

    if [[ "${MATCHED}" == "true" ]]; then
        _log "FAIL: injection pattern detected in ${f}"
        if [[ "${DEBUG}" == "1" ]]; then
            printf '%s\n' "${JSON_OUT}" | (command -v jq >/dev/null 2>&1 && jq '.' || cat) >&2
        fi
        OVERALL_FAIL=1
    else
        _debug "PASS: ${f}"
    fi
done

# ---------------------------------------------------------------------------
# Final verdict
# ---------------------------------------------------------------------------
if [[ "${OVERALL_FAIL}" -eq 1 ]]; then
    _log "scan-injection-strict: FAIL — injection patterns found. See details above."
    exit 1
fi

_debug "scan-injection-strict: PASS — no injection patterns detected."
exit 0
