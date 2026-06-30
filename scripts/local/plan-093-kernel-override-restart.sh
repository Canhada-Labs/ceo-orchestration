#!/usr/bin/env bash
# PLAN-093 Wave A + C kernel-override + Claude.app restart helper (v2).
#
# Run this OUTSIDE Claude.app (in any Terminal/iTerm window). Sets the
# `CEO_KERNEL_OVERRIDE` + `CEO_KERNEL_OVERRIDE_ACK` env vars via
# `launchctl setenv` so GUI Claude.app inherits them on next launch,
# then fully terminates + reopens Claude.app.
#
# v2 changes (S123): adds aggressive quit (osascript + pkill loop with
# timeout) + post-launch verification + safety prompts so a stale GUI
# process doesn't sneak through.
#
# After Claude reopens, /resume this session and type "ok env" — CEO
# resumes Wave A.2 coverage.yml + Wave C kernel edits in batch.
#
# Cleanup: run with `--unset` to remove the launchctl env vars after
# PLAN-093 ships (or rely on reboot).

set -euo pipefail

OVERRIDE_SLUG="plan-093-wave-a-c-execute"
ACK_TOKEN="I-ACCEPT"

if [[ "${1:-}" == "--unset" ]]; then
    echo "Unsetting launchctl env vars..."
    launchctl unsetenv CEO_KERNEL_OVERRIDE 2>/dev/null || true
    launchctl unsetenv CEO_KERNEL_OVERRIDE_ACK 2>/dev/null || true
    echo "  Done. Restart Claude.app to fully clear."
    exit 0
fi

echo "PLAN-093 kernel-override + Claude.app restart (v2)"
echo "==================================================="
echo ""

echo "[1/5] Setting launchctl env vars (GUI scope)..."
launchctl setenv CEO_KERNEL_OVERRIDE "$OVERRIDE_SLUG"
launchctl setenv CEO_KERNEL_OVERRIDE_ACK "$ACK_TOKEN"

CHECK_OVR=$(launchctl getenv CEO_KERNEL_OVERRIDE || echo "")
CHECK_ACK=$(launchctl getenv CEO_KERNEL_OVERRIDE_ACK || echo "")
if [[ "$CHECK_OVR" != "$OVERRIDE_SLUG" ]] || [[ "$CHECK_ACK" != "$ACK_TOKEN" ]]; then
    echo "  ERROR: launchctl setenv did not stick" >&2
    echo "  Got CEO_KERNEL_OVERRIDE='$CHECK_OVR' CEO_KERNEL_OVERRIDE_ACK='$CHECK_ACK'" >&2
    exit 1
fi
echo "  CEO_KERNEL_OVERRIDE     = $CHECK_OVR"
echo "  CEO_KERNEL_OVERRIDE_ACK = $CHECK_ACK"

echo ""
echo "[2/5] Aggressively quitting Claude.app + Electron helpers..."
osascript -e 'tell application "Claude" to quit' 2>/dev/null || true
sleep 3

# Loop pkill — Electron apps have helper processes that respawn.
QUIT_ATTEMPTS=0
while pgrep -ix "claude" >/dev/null 2>&1 && [[ $QUIT_ATTEMPTS -lt 10 ]]; do
    QUIT_ATTEMPTS=$((QUIT_ATTEMPTS + 1))
    echo "  Attempt $QUIT_ATTEMPTS: killing remaining Claude processes..."
    pkill -ix "claude" 2>/dev/null || true
    sleep 1
done

# Final check + force-kill helpers
pkill -if "Claude Helper" 2>/dev/null || true
pkill -if "Electron Framework" 2>/dev/null || true
sleep 1

if pgrep -ix "claude" >/dev/null 2>&1; then
    echo "  WARNING: Claude processes still present after $QUIT_ATTEMPTS attempts" >&2
    echo "  Open Activity Monitor and force-quit Claude.app manually." >&2
    echo ""
    echo "  Aborting auto-restart. Continue manually:" >&2
    echo "    1. Activity Monitor → Force Quit all 'Claude' rows" >&2
    echo "    2. open -a Claude" >&2
    echo "    3. /resume this session and type 'ok env'" >&2
    exit 2
fi
echo "  All Claude processes terminated."

echo ""
echo "[3/5] Reopening Claude.app (will inherit launchctl env)..."
open -a Claude
sleep 2

echo ""
echo "[4/5] Verifying Claude.app launched..."
LAUNCH_ATTEMPTS=0
while ! pgrep -ix "claude" >/dev/null 2>&1 && [[ $LAUNCH_ATTEMPTS -lt 10 ]]; do
    LAUNCH_ATTEMPTS=$((LAUNCH_ATTEMPTS + 1))
    sleep 1
done

if ! pgrep -ix "claude" >/dev/null 2>&1; then
    echo "  ERROR: Claude.app did not launch after 10s" >&2
    echo "  Open manually: open -a Claude" >&2
    exit 3
fi
echo "  Claude.app running."

echo ""
echo "[5/5] State persisted on disk:"
echo "  - Memory:    ~/.claude/projects/-Users-devuser-ceo-orchestration/memory/project_session_123_plan_093_handoff.md"
echo "  - Resume:    .claude/plans/PLAN-093/wave-a-c-resume.md"
echo "  - Sentinel:  .claude/plans/PLAN-093/architect/round-2/approved.md(.asc)"
echo "  - MEMORY.md  updated with S123 in-flight entry"
echo ""
echo "Next steps:"
echo "  1. Claude.app should be focused now. If not, click Claude in Dock."
echo "  2. /resume   → pick this PLAN-093 session"
echo "  3. Type: ok env"
echo "  4. CEO verifies env + applies 6 kernel edits + tests + closeout"
echo "  5. Owner does 2 GPG taps (commit + tag v1.26.0)"
echo ""
echo "Done."
