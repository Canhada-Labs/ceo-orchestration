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
    *)                          printf '' ;;
  esac
}

_wbm_is_conditional() {
  case "$1" in
    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
  esac
  return 1
}

# The digest the PRE-run manifest recorded. Empty when unavailable, which the
# fail-closed branch turns into "do not record" rather than a guess.
_wbm_prior_digest() {
  [ -n "${FMS_PRIOR_MANIFEST:-}" ] && [ -f "$FMS_PRIOR_MANIFEST" ] || { printf ''; return 0; }
  grep -E "^[0-9a-f]{64}  $1\$" "$FMS_PRIOR_MANIFEST" 2>/dev/null | head -1 | cut -d' ' -f1 || printf ''
}

_write_baseline_manifest() {
  _wbm_manifest="$1"
  if ! command -v _framework_manifest_files >/dev/null 2>&1 \
     || ! command -v _hash_file >/dev/null 2>&1; then
    echo "    NOTE: baseline manifest skipped — hash/enumeration helpers not sourced" >&2
    return 0
  fi
  : "${FMS_ROOT:?_write_baseline_manifest requires FMS_ROOT}"
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
          if [ -f "$_wbm_hash_root/$_wbm_rel" ]; then
            _wbm_hash_path="$_wbm_hash_root/$_wbm_rel"
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
      _render_protocol_pointer_degraded "$_rpp_target" "$_rpp_profile" "$_rpp_stack" \
        | sed "s|{{PROTOCOL_SOURCE}}|$( printf '%s' "$_rpp_psource" | sed 's/[|&\\]/\\&/g' )|g"
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
  if git -C "$_gre_repo" check-ignore -q -- "$_gre_probe" 2>/dev/null; then
    return 0
  fi
  {
    echo ""
    echo "# Re-asserted by ceo-orchestration (re-pass rc.4 t8 P1): a later"
    echo "# rule in this file negated the mandatory exclusion below; git's"
    echo "# last-matching-rule-wins makes this trailing copy effective."
    printf '%s\n' "$_gre_line"
  } >> "$_gre_file"
  if git -C "$_gre_repo" check-ignore -q -- "$_gre_probe" 2>/dev/null; then
    echo "    RE-ASSERTED (was textually present but negated): $_gre_line"
    return 0
  fi
  echo "    WARNING: $_gre_line is present but NOT effective (a negation outside $_gre_file wins) — fix the adopter ignore rules manually" >&2
  return 0
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
    ".claude/state/" ".claude/state/__ceo_ignore_probe__"
  _gitignore_reassert_effective "$_psi_repo" "$_psi_gitignore" \
    ".claude/settings.local.json" ".claude/settings.local.json"
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
    "/state/" ".claude/state/__ceo_ignore_probe__"
  _gitignore_reassert_effective "$_cdg_repo" "$_cdg_file" \
    "/settings.local.json" ".claude/settings.local.json"
  if [ "$_cdg_added" = "1" ]; then
    echo "    APPENDED: missing posture entries into existing .claude/.gitignore"
  else
    echo "    EXISTS: .claude/.gitignore already carries both entries"
  fi
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
  if [ -n "$_pcg_missing" ]; then
    echo "    (dry-run) would APPEND into existing .claude/.gitignore:$_pcg_missing"
  else
    echo "    (dry-run) EXISTS: .claude/.gitignore already carries both entries (would PRESERVE)"
  fi
  return 0
}
