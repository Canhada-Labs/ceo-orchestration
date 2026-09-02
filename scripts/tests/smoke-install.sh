#!/usr/bin/env bash
# PLAN-004 Phase 7 — smoke install test (release gate).
#
# Runs install.sh into a scratch directory and asserts invariants that
# a fresh adopter should observe. Exits 0 on success, non-zero on any
# failure. Used by .github/workflows/release.yml on tag push.
#
# Usage:
#   bash scripts/tests/smoke-install.sh            # default scratch dir
#   bash scripts/tests/smoke-install.sh /tmp/x     # explicit target

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

TARGET="${1:-}"
CLEANUP=0
if [[ -z "$TARGET" ]]; then
  TARGET="$(mktemp -d -t ceo-smoke-XXXXXX)"
  CLEANUP=1
fi

echo "==> smoke install into: $TARGET"
mkdir -p "$TARGET"

# Initialize a minimal git repo so CODEOWNERS / hooks have a valid context
if [[ ! -d "$TARGET/.git" ]]; then
  ( cd "$TARGET" && git init -q )
fi

# Run the installer (capture output to a log)
LOG="$TARGET/.smoke-install.log"
if ! bash "$SOURCE_DIR/scripts/install.sh" "$TARGET" --profile core,frontend >"$LOG" 2>&1; then
  echo "::error::install.sh failed (see $LOG)"
  tail -40 "$LOG"
  exit 1
fi
echo "==> install.sh returned 0"

# --- Assertions ---
fail=0

assert_exists() {
  local path="$1"
  if [[ ! -e "$TARGET/$path" ]]; then
    echo "::error::missing: $path"
    fail=1
  fi
}

assert_not_contains() {
  local pattern="$1"
  local scope="$2"
  # Allowlist: files that legitimately mention placeholder syntax in
  # docstrings / help text / error messages targeted at the adopter
  # themselves. These are documentation, not code that the installer
  # is expected to render. Keep this list narrow and commented.
  local allowlist_regex="(admin-invite\.py|check-originator-residue\.py)"
  local matches
  matches=$(grep -rn "$pattern" "$TARGET/$scope" 2>/dev/null || true)
  # Filter out allowlisted files
  local real_matches
  real_matches=$(echo "$matches" | grep -Ev "$allowlist_regex" || true)
  if [[ -n "$real_matches" ]]; then
    echo "::error::unrendered placeholder '$pattern' leaked into $scope"
    echo "$real_matches" | head -5 >&2
    fail=1
  fi
}

# Essential files
assert_exists ".claude/team.md"
assert_exists ".claude/frontend-team.md"
assert_exists ".claude/settings.json"
assert_exists ".claude/skills/core"
assert_exists ".claude/skills/frontend"
assert_exists ".claude/hooks/check_agent_spawn.py"
assert_exists ".claude/hooks/_lib/filelock.py"
assert_exists ".claude/scripts/validate-governance.sh"
assert_exists "CLAUDE.md"

# Tests should NOT be installed into the adopter's tree (Sprint 3 I-4 fix)
if [[ -d "$TARGET/.claude/hooks/tests" ]]; then
  echo "::error::.claude/hooks/tests/ should not be installed in adopter"
  fail=1
fi

# PLAN-120-FOLLOWUP WS-D (E4-F1/E4-F2) — the framework's OWN _lib test
# harness must NOT ship: _lib/tests/ emits real audit events with no
# session redirect, and test_isolation.py/testing.py `import pytest` at
# module top. install.sh::install_lib_selective() excludes them; assert it.
if [[ -d "$TARGET/.claude/hooks/_lib/tests" ]]; then
  echo "::error::.claude/hooks/_lib/tests/ should not be installed in adopter"
  fail=1
fi
for leaked in test_isolation.py testing.py; do
  if [[ -e "$TARGET/.claude/hooks/_lib/$leaked" ]]; then
    echo "::error::.claude/hooks/_lib/$leaked should not be installed in adopter"
    fail=1
  fi
done
# A runtime _lib module MUST still be present (selective copy did not over-prune)
if [[ ! -f "$TARGET/.claude/hooks/_lib/audit_emit.py" ]]; then
  echo "::error::.claude/hooks/_lib/audit_emit.py missing — selective _lib install over-pruned"
  fail=1
