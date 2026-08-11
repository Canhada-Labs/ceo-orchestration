#!/bin/bash
# Pair-rail review do diff de CURAS rc.3 (triagem do NO-GO do re-pass GA,
# 10/08). Pipeline identico ao run-ga-repass.sh: prompt + diff -> redactor
# ADR-114 --outgoing -> controles (bytes/hunks/linhas) -> codex exec
# read-only DE DENTRO do worktree curado. 1 parte so (diff ~15KB).
# Uso: bash run-rc3-cure-review.sh <round-N>
set -uo pipefail
ROUND="${1:?uso: run-rc3-cure-review.sh <round-N>}"
REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT" || exit 2
OUT="$REPO_ROOT/.claude/plans/PLAN-166/repass-rc3-cures"
WT="/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/cbec69fd-7f41-4426-81f6-544a454e392a/scratchpad/rc3-wt"
BASE="0cb09c3cc587abdeaed33e0ff13b1c8b3677061d"   # rc.2 == base das curas
[ -d "$WT" ] || { echo "FATAL: worktree das curas ausente em $WT"; exit 2; }
[ "$(git -C "$WT" rev-parse HEAD)" = "$BASE" ] \
  || { echo "FATAL: worktree nao esta detached na rc.2"; exit 2; }

DIFF="$OUT/diff-cures-$ROUND.patch"
git -C "$WT" diff > "$DIFF"
DL=$(wc -l < "$DIFF" | tr -d ' ')
[ "$DL" -ge 100 ] || { echo "FATAL: diff com so $DL linhas"; exit 1; }

RAW="$OUT/payload-cures-$ROUND.raw.txt"
RED="$OUT/payload-cures-$ROUND.redacted.txt"
{
cat <<PROMPT
You are the cross-vendor reviewer on the v1.3.0 GA train of
ceo-orchestration (governance/auditability framework, Python stdlib-only
>=3.9, no speed claims). Be adversarial and concrete.

CONTEXT
- The 24h-hold re-pass over v1.3.0-rc.2 returned NO-GO on both parts
  (2026-08-10). All 8 findings were triaged as REAL. The diff below is
  the CURE SET, authored on a detached worktree of the rc.2 commit; it
  will land as v1.3.0-rc.3 (new 24h ADR-103 hold, then GA).
- The 8 findings being answered:
  P1-a CHANGELOG header said 188 ADRs, disk has 190 (+ no matcher).
  P1-b CHANGELOG v1.3.0 notes omitted adopter-visible upgrade semantics
       (PLAN-166/167/168: ownership single decision, SPEC/v1 forced
       route, .framework-version marker, PROTOCOL pointer generator).
  P1-c npm-publish.yml: after a delete/re-tag recovery, the ORIGINAL
       run could still be approved/re-run pinned to the OLD event SHA
       and irreversibly publish the wrong tree (registry still empty,
       version strings agree). Cure: fail-closed tag-liveness assert
       immediately before npm publish.
  P2-d release-checklist version-site list omitted
       .claude/.framework-version.
  P2-e release-checklist said "~29 steps", release.yml has 31.
  P2-f verify-counts.sh --help header carried stale exacts (188/29/21).
  + timeout bump release-gate 20->35 (S300 lesson: suite runs 19-20 min
    on loaded 2-core runners; attempt-1 of the rc.2 cut hit the axe).
- DEFERRED BY TRIAGE (not cured here, next train; challenge ONLY if you
  believe one must block rc.3): P2 await_release_gate parse_timestamp
  accepts out-of-range time components via calendar.timegm
  normalization; P2 install-npm.sh local stager still copies root
  README.md over npm/README.md (local tooling parity only — the
  PUBLISHED artifact comes from npm-publish.yml, already cured).
- Known-good invariants you must check the diff does NOT break:
  verify-counts.sh census mirror test pins EXACT per-doc match counts;
  CHANGELOG body legitimately carries HISTORICAL counts (184, 178, ...)
  and must NOT join the generic DOCS scan; npm publish flow order is
  await-gate -> environment approval -> registry idempotency check ->
  publish; RC tags stay excluded from publish.

THREAT MODEL (ratified, PLAN-169/S298): Owner-run local ceremony under
a single UID; a concurrent same-UID adversary is OUT OF SCOPE (it could
edit the ceremony scripts themselves). AUTHORIZATION NOTE: the round-4
condition (fresh Owner authorization for the workflow edits) is
SATISFIED by construction - an rc.3 sentinel (RC3-approved.md, anchored
at the rc.2 commit, GPG-signed as pinentry 1 of OWNER-RC3-CUT.sh BEFORE
the pack applies) covers exactly these 7 canonical paths; the ceremony
scripts have their own review rail. Do not re-raise authorization as a
finding; judge the PRODUCT diff. CONSUMER FACTS (reviewed in the
ceremony rail, not in this payload - do NOT speculate about them):
OWNER-GA-CUT.sh undrafts the draft-born stable release as its FINAL
mutation, only after npm view + a pinned Publish-step receipt +
tag-object/main rechecks, and re-drafts on a failed post-undraft
verify; an existing pushed GA tag enters a read-only MONITOR resume
mode (not a hard abort); the GA release.yml observer budget is 60 min
and the rc observer 60 min, both with tag-coherent resume.

WHAT TO REVIEW
1. Does each cure actually cure its finding? A cosmetic cure that
   leaves the failure scenario reachable is a P1.
2. New defects introduced by the cures (shell quoting in workflow YAML,
   regex correctness, test vacuity, census drift, GITHUB_SHA semantics
   for annotated vs lightweight tags).
3. The tag-liveness guard specifically: can an obsolete run still pass
   it? Can a legitimate run be wrongly blocked (false positive)?
4. Anything in the diff that makes the rc.3 cut or the subsequent GA
   promotion NON-idempotent or order-dependent.

OUTPUT FORMAT
Per finding: SEVERITY (P0 blocks rc.3 / P1 fix before rc.3 / P2
follow-up), FILE:LINE, concrete failure scenario, minimal fix. Cite the
diff. End with exactly one line: "VERDICT: GO" or "VERDICT: NO-GO" or
"VERDICT: GO-WITH-CONDITIONS", plus one sentence. A clean round is a
legitimate result - do not manufacture findings.

UNIFIED DIFF (rc.2 -> cure worktree) FOLLOWS.
PROMPT
echo
cat "$DIFF"
} > "$RAW"
RAWB=$(wc -c < "$RAW" | tr -d ' ')
[ "$RAWB" -lt 250000 ] || { echo "FATAL: payload ${RAWB}B >= 250KB"; exit 1; }
python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing < "$RAW" > "$RED" \
  || { echo "FATAL: redactor rc!=0"; exit 1; }
