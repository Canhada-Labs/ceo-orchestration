#!/usr/bin/env bash
# scripts/tests/test-night-mode-ignore-effect.sh
# PLAN-177 W1 (CF-9) — EFFICACY of the posture-state ignores, not parity.
#
# WHY THIS EXISTS
# ---------------
# The install/upgrade parity e2e proves the two routes converge on the same
# BYTES, and BYTE-PROOF.md proves the generator reproduces install.sh's output
# exactly. Neither can see whether the delivered bytes actually WORK: an
# ineffective ignore — wrong anchor, wrong path, right file in the wrong
# directory — is equally ineffective on both routes, so it is byte-identical
# and every parity check stays green. That is the "instrument green with a
# stale question" class. This test asks the question the P1 actually named:
#
#   after `/night-mode on`, does `git status` in the adopter stay clean?
#
# PLAN-165 AC-1 words it as "git status stays empty"; the GA re-pass
# (verdict-ga-1.txt:5) names the `--ceremony user` population as the one that
# never got any protection, because a user install writes nothing outside
# .claude/ and the root .gitignore blocks are all there was.
#
# WHY THE ARTIFACTS ARE SIMULATED, NOT ARMED
# ------------------------------------------
# This test CREATES the two files `/night-mode on` leaves behind rather than
# invoking the toggle. That is not a sandbox shortcut — arming the autonomy
# posture is a HUMAN action (PLAN-165 OQ1-redo, Owner-ratified 2026-08-03) and
# the model rail is blocked from running `.claude/scripts/night-mode.py` at
# all. A CI job arming a real posture would be the same violation. What is
# under test is whether git ignores those two paths, and for that the file
# CONTENT is irrelevant — only their names and locations matter, and those are
# read from night-mode.py's own docstring/`_marker_path` (`.claude/state/
# night-mode.json`, `.claude/settings.local.json`).
#
# SCENARIOS
#   A  install @ $PIN (maintainer) -> upgrade (working tree)   [the upgrade route]
#   B  install @ $PIN (user)       -> upgrade (working tree)   [the damaged population]
#   C  install (working tree, user)                            [fresh user install]
#
# EVERY scenario carries its own POSITIVE CONTROL, inline and unconditional:
# after asserting the tree is clean, the delivered ignores are removed and the
# SAME assertion must go dirty. A control that can be skipped is a control that
# silently stops firing, so there is no flag to turn this off.
#
# EXIT CODES
#   0  every scenario clean, every control fired
#   1  FAIL — a night-mode artifact was visible to git, or a control did not fire
#   9  SCAFFOLD-ERROR — the fixture broke (pin unresolvable, install/upgrade
#      returned non-zero, git missing). NEVER a verdict on the bug.
#
# bash-3.2 safe. Network-free (the pin must already be fetched — CI does that
# in the "Fetch the parity pin tag" step). Writes only under mktemp -d.
set -uo pipefail

# HERMETIC IGNORE SOURCES — measured, not assumed.
#
# git consults THREE ignore sources outside the repo: the system config, the
# user's global config, and `core.excludesFile` (commonly
# ~/.config/git/ignore). On this maintainer's machine that file contains
# `**/.claude/settings.local.json`, which means the overlay is invisible to git
# whether or not the framework delivers anything. Left alone, that produces a
# test whose control is half-blind locally and full-sighted on a clean CI
# runner — "it passes on my machine" with the sign flipped, and the exact class
# the probe-needs-a-neutral-user-layer lesson names.
#
# Neutralising them makes every scenario measure ONLY what install/upgrade put
# in the target. GIT_CONFIG_GLOBAL/SYSTEM need git >= 2.32; each target also
# sets core.excludesFile to an empty file so older git is covered too.
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_SYSTEM=/dev/null

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Single source of truth for the pin: ask the parity e2e rather than hardcoding
# a second copy that drifts (the same rule smoke-install.yml follows).
PIN="${CEO_PARITY_PIN:-}"
if [ -z "$PIN" ]; then
  PIN="$( bash "$SCRIPT_DIR/test-install-upgrade-parity-e2e.sh" --print-pin 2>/dev/null )"
