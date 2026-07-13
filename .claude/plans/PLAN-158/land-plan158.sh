#!/usr/bin/env bash
# =============================================================================
# land-plan158.sh — PLAN-158 Waves 1+2 landing ceremony (Owner runs via `!`).
#
# Release v1.1.0 — npm Trusted Publishing (OIDC) flip + check_adversary
# PII-collision fix. Everything is STAGED + PROVEN (W2: 8/8 regression tests
# in a neutral-layout proof + live positive control; W1: pins asserted, SPEC
# patcher proven idempotent on a copy). This script performs the
# canonical-edit GPG ceremony that lands both waves on main. It is the
# land-plan156.sh pattern: 2 sentinel commits with a PROGRESSIVE anchor,
# the Owner's GPG key signs each sentinel inline. No _KERNEL_PATHS in either
# scope (npm-publish.yml + check_adversary.py + SPEC/v1/npm-shim.md +
# install-npm.sh are all CANONICAL class) — no kernel-override env needed.
#
# ⚠ PREREQUISITE (Owner, npmjs.com web console, BEFORE running this):
#   package ceo-orchestration → Settings → Trusted Publisher →
#     repository = Canhada-Labs/ceo-orchestration
#     workflow   = npm-publish.yml        (the FILENAME, not display name)
#     environment = production-npm
#   Without this registration the GA publish dies ENEEDAUTH (playbook:
#   .claude/plans/PLAN-158/oidc-failure-playbook.md).
#
# Landing order (anchor progressivo, binding):
#   1. SENT-OIDC  npm-publish OIDC flip + auth-doc cascade
#                 (canonical: npm-publish.yml, SPEC/v1/npm-shim.md,
#                  install-npm.sh; unguarded: GOVERNANCE-MAP.md, playbook)
#   2. SENT-ADV   check_adversary SECRETS-only scan (canonical: the hook;
#                 unguarded: regression test)
#
# Each commit: fill anchor from HEAD → write approved.md → detach-sign →
# apply staged files (+ SPEC patch) → assert touched ⊆ scope → commit.
# After landing: push, watch Validate, then proceed to Wave 3 (RC ceremony).
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
STAGED=".claude/plans/PLAN-158/staged"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
export GPG_TTY="${GPG_TTY:-$(tty || true)}"
# NOTE: the Owner-shell apply route (cp/git here) does not trip the
# in-session canonical hooks — those gate Claude's tool calls, not the
# Owner's shell. The signed sentinel IS the authorization record (S261
# precedent).

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- preflight --------------------------------------------------------------
say "Preflight"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
# The PLAN-158 materials (playbook, land script, debate, verdicts) are already
# committed; the ceremony applies ONLY staged overlays. Tree must be clean.
if [ -n "$(git status --porcelain=v1)" ]; then
  git status --short >&2
  die "working tree not clean — commit/stash unrelated changes first"
fi
gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || die "signing key $KEY not in your keyring"
[ -d "$STAGED/wave1/root" ] || die "staged overlays missing — run from the session's repo checkout"
[ -f "$STAGED/wave1/rollback-oidc-to-token.patch" ] || die "rollback patch missing"

# ---- helpers ----------------------------------------------------------------
apply_file() {
  local rel="$2" src="$STAGED/$1/root/$2"
  [ -f "$src" ] || die "staged file missing: $src"
  mkdir -p "$(dirname "$REPO/$rel")"
  cp "$src" "$REPO/$rel"
  echo "    applied: $rel"
}

sign_sentinel() {
  local dir="$1" body="$2"
  local anchor; anchor="$(git rev-parse HEAD)"
  sed "s/__ANCHOR_SHA__/$anchor/" "$body" > "$dir/approved.md"
  rm -f "$dir/approved.md.asc"
  gpg --local-user "$KEY" --armor --detach-sign --output "$dir/approved.md.asc" "$dir/approved.md" \
    || die "GPG signing failed for $dir (run: export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"
  echo "    signed: $dir/approved.md (anchor $anchor)"
}

