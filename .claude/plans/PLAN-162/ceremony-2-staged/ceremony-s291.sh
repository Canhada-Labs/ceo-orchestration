#!/bin/bash
# ceremony-s291.sh — consolidated Owner-GPG ceremony for S291.
#
# WHAT THIS LANDS (one sentinel, one signed commit):
#   p1-corrected  PLAN-165 posture-write surface: 6 deny entries (kernel +
#                 template mirror) + the 3 paths into _CANONICAL_GUARDS
#                 (the load-bearing Bash rail — closes codex CX-1/CX-2/CX-6
#                 and implements the Owner-ratified OQ1-redo) + overlay and
#                 marker into _KERNEL_PATHS
#   p2            night_mode_toggled registered in _lib/audit_emit.py
#   p2b           the 4 pinned contract tests that p2 turns red + the
#                 per-action coverage test (pack checklist item 4)
#   p4            install.sh: posture-state .gitignore entries (CX-3)
#   p5            SPEC/v1/audit-log.schema.md row + v2.54 history entry
#                 (the pack's 4-source checklist item 3 — SPEC/** is
#                 deny-Edit'd, so the schema row is a ceremony input)
#   + BLOCK 3.5   regenerates .claude/data/audit-registry.golden.txt
#
# NOT IN THIS SCRIPT (deliberately):
#   - PLAN-162 fixes + ADR-164-AMEND-1 + ADR-110-AMEND-2: they need the
#     pair-rail APPROVE first, and the debate consensus (S7) requires the
#     fail-closed canonical-edit fixes to stay SEPARABLE from the riders,
#     so a rail REJECT on one does not block all. Second ceremony.
#   - RC3-F7 (upgrade.sh backup ||true): rides the second ceremony.
#
# The script NEVER pushes and NEVER tags. It signs INLINE (no pre-existing
# .asc is required — repo lesson feedback-ceremony-scripts-must-sign-inline).
#
# Usage:
#   bash ceremony-s291.sh --dry-run     # rehearse; restores tree AND index
#   bash ceremony-s291.sh               # real run (prompts for GPG)

set -euo pipefail

REPO="/Users/joaocanhada/canhada-labs/ceo-orchestration"
# The CORRECTED pack lives on plan-165-draft (commit fdb0f06), not on
# main — main still carries the stale 3-patch pack whose p1 no longer
# applies (p3 rewrote its settings.json anchor). Materialize the pack
# from the branch into a temp dir OUTSIDE the repo: that keeps the
# tracked-hash-manifest discipline (the bytes come from a committed
# branch, verified by shasum) while keeping the working tree free of
# pack files, so they never enter the signed scope.
PACK_REF="plan-165-draft"
PACK_REL=".claude/plans/PLAN-165/ceremony-staged"
PACK="$(mktemp -d)/ceremony-staged"
SENTINEL_DIR="$REPO/.claude/plans/PLAN-165/architect/round-3"
KEY="CFCFACF00335DC74"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

cd "$REPO"

# --- trap: a dry-run (or an abort) must leave NEITHER tree NOR index dirty.
_ORIG_HEAD="$(git rev-parse HEAD)"
# Untracked snapshot taken BEFORE anything is applied. `git checkout -- .`
# restores TRACKED files only, so a patch that CREATES a file (p2b adds
# test_audit_emit_night_mode_toggled.py) leaves it behind after a
# dry-run — the ceremony-residue class that poisoned a staged-vs-canonical
# resolver in S287. Remove exactly the delta, never a blind `git clean`,
# so the operator's own untracked work is untouchable.
_UNTRACKED_BEFORE="$(git ls-files --others --exclude-standard | sort)"
_restore() {
  local rc=$?
  if [[ "$DRY_RUN" -eq 1 || $rc -ne 0 ]]; then
    echo ""
    echo "--> restoring tree + index to $_ORIG_HEAD"
    git reset -q "$_ORIG_HEAD" 2>/dev/null || true
    git checkout -q -- . 2>/dev/null || true
    local after new
    after="$(git ls-files --others --exclude-standard | sort)"
    new="$(comm -13 <(printf '%s\n' "$_UNTRACKED_BEFORE") <(printf '%s\n' "$after"))"
    if [[ -n "$new" ]]; then
      printf '%s\n' "$new" | while IFS= read -r f; do
        [[ -n "$f" ]] && rm -f "$f" && echo "    removed residue: $f"
      done
    fi
    rm -f "$SENTINEL_DIR/approved.md" "$SENTINEL_DIR/approved.md.asc" 2>/dev/null || true
    rmdir "$SENTINEL_DIR" 2>/dev/null || true
    echo "    tree: $(git status --porcelain | wc -l | tr -d ' ') change(s)"
  fi
  return $rc
}
trap _restore EXIT

