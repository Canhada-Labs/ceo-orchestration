#!/bin/bash
# OWNER-GA-CUT.sh — corte do GA v1.4.1 em UM comando (PLAN-192): promocao da
# v1.4.1-rc.1 depois do hold ADR-103.
#
#   bash .claude/plans/PLAN-192/OWNER-GA-CUT.sh [--from <1-20>] [--until <1-20>] [--g0-only]
#
# CEREMONY-LINT: handwritten-exception: DERIVADO por
# .claude/plans/PLAN-192/derive-ga-kit-141.py do script de corte da rc.1 (fonte e
# sha256 em SOURCES, no derivador; o molde foi escrito contra o corpus
# `.claude/plans/PLAN-188/ceremony-defect-corpus-S348.md`). NAO edite a mao.
# Ensaiado por test-ga-kit.sh.
#
# PRE-REQUISITOS:
#  (a) o kit do GA COMMITADO e pushado em main (runner, condicoes, README, gerador,
#      derivador, harness e este script): o README e as condicoes entram no commit do
#      veredito e tem de ser identicos ao HEAD, e o preflight roda num clone de HEAD.
#      O G0 confere e recusa nomeando o arquivo — e recusa tambem qualquer arquivo NAO
#      rastreado no plano fora da evidencia deste corte (o passo 15 o recusaria tarde).
#  (b) >= 24 h desde o publishedAt do pre-release da v1.4.1-rc.1 (o G0 confere).
#  (c) a maquina QUIETA nos passos 1 e 15: o preflight roda a suite serial de hooks,
#      e tres testes de desempenho com teto ABSOLUTO de p99
#      (TestOutputScanPerfRigorous::test_p99_*) reprovam sob carga de CPU — foi o que
#      matou a 1.a tentativa da rc.1. O script mede a carga e avisa antes.
#  (d) FREEZE de main: do G0 ate o push da tag (passo 16) NENHUMA sessao pusha em
#      main (o passo 5 e o pre-push do 16 recusam main que andou; o passo 5 recusa
#      tambem um candidato que nao e o commit que os passos 1 e 4 conferiram). Depois
#      do 16, um push alheio nao derruba a retomada (G0) nem o passo 19 enquanto a tag
#      seguir na cadeia first-parent de origin/main. Durante o freeze, os runs
#      AGENDADOS (cron) de QUALQUER workflow sobre o commit congelado CONTAM nos
#      passos 4 e 14 e nos preflights 1 e 15: um vermelho agendado tem a rota do
#      vermelho de CI (abaixo), e um agendado AINDA RODANDO faz o preflight recusar
#      («a workflow for HEAD is still running»: espere e re-rode). Janelas a evitar
#      (INICIO dos crons de .github/workflows/, UTC): todo dia 06:43, 07:00, 07:37 e
#      11:00; as segundas, dez entre 03:00 e 19:23; no dia 1 do mes, 04:00 e 07:00.
#  (e) CLAUDE.md abaixo do limite do validate-governance.sh COMPLETO (40000 bytes, ou
#      CLAUDE_MD_SIZE_LIMIT): o preflight o roda com a saida suprimida. O G0 confere
#      antes, pelo nome. Nao edite o CLAUDE.md antes do GA sem rodar o gate completo.
#  (f) nenhum commit da faixa v1.4.0..HEAD cita plano (PLAN-NNN) ou toca ADR fora do
#      RELEASE_SCOPE do release.sh: a linha Scope da anotacao ASSINADA da tag sai de
#      la, e ela foi derivada dos planos citados nos assuntos de commit dessa faixa. O
#      G0 confere. Um plano NOVO fica FORA do repositorio ate o GA — sem commit nao
#      basta: o G0 recusa arquivo nao rastreado fora deste plano.
#
# RESUMIVEL. Cada passo grava um marcador em repass-ga/.cut-state. Rodar de
# novo RETOMA do primeiro passo nao concluido. `--from N` PULA os passos < N ainda
# nao concluidos — o script os NOMEIA antes de seguir (use so para passos que voce
# fez a mao; eles seguem pendentes). `--until N` para depois do passo N;
# `--g0-only` roda so as pre-condicoes. O banner de PUBLICADO so sai com o passo 20
# concluido; sem ele o script lista os passos pendentes.
# `--from` nao marca nada, e nao resolve os passos que deixam OBJETOS que o G0 confere
# pelo .cut-state: o commit do veredito (11), a tag local (15) e a tag no remoto (16).
# O G0 (tambem sob --g0-only) reconhece e REGISTRA um push da tag que ficou sem o
# marcador do 16 (o remoto tem o objeto assinado local). Para o 15 a recusa nomeia a
# rota (`git tag -d`, com a tag fora do remoto). Para o 11 (commit do veredito sem o
# marcador) ela manda NAO pushar e chamar o Claude: o guard do passo 12 ainda nao
# conferiu aquele commit. Entre os passos 5 e 11 o G0 exige HEAD == CANDIDATE.sha: um
# .cut-state de tentativa anterior e recusado.
#
# OS MOMENTOS EM QUE VOCE PARTICIPA:
#   Enter       passos 1 e 15  SO se a carga da maquina estiver alta (o aviso diz)
#   y + Enter   passos 1 e 15  a sonda GPG do preflight pergunta neste terminal
#                              «File exists. Overwrite? (y/N)» — responda y (com N
#                              ou so Enter o driver MENTE «the key cannot sign»)
#   pinentry    passos 1 e 15  a sonda (e a tag, no 15) podem pedir a senha
#   Enter       passo 2   confirmar que releu npm/README.md
#   Enter       passo 7   ler as condicoes que entram no material assinado
#   Enter       passo 9   depois de ler o conteudo; e o pinentry do verdict-fields
#   SIM         passo 16  confirmar o push da tag (o passo irreversivel)
#   navegador   passo 18  aprovar o ambiente production-npm (no GA o publish e REAL)
#
# O QUE ESTE SCRIPT NUNCA FAZ SOZINHO: empurrar a tag sem o SIM, aprovar o
# ambiente do npm, ou editar qualquer pin do codex.
#
# GA x rc.1: `--stable` no driver com bump NO-OP obrigatorio (VERSION ja e 1.4.1): o
# passo 2 recusa, ANTES de qualquer fetch/merge/push, um bump que produza commit ou
# arquivo, e `--restamp` nao existe no GA (ele sempre produz commit). O G0 exige o kit
# commitado, o hold ADR-103 da rc.1 (tag assinada, mesmo objeto no remoto,
# pre-release PUBLICO, >= 24 h, controle positivo do caminho de publish) e recusa
# se, entre a tag da rc.1 e o candidato, mudou caminho fora de CLAUDE.md e
# .claude/plans/PLAN-<N>* (no G0 contra o HEAD; no passo 5 contra o candidato). Sobre
# o candidato entra so o commit do veredito (envelope em .claude/governance/, fields
# e evidencia). O G0 reconhece as retomadas entre os passos 11 e 13 (veredito
# commitado, ainda nao pushado) e depois do 16 (tag no remoto; o Release em DRAFT que
# o release.yml cria). Espera de CI de ate 150 min (o Smoke Install levou 1h51 e
# derrubou a 3.a tentativa da rc.1 com o teto de 90). O passo 18 e o publish REAL no
# npm — o GitHub Release fica em DRAFT ate o registry confirmar e o step de publish
# dar recibo; o 19 faz os rechecks finais e o UNDRAFT; o 20 confirma npm view +
# Release publico (molde do corte do GA v1.4.0).
#
# CI VERMELHO so no gate de latencia de hooks, sem .py de hooks no diff (o caso do
# GA) — inclusive num run AGENDADO sobre o mesmo commit: e drift de runner —
# `gh run rerun <id> --failed`, espere o verde e re-rode este script (ele retoma).
# NUNCA faca patch. Vale para os passos 4 e 14 e para os preflights 1 e 15.
#
# Topologia herdada (S349): bump e preflight num clone descartavel de HEAD; o
# candidato e o que o passo 5 GRAVOU, nunca o HEAD do momento; evidencia + fields +
# veredito num commit SO, direto sobre o candidato (o release.yml exige parent_sha
# == PAI do commit que introduz o veredito).
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

PLAN_DIR=".claude/plans/PLAN-192"
EV="$PLAN_DIR/repass-ga"
RUNNER="$EV/run-ga-repass.sh"
GEN="$PLAN_DIR/gen-envelope-ga.py"
TAG="v1.4.1"
BASE="1.4.1"
RC_TAG="v1.4.1-rc.1"
KEY="CFCFACF00335DC74"
VF="$PLAN_DIR/verdict-fields-$TAG.md"
VD=".claude/governance/pair-rail-verdict-$TAG.md"
COND="$EV/CONDITIONS-ga.md"
STATE="$EV/.cut-state"
RELEASE=".claude/scripts/local/release.sh"
GUARD=".claude/scripts/local/_release_tag_guard.py"
TODAY="$(date -u +%Y-%m-%d)"
NPM_PKG="$(python3 -c 'import json;print(json.load(open("npm/package.json"))["name"])')" \
  || { printf 'FAIL: nome do pacote npm ilegivel em npm/package.json\n' >&2; exit 1; }
# Teto da espera de CI (passos 4 e 14), em minutos: o Smoke Install levou 1h51 no
# candidato da rc.1 e matou a 3.a tentativa com o teto antigo de 90.
CI_WAIT_MAX_MIN="${GA_CI_WAIT_MAX_MIN:-150}"
case "$CI_WAIT_MAX_MIN" in
  ''|*[!0-9]*|0) printf 'FAIL: GA_CI_WAIT_MAX_MIN invalido: %s\n' "$CI_WAIT_MAX_MIN" >&2; exit 1 ;;
esac
# A base da faixa da release (o GA anterior): RELEASE_SCOPE foi derivado de PREV_TAG..HEAD.
PREV_TAG="v1.4.0"
# O vermelho dos preflights (passos 1 e 15): o driver diz so a frase, e o
# validate-governance.sh roda la dentro com a saida suprimida.
PREFLIGHT_RED_HINT="O preflight conta QUALQUER workflow sobre este commit, agendado (cron) inclusive.
Se o motivo e «a workflow for HEAD is still running»: espere o run terminar e re-rode
este script (ele retoma deste passo).
Se o motivo e «a workflow for HEAD is not green» e o vermelho e SO o gate de
latencia de hooks, sem .py de hooks no diff desde a $RC_TAG, e drift de runner: rode
  gh run rerun <run> --failed
espere o verde e re-rode este script (ele retoma deste passo). NUNCA faca patch.
Se o motivo e «hooks test suite failed (serial)»: e a carga da maquina (os testes de
p99 com teto absoluto). Feche o que pesa, espere a carga cair e re-rode este script
(ele retoma deste passo).
Se o motivo e «validate-governance.sh nonzero» (o preflight suprime a saida), rode
  bash .claude/scripts/validate-governance.sh
e leia as linhas FAIL. Qualquer outro motivo: me chame no Claude."
# O kit que TEM de estar commitado e identico ao HEAD antes do corte (G0): os 8
# arquivos. Um derivador ou harness untracked passaria o G0 e mataria o passo 15.
KIT_TRACKED="$RUNNER $GEN $EV/README-ga.md $COND $EV/.gitignore $PLAN_DIR/OWNER-GA-CUT.sh"
KIT_TRACKED="$KIT_TRACKED $PLAN_DIR/derive-ga-kit-141.py $PLAN_DIR/test-ga-kit.sh"

