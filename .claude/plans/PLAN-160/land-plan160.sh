#!/usr/bin/env bash
# =============================================================================
# land-plan160.sh — PLAN-160 canonical-edit hardening ceremony (Owner runs `!`).
#
# S276 council findings A/C/D on check_canonical_edit.py (a _KERNEL_PATHS
# entry). Everything canonical is STAGED under .claude/plans/PLAN-160/staged/**
# (gitignored — the staged tree never lands; the ceremony COPIES it over
# canonical). ONE segment (single blast radius — the kernel gate + its 2 ADRs):
#
#   check_canonical_edit.py        (KERNEL: CEO_KERNEL_OVERRIDE for this apply)
#   .claude/adr/ADR-164-*.md       (findings A + C — multi-candidate + fail-closed)
#   .claude/adr/ADR-165-*.md       (finding D — shared-predicate dual-anchor)
#
# The finding-A/C/D fix bytes + the 2 ADRs are gitignored (staged/); their
# integrity is pinned by a TRACKED manifest (.claude/plans/PLAN-160/inputs.sha256,
# `shasum -c` fail-closed in preflight). The Wave-1 regression test file
# (.claude/hooks/tests/test_canonical_edit_council_findings.py) is NOT in this
# ceremony — it already landed on main via normal commits.
#
# The ADR add (178 -> 180) bumps the CLAUDE.md ADR-count claim (CI-enforced by
# check-claude-md-claims.py, tolerance=0) + 7 unwatched docs (README x2,
# ARCHITECTURE, GUIA x2, FAQ, npm/README) for consistency (S275 drift lesson).
# CHANGELOG v1.1.0 lines stay 178 (historical snapshot). Count-surface docs are
# UNGUARDED and ride the ceremony commit.
#
# PREFLIGHT runs EVERYTHING before any GPG sign: branch, tree pristine, origin
# sync, Validate green on HEAD, GPG key present, staged-input manifest
# (`shasum -c`), kernel basepin vs canonical, a BEHAVIORAL oracle probe that
# FAILS unless the staged bytes actually block a {granted, ungranted}
# multi-candidate smuggle (never sign a claim the bytes do not hold), the named
# regression set in STAGED mode, and a count-cascade dry-check.
#
# Usage:
#   bash .claude/plans/PLAN-160/land-plan160.sh --dry-run
#   bash .claude/plans/PLAN-160/land-plan160.sh
#
# --dry-run does everything except gpg + git add/commit, then RESTORES every
# applied file (trap on ANY exit). Origin-sync / Validate / gpg-key soften to
# WARN in dry-run. No auto-push.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
PLAN_DIR=".claude/plans/PLAN-160"
STAGED="$PLAN_DIR/staged"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
OVERRIDE_SLUG="PLAN-160-CANONICAL-HARDENING"
GPG_TTY="${GPG_TTY:-$(tty || true)}"
export GPG_TTY
# NOTE: the Owner-shell apply route (cp/git here) does not trip the in-session
# canonical hooks — those gate Claude's tool calls, not the Owner's shell. The
# signed sentinel IS the authorization record (S261 precedent). The
# kernel-override export below is the ADR-031 declaration for the kernel file.

DRY_RUN=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  "") ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 64 ;;
esac

