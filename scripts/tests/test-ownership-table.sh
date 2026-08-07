#!/usr/bin/env bash
# =============================================================================
# PLAN-167 W0.3 — ownership decision table runner.
#
# Executes EVERY legal cell of scripts/tests/ownership_table.tsv against the
# REAL scripts/install.sh and scripts/upgrade.sh. There is no mock of the
# subject under test: the fixture is a real target tree, the run is a real
# invocation, and the verdict is DERIVED from observable state, never parsed
# out of prose.
#
# Reasoning + dimension/enum definitions: docs/ownership-decision-table.md
#
# Usage:
#   test-ownership-table.sh              run every row
#   test-ownership-table.sh --only OWN-0013
#   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
#   test-ownership-table.sh --list       list row ids and exit
#   test-ownership-table.sh --keep       keep the scratch dir (debugging)
#
# Exit: 0 = every row matched its expected pair. 1 = at least one mismatch.
#       2 = harness/usage error (never confused with a row failure).
#
# NOT `set -e`: this harness OBSERVES scripts that are expected to fail on
# some rows. Dying on their exit status would erase the observation.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
TSV="$SCRIPT_DIR/ownership_table.tsv"

CELL_TIMEOUT="${CELL_TIMEOUT:-60}"
ONLY=""
MAP_ONLY=0
LIST_ONLY=0
KEEP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --only) ONLY="${2:-}"; shift 2 ;;
    --map)  MAP_ONLY=1; shift ;;
    --list) LIST_ONLY=1; shift ;;
    --keep) KEEP=1; shift ;;
    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$TSV" ]] || { echo "ERROR: table not found: $TSV" >&2; exit 2; }

# --- framework hash helpers (the same ones the scripts use) ------------------
# shellcheck source=/dev/null
. "$REPO_ROOT/scripts/_hash_lib.sh" 2>/dev/null || {
  echo "ERROR: cannot source scripts/_hash_lib.sh" >&2; exit 2; }
command -v _hash_file  >/dev/null 2>&1 || { echo "ERROR: _hash_file missing"  >&2; exit 2; }
command -v _hash_stdin >/dev/null 2>&1 || { echo "ERROR: _hash_stdin missing" >&2; exit 2; }

# --- scratch ----------------------------------------------------------------
# NEVER $HOME, NEVER inside the repo (PLAN-167 W0.3 hard requirement).
WORK="$( mktemp -d "${TMPDIR:-/tmp}/plan167-own.XXXXXX" )" || exit 2
T="$WORK/t"                 # the ONE target path every row uses (see §fixtures)
cleanup() {
  [[ "$KEEP" -eq 1 ]] && { echo "scratch kept: $WORK" >&2; return; }
  chmod -R u+w "$WORK" 2>/dev/null || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

# --- portable timeout -------------------------------------------------------
# macOS ships no timeout(1). A cell that hangs (the FIFO class) must be killed,
# not waited on — two separate defects in this space were a blocking cp.
_TIMEOUT_BIN=""
if command -v timeout  >/dev/null 2>&1; then _TIMEOUT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then _TIMEOUT_BIN="gtimeout"; fi

_run_with_timeout() {  # $1 = seconds; rest = command
  local secs="$1"; shift
  if [[ -n "$_TIMEOUT_BIN" ]]; then
    "$_TIMEOUT_BIN" "$secs" "$@"
    return $?
  fi
  # Fallback: background + watchdog. Kills the process group so a blocked cp
  # inside the script dies with it.
  "$@" &
  local pid=$!
  ( sleep "$secs"; kill -9 "$pid" 2>/dev/null ) &
  local watch=$!
  wait "$pid" 2>/dev/null
  local rc=$?
  kill "$watch" 2>/dev/null
  wait "$watch" 2>/dev/null
  return $rc
}

# --- surface geometry -------------------------------------------------------
_relpath_for() {
  case "$1" in
    spec)     printf 'SPEC/v1' ;;
    protocol) printf 'PROTOCOL.md' ;;
    marker)   printf '.claude/.framework-version' ;;
    *) return 1 ;;
  esac
}
MANIFEST_REL=".claude/.install-manifest.sha256"

