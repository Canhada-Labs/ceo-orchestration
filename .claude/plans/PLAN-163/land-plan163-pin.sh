#!/usr/bin/env bash
# =============================================================================
# land-plan163-pin.sh — PLAN-163 GATE-PIN: codex payload-pin ceremony
# (Owner runs `!`). Modeled on land-plan161.sh; FIRST of the two declared
# PLAN-163 ceremonies (order: GATE-PIN → GATE-V2 → pack review → pack GPG).
#
# Scope: .claude/plans/PLAN-163/staged/pin-pack/ ONLY (20 files, ADR-182
# payload-pin + verify-then-invoke enforcement + ADR-111 ledger repair;
# +2 = the migrated test_check_pair_rail_{matrix,golden}.py, PLAN-163 FXα).
# Integrity is pinned by the TRACKED manifest twin
# `.claude/plans/PLAN-163/inputs-pin.sha256` (byte-copy of the staged
# consolidated MANIFEST.sha256; `shasum -a 256 -c` fail-closed — staged/ is
# gitignored, so the twin is the tamper-evidence rail, S274 lesson).
#
# PREFLIGHT (no signature, no live-tree write):
#   - manifest twin tracked + identical to staged + shasum -c fail-closed
#   - sentinel Scope == manifest dest-set (NAME-BY-NAME set equality, S272)
#   - overlay clone (git clone --local) + pin-pack applied THERE
#   - pytest of the 4 pin-pack test files (incl. the red-first
#     launcher≠payload tests in test_check_pair_rail_payload_pin.py)
#   - pair-rail-gate.sh --phase 6 in the overlay, against the REAL
#     installed codex binary (Gate 4 unstubbed)
#   - LIVE payload-sha revalidation: `check_pair_rail.py --verify-codex-pin`
#     recomputes the installed payload sha NOW vs the staged manifest —
#     if codex changed since the probe, ABORT with re-probe instructions
#
# APPLY (real run only): sentinel signed INLINE (anchor = HEAD, GPG detach
# + verify), cp per manifest, post-apply oracles, ONE signed commit
# `[SENT-PLAN163-PIN]`, GATE-PIN anchor recorded, then the embedded
# GATE-V2 probe/instructions.
#
# GATE-V2 (re-runnable any time after the ceremony):
#   bash .claude/plans/PLAN-163/land-plan163-pin.sh --gate-v2
# Evaluates ONLY events with ts AFTER the ceremony commit (S283
# any-in-window correction): expected>=1 ∧ healthy>=1 ∧ failopen==0 ∧
# no deficit/unclassified on the post-anchor set.
#
# Usage:
#   bash .claude/plans/PLAN-163/land-plan163-pin.sh --preflight-only
#   bash .claude/plans/PLAN-163/land-plan163-pin.sh --dry-run
#   bash .claude/plans/PLAN-163/land-plan163-pin.sh
#   bash .claude/plans/PLAN-163/land-plan163-pin.sh --gate-v2
#
# --dry-run: everything except gpg + git add/commit; restores tree AND
# index on ANY exit (trap, S273 lesson). Origin/Validate/gpg soften to WARN.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO" || exit 1
PLAN_DIR=".claude/plans/PLAN-163"
STAGED="$PLAN_DIR/staged/pin-pack"
MANIFEST_STAGED="$STAGED/MANIFEST.sha256"
MANIFEST_TRACKED="$PLAN_DIR/inputs-pin.sha256"
SENTINEL_DIR="$PLAN_DIR/architect/round-1-pin"
ANCHOR_FILE="$PLAN_DIR/GATE-PIN-ANCHOR"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
AUDIT_LOG="${HOME}/.claude/projects/ceo-orchestration/audit-log.jsonl"
GPG_TTY="${GPG_TTY:-$(tty || true)}"
export GPG_TTY
export CEO_OVERHEAD_ACK=1
# Owner-shell apply route (cp/git) does not trip in-session canonical hooks —
# the signed sentinel IS the authorization record (S261 precedent); the
# kernel-override export below is the ADR-031 declaration for release.yml.

DRY_RUN=0
PREFLIGHT_ONLY=0
GATE_V2_ONLY=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  --preflight-only) DRY_RUN=1; PREFLIGHT_ONLY=1 ;;
  --gate-v2) GATE_V2_ONLY=1 ;;
  "") ;;
  *) echo "usage: $0 [--dry-run|--preflight-only|--gate-v2]" >&2; exit 64 ;;