# =============================================================================
# COMMIT 1 — SENT-OIDC — npm Trusted Publishing flip + auth-doc cascade
# =============================================================================
say "COMMIT 1 / SENT-OIDC — npm-publish OIDC + SPEC/GOVERNANCE-MAP/install-npm cascade"
D=".claude/plans/PLAN-158/architect/sent-oidc"; mkdir -p "$D"
cat > "$D/approved.body.md" <<'BODY'
# SENT-OIDC — PLAN-158 Wave 1 npm Trusted Publishing (OIDC)

Flips npm-publish.yml registry auth from the granular NPM_TOKEN (expires
~2026-09-28) to npm Trusted Publishing: npm CLI >=11.5.1 upgrade step
(Node 20 bundles npm 10.x — without it GA dies ENEEDAUTH) + tokenless
publish step. RC-exclusion, production-npm gate, already_published guard
and --provenance are UNCHANGED (pins asserted). Carries the PLAN-152
§Deferred doc cascade assigned to this flip: SPEC/v1/npm-shim.md
§Publishing (via spec patcher under this sentinel), GOVERNANCE-MAP.md
secret row + workflow row, install-npm.sh auth wording. Rollback diff is
PRE-STAGED and PRE-AUTHORIZED by this sentinel
(staged/wave1/rollback-oidc-to-token.patch — Recovery B of the playbook):
applying EXACTLY that diff to npm-publish.yml needs no fresh sentinel.
Old token REVOKED after first OIDC GA publish (Owner console + rotation
log). OQ1 ratified by Owner S270 ("OIDC nesta release").

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-158
Kernel-Override: (none — no _KERNEL_PATHS in this scope)
Scope:
  - .github/workflows/npm-publish.yml
  - SPEC/v1/npm-shim.md
  - .github/workflows/GOVERNANCE-MAP.md
  - scripts/install-npm.sh
Amends: SPEC/v1/npm-shim.md — §Publishing auth mechanism + version-history
  row 1.1.0 (documentation-of-mechanism; shim contract unchanged). Applied
  via .claude/plans/PLAN-158/staged/spec-patches/apply-spec-npm-shim.py.
<!-- END SIGNED SCOPE -->
BODY
sign_sentinel "$D" "$D/approved.body.md"
apply_file wave1 .github/workflows/npm-publish.yml
apply_file wave1 .github/workflows/GOVERNANCE-MAP.md
apply_file wave1 scripts/install-npm.sh
python3 "$STAGED/spec-patches/apply-spec-npm-shim.py"
# scope assert: touched (vs HEAD) ⊆ scope + sentinel dir
_touched="$(git status --porcelain=v1 | sed -E 's/^.{3}//; s/^.* -> //')"
_bad="$(printf '%s\n' "$_touched" | grep -vE '^(\.github/workflows/(npm-publish\.yml|GOVERNANCE-MAP\.md)|SPEC/v1/npm-shim\.md|scripts/install-npm\.sh|\.claude/plans/PLAN-158/)' || true)"
[ -z "$_bad" ] || { printf '%s\n' "$_bad" >&2; die "touched files outside SENT-OIDC scope"; }
git add .github/workflows/npm-publish.yml .github/workflows/GOVERNANCE-MAP.md \
  scripts/install-npm.sh SPEC/v1/npm-shim.md "$D"
git commit -m "feat(PLAN-158): SENT-OIDC — npm Trusted Publishing (OIDC) + doc cascade

npm-publish.yml: npm CLI >=11.5.1 upgrade step + tokenless OIDC publish
(RC-exclusion / production-npm / already_published / --provenance pins
unchanged); rollback diff pre-staged + pre-authorized. Doc cascade:
SPEC/v1/npm-shim.md §Publishing (spec version 1.1.0), GOVERNANCE-MAP
secret+workflow rows, install-npm.sh wording. NPM_TOKEN revoked after
first OIDC GA proof. [SENT-OIDC]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || die "commit 1 failed"

