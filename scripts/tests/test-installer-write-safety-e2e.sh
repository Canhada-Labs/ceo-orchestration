#!/usr/bin/env bash
# PLAN-185 W1+W2 (S329) — the installer must not write outside the directory it
# was given, and --github-owner must not be able to leave .github/CODEOWNERS
# empty for ever. This file is the e2e oracle for both defects.
#
# WHAT F1 IS. Every destination writer in install.sh decided whether to write by
# testing the destination for EXISTENCE, and -e FOLLOWS symlinks. A DANGLING
# link planted at a destination answers false, so the writer takes the "nothing
# there yet" branch and cp/> write THROUGH the link. MEASURED against the
# pre-cure installer (S329): with docs/rotation-log.md a dangling symlink to a
# path outside the target, the run exited 0, logged "COPIED:", and 536 bytes
# landed at the external path. A RESOLVED link and a symlinked ANCESTOR escape
# the same way; a HARD LINK escapes while every path check passes, because a
# second name for one inode is not a link any path walk encounters.
#
# WHAT F2 IS. --github-owner was interpolated raw into a sed s-command. A value
# containing "/" ends the command early: sed exits "bad flag in substitute
# command" AFTER > has already truncated the destination, so .github/CODEOWNERS
# survives at 0 bytes — EXISTS-skipped for ever, outside the rollback snapshot,
# and read by GitHub as "no owners". MEASURED pre-cure (S329): rc=1, 0 bytes.
#
# ASSERT ON BYTES, NEVER ON THE EXIT CODE ALONE (plan AC-1). The pre-cure defect
# exits 0 while writing outside the target, so an exit-code assertion would have
# passed against it. Every F1 leg below asserts on the EXTERNAL path.
#
# ---------------------------------------------------------------------------
# POSITIVE CONTROL — how to prove these assertions can fail.
#
# This file tests the framework tree it lives in. To run it against a DIFFERENT
# tree (an unpatched one), pass that tree as $1; the banner prints which root is
# under test, so a control run is never mistaken for a normal one:
#
#   cp -R <unpatched-checkout> /tmp/ctrl          # never the live repo in place
#   cp scripts/tests/test-installer-write-safety-e2e.sh /tmp/ctrl/scripts/tests/
#   bash /tmp/ctrl/scripts/tests/test-installer-write-safety-e2e.sh /tmp/ctrl
#
# Against the pre-cure tree the F1 and F2 legs MUST go red. A green control run
# means this file is asserting something other than the defect.
# ---------------------------------------------------------------------------
#
# bash 3.2-safe (macOS). mktemp -d only, so parallel runs never collide.
# A full install is ~25s; the legs that abort at flag-parse cost nothing.
#
# Run:  bash scripts/tests/test-installer-write-safety-e2e.sh ; echo rc=$?
set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FRAMEWORK_ROOT="${1:-$( cd "$SCRIPT_DIR/../.." && pwd )}"
INSTALLER="$FRAMEWORK_ROOT/scripts/install.sh"
LIB="$FRAMEWORK_ROOT/scripts/_framework_manifest_set.sh"
CODEOWNERS_SRC="$FRAMEWORK_ROOT/templates/.github/CODEOWNERS.template"

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-wsafe-XXXXXX )"
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

echo "=== PLAN-185 W1+W2 installer write-safety e2e ==="
echo "    framework root under test : $FRAMEWORK_ROOT"
echo "    installer                 : $INSTALLER"
echo "    workroot                  : $WORKROOT"
echo ""

[ -f "$INSTALLER" ] || { echo "::error::no installer at $INSTALLER" >&2; exit 2; }
[ -f "$CODEOWNERS_SRC" ] || { echo "::error::no CODEOWNERS template at $CODEOWNERS_SRC" >&2; exit 2; }

# A fresh case directory: $1 becomes CASE, CASE/target and CASE/outside exist.
# "outside" is the tree the installer must never reach.
_mkcase() {
  CASE="$WORKROOT/$1"
  TARGET="$CASE/target"
  OUTSIDE="$CASE/outside"
  LOG="$CASE/install.log"
  mkdir -p "$TARGET" "$OUTSIDE"
}

# One real install. rc lands in RC; output in $LOG. Never `local` (called at
# top level), never piped (a pipe would make $? the tail's, not the install's).
# CEO_RAG_INSTALL_PROMPT=0: the installer's RAG-sidecar block runs only under a
# TTY (`[[ -t 0 ]]`, install.sh) and, when it runs, invokes
# detect-repo-profile.py, which stamps `detected_at`/`created_at` with the wall
# clock into .claude/repo-profile.yaml. Under the Owner's terminal (the real
# LAND) that made F1.8's two clean installs differ by a timestamp; in CI and in
# background runs the block never ran, so the leg was green there and red only
# in the ceremony. Same kill-switch scripts/tests/smoke-install.sh uses — this
# test is about write confinement, not about the interactive sidecar prompt.
_install() {
  CEO_RAG_INSTALL_PROMPT=0 \
    bash "$INSTALLER" "$TARGET" --profile core --ceremony maintainer "$@" >"$LOG" 2>&1
  RC=$?
}

# Octal mode of a path, GNU-first with the output VALIDATED: on GNU `stat -f`
# SUCCEEDS printing FILESYSTEM information instead of failing, so an
# unvalidated chain silently returns a filesystem field where a mode belongs.
_mode_of() {
  _mo="$( stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1" 2>/dev/null || true )"
  case "$_mo" in ''|*[!0-7]*) printf '' ;; *) printf '%s' "$_mo" ;; esac
}

# The whole point of every F1 leg: NOTHING was written at the external path.
# Checked with -e AND -L, so a path that exists only as a broken link still
# counts as absent, and the byte count is reported when it is not.
_assert_external_untouched() {
  _aeu_path="$1"; _aeu_label="$2"
  if [ -e "$_aeu_path" ] || [ -L "$_aeu_path" ]; then
    if [ -f "$_aeu_path" ]; then
      bad "$_aeu_label — $(wc -c < "$_aeu_path" | tr -d ' ') bytes were written OUTSIDE the target at $_aeu_path"
    else
      bad "$_aeu_label — something was created OUTSIDE the target at $_aeu_path"
    fi
  else
    ok "$_aeu_label — external path does not exist (zero bytes written outside the target)"
  fi
}

_assert_named_refusal() {
  if grep -q "REFUSED (nothing written)" "$LOG" 2>/dev/null; then
    ok "$1 — refusal is NAMED in the run output"
  else
    bad "$1 — no named refusal in $LOG (a silent skip is fail-open on delivery)"
  fi
}

# ---------------------------------------------------------------------------
# F0 — the PREDICATE itself, one leg per refused FORM, each with a POSITIVE
# CONTROL that removes exactly that clause from a COPY of the library and
# asserts the refusal disappears. A guard whose clause can be deleted with the
# fixture still green is a guard that is not the thing doing the work.
#
# The mutation is mechanical (one line, by exact text) rather than a rewrite, so
# what is being proven is that THIS line is what produces THIS refusal. If an
# anchor ever stops matching, the leg reports it instead of passing quietly.
# ---------------------------------------------------------------------------
echo "==> F0 the destination predicate, per form, with clause-removal controls"

PRED_ROOT="$WORKROOT/pred/root"
PRED_OUT="$WORKROOT/pred/outside"
mkdir -p "$PRED_ROOT/docs" "$PRED_OUT"

# Prints the refusal reason and exits 0 when the predicate REFUSES; exits 1 when
# it considers the destination confined.
# $1 = library to source, $2 = target root, $3 = destination relpath
_pred_refuses() {
  (
    # shellcheck disable=SC1090
    . "$1" >/dev/null 2>&1
    if _wbm_dst_refuses "$2" "$3"; then
      printf '%s' "${_WBM_DST_REFUSE_WHY:-}"
      exit 0
    fi
    exit 1
  )
}

# Writes a mutated copy of the library with ONE exact line replaced, or reports
# that the anchor is gone. $1 = tag, $2 = anchor (exact), $3 = replacement.
# The result lands in the GLOBAL _MUT_OUT rather than on stdout: called through a
# command substitution, its bad() would increment FAIL inside a subshell and the
# failure would vanish from the count — a test harness losing its own failures is
# the same fail-open class this file exists to catch.
_MUT_OUT=""
_mutate_lib() {
  _MUT_OUT=""
  if ! grep -qF "$2" "$LIB"; then
    bad "F0 control ($1) — the anchor line is GONE from the library; the control cannot run: $2"
    return 1
  fi
  _ml_out="$WORKROOT/lib-$1.sh"
  awk -v anchor="$2" -v repl="$3" \
      '{ if (index($0, anchor)) { print repl } else { print } }' "$LIB" > "$_ml_out"
  # The mutation must actually have changed something, and the result must still
  # be a loadable shell file — otherwise "no longer refuses" would be explained
  # by a syntax error rather than by the missing clause.
  if cmp -s "$_ml_out" "$LIB"; then
    bad "F0 control ($1) — the mutated library is identical to the original"
    return 1
  fi
  if ! bash -n "$_ml_out" 2>/dev/null; then
    bad "F0 control ($1) — the mutated library does not parse; the control would be vacuous"
    return 1
  fi
  _MUT_OUT="$_ml_out"
  return 0
}