START_SHA="$(git rev-parse HEAD)"
RESTORE_HINT="nothing was changed — safe to rerun after fixing the cause"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/land-plan160.XXXXXX")"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARN: %s\033[0m\n' "$*" >&2; }
die()  {
  printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2
  printf '\033[1;31mRESTORE: %s\033[0m\n' "$RESTORE_HINT" >&2
  exit 1
}

# ---- canonical file set (sentinel scope mirrors this) -----------------------
ADR_164=".claude/adr/ADR-164-canonical-multicandidate-and-failclosed.md"
ADR_165=".claude/adr/ADR-165-canonical-shared-predicate-dual-anchor.md"
KERNEL=".claude/hooks/check_canonical_edit.py"
# staged sources
S_KERNEL="$STAGED/check_canonical_edit.py"
S_ADR164="$STAGED/adr/$(basename "$ADR_164")"
S_ADR165="$STAGED/adr/$(basename "$ADR_165")"

# Count-surface docs (178 -> 180). CLAUDE.md is CI-enforced; the rest are
# consistency-only. Each entry: "<file>::<from>::<to>" applied with a
# context-anchored sed so an unrelated "178" is never touched.
COUNT_DOCS=(
  "CLAUDE.md"
  "README.md"
  "README.pt-BR.md"
  "docs/ARCHITECTURE.md"
  "docs/GUIA-COMPLETO.md"
  "docs/GUIA-COMPLETO.pt-BR.md"
  "docs/FAQ.md"
  "npm/README.md"
)

RE_SCOPE='^(\.claude/hooks/check_canonical_edit\.py|\.claude/adr/ADR-16[45]-[a-z0-9-]+\.md)$'
RE_COUNT='^(CLAUDE\.md|README\.md|README\.pt-BR\.md|docs/ARCHITECTURE\.md|docs/GUIA-COMPLETO\.md|docs/GUIA-COMPLETO\.pt-BR\.md|docs/FAQ\.md|npm/README\.md)$'
RE_PLANS='^\.claude/plans/'

touched_files() { git status --porcelain=v1 | sed -E 's/^.{3}//; s/^.* -> //'; }

assert_touched() {
  local allowed="$1" label="$2" bad
  bad="$(touched_files | grep -vE "$allowed" || true)"
  if [ -n "$bad" ]; then
    printf '%s\n' "$bad" >&2
    die "touched files outside $label scope (touched − scope != ∅)"
  fi
  echo "    touched ⊆ scope OK ($label)"
}

# ---- preflight ---------------------------------------------------------------
say "Preflight (ALL checks run BEFORE any GPG sign)"

[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
command -v python3 >/dev/null || die "python3 not found"
command -v shasum  >/dev/null || die "shasum not found"

say "Tree state (must be PRISTINE — every canonical file comes from staged/)"
assert_touched "${RE_PLANS}" "pre-ceremony allowed-dirt (plan materials only)"

for f in "$S_KERNEL" "$S_ADR164" "$S_ADR165"; do
  [ -f "$f" ] || die "staged input missing: $f (the pack is machine-local — run from the session checkout that built it)"
done

# Staged-input manifest (tracked) — staged/ is gitignored, so the bytes the
# sentinel authorizes MUST be pinned by a tracked hash (S275 lesson).
say "Staged-input manifest (shasum -c, fail-closed)"
MANIFEST="$PLAN_DIR/inputs.sha256"
[ -f "$MANIFEST" ] || die "manifest missing: $MANIFEST (regenerate before ceremony)"
git ls-files --error-unmatch "$MANIFEST" >/dev/null 2>&1 || die "manifest $MANIFEST is not tracked — commit it first (its whole point is to be tamper-evident)"
( cd "$REPO" && shasum -a 256 -c "$MANIFEST" ) || die "staged-input manifest MISMATCH — the staged bytes drifted from the signed manifest; regenerate + re-review before signing"

# Origin sync (WARN-only under --dry-run).
say "Origin sync"
if git fetch origin main --quiet 2>/dev/null; then
  if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    if [ "$DRY_RUN" = 1 ]; then warn "HEAD != origin/main (push/pull first for the real run)"
    else die "HEAD != origin/main — push the ceremony materials (or pull) first"; fi
  else echo "    HEAD == origin/main"; fi
else
  if [ "$DRY_RUN" = 1 ]; then warn "git fetch origin failed (offline?) — origin-sync unchecked"
  else die "git fetch origin main failed — cannot verify origin sync"; fi
fi

# Validate green on HEAD (WARN-only under --dry-run).
say "Validate on HEAD"
if command -v gh >/dev/null; then
  _head="$(git rev-parse HEAD)"
  _v="$(gh run list --workflow validate.yml --branch main --limit 20 \
        --json headSha,status,conclusion \
        --jq "map(select(.headSha==\"$_head\")) | .[0] | \"\(.status) \(.conclusion)\"" \
        2>/dev/null || true)"
  if [ "$_v" = "completed success" ]; then echo "    Validate green on $_head"
  else
    if [ "$DRY_RUN" = 1 ]; then warn "Validate on HEAD is '${_v:-<none>}' (need completed+success for the real run)"
    else die "Validate on HEAD is '${_v:-<no run found>}' — need completed+success for $_head"; fi
  fi
else
  if [ "$DRY_RUN" = 1 ]; then warn "gh not found — Validate-on-HEAD unchecked"
  else die "gh not found — cannot verify Validate on HEAD"; fi
fi

# GPG key (WARN-only under --dry-run).
say "GPG key"
if gpg --list-secret-keys "$KEY" >/dev/null 2>&1; then echo "    signing key present"
else
  if [ "$DRY_RUN" = 1 ]; then warn "signing key $KEY not in keyring (required for the real run)"
  else die "signing key $KEY not in your keyring"; fi
fi

# Kernel basepin: the staged fix was authored against THIS canonical sha256.
say "Kernel basepin vs canonical"
BASEPIN="$PLAN_DIR/check_canonical_edit.py.basepin"
[ -f "$BASEPIN" ] || die "basepin missing: $BASEPIN"
pinned="$(grep -oE '[0-9a-f]{64}' "$BASEPIN" | head -1)"
[ -n "$pinned" ] || die "unparseable basepin (no sha256): $BASEPIN"
cur="$(shasum -a 256 "$KERNEL" | awk '{print $1}')"
[ "$cur" = "$pinned" ] || die "BASEPIN DRIFT: $KERNEL canonical=$cur pinned=$pinned — rebase the staged fix before signing"
echo "    basepin OK ($KERNEL)"

# New-ADR collision: the 2 ADR files must not already exist canonically.
for adr in "$ADR_164" "$ADR_165"; do
  [ -f "$adr" ] && die "$adr already exists canonically — resolve before ceremony"
done
echo "    ADR paths free (no collision)"

# Behavioral oracle probe (STAGED bytes): the sentinel claims the finding-A
# fix — refuse to sign unless the staged hook actually BLOCKS a
# {granted, ungranted} multi-candidate smuggle AND allows single-granted.
say "Behavioral oracle probe (finding-A fix present in staged bytes)"
python3 - "$S_KERNEL" <<'PYEOF' || die "A-fix oracle probe FAILED — the staged bytes do not carry the finding-A fix; do NOT sign"
import sys, os, json, subprocess, tempfile, pathlib
staged = sys.argv[1]
tmp = pathlib.Path(tempfile.mkdtemp())
(tmp / ".claude").mkdir()
(tmp / ".claude" / "team.md").write_text("t")
(tmp / ".claude" / "frontend-team.md").write_text("f")
sdir = tmp / ".claude" / "plans" / "PLAN-201" / "architect" / "round-1"
sdir.mkdir(parents=True)
(sdir / "approved.md").write_text(
    "---\nplan: PLAN-201\nround: 1\ntype: architect-sentinel\n---\n\n"
    "Approved-By: @Canhada-Labs deadbeef\nApproved-At: 2026-04-13T15:30:00Z\n"
    "Scope:\n  - .claude/team.md\n"
)
env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp),
       "CEO_SENTINEL_UNLOCK": "PLAN-160-oracle-probe", "CEO_SENTINEL_UNLOCK_ACK": "I-ACCEPT"}
granted = str(tmp / ".claude" / "team.md")
ungranted = str(tmp / ".claude" / "frontend-team.md")
def decide(paths):
    ev = {"hook_event_name": "PreToolUse", "session_id": "probe",
          "tool_name": "mcp__x__bulk", "tool_input": {"path": paths, "content": "x"}}
    p = subprocess.run([sys.executable, staged], input=json.dumps(ev),
                       capture_output=True, text=True, env=env, timeout=30)
    return json.loads(p.stdout).get("decision", "allow")
# granted-first smuggle MUST block (the bug allowed it); single-granted MUST allow.
assert decide([granted, ungranted]) == "block", "SMUGGLE NOT BLOCKED (A-fix absent)"
assert decide([ungranted, granted]) == "block", "smuggle (reordered) not blocked"
assert decide([granted]) == "allow", "single-granted wrongly blocked (fixture/over-block)"
print("    A-fix oracle probe OK (smuggle blocked both orders; single-granted allowed)")
PYEOF

# Named regression set, STAGED mode (the committed test file points at the
# staged bytes via PLAN160_HOOK_PATH).
say "Named regression set (STAGED mode)"
PLAN160_HOOK_PATH="$REPO/$S_KERNEL" python3 -m pytest \
  .claude/hooks/tests/test_canonical_edit_council_findings.py -q \
  || die "council-findings repros RED in staged mode"
# And HEAD-mode must still be CI-green (xfails intact).
python3 -m pytest .claude/hooks/tests/test_canonical_edit_council_findings.py -q \
  || die "council-findings file RED on HEAD (CI would break)"

# Count-cascade dry-check: after apply the on-disk ADR count is 180 and every
# count surface will say 180.
say "Count-cascade dry-check (178 -> 180)"
_disk_now="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
[ "$_disk_now" = "178" ] || warn "on-disk ADR count is $_disk_now (expected 178 pre-apply) — verify the count bump targets"
for d in "${COUNT_DOCS[@]}"; do
  [ -f "$d" ] || die "count-surface doc missing: $d"
  grep -qE '178' "$d" || warn "no '178' token in $d — count bump may be a no-op there"
done

say "Preflight PASSED — no signature has been made yet"

# ---- helpers -----------------------------------------------------------------
APPLIED_PREEXISTING=()
APPLIED_NEW=()

apply_cp() {
  local rel="$1" src="$2"
  [ -f "$src" ] || die "staged source missing at apply time: $src"
  if [ -f "$rel" ]; then APPLIED_PREEXISTING+=("$rel"); else APPLIED_NEW+=("$rel"); fi
  mkdir -p "$(dirname "$REPO/$rel")"
  cp "$src" "$REPO/$rel"
  echo "    applied: $rel"
}

bump_counts() {
  # Context-anchored 178 -> 180 for ADR-count claims only.
  local d
  for d in "${COUNT_DOCS[@]}"; do
    APPLIED_PREEXISTING+=("$d")
    # Only the ADR-context occurrences: "178 ADR", "178 architecture",
    # "178 Architecture", "**178**" in an ADR table row, "(178 to date)".
    sed -i.bak -E \
      -e 's/178( ADR)/180\1/g' \
      -e 's/178( architecture decision)/180\1/g' \
      -e 's/178( Architecture Decision)/180\1/g' \
      -e 's/\*\*178\*\*/**180**/g' \
      -e 's/\(178 to date\)/(180 to date)/g' \
      "$d"
    rm -f "$d.bak"
    echo "    count-bumped: $d"
  done
}

sign_sentinel() {
  local dir="$PLAN_DIR/architect/round-1" body="$PLAN_DIR/architect/round-1/approved.body.md" anchor
  [ -f "$body" ] || die "sentinel body missing: $body"
  grep -q '__ANCHOR_SHA__' "$body" || die "sentinel body has no __ANCHOR_SHA__ placeholder: $body"
  anchor="$(git rev-parse HEAD)"
  if [ "$DRY_RUN" = 1 ]; then
    sed "s/__ANCHOR_SHA__/$anchor/" "$body" > "$SCRATCH/approved.preview.md"
    echo "    [dry-run] sentinel render OK -> $SCRATCH/approved.preview.md (anchor $anchor)"
    return 0
  fi
  sed "s/__ANCHOR_SHA__/$anchor/" "$body" > "$dir/approved.md"
  rm -f "$dir/approved.md.asc"
  gpg --local-user "$KEY" --armor --detach-sign --output "$dir/approved.md.asc" "$dir/approved.md" \
    || die "GPG signing failed (run: export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"
  echo "    signed: $dir/approved.md (anchor $anchor)"
}

restore_dry_run() {
  if [ "${#APPLIED_PREEXISTING[@]}" -eq 0 ] && [ "${#APPLIED_NEW[@]}" -eq 0 ]; then return 0; fi
  say "[dry-run] restoring applied files"
  if [ "${#APPLIED_PREEXISTING[@]}" -gt 0 ]; then
    git checkout --quiet -- ${APPLIED_PREEXISTING[@]+"${APPLIED_PREEXISTING[@]}"}
  fi
  for f in ${APPLIED_NEW[@]+"${APPLIED_NEW[@]}"}; do rm -f "$f"; done
  APPLIED_PREEXISTING=(); APPLIED_NEW=()
  echo "    restored — tree back to pre-ceremony state"
}
if [ "$DRY_RUN" = 1 ]; then trap restore_dry_run EXIT; fi

# =============================================================================
# APPLY (single segment)
# =============================================================================
say "SEGMENT — canonical hardening (kernel + 2 ADRs + count bumps)"
export CEO_KERNEL_OVERRIDE="$OVERRIDE_SLUG"
export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
echo "    kernel override EXPORTED: CEO_KERNEL_OVERRIDE=$OVERRIDE_SLUG"
RESTORE_HINT="git checkout -- $KERNEL ${COUNT_DOCS[*]}; rm -f $ADR_164 $ADR_165"

sign_sentinel
apply_cp "$KERNEL"  "$S_KERNEL"
apply_cp "$ADR_164" "$S_ADR164"
apply_cp "$ADR_165" "$S_ADR165"
bump_counts

if [ "$DRY_RUN" = 1 ]; then
  assert_touched "${RE_SCOPE}|${RE_COUNT}|${RE_PLANS}" "dry-run apply"
else
  assert_touched "${RE_SCOPE}|${RE_COUNT}|${RE_PLANS}" "ceremony apply"
fi

# ---- post-apply verification (CANONICAL mode) -------------------------------
say "Post-apply verification (canonical bytes)"
# CLAUDE.md ADR-count claim must now match the on-disk count (CI gate).
python3 .claude/scripts/check-claude-md-claims.py \
  || die "post-apply: check-claude-md-claims.py RED (ADR-count claim drift)"
# The council repros run GREEN against the now-canonical fixed hook (no
# PLAN160_HOOK_PATH — canonical IS the fix).
python3 -m pytest .claude/hooks/tests/test_canonical_edit_council_findings.py -q \
  || die "post-apply: council-findings repros RED against canonical"
# The direct-import canonical suites (no regression).
python3 -m pytest .claude/hooks/tests/ -q -k "canonical" \
  || die "post-apply: hooks canonical set RED"
# Behavioral oracle probe against the NOW-canonical hook.
python3 - "$KERNEL" <<'PYEOF' || die "post-apply A-fix oracle probe FAILED against canonical"
import sys, os, json, subprocess, tempfile, pathlib
staged = sys.argv[1]
tmp = pathlib.Path(tempfile.mkdtemp())
(tmp / ".claude").mkdir()
(tmp / ".claude" / "team.md").write_text("t")
(tmp / ".claude" / "frontend-team.md").write_text("f")
sdir = tmp / ".claude" / "plans" / "PLAN-201" / "architect" / "round-1"
sdir.mkdir(parents=True)
(sdir / "approved.md").write_text(
    "---\nplan: PLAN-201\nround: 1\ntype: architect-sentinel\n---\n\n"
    "Approved-By: @Canhada-Labs deadbeef\nApproved-At: 2026-04-13T15:30:00Z\n"
    "Scope:\n  - .claude/team.md\n"
)
env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp),
       "CEO_SENTINEL_UNLOCK": "PLAN-160-oracle-probe", "CEO_SENTINEL_UNLOCK_ACK": "I-ACCEPT"}
