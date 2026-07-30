#!/usr/bin/env bash
# =============================================================================
# land-plan164-rail.sh — PLAN-164 GATE-RAIL: pair-rail timeout uplift ceremony
# (Owner runs `!`). Modeled on land-plan163-pin.sh; the SINGLE declared
# PLAN-164 ceremony (order: this ceremony -> immediate closeout -> W3 fresh
# proof in a NEW session -> PLAN-163 pack ceremony unblocked).
#
# Scope: .claude/plans/PLAN-164/staged/rail-pack/ ONLY (ratified OQ1-OQ4:
# internal default 30 -> 120 s in check_pair_rail.py; harness registration
# 60 -> 150 s in kernel settings.json + template parity + statusMessage;
# cross-layer invariant test; doctor.sh margin warn — the adopter
# upgrade.sh migration MOVED to the PLAN-163 main-pack after the
# cross-pack clobber finding, it does NOT land here; ADR-110-AMEND-1 as a
# SEPARATE FILE per house convention (17 precedents) — ADR COUNT 181->182,
# so this pack also stages land-plan163-pack.sh with its fail-closed
# count gates bumped 181/183 -> 182/184). Integrity is pinned by the TRACKED
# manifest twin `.claude/plans/PLAN-164/inputs-rail.sha256` (byte-copy of
# the staged MANIFEST.sha256; `shasum -a 256 -c` fail-closed — staged/ is
# gitignored, so the twin is the tamper-evidence rail, S274 lesson).
#
# PREFLIGHT (no signature, no live-tree write):
#   - manifest twin tracked + identical to staged + shasum -c fail-closed
#   - sentinel Scope == manifest dest-set (NAME-BY-NAME set equality, S272)
#   - core rail surfaces asserted present in the dest-set
#   - overlay clone (git clone --local) + rail-pack applied THERE
#   - pytest -k pair_rail + test_pair_rail_timeout_invariant.py in overlay
#   - VALUE-GATE on the staged bytes (C4/S284 lesson — verify behavior,
#     never a report): internal literal 120, registration 150 kernel ==
#     template, margin >= 30, statusMessage present, stale 30/60 gone
#   NO codex-attestation gates: this ceremony does NOT touch the ADR-182
#   codex pin (no --verify-codex-pin, no pair-rail-gate phase 6).
#
# APPLY (real run only): sentinel signed INLINE (anchor = HEAD, GPG detach
# + verify against BOTH signer rails), cp per manifest under
# CEO_KERNEL_OVERRIDE=PLAN-164-RAIL-TIMEOUT, post-apply oracles, ONE signed
# commit `[SENT-PLAN164-RAIL]`, then the RE-ANCHOR (OQ3 pin mechanics): the
# GATE-PIN-ANCHOR is rewritten with the NEW commit's sha+ts and committed
# in the IMMEDIATE closeout (a commit cannot contain its own sha).
#
# There is NO --gate-v2 mode in this script ON PURPOSE: the GATE-V2 verdict
# remains `bash .claude/plans/PLAN-163/land-plan163-pin.sh --gate-v2`
# (this ceremony re-anchors it; it does not replace it).
#
# Usage:
#   bash .claude/plans/PLAN-164/land-plan164-rail.sh --preflight-only
#   bash .claude/plans/PLAN-164/land-plan164-rail.sh --dry-run
#   bash .claude/plans/PLAN-164/land-plan164-rail.sh
#
# --dry-run: everything except gpg + git add/commit; restores tree AND
# index on ANY exit (trap, S273 lesson). Origin/Validate/gpg soften to WARN.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO" || exit 1
[ -f "CLAUDE.md" ] && [ -d ".claude" ] || { echo "FATAL: repo root not resolved ($REPO)" >&2; exit 1; }
PLAN_DIR=".claude/plans/PLAN-164"
PLAN163_DIR=".claude/plans/PLAN-163"
STAGED="$PLAN_DIR/staged/rail-pack"
MANIFEST_STAGED="$STAGED/MANIFEST.sha256"
MANIFEST_TRACKED="$PLAN_DIR/inputs-rail.sha256"
SENTINEL_DIR="$PLAN_DIR/architect/round-1"
ANCHOR_FILE="$PLAN163_DIR/GATE-PIN-ANCHOR"
PIN_SCRIPT="$PLAN163_DIR/land-plan163-pin.sh"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
INTERNAL_S=120     # OQ1 (ratified) — hook internal default
REGISTRATION_S=150 # OQ2 (ratified) — harness registration timeout
MARGIN_S=30        # invariant: REGISTRATION >= INTERNAL + MARGIN
GPG_TTY="${GPG_TTY:-$(tty || true)}"
export GPG_TTY
export CEO_OVERHEAD_ACK=1
# Owner-shell apply route (cp/git) does not trip in-session canonical hooks —
# the signed sentinel IS the authorization record (S261 precedent); the
# kernel-override export below is the ADR-031 declaration for settings.json.

