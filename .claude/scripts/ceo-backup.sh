#!/bin/bash
# ceo-backup.sh — snapshot framework state to ~/.ceo-backups/<slug>/
#
# Snapshots:
#   - ${CEO_AUDIT_LOG_DIR:-$HOME/.claude/projects/<slug>}/audit-log.jsonl
#   - same dir's memory/ subtree (auto-memory)
#   - .claude/agent-metrics.md (in-repo)
#   - optionally .claude/plans/ (--include-plans)
#
# Output: ts-named tarball at ~/.ceo-backups/<slug>/ceo-backup-YYYY-MM-DDTHHMMSSZ.tar.gz
#         + sidecar SHA256 file
#
# Rotation policy (default):
#   - keep last 7 daily backups
#   - keep last 4 weekly backups (Sundays)
#   - keep last 3 monthly backups (1st of month)
#
# Stdlib only (tar + sha256sum or shasum -a 256). No third-party deps.
#
# Exit codes:
#   0 — success
#   1 — usage error / no audit log to back up
#   2 — fatal (tar failed, dir unwritable)

set -euo pipefail

DRY_RUN=0
INCLUDE_PLANS=0
QUIET=0
KEEP_DAILY=7
KEEP_WEEKLY=4
KEEP_MONTHLY=3
BACKUP_ROOT_OVERRIDE=""
PROJECT_SLUG_OVERRIDE=""
AUDIT_DIR_OVERRIDE=""

usage() {
  cat <<EOF
ceo-backup.sh — snapshot framework state

Usage:
  ceo-backup.sh [options]

Options:
  --dry-run                Show what would be backed up; create no files
  --include-plans          Include .claude/plans/ in the tarball
  --quiet                  Suppress progress output
  --backup-root <dir>      Override ~/.ceo-backups (default)
  --project-slug <name>    Override project slug detection (default: ceo-orchestration)
  --audit-dir <dir>        Override CEO_AUDIT_LOG_DIR
  --keep-daily <N>         Daily retention (default 7)
  --keep-weekly <N>        Weekly retention (default 4)
  --keep-monthly <N>       Monthly retention (default 3)
  -h, --help               This message

Env vars honored:
  CEO_AUDIT_LOG_DIR        Source dir for audit log + memory
  CEO_PROJECT_NAME         Default project slug
  CEO_BACKUP_ROOT          Default backup destination root
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --include-plans) INCLUDE_PLANS=1; shift ;;
    --quiet) QUIET=1; shift ;;
    --backup-root) BACKUP_ROOT_OVERRIDE="$2"; shift 2 ;;
    --project-slug) PROJECT_SLUG_OVERRIDE="$2"; shift 2 ;;
    --audit-dir) AUDIT_DIR_OVERRIDE="$2"; shift 2 ;;
    --keep-daily) KEEP_DAILY="$2"; shift 2 ;;
    --keep-weekly) KEEP_WEEKLY="$2"; shift 2 ;;
    --keep-monthly) KEEP_MONTHLY="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage >&2; exit 1 ;;
  esac
done

log() {
  if [ "$QUIET" -eq 0 ]; then
    echo "$@" >&2
  fi
  return 0
}

# Resolve project slug
PROJECT_SLUG="${PROJECT_SLUG_OVERRIDE:-${CEO_PROJECT_NAME:-ceo-orchestration}}"

# Resolve audit dir (where audit-log.jsonl + memory/ live)
if [ -n "$AUDIT_DIR_OVERRIDE" ]; then
  AUDIT_DIR="$AUDIT_DIR_OVERRIDE"
else
  AUDIT_DIR="${CEO_AUDIT_LOG_DIR:-$HOME/.claude/projects/$PROJECT_SLUG}"
fi

# Resolve backup root
BACKUP_ROOT="${BACKUP_ROOT_OVERRIDE:-${CEO_BACKUP_ROOT:-$HOME/.ceo-backups}}"
BACKUP_DIR="$BACKUP_ROOT/$PROJECT_SLUG"

log "ceo-backup: source=$AUDIT_DIR slug=$PROJECT_SLUG dest=$BACKUP_DIR"

# Validate source
if [ ! -d "$AUDIT_DIR" ]; then
  echo "warning: audit dir not found: $AUDIT_DIR (nothing to back up)" >&2
  echo "(framework hasn't run yet; this is expected on a fresh install)" >&2
  exit 0
fi

# Resolve sha256 binary (gnu vs mac)
SHA256_BIN=""
if command -v sha256sum >/dev/null 2>&1; then
  SHA256_BIN="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
  SHA256_BIN="shasum -a 256"
else
  echo "fatal: neither sha256sum nor shasum -a 256 available" >&2
  exit 2
