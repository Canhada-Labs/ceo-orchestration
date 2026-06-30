#!/usr/bin/env bash
# C5 hypothesis sidecar install (per ADR-126 §Part 4 install.script + ADR-131).
#
# Idempotent: re-running this script is a no-op when the pins are already
# satisfied. Pins are EXACT and MUST match manifest.json dependencies.python
# byte-for-byte (ADR-131 §C5.2). Emits a pinned-version record for adopter audit.
#
# Governance (manifest.json / ADR-131): default_state="on", Tier A — the sidecar
# is enabled unless CEO_SIDECAR_HYPOTHESIS_ENABLED=0 explicitly disables it.

set -euo pipefail

SIDECAR_DIR="$(cd "$(dirname "$0")" && pwd)"
# EXACT pins (ADR-131 §C5.2 — no >=/^/~=; must equal manifest.json byte-for-byte).
HYPOTHESIS_PIN="hypothesis==6.100.0"
JSONSCHEMA_PIN="jsonschema==4.21.1"
RECORD_FILE="${SIDECAR_DIR}/installed-version.txt"

log() { printf '[c5-hypothesis/install] %s\n' "$*" >&2; }
die() { log "FATAL: $*"; exit 1; }

# Kill-switch — default ON (manifest.json default_state="on"). Only an explicit
# CEO_SIDECAR_HYPOTHESIS_ENABLED=0 disables; unset OR any other value = enabled.
if [[ "${CEO_SIDECAR_HYPOTHESIS_ENABLED:-1}" == "0" ]]; then
  log "kill-switch: CEO_SIDECAR_HYPOTHESIS_ENABLED=0 — install skipped (exit 0)"
  exit 0
fi

log "installing exact pins: $HYPOTHESIS_PIN $JSONSCHEMA_PIN"
if ! python3 -m pip install "$HYPOTHESIS_PIN" "$JSONSCHEMA_PIN" --quiet; then
  die "pip install failed"
fi

# Verify imports
HYP_VERSION="$(python3 -c "import hypothesis; print(hypothesis.__version__)" 2>/dev/null || true)"
JS_VERSION="$(python3 -c "import jsonschema; print(jsonschema.__version__)" 2>/dev/null || true)"

[[ -n "$HYP_VERSION" ]] || die "hypothesis import failed after install"
[[ -n "$JS_VERSION" ]] || die "jsonschema import failed after install"

log "installed: hypothesis $HYP_VERSION, jsonschema $JS_VERSION"
printf 'hypothesis==%s\njsonschema==%s\nlast_install_date=%s\nkill_switch=CEO_SIDECAR_HYPOTHESIS_ENABLED (default on; =0 disables)\n' \
  "$HYP_VERSION" "$JS_VERSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$RECORD_FILE"

log "install record: $RECORD_FILE"
log "done."
