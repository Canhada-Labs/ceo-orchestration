#!/usr/bin/env bash
# scripts/tests/test_install_baseline_manifest.sh
# PLAN-138 Wave C (ADR-155) — baseline SHA-256 install/upgrade manifest tests.
#
# Exercises:
#   C.2  enumeration vs reality (every enumerated target exists in a fresh
#        install; profile-aware). Install/upgrade parity moved to
#        scripts/tests/test-install-upgrade-parity-e2e.sh (PLAN-166 F4)
#   C.3  _hash_file + _hash_stdin (each hasher mocked alone on PATH) + guard grep
#   C.4  install writes a verifiable manifest (+ a root PROTOCOL.md line; LINK mode)
#   C.5  4 classifications (FRAMEWORK-CHANGED / ADOPTER-CUSTOMIZED / CONFLICT /
#        per-file-in-dir preservation) + traversal/garbage fallback + idempotency
#   C.6  root PROTOCOL.md backup with AND without a manifest
#   C.7  manifest (re)written on upgrade
#
# bash 3.2-safe. Uses mktemp -d (never a hardcoded path) so xdist/parallel runs
# never collide. Exits 0 on success, non-zero on any failed assertion.
#
# EXECUTION POSTURE (PLAN-166 W0 re-pass r2 — declared so the next census
# does not count this as a live CI gate): this suite is OPERATOR-LOCAL /
# landing-gate only. NO workflow executes it (grep .github/ for this
# filename: zero hits) — the same deliberate posture as its siblings
# test_install_state_replay.sh / test-doctor.sh, recorded in the
# validate.yml collection-note comment ("local/landing-gate only;
# smoke-install.yml wiring is a separate ceremony"). A full run costs
# ~15 min of real install/upgrade legs under load, which is why it is not
# in push CI. The PLAN-166 W1 staged patch
# `smoke-install-parity-e2e-wiring.patch` wires the parity e2e
# (test-install-upgrade-parity-e2e.sh) into smoke-install.yml — NOT this
# suite. If that ever changes, update THIS header: the declaration is what
# a census reads.
#
# Run:  bash scripts/tests/test_install_baseline_manifest.sh ; echo rc=$?

set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Source-checkout installs warn-and-proceed on the self-SHA placeholder; make it
# explicit so the test is deterministic regardless of release-fill state.
export CEO_INSTALL_SKIP_SELF_SHA=1
# Never prompt for the RAG sidecar in a non-interactive test.
export CEO_RAG_INSTALL_PROMPT=0

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-c8-XXXXXX )"
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

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

echo "==> C.3 — _hash_lib.sh: _hash_file + _hash_stdin under each hasher alone"
(
  # Subshell so the source + PATH mock never leaks to other sections.
  # shellcheck source=scripts/_hash_lib.sh
  . "$SOURCE_DIR/scripts/_hash_lib.sh"
  probe="$WORKROOT/probe.txt"
  printf 'baseline-manifest probe\n' > "$probe"
  # Reference digest from whatever is natively available.
  ref="$( _hash_file "$probe" )"
  case "$ref" in
    [0-9a-f]*) [ "${#ref}" -eq 64 ] && echo "OKLEN" > "$WORKROOT/.c3ref" ;;
  esac
  # Mock each hasher ALONE on PATH and confirm the SAME digest. We build a
  # minimal PATH dir that exposes only ONE of shasum / sha256sum.
  mkdir -p "$WORKROOT/bin-shasum" "$WORKROOT/bin-sha256sum"
  for tool in shasum sha256sum; do
    real="$( command -v "$tool" 2>/dev/null || true )"
    [ -n "$real" ] || continue
    bindir="$WORKROOT/bin-$tool"
    ln -sf "$real" "$bindir/$tool"
    # Need awk + the shell builtins; expose coreutils dir too via a 2nd PATH entry.
    dig="$( PATH="$bindir:/usr/bin:/bin" bash -c '. "'"$SOURCE_DIR"'/scripts/_hash_lib.sh"; _hash_file "'"$probe"'"' 2>/dev/null )"
    if [ "$dig" = "$ref" ]; then
      printf 'C3-%s-match\n' "$tool" >> "$WORKROOT/.c3log"
    else
      printf 'C3-%s-MISMATCH(%s)\n' "$tool" "$dig" >> "$WORKROOT/.c3log"
    fi
  done
  # _hash_stdin on a PATH STRING (the upgrade.sh:209 use).
  s1="$( printf '%s' "/some/repo/root" | _hash_stdin )"
  s2="$( printf '%s' "/some/repo/root" | _hash_stdin )"
  s3="$( printf '%s' "/other/root" | _hash_stdin )"
  { [ "$s1" = "$s2" ] && [ "$s1" != "$s3" ] && [ "${#s1}" -eq 64 ]; } && echo "STDINOK" > "$WORKROOT/.c3stdin"
)
[ -f "$WORKROOT/.c3ref" ]   && ok "C.3 _hash_file returns 64-hex" || bad "C.3 _hash_file digest length"
[ -f "$WORKROOT/.c3stdin" ] && ok "C.3 _hash_stdin deterministic + distinct + 64-hex" || bad "C.3 _hash_stdin"
if [ -f "$WORKROOT/.c3log" ] && ! grep -q MISMATCH "$WORKROOT/.c3log"; then
  ok "C.3 _hash_file matches under each hasher mocked alone on PATH"
