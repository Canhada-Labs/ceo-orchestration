#!/usr/bin/env bash
# check-doc-skill-paths.sh — PLAN-112-FOLLOWUP-install-md-skill-path W2 —
# broken-skill-path detector for the framework's top-level docs.
#
# Closes finding C6 P1 / F-4.2-install-md-broken-path: INSTALL.md once
# referenced `.claude/skills/ceo-orchestration/SKILL.md` (missing the
# `core/` tier), a user-visible "file not found" in the adopter verify
# step. No CI gate caught it, so it survived undetected. This checker is
# that gate.
#
# It extracts every literal `.claude/skills/<...>SKILL.md` reference from
# INSTALL.md, README.md, and CLAUDE.md and asserts each one either
#   (a) resolves on disk (`test -f`), OR
#   (b) is a documented template placeholder (the extraction char-class
#       already excludes `<`/`>`, so a `<domain>` placeholder can never be
#       emitted as a complete `...SKILL.md` token — defense-in-depth), OR
#   (c) appears in the explicit ALLOWLIST below (the load-bearing escape
#       hatch for any known non-resolving reference).
#
# Prints one line per miss; exits non-zero only when a non-placeholder,
# non-allowlisted path fails to resolve. Exits 0 when all resolve.
#
# Usage:
#   bash .claude/scripts/local/check-doc-skill-paths.sh           # human report + exit code
#   bash .claude/scripts/local/check-doc-skill-paths.sh --quiet   # exit code only
#
# Bash 3.2 portable (macOS default). Mirrors verify-counts.sh style.

set -euo pipefail

# REPO_ROOT defaults to the framework root (3 levels up). Tests/adopters
# may override via CHECK_DOC_SKILL_PATHS_ROOT to scan an alternate tree.
REPO_ROOT="${CHECK_DOC_SKILL_PATHS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"

QUIET=0
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=1 ;;
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *)
      echo "check-doc-skill-paths.sh: unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

# Docs scanned for `.claude/skills/...SKILL.md` literals.
DOCS=(INSTALL.md README.md CLAUDE.md)

# Explicit escape hatch (AC3 load-bearing): exact literal paths that are
# allowed NOT to resolve on disk (e.g. an intentionally-illustrative
# reference). Empty by default — add a path here only with a comment
# justifying why it cannot resolve.
ALLOWLIST=()

# Optional colon-separated extension to the allowlist (adopters / tests),
# e.g. CHECK_DOC_SKILL_PATHS_ALLOWLIST=".claude/skills/foo/SKILL.md:..."
if [ -n "${CHECK_DOC_SKILL_PATHS_ALLOWLIST:-}" ]; then
  _OLD_IFS="$IFS"; IFS=':'
  for _entry in $CHECK_DOC_SKILL_PATHS_ALLOWLIST; do
    [ -n "$_entry" ] && ALLOWLIST+=("$_entry")
  done
  IFS="$_OLD_IFS"
fi

report() {
  [ "$QUIET" -eq 0 ] && printf '%s\n' "$1"
  return 0
}

in_allowlist() {
  local needle="$1" entry
  for entry in "${ALLOWLIST[@]:-}"; do
    [ "$entry" = "$needle" ] && return 0
  done
  return 1
}

MISS=0
CHECKED=0

report "=== check-doc-skill-paths.sh — PLAN-112-FOLLOWUP-install-md-skill-path ==="

for doc in "${DOCS[@]}"; do
  doc_path="$REPO_ROOT/$doc"
  [ -f "$doc_path" ] || { report "  WARN: $doc not found, skipping"; continue; }

  # Extract literals. The char-class excludes `<`/`>` so template
  # placeholders like `<domain>` never produce a complete token.
  while IFS= read -r ref; do
    [ -n "$ref" ] || continue
    CHECKED=$((CHECKED + 1))

    # (b) defense-in-depth: a `<` slipped through somehow → treat as placeholder.
    case "$ref" in
      *"<"*|*">"*) continue ;;
    esac

    # (c) explicit allowlist.
    if in_allowlist "$ref"; then
      continue
    fi

    # (a) must resolve on disk.
    if [ ! -f "$REPO_ROOT/$ref" ]; then
      report "  MISS: $doc references '$ref' — file does not exist on disk"
      MISS=$((MISS + 1))
    fi
  done < <(grep -oE '\.claude/skills/[A-Za-z0-9_./-]*SKILL\.md' "$doc_path" 2>/dev/null | sort -u || true)
done

if [ "$MISS" -eq 0 ]; then
  report "  OK: all $CHECKED skill-path reference(s) resolve (or are placeholders/allowlisted)"
  exit 0
fi

report ""
report "Exit 1: $MISS broken skill-path reference(s). Fix the doc path, or"
report "(if intentionally non-resolving) add it to the ALLOWLIST with a"
report "justifying comment."
exit 1