fi

# Legacy bash hooks should not leak
if [[ -d "$TARGET/.claude/hooks/legacy" ]]; then
  echo "::error::.claude/hooks/legacy/ should not be installed in adopter"
  fail=1
fi

# settings.json parses as JSON
if ! python3 -c "import json; json.load(open('$TARGET/.claude/settings.json'))" 2>/dev/null; then
  echo "::error::.claude/settings.json is not valid JSON"
  fail=1
fi

# OSS-D5 - real-time context viz (statusLine) regression guard.
# The default (maintainer-ceremony) install must ship statusline-ceo.py AND
# wire it as the settings.json statusLine command, or the live context
# display silently disappears for adopters.
assert_exists ".claude/scripts/statusline-ceo.py"
if ! python3 -c "import json,sys; s=json.load(open('$TARGET/.claude/settings.json')); sl=s.get('statusLine') or {}; sys.exit(0 if 'statusline-ceo.py' in (sl.get('command') or '') else 1)" 2>/dev/null; then
  echo "::error::settings.json does not wire statusLine -> statusline-ceo.py"
  fail=1
fi

# No unrendered placeholders in code paths
assert_not_contains "{{OWNER_NAME}}" ".claude/hooks"
assert_not_contains "{{PROJECT_NAME}}" ".claude/hooks"
assert_not_contains "{{OWNER_NAME}}" ".claude/scripts"

# PLAN-183 W2 (finding A3): the delivered tree must not name a script the
# installer does not deliver. `.github/` reaches the adopter ONLY through
# install_github_templates() (install.sh) — CODEOWNERS + the two workflow
# .template files — and `_framework_target_entries` carries no `.github`
# entry at all, so `.github/scripts/` is never installed. Any surviving
# reference is a call that dies AFTER the adopter has paid for the API run.
#
# A blind substring grep for ".github/scripts/" self-defeats: the A3 cure
# itself explains the absence in-line (e.g. "is NOT installed", "is not
# part of an install"), and that explanatory text also contains the
# substring (measured: a real clean install hits 3 lines that are ALL
# disclaimer prose, zero of which are dangling calls). So a match only
# counts as dangling when the SAME line carries no such disclaimer.
gh_scripts_hits="$(grep -rn '\.github/scripts/' "$TARGET/.github" "$TARGET/docs" 2>/dev/null || true)"
dangling_gh_scripts="$(printf '%s' "$gh_scripts_hits" | grep -viE 'not installed|not part of' || true)"
if [[ -n "$dangling_gh_scripts" ]]; then
  echo "::error::delivered tree references .github/scripts/, which install.sh does not deliver"
  echo "$dangling_gh_scripts" | head -5 >&2
  fail=1
fi

# Hook scripts are executable
for h in check_agent_spawn.py audit_log.py check_bash_safety.py check_plan_edit.py; do
  if [[ ! -x "$TARGET/.claude/hooks/$h" ]]; then
    echo "::error::hook not executable: $h"
    fail=1
  fi
done

# Registry works against the installed tree
if ! python3 "$TARGET/.claude/scripts/registry.py" --validate --repo-root "$TARGET" >/dev/null 2>&1; then
  echo "::error::registry validation failed in installed tree"
  fail=1
fi

# WS4-user-ceremony: a fresh install must pass its OWN bundled validator (E6-F5).
# The CI escape that let the dispatcher gap through was that smoke-install only
# ran registry.py --validate, never validate-governance.sh.
if ! ( cd "$TARGET" && bash .claude/scripts/validate-governance.sh >/dev/null 2>&1 ); then
  echo "::error::validate-governance.sh failed in installed tree (default profile)"
  fail=1
fi

# ---------------------------------------------------------------------------
# PLAN-183 W0-US3 / AC-5 (S334): the delivered CI template ACTIVATES.
# The adopter's documented activation move is a rename of the .template;
# this leg exercises that rename in the disposable target and validates
# the ACTIVATED workflow — with actionlint when available, and with a
# structural stdlib check ALWAYS (so the leg never silently no-ops).
# The step-set contract itself is guarded by
# .claude/scripts/tests/test_validate_template_frozen_subset.py (Ramo B).
# ---------------------------------------------------------------------------
TPL_REL=".github/workflows/validate.yml.template"
ACT_REL=".github/workflows/validate.yml"
if [[ ! -f "$TARGET/$TPL_REL" ]]; then
  echo "::error::CI template not delivered: $TPL_REL"
  fail=1
