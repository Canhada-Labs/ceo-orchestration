#!/usr/bin/env bash
# trading-readonly-escape-hatch.sh — PLAN-083 §7.5 Owner-signed kill-switch
# disable ceremony.
#
# Use ONLY when the framework's trading-readonly kill-switch has FAIL-CLOSED
# (missing `.claude/repo-profile.yaml`) and the Owner needs to re-enable
# trading actions in this repo.
#
# Contract:
#   - Requires an Owner-authored `escape-hatch-justification.md` at the
#     ceremony staging path (--justification-file FLAG or default).
#   - Requires GPG signing key configured (`user.signingkey` set in git).
#   - Produces a detached `.asc` signature of the justification file +
#     emits an audit row via the framework's `_lib.audit_emit.emit_generic`
#     with action `trading_kill_switch_disabled`.
#   - Idempotent: if the justification SHA-256 matches an existing
#     `.asc` signature next to it, the script re-emits the audit row
#     (forensic re-attestation) but does NOT re-sign.
#
# Exit codes:
#   0 — success (audit emitted; existing or new signature present)
#   1 — missing justification file
#   2 — justification file too short / malformed
#   3 — GPG signing failed
#   4 — audit emit error (audit row not written; rare; framework path)
#   5 — usage error

set -Eeuo pipefail
IFS=$'\n\t'

PROG="$(basename "$0")"