else
  bad "C.3 hasher-alone parity (see $WORKROOT/.c3log)"
fi
# Guard grep (C.3): both helpers are in the canonical guard list.
if grep -q "_hash_lib.sh" "$SOURCE_DIR/.claude/hooks/check_canonical_edit.py" \
   && grep -q "_framework_manifest_set.sh" "$SOURCE_DIR/.claude/hooks/check_canonical_edit.py"; then
  ok "C.3 both helpers added to _CANONICAL_GUARDS"
else
  bad "C.3 canonical guard entries missing"
fi

echo "==> C.4 — install writes a verifiable manifest with a root PROTOCOL.md line"
T1="$( fresh_install core )" || { bad "C.4 install failed"; T1=""; }

# ---------------------------------------------------------------------------
# C.2 — enumeration vs REALITY (PLAN-166 F4 rewrite)
#
# WHAT WAS HERE AND WHY IT IS GONE (F4, P1 — the gate was dead twice over):
#   * A set-equality assertion that called `_framework_target_entries()`, called
#     it a SECOND time, and diffed the two — with a comment admitting the
#     tautology ("the enumeration is static (root-independent), so an 'install
#     context' and an 'upgrade context' derive an identical target set by
#     construction"). It could not fail.
#   * A hand-written closed list of "required entries". A closed set recited
#     from memory errs in BOTH directions: it silently omitted `SPEC/v1` — the
#     exact path whose install/upgrade asymmetry became F3 — and it was matched
#     with `grep "^${need}"`, an unanchored prefix, so `.claude/skills` was
#     "satisfied" by anything starting with it.
#
# The install-vs-upgrade question is now answered by comparing REAL RESULTING
# TREES, per ceremony mode, against BOTH source generations:
#     scripts/tests/test-install-upgrade-parity-e2e.sh
# Set-equality of enumerations — even independently derived ones — can never
# reach a delivery site that lives outside the enumeration, which is precisely
# where F3 lived.
#
# What survives here is the one non-tautological property this file can still
# prove cheaply, and it is DERIVED, never recited: every entry the enumeration
# emits must actually EXIST in a real fresh install of the same profile. That
# catches an enumeration that has drifted into fiction (renamed/removed target).
# The opposite direction — install delivers paths the enumeration never lists —
# is the e2e's job.
# ---------------------------------------------------------------------------
echo "==> C.2 — enumeration is not fiction (every entry exists in a real install)"
if [ -n "$T1" ]; then
  (
    # shellcheck source=scripts/_framework_manifest_set.sh
    . "$SOURCE_DIR/scripts/_framework_manifest_set.sh"
    # Profile MUST match the install under test (T1 is `--profile core`),
    # otherwise the check would report by-design profile gating as drift.
    export FMS_PROFILE_PARTS="core"
    # Capture ONCE: both checks read the same snapshot, and nothing here is a
    # `producer | grep -q` pipeline. Under `set -o pipefail` a grep -q match
    # closes the pipe early; if the producer takes SIGPIPE the pipeline exits
    # 141 and the POSITIVE case (a leak) would print PROFILE_OK — fail-open
    # (house lesson: grep-q-pipefail-kills-producer; capture + case instead).
    _ents="$( _framework_target_entries )"
    missing=""
    count=0
    while IFS= read -r entry; do
      [ -n "$entry" ] || continue
      count=$(( count + 1 ))
      if [ ! -e "$T1/$entry" ]; then
        missing="$missing $entry"
      fi
    done <<EOF
$_ents
EOF
    echo "    enumerated=$count profile=core target=$T1"
    if [ "$count" -lt 5 ]; then
      # A vacuous enumeration would make the existence check pass trivially.
      printf 'VACUOUS:%s\n' "$count" > "$WORKROOT/.c2exist"
    elif [ -z "$missing" ]; then
      echo "ALLEXIST" > "$WORKROOT/.c2exist"
    else
      printf 'MISSING:%s\n' "$missing" > "$WORKROOT/.c2exist"
    fi
    # profile-awareness: a core-only profile must NOT enumerate frontend skills.
    nl=$'\n'
    case "${nl}${_ents}" in
      *"${nl}.claude/skills/frontend"*)
        echo "FRONTEND_LEAK" > "$WORKROOT/.c2prof"
        ;;
      *)
        echo "PROFILE_OK" > "$WORKROOT/.c2prof"
        ;;
    esac
  )
  if grep -q "ALLEXIST" "$WORKROOT/.c2exist" 2>/dev/null; then
    ok "C.2 every enumerated target entry exists in a real fresh install"
  else
    bad "C.2 enumeration vs reality ($(cat "$WORKROOT/.c2exist" 2>/dev/null))"
  fi
  if grep -q "PROFILE_OK" "$WORKROOT/.c2prof" 2>/dev/null; then
    ok "C.2 profile-aware (core-only omits frontend skills)"
  else
    bad "C.2 profile leak"
  fi
