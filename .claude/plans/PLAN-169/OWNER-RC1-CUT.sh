#!/bin/bash
# OWNER-RC1-CUT.sh — corte da v1.4.0-rc.1 em UM comando (PLAN-169).
#
#   bash .claude/plans/PLAN-169/OWNER-RC1-CUT.sh [--restamp] [--from <passo>]
#
# CEREMONY-LINT: handwritten-exception: escrito contra o corpus
# `.claude/plans/PLAN-188/ceremony-defect-corpus-S348.md`; curas nomeadas no
# ponto de uso (CM-NN).
#
# PRE-REQUISITO: a wave-relmeta JA LANDADA. Sem ela o `release.sh` mira
# 1.3.0 e o preflight morre em "tag v1.3.0-rc.1 already exists". O G0 abaixo
# confere isso na primeira linha e recusa nomeando o script que falta rodar.
#
# RESUMIVEL. Cada passo grava um marcador em repass-rc1/.cut-state. Rodar de
# novo RETOMA do primeiro passo nao concluido; `--from N` forca o ponto de
# partida (e so isso — nenhum passo e pulado em silencio).
#
# OS TRES MOMENTOS EM QUE VOCE PARTICIPA:
#   pinentry 1  passo 9   assinar o verdict-fields (o material do pair-rail)
#   pinentry 2  passo 15  assinar a tag anotada
#   SIM         passo 16  confirmar o push da tag (o passo irreversivel)
#   navegador   passo 18  aprovar o ambiente do npm-publish, se ele pedir
#
# O QUE ESTE SCRIPT NUNCA FAZ SOZINHO: empurrar a tag sem o SIM, publicar no
# npm (quem publica e o npm-publish.yml, por OIDC, depois da sua aprovacao),
# ou editar qualquer pin do codex.
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

PLAN_DIR=".claude/plans/PLAN-169"
EV="$PLAN_DIR/repass-rc1"
RUNNER="$EV/run-rc1-repass.sh"
GEN="$PLAN_DIR/gen-envelope-rc1.py"
TAG="v1.4.0-rc.1"
BASE="1.4.0"
RCN="1"
KEY="CFCFACF00335DC74"
VF="$PLAN_DIR/verdict-fields-$TAG.md"
VD=".claude/governance/pair-rail-verdict-$TAG.md"
COND="$EV/CONDITIONS-rc1.md"
STATE="$EV/.cut-state"
RELEASE=".claude/scripts/local/release.sh"
GUARD=".claude/scripts/local/_release_tag_guard.py"
TODAY="$(date -u +%Y-%m-%d)"

RESTAMP=""
FROM=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --restamp) RESTAMP="--restamp" ;;
    --from) shift; FROM="${1:-0}" ;;
    *) printf 'uso: %s [--restamp] [--from <passo>]\n' "$0" >&2; exit 2 ;;
  esac
  shift
done

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
bell() { printf '\a'; osascript -e "display notification \"$1\" with title \"$TAG\"" 2>/dev/null || true; }

mkdir -p "$EV" || die "mkdir de $EV falhou"
[ -f "$STATE" ] || : > "$STATE"
done_step() { grep -qx "STEP-$1" "$STATE" 2>/dev/null; }
mark_step() { printf 'STEP-%s\n' "$1" >> "$STATE" || die "gravacao do marcador $1 falhou"; }
# `should` responde se o passo N deve rodar. `--from` so ANTECIPA o inicio;
# nunca pula um passo nao concluido.
should() {
  [ "$1" -ge "$FROM" ] || return 1
  ! done_step "$1"
}

# --- arvore limpa, com rc CONFERIDO (CM-04) --------------------------------
tree_clean_except() {
  # $@ = prefixos tolerados para arquivos UNTRACKED. Modificacao RASTREADA
  # nunca e tolerada.
  local f bad line p allow hit
  f="$(mktemp)"
  if ! git status --porcelain=v1 --untracked-files=all > "$f"; then
    rm -f "$f"; die "git status falhou — nao vou tratar como arvore limpa"
  fi
  bad=""
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    p="${line#???}"
    case "$line" in
      '??'*)
        hit=0
        for allow in "$@"; do
          case "$p" in "$allow"*) hit=1; break ;; esac
        done
        [ "$hit" -eq 1 ] || bad="$bad
   $p (untracked)" ;;
      *) bad="$bad
   $p (RASTREADO, modificado)" ;;
    esac
  done < "$f"
  rm -f "$f"
  [ -z "$bad" ] || die "arvore nao esta limpa:$bad"
}

