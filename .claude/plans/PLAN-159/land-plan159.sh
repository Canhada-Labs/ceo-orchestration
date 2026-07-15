#!/usr/bin/env bash
# =============================================================================
# land-plan159.sh — PLAN-159 Wave 1 landing ceremony (Owner runs via `!`).
#
# Perf-gate robustness: hook-latency gate N=20 -> N=200 + single
# fail-closed capped in-step retry + job timeout 5->16min + ADR-163 + citation
# drift fix. ONE sentinel commit (SENT-PERFGATE). land-plan158.sh lineage:
# the sentinel is created AND signed inline by this script (anchor filled
# from HEAD at ceremony time); staged artifacts are applied mechanically.
#
# Usage:
#     bash .claude/plans/PLAN-159/land-plan159.sh [--dry-run] [--skip-proof]
#         --dry-run     preflight + plan report only. READ-ONLY BY
#                       CONSTRUCTION: no file is written, no git command
#                       that mutates tree/index is executed (S273 lesson —
#                       nothing to restore because nothing is touched).
#         --skip-proof  skip the local N=200 profiler proof run (~80s).
#                       Use only if the proof was run green immediately
#                       before the ceremony in this same tree.
#
# ⚠ PREREQUISITES (Owner, at the ceremony, BEFORE running this):
#   1. PLAN-159 debate round-1 verdict PROCEED + OQ1-OQ3 ratified
#      (plan §Open questions carries the verbatim ratification lines).
#   2. Codex pair-rail verdict (V2) at
#      .claude/plans/PLAN-159/pair-rail-verdict-wave1.md with GO/ACCEPT.
#      This script FAILS CLOSED if the file is missing or has no verdict.
#   3. Validate green on HEAD — OQ2 exception: if the ONLY red is the old
#      flaky hook-latency gate itself, one bounded rerun is pre-authorized
#      by the ratified OQ2 (this script prints the check, Owner decides).
#
# Landing (single commit, anchor = HEAD at sign time):
#   [0] preflight   (main, clean, origin sync, gpg key, staged patch
#                    applies, ADR staged, pair-rail verdict present)
#   [1] sentinel    (fill anchor -> approved.md -> detach-sign .asc)
#   [2] apply       (git apply validate-yml.patch; cp ADR-163; targeted
#                    citation fix in test_hook_latency.py; CLAUDE.md ADR
#                    count derived from disk, never hardcoded)
#   [3] gates       (claims check, governance fast, local N=200 proof)
#   [4] scope       (touched vs HEAD ⊆ signed scope, else abort)
#   [5] commit -S
# After landing: push, watch Validate, then Wave 2 (3-green proof +
# deliberate-regression fixture via wave2-regression-proof.sh).
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
STAGED=".claude/plans/PLAN-159/staged/wave1"
ADR_REL=".claude/adr/ADR-163-hook-latency-gate-percentile-stability.md"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
export GPG_TTY="${GPG_TTY:-$(tty || true)}"
# Owner-shell apply route: in-session canonical hooks gate Claude's tool
# calls, not the Owner's shell; the signed sentinel IS the authorization
# record (S261 precedent).

DRY=0; SKIP_PROOF=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --skip-proof) SKIP_PROOF=1 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- preflight (READ-ONLY — shared by dry-run and live) ---------------------
say "Preflight"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
# Clean-tree contract (pair-rail r3 #1): the LIVE ceremony anchors the
# sentinel to a shared, committed tip — the PLAN-159 materials must be
# committed+pushed FIRST (runbook step 2 in the plan §How to continue).
# DRY-RUN is allowed while ONLY the PLAN-159 bundle itself is dirty, so
# the preflight is testable before that commit.
_dirty="$(git status --porcelain=v1)"
if [ -n "$_dirty" ]; then
  _non159="$(printf '%s\n' "$_dirty" | sed -E 's/^.{3}//; s/^"//; s/"$//' | grep -vE '^\.claude/plans/PLAN-159' || true)"
  if [ "$DRY" -eq 1 ] && [ -z "$_non159" ]; then
    echo "  (dry-run: PLAN-159 bundle is uncommitted — allowed for preflight; the LIVE ceremony requires it committed+pushed first)"
  else
    git status --short >&2
    die "working tree not clean — commit+push the PLAN-159 materials (and stash anything else) before the ceremony: git add .claude/plans/PLAN-159-perf-gate-robustness.md .claude/plans/PLAN-159/ && git commit && git push"
  fi
fi
git fetch origin main --quiet || echo "  (warn: fetch failed — offline? continuing on local refs)"
[ "$(git rev-parse HEAD)" = "$(git rev-parse --verify -q origin/main 2>/dev/null || git rev-parse HEAD)" ] \
  || die "main != origin/main — pull/push first (ceremony anchors to the shared tip)"