esac

START_SHA="$(git rev-parse HEAD)"
RESTORE_HINT="nothing was changed — safe to rerun after fixing the cause"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/land-plan163-pin.XXXXXX")"

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

# =============================================================================
# GATE-V2 — post-anchor fresh-liveness verdict (also called at end of apply)
# =============================================================================
resolve_anchor() {
  # Prefer the recorded anchor file; fall back to the tagged commit in log.
  local sha="" ts=""
  if [ -f "$ANCHOR_FILE" ]; then
    sha="$(sed -n 's/^sha=//p' "$ANCHOR_FILE" | head -1)"
    ts="$(sed -n 's/^ts=//p' "$ANCHOR_FILE" | head -1)"
  fi
  if [ -z "$sha" ]; then
    sha="$(git log --format='%H' --grep='\[SENT-PLAN163-PIN\]' -n 1 || true)"
    [ -n "$sha" ] && ts="$(git log -1 --format='%cI' "$sha")"
  fi
  [ -n "$sha" ] && [ -n "$ts" ] || return 1
  printf '%s\t%s\n' "$sha" "$ts"
}

gate_v2() {
  say "GATE-V2 — fresh liveness under the NEW pin (post-anchor set ONLY)"
  local pair
  if ! pair="$(resolve_anchor)"; then
    die "GATE-V2: no anchor — the GATE-PIN ceremony commit was not found (run the ceremony first)"
  fi
  local ANCHOR_SHA ANCHOR_TS
  ANCHOR_SHA="$(printf '%s' "$pair" | cut -f1)"
  ANCHOR_TS="$(printf '%s' "$pair" | cut -f2)"
  echo "    anchor commit: $ANCHOR_SHA"
  echo "    anchor ts:     $ANCHOR_TS (events strictly AFTER this count)"

  say "GATE-V2 step 1 — enforcement self-check (ADR-182 verify-codex-pin, live tree)"
  local rc=0
  set +e
  CLAUDE_PROJECT_DIR="$REPO" python3 .claude/hooks/check_pair_rail.py \
    --verify-codex-pin "$(command -v codex)" | tee "$SCRATCH/gv2-selfcheck.json"
  rc=$?
  set -e
  [ "$rc" -eq 0 ] || die "GATE-V2: --verify-codex-pin exited rc=$rc — the enforcement path is NOT healthy under the landed pin"
  echo "    self-check OK (payload sha verified against the landed manifest)"

  say "GATE-V2 step 2 — post-anchor classifier (mirrors ceo-boot failopen_rail_liveness_7d)"
  set +e
  GV2_ANCHOR_TS="$ANCHOR_TS" GV2_AUDIT_LOG="$AUDIT_LOG" python3 - <<'PYEOF'
import json, os, re, sys
from datetime import datetime, timezone

anchor = datetime.fromisoformat(os.environ["GV2_ANCHOR_TS"].replace("Z", "+00:00"))
log = os.environ["GV2_AUDIT_LOG"]
RID = re.compile(r"^[0-9a-f]{16}$")

expected_total = 0
healthy = failopen = unclassified = 0
expected_ids, terminal_ids = set(), set()
exp_bucket, term_bucket = {}, {}

def bucket(ev):
    return (str(ev.get("session_id") or ""), str(ev.get("file_path_hash_prefix") or ""))

def rid(ev):
    r = str(ev.get("review_id") or "")
    return r if RID.match(r) else ""

try:
    fh = open(log, "r", encoding="utf-8", errors="replace")
except OSError as exc:
    print("GATE-V2: audit log unreadable (%s) — cannot prove liveness" % exc)
    sys.exit(1)

with fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = ev.get("ts") or ev.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt <= anchor:
            continue
        action = ev.get("action")
        if action == "pair_rail_review_expected":
            expected_total += 1
            r = rid(ev)
            if r:
                expected_ids.add((str(ev.get("session_id") or ""), r))
            else:
                exp_bucket[bucket(ev)] = exp_bucket.get(bucket(ev), 0) + 1
        elif action == "pair_rail_case":
            case = ev.get("case")
            if case == "F":
                failopen += 1
            elif case in ("A", "B", "C", "D", "E"):
                healthy += 1
            else:
                unclassified += 1
            r = rid(ev)
            if r:
                terminal_ids.add((str(ev.get("session_id") or ""), r))
            else:
                term_bucket[bucket(ev)] = term_bucket.get(bucket(ev), 0) + 1
        elif action in ("pair_rail_codex_unavailable", "pair_rail_fatal_failopen"):
            failopen += 1
        elif action in ("pair_rail_review_passed", "pair_rail_codex_violation"):
            healthy += 1

outstanding = expected_ids - terminal_ids
deficit = len(outstanding) + sum(
    max(0, n - term_bucket.get(k, 0)) for k, n in exp_bucket.items()
)

print("    post-anchor expected      : %d" % expected_total)
print("    post-anchor healthy (A-E) : %d" % healthy)
print("    post-anchor failopen (F..): %d" % failopen)
print("    post-anchor unclassified  : %d" % unclassified)
print("    post-anchor deficit       : %d%s" % (
    deficit, ("  outstanding=%s" % sorted(outstanding)) if outstanding else ""))

ok = (expected_total >= 1 and healthy >= 1 and failopen == 0
      and unclassified == 0 and deficit == 0)
print("")
print("    GATE-V2 VERDICT: %s" % ("PASS" if ok else "FAIL (not yet satisfied)"))
sys.exit(0 if ok else 1)
PYEOF
  local verdict=$?
  set -e

  say "GATE-V2 step 3 — official classifier confirmation (ceo-boot, window = hours-since-anchor)"
  local hours
  hours="$(GV2_ANCHOR_TS="$ANCHOR_TS" python3 -c '
import os
from datetime import datetime, timezone
a = datetime.fromisoformat(os.environ["GV2_ANCHOR_TS"].replace("Z", "+00:00"))
h = (datetime.now(timezone.utc) - a).total_seconds() / 3600.0
print(max(1.0, round(h, 3)))')"
  echo "    CEO_FAILOPEN_LIVENESS_WINDOW_H=$hours (clamped >=1h by ceo-boot; if the"
  echo "    ceremony is <1h old this ADVISORY row may include pre-anchor events —"
  echo "    the step-2 verdict above is the exact post-anchor authority)"
  CEO_FAILOPEN_LIVENESS_WINDOW_H="$hours" python3 .claude/scripts/ceo-boot.py --json 2>/dev/null \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
for r in d.get("results", []):
    if r.get("name") == "failopen_rail_liveness_7d":
        print("    ceo-boot row: [%s] %s" % (r.get("status"), r.get("summary")))
        break
else:
    print("    ceo-boot row: NOT FOUND (check name drift)")' \
    || warn "ceo-boot confirmation run failed (advisory only)"

  if [ "$verdict" -ne 0 ]; then
    cat <<EOF

  GATE-V2 is NOT satisfied yet. To generate a FRESH invocation under the
  new pin (zero-risk S281 pattern):
    1. Open a NEW Claude Code session in this repo (the landed pin must be
       the one in the tree — push not required for a local session).
    2. Ask for ONE trivial canonical edit that rewrites a hook file with
       IDENTICAL bytes (e.g. "re-write .claude/hooks/check_pair_rail.py
       with its exact current content via Write") — this drives the REAL
       PreToolUse pair-rail path exactly as the harness runs it (no manual
       env), emitting pair_rail_review_expected + pair_rail_case.
    3. Re-run:  bash $PLAN_DIR/land-plan163-pin.sh --gate-v2
  Manual proof (equivalent):
    python3 - reads $AUDIT_LOG and filters ts > $ANCHOR_TS for actions
    pair_rail_review_expected / pair_rail_case (case A-E healthy, F failopen).
EOF
    exit 1
  fi
  say "GATE-V2 PASS — record this output in the plan; the pack ceremony may proceed"
  return 0
}

if [ "$GATE_V2_ONLY" = 1 ]; then
  gate_v2
  exit 0
fi

# =============================================================================
# PREFLIGHT (ALL checks run BEFORE any GPG sign)
# =============================================================================
say "Preflight — GATE-PIN (no signature until every oracle is green)"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
command -v python3 >/dev/null || die "python3 not found"
command -v shasum  >/dev/null || die "shasum not found"
command -v codex   >/dev/null || die "codex CLI not found in PATH (the pin ceremony attests the INSTALLED binary)"
CODEX_LAUNCHER="$(command -v codex)"

say "Tree state (pin scope must come ONLY from staged/; W2 dirt is tolerated)"
# The pack ceremony (land-plan163-pack.sh) commits the W2 live-tree fixes
# LATER; during GATE-PIN they are allowed dirt — but they must stay disjoint
# from the pin scope, which the assert below enforces by exact path.
RE_PLANS='^\.claude/plans/'
RE_STATE='^\.claude/state/'
RE_W2='^(\.claude/scripts/(audit-telemetry\.py|budget-summary\.py|ceo-cost\.py|cost-table\.yaml|detectors/(overpowered|wasteful_thinking)\.py|detectors/tests/test_overpowered\.py|tests/test_model_fleet_presence\.py)|scripts/local/smoke-install-parity\.sh|scripts/tests/test-parity-stale-planted\.sh)$'
touched_files() { git status --porcelain=v1 | sed -E 's/^.{3}//; s/^.* -> //'; }
BAD="$(touched_files | grep -vE "${RE_PLANS}|${RE_STATE}|${RE_W2}" || true)"
if [ -n "$BAD" ]; then
  printf '%s\n' "$BAD" >&2
  die "unexpected dirty files outside plans/state/W2 allowlist — resolve before the ceremony"
fi
echo "    tree OK (only plan materials / .claude/state / known W2 dirt)"

say "Staged manifest twin (tracked, fail-closed — S274 lesson)"
[ -f "$MANIFEST_STAGED" ] || die "staged manifest missing: $MANIFEST_STAGED (pack is machine-local)"
if [ ! -f "$MANIFEST_TRACKED" ]; then
  cp "$MANIFEST_STAGED" "$MANIFEST_TRACKED"
  warn "created tracked twin $MANIFEST_TRACKED from staged — COMMIT IT before the real run:"
  warn "  git add $MANIFEST_TRACKED && git commit -m 'docs(PLAN-163): pin-pack input manifest (tamper-evidence)'"
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
[ "$N_ROWS" = "20" ] || die "pin manifest row count is $N_ROWS, expected 20"
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

say "ADR count pre-apply (must be 180; ADR-182 makes it 181)"
_adr_now="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
[ "$_adr_now" = "180" ] || die "pre-apply ADR count is $_adr_now, expected 180"

# ---- overlay: scratch clone with the pin-pack applied; oracles run there ----
say "Build verification overlay (clone + pin-pack applied)"
OVERLAY="$SCRATCH/overlay"
git clone --local --no-hardlinks --quiet "$REPO" "$OVERLAY" || die "overlay clone failed"
while IFS=$'\t' read -r _sha src dst; do
  mkdir -p "$OVERLAY/$(dirname "$dst")"
  cp "$src" "$OVERLAY/$dst" || die "overlay apply failed: $src -> $dst"
done < <(manifest_rows)
echo "    overlay ready: $OVERLAY"

say "LIVE payload-sha revalidation (staged manifest vs the binary installed NOW)"
# The staged helper + staged manifest (both applied in the overlay) run
# against the REAL launcher: this recomputes the native payload sha at
# ceremony time. If codex was upgraded since the T5.2a probe, this MUST
# abort — never sign a stale attestation.
set +e
PIN_OUT="$(cd "$OVERLAY" && CLAUDE_PROJECT_DIR="$OVERLAY" \
  python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$CODEX_LAUNCHER")"