grep -q 'CODEX-OUTPUT-TRUNCATED' "$RED" && { echo "FATAL: payload truncado"; exit 1; }
RH=$(grep -c '^@@' "$RAW" || true); DH=$(grep -c '^@@' "$RED" || true)
[ "$RH" = "$DH" ] || { echo "FATAL: hunks $RH -> $DH"; exit 1; }
RAWL=$(wc -l < "$RAW" | tr -d ' '); REDL=$(wc -l < "$RED" | tr -d ' ')
[ "$RAWL" = "$REDL" ] || { echo "FATAL: linhas $RAWL -> $REDL"; exit 1; }
echo "payload OK (${RAWB}B, $RH hunks) - codex rodando (~10-15 min)..."
( cd "$WT" && codex exec --sandbox read-only --color never \
    --output-last-message "$OUT/verdict-cures-$ROUND.txt" \
    - < "$RED" > "$OUT/transcript-cures-$ROUND.log" 2>&1 )
CRC=$?
VLINE=$(grep -E '^VERDICT:' "$OUT/verdict-cures-$ROUND.txt" 2>/dev/null | tail -1 || true)
[ -n "$VLINE" ] || VLINE="(sem linha VERDICT; rc=$CRC)"
RAW_SHA=$(shasum -a 256 "$RAW" | awk '{print $1}')
{
  echo "- $ROUND: $VLINE [codex rc=$CRC]"
  echo "  - payload raw NAO commitado; pin sha256: $RAW_SHA"
  echo "  - base do diff: $BASE (rc.2); diff sha256: $(shasum -a 256 "$DIFF" | awk '{print $1}')"
} >> "$OUT/PROVENANCE-cures.md"
mkdir -p "$HOME/.rc2-backup"; mv "$RAW" "$HOME/.rc2-backup/payload-cures-$ROUND.raw.txt"
echo "$ROUND: $VLINE [rc=$CRC]"
if [ "$CRC" -ne 0 ]; then exit 1; fi
case "$VLINE" in
  "VERDICT: GO") exit 0 ;;
  *) exit 1 ;;
esac