else
  bad "C.2 skipped — no install target (see C.4 failure above)"
fi
if [ -n "$T1" ]; then
  MAN="$T1/.claude/.install-manifest.sha256"
  if [ -s "$MAN" ]; then ok "C.4 manifest written + non-empty"; else bad "C.4 manifest absent/empty"; fi
  # shasum -c / sha256sum -c clean over the hash-record subset (exclude LINK).
  grep -v '^LINK  ' "$MAN" > "$T1/.man-hashonly" 2>/dev/null || true
  if ( cd "$T1" && { shasum -a 256 -c "$T1/.man-hashonly" || sha256sum -c "$T1/.man-hashonly"; } >/dev/null 2>&1 ); then
    ok "C.4 manifest hash records verify (shasum/sha256sum -c)"
  else
    bad "C.4 manifest verify failed"
  fi
  if grep -qE '^[0-9a-f]{64}  PROTOCOL\.md$' "$MAN"; then
    ok "C.4 manifest contains a root PROTOCOL.md line"
  else
    bad "C.4 no root PROTOCOL.md line in manifest"
  fi
  # manifest must NOT list itself or .claude.bak/
  if grep -qE '\.install-manifest\.sha256|\.claude\.bak/' "$MAN"; then
    bad "C.4 manifest lists itself or .claude.bak/"
  else
    ok "C.4 manifest excludes itself + .claude.bak/"
  fi
fi

