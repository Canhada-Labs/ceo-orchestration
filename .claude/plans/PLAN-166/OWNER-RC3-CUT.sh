#!/bin/bash
# OWNER-RC3-CUT.sh - corte da v1.3.0-rc.3 em UM comando (S301).
#
#   bash .claude/plans/PLAN-166/OWNER-RC3-CUT.sh
#
# POR QUE rc.3: o re-pass do hold da rc.2 (10/08) terminou NO-GO nas 2
# partes - 8 achados triados como REAIS (3 P1 + 5 P2; triagem em
# repass-ga-rc2-NOGO/TRIAGE-ga-repass.md). As curas foram autoradas em
# worktree, revisadas pelo rail codex ate GO (repass-rc3-cures/) e estao
# STAGED em staged-rc3/ sob MANIFEST+BASELINE sha256.
#
# O que faz, na ordem (fail-closed em tudo):
#   1. assina o sentinel RC3-approved.md (pinentry 1)
#   2. APLICA o pack staged-rc3 -> arvore viva (BASELINE conferida antes,
#      MANIFEST conferido depois) + gates locais (verify-counts, pytest,
#      yaml, bash -n)
#   3. commit 1: curas + evidencia + pack + scripts (allowlist FECHADA)
#   4. gera verdict-fields rc.3 (parent = commit 1) e voce assina (pinentry 2)
#   5. monta o verdito, commit 2, guard local, push, espera CI
#   6. preflight --rc 3 + tag assinada (pinentry 3)
#   7. push da tag (confirmacao SIM MAIUSCULO) + release.yml +
#      controle positivo await-release-gate + pre-release GitHub
# Depois: HOLD ADR-103 reinicia (>= 24h do publishedAt da rc.3);
# amanha: bash .claude/plans/PLAN-166/OWNER-GA-CUT.sh (ja aponta rc.3).
#
# Se falhar em QUALQUER passo, para com mensagem clara. Rodar de novo e
# seguro ANTES do commit 1. DEPOIS do commit 1 o HEAD moveu e o G0
# recusa de proposito - NAO re-rode nem resete: me chame no Claude.
set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"; cd "$REPO"
EXPECTED_HEAD="0cb09c3cc587abdeaed33e0ff13b1c8b3677061d"
TAG="v1.3.0-rc.3"
KEY="CFCFACF00335DC74"
P166=".claude/plans/PLAN-166"
P169=".claude/plans/PLAN-169"
PACK="$P166/staged-rc3"
CURES="$P166/repass-rc3-cures"
SCRIPTSR="$P166/repass-rc3-scripts"
NOGO="$P166/repass-ga-rc2-NOGO"
SENT="$P166/RC3-approved.md"
SENT_DRAFT="$P166/RC3-approved-draft.md"
VF="$P166/verdict-fields-v1.3.0-rc.3.md"
VD=".claude/governance/pair-rail-verdict-v1.3.0-rc.3.md"
VF_TPL="$P166/verdict-fields-v1.3.0-rc.3.TEMPLATE.md"
VD_TPL="$P166/pair-rail-verdict-v1.3.0-rc.3.TEMPLATE.md"

say() { printf '\n== %s\n' "$*"; }
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
bell() { printf '\a'; osascript -e "display notification \"$1\" with title \"rc.3\"" 2>/dev/null || true; }

GPG_TTY="$(tty 2>/dev/null || true)"; export GPG_TTY
gpgconf --kill gpg-agent 2>/dev/null || true

say "G0 pre-condicoes"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] \
  || die "nao esta em main (branch/detached) - r6-P2 do rail"
[ "$(git rev-parse HEAD)" = "$EXPECTED_HEAD" ] \
  || die "HEAD nao e $EXPECTED_HEAD (o commit da rc.2). Se o script ja
rodou ate o commit 1 e falhou depois, NAO resete: me chame no Claude
que eu retomo do ponto exato. Se main andou por outro motivo, idem."
git fetch --quiet origin main
[ "$(git rev-parse origin/main)" = "$EXPECTED_HEAD" ] \
  || die "origin/main moveu - investigar antes de cortar"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 \
  && die "tag $TAG ja existe (local)"
# Tag REMOTA tambem (rail r12 P1-5): um rc.3 remoto que o fetch de main
# nao traz deixaria o script commitar/pushar main e so falhar no push da
# tag - com o G0 pos-commit recusando a retomada. Transporte falhando e
# erro, nunca "ausente".
_rls="$(git ls-remote origin "refs/tags/$TAG" "refs/tags/$TAG^{}")" \
  || die "git ls-remote falhou (transporte) - nao vou assumir tag remota ausente"
[ -z "$_rls" ] || die "tag $TAG ja existe no REMOTO:
$_rls"
# Release fantasma de tentativa abortada (rail r27 P1-2): um pre-release
# orfao com publishedAt antigo furaria o hold do GA. NOT-FOUND != falha
# de API.
# Probe dentro de `if` (rail r28 P0): atribuicao com rc!=0 sob set -e
# mataria o script ANTES do $? - o caminho normal (release ausente)
# nunca chegava a classificacao NOT-FOUND.
if _grv_out="$(gh release view "$TAG" --json name 2>&1)"; then
  die "GitHub Release do $TAG JA EXISTE (tentativa anterior?) - delete/triagem antes: gh release delete $TAG"
fi
printf '%s' "$_grv_out" | grep -qi "not found\|release not found\|HTTP 404" \
  || die "gh release view falhou sem ser NOT-FOUND (API?): $_grv_out"
command -v gh >/dev/null 2>&1 || die "gh CLI ausente"
[ -f "$VF_TPL" ] && [ -f "$VD_TPL" ] || die "templates rc.3 ausentes (o Claude gera pos-rail)"
[ -f "$SENT_DRAFT" ] || die "RC3-approved-draft.md ausente"
grep -q "Anchor-SHA: $EXPECTED_HEAD" "$SENT_DRAFT" \
  || die "Anchor-SHA do sentinel nao bate com o HEAD esperado"
ls "$CURES"/payload-*.raw.txt >/dev/null 2>&1 \
  && die "payload raw do rail ainda na arvore - o Claude devia ter movido"
ls "$SCRIPTSR"/payload-*.raw.txt >/dev/null 2>&1 \
  && die "payload raw do rail de SCRIPTS ainda na arvore"
ls "$NOGO"/payload-*.raw.txt >/dev/null 2>&1 \
  && die "payload raw do NO-GO ainda na arvore"

