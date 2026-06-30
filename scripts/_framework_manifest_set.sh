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

# _framework_target_entries — the top-level target relpaths (files + dirs),
# profile-aware, sorted + deduped. This is the STATIC intended set; it does not
# touch disk (so install and upgrade derive an identical list regardless of
# what is currently present).
_framework_target_entries() {
  {
    # Root governance pointer (the verified S238 driver target — outside .claude/).
    printf '%s\n' "PROTOCOL.md"

    # Always-installed team rosters + universal catalogs.
    printf '%s\n' ".claude/team.md"
    printf '%s\n' ".claude/frontend-team.md"
    printf '%s\n' ".claude/pitfalls-catalog.yaml"
    printf '%s\n' ".claude/task-chains.yaml"

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
    if [ "${FMS_MODE:-copy}" = "link" ] && [ -L "$_wbm_abs" ]; then
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
      else
        # Hash the FRAMEWORK version. When FMS_HASH_ROOT is set (upgrade) and the
        # path is ABSENT there, the framework no longer ships it — OMIT it from
        # the baseline (recording the adopter-retained target file would falsely
        # mark it FRAMEWORK-CHANGED if the framework later reintroduces the
        # path). Codex R2 P1.
        _wbm_hash_path="$_wbm_abs"
        if [ -n "${FMS_HASH_ROOT:-}" ]; then
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
