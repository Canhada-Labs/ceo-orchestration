#!/bin/bash
# ceo-restore.sh — restore framework state from a ceo-backup tarball
#
# Usage:
#   ceo-restore.sh <tarball>             # dry-run by default
#   ceo-restore.sh <tarball> --apply     # actually restore
#
# Default mode is DRY-RUN — verifies SHA256 sidecar + lists files
# the apply mode would overwrite.
#
# Apply mode prompts for confirmation unless --force is passed.
#
# Exit codes:
#   0 — success (dry-run lists; apply completed)
#   1 — usage error / SHA mismatch / refused destination
#   2 — fatal (tarball corrupt, no permissions)

set -euo pipefail

TARBALL=""
APPLY=0
FORCE=0
QUIET=0
DEST_OVERRIDE=""
PROJECT_SLUG_OVERRIDE=""
RESTORE_PLANS=0
RESTORE_AGENT_METRICS=0

usage() {
  cat <<EOF
ceo-restore.sh — restore framework state from a ceo-backup tarball

Usage:
  ceo-restore.sh <tarball> [options]

Options:
  --apply                  Commit the restore (default: dry-run)
  --force                  Skip the apply confirmation prompt
  --quiet                  Suppress progress
  --dest <dir>             Restore destination (default: CEO_AUDIT_LOG_DIR or ~/.claude/projects/<slug>)
  --project-slug <name>    Override slug for default dest path
  --restore-plans          Also restore plans/ subdir if present in tarball
  --restore-agent-metrics  Also restore .claude/agent-metrics.md
  -h, --help               This message

The default --dry-run mode:
  - verifies tarball SHA256 against the .sha256 sidecar (if present)
  - lists every file the apply mode would write
  - exits 0 on success; non-zero only on integrity failure

The --apply mode:
  - re-verifies SHA256
  - prompts for confirmation (unless --force)
  - extracts audit/ + memory/ to <dest>
  - extracts agent-metrics.md / plans/ to CWD's .claude/ if --restore-* flags
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --force) FORCE=1; shift ;;
    --quiet) QUIET=1; shift ;;
    --dest) DEST_OVERRIDE="$2"; shift 2 ;;
    --project-slug) PROJECT_SLUG_OVERRIDE="$2"; shift 2 ;;
    --restore-plans) RESTORE_PLANS=1; shift ;;
    --restore-agent-metrics) RESTORE_AGENT_METRICS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --*) echo "unknown flag: $1" >&2; usage >&2; exit 1 ;;
    *)
      if [ -z "$TARBALL" ]; then
        TARBALL="$1"; shift
      else
        echo "extra argument: $1" >&2; usage >&2; exit 1
      fi
      ;;
  esac
done

log() {
  if [ "$QUIET" -eq 0 ]; then
    echo "$@" >&2
  fi
  return 0
}

if [ -z "$TARBALL" ]; then
  echo "error: tarball path required" >&2
  usage >&2
  exit 1
fi

if [ ! -f "$TARBALL" ]; then
  echo "error: tarball not found: $TARBALL" >&2
  exit 1
fi

