#!/usr/bin/env bash
# log-friction.sh — append a structured friction entry to the PLAN-015
#                   frictions markdown log during the 14-day adopter-1
#                   validation window (and any future adopter window).
#
# Phase 0.4 of PLAN-015 (Internal Validation — adopter-1). Without this
# helper the Owner would hand-edit frictions.md mid-install, which breaks
# the triage script in Phase 3 (it assumes a strict markdown table shape
# and a validated severity/category enum).
#
# ## Usage
#
#   bash .claude/scripts/log-friction.sh \
#     --severity P0 \
#     --category install \
#     --message "install.sh failed on macOS 14.5 ARM64 — homebrew jq missing"
#
# ## Flags
#
#   --severity   Required. One of: P0, P1, P2, P3.
#                P0 = blocker, P1 = serious, P2 = nice-to-have, P3 = cosmetic.
#   --category   Required. One of: install, hook, spawn, docs, ux,
#                governance, performance, other.
#   --message    Required. Free text, 3..500 chars, no embedded newlines.
#   --file PATH  Optional. Override output file. Default:
#                $PWD/.claude/plans/PLAN-015/frictions.md. Relative paths
#                are resolved from $PWD (not from the script's directory)
#                so the Owner can run this from any repo checkout.
#   --help, -h   Print this usage and exit 0.
#
# ## Exit codes
#
#   0 — success (row appended, confirmation printed to stdout)
#   1 — user error (missing flag, bad enum, bad length, embedded newline)
#   2 — infra error (cannot create parent directory, cannot write file)
#
# ## Portability notes
#
# - Bash >= 3.2 (macOS default). No `mapfile`, no `declare -A` required.
# - Uses POSIX `date -u +%Y-%m-%dT%H:%M:%SZ` (works on BSD date + GNU date).
# - Uses `printf` everywhere; never `echo -e`.
# - `set -euo pipefail` to fail fast on undefined vars + pipe errors.

set -euo pipefail

SCRIPT_NAME="log-friction.sh"

VALID_SEVERITIES=(P0 P1 P2 P3)
VALID_CATEGORIES=(install hook spawn docs ux governance performance other)

MIN_MSG_LEN=3
MAX_MSG_LEN=500

usage() {
  cat <<'EOF'
log-friction.sh — append a friction entry to frictions.md

Usage:
  bash .claude/scripts/log-friction.sh \
    --severity <P0|P1|P2|P3> \
    --category <install|hook|spawn|docs|ux|governance|performance|other> \
    --message "<3..500 chars, no newlines>" \
    [--file PATH]

Flags:
  --severity   Required. Severity level (P0..P3).
               P0=blocker, P1=serious, P2=nice-to-have, P3=cosmetic.
  --category   Required. One of:
               install, hook, spawn, docs, ux, governance, performance, other.
  --message    Required. Free text, 3..500 chars, no embedded newlines.
               Pipe chars (|) are escaped automatically in the markdown row.
  --file PATH  Optional. Override output file. Default:
               $PWD/.claude/plans/PLAN-015/frictions.md
  --help, -h   Print this usage and exit 0.

Exit codes:
  0 — success
  1 — user error (missing flag, bad enum, bad length, embedded newline)
  2 — infra error (cannot create parent dir, cannot write file)

Example:
  bash .claude/scripts/log-friction.sh \
    --severity P0 \
    --category install \
    --message "install.sh failed on macOS 14.5 ARM64 — jq missing"
EOF
}

die_user() {
  # Exit 1 with a consistent "[script] error: ..." stderr prefix.
  printf '[%s] error: %s\n' "$SCRIPT_NAME" "$1" >&2
  if [ "${2:-}" = "with-usage" ]; then
    printf '\n' >&2
    usage >&2
  fi
  exit 1
}

die_infra() {
  printf '[%s] infra error: %s\n' "$SCRIPT_NAME" "$1" >&2
  exit 2
}

in_list() {
  # Usage: in_list <needle> <item1> <item2> ...
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    if [ "$item" = "$needle" ]; then
      return 0
    fi
  done
  return 1
}

# ----- parse args -----

severity=""
category=""
message=""
out_file=""
message_set=0

