#!/usr/bin/env bash
# =============================================================================
# land-followup.sh — PLAN-156-FOLLOWUP landing ceremony (Owner runs via `!`).
#
# Council live-fire S270 findings F1-F7. Everything canonical is STAGED
# under .claude/plans/PLAN-156-FOLLOWUP/staged/root/** (gitignored — the
# staged tree never lands; the ceremony COPIES it over canonical).
# Unguarded fixes + new tests were written DIRECTLY to their real paths
# and ride the segment commits. land-plan158.sh pattern: sentinel commits
# with a PROGRESSIVE anchor, Owner GPG key signs each sentinel inline.
#
# TWO segments (debate consensus C3 — independent rollback of the
# widest-blast-radius change):
#   A. FU-MAIN   F1+F2+F7+F6+F4 — redactor CLI, verify fail-loud,
#                council.md invocation pin, exit-2 structural parse,
#                trust-probe exact parse (+ all their tests).
#   B. FU-KERNEL F3+F5 — check_canonical_edit.py (a _KERNEL_PATHS entry:
#                workflows-class guard glob + --is-canonical oracle) +
#                the gate flip + parity test. CEO_KERNEL_OVERRIDE is
#                exported for THIS segment only and unset after.
#
# PREFLIGHT runs EVERYTHING before any GPG sign: branch, tree state,
# origin sync, Validate green on HEAD, key present, every basepin matches
# canonical sha256 (abort on drift), full named test set in STAGED mode,
# the shellcheck gate, and a behavioral oracle probe that FAILS unless the staged
# guard really carries the F3 class glob (a sentinel must never sign a
# claim the staged bytes do not hold).
#
# Usage:
#   bash .claude/plans/PLAN-156-FOLLOWUP/land-followup.sh --dry-run
#   bash .claude/plans/PLAN-156-FOLLOWUP/land-followup.sh
#
# --dry-run does everything except gpg + git add/commit: preflight,
# sentinel-body render preview (scratch dir), staged apply, per-segment
# touched-vs-scope asserts, post-apply canonical test set — then RESTORES
# the applied canonical files. Origin-sync / Validate / gpg-key checks
# soften to WARN in dry-run (exercisable offline and without the key).
#
# Every failure aborts with a restore hint. No auto-push.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
PLAN_DIR=".claude/plans/PLAN-156-FOLLOWUP"
STAGED_ROOT="$PLAN_DIR/staged/root"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
OVERRIDE_SLUG="PLAN-156-FOLLOWUP-GUARD-GLOB"
GPG_TTY="${GPG_TTY:-$(tty || true)}"
export GPG_TTY
# NOTE: the Owner-shell apply route (cp/git here) does not trip the
# in-session canonical hooks — those gate Claude's tool calls, not the
# Owner's shell. The signed sentinel IS the authorization record (S261
# precedent). The kernel-override export below is the C3/ADR-031
# declaration for segment B and covers any git-hook path that consults it.

DRY_RUN=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  "") ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 64 ;;
esac

