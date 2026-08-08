#!/bin/bash
# check-framework-updates.sh — compare local VERSION to upstream tags
#
# Fetches upstream tag list via `git ls-remote --tags <repo>` (HTTPS),
# parses semantic versions (vX.Y.Z, vX.Y.Z-rc.N), compares with local
# VERSION file, and reports the delta.
#
# Network call: HTTPS only. Adopter-invoked. Documented in
# threat-model.md as opt-in trust boundary.
#
# Usage:
#   check-framework-updates.sh                              # default upstream
#   check-framework-updates.sh --upstream <git-url>
#   check-framework-updates.sh --json
#   check-framework-updates.sh --quiet                       # exit code only
#
# Exit codes:
#   0 — local matches upstream OR cannot determine (network failure)
#   1 — local is behind (newer GA tag available)
#   2 — local is behind by ≥ 1 MINOR version (highlighted as urgent)
#   3 — fatal (no git, no VERSION file, malformed local version)

set -euo pipefail

# Framework upstream URL — points to the canonical ceo-orchestration
# upstream by default. Adopters who fork the framework override via
# CEO_FRAMEWORK_UPSTREAM env var OR install.sh
# `--framework-upstream=<url>` substitution at install time.
UPSTREAM="${CEO_FRAMEWORK_UPSTREAM:-https://github.com/Canhada-Labs/ceo-orchestration}"
FORMAT="text"
QUIET=0
LOCAL_VERSION_FILE=""

usage() {
  cat <<EOF
check-framework-updates.sh — compare local VERSION to upstream tags

Usage:
  check-framework-updates.sh [options]

Options:
  --upstream <git-url>     Override default upstream
                           (default: \$CEO_FRAMEWORK_UPSTREAM or
                            https://github.com/Canhada-Labs/ceo-orchestration)
  --version-file <path>    Override default VERSION lookup
  --json                   Machine-readable output
  --quiet                  Suppress output; exit code only
  -h, --help               This message

Exit codes:
  0 — up to date (or cannot determine)
  1 — behind (newer GA tag available)
  2 — behind by ≥ 1 MINOR (urgent)
  3 — fatal
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream) UPSTREAM="$2"; shift 2 ;;
    --version-file) LOCAL_VERSION_FILE="$2"; shift 2 ;;
    --json) FORMAT="json"; shift ;;
    --quiet) QUIET=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage >&2; exit 3 ;;
  esac
done

log() {
  if [ "$QUIET" -eq 0 ]; then
    echo "$@" >&2
  fi
  return 0
}
out() {
  if [ "$QUIET" -eq 0 ]; then
    echo "$@"
  fi
  return 0
}

# Resolve the LOCAL framework version — MARKER-FIRST with VERSION fallback
# (PLAN-166 F3 / ADR-155-AMEND-1). In an ADOPTER tree the root VERSION is an
# install-time snapshot: upgrade.sh deliberately never touches it (the
# S238/ADR-155 clobber class), so reading it post-upgrade reports the OLD
# version forever and this checker would exit behind-minor demanding the
# SAME upgrade it just performed, in a loop (r8). The upgrade refreshes
# .claude/.framework-version instead — but the marker is only TRUSTED when
# the SAME delivery record the writers use (the ADR-155 baseline manifest,
# .claude/.install-manifest.sha256) records it as framework-delivered: a
# pre-existing adopter marker that install EXISTS-skipped must not be read
# at all (r20). Resolution order:
#   1. --version-file <path>              (explicit override — unchanged)
#   2. <root>/.claude/.framework-version  when well-formed AND
#                                         delivery-recorded in the manifest
#   3. <root>/VERSION                     (pre-v1.3.0 installs, and the
#                                          framework repo itself, where the
#                                          tracked marker == VERSION and
#                                          VERSION stays the authority)
if [ -n "$LOCAL_VERSION_FILE" ]; then
  VFILE="$LOCAL_VERSION_FILE"
  VSOURCE="explicit --version-file"
