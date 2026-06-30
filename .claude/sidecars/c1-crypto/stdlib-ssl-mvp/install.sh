#!/usr/bin/env bash
# PLAN-099 C1 crypto sidecar (stdlib-ssl-mvp) install script.
#
# Per ADR-129 §Part 6 SBOM: this sidecar is stdlib-only. There are NO
# Python packages to install — `ssl` / `hmac` / `hashlib` / `secrets` /
# `http.server` / `http.client` / `ipaddress` all ship with CPython.
#
# The one system dependency is `gpg` (consumed by `_lib/gpg_verify.py`
# for Owner-GPG sentinel verification per ADR-135 §Part 4). We verify
# it's available + emit a structured pre-flight breadcrumb. If gpg is
# missing the federation server will fail-CLOSED on start; this script
# just surfaces the missing dependency earlier.
#
# Idempotent — re-runs report "already configured" and exit 0.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
cd "$REPO"

_log() { printf '[c1-crypto/stdlib-ssl-mvp install] %s\n' "$*" >&2; }
_warn() { printf '[c1-crypto/stdlib-ssl-mvp install] WARN: %s\n' "$*" >&2; }

_log "stdlib-only sidecar — no Python deps to install"

if ! command -v gpg >/dev/null 2>&1; then
    _warn "gpg binary NOT in PATH"
    _warn "federation server will fail-CLOSED at start with"
    _warn "  federation_enable_sentinel_invalid:gpg_missing"
    _warn "install gpg via your package manager (brew install gnupg / apt install gnupg)"
    exit 0  # advisory — not a hard failure at install time
fi

GPG_VERSION="$(gpg --version 2>&1 | head -1 || true)"
_log "gpg available: $GPG_VERSION"

# Verify the Owner sentinel registry is reachable.
REGISTRY="$REPO/.claude/security/sentinel-signers-registry.yaml"
if [[ -f "$REGISTRY" ]]; then
    _log "sentinel-signers-registry present: $REGISTRY"
else
    _warn "sentinel-signers-registry MISSING at $REGISTRY"
    _warn "Stage-2 validity check (ADR-121) will fail-CLOSED"
fi

# Verify the federation data dir exists (kernel-path-guarded; only Owner
# can populate it via the install ceremony).
FED_DIR="$REPO/.claude/data/federation"
if [[ -d "$FED_DIR" ]]; then
    _log "federation data dir present: $FED_DIR"
else
    _warn "federation data dir MISSING — federation cannot start without it"
fi

_log "C1 crypto sidecar install complete"
exit 0