fi
PROFILE="${CEO_PARITY_PROFILE:-core}"

# The two paths `/night-mode on` writes. Derived from night-mode.py so a rename
# there surfaces here as a scaffold error instead of a silently narrowed test.
MARKER_REL=".claude/state/night-mode.json"
OVERLAY_REL=".claude/settings.local.json"

FAILED=0

say()  { echo "$@"; }
fail() { echo "  FAIL: $*" >&2; FAILED=1; }
scaffold() {
  echo "" >&2
  echo "SCAFFOLD-ERROR: $*" >&2
  echo "  (this is a broken fixture, NOT a verdict on the ignores)" >&2
  exit 9
}

command -v git >/dev/null 2>&1 || scaffold "git not on PATH"
[ -n "$PIN" ] || scaffold "could not resolve the historical pin (--print-pin returned empty)"
git -C "$REPO_ROOT" rev-parse --verify "refs/tags/$PIN^{commit}" >/dev/null 2>&1 \
  || scaffold "pin tag $PIN not present in this checkout (CI must fetch it first)"

# Assert night-mode.py still names the paths this test asserts on. A rename
# there would leave this test green while testing nothing.
_NM="$REPO_ROOT/.claude/scripts/night-mode.py"
if [ -f "$_NM" ]; then
  grep -Fq 'night-mode.json' "$_NM" \
    || scaffold "night-mode.py no longer mentions night-mode.json — re-derive MARKER_REL"
  grep -Fq 'settings.local.json' "$_NM" \
    || scaffold "night-mode.py no longer mentions settings.local.json — re-derive OVERLAY_REL"
fi

WORK="$( mktemp -d "${TMPDIR:-/tmp}/ceo-nightmode-ignore-XXXXXX" )" || scaffold "mktemp failed"
cleanup() { [ -n "${WORK:-}" ] && rm -rf "$WORK"; }
trap cleanup EXIT

say "=============================================================="
say " night-mode ignore EFFICACY  (PLAN-177 W1 / CF-9)"
say "=============================================================="
say "  repo            : $REPO_ROOT"
say "  historical pin  : $PIN"
say "  profile         : $PROFILE"
say "  workdir         : $WORK"
say "--------------------------------------------------------------"

PIN_SRC="$WORK/src-$PIN"
mkdir -p "$PIN_SRC"
git -C "$REPO_ROOT" archive "$PIN" | tar -x -C "$PIN_SRC" \
  || scaffold "git archive $PIN | tar -x failed"
[ -f "$PIN_SRC/scripts/install.sh" ] || scaffold "$PIN archive has no scripts/install.sh"

# --- helpers ---------------------------------------------------------------

new_target() {  # $1 = name -> echoes the path
  local t="$WORK/$1"
  mkdir -p "$t"
  : > "$WORK/empty-excludes"
  ( cd "$t" \
      && git init -q \
      && git config user.email t@e \
      && git config user.name t \
      && git config core.excludesFile "$WORK/empty-excludes" ) \
    || scaffold "git init failed in $t"
  echo "$t"
}

# Fail loudly if any ignore source outside the target survives the
# neutralisation above: a leftover rule would silently weaken every control.
assert_no_external_ignores() {  # $1 = target
  local src
  for src in "$MARKER_REL" "$OVERLAY_REL"; do
    local probe
    probe="$( cd "$1" && git check-ignore -v --no-index "$src" 2>/dev/null )" || true
    case "$probe" in
      ""|.gitignore:*|.claude/.gitignore:*) : ;;
      *) scaffold "an ignore source OUTSIDE the target still matches $src: $probe" ;;
    esac
  done
}

