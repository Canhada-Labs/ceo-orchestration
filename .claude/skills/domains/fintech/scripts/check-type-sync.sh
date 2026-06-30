#!/bin/bash
# Cross-repo type sync check
# Compares backend types with frontend engine/types.ts
# Usage: BACKEND=/path/to/backend FRONTEND=/path/to/frontend bash .claude/scripts/check-type-sync.sh
#
# NOTE: This script is a TEMPLATE for cross-repo drift detection in a split
# backend/frontend fintech project. Adapt the paths, file names, and interface
# names for your own project before using. Export BACKEND and FRONTEND env vars
# (or edit the defaults below) to point at your repos.

BACKEND="${BACKEND:?ERROR: set BACKEND env var to backend repo path}"
FRONTEND="${FRONTEND:?ERROR: set FRONTEND env var to frontend repo path}"
BACKEND_TYPES="$BACKEND/src/types.ts"
FRONTEND_TYPES="$FRONTEND/src/engine/types.ts"
ERRORS=0

echo "=== Cross-Repo Type Sync Check ==="
echo "Backend:  $BACKEND_TYPES"
echo "Frontend: $FRONTEND_TYPES"
echo ""

[[ -s "$BACKEND_TYPES" && -r "$BACKEND_TYPES" ]] || { echo "ERROR: backend types file missing, empty, or unreadable: $BACKEND_TYPES"; exit 2; }
[[ -s "$FRONTEND_TYPES" && -r "$FRONTEND_TYPES" ]] || { echo "ERROR: frontend types file missing, empty, or unreadable: $FRONTEND_TYPES"; exit 2; }
echo ""

# 1. Check ExchangeCode enum values match
echo "--- ExchangeCode ---"
BACKEND_EXCHANGES=$(grep -oE '"[a-z]+"' "$BACKEND_TYPES" | sort -u)
FRONTEND_EXCHANGES=$(grep -oE '"[a-z]+"' "$FRONTEND_TYPES" | grep -v 'http\|ws\|api\|src\|eng' | sort -u)

[[ -n "$BACKEND_EXCHANGES" ]] || { echo "  ERROR: no backend ExchangeCode-like values found"; exit 2; }
[[ -n "$FRONTEND_EXCHANGES" ]] || { echo "  ERROR: no frontend ExchangeCode-like values found"; exit 2; }

# Find exchanges in backend but not frontend
echo "  Backend exchanges not in frontend:"
for ex in $BACKEND_EXCHANGES; do
  if ! echo "$FRONTEND_EXCHANGES" | grep -q "$ex"; then
    echo "    MISSING: $ex"
    ERRORS=$((ERRORS + 1))
  fi
done

if [ $ERRORS -eq 0 ]; then
  echo "    (all present)"
fi

echo ""

# 2. Check key interfaces exist in both
echo "--- Key Interfaces ---"
KEY_TYPES=("BookState" "EngineStatus" "ExchangeCode" "ArbitrageOpportunity" "MarketData" "TickerData")

# FIELD-LEVEL CHECK: intentionally out of scope for this advisory script.
# Use a TypeScript parser such as ts-morph in CI for field/property equivalence.
for t in "${KEY_TYPES[@]}"; do
  BE=$(grep -Ec "(interface|type|enum)[[:space:]]+$t([[:space:]=<{]|$)" "$BACKEND_TYPES")
  FE=$(grep -Ec "(interface|type|enum)[[:space:]]+$t([[:space:]=<{]|$)" "$FRONTEND_TYPES")
  if [ "$BE" -gt 0 ] && [ "$FE" -gt 0 ]; then
    echo "  OK: $t (backend: $BE, frontend: $FE)"
  elif [ "$BE" -gt 0 ] && [ "$FE" -eq 0 ]; then
    echo "  DRIFT: $t exists in backend but NOT in frontend"
    ERRORS=$((ERRORS + 1))
  elif [ "$BE" -eq 0 ] && [ "$FE" -gt 0 ]; then
    echo "  INFO: $t exists in frontend only (frontend-specific type)"
  else
    echo "  MISSING: $t not found in backend or frontend"
    ERRORS=$((ERRORS + 1))
  fi
done

echo ""

# 3. Check API response wrapper patterns
echo "--- API Response Patterns ---"
# Check if frontend uses same field names as backend routes
BACKEND_WRAPPERS=$(grep -oE 'return.*\{.*(markets|opportunities|exchanges|pairs|books)' "$BACKEND/src/routes/"*.ts 2>/dev/null | grep -oE '(markets|opportunities|exchanges|pairs|books)' | sort -u)

echo "  Backend response wrappers: $BACKEND_WRAPPERS"
echo "  (Manual check: verify frontend queries use same field names)"

echo ""

# 4. Check EngineStatus values match
echo "--- EngineStatus Values ---"
BE_STATUS=$(grep -oE '"(WARMING|READY|DELAYED|STALE|INVALID|DISABLED)"' "$BACKEND_TYPES" | sort -u)
FE_STATUS=$(grep -oE '"(WARMING|READY|DELAYED|STALE|INVALID|DISABLED)"' "$FRONTEND_TYPES" | sort -u)

[[ -n "$BE_STATUS" ]] || { echo "  ERROR: no backend EngineStatus values found"; exit 2; }
[[ -n "$FE_STATUS" ]] || { echo "  ERROR: no frontend EngineStatus values found"; exit 2; }

echo "  Backend:  $BE_STATUS"
echo "  Frontend: $FE_STATUS"

if [ "$BE_STATUS" = "$FE_STATUS" ]; then
  echo "  OK: EngineStatus values match"
else
  echo "  DRIFT: EngineStatus values differ!"
  ERRORS=$((ERRORS + 1))
fi

echo ""
echo "=== Summary ==="
echo "Errors: $ERRORS"
if [ $ERRORS -gt 0 ]; then
  echo "ACTION: DataSchemaArchitect + Frontend Lead need to sync types"
  exit 1
else
  echo "PASS: Types appear in sync"
  exit 0
fi
