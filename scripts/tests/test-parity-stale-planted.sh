#!/usr/bin/env bash
# PLAN-163 T1.8 — planted-fixture positive control for the STALE_RE scan in
# scripts/local/smoke-install-parity.sh (FOLLOWUP planted-fixture pattern:
# a known-bad INPUT the scanner MUST flag, so a born-green pattern addition
# is proven effective instead of assumed).
#
# Why: `claude-opus-4-1` retires 2026-08-05 (model-deprecations.json fuse)
# and is born-green in the live tree — zero non-exempt hits today — so
# adding it to STALE_RE cannot be proven by the live scan alone. This test
# EXTRACTS STALE_RE / EXEMPT_PATH_RE / ALLOWLIST_RE from the LIVE parity
# script (so it tracks future edits, never a stale copy), replicates the
# scan_stale_literals file-level pipeline over a temp tree, and asserts:
#
#   1. planted claude-opus-4-1 at a non-exempt path IS flagged (red path —
#      this assertion FAILED before PLAN-163 added the id to STALE_RE)
#   2. planted claude-opus-4-7 at a non-exempt path IS flagged (extraction
#      sanity control — guards against a vacuous regex extraction)
#   3. planted claude-opus-4-1 in a test_*.py file is EXEMPT (path class)
#   4. planted claude-opus-4-1 in an ALLOWLIST_RE by-design carrier
#      (.claude/scripts/ceo-cost.py) is exempt (per-file allowlist)
#   5. current-fleet id claude-opus-4-8 is NOT flagged (no overmatch)
#
# Allowlist-delta audit (enumerated BEFORE the STALE_RE edit, then
# corrected by a live-fire run of the full parity script, 2026-07-28):
#   - .claude/scripts/model-deprecations.json — carries opus-4-1 literals by
#     design, but is NOT shipped by install.sh (the .claude/scripts glob
#     installs *.sh/*.py/*.yaml only) and is not under templates/ — outside
#     the parity scan scope; the checker's own 'deprecation-instrument'
#     inert rule covers it repo-side. NO delta needed (live-fire confirmed).
#   - .claude/scripts/check-model-deprecations.py — the matcher is
#     ledger-driven, but the build_matcher DOCSTRING carries opus-4-1
#     literals and the file IS installed. The static audit called this "no
#     delta"; the live-fire run refuted that → ALLOWLIST_RE delta applied
#     (deprecation instrument, same class as the ledger's inert rule).
#   - .claude/data/canonical_models.json — carries opus-4-1 historical
#     rate-card rows, but .claude/data/ is not installed and not under
#     templates/; repo-side it is covered by the ledger's
#     'by-design-id-carriers' inert rule. NO delta needed (live-fire
#     confirmed).
#   - (adjacent, caught by the same live-fire run: security-and-auth
#     references/owasp.md carries a claude-opus-4-7 measurement anchor —
#     a LATENT pre-existing offender, the PLAN-153 skill import postdates
#     the scan's authoring — allowlisted with the other security-and-auth
#     instructional carriers.)
#
# Exit 0 = all five assertions hold. Exit 1 = at least one failed.
# bash-3.2-safe; no network; writes only under mktemp.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
PARITY="$REPO_ROOT/scripts/local/smoke-install-parity.sh"

FAIL=0
fail() { echo "FAIL: $*" >&2; FAIL=1; }
ok()   { echo "  ok: $*"; }

# --- 1. Extract the LIVE regexes (single-quoted assignments) ---------------
extract_var() {
  # $1 = variable name; prints the single-quoted RHS or empty.
  sed -n "s/^$1='\(.*\)'\$/\1/p" "$PARITY" | head -1
}
STALE_RE="$(extract_var STALE_RE)"
EXEMPT_PATH_RE="$(extract_var EXEMPT_PATH_RE)"
ALLOWLIST_RE="$(extract_var ALLOWLIST_RE)"

[ -n "$STALE_RE" ]       || { echo "ERROR: STALE_RE not extractable from $PARITY" >&2; exit 1; }
[ -n "$EXEMPT_PATH_RE" ] || { echo "ERROR: EXEMPT_PATH_RE not extractable" >&2; exit 1; }
[ -n "$ALLOWLIST_RE" ]   || { echo "ERROR: ALLOWLIST_RE not extractable" >&2; exit 1; }
echo "==> extracted STALE_RE: $STALE_RE"