usage() {
  cat <<'EOF'
usage: land-plan164-rail.sh [--dry-run|--preflight-only|--help]

  --preflight-only      all oracles in an overlay clone; no live-tree writes
  --dry-run             full rehearsal (apply + restore); no gpg, no commit
  --rerun-after-revert  real run ALLOWED even though a prior (reverted)
                        ceremony commit exists — deliberate recovery path;
                        requires the revert commit to be in history
  (no flag)             the real Owner-run ceremony (GPG + signed commit)

NOTE: there is NO --gate-v2 here. The GATE-V2 verdict remains
  bash .claude/plans/PLAN-163/land-plan163-pin.sh --gate-v2
run AFTER this ceremony (re-anchored) + a fresh probe in a NEW session (W3).
EOF
}

DRY_RUN=0
PREFLIGHT_ONLY=0
RERUN_AFTER_REVERT=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  --preflight-only) DRY_RUN=1; PREFLIGHT_ONLY=1 ;;
  --rerun-after-revert) RERUN_AFTER_REVERT=1 ;;
  -h|--help) usage; exit 0 ;;
  "") ;;
  *) usage >&2; exit 64 ;;
esac

START_SHA="$(git rev-parse HEAD)"
RESTORE_HINT="nothing was changed — safe to rerun after fixing the cause"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/land-plan164-rail.XXXXXX")"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARN: %s\033[0m\n' "$*" >&2; }
die()  {
  printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2
  printf '\033[1;31mRESTORE: %s\033[0m\n' "$RESTORE_HINT" >&2
  exit 1
}

# ---- manifest parsing (format: "sha256  staged-path  ->  dest-path") --------
manifest_rows()  { awk '/^[0-9a-f]{64}/ {print $1 "\t" $2 "\t" $4}' "$MANIFEST_TRACKED"; }
manifest_dests() { manifest_rows | cut -f3 | sort; }

# ---- value-gate (C4/S284: verify the BYTES, never a report) -----------------
assert_rail_values() { # root label
  local root="$1" label="$2"
  RAIL_ROOT="$root" RAIL_INTERNAL="$INTERNAL_S" RAIL_REG="$REGISTRATION_S" \
  RAIL_MARGIN="$MARGIN_S" python3 - <<'PYEOF' || die "value-gate FAILED ($label) — bytes do not carry the ratified 120/150/statusMessage literals"
from __future__ import annotations
import json
import os
import sys

root = os.environ["RAIL_ROOT"]
internal = int(os.environ["RAIL_INTERNAL"])
registration = int(os.environ["RAIL_REG"])
margin = int(os.environ["RAIL_MARGIN"])
problems = []


def rail_entry(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)  # doubles as the json.load sanity oracle
    for entry in (data.get("hooks") or {}).get("PreToolUse", []):
        if "check_pair_rail.py" in json.dumps(entry):
            return entry
    raise SystemExit("no PreToolUse check_pair_rail.py registration in %s" % path)


timeouts = {}
for rel in (".claude/settings.json", "templates/settings/settings.base.json"):
    path = os.path.join(root, rel)
    entry = rail_entry(path)
    blob = json.dumps(entry)
    hook0 = (entry.get("hooks") or [{}])[0]
    timeouts[rel] = hook0.get("timeout")
    if hook0.get("timeout") != registration:
        problems.append("%s: registration timeout=%r, expected %d"
                        % (rel, hook0.get("timeout"), registration))
    if "statusMessage" not in blob:
        problems.append("%s: statusMessage missing from the pair-rail entry" % rel)
    if "default 30s" in blob:
        problems.append("%s: stale '(default 30s)' _comment survives" % rel)

if len(set(timeouts.values())) != 1:
    problems.append("kernel/template registration timeouts differ: %r" % timeouts)

with open(os.path.join(root, ".claude/hooks/check_pair_rail.py"),
          "r", encoding="utf-8") as fh:
    src = fh.read()
if '"CEO_PAIR_RAIL_TIMEOUT_S", "%d"' % internal not in src:
    problems.append('check_pair_rail.py: env default literal "%d" not found' % internal)
if "timeout_s = %d.0" % internal not in src:
    problems.append("check_pair_rail.py: fallback %d.0 not found" % internal)
for stale in ('"CEO_PAIR_RAIL_TIMEOUT_S", "30"', "timeout_s = 30.0"):
    if stale in src:
        problems.append("check_pair_rail.py: stale literal %r survives" % stale)
if registration < internal + margin:
    problems.append("margin invariant broken: %d < %d + %d"
                    % (registration, internal, margin))

if problems:
    for p in problems:
        print("    VALUE-GATE MISS: " + p, file=sys.stderr)
    sys.exit(1)
print("    value-gate: internal=%d registration=%d (kernel==template) "
      "margin=%d statusMessage OK" % (internal, registration,
                                      registration - internal))
PYEOF
}

# =============================================================================
# PREFLIGHT (ALL checks run BEFORE any GPG sign)
# =============================================================================
say "Preflight — GATE-RAIL (no signature until every oracle is green)"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
command -v python3 >/dev/null || die "python3 not found"
command -v shasum  >/dev/null || die "shasum not found"

say "Already-landed guard (re-run would launder the re-anchor)"
# Ceremony commit = subject ENDS with the tag (same suffix rule as
# resolve_anchor). A revert of it (git revert keeps the tag mid-subject
# under the Revert prefix, so the reverted state is detectable).
_prior=""
while IFS=$'\t' read -r _h _subj; do
  case "$_subj" in *"[SENT-PLAN164-RAIL]") _prior="$_h"; break ;; esac
