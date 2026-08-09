#!/bin/bash
# OWNER-GA-CUT.sh - promocao v1.3.0-rc.2 -> GA v1.3.0 em UM comando.
#
#   bash .claude/plans/PLAN-166/OWNER-GA-CUT.sh
#
# Pre-requisito: rc.2 cortada ha >= 24h (hold ADR-103). O script:
#   1. valida janela do hold + freeze (origin/main == commit da rc.2)
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
RC_TAG="v1.3.0-rc.2"
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
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] \
  || die "nao esta em main (branch/detached) - r6-P2 do rail"
git rev-parse -q --verify "refs/tags/$RC_TAG" >/dev/null 2>&1 || die "tag $RC_TAG nao existe"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 && die "tag $TAG ja existe"
RC_SHA="$(git rev-parse "$RC_TAG^{commit}")"
# Hold medido do EVENTO PUBLICADO, nao do tag local (pair-rail S300 r8
# P1-1): um corte que parou antes do push deixaria taggerdate local
# valido sem NENHUMA rc publica. Exige: tag no remoto apontando o mesmo
# SHA + pre-release publicado; hold conta de publishedAt.
REMOTE_TAG_SHA="$(git ls-remote origin "refs/tags/$RC_TAG^{}" | awk '{print $1}')"
[ -z "$REMOTE_TAG_SHA" ] && REMOTE_TAG_SHA="$(git ls-remote origin "refs/tags/$RC_TAG" | awk '{print $1}')"
[ "$REMOTE_TAG_SHA" = "$RC_SHA" ] || [ "$REMOTE_TAG_SHA" = "$(git rev-parse "$RC_TAG")" ] \
  || die "tag $RC_TAG nao esta no remoto (ou aponta outro SHA) - a rc.2 nunca foi publicada; termine o corte primeiro"
