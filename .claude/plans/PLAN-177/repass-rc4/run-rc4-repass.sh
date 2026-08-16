#!/bin/bash
# Re-pass do CANDIDATO rc.4 (PLAN-177 W2.2) - 2 PARTES.
# Revisa as CURAS dos 4 P1 do re-pass GA (NO-GO 12/08): diff
# rc.3..CANDIDATE, pipeline identico ao run-ga-repass.sh do 166
# (prompt+diff -> redactor ADR-114 -> controles -> codex read-only
# de worktree DETACHED no SHA candidato - doutrina r17: a tag rc.4
# ainda nao existe, exigir worktree da tag seria circular).
#   p1: os dois validadores do P1-4 + regressao (test_release_bump_sites
#       + test_release_workflow_asserts)
#   p2: entrega .gitignore (gerador+install+upgrade) + honestidade npm
#       + parity + e2e + workflows tournament/smoke + ceo-boot triagem-2
# Saida por parte: payload-rc4-N.redacted.txt, diff-rc4-N.patch,
# paths-rc4-N.manifest.txt, verdict-rc4-N.txt, transcript-rc4-N.log;
# agregado em PROVENANCE-rc4.md + MANIFEST-rc4.sha256.
# A tag rc.4 so e cortada com VERDICT GO/GO-WITH-CONDITIONS nas DUAS.
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT" || exit 2
OUT="$REPO_ROOT/.claude/plans/PLAN-177/repass-rc4"
BASE_TAG="v1.3.0-rc.3"
BASE_TAG_OBJ="ef90e9201790ed29a1b3f6f91ab7d357e65c5db0"
BASE_TAG_COMMIT="7362cfca026c1fd6b6cd780ff56329405ac91a25"
CANDIDATE_SHA="a604e6b572a8b058bc0426780ccc372d66e65351"
git tag -v "$BASE_TAG" >/dev/null 2>&1 \
  || { echo "FATAL: assinatura da $BASE_TAG nao verifica"; exit 2; }
[ "$(git rev-parse "$BASE_TAG")" = "$BASE_TAG_OBJ" ] \
  || { echo "FATAL: objeto local da $BASE_TAG != pin"; exit 2; }
[ "$(git rev-parse "$BASE_TAG^{commit}")" = "$BASE_TAG_COMMIT" ] \
  || { echo "FATAL: commit da $BASE_TAG != pin"; exit 2; }
_bt_rls="$(git ls-remote origin "refs/tags/$BASE_TAG" "refs/tags/$BASE_TAG^{}")" \
  || { echo "FATAL: ls-remote da $BASE_TAG falhou"; exit 2; }
_bt_plain="$(printf '%s\n' "$_bt_rls" | awk -v r="refs/tags/$BASE_TAG" '$2==r{print $1}')"
_bt_peel="$(printf '%s\n' "$_bt_rls" | awk -v r="refs/tags/$BASE_TAG^{}" '$2==r{print $1}')"
[ "$_bt_plain" = "$BASE_TAG_OBJ" ] || { echo "FATAL: $BASE_TAG remota != pin"; exit 2; }
[ -z "$_bt_peel" ] || [ "$_bt_peel" = "$BASE_TAG_COMMIT" ] \
  || { echo "FATAL: peel remoto da $BASE_TAG != pin"; exit 2; }
git merge-base --is-ancestor "$BASE_TAG_COMMIT" "$CANDIDATE_SHA" \
  || { echo "FATAL: base nao e ancestral do candidato"; exit 2; }
_rm_main="$(git ls-remote origin refs/heads/main | awk '{print $1}')" \
  || { echo "FATAL: ls-remote main falhou"; exit 2; }
[ "$_rm_main" = "$CANDIDATE_SHA" ] \
  || { echo "FATAL: origin/main ($_rm_main) != candidato pinado - main avancou, re-pinar conscientemente"; exit 2; }

