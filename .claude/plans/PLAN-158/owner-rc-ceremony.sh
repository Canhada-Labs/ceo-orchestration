#!/usr/bin/env bash
# =============================================================================
# owner-rc-ceremony.sh — PLAN-158 Wave 3: RC tag ceremony (Owner runs via `!`).
#
# Cuts v1.1.0-rc.1: authors the pair-rail RC verdict ENVELOPE at run time
# (parent_sha / generated_at / inputs_hash / tool pins / transcript hash),
# GPG-signs the canonical fields file, commits the verdict, creates the
# SIGNED tag, pushes, and prints the release-gate monitor commands.
#
# The verdict BODY (codex findings, verdict rationale) is data, prepared by
# the CEO at .claude/plans/PLAN-158/rc-verdict-body.md — this script never
# invents review content; it binds the envelope and authorizes via GPG.
#
# ⚠ PREREQUISITES (in order):
#   1. npmjs.com trusted publisher registered (repo Canhada-Labs/
#      ceo-orchestration, workflow npm-publish.yml [FILENAME], environment
#      production-npm). Not needed for the RC itself (RC skips npm) but do
#      it NOW so GA (Wave 4, ≥24h later) does not die ENEEDAUTH.
#   2. Validate green on current HEAD of main.
#   3. rc-verdict-body.md reviewed by you (the codex R1 output + CEO fold).
#
# After this script: RC-hold 24h FULL (ADR-103; Owner-ratified OQ4
# RC-hold-full). GA ceremony is a SEPARATE script run ≥24h later with a
# FRESH pair-rail verdict (verdicts are per-tag; TTL 24h).
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
TAG="v1.1.0-rc.1"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
GOV=".claude/governance"
PLANDIR=".claude/plans/PLAN-158"
VERDICT="$GOV/pair-rail-verdict-$TAG.md"
BODY="$PLANDIR/rc-verdict-body.md"
FIELDS="$PLANDIR/architect/rc/verdict-fields-$TAG.txt"
TRANSCRIPT="$PLANDIR/rc-review-transcript.txt"
export GPG_TTY="${GPG_TTY:-$(tty || true)}"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- preflight --------------------------------------------------------------
say "Preflight"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
[ -z "$(git status --porcelain=v1)" ] || { git status --short >&2; die "working tree not clean"; }
git fetch origin main --quiet
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "main not up to date with origin"
gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || die "signing key $KEY not in keyring"
[ -f "$BODY" ] || die "verdict body missing: $BODY (CEO prepares it from codex R1)"
[ -f "$TRANSCRIPT" ] || die "codex transcript missing: $TRANSCRIPT"
# machine-local staged overlay (gitignored by design) — required unless the
# SENT-RC-SPEC fix has already been applied to canonical:
if ! diff -q "$PLANDIR/staged/rc/npm-shim.md" SPEC/v1/npm-shim.md >/dev/null 2>&1; then
  [ -f "$PLANDIR/staged/rc/npm-shim.md" ] || die "staged/rc/npm-shim.md missing — run from the session's machine (staged/ is machine-local)"
fi
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null && die "tag $TAG already exists"

say "Validate green on HEAD?"
VSTATE=$(gh run list --workflow validate.yml --branch main --limit 1 \
  --json headSha,status,conclusion \
  --jq '.[0] | .headSha + ":" + .status + ":" + .conclusion')
case "$VSTATE" in
  "$(git rev-parse HEAD)":completed:success) echo "    Validate OK ($VSTATE)";;
  *) die "Validate on HEAD is not completed:success → $VSTATE (wait or fix first)";;
esac

say "Codex pin verification"
CODEX_VER_RAW="$(codex --version 2>/dev/null || true)"
CODEX_VER="$(printf '%s' "$CODEX_VER_RAW" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
[ -n "$CODEX_VER" ] || die "codex CLI not found"
BIN_SHA="$(shasum -a 256 "$(command -v codex)" | awk '{print $1}')"
PIN_SHA="$(grep -E '^[0-9a-f]{64}$' "$GOV/codex-cli-binary-sha256.txt" | head -1)"
[ "$BIN_SHA" = "$PIN_SHA" ] || die "codex binary sha $BIN_SHA != pin $PIN_SHA"
python3 - "$CODEX_VER" <<'PYEOF' || die "codex version outside pin range"
import re, sys
ver = tuple(int(x) for x in sys.argv[1].split("."))
spec = open(".claude/governance/codex-cli-pin.txt").read()
rng = [l.strip() for l in spec.splitlines() if l.strip() and not l.strip().startswith("#")][-1]
lo = tuple(int(x) for x in re.search(r">=([0-9.]+)", rng).group(1).split("."))
hi = tuple(int(x) for x in re.search(r"<([0-9.]+)", rng).group(1).split("."))
sys.exit(0 if lo <= ver < hi else 1)
PYEOF
echo "    codex $CODEX_VER in range, binary sha matches pin"

