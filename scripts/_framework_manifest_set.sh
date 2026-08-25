# shellcheck shell=bash
# scripts/_framework_manifest_set.sh — the SINGLE canonical enumeration of
# framework-owned files that an upgrade overwrites (PLAN-138 Wave C / ADR-155).
#
# WHY (ADR-155 decision (i)): install.sh writes a SELECTIVE list
# (install_hooks_selective / install_scripts_selective / install_one
# ".claude/commands" / the install_protocol_pointer at install.sh:1425) while
# upgrade.sh `cp -R` drags whole directory trees (backup_and_replace at
# upgrade.sh:654-679 + _refresh_protocol_pointer at :450-486). Those two
# divergent enumerations are the install≠upgrade drift. This file is the ONE
# source of truth, sourced by BOTH write_install_manifest (install side) and
# _classify_against_baseline (upgrade side), so the recorded baseline and the
# classifier walk the exact same set.
#
# Contract:
#   * bash 3.2-safe: no associative arrays, no mapfile, no GNU-only flags.
#   * Profile-aware: a `--profile core` install must NOT enumerate absent
#     frontend / domain files. Callers export FMS_PROFILE_PARTS as a
#     space-separated profile list (e.g. "core frontend fintech") before
#     calling the functions; if unset it defaults to "core frontend".
#   * Two surfaces:
#       _framework_target_entries  -> the TOP-LEVEL target relpaths (mix of
#                                     files + directories) install/upgrade
#                                     operate on, one per line, sorted, deduped.
#                                     Used for the install==upgrade set assertion.
#       _framework_manifest_files  -> the EXPANDED per-file relpaths (every
#                                     regular file under each target entry,
#                                     directories walked), one per line, sorted.
#                                     Used by the manifest writer + classifier.
#   * EXCLUDES the manifest dotfile itself (.claude/.install-manifest.sha256)
#     and the backup tree (.claude.bak/).
#   * Includes the root PROTOCOL.md plus the .claude/{team.md,frontend-team.md,
#     skills,hooks,scripts,commands,pitfalls-catalog.yaml,task-chains.yaml}
#     targets, gated by profile where applicable.
#   * DELIVERY-RECORD-CONDITIONAL entries (PLAN-166 F3 / ADR-155-AMEND-1):
#     PROTOCOL.md, SPEC/v1 and .claude/.framework-version are enumerated ONLY
#     when the caller exports the matching flag as "1":
#         FMS_DELIVERED_PROTOCOL   root PROTOCOL.md pointer
#         FMS_DELIVERED_SPEC       SPEC/v1 contract tree
#         FMS_DELIVERED_MARKER     .claude/.framework-version marker
#     The flags MUST derive from the REGISTERED DELIVERY (install.sh's
#     install_one actually wrote the path this run, or the pre-upgrade
#     baseline manifest already carried the record) — NEVER from the
#     ceremony alone and NEVER from file presence: a target that already
#     had the path (install_one EXISTS-skip) stays OUTSIDE framework
#     ownership, else the baseline hashes an ADOPTER file as
#     framework-owned, the update-checker trusts a stale value, and
#     uninstall.sh may delete it. Unset/other values => NOT enumerated:
#     the deliberate fail direction is UNDER-claiming ownership.
#   * The root VERSION file is deliberately ABSENT from this enumeration:
#     install_one is skip-if-exists (an adopter with its own VERSION never
#     received the framework's), and upgrade.sh never touches it — see
#     ADR-155-AMEND-1 (the S238/ADR-155 "verified worst case" class, C.5).
#
# This file is CANONICAL (added to _CANONICAL_GUARDS in check_canonical_edit.py).
#
# Callers must set FMS_ROOT to the tree the entries are relative to:
#   - install side: FMS_ROOT="$TARGET"   (paths exist after the copy)
#   - to derive the set itself the root only matters for the file-expansion
#     pass (which directories actually have files); _framework_target_entries
#     is root-independent (it is the static intended set).

# Internal: emit the profile parts, defaulting to "core frontend".
_fms_profile_parts() {
  if [ -n "${FMS_PROFILE_PARTS:-}" ]; then
    printf '%s\n' $FMS_PROFILE_PARTS
  else
    printf '%s\n' core frontend
  fi
}

# Internal: is profile $1 present in the active profile list?
_fms_has_profile() {
  _fms_want="$1"
  _fms_p=""
  for _fms_p in $( _fms_profile_parts ); do
    if [ "$_fms_p" = "$_fms_want" ]; then
      return 0
    fi
  done
  return 1
}

