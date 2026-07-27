#!/usr/bin/env bash
# =============================================================================
# land-plan161.sh — PLAN-161 consolidated maintenance sweep ceremony
# (Owner runs `!`). Modeled on land-plan160.sh.
#
# ONE sentinel, SIX per-concern segments (CF-8 drop-out protocol: a concern
# whose staged oracle is RED at ceremony time is DROPPED — touched ⊆ scope
# stays legal — and deferred; it never stalls the batch):
#
#   C1   deny-baseline Write-twin removal   (KERNEL: .claude/settings.json)
#   U    upgrade.sh dry-run + exclusions + --purge-misinstalled (+SPEC cli)
#   C2C3 council grok artifact transport + codex budget watchdog
#   C4   perf-gate probe-gated retry        (KERNEL: validate.yml) + ADR-163
#   C5   liveness typed actions 319→321     (KERNEL: audit_emit.py) + SPEC schema
#   CI   smoke-install wiring (auto-DROPPED if U dropped)
#
# Staged bytes live under .claude/plans/PLAN-161/staged/** (gitignored);
# integrity pinned by the TRACKED manifest inputs.sha256 (`shasum -c`
# fail-closed in preflight). PREFLIGHT builds ONE scratch overlay clone with
# the full pack applied and runs EVERY concern oracle there BEFORE any GPG
# signature. The W1 red-first oracles (already on main) must flip GREEN in
# the overlay.
#
# Usage:
#   bash .claude/plans/PLAN-161/land-plan161.sh --dry-run
#   bash .claude/plans/PLAN-161/land-plan161.sh
#
# --dry-run: everything except gpg + git add/commit; restores every applied
# file on ANY exit (trap). Origin-sync / Validate / gpg-key soften to WARN.
# =============================================================================
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO" || exit 1
PLAN_DIR=".claude/plans/PLAN-161"
STAGED="$PLAN_DIR/staged"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
GPG_TTY="${GPG_TTY:-$(tty || true)}"
export GPG_TTY
export CEO_OVERHEAD_ACK=1
# Owner-shell apply route (cp/git) does not trip in-session canonical hooks —
# the signed sentinel IS the authorization record (S261 precedent); the
# kernel-override exports are the ADR-031 declaration per kernel segment.

DRY_RUN=0
PREFLIGHT_ONLY=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  --preflight-only) DRY_RUN=1; PREFLIGHT_ONLY=1 ;;
  "") ;;
  *) echo "usage: $0 [--dry-run|--preflight-only]" >&2; exit 64 ;;
esac