say "Advisory freshness quick-check (6 workflows, latest non-red + <14d)"
for wf in chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml red-team.yml formal-verify.yml; do
  latest=$(gh run list --workflow "$wf" --limit 1 --json conclusion,startedAt \
    --jq '.[0] | .conclusion + " " + .startedAt' 2>/dev/null || echo "none")
  case "$latest" in
    success*) ;;
    *) die "$wf latest run: $latest — dispatch/fix it before tagging (gh workflow run $wf)";;
  esac
  started=$(echo "$latest" | awk '{print $2}')
  age_days=$(( ( $(date -u +%s) - $(date -ju -f "%Y-%m-%dT%H:%M:%SZ" "$started" +%s 2>/dev/null || gdate -u -d "$started" +%s) ) / 86400 ))
  [ "$age_days" -lt 14 ] || die "$wf stale: last run ${age_days}d ago"
  echo "    $wf OK (${age_days}d)"
done

# ---- SENT-RC-SPEC: apply the R1-folded SPEC fix under sentinel --------------
# (codex R1 P2: stale cross-reference; R2 APPROVE on the staged diff. The fix
# must land BEFORE the envelope so the tagged tree carries the corrected SPEC.)
if diff -q "$PLANDIR/staged/rc/npm-shim.md" SPEC/v1/npm-shim.md >/dev/null 2>&1; then
  say "SENT-RC-SPEC: fix already applied (canonical matches staged) — skipping"
else
  say "SENT-RC-SPEC: sign + apply SPEC/v1/npm-shim.md cross-reference fix"
  SENTDIR="$PLANDIR/architect/rc-spec"
  [ -f "$SENTDIR/approved.body.md" ] || die "sentinel body missing: $SENTDIR/approved.body.md"
  ANCHOR="$(git rev-parse HEAD)"
  sed "s/__ANCHOR_SHA__/$ANCHOR/" "$SENTDIR/approved.body.md" > "$SENTDIR/approved.md"
  rm -f "$SENTDIR/approved.md.asc"
  gpg --local-user "$KEY" --armor --detach-sign --output "$SENTDIR/approved.md.asc" "$SENTDIR/approved.md" \
    || die "GPG signing failed (export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"
  cp "$PLANDIR/staged/rc/npm-shim.md" SPEC/v1/npm-shim.md
  # touched-set == scope check: exactly the SPEC file + sentinel artifacts
  TOUCHED="$(git status --porcelain=v1 | awk '{print $2}' | grep -v "^.claude/plans/PLAN-158/" || true)"
  [ "$TOUCHED" = "SPEC/v1/npm-shim.md" ] || die "touched set != scope: [$TOUCHED]"
  # staged/rc/* is machine-local by design (.gitignore:17 'staged/') — the
  # signed sentinel + the applied SPEC file are the committed record.
  git add SPEC/v1/npm-shim.md "$SENTDIR/approved.md" "$SENTDIR/approved.md.asc"
  git commit -S -m "fix(PLAN-158): SENT-RC-SPEC — npm-shim §Cross-reference OIDC stale claim

Pair-rail RC R1 P2 (codex 0.144.1): ADR-012 cross-reference still said
trusted publisher 'not yet configured' vs §Publishing OIDC-live. Doc-only
sweep; R2 APPROVE on staged diff. [SENT-RC-SPEC]"
  echo "    SENT-RC-SPEC landed: $(git rev-parse --short HEAD)"
fi