# One form: assert the predicate refuses and the reason NAMES the form, then
# assert the mutated library stops refusing.
# $1 label  $2 relpath  $3 expected substring in the reason
# $4 anchor  $5 replacement
_form_leg() {
  _fl_reason="$( _pred_refuses "$LIB" "$PRED_ROOT" "$2" )"
  if [ $? -ne 0 ]; then
    bad "F0 $1 — the predicate did NOT refuse '$2'"
    return
  fi
  case "$_fl_reason" in
    *"$3"*) ok "F0 $1 — refused, and the reason names the form ($3)" ;;
    *)      bad "F0 $1 — refused but the reason does not name '$3': $_fl_reason" ;;
  esac
  _mutate_lib "$1" "$4" "$5" || return
  # The control asserts on the REASON, not merely on "does it still refuse".
  # The walls are deliberately layered: `../escape.md` is caught by the lexical
  # clause AND, independently, by physical containment — so demanding that the
  # mutated predicate accept the path would assert that the guard has no depth,
  # which is the opposite of what is wanted. What must hold is narrower and
  # truer: THIS clause is what produces THIS reason.
  _fl_mut_reason="$( _pred_refuses "$_MUT_OUT" "$PRED_ROOT" "$2" )" || _fl_mut_reason=""
  case "$_fl_mut_reason" in
    *"$3"*)
      bad "F0 $1 CONTROL — the reason SURVIVED removing its own clause; the clause is not what refuses"
      ;;
    "")
      ok "F0 $1 CONTROL — removing the clause removes the refusal entirely (load-bearing)"
      ;;
    *)
      ok "F0 $1 CONTROL — removing the clause removes THIS reason; a deeper wall still refuses (layered, load-bearing)"
      ;;
  esac
}

# The predicate must EXIST before anything below means anything. Without this
# leg, a library that never defines it makes every "not refused" answer look
# like an acceptance — the guard reading green because the guard is absent.
# shellcheck disable=SC1090  # $LIB is the tree under test, variable by design
_lib_defines() { ( . "$LIB" >/dev/null 2>&1; command -v "$1" >/dev/null 2>&1 ); }
if _lib_defines _wbm_dst_refuses; then
  ok "F0 baseline — _wbm_dst_refuses is defined by the library under test"
else
  bad "F0 baseline — the library defines NO _wbm_dst_refuses; every leg below is vacuous"
fi

# A confined destination must NOT be refused, or every leg above is vacuous.
if _pred_refuses "$LIB" "$PRED_ROOT" "docs/plain.md" >/dev/null; then
  bad "F0 baseline — a confined destination was refused (the predicate is not usable)"
else
  ok "F0 baseline — a confined destination is accepted"
fi

ln -s "$PRED_OUT/dangling-target.md" "$PRED_ROOT/docs/dangling.md"
_form_leg "dangling-symlink" "docs/dangling.md" "DANGLING symlink" \
  'if [ -L "$_wbm_dr_walk" ]; then' '    if false; then'

printf 'x\n' > "$PRED_OUT/resolved-target.md"
ln -s "$PRED_OUT/resolved-target.md" "$PRED_ROOT/docs/resolved.md"
_form_leg "resolved-symlink" "docs/resolved.md" "is a symlink" \
  'if [ -L "$_wbm_dr_walk" ]; then' '    if false; then'

printf 'y\n' > "$PRED_OUT/linked.md"
if ln "$PRED_OUT/linked.md" "$PRED_ROOT/docs/hardlink.md" 2>/dev/null; then
  _form_leg "hard-link" "docs/hardlink.md" "hard links" \
    'if [ -n "$_wbm_dr_n" ] && [ "$_wbm_dr_n" -gt 1 ] 2>/dev/null; then' \
    '      if false; then'
else
  bad "F0 hard-link — could not build the fixture"
fi

_form_leg "escaping-relpath" "../escape.md" "not a confined relative path" \
  'if ! _wbm_route_relpath_ok "$_wbm_dr_rel"; then' '  if false; then'

# An ABSOLUTE destination and a glob metacharacter travel the same clause; assert
# them on the reason only (the control above already proved the clause).
for pair in "/etc/passwd|absolute" "docs/a*.md|glob"; do
  _p_rel="${pair%%|*}"; _p_tag="${pair##*|}"
  _p_why="$( _pred_refuses "$LIB" "$PRED_ROOT" "$_p_rel" )" \
    && case "$_p_why" in
         *"not a confined relative path"*) ok "F0 $_p_tag — refused by the lexical wall" ;;
         *) bad "F0 $_p_tag — refused for the wrong reason: $_p_why" ;;
       esac \
    || bad "F0 $_p_tag — NOT refused ('$_p_rel')"
done

# A symlinked ANCESTOR: the leaf does not exist at all, which is exactly the
# case a leaf-only check answers "nothing there yet" to.
mkdir -p "$PRED_OUT/ancestor-real"
ln -s "$PRED_OUT/ancestor-real" "$PRED_ROOT/linkdir"
_p_why="$( _pred_refuses "$LIB" "$PRED_ROOT" "linkdir/child.md" )" \
  && case "$_p_why" in
       *symlink*) ok "F0 symlinked-ancestor — refused, naming the component" ;;
       *) bad "F0 symlinked-ancestor — refused for the wrong reason: $_p_why" ;;
     esac \
  || bad "F0 symlinked-ancestor — NOT refused"

# ---------------------------------------------------------------------------
# F1.1 — DANGLING symlink at a docs destination, pointing outside the target.
# The exact reproduction the plan records, and the one that exits 0 pre-cure.
# ---------------------------------------------------------------------------
echo "==> F1.1 dangling symlink destination -> outside the target"
_mkcase f1-dangling
mkdir -p "$TARGET/docs"
ln -s "$OUTSIDE/pwned.md" "$TARGET/docs/rotation-log.md"
_install
_assert_external_untouched "$OUTSIDE/pwned.md" "F1.1"
_assert_named_refusal "F1.1"
[ "$RC" -ne 0 ] && ok "F1.1 — the run fails (rc=$RC), so the refusal is not swallowed" \
                || bad "F1.1 — run exited 0 with a refused destination"

# ---------------------------------------------------------------------------
# F1.2 — RESOLVED symlink. -e answers TRUE here, so the pre-cure code took the
# EXISTS branch and skipped; the escape is that any writer reaching it follows
# the link. Asserted on the external file's BYTES, which must not change.
# ---------------------------------------------------------------------------
echo "==> F1.2 resolved symlink destination -> outside the target"
_mkcase f1-resolved
mkdir -p "$TARGET/docs"
printf 'ADOPTER CONTENT, MUST NOT CHANGE\n' > "$OUTSIDE/existing.md"
BEFORE_SUM="$( shasum -a 256 < "$OUTSIDE/existing.md" | awk '{print $1}' )"
ln -s "$OUTSIDE/existing.md" "$TARGET/docs/rotation-log.md"
_install
AFTER_SUM="$( shasum -a 256 < "$OUTSIDE/existing.md" | awk '{print $1}' )"
[ "$BEFORE_SUM" = "$AFTER_SUM" ] \
  && ok "F1.2 — the external file is byte-identical after the run" \
  || bad "F1.2 — the external file CHANGED through the symlink ($BEFORE_SUM -> $AFTER_SUM)"
_assert_named_refusal "F1.2"

# ---------------------------------------------------------------------------
# F1.3 — symlinked ANCESTOR. The leaf is innocent; the parent is the escape.
# ---------------------------------------------------------------------------
echo "==> F1.3 symlinked parent directory -> outside the target"
_mkcase f1-parent
mkdir -p "$OUTSIDE/docs-real"
ln -s "$OUTSIDE/docs-real" "$TARGET/docs"
_install
_assert_external_untouched "$OUTSIDE/docs-real/BRANCH-PROTECTION.md" "F1.3"
_assert_external_untouched "$OUTSIDE/docs-real/rotation-log.md" "F1.3 (second destination)"
_assert_named_refusal "F1.3"

# ---------------------------------------------------------------------------
# F1.4 — HARD LINK. No path check can see this: a second name for one inode is
# not a link any walk encounters. Writing the destination rewrites the external
# file in place, so the assertion is on that file's BYTES.
# ---------------------------------------------------------------------------
echo "==> F1.4 hard-linked destination sharing an inode with an external file"
_mkcase f1-hardlink
mkdir -p "$TARGET/docs"
printf 'ADOPTER CONTENT BEHIND A SECOND NAME\n' > "$OUTSIDE/shared.md"
if ln "$OUTSIDE/shared.md" "$TARGET/docs/rotation-log.md" 2>/dev/null; then
  BEFORE_SUM="$( shasum -a 256 < "$OUTSIDE/shared.md" | awk '{print $1}' )"
  _install
  AFTER_SUM="$( shasum -a 256 < "$OUTSIDE/shared.md" | awk '{print $1}' )"
  [ "$BEFORE_SUM" = "$AFTER_SUM" ] \
    && ok "F1.4 — the hard-linked external file is byte-identical after the run" \
    || bad "F1.4 — the hard-linked external file CHANGED ($BEFORE_SUM -> $AFTER_SUM)"
  _assert_named_refusal "F1.4"
else
  bad "F1.4 — could not create the hard-link fixture (filesystem refused ln)"
fi

# ---------------------------------------------------------------------------
# F1.5 — PRE-FLIGHT. The refusal is on the SECOND destination of the docs
# group; the FIRST must not have been written. docs/ is outside the rollback
# snapshot ($TARGET/.claude only), so a mid-group abort would be permanent —
# this is the assertion that the group is answered before its first write.
# ---------------------------------------------------------------------------
echo "==> F1.5 pre-flight: a refusal on the SECOND destination leaves the FIRST unwritten"
_mkcase f1-preflight
mkdir -p "$TARGET/docs"
ln -s "$OUTSIDE/pwned.md" "$TARGET/docs/rotation-log.md"
_install
if [ -e "$TARGET/docs/BRANCH-PROTECTION.md" ]; then
  bad "F1.5 — the FIRST destination was written before the group was refused (partial, unrecoverable state)"
else
  ok "F1.5 — the FIRST destination was never written (group refused before its first write)"
fi
_assert_external_untouched "$OUTSIDE/pwned.md" "F1.5"

