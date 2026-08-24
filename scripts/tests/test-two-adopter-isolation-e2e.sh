#!/usr/bin/env bash
# PLAN-182 W3 — TWO adopters under ONE $HOME do not entangle their audit chains.
#
# The class this pins (ADR-001 / PLAN-182 W1): every runtime-state write used to
# resolve to `$HOME/.claude/projects/ceo-orchestration`, a literal named after
# the FRAMEWORK rather than the project. Two different adopters under the same
# $HOME therefore shared one state directory, one HMAC key and one chain: their
# events interleaved, `verify_chain()` became meaningless per project, and
# attribution was impossible.
#
# Why this test has to do REAL installs. The unit tests cover the resolver in
# isolation, but the claim being made is about the INSTALLED product: what an
# adopter actually gets. Measured gaps that made this test necessary:
#   * `grep -cE '\bHOME\b' scripts/tests/smoke-install.sh` = 0 — the existing
#     e2e does three real installs but never isolates HOME, so it structurally
#     cannot observe cross-project entanglement.
#   * no shell test in `scripts/tests/*.sh` mentions `verify_chain` at all —
#     the property that matters most had no e2e coverage whatsoever.
#
# FOUR legs are asserted, because three of them can pass while the product is
# still broken:
#   1. the single resolver is PRESENT in each install;
#   2. each project resolves to its OWN state directory;
#   3. the HMAC keys are DISTINCT (same dir would mean same key);
#   4. each chain verifies INDEPENDENTLY, and — the leg that catches a silent
#      regression — the legacy literal dir sees ZERO growth, under a POSITIVE
#      control proving the writes actually happened somewhere.
#
# Leg 4's positive control is the point: "nothing was written to the legacy
# dir" is also satisfied by "nothing was written at all". So each adopter's
# own chain must GROW by a known amount in the same run.
#
# bash 3.2-safe. mktemp -d only. Local/landing-gate posture, matching what
# `.github/workflows/validate.yml:879` already documents for `test-doctor.sh`
# and its siblings; wiring this into the nightly touches a CANONICAL workflow
# and is deliberately out of scope.
set -uo pipefail   # NOT -e: failures are asserted explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

FAIL=0
PASS=0
WORK="$( mktemp -d -t ceo-two-adopter-XXXXXX )"
cleanup() { [ -n "${WORK:-}" ] && rm -rf "$WORK" 2>/dev/null || true; }
trap cleanup EXIT

ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

# Hermetic env: a FAKE shared HOME is the whole point — both adopters live
# under it, exactly as two repos of one developer would.
export HOME="$WORK/home"; mkdir -p "$HOME"
export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0
# The whole-dir override outranks everything else (ADR-001); an ambient value
# would send every write outside the sandbox and make the test lie.
unset CLAUDE_PROJECT_DIR_NATIVE 2>/dev/null || true
unset CEO_AUDIT_LOG_DIR 2>/dev/null || true
unset CEO_AUDIT_LOG_PATH 2>/dev/null || true

LEGACY_DIR="$HOME/.claude/projects/ceo-orchestration"

_git_init_retry() {
  d="$1"; n=0
  while [ "$n" -lt 5 ]; do
    if ( cd "$d" && git init -q 2>/dev/null ); then return 0; fi
    n=$((n+1)); sleep 1
  done
  ( cd "$d" && git init -q )
}

install_adopter() {  # $1 = adopter dir name -> echoes the path
  _ia_t="$WORK/$1"
  mkdir -p "$_ia_t"
  _git_init_retry "$_ia_t"
  if ! bash "$SOURCE_DIR/scripts/install.sh" "$_ia_t" --profile core \
        > "$_ia_t/.install.log" 2>&1; then
    echo "INSTALL_FAILED:$1" >&2
    tail -25 "$_ia_t/.install.log" >&2
    return 1
  fi
  printf '%s\n' "$_ia_t"
}

echo "==> I.0 — two REAL installs under one shared \$HOME"
A="$( install_adopter adopter-alpha )" || { bad "I.0 install alpha"; A=""; }
B="$( install_adopter adopter-beta )"  || { bad "I.0 install beta";  B=""; }
if [ -n "$A" ] && [ -n "$B" ]; then
  ok "I.0 both adopters installed (shared HOME=$HOME)"
