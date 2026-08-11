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
# Pins LITERAIS do objeto/commit da base (rail r23 P1): a v1.2.0 e um
# release publicado imutavel - o runner nao confia na tag local nem so
# na igualdade local==remoto (um force-move acidental dos DOIS lados
# passaria); os hashes esperados sao constantes revisadas.
BASE_TAG_OBJ="abbb39eba5e5b83c7da6a817c4cf0ee033b5c266"
BASE_TAG_COMMIT="31c5026a37451a577cde8f60ed95306ee0cd8894"
RC_TAG="v1.3.0-rc.3"
git rev-parse -q --verify "refs/tags/$RC_TAG" >/dev/null 2>&1 \
  || { echo "FATAL: tag $RC_TAG nao existe - corte-a primeiro (OWNER-RC3-CUT.sh)"; exit 2; }
# BASE_TAG amarrado (rail r22/r23/r24): assinatura + pins LITERAIS do
# objeto e do commit + remoto == local + ancestral do RC. O diff mais
# abaixo usa o COMMIT PINADO, nunca o nome simbolico.
git tag -v "$BASE_TAG" >/dev/null 2>&1 \
  || { echo "FATAL: assinatura da $BASE_TAG nao verifica"; exit 2; }
[ "$(git rev-parse "$BASE_TAG")" = "$BASE_TAG_OBJ" ] \
  || { echo "FATAL: objeto local da $BASE_TAG != pin revisado $BASE_TAG_OBJ"; exit 2; }
[ "$(git rev-parse "$BASE_TAG^{commit}")" = "$BASE_TAG_COMMIT" ] \
  || { echo "FATAL: commit da $BASE_TAG != pin revisado $BASE_TAG_COMMIT"; exit 2; }
_bt_rls="$(git ls-remote origin "refs/tags/$BASE_TAG" "refs/tags/$BASE_TAG^{}")" \
  || { echo "FATAL: ls-remote da $BASE_TAG falhou"; exit 2; }
_bt_plain="$(printf '%s\n' "$_bt_rls" | awk -v r="refs/tags/$BASE_TAG" '$2==r{print $1}')"
_bt_peel="$(printf '%s\n' "$_bt_rls" | awk -v r="refs/tags/$BASE_TAG^{}" '$2==r{print $1}')"
[ "$_bt_plain" = "$BASE_TAG_OBJ" ] \
  || { echo "FATAL: $BASE_TAG remota != pin revisado"; exit 2; }
[ -z "$_bt_peel" ] || [ "$_bt_peel" = "$BASE_TAG_COMMIT" ] \
  || { echo "FATAL: peel remoto da $BASE_TAG != pin"; exit 2; }
git merge-base --is-ancestor "$BASE_TAG_COMMIT" "$(git rev-parse "$RC_TAG^{commit}")" \
  || { echo "FATAL: base pinada nao e ancestral do $RC_TAG"; exit 2; }

WT="$(mktemp -d "${TMPDIR:-/tmp}/repass-ga.XXXXXX")/wt"
git worktree add --detach "$WT" "$RC_TAG" >/dev/null || exit 2
# Trap unico: remove o worktree E poe em quarentena qualquer payload
# raw que uma falha precoce (redactor/cap/codex) deixaria na arvore -
# sem isso o proximo G0 do OWNER-GA-CUT recusa e a retomada trava
# (rail rc.3 r5 P1-5).
_ga_cleanup() {
  git worktree remove --force "$WT" >/dev/null 2>&1 || true
  mkdir -p "$HOME/.rc2-backup"
  for _raw in "$OUT"/payload-ga-*.raw.txt; do
    [ -e "$_raw" ] || continue
    mv "$_raw" "$HOME/.rc2-backup/quarantine-$(date +%s)-$(basename "$_raw")" \
      && echo "quarentena: $(basename "$_raw") -> ~/.rc2-backup/" >&2
  done
}
trap _ga_cleanup EXIT
_wt_st="$(git -C "$WT" status --porcelain)" \
  || { echo "FATAL: git status do worktree falhou - nao vou assumir limpo"; exit 2; }