START_SHA="$(git rev-parse HEAD)"
RESTORE_HINT="nothing was changed — safe to rerun after fixing the cause"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/land-followup.XXXXXX")"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARN: %s\033[0m\n' "$*" >&2; }
die()  {
  printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2
  printf '\033[1;31mRESTORE: %s\033[0m\n' "$RESTORE_HINT" >&2
  exit 1
}

# ---- segment file sets (exact — the sentinel scopes mirror these) ----------
# Staged canonical copies (applied by this ceremony).
STAGED_A=(
  ".claude/hooks/_lib/codex_egress_redact.py"
  ".claude/hooks/_lib/tests/test_redactor_cli.py"
  ".claude/workflows/council-audit.js"
  ".claude/commands/council.md"
  ".claude/hooks/_python-hook.sh"
)
STAGED_A+=(
  "scripts/_grok_harness.sh"
  "scripts/tests/test-council-fixture.mjs"
  ".claude/scripts/tests/test_redactor_cli_matrix.py"
  ".claude/scripts/tests/test_council_verify_semantics.py"
  ".claude/scripts/tests/test_grok_trust_probe.py"
  ".claude/hooks/tests/test_python_hook_exit_map.py"
)
STAGED_B=(
  ".claude/hooks/check_canonical_edit.py"
  ".claude/hooks/tests/test_workflows_class_guard.py"
  "templates/grok/pre-push-review-gate.sh"
  ".claude/scripts/tests/test_fingerprint_parity.py"
)
# S272 reconcile: the unguarded fixes + new tests are ALSO applied from
# staged/root (they were originally written straight to canonical, which
# left the tree dirty and put tests for not-yet-landed fixes on canonical
# paths — the pre-push suite runs those red). Staged-only keeps the tree
# pristine until the ceremony and makes this script self-contained.

# Anchored allowlist regexes for the touched-vs-scope asserts.
RE_SCOPE_A='^(\.claude/hooks/_lib/codex_egress_redact\.py|\.claude/hooks/_lib/tests/test_redactor_cli\.py|\.claude/workflows/council-audit\.js|\.claude/commands/council\.md|\.claude/hooks/_python-hook\.sh|scripts/_grok_harness\.sh|scripts/tests/test-council-fixture\.mjs|\.claude/scripts/tests/test_redactor_cli_matrix\.py|\.claude/scripts/tests/test_council_verify_semantics\.py|\.claude/scripts/tests/test_grok_trust_probe\.py|\.claude/hooks/tests/test_python_hook_exit_map\.py)$'
RE_SCOPE_B='^(\.claude/hooks/check_canonical_edit\.py|\.claude/hooks/tests/test_workflows_class_guard\.py|templates/grok/pre-push-review-gate\.sh|\.claude/scripts/tests/test_fingerprint_parity\.py)$'
RE_PLANS='^\.claude/plans/'

touched_files() {
  git status --porcelain=v1 | sed -E 's/^.{3}//; s/^.* -> //'
}

# assert_touched <allowed-regex> <label> — mantra: touched − scope = ∅,
# or no commit.
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
command -v python3  >/dev/null || die "python3 not found"
command -v shasum   >/dev/null || die "shasum not found"
command -v shellcheck >/dev/null || die "shellcheck not found (wave check: shellcheck -S warning)"

# Tree state: the ONLY allowed dirt is (a) the direct-written fix/test
# files this ceremony commits, (b) plan-dir materials (sentinel bodies,
# other plans' scripts — never swept in: adds below are explicit paths).
say "Tree state (must be PRISTINE — every file comes from staged/root)"
RESTORE_HINT="a leftover applied copy from an aborted run? restore with: git checkout -- <file>, and rm any file this script creates"
assert_touched "${RE_PLANS}" "pre-ceremony allowed-dirt (plan materials only)"
RESTORE_HINT="nothing was changed — safe to rerun after fixing the cause"
for rel in "${STAGED_A[@]}" "${STAGED_B[@]}"; do
  [ -f "$STAGED_ROOT/$rel" ] || die "staged file missing: $STAGED_ROOT/$rel (the pack is machine-local — run from the session checkout that built it)"
done

# Origin sync (WARN-only under --dry-run: exercisable offline).
say "Origin sync"
if git fetch origin main --quiet 2>/dev/null; then
  if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    if [ "$DRY_RUN" = 1 ]; then warn "HEAD != origin/main (push/pull first for the real run)"
    else die "HEAD != origin/main — push the ceremony materials (or pull) first"; fi
  else
    echo "    HEAD == origin/main"
  fi
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
  if [ "$_v" = "completed success" ]; then
    echo "    Validate green on $_head"
  else
    if [ "$DRY_RUN" = 1 ]; then warn "Validate on HEAD is '$_v' (need 'completed success' for the real run)"
    else die "Validate on HEAD is '${_v:-<no run found>}' — need a completed+success run for $_head"; fi
  fi
else
  if [ "$DRY_RUN" = 1 ]; then warn "gh not found — Validate-on-HEAD unchecked"
  else die "gh not found — cannot verify Validate on HEAD"; fi
fi

# GPG key (WARN-only under --dry-run: dry-run must run without the key).
say "GPG key"
if gpg --list-secret-keys "$KEY" >/dev/null 2>&1; then
  echo "    signing key present"
else
  if [ "$DRY_RUN" = 1 ]; then warn "signing key $KEY not in keyring (required for the real run)"
  else die "signing key $KEY not in your keyring"; fi
fi

# Basepins: every staged/root/** .basepin must match its canonical file
# sha256 (rebase-drift gate — REBASE the staged copy if canonical moved).
say "Basepins vs canonical"
_pins=0
while IFS= read -r pin; do
  rel="${pin#"$STAGED_ROOT"/}"; rel="${rel%.basepin}"
  pinned="$(grep -oE '[0-9a-f]{64}' "$pin" | head -1)"
  [ -n "$pinned" ] || die "unparseable basepin (no sha256): $pin"
  [ -f "$rel" ] || die "basepin exists but canonical file missing: $rel"
  cur="$(shasum -a 256 "$rel" | awk '{print $1}')"
  [ "$cur" = "$pinned" ] || die "BASEPIN DRIFT: $rel canonical=$cur pinned=$pinned — rebase the staged copy before signing"
  echo "    pin OK: $rel"
  _pins=$((_pins + 1))
done < <(find "$STAGED_ROOT" -name '*.basepin' | sort)
[ "$_pins" -ge 5 ] || die "expected >=5 basepins under $STAGED_ROOT, found $_pins"

# Staged file presence + new-canonical-file collision check.
say "Staged copies present"
for rel in "${STAGED_A[@]}" "${STAGED_B[@]}"; do
  [ -f "$STAGED_ROOT/$rel" ] || die "staged copy missing: $STAGED_ROOT/$rel"
done
# test_redactor_cli.py is a NEW canonical file (no basepin): it must not
# already exist with different content.
_newf=".claude/hooks/_lib/tests/test_redactor_cli.py"
if [ -f "$_newf" ] && ! cmp -s "$_newf" "$STAGED_ROOT/$_newf"; then
  die "$_newf already exists canonically and differs from staged — resolve before ceremony"
fi

# Behavioral oracle probe (F3+F5, staged copy): the FU-KERNEL sentinel
# claims the workflows-CLASS glob — refuse to proceed unless the staged
# guard actually classifies a sibling AND a nested .js as canonical.
say "Oracle probe (staged guard: F3 class glob + F5 CLI)"
probe_oracle() {
  local oracle="$1" out line spec
  out="$(CLAUDE_PROJECT_DIR="$REPO" python3 "$oracle" --is-canonical \
        .claude/workflows/council-audit.js \
        .claude/workflows/evil-sibling-probe.js \
        .claude/workflows/sub/nested-probe.js \
        .claude/commands/council.md \
        tmp/fu-not-canonical-probe.txt)" \
    || die "oracle CLI failed (exit != 0): $oracle"
  for spec in \
    ".claude/workflows/council-audit.js:1" \
    ".claude/workflows/evil-sibling-probe.js:1" \
    ".claude/workflows/sub/nested-probe.js:1" \
    ".claude/commands/council.md:1" \
    "tmp/fu-not-canonical-probe.txt:0"; do
    line="$(printf '%s\t%s' "${spec%:*}" "${spec##*:}")"
    if ! printf '%s\n' "$out" | grep -qxF "$line"; then
      printf '%s\n' "$out" >&2
      case "$spec" in
        *-probe.js:1)
          die "F3 GAP: oracle did not classify '${spec%:*}' as canonical — the staged check_canonical_edit.py carries the F5 oracle but NOT the F3 workflows-class glob. Stage the F3 hunk (guard '.claude/workflows/**/*.js' as a CLASS) before the ceremony." ;;
      esac
      die "oracle probe mismatch: expected '${spec%:*} -> ${spec##*:}' ($oracle)"
    fi
  done
  echo "    oracle probe OK ($oracle)"
}
probe_oracle "$STAGED_ROOT/.claude/hooks/check_canonical_edit.py"

# Named regression set, STAGED mode (tests resolve staged copies through
# CEO_FU_STAGED_ROOT; canonical files are still pre-fix here).
say "Named test set (STAGED mode)"
export CEO_FU_STAGED_ROOT="$REPO/$STAGED_ROOT"
python3 -m pytest "$STAGED_ROOT/.claude/hooks/_lib/tests/test_redactor_cli.py" \
  "$STAGED_ROOT/.claude/scripts/tests/test_redactor_cli_matrix.py" -q \
  || die "F1 smoke suites red (staged mode)"
python3 -m pytest "$STAGED_ROOT/.claude/scripts/tests/test_council_verify_semantics.py" -q \
  || die "F2/F7 council verify semantics red (staged mode)"
python3 -m pytest .claude/hooks/tests/ -q -k "canonical or python_hook" \
  || die "hooks canonical/python_hook set red (staged mode)"
python3 -m pytest .claude/hooks/tests/test_codex_stop_review.py \
  "$STAGED_ROOT/.claude/hooks/tests/test_workflows_class_guard.py" \
  "$STAGED_ROOT/.claude/hooks/tests/test_python_hook_exit_map.py" \
  "$STAGED_ROOT/.claude/scripts/tests/test_grok_trust_probe.py" \
  "$STAGED_ROOT/.claude/scripts/tests/test_fingerprint_parity.py" -q \
  || die "W3 named set red (staged mode)"
if command -v node >/dev/null; then
  node "$STAGED_ROOT/scripts/tests/test-council-fixture.mjs" >/dev/null \
    || die ".mjs council fixture red (staged mode)"
  echo "    .mjs council fixture green"
else
  warn "node not found — .mjs fixture skipped (Python mirror is the CI-load-bearing set)"
fi
unset CEO_FU_STAGED_ROOT

# Repo meta-gates — the two live-corpus linters that scan EVERY test file
# and redden the python matrix (PLAN-119 WS-C audit isolation; env
# hygiene). Pre-apply this catches violations in the direct-written
# tests; the post-apply matrix pass re-runs them over the applied staged
# tests too.
say "Repo meta-gates (test audit-isolation + env-hygiene)"
python3 -m pytest .claude/scripts/tests/test_check_test_audit_isolation.py \
  .claude/scripts/tests/test_check_test_env_hygiene.py -q \
  || die "repo meta-gates red — a new test file violates audit-isolation (use self.subprocess_env(), never a minimal env=) or env-hygiene (derive from TestEnvContext, not bare unittest.TestCase); fix the flagged files before ceremony"

say "Shellcheck / bash -n on touched shells"
shellcheck -S warning "$STAGED_ROOT/scripts/_grok_harness.sh" \
  "$STAGED_ROOT/templates/grok/pre-push-review-gate.sh" \
  || die "shellcheck -S warning red on staged shells"
bash -n "$STAGED_ROOT/scripts/_grok_harness.sh" \
  && bash -n "$STAGED_ROOT/templates/grok/pre-push-review-gate.sh" \
  || die "bash -n red on staged shells"

say "Preflight PASSED — no signature has been made yet"

# ---- helpers -----------------------------------------------------------------
APPLIED_PREEXISTING=()   # canonical files overwritten (dry-run restore: git checkout)
APPLIED_NEW=()           # canonical files created    (dry-run restore: rm)

apply_file() {
  local rel="$1" src="$STAGED_ROOT/$1"
  [ -f "$src" ] || die "staged file missing at apply time: $src"
  if [ -f "$rel" ]; then APPLIED_PREEXISTING+=("$rel"); else APPLIED_NEW+=("$rel"); fi
  mkdir -p "$(dirname "$REPO/$rel")"
  cp "$src" "$REPO/$rel"
  echo "    applied: $rel"
}

# sign_sentinel <dir> — render approved.md from approved.body.md with
# anchor = HEAD, then GPG detach-sign. Dry-run renders a PREVIEW into the
# scratch dir only (never writes approved.md, never signs).
sign_sentinel() {
  local dir="$1" body="$1/approved.body.md" anchor
  [ -f "$body" ] || die "sentinel body missing: $body"
  grep -q '__ANCHOR_SHA__' "$body" || die "sentinel body has no __ANCHOR_SHA__ placeholder: $body"
  anchor="$(git rev-parse HEAD)"
  if [ "$DRY_RUN" = 1 ]; then
    sed "s/__ANCHOR_SHA__/$anchor/" "$body" > "$SCRATCH/$(basename "$dir").approved.preview.md"
    echo "    [dry-run] sentinel render OK -> $SCRATCH/$(basename "$dir").approved.preview.md (anchor $anchor)"
    return 0
  fi
  sed "s/__ANCHOR_SHA__/$anchor/" "$body" > "$dir/approved.md"
  rm -f "$dir/approved.md.asc"
  gpg --local-user "$KEY" --armor --detach-sign --output "$dir/approved.md.asc" "$dir/approved.md" \
    || die "GPG signing failed for $dir (run: export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"
  echo "    signed: $dir/approved.md (anchor $anchor)"
}

restore_dry_run() {
  # ${arr[@]+...} guards: empty-array expansion is an unbound-variable
  # error under `set -u` on bash 3.2 (macOS system bash).
  if [ "${#APPLIED_PREEXISTING[@]}" -eq 0 ] && [ "${#APPLIED_NEW[@]}" -eq 0 ]; then
    return 0
  fi
  say "[dry-run] restoring applied canonical files"
  if [ "${#APPLIED_PREEXISTING[@]}" -gt 0 ]; then
    git checkout --quiet -- ${APPLIED_PREEXISTING[@]+"${APPLIED_PREEXISTING[@]}"}
  fi
  for f in ${APPLIED_NEW[@]+"${APPLIED_NEW[@]}"}; do rm -f "$f"; done
  APPLIED_PREEXISTING=(); APPLIED_NEW=()
  echo "    restored — tree back to pre-ceremony state"
}

# A dry-run that ABORTS after the apply step (e.g. a red post-apply gate —
# exactly what the dry-run exists to catch) must still hand the tree back
# clean; otherwise the operator restores canonical files by hand and every
# other ceremony's clean-tree preflight blocks. Fire on ANY exit.
if [ "$DRY_RUN" = 1 ]; then
  trap restore_dry_run EXIT
fi

# =============================================================================
# SEGMENT A — FU-MAIN — F1+F2+F7+F6+F4 (everything EXCEPT the kernel file)
# =============================================================================
say "SEGMENT A / FU-MAIN — redactor CLI + verify fail-loud + council.md + exit-2 map + trust probe"
DA="$PLAN_DIR/architect/fu-main"
RESTORE_HINT="git checkout -- <applied canonical files>; rm the new $_newf; direct-write files were never touched by this script"
sign_sentinel "$DA"
for rel in "${STAGED_A[@]}"; do apply_file "$rel"; done
assert_touched "${RE_SCOPE_A}|${RE_SCOPE_B}|${RE_PLANS}" "FU-MAIN (segment-B files pending, tolerated)"
if [ "$DRY_RUN" = 1 ]; then
  echo "    [dry-run] skipping git add/commit for FU-MAIN"
else
  git add "${STAGED_A[@]}" "$DA"
  git -c user.signingkey="$KEY" commit -S -m "fix(PLAN-156-FOLLOWUP): FU-MAIN — council egress redactor CLI + verify fail-loud + grok-rail probes

F1 codex_egress_redact.py: script-safe import + fail-CLOSED --outgoing
CLI (any internal error -> exit!=0 + EMPTY stdout, never echo input);
council-audit.js folds redact->send into one pipe under pipefail.
F2: verify_failed split from explicit unverifiable; CLEAN iff lanes>=3
AND confirmed==0 AND verify_failed==0; count surfaced in the report.
F7 re-anchored to the /council -> Workflow boundary (council.md).
F6 _python-hook.sh exit-2 map: structural top-level JSON parse, dual
fail semantics (deny-token+parse-failure -> exit 2; infra fail-open
preserved). F4 _grok_harness.sh trust probe: exact-entry parse against
the characterized grok 0.2.93 schema, NOT-ARMED on any ambiguity.
Tests: _lib smoke + 3.9-3.12 matrix mirrors + exit-map + trust-probe +
council fixture (.mjs local). [FU-MAIN]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || die "FU-MAIN commit failed"
  RESTORE_HINT="git reset --hard $START_SHA (FU-MAIN commit is in the reflog; direct-write files are inside it — recover via reflog, not checkout)"
fi

# =============================================================================
# SEGMENT B — FU-KERNEL — F3 guard glob + F5 oracle (kernel override scoped
# to THIS segment only — consensus C3, ADR-031)
# =============================================================================
say "SEGMENT B / FU-KERNEL — check_canonical_edit.py (_KERNEL_PATHS) + gate flip + parity test"
DB="$PLAN_DIR/architect/fu-kernel"
export CEO_KERNEL_OVERRIDE="$OVERRIDE_SLUG"
export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
echo "    kernel override EXPORTED for this segment: CEO_KERNEL_OVERRIDE=$OVERRIDE_SLUG"
sign_sentinel "$DB"
for rel in "${STAGED_B[@]}"; do apply_file "$rel"; done
if [ "$DRY_RUN" = 1 ]; then
  # Segment-A files are uncommitted in dry-run (no commits happen) —
  # tolerate them here; the real run asserts the strict B-only set.
  assert_touched "${RE_SCOPE_A}|${RE_SCOPE_B}|${RE_PLANS}" "FU-KERNEL (dry-run: segment-A uncommitted, tolerated)"
else
  assert_touched "${RE_SCOPE_B}|${RE_PLANS}" "FU-KERNEL"
fi
if [ "$DRY_RUN" = 1 ]; then
  echo "    [dry-run] skipping git add/commit for FU-KERNEL"
else
  git add "${STAGED_B[@]}" "$DB"
  git -c user.signingkey="$KEY" commit -S -m "fix(PLAN-156-FOLLOWUP): FU-KERNEL — workflows-class guard glob + canonical-path oracle (F3+F5)

check_canonical_edit.py: .claude/workflows JS guarded as a CLASS
(sibling CREATE is the attack, not only edit) + read-only
--is-canonical oracle CLI — one predicate for guard, recorder and gate.
templates/grok/pre-push-review-gate.sh: classifier flips to the oracle
shell-out, ONE aggregate fingerprint over the whole pushed range,
coarse fallback retained solely as the fail-CLOSED oracle-failure path.
Coverage delta enumerated in the signed sentinel (C2(e)).
CEO_KERNEL_OVERRIDE=$OVERRIDE_SLUG (+ACK) exported for this segment
only, unset after (C3, ADR-031). [FU-KERNEL]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || die "FU-KERNEL commit failed"
  RESTORE_HINT="git reset --hard $START_SHA (BOTH ceremony commits are in the reflog)"
fi
unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
echo "    kernel override UNSET (segment B closed)"
if [ "$DRY_RUN" != 1 ]; then
  # Final invariant: after both segment commits, nothing may remain
  # touched outside plan materials.
  assert_touched "$RE_PLANS" "post-ceremony (only plan materials may remain)"
fi

# =============================================================================
# POST-APPLY — flip to CANONICAL mode (no CEO_FU_STAGED_ROOT) and re-prove
# =============================================================================
say "Post-apply verification (CANONICAL mode — CEO_FU_STAGED_ROOT unset)"

# W1 Check, LITERAL council-audit.js:145 shape as a subprocess from repo
# root (never python3 -m — that masks the run-as-file failure class).
_red_out="$(printf 'x' | python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing)" \
  || die "W1 literal check failed: canonical redactor CLI exit != 0"
[ -n "$_red_out" ] || die "W1 literal check failed: canonical redactor CLI emitted empty stdout on benign input"
echo "    W1 literal redactor invocation OK"

python3 -m pytest .claude/hooks/_lib/tests/test_redactor_cli.py \
  .claude/scripts/tests/test_redactor_cli_matrix.py -q \
  || die "post-apply F1 smoke red (canonical)"
python3 -m pytest .claude/scripts/tests/test_council_verify_semantics.py -q \
  || die "post-apply council verify semantics red (canonical)"
python3 -m pytest .claude/hooks/tests/ -q -k "canonical or python_hook" \
  || die "post-apply hooks canonical/python_hook set red"
python3 -m pytest .claude/hooks/tests/test_codex_stop_review.py \
  .claude/scripts/tests/test_grok_trust_probe.py \
  .claude/scripts/tests/test_fingerprint_parity.py -q \
  || die "post-apply W3 named set red"
if command -v node >/dev/null; then
  node scripts/tests/test-council-fixture.mjs >/dev/null \
    || die "post-apply .mjs council fixture red"
fi
# NOTE: the staged-if-exists-style tests (exit-map / trust-probe /
# parity) still resolve the staged copies while the staged tree is on
# disk — post-apply those bytes are IDENTICAL to canonical (cp), and the
# strictly-canonical proofs are the literal invocation above, the
# module-level-resolved F1/F2 suites, and the oracle probe below.
# (A CEO_FU_STAGED_ROOT=. force-flip was tried and rejected: relative
# resolution breaks under the tests' own scratch-cwd subprocesses.)
# Canonical oracle now carries F3+F5 — same behavioral probe as preflight.
probe_oracle ".claude/hooks/check_canonical_edit.py"
# Matrix dir quick pass (3.9-3.12 CI home for the mirrored assertions;
# includes the meta-gates over the now-applied staged tests). Serial run
# is ~12 min; use xdist when available (~3.5 min).
if python3 -c "import xdist" >/dev/null 2>&1; then
  python3 -m pytest .claude/scripts/tests/ -q -n auto \
    || die "post-apply matrix-dir quick pass red"
else
  python3 -m pytest .claude/scripts/tests/ -q \
    || die "post-apply matrix-dir quick pass red"
fi

if [ "$DRY_RUN" = 1 ]; then
  restore_dry_run
  say "[dry-run] DONE — full rehearsal green (no signature, no commit). Run without --dry-run to land."
  exit 0
fi

# =============================================================================
# WRAP — push + watch instructions (NO auto-push)
# =============================================================================
say "DONE — 2 sentinel commits landed (FU-MAIN + FU-KERNEL). Review, then push:"
echo "    git log --oneline -3"
echo "    git verify-commit HEAD HEAD~1        # both segments are -S signed"
echo "    git push origin main"
echo ""
echo "  Watch Validate:"
echo "    gh run watch \$(gh run list --workflow validate.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')"
echo ""
echo "  Rollback (independent segments, by design):"
echo "    FU-KERNEL only:  git revert HEAD          # F3+F5, widest blast radius"
echo "    both:            git reset --hard $START_SHA   # before push only"
echo ""
echo "  Next (Wave 4 — full-quorum live-fire, Owner-gated; see"
echo "  $PLAN_DIR/staged/LAND-README.md):"
echo "    1. cp templates/grok/sandbox.toml.example ~/.grok/sandbox.toml (review first)"
echo "    2. /council on .claude/hooks/ — 3-lane quorum, no concurrent codex"
echo "    3. planted employer-class token redaction proof + fail-loud crash check"
