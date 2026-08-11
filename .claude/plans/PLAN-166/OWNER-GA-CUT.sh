#!/bin/bash
# OWNER-GA-CUT.sh - promocao v1.3.0-rc.3 -> GA v1.3.0 em UM comando.
# (o freeze do main comeca no CORTE DA rc.3 - rail rc.3 r5 P2)
#
#   bash .claude/plans/PLAN-166/OWNER-GA-CUT.sh
#
# Pre-requisito: rc.3 cortada ha >= 24h (hold ADR-103). O script:
# (rc.3 = rc.2 + curas dos 8 achados do re-pass NO-GO de 10/08; ver
#  OWNER-RC3-CUT.sh e repass-ga-rc2-NOGO/TRIAGE-ga-repass.md)
#   1. valida janela do hold + freeze (origin/main == commit da rc.3)
#   2. roda o re-pass do hold (codex, ~10-15 min) se ainda nao rodou;
#      exige VERDICT: GO ou GO-WITH-CONDITIONS (NO-GO => aborta)
#   3. commit 1: evidencia do re-pass (repass-ga/**)
#   4. gera verdict-fields GA e voce assina (pinentry 1)
#   5. monta o verdito GA, commit 2, guard local, push, espera CI
#   6. preflight --stable + bump --stable (no-op esperado) +
#      tag v1.3.0 assinada (pinentry 2)
#   7. push da tag (confirmacao SIM) + espera release.yml + npm:
#      aprovacao production-npm e SUA no browser (o script te da o link)
#   8. GitHub Release (SEM pre-release) + npm view
# Depois do GA: assinar W3 e rodar OWNER-W3-LAND.sh (curas V1-V5).
set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"; cd "$REPO"
RC_TAG="v1.3.0-rc.3"
TAG="v1.3.0"
KEY="CFCFACF00335DC74"
P166=".claude/plans/PLAN-166"
GA_DIR="$P166/repass-ga"
VF="$P166/verdict-fields-v1.3.0.md"
VD=".claude/governance/pair-rail-verdict-v1.3.0.md"
VF_TPL="$P166/verdict-fields-v1.3.0.TEMPLATE.md"
VD_TPL="$P166/pair-rail-verdict-v1.3.0.TEMPLATE.md"

say() { printf '\n== %s\n' "$*"; }
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
bell() { printf '\a'; osascript -e "display notification \"$1\" with title \"GA v1.3.0\"" 2>/dev/null || true; }

GPG_TTY="$(tty 2>/dev/null || true)"; export GPG_TTY
gpgconf --kill gpg-agent 2>/dev/null || true

say "G0 pre-condicoes"
# Orfao do manifesto atomico do runner (rail r22 P1-1): removido antes
# da checagem de arvore; symlink = erro.
if [ -e "$GA_DIR/MANIFEST-ga.sha256.tmp" ] || [ -L "$GA_DIR/MANIFEST-ga.sha256.tmp" ]; then
  [ -L "$GA_DIR/MANIFEST-ga.sha256.tmp" ] && die "MANIFEST-ga.sha256.tmp e SYMLINK"
  [ -f "$GA_DIR/MANIFEST-ga.sha256.tmp" ] || die "MANIFEST-ga.sha256.tmp nao-regular"
  rm -f "$GA_DIR/MANIFEST-ga.sha256.tmp"
  echo "   (limpo) orfao MANIFEST-ga.sha256.tmp"
fi
# Quarentena de payloads raw ANTES de qualquer checagem de arvore (rail
# r14 P2: SIGKILL/queda de energia pula o trap EXIT do runner; sem isso
# a fase de evidencia nao e auto-retomavel). Symlink = erro, nao move.
for _raw in "$GA_DIR"/payload-ga-*.raw.txt; do
  [ -e "$_raw" ] || continue
  [ -L "$_raw" ] && die "payload raw e SYMLINK: $_raw"
  [ -f "$_raw" ] || die "payload raw nao-regular: $_raw"
  mkdir -p "$HOME/.rc2-backup"
  mv "$_raw" "$HOME/.rc2-backup/quarantine-$(date +%s)-$(basename "$_raw")" \
    || die "quarentena do raw falhou: $_raw"
  echo "   quarentena: $(basename "$_raw") -> ~/.rc2-backup/"
done
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] \
  || die "nao esta em main (branch/detached) - r6-P2 do rail"
git rev-parse -q --verify "refs/tags/$RC_TAG" >/dev/null 2>&1 || die "tag $RC_TAG nao existe"
# Tag GA ja existente NAO e mais morte automatica (rail rc.3 r6 P1-5):
# um timeout do monitoramento DEPOIS do push da tag deixava rerun
# impossivel. Se a tag local aponta o HEAD e o remoto bate, entramos em
# modo MONITORAMENTO (pula direto para as esperas de release/npm).
MONITOR_ONLY=0
# Remoto consultado INCONDICIONALMENTE antes de qualquer mutacao (rail
# r13 P1-2): uma tag GA remota sem ref local deixaria o script commitar
# e pushar main para so entao falhar no push da tag.
_ga_rls="$(git ls-remote origin "refs/tags/$TAG" "refs/tags/$TAG^{}")" \
  || die "git ls-remote da tag GA falhou (transporte)"
if [ -n "$_ga_rls" ] && ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1; then
  die "tag $TAG existe no REMOTO mas nao localmente - estado incoerente; me chame no Claude:
$_ga_rls"
fi
# Release GA orfao com REMOTO sem tag (rail r29 P1-3 + r30 P1-1):
# independente de tag local, se a tag nao esta no remoto o Release nao
# pode existir - um SKIP_TO_PUSH re-pushando sobre Release stale
# reusaria titulo/notes velhos.
if [ -z "$_ga_rls" ]; then
  if _gaorf="$(gh release view "$TAG" --json name 2>&1)"; then
    die "Release do $TAG existe SEM tag remota (orfao/stale de tentativa anterior) - gh release delete $TAG apos triagem; me chame no Claude"
  fi
  printf '%s' "$_gaorf" | grep -qi "not found\|release not found\|HTTP 404" \
    || die "gh release view do GA falhou sem ser NOT-FOUND (API?): $_gaorf"