# ---------------------------------------------------------------------------
# F1.9 — GLOBAL pre-flight: NOTHING is written anywhere before the refusal.
#
# Rail round-1 P1. The group pre-flight above is not enough on its own: it runs
# when its group runs, and by then `.claude` has been created and filled.
# MEASURED pre-cure on this exact fixture: zero bytes escaped the target and the
# refusal WAS named — and 563 files were left INSIDE it, PROTOCOL.md and
# .github/ among them, with no manifest and no install-state to record them.
# Rollback cannot reach that: BACKUP_DIR is empty for a fresh target.
#
# So the assertion is the strong one — the target is untouched, `.claude`
# included — because "the refusal was named" was already TRUE while the adopter
# was being handed a half-installed framework.
# ---------------------------------------------------------------------------
echo "==> F1.9 global pre-flight: a refused destination leaves the target ENTIRELY untouched"
_mkcase f1-global
mkdir -p "$TARGET/docs"
ln -s "$OUTSIDE/pwned.md" "$TARGET/docs/rotation-log.md"
_install
[ "$RC" -ne 0 ] && ok "F1.9 — the run fails (rc=$RC)" \
                || bad "F1.9 — the run exited 0 with a refused destination"
F19_FILES="$( find "$TARGET" -type f 2>/dev/null | wc -l | tr -d ' ' )"
[ "$F19_FILES" = "0" ] \
  && ok "F1.9 — ZERO files were written into the target" \
  || bad "F1.9 — $F19_FILES file(s) left inside the target (partial install nothing records)"
[ -e "$TARGET/.claude" ] \
  && bad "F1.9 — .claude was created before the refusal" \
  || ok "F1.9 — .claude was never created (the refusal precedes the first touch)"
for leftover in PROTOCOL.md .github .claude/.install-manifest.sha256 .claude/.install-state.json; do
  [ -e "$TARGET/$leftover" ] \
    && bad "F1.9 — leftover after the refusal: $leftover" \
    || ok "F1.9 — absent after the refusal, as it must be: $leftover"
done
_assert_external_untouched "$OUTSIDE/pwned.md" "F1.9"

# ---------------------------------------------------------------------------
# F1.10 — the FIXED project templates are in the global pre-flight too.
#
# Rail round-2. CLAUDE.md, MEMORY.md and .mcp.json are delivered by the LAST
# writer of the run, long after `.claude/`, `docs/` and `.github/` are
# populated. A pre-flight that lists only the earlier groups lets a dangling
# CLAUDE.md through: pre-cure the whole framework was delivered and 4504 bytes
# were written THROUGH the link; with only a per-writer guard the escape stops
# but a full partial install remains, on a fresh target with nothing to roll
# back to. Both sides now read one shared row list, so a destination cannot be
# in the writers and missing from the pre-flight.
# ---------------------------------------------------------------------------
echo "==> F1.10 a dangling CLAUDE.md is refused BEFORE the framework is delivered"
_mkcase f1-fixed-tmpl
ln -s "$OUTSIDE/claude-escape.md" "$TARGET/CLAUDE.md"
_install
[ "$RC" -ne 0 ] && ok "F1.10 — the run fails (rc=$RC)" \
                || bad "F1.10 — the run exited 0 with a refused destination"
if grep -q "REFUSED (nothing written): CLAUDE.md" "$LOG" 2>/dev/null; then
  ok "F1.10 — the refusal NAMES CLAUDE.md"
else
  bad "F1.10 — CLAUDE.md is not named in the refusal (pre-flight still blind to it)"
fi
F110_FILES="$( find "$TARGET" -type f 2>/dev/null | wc -l | tr -d ' ' )"
[ "$F110_FILES" = "0" ] \
  && ok "F1.10 — ZERO files written into the target" \
  || bad "F1.10 — $F110_FILES file(s) delivered before the late refusal"
for leftover in .claude docs .github; do
  [ -e "$TARGET/$leftover" ] \
    && bad "F1.10 — $leftover/ was populated before the refusal" \
    || ok "F1.10 — $leftover/ was never created"
done
_assert_external_untouched "$OUTSIDE/claude-escape.md" "F1.10"

# ---------------------------------------------------------------------------
# F1.11 — a target ROOT that is itself a symlink.
#
# Rail round-2. The root used to be tested with `! -e` first, so only a DANGLING
# root ever reached the `-L` test: a RESOLVED symlink root answered `-e` true,
# fell through to `cd -P`, and silently moved the confinement BASE to the
# referent. MEASURED pre-cure: the install ran to completion and 567 files
# landed under the referent. Containment held — nothing escaped the referent —
# but the dereference happened on the operator's behalf without being said, and
# `install.sh` resolves the target with plain `cd`/`pwd` (LOGICAL path), so this
# is reachable on every real install.
#
# It is a refusal WITH a recovery: the message prints the referent to re-run
# against, which keeps the gate fail-closed while costing a legitimate symlinked
# project directory one re-run rather than an install it cannot perform.
# ---------------------------------------------------------------------------
echo "==> F1.11 a symlinked target root is refused, naming the referent"
_mkcase f1-root-link
ROOT_REAL="$CASE/real-project"
ROOT_LINK="$CASE/via-link"
mkdir -p "$ROOT_REAL"
ln -s "$ROOT_REAL" "$ROOT_LINK"
bash "$INSTALLER" "$ROOT_LINK" --profile core --ceremony maintainer >"$CASE/rootlink.log" 2>&1
ROOTLINK_RC=$?
[ "$ROOTLINK_RC" -ne 0 ] \
  && ok "F1.11 — the run fails (rc=$ROOTLINK_RC)" \
  || bad "F1.11 — the install proceeded through a symlinked root"
F111_FILES="$( find "$ROOT_REAL" -type f 2>/dev/null | wc -l | tr -d ' ' )"
[ "$F111_FILES" = "0" ] \
  && ok "F1.11 — nothing was written under the referent" \
  || bad "F1.11 — $F111_FILES file(s) written under the referent through the root link"
if grep -q "is a SYMLINK to" "$CASE/rootlink.log" 2>/dev/null; then
  ok "F1.11 — the refusal NAMES the root symlink"
else
  bad "F1.11 — the root symlink is not named in the refusal"
fi
if grep -q "re-run against" "$CASE/rootlink.log" 2>/dev/null; then
  ok "F1.11 — the refusal carries the recovery path (fail-closed WITH a way out)"
else
  bad "F1.11 — the refusal gives the operator no recovery route"
fi

# Control for F1.11: a REAL directory root must still install, and every fixed
# template must arrive. Without this leg the refusal above could be a blanket
# one that breaks ordinary installs and the suite would not notice.
echo "==> F1.11 control: a real directory root installs, fixed templates included"
_mkcase f1-root-real
_install
[ "$RC" -eq 0 ] && ok "F1.11 control — a real directory root installs (rc=0)" \
               || bad "F1.11 control — a real directory root FAILED (rc=$RC)"
if grep -q "REFUSED (nothing written)" "$LOG" 2>/dev/null; then
  bad "F1.11 control — a real directory root produced a refusal (false positive)"
else
  ok "F1.11 control — no refusal on a real directory root"
fi
for rel in CLAUDE.md MEMORY.md .mcp.json \
           .claude/tier-policy.json .claude/tier-policy.json.sigchain; do
  [ -f "$TARGET/$rel" ] && ok "F1.11 control — fixed template delivered: $rel" \
                        || bad "F1.11 control — fixed template MISSING: $rel"
done

# ---------------------------------------------------------------------------
# F1.6 — PROTOCOL.md, a writer in a different group, guarded by the same
# predicate. Its `>` redirection had no symlink check of any kind.
# ---------------------------------------------------------------------------
echo "==> F1.6 dangling PROTOCOL.md pointer -> outside the target"
_mkcase f1-protocol
ln -s "$OUTSIDE/protocol-escape.md" "$TARGET/PROTOCOL.md"
_install
_assert_external_untouched "$OUTSIDE/protocol-escape.md" "F1.6"
_assert_named_refusal "F1.6"

# ---------------------------------------------------------------------------
# F1.7 — .claude/settings.json. Three consumers (SETTINGS_PRE_EXISTING,
# build_settings, apply_deny_baseline) all asked with -e/-f; one shared verdict
# now answers for all three.
# ---------------------------------------------------------------------------
echo "==> F1.7 dangling .claude/settings.json -> outside the target"
_mkcase f1-settings
mkdir -p "$TARGET/.claude"
ln -s "$OUTSIDE/settings-escape.json" "$TARGET/.claude/settings.json"
_install
_assert_external_untouched "$OUTSIDE/settings-escape.json" "F1.7"
_assert_named_refusal "F1.7"

# ---------------------------------------------------------------------------
# F1.8 — NON-REGRESSION. With no symlink anywhere, the install must behave
# exactly as before: rc 0, no refusal, every destination delivered, and two
# runs into different targets byte-identical to each other.
# ---------------------------------------------------------------------------
echo "==> F1.8 non-regression: a clean target installs unchanged"
_mkcase f1-clean
_install
CLEAN_RC="$RC"
[ "$CLEAN_RC" -eq 0 ] && ok "F1.8 — clean install returns 0" \
                      || bad "F1.8 — clean install returned $CLEAN_RC (see $LOG)"
if grep -q "REFUSED (nothing written)" "$LOG" 2>/dev/null; then
  bad "F1.8 — a clean target produced a refusal (false positive in the predicate)"
else
  ok "F1.8 — a clean target produces no refusal"
fi
for rel in docs/BRANCH-PROTECTION.md docs/rotation-log.md PROTOCOL.md \
           .claude/settings.json .github/CODEOWNERS.template; do
  [ -f "$TARGET/$rel" ] && ok "F1.8 — delivered: $rel" \
                        || bad "F1.8 — MISSING after a clean install: $rel"