check_rail_and_evidence() {
say "G0b: rail de curas terminou GO (verificacao completa)"
# O round FINAL e DERIVADO do proprio conjunto de rounds no disco (o
# maior N com verdict presente) - nunca lido de um arquivo de status
# mutavel (rail r5 P1-3: um RAIL-STATUS editado selecionaria um GO
# anterior). RAIL-STATUS.txt existe so como registro informacional.
FINAL_N=0
for _vfp in "$CURES"/verdict-cures-round*.txt; do
  [ -e "$_vfp" ] || die "nenhum verdict-cures-roundN.txt - rail nao rodou"
  _n="${_vfp##*round}"; _n="${_n%.txt}"
  case "$_n" in (*[!0-9]*|'') die "nome de verdito invalido: $_vfp" ;; esac
  [ "$_n" -gt "$FINAL_N" ] && FINAL_N="$_n"
done
[ "$FINAL_N" -gt 0 ] || die "nenhum round de rail encontrado"
FINAL_ROUND="round$FINAL_N"
# Exatamente UMA linha VERDICT (rail r11 P1-1): um arquivo com NO-GO
# seguido de GO e ambiguo, nao aprovacao.
_fvn="$(grep -cE '^VERDICT:' "$CURES/verdict-cures-$FINAL_ROUND.txt" 2>/dev/null || true)"
[ "$_fvn" = "1" ] \
  || die "verdito final do rail ($FINAL_ROUND) tem $_fvn linhas VERDICT (exigido: exatamente 1) - ambiguo"
FVL="$(grep -E '^VERDICT:' "$CURES/verdict-cures-$FINAL_ROUND.txt")"
[ "$FVL" = "VERDICT: GO" ] \
  || die "verdito final do rail ($FINAL_ROUND, derivado do disco): '$FVL' != GO exato - triagem comigo no Claude"
( cd "$CURES" && shasum -a 256 -c MANIFEST-cures.sha256 --status ) \
  || die "MANIFEST-cures nao confere - evidencia do rail adulterada/incompleta"
# Set-equality BIDIRECIONAL: o manifesto lista exatamente as 4-tuplas
# (payload.redacted/diff/verdict/transcript) de TODOS os rounds 1..N -
# um round suprimido do manifesto ou um arquivo extra nele aborta.
_ev_want="$( { _r=1; while [ "$_r" -le "$FINAL_N" ]; do
    echo "diff-cures-round$_r.patch"
    echo "payload-cures-round$_r.redacted.txt"
    echo "transcript-cures-round$_r.log"
    echo "verdict-cures-round$_r.txt"
    _r=$((_r+1)); done; echo "PROVENANCE-cures.md"; \
    echo "CEREMONY-MANIFEST.sha256"; } | sort )"
_ev_have="$( awk '{print $2}' "$CURES/MANIFEST-cures.sha256" | sort )"
[ "$_ev_want" = "$_ev_have" ] || die "MANIFEST-cures nao cobre exatamente os rounds 1..$FINAL_N:
$(diff <(printf '%s\n' "$_ev_want") <(printf '%s\n' "$_ev_have") | sed 's/^/   /')"
# Fechamento do DIRETORIO de evidencia por conjunto exato de filhos
# DIRETOS (rail r5 P1-2: prefixo na allowlist admite look-alike
# aninhado que o git add recursivo commitaria como parent revisado).
_cd_odd="$( cd "$CURES" && find . ! -type f ! -type d | head -5 )"
[ -z "$_cd_odd" ] || die "entrada NAO-regular em repass-rc3-cures: $_cd_odd"
_cd_sub="$( cd "$CURES" && find . -mindepth 2 | head -5 )"
[ -z "$_cd_sub" ] || die "subdiretorio/arquivo aninhado em repass-rc3-cures (look-alike?):
$_cd_sub"
_cd_disk="$( cd "$CURES" && find . -maxdepth 1 -type f | sed 's|^\./||' | sort )"
_cd_want="$( { printf '%s\n' "$_ev_want"; \
  echo "MANIFEST-cures.sha256"; \
  echo "RAIL-STATUS.txt"; echo "run-rc3-cure-review.sh"; } | sort -u )"
[ "$_cd_disk" = "$_cd_want" ] || die "conjunto de arquivos em repass-rc3-cures difere do esperado:
$(diff <(printf '%s\n' "$_cd_want") <(printf '%s\n' "$_cd_disk") | sed 's/^/   /')"
# BINDING evidencia<->pack<->anchor (rail r6 P1-1): a proveniencia —
# que esta DENTRO do manifesto shasum-verificado acima — tem de nomear
# o anchor exato e pinar os manifestos do pack staged-rc3 vigente. Um
# dir de evidencia GO stale pareado com um pack diferente aborta aqui.
_bind_anchor="$(awk '/^BINDING-ANCHOR:/{print $2}' "$CURES/PROVENANCE-cures.md" | tail -1)"
[ "$_bind_anchor" = "$EXPECTED_HEAD" ] \
  || die "BINDING-ANCHOR da evidencia ('$_bind_anchor') != EXPECTED_HEAD - evidencia de outro anchor"
_bind_pm="$(awk '/^BINDING-PACK-MANIFEST-SHA256:/{print $2}' "$CURES/PROVENANCE-cures.md" | tail -1)"
[ "$_bind_pm" = "$(shasum -a 256 "$PACK/MANIFEST.sha256" | awk '{print $1}')" ] \
  || die "BINDING do MANIFEST do pack nao bate - o pack staged-rc3 NAO e o que o rail revisou"
_bind_bl="$(awk '/^BINDING-PACK-BASELINE-SHA256:/{print $2}' "$CURES/PROVENANCE-cures.md" | tail -1)"
[ "$_bind_bl" = "$(shasum -a 256 "$PACK/BASELINE.sha256" | awk '{print $1}')" ] \
  || die "BINDING do BASELINE do pack nao bate"
_bind_md="$(awk '/^BINDING-PACK-MODES-SHA256:/{print $2}' "$CURES/PROVENANCE-cures.md" | tail -1)"
[ "$_bind_md" = "$(shasum -a 256 "$PACK/MODES.txt" | awk '{print $1}')" ] \
  || die "BINDING do MODES.txt do pack nao bate (exec-bit fora do revisado?)"