else
  mv "$TARGET/$TPL_REL" "$TARGET/$ACT_REL"
  if [[ -e "$TARGET/$TPL_REL" || ! -f "$TARGET/$ACT_REL" ]]; then
    echo "::error::activation rename did not take effect"
    fail=1
  fi
  if ! python3 - "$TARGET/$ACT_REL" <<'PYCHK'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
ok = True
for key in ("^name:", "^on:", "^jobs:"):
    if not re.search(key, text, re.M):
        print("activated workflow missing top-level key %r" % key, file=sys.stderr)
        ok = False
steps = re.findall(r"^\s+- name:\s*(.+?)\s*$", text, re.M)
if len(steps) != 11:
    print("activated workflow has %d steps, expected the 11 frozen ones" % len(steps), file=sys.stderr)
    ok = False
sys.exit(0 if ok else 1)
PYCHK
  then
    echo "::error::activated validate.yml failed structural validation"
    fail=1
  fi
  if command -v actionlint >/dev/null 2>&1; then
    if ! actionlint "$TARGET/$ACT_REL"; then
      echo "::error::actionlint rejected the activated validate.yml"
      fail=1
    fi
  else
    echo "note: actionlint not on PATH - structural check only for the activated template"
  fi
  # -------------------------------------------------------------------------
  # PLAN-183 W0-US3 / AC-5 (S337): EXECUTE the activated workflow — the half
  # that was missing. scripts/tests/run-activated-workflow.py runs the
  # workflow's OWN `run:` steps, in order, inside the installed tree, the way
  # the hosted runner does (one `bash -eo pipefail` per step, stop at the first
  # failure; `uses:` steps are runner-provided and skipped BY NAME). Nothing is
  # re-implemented: a step that fails here is a step the adopter's CI would
  # fail on day one. The adopter commits the install before CI ever runs, and
  # the git-ls-files based steps (Contamination check) see NOTHING on an
  # uncommitted tree — so the tree is committed first (install.sh writes no
  # git hooks; the smoke log stays out of the commit).
  # Linux under CI only (rail r1, S337): the template pins a linux_amd64
  # actionlint release asset (its step 10), and its shellcheck step runs
  # `sudo apt-get` when shellcheck is absent — so the delivered steps execute
  # only where they were written to run: a Linux runner with CI=true (what
  # GitHub sets), or an operator who opts in with CEO_SMOKE_EXECUTE_CI=1 (the
  # docker proof recorded in PLAN-183 W0-US3). Everywhere else the steps are
  # LISTED, not run, and the note says so.
  # -------------------------------------------------------------------------
  RUNNER="$SOURCE_DIR/scripts/tests/run-activated-workflow.py"
  if [[ ! -f "$RUNNER" ]]; then
    echo "::error::workflow runner missing: $RUNNER (the AC-5 execution leg cannot run)"
    fail=1
  elif [[ "$(uname -s)" == "Linux" && ( "${CI:-}" == "true" || "${CEO_SMOKE_EXECUTE_CI:-0}" == "1" ) ]]; then
    if ! ( cd "$TARGET" \
           && git add -A -- . ':!.smoke-install.log' >/dev/null 2>&1 \
           && git -c user.name=smoke -c user.email=smoke@example.invalid -c commit.gpgsign=false \
                  commit -q -m "smoke: installed tree (PLAN-183 AC-5)" >/dev/null 2>&1 ); then
      echo "::error::could not commit the installed tree before executing the delivered CI"
      fail=1
    elif ! python3 "$RUNNER" "$TARGET" "$ACT_REL"; then
      echo "::error::the activated validate.yml FAILED when EXECUTED in the installed tree — a step the adopter's CI would run went red (step output above)"
      fail=1
    fi
  else
    echo "note: the delivered CI is EXECUTED only on Linux under CI=true or CEO_SMOKE_EXECUTE_CI=1 (its steps may apt-get/sudo and download a linux_amd64 actionlint asset); listing its steps instead:"
    if ! python3 "$RUNNER" "$TARGET" "$ACT_REL" --list; then
      echo "::error::the activated validate.yml could not be parsed by the workflow runner"
      fail=1
    fi
  fi
  # Restore the delivered state: activation is the ADOPTER's move, and the
  # parity/upgrade legs downstream must see the tree exactly as installed.
  mv "$TARGET/$ACT_REL" "$TARGET/$TPL_REL"