FROM=0
UNTIL=20
G0_ONLY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --restamp)
      printf 'FAIL: --restamp nao existe no corte do GA: ele sempre produz um commit de bump,\n' >&2
      printf 'e o GA promove a arvore da rc.1 CONGELADA (o bump tem de ser no-op).\n' >&2
      exit 2 ;;
    --from)
      # Sem valor, o `shift` do fim do laco falharia sob set -e: rc 1 MUDO.
      [ "$#" -ge 2 ] || { printf 'FAIL: --from exige um passo de 1 a 20 (veio: nada)\n' >&2; exit 2; }
      shift; FROM="$1" ;;
    --until)
      [ "$#" -ge 2 ] || { printf 'FAIL: --until exige um passo de 1 a 20 (veio: nada)\n' >&2; exit 2; }
      shift; UNTIL="$1" ;;
    --g0-only) G0_ONLY=1 ;;
    *) printf 'uso: %s [--from <1-20>] [--until <1-20>] [--g0-only]\n' "$0" >&2; exit 2 ;;
  esac
  shift
done
# Passo = inteiro de 1 a 20 (o --from padrao 0 = sem --from). Qualquer outra coisa e
# recusa: um --from nao numerico fazia o `[ -ge ]` de should() falhar em todos os
# passos e o script terminava com o banner de PUBLICADO sem rodar nada.
_step_ok() { case "$1" in ''|*[!0-9]*) return 1 ;; esac; [ "$1" -ge "$2" ] && [ "$1" -le 20 ]; }
_step_ok "$FROM" 0 || { printf 'FAIL: --from exige um passo de 1 a 20 (veio: %s)\n' "$FROM" >&2; exit 2; }
_step_ok "$UNTIL" 1 || { printf 'FAIL: --until exige um passo de 1 a 20 (veio: %s)\n' "$UNTIL" >&2; exit 2; }
[ "$FROM" -le "$UNTIL" ] || { printf 'FAIL: --from %s depois de --until %s\n' "$FROM" "$UNTIL" >&2; exit 2; }
FROM=$((10#$FROM)); UNTIL=$((10#$UNTIL))

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
bell() { printf '\a'; osascript -e "display notification \"$1\" with title \"$TAG\"" 2>/dev/null || true; }

mkdir -p "$EV" || die "mkdir de $EV falhou"
[ -f "$STATE" ] || : > "$STATE"
done_step() { grep -qx "STEP-$1" "$STATE" 2>/dev/null; }
mark_step() { printf 'STEP-%s\n' "$1" >> "$STATE" || die "gravacao do marcador $1 falhou"; }
# `should` responde se o passo N deve rodar: nao concluido, >= --from e <= --until.
# Os passos < --from ainda NAO concluidos sao PULADOS — e o script os nomeia antes do
# passo 1, nunca em silencio.
should() {
  [ "$1" -ge "$FROM" ] || return 1
  [ "$1" -le "$UNTIL" ] || return 1
  ! done_step "$1"
}
pending_steps() {
  local _s=1 _l=""
  while [ "$_s" -le 20 ]; do
    done_step "$_s" || _l="$_l $_s"
    _s=$((_s+1))
  done
  printf '%s' "$_l"
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
    i=$((i+1)); [ "$i" -le "$CI_WAIT_MAX_MIN" ] \
      || die "CI nao terminou em $CI_WAIT_MAX_MIN min — re-rode este script: ele retoma deste passo (GA_CI_WAIT_MAX_MIN=<min> estica o teto)"
    sleep 60
    info="$(gh run list --limit 30 --json headSha,status,conclusion \
      --jq "[.[]|select(.headSha==\"$sha\")] | \
{n:length, p:[.[]|select(.status!=\"completed\")]|length, \
b:[.[]|select(.status==\"completed\" and .conclusion!=\"success\" \
and .conclusion!=\"skipped\")]|length}" 2>/dev/null || echo "")"
    [ -n "$info" ] || { printf '  ... gh falhou, tentando de novo\n'; continue; }
    n="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["n"])')" \
      || { printf '  ... resposta do gh ilegivel, tentando de novo\n'; continue; }
    p="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["p"])')" \
      || { printf '  ... resposta do gh ilegivel, tentando de novo\n'; continue; }
    b="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["b"])')" \
      || { printf '  ... resposta do gh ilegivel, tentando de novo\n'; continue; }
    printf '  ... runs=%s pendentes=%s vermelhos=%s\n' "$n" "$p" "$b"
    if [ "$b" -ne 0 ]; then
      gh run list --limit 30 --json headSha,status,conclusion,workflowName,databaseId,event \
        --jq ".[]|select(.headSha==\"$sha\" and .status==\"completed\" and .conclusion!=\"success\" and .conclusion!=\"skipped\")|\"   vermelho: \" + .workflowName + \" (run \" + (.databaseId|tostring) + \", \" + .conclusion + \", evento \" + .event + \")\"" \
        || printf '   (gh nao listou os runs vermelhos)\n'
      die "workflow vermelho para $sha (conta QUALQUER workflow e evento sobre o commit,
inclusive um run AGENDADO (cron) durante o freeze).
Se o vermelho e SO o gate de latencia de hooks e o diff desde a $RC_TAG nao tem
.py de hooks (o caso do GA: so CLAUDE.md e planos), e drift de runner: rode
  gh run rerun <run> --failed
espere ficar verde e re-rode este script (ele retoma deste passo). NUNCA faca
patch. Qualquer outro vermelho: me chame no Claude."
    fi
    if [ "$n" -gt 0 ] && [ "$p" -eq 0 ]; then break; fi
  done
  vid="$(gh run list --workflow validate.yml --limit 20 \
    --json headSha,databaseId,status,conclusion,event,headBranch \
    --jq "[.[]|select(.headSha==\"$sha\" and .status==\"completed\" and .conclusion==\"success\" and .event==\"push\" and .headBranch==\"main\")][0].databaseId" 2>/dev/null || echo "")"
  [ -n "$vid" ] && [ "$vid" != "null" ] \
    || die "nenhum run COMPLETO e success do validate.yml para $sha"
  vj="$(gh run view "$vid" --json jobs \
    --jq '{s:[.jobs[]|select(.conclusion=="success")]|length, f:[.jobs[]|select(.conclusion=="failure")]|length, p:[.jobs[]|select(.status!="completed")]|length, o:[.jobs[]|select(.status=="completed" and .conclusion!="success" and .conclusion!="skipped")]|length}' 2>/dev/null || echo "")"
  # Uma falha transitoria do `gh run view` tem NOME (antes era um traceback do python
  # e o script morria sem linha FAIL). O passo e resumivel.
  [ -n "$vj" ] || die "gh run view $vid falhou — re-rode este script (ele retoma deste passo)"
  vs="$(printf '%s' "$vj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["s"])')" \
    || die "resposta do gh run view $vid ilegivel — re-rode este script (ele retoma deste passo)"
  vf="$(printf '%s' "$vj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["f"])')" \
    || die "resposta do gh run view $vid ilegivel — re-rode este script (ele retoma deste passo)"
  vp="$(printf '%s' "$vj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["p"])')" \
    || die "resposta do gh run view $vid ilegivel — re-rode este script (ele retoma deste passo)"
  vo="$(printf '%s' "$vj" | python3 -c 'import json,sys;print(json.load(sys.stdin)["o"])')" \
    || die "resposta do gh run view $vid ilegivel — re-rode este script (ele retoma deste passo)"
  [ "$vf" -eq 0 ] || die "job vermelho dentro do validate.yml"
  [ "$vp" -eq 0 ] || die "validate.yml selecionado ainda tem job pendente"
  [ "$vo" -eq 0 ] || die "validate.yml tem job terminal nao-success"
  [ "$vs" -ge 1 ] || die "validate.yml sem NENHUM job executado (CEO_SOTA_DISABLE?)"
  printf '   validate.yml: %s job(s) success, 0 failure\n' "$vs"
}

# --- evidencia do re-pass ---------------------------------------------------
# A lista LITERAL do que o passo 11 commita junto com o veredito: o MANIFEST e
# tudo o que ele lista, o README do re-pass e as condicoes (quando existem).
# Caminhos RELATIVOS a raiz do repo — o mesmo dialeto de `git diff --cached
# --name-only`, contra o qual a lista e conferida nos dois sentidos.
evidence_list() {
  awk '{print $2}' "$EV/MANIFEST-ga.sha256" | sed "s|^|$EV/|"
  printf '%s\n' "$EV/MANIFEST-ga.sha256" "$EV/README-ga.md"
  if [ -f "$COND" ]; then printf '%s\n' "$COND"; fi
}
# Evidencia COMPLETA, verificada e GO para o candidato $1 — o que o CEO deixa
# pronto quando roda o re-pass ANTES desta cerimonia. Quatro fontes concordam:
# MANIFEST (shasum -c), RUNNER-OVERALL rc=0, o candidato da PROVENANCE e o
# CANDIDATE.sha que o runner leu. O gerador revalida todos os vereditos
# e os mesmos bytes de condicoes antes da assinatura e da montagem.
evidence_complete_for() {
  [ -f "$EV/MANIFEST-ga.sha256" ] || return 1
  ( cd "$EV" && shasum -a 256 -c MANIFEST-ga.sha256 --status ) 2>/dev/null || return 1
  grep -qE '^RUNNER-OVERALL: rc=0$' "$EV/PROVENANCE-ga.md" 2>/dev/null || return 1
  grep -qF -- "Candidato: $1 (" "$EV/PROVENANCE-ga.md" 2>/dev/null || return 1
  [ "$(tr -d ' \t\r\n' < "$EV/CANDIDATE.sha" 2>/dev/null)" = "$1" ] || return 1
}

# --- o kit do GA tem de estar COMMITADO e identico ao HEAD (so no GA) ------
# O README e as condicoes entram no commit do veredito e o passo 11 exige que
# sejam identicos ao HEAD; o preflight roda num clone de HEAD, que nao ve arquivo
# untracked. Um kit derivado e nao commitado so apareceria como recusa no passo 11
# ou 12 — depois da assinatura. Aqui ele e recusado ANTES, pelo nome.
assert_kit_committed() {
  local k miss
  miss=""
  for k in $KIT_TRACKED; do
    if [ ! -f "$k" ] || [ -L "$k" ]; then
      miss="$miss
   $k (ausente ou nao-regular)"
    elif ! git ls-files --error-unmatch -- "$k" >/dev/null 2>&1; then
      miss="$miss
   $k (NAO rastreado)"
    elif ! git diff --quiet HEAD -- "$k"; then
      miss="$miss
   $k (diferente do HEAD)"
    fi
  done
  [ -z "$miss" ] || die "o kit do GA nao esta commitado como o HEAD:$miss
Rode derive-ga-kit-141.py --check (tem de dar OK), commite e pushe o kit, espere o
CI verde e re-rode este script."
  printf '   OK: kit do GA commitado e identico ao HEAD\n'
}