do_install() {  # $1 = source dir, $2 = target, $3 = ceremony
  CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    bash "$1/scripts/install.sh" "$2" --ceremony "$3" --profile "$PROFILE" \
    > "$2.install.log" 2>&1 \
    || scaffold "install.sh ($3, source=$1) exited non-zero — see $2.install.log"
}

do_upgrade() {  # $1 = target
  CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    bash "$REPO_ROOT/scripts/upgrade.sh" "$1" --profile "$PROFILE" \
    > "$1.upgrade.log" 2>&1 \
    || scaffold "upgrade.sh exited non-zero — see $1.upgrade.log"
}

arm_night_mode_artifacts() {  # $1 = target — simulate, never arm (see header)
  mkdir -p "$1/.claude/state"
  printf '%s\n' '{"armed": true, "plan": "PLAN-177 test fixture"}' > "$1/$MARKER_REL"
  printf '%s\n' '{"permissions": {"defaultMode": "acceptEdits"}}' > "$1/$OVERLAY_REL"
}

# Lines git reports for the two artifacts.
#
# `-uall` is LOAD-BEARING, not a flourish. Plain `git status --porcelain` in a
# repo where nothing is committed collapses the whole tree to a single
# `?? .claude/` line, so a matcher looking for `.claude/state/...` finds
# nothing and reports "clean" no matter what the ignores do. That vacuous shape
# is exactly what this test's own positive control caught on its first run, and
# it is why the scenarios commit a baseline first: a real adopter has the
# framework committed before ever running `/night-mode on`.
leaked() {  # $1 = target
  ( cd "$1" && git status --porcelain -uall 2>/dev/null ) \
    | grep -E "(\.claude/state/|\.claude/settings\.local\.json)" || true
}

# WHICH rule does the ignoring. `git status` alone cannot tell "ignored by the
# file we delivered" from "ignored by something else the adopter already had",
# and only the former is evidence for this cure. `git check-ignore -v` prints
# `<source>:<line>:<pattern>\t<path>`, so the source file is checkable.
ignoring_rule() {  # $1 = target, $2 = relpath
  ( cd "$1" && git check-ignore -v "$2" 2>/dev/null ) || true
}

strip_delivered_ignores() {  # $1 = target — the positive control's mutation
  rm -f "$1/.claude/.gitignore"
  if [ -f "$1/.gitignore" ]; then
    grep -v -x -e '.claude/state/' -e '.claude/settings.local.json' \
      "$1/.gitignore" > "$1/.gitignore.stripped" 2>/dev/null || true
    mv "$1/.gitignore.stripped" "$1/.gitignore"
  fi
}

commit_baseline() {  # $1 = target — what a real adopter does after installing
  ( cd "$1" && git add -A && git commit -q -m "install framework" ) \
    || scaffold "baseline commit failed in $1"
  # The install itself must not have staged posture state into that commit.
  local tracked
  tracked="$( cd "$1" && git ls-files | grep -E "(\.claude/state/|\.claude/settings\.local\.json)" || true )"
  [ -z "$tracked" ] && return 0
  fail "baseline commit TRACKS posture state (it should be ignored):"
  echo "$tracked" | sed 's/^/        /' >&2
}