# Os PROPRIOS arquivos de cerimonia sao content-pinados (rail r16
# P1-1): scripts, templates, sentinel draft e morning doc nao podem
# mudar depois do review por mero same-path. O CEREMONY-MANIFEST esta
# dentro do MANIFEST-cures (bytes) e seu sha no BINDING da proveniencia.
( cd "$REPO" && shasum -a 256 -c "$CURES/CEREMONY-MANIFEST.sha256" --status ) \
  || die "arquivo de CERIMONIA mudou depois do review (CEREMONY-MANIFEST nao confere) - regenerar/re-revisar; me chame no Claude"
echo "   OK: rail de PRODUTO GO ($FINAL_ROUND de $FINAL_N rounds; evidencia fechada + BINDING confere)"
# --- Trilho 2: reviews de CERIMONIA (rail r25 P0: namespace proprio,
# FORA do delta-manifest dos templates - fecha o loop de clausura).
SFINAL_N=0
for _svp in "$SCRIPTSR"/verdict-cures-round*.txt; do
  [ -e "$_svp" ] || die "nenhum verdito de scripts em repass-rc3-scripts"
  _sn="${_svp##*round}"; _sn="${_sn%.txt}"
  case "$_sn" in (*[!0-9]*|'') die "verdito de scripts invalido: $_svp" ;; esac
  [ "$_sn" -gt "$SFINAL_N" ] && SFINAL_N="$_sn"
done
[ "$SFINAL_N" -gt 0 ] || die "rail de scripts sem rounds"
_sfn="$(grep -cE '^VERDICT:' "$SCRIPTSR/verdict-cures-round$SFINAL_N.txt" 2>/dev/null || true)"
[ "$_sfn" = "1" ] || die "verdito de scripts round$SFINAL_N com $_sfn linhas VERDICT - ambiguo"
_sfl="$(grep -E '^VERDICT:' "$SCRIPTSR/verdict-cures-round$SFINAL_N.txt")"
[ "$_sfl" = "VERDICT: GO" ] \
  || die "verdito FINAL do rail de scripts (round$SFINAL_N): '$_sfl' != GO exato - triagem comigo no Claude"
( cd "$SCRIPTSR" && shasum -a 256 -c SCRIPTS-MANIFEST.sha256 --status ) \
  || die "SCRIPTS-MANIFEST nao confere"
_sc_odd="$( cd "$SCRIPTSR" && find . ! -type f ! -type d | head -5 )"
[ -z "$_sc_odd" ] || die "nao-regular em repass-rc3-scripts: $_sc_odd"
_sc_sub="$( cd "$SCRIPTSR" && find . -mindepth 2 | head -5 )"
[ -z "$_sc_sub" ] || die "aninhado em repass-rc3-scripts: $_sc_sub"
_sc_disk="$( cd "$SCRIPTSR" && find . -maxdepth 1 -type f | sed 's|^\./||' | sort )"
_sc_want="$( { awk '{print $2}' "$SCRIPTSR/SCRIPTS-MANIFEST.sha256"; \
  echo "SCRIPTS-MANIFEST.sha256"; } | sort -u )"
[ "$_sc_disk" = "$_sc_want" ] || die "conjunto em repass-rc3-scripts difere do SCRIPTS-MANIFEST:
$(diff <(printf '%s\n' "$_sc_want") <(printf '%s\n' "$_sc_disk") | sed 's/^/   /')"
# Evidencia de scripts amarrada ao CEREMONY-MANIFEST vigente (rail r27
# P1-1): a ULTIMA linha AT-REVIEW da provenance de scripts tem de pinar
# exatamente o manifesto de cerimonia atual.
[ "$SFINAL_N" -ge 5 ] || die "rail de scripts abaixo do namespace esperado (SFINAL=$SFINAL_N < 5)"
# A linha AT-REVIEW tem de ser DO round final especifico (rail r29
# P1-1: um GO stale de round maior nao pode casar com o AT-REVIEW de
# outro round).
_sc_cm="$(awk -v r="round$SFINAL_N:" '$0 ~ ("CEREMONY-MANIFEST-SHA256-AT-REVIEW " r) {print $NF}' "$SCRIPTSR/PROVENANCE-scripts.md" 2>/dev/null | tail -1)"
[ "$_sc_cm" = "$(shasum -a 256 "$CURES/CEREMONY-MANIFEST.sha256" | awk '{print $1}')" ] \
  || die "review de scripts round$SFINAL_N NAO cobre o CEREMONY-MANIFEST vigente (AT-REVIEW='$_sc_cm') - nova rodada necessaria"
# Tuplas CONTIGUAS 5..N (rail r27 P1-1).
_scn=5
while [ "$_scn" -le "$SFINAL_N" ]; do
  for _sk in "payload-cures-round$_scn.redacted.txt" "diff-cures-round$_scn.patch" \
             "verdict-cures-round$_scn.txt" "transcript-cures-round$_scn.log"; do
    [ -f "$SCRIPTSR/$_sk" ] || die "tupla de scripts incompleta no round$_scn: falta $_sk"
  done
  _scn=$((_scn+1))
done
_bind_sm="$(awk '/^BINDING-SCRIPTS-MANIFEST-SHA256:/{print $2}' "$CURES/PROVENANCE-cures.md" | tail -1)"
[ "$_bind_sm" = "$(shasum -a 256 "$SCRIPTSR/SCRIPTS-MANIFEST.sha256" | awk '{print $1}')" ] \
  || die "BINDING do SCRIPTS-MANIFEST nao bate"
echo "   OK: rail de SCRIPTS GO (round$SFINAL_N; evidencia fechada + BINDING confere)"
}
check_rail_and_evidence

