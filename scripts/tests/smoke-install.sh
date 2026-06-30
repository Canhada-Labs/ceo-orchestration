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