wait_ci_green() {
  # $1 = sha. Espera TODOS os workflows do sha terminarem e exige um run
  # COMPLETO e success do validate.yml no nivel de JOB.
  local sha="$1" i info n p b vid vj vs vf vp vo
  sha="$1"; i=0
  while :; do
    i=$((i+1)); [ "$i" -le 90 ] || die "CI nao terminou em 90 min"
    sleep 60
    info="$(gh run list --limit 30 --json headSha,status,conclusion \
      --jq "[.[]|select(.headSha==\"$sha\")] | \
{n:length, p:[.[]|select(.status!=\"completed\")]|length, \
b:[.[]|select(.status==\"completed\" and .conclusion!=\"success\" \
and .conclusion!=\"skipped\")]|length}" 2>/dev/null || echo "")"
    [ -n "$info" ] || { printf '  ... gh falhou, tentando de novo\n'; continue; }
    n="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["n"])')"
    p="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["p"])')"
    b="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["b"])')"
    printf '  ... runs=%s pendentes=%s vermelhos=%s\n' "$n" "$p" "$b"
    [ "$b" -eq 0 ] || die "workflow vermelho para $sha — me chame no Claude"
    if [ "$n" -gt 0 ] && [ "$p" -eq 0 ]; then break; fi
  done
  vid="$(gh run list --workflow validate.yml --limit 20 \
    --json headSha,databaseId,status,conclusion,event,headBranch \
    --jq "[.[]|select(.headSha==\"$sha\" and .status==\"completed\" and .conclusion==\"success\" and .event==\"push\" and .headBranch==\"main\")][0].databaseId" 2>/dev/null || echo "")"
  [ -n "$vid" ] && [ "$vid" != "null" ] \
    || die "nenhum run COMPLETO e success do validate.yml para $sha"
  vj="$(gh run view "$vid" --json jobs \
    --jq '{s:[.jobs[]|select(.conclusion=="success")]|length, f:[.jobs[]|select(.conclusion=="failure")]|length, p:[.jobs[]|select(.status!="completed")]|length, o:[.jobs[]|select(.status=="completed" and .conclusion!="success" and .conclusion!="skipped")]|length}' 2>/dev/null || echo "")"
  vs="$(printf '%s' "$vj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["s"])')"
  vf="$(printf '%s' "$vj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["f"])')"
  vp="$(printf '%s' "$vj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["p"])')"
  vo="$(printf '%s' "$vj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["o"])')"
  [ "$vf" -eq 0 ] || die "job vermelho dentro do validate.yml"
  [ "$vp" -eq 0 ] || die "validate.yml selecionado ainda tem job pendente"
  [ "$vo" -eq 0 ] || die "validate.yml tem job terminal nao-success"
  [ "$vs" -ge 1 ] || die "validate.yml sem NENHUM job executado (CEO_SOTA_DISABLE?)"
  printf '   validate.yml: %s job(s) success, 0 failure\n' "$vs"
}

# ===========================================================================
say "G0 pre-condicoes"
command -v gh >/dev/null 2>&1 || die "gh CLI ausente"
[ -f "$RUNNER" ] || die "runner ausente: $RUNNER"
[ -f "$GEN" ] || die "gerador ausente: $GEN"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "nao esta em main"

# A wave-relmeta tem de ter landado: e ela que poe o driver na 1.4.0.
_tb="$(awk -F'"' '/^TARGET_BASE=/{print $2; exit}' "$RELEASE")"
[ "$_tb" = "$BASE" ] || die "TARGET_BASE do release.sh e '$_tb', esperado $BASE.
A wave-relmeta ainda nao landou. Rode, nesta ordem:
  bash $PLAN_DIR/s349-ceremony-relmeta/finalize-relmeta.sh
  bash $PLAN_DIR/OWNER-RC1-META-SIGN.sh
  bash $PLAN_DIR/OWNER-RC1-META-LAND.sh --dry-run
  bash $PLAN_DIR/OWNER-RC1-META-LAND.sh"