PIN_RC=$?
set -e
echo "    verify-codex-pin: $PIN_OUT (rc=$PIN_RC)"
if [ "$PIN_RC" -ne 0 ]; then
  cat >&2 <<EOF
  The installed codex payload does NOT match the staged manifest
  (rc=1 mismatch/triple-missing, rc=3 infra). If codex was upgraded since
  the T5.2a probe, RE-PROBE before any ceremony:
    1. npm ls -g @openai/codex  (record the new version)
    2. Recompute the native payload sha per ADR-182 (resolve
       @openai/codex-<platform>/vendor/<triple>/bin/codex, shasum -a 256)
    3. Update staged/pin-pack/.claude/governance/codex-cli-pin-manifest.json
       (+ package_version + npm_integrity), recompute MANIFEST.sha256,
       refresh the tracked twin, and RE-RUN the cross-vendor review of the
       changed bytes before landing.
EOF
  die "payload-sha revalidation failed — the pin would attest a stale binary"
fi
echo "    installed payload matches the staged pin manifest"

run_oracle() { # label logfile cmd... (cwd = overlay, CLAUDE_PROJECT_DIR pinned)
  local label="$1" log="$2"; shift 2
  if ( cd "$OVERLAY" && CLAUDE_PROJECT_DIR="$OVERLAY" "$@" ) > "$log" 2>&1; then
    echo "    ORACLE GREEN: $label"
  else
    tail -20 "$log" >&2
    die "ORACLE RED: $label (log: $log) — GATE-PIN has no drop-out protocol; fix or defer the whole pin"
  fi
}

