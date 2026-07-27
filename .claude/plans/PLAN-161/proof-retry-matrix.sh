#!/usr/bin/env bash
# =============================================================================
# proof-retry-matrix.sh — PLAN-161 C4: extended perf-gate retry truth table.
#
# Cited by the ADR-163 in-place amendment (codex r2 F5). The PLAN-159 matrix
# (wave1-wrapper-matrix-proof.sh) covers only the 2-attempt cases and goes
# stale once C4 lands; THIS matrix covers the amended contract:
#
#   pass@1                                        -> exit 0, probe never runs
#   flake fail@1 + pass@2                         -> exit 0 + ::warning
#   fail both + probe CONTENDED (p50 > 200)       -> exit 1, NO 3rd attempt,
#                                                    "still-contended VM" label
#   fail both + probe UNCONTENDED + pass@3        -> exit 0, probe-gated 3rd
#   fail both + probe UNCONTENDED + fail@3        -> exit 1 (real regression)
#   malformed probe report                        -> CONTENDED (fail-safe)
#   probe timeout (rc 124)                        -> CONTENDED (fail-safe)
#   nonzero probe exit + below-threshold JSON     -> CONTENDED (rc overrides
#                                                    JSON — codex r4 F4)
#   boundary p50 == 200 (threshold is <=)         -> UNCONTENDED
#
# The contention-verdict PARSER runs REAL (codex r3 F4): only the profiler
# subprocess (probe_floor_raw) and run_gate are mocked. Backoffs are exercised
# env-faked via CEO_PERF_GATE_BACKOFF_S=0 (no real sleeps — codex r2 F5).
#
# EXPECTED-RED against HEAD validate.yml (no 3rd-attempt logic there); green
# exclusively against the PLAN-161 W2 STAGED validate.yml:
#   VALIDATE_YML=<staged>/validate.yml bash proof-retry-matrix.sh
# Backward compat: the historical "FAILED on BOTH attempts (rc1=1 rc2=1)"
# marker (grepped by PLAN-159 wave2-regression-proof.sh:134) must survive in
# every both-attempts-failed outcome; 3rd-attempt markers are ADDITIVE.
#
# READ-ONLY on the repo: everything happens in a mktemp dir.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VALIDATE_YML="${VALIDATE_YML:-$REPO/.github/workflows/validate.yml}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP" 2>/dev/null || true' EXIT
say() { printf '\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

say "Extract the step run-block from $VALIDATE_YML (textual, no yaml dependency)"
cp "$VALIDATE_YML" "$TMP/validate.yml"
python3 - "$TMP" <<'PY'
import sys
from pathlib import Path
tmp = Path(sys.argv[1])
lines = (tmp / "validate.yml").read_text().splitlines(keepends=True)
out, taking = [], False
for l in lines:
    if l.rstrip() == "      - name: Run profile-opus-4-7.py --hook-latency (p95/p99 gate)":
        taking = "seek-run"; continue
    if taking == "seek-run":
        assert l.rstrip() == "        run: |", f"unexpected step layout: {l!r}"
        taking = "body"; continue
    if taking == "body":
        if l.strip() == "" or l.startswith("          "):
            out.append(l[10:] if l.startswith("          ") else l)
        else:
            break
assert out, "run block not found"
(tmp / "gate-step.sh").write_text("".join(out))
print(f"  extracted {len(out)} lines")
PY

say "Structural asserts: 3rd-attempt + probe + env-faked backoff present"
grep -q 'contention_probe' "$TMP/gate-step.sh" \
  || die "extracted block has NO contention_probe — running against HEAD? (this proof targets the PLAN-161 STAGED validate.yml)"
grep -q 'probe_floor_raw' "$TMP/gate-step.sh" \
  || die "extracted block lacks probe_floor_raw (parser must be separable from the subprocess for this proof)"
grep -q 'CEO_PERF_GATE_BACKOFF_S' "$TMP/gate-step.sh" \
  || die "extracted block lacks the CEO_PERF_GATE_BACKOFF_S env-faked backoff knob"
grep -q 'run_gate 3' "$TMP/gate-step.sh" \
  || die "extracted block lacks the probe-gated 3rd attempt"

say "Substitute run_gate + probe_floor_raw with recording mocks (parser stays REAL)"
python3 - "$TMP" <<'PY'
import re, sys
from pathlib import Path
tmp = Path(sys.argv[1])
blk = (tmp / "gate-step.sh").read_text()
mock_gate = '''run_gate() {
  local rc_var="MOCK_RC_$1" js_var="MOCK_JSON_$1"
  echo "gate:$1" >> "$MOCK_CALLS"
  if [ "${!js_var}" = "1" ]; then
    echo '{"hooks":{"mock_entry":{"p50_ms":1,"p95_ms":2,"p99_ms":3,"max_ms":4}}}' > "/tmp/hook-latency-attempt-$1.json"
  else
    rm -f "/tmp/hook-latency-attempt-$1.json"
  fi
  return "${!rc_var}"
}
'''
mock_probe = '''probe_floor_raw() {
  echo "probe" >> "$MOCK_CALLS"
  printf '%s' "$MOCK_PROBE_JSON"
  return "$MOCK_PROBE_RC"
}
'''
blk2 = re.sub(r'run_gate\(\) \{\n.*?\n\}\n', mock_gate, blk, count=1, flags=re.S)
assert blk2 != blk, "run_gate mock substitution failed — step layout drifted"
blk3 = re.sub(r'probe_floor_raw\(\) \{\n.*?\n\}\n', mock_probe, blk2, count=1, flags=re.S)
assert blk3 != blk2, "probe_floor_raw mock substitution failed — step layout drifted"
assert "contention_probe()" in blk3, "REAL contention_probe parser must survive the mocks"
(tmp / "gate-step-mocked.sh").write_text(blk3)
print("  mocked (run_gate + probe_floor_raw only; contention_probe parser REAL)")
PY

floor_json() { # $1 = p50 value
  printf '{"schema":"profile-opus-4-7.v1","mode":"floor","subprocess_floor_ms":{"p50":%s,"p95":9.0,"p99":9.0}}' "$1"
}

say "Truth table (backoffs env-faked to 0s)"
run_case() { # label rc1 rc2 rc3 js1 js2 js3 probe_rc probe_json want_exit
  local label="$1" rc1="$2" rc2="$3" rc3="$4" js1="$5" js2="$6" js3="$7"
  local prc="$8" pjson="$9" want="${10}"
  local sf="$TMP/summary-$RANDOM.md"; : > "$sf"
  local calls="$TMP/calls-$RANDOM.log"; : > "$calls"
  set +e
  MOCK_RC_1="$rc1" MOCK_RC_2="$rc2" MOCK_RC_3="$rc3" \
    MOCK_JSON_1="$js1" MOCK_JSON_2="$js2" MOCK_JSON_3="$js3" \
    MOCK_PROBE_RC="$prc" MOCK_PROBE_JSON="$pjson" MOCK_CALLS="$calls" \
    CEO_PERF_GATE_BACKOFF_S=0 \
    GITHUB_STEP_SUMMARY="$sf" bash "$TMP/gate-step-mocked.sh" > "$TMP/case-out.log" 2>&1
  local got=$?
  set -e
  [ "$got" -eq "$want" ] || { cat "$TMP/case-out.log" >&2; die "[$label] exit=$got want=$want"; }
  echo "  OK [$label] exit=$got"
  LAST_SUMMARY="$sf"; LAST_LOG="$TMP/case-out.log"; LAST_CALLS="$calls"
}

# 1. pass@1 — no probe, no attempts 2/3.
run_case "pass@1" 0 0 0 1 1 1 0 "$(floor_json 1.0)" 0
grep -q "attempt 1: mock_entry" "$LAST_SUMMARY" || die "pass@1: attempt-1 percentiles missing"
grep -q "probe" "$LAST_CALLS" && die "pass@1: probe ran without a double failure"
grep -q "gate:2" "$LAST_CALLS" && die "pass@1: attempt 2 ran after a pass"

# 2. flake fail@1 pass@2 — warning, still no probe.
run_case "flake fail@1 pass@2" 1 0 0 1 1 1 0 "$(floor_json 1.0)" 0
grep -q "::warning::hook-latency gate attempt 1 FAILED" "$LAST_LOG" || die "flake: ::warning missing"
grep -q "probe" "$LAST_CALLS" && die "flake: probe ran without a double failure"

# 3. fail both + probe CONTENDED (p50 above threshold) — fail fast, NO 3rd.
run_case "fail both, contended probe" 1 1 0 1 1 1 0 "$(floor_json 200.01)" 1
grep -q "still-contended VM" "$LAST_LOG" || die "contended: distinct infrastructure label missing"
grep -q "FAILED on BOTH attempts (rc1=1 rc2=1)" "$LAST_LOG" || die "contended: historical both-attempts marker missing (wave2 back-compat)"
grep -q "gate:3" "$LAST_CALLS" && die "contended: 3rd attempt ran despite a contended probe"

# 4. fail both + probe UNCONTENDED + pass@3 — probe-gated recovery.
run_case "uncontended pass@3" 1 1 0 1 1 1 0 "$(floor_json 150.0)" 0
grep -q "probe-gated 3rd attempt" "$LAST_LOG" || die "pass@3: probe-gated marker missing"
grep -q "gate:3" "$LAST_CALLS" || die "pass@3: 3rd attempt never ran"
grep -q "attempt 3: mock_entry" "$LAST_SUMMARY" || die "pass@3: attempt-3 percentiles missing"

# 5. fail both + probe UNCONTENDED + fail@3 — real regression.
run_case "uncontended fail@3" 1 1 1 1 1 1 0 "$(floor_json 150.0)" 1
grep -q "rc3=1" "$LAST_LOG" || die "fail@3: rc3 missing from the error"
grep -q "FAILED on BOTH attempts (rc1=1 rc2=1)" "$LAST_LOG" || die "fail@3: historical both-attempts marker missing (wave2 back-compat)"

# 6. malformed probe report — CONTENDED (fail-safe), NO 3rd.
run_case "malformed probe json" 1 1 0 1 1 1 0 'not-json-at-all' 1
grep -q "still-contended VM" "$LAST_LOG" || die "malformed: not treated as contended"
grep -q "gate:3" "$LAST_CALLS" && die "malformed: 3rd attempt ran on a malformed report"

# 7. probe timeout (rc 124, empty output) — CONTENDED (fail-safe).
run_case "probe timeout" 1 1 0 1 1 1 124 '' 1
grep -q "still-contended VM" "$LAST_LOG" || die "timeout: not treated as contended"
grep -q "gate:3" "$LAST_CALLS" && die "timeout: 3rd attempt ran after a probe timeout"

# 8. nonzero probe exit WITH below-threshold JSON — rc OVERRIDES JSON (r4 F4).
run_case "probe rc overrides good json" 1 1 0 1 1 1 1 "$(floor_json 1.0)" 1
grep -q "still-contended VM" "$LAST_LOG" || die "rc-override: not treated as contended"
grep -q "gate:3" "$LAST_CALLS" && die "rc-override: 3rd attempt ran despite nonzero probe exit"

# 9. boundary p50 == 200 — threshold is <= — UNCONTENDED.
run_case "boundary p50==200 uncontended" 1 1 0 1 1 1 0 "$(floor_json 200)" 0
grep -q "gate:3" "$LAST_CALLS" || die "boundary: p50==200 must be UNCONTENDED (<= threshold)"

say "PROOF GREEN: extended retry matrix holds on the staged step text (9/9 cases)"
