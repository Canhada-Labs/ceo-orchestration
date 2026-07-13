#!/usr/bin/env bash
# =============================================================================
# land-plan157-w1.sh — PLAN-157 Wave 1 landing ceremony (Owner runs via `!`).
#
# Sunsets 4 grandfathered squads (desktop, dotnet, architecture, agents-meta;
# OQ2 git-history-only deletion) + lands the 4 fold SPs (SP-043..SP-046,
# soak waived per OQ4 — Owner ratifies by detach-signing each SP) + the full
# count-reconcile (166→160 skills / 116→110 domain / 37→33 profiles / roster
# 32→28 with cap := 28 per OQ3), as ONE signed commit. Pattern: land-plan158.sh
# lineage, except the W1 sentinel is CREATED AND SIGNED AT THE CEREMONY
# (before running this) and this script only VERIFIES it — the script applies
# the pack MECHANICALLY and never thinks (contract in
# .claude/plans/PLAN-157/staged/w1/sunset/reconcile-notes.md).
#
# ⚠ PREREQUISITES (Owner, at the ceremony, BEFORE running this):
#   1. W1 sentinel: $SENTINEL_DIR/approved.md with Anchor-SHA = current HEAD
#      and a Scope block enumerating the W1 surfaces (reconcile-notes
#      §Scope-alternation), detach-signed to approved.md.asc.
#      Default dir: .claude/plans/PLAN-157/architect/w1 (override with
#      PLAN157_W1_SENTINEL_DIR=<dir>).
#   2. Owner .asc siblings for the four fold SPs, next to the staged .md:
#      .claude/plans/PLAN-157/staged/w1/proposals/SP-04{3,4,5,6}-*.md.asc
#      (gpg --local-user <KEY> --armor --detach-sign <file>).
#   3. Validate green on HEAD (this script checks via `gh run list`).
#
# Landing order (single commit — the pack encodes the single-commit end
# state; an intermediate sunsets/folds split would be RED against the staged
# roster-28 policy/test, see reconcile-notes §Commit atomicity):
#   [0] preconditions   (clean tree, main==origin/main, Validate green,
#                        sentinel GPG-verified + anchored at HEAD,
#                        apply-base sha256 pins intact)
#   [1] deletions       (git rm -r of the 4 trees, manifest-verified)
#   [2] staged replicas (11 full-file copies) + SQUAD_GRANDFATHER sed
#   [3] fold SPs        (copy SP-043..046 +.asc into .claude/proposals/,
#                        git-apply each inline diff, staged-hash asserted;
#                        SP-047 SKIPPED — W3) + pointer.md __LAND_SHA__ fill
#   [4] regen           (gen-command-skill-hook-map --write; skill-inventory
#                        re-embed between markers + --check)
#   [5] FULL per-wave check set (no gate skipped, slow ones included)
#   [6] scope assert    (touched − scope = ∅, or no commit)
#   [7] git add exact list + single `git commit -S` (NO auto-push)
#
# NOTE: the Owner-shell apply route (cp/git/sed here) does not trip the
# in-session canonical hooks — those gate Claude's tool calls, not the
# Owner's shell. The signed sentinel IS the authorization record (S261
# precedent); the guarded files this script rewrites (grandfather-cap
# policy, CLAUDE.md, the four core SKILL.md targets) are covered by it.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"

PACK=".claude/plans/PLAN-157/staged/w1"
SUNSET="$PACK/sunset"
PROPS="$PACK/proposals"
# OQ2 recovery pointer — NON-ignored path so it actually rides the W1
# commit (staged/ is gitignored: a pointer inside the pack would be
# silently skipped by git add and invisible to the scope assert —
# verify-pass P1, S272).
POINTER=".claude/plans/PLAN-157/w1-sunset-pointer.md"
SENTINEL_DIR="${PLAN157_W1_SENTINEL_DIR:-.claude/plans/PLAN-157/architect/w1}"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
CORE_SKILL=".claude/skills/core/ceo-orchestration/SKILL.md"
export GPG_TTY="${GPG_TTY:-$(tty || true)}"

TREES=(
  .claude/skills/domains/agents-meta
  .claude/skills/domains/architecture
  .claude/skills/domains/desktop
  .claude/skills/domains/dotnet
)

