#!/bin/bash
# .claude/sidecars/c2-vector-memory/lightrag-mvp/install.sh — ADR-128 / PLAN-097 Wave A.3
#
# Owner-facing C2 vector-memory sidecar installer. Delegates to the
# PLAN-041 install-sidecar.sh script preserved at .claude/rag/ for
# backward compatibility — adopters with PLAN-041 installs do NOT need
# to migrate paths.
#
# Future PLAN-097-FOLLOWUP MAY move the implementation here; for now
# this is a thin wrapper that adds the C2 manifest-presence check
# before delegating.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
LEGACY_INSTALLER="$REPO_ROOT/.claude/rag/install-sidecar.sh"
MANIFEST="$SCRIPT_DIR/manifest.json"

_log() { printf '[c2-install] %s\n' "$*" >&2; }
_err() { printf '[c2-install] ERROR: %s\n' "$*" >&2; exit 1; }

if [ ! -f "$MANIFEST" ]; then
    _err "Missing manifest at $MANIFEST — C2 sidecar layout incomplete."
fi

if [ ! -f "$LEGACY_INSTALLER" ]; then
    _err "Legacy installer at $LEGACY_INSTALLER missing. PLAN-041 baseline absent."
fi

_log "Delegating to legacy installer at $LEGACY_INSTALLER"
_log "  (C2 manifest at $MANIFEST verified present)"
exec bash "$LEGACY_INSTALLER" "$@"
