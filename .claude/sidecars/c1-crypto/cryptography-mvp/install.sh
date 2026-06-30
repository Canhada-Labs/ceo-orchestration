#!/usr/bin/env bash
# C1 cryptography-mvp sidecar install (per ADR-126 §Part 4 install.script).
#
# Idempotent: re-running this script is a no-op when the pin is already
# satisfied. Verifies cryptography>=42.0,<44.0 + emits a pinned-hash record
# for adopter audit.

set -euo pipefail

SIDECAR_DIR="$(cd "$(dirname "$0")" && pwd)"
PIN_SPEC="cryptography>=42.0,<44.0"
RECORD_FILE="${SIDECAR_DIR}/installed-version.txt"

log() { printf '[c1-crypto/install] %s\n' "$*" >&2; }
die() { log "FATAL: $*"; exit 1; }

# Kill-switch — abort if explicitly disabled.
if [[ "${CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED:-0}" != "1" ]]; then
  die "kill-switch active: set CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=1 to install"
fi

log "installing pin: $PIN_SPEC"
if ! python3 -m pip install "$PIN_SPEC" --quiet; then
  die "pip install failed for $PIN_SPEC"
fi

# Verify import + record version
INSTALLED_VERSION="$(python3 -c "import cryptography; print(cryptography.__version__)" 2>/dev/null || true)"
if [[ -z "$INSTALLED_VERSION" ]]; then
  die "cryptography import failed after install"
fi

# Verify pin satisfied: 42.x or 43.x acceptable (>=42.0,<44.0)
MAJOR_MINOR="$(echo "$INSTALLED_VERSION" | awk -F. '{printf "%d.%d", $1, $2}')"
case "$MAJOR_MINOR" in
  42.*|43.*) ;;
  *) die "version $INSTALLED_VERSION outside pin >=42.0,<44.0" ;;
esac

log "installed: cryptography $INSTALLED_VERSION (pin $PIN_SPEC)"
printf 'cryptography==%s\nlast_install_date=%s\nkill_switch=CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED\n' \
  "$INSTALLED_VERSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$RECORD_FILE"

log "install record: $RECORD_FILE"
log "done."
