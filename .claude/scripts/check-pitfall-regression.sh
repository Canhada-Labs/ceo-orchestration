#!/bin/bash
set -euo pipefail
# Pitfall Regression Check — enforces known universal rules haven't been violated
# Usage: bash .claude/scripts/check-pitfall-regression.sh
# Run before commit or as CI check
#
# Domain-specific checks (e.g. fintech: FIN-*, EX-*) live in:
#   .claude/skills/domains/<domain>/scripts/check-pitfall-regression.sh
# Run both if your project installs a domain profile.

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$REPO_ROOT/src"
ERRORS=0
WARNINGS=0

echo "=== Pitfall Regression Check (universal) ==="
echo "Repo: $REPO_ROOT"
echo ""

# Detect if this is frontend or backend (heuristic — override by setting REPO_TYPE env)
if [ -z "${REPO_TYPE:-}" ]; then
  if [ -f "$REPO_ROOT/vite.config.ts" ] || [ -f "$REPO_ROOT/vite.config.js" ] || [ -f "$REPO_ROOT/next.config.js" ]; then
    REPO_TYPE="frontend"
  else
    REPO_TYPE="backend"
  fi
fi

echo "Repo type: $REPO_TYPE"
echo ""

# === UNIVERSAL CHECKS ===

# Universal: No parseFloat on numeric values in production code (not tests).
# This is strict on projects that care about numeric correctness. Comment out if too noisy.
echo "--- Universal: parseFloat usage ---"
PARSE_FLOAT=$(grep -rn "parseFloat" "$SRC" --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v "test" | grep -v "__tests__" | grep -v "node_modules" | grep -v ".d.ts" || true)
if [ -n "$PARSE_FLOAT" ]; then
  echo "  WARNING: parseFloat found in production code (consider typed number parsing):"
  echo "$PARSE_FLOAT" | head -5
  WARNINGS=$((WARNINGS + 1))
else
  echo "  PASS: Zero parseFloat in production code"
fi

echo ""

# === BACKEND-SPECIFIC CHECKS ===
if [ "$REPO_TYPE" = "backend" ]; then

  # SEC-001: Check route ordering (literal before parameterized). Heuristic only.
  echo "--- SEC-001: Route ordering ---"
  ROUTE_FILES=$(grep -rl "app\.\(get\|post\|put\|delete\)" "$SRC/routes/" --include="*.ts" 2>/dev/null || true)
  if [ -n "$ROUTE_FILES" ]; then
    echo "  INFO: Route files to review: $(echo "$ROUTE_FILES" | wc -l | tr -d ' ')"
    echo "  (Manual check: literal paths must come BEFORE parameterized in each file)"
  fi

  echo ""

  # IPC-001: No hot-path CPU on main thread. Customize HOT_FILES for your project.
  # For multi-process backends: list the main-thread hot files (e.g. router, gateway).
  echo "--- IPC-001: Hot-path CPU check ---"
  HOT_FILES_PATTERN="${HOT_FILES_PATTERN:-src/main.ts src/gateway.ts src/router.ts}"
  MAIN_PROCESS_HEAVY=""
  for f in $HOT_FILES_PATTERN; do
    if [ -f "$REPO_ROOT/$f" ]; then
      MATCHES=$(grep -n "JSON\.parse\|JSON\.stringify" "$REPO_ROOT/$f" 2>/dev/null | grep -v "//\|control\|config\|log\|debug" || true)
      if [ -n "$MATCHES" ]; then
        MAIN_PROCESS_HEAVY="$MAIN_PROCESS_HEAVY\n$f:\n$MATCHES"
      fi
    fi
  done
  if [ -n "$MAIN_PROCESS_HEAVY" ]; then
    echo "  WARNING: JSON.parse/stringify in main thread hot files:"
    echo -e "$MAIN_PROCESS_HEAVY" | head -10
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  PASS: No heavy JSON ops in configured hot-path files"
  fi

  echo ""

  # SEC-002: Async pollers must use safe() wrapper
  echo "--- SEC-002: Async pollers safety ---"
  UNSAFE_TIMERS=$(grep -rn "setInterval\|setTimeout" "$SRC" --include="*.ts" 2>/dev/null | grep "async" | grep -v "safe\|try\|catch\|test\|__tests__" || true)
  if [ -n "$UNSAFE_TIMERS" ]; then
    echo "  WARNING: Async callbacks in timers without visible safe() wrapper:"
    echo "$UNSAFE_TIMERS" | head -5
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  PASS: Timer callbacks appear safe"
  fi

fi

# === FRONTEND-SPECIFIC CHECKS ===
if [ "$REPO_TYPE" = "frontend" ]; then

  # FE-001/FE-002: No hardcoded colors outside design tokens
  echo "--- FE: Hardcoded colors ---"
  HARDCODED_COLORS=$(grep -rn "text-white\b" "$SRC" --include="*.tsx" 2>/dev/null | grep -v "bg-\|btn-\|border-" | head -5 || true)
  if [ -n "$HARDCODED_COLORS" ]; then
    echo "  WARNING: text-white usage (should use design token semantic class):"
    echo "$HARDCODED_COLORS" | head -3
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  PASS: No suspicious text-white"
  fi

  echo ""

  # Check for :any type — grep exits 1 on zero matches; tolerate under
  # set -e + pipefail (especially common in this framework repo which has
  # no src/ tree).
  echo "--- TS: :any types ---"
  ANY_COUNT=$({ grep -rn ": any\b\|:any\b\|as any\b" "$SRC" --include="*.ts" --include="*.tsx" 2>/dev/null || true; } | { grep -v "test\|__tests__\|.d.ts\|node_modules" || true; } | wc -l | tr -d ' ')
  ANY_THRESHOLD="${ANY_THRESHOLD:-10}"
  echo "  :any count: $ANY_COUNT (threshold: $ANY_THRESHOLD)"
  if [ "$ANY_COUNT" -gt "$ANY_THRESHOLD" ]; then
    echo "  WARNING: :any count above threshold ($ANY_COUNT > $ANY_THRESHOLD)"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  PASS: :any count acceptable ($ANY_COUNT)"
  fi

  echo ""

  # Check for dangerouslySetInnerHTML (XSS vector)
  echo "--- SEC: dangerouslySetInnerHTML ---"
  DANGEROUS=$(grep -rn "dangerouslySetInnerHTML" "$SRC" --include="*.tsx" 2>/dev/null | grep -v "test\|__tests__" || true)
  if [ -n "$DANGEROUS" ]; then
    echo "  WARNING: dangerouslySetInnerHTML found:"
    echo "$DANGEROUS" | head -5
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  PASS: No dangerouslySetInnerHTML"
  fi

fi

echo ""
echo "=== Summary ==="
echo "Errors: $ERRORS (blocking)"
echo "Warnings: $WARNINGS (review needed)"

if [ $ERRORS -gt 0 ]; then
  echo "FAIL: $ERRORS pitfall regressions detected"
  exit 1
else
  echo "PASS: No pitfall regressions (warnings are advisory)"
  exit 0
fi
