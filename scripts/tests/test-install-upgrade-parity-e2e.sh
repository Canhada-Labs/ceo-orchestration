#!/usr/bin/env bash
# scripts/tests/test-install-upgrade-parity-e2e.sh
# PLAN-166 W0 / F4 (OQ-4) — install≠upgrade parity, measured on the RESULTING
# TREES, per ceremony mode.
#
# WHY THIS EXISTS (F4, P1)
# ------------------------
# The previous parity gate was dead twice over:
#   (a) TAUTOLOGICAL — scripts/tests/test_install_baseline_manifest.sh "C.2"
#       compared `_framework_target_entries()` with `_framework_target_entries()`
#       and admitted it in a comment ("the enumeration is static
#       (root-independent), so an 'install context' and an 'upgrade context'
#       derive an identical target set by construction"). It also carried a
#       hand-written closed list of "required entries".
#   (b) INVISIBLE — no workflow ran scripts/tests/*.sh except smoke-install.yml,
#       and neither the old assertion nor this file was wired into it. 5th
#       instance of the "red gate nobody runs" class.
# Set-equality of ENUMERATIONS — even independently derived ones — can NEVER
# reach the delivery sites that live OUTSIDE the enumeration. That is exactly
# how F3 was born: `SPEC/v1` is delivered by install.sh (`install_one "SPEC/v1"`,
# install.sh:1307) and by NOTHING in upgrade.sh, and it is absent from
# `_framework_target_entries()`. So this test compares REAL TREES.
#
# WHAT IT DOES
# ------------
#   Route A (fresh)      : install.sh (WORKING TREE)                      -> A
#   Route B (historical) : install.sh @ $PIN -> upgrade.sh (WORKING TREE) -> B
# for EACH ceremony mode (maintainer, user). Both targets get the SAME basename
# so install.sh's {{PROJECT_NAME}} substitution is identical on both sides.
#
# THE MEASUREMENT (why "diff -r A B" is the wrong instrument)
# -----------------------------------------------------------
# A raw byte-diff of the two trees answers "are these two installs identical",
# which is not the question. The question is "did the upgrade deliver the
# CURRENT generation of framework content?" So every path is classified against
# BOTH source generations (the working tree and the $PIN archive):
#
#   IDENTICAL      A(p) == B(p)                                      ok
#   PERSONALIZED   B(p) == head_src(p): upgrade shipped CURRENT       advisory
#                  framework bytes; install.sh additionally
#                  substitutes {{PROJECT_NAME}}-class placeholders
#   STALE          B(p) == pin_src(p) != head_src(p): the upgrade     FATAL
#                  LEFT THE OLD GENERATION IN PLACE   <-- F3 signature
#   MISSING_IN_B   install delivered p, upgrade did not               FATAL
#   UNCLASSIFIED   diverges and matches neither generation            FATAL
#                  (generated/adopter-owned paths must be DECLARED)
#   MODE_DIFF      same bytes, different +x bit ("cp lost the exec     FATAL
#                  bit" is a verified S286 failure mode here)
#   ONLY_IN_B      upgrade's `cp -R` drags content install's          advisory
#                  selective walk never ships (ADR-155 pre-existing
#                  drift) -- EXCEPT outside .claude/ in `user` mode,
#                  which is FATAL (the WS4 no-writes-outside-.claude
#                  invariant that smoke-install.yml already asserts
#                  for install and nobody asserts for upgrade)
#
# Declarations are checked for ROT in both directions:
#   * KNOWN-OPEN ledger entries are MANDATORY-FIRE: an entry that matches
#     nothing is FATAL ("the bug you named is closed -- delete the entry").
#     A ledger cannot outlive its bug.
#   * DECLARED generated/adopter-owned paths that turn out IDENTICAL emit a
#     WARNING (declaration is stale; harmless).
#   * Any divergence matching NO declaration is FATAL. That is the live gate;
#     the positive control trips exactly there.
#
# EXIT CODES
#   0  parity   — no fatal divergence and no KNOWN-OPEN entry outstanding
#   1  FAIL     — undeclared divergence (what the positive control must
#                 produce, and what a real install/upgrade regression produces)
#   2  KNOWN-OPEN — only the explicitly named PLAN-166 W1 prerequisites are
#                 outstanding. STILL A FAILURE, never a silent skip: the
#                 printed ledger names each one and what unblocks it. This is
#                 the expected pre-W1 result.
#   9  SCAFFOLD-ERROR — the fixture itself broke (tag unresolvable, install or
#                 upgrade returned non-zero, python3 missing). NEVER a verdict
#                 on the bug. In CI the historical leg needs the TAG: a
#                 `fetch-depth: 1` checkout does not have it.
#
# POSITIVE CONTROL
#   --positive-control deletes ONE `backup_and_replace "<dir>"` line from a COPY
#   of upgrade.sh and re-runs the whole thing. The expected outcome is exit 1 in
#   EVERY mode tested. If any mode does NOT go fatal, the run ends in exit 9
#   SCAFFOLD-ERROR ("the control is vacuous"), never in a green — a control that
#   silently stops firing is worse than no control at all. That happens for a
#   real reason: the plant only bites if the planted directory actually drifted
#   between $PIN and HEAD, so the guard is DERIVED from the run, not asserted
#   from memory.
#   ORDERING MATTERS: the control only proves something when the UN-planted run
#   was not already fatal, otherwise rc=1 could come from a pre-existing
#   divergence rather than from the plant. So CI runs the plain gate FIRST and
#   the control only after it passed; run it the same way by hand.
#
# USAGE
#   bash scripts/tests/test-install-upgrade-parity-e2e.sh
#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --mode user
#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --positive-control
#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin
#
# W1 CHECKLIST: the KNOWN_OPEN ledger in _parity_classify.py is MANDATORY-FIRE.
# When W1 lands the F3 fix those entries stop matching and the classifier goes
# fatal on ledger-rot BY DESIGN — deleting them belongs to the same commit.
#
# bash-3.2 safe (no associative arrays, no mapfile). Network-free. Writes only
# under mktemp -d. Requires: git, python3, tar.