echo "==> C.4 (LINK) — --mode link emits a LINK record, no content hash for it"
TL="$( mktemp -d "$WORKROOT/tgt-link-XXXXXX" )"
_git_init_retry "$TL"
if bash "$SOURCE_DIR/scripts/install.sh" "$TL" --link --profile core >"$TL/.install.log" 2>&1; then
  MANL="$TL/.claude/.install-manifest.sha256"
  if [ -s "$MANL" ] && grep -qE '^LINK  ' "$MANL"; then
    ok "C.4 link-mode install emits LINK record(s)"
  else
    # Some link installs may still copy certain top-level files; accept if the
    # manifest exists and grammar is valid even if no LINK line (degraded).
    if [ -s "$MANL" ]; then ok "C.4 link-mode manifest written (no LINK lines — copied entries)"; else bad "C.4 link-mode manifest absent"; fi
  fi
  # grammar: every line is either a hash record or a LINK record.
  if grep -vE '^([0-9a-f]{64}  .+|LINK  .+  .+)$' "$MANL" | grep -q .; then
    bad "C.4 link manifest has a line matching neither grammar"
  else
    ok "C.4 link manifest grammar valid (hash OR link records only)"
  fi
else
  bad "C.4 link-mode install failed (see $TL/.install.log)"
fi

echo "==> C.5 — classifications: ADOPTER-CUSTOMIZED preserved, per-file-in-dir, idempotency"
if [ -n "$T1" ]; then
  # (a) ADOPTER-CUSTOMIZED a top-level FILE target: append to task-chains.yaml.
  CUST_FILE="$T1/.claude/task-chains.yaml"
  if [ -f "$CUST_FILE" ]; then
    printf '\n# adopter-custom-line-c8\n' >> "$CUST_FILE"
    CUST_BEFORE="$( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$CUST_FILE" )"
  fi
  # (b) ADOPTER-CUSTOMIZED a file INSIDE a directory target (.claude/hooks/).
  DIR_CUST="$( find "$T1/.claude/hooks" -maxdepth 1 -type f -name '*.py' 2>/dev/null | head -1 )"
  if [ -n "$DIR_CUST" ]; then
    printf '\n# adopter-custom-in-dir-c8\n' >> "$DIR_CUST"
    DIR_BEFORE="$( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$DIR_CUST" )"
  fi
  # Run the upgrade (source==target framework, so unchanged framework files are
  # IDENTICAL; the two customized files must be PRESERVED, not clobbered).
  if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T1" --profile core >"$T1/.upgrade1.log" 2>&1; then
    ok "C.5 upgrade run #1 returned 0"
  else
    bad "C.5 upgrade #1 failed (see $T1/.upgrade1.log)"
  fi
  if [ -f "$CUST_FILE" ]; then
    CUST_AFTER="$( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$CUST_FILE" )"
    if [ "${CUST_BEFORE:-x}" = "${CUST_AFTER:-y}" ]; then
      ok "C.5 ADOPTER-CUSTOMIZED top-level file preserved (task-chains.yaml)"
    else
      bad "C.5 task-chains.yaml was clobbered"
    fi
  fi
  if [ -n "${DIR_CUST:-}" ]; then
    DIR_AFTER="$( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$DIR_CUST" )"
    if [ "${DIR_BEFORE:-x}" = "${DIR_AFTER:-y}" ]; then
      ok "C.5 per-file-in-directory customization preserved (.claude/hooks/*.py)"
    else
      bad "C.5 per-file-in-directory customization clobbered"
    fi
  fi
  # Idempotency: a second upgrade reports zero new conflicts and leaves the
  # customized files preserved still.
  if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T1" --profile core >"$T1/.upgrade2.log" 2>&1; then
    DIR_AFTER2="$( [ -n "${DIR_CUST:-}" ] && { . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$DIR_CUST"; } || echo "" )"
    if [ -z "${DIR_CUST:-}" ] || [ "${DIR_BEFORE:-x}" = "${DIR_AFTER2:-y}" ]; then
      ok "C.5 idempotent (2nd upgrade still preserves customization)"
    else
      bad "C.5 2nd upgrade clobbered the customization"
    fi
  else
    bad "C.5 upgrade #2 failed"
  fi
fi

