#!/usr/bin/env bash
# test-install-harness-codex.sh — PLAN-155 Wave 5 (SENT-CX-C) installer matrix
# =============================================================================
# The debate-A11 NINE-case matrix for `install.sh --harness codex`:
#   1. no-flag run byte-identical to --harness claude (+ no codex artifacts)
#   2. --harness codex: every registered command path resolves AND is
#      executable at the harness's REAL runtime resolution (shim dirname, not
#      cwd), executed as a subprocess from a foreign cwd
#   3. --dry-run: zero writes
#   4. unknown harness => usage error (exit 2), no partial writes
#   5. idempotent re-run (identical-skip, exit 0)
#   6. --harness round-trips through the manifest into upgrade.sh replay
#   7. RENDERED operator AGENTS.md <= 32768 bytes (post-substitution)
#   8. --with-codex-skills is N/A-guarded (Wave 8 not landed): no .codex/skills/
#   9. pre-existing-files collision: refuse-and-print-diff default; --force
#      backs up + overwrites (A10 — never clobber)
#
# DURABLE pre/post-landing: the test assembles the SOURCE tree it installs from
# by overlaying whatever PLAN-155/PLAN-154 staged wave dirs still exist onto a
# copy of the repo. Once the waves land, those staged dirs are gone and the
# overlay is just the repo — same test, both worlds.
#
# Hermetic: never touches the real $HOME / $CODEX_HOME; all installs go to
# throwaway target dirs under a mktemp workdir. No codex binary required (the
# runtime-resolution case runs the shipped command lines as subprocesses; the
# real-binary live-fire is the T2 tier recorded under PLAN-155/artifacts/).
#
# Exit 0 = all cases pass. shellcheck -S warning clean.
# =============================================================================
set -uo pipefail

# ---- locate the repo root (dir containing scripts/install.sh) --------------
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
  echo "FATAL: could not locate repo root (scripts/install.sh + .claude/) above $_dir" >&2
  exit 1
fi

WORK="$( mktemp -d "${TMPDIR:-/tmp}/ceo-harness-matrix.XXXXXX" )"
cleanup() { rm -rf "$WORK" 2>/dev/null || true; }
trap cleanup EXIT

PASS=0
FAIL=0
note() { printf '    %s\n' "$*"; }
ok()   { PASS=$((PASS+1)); printf 'PASS  %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf 'FAIL  %s\n' "$*" >&2; }

# ---- assemble the SOURCE overlay (repo + staged waves, landing order) -------
SRC="$WORK/src"
echo "==> Assembling SOURCE overlay at $SRC (repo + any staged PLAN-155 waves)"
mkdir -p "$SRC"
# Copy the repo (exclude the heavy/irrelevant VCS + node dirs).
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude '.git' --exclude 'node_modules' "$REPO_ROOT"/ "$SRC"/ >/dev/null 2>&1
else
  cp -R "$REPO_ROOT"/. "$SRC"/ 2>/dev/null || true
  rm -rf "$SRC/.git" 2>/dev/null || true
fi
# Overlay staged waves if present (landing order: sent-f, wave-1, wave-2, wave-5).
_overlay() {
  local d="$SRC/.claude/plans/$1"
  [ -d "$d" ] || return 0
  note "overlay: $1"
  # copy every path under the staged dir into $SRC at the mirrored location
  ( cd "$d" && find . -type f -print ) | while IFS= read -r rel; do
    rel="${rel#./}"
    mkdir -p "$SRC/$( dirname "$rel" )"
    cp "$d/$rel" "$SRC/$rel"
  done
}
_overlay "PLAN-154/staged/sent-f"
_overlay "PLAN-155/staged/wave-1"
_overlay "PLAN-155/staged/wave-2"
_overlay "PLAN-155/staged/wave-5"
# Ensure exec bits on the scripts we invoke.
chmod +x "$SRC/scripts/install.sh" "$SRC/scripts/upgrade.sh" 2>/dev/null || true
[ -f "$SRC/scripts/_codex_harness.sh" ] || { echo "FATAL: overlay missing scripts/_codex_harness.sh" >&2; exit 1; }
[ -f "$SRC/templates/codex/hooks.json" ] || { echo "FATAL: overlay missing templates/codex/hooks.json" >&2; exit 1; }

INSTALL="$SRC/scripts/install.sh"
UPGRADE="$SRC/scripts/upgrade.sh"

# Hermetic env for every install: fake HOME/CODEX_HOME, skip self-SHA (source
# tree), non-interactive.
export HOME="$WORK/home"; mkdir -p "$HOME"
export CODEX_HOME="$WORK/codex-home"; mkdir -p "$CODEX_HOME"
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
  # $1 = target, rest = flags. Captures rc; logs to per-target file.
  local t="$1"; shift
  ( cd "$SRC" && bash "$INSTALL" "$t" "${COMMON_FLAGS[@]}" "$@" ) \
    > "$t/.install.log" 2> "$t/.install.err"
}

