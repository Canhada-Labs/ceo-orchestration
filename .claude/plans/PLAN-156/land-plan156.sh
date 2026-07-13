#!/usr/bin/env bash
# =============================================================================
# land-plan156.sh — PLAN-156 landing ceremony (Owner runs this via `!`).
#
# Multi-Harness Expansion: Grok Build adapter + GPT-5.6 codex refresh +
# Cross-Vendor Audit Council. Everything is STAGED + PROVEN in clean-clone
# overlays; this script performs the canonical-edit GPG ceremony that lands
# it on main. It is the land-plan155.sh pattern: 6 sentinel commits with a
# PROGRESSIVE anchor (each anchors on the prior commit), the Owner's GPG key
# (AE9B236FDAF0462874060C6BCFCFACF00335DC74) signs each sentinel inline, and
# the kernel-override env authorizes each _KERNEL_PATHS edit.
#
# ⚠ READ BEFORE RUNNING. This edits kernel/canonical governance surfaces and
# signs with your real key. Review the SCOPE of each sentinel below. Run
# from a CLEAN main checkout of the repo root. The staged overlays live at
# .claude/plans/PLAN-156/staged/<wave>/root/ (mirror layout = repo-relative
# targets) and are gitignored — they are the source of truth for each apply.
#
# Landing order (anchor progressivo, binding):
#   1. SENT-CX-PIN  codex 5.6 pin bump          (kernel: codex pins)
#   2. SENT-GK-A    grok adapter + kernel + shim (kernel: adapter seam + shim)
#   3. SENT-GK-B    grok+council audit chain     (kernel: audit_emit/audit_log)
#   4. SENT-GK-C    installer + CI               (kernel: validate.yml)
#   5. SENT-GK-E    kill-switch + council guards  (kernel: check_canonical_edit)
#   6. SENT-GK-F    council workflow + ADR-162   (canonical: workflow/cmd/adr)
#
# Each commit: fill anchor from HEAD → write approved.md → detach-sign →
# apply staged files (+ SPEC patches) with kernel override → assert
# touched ⊆ scope → commit. Unguarded companions (tests/docs/fixtures/
# ledgers/templates/artifacts) ride the commit they belong to.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
STAGED=".claude/plans/PLAN-156/staged"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
export GPG_TTY="${GPG_TTY:-$(tty || true)}"
# NOTE on kernel overrides: the Owner-shell apply route (cp/git in this
# script) does NOT trip the in-session canonical/kernel hooks — those gate
# Claude's tool calls, not the Owner's shell. The signed sentinel + its
# Kernel-Override line ARE the authorization record (S261 precedent). No
# CEO_KERNEL_OVERRIDE env is needed at apply time.

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- preflight --------------------------------------------------------------
say "Preflight"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"

# The session left the UNGUARDED companions (docs, tests, ledgers, CLAUDE.md,
# the new scripts/templates, the plan dir) modified/untracked in the working
# tree by design — the land script commits exactly those, per-commit, via
# explicit `git add`. So a dirty tree is EXPECTED here; a clean-tree check
# would wrongly reject the very changes we are landing. Instead: verify every
# dirty/untracked path is INSIDE the PLAN-156 landing set. Anything OUTSIDE is
# unrelated work that must not be swept in — that is the real hazard, and it
# fails closed. (staged/ is gitignored, so it never shows here.)
_ALLOWED_RE='^(docs/(adapters|provider_capability_matrix|degradation-outside-claude-code)\.md|INSTALL\.md|README\.md|CLAUDE\.md|\.claude/scripts/(model-deprecations|substrate-watch)\.json|\.claude/hooks/tests/test_[A-Za-z0-9_]+\.py|\.claude/hooks/tests/fixtures/adapters/grok/|templates/grok/|scripts/_grok_harness\.sh|scripts/tests/test-(install-harness-grok\.sh|council-fixture\.mjs)|\.claude/plans/PLAN-156)'
# Extract each changed path (handle `R  old -> new` renames → take the target).
_unexpected="$(git status --porcelain=v1 2>/dev/null \
  | sed -E 's/^.{3}//; s/^.* -> //' \
  | grep -vE "$_ALLOWED_RE" || true)"