done < <(git log --format='%H%x09%s' --grep='\[SENT-PLAN164-RAIL\]' || true)
if [ -n "$_prior" ]; then
  _revert="$(git log --format='%H' --grep='This reverts commit '"$_prior" -n 1 || true)"
  if [ -n "$_revert" ] && [ "$RERUN_AFTER_REVERT" = 1 ]; then
    warn "prior ceremony $_prior was REVERTED by $_revert — --rerun-after-revert accepted; the new ceremony commit becomes the newest anchor"
  elif [ -n "$_revert" ]; then
    if [ "$DRY_RUN" = 1 ]; then
      warn "prior ceremony $_prior reverted by $_revert — the real re-run needs the explicit --rerun-after-revert flag"
    else
      die "prior ceremony $_prior was reverted ($_revert) — re-run REQUIRES the explicit --rerun-after-revert flag (deliberate recovery, codex r2 HIGH-1)"
    fi
  else
    if [ "$DRY_RUN" = 1 ]; then
      warn "[SENT-PLAN164-RAIL] already landed at $_prior — rehearsal only, the real run will refuse"
    else
      die "ceremony already landed at $_prior (not reverted) — re-running would move the GATE-V2 anchor and launder post-anchor fail-opens; use PLAN-163 --gate-v2 for the verdict"
    fi
  fi
else
  echo "    no prior [SENT-PLAN164-RAIL] ceremony commit"