PROF_REL=".claude/scripts/profile-opus-4-7.py"
TEST_REL=".claude/scripts/tests/test_profile_opus47_latency_gate.py"
[ -f "$STAGED/validate-yml.patch" ] || die "staged patch missing: $STAGED/validate-yml.patch"
[ -f "$STAGED/root/$ADR_REL" ] || die "staged ADR missing: $STAGED/root/$ADR_REL"
[ -f "$STAGED/root/$PROF_REL" ] || die "staged profiler missing: $STAGED/root/$PROF_REL"
[ -f "$STAGED/root/$TEST_REL" ] || die "staged unit test missing: $STAGED/root/$TEST_REL"
[ ! -f "$ADR_REL" ] || die "$ADR_REL already exists on main — did Wave 1 already land?"
python3 -c "import ast,sys; ast.parse(open('$STAGED/root/$PROF_REL').read())" || die "staged profiler does not parse"
# Integrity pin (pair-rail r4 #1): staged/ is GITIGNORED by design in
# this repo, so the ceremony inputs live only in this checkout. The
# TRACKED manifest below anchors their exact bytes: the pair-rail V2
# verdict was issued against THESE hashes, and any post-review mutation
# of a staged input fails here. If you intentionally changed a staged
# artifact, you must re-run the pair-rail AND regenerate the manifest.
shasum -a 256 -c .claude/plans/PLAN-159/staged-wave1.sha256 --status \
  || { shasum -a 256 -c .claude/plans/PLAN-159/staged-wave1.sha256 >&2 || true; \
       die "staged inputs do not match the tracked manifest (staged-wave1.sha256) — post-review mutation detected; re-run the pair-rail + regenerate the manifest"; }
echo "  staged integrity: 4/4 inputs match the tracked manifest"
git apply --check "$STAGED/validate-yml.patch" || die "validate-yml.patch does not apply — validate.yml drifted; regenerate via the plan's gen-validate-patch.py flow"
# Wrapper truth-table proof runs in PREFLIGHT (uncommitted-review P1):
# it reads HEAD (order-independent) and must fail BEFORE the sentinel is
# signed or anything is applied.
bash .claude/plans/PLAN-159/wave1-wrapper-matrix-proof.sh 2>&1 | tail -2 || die "wrapper truth-table proof red — do not land"
grep -q 'ADR-071 N≥200 percentile-stability minimum' .claude/hooks/tests/test_hook_latency.py \
  || die "citation-fix anchor not found in test_hook_latency.py (drifted)"
grep -Eq '\*\*[0-9]+ ADRs\*\*' CLAUDE.md || die "ADR-count claim anchor not found in CLAUDE.md"

VERDICT=".claude/plans/PLAN-159/pair-rail-verdict-wave1.md"
# Anchored parse, NEGATIVE first (pair-rail round-1 finding #1: a bare
# `grep 'GO|ACCEPT'` matches the "GO" inside "NO-GO" and would let a
# rejecting verdict authorize the ceremony — the exact fail-open this
# gate exists to prevent). Unparseable verdict == no verdict (fail-closed).
if [ -f "$VERDICT" ]; then
  if grep -Eiq '^[[:space:]]*VERDICT:[[:space:]]*(NO-GO|NO GO|REJECT|BLOCK)' "$VERDICT"; then
    die "pair-rail verdict is NEGATIVE — resolve findings + re-run the pair-rail to GO before the ceremony (V2 fail-closed)"
  elif grep -Eiq '^[[:space:]]*VERDICT:[[:space:]]*(GO|ACCEPT)([[:space:]]|$)' "$VERDICT"; then
    echo "  pair-rail verdict: anchored GO/ACCEPT"
  else
    die "pair-rail verdict has no parseable 'VERDICT: GO|ACCEPT' line — unparseable == missing (V2 fail-closed)"
  fi
elif [ "$DRY" -eq 1 ]; then
  echo "  PENDING: pair-rail verdict ($VERDICT) — the LIVE ceremony fails closed without it (V2)"
else
  die "pair-rail verdict missing ($VERDICT) — run the V2 Codex review on the staged diff first (V2 is fail-closed; no verdict => no ceremony)"
fi

if [ "$DRY" -eq 0 ]; then
  gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || die "signing key $KEY not in your keyring"
fi

say "Validate status on HEAD (OQ2 context)"
gh run list --branch main --workflow validate.yml --limit 3 \
  --json headSha,conclusion,displayTitle \
  --jq '.[] | "  \(.headSha[:8]) \(.conclusion // "in-progress") \(.displayTitle[:60])"' \
  2>/dev/null || echo "  (gh unavailable — check Validate manually before landing)"
echo "  OQ2: if the ONLY red on HEAD is the old hook-latency flake, one bounded rerun is pre-authorized by the ratified OQ2."

