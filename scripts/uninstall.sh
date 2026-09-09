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
#   --no-hmac-verify           Skip HMAC verification of the restore backup's .hmac sidecar
#   -h, --help                 Show this help
#
# Exit codes:
#   0  success (or dry-run preview)
#   1  generic failure / invalid args
#   2  target path invalid OR no manifest found
#   3  (reserved) — the install MANIFEST is NOT HMAC-verified in this version.
#      The pre-uninstall backup gets an HMAC sidecar ONLY when a target-local
#      key exists (.claude/.audit-key or .claude/.install-backup-key); neither
#      install nor upgrade creates one in copy mode, so a normal backup is
#      UNSIGNED and --restore accepts it as such (rc.1 condition 51). A
#      manifest record is trusted for its PATH shape and SHA only.
#   4  --restore: backup tar.gz invalid or HMAC mismatch
#   5  uninstall INCOMPLETE: SHA mismatches encountered without --force
#      (user-modified files preserved, manifest kept)
#   6  uninstall INCOMPLETE: one or more manifest records REFUSED (unsafe
#      path, symlinked ancestor, a relpath recorded more than once, or an
#      alias of another recorded path — same inode) —
#      never lifted by --force
#   A dry-run over a PARSED manifest exits 0: it previews what would be
#   removed, preserved or refused. Input-integrity failures happen BEFORE
#   the preview and exit non-zero even under --dry-run: a manifest carrying
#   a NUL byte (6), a manifest that is itself a symlink (6), a --restore
#   tar.gz that is invalid or fails its HMAC check (4).
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
      # The whole header comment, up to the Bash guard — not the first 30
      # lines, which hid the exit codes documented below them.
      sed -n '2,/^# Bash 3.2 portability guard/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'
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
    # rc.1 re-pass round 10 (refuter): an EMPTY SEGMENT is an alias of the
    # same path — `docs/x` and `docs//x` name one inode but are two strings,
    # so the relpath-uniqueness pass below could not see them as one record
    # and the walk acted on both (preserve, then remove). The shared route
    # predicate (_wbm_route_relpath_ok) refuses `//` too; a trailing `/` is
    # the same alias class.
    *//*|*/) return 0 ;;
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

# PLAN-183 §9.8 (S337): remember the directories a removal may have emptied.
#
# rc.1 re-pass round 3, part 3 — this used to remember the TOP-LEVEL component
# and the sweep then ran `find <top> -type d -empty -delete` over the whole
# tree. Removing one framework file under `docs/` therefore deleted every
# empty directory anywhere below `docs/`, including ones the adopter created.
# The claim the sweep makes is "the directories MY deliveries left empty", and
# the only paths that can be is the PARENT CHAIN of a file this run removed.
swept_dirs=""
_track_tree() {
  case "$1" in
    .claude/*) return 0 ;;   # .claude has its own sweep
    */*) ;;
    *) return 0 ;;           # a top-level file leaves no directory behind
  esac
  _tt_dir="${1%/*}"
  while [ -n "$_tt_dir" ] && [ "$_tt_dir" != "." ] && [ "$_tt_dir" != "/" ]; do
    case "
$swept_dirs" in
      *"
$_tt_dir
"*) ;;
      *) swept_dirs="$swept_dirs