else
  echo "==> RESULT: $PASS passed, $FAIL failed (aborting: installs failed)"
  exit 1
fi

# ---------------------------------------------------------------------------
# Leg 1 — the single resolver is present in each install.
# ---------------------------------------------------------------------------
echo "==> I.1 — the single resolver ships to each adopter"
for t in "$A" "$B"; do
  n="$( basename "$t" )"
  if [ -f "$t/.claude/hooks/_lib/runtime_paths.py" ]; then
    ok "I.1 $n has _lib/runtime_paths.py"
  else
    bad "I.1 $n MISSING _lib/runtime_paths.py — nothing to resolve through"
  fi
done

# ---------------------------------------------------------------------------
# Legs 2-4 — emit into each adopter's chain, then compare.
# `emit_generic` takes top-level **kwargs (fields=... would nest them and the
# scrubber would drop the lot). Actions come from the closed enum.
# ---------------------------------------------------------------------------
echo "==> I.2 — each project resolves to its OWN state dir"

EMIT_PY="$WORK/emit.py"
cat > "$EMIT_PY" <<'PYEOF'
import os, sys
target = sys.argv[1]
n = int(sys.argv[2])
sys.path.insert(0, os.path.join(target, ".claude", "hooks"))
from _lib import runtime_paths as rp
from _lib import audit_emit as ae
d = rp.runtime_state_dir()
os.makedirs(str(d), mode=0o700, exist_ok=True)
for i in range(n):
    ae.emit_generic("session_start", session_index_count=i)
print(str(d))
PYEOF

emit_into() {  # $1 = adopter path, $2 = how many events -> echoes resolved dir
  ( cd "$1" && CLAUDE_PROJECT_DIR="$1" python3 "$EMIT_PY" "$1" "$2" 2>/dev/null )
}

DIR_A="$( emit_into "$A" 3 )"
DIR_B="$( emit_into "$B" 5 )"

if [ -n "$DIR_A" ] && [ -n "$DIR_B" ]; then
  ok "I.2 both adopters resolved a state dir"
else
  bad "I.2 resolution produced no dir (A='$DIR_A' B='$DIR_B')"
fi

if [ -n "$DIR_A" ] && [ "$DIR_A" != "$DIR_B" ]; then
  ok "I.2 the two dirs DIFFER (alpha=$( basename "$DIR_A" ), beta=$( basename "$DIR_B" ))"
else
  bad "I.2 both projects resolved to the SAME dir ($DIR_A) — chains entangle"
fi

case "$DIR_A" in
  *"/projects/ceo-orchestration") bad "I.2 alpha resolved to the LEGACY literal" ;;
  *) ok "I.2 alpha did not resolve to the legacy literal" ;;
esac

# ---------------------------------------------------------------------------
# Leg 3 — distinct HMAC keys. Same dir would mean same key, so this is the
# assertion that makes leg 2 consequential rather than cosmetic.
# ---------------------------------------------------------------------------
echo "==> I.3 — the HMAC keys are DISTINCT"
KEY_A="$DIR_A/audit-key"
KEY_B="$DIR_B/audit-key"
if [ -f "$KEY_A" ] && [ -f "$KEY_B" ]; then
  ok "I.3 both adopters have their own audit-key file"
  SA="$( shasum -a 256 "$KEY_A" | cut -d' ' -f1 )"
  SB="$( shasum -a 256 "$KEY_B" | cut -d' ' -f1 )"
  if [ "$SA" != "$SB" ]; then
    ok "I.3 keys differ (${SA:0:12}… vs ${SB:0:12}…)"
  else
    bad "I.3 IDENTICAL keys — one adopter can forge the other's chain"
  fi
  # 0600 is the documented posture; a looser mode is a real finding.
  for k in "$KEY_A" "$KEY_B"; do
    m="$( ls -l "$k" | cut -c1-10 )"
    case "$m" in
      -rw-------) ok "I.3 $( basename "$( dirname "$k" )" ) key mode 0600" ;;
      *) bad "I.3 key mode is $m, want -rw------- ($k)" ;;
    esac
  done