# _framework_path_excluded — PLAN-161 U2 (CF-7): the SINGLE canonical
# framework-internal exclusion predicate. $1 = repo-relative path. Returns 0
# (excluded) for content the framework NEVER ships to adopters — the dogfood
# test/legacy trees, the two pytest-importing _lib helpers, __pycache__ dirs
# and *.pyc anywhere. Also matches the bare directory paths themselves (no
# trailing slash/content) so callers can test dirs. Mirrors install.sh's
# structural exclusions (install_hooks_selective / install_lib_selective /
# install_scripts_selective); install.sh's _lib walk now calls THIS predicate,
# and upgrade.sh applies it at its three write surfaces (classified union
# walk, legacy cp -R prune, manifest enumeration below).
# bash 3.2-safe: pure case globs, no arrays.
_framework_path_excluded() {
  case "$1" in
    .claude/hooks/tests|.claude/hooks/tests/*) return 0 ;;
    .claude/hooks/legacy|.claude/hooks/legacy/*) return 0 ;;
    .claude/scripts/tests|.claude/scripts/tests/*) return 0 ;;
    .claude/hooks/_lib/tests|.claude/hooks/_lib/tests/*) return 0 ;;
    .claude/hooks/_lib/test_isolation.py) return 0 ;;
    .claude/hooks/_lib/testing.py) return 0 ;;
    __pycache__|*/__pycache__|__pycache__/*|*/__pycache__/*) return 0 ;;
    *.pyc) return 0 ;;
  esac
  return 1
}

# _framework_target_entries — the top-level target relpaths (files + dirs),
# profile-aware, sorted + deduped. This is the STATIC intended set; it does not
# touch disk (so install and upgrade derive an identical list regardless of
# what is currently present).
_framework_target_entries() {
  {
    # rail round-3 F1 — PATHNAME EXPANSION IS OFF for this whole enumeration.
    # Every unquoted expansion below (FMS_PROFILE_PARTS, the delivered-template
    # list before the cure) is fed from the environment, and word splitting is
    # WANTED there while globbing never is. `set -f` separates the two: it
    # disables pathname expansion and leaves splitting intact. MEASURED
    # pre-cure: `FMS_DELIVERED_TEMPLATES='docs/*'` with the repo root as cwd
    # recorded 125 unrelated files as framework-owned. Restored below so the
    # option never leaks to a caller that reaches this function directly (the
    # brace group is the left side of a pipeline, hence a subshell today — the
    # save/restore is what keeps that true after a refactor).
    _fms_te_had_f=0
    case "$-" in *f*) _fms_te_had_f=1 ;; esac
    set -f

    # Root governance pointer (the verified S238 driver target — outside
    # .claude/). PLAN-166 F3 (ADR-155-AMEND-1): CONDITIONAL on the recorded
    # delivery. A `--ceremony user` install SKIPS install_protocol_pointer
    # (install.sh WS4-guard-proto), and a maintainer target that ALREADY had
    # its own root PROTOCOL.md was never written by the framework —
    # enumerating it unconditionally records the ADOPTER's file as
    # framework-owned (r13/r17).
    if [ "${FMS_DELIVERED_PROTOCOL:-0}" = "1" ]; then
      printf '%s\n' "PROTOCOL.md"
    fi

    # SPEC/v1 published contract (PLAN-166 F3): an upgrade surface as of
    # v1.3.0 — same delivery-record condition (never ceremony alone, never
    # file presence; r7/r17).
    if [ "${FMS_DELIVERED_SPEC:-0}" = "1" ]; then
      printf '%s\n' "SPEC/v1"
    fi

    # Framework version marker (PLAN-166 F3): a NORMAL tracked-file entry —
    # present in the source tree, so the FMS_HASH_ROOT baseline rewrite
    # (below) preserves it with no generated-file special-case — but
    # ownership still derives from the registered delivery: a target whose
    # marker pre-existed (install_one EXISTS-skip) stays adopter-owned and
    # every marker-first reader keyed off this same record falls back to
    # VERSION (r20).
    if [ "${FMS_DELIVERED_MARKER:-0}" = "1" ]; then
      printf '%s\n' ".claude/.framework-version"
    fi

    # Always-installed team rosters + universal catalogs.
    printf '%s\n' ".claude/team.md"
    printf '%s\n' ".claude/frontend-team.md"
    printf '%s\n' ".claude/pitfalls-catalog.yaml"
    printf '%s\n' ".claude/task-chains.yaml"
    # Framework schema contracts (re-pass rc.4 t5 P1, t8 P1): enumerated so
    # the NEXT generation's baseline manifest classifies them 3-state — but
    # ONLY when this run actually DELIVERED them (install_one wrote, or the
    # upgrade's hash-gated refresh installed/refreshed/found-identical
    # bytes). Same delivery-record condition as PROTOCOL.md/SPEC above:
    # never file presence. An EXISTS-skipped adopter-customized schema in
    # the manifest would record the ADOPTER's bytes as framework-owned, and
    # a later uninstall would see the matching hash and DELETE it (t8 P1).
    if [ "${FMS_DELIVERED_PLAN_SCHEMA:-0}" = "1" ]; then
      printf '%s\n' ".claude/plans/PLAN-SCHEMA.md"
    fi
    if [ "${FMS_DELIVERED_DEBATE_SCHEMA:-0}" = "1" ]; then
      printf '%s\n' ".claude/plans/DEBATE-SCHEMA.md"
    fi

    # Protocol-enforcement directory targets (always installed).
    printf '%s\n' ".claude/hooks"
    printf '%s\n' ".claude/scripts"
    printf '%s\n' ".claude/commands"

    # Skills are profile-gated.
    if _fms_has_profile "core"; then
      printf '%s\n' ".claude/skills/core"
    fi
    if _fms_has_profile "frontend"; then
      printf '%s\n' ".claude/skills/frontend"
    fi
    # Domain profiles: any profile part that is neither core nor frontend.
    for _fms_part in $( _fms_profile_parts ); do
      case "$_fms_part" in
        core|frontend) : ;;
        *) printf '%s\n' ".claude/skills/domains/$_fms_part" ;;
      esac
    done

    # PLAN-183 W5 (D3) — docs/ + .github/ destinations this run DELIVERED.
    #
    # FILE entries, never DIRECTORY entries (C5, decided S327): `docs/` and
    # `.github/` are ADOPTER-owned trees that merely CONTAIN framework
    # deliveries. A directory entry would make _framework_manifest_files walk
    # them and record every adopter file underneath as framework-owned — the
    # exact over-claim that _wbm_link_allowed and the conditional surfaces
    # exist to prevent, and a later uninstall deletes on a hash match.
    #
    # Same delivery-record condition as PROTOCOL.md/SPEC/marker above: never
    # ceremony alone, never file presence. The caller enumerates exactly what
    # it delivered, so the mutual exclusivity of .github/CODEOWNERS vs
    # .github/CODEOWNERS.template (install.sh:1496 elif vs :1511 else) is
    # INHERITED — this function never has to know which branch ran.
    #
    # rail round-3 F1 — read the list with a QUOTED `while read`, never an
    # unquoted `for`: the old loop split on newline and then PATHNAME-EXPANDED
    # each word, so `docs/*` became 125 confined, legitimate-looking relpaths
    # that walked straight past the shape predicate.
    if [ -n "${FMS_DELIVERED_TEMPLATES:-}" ]; then
      if ! command -v _wbm_route_dest_declared >/dev/null 2>&1; then
        # Same file as the reader, so this is only reachable from a fragment
        # harness that extracted the enumerator without its validators. RED
        # there is correct (rail round-1 collateral): a harness that proves
        # nothing must say so instead of recording unvalidated entries.
        echo "    ERROR: delivered-template entries REJECTED — route-table whitelist unavailable (fail-closed)" >&2
      else
        printf '%s\n' "$FMS_DELIVERED_TEMPLATES" | while IFS= read -r _fms_tpl; do
          [ -n "$_fms_tpl" ] || continue
          # rail round-1 F2/F4 — FMS_DELIVERED_TEMPLATES arrives through the
          # ENVIRONMENT, so it is untrusted here exactly as the route table is.
          # An absolute or `..`-bearing entry would enter the manifest as a
          # framework-owned path outside the install, which a manifest-honouring
          # uninstall then acts on. Same predicate, one place.
          if ! _wbm_route_relpath_ok "$_fms_tpl"; then
            echo "    ERROR: delivered-template entry REJECTED (not a confined relative path): '$_fms_tpl'" >&2
            continue
          fi
          # rail round-3 F1 — and it must be a destination the SHARED TABLE
          # declares. Shape rules are a denylist; this is the whitelist.
          if ! _wbm_route_dest_declared "$_fms_tpl"; then
            echo "    ERROR: delivered-template entry REJECTED (not a destination declared in $_WBM_ROUTES_TSV): '$_fms_tpl'" >&2
            continue
          fi
          printf '%s\n' "$_fms_tpl"
        done
      fi
    fi

    [ "$_fms_te_had_f" = "1" ] || set +f
  } | LC_ALL=C sort -u
}

# _framework_manifest_files — expand every target entry into its per-file
# relpaths, relative to FMS_ROOT. Directories are walked (regular files only;
# symlinks are NOT followed into — a symlinked file is emitted as its own
# relpath and the manifest writer records it as a LINK record). EXCLUDES the
# manifest dotfile + .claude.bak/. Sorted + deduped. Missing entries (e.g. a
# profile dir absent on disk) are silently skipped — profile-awareness.
_framework_manifest_files() {
  _fms_root="${FMS_ROOT:-.}"
  {
    _framework_target_entries | while IFS= read -r _fms_entry; do
      [ -n "$_fms_entry" ] || continue
      _fms_abs="$_fms_root/$_fms_entry"
      if [ -f "$_fms_abs" ] || [ -L "$_fms_abs" ]; then
        # A plain file (or symlinked file) target.
        printf '%s\n' "$_fms_entry"
      elif [ -d "$_fms_abs" ]; then
        # Walk the directory for regular files + symlinks. `-print` with a
        # leading "./"-stripped relpath; we re-root each hit at $_fms_entry.
        # bash 3.2-safe: no mapfile; pipe find into a read loop.
        find "$_fms_abs" \( -type f -o -type l \) -print 2>/dev/null | while IFS= read -r _fms_hit; do
          # Strip the "$_fms_root/" prefix to get a repo-relative path.
          _fms_rel="${_fms_hit#"$_fms_root"/}"
          printf '%s\n' "$_fms_rel"
        done
      fi
      # else: entry absent on disk for this profile — skip (profile-aware).
    done
  } | grep -v -e '^\.claude/\.install-manifest\.sha256$' \
            -e '^\.claude\.bak/' \
            -e '/\.claude\.bak/' \
            -e '/__pycache__/' \
            -e '\.pyc$' \
    | while IFS= read -r _fms_out; do
        # PLAN-161 U2 (CF-7): never record framework-internal excluded paths
        # in the baseline — recording them would legitimize a mis-install
        # (and the upgrade would re-add what an adopter deleted by hand).
        if ! _framework_path_excluded "$_fms_out"; then
          printf '%s\n' "$_fms_out"
        fi
      done \
    | LC_ALL=C sort -u
}

# _write_baseline_manifest — THE single baseline-manifest generator (ADR-155
# decision (iv)). Called by install.sh write_install_manifest AND by upgrade.sh
# after a successful upgrade, so a long-lived adopter who upgrades but never
# re-runs install.sh acquires/refreshes a manifest.
#
# Inputs (callers export these before calling):
#   FMS_ROOT          — the installed target root (paths are relative to it)
#   FMS_PROFILE_PARTS — space-separated profile list (profile-aware enumeration)
#   FMS_MODE          — "link" to emit LINK records for symlinks, else "copy"
# Requires _hash_file (from _hash_lib.sh) on PATH. Writes validated records to
# $1 (the manifest path) atomically. Fail-open: returns 0 with a stderr NOTE on
# any problem; never aborts the caller.
#
# Grammar:
#   <64hex>  <relpath>          — content hash
#   LINK  <relpath>  <target>   — link-mode symlink (content == source)

# Does FMS_HASH_ROOT apply to this relpath? UNSET FMS_HASH_ROOT_PATHS means
# ALL of them — the upgrade posture, where every enumerated file must record
# what the framework SHIPS. install.sh needs the opposite default for most of
# the tree: it RENDERS templates (`.claude/team.md`, skills, `{{X}}`
# placeholders under --project et al), so those legitimately differ from
# source and their baseline must be the rendered TARGET. A global
# FMS_HASH_ROOT on an install rerun rewrote every rendered file's hash to the
# unrendered source, which doctor.sh reads as widespread adopter drift and
# later upgrades read as customized => the files stop being refreshed (codex
# W1 round 8, P1). Scoping the override to the ownership-continuity paths
# keeps the round-5 fix (an EDITED delivered SPEC must not be re-baselined as
# framework-owned, or uninstall would delete the adopter's fork) without
# touching the rendered tree. Prefix match: an entry covers the path itself
# and everything under it.
_wbm_hash_root_applies() {
  [ -n "${FMS_HASH_ROOT_PATHS:-}" ] || return 0
  _hra_rel="$1"
  _hra_oldIFS="$IFS"
  IFS='
'
  for _hra_p in $FMS_HASH_ROOT_PATHS; do
    [ -n "$_hra_p" ] || continue
    case "$_hra_rel" in
      "$_hra_p"|"$_hra_p"/*)
        IFS="$_hra_oldIFS"
        return 0
        ;;
    esac
  done
  IFS="$_hra_oldIFS"
  return 1
}

# May this relpath be serialized as a LINK record? UNSET FMS_LINK_PATHS means
# ANY live symlink may — correct on the INSTALL path, where the installer
# itself created every symlink it is about to record. On the UPGRADE rewrite
# that default is too wide (codex W1 round 10, P2): FMS_MODE=link is inferred
# from the presence of ANY prior LINK record, and every live symlink then
# serializes as a delivery record — including an adopter's OWN symlink
# preserved inside an enumerated directory like `.claude/hooks/`, converting
# an unowned path into framework-managed content that doctor.sh polices.
# upgrade.sh passes the exact set of pre-upgrade LINK relpaths instead.
_wbm_link_allowed() {
  [ -n "${FMS_LINK_PATHS:-}" ] || return 0
  _wla_rel="$1"
  _wla_oldIFS="$IFS"
  IFS='
'
  for _wla_p in $FMS_LINK_PATHS; do
    [ -n "$_wla_p" ] || continue
    if [ "$_wla_rel" = "$_wla_p" ]; then
      IFS="$_wla_oldIFS"
      return 0
    fi
  done
  IFS="$_wla_oldIFS"
  return 1
}

# --- PLAN-167 W2.3: the DECISION reaches the generator ----------------------
# _ownership_verdict chooses a hash_source per conditional surface; the writer
# obeys it instead of falling back to a default. Across all 62 rows of the
# table the default (HASH_TARGET) is never the correct answer, and it is
# exactly what let three P1 defects re-baseline adopter content as
# framework-owned (docs §3.4).
_wbm_declared_hash_source() {
  case "$1" in
    SPEC/v1|SPEC/v1/*)          printf '%s' "${FMS_HASH_SOURCE_SPEC:-}" ;;
    PROTOCOL.md)                printf '%s' "${FMS_HASH_SOURCE_PROTOCOL:-}" ;;
    .claude/.framework-version) printf '%s' "${FMS_HASH_SOURCE_MARKER:-}" ;;
    # PLAN-183 W5 (OQ-4, MIXED lane): the RENDERED delivery. Its bytes exist in
    # NO checkout — `sed s/{{OWNER_HANDLE}}/<handle>/` at install.sh:1508
    # produces them — so the route reader has nothing to hash and the
    # non-conditional lane can only DROP it. The conditional lane is the one
    # that can express "the target IS the delivered bytes" (HASH_TARGET on a
    # fresh render) and "carry what was recorded" (HASH_PRIOR_RECORD on
    # continuity), which is exactly the PROTOCOL.md pointer's situation.
    # The 5 VERBATIM routes stay on the non-conditional lane: they have real
    # source bytes and the route reader resolves them.
    .github/CODEOWNERS)         printf '%s' "${FMS_HASH_SOURCE_CODEOWNERS:-}" ;;
    *)                          printf '' ;;
  esac
}

_wbm_is_conditional() {
  case "$1" in
    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
    .github/CODEOWNERS) return 0 ;;
  esac
  return 1
}

# --- PLAN-183 W5 (D3): the THIRD reader of the shared delivery-route table --
# Defect D3: this generator resolved every framework path as "$root/$rel",
# which assumes the SOURCE relpath equals the DESTINATION relpath. That is
# false for every route install.sh delivers out of `templates/` — on the
# upgrade path (FMS_HASH_ROOT=$SOURCE_DIR) `docs/BRANCH-PROTECTION.md` hashes
# the ROOT HOMONYM (wrong bytes recorded as the framework baseline) and
# `.github/*.template` hits the `continue` and vanishes from the baseline in
# SILENCE. The route table is the one place that answers "which source is
# this destination?"; a local branch here would re-open the class CLAUDE.md §4
# closed twice already (PLAN-182 16 modules -> one resolver; PLAN-167
# _ownership_verdict).
#
# Same table, same idiom as scripts/doctor.sh:_route_source and
# scripts/tests/_parity_classify.py. bash 3.2 floor: no `declare -A`, so the
# lookup is a linear scan over ~7 rows. Skip guards act on the FIRST FIELD
# only (the ownership_table.tsv idiom).
#
# rc 0 = identity route, source relpath on stdout
# rc 1 = no row for this destination (the normal case for every framework
#        path that IS identity-mapped: callers keep today's behaviour)
# rc 2 = RENDERED, or the row is malformed => there are no framework source
#        bytes to hash. Fail-CLOSED (CLAUDE.md §4: fail-open on
#        infrastructure, fail-closed on INPUT). `${_wbm_rs_transform:-}` is
#        deliberately an unbraced-default-EMPTY: `:-identity` was the rail
#        S325 fail-OPEN finding that let a truncated row be treated as
#        copyable.
#
# --- rail round-6 F3: the table has ONE source — the running checkout ------
# The table sits NEXT TO this library (scripts/). Both callers source it via
# an absolute $SCRIPT_DIR (install.sh:251, upgrade.sh:95), so BASH_SOURCE is
# absolute and the lookup never depends on the caller's cwd.
#
# It is resolved UNCONDITIONALLY here, which is the point: this assignment
# CLOBBERS any inherited value, so the environment is not a channel into a
# table that drives WRITES (upgrade delivers into $TARGET, doctor --repair
# copies into it).
#
# WHAT ROUND 6 REMOVED AND WHY. Round 5 kept an environment override behind a
# test switch (an opt-in variable plus a candidate path physically under
# ${TMPDIR:-/tmp}). Both conditions are readable and writable by anyone who
# can influence the environment of an upgrade — setting TMPDIR is the same
# gesture as setting the table — so the pair was never a production trust
# boundary; it was a fixture loader living inside a production entrypoint. The
# cure is not a stronger switch (that class regenerates: see round 3 F1 and
# PLAN-185 W0) but the REMOVAL of the mechanism. Fixtures are now exercised the
# way a real run is: against a COPIED framework tree whose own
# scripts/delivery-routes.tsv is the fixture — the copy's library reads the
# copy's table because BASH_SOURCE says so.
#
# The variable is deliberately NOT named FMS_*: every FMS_* name in this file
# is an input knob a caller may set (FMS_ROOT, FMS_HASH_ROOT, FMS_PRIOR_MANIFEST,
# FMS_DELIVERED_TEMPLATES), and keeping that prefix would invite the next
# author to re-open the channel. `_WBM_ROUTES_TSV` is internal state.
#
# ONE in-process re-point survives, by design and with exactly one production
# user: upgrade.sh copies the table's BYTES to a snapshot before a `--pin`
# checkout can move the source tree, then assigns this variable (rail round-2
# F2). That is code running in the process after sourcing, not an environment
# read; the oracles assert that no THIRD production assignment exists.
_FMS_LIB_DIR="$( dirname "${BASH_SOURCE[0]:-$0}" )"
_WBM_ROUTES_TSV="$_FMS_LIB_DIR/delivery-routes.tsv"

# --- rail round-1 F2: the table is UNTRUSTED INPUT -------------------------
# The table is a FILE, and a file is input even when it ships with the code: a
# partial checkout, a bad merge or a tampered tree all reach these fields, and
# every field reaches a filesystem path. Round 6 removed the environment
# channel (above); it did NOT make the CONTENT trusted — the validators below
# are what a row has to satisfy, wherever the bytes came from.
# MEASURED pre-cure, S327: a row with
# `dest=../../outside/PWNED.md` was accepted rc=0 by both readers and
# upgrade.sh's `_up_deliver_template` wrote 536 bytes to
# `$TARGET/../../outside/PWNED.md` — a real write outside the requested
# target, before any ownership gate. A row with `src=../../../../etc/passwd`
# reached `cp "$SOURCE_DIR/$src"` the same way, delivering foreign bytes as
# framework content.
#
# A relpath is VALID only when it is: non-empty; RELATIVE (no leading `/`);
# free of any `..` segment (leading, embedded or trailing); free of a leading
# `./`; free of `//`; free of backslashes; and free of whitespace and control
# characters. The predicate ENUMERATES what is acceptable and rejects
# everything else — the "declare the safe forms, not the unsafe ones"
# architecture PLAN-185 W0 arrived at after the same class regenerated three
# times under review.
#
# Deliberately NOT a realpath() check: the fields name paths that do not exist
# yet (a fresh INSTALL destination), so lexical confinement is the only
# property available at read time. The physical confinement assertion lives at
# the write site in upgrade.sh (_up_tpl_confined), belt and braces.
#
# rail round-3 F1: GLOB METACHARACTERS are rejected too. MEASURED pre-cure
# (S327): `FMS_DELIVERED_TEMPLATES='docs/*'` passed this predicate — the entry
# was pathname-EXPANDED by the consumer before it ever got here, so what the
# predicate saw was `docs/ACCELERATORS.md`, a perfectly confined relpath. 125
# unrelated adopter files entered the baseline as framework-owned, which a
# manifest-honouring uninstall deletes on a hash match. The expansion itself is
# killed at the consumer (`set -f` + a quoted read loop), but a path that
# CONTAINS a glob metacharacter is also not a path this framework ever ships,
# so refusing it here is the second, order-independent wall.
_wbm_route_relpath_ok() {
  case "${1:-}" in
    "")            return 1 ;;   # empty
    /*)            return 1 ;;   # absolute
    ./*)           return 1 ;;   # leading ./
    ..|../*)       return 1 ;;   # leading ..
    */../*)        return 1 ;;   # embedded ..
    */..)          return 1 ;;   # trailing ..
    *//*)          return 1 ;;   # empty segment
    *\\*)          return 1 ;;   # backslash
    *\**)          return 1 ;;   # glob metacharacter *
    *\?*)          return 1 ;;   # glob metacharacter ?
    *\[*)          return 1 ;;   # glob metacharacter [
    *\]*)          return 1 ;;   # glob metacharacter ]
    *[[:space:]]*) return 1 ;;   # whitespace (incl. tab/newline)
    *[[:cntrl:]]*) return 1 ;;   # control characters
  esac
  return 0
}