fi

say "Tree state (rail scope must come ONLY from staged/; known W2 dirt tolerated)"
# The PLAN-163 pack ceremony commits the W2 live-tree fixes LATER; at
# rail-ceremony time they are allowed dirt — but they must stay disjoint
# from the rail scope, which the touched-scope assert enforces by exact path.
RE_PLANS='^\.claude/plans/'
RE_STATE='^\.claude/state/'
RE_W2='^(\.claude/scripts/(audit-telemetry\.py|budget-summary\.py|ceo-cost\.py|cost-table\.yaml|detectors/(overpowered|wasteful_thinking)\.py|detectors/tests/test_overpowered\.py|tests/test_model_fleet_presence\.py)|scripts/local/smoke-install-parity\.sh|scripts/tests/test-parity-stale-planted\.sh)$'
touched_files() { git status --porcelain=v1 | sed -E 's/^.{3}//; s/^.* -> //'; }
BAD="$(touched_files | grep -vE "${RE_PLANS}|${RE_STATE}|${RE_W2}" || true)"
if [ -n "$BAD" ]; then
  printf '%s\n' "$BAD" >&2
  die "unexpected dirty files outside plans/state/W2 allowlist — resolve before the ceremony"
fi
echo "    tree OK (only plan materials / .claude/state / known PLAN-163 W2 dirt)"

say "Staged manifest twin (tracked, fail-closed — S274 lesson)"
[ -f "$MANIFEST_STAGED" ] || die "staged manifest missing: $MANIFEST_STAGED (pack is machine-local)"
if [ ! -f "$MANIFEST_TRACKED" ]; then
  cp "$MANIFEST_STAGED" "$MANIFEST_TRACKED"
  warn "created tracked twin $MANIFEST_TRACKED from staged — COMMIT IT before the real run:"
  warn "  git add $MANIFEST_TRACKED && git commit -m 'docs(PLAN-164): rail-pack input manifest (tamper-evidence)'"
fi
cmp -s "$MANIFEST_STAGED" "$MANIFEST_TRACKED" \
  || die "tracked twin differs from staged MANIFEST.sha256 — reconcile deliberately (the TWIN is authoritative once committed)"
if git ls-files --error-unmatch "$MANIFEST_TRACKED" >/dev/null 2>&1 \
   && git diff --quiet HEAD -- "$MANIFEST_TRACKED" 2>/dev/null; then
  echo "    twin tracked + committed"
else
  if [ "$DRY_RUN" = 1 ]; then warn "twin not tracked/committed yet — required before the real run"
  else die "manifest twin $MANIFEST_TRACKED must be git-tracked AND committed (tamper-evidence)"; fi
fi

say "Staged-input integrity (shasum -a 256 -c, fail-closed)"
manifest_rows | awk -F'\t' '{print $1 "  " $2}' > "$SCRATCH/check.sha256"
N_ROWS="$(wc -l < "$SCRATCH/check.sha256" | tr -d ' ')"
[ "$N_ROWS" -ge 1 ] 2>/dev/null || die "rail manifest has no parseable rows ($MANIFEST_TRACKED)"
( cd "$REPO" && shasum -a 256 -c "$SCRATCH/check.sha256" > "$SCRATCH/shasum.log" 2>&1 ) \
  || { tail -20 "$SCRATCH/shasum.log" >&2; die "staged bytes drifted from the pinned manifest"; }
echo "    manifest verifies ($N_ROWS pinned inputs)"

say "Sentinel Scope == manifest dest-set (NAME-BY-NAME set equality — S272)"
BODY="$SENTINEL_DIR/approved.body.md"
[ -f "$BODY" ] || die "sentinel body missing: $BODY"
grep -q '__ANCHOR_SHA__' "$BODY" || die "sentinel body lacks __ANCHOR_SHA__ placeholder"
grep -q '__APPROVED_AT__' "$BODY" || die "sentinel body lacks __APPROVED_AT__ placeholder"
sed -n '/^Scope:/,$p' "$BODY" | sed -n 's/^  - //p' | sort > "$SCRATCH/scope.txt"
manifest_dests > "$SCRATCH/dests.txt"
diff -u "$SCRATCH/scope.txt" "$SCRATCH/dests.txt" >&2 \
  || die "sentinel Scope != manifest dest-set (see diff above) — reconcile the body vs staged pack DELIBERATELY"