set -uo pipefail   # NOT -e: failures are classified, not fatal-by-default.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

PIN="${CEO_PARITY_PIN:-v1.2.0}"
PROFILE="${CEO_PARITY_PROFILE:-core}"
MODES="maintainer user"
POSITIVE_CONTROL=0
# The single line deleted from a COPY of upgrade.sh by --positive-control.
PLANT_TARGET='.claude/commands'

PRINT_PIN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODES="${2:-}"; shift 2 ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --pin) PIN="${2:-}"; shift 2 ;;
    --positive-control) POSITIVE_CONTROL=1; shift ;;
    # Only meaningful with --positive-control. Exists so the vacuity guard
    # itself can be exercised: planting a target that did NOT drift between
    # $PIN and HEAD must end in exit 9, not in a green.
    --plant-target) PLANT_TARGET="${2:-}"; shift 2 ;;
    # Single source of truth for the historical pin: CI must FETCH this tag
    # (the checkout is fetch-depth:1 and has no tags), and hardcoding the value
    # in the workflow would make a second copy of the truth that drifts.
    --print-pin) PRINT_PIN=1; shift ;;
    # Print the header block, whatever its length — a hardcoded `sed -n '2,80p'`
    # silently truncates the help the first time the header grows.
    -h|--help) awk 'NR>1 && /^[^#]/ {exit} NR>1 {print}' "$0"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 9 ;;
  esac
done

if [ "$PRINT_PIN" -eq 1 ]; then
  printf '%s\n' "$PIN"
  exit 0
fi
[ "$MODES" = "both" ] && MODES="maintainer user"

scaffold() { echo "" >&2; echo "SCAFFOLD-ERROR: $*" >&2; exit 9; }

command -v python3 >/dev/null 2>&1 || scaffold "python3 not on PATH"
command -v git     >/dev/null 2>&1 || scaffold "git not on PATH"
command -v tar     >/dev/null 2>&1 || scaffold "tar not on PATH"

CLASSIFY="$SCRIPT_DIR/_parity_classify.py"
[ -f "$CLASSIFY" ] || scaffold "classifier missing: $CLASSIFY"