# Files that are inherently volatile across two runs (timestamps / content
# hashes) and must be excluded from any byte-identity diff.
_VOLATILE=( ".install-state.json" ".install-manifest.sha256" )
_strip_volatile() {
  local root="$1" v
  for v in "${_VOLATILE[@]}"; do
    find "$root" -name "$v" -type f -exec rm -f {} + 2>/dev/null || true
  done
}

# =============================================================================
echo ""
echo "==> Case 1 — no-flag ≡ --harness claude (byte-identical) + no codex artifacts"
# Install BOTH into the SAME target path (sequentially, wipe between) so every
# placeholder ($TARGET, {{PROJECT_NAME}}, {{PROJECT_PATH}}, the PROTOCOL.md
# pointer that embeds the target path) renders identically — the ONLY variable
# under test is the presence/absence of --harness claude.
T_C1="$( _fresh_target case1 )"
_run_install "$T_C1"
c1a=$?
cp -R "$T_C1" "$WORK/c1a-cmp"
rm -rf "$T_C1"; mkdir -p "$T_C1"; ( cd "$T_C1" && git init -q 2>/dev/null || true )
_run_install "$T_C1" --harness claude
c1b=$?
cp -R "$T_C1" "$WORK/c1b-cmp"
if [ "$c1a" -ne 0 ] || [ "$c1b" -ne 0 ]; then
  bad "case1: an install exited non-zero (noflag=$c1a claude=$c1b)"
  sed -n '1,20p' "$T_C1/.install.err" >&2 || true
else
  # No codex artifacts on the --harness claude install.
  _art=0
  [ -e "$T_C1/.codex" ] && { bad "case1: .codex/ present on claude path"; _art=1; }
  [ -e "$T_C1/AGENTS.md" ] && { bad "case1: AGENTS.md present on claude path"; _art=1; }
  [ -e "$T_C1/requirements.toml" ] && { bad "case1: requirements.toml present on claude path"; _art=1; }
  # Byte-identity (excluding volatile state/manifest + the harness log files).
  for d in "$WORK/c1a-cmp" "$WORK/c1b-cmp"; do
    _strip_volatile "$d"
    rm -f "$d/.install.log" "$d/.install.err" 2>/dev/null || true
    rm -rf "$d/.git" 2>/dev/null || true
  done
  if diff -r "$WORK/c1a-cmp" "$WORK/c1b-cmp" > "$WORK/c1.diff" 2>&1; then
    [ "$_art" -eq 0 ] && ok "case1: --harness claude is byte-identical to no-flag; no codex artifacts"
  else
    bad "case1: no-flag vs --harness claude differ"; sed -n '1,30p' "$WORK/c1.diff" >&2
  fi
fi

# =============================================================================
echo ""
echo "==> Case 2 — --harness codex: every command resolves + is executable + runs"
T_CX="$( _fresh_target case2-codex )"
# codex path requires a NON-worktree repo (worktree discovery gap); git init
# above makes a normal repo — good.
_run_install "$T_CX" --harness codex
c2=$?
if [ "$c2" -ne 0 ]; then
  bad "case2: --harness codex install exited $c2"; sed -n '1,30p' "$T_CX/.install.err" >&2
else
  miss=0
  for f in .codex/hooks.json .codex/rules/ceo.rules AGENTS.md; do
    [ -f "$T_CX/$f" ] || { bad "case2: missing emitted $f"; miss=1; }
  done
  # Placeholder must be gone from hooks.json (substituted to the abs target).
  if grep -q '{{PROJECT_PATH}}' "$T_CX/.codex/hooks.json" 2>/dev/null; then
    bad "case2: unsubstituted {{PROJECT_PATH}} left in .codex/hooks.json"; miss=1
  fi
  if [ "$miss" -eq 0 ]; then
    # Runtime resolution + subprocess execution of every registered command.
    if PYTHONNOUSERSITE=1 python3 -I "$SRC/scripts/tests/_case2_probe.py" "$T_CX" 2>"$WORK/c2.err"; then
      ok "case2: every registered command resolves, is executable, and runs (no shim ERROR)"
    else
      bad "case2: runtime-resolution probe failed"; sed -n '1,40p' "$WORK/c2.err" >&2
    fi
  fi
