#!/bin/bash
# Round de review dos SCRIPTS da cerimonia rc.3 (precedente S300: o rail
# achou P1s reais nos scripts de corte, nao so no produto). Artefatos com
# o MESMO naming roundN do rail de curas (entram no mesmo manifesto).
# Uso: bash run-rc3-scripts-review.sh <round-N>
set -uo pipefail
ROUND="${1:?uso: run-rc3-scripts-review.sh <round-N>}"
REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT" || exit 2
OUT="$REPO_ROOT/.claude/plans/PLAN-166/repass-rc3-scripts"
WT="/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/cbec69fd-7f41-4426-81f6-544a454e392a/scratchpad/rc3-wt"

# Conjunto FECHADO dos arquivos de cerimonia sob review.
FILES_LIST="$(cat <<'EOF'
.claude/plans/PLAN-166/OWNER-RC3-CUT.sh
.claude/plans/PLAN-166/RC3-approved-draft.md
.claude/plans/PLAN-166/OWNER-GA-CUT.sh
.claude/plans/PLAN-166/repass-ga/run-ga-repass.sh
.claude/plans/PLAN-166/verdict-fields-v1.3.0-rc.3.TEMPLATE.md
.claude/plans/PLAN-166/pair-rail-verdict-v1.3.0-rc.3.TEMPLATE.md
.claude/plans/PLAN-166/verdict-fields-v1.3.0.TEMPLATE.md
.claude/plans/PLAN-166/pair-rail-verdict-v1.3.0.TEMPLATE.md
EOF
)"

DIFF="$OUT/diff-cures-$ROUND.patch"
: > "$DIFF"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || { echo "FATAL: arquivo de cerimonia ausente: $f"; exit 1; }
  # --no-index contra /dev/null gera hunks (@@) para os controles de
  # paridade raw/redacted; rc do git diff --no-index e 1 por design.
  git diff --no-index -- /dev/null "$f" >> "$DIFF" || true
done <<FL
$FILES_LIST
FL
DL=$(wc -l < "$DIFF" | tr -d ' ')
[ "$DL" -ge 100 ] || { echo "FATAL: payload de scripts com so $DL linhas"; exit 1; }