# The framework SINGLE resolver (ADR-001; PLAN-182 OQ-6, S326). The old
# default slug `ceo-orchestration` named THIS framework, not the adopter: every
# project under one $HOME backed up -- and restored -- the same shared dir.
# `--project-slug` / CEO_PROJECT_NAME stay as EXPLICIT operator overrides;
# nothing is defaulted from a literal. No resolver on disk (partial upgrade)
# => fail loud rather than guess where the state lives.
# `|| true` inside: under `set -e` a failed `cd` (script copied outside a
# framework tree) would abort this assignment SILENTLY, before _resolve_rp can
# print its loud `fatal:`. An empty dir here simply fails the -f test below.
_RP_DIR="$(dirname "${BASH_SOURCE[0]}")/../hooks/_lib"
_RP="$( { cd "$_RP_DIR" 2>/dev/null && pwd; } || printf '%s' "$_RP_DIR" )/runtime_paths.py"
_project_root() {
  # The project the state belongs to (rail r1 P2 + r3 P1):
  #   1. the harness-set CLAUDE_PROJECT_DIR;
  #   2. else walk up from the CWD to the nearest `.claude/` (the resolver
  #      falls back to the CWD, so a call from a SUBDIRECTORY would otherwise
  #      name the subdirectory);
  #   3. else the project this script is INSTALLED in — it lives at
  #      <project>/.claude/scripts/ — because the documented cron entry
  #      (docs/DISASTER-RECOVERY.md) invokes it by absolute path with
  #      CWD=$HOME and no CLAUDE_PROJECT_DIR, where step 2 finds nothing.
  # Nothing at all => failure (never a guessed slug).
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then printf '%s' "$CLAUDE_PROJECT_DIR"; return 0; fi
  # A project is a directory with the framework INSTALL MARKER — not merely a
  # `.claude/` (rail r4 P1): under the documented cron, CWD=$HOME and the
  # user's GLOBAL ~/.claude exists, so a bare `-d .claude` test picked $HOME
  # as the project and the backup targeted the wrong slug with exit 0.
  local cur
  cur="$(pwd)"
  while [ "$cur" != "/" ]; do
    if [ -f "$cur/.claude/.framework-version" ]; then printf '%s' "$cur"; return 0; fi
    cur="$(dirname "$cur")"
  done
  local here
  here="$( { cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd; } || true )"
  if [ -n "$here" ] && [ -d "$here/.claude/scripts" ] && [ -d "$here/.claude/hooks" ]; then printf '%s' "$here"; return 0; fi
  return 1
}
_resolve_rp() {
  if [ ! -f "$_RP" ] || ! command -v python3 >/dev/null 2>&1; then
    echo "fatal: single resolver not found at $_RP (run scripts/upgrade.sh) -- refusing to guess the state dir" >&2
    return 2
  fi
  local root
  root="$(_project_root)" || {
    echo "fatal: no project root (.claude/) above $(pwd) and CLAUDE_PROJECT_DIR unset -- pass --project-slug or run from the project" >&2
    return 2
  }
  python3 "$_RP" --project "$root" "$@"
}

# Resolve destination. An EXPLICIT destination (--dest / CEO_AUDIT_LOG_DIR)
# is honoured without any project discovery (pair-rail r2 P2): the slug is
# only needed by the branch that builds the path from it.
if [ -n "$DEST_OVERRIDE" ]; then
  DEST="$DEST_OVERRIDE"
elif [ -n "${CEO_AUDIT_LOG_DIR:-}" ]; then
  DEST="$CEO_AUDIT_LOG_DIR"
elif [ -n "${PROJECT_SLUG_OVERRIDE:-}${CEO_PROJECT_NAME:-}" ]; then
  # An explicit operator slug names the destination directly under $HOME.
  PROJECT_SLUG="${PROJECT_SLUG_OVERRIDE:-$CEO_PROJECT_NAME}"
  DEST="$HOME/.claude/projects/$PROJECT_SLUG"
else
  DEST="$(_resolve_rp --state-dir)" || exit 2
fi
[ -n "$DEST" ] || { echo "fatal: empty destination" >&2; exit 2; }

log "ceo-restore: tarball=$TARBALL dest=$DEST mode=$([ "$APPLY" -eq 1 ] && echo APPLY || echo DRY-RUN)"

# Resolve sha256 binary
SHA256_BIN=""
if command -v sha256sum >/dev/null 2>&1; then
  SHA256_BIN="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
  SHA256_BIN="shasum -a 256"
fi

