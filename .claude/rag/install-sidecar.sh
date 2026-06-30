#!/bin/bash
# .claude/rag/install-sidecar.sh — LightRAG sidecar installer (PLAN-041 Phase 3 / ADR-062)
#
# Owner-facing: `bash .claude/rag/install-sidecar.sh [--help|--status|--uninstall|--skip-model-verify]`
#
# Refuses to run if:
# - EUID == 0 (security P1-4)
# - .install.lock exists (idempotency per devops R-OPS1)
# - requirements.lock has PLACEHOLDER hashes (supply-chain P0-2)
# - models.manifest.json has PLACEHOLDER sha256 (unless --skip-model-verify
#   with CEO_RAG_UNVERIFIED_MODEL_ACK=I-ACCEPT-MODEL-INTEGRITY-RISK)
#
# Idempotent re-run: detects valid venv + skips reinstall. Corrupted
# venv: errors with recovery instructions.
#
# Cross-platform: bash 3.2 portable (macOS default). No mapfile, no
# associative arrays. Detects OS via `uname -s`.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RAG_DIR="$SCRIPT_DIR"
VENV_DIR="$RAG_DIR/venv"
LOCK_FILE="$RAG_DIR/.install.lock"
REQS_LOCK="$RAG_DIR/requirements.lock"
MODELS_MANIFEST="$RAG_DIR/models.manifest.json"
CONFIG_HOME="${CEO_RAG_HOME:-$HOME/.ceo-orchestration/rag}"

SKIP_MODEL_VERIFY=0
UNINSTALL=0
STATUS=0

_log() { printf '[install-sidecar] %s\n' "$*" >&2; }
_err() { printf '[install-sidecar] ERROR: %s\n' "$*" >&2; exit 1; }

_usage() {
    cat >&2 <<'USAGE'
Usage: install-sidecar.sh [OPTIONS]

Options:
  --help              Show this message and exit
  --status            Report current install state and exit
  --uninstall         Remove venv + config dir (keeps indexed data)
  --skip-model-verify Bypass model sha256 check (requires CEO_RAG_UNVERIFIED_MODEL_ACK)

Environment:
  CEO_RAG_HOME        Override ~/.ceo-orchestration/rag
  CEO_RAG_UNVERIFIED_MODEL_ACK=I-ACCEPT-MODEL-INTEGRITY-RISK
                      Two-factor ack to skip model sha256 verification

See docs/INSTALL-RAG.md for full install guide.
USAGE
}

# Parse args
while [ $# -gt 0 ]; do
    case "$1" in
        --help|-h) _usage; exit 0 ;;
        --status) STATUS=1; shift ;;
        --uninstall) UNINSTALL=1; shift ;;
        --skip-model-verify) SKIP_MODEL_VERIFY=1; shift ;;
        *) _err "Unknown option: $1 (see --help)" ;;
    esac
done

_check_not_root() {
    # security P1-4
    if [ "${EUID:-$(id -u)}" = "0" ]; then
        _err "Refuse to run as root. Sidecar runs as user UID only."
    fi
}

_detect_os() {
    case "$(uname -s)" in
        Darwin) echo "macos" ;;
        Linux)  echo "linux" ;;
        MINGW*|CYGWIN*|MSYS*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

_status() {
    _log "Install status:"
    _log "  RAG_DIR:        $RAG_DIR"
    _log "  VENV_DIR:       $VENV_DIR $([ -d "$VENV_DIR" ] && echo '(exists)' || echo '(missing)')"
    _log "  LOCK_FILE:      $LOCK_FILE $([ -f "$LOCK_FILE" ] && echo '(exists)' || echo '(missing)')"
    _log "  CONFIG_HOME:    $CONFIG_HOME $([ -d "$CONFIG_HOME" ] && echo '(exists)' || echo '(missing)')"
    _log "  OS:             $(_detect_os)"
    _log "  Python:         $(command -v python3.10 || command -v python3.11 || command -v python3.12 || echo '(not found)')"
    _log "  requirements.lock: $(grep -c '^\s*[a-z]' "$REQS_LOCK" 2>/dev/null || echo '0') pinned (0 = placeholder)"
}

_uninstall() {
    _log "Uninstalling sidecar..."
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
        _log "  removed venv"
    fi
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        _log "  removed install lock"
    fi
    _log "Done. Indexed data at $CONFIG_HOME preserved. Remove manually if desired."
}

_check_requirements_lock() {
    # security P0-2
    if [ ! -f "$REQS_LOCK" ]; then
        _err "$REQS_LOCK missing. Regenerate via pip-compile --generate-hashes."
    fi
    if grep -q "PLACEHOLDER" "$REQS_LOCK" || ! grep -q "^\s*[a-z].*==" "$REQS_LOCK"; then
        _err "$REQS_LOCK is a placeholder (no pinned packages). Regenerate per file header instructions + commit via branch-protected PR. Supply-chain P0-2 blocker."
    fi
}