echo "=== BLOCK 0 — preconditions ==="
[[ -z "$(git status --porcelain)" ]] || { echo "FAIL: tree not clean"; exit 1; }
echo "HEAD: $_ORIG_HEAD"

echo ""
echo "=== BLOCK 1 — materialize pack from $PACK_REF + manifest (fail-closed) ==="
git rev-parse --verify "$PACK_REF" >/dev/null 2>&1 \
  || { echo "FAIL: branch $PACK_REF not found"; exit 1; }
mkdir -p "$PACK"
# git archive keeps the bytes exactly as committed on the branch and
# never touches the working tree or the index.
git archive "$PACK_REF" "$PACK_REL" | tar -x -C "$PACK" --strip-components=4 \
  || { echo "FAIL: could not extract pack from $PACK_REF"; exit 1; }
echo "  pack extracted from $PACK_REF ($(git rev-parse --short "$PACK_REF"))"
( cd "$PACK" && shasum -a 256 -c MANIFEST.sha256 ) || { echo "FAIL: manifest"; exit 1; }

echo ""
echo "=== BLOCK 2 — git apply --check (all four, against live HEAD) ==="
for p in p1-deny-overlay p2-audit-action p2b-contract-tests p4-install-gitignore p5-spec-schema-row; do
  git apply --check "$PACK/$p.patch" || { echo "FAIL: $p does not apply"; exit 1; }
  echo "  ok: $p.patch"
done

echo ""
echo "=== BLOCK 3 — apply ==="
for p in p1-deny-overlay p2-audit-action p2b-contract-tests p4-install-gitignore p5-spec-schema-row; do
  git apply "$PACK/$p.patch"
  echo "  applied: $p.patch"
done

echo ""
echo "=== BLOCK 3.5 — regenerate the audit-registry golden ==="
# The golden (.claude/data/audit-registry.golden.txt) is GENERATED from
# _KNOWN_ACTIONS; registering an action without regenerating it reds
# test_real_repo_golden_in_sync. The dry-run caught this. Regenerate as a
# PROCESS — never hand-edit a generated file.
python3 "$REPO/.claude/scripts/check-audit-registry-coverage.py" --write-golden \
  || { echo "FAIL: golden regeneration"; exit 1; }
echo "  golden regenerated"

echo ""
echo "=== BLOCK 4 — post-apply gates ==="
python3 "$REPO/.claude/scripts/local/json_ok.py" \
  "$REPO/.claude/settings.json" \
  "$REPO/templates/settings/settings.base.json" 2>/dev/null \
  || python3 - "$REPO/.claude/settings.json" "$REPO/templates/settings/settings.base.json" <<'PYJSON'
import json, sys
for p in sys.argv[1:]:
    json.load(open(p, encoding="utf-8"))
print("json ok")
PYJSON
shellcheck -S warning "$REPO/scripts/install.sh" && echo "  shellcheck: clean"
# DERIVE the target files from disk — never recall them. The first
# version of this block listed nine filenames from memory; two of them
# (test_reality_ledger.py, test_check_audit_registry_coverage.py) live
# in .claude/scripts/tests/, not hooks/tests/, so pytest collected ZERO
# and the gate passed on nothing. That is the closed-set-from-memory
# class (feedback-closed-sets-must-be-derived-not-recalled) landing
# inside a ceremony gate. The globs below cannot name a file that is
# not there, and the count assertion makes an empty expansion fail loud.
# bash 3.2 (macOS default) has no `mapfile` — the repo mandates 3.2
# portability and the first version of this line used it anyway. The
# while-read + process-substitution form is the portable idiom.
_GATE_FILES=()
while IFS= read -r _f; do
  [ -n "$_f" ] && _GATE_FILES+=("$_f")
done < <(
  find "$REPO/.claude/hooks/tests" "$REPO/.claude/scripts/tests" \
       -maxdepth 1 -name '*.py' \
       \( -name 'test_audit_emit*' \
          -o -name 'test_*canonical_edit*' \
          -o -name 'test_check_arbitration_kernel*' \
          -o -name 'test_reality_ledger*' \
          -o -name 'test_check_audit_registry_coverage*' \) \
       2>/dev/null | sort
)
[[ "${#_GATE_FILES[@]}" -ge 20 ]] \
  || { echo "FAIL: gate file derivation collected ${#_GATE_FILES[@]} files (<20) — the glob is wrong, not the tree"; exit 1; }
echo "  gate files derived from disk: ${#_GATE_FILES[@]}"
python3 -m pytest -q --no-header -p no:cacheprovider "${_GATE_FILES[@]}" 2>&1 | tail -2
bash "$REPO/.claude/scripts/local/verify-counts.sh" --quiet --no-tests \
  && echo "  verify-counts: clean"