[ -z "$_wt_st" ] || { echo "FATAL: worktree sujo"; exit 2; }

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
scripts/install.sh
scripts/_framework_manifest_set.sh
.claude/.framework-version
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
  (all real findings cured in fix-forwards) + the FIRST hold re-pass
  (over rc.2, 2026-08-10) which returned NO-GO with 8 real findings -
  ALL cured in rc.3 (CHANGELOG counts+upgrade section, scoped header
  matcher, checklist sites, npm-publish tag-liveness guard, release-gate
  timeout 20->35) and the cure diff itself passed a codex rail to GO
  (evidence: repass-rc3-cures/). Verify the cures HOLD at this tag;
  do not re-report them as new findings unless one is WRONG or
  incomplete.
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

# Tentativa COMPLETA anterior (manifesto valido + RUNNER-OVERALL) NAO e
# apagada por rerun (rail r26 P1-1): um NO-GO integro exige triagem e
# arquivamento explicito antes de nova tentativa - um GO posterior nao
# pode simplesmente superar um NO-GO sem cura.
if [ -f "$OUT/MANIFEST-ga.sha256" ] \
   && ( cd "$OUT" && shasum -a 256 -c MANIFEST-ga.sha256 --status ) 2>/dev/null \
   && grep -qE "^RUNNER-OVERALL: rc=" "$OUT/PROVENANCE-ga.md" 2>/dev/null; then
  echo "FATAL: evidencia COMPLETA de tentativa anterior presente em repass-ga/"
  echo "  (RUNNER-OVERALL: $(grep -E '^RUNNER-OVERALL:' "$OUT/PROVENANCE-ga.md" | tail -1))"
  echo "  Se foi NO-GO: triagem + arquivamento (mv para repass-ga-<data>-NOGO/) antes de re-rodar."
  echo "  Se foi GO: o OWNER-GA-CUT reusa - nao re-rode o runner."
  exit 1
fi
# Outputs fixos NUNCA atraves de symlink/non-regular pre-existente
# (rail r16 P1-2: um PROVENANCE-ga.md symlink para CHANGELOG.md seria
# TRUNCADO pelo redirect abaixo). So regulares esperados sao removidos.
for _o in PROVENANCE-ga.md MANIFEST-ga.sha256 MANIFEST-ga.sha256.tmp \
  payload-ga-1.redacted.txt payload-ga-2.redacted.txt \
  payload-ga-1.raw.txt payload-ga-2.raw.txt \
  diff-ga-1.patch diff-ga-2.patch \
  paths-ga-1.manifest.txt paths-ga-2.manifest.txt \
  verdict-ga-1.txt verdict-ga-2.txt \
  transcript-ga-1.log transcript-ga-2.log; do
  _op="$OUT/$_o"
  [ -e "$_op" ] || [ -L "$_op" ] || continue
  if [ -L "$_op" ] || [ ! -f "$_op" ]; then
    echo "FATAL: output fixo pre-existente NAO-regular (symlink?): $_op"; exit 1
  fi
  rm -f "$_op" || { echo "FATAL: nao consegui limpar $_op"; exit 1; }
