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

_physical_dest() {
  local raw="$1" parent leaf
  case "$raw" in
    *//*|*/./*|*/../*|../*|.)
      echo "fatal: refused destination spelling: $raw" >&2; return 1 ;;
  esac
  parent="$(dirname "$raw")"
  leaf="$(basename "$raw")"
  if [ -e "$raw" ] || [ -L "$raw" ]; then
    [ -d "$raw" ] && [ ! -L "$raw" ] || {
      echo "fatal: destination must be a real directory, not a link or file" >&2; return 1;
    }
    (cd -P "$raw" && pwd)
    return 0
  fi
  [ -d "$parent" ] && [ ! -L "$parent" ] || {
    echo "fatal: destination parent must be a real directory" >&2; return 1;
  }
  printf '%s/%s\n' "$(cd -P "$parent" && pwd)" "$leaf"
}

ARCHIVE_VALIDATOR="$(dirname "${BASH_SOURCE[0]}")/_restore_archive.py"
[ -f "$ARCHIVE_VALIDATOR" ] || { echo "fatal: archive validator missing" >&2; exit 2; }
python3 "$ARCHIVE_VALIDATOR" "$TARBALL" || exit 2
DEST="$(_physical_dest "$DEST")" || exit 2

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

# Validate the exact tree that both preview and apply describe.  This is before
# the dry-run return deliberately: preview must never bless an apply it rejects.
if [ "$RESTORE_AGENT_METRICS" -eq 1 ] || [ "$RESTORE_PLANS" -eq 1 ]; then
  if [ -L "$(pwd)/.claude" ] || [ ! -d "$(pwd)/.claude" ]; then
    echo "fatal: optional restore requires a real .claude directory in CWD" >&2
    exit 2
  fi
  if [ "$RESTORE_PLANS" -eq 1 ] && [ -L "$(pwd)/.claude/plans" ]; then
    echo "fatal: optional plans restore requires a real .claude/plans directory" >&2
    exit 2
  fi
fi
STAGE_DIR="$(mktemp -d -t ceo-restore-XXXXXX)"
trap 'rm -rf "$STAGE_DIR"' EXIT
tar -xzf "$TARBALL" -C "$STAGE_DIR" --no-same-owner --no-same-permissions
if find "$STAGE_DIR" -type l -print -quit | grep -q .; then
  echo "fatal: archive contains symbolic links" >&2
  exit 2
fi

# List contents (dry-run preview)
log ""
log "tarball contents:"
if [ "$QUIET" -eq 0 ]; then
  tar -tzf "$TARBALL" | sed -n '1,50{s/^/  /;p;}' >&2
fi

_refuse_link_ancestors() {
  local path="$1" stop="$2"
  if [ -L "$path" ]; then
    echo "fatal: restore target is a symbolic link: $path" >&2
    return 2
  fi
  if [ -e "$path" ] && [ ! -f "$path" ]; then
    echo "fatal: restore target must be a regular file: $path" >&2
    return 2
  fi
  while [ "$path" != "$stop" ]; do
    if [ -L "$path" ]; then
      echo "fatal: restore target is a symbolic link: $path" >&2
      return 2
    fi
    path="$(dirname "$path")"
  done
}

_preflight_targets() {
  local f rel target
  if [ -d "$STAGE_DIR/audit" ]; then
    for f in "$STAGE_DIR/audit"/*; do
      [ -f "$f" ] || continue
      _refuse_link_ancestors "$DEST/$(basename "$f")" "$DEST" || return 2
    done
  fi
  if [ -d "$STAGE_DIR/memory" ]; then
    while IFS= read -r -d '' f; do
      rel="${f#"$STAGE_DIR/memory/"}"
      target="$DEST/memory/$rel"
      _refuse_link_ancestors "$target" "$DEST" || return 2
    done < <(find "$STAGE_DIR/memory" -type f -print0)
  fi
  if [ "$RESTORE_AGENT_METRICS" -eq 1 ] && [ -f "$STAGE_DIR/agent-metrics.md" ]; then
    _refuse_link_ancestors "$(pwd)/.claude/agent-metrics.md" "$(pwd)" || return 2
  fi
  if [ "$RESTORE_PLANS" -eq 1 ] && [ -d "$STAGE_DIR/plans" ]; then
    while IFS= read -r -d '' f; do
      rel="${f#"$STAGE_DIR/plans/"}"
      _refuse_link_ancestors "$(pwd)/.claude/plans/$rel" "$(pwd)" || return 2
    done < <(find "$STAGE_DIR/plans" -type f -print0)
  fi
}

_preflight_targets || exit 2

if [ "$APPLY" -eq 0 ]; then
  log ""
  log "[dry-run] no files modified."
  log "[dry-run] re-run with --apply to commit (will prompt unless --force)."
  exit 0
fi

# ----- APPLY -----
if [ "$FORCE" -ne 1 ]; then
  read -r -p "Proceed with restore into $DEST? [yes/no] " ANSWER
  [ "$ANSWER" = "yes" ] || { echo "aborted."; exit 1; }
fi
mkdir -p "$DEST"

# Restore audit/
if [ -d "$STAGE_DIR/audit" ]; then
  for f in "$STAGE_DIR/audit"/*; do
    [ -f "$f" ] && [ ! -L "$f" ] || continue
    cp -p -- "$f" "$DEST/$(basename "$f")"
  done
  log "restored: audit/ → $DEST/"
fi

# Restore memory/
if [ -d "$STAGE_DIR/memory" ]; then
  mkdir -p "$DEST/memory"
  while IFS= read -r -d '' f; do
    rel="${f#"$STAGE_DIR/memory/"}"
    mkdir -p "$DEST/memory/$(dirname "$rel")"
    cp -p -- "$f" "$DEST/memory/$rel"
  done < <(find "$STAGE_DIR/memory" -type f -print0)
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
    while IFS= read -r -d '' f; do
      rel="${f#"$STAGE_DIR/plans/"}"
      mkdir -p "$(pwd)/.claude/plans/$(dirname "$rel")"
      cp -p -- "$f" "$(pwd)/.claude/plans/$rel"
    done < <(find "$STAGE_DIR/plans" -type f -print0)
    log "restored: plans/ → $(pwd)/.claude/plans/"
  else
    log "warning: no .claude/ in CWD; plans/ not restored"
  fi
fi

log ""
log "restore complete."
exit 0
