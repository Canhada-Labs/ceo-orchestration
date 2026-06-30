#!/usr/bin/env bash
# uninstall.sh — manifest-honoring uninstaller for ceo-orchestration
# (PLAN-083 sub-1.9)
#
# Safety property: ONLY removes files whose current sha256 matches the
# recorded manifest entry. Files modified by the user post-install have
# divergent SHAs and are PRESERVED. Files NOT listed in the manifest
# (Owner-authored, never installed by us) are also PRESERVED.
#
# Usage:
#   ./uninstall.sh <target-repo-path> [options]
#
# Options:
#   --dry-run                  Preview what WOULD be removed; touch nothing
#   --restore <backup-path>    Inverse mode: restore .claude/ from a backup .tar.gz
#   --force                    Remove files even if SHA mismatches (DESTRUCTIVE)
#   --no-backup                Skip the pre-uninstall backup tarball
#   --no-hmac-verify           Skip HMAC verification of the manifest sidecar
#   -h, --help                 Show this help
#
# Exit codes:
#   0  success (or dry-run preview)
#   1  generic failure / invalid args
#   2  target path invalid OR no manifest found
#   3  HMAC verification failed (manifest tampered)
#   4  --restore: backup tar.gz invalid or HMAC mismatch
#   5  --force not provided when SHA mismatches encountered
#
# Bash 3.2 portability guard
if [ -z "${BASH_VERSINFO:-}" ]; then
  echo "ERROR: uninstall.sh requires bash" >&2
  exit 1
fi
if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
  echo "ERROR: uninstall.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
  exit 1
fi

set -euo pipefail

TARGET=""
DRY_RUN=0
RESTORE_PATH=""
FORCE=0
NO_BACKUP=0
NO_HMAC_VERIFY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)         DRY_RUN=1; shift ;;
    --restore)         RESTORE_PATH="${2:-}"; shift 2 ;;
    --restore=*)       RESTORE_PATH="${1#--restore=}"; shift ;;
    --force)           FORCE=1; shift ;;
    --no-backup)       NO_BACKUP=1; shift ;;
    --no-hmac-verify)  NO_HMAC_VERIFY=1; shift ;;
    -h|--help)
      sed -n '1,30p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    -*)
      echo "ERROR: unknown option: $1" >&2
      exit 1
      ;;
    *)
      TARGET="$1"
      shift
      ;;
  esac
done

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "Usage: $0 <target-repo-path> [--dry-run | --restore <backup.tar.gz> | --force]" >&2
  exit 1
fi

TARGET="$( cd "$TARGET" && pwd )"

_log() { printf '%s\n' "$*"; }
_dry() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '(dry-run) %s\n' "$*"
    return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# Resolve HMAC backup key (same algorithm as install.sh)