# Fold SPs, in binding order (SP-046's diff is based on SP-045's post-apply
# state — do not reorder). "file|target" pairs; target mirrors each SP's
# **Target:** line and is cross-asserted below.
SP_SET=(
  "SP-043-architecture-decisions-hexagonal-fold-2026-07-13.md|.claude/skills/core/architecture-decisions/SKILL.md"
  "SP-044-ai-llm-orchestration-recsys-fold-2026-07-13.md|.claude/skills/core/ai-llm-orchestration/SKILL.md"
  "SP-045-parallelization-by-default-dynamic-workflow-fold-2026-07-13.md|.claude/skills/core/parallelization-by-default/SKILL.md"
  "SP-046-parallelization-by-default-loop-design-fold-2026-07-13.md|.claude/skills/core/parallelization-by-default/SKILL.md"
)
# SP-047-prisma-patterns-saas-platforms-move-2026-07-13.md is W3 (OQ5) —
# deliberately NOT copied, NOT applied here. data-ml keeps 2 skills through W1.

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }
sha() { shasum -a 256 "$1" | awk '{print $1}'; }
fm()  { sed -n "s/^$2: *//p" "$1" | head -1 | sed 's/[[:space:]]*#.*$//; s/[[:space:]]*$//'; }

# --- failure trap: never leave a dirty repo without a restore hint ----------
CLEAN_HEAD=""
MUTATING=0
COMMITTED=0
TMP_CEREMONY="$(mktemp -d)"
on_exit() {
  local rc=$?
  rm -rf "$TMP_CEREMONY"
  if [ "$rc" -ne 0 ] && [ "$MUTATING" -eq 1 ] && [ "$COMMITTED" -eq 0 ]; then
    {
      printf '\n\033[1;33mABORTED MID-APPLY — the repo is dirty; NOTHING was committed or pushed.\033[0m\n'
      printf 'Restore the pre-ceremony state (tree was verified clean at preflight):\n'
      printf '    git reset --hard %s\n' "$CLEAN_HEAD"
      printf '    git clean -nd .claude/proposals   # inspect copied SP files, then -fd to drop them\n'
      printf 'The staged pack under %s is read-only input and was not modified,\n' "$PACK"
      printf 'except pointer.md (restored by the reset above).\n'
    } >&2
  fi
  return "$rc"
}
trap on_exit EXIT

gpg_verify_owner() { # <detached.asc> <file>
  local out
  out="$(gpg --status-fd 1 --verify "$1" "$2" 2>/dev/null || true)"
  printf '%s\n' "$out" | grep -q "^\[GNUPG:\] VALIDSIG .*$KEY" \
    || die "GPG verification failed for $2 (need VALIDSIG by $KEY)"
  echo "    GPG OK: $2"
}

# =============================================================================
# [0/7] Preconditions
# =============================================================================
say "[0/7] Preflight"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
if [ -n "$(git status --porcelain=v1)" ]; then
  git status --short >&2
  die "working tree not clean — commit/stash unrelated changes first"
fi
CLEAN_HEAD="$(git rev-parse HEAD)"
gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || die "signing key $KEY not in your keyring"

say "[0/7] Preflight: main up to date with origin"
git fetch origin main --quiet || die "git fetch origin main failed — network/auth?"
[ "$CLEAN_HEAD" = "$(git rev-parse origin/main)" ] \
  || die "local main ($CLEAN_HEAD) != origin/main — sync first (git pull --ff-only) or push"

say "[0/7] Preflight: Validate green on HEAD ($CLEAN_HEAD)"
_runs_json="$(gh run list --workflow validate.yml --branch main --limit 30 \
  --json headSha,status,conclusion)" || die "gh run list failed (is gh authenticated?)"
_state="$(printf '%s' "$_runs_json" | python3 -c '
import json, sys
head = sys.argv[1]
runs = [r for r in json.load(sys.stdin) if r.get("headSha") == head]
print((str(runs[0].get("status")) + "/" + str(runs[0].get("conclusion"))) if runs else "none/none")
' "$CLEAN_HEAD")"
[ "$_state" = "completed/success" ] \
  || die "Validate on HEAD is '$_state' (need completed/success) — wait for CI before landing"
echo "    Validate: completed/success"

say "[0/7] Preflight: pack integrity"
for f in "$SUNSET/deletion-manifest.txt" "$POINTER" \
         "$SUNSET/reconcile-notes.md" "$SUNSET/base-pins.sha256" \
         "$SUNSET/snippets/SQUAD_GRANDFATHER.new"; do
  [ -f "$f" ] || die "staged pack file missing: $f"