echo "    scope matches ($(wc -l < "$SCRATCH/dests.txt" | tr -d ' ') files)"

say "Dest paths clean pre-ceremony (codex r1 MED-5 — apply/restore must never clobber uncommitted work)"
_dirty_dests="$(git status --porcelain=v1 -- $(cat "$SCRATCH/dests.txt") 2>/dev/null | sed -E 's/^.{3}//')"
if [ -n "$_dirty_dests" ]; then
  printf '%s\n' "$_dirty_dests" >&2
  die "dest path(s) above have uncommitted worktree/index state — commit or stash them BEFORE the ceremony (apply would overwrite; dry-run restore would destroy them)"
fi
echo "    all $(wc -l < "$SCRATCH/dests.txt" | tr -d ' ') dest paths clean"

say "Core rail surfaces present in the dest-set (ratified W1 shape)"
for _core in \
  ".claude/hooks/check_pair_rail.py" \
  ".claude/settings.json" \
  "templates/settings/settings.base.json" \
  ".claude/hooks/tests/test_pair_rail_timeout_invariant.py"; do
  grep -qxF "$_core" "$SCRATCH/dests.txt" \
    || die "core surface missing from the rail-pack dest-set: $_core"
done
echo "    hook + kernel + template + invariant test all in scope"

say "Origin sync"
if git fetch origin main --quiet 2>/dev/null; then
  if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    if [ "$DRY_RUN" = 1 ]; then warn "HEAD != origin/main (sync before the real run)"
    else die "HEAD != origin/main — push/pull first"; fi
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

say "GPG key + BOTH signer rails (sentinel-signers.txt + ADR-121 registry)"
if gpg --list-secret-keys "$KEY" >/dev/null 2>&1; then echo "    signing key present"
else
  if [ "$DRY_RUN" = 1 ]; then warn "signing key $KEY not in keyring"
  else die "signing key $KEY not in your keyring (export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"; fi
fi
grep -q "$KEY" .claude/sentinel-signers.txt \
  || die "key $KEY absent from .claude/sentinel-signers.txt (rail 1)"
grep -q "$KEY" .claude/security/sentinel-signers-registry.yaml \
  || die "key $KEY absent from .claude/security/sentinel-signers-registry.yaml (rail 2, ADR-121)"
echo "    both signer rails carry the ceremony key"

# ---- overlay: scratch clone with the rail-pack applied; oracles run there ---
say "Build verification overlay (clone + rail-pack applied)"
OVERLAY="$SCRATCH/overlay"
git clone --local --no-hardlinks --quiet "$REPO" "$OVERLAY" || die "overlay clone failed"
while IFS=$'\t' read -r _sha src dst; do
  mkdir -p "$OVERLAY/$(dirname "$dst")"
  cp "$src" "$OVERLAY/$dst" || die "overlay apply failed: $src -> $dst"
done < <(manifest_rows)
echo "    overlay ready: $OVERLAY"

say "Value-gate on the staged bytes (in overlay — ratified literals, C4/S284)"
assert_rail_values "$OVERLAY" "overlay/staged"

run_oracle() { # label logfile cmd... (cwd = overlay, CLAUDE_PROJECT_DIR pinned)
  local label="$1" log="$2"; shift 2
  if ( cd "$OVERLAY" && CLAUDE_PROJECT_DIR="$OVERLAY" "$@" ) > "$log" 2>&1; then
    echo "    ORACLE GREEN: $label"
  else
    tail -20 "$log" >&2
    die "ORACLE RED: $label (log: $log) — a liveness fix with red oracles does not land; fix or defer the whole pack"
  fi
}