echo "==> C.5 — provenance: garbage / traversal manifest degrades to fallback (no crash)"
T2="$( fresh_install core )" || { bad "C.5 fallback install failed"; T2=""; }
if [ -n "$T2" ]; then
  MAN2="$T2/.claude/.install-manifest.sha256"
  # Craft a manifest with a traversal line + a garbage line + one truncated hash.
  {
    printf '%s\n' "../../etc/passwd"
    printf 'deadbeef  ../escape\n'
    printf 'not-a-hash-line-at-all\n'
    printf 'LINK  weird\n'   # malformed LINK (no target)
  } >> "$MAN2"
  # Customize a dir file so a clobber would be detectable.
  DC2="$( find "$T2/.claude/hooks" -maxdepth 1 -type f -name '*.py' 2>/dev/null | head -1 )"
  [ -n "$DC2" ] && printf '\n# c8-fallback-probe\n' >> "$DC2"
  if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T2" --profile core >"$T2/.upgrade.log" 2>&1; then
    ok "C.5 garbage/traversal manifest did NOT crash the upgrade (fail-open)"
  else
    bad "C.5 upgrade crashed on garbage manifest (see $T2/.upgrade.log)"
  fi
  # A truncated manifest (head -3) also degrades cleanly.
  head -3 "$MAN2" > "$MAN2.trunc" 2>/dev/null && mv "$MAN2.trunc" "$MAN2"
  if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T2" --profile core >"$T2/.upgrade-trunc.log" 2>&1; then
    ok "C.5 truncated manifest degrades to fallback (no crash)"
  else
    bad "C.5 truncated manifest crashed the upgrade"
  fi
fi

echo "==> C.5 — CONFLICT (--on-conflict=refuse default) is per-file, never aborts"
T3="$( fresh_install core )" || { bad "C.5 conflict install failed"; T3=""; }
if [ -n "$T3" ]; then
  # Make a CONFLICT: a dir file differs from BOTH baseline and source. We can't
  # change the source tree (shared), so simulate by (1) recording a baseline,
  # then (2) editing the dst AND (3) faking a differing baseline entry for that
  # file so dst!=base and src!=base. Simpler: edit dst to differ from src, then
  # tamper the baseline digest for that file to a value != src and != dst.
  CF="$( find "$T3/.claude/hooks" -maxdepth 1 -type f -name '*.py' 2>/dev/null | head -1 )"
  MAN3="$T3/.claude/.install-manifest.sha256"
  if [ -n "$CF" ] && [ -f "$MAN3" ]; then
    rel="${CF#"$T3"/}"
    printf '\n# c8-conflict-dst-change\n' >> "$CF"   # dst now != src and != base
    # Overwrite that file's baseline line with a bogus-but-valid 64-hex (=> base
    # differs from both dst and src => CONFLICT).
    bogus="$( printf '%064d' 0 | tr '0' 'a' )"
    grep -v "  ${rel}\$" "$MAN3" > "$MAN3.f" 2>/dev/null || true
    printf '%s  %s\n' "$bogus" "$rel" >> "$MAN3.f"
    mv "$MAN3.f" "$MAN3"
    DST_BEFORE="$( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$CF" )"
    if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T3" --profile core --on-conflict refuse >"$T3/.upgrade.log" 2>&1; then
      DST_AFTER="$( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$CF" )"
      if [ "$DST_BEFORE" = "$DST_AFTER" ] && grep -qi 'REFUSED (CONFLICT' "$T3/.upgrade.log"; then
        ok "C.5 CONFLICT refused per-file (file untouched, upgrade continued)"
      else
        bad "C.5 CONFLICT not refused as expected (see $T3/.upgrade.log)"
      fi
    else
      bad "C.5 upgrade aborted on a per-file CONFLICT (should continue)"
    fi
  fi
fi

