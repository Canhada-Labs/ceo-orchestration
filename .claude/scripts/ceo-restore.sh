#!/bin/bash
# ceo-restore.sh — restore framework state from a ceo-backup tarball
#
# Usage:
#   ceo-restore.sh <tarball>             # dry-run by default
#   ceo-restore.sh <tarball> --apply     # actually restore
#
# Default mode is DRY-RUN — verifies SHA256 sidecar + lists files
# the apply mode would overwrite.
#
# Apply mode prompts for confirmation unless --force is passed.
#
# Exit codes:
#   0 — success (dry-run lists; apply completed)
#   1 — usage error / SHA mismatch / refused destination
#   2 — fatal (tarball corrupt, no permissions)

set -euo pipefail

TARBALL=""
APPLY=0
FORCE=0
QUIET=0
DEST_OVERRIDE=""
PROJECT_SLUG_OVERRIDE=""
RESTORE_PLANS=0
RESTORE_AGENT_METRICS=0

usage() {
  cat <<EOF
ceo-restore.sh — restore framework state from a ceo-backup tarball

Usage:
  ceo-restore.sh <tarball> [options]

Options:
  --apply                  Commit the restore (default: dry-run)
  --force                  Skip the apply confirmation prompt
  --quiet                  Suppress progress
  --dest <dir>             Restore destination (default: CEO_AUDIT_LOG_DIR or ~/.claude/projects/<slug>)
  --project-slug <name>    Override slug for default dest path
  --restore-plans          Also restore plans/ subdir if present in tarball
  --restore-agent-metrics  Also restore .claude/agent-metrics.md
  -h, --help               This message

The default --dry-run mode:
  - verifies tarball SHA256 against the .sha256 sidecar (if present)
  - lists every file the apply mode would write
  - exits 0 on success; non-zero only on integrity failure

The --apply mode:
  - re-verifies SHA256
  - prompts for confirmation (unless --force)
  - extracts audit/ + memory/ to <dest>
  - extracts agent-metrics.md / plans/ to CWD's .claude/ if --restore-* flags
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --force) FORCE=1; shift ;;
    --quiet) QUIET=1; shift ;;
    --dest) DEST_OVERRIDE="$2"; shift 2 ;;
    --project-slug) PROJECT_SLUG_OVERRIDE="$2"; shift 2 ;;
    --restore-plans) RESTORE_PLANS=1; shift ;;
    --restore-agent-metrics) RESTORE_AGENT_METRICS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --*) echo "unknown flag: $1" >&2; usage >&2; exit 1 ;;
    *)
      if [ -z "$TARBALL" ]; then
        TARBALL="$1"; shift
      else
        echo "extra argument: $1" >&2; usage >&2; exit 1
      fi
      ;;
  esac
done

log() {
  if [ "$QUIET" -eq 0 ]; then
    echo "$@" >&2
  fi
  return 0
}

if [ -z "$TARBALL" ]; then
  echo "error: tarball path required" >&2
  usage >&2
  exit 1
fi

if [ ! -f "$TARBALL" ]; then
  echo "error: tarball not found: $TARBALL" >&2
  exit 1
fi

# Resolve destination
PROJECT_SLUG="${PROJECT_SLUG_OVERRIDE:-${CEO_PROJECT_NAME:-ceo-orchestration}}"
if [ -n "$DEST_OVERRIDE" ]; then
  DEST="$DEST_OVERRIDE"
else
  DEST="${CEO_AUDIT_LOG_DIR:-$HOME/.claude/projects/$PROJECT_SLUG}"
fi

log "ceo-restore: tarball=$TARBALL dest=$DEST mode=$([ "$APPLY" -eq 1 ] && echo APPLY || echo DRY-RUN)"

# Resolve sha256 binary
SHA256_BIN=""
if command -v sha256sum >/dev/null 2>&1; then
  SHA256_BIN="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
  SHA256_BIN="shasum -a 256"
fi