# --- rail round-5 F1: the DELIVERY DOMAIN, fixed in CODE -------------------
# The table says HOW to route; this says WHERE delivery may EVER write.
#
# WHY THIS EXISTS: `_wbm_route_dest_declared` (round 3) is a whitelist of
# declared destinations, but it reads the SAME table it is meant to constrain —
# so a well-formed hostile table simply declares its own destinations and the
# whitelist agrees with it. MEASURED pre-cure (S327): a row
# `.git/hooks/pre-commit <- scripts/install.sh, identity` passed every lexical
# gate, kept `routes == rows`, was copied into the absent destination, was
# recorded in the manifest, and the upgrade exited 0. A confined relative path
# is not the same property as a path this framework is allowed to deliver.
#
# The domain is a CODE constant, unreachable from any input: destinations live
# under `docs/` or `.github/` — the two trees this wave delivers, by design
# (ADR-194 §1/§4) — and sources live under `templates/`. All six shipped routes
# satisfy it; widening it is an ADR amendment, not a table edit.
#
# rail round-7 F1 — "under .github/" is NOT the property this wave needs, and
# MEASURED pre-cure (S327) the whole tree was in domain: `.github/dependabot.yml`,
# `.github/workflows/pwn.yml` and, worst, `.github/workflows/validate.yml`
# ACCEPTED. That last one is the shipped `validate.yml.template` route with four
# characters removed from its destination: delivery would then write a LIVE
# workflow into the adopter, contradicting the table's own `note` ("the adopter
# never gets a live workflow from install") while the upgrade exits 0.
# So the domain enumerates the INERT FORMS instead of a subtree:
#   docs/<name>.md                    — one segment, Markdown, inert by content;
#   .github/CODEOWNERS                — the rendered route (not executable);
#   .github/CODEOWNERS.template       — its mutually exclusive twin;
#   .github/workflows/<name>.template — one segment under workflows/, and the
#                                       `.template` suffix is what keeps GitHub
#                                       Actions from ever loading the file.
# Nothing else — no second segment, no other basename, no other extension.
# This is the same inversion round 3 F1 and PLAN-185 W0 already paid for:
# enumerate what is PROVEN safe, classify the rest as refused. Widening it is
# an ADR-194 amendment, never a table edit.
#
# $1 = destination relpath. $2 = source relpath, OPTIONAL: the write site holds
# only the destination, and passing an EMPTY $2 is a rejection (not a skip), so
# the one-argument form is the only way to check the destination alone.
# rc 0 = inside the domain.
_wbm_route_domain_ok() {
  case "${1:-}" in
    docs/*)
      _wbm_rd_leaf="${1#docs/}"
      case "$_wbm_rd_leaf" in
        ""|*/*) return 1 ;;   # empty, or more than one segment
        .md)    return 1 ;;   # ".md" is an extension, not a name
        *.md)   ;;
        *)      return 1 ;;
      esac
      ;;
    .github/CODEOWNERS|.github/CODEOWNERS.template) ;;
    .github/workflows/*)
      _wbm_rd_leaf="${1#.github/workflows/}"
      case "$_wbm_rd_leaf" in
        ""|*/*)     return 1 ;;   # empty, or nested under workflows/
        .template)  return 1 ;;   # bare suffix, no workflow name
        *.template) ;;
        *)          return 1 ;;   # anything GitHub Actions would LOAD
      esac
      ;;
    *) return 1 ;;
  esac
  if [ "$#" -ge 2 ]; then
    case "${2:-}" in
      templates/?*) ;;
      *) return 1 ;;
    esac
  fi
  return 0
}