while [ $# -gt 0 ]; do
  case "$1" in
    --severity)
      [ $# -ge 2 ] || die_user "--severity requires a value" "with-usage"
      severity="$2"
      shift 2
      ;;
    --severity=*)
      severity="${1#--severity=}"
      shift 1
      ;;
    --category)
      [ $# -ge 2 ] || die_user "--category requires a value" "with-usage"
      category="$2"
      shift 2
      ;;
    --category=*)
      category="${1#--category=}"
      shift 1
      ;;
    --message)
      [ $# -ge 2 ] || die_user "--message requires a value" "with-usage"
      message="$2"
      message_set=1
      shift 2
      ;;
    --message=*)
      message="${1#--message=}"
      message_set=1
      shift 1
      ;;
    --file)
      [ $# -ge 2 ] || die_user "--file requires a value" "with-usage"
      out_file="$2"
      shift 2
      ;;
    --file=*)
      out_file="${1#--file=}"
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      die_user "unknown argument: $1" "with-usage"
      ;;
  esac
done

# ----- validate args -----

if [ -z "$severity" ]; then
  die_user "--severity is required" "with-usage"
fi
if ! in_list "$severity" "${VALID_SEVERITIES[@]}"; then
  die_user "invalid --severity '$severity' (expected one of: ${VALID_SEVERITIES[*]})"
fi

if [ -z "$category" ]; then
  die_user "--category is required" "with-usage"
fi
if ! in_list "$category" "${VALID_CATEGORIES[@]}"; then
  die_user "invalid --category '$category' (expected one of: ${VALID_CATEGORIES[*]})"
fi

if [ "$message_set" -eq 0 ]; then
  die_user "--message is required" "with-usage"
fi

# Reject embedded newlines BEFORE length check (clearer error).
# `case` with glob handles this portably; `$'\n'` is a bash literal newline.
case "$message" in
  *$'\n'*)
    die_user "--message must not contain embedded newlines (split into separate invocations)"
    ;;
esac
# Also reject carriage returns for symmetry (Windows pasting edge case).
case "$message" in
  *$'\r'*)
    die_user "--message must not contain embedded carriage returns"
    ;;
esac

msg_len=${#message}
if [ "$msg_len" -lt "$MIN_MSG_LEN" ]; then
  die_user "--message too short: $msg_len chars (minimum $MIN_MSG_LEN)"
fi
if [ "$msg_len" -gt "$MAX_MSG_LEN" ]; then
  die_user "--message too long: $msg_len chars (maximum $MAX_MSG_LEN)"
fi

# ----- resolve output file -----

if [ -z "$out_file" ]; then
  out_file="$PWD/.claude/plans/PLAN-015/frictions.md"
fi

# If relative, anchor to $PWD (consistent with default).
case "$out_file" in
  /*) : ;;
  *)  out_file="$PWD/$out_file" ;;
esac

out_dir="$(dirname "$out_file")"
if [ ! -d "$out_dir" ]; then
  if ! mkdir -p "$out_dir" 2>/dev/null; then
    die_infra "cannot create parent directory: $out_dir"
  fi
fi

# ----- compute timestamp -----

# POSIX-compatible UTC ISO-8601 (second precision). Works on BSD date too.
timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ----- prepare escaped message for markdown cell -----

# Escape pipe chars so they don't break the markdown table column boundary.
# We only escape in the written row, never in the stdout confirmation.
escaped_message="${message//|/\\|}"

# ----- write header if file missing -----

if [ ! -f "$out_file" ]; then
  if ! {
    cat >"$out_file" <<'HEADER'
# Frictions log — PLAN-015

> Appended by `.claude/scripts/log-friction.sh`. Do not hand-edit rows
> — the triage script in Phase 3 assumes table shape. Add narrative
> comments below the table if needed.

| Timestamp (UTC) | Severity | Category | Message |
|-----------------|----------|----------|---------|
HEADER
  } 2>/dev/null; then
    die_infra "cannot write header to: $out_file"
  fi
fi

# ----- append row -----

# `>>` append of a single line ≤ PIPE_BUF (~4KB on macOS/Linux) is atomic
# per POSIX. Our rows are bounded by MAX_MSG_LEN=500 + overhead << 4KB.
if ! printf '| %s | %s | %s | %s |\n' \
    "$timestamp" "$severity" "$category" "$escaped_message" \
    >>"$out_file" 2>/dev/null; then
  die_infra "cannot append row to: $out_file"
fi

# ----- stdout confirmation (uses original, un-escaped message) -----

# Truncate the confirmation message preview to 50 chars for terminal hygiene.
if [ "$msg_len" -gt 50 ]; then
  preview="${message:0:50}..."
else
  preview="$message"
fi

printf '%s %s %s %s\n' "$timestamp" "$severity" "$category" "$preview"
exit 0