# --- observation primitives -------------------------------------------------
_obs_type() {  # $1 = abs path -> the live_type vocabulary
  local p="$1"
  if   [[ -L "$p" ]]; then printf 'symlink'
  elif [[ ! -e "$p" ]]; then printf 'absent'
  elif [[ -d "$p" ]]; then
    if [[ -z "$( ls -A "$p" 2>/dev/null )" ]]; then printf 'dir_empty'; else printf 'dir'; fi
  elif [[ -p "$p" || -S "$p" || -b "$p" || -c "$p" ]]; then printf 'special'
  elif [[ -f "$p" ]]; then printf 'regular'
  else printf 'special'; fi
}

# Content digest of a surface, whatever its shape. Directory digest reproduces
# upgrade.sh's _spec_tree_fingerprint semantics (sorted "<sha>  <rel>" lines).
_obs_digest() {  # $1 = abs path
  local p="$1" lines
  if [[ -L "$p" ]]; then printf 'link:%s' "$( readlink "$p" 2>/dev/null || true )"; return 0; fi
  if [[ ! -e "$p" ]]; then printf 'absent'; return 0; fi
  if [[ -d "$p" ]]; then
    lines="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
      | while IFS= read -r r; do
          [[ -n "$r" ]] || continue
          printf '%s  %s\n' "$( _hash_file "$p/$r" 2>/dev/null || echo FAIL )" "$r"
        done )"
    [[ -z "$lines" ]] && { printf 'emptydir'; return 0; }
    printf '%s' "$( printf '%s\n' "$lines" | _hash_stdin )"
    return 0
  fi
  if [[ -f "$p" ]]; then printf '%s' "$( _hash_file "$p" 2>/dev/null || echo UNREADABLE )"; return 0; fi
  printf 'special'
}

# Modification-time signature of a surface. BSD stat takes -f, GNU takes -c;
# both are tried so the harness behaves the same on macOS and CI.
_stat_mtime() {  # $1 = abs path
  stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1" 2>/dev/null || printf '0'
}
_obs_mtime() {  # $1 = abs path -> newest mtime under it (or its own)
  local p="$1" newest=0 m r
  if [[ -L "$p" || ! -e "$p" ]]; then printf '%s' "$( _stat_mtime "$p" )"; return 0; fi
  if [[ -d "$p" ]]; then
    while IFS= read -r r; do
      [[ -n "$r" ]] || continue
      m="$( _stat_mtime "$p/$r" )"
      [[ "$m" =~ ^[0-9]+$ ]] || continue
      (( m > newest )) && newest="$m"
    done < <( cd "$p" && find . -type f -print 2>/dev/null )
    printf '%s' "$newest"; return 0
  fi
  printf '%s' "$( _stat_mtime "$p" )"
}