WT="$(mktemp -d "${TMPDIR:-/tmp}/repass-rc4.XXXXXX")/wt"
git worktree add --detach "$WT" "$CANDIDATE_SHA" >/dev/null || exit 2
_cleanup() {
  git worktree remove --force "$WT" >/dev/null 2>&1 || true
  mkdir -p "$HOME/.rc2-backup"
  for _raw in "$OUT"/payload-rc4-*.raw.txt; do
    [ -e "$_raw" ] || continue
    mv "$_raw" "$HOME/.rc2-backup/quarantine-$(date +%s)-$(basename "$_raw")" \
      && echo "quarentena: $(basename "$_raw") -> ~/.rc2-backup/" >&2
  done
}
trap _cleanup EXIT
_wt_st="$(git -C "$WT" status --porcelain)" \
  || { echo "FATAL: git status do worktree falhou"; exit 2; }
[ -z "$_wt_st" ] || { echo "FATAL: worktree sujo"; exit 2; }

part_paths() {
  case "$1" in
    1) cat <<'P1'
.github/scripts/validate-pair-rail-verdict.py
.claude/scripts/local/_release_tag_guard.py
.claude/scripts/tests/test_release_bump_sites.py
.claude/scripts/tests/test_release_workflow_asserts.py
P1
;;
    2) cat <<'P2'
scripts/_framework_manifest_set.sh
scripts/install.sh
scripts/upgrade.sh
scripts/install-npm.sh
scripts/tests/_parity_classify.py
scripts/tests/test-night-mode-ignore-effect.sh
.github/workflows/tournament.yml
.github/workflows/smoke-install.yml
npm/INTEGRITY.md
npm/SHA256SUMS.txt
SUPPORT.md
README.md
.github/release-checklist.md
.claude/scripts/ceo-boot.py
.claude/scripts/tests/test_ceo_boot.py
.claude/scripts/tests/test_tournament_projection_workdir.py
CLAUDE.md
P2
;;
  esac
}
part_label() {
  case "$1" in
    1) echo "P1-4 decision gate in both validators + regression suites" ;;
    2) echo "P1-1 gitignore delivery via shared generator + P1-2/P1-3 npm honesty + T-1/T-2 + workflow wiring" ;;
  esac
}

prompt_header() {
cat <<PROMPT
You are the cross-vendor reviewer for the rc.4 CANDIDATE of v1.3.0
(repo ceo-orchestration). Be adversarial and concrete. Your output is
advisory evidence, not an authorization. Scope is SPLIT in 2 payloads;
this is payload $1/2: $2. Each part judged independently; the rc.4 tag
is only cut with GO (or GO-WITH-CONDITIONS) on both.

CONTEXT
- Your OWN GA re-pass over rc.3 (2026-08-12) returned NO-GO with 4 P1s:
  (a) the server validator never reads the verdict decision field, a
  NO-GO still authorizes the generic release path; (b) upgrade.sh never
  delivers the night-mode .gitignore entries and the parity gate
  allowlists the defect; (c) npm/INTEGRITY.md says "currently 1.0.1";
  (d) a per-tarball SHA-256 manifest is promised as enforced today but
  no workflow generates it. THIS DIFF IS THE CURE SET for all four,
  plus two S303 triage patches (tournament working-directory;
  ceo-boot harness-probe filter).
- Chosen routes you should judge on their merits but not re-litigate
  as scope: (d) was cured via route (ii) HONESTY (promise moved to
  not-yet-automated, impossible consumer recipe REMOVED, sibling false
  promises cured, negative vocabulary gate added); implementing real
  tarball checksums is a named v1.4.0 item. The 4 NAMED PRODUCT
  EXCEPTIONS (V1/V2/V4/V5) still ride by signed decision - report only
  if one got WORSE.
- The cure set went through: plan debate (3 critics, 9 consensus
  adjustments), 2 codex plan reviews (findings applied), and each cure
  carries a positive control (a test proven to FAIL on the exact
  defect scenario). Node/python: stdlib-only, >=3.9.

WHAT TO VERIFY
1. Are the 4 cures CORRECT and COMPLETE at this SHA? A partial cure
   here repeats the exact history that produced this re-pass.
2. Does any cure introduce a NEW defect (fail-open, bypass, parity
   break, packaging leak, workflow break)?
3. Are the positive controls REAL (would they actually fail on the
   defect) or decorative?
4. Adopter blast radius of the delivery changes (install/upgrade,
   ceremonies maintainer AND user, pre-v1.2.0 adopters).
5. What a reviewer would most plausibly miss.

OUTPUT FORMAT
Per finding: SEVERITY (P0 blocks rc.4 / P1 fix before rc.4 / P2
follow-up), FILE:LINE, concrete failure scenario, minimal fix. Cite
the diff. End with exactly one line: "VERDICT: GO" or "VERDICT: NO-GO"
or "VERDICT: GO-WITH-CONDITIONS", plus one sentence. A clean round is
a legitimate result - do not manufacture findings.

UNIFIED DIFF ($BASE_TAG..candidate-$CANDIDATE_SHA, part $1/2) FOLLOWS.
PROMPT
}