# --- hold ADR-103 da rc.1 (so no GA): tag assinada, MESMO objeto no remoto,
# pre-release PUBLICO nao-draft, >= 24 h desde publishedAt, e o controle
# positivo do caminho de publish (await-release-gate da rc.1 = success).
# Moldura do corte do GA v1.4.0 (e do v1.3.0, PLAN-166).
assert_rc_hold() {
  local _rc_rls _rc_plain _rc_peel _rcj _rcp _rcd _pcn _pca _rcerr _rcj_rc _ghe
  git tag -v "$RC_TAG" >/dev/null 2>&1 \
    || die "assinatura da tag $RC_TAG local nao verifica — me chame no Claude"
  _rc_rls="$(git ls-remote origin "refs/tags/$RC_TAG" "refs/tags/$RC_TAG^{}")" \
    || die "git ls-remote da $RC_TAG falhou (transporte)"
  _rc_plain="$(printf '%s\n' "$_rc_rls" | awk -v r="refs/tags/$RC_TAG" '$2==r{print $1}')"
  _rc_peel="$(printf '%s\n' "$_rc_rls" | awk -v r="refs/tags/$RC_TAG^{}" '$2==r{print $1}')"
  RC_SHA="$(git rev-parse "$RC_TAG^{commit}")" || die "rev-parse da $RC_TAG falhou"
  [ "$_rc_plain" = "$(git rev-parse "$RC_TAG")" ] \
    || die "tag $RC_TAG remota nao e o mesmo OBJETO assinado local — me chame no Claude"
  [ -z "$_rc_peel" ] || [ "$_rc_peel" = "$RC_SHA" ] \
    || die "peel remoto da $RC_TAG diverge do commit local"
  # MECH3-P2-4: uma falha de TRANSPORTE do gh tem nome proprio (antes virava «ausente,
  # draft» ou «controle positivo ausente»); so «release not found» e ausencia real.
  _rcerr="$(mktemp)" || die "mktemp falhou"
  _rcj_rc=0
  _rcj="$(gh release view "$RC_TAG" --json isPrerelease,isDraft,publishedAt 2>"$_rcerr")" || _rcj_rc=$?
  if [ "$_rcj_rc" -ne 0 ]; then
    if grep -qi 'release not found' "$_rcerr"; then
      rm -f "$_rcerr"
      die "pre-release da $RC_TAG ausente (gh: release not found) — o hold conta de release PUBLICO"
    fi
    _ghe="$(head -c 300 "$_rcerr")" || _ghe=""
    rm -f "$_rcerr"
    die "gh release view $RC_TAG falhou (rc=$_rcj_rc; transporte?): $_ghe
O G0 so le: re-rode este script. Persistindo, me chame no Claude."
  fi
  rm -f "$_rcerr"
  _rcp="$(printf '%s' "$_rcj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
  _rcd="$(printf '%s' "$_rcj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
  PUBAT="$(printf '%s' "$_rcj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("publishedAt") or "")' 2>/dev/null || echo "")"
  { [ "$_rcp" = "True" ] && [ "$_rcd" = "False" ] && [ -n "$PUBAT" ]; } \
    || die "pre-release da $RC_TAG ausente, draft ou sem publishedAt (pre='$_rcp' draft='$_rcd') — o hold conta de release PUBLICO"
  PUB_EPOCH="$(python3 - "$PUBAT" <<'PYHOLD'
import sys, datetime
try:
    print(int(datetime.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")).timestamp()))
except Exception:
    print("BAD")
PYHOLD
)"
  [ "$PUB_EPOCH" != "BAD" ] || die "publishedAt da $RC_TAG ilegivel: '$PUBAT'"
  HOLD=$(( $(date +%s) - PUB_EPOCH ))
  [ "$HOLD" -ge 86400 ] \
    || die "hold ADR-103 incompleto: $((HOLD/3600))h < 24h desde o pre-release da $RC_TAG — volte mais tarde"
  _pcn="$(gh run list --workflow npm-publish.yml --limit 30 \
    --json headSha,databaseId,headBranch,event \
    --jq "[.[]|select(.headSha==\"$RC_SHA\" and .headBranch==\"$RC_TAG\" and .event==\"push\")][0].databaseId" 2>/dev/null)" \
    || die "gh run list do npm-publish.yml falhou (transporte?) — o G0 so le: re-rode este script"
  [ -n "$_pcn" ] && [ "$_pcn" != "null" ] \
    || die "nenhum run do npm-publish.yml para a $RC_TAG ($RC_SHA) — controle positivo ausente; me chame no Claude"
  _pca="$(gh run view "$_pcn" --json jobs \
    --jq '[.jobs[]|select(.name|startswith("Await release-gate"))][0].conclusion' 2>/dev/null)" \
    || die "gh run view $_pcn falhou (transporte?) — o G0 so le: re-rode este script"
  [ "$_pca" = "success" ] \
    || die "controle positivo await-release-gate da $RC_TAG NAO e success ('$_pca') — me chame no Claude"
  git merge-base --is-ancestor "$RC_SHA" HEAD \
    || die "HEAD nao descende da $RC_TAG — o GA promove a arvore da rc.1"
  printf '   OK: hold ADR-103 da %s completo (%sh >= 24h; publishedAt %s); await-release-gate da rc: success\n' \
    "$RC_TAG" "$((HOLD/3600))" "$PUBAT"
}

# --- evidencia deste corte e o UNICO untracked tolerado no plano (so no GA) --
# O passo 15 recusa QUALQUER arquivo nao rastreado (o release.sh tag exige arvore
# limpa) — e roda DEPOIS do push do veredito (passo 13). No plano, so a evidencia
# deste corte ($EV/, os fields e a assinatura) pode estar fora do git no G0; ela
# entra no commit do passo 11. Qualquer outro untracked no plano e recusado AQUI.
assert_plan_untracked_expected() {
  local f line p bad
  f="$(mktemp)" || die "mktemp falhou"
  if ! git status --porcelain=v1 --untracked-files=all -- "$PLAN_DIR/" > "$f"; then
    rm -f "$f"; die "git status do plano falhou — nao vou tratar como limpo"
  fi
  bad=""
  while IFS= read -r line; do
    case "$line" in
      '??'*)
        p="${line#???}"
        case "$p" in
          "$EV/"*|"$VF"|"$VF.asc") : ;;
          *) bad="$bad
   $p" ;;
        esac ;;
    esac
  done < "$f"
  rm -f "$f"
  [ -z "$bad" ] || die "arquivo NAO rastreado no plano, fora da evidencia deste corte:$bad
O passo 15 recusa qualquer arquivo nao rastreado, e ele roda DEPOIS do push do
veredito. Commite (e pushe) ou tire do repositorio agora, e re-rode este script."
  printf '   OK: no plano, so a evidencia deste corte esta fora do git\n'
}

# --- a arvore da rc.1, CONGELADA (so no GA) ---------------------------------
# O GA promove a arvore da rc.1: entre a tag dela e o candidato revisado so podem
# mudar CLAUDE.md (o contrato deste repo, nao entregue) e arquivos de planos
# NUMERADOS (.claude/plans/PLAN-<N>*: evidencia, ledger, este kit — fora do
# instalador e do pacote npm). Sobre o candidato entra so o commit do veredito (o
# passo 11), que toca .claude/governance/ por desenho. As condicoes assinadas do GA
# afirmam isso; aqui e mecanico. Um rename conta pelos DOIS nomes (--no-renames).
# $1 = a revisao a conferir (o HEAD no G0; o candidato no passo 5).
assert_rc_tree_frozen() {
  local rev="$1" rs f bad p
  rs="$(git rev-parse "$RC_TAG^{commit}")" || die "rev-parse da $RC_TAG falhou"
  f="$(mktemp)" || die "mktemp falhou"
  if ! git diff --no-renames --name-only "$rs" "$rev" -- > "$f"; then
    rm -f "$f"; die "git diff $RC_TAG..$rev falhou — nao vou tratar como arvore congelada"
  fi
  bad=""
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    case "$p" in
      CLAUDE.md|.claude/plans/PLAN-[0-9]*) : ;;
      *) bad="$bad
   $p" ;;
    esac
  done < "$f"
  rm -f "$f"
  [ -z "$bad" ] || die "desde a $RC_TAG mudou caminho FORA de CLAUDE.md e .claude/plans/PLAN-<N>*:$bad
O GA promove a arvore da rc.1: as condicoes do GA afirmam que, da tag da rc.1 ao
candidato revisado, so mudaram CLAUDE.md e planos numerados. Mudar isso exige
re-derivar o kit do GA (condicoes novas) — me chame no Claude."
  printf '   OK: desde a %s so mudaram CLAUDE.md e planos numerados (ate %s)\n' \
    "$RC_TAG" "$(git rev-parse --short "$rev")"
}

# --- CLAUDE.md dentro do limite do validate-governance.sh COMPLETO (so no GA) --
# O preflight dos passos 1 e 15 roda o validate-governance.sh completo com a saida
# SUPRIMIDA ("validate-governance.sh nonzero"); ele reprova o CLAUDE.md a partir de
# CLAUDE_MD_SIZE_LIMIT bytes (padrao 40000). Aqui o motivo tem nome, antes do passo 1.
assert_claude_md_fits() {
  local _cb _cl
  _cl="${CLAUDE_MD_SIZE_LIMIT:-40000}"
  [ -f CLAUDE.md ] || die "CLAUDE.md ausente na raiz"
  _cb="$(wc -c < CLAUDE.md | tr -d ' ')" || die "wc de CLAUDE.md falhou"
  [ "$_cb" -lt "$_cl" ] || die "CLAUDE.md tem $_cb bytes; o validate-governance.sh completo (que o preflight
dos passos 1 e 15 roda, com a saida suprimida) reprova a partir de $_cl. Encurte o
CLAUDE.md (commit + push, CI verde) e re-rode este script."
  printf '   OK: CLAUDE.md com %s bytes (o validate-governance.sh reprova a partir de %s)\n' "$_cb" "$_cl"
}

# --- o Scope ASSINADO da tag cobre a faixa (so no GA) ------------------------
# RELEASE_SCOPE (release.sh) entra na anotacao ASSINADA da tag no passo 15. Ele foi
# DERIVADO dos planos (PLAN-NNN) citados nos assuntos de `git log $PREV_TAG..HEAD` e
# dos ADRs tocados na faixa (a regra do apply-relmeta141-edits.py). Um commit que cite
# plano fora dele, ou que toque ADR fora dele, torna a linha Scope assinada falsa.
assert_release_scope_covers_log() {
  local _lg _adr _miss
  _lg="$(git log --format=%s "$PREV_TAG..HEAD")" || die "git log $PREV_TAG..HEAD falhou"
  _adr="$(git diff --name-only "$PREV_TAG" HEAD -- .claude/adr/)" || die "git diff das ADRs falhou"
  _miss="$(python3 - "$RELEASE" "$_lg" "$_adr" <<'PYSCOPE'
import re, sys
rel = open(sys.argv[1], encoding="utf-8").read()
m = re.findall(r'(?m)^RELEASE_SCOPE="([^"\n]*)"$', rel)
if len(m) != 1:
    print("RELEASE_SCOPE-ilegivel")
    sys.exit(0)
scope = m[0]
miss = sorted(set(re.findall(r"PLAN-\d{3}", sys.argv[2])) - set(re.findall(r"PLAN-\d{3}", scope)))
miss += sorted(set(re.findall(r"ADR-\d{3}", sys.argv[3])) - set(re.findall(r"ADR-\d{3}", scope)))
print(" ".join(miss))
PYSCOPE
)" || die "conferencia do RELEASE_SCOPE falhou"
  [ -z "$_miss" ] || die "a faixa $PREV_TAG..HEAD tem o que o RELEASE_SCOPE do release.sh nao lista: $_miss
A linha Scope da anotacao ASSINADA da tag sai do RELEASE_SCOPE, derivado dos planos
citados nos assuntos de commit da faixa e dos ADRs tocados nela. Com o commit ja em
main, o RELEASE_SCOPE precisa ser re-derivado (cerimonia da relmeta) — me chame no
Claude. Para nao cair aqui: um plano NOVO fica fora do repositorio ate o GA."
  printf '   OK: o Scope assinado da tag cobre os planos e ADRs de %s..HEAD\n' "$PREV_TAG"
}