say "Rail oracles (in overlay) — fail-closed"
run_oracle "pytest -k pair_rail (hook suite incl. timeout sweep + invariant module)" \
  "$SCRATCH/o-rail1.log" \
  python3 -m pytest .claude/hooks/tests/ -k "pair_rail" -q
run_oracle "test_pair_rail_timeout_invariant.py (C2 cross-layer invariant, explicit)" \
  "$SCRATCH/o-rail2.log" \
  python3 -m pytest .claude/hooks/tests/test_pair_rail_timeout_invariant.py -q

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
  # GPG preamble — sign INLINE, never require a pre-existing .asc (S273/S274)
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

say "Sign the GATE-RAIL sentinel (inline; anchor = pre-ceremony HEAD)"
sign_sentinel

say "Apply rail-pack to the live tree (kernel: settings.json under declared override)"
export CEO_KERNEL_OVERRIDE="PLAN-164-RAIL-TIMEOUT"
export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
RESTORE_HINT="git reset --hard $START_SHA  (sentinel .md/.asc under $SENTINEL_DIR are plan materials)"
while IFS=$'\t' read -r _sha src dst; do
  apply_cp "$src" "$dst"
done < <(manifest_rows)

say "Post-apply verification (live tree — verify behavior, not intention)"
python3 -m pytest .claude/hooks/tests/ -k "pair_rail" -q \
  > "$SCRATCH/post-rail1.log" 2>&1 || die "post-apply pytest -k pair_rail RED ($SCRATCH/post-rail1.log)"
python3 -m pytest .claude/hooks/tests/test_pair_rail_timeout_invariant.py -q \
  > "$SCRATCH/post-rail2.log" 2>&1 || die "post-apply invariant test RED ($SCRATCH/post-rail2.log)"
assert_rail_values "$REPO" "live/applied"
echo "    pytest -k pair_rail + invariant test + settings value-gate OK"

# touched ⊆ scope rail
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
  echo "    [dry-run] would commit the rail ceremony ($N_ROWS files + plan materials)"
  restore_dry_run
  trap - EXIT
  say "[dry-run] DONE — full rehearsal green (no signature, no commit). Run without --dry-run to land."
  exit 0
fi

say "Commit (signed)"
while read -r f; do git add "$f" || die "git add failed: $f"; done < "$SCRATCH/dests.txt"
git add "$PLAN_DIR" || die "git add failed: $PLAN_DIR"
# The PLAN-163 scripts (anchor validator + retirement guard + count gates)
# are NOT in this commit: they landed PRE-ceremony in their own commit so
# they survive a ceremony rollback (codex r4 HIGH) — nothing to add here.
git add ".claude/plans/PLAN-164-pair-rail-timeout-uplift.md" 2>/dev/null || true
BAD="$(touched_files | grep -vE "${RE_SCOPE}|${RE_PLANS}|${RE_STATE}|${RE_W2}" || true)"
if [ -n "$BAD" ]; then printf '%s\n' "$BAD" >&2; die "touched − scope != ∅ before commit"; fi
echo "    touched ⊆ scope OK"
# codex r1 MED-4: `git commit` commits the WHOLE index — assert the CACHED
# set is exactly what this ceremony added (dests + PLAN-164 materials).
# A W2/state file someone pre-staged would otherwise ride into the signed
# commit despite the sentinel declaring only the 8 scope paths.
RE_MATERIALS='^\.claude/plans/PLAN-164/|^\.claude/plans/PLAN-164-pair-rail-timeout-uplift\.md$'
BAD_IDX="$(git diff --cached --name-only | grep -vE "${RE_SCOPE}|${RE_MATERIALS}" || true)"
if [ -n "$BAD_IDX" ]; then
  printf '%s\n' "$BAD_IDX" >&2
  die "index carries path(s) outside scope+materials (above) — git restore --staged them and re-run"