RAW="$OUT/payload-cures-$ROUND.raw.txt"
RED="$OUT/payload-cures-$ROUND.redacted.txt"
{
cat <<'PROMPT'
You are the cross-vendor reviewer on the v1.3.0 GA train of
ceo-orchestration. This round reviews the CEREMONY SCRIPTS for the
v1.3.0-rc.3 cut, not the product cures (those passed their own rounds;
do not re-litigate them). Be adversarial and concrete. S300 precedent:
prior script-review rounds found real P1s (stale-provenance reuse,
non-main HEAD, look-alike evidence paths, lowercase confirm aborting).


THREAT MODEL (ratified, PLAN-169/S298 - do not relitigate): these are
Owner-run LOCAL scripts under a single UID. A concurrent same-UID
adversary is OUT OF SCOPE by ratified decision - such an adversary can
edit the scripts themselves, so no local check can close that class
(the same-UID oracle limitation). Report ONLY defects reachable via:
operator mistakes, stale/partial state, interruptions and resumes,
races with REMOTE systems (GitHub/npm/CI), command failure semantics,
or wrong-selection of remote receipts. Findings whose only reachable
path requires a live local adversary mutating files mid-ceremony will
be triaged as out-of-scope.

CONTEXT
- The rc.2 hold re-pass returned NO-GO (8 real findings). Cures are
  staged in .claude/plans/PLAN-166/staged-rc3/ under MANIFEST.sha256
  (pack content) + BASELINE.sha256 (live pre-cure state). The Owner will
  run OWNER-RC3-CUT.sh in the morning: sign sentinel (pinentry 1), apply
  pack, local gates, commit 1 (closed allowlist), verdict-fields sign
  (pinentry 2), verdict commit 2, local delta guard, push, CI wait
  (job-level validate assert), preflight --rc 3, tag sign (pinentry 3),
  push tag after literal SIM, release.yml wait, await-release-gate
  positive control, pre-release verify. Then the ADR-103 24h hold
  restarts and OWNER-GA-CUT.sh (already re-pointed to rc.3) promotes.
- The delta guard (_release_tag_guard.py) enforces: parent_sha ancestry,
  closed delta allowlist (verdict + verdict-fields at canonical paths +
  manifest-dir files with set equality vs MANIFEST-cures.sha256, sha256
  pinned in the signed verdict), no globs, vacuity check.
- Known environment facts: macOS zsh Owner shell but scripts run under
  bash; gpg pinentry needs GPG_TTY; gh CLI authenticated; origin/main ==
  0cb09c3 (rc.2 commit) — the required EXPECTED_HEAD.

WHAT TO REVIEW (the payload = full text of each ceremony file)
1. FAIL-CLOSED completeness: any path where a failed check still
   proceeds, or where rerun-after-partial-failure corrupts state
   (commits, tags, worktree, staged pack, evidence dirs)?
2. Allowlist closure of commit 1: does any file class escape or block?
   The tree at run time contains exactly: applied cures (7 canonical
   paths), staged-rc3/, repass-rc3-cures/, repass-ga-rc2-NOGO/,
   edited OWNER-GA-CUT.sh + run-ga-repass.sh + templates + draft +
   OWNER-MORNING-RC3.md + PLAN-169 staged-w3 mirror + W3 draft.
3. Template/guard coherence: will the generated verdict-fields pass the
   delta guard and the server-side step-15 validator (inputs_hash reused
   from rc.2 — no trust-chain surface changed; delta_manifest basenames;
   allowlist set equality)?
4. GA path coherence: OWNER-GA-CUT.sh now points at rc.3; run-ga-repass
   regenerates evidence into repass-ga/ (old NO-GO archived in
   repass-ga-rc2-NOGO/). Any stale rc.2 residue that would abort or,
   worse, falsely pass the GA?
5. Idempotency/resume: G0 refuses reruns after commit 1 by design; is
   every pre-commit-1 step safely re-runnable?

OUTPUT FORMAT
Per finding: SEVERITY (P0 blocks the cut / P1 fix before the cut / P2
follow-up), FILE:LINE, concrete failure scenario, minimal fix. End with
exactly one line: "VERDICT: GO" or "VERDICT: NO-GO" or
"VERDICT: GO-WITH-CONDITIONS", plus one sentence. A clean round is a
legitimate result - do not manufacture findings.

CEREMONY FILES (each as a /dev/null diff) FOLLOW.
PROMPT
echo
cat "$DIFF"
} > "$RAW"
RAWB=$(wc -c < "$RAW" | tr -d ' ')
[ "$RAWB" -lt 250000 ] || { echo "FATAL: payload ${RAWB}B >= 250KB"; exit 1; }
python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing < "$RAW" > "$RED" \
  || { echo "FATAL: redactor rc!=0"; exit 1; }
# Ancorado na LINHA exata que o redactor emite (linha 85 do
# codex_egress_redact.py) — um grep solto casaria com o proprio texto
# do run-ga-repass.sh dentro do payload (classe waiter-casa-a-si-mesmo).
grep -q '^\[CODEX-OUTPUT-TRUNCATED-AT-256KB-PER-_MAX_REDACT_INPUT_BYTES\]$' "$RED" \
  && { echo "FATAL: payload truncado"; exit 1; }
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
  echo "- $ROUND (SCRIPTS da cerimonia): $VLINE [codex rc=$CRC]"
  echo "  - payload raw NAO commitado; pin sha256: $RAW_SHA"
  echo "  - alvo: OWNER-RC3-CUT/GA-CUT/run-ga-repass/templates/draft (full-file diffs vs /dev/null)"
  echo "  - CEREMONY-MANIFEST-SHA256-AT-REVIEW $ROUND: $(shasum -a 256 "$REPO_ROOT/.claude/plans/PLAN-166/repass-rc3-cures/CEREMONY-MANIFEST.sha256" | awk '{print $1}')"
} >> "$OUT/PROVENANCE-scripts.md"
mkdir -p "$HOME/.rc2-backup"; mv "$RAW" "$HOME/.rc2-backup/payload-cures-$ROUND.raw.txt"
echo "$ROUND: $VLINE [rc=$CRC]"
if [ "$CRC" -ne 0 ]; then exit 1; fi
case "$VLINE" in
  "VERDICT: GO") exit 0 ;;
  *) exit 1 ;;
esac
