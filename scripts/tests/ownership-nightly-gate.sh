#!/usr/bin/env bash
# =============================================================================
# PLAN-168 W1 (AC-5) — the ownership nightly GATE.
#
# Runs the ownership e2e harness and compares the observed RED id set
# against scripts/tests/ownership-expected-reds.txt. ANY set difference fails
# — including shrinkage: deliberate reds are part of the contract
# (CLAUDE.md §4), and an all-green run means the truth table changed, which
# is a reason to STOP, not to celebrate.
#
# This is a separate script (not inline YAML) so it can be exercised by a
# positive control (test-ownership-nightly-gate.sh) — a gate nobody can test
# is a gate nobody has proven (PLAN-167: 8 instrument defects; PLAN-168
# debate r1 QA must-fix 2: describing behavior is not a gate).
#
# rc semantics, explicit by design (codex rail r1 P1):
#   - harness rc >= 2  => harness/infra error, NEVER comparable => gate FAILS
#   - summary line must exist and report HARNESS-ERR=0 (partial output fails)
#   - non-empty expected set REQUIRES harness rc == 1 (its designed status)
#   - empty     expected set REQUIRES harness rc == 0
#   - observed RED set must equal the expected set exactly
#   - any OTHER non-GREEN status (TIMEOUT / ESCAPE / AMBIG) fails OUTRIGHT
#     (codex rail r2 P1): an expected-red id that starts timing out or
#     escaping the target keeps the id set unchanged — comparing ids alone
#     would wave a MORE SEVERE regression through as "same set".
#
# NEVER wire the harness's --map mode into this gate: --map exits 0 over
# failures by design (reporting mode) — a dead gate by construction.
#
# Test seams (positive control only — CI uses the defaults):
#   OWNERSHIP_GATE_HARNESS       command to run instead of the real harness
#   OWNERSHIP_GATE_EXPECTED      expected-reds file to compare against
#   OWNERSHIP_GATE_EXPECTED_ALL  full-id-set file (default: harness --list)
#
# Exit: 0 = set stable. 1 = gate failed (set changed / harness error / vacuous
#       output). 2 = gate usage/infra error (missing expected file).
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

HARNESS="${OWNERSHIP_GATE_HARNESS:-}"
if [[ -z "$HARNESS" ]]; then
  HARNESS="bash '$SCRIPT_DIR/test-ownership-table.sh'"
fi
EXPECTED="${OWNERSHIP_GATE_EXPECTED:-$SCRIPT_DIR/ownership-expected-reds.txt}"

[[ -f "$EXPECTED" ]] || { echo "GATE-ERR: expected-reds file not found: $EXPECTED" >&2; exit 2; }

WORK="$( mktemp -d "${TMPDIR:-/tmp}/own-gate.XXXXXX" )" || exit 2
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT

MAP="$WORK/map.txt"
ERRS="$WORK/err.txt"

rc=0
( cd "$REPO_ROOT" && eval "$HARNESS" ) > "$MAP" 2> "$ERRS" || rc=$?

cat "$MAP"
sed -n '1,40p' "$ERRS" >&2 || true

if [[ "$rc" -ge 2 ]]; then
  echo "GATE-RED: harness returned rc=$rc (harness/infra error — not comparable)" >&2
  exit 1
fi

# The summary line is load-bearing: without it, a run that died mid-table
# would present a truncated (smaller) non-GREEN set that could still match a
# shrunken expectation. HARNESS-ERR must be literally 0.
if ! grep -E '^GREEN=[0-9]+[[:space:]]+RED=[0-9]+[[:space:]]+AMBIG=[0-9]+[[:space:]]+HARNESS-ERR=0$' "$MAP" >/dev/null; then
  echo "GATE-RED: summary line missing or HARNESS-ERR>0 — partial or vacuous output cannot pass" >&2
  exit 1
fi

# The RED-set comparison alone cannot prove the FULL table ran: a run that
# silently skipped every GREEN cell would still present the expected REDs and
# an honest-looking summary (codex pack-review P1). Demand that the observed
# id set equals the TABLE's id set — authority: the harness's own --list
# (which reads the TSV), overridable only by the positive control's seam.
if [[ -n "${OWNERSHIP_GATE_EXPECTED_ALL:-}" ]]; then
  grep -E '^OWN-' "$OWNERSHIP_GATE_EXPECTED_ALL" | LC_ALL=C sort > "$WORK/all-exp.txt"
else
  ( cd "$REPO_ROOT" && bash scripts/tests/test-ownership-table.sh --list ) 2>/dev/null \
    | awk '{print $1}' | grep -E '^OWN-' | LC_ALL=C sort > "$WORK/all-exp.txt"
fi
grep -E '^OWN-[0-9]+[[:space:]]' "$MAP" | awk '{print $1}' | LC_ALL=C sort > "$WORK/all-got.txt"
if [[ ! -s "$WORK/all-exp.txt" ]]; then
  echo "GATE-RED: could not derive the full table id set (--list empty) — cannot certify coverage" >&2
  exit 1
fi
if ! diff -u "$WORK/all-exp.txt" "$WORK/all-got.txt" >/dev/null; then
  echo "GATE-RED: observed cell set != FULL table — a partial run certifies nothing:" >&2
  diff -u "$WORK/all-exp.txt" "$WORK/all-got.txt" | grep -E '^[+-]OWN' | head -10 >&2
  exit 1
fi

# Statuses other than GREEN and RED are never expected and never comparable:
# TIMEOUT / ESCAPE / AMBIG on an EXPECTED-red id would keep the id set intact
# while hiding a more severe regression behind "same set" (codex rail r2 P1).
grep -E '^OWN-[0-9]+[[:space:]]' "$MAP" \
  | awk '$2 != "GREEN" && $2 != "RED" {print $1" "$2}' > "$WORK/other.txt"
if [[ -s "$WORK/other.txt" ]]; then
  echo "GATE-RED: cell(s) in a status that is never acceptable (TIMEOUT/ESCAPE/AMBIG):" >&2
  sed 's/^/  /' "$WORK/other.txt" >&2
  exit 1
fi

grep -E '^OWN-[0-9]+[[:space:]]' "$MAP" \
  | awk '$2 == "RED" {print $1}' | LC_ALL=C sort > "$WORK/got.txt"
grep -E '^OWN-' "$EXPECTED" | LC_ALL=C sort > "$WORK/exp.txt"

if ! diff -u "$WORK/exp.txt" "$WORK/got.txt"; then
  echo "GATE-RED: the RED set CHANGED (shrinkage included: all-green means the table changed — stop and find out why)" >&2
  exit 1
fi

if [[ -s "$WORK/exp.txt" && "$rc" -ne 1 ]]; then
  echo "GATE-RED: rc=$rc but the expected set is non-empty (harness must exit 1 over expected reds)" >&2
  exit 1
fi
if [[ ! -s "$WORK/exp.txt" && "$rc" -ne 0 ]]; then
  echo "GATE-RED: rc=$rc but the expected set is empty (harness must exit 0 when everything is green)" >&2
  exit 1
fi

echo "ownership gate: RED set stable ($(wc -l < "$WORK/exp.txt" | tr -d ' ') expected RED cells, zero TIMEOUT/ESCAPE/AMBIG)"
exit 0