fi

# Find adopter project root (CWD walks up looking for .claude/agent-metrics.md or .claude/)
ADOPTER_ROOT=""
cur="$(pwd)"
while [ "$cur" != "/" ]; do
  if [ -d "$cur/.claude" ]; then
    ADOPTER_ROOT="$cur"
    break
  fi
  cur="$(dirname "$cur")"
done

# Build the file list
TS="$(date -u +%Y-%m-%dT%H%M%SZ)"
ARCHIVE_NAME="ceo-backup-$TS.tar.gz"

if [ "$DRY_RUN" -eq 1 ]; then
  log ""
  log "[dry-run] would create: $BACKUP_DIR/$ARCHIVE_NAME"
  log "[dry-run] would include:"
  [ -f "$AUDIT_DIR/audit-log.jsonl" ] && log "  - $AUDIT_DIR/audit-log.jsonl"
  for f in "$AUDIT_DIR"/audit-log-*.jsonl; do
    [ -f "$f" ] && log "  - $f"
  done
  [ -d "$AUDIT_DIR/memory" ] && log "  - $AUDIT_DIR/memory/"
  if [ -n "$ADOPTER_ROOT" ] && [ -f "$ADOPTER_ROOT/.claude/agent-metrics.md" ]; then
    log "  - $ADOPTER_ROOT/.claude/agent-metrics.md"
  fi
  if [ "$INCLUDE_PLANS" -eq 1 ] && [ -n "$ADOPTER_ROOT" ] && [ -d "$ADOPTER_ROOT/.claude/plans" ]; then
    log "  - $ADOPTER_ROOT/.claude/plans/"
  fi
  log ""
  log "[dry-run] retention: keep $KEEP_DAILY daily + $KEEP_WEEKLY weekly + $KEEP_MONTHLY monthly"
  exit 0
fi

mkdir -p "$BACKUP_DIR"

# Stage in a temp dir then tar — atomic produce + verify
STAGE_DIR="$(mktemp -d -t ceo-backup-stage-XXXXXX)"
trap 'rm -rf "$STAGE_DIR"' EXIT

# Layout inside the tarball:
#   audit/audit-log.jsonl
#   audit/audit-log-YYYY-MM.jsonl  (rotated archives)
#   audit/audit-log.errors  (if present)
#   memory/<files>
#   agent-metrics.md  (if present)
#   plans/<files>     (if --include-plans)

if [ -f "$AUDIT_DIR/audit-log.jsonl" ]; then
  mkdir -p "$STAGE_DIR/audit"
  cp -p "$AUDIT_DIR/audit-log.jsonl" "$STAGE_DIR/audit/"
fi
for f in "$AUDIT_DIR"/audit-log-*.jsonl; do
  [ -f "$f" ] || continue
  mkdir -p "$STAGE_DIR/audit"
  cp -p "$f" "$STAGE_DIR/audit/"
done
if [ -f "$AUDIT_DIR/audit-log.errors" ]; then
  mkdir -p "$STAGE_DIR/audit"
  cp -p "$AUDIT_DIR/audit-log.errors" "$STAGE_DIR/audit/"
fi

if [ -d "$AUDIT_DIR/memory" ]; then
  mkdir -p "$STAGE_DIR/memory"
  # Use cp -r to avoid tar streaming surprises with weird filenames
  cp -pR "$AUDIT_DIR/memory/." "$STAGE_DIR/memory/"
fi

if [ -n "$ADOPTER_ROOT" ] && [ -f "$ADOPTER_ROOT/.claude/agent-metrics.md" ]; then
  cp -p "$ADOPTER_ROOT/.claude/agent-metrics.md" "$STAGE_DIR/"
fi

if [ "$INCLUDE_PLANS" -eq 1 ] && [ -n "$ADOPTER_ROOT" ] && [ -d "$ADOPTER_ROOT/.claude/plans" ]; then
  mkdir -p "$STAGE_DIR/plans"
  cp -pR "$ADOPTER_ROOT/.claude/plans/." "$STAGE_DIR/plans/"
fi

# Detect empty stage — bail with explanation
if [ -z "$(ls -A "$STAGE_DIR" 2>/dev/null)" ]; then
  echo "warning: nothing to back up at $AUDIT_DIR" >&2
  exit 0
fi

# Manifest of what's in the tarball
( cd "$STAGE_DIR" && find . -type f | sort > MANIFEST.txt )

# Tar
ARCHIVE_PATH="$BACKUP_DIR/$ARCHIVE_NAME"
( cd "$STAGE_DIR" && tar -czf "$ARCHIVE_PATH" . )