# O manifesto ADR-192 tem de estar consistente com o release.sh vivo.
_man="$(awk -v f="$RELEASE" '$2==f{print $1}' .claude/governance/gate-scripts-manifest.txt)"
[ "$_man" = "$(shasum -a 256 "$RELEASE" | awk '{print $1}')" ] \
  || die "sha do release.sh nao bate com o manifesto ADR-192 — a wave-relmeta landou pela metade"

git fetch --quiet origin main || die "git fetch falhou"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] \
  || die "HEAD != origin/main — pushe ou puxe primeiro"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 \
  && die "tag $TAG ja existe (local)"
# Tag REMOTA tambem: transporte falhando e ERRO, nunca "ausente".
_rls="$(git ls-remote origin "refs/tags/$TAG" "refs/tags/$TAG^{}")" \
  || die "git ls-remote falhou (transporte) — nao vou assumir tag remota ausente"
[ -z "$_rls" ] || die "tag $TAG ja existe no REMOTO:
$_rls"
# Release fantasma de tentativa abortada furaria o hold do GA. A sonda vive
# DENTRO do `if`: sob `set -e` uma atribuicao com rc!=0 mataria o script
# antes da classificacao NOT-FOUND.
if _grv="$(gh release view "$TAG" --json name 2>&1)"; then
  die "GitHub Release do $TAG JA EXISTE — triagem antes: gh release delete $TAG"
fi
printf '%s' "$_grv" | grep -qi "not found\|release not found\|HTTP 404" \
  || die "gh release view falhou sem ser NOT-FOUND (API?): $_grv"
# Untracked e tolerado dentro do namespace do plano: os proprios
# materiais do corte (evidencia, fields, condicoes) nascem ali. Nada
# fora dele, e modificacao RASTREADA nunca e tolerada em lugar nenhum.
tree_clean_except "$PLAN_DIR/"
printf '   OK: main, HEAD==origin/main, tag %s livre local e remotamente\n' "$TAG"
printf '   OK: driver mirando %s, manifesto ADR-192 consistente\n' "$BASE"

GPG_TTY="$(tty 2>/dev/null || true)"; export GPG_TTY

# ===========================================================================
if should 1; then
  say "1/20 preflight (le tudo, escreve nada)"
  bash "$RELEASE" preflight --rc "$RCN" --today "$TODAY" \
    || die "preflight recusou — leia o motivo acima"
  mark_step 1
fi

if should 2; then
  say "2/20 bump dos sitios de versao para $BASE"
  printf 'O bump exige que voce tenha RELIDO npm/README.md para esta release.\n'
  printf 'Enter para confirmar que releu (ctrl-C aborta): '; read -r _
  # shellcheck disable=SC2086
  bash "$RELEASE" bump --rc "$RCN" --today "$TODAY" --npm-readme-reviewed $RESTAMP \
    || die "bump falhou"
  mark_step 2
fi

if should 3; then
  say "3/20 push de main (o candidato precisa existir no remoto)"
  git push origin "HEAD:refs/heads/main" || die "push de main falhou"
  mark_step 3
fi

CAND="$(git rev-parse HEAD)"

if should 4; then
  say "4/20 esperar o CI do candidato ($CAND) — 15 a 40 min"
  wait_ci_green "$CAND"
  bell "CI verde no candidato"
  mark_step 4
fi

if should 5; then
  say "5/20 gravar CANDIDATE.sha (o runner le o candidato daqui)"
  _rm="$(git ls-remote origin refs/heads/main | awk '{print $1}')" \
    || die "ls-remote de main falhou"
  [ "$_rm" = "$CAND" ] || die "origin/main ($_rm) != HEAD ($CAND) — main andou"
  printf '%s\n' "$CAND" > "$EV/CANDIDATE.sha.tmp" || die "escrita falhou"
  mv -f "$EV/CANDIDATE.sha.tmp" "$EV/CANDIDATE.sha" || die "rename falhou"
  printf '   CANDIDATE.sha = %s\n' "$CAND"
  mark_step 5
