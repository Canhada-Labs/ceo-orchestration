#!/bin/bash
# Build the ADR-103 hold re-pass payload for v1.3.0-rc.1.
#
# ONE pipeline: prompt + diff -> ADR-114 egress redactor -> payload file.
# Every control here exists because a silently-truncated or structurally
# flattened payload would produce a PLAUSIBLE review of the wrong thing.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

OUT_DIR="${1:?usage: $0 <out_dir>}"
mkdir -p "$OUT_DIR"

RAW="$OUT_DIR/payload.raw.txt"
RED="$OUT_DIR/payload.redacted.txt"
DIFF="$OUT_DIR/release-mechanics.diff"
MANIFEST="$OUT_DIR/paths.manifest.txt"

BASE_TAG="v1.2.0"
RC_TAG="v1.3.0-rc.1"

# --- Scope: release mechanics, same path set the 4-round verdict used ------
cat > "$MANIFEST" <<'PATHS'
VERSION
npm/README.md
npm/package.json
pyproject.toml
CHANGELOG.md
INSTALL.md
docs/ARCHITECTURE.md
README.md
README.pt-BR.md
SECURITY.md
VERSIONING.md
SBOM.md
.github/workflows/release.yml
.github/workflows/npm-publish.yml
.github/release-checklist.md
.claude/scripts/local/verify-counts.sh
.claude/scripts/local/release-v1-2-0.sh
scripts/upgrade.sh
.claude-plugin/marketplace.json
.claude-plugin/plugin.json
PATHS

# Fail-closed: every declared path must exist at the RC tag. A path that
# silently drops out of the pathspec yields a smaller, plausible diff.
while IFS= read -r p; do
  [ -z "$p" ] && continue
  git cat-file -e "$RC_TAG:$p" 2>/dev/null \
    || { echo "FATAL: declared scope path missing at $RC_TAG: $p" >&2; exit 1; }
done < "$MANIFEST"

# shellcheck disable=SC2046
git diff "$BASE_TAG".."$RC_TAG" -- $(tr '\n' ' ' < "$MANIFEST") > "$DIFF"

DIFF_LINES=$(wc -l < "$DIFF" | tr -d ' ')
if [ "$DIFF_LINES" -lt 100 ]; then
  echo "FATAL: diff only $DIFF_LINES lines — scope collapsed" >&2; exit 1
fi

