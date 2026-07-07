#!/usr/bin/env bash
# scripts/doctor.sh — installed-state diagnostician + selective repair
# (PLAN-153 Wave B item B3)
#
# Diffs an installed target repo against the baseline recorded at install
# time in .claude/.install-manifest.sha256 (written by install.sh
# write_install_manifest / upgrade.sh via _write_baseline_manifest) and
# reports, per manifest record:
#
#   OK        current sha256 == recorded baseline (framework-pristine)
#   DRIFT     file exists, sha256 != baseline (sub-classified against the
#             framework checkout: adopter-modified / baseline-stale / conflict)
#   MISSING   manifest record present, file absent on disk
#   ORPHAN?   file present under a framework-owned directory but NOT in the
#             manifest (candidates only — NEVER removed by this script)
#
# --repair restores drifted/missing files SELECTIVELY from the framework
# checkout this script lives in (SOURCE_DIR resolution mirrors install.sh).
#
# SAFETY INVARIANTS (uninstall.sh depends on these):
#   * uninstall.sh removes ONLY files whose current sha256 matches the
#     manifest record (uninstall.sh:227). doctor.sh preserves that property:
#     a repair copies a file ONLY when the framework source still hashes to
#     the recorded baseline (H_src == H_base), and verifies the restored
#     content re-hashes to the baseline. Post-repair state is therefore
#     exactly the recorded install state.
#   * doctor.sh NEVER writes .claude/.install-manifest.sha256. If the
#     framework checkout has moved past the baseline, repair is BLOCKED for
#     that file and upgrade.sh (which owns baseline rewrites) is advised.
#   * Adopter-modified files are NEVER overwritten without an explicit
#     per-file confirmation: --yes-file <relpath> (repeatable) or an
#     interactive [y/N] prompt when stdin is a TTY. Overwritten files are
#     first backed up to .claude.bak/doctor-<UTC-ts>/<relpath>.
#   * Orphan candidates are report-only. doctor.sh deletes nothing, ever.
#
# Usage:
#   ./doctor.sh <target-repo-path> [options]
#
# Options:
#   --repair             Restore drifted/missing framework files (selective)
#   --dry-run            With --repair: print what WOULD be restored, write
#                        nothing. (Without --repair, report-only is already
#                        the default posture.)
#   --yes-file <rel>     Pre-approve restore of ONE adopter-modified file
#                        (repeatable; exact manifest relpath)
#   --profile <list>     Comma-separated profile list for the orphan scan
#                        (default: auto-detect core,frontend + installed
#                        domain dirs under .claude/skills/domains/)
#   --strict-orphans     Orphan candidates also drive exit code 1
#   --no-orphan-scan     Skip the orphan scan
#   --verbose            Also print OK lines (default: findings only)
#   -h, --help           Show this help
#
# Exit codes:
#   0  clean (no unresolved drift/missing; orphans ignored unless --strict-orphans)
#   1  findings remain after the run (drift/missing, or orphans under --strict-orphans)
#   2  usage error / infrastructure problem (bad args, no manifest, no hasher)
#
# bash 3.2-safe (macOS /bin/bash): no mapfile, no associative arrays.

# Bash portability guard (mirrors uninstall.sh:30-38).
if [ -z "${BASH_VERSINFO:-}" ]; then
  echo "ERROR: doctor.sh requires bash" >&2
  exit 2
fi
if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
  echo "ERROR: doctor.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
  exit 2
fi

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
TARGET=""
REPAIR=0
DRY_RUN=0
PROFILE=""
STRICT_ORPHANS=0
NO_ORPHAN_SCAN=0
VERBOSE=0
YES_FILES="
"   # newline-delimited set of pre-approved relpaths (bash-3.2 "set" idiom)

usage() {
  # Header spans line 2 .. the "bash 3.2-safe" sentinel line (keep in sync).
  sed -n '2,59p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repair)          REPAIR=1; shift ;;
    --dry-run)         DRY_RUN=1; shift ;;
    --yes-file)
      if [ -z "${2:-}" ]; then
        echo "ERROR: --yes-file requires a relpath argument" >&2
        exit 2
      fi
      YES_FILES="${YES_FILES}${2}