# The manifest's record for a relpath: "" | "hash:<64hex>" | "link:<target>"
# For SPEC/v1 the record may be per-file rows; presence of ANY row counts, and
# the digest reported is the tree-shaped roll-up of those rows.
_obs_record() {  # $1 = manifest abs path, $2 = relpath
  local m="$1" rel="$2" line rows
  [[ -f "$m" ]] || { printf ''; return 0; }
  line="$( grep -E "^LINK  ${rel//./\\.}  " "$m" 2>/dev/null | head -1 || true )"
  if [[ -n "$line" ]]; then printf 'link:%s' "${line#LINK  $rel  }"; return 0; fi
  line="$( grep -E "^[0-9a-f]{64}  ${rel//./\\.}$" "$m" 2>/dev/null | head -1 || true )"
  if [[ -n "$line" ]]; then printf 'hash:%s' "${line%% *}"; return 0; fi
  # tree surface: any per-file row under the relpath
  rows="$( grep -E "^[0-9a-f]{64}  ${rel//./\\.}/" "$m" 2>/dev/null || true )"
  if [[ -n "$rows" ]]; then
    printf 'hash:%s' "$( printf '%s\n' "$rows" | LC_ALL=C sort | _hash_stdin )"
    return 0
  fi
  printf ''
}

# Refusal markers — the operator-visible contract of ABORT_SURFACE. Matching
# output is a deliberate choice, recorded in docs §6 (OQ-1/OQ-2): a refusal is
# defined by the framework having ATTEMPTED and declined, which leaves no
# filesystem trace at all. If this wording changes, this test fails loudly —
# which is correct, because the operator-visible contract changed.
_ABORT_MARKERS='REFUSING to|could not back up|unsupported special file|backup-before-replace'

# =============================================================================
# Fixtures
#
# Every row runs at the SAME target path ($T). That is load-bearing, not
# convenience: the root PROTOCOL.md pointer body embeds the target path, so a
# base tree captured at one path and restored at another would carry a stale
# canonical pointer digest and silently corrupt every protocol row.
# =============================================================================
BASE_DIR="$WORK/base"; mkdir -p "$BASE_DIR"
CANON_POINTER_HASH=""       # captured from a real install at $T (never recomputed)

_base_tar() {  # $1 = ceremony, $2 = base mode(copy|link) -> path to tarball
  local ceremony="$1" bmode="$2"
  local tarball="$BASE_DIR/$ceremony-$bmode.tar"
  [[ -f "$tarball" ]] && { printf '%s' "$tarball"; return 0; }

  rm -rf "$T"; mkdir -p "$T"
  local args=( "$T" --ceremony "$ceremony" )
  [[ "$bmode" == "link" ]] && args+=( --link )
  if ! _run_with_timeout 300 "$REPO_ROOT/scripts/install.sh" "${args[@]}" \
        > "$BASE_DIR/$ceremony-$bmode.install.log" 2>&1; then
    echo "ERROR: base install failed ($ceremony/$bmode) — see $BASE_DIR/$ceremony-$bmode.install.log" >&2
    return 1
  fi
  # The canonical pointer digest for THIS target path, taken from the file the
  # real installer just generated (never reproduced by duplicating the heredoc,
  # which would be an oracle that passes when both sides are wrong together).
  if [[ -z "$CANON_POINTER_HASH" && -f "$T/PROTOCOL.md" ]]; then
    CANON_POINTER_HASH="$( _hash_file "$T/PROTOCOL.md" 2>/dev/null || true )"
  fi
  ( cd "$T" && tar -cf "$tarball" . ) || return 1
  rm -rf "$T"
  printf '%s' "$tarball"
}

# A source checkout that LACKS a surface — what `--pin <pre-v1.3 tag>` yields.
_alt_source() {  # $1 = surface -> path to a source tree without it
  local surface="$1"
  local alt="$WORK/src-no-$surface"
  [[ -d "$alt" ]] && { printf '%s' "$alt"; return 0; }
  _clone_source "$alt" || return 1
  local rel; rel="$( _relpath_for "$surface" )"
  rm -rf "${alt:?}/$rel"
  printf '%s' "$alt"
}

_clone_source() {  # $1 = destination
  mkdir -p "$1"
  ( cd "$REPO_ROOT" && tar -cf - --exclude='./.git' --exclude='./node_modules' . ) \
    | ( cd "$1" && tar -xf - )
}

# The NEXT version of the framework — a source whose surfaces differ from the
# one that produced the baseline.
#
# This is not decoration. A real upgrade runs against a source NEWER than the
# install that wrote the manifest. Reusing one source makes `HASH_SOURCE` and
# `HASH_PRIOR_RECORD` byte-equal, and a classifier can then only tell them
# apart by preferring one — which is resolving an ambiguity by preference, the
# exact thing docs §5.6 forbids. Perturbing the source is how the fixture is
# DIFFERENTIATED until the two candidates separate.
_next_source() {
  local nxt="$WORK/src-next"
  [[ -d "$nxt" ]] && { printf '%s' "$nxt"; return 0; }
  _clone_source "$nxt" || return 1
  local first
  first="$( ( cd "$nxt/SPEC/v1" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
  first="${first#./}"
  [[ -n "$first" ]] && printf '\n<!-- next-version marker (PLAN-167 fixture) -->\n' >> "$nxt/SPEC/v1/$first"
  printf '1.3.1\n' > "$nxt/.claude/.framework-version"
  printf '%s' "$nxt"
}

_strip_record() {  # $1 = manifest, $2 = relpath — make prior_record=none
  local m="$1" rel="$2" tmp
  [[ -f "$m" ]] || return 0
  tmp="$( mktemp "$m.XXXXXX" )" || return 1
  grep -vE "^([0-9a-f]{64}|LINK)  ${rel//./\\.}(/|  |$)" "$m" > "$tmp" 2>/dev/null
  mv "$tmp" "$m"
}

_mutate_surface() {  # $1 surface, $2 live_type, $3 live_content, $4 src root, $5 prior_record
  local surface="$1" ltype="$2" lcontent="$3" src_root="$4" prior="${5:-none}"
  local rel; rel="$( _relpath_for "$surface" )"
  local p="$T/$rel"

  # A `link_match` row means the live symlink IS the recorded delivery. The
  # base --link install already created exactly that, so pointing it somewhere
  # else here would silently convert every link_match row into a
  # link_retargeted one — the fixture would then agree with the expectation for
  # the wrong reason, which is how a row goes green while testing nothing.
  if [[ "$ltype" == "symlink" && "$prior" == "link_match" ]]; then
    [[ -L "$p" ]] || { echo "FIXTURE-ERR: $rel is not a symlink after a --link base install" >&2; return 1; }
    ltype="__keep__"
  fi

  case "$ltype" in
    absent)   rm -rf "$p" ;;
    dir_empty)
      rm -rf "$p"; mkdir -p "$p" ;;
    regular)
      if [[ -d "$p" ]]; then rm -rf "$p"; fi
      [[ -e "$p" ]] || { mkdir -p "$( dirname "$p" )"; printf 'adopter regular file\n' > "$p"; }
      ;;
    symlink)
      # The foreign leaf is a TRIPWIRE, not scenery. A surface written with
      # `cat >` follows a leaf symlink and mutates whatever it points at —
      # OUTSIDE the target tree, which is adopter or system data. Comparing
      # only the target would let that row report GREEN while the run
      # destroyed a file the test never looked at.
      rm -rf "$p"
      mkdir -p "$( dirname "$p" )" "$WORK/foreign"
      printf 'foreign content — MUST NOT be modified by any run\n' > "$WORK/foreign/leaf"
      ln -s "$WORK/foreign/leaf" "$p"
      ;;
    special)
      rm -rf "$p"; mkdir -p "$( dirname "$p" )"; mkfifo "$p" 2>/dev/null || return 1 ;;
    ancestor_symlink)
      # Move the parent aside and symlink it back — the leaf is then reachable
      # only by writing THROUGH a symlink out of the target tree.
      local parent; parent="$( dirname "$p" )"
      local real="$WORK/ancestor-real-$surface"
      rm -rf "$real"; mkdir -p "$( dirname "$real" )"
      mv "$parent" "$real" 2>/dev/null || return 1
      ln -s "$real" "$parent"
      ;;
    dir)
      # On a rerun the base install already left the tree; on a structurally
      # fresh target there is nothing yet, so the adopter's own directory has
      # to be built here.
      if [[ ! -d "$p" || -L "$p" ]]; then
        rm -rf "$p"; mkdir -p "$p"; printf 'adopter content\n' > "$p/adopter.md"
      fi
      ;;
  esac

  case "$lcontent" in
    edited)
      if [[ -d "$p" && ! -L "$p" ]]; then
        local victim
        victim="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
        victim="${victim#./}"
        # Guard the empty-tree case: without it the redirect target collapses to
        # "$p/" and the shell reports "Is a directory" instead of mutating.
        # if/fi, NOT `[[ ]] && cmd`: as the last statement of the branch, a
        # false test would make the whole function return 1 and the row would
        # be recorded as a harness error rather than run.
        if [[ -n "$victim" ]]; then
          printf '\nADOPTER EDIT\n' >> "$p/$victim"
        fi
      elif [[ -f "$p" && ! -L "$p" ]]; then
        printf 'ADOPTER EDIT\n' >> "$p"
      fi
      ;;
    pristine)
      # "byte-identical to what THIS run's source would deliver" — so it must be
      # synced from the RUN source, not left as whatever the base install wrote.
      # The generated pointer has no source file: the base install's own output
      # IS its pristine form, so protocol is left untouched.
      if [[ "$surface" != "protocol" && -e "$src_root/$rel" && ! -L "$p" ]]; then
        rm -rf "$p"; mkdir -p "$( dirname "$p" )"; cp -R "$src_root/$rel" "$p" 2>/dev/null || true
      fi
      ;;
    legacy_pristine)
      # A REAL v1.2.0 SPEC/v1 tree from the tag the pristine fingerprints were
      # derived from — never a hand-built approximation, which would test the
      # fixture rather than the migration.
      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
        echo "FIXTURE-ERR: tag v1.2.0 is not available in this checkout." >&2
        echo "             legacy_pristine rows need the REAL shipped tree, never an" >&2
        echo "             approximation. A CI checkout using fetch-depth:1 has NO tags" >&2
        echo "             — that job needs fetch-depth:0 or fetch-tags:true." >&2
        return 1
      fi
      rm -rf "$p"; mkdir -p "$p"
      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
        | ( cd "$T" && tar -xf - ) || return 1
      ;;
  esac

  # Structured `note` directives that alter the fixture. Two rows can otherwise
  # share an identical fixture while asserting opposite outcomes — at least one
  # of them then passes or fails for a reason that has nothing to do with what
  # it claims to test. (More evidence for OQ-7: `note` is accumulating
  # dimensions that nothing validates.)
  case "${_ROW_NOTE:-}" in
    *extra=adopter_symlink*)
      # An adopter-ADDED non-regular entry inside an otherwise pristine tree.
      # The fingerprint must refuse to certify a tree it cannot fully inventory.
      ln -s /dev/null "$p/adopter-added.link" 2>/dev/null || true
      ;;
  esac

}