done
_n="$(cd "$SUNSET/root" && find . -type f | wc -l | tr -d ' ')"
[ "$_n" = "11" ] || die "expected 11 staged replicas under $SUNSET/root, found $_n — pack/script drift"
grep -q '__LAND_SHA__' "$POINTER" \
  || die "pointer.md has no __LAND_SHA__ placeholder — W1 appears to have landed already"
for t in "${TREES[@]}"; do
  [ -d "$t" ] || die "squad tree already gone: $t — W1 appears to have landed already"
done

say "[0/7] Preflight: W1 sentinel at $SENTINEL_DIR"
[ -f "$SENTINEL_DIR/approved.md" ]     || die "sentinel missing: $SENTINEL_DIR/approved.md (create+sign at the ceremony first)"
[ -f "$SENTINEL_DIR/approved.md.asc" ] || die "sentinel signature missing: $SENTINEL_DIR/approved.md.asc"
gpg_verify_owner "$SENTINEL_DIR/approved.md.asc" "$SENTINEL_DIR/approved.md"
_anchor="$(sed -n 's/^Anchor-SHA: *//p' "$SENTINEL_DIR/approved.md" | head -1)"
[ "$_anchor" = "$CLEAN_HEAD" ] \
  || die "sentinel Anchor-SHA ($_anchor) != HEAD ($CLEAN_HEAD) — re-sign the sentinel at current HEAD"
grep -q 'PLAN-157' "$SENTINEL_DIR/approved.md" || die "sentinel does not reference PLAN-157"
# The guarded files this ceremony rewrites MUST be in the signed Scope block.
_scope_block="$(sed -n '/^Scope:/,/END SIGNED SCOPE/p' "$SENTINEL_DIR/approved.md")"
[ -n "$_scope_block" ] || die "sentinel has no Scope: block"
for must in \
  CLAUDE.md \
  .claude/policies/grandfather-cap.policy.yaml \
  .claude/skills/core/ceo-orchestration/SKILL.md \
  .claude/skills/core/architecture-decisions/SKILL.md \
  .claude/skills/core/ai-llm-orchestration/SKILL.md \
  .claude/skills/core/parallelization-by-default/SKILL.md; do
  printf '%s\n' "$_scope_block" | grep -qF "$must" \
    || die "sentinel Scope is missing guarded path: $must — fix + re-sign"
done
echo "    sentinel scope covers all guarded targets"

say "[0/7] Preflight: fold SP signatures (OQ4 waiver = Owner detach-signs each SP)"
for entry in "${SP_SET[@]}"; do
  spfile="${entry%%|*}"
  [ -f "$PROPS/$spfile" ]     || die "staged SP missing: $PROPS/$spfile"
  [ -f "$PROPS/$spfile.asc" ] || die "missing Owner signature $PROPS/$spfile.asc — detach-sign at the ceremony: gpg --local-user $KEY --armor --detach-sign $PROPS/$spfile"
  gpg_verify_owner "$PROPS/$spfile.asc" "$PROPS/$spfile"
done

say "[0/7] Preflight: apply-base sha256 pins (stale-base apply hazard gate)"
if ! shasum -a 256 --check --status "$SUNSET/base-pins.sha256"; then
  shasum -a 256 --check "$SUNSET/base-pins.sha256" 2>&1 | grep -v ': OK$' >&2 || true
  die "apply-base pins DRIFTED — canonical base moved since the pack was built (2026-07-13, base 705562f). REBUILD the pack; do not apply."
fi
echo "    12/12 pins OK"

# =============================================================================
# [1/7] Deletions (OQ2: git-history-only; recovery pointer rides the commit)
# =============================================================================
say "[1/7] Delete 4 squad trees (manifest-verified)"
MUTATING=1
_manifest="$(grep -Ev '^#|^[[:space:]]*$' "$SUNSET/deletion-manifest.txt" | sort)"
_tracked="$(git ls-files -- "${TREES[@]}" | sort)"
if [ "$_manifest" != "$_tracked" ]; then
  diff <(printf '%s\n' "$_manifest") <(printf '%s\n' "$_tracked") >&2 || true
  die "deletion-manifest.txt != tracked files under the 4 trees — rebuild the pack"
fi
git rm -r -q -- "${TREES[@]}"
echo "    removed: ${TREES[*]}"