g = str(tmp / ".claude" / "team.md"); u = str(tmp / ".claude" / "frontend-team.md")
def decide(paths):
    ev = {"hook_event_name": "PreToolUse", "session_id": "probe",
          "tool_name": "mcp__x__bulk", "tool_input": {"path": paths, "content": "x"}}
    p = subprocess.run([sys.executable, staged], input=json.dumps(ev),
                       capture_output=True, text=True, env=env, timeout=30)
    return json.loads(p.stdout).get("decision", "allow")
assert decide([g, u]) == "block" and decide([u, g]) == "block" and decide([g]) == "allow"
print("    post-apply A-fix oracle probe OK")
PYEOF

unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
echo "    kernel override UNSET"

if [ "$DRY_RUN" = 1 ]; then
  restore_dry_run
  say "[dry-run] DONE — full rehearsal green (no signature, no commit). Run without --dry-run to land."
  exit 0
fi

# ---- commit ------------------------------------------------------------------
say "Commit (-S signed)"
git add "$KERNEL" "$ADR_164" "$ADR_165" "${COUNT_DOCS[@]}" "$PLAN_DIR"
assert_touched "${RE_SCOPE}|${RE_COUNT}|${RE_PLANS}" "pre-commit"
git -c user.signingkey="$KEY" commit -S -m "fix(PLAN-160): canonical-edit gate hardening — council findings A/C/D [SENT-PLAN160]

