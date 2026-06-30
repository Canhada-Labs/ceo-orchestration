#!/bin/bash
# Skill Health Score — checks if skills reference existing code
#
# Usage:
#   bash .claude/scripts/check-skill-health.sh            # local mode (default)
#   bash .claude/scripts/check-skill-health.sh --ci       # CI mode (non-strict)
#   bash .claude/scripts/check-skill-health.sh --strict   # alias for local default
#
# Modes:
#   Default / --strict : stale skills → exit 1 (local authoring gate).
#   --ci               : stale skills → warnings only, exit 0 (CI gate).
#                        Framework skills in this template repo reference
#                        src/*.ts files that exist in target projects but
#                        not here — treating them as errors would fail CI
#                        on every PR. The --ci mode acknowledges this.
#
# Walks all skill tiers (core/, frontend/, domains/*/skills/) and for each
# SKILL.md (or legacy SKILL-frontend.md as fallback) extracts `src/...`
# file references and verifies they exist in the target repo. A skill with
# zero file refs is "pattern-based" (OK).

set -euo pipefail

MODE="strict"
for arg in "$@"; do
  case "$arg" in
    --ci)
      MODE="ci"
      ;;
    --strict)
      MODE="strict"
      ;;
    -h|--help)
      echo "Usage: $0 [--ci|--strict]"
      echo "  --ci      Stale skills are warnings only; exit 0."
      echo "  --strict  Stale skills are errors; exit 1. (default)"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOTAL=0
HEALTHY=0
STALE=0
# V1 inspired_by: validator (PLAN-074 ADJ-B4)
# Use .claude/scripts/ canonical path; fall back to PLAN-074 staging during Wave 0 transition.
FRONTMATTER_VALIDATOR="$REPO_ROOT/.claude/scripts/validate-skill-frontmatter.py"
if [ ! -f "$FRONTMATTER_VALIDATOR" ]; then
  FRONTMATTER_VALIDATOR="$REPO_ROOT/.claude/plans/PLAN-074/staging/validate-skill-frontmatter.py"
fi

echo "=== Skill Health Check (mode: $MODE) ==="
echo "Repo: $REPO_ROOT"
echo ""

check_skill() {
  local skill_dir="$1"
  local tier="$2"
  local skill_name
  skill_name=$(basename "$skill_dir")
  local skill_file="$skill_dir/SKILL.md"
  # Legacy fallback: some skills use SKILL-frontend.md as primary
  if [ ! -f "$skill_file" ] && [ -f "$skill_dir/SKILL-frontend.md" ]; then
    skill_file="$skill_dir/SKILL-frontend.md"
  fi

  if [ ! -f "$skill_file" ]; then
    return
  fi

  TOTAL=$((TOTAL + 1))

  # Extract file paths referenced in the skill (src/... patterns).
  # grep -o exits 1 when no matches (pattern-based skills); tolerate under
  # set -e + pipefail.
  local referenced_files
  referenced_files=$(grep -oE 'src/[a-zA-Z0-9/_.-]+\.(ts|tsx|js|jsx|py|go|rs)' "$skill_file" 2>/dev/null | sort -u || true)

  if [ -z "$referenced_files" ]; then
    HEALTHY=$((HEALTHY + 1))
    echo "  OK: $tier/$skill_name (pattern-based)"
    return
  fi

  local missing=""
  local total_refs=0
  local missing_count=0

  for ref in $referenced_files; do
    total_refs=$((total_refs + 1))
    if [ ! -f "$REPO_ROOT/$ref" ]; then
      missing="$missing $ref"
      missing_count=$((missing_count + 1))
    fi
  done

  if [ "$missing_count" -eq 0 ]; then
    HEALTHY=$((HEALTHY + 1))
    echo "  OK: $tier/$skill_name ($total_refs refs, all exist)"
  else
    STALE=$((STALE + 1))
    if [ "$MODE" = "ci" ]; then
      echo "  WARN: $tier/$skill_name ($missing_count/$total_refs refs missing)"
    else
      echo "  STALE: $tier/$skill_name ($missing_count/$total_refs refs missing)"
    fi
    for m in $missing; do
      echo "    MISSING: $m"
    done
  fi

  # V1 inspired_by: frontmatter validator (PLAN-074 ADJ-B4)
  # Only run when the helper is available (Wave 0 applied or staging path exists).
  if [ -f "$FRONTMATTER_VALIDATOR" ]; then
    set +e
    v1_result=$(python3 "$FRONTMATTER_VALIDATOR" --v1 "$skill_file" 2>&1)
    v1_rc=$?
    set -e
    if [ $v1_rc -ne 0 ]; then
      echo "$v1_result" | sed 's/^/    [V1] /'
    fi
  fi
}

# Walk each tier
if [ -d "$REPO_ROOT/.claude/skills/core" ]; then
  for skill_dir in "$REPO_ROOT/.claude/skills/core/"*/; do
    [ -d "$skill_dir" ] && check_skill "$skill_dir" "core"
  done
fi

if [ -d "$REPO_ROOT/.claude/skills/frontend" ]; then
  for skill_dir in "$REPO_ROOT/.claude/skills/frontend/"*/; do
    [ -d "$skill_dir" ] && check_skill "$skill_dir" "frontend"
  done
fi

if [ -d "$REPO_ROOT/.claude/skills/domains" ]; then
  for domain_dir in "$REPO_ROOT/.claude/skills/domains/"*/; do
    [ -d "$domain_dir" ] || continue
    domain_name=$(basename "$domain_dir")
    if [ -d "${domain_dir}skills" ]; then
      for skill_dir in "${domain_dir}skills/"*/; do
        [ -d "$skill_dir" ] && check_skill "$skill_dir" "domains/$domain_name/skills"
      done
    fi
  done
fi

echo ""
echo "=== Summary ==="
echo "Total skills: $TOTAL"
echo "Healthy: $HEALTHY"
echo "Stale: $STALE"
if [ "$TOTAL" -gt 0 ]; then
  echo "Health score: $HEALTHY/$TOTAL ($(( HEALTHY * 100 / TOTAL ))%)"
fi

if [ "$STALE" -gt 0 ]; then
  echo ""
  if [ "$MODE" = "ci" ]; then
    echo "NOTE (--ci mode): $STALE stale skill(s) reported as warnings only."
    echo "  Framework skills in this template repo may reference src/*.ts paths"
    echo "  that exist in target projects but not here. This is expected."
    echo "  Run without --ci to treat stale as errors."
    exit 0
  else
    echo "ACTION: Update stale skills to reference current file paths"
    echo "  (Or run with --ci to tolerate stale refs in template repos.)"
    exit 1
  fi
fi

exit 0