fi

# WS4-user-ceremony: --ceremony user must (a) pass validate-governance.sh and
# (b) write nothing outside .claude/. Fresh install into a second temp dir.
UTARGET="$(mktemp -d 2>/dev/null || mktemp -d -t ceo-smoke-user)"
( cd "$UTARGET" && git init -q )
if ! CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
     bash "$SOURCE_DIR/scripts/install.sh" "$UTARGET" --ceremony user >/dev/null 2>&1; then
  echo "::error::install.sh --ceremony user failed"
  fail=1
fi
if ! ( cd "$UTARGET" && bash .claude/scripts/validate-governance.sh >/dev/null 2>&1 ); then
  echo "::error::validate-governance.sh failed for --ceremony user install"
  fail=1
fi
user_extra="$(ls -A "$UTARGET" | grep -v -E '^[.]claude$|^[.]git$' || true)"
if [[ -n "$user_extra" ]]; then
  echo "::error::--ceremony user wrote outside .claude/: $user_extra"
  fail=1
fi
rm -rf "$UTARGET"

# PLAN-133 G2 — foreign context filenames are DISCOVERY-only, never merged.
# Pre-seed a fresh target with an adopter's AGENTS.md + .cursorrules BEFORE
# install, then assert: (a) the installer leaves them byte-identical (never
# overwrites/merges), (b) the discovery helper surfaces them existence-only,
# (c) settings.json stays valid JSON and carries no foreign-file path (no
# settings merge leaked in). install.sh:~1126 SKIPS an existing settings.json
# — a foreign context file must influence NOTHING mechanical (this is the
# exact hole that made PLAN-128 §7 measure 0/0/0).
GTARGET="$(mktemp -d 2>/dev/null || mktemp -d -t ceo-smoke-g2)"
( cd "$GTARGET" && git init -q )
AGENTS_BODY="# Adopter AGENTS.md — DO NOT TOUCH (G2 discovery-only)"
CURSOR_BODY="adopter cursor rules — leave untouched"
printf '%s\n' "$AGENTS_BODY" > "$GTARGET/AGENTS.md"
printf '%s\n' "$CURSOR_BODY" > "$GTARGET/.cursorrules"
AGENTS_SHA_BEFORE="$(python3 - "$GTARGET/AGENTS.md" <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())
PY
)"
if ! CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
     bash "$SOURCE_DIR/scripts/install.sh" "$GTARGET" --profile core >/dev/null 2>&1; then
  echo "::error::install.sh failed on a target carrying a foreign AGENTS.md"
  fail=1
fi
# (a) foreign files untouched (byte-identical) — discovery NEVER overwrites.
if [[ ! -f "$GTARGET/AGENTS.md" ]]; then
  echo "::error::G2: installer deleted the adopter's AGENTS.md"
  fail=1
else
  AGENTS_SHA_AFTER="$(python3 - "$GTARGET/AGENTS.md" <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())
PY
)"
  if [[ "$AGENTS_SHA_BEFORE" != "$AGENTS_SHA_AFTER" ]]; then
    echo "::error::G2: installer modified the adopter's AGENTS.md (merge leaked)"
    fail=1
  fi
fi
if [[ ! -f "$GTARGET/.cursorrules" ]]; then
  echo "::error::G2: installer removed the adopter's .cursorrules"
  fail=1
fi
# (b) the discovery helper surfaces the foreign files existence-only.
G2_HELPER="$SOURCE_DIR/scripts/discover_foreign_context.py"
if [[ ! -f "$G2_HELPER" ]]; then
  echo "::error::G2: discover_foreign_context.py helper is missing"
  fail=1