if [ -f "$OUT/MANIFEST-rc4.sha256" ] \
   && ( cd "$OUT" && shasum -a 256 -c MANIFEST-rc4.sha256 --status ) 2>/dev/null \
   && grep -qE "^RUNNER-OVERALL: rc=" "$OUT/PROVENANCE-rc4.md" 2>/dev/null; then
  echo "FATAL: evidencia COMPLETA de tentativa anterior presente"
  echo "  NO-GO: triagem + mv para repass-rc4-<data>-NOGO/ antes de re-rodar."
  exit 1
fi
for _o in PROVENANCE-rc4.md MANIFEST-rc4.sha256 MANIFEST-rc4.sha256.tmp \
  payload-rc4-1.redacted.txt payload-rc4-2.redacted.txt \
  payload-rc4-1.raw.txt payload-rc4-2.raw.txt \
  diff-rc4-1.patch diff-rc4-2.patch \
  paths-rc4-1.manifest.txt paths-rc4-2.manifest.txt \
  verdict-rc4-1.txt verdict-rc4-2.txt \
  transcript-rc4-1.log transcript-rc4-2.log; do
  _op="$OUT/$_o"
  [ -e "$_op" ] || [ -L "$_op" ] || continue
  if [ -L "$_op" ] || [ ! -f "$_op" ]; then
    echo "FATAL: output fixo pre-existente NAO-regular: $_op"; exit 1
  fi
  rm -f "$_op" || { echo "FATAL: nao consegui limpar $_op"; exit 1; }