# --- o .cut-state e desta tentativa (so no GA) -----------------------------
# Entre os passos 5 e 11 nada e commitado: o HEAD E o candidato gravado. Um
# .cut-state com o passo 5 e outro HEAD e resto de uma tentativa anterior (um NO-GO
# arquivado sem ele): seguir poria o runner sobre o candidato velho.
assert_cut_state_matches_head() {
  local _c5=""
  if done_step 5 && ! done_step 11; then
    if [ -f "$EV/CANDIDATE.sha" ] && [ ! -L "$EV/CANDIDATE.sha" ]; then
      _c5="$(tr -d ' \t\r\n' < "$EV/CANDIDATE.sha")" || die "leitura de CANDIDATE.sha falhou"
    fi
    [ -n "$_c5" ] && [ "$(git rev-parse HEAD)" = "$_c5" ] \
      || die "o .cut-state diz que o passo 5 gravou o candidato ${_c5:-<sem CANDIDATE.sha>}, mas o HEAD e $(git rev-parse HEAD).
Resto de uma tentativa anterior (um NO-GO?): mova o $STATE para o diretorio arquivado
dela, FORA do repositorio (README-ga §0), e re-rode este script — ele recomeca do passo 1."
    printf '   OK: o .cut-state (passo 5 feito) e o HEAD apontam o mesmo candidato\n'
  fi
}

# --- os passos 1 e 4 conferiram ESTE candidato (so no GA; MECH3-P2-5) --------
# O marcador STEP-N nao diz sobre qual commit o passo rodou; os passos 1 (preflight) e
# 4 (CI verde) gravam tambem `SHA-N <commit>`. Se o HEAD mudou depois deles (um push
# alheio durante o freeze, e um pull), o preflight e o CI verde sao de OUTRO commit.
# Sem a linha (passo feito a mao, ou .cut-state anterior a esta regra): AVISO nomeado.
assert_steps_saw_cand() {
  local _n _s _bad=""
  for _n in 1 4; do
    _s="$(awk -v k="SHA-$_n" '$1 == k { v = $2 } END { print v }' "$STATE")" \
      || die "leitura do $STATE falhou"
    if [ -z "$_s" ]; then
      printf '   AVISO: o .cut-state nao registra o commit que o passo %s conferiu (feito a mao?)\n' "$_n"
    elif [ "$_s" != "$1" ]; then
      _bad="$_bad
   passo $_n: conferiu $_s (linhas STEP-$_n e SHA-$_n)"
    fi
  done
  [ -z "$_bad" ] || die "o candidato agora e $1, e passo(s) ja marcado(s) conferiram OUTRO commit:$_bad
O HEAD mudou depois deles. Tire do $STATE as linhas nomeadas e re-rode este script: ele
refaz esses passos sobre o candidato novo. Se main andou por um push alheio durante o
freeze, me chame no Claude antes."
  printf '   OK: os passos 1 e 4 conferiram o candidato %s (ou nao registraram o commit)\n' "$(printf '%s' "$1" | cut -c1-12)"
}

# --- o prazo do veredito (TTL; so no GA; MECH3-P2-2) -------------------------
# O release.yml re-valida o veredito com --max-age-hours 24 NA HORA do run: um rerun
# depois do prazo fica vermelho para sempre, com a tag ja publica. O prazo impresso
# e generated_at + (ttl_hours - 1) h — a mesma folga de 1 h do pre-push do passo 16.
verdict_deadline() {
  local _g _t
  _g="$(awk '/^generated_at:/{print $2}' "$VF" 2>/dev/null | tail -1)" || _g=""
  _t="$(awk '/^ttl_hours:/{print $2}' "$VF" 2>/dev/null | tail -1)" || _t=""
  python3 - "$_g" "$_t" <<'PYDL' 2>/dev/null || printf '(prazo ilegivel: confira generated_at e ttl_hours em %s)' "$VF"
import sys, datetime
g = datetime.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00"))
print((g + datetime.timedelta(hours=int(sys.argv[2]) - 1)).strftime("%Y-%m-%d %H:%M UTC"))
PYDL
}

# --- carga da maquina antes do preflight (licao da 1.a tentativa da rc.1) ---
_load_pair() {
  python3 -c 'import os; print("%.2f %d" % (os.getloadavg()[0], os.cpu_count() or 1))' 2>/dev/null
}
warn_load() {
  # $1 = passo. Alta = media de 1 min >= metade das CPUs.
  local lp l n
  lp="$(_load_pair)" || lp=""
  l="${lp%% *}"; n="${lp##* }"
  case "$l$n" in
    ''|*[!0-9.]*)
      printf '   (carga da maquina ilegivel — siga so com a maquina QUIETA)\n'
      return 0 ;;
  esac
  printf '   carga da maquina (media de 1 min): %s em %s CPU(s)\n' "$l" "$n"
  if awk -v l="$l" -v n="$n" 'BEGIN { exit !(l >= n / 2) }'; then
    bell "maquina carregada antes do passo $1"
    printf '\nAVISO: a maquina esta CARREGADA. O passo %s roda o preflight, que roda a\n' "$1"
    printf 'suite serial de hooks: tres testes de desempenho com teto ABSOLUTO de p99\n'
    printf '(TestOutputScanPerfRigorous::test_p99_*) reprovam sob carga de CPU — foi o\n'
    printf 'que matou a 1.a tentativa da rc.1. Feche o que pesa (outras sessoes do\n'
    printf 'Claude ou do codex, VMs, builds) e espere a carga cair.\n'
    printf 'Enter para seguir mesmo assim (ctrl-C aborta; o script e resumivel): '
    read -r _
  else
    printf '   carga baixa; mesmo assim, nada pesado em paralelo ate o fim do preflight\n'
  fi
}
gpg_probe_hint() {
  printf '\n>>> O preflight PROVA a chave de assinatura, e o gpg vai perguntar NESTE terminal:\n'
  printf '>>>     File exists. Overwrite? (y/N)\n'
  printf '>>> Responda  y  e Enter. Com N (ou so Enter) o driver diz "the key cannot sign\n'
  printf '>>> right now" — e MENTIRA, e o preflight recusa; re-rode este script (ele\n'
  printf '>>> retoma deste passo). O pinentry pode pedir a senha aqui tambem.\n\n'
}

# ===========================================================================
say "G0 pre-condicoes"
command -v gh >/dev/null 2>&1 || die "gh CLI ausente"
[ -f "$RUNNER" ] || die "runner ausente: $RUNNER"
[ -f "$GEN" ] || die "gerador ausente: $GEN"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "nao esta em main"

# O driver mira a 1.4.1 desde a relmeta-141, landada antes da rc.1. Outro valor quer
# dizer que o release.sh mudou depois da rc.1: a arvore nao e mais a dela.
_tb="$(awk -F'"' '/^TARGET_BASE=/{print $2; exit}' "$RELEASE")"
[ "$_tb" = "$BASE" ] || die "TARGET_BASE do release.sh e '$_tb', esperado $BASE.
O driver ja nao mira a $BASE: o release.sh mudou depois da $RC_TAG, e o GA $TAG
promove a arvore da rc.1 CONGELADA — ele nao pode mais ser cortado deste main.
Me chame no Claude (a decisao e do Owner)."

# O manifesto ADR-192 tem de estar consistente com o release.sh vivo.
_man="$(awk -v f="$RELEASE" '$2==f{print $1}' .claude/governance/gate-scripts-manifest.txt)"
[ "$_man" = "$(shasum -a 256 "$RELEASE" | awk '{print $1}')" ] \
  || die "sha do release.sh nao bate com o manifesto ADR-192 — a wave-relmeta landou pela metade"

git fetch --quiet origin main || die "git fetch falhou"
# Push da tag feito e o passo 16 SEM marcador (interrupcao logo depois do push, ou um
# `git push` com rc != 0 depois de o servidor aceitar): com o passo 15 marcado e a tag
# no remoto EXATAMENTE o objeto assinado local — o que o `release.sh tag` criou e
# verificou no passo 15 —, o push aconteceu, e o G0 o registra. Qualquer outro objeto
# no remoto segue recusado abaixo. (`--from 17` nao resolveria: o G0 le o .cut-state.)
if done_step 15 && ! done_step 16; then
  _g0_r16="$(git ls-remote origin "refs/tags/$TAG")" \
    || die "git ls-remote da tag falhou (transporte) — nao vou assumir tag remota ausente"
  _g0_r16="$(printf '%s\n' "$_g0_r16" | awk -v r="refs/tags/$TAG" '$2==r{print $1}')"
  _g0_l16=""
  if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1; then
    _g0_l16="$(git rev-parse "refs/tags/$TAG")" || die "rev-parse da tag local falhou"
  fi
  if [ -n "$_g0_r16" ] && [ "$_g0_r16" = "$_g0_l16" ]; then
    if [ ! -s "$EV/.tag-push-epoch" ]; then
      # O passo 16 grava o epoch ANTES do push; sem ele, o piso do passo 19 e a data
      # do objeto da tag, criado no passo 15 desta cerimonia.
      git for-each-ref --format='%(taggerdate:unix)' "refs/tags/$TAG" > "$EV/.tag-push-epoch" \
        || die "gravacao de .tag-push-epoch falhou"
    fi
    mark_step 16
    printf '   o push da tag %s JA aconteceu (o remoto tem o objeto assinado local): passo 16 registrado agora\n' "$TAG"
  fi
fi
# Retomada depois do push da tag com main que ANDOU (push alheio depois do 16): o HEAD
# contem a tag, o HEAD e ancestral de origin/main, e a tag esta na cadeia first-parent
# de origin/main. Os passos 17-20 usam so a tag, nunca o HEAD.
_g0_tag_on_main() {
  local _tc _fpl
  git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 || return 1
  _tc="$(git rev-parse "$TAG^{commit}")" || return 1
  git merge-base --is-ancestor "$_tc" HEAD || return 1
  git merge-base --is-ancestor HEAD origin/main || return 1
  _fpl="$(git rev-list --first-parent origin/main)" || return 1
  grep -qxF -- "$_tc" <<FPL
$_fpl
FPL
}
_g0_ahead=0
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
  # Retomada entre o passo 11 (commit do veredito, LOCAL) e o 13 (push): o HEAD
  # esta UM commit a frente de origin/main, e esse commit senta sobre o candidato
  # gravado. O passo 12 (guard de delta) confere antes do push do 13.
  _g0_cs=""; _g0_hp=""
  if [ -f "$EV/CANDIDATE.sha" ] && [ ! -L "$EV/CANDIDATE.sha" ]; then
    _g0_cs="$(tr -d ' \t\r\n' < "$EV/CANDIDATE.sha")" || die "leitura de CANDIDATE.sha falhou"
  fi
  if git rev-parse -q --verify 'HEAD^' >/dev/null 2>&1; then
    _g0_hp="$(git rev-parse 'HEAD^')" || die "rev-parse de HEAD^ falhou"
  fi
  if done_step 11 && ! done_step 13 && [ -n "$_g0_cs" ] && [ "$_g0_hp" = "$_g0_cs" ] \
     && [ "$(git rev-parse origin/main)" = "$_g0_cs" ]; then
    _g0_ahead=1
  elif done_step 16 && _g0_tag_on_main; then
    printf '   AVISO: main andou depois do push da tag (%s commit(s) sobre ela); a tag segue na cadeia first-parent de origin/main — os passos 17-20 usam so a tag\n' \
      "$(git rev-list --count "$TAG^{commit}..origin/main")"
  elif [ ! -s "$STATE" ]; then
    die "HEAD != origin/main — pushe ou puxe primeiro (o kit commitado tem de estar em origin/main)"
  else
    die "HEAD != origin/main fora de uma retomada conhecida (.cut-state:$(tr '\n' ' ' < "$STATE")).
NAO pushe as cegas: se o guard do passo 12 recusou, o commit local do veredito NAO
pode subir. Veja git log --oneline -3 HEAD origin/main e me chame no Claude."
  fi