# =============================================================================
# [2/7] Staged replicas + roster sed
# =============================================================================
say "[2/7] Apply 11 staged full-file replicas"
while IFS= read -r rel; do
  src="$SUNSET/root/$rel"
  [ -f "$src" ] || die "staged file missing: $src"
  [ -f "$rel" ] || die "canonical target missing (replicas only REPLACE existing files): $rel"
  cp "$src" "$rel"
  echo "    applied: $rel"
done < <(cd "$SUNSET/root" && find . -type f | sed 's|^\./||' | sort)

say "[2/7] SQUAD_GRANDFATHER roster sed (32 → 28 names)"
SNIP="$SUNSET/snippets/SQUAD_GRANDFATHER.new"
# BSD sed; the replacement line contains no '|', '&', or '\' (verified at
# pack build), so the '|' delimiter is safe.
sed -i '' -E "s|^SQUAD_GRANDFATHER=\"[^\"]*\"$|$(sed -n 1p "$SNIP")|" \
  .claude/scripts/validate-governance.sh
grep -qxF "$(sed -n 1p "$SNIP")" .claude/scripts/validate-governance.sh \
  || die "SQUAD_GRANDFATHER replacement did not apply"
[ "$(grep -c '^SQUAD_GRANDFATHER=' .claude/scripts/validate-governance.sh)" = 1 ] \
  || die "unexpected extra SQUAD_GRANDFATHER assignment"
echo "    roster line replaced + verified (exactly one assignment)"

# =============================================================================
# [3/7] Fold SPs into .claude/proposals/ + apply diffs; fill pointer
# =============================================================================
say "[3/7] Land fold SPs (SP-043, SP-044, SP-045, SP-046 — SP-047 is W3, SKIPPED)"
for entry in "${SP_SET[@]}"; do
  spfile="${entry%%|*}"
  target="${entry##*|}"
  sp_src="$PROPS/$spfile"
  echo "  -- $spfile"
  # cross-assert the hardcoded target against the SP's own **Target:** line
  grep -qF "**Target:** \`$target\`" "$sp_src" \
    || die "$spfile: **Target:** line does not match expected target $target"
  [ -f "$target" ] || die "fold target missing on disk: $target"
  # extract the FIRST inline ```diff fence and pin-verify it
  dtmp="$TMP_CEREMONY/$spfile.diff"
  awk '/^```diff$/{f=1;next} f&&/^```$/{exit} f' "$sp_src" > "$dtmp"
  [ -s "$dtmp" ] || die "$spfile: could not extract inline diff fence"
  _want_diff="$(fm "$sp_src" sha256_of_diff)"
  _got_diff="$(sha "$dtmp")"
  [ "$_got_diff" = "$_want_diff" ] \
    || die "$spfile: extracted diff sha256 ($_got_diff) != pinned sha256_of_diff ($_want_diff)"
  # apply (git apply is the base-match gate: context mismatch = loud abort)
  git apply --check --whitespace=nowarn "$dtmp" \
    || die "$spfile: diff does not apply cleanly to $target (base drifted?)"
  git apply --whitespace=nowarn "$dtmp"
  # post-apply pin: the SP's sha256_of_staged pins the exact end-state file
  _want_staged="$(fm "$sp_src" sha256_of_staged)"
  _got_staged="$(sha "$target")"
  [ "$_got_staged" = "$_want_staged" ] \
    || die "$spfile: post-apply $target sha256 ($_got_staged) != pinned sha256_of_staged ($_want_staged)"
  # register the proposal (+ Owner signature) in the canonical proposals dir
  cp "$sp_src" ".claude/proposals/$spfile"
  cp "$sp_src.asc" ".claude/proposals/$spfile.asc"
  echo "     applied → $target (staged-hash OK); registered in .claude/proposals/"
done

say "[3/7] Fill pointer.md __LAND_SHA__ (pre-deletion commit = current HEAD)"
sed -i '' "s/__LAND_SHA__/$CLEAN_HEAD/g" "$POINTER"
if grep -q '__LAND_SHA__' "$POINTER"; then
  die "pointer.md still contains __LAND_SHA__ after fill"
fi
echo "    pointer anchored at $CLEAN_HEAD"

# =============================================================================
# [4/7] Regenerate derived surfaces (the ONLY content not byte-staged)
# =============================================================================
say "[4/7] Regen: COMMAND-SKILL-HOOK-MAP"
python3 .claude/scripts/gen-command-skill-hook-map.py --write \
  || die "gen-command-skill-hook-map --write failed"

say "[4/7] Regen: skill inventory block in core SKILL.md"
INV_TMP="$TMP_CEREMONY/inventory.md"
bash .claude/scripts/generate-skill-inventory.sh > "$INV_TMP" \
  || die "generate-skill-inventory.sh failed"
