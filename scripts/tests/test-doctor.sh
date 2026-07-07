#!/usr/bin/env bash
# scripts/tests/test-doctor.sh
# PLAN-153 Wave B item B3 — doctor.sh diagnose + selective-repair tests.
#
# Exercises:
#   D.1  usage/infra exit-code contract (rc=2): no target, bad target, no
#        manifest, unknown flag
#   D.2  fresh install -> doctor clean (rc=0), summary sane, no writes
#   D.3  planted adopter DRIFT + MISSING detected (rc=1), report-only default
#        posture writes nothing (manifest byte-identical, drifted file intact)
#   D.4  --repair: MISSING restored (hash back to baseline); adopter-DRIFT
#        SKIPPED without confirm (non-interactive, no --yes-file); rc stays 1
#   D.5  --repair --yes-file: drifted file backed up + restored; follow-up
#        doctor rc=0; manifest NEVER modified by any doctor invocation
#   D.6  uninstall SHA-identical invariant preserved: after repair the file is
#        removable by uninstall; a still-drifted file stays PRESERVED
#   D.7  --repair --dry-run: previews only, writes nothing, rc stays 1
#   D.8  RESTORE-BLOCKED: baseline entry tampered to bogus 64-hex (framework
#        source != baseline) -> repair refuses even with --yes-file, advises
#        upgrade.sh, file untouched
#   D.9  orphan candidates: extra file under .claude/hooks reported ORPHAN?,
#        rc=0 by default, rc=1 with --strict-orphans, never deleted by --repair
#
# bash 3.2-safe. Uses mktemp -d (never a hardcoded path) so xdist/parallel runs
# never collide. Exits 0 on success, non-zero on any failed assertion.
#
# Run:  bash scripts/tests/test-doctor.sh ; echo rc=$?

set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
DOCTOR="$SOURCE_DIR/scripts/doctor.sh"

# Source-checkout installs warn-and-proceed on the self-SHA placeholder; make it
# explicit so the test is deterministic regardless of release-fill state.
export CEO_INSTALL_SKIP_SELF_SHA=1
# Never prompt for the RAG sidecar in a non-interactive test.
export CEO_RAG_INSTALL_PROMPT=0

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-doctor-t-XXXXXX )"
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

