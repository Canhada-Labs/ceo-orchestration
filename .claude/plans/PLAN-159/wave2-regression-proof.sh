#!/usr/bin/env bash
# =============================================================================
# wave2-regression-proof.sh — PLAN-159 Wave 2 deliberate-regression fixture.
#
# Proves the LANDED gate (N=200 + capped fail-closed retry) still catches
# an injected over-ceiling regression THROUGH THE FULL RETRY WRAPPER
# (debate consensus C2/K-SE-MF1: asserting the profiler exits non-zero
# once is NOT the contract — the JOB must go RED after BOTH attempts).
#
# Mechanism: in a THROWAWAY git worktree at HEAD (main tree untouched):
#   1. inject a 150ms sleep into check_output_secrets.py's entrypoint
#      (pushes that entry's p95 from ~65ms to ~215ms — over the 120ms
#      ceiling; criterion per consensus C4 is "over-ceiling", not "2x")
#   2. extract the REAL step run-block from the worktree's validate.yml
#      (the exact shell the CI job executes — wrapper included)
#   3. execute it; REQUIRE non-zero exit AND the both-attempts marker.
#
# Run AFTER Wave 1 landed (the step must be the new wrapper). ~5-10min.
# Usage: bash .claude/plans/PLAN-159/wave2-regression-proof.sh
# Safe: never lands anything; the worktree is removed on every exit path.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WT="$(mktemp -d)/plan159-regproof"
# Unique branch name + delete-only-what-we-created (uncommitted-review
# P2: a fixed name could force-delete a developer's pre-existing branch
# via the EXIT trap when worktree-add fails).
BRANCH="plan159-regproof-$$-$(date +%s)"
BRANCH_CREATED=0
say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

cleanup() {
  cd "$REPO"
  git worktree remove --force "$WT" 2>/dev/null || true
  [ "$BRANCH_CREATED" -eq 1 ] && git branch -D "$BRANCH" 2>/dev/null || true
}
trap cleanup EXIT

say "Throwaway worktree at $WT (HEAD, branch $BRANCH)"
cd "$REPO"
git worktree add -b "$BRANCH" "$WT" HEAD --quiet
BRANCH_CREATED=1

say "Sanity: worktree carries the NEW wrapper step"
grep -q 'run_gate() {' "$WT/.github/workflows/validate.yml" \
  || die "validate.yml in HEAD does not carry the PLAN-159 wrapper — run this AFTER Wave 1 lands"

say "Inject deliberate 150ms over-ceiling regression into check_output_secrets.py (worktree only)"
python3 - "$WT" <<'PY'
import sys
from pathlib import Path
hook = Path(sys.argv[1]) / ".claude/hooks/check_output_secrets.py"
t = hook.read_text()
anchor = "from __future__ import annotations"
assert anchor in t, "anchor not found in check_output_secrets.py"
t = t.replace(anchor, anchor + "\nimport time as _t; _t.sleep(0.15)  # PLAN-159 W2 DELIBERATE REGRESSION FIXTURE — never lands", 1)
hook.write_text(t)
print("  injected")
PY

say "Extract the REAL gate step run-block from the worktree's validate.yml"
python3 - "$WT" <<'PY'
import sys
from pathlib import Path
wt = Path(sys.argv[1])
lines = (wt / ".github/workflows/validate.yml").read_text().splitlines(keepends=True)
out, taking = [], False
for i, l in enumerate(lines):
    if l.rstrip() == "      - name: Run profile-opus-4-7.py --hook-latency (p95/p99 gate)":
        taking = "seek-run"
        continue
    if taking == "seek-run":
        assert l.rstrip() == "        run: |", f"unexpected step layout: {l!r}"
        taking = "body"
        continue
    if taking == "body":
        if l.strip() == "" or l.startswith("          "):
            out.append(l[10:] if l.startswith("          ") else l)
        else:
            break
assert out, "run block not found"
(wt / "gate-step.sh").write_text("".join(out))
print(f"  extracted {len(out)} lines -> gate-step.sh")
PY

say "Execute the REAL wrapper against the regressed tree (expect RED after BOTH attempts; ~5-10min)"
cd "$WT"
export GITHUB_STEP_SUMMARY="$WT/step-summary.md"
: > "$GITHUB_STEP_SUMMARY"
# macOS portability (pair-rail finding): coreutils `timeout` exists on
# ubuntu-latest (the gate's real home) but NOT on stock macOS. Without
# this shim the extracted step dies rc=127 on BOTH attempts and this
# proof would go green VACUOUSLY (S254 class — red for the wrong
# reason). Local proof runs UNCAPPED (pass-through); the cap semantics
# are CI-side and covered by the wrapper matrix test.
RUNNER="bash"
if ! command -v timeout >/dev/null 2>&1; then
  say "coreutils 'timeout' absent (macOS) — running the step with a pass-through shim (uncapped local proof)"
  cat > "$WT/timeout-shim.sh" <<'SHIM'
timeout() { shift; "$@"; }
SHIM
  RUNNER="shimmed"
fi
set +e
if [ "$RUNNER" = "shimmed" ]; then
  bash -c "source '$WT/timeout-shim.sh'; source '$WT/gate-step.sh'" > "$WT/gate-output.log" 2>&1
else
  bash "$WT/gate-step.sh" > "$WT/gate-output.log" 2>&1
fi
rc=$?
set -e
tail -5 "$WT/gate-output.log"

# Anti-vacuity: the RED must come from the MEASUREMENT (injected entry
# over the 120ms ceiling in the attempt report), never from environment
# breakage (127 command-not-found, missing profiler, etc.).
say "Anti-vacuity check: the breach is real and measured"
python3 - <<'PY' || die "PROOF VACUOUS: gate went red WITHOUT a measured over-ceiling breach on the injected entry — fix the environment, do not count this as detection proof"
import json, sys
try:
    d = json.load(open("/tmp/hook-latency-attempt-1.json"))
except Exception as e:
    sys.exit(f"attempt-1 report unreadable: {e}")
hooks = d.get("hooks", {})
breached = [n for n, h in hooks.items()
            if isinstance(h, dict) and "output_secrets" in n and h.get("p95_ms", 0) > 120.0]
if not breached:
    sys.exit(f"no injected entry breached: { {n: h.get('p95_ms') for n, h in hooks.items() if isinstance(h, dict)} }")
print(f"  measured breach confirmed on: {breached}")
PY

if [ "$rc" -ne 0 ] && grep -q "FAILED on BOTH attempts (rc1=1 rc2=1)" "$WT/gate-output.log"; then
  say "PROOF GREEN: over-ceiling regression RED-flagged THROUGH the wrapper (exit=$rc, both attempts failed on the MEASUREMENT)"
  echo "  Step summary captured $(wc -l < "$GITHUB_STEP_SUMMARY" | tr -d ' ') lines (attempt percentiles published even on failure)."
  echo "  Record in the plan:"
  echo "  - [x] injected over-ceiling regression RED-flags through the retry wrapper ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  exit 0
else
  echo "--- last 40 lines of gate output ---"; tail -40 "$WT/gate-output.log"
  die "PROOF FAILED: exit=$rc (wanted non-zero + 'FAILED on BOTH attempts (rc1=1 rc2=1)') — detection contract broken or environment red; do NOT close Wave 2"
fi