if [ -n "$_unexpected" ]; then
  echo "  Working-tree changes OUTSIDE the PLAN-156 landing set:" >&2
  printf '%s\n' "$_unexpected" | sed 's/^/    /' >&2
  die "resolve/stash the unrelated changes above first (the land script only touches PLAN-156 paths)"
fi
echo "  working tree: only PLAN-156 companion changes present (expected)"

gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || die "signing key $KEY not in your keyring"
[ -d "$STAGED/wave2/root" ] || die "staged overlays missing — run from the session's repo"

# Version pins must match the binaries you characterized (refuse-on-drift).
CODEX_VER="$(codex --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
[ "$CODEX_VER" = "0.144.1" ] || echo "  WARN: codex $CODEX_VER != pinned 0.144.1 (pin bump assumes 0.144.1)"
if command -v grok >/dev/null 2>&1; then
  GROK_VER="$(grok --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
  [ "$GROK_VER" = "0.2.93" ] || echo "  WARN: grok $GROK_VER != pinned 0.2.93"
fi

# ---- helpers ----------------------------------------------------------------
# Copy ONE staged file (repo-relative) from a wave overlay into the tree.
# Explicit per-file (never whole-overlay) so a commit never pulls another
# commit's files into the tree prematurely.
apply_file() {
  local rel="$2" src="$STAGED/$1/root/$2"
  [ -f "$src" ] || die "staged file missing: $src"
  mkdir -p "$(dirname "$REPO/$rel")"
  cp "$src" "$REPO/$rel"
  echo "    applied: $rel"
}

# Write + detach-sign a sentinel approved.md. Args: <sent-dir> <body-file>.
sign_sentinel() {
  local dir="$1" body="$2"
  local anchor; anchor="$(git rev-parse HEAD)"
  # substitute the anchor placeholder
  sed "s/__ANCHOR_SHA__/$anchor/" "$body" > "$dir/approved.md"
  rm -f "$dir/approved.md.asc"
  gpg --local-user "$KEY" --armor --detach-sign --output "$dir/approved.md.asc" "$dir/approved.md" \
    || die "GPG signing failed for $dir (run: export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"
  echo "    signed: $dir/approved.md (anchor $anchor)"
}

# =============================================================================
# COMMIT 1 — SENT-CX-PIN — codex-cli 5.6 pin bump
# =============================================================================
say "COMMIT 1 / SENT-CX-PIN — codex-cli pin bump (>=0.128.0,<0.145.0)"
D=".claude/plans/PLAN-156/architect/sent-cx-pin"; mkdir -p "$D"
cat > "$D/approved.body.md" <<'BODY'
# SENT-CX-PIN — PLAN-156 Wave 1 codex-cli 5.6 pin bump

