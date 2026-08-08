#!/usr/bin/env bash
# =============================================================================
# PLAN-168 W1 — positive control for ownership-nightly-gate.sh.
#
# The gate is the instrument that watches the ownership e2e in CI; this test
# watches the GATE. Every failure mode the gate claims to catch is planted
# here with a fake harness, and the test demands the gate actually goes red —
# green-without-control proves nothing (PLAN-167: 8 instrument defects).
#
# Scenarios:
#   S1  matching set, rc=1, HARNESS-ERR=0            => gate PASSES
#   S2  set GREW (one extra red)                     => gate FAILS
#   S3  set SHRANK (all green, rc=0)                 => gate FAILS
#   S4  harness rc=2 (infra error)                   => gate FAILS
#   S5  summary line missing (truncated output)      => gate FAILS
#   S6  HARNESS-ERR=1 in summary                     => gate FAILS
#   S7  rc=0 while expected set non-empty            => gate FAILS
#   S8  set SWAPPED (same size, different ids)       => gate FAILS
#   S9  empty expected set + all green, rc=0         => gate PASSES
#   S10 expected id degraded to TIMEOUT (same ids)   => gate FAILS
#   S11 expected id degraded to ESCAPE  (same ids)   => gate FAILS
#   S12 green cell degraded to AMBIG                 => gate FAILS
#
# Exit: 0 all scenarios behave. 1 at least one does not. 2 harness error.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
GATE="$SCRIPT_DIR/ownership-nightly-gate.sh"
[[ -f "$GATE" ]] || { echo "ERROR: gate not found: $GATE" >&2; exit 2; }

WORK="$( mktemp -d "${TMPDIR:-/tmp}/own-gate-test.XXXXXX" )" || exit 2
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT

# --- fake harness ------------------------------------------------------------
# Emits a canned map on stdout and exits with a canned rc. The gate consumes
# it via OWNERSHIP_GATE_HARNESS exactly as it would the real harness.
mk_fake() { # $1=out-file $2=rc-file
  cat > "$WORK/fake-harness.sh" <<EOF
#!/usr/bin/env bash
cat "$1"
exit "\$(cat "$2")"
EOF
  chmod +x "$WORK/fake-harness.sh"
}

map_line() { # $1=id $2=status
  printf '%-10s %-7s exp=%-16s/%-22s got=%-16s/%-22s rc=%-3s %s\n' \
    "$1" "$2" "V" "H" "V" "H" "0" "test"
}

write_map() { # $1=file, then "id:status" pairs; appends summary from counts
  local f="$1"; shift
  local green=0 red=0 err="${SUMMARY_ERR:-0}"
  : > "$f"
  local pair id st
  for pair in "$@"; do
    id="${pair%%:*}"; st="${pair##*:}"
    map_line "$id" "$st" >> "$f"
    case "$st" in GREEN) green=$((green+1)) ;; *) red=$((red+1)) ;; esac
  done
  if [[ "${SUMMARY_OMIT:-0}" -ne 1 ]]; then
    printf '\nGREEN=%d  RED=%d  AMBIG=0  HARNESS-ERR=%d\n' "$green" "$red" "$err" >> "$f"
  fi
}

expected_4() {
  printf 'OWN-0016\nOWN-0024\nOWN-0027\nOWN-0074\n' > "$WORK/exp.txt"
}

run_gate() { # $1=expected-rc  $2=label
  local want="$1" label="$2" got=0
  OWNERSHIP_GATE_HARNESS="$WORK/fake-harness.sh" \
  OWNERSHIP_GATE_EXPECTED="$WORK/exp.txt" \
    bash "$GATE" > "$WORK/gate-out.txt" 2> "$WORK/gate-err.txt" || got=$?
  if [[ "$got" -eq "$want" ]]; then
    echo "PASS  $label (gate rc=$got)"
    return 0
  fi
  echo "FAIL  $label — gate rc=$got, expected $want"
  sed -n '1,15p' "$WORK/gate-out.txt" | sed 's/^/      out| /'
  sed -n '1,15p' "$WORK/gate-err.txt" | sed 's/^/      err| /'
  return 1
}

FAILURES=0

# S1 — matching set, honest rc=1 => PASS
expected_4
write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 0 "S1 matching set + rc=1" || FAILURES=$((FAILURES+1))

# S2 — set grew => FAIL
write_map "$WORK/map.txt" OWN-0001:RED OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S2 set grew" || FAILURES=$((FAILURES+1))

# S3 — set shrank to zero (all green, honest rc=0) => FAIL (all-green = STOP)
write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0016:GREEN OWN-0024:GREEN OWN-0027:GREEN OWN-0074:GREEN
echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S3 set shrank (all green)" || FAILURES=$((FAILURES+1))

# S4 — harness infra error rc=2 => FAIL
write_map "$WORK/map.txt" OWN-0016:RED
echo 2 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S4 harness rc=2" || FAILURES=$((FAILURES+1))

# S5 — summary line missing (truncated run) => FAIL even with matching ids
# (explicit set/reset: VAR=x prefixed to a FUNCTION call has version-divergent
# persistence semantics in bash — never rely on it.)
SUMMARY_OMIT=1
write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
SUMMARY_OMIT=0
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S5 summary missing" || FAILURES=$((FAILURES+1))

# S6 — HARNESS-ERR=1 => FAIL even with matching ids
SUMMARY_ERR=1
write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
SUMMARY_ERR=0
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S6 HARNESS-ERR=1" || FAILURES=$((FAILURES+1))

# S7 — rc=0 while expected set non-empty (rc/set incoherence) => FAIL
write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S7 rc=0 with non-empty expected set" || FAILURES=$((FAILURES+1))

# S8 — same size, different ids => FAIL
write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0099:RED OWN-0074:GREEN
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S8 set swapped" || FAILURES=$((FAILURES+1))

# S9 — empty expected set + all green + rc=0 => PASS
: > "$WORK/exp.txt"
write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0002:GREEN
echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 0 "S9 empty expected set, all green" || FAILURES=$((FAILURES+1))

# S10-S12 — an EXPECTED-red id degrades to TIMEOUT / ESCAPE / AMBIG: the id
# set is UNCHANGED, so an ids-only comparison would pass a more severe
# regression as "same set" (codex rail r2 P1). The gate must go red on the
# STATUS, not just the set.
expected_4
write_map "$WORK/map.txt" OWN-0016:TIMEOUT OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S10 expected id degraded to TIMEOUT" || FAILURES=$((FAILURES+1))

write_map "$WORK/map.txt" OWN-0016:ESCAPE OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S11 expected id degraded to ESCAPE" || FAILURES=$((FAILURES+1))

write_map "$WORK/map.txt" OWN-0001:AMBIG OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S12 green cell degraded to AMBIG" || FAILURES=$((FAILURES+1))

echo ""
if [[ "$FAILURES" -gt 0 ]]; then
  echo "ownership-nightly-gate positive control: $FAILURES scenario(s) FAILED"
  exit 1
fi
echo "ownership-nightly-gate positive control: 12/12 scenarios behave"
exit 0