else
  G2_OUT="$(python3 "$G2_HELPER" "$GTARGET" 2>/dev/null || true)"
  if ! grep -q "AGENTS.md" <<<"$G2_OUT"; then
    echo "::error::G2: discovery did not report AGENTS.md"
    fail=1
  fi
  if ! grep -qi "not merged" <<<"$G2_OUT"; then
    echo "::error::G2: discovery report omitted the 'not merged' invariant"
    fail=1
  fi
fi
# (c) settings.json stays valid JSON and carries no foreign-file path.
if [[ -f "$GTARGET/.claude/settings.json" ]]; then
  if ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$GTARGET/.claude/settings.json" 2>/dev/null; then
    echo "::error::G2: .claude/settings.json is not valid JSON after foreign-context install"
    fail=1
  fi
  if grep -E -q 'AGENTS\.md|\.cursorrules' "$GTARGET/.claude/settings.json"; then
    echo "::error::G2: foreign context filename leaked into settings.json (merge happened)"
    fail=1
  fi
fi
rm -rf "$GTARGET"

# ---------------------------------------------------------------------------
# PLAN-183 §9.8 (S337): uninstall.sh exercised with the two delivered trees.
# W5 made the install manifest record the docs/ and .github/ deliveries, which
# widened the reach of the ONE destructive consumer of that manifest without
# any check touching it. Three legs, each MEASURED before it was written:
#  (a) install -> uninstall removes the docs/ and .github/ deliveries and
#      touches nothing outside the target (asserted on an outside probe's
#      bytes, never on rc alone);
#  (b) .github/CODEOWNERS: the manifest records the RENDERED bytes (install
#      hashes what it wrote — measured: manifest sha == rendered file sha !=
#      template sha), so a pristine rendered file is removed like any other
#      delivery, while an adopter-EDITED one is PRESERVED, the summary is
#      marked incomplete, the manifest is KEPT for a --force re-run and the
#      exit is 0. The plan's earlier prose ("the rendered file never matches
#      the template sha => PRESERVED") described the pre-W5 generator and is
#      superseded by this measurement;
#  (c) the directories the deliveries emptied (docs/, .github/workflows/,
#      .github/, SPEC/...) are swept, and the pre-uninstall backup covers
#      every manifest record the run removes, not only .claude/ (measured
#      pre-cure: docs/ + .github/workflows/ + SPEC/v1 left behind empty, and
#      0 docs/.github entries in the backup tarball).
# ---------------------------------------------------------------------------
_x_sum() {
  python3 - "$1" <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())
PY
}
X_DELIVERED="docs/BRANCH-PROTECTION.md docs/rotation-log.md .github/CODEOWNERS .github/workflows/validate.yml.template .github/workflows/benchmarks.yml.template"
XT="$(mktemp -d 2>/dev/null || mktemp -d -t ceo-smoke-uninst)"
XO="$(mktemp -d 2>/dev/null || mktemp -d -t ceo-smoke-outside)"
( cd "$XT" && git init -q )
printf 'OUTSIDE PROBE - MUST NOT CHANGE\n' > "$XO/probe.md"
XO_BEFORE="$(_x_sum "$XO/probe.md")"
if ! CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
     bash "$SOURCE_DIR/scripts/install.sh" "$XT" --profile core --github-owner smoke-owner >"$XO/install.log" 2>&1; then
  echo "::error::9.8: install for the uninstall leg failed (see $XO/install.log)"
  fail=1