check_scenario() {  # $1 = label, $2 = target
  local label="$1" t="$2" out n rule_m rule_o
  assert_no_external_ignores "$t"
  commit_baseline "$t"
  arm_night_mode_artifacts "$t"

  # Sanity: the artifacts really are on disk. Without this the "clean" verdict
  # could just mean nothing was ever created.
  [ -f "$t/$MARKER_REL" ]  || scaffold "$label: fixture did not create $MARKER_REL"
  [ -f "$t/$OVERLAY_REL" ] || scaffold "$label: fixture did not create $OVERLAY_REL"

  out="$( leaked "$t" )"
  if [ -n "$out" ]; then
    fail "$label: night-mode artifacts are VISIBLE to git:"
    echo "$out" | sed 's/^/        /' >&2
  else
    say "  $label: clean — git -uall sees no night-mode artifacts"
  fi

  # Attribution: a framework-delivered .gitignore must be the rule doing it.
  rule_m="$( ignoring_rule "$t" "$MARKER_REL" )"
  rule_o="$( ignoring_rule "$t" "$OVERLAY_REL" )"
  for _r in "$rule_m" "$rule_o"; do
    case "$_r" in
      .claude/.gitignore:*|.gitignore:*) : ;;
      "") fail "$label: no ignore rule matches one of the artifacts: '$_r'" ;;
      *)  fail "$label: ignored by an UNEXPECTED source (not a framework-delivered .gitignore): $_r" ;;
    esac
  done
  [ -n "$rule_m" ] && say "  $label: rule -> ${rule_m%%	*}"

  # --- inline positive control ---------------------------------------------
  strip_delivered_ignores "$t"
  out="$( leaked "$t" )"
  n="$( printf '%s' "$out" | grep -c . || true )"
  # BOTH artifacts must surface. "At least one" would pass while some other
  # ignore source still hid the other one -- which is exactly what happened on
  # the first run of this test, before the external sources were neutralised.
  if [ "$n" -ne 2 ]; then
    fail "$label: CONTROL FIRED PARTIALLY OR NOT AT ALL — after removing the"
    fail "       delivered ignores git should report BOTH artifacts, got $n:"
    [ -n "$out" ] && echo "$out" | sed 's/^/        /' >&2
    fail "       (something ELSE is hiding a path, or the matcher is blind)"
  else
    say "  $label: control fired — without the ignores git reports both artifacts"
  fi
}

# Count the posture entries in the ROOT .gitignore.
#
# WHY THIS EXISTS SEPARATELY from the git-status assertion: `.claude/.gitignore`
# alone is enough to make every scenario below report "clean", so an upgrade
# whose ROOT delivery silently did nothing would still pass. `git check-ignore`
# reports only the WINNING rule, and that is the .claude one. So the root block
# is measured directly, and BEFORE/AFTER — which also pins the fixture: the pin
# must still reproduce the gap, or the whole scenario has stopped testing it.
root_posture_count() {  # $1 = target -> number of the two posture entries present
  # `grep -c` PRINTS 0 and EXITS 1 when nothing matches, so the obvious
  # `grep -c ... || echo 0` emits TWO lines ("0\n0") and every arithmetic test
  # downstream dies with "integer expression expected". Capture first, then
  # default — verified by the run that produced exactly that scaffold error.
  local n
  [ -f "$1/.gitignore" ] || { echo 0; return 0; }
  n="$( grep -c -x -e '.claude/state/' -e '.claude/settings.local.json' "$1/.gitignore" 2>/dev/null )" || n=0
  [ -n "$n" ] || n=0
  echo "$n"
}

# --- A: pinned install (maintainer) -> upgrade -------------------------------
say ""
say "--> [A] install @ $PIN (maintainer) -> upgrade (working tree)"
TA="$( new_target A-pin-maintainer )"
do_install "$PIN_SRC" "$TA" maintainer
[ -f "$TA/.claude/.gitignore" ] && scaffold "[A] the $PIN install already ships .claude/.gitignore — the fixture no longer reproduces the gap"
_A_BEFORE="$( root_posture_count "$TA" )"
[ "$_A_BEFORE" -eq 0 ] || scaffold "[A] the $PIN install already writes $_A_BEFORE posture entr(y|ies) into the root .gitignore — the fixture no longer reproduces the P1-1 gap"
do_upgrade "$TA"
_A_AFTER="$( root_posture_count "$TA" )"
if [ "$_A_AFTER" -eq 2 ]; then
  say "  [A] root .gitignore: posture entries 0 -> 2 across the upgrade — the P1-1 delivery"
else
  fail "[A] the upgrade did NOT deliver the root posture block (entries: $_A_BEFORE -> $_A_AFTER, expected 2)"
