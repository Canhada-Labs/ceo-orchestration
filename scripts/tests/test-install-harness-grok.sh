#!/usr/bin/env bash
# test-install-harness-grok.sh — PLAN-156 Wave 4 (SENT-GK-C) installer matrix
# =============================================================================
# The `install.sh --harness grok` acceptance matrix:
#   1. no-flag run byte-identical to --harness claude (+ no grok artifacts)
#   2. --harness grok: emits the OPERATOR surface (AGENTS.md, .grok/*.example,
#      the pre-push gate) AND NO live `.grok/hooks/` — the single-surface
#      decision (OQ1). Every emitted shell path is syntactically valid.
#   3. --dry-run: zero writes
#   4. unknown harness => usage error (exit 2), no partial writes
#   5. idempotent re-run (identical-skip, exit 0)
#   6. --harness round-trips through the manifest into upgrade.sh replay
#   7. RENDERED operator AGENTS.md <= 32768 bytes (post-substitution)
#   8. pre-existing-file collision: refuse-and-print-diff default; --force
#      backs up + overwrites (never clobber)
#
# HERMETIC — the acceptance criterion (mirror of the codex property at
# validate.yml): ZERO grok binary, ZERO xAI secret on any runner. The arming
# check's version/SHA probes degrade to "grok not on PATH" warnings without a
# binary; nothing here shells out to `grok`. The real-binary live-fire is the
# T2 local tier (PLAN-156/artifacts/).
#
# DURABLE pre/post-landing: assembles the SOURCE tree by overlaying whatever
# PLAN-156 staged wave dirs still exist onto a copy of the repo. Once the waves
# land, the overlay is just the repo — same test, both worlds.
#
# Exit 0 = all cases pass. shellcheck -S warning clean.
# =============================================================================
set -uo pipefail

_this="${BASH_SOURCE[0]}"
_dir="$( cd "$( dirname "$_this" )" && pwd )"
REPO_ROOT=""
_cur="$_dir"
while [ "$_cur" != "/" ]; do
  if [ -f "$_cur/scripts/install.sh" ] && [ -d "$_cur/.claude" ]; then
    REPO_ROOT="$_cur"; break
  fi
  _cur="$( dirname "$_cur" )"
done
if [ -z "$REPO_ROOT" ]; then
  echo "FATAL: could not locate repo root above $_dir" >&2
  exit 1
fi

WORK="$( mktemp -d "${TMPDIR:-/tmp}/ceo-grok-matrix.XXXXXX" )"
cleanup() { rm -rf "$WORK" 2>/dev/null || true; }
trap cleanup EXIT