fi

# =============================================================================
echo ""
echo "==> Case 3 — --harness codex --dry-run writes nothing"
T_DRY="$( _fresh_target case3-dry )"
_run_install "$T_DRY" --harness codex --dry-run
c3=$?
# A dry-run must not create .claude/, .codex/, AGENTS.md, requirements.toml.
if [ "$c3" -eq 0 ] \
   && [ ! -e "$T_DRY/.codex" ] && [ ! -e "$T_DRY/AGENTS.md" ] \
   && [ ! -e "$T_DRY/requirements.toml" ] && [ ! -e "$T_DRY/.claude" ]; then
  ok "case3: dry-run produced zero writes"
else
  bad "case3: dry-run wrote files (rc=$c3): $(ls -A "$T_DRY" 2>/dev/null | tr '\n' ' ')"
fi

# =============================================================================
echo ""
echo "==> Case 4 — unknown harness => usage error (exit 2), no partial writes"
T_BAD="$( _fresh_target case4-bad )"
( cd "$SRC" && bash "$INSTALL" "$T_BAD" "${COMMON_FLAGS[@]}" --harness bogus ) \
  > "$T_BAD/.log" 2> "$T_BAD/.err"
c4=$?
if [ "$c4" -eq 2 ] && [ ! -e "$T_BAD/.claude" ] && [ ! -e "$T_BAD/.codex" ]; then
  ok "case4: unknown harness rejected with exit 2, no partial writes"
else
  bad "case4: expected exit 2 + no writes; got rc=$c4, contents: $(ls -A "$T_BAD" 2>/dev/null | tr '\n' ' ')"
fi

# =============================================================================
echo ""
echo "==> Case 5 — idempotent re-run (--harness codex twice)"
T_IDEM="$( _fresh_target case5-idem )"
_run_install "$T_IDEM" --harness codex
c5a=$?
# snapshot the codex bundle after run 1
h1="$( shasum -a 256 "$T_IDEM/.codex/hooks.json" 2>/dev/null | awk '{print $1}' )"
_run_install "$T_IDEM" --harness codex
c5b=$?
h2="$( shasum -a 256 "$T_IDEM/.codex/hooks.json" 2>/dev/null | awk '{print $1}' )"
if [ "$c5a" -eq 0 ] && [ "$c5b" -eq 0 ] && [ -n "$h1" ] && [ "$h1" = "$h2" ]; then
  # And the second run must NOT have created a --force backup.
  if ls "$T_IDEM"/.codex/hooks.json.ceo-bak-* >/dev/null 2>&1 || ls "$T_IDEM"/AGENTS.md.ceo-bak-* >/dev/null 2>&1; then
    bad "case5: idempotent re-run created a backup (should identical-skip)"
  else
    ok "case5: re-run is idempotent (exit 0, bundle byte-stable, no backups)"
  fi
else
  bad "case5: re-run not idempotent (rc1=$c5a rc2=$c5b h1=$h1 h2=$h2)"
fi

# =============================================================================
echo ""
echo "==> Case 6 — --harness round-trips through the manifest into upgrade.sh replay"
T_RT="$( _fresh_target case6-rt )"
_run_install "$T_RT" --harness codex
c6i=$?
# state must record harness=codex
if command -v python3 >/dev/null 2>&1; then
  _rec="$( PYTHONNOUSERSITE=1 python3 -I -c 'import json,sys
d=json.load(open(sys.argv[1])); print(d.get("request",{}).get("harness",""))' "$T_RT/.claude/.install-state.json" 2>/dev/null )"
else
  _rec="?"
fi
( cd "$SRC" && bash "$UPGRADE" "$T_RT" --profile core ) > "$T_RT/.up.log" 2> "$T_RT/.up.err"
c6u=$?
if [ "$c6i" -eq 0 ] && [ "$_rec" = "codex" ] && grep -q 'REPLAY: --harness codex' "$T_RT/.up.err" && [ -f "$T_RT/.codex/hooks.json" ]; then
  ok "case6: install recorded harness=codex; upgrade replayed it (REPLAY line) and kept .codex/"
else
  bad "case6: round-trip failed (install rc=$c6i, recorded='$_rec', upgrade rc=$c6u)"
  grep -i 'harness\|replay' "$T_RT/.up.err" >&2 || true