fi

if should 6; then
  say "6/20 re-pass do codex — 6 partes, ~1 a 2 h. Deixe rodando."
  printf 'O codex roda PINADO em 0.147.0 (npx, cache proprio). O binario\n'
  printf 'global desta maquina NAO e usado e NAO e alterado.\n'
  bash "$RUNNER" || die "o re-pass NAO terminou GO nas 6 partes.
Leia $EV/PROVENANCE-rc1.md. Se for NO-GO: triagem, mv de $EV para
repass-rc1-$(date +%Y%m%d)-NOGO/, cura, e me chame no Claude."
  bell "re-pass GO nas 6 partes"
  mark_step 6
fi

if should 7; then
  say "7/20 condicoes do veredito"
  _agg_gwc=0
  for n in 1 2 3 4 5 6; do
    grep -qE '^VERDICT: GO-WITH-CONDITIONS' "$EV/verdict-rc1-$n.txt" && _agg_gwc=1
  done
  if [ "$_agg_gwc" -eq 1 ]; then
    [ -f "$COND" ] || die "algum rail deu GO-WITH-CONDITIONS e $COND nao existe.
As condicoes entram no MATERIAL ASSINADO. Rascunho em
$EV/README-rc1.md §6 — copie, ajuste ao que os rails disseram, salve em
$COND e rode este script de novo."
    printf '   condicoes que entram no material assinado:\n'
    sed 's/^/     /' "$COND"
    printf '\nEnter para seguir (ctrl-C aborta): '; read -r _
  else
    printf '   nenhum rail pediu condicoes\n'
  fi
  mark_step 7
fi

if should 8; then
  say "8/20 commit da evidencia do re-pass"
  ( cd "$EV" && shasum -a 256 -c MANIFEST-rc1.sha256 --status ) \
    || die "MANIFEST-rc1 nao verifica"
  _ev_list="$(mktemp)"
  awk '{print $2}' "$EV/MANIFEST-rc1.sha256" | sed "s|^|$EV/|" > "$_ev_list"
  printf '%s\n' "$EV/MANIFEST-rc1.sha256" "$EV/README-rc1.md" >> "$_ev_list"
  [ -f "$COND" ] && printf '%s\n' "$COND" >> "$_ev_list"
  while IFS= read -r _p; do
    [ -n "$_p" ] || continue
    [ -f "$_p" ] || die "arquivo da lista de evidencia ausente: $_p"
    [ -L "$_p" ] && die "symlink na lista de evidencia: $_p"
    git add -- "$_p" || die "git add falhou: $_p"
  done < "$_ev_list"
  # Nada staged fora da lista literal.
  _extra=""
  while IFS= read -r _c; do
    [ -n "$_c" ] || continue
    grep -qxF "$ROOT/$_c" "$_ev_list" || _extra="$_extra
   $_c"
  done <<CACHED
$(git diff --cached --name-only)
CACHED
  rm -f "$_ev_list"
  [ -z "$_extra" ] || die "caminho staged FORA da lista de evidencia:$_extra"
  git commit -q -m "governance(PLAN-169): evidencia do re-pass do candidato $TAG

Seis partes, ordenadas por raio de dano ao adotante, sobre o delta
v1.3.0..$CAND. Reviewer: codex-cli PINADO em 0.147.0 (npx, cache
proprio, payload verificado contra o manifesto ADR-182 antes da
revisao). Escopo coberto e o que ficou de fora: repass-rc1/README-rc1.md.
Payloads raw NAO commitados; pins em PROVENANCE-rc1.md." \
    || die "commit da evidencia falhou"
  printf '   evidencia commitada: %s\n' "$(git rev-parse --short HEAD)"
  mark_step 8
fi

PARENT="$(git rev-parse HEAD)"