python3 - "$INV_TMP" "$CORE_SKILL" <<'PY'
import pathlib, sys
gen = pathlib.Path(sys.argv[1]).read_text()
skill = pathlib.Path(sys.argv[2])
lines = skill.read_text().splitlines(keepends=True)
B = "<!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->"
E = "<!-- END AUTO-GENERATED SKILL INVENTORY -->"
bi = [i for i, l in enumerate(lines) if l.rstrip("\n") == B]
ei = [i for i, l in enumerate(lines) if l.rstrip("\n") == E]
if len(bi) != 1 or len(ei) != 1 or bi[0] >= ei[0]:
    sys.exit("FATAL: AUTO-GENERATED markers not found exactly once in core SKILL.md")
out = "".join(lines[: bi[0]]) + gen + "".join(lines[ei[0] + 1 :])
skill.write_text(out)
print("    re-embedded %d generated lines" % gen.count("\n"))
PY
bash .claude/scripts/generate-skill-inventory.sh --check \
  || die "skill-inventory idempotency check failed right after re-embed"

# =============================================================================
# [5/7] FULL per-wave check set (reconcile-notes §Post-apply gate set —
#       --fast excludes exactly the exercised families, so: no shortcuts,
#       and the slow full pytest runs too)
# =============================================================================
say "[5/7] Gate 1/9: validate-governance (FULL)"
bash .claude/scripts/validate-governance.sh || die "validate-governance red"

say "[5/7] Gate 2/9: check-claude-md-claims"
python3 .claude/scripts/check-claude-md-claims.py || die "CLAUDE.md claims red"

say "[5/7] Gate 3/9: verify-counts --no-tests"
bash .claude/scripts/local/verify-counts.sh --no-tests || die "verify-counts red"

say "[5/7] Gate 4/9: gen-command-skill-hook-map --check"
python3 .claude/scripts/gen-command-skill-hook-map.py --check || die "map drift after --write (regenerator bug?)"

say "[5/7] Gate 5/9: skill-inventory --check"
bash .claude/scripts/generate-skill-inventory.sh --check || die "skill-inventory drift"

say "[5/7] Gate 6/9: check-install-profiles (glob + disk<->manifest bijection)"
python3 .claude/scripts/check-install-profiles.py || die "install-profiles red"

say "[5/7] Gate 7/9: check-docs-freshness"
python3 .claude/scripts/check-docs-freshness.py --format=text \
  || die "docs-freshness red — expected ZERO new breaks (reconcile surface 7). If a link target newly broke, append the exact bare path (one per line, #fragment stripped) to docs/docs-freshness-allowlist.txt and re-run."

say "[5/7] Gate 8/9: check-tier-boundaries"
python3 .claude/scripts/check-tier-boundaries.py || die "tier-boundaries red"

say "[5/7] Gate 9/9: full pytest (hooks + scripts + optimizer) — slow, not skippable"
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -q \
  || die "pytest red — do not land"

# =============================================================================
# [6/7] Scope assert: touched − scope = ∅, or no commit
# =============================================================================
say "[6/7] Scope assert (touched set vs W1 sentinel scope)"
_scope_re='^(\.claude/skills/domains/(agents-meta|architecture|desktop|dotnet)/'
_scope_re+='|CLAUDE\.md$|README\.md$|INSTALL\.md$'
_scope_re+='|docs/ARCHITECTURE\.md$|docs/GUIA-COMPLETO\.md$|docs/GUIA-COMPLETO\.pt-BR\.md$'
_scope_re+='|docs/COMMAND-SKILL-HOOK-MAP\.md$|docs/docs-freshness-allowlist\.txt$'
_scope_re+='|\.claude/policies/grandfather-cap\.policy\.yaml$'
_scope_re+='|\.claude/scripts/validate-governance\.sh$'
_scope_re+='|\.claude/scripts/tests/test_squad_grandfather_cap\.py$'
_scope_re+='|\.claude/scripts/local/verify-counts\.sh$'
_scope_re+='|\.claude/skills/core/ceo-orchestration/SKILL\.md$'
_scope_re+='|\.claude/skills/core/(architecture-decisions|ai-llm-orchestration|parallelization-by-default)/SKILL\.md$'
_scope_re+='|scripts/profiles/profiles\.json$'
_scope_re+='|\.claude/proposals/SP-04[3-6]-[A-Za-z0-9.-]+\.md(\.asc)?$'
_scope_re+='|\.claude/plans/PLAN-157/'
_scope_re+='|'"${SENTINEL_DIR//./\\.}"'/)'
_touched="$(git status --porcelain=v1 | sed -E 's/^.{3}//; s/^.* -> //')"
[ -n "$_touched" ] || die "nothing touched — apply phase did not run?"
_extras="$(printf '%s\n' "$_touched" | grep -Ev "$_scope_re" || true)"
if [ -n "$_extras" ]; then
  printf '%s\n' "$_extras" >&2
  die "touched files OUTSIDE the W1 scope — touched minus scope must be the empty set; NOT committing"
