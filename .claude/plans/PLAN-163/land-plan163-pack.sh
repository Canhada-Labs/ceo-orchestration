#!/usr/bin/env bash
# =============================================================================
# land-plan163-pack.sh — PLAN-163 main-pack ceremony (Owner runs `!`).
# Modeled on land-plan161.sh; SECOND of the two declared PLAN-163 ceremonies.
#
# HARD ENTRY GATE (plan §Gates, order GATE-PIN → GATE-V2 → review → pack):
#   --confirm-gate-pin-done   Owner asserts the pin ceremony landed
#   --confirm-gate-v2-fresh   Owner asserts GATE-V2 PASS on the POST-anchor
#                             set (land-plan163-pin.sh --gate-v2)
# plus a mechanical check that the `[SENT-PLAN163-PIN]` commit exists in log.
# The natural 168h expiry (~2026-08-03) does NOT satisfy GATE-V2 — only a
# fresh post-anchor PASS does (S283 any-in-window correction).
#
# Scope: .claude/plans/PLAN-163/staged/main-pack/ (43 files, consolidated
# MANIFEST.sha256 — incl. SPEC/v1/audit-log.schema.md v2.53 appended by the
# docs/spec thread; for settings.json + settings.base.json the valid hashes
# are the MANIFEST-B4 era ones, already reflected in the consolidated file,
# which is AUTHORITATIVE). Integrity rail = the TRACKED twin
# `.claude/plans/PLAN-163/inputs-pack.sha256` (S274 lesson).
#
# W2 pre-step: the non-canonical live-tree fixes (audit-telemetry presence
# fixes + siblings + their two oracles) are committed in their OWN
# `fix(PLAN-163): W2 ...` commit BEFORE the ceremony — never inside the
# sentinel-scoped ceremony commit.
#
# KERNEL surfaces (settings.json, validate.yml, audit_emit.py) land under
# the declared token CEO_KERNEL_OVERRIDE=PLAN-163-T3-EVENT-ACTIONS
# (precedent PLAN-161-C5-LIVENESS-ACTIONS). SPEC surfaces are deny-Edit and
# applied via cp under the sentinel.
#
# COUNTS: this ceremony does NOT edit CLAUDE.md (cache discipline). It
# VALIDATES the mechanical post-apply counts (hooks 55→57, wired 44→46,
# registrations 46→48, ADRs 182→184 — inclui ADR-110-AMEND-1 do PLAN-164) and PRINTS the closeout deltas; the
# CLAUDE.md/docs closeout commit must land BEFORE push.
#
# Usage:
#   bash .claude/plans/PLAN-163/land-plan163-pack.sh --preflight-only
#   bash .claude/plans/PLAN-163/land-plan163-pack.sh --dry-run
#   bash .claude/plans/PLAN-163/land-plan163-pack.sh \
#        --confirm-gate-pin-done --confirm-gate-v2-fresh
#
# --dry-run: everything except gpg + git add/commit (incl. the W2 commit —
# reported only); restores tree AND index on ANY exit (trap, S273 lesson).
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO" || exit 1
PLAN_DIR=".claude/plans/PLAN-163"
STAGED="$PLAN_DIR/staged/main-pack"
MANIFEST_STAGED="$STAGED/MANIFEST.sha256"
MANIFEST_TRACKED="$PLAN_DIR/inputs-pack.sha256"
SENTINEL_DIR="$PLAN_DIR/architect/round-2-pack"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
GPG_TTY="${GPG_TTY:-$(tty || true)}"
export GPG_TTY
export CEO_OVERHEAD_ACK=1

DRY_RUN=0
PREFLIGHT_ONLY=0
CONFIRM_PIN=0
CONFIRM_V2=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --preflight-only) DRY_RUN=1; PREFLIGHT_ONLY=1 ;;
    --confirm-gate-pin-done) CONFIRM_PIN=1 ;;
    --confirm-gate-v2-fresh) CONFIRM_V2=1 ;;
    *) echo "usage: $0 [--dry-run|--preflight-only] --confirm-gate-pin-done --confirm-gate-v2-fresh" >&2; exit 64 ;;
  esac
done