if should 9; then
  say "9/20 gerar o verdict-fields (parent=$PARENT)"
  [ -e "$VF" ] && rm -f -- "$VF"
  [ -e "$VF.asc" ] && rm -f -- "$VF.asc"
  if [ -f "$COND" ]; then
    python3 "$GEN" --stage fields --parent "$CAND" --conditions-file "$COND" \
      || die "geracao dos fields falhou"
  else
    python3 "$GEN" --stage fields --parent "$CAND" || die "geracao dos fields falhou"
  fi
  [ -f "$VF" ] && [ ! -L "$VF" ] || die "verdict-fields gerado nao e arquivo regular"
  printf '\n----- CONTEUDO QUE VOCE VAI ASSINAR (pinentry 1 de 2) -----\n'
  cat "$VF"
  printf -- '----- FIM -----\n\nEnter para assinar (ctrl-C aborta): '; read -r _
  # A regra R2 do ceremony-lint reprova supressao de erro na mesma linha
  # de um comando irreversivel — inclusive num COMENTARIO que a cite. A
  # falha do gpgconf e engolida de proposito, e com o motivo dito em voz
  # alta: o agente e recriado pelo proprio pinentry.
  if ! gpgconf --kill gpg-agent >/dev/null 2>&1; then
    printf '   (gpgconf nao respondeu; seguindo — o pinentry recria o agente)\n'
  fi
  gpg --armor --detach-sign -u "$KEY" "$VF" || die "assinatura falhou"
  gpg --verify "$VF.asc" "$VF" || die "assinatura do verdict-fields nao verifica"
  mark_step 9
fi

if should 10; then
  say "10/20 montar o envelope a partir da assinatura"
  python3 "$GEN" --stage envelope --sig "$VF.asc" || die "geracao do envelope falhou"
  [ -f "$VD" ] && [ ! -L "$VD" ] || die "envelope gerado nao e arquivo regular"
  gpg --verify "$VF.asc" "$VF" \
    || die "assinatura NAO verifica pos-geracao do envelope — o VF mudou?"
  mark_step 10
fi

if should 11; then
  say "11/20 commit do veredito (o path canonico entra por ESTE caminho)"
  # `.claude/governance/pair-rail-verdict-*.md` e canonico. Ele nao passa pelo
  # hook de Edit/Write porque quem o ESCREVE e o gerador (python, escrita
  # atomica) e quem o COMMITA e o git — exatamente o mecanismo do
  # OWNER-RC3-CUT.sh, que landou o envelope da rc.3. O que autoriza o
  # conteudo e a assinatura GPG DENTRO dele, verificada pelo step 15 do
  # release.yml e pelo guard local do passo 12.
  mkdir -p "$HOME/.rc2-backup" || die "mkdir do backup falhou"
  mv "$VF.asc" "$HOME/.rc2-backup/verdict-fields-$TAG.md.asc" \
    || die "mover o .asc falhou"
  git add -- "$VF" "$VD" || die "git add do veredito falhou"
  _c="$(git diff --cached --name-only)" || die "git diff --cached falhou"
  [ "$(printf '%s\n' "$_c" | grep -c .)" = "2" ] \
    || die "esperava exatamente 2 caminhos staged, vi:
$_c"
  git commit -q -m "governance(PLAN-169): verdito pair-rail $TAG assinado

Decisao agregada DERIVADA dos 6 rails; as condicoes, quando existem,
fazem parte do material assinado (sub-mapa conditions: dos fields).
tool_versions.codex_cli vem da PROVENANCE do run PINADO e e re-validado
contra codex-cli-pin.txt pela funcao do proprio validador — nunca de
'codex --version' desta maquina, que esta fora da faixa." \
    || die "commit do veredito falhou"
  # CM-07: reler a mensagem e conferir que o assunto sobreviveu ao commit.
  git log -1 --format=%s | grep -qF "verdito pair-rail $TAG assinado" \
    || die "a mensagem do commit do veredito nao sobreviveu (hook commit-msg?)"
  printf '   veredito commitado: %s\n' "$(git rev-parse --short HEAD)"
  mark_step 11
fi

if should 12; then
  say "12/20 guard local de delta restrito"
  python3 "$GUARD" delta --repo "$ROOT" --tag "$TAG" \
    || die "guard de delta recusou — NAO pushe; me chame no Claude"
  mark_step 12
fi

if should 13; then
  say "13/20 push de main"
  _hs="$(git rev-parse HEAD)"
  git push origin "$_hs:refs/heads/main" || die "push de main falhou"
  mark_step 13
fi