check_pack() {
say "G0c: pack staged-rc3 fechado por manifesto + baseline"
( cd "$PACK" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || die "staged-rc3 nao confere com o MANIFEST do pack"
_st_odd="$( cd "$PACK" && find . ! -type f ! -type d | head -5 )"
[ -z "$_st_odd" ] || die "entrada NAO-regular dentro de staged-rc3 (symlink/fifo?):
$_st_odd"
_st_disk="$( cd "$PACK" && find . -type f | sed 's|^\./||' | sort )"
_st_want="$( { awk '{print $2}' "$PACK/MANIFEST.sha256"; \
  echo "MANIFEST.sha256"; echo "BASELINE.sha256"; echo "MODES.txt"; } | sort )"
[ "$_st_disk" = "$_st_want" ] || die "conjunto de arquivos em staged-rc3 difere do MANIFEST:
$(diff <(printf '%s\n' "$_st_want") <(printf '%s\n' "$_st_disk") | sed 's/^/   /')"
# TRI-ESTADO por arquivo (rail r5 P1-4: exigir BASELINE puro quebrava o
# rerun anunciado — apos um apply parcial, arquivos ja curados falhavam
# o baseline). Cada arquivo vivo tem de estar EM UM de dois estados:
# pre-cura (== BASELINE) ou ja-curado (== MANIFEST do pack). Qualquer
# TERCEIRO estado (cherry-pick perdido, edicao manual) aborta.
_tri_bad=""
while IFS= read -r _mline; do
  [ -n "$_mline" ] || continue
  _mf="${_mline#*  }"; _msha="${_mline%%  *}"
  _bsha="$(awk -v f="$_mf" '$0 ~ ("  " f "$") {print $1}' "$PACK/BASELINE.sha256")"
  [ -n "$_bsha" ] || die "arquivo do MANIFEST sem linha no BASELINE: $_mf"
  # Symlink no alvo canonico e sempre TERCEIRO estado (rail r8 P1-3):
  # shasum seguiria o link e "ja aplicado" commitaria o symlink.
  if [ -L "$_mf" ]; then
    _tri_bad="$_tri_bad
   $_mf (SYMLINK no lugar do arquivo canonico)"
    continue
  fi
  _lsha="$(shasum -a 256 "$_mf" | awk '{print $1}')"
  if [ "$_lsha" != "$_bsha" ] && [ "$_lsha" != "$_msha" ]; then
    _tri_bad="$_tri_bad
   $_mf (vivo=$_lsha nem baseline nem pack)"
  fi
  # Estado "ja aplicado" exige tambem o MODO do MODES.txt assinado
  # (rail r12 P1-6: chmod no vivo pos-apply passava o re-check de
  # staging - sha igual, modo nao olhado).
  if [ "$_lsha" = "$_msha" ]; then
    _tri_wm="$(awk -v f="$_mf" '$2==f{print $1}' "$PACK/MODES.txt")"
    _tri_lm="$(python3 -c 'import os,sys;print(oct(os.stat(sys.argv[1]).st_mode & 0o777)[2:])' "$_mf")"
    [ "$_tri_lm" = "$_tri_wm" ] || _tri_bad="$_tri_bad
   $_mf (modo vivo $_tri_lm != $_tri_wm do MODES.txt assinado)"
  fi
done < "$PACK/MANIFEST.sha256"
[ -z "$_tri_bad" ] || die "arquivo(s) vivos em TERCEIRO estado (nem rc.2 nem pack) - me chame no Claude:$_tri_bad"
# Exec-bit e parte do material revisado (rail r9 P1-3): sha256 nao
# cobre modo; MODES.txt (pinado no BINDING) e a autoridade — o modo
# ATUAL do pack nao decide nada.
while IFS=' ' read -r _mmode _mpath; do
  [ -n "$_mpath" ] || continue
  _pm="$(python3 -c 'import os,sys;print(oct(os.stat(sys.argv[1]).st_mode & 0o777)[2:])' "$PACK/$_mpath")"
  [ "$_pm" = "$_mmode" ] \
    || die "modo do pack divergiu do MODES.txt revisado: $_mpath ($_pm != $_mmode)"
done < "$PACK/MODES.txt"
echo "   OK: pack fechado ($(grep -c . "$PACK/MANIFEST.sha256") arquivos) + vivos em estado pre-cura ou ja-curado + modes conferem"
}
check_pack

check_nogo_w3() {
say "G0c2: arquivo morto do NO-GO + espelho W3 fechados por manifesto"
# repass-ga-rc2-NOGO: conjunto exato + conteudo pinado (rail r5 P1-2).
( cd "$NOGO" && shasum -a 256 -c MANIFEST-NOGO.sha256 --status ) \
  || die "arquivo do NO-GO nao confere com MANIFEST-NOGO"
_ng_odd="$( cd "$NOGO" && find . ! -type f ! -type d | head -5 )"
[ -z "$_ng_odd" ] || die "entrada NAO-regular em repass-ga-rc2-NOGO: $_ng_odd"
_ng_sub="$( cd "$NOGO" && find . -mindepth 2 | head -5 )"
[ -z "$_ng_sub" ] || die "aninhado em repass-ga-rc2-NOGO (look-alike?): $_ng_sub"
_ng_disk="$( cd "$NOGO" && find . -maxdepth 1 -type f | sed 's|^\./||' | sort )"
_ng_want="$( { awk '{print $2}' "$NOGO/MANIFEST-NOGO.sha256"; echo "MANIFEST-NOGO.sha256"; } | sort )"
[ "$_ng_disk" = "$_ng_want" ] || die "conjunto em repass-ga-rc2-NOGO difere do MANIFEST-NOGO:
$(diff <(printf '%s\n' "$_ng_want") <(printf '%s\n' "$_ng_disk") | sed 's/^/   /')"
# staged-w3: mesma disciplina do G0b do RC2-CUT (conteudo + conjunto).
( cd "$P169/staged-w3" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || die "staged-w3 nao confere com o MANIFEST do pack W3"
_sw_odd="$( cd "$P169/staged-w3" && find . ! -type f ! -type d | head -5 )"
[ -z "$_sw_odd" ] || die "entrada NAO-regular em staged-w3: $_sw_odd"
_sw_disk="$( cd "$P169/staged-w3" && find . -type f | sed 's|^\./||' | sort )"
_sw_want="$( { awk '{print $2}' "$P169/staged-w3/MANIFEST.sha256"; \
  echo "MANIFEST.sha256"; echo "BASELINE.sha256"; } | sort )"
[ "$_sw_disk" = "$_sw_want" ] || die "conjunto em staged-w3 difere do MANIFEST:
$(diff <(printf '%s\n' "$_sw_want") <(printf '%s\n' "$_sw_disk") | sed 's/^/   /')"
echo "   OK: NO-GO ($(grep -c . "$NOGO/MANIFEST-NOGO.sha256") arquivos) + staged-w3 fechados"
}
check_nogo_w3

say "G0d: pin do codex"
PIN_JSON="$(python3 .claude/hooks/check_pair_rail.py --verify-codex-pin 2>/dev/null || true)"
printf '%s' "$PIN_JSON" | grep -q '"status": "verified"' || die "pin do codex nao verifica"

# Allowlist FECHADA do commit 1 (curas aplicadas + evidencia + pack +
# scripts do corte + espelho W3). Entrada terminada em / cobre o dir.
COMMIT1_ALLOW="CHANGELOG.md
.claude/scripts/local/verify-counts.sh
.github/release-checklist.md
.github/workflows/npm-publish.yml
.github/workflows/release.yml
.claude/scripts/tests/test_release_workflow_asserts.py
.claude/scripts/tests/test_verify_counts.py
$P166/OWNER-GA-CUT.sh
$P166/OWNER-RC3-CUT.sh
$P166/RC3-approved-draft.md
$P166/RC3-approved.md
$P166/RC3-approved.md.asc
$P166/OWNER-MORNING-RC3.md
$P166/verdict-fields-v1.3.0-rc.3.TEMPLATE.md
$P166/pair-rail-verdict-v1.3.0-rc.3.TEMPLATE.md
$P166/verdict-fields-v1.3.0.TEMPLATE.md
$P166/pair-rail-verdict-v1.3.0.TEMPLATE.md
$P166/repass-ga/run-ga-repass.sh
$P166/repass-ga-rc2-NOGO/
$P166/repass-rc3-cures/
$P166/repass-rc3-scripts/
$P166/staged-rc3/
$P169/W3-approved-draft.md
$P169/staged-w3/"

check_tree_is_exactly_the_prep() {
  # git status CAPTURADO com rc checado (rail r8 P1-2: falha dentro de
  # command substitution em heredoc virava "arvore limpa").
  _st_out="$(git status --porcelain --untracked-files=all)" \
    || die "git status falhou - nao vou tratar como arvore limpa"
  _bad=""
  while IFS= read -r _line; do
    [ -n "$_line" ] || continue
    _path="${_line#???}"
    _hit=0
    while IFS= read -r _allow; do
      [ -n "$_allow" ] || continue
      case "$_allow" in
        */) case "$_path" in "$_allow"*|"${_allow%/}") _hit=1 ;; esac ;;
        *)  [ "$_path" = "$_allow" ] && _hit=1 ;;
      esac
      [ "$_hit" -eq 1 ] && break
    done <<ALLOW
