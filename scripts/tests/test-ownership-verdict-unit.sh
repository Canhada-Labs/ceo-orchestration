#!/usr/bin/env bash
# =============================================================================
# PLAN-167 W2 — UNIT oracle for _ownership_verdict().
#
# The same table, the other half of the contract:
#
#   this script            — does the DECISION match the model?   (milliseconds)
#   test-ownership-table.sh — do the callers OBSERVE the dimensions
#                             correctly and EXECUTE the verdict?  (~25 minutes)
#
# Both are required and they fail for different reasons. A wrong decision shows
# up here; a caller that reads the world wrong, or ignores the verdict it was
# handed, only shows up there.
#
# This one exists because of how PLAN-167 was caused. In S296 the only
# instrument was the slow one, one cell per ~40-minute round — a loop too long
# to converge in. An oracle that answers in milliseconds is what makes
# "drive the map to 100% green" a normal edit-run cycle instead of an
# overnight gamble.
#
# Usage:
#   test-ownership-verdict-unit.sh            every row
#   test-ownership-verdict-unit.sh --only OWN-0013,OWN-0021
#   test-ownership-verdict-unit.sh --quiet    only the summary
#
# Exit: 0 all rows match · 1 at least one mismatch · 2 harness/usage error.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
TSV="$SCRIPT_DIR/ownership_table.tsv"
LIB="$REPO_ROOT/scripts/_framework_manifest_set.sh"

ONLY=""
QUIET=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only)  ONLY="${2:-}"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    -h|--help) sed -n '2,26p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$TSV" ]] || { echo "ERROR: table not found: $TSV" >&2; exit 2; }
[[ -f "$LIB" ]] || { echo "ERROR: library not found: $LIB" >&2; exit 2; }

# shellcheck source=/dev/null
. "$LIB" 2>/dev/null || { echo "ERROR: cannot source $LIB" >&2; exit 2; }
command -v _ownership_verdict >/dev/null 2>&1 || {
  echo "ERROR: _ownership_verdict is not defined in $LIB" >&2
  echo "       (W2 has not landed the function yet)" >&2
  exit 2
}

PASS=0; FAIL=0; SKIPPED=0
SKIP_IDS=""
LINES=""

while IFS=$'\t' read -r id surface prior_record live_type live_content \
      source_has mode ceremony operation skip_requested fault \
      exp_verdict exp_hash origin note; do
  [[ -z "${id:-}" ]] && continue
  case "$id" in \#*|id) continue ;; esac
  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi

  # Rows with an injected fault assert what the CALLER does when it cannot
  # carry out a verdict. That is execution, not decision (round-1 consensus
  # C2), so the pure function has nothing to say about them and the e2e suite
  # covers them. Counted and named, never silently skipped: a suite that goes
  # green by quietly not running rows is the vacuous-gate class.
  if [[ "${fault:-none}" != "none" ]]; then
    SKIPPED=$((SKIPPED+1))
    SKIP_IDS+="$id "
    continue
  fi

  got="$( _ownership_verdict "$surface" "$prior_record" "$live_type" \
            "$live_content" "$source_has" "$mode" "$ceremony" \
            "$operation" "$skip_requested" 2>/dev/null )"
  rc=$?
  exp="$exp_verdict $exp_hash"

  # A non-zero return or unparseable output is a FAILURE, never a skip: a
  # decision function that cannot answer for a legal cell has a hole in it,
  # and a hole that reports as "not applicable" is how a gap stays invisible.
  if [[ $rc -ne 0 || -z "$got" ]]; then
    LINES+="$( printf '%-10s FAIL   exp=%-40s got=<no answer, rc=%s>  %s\n' "$id" "$exp" "$rc" "$origin" )"$'\n'
    FAIL=$((FAIL+1)); continue
  fi

  if [[ "$got" == "$exp" ]]; then
    PASS=$((PASS+1))
    [[ "$QUIET" -eq 1 ]] || LINES+="$( printf '%-10s ok     %-40s %s\n' "$id" "$exp" "$origin" )"$'\n'
  else
    FAIL=$((FAIL+1))
    LINES+="$( printf '%-10s FAIL   exp=%-40s got=%-40s %s\n' "$id" "$exp" "$got" "$origin" )"$'\n'
  fi
done < "$TSV"

printf '%s' "$LINES" | LC_ALL=C sort
echo ""
echo "unit oracle: PASS=$PASS  FAIL=$FAIL  SKIPPED(execution-fault rows)=$SKIPPED"
[[ -n "$SKIP_IDS" ]] && echo "  not decision cells, covered by the e2e: $SKIP_IDS"
[[ "$FAIL" -gt 0 ]] && exit 1
exit 0