fi
# Os tres objetos abaixo (tag local, tag remota, GitHub Release) so podem
# EXISTIR numa retomada depois do passo que os cria (15, 16, 17). Numa corrida
# FRESCA a existencia e um corte anterior abortado — recusa nomeada, como
# antes. A retomada pos-tag so tem passos de espera e verificacao (17-20).
if ! done_step 15; then
  git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1 \
    && die "tag $TAG ja existe (local), e o .cut-state nao marca o passo 15.
Se foi o passo 15 desta cerimonia que a criou e o script morreu antes de marca-lo, e
ela NAO esta no remoto (git ls-remote origin refs/tags/$TAG sai vazio), apague-a com
  git tag -d $TAG
e re-rode este script: o passo 15 refaz o preflight, os guards e a tag. Tag no remoto,
ou tag que nao foi este script que criou: me chame no Claude."
fi
# Tag REMOTA tambem: transporte falhando e ERRO, nunca "ausente".
_rls="$(git ls-remote origin "refs/tags/$TAG" "refs/tags/$TAG^{}")" \
  || die "git ls-remote falhou (transporte) — nao vou assumir tag remota ausente"
if ! done_step 16; then
  [ -z "$_rls" ] || die "tag $TAG ja existe no REMOTO:
$_rls"
else
  # Retomada depois do push da tag: a tag remota TEM de ser o objeto assinado local.
  _g0_rpl="$(printf '%s\n' "$_rls" | awk -v r="refs/tags/$TAG" '$2==r{print $1}')"
  _g0_lt=""
  if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1; then
    _g0_lt="$(git rev-parse "refs/tags/$TAG")" || die "rev-parse da tag local falhou"
  fi
  [ -n "$_g0_rpl" ] && [ "$_g0_rpl" = "$_g0_lt" ] \
    || die "retomada pos-tag: a tag $TAG remota nao e o objeto assinado local — me chame no Claude"
fi
# Release fantasma de tentativa abortada furaria o hold do GA. A sonda vive
# DENTRO do `if`: sob `set -e` uma atribuicao com rc!=0 mataria o script
# antes da classificacao NOT-FOUND.
if _grv="$(gh release view "$TAG" --json isPrerelease,isDraft 2>&1)"; then
  if done_step 16; then
    # O release.yml cria o Release do GA (em DRAFT) no fim do run que a tag dispara:
    # numa retomada depois do passo 16 ele existir e o esperado — os passos 17-19
    # cuidam dele (draft ate o npm confirmar; undraft no 19). So nao pode ser
    # pre-release.
    _g0_rpp="$(printf '%s' "$_grv" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
    [ "$_g0_rpp" = "False" ] \
      || die "retomada pos-tag: o Release do $TAG existe mas isPrerelease='$_g0_rpp' — me chame no Claude"
    printf '   retomada pos-tag: o Release do %s existe (o release.yml o cria em DRAFT); os passos 17-19 cuidam dele\n' "$TAG"
  else
    die "GitHub Release do $TAG JA EXISTE antes do push da tag (corte anterior abortado?) — triagem antes: gh release view $TAG; me chame no Claude"
  fi
else
  printf '%s' "$_grv" | grep -qi "not found\|release not found\|HTTP 404" \
    || die "gh release view falhou sem ser NOT-FOUND (API?): $_grv"
fi
assert_kit_committed
assert_plan_untracked_expected
assert_rc_hold
# Antes do passo 5 o candidato ainda e o HEAD; depois, o passo 5 ja conferiu o
# candidato gravado (e o commit do veredito toca .claude/governance/ por desenho).
if ! done_step 5; then
  assert_rc_tree_frozen HEAD
fi
assert_cut_state_matches_head
# Scope e CLAUDE.md so importam ate a tag existir (a anotacao e assinada no 15, e o
# preflight so roda no 1 e no 15). Depois, main pode andar sem derrubar a retomada.
if ! done_step 15; then
  assert_release_scope_covers_log
  assert_claude_md_fits
fi
# Untracked e tolerado dentro do namespace do plano: os proprios
# materiais do corte (evidencia, fields, condicoes) nascem ali. Nada
# fora dele, e modificacao RASTREADA nunca e tolerada em lugar nenhum.
tree_clean_except "$PLAN_DIR/"
if done_step 16; then
  printf '   OK: main; retomada pos-tag (a tag %s no remoto e o objeto assinado local)\n' "$TAG"
elif done_step 15; then
  printf '   OK: main, HEAD==origin/main; tag %s assinada localmente, ainda NAO pushada\n' "$TAG"
elif [ "$_g0_ahead" -eq 1 ]; then
  printf '   OK: main; retomada entre os passos 11 e 13: o commit do veredito (%s) ainda nao foi pushado\n' \
    "$(git rev-parse --short HEAD)"
else
  printf '   OK: main, HEAD==origin/main, tag %s livre local e remotamente\n' "$TAG"
fi
printf '   OK: driver mirando %s, manifesto ADR-192 consistente\n' "$BASE"
printf '\n   FREEZE: do G0 ate o push da tag (passo 16) NENHUMA sessao pode pushar em main.\n'
printf '   Depois do 16, um push alheio nao derruba a retomada nem o passo 19 enquanto a\n'
printf '   tag seguir na cadeia first-parent de origin/main. Runs AGENDADOS (cron) de\n'
printf '   QUALQUER workflow sobre o commit congelado contam nos passos 4/14 e nos\n'
printf '   preflights 1/15. Inicio dos crons (UTC): todo dia 06:43, 07:00, 07:37 e 11:00;\n'
printf '   as segundas, dez de 03:00 a 19:23; no dia 1 do mes, 04:00 e 07:00.\n'

GPG_TTY="$(tty 2>/dev/null || true)"; export GPG_TTY

if [ "$G0_ONLY" -eq 1 ]; then
  printf '\nG0 verde (--g0-only): nenhum passo rodou. Pendentes:%s\n' "$(pending_steps)"
  exit 0
fi
if [ "$FROM" -gt 1 ]; then
  _skip=""; _s=1
  while [ "$_s" -lt "$FROM" ]; do
    done_step "$_s" || _skip="$_skip $_s"
    _s=$((_s+1))
  done
  if [ -n "$_skip" ]; then
    printf '\nAVISO: --from %s PULA passo(s) NAO concluido(s):%s\n' "$FROM" "$_skip"
    printf '(so para passos que voce fez a mao; eles seguem pendentes no .cut-state)\n'
  fi
fi

# ===========================================================================
if should 1; then
  say "1/20 preflight (le tudo, escreve nada) — num clone descartavel de HEAD"
  warn_load 1
  # S349 (10/09): `release.sh preflight` recusa QUALQUER `git status --porcelain`
  # nao vazio, untracked incluido — e a arvore viva carrega, por desenho, a
  # evidencia untracked do re-pass que o CEO rodou antes desta cerimonia. O
  # preflight roda portanto num clone local de HEAD (o MESMO objeto), limpo por
  # construcao — o molde do passo 2. O driver confere o CI de HEAD por `gh`, que
  # exige um remoto do GitHub: o clone local aponta para a arvore viva, entao o
  # remoto do CLONE (config propria; nao e worktree) recebe a URL do remoto vivo.
  _pw="$(mktemp -d)" || die "mktemp falhou"
  git clone --quiet --local --no-hardlinks "$ROOT" "$_pw/wt" \
    || die "clone descartavel para o preflight falhou"
  [ "$(git -C "$_pw/wt" rev-parse HEAD)" = "$(git rev-parse HEAD)" ] \
    || die "o clone descartavel nao esta no HEAD vivo"
  _origin="$(git remote get-url origin)" || die "remoto origin da arvore viva"
  git -C "$_pw/wt" remote set-url origin "$_origin" \
    || die "remoto do clone descartavel"
  gpg_probe_hint
  ( cd "$_pw/wt" && bash "$RELEASE" preflight --stable --today "$TODAY" ) \
    || die "preflight recusou — leia o motivo acima.
$PREFLIGHT_RED_HINT"
  _s1_sha="$(git -C "$_pw/wt" rev-parse HEAD)" || die "rev-parse do clone do preflight falhou"
  rm -rf -- "$_pw"
  printf 'SHA-1 %s\n' "$_s1_sha" >> "$STATE" || die "gravacao do commit do passo 1 falhou"
  mark_step 1
fi

if should 2; then
  say "2/20 bump --stable NO-OP (a arvore da rc.1 ja esta em $BASE; numa arvore descartavel)"
  printf 'O bump exige que voce tenha RELIDO npm/README.md para esta release.\n'
  printf 'Enter para confirmar que releu (ctrl-C aborta): '; read -r _
  # S349: `release.sh bump` recusa QUALQUER `git status --porcelain` nao vazio,
  # untracked incluido — e a arvore viva carrega, por desenho, a evidencia
  # untracked do re-pass que o CEO rodou antes desta cerimonia. O bump roda
  # portanto num clone local do HEAD, limpo por construcao.
  # GA: o bump TEM de ser no-op (VERSION ja em $BASE e os quatro oraculos limpos).
  # Um commit ou arquivo novo no clone e recusado AQUI, antes de qualquer
  # fetch/merge/push: ele mudaria caminhos fora dos planos (SBOM.md, npm/README.md, ...)
  # e o passo 5 recusaria o candidato — com main ja pushado.
  _bw="$(mktemp -d)" || die "mktemp falhou"
  git clone --quiet --local --no-hardlinks "$ROOT" "$_bw/wt" \
    || die "clone descartavel para o bump falhou"
  [ "$(git -C "$_bw/wt" rev-parse HEAD)" = "$(git rev-parse HEAD)" ] \
    || die "o clone descartavel nao esta no HEAD vivo"
  _b_rc=0
  ( cd "$_bw/wt" && bash "$RELEASE" bump --stable --today "$TODAY" \
      --npm-readme-reviewed ) || _b_rc=$?
  [ "$_b_rc" -eq 0 ] || die "bump falhou (rc=$_b_rc) — leia o motivo acima"
  _b_head="$(git -C "$_bw/wt" rev-parse HEAD)" || die "rev-parse do clone do bump falhou"
  _b_st="$(git -C "$_bw/wt" status --porcelain=v1 --untracked-files=all)" \
    || die "git status do clone do bump falhou"
  if [ "$_b_head" != "$(git rev-parse HEAD)" ] || [ -n "$_b_st" ]; then
    die "o bump do GA NAO foi no-op: o clone descartavel ($_bw/wt) ganhou commit ou arquivo.
O GA promove a arvore da rc.1 CONGELADA: VERSION ja e $BASE e os quatro oraculos
tem de estar limpos. NADA foi trazido para main nem pushado. Leia o log acima
(qual oraculo reprovou?) e me chame no Claude."
  fi
  printf '   bump e no-op: a arvore ja esta em %s (nada escrito)\n' "$BASE"
  rm -rf -- "$_bw"
  mark_step 2
fi

if should 3; then
  say "3/20 push de main (o candidato precisa existir no remoto)"
  git push origin "HEAD:refs/heads/main" || die "push de main falhou"
  mark_step 3
fi

# S349: o candidato e o que o passo 5 GRAVOU, nunca o HEAD do momento — numa
# retomada depois do passo 11 o HEAD ja e o commit do veredito, e o gerador
# recusa parent != CANDIDATE.sha. Antes do passo 5 o candidato e o HEAD.
if done_step 5; then
  CAND="$(tr -d ' \t\r\n' < "$EV/CANDIDATE.sha")" || die "leitura de CANDIDATE.sha falhou"
  printf '%s\n' "$CAND" | grep -qE '^[0-9a-f]{40}$' || die "CANDIDATE.sha nao e um sha40: '$CAND'"
  git merge-base --is-ancestor "$CAND" HEAD \
    || die "o candidato gravado ($CAND) nao e ancestral do HEAD"
