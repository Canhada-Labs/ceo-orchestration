#!/usr/bin/env bash
# scripts/tests/test-upgrade-dryrun-identity.sh
# PLAN-161 W1a (U1 oracle) — upgrade.sh --dry-run must write NOTHING inside the
# adopter target WHILE baseline-manifest provenance classification still works.
#
# EXPECTED-RED on HEAD (PLAN-161 context item 2a, found live in the 2026-07-21
# adopter upgrade): three target-tree writers ignore --dry-run —
#   - mkdir -p "$BAK_DIR"                          (upgrade.sh:567)
#   - _load_baseline_manifest mktemp in $BAK_DIR   (upgrade.sh:646, called :799)
#   - upgrade_agents_canonical_only                (upgrade.sh:1366-1420)
# (+ the codex/grok bundle refresh blocks when --harness codex|grok is active).
#
# Oracle = FULL tree listing (files+dirs+symlinks) + per-file sha256 before vs
# after --dry-run (debate CF-12), PLUS semantic assertions (codex r1 F4):
# byte-identity alone would pass on a dry-run that silently lost provenance
# classification, so the dry-run log must ALSO prove the manifest loaded and
# classification ran (contract provided by the W2 U1 patch):
#   - "Baseline manifest: loaded"  status line
#   - a classification-aware dry-run preview for a customized FILE target
#   - the U3 purge preview (would-purge list + --purge-misinstalled hint) for a
#     seeded mis-installed excluded-tree file
#
# Markers (PLAN-161 W1 check, codex r5 F2 + r6 F1):
#   REPRO-CONFIRMED  = the seeded HEAD bug reproduced (dry-run mutated the tree)
#   SCAFFOLD-ERROR   = the fixture itself broke (never a verdict on the bug)
#
# Staged-oracle hook: UPGRADE_SOURCE_DIR points the test at a patched framework
# checkout (land-plan161.sh --dry-run runs this in STAGED mode); defaults to
# the repo this test lives in.
#
# bash 3.2-safe. Run: bash scripts/tests/test-upgrade-dryrun-identity.sh; echo rc=$?

set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="${UPGRADE_SOURCE_DIR:-$( cd "$SCRIPT_DIR/../.." && pwd )}"

export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-p161-dry-XXXXXX )" \
  || { printf 'SCAFFOLD-ERROR: mktemp WORKROOT failed\n' >&2; exit 2; }
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