done
OVERALL=0
{
  echo "# Proveniencia do re-pass do CANDIDATO rc.4 - PLAN-177 W2.2 - 2 partes"
  echo "- Base: $BASE_TAG ($BASE_TAG_OBJ -> $BASE_TAG_COMMIT) .. Candidato: $CANDIDATE_SHA (PRE-tag, doutrina r17)"
  echo "- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only"
  echo "- Data: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$OUT/PROVENANCE-rc4.md"

for P in 1 2; do
  LABEL="$(part_label "$P")"
  MAN="$OUT/paths-rc4-$P.manifest.txt"
  part_paths "$P" > "$MAN" || { echo "FATAL: manifesto parte $P"; exit 1; }
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    git cat-file -e "$CANDIDATE_SHA:$p" 2>/dev/null \
      || { echo "FATAL: caminho ausente no candidato: $p" >&2; exit 1; }
  done < "$MAN"
  DIFF="$OUT/diff-rc4-$P.patch"
  _ps="$(tr '\n' ' ' < "$MAN")" || { echo "FATAL: pathspec parte $P"; exit 1; }
  [ -n "$_ps" ] || { echo "FATAL: pathspec vazio parte $P"; exit 1; }
  # shellcheck disable=SC2086
  git diff "$BASE_TAG_COMMIT".."$CANDIDATE_SHA" -- $_ps > "$DIFF" \
    || { echo "FATAL: git diff parte $P rc!=0"; exit 1; }
  DL=$(wc -l < "$DIFF" | tr -d ' ')
  [ "$DL" -ge 50 ] || { echo "FATAL: parte $P com so $DL linhas"; exit 1; }
  RAW="$OUT/payload-rc4-$P.raw.txt"; RED="$OUT/payload-rc4-$P.redacted.txt"
  { prompt_header "$P" "$LABEL" && echo && cat "$DIFF"; } > "$RAW" \
    || { echo "FATAL: montagem raw parte $P"; exit 1; }
  RAWB=$(wc -c < "$RAW" | tr -d ' ')
  [ "$RAWB" -lt 250000 ] || { echo "FATAL: parte $P ${RAWB}B >= 250KB"; exit 1; }
  python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing < "$RAW" > "$RED" \
    || { echo "FATAL: redactor rc!=0 parte $P"; exit 1; }
  set +e
  grep -q 'CODEX-OUTPUT-TRUNCATED' "$RED"; _trc=$?
  set -uo pipefail
  case "$_trc" in
    0) echo "FATAL: parte $P truncada"; exit 1 ;;
    1) : ;;
    *) echo "FATAL: grep truncamento rc=$_trc"; exit 1 ;;
  esac
  RH=$(grep -c '^@@' "$RAW"); _rhrc=$?
  [ "$_rhrc" -le 1 ] || { echo "FATAL: grep hunks RAW rc=$_rhrc"; exit 1; }
  DH=$(grep -c '^@@' "$RED"); _dhrc=$?
  [ "$_dhrc" -le 1 ] || { echo "FATAL: grep hunks RED rc=$_dhrc"; exit 1; }
  [ "$RH" = "$DH" ] || { echo "FATAL: parte $P hunks $RH -> $DH"; exit 1; }
  RAWL=$(wc -l < "$RAW" | tr -d ' '); REDL=$(wc -l < "$RED" | tr -d ' ')
  [ "$RAWL" = "$REDL" ] || { echo "FATAL: parte $P linhas $RAWL -> $REDL"; exit 1; }
  PRE_SHA_RED=$(shasum -a 256 "$RED" | awk '{print $1}') || { echo "FATAL: shasum RED"; exit 1; }
  PRE_SHA_DIFF=$(shasum -a 256 "$DIFF" | awk '{print $1}') || { echo "FATAL: shasum DIFF"; exit 1; }
  PRE_SHA_MAN=$(shasum -a 256 "$MAN" | awk '{print $1}') || { echo "FATAL: shasum MAN"; exit 1; }
  eval "PIN_RED_$P=\$PRE_SHA_RED"; eval "PIN_DIFF_$P=\$PRE_SHA_DIFF"; eval "PIN_MAN_$P=\$PRE_SHA_MAN"
  echo "parte $P OK (${RAWB}B, $RH hunks) - codex rodando (~10-15 min)..."
  ( cd "$WT" && codex exec --sandbox read-only --color never \
      --output-last-message "$OUT/verdict-rc4-$P.txt" \
      - < "$RED" > "$OUT/transcript-rc4-$P.log" 2>&1 )
  CRC=$?
  VN=$(grep -cE '^VERDICT:' "$OUT/verdict-rc4-$P.txt" 2>/dev/null || true)
  if [ "$VN" = "1" ]; then
    VLINE=$(grep -E '^VERDICT:' "$OUT/verdict-rc4-$P.txt")
  else
    VLINE="(VERDICT ambiguo: $VN linhas - inspecionar transcript; rc=$CRC)"
  fi
  RAW_SHA=$(shasum -a 256 "$RAW" | awk '{print $1}') \
    || { echo "FATAL: shasum raw parte $P"; exit 1; }
  case "$RAW_SHA" in
    ????????????????????????????????????????????????????????????????) : ;;
    *) echo "FATAL: pin raw invalido parte $P"; exit 1 ;;
  esac
  {
    echo "- parte $P ($LABEL): $VLINE [codex rc=$CRC]"
    echo "  - payload-rc4-$P.raw.txt NAO commitado; pin sha256: $RAW_SHA"
  } >> "$OUT/PROVENANCE-rc4.md" \
    || { echo "FATAL: proveniencia parte $P"; exit 1; }
  mkdir -p "$HOME/.rc2-backup"; mv "$RAW" "$HOME/.rc2-backup/payload-rc4-$P.raw.txt"
  [ "$(shasum -a 256 "$RED" | awk '{print $1}')" = "$PRE_SHA_RED" ] \
    || { echo "FATAL: payload parte $P mudou durante o codex"; exit 1; }
  [ "$(shasum -a 256 "$DIFF" | awk '{print $1}')" = "$PRE_SHA_DIFF" ] \
    || { echo "FATAL: diff parte $P mudou durante o run"; exit 1; }
  [ "$(shasum -a 256 "$MAN" | awk '{print $1}')" = "$PRE_SHA_MAN" ] \
    || { echo "FATAL: manifesto parte $P mudou durante o run"; exit 1; }
  echo "parte $P: $VLINE [rc=$CRC]"
  if [ "$CRC" -ne 0 ]; then
    OVERALL=1
  else
    case "$VLINE" in
      "VERDICT: GO"|"VERDICT: GO-WITH-CONDITIONS"*) : ;;
      *) OVERALL=1 ;;
    esac
  fi