else
  CAND="$(git rev-parse HEAD)"
fi

if should 4; then
  say "4/20 esperar o CI do candidato ($CAND) — ~15-20 min so com o Validate; ate ~2 h se o Smoke Install disparar (teto $CI_WAIT_MAX_MIN min)"
  wait_ci_green "$CAND"
  bell "CI verde no candidato"
  printf 'SHA-4 %s\n' "$CAND" >> "$STATE" || die "gravacao do commit do passo 4 falhou"
  mark_step 4
fi

if should 5; then
  say "5/20 gravar CANDIDATE.sha (o runner le o candidato daqui)"
  assert_rc_tree_frozen "$CAND"
  assert_steps_saw_cand "$CAND"
  _rm="$(git ls-remote origin refs/heads/main | awk '{print $1}')" \
    || die "ls-remote de main falhou"
  [ "$_rm" = "$CAND" ] || die "origin/main ($_rm) != HEAD ($CAND) — main andou"
  if [ -f "$EV/CANDIDATE.sha" ] && [ ! -L "$EV/CANDIDATE.sha" ] \
     && [ "$(tr -d ' \t\r\n' < "$EV/CANDIDATE.sha")" = "$CAND" ]; then
    # Re-pass rodado ANTES desta cerimonia sobre este mesmo commit: o MANIFEST pina o
    # CANDIDATE.sha byte a byte, e reescreve-lo poria a evidencia fora do MANIFEST.
    printf '   CANDIDATE.sha ja aponta %s — mantido byte a byte\n' "$CAND"
  else
    printf '%s\n' "$CAND" > "$EV/CANDIDATE.sha.tmp" || die "escrita falhou"
    mv -f "$EV/CANDIDATE.sha.tmp" "$EV/CANDIDATE.sha" || die "rename falhou"
    printf '   CANDIDATE.sha = %s\n' "$CAND"
  fi
  mark_step 5
fi

if should 6; then
  say "6/20 re-pass do codex — 3 partes (GA_CODEX_JOBS=3 corre-as ao mesmo tempo; cada parte leva ~10-45 min). Deixe rodando."
  if evidence_complete_for "$CAND"; then
    # S349: o CEO rodou o re-pass ANTES desta cerimonia, sobre este MESMO
    # candidato, e deixou a evidencia completa. O runner recusa rodar por cima
    # de evidencia anterior (completa OU parcial), e re-rodar seriam 3
    # sessoes de codex identicas.
    printf '   re-pass ja concluido (rc=0) para %s — nada a rodar\n' "$CAND"
  else
    printf 'O codex roda na versao que o manifesto ADR-182 pina: o binario global, se for\n'
    printf 'o pinado e o payload conferir; senao por npx num cache proprio. Nada e instalado.\n'
    GA_CODEX_JOBS="${GA_CODEX_JOBS:-3}" bash "$RUNNER" || die "o re-pass NAO terminou GO nas 3 partes. Leia $EV/PROVENANCE-ga.md (se existir).
Preserve a tentativa, inclusive parcial, FORA do repositorio (README-ga §0): o G0 recusa
arquivo nao rastreado no plano fora da evidencia deste corte, e o runner recusa rodar
sobre evidencia anterior. Crie um diretorio NOVO em $HOME/.ceo-ga-archive/ e mova para ele os arquivos
NAO rastreados de $EV/, menos o CANDIDATE.sha (fica; copie-o). Liste-os com:
  git status --porcelain --untracked-files=all -- $EV/
O runner, as condicoes, o README e o .gitignore sao rastreados e FICAM. O diretorio
arquivado e commitado no plano no closeout, depois do corte (nunca durante o freeze) e
sem o $STATE.
(a) NO-GO (a linha VERDICT: NO-GO em algum $EV/verdict-ga-N.txt): PARE — no GA nao ha
2.a rodada por conta propria. Diretorio: $HOME/.ceo-ga-archive/repass-ga-$(date +%Y%m%d)-NOGO-r1/
Mova para la TAMBEM o $STATE (ignorado pelo git, por isso fora da lista): sem ele a
proxima tentativa recomeca do passo 1. Leve ao Owner (me chame no Claude).
(b) Sem NO-GO e com parte SEM veredito: morte por CAPACIDADE do modelo (a PROVENANCE
diz) ou por INFRAESTRUTURA (rede, npx, git, gpg; o runner morto antes do codex, com ou
sem PROVENANCE). Nao e rodada. Diretorio:
  $HOME/.ceo-ga-archive/repass-ga-$(date +%Y%m%dT%H%M%S)-capacidade/  (ou -infra/)
MANTENHA o $STATE e o CANDIDATE.sha e re-rode este script: ele retoma do passo 6.
Qualquer outro caso (veredito ambiguo, main que andou): me chame no Claude."
  fi
  bell "re-pass GO nas 3 partes"
  mark_step 6
fi

if should 7; then
  say "7/20 condicoes do veredito"
  _agg_gwc=0
  for n in 1 2 3; do
    grep -qE '^VERDICT: GO-WITH-CONDITIONS' "$EV/verdict-ga-$n.txt" && _agg_gwc=1
  done
  if [ "$_agg_gwc" -eq 1 ]; then
    [ -f "$COND" ] || die "algum rail deu GO-WITH-CONDITIONS e $COND nao existe.
As condicoes entram no MATERIAL ASSINADO e devem ser identicas ao snapshot
$EV/CONDITIONS-ga.reviewed.md. Ajustar ou acrescentar condicoes exige
arquivar a tentativa e obter os tres GO/GWC num NOVO re-pass."
    printf '   condicoes que entram no material assinado:\n'
    sed 's/^/     /' "$COND"
    printf '\nEnter para seguir (ctrl-C aborta): '; read -r _
  else
    printf '   nenhum rail pediu condicoes\n'
  fi
  mark_step 7
fi

if should 8; then
  say "8/20 conferir a evidencia do re-pass (ela entra no commit do veredito, passo 11)"
  # S349: o molde commitava a evidencia AQUI e o veredito no passo 11 — dois
  # commits. O release.yml (step 15 e o gate delta+ancestry) exige
  # `parent_sha` == PAI do commit que INTRODUZ o veredito; com o veredito num
  # segundo commit esse pai seria o commit da evidencia, nunca o candidato
  # revisado, e o gate reprovaria DEPOIS da tag empurrada. Os cortes anteriores
  # landaram evidencia + veredito + fields num commit SO. Este passo
  # apenas CONFERE; o passo 11 commita tudo junto, sobre o candidato.
  ( cd "$EV" && shasum -a 256 -c MANIFEST-ga.sha256 --status ) \
    || die "MANIFEST-ga nao verifica"
  _ev_list="$(mktemp)"
  evidence_list > "$_ev_list" || die "lista de evidencia falhou"
  _ev_n=0
  while IFS= read -r _p; do
    [ -n "$_p" ] || continue
    [ -f "$_p" ] || die "arquivo da lista de evidencia ausente: $_p"
    [ -L "$_p" ] && die "symlink na lista de evidencia: $_p"
    _ev_n=$((_ev_n + 1))
  done < "$_ev_list"
  rm -f "$_ev_list"
  git diff --cached --quiet \
    || die "o index nao esta vazio — nada pode estar staged antes do passo 11"
  [ "$(git rev-parse HEAD)" = "$CAND" ] \
    || die "HEAD ($(git rev-parse --short HEAD)) != candidato revisado — o commit do veredito tem de sentar DIRETAMENTE sobre o candidato"
  printf '   evidencia verificada: %s caminho(s); index vazio; HEAD == candidato\n' "$_ev_n"
  mark_step 8
fi

if should 9; then
  say "9/20 gerar o verdict-fields (parent = candidato revisado $CAND)"
  [ -e "$VF" ] && rm -f -- "$VF"
  [ -e "$VF.asc" ] && rm -f -- "$VF.asc"
  if [ -f "$COND" ]; then
    python3 "$GEN" --stage fields --parent "$CAND" --conditions-file "$COND" \
      || die "geracao dos fields falhou"
  else
    python3 "$GEN" --stage fields --parent "$CAND" || die "geracao dos fields falhou"
  fi
  [ -f "$VF" ] && [ ! -L "$VF" ] || die "verdict-fields gerado nao e arquivo regular"
  printf '\n----- CONTEUDO QUE VOCE VAI ASSINAR (pinentry do passo 9) -----\n'
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
  printf '   PRAZO do veredito: o push da tag (passo 16) e qualquer rerun do release.yml\n'
  printf '   ate %s (o release.yml recusa um veredito com mais de 24 h)\n' "$(verdict_deadline)"
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
  say "11/20 commit do veredito + evidencia (o path canonico entra por ESTE caminho)"
  _asc_bk="$HOME/.rc2-backup/verdict-fields-$TAG.md.asc"
  # Retomada do passo 11 depois de uma falha: a assinatura pode ja estar no backup.
  if [ ! -f "$VF.asc" ] && [ -f "$_asc_bk" ]; then
    cp -p -- "$_asc_bk" "$VF.asc" || die "restaurar o .asc do backup ($_asc_bk) falhou"
    printf '   assinatura restaurada do backup: %s\n' "$_asc_bk"
  fi
  # Uma retomada nao reutiliza a assinatura sobre evidencia/condicoes alteradas.
  python3 "$GEN" --stage verify --sig "$VF.asc" \
    || die "fields assinados nao correspondem mais a evidencia revisada"
  # `.claude/governance/pair-rail-verdict-*.md` e canonico. Ele nao passa pelo
  # hook de Edit/Write porque quem o ESCREVE e o gerador (python, escrita
  # atomica) e quem o COMMITA e o git — o mecanismo que landou os envelopes
  # das releases anteriores. O que autoriza o
  # conteudo e a assinatura GPG DENTRO dele, verificada pelo step 15 do
  # release.yml e pelo guard local do passo 12.
  # S349: UM commit so, sobre o candidato — ver o passo 8.
  [ "$(git rev-parse HEAD)" = "$CAND" ] \
    || die "HEAD != candidato revisado — algo foi commitado entre o re-pass e o veredito"
  git diff --cached --quiet || die "o index nao esta vazio antes do staging literal"
  # O .asc sai da arvore (o passo 15 recusa arquivo nao rastreado) SO agora, depois
  # dos guards: se algo falhar daqui em diante, ele esta no backup e a retomada deste
  # passo o restaura (acima).
  mkdir -p "$HOME/.rc2-backup" || die "mkdir do backup falhou"
  mv "$VF.asc" "$_asc_bk" || die "mover o .asc para $_asc_bk falhou"
  printf '   assinatura guardada fora da arvore: %s\n' "$_asc_bk"
  _ev_list="$(mktemp)"
  evidence_list > "$_ev_list" || die "lista de evidencia falhou"
  printf '%s\n' "$VF" "$VD" >> "$_ev_list"
  while IFS= read -r _p; do
    [ -n "$_p" ] || continue
    [ -f "$_p" ] || die "arquivo da lista ausente: $_p"
    [ -L "$_p" ] && die "symlink na lista: $_p"
    git add -- "$_p" || die "git add falhou: $_p"
  done < "$_ev_list"
  # Conjunto staged == lista literal, nos DOIS sentidos (CM-06): nada FORA da
  # lista; e cada item da lista ou esta staged ou ja e identico ao HEAD (um
  # arquivo rastreado que o re-pass nao mudou — o runner, o README, as
  # condicoes). Caminhos RELATIVOS dos dois lados.
  _extra=""
  while IFS= read -r _c; do
    [ -n "$_c" ] || continue
    grep -qxF -- "$_c" "$_ev_list" || _extra="$_extra
   $_c"
  done <<CACHED