fi
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1; then
  _tagc="$(git rev-parse "$TAG^{commit}")"
  _tago="$(git rev-parse "$TAG")"
  [ "$_tagc" = "$(git rev-parse HEAD)" ] \
    || die "tag $TAG existe e NAO aponta o HEAD - me chame no Claude"
  git tag -v "$TAG" >/dev/null 2>&1 \
    || die "assinatura da tag $TAG local nao verifica - me chame no Claude"
  # OBJETO exato, nao commit peelado (rail r14 P1-1): um delete/re-tag
  # lightweight/re-anotado no MESMO commit passaria pelo peel.
  _rt_plain="$(printf '%s\n' "$_ga_rls" | awk -v r="refs/tags/$TAG" '$2==r{print $1}')"
  _rt_peel="$(printf '%s\n' "$_ga_rls" | awk -v r="refs/tags/$TAG^{}" '$2==r{print $1}')"
  if [ -n "$_rt_plain" ]; then
    [ "$_rt_plain" = "$_tago" ] \
      || die "tag $TAG remota NAO e o mesmo OBJETO assinado local ($_rt_plain != $_tago) - delete/re-tag?; me chame no Claude"
    [ -z "$_rt_peel" ] || [ "$_rt_peel" = "$_tagc" ] \
      || die "peel remoto da tag $TAG diverge do commit local"
    MONITOR_ONLY=1
    # Monitor e read-only: exige arvore LIMPA e origin/main == HEAD ==
    # commit da tag (rail r20 P1-3/P1-4) - um rollback de main ou lixo
    # local nao pode ser monitorado como se fosse o GA.
    _mo_st="$(git status --porcelain --untracked-files=all)" \
      || die "monitor: git status falhou"
    [ -z "$_mo_st" ] || die "monitor: arvore suja - o modo monitoramento e read-only; limpe antes"
    git fetch --quiet origin main || die "monitor: fetch falhou"
    [ "$(git rev-parse origin/main)" = "$(git rev-parse HEAD)" ] \
      || die "monitor: origin/main != HEAD - main andou/rolou; me chame no Claude"
    echo "   tag $TAG ja assinada e pushada (OBJETO coerente) - modo MONITORAMENTO (read-only)"
  else
    SKIP_TO_PUSH=1
    echo "   tag $TAG assinada local e ainda nao pushada - retomada VIA prompt SIM (mesma cerimonia)"
  fi
fi
RC_SHA="$(git rev-parse "$RC_TAG^{commit}")"
# Hold medido do EVENTO PUBLICADO, nao do tag local (pair-rail S300 r8
# P1-1): um corte que parou antes do push deixaria taggerdate local
# valido sem NENHUMA rc publica. Exige: tag no remoto apontando o mesmo
# SHA + pre-release publicado; hold conta de publishedAt.
# UM snapshot; OBJETO plain == tag local assinada, peel == commit
# (rail r14 P1-1) + assinatura verificada.
git tag -v "$RC_TAG" >/dev/null 2>&1 \
  || die "assinatura da tag $RC_TAG local nao verifica - me chame no Claude"
_rc_rls="$(git ls-remote origin "refs/tags/$RC_TAG" "refs/tags/$RC_TAG^{}")" \
  || die "git ls-remote da $RC_TAG falhou (transporte)"
_rc_plain="$(printf '%s\n' "$_rc_rls" | awk -v r="refs/tags/$RC_TAG" '$2==r{print $1}')"
_rc_peel="$(printf '%s\n' "$_rc_rls" | awk -v r="refs/tags/$RC_TAG^{}" '$2==r{print $1}')"
[ "$_rc_plain" = "$(git rev-parse "$RC_TAG")" ] \
  || die "tag $RC_TAG remota nao e o mesmo OBJETO assinado local - a rc publicada nao e a assinada; me chame no Claude"
[ -z "$_rc_peel" ] || [ "$_rc_peel" = "$RC_SHA" ] \
  || die "peel remoto da $RC_TAG diverge do commit local"
RC_PREJ="$(gh release view "$RC_TAG" --json isPrerelease,isDraft 2>/dev/null || echo "")"
RC_PRE="$(printf '%s' "$RC_PREJ" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
RC_DR="$(printf '%s' "$RC_PREJ" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
{ [ "$RC_PRE" = "True" ] && [ "$RC_DR" = "False" ]; } \
  || die "pre-release da $RC_TAG ausente, draft ou nao-prerelease (pre='$RC_PRE' draft='$RC_DR') - o hold conta de release PUBLICO; me chame no Claude"