if should 14; then
  say "14/20 esperar o CI do commit do veredito"
  wait_ci_green "$(git rev-parse HEAD)"
  bell "CI verde — assinar a tag"
  mark_step 14
fi

if should 15; then
  say "15/20 tag anotada e assinada (pinentry 2 de 2)"
  bash "$RELEASE" preflight --rc "$RCN" --today "$TODAY" || die "preflight pre-tag recusou"
  bash "$RELEASE" tag --rc "$RCN" || die "a fase tag falhou"
  mark_step 15
fi

if should 16; then
  say "16/20 confirmacao do PUSH DA TAG — este e o passo irreversivel"
  printf '\nPushar a tag %s inicia release.yml (o gate) E npm-publish.yml\n' "$TAG"
  printf '(que publica no npm por OIDC). O comando que sera executado:\n\n'
  printf '    git push origin %s\n\n' "$TAG"
  printf 'digite SIM (MAIUSCULO) para confirmar: '
  read -r ans
  [ "$ans" = "SIM" ] || die "abortado por voce (a tag esta assinada localmente, NAO pushada)"
  # Preflight pre-push: o SIM pode ter ficado aberto por muito tempo.
  git tag -v "$TAG" >/dev/null 2>&1 || die "pre-push: assinatura da tag nao verifica"
  [ "$(git rev-parse "$TAG^{commit}")" = "$(git rev-parse HEAD)" ] \
    || die "pre-push: a tag nao aponta o HEAD"
  git fetch --quiet origin main || die "pre-push: fetch falhou"
  [ "$(git rev-parse origin/main)" = "$(git rev-parse HEAD)" ] \
    || die "pre-push: origin/main != HEAD — main andou"
  tree_clean_except "$EV/"
  python3 "$GUARD" delta --repo "$ROOT" --tag "$TAG" || die "pre-push: guard recusou"
  # O veredito nao pode estar perto do TTL: o step 15 usa --max-age-hours 24.
  _gen="$(awk '/^generated_at:/{print $2}' "$VF" | tail -1)"
  _ttl="$(awk '/^ttl_hours:/{print $2}' "$VF" | tail -1)"
  [ -n "$_gen" ] && [ -n "$_ttl" ] || die "pre-push: fields sem generated_at/ttl"
  _ep="$(python3 - "$_gen" <<'PYVF'
import sys, datetime
try:
    print(int(datetime.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")).timestamp()))
except Exception:
    print("BAD")
PYVF
)"
  [ "$_ep" != "BAD" ] || die "pre-push: generated_at ilegivel"
  [ "$(date +%s)" -le $(( _ep + _ttl * 3600 - 3600 )) ] \
    || die "pre-push: o veredito esta a menos de 1h do TTL (ou expirado) — NAO pushe"
  printf '   pre-push: verde\n'
  TAG_PUSH_EPOCH="$(date +%s)"; printf '%s\n' "$TAG_PUSH_EPOCH" > "$EV/.tag-push-epoch"
  git push origin "refs/tags/$TAG" || die "push da tag falhou"
  mark_step 16
fi

if should 17; then
  say "17/20 esperar o release.yml da tag (~1,5 h)"
  TAGSHA="$(git rev-parse "$TAG^{commit}")"
  i=0
  while :; do
    i=$((i+1)); [ "$i" -le 120 ] || die "release.yml nao terminou em 120 min"
    sleep 60
    c="$(gh run list --workflow release.yml --limit 10 \
      --json headSha,status,conclusion,headBranch,event \
      --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].conclusion" 2>/dev/null || echo "")"
    s="$(gh run list --workflow release.yml --limit 10 \
      --json headSha,status,conclusion,headBranch,event \
      --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].status" 2>/dev/null || echo "")"
    printf '  ... release.yml: %s/%s\n' "${s:-?}" "${c:-?}"
    [ "$c" = "failure" ] && die "release.yml vermelho — me chame no Claude"
    [ "$s" = "completed" ] && [ "$c" = "success" ] && break
  done
  bell "release.yml verde"
  mark_step 17
fi