done

echo "RUNNER-OVERALL: rc=$OVERALL" >> "$OUT/PROVENANCE-rc4.md"
for _pp in 1 2; do
  eval "_prd=\$PIN_RED_$_pp"; eval "_pdf=\$PIN_DIFF_$_pp"; eval "_pmn=\$PIN_MAN_$_pp"
  [ "$(shasum -a 256 "$OUT/payload-rc4-$_pp.redacted.txt" | awk '{print $1}')" = "$_prd" ] \
    || { echo "FATAL: payload parte $_pp mudou antes da agregacao"; exit 1; }
  [ "$(shasum -a 256 "$OUT/diff-rc4-$_pp.patch" | awk '{print $1}')" = "$_pdf" ] \
    || { echo "FATAL: diff parte $_pp mudou antes da agregacao"; exit 1; }
  [ "$(shasum -a 256 "$OUT/paths-rc4-$_pp.manifest.txt" | awk '{print $1}')" = "$_pmn" ] \
    || { echo "FATAL: manifesto parte $_pp mudou antes da agregacao"; exit 1; }
done
( cd "$OUT" && shasum -a 256 \
    payload-rc4-1.redacted.txt payload-rc4-2.redacted.txt \
    diff-rc4-1.patch diff-rc4-2.patch \
    paths-rc4-1.manifest.txt paths-rc4-2.manifest.txt \
    verdict-rc4-1.txt verdict-rc4-2.txt \
    transcript-rc4-1.log transcript-rc4-2.log \
    PROVENANCE-rc4.md \
    > MANIFEST-rc4.sha256.tmp ) \
  || { echo "FATAL: geracao do MANIFEST-rc4 falhou"; exit 1; }
mv -f "$OUT/MANIFEST-rc4.sha256.tmp" "$OUT/MANIFEST-rc4.sha256" \
  || { echo "FATAL: rename do MANIFEST-rc4 falhou"; exit 1; }
MREAL=$(grep -c . "$OUT/MANIFEST-rc4.sha256" || true)
[ "$MREAL" = "11" ] || { echo "FATAL: MANIFEST-rc4 com $MREAL linhas"; exit 1; }
( cd "$OUT" && shasum -a 256 -c MANIFEST-rc4.sha256 --status ) \
  || { echo "FATAL: MANIFEST-rc4 nao verifica"; exit 1; }
echo "OVERALL: $( [ "$OVERALL" -eq 0 ] && echo GO-nas-2-partes || echo 'PARTE SEM GO - triagem' )"
exit "$OVERALL"