# --- 2. Plant the fixture tree ---------------------------------------------
TREE="$(mktemp -d -t ceo-parity-planted-XXXXXX)"
trap 'rm -rf "$TREE"' EXIT

mkdir -p "$TREE/planted" "$TREE/.claude/scripts"
# (1) retiring id at a NON-exempt path — MUST be flagged.
printf 'MODEL = "claude-opus-4-1"  # planted PLAN-163 T1.8 fixture\n' \
  > "$TREE/planted/routing_opus41.py"
# (2) long-stale id at a NON-exempt path — extraction sanity control.
printf 'MODEL = "claude-opus-4-7"  # planted extraction control\n' \
  > "$TREE/planted/routing_opus47.py"
# (3) retiring id inside a test_*.py — path-class EXEMPT.
printf 'PIN = "claude-opus-4-1"  # negative-case fixture pin\n' \
  > "$TREE/test_tier_policy_planted.py"
# (4) retiring id inside a by-design carrier — per-file allowlist exempt.
printf '# historical replay row: claude-opus-4-1\n' \
  > "$TREE/.claude/scripts/ceo-cost.py"
# (4b) the deprecation instrument's docstring (installed file) — the delta
# the live-fire run forced; must stay allowlisted.
printf '"""alias example: claude-opus-4-1 wins longest-first"""\n' \
  > "$TREE/.claude/scripts/check-model-deprecations.py"
# (5) current-fleet id — must never be flagged.
printf 'MODEL = "claude-opus-4-8"\n' > "$TREE/planted/current_fleet.py"

# --- 3. Replicate the scan_stale_literals pipeline (file-level filter) -----
OFFENDERS="$(
  cd "$TREE"
  grep -rlE "$STALE_RE" . 2>/dev/null | while IFS= read -r f; do
    rel="${f#./}"
    if echo "$rel" | grep -Eq "$EXEMPT_PATH_RE"; then continue; fi
    if echo "$rel" | grep -Eq "^($ALLOWLIST_RE)\$"; then continue; fi
    echo "$rel"
  done | sort
)"
echo "==> offenders detected:"
echo "${OFFENDERS:-  (none)}" | sed 's/^/    /'

has_offender() { printf '%s\n' "$OFFENDERS" | grep -qxF "$1"; }

# --- 4. Assertions ---------------------------------------------------------
if has_offender "planted/routing_opus41.py"; then
  ok "claude-opus-4-1 planted at non-exempt path is flagged"
else
  fail "claude-opus-4-1 planted at non-exempt path NOT flagged — STALE_RE is missing the 2026-08-05 retiree"
fi

if has_offender "planted/routing_opus47.py"; then
  ok "claude-opus-4-7 extraction sanity control is flagged"
else
  fail "claude-opus-4-7 control NOT flagged — regex extraction is broken/vacuous"
fi

if has_offender "test_tier_policy_planted.py"; then
  fail "test_*.py fixture pin was flagged — EXEMPT_PATH_RE regressed"
else
  ok "test_*.py fixture pin is exempt (path class)"
fi

if has_offender ".claude/scripts/ceo-cost.py"; then
  fail "by-design carrier ceo-cost.py was flagged — ALLOWLIST_RE regressed"
else
  ok "by-design carrier ceo-cost.py is exempt (per-file allowlist)"
fi

if has_offender ".claude/scripts/check-model-deprecations.py"; then
  fail "deprecation instrument was flagged — its ALLOWLIST_RE entry regressed"
else
  ok "deprecation instrument docstring is exempt (per-file allowlist)"
fi

if has_offender "planted/current_fleet.py"; then
  fail "current-fleet id claude-opus-4-8 was flagged — STALE_RE overmatches"
else
  ok "current-fleet id claude-opus-4-8 is not flagged"
fi

# --------------------------------------------------------------------------
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAIL — planted-fixture positive control did not hold" >&2
  exit 1
fi
echo "RESULT: PASS — STALE_RE catches the planted retiree; exemptions intact"
