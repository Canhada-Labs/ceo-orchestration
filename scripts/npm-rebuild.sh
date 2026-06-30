#!/usr/bin/env bash
# =========================================================================
# scripts/npm-rebuild.sh — regenerate the npm/ bundle from canonical sources.
#
# Closes Session 75 Codex Finding 3 + Owner D1 lock (2026-04-29):
# the `npm/` directory is GENERATED, not hand-edited. Source-of-truth is
# the canonical `.claude/`, `templates/`, `SPEC/v1/`, `VERSION` at the
# repo root. CI gate `verify-npm-bundle-sync` enforces this.
#
# What it does:
#   1. Validate working tree clean enough to compare hashes.
#   2. Rsync .claude/hooks/ + .claude/scripts/ into npm/.claude/.
#   3. Rsync templates/ into npm/templates/.
#   4. Rsync SPEC/v1/ into npm/SPEC/v1/.
#   5. Copy VERSION → npm/VERSION (so the two files are bit-identical).
#   6. Rewrite npm/package.json `version` field to match VERSION via jq
#      (or a Python fallback if jq is missing).
#   7. Smoke-pack via `npm pack --dry-run` if `npm` is available.
#
# Usage:
#   bash scripts/npm-rebuild.sh
#
# Exit codes:
#   0 — bundle in sync
#   1 — rsync / copy failure
#   2 — version-bump failure
#   3 — npm-pack smoke failure
# =========================================================================

set -u
set -o pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

GRN=$'\033[0;32m'; RED=$'\033[0;31m'; YLW=$'\033[0;33m'; BLU=$'\033[0;34m'; RST=$'\033[0m'
info() { echo "${BLU}[*]${RST} $*"; }
ok()   { echo "${GRN}[OK]${RST} $*"; }
warn() { echo "${YLW}[!]${RST} $*"; }
fail() { echo "${RED}[X]${RST} $*" >&2; }

if [ ! -f VERSION ]; then
  fail "VERSION file missing — run from repo root"
  exit 1
fi
if [ ! -d npm ]; then
  fail "npm/ directory missing — run from repo root"
  exit 1
fi

VERSION="$(tr -d '[:space:]' < VERSION)"
info "Rebuilding npm/ bundle for VERSION=$VERSION"

# ---------------------------------------------------------------------
# Rsync canonical .claude/{hooks,scripts} → npm/.claude/
# Exclude pytest cache, .coverage, *.bak, *.pyc, __pycache__.
#
# PLAN-119-FOLLOWUP WS-1: `--delete-excluded` removes excluded items that are
# ALREADY in the destination from a prior run. Plain `--delete-after` only
# deletes dest items absent from source AND not excluded — so stale
# `__pycache__/`/`*.pyc` that entered the bundle before these excludes existed
# would otherwise persist forever (perf debate R-PERF4).
# ---------------------------------------------------------------------
RSYNC_FLAGS=(-a --delete-after --delete-excluded
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='.pytest_cache/'
  --exclude='.coverage' --exclude='*.bak' --exclude='*.bak.*')

mkdir -p npm/.claude

# ---------------------------------------------------------------------
# PLAN-119-FOLLOWUP WS-1 — prune stale out-of-scope subtrees under npm/.claude/.
# `npm/.claude/` is gitignored build state. `npm-rebuild.sh` only owns
# hooks/+scripts/, but a prior `install-npm.sh` (`cp -r .claude`) can leave a
# multi-GB `npm/.claude/plans/` here. `npm pack --dry-run` (below) STATs the
# whole tree to apply `.npmignore`, so a stale 4.3GB / 250k-file plans/ makes
# the smoke take ~430s and times out the dev-env test (CI starts clean, so it
# passes there — a structural parity gap). plans/ is gitignored,
# `.npmignore`-excluded from the shipped tarball, and never synced — pruning it
# is safe and is the real root-cause fix (perf debate R-PERF1/Must-fix-2).
NPM_CLAUDE_PLANS="$REPO/npm/.claude/plans"
if [ -n "${REPO:-}" ] && [ -d "$NPM_CLAUDE_PLANS" ]; then
  info "Pruning stale out-of-scope npm/.claude/plans (not part of the bundle)"
  rm -rf "$NPM_CLAUDE_PLANS"
  ok "stale npm/.claude/plans pruned"
fi

info "Syncing .claude/hooks → npm/.claude/hooks"
rsync "${RSYNC_FLAGS[@]}" .claude/hooks/ npm/.claude/hooks/ || { fail "hooks rsync failed"; exit 1; }
ok ".claude/hooks synced"