echo ""
echo "=== BLOCK 5 — sentinel (scope = exactly the touched set) ==="
mkdir -p "$SENTINEL_DIR"
# Stage first, THEN read the set. `git diff --name-only HEAD` omits
# untracked files, so p2b's NEW test file was missing from the Scope and
# then flagged as out-of-scope in BLOCK 7 — the dry-run caught it. The
# sentinel's own files are excluded: they are the authorization, not the
# change being authorized.
git add -A
TOUCHED="$(git diff --cached --name-only \
            | grep -v '^\.claude/plans/PLAN-165/architect/round-3/' \
            | sort)"
echo "touched:"; echo "$TOUCHED" | sed 's/^/    /'

{
  echo "# PLAN-165 P1-corrected + P2 — Owner sentinel (S291)"
  echo ""
  echo "Anchor-sha: $_ORIG_HEAD"
  echo "Ceremony: consolidated posture-write surface + audit action"
  echo ""
  echo "Scope:"
  echo "$TOUCHED" | sed 's/^/- /'
  echo ""
  echo "Rationale: closes the escalation ladder the codex review (CX-1)"
  echo "proved the original p1 left open — per-tool deny entries never see"
  echo "the Bash rail, so the three posture paths also enter"
  echo "_CANONICAL_GUARDS (which check_bash_safety keys off) and the two"
  echo "state files enter _KERNEL_PATHS. Implements the Owner-ratified"
  echo "OQ1-redo (2026-08-03): night-mode on/off become human actions."
  echo "P2 registers night_mode_toggled atomically with the contract tests"
  echo "it turns red, so no commit ever has an unregistered emit."
  echo ""
  echo "Signed-by: Owner"
} > "$SENTINEL_DIR/approved.md"

echo ""
echo "=== BLOCK 6 — sign the sentinel INLINE ==="
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "  (dry-run) would: gpg --armor --detach-sign -u $KEY approved.md"
else
  GPG_TTY="$(tty)"
  export GPG_TTY
  gpg --armor --detach-sign -u "$KEY" -o "$SENTINEL_DIR/approved.md.asc" \
      "$SENTINEL_DIR/approved.md"
  gpg --verify "$SENTINEL_DIR/approved.md.asc" "$SENTINEL_DIR/approved.md"
  echo "  signature verified"
fi

echo ""
echo "=== BLOCK 7 — touched MINUS scope must be empty ==="
git add -A
# The allowed set = the signed Scope + the sentinel pair itself. The
# previous form piped only the LAST echo into `sort`, so `comm` received
# unsorted input and mis-reported — a broken gate that would have either
# passed junk or blocked a correct ceremony. Build both sides explicitly.
ALLOWED="$(printf '%s\n%s\n%s\n' "$TOUCHED" \
  ".claude/plans/PLAN-165/architect/round-3/approved.md" \
  ".claude/plans/PLAN-165/architect/round-3/approved.md.asc" \
  | grep -v '^$' | sort -u)"
FINAL="$(git diff --cached --name-only | sort -u)"
EXTRA="$(comm -23 <(printf '%s\n' "$FINAL") <(printf '%s\n' "$ALLOWED"))"
if [[ -n "$EXTRA" ]]; then
  echo "FAIL: files staged outside the signed scope:"; echo "$EXTRA"; exit 1
fi
echo "  touched - scope = empty  (scope: $(printf '%s\n' "$TOUCHED" | grep -c . ) files)"

echo ""
echo "=== BLOCK 8 — commit (signed) ==="
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "  (dry-run) would: git commit -S -u $KEY  [SENT-S291]"
  echo ""
  echo "DRY-RUN COMPLETE — tree and index will be restored by the trap."
else
  git commit -S -q -m "governance(PLAN-165): posture-write surface closed on the Bash rail [SENT-S291]

p1-corrected: the six deny entries were never the load-bearing rail — the
codex review (CX-1) showed deny is per-TOOL while check_bash_safety keys
off _CANONICAL_GUARDS, so \`echo '{...}' > settings.local.json\` walked
straight through under acceptEdits. The three posture paths now enter
_CANONICAL_GUARDS, and the overlay + marker enter _KERNEL_PATHS. Listing
the writer script there also removes model-rail invocation of the toggle,
which is what the Owner ratified in the OQ1-redo: arming autonomy is a
human action.

p2 + p2b: night_mode_toggled is registered together with the four pinned
contract tests it turns red and its per-action coverage test, so no commit
in this history has an emit the registry does not know about.

p4: adopters get the posture-state ignore entries install.sh was missing
(CX-3) — without them \`/night-mode on\` dirties an adopter's tree.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
  echo "  committed: $(git rev-parse --short HEAD)"
  echo ""
  echo "NEXT (Owner): review the commit, then 'git push origin <branch>'."
  echo "This script never pushes."
fi