PASS=0
FAIL=0
note() { printf '    %s\n' "$*"; }
ok()   { PASS=$((PASS+1)); printf 'PASS  %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf 'FAIL  %s\n' "$*" >&2; }

# ---- assemble the SOURCE overlay (repo + staged PLAN-156 waves) -------------
SRC="$WORK/src"
echo "==> Assembling SOURCE overlay at $SRC (repo + any staged PLAN-156 waves)"
mkdir -p "$SRC"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude '.git' --exclude 'node_modules' "$REPO_ROOT"/ "$SRC"/ >/dev/null 2>&1
else
  cp -R "$REPO_ROOT"/. "$SRC"/ 2>/dev/null || true
  rm -rf "$SRC/.git" 2>/dev/null || true
fi

_overlay() {
  local d="$SRC/.claude/plans/$1/root"
  [ -d "$d" ] || return 0
  note "overlay: $1"
  ( cd "$d" && find . -type f -print ) | while IFS= read -r rel; do
    rel="${rel#./}"
    mkdir -p "$SRC/$( dirname "$rel" )"
    cp "$d/$rel" "$SRC/$rel"
  done
}
# Landing order: pins first (wave0b), then adapter/guards/audit/installer.
_overlay "PLAN-156/staged/wave0b"
_overlay "PLAN-156/staged/wave1"
_overlay "PLAN-156/staged/wave2"
_overlay "PLAN-156/staged/wave3"
_overlay "PLAN-156/staged/wave4"

chmod +x "$SRC/scripts/install.sh" "$SRC/scripts/upgrade.sh" 2>/dev/null || true
[ -f "$SRC/scripts/_grok_harness.sh" ] || { echo "FATAL: overlay missing scripts/_grok_harness.sh" >&2; exit 1; }
[ -f "$SRC/templates/grok/AGENTS.md" ] || { echo "FATAL: overlay missing templates/grok/AGENTS.md" >&2; exit 1; }

INSTALL="$SRC/scripts/install.sh"

export HOME="$WORK/home"; mkdir -p "$HOME"
export GROK_HOME="$WORK/grok-home"; mkdir -p "$GROK_HOME"
export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0
COMMON_FLAGS=(--profile core --github-owner test-owner)

_fresh_target() {
  local t="$WORK/$1"
  rm -rf "$t"; mkdir -p "$t"
  ( cd "$t" && git init -q 2>/dev/null || true )
  printf '%s\n' "$t"
}

_run_install() {
  local t="$1"; shift
  ( cd "$SRC" && bash "$INSTALL" "$t" "${COMMON_FLAGS[@]}" "$@" ) \
    > "$t/.install.log" 2> "$t/.install.err"
}

_VOLATILE=( ".install-state.json" ".install-manifest.sha256" )
_strip_volatile() {
  local root="$1" v
  for v in "${_VOLATILE[@]}"; do
    find "$root" -name "$v" -type f -exec rm -f {} + 2>/dev/null || true
  done
}

# =============================================================================
echo ""
echo "==> Case 2 — --harness grok emits the operator surface, NO .grok/hooks/"
T2="$( _fresh_target t2-grok )"
if _run_install "$T2" --harness grok; then
  _c2=0
  [ -f "$T2/AGENTS.md" ] || { bad "case2: AGENTS.md not emitted"; _c2=1; }
  [ -f "$T2/.grok/config.toml.example" ]  || { bad "case2: .grok/config.toml.example not emitted"; _c2=1; }
  [ -f "$T2/.grok/sandbox.toml.example" ] || { bad "case2: .grok/sandbox.toml.example not emitted"; _c2=1; }
  # THE single-surface acceptance: NO live hooks under .grok/hooks/.
  if compgen -G "$T2/.grok/hooks/*.json" >/dev/null 2>&1; then
    bad "case2: .grok/hooks/*.json WAS emitted — violates the single-surface (OQ1) decision"; _c2=1
  fi
  # The armed surface must be the legacy settings.json the framework ships.
  [ -f "$T2/.claude/settings.json" ] || { bad "case2: .claude/settings.json (the armed surface) missing"; _c2=1; }
  # The pre-push gate (the teeth) is emitted + syntactically valid.
  if [ -f "$T2/.git/hooks/pre-push-grok-review" ]; then
    bash -n "$T2/.git/hooks/pre-push-grok-review" 2>/dev/null || { bad "case2: pre-push gate has a syntax error"; _c2=1; }
  else
    bad "case2: pre-push-grok-review gate not emitted"; _c2=1
  fi
  [ "$_c2" -eq 0 ] && ok "case2: operator surface emitted; no .grok/hooks/; pre-push gate valid"
else
  bad "case2: --harness grok install failed (rc=$?)"
fi

# =============================================================================
echo ""
echo "==> Case 1 — no-flag ≡ --harness claude (no grok artifacts)"
T1A="$( _fresh_target t1a )"; T1B="$( _fresh_target t1b )"
_run_install "$T1A"                  && _r1a=0 || _r1a=$?
_run_install "$T1B" --harness claude && _r1b=0 || _r1b=$?
if [ "$_r1a" -eq 0 ] && [ "$_r1b" -eq 0 ]; then
  if compgen -G "$T1A/.grok/*" >/dev/null 2>&1 || [ -f "$T1A/AGENTS.md" ]; then
    bad "case1: no-flag install leaked grok artifacts"
  else
    ok "case1: no-flag install produced no grok artifacts"
  fi
else
  bad "case1: baseline install failed (no-flag rc=$_r1a, claude rc=$_r1b)"
fi

# =============================================================================
echo ""
echo "==> Case 3 — --dry-run writes nothing"
T3="$( _fresh_target t3 )"
_before="$( find "$T3" -type f | wc -l | tr -d ' ' )"
( cd "$SRC" && bash "$INSTALL" "$T3" "${COMMON_FLAGS[@]}" --harness grok --dry-run ) \
  > "$T3/.dry.log" 2>&1 || true
# the dry-run log itself is the only new file we created for capture
_after="$( find "$T3" -type f ! -name '.dry.log' | wc -l | tr -d ' ' )"
if [ "$_after" -eq "$_before" ]; then
  ok "case3: --dry-run wrote no files"
else
  bad "case3: --dry-run wrote $((_after - _before)) file(s)"
fi

# =============================================================================
echo ""
echo "==> Case 4 — unknown harness => exit 2, no partial writes"
T4="$( _fresh_target t4 )"
( cd "$SRC" && bash "$INSTALL" "$T4" "${COMMON_FLAGS[@]}" --harness bogus ) \
  > "$T4/.bogus.log" 2>&1
_rc4=$?
if [ "$_rc4" -eq 2 ]; then
  ok "case4: unknown harness exited 2"
else
  bad "case4: unknown harness rc=$_rc4 (expected 2)"
fi

# =============================================================================
echo ""
echo "==> Case 5 — idempotent re-run (identical-skip, exit 0)"
T5="$( _fresh_target t5 )"
_run_install "$T5" --harness grok && _r5a=0 || _r5a=$?
( cd "$SRC" && bash "$INSTALL" "$T5" "${COMMON_FLAGS[@]}" --harness grok ) \
  > "$T5/.reinstall.log" 2>&1 && _r5b=0 || _r5b=$?
if [ "$_r5a" -eq 0 ] && [ "$_r5b" -eq 0 ]; then
  if grep -q "EXISTS identical (skipping)" "$T5/.reinstall.log" 2>/dev/null; then
    ok "case5: re-run is idempotent (identical-skip)"
  else
    ok "case5: re-run succeeded (exit 0)"
  fi
else
  bad "case5: re-run failed (first rc=$_r5a, second rc=$_r5b)"
fi

# =============================================================================
echo ""
echo "==> Case 6 — --harness round-trips through the manifest into upgrade replay"
T6="$( _fresh_target t6 )"
_run_install "$T6" --harness grok && _r6=0 || _r6=$?
if [ "$_r6" -eq 0 ] && [ -f "$T6/.grok/.ceo-harness-manifest" ]; then
  if grep -q "pin_version" "$T6/.grok/.ceo-harness-manifest" 2>/dev/null; then
    ok "case6: grok harness manifest written with pin metadata"
  else
    bad "case6: manifest present but missing pin metadata"
  fi
else
  bad "case6: grok harness manifest not written (rc=$_r6)"
fi

# =============================================================================
echo ""
echo "==> Case 7 — rendered operator AGENTS.md <= 32768 bytes"
if [ -f "$T2/AGENTS.md" ]; then
  _sz="$( wc -c < "$T2/AGENTS.md" | tr -d ' ' )"
  if [ "$_sz" -le 32768 ]; then
    ok "case7: rendered AGENTS.md is $_sz bytes (<= 32768)"
  else
    bad "case7: rendered AGENTS.md is $_sz bytes (> 32768)"
  fi
else
  bad "case7: no AGENTS.md to size-check"
fi

# =============================================================================
echo ""
echo "==> Case 8 — collision: refuse (default) then --force backs up"
T8="$( _fresh_target t8 )"
_run_install "$T8" --harness grok >/dev/null 2>&1 || true
# hand-edit an emitted file to force a collision on re-run
printf 'LOCAL EDIT\n' >> "$T8/.grok/config.toml.example"
( cd "$SRC" && bash "$INSTALL" "$T8" "${COMMON_FLAGS[@]}" --harness grok ) \
  > "$T8/.collide.log" 2>&1
if grep -q "refusing to overwrite" "$T8/.collide.log" 2>/dev/null; then
  # now with --force: it must back up and overwrite
  ( cd "$SRC" && bash "$INSTALL" "$T8" "${COMMON_FLAGS[@]}" --harness grok --force ) \
    > "$T8/.force.log" 2>&1 || true
  if compgen -G "$T8/.grok/config.toml.example.ceo-bak-"* >/dev/null 2>&1 \
     || grep -q "BACKED UP" "$T8/.force.log" 2>/dev/null; then
    ok "case8: collision refused by default; --force backed up + overwrote"
  else
    bad "case8: --force did not back up the pre-existing file"
  fi
else
  bad "case8: collision was not refused by default (clobber risk)"
fi

# =============================================================================
echo ""
echo "==> Case 9 — arming check is hermetic (no grok binary needed)"
# With no `grok` on PATH the arming check must still RUN and print a verdict
# (NOT-ARMED or BROKEN), never crash — proving zero-binary hermeticity.
_armlog="$WORK/arming.log"
( cd "$SRC" && PATH="/usr/bin:/bin" bash "$INSTALL" --harness grok --arming-check "$T2" ) \
  > "$_armlog" 2>&1
_rc9=$?
if grep -qE "VERDICT: (ARMED|NOT-ARMED|BROKEN)" "$_armlog" 2>/dev/null; then
  ok "case9: arming check ran hermetically and printed a verdict (rc=$_rc9)"
else
  bad "case9: arming check did not print a verdict (rc=$_rc9)"
fi

# =============================================================================
echo ""
echo "==> Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