"
      shift 2 ;;
    --yes-file=*)
      YES_FILES="${YES_FILES}${1#--yes-file=}
"
      shift ;;
    --profile)
      if [ -z "${2:-}" ]; then
        echo "ERROR: --profile requires a comma-separated list" >&2
        exit 2
      fi
      PROFILE="$2"; shift 2 ;;
    --profile=*)       PROFILE="${1#--profile=}"; shift ;;
    --strict-orphans)  STRICT_ORPHANS=1; shift ;;
    --no-orphan-scan)  NO_ORPHAN_SCAN=1; shift ;;
    --verbose)         VERBOSE=1; shift ;;
    -h|--help)         usage; exit 0 ;;
    -*)
      echo "ERROR: unknown option: $1" >&2
      echo "Usage: $0 <target-repo-path> [--repair] [--dry-run] [--yes-file <rel>]..." >&2
      exit 2 ;;
    *)
      if [ -n "$TARGET" ]; then
        echo "ERROR: multiple target paths given ('$TARGET' and '$1')" >&2
        exit 2
      fi
      TARGET="$1"; shift ;;
  esac
done

if [ -z "$TARGET" ]; then
  echo "Usage: $0 <target-repo-path> [--repair] [--dry-run] [--yes-file <rel>]..." >&2
  exit 2
fi
if [ ! -d "$TARGET" ]; then
  echo "ERROR: target directory does not exist: $TARGET" >&2
  exit 2
fi
TARGET="$( cd "$TARGET" && pwd )"

