#!/usr/bin/env bash
# =============================================================================
# S313 — UNIT guard for the schema-doc prior-generation pins in upgrade.sh.
#
# upgrade.sh refreshes `.claude/plans/{PLAN,DEBATE}-SCHEMA.md` HASH-GATED:
# only a byte-pristine copy of a KNOWN prior framework generation is
# replaced; anything else is PRESERVED (an adopter edit must never be
# clobbered). "Known" is a hardcoded sha256 list per doc — a closed set
# written by hand. The class this guard closes: a commit changes a schema
# doc and forgets to append the hash of the generation it replaces, so
# every adopter on that generation is left STALE forever and the
# install/upgrade parity e2e turns red on the next run (S313: 996d72b
# changed PLAN-SCHEMA; the v1.2.0/v1.3.0 generation 8ca4f866 was never
# listed — one hash short, two workflows red).
#
# The generation set is DERIVED, never recalled:
#   - the doc's bytes at every release tag `v*` reachable in this clone
#     (the set an adopter could actually have installed), and
#   - when the clone is not shallow, the doc's bytes at every commit that
#     touched it (main-tracking adopters).
# Every enumerated generation whose bytes differ from HEAD's must appear
# in that doc's list. Zero enumerable generations is a SCAFFOLD FAILURE
# (exit 2), never a green skip — CI must fetch the tags first (the
# smoke-install workflow does). Coverage is printed so a reduced set is
# visible, not silent.
#
# Usage:
#   test-schema-generation-pins-unit.sh            check both docs
#   test-schema-generation-pins-unit.sh --quiet    only the summary
#   UPGRADE_SH=<path> overrides the script under test (staged-pack dry runs).
#
# Exit: 0 every generation pinned · 1 at least one unpinned generation
#       · 2 harness/scaffold error (no upgrade.sh, no hasher, no generation).
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# The repo root is the git toplevel of the checkout this script lives in —
# NOT `$SCRIPT_DIR/../..`: a copy of this script inside a staged pack
# (`.claude/plans/PLAN-NNN/staged-*/scripts/tests/`) would otherwise
# resolve to the pack and grade the STAGED upgrade.sh while claiming to
# grade the live one (the S313 dead-negative-control found exactly that).
REPO_ROOT="$( git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null )" \
  || { echo "ERROR: $SCRIPT_DIR is not inside a git checkout" >&2; exit 2; }
UPGRADE_SH="${UPGRADE_SH:-$REPO_ROOT/scripts/upgrade.sh}"
DOCS=".claude/plans/PLAN-SCHEMA.md .claude/plans/DEBATE-SCHEMA.md"

QUIET=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet) QUIET=1; shift ;;
    -h|--help) sed -n '2,33p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$UPGRADE_SH" ]] || { echo "ERROR: upgrade.sh not found: $UPGRADE_SH" >&2; exit 2; }
[[ "$QUIET" -eq 1 ]] || echo "  script under test: $UPGRADE_SH"

# sha256 of stdin — same portability posture as upgrade.sh (_hash_file):
# shasum, else sha256sum, else python3; no hasher = scaffold error.
_hash_stdin() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 | cut -d' ' -f1
  elif command -v sha256sum >/dev/null 2>&1; then sha256sum | cut -d' ' -f1
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
  else return 1; fi
}
printf '' | _hash_stdin >/dev/null 2>&1 || { echo "ERROR: no sha256 hasher available" >&2; exit 2; }

# The pinned list for one doc: every 64-hex token on the
# `_refresh_schema_doc "<doc>" \` call and its backslash-continuation lines.
_pinned_hashes() {
  local doc="$1"
  awk -v doc="$doc" '
    $0 ~ "^[[:space:]]*_refresh_schema_doc[[:space:]]+\"" doc "\"" { grab = 1 }
    grab {
      line = $0
      while (match(line, /[0-9a-f]{64}/)) {
        print substr(line, RSTART, RLENGTH)
        line = substr(line, RSTART + RLENGTH)
      }
      if (line !~ /\\[[:space:]]*$/ && $0 !~ /\\[[:space:]]*$/) grab = 0
    }
  ' "$UPGRADE_SH"
}

SHALLOW=0
[[ "$(git -C "$REPO_ROOT" rev-parse --is-shallow-repository 2>/dev/null)" == "true" ]] && SHALLOW=1

FAIL=0; TOTAL_GENS=0; LINES=""
for doc in $DOCS; do
  head_hash="$(git -C "$REPO_ROOT" show "HEAD:$doc" 2>/dev/null | _hash_stdin)" \
    || { echo "ERROR: cannot read HEAD:$doc" >&2; exit 2; }
  pinned="$(_pinned_hashes "$doc")"
  [[ -n "$pinned" ]] || { echo "ERROR: no _refresh_schema_doc call with a pin list found for $doc in $UPGRADE_SH" >&2; exit 2; }

  # Enumerate refs: release tags always; full file history when not shallow.
  refs="$(git -C "$REPO_ROOT" tag -l 'v[0-9]*' 2>/dev/null)"
  if [[ "$SHALLOW" -eq 0 ]]; then
    refs="$refs
$(git -C "$REPO_ROOT" log --format=%H -- "$doc" 2>/dev/null)"
  fi

  gens=0; unpinned=""; seen=""
  while IFS= read -r ref; do
    [[ -n "$ref" ]] || continue
    h="$(git -C "$REPO_ROOT" show "$ref:$doc" 2>/dev/null | _hash_stdin)" || continue
    [[ -n "$h" ]] || continue
    [[ "$h" == "$head_hash" ]] && continue          # current generation: IDENTICAL branch
    case " $seen " in *" $h "*) continue ;; esac     # same bytes at several refs
    seen="$seen $h"
    gens=$((gens + 1))
    case "$pinned" in
      *"$h"*) LINES="$LINES
  ok    $doc  ${h:0:16}  (@$ref)" ;;
      *) unpinned="$unpinned ${h:0:16}@$ref"; FAIL=1
         LINES="$LINES
  MISS  $doc  ${h:0:16}  (@$ref) — NOT in upgrade.sh pin list" ;;
    esac
  done <<< "$refs"
  TOTAL_GENS=$((TOTAL_GENS + gens))
  LINES="$LINES
  coverage $doc: $gens prior generation(s) enumerated (shallow=$SHALLOW, tags=$(git -C "$REPO_ROOT" tag -l 'v[0-9]*' | wc -l | tr -d ' '))"
done

[[ "$QUIET" -eq 1 ]] || printf '%s\n' "$LINES"
if [[ "$TOTAL_GENS" -eq 0 ]]; then
  echo "SCAFFOLD FAILURE: zero prior generations enumerable (no v* tags fetched and shallow clone) — fetch tags first; this guard did NOT run" >&2
  exit 2
fi
if [[ "$FAIL" -ne 0 ]]; then
  echo "FAIL: schema generation(s) missing from the upgrade.sh pin list — append the sha256 of the replaced generation in the same commit that changes the doc" >&2
  exit 1
fi
echo "OK: every enumerated prior schema generation is pinned in upgrade.sh ($TOTAL_GENS generation(s))"
exit 0
