#!/usr/bin/env bash
# run-tlc.sh — download + verify + invoke TLA+ TLC against breaker.tla.
#
# PLAN-013 Phase D.2 helper. Stdlib + bash only (ADR-002 extended to
# /bin/sh tooling). Requires ``curl`` and ``java`` in PATH; fails with a
# clear message if either is missing.
#
# Toolchain pin:
#   tla2tools.jar 1.8.0 — SHA-256 verified against ``TLA_TOOLS_SHA256``.
#   Release page: https://github.com/tlaplus/tlaplus/releases/tag/v1.8.0
#   Download URL: https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar
#
# Usage:
#   bash docs/formal-verification/run-tlc.sh            # runs TLC
#   bash docs/formal-verification/run-tlc.sh download   # download jar only
#   bash docs/formal-verification/run-tlc.sh hash       # print log hashes
#   TLA_CACHE=/custom/path bash run-tlc.sh              # override cache dir
#
# Exit codes:
#   0  — TLC ran; no invariant/property violations.
#   1  — Prerequisite missing (curl or java).
#   2  — Jar SHA-256 mismatch (possible supply-chain tamper).
#   3  — TLC reported an error (invariant violation, stuttering, etc.).
#   4  — Other I/O failure.
#
# Outputs per-property SHA-256 log hashes on the last stdout line so
# ``properties-proved.md`` can capture them mechanically.

set -euo pipefail

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

TLA_VERSION="1.8.0"
TLA_TOOLS_SHA256="4c1d62e0f67c1d89f833619d7edad9d161e74a54b153f4f81dcef6043ea0d618"
TLA_TOOLS_URL="https://github.com/tlaplus/tlaplus/releases/download/v${TLA_VERSION}/tla2tools.jar"

CACHE_DIR="${TLA_CACHE:-/tmp/tla-cache}"
JAR_PATH="${CACHE_DIR}/tla2tools-${TLA_VERSION}.jar"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEC_DIR="${REPO_ROOT}/docs/formal-verification"
SPEC="${SPEC_DIR}/breaker.tla"
CONFIG="${SPEC_DIR}/breaker.cfg"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

log() {
  printf '[run-tlc] %s\n' "$*" >&2
}

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    log "ERROR: required tool '$tool' not found in PATH."
    log "       Install on macOS: brew install $tool"
    log "       Install on Debian/Ubuntu: apt-get install $tool"
    exit 1
  fi
}

sha256_file() {
  local f="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$f" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}'
  else
    log "ERROR: neither shasum nor sha256sum found."
    exit 1
  fi
}

# -----------------------------------------------------------------------------
# Download + verify jar
# -----------------------------------------------------------------------------

download_jar() {
  mkdir -p "${CACHE_DIR}"
  if [ -f "${JAR_PATH}" ]; then
    local existing_sha
    existing_sha="$(sha256_file "${JAR_PATH}")"
    if [ "${existing_sha}" = "${TLA_TOOLS_SHA256}" ]; then
      log "jar already present + sha-verified: ${JAR_PATH}"
      return 0
    fi
    log "existing jar SHA mismatch — redownloading"
    rm -f "${JAR_PATH}"
  fi

  log "downloading tla2tools.jar ${TLA_VERSION} from ${TLA_TOOLS_URL}"
  if ! curl -fsSL -o "${JAR_PATH}" "${TLA_TOOLS_URL}"; then
    log "ERROR: download failed (curl exited non-zero)."
    exit 4
  fi

  local got_sha
  got_sha="$(sha256_file "${JAR_PATH}")"
  if [ "${got_sha}" != "${TLA_TOOLS_SHA256}" ]; then
    log "ERROR: SHA-256 mismatch — jar rejected as potentially tampered."
    log "  expected: ${TLA_TOOLS_SHA256}"
    log "  got:      ${got_sha}"
    rm -f "${JAR_PATH}"
    exit 2
  fi
  log "jar sha-verified: ${got_sha}"
}

# -----------------------------------------------------------------------------
# Run TLC
# -----------------------------------------------------------------------------

run_tlc() {
  local log_file="${CACHE_DIR}/tlc-$(date -u +%Y%m%dT%H%M%SZ).log"
  log "running TLC against ${SPEC} (config: ${CONFIG})"
  log "log: ${log_file}"

  local tlc_exit=0
  java \
    -XX:+UseParallelGC \
    -Xmx2G \
    -cp "${JAR_PATH}" \
    tlc2.TLC \
      -workers auto \
      -config "${CONFIG}" \
      "${SPEC}" \
      >"${log_file}" 2>&1 || tlc_exit=$?

  if [ "${tlc_exit}" -ne 0 ]; then
    log "TLC exited non-zero (${tlc_exit}) — see ${log_file}"
    tail -40 "${log_file}" >&2 || true
    # Print hashes anyway so drift can be logged.
    emit_hashes "${log_file}"
    return 3
  fi

  log "TLC PASSED — no invariant / property violations."
  emit_hashes "${log_file}"
}

# -----------------------------------------------------------------------------
# Extract per-property log sections + SHA-256 each.
#
# TLC writes property failures inline; on success it writes a
# "Property X was checked." line. We grep the relevant sections and
# hash them so properties-proved.md can cite a stable fingerprint.
# -----------------------------------------------------------------------------

emit_hashes() {
  local log_file="$1"
  if [ ! -f "${log_file}" ]; then
    log "no log file to hash"
    return
  fi

  printf '\n=== TLC log hashes ===\n'
  for prop in TypeOK S1_OpenOnThreshold S2_HalfOpenSingleton S3_OpenEmitsAudit L1_EventuallyHeal; do
    local section_hash
    # Grab a window of 8 lines around each property mention. Empty
    # section → hash of empty string (known fingerprint).
    section_hash="$(grep -A 6 -B 1 "${prop}" "${log_file}" 2>/dev/null | sha256_stream)"
    printf '  %-30s  %s\n' "${prop}" "${section_hash}"
  done
  printf '=======================\n'
}

sha256_stream() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
  else
    sha256sum | awk '{print $1}'
  fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
  local mode="${1:-all}"
  require_tool curl

  case "${mode}" in
    download)
      download_jar
      ;;
    hash)
      require_tool java
      download_jar
      run_tlc
      ;;
    all|"")
      require_tool java
      download_jar
      run_tlc
      ;;
    *)
      log "unknown mode: ${mode} (expected: download | hash | all)"
      exit 1
      ;;
  esac
}

main "$@"