done
# Determinism, over the SAME target path. It has to be the same path: the
# installer substitutes {{PROJECT_PATH}} and {{PROJECT_NAME}} (the target's
# basename) into CLAUDE.md, PROTOCOL.md, team.md and ~30 SKILL.md files, so two
# installs into DIFFERENTLY-NAMED directories differ by design and comparing
# them would assert the placeholder pass does nothing. Wiping and re-installing
# into the identical path holds the placeholders constant, which leaves the
# staged-write path (portable_sed_inplace, rewritten in this wave to stage on an
# UNPREDICTABLE name) as the thing actually under test.
( cd "$TARGET" && find . -type f -exec shasum -a 256 {} \; 2>/dev/null | sort -k2 ) \
    > "$WORKROOT/sums-a.txt"
rm -rf "$TARGET" && mkdir -p "$TARGET"
_install
if [ "$RC" -eq 0 ]; then
  ( cd "$TARGET" && find . -type f -exec shasum -a 256 {} \; 2>/dev/null | sort -k2 ) \
      > "$WORKROOT/sums-b.txt"
  # .install-state.json stamps written_at/first_recorded_at with wall-clock
  # time, so it cannot be byte-identical across runs by construction. The same
  # holds for .claude/repo-profile.yaml (detected_at/created_at) whenever the
  # TTY-gated sidecar block runs; _install disables that block, and the filter
  # is kept as belt-and-braces so a future TTY-only path cannot turn a clock
  # into a false write-confinement regression.
  grep -v -e '\.install-state\.json$' -e '/\.claude/repo-profile\.yaml$' \
      "$WORKROOT/sums-a.txt" > "$WORKROOT/sums-a.f" 2>/dev/null
  grep -v -e '\.install-state\.json$' -e '/\.claude/repo-profile\.yaml$' \
      "$WORKROOT/sums-b.txt" > "$WORKROOT/sums-b.f" 2>/dev/null
  if diff -q "$WORKROOT/sums-a.f" "$WORKROOT/sums-b.f" >/dev/null 2>&1; then
    ok "F1.8 — re-installing into the same path is byte-identical ($(wc -l < "$WORKROOT/sums-a.f" | tr -d ' ') files)"
  else
    bad "F1.8 — re-install into the same path DIFFERS: $(diff "$WORKROOT/sums-a.f" "$WORKROOT/sums-b.f" | head -5 | tr '\n' ' ')"
  fi
else
  bad "F1.8 — the second clean install returned $RC"
fi

# ---------------------------------------------------------------------------
# F2.1 — the reproduction: a handle containing the sed delimiter. The refusal
# must land BEFORE any mkdir, so no directory and no CODEOWNERS exist at all.
# ---------------------------------------------------------------------------
echo "==> F2.1 --github-owner with a slash is refused before anything is created"
_mkcase f2-slash
_install --github-owner 'acme/platform'
[ "$RC" -ne 0 ] && ok "F2.1 — refused (rc=$RC)" || bad "F2.1 — accepted a handle containing the sed delimiter"
[ -e "$TARGET/.github/CODEOWNERS" ] \
  && bad "F2.1 — .github/CODEOWNERS was created ($(wc -c < "$TARGET/.github/CODEOWNERS" | tr -d ' ') bytes)" \
  || ok "F2.1 — no .github/CODEOWNERS exists"
[ -e "$TARGET/.github" ] \
  && bad "F2.1 — .github/ was created before the value was validated" \
  || ok "F2.1 — the refusal precedes every mkdir (.github/ does not exist)"
if grep -q "must be a GitHub handle" "$LOG" 2>/dev/null; then
  ok "F2.1 — the failure NAMES the grammar"
else
  bad "F2.1 — the failure does not name the grammar (see $LOG)"
fi
if grep -q "TEAM handles" "$LOG" 2>/dev/null; then
  ok "F2.1 — the failure says team handles are unsupported (OQ-2 default)"
else
  bad "F2.1 — the failure does not explain the org/team case"
fi

# ---------------------------------------------------------------------------
# F2.2 — the rest of the rejected forms. Each must fail AND leave no CODEOWNERS.
# The empty-value leg is the one that used to render "@" as the owner.
# ---------------------------------------------------------------------------
echo "==> F2.2 the other out-of-grammar handles"
_f2_reject() {
  _mkcase "f2-rej-$2"
  _install --github-owner "$1"
  if [ "$RC" -ne 0 ] && [ ! -e "$TARGET/.github/CODEOWNERS" ]; then
    ok "F2.2 — refused, nothing written: $2"
  else
    bad "F2.2 — accepted (rc=$RC) or wrote CODEOWNERS: $2"
  fi
}
_f2_reject '-leading-hyphen'                        'leading-hyphen'
_f2_reject 'abcdefghij0123456789abcdefghij0123456789' 'forty-chars'
_f2_reject 'has space'                              'embedded-space'
_f2_reject 'amp&sand'                               'ampersand'
_f2_reject 'back\slash'                             'backslash'

