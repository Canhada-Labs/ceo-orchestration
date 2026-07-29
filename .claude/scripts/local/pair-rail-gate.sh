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
# PLAN-163 C4 (codex/grok R4): REPO_ROOT_OVERRIDE is a TEST-ONLY seam — it
# redirects Gate 4 pin verification AND the subsequent codex exec onto an
# arbitrary tree, so it is honored ONLY under the explicit
# CEO_PAIR_RAIL_TEST_MODE=1 marker (mirrors the hook's triple/manifest seams).
# On the live path it is IGNORED: a stray/hostile REPO_ROOT_OVERRIDE cannot
# point pin verification at an attacker-controlled tree/verifier.
if [ "${CEO_PAIR_RAIL_TEST_MODE:-}" = "1" ] && [ -n "${REPO_ROOT_OVERRIDE:-}" ]; then
  REPO_ROOT="$REPO_ROOT_OVERRIDE"
fi
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

# ---- Gate 3a: Codex CLI PRESENT (path resolution only — NO exec yet) ----
# M4 (PLAN-163 fix-pass): `command -v` resolves the launcher path WITHOUT
# executing the binary. The warm-startup `codex --version` exec is deferred
# to Gate 3b, AFTER the ADR-182 pin verification (Gate 4) has run — so on
# Phase 6 an unverified / swapped payload is NEVER exec'd. The pin check
# itself (check_pair_rail.py --verify-codex-pin) only HASHES the payload; it
# never spawns it.
echo ""
echo "Gate 3: Codex CLI present + warm startup"
if ! command -v codex >/dev/null 2>&1; then
  echo "  FAIL: codex CLI not found in PATH"
  echo "  Install via: npm install -g @openai/codex"
  exit 1
fi
CODEX_PATH="$(command -v codex)"
echo "  Codex CLI path: $CODEX_PATH"

# ---- Gate 4 (Phase 6): codex pin check — semver file + ADR-182 payload sha ----
# M4: MUST run BEFORE the Gate 3b warm-startup exec. If the pin fails we
# abort here, having never executed the unverified codex payload.
if [ "$PHASE_NUM" = "6" ]; then
  echo ""
  echo "Gate 4: Codex CLI version pin check (BEFORE any binary exec — M4)"
  PIN_FILE=".claude/governance/codex-cli-pin.txt"
  if [ ! -f "$PIN_FILE" ]; then
    echo "  FAIL: $PIN_FILE missing (Phase 6 deliverable)"
    exit 1
  fi
  # ADR-182 (PLAN-163 T5.2): the old "binary sha" here compared only the
  # semver / launcher artifact — `shasum -a 256 $(which codex)` hashes
  # the npm JS launcher, not the native payload that executes. Gate 4
  # now performs the REAL payload-sha comparison via the SAME helper the
  # runtime hook uses (`check_pair_rail.py verify_codex_payload()`), so
  # the pre-flight and the per-invocation check can never disagree on
  # algorithm or manifest. Exit contract of the helper CLI:
  #   0 = verified; 1 = mismatch/triple-missing (fail-CLOSED);
  #   3 = infra (manifest unreadable, payload unresolvable, ...).
  # The Owner pre-flight is strict: ANY non-zero fails the gate — an
  # infra arm at pre-flight means the pin ceremony is incomplete.
  echo "  Gate 4b: ADR-182 payload-pin verification (codex-cli-pin-manifest.json)"
  PIN_MANIFEST=".claude/governance/codex-cli-pin-manifest.json"
  if [ ! -f "$PIN_MANIFEST" ]; then
    echo "  FAIL: $PIN_MANIFEST missing (ADR-182 deliverable)"
    exit 1
  fi
  set +e
  PIN_JSON=$(python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$CODEX_PATH")
  PIN_RC=$?
  set -e
  echo "  verify-codex-pin: $PIN_JSON"
  if [ "$PIN_RC" -ne 0 ]; then
    echo "  FAIL: ADR-182 payload-pin verification exited rc=$PIN_RC"
    echo "  (1=sha mismatch / triple missing — possible supply-chain swap;"
    echo "   3=infra — manifest unreadable or payload unresolvable)"
    echo "  If a codex upgrade is legitimate, re-pin via the ADR-182 ceremony."
    echo "  Refusing to exec the unverified codex payload (M4 ordering)."
    exit 1
  fi
  echo "  OK: native payload sha256 matches codex-cli-pin-manifest.json"
fi

# ---- Gate 3b: Codex CLI warm startup (exec) — gated behind Gate 4 on Phase 6 ----
echo ""
echo "Gate 3b: codex --version warm startup"
# Run --version (5s timeout — Codex CLI cold start is typically <2s). On
# Phase 6 this line is reached ONLY after Gate 4 verified the payload sha.
CODEX_VERSION=$(timeout 5 codex --version 2>&1 || echo "TIMEOUT")
if [ "$CODEX_VERSION" = "TIMEOUT" ]; then
  echo "  FAIL: codex --version timed out (>5s)"
  exit 1
fi
echo "  Codex CLI version: $CODEX_VERSION"

echo ""
echo "============================================"
echo "All Phase $PHASE_NUM pre-flight gates PASS"
echo "============================================"
exit 0
