#!/usr/bin/env bash
# =============================================================================
# wave1-wrapper-matrix-proof.sh — PLAN-159 Wave 1: retry-wrapper truth table.
#
# Repeatable proof (pair-rail round-1 finding #3a: "proven by test" must be
# a runnable artifact, not a session anecdote). Applies the STAGED patch to
# a temp copy of validate.yml, extracts the REAL step run-block, replaces
# run_gate with a mock, and asserts the full truth table:
#
#   pass@1                 -> exit 0
#   fail@1 + pass@2        -> exit 0  + ::warning logged
#   fail@1 + fail@2        -> exit 1  + ::error logged     (fail-closed)
#   fail@1 no-report + ... -> publish() notes "NO parseable report"
#
# Run by land-plan159.sh as a pre-commit gate; also runnable standalone.
# READ-ONLY on the repo: everything happens in a mktemp dir.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
STAGED="$REPO/.claude/plans/PLAN-159/staged/wave1"
TMP="$(mktemp -d)"
trap 'rm -f "$TMP"/* 2>/dev/null; rmdir "$TMP" 2>/dev/null || true' EXIT
say() { printf '\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

say "Apply staged patch to a temp copy of validate.yml (from HEAD, not the worktree)"
# HEAD, not the worktree file (uncommitted-review P1): during the live
# ceremony this gate may run around the apply step — the worktree copy
# could already be patched, and re-applying would fail spuriously. HEAD
# is patch-clean by construction until the ceremony commit lands, which
# also means: this proof is a PRE-LAND gate only (post-land, HEAD already
# carries the new step and the patch no longer applies).
git -C "$REPO" show HEAD:.github/workflows/validate.yml > "$TMP/validate.yml"
python3 - "$TMP" "$STAGED/validate-yml.patch" <<'PY'
import subprocess, sys, pathlib, shutil, os
tmp, patch = sys.argv[1], sys.argv[2]
# use git apply in an isolated throwaway repo so --check/apply semantics match the ceremony
os.chdir(tmp)
subprocess.run(["git", "init", "-q"], check=True)
pathlib.Path(".github/workflows").mkdir(parents=True)
shutil.move("validate.yml", ".github/workflows/validate.yml")
subprocess.run(["git", "apply", patch], check=True)
print("  patch applied in isolated tmp repo")
PY

say "Extract the step run-block (textual, no yaml dependency)"
python3 - "$TMP" <<'PY'
import sys
from pathlib import Path
tmp = Path(sys.argv[1])
lines = (tmp / ".github/workflows/validate.yml").read_text().splitlines(keepends=True)
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

say "Substitute run_gate with the mock (writes a report only when MOCK_JSON_\$n=1)"
python3 - "$TMP" <<'PY'
import re, sys
from pathlib import Path
tmp = Path(sys.argv[1])
blk = (tmp / "gate-step.sh").read_text()
mock = '''run_gate() {
  local rc_var="MOCK_RC_$1" js_var="MOCK_JSON_$1"
  if [ "${!js_var}" = "1" ]; then
    echo '{"hooks":{"mock_entry":{"p50_ms":1,"p95_ms":2,"p99_ms":3,"max_ms":4}}}' > "/tmp/hook-latency-attempt-$1.json"
  else
    rm -f "/tmp/hook-latency-attempt-$1.json"
  fi
  return "${!rc_var}"
}
'''
blk2 = re.sub(r'run_gate\(\) \{\n.*?\n\}\n', mock, blk, count=1, flags=re.S)
assert blk2 != blk, "run_gate mock substitution failed — step layout drifted"
(tmp / "gate-step-mocked.sh").write_text(blk2)
print("  mocked")
PY

say "Truth table"
run_case() { # label rc1 rc2 js1 js2 want_exit
  local label="$1" rc1="$2" rc2="$3" js1="$4" js2="$5" want="$6"
  local sf="$TMP/summary-$RANDOM.md"; : > "$sf"
  set +e
  MOCK_RC_1="$rc1" MOCK_RC_2="$rc2" MOCK_JSON_1="$js1" MOCK_JSON_2="$js2" \
    GITHUB_STEP_SUMMARY="$sf" bash "$TMP/gate-step-mocked.sh" > "$TMP/case-out.log" 2>&1
  local got=$?
  set -e
  [ "$got" -eq "$want" ] || { cat "$TMP/case-out.log" >&2; die "[$label] exit=$got want=$want"; }
  echo "  OK [$label] exit=$got"
  LAST_SUMMARY="$sf"; LAST_LOG="$TMP/case-out.log"
}

run_case "pass@1"              0 0 1 1 0
grep -q "attempt 1: mock_entry" "$LAST_SUMMARY" || die "pass@1: attempt-1 percentiles missing from step summary"

run_case "flake fail@1 pass@2" 1 0 1 1 0
grep -q "::warning::hook-latency gate attempt 1 FAILED" "$LAST_LOG" || die "flake: ::warning missing"
grep -q "attempt 2: mock_entry" "$LAST_SUMMARY" || die "flake: attempt-2 percentiles missing"

run_case "regression fail both" 1 1 1 1 1
grep -q "::error::hook-latency gate FAILED on BOTH attempts (rc1=1 rc2=1)" "$LAST_LOG" || die "regression: ::error marker missing"

run_case "cap-kill no report"  124 0 0 1 0
grep -q "NO parseable report" "$LAST_SUMMARY" || die "cap-kill: publish() did not note the missing report"

say "PROOF GREEN: wrapper truth table holds on the STAGED step text (4/4 cases)"