# =============================================================================
# Verdict derivation
# =============================================================================
_derive_verdict() {  # $1 bd $2 ad $3 br $4 ar $5 out $6 surface $7 rel $8 operation
  local bd="$1" ad="$2" br="$3" ar="$4" out="$5" surface="$6" rel="$7" op="${8:-upgrade}"
  if [[ "$bd" != "$ad" ]]; then
    if [[ "$bd" == "absent" ]]; then printf 'DELIVER'; else printf 'REFRESH'; fi
    return 0
  fi
  # Unchanged target from here on.
  if grep -Eq "$_ABORT_MARKERS" "$out" 2>/dev/null; then printf 'ABORT_SURFACE'; return 0; fi
  # A REFRESH that writes byte-identical content leaves the CONTENT unchanged,
  # so a content digest alone cannot separate it from a PRESERVE.
  #
  # Backup presence does not settle it either: the ADOPTER-FORK preserve path
  # also snapshots into BAK_DIR, so "a backup exists" is evidence the framework
  # looked, not that it wrote.
  #
  # Modification time settles it on the UPGRADE path, from state and without
  # reading prose: the forced route replaces content with `cp -R` (no -p),
  # which stamps new mtimes, while every preserve path leaves bytes AND
  # timestamps alone.
  #
  # Restricted to upgrade deliberately. install.sh re-runs placeholder
  # SUBSTITUTION on every invocation, so it rewrites the pointer with identical
  # bytes and a fresh mtime — a write with no semantic content. Counting that
  # as REFRESH would report an ownership change where none happened.
  #
  # No single signal is valid everywhere here: the content digest cannot see an
  # identical-content refresh, the backup fires on the preserve-with-snapshot
  # path, and mtime fires on install re-substitution. Each is used only where
  # it is sound, and the boundary is stated rather than assumed.
  if [[ "$op" == "upgrade" && "$_MTIME_BEFORE" != "$_MTIME_AFTER" ]]; then
    printf 'REFRESH'; return 0
  fi
  if [[ -n "$br" && -z "$ar" ]]; then printf 'OMIT_RECORD'; return 0; fi
  if [[ -n "$ar" ]]; then printf 'PRESERVE_OWNED'; else printf 'PRESERVE_UNOWNED'; fi
}

_derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
  local surface="$1" ar="$2" pr="$3" src="$4"
  [[ -z "$ar" ]] && { printf 'HASH_NONE'; return 0; }
  case "$ar" in link:*) printf 'LINK_RECORD'; return 0 ;; esac

  local got="${ar#hash:}"
  local rel; rel="$( _relpath_for "$surface" )"

  # Candidate 1: the bytes now at the target.
  local c_target; c_target="$( _obs_digest "$T/$rel" )"
  # Candidate 2: the framework's copy in the source checkout.
  local c_source; c_source="$( _obs_digest "$src/$rel" )"
  # Candidate 3: the digest the PRE-run manifest recorded.
  local c_prior="${pr#hash:}"
  # Candidate 4: the canonical pointer digest (protocol only).
  local c_pointer="$CANON_POINTER_HASH"

  # For tree surfaces the recorded value is the roll-up of per-file rows, which
  # is not comparable to a content fingerprint — compare tree membership by
  # re-deriving both roll-ups instead.
  if [[ "$surface" == "spec" ]]; then
    local roll_t roll_s
    roll_t="$( _rollup_from_tree "$T/$rel" "$rel" )"
    roll_s="$( _rollup_from_tree "$src/$rel" "$rel" )"
    [[ -n "$c_prior" && "$got" == "$c_prior" ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
    [[ -n "$roll_s" && "$got" == "$roll_s" ]] && { printf 'HASH_SOURCE'; return 0; }
    [[ -n "$roll_t" && "$got" == "$roll_t" ]] && { printf 'HASH_TARGET'; return 0; }
    printf 'HASH_UNCLASSIFIED'; return 0
  fi

  [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
  [[ -n "$c_source"  && "$got" == "$c_source"  ]] && { printf 'HASH_SOURCE'; return 0; }
  [[ -n "$c_pointer" && "$got" == "$c_pointer" ]] && { printf 'HASH_CANONICAL_POINTER'; return 0; }
  [[ -n "$c_target"  && "$got" == "$c_target"  ]] && { printf 'HASH_TARGET'; return 0; }
  printf 'HASH_UNCLASSIFIED'
}

_rollup_from_tree() {  # $1 = tree abs path, $2 = relpath prefix
  local root="$1" pfx="$2"
  [[ -d "$root" ]] || { printf ''; return 0; }
  ( cd "$root" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
    | while IFS= read -r r; do
        [[ -n "$r" ]] || continue
        printf '%s  %s/%s\n' "$( _hash_file "$root/$r" 2>/dev/null || echo FAIL )" "$pfx" "${r#./}"
      done | LC_ALL=C sort | _hash_stdin
}

# =============================================================================
# Row execution
# =============================================================================
PASS=0; FAIL=0; AMBIG=0; ERR=0
MAP_LINES=""

_run_row() {
  local id="$1" surface="$2" prior_record="$3" live_type="$4" live_content="$5"
  local source_has="$6" mode="$7" ceremony="$8" operation="$9" skip_requested="${10}"
  local exp_verdict="${11}" exp_hash="${12}" origin="${13}" note="${14}"

  local rel; rel="$( _relpath_for "$surface" )" || { ERR=$((ERR+1)); return; }

  # --- base selection ------------------------------------------------------
  # base_mode follows PRIOR_RECORD (the previous run), never `mode` (this run).
  # Conflating them would erase the r11-F1 cell — see docs §4.1.
  local base_mode="copy"
  case "$prior_record" in link_match|link_retargeted) base_mode="link" ;; esac
  local base_ceremony="$ceremony"
  # A user-ceremony row asserting residue of a MAINTAINER install must be built
  # from a maintainer base, then transitioned — that transition is the r7-F2 cell.
  local transition_to_user=0
  if [[ "$ceremony" == "user" && "$prior_record" != "none" && "$surface" != "marker" ]]; then
    base_ceremony="maintainer"; transition_to_user=1
  fi

  # --- source selection (BEFORE the fixture — `pristine` syncs from it) ----
  local src
  if [[ "$source_has" == "no" ]]; then
    src="$( _alt_source "$surface" )" || { ERR=$((ERR+1)); return; }
  elif [[ "$operation" == "install_fresh" ]]; then
    src="$REPO_ROOT"
  else
    # An upgrade/rerun runs against a source NEWER than the one that wrote the
    # baseline. Without that, HASH_SOURCE and HASH_PRIOR_RECORD are byte-equal.
    src="$( _next_source )" || { ERR=$((ERR+1)); return; }
  fi

  # --- base tree -----------------------------------------------------------
  if [[ "$operation" == "install_fresh" ]]; then
    # Structurally fresh means NO pre-existing manifest (docs R-01). Extracting
    # a base and stripping one record would leave a manifest behind and make the
    # row an install_rerun wearing a fresh label.
    rm -rf "$T"; mkdir -p "$T"
  else
    local tarball; tarball="$( _base_tar "$base_ceremony" "$base_mode" )" || { ERR=$((ERR+1)); return; }
    rm -rf "$T"; mkdir -p "$T"
    tar -xf "$tarball" -C "$T" || { ERR=$((ERR+1)); return; }
  fi

  # --- fixture mutation ----------------------------------------------------
  [[ "$prior_record" == "none" ]] && _strip_record "$T/$MANIFEST_REL" "$rel"
  if [[ "$prior_record" == "link_retargeted" && -L "$T/$rel" ]]; then
    mkdir -p "$WORK/retarget"; printf 'retargeted\n' > "$WORK/retarget/leaf"
    rm -f "$T/$rel"; ln -s "$WORK/retarget/leaf" "$T/$rel"
  fi
  _ROW_NOTE="$note"
  _mutate_surface "$surface" "$live_type" "$live_content" "$src" "$prior_record" \
    || { ERR=$((ERR+1)); return; }

  # fault injection (docs OQ-7 — a tenth axis riding in `note` until ratified)
  local bak_guard=""
  case "$note" in
    *fault=backup_unwritable*)
      bak_guard="$T/.claude.bak"
      rm -rf "$bak_guard"; mkdir -p "$bak_guard"; chmod 500 "$bak_guard" ;;
  esac

  # --- BEFORE snapshot -----------------------------------------------------
  local b_digest b_rec
  b_digest="$( _obs_digest "$T/$rel" )"
  b_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
  _MTIME_BEFORE="$( _obs_mtime "$T/$rel" )"
  # Everything outside $T that a run could reach. Any change here is an escape.
  _ESCAPE_BEFORE="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"

  # --- run the REAL script -------------------------------------------------
  local out="$WORK/run-$id.log"; : > "$out"
  local rc=0
  # A `ceremony=user` UPGRADE row asserts residue of a maintainer install that
  # was later re-run as `--ceremony user`. The ceremony is read from
  # .claude/.install-state.json, so labelling the row is not enough: the
  # transition has to actually happen, or upgrade.sh still sees `maintainer`
  # and the row silently tests the wrong branch.
  if [[ "$transition_to_user" -eq 1 && "$operation" == "upgrade" ]]; then
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "$T" --ceremony user \
      >> "$out" 2>&1 || true
  fi
  if [[ "$operation" == "upgrade" ]]; then
    local uargs=( "$T" )
    [[ "$skip_requested" == "self" ]] && uargs+=( --skip "$rel" )
    if [[ "$skip_requested" == "descendant" ]]; then
      local victim; victim="$( ( cd "$T/$rel" 2>/dev/null && find . ! -type d -print 2>/dev/null | LC_ALL=C sort | head -1 ) )"
      victim="${victim#./}"
      [[ -n "$victim" ]] && uargs+=( --skip "$rel/$victim" )
    fi
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/upgrade.sh" "${uargs[@]}" >> "$out" 2>&1
    rc=$?
  else
    local iargs=( "$T" --ceremony "$ceremony" )
    [[ "$mode" == "link" ]] && iargs+=( --link )
    [[ "$transition_to_user" -eq 1 ]] && iargs=( "$T" --ceremony user )
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "${iargs[@]}" >> "$out" 2>&1
    rc=$?
  fi
  [[ -n "$bak_guard" ]] && chmod 700 "$bak_guard" 2>/dev/null

  local timed_out=0
  [[ $rc -eq 124 || $rc -eq 137 ]] && timed_out=1

  # --- AFTER snapshot + derivation ----------------------------------------
  local a_digest a_rec got_verdict got_hash
  a_digest="$( _obs_digest "$T/$rel" )"
  a_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
  _MTIME_AFTER="$( _obs_mtime "$T/$rel" )"
  _ESCAPE_AFTER="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"

  if [[ "$timed_out" -eq 1 ]]; then
    got_verdict="TIMEOUT"; got_hash="TIMEOUT"
  else
    got_verdict="$( _derive_verdict "$b_digest" "$a_digest" "$b_rec" "$a_rec" "$out" "$surface" "$rel" "$operation" )"
    got_hash="$( _derive_hash_source "$surface" "$a_rec" "$b_rec" "$src" )"
  fi

  # --- compare -------------------------------------------------------------
  local status="RED"
  local alt=""
  case "$note" in *indistinguishable=*) alt="${note##*indistinguishable=}"; alt="${alt%% *}" ;; esac

  # An escape outranks the verdict comparison. A row whose pair matches while
  # the run wrote OUTSIDE the target has not passed: it has demonstrated the
  # exact damage class this table exists to prevent, and calling that GREEN
  # would be the instrument concealing a data loss.
  if [[ "$_ESCAPE_BEFORE" != "$_ESCAPE_AFTER" ]]; then
    status="ESCAPE"; FAIL=$((FAIL+1))
  elif [[ "$got_verdict" == "$exp_verdict" && "$got_hash" == "$exp_hash" ]]; then
    status="GREEN"; PASS=$((PASS+1))
  elif [[ "$got_verdict" == "$exp_verdict" && -n "$alt" && "$got_hash" == "$alt" ]]; then
    status="AMBIG"; AMBIG=$((AMBIG+1))
  elif [[ "$got_verdict" == "TIMEOUT" ]]; then
    status="TIMEOUT"; FAIL=$((FAIL+1))
  else
    FAIL=$((FAIL+1))
  fi

  MAP_LINES+="$( printf '%-10s %-7s exp=%-16s/%-22s got=%-16s/%-22s rc=%-3s %s\n' \
      "$id" "$status" "$exp_verdict" "$exp_hash" "$got_verdict" "$got_hash" "$rc" "$origin" )"$'\n'
}