PUBAT="$(gh release view "$RC_TAG" --json publishedAt --jq .publishedAt 2>/dev/null || echo "")"
[ -n "$PUBAT" ] || die "sem publishedAt no release da $RC_TAG"
PUB_EPOCH="$(python3 - "$PUBAT" <<'PYEOF'
import sys, datetime
ts = sys.argv[1].replace("Z", "+00:00")
print(int(datetime.datetime.fromisoformat(ts).timestamp()))
PYEOF
)"
NOW="$(date +%s)"
HOLD=$(( NOW - PUB_EPOCH ))
[ "$HOLD" -ge 86400 ] || die "hold ADR-103 incompleto: $((HOLD/3600))h < 24h desde o pre-release publicado - volte mais tarde"
# Controle positivo da rc RE-verificado aqui (rail r18 P1): o corte da
# rc pode ter abortado DEPOIS do pre-release publico com o job
# await-release-gate vermelho/timeout - o GA nao pode promover sobre um
# caminho de publish nunca validado.
_pcn="$(gh run list --workflow npm-publish.yml --limit 30 \
  --json headSha,databaseId,headBranch,event \
  --jq "[.[]|select(.headSha==\"$RC_SHA\" and .headBranch==\"$RC_TAG\" and .event==\"push\")][0].databaseId" 2>/dev/null || echo "")"
[ -n "$_pcn" ] && [ "$_pcn" != "null" ] \
  || die "nenhum run do npm-publish.yml para a $RC_TAG ($RC_SHA) - controle positivo ausente; me chame no Claude"
_pca="$(gh run view "$_pcn" --json jobs \
  --jq '[.jobs[]|select(.name|startswith("Await release-gate"))][0].conclusion' 2>/dev/null || echo "")"
[ "$_pca" = "success" ] \
  || die "controle positivo await-release-gate da rc NAO e success ('$_pca') - o corte da rc terminou sem validar o caminho de publish; me chame no Claude"
echo "   controle positivo da rc: await-release-gate success (recibo re-verificado)"
git fetch --quiet origin main
# Estados legitimos (pair-rail S300 r13 P2 — retomada real): HEAD ==
# a rc do trem (fresh), ou HEAD descendente dela cujo delta contem SO
# evidencia do hold + artefatos do verdito GA (interrompido apos o
# commit 2/4). origin/main pode ser rc.2 (pre-push) ou o proprio HEAD
# (interrompido apos o push). Qualquer outra coisa = freeze violado.
# Conjunto FECHADO das saidas do runner do re-pass (definido ANTES da
# checagem de retomada, que o consome — rail rc.3 r5).
GA_OUT_OK="payload-ga-1.redacted.txt payload-ga-2.redacted.txt
diff-ga-1.patch diff-ga-2.patch
paths-ga-1.manifest.txt paths-ga-2.manifest.txt
verdict-ga-1.txt verdict-ga-2.txt
transcript-ga-1.log transcript-ga-2.log
PROVENANCE-ga.md MANIFEST-ga.sha256"
HEADNOW="$(git rev-parse HEAD)"
if [ "$HEADNOW" != "$RC_SHA" ]; then
  git merge-base --is-ancestor "$RC_SHA" "$HEADNOW" \
    || die "HEAD nao descende do commit da rc - me chame no Claude"
  # --no-renames + saida CAPTURADA com rc checado (rail rc.3 r5 P1-1:
  # rename-aware podia reportar so o destino permitido de um rename
  # produto->evidencia, e um git falhando dentro de heredoc virava
  # delta vazio = aprovacao falsa). Conjunto FECHADO: so os filhos
  # DIRETOS nomeados em GA_OUT_OK + VF + VD.
  _delta_out="$(git diff --no-renames --name-only "$RC_SHA"..HEAD)" \
    || die "git diff do delta de retomada falhou - nao vou tratar como vazio"
  _bad_delta=""
  while IFS= read -r _dp; do
    [ -n "$_dp" ] || continue
    if [ "$_dp" = "$VF" ] || [ "$_dp" = "$VD" ]; then continue; fi
    case "$_dp" in
      "$GA_DIR"/*)
        _rel="${_dp#"$GA_DIR"/}"
        _okp=0
        case "$_rel" in
          */) : ;;
          */*) : ;;
          *) for _b in $GA_OUT_OK; do
               [ "$_rel" = "$_b" ] && { _okp=1; break; }
             done ;;
        esac
        [ "$_okp" -eq 1 ] || _bad_delta="$_bad_delta
   $_dp" ;;
      *) _bad_delta="$_bad_delta
   $_dp" ;;
    esac
  done <<GADELTA
$_delta_out
GADELTA
  [ -z "$_bad_delta" ] \
    || die "delta rc..HEAD contem caminho fora do conjunto FECHADO de evidencia/verdito GA (freeze violado):$_bad_delta"
  echo "   modo RETOMADA: commits locais contem so evidencia/verdito GA (conjunto fechado, --no-renames)"
fi
OM="$(git rev-parse origin/main)"
[ "$OM" = "$RC_SHA" ] || [ "$OM" = "$HEADNOW" ] \
  || die "origin/main nao e a rc.2 nem o HEAD da retomada - freeze violado; me chame no Claude"
# Arvore limpa EXCETO o conjunto FECHADO de saidas do runner do re-pass
# (pair-rail S300 r11 P2: uma invocacao que rodou o re-pass e parou
# antes do commit deixa esses untracked — o reuso precisa alcanca-los).
# status CAPTURADO com rc checado (rail r9 P1-2: falha dentro de
# heredoc-substitution virava "arvore limpa").
_ga_st_out="$(git status --porcelain --untracked-files=all)" \
  || die "git status falhou - nao vou tratar como arvore limpa"
_dirty=""
while IFS= read -r _line; do
  [ -n "$_line" ] || continue
  _pathp="${_line#???}"
  case "$_pathp" in
    "$VF.tmp"|"$VD.tmp")
      # Orfaos de uma geracao atomica interrompida (rail r11 P1-2):
      # removidos aqui mesmo (symlink rejeitado antes de remover).
      [ -L "$_pathp" ] && die "temporario de assinatura e SYMLINK: $_pathp"
      rm -f "$_pathp"
      echo "   (limpo) temporario orfao: $_pathp"
      : ;;
    "$VF"|"$VF.asc"|"$VD")
      # Estado parcial de assinatura de uma retomada (rail rc.3 r6
      # P1-3): os tres artefatos sao integralmente REGENERADOS nos
      # passos 3-4 (que comecam com rm -f), entao presenca suja aqui e
      # retomavel. SYMLINK nao (rail r10 P1-1): um $VD -> $VF faria a
      # geracao do verdito SOBRESCREVER o verdict-fields ja assinado.
      [ -L "$_pathp" ] && die "artefato de assinatura e SYMLINK: $_pathp - remova antes"
      : ;;
    "$GA_DIR"/*)
      # SO filhos DIRETOS do dir de evidencia contam (r14 P2: um
      # look-alike aninhado tipo repass-ga/rehearsal/verdict-ga-1.txt
      # cairia no git add do commit 1 e o guard de delta, ancorado no
      # PARENT pos-commit, nunca o veria).
      _rel="${_pathp#"$GA_DIR"/}"
      case "$_rel" in
        */*) _dirty="$_dirty
   $_pathp" ;;
        *)
          _okp=0
          for _b in $GA_OUT_OK; do
            [ "$_rel" = "$_b" ] && { _okp=1; break; }
          done
          [ "$_okp" -eq 1 ] || _dirty="$_dirty
   $_pathp"
          ;;
      esac
      ;;
    *) _dirty="$_dirty
   $_pathp" ;;
  esac