$COMMIT1_ALLOW
ALLOW
    [ "$_hit" -eq 1 ] || _bad="$_bad
   $_path"
  done <<STATUS
$_st_out
STATUS
  [ -z "$_bad" ] || die "arquivo(s) FORA da allowlist do commit 1 (nao revisados pelo rail):$_bad
Remova/stash antes de cortar, ou me chame no Claude."
}
# Limpa temporarios de um apply interrompido ANTES do fechamento de
# arvore (rail r7 P1-2: um .rc3tmp.* orfao triparia a allowlist).
while IFS= read -r _mline; do
  [ -n "$_mline" ] || continue
  _mf="${_mline#*  }"
  rm -f "$(dirname "$_mf")/.rc3tmp.$(basename "$_mf")"
done < "$PACK/MANIFEST.sha256"
check_tree_is_exactly_the_prep
say "mudancas que entram no commit 1 (todas dentro da allowlist):"
git status --short
printf '\nEnter para seguir (ctrl-C para abortar): '; read -r _

say "1/7 assinar o sentinel RC3-approved.md (pinentry 1)"
# Destino do sentinel nunca atraves de symlink pre-existente (rail
# r24-3): remove qualquer resto antes do cp e assere regular depois.
[ -L "$SENT" ] && rm -f "$SENT"
rm -f "$SENT" "$SENT.asc"
cp "$SENT_DRAFT" "$SENT"
[ -f "$SENT" ] && [ ! -L "$SENT" ] || die "sentinel gerado nao e arquivo regular"
gpg --armor --detach-sign -u "$KEY" "$SENT"
gpg --verify "$SENT.asc" "$SENT" || die "assinatura do sentinel nao verifica"

say "2/7 aplicar o pack staged-rc3 -> arvore viva + gates locais"
# Idempotente (rail r5 P1-4) e ATOMICO (rail r7 P1-2): copia para um
# temporario no MESMO diretorio, verifica o hash do pack e so entao
# renomeia — uma interrupcao/IO-error nunca deixa o alvo truncado num
# terceiro estado; o tmp remanescente e removido no rerun.
while IFS= read -r _mline; do
  [ -n "$_mline" ] || continue
  _mf="${_mline#*  }"; _msha="${_mline%%  *}"
  _tmp="$(dirname "$_mf")/.rc3tmp.$(basename "$_mf")"
  rm -f "$_tmp"
  _lsha="$(shasum -a 256 "$_mf" | awk '{print $1}')"
  # Modo esperado vem do MODES.txt REVISADO, nunca do pack atual (r9
  # P1-3: um chmod no pack pos-review passaria com sha igual).
  _wmode="$(awk -v f="$_mf" '$2==f{print $1}' "$PACK/MODES.txt")"
  [ -n "$_wmode" ] || die "arquivo sem entrada no MODES.txt: $_mf"
  _lmode="$(python3 -c 'import os,sys;print(oct(os.stat(sys.argv[1]).st_mode & 0o777)[2:])' "$_mf")"
  if [ "$_lsha" = "$_msha" ] && [ ! -L "$_mf" ] && [ -f "$_mf" ] \
     && [ "$_lmode" = "$_wmode" ]; then
    echo "   (ja aplicado) $_mf"
  else
    cp -p "$PACK/$_mf" "$_tmp" || die "cp para temporario falhou: $_mf"
    [ "$(shasum -a 256 "$_tmp" | awk '{print $1}')" = "$_msha" ] \
      || die "temporario nao bate com o pack (IO?): $_mf"
    mv -f "$_tmp" "$_mf" || die "rename atomico falhou: $_mf"
    chmod "$_wmode" "$_mf" || die "chmod para o modo revisado falhou: $_mf"
  fi
done < "$PACK/MANIFEST.sha256"
# pos-apply: o vivo tem de bater byte a byte com o MANIFEST do pack
( shasum -a 256 -c "$PACK/MANIFEST.sha256" --status ) \
  || die "pos-apply: vivo != pack (cp parcial?)"
echo "   pack aplicado; rodando gates locais..."
bash -n .claude/scripts/local/verify-counts.sh || die "bash -n verify-counts falhou"
python3 - <<'PYEOF' || die "yaml dos workflows nao parseia"
import yaml
for f in (".github/workflows/npm-publish.yml", ".github/workflows/release.yml"):
    yaml.safe_load(open(f, encoding="utf-8"))
