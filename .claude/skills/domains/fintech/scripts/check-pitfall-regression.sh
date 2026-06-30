#!/bin/bash
# Pitfall Regression Check — FINTECH DOMAIN
# Usage: bash .claude/skills/domains/fintech/scripts/check-pitfall-regression.sh
# Run alongside the universal check-pitfall-regression.sh for fintech projects.
#
# This script enforces FIN-*, EX-* pitfalls from
#   .claude/skills/domains/fintech/pitfalls.yaml

REPO_ROOT="$(cd "$(dirname "$0")/../../../../.." && pwd)"
SRC="$REPO_ROOT/src"
ERRORS=0
WARNINGS=0

echo "=== Pitfall Regression Check (fintech) ==="
echo "Repo: $REPO_ROOT"
echo ""

# FIN-001: Float arithmetic on financial values (check for Math.round/floor/ceil on prices)
echo "--- FIN-001: Float arithmetic on prices ---"
MATH_ROUND_PRICE=$(grep -rn "Math\.\(round\|floor\|ceil\)" "$SRC" --include="*.ts" --include="*.tsx" 2>/dev/null \
  | grep -iv "test\|log\|debug\|count\|index\|page\|limit\|offset\|timeout\|delay\|interval\|retry\|max\|min\|bucket" \
  | grep -i "price\|volume\|amount\|pnl\|profit\|loss\|fee\|cost\|value\|balance\|spread\|depth\|vwap" || true)
if [ -n "$MATH_ROUND_PRICE" ]; then
  echo "  WARNING: Math.round/floor/ceil near financial terms (use decimal library instead):"
  echo "$MATH_ROUND_PRICE" | head -5
  WARNINGS=$((WARNINGS + 1))
else
  echo "  PASS: No suspicious Math.round on financial values"
fi

echo ""

# FIN-004: parseFloat on financial values (stricter than universal warning — BLOCK for fintech)
echo "--- FIN-004: parseFloat on financial values ---"
PARSE_FLOAT_FIN=$(grep -rn "parseFloat" "$SRC" --include="*.ts" --include="*.tsx" 2>/dev/null \
  | grep -v "test\|__tests__\|node_modules\|.d.ts" \
  | grep -i "price\|volume\|amount\|pnl\|profit\|loss\|fee\|cost\|balance\|spread\|depth\|vwap" || true)
if [ -n "$PARSE_FLOAT_FIN" ]; then
  echo "  FAIL: parseFloat on financial values found (use safeNumber/safeFixed/safePct):"
  echo "$PARSE_FLOAT_FIN" | head -5
  ERRORS=$((ERRORS + 1))
else
  echo "  PASS: Zero parseFloat on financial values"
fi

echo ""

# EX-004: cleanupConnection must clear orderbooks (heuristic — check adapter files)
echo "--- EX-004: Adapter cleanup completeness ---"
ADAPTER_FILES=$(grep -rl "cleanupConnection\|onDisconnect\|onClose" "$SRC/adapters/" --include="*.ts" 2>/dev/null || true)
if [ -n "$ADAPTER_FILES" ]; then
  echo "  INFO: Adapter cleanup handlers found in $(echo "$ADAPTER_FILES" | wc -l | tr -d ' ') files"
  echo "  (Manual check: each cleanup must clear orderbooks/state for the closed connection)"
fi

echo ""

# FIN-003: spread_pct / change_pct type safety (frontend display)
echo "--- FIN-003: Percentage field type safety ---"
PCT_RAW=$(grep -rn "spread_pct\|change_pct" "$SRC" --include="*.tsx" --include="*.ts" 2>/dev/null \
  | grep -v "test\|__tests__\|.d.ts\|interface\|type " \
  | grep -i "toFixed\|\.toString" || true)
if [ -n "$PCT_RAW" ]; then
  echo "  WARNING: Direct formatting of _pct fields without safe helper:"
  echo "$PCT_RAW" | head -3
  WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "=== Summary (fintech) ==="
echo "Errors: $ERRORS (blocking)"
echo "Warnings: $WARNINGS (review needed)"

if [ $ERRORS -gt 0 ]; then
  echo "FAIL: $ERRORS fintech pitfall regressions detected"
  exit 1
else
  echo "PASS: No fintech pitfall regressions (warnings are advisory)"
  exit 0
fi