done <<GASTATUS
$_ga_st_out
GASTATUS
[ -z "$_dirty" ] || die "arvore suja fora do conjunto de saidas do re-pass:$_dirty"
command -v gh >/dev/null 2>&1 || die "gh ausente"
[ -f "$VF_TPL" ] && [ -f "$VD_TPL" ] || die "templates GA ausentes"
PIN_JSON="$(python3 .claude/hooks/check_pair_rail.py --verify-codex-pin 2>/dev/null || true)"
printf '%s' "$PIN_JSON" | grep -q '"status": "verified"' || die "pin do codex nao verifica"
printf '%s' "$PIN_JSON" | grep -q '80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff' \
  || die "sha do payload codex mudou - re-gerar templates antes de assinar"

validate_ga_evidence() {
  [ -f "$GA_DIR/verdict-ga-1.txt" ] && [ -f "$GA_DIR/verdict-ga-2.txt" ] || return 1
  ( cd "$GA_DIR" && shasum -a 256 -c MANIFEST-ga.sha256 --status ) 2>/dev/null || return 1
  # Conjunto EXATO de 11 basenames (rail r20 P1-1): um manifesto
  # parcial-mas-valido de uma escrita interrompida nao passa.
  _vm_have="$(awk '{print $2}' "$GA_DIR/MANIFEST-ga.sha256" | sort)"
  _vm_want="$(printf '%s\n' $GA_OUT_OK | grep -v '^MANIFEST-ga.sha256$' | sort)"
  [ "$_vm_have" = "$_vm_want" ] || return 1
  grep -q "$RC_SHA" "$GA_DIR/PROVENANCE-ga.md" 2>/dev/null || return 1
  grep -q "Tag: $RC_TAG" "$GA_DIR/PROVENANCE-ga.md" 2>/dev/null || return 1
  # Base pinada na evidencia (rail r23/r24): o reuso exige a linha Base
  # com os objetos LITERAIS revisados da v1.2.0.
  grep -q "abbb39eba5e5b83c7da6a817c4cf0ee033b5c266" "$GA_DIR/PROVENANCE-ga.md" 2>/dev/null || return 1
  grep -q "31c5026a37451a577cde8f60ed95306ee0cd8894" "$GA_DIR/PROVENANCE-ga.md" 2>/dev/null || return 1
  grep -q "^RUNNER-OVERALL: rc=0$" "$GA_DIR/PROVENANCE-ga.md" 2>/dev/null || return 1
  # Exatamente 2 pins 64-hex de payload raw (rail r13 P1-3): um shasum
  # falhando no runner nao pode virar proveniencia semanticamente vazia.
  _npin="$(grep -cE "pin sha256: [0-9a-f]{64}$" "$GA_DIR/PROVENANCE-ga.md" 2>/dev/null || true)"
  [ "$_npin" = "2" ] || return 1
  # Binding TEMPORAL (rail r9 P1-1): a Data de inicio do runner tem de
  # cair DEPOIS do hold completo (publishedAt + 24h) e nunca no futuro
  # - um re-pass rodado antes do fim do hold nao vale como o re-pass
  # do hold, por mais GO que seja.
  _ev_ts="$(awk '/^- Data: /{print $3}' "$GA_DIR/PROVENANCE-ga.md" | tail -1)"
  [ -n "$_ev_ts" ] || return 1
  _ev_epoch="$(python3 - "$_ev_ts" <<'PYTS'
import sys, datetime
try:
    ts = sys.argv[1].replace("Z", "+00:00")
    print(int(datetime.datetime.fromisoformat(ts).timestamp()))
except Exception:
    print("BAD")
PYTS
)"
  [ "$_ev_epoch" != "BAD" ] || return 1
  [ "$_ev_epoch" -ge $(( PUB_EPOCH + 86400 )) ] || return 1
  [ "$_ev_epoch" -le $(( $(date +%s) + 300 )) ] || return 1
  _vo="$( cd "$GA_DIR" && find . ! -type f ! -type d | head -3 )"
  [ -z "$_vo" ] || return 1
  _vs="$( cd "$GA_DIR" && find . -mindepth 2 | head -3 )"
  [ -z "$_vs" ] || return 1
  _vd="$( cd "$GA_DIR" && find . -maxdepth 1 -type f | sed 's|^\./||' | sort )"
  _vw="$( { printf '%s\n' $GA_OUT_OK; echo "run-ga-repass.sh"; } | sort )"
  [ "$_vd" = "$_vw" ] || return 1
  return 0
}

# Modo MONITORAMENTO e estritamente READ-ONLY (rail r20 P1-3): pula
# runner e commits — evidencia ja esta commitada na arvore taggeada.
if [ "$MONITOR_ONLY" -eq 0 ]; then

say "1/8 re-pass do hold"
# UMA funcao de validacao de evidencia, chamada tanto na decisao de
# reuso quanto INCONDICIONALMENTE apos o runner (rail rc.3 r8 P1-4: um
# runner stale/re-apontado podia revisar a rc errada e seguir para a
# assinatura sem nenhum assert pos-execucao).
if validate_ga_evidence; then
  echo "   verditos existentes com proveniencia pinada da $RC_TAG ($RC_SHA) - reusando"
else
  bash "$GA_DIR/run-ga-repass.sh" \
    || die "re-pass do hold nao terminou GO limpo (rc!=0) - triagem comigo no Claude"
  validate_ga_evidence \
    || die "evidencia POS-runner invalida (tag/SHA/manifesto/conjunto) - runner stale ou re-pass incompleto; me chame no Claude"
