# shellcheck shell=bash
# scripts/_hash_lib.sh — portable SHA-256 helpers (PLAN-138 Wave C / ADR-155)
#
# Sourced (not executed) by scripts/install.sh and scripts/upgrade.sh. Extracts
# the shasum||sha256sum probe that previously lived inline in install.sh's
# _self_sha_compute (lines 228-243) so the install/upgrade baseline-manifest
# engine has ONE portable hasher.
#
# Two surfaces, deliberately distinct:
#   _hash_file  <path>   -> sha256 of FILE CONTENT (the manifest baseline + dst/src classification)
#   _hash_stdin          -> sha256 of a STRING/STREAM read from stdin
#                           (upgrade.sh:209 hashes a PATH STRING, not a file —
#                            a content hash there would be wrong)
#
# Contract:
#   * bash 3.2-safe (macOS /bin/bash 3.2.57): no associative arrays, no mapfile,
#     no process-substitution dependency, no GNU-only flags.
#   * Portable across macOS (shasum) and Linux (sha256sum). shasum is preferred
#     (present on macOS by default); sha256sum is the Linux fallback.
#   * Each function prints exactly the 64-hex digest on stdout (no filename
#     column) and returns 0 on success; returns 1 if neither hasher exists or
#     (for _hash_file) the path is unreadable. Never prints a partial/empty
#     digest on success — callers under `set -euo pipefail` rely on this.
#
# This file is CANONICAL (added to _CANONICAL_GUARDS in check_canonical_edit.py):
# it is sourced by the GPG-gated install/upgrade and must not be a soft
# underbelly for tampering with the integrity engine.

# Resolve the available hasher ONCE and echo the command words. Probe order
# matches install.sh _self_sha_compute (shasum first, sha256sum fallback).
# Prints the hasher invocation (e.g. "shasum -a 256") on stdout; returns 1 if
# neither is on PATH.
_hash_resolver() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s\n' "shasum -a 256"
    return 0
  elif command -v sha256sum >/dev/null 2>&1; then
    printf '%s\n' "sha256sum"
    return 0
  fi
  return 1
}

# _hash_file <path> — SHA-256 of the file's CONTENT. Prints 64-hex on stdout.
# Returns 1 if no hasher is available or the path is not a readable file.
_hash_file() {
  _hf_path="$1"
  if [ -z "${_hf_path:-}" ] || [ ! -f "$_hf_path" ] || [ ! -r "$_hf_path" ]; then
    return 1
  fi
  _hf_hasher="$( _hash_resolver )" || return 1
  # Feed the file on stdin so neither hasher prints the filename column; then
  # take the first whitespace-delimited field (the digest). Guard against an
  # empty digest by checking the length downstream is the caller's job, but we
  # never emit a success line without a digest because a hasher failure makes
  # the pipeline's last stage (awk) print nothing AND we propagate non-zero.
  _hf_digest="$( eval "$_hf_hasher" < "$_hf_path" | awk '{print $1; exit}' )"
  if [ -z "${_hf_digest:-}" ]; then
    return 1
  fi
  printf '%s\n' "$_hf_digest"
}

# _hash_stdin — SHA-256 of whatever is on stdin (a string or a stream). Prints
# 64-hex on stdout. Use for hashing a PATH STRING or other non-file input, e.g.
#   hash="$( printf '%s' "$repo_root" | _hash_stdin )"
# Returns 1 if no hasher is available or the resulting digest is empty.
_hash_stdin() {
  _hs_hasher="$( _hash_resolver )" || return 1
  _hs_digest="$( eval "$_hs_hasher" | awk '{print $1; exit}' )"
  if [ -z "${_hs_digest:-}" ]; then
    return 1
  fi
  printf '%s\n' "$_hs_digest"
}

# _hash_verify_c <checksum-file> — portable `shasum -a 256 -c` / `sha256sum -c`.
# Verifies the "<hex>  <path>" lines in <checksum-file> against the CURRENT
# working directory (caller cd's first, matching the legacy call sites).
# Returns 0 if all listed files match, 1 otherwise (incl. no hasher). Output is
# suppressed by the caller; this just carries the exit status.
_hash_verify_c() {
  _hv_file="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c "$_hv_file"
    return $?
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "$_hv_file"
    return $?
  fi
  return 1
}