PYEOF
bash .claude/scripts/local/verify-counts.sh --no-tests >/dev/null \
  || die "verify-counts com drift pos-cura (nao devia)"
python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py \
  .claude/scripts/tests/test_verify_counts.py -q \
  || die "suites-espelho vermelhas pos-apply"
echo "   gates locais verdes"

say "3/7 commit 1 (commit-POR-MANIFESTO: staging literal + re-verificacao)"
# Re-verificacao COMPLETA no momento do staging (rail r8 P1-1: as
# checagens de G0 rodavam antes do prompt/assinatura/apply; um arquivo
# criado depois casaria o prefixo e seria commitado como revisado).
check_rail_and_evidence
check_pack
check_nogo_w3
check_tree_is_exactly_the_prep
# Lista LITERAL de arquivos do commit 1, DERIVADA dos manifestos que
# acabaram de verificar - nenhum `git add` de diretorio (rail r8 P1-1).
_commit1_files() {
  awk '{print $2}' "$PACK/MANIFEST.sha256"
  awk -v p="$PACK/" '{print p $2}' "$PACK/MANIFEST.sha256"
  echo "$PACK/MANIFEST.sha256"; echo "$PACK/BASELINE.sha256"; echo "$PACK/MODES.txt"
  ( cd "$CURES" && find . -maxdepth 1 -type f | sed 's|^\./||' ) | sed "s|^|$CURES/|"
  ( cd "$SCRIPTSR" && find . -maxdepth 1 -type f | sed 's|^\./||' ) | sed "s|^|$SCRIPTSR/|"
  awk -v p="$NOGO/" '{print p $2}' "$NOGO/MANIFEST-NOGO.sha256"
  echo "$NOGO/MANIFEST-NOGO.sha256"
  awk -v p="$P169/staged-w3/" '{print p $2}' "$P169/staged-w3/MANIFEST.sha256"
  echo "$P169/staged-w3/MANIFEST.sha256"; echo "$P169/staged-w3/BASELINE.sha256"
  echo "$P166/OWNER-GA-CUT.sh"
  echo "$P166/OWNER-RC3-CUT.sh"
  echo "$P166/RC3-approved-draft.md"
  echo "$P166/RC3-approved.md"
  echo "$P166/RC3-approved.md.asc"
  echo "$P166/OWNER-MORNING-RC3.md"
  echo "$P166/verdict-fields-v1.3.0-rc.3.TEMPLATE.md"
  echo "$P166/pair-rail-verdict-v1.3.0-rc.3.TEMPLATE.md"
  echo "$P166/verdict-fields-v1.3.0.TEMPLATE.md"
  echo "$P166/pair-rail-verdict-v1.3.0.TEMPLATE.md"
  echo "$P166/repass-ga/run-ga-repass.sh"
  echo "$P169/W3-approved-draft.md"
}
_c1_list="$(_commit1_files | sort -u)"
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  [ -e "$_p" ] || die "arquivo da lista do commit 1 ausente: $_p"
  [ -L "$_p" ] && die "symlink na lista do commit 1: $_p"
  [ -f "$_p" ] || die "nao-regular na lista do commit 1: $_p"
  git add -- "$_p"
done <<C1
$_c1_list
C1
# Asserts do INDEX (rail r8 P1-2): todo caminho staged tem de estar na
# lista literal; nada tracked fora dela pode ter sobrado modificado; e
# nenhum untracked pode restar (status CAPTURADO, rc checado).
_cached="$(git diff --cached --name-only)" || die "git diff --cached falhou"
while IFS= read -r _cp; do
  [ -n "$_cp" ] || continue
  printf '%s\n' "$_c1_list" | grep -qxF "$_cp" \
    || die "caminho staged FORA da lista literal do commit 1: $_cp"
done <<CACHED
$_cached
CACHED
git diff --quiet \
  || die "sobrou mudanca tracked NAO-staged apos o staging literal - investigar"
_st_final="$(git status --porcelain --untracked-files=all)" \
  || die "git status falhou no assert final"
printf '%s\n' "$_st_final" | grep -q '^??' \
  && die "sobrou arquivo untracked apos o staging literal - investigar"
git commit -m "fix(PLAN-166 W2): curas do NO-GO do re-pass GA - corte da rc.3

8 achados reais do hold ADR-103 (10/08): CHANGELOG 188->190 + secao de
upgrade adopter-visivel; matcher escopado do header no verify-counts;
checklist +.framework-version e sem contagem hardcoded de steps; guard
fail-closed de tag-liveness antes do npm publish (delete/re-tag nao
publica arvore obsoleta) + pins de regressao; timeout release-gate
20->35 (licao S300). Espelho no staged-w3 (o W3 nao reverte as curas).
Evidencia: repass-ga-rc2-NOGO/ (NO-GO) + repass-rc3-cures/ (rail GO).
Sentinel: RC3-approved.md assinado (anchor $EXPECTED_HEAD)."
PARENT="$(git rev-parse HEAD)"
printf 'commit 1 = %s\n' "$PARENT"

say "4/7 verdict-fields rc.3 (parent=$PARENT) - revisar e assinar (pinentry 2)"
GEN="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DMS="$(shasum -a 256 "$CURES/MANIFEST-cures.sha256" | awk '{print $1}')"
TSH="$(cat $(ls "$CURES"/transcript-cures-round*.log | sort -V) | shasum -a 256 | awk '{print $1}')"
# Higiene de assinatura (rail r13 P1-1, espelha GA 3/8-4/8): comeca
# limpo, gera via temporario regular + rename atomico.
rm -f "$VF" "$VF.asc" "$VD" "$VF.tmp" "$VD.tmp"
awk 'f{print} /-->/{f=1}' "$VF_TPL" \
  | sed -e "s/@@PARENT_SHA@@/$PARENT/" -e "s/@@GENERATED_AT@@/$GEN/" \
        -e "s/@@DELTA_MANIFEST_SHA@@/$DMS/" -e "s/@@TRANSCRIPT_SHA@@/$TSH/" > "$VF.tmp"