$(git diff --cached --name-only)
CACHED
  [ -z "$_extra" ] || die "caminho staged FORA da lista literal:$_extra"
  _missing=""
  while IFS= read -r _p; do
    [ -n "$_p" ] || continue
    if git diff --cached --quiet -- "$_p"; then
      # nao staged: so e aceitavel se ja for rastreado E identico ao HEAD
      if ! git ls-files --error-unmatch -- "$_p" >/dev/null 2>&1 \
         || ! git diff --quiet HEAD -- "$_p"; then
        _missing="$_missing
   $_p"
      fi
    fi
  done < "$_ev_list"
  rm -f "$_ev_list"
  [ -z "$_missing" ] || die "item da lista nem staged nem identico ao HEAD:$_missing"
  # O veredito e os fields TEM de ser NOVOS neste commit: o guard de vacuidade
  # (passo 12 e release.yml) exige o veredito DENTRO do delta candidato..tag.
  git diff --cached --quiet -- "$VD" && die "o veredito nao esta staged"
  git diff --cached --quiet -- "$VF" && die "o verdict-fields nao esta staged"
  git commit -q -F - <<MSG || die "commit do veredito falhou"
governance(PLAN-192): verdito pair-rail $TAG assinado + evidencia do re-pass

GA: promocao da v1.4.1-rc.1 depois do hold ADR-103. Decisao agregada
DERIVADA dos 3 rails; as condicoes, quando existem, fazem parte do
material assinado (sub-mapa conditions: dos fields) — inclusive a condicao
1: o anexo P1 do envelope da v1.4.0 NAO e curado nesta release. A cura foi
re-alvejada para a v1.4.2 em 2026-09-18 (PLAN-192 OQ-1); em 2026-09-22 o
Owner fez da v1.4.2 uma release expressa que nao a leva e a re-declara
aberta, e nenhuma versao esta prometida para ela. E a condicao 23: o hook
PreToolUse da tool Workflow grava uma copia do arquivo que um scriptPath
nomeia antes da decisao de permissao do harness (known-open; cura alvejada
para a v1.4.2). Nada foi curado entre a rc.1 e o GA: o que a rc.1 declarou
aberto segue aberto.
tool_versions.codex_cli vem da PROVENANCE do run PINADO e e re-validado
contra codex-cli-pin.txt e contra o manifesto ADR-182 pela funcao do proprio
validador — nunca de 'codex --version' desta maquina.

Evidencia do re-pass no MESMO commit: tres partes, ordenadas por raio de
dano ao adotante, sobre o delta v1.4.0..$CAND (a arvore da rc.1; a
PROVENANCE diz, por parte, se algum arquivo da pathspec mudou desde o
candidato da rc.1).
Reviewer: codex-cli na versao que o manifesto ADR-182 pina, com o payload
nativo verificado contra o manifesto antes da revisao (a rota esta na
PROVENANCE). Escopo coberto e o que ficou de fora: repass-ga/README-ga.md.
Payloads raw NAO commitados; pins em PROVENANCE-ga.md. O release.yml
exige parent_sha == pai do commit que introduz o veredito, e o guard local
exige o veredito dentro do delta candidato..tag: um commit so satisfaz os
dois.
MSG
  # CM-07: reler a mensagem e conferir que o assunto sobreviveu ao commit.
  git log -1 --format=%s | grep -qF "verdito pair-rail $TAG assinado" \
    || die "a mensagem do commit do veredito nao sobreviveu (hook commit-msg?)"
  [ "$(git rev-parse HEAD^)" = "$CAND" ] \
    || die "o commit do veredito nao senta sobre o candidato (pai != candidato)"
  printf '   veredito + evidencia commitados: %s (pai = candidato)\n' "$(git rev-parse --short HEAD)"
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
  say "15/20 preflight de novo + tag anotada e assinada (pinentry)"
  # S349: `release.sh tag` recusa QUALQUER porcelain nao vazio (untracked
  # incluido); nomear o que sobrou e melhor do que deixar o driver morrer
  # com "working tree dirty".
  _stray="$(git status --porcelain=v1 --untracked-files=all)" \
    || die "git status falhou antes da tag"
  [ -z "$_stray" ] || die "arvore nao esta limpa para a tag (release.sh recusaria):
$_stray"
  warn_load 15
  gpg_probe_hint
  bash "$RELEASE" preflight --stable --today "$TODAY" || die "preflight pre-tag recusou.
$PREFLIGHT_RED_HINT"
  bash "$RELEASE" tag --stable || die "a fase tag falhou"
  mark_step 15
fi

if should 16; then
  say "16/20 confirmacao do PUSH DA TAG — este e o passo irreversivel"
  printf '\nPushar a tag %s inicia release.yml (o gate) E npm-publish.yml\n' "$TAG"
  printf '(que PUBLICA no npm por OIDC — no GA o publish e REAL, depois da sua\n'
  printf 'aprovacao do ambiente production-npm no navegador). O comando:\n\n'
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
    || die "pre-push: o veredito esta a menos de 1h do TTL (ou expirado) — NAO pushe.
O prazo era $(verdict_deadline). Um veredito vencido exige fields novos, assinados
de novo, e o commit do veredito ja esta em main: me chame no Claude."
  printf '   pre-push: verde\n'
  TAG_PUSH_EPOCH="$(date +%s)"; printf '%s\n' "$TAG_PUSH_EPOCH" > "$EV/.tag-push-epoch"
  git push origin "refs/tags/$TAG" || die "push da tag falhou"
  mark_step 16
fi

if should 17; then
  say "17/20 esperar o release.yml da tag (~20-25 min; medido 18-22 min nos ultimos cortes, teto 120)"
  TAGSHA="$(git rev-parse "$TAG^{commit}")"
  i=0
  while :; do
    i=$((i+1)); [ "$i" -le 120 ] \
      || die "release.yml nao terminou em 120 min — re-rode este script: ele retoma do passo 17"
    sleep 60
    _r17="$(gh run list --workflow release.yml --limit 10 \
      --json headSha,status,conclusion,headBranch,event,databaseId \
      --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0] | ((.status // \"\") + \"|\" + (.conclusion // \"\") + \"|\" + ((.databaseId // \"\")|tostring))" 2>/dev/null || echo "")"
    # Separador `|`: uma conclusao VAZIA (run em andamento) nao desloca os campos.
    s="$(printf '%s' "$_r17" | awk -F'|' '{print $1}')"
    c="$(printf '%s' "$_r17" | awk -F'|' '{print $2}')"
    printf '  ... release.yml: %s/%s\n' "${s:-?}" "${c:-?}"
    if [ "$s" = "completed" ] && [ "$c" != "success" ]; then
      die "release.yml terminou '${c:-?}' para a tag $TAG (run $(printf '%s' "$_r17" | awk -F'|' '{print $3}')).
Leia o run: gh run view <run> --log-failed
Cancelamento, timeout ou drift de runner (so o gate de latencia de hooks, sem .py de
hooks no diff): gh run rerun <run> --failed e espere o verde. O await-release-gate do
npm-publish.yml da tag recusa um gate que terminou sem success, e essa recusa nao volta
sozinha: depois do verde, se o run do npm-publish.yml da tag terminou vermelho, rode
tambem gh run rerun <run dele> --failed; so entao re-rode este script
(ele retoma do passo 17). PRAZO: o release.yml re-valida o veredito na hora do run —
rerun so ate $(verdict_deadline); depois disso ele fica vermelho para sempre.
Vermelho no gate do veredito ou em outro step: me chame no Claude."
    fi
    [ "$s" = "completed" ] && [ "$c" = "success" ] && break
  done
  bell "release.yml verde"
  mark_step 17
fi