START_SHA="$(git rev-parse HEAD)"
RESTORE_HINT="nothing was changed — safe to rerun after fixing the cause"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/land-plan161.XXXXXX")"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARN: %s\033[0m\n' "$*" >&2; }
die()  {
  printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2
  printf '\033[1;31mRESTORE: %s\033[0m\n' "$RESTORE_HINT" >&2
  exit 1
}

# ---- segment file sets (sentinel scope mirrors the union) -------------------
FILES_C1="
.claude/settings.json
.claude/hooks/check_harness_config.py
templates/settings/settings.base.json
.claude/hooks/tests/fixtures/harness-config/settings/settings_good.json
.claude/hooks/tests/fixtures/harness-config/settings/settings_inline_secret.json
.claude/hooks/tests/fixtures/harness-config/settings/settings_noop_allowlisted.json
.claude/hooks/tests/fixtures/harness-config/settings/settings_noop_unlisted.json
.claude/hooks/tests/fixtures/harness-config/settings/settings_runtime_unresolvable.json
scripts/tests/test-install-deny-baseline.sh
.claude/adr/ADR-158-harness-config-gate.md
docs/PERMISSION-MODEL-DESIGN.md
docs/deny-baseline.md
"
FILES_U="
scripts/upgrade.sh
scripts/install.sh
scripts/_framework_manifest_set.sh
.claude/adr/ADR-155-install-baseline-manifest.md
SPEC/v1/install-cli.md
"
FILES_C2C3="
.claude/workflows/council-audit.js
.claude/commands/council.md
scripts/tests/test-council-fixture.mjs
.claude/scripts/tests/test_council_verify_semantics.py
templates/grok/sandbox.toml.example
"
FILES_C4="
.github/workflows/validate.yml
.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
"
FILES_C5="
.claude/hooks/_lib/audit_emit.py
SPEC/v1/audit-log.schema.md
.claude/data/audit-registry.golden.txt
.claude/hooks/codex_review_user_code.py
.claude/hooks/check_pair_rail.py
.claude/scripts/ceo-boot.py
.claude/hooks/tests/test_audit_emit_api_contract.py
.claude/hooks/tests/test_w5_scrub_enforcement.py
.claude/hooks/tests/test_git_bypass_guard.py
.claude/hooks/tests/test_codex_egress_proof_telemetry.py
.claude/hooks/tests/test_codex_review_user_code.py
.claude/hooks/tests/test_check_pair_rail_matrix.py
.claude/scripts/tests/test_ceo_boot_liveness.py
"
FILES_CI="
.github/workflows/smoke-install.yml
"
ALL_FILES="$FILES_C1 $FILES_U $FILES_C2C3 $FILES_C4 $FILES_C5 $FILES_CI"

# touched ⊆ scope rail: exact-path alternation built from the file sets.
build_scope_re() {
  local re="" f esc
  for f in $ALL_FILES; do
    esc="$(printf '%s' "$f" | sed -e 's/[.[\*^$()+?{|]/\\&/g' -e 's|/|\\/|g')"
    esc="$(printf '%s' "$esc" | sed 's|\\/|/|g')"
    if [ -z "$re" ]; then re="$esc"; else re="$re|$esc"; fi
  done
  printf '^(%s)$' "$re"
}
RE_SCOPE="$(build_scope_re)"
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
command -v node    >/dev/null || warn "node not found — C2C3 oracle will drop that concern"

say "Tree state (must be PRISTINE — every guarded file comes from staged/)"
assert_touched "${RE_PLANS}" "pre-ceremony allowed-dirt (plan materials only)"

say "Staged inputs present"
MISSING=0
for f in $ALL_FILES; do
  if [ ! -f "$STAGED/$f" ]; then echo "    MISSING staged: $f" >&2; MISSING=1; fi
done
[ "$MISSING" -eq 0 ] || die "staged pack incomplete (pack is machine-local — run from the session checkout that built it)"

say "Staged-input manifest (shasum -c, fail-closed)"
MANIFEST="$PLAN_DIR/inputs.sha256"
[ -f "$MANIFEST" ] || die "manifest missing: $MANIFEST"
git ls-files --error-unmatch "$MANIFEST" >/dev/null 2>&1 \
  || die "manifest $MANIFEST is not tracked — commit it first (tamper-evidence)"
( cd "$REPO" && shasum -a 256 -c "$MANIFEST" >/dev/null ) \
  || die "staged-input manifest MISMATCH — staged bytes drifted from the signed manifest"
echo "    manifest verifies ($(wc -l < "$MANIFEST" | tr -d ' ') pinned inputs)"

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

say "GPG key"
if gpg --list-secret-keys "$KEY" >/dev/null 2>&1; then echo "    signing key present"
else
  if [ "$DRY_RUN" = 1 ]; then warn "signing key $KEY not in keyring"
  else die "signing key $KEY not in your keyring"; fi
fi

say "Kernel basepins (staged fixes authored against THESE canonical bytes)"
for pin in settings.json validate.yml audit_emit.py; do
  BP="$PLAN_DIR/$pin.basepin"
  [ -f "$BP" ] || die "basepin missing: $BP"
  pinned="$(grep -oE '[0-9a-f]{64}' "$BP" | head -1)"
  rel="$(sed -n '1p' "$BP" | awk '{print $2}')"
  [ -n "$pinned" ] && [ -n "$rel" ] || die "unparseable basepin: $BP"
  cur="$(shasum -a 256 "$rel" | awk '{print $1}')"
  [ "$cur" = "$pinned" ] || die "BASEPIN DRIFT: $rel canonical=$cur pinned=$pinned — rebase the staged fix"
  echo "    basepin OK ($rel)"
done

say "ADR count invariant (in-place amendments only — stays 180)"
_adr_now="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
[ "$_adr_now" = "180" ] || die "pre-apply ADR count is $_adr_now, expected 180"

# ---- overlay: ONE scratch clone with the full pack, all oracles run there ---
say "Build verification overlay (clone + staged pack applied)"
OVERLAY="$SCRATCH/overlay"
git clone --local --no-hardlinks --quiet "$REPO" "$OVERLAY" || die "overlay clone failed"
for f in $ALL_FILES; do
  mkdir -p "$OVERLAY/$(dirname "$f")"
  cp "$STAGED/$f" "$OVERLAY/$f" || die "overlay apply failed: $f"
done
echo "    overlay ready: $OVERLAY"

DROP_C1=0; DROP_U=0; DROP_C2C3=0; DROP_C4=0; DROP_C5=0; DROP_CI=0

run_oracle() { # label logfile cmd...
  local label="$1" log="$2"; shift 2
  if ( cd "$OVERLAY" && "$@" ) > "$log" 2>&1; then
    echo "    ORACLE GREEN: $label"
    return 0
  fi
  warn "ORACLE RED: $label (log: $log) — concern will be DROPPED (CF-8)"
  tail -15 "$log" >&2
  return 1
}

say "Concern oracles (STAGED mode, in overlay) — CF-8 drop-out armed"
run_oracle "C1 harness-config pytest" "$SCRATCH/o-c1a.log" \
  python3 -m pytest .claude/hooks/tests/test_check_harness_config.py -q || DROP_C1=1
if [ "$DROP_C1" -eq 0 ]; then
  run_oracle "C1 install-deny-baseline e2e" "$SCRATCH/o-c1b.log" \
    bash scripts/tests/test-install-deny-baseline.sh || DROP_C1=1
fi

run_oracle "U dry-run identity (W1 oracle flips GREEN)" "$SCRATCH/o-u1.log" \
  bash scripts/tests/test-upgrade-dryrun-identity.sh || DROP_U=1
if [ "$DROP_U" -eq 0 ]; then
  run_oracle "U exclusions+purge (W1 oracle flips GREEN)" "$SCRATCH/o-u2.log" \
    bash scripts/tests/test-upgrade-exclusions.sh || DROP_U=1
fi
if [ "$DROP_U" -eq 0 ]; then
  run_oracle "U baseline-manifest regression" "$SCRATCH/o-u3.log" \
    bash scripts/tests/test_install_baseline_manifest.sh || DROP_U=1
fi

if command -v node >/dev/null; then
  run_oracle "C2C3 node --check" "$SCRATCH/o-c2a.log" \
    node --check .claude/workflows/council-audit.js || DROP_C2C3=1
  if [ "$DROP_C2C3" -eq 0 ]; then
    ( cd "$OVERLAY" && COUNCIL_JS="$OVERLAY/.claude/workflows/council-audit.js" \
        bash scripts/tests/test-council-grok-artifact.sh ) > "$SCRATCH/o-c2b.log" 2>&1 \
      && echo "    ORACLE GREEN: C2 grok-artifact fixture" \
      || { warn "ORACLE RED: C2 grok-artifact fixture ($SCRATCH/o-c2b.log)"; tail -15 "$SCRATCH/o-c2b.log" >&2; DROP_C2C3=1; }
  fi
  if [ "$DROP_C2C3" -eq 0 ]; then
    run_oracle "C2C3 council fixture mjs" "$SCRATCH/o-c2c.log" \
      node scripts/tests/test-council-fixture.mjs || DROP_C2C3=1
  fi
  if [ "$DROP_C2C3" -eq 0 ]; then
    run_oracle "C2C3 council verify semantics" "$SCRATCH/o-c2d.log" \
      python3 -m pytest .claude/scripts/tests/test_council_verify_semantics.py -q || DROP_C2C3=1
  fi
else
  warn "node missing — DROPPING C2C3"
  DROP_C2C3=1
fi

( VALIDATE_YML="$OVERLAY/.github/workflows/validate.yml" \
    bash "$REPO/$PLAN_DIR/proof-retry-matrix.sh" ) > "$SCRATCH/o-c4.log" 2>&1 \
  && echo "    ORACLE GREEN: C4 proof-retry-matrix (staged validate.yml)" \
  || { warn "ORACLE RED: C4 proof-retry-matrix ($SCRATCH/o-c4.log)"; tail -15 "$SCRATCH/o-c4.log" >&2; DROP_C4=1; }

run_oracle "C5 registration-cascade pins" "$SCRATCH/o-c5a.log" \
  python3 -m pytest .claude/hooks/tests/test_audit_emit_api_contract.py \
    .claude/hooks/tests/test_w5_scrub_enforcement.py \
    .claude/hooks/tests/test_git_bypass_guard.py \
    .claude/hooks/tests/test_codex_egress_proof_telemetry.py -q || DROP_C5=1
if [ "$DROP_C5" -eq 0 ]; then
  run_oracle "C5 producers" "$SCRATCH/o-c5b.log" \
    python3 -m pytest .claude/hooks/tests/test_codex_review_user_code.py \
      .claude/hooks/tests/test_check_pair_rail.py \
      .claude/hooks/tests/test_check_pair_rail_matrix.py -q || DROP_C5=1
fi
if [ "$DROP_C5" -eq 0 ]; then
  run_oracle "C5 boot-liveness classifier" "$SCRATCH/o-c5c.log" \
    python3 -m pytest .claude/scripts/tests/test_ceo_boot_liveness.py -q || DROP_C5=1
fi
if [ "$DROP_C5" -eq 0 ]; then
  run_oracle "C5 dispatcher predicate unpolluted" "$SCRATCH/o-c5d.log" \
    python3 -m pytest .claude/dispatcher/tests/test_disable_predicate_eval.py -q || DROP_C5=1
fi
if [ "$DROP_C5" -eq 0 ]; then
  run_oracle "C5 audit-registry golden" "$SCRATCH/o-c5e.log" \
    python3 .claude/scripts/check-audit-registry-coverage.py --check || DROP_C5=1
fi

if [ "$DROP_U" -eq 1 ]; then
  warn "CI wiring auto-DROPPED (depends on U tests being green post-land)"
  DROP_CI=1
fi

say "Drop-out summary (CF-8)"
echo "    C1=$([ $DROP_C1 -eq 0 ] && echo APPLY || echo DROP)  U=$([ $DROP_U -eq 0 ] && echo APPLY || echo DROP)  C2C3=$([ $DROP_C2C3 -eq 0 ] && echo APPLY || echo DROP)  C4=$([ $DROP_C4 -eq 0 ] && echo APPLY || echo DROP)  C5=$([ $DROP_C5 -eq 0 ] && echo APPLY || echo DROP)  CI=$([ $DROP_CI -eq 0 ] && echo APPLY || echo DROP)"
if [ "$DROP_C1" -eq 1 ] && [ "$DROP_U" -eq 1 ] && [ "$DROP_C2C3" -eq 1 ] \
   && [ "$DROP_C4" -eq 1 ] && [ "$DROP_C5" -eq 1 ]; then
  die "every concern dropped — nothing to land"
fi

say "Preflight PASSED — no signature has been made yet"
if [ "$PREFLIGHT_ONLY" = 1 ]; then
  say "[preflight-only] DONE — overlay oracles green; no live-tree writes performed."
  exit 0
fi

# ---- helpers -----------------------------------------------------------------
APPLIED_PREEXISTING=()
APPLIED_NEW=()

apply_cp() {
  local rel="$1"
  [ -f "$STAGED/$rel" ] || die "staged source missing at apply time: $STAGED/$rel"
  if [ -f "$rel" ]; then APPLIED_PREEXISTING+=("$rel"); else APPLIED_NEW+=("$rel"); fi
  mkdir -p "$(dirname "$REPO/$rel")"
  cp "$STAGED/$rel" "$REPO/$rel"
  echo "    applied: $rel"
}

sign_sentinel() {
  local dir="$PLAN_DIR/architect/round-1" body="$PLAN_DIR/architect/round-1/approved.body.md" anchor
  [ -f "$body" ] || die "sentinel body missing: $body"
  grep -q '__ANCHOR_SHA__' "$body" || die "sentinel body lacks __ANCHOR_SHA__ placeholder"
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

commit_segment() { # label files... (message on stdin)
  local label="$1"; shift
  if [ "$DRY_RUN" = 1 ]; then
    echo "    [dry-run] would commit segment $label ($# files)"
    cat > /dev/null
    return 0
  fi
  git add "$@" "$PLAN_DIR" || die "git add failed ($label)"
  assert_touched "${RE_SCOPE}|${RE_PLANS}" "pre-commit $label"
  git -c user.signingkey="$KEY" commit -S -F - || die "commit failed ($label)"
  echo "    committed segment $label: $(git log --oneline -1)"
}

# =============================================================================
# APPLY (per-concern segments; sentinel signed once, before the first apply)
# =============================================================================
sign_sentinel

if [ "$DROP_C1" -eq 0 ]; then
  say "SEGMENT C1 — deny-baseline Write-twin removal (KERNEL settings.json)"
  export CEO_KERNEL_OVERRIDE="PLAN-161-C1-DENY-BASELINE"
  export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
  RESTORE_HINT="git reset --hard $START_SHA"
  for f in $FILES_C1; do apply_cp "$f"; done
  python3 -m pytest .claude/hooks/tests/test_check_harness_config.py -q \
    > "$SCRATCH/post-c1.log" 2>&1 || die "post-apply C1 verification RED ($SCRATCH/post-c1.log)"
  commit_segment "C1" $FILES_C1 <<'MSG'
fix(PLAN-161): C1 — remove the 3 redundant Write() deny twins [SENT-PLAN161]

CLI >=2.1.216 permission-rule semantics: Edit(path) deny covers ALL
file-editing tools; Write(path) rules are unconsulted and print 3 startup
deprecation warnings. Removed from live settings.json (KERNEL,
CEO_KERNEL_OVERRIDE=PLAN-161-C1-DENY-BASELINE), the check_harness_config
DENY_BASELINE floor (7->4), the install template, the harness-config
fixtures, and test-install-deny-baseline expectations. ADR-158 amended
in-place; PERMISSION-MODEL-DESIGN + deny-baseline docs aligned. Edit()
twins stay (they carry the protection); Owner accepted the old-CLI
residual (OQ5(a), Security VETO lift condition (ii)).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
  unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
fi

if [ "$DROP_U" -eq 0 ]; then
  say "SEGMENT U — upgrade.sh dry-run identity + exclusions + opt-in purge"
  for f in $FILES_U; do apply_cp "$f"; done
  bash scripts/tests/test-upgrade-dryrun-identity.sh > "$SCRATCH/post-u1.log" 2>&1 \
    || die "post-apply U dry-run oracle RED ($SCRATCH/post-u1.log)"
  bash scripts/tests/test-upgrade-exclusions.sh > "$SCRATCH/post-u2.log" 2>&1 \
    || die "post-apply U exclusions oracle RED ($SCRATCH/post-u2.log)"
  commit_segment "U" $FILES_U <<'MSG'
fix(PLAN-161): U1/U2/U3 — upgrade dry-run identity, exclusion predicate, opt-in purge [SENT-PLAN161]

U1: --dry-run writes NOTHING in the target (BAK_DIR mkdir guarded,
sanitized-manifest mktemp relocated outside $TARGET, agent-pin refresh +
codex/grok bundle refresh dry-run-guarded, composed EXIT trap preserves
--pin branch restoration) while provenance classification still works
(manifest-load status line + classification-aware FILE previews).
U2: _framework_path_excluded() single canonical predicate applied at the
union walk, the legacy cp -R branch, and _framework_manifest_files;
install.sh refactored onto the same predicate.
U3: --purge-misinstalled (OQ1 Owner-ratified; ADR-155 amended in-place;
SPEC/v1/install-cli.md updated under sentinel) — hash-gated nomination of
excluded trees only, lstat/no-follow, backup-first, keep+warn outside
provenance rails, preview default, second-run no-op.
Proven by the W1 red-first oracles flipping green:
test-upgrade-dryrun-identity + test-upgrade-exclusions.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
fi

if [ "$DROP_C2C3" -eq 0 ]; then
  say "SEGMENT C2C3 — council grok artifact transport + codex budget watchdog"
  for f in $FILES_C2C3; do apply_cp "$f"; done
  ( COUNCIL_JS="$REPO/.claude/workflows/council-audit.js" \
      bash scripts/tests/test-council-grok-artifact.sh ) > "$SCRATCH/post-c2.log" 2>&1 \
    || die "post-apply C2 fixture RED ($SCRATCH/post-c2.log)"
  commit_segment "C2C3" $FILES_C2C3 <<'MSG'
fix(PLAN-161): C2/C3 — grok-lane artifact transport + mechanical codex budget [SENT-PLAN161]

C2 (CF-3): grok 0.2.93 -p cannot read stdin — the grok lane now composes
redactor stdout -> 0600 artifact in a fresh 0700 mkdtemp dir ->
rename-into-place (&&-chained, fail-closed: artifact exists ONLY if the
redactor exited 0) -> fixed pointer argv (no brief bytes in argv; $(cat)
forbidden); artifact sha256 attested in the lane schema. ONE redactor
chokepoint unchanged (ADR-114 untouched — redaction-before-egress is the
mandate, the pipe shape was workflow prose). council.md false
scope-default claim fixed; sandbox.toml.example transport updated.
C3: codex lane budget is now MECHANICAL — scope-aware wall-clock bound
(resolved file count, hard cap) via portable watchdog (timeout ->
gtimeout -> stdlib python3 process-group watchdog; missing python3 ->
lane unavailable, fail-loud). One-pipe tests rewritten to vendor-specific
invariants; test-council-grok-artifact green against canonical.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
fi

if [ "$DROP_C4" -eq 0 ]; then
  say "SEGMENT C4 — perf-gate probe-gated retry (KERNEL validate.yml)"
  export CEO_KERNEL_OVERRIDE="PLAN-161-C4-PERF-GATE"
  export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
  for f in $FILES_C4; do apply_cp "$f"; done
  ( VALIDATE_YML="$REPO/.github/workflows/validate.yml" \
      bash "$REPO/$PLAN_DIR/proof-retry-matrix.sh" ) > "$SCRATCH/post-c4.log" 2>&1 \
    || die "post-apply C4 proof matrix RED ($SCRATCH/post-c4.log)"
  commit_segment "C4" $FILES_C4 <<'MSG'
fix(PLAN-161): C4 — perf-gate backoff + probe-gated 3rd attempt [SENT-PLAN161]

ADR-163 amended in-place (CEO_KERNEL_OVERRIDE=PLAN-161-C4-PERF-GATE for
validate.yml): 2 unconditional attempts (420s caps) + 60s inter-attempt
backoff + AT MOST one 3rd attempt gated on a contention pre-probe
(profile --floor, 30s cap, p50<=200ms parsed from JSON; nonzero probe
exit overrides JSON; malformed/timeout -> contended fail-safe);
still-contended -> distinct infrastructure fail-fast, never a regression
verdict. Worst-case inequality pinned: 3x420+2x60+30+30+~180 ~= 27min ->
timeout-minutes 28. Historical FAILED-on-BOTH marker preserved
(wave2-proof back-compat); proof = PLAN-161/proof-retry-matrix.sh (9/9).
CI wiring: smoke-install runs the two new upgrade oracles (timeout 5->8).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
  unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
fi

if [ "$DROP_C5" -eq 0 ]; then
  say "SEGMENT C5 — pair-rail liveness typed actions (KERNEL audit_emit.py)"
  export CEO_KERNEL_OVERRIDE="PLAN-161-C5-LIVENESS-ACTIONS"
  export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
  for f in $FILES_C5; do apply_cp "$f"; done
  python3 -m pytest .claude/hooks/tests/test_audit_emit_api_contract.py \
    .claude/hooks/tests/test_codex_review_user_code.py \
    .claude/scripts/tests/test_ceo_boot_liveness.py -q \
    > "$SCRATCH/post-c5.log" 2>&1 || die "post-apply C5 verification RED ($SCRATCH/post-c5.log)"
  python3 .claude/scripts/check-audit-registry-coverage.py --check \
    > "$SCRATCH/post-c5b.log" 2>&1 || die "post-apply C5 golden RED ($SCRATCH/post-c5b.log)"
  commit_segment "C5" $FILES_C5 <<'MSG'
fix(PLAN-161): C5 — pair-rail liveness telemetry (2 typed actions, 319->321) [SENT-PLAN161]

The failopen_rail_liveness_7d yellow was a SIGNAL gap, not a rail gap.
audit_emit.py (KERNEL, CEO_KERNEL_OVERRIDE=PLAN-161-C5-LIVENESS-ACTIONS):
codex_review_verdict (closed outcome enum clean/findings/
skipped_failopen/detected_only + diff_sha256, deny-by-default scrub) +
pair_rail_review_expected (session-correlated activity denominator).
Producer codex_review_user_code.py: strict bounded verdict parser
(malformed -> skipped_failopen, never healthy), per-outcome typed emits,
(diff,outcome) telemetry dedupe, session id threaded. check_pair_rail.py
emits review-expected at review entry + threads session id into
pair_rail_case. ceo-boot classifier: stop_review sub-rail (detected_only
neutral) + pair_rail row activity-conditioned with per-session
correlation. SPEC audit-log.schema v2.52 (via sentinel), golden
regenerated, all four 319-count pins -> 321, SHA pin rebased.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
  unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
fi

if [ "$DROP_CI" -eq 0 ]; then
  say "SEGMENT CI — smoke-install wiring"
  for f in $FILES_CI; do apply_cp "$f"; done
  commit_segment "CI" $FILES_CI <<'MSG'
ci(PLAN-161): wire the W1 upgrade oracles into smoke-install [SENT-PLAN161]

test-upgrade-dryrun-identity + test-upgrade-exclusions added to both
path filters and the run steps; job timeout 5 -> 8 minutes.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
fi

# ---- post-apply global verification -----------------------------------------
say "Global post-apply verification"
python3 .claude/scripts/check-claude-md-claims.py \
  > "$SCRATCH/post-claims.log" 2>&1 || die "check-claude-md-claims RED ($SCRATCH/post-claims.log)"
bash .claude/scripts/local/verify-counts.sh --no-tests --quiet \
  || die "verify-counts RED post-apply"
_adr_post="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
[ "$_adr_post" = "180" ] || die "post-apply ADR count is $_adr_post, expected 180 (in-place only)"
echo "    claims + counts + ADR-count(180) OK"

if [ "$DRY_RUN" = 1 ]; then
  restore_dry_run
  say "[dry-run] DONE — full rehearsal green (no signature, no commit). Run without --dry-run to land."
  exit 0
fi

# =============================================================================
say "DONE — ceremony commits landed. Review, then push:"
echo "    git log --oneline -7 && git verify-commit HEAD"
echo "    git push origin main"
echo ""
echo "  Watch Validate:"
echo "    gh run watch \$(gh run list --workflow validate.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')"
echo ""
echo "  Then (PLAN-161 L-waves, see HANDOFF-S279-PLAN161.md):"
echo "    L1 lint proof: fresh claude session -> zero Permission-deny-rule warnings"
echo "    L3 council 3-lane [egress auth]: /council scope=check_canonical_edit.py"
echo "    L4 liveness: CEO_CODEX_USER_REVIEW_AUTO=1 risky-diff review -> /ceo-boot green"
echo ""
echo "  Rollback (before push): git reset --hard $START_SHA"
echo "  Rollback (after push):  git revert <segment-shas>"