mv -f "$VF.tmp" "$VF"
[ -f "$VF" ] && [ ! -L "$VF" ] || die "verdict-fields gerado nao e arquivo regular"
printf '\n----- CONTEUDO QUE VOCE VAI ASSINAR -----\n'
cat "$VF"
printf -- '----- FIM -----\n\nEnter para assinar (ctrl-C aborta): '; read -r _
rm -f "$VF.asc"
gpg --armor --detach-sign -u "$KEY" "$VF"
gpg --verify "$VF.asc" "$VF" || die "assinatura do verdict-fields nao verifica"

say "5/7 montar verdito + commit 2 + guard local"
SIG="$(base64 < "$VF.asc" | tr -d '\n')"
sed -e "s/@@PARENT_SHA@@/$PARENT/" -e "s/@@GENERATED_AT@@/$GEN/" \
    -e "s/@@DELTA_MANIFEST_SHA@@/$DMS/" -e "s/@@TRANSCRIPT_SHA@@/$TSH/" \
    -e "s|@@SIG_B64@@|$SIG|" "$VD_TPL" > "$VD.tmp"
mv -f "$VD.tmp" "$VD"
# Re-verifica ANTES de mover o .asc e de commitar (rail r13 P1-1): se
# algo trocou o VF entre a assinatura e aqui, para agora.
[ -f "$VD" ] && [ ! -L "$VD" ] || die "verdito gerado nao e arquivo regular"
[ -f "$VF" ] && [ ! -L "$VF" ] || die "verdict-fields deixou de ser regular"
gpg --verify "$VF.asc" "$VF" || die "assinatura NAO verifica pos-geracao do verdito - VF mudou?"
mkdir -p "$HOME/.rc2-backup"
mv "$VF.asc" "$HOME/.rc2-backup/verdict-fields-v1.3.0-rc.3.md.asc"
git add "$VF" "$VD"
git commit -m "governance(PLAN-166 W2): verdito pair-rail v1.3.0-rc.3 assinado

GO-WITH-CONDITIONS: as 4 excecoes herdadas do trem (V1/V2/V4/V5, curas
no pack W3 pos-GA) + curas dos 8 achados do NO-GO do re-pass GA.
Evidencia do rail de curas em repass-rc3-cures/."
python3 .claude/scripts/local/_release_tag_guard.py delta \
  --repo "$REPO" --tag "$TAG" || die "guard delta recusou - NAO pushe"

say "6/7 push + espera CI (15-40 min; deixe rodando)"
git push origin main
HEADSHA="$(git rev-parse HEAD)"
i=0
while :; do
  i=$((i+1)); [ "$i" -le 90 ] || die "CI nao terminou em 90 min"
  sleep 60
  info="$(gh run list --limit 20 --json headSha,status,conclusion \
    --jq "[.[]|select(.headSha==\"$HEADSHA\")] | \
{n:length, p:[.[]|select(.status!=\"completed\")]|length, \
b:[.[]|select(.status==\"completed\" and .conclusion!=\"success\" \
and .conclusion!=\"skipped\")]|length}" 2>/dev/null || echo "")"
  [ -n "$info" ] || { printf '  ... gh falhou, tentando de novo\n'; continue; }
  n="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["n"])')"
  p="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["p"])')"
  b="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["b"])')"
  printf '  ... runs=%s pendentes=%s vermelhos=%s\n' "$n" "$p" "$b"
  [ "$b" -eq 0 ] || die "workflow vermelho - me chame no Claude"
  if [ "$n" -gt 0 ] && [ "$p" -eq 0 ]; then break; fi
done
VID="$(gh run list --workflow validate.yml --limit 20 \
  --json headSha,databaseId,status,conclusion,event,headBranch \
  --jq "[.[]|select(.headSha==\"$HEADSHA\" and .status==\"completed\" and .conclusion==\"success\" and .event==\"push\" and .headBranch==\"main\")][0].databaseId" 2>/dev/null || echo "")"
[ -n "$VID" ] && [ "$VID" != "null" ] || die "nenhum run COMPLETO e success do validate.yml para o HEAD (rail r19 P1-3)"
VJ="$(gh run view "$VID" --json jobs \
  --jq '{s:[.jobs[]|select(.conclusion=="success")]|length, f:[.jobs[]|select(.conclusion=="failure")]|length, p:[.jobs[]|select(.status!="completed")]|length, o:[.jobs[]|select(.status=="completed" and .conclusion!="success" and .conclusion!="skipped")]|length}' 2>/dev/null || echo "")"
vs="$(printf '%s' "$VJ" | python3 -c 'import json,sys;print(json.load(sys.stdin)["s"])')"
vf="$(printf '%s' "$VJ" | python3 -c 'import json,sys;print(json.load(sys.stdin)["f"])')"
vp="$(printf '%s' "$VJ" | python3 -c 'import json,sys;print(json.load(sys.stdin)["p"])')"
vo="$(printf '%s' "$VJ" | python3 -c 'import json,sys;print(json.load(sys.stdin)["o"])')"
[ "$vf" -eq 0 ] || die "job vermelho dentro do validate.yml"
[ "$vp" -eq 0 ] || die "validate.yml selecionado ainda tem job pendente (snapshot incoerente)"
[ "$vo" -eq 0 ] || die "validate.yml tem job terminal nao-success (cancelled/timed_out?)"
[ "$vs" -ge 1 ] || die "validate.yml sem NENHUM job executado (CEO_SOTA_DISABLE?) - me chame no Claude"
echo "   validate.yml: $vs job(s) success, 0 failure (nivel de job)"
bell "CI verde - assinar a tag rc.3"

say "7/7 preflight + tag (pinentry 3) + push + pre-release"
bash .claude/scripts/local/release.sh preflight --rc 3
bash .claude/scripts/local/release.sh tag --rc 3
printf 'push da tag %s e pre-release GitHub? digite SIM (MAIUSCULO): ' "$TAG"
read -r ans
[ "$ans" = "SIM" ] || die "abortado pelo Owner (tag assinada local, nao pushada)"
# Preflight pre-push (rail r11 P1-3): o SIM pode ter ficado aberto -
# recheca tag==HEAD==origin/main, assinatura, arvore limpa, guard e TTL
# do verdito ANTES do push (mesma disciplina do GA-CUT).
git tag -v "$TAG" >/dev/null 2>&1 \
  || die "pre-push: assinatura da tag nao verifica"
[ "$(git rev-parse "$TAG^{commit}")" = "$(git rev-parse HEAD)" ] \
  || die "pre-push: tag nao aponta o HEAD"
git fetch --quiet origin main
[ "$(git rev-parse origin/main)" = "$(git rev-parse HEAD)" ] \
  || die "pre-push: origin/main != HEAD - main andou; me chame no Claude"
_pp_st="$(git status --porcelain --untracked-files=all)" \
  || die "pre-push: git status falhou"
[ -z "$_pp_st" ] || die "pre-push: arvore suja"
python3 .claude/scripts/local/_release_tag_guard.py delta \
  --repo "$REPO" --tag "$TAG" || die "pre-push: guard delta recusou - NAO pushe"
_vf_gen="$(awk '/^generated_at:/{print $2}' "$VF" | tail -1)"
_vf_ttl="$(awk '/^ttl_hours:/{print $2}' "$VF" | tail -1)"
[ -n "$_vf_gen" ] && [ -n "$_vf_ttl" ] || die "pre-push: verdict-fields sem generated_at/ttl"
_vf_epoch="$(python3 - "$_vf_gen" <<'PYVF'
import sys, datetime
try:
    print(int(datetime.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")).timestamp()))
except Exception:
    print("BAD")
PYVF
)"
[ "$_vf_epoch" != "BAD" ] || die "pre-push: generated_at ilegivel"
[ "$(date +%s)" -le $(( _vf_epoch + _vf_ttl * 3600 - 3600 )) ] \
  || die "pre-push: verdito a menos de 1h do TTL (ou expirado) - NAO pushe; me chame no Claude"
echo "   pre-push preflight: verde"
_TAG_PUSH_EPOCH="$(date +%s)"
git push origin "$TAG"
printf 'esperando release.yml da tag...\n'
TAGSHA="$(git rev-parse "$TAG^{commit}")"
i=0
while :; do
  # 60 > fila + gate 35 + publish-release (rail r6-produto P1-2).
  i=$((i+1)); [ "$i" -le 60 ] || die "release.yml nao terminou em 60 min - re-rode (a tag ja pushada e re-verificada na retomada)"
  sleep 60
  c="$(gh run list --workflow release.yml --limit 10 \
    --json headSha,status,conclusion,headBranch,event \
    --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].conclusion" 2>/dev/null || echo "")"
  s="$(gh run list --workflow release.yml --limit 10 \
    --json headSha,status,conclusion,headBranch,event \
    --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].status" 2>/dev/null || echo "")"
  printf '  ... release.yml: %s/%s\n' "${s:-?}" "${c:-?}"
  [ "$c" = "failure" ] && die "release.yml vermelho - me chame no Claude"
  [ "$s" = "completed" ] && [ "$c" = "success" ] && break
done
printf 'esperando o job await-release-gate do npm-publish.yml (controle positivo)...\n'
i=0
while :; do
  i=$((i+1)); [ "$i" -le 30 ] || die "await-release-gate nao concluiu em 30 min"
  sleep 60
  NID="$(gh run list --workflow npm-publish.yml --limit 10 \
    --json headSha,databaseId,headBranch,event \
    --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].databaseId" 2>/dev/null || echo "")"
  if [ -z "$NID" ] || [ "$NID" = "null" ]; then
    printf '  ... run do npm-publish ainda nao apareceu\n'; continue
  fi
  AC="$(gh run view "$NID" --json jobs \
    --jq '[.jobs[]|select(.name|startswith("Await release-gate"))][0].conclusion' 2>/dev/null || echo "")"
  printf '  ... await-release-gate: %s\n' "${AC:-pendente}"
  [ "$AC" = "failure" ] && die "await-release-gate FALHOU na rc - me chame no Claude"
  [ "$AC" = "success" ] && break