# ---------------------------------------------------------------------------
# F2.3 — a VALID handle, asserted on DERIVED values only. Constants would be
# wrong the next time the template is edited legitimately: 1442 bytes / 33 lines
# is the UNRENDERED size, and the rendered one is 1266 + 11 x len(handle).
# The negative (no markers left) is asserted LAST, because an EMPTY file
# satisfies it — and an empty file is precisely the defect.
# ---------------------------------------------------------------------------
echo "==> F2.3 a valid handle renders, with every expectation derived from the source"
_mkcase f2-valid
HANDLE='acme-platform'
_install --github-owner "$HANDLE"
CO="$TARGET/.github/CODEOWNERS"
if [ "$RC" -eq 0 ] && [ -f "$CO" ]; then
  ok "F2.3 — the install succeeds and .github/CODEOWNERS exists"
  SRC_MARKERS="$( grep -c '{{OWNER_HANDLE}}' "$CODEOWNERS_SRC" 2>/dev/null | tr -d ' ' )"
  SRC_LINES="$(  wc -l < "$CODEOWNERS_SRC" | tr -d ' ' )"
  SRC_BYTES="$(  wc -c < "$CODEOWNERS_SRC" | tr -d ' ' )"
  OUT_LINES="$(  wc -l < "$CO" | tr -d ' ' )"
  OUT_BYTES="$(  wc -c < "$CO" | tr -d ' ' )"
  OUT_HANDLE="$( grep -c "$HANDLE" "$CO" 2>/dev/null | tr -d ' ' )"
  OUT_MARKERS="$( grep -c '{{OWNER_HANDLE}}' "$CO" 2>/dev/null | tr -d ' ' )"
  # marker text is 16 chars; each occurrence becomes len(handle).
  EXPECT_BYTES=$(( SRC_BYTES - SRC_MARKERS * 16 + SRC_MARKERS * ${#HANDLE} ))
  [ "$OUT_BYTES" -gt 0 ] && ok "F2.3 — non-empty ($OUT_BYTES bytes)" \
                         || bad "F2.3 — the rendered file is EMPTY (the defect)"
  [ "$OUT_LINES" = "$SRC_LINES" ] \
    && ok "F2.3 — line count matches the source ($OUT_LINES)" \
    || bad "F2.3 — line count $OUT_LINES != source $SRC_LINES"
  [ "$OUT_HANDLE" = "$SRC_MARKERS" ] \
    && ok "F2.3 — the handle appears once per source marker ($OUT_HANDLE)" \
    || bad "F2.3 — handle occurrences $OUT_HANDLE != source markers $SRC_MARKERS"
  [ "$OUT_BYTES" = "$EXPECT_BYTES" ] \
    && ok "F2.3 — byte count matches the derived render size ($EXPECT_BYTES)" \
    || bad "F2.3 — byte count $OUT_BYTES != derived $EXPECT_BYTES"
  CO_MODE="$( _mode_of "$CO" )"
  [ "$CO_MODE" = "644" ] \
    && ok "F2.3 — mode is 0644 (mktemp creates 0600; an unreadable CODEOWNERS is a regression bytes do not catch)" \
    || bad "F2.3 — mode is ${CO_MODE:-unknown}, expected 644"
  [ "$OUT_MARKERS" = "0" ] \
    && ok "F2.3 — no unrendered markers remain" \
    || bad "F2.3 — $OUT_MARKERS unrendered marker(s) remain"
  # No staging file may survive a successful render.
  LEFTOVER="$( find "$TARGET/.github" -name '.ceo-codeowners.*' 2>/dev/null | head -1 )"
  [ -z "$LEFTOVER" ] && ok "F2.3 — no staging file left behind" \
                     || bad "F2.3 — staging file survived: $LEFTOVER"
else
  bad "F2.3 — install rc=$RC, CODEOWNERS present=$( [ -f "$CO" ] && echo yes || echo no )"
fi
VALID_TARGET="$TARGET"
VALID_SUM="$( [ -f "$CO" ] && shasum -a 256 < "$CO" | awk '{print $1}' || echo none )"

# ---------------------------------------------------------------------------
# F2.4 — idempotence. A second identical run must not change the file.
# ---------------------------------------------------------------------------
echo "==> F2.4 a second identical run leaves CODEOWNERS unchanged"
TARGET="$VALID_TARGET"; LOG="$CASE/install2.log"
_install --github-owner "$HANDLE"
SUM2="$( [ -f "$VALID_TARGET/.github/CODEOWNERS" ] && shasum -a 256 < "$VALID_TARGET/.github/CODEOWNERS" | awk '{print $1}' || echo none )"
[ "$RC" -eq 0 ] && [ "$SUM2" = "$VALID_SUM" ] \
  && ok "F2.4 — second run rc=0 and CODEOWNERS is byte-identical" \
  || bad "F2.4 — second run rc=$RC, sum $VALID_SUM -> $SUM2"

# ---------------------------------------------------------------------------
# F2.5 — 0-byte recovery WITH provenance (OQ-1 default). The framework wrote
# this file, so it may re-render it, and it must say so out loud.
# ---------------------------------------------------------------------------
echo "==> F2.5 a 0-byte CODEOWNERS the framework can PROVE it wrote is recovered"
: > "$VALID_TARGET/.github/CODEOWNERS"
[ ! -s "$VALID_TARGET/.github/CODEOWNERS" ] || bad "F2.5 — fixture setup failed to truncate"
TARGET="$VALID_TARGET"; LOG="$CASE/install3.log"
_install --github-owner "$HANDLE"
if [ -s "$VALID_TARGET/.github/CODEOWNERS" ]; then
  ok "F2.5 — the empty file was re-rendered ($(wc -c < "$VALID_TARGET/.github/CODEOWNERS" | tr -d ' ') bytes)"
else
  bad "F2.5 — the empty file was NOT recovered despite provenance"
fi
if grep -q "RECOVERED:" "$LOG" 2>/dev/null; then
  ok "F2.5 — the recovery is RUIDOSA (RECOVERED: names the evidence)"
else
  bad "F2.5 — the recovery was silent (see $LOG)"
fi

# ---------------------------------------------------------------------------
# F2.6 — 0-byte WITHOUT provenance. Truncating to zero is a real way to switch
# mandatory review routing off without deleting the path; re-rendering it would
# silently re-enable owners in a repository the framework cannot prove it owns
# (the PLAN-183 D4 class). The file must be left EXACTLY as found.
# ---------------------------------------------------------------------------
echo "==> F2.6 a 0-byte CODEOWNERS with NO provenance is left untouched"
_mkcase f2-noprov
mkdir -p "$TARGET/.github"
: > "$TARGET/.github/CODEOWNERS"
_install --github-owner "$HANDLE"
if [ -e "$TARGET/.github/CODEOWNERS" ] && [ ! -s "$TARGET/.github/CODEOWNERS" ]; then
  ok "F2.6 — the adopter's empty file is still empty (nothing was re-enabled)"
else
  bad "F2.6 — the file was rewritten without provenance ($(wc -c < "$TARGET/.github/CODEOWNERS" 2>/dev/null | tr -d ' ') bytes)"
fi
if grep -q "WARNING: .github/CODEOWNERS exists and is EMPTY" "$LOG" 2>/dev/null; then
  ok "F2.6 — a NAMED warning is emitted"
else
  bad "F2.6 — no named warning (silence is the wrong answer either way)"
fi
if grep -q "doctor.sh" "$LOG" 2>/dev/null; then
  ok "F2.6 — the warning points at scripts/doctor.sh, as the plan requires"
else
  bad "F2.6 — the warning does not point at the recovery route"
fi

# ---------------------------------------------------------------------------
# F2.8 — the case a RECORDED OWNER is not evidence for (rail round-1 P1).
#
# An adopter with their own non-empty .github/CODEOWNERS runs the installer with
# --github-owner. The file is SKIPPED (their bytes survive, correctly) but the
# owner is persisted anyway — it records the REQUEST. Later the adopter empties
# that file deliberately, which is how mandatory review routing gets switched
# off without deleting the path. REPRODUCED pre-cure: the next install read the
# persisted owner as proof of authorship and re-rendered 1409 bytes of framework
# template over it, silently re-enabling review routing in a repository the
# framework never wrote to. Only a DELIVERY RECORD may authorize recovery.
# ---------------------------------------------------------------------------
echo "==> F2.8 a recorded owner is NOT a delivery record"
_mkcase f2-owner-not-delivery
mkdir -p "$TARGET/.github"
printf '* @adopter-team\n' > "$TARGET/.github/CODEOWNERS"
ADOPTER_SUM="$( shasum -a 256 < "$TARGET/.github/CODEOWNERS" | awk '{print $1}' )"
_install --github-owner "$HANDLE"
if [ "$( shasum -a 256 < "$TARGET/.github/CODEOWNERS" | awk '{print $1}' )" = "$ADOPTER_SUM" ]; then
  ok "F2.8 — the adopter's own CODEOWNERS was left alone by the install"
else
  bad "F2.8 — the install overwrote an adopter-owned CODEOWNERS"
fi
# The owner IS persisted (it records the request) and the manifest must NOT
# carry a delivery row — that asymmetry is the whole finding.
F28_MANIFEST_ROWS="$( grep -c '  \.github/CODEOWNERS$' "$TARGET/.claude/.install-manifest.sha256" 2>/dev/null | tr -d ' ' )"
[ "${F28_MANIFEST_ROWS:-0}" = "0" ] \
  && ok "F2.8 — no delivery row in the manifest for a file the framework did not write" \
  || bad "F2.8 — the manifest claims a delivery that never happened ($F28_MANIFEST_ROWS row(s))"
# Now the adopter empties it on purpose, and re-installs.
: > "$TARGET/.github/CODEOWNERS"
LOG="$CASE/install2.log"
_install --github-owner "$HANDLE"
if [ -e "$TARGET/.github/CODEOWNERS" ] && [ ! -s "$TARGET/.github/CODEOWNERS" ]; then
  ok "F2.8 — the deliberately emptied file is STILL empty (a request is not provenance)"
else
  bad "F2.8 — recovery fired on a recorded owner alone ($( wc -c < "$TARGET/.github/CODEOWNERS" 2>/dev/null | tr -d ' ' ) bytes) — review routing silently re-enabled"
fi
if grep -q "RECOVERED:" "$LOG" 2>/dev/null; then
  bad "F2.8 — the run claims RECOVERED for a file it never delivered"
else
  ok "F2.8 — no recovery was claimed"
fi

# ---------------------------------------------------------------------------
# F3 — dry-run must not be collateral damage (rail round-1 P2).
#
# Previewing a target that does not exist yet is SUPPORTED. Pre-cure, the
# confinement predicate resolved the root with `cd -P`, which necessarily fails
# for an absent directory, so all 12 checked destinations came back "does not
# resolve" and the preview exited 1 having previewed nothing.
#
# The policy, stated: an ABSENT root is not a refusal. Nothing exists beneath a
# directory that does not exist, so there is no component to follow. A root that
# is a SYMLINK stays a refusal — the link exists, and every write under it
# follows it.
# ---------------------------------------------------------------------------
echo "==> F3 dry-run against an absent target, and the preview that must not lie"
_mkcase f3-dry-absent
ABSENT="$CASE/never-created"
bash "$INSTALLER" "$ABSENT" --profile core --ceremony maintainer --dry-run \
  >"$CASE/dry.log" 2>&1
DRY_RC=$?
[ "$DRY_RC" -eq 0 ] \
  && ok "F3 — dry-run against an absent target returns 0" \
  || bad "F3 — dry-run against an absent target returned $DRY_RC (see $CASE/dry.log)"
[ -e "$ABSENT" ] \
  && bad "F3 — the dry-run CREATED the target" \
  || ok "F3 — the dry-run created nothing"
F3_REFUSALS="$( grep -c 'REFUSED (nothing written)' "$CASE/dry.log" 2>/dev/null | tr -d ' ' )"
[ "${F3_REFUSALS:-0}" = "0" ] \
  && ok "F3 — an absent root produces no refusals" \
  || bad "F3 — $F3_REFUSALS spurious refusal(s) against an absent target"

_mkcase f3-dry-dangling
mkdir -p "$TARGET/docs"
ln -s "$OUTSIDE/preview-lie.md" "$TARGET/docs/rotation-log.md"
bash "$INSTALLER" "$TARGET" --profile core --ceremony maintainer --dry-run \
  >"$LOG" 2>&1
if grep -q "REFUSED (nothing written)" "$LOG" 2>/dev/null; then
  ok "F3 — the preview NAMES the refusal instead of promising 'would COPY'"
else
  bad "F3 — the preview hides the refusal (pre-cure it printed 'would COPY' over a dangling link)"
fi
_assert_external_untouched "$OUTSIDE/preview-lie.md" "F3 (dry-run)"

# ---------------------------------------------------------------------------
# F4.1 — nothing the EXIT trap deletes may be inherited from the environment.
#
# Rail round-4. The trap runs `rm -f` on `_STATE_OPS_FILE` and
# `_ATOMIC_TMP_PENDING`; neither was initialised before the trap was installed
# (`_ATOMIC_TMP_PENDING` was first assigned inside the atomic writer, which
# --dry-run never calls; `_STATE_OPS_FILE` ten lines below the trap). A caller
# exporting either one therefore handed the installer an arbitrary path to
# delete on ANY exit. REPRODUCED: a --dry-run — the mode whose entire promise is
# that no file is modified — exited 0 and the unrelated file was gone.
#
# The assertion is on the victim's BYTES, not on the exit code, for the same
# reason every F1 leg is: the pre-cure run reported success while doing it.
# ---------------------------------------------------------------------------
echo "==> F4.1 an inherited trap variable must not become an arbitrary deletion"
_trap_inherit_leg() {
  _til_var="$1"
  _mkcase "f4-trap-${2}"
  _til_victim="$CASE/precious.txt"
  printf 'ADOPTER DATA THAT MUST SURVIVE\n' > "$_til_victim"
  _til_before="$( shasum -a 256 < "$_til_victim" | awk '{print $1}' )"
  env "$_til_var=$_til_victim" \
      bash "$INSTALLER" "$TARGET" --profile core --ceremony maintainer --dry-run \
      >"$LOG" 2>&1
  if [ ! -e "$_til_victim" ]; then
    bad "F4.1 ($_til_var) — the file was DELETED by the trap under --dry-run"
  elif [ "$( shasum -a 256 < "$_til_victim" | awk '{print $1}' )" = "$_til_before" ]; then
    ok "F4.1 ($_til_var) — the inherited path survives byte-identical"
  else
    bad "F4.1 ($_til_var) — the file was MODIFIED"
  fi
}
_trap_inherit_leg _ATOMIC_TMP_PENDING atomic
_trap_inherit_leg _STATE_OPS_FILE ops

# ---------------------------------------------------------------------------
# F4.2 — the recorded owner is validated BEFORE the lossy transport.
#
# Rail round-4. `upgrade.sh` reads github_owner out of the install-state through
# a command substitution, and that transport is lossy in two specific ways:
# bash cannot hold a NUL in a variable (it is dropped silently) and `$( )`
# strips trailing newlines. So the shell validated a DIFFERENT string than the
# one recorded. MEASURED pre-cure, against the reader extracted from the shipped
# upgrade.sh: "ali<NUL>ce" arrived as "alice" and PASSED the grammar, and so did
# "alice\n\n".
#
# The reader is EXTRACTED from upgrade.sh rather than copied here, so this leg
# measures the shipped code — an embedded copy would only ever agree with
# itself.
# ---------------------------------------------------------------------------
echo "==> F4.2 an owner that cannot survive the transport is refused at the source"
UPGRADE="$FRAMEWORK_ROOT/scripts/upgrade.sh"
if [ ! -f "$UPGRADE" ]; then
  bad "F4.2 — no scripts/upgrade.sh at $UPGRADE"
else
  _mkcase f4-owner-transport
  READER_PY="$CASE/reader.py"
  awk '/_riso_h="\$\( PYTHONNOUSERSITE=1 python3 -I -c /{f=1;next} f&&/^'"'"' "\$_INSTALL_STATE_FILE"/{f=0} f{print}' \
      "$UPGRADE" > "$READER_PY"
  if [ ! -s "$READER_PY" ]; then
    bad "F4.2 — could not extract the reader from upgrade.sh; this leg is dead, not passing"
  else
    ok "F4.2 — extracted the reader from the shipped upgrade.sh ($( wc -l < "$READER_PY" | tr -d ' ' ) lines)"
    _owner_leg() {
      _ol_label="$1"; _ol_pyexpr="$2"; _ol_tag="$3"; _ol_expect="$4"
      _ol_dir="$CASE/$_ol_tag"; mkdir -p "$_ol_dir"
      PYTHONNOUSERSITE=1 python3 -I -c "$_ol_pyexpr" > "$_ol_dir/state.json" 2>/dev/null
      _ol_got="$(
        # shellcheck disable=SC1090
        . "$LIB" >/dev/null 2>&1
        h="$( PYTHONNOUSERSITE=1 python3 -I "$READER_PY" "$_ol_dir/state.json" 2>/dev/null )" \
          || { printf 'refused'; exit 0; }
        if _wbm_github_handle_ok "$h"; then printf 'accepted:%s' "$h"; else printf 'refused'; fi
      )"
      if [ "$_ol_got" = "$_ol_expect" ]; then
        ok "F4.2 — $_ol_label => $_ol_got"
      else
        bad "F4.2 — $_ol_label => $_ol_got (expected $_ol_expect)"
      fi
    }
    _owner_leg "owner carrying a NUL" \
      'import json,sys; sys.stdout.write(json.dumps({"schema_version":1,"request":{"github_owner":"ali\u0000ce"}}))' \
      nul refused
    _owner_leg "owner with two trailing newlines" \
      'import json,sys; sys.stdout.write(json.dumps({"schema_version":1,"request":{"github_owner":"alice\n\n"}}))' \
      nl refused
    _owner_leg "owner with a carriage return" \
      'import json,sys; sys.stdout.write(json.dumps({"schema_version":1,"request":{"github_owner":"alice\r"}}))' \
      cr refused
    # Control: without this the three refusals above are satisfied by a reader
    # that refuses everything, which would silently disable the CODEOWNERS route.
    _owner_leg "a clean handle (control)" \
      'import json,sys; sys.stdout.write(json.dumps({"schema_version":1,"request":{"github_owner":"acme-platform"}}))' \
      ok "accepted:acme-platform"
  fi
fi

# ---------------------------------------------------------------------------
# F2.7 — ONE grammar, two executables. install.sh validates through
# _wbm_github_handle_ok; upgrade.sh's _read_install_state_github_owner reads
# back through the SAME function. A divergence here does not fail loudly: the
# reader exits 3 and the upgrade degrades to an empty handle, flipping the
# CODEOWNERS delivery branch. Compared against the frozen regex the grammar was
# adopted from, so a drift in EITHER direction is named.
# ---------------------------------------------------------------------------
echo "==> F2.7 the shared grammar answers identically to the regex it was adopted from"
if [ ! -f "$LIB" ]; then
  bad "F2.7 — no shared library at $LIB"
elif ! command -v python3 >/dev/null 2>&1; then
  bad "F2.7 — python3 unavailable, cannot compare against the reference regex"
else
  # $LIB is a VARIABLE on purpose: this file tests whichever framework tree it
  # is pointed at, which is what makes the positive control possible.
  # shellcheck disable=SC1090
  _grammar_accepts() { ( . "$LIB" >/dev/null 2>&1; _wbm_github_handle_ok "$1" ); }

  GRAMMAR_MISMATCH=0
  GRAMMAR_CHECKED=0
  for v in 'a' 'A9' 'acme-platform' 'a-b-c' \
           'abcdefghij0123456789abcdefghij012345678' \
           'abcdefghij0123456789abcdefghij0123456789' \
           '' '-lead' 'acme/platform' 'amp&sand' 'back\slash' 'has space' \
           'dot.dot' 'under_score' 'pipe|pipe' 'semi;colon' 'tick`tick' \
           'dollar$sign' 'at@sign' 'tilde~x' 'quote"x' "apos'x"; do
    if _grammar_accepts "$v" 2>/dev/null; then
      SH_ANS=accept; else SH_ANS=reject; fi
    if PYTHONNOUSERSITE=1 python3 -I -c '
import re, sys
sys.exit(0 if re.match(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$", sys.argv[1]) else 1)
' "$v" 2>/dev/null; then PY_ANS=accept; else PY_ANS=reject; fi
    GRAMMAR_CHECKED=$((GRAMMAR_CHECKED+1))
    if [ "$SH_ANS" != "$PY_ANS" ]; then
      GRAMMAR_MISMATCH=$((GRAMMAR_MISMATCH+1))
      bad "F2.7 — grammar DIVERGES on '$v': shell=$SH_ANS regex=$PY_ANS"
    fi
  done
  [ "$GRAMMAR_MISMATCH" -eq 0 ] \
    && ok "F2.7 — shell predicate and reference regex agree on all $GRAMMAR_CHECKED values" \
    || bad "F2.7 — $GRAMMAR_MISMATCH divergence(s) out of $GRAMMAR_CHECKED"
  # A newline cannot travel through argv the same way; assert it separately,
  # because a multi-line value is what would let a handle inject a CODEOWNERS
  # rule of its own.
  if _grammar_accepts "$( printf 'ok\nevil' )" 2>/dev/null; then
    bad "F2.7 — the grammar ACCEPTS an embedded newline"
  else
    ok "F2.7 — the grammar rejects an embedded newline"
  fi
fi

# ---------------------------------------------------------------------------
# D — doctor.sh repair writes are confined (PLAN-185-FOLLOWUP FU-7, S337).
#
# doctor.sh REPAIRS an installed tree from the framework checkout: it copies a
# framework file over a drifted destination, backs the adopter's copy up first,
# and re-creates LINK records. Until FU-7 the destination side of those writes
# was a LOCAL copy of the confinement walk (a second implementation of what
# install.sh/upgrade.sh already consume from the shared library) that never
# asked about HARD LINKS, and the backup path was not asked anything at all.
# Both escapes were MEASURED against the pre-cure doctor.sh — the positive
# control is this same file pointed at a pre-cure tree (see the header):
#   D.1  the delivered file replaced by a HARD LINK to an outside file: doctor
#        classified it DRIFT (adopter-modified), --yes-file confirmed the
#        repair, `cp -p` wrote the destination IN PLACE — and the outside name
#        showed the framework bytes. rc=0, "RESTORED:".
#   D.2  `.claude.bak` a symlink to an outside directory: the pre-restore
#        backup followed it through `mkdir -p` + `cp -p` — the ADOPTER'S bytes
#        landed outside the target, then the file was overwritten.
# Post-cure both are refused BY NAME, nothing lands outside, and the run exits
# 1 (a refusal is an unresolved finding). Same doctrine as F1: assert on the
# EXTERNAL BYTES, never on rc alone — the pre-cure runs exit 0.
# ---------------------------------------------------------------------------
DOCTOR="$FRAMEWORK_ROOT/scripts/doctor.sh"
# A regular manifest record delivered by --profile core on the identity route
# (`.claude/**` falls back to identity), so doctor CAN restore it when nothing
# stands in the way — which is what makes a refusal meaningful (D.0 proves it).
D_REL=".claude/scripts/check-tier-boundaries.py"

# One doctor run against $TARGET. rc in RC, output in $LOG (never piped).
_doctor() {
  bash "$DOCTOR" "$TARGET" "$@" >"$LOG" 2>&1
  RC=$?
}

echo "==> D.0 doctor baseline: a fresh install verifies clean and a plain drift IS repaired"
_mkcase d0-baseline
_install
if [ "$RC" -ne 0 ]; then
  bad "D.0 — install failed (rc=$RC, see $LOG); the D legs cannot run"
elif [ ! -f "$TARGET/$D_REL" ]; then
  bad "D.0 — $D_REL was not delivered; the D legs need a delivered regular-file record"
else
  LOG="$CASE/doctor-clean.log"; _doctor
  [ "$RC" -eq 0 ] \
    && ok "D.0 — doctor reports a fresh install clean (rc=0)" \
    || bad "D.0 — doctor is not clean on a fresh install (rc=$RC, see $LOG)"
  printf '\n# adopter edit\n' >> "$TARGET/$D_REL"
  LOG="$CASE/doctor-repair.log"; _doctor --repair --yes-file "$D_REL"
  grep -q "RESTORED: $D_REL" "$LOG" \
    && ok "D.0 — a plain adopter drift is repaired (RESTORED:) — the refusals below are not vacuous" \
    || bad "D.0 — the plain drift was NOT repaired (see $LOG); every refusal below would be vacuous"
  grep -q "BACKED-UP: $D_REL" "$LOG" \
    && ok "D.0 — the adopter's copy was backed up before the overwrite" \
    || bad "D.0 — no BACKED-UP line for the repaired file"
  [ "$RC" -eq 0 ] \
    && ok "D.0 — the repair run exits 0 (nothing left unresolved)" \
    || bad "D.0 — the repair run exited $RC on a plain drift"
fi

# ---------------------------------------------------------------------------
# D.1 — HARD-LINKED destination. Every path test passes (a second name for one
# inode is not a link any walk encounters), doctor sees a regular file whose
# bytes drifted, and `cp -p` over it writes IN PLACE: the outside name sees the
# framework bytes. Asserted on the outside file's BYTES.
# ---------------------------------------------------------------------------
echo "==> D.1 a hard-linked destination must not be written in place"
_mkcase d1-hardlink
_install
if [ "$RC" -ne 0 ]; then
  bad "D.1 — install failed (rc=$RC, see $LOG)"
else
  printf 'OUTSIDE FILE - MUST KEEP THESE BYTES\n' > "$OUTSIDE/victim.py"
  D1_BEFORE="$( shasum -a 256 < "$OUTSIDE/victim.py" | awk '{print $1}' )"
  rm -f "$TARGET/$D_REL"
  ln "$OUTSIDE/victim.py" "$TARGET/$D_REL"    # a second name for the OUTSIDE inode
  LOG="$CASE/doctor.log"; _doctor --repair --yes-file "$D_REL"
  D1_AFTER="$( shasum -a 256 < "$OUTSIDE/victim.py" | awk '{print $1}' )"
  [ "$D1_BEFORE" = "$D1_AFTER" ] \
    && ok "D.1 — the outside file is byte-identical (nothing written through the hard link)" \
    || bad "D.1 — the outside file CHANGED through the hard link ($D1_BEFORE -> $D1_AFTER)"
  grep -q "RESTORE-BLOCKED (destination refused" "$LOG" \
    && ok "D.1 — the refusal is NAMED in the run output" \
    || bad "D.1 — no named refusal in $LOG (a silent skip is fail-open on repair)"
  grep -q "hard links" "$LOG" \
    && ok "D.1 — the reason names the hard link" \
    || bad "D.1 — the refusal reason does not mention hard links"
  [ "$RC" -ne 0 ] \
    && ok "D.1 — doctor exits non-zero (rc=$RC): the refusal is an unresolved finding" \
    || bad "D.1 — doctor exited 0 with a refused repair"
fi

# ---------------------------------------------------------------------------
# D.2 — symlinked BACKUP directory. `.claude.bak` is not a manifest record, so
# nothing sanitised it: the pre-restore backup's `mkdir -p` + `cp -p` follow the
# link and the ADOPTER'S bytes land outside the target — then the overwrite
# proceeds. Post-cure: BACKUP-BLOCKED, no overwrite without a backup, the
# adopter's edit survives, nothing outside.
# ---------------------------------------------------------------------------
echo "==> D.2 a symlinked .claude.bak must not receive the adopter's backup outside the target"
_mkcase d2-bakjail
_install
if [ "$RC" -ne 0 ]; then
  bad "D.2 — install failed (rc=$RC, see $LOG)"
else
  mkdir -p "$OUTSIDE/bakjail"
  ln -s "$OUTSIDE/bakjail" "$TARGET/.claude.bak"
  printf '\n# adopter edit\n' >> "$TARGET/$D_REL"
  LOG="$CASE/doctor.log"; _doctor --repair --yes-file "$D_REL"
  D2_LEAK="$( find "$OUTSIDE/bakjail" -type f 2>/dev/null | wc -l | tr -d ' ' )"
  [ "${D2_LEAK:-0}" = "0" ] \
    && ok "D.2 — nothing landed outside the target under the symlinked backup dir" \
    || bad "D.2 — $D2_LEAK file(s) landed OUTSIDE the target through the symlinked .claude.bak"
  grep -q "BACKUP-BLOCKED" "$LOG" \
    && ok "D.2 — the backup refusal is NAMED" \
    || bad "D.2 — no BACKUP-BLOCKED line in $LOG"
  if grep -q "RESTORED: $D_REL" "$LOG"; then
    bad "D.2 — the file was overwritten WITHOUT a backup"
  else
    ok "D.2 — no overwrite without a backup"
  fi
  grep -q "adopter edit" "$TARGET/$D_REL" \
    && ok "D.2 — the adopter's edit survives" \
    || bad "D.2 — the adopter's edit is gone"
  [ "$RC" -ne 0 ] \
    && ok "D.2 — doctor exits non-zero (rc=$RC)" \
    || bad "D.2 — doctor exited 0 with a refused backup"
  # --dry-run with the same plant: previews, writes nothing anywhere.
  LOG="$CASE/doctor-dry.log"; _doctor --repair --dry-run --yes-file "$D_REL"
  D2_LEAK="$( find "$OUTSIDE/bakjail" -type f 2>/dev/null | wc -l | tr -d ' ' )"
  [ "${D2_LEAK:-0}" = "0" ] \
    && ok "D.2 — --dry-run writes nothing outside either" \
    || bad "D.2 — --dry-run wrote $D2_LEAK file(s) outside the target"
fi

# ---------------------------------------------------------------------------
# D.3 — DANGLING symlink at a regular-file destination. Doctor's verification
# loop already classifies this as a type-change (regular file recorded,
# non-file found) and never repairs through it; this leg pins that behaviour
# so the class stays covered from BOTH sides (loop verdict + write predicate).
# ---------------------------------------------------------------------------
echo "==> D.3 a dangling symlink at a delivered file is never written through"
_mkcase d3-dangling
_install
if [ "$RC" -ne 0 ]; then
  bad "D.3 — install failed (rc=$RC, see $LOG)"
else
  rm -f "$TARGET/$D_REL"
  ln -s "$OUTSIDE/pwned.py" "$TARGET/$D_REL"
  LOG="$CASE/doctor.log"; _doctor --repair --yes-file "$D_REL"
  _assert_external_untouched "$OUTSIDE/pwned.py" "D.3"
  grep -qE "type-change|destination refused" "$LOG" \
    && ok "D.3 — the dangling destination is NAMED (type-change / refused), not repaired" \
    || bad "D.3 — nothing in $LOG names the dangling destination"
  [ "$RC" -ne 0 ] \
    && ok "D.3 — doctor exits non-zero (rc=$RC)" \
    || bad "D.3 — doctor exited 0 over a dangling destination"
fi

# ---------------------------------------------------------------------------
# D.4 — root-level LINK repair through a SYMLINKED target root (rail r1 S337,
# P1). doctor resolves $TARGET logically (`cd && pwd`), and the shared
# predicate refuses a symlinked root for every regular-file write — but a
# root-level LINK record whose parent IS the root took an early return that
# skipped the clause, so `rm -f` + `ln -s` followed the root symlink into the
# referent. Post-cure the refusal names the root and nothing is rewritten.
# ---------------------------------------------------------------------------
echo "==> D.4 a LINK repair through a symlinked target root is refused"
_mkcase d4-rootlink
D4_REAL="$CASE/real"; D4_VIA="$CASE/via"
D4_REL=".claude/hooks/SessionStart.py"   # a real LINK record on a --link install
mkdir -p "$D4_REAL"
ln -s "$D4_REAL" "$D4_VIA"
LOG="$CASE/install.log"
CEO_RAG_INSTALL_PROMPT=0 bash "$INSTALLER" "$D4_REAL" --profile core --ceremony maintainer --link >"$LOG" 2>&1
RC=$?
if [ "$RC" -ne 0 ]; then
  bad "D.4 — --link install failed (rc=$RC, see $LOG)"
elif ! grep -q "^LINK  $D4_REL  " "$D4_REAL/.claude/.install-manifest.sha256" 2>/dev/null; then
  # NOTE (measured, S337): root-level files like VERSION are symlinks on disk
  # but NOT manifest records on a --link install ("seeded outside the walk"),
  # so the leg pins a NESTED record — the root-symlink clause fires for every
  # LINK record when the target ROOT is the symlink, nesting included.
  bad "D.4 — $D4_REL is not a LINK record on this --link install; the leg cannot run"
else
  rm -f "$D4_REAL/$D4_REL"
  ln -s "$OUTSIDE/nowhere" "$D4_REAL/$D4_REL"     # a drifted link record
  TARGET="$D4_VIA"; LOG="$CASE/doctor.log"; _doctor --repair --yes-file "$D4_REL"
  D4_READ="$( readlink "$D4_REAL/$D4_REL" 2>/dev/null || true )"
  [ "$D4_READ" = "$OUTSIDE/nowhere" ] \
    && ok "D.4 — the link under the referent was NOT rewritten through the symlinked root" \
    || bad "D.4 — doctor re-linked through the symlinked target root (now -> $D4_READ)"
  grep -q "target root .* is a SYMLINK" "$LOG" \
    && ok "D.4 — the refusal names the symlinked root" \
    || bad "D.4 — no symlinked-root refusal in $LOG"
  [ "$RC" -ne 0 ] \
    && ok "D.4 — doctor exits non-zero (rc=$RC)" \
    || bad "D.4 — doctor exited 0 after writing through the root symlink"
fi

# ---------------------------------------------------------------------------
# U — uninstall.sh confinement (PLAN-183 §9.8 + rail r1 S337). The install
# manifest is a FILE in the target and it is NOT integrity-checked before the
# walk; W5 made it name deliveries OUTSIDE .claude/, which widened what the one
# DESTRUCTIVE consumer of that file can reach. Measured pre-cure:
#   U.1  docs/ replaced by a symlink to an outside directory: the walk removed
#        the outside file (sha matched — `rm -f` follows the ancestor) and the
#        pre-uninstall backup archived bytes read through the link;
#   U.2  a record `<sha>  ../outside/victim.txt` was REMOVED outside the target;
#   U.3  --restore ran `tar xzf` over whatever existed at the archived paths;
#   U.4  (rail r5 S337, P2) --force with a refused record skipped the
#        "incomplete" branch — its `&& FORCE -eq 0` guard negated the refusal
#        too — and printed the "everything matched" summary: a complete-looking
#        report carrying `Refused: 1` and `Manifest: KEPT` in its own body.
# Post-cure: refused BY NAME, nothing outside touched, restore never clobbers,
# and --force never reports a run that refused a record as complete.
# ---------------------------------------------------------------------------
UNINSTALLER="$FRAMEWORK_ROOT/scripts/uninstall.sh"
_uninstall() {
  bash "$UNINSTALLER" "$TARGET" "$@" >"$LOG" 2>&1
  RC=$?
}

echo "==> U.1 a symlinked ancestor must not let uninstall delete (or archive) outside the target"
_mkcase u1-ancestor
_install
if [ "$RC" -ne 0 ]; then
  bad "U.1 — install failed (rc=$RC, see $LOG)"
elif [ ! -f "$TARGET/docs/BRANCH-PROTECTION.md" ]; then
  bad "U.1 — docs/BRANCH-PROTECTION.md was not delivered; the leg cannot run"
else
  mv "$TARGET/docs" "$OUTSIDE/docs-jail"
  ln -s "$OUTSIDE/docs-jail" "$TARGET/docs"
  LOG="$CASE/uninstall.log"; _uninstall
  [ -f "$OUTSIDE/docs-jail/BRANCH-PROTECTION.md" ] \
    && ok "U.1 — the outside file survived (uninstall did not follow the symlinked ancestor)" \
    || bad "U.1 — uninstall DELETED a file outside the target through the symlinked docs/"
  grep -q "symlinked ancestor" "$LOG" \
    && ok "U.1 — the refusal is NAMED" \
    || bad "U.1 — no named refusal in $LOG"
  U1_BK="$( ls "$TARGET"/.claude.backup-uninstall-*.tar.gz 2>/dev/null | head -n 1 || true )"
  if [ -n "$U1_BK" ]; then
    tar tzf "$U1_BK" > "$CASE/backup.list" 2>/dev/null || true
    if grep -qE '^(\./)?docs/' "$CASE/backup.list"; then
      bad "U.1 — the backup archived bytes read THROUGH the symlinked docs/"
    else
      ok "U.1 — the backup carries nothing from behind the symlinked ancestor"
    fi
  else
    bad "U.1 — no backup tarball written"
  fi
fi

echo "==> U.2 a manifest record that escapes the target is refused, not removed"
_mkcase u2-traversal
_install
if [ "$RC" -ne 0 ]; then
  bad "U.2 — install failed (rc=$RC, see $LOG)"
else
  printf 'ADOPTER FILE OUTSIDE THE TARGET\n' > "$OUTSIDE/victim.txt"
  U2_SHA="$( shasum -a 256 < "$OUTSIDE/victim.txt" | awk '{print $1}' )"
  printf '%s  ../outside/victim.txt\n' "$U2_SHA" >> "$TARGET/.claude/.install-manifest.sha256"
  LOG="$CASE/uninstall.log"; _uninstall
  [ -f "$OUTSIDE/victim.txt" ] \
    && ok "U.2 — the outside file survived a crafted ../ manifest record" \
    || bad "U.2 — uninstall DELETED a file outside the target via a ../ record"
  grep -q "unsafe manifest path" "$LOG" \
    && ok "U.2 — the refusal is NAMED" \
    || bad "U.2 — no named refusal for the ../ record in $LOG"
  [ -d "$OUTSIDE" ] \
    && ok "U.2 — the outside directory still exists (the sweep never left the target)" \
    || bad "U.2 — the sweep removed the outside directory"
fi

echo "==> U.3 --restore never overwrites a file that exists at a non-.claude path"
_mkcase u3-restore
_install
if [ "$RC" -ne 0 ]; then
  bad "U.3 — install failed (rc=$RC, see $LOG)"
else
  LOG="$CASE/uninstall.log"; _uninstall
  U3_BK="$( ls "$TARGET"/.claude.backup-uninstall-*.tar.gz 2>/dev/null | head -n 1 || true )"
  if [ -z "$U3_BK" ]; then
    bad "U.3 — no backup tarball written by the uninstall"
  else
    if [ -e "$TARGET/docs/BRANCH-PROTECTION.md" ]; then
      bad "U.3 — precondition: the docs delivery is still present after uninstall"
    else
      ok "U.3 — precondition: the docs delivery was removed"
    fi
    mkdir -p "$TARGET/docs"
    printf 'MINE - written after the uninstall\n' > "$TARGET/docs/BRANCH-PROTECTION.md"
    U3_BEFORE="$( shasum -a 256 < "$TARGET/docs/BRANCH-PROTECTION.md" | awk '{print $1}' )"
    LOG="$CASE/restore.log"
    bash "$UNINSTALLER" "$TARGET" --restore "$U3_BK" >"$LOG" 2>&1
    RC=$?
    U3_AFTER="$( shasum -a 256 < "$TARGET/docs/BRANCH-PROTECTION.md" 2>/dev/null | awk '{print $1}' )"
    [ "$U3_BEFORE" = "$U3_AFTER" ] \
      && ok "U.3 — the adopter's file is byte-identical after --restore" \
      || bad "U.3 — --restore OVERWROTE the adopter's file"
    grep -q "PRESERVED (exists" "$LOG" \
      && ok "U.3 — the preservation is NAMED" \
      || bad "U.3 — no PRESERVED line in $LOG"
    [ -f "$TARGET/docs/rotation-log.md" ] \
      && ok "U.3 — the other docs delivery WAS restored" \
      || bad "U.3 — docs/rotation-log.md was not restored"
    [ -f "$TARGET/.claude/settings.json" ] \
      && ok "U.3 — .claude/ was restored" \
      || bad "U.3 — .claude/settings.json is missing after restore"
    [ "$RC" -eq 0 ] \
      && ok "U.3 — restore exits 0" \
      || bad "U.3 — restore exited $RC (see $LOG)"
  fi
fi

echo "==> U.4 --force never reports a run that refused a record as complete"
_mkcase u4-force-refused
_install
if [ "$RC" -ne 0 ]; then
  bad "U.4 — install failed (rc=$RC, see $LOG)"
else
  # A fresh install: every recorded sha matches, so mismatch_count is 0 and the
  # ONLY thing --force meets is the refused record — the exact cell the guard
  # got wrong. Exit code and manifest do NOT discriminate the two exit paths
  # (both exit 0; the manifest block already kept the ledger on a refusal), the
  # summary header does: pre-cure this run printed "==> Uninstall summary:".
  printf 'ADOPTER FILE OUTSIDE THE TARGET\n' > "$OUTSIDE/victim.txt"
  U4_SHA="$( shasum -a 256 < "$OUTSIDE/victim.txt" | awk '{print $1}' )"
  printf '%s  ../outside/victim.txt\n' "$U4_SHA" >> "$TARGET/.claude/.install-manifest.sha256"
  LOG="$CASE/uninstall.log"; _uninstall --force
  [ -f "$OUTSIDE/victim.txt" ] \
    && ok "U.4 — the outside file survived the ../ record under --force" \
    || bad "U.4 — --force DELETED a file outside the target via a ../ record"
  grep -q "Uninstall summary (incomplete)" "$LOG" \
    && ok "U.4 — the summary is INCOMPLETE (a refused record routes --force to the refused path)" \
    || bad "U.4 — --force with a refused record printed a COMPLETE summary (see $LOG)"
  grep -q "Refused:   1 (unsafe" "$LOG" \
    && ok "U.4 — the refusal is COUNTED in the summary" \
    || bad "U.4 — no 'Refused:   1' line in $LOG"
  [ -f "$TARGET/.claude/.install-manifest.sha256" ] \
    && ok "U.4 — the manifest survived (--force overrides a mismatch, never a refusal)" \
    || bad "U.4 — --force REMOVED the manifest with a refused record still on the ledger"
  grep -q "re-run with --force" "$LOG" \
    && bad "U.4 — the incomplete summary tells a --force run to re-run with --force" \
    || ok "U.4 — no misleading --force hint under --force"
  [ "$RC" -eq 0 ] \
    && ok "U.4 — the refused run under --force exits 0 (the incomplete path's exit code)" \
    || bad "U.4 — the refused run exited $RC (see $LOG)"
fi

# ---------------------------------------------------------------------------
echo ""
echo "=== summary ==="
echo "    framework root : $FRAMEWORK_ROOT"
echo "    passed         : $PASS"
echo "    failed         : $FAIL"
if [ "$FAIL" -ne 0 ]; then
  echo "::error::installer write-safety e2e FAILED ($FAIL assertion(s))" >&2
  exit 1
fi
echo "OK"
exit 0