# ---- envelope ---------------------------------------------------------------
say "Assemble verdict envelope (computed NOW — TTL 24h starts here)"
PARENT_SHA="$(git rev-parse HEAD)"
GENERATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
INPUTS_HASH="$(python3 - <<'PYEOF'
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("vprv", ".github/scripts/validate-pair-rail-verdict.py")
vprv = importlib.util.module_from_spec(spec); spec.loader.exec_module(vprv)
print(vprv.compute_inputs_hash(Path("."), Path(".claude/governance/pair-rail-inputs-hash-manifest.txt")))
PYEOF
)"
MANIFEST_SHA="$(shasum -a 256 "$GOV/pair-rail-inputs-hash-manifest.txt" | awk '{print $1}')"
TRANSCRIPT_SHA="$(shasum -a 256 "$TRANSCRIPT" | awk '{print $1}')"
PY_VER="$(python3 -c 'import platform; print(platform.python_version())')"
echo "    parent_sha=$PARENT_SHA"
echo "    inputs_hash=$INPUTS_HASH"

# Findings block: extracted verbatim from the body file (between markers).
FINDINGS_YAML="$(awk '/^<!-- FINDINGS-YAML/{f=1;next} /^FINDINGS-YAML -->/{f=0} f' "$BODY")"
[ -n "$FINDINGS_YAML" ] || FINDINGS_YAML="findings: []"
VERDICT_WORD="$(awk '/^<!-- VERDICT:/{print $3; exit}' "$BODY")"
case "$VERDICT_WORD" in
  GO|GO-WITH-CONDITIONS) ;;
  NO-GO) die "body says NO-GO — do not tag; fold findings and re-run codex";;
  *) die "body missing '<!-- VERDICT: GO|NO-GO|GO-WITH-CONDITIONS -->' marker";;
esac

mkdir -p "$(dirname "$FIELDS")"
cat > "$FIELDS" <<EOF
verdict: $VERDICT_WORD
generated_at: $GENERATED_AT
ttl_hours: 24
parent_sha: $PARENT_SHA
release_tag: $TAG
inputs_hash: $INPUTS_HASH
inputs_hash_paths_manifest_sha: $MANIFEST_SHA
tool_versions:
  codex_cli: $CODEX_VER
  codex_cli_binary_sha256: $BIN_SHA
  claude_code: claude-fable-5
  python: $PY_VER
transcript_hash: $TRANSCRIPT_SHA
$FINDINGS_YAML
EOF

say "GPG sign the fields file"
rm -f "$FIELDS.asc"
gpg --local-user "$KEY" --armor --detach-sign --output "$FIELDS.asc" "$FIELDS" \
  || die "GPG signing failed (try: export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"
SIG_B64="$(base64 < "$FIELDS.asc" | tr -d '\n')"

say "Write $VERDICT"
{
  echo "# Pair-Rail Verdict — $TAG"
  echo
  echo '```yaml'
  cat "$FIELDS"
  echo "gpg_signature: base64:$SIG_B64"
  echo '```'
  echo
  echo "## Signature verification recipe"
  echo
  echo 'base64 -d of the value after `base64:` → detached .asc; verify against'
  echo "\`$FIELDS\` (committed alongside). Signer $KEY."
  echo
  cat "$BODY"
} > "$VERDICT"

say "Commit verdict + evidence"
git add "$VERDICT" "$FIELDS" "$FIELDS.asc" "$TRANSCRIPT" "$BODY"
git commit -S -m "release(PLAN-158): pair-rail RC verdict $VERDICT_WORD for $TAG

Envelope bound to parent_sha $PARENT_SHA; codex-cli $CODEX_VER (pinned
binary verified); inputs_hash over the 18-path trust-chain manifest;
transcript + body committed as evidence. Wave 3 RC ceremony."
VERDICT_COMMIT="$(git rev-parse HEAD)"
echo "    verdict commit: $VERDICT_COMMIT (parent $PARENT_SHA)"

say "Signed tag $TAG"
git tag -s "$TAG" -m "ceo-orchestration $TAG — release candidate (PLAN-158 Wave 3)

Pair-rail verdict: $VERDICT_WORD (parent_sha $PARENT_SHA).
RC-hold 24h FULL begins at release-gate green (ADR-103)."
git tag -v "$TAG" || die "tag signature does not verify"

say "Push"
git push origin main
git push origin "$TAG"

say "DONE — monitor the release gate:"
echo "  gh run list --workflow release.yml --limit 1"
echo "  gh run watch \$(gh run list --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
echo
echo "RC-hold 24h FULL a partir do release-gate verde. Wave 4 (GA):"
echo "  1. (prereq) trusted publisher já registrado no console npm"
echo "  2. ≥24h depois: rode owner-ga-ceremony.sh (verdict GA FRESCO é gerado lá)"
echo "  3. GA publica no npm via OIDC → depois REVOGUE o NPM_TOKEN antigo + rotation-log"