done
echo "   controle positivo do npm-gate: verde"
# publishedAt tem de ser DESTA cerimonia (rail r27 P1-2).
_pub_now="$(gh release view "$TAG" --json publishedAt --jq .publishedAt 2>/dev/null || echo "")"
[ -n "$_pub_now" ] || die "pre-release sem publishedAt"
_pub_ep="$(python3 - "$_pub_now" <<'PYPB'
import sys, datetime
try:
    print(int(datetime.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")).timestamp()))
except Exception:
    print("BAD")
PYPB
)"
[ "$_pub_ep" != "BAD" ] || die "publishedAt ilegivel"
[ "$_pub_ep" -ge $(( _TAG_PUSH_EPOCH - 300 )) ] \
  || die "publishedAt do pre-release e ANTERIOR a esta cerimonia (release stale?) - me chame no Claude"
_prj="$(gh release view "$TAG" --json isPrerelease,isDraft 2>/dev/null || echo "")"
_pr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
_dr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
{ [ "$_pr" = "True" ] && [ "$_dr" = "False" ]; } \
  || die "GitHub Release da $TAG ausente, draft ou sem flag pre-release (pre='$_pr' draft='$_dr') - o hold ADR-103 conta de release PUBLICO (rail r11 P1-4); me chame no Claude"
echo "   GitHub pre-release confirmado NAO-draft (criado pelo release.yml)"

# Recheck do OBJETO da tag no remoto (rail r21 P1-3): a tag nao pode
# ter sido deletada/movida durante as esperas.
_ft_rls="$(git ls-remote origin "refs/tags/$TAG" "refs/tags/$TAG^{}")" \
  || die "ls-remote final da tag falhou (transporte)"
_ft_plain="$(printf '%s\n' "$_ft_rls" | awk -v r="refs/tags/$TAG" '$2==r{print $1}')"
_ft_peel="$(printf '%s\n' "$_ft_rls" | awk -v r="refs/tags/$TAG^{}" '$2==r{print $1}')"
[ "$_ft_plain" = "$(git rev-parse "$TAG")" ] \
  || die "tag $TAG remota NAO e mais o objeto assinado local (deletada/movida durante as esperas?) - me chame no Claude"
[ -z "$_ft_peel" ] || [ "$_ft_peel" = "$(git rev-parse "$TAG^{commit}")" ] \
  || die "peel remoto final da tag diverge - me chame no Claude"
bell "rc.3 cortada - hold reinicia"
cat <<'DONE'

============================================================
 rc.3 CORTADA. MAIN CONGELADO ate o GA.
 - Hold ADR-103: >= 24h a partir do publishedAt da rc.3.
 - Depois do hold: bash .claude/plans/PLAN-166/OWNER-GA-CUT.sh
   (ja aponta para a rc.3; o re-pass do hold roda de novo sobre
   a arvore CURADA - os 8 achados do NO-GO estao curados nela).
 - Me chame no Claude para o fechamento da sessao.
============================================================
DONE