usage() {
  cat <<EOF
$PROG — Owner-signed trading kill-switch escape hatch (PLAN-083 §7.5)

Usage:
  $PROG [--justification-file PATH] [--profile-path PATH]
        [--audit-emit BOOL] [--repo-root PATH]

Defaults:
  --justification-file  \$REPO_ROOT/.claude/escape-hatch-justification.md
  --profile-path        \$REPO_ROOT/.claude/repo-profile.yaml
  --audit-emit          true
  --repo-root           \$CLAUDE_PROJECT_DIR or \$(git rev-parse --show-toplevel)

Required content in justification-file:
  - Header line beginning with "# Trading kill-switch escape hatch"
  - Justification paragraph >= 80 chars total (signed body)
  - Owner GPG key configured (\`git config user.signingkey\` set)

Exit codes:
  0 success | 1 missing | 2 malformed | 3 gpg-fail | 4 audit-fail | 5 usage
EOF
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

JUSTIFICATION_FILE=""
PROFILE_PATH=""
AUDIT_EMIT="true"
REPO_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --justification-file) JUSTIFICATION_FILE="$2"; shift 2;;
    --profile-path)       PROFILE_PATH="$2"; shift 2;;
    --audit-emit)         AUDIT_EMIT="$2"; shift 2;;
    --repo-root)          REPO_ROOT="$2"; shift 2;;
    -h|--help)            usage; exit 0;;
    *) echo "$PROG: error: unknown flag $1" >&2; usage; exit 5;;
  esac
done

# ---------------------------------------------------------------------------
# Resolve defaults
# ---------------------------------------------------------------------------

if [[ -z "$REPO_ROOT" ]]; then
  if [[ -n "${CLAUDE_PROJECT_DIR:-}" ]]; then
    REPO_ROOT="$CLAUDE_PROJECT_DIR"
  else
    REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
  fi
fi

if [[ -z "$JUSTIFICATION_FILE" ]]; then
  JUSTIFICATION_FILE="${REPO_ROOT}/.claude/escape-hatch-justification.md"
fi
if [[ -z "$PROFILE_PATH" ]]; then
  PROFILE_PATH="${REPO_ROOT}/.claude/repo-profile.yaml"
fi

# ---------------------------------------------------------------------------
# Validate justification file
# ---------------------------------------------------------------------------

if [[ ! -f "$JUSTIFICATION_FILE" ]]; then
  echo "$PROG: error: justification file missing: $JUSTIFICATION_FILE" >&2
  cat >&2 <<EOF
Author one with the required header + >=80-char body, then re-run.
Example template:

  # Trading kill-switch escape hatch

  Justification: <Owner-authored paragraph explaining why the
  fail-CLOSED state should be reverted; reference relevant
  ticket/incident; minimum 80 chars total>.
EOF
  exit 1
fi

JUST_BODY="$(cat "$JUSTIFICATION_FILE")"
JUST_LEN="${#JUST_BODY}"

if (( JUST_LEN < 80 )); then
  echo "$PROG: error: justification too short (got $JUST_LEN chars, need >=80)" >&2
  exit 2
fi

if ! grep -q '^# Trading kill-switch escape hatch' "$JUSTIFICATION_FILE"; then
  echo "$PROG: error: justification file missing required header" >&2
  echo "   expected line: '# Trading kill-switch escape hatch'" >&2
  exit 2
fi

# Compute SHA-256 of the justification body (forensic + idempotency key).
if command -v shasum >/dev/null 2>&1; then
  JUST_SHA="$(shasum -a 256 "$JUSTIFICATION_FILE" | awk '{print $1}')"
elif command -v sha256sum >/dev/null 2>&1; then
  JUST_SHA="$(sha256sum "$JUSTIFICATION_FILE" | awk '{print $1}')"
else
  echo "$PROG: error: neither shasum nor sha256sum available" >&2
  exit 2
fi

JUST_SHA_PREFIX="${JUST_SHA:0:16}"

# ---------------------------------------------------------------------------
# GPG signing (idempotent)
# ---------------------------------------------------------------------------

ASC_PATH="${JUSTIFICATION_FILE}.asc"

if [[ -f "$ASC_PATH" ]]; then
  # Verify the existing signature matches the current justification.
  if gpg --verify "$ASC_PATH" "$JUSTIFICATION_FILE" >/dev/null 2>&1; then
    echo "$PROG: existing signature verified; re-emitting audit row only"
    SIGNED_NEW="false"
  else
    echo "$PROG: existing $ASC_PATH does not verify; re-signing"
    rm -f "$ASC_PATH"
    SIGNED_NEW="true"
  fi
else
  SIGNED_NEW="true"
fi

if [[ "$SIGNED_NEW" == "true" ]]; then
  SIGNING_KEY="$(git config --get user.signingkey 2>/dev/null || echo "")"
  if [[ -z "$SIGNING_KEY" ]]; then
    echo "$PROG: error: git user.signingkey not configured" >&2
    echo "   run: git config --global user.signingkey <KEYID>" >&2
    exit 3
  fi
  if ! gpg --local-user "$SIGNING_KEY" \
        --output "$ASC_PATH" \
        --detach-sign --armor "$JUSTIFICATION_FILE" 2>/dev/null; then
    echo "$PROG: error: gpg detached-sign failed" >&2
    exit 3
  fi
  echo "$PROG: signed $ASC_PATH with key $SIGNING_KEY"
fi

# Get signer fingerprint (best-effort).
SIGNER_FPR=""
if command -v gpg >/dev/null 2>&1; then
  SIGNER_FPR="$(gpg --verify "$ASC_PATH" "$JUSTIFICATION_FILE" 2>&1 \
    | grep -oE '[0-9A-F]{40}' | head -1 || echo "")"
fi
SIGNER_FPR_PREFIX="${SIGNER_FPR:0:16}"

# ---------------------------------------------------------------------------
# Audit emit (best-effort; framework path)
# ---------------------------------------------------------------------------

AUDIT_OK="skip"
if [[ "$AUDIT_EMIT" == "true" ]]; then
  PYTHON_BIN="${PYTHON:-python3}"
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python"
  fi
  AUDIT_PY="${REPO_ROOT}/.claude/hooks/_lib/audit_emit.py"
  if [[ -f "$AUDIT_PY" ]] && command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    if env REPO_ROOT="$REPO_ROOT" PYTHONPATH="${REPO_ROOT}/.claude/hooks" "$PYTHON_BIN" - <<PY 2>/dev/null
import os, sys
sys.path.insert(0, os.path.join(os.environ.get("REPO_ROOT", "."), ".claude/hooks"))
try:
    from _lib import audit_emit
    audit_emit.emit_generic(
        "trading_kill_switch_disabled",
        justification_sha256_prefix="${JUST_SHA_PREFIX}",
        signer_fingerprint_prefix="${SIGNER_FPR_PREFIX}",
        signed_new=("${SIGNED_NEW}" == "true"),
        justification_length=int("${JUST_LEN}"),
    )
except Exception as exc:
    print(f"audit_emit failed: {exc}", file=sys.stderr)
    sys.exit(1)
PY
    then
      AUDIT_OK="ok"
    else
      AUDIT_OK="failed"
      echo "$PROG: warning: audit emit failed (forensic gap)" >&2
    fi
  else
    AUDIT_OK="unavailable"
    echo "$PROG: warning: audit_emit module unavailable; audit row skipped" >&2
  fi
fi

# ---------------------------------------------------------------------------
# Report + exit
# ---------------------------------------------------------------------------

cat <<EOF
$PROG: escape-hatch ceremony complete
  justification : $JUSTIFICATION_FILE
  signature     : $ASC_PATH (newly signed: $SIGNED_NEW)
  just-sha256   : $JUST_SHA_PREFIX...
  signer-fpr    : ${SIGNER_FPR_PREFIX:-unknown}...
  audit-emit    : $AUDIT_OK
  profile-path  : $PROFILE_PATH
EOF

# If audit emit was requested but failed, surface as exit 4 (forensic gap).
if [[ "$AUDIT_EMIT" == "true" && "$AUDIT_OK" == "failed" ]]; then
  exit 4
fi

exit 0