# =============================================================================
# COMMIT 2 — SENT-ADV — check_adversary SECRETS-only pre-exec scan
# =============================================================================
say "COMMIT 2 / SENT-ADV — check_adversary PII-collision fix"
D=".claude/plans/PLAN-158/architect/sent-adv"; mkdir -p "$D"
cat > "$D/approved.body.md" <<'BODY'
# SENT-ADV — PLAN-158 Wave 2 check_adversary SECRETS-only scan

Spec-conformance fix (debate upgraded from optional; OQ2 ratified by
Owner S270): the E1 §4 pre-exec Bash gate is docstring-scoped to LIVE
CREDENTIALS but scanned ALL_PATTERNS — checksum-valid numeric PII
collisions (S270 live incident: a benign GitHub run id passes the CPF
checksum; br_rg matches ANY bare 8-9 digit run) fail-CLOSED blocked
benign commands with no env escape. Fix: _command_carries_secret now
scans patterns=SECRETS (28 credential families); fallback to the full
catalog if SECRETS is absent (over-block, never under-block). VETO
guardrails (recorded, security critic): NO PII family deleted from the
shared catalog (egress-redaction keeps consuming them); the
unconditional credential fail-closed path untouched; no RC dist-tag npm
publish. Proven: 8/8 regression tests (neutral-layout clean proof) +
live positive control (the unpatched gate ASK-blocked the session's own
command carrying the colliding literal).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-158
Kernel-Override: (none — no _KERNEL_PATHS in this scope)
Scope:
  - .claude/hooks/check_adversary.py
<!-- END SIGNED SCOPE -->
BODY
sign_sentinel "$D" "$D/approved.body.md"
apply_file wave2 .claude/hooks/check_adversary.py
apply_file wave2 .claude/hooks/tests/test_adversary_pii_collision.py
say "Wave-2 gate: adversary test suite"
python3 -m pytest .claude/hooks/tests/ -q -k adversary 2>&1 | tail -3 || die "adversary suite red — do not land"
git add .claude/hooks/check_adversary.py \
  .claude/hooks/tests/test_adversary_pii_collision.py "$D"
git commit -m "fix(PLAN-158): SENT-ADV — check_adversary scans SECRETS families only

The E1 §4 pre-exec gate is spec-scoped to live credentials; ALL_PATTERNS
swept the 11 LGPD/BR PII families too, so checksum-valid numeric
collisions (CPF-shaped GitHub run ids; br_rg on any bare 8-9 digit run)
fail-CLOSED blocked benign commands (S270 incident). SECRETS-only now;
PII stays in the shared catalog for the egress rail; missing-SECRETS
fallback over-blocks. 8/8 regression tests. [SENT-ADV]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || die "commit 2 failed"

# =============================================================================
# WRAP — verify, next steps (plan stays 'executing': Waves 3-4 follow)
# =============================================================================
say "Post-land verification"
bash .claude/scripts/validate-governance.sh --fast 2>&1 | tail -3
python3 .claude/scripts/check-claude-md-claims.py 2>&1 | tail -3 || true

say "DONE — 2 sentinel commits landed. Review, then push:"
echo "    git log --oneline -3"
echo "    git push origin main"
echo ""
echo "  Next (Wave 3 — RC ceremony, after Validate green):"
echo "    1. Codex pair-rail verdict: .claude/governance/pair-rail-verdict-v1.1.0-rc.1.md"
echo "    2. Check the 6 advisory workflows fresh ≤14d (dispatch any stale one)"
echo "    3. Cut signed v1.1.0-rc.1  →  24h RC-hold (full hold, OQ3)"
echo "  Then Wave 4 — GA: fresh verdict (v1.1.0), signed GA tag, approve"
echo "  production-npm, watch the FIRST OIDC publish (playbook at hand),"
echo "  REVOKE the old NPM_TOKEN + record in docs/rotation-log.md."