done
OVERALL=0
{
  echo "# Proveniencia do re-pass GA (hold ADR-103) - v1.3.0 - 2 partes"
  echo "- Base: $BASE_TAG ($BASE_TAG_OBJ -> $BASE_TAG_COMMIT) .. Tag: $RC_TAG ($(git rev-parse "$RC_TAG") -> $(git rev-parse "$RC_TAG^{commit}"))"
  echo "- Worktree detached da TAG: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only"
  echo "- Data: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$OUT/PROVENANCE-ga.md"

for P in 1 2; do
  LABEL="$(part_label "$P")"
  MAN="$OUT/paths-ga-$P.manifest.txt"
  # Todo comando que PRODUZ evidencia falha explicito (rail rc.3 r7
  # P1-4: sob set -uo sem -e, um git diff morrendo no meio deixava
  # payload truncado auto-consistente que os controles RAW/RED nao veem).
  part_paths "$P" > "$MAN" || { echo "FATAL: escrita do manifesto de escopo falhou (parte $P)"; exit 1; }
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    git cat-file -e "$RC_TAG:$p" 2>/dev/null \
      || { echo "FATAL: caminho do escopo ausente na tag: $p" >&2; exit 1; }
  done < "$MAN"
  DIFF="$OUT/diff-ga-$P.patch"
  _ps="$(tr '\n' ' ' < "$MAN")" \
    || { echo "FATAL: leitura do pathspec falhou (parte $P)"; exit 1; }
  [ -n "$_ps" ] || { echo "FATAL: pathspec vazio (parte $P)"; exit 1; }
  # shellcheck disable=SC2086
  git diff "$BASE_TAG_COMMIT".."$RC_TAG" -- $_ps > "$DIFF" \
    || { echo "FATAL: git diff da parte $P falhou (rc!=0) - payload seria truncado"; exit 1; }
  DL=$(wc -l < "$DIFF" | tr -d ' ')
  [ "$DL" -ge 50 ] || { echo "FATAL: parte $P com so $DL linhas de diff"; exit 1; }
  RAW="$OUT/payload-ga-$P.raw.txt"; RED="$OUT/payload-ga-$P.redacted.txt"
  { prompt_header "$P" "$LABEL" && echo && cat "$DIFF"; } > "$RAW" \
    || { echo "FATAL: montagem do payload raw da parte $P falhou"; exit 1; }
  RAWB=$(wc -c < "$RAW" | tr -d ' ')
  [ "$RAWB" -lt 250000 ] || { echo "FATAL: parte $P ${RAWB}B >= 250KB"; exit 1; }
  python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing < "$RAW" > "$RED" \
    || { echo "FATAL: redactor rc!=0 na parte $P"; exit 1; }
  set +e
  grep -q 'CODEX-OUTPUT-TRUNCATED' "$RED"; _trc=$?
  set -uo pipefail
  case "$_trc" in
    0) echo "FATAL: parte $P truncada"; exit 1 ;;
    1) : ;;
    *) echo "FATAL: grep do marcador de truncamento falhou (rc=$_trc)"; exit 1 ;;
  esac
  RH=$(grep -c '^@@' "$RAW"); _rhrc=$?
  [ "$_rhrc" -le 1 ] || { echo "FATAL: grep -c hunks RAW falhou (rc=$_rhrc)"; exit 1; }
  DH=$(grep -c '^@@' "$RED"); _dhrc=$?
  [ "$_dhrc" -le 1 ] || { echo "FATAL: grep -c hunks RED falhou (rc=$_dhrc)"; exit 1; }
  [ "$RH" = "$DH" ] || { echo "FATAL: parte $P hunks $RH -> $DH"; exit 1; }
  RAWL=$(wc -l < "$RAW" | tr -d ' '); REDL=$(wc -l < "$RED" | tr -d ' ')
  [ "$RAWL" = "$REDL" ] || { echo "FATAL: parte $P linhas $RAWL -> $REDL"; exit 1; }
  # Binding por-parte (rail r19 P1-2): hash dos insumos ANTES do codex,
  # verificado apos a parte E de novo na agregacao — evidencia de uma
  # parte nao fica mutavel enquanto a outra roda (contra auto-corrupcao
  # acidental; adversario mesmo-UID esta FORA do threat model ratificado).
  PRE_SHA_RED=$(shasum -a 256 "$RED" | awk '{print $1}') || { echo "FATAL: shasum RED"; exit 1; }
  PRE_SHA_DIFF=$(shasum -a 256 "$DIFF" | awk '{print $1}') || { echo "FATAL: shasum DIFF"; exit 1; }
  PRE_SHA_MAN=$(shasum -a 256 "$MAN" | awk '{print $1}') || { echo "FATAL: shasum MAN"; exit 1; }
  eval "PIN_RED_$P=\$PRE_SHA_RED"; eval "PIN_DIFF_$P=\$PRE_SHA_DIFF"; eval "PIN_MAN_$P=\$PRE_SHA_MAN"
  echo "parte $P OK (${RAWB}B, $RH hunks) - codex rodando (~10-15 min)..."
  ( cd "$WT" && codex exec --sandbox read-only --color never \
      --output-last-message "$OUT/verdict-ga-$P.txt" \
      - < "$RED" > "$OUT/transcript-ga-$P.log" 2>&1 )
  CRC=$?
  VN=$(grep -cE '^VERDICT:' "$OUT/verdict-ga-$P.txt" 2>/dev/null || true)
  if [ "$VN" = "1" ]; then
    VLINE=$(grep -E '^VERDICT:' "$OUT/verdict-ga-$P.txt")
  else
    # 0 ou >1 linhas = ambiguo, nunca aprovacao (rail r11 P1-1)
    VLINE="(VERDICT ambiguo: $VN linhas - inspecionar transcript; rc=$CRC)"
  fi
  RAW_SHA=$(shasum -a 256 "$RAW" | awk '{print $1}') \
    || { echo "FATAL: shasum do payload raw falhou (parte $P)"; exit 1; }
  case "$RAW_SHA" in
    ????????????????????????????????????????????????????????????????) : ;;
    *) echo "FATAL: pin do raw invalido (parte $P): '$RAW_SHA'"; exit 1 ;;
  esac
  {
    echo "- parte $P ($LABEL): $VLINE [codex rc=$CRC]"
    echo "  - payload-ga-$P.raw.txt NAO commitado; pin sha256: $RAW_SHA"
  } >> "$OUT/PROVENANCE-ga.md" \
    || { echo "FATAL: escrita da proveniencia falhou (parte $P)"; exit 1; }
  mkdir -p "$HOME/.rc2-backup"; mv "$RAW" "$HOME/.rc2-backup/payload-ga-$P.raw.txt"
  # pos-parte: insumos identicos aos que o codex consumiu
  [ "$(shasum -a 256 "$RED" | awk '{print $1}')" = "$PRE_SHA_RED" ] \
    || { echo "FATAL: payload da parte $P mudou DURANTE o run do codex"; exit 1; }
  [ "$(shasum -a 256 "$DIFF" | awk '{print $1}')" = "$PRE_SHA_DIFF" ] \
    || { echo "FATAL: diff da parte $P mudou durante o run"; exit 1; }
  [ "$(shasum -a 256 "$MAN" | awk '{print $1}')" = "$PRE_SHA_MAN" ] \
    || { echo "FATAL: manifesto de escopo da parte $P mudou durante o run"; exit 1; }
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