# --- rail round-7 F2: PHYSICAL confinement of the SOURCE --------------------
# The destination side has had physical confinement since round 1 F2; the
# SOURCE side had only the lexical predicate, and `[ -f ]`, `cp`, `cat` and
# `sha256` all FOLLOW symlinks. MEASURED pre-cure (S327): with
# `templates/docs/BRANCH-PROTECTION.md` a symlink to a regular file outside the
# checkout, `[ -f ]` answered true and the delivered bytes hashed IDENTICAL to
# the foreign file — foreign content installed into an adopter tree as
# framework content, with the manifest then recording it as framework-owned.
# A symlinked ANCESTOR (`templates/docs -> /elsewhere`) does the same thing and
# passes every per-path lexical check.
#
# Two independent walls, both required:
#   1. NO SYMLINK COMPONENT — every component of $2 under the physical root is
#      tested with `-L`, leaf included. A real checkout of this framework has
#      ZERO symlinks (measured: 0 under templates/, .claude/, docs/, and 0 in
#      the whole tree excluding .git), so this costs production nothing.
#   2. PHYSICAL CONTAINMENT — the deepest EXISTING ancestor of the source must
#      resolve (cd -P/pwd -P; the bash 3.2 floor has no realpath) under the
#      PHYSICALLY resolved root. "Deepest existing", not "the parent", so a
#      source that is simply ABSENT — the `--pin` lane, where the destination
#      list is this upgrader's and the sources are the pin's — still reaches
#      its caller's `-f` test and keeps its "SKIPPED (source missing)" verdict
#      instead of being renamed into a confinement refusal.
#
# $1 = source root (absolute). $2 = source relpath.
# rc 0 = usable. rc 1 = refuse, with the reason in _WBM_SRC_CONFINE_WHY (a
# refusal nobody can NAME is the silence D3 was made of).
_WBM_SRC_CONFINE_WHY=""
_wbm_source_confined() {
  _WBM_SRC_CONFINE_WHY=""
  _wbm_sc_root="${1:-}"
  _wbm_sc_rel="${2:-}"
  if [ -z "$_wbm_sc_root" ] || [ -z "$_wbm_sc_rel" ]; then
    _WBM_SRC_CONFINE_WHY="empty source root or source relpath"
    return 1
  fi
  if ! _wbm_route_relpath_ok "$_wbm_sc_rel"; then
    _WBM_SRC_CONFINE_WHY="'$_wbm_sc_rel' is not a confined relative path"
    return 1
  fi
  # `|| true` is load-bearing under `set -euo pipefail`: a failing `cd -P`
  # would abort the caller instead of reaching the named refusal below.
  _wbm_sc_phys="$( cd -P "$_wbm_sc_root" 2>/dev/null && pwd -P || true )"
  if [ -z "$_wbm_sc_phys" ]; then
    _WBM_SRC_CONFINE_WHY="the source root '$_wbm_sc_root' does not resolve"
    return 1
  fi
  _wbm_sc_walk="$_wbm_sc_phys"
  _wbm_sc_rest="$_wbm_sc_rel"
  while [ -n "$_wbm_sc_rest" ]; do
    case "$_wbm_sc_rest" in
      */*) _wbm_sc_seg="${_wbm_sc_rest%%/*}"; _wbm_sc_rest="${_wbm_sc_rest#*/}" ;;
      *)   _wbm_sc_seg="$_wbm_sc_rest";       _wbm_sc_rest="" ;;
    esac
    _wbm_sc_walk="$_wbm_sc_walk/$_wbm_sc_seg"
    if [ -L "$_wbm_sc_walk" ]; then
      _WBM_SRC_CONFINE_WHY="component '$_wbm_sc_seg' of '$_wbm_sc_rel' is a symlink — reading it would deliver bytes from outside the checkout"
      return 1
    fi
  done
  _wbm_sc_anc="$( dirname "$_wbm_sc_phys/$_wbm_sc_rel" )"
  while [ -n "$_wbm_sc_anc" ] && [ ! -d "$_wbm_sc_anc" ]; do
    _wbm_sc_next="$( dirname "$_wbm_sc_anc" )"
    [ "$_wbm_sc_next" != "$_wbm_sc_anc" ] || break
    _wbm_sc_anc="$_wbm_sc_next"
  done
  _wbm_sc_res="$( cd -P "$_wbm_sc_anc" 2>/dev/null && pwd -P || true )"
  if [ -z "$_wbm_sc_res" ]; then
    _WBM_SRC_CONFINE_WHY="the nearest existing ancestor of '$_wbm_sc_rel' does not resolve"
    return 1
  fi
  case "$_wbm_sc_res" in
    "$_wbm_sc_phys"|"$_wbm_sc_phys"/*) return 0 ;;
  esac
  _WBM_SRC_CONFINE_WHY="'$_wbm_sc_rel' resolves to $_wbm_sc_res, outside the source checkout $_wbm_sc_phys"
  return 1
}

# One row's fields, validated together. Emits a breadcrumb NAMING the offending
# row on stderr — a rejection nobody can see is the silence D3 was made of.
# rc 0 = the row may be used; rc 1 = rejected.
#
# This is the ONE choke point every reader passes through (_wbm_route_src via
# _wbm_route_meta, _wbm_route_dests, and therefore _wbm_route_dest_declared),
# which is why the round-5 domain check lands here and not in each caller: a
# rejected row drops out of _wbm_route_dests, `routes < rows` becomes true, and
# upgrade.sh's AC-9 precondition turns the whole delivery into a named failure
# with exit 3 (rounds 3/4 semantics) instead of a partial write.
_wbm_route_row_ok() {
  if ! _wbm_route_relpath_ok "${1:-}"; then
    echo "    ERROR: delivery-route row REJECTED (invalid destination): '${1:-}' in $_WBM_ROUTES_TSV" >&2
    return 1
  fi
  if ! _wbm_route_relpath_ok "${2:-}"; then
    echo "    ERROR: delivery-route row REJECTED (invalid source '${2:-}') for destination '${1}' in $_WBM_ROUTES_TSV" >&2
    return 1
  fi
  if ! _wbm_route_domain_ok "${1:-}" "${2:-}"; then
    echo "    ERROR: delivery-route row REJECTED (outside delivery domain): '${1:-}' <- '${2:-}' in $_WBM_ROUTES_TSV — delivery writes ONLY docs/<name>.md, .github/CODEOWNERS[.template] or .github/workflows/<name>.template, from templates/" >&2
    return 1
  fi
  return 0
}

# --- rail round-5 F4: ONE accessor for a row's metadata --------------------
# Prints "<src><TAB><transform>" for the row naming destination $1, AFTER the
# row has passed _wbm_route_row_ok.
#   rc 0 = a valid row exists (its transform may be ANY declared value —
#          judging the transform is the caller's job, reading it is not);
#   rc 1 = no table, or no row for this destination;
#   rc 2 = the row exists and was REJECTED (never collapse this into rc=1:
#          rc=1 is answered by the callers' identity fallback "$root/$rel",
#          which for a poisoned row hands back exactly the D3 behaviour).
#
# WHY: upgrade.sh's rendered-CODEOWNERS branch used to pull `src` and
# `transform` out of the table with its own two `awk` calls — a FOURTH parser
# of the shared table, which ADR-194 vetoes by name, and one that would not
# have inherited the round-1/3/5 validators or the round-4 unterminated-row
# fix. This is the accessor it calls instead. _wbm_route_src is now a thin
# projection of the same row, so the file holds ONE loop over the table for
# per-destination lookups, not two that can drift.
#
# rail round-4 F4 — `|| [ -n "$dest" ]`: a final row with NO trailing newline
# fills the read variables but returns non-zero, so a bare `while read` DROPS
# it. MEASURED pre-cure (S327) on a newline-stripped copy of the real table:
# _wbm_route_dests emitted 5 of 6 destinations and _wbm_route_rows_total
# counted 5 — the two agreed, so upgrade.sh's AC-9 precondition
# (routes == rows) PASSED and the run shipped omitting the last delivery,
# exit 0. A disagreement is visible; an agreed-upon undercount is not.
# The row is still put through _wbm_route_row_ok: "process it" is not "trust
# it", and a TRUNCATED final row (missing the transform field) still resolves
# fail-closed at the caller, which sees an empty transform.
# bash 3.2: `read` clears the variables on a true EOF, so the guard is false
# on the next pass and the loop terminates (verified on 3.2.57 for the
# unterminated, terminated and empty-file cases).
# It ALSO publishes the two fields as _WBM_ROUTE_SRC / _WBM_ROUTE_TRANSFORM
# (always reset at entry, filled only on rc=0). That is not decoration: it lets
# a hot caller read them WITHOUT a command substitution. doctor.sh asks
# _wbm_route_src once per manifest record — several hundred per run — and a
# subshell per record is a fork per record for a linear scan of six rows.
_wbm_route_meta() {
  _wbm_rm_want="${1:-}"
  _wbm_rm_rc=1
  _WBM_ROUTE_SRC=""
  _WBM_ROUTE_TRANSFORM=""
  [ -n "$_wbm_rm_want" ] || return 1
  # rail round-6 F2 — the TABLE is validated before any ROW is consumed, and
  # an unusable table answers 2, never 1. rc=1 is the identity fallback
  # ("$root/$rel") every caller applies, which for a table nobody could parse
  # is defect D3/D4 arriving through a header instead of a wrong branch. This
  # also SUBSUMES the old `[ ! -f ]` check: a missing file is one of the ways
  # a table is unusable, and it now gets the same fail-closed answer.
  _wbm_route_table_gate || return 2
  while IFS="$( printf '\t' )" read -r _wbm_rm_dest _wbm_rm_src _wbm_rm_transform _wbm_rm_rest \
        || [ -n "${_wbm_rm_dest:-}" ]; do
    if [ -z "${_wbm_rm_dest:-}" ]; then continue; fi
    case "$_wbm_rm_dest" in \#*|dest) continue ;; esac
    if [ "$_wbm_rm_dest" != "$_wbm_rm_want" ]; then continue; fi
    if ! _wbm_route_row_ok "$_wbm_rm_dest" "${_wbm_rm_src:-}"; then
      _wbm_rm_rc=2
      break
    fi
    _WBM_ROUTE_SRC="$_wbm_rm_src"
    _WBM_ROUTE_TRANSFORM="${_wbm_rm_transform:-}"
    printf '%s\t%s\n' "$_WBM_ROUTE_SRC" "$_WBM_ROUTE_TRANSFORM"
    _wbm_rm_rc=0
    break
  done < "$_WBM_ROUTES_TSV"
  return "$_wbm_rm_rc"
}

# The IDENTITY projection of _wbm_route_meta: the source relpath, and only for
# a route the framework copies VERBATIM.
#   rc 0 = identity route, source relpath on stdout
#   rc 1 = no row (callers keep today's behaviour: "$root/$rel")
#   rc 2 = RENDERED, or malformed => there are no framework source bytes to
#          hash. `${transform}` is compared against the literal `identity` and
#          nothing else: `:-identity` as a DEFAULT was the rail S325 fail-OPEN
#          finding that let a truncated row be treated as copyable.
_wbm_route_src() {
  _wbm_rs_rc=0
  # In-process (stdout discarded, fields read from the globals), never
  # `$( _wbm_route_meta ... )`: this is the per-manifest-record hot path.
  _wbm_route_meta "${1:-}" >/dev/null || _wbm_rs_rc=$?
  [ "$_wbm_rs_rc" -eq 0 ] || return "$_wbm_rs_rc"
  case "${_WBM_ROUTE_TRANSFORM:-}" in
    identity)
      if [ -z "${_WBM_ROUTE_SRC:-}" ]; then
        return 2          # declared identity but no source: malformed
      fi
      printf '%s\n' "$_WBM_ROUTE_SRC"
      return 0
      ;;
  esac
  return 2
}

# Every destination the table declares, one per line. Callers that must decide
# WHICH routes they delivered (upgrade.sh) iterate this instead of carrying a
# second copy of the destination list.
#
# F2: a row that fails validation is NOT emitted. The count therefore DROPS
# below _wbm_route_rows_total, which is what upgrade.sh's AC-9 precondition
# turns into a named delivery failure — the rejected row can never reach a
# write, and it cannot be swallowed either.
_wbm_route_dests() {
  # rail round-6 F2 — same table gate as _wbm_route_meta, and it is what makes
  # a corrupted header a NAMED delivery failure: zero destinations enumerated
  # => routes=0 => upgrade.sh's AC-9 precondition refuses the whole delivery
  # with exit 3, instead of the readers walking data rows under a header that
  # no longer says what the columns mean.
  _wbm_route_table_gate || return 2
  # rail round-4 F4 — see the note on _wbm_route_src: an unterminated final row
  # is READ, not dropped. This loop and _wbm_route_rows_total are the numerator
  # and the denominator of the AC-9 precondition, so they must agree about
  # WHICH rows exist for the comparison to mean anything.
  while IFS="$( printf '\t' )" read -r _wbm_rd_dest _wbm_rd_src _wbm_rd_rest \
        || [ -n "${_wbm_rd_dest:-}" ]; do
    if [ -z "${_wbm_rd_dest:-}" ]; then continue; fi
    case "$_wbm_rd_dest" in \#*|dest) continue ;; esac
    _wbm_route_row_ok "$_wbm_rd_dest" "${_wbm_rd_src:-}" || continue
    printf '%s\n' "$_wbm_rd_dest"
  done < "$_WBM_ROUTES_TSV"
}

# --- rail round-3 F1: the WHITELIST ---------------------------------------
# Is $1 byte-equal to a destination the (already validated) route table
# declares? rc 0 = yes.
#
# WHY A WHITELIST AND NOT ONE MORE SHAPE RULE: the delivered-template list
# reaches the generator through the ENVIRONMENT, and every previous cure of
# this class enumerated what is FORBIDDEN — absolute, `..`, backslash, now
# glob. Round 3 found the next shape (pathname expansion produced entries that
# were confined AND legitimate-looking), which is the signature of a denylist
# architecture regenerating. The table already answers the only question that
# matters — "may the framework own this destination at all?" — for six paths,
# and it is the single source of truth the whole wave is built on. Anything
# that is not a declared destination can never be baselined from the
# environment, whatever its shape. This is the "enumerate what is PROVEN safe"
# inversion PLAN-185 W0 arrived at after the same class regenerated three
# times under review.
#
# Fail-CLOSED by construction: no table (or an unreadable one) yields an empty
# destination list, so every entry is rejected. Ownership is under-claimed,
# which is the recoverable direction (CLAUDE.md §4).
_wbm_route_dest_declared() {
  _wbm_dd_want="${1:-}"
  [ -n "$_wbm_dd_want" ] || return 1
  _wbm_dd_rc=1
  # Redirection, not a pipe: the loop must run in THIS shell or _wbm_dd_rc
  # would be lost with the subshell.
  while IFS= read -r _wbm_dd_line; do
    if [ "$_wbm_dd_line" = "$_wbm_dd_want" ]; then
      _wbm_dd_rc=0
      break
    fi
  done <<< "$( _wbm_route_dests 2>/dev/null || true )"
  return "$_wbm_dd_rc"
}

# How many DATA rows the table holds, validated or not. The denominator for
# the AC-9 precondition: `_wbm_route_dests | wc -l` < this means at least one
# row was rejected. Parsing stays in the ONE reader — a caller counting rows
# itself would be the second copy of the table CLAUDE.md §4 forbids.
_wbm_route_rows_total() {
  _wbm_rt_n=0
  # rail round-6 F2 — the DENOMINATOR obeys the same gate as the numerator. If
  # only one of the two refused, `routes == rows` could be satisfied by two
  # numbers derived from different premises, which is exactly the agreed-upon
  # undercount round 4 F4 closed.
  _wbm_route_table_gate || { printf '0\n'; return 2; }
  # rail round-4 F4 — the DENOMINATOR must count the unterminated final row too
  # (see _wbm_route_src). Dropping it here as well is what made the pre-cure
  # undercount INVISIBLE: routes and rows both said 5 and the precondition was
  # satisfied by two wrong numbers agreeing.
  while IFS="$( printf '\t' )" read -r _wbm_rt_dest _wbm_rt_rest \
        || [ -n "${_wbm_rt_dest:-}" ]; do
    if [ -z "${_wbm_rt_dest:-}" ]; then continue; fi
    case "$_wbm_rt_dest" in \#*|dest) continue ;; esac
    _wbm_rt_n=$(( _wbm_rt_n + 1 ))
  done < "$_WBM_ROUTES_TSV"
  printf '%s\n' "$_wbm_rt_n"
}

# --- rail round-4 F3: the table is a REQUIRED input, not an optional one ----
# Is the shared route table PRESENT and shaped like a route table? rc 0 = yes.
#
# Every reader above answers "no table" with rc=1, and rc=1 means "no row for
# this destination" — which the callers answer with the identity fallback
# `$root/$rel`. That is defect D3/D4 verbatim, arriving through a MISSING file
# instead of a wrong branch: on a partial checkout `doctor.sh --repair` would
# hash and copy `$SOURCE_DIR/.github/CODEOWNERS` (this repo's LIVE maintainer
# file) into an adopter tree. A caller that must not degrade to identity asks
# THIS question once, at startup, before any verdict is computed.
#
# It lives here, next to the reader, for the reason the whole wave exists: the
# shape of the table is knowledge the table's owner holds. doctor growing its
# own header parser is exactly the private copy W6 deleted.
#
# Checked: readable regular file; a header row whose first three fields are
# `dest`, `src`, `transform`; and at least one DATA row. An empty-but-present
# table is not a degenerate success — it is a file that would silently deliver
# and repair nothing.
_wbm_route_table_ok() {
  _wbm_tok_tbl="${_WBM_ROUTES_TSV:-}"
  _wbm_tok_why=""
  _wbm_tok_hdr=0
  _wbm_tok_rows=0
  if [ -z "$_wbm_tok_tbl" ]; then
    _WBM_ROUTE_TABLE_WHY="_WBM_ROUTES_TSV is empty"
    return 1
  fi
  if [ ! -f "$_wbm_tok_tbl" ]; then
    _WBM_ROUTE_TABLE_WHY="not a readable file: $_wbm_tok_tbl"
    return 1
  fi
  if [ ! -r "$_wbm_tok_tbl" ]; then
    _WBM_ROUTE_TABLE_WHY="not readable (permissions): $_wbm_tok_tbl"
    return 1
  fi
  while IFS="$( printf '\t' )" read -r _wbm_tok_a _wbm_tok_b _wbm_tok_c _wbm_tok_rest \
        || [ -n "${_wbm_tok_a:-}" ]; do
    if [ -z "${_wbm_tok_a:-}" ]; then continue; fi
    case "$_wbm_tok_a" in \#*) continue ;; esac
    if [ "$_wbm_tok_a" = "dest" ]; then
      if [ "${_wbm_tok_b:-}" = "src" ] && [ "${_wbm_tok_c:-}" = "transform" ]; then
        _wbm_tok_hdr=1
      else
        _wbm_tok_why="header row is 'dest' but its 2nd/3rd fields are '${_wbm_tok_b:-}'/'${_wbm_tok_c:-}', not 'src'/'transform'"
      fi
      continue
    fi
    _wbm_tok_rows=$(( _wbm_tok_rows + 1 ))
  done < "$_wbm_tok_tbl"
  if [ "$_wbm_tok_hdr" -ne 1 ]; then
    _WBM_ROUTE_TABLE_WHY="${_wbm_tok_why:-no 'dest<TAB>src<TAB>transform' header row}: $_wbm_tok_tbl"
    return 1
  fi
  if [ "$_wbm_tok_rows" -lt 1 ]; then
    _WBM_ROUTE_TABLE_WHY="header present but ZERO data rows: $_wbm_tok_tbl"
    return 1
  fi
  _WBM_ROUTE_TABLE_WHY=""
  return 0
}

# --- rail round-6 F2: the table PRECONDITION, for every reader -------------
# Round 4 F3 put _wbm_route_table_ok in front of doctor.sh only. MEASURED
# pre-cure (S327) on the other two readers: with the header row deleted — or
# with its 2nd/3rd column names corrupted to anything but `src`/`transform` —
# _wbm_route_meta and _wbm_route_dests happily consumed the DATA rows,
# _wbm_route_rows_total counted the same rows, `routes == rows` held, and a
# real upgrade DELIVERED and exited 0. A header is not decoration: it is the
# statement that column 2 means "source" and column 3 means "transform", and
# without it the rows are an unlabelled tuple the reader is guessing at.
#
# So the question moves to where every reader already passes: this gate. One
# implementation, three call sites (the three loops that open the table), and
# the oracles assert that a fourth loop cannot be added without one — the
# alternative, a gate per caller, is the private copy this whole wave deletes.
#
# MEMOISED, and the memo is keyed on the table PATH. Not an optimisation for
# its own sake: doctor.sh asks _wbm_route_src once per manifest record and a
# full extra pass over the table per record measured ~20 ms each on this
# machine — hundreds of records means seconds of pure re-reading. Keying on
# the path is safe because, with the environment channel gone (round 6 F3),
# the path changes at most once per process: upgrade.sh's snapshot re-point,
# which the key observes. The named line is therefore printed ONCE per
# verdict, not once per record — a wall of identical errors is its own kind of
# silence.
_WBM_ROUTE_GATE_FOR=""
_WBM_ROUTE_GATE_RC=""
_wbm_route_table_gate() {
  if [ "${_WBM_ROUTE_GATE_FOR:-}" = "${_WBM_ROUTES_TSV:-}" ] && [ -n "${_WBM_ROUTE_GATE_RC:-}" ]; then
    return "$_WBM_ROUTE_GATE_RC"
  fi
  _WBM_ROUTE_GATE_FOR="${_WBM_ROUTES_TSV:-}"
  if _wbm_route_table_ok; then
    _WBM_ROUTE_GATE_RC=0
  else
    _WBM_ROUTE_GATE_RC=1
    echo "    ERROR: delivery-route table REFUSED — ${_WBM_ROUTE_TABLE_WHY:-unknown reason}" >&2
    echo "           Every reader now answers fail-closed and enumerates ZERO routes." >&2
    echo "           Expected a 'dest<TAB>src<TAB>transform' header and at least one data" >&2
    echo "           row. docs/ and .github/ are NOT delivered, and nothing is repaired" >&2
    echo "           or recorded through the identity fallback (that fallback IS D3)." >&2
  fi
  return "$_WBM_ROUTE_GATE_RC"
}

# The digest the PRE-run manifest recorded. Empty when unavailable, which the
# fail-closed branch turns into "do not record" rather than a guess.
#
# rail round-4 F1: EXACT relpath match, via awk on the two-space separator the
# manifest format uses — never a regex. The relpaths this is asked about carry
# `.` (`.github/CODEOWNERS`), and under `grep -E` a `.` matches ANY character,
# so `Xgithub/CODEOWNERS` would have answered for it. upgrade.sh carried its
# own awk for exactly this reason; it now calls this instead, so the manifest
# format has one parser again.
_wbm_prior_digest() {
  [ -n "${FMS_PRIOR_MANIFEST:-}" ] && [ -f "$FMS_PRIOR_MANIFEST" ] || { printf ''; return 0; }
  awk -v want="$1" '
    { i = index($0, "  "); if (i == 0) next
      if (substr($0, i + 2) != want) next
      d = substr($0, 1, i - 1)
      if (length(d) == 64 && d ~ /^[0-9a-f]+$/) { print d; exit } }' \
    "$FMS_PRIOR_MANIFEST" 2>/dev/null || printf ''
}

_write_baseline_manifest() {
  _wbm_manifest="$1"
  if ! command -v _framework_manifest_files >/dev/null 2>&1 \
     || ! command -v _hash_file >/dev/null 2>&1; then
    echo "    NOTE: baseline manifest skipped — hash/enumeration helpers not sourced" >&2
    return 0
  fi
  : "${FMS_ROOT:?_write_baseline_manifest requires FMS_ROOT}"
  # PLAN-183 W5 (D3) fail-CLOSED precondition. Enumerating delivered templates
  # WITHOUT a usable route table would resolve each one as "$root/$rel" —
  # precisely the D3 defect, arriving silently. The table is INPUT, not
  # infrastructure (CLAUDE.md §4), so refuse to record rather than record the
  # wrong bytes; ownership is under-claimed, which is recoverable.
  #
  # rail round-6 F2 — the whole WRITE is abandoned, not just the delivered
  # templates. On the upgrade lane every path under $FMS_HASH_ROOT is resolved
  # through _wbm_route_src, which now answers rc=2 for ALL of them when the
  # table is unusable; carrying on would replace a correct manifest with a
  # near-empty one, and an empty baseline is what uninstall and doctor read
  # next. Leaving the previous manifest untouched is the recoverable direction.
  # The old check asked `[ ! -f ]`; the gate asks the same question and four
  # more (readable, regular, header, ≥1 data row).
  if ! _wbm_route_table_gate; then
    echo "    ERROR: baseline manifest NOT written — the delivery-route table is" >&2
    echo "           unusable (${_WBM_ROUTE_TABLE_WHY:-unknown reason})." >&2
    echo "           Every source would resolve through the identity fallback, which is" >&2
    echo "           defect D3; the manifest already on disk is left as it stands." >&2
    return 0
  fi
  # FMS_HASH_ROOT (optional): hash the FRAMEWORK version of each file from here
  # instead of FMS_ROOT. The ENUMERATION still walks FMS_ROOT (what the target
  # holds), but the recorded baseline must be what the framework SHIPS — never
  # an adopter-customized target file. Without this, upgrade.sh's post-upgrade
  # rewrite (C.7) records hash(customized-but-preserved file) as the baseline,
  # which the NEXT upgrade reads as H_dst==H_base => FRAMEWORK-CHANGED => clobber
  # (the verified C.5 idempotency failure). Default = FMS_ROOT (install path,
  # where the target IS the freshly-written framework version). The root
  # PROTOCOL.md is GENERATED (a pointer), not a source copy, so it always hashes
  # from FMS_ROOT (the target pointer), never FMS_HASH_ROOT. (Codex R1 + dry-run)
  _wbm_hash_root="${FMS_HASH_ROOT:-$FMS_ROOT}"

  _wbm_tmp="$( mktemp "$_wbm_manifest.XXXXXX" 2>/dev/null )" || {
    echo "    NOTE: baseline manifest skipped (mktemp failed) — advisory only" >&2
    return 0
  }

  _framework_manifest_files | while IFS= read -r _wbm_rel; do
    [ -n "$_wbm_rel" ] || continue
    _wbm_abs="$FMS_ROOT/$_wbm_rel"
    # Drop relpaths carrying control chars (line-based manifest).
    case "$_wbm_rel" in
      *[$'\n\r\t']*) continue ;;
    esac
    if [ "${FMS_MODE:-copy}" = "link" ] && [ -L "$_wbm_abs" ] \
       && _wbm_link_allowed "$_wbm_rel"; then
      _wbm_target="$( readlink "$_wbm_abs" 2>/dev/null || true )"
      [ -n "$_wbm_target" ] || continue
      case "$_wbm_target" in
        *[$'\n\r\t']*) continue ;;
      esac
      printf 'LINK  %s  %s\n' "$_wbm_rel" "$_wbm_target" >> "$_wbm_tmp"
    elif [ -L "$_wbm_abs" ]; then
      # A live symlink that did NOT qualify as a LINK record (wrong mode, or
      # rejected by _wbm_link_allowed) must never fall through to the hash
      # branch: POSIX -f FOLLOWS the link, and the record would serialize the
      # ADOPTER's target content as a framework HASH delivery — a new route
      # around INV-2 (repass-r2 part-a V4). No record at all: not delivered.
      echo "    NOTE: symlink $_wbm_rel not recorded (no LINK authorization; refusing to hash through it)" >&2
      continue
    elif [ -f "$_wbm_abs" ]; then
      if [ "$_wbm_rel" = "PROTOCOL.md" ]; then
        # Generated pointer. Use the CANONICAL pointer hash (FMS_PROTOCOL_HASH,
        # exported by upgrade.sh _refresh_protocol_pointer) so a PRESERVED
        # adopter-customized PROTOCOL.md is NOT re-recorded as its own baseline
        # (Codex R2 P0 — else the next upgrade reads H_dst==H_base and clobbers
        # it). On install (no FMS_PROTOCOL_HASH) the target IS the freshly
        # written pointer, so hashing it directly is correct.
        if [ -n "${FMS_PROTOCOL_HASH:-}" ]; then
          _wbm_digest="$FMS_PROTOCOL_HASH"
        else
          _wbm_digest="$( _hash_file "$_wbm_abs" 2>/dev/null || true )"
        fi
      elif _wbm_is_conditional "$_wbm_rel"; then
        _wbm_decl="$( _wbm_declared_hash_source "$_wbm_rel" )"
        case "$_wbm_decl" in
          HASH_SOURCE)
            # FMS_SOURCE_ROOT, never FMS_HASH_ROOT: the global override is an
            # upgrade-only mechanism, and borrowing it here is what dragged
            # install into the r8-F1 rendered-tree regression.
            if [ -n "${FMS_SOURCE_ROOT:-}" ] && [ -f "$FMS_SOURCE_ROOT/$_wbm_rel" ]; then
              _wbm_digest="$( _hash_file "$FMS_SOURCE_ROOT/$_wbm_rel" 2>/dev/null || true )"
            else
              continue   # the framework no longer ships it: record nothing
            fi
            ;;
          HASH_PRIOR_RECORD)   _wbm_digest="$( _wbm_prior_digest "$_wbm_rel" )" ;;
          HASH_CANONICAL_POINTER) _wbm_digest="${FMS_PROTOCOL_HASH:-}" ;;
          HASH_TARGET)         _wbm_digest="$( _hash_file "$_wbm_abs" 2>/dev/null || true )" ;;
          HASH_NONE)           continue ;;
          *)
            # FAIL-CLOSED, scoped to the three conditional surfaces (Owner
            # ratified 2026-08-07). Under-claiming is recoverable; over-claiming
            # is the delete-the-adopter's-file class.
            echo "    NOTE: $_wbm_rel delivered but declared no hash_source —" >&2
            echo "          NOT recorded (fail-closed; ownership under-claimed)" >&2
            continue
            ;;
        esac
        case "$_wbm_digest" in
          "" ) continue ;;
        esac
      else
        # Hash the FRAMEWORK version. When FMS_HASH_ROOT is set (upgrade) and the
        # path is ABSENT there, the framework no longer ships it — OMIT it from
        # the baseline (recording the adopter-retained target file would falsely
        # mark it FRAMEWORK-CHANGED if the framework later reintroduces the
        # path). Codex R2 P1.
        _wbm_hash_path="$_wbm_abs"
        if [ -n "${FMS_HASH_ROOT:-}" ] && _wbm_hash_root_applies "$_wbm_rel"; then
          # PLAN-183 W5 (D3): resolve the SOURCE relpath through the shared
          # route table before touching $_wbm_hash_root. Identity-mapped paths
          # (rc=1, no row) keep today's "$root/$rel" behaviour exactly.
          _wbm_src_rel="$_wbm_rel"
          _wbm_route_rc=0
          _wbm_route_out="$( _wbm_route_src "$_wbm_rel" )" || _wbm_route_rc=$?
          case "$_wbm_route_rc" in
            0) _wbm_src_rel="$_wbm_route_out" ;;
            2)
              # RENDERED (or malformed row): the delivered bytes exist in NO
              # checkout, so this lane has nothing to hash. Today's behaviour
              # was to `continue` SILENTLY — the silence is the defect, not
              # the skip. Name the path.
              echo "    NOTE: $_wbm_rel is delivered through a TRANSFORM (or its route row is malformed) —" >&2
              echo "          no framework source bytes on this lane; NOT recorded (fail-closed)" >&2
              continue
              ;;
            *) : ;;   # rc=1: no route row — identity destination, unchanged
          esac
          if [ -f "$_wbm_hash_root/$_wbm_src_rel" ]; then
            _wbm_hash_path="$_wbm_hash_root/$_wbm_src_rel"
          else
            continue   # framework no longer ships this path — no baseline record
          fi
        fi
        _wbm_digest="$( _hash_file "$_wbm_hash_path" 2>/dev/null || true )"
      fi
      case "$_wbm_digest" in
        [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
        *) continue ;;
      esac
      printf '%s  %s\n' "$_wbm_digest" "$_wbm_rel" >> "$_wbm_tmp"
    fi
  done

  LC_ALL=C sort -u "$_wbm_tmp" > "$_wbm_tmp.sorted" 2>/dev/null && mv "$_wbm_tmp.sorted" "$_wbm_tmp"
  if mv "$_wbm_tmp" "$_wbm_manifest"; then
    echo "    WROTE: $( wc -l < "$_wbm_manifest" | tr -d ' ' ) baseline records -> $_wbm_manifest"
  else
    rm -f "$_wbm_tmp" "$_wbm_tmp.sorted" 2>/dev/null || true
    echo "    NOTE: baseline manifest atomic mv failed — advisory only" >&2
  fi
  return 0
}

# =============================================================================
# PLAN-167 — _ownership_verdict: THE ownership decision.
#
# install.sh and upgrade.sh stop deciding and start executing. Every defect in
# the 35-finding S296 review series was a cell of this space whose answer was
# decided branch-locally, so two branches could disagree about the same
# question and nothing detected it.
#
#   $1 surface        spec | protocol | marker
#   $2 prior_record   none | hash | link_match | link_retargeted
#   $3 live_type      absent | dir | dir_empty | regular | symlink | special
#                     | ancestor_symlink
#   $4 live_content   pristine | legacy_pristine | legacy_pristine_partial
#                     | edited | -
#   $5 source_has     yes | no
#   $6 mode           copy | link
#   $7 ceremony       user | maintainer
#   $8 operation      install_fresh | install_rerun | upgrade
#   $9 skip_requested none | self | descendant
#
#   stdout: "<VERDICT> <HASH_SOURCE>", rc 0
#   rc 1, no output: a combination the legality rules forbid.
#
# PURE: no filesystem, no globals, no environment. Callers observe the nine
# dimensions and pass them in. That purity is what lets the same table drive a
# millisecond unit oracle as well as the ~25-minute end-to-end suite; S296 had
# only the slow instrument, at one cell per ~40-minute round.
#
# ABORT_SURFACE is deliberately NOT produced here (round-1 consensus C2). A
# failed backup is not a property of these nine dimensions — it is the CALLER
# failing to carry out a verdict it was handed. And per INV-3 that failure
# NEVER advances the record: recording a delivery that did not happen is the
# over-claiming direction ADR-155-AMEND-1 §3 forbids.
#
# Contract: docs/ownership-decision-table.md · Truth: scripts/tests/ownership_table.tsv
# =============================================================================
_ownership_verdict() {
  _ov_surface="$1"; _ov_prior="$2";  _ov_ltype="$3"; _ov_lcontent="$4"
  _ov_shas="$5";    _ov_mode="$6";   _ov_cer="$7";   _ov_op="$8"; _ov_skip="$9"

  # Do not touch the surface; decide the RECORD. Ownership continuity and the
  # digit it carries are separate decisions, and moving one without the other
  # produced four distinct defects — so they are resolved together, once.
  _ov_carry() {
    case "$_ov_prior" in
      link_match)      printf 'PRESERVE_OWNED LINK_RECORD';  return 0 ;;
      link_retargeted) printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;
      none)            printf 'PRESERVE_UNOWNED HASH_NONE';  return 0 ;;
    esac
    # prior_record=hash. HASH_TARGET is never an option: it re-baselines the
    # bytes now on disk, which is how a later upgrade comes to overwrite an
    # adopter edit and uninstall comes to delete it.
    if [ "$_ov_surface" = "protocol" ] \
       || [ "$_ov_shas" = "no" ] \
       || [ "$_ov_ltype" = "dir_empty" ]; then
      printf 'PRESERVE_OWNED HASH_PRIOR_RECORD'   # no source bytes to hash
    else
      printf 'PRESERVE_OWNED HASH_SOURCE'
    fi
  }

  # The framework must not claim this path. Whether a record existed changes
  # only which NAME the observation takes (OQ-9 — the evidence that these are
  # one outcome, not two).
  # OQ-9 (ratificada pelo Owner 2026-08-07): PRESERVE_UNOWNED é o único nome.
  # OMIT_RECORD dizia a mesma coisa — sem registro no disco — e diferia apenas
  # por já existir registro antes, que é a coluna prior_record. Um membro de
  # enum redundante é onde dois ramos discordam sobre qual deles se aplica.
  _ov_unowned() { printf 'PRESERVE_UNOWNED HASH_NONE'; }

  # --- Stage A: gates that refuse to act, in priority order ------------------

  # A1. The source cannot deliver this surface.
  if [ "$_ov_shas" = "no" ]; then
    case "$_ov_surface" in
      marker)   printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;  # --pin: readers fall back to VERSION
      protocol) return 1 ;;                                  # R-03: generated, never absent
      *)        _ov_carry; return 0 ;;
    esac
  fi

  # A2. A user ceremony never receives the root surfaces (WS4).
  if [ "$_ov_cer" = "user" ] && [ "$_ov_surface" != "marker" ]; then
    if [ "$_ov_op" = "install_fresh" ]; then printf 'PRESERVE_UNOWNED HASH_NONE'
    else _ov_carry; fi
    return 0
  fi

  # A3. Reachable only by writing THROUGH a symlink, out of the target tree.
  # Always unowned: the relpath sanitizer already dropped any record whose path
  # crosses a symlink, so there is no record left to carry (docs §5.8).
  if [ "$_ov_ltype" = "ancestor_symlink" ]; then _ov_unowned; return 0; fi

  # A4. A leaf symlink is healthy ONLY as the recorded link-mode delivery.
  # The absence of a LINK row is not a match — it is the absence of evidence.
  if [ "$_ov_ltype" = "symlink" ]; then
    if [ "$_ov_prior" = "link_match" ]; then printf 'PRESERVE_OWNED LINK_RECORD'
    else _ov_unowned; fi
    return 0
  fi

  # A5. Anything that exists but is not shaped like this surface is
  # adopter-owned: never write into it, never through it, never block on it.
  case "$_ov_surface" in
    spec)
      case "$_ov_ltype" in special) _ov_unowned; return 0 ;; esac ;;
    protocol|marker)
      case "$_ov_ltype" in dir|dir_empty|special) _ov_unowned; return 0 ;; esac ;;
  esac

  # A6. An explicit skip is honoured as a UNIT — a partial contract refresh is
  # incoherent, so a descendant skip preserves the whole tree.
  if [ "$_ov_skip" != "none" ]; then _ov_carry; return 0; fi

  # --- Stage B: ownership resolution ----------------------------------------
  _ov_owned=""
  if [ "$_ov_prior" = "hash" ] || [ "$_ov_prior" = "link_match" ]; then
    _ov_owned=1
  elif [ "$_ov_ltype" = "absent" ]; then
    _ov_owned=1                                   # new delivery
  elif [ "$_ov_lcontent" = "pristine" ] || [ "$_ov_lcontent" = "legacy_pristine" ]; then
    _ov_owned=1                                   # current-source takeover / legacy migration
  elif [ "$_ov_lcontent" = "degraded" ]; then
    # PLAN-168 W2 (AC-6b, Owner decision D2): a DEGRADED body — byte-exact
    # reconstruction of the {{PROTOCOL_SOURCE}}-literal template the broken
    # upgrade wrote (recognized by _protocol_pointer_is_degraded, NEVER by
    # substring) — is the framework's own output, not adopter content. Owned
    # even without a delivery record, same content-proven takeover doctrine
    # as legacy_pristine (the r20 precedent). Downstream this falls into the
    # protocol REFRESH route: the cure, with the standard backup.
    _ov_owned=1
  fi
  # legacy_pristine_partial is deliberately NOT owned: every regular file may
  # match a shipped release, but a tree carrying an entry the fingerprint
  # cannot inventory has not been inventoried, and a partial inventory must
  # never certify a wholesale replace (ADR-155-AMEND-1 §4).

  if [ -z "$_ov_owned" ]; then _ov_unowned; return 0; fi

  # --- Stage C: execution ---------------------------------------------------
  if [ "$_ov_ltype" = "absent" ]; then
    case "$_ov_surface" in
      protocol) printf 'DELIVER HASH_CANONICAL_POINTER' ;;
      *)        printf 'DELIVER HASH_SOURCE' ;;
    esac
    return 0
  fi

  # An install rerun does not re-deliver an existing surface; it decides the
  # record. Only the upgrade's forced route replaces content.
  if [ "$_ov_op" != "upgrade" ]; then _ov_carry; return 0; fi

  # The pointer is the ONE surface where an adopter edit is PRESERVED rather
  # than treated as a fork. SPEC/v1 is deliberately the opposite: it is the
  # published compliance CONTRACT, so an edit is a fork and the forced route
  # replaces it (ADR-155-AMEND-1 §4). The root PROTOCOL.md is adopter-editable
  # prose, and overwriting a customised one is the verified S238 data loss that
  # ADR-155 decision (iii) exists to close.
  #
  # The recorded digest stays CANONICAL either way: recording the customised
  # bytes would make the NEXT upgrade read H_dst==H_base and clobber them.
  if [ "$_ov_surface" = "protocol" ] && [ "$_ov_lcontent" = "edited" ]; then
    printf 'PRESERVE_OWNED HASH_CANONICAL_POINTER'
    return 0
  fi

  case "$_ov_surface" in
    protocol) printf 'REFRESH HASH_CANONICAL_POINTER' ;;
    *)        printf 'REFRESH HASH_SOURCE' ;;
  esac
}
# =============================================================================
# PLAN-168 W2 (AC-6, Owner decision D1-b) — the ONE protocol-pointer generator.
#
# INV-4 existed because install.sh and upgrade.sh each carried a private copy
# of the pointer heredoc: install substituted {{PROTOCOL_SOURCE}} in a later
# pass, upgrade hashed (and on REFRESH wrote) the body with the token still
# literal. Two bodies for the same file. This library is the cure for the
# CLASS: both callers render through the same function, so the bodies cannot
# diverge again (ADR-155 decision (i), applied to CONTENT — the shared
# enumeration solved WHICH paths both sides touch; this solves WHAT they
# produce).
#
# Sourced by scripts/install.sh and scripts/upgrade.sh (same $SCRIPT_DIR
# pattern as _hash_lib.sh). Bash 3.2-compatible, stdlib/POSIX-tools only.
#
# Functions:
#   _render_protocol_pointer SOURCE_DIR TARGET PROFILE STACK PROTOCOL_SOURCE
#       Emit the COMPLETE healthy file content ("# Protocol reference" header
#       included, trailing newline included). Inside-target checkouts get the
#       relative form; everything else gets the PROTOCOL_SOURCE-resolved form
#       (never the literal token — the caller passes the resolved value).
#   _render_protocol_pointer_degraded TARGET PROFILE STACK
#       Emit the DEGRADED file content: the outside-target template with
#       {{PROTOCOL_SOURCE}} kept literal. This is byte-for-byte what the
#       pre-PLAN-168 upgrade.sh wrote on every refresh — the template text is
#       IDENTICAL across v1.0.1, v1.1.0, v1.2.0 and HEAD (verified by
#       extracting and diffing all four), so ONE skeleton covers the shipped
#       population. Residual out of scope: pre-v1.0.1 trees.
#   _protocol_pointer_is_degraded FILE
#       rc=0 iff FILE is EXACTLY a degraded body the framework produced:
#       the invocation-specific values (TARGET/PROFILE/STACK) are extracted
#       from the file's own upgrade line, the degraded template is re-rendered
#       with them, and the reconstruction must be byte-identical. Any parse
#       failure, any adopter edit anywhere, any deviation => rc=1 (fail toward
#       PRESERVATION — codex rail r1 P1: substring matching would destroy an
#       adopter file that legitimately CONTAINS the token; rail r2 P1: static
#       whole-body hashes cannot match invocation-specific bodies).
# =============================================================================

# PLAN-169 W3.1: literal newline for the case-guard below (command
# substitution would strip it).
_RPP_NL='
'

_render_protocol_pointer() {
  # $1=SOURCE_DIR $2=TARGET $3=PROFILE $4=STACK $5=PROTOCOL_SOURCE(resolved)
  _rpp_src="$1"; _rpp_target="$2"; _rpp_profile="$3"; _rpp_stack="$4"; _rpp_psource="$5"
  case "$_rpp_src" in
    "$_rpp_target"/*)
      _rpp_rel="${_rpp_src#"$_rpp_target"/}"
      printf '%s\n' \
        "# Protocol reference" \
        "" \
        "The full CEO orchestration protocol lives at:" \
        "./${_rpp_rel}/PROTOCOL.md" \
        "" \
        "To pull updates:" \
        "  ( cd ./${_rpp_rel} && git pull )" \
        "  ./${_rpp_rel}/scripts/upgrade.sh . --profile $_rpp_profile --stack $_rpp_stack"
      ;;
    *)
      # The healthy outside-target form: the degraded template with the token
      # substituted EVERYWHERE — exactly what install.sh's placeholder pass
      # has always produced, so existing healthy pointers keep their digest.
      # PLAN-169 W3.1: `sed s|…|VALUE|` cannot carry a NEWLINE in VALUE
      # (unterminated s-command aborts under set -e — mid-upgrade). The
      # upgrade path rejects such values upstream (charset allowlist);
      # this guard covers every other caller: a value the substitution
      # cannot represent leaves the token LITERAL (degraded body — the
      # recognized cure target), never a corrupt render, never an abort.
      case "$_rpp_psource" in
        *"$_RPP_NL"*)
          _render_protocol_pointer_degraded "$_rpp_target" "$_rpp_profile" "$_rpp_stack"
          ;;
        *)
          _render_protocol_pointer_degraded "$_rpp_target" "$_rpp_profile" "$_rpp_stack" \
            | sed "s|{{PROTOCOL_SOURCE}}|$( printf '%s' "$_rpp_psource" | sed 's/[|&\\]/\\&/g' )|g"
          ;;
      esac
      ;;
  esac
}

_render_protocol_pointer_degraded() {
  # $1=TARGET $2=PROFILE $3=STACK — the token stays LITERAL. This is both the
  # historical broken-upgrade output (the cure's recognition target) and the
  # pre-substitution install body (one template, one truth).
  _rppd_target="$1"; _rppd_profile="$2"; _rppd_stack="$3"
  printf '%s\n' \
    "# Protocol reference" \
    "" \
    "The full CEO orchestration protocol lives at:" \
    "{{PROTOCOL_SOURCE}}/PROTOCOL.md" \
    "" \
    "Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout" \
    "(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration)." \
    "" \
    "To pull updates:" \
    "  ( cd {{PROTOCOL_SOURCE}} && git pull )" \
    "  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $_rppd_target --profile $_rppd_profile --stack $_rppd_stack"
}

_protocol_pointer_is_degraded() {
  # $1=FILE. rc=0 iff the file is byte-identical to a degraded render whose
  # TARGET/PROFILE/STACK come from the file's own last line. Everything else
  # (missing file, unparseable line, values with spaces, any edit) => rc=1.
  _ppid_file="$1"
  [ -f "$_ppid_file" ] || return 1
  # Cheap pre-filter: files without the literal token can never be degraded.
  grep -F -q '{{PROTOCOL_SOURCE}}' "$_ppid_file" 2>/dev/null || return 1

  # The upgrade line is the ONE line carrying all three invocation values:
  #   {{PROTOCOL_SOURCE}}/scripts/upgrade.sh <target> --profile <p> --stack <s>
  _ppid_line="$( grep -F '{{PROTOCOL_SOURCE}}/scripts/upgrade.sh ' "$_ppid_file" 2>/dev/null | head -1 )"
  [ -n "$_ppid_line" ] || return 1

  # POSIX-safe field extraction; single-token values only. A target/profile/
  # stack containing whitespace makes the line ambiguous => no match =>
  # preserved (documented residual, consistent with fail-toward-preservation).
  _ppid_target="$( printf '%s\n' "$_ppid_line" | sed -n 's|.*scripts/upgrade\.sh \([^ ][^ ]*\) --profile .*|\1|p' )"
  _ppid_profile="$( printf '%s\n' "$_ppid_line" | sed -n 's|.* --profile \([^ ][^ ]*\) --stack .*|\1|p' )"
  _ppid_stack="$( printf '%s\n' "$_ppid_line" | sed -n 's|.* --stack \([^ ][^ ]*\)$|\1|p' )"
  [ -n "$_ppid_target" ] && [ -n "$_ppid_profile" ] && [ -n "$_ppid_stack" ] || return 1

  _ppid_tmp="$( mktemp "${TMPDIR:-/tmp}/ceo-ptr-recon.XXXXXX" )" || return 1
  _render_protocol_pointer_degraded "$_ppid_target" "$_ppid_profile" "$_ppid_stack" > "$_ppid_tmp"
  if cmp -s "$_ppid_tmp" "$_ppid_file"; then
    rm -f "$_ppid_tmp" 2>/dev/null
    return 0
  fi
  rm -f "$_ppid_tmp" 2>/dev/null
  return 1
}

# =============================================================================
# PLAN-177 W1 (P1-1 / CF-9) — the ONE owner of every .gitignore surface the
# framework delivers.
#
# THE BUG. install.sh has appended two marker-guarded blocks to the adopter's
# ROOT .gitignore for a long time — the MCP shared-secret store (PLAN-019
# P2-SEC-H) and the posture/runtime state (PLAN-165 CX-3) — and upgrade.sh has
# appended NOTHING, ever. An adopter who installed at v1.2.0 and only ever runs
# upgrade.sh therefore receives /night-mode without the ignores, so
# `/night-mode on` leaves .claude/settings.local.json and the state marker as
# untracked files (falsifying PLAN-165 AC-1, "git status stays empty") and
# risks committing a machine-specific permission posture. The parity gate NAMED
# that gap and allowlisted it, so CI was structurally unable to fail on it.
#
# WHY BOTH BLOCKS. Owning only the posture block would leave the mcp-secrets
# block as a second, unowned copy of the same kind of text on the same file —
# a ceremony that grants ownership of half a surface. An adopter older than
# v1.2.0 also never received the mcp-secrets entry from an upgrade.
#
# WHY ONE PLACE. This is INV-4 (PLAN-168 W2): install.sh and upgrade.sh each
# carrying a private copy of the same emitted text is precisely the class that
# produced the PROTOCOL.md pointer divergence. Both callers render through
# these functions, so the routes cannot diverge again.
#
# BYTE-COMPATIBILITY (do not "tidy"): every emission below reproduces the
# shipped install.sh output exactly, including two idiosyncrasies that a
# reviewer will be tempted to clean up.
#   1. The posture header comment is emitted INSIDE the loop, once per APPENDED
#      entry. Hoisting it to a single header changes the bytes on every adopter
#      .gitignore and breaks install/upgrade tree parity.
#   2. The mcp-secrets CREATE branch (no .gitignore yet) writes the header with
#      NO leading blank line, while the APPEND branch writes one. Same file,
#      two shapes, by construction.
# BYTE-PROOF.md plants both as mutations and requires the harness to go red.
#
# IDEMPOTENCE, and its deliberate limit. Re-running never duplicates a line:
# every entry is `grep -Fxq` (fixed-string, whole-line) checked first. The
# check is PER LINE, not per block, so an adopter who deliberately deletes one
# entry gets it re-appended on the next install/upgrade — with a fresh header
# comment above it. That is intentional, not an oversight: these entries exist
# to keep secrets and per-machine permission posture out of VCS, so the
# framework re-asserts them rather than honouring a deletion it cannot
# distinguish from an accident. An adopter who truly wants the path tracked
# should scope it in .git/info/exclude or a nested .gitignore instead.
#
# Functions:
#   _mcp_secrets_ignore_entry              -> the mcp-secrets entry (one line)
#   _apply_mcp_secrets_ignore GITIGNORE    -> ensure it, create-or-append
#   _posture_state_ignore_entries          -> the posture entries (one line,
#                                             space-separated; both callers
#                                             word-split it AND print it
#                                             verbatim, so the single-line
#                                             shape is part of the contract)
#   _apply_posture_state_ignores GITIGNORE -> ensure them, append-only
#   _claude_dir_gitignore_body             -> the NEW .claude/.gitignore body
#   _apply_claude_dir_gitignore CLAUDE_DIR -> create-if-missing, never rewrite
#   _preview_claude_dir_gitignore CLAUDE_DIR -> dry-run twin of the apply:
#       reports would-CREATE / would-APPEND (per missing entry) /
#       would-PRESERVE, so a seeded adopter file (e.g. `/cache/` only) is
#       never misreported as PRESERVE when the real run would append
#       (re-pass rc.4 t2 P1 — the seeded-file dry-run regression)
# =============================================================================

_mcp_secrets_ignore_entry() {
  printf '%s\n' "state/mcp_client_secrets/"
}

_apply_mcp_secrets_ignore() {
  # $1 = path to the adopter ROOT .gitignore (may not exist yet).
  _msi_gitignore="$1"
  # Re-pass rc.4 t2 (P1): shared symlink refusal — a root .gitignore
  # symlink must never route framework appends elsewhere.
  _root_gitignore_symlink_guard "$_msi_gitignore" || return 1
  _msi_line="$( _mcp_secrets_ignore_entry )"
  if [ -f "$_msi_gitignore" ]; then
    if ! grep -Fxq "$_msi_line" "$_msi_gitignore" 2>/dev/null; then
      {
        echo ""
        echo "# PLAN-019 P2-SEC-H: MCP shared-secret store (never commit)"
        echo "$_msi_line"
      } >> "$_msi_gitignore"
      echo "    APPENDED to .gitignore: $_msi_line"
    else
      echo "    .gitignore already excludes $_msi_line"
    fi
  else
    {
      echo "# PLAN-019 P2-SEC-H: MCP shared-secret store (never commit)"
      echo "$_msi_line"
    } > "$_msi_gitignore"
    echo "    CREATED .gitignore with: $_msi_line"
  fi
  # t9 P1: the SECRET store is exactly where textual presence must not be
  # mistaken for effective exclusion — a later `!` negation would leave
  # secret files commit-eligible while this applier reports "already
  # excludes". Same shared probe + re-assert as the posture entries.
  _msi_repo="$( dirname "$_msi_gitignore" )"
  _gitignore_reassert_effective "$_msi_repo" "$_msi_gitignore" \
    "$_msi_line" "state/mcp_client_secrets/__ceo_ignore_probe__" || return 1
  return 0
}

_posture_state_ignore_entries() {
  printf '%s\n' ".claude/state/ .claude/settings.local.json"
}

_root_gitignore_symlink_guard() {
  # $1 = path to the adopter ROOT .gitignore. 0 = safe; 1 = symlink
  # (re-pass rc.4 t3 P2: shared predicate for APPLY *and* dry-run
  # previews — the preview must never say "would ENSURE" where the real
  # run refuses).
  if [ -L "$1" ]; then
    echo "    ERROR: root .gitignore is a symlink — refusing to write through it" >&2
    return 1
  fi
  return 0
}

# t8 P1: textual PRESENCE of an exact ignore line is not EFFECTIVENESS —
# a later `!*.json` negation in the same (or a deeper) file wins in git,
# so `grep -Fxq` alone let night-mode artifacts stay commit-eligible.
# _gitignore_reassert_effective probes git's EFFECTIVE answer for each
# mandatory exclusion; when a probe is visible it APPENDS the exclusion
# again (after the winning negation — last matching rule wins) and
# re-probes; a still-visible probe fails loudly (the negation lives in a
# file this applier does not own, e.g. a deeper .gitignore).
#   $1 = repo root to run git in; $2 = gitignore file to re-assert into;
#   $3 = the raw exclusion line; $4 = repo-relative probe path.
# Outside a git work tree the probe cannot run — NOTE and return 0
# (fail-open on infra; the textual pass above already ran).
_gitignore_reassert_effective() {
  _gre_repo="$1"; _gre_file="$2"; _gre_line="$3"; _gre_probe="$4"
  if ! git -C "$_gre_repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "    NOTE: not a git work tree — cannot probe effective ignore for $_gre_line"
    return 0
  fi
  # t10 P1 #2: ignore rules NEVER affect files already in the index — a
  # pre-rc.4 adopter who committed the posture/secret path stays dirty no
  # matter what this file says. Detect tracked content FIRST and require
  # an explicit migration; this is fail-CLOSED because leaving it silent
  # is exactly the leak this delivery exists to close.
  case "$_gre_probe" in
    */__ceo_ignore_probe__) _gre_scope="$( dirname "$_gre_probe" )" ;;
    *)                      _gre_scope="$_gre_probe" ;;
  esac
  # sed, never `head` (t11 P2): under the callers' pipefail, head closing
  # the pipe early makes ls-files exit 141 and aborts the WHOLE upgrade
  # before the migration message prints (the repo's known SIGPIPE class).
  _gre_tracked="$( git -C "$_gre_repo" ls-files -- "$_gre_scope" 2>/dev/null | sed -n '1,5p' )"
  if [ -n "$_gre_tracked" ]; then
    echo "    ERROR: $_gre_scope is already TRACKED by git — an ignore rule cannot protect it." >&2
    echo "      Migrate explicitly, then re-run:" >&2
    printf '%s\n' "$_gre_tracked" | while IFS= read -r _gre_t; do
      echo "        git rm --cached '$_gre_t'" >&2
    done
    return 1
  fi
  # t10 P1 #2: --no-index — plain check-ignore consults the index and
  # reports a tracked path as unmatched, causing a re-assert loop; the
  # question here is strictly "does the PATTERN SET cover this path?".
  if git -C "$_gre_repo" check-ignore -q --no-index -- "$_gre_probe" 2>/dev/null; then
    return 0
  fi
  {
    echo ""
    echo "# Re-asserted by ceo-orchestration (re-pass rc.4 t8 P1): a later"
    echo "# rule in this file negated the mandatory exclusion below; git's"
    echo "# last-matching-rule-wins makes this trailing copy effective."
    printf '%s\n' "$_gre_line"
  } >> "$_gre_file"
  if git -C "$_gre_repo" check-ignore -q --no-index -- "$_gre_probe" 2>/dev/null; then
    echo "    RE-ASSERTED (was textually present but negated): $_gre_line"
    return 0
  fi
  # t10 P1 #1: a still-visible SECURITY exclusion is a FAILURE, not a
  # warning — returning 0 here let install/upgrade finish green while
  # the secret store stayed commit-eligible (e.g. a deeper
  # state/.gitignore re-including it, which outranks this file).
  echo "    ERROR: $_gre_line is present but NOT effective (a rule outside $_gre_file wins — e.g. a deeper .gitignore re-including it). Fix the adopter ignore rules, then re-run." >&2
  return 1
}