# Sidecar SHA256
SHA_PATH="$ARCHIVE_PATH.sha256"
$SHA256_BIN "$ARCHIVE_PATH" | awk '{print $1}' > "$SHA_PATH"

log "ok: $ARCHIVE_PATH ($(stat -f%z "$ARCHIVE_PATH" 2>/dev/null || stat -c%s "$ARCHIVE_PATH") bytes)"
log "sha256: $(cat "$SHA_PATH")"

# ----- Rotation -----
#
# Group existing backups by intent:
#   - Daily: any backup ≤ KEEP_DAILY days old (most recent N)
#   - Weekly: oldest of each ISO-week, up to KEEP_WEEKLY
#   - Monthly: oldest of each YYYY-MM, up to KEEP_MONTHLY
# Anything else is removed.

# List all backups, newest first
ALL_BACKUPS=()
while IFS= read -r line; do
  [ -n "$line" ] && ALL_BACKUPS+=("$line")
done < <(ls -t "$BACKUP_DIR"/ceo-backup-*.tar.gz 2>/dev/null || true)

if [ "${#ALL_BACKUPS[@]}" -le 1 ]; then
  log "rotation: only ${#ALL_BACKUPS[@]} backup(s) present; nothing to prune"
  exit 0
fi

# bash 3.2 has no associative arrays; use newline-delimited strings as sets
# (keys are fs-safe backup names / week / month tokens — no embedded newlines).
KEEP_LIST=""
# Newest N → daily slot
i=0
for b in "${ALL_BACKUPS[@]}"; do
  [ "$i" -ge "$KEEP_DAILY" ] && break   # check BEFORE appending so --keep-daily 0 keeps zero
  KEEP_LIST="$KEEP_LIST"$'\n'"$b"
  i=$((i+1))
done

# Walk backups and group by week / month
WEEK_KEEP_LIST=""
MONTH_KEEP_LIST=""
WEEK_KEEP_COUNT=0
MONTH_KEEP_COUNT=0
for b in "${ALL_BACKUPS[@]}"; do
  base="$(basename "$b" .tar.gz)"
  # ceo-backup-YYYY-MM-DDTHHMMSSZ
  ts="${base#ceo-backup-}"
  date_part="${ts%T*}"
  # Extract YYYY-MM and YYYY-WNN
  ym="${date_part%-*}"
  case $'\n'"$MONTH_KEEP_LIST"$'\n' in
    *$'\n'"$ym"$'\n'*) : ;; # already have this month
    *)
      if [ "$MONTH_KEEP_COUNT" -lt "$KEEP_MONTHLY" ]; then
        MONTH_KEEP_LIST="$MONTH_KEEP_LIST"$'\n'"$ym"
        MONTH_KEEP_COUNT=$((MONTH_KEEP_COUNT+1))
        KEEP_LIST="$KEEP_LIST"$'\n'"$b"
      fi
      ;;
  esac
  # ISO week
  if command -v gdate >/dev/null 2>&1; then
    iw="$(gdate -d "$date_part" +%G-%V 2>/dev/null || echo "$date_part")"
  else
    # macOS BSD date
    iw="$(date -j -f "%Y-%m-%d" "$date_part" +%G-%V 2>/dev/null || echo "$date_part")"
  fi
  case $'\n'"$WEEK_KEEP_LIST"$'\n' in
    *$'\n'"$iw"$'\n'*) : ;; # already have this week
    *)
      if [ "$WEEK_KEEP_COUNT" -lt "$KEEP_WEEKLY" ]; then
        WEEK_KEEP_LIST="$WEEK_KEEP_LIST"$'\n'"$iw"
        WEEK_KEEP_COUNT=$((WEEK_KEEP_COUNT+1))
        KEEP_LIST="$KEEP_LIST"$'\n'"$b"
      fi
      ;;
  esac
done

# Prune
PRUNED=0
for b in "${ALL_BACKUPS[@]}"; do
  case $'\n'"$KEEP_LIST"$'\n' in
    *$'\n'"$b"$'\n'*) : ;; # keep
    *)
      rm -f "$b" "$b.sha256"
      PRUNED=$((PRUNED+1))
      ;;
  esac
done

# KEEP_LIST may list a backup twice (daily slot + week/month rep); dedup for the count.
# Use `awk 'NF'` (not `grep .`) to drop blank lines: grep exits 1 on an all-empty list
# (e.g. --keep-daily/weekly/monthly all 0), which would abort the script under
# `set -euo pipefail` before the final log/exit; awk exits 0 and yields a count of 0.
KEPT_COUNT="$(printf '%s\n' "$KEEP_LIST" | awk 'NF' | sort -u | wc -l | tr -d ' ')"
log "rotation: kept $KEPT_COUNT, pruned $PRUNED"
exit 0