# SHA verification
SHA_SIDE="$TARBALL.sha256"
if [ -n "$SHA256_BIN" ] && [ -f "$SHA_SIDE" ]; then
  EXPECTED="$(cat "$SHA_SIDE" | awk '{print $1}')"
  ACTUAL="$($SHA256_BIN "$TARBALL" | awk '{print $1}')"
  if [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "fatal: SHA256 mismatch" >&2
    echo "  expected: $EXPECTED" >&2
    echo "  actual:   $ACTUAL" >&2
    exit 2
  fi
  log "sha256: verified ($ACTUAL)"
else
  log "warning: no .sha256 sidecar found; integrity not verified"
fi

# List contents (dry-run preview)
log ""
log "tarball contents:"
tar -tzf "$TARBALL" | sed 's/^/  /' | (head -50; echo "  ... (use 'tar tzf $TARBALL' for full listing)" 2>/dev/null) | head -52 | tee /tmp/ceo-restore-listing.$$ >/dev/null
[ "$QUIET" -eq 0 ] && cat /tmp/ceo-restore-listing.$$ >&2
rm -f /tmp/ceo-restore-listing.$$

if [ "$APPLY" -eq 0 ]; then
  log ""
  log "[dry-run] no files modified."
  log "[dry-run] re-run with --apply to commit (will prompt unless --force)."
  exit 0
fi

# ----- APPLY -----

# Confirmation
if [ "$FORCE" -ne 1 ]; then
  echo ""
  echo "About to restore tarball INTO:"
  echo "  $DEST/audit/        (overwrites audit-log.jsonl + rotated archives)"
  echo "  $DEST/memory/       (overwrites auto-memory)"
  if [ "$RESTORE_AGENT_METRICS" -eq 1 ]; then
    echo "  $(pwd)/.claude/agent-metrics.md (if present in tarball)"
  fi
  if [ "$RESTORE_PLANS" -eq 1 ]; then
    echo "  $(pwd)/.claude/plans/ (if present in tarball)"
  fi
  echo ""
  read -p "Proceed? [yes/no] " ANSWER
  if [ "$ANSWER" != "yes" ]; then
    echo "aborted."
    exit 1
  fi
fi

mkdir -p "$DEST"

# Stage extract to a temp dir then move
STAGE_DIR="$(mktemp -d -t ceo-restore-XXXXXX)"
trap 'rm -rf "$STAGE_DIR"' EXIT

tar -xzf "$TARBALL" -C "$STAGE_DIR"

# Restore audit/
if [ -d "$STAGE_DIR/audit" ]; then
  for f in "$STAGE_DIR/audit"/*; do
    [ -f "$f" ] || continue
    cp -p "$f" "$DEST/$(basename "$f")"
  done
  log "restored: audit/ → $DEST/"
fi

# Restore memory/
if [ -d "$STAGE_DIR/memory" ]; then
  mkdir -p "$DEST/memory"
  cp -pR "$STAGE_DIR/memory/." "$DEST/memory/"
  log "restored: memory/ → $DEST/memory/"
fi

# Optional: agent-metrics.md
if [ "$RESTORE_AGENT_METRICS" -eq 1 ] && [ -f "$STAGE_DIR/agent-metrics.md" ]; then
  if [ -d "$(pwd)/.claude" ]; then
    cp -p "$STAGE_DIR/agent-metrics.md" "$(pwd)/.claude/agent-metrics.md"
    log "restored: agent-metrics.md → $(pwd)/.claude/agent-metrics.md"
  else
    log "warning: no .claude/ in CWD; agent-metrics.md not restored"
  fi
fi

# Optional: plans/
if [ "$RESTORE_PLANS" -eq 1 ] && [ -d "$STAGE_DIR/plans" ]; then
  if [ -d "$(pwd)/.claude" ]; then
    mkdir -p "$(pwd)/.claude/plans"
    cp -pR "$STAGE_DIR/plans/." "$(pwd)/.claude/plans/"
    log "restored: plans/ → $(pwd)/.claude/plans/"
  else
    log "warning: no .claude/ in CWD; plans/ not restored"
  fi
fi

log ""
log "restore complete."
exit 0