fi
check_scenario "[A] upgrade/maintainer" "$TA"

# --- B: pinned install (user) -> upgrade -------------------------------------
say ""
say "--> [B] install @ $PIN (user) -> upgrade (working tree)"
TB="$( new_target B-pin-user )"
do_install "$PIN_SRC" "$TB" user
do_upgrade "$TB"
# The mirror assertion: in `user` ceremony NEITHER route touches the root, so
# the count must stay 0. A cure that delivered here would break the WS4
# invariant install.sh has always honoured — and the parity gate would only
# see it as a divergence, never as a rule violation.
_B_ROOT="$( root_posture_count "$TB" )"
if [ "$_B_ROOT" -eq 0 ]; then
  say "  [B] root .gitignore: still 0 posture entries — user ceremony skipped on BOTH routes"
else
  fail "[B] the upgrade wrote $_B_ROOT posture entr(y|ies) into the root .gitignore under --ceremony user"
fi
check_scenario "[B] upgrade/user" "$TB"

# --- C: fresh user install ---------------------------------------------------
say ""
say "--> [C] install (working tree) --ceremony user"
TC="$( new_target C-fresh-user )"
do_install "$REPO_ROOT" "$TC" user
# WS4 belt-and-braces: a user install must still write nothing outside .claude/
_extra=""
for _e in "$TC"/* "$TC"/.[!.]* "$TC"/..?*; do
  [ -e "$_e" ] || continue
  _b="$( basename "$_e" )"
  case "$_b" in .claude|.git) continue ;; esac
  _extra="$_extra $_b"
done
[ -n "$_extra" ] && fail "[C] --ceremony user wrote outside .claude/:$_extra"
check_scenario "[C] fresh/user" "$TC"

# --- D: SEEDED .claude/.gitignore (re-pass rc.4 t1 P1-b) --------------------
# The adopter already owns a .claude/.gitignore (e.g. only /cache/) that
# LACKS the two posture entries. Create-if-missing alone proved the clean
# target; the P1 was exactly this shape: helper saw the file, returned, and
# night-mode state stayed commit-eligible. Both routes must APPEND the two
# entries per line while preserving every adopter byte.
say ""
say "--> [D] fresh user install over a SEEDED .claude/.gitignore"
TD="$( new_target D-seeded-user )"
mkdir -p "$TD/.claude"
printf '%s\n' "# adopter file" "/cache/" > "$TD/.claude/.gitignore"
do_install "$REPO_ROOT" "$TD" user
for _need in "/cache/" "/state/" "/settings.local.json" "# adopter file"; do
  grep -Fxq "$_need" "$TD/.claude/.gitignore" \
    || fail "[D] seeded install: line missing or adopter byte lost: $_need"
done
check_scenario "[D] seeded/user-install" "$TD"

say ""
say "--> [D2] pinned user install -> SEED -> upgrade"
TD2="$( new_target D2-seeded-upgrade )"
do_install "$PIN_SRC" "$TD2" user
printf '%s\n' "# adopter file" "/cache/" > "$TD2/.claude/.gitignore"
do_upgrade "$TD2"
for _need in "/cache/" "/state/" "/settings.local.json" "# adopter file"; do
  grep -Fxq "$_need" "$TD2/.claude/.gitignore" \
    || fail "[D2] seeded upgrade: line missing or adopter byte lost: $_need"
done
check_scenario "[D2] seeded/upgrade" "$TD2"

say ""
say "--------------------------------------------------------------"
if [ "$FAILED" -eq 0 ]; then
  say "RESULT: PASS — after a simulated \`/night-mode on\`, git reports no"
  say "        posture artifacts in any route or ceremony, and every"
  say "        scenario's control fired."
  say "=============================================================="
  exit 0
fi
say "RESULT: FAIL (exit 1) — see the FAIL lines above."
say "=============================================================="
exit 1