_apply_posture_state_ignores() {
  # $1 = path to the adopter ROOT .gitignore (append creates it if absent).
  _psi_gitignore="$1"
  _root_gitignore_symlink_guard "$_psi_gitignore" || return 1
  for _psi_line in $( _posture_state_ignore_entries ); do
    if [ -f "$_psi_gitignore" ] && grep -Fxq "$_psi_line" "$_psi_gitignore" 2>/dev/null; then
      echo "    .gitignore already excludes $_psi_line"
      continue
    fi
    {
      echo ""
      echo "# PLAN-165 CX-3: per-machine posture/runtime state (never commit)"
      echo "$_psi_line"
    } >> "$_psi_gitignore"
    echo "    APPENDED to .gitignore: $_psi_line"
  done
  # t8 P1: presence pass done — now assert EFFECTIVENESS per entry.
  _psi_repo="$( dirname "$_psi_gitignore" )"
  _gitignore_reassert_effective "$_psi_repo" "$_psi_gitignore" \
    ".claude/state/" ".claude/state/__ceo_ignore_probe__" || return 1
  _gitignore_reassert_effective "$_psi_repo" "$_psi_gitignore" \
    ".claude/settings.local.json" ".claude/settings.local.json" || return 1
  return 0
}

_claude_dir_gitignore_body() {
  # Paths are anchored with a leading slash so they bind to .claude/ ONLY and
  # cannot match a same-named path deeper in an adopter tree.
  printf '%s\n' \
    "# Delivered by ceo-orchestration (PLAN-177 W1 / CF-9)." \
    "#" \
    "# Per-machine posture + runtime state that must never reach VCS:" \
    "#   state/             runtime state as a whole (PLAN-163 T3.1)" \
    "#   settings.local.json  permission overlay deciding the NEXT session's" \
    "#                        posture (PLAN-165)" \
    "#" \
    "# The root .gitignore carries the same exclusions for adopters who track" \
    "# this tree from the repository root. This file additionally covers the" \
    "# --ceremony user install, which never writes outside .claude/ and so" \
    "# never received them." \
    "#" \
    "# Adopter-owned once created: install and upgrade never REPLACE this" \
    "# file — adopter bytes are preserved; missing mandatory framework" \
    "# security entries may be APPENDED (additively reasserted) on upgrade." \
    "/state/" \
    "/settings.local.json"
}