RC_PRE="$(gh release view "$RC_TAG" --json isPrerelease --jq .isPrerelease 2>/dev/null || echo "")"
[ "$RC_PRE" = "true" ] || die "pre-release da $RC_TAG ausente no GitHub - a rc nunca publicou; me chame no Claude"
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
git fetch --quiet origin main
# Estados legitimos (pair-rail S300 r13 P2 — retomada real): HEAD ==
# rc.2 (fresh), ou HEAD descendente da rc.2 cujo delta contem SO
# evidencia do hold + artefatos do verdito GA (interrompido apos o
# commit 2/4). origin/main pode ser rc.2 (pre-push) ou o proprio HEAD
# (interrompido apos o push). Qualquer outra coisa = freeze violado.
HEADNOW="$(git rev-parse HEAD)"
if [ "$HEADNOW" != "$RC_SHA" ]; then
  git merge-base --is-ancestor "$RC_SHA" "$HEADNOW" \
    || die "HEAD nao descende do commit da rc.2 - me chame no Claude"
  _bad_delta=""
  while IFS= read -r _dp; do
    [ -n "$_dp" ] || continue
    case "$_dp" in
      "$GA_DIR"/*|"$VF"|"$VD") : ;;
      *) _bad_delta="$_bad_delta
   $_dp" ;;
    esac
  done <<GADELTA
$(git diff --name-only "$RC_SHA"..HEAD)
GADELTA
  [ -z "$_bad_delta" ] \
    || die "delta rc.2..HEAD contem caminho fora da evidencia/verdito GA (freeze violado):$_bad_delta"
  echo "   modo RETOMADA: commits locais contem so evidencia/verdito GA"
fi
OM="$(git rev-parse origin/main)"
[ "$OM" = "$RC_SHA" ] || [ "$OM" = "$HEADNOW" ] \
  || die "origin/main nao e a rc.2 nem o HEAD da retomada - freeze violado; me chame no Claude"
# Arvore limpa EXCETO o conjunto FECHADO de saidas do runner do re-pass
# (pair-rail S300 r11 P2: uma invocacao que rodou o re-pass e parou
# antes do commit deixa esses untracked — o reuso precisa alcanca-los).
GA_OUT_OK="payload-ga-1.redacted.txt payload-ga-2.redacted.txt
diff-ga-1.patch diff-ga-2.patch
paths-ga-1.manifest.txt paths-ga-2.manifest.txt
verdict-ga-1.txt verdict-ga-2.txt
transcript-ga-1.log transcript-ga-2.log
PROVENANCE-ga.md MANIFEST-ga.sha256"
_dirty=""
while IFS= read -r _line; do
  [ -n "$_line" ] || continue
  _pathp="${_line#???}"
  case "$_pathp" in
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
$(git status --porcelain --untracked-files=all)
GASTATUS
[ -z "$_dirty" ] || die "arvore suja fora do conjunto de saidas do re-pass:$_dirty"
command -v gh >/dev/null 2>&1 || die "gh ausente"
[ -f "$VF_TPL" ] && [ -f "$VD_TPL" ] || die "templates GA ausentes"
PIN_JSON="$(python3 .claude/hooks/check_pair_rail.py --verify-codex-pin 2>/dev/null || true)"
printf '%s' "$PIN_JSON" | grep -q '"status": "verified"' || die "pin do codex nao verifica"
printf '%s' "$PIN_JSON" | grep -q '80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff' \
  || die "sha do payload codex mudou - re-gerar templates antes de assinar"

say "1/8 re-pass do hold"
# Reuso SO com proveniencia amarrada (pair-rail S300 r3 P1-2/P1-3):
# verditos de ensaio/stale nao citam o commit REAL da rc.2 nem o
# RUNNER-OVERALL: rc=0 que o runner grava ao final.
if [ -f "$GA_DIR/verdict-ga-1.txt" ] && [ -f "$GA_DIR/verdict-ga-2.txt" ] \
   && grep -q "$RC_SHA" "$GA_DIR/PROVENANCE-ga.md" 2>/dev/null \
   && grep -q "^RUNNER-OVERALL: rc=0$" "$GA_DIR/PROVENANCE-ga.md" 2>/dev/null; then
  echo "   verditos existentes com proveniencia da rc.2 ($RC_SHA) - reusando"
else
  bash "$GA_DIR/run-ga-repass.sh" \
    || die "re-pass do hold nao terminou GO limpo (rc!=0) - triagem comigo no Claude"
fi
# SO "VERDICT: GO" exato segue automatico (pair-rail S300 r2 P1-2):
# um GO-WITH-CONDITIONS do rail carrega condicao NOVA que o envelope
# pre-escrito (so as 4 excecoes herdadas) NAO contem — assinar sem
# triagem omitiria a condicao da decisao assinada. Nesse caso: pare,
# me chame no Claude, triamos e REGERAMOS o envelope antes de assinar.
for _vp in 1 2; do
  VLINE="$(grep -E '^VERDICT:' "$GA_DIR/verdict-ga-$_vp.txt" 2>/dev/null | tail -1 || true)"
  echo "   rail parte $_vp: ${VLINE:-sem verdito}"
  case "$VLINE" in
    "VERDICT: GO") : ;;
    *) die "re-pass parte $_vp: '$VLINE' != GO exato - triagem comigo no Claude (envelope sera regerado se houver condicao nova)" ;;
  esac
done

say "2/8 commit 1 (evidencia do hold)"
ls "$GA_DIR"/payload-ga-*.raw.txt >/dev/null 2>&1 && die "payload raw ainda na arvore"
git add "$GA_DIR"
if git diff --cached --quiet; then
  echo "   evidencia ja commitada (rerun)"
else
  git commit -m "docs(PLAN-166 W2): evidencia do re-pass do hold ADR-103 (GA v1.3.0)"
fi
PARENT="$(git rev-parse HEAD)"

say "3/8 verdict-fields GA (parent=$PARENT) - revisar e assinar (pinentry 1)"
GEN="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DMS="$(shasum -a 256 "$GA_DIR/MANIFEST-ga.sha256" | awk '{print $1}')"
TSH="$(cat "$GA_DIR/transcript-ga-1.log" "$GA_DIR/transcript-ga-2.log" | shasum -a 256 | awk '{print $1}')"
awk 'f{print} /-->/{f=1}' "$VF_TPL" \
  | sed -e "s/@@PARENT_SHA@@/$PARENT/" -e "s/@@GENERATED_AT@@/$GEN/" \
        -e "s/@@DELTA_MANIFEST_SHA@@/$DMS/" -e "s/@@TRANSCRIPT_SHA@@/$TSH/" > "$VF"
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
    -e "s|@@SIG_B64@@|$SIG|" "$VD_TPL" > "$VD"
mkdir -p "$HOME/.rc2-backup"
mv "$VF.asc" "$HOME/.rc2-backup/verdict-fields-v1.3.0.md.asc"
git add "$VF" "$VD"
git commit -m "governance(PLAN-166 W2): verdito pair-rail GA v1.3.0 assinado

GO-WITH-CONDITIONS: 4 excecoes nomeadas carregadas da rc.2 (curas no
pack W3 pos-GA). Re-pass do hold ADR-103 em repass-ga/."
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
  --json headSha,databaseId \
  --jq "[.[]|select(.headSha==\"$HEADSHA\")][0].databaseId" 2>/dev/null || echo "")"
[ -n "$VID" ] && [ "$VID" != "null" ] || die "nenhum run do validate.yml para o HEAD"
VJ="$(gh run view "$VID" --json jobs \
  --jq '{s:[.jobs[]|select(.conclusion=="success")]|length, f:[.jobs[]|select(.conclusion=="failure")]|length}' 2>/dev/null || echo "")"
vs="$(printf '%s' "$VJ" | python3 -c 'import json,sys;print(json.load(sys.stdin)["s"])')"
vf="$(printf '%s' "$VJ" | python3 -c 'import json,sys;print(json.load(sys.stdin)["f"])')"
[ "$vf" -eq 0 ] || die "job vermelho dentro do validate.yml"
[ "$vs" -ge 1 ] || die "validate.yml sem NENHUM job executado (CEO_SOTA_DISABLE?) - me chame no Claude"
echo "   validate.yml: $vs job(s) success, 0 failure (nivel de job)"
bell "CI verde - assinar a tag GA"

say "6/8 preflight + bump (no-op) + tag GA (pinentry 2)"
bash .claude/scripts/local/release.sh preflight --stable
bash .claude/scripts/local/release.sh bump --stable
bash .claude/scripts/local/release.sh tag --stable

say "7/8 push da tag + release.yml + npm"
printf 'push da tag %s (dispara publish npm via OIDC)? digite SIM: ' "$TAG"
read -r ans
[ "$ans" = "SIM" ] || die "abortado (tag assinada local, nao pushada)"
git push origin "$TAG"
TAGSHA="$(git rev-parse "$TAG^{commit}")"
echo "   aguardando release.yml da tag..."
i=0
while :; do
  i=$((i+1)); [ "$i" -le 40 ] || die "release.yml nao terminou em 40 min"
  sleep 60
  c="$(gh run list --workflow release.yml --limit 10 \
    --json headSha,status,conclusion \
    --jq "[.[]|select(.headSha==\"$TAGSHA\")][0].conclusion" 2>/dev/null || echo "")"
  s="$(gh run list --workflow release.yml --limit 10 \
    --json headSha,status,conclusion \
    --jq "[.[]|select(.headSha==\"$TAGSHA\")][0].status" 2>/dev/null || echo "")"
  printf '  ... release.yml: %s/%s\n' "${s:-?}" "${c:-?}"
  [ "$c" = "failure" ] && die "release.yml vermelho - me chame no Claude"
  [ "$s" = "completed" ] && [ "$c" = "success" ] && break
done
bell "release.yml verde - aprovar production-npm"
echo "   aguardando npm-publish.yml da TAG (aprove production-npm quando o run pedir)"
_url_shown=0
i=0
while :; do
  i=$((i+1)); [ "$i" -le 90 ] || die "npm-publish nao concluiu em 90 min"
  sleep 60
  ns="$(gh run list --workflow npm-publish.yml --limit 10 \
    --json headSha,status,conclusion \
    --jq "[.[]|select(.headSha==\"$TAGSHA\")][0].status" 2>/dev/null || echo "")"
  nc="$(gh run list --workflow npm-publish.yml --limit 10 \
    --json headSha,status,conclusion \
    --jq "[.[]|select(.headSha==\"$TAGSHA\")][0].conclusion" 2>/dev/null || echo "")"
  printf '  ... npm-publish: %s/%s\n' "${ns:-?}" "${nc:-?}"
  if [ "$ns" = "waiting" ] && [ "$_url_shown" -eq 0 ]; then
    nu="$(gh run list --workflow npm-publish.yml --limit 10 \
      --json headSha,url \
      --jq "[.[]|select(.headSha==\"$TAGSHA\")][0].url" 2>/dev/null || echo "")"
    bell "aprovar production-npm agora"
    echo "   >>> APROVE production-npm neste run: ${nu:-abra a aba Actions}"
    _url_shown=1
  fi
  if [ "$nc" = "failure" ]; then
    bell "npm FALHOU - Release GA ja esta publico"
    echo "   ATENCAO (ordem herdada do release.yml, pre-existente ao trem:"
    echo "   o job publish-release cria o Release GA logo apos o release-gate,"
    echo "   SEM esperar o npm). Mitigacao imediata para nao deixar GA"
    echo "   parcial publico enquanto triamos:"
    echo "       gh release edit $TAG --draft"
    die "npm-publish vermelho - rode a mitigacao acima e me chame no Claude"
  fi
  [ "$ns" = "completed" ] && [ "$nc" = "success" ] && break
done
NPMV="$(npm view ceo-orchestration version 2>/dev/null || true)"
[ "$NPMV" = "1.3.0" ] \
  || die "npm view devolveu '$NPMV' (esperado 1.3.0) - publish nao confirmado; me chame no Claude"
echo "   npm confirmado: ceo-orchestration@$NPMV"

say "8/8 GitHub Release (GA) - verificacao"
# release.yml cria o Release sozinho (idempotente; SEM --prerelease em
# tag estavel) - aqui so verificamos (pair-rail S300 r6 P1-1).
_pr="$(gh release view "$TAG" --json isPrerelease --jq .isPrerelease 2>/dev/null || echo "")"
[ "$_pr" = "false" ] \
  || die "GitHub Release do $TAG ausente ou marcado pre-release (isPrerelease='$_pr') - me chame no Claude"
echo "   GitHub Release GA confirmado (criado pelo release.yml)"

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