$_tt_dir" ;;
    esac
    case "$_tt_dir" in
      */*) _tt_dir="${_tt_dir%/*}" ;;
      *) _tt_dir="" ;;
    esac
  done
}
# The sweep itself: only EMPTY directories go (-empty), so a tree that still
# holds a file of the adopter's — or a PRESERVED delivery — is never touched,
# and trees this run did not remove from are not visited at all. Called on
# BOTH exit paths (complete and incomplete): a partial uninstall that removed
# every docs/ delivery but preserved an edited CODEOWNERS still empties docs/.
_sweep_emptied_trees() {
  # DEEPEST FIRST, so `docs/a/b` is tried before `docs/a` and a chain empties
  # in one pass. `rmdir` on the exact path, never `find -delete` over a tree:
  # rmdir refuses a non-empty directory by itself, so a directory holding
  # anything at all — an adopter's file, a PRESERVED delivery, another
  # adopter-created directory — survives without this code having to reason
  # about it.
  printf '%s\n' "$swept_dirs" \
    | awk 'NF { print gsub(/\//, "/") "\t" $0 }' \
    | sort -rn -k1,1 \
    | cut -f2- \
    | while IFS= read -r _dir; do
        case "$_dir" in ''|.|..|/*|*..*) continue ;; esac   # never leave the target
        [ -d "$TARGET/$_dir" ] || continue
        [ -L "$TARGET/$_dir" ] && continue
        if ! _dry "would REMOVE the empty directory $_dir/"; then
          rmdir "$TARGET/$_dir" 2>/dev/null || true
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

  # rc.1 re-pass (round 7, part 3): the archive is VALIDATED before the
  # dry-run preview, not after it. `--dry-run --restore README.md` used to
  # print "would EXTRACT" and exit 0 for a file that is not a tarball —
  # the help promises exit 4 for an invalid archive BEFORE the preview, and
  # a preview that cannot fail is not a preview. The listing and the
  # .claude-member check need nothing moved aside, so they run first; the
  # rollback helper below tolerates an unset `aside` for exactly that.
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
    exit 4
  fi
  if ! grep -qE '^(\./)?\.claude(/|$)' "$_rst_list"; then
    rm -f "$_rst_list"
    echo "ERROR: the archive carries no .claude/ member — not a ceo-orchestration backup" >&2
    exit 4
  fi

  if _dry "would EXTRACT $RESTORE_PATH into $TARGET ($(grep -c . "$_rst_list") member(s) listed)"; then
    rm -f "$_rst_list"
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

# rc.1 re-pass round 9, part 3: `-f` FOLLOWS a link, so a manifest that is a
# symlink was read THROUGH it — the ledger, the backup list and the removal
# walk all came from bytes at a path nobody validated. The link itself is
# refused (never followed) before anything reads it; exit 6 like every other
# refusal, dry-run included (an input-integrity failure, not a preview).
if [ -L "$MANIFEST" ]; then
  _log "    REFUSED: the install manifest at $MANIFEST is a SYMLINK — this"
  _log "             uninstaller never reads a manifest through a link."
  _log "             NOTHING was removed; the link is left as it stands."
  exit 6
fi

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

# --- rc.1 re-pass round 3, part 3: the NUL preflight ------------------------
# `read -r` on the Bash 3.2 floor this project supports DISCARDS a NUL and
# everything after it in that record, so the per-record `grep [[:cntrl:]]`
# below never sees it: `<valid-sha>  docs/file<NUL>garbage` arrived at the
# parser already truncated to `<valid-sha>  docs/file`, hashed, matched, and
# was deleted — with the manifest removed and the run exiting 0. The reviewer
# reproduced exactly that under 3.2.57. A per-record check cannot see a byte
# that `read` ate; the question has to be asked of the FILE, in raw bytes,
# before anything parses it. Refusing the WHOLE manifest is the only honest
# answer: a NUL means the file is not the text this uninstaller can read, and
# picking the survivors would be deciding which truncation to trust.
if ! LC_ALL=C tr -d '\000' < "$MANIFEST" | cmp -s - "$MANIFEST"; then
  _log "    REFUSED: the manifest contains NUL byte(s) — this uninstaller"
  _log "             cannot read it, and `read` would silently truncate the"
  _log "             affected record(s) into shapes that look valid."
  _log "             NOTHING was removed; the manifest is left as it stands."
  exit 6
fi

# --- rc.1 re-pass round 3, part 3: ONE grammar, parsed ONCE ----------------
# Backup construction and the removal walk used DIFFERENT grammars: the walk
# accepted one OR two spaces after the digest (`  ?`), while the backup list
# only matched records containing two consecutive spaces. A one-space record
# was therefore deleted but never archived — the recovery tarball silently
# missing exactly what the run removed. The canonical grammar is EXACTLY two
# spaces (what the writer emits); it is applied once, here, into a sanitized
# ledger that both the backup and the walk read. No second parser can drift
# from this one because there is no second parser.
_LEDGER="$(mktemp 2>/dev/null || mktemp -t ceo-uninstall-ledger)"
unsafe_count=0
valid_count=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in '#'*|'') continue ;; esac
  if printf '%s' "$line" | LC_ALL=C grep -q '[[:cntrl:]]'; then
    unsafe_count=$((unsafe_count + 1))
    _log "    REFUSED (manifest record carries control bytes — not touched)"
    continue
  fi
  case "$line" in
    LINK\ *)
      # `LINK <relpath> <target>` is what a --link install records; this
      # uninstaller handles copy-mode records only (rc.1 condition): the
      # link stays, the refusal is named and counted.
      unsafe_count=$((unsafe_count + 1))
      _log "    REFUSED (LINK record — copy-mode uninstaller; the link is left in place): ${line#LINK }"
      continue ;;
  esac
  if ! printf '%s' "$line" | LC_ALL=C grep -qE '^[0-9a-f]{64}  [^ ]'; then
    unsafe_count=$((unsafe_count + 1))
    _log "    REFUSED (malformed manifest record — not touched): $line"
    continue
  fi
  _rel="${line#*  }"
  if _rel_unsafe "$_rel"; then
    unsafe_count=$((unsafe_count + 1))
    _log "    REFUSED (unsafe manifest path — not touched): $_rel"
    continue
  fi
  if _rel_ancestor_link "$_rel"; then
    unsafe_count=$((unsafe_count + 1))
    _log "    REFUSED (symlinked ancestor — a removal would follow it outside the target): $_rel"
    continue
  fi
  valid_count=$((valid_count + 1))
  printf '%s\t%s\n' "${line%%  *}" "$_rel" >> "$_LEDGER"
done < "$MANIFEST"

# rc.1 re-pass round 9, part 3: relpath UNIQUENESS across the whole ledger.
# Each record was validated on its own, so a relpath recorded TWICE produced
# two ledger rows and the walk below acts per row: `<old-sha>  docs/x` followed
# by `<current-sha>  docs/x` PRESERVED the adopter's modified file on the first
# row and REMOVED it on the second — without --force, exit 5 only afterwards.
# Ambiguous provenance is refused WHOLE (every occurrence, as doctor.sh does):
# nothing under a duplicated relpath is archived or removed.
_dup_rels="$( cut -f2- "$_LEDGER" | LC_ALL=C sort | LC_ALL=C uniq -d )"
if [ -n "$_dup_rels" ]; then
  _LEDGER_UNIQ="$(mktemp 2>/dev/null || mktemp -t ceo-uninstall-ledger-uniq)"
  while IFS="$( printf '\t' )" read -r _lsha _lrel || [ -n "$_lrel" ]; do
    [ -n "$_lrel" ] || continue
    if printf '%s\n' "$_dup_rels" | LC_ALL=C grep -qxF -- "$_lrel"; then
      unsafe_count=$((unsafe_count + 1))
      valid_count=$((valid_count - 1))
      _log "    REFUSED (relpath recorded more than once — ambiguous provenance, not touched): $_lrel"
      continue
    fi
    printf '%s\t%s\n' "$_lsha" "$_lrel" >> "$_LEDGER_UNIQ"
  done < "$_LEDGER"
  mv -f "$_LEDGER_UNIQ" "$_LEDGER"
fi

# rc.1 re-pass round 10 (refuter): uniqueness by STRING cannot see every alias
# of one inode — an empty segment (`docs//x`), case folding on a
# case-insensitive filesystem (`docs/X`), Unicode normalisation on APFS, or a
# hard link between two recorded paths. Enumerating spellings does not
# converge; IDENTITY does: every ledger relpath that exists is lstat()ed
# (the leaf is never followed) and EVERY relpath whose (st_dev, st_ino)
# appears under more than one spelling is refused before backup and removal.
# The grammar above already refused control bytes, whitespace and glob
# characters, so the relpaths round-trip through python3 byte-exact.
_alias_rels="$(python3 - "$TARGET" "$_LEDGER" <<'PY'
import os, sys
target, ledger = sys.argv[1], sys.argv[2]
seen = {}
with open(ledger, 'r', encoding='utf-8') as fh:
    for line in fh:
        line = line.rstrip('\n')
        if '\t' not in line:
            continue
        rel = line.split('\t', 1)[1]
        try:
            st = os.lstat(os.path.join(target, rel))
        except OSError:
            continue
        seen.setdefault((st.st_dev, st.st_ino), set()).add(rel)
for rels in seen.values():
    if len(rels) > 1:
        for rel in sorted(rels):
            sys.stdout.write(rel + '\n')
PY
)"
if [ -n "$_alias_rels" ]; then
  _LEDGER_IDENT="$(mktemp 2>/dev/null || mktemp -t ceo-uninstall-ledger-ident)"
  while IFS="$( printf '\t' )" read -r _lsha _lrel || [ -n "$_lrel" ]; do
    [ -n "$_lrel" ] || continue
    if printf '%s\n' "$_alias_rels" | LC_ALL=C grep -qxF -- "$_lrel"; then
      unsafe_count=$((unsafe_count + 1))
      valid_count=$((valid_count - 1))
      _log "    REFUSED (relpath is an alias of another recorded path — same inode, ambiguous provenance, not touched): $_lrel"
      continue
    fi
    printf '%s\t%s\n' "$_lsha" "$_lrel" >> "$_LEDGER_IDENT"
  done < "$_LEDGER"
  mv -f "$_LEDGER_IDENT" "$_LEDGER"
fi

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
    # rc.1 re-pass round 3, part 3 — from the SANITIZED LEDGER, which is the
    # same set of records the removal walk below acts on. The path checks that
    # used to be repeated here now live in the single parse; what is left is
    # the archive-specific question of whether the file exists as a regular
    # file right now (`-f` and `tar` follow links, `! -L` tests the leaf).
    cut -f2- "$_LEDGER" 2>/dev/null \
      | while IFS= read -r _brel; do
          case "$_brel" in .claude/*) continue ;; esac
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

# Walk the SANITIZED LEDGER; for each entry, verify SHA before delete.
mismatch_count=0
removed_count=0
preserved_count=0
absent_count=0
mismatch_files=""

# rc.1 re-pass (round 2, part 3): the parse is TOTAL. `read` alone drops an
# unterminated final record (a manifest whose trailing newline was lost never
# processed its last delivery); a record that matched no shape was skipped in
# silence — so an empty, comment-only or malformed manifest left every counter
# at zero, the ledger was DELETED below and the run exited 0 with framework
# files still on disk.
#
# rc.1 re-pass (round 3, part 3): that parse now happens ONCE, above, into
# `$_LEDGER` — the same records the backup archived. What is left here is the
# filesystem question, and it used to fail OPEN on every answer but "regular
# file": a directory or a FIFO at a managed path fell through `continue`
# without touching a counter, so the run could remove the ownership manifest
# and exit 0 with the managed path still there; a dangling symlink counted as
# ABSENT; and a symlink leaf pointing at an external regular file passed `-f`
# and was read THROUGH by the hasher. Every one of those is now REFUSED and
# counted, which keeps the manifest and exits 6.
while IFS="$( printf '\t' )" read -r recorded_sha rel || [ -n "$rel" ]; do
  [ -n "$rel" ] || continue
  fpath="$TARGET/$rel"

  # BEFORE -e, because -e is FALSE for a dangling link and the link would
  # otherwise be filed as "absent" and left behind. A link is never followed:
  # not to test it, not to hash it, not to remove it.
  if [ -L "$fpath" ]; then
    unsafe_count=$((unsafe_count + 1))
    _log "    REFUSED (manifest path is a symlink — never followed, never removed): $rel"
    continue
  fi

  if [ ! -e "$fpath" ]; then
    absent_count=$((absent_count + 1))
    continue
  fi

  if [ ! -f "$fpath" ]; then
    unsafe_count=$((unsafe_count + 1))
    _log "    REFUSED (manifest path exists but is not a regular file — not touched): $rel"
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
done < "$_LEDGER"
rm -f "$_LEDGER"

# No valid record at all (empty, comment-only or wholly malformed manifest) is
# not "everything matched": it is an unreadable ledger, and deleting it would
# erase the only evidence of what was installed.
if [ "$valid_count" -eq 0 ]; then
  unsafe_count=$((unsafe_count + 1))
  _log "    REFUSED (manifest has no valid record — empty, comment-only or malformed; kept for inspection)"
fi

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
  _log "    Refused:   $unsafe_count (unsafe manifest path, symlinked ancestor or relpath recorded more than once — not touched)"
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
  # An INCOMPLETE uninstall is never a success (rc.1 re-pass, part 3 U2):
  # automation that reads only $? must not record a refused or preserved
  # run as done. The dry-run stays 0 — it is a preview (header). Refusal
  # outranks mismatch: a refused record is never lifted by --force.
  if [ "$DRY_RUN" -eq 1 ]; then exit 0; fi
  if [ "$unsafe_count" -gt 0 ]; then exit 6; fi
  exit 5
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
_log "    Refused:   $unsafe_count (unsafe manifest path, symlinked ancestor or relpath recorded more than once — not touched)"
_log "    Manifest:  $([ -f "$MANIFEST" ] && echo "KEPT" || echo "REMOVED")"
exit 0