_apply_claude_dir_gitignore() {
  # $1 = the adopter .claude directory.
  # Create when absent; when PRESENT, append only the entries that are
  # missing, per line, preserving every adopter byte (re-pass rc.4 t1
  # P1-b: an adopter with a pre-existing .claude/.gitignore -- e.g.
  # /cache/ only -- never received /state/ nor /settings.local.json,
  # so night-mode state stayed commit-eligible under --ceremony user;
  # create-if-missing alone proved the clean-target case only). Same
  # grep -Fxq per-entry predicate as the root blocks: the file stays
  # adopter-owned, nothing is rewritten, a deliberate edit to OUR
  # comment lines is never repaired.
  _cdg_dir="$1"
  _cdg_file="$_cdg_dir/.gitignore"
  # Re-pass rc.4 t2 (P1): NEVER follow a symlink here. A .claude/.gitignore
  # symlinked to another writable file would receive framework appends at
  # the EXTERNAL target; a dangling symlink passes `[ ! -e ]` and the
  # redirect would CREATE its target. -L catches both, before any read.
  if [ -L "$_cdg_file" ]; then
    echo "    ERROR: .claude/.gitignore is a symlink — refusing to read or write through it (preserve/replace it manually)" >&2
    return 1
  fi
  if [ ! -e "$_cdg_file" ]; then
    [ -d "$_cdg_dir" ] || mkdir -p "$_cdg_dir"
    _claude_dir_gitignore_body > "$_cdg_file"
    echo "    CREATED: .claude/.gitignore"
    # t11 P1: DO NOT return here — the effectiveness + tracked checks
    # below must run on the freshly created file too. A user-ceremony
    # adopter with an already-TRACKED .claude/settings.local.json got a
    # green install while the overlay stayed commit-eligible (user
    # ceremony never runs the root helper that would have caught it).
    _cdg_repo="$( dirname "$_cdg_dir" )"
    _gitignore_reassert_effective "$_cdg_repo" "$_cdg_file" \
      "/state/" ".claude/state/__ceo_ignore_probe__" || return 1
    _gitignore_reassert_effective "$_cdg_repo" "$_cdg_file" \
      "/settings.local.json" ".claude/settings.local.json" || return 1
    return 0
  fi
  if [ ! -f "$_cdg_file" ]; then
    echo "    ERROR: .claude/.gitignore exists but is not a regular file" >&2
    return 1
  fi
  _cdg_added=0
  for _cdg_entry in "/state/" "/settings.local.json"; do
    if grep -Fxq "$_cdg_entry" "$_cdg_file"; then
      continue
    fi
    {
      echo ""
      echo "# Delivered by ceo-orchestration (PLAN-177 W1 / CF-9): per-machine"
      echo "# posture/runtime state (never commit)."
      printf '%s\n' "$_cdg_entry"
    } >> "$_cdg_file"
    _cdg_added=1
  done
  # t8 P1: presence pass done — now assert EFFECTIVENESS per entry
  # (probes are repo-relative; the repo root is the parent of .claude/).
  _cdg_repo="$( dirname "$_cdg_dir" )"
  _gitignore_reassert_effective "$_cdg_repo" "$_cdg_file" \
    "/state/" ".claude/state/__ceo_ignore_probe__" || return 1
  _gitignore_reassert_effective "$_cdg_repo" "$_cdg_file" \
    "/settings.local.json" ".claude/settings.local.json" || return 1
  if [ "$_cdg_added" = "1" ]; then
    echo "    APPENDED: missing posture entries into existing .claude/.gitignore"
  else
    echo "    EXISTS: .claude/.gitignore already carries both entries"
  fi
  return 0
}

