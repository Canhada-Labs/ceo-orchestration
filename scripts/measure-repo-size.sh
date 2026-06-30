#!/usr/bin/env bash
# measure-repo-size.sh — print ceo-orchestration adopter scale tier.
# PLAN-062 Phase 5 — see docs/ADOPTER-SCALE-TIERS.md.
#
# Stdlib only. Works on macOS + Linux. No Python, no npm, nothing.
#
# Usage:
#   bash scripts/measure-repo-size.sh           # measure current repo
#   bash scripts/measure-repo-size.sh /path     # measure given repo
#
# Exit codes:
#   0 — measured successfully (Tier 0/1/2 printed)
#   1 — repo path doesn't exist or is not a directory

REPO_DIR="${1:-$(pwd)}"

if [ ! -d "$REPO_DIR" ]; then
    echo "error: $REPO_DIR is not a directory" >&2
    exit 1
fi

# Counted file extensions — common code + docs + config
EXT_RE='\.(py|ts|tsx|js|jsx|go|rs|java|kt|swift|rb|php|cs|cpp|c|h|hpp|md|yaml|yml|toml)$'

# Excluded directory components (anywhere in path)
EXCLUDE_RE='/(\.git|node_modules|vendor|\.venv|venv|dist|build|__pycache__|\.pytest_cache|target|out)/'

# Use git ls-files if we're in a git repo (respects .gitignore, faster)
# Fall back to find otherwise.
LOC=0
if git -C "$REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # git ls-files path
    FILES=$(git -C "$REPO_DIR" ls-files 2>/dev/null \
            | grep -E "$EXT_RE" 2>/dev/null \
            | grep -vE "$EXCLUDE_RE" 2>/dev/null \
            || true)
    if [ -n "$FILES" ]; then
        # Count lines via xargs with absolute paths
        LOC=$(echo "$FILES" \
              | sed "s|^|$REPO_DIR/|" \
              | xargs wc -l 2>/dev/null \
              | awk '/total/ {sum += $1} {last = $1} END {print (sum > 0 ? sum : last+0)}')
    fi
else
    # find fallback
    FILES=$(find "$REPO_DIR" -type f 2>/dev/null \
            | grep -E "$EXT_RE" 2>/dev/null \
            | grep -vE "$EXCLUDE_RE" 2>/dev/null \
            || true)
    if [ -n "$FILES" ]; then
        LOC=$(echo "$FILES" \
              | xargs wc -l 2>/dev/null \
              | awk '/total/ {sum += $1} {last = $1} END {print (sum > 0 ? sum : last+0)}')
    fi
fi

LOC=${LOC:-0}

# Estimate tokens (1 LoC ≈ 8-12 tokens for typical code mix; use 10 as midpoint)
TOKENS_EST=$((LOC * 10))

# Tier classification
if [ "$LOC" -lt 50000 ]; then
    TIER="0 (Vibecoder solo)"
    RECMD="Core only. Skip sidecar. Skip HyDE."
elif [ "$LOC" -lt 1000000 ]; then
    TIER="1 (Lightweight Enterprise)"
    RECMD="Install LightRAG sidecar. HyDE optional (yes if multi-skill team)."
else
    TIER="2 (Heavy Enterprise)"
    RECMD="Sidecar mandatory. HyDE recommended. Build org extensions."
fi

# Format LoC with thousand separators (POSIX-portable; fall back to plain).
# Note: printf "%'d" depends on LC_ALL / LC_NUMERIC. Under LC_ALL=POSIX or
# LC_ALL=C the separators silently drop (output is unformatted but valid).
# This is acceptable degradation; ADOPTER-SCALE-TIERS.md docs the formatted
# variant. To force separators on macOS: export LC_ALL=en_US.UTF-8
LOC_FMT=$(printf "%'d\n" "$LOC" 2>/dev/null || echo "$LOC")
TOKENS_FMT=$(printf "%'d\n" "$TOKENS_EST" 2>/dev/null || echo "$TOKENS_EST")

cat <<EOF
=== ceo-orchestration scale tier check ===
Repo: $REPO_DIR

Counted: .py .ts .tsx .js .jsx .go .rs .java .kt .swift
         .rb .php .cs .cpp .c .h .hpp .md .yaml .yml .toml
Excluded: .git/ node_modules/ vendor/ .venv/ venv/ dist/ build/
          __pycache__/ .pytest_cache/ target/ out/

LoC (best effort, includes blanks/comments): $LOC_FMT
Estimated tokens (~10 tok/LoC):              ~$TOKENS_FMT

→ Tier: $TIER
→ Recommendation: $RECMD

See docs/ADOPTER-SCALE-TIERS.md for the full per-tier checklist.
EOF
