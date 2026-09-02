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
# Manifest-path safety (PLAN-183 §9.8, rail r1 S337). The manifest is a FILE in
# the target and it is NOT integrity-checked before the walk: a crafted or
# corrupted record must not turn this script into a deleter, reader or
# extractor OUTSIDE the target. Two tests, applied before every removal, every
# backup entry and every restore member:
#   _rel_unsafe REL         lexical — empty, absolute, `.`/`..` segments,
#                           control characters                 (rc 0 = unsafe)
#   _rel_ancestor_link REL  physical — an ancestor component under $TARGET is
#                           a symlink; `-f`, `rm -f` and `tar` all follow it,
#                           `! -L` only ever tests the leaf     (rc 0 = linked)
# Measured pre-cure (S337): a record `<sha>  ../outside/victim.txt` was
# REMOVED (outside the target), and with `docs -> <outside dir>` the walk
# deleted the outside file and the backup archived bytes read through the link.
# ---------------------------------------------------------------------------
_rel_unsafe() {
  case "$1" in
    ''|/*|.|./*|..|../*|*/./*|*/../*|*/.|*/..) return 0 ;;
    *[$'\n\r\t']*) return 0 ;;
    # rail r2 (S337) P2: whitespace and glob metacharacters — no delivery route
    # ever carries them (_wbm_route_relpath_ok rejects both), and a crafted
    # name with either would word-split or pathname-expand in the sweep loop.
    *' '*|*'*'*|*'?'*|*'['*|*']'*|*'\'*) return 0 ;;
    # rail r3 (S337) P1: an option-like path — the leaf OR any component
    # starting with '-' — would be read by tar as a flag, not an operand.
    -*|*/-*) return 0 ;;
  esac
  return 1
}
_rel_ancestor_link() {
  _ral_cur="$TARGET"
  _ral_parent="$( dirname "$1" )"
  _ral_old="$IFS"
  IFS='/'
  # shellcheck disable=SC2086  # intentional word-split on the relpath components
  for _ral_c in $_ral_parent; do
    [ -n "$_ral_c" ] || continue
    [ "$_ral_c" = "." ] && continue
    _ral_cur="$_ral_cur/$_ral_c"
    if [ -L "$_ral_cur" ]; then
      IFS="$_ral_old"
      return 0
    fi
  done
  IFS="$_ral_old"
  return 1
}