ok()       { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()      { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }
scaffold() { printf 'SCAFFOLD-ERROR: %s\n' "$1" >&2; exit 2; }

if command -v shasum >/dev/null 2>&1; then
  _sha() { shasum -a 256 "$1" | awk '{print $1}'; }
elif command -v sha256sum >/dev/null 2>&1; then
  _sha() { sha256sum "$1" | awk '{print $1}'; }
else
  scaffold "neither shasum nor sha256sum on PATH"
fi

_git_init_retry() {
  local d="$1" n=0
  while [ "$n" -lt 5 ]; do
    if ( cd "$d" && git init -q 2>/dev/null ); then return 0; fi
    n=$((n+1)); sleep 1
  done
  ( cd "$d" && git init -q )
}

# Full-tree oracle snapshot: every path (file/dir/symlink) + per-file sha256.
# .git pruned (created by the fixture, never touched by upgrade.sh).
snapshot() {
  local t="$1" out="$2"
  ( cd "$t" && find . -name .git -prune -o -print 2>/dev/null | LC_ALL=C sort ) \
    > "$out.paths" || scaffold "snapshot path walk failed for $t"
  : > "$out"
  local p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if [ -L "$t/$p" ]; then
      printf 'L %s -> %s\n' "$p" "$( readlink "$t/$p" )" >> "$out"
    elif [ -d "$t/$p" ]; then
      printf 'D %s\n' "$p" >> "$out"
    elif [ -f "$t/$p" ]; then
      printf 'F %s %s\n' "$p" "$( _sha "$t/$p" )" >> "$out"
    else
      printf 'O %s\n' "$p" >> "$out"
    fi
  done < "$out.paths"
}

echo "==> D.0 — fixture adopter via the real installer"
T="$( mktemp -d "$WORKROOT/tgt-XXXXXX" )" || scaffold "mktemp target failed"
_git_init_retry "$T"
if ! bash "$SOURCE_DIR/scripts/install.sh" "$T" --profile core \
     > "$WORKROOT/install.log" 2>&1; then
  tail -30 "$WORKROOT/install.log" >&2
  scaffold "install.sh failed (see log above)"
fi
[ -s "$T/.claude/.install-manifest.sha256" ] \
  || scaffold "install produced no baseline manifest"

# Seed (a) an adopter customization of a single-FILE framework target so the
# classifier MUST produce an ADOPTER-CUSTOMIZED verdict, and (b) a
# mis-installed excluded-tree file (bytes == current framework source) so the
# U3 purge PREVIEW has something to nominate.
CUST_FILE="$T/.claude/task-chains.yaml"
[ -f "$CUST_FILE" ] || scaffold "fixture target lacks .claude/task-chains.yaml"
printf '\n# adopter-custom-line-p161-dry\n' >> "$CUST_FILE"

SEED_SRC="$( find "$SOURCE_DIR/.claude/hooks/tests" -maxdepth 1 -type f -name 'test_*.py' 2>/dev/null | LC_ALL=C sort | head -1 )"
[ -n "$SEED_SRC" ] || scaffold "framework source has no .claude/hooks/tests/test_*.py to seed"
SEED_REL=".claude/hooks/tests/$( basename "$SEED_SRC" )"
mkdir -p "$T/.claude/hooks/tests" || scaffold "seed mkdir failed"
cp "$SEED_SRC" "$T/$SEED_REL" || scaffold "seed cp failed"

echo "==> D.1 — snapshot, --dry-run, snapshot"
snapshot "$T" "$WORKROOT/before.oracle"
if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T" --profile core --dry-run \
     > "$WORKROOT/dryrun.log" 2>&1; then
  ok "D.1 upgrade --dry-run exited 0"
else
  bad "D.1 upgrade --dry-run exited nonzero (see $WORKROOT/dryrun.log)"
  tail -20 "$WORKROOT/dryrun.log" >&2
fi
snapshot "$T" "$WORKROOT/after.oracle"

echo "==> D.2 — byte-identity: --dry-run wrote NOTHING in the target (CF-12)"
if diff -u "$WORKROOT/before.oracle" "$WORKROOT/after.oracle" \
     > "$WORKROOT/oracle.diff" 2>&1; then
  ok "D.2 full-tree listing + per-file sha256 identical across --dry-run"
else
  bad "D.2 --dry-run mutated the adopter tree:"
  sed -n '1,40p' "$WORKROOT/oracle.diff" >&2
  echo "REPRO-CONFIRMED: upgrade.sh --dry-run wrote inside the target (PLAN-161 U1 bug 2a — BAK_DIR/agents-pin/manifest-tmp writer family)"
fi

echo "==> D.3 — semantic: baseline manifest still LOADS under --dry-run (codex r1 F4)"
if grep -q 'Baseline manifest: loaded' "$WORKROOT/dryrun.log"; then
  ok "D.3 dry-run log carries the manifest-loaded status line"
else
  bad "D.3 no 'Baseline manifest: loaded' status in the dry-run log (provenance classification not proven under dry-run)"
fi

echo "==> D.4 — semantic: classifier verdict present in the dry-run log"
if grep -q 'would PRESERVE (ADOPTER-CUSTOMIZED).*task-chains\.yaml' "$WORKROOT/dryrun.log"; then
  ok "D.4 classification-aware dry-run preview for the customized FILE target"
else
  bad "D.4 no classification-aware preview for .claude/task-chains.yaml (dry-run lost — or never had — classifier verdicts)"
fi

echo "==> D.5 — semantic: U3 purge PREVIEW prints under --dry-run (no flag)"
if grep -q -- '--purge-misinstalled' "$WORKROOT/dryrun.log" \
   && grep -q "$SEED_REL" "$WORKROOT/dryrun.log"; then
  ok "D.5 would-purge preview names the seeded mis-install + the opt-in flag"
else
  bad "D.5 no purge preview for seeded $SEED_REL (+ --purge-misinstalled hint) in the dry-run log"
fi

echo "==> D.6 — sanity: dry-run still previews work (not a silent no-op)"
if grep -q '(dry-run)' "$WORKROOT/dryrun.log"; then
  ok "D.6 dry-run log contains at least one (dry-run) preview line"
else
  bad "D.6 dry-run log has NO preview lines (dry-run silently skipped the walk?)"
fi

echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