WORK="$( mktemp -d -t ceo-parity-e2e-XXXXXX )" || scaffold "mktemp -d failed"
# shellcheck disable=SC2329  # invoked indirectly by the EXIT trap below
cleanup() {
  [ "${CEO_PARITY_KEEP_WORK:-0}" = "1" ] && return 0
  [ -n "${WORK:-}" ] || return 0
  find "$WORK" -mindepth 1 -depth -exec chmod u+w {} + 2>/dev/null || true
  find "$WORK" -mindepth 1 -depth -delete 2>/dev/null || true
  rmdir "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

# Non-interactive install/upgrade. A source checkout carries a placeholder
# self-SHA; skipping it keeps the fixture deterministic regardless of
# release-fill state (the same knobs smoke-install.yml already uses).
export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

echo "=============================================================="
echo " install/upgrade parity e2e  (PLAN-166 F4 / OQ-4)"
echo "=============================================================="
echo "  repo (route A source) : $REPO_ROOT"
echo "  historical pin        : $PIN"
echo "  profile               : $PROFILE"
echo "  ceremony modes        : $MODES"
echo "  positive control      : $POSITIVE_CONTROL"
echo "  workdir               : $WORK"
echo "  git describe (repo)   : $( git -C "$REPO_ROOT" describe --tags --always --dirty 2>/dev/null || echo '(n/a)' )"
echo "--------------------------------------------------------------"

# --- historical source: pure read of the tag, never a repo mutation ---------
if ! git -C "$REPO_ROOT" rev-parse --verify --quiet "refs/tags/$PIN" >/dev/null 2>&1; then
  {
    echo ""
    echo "  tag '$PIN' does not resolve in $REPO_ROOT."
    echo "  In CI this is the fetch-depth:1 hole — the checkout has no tags, so"
    echo "  the historical leg cannot run, and 'it passes on my clone' is"
    echo "  exactly the gap this test exists to close. Fetch the tag first:"
    echo "      git fetch --no-tags --depth 1 origin +refs/tags/$PIN:refs/tags/$PIN"
  } >&2
  scaffold "historical pin '$PIN' unresolvable — refusing to skip"
fi
PIN_SRC="$WORK/src-$PIN"
mkdir -p "$PIN_SRC"
if ! git -C "$REPO_ROOT" archive "$PIN" | tar -x -C "$PIN_SRC"; then
  scaffold "git archive $PIN | tar -x failed"
fi
[ -f "$PIN_SRC/scripts/install.sh" ] || scaffold "$PIN archive has no scripts/install.sh"

# --- optional planted-divergence source for the positive control ------------
# A depth-1 symlink farm over the working tree with ONE edited file. upgrade.sh
# derives SOURCE_DIR from its own location ("cd $SCRIPT_DIR/.." with a logical
# pwd), so the farm root becomes the source and every other path resolves
# through the symlinks to the live tree. Cheap (no 75MB copy) and it perturbs
# exactly one line, which is what a positive control is for.
PLANTED_SRC=""
if [ "$POSITIVE_CONTROL" -eq 1 ]; then
  PLANTED_SRC="$WORK/src-planted"
  mkdir -p "$PLANTED_SRC/scripts"
  for _e in "$REPO_ROOT"/* "$REPO_ROOT"/.[!.]* "$REPO_ROOT"/..?*; do
    [ -e "$_e" ] || continue
    _b="$( basename "$_e" )"
    [ "$_b" = "scripts" ] && continue
    ln -s "$_e" "$PLANTED_SRC/$_b" 2>/dev/null || true
  done
  for _f in "$REPO_ROOT"/scripts/* "$REPO_ROOT"/scripts/.[!.]*; do
    [ -e "$_f" ] || continue
    _b="$( basename "$_f" )"
    [ "$_b" = "upgrade.sh" ] && continue
    ln -s "$_f" "$PLANTED_SRC/scripts/$_b" 2>/dev/null || true
  done
  _before="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$REPO_ROOT/scripts/upgrade.sh" || true )"
  grep -v "^backup_and_replace \"$PLANT_TARGET\"\$" \
    "$REPO_ROOT/scripts/upgrade.sh" > "$PLANTED_SRC/scripts/upgrade.sh" \
    || scaffold "could not write planted upgrade.sh"
  _after="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$PLANTED_SRC/scripts/upgrade.sh" || true )"
  if [ "${_before:-0}" -lt 1 ] || [ "${_after:-1}" -ne 0 ]; then
    scaffold "planting failed: backup_and_replace \"$PLANT_TARGET\" occurrences before=$_before after=$_after — the control perturbed nothing"
  fi
  echo "  PLANTED: dropped backup_and_replace \"$PLANT_TARGET\" from a COPY of"
  echo "           upgrade.sh (occurrences $_before -> $_after). The live"
  echo "           scripts/upgrade.sh is untouched."
  echo "--------------------------------------------------------------"
fi

_git_init() {
  _n=0
  while [ "$_n" -lt 5 ]; do
    ( cd "$1" && git init -q 2>/dev/null ) && return 0
    _n=$(( _n + 1 )); sleep 1
  done
  ( cd "$1" && git init -q )
}

OVERALL=0          # 0 parity | 1 fail | 2 known-open
MODE_VERDICTS=""   # "mode:rc" pairs, bash-3.2 has no associative arrays
for MODE in $MODES; do
  echo ""
  echo "##############################################################"
  echo "# ceremony mode: $MODE"
  echo "##############################################################"

  # SAME basename on both sides: install.sh substitutes {{PROJECT_NAME}} with
  # basename($TARGET). Different basenames would fabricate ~30 phantom
  # divergences that say nothing about install/upgrade parity.
  A_DIR="$WORK/$MODE/route-a/adopter"
  B_DIR="$WORK/$MODE/route-b/adopter"
  mkdir -p "$A_DIR" "$B_DIR"
  _git_init "$A_DIR"; _git_init "$B_DIR"

  echo "--> [A] install.sh (working tree) --ceremony $MODE --profile $PROFILE"
  if ! bash "$REPO_ROOT/scripts/install.sh" "$A_DIR" \
        --profile "$PROFILE" --ceremony "$MODE" \
        >"$WORK/$MODE-a-install.log" 2>&1; then
    tail -40 "$WORK/$MODE-a-install.log" >&2
    scaffold "[A] install.sh failed (mode=$MODE)"
  fi

  echo "--> [B1] install.sh @ $PIN --ceremony $MODE --profile $PROFILE"
  if ! bash "$PIN_SRC/scripts/install.sh" "$B_DIR" \
        --profile "$PROFILE" --ceremony "$MODE" \
        >"$WORK/$MODE-b-install.log" 2>&1; then
    tail -40 "$WORK/$MODE-b-install.log" >&2
    scaffold "[B1] install.sh @ $PIN failed (mode=$MODE)"
  fi

  UP_SRC="$REPO_ROOT"
  [ -n "$PLANTED_SRC" ] && UP_SRC="$PLANTED_SRC"
  echo "--> [B2] upgrade.sh (source: $UP_SRC)"
  if ! bash "$UP_SRC/scripts/upgrade.sh" "$B_DIR" \
        --profile "$PROFILE" --no-diff-warn \
        >"$WORK/$MODE-b-upgrade.log" 2>&1; then
    tail -40 "$WORK/$MODE-b-upgrade.log" >&2
    scaffold "[B2] upgrade.sh failed (mode=$MODE)"
  fi

  echo "--> classify"
  # When planted, the farm root is a THIRD absolute source path that can be
  # embedded in generated files; fold it too, so the control fails for the
  # planted reason instead of for an unfolded /tmp path.
  EXTRA_ARGS=""
  [ -n "$PLANTED_SRC" ] && EXTRA_ARGS="--extra-source $PLANTED_SRC"
  # shellcheck disable=SC2086  # EXTRA_ARGS is a controlled, space-free pair
  python3 "$CLASSIFY" \
    --a "$A_DIR" --b "$B_DIR" \
    --head-src "$REPO_ROOT" --pin-src "$PIN_SRC" --pin "$PIN" \
    --mode "$MODE" $EXTRA_ARGS
  rc=$?
  case "$rc" in
    0) : ;;
    2) [ "$OVERALL" -eq 0 ] && OVERALL=2 ;;
    1) OVERALL=1 ;;
    *) scaffold "classifier returned unexpected rc=$rc (mode=$MODE)" ;;
  esac
  MODE_VERDICTS="$MODE_VERDICTS $MODE:$rc"
done

echo ""
echo "--------------------------------------------------------------"
echo "per-mode verdicts (0 parity / 1 fail / 2 known-open):$MODE_VERDICTS"

# --- positive-control self-check ------------------------------------------
# A control that stops firing must never read as a pass. Requiring rc==1 in
# EVERY mode is DERIVED from the run: the plant only bites if the planted
# directory actually drifted between $PIN and HEAD.
if [ "$POSITIVE_CONTROL" -eq 1 ]; then
  _not_fatal=""
  for _pair in $MODE_VERDICTS; do
    _m="${_pair%%:*}"; _r="${_pair##*:}"
    [ "$_r" = "1" ] || _not_fatal="$_not_fatal $_m(rc=$_r)"
  done
  if [ -n "$_not_fatal" ]; then
    {
      echo ""
      echo "  The plant removed backup_and_replace \"$PLANT_TARGET\" from the copy"
      echo "  of upgrade.sh, yet these modes did NOT go FATAL:$_not_fatal"
      echo "  Most likely cause: nothing under '$PLANT_TARGET' changed between"
      echo "  $PIN and HEAD, so removing its refresh is undetectable — the"
      echo "  control is vacuous and proves nothing. Pick a PLANT_TARGET with"
      echo "  real drift, or advance the pin."
    } >&2
    scaffold "positive control did not fire in every mode"
  fi
  echo "positive control: FIRED in every mode (rc=1 each) — the gate is alive."
fi

echo ""
echo "=============================================================="
case "$OVERALL" in
  0) echo "RESULT: PASS — install and upgrade converge on the same framework"
     echo "        content in every ceremony mode tested ($MODES)." ;;
  2) {
       echo "RESULT: KNOWN-OPEN (exit 2) — the ONLY outstanding divergences are the"
       echo "        explicitly named PLAN-166 W1 prerequisites printed above."
       echo "        This is a FAILURE, not a skip. It goes green when W1 lands."
     } >&2 ;;
  1) echo "RESULT: FAIL (exit 1) — undeclared install/upgrade divergence above." >&2 ;;
esac
echo "=============================================================="
exit "$OVERALL"