# t11 P1 #2: read-only tracked-path classifier SHARED by apply previews —
# prints the tracked sensitive paths (max 5) under $2.. scopes of repo $1;
# empty output == nothing tracked. Never writes, never fails the caller.
_gitignore_tracked_sensitive() {
  _gts_repo="$1"; shift
  git -C "$_gts_repo" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
  for _gts_scope in "$@"; do
    git -C "$_gts_repo" ls-files -- "$_gts_scope" 2>/dev/null
  done | sed -n '1,5p'
  return 0
}

_preview_claude_dir_gitignore() {
  # Dry-run twin of _apply_claude_dir_gitignore (re-pass rc.4 t2 P1):
  # SAME per-entry predicate, ZERO writes. Reports the action the real
  # run would take — including would-APPEND on a seeded adopter file.
  _pcg_file="$1/.gitignore"
  if [ -L "$_pcg_file" ]; then
    echo "    (dry-run) ERROR: .claude/.gitignore is a symlink — real run would REFUSE" >&2
    return 1
  fi
  if [ ! -e "$_pcg_file" ]; then
    # t12 P1: the ABSENT branch must be as honest as the rest — the real
    # run CREATES the file and then fails on the tracked check, so a
    # would-CREATE + exit 0 preview over a tracked overlay lies. Same
    # read-only classifier, still zero writes.
    _pcg_repo="$( dirname "$1" )"
    _pcg_tracked="$( _gitignore_tracked_sensitive "$_pcg_repo" \
      ".claude/settings.local.json" ".claude/state" )"
    if [ -n "$_pcg_tracked" ]; then
      echo "    (dry-run) ERROR: sensitive path(s) already TRACKED — real run would CREATE .claude/.gitignore and then REFUSE, demanding git rm --cached:" >&2
      printf '%s\n' "$_pcg_tracked" | sed 's/^/      /' >&2
      return 1
    fi
    echo "    (dry-run) would CREATE: .claude/.gitignore"
    return 0
  fi
  if [ ! -f "$_pcg_file" ]; then
    echo "    (dry-run) ERROR: .claude/.gitignore exists but is not a regular file" >&2
    return 1
  fi
  _pcg_missing=""
  for _pcg_entry in "/state/" "/settings.local.json"; do
    grep -Fxq "$_pcg_entry" "$_pcg_file" || _pcg_missing="$_pcg_missing $_pcg_entry"
  done
  # t9 P1: the real run now RE-ASSERTS a textually-present-but-negated
  # entry, so a "would PRESERVE" preview over that state is a lie. Run the
  # SAME read-only `git check-ignore` probes and report would-RE-ASSERT.
  _pcg_repo="$( dirname "$1" )"
  _pcg_reassert=""
  if git -C "$_pcg_repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if ! git -C "$_pcg_repo" check-ignore -q --no-index -- \
         ".claude/state/__ceo_ignore_probe__" 2>/dev/null; then
      case "$_pcg_missing" in
        *" /state/"*) : ;;  # already reported as would-APPEND
        *) _pcg_reassert="$_pcg_reassert /state/" ;;
      esac
    fi
    if ! git -C "$_pcg_repo" check-ignore -q --no-index -- \
         ".claude/settings.local.json" 2>/dev/null; then
      case "$_pcg_missing" in
        *" /settings.local.json"*) : ;;
        *) _pcg_reassert="$_pcg_reassert /settings.local.json" ;;
      esac
    fi
  fi
  if [ -n "$_pcg_missing" ]; then
    echo "    (dry-run) would APPEND into existing .claude/.gitignore:$_pcg_missing"
  fi
  if [ -n "$_pcg_reassert" ]; then
    echo "    (dry-run) would RE-ASSERT (present but negated by a later rule):$_pcg_reassert"
  fi
  # t11 P1 #2: the REAL run refuses on tracked sensitive paths — a
  # would-PRESERVE preview over that state is dishonest. Same read-only
  # classifier, no writes.
  _pcg_tracked="$( _gitignore_tracked_sensitive "$_pcg_repo" \
    ".claude/settings.local.json" ".claude/state" )"
  if [ -n "$_pcg_tracked" ]; then
    echo "    (dry-run) ERROR: sensitive path(s) already TRACKED — real run would REFUSE and demand git rm --cached:" >&2
    printf '%s\n' "$_pcg_tracked" | sed 's/^/      /' >&2
    return 1
  fi
  if [ -z "$_pcg_missing" ] && [ -z "$_pcg_reassert" ]; then
    echo "    (dry-run) EXISTS: .claude/.gitignore already carries both entries (would PRESERVE)"
  fi
  return 0
}