fi
# SO "VERDICT: GO" exato segue automatico (pair-rail S300 r2 P1-2):
# um GO-WITH-CONDITIONS do rail carrega condicao NOVA que o envelope
# pre-escrito (so as 4 excecoes herdadas) NAO contem — assinar sem
# triagem omitiria a condicao da decisao assinada. Nesse caso: pare,
# me chame no Claude, triamos e REGERAMOS o envelope antes de assinar.
for _vp in 1 2; do
  _vn="$(grep -cE '^VERDICT:' "$GA_DIR/verdict-ga-$_vp.txt" 2>/dev/null || true)"
  [ "$_vn" = "1" ] \
    || die "verdict-ga-$_vp tem $_vn linhas VERDICT (exigido: exatamente 1) - ambiguo (rail r11 P1-1)"
  VLINE="$(grep -E '^VERDICT:' "$GA_DIR/verdict-ga-$_vp.txt")"
  echo "   rail parte $_vp: ${VLINE:-sem verdito}"
  case "$VLINE" in
    "VERDICT: GO") : ;;
    *) die "re-pass parte $_vp: '$VLINE' != GO exato - triagem comigo no Claude (envelope sera regerado se houver condicao nova)" ;;
  esac
done

say "2/8 commit 1 (evidencia do hold)"
ls "$GA_DIR"/payload-ga-*.raw.txt >/dev/null 2>&1 && die "payload raw ainda na arvore (a quarentena do G0 devia ter movido)"
# Fechamento FISICO do dir de evidencia (rail rc.3 r6 P1-2): rejeita
# nao-regular (symlink redirecionaria verdict/payload e -f/shasum/git
# add seguem o link), rejeita aninhado, exige conjunto EXATO de filhos
# diretos = GA_OUT_OK + o runner rastreado.
_ga_odd="$( cd "$GA_DIR" && find . ! -type f ! -type d | head -5 )"
[ -z "$_ga_odd" ] || die "entrada NAO-regular em repass-ga: $_ga_odd"
_ga_sub="$( cd "$GA_DIR" && find . -mindepth 2 | head -5 )"
[ -z "$_ga_sub" ] || die "aninhado em repass-ga (look-alike?): $_ga_sub"
_ga_disk="$( cd "$GA_DIR" && find . -maxdepth 1 -type f | sed 's|^\./||' | sort )"
_ga_want="$( { printf '%s\n' $GA_OUT_OK; echo "run-ga-repass.sh"; } | sort )"
[ "$_ga_disk" = "$_ga_want" ] || die "conjunto em repass-ga difere do fechado:
$(diff <(printf '%s\n' "$_ga_want") <(printf '%s\n' "$_ga_disk") | sed 's/^/   /')"
# VF/VD de uma retomada nao podem ser varridos para o commit de
# evidencia (r6 P1-3): tira do index e commita com PATHSPEC do dir.
git reset -q -- "$VF" "$VD" 2>/dev/null || true
for _b in $GA_OUT_OK; do
  git add -- "$GA_DIR/$_b"
done
git add -- "$GA_DIR/run-ga-repass.sh"
if git diff --cached --quiet -- "$GA_DIR"; then
  echo "   evidencia ja commitada (rerun)"
else
  git commit -m "docs(PLAN-166 W2): evidencia do re-pass do hold ADR-103 (GA v1.3.0)" -- "$GA_DIR"
fi
PARENT="$(git rev-parse HEAD)"

if [ "${SKIP_TO_PUSH:-0}" -eq 0 ]; then

say "3/8 verdict-fields GA (parent=$PARENT) - revisar e assinar (pinentry 1)"
# Comeca LIMPO (rail r10 P1-1): remove qualquer resto/symlink dos tres
# artefatos - eles sao integralmente regenerados neste passo e no 4/8.
rm -f "$VF" "$VF.asc" "$VD" "$VF.tmp" "$VD.tmp"
GEN="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DMS="$(shasum -a 256 "$GA_DIR/MANIFEST-ga.sha256" | awk '{print $1}')"
TSH="$(cat "$GA_DIR/transcript-ga-1.log" "$GA_DIR/transcript-ga-2.log" | shasum -a 256 | awk '{print $1}')"
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
gpg --verify "$VF.asc" "$VF" || die "assinatura nao verifica"

say "4/8 verdito GA + commit 2 + guard local"
SIG="$(base64 < "$VF.asc" | tr -d '\n')"
sed -e "s/@@PARENT_SHA@@/$PARENT/" -e "s/@@GENERATED_AT@@/$GEN/" \
    -e "s/@@DELTA_MANIFEST_SHA@@/$DMS/" -e "s/@@TRANSCRIPT_SHA@@/$TSH/" \
    -e "s|@@SIG_B64@@|$SIG|" "$VD_TPL" > "$VD.tmp"
mv -f "$VD.tmp" "$VD"
# Pos-geracao do VD, RE-verifica a assinatura contra o VF em disco e a
# regularidade dos dois (rail r10 P1-1): se algo tocou o VF entre a
# assinatura e aqui, para ANTES de mover o .asc e de commitar.
[ -f "$VD" ] && [ ! -L "$VD" ] || die "verdito gerado nao e arquivo regular"
[ -f "$VF" ] && [ ! -L "$VF" ] || die "verdict-fields deixou de ser regular"
gpg --verify "$VF.asc" "$VF" || die "assinatura NAO verifica pos-geracao do verdito - VF mudou?"
mkdir -p "$HOME/.rc2-backup"
mv "$VF.asc" "$HOME/.rc2-backup/verdict-fields-v1.3.0.md.asc"
git add "$VF" "$VD"
git commit -m "governance(PLAN-166 W2): verdito pair-rail GA v1.3.0 assinado

