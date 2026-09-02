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
#   * Every write under the target (restore, backup, re-link) is answered
#     first by the destination-confinement predicate the installer and the
#     upgrader use (_wbm_dst_refuses, PLAN-185 / PLAN-185-FOLLOWUP FU-7): a
#     symlinked or hard-linked destination, a symlinked ancestor, or a path
#     that resolves outside the target is REFUSED by name and nothing is
#     written — a refusal counts as an unresolved finding (exit 1).
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
  # rail r2 (S337) P3: terminate at the sentinel, not at a line number — the
  # header grows and a fixed range silently truncates the exit-code section.
  sed -n '2,/^# bash 3\.2-safe/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

# _framework_manifest_set.sh is REQUIRED (PLAN-183 W6). It has TWO consumers
# here now: the orphan scan (framework-owned enumeration) and — since W6 — the
# ONE validated reader of scripts/delivery-routes.tsv. doctor used to carry its
# own copy of that parser; the copy WAS the defect (see the delivery-route
# section below), so there is no longer anything to degrade to. Falling back to
# identity resolution is D4 returning, and D4 does not merely misclassify: it
# REPAIRS with the wrong bytes. Fail-closed to rc=2 (infra), mirroring the
# _hash_lib.sh treatment above.
if [ ! -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
  echo "ERROR: $SCRIPT_DIR/_framework_manifest_set.sh not found — partial checkout?" >&2
  echo "       doctor resolves every delivery route through that library; without" >&2
  echo "       it a repair would fall back to identity and copy the WRONG source." >&2
  exit 2
fi
# shellcheck source=scripts/_framework_manifest_set.sh
. "$SCRIPT_DIR/_framework_manifest_set.sh"
# Presence of the FILE is not presence of the CONTRACT. Assert the three route
# functions BY NAME, so an upstream rename fails HERE, loudly, instead of
# silently taking the identity path at the first repair. _wbm_route_row_ok is
# asserted even though doctor never calls it directly: it is what makes
# _wbm_route_src fail-closed, and a reader missing it would answer rc=2 to
# everything. (The S327 rail round paid this exact lesson on the manifest
# oracle's own fragment harness.)
# rail round-6 F2 added _wbm_route_table_gate to that set: the three readers
# call it, so a library missing it would answer rc=2 to every lookup — the
# right posture, reached the wrong way and with no name attached to it.
# rail round-7 F2 added _wbm_source_confined for the same reason: _restore_file
# COPIES from "$SOURCE_DIR/$src", and a library without that predicate would
# copy through a symlinked source without anything saying so. rail round-8
# widened that to the THREE sites that resolve a source — the write site and
# both HASH sites — so this name is now load-bearing for CLASSIFICATION too,
# not only for the copy.
# PLAN-185-FOLLOWUP FU-7 (S337) added _wbm_dst_refuses: every write doctor
# makes under the target (restore, backup, re-link) is now answered by the SAME
# destination-confinement predicate install.sh and upgrade.sh consume, so a
# library without it must fail here, by name, instead of letting doctor fall
# back to the retired local copy.
for _fms_req in _wbm_route_src _wbm_route_relpath_ok _wbm_route_row_ok \
                _wbm_route_table_ok _wbm_route_table_gate _wbm_source_confined \
                _wbm_dst_refuses; do
  if ! command -v "$_fms_req" >/dev/null 2>&1; then
    echo "ERROR: $SCRIPT_DIR/_framework_manifest_set.sh does not define $_fms_req —" >&2
    echo "       the shared delivery-route reader is unavailable. Refusing to run" >&2
    echo "       rather than resolve delivery routes by identity (defect D4)." >&2
    exit 2
  fi
done
unset _fms_req

# rail round-4 F3 — the READER being present is not the TABLE being present.
# _wbm_route_src answers rc=1 ("no row for this destination") when the table is
# missing or unreadable, and every call site below answers rc=1 with the
# identity fallback `$SOURCE_DIR/$rel`. On a partial checkout that is defect D4
# arriving through an absent file instead of a wrong branch — and D4 does not
# merely misclassify: `_restore_file` COPIES. MEASURED pre-cure (S327): with
# the table removed, `--repair` of a deleted `docs/BRANCH-PROTECTION.md` wrote
# the ROOT homonym's bytes into the adopter tree, and the same path applied to
# `.github/CODEOWNERS` copies THIS repo's live maintainer file — the exact
# contamination class PLAN-183 A3 closed elsewhere.
#
# So the table is a REQUIRED input, asserted once, before any verdict is
# computed. Fail-closed rc=2 (infra), mirroring _hash_lib.sh and the library
# itself above. The shape question is answered by the table's OWNER
# (_wbm_route_table_ok); doctor parsing a header here would be the private copy
# W6 deleted.
#
# rc=1 from _wbm_route_src keeps its meaning — "no route declared for this
# path" — but now only for a path genuinely absent from a table that IS there.
# Rail r8 (S327, P2): call the MEMOIZED gate so the parent process seeds the
# memo — every later _wbm_route_src runs inside a command substitution and would
# otherwise rescan the table once per manifest record.
if ! _wbm_route_table_gate; then
  echo "ERROR: the shared delivery-route table is unusable — ${_WBM_ROUTE_TABLE_WHY:-unknown reason}." >&2
  echo "       doctor resolves every delivery route through that table; without it" >&2
  echo "       a repair would fall back to identity and copy the WRONG source" >&2
  echo "       (defect D4). Refusing to run rather than verify or repair blind." >&2
  echo "       Expected scripts/delivery-routes.tsv next to the manifest library," >&2
  echo "       readable, with its dest/src/transform header and at least one row." >&2
  exit 2
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
BAK_DIR=""       # created lazily on the first backup
BAK_REL_DIR=""   # its relpath under $TARGET — the confinement predicate walks relpaths
_ensure_bak_rel() {
  if [ -z "$BAK_REL_DIR" ]; then
    BAK_REL_DIR=".claude.bak/doctor-$(date -u +%Y%m%d-%H%M%SZ)"
  fi
}
_ensure_bak_dir() {
  _ensure_bak_rel
  if [ -z "$BAK_DIR" ]; then
    BAK_DIR="$TARGET/$BAK_REL_DIR"
    mkdir -p "$BAK_DIR"
  fi
}

_backup_file() {
  # $1 = relpath of an existing regular file to preserve before overwrite.
  # Returns 0 when the backup landed, 1 when it was REFUSED (nothing written):
  # a caller must never overwrite a file whose backup could not be made.
  _bf_rel="$1"
  # PLAN-185-FOLLOWUP FU-7 (S337): the backup destination is a write under the
  # target too, and nothing sanitised it at ingest — `.claude.bak` is not a
  # manifest record. A symlink planted there sends the ADOPTER'S OWN bytes
  # outside the target through `mkdir -p` + `cp -p` (e2e D.2 reproduces it
  # against the pre-cure copy). Same shared predicate as every other write,
  # asked about the relpath that will be written, BEFORE _ensure_bak_dir's own
  # mkdir: the timestamped directory does not exist yet, so the walk covers
  # `.claude.bak` and the nearest existing ancestor.
  _ensure_bak_rel
  if _wbm_dst_refuses "$TARGET" "$BAK_REL_DIR/$_bf_rel"; then
    REFUSED_COUNT=$((REFUSED_COUNT + 1))
    _log "    BACKUP-BLOCKED (destination refused — nothing written: ${_WBM_DST_REFUSE_WHY:-unknown reason}): $_bf_rel"
    return 1
  fi
  _ensure_bak_dir
  mkdir -p "$BAK_DIR/$( dirname "$_bf_rel" )"
  cp -p "$TARGET/$_bf_rel" "$BAK_DIR/$_bf_rel"
}

# PLAN-185-FOLLOWUP FU-7 (S337): confinement for LINK-record repairs. A LINK
# record's LEAF is legitimately a symlink (that is what the record describes),
# so when the leaf is present and about to be replaced, the shared predicate is
# asked about the PARENT the link is created in — a symlinked or escaping
# ancestor is the write-through hazard; the leaf itself is replaced (`rm -f`
# never follows a link), not written through. When the leaf is absent, the full
# relpath is asked, exactly as for a regular file. $1 = link relpath.
# Returns 0 to REFUSE (the polarity of _restore_refuses).
_link_dst_refuses() {
  _ld_rel="$1"
  # rail r1 (S337) P1: the shared predicate refuses a SYMLINKED target root for
  # every relpath it is asked about, and doctor resolves $TARGET logically
  # (`cd && pwd`, symlink preserved) — so a root-level link whose parent IS the
  # root must not skip that clause. Same test, same message, same recovery.
  if [ -L "$TARGET" ]; then
    REFUSED_COUNT=$((REFUSED_COUNT + 1))
    _ld_ref="$( cd -P "$TARGET" 2>/dev/null && pwd -P || true )"
    _log "    RESTORE-BLOCKED (link destination refused — nothing written: the target root '$TARGET' is a SYMLINK${_ld_ref:+ to '$_ld_ref'} — every write would follow it; re-run against the referent): $_ld_rel"
    return 0
  fi
  _ld_ask="$_ld_rel"
  if [ -e "$TARGET/$_ld_rel" ] || [ -L "$TARGET/$_ld_rel" ]; then
    _ld_ask="$( dirname "$_ld_rel" )"
    case "$_ld_ask" in
      .|"") return 1 ;;   # root-level link: the (non-symlink) target root is the parent
    esac
  fi
  if _wbm_dst_refuses "$TARGET" "$_ld_ask"; then
    REFUSED_COUNT=$((REFUSED_COUNT + 1))
    _log "    RESTORE-BLOCKED (link destination refused — nothing written: ${_WBM_DST_REFUSE_WHY:-unknown reason}): $_ld_rel"
    return 0
  fi
  return 1
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

# ---------------------------------------------------------------------------
# Delivery-route resolution (PLAN-183 W5 defect D4; consolidated in W6)
# ---------------------------------------------------------------------------
# Truth: scripts/delivery-routes.tsv. READER: _wbm_route_src, in
# scripts/_framework_manifest_set.sh, sourced above — the SAME reader install.sh,
# upgrade.sh and scripts/tests/_parity_classify.py resolve through. doctor is the
# fourth consumer, and until W6 it was the odd one out: it carried a PRIVATE copy
# of the parser.
#
# What the copy cost, MEASURED (pair-rail round 1, finding F2 — S327): the
# canonical reader had grown path validation the copy never received, so a route
# table with an absolute or `..`-bearing `src` resolved rc=0 here and reached
# `cp "$SOURCE_DIR/$src"` in _restore_file — a read from OUTSIDE the framework
# checkout, delivered into an adopter tree as framework content. The second
# implementation was the defect, not a convenience: it is the same class
# CLAUDE.md §4 records closing twice already (PLAN-182, 16 modules -> one
# resolver; PLAN-167, _ownership_verdict).
#
# The contract the three call sites below depend on is the canonical one, and it
# is byte-for-byte the contract doctor's retired copy published:
#   stdout = source relpath, exit 0 : identity route — hashable and copyable
#   exit 1                          : no route declared — identity applies
#   exit 2                          : RENDERED, malformed, or a REJECTED
#                                     (hostile) row — the delivered bytes exist
#                                     in NO checkout; nothing to hash, nothing
#                                     to copy.
# rc=2 must never collapse into rc=1: rc=1 is answered by the identity fallback,
# which is exactly D4 coming back.
#
# Table location: resolved by the READER, next to the library it ships in
# (rail round-6 F3 removed the environment channel entirely). doctor's own
# DELIVERY_ROUTES_TSV was RETIRED in W6. A second knob the reader does not
# honour is worse than none: a caller could poison a table nobody reads and see
# a green run for it.

# Last gate before anything touches the filesystem. Returns 0 to REFUSE — the
# polarity of upgrade.sh's _up_tpl_confined_refuses / _up_tpl_symlink_refuses,
# deliberately, so the two files read as a pair; keep them consistent when
# either changes. $1 = destination relpath, $2 = resolved source relpath.
#
# The route reader already rejects a hostile row, and doctor's manifest
# sanitiser (_relpath_unsafe, above) already screens every destination at
# INGEST. Neither of those is a property of THIS write: the table is a FILE and
# a partial checkout or a tampered tree still reaches these fields, the
# sanitiser ran before the whole verification loop (a symlink planted in
# between is a real TOCTOU window), and this is the LAST place before `cp`.
# Belt and braces, on BOTH halves of the copy:
#   1. LEXICAL — the reader's own predicate, applied to the destination AND to
#      the source relpath that will be appended to $SOURCE_DIR.
#   2. SYMLINK — never write THROUGH a link: refuse a symlinked leaf and any
#      symlinked ancestor component.
#   3. PHYSICAL — the deepest EXISTING ancestor of the destination must resolve
#      (cd -P/pwd -P; the bash 3.2 floor has no realpath) to $TARGET or to a
#      path under it, comparing against the RESOLVED $TARGET so a symlinked
#      target directory is not a spurious refusal.
# `|| true` inside each command substitution is load-bearing under `set -e`:
# without it a failing `cd -P` aborts the whole script (measured) and the
# named-refusal branch below is unreachable.
_restore_refuses() {
  _rr_rel="$1"
  _rr_src="${2:-}"
  if ! _wbm_route_relpath_ok "$_rr_rel"; then
    _log "    RESTORE-BLOCKED (destination is not a confined relative path): $_rr_rel"
    return 0
  fi
  if [ -n "$_rr_src" ] && ! _wbm_route_relpath_ok "$_rr_src"; then
    _log "    RESTORE-BLOCKED (source '$_rr_src' is not a confined relative path — route table poisoned?): $_rr_rel"
    return 0
  fi
  # rail round-7 F2 — LEXICAL is not PHYSICAL on the source side either. `cp -p`
  # follows symlinks, so a source whose leaf or ancestor is a link to a regular
  # file outside this checkout would be copied into the adopter tree as
  # framework content — the same escape measured on the upgrade side (S327),
  # and the same class as D4/A3 (doctor copying the WRONG source) arriving
  # through a different door. This covers BOTH lanes: the route lane and the
  # identity fallback that answers for every `.claude/**` manifest record.
  if [ -n "$_rr_src" ] && ! _wbm_source_confined "$SOURCE_DIR" "$_rr_src"; then
    _log "    RESTORE-BLOCKED (source not confined to the framework checkout — ${_WBM_SRC_CONFINE_WHY:-unknown reason}): $_rr_rel"
    return 0
  fi
  # PLAN-185-FOLLOWUP FU-7 (S337): the destination half is the SHARED
  # predicate install.sh and upgrade.sh consume (_wbm_dst_refuses,
  # scripts/_framework_manifest_set.sh) — one implementation, not doctor's own
  # copy of the symlink walk + physical resolution that lived here. It refuses
  # everything the retired copy refused (symlinked leaf, symlinked ancestor,
  # unresolvable ancestor, resolution outside the RESOLVED target) and one
  # thing the copy did not: a HARD-LINKED leaf (nlink > 1). `cp -p` writes an
  # existing destination IN PLACE, so every other name for that inode —
  # including names outside the target — sees the framework bytes; e2e D.1
  # reproduces that escape against the pre-cure copy. Polarity preserved:
  # 0 = REFUSE.
  if _wbm_dst_refuses "$TARGET" "$_rr_rel"; then
    REFUSED_COUNT=$((REFUSED_COUNT + 1))
    _log "    RESTORE-BLOCKED (destination refused — nothing written: ${_WBM_DST_REFUSE_WHY:-unknown reason}): $_rr_rel"
    return 0
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
  # D4: repair from the route's SOURCE, never from the destination relpath.
  _rf_rc=0
  _rf_src="$( _wbm_route_src "$_rf_rel" )" || _rf_rc=$?
  if [ "$_rf_rc" -eq 2 ]; then
    _log "    RESTORE-BLOCKED (delivered through a transform, or its route row was rejected — the bytes exist in no checkout): $_rf_rel"
    return 1
  fi
  if [ "$_rf_rc" -ne 0 ] || [ -z "${_rf_src:-}" ]; then
    _rf_src="$_rf_rel"
  fi
  # Belt and braces (W6). Deliberately AHEAD of `mkdir -p`: mkdir -p of an
  # escaping destination already creates directories outside the target, so a
  # check placed after it would be too late to prevent the side effect.
  if _restore_refuses "$_rf_rel" "$_rf_src"; then
    return 1
  fi
  mkdir -p "$TARGET/$( dirname "$_rf_rel" )"
  cp -p "$SOURCE_DIR/$_rf_src" "$TARGET/$_rf_rel"
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
REFUSED_COUNT=0   # FU-7: writes refused by the destination-confinement predicate
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
          elif _link_dst_refuses "$rel"; then
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
            _lk_go=1
            if [ -f "$lpath" ] && [ ! -L "$lpath" ]; then
              if _backup_file "$rel"; then
                _log "    BACKED-UP: $rel -> $BAK_DIR/$rel"
              else
                _lk_go=0   # FU-7: no backup, no overwrite
              fi
            fi
            if [ "$_lk_go" -eq 0 ] || _link_dst_refuses "$rel"; then
              UNRESOLVED=$((UNRESOLVED + 1))
            else
              rm -f "$lpath"
              if ln -s "$target" "$lpath" 2>/dev/null; then
                _log "    RE-LINKED: $rel -> $target"
                REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
              else
                _log "    RESTORE-FAILED (ln -s failed): $rel"
                UNRESOLVED=$((UNRESOLVED + 1))
              fi
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
        # D4: hash the route's SOURCE. A rendered route yields an empty
        # src_hash on purpose, which the existing branch below already
        # reports as not-repairable — the correct verdict.
        _ms_rc=0
        src_rel="$( _wbm_route_src "$rel" )" || _ms_rc=$?
        if [ "$_ms_rc" -eq 2 ]; then
          src_hash=""
        else
          if [ "$_ms_rc" -ne 0 ] || [ -z "${src_rel:-}" ]; then src_rel="$rel"; fi
          # rail round-8 — the WRITE site (_restore_refuses) has demanded
          # PHYSICAL source confinement since round 7; the two HASH sites did
          # not, and `_hash_file` follows symlinks exactly as `cp -p` does. A
          # source whose leaf OR ancestor links to a regular file outside this
          # checkout therefore hashed FOREIGN bytes, and the verdict flipped
          # away from the conservative one: here to "MISSING (restorable)" for
          # a file `_restore_file` would then refuse to write, and at the DRIFT
          # site below to "baseline-stale" — a verdict that TELLS the operator
          # to bless foreign bytes into the baseline by running upgrade.sh.
          # Same predicate as the write site (no second implementation — the
          # PLAN-182 lesson), and the refusal travels on the EXISTING
          # empty-src_hash channel, so no verdict here is new.
          if _wbm_source_confined "$SOURCE_DIR" "$src_rel"; then
            src_hash="$( _hash_file "$SOURCE_DIR/$src_rel" 2>/dev/null || true )"
          else
            _log "    SOURCE-BLOCKED (source '$src_rel' is not confined to the framework checkout — ${_WBM_SRC_CONFINE_WHY:-unknown reason}): $rel"
            src_hash=""
          fi
        fi
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
      # D4: hash the route's SOURCE (see the MISSING branch above).
      _dr_rc=0
      src_rel="$( _wbm_route_src "$rel" )" || _dr_rc=$?
      if [ "$_dr_rc" -eq 2 ]; then
        src_hash=""
      else
        if [ "$_dr_rc" -ne 0 ] || [ -z "${src_rel:-}" ]; then src_rel="$rel"; fi
        # rail round-8 — the same physical confinement the MISSING branch above
        # explains. THIS is the site the finding named: unguarded, a symlinked
        # source made `cur` and `src_hash` agree on the FOREIGN bytes and the
        # run reported `DRIFT (baseline-stale)`, i.e. "your baseline is behind
        # the framework, run upgrade.sh" — laundering content from outside the
        # checkout into the adopter's recorded framework baseline. Refused, the
        # empty src_hash lands on the existing not-repairable verdict below.
        if _wbm_source_confined "$SOURCE_DIR" "$src_rel"; then
          src_hash="$( _hash_file "$SOURCE_DIR/$src_rel" 2>/dev/null || true )"
        else
          _log "    SOURCE-BLOCKED (source '$src_rel' is not confined to the framework checkout — ${_WBM_SRC_CONFINE_WHY:-unknown reason}): $rel"
          src_hash=""
        fi
      fi
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
              if _backup_file "$rel"; then
                _log "    BACKED-UP: $rel -> $BAK_DIR/$rel"
                if _restore_file "$rel" "$base"; then
                  REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
                else
                  UNRESOLVED=$((UNRESOLVED + 1))
                fi
              else
                UNRESOLVED=$((UNRESOLVED + 1))   # FU-7: no backup, no overwrite
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
  # W6: the old `if [ "$HAVE_FMS" -eq 1 ]` guard and its "orphan scan skipped"
  # else-branch are GONE, not silenced — _framework_manifest_set.sh is required
  # at startup now, so the branch was unreachable, and an unreachable branch
  # that reports a degraded mode is a lie a future reader has to disprove.
  {
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
    # PLAN-166 F3 (ADR-155-AMEND-1): the FMS entries for PROTOCOL.md,
    # SPEC/v1 and .claude/.framework-version are CONDITIONAL on the
    # recorded delivery. doctor resolves the flags from the SAME record
    # the writers use — the sanitized baseline manifest — NEVER from the
    # ceremony: ceremony-only resolution would re-include paths a
    # `--ceremony user` install skipped and --strict-orphans would flag
    # the ADOPTER's own SPEC/PROTOCOL files as orphans (r19), while a
    # blanket maintainer default would do the same and a blanket user
    # default would hide a delivered SPEC from a maintainer (r9 P2).
    _dr_delivered() {  # $1 = ERE fragment anchored at the relpath position
      grep -Eq "^([0-9a-f]{64}|LINK)  $1" "$SANITIZED" 2>/dev/null
    }
    # `SPEC/v1(/|  |$)` and not a bare `SPEC/v1/`: a --mode link install
    # records the whole tree as ONE directory symlink (`LINK  SPEC/v1
    # <target>`, no trailing slash) — the same `(  |$)` treatment the
    # PROTOCOL/marker fragments below already have (re-pass closure; family
    # swept with upgrade.sh _baseline_has_spec_record).
    if _dr_delivered 'SPEC/v1(/|  |$)'; then
      FMS_DELIVERED_SPEC=1
    else
      FMS_DELIVERED_SPEC=0
    fi
    if _dr_delivered 'PROTOCOL\.md(  |$)'; then
      FMS_DELIVERED_PROTOCOL=1
    else
      FMS_DELIVERED_PROTOCOL=0
    fi
    if _dr_delivered '\.claude/\.framework-version(  |$)'; then
      FMS_DELIVERED_MARKER=1
    else
      FMS_DELIVERED_MARKER=0
    fi
    export FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
    export FMS_ROOT="$TARGET"
    export FMS_PROFILE_PARTS="$PROFILE_PARTS_STR"
    _framework_manifest_files > "$WORKDIR/enumerated" 2>/dev/null || : > "$WORKDIR/enumerated"
    unset FMS_ROOT FMS_PROFILE_PARTS
    unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
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
  }
fi

# ---------------------------------------------------------------------------
# Pair-rail timeout coherence (PLAN-164 / ADR-110-AMEND-1 — ADVISORY,
# report-only, NEVER drives the exit code): the harness kills a hook at its
# settings.json registration timeout, so a check_pair_rail.py registration
# below the hook's INTERNAL default (CEO_PAIR_RAIL_TIMEOUT_S) + the 30s
# invariant margin means the codex verdict can be killed mid-flight — the
# historical 12/12 pair_rail_case F/TIMEOUT class (hook-kill risk). The
# internal default is read with the SAME regex the invariant uses:
# os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "NNN"). Fail-open: missing
# jq/hook/settings or an unparseable value => NOTE + skip.
# ---------------------------------------------------------------------------
_pair_rail_timeout_check() {
  _prt_settings="$TARGET/.claude/settings.json"
  _prt_hook="$TARGET/.claude/hooks/check_pair_rail.py"
  if [ ! -f "$_prt_settings" ] || [ ! -f "$_prt_hook" ]; then
    return 0
  fi
  if ! command -v jq >/dev/null 2>&1; then
    _log "    NOTE: pair-rail timeout check skipped (jq not found) — advisory only"
    return 0
  fi
  _prt_reg="$( jq -r '[ .hooks // {} | to_entries[] | .value
      | select(type == "array") | .[] | .hooks[]?
      | select((type == "object")
          and ((.command? | type) == "string")
          and (.command | test("check_pair_rail\\.py")))
      | .timeout ] | first // empty' "$_prt_settings" 2>/dev/null || true )"
  _prt_int="$( sed -n 's/.*os\.environ\.get("CEO_PAIR_RAIL_TIMEOUT_S", "\([0-9][0-9]*\)").*/\1/p' "$_prt_hook" 2>/dev/null | head -n 1 )"
  case "$_prt_reg" in
    ''|*[!0-9]*)
      _log "    NOTE: pair-rail timeout check skipped (no numeric check_pair_rail.py registration timeout in settings.json) — advisory only"
      return 0 ;;
  esac
  case "$_prt_int" in
    ''|*[!0-9]*)
      _log "    NOTE: pair-rail timeout check skipped (internal CEO_PAIR_RAIL_TIMEOUT_S default not found in check_pair_rail.py) — advisory only"
      return 0 ;;
  esac
  if [ "$_prt_reg" -lt $((_prt_int + 30)) ]; then
    _log ""
    _log "    WARN: check_pair_rail.py registration timeout (${_prt_reg}s) < internal default (${_prt_int}s) + 30s margin —"
    _log "          the harness can KILL the hook before the codex verdict lands (PLAN-164 hook-kill risk;"
    _log "          the historical 12/12 pair_rail_case F/TIMEOUT class). Raise the settings.json registration"
    _log "          timeout to >= $((_prt_int + 30))s (upgrade.sh migrates the old default 60 -> 150)."
  elif [ "$VERBOSE" -eq 1 ]; then
    _log "    OK (pair-rail timeouts): registration ${_prt_reg}s >= internal ${_prt_int}s + 30s margin"
  fi
  return 0
}
_pair_rail_timeout_check

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
_log "    Refused:   $REFUSED_COUNT (destination not confined to the target — nothing written)"
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