check_canonical_edit.py (_KERNEL_PATHS): finding A most-restrictive-wins
multi-candidate scan (emit-once, _find_sentinels lazy+guarded, cap 512
fail-closed, scan fault fail-CLOSED via _forced_out bypassing decide());
finding C decide() resolve fault fail-CLOSED (canonical_edit_hook_fault,
F-01-07); finding D _is_canonical dual-anchor via single-source
_repo_rels/_canonical_rel, made TOTAL (except Exception) so a symlink-loop
RuntimeError cannot fail-open the scan. Shared predicate → the
--is-canonical oracle too. ADR-164 (A+C), ADR-165 (D). ADR count 178->180.

Wave-1 repros (test_canonical_edit_council_findings.py, already landed):
HEAD 9p/5skip/5xf, --runxfail fails exactly 5, STAGED 19p; clean-clone
mirror full hooks suite green. Pair-rail: codex round-2 APPROVE (no
findings), security round-2 (VETO resolved). CEO_KERNEL_OVERRIDE=$OVERRIDE_SLUG
for this apply only (ADR-031).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || die "commit failed"
RESTORE_HINT="git reset --hard $START_SHA (the ceremony commit is in the reflog)"

# =============================================================================
say "DONE — 1 sentinel commit landed. Review, then push:"
echo "    git log --oneline -1 && git verify-commit HEAD"
echo "    git push origin main"
echo ""
echo "  Watch Validate:"
echo "    gh run watch \$(gh run list --workflow validate.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')"
echo ""
echo "  Rollback (before push): git reset --hard $START_SHA"
echo "  Rollback (after push):  git revert HEAD"