# SHA verification
SHA_SIDE="$TARBALL.sha256"
if [ -n "$SHA256_BIN" ] && [ -f "$SHA_SIDE" ]; then
  EXPECTED="$(cat "$SHA_SIDE" | awk '{print $1}')"
  ACTUAL="$($SHA256_BIN "$TARBALL" | awk '{print $1}')"
  if [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "fatal: SHA256 mismatch" >&2
    echo "  expected: $EXPECTED" >&2
    echo "  actual:   $ACTUAL" >&2
    exit 2
  fi
  log "sha256: verified ($ACTUAL)"
else
  log "warning: no .sha256 sidecar found; integrity not verified"
fi

# List contents (dry-run preview)
log ""
log "tarball contents:"
tar -tzf "$TARBALL" | sed 's/^/  /' | (head -50; echo "  ... (use 'tar tzf $TARBALL' for full listing)" 2>/dev/null) | head -52 | tee /tmp/ceo-restore-listing.$$ >/dev/null
[ "$QUIET" -eq 0 ] && cat /tmp/ceo-restore-listing.$$ >&2
rm -f /tmp/ceo-restore-listing.$$

if [ "$APPLY" -eq 0 ]; then
  log ""
  log "[dry-run] no files modified."
  log "[dry-run] re-run with --apply to commit (will prompt unless --force)."
  exit 0
fi

# ----- APPLY -----

# Confirmation
if [ "$FORCE" -ne 1 ]; then
  echo ""
  echo "About to restore tarball INTO:"
  echo "  $DEST/audit/        (overwrites audit-log.jsonl + rotated archives)"
  echo "  $DEST/memory/       (overwrites auto-memory)"
  if [ "$RESTORE_AGENT_METRICS" -eq 1 ]; then
    echo "  $(pwd)/.claude/agent-metrics.md (if present in tarball)"
  fi
  if [ "$RESTORE_PLANS" -eq 1 ]; then
    echo "  $(pwd)/.claude/plans/ (if present in tarball)"
  fi
  echo ""
  read -p "Proceed? [yes/no] " ANSWER
  if [ "$ANSWER" != "yes" ]; then
    echo "aborted."
    exit 1
  fi
fi

mkdir -p "$DEST"

# Stage extract to a temp dir then move
STAGE_DIR="$(mktemp -d -t ceo-restore-XXXXXX)"
trap 'rm -rf "$STAGE_DIR"' EXIT

tar -xzf "$TARBALL" -C "$STAGE_DIR"

# Restore audit/
if [ -d "$STAGE_DIR/audit" ]; then
  for f in "$STAGE_DIR/audit"/*; do
    [ -f "$f" ] || continue
    cp -p "$f" "$DEST/$(basename "$f")"
  done
  log "restored: audit/ → $DEST/"
fi

# Restore memory/
if [ -d "$STAGE_DIR/memory" ]; then
  mkdir -p "$DEST/memory"
  cp -pR "$STAGE_DIR/memory/." "$DEST/memory/"
  log "restored: memory/ → $DEST/memory/"
fi

# Optional: agent-metrics.md
if [ "$RESTORE_AGENT_METRICS" -eq 1 ] && [ -f "$STAGE_DIR/agent-metrics.md" ]; then
  if [ -d "$(pwd)/.claude" ]; then
    cp -p "$STAGE_DIR/agent-metrics.md" "$(pwd)/.claude/agent-metrics.md"
    log "restored: agent-metrics.md → $(pwd)/.claude/agent-metrics.md"
  else
    log "warning: no .claude/ in CWD; agent-metrics.md not restored"
  fi
fi

# Optional: plans/
if [ "$RESTORE_PLANS" -eq 1 ] && [ -d "$STAGE_DIR/plans" ]; then
  if [ -d "$(pwd)/.claude" ]; then
    mkdir -p "$(pwd)/.claude/plans"
    cp -pR "$STAGE_DIR/plans/." "$(pwd)/.claude/plans/"
    log "restored: plans/ → $(pwd)/.claude/plans/"
  else
    log "warning: no .claude/ in CWD; plans/ not restored"
  fi
fi

log ""
log "restore complete."
exit 0