# PLAN-183 §9.8 (S337): remember which top-level trees (other than .claude,
# which has its own sweep) this run removed from — exact-sha AND --force
# removals — so the empty directories the deliveries leave behind are swept.
swept_trees=""
_track_tree() {
  case "$1" in
    .claude/*) ;;
    */*)
      _tt_top="${1%%/*}"
      case " $swept_trees " in
        *" $_tt_top "*) ;;
        *) swept_trees="$swept_trees $_tt_top" ;;
      esac ;;
  esac
}
# The sweep itself: only EMPTY directories go (-empty), so a tree that still
# holds a file of the adopter's — or a PRESERVED delivery — is never touched,
# and trees this run did not remove from are not visited at all. Called on
# BOTH exit paths (complete and incomplete): a partial uninstall that removed
# every docs/ delivery but preserved an edited CODEOWNERS still empties docs/.
_sweep_emptied_trees() {
  for _tree in $swept_trees; do
    case "$_tree" in ''|.|..|/*) continue ;; esac   # never leave the target
    [ -d "$TARGET/$_tree" ] || continue
    if ! _dry "would REMOVE empty directories left under $_tree/"; then
      find "$TARGET/$_tree" -depth -type d -empty -delete 2>/dev/null || true
    fi
  done
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
  # PLAN-183 §9.8 (rail r1, S337): the archive now carries deliveries OUTSIDE
  # .claude/ (docs/, .github/, SPEC/, root files). `.claude/` is restored whole
  # (the live one was moved aside above); every OTHER member is restored only
  # when nothing exists at its path — a file the adopter recreated or edited
  # since the uninstall is PRESERVED — and a member whose path is unsafe or
  # whose ancestor is a symlink is never extracted (traversal / write-through).
  # rail r2 (S337) P1: a restore that could not deliver is a FAILURE, not a
  # note — a broken/absent .claude member rolls the moved-aside .claude back
  # and exits 4; a failed or refused non-.claude member exits 1. Members are
  # read from a LIST FILE, not a pipeline, so the counters survive the loop.
  _rst_rollback() {
    # rail r3 (S337) P2: a FAILED .claude extraction can leave a PARTIAL
    # $TARGET/.claude directory, which the `! -d` guard would treat as "already
    # restored". Clear the partial first so the moved-aside tree comes back
    # whole rather than merged with half an extraction.
    if [ -n "${aside:-}" ] && [ -d "$aside" ]; then
      rm -rf "$TARGET/.claude" 2>/dev/null || true
      mv "$aside" "$TARGET/.claude"
      _log "    Rolled the previous .claude/ back into place."
    fi
  }
  _rst_list="$(mktemp 2>/dev/null || mktemp -t ceo-restore-list)"
  if ! tar tzf "$RESTORE_PATH" > "$_rst_list" 2>/dev/null; then
    rm -f "$_rst_list"
    echo "ERROR: cannot list the backup archive (corrupt tarball?)" >&2
    _rst_rollback
    exit 4
  fi
  if ! grep -qE '^(\./)?\.claude(/|$)' "$_rst_list"; then
    rm -f "$_rst_list"
    echo "ERROR: the archive carries no .claude/ member — not a ceo-orchestration backup" >&2
    _rst_rollback
    exit 4
  fi
  if ! ( cd "$TARGET" && tar xzf "$RESTORE_PATH" .claude 2>/dev/null ); then
    rm -f "$_rst_list"
    echo "ERROR: failed to extract .claude/ from the backup" >&2
    _rst_rollback
    exit 4
  fi
  restore_failed=0
  restore_refused=0
  while IFS= read -r _m; do
    _mrel="${_m#./}"
    case "$_mrel" in .claude|.claude/*|*/) continue ;; esac
    if _rel_unsafe "$_mrel" || _rel_ancestor_link "$_mrel"; then
      restore_refused=$((restore_refused + 1))
      _log "    SKIPPED (unsafe path or symlinked ancestor — not extracted): $_mrel"
      continue
    fi
    if [ -e "$TARGET/$_mrel" ] || [ -L "$TARGET/$_mrel" ]; then
      _log "    PRESERVED (exists — not overwritten by restore): $_mrel"
      continue
    fi
    if ( cd "$TARGET" && tar xzf "$RESTORE_PATH" -- "$_m" 2>/dev/null ); then
      _log "    RESTORED: $_mrel"
    else
      restore_failed=$((restore_failed + 1))
      _log "    RESTORE-FAILED: $_mrel"
    fi
  done < "$_rst_list"
  rm -f "$_rst_list"
  if [ "$restore_failed" -gt 0 ] || [ "$restore_refused" -gt 0 ]; then
    _log "    Restore INCOMPLETE: $restore_failed member(s) failed, $restore_refused refused (unsafe path) — see the lines above."
    exit 1
  fi
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
    # PLAN-183 §9.8 (S337): the manifest records deliveries OUTSIDE .claude/
    # (docs/, .github/ since W5; SPEC/, PROTOCOL.md, the marker) and the walk
    # below removes them, so the backup must cover them too — a tarball of
    # .claude/ alone could not restore what this run deletes. The list comes
    # from the manifest itself, regular files only, nothing outside it.
    backup_list="$(mktemp 2>/dev/null || mktemp -t ceo-uninstall-list)"
    printf '.claude\n' > "$backup_list"
    awk '{ idx = index($0, "  "); if (idx == 0) next; print substr($0, idx + 2) }' "$MANIFEST" \
      | while IFS= read -r _brel; do
          case "$_brel" in '#'*|.claude/*) continue ;; esac
          # rail r1 (S337): never read THROUGH a symlinked ancestor into the
          # archive — `-f` and `tar` follow it, `! -L` only tests the leaf.
          if _rel_unsafe "$_brel" || _rel_ancestor_link "$_brel"; then continue; fi
          [ -f "$TARGET/$_brel" ] && [ ! -L "$TARGET/$_brel" ] && printf '%s\n' "$_brel"
        done >> "$backup_list"
    # NO --no-recursion: the list carries `.claude` as a DIRECTORY entry whose
    # contents must be archived (its files are excluded from the list by
    # design). Adding it emptied every backup of .claude/* — caught by e2e U.3
    # and by the pair rail in the same round (r3 defect, cured r4).
    ( cd "$TARGET" && tar czf "$backup" -T "$backup_list" 2>/dev/null )
    rm -f "$backup_list"
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
unsafe_count=0

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
  # rail r1 (S337): a record is REFUSED — never tested, hashed or removed —
  # when its path escapes the target lexically or through a symlinked ancestor.
  if _rel_unsafe "$rel"; then
    unsafe_count=$((unsafe_count + 1))
    _log "    REFUSED (unsafe manifest path — not touched): $rel"
    continue
  fi
  if _rel_ancestor_link "$rel"; then
    unsafe_count=$((unsafe_count + 1))
    _log "    REFUSED (symlinked ancestor — a removal would follow it outside the target): $rel"
    continue
  fi
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
    _track_tree "$rel"   # PLAN-183 §9.8: remember the tree for the emptied-directory sweep
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
      _track_tree "$rel"   # rail r1 (S337): forced removals empty trees too
    else
      preserved_count=$((preserved_count + 1))
      _log "    PRESERVED (sha mismatch, user-modified): $rel"
    fi
  fi
done < "$MANIFEST"

# Refuse if mismatches were encountered without --force, or if ANY record was
# refused. rail r5 (S337) P2: --force overrides a sha MISMATCH, never a REFUSAL
# (the manifest block below already says so), so a --force run that refused a
# record is still an INCOMPLETE uninstall. Before this cure the `&& FORCE -eq 0`
# applied to the refusal too: such a run fell through to the "everything
# matched" summary below — a complete-looking report contradicted by its own
# `Refused:` and `Manifest: KEPT` lines.
if [ "$unsafe_count" -gt 0 ] || { [ "$mismatch_count" -gt 0 ] && [ "$FORCE" -eq 0 ]; }; then
  _sweep_emptied_trees   # rail r1 (S337): the partial path empties trees too
  _log ""
  _log "==> Uninstall summary (incomplete):"
  _log "    Removed:   $removed_count"
  _log "    Preserved: $preserved_count (user-modified — sha didn't match manifest)"
  _log "    Absent:    $absent_count (already gone)"
  _log "    Refused:   $unsafe_count (unsafe manifest path or symlinked ancestor — not touched)"
  _log ""
  # The --force hint is only true for a sha mismatch met WITHOUT --force; a
  # refusal is never lifted by --force, so say that instead of suggesting it.
  if [ "$mismatch_count" -gt 0 ] && [ "$FORCE" -eq 0 ]; then
    _log "    To force-remove user-modified files: re-run with --force"
  fi
  if [ "$unsafe_count" -gt 0 ]; then
    _log "    Refused records are never removed, with or without --force: fix the manifest path or the symlinked ancestor, then re-run."
  fi
  _log "    Preserved files were NOT touched."
  exit 0
fi

# Clean up manifest + empty .claude/ subdirs (only if everything matched)
if ! _dry "would REMOVE manifest $MANIFEST"; then
  # rail r3 (S337) P1: a refused record (unsafe path / symlinked ancestor) means
  # the install was not fully removed — keep the manifest for a --force retry.
  # rail r4 (S337) P2: --force overrides a sha MISMATCH, never a REFUSAL —
  # a refused record was not removed by any run, so the ledger must survive.
  if [ "$unsafe_count" -eq 0 ] && { [ "$mismatch_count" -eq 0 ] || [ "$FORCE" -eq 1 ]; }; then
    rm -f "$MANIFEST"
  fi
fi

# Clean up empty directories under .claude/ (post-removal sweep)
if [ "$DRY_RUN" -eq 0 ] && [ -d "$TARGET/.claude" ]; then
  find "$TARGET/.claude" -depth -type d -empty -delete 2>/dev/null || true
fi

# PLAN-183 §9.8 (S337): the same sweep for every other top-level tree this run
# removed deliveries from (docs/, .github/, SPEC/ …). Measured before the cure:
# a pristine uninstall left docs/, .github/workflows/ and SPEC/v1 behind, empty.
_sweep_emptied_trees

_log ""
_log "==> Uninstall summary:"
_log "    Removed:   $removed_count"
_log "    Preserved: $preserved_count"
_log "    Absent:    $absent_count"
_log "    Refused:   $unsafe_count (unsafe manifest path or symlinked ancestor — not touched)"
_log "    Manifest:  $([ -f "$MANIFEST" ] && echo "KEPT" || echo "REMOVED")"
exit 0