# ---------------------------------------------------------------------------
# Resolve SCRIPT_DIR / SOURCE_DIR (mirrors install.sh:178-204 so doctor's
# restore source is the SAME framework checkout install.sh would copy from,
# including when invoked via a symlink).
# ---------------------------------------------------------------------------
_resolve_script_path() {
  local src="$1"
  if command -v readlink >/dev/null 2>&1; then
    local resolved
    if resolved="$(readlink -f "$src" 2>/dev/null)" && [ -n "$resolved" ]; then
      printf '%s\n' "$resolved"
      return 0
    fi
    while [ -L "$src" ]; do
      local link_target
      link_target="$(readlink "$src")"
      case "$link_target" in
        /*) src="$link_target" ;;
        *)  src="$(cd "$(dirname "$src")" && pwd)/$link_target" ;;
      esac
    done
  fi
  printf '%s\n' "$src"
}

SCRIPT_SRC="$(_resolve_script_path "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_SRC" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# _hash_lib.sh is REQUIRED — without a portable hasher every verdict here
# would be a guess. Fail-closed to rc=2 (infra), matching the exit contract.
if [ ! -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
  echo "ERROR: $SCRIPT_DIR/_hash_lib.sh not found — partial checkout? doctor cannot hash." >&2
  exit 2
fi
# shellcheck source=scripts/_hash_lib.sh
. "$SCRIPT_DIR/_hash_lib.sh"
if ! _hash_resolver >/dev/null 2>&1; then
  echo "ERROR: neither shasum nor sha256sum found on PATH — doctor cannot hash." >&2
  exit 2
fi

# _framework_manifest_set.sh is OPTIONAL — only the orphan scan needs it.
HAVE_FMS=0
if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
  # shellcheck source=scripts/_framework_manifest_set.sh
  . "$SCRIPT_DIR/_framework_manifest_set.sh"
  HAVE_FMS=1
fi

MANIFEST="$TARGET/.claude/.install-manifest.sha256"
if [ ! -f "$MANIFEST" ]; then
  echo "ERROR: install manifest not found at $MANIFEST" >&2
  echo "       This target has no recorded baseline (pre-PLAN-138 install?)." >&2
  echo "       Run upgrade.sh once to (re)generate it, then re-run doctor." >&2
  exit 2
fi

WORKDIR="$( mktemp -d -t ceo-doctor-XXXXXX )"
cleanup() { [ -n "${WORKDIR:-}" ] && rm -rf "$WORKDIR" 2>/dev/null || true; }
trap cleanup EXIT

_log() { printf '%s\n' "$*"; }

_log "==> ceo-orchestration doctor"
_log "    Target:   $TARGET"
_log "    Source:   $SOURCE_DIR"
_log "    Manifest: $MANIFEST"
_log "    Mode:     $( if [ "$REPAIR" -eq 1 ]; then
                         if [ "$DRY_RUN" -eq 1 ]; then echo "repair (dry-run)"; else echo "repair"; fi
                       else echo "report-only"; fi )"
_log ""

# ---------------------------------------------------------------------------
# Manifest sanitization (mirrors upgrade.sh _load_baseline_manifest:435-526:
# accept only the two record grammars; reject absolute / traversal /
# control-char relpaths; reject duplicate relpaths ENTIRELY — ambiguous
# provenance. One divergence, on purpose: for LINK records the LEAF is
# allowed to be a symlink (that is what a link record describes); only
# INTERMEDIATE symlinked components are rejected. upgrade.sh's checker also
# rejects a symlinked leaf, which is fine there because LINK records
# short-circuit its lookup — here we must actually verify links.)
# ---------------------------------------------------------------------------
SANITIZED="$WORKDIR/manifest.sanitized"
: > "$SANITIZED"
_DUP_GUARD="
"
_INVALID="
"

# Reject an unsafe relpath. $2 = "link" to allow a symlinked LEAF.
_relpath_unsafe() {
  _ru_rel="$1"
  _ru_kind="${2:-file}"
  case "$_ru_rel" in
    ''|/*) return 0 ;;
    *..*)  return 0 ;;
  esac
  case "$_ru_rel" in
    *[$'\n\r\t']*) return 0 ;;
  esac
  _ru_parent="$( dirname "$_ru_rel" )"
  _ru_cur="$TARGET"
  _ru_oldIFS="$IFS"
  IFS='/'
  # shellcheck disable=SC2086  # intentional word-split on the relpath components
  for _ru_comp in $_ru_parent; do
    [ -n "$_ru_comp" ] || continue
    [ "$_ru_comp" = "." ] && continue
    _ru_cur="$_ru_cur/$_ru_comp"
    if [ -L "$_ru_cur" ]; then
      IFS="$_ru_oldIFS"
      return 0
    fi
  done
  IFS="$_ru_oldIFS"
  # Codex pair-rail P2 (S261): a symlinked LEAF is NOT a traversal risk and
  # must NOT be filtered out here — dropping the record makes doctor exit
  # clean while a managed regular-file path has been swapped for a symlink.
  # It is a type-change: the diagnosis loop reports it as
  # `DRIFT (type-change: regular file recorded, non-file found)` and repair
  # refuses to follow it (leaf `-L` guard at the repair site). Only
  # symlinked PARENT components (the loop above) are a genuine traversal
  # hazard and stay filtered.
  return 1
}

_seen_before() {
  case "$_DUP_GUARD" in
    *"
$1
"*) return 0 ;;
  esac
  return 1
}

_mark_seen()    { _DUP_GUARD="${_DUP_GUARD}${1}
"; }
_mark_invalid() {
  case "$_INVALID" in
    *"
$1
"*) : ;;
    *) _INVALID="${_INVALID}${1}
" ;;
  esac
}

while IFS= read -r line || [ -n "$line" ]; do
  [ -n "$line" ] || continue
  case "$line" in
    '#'*) continue ;;
    LINK\ \ *)
      rest="${line#LINK  }"
      case "$rest" in
        *"  "*)
          rel="${rest%%  *}"
          target="${rest#*  }"
          ;;
        *) continue ;;   # malformed LINK (no target) — drop
      esac
      case "$target" in
        ''|*[$'\n\r\t']*) continue ;;
      esac
      if _relpath_unsafe "$rel" link; then continue; fi
      if _seen_before "$rel"; then _mark_invalid "$rel"; continue; fi
      _mark_seen "$rel"
      printf 'LINK  %s  %s\n' "$rel" "$target" >> "$SANITIZED"
      ;;
    *)
      digest="${line%%  *}"
      rel="${line#*  }"
      [ "$digest" != "$line" ] || continue
      case "$digest" in
        *[!0-9a-f]*) continue ;;
      esac
      [ "${#digest}" -eq 64 ] || continue
      if _relpath_unsafe "$rel" file; then continue; fi
      if _seen_before "$rel"; then _mark_invalid "$rel"; continue; fi
      _mark_seen "$rel"
      printf '%s  %s\n' "$digest" "$rel" >> "$SANITIZED"
      ;;
  esac
done < "$MANIFEST"

# Second pass: drop records for relpaths flagged ambiguous (dup) — they were
# emitted on first sight before the dup was discovered.
if [ "$_INVALID" != "
" ]; then
  : > "$SANITIZED.f"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      LINK\ \ *) rel_probe="${line#LINK  }"; rel_probe="${rel_probe%%  *}" ;;
      *)         rel_probe="${line#*  }" ;;
    esac
    case "$_INVALID" in
      *"
$rel_probe
"*) continue ;;
    esac
    printf '%s\n' "$line" >> "$SANITIZED.f"
  done < "$SANITIZED"
  mv "$SANITIZED.f" "$SANITIZED"
fi

if [ ! -s "$SANITIZED" ]; then
  echo "ERROR: manifest at $MANIFEST contains no valid records after sanitization." >&2
  echo "       It may be corrupted. Run upgrade.sh to regenerate the baseline." >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Repair helpers
# ---------------------------------------------------------------------------
BAK_DIR=""   # created lazily on the first backup
_ensure_bak_dir() {
  if [ -z "$BAK_DIR" ]; then
    BAK_DIR="$TARGET/.claude.bak/doctor-$(date -u +%Y%m%d-%H%M%SZ)"
    mkdir -p "$BAK_DIR"
  fi
}

_backup_file() {
  # $1 = relpath of an existing regular file to preserve before overwrite.
  _bf_rel="$1"
  _ensure_bak_dir
  mkdir -p "$BAK_DIR/$( dirname "$_bf_rel" )"
  cp -p "$TARGET/$_bf_rel" "$BAK_DIR/$_bf_rel"
}

# Per-file confirmation: --yes-file match, else interactive [y/N] on a TTY,
# else refuse (0 = confirmed, 1 = not confirmed).
_confirmed() {
  _cf_rel="$1"
  case "$YES_FILES" in
    *"
$_cf_rel
"*) return 0 ;;
  esac
  if [ -t 0 ] && [ -r /dev/tty ]; then
    printf '    restore %s (overwrites your modified copy; backup taken)? [y/N] ' "$_cf_rel"
    _cf_ans=""
    read -r _cf_ans < /dev/tty || _cf_ans=""
    case "$_cf_ans" in
      y|Y|yes|YES) return 0 ;;
    esac
  fi
  return 1
}

# Restore one hash-record file from SOURCE_DIR. Preconditions already checked
# by the caller: source exists AND H_src == H_base, and DRY_RUN handled by the
# caller (a dry-run preview leaves the finding UNRESOLVED — the disk still
# drifts, so the exit code must stay 1). $1=rel $2=base-digest.
# Returns 0 on verified restore, 1 otherwise.
_restore_file() {
  _rf_rel="$1"
  _rf_base="$2"
  mkdir -p "$TARGET/$( dirname "$_rf_rel" )"
  cp -p "$SOURCE_DIR/$_rf_rel" "$TARGET/$_rf_rel"
  # Post-copy verification: the restored content MUST re-hash to the recorded
  # baseline, or the uninstall SHA-identical property would silently not hold
  # (TOCTOU on the source between classify and copy).
  _rf_after="$( _hash_file "$TARGET/$_rf_rel" 2>/dev/null || true )"
  if [ "$_rf_after" = "$_rf_base" ]; then
    _log "    RESTORED: $_rf_rel"
    return 0
  fi
  _log "    RESTORE-FAILED (post-copy hash != baseline — source changed mid-run?): $_rf_rel"
  return 1
}

# ---------------------------------------------------------------------------
# Main verification loop
# ---------------------------------------------------------------------------
OK_COUNT=0
DRIFT_COUNT=0
MISSING_COUNT=0
REPAIRED_COUNT=0
WOULD_REPAIR=0
SKIPPED_CONFIRM=0
BLOCKED_COUNT=0
UNRESOLVED=0
ORPHAN_COUNT=0

_log "==> Verifying $( wc -l < "$SANITIZED" | tr -d ' ' ) manifest records"

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    LINK\ \ *)
      rest="${line#LINK  }"
      rel="${rest%%  *}"
      target="${rest#*  }"
      lpath="$TARGET/$rel"
      if [ -L "$lpath" ]; then
        cur_target="$( readlink "$lpath" 2>/dev/null || true )"
        if [ "$cur_target" = "$target" ]; then
          OK_COUNT=$((OK_COUNT + 1))
          [ "$VERBOSE" -eq 1 ] && _log "    OK (link): $rel"
          continue
        fi
      fi
      if [ ! -e "$lpath" ] && [ ! -L "$lpath" ]; then
        MISSING_COUNT=$((MISSING_COUNT + 1))
        _log "    MISSING (link): $rel -> $target"
        if [ "$REPAIR" -eq 1 ]; then
          if [ "$DRY_RUN" -eq 1 ]; then
            _log "    (dry-run) would RE-LINK: $rel -> $target"
            WOULD_REPAIR=$((WOULD_REPAIR + 1))
            UNRESOLVED=$((UNRESOLVED + 1))
          else
            mkdir -p "$TARGET/$( dirname "$rel" )"
            if ln -s "$target" "$lpath" 2>/dev/null; then
              _log "    RE-LINKED: $rel -> $target"
              REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
              [ -e "$lpath" ] || _log "    NOTE: link target does not exist (broken link recreated as recorded): $target"
            else
              _log "    RESTORE-FAILED (ln -s failed): $rel"
              UNRESOLVED=$((UNRESOLVED + 1))
            fi
          fi
        else
          UNRESOLVED=$((UNRESOLVED + 1))
        fi
        continue
      fi
      # Present but wrong: retargeted symlink, or a regular file replaced it.
      DRIFT_COUNT=$((DRIFT_COUNT + 1))
      _log "    DRIFT (link: expected -> $target): $rel"
      if [ "$REPAIR" -eq 1 ]; then
        if _confirmed "$rel"; then
          if [ "$DRY_RUN" -eq 1 ]; then
            _log "    (dry-run) would RE-LINK (replacing current): $rel -> $target"
            WOULD_REPAIR=$((WOULD_REPAIR + 1))
            UNRESOLVED=$((UNRESOLVED + 1))
          else
            if [ -f "$lpath" ] && [ ! -L "$lpath" ]; then
              _backup_file "$rel"
              _log "    BACKED-UP: $rel -> $BAK_DIR/$rel"
            fi
            rm -f "$lpath"
            if ln -s "$target" "$lpath" 2>/dev/null; then
              _log "    RE-LINKED: $rel -> $target"
              REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
            else
              _log "    RESTORE-FAILED (ln -s failed): $rel"
              UNRESOLVED=$((UNRESOLVED + 1))
            fi
          fi
        else
          SKIPPED_CONFIRM=$((SKIPPED_CONFIRM + 1))
          UNRESOLVED=$((UNRESOLVED + 1))
          _log "    SKIPPED (needs --yes-file '$rel' or interactive confirm): $rel"
        fi
      else
        UNRESOLVED=$((UNRESOLVED + 1))
      fi
      ;;
    *)
      base="${line%%  *}"
      rel="${line#*  }"
      fpath="$TARGET/$rel"

      if [ ! -e "$fpath" ] && [ ! -L "$fpath" ]; then
        MISSING_COUNT=$((MISSING_COUNT + 1))
        src_hash="$( _hash_file "$SOURCE_DIR/$rel" 2>/dev/null || true )"
        if [ -z "$src_hash" ]; then
          _log "    MISSING (framework checkout no longer ships this file): $rel"
          BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
          UNRESOLVED=$((UNRESOLVED + 1))
        elif [ "$src_hash" != "$base" ]; then
          _log "    MISSING (framework source diverged from baseline — run upgrade.sh): $rel"
          BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
          UNRESOLVED=$((UNRESOLVED + 1))
        else
          _log "    MISSING (restorable): $rel"
          if [ "$REPAIR" -eq 1 ]; then
            if [ "$DRY_RUN" -eq 1 ]; then
              _log "    (dry-run) would RESTORE: $rel"
              WOULD_REPAIR=$((WOULD_REPAIR + 1))
              UNRESOLVED=$((UNRESOLVED + 1))
            elif _restore_file "$rel" "$base"; then
              REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
            else
              UNRESOLVED=$((UNRESOLVED + 1))
            fi
          else
            UNRESOLVED=$((UNRESOLVED + 1))
          fi
        fi
        continue
      fi

      if [ -L "$fpath" ] || [ ! -f "$fpath" ]; then
        # Hash record but the path is now a symlink / non-regular file. Never
        # hash-through or repair-through it (symlink write-through escape).
        DRIFT_COUNT=$((DRIFT_COUNT + 1))
        BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
        UNRESOLVED=$((UNRESOLVED + 1))
        _log "    DRIFT (type-change: regular file recorded, non-file found — not repairable): $rel"
        continue
      fi

      cur="$( _hash_file "$fpath" 2>/dev/null || true )"
      if [ "$cur" = "$base" ]; then
        OK_COUNT=$((OK_COUNT + 1))
        [ "$VERBOSE" -eq 1 ] && _log "    OK: $rel"
        continue
      fi

      DRIFT_COUNT=$((DRIFT_COUNT + 1))
      src_hash="$( _hash_file "$SOURCE_DIR/$rel" 2>/dev/null || true )"
      if [ -z "$src_hash" ]; then
        _log "    DRIFT (framework checkout no longer ships this file — not repairable): $rel"
        BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
        UNRESOLVED=$((UNRESOLVED + 1))
      elif [ "$cur" = "$src_hash" ]; then
        _log "    DRIFT (baseline-stale: file matches CURRENT framework; run upgrade.sh to refresh the baseline): $rel"
        BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
        UNRESOLVED=$((UNRESOLVED + 1))
      elif [ "$src_hash" = "$base" ]; then
        _log "    DRIFT (adopter-modified): $rel"
        if [ "$REPAIR" -eq 1 ]; then
          if _confirmed "$rel"; then
            if [ "$DRY_RUN" -eq 1 ]; then
              _log "    (dry-run) would BACKUP + RESTORE: $rel"
              WOULD_REPAIR=$((WOULD_REPAIR + 1))
              UNRESOLVED=$((UNRESOLVED + 1))
            else
              _backup_file "$rel"
              _log "    BACKED-UP: $rel -> $BAK_DIR/$rel"
              if _restore_file "$rel" "$base"; then
                REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
              else
                UNRESOLVED=$((UNRESOLVED + 1))
              fi
            fi
          else
            SKIPPED_CONFIRM=$((SKIPPED_CONFIRM + 1))
            UNRESOLVED=$((UNRESOLVED + 1))
            _log "    SKIPPED (needs --yes-file '$rel' or interactive confirm): $rel"
          fi
        else
          UNRESOLVED=$((UNRESOLVED + 1))
        fi
      else
        _log "    DRIFT (conflict: file AND framework both diverged from baseline — run upgrade.sh): $rel"
        BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
        UNRESOLVED=$((UNRESOLVED + 1))
      fi
      ;;
  esac
done < "$SANITIZED"

# ---------------------------------------------------------------------------
# Orphan scan (report-only): files present under the framework-owned
# enumeration (_framework_manifest_set.sh, FMS_ROOT=$TARGET) with NO manifest
# record. Candidates ONLY — they may be adopter-authored; never removed.
# ---------------------------------------------------------------------------
if [ "$NO_ORPHAN_SCAN" -eq 0 ]; then
  if [ "$HAVE_FMS" -eq 1 ]; then
    if [ -n "$PROFILE" ]; then
      PROFILE_PARTS_STR="$( printf '%s' "$PROFILE" | tr ',' ' ' )"
    else
      # Auto-detect: core + frontend (absent dirs are skipped by the
      # enumerator) + every installed domain dir.
      PROFILE_PARTS_STR="core frontend"
      if [ -d "$TARGET/.claude/skills/domains" ]; then
        for d in "$TARGET/.claude/skills/domains"/*/; do
          [ -d "$d" ] || continue
          PROFILE_PARTS_STR="$PROFILE_PARTS_STR $( basename "$d" )"
        done
      fi
    fi
    export FMS_ROOT="$TARGET"
    export FMS_PROFILE_PARTS="$PROFILE_PARTS_STR"
    _framework_manifest_files > "$WORKDIR/enumerated" 2>/dev/null || : > "$WORKDIR/enumerated"
    unset FMS_ROOT FMS_PROFILE_PARTS
    # Manifest relpaths (both record kinds).
    awk '{
      idx = index($0, "  ");
      if (idx == 0) next;
      d = substr($0, 1, idx - 1);
      rest = substr($0, idx + 2);
      if (d == "LINK") { j = index(rest, "  "); if (j > 0) rest = substr(rest, 1, j - 1) }
      print rest;
    }' "$SANITIZED" | LC_ALL=C sort -u > "$WORKDIR/manifest-rels"
    LC_ALL=C sort -u "$WORKDIR/enumerated" > "$WORKDIR/enumerated.sorted"
    comm -23 "$WORKDIR/enumerated.sorted" "$WORKDIR/manifest-rels" > "$WORKDIR/orphans" || : > "$WORKDIR/orphans"
    if [ -s "$WORKDIR/orphans" ]; then
      _log ""
      _log "==> Orphan candidates (present in framework-owned dirs, absent from manifest;"
      _log "    possibly adopter-authored — REPORT-ONLY, nothing is removed):"
      while IFS= read -r orel; do
        [ -n "$orel" ] || continue
        ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
        _log "    ORPHAN?: $orel"
      done < "$WORKDIR/orphans"
    fi
  else
    _log "    NOTE: orphan scan skipped — _framework_manifest_set.sh not found beside doctor.sh"
  fi
fi

# ---------------------------------------------------------------------------
# Summary + exit code
# ---------------------------------------------------------------------------
_log ""
_log "==> Doctor summary:"
_log "    OK:        $OK_COUNT"
_log "    Drift:     $DRIFT_COUNT"
_log "    Missing:   $MISSING_COUNT"
if [ "$REPAIR" -eq 1 ] && [ "$DRY_RUN" -eq 1 ]; then
  _log "    Repaired:  0 (dry-run: $WOULD_REPAIR would be repaired; nothing written)"
else
  _log "    Repaired:  $REPAIRED_COUNT"
fi
_log "    Skipped:   $SKIPPED_CONFIRM (awaiting per-file confirm)"
_log "    Blocked:   $BLOCKED_COUNT (baseline/framework divergence — use upgrade.sh)"
_log "    Orphans:   $ORPHAN_COUNT (candidates, report-only)"
if [ -n "$BAK_DIR" ]; then
  _log "    Backups:   $BAK_DIR"
fi

if [ "$UNRESOLVED" -gt 0 ]; then
  exit 1
fi
if [ "$STRICT_ORPHANS" -eq 1 ] && [ "$ORPHAN_COUNT" -gt 0 ]; then
  exit 1
fi
exit 0