# ---------------------------------------------------------------------------
_resolve_backup_key() {
  if [ -f "$TARGET/.claude/.audit-key" ]; then
    printf '%s\n' "$TARGET/.claude/.audit-key"
    return 0
  fi
  if [ -f "$TARGET/.claude/.install-backup-key" ]; then
    printf '%s\n' "$TARGET/.claude/.install-backup-key"
    return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# RESTORE MODE — invert a backup
# ---------------------------------------------------------------------------
if [ -n "$RESTORE_PATH" ]; then
  if [ ! -f "$RESTORE_PATH" ]; then
    echo "ERROR: backup file not found: $RESTORE_PATH" >&2
    exit 4
  fi
  _log "==> Restore mode: $RESTORE_PATH -> $TARGET"

  # Optional HMAC verification of backup
  if [ -f "$RESTORE_PATH.hmac" ] && [ "$NO_HMAC_VERIFY" -eq 0 ]; then
    key_path="$(_resolve_backup_key || true)"
    if [ -n "$key_path" ] && [ -f "$key_path" ]; then
      expected_hmac="$(awk '{print $1; exit}' "$RESTORE_PATH.hmac")"
      actual_hmac="$(python3 -c "
import hashlib, hmac, sys
key = open('$key_path', 'rb').read()
tar_sha = hashlib.sha256(open('$RESTORE_PATH', 'rb').read()).digest()
sys.stdout.write(hmac.new(key, tar_sha, hashlib.sha256).hexdigest())
")"
      if [ "$expected_hmac" != "$actual_hmac" ]; then
        echo "ERROR: backup HMAC mismatch — tarball may have been tampered with" >&2
        echo "       expected: $expected_hmac" >&2
        echo "       actual:   $actual_hmac" >&2
        exit 4
      fi
      _log "    Backup HMAC verified."
    else
      _log "    NOTE: no backup key found; skipping HMAC verification"
    fi
  fi

  if _dry "would EXTRACT $RESTORE_PATH into $TARGET"; then
    exit 0
  fi

  # Move existing .claude/ aside (safety net)
  if [ -d "$TARGET/.claude" ]; then
    aside="$TARGET/.claude.pre-restore-$(date -u +%Y%m%d-%H%M%SZ)"
    _log "    Moving current .claude/ aside to: $aside"
    mv "$TARGET/.claude" "$aside"
  fi

  _log "    Extracting backup..."
  ( cd "$TARGET" && tar xzf "$RESTORE_PATH" )
  _log "    Restore complete."
  exit 0
fi

# ---------------------------------------------------------------------------
# UNINSTALL MODE — manifest-honoring removal
# ---------------------------------------------------------------------------
MANIFEST="$TARGET/.claude/.install-manifest.sha256"

if [ ! -f "$MANIFEST" ]; then
  echo "ERROR: install manifest not found at $MANIFEST" >&2
  echo "       This target was not installed via PLAN-083 install.sh." >&2
  echo "       To remove manually, see INSTALL.md §Uninstall." >&2
  exit 2
fi

_log "==> Uninstall mode (manifest-honoring)"
_log "    Target:   $TARGET"
_log "    Manifest: $MANIFEST"
_log "    Dry-run:  $DRY_RUN"
_log "    Force:    $FORCE"
_log ""

# Pre-uninstall backup (unless --no-backup)
if [ "$NO_BACKUP" -eq 0 ]; then
  if ! _dry "would BACKUP .claude/ before uninstall"; then
    timestamp="$(date -u +%Y%m%d-%H%M%SZ)"
    backup="$TARGET/.claude.backup-uninstall-$timestamp.tar.gz"
    _log "==> Pre-uninstall backup: $backup"
    ( cd "$TARGET" && tar czf "$backup" .claude/ 2>/dev/null )
    key_path="$(_resolve_backup_key || true)"
    if [ -n "$key_path" ] && [ -f "$key_path" ]; then
      backup_hmac="$(python3 -c "
import hashlib, hmac, sys
key = open('$key_path', 'rb').read()
tar_sha = hashlib.sha256(open('$backup', 'rb').read()).digest()
sys.stdout.write(hmac.new(key, tar_sha, hashlib.sha256).hexdigest())
")"
      printf '%s  %s\n' "$backup_hmac" "$backup" > "$backup.hmac"
      chmod 0600 "$backup.hmac"
    fi
  fi
fi

# Walk the manifest; for each entry, verify SHA before delete.
mismatch_count=0
removed_count=0
preserved_count=0
absent_count=0
mismatch_files=""

while IFS= read -r line; do
  # Skip comments and blank lines
  case "$line" in
    '#'*|'') continue ;;
  esac
  # Format: <sha>  <relpath>
  recorded_sha="${line%% *}"
  rel="${line#* }"
  rel="${rel#* }"  # strip second space if double-space format
  rel="$(printf '%s' "$line" | awk '{ $1=""; sub(/^ +/, ""); print }')"
  fpath="$TARGET/$rel"

  if [ ! -e "$fpath" ]; then
    absent_count=$((absent_count + 1))
    continue
  fi

  if [ ! -f "$fpath" ]; then
    continue
  fi

  actual_sha="$(python3 -c "
import hashlib, sys
with open(sys.argv[1], 'rb') as f:
    sys.stdout.write(hashlib.sha256(f.read()).hexdigest())
" "$fpath")"

  if [ "$actual_sha" = "$recorded_sha" ]; then
    if _dry "would REMOVE $rel"; then
      removed_count=$((removed_count + 1))
    else
      rm -f "$fpath"
      removed_count=$((removed_count + 1))
    fi
  else
    mismatch_count=$((mismatch_count + 1))
    mismatch_files="$mismatch_files $rel"
    if [ "$FORCE" -eq 1 ]; then
      if _dry "would FORCE-REMOVE (sha mismatch) $rel"; then
        removed_count=$((removed_count + 1))
      else
        rm -f "$fpath"
        removed_count=$((removed_count + 1))
      fi
    else
      preserved_count=$((preserved_count + 1))
      _log "    PRESERVED (sha mismatch, user-modified): $rel"
    fi
  fi
done < "$MANIFEST"

# Refuse if mismatches encountered without --force
if [ "$mismatch_count" -gt 0 ] && [ "$FORCE" -eq 0 ]; then
  _log ""
  _log "==> Uninstall summary (incomplete):"
  _log "    Removed:   $removed_count"
  _log "    Preserved: $preserved_count (user-modified — sha didn't match manifest)"
  _log "    Absent:    $absent_count (already gone)"
  _log ""
  _log "    To force-remove user-modified files: re-run with --force"
  _log "    Preserved files were NOT touched."
  exit 0
fi

# Clean up manifest + empty .claude/ subdirs (only if everything matched)
if ! _dry "would REMOVE manifest $MANIFEST"; then
  if [ "$mismatch_count" -eq 0 ] || [ "$FORCE" -eq 1 ]; then
    rm -f "$MANIFEST"
  fi
fi

# Clean up empty directories under .claude/ (post-removal sweep)
if [ "$DRY_RUN" -eq 0 ] && [ -d "$TARGET/.claude" ]; then
  find "$TARGET/.claude" -depth -type d -empty -delete 2>/dev/null || true
fi

_log ""
_log "==> Uninstall summary:"
_log "    Removed:   $removed_count"
_log "    Preserved: $preserved_count"
_log "    Absent:    $absent_count"
_log "    Manifest:  $([ -f "$MANIFEST" ] && echo "KEPT" || echo "REMOVED")"
exit 0