if [ "$DRY" -eq 1 ]; then
  say "DRY-RUN report (nothing was touched)"
  echo "  would apply : $STAGED/validate-yml.patch  (N=200 + capped fail-closed retry + timeout 16min)"
  echo "  would apply : $PROF_REL (precondition + TimeoutExpired fold + default 200)"
  echo "  would create: $TEST_REL (9 unit tests)"
  echo "  would create: $ADR_REL"
  echo "  would edit  : .claude/hooks/tests/test_hook_latency.py (citation ADR-071 -> ADR-163)"
  _adr_next=$(( $(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ') + 1 ))
  echo "  would edit  : CLAUDE.md ADR count -> ${_adr_next} (derived from disk at apply time)"
  echo "  would sign  : .claude/plans/PLAN-159/architect/sent-perfgate/approved.md (+ .asc)"
  echo "  then        : 1 signed commit [SENT-PERFGATE], scope-asserted"
  exit 0
fi

# ---- [1] sentinel: fill anchor + sign inline --------------------------------
say "Sentinel SENT-PERFGATE (sign inline, anchor = HEAD)"
D=".claude/plans/PLAN-159/architect/sent-perfgate"; mkdir -p "$D"
ANCHOR="$(git rev-parse HEAD)"
cat > "$D/approved.md" <<BODY
# SENT-PERFGATE — PLAN-159 Wave 1: hook-latency gate percentile stability

Raises the opus-4-7-profiler-smoke hook-latency gate from N=20 to N=200
warm iterations, adds a single deterministic in-step retry that is
fail-closed by construction (if-not form, EXACTLY 2 attempts, 420s
per-attempt wall-cap, explicit exit 1 on double failure, attempt
percentiles in the step summary whenever a parseable report exists and
an explicit no-report note otherwise), bumps the job timeout 5->16min
(contended 2xcap + overhead), hardens the profiler (fail-loud
percentile_indices_collapsed precondition min N=22; TimeoutExpired
folded into the fail-closed hook_failed sink; default N 20->200) with 9
staged unit tests, ships ADR-163 (canonical N>=200
percentile-stability record + invariants + measured evidence), and
repairs the ADR-071 citation drift in validate.yml +
test_hook_latency.py. Ceilings UNCHANGED (p95<120ms / p99<160ms).
Root cause measured in .claude/plans/PLAN-159/measurements.md: at N=20
the nearest-rank index collapses (idx_p95 == idx_p99 == 2nd-largest
sample; p99 was dead code) — 8 load-flakes S272/S273 on doc-only
commits. Detection: an injected over-ceiling regression fails BOTH
attempts (proven post-land by wave2-regression-proof.sh THROUGH the
wrapper). Debate round-1: 3x ADJUST -> consensus PROCEED, all
must-fixes resolved + mirror-clone proven. OQ1-OQ3 ratified (plan
§Open questions); pair-rail V2 verdict at
.claude/plans/PLAN-159/pair-rail-verdict-wave1.md.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs $KEY
Anchor-SHA: $ANCHOR
Plans: PLAN-159
Kernel-Override: (none — .github/workflows/*.yml + .claude/adr/*.md are CANONICAL class, not _KERNEL_PATHS; profiler + tests are unguarded)
Scope:
  - .github/workflows/validate.yml
  - $ADR_REL
  - $PROF_REL
  - $TEST_REL
  - .claude/hooks/tests/test_hook_latency.py
  - CLAUDE.md
<!-- END SIGNED SCOPE -->
BODY
rm -f "$D/approved.md.asc"
gpg --local-user "$KEY" --armor --detach-sign --output "$D/approved.md.asc" "$D/approved.md" \
  || die "GPG signing failed (run: export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"
echo "  signed: $D/approved.md (anchor $ANCHOR)"

# ---- [2] apply ---------------------------------------------------------------
say "Apply staged artifacts"
git apply "$STAGED/validate-yml.patch" || die "patch apply failed after --check passed (?)"
echo "    applied: .github/workflows/validate.yml"
cp "$STAGED/root/$ADR_REL" "$ADR_REL"
echo "    applied: $ADR_REL"
cp "$STAGED/root/$PROF_REL" "$PROF_REL"
echo "    applied: $PROF_REL"
cp "$STAGED/root/$TEST_REL" "$TEST_REL"
echo "    applied: $TEST_REL"
python3 - <<'PYFIX' || die "citation fix failed"
from pathlib import Path
p = Path(".claude/hooks/tests/test_hook_latency.py")
t = p.read_text()
old = ("All measured with N=200 iterations per hook (was 50; matches\n"
       "ADR-071 N≥200 percentile-stability minimum).")
new = ("All measured with N=200 iterations per hook (was 50; matches the\n"
       "ADR-163 N≥200 percentile-stability rule — the CI gate samples the\n"
       "same N=200 since PLAN-159; ADR-071 covers benchmark methodology,\n"
       "not hook-latency percentiles).")
assert old in t, "anchor not found"
p.write_text(t.replace(old, new, 1))
print("    applied: test_hook_latency.py citation fix")
PYFIX
python3 - <<'PYCNT' || die "CLAUDE.md ADR-count bump failed"
import re, glob
from pathlib import Path
n = len(glob.glob(".claude/adr/ADR-*.md"))  # derived from disk AFTER the ADR copy
p = Path("CLAUDE.md")
t = p.read_text()
new_t, k = re.subn(r"\*\*\d+ ADRs\*\*", f"**{n} ADRs**", t, count=1)
assert k == 1, "ADR-count claim not found"
p.write_text(new_t)
print(f"    applied: CLAUDE.md ADR count -> {n}")
PYCNT

# ---- [3] gates ----------------------------------------------------------------
say "Gates"
python3 -m pytest "$TEST_REL" -q 2>&1 | tail -2 || die "new unit tests red — do not land"
python3 .claude/scripts/check-claude-md-claims.py 2>&1 | tail -3 || die "claims check red"
bash .claude/scripts/validate-governance.sh --fast 2>&1 | tail -3 || die "governance fast red"
if [ "$SKIP_PROOF" -eq 0 ]; then
  say "Local N=200 proof (~80s; --skip-proof to skip if just proven)"
  python3 .claude/scripts/profile-opus-4-7.py --hook-latency \
    --latency-iterations 200 --p95-ceiling-ms 120 --p99-ceiling-ms 160 >/dev/null \
    || die "local N=200 proof RED — do not land"
  echo "    proof: green"
fi

# ---- [4] scope assert ----------------------------------------------------------
say "Scope assert (touched ⊆ signed scope)"
_touched="$(git status --porcelain=v1 | sed -E 's/^.{3}//; s/^.* -> //')"
_bad="$(printf '%s\n' "$_touched" | grep -vE '^(\.github/workflows/validate\.yml|\.claude/adr/ADR-163-hook-latency-gate-percentile-stability\.md|\.claude/scripts/profile-opus-4-7\.py|\.claude/scripts/tests/test_profile_opus47_latency_gate\.py|\.claude/hooks/tests/test_hook_latency\.py|CLAUDE\.md|\.claude/plans/PLAN-159)' || true)"
[ -z "$_bad" ] || { printf '%s\n' "$_bad" >&2; die "touched files outside SENT-PERFGATE scope"; }

# ---- [5] commit -S --------------------------------------------------------------
say "Commit"
git add .github/workflows/validate.yml "$ADR_REL" "$PROF_REL" "$TEST_REL" \
  .claude/hooks/tests/test_hook_latency.py CLAUDE.md "$D"
git commit -S -m "feat(PLAN-159): SENT-PERFGATE — hook-latency gate N=200 + capped fail-closed retry [ADR-163]

validate.yml opus-4-7-profiler-smoke: --latency-iterations 20->200 (at
N=20 the nearest-rank index collapsed: p95==p99==2nd-largest sample; 2
contended iterations failed the gate — 8 load-flakes S272/S273 on
doc-only commits; p99 ceiling was dead code), fail-closed in-step retry
(EXACTLY 2 attempts, 420s per-attempt wall-cap, explicit exit 1 on
double failure, attempt percentiles in the step summary when a
parseable report exists + explicit no-report note otherwise), job
timeout 5->16min sized for the contended case. Profiler hardening:
fail-loud percentile_indices_collapsed precondition (min N=22),
TimeoutExpired folded fail-closed, default N=200; 9 unit tests.
Ceilings UNCHANGED 120/160. ADR-163 records the rule, invariants
(exactly-2 attempts; anti-vacuity >= iterations; per-entry sensitivity
1.6x-2.2x) + measured distributions; fixes the ADR-071 citation drift
here and in test_hook_latency.py. CLAUDE.md ADR count derived from
disk. Debate round-1: 3x ADJUST -> PROCEED. Evidence:
.claude/plans/PLAN-159/measurements.md. [SENT-PERFGATE]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || die "commit failed"

say "DONE — 1 sentinel commit. Review, then push:"
echo "    git log --oneline -2"
echo "    git push origin main"
echo ""
echo "  Wave 2 (prove + closeout):"
echo "    1. Watch Validate on the landing push (OQ2: one bounded rerun"
echo "       pre-authorized if the OLD gate flakes on this very push)."
echo "    2. Two no-op pushes -> 3 consecutive green (anti-flake acceptance)."
echo "    3. bash .claude/plans/PLAN-159/wave2-regression-proof.sh"
echo "       (scratch branch, injected sleep, gate must go RED; branch deleted)."
echo "    4. Plan -> executing ticks -> done (completed_at + related_commits)."