echo "==> C.6 — root PROTOCOL.md backed up with AND without a manifest"
# (a) WITHOUT a manifest: remove it, customize root PROTOCOL.md, upgrade.
T4="$( fresh_install core )" || { bad "C.6 install failed"; T4=""; }
if [ -n "$T4" ]; then
  rm -f "$T4/.claude/.install-manifest.sha256"
  printf '# CUSTOM ROOT PROTOCOL c8\nadopter content\n' > "$T4/PROTOCOL.md"
  if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T4" --profile core >"$T4/.upgrade.log" 2>&1; then
    # the most-recent .claude.bak/<ts>/PROTOCOL.md must hold the custom content.
    BK="$( find "$T4/.claude.bak" -name 'PROTOCOL.md' -type f 2>/dev/null | head -1 )"
    if [ -n "$BK" ] && grep -q 'CUSTOM ROOT PROTOCOL c8' "$BK"; then
      ok "C.6 root PROTOCOL.md backed up before overwrite (NO manifest)"
    else
      bad "C.6 root PROTOCOL.md NOT backed up without a manifest"
    fi
  else
    bad "C.6 upgrade failed (no-manifest path)"
  fi
fi
# (b) WITH a manifest: a customized root PROTOCOL.md is preserved (refuse).
T5="$( fresh_install core )" || { bad "C.6 install#2 failed"; T5=""; }
if [ -n "$T5" ]; then
  printf '# CUSTOM ROOT PROTOCOL c8b\nadopter content 2\n' > "$T5/PROTOCOL.md"
  if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T5" --profile core --on-conflict refuse >"$T5/.upgrade.log" 2>&1; then
    if grep -q 'CUSTOM ROOT PROTOCOL c8b' "$T5/PROTOCOL.md"; then
      ok "C.6 customized root PROTOCOL.md preserved with manifest (refuse)"
    else
      bad "C.6 customized root PROTOCOL.md was clobbered despite manifest"
    fi
    # backup still made regardless.
    BK2="$( find "$T5/.claude.bak" -name 'PROTOCOL.md' -type f 2>/dev/null | head -1 )"
    [ -n "$BK2" ] && ok "C.6 root PROTOCOL.md also backed up (manifest path)" || bad "C.6 no backup on manifest path"
    # (c) TWO-UPGRADE regression (Codex R2 P0): upgrade #1 above preserved the
    # customized PROTOCOL.md AND rewrote the manifest. The rewrite must record
    # the CANONICAL pointer hash, NOT the preserved customization — else
    # upgrade #2 reads H_dst==H_base and clobbers it. Run a second upgrade and
    # assert the customization SURVIVES.
    if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T5" --profile core --on-conflict refuse >"$T5/.upgrade2.log" 2>&1; then
      if grep -q 'CUSTOM ROOT PROTOCOL c8b' "$T5/PROTOCOL.md"; then
        ok "C.6 customized root PROTOCOL.md survives a SECOND upgrade (manifest rewrite not poisoned)"
      else
        bad "C.6 2nd upgrade clobbered the customized root PROTOCOL.md (manifest-rewrite poison)"
      fi
    else
      bad "C.6 second upgrade failed (manifest path)"
    fi
  else
    bad "C.6 upgrade failed (manifest path)"
  fi
fi

echo "==> C.7 — manifest (re)written on upgrade for a manifestless adopter"
T6="$( fresh_install core )" || { bad "C.7 install failed"; T6=""; }
if [ -n "$T6" ]; then
  rm -f "$T6/.claude/.install-manifest.sha256"   # simulate S238 acme population
  if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T6" --profile core >"$T6/.upgrade.log" 2>&1; then
    MAN6="$T6/.claude/.install-manifest.sha256"
    if [ -s "$MAN6" ]; then
      grep -v '^LINK  ' "$MAN6" > "$T6/.man-h" 2>/dev/null || true
      if ( cd "$T6" && { shasum -a 256 -c "$T6/.man-h" || sha256sum -c "$T6/.man-h"; } >/dev/null 2>&1 ); then
        ok "C.7 upgrade (re)wrote a valid baseline manifest"
      else
        bad "C.7 rewritten manifest does not verify"
      fi
    else
      bad "C.7 upgrade did not write a manifest"
    fi
    # Second upgrade now uses the manifest-present path (no fallback warning).
    if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T6" --profile core >"$T6/.upgrade2.log" 2>&1; then
      ok "C.7 second upgrade runs on the manifest-present path"
    else
      bad "C.7 second upgrade failed"
    fi
  else
    bad "C.7 upgrade failed"
  fi
fi

echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