fi
echo "    index ⊆ scope+materials OK"
git -c user.signingkey="$KEY" commit -S -F - <<'MSG' || die "commit failed"
fix(PLAN-164): pair-rail timeout uplift 120/150 + anchor validation + doctor warn (ADR-110-AMEND-1) [SENT-PLAN164-RAIL]

The default CEO_PAIR_RAIL_TIMEOUT_S=30 is structurally below the real
latency of a codex verdict (measured N=9: p95 ~75s incl. 75.1s under
load; 12 of 12 pair_rail_case in the log's entire history are F/TIMEOUT
— the rail never completed a live review; PLAN-163 GATE-V2 FAIL
diagnosis 2026-07-29). This ceremony lands the ratified OQ1-OQ4 fix:
check_pair_rail.py internal default 30 -> 120s (env get + fallback +
clamp-reset + docstring; >600 clamp kept); kernel settings.json
registration 60 -> 150s with template settings.base.json in parity,
statusMessage added and stale "(default 30s)" comments updated (margin
invariant 150 >= 120 + 30 restored); cross-layer invariant test
(test_pair_rail_timeout_invariant.py) makes any unilateral flip RED;
doctor.sh warns on registration < internal+30. The adopter upgrade.sh
value migration (60 -> 150 IFF currently 60) rides the PLAN-163
main-pack instead — upgrade.sh lives there with its settings-migration
machinery and test_upgrade_settings_migration.py; carrying a live-based
copy here would cross-clobber (S284 class). Record is AMEND-1 of
ADR-110 as a separate file per house convention (not a new numbered
ADR), which moves the ADR file count 181 -> 182 — therefore this pack
also stages land-plan163-pack.sh with its fail-closed ADR-count gates
bumped 181/183 -> 182/184 (the frozen main-pack bytes stay untouched);
the amend names the env-knob sub-floor residual, the >=10-healthy p95
recalibration trigger, and the rejected alternatives. The PLAN-163
gate tooling (land-plan163-pin.sh: resolve_anchor fail-closed pointer
validation with the suffix-newest + revert-aware rule; pin-pack
retirement guard; land-plan163-pack.sh: ADR-count gates 182/184) landed
in its own PRE-ceremony commit so the validator survives a rollback of
THIS commit (codex r4 HIGH).
Kernel surface .claude/settings.json under
CEO_KERNEL_OVERRIDE=PLAN-164-RAIL-TIMEOUT; sentinel
PLAN-164/architect/round-1 (GPG, anchor = pre-ceremony HEAD). This
commit is the NEW GATE-V2 anchor (OQ3 pin mechanics): GATE-PIN-ANCHOR
is rewritten post-commit with this sha+ts and committed in the
immediate closeout; the re-anchored PASS proves liveness under the
ADR-182 pin + the new timeout (strictly stronger; the pin is untouched).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
CEREMONY_SHA="$(git rev-parse HEAD)"
CEREMONY_TS="$(git log -1 --format='%cI' "$CEREMONY_SHA")"
echo "    committed: $(git log --oneline -1)"

say "RE-ANCHOR (OQ3 pin mechanics — a commit cannot contain its own sha)"
{
  echo "# PLAN-163 GATE-PIN anchor — RE-ANCHORED by PLAN-164 [SENT-PLAN164-RAIL]"
  echo "# GATE-V2 counts ONLY events after ts= (resolve_anchor re-derives ts from sha, C1)"
  echo "sha=$CEREMONY_SHA"
  echo "ts=$CEREMONY_TS"
} > "$ANCHOR_FILE"
echo "    $ANCHOR_FILE rewritten (sha=$CEREMONY_SHA)"