else
  # Walk up from CWD to the first directory carrying either signal.
  cur="$(pwd)"
  VROOT=""
  VFILE=""
  VSOURCE=""
  while [ "$cur" != "/" ]; do
    if [ -f "$cur/.claude/.framework-version" ] || [ -f "$cur/VERSION" ]; then
      VROOT="$cur"
      break
    fi
    cur="$(dirname "$cur")"
  done
  if [ -z "$VROOT" ]; then
    echo "fatal: no .claude/.framework-version or VERSION found (looked from $(pwd))" >&2
    exit 3
  fi
  MARKER="$VROOT/.claude/.framework-version"
  MANIFEST="$VROOT/.claude/.install-manifest.sha256"
  if [ -f "$MARKER" ]; then
    MARKER_REC=""
    if [ -f "$MANIFEST" ]; then
      MARKER_REC="$(grep -E '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$MANIFEST" 2>/dev/null | head -1 || true)"
    fi
    if [ -n "$MARKER_REC" ]; then
      # r20 answered PROVENANCE (is this marker the framework's delivery?)
      # but never INTEGRITY: a delivered marker edited afterwards to any
      # well-formed version still satisfied the record check, so hand-editing
      # 1.3.0 -> 9.9.9 made the checker report up-to-date against an upstream
      # 1.3.0 and SUPPRESS a real update (codex W1 round 7, P2). Verify the
      # live bytes against the record before selecting the marker; anything
      # unverifiable falls back to VERSION — the same conservative direction
      # r20 already takes for an unrecorded marker.
      MARKER_OK=""
      case "$MARKER_REC" in
        LINK\ \ *)
          # Fixed double-space delimiter (targets may contain spaces).
          _rec_tgt="${MARKER_REC#LINK  .claude/.framework-version  }"
          _live_tgt="$(readlink "$MARKER" 2>/dev/null || true)"
          if [ -n "$_rec_tgt" ] && [ "$_rec_tgt" = "$_live_tgt" ]; then MARKER_OK=1; fi
          ;;
        *)
          _rec_dg="${MARKER_REC%%  *}"
          _live_dg=""
          if command -v shasum >/dev/null 2>&1; then
            _live_dg="$(shasum -a 256 "$MARKER" 2>/dev/null | cut -d' ' -f1 || true)"
          elif command -v sha256sum >/dev/null 2>&1; then
            _live_dg="$(sha256sum "$MARKER" 2>/dev/null | cut -d' ' -f1 || true)"
          fi
          if [ -n "$_live_dg" ] && [ "$_rec_dg" = "$_live_dg" ]; then MARKER_OK=1; fi
          ;;
      esac
      if [ -z "$MARKER_OK" ]; then
        log "note: .claude/.framework-version does NOT match its delivery record (edited, redirected, or no digest tool available) — falling back to VERSION"
      else
        MARKER_VAL="$(tr -d '\n\r ' < "$MARKER" 2>/dev/null || true)"
        if [[ "$MARKER_VAL" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
          VFILE="$MARKER"
          VSOURCE="marker (.claude/.framework-version, delivery-recorded)"
        else
          log "note: .claude/.framework-version malformed ('$MARKER_VAL') — falling back to VERSION"
        fi
      fi
    elif [ ! -f "$MANIFEST" ] && [ ! -f "$VROOT/VERSION" ]; then
      # No manifest AND no VERSION: the marker is the only signal there is
      # (fail-open — refusing here would make the checker fatal on a tree
      # that still has a perfectly readable version value).
      VFILE="$MARKER"
      VSOURCE="marker (no manifest — only signal present)"
    else
      log "note: .claude/.framework-version present but NOT delivery-recorded in .claude/.install-manifest.sha256 — falling back to VERSION (r20: a pre-existing adopter marker is not the framework's)"
    fi
  fi
  if [ -z "$VFILE" ] && [ -f "$VROOT/VERSION" ]; then
    VFILE="$VROOT/VERSION"
    VSOURCE="root VERSION (fallback)"
  fi
fi

if [ -z "$VFILE" ] || [ ! -f "$VFILE" ]; then
  echo "fatal: version source not found (looked from $(pwd))" >&2
  exit 3
fi
log "version source: ${VSOURCE:-unknown} ($VFILE)"

LOCAL="$(tr -d '\n\r ' < "$VFILE")"
if [ -z "$LOCAL" ]; then
  echo "fatal: VERSION file is empty: $VFILE" >&2
  exit 3
fi

# Validate local version shape
if ! [[ "$LOCAL" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
  echo "fatal: local VERSION malformed: $LOCAL" >&2
  exit 3
fi

# Fetch upstream tags
if ! command -v git >/dev/null 2>&1; then
  echo "fatal: git not available" >&2
  exit 3
fi

log "fetching tags from $UPSTREAM ..."

# Network call. Tolerate failure with exit 0 (we should not pageop on a
# transient git fetch failure).
TAGS_RAW="$(git ls-remote --tags --refs "$UPSTREAM" 2>&1 || true)"
if [ -z "$TAGS_RAW" ] || echo "$TAGS_RAW" | grep -qiE 'fatal|error|denied'; then
  log "warning: could not fetch upstream tags; assuming up-to-date"
  if [ "$FORMAT" = "json" ]; then
    out '{"status":"unknown","local":"'"$LOCAL"'","upstream":null,"reason":"network_or_perm_failure"}'
  else
    out "status: unknown (could not fetch upstream)"
    out "local:    $LOCAL"
    out "upstream: <unreachable>"
  fi
  exit 0
fi

# Parse — extract refs/tags/vX.Y.Z[-rc.N], strip leading v
TAGS=()
while IFS= read -r tag; do
  [ -n "$tag" ] && TAGS+=("$tag")
done < <(echo "$TAGS_RAW" | awk '{print $2}' | sed 's|^refs/tags/||' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$' | sed 's/^v//' | sort -V -u)

if [ "${#TAGS[@]}" -eq 0 ]; then
  log "warning: no semver tags found upstream"
  if [ "$FORMAT" = "json" ]; then
    out '{"status":"unknown","local":"'"$LOCAL"'","upstream":null,"reason":"no_semver_tags"}'
  else
    out "status: unknown (no semver tags upstream)"
  fi
  exit 0
fi

LATEST="${TAGS[${#TAGS[@]}-1]}"

# Helper: parse "X.Y.Z[-rc.N]" into space-sep "X Y Z RC" (RC=999 if no -rc)
_parse_version() {
  local v="$1"
  local x y z rc
  if [[ "$v" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)-rc\.([0-9]+)$ ]]; then
    x="${BASH_REMATCH[1]}"
    y="${BASH_REMATCH[2]}"
    z="${BASH_REMATCH[3]}"
    rc="${BASH_REMATCH[4]}"
  elif [[ "$v" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    x="${BASH_REMATCH[1]}"
    y="${BASH_REMATCH[2]}"
    z="${BASH_REMATCH[3]}"
    rc="999"
  else
    echo "0 0 0 0"
    return
  fi
  echo "$x $y $z $rc"
}

# Compare LOCAL vs LATEST
read -r LX LY LZ LR < <(_parse_version "$LOCAL")
read -r UX UY UZ UR < <(_parse_version "$LATEST")

CMP=0
if [ "$UX" -gt "$LX" ]; then CMP=1
elif [ "$UX" -eq "$LX" ] && [ "$UY" -gt "$LY" ]; then CMP=1
elif [ "$UX" -eq "$LX" ] && [ "$UY" -eq "$LY" ] && [ "$UZ" -gt "$LZ" ]; then CMP=1
elif [ "$UX" -eq "$LX" ] && [ "$UY" -eq "$LY" ] && [ "$UZ" -eq "$LZ" ] && [ "$UR" -gt "$LR" ]; then CMP=1
fi

# Compute MINOR delta for urgency tier
MINOR_BEHIND=0
if [ "$UX" -eq "$LX" ] && [ "$UY" -gt "$LY" ]; then
  MINOR_BEHIND=$((UY - LY))
elif [ "$UX" -gt "$LX" ]; then
  MINOR_BEHIND=99   # MAJOR jump → always "urgent"
fi

# Status
if [ "$CMP" -eq 0 ]; then
  STATUS="up-to-date"
  EXIT=0
else
  if [ "$MINOR_BEHIND" -ge 1 ]; then
    STATUS="behind-minor"
    EXIT=2
  else
    STATUS="behind"
    EXIT=1
  fi
fi

# Output
if [ "$FORMAT" = "json" ]; then
  out "{\"status\":\"$STATUS\",\"local\":\"$LOCAL\",\"upstream\":\"$LATEST\",\"minor_behind\":$MINOR_BEHIND}"
else
  out "ceo-orchestration update check"
  out ""
  out "  local:    $LOCAL"
  out "  upstream: $LATEST"
  out "  status:   $STATUS"
  out ""
  case "$STATUS" in
    up-to-date)
      out "✓ You are running the latest version."
      ;;
    behind)
      out "→ A newer version is available."
      out "  Upgrade: bash scripts/upgrade.sh --target v$LATEST"
      out "  See: docs/UPGRADE-PROCEDURE.md"
      ;;
    behind-minor)
      out "⚠ You are $MINOR_BEHIND MINOR version(s) behind."
      out "  This may include security fixes; upgrade soon."
      out "  Upgrade: bash scripts/upgrade.sh --target v$LATEST"
      out "  See: docs/UPGRADE-PROCEDURE.md"
      ;;
  esac
  out ""
fi

exit "$EXIT"