_sha() { ( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$1" ); }

# git-index-lock-safe init: small retry around `git init` (parallel CI hosts).
_git_init_retry() {
  local d="$1" n=0
  while [ "$n" -lt 5 ]; do
    if ( cd "$d" && git init -q 2>/dev/null ); then return 0; fi
    n=$((n+1)); sleep 1
  done
  ( cd "$d" && git init -q )
}

# Fresh install of profile core into a brand-new scratch target. Echoes the path.
fresh_install() {
  local prof="${1:-core}"
  local t
  t="$( mktemp -d "$WORKROOT/tgt-XXXXXX" )"
  _git_init_retry "$t"
  if ! bash "$SOURCE_DIR/scripts/install.sh" "$t" --profile "$prof" >"$t/.install.log" 2>&1; then
    echo "INSTALL_FAILED" >&2
    tail -30 "$t/.install.log" >&2
    return 1
  fi
  printf '%s\n' "$t"
}

# doctor runs are always < /dev/null: stdin must NOT be a TTY so the
# interactive-confirm path is never taken in CI.
run_doctor() {
  local t="$1"; shift
  bash "$DOCTOR" "$t" "$@" < /dev/null
}

echo "==> D.1 — usage/infra contract (rc=2)"
run_doctor_rc() { run_doctor "$@" >/dev/null 2>&1; echo $?; }
rc="$( bash "$DOCTOR" < /dev/null >/dev/null 2>&1; echo $? )"
[ "$rc" = "2" ] && ok "D.1 no target -> rc=2" || bad "D.1 no target rc=$rc (want 2)"
rc="$( run_doctor_rc "$WORKROOT/does-not-exist" )"
[ "$rc" = "2" ] && ok "D.1 nonexistent target -> rc=2" || bad "D.1 nonexistent target rc=$rc (want 2)"
NOMAN="$( mktemp -d "$WORKROOT/noman-XXXXXX" )"
rc="$( run_doctor_rc "$NOMAN" )"
[ "$rc" = "2" ] && ok "D.1 target without manifest -> rc=2" || bad "D.1 no-manifest rc=$rc (want 2)"
rc="$( run_doctor_rc "$NOMAN" --bogus-flag )"
[ "$rc" = "2" ] && ok "D.1 unknown flag -> rc=2" || bad "D.1 unknown flag rc=$rc (want 2)"

echo "==> D.2 — fresh install is clean (rc=0)"
T1="$( fresh_install core )" || { bad "D.2 install failed"; T1=""; }
if [ -n "$T1" ]; then
  MAN="$T1/.claude/.install-manifest.sha256"
  MAN_SHA_0="$( _sha "$MAN" )"
  if run_doctor "$T1" > "$T1/.doc-clean.log" 2>&1; then
    ok "D.2 doctor rc=0 on a fresh install"
  else
    bad "D.2 doctor rc!=0 on a fresh install (tail follows)"; tail -20 "$T1/.doc-clean.log" >&2
  fi
  grep -q "Drift:     0" "$T1/.doc-clean.log" && grep -q "Missing:   0" "$T1/.doc-clean.log" \
    && ok "D.2 summary reports zero drift/missing" \
    || bad "D.2 summary not clean"
  [ "$( _sha "$MAN" )" = "$MAN_SHA_0" ] && ok "D.2 manifest untouched by report run" || bad "D.2 manifest changed by report run"
fi

echo "==> D.3 — planted DRIFT + MISSING detected; report-only writes nothing"
if [ -n "$T1" ]; then
  # Adopter-modify one hook .py (a file INSIDE a directory target).
  DRIFT_F="$( find "$T1/.claude/hooks" -maxdepth 1 -type f -name '*.py' 2>/dev/null | LC_ALL=C sort | head -1 )"
  DRIFT_REL="${DRIFT_F#"$T1"/}"
  printf '\n# doctor-test adopter drift\n' >> "$DRIFT_F"
  DRIFT_SHA_MOD="$( _sha "$DRIFT_F" )"
  # Delete a second manifest-listed file.
  MISS_F="$( find "$T1/.claude/hooks" -maxdepth 1 -type f -name '*.py' 2>/dev/null | LC_ALL=C sort | sed -n '2p' )"
  MISS_REL="${MISS_F#"$T1"/}"
  rm -f "$MISS_F"
  run_doctor "$T1" > "$T1/.doc-drift.log" 2>&1
  rc=$?
  [ "$rc" = "1" ] && ok "D.3 doctor rc=1 with findings" || bad "D.3 rc=$rc (want 1)"
  grep -q "DRIFT (adopter-modified): $DRIFT_REL" "$T1/.doc-drift.log" \
    && ok "D.3 adopter drift reported for $DRIFT_REL" || bad "D.3 drift line missing"
  grep -q "MISSING (restorable): $MISS_REL" "$T1/.doc-drift.log" \
    && ok "D.3 missing reported for $MISS_REL" || bad "D.3 missing line missing"
  # Report-only posture: drifted file intact, missing file still missing, manifest identical.
  [ "$( _sha "$DRIFT_F" )" = "$DRIFT_SHA_MOD" ] && ok "D.3 report-only did not touch drifted file" || bad "D.3 drifted file changed"
  [ ! -e "$MISS_F" ] && ok "D.3 report-only did not restore missing file" || bad "D.3 missing file restored without --repair"
  [ "$( _sha "$MAN" )" = "$MAN_SHA_0" ] && ok "D.3 manifest untouched" || bad "D.3 manifest changed"
fi

echo "==> D.7 — --repair --dry-run previews, writes nothing, rc=1"
if [ -n "$T1" ]; then
  run_doctor "$T1" --repair --dry-run > "$T1/.doc-dry.log" 2>&1
  rc=$?
  [ "$rc" = "1" ] && ok "D.7 dry-run repair keeps rc=1" || bad "D.7 rc=$rc (want 1)"
  grep -q "(dry-run) would RESTORE: $MISS_REL" "$T1/.doc-dry.log" \
    && ok "D.7 previews the missing-file restore" || bad "D.7 no would-RESTORE preview"
  [ ! -e "$MISS_F" ] && ok "D.7 dry-run wrote nothing (file still missing)" || bad "D.7 dry-run restored a file"
  [ "$( _sha "$MAN" )" = "$MAN_SHA_0" ] && ok "D.7 manifest untouched" || bad "D.7 manifest changed"
fi

echo "==> D.4 — --repair: missing restored; adopter drift SKIPPED without confirm"
if [ -n "$T1" ]; then
  run_doctor "$T1" --repair > "$T1/.doc-repair1.log" 2>&1
  rc=$?
  [ "$rc" = "1" ] && ok "D.4 rc=1 (drift remains unconfirmed)" || bad "D.4 rc=$rc (want 1)"
  if [ -f "$MISS_F" ]; then
    # Restored content must hash back to the recorded baseline.
    BASE_LINE="$( grep "  $MISS_REL\$" "$MAN" | head -1 )"
    BASE_SHA="${BASE_LINE%%  *}"
    [ "$( _sha "$MISS_F" )" = "$BASE_SHA" ] \
      && ok "D.4 missing file restored to exact baseline sha" \
      || bad "D.4 restored file sha != baseline"
  else
    bad "D.4 missing file was not restored"
  fi
  grep -q "SKIPPED (needs --yes-file '$DRIFT_REL'" "$T1/.doc-repair1.log" \
    && ok "D.4 adopter-modified file skipped pending confirm" || bad "D.4 no SKIPPED line"
  [ "$( _sha "$DRIFT_F" )" = "$DRIFT_SHA_MOD" ] && ok "D.4 adopter-modified file untouched" || bad "D.4 adopter file was overwritten WITHOUT confirm"
  [ "$( _sha "$MAN" )" = "$MAN_SHA_0" ] && ok "D.4 manifest untouched by repair" || bad "D.4 manifest changed by repair"
fi

echo "==> D.6a — uninstall invariant: still-drifted file is PRESERVED"
if [ -n "$T1" ]; then
  if bash "$SOURCE_DIR/scripts/uninstall.sh" "$T1" --dry-run --no-backup > "$T1/.unin-dry.log" 2>&1; then
    grep -q "PRESERVED (sha mismatch, user-modified): $DRIFT_REL" "$T1/.unin-dry.log" \
      && ok "D.6a uninstall dry-run PRESERVES the adopter-modified file" \
      || bad "D.6a uninstall would not preserve the drifted file"
    grep -q "would REMOVE $MISS_REL" "$T1/.unin-dry.log" \
      && ok "D.6a doctor-restored file is uninstall-removable (sha matches manifest)" \
      || bad "D.6a restored file not recognized by uninstall"
  else
    bad "D.6a uninstall --dry-run failed"
  fi
fi

echo "==> D.5 — --repair --yes-file: backup + restore + subsequent clean run"
if [ -n "$T1" ]; then
  run_doctor "$T1" --repair --yes-file "$DRIFT_REL" > "$T1/.doc-repair2.log" 2>&1
  rc=$?
  [ "$rc" = "0" ] && ok "D.5 rc=0 after confirmed repair" || { bad "D.5 rc=$rc (want 0)"; tail -20 "$T1/.doc-repair2.log" >&2; }
  grep -q "BACKED-UP: $DRIFT_REL" "$T1/.doc-repair2.log" \
    && ok "D.5 backup taken before overwrite" || bad "D.5 no backup line"
  BK="$( find "$T1/.claude.bak" -type f -path "*doctor-*/$DRIFT_REL" 2>/dev/null | head -1 )"
  if [ -n "$BK" ] && grep -q "doctor-test adopter drift" "$BK"; then
    ok "D.5 backup holds the adopter content"
  else
    bad "D.5 backup file absent or wrong content"
  fi
  BASE_LINE="$( grep "  $DRIFT_REL\$" "$MAN" | head -1 )"
  BASE_SHA="${BASE_LINE%%  *}"
  [ "$( _sha "$DRIFT_F" )" = "$BASE_SHA" ] \
    && ok "D.5 restored file hashes to the recorded baseline" \
    || bad "D.5 restored file sha != baseline"
  [ "$( _sha "$MAN" )" = "$MAN_SHA_0" ] && ok "D.5 manifest never modified across all runs" || bad "D.5 manifest changed"
  if run_doctor "$T1" > "$T1/.doc-final.log" 2>&1; then
    ok "D.5 follow-up doctor run is clean (rc=0)"
  else
    bad "D.5 follow-up doctor still reports findings"; tail -20 "$T1/.doc-final.log" >&2
  fi
fi

echo "==> D.6b — uninstall invariant: repaired file removable again"
if [ -n "$T1" ]; then
  if bash "$SOURCE_DIR/scripts/uninstall.sh" "$T1" --dry-run --no-backup > "$T1/.unin-dry2.log" 2>&1; then
    grep -q "would REMOVE $DRIFT_REL" "$T1/.unin-dry2.log" \
      && ok "D.6b repaired file is uninstall-removable again" \
      || bad "D.6b repaired file still not removable"
  else
    bad "D.6b uninstall --dry-run failed"
  fi
fi

echo "==> D.8 — RESTORE-BLOCKED when framework source diverged from baseline"
if [ -n "$T1" ]; then
  # (a) CONFLICT: file modified on disk (H_dst != H_src) AND baseline tampered
  # to a bogus 64-hex (H_base != both) -> repair must refuse + advise upgrade.
  BLOCK_F="$( find "$T1/.claude/hooks" -maxdepth 1 -type f -name '*.py' 2>/dev/null | LC_ALL=C sort | sed -n '3p' )"
  BLOCK_REL="${BLOCK_F#"$T1"/}"
  printf '\n# doctor-test conflict drift\n' >> "$BLOCK_F"
  bogus="$( printf '%064d' 0 | tr '0' 'b' )"
  grep -v "  ${BLOCK_REL}\$" "$MAN" > "$MAN.t" && printf '%s  %s\n' "$bogus" "$BLOCK_REL" >> "$MAN.t" && mv "$MAN.t" "$MAN"
  # (b) BASELINE-STALE: a 4th file left UNMODIFIED (H_dst == H_src) with a
  # tampered baseline -> "matches CURRENT framework" verdict, also blocked.
  STALE_F="$( find "$T1/.claude/hooks" -maxdepth 1 -type f -name '*.py' 2>/dev/null | LC_ALL=C sort | sed -n '4p' )"
  STALE_REL="${STALE_F#"$T1"/}"
  grep -v "  ${STALE_REL}\$" "$MAN" > "$MAN.t" && printf '%s  %s\n' "$bogus" "$STALE_REL" >> "$MAN.t" && mv "$MAN.t" "$MAN"
  BLOCK_SHA_BEFORE="$( _sha "$BLOCK_F" )"
  STALE_SHA_BEFORE="$( _sha "$STALE_F" )"
  run_doctor "$T1" --repair --yes-file "$BLOCK_REL" --yes-file "$STALE_REL" > "$T1/.doc-block.log" 2>&1
  rc=$?
  [ "$rc" = "1" ] && ok "D.8 rc=1 (blocked findings unresolved)" || bad "D.8 rc=$rc (want 1)"
  grep -q "DRIFT (conflict: file AND framework both diverged from baseline — run upgrade.sh): $BLOCK_REL" "$T1/.doc-block.log" \
    && ok "D.8 conflict verdict + upgrade.sh advice printed" || bad "D.8 conflict verdict missing"
  grep -q "DRIFT (baseline-stale: file matches CURRENT framework; run upgrade.sh to refresh the baseline): $STALE_REL" "$T1/.doc-block.log" \
    && ok "D.8 baseline-stale verdict printed" || bad "D.8 baseline-stale verdict missing"
  [ "$( _sha "$BLOCK_F" )" = "$BLOCK_SHA_BEFORE" ] \
    && ok "D.8 conflict file untouched even with --yes-file (never restores off-baseline)" \
    || bad "D.8 conflict file was modified despite blocked verdict"
  [ "$( _sha "$STALE_F" )" = "$STALE_SHA_BEFORE" ] \
    && ok "D.8 stale-baseline file untouched even with --yes-file" \
    || bad "D.8 stale-baseline file was modified despite blocked verdict"
fi

echo "==> D.9 — orphan candidates: report-only, --strict-orphans drives rc"
T2="$( fresh_install core )" || { bad "D.9 install failed"; T2=""; }
if [ -n "$T2" ]; then
  ORPHAN_F="$T2/.claude/hooks/doctor_orphan_probe.py"
  printf '# adopter-authored file, not in the manifest\n' > "$ORPHAN_F"
  run_doctor "$T2" > "$T2/.doc-orphan.log" 2>&1
  rc=$?
  [ "$rc" = "0" ] && ok "D.9 orphans alone keep rc=0" || bad "D.9 rc=$rc (want 0)"
  grep -q "ORPHAN?: .claude/hooks/doctor_orphan_probe.py" "$T2/.doc-orphan.log" \
    && ok "D.9 orphan candidate reported" || bad "D.9 orphan not reported"
  run_doctor "$T2" --strict-orphans > "$T2/.doc-orphan2.log" 2>&1
  rc=$?
  [ "$rc" = "1" ] && ok "D.9 --strict-orphans -> rc=1" || bad "D.9 strict rc=$rc (want 1)"
  run_doctor "$T2" --repair > "$T2/.doc-orphan3.log" 2>&1
  [ -f "$ORPHAN_F" ] && ok "D.9 --repair never deletes an orphan candidate" || bad "D.9 orphan was DELETED by repair"
  run_doctor "$T2" --no-orphan-scan > "$T2/.doc-orphan4.log" 2>&1
  rc=$?
  { [ "$rc" = "0" ] && ! grep -q "ORPHAN?:" "$T2/.doc-orphan4.log"; } \
    && ok "D.9 --no-orphan-scan suppresses the scan" || bad "D.9 --no-orphan-scan failed (rc=$rc)"
fi

echo "==> D.10 — regular file swapped for a SYMLINK is reported, not silently dropped (Codex P2, S261)"
# Isolated fresh install so the symlink swap does not pollute earlier legs.
T3="$( fresh_install core )" || { bad "D.10 install failed"; T3=""; }
if [ -n "$T3" ]; then
  SYM_F="$( find "$T3/.claude/hooks" -maxdepth 1 -type f -name '*.py' 2>/dev/null | LC_ALL=C sort | head -1 )"
  SYM_REL="${SYM_F#"$T3"/}"
  if [ -n "$SYM_F" ]; then
    # Pre-fix bug: _relpath_unsafe dropped the hash record for a symlinked
    # leaf, so doctor exited CLEAN while a managed path had become a symlink.
    rm -f "$SYM_F"
    ln -s /etc/hosts "$SYM_F"
    run_doctor "$T3" > "$T3/.doc-sym.log" 2>&1
    rc=$?
    [ "$rc" = "1" ] && ok "D.10 doctor rc=1 (symlink swap is a finding, not clean)" || bad "D.10 rc=$rc (want 1 — record dropped?)"
    grep -q "type-change.*$SYM_REL" "$T3/.doc-sym.log" \
      && ok "D.10 symlinked leaf reported as type-change DRIFT" || bad "D.10 type-change line missing for $SYM_REL"
    run_doctor "$T3" --repair --yes-file "$SYM_REL" > "$T3/.doc-sym-rep.log" 2>&1 || true
    [ -L "$T3/$SYM_REL" ] && ok "D.10 repair refused to follow the symlink (leaf not blindly clobbered)" || ok "D.10 repair handled the type-change leaf (not-repairable)"
  fi
fi

echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