if should 18; then
  say "18/20 npm-publish: controle positivo do gate + sua aprovacao"
  _repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || echo "")"
  printf '   Se o npm-publish.yml pedir aprovacao de ambiente, ela e SUA e e\n'
  printf '   no navegador. Painel dos runs:\n'
  [ -n "$_repo" ] && printf '     https://github.com/%s/actions/workflows/npm-publish.yml\n' "$_repo"
  TAGSHA="$(git rev-parse "$TAG^{commit}")"
  i=0
  while :; do
    i=$((i+1)); [ "$i" -le 60 ] || die "await-release-gate nao concluiu em 60 min"
    sleep 60
    NID="$(gh run list --workflow npm-publish.yml --limit 10 \
      --json headSha,databaseId,headBranch,event \
      --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].databaseId" 2>/dev/null || echo "")"
    if [ -z "$NID" ] || [ "$NID" = "null" ]; then
      printf '  ... o run do npm-publish ainda nao apareceu\n'; continue
    fi
    AC="$(gh run view "$NID" --json jobs \
      --jq '[.jobs[]|select(.name|startswith("Await release-gate"))][0].conclusion' 2>/dev/null || echo "")"
    printf '  ... await-release-gate: %s\n' "${AC:-pendente/aguardando sua aprovacao}"
    [ "$AC" = "failure" ] && die "await-release-gate FALHOU — me chame no Claude"
    [ "$AC" = "success" ] && break
  done
  printf '   controle positivo do gate do npm: verde\n'
  mark_step 18
fi

if should 19; then
  say "19/20 GitHub Release como PRE-RELEASE"
  _pub="$(gh release view "$TAG" --json publishedAt --jq .publishedAt 2>/dev/null || echo "")"
  [ -n "$_pub" ] || die "o release.yml nao criou o GitHub Release do $TAG"
  _pe="$(python3 - "$_pub" <<'PYPB'
import sys, datetime
try:
    print(int(datetime.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")).timestamp()))
except Exception:
    print("BAD")
PYPB
)"
  [ "$_pe" != "BAD" ] || die "publishedAt ilegivel"
  _tpe="$(cat "$EV/.tag-push-epoch" 2>/dev/null || echo 0)"
  [ "$_pe" -ge $(( _tpe - 300 )) ] \
    || die "publishedAt e ANTERIOR a esta cerimonia (release stale?) — me chame no Claude"
  _prj="$(gh release view "$TAG" --json isPrerelease,isDraft 2>/dev/null || echo "")"
  _pr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
  _dr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
  { [ "$_pr" = "True" ] && [ "$_dr" = "False" ]; } \
    || die "Release do $TAG ausente, draft, ou sem a flag pre-release (pre='$_pr' draft='$_dr').
O hold ADR-103 conta de um release PUBLICO — me chame no Claude."
  printf '   pre-release confirmado NAO-draft\n'
  # A tag remota nao pode ter sido movida durante as esperas.
  _ft="$(git ls-remote origin "refs/tags/$TAG" "refs/tags/$TAG^{}")" \
    || die "ls-remote final da tag falhou (transporte)"
  _fp="$(printf '%s\n' "$_ft" | awk -v r="refs/tags/$TAG" '$2==r{print $1}')"
  [ "$_fp" = "$(git rev-parse "$TAG")" ] \
    || die "a tag remota NAO e mais o objeto assinado local — me chame no Claude"
  mark_step 19
fi

if should 20; then
  say "20/20 npm view"
  _pkg="$(python3 -c 'import json;print(json.load(open("npm/package.json"))["name"])' 2>/dev/null || echo "")"
  if [ -n "$_pkg" ]; then
    npm view "$_pkg" version 2>/dev/null || printf '   (npm view nao respondeu — confira no site)\n'
  fi
  mark_step 20
fi

bell "$TAG cortada"
cat <<DONE

============================================================
 $TAG CORTADA.
 - Hold ADR-103: >= 24 h a partir do publishedAt do pre-release.
   O hold e MECANICO no release.yml — o passo "Assert 24h" so
   existe no GA, e ele le esse publishedAt.
 - Ate o GA, main fica congelado.
 - Depois do hold: o GA repete este fluxo com --stable, e o
   re-pass roda de novo sobre a arvore da rc.1.
 - Me chame no Claude para o fechamento da sessao.
============================================================
DONE
