#!/bin/bash
# Re-pass do hold ADR-103 para o GA v1.3.0 (PLAN-166 W2 / W6.1) - 2 PARTES.
# Pipeline identico ao r1/r2: prompt + diff -> redactor ADR-114 ->
# controles -> codex exec read-only de worktree detached DA TAG rc.2.
# O diff v1.2.0..rc.2 do escopo release-mechanics tem ~282KB > cap de
# 250KB do redactor => particao coerente em 2 payloads (medida S300):
#   g1: superficies de versao/docs/config + upgrade.sh (blast radius
#       do adotante) ~111KB
#   g2: maquinaria executavel do release (workflows + driver + guard +
#       bump-sites + await-gate + validador step-15) ~176KB
# Saida por parte: payload-ga-N.redacted.txt, diff-ga-N.patch,
# paths-ga-N.manifest.txt, verdict-ga-N.txt, transcript-ga-N.log;
# agregado em PROVENANCE-ga.md + MANIFEST-ga.sha256 (BASENAMES).
# O GA so segue com VERDICT: GO (ou GO-WITH-CONDITIONS) nas DUAS partes.
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT" || exit 2
OUT="$REPO_ROOT/.claude/plans/PLAN-166/repass-ga"
BASE_TAG="v1.2.0"
RC_TAG="v1.3.0-rc.2"
git rev-parse -q --verify "refs/tags/$RC_TAG" >/dev/null 2>&1 \
  || { echo "FATAL: tag $RC_TAG nao existe - corte a rc.2 primeiro"; exit 2; }

WT="$(mktemp -d "${TMPDIR:-/tmp}/repass-ga.XXXXXX")/wt"
git worktree add --detach "$WT" "$RC_TAG" >/dev/null || exit 2
trap 'git worktree remove --force "$WT" >/dev/null 2>&1 || true' EXIT
[ -z "$(git -C "$WT" status --porcelain)" ] || { echo "FATAL: worktree sujo"; exit 2; }

part_paths() {
  case "$1" in
    1) cat <<'P1'
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
.github/release-checklist.md
.claude-plugin/marketplace.json
.claude-plugin/plugin.json
scripts/upgrade.sh
P1
;;
    2) cat <<'P2'
.github/workflows/release.yml
.github/workflows/npm-publish.yml
.claude/scripts/local/verify-counts.sh
.claude/scripts/local/release.sh
.claude/scripts/local/_release_tag_guard.py
.claude/scripts/local/_release_bump_sites.py
.claude/scripts/await_release_gate.py
.github/scripts/validate-pair-rail-verdict.py
P2
;;
  esac
}
part_label() {
  case "$1" in
    1) echo "version/docs/config surfaces + adopter upgrade path" ;;
    2) echo "executable release machinery (workflows, driver, tag guard, bump sites, npm await-gate, step-15 validator)" ;;
  esac
}

prompt_header() {
cat <<PROMPT
You are the cross-vendor reviewer on the 24h release hold (ADR-103) for
the GA promotion of $RC_TAG to v1.3.0. Be adversarial and concrete.
Your output is advisory evidence, not an authorization. The scope is
SPLIT in 2 payloads (redactor cap); this is payload $1/2: $2.
Each part is judged independently; GA needs GO on both.

CONTEXT
- Repo: ceo-orchestration, a governance/auditability framework. Python
  stdlib-only, >=3.9. No speed claims anywhere.
- $RC_TAG is CUT, signed, CI-green, published as a GitHub pre-release,
  under a signed pair-rail verdict (GO-WITH-CONDITIONS).
- Review history you must NOT re-litigate: 4 pre-rc.1 rounds (18
  findings, 17 fixed 1 refuted) + 4 multi-part rounds rc.1->rc.2
  (all real findings cured in fix-forwards; final candidate green).
- FOUR NAMED PRODUCT EXCEPTIONS ride this GA by signed decision
  (V1/V2/V4/V5 - upgrade.sh observer w/o baseline-invalid guard; false
  --pin NOTE; rejected-symlink hash fallthrough; FMS_LINK_PATHS unset
  allow-all on install). Cures are STAGED in a post-GA ceremony pack.
  Do NOT report these as new; DO report if any is WORSE than described
  or reachable on the mainline install/upgrade path (they were assessed
  as non-mainline).
- OWN-0016 is a known gated defect (ADR-190 s2.6, expected nightly RED).

WHAT THIS HOLD RE-PASS IS FOR
1. GA EXECUTABILITY: remaining path is bump --stable (expected no-op),
   tag --stable, push (push triggers npm publish via OIDC). Anything
   non-idempotent or order-dependent?
2. IRREVERSIBILITY: what lands wrong on npm and cannot be undone?
   Version-string disagreement across published surfaces is the
   highest-value class.
3. ADOPTER BLAST RADIUS: v1.2.0 adopter runs the documented upgrade
   against v1.3.0 - broken/locked states?
4. HONESTY OF CLAIMS: every count/guarantee in the changed docs must
   match the code at the tag. A gate that cannot fail is a finding.
5. What a reviewer would most plausibly have missed across 8 rounds.

OUTPUT FORMAT
Per finding: SEVERITY (P0 blocks GA / P1 fix before GA / P2 follow-up),
FILE:LINE, concrete failure scenario, minimal fix. Cite the diff.
End with exactly one line: "VERDICT: GO" or "VERDICT: NO-GO" or
"VERDICT: GO-WITH-CONDITIONS", plus one sentence. A clean round is a
legitimate result - do not manufacture findings.

UNIFIED DIFF ($BASE_TAG..$RC_TAG, part $1/2) FOLLOWS.
PROMPT
}