else
  for p in $X_DELIVERED; do
    if [[ ! -f "$XT/$p" ]]; then
      echo "::error::9.8: $p was not delivered"
      fail=1
    elif ! grep -q "  $p\$" "$XT/.claude/.install-manifest.sha256"; then
      echo "::error::9.8: $p is not in the install manifest - uninstall could never reach it"
      fail=1
    fi
  done
  # (a)+(c) pristine: every delivery goes, the emptied trees go, the probe is untouched,
  # the backup covers the removed deliveries.
  if ! bash "$SOURCE_DIR/scripts/uninstall.sh" "$XT" >"$XO/uninstall.log" 2>&1; then
    echo "::error::9.8: uninstall.sh failed on a pristine install (see $XO/uninstall.log)"
    fail=1
  fi
  for p in $X_DELIVERED; do
    if [[ -e "$XT/$p" ]]; then
      echo "::error::9.8: $p survived a pristine uninstall"
      fail=1
    fi
  done
  for d in docs .github SPEC; do
    if [[ -e "$XT/$d" ]]; then
      echo "::error::9.8: the emptied directory $d/ was left behind by uninstall"
      fail=1
    fi
  done
  if [[ "$(_x_sum "$XO/probe.md")" != "$XO_BEFORE" ]]; then
    echo "::error::9.8: the outside probe CHANGED during uninstall"
    fail=1
  fi
  X_BK="$(ls "$XT"/.claude.backup-uninstall-*.tar.gz 2>/dev/null | head -n 1 || true)"
  if [[ -z "$X_BK" ]]; then
    echo "::error::9.8: no pre-uninstall backup tarball was written"
    fail=1
  else
    # List to a FILE, then grep: `tar tzf | grep -q` under pipefail kills tar
    # with SIGPIPE on the first match and reports the SUCCESS as rc 141.
    # Measured (S337): green on macOS/bsdtar, red on Linux/GNU tar 1.35 for the
    # same tarball with the same entries.
    tar tzf "$X_BK" > "$XO/backup.list" 2>/dev/null || true
    if ! grep -qE '^(\./)?docs/BRANCH-PROTECTION\.md$' "$XO/backup.list"; then
      echo "::error::9.8: the pre-uninstall backup does not cover docs/ - the removed deliveries must be restorable"
      fail=1
    fi
  fi
  # (b) adopter-edited CODEOWNERS: PRESERVED, summary incomplete, manifest KEPT, exit 0;
  # the untouched deliveries are still removed.
  XT2="$(mktemp -d 2>/dev/null || mktemp -d -t ceo-smoke-uninst2)"
  ( cd "$XT2" && git init -q )
  if ! CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
       bash "$SOURCE_DIR/scripts/install.sh" "$XT2" --profile core --github-owner smoke-owner >"$XO/install2.log" 2>&1; then
    echo "::error::9.8: second install (edited-CODEOWNERS leg) failed (see $XO/install2.log)"
    fail=1
  else
    printf '\n# adopter rule\n* @smoke-owner\n' >> "$XT2/.github/CODEOWNERS"
    bash "$SOURCE_DIR/scripts/uninstall.sh" "$XT2" >"$XO/uninstall2.log" 2>&1
    x_rc=$?
    if [[ "$x_rc" -ne 0 ]]; then
      echo "::error::9.8: uninstall exited $x_rc with an adopter-edited CODEOWNERS (expected 0 + PRESERVED)"
      fail=1
    fi
    if [[ ! -f "$XT2/.github/CODEOWNERS" ]]; then
      echo "::error::9.8: the adopter-edited .github/CODEOWNERS was DELETED"
      fail=1
    fi
    if ! grep -q "PRESERVED (sha mismatch, user-modified): .github/CODEOWNERS" "$XO/uninstall2.log"; then
      echo "::error::9.8: no PRESERVED line for the edited CODEOWNERS (see $XO/uninstall2.log)"
      fail=1
    fi
    if ! grep -q "Uninstall summary (incomplete)" "$XO/uninstall2.log"; then
      echo "::error::9.8: the summary does not say incomplete with a preserved file"
      fail=1
    fi
    if [[ ! -f "$XT2/.claude/.install-manifest.sha256" ]]; then
      echo "::error::9.8: the manifest was removed despite a preserved file (a --force re-run is impossible)"
      fail=1
    fi
    if [[ -e "$XT2/docs/rotation-log.md" ]]; then
      echo "::error::9.8: a pristine docs/ delivery survived while only CODEOWNERS should be preserved"
      fail=1
    fi
    # rail r1 (S337): the PARTIAL path must sweep too — docs/ was emptied here.
    if [[ -e "$XT2/docs" ]]; then
      echo "::error::9.8: the emptied docs/ directory was left behind by a partial uninstall (preserved CODEOWNERS)"
      fail=1
    fi
  fi
  rm -rf "$XT2"
fi
rm -rf "$XT" "$XO"

if [[ "$CLEANUP" -eq 1 ]]; then
  rm -rf "$TARGET"
fi

if [[ "$fail" -eq 0 ]]; then
  echo "==> smoke install OK"
  exit 0
else
  echo "==> smoke install FAILED"
  exit 1
fi