_check_models_manifest() {
    # security P0-2 #3
    if [ "$SKIP_MODEL_VERIFY" = "1" ]; then
        if [ "${CEO_RAG_UNVERIFIED_MODEL_ACK:-}" != "I-ACCEPT-MODEL-INTEGRITY-RISK" ]; then
            _err "--skip-model-verify requires CEO_RAG_UNVERIFIED_MODEL_ACK=I-ACCEPT-MODEL-INTEGRITY-RISK (two-factor ack)."
        fi
        _log "WARN: model sha256 verification SKIPPED per explicit two-factor ack."
        return 0
    fi
    if [ ! -f "$MODELS_MANIFEST" ]; then
        _err "$MODELS_MANIFEST missing."
    fi
    if grep -q "PLACEHOLDER_SHA256" "$MODELS_MANIFEST"; then
        _err "$MODELS_MANIFEST has placeholder sha256. Regenerate via adopter mirror workflow + commit. Use --skip-model-verify + CEO_RAG_UNVERIFIED_MODEL_ACK if proceeding without verification is acceptable."
    fi
}

_check_venv_state() {
    # devops R-OPS1 — idempotency
    if [ -d "$VENV_DIR" ] && [ -f "$LOCK_FILE" ]; then
        _log "Install lock present. Venv appears installed."
        _log "  To reinstall: bash $0 --uninstall && bash $0"
        exit 0
    fi
    if [ -d "$VENV_DIR" ] && [ ! -f "$LOCK_FILE" ]; then
        _err "Venv directory exists but no install lock. Partial install detected. Run bash $0 --uninstall first."
    fi
}

_check_python() {
    for py in python3.12 python3.11 python3.10; do
        if command -v "$py" >/dev/null 2>&1; then
            echo "$py"
            return 0
        fi
    done
    _err "Python 3.10+ required. Install via pyenv / brew / apt."
}

_check_disk_space() {
    # LightRAG + chroma + torch ~ 2 GiB; plus embedding model ~ 400 MiB
    local required_mb=2500
    local available_mb
    case "$(_detect_os)" in
        macos)
            # df -m reports MiB on macOS
            available_mb=$(df -m "$HOME" | awk 'NR==2 {print $4}')
            ;;
        linux)
            available_mb=$(df -BM "$HOME" | awk 'NR==2 {gsub(/M/, "", $4); print $4}')
            ;;
        *)
            _log "WARN: disk space check skipped on this OS"
            return 0
            ;;
    esac
    if [ "$available_mb" -lt "$required_mb" ]; then
        _err "Insufficient disk space: ${available_mb} MiB available, need ${required_mb} MiB."
    fi
}

_check_ram() {
    # devops R-OPS7 + performance P1-003
    local required_gb=4
    local available_gb
    case "$(_detect_os)" in
        macos)
            # sysctl reports bytes
            local bytes
            bytes=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
            available_gb=$((bytes / 1073741824))
            ;;
        linux)
            available_gb=$(awk '/MemTotal/ {print int($2/1024/1024)}' /proc/meminfo 2>/dev/null || echo "0")
            ;;
        *)
            _log "WARN: RAM check skipped on this OS"
            return 0
            ;;
    esac
    if [ "$available_gb" -lt "$required_gb" ]; then
        _log "WARN: ${available_gb} GiB RAM detected; sidecar at 500k LoC ceiling is ~3 GiB. Consider smaller codebase or external RAG service."
    fi
}

_create_config_home() {
    mkdir -p "$CONFIG_HOME"
    chmod 0700 "$CONFIG_HOME"
    if [ ! -f "$CONFIG_HOME/config.json" ]; then
        cp "$RAG_DIR/sidecar-config.template.json" "$CONFIG_HOME/config.json"
        chmod 0600 "$CONFIG_HOME/config.json"
        _log "Created config at $CONFIG_HOME/config.json (0600)"
    fi
}

_install_venv() {
    # devops R-OPS1 — atomic via .install.lock written LAST
    local py
    py="$(_check_python)"
    _log "Using $py for venv"
    _log "Creating venv at $VENV_DIR"
    "$py" -m venv "$VENV_DIR"

    # security P0-2 — require hashes, no deps, disable cache, disable pip
    # self-update check (determinism), no build isolation
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    export PIP_NO_CACHE_DIR=1
    export TMPDIR="$CONFIG_HOME/tmp"
    mkdir -p "$TMPDIR" && chmod 0700 "$TMPDIR"

    _log "Installing pinned dependencies from $REQS_LOCK (--require-hashes --no-deps)"
    "$VENV_DIR/bin/python" -m pip install \
        --require-hashes \
        --no-deps \
        --upgrade-strategy only-if-needed \
        -r "$REQS_LOCK" \
        || _err "pip install failed. See stderr above."

    # Create install lock AFTER successful install
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$LOCK_FILE"
    chmod 0600 "$LOCK_FILE"
    _log "Install lock written: $LOCK_FILE"
}

_install_embedding_model() {
    # Placeholder: production script would download + verify SHA256.
    # This version emits instructions only.
    _log "Embedding model install is deferred to first `ceo-rag index` run."
    _log "Model manifest at $MODELS_MANIFEST will be checked at that time."
}

# ------------ main ------------

_check_not_root
if [ "$STATUS" = "1" ]; then
    _status
    exit 0
fi
if [ "$UNINSTALL" = "1" ]; then
    _uninstall
    exit 0
fi

_log "Install starting..."
_check_requirements_lock
_check_models_manifest
_check_venv_state
_check_disk_space
_check_ram
_create_config_home
_install_venv
_install_embedding_model

_log "Install complete. Next steps:"
_log "  1. ceo-rag start         # launch sidecar"
_log "  2. ceo-rag index         # build first index"
_log "  3. ceo-rag status        # verify health"
_log ""
_log "Adopter docs: docs/INSTALL-RAG.md"