# =============================================================================
# Main
# =============================================================================
if [[ "$LIST_ONLY" -eq 1 ]]; then
  awk -F'\t' '!/^#/ && $1!="id" && NF>1 {print $1"\t"$13}' "$TSV"
  exit 0
fi

echo "== PLAN-167 ownership decision table =="
echo "   table:  $TSV"
echo "   source: $REPO_ROOT"
echo "   scratch:$WORK"
echo "   timeout:${CELL_TIMEOUT}s/cell   timeout-bin:${_TIMEOUT_BIN:-<fallback>}"
echo ""

# Prime the canonical pointer digest for $T from a real install. Structurally
# fresh rows build no base, so without this the protocol candidate would be
# unavailable exactly where it is needed.
_base_tar maintainer copy >/dev/null || { echo "ERROR: could not prime base" >&2; exit 2; }


# Rows are consumed in file order; the map is sorted by id at emit time so the
# output is deterministic regardless of table order.
while IFS=$'\t' read -r id surface prior_record live_type live_content \
      source_has mode ceremony operation skip_requested \
      exp_verdict exp_hash origin note; do
  [[ -z "${id:-}" ]] && continue
  case "$id" in \#*|id) continue ;; esac
  # --only takes a comma-separated list: iterating on a cluster of related rows
  # should cost ONE base install, not one per row.
  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi
  _run_row "$id" "$surface" "$prior_record" "$live_type" "$live_content" \
           "$source_has" "$mode" "$ceremony" "$operation" "$skip_requested" \
           "$exp_verdict" "$exp_hash" "$origin" "${note:-}"
done < "$TSV"

printf '%s' "$MAP_LINES" | LC_ALL=C sort

echo ""
echo "GREEN=$PASS  RED=$FAIL  AMBIG=$AMBIG  HARNESS-ERR=$ERR"

[[ "$MAP_ONLY" -eq 1 ]] && exit 0
[[ "$ERR" -gt 0 ]] && exit 2
[[ "$FAIL" -gt 0 ]] && exit 1
exit 0