if should 18; then
  say "18/20 npm-publish: aprovacao do ambiente production-npm + publish REAL + recibo"
  # Molde do corte do GA v1.4.0 (e do v1.3.0, PLAN-166): o release.yml cria o
  # Release do GA ja em DRAFT (rail rc.3 r27); este passo re-afirma o draft
  # (idempotente) e ele fica em DRAFT ate o npm confirmar. Estado TERMINAL (registry
  # ja tem $BASE + Release publico nao-draft) e READ-ONLY.
  TAGSHA="$(git rev-parse "$TAG^{commit}")"
  _repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || echo "")"
  _np_done="$(npm view "$NPM_PKG@$BASE" version 2>/dev/null || echo "")"
  _tr_j="$(gh release view "$TAG" --json isDraft,isPrerelease 2>/dev/null || echo "")"
  _tr_d="$(printf '%s' "$_tr_j" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
  _tr_p="$(printf '%s' "$_tr_j" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
  TERMINAL_MODE=0
  if [ "$_np_done" = "$BASE" ] && [ "$_tr_d" = "False" ] && [ "$_tr_p" = "False" ]; then
    TERMINAL_MODE=1
    printf '   estado TERMINAL (npm %s + Release publico): modo READ-ONLY\n' "$BASE"
  else
    gh release edit "$TAG" --draft \
      || die "draft imediato do GA falhou — rode: gh release edit $TAG --draft; e re-rode este script"
    _dr0="$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")"
    [ "$_dr0" = "true" ] || die "GA nao esta em draft apos o edit (isDraft='$_dr0') — verifique antes de seguir"
    printf '   GA em DRAFT ate o npm confirmar (undraft automatico no passo 19)\n'
  fi
  bell "aprovar production-npm"
  printf '   Se o npm-publish.yml pedir aprovacao de ambiente, ela e SUA e e no navegador:\n'
  [ -n "$_repo" ] && printf '     https://github.com/%s/actions/workflows/npm-publish.yml\n' "$_repo"
  NID=""; _url_shown=0; i=0
  while :; do
    i=$((i+1))
    if [ "$i" -gt 90 ]; then
      [ "$TERMINAL_MODE" -eq 1 ] && die "estado TERMINAL: npm-publish ilegivel mas o GA JA esta completo — verifique manualmente (read-only)"
      gh release edit "$TAG" --draft \
        || die "timeout de 90 min E o draft falhou — rode: gh release edit $TAG --draft; me chame no Claude"
      die "npm-publish nao concluiu em 90 min — GA em DRAFT (invisivel); re-rode este script (retoma no passo 18)"
    fi
    sleep 60
    if [ -z "$NID" ]; then
      NID="$(gh run list --workflow npm-publish.yml --limit 10 \
        --json headSha,databaseId,headBranch,event \
        --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].databaseId" 2>/dev/null || echo "")"
      [ "$NID" = "null" ] && NID=""
    fi
    if [ -z "$NID" ]; then
      printf '  ... o run do npm-publish ainda nao apareceu\n'; continue
    fi
    _nrj="$(gh run view "$NID" --json status,conclusion 2>/dev/null || echo "")"
    ns="$(printf '%s' "$_nrj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("status",""))' 2>/dev/null || echo "")"
    nc="$(printf '%s' "$_nrj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("conclusion",""))' 2>/dev/null || echo "")"
    printf '  ... npm-publish: %s/%s\n' "${ns:-?}" "${nc:-?}"
    if [ "$ns" = "waiting" ] && [ "$_url_shown" -eq 0 ]; then
      nu="$(gh run view "$NID" --json url --jq .url 2>/dev/null || echo "")"
      bell "aprovar production-npm agora"
      printf '   >>> APROVE production-npm neste run: %s\n' "${nu:-abra a aba Actions}"
      _url_shown=1
    fi
    if [ "$ns" = "completed" ] && [ "$nc" != "success" ]; then
      [ "$TERMINAL_MODE" -eq 1 ] && die "estado TERMINAL: run '$nc' mas o GA JA esta completo — verifique manualmente (read-only)"
      gh release edit "$TAG" --draft \
        || die "npm-publish '$nc' E o draft falhou — rode: gh release edit $TAG --draft; me chame no Claude"
      _mdr="$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")"
      [ "$_mdr" = "true" ] || die "npm-publish '$nc' e o Release NAO virou draft (isDraft='$_mdr') — verifique AGORA"
      die "npm-publish terminou '$nc' — GA em DRAFT (invisivel); me chame no Claude para triagem"
    fi
    [ "$ns" = "completed" ] && [ "$nc" = "success" ] && break
  done
  NPMV=""; _nv=0
  while [ "$_nv" -lt 5 ]; do
    _nv=$((_nv+1))
    NPMV="$(npm view "$NPM_PKG@$BASE" version 2>/dev/null || echo "")"
    [ "$NPMV" = "$BASE" ] && break
    printf '  ... npm view tentativa %s/5 devolveu "%s"; aguardando 30s\n' "$_nv" "$NPMV"
    sleep 30
  done
  if [ "$NPMV" != "$BASE" ]; then
    [ "$TERMINAL_MODE" -eq 1 ] && die "estado TERMINAL: npm view ilegivel mas o GA JA esta completo — verifique manualmente"
    gh release edit "$TAG" --draft \
      || die "npm view nao confirmou E o draft falhou — rode: gh release edit $TAG --draft; me chame no Claude"
    die "npm view devolveu '$NPMV' apos 5 tentativas — GA em DRAFT; re-rode este script quando o registry confirmar"
  fi
  # RECIBO do publish DESTA arvore: o run pode terminar success por already_published
  # (a versao no registry seria de OUTRA arvore). Exige o step de publish = success.
  _pubc="$(gh run view "$NID" --json jobs \
    --jq '[.jobs[].steps[]|select(.name|startswith("Publish (Trusted Publishing"))][0].conclusion' 2>/dev/null || echo "")"
  if [ "$_pubc" != "success" ]; then
    [ "$TERMINAL_MODE" -eq 1 ] && die "estado TERMINAL: recibo ilegivel mas o GA JA esta completo — verifique manualmente"
    gh release edit "$TAG" --draft \
      || die "publish step '$_pubc' E o draft falhou — rode: gh release edit $TAG --draft; me chame no Claude"
    die "step de publish concluiu '$_pubc' (skipped = registry ja tinha $BASE de OUTRA arvore) — GA em DRAFT; triagem comigo no Claude"
  fi
  printf '   npm confirmado: %s@%s (recibo do step Publish: success)\n' "$NPM_PKG" "$NPMV"
  mark_step 18
fi

if should 19; then
  say "19/20 rechecks finais (tag, rc.1, main) + UNDRAFT do GitHub Release (GA, nao pre-release)"
  # Recheck do OBJETO da tag no remoto: nao pode ter sido deletada/movida.
  _ft="$(git ls-remote origin "refs/tags/$TAG" "refs/tags/$TAG^{}")" \
    || die "ls-remote final da tag falhou (transporte)"
  _fp="$(printf '%s\n' "$_ft" | awk -v r="refs/tags/$TAG" '$2==r{print $1}')"
  _fpe="$(printf '%s\n' "$_ft" | awk -v r="refs/tags/$TAG^{}" '$2==r{print $1}')"
  [ "$_fp" = "$(git rev-parse "$TAG")" ] \
    || die "a tag remota NAO e mais o objeto assinado local — me chame no Claude"
  [ -z "$_fpe" ] || [ "$_fpe" = "$(git rev-parse "$TAG^{commit}")" ] \
    || die "peel remoto final da tag diverge — me chame no Claude"
  # Recheck do OBJETO da rc.1 tambem.
  _fr="$(git ls-remote origin "refs/tags/$RC_TAG" "refs/tags/$RC_TAG^{}")" \
    || die "ls-remote final da $RC_TAG falhou"
  [ "$(printf '%s\n' "$_fr" | awk -v r="refs/tags/$RC_TAG" '$2==r{print $1}')" = "$(git rev-parse "$RC_TAG")" ] \
    || die "$RC_TAG remota mudou durante as esperas — me chame no Claude"
  # main nao pode ter sido REVERTIDO: o commit da tag segue na cadeia first-parent
  # de origin/main. Um push de outra sessao DEPOIS do push da tag nao e rollback (o
  # Release e o npm sao da tag) — e aviso, nao morte com o npm ja publicado.
  git fetch --quiet origin main || die "fetch final falhou"
  _tc="$(git rev-parse "$TAG^{commit}")" || die "rev-parse do commit da tag falhou"
  if [ "$(git rev-parse origin/main)" != "$_tc" ]; then
    _fpl="$(git rev-list --first-parent origin/main)" || die "rev-list de origin/main falhou"
    grep -qxF -- "$_tc" <<FPL || die "o commit da tag GA NAO esta na cadeia first-parent de origin/main — rollback ou force-push? O Release segue em DRAFT: me chame no Claude ANTES de anunciar"
$_fpl
FPL
    printf '   AVISO: main andou depois da tag (%s commit(s) sobre ela); a tag segue na cadeia first-parent\n' \
      "$(git rev-list --count "$_tc..origin/main")"
  fi
  _prj="$(gh release view "$TAG" --json isPrerelease,isDraft 2>/dev/null || echo "")"
  _pr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
  _dr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
  [ "$_pr" = "False" ] \
    || die "GitHub Release do $TAG ausente ou marcado pre-release (isPrerelease='$_pr') — me chame no Claude"
  # UNDRAFT por ultimo: todos os rechecks acima verdes.
  if [ "$_dr" = "True" ]; then
    gh release edit "$TAG" --draft=false \
      || die "undraft final falhou — rode: gh release edit $TAG --draft=false"
  fi
  _fdr="$(gh release view "$TAG" --json isDraft,isPrerelease,publishedAt 2>/dev/null || echo "")"
  _fd="$(printf '%s' "$_fdr" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
  _fpr="$(printf '%s' "$_fdr" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
  _pub="$(printf '%s' "$_fdr" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("publishedAt") or "")' 2>/dev/null || echo "")"
  if [ "$_fd" != "False" ] || [ "$_fpr" != "False" ] || [ -z "$_pub" ]; then
    [ "${TERMINAL_MODE:-0}" -eq 1 ] \
      && die "estado final ilegivel/invalido (isDraft='$_fd' isPrerelease='$_fpr') em modo TERMINAL — NAO mutei o Release; verifique manualmente"
    if gh release edit "$TAG" --draft \
       && [ "$(gh release view "$TAG" --json isDraft --jq .isDraft 2>/dev/null || echo "")" = "true" ]; then
      die "estado final do Release invalido (isDraft='$_fd' isPrerelease='$_fpr') — re-draftado E VERIFICADO; me chame no Claude"
    fi
    die "estado final do Release invalido (isDraft='$_fd' isPrerelease='$_fpr') e o re-draft NAO se confirmou — O GA PODE ESTAR PUBLICO EM ESTADO INVALIDO; verifique AGORA: gh release view $TAG"
  fi
  # O publishedAt tem de ser DESTA cerimonia (release stale de tentativa abortada).
  _pe="$(python3 - "$_pub" <<'PYPB'
import sys, datetime
try:
    print(int(datetime.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")).timestamp()))
except Exception:
    print("BAD")
PYPB
)"
  [ "$_pe" != "BAD" ] || die "publishedAt ilegivel"
  # O piso e o epoch que o passo 16 grava ANTES do push. Sem ele (o 16 feito a mao),
  # o piso e a data do objeto da tag, criado no passo 15 DESTA cerimonia — nunca 0,
  # que tornaria esta conferencia vacua.
  _tpe=""
  if [ -f "$EV/.tag-push-epoch" ] && [ ! -L "$EV/.tag-push-epoch" ]; then
    _tpe="$(tr -d ' \t\r\n' < "$EV/.tag-push-epoch")" || die "leitura de .tag-push-epoch falhou"
  fi
  case "$_tpe" in
    ''|*[!0-9]*)
      _tpe="$(git for-each-ref --format='%(taggerdate:unix)' "refs/tags/$TAG")" \
        || die "data da tag local ilegivel"
      case "$_tpe" in
        ''|*[!0-9]*) die "sem .tag-push-epoch e sem a data da tag local: nao consigo provar que o publishedAt e desta cerimonia — me chame no Claude" ;;
      esac
      printf '   (.tag-push-epoch ausente: o piso e a data do objeto da tag, %s)\n' "$_tpe" ;;
  esac
  [ "$_pe" -ge $(( _tpe - 300 )) ] \
    || die "publishedAt e ANTERIOR a esta cerimonia (release stale?) — me chame no Claude"
  printf '   GA publicado NAO-draft, NAO pre-release (publishedAt %s)\n' "$_pub"
  mark_step 19
fi

if should 20; then
  say "20/20 confirmacao final: npm view + GitHub Release"
  _lat="$(npm view "$NPM_PKG" version 2>/dev/null || echo "?")"
  _exact="$(npm view "$NPM_PKG@$BASE" version 2>/dev/null || echo "?")"
  printf '   npm: %s latest=%s ; %s@%s=%s\n' "$NPM_PKG" "$_lat" "$NPM_PKG" "$BASE" "$_exact"
  [ "$_exact" = "$BASE" ] || die "npm view $NPM_PKG@$BASE nao devolve $BASE — verifique o registry"
  [ "$_lat" = "$BASE" ] || printf '   AVISO: dist-tag latest = %s (esperado %s) — conferir no npm\n' "$_lat" "$BASE"
  gh release view "$TAG" --json url,isDraft,isPrerelease,publishedAt 2>/dev/null \
    || printf '   (gh release view nao respondeu — confira no site)\n'
  mark_step 20
fi

# O banner de PUBLICADO so com o passo 20 concluido. Sem ele: --until parou antes
# (rc 0, pendentes listados) ou algum passo ficou pendente (rc 3, nunca o banner).
if ! done_step 20; then
  if [ "$UNTIL" -lt 20 ]; then
    printf '\nPARADO depois do passo %s (--until). Passos pendentes:%s\n' "$UNTIL" "$(pending_steps)"
    printf 'Re-rode este script (sem --until) para seguir de onde parou.\n'
    exit 0
  fi
  printf '\nFAIL: o corte NAO terminou — passos pendentes:%s\n' "$(pending_steps)" >&2
  printf '(um --from pulou passo nao concluido? Re-rode sem --from para retomar.)\n' >&2
  exit 3
fi
bell "$TAG cortada"
cat <<DONE

============================================================
 GA $TAG PUBLICADO: GitHub Release publico (nao pre-release) e
 npm $NPM_PKG@$BASE com recibo do step de publish.
 Freeze de main ENCERRADO. Proximos passos (me chame no Claude):
 - closeout: CLAUDE.md e o LEDGER do PLAN-192 registram o GA, e o que
   houver em ~/.ceo-ga-archive/ (tentativas arquivadas) entra no plano;
 - adopters: upgrade.sh --pin $TAG, com a cerimonia gravada ou passada;
 - a cura estrutural do relaunch --out (a opcao B), fora deste corte;
 - abertos: o anexo da v1.4.0 (condicao 1: a 1.4.2 expressa o re-declara,
   sem versao prometida para a cura); o hook que copia o scriptPath antes
   da decisao de permissao (condicao 23, cura alvejada para a 1.4.2); os
   achados abertos da rc.1 e deste GA (vereditos em repass-rc1/ e
   repass-ga/), sem versao prometida.
============================================================
DONE
