#!/usr/bin/env bash
# PLAN-093 Wave A + C execute ceremony — run from a terminal OUTSIDE Claude.app.
#
# Applies 6 kernel edits via direct Python file writes (bypasses claude-code's
# Edit-tool hooks, since the script does not invoke that tool). Owner-signed
# sentinel at .claude/plans/PLAN-093/architect/round-2/approved.md(.asc)
# is the audit trail authorizing these writes.
#
# Workflow:
#   1. Owner runs ./scripts/local/plan-093-execute-ceremony.sh
#   2. Script applies 6 edits + runs validators + runs tests + git diff stat
#   3. Owner copies the script output and pastes it back to CEO in the
#      ongoing Claude session
#   4. CEO does the closeout (VERSION + CHANGELOG + waivers + CLAUDE.md +
#      status flip executing→done) via the regular Edit tool — those files
#      are not kernel-protected
#   5. Owner runs `git commit -S` + `git tag -s v1.26.0 -m "..." ` + `git push`
#
# IMPORTANT: this script does NOT commit or tag. Owner approves diffs first.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "PLAN-093 Wave A + C execute ceremony"
echo "===================================="
echo "Repo: $REPO_ROOT"
echo "HEAD: $(git rev-parse --short HEAD)"
echo ""

# -----------------------------------------------------------------
# Pre-flight — Codex P2-4 closure: verify sentinel + .asc exist
# -----------------------------------------------------------------
SENTINEL="$REPO_ROOT/.claude/plans/PLAN-093/architect/round-2/approved.md"
if [[ ! -f "$SENTINEL" ]] || [[ ! -f "$SENTINEL.asc" ]]; then
    echo "ABORT: round-2 sentinel + .asc missing. Cannot proceed without audit trail." >&2
    echo "  Expected: $SENTINEL(.asc)" >&2
    exit 10
fi
echo "Sentinel: $(basename "$SENTINEL")(.asc) present."
echo ""

# -----------------------------------------------------------------
# Pre-flight — Codex P1-1 closure: detect v1-state and abort.
# v1 ceremony shipped a buggy belt-and-braces grep line at
# coverage.yml:67. v2 is idempotent against clean OR clean-v1 state,
# but cannot REPAIR v1's bad line because the marker would skip it.
# -----------------------------------------------------------------
BUGGY_LINE='if grep -rn "import hypothesis'
if grep -qF "$BUGGY_LINE" "$REPO_ROOT/.github/workflows/coverage.yml" 2>/dev/null; then
    echo "ABORT: detected v1 ceremony residue in coverage.yml (self-colliding grep line)." >&2
    echo "" >&2
    echo "Recovery (run these 6 git checkouts first to clean v1 state):" >&2
    echo "  git -C $REPO_ROOT checkout -- .github/workflows/coverage.yml" >&2
    echo "  git -C $REPO_ROOT checkout -- .claude/hooks/SessionStart.py" >&2
    echo "  git -C $REPO_ROOT checkout -- .claude/hooks/_lib/tier_policy/loader.py" >&2
    echo "  git -C $REPO_ROOT checkout -- .claude/hooks/_lib/adapters/live/_transport.py" >&2
    echo "  git -C $REPO_ROOT checkout -- .claude/hooks/check_pair_rail.py" >&2
    echo "  git -C $REPO_ROOT checkout -- .claude/hooks/_lib/audit_emit.py" >&2
    echo "" >&2
    echo "Then re-run: bash $0" >&2
    exit 11
fi

# -----------------------------------------------------------------
# Step 1 — Apply kernel edits via Python file writes
# -----------------------------------------------------------------
echo "[1/6] Applying 6 kernel edits..."
python3 "$REPO_ROOT/scripts/local/plan-093-apply-kernel-edits.py"
echo ""

# -----------------------------------------------------------------
# Step 2 — Sidecar validators
# -----------------------------------------------------------------
echo "[2/6] Sidecar manifest + boundary validators..."
python3 "$REPO_ROOT/.claude/scripts/check-sidecar-manifest.py" --strict
python3 "$REPO_ROOT/.claude/sidecars/c5-dev-tools/hypothesis/boundary_test.py"
echo ""

# -----------------------------------------------------------------
# Step 3 — Smoke /ceo-boot (should show 18 Tier-S checks)
# -----------------------------------------------------------------
echo "[3/6] /ceo-boot smoke (expect 18 Tier-S checks)..."
python3 "$REPO_ROOT/.claude/scripts/ceo-boot.py" --short 2>&1 | tail -8 || true
echo ""

# -----------------------------------------------------------------
# Step 4 — Hook tests
# -----------------------------------------------------------------
echo "[4/6] Hook tests (pre-existing 14 failures from S115 baseline are NOT regressions)..."
python3 -m pytest "$REPO_ROOT/.claude/hooks/tests" -q --tb=no 2>&1 | tail -5 || true
echo ""

# -----------------------------------------------------------------
# Step 5 — Script tests + detect-repo-profile fixtures
# -----------------------------------------------------------------
echo "[5/6] Script tests (Wave D fixtures should bring detect-repo-profile to 27/27)..."
CEO_REQUIRE_REPO_PROFILE_FIXTURES=1 python3 -m pytest \
    "$REPO_ROOT/.claude/scripts/tests/test_detect_repo_profile.py" -q --tb=no 2>&1 | tail -5 || true
python3 -m pytest "$REPO_ROOT/.claude/scripts/tests" -q --tb=no 2>&1 | tail -5 || true
echo ""

# -----------------------------------------------------------------
# Step 6 — Git status / diff stat
# -----------------------------------------------------------------
echo "[6/6] Working tree state:"
git -C "$REPO_ROOT" status --short
echo ""
echo "Diff stat:"
git -C "$REPO_ROOT" diff --stat
echo ""

echo "===================================="
echo "CEREMONY COMPLETE — copy this output back to CEO in the Claude session."
echo ""
echo "Next: CEO runs closeout (VERSION + CHANGELOG + waivers + CLAUDE.md + status→done)"
echo "       then Owner: git commit -S + git tag -s v1.26.0 + git push origin main --tags"