fi

# =============================================================================
echo ""
echo "==> Case 7 — RENDERED operator AGENTS.md <= 32768 bytes"
if [ -f "$T_CX/AGENTS.md" ]; then
  _sz="$( wc -c < "$T_CX/AGENTS.md" | tr -d ' ' )"
  if [ "$_sz" -le 32768 ]; then
    ok "case7: rendered AGENTS.md is $_sz bytes (<= 32768)"
  else
    bad "case7: rendered AGENTS.md is $_sz bytes (> 32768 = codex project_doc_max_bytes)"
  fi
else
  bad "case7: no rendered AGENTS.md from case 2 install"
fi

# =============================================================================
echo ""
echo "==> Case 8 — --with-codex-skills is N/A-guarded (Wave 8 not landed)"
T_SK="$( _fresh_target case8-skills )"
_run_install "$T_SK" --harness codex --with-codex-skills
c8=$?
if [ "$c8" -eq 0 ] && [ ! -e "$T_SK/.codex/skills" ]; then
  if grep -q 'NO-OP until PLAN-155 Wave 8' "$T_SK/.install.log"; then
    ok "case8: --with-codex-skills is a guarded no-op (no .codex/skills/, note printed)"
  else
    bad "case8: no-op guard note not printed"
  fi
else
  bad "case8: --with-codex-skills created .codex/skills/ or failed (rc=$c8)"
fi

# =============================================================================
echo ""
echo "==> Case 9 — pre-existing collision: refuse-and-print-diff default; --force backs up"
T_COL="$( _fresh_target case9-collision )"
# Pre-seed a FOREIGN AGENTS.md before install.
printf 'PRE-EXISTING OPERATOR FILE — do not clobber\n' > "$T_COL/AGENTS.md"
_seed_sha="$( shasum -a 256 "$T_COL/AGENTS.md" | awk '{print $1}' )"
_run_install "$T_COL" --harness codex
c9a=$?
_after_sha="$( shasum -a 256 "$T_COL/AGENTS.md" | awk '{print $1}' )"
if [ "$c9a" -ne 0 ] && [ "$_seed_sha" = "$_after_sha" ]; then
  note "refuse path OK (exit $c9a, AGENTS.md unchanged)"
  # Now --force must back up the original and overwrite.
  _run_install "$T_COL" --harness codex --force
  c9b=$?
  _forced_sha="$( shasum -a 256 "$T_COL/AGENTS.md" | awk '{print $1}' )"
  if [ "$c9b" -eq 0 ] && [ "$_forced_sha" != "$_seed_sha" ] && ls "$T_COL"/AGENTS.md.ceo-bak-* >/dev/null 2>&1; then
    _bak="$( ls "$T_COL"/AGENTS.md.ceo-bak-* | head -n1 )"
    _bak_sha="$( shasum -a 256 "$_bak" | awk '{print $1}' )"
    if [ "$_bak_sha" = "$_seed_sha" ]; then
      ok "case9: default refuses (no clobber); --force backs up original + overwrites"
    else
      bad "case9: --force backup does not match the original bytes"
    fi
  else
    bad "case9: --force did not overwrite+backup (rc=$c9b)"
  fi
else
  bad "case9: default did not refuse without --force (rc=$c9a, seed=$_seed_sha after=$_after_sha)"
fi

# =============================================================================
echo ""
echo "==> Bonus — uninstall lifecycle symmetry (A9): removes emitted paths, restores backup"
# Reuse T_COL (has a --force backup recorded). Uninstall should restore AGENTS.md.
( cd "$SRC" && bash "$INSTALL" "$T_COL" --harness codex --uninstall ) > "$T_COL/.uni.log" 2>&1
cu=$?
_uni_sha="$( shasum -a 256 "$T_COL/AGENTS.md" 2>/dev/null | awk '{print $1}' )"
if [ "$cu" -eq 0 ] && [ ! -e "$T_COL/.codex/hooks.json" ] && [ "$_uni_sha" = "$_seed_sha" ]; then
  ok "bonus: uninstall removed .codex/ + restored the pre-existing AGENTS.md from backup"
else
  bad "bonus: uninstall left residue or did not restore (rc=$cu, agents_sha=$_uni_sha)"
fi

# =============================================================================
echo ""
echo "============================================================"
echo "  PLAN-155 Wave 5 installer matrix: $PASS passed, $FAIL failed"
echo "============================================================"
[ "$FAIL" -eq 0 ]