info "Syncing .claude/scripts → npm/.claude/scripts"
rsync "${RSYNC_FLAGS[@]}" .claude/scripts/ npm/.claude/scripts/ || { fail "scripts rsync failed"; exit 1; }
ok ".claude/scripts synced"

info "Syncing templates → npm/templates"
rsync "${RSYNC_FLAGS[@]}" templates/ npm/templates/ || { fail "templates rsync failed"; exit 1; }
ok "templates synced"

info "Syncing SPEC/v1 → npm/SPEC/v1"
mkdir -p npm/SPEC
rsync "${RSYNC_FLAGS[@]}" SPEC/v1/ npm/SPEC/v1/ || { fail "SPEC rsync failed"; exit 1; }
ok "SPEC/v1 synced"

# ---------------------------------------------------------------------
# Copy VERSION → npm/VERSION (bit-identical).
# ---------------------------------------------------------------------
cp -f VERSION npm/VERSION || { fail "VERSION copy failed"; exit 1; }
ok "npm/VERSION = $VERSION"

# ---------------------------------------------------------------------
# Rewrite npm/package.json version field.
# ---------------------------------------------------------------------
if command -v jq >/dev/null 2>&1; then
  tmp="$(mktemp -t npm-pkg-XXXXXX.json)"
  jq --arg v "$VERSION" '.version = $v' npm/package.json > "$tmp" \
    && mv "$tmp" npm/package.json \
    || { fail "jq package.json bump failed"; rm -f "$tmp"; exit 2; }
else
  python3 - "$VERSION" <<'PY' || { fail "python package.json bump failed"; exit 2; }
import json, sys, pathlib
v = sys.argv[1]
p = pathlib.Path("npm/package.json")
data = json.loads(p.read_text(encoding="utf-8"))
data["version"] = v
p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
fi
ok "npm/package.json version = $VERSION"

# ---------------------------------------------------------------------
# Optional: npm-pack smoke (catches obvious package errors before publish).
# ---------------------------------------------------------------------
if command -v npm >/dev/null 2>&1; then
  info "Running npm pack --dry-run smoke"
  pack_json="$( (cd npm && npm pack --dry-run --json 2>/dev/null) )"
  pack_rc=$?
  if [ "$pack_rc" -ne 0 ]; then
    fail "npm pack --dry-run failed"
    (cd npm && npm pack --dry-run 2>&1 | tail -10)
    exit 3
  fi
  ok "npm pack --dry-run clean"
  # PLAN-119-FOLLOWUP WS-1 — tarball bloat/leak guard (PLAN-118 AC-B8 recurrence),
  # FAIL-CLOSED. A clean bundle is ~2178 files (measured S184, VERSION 1.0.0). A
  # leak of the gitignored .claude/plans/ sandbox (~250k files) — what made the
  # dev-env pack take ~430s — would blow past this. Ceiling 6000 = ~2.75x headroom
  # over the current bundle for legit growth (more skills/ADRs) while staying ~40x
  # below a plans/ leak. Parse the structured `--json` entryCount (robust across
  # npm versions); if the count cannot be determined the guard FAILS rather than
  # silently skipping (Codex 019e73ab P1-B).
  NPM_PACK_FILE_CEILING=6000
  pack_files="$(printf '%s' "$pack_json" | python3 -c 'import sys, json
d = json.load(sys.stdin); o = d[0] if isinstance(d, list) else d; print(int(o["entryCount"]))' 2>/dev/null)"
  if [ -z "$pack_files" ]; then
    fail "could not determine npm pack file count from --json entryCount — failing CLOSED (PLAN-119-FOLLOWUP WS-1 tarball guard)"
    exit 3
  fi
  if [ "$pack_files" -gt "$NPM_PACK_FILE_CEILING" ]; then
    fail "npm pack would ship $pack_files files (> $NPM_PACK_FILE_CEILING ceiling) — a stale .claude/plans/ or other out-of-scope tree likely leaked into the bundle (PLAN-118 AC-B8 / PLAN-119-FOLLOWUP WS-1)."
    exit 3
  fi
  ok "npm pack file count $pack_files within ceiling $NPM_PACK_FILE_CEILING"
else
  warn "npm not installed — skipping pack smoke (CI will catch on publish)"
fi

echo ""
ok "npm/ bundle regenerated. Stage with:"
echo "    git add npm/"
echo "    git diff --stat npm/ | tail -5"
echo ""
warn "Per Owner D1: do NOT hand-edit anything under npm/. Generated only."