# RUNNER-OVERALL entra na proveniencia ANTES do manifesto, que agora a
# INCLUI (rail rc.3 r5 P1-3: proveniencia fora do manifesto era
# reescrevivel para casar evidencia stale no reuso do GA-CUT).
echo "RUNNER-OVERALL: rc=$OVERALL" >> "$OUT/PROVENANCE-ga.md"
# Geracao do manifesto GUARDADA (rail rc.3 r6 P1-4): sob `set -uo
# pipefail` sem -e, um shasum falhando escrevia manifesto parcial e o
# runner ainda saia 0 — o OWNER-GA-CUT assinava ate o guard recusar.
for _pp in 1 2; do
  eval "_prd=\$PIN_RED_$_pp"; eval "_pdf=\$PIN_DIFF_$_pp"; eval "_pmn=\$PIN_MAN_$_pp"
  [ "$(shasum -a 256 "$OUT/payload-ga-$_pp.redacted.txt" | awk '{print $1}')" = "$_prd" ] \
    || { echo "FATAL: payload da parte $_pp mudou antes da agregacao"; exit 1; }
  [ "$(shasum -a 256 "$OUT/diff-ga-$_pp.patch" | awk '{print $1}')" = "$_pdf" ] \
    || { echo "FATAL: diff da parte $_pp mudou antes da agregacao"; exit 1; }
  [ "$(shasum -a 256 "$OUT/paths-ga-$_pp.manifest.txt" | awk '{print $1}')" = "$_pmn" ] \
    || { echo "FATAL: manifesto da parte $_pp mudou antes da agregacao"; exit 1; }
done
( cd "$OUT" && shasum -a 256 \
    payload-ga-1.redacted.txt payload-ga-2.redacted.txt \
    diff-ga-1.patch diff-ga-2.patch \
    paths-ga-1.manifest.txt paths-ga-2.manifest.txt \
    verdict-ga-1.txt verdict-ga-2.txt \
    transcript-ga-1.log transcript-ga-2.log \
    PROVENANCE-ga.md \
    > MANIFEST-ga.sha256.tmp ) \
  || { echo "FATAL: geracao do MANIFEST-ga falhou"; exit 1; }
mv -f "$OUT/MANIFEST-ga.sha256.tmp" "$OUT/MANIFEST-ga.sha256" \
  || { echo "FATAL: rename atomico do MANIFEST-ga falhou"; exit 1; }
MREAL=$(grep -c . "$OUT/MANIFEST-ga.sha256" || true)
[ "$MREAL" = "11" ] || { echo "FATAL: MANIFEST-ga com $MREAL linhas (esperado 11)"; exit 1; }
( cd "$OUT" && shasum -a 256 -c MANIFEST-ga.sha256 --status ) \
  || { echo "FATAL: MANIFEST-ga recem-gerado nao verifica"; exit 1; }
echo "OVERALL: $( [ "$OVERALL" -eq 0 ] && echo GO-nas-2-partes || echo 'PARTE SEM GO - triagem' )"
exit "$OVERALL"