say "Pin oracles (in overlay) — fail-closed, no CF-8 drop-out for a supply-chain gate"
# test_check_pair_rail_{matrix,golden}.py are now IN the pin manifest
# (PLAN-163 FXα migrated them to the _invoke_codex_review mock boundary in
# lockstep with the hook's fixture-path removal, so they must land atomically
# WITH the hook — an un-migrated copy would break against the pinned rail).
run_oracle "pin-pack pytest (pair-rail + matrix + golden + payload-pin red-first + substrate-watch + verdict validator)" \
  "$SCRATCH/o-pin1.log" \
  python3 -m pytest \
    .claude/hooks/tests/test_check_pair_rail.py \
    .claude/hooks/tests/test_check_pair_rail_matrix.py \
    .claude/hooks/tests/test_check_pair_rail_golden.py \
    .claude/hooks/tests/test_check_pair_rail_payload_pin.py \
    .claude/scripts/tests/test_check_substrate_watch.py \
    .github/scripts/tests/test_validate_pair_rail_verdict.py -q

if [ -n "${OPENAI_API_KEY:-}" ]; then
  run_oracle "pair-rail-gate.sh --phase 6 (Gate 4 unstubbed, REAL installed codex)" \
    "$SCRATCH/o-pin2.log" \
    bash .claude/scripts/local/pair-rail-gate.sh --phase 6
