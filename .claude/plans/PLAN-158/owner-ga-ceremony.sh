#!/usr/bin/env bash
# =============================================================================
# owner-ga-ceremony.sh — PLAN-158 Wave 4: GA tag ceremony (Owner runs via `!`).
#
# Cuts v1.1.0 GA ≥24h after the RC release-gate went green (RC-hold FULL,
# Owner-ratified). SELF-CONTAINED fresh pair-rail verdict: this script runs
# codex itself on the rc.1..HEAD delta (usually empty/tiny), asserts APPROVE,
# assembles + GPG-signs the per-tag envelope, tags, pushes.
#
# ⚠ HARD PREREQUISITE: npmjs.com trusted publisher registered
#   (repo Canhada-Labs/ceo-orchestration, workflow npm-publish.yml [FILENAME],
#   environment production-npm). Without it the publish dies ENEEDAUTH —
#   playbook: .claude/plans/PLAN-158/oidc-failure-playbook.md (delete/re-tag
#   with the pre-authorized rollback patch).
#
# AFTER the tag: (1) approve the production-npm environment gate when
# npm-publish.yml pauses; (2) npx ceo-orchestration@latest --help smoke;
# (3) REVOKE the old NPM_TOKEN on npmjs.com + delete the repo secret +
# record in docs/rotation-log.md; (4) session closeout (plan → done).
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
TAG="v1.1.0"
RC_TAG="v1.1.0-rc.1"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
GOV=".claude/governance"
PLANDIR=".claude/plans/PLAN-158"
VERDICT="$GOV/pair-rail-verdict-$TAG.md"
FIELDS="$PLANDIR/architect/ga/verdict-fields-$TAG.txt"
TRANSCRIPT="$PLANDIR/ga-review-transcript.txt"
export GPG_TTY="${GPG_TTY:-$(tty || true)}"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- preflight --------------------------------------------------------------
say "Preflight"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
[ -z "$(git status --porcelain=v1)" ] || { git status --short >&2; die "working tree not clean"; }
git fetch origin main --tags --quiet
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "main not up to date"
git rev-parse -q --verify "refs/tags/$RC_TAG" >/dev/null || die "RC tag $RC_TAG not found — run owner-rc-ceremony.sh first"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null && die "tag $TAG already exists"
gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || die "signing key missing"

say "RC-hold check (24h FULL after RC release-gate green — ADR-103)"
RC_RUN=$(gh run list --workflow release.yml --limit 10 \
  --json databaseId,headBranch,conclusion,updatedAt \
  --jq "[.[] | select(.headBranch == \"$RC_TAG\")][0]")