GO-WITH-CONDITIONS: 4 excecoes nomeadas carregadas do trem rc.2->rc.3
(curas no pack W3 pos-GA). Re-pass do hold ADR-103 em repass-ga/."
python3 .claude/scripts/local/_release_tag_guard.py delta \
  --repo "$REPO" --tag "$TAG" || die "guard delta recusou - NAO pushe"

say "5/8 push + espera CI"
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
# Nivel de JOB no validate.yml (r10 P1-1 - envelope verde com jobs
# pulados por CEO_SOTA_DISABLE nao autoriza tag).
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
bell "CI verde - assinar a tag GA"

say "6/8 preflight + bump (no-op) + tag GA (pinentry 2)"
bash .claude/scripts/local/release.sh preflight --stable
bash .claude/scripts/local/release.sh bump --stable
bash .claude/scripts/local/release.sh tag --stable

fi

fi

if [ "$MONITOR_ONLY" -eq 0 ]; then
say "7/8 push da tag + release.yml + npm"
# Preflight pre-push UNICO (rail r10 P1-2 + r11 P1-3): roda DEPOIS do
# SIM e imediatamente antes de TODO push de tag - caminho normal E
# retomada. Um prompt SIM deixado aberto ate o TTL do verdito, ou um
# main que andou, para AQUI, nao no server.
prepush_preflight() {
  git tag -v "$TAG" >/dev/null 2>&1 \
    || die "pre-push: assinatura da tag nao verifica - me chame no Claude"
  [ "$(git rev-parse "$TAG^{commit}")" = "$(git rev-parse HEAD)" ] \
    || die "pre-push: tag nao aponta o HEAD"
  git fetch --quiet origin main
  [ "$(git rev-parse origin/main)" = "$(git rev-parse HEAD)" ] \
    || die "pre-push: origin/main != HEAD - main andou; me chame no Claude"
  _rp_st="$(git status --porcelain --untracked-files=all)" \
    || die "pre-push: git status falhou"
  [ -z "$_rp_st" ] || die "pre-push: arvore suja - limpe antes do push"
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
  # margem de 1h para a duracao do release: um verdito a minutos do TTL
  # expiraria com o release.yml no meio do voo.
  [ "$(date +%s)" -le $(( _vf_epoch + _vf_ttl * 3600 - 3600 )) ] \
    || die "pre-push: verdito a menos de 1h do TTL (ou expirado) - NAO pushe; me chame no Claude (rota: regenerar verdito/tag)"
  _rvid="$(gh run list --workflow validate.yml --limit 20 \
    --json headSha,databaseId,status,conclusion,event,headBranch \
    --jq "[.[]|select(.headSha==\"$(git rev-parse HEAD)\" and .status==\"completed\" and .conclusion==\"success\" and .event==\"push\" and .headBranch==\"main\")][0].databaseId" 2>/dev/null || echo "")"
  [ -n "$_rvid" ] && [ "$_rvid" != "null" ] || die "pre-push: nenhum run do validate.yml para o HEAD"
  _rvj="$(gh run view "$_rvid" --json jobs \
    --jq '{s:[.jobs[]|select(.conclusion=="success")]|length, f:[.jobs[]|select(.conclusion=="failure")]|length}' 2>/dev/null || echo "")"
  _rvs="$(printf '%s' "$_rvj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["s"])')"
  _rvf="$(printf '%s' "$_rvj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["f"])')"
  [ "$_rvf" -eq 0 ] && [ "$_rvs" -ge 1 ] \
    || die "pre-push: validate.yml nao esta verde ao nivel de job para o HEAD"
  # Re-snapshot da RC tag (rail r24-2): a rc publica nao pode ter sido
  # deletada/movida entre o G0 e este ponto.
  _rp_rls="$(git ls-remote origin "refs/tags/$RC_TAG" "refs/tags/$RC_TAG^{}")" \
    || die "pre-push: ls-remote da $RC_TAG falhou"
  [ "$(printf '%s\n' "$_rp_rls" | awk -v r="refs/tags/$RC_TAG" '$2==r{print $1}')" = "$(git rev-parse "$RC_TAG")" ] \
    || die "pre-push: $RC_TAG remota nao e mais o objeto assinado - me chame no Claude"
  echo "   pre-push preflight: verde"
}
if [ "${SKIP_TO_PUSH:-0}" -eq 1 ]; then
  echo "   [RETOMADA] tag local existente - mesmo prompt SIM + mesmo preflight"
fi
printf 'push da tag %s (dispara publish npm via OIDC)? digite SIM: ' "$TAG"
read -r ans
[ "$ans" = "SIM" ] || die "abortado (tag assinada local, nao pushada)"
prepush_preflight
git push origin "$TAG"

else
  echo "   [MONITORAMENTO] assinaturas, commits, CI e push da tag ja feitos - indo direto as esperas"
fi
TAGSHA="$(git rev-parse "$TAG^{commit}")"
echo "   aguardando release.yml da tag..."
i=0
while :; do
  # 60 > release-gate 35 + publish-release + skew de runner (rail rc.3
  # r6 P1-5: 40 min podia estourar com a tag JA pushada; alem do bump,
  # o modo MONITORAMENTO do G0 torna o proprio timeout retomavel).
  i=$((i+1)); [ "$i" -le 60 ] || die "release.yml nao terminou em 60 min - re-rode este script (modo MONITORAMENTO retoma as esperas)"
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
# Janela de GA publico sem npm confirmado reduzida a segundos (rail
# r25 P1-3): drafta o release IMEDIATAMENTE; o undraft acontece so
# depois do npm view + recibo do step de publish. Ctrl-C/queda durante
# a espera do npm deixa o GA em DRAFT (invisivel), nao publico-parcial.
# Fast-path TERMINAL (rail r29 P1-2): um GA ja COMPLETO (npm no
# registry + release publico nao-draft) nunca volta a draft - um rerun
# de monitoramento e read-only sobre estado terminal.
_np_done="$(npm view ceo-orchestration@1.3.0 version 2>/dev/null || true)"
_tr_j="$(gh release view "$TAG" --json isDraft,isPrerelease 2>/dev/null || echo "")"
_tr_d="$(printf '%s' "$_tr_j" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
_tr_p="$(printf '%s' "$_tr_j" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
TERMINAL_MODE=0
if [ "$_np_done" = "1.3.0" ] && [ "$_tr_d" = "False" ] && [ "$_tr_p" = "False" ]; then
  TERMINAL_MODE=1
  echo "   estado TERMINAL detectado (npm 1.3.0 + release publico) - modo READ-ONLY; nenhuma mutacao de Release a partir daqui"