else
  if [ "$DRY_RUN" = 1 ]; then
    warn "OPENAI_API_KEY unset — pair-rail-gate.sh --phase 6 SKIPPED (Gate 1 would fail); source your env before the real run"
  else
    die "OPENAI_API_KEY unset — pair-rail-gate.sh --phase 6 cannot run (source your .envrc)"
  fi
fi

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

say "Sign the GATE-PIN sentinel (inline)"
sign_sentinel

say "Apply pin-pack to the live tree (kernel: release.yml under declared override)"
export CEO_KERNEL_OVERRIDE="PLAN-163-T5-CODEX-PIN"
export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
RESTORE_HINT="git reset --hard $START_SHA  (sentinel .md/.asc under $SENTINEL_DIR are plan materials)"
while IFS=$'\t' read -r _sha src dst; do
  apply_cp "$src" "$dst"
done < <(manifest_rows)

say "Post-apply verification (live tree)"
python3 -m pytest \
  .claude/hooks/tests/test_check_pair_rail.py \
  .claude/hooks/tests/test_check_pair_rail_matrix.py \
  .claude/hooks/tests/test_check_pair_rail_golden.py \
  .claude/hooks/tests/test_check_pair_rail_payload_pin.py \
  .claude/scripts/tests/test_check_substrate_watch.py \
  .github/scripts/tests/test_validate_pair_rail_verdict.py -q \
  > "$SCRATCH/post-pin1.log" 2>&1 || die "post-apply pin pytest RED ($SCRATCH/post-pin1.log)"
set +e
( CLAUDE_PROJECT_DIR="$REPO" python3 .claude/hooks/check_pair_rail.py \
    --verify-codex-pin "$CODEX_LAUNCHER" ) > "$SCRATCH/post-pin2.log" 2>&1
_vrc=$?
set -e
[ "$_vrc" -eq 0 ] || die "post-apply --verify-codex-pin rc=$_vrc ($SCRATCH/post-pin2.log)"
_adr_post="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
[ "$_adr_post" = "181" ] || die "post-apply ADR count is $_adr_post, expected 181 (ADR-182 added)"
echo "    pytest + verify-codex-pin + ADR-count(181) OK"

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
  echo "    [dry-run] would commit the pin ceremony (20 files + plan dir)"
  restore_dry_run
  trap - EXIT
  say "[dry-run] DONE — full rehearsal green (no signature, no commit). Run without --dry-run to land."
  exit 0
