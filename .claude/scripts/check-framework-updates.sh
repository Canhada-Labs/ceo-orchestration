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

# Resolve VERSION
if [ -n "$LOCAL_VERSION_FILE" ]; then
  VFILE="$LOCAL_VERSION_FILE"
else
  # Walk up from CWD looking for a VERSION file
  cur="$(pwd)"
  VFILE=""
  while [ "$cur" != "/" ]; do
    if [ -f "$cur/VERSION" ]; then
      VFILE="$cur/VERSION"
      break
    fi
    cur="$(dirname "$cur")"
  done
fi

if [ -z "$VFILE" ] || [ ! -f "$VFILE" ]; then
  echo "fatal: VERSION file not found (looked from $(pwd))" >&2
  exit 3
fi

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