say "IMMEDIATE closeout (ALL via bash — read the box below FIRST)"
cat <<EOF

  ==========================================================================
  ATTENTION — ASYMMETRY WINDOW (consensus kept-2 / OQ3):
  THE NEW INTERNAL BUDGET (120 S) IS PER-INVOCATION AND HOLDS NOW; THE
  150 S REGISTRATION ONLY HOLDS AFTER A HARNESS RESTART. IN THIS SESSION,
  POST-APPLY: NO CANONICAL Edit/Write/MultiEdit OF ANY KIND — THE ENTIRE
  CLOSEOUT RUNS VIA \`!\`/bash BELOW. ONE CANONICAL EDIT HERE WOULD EMIT
  pair_rail_review_expected WITH NO HEALTHY TERMINAL (POST-ANCHOR
  DEFICIT) AND RE-POISON THE GATE — THE SAME ARITHMETIC THAT KILLED THE
  a4371c7 ANCHOR. FREEZE OF CANONICAL EDITS IN ALL SESSIONS UNTIL THE
  W3 PASS IS RECORDED.
  ==========================================================================

  Closeout NOW (bash only, in order — AMEND-1 is a FILE: ADR count 181->182,
  so the doc sweep below is MANDATORY before the claims check):
    1. git add $ANCHOR_FILE
    2. Doc sweep 181->182 (sed in place, bash only — 9 sites / 6 docs):
         sed -i '' 's/\*\*181 ADRs\*\*/**182 ADRs**/' CLAUDE.md
         sed -i '' 's/| \*\*181\*\* | under/| **182** | under/' README.md npm/README.md
         sed -i '' "s/# 181 ADRs/# 182 ADRs/" README.md npm/README.md docs/FAQ.md
         sed -i '' 's/181 ADRs document every/182 ADRs document every/' docs/GUIA-COMPLETO.md
         sed -i '' 's/— 181 Architecture Decision Records/— 182 Architecture Decision Records/' docs/GUIA-COMPLETO.md
         sed -i '' 's/# 181 architecture decision records/# 182 architecture decision records/' docs/ARCHITECTURE.md
         sed -i '' 's/| 181                          |/| 182                          |/' docs/ARCHITECTURE.md
         sed -i '' 's/(181 to date)/(182 to date)/' docs/ARCHITECTURE.md
         git add CLAUDE.md README.md npm/README.md docs/FAQ.md docs/GUIA-COMPLETO.md docs/ARCHITECTURE.md
    3. python3 .claude/scripts/check-claude-md-claims.py            # must PASS
    4. bash .claude/scripts/local/verify-counts.sh --no-tests --quiet
    5. git -c user.signingkey=$KEY commit -S \\
         -m "docs(PLAN-164): re-anchor GATE-V2 on the rail ceremony commit + ADR count 182 (closeout)" \\
         -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
       # NEVER put the bracketed sentinel tag in closeout/other messages —
       # resolve_anchor greps for it; a reused tag would move the GATE-V2
       # cutoff to the newer commit and launder the window in between
       # (codex r1 HIGH-1).
    6. git push origin main   # then: gh run watch (Validate = success)

  W3 (NEW session — the 150s registration only applies post-restart):
    - fresh probe, identical-bytes Write pattern (S281) -> expect case A-E
    - verdict stays with PLAN-163:
        bash $PIN_SCRIPT --gate-v2      # must print the NEW anchor + PASS
    - record the PASS in $PLAN163_DIR/probes/ with the kept-8 semantics
      ("liveness under ADR-182 pin + new timeout")
EOF

say "DONE — GATE-RAIL landed at $CEREMONY_SHA"
echo "  Rollback (before push): git reset --hard $START_SHA"
echo "  Rollback (after push) — BOTH commits, reverse order (codex r3 HIGH-N1:"
echo "  reverting only the ceremony leaves ADR count 181 vs closeout docs claiming"
echo "  182 = permanent CI red, and the recovery rerun then dies at its own"
echo "  origin/Validate gates):"
echo "    1. git revert <closeout-sha>   # docs back to 181 (keep the bracketed tag OUT of any -m text)"
echo "    2. git revert $CEREMONY_SHA"
echo "    3. git push origin main && gh run watch   # Validate must be GREEN"
echo "    4. re-run with --rerun-after-revert (the NEW ceremony commit becomes the newest anchor)"
echo "  While reverted, --gate-v2 fails CLOSED by design (reverted ceremonies never anchor)."
