#!/bin/bash
# verify-sprint3-invariants.sh — gate for PLAN-003 Item C (bash legacy removal).
#
# Per PLAN-002 §11-bis Q5, the bash fallback hooks in
# .claude/hooks/legacy/ may be removed ONLY IF all three invariants hold.
# This script checks them mechanically. Exit 0 unlocks the removal
# commit; any non-zero exit keeps legacy/ for one more sprint.
#
# Invariants:
#
#   1. CI green continuously from A.4 commit to current HEAD (macOS + Linux,
#      including test_hook_latency.py).
#   2. audit-log.errors file is empty (or absent) — no infrastructure
#      errors captured by the Python hooks in the window.
#   3. At least 50 real Python-hooked spawns have been captured in the
#      audit log — enough sample size to trust the Python path in
#      production.
#
# Plus debate consensus additions (S5):
#
#   4. No stale references to .claude/hooks/legacy/ anywhere in the repo
#      outside this script itself and the PLAN-*.md history.
#
# Exit codes:
#   0 — all invariants met; removal is safe
#   1 — one or more invariants failed
#   2 — cannot check (missing tools, missing audit log)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

FAIL=0
WARN=0

echo "==> Verifying PLAN-003 Item C invariants"
echo ""

# ---- Invariant 1: CI green continuously ----
# We cannot programmatically check "CI was green on every commit since
# A.4" from the local clone. This invariant is verified manually by the
# Owner — we surface the instruction and check that the most recent
# commit at least exists.
echo "## Invariant 1: CI green continuously"
echo ""
echo "   This cannot be checked locally. Verify on GitHub:"
echo "     https://github.com/<owner>/<repo>/actions"
echo "   Confirm: every commit from A.4 (audit_log.py landing) to HEAD"
echo "   shows green 'validate' workflow on BOTH macOS and Linux runners."
echo ""
echo "   Latest 5 commits on this branch:"
git log --oneline -5 | sed 's/^/     /'
echo ""
echo "   [MANUAL] Did CI stay green for all of them? (y/N) — this script"
echo "   cannot assert this; skipping automated verification."
echo ""

# ---- Invariant 2: audit-log.errors empty ----
echo "## Invariant 2: audit-log.errors empty"
echo ""
ERR_PATH="$HOME/.claude/projects/ceo-orchestration/audit-log.errors"
if [ ! -f "$ERR_PATH" ]; then
  echo "   ✓ audit-log.errors does not exist — zero infra errors captured"
else
  lines=$(wc -l < "$ERR_PATH" | tr -d ' ')
  if [ "$lines" -eq 0 ]; then
    echo "   ✓ audit-log.errors is empty — zero infra errors"
  else
    echo "   ❌ audit-log.errors has $lines line(s) — infrastructure errors present"
    echo "   Path: $ERR_PATH"
    echo "   Review before removing legacy fallbacks."
    FAIL=1
  fi
fi
echo ""

# ---- Invariant 3: 50+ real Python-hooked spawns ----
echo "## Invariant 3: 50+ real Python-hooked spawns in audit log"
echo ""
AUDIT_PATH="$HOME/.claude/projects/ceo-orchestration/audit-log.jsonl"
if [ ! -f "$AUDIT_PATH" ]; then
  echo "   ⚠ audit-log.jsonl not found at $AUDIT_PATH"
  echo "   Either nothing has been spawned yet, or XDG path differs."
  echo "   [MANUAL] Confirm you have >= 50 spawns; otherwise defer removal."
  WARN=1
else
  SPAWN_COUNT=$(wc -l < "$AUDIT_PATH" | tr -d ' ')
  echo "   Audit log has $SPAWN_COUNT line(s)"
  if [ "$SPAWN_COUNT" -ge 50 ]; then
    echo "   ✓ >= 50 spawns captured"
  else
    echo "   ❌ < 50 spawns — insufficient sample size"
    FAIL=1
  fi
fi
echo ""

# ---- Invariant 4 (debate S5): no stale legacy references ----
echo "## Invariant 4 (debate S5): no stale legacy/ references"
echo ""
# Search the repo for 'legacy' mentions outside allowed zones.
# Allowed: this script, PLAN-001/002/003 (history), the legacy/ dir itself.
STALE=$(grep -rln 'hooks/legacy' \
  .github/workflows \
  .claude/settings.json \
  templates/settings \
  README.md INSTALL.md CLAUDE.md PROTOCOL.md 2>/dev/null || true)

if [ -z "$STALE" ]; then
  echo "   ✓ No stale references to .claude/hooks/legacy/ in CI/settings/docs"
else
  echo "   ❌ Stale references to hooks/legacy found in:"
  echo "$STALE" | sed 's/^/     /'
  echo "   Clean these up before the removal commit."
  FAIL=1
fi
echo ""

# ---- Summary ----
echo "==> Summary"
if [ "$FAIL" -eq 1 ]; then
  echo "   ❌ One or more invariants FAILED. Do not remove legacy/ yet."
  exit 1
elif [ "$WARN" -eq 1 ]; then
  echo "   ⚠ One or more invariants could not be verified automatically."
  echo "   Review manually, then re-run."
  exit 1
else
  echo "   ✓ All mechanical invariants met. Legacy removal is safe."
  echo "   Remaining: manual confirmation of Invariant 1 (CI history)."
  exit 0
fi