fi
echo "    touched - scope = (empty set)"

# =============================================================================
# [7/7] Single signed commit (NO auto-push)
# =============================================================================
say "[7/7] git add exact scope + git commit -S"
ADD_PATHS=(
  CLAUDE.md
  README.md
  INSTALL.md
  docs/ARCHITECTURE.md
  docs/GUIA-COMPLETO.md
  docs/GUIA-COMPLETO.pt-BR.md
  docs/COMMAND-SKILL-HOOK-MAP.md
  .claude/policies/grandfather-cap.policy.yaml
  .claude/scripts/validate-governance.sh
  .claude/scripts/tests/test_squad_grandfather_cap.py
  .claude/scripts/local/verify-counts.sh
  .claude/skills/core/ceo-orchestration/SKILL.md
  .claude/skills/core/architecture-decisions/SKILL.md
  .claude/skills/core/ai-llm-orchestration/SKILL.md
  .claude/skills/core/parallelization-by-default/SKILL.md
  scripts/profiles/profiles.json
  .claude/plans/PLAN-157
  "$SENTINEL_DIR"
)
for entry in "${SP_SET[@]}"; do
  spfile="${entry%%|*}"
  ADD_PATHS+=(".claude/proposals/$spfile" ".claude/proposals/$spfile.asc")
done
# contingency only (expected untouched — gate 7 would have died otherwise):
if git status --porcelain=v1 -- docs/docs-freshness-allowlist.txt | grep -q .; then
  ADD_PATHS+=(docs/docs-freshness-allowlist.txt)
fi
git add -- "${ADD_PATHS[@]}"
# the 4 tree deletions were staged by `git rm` in [1/7]

git commit -S -m "feat(PLAN-157): W1 — sunset 4 grandfathered squads + fold SPs + count reconcile

Deletes the desktop, dotnet, architecture, agents-meta squad trees
(PLAN-153 Wave-D imports; OQ2 git-history-only deletion — recovery
pointer with pre-deletion sha rides in w1-sunset-pointer.md).
Folds land as SP-043..SP-046 (Owner-signed, OQ4 soak waived) into
core/architecture-decisions, core/ai-llm-orchestration,
core/parallelization-by-default; staged-hash pins asserted. Roster
triplet commit-atomic 32→28: validate-governance SQUAD_GRANDFATHER,
grandfather-cap policy current+cap:=28 (OQ3), cap test. Count
reconcile 166→160 skills / 116→110 domain / 37→33 profiles across
CLAUDE.md, README, INSTALL, ARCHITECTURE, GUIA twins, verify-counts,
profiles.json; COMMAND-SKILL-HOOK-MAP + skill inventory regenerated.
SP-047 (prisma-patterns move) deferred to W3 per OQ5. Full per-wave
gate set green pre-commit. [SENT-W1]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || die "commit failed"
COMMITTED=1

# =============================================================================
# WRAP — verify + next steps (push is the Owner's explicit act)
# =============================================================================
say "DONE — PLAN-157 W1 landed as ONE signed commit. Review, then push:"
echo "    git log -1 --show-signature"
echo "    git show --stat HEAD | head -60"
echo "    git push origin main"
echo "    gh run watch \$(gh run list --workflow validate.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
echo ""
echo "  Recommended post-land proof (73f9b0e clean-clone pattern, for the"
echo "  changed test file):"
echo "    d=\$(mktemp -d) && git clone --local --quiet . \"\$d\" \\"
echo "      && (cd \"\$d\" && python3 -m pytest .claude/scripts/tests/test_squad_grandfather_cap.py -q)"
echo ""
echo "  Then: tick W1 in .claude/plans/PLAN-157-*.md (next session), and"
echo "  remember prisma-patterns (SP-047) + graduation bundles are W3."