OVERALL=0
{
  echo "# Proveniencia do re-pass GA (hold ADR-103) - v1.3.0 - 2 partes"
  echo "- Base: $BASE_TAG .. Tag: $RC_TAG ($(git rev-parse "$RC_TAG^{commit}"))"
  echo "- Worktree detached da TAG: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only"
  echo "- Data: $(date -u +%Y-%m-%dT%H:%MZ)"
} > "$OUT/PROVENANCE-ga.md"

for P in 1 2; do
  LABEL="$(part_label "$P")"
  MAN="$OUT/paths-ga-$P.manifest.txt"
  part_paths "$P" > "$MAN"
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    git cat-file -e "$RC_TAG:$p" 2>/dev/null \
      || { echo "FATAL: caminho do escopo ausente na tag: $p" >&2; exit 1; }
  done < "$MAN"
  DIFF="$OUT/diff-ga-$P.patch"
  # shellcheck disable=SC2046
  git diff "$BASE_TAG".."$RC_TAG" -- $(tr '\n' ' ' < "$MAN") > "$DIFF"
  DL=$(wc -l < "$DIFF" | tr -d ' ')
  [ "$DL" -ge 50 ] || { echo "FATAL: parte $P com so $DL linhas de diff"; exit 1; }
  RAW="$OUT/payload-ga-$P.raw.txt"; RED="$OUT/payload-ga-$P.redacted.txt"
  { prompt_header "$P" "$LABEL"; echo; cat "$DIFF"; } > "$RAW"
  RAWB=$(wc -c < "$RAW" | tr -d ' ')
  [ "$RAWB" -lt 250000 ] || { echo "FATAL: parte $P ${RAWB}B >= 250KB"; exit 1; }
  python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing < "$RAW" > "$RED" \
    || { echo "FATAL: redactor rc!=0 na parte $P"; exit 1; }
  grep -q 'CODEX-OUTPUT-TRUNCATED' "$RED" && { echo "FATAL: parte $P truncada"; exit 1; }
  RH=$(grep -c '^@@' "$RAW" || true); DH=$(grep -c '^@@' "$RED" || true)
  [ "$RH" = "$DH" ] || { echo "FATAL: parte $P hunks $RH -> $DH"; exit 1; }
  RAWL=$(wc -l < "$RAW" | tr -d ' '); REDL=$(wc -l < "$RED" | tr -d ' ')
  [ "$RAWL" = "$REDL" ] || { echo "FATAL: parte $P linhas $RAWL -> $REDL"; exit 1; }
  echo "parte $P OK (${RAWB}B, $RH hunks) - codex rodando (~10-15 min)..."
  ( cd "$WT" && codex exec --sandbox read-only --color never \
      --output-last-message "$OUT/verdict-ga-$P.txt" \
      - < "$RED" > "$OUT/transcript-ga-$P.log" 2>&1 )
  CRC=$?
  VLINE=$(grep -E '^VERDICT:' "$OUT/verdict-ga-$P.txt" 2>/dev/null | tail -1 || true)
  [ -n "$VLINE" ] || VLINE="(sem linha VERDICT - inspecionar transcript; rc=$CRC)"
  RAW_SHA=$(shasum -a 256 "$RAW" | awk '{print $1}')
  {
    echo "- parte $P ($LABEL): $VLINE [codex rc=$CRC]"
    echo "  - payload-ga-$P.raw.txt NAO commitado; pin sha256: $RAW_SHA"
  } >> "$OUT/PROVENANCE-ga.md"
  mkdir -p "$HOME/.rc2-backup"; mv "$RAW" "$HOME/.rc2-backup/payload-ga-$P.raw.txt"
  echo "parte $P: $VLINE [rc=$CRC]"
  # Pair-rail S300 r3 P1-3: um VERDICT escrito seguido de crash/timeout
  # do codex (rc!=0) e evidencia INCOMPLETA, nao autorizacao — o rc da
  # execucao E a linha exata contam.
  if [ "$CRC" -ne 0 ]; then
    OVERALL=1
  else
    case "$VLINE" in
      "VERDICT: GO"|"VERDICT: GO-WITH-CONDITIONS"*) : ;;
      *) OVERALL=1 ;;
    esac
  fi
done

( cd "$OUT" && shasum -a 256 \
    payload-ga-1.redacted.txt payload-ga-2.redacted.txt \
    diff-ga-1.patch diff-ga-2.patch \
    paths-ga-1.manifest.txt paths-ga-2.manifest.txt \
    verdict-ga-1.txt verdict-ga-2.txt \
    transcript-ga-1.log transcript-ga-2.log \
    > MANIFEST-ga.sha256 )
echo "RUNNER-OVERALL: rc=$OVERALL" >> "$OUT/PROVENANCE-ga.md"
echo "OVERALL: $( [ "$OVERALL" -eq 0 ] && echo GO-nas-2-partes || echo 'PARTE SEM GO - triagem' )"
exit "$OVERALL"