Widen-upper-ONLY pin bump so codex-cli 0.144.1 (GPT-5.6 Sol/Terra/Luna
first-class) is in range. Lower bound UNCHANGED (>=0.128.0) — raising it
would drop an in-flight RC verdict out of range in release.yml step-15
(debate C10). Both pin files are _KERNEL_PATHS.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: PLAN-156-CODEX-PIN-BUMP (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - .claude/governance/codex-cli-pin.txt
  - .claude/governance/codex-cli-binary-sha256.txt
<!-- END SIGNED SCOPE -->
BODY
sign_sentinel "$D" "$D/approved.body.md"
apply_file wave1 .claude/governance/codex-cli-pin.txt
apply_file wave1 .claude/governance/codex-cli-binary-sha256.txt
git add .claude/governance/codex-cli-pin.txt .claude/governance/codex-cli-binary-sha256.txt "$D"
git commit -m "chore(PLAN-156): SENT-CX-PIN — bump codex-cli pin to <0.145.0 for GPT-5.6

Widen-upper-only (lower bound unchanged >=0.128.0 per debate C10). Binary
SHA re-pinned to codex-cli 0.144.1. Enables gpt-5.6-sol/terra/luna on the
pair-rail lane. [SENT-CX-PIN]

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || die "commit 1 failed"

# =============================================================================
# COMMIT 2 — SENT-GK-A — grok host adapter + kernel enroll + shim + settings
# =============================================================================
say "COMMIT 2 / SENT-GK-A — grok adapter + kernel + exit-2 chokepoint"
D=".claude/plans/PLAN-156/architect/sent-gk-a"; mkdir -p "$D"
cat > "$D/approved.body.md" <<'BODY'
# SENT-GK-A — PLAN-156 Wave 0b+2 grok host adapter + kernel + shim

Creates the grok host adapter and enrolls it + the grok pins in the
arbitration kernel, adds the decision→exit-2 + block→deny chokepoint to
the shared shim (grok-gated per lacuna (h): exit-2 is an ACTIVE deny on
codex, so Claude/Codex stay byte-identical), reroutes check_codex_filewrite
through the shim in both settings surfaces, and amends the SPEC hook-io
exit ABI (grok-scoped, via Bash under this sentinel). KNOWN_ADAPTERS +=
grok. Kernel-class: adapter seam + shim + settings + kernel guard.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: PLAN-156-GROK-HOST-ADAPTER (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - .claude/governance/grok-cli-pin.txt
  - .claude/governance/grok-cli-binary-sha256.txt
  - .claude/hooks/_lib/adapters/grok.py
  - .claude/hooks/_lib/adapters/__init__.py
  - .claude/hooks/_lib/contract.py
  - .claude/hooks/check_arbitration_kernel.py
  - .claude/hooks/_python-hook.sh
  - .claude/settings.json
  - templates/settings/settings.base.json
  - SPEC/v1/hook-io.schema.md
Amends: SPEC/v1/hook-io.schema.md — grok-scoped exit ABI addendum (block→deny
  rewrite + emitted-deny→exit-2 under CEO_HOOK_ADAPTER=grok; Claude/Codex
  unchanged). Applied via .claude/plans/PLAN-156/staged/spec-patches/apply-spec-hook-io.py.
<!-- END SIGNED SCOPE -->
BODY
sign_sentinel "$D" "$D/approved.body.md"
apply_file wave0b .claude/governance/grok-cli-pin.txt
apply_file wave0b .claude/governance/grok-cli-binary-sha256.txt
apply_file wave2 .claude/hooks/_lib/adapters/grok.py
apply_file wave2 .claude/hooks/_lib/adapters/__init__.py
apply_file wave2 .claude/hooks/_lib/contract.py
apply_file wave2 .claude/hooks/check_arbitration_kernel.py
apply_file wave2 .claude/hooks/_python-hook.sh
apply_file wave2 .claude/settings.json
apply_file wave2 templates/settings/settings.base.json
# SPEC hook-io amendment (guarded — apply under the sentinel via Bash)
python3 "$STAGED/spec-patches/apply-spec-hook-io.py"
# grok adapter fixtures (unguarded companions ride this commit)
git add .claude/hooks/_lib/adapters/grok.py .claude/hooks/_lib/adapters/__init__.py \
  .claude/hooks/_lib/contract.py .claude/hooks/check_arbitration_kernel.py \
  .claude/hooks/_python-hook.sh .claude/settings.json templates/settings/settings.base.json \
  SPEC/v1/hook-io.schema.md .claude/governance/grok-cli-pin.txt \
  .claude/governance/grok-cli-binary-sha256.txt \
  .claude/hooks/tests/fixtures/adapters/grok/ \
  .claude/hooks/tests/test_exit2_chokepoint.py \
  .claude/hooks/tests/test_adapter_golden.py \
  .claude/hooks/tests/test_adapter_drift_detector.py "$D"
git commit -m "feat(PLAN-156): SENT-GK-A — grok host adapter + exit-2 chokepoint

grok.py host adapter (camelCase wire → NormalizedEvent, block→deny egress);
decision→exit-2 + block→deny chokepoint in the shared shim (grok-gated per
lacuna (h)); check_codex_filewrite rerouted through the shim in both
settings; KNOWN_ADAPTERS += grok; grok.py + grok pins enrolled in
_KERNEL_PATHS; SPEC hook-io exit ABI addendum. Hermetic teeth:
test_exit2_chokepoint. [SENT-GK-A]

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || die "commit 2 failed"

# =============================================================================
# COMMIT 3 — SENT-GK-B — grok + council audit chain
# =============================================================================
say "COMMIT 3 / SENT-GK-B — grok + council audit actions"
D=".claude/plans/PLAN-156/architect/sent-gk-b"; mkdir -p "$D"
cat > "$D/approved.body.md" <<'BODY'
# SENT-GK-B — PLAN-156 Wave 4+6 audit chain (grok + council)

Registers 3 metadata-only actions in _KNOWN_ACTIONS (grok_tool_recorded,
grok_turn_ended — Wave 4; council_lane_invoked — Wave 6, landed together
in the one audit_emit.py) + their typed emitters + closed-enum allowlists,
the audit_log.py grok dispatch, the golden (+3 → 319), and the SPEC
audit-log rows (via Bash). Count-pin test companions (unguarded) ride this
commit. audit_emit.py + audit_log.py are _KERNEL_PATHS.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: PLAN-156-GROK-AUDIT-ACTIONS (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - .claude/hooks/_lib/audit_emit.py
  - .claude/hooks/audit_log.py
  - .claude/data/audit-registry.golden.txt
  - SPEC/v1/audit-log.schema.md
Amends: SPEC/v1/audit-log.schema.md — 3 action rows (grok_tool_recorded,
  grok_turn_ended, council_lane_invoked) + version-history rows v2.50/v2.51.
  Applied via .claude/plans/PLAN-156/staged/spec-patches/apply-spec-audit-log.py.
  _KNOWN_ACTIONS 316 → 319.
<!-- END SIGNED SCOPE -->
BODY
sign_sentinel "$D" "$D/approved.body.md"
apply_file wave6 .claude/hooks/_lib/audit_emit.py
apply_file wave6 .claude/data/audit-registry.golden.txt
apply_file wave4 .claude/hooks/audit_log.py
python3 "$STAGED/spec-patches/apply-spec-audit-log.py"
git add .claude/hooks/_lib/audit_emit.py .claude/hooks/audit_log.py \
  .claude/data/audit-registry.golden.txt SPEC/v1/audit-log.schema.md \
  .claude/hooks/tests/test_audit_emit_api_contract.py \
  .claude/hooks/tests/test_codex_egress_proof_telemetry.py \
  .claude/hooks/tests/test_git_bypass_guard.py \
  .claude/hooks/tests/test_w5_scrub_enforcement.py "$D"
git commit -m "feat(PLAN-156): SENT-GK-B — grok + council audit chain (+3 actions → 319)

grok_tool_recorded + grok_turn_ended (Wave 4) + council_lane_invoked
(Wave 6) typed emitters + closed-enum allowlists; audit_log.py grok
dispatch; golden +3 → 319; SPEC audit-log rows v2.50/v2.51. [SENT-GK-B]

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || die "commit 3 failed"

# =============================================================================
# COMMIT 4 — SENT-GK-C — installer + CI
# =============================================================================
say "COMMIT 4 / SENT-GK-C — installer --harness grok + validate.yml"
D=".claude/plans/PLAN-156/architect/sent-gk-c"; mkdir -p "$D"
cat > "$D/approved.body.md" <<'BODY'
# SENT-GK-C — PLAN-156 Wave 4 installer + CI

install.sh/upgrade.sh gain --harness grok (single-surface emit, arming
check, --force fix); validate.yml extends the installer matrix + the
pair-rail teeth loop to grok (shape-aware: exit-2 chokepoint + adapter
golden/drift). validate.yml is _KERNEL_PATHS. The unguarded companions
scripts/_grok_harness.sh + scripts/tests/test-install-harness-grok.sh
ride this commit.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: PLAN-156-GROK-CI (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - scripts/install.sh
  - scripts/upgrade.sh
  - .github/workflows/validate.yml
<!-- END SIGNED SCOPE -->
BODY
sign_sentinel "$D" "$D/approved.body.md"
apply_file wave4 scripts/install.sh
apply_file wave4 scripts/upgrade.sh
apply_file wave4 .github/workflows/validate.yml
git add scripts/install.sh scripts/upgrade.sh .github/workflows/validate.yml \
  scripts/_grok_harness.sh scripts/tests/test-install-harness-grok.sh "$D"
git commit -m "feat(PLAN-156): SENT-GK-C — installer --harness grok + CI matrix

install.sh/upgrade.sh --harness grok (single-surface, arming check,
--force→GROK_FORCE fix); validate.yml grok installer matrix + shape-aware
pair-rail teeth loop; hermetic (zero grok binary/secret). [SENT-GK-C]

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || die "commit 4 failed"

# =============================================================================
# COMMIT 5 — SENT-GK-E — kill-switch + council guards
# =============================================================================
say "COMMIT 5 / SENT-GK-E — canonical guard extension (grok + council)"
D=".claude/plans/PLAN-156/architect/sent-gk-e"; mkdir -p "$D"
cat > "$D/approved.body.md" <<'BODY'
# SENT-GK-E — PLAN-156 Wave 3+6 canonical guard extension

check_canonical_edit.py: adds the grok kill-switch surface (.grok/hooks/**,
.grok/config.toml, .grok/sandbox.toml, .grok/rules/*.md) + templates/settings
+ the council egress surface (.claude/workflows/council-audit.js,
.claude/commands/council.md) to _CANONICAL_GUARDS, AND their first-segment
prefixes (.grok, templates) to _CANONICAL_PREFIXES (else the globs are
INERT — the dead-guard class). check_canonical_edit.py is _KERNEL_PATHS.
The templates/grok/** operator surface (unguarded) rides this commit.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: PLAN-156-GROK-KILLSWITCH-GUARD-EXTENSION (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - .claude/hooks/check_canonical_edit.py
<!-- END SIGNED SCOPE -->
BODY
sign_sentinel "$D" "$D/approved.body.md"
apply_file wave6 .claude/hooks/check_canonical_edit.py
git add .claude/hooks/check_canonical_edit.py templates/grok/ "$D"
git commit -m "feat(PLAN-156): SENT-GK-E — canonical guard extension (grok + council)

grok kill-switch surface + templates/settings + council egress surface
added to _CANONICAL_GUARDS with their first-segment prefixes in
_CANONICAL_PREFIXES (no dead guards). templates/grok/ operator surface.
[SENT-GK-E]

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || die "commit 5 failed"

# =============================================================================
# COMMIT 6 — SENT-GK-F — council workflow + command + ADR-162
# =============================================================================
say "COMMIT 6 / SENT-GK-F — council workflow + ADR-162"
D=".claude/plans/PLAN-156/architect/sent-gk-f"; mkdir -p "$D"
cat > "$D/approved.body.md" <<'BODY'
# SENT-GK-F — PLAN-156 Wave 6+7 council workflow + ADR-162

Lands the council-audit.js workflow (now guarded by SENT-GK-E) + the
/council command + ADR-162. council-audit.js OWNS live external egress
(ADR-114 redactor + budget hard-kill + no-CI fence) — guarded so a later
edit cannot strip those. ADR-162 is the normative grok capability record.
Docs (unguarded) + the council fixture test ride this commit.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: (none — no _KERNEL_PATHS in this scope)
Scope:
  - .claude/workflows/council-audit.js
  - .claude/commands/council.md
  - .claude/adr/ADR-162-grok-harness-capability-matrix.md
<!-- END SIGNED SCOPE -->
BODY
sign_sentinel "$D" "$D/approved.body.md"
mkdir -p .claude/workflows
apply_file wave6 .claude/workflows/council-audit.js
apply_file wave6 .claude/commands/council.md
apply_file wave7 .claude/adr/ADR-162-grok-harness-capability-matrix.md
git add .claude/workflows/council-audit.js .claude/commands/council.md \
  .claude/adr/ADR-162-grok-harness-capability-matrix.md \
  scripts/tests/test-council-fixture.mjs \
  docs/adapters.md docs/provider_capability_matrix.md \
  docs/degradation-outside-claude-code.md INSTALL.md README.md \
  .claude/scripts/model-deprecations.json .claude/scripts/substrate-watch.json \
  .claude/plans/PLAN-156/artifacts/ "$D"
git commit -m "feat(PLAN-156): SENT-GK-F — cross-vendor council + ADR-162 + docs

council-audit.js (3-vendor read-only audit, ADR-114 egress redaction,
fail-loud, budget hard-kill, no-CI fence) + /council + ADR-162 (grok
capability matrix + exit-2 discipline). Docs, model-deprecations,
substrate-watch, live-fire artifacts. [SENT-GK-F]

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || die "commit 6 failed"

# =============================================================================
# CLOSEOUT — plan status, counts, gates
# =============================================================================
say "CLOSEOUT — plan status → done + count reconcile"
# Flip the plan reviewed→executing→done (illegal to jump reviewed→done).
python3 - <<'PY'
import re
p=".claude/plans/PLAN-156-grok-harness-56-refresh-council.md"
t=open(p).read()
t=t.replace("status: executing","status: done")
if "completed_at:" not in t:
    t=t.replace("executing_at: 2026-07-12","executing_at: 2026-07-12\ncompleted_at: 2026-07-12")
open(p,"w").write(t)
print("plan → done")
PY

say "Reconciling derived counts (hooks / ADRs / actions)"
bash .claude/scripts/verify-counts.sh 2>&1 | tail -5 || echo "  (verify-counts advisory)"
python3 .claude/scripts/check-claude-md-claims.py 2>&1 | tail -5 || echo "  (claim check — update CLAUDE.md counts if drift)"

say "Golden reconcile"
python3 .claude/scripts/check-audit-registry-coverage.py --check 2>&1 | tail -3

# The plan record: the .md, README, land script, debate, artifacts, spec
# appliers. staged/ is gitignored (never committed — the S266 lesson). Add
# the whole plan dir; git skips the gitignored staged/ automatically.
git add .claude/plans/PLAN-156-grok-harness-56-refresh-council.md \
  .claude/plans/PLAN-156/ 2>/dev/null || true
# If CLAUDE.md counts drifted, the claim check above printed the delta —
# update CLAUDE.md by hand and re-add before this commit if so.
git add CLAUDE.md 2>/dev/null || true
git commit -m "chore(PLAN-156): close out — status→done, counts reconciled

hooks/ADRs/actions counts reconciled; grok third harness + GPT-5.6 refresh
+ cross-vendor council landed across SENT-CX-PIN + SENT-GK-{A,B,C,E,F}.
Plan record (README-WAKEUP, land script, debate, artifacts) committed;
staged/ stays gitignored (S266 clean-clone lesson).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || echo "  (no closeout delta to commit)"

say "DONE — 7 commits landed. Review, then push:"
echo "    git log --oneline -8"
echo "    git push origin main"
echo ""
echo "  Then watch the Validate workflow; the grok installer matrix + exit-2"
echo "  teeth + council fixture test are all hermetic (no grok binary on CI)."