else
  # INCONDICIONAL fora do estado terminal (rail r26 P1-2): uma falha
  # transiente do gh view nao pode pular o draft; o VERIFY e o gate.
  gh release edit "$TAG" --draft \
    || die "draft imediato do GA falhou - rode gh release edit $TAG --draft e re-rode"
  _dr0="$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")"
  [ "$_dr0" = "true" ] \
    || die "GA nao esta em draft apos o edit (isDraft='$_dr0') - verifique antes de seguir"
  echo "   GA draftado ate o npm confirmar (undraft automatico no final)"
fi
bell "release.yml verde - aprovar production-npm"
echo "   aguardando npm-publish.yml da TAG (aprove production-npm quando o run pedir)"
_url_shown=0
NID=""
i=0
while :; do
  i=$((i+1))
  if [ "$i" -gt 90 ]; then
    [ "${TERMINAL_MODE:-0}" -eq 1 ] && die "estado TERMINAL: evidencia nao re-legivel mas o GA JA esta completo - NAO draftei; verifique manualmente (read-only, rail r30 P1-2)"
    bell "timeout do npm - draftando o Release GA"
    gh release edit "$TAG" --draft \
      || die "timeout de 90 min E o draft automatico falhou - rode gh release edit $TAG --draft; me chame no Claude"
    _mdr="$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")"
    [ "$_mdr" = "true" ] || die "timeout e o release NAO virou draft - verifique; me chame no Claude"
    die "npm-publish nao concluiu em 90 min - GA draftado automaticamente; re-rode este script (MONITORAMENTO retoma e undrafta apos npm confirmar)"
  fi
  sleep 60
  # Run PINADO uma unica vez por tag/SHA/evento (rail r21 P0): todo o
  # resto (status, conclusao, URL de aprovacao, recibo do step) le do
  # MESMO databaseId.
  if [ -z "$NID" ]; then
    NID="$(gh run list --workflow npm-publish.yml --limit 10 \
      --json headSha,databaseId,headBranch,event \
      --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].databaseId" 2>/dev/null || echo "")"
    [ "$NID" = "null" ] && NID=""
  fi
  if [ -z "$NID" ]; then
    printf '  ... run do npm-publish (tag %s) ainda nao apareceu\n' "$TAG"; continue
  fi
  _nrj="$(gh run view "$NID" --json status,conclusion 2>/dev/null || echo "")"
  ns="$(printf '%s' "$_nrj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("status",""))' 2>/dev/null || echo "")"
  nc="$(printf '%s' "$_nrj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("conclusion",""))' 2>/dev/null || echo "")"
  printf '  ... npm-publish: %s/%s\n' "${ns:-?}" "${nc:-?}"
  if [ "$ns" = "waiting" ] && [ "$_url_shown" -eq 0 ]; then
    nu="$(gh run view "$NID" --json url --jq .url 2>/dev/null || echo "")"
    bell "aprovar production-npm agora"
    echo "   >>> APROVE production-npm neste run: ${nu:-abra a aba Actions}"
    _url_shown=1
  fi
  if [ "$ns" = "completed" ] && [ "$nc" != "success" ] && [ "$nc" != "skipped" ]; then
    # QUALQUER conclusao terminal nao-success (failure/cancelled/
    # timed_out/stale/...) drafta AUTOMATICAMENTE o GA ja-publico e
    # verifica que draftou (rail r14 P1-2) - nunca um comando manual.
    [ "${TERMINAL_MODE:-0}" -eq 1 ] && die "estado TERMINAL: evidencia nao re-legivel mas o GA JA esta completo - NAO draftei; verifique manualmente (read-only, rail r30 P1-2)"
    bell "npm NAO publicou - draftando o Release GA"
    gh release edit "$TAG" --draft \
      || die "npm-publish '$nc' E o draft automatico FALHOU - rode gh release edit $TAG --draft e me chame no Claude"
    _mdr="$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")"
    [ "$_mdr" = "true" ] \
      || die "npm-publish '$nc' e o release NAO virou draft (isDraft='$_mdr') - verifique manualmente; me chame no Claude"
    die "npm-publish terminou '$nc' - GA draftado automaticamente (invisivel); me chame no Claude para triagem"
  fi
  [ "$ns" = "completed" ] && [ "$nc" = "success" ] && break
done
# npm view com RETRY limitado; falha persistente drafta o GA antes de
# abortar (rail r15 P1: o run do npm deu success mas um erro transiente
# de registry aqui deixava GA parcial PUBLICO sem mitigacao).
NPMV=""
_nv=0
while [ "$_nv" -lt 5 ]; do
  _nv=$((_nv+1))
  NPMV="$(npm view ceo-orchestration@1.3.0 version 2>/dev/null || true)"
  [ "$NPMV" = "1.3.0" ] && break
  printf '  ... npm view tentativa %s/5 devolveu "%s"; aguardando 30s\n' "$_nv" "$NPMV"
  sleep 30
done
if [ "$NPMV" != "1.3.0" ]; then
  [ "${TERMINAL_MODE:-0}" -eq 1 ] && die "estado TERMINAL: evidencia nao re-legivel mas o GA JA esta completo - NAO draftei; verifique manualmente (read-only, rail r30 P1-2)"
  bell "npm view nao confirmou - draftando o GA"
  gh release edit "$TAG" --draft \
    || die "npm view nao confirmou E o draft automatico falhou - rode gh release edit $TAG --draft; me chame no Claude"
  _mdr="$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")"
  [ "$_mdr" = "true" ] || die "npm view nao confirmou e o release NAO virou draft - verifique; me chame no Claude"
  die "npm view devolveu '$NPMV' apos 5 tentativas - GA draftado automaticamente; re-rode este script (MONITORAMENTO retoma e undrafta quando o registry confirmar)"