else
  bad "I.3 key file missing (A=$KEY_A B=$KEY_B) — emission never happened"
fi

# ---------------------------------------------------------------------------
# Leg 4 — each chain verifies INDEPENDENTLY, with the growth control.
# ---------------------------------------------------------------------------
echo "==> I.4 — verify_chain() is meaningful PER PROJECT"

VERIFY_PY="$WORK/verify.py"
cat > "$VERIFY_PY" <<'PYEOF'
import os, sys
from pathlib import Path
target, state_dir = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(target, ".claude", "hooks"))
from _lib import audit_hmac
log = Path(state_dir) / "audit-log.jsonl"
if not log.is_file():
    print("NOLOG 0"); raise SystemExit(0)
res = audit_hmac.verify_chain(log, key_path_override=Path(state_dir) / "audit-key")
lines = sum(1 for _ in log.open("r", encoding="utf-8", errors="replace"))
print("%s %d" % ("INTACT" if res.is_intact else "BROKEN", lines))
PYEOF

check_chain() {  # $1=adopter $2=state dir $3=expected line count $4=label
  out="$( cd "$1" && CLAUDE_PROJECT_DIR="$1" python3 "$VERIFY_PY" "$1" "$2" 2>/dev/null )"
  verdict="${out%% *}"; lines="${out##* }"
  case "$verdict" in
    INTACT) ok "I.4 $4 chain verifies INTACT ($lines line(s))" ;;
    BROKEN) bad "I.4 $4 chain is BROKEN — entangled or tampered" ;;
    *)      bad "I.4 $4 has no chain at all (out='$out')" ;;
  esac
  # Positive control for leg 4: the events must actually be THERE, or the
  # legacy-dir assertion below would pass for the wrong reason.
  if [ "${lines:-0}" -ge "$3" ]; then
    ok "I.4 $4 chain grew by >= $3 line(s) — the writes really happened"
  else
    bad "I.4 $4 chain has $lines line(s), expected >= $3 — nothing was written, so the leak test is vacuous"
  fi
}
check_chain "$A" "$DIR_A" 3 "alpha"
check_chain "$B" "$DIR_B" 5 "beta"

echo "==> I.5 — the legacy literal dir saw ZERO writes"
if [ -e "$LEGACY_DIR" ]; then
  LEG_LINES="$( find "$LEGACY_DIR" -type f 2>/dev/null | wc -l | tr -d ' ' )"
  if [ "$LEG_LINES" = "0" ]; then
    ok "I.5 legacy dir exists but is EMPTY"
  else
    bad "I.5 legacy dir has $LEG_LINES file(s) — something still writes to the framework-named literal"
    find "$LEGACY_DIR" -type f 2>/dev/null | head -5 >&2
  fi
else
  ok "I.5 legacy dir was never created"
fi

# Cross-contamination: neither adopter's dir may contain the other's events.
echo "==> I.6 — no cross-contamination between the two chains"
if [ -f "$DIR_A/audit-log.jsonl" ] && [ -f "$DIR_B/audit-log.jsonl" ]; then
  # `grep -c` PRINTS "0" and exits 1 on no-match, so `|| echo 0` would
  # append a SECOND line and every numeric comparison below would break on
  # "0\n0". `|| true` fixes the exit without touching stdout.
  HITS_A="$( grep -c "$( basename "$B" )" "$DIR_A/audit-log.jsonl" 2>/dev/null || true )"
  HITS_B="$( grep -c "$( basename "$A" )" "$DIR_B/audit-log.jsonl" 2>/dev/null || true )"
  [ "$HITS_A" = "0" ] && ok "I.6 alpha's log carries no beta paths" \
                      || bad "I.6 alpha's log mentions beta $HITS_A time(s)"
  [ "$HITS_B" = "0" ] && ok "I.6 beta's log carries no alpha paths" \
                      || bad "I.6 beta's log mentions alpha $HITS_B time(s)"
else
  bad "I.6 one or both logs missing — cannot compare"
fi

echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