START_SHA="$(git rev-parse HEAD)"
RESTORE_HINT="nothing was changed — safe to rerun after fixing the cause"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/land-plan163-pack.XXXXXX")"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARN: %s\033[0m\n' "$*" >&2; }
die()  {
  printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2
  printf '\033[1;31mRESTORE: %s\033[0m\n' "$RESTORE_HINT" >&2
  exit 1
}

manifest_rows()  { awk '/^[0-9a-f]{64}/ {print $1 "\t" $2 "\t" $4}' "$MANIFEST_TRACKED"; }
manifest_dests() { manifest_rows | cut -f3 | sort; }
touched_files()  { git status --porcelain=v1 | sed -E 's/^.{3}//; s/^.* -> //'; }

# ---- W2 file set (non-canonical live-tree fixes, committed pre-ceremony) ----
W2_MODIFIED="
.claude/scripts/audit-telemetry.py
.claude/scripts/budget-summary.py
.claude/scripts/ceo-cost.py
.claude/scripts/cost-table.yaml
.claude/scripts/detectors/overpowered.py
.claude/scripts/detectors/tests/test_overpowered.py
.claude/scripts/detectors/wasteful_thinking.py
scripts/local/smoke-install-parity.sh
"
W2_NEW="
.claude/scripts/tests/test_model_fleet_presence.py
scripts/tests/test-parity-stale-planted.sh
"
# NOTE: scripts/local/smoke-install-parity.sh is BOTH a W2 live edit and a
# main-pack entry (staged bytes differ — verified at draft time). The W2
# commit records the intermediate state; the ceremony commit supersedes it
# with the reviewed staged bytes. Both states are test-gated.

# =============================================================================
# ENTRY GATE
# =============================================================================
say "Entry gate — GATE-PIN + GATE-V2 must precede this ceremony"
PIN_SHA="$(git log --format='%H' --grep='\[SENT-PLAN163-PIN\]' -n 1 || true)"
if [ -z "$PIN_SHA" ]; then
  die "no [SENT-PLAN163-PIN] commit in log — run land-plan163-pin.sh first (gate order is mandatory)"
fi
echo "    pin ceremony commit found: $(git log --oneline -1 "$PIN_SHA")"
if [ "$CONFIRM_PIN" -ne 1 ] || [ "$CONFIRM_V2" -ne 1 ]; then
  if [ "$DRY_RUN" = 1 ]; then
    warn "confirmation flags absent — allowed in rehearsal, REQUIRED for the real run"
  else
    cat >&2 <<EOF
  This ceremony requires BOTH explicit confirmations:
    --confirm-gate-pin-done   (pin ceremony landed + pushed + Validate green)
    --confirm-gate-v2-fresh   (fresh GATE-V2 PASS on the POST-anchor set:
                               bash $PLAN_DIR/land-plan163-pin.sh --gate-v2)
  The ~2026-08-03 expiry of the old fail-open window does NOT satisfy
  GATE-V2 (S283). Also required before the real run: 3-vendor pack review
  APPROVE recorded under $PLAN_DIR/review/.
EOF
    die "missing confirmation flag(s)"
  fi
fi
if [ -f "$PLAN_DIR/GATE-PIN-ANCHOR" ]; then
  echo "    anchor on disk: $(grep '^ts=' "$PLAN_DIR/GATE-PIN-ANCHOR" || true)"
else
  warn "GATE-PIN-ANCHOR file missing (git-log fallback exists; --gate-v2 still works)"
fi

# =============================================================================
# PREFLIGHT
# =============================================================================
say "Preflight — main-pack (ALL checks before any GPG sign)"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
command -v python3 >/dev/null || die "python3 not found"
command -v shasum  >/dev/null || die "shasum not found"

say "Staged manifest twin (tracked, fail-closed — S274 lesson)"
[ -f "$MANIFEST_STAGED" ] || die "staged manifest missing: $MANIFEST_STAGED (pack is machine-local)"
if [ ! -f "$MANIFEST_TRACKED" ]; then
  cp "$MANIFEST_STAGED" "$MANIFEST_TRACKED"
  warn "created tracked twin $MANIFEST_TRACKED from staged — COMMIT IT before the real run:"
  warn "  git add $MANIFEST_TRACKED && git commit -m 'docs(PLAN-163): main-pack input manifest (tamper-evidence)'"
fi
cmp -s "$MANIFEST_STAGED" "$MANIFEST_TRACKED" \
  || die "tracked twin differs from staged MANIFEST.sha256 — reconcile deliberately"
if git ls-files --error-unmatch "$MANIFEST_TRACKED" >/dev/null 2>&1 \
   && git diff --quiet HEAD -- "$MANIFEST_TRACKED" 2>/dev/null; then
  echo "    twin tracked + committed"
else
  if [ "$DRY_RUN" = 1 ]; then warn "twin not tracked/committed yet — required before the real run"
  else die "manifest twin $MANIFEST_TRACKED must be git-tracked AND committed"; fi
fi

say "Staged-input integrity (shasum -a 256 -c, fail-closed)"
manifest_rows | awk -F'\t' '{print $1 "  " $2}' > "$SCRATCH/check.sha256"
N_ROWS="$(wc -l < "$SCRATCH/check.sha256" | tr -d ' ')"
[ "$N_ROWS" = "43" ] || die "main-pack manifest row count is $N_ROWS, expected 43"
( cd "$REPO" && shasum -a 256 -c "$SCRATCH/check.sha256" > "$SCRATCH/shasum.log" 2>&1 ) \
  || { tail -20 "$SCRATCH/shasum.log" >&2; die "staged bytes drifted from the pinned manifest"; }
echo "    manifest verifies ($N_ROWS pinned inputs)"

say "Sentinel Scope == manifest dest-set (NAME-BY-NAME set equality — S272)"
BODY="$SENTINEL_DIR/approved.body.md"
[ -f "$BODY" ] || die "sentinel body missing: $BODY"
grep -q '__ANCHOR_SHA__' "$BODY" || die "sentinel body lacks __ANCHOR_SHA__ placeholder"
sed -n '/^Scope:/,$p' "$BODY" | sed -n 's/^  - //p' | sort > "$SCRATCH/scope.txt"
manifest_dests > "$SCRATCH/dests.txt"
diff -u "$SCRATCH/scope.txt" "$SCRATCH/dests.txt" >&2 \
  || die "sentinel Scope != manifest dest-set (see diff above)"
echo "    scope matches ($(wc -l < "$SCRATCH/dests.txt" | tr -d ' ') files)"

say "Tree state — only plan materials / .claude/state / the W2 set may be dirty"
RE_PLANS='^\.claude/plans/'
RE_STATE='^\.claude/state/'
RE_W2='^(\.claude/scripts/(audit-telemetry\.py|budget-summary\.py|ceo-cost\.py|cost-table\.yaml|detectors/(overpowered|wasteful_thinking)\.py|detectors/tests/test_overpowered\.py|tests/test_model_fleet_presence\.py)|scripts/local/smoke-install-parity\.sh|scripts/tests/test-parity-stale-planted\.sh)$'
BAD="$(touched_files | grep -vE "${RE_PLANS}|${RE_STATE}|${RE_W2}" || true)"
if [ -n "$BAD" ]; then
  printf '%s\n' "$BAD" >&2
  die "unexpected dirty files outside plans/state/W2 allowlist"
fi
W2_DIRTY="$(touched_files | grep -E "$RE_W2" || true)"
if [ -n "$W2_DIRTY" ]; then
  echo "    W2 files pending their own commit:"
  printf '        %s\n' $W2_DIRTY
else
  echo "    W2 already committed (nothing pending)"
fi

say "Origin sync"
if git fetch origin main --quiet 2>/dev/null; then
  if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    if [ "$DRY_RUN" = 1 ]; then warn "HEAD != origin/main (sync before the real run)"
    else die "HEAD != origin/main — push/pull the ceremony materials first"; fi
  else echo "    HEAD == origin/main"; fi
else
  if [ "$DRY_RUN" = 1 ]; then warn "git fetch origin failed — origin-sync unchecked"
  else die "git fetch origin main failed"; fi
fi

say "Validate on HEAD"
if command -v gh >/dev/null; then
  _head="$(git rev-parse HEAD)"
  _v="$(gh run list --workflow validate.yml --branch main --limit 20 \
        --json headSha,status,conclusion \
        --jq "map(select(.headSha==\"$_head\")) | .[0] | \"\(.status) \(.conclusion)\"" \
        2>/dev/null || true)"
  if [ "$_v" = "completed success" ]; then echo "    Validate green on $_head"
  else
    if [ "$DRY_RUN" = 1 ]; then warn "Validate on HEAD is '${_v:-<none>}'"
    else die "Validate on HEAD is '${_v:-<no run found>}' — need completed+success"; fi
  fi
else
  if [ "$DRY_RUN" = 1 ]; then warn "gh not found — Validate-on-HEAD unchecked"
  else die "gh not found"; fi
fi

say "GPG key + BOTH signer rails"
if gpg --list-secret-keys "$KEY" >/dev/null 2>&1; then echo "    signing key present"
else
  if [ "$DRY_RUN" = 1 ]; then warn "signing key $KEY not in keyring"
  else die "signing key $KEY not in your keyring"; fi
fi
grep -q "$KEY" .claude/sentinel-signers.txt \
  || die "key $KEY absent from .claude/sentinel-signers.txt (rail 1)"
grep -q "$KEY" .claude/security/sentinel-signers-registry.yaml \
  || die "key $KEY absent from .claude/security/sentinel-signers-registry.yaml (rail 2, ADR-121)"
echo "    both signer rails carry the ceremony key"

say "ADR count pre-apply (pin+PLAN-164 landed → must be 182; pack makes it 184)"
_adr_now="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
[ "$_adr_now" = "182" ] || die "pre-apply ADR count is $_adr_now, expected 182 (are GATE-PIN + [SENT-PLAN164-RAIL] really landed? PLAN-164 adds ADR-110-AMEND-1)"

# =============================================================================
# W2 oracles (live tree) — run BEFORE committing W2, and again in overlay
# =============================================================================
say "W2 oracles on the live tree (presence fixes + planted-stale parity)"
python3 -m pytest .claude/scripts/tests/test_model_fleet_presence.py -q \
  > "$SCRATCH/w2-a.log" 2>&1 || { tail -15 "$SCRATCH/w2-a.log" >&2; die "W2 fleet-presence RED"; }
bash scripts/tests/test-parity-stale-planted.sh \
  > "$SCRATCH/w2-b.log" 2>&1 || { tail -15 "$SCRATCH/w2-b.log" >&2; die "W2 parity-stale-planted RED"; }
echo "    W2 oracles green"

if [ -n "$W2_DIRTY" ]; then
  if [ "$DRY_RUN" = 1 ]; then
    echo "    [dry-run] would commit W2 in its own 'fix(PLAN-163): W2 ...' commit"
  else
    say "Commit W2 (own commit, BEFORE the sentinel ceremony)"
    for f in $W2_MODIFIED $W2_NEW; do
      [ -e "$f" ] && git add "$f"
    done
    git -c user.signingkey="$KEY" commit -S -F - <<'MSG' || die "W2 commit failed"
fix(PLAN-163): W2 — presence-based pricing/detector fleet fixes (pre-ceremony)

Non-canonical live-tree fixes, committed OUTSIDE the sentinel scope:
_PRICING_PER_MTOK (audit-telemetry.py) += opus-4-8/fable-5 (+opus-5/
sonnet-5); detectors _LARGE_MODELS/wasteful += fable-5, opus-5;
cost-table.yaml / ceo-cost.py / budget-summary.py += the NEW ids only
(historical ids preserved — ADR-142 replay); smoke-install-parity.sh
intermediate parity assert (superseded by the ceremony's staged bytes);
oracles: test_model_fleet_presence.py (born red pre-fix) +
test-parity-stale-planted.sh (planted claude-opus-4-1 proves the red
path). CLAUDE.md untouched (cache discipline).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
    echo "    W2 committed: $(git log --oneline -1)"
  fi
fi

# =============================================================================
# Overlay — clone + W2 overlay (if uncommitted) + main-pack applied; oracles
# =============================================================================
say "Build verification overlay (clone + W2 + main-pack applied)"
OVERLAY="$SCRATCH/overlay"
git clone --local --no-hardlinks --quiet "$REPO" "$OVERLAY" || die "overlay clone failed"
# In rehearsal the W2 commit may not exist yet — overlay the live W2 bytes so
# the oracles see the same final state the real run will produce.
for f in $W2_MODIFIED $W2_NEW; do
  if [ -e "$f" ]; then mkdir -p "$OVERLAY/$(dirname "$f")"; cp "$f" "$OVERLAY/$f"; fi
done
while IFS=$'\t' read -r _sha src dst; do
  mkdir -p "$OVERLAY/$(dirname "$dst")"
  cp "$src" "$OVERLAY/$dst" || die "overlay apply failed: $src -> $dst"
done < <(manifest_rows)
echo "    overlay ready: $OVERLAY"

run_oracle() { # label logfile cmd... (cwd = overlay, CLAUDE_PROJECT_DIR pinned)
  local label="$1" log="$2"; shift 2
  if ( cd "$OVERLAY" && CLAUDE_PROJECT_DIR="$OVERLAY" "$@" ) > "$log" 2>&1; then
    echo "    ORACLE GREEN: $label"
  else
    tail -25 "$log" >&2
    die "ORACLE RED: $label (log: $log) — single-sentinel pack: fix or re-stage before any signature"
  fi
}

say "Pack oracles (in overlay) — fail-closed"
run_oracle "pack pytest — hooks/tests (14 files)" "$SCRATCH/o-p1.log" \
  python3 -m pytest \
    .claude/hooks/tests/test_adr149_validator_parity.py \
    .claude/hooks/tests/test_adr_052_role_to_model_coverage.py \
    .claude/hooks/tests/test_audit_emit_api_contract.py \
    .claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py \
    .claude/hooks/tests/test_check_directory_added.py \
    .claude/hooks/tests/test_check_notification.py \
    .claude/hooks/tests/test_check_tier_policy_misrouting_24h.py \
    .claude/hooks/tests/test_codex_egress_proof_telemetry.py \
    .claude/hooks/tests/test_git_bypass_guard.py \
    .claude/hooks/tests/test_model_routing_resolve.py \
    .claude/hooks/tests/test_model_routing_resolve_full.py \
    .claude/hooks/tests/test_session_roots_write_guard.py \
    .claude/hooks/tests/test_template_dogfood_parity.py \
    .claude/hooks/tests/test_w5_scrub_enforcement.py -q

run_oracle "pack pytest — scripts/tests + tier_policy_cli" "$SCRATCH/o-p2.log" \
  python3 -m pytest \
    .claude/scripts/tests/test_check_hook_stdout_schema.py \
    .claude/scripts/tests/test_generate_available_models.py \
    .claude/scripts/tier_policy_cli/tests/test_types.py -q

run_oracle "ADR-149 mirror regen check — dogfood settings" "$SCRATCH/o-p3.log" \
  python3 .claude/scripts/generate-available-models.py --check

run_oracle "ADR-149 mirror regen check — template settings.base.json" "$SCRATCH/o-p4.log" \
  python3 .claude/scripts/generate-available-models.py --check \
    --settings templates/settings/settings.base.json

run_oracle "availableModels mirror test (fallback equality enforced)" "$SCRATCH/o-p5.log" \
  python3 -m pytest .claude/hooks/tests/test_available_models_mirror.py -q

run_oracle "hook-stdout-schema oracle (T2, wired set DERIVED from settings.json)" "$SCRATCH/o-p6.log" \
  python3 .claude/scripts/check-hook-stdout-schema.py --repo "$OVERLAY"

run_oracle "pair-rail timeout invariant (PLAN-164 C2 — kernel==template, margin, absolutes)" "$SCRATCH/o-p7a.log" \
  python3 -m pytest .claude/hooks/tests/test_pair_rail_timeout_invariant.py -q

run_oracle "upgrade settings-migration fixtures — pass 1" "$SCRATCH/o-p7.log" \
  python3 -m pytest .claude/scripts/tests/test_upgrade_settings_migration.py -q
run_oracle "upgrade settings-migration fixtures — pass 2 (idempotency re-run)" "$SCRATCH/o-p8.log" \
  python3 -m pytest .claude/scripts/tests/test_upgrade_settings_migration.py -q

run_oracle "W2 oracles under the FINAL bytes (fleet presence + planted stale)" "$SCRATCH/o-p9.log" \
  bash -c 'python3 -m pytest .claude/scripts/tests/test_model_fleet_presence.py -q && bash scripts/tests/test-parity-stale-planted.sh'

say "Mechanical count validation in overlay (closeout deltas — CLAUDE.md NOT edited here)"
( cd "$OVERLAY" && python3 - <<'PYEOF'
import glob, json, sys
hooks_on_disk = len(glob.glob(".claude/hooks/*.py"))
adrs = len(glob.glob(".claude/adr/ADR-*.md"))
s = json.load(open(".claude/settings.json"))
regs = 0
scripts = set()
for event, arr in s.get("hooks", {}).items():
    for m in arr:
        for h in m.get("hooks", []):
            regs += 1
            for tok in h.get("command", "").split():
                if tok.endswith(".py"):
                    scripts.add(tok.split("/")[-1])
wired = len(scripts)
expect = {"hooks_on_disk": 57, "wired": 46, "registrations": 48, "adrs": 184}
got = {"hooks_on_disk": hooks_on_disk, "wired": wired,
       "registrations": regs, "adrs": adrs}
ok = True
for k in expect:
    mark = "OK " if got[k] == expect[k] else "BAD"
    if got[k] != expect[k]:
        ok = False
    print("    %s %-14s got=%-3d expected=%d" % (mark, k, got[k], expect[k]))
sys.exit(0 if ok else 1)
PYEOF
) || die "post-apply mechanical counts do not match the plan's closeout triple"

say "Claims + counts scripts in overlay (EXPECTED-DRIFT until the closeout commit)"
( cd "$OVERLAY" && python3 .claude/scripts/check-claude-md-claims.py ) \
  > "$SCRATCH/o-claims.log" 2>&1 && \
  warn "check-claude-md-claims PASSED in overlay — unexpected (counts should drift until closeout); inspect $SCRATCH/o-claims.log" || \
  echo "    check-claude-md-claims RED as EXPECTED (CLAUDE.md counts update in the closeout commit — log: $SCRATCH/o-claims.log)"
( cd "$OVERLAY" && bash .claude/scripts/local/verify-counts.sh --no-tests --quiet ) \
  > "$SCRATCH/o-counts.log" 2>&1 && \
  echo "    verify-counts green in overlay" || \
  warn "verify-counts RED in overlay (expected count drift pre-closeout — VERIFY the log shows ONLY count drift: $SCRATCH/o-counts.log)"

say "Preflight PASSED — no signature has been made yet"
if [ "$PREFLIGHT_ONLY" = 1 ]; then
  say "[preflight-only] DONE — overlay oracles green; no live-tree writes performed."
  exit 0
fi

# =============================================================================
# APPLY
# =============================================================================
APPLIED_PREEXISTING=()
APPLIED_NEW=()

apply_cp() { # src dst
  local src="$1" dst="$2"
  [ -f "$src" ] || die "staged source missing at apply time: $src"
  if [ -f "$dst" ]; then APPLIED_PREEXISTING+=("$dst"); else APPLIED_NEW+=("$dst"); fi
  mkdir -p "$(dirname "$REPO/$dst")"
  cp "$src" "$REPO/$dst"
  echo "    applied: $dst"
}

restore_dry_run() {
  if [ "${#APPLIED_PREEXISTING[@]}" -eq 0 ] && [ "${#APPLIED_NEW[@]}" -eq 0 ]; then return 0; fi
  say "[dry-run] restoring applied files (worktree AND index — S273)"
  if [ "${#APPLIED_PREEXISTING[@]}" -gt 0 ]; then
    git reset -q HEAD -- ${APPLIED_PREEXISTING[@]+"${APPLIED_PREEXISTING[@]}"} 2>/dev/null || true
    git checkout -q -- ${APPLIED_PREEXISTING[@]+"${APPLIED_PREEXISTING[@]}"}
  fi
  for f in ${APPLIED_NEW[@]+"${APPLIED_NEW[@]}"}; do
    git reset -q HEAD -- "$f" 2>/dev/null || true
    rm -f "$f"
  done
  APPLIED_PREEXISTING=(); APPLIED_NEW=()
  echo "    restored — tree and index back to pre-ceremony state"
}
if [ "$DRY_RUN" = 1 ]; then trap restore_dry_run EXIT; fi

sign_sentinel() {
  local anchor
  anchor="$(git rev-parse HEAD)"
  if [ "$DRY_RUN" = 1 ]; then
    sed -e "s/__ANCHOR_SHA__/$anchor/" -e "s/__APPROVED_AT__/$(date -u +%F)/" \
      "$BODY" > "$SCRATCH/approved.preview.md"
    echo "    [dry-run] sentinel render OK -> $SCRATCH/approved.preview.md (anchor $anchor)"
    return 0
  fi
  export GPG_TTY="${GPG_TTY:-$(tty)}"
  gpgconf --kill gpg-agent 2>/dev/null || true
  sed -e "s/__ANCHOR_SHA__/$anchor/" -e "s/__APPROVED_AT__/$(date -u +%F)/" \
    "$BODY" > "$SENTINEL_DIR/approved.md"
  rm -f "$SENTINEL_DIR/approved.md.asc"
  gpg --local-user "$KEY" --armor --detach-sign \
      --output "$SENTINEL_DIR/approved.md.asc" "$SENTINEL_DIR/approved.md" \
    || die "GPG signing failed (export GPG_TTY=\$(tty); gpgconf --kill gpg-agent; retry)"
  gpg --verify "$SENTINEL_DIR/approved.md.asc" "$SENTINEL_DIR/approved.md" >/dev/null 2>&1 \
    || die "sentinel signature does not verify"
  echo "    signed + verified: $SENTINEL_DIR/approved.md (anchor $anchor)"
}

say "Sign the main-pack sentinel (inline)"
sign_sentinel

say "Apply main-pack (KERNEL settings.json/validate.yml/audit_emit.py under declared override)"
export CEO_KERNEL_OVERRIDE="PLAN-163-T3-EVENT-ACTIONS"
export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
RESTORE_HINT="git reset --hard $START_SHA  (W2 commit survives; sentinel files are plan materials)"
while IFS=$'\t' read -r _sha src dst; do
  apply_cp "$src" "$dst"
done < <(manifest_rows)

say "Post-apply verification (live tree)"
python3 -m pytest \
  .claude/hooks/tests/test_audit_emit_api_contract.py \
  .claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py \
  .claude/hooks/tests/test_check_directory_added.py \
  .claude/hooks/tests/test_check_notification.py \
  .claude/hooks/tests/test_session_roots_write_guard.py \
  .claude/hooks/tests/test_template_dogfood_parity.py \
  .claude/hooks/tests/test_available_models_mirror.py \
  .claude/hooks/tests/test_pair_rail_timeout_invariant.py -q \
  > "$SCRATCH/post-1.log" 2>&1 || die "post-apply pytest RED ($SCRATCH/post-1.log)"
python3 .claude/scripts/generate-available-models.py --check \
  > "$SCRATCH/post-2.log" 2>&1 || die "post-apply generate --check RED ($SCRATCH/post-2.log)"
python3 .claude/scripts/check-hook-stdout-schema.py --repo "$REPO" \
  > "$SCRATCH/post-3.log" 2>&1 || die "post-apply hook-stdout-schema RED ($SCRATCH/post-3.log)"
_adr_post="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
[ "$_adr_post" = "184" ] || die "post-apply ADR count is $_adr_post, expected 184"
echo "    pytest + generate --check + stdout-schema + ADR-count(184) OK"

build_scope_re() {
  local re="" f esc
  while read -r f; do
    esc="$(printf '%s' "$f" | sed -e 's/[.[\*^$()+?{|]/\\&/g')"
    if [ -z "$re" ]; then re="$esc"; else re="$re|$esc"; fi
  done < "$SCRATCH/dests.txt"
  printf '^(%s)$' "$re"
}
RE_SCOPE="$(build_scope_re)"

if [ "$DRY_RUN" = 1 ]; then
  echo "    [dry-run] would commit the pack ceremony (43 files + plan dir)"
  restore_dry_run
  trap - EXIT
  say "[dry-run] DONE — full rehearsal green (no signature, no commit). Run without --dry-run to land."
  exit 0
fi

say "Commit (signed)"
while read -r f; do git add "$f" || die "git add failed: $f"; done < "$SCRATCH/dests.txt"
git add "$PLAN_DIR" || die "git add failed: $PLAN_DIR"
BAD="$(touched_files | grep -vE "${RE_SCOPE}|${RE_PLANS}|${RE_STATE}" || true)"
if [ -n "$BAD" ]; then printf '%s\n' "$BAD" >&2; die "touched − scope != ∅ before commit"; fi
echo "    touched ⊆ scope OK"
git -c user.signingkey="$KEY" commit -S -F - <<'MSG' || die "commit failed"
feat(PLAN-163): substrate uplift — CC 2.1.220 + Claude 5 family main pack [SENT-PLAN163-PACK]

Pre-conditions honored in order: GATE-PIN ([SENT-PLAN163-PIN]) -> GATE-V2
fresh PASS on the post-anchor set -> 3-vendor pack review APPROVE.
T1 (ADR-181 NEW + ADR-149 amend): working-set += claude-opus-5 +
claude-sonnet-5 (appended at END, order load-bearing), FALLBACK_MODEL_CHAIN
-> [claude-opus-5] (OQ1=b), VETO floor += opus-5 (Fable 5 stays ceiling);
both availableModels mirrors regenerated; independent validators
(validate-governance.sh, tier_policy_cli/_types.py) aligned + parity test.
T2: check-hook-stdout-schema.py oracle over the DERIVED wired set +
versioned 2.1.220 schema snapshot + validate.yml job (additions-only).
T3 (ADR-183 NEW): check_directory_added.py observer-writer
(.claude/state/session-roots.json, gitignored) + check_notification.py
typed no-value-echo emits + session-roots write-guard extension of
check_canonical_edit.py + audit_emit.py typed actions (KERNEL,
CEO_KERNEL_OVERRIDE=PLAN-163-T3-EVENT-ACTIONS) + SPEC audit-log v2.53;
registrations 46->48 dogfood, template stays 45 behind the T3.4 gate.
T5: settings posture OQ5(c) (defaultMode manual, strictAllowlist,
workflowSizeGuideline "medium" — evidence in ADR-181) + upgrade.sh
baseline-aware idempotent settings migration (3-state per leaf key) +
oracles; smoke-install-parity fleet assert. T6: substrate-adopt-2026-08,
CEO-MODEL-ROUTING, ACCELERATORS (fast mode = cost-latency trade-off, no
speed numbers — AGENTS.md scrub). CLAUDE.md count triple (57/46/48 +
ADRs 184) lands in the closeout commit before push (cache discipline).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
echo "    committed: $(git log --oneline -1)"

# =============================================================================
say "DONE — main-pack ceremony landed. CLOSEOUT (before push):"
cat <<'EOF'
  1. Closeout commit — count surfaces (tolerance=0 in CI):
     - CLAUDE.md triple: hooks on disk 55->57, wired 44->46,
       registrations 46->48; ADRs 182->184; skills/commands unchanged.
     - team.md :578/:589 model drift (T1.6, cache-stable file).
     - Regenerate COMMAND-SKILL-HOOK-MAP (gen---write) if hook surfaces
       feed it; sweep unwatched docs (ARCHITECTURE/GUIA-COMPLETO/FAQ/
       npm-README) for the same counts.
     - python3 .claude/scripts/check-claude-md-claims.py   (must PASS)
     - bash .claude/scripts/local/verify-counts.sh --no-tests --quiet
  2. git log --oneline -5 && git verify-commit HEAD
  3. git push origin main
  4. Watch Validate:
     gh run watch $(gh run list --workflow validate.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
  5. Plan lifecycle: PLAN-163 stays `executing` until L-proofs; then
     executing -> done with completed_at + related_commits (NEVER
     reviewed->done).

  Rollback (before push): git reset --hard <pre-ceremony sha printed above>
  Rollback (after push):  git revert <ceremony sha> (+ closeout revert);
                          the W2 commit is independent and can stay.
EOF
echo "  Pre-ceremony sha was: $START_SHA"