fi

say "Commit (signed)"
while read -r f; do git add "$f" || die "git add failed: $f"; done < "$SCRATCH/dests.txt"
git add "$PLAN_DIR" || die "git add failed: $PLAN_DIR"
BAD="$(touched_files | grep -vE "${RE_SCOPE}|${RE_PLANS}|${RE_STATE}|${RE_W2}" || true)"
if [ -n "$BAD" ]; then printf '%s\n' "$BAD" >&2; die "touched − scope != ∅ before commit"; fi
echo "    touched ⊆ scope OK"
git -c user.signingkey="$KEY" commit -S -F - <<'MSG' || die "commit failed"
fix(PLAN-163): GATE-PIN — codex payload pin + verify-then-invoke (ADR-182) [SENT-PLAN163-PIN]

The retired sha pin attested the npm JS launcher (codex.js), not the
native payload that executes — the 0.144.1->0.144.6 payload bump passed
the "pin" with NO gate trip (T5.2a evidence). This ceremony lands:
codex-cli-pin-manifest.json (schema 1, per-targetTriple payload sha256 +
npm dist.integrity provenance); check_pair_rail.py resolves the native
payload, verifies its sha256 against the manifest BEFORE the subprocess
and invokes EXACTLY the verified path (fail-closed on mismatch /
triple-missing; --verify-codex-pin CLI shared with the gate);
pair-rail-gate.sh Gate 4 unstubbed onto the same helper;
validate-pair-rail-verdict.py + release.yml envelope carry payload sha +
targetTriple (legacy semantics preserved for pre-ADR-182 tags);
codex-cli-binary-sha256.txt becomes a tombstone; ADR-111 ledger repaired
(false "SUPERSEDED by ADR-120" relation removed — ADR-120 is the PII
ADR). ADR-182 is NEW (180 -> 181; CLAUDE.md count surfaces update in the
closeout commit before push). Kernel surface release.yml under
CEO_KERNEL_OVERRIDE=PLAN-163-T5-CODEX-PIN; sentinel
PLAN-163/architect/round-1-pin (GPG, anchor = pre-ceremony HEAD).
This commit's timestamp is the GATE-V2 anchor (post-anchor events only).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
MSG
unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
CEREMONY_SHA="$(git rev-parse HEAD)"
CEREMONY_TS="$(git log -1 --format='%cI' "$CEREMONY_SHA")"
echo "    committed: $(git log --oneline -1)"

say "Record the GATE-V2 anchor"
{
  echo "# PLAN-163 GATE-PIN anchor — GATE-V2 counts ONLY events after ts="
  echo "sha=$CEREMONY_SHA"
  echo "ts=$CEREMONY_TS"
} > "$ANCHOR_FILE"
echo "    $ANCHOR_FILE (commit it with the closeout; --gate-v2 also falls back to git log)"

say "Closeout counts NOTE (do BEFORE push — claims gate is tolerance=0)"
cat <<'EOF'
    ADR count is now 181 while CLAUDE.md still claims 180. Before pushing:
      1. Update CLAUDE.md ADR count 180 -> 181 (closeout commit; also sweep
         the unwatched docs: ARCHITECTURE/GUIA-COMPLETO/FAQ/npm-README).
      2. python3 .claude/scripts/check-claude-md-claims.py   (must PASS)
      3. bash .claude/scripts/local/verify-counts.sh --no-tests --quiet
      4. git push origin main && watch Validate.
EOF

# Embedded GATE-V2 probe (will normally FAIL now — no post-anchor events yet;
# that is the honest state, not an error of the ceremony).
set +e
gate_v2
GV2_RC=$?
set -e

say "DONE — GATE-PIN landed at $CEREMONY_SHA"
echo "  Rollback (before push): git reset --hard $START_SHA"
echo "  Rollback (after push):  git revert $CEREMONY_SHA  (then re-run the pin ceremony)"
if [ "$GV2_RC" -ne 0 ]; then
  echo ""
  echo "  GATE-V2 is pending fresh post-anchor invocations (instructions above)."
  echo "  Re-check any time:  bash $PLAN_DIR/land-plan163-pin.sh --gate-v2"
fi