[ -n "$RC_RUN" ] && [ "$RC_RUN" != "null" ] || die "no release.yml run found for $RC_TAG"
RC_CONC=$(echo "$RC_RUN" | python3 -c 'import json,sys; print(json.load(sys.stdin)["conclusion"])')
[ "$RC_CONC" = "success" ] || die "RC release-gate not green: $RC_CONC"
RC_TS=$(echo "$RC_RUN" | python3 -c 'import json,sys; print(json.load(sys.stdin)["updatedAt"])')
AGE_H=$(python3 - "$RC_TS" <<'PYEOF'
import sys, datetime
ts = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
print(int((datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() // 3600))
PYEOF
)
if [ "$AGE_H" -lt 24 ]; then
  die "RC-hold: only ${AGE_H}h since RC gate green (<24h). Waivable ONLY via rc_hold: entry in $GOV/governance-waivers.yaml (Owner decision — RC-hold FULL was ratified S270)"
fi
echo "    RC gate green ${AGE_H}h ago — hold satisfied"

say "Validate green on HEAD?"
VSTATE=$(gh run list --workflow validate.yml --branch main --limit 1 \
  --json headSha,status,conclusion --jq '.[0] | .headSha + ":" + .status + ":" + .conclusion')
[ "$VSTATE" = "$(git rev-parse HEAD):completed:success" ] || die "Validate on HEAD: $VSTATE"

say "Advisory freshness re-check (a cron red can interpose between RC and GA)"
for wf in chaos.yml otel-smoke.yml perf-profile.yml adapter-live.yml red-team.yml formal-verify.yml; do
  latest=$(gh run list --workflow "$wf" --limit 1 --json conclusion --jq '.[0].conclusion' 2>/dev/null || echo none)
  [ "$latest" = "success" ] || die "$wf latest: $latest — re-dispatch before GA (gh workflow run $wf)"
done
echo "    6/6 advisory workflows green"

say "Codex pin verification"
CODEX_VER="$(codex --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
[ -n "$CODEX_VER" ] || die "codex CLI not found"
BIN_SHA="$(shasum -a 256 "$(command -v codex)" | awk '{print $1}')"
PIN_SHA="$(grep -E '^[0-9a-f]{64}$' "$GOV/codex-cli-binary-sha256.txt" | head -1)"
[ "$BIN_SHA" = "$PIN_SHA" ] || die "codex binary sha != pin"

# ---- fresh pair-rail review (per-tag verdict; V2 truth gate) -----------------
say "Fresh codex review of $RC_TAG..HEAD (per-tag GA verdict)"
mkdir -p "$(dirname "$FIELDS")"
DELTA="$(git diff "$RC_TAG"..HEAD --stat | tail -1)"
{
  echo "PAIR-RAIL GA REVIEW — ceo-orchestration $TAG."
  echo "The RC verdict (16/16 APPROVE, GO) covered v1.0.1..rc. Review ONLY the"
  echo "post-RC delta below for release-blocking defects. If the delta is empty"
  echo "or ceremony-only (verdict/tag artifacts), say so."
  echo "OUTPUT FORMAT (strict):"
  echo "OVERALL: GO|NO-GO — <one-line rationale>"
  echo
  echo "=== COMMITS $RC_TAG..HEAD ==="
  git log --oneline "$RC_TAG"..HEAD || true
  echo
  echo "=== DIFF $RC_TAG..HEAD ==="
  git diff "$RC_TAG"..HEAD
} > /tmp/ga-review-prompt.txt
codex exec --color never --sandbox read-only \
  --output-last-message /tmp/ga-review-verdict.txt - \
  < /tmp/ga-review-prompt.txt > /tmp/ga-review-full.log 2>&1 \
  || die "codex GA review failed (check /tmp/ga-review-full.log)"
{
  echo "=== PAIR-RAIL GA REVIEW TRANSCRIPT — $TAG ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
  echo "--- PROMPT sha256 ---"; shasum -a 256 /tmp/ga-review-prompt.txt
  echo "--- FULL LOG ---"; cat /tmp/ga-review-full.log
} > "$TRANSCRIPT"
GA_LINE="$(grep -E '^OVERALL:' /tmp/ga-review-verdict.txt | head -1)"
echo "    codex: $GA_LINE (delta: ${DELTA:-empty})"
case "$GA_LINE" in
  "OVERALL: GO"*) ;;
  *) die "codex GA verdict is not GO: $GA_LINE — fold findings first (fail-closed to Owner)";;
esac

# ---- envelope ---------------------------------------------------------------
say "Assemble + sign GA verdict envelope"
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

cat > "$FIELDS" <<EOF
verdict: GO
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
findings: []
EOF

rm -f "$FIELDS.asc"
gpg --local-user "$KEY" --armor --detach-sign --output "$FIELDS.asc" "$FIELDS" \
  || die "GPG signing failed (export GPG_TTY=\$(tty); gpgconf --kill gpg-agent)"
SIG_B64="$(base64 < "$FIELDS.asc" | tr -d '\n')"

{
  echo "# Pair-Rail Verdict — $TAG GA"
  echo
  echo '```yaml'
  cat "$FIELDS"
  echo "gpg_signature: base64:$SIG_B64"
  echo '```'
  echo
  echo "## Review record"
  echo
  echo "- RC verdict (v1.1.0-rc.1): 16/16 APPROVE → GO (R1 GO-WITH-CONDITIONS,"
  echo "  P2 SPEC stale-xref folded under SENT-RC-SPEC, R2 APPROVE)."
  echo "- GA delta review ($RC_TAG..$PARENT_SHA): $GA_LINE"
  echo "- Transcript: \`$TRANSCRIPT\` (sha256 in envelope)."
  echo
  echo "## Signature verification recipe"
  echo
  echo 'base64 -d of the value after `base64:` → detached .asc; verify against'
  echo "\`$FIELDS\` (committed alongside). Signer $KEY."
} > "$VERDICT"

say "Commit + signed tag"
git add "$VERDICT" "$FIELDS" "$FIELDS.asc" "$TRANSCRIPT"
git commit -S -m "release(PLAN-158): pair-rail GA verdict GO for $TAG

Fresh per-tag envelope (parent_sha $PARENT_SHA); RC verdict chain +
post-RC delta review committed as evidence. Wave 4 GA ceremony."
git tag -s "$TAG" -m "ceo-orchestration $TAG

Governance + auditability release: npm Trusted Publishing (OIDC),
check_adversary SECRETS-only scan, grok third harness + /council,
gated learning loop, codex harness compat, ecc skill uplift.
No speed claim — six internal experiments found no general speedup;
the value is governance and auditability."
git tag -v "$TAG" || die "tag signature does not verify"
git push origin main
git push origin "$TAG"

say "DONE — now:"
echo "  1. gh run watch \$(gh run list --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
echo "  2. Quando npm-publish.yml pausar: aprove o environment production-npm na UI do GitHub"
echo "  3. Smoke: npx ceo-orchestration@latest --help  (rc=0)"
echo "  4. REVOGUE o NPM_TOKEN granular no npmjs.com + delete o secret NPM_TOKEN do repo"
echo "     + registre em docs/rotation-log.md (playbook Recovery A/B se o publish falhar:"
echo "     .claude/plans/PLAN-158/oidc-failure-playbook.md)"
echo "  5. Feche o plano: status executing→done com completed_at + related_commits"