# --- Prompt -----------------------------------------------------------------
{
cat <<PROMPT
You are the cross-vendor reviewer on a release hold. Be adversarial and
concrete. Your output is advisory evidence, not an authorization.

CONTEXT
- Repo: ceo-orchestration, a governance/auditability framework installed
  into other repos. Python stdlib-only, >=3.9. No speed claims anywhere.
- $RC_TAG is CUT, signed, CI-green, and published as a GitHub pre-release.
- A mandatory 24h hold (ADR-103) is running before GA. This re-pass is the
  hold's review. Nothing has been pushed to npm.
- A 4-round pair-rail already ran BEFORE the cut against the same scope:
  18 findings, 17 real and fixed, 1 refuted. Those rounds ran under time
  pressure at the end of a long session.

ALREADY CLOSED — do NOT re-report these as new. DO report if you find the
fix itself incorrect, incomplete, or that it introduced a new defect:
  r1-r3: signed tag annotation still describing v1.2.0; 'bump --dry-run'
    leaving debris (restore list shorter than write list); three stale
    current-version declarations (SBOM/SECURITY/VERSIONING) that were also
    unwatched by any check; a support-window guard watching only
    'Current MINOR'.
  r4-P1: 'bump' made idempotent (a no-op bump is success).
  r4-P2: release checklist no longer claims the driver covers every site.
  Self-caught after r4: post-bump hint used \${STABLE:+...}, which expands
    for STABLE=0 and wrongly told the operator to cut the STABLE tag during
    an RC run.
  REFUTED (do not re-raise without NEW evidence): that the sentinel-unlock
    provenance requirement forces a SemVer MAJOR. This repo's published
    VERSIONING.md scopes MAJOR to schema-consumer breakage; a new trust
    boundary is the literal MINOR case and is called out in CHANGELOG
    under Security with the adopter action.

WHAT THIS RE-PASS IS FOR
The pre-cut rounds asked "is the release machinery correct?". Ask the
questions a 24h pause is supposed to surface:
  1. GA EXECUTABILITY. The remaining path is: bump --stable, then
     tag --stable, then push (push triggers npm publish via OIDC). Read
     the driver as it now stands. Does that path actually run to
     completion on a tree already at the RC? Is any step non-idempotent,
     order-dependent, or dependent on state the RC cut consumed?
  2. IRREVERSIBILITY. Pushing the GA tag publishes to npm and cannot be
     undone. What lands wrong and is unrecoverable? Version strings that
     disagree across published surfaces (npm/package.json vs VERSION vs
     pyproject vs plugin manifests) are the highest-value class here.
  3. ADOPTER BLAST RADIUS. Someone on v1.2.0 runs the documented upgrade.
     Read scripts/upgrade.sh and INSTALL.md against what actually changed.
     Does the upgrade path handle the new trust-boundary requirement, or
     does it silently leave an adopter in a broken/locked state?
  4. HONESTY OF CLAIMS. Every count, capability, and guarantee in the
     changed docs must match what the code does. Flag any claim that is
     stale, unfalsifiable, or that describes a gate which cannot fail.
     A gate that structurally cannot fail is a finding.
  5. What a tired reviewer at round 4 would most plausibly have missed.

OUTPUT FORMAT
For each finding: SEVERITY (P0 blocks GA / P1 fix before GA / P2 follow-up),
FILE:LINE, the concrete failure scenario (inputs -> wrong outcome), and the
minimal fix. Cite evidence from the diff; do not speculate.
End with exactly one line: "VERDICT: GO" or "VERDICT: NO-GO" or
"VERDICT: GO-WITH-CONDITIONS", followed by a one-sentence justification.
If you find nothing material, say so plainly and return GO — a clean round
is a legitimate result, but do not manufacture findings to look thorough.

UNIFIED DIFF ($BASE_TAG..$RC_TAG, release-mechanics scope) FOLLOWS.
PROMPT
echo
cat "$DIFF"
} > "$RAW"

# --- ADR-114 egress boundary: the canonical invocation, from repo root ------
set +e
python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing < "$RAW" > "$RED"
RC=$?
set -e
[ "$RC" -eq 0 ] || { echo "FATAL: egress redactor exited $RC (fail-closed)" >&2; exit 1; }

# --- Controls: the payload must be whole and still be a diff ---------------
[ -s "$RED" ] || { echo "FATAL: redacted payload empty" >&2; exit 1; }

if grep -q 'CODEX-OUTPUT-TRUNCATED-AT-256KB' "$RED"; then
  echo "FATAL: payload hit the 256KB redactor cap and was truncated" >&2; exit 1
fi

RAW_LINES=$(wc -l < "$RAW" | tr -d ' ')
RED_LINES=$(wc -l < "$RED" | tr -d ' ')
if [ "$RAW_LINES" -ne "$RED_LINES" ]; then
  echo "FATAL: line count changed $RAW_LINES -> $RED_LINES (structure altered)" >&2
  exit 1
fi

# The diff must still read as a diff on the far side of redaction.
RED_HUNKS=$(grep -c '^@@ ' "$RED" || true)
RAW_HUNKS=$(grep -c '^@@ ' "$RAW" || true)
if [ "$RED_HUNKS" -ne "$RAW_HUNKS" ] || [ "$RED_HUNKS" -lt 10 ]; then
  echo "FATAL: hunk headers $RAW_HUNKS -> $RED_HUNKS (diff structure lost)" >&2
  exit 1
fi

INPUTS_HASH=$(shasum -a 256 "$RED" | awk '{print $1}')
MANIFEST_SHA=$(shasum -a 256 "$MANIFEST" | awk '{print $1}')

cat <<SUMMARY
payload built OK
  raw bytes        : $(wc -c < "$RAW" | tr -d ' ')
  redacted bytes   : $(wc -c < "$RED" | tr -d ' ')
  lines            : $RED_LINES (unchanged through redactor)
  hunk headers     : $RED_HUNKS (unchanged through redactor)
  diff lines       : $DIFF_LINES
  inputs_hash      : $INPUTS_HASH
  paths_manifest   : $MANIFEST_SHA
  payload          : $RED
SUMMARY
