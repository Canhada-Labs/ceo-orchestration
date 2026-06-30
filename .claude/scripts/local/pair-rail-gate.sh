#!/bin/bash
# Pair-rail gate — Phase 1 pre-flight (PLAN-081 R1 S-Sec-6 + C7 + C5).
#
# Owner-physical / CI-runnable pre-flight checks before invoking the Pair-
# Rail dispatch (PLAN-081 Phase 2+) or running the Phase 4 promotion gate.
# Phase 1 subset codifies the FOUR mandatory pre-conditions:
#
#   1. OPENAI_API_KEY env var presence (Codex MCP requires it).
#   2. Last Codex API key rotation <90 days (R1 S-Sec-6).
#   3. Codex CLI binary present + `codex --version` returns cleanly
#      (warm CLI startup pre-test for first-prompt latency).
#   4. (Phase 6) Codex CLI version matches `.claude/governance/codex-cli-pin.txt`
#      semver range. Phase 1 stub: file may not exist; warn but don't fail.
#
# Phase 6 will EXTEND this script (additional blocks for verdict release_tag
# verification, codex CLI binary SHA pin check, etc.). Phase 1 ships this
# subset; Phase 6 amends.
#
# Usage:
#
#   bash .claude/scripts/local/pair-rail-gate.sh --phase 1
#
# Exit codes:
#   0  — all gates pass
#   1  — gate failure (specific message printed)
#   2  — env override active (audit event emitted, gate bypassed)
#
# Owner overrides (use sparingly + audit):
#   CEO_CODEX_KEY_ROTATION_OVERRIDE=1   bypass 90-day rotation refusal
#   CEO_PAIR_RAIL_DISABLE=1             skip ALL gates (emergency only)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REPO_ROOT="${REPO_ROOT_OVERRIDE:-$REPO_ROOT}"
cd "$REPO_ROOT"

PHASE="${1:-}"
if [ "$PHASE" != "--phase" ] || [ -z "${2:-}" ]; then
  echo "usage: $0 --phase <1|6>"
  exit 1
fi
PHASE_NUM="$2"

if [ "${CEO_PAIR_RAIL_DISABLE:-}" = "1" ]; then
  echo "WARNING: CEO_PAIR_RAIL_DISABLE=1 — bypassing all gates (emergency mode)"
  exit 2
fi

echo "============================================"
echo "pair-rail-gate.sh — Phase $PHASE_NUM pre-flight"
echo "============================================"

# ---- Gate 1: OPENAI_API_KEY env var presence ----
echo ""
echo "Gate 1: OPENAI_API_KEY presence"
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "  FAIL: OPENAI_API_KEY not set in environment"
  echo "  Codex MCP requires this env var. Source your .envrc / .env file."
  exit 1
fi
KEY_LEN="${#OPENAI_API_KEY}"
if [ "$KEY_LEN" -lt 16 ]; then
  echo "  FAIL: OPENAI_API_KEY length $KEY_LEN suspiciously short"
  exit 1
fi
echo "  OK: OPENAI_API_KEY present (length=$KEY_LEN)"

# ---- Gate 2: last rotation <90 days ----
echo ""
echo "Gate 2: OPENAI_API_KEY rotation cadence (90-day)"
ROTATION_LOG="docs/rotation-log.md"
if [ ! -f "$ROTATION_LOG" ]; then
  echo "  WARN: rotation-log.md missing; skipping cadence check"
else
  # Find the latest OPENAI_API_KEY row's date column. The row format is:
  #   | YYYY-MM-DD | OPENAI_API_KEY | ... |
  LAST_ROTATION_DATE=$(grep -E '^\| [0-9]{4}-[0-9]{2}-[0-9]{2} \| OPENAI_API_KEY' "$ROTATION_LOG" \
    | tail -1 \
    | awk -F'|' '{gsub(/ /,"",$2); print $2}' \
    || echo "")
  if [ -z "$LAST_ROTATION_DATE" ]; then
    echo "  WARN: no OPENAI_API_KEY rotation row found in log"
    if [ "${CEO_CODEX_KEY_ROTATION_OVERRIDE:-}" != "1" ]; then
      echo "  Set CEO_CODEX_KEY_ROTATION_OVERRIDE=1 to bypass + log a fresh rotation."
      exit 1
    fi
  else
    # Compute days since rotation
    if command -v gdate >/dev/null 2>&1; then
      DATE_CMD="gdate"
    else
      DATE_CMD="date"
    fi
    LAST_TS=$($DATE_CMD -d "$LAST_ROTATION_DATE" +%s 2>/dev/null || $DATE_CMD -j -f "%Y-%m-%d" "$LAST_ROTATION_DATE" +%s 2>/dev/null || echo 0)
    NOW_TS=$($DATE_CMD +%s)
    if [ "$LAST_TS" = "0" ]; then
      echo "  WARN: could not parse rotation date $LAST_ROTATION_DATE; skipping cadence"
    else
      DAYS_SINCE=$(( (NOW_TS - LAST_TS) / 86400 ))
      echo "  Last rotation: $LAST_ROTATION_DATE ($DAYS_SINCE days ago)"
      if [ "$DAYS_SINCE" -ge 90 ]; then
        if [ "${CEO_CODEX_KEY_ROTATION_OVERRIDE:-}" = "1" ]; then
          echo "  WARN: rotation >90d but CEO_CODEX_KEY_ROTATION_OVERRIDE=1 — bypassing"
        else
          echo "  FAIL: OPENAI_API_KEY rotation $DAYS_SINCE days ago exceeds 90-day cadence"
          echo "  Rotate via OpenAI dashboard + append to docs/rotation-log.md."
          echo "  Or set CEO_CODEX_KEY_ROTATION_OVERRIDE=1 for emergency/off-cycle."
          exit 1
        fi
      elif [ "$DAYS_SINCE" -ge 75 ]; then
        echo "  WARN: rotation $DAYS_SINCE days ago — approaching 90-day refusal"
      else
        echo "  OK: rotation $DAYS_SINCE days ago (<75 day warn threshold)"
      fi
    fi
  fi
fi

# ---- Gate 3: Codex CLI present + warm startup ----
echo ""
echo "Gate 3: Codex CLI present + warm startup"
if ! command -v codex >/dev/null 2>&1; then
  echo "  FAIL: codex CLI not found in PATH"
  echo "  Install via: npm install -g @openai/codex"
  exit 1
fi
CODEX_PATH="$(command -v codex)"
echo "  Codex CLI path: $CODEX_PATH"

# Run --version (5s timeout — Codex CLI cold start is typically <2s)
CODEX_VERSION=$(timeout 5 codex --version 2>&1 || echo "TIMEOUT")
if [ "$CODEX_VERSION" = "TIMEOUT" ]; then
  echo "  FAIL: codex --version timed out (>5s)"
  exit 1
fi
echo "  Codex CLI version: $CODEX_VERSION"

# ---- Gate 4 (Phase 6): codex-cli-pin.txt semver range check ----
if [ "$PHASE_NUM" = "6" ]; then
  echo ""
  echo "Gate 4: Codex CLI version pin check"
  PIN_FILE=".claude/governance/codex-cli-pin.txt"
  if [ ! -f "$PIN_FILE" ]; then
    echo "  FAIL: $PIN_FILE missing (Phase 6 deliverable)"
    exit 1
  fi
  # Phase 6 will codify this — for Phase 1 we stub-pass
  echo "  STUB: Phase 6 implements semver-range check (Phase 1 stub-pass)"
fi

echo ""
echo "============================================"
echo "All Phase $PHASE_NUM pre-flight gates PASS"
echo "============================================"
exit 0