fi
echo "   npm view: ceo-orchestration@$NPMV presente no registry"
# RECIBO do publish DESTA arvore (rail r20 P0): o run pode ter terminado
# success pelo no-op already_published - a versao no registry seria de
# OUTRA arvore. Exige o STEP "Publish (Trusted Publishing" com
# conclusion=success (skipped = fail-closed com triagem).
_pubc="$(gh run view "$NID" --json jobs \
  --jq '[.jobs[].steps[]|select(.name|startswith("Publish (Trusted Publishing"))][0].conclusion' 2>/dev/null || echo "")"
if [ "$_pubc" != "success" ]; then
  [ "${TERMINAL_MODE:-0}" -eq 1 ] && die "estado TERMINAL: evidencia nao re-legivel mas o GA JA esta completo - NAO draftei; verifique manualmente (read-only, rail r30 P1-2)"
  bell "npm SEM recibo de publish desta arvore - draftando"
  gh release edit "$TAG" --draft \
    || die "publish step '$_pubc' (nao-success) E draft falhou - gh release edit $TAG --draft; me chame no Claude"
  _mdr="$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")"
  [ "$_mdr" = "true" ] || die "publish step '$_pubc' e release nao virou draft - verifique; me chame no Claude"
  die "step de publish concluiu '$_pubc' (skipped = registry ja tinha 1.3.0 de OUTRA arvore) - GA draftado; TRIAGEM comigo no Claude antes de qualquer undraft"
fi
echo "   recibo de publish desta arvore: step Publish success"
echo "   npm confirmado: ceo-orchestration@$NPMV"

say "8/8 GitHub Release (GA) - verificacao"
# release.yml cria o Release sozinho (idempotente; SEM --prerelease em
# tag estavel) - aqui so verificamos (pair-rail S300 r6 P1-1).
_prj="$(gh release view "$TAG" --json isPrerelease,isDraft 2>/dev/null || echo "")"
_pr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
_dr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
[ "$_pr" = "False" ] \
  || die "GitHub Release do $TAG ausente ou pre-release (isPrerelease='$_pr') - me chame no Claude"
# O UNDRAFT acontece so DEPOIS dos rechecks finais de tag/main (rail
# r26 P1-3) - aqui apenas registramos o estado.
echo "   Release GA presente (isDraft=$_dr) - undraft pos-rechecks"

# Recheck do OBJETO da RC tag tambem (rail r24-2).
_fr_rls="$(git ls-remote origin "refs/tags/$RC_TAG" "refs/tags/$RC_TAG^{}")" \
  || die "ls-remote final da $RC_TAG falhou"
[ "$(printf '%s\n' "$_fr_rls" | awk -v r="refs/tags/$RC_TAG" '$2==r{print $1}')" = "$(git rev-parse "$RC_TAG")" ] \
  || die "$RC_TAG remota mudou durante as esperas - me chame no Claude"
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
# Recheck FINAL fail-closed (rail r20 P1-4): main nao pode ter rolado
# entre o G0 e aqui - o GA declarado tem de estar em origin/main.
git fetch --quiet origin main || die "fetch final falhou"
[ "$(git rev-parse origin/main)" = "$(git rev-parse "$TAG^{commit}")" ] \
  || die "origin/main != commit da tag GA no recheck final - rollback? me chame no Claude ANTES de anunciar"
# UNDRAFT por ultimo (rail r26 P1-3): todos os rechecks acima verdes.
if [ "$_dr" = "True" ]; then
  gh release edit "$TAG" --draft=false \
    || die "undraft final falhou - gh release edit $TAG --draft=false manualmente"
fi
_fdr="$(gh release view "$TAG" --json isDraft,isPrerelease 2>/dev/null || echo "")"
_fd="$(printf '%s' "$_fdr" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
_fp="$(printf '%s' "$_fdr" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
if [ "$_fd" != "False" ] || [ "$_fp" != "False" ]; then
  # Compensacao VERIFICADA (rail r30 P1-3): nunca reportar re-draft que
  # nao se provou; um estado publico nao-resolvido e dito com todas as
  # letras.
  if [ "${TERMINAL_MODE:-0}" -eq 1 ]; then
    die "estado final ilegivel/invalido (isDraft='$_fd' isPrerelease='$_fp') em modo TERMINAL - NAO mutei o Release; verifique manualmente"
  fi
  if gh release edit "$TAG" --draft \
     && [ "$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")" = "true" ]; then
    die "estado final do Release invalido (isDraft='$_fd' isPrerelease='$_fp') - re-draftado E VERIFICADO; me chame no Claude"
  fi
  die "estado final do Release invalido (isDraft='$_fd' isPrerelease='$_fp') e a compensacao de re-draft NAO se confirmou - O GA PODE ESTAR PUBLICO EM ESTADO INVALIDO; verifique AGORA: gh release view $TAG"
fi
echo "   GA publicado NAO-draft (undraft pos-rechecks)"
bell "GA v1.3.0 publicado"
cat <<'DONE'

============================================================
 GA v1.3.0 PUBLICADO. Freeze ENCERRADO.
 Proximo (mesma sessao ou proxima):
   1. assinar o pack W3 (cura as 4 excecoes do verdito):
      cd .claude/plans/PLAN-169
      cp W3-approved-draft.md W3-approved.md
      (preencher Anchor-SHA = git rev-parse HEAD e a Data)
      gpg --armor --detach-sign W3-approved.md
      bash OWNER-W3-LAND.sh --dry-run   # e depois sem flag
   2. me chamar no Claude para: E0 + fechamento + memoria.
============================================================
DONE
