#!/bin/bash
# OWNER-RC1-CUT.sh — corte da v1.4.3-rc.1 em UM comando (PLAN-194).
#
#   bash .claude/plans/PLAN-194/OWNER-RC1-CUT.sh [--restamp] [--from <1-20>] [--until <1-20>] [--g0-only]
#
# CEREMONY-LINT: handwritten-exception: DERIVADO por
# .claude/plans/PLAN-194/derive-kit-143.py do script de corte da v1.4.2-rc.1 (fonte e
# sha256 em SOURCES, no derivador; o molde foi escrito contra o corpus
# `.claude/plans/PLAN-188/ceremony-defect-corpus-S348.md`), com as curas que o kit do
# GA v1.4.2 acrescentou depois do kit da rc.1 dele. NAO edite a mao. Ensaiado por
# test-rc1-kit.sh.
#
# PRE-REQUISITOS (a ordem do trem, PLAN-194):
#  (a) o GA v1.4.2 CORTADO (2026-09-30): a tag v1.4.2 existe, anotada e assinada, local e
#      no remoto — ela e a BASE deste re-pass. O G0 confere e recusa pelo nome se ela nao
#      existe.
#  (b) os lands da 1.4.3 em main, pushados e com CI verde: os livres (entre eles ESTE
#      kit, commitado — o G0 confere), o re-pin do Codex 0.160.0, a W4 (o job da prova do
#      toolchain da rc no npm-publish.yml; sem ele o G0 recusa nomeando o job) e a
#      relmeta-143, que poe o driver na 1.4.3 (sem ela o G0 recusa nomeando o pack).
#  (c) a SONDA das condicoes verde contra o HEAD: o G0 roda probe-conditions-rc1.py e
#      recusa, nomeando a afirmacao, se uma condicao declarada ficou falsa contra o
#      codigo que landou (ou se uma parte passaria do teto do redator). Corrija ANTES:
#      nunca mande ao revisor um texto falso contra o codigo.
#  (d) a maquina QUIETA nos passos 1 e 15: o preflight roda a suite serial de hooks, e
#      testes de desempenho com teto ABSOLUTO de p99
#      (TestOutputScanPerfRigorous::test_p99_*) reprovam sob carga de CPU — foi o que
#      matou a 1.a tentativa da v1.4.1-rc.1. O script mede a carga e avisa antes.
#  (e) FREEZE de main: do G0 ate o push da tag (passo 16) NENHUMA sessao pusha em main
#      (o passo 5 e o pre-push do 16 recusam main que andou; o passo 5 recusa tambem um
#      candidato que nao e o commit que os passos 1, 2 e 4 conferiram). Depois do 16, um
#      push alheio nao derruba a retomada (G0) nem o passo 19 enquanto a tag seguir na
#      cadeia first-parent de origin/main. Durante o freeze, os runs AGENDADOS (cron) de
#      QUALQUER workflow sobre o commit congelado CONTAM nos passos 4 e 14 e nos
#      preflights 1 e 15: um vermelho agendado tem a rota do vermelho de CI (abaixo), e
#      um agendado AINDA RODANDO faz o preflight recusar («a workflow for HEAD is still
#      running»: espere e re-rode). Janelas a evitar (INICIO dos crons de
#      .github/workflows/, UTC): todo dia 06:43, 07:00, 07:37 e 11:00; as segundas, dez
#      entre 03:00 e 19:23; no dia 1 do mes, 04:00 e 07:00.
#  (f) CLAUDE.md abaixo do limite do validate-governance.sh COMPLETO (40000 bytes, ou
#      CLAUDE_MD_SIZE_LIMIT): o preflight o roda com a saida suprimida; o G0 confere antes.
#  (g) nenhum commit da faixa v1.4.2..HEAD cita plano (PLAN-NNN) ou toca ADR fora do
#      RELEASE_SCOPE do release.sh: a linha Scope da anotacao ASSINADA da tag sai de la.
#      O G0 confere.
#
# RESUMIVEL. Cada passo grava um marcador em repass-rc1/.cut-state; os passos 1, 2 e 4
# gravam tambem o commit que conferiram (SHA-1, SHA-2P/SHA-2, SHA-4), e o passo 5 os
# cobra do candidato. Rodar de novo RETOMA do primeiro passo nao concluido. `--from N`
# PULA os passos < N ainda nao concluidos — o script os NOMEIA antes de seguir (use so
# para passos que voce fez a mao; eles seguem pendentes). `--until N` para depois do
# passo N; `--g0-only` roda so as pre-condicoes. O banner de CORTADA so sai com os 20
# passos concluidos (M3-02); sem isso o script lista os passos pendentes.
# `--from` nao marca nada, e nao resolve os passos que deixam OBJETOS que o G0 confere
# pelo .cut-state: o commit do veredito (11), a tag local (15) e a tag no remoto (16).
# O G0 (tambem sob --g0-only) reconhece e REGISTRA um push da tag que ficou sem o
# marcador do 16 (o remoto tem o objeto assinado local). Para o 15 a recusa nomeia a
# rota (`git tag -d`, com a tag fora do remoto). Para o 11 (commit do veredito sem o
# marcador) ela manda NAO pushar e chamar o Claude: o guard do passo 12 ainda nao
# conferiu aquele commit. Entre os passos 5 e 11 o G0 exige HEAD == CANDIDATE.sha: um
# .cut-state de tentativa anterior e recusado. Entre os passos 2 e 3 (o commit do bump
# ja em main LOCAL, o push do 3 falhou ou nao rodou) o G0 reconhece a retomada — o HEAD
# e o commit que o passo 2 gravou, `release: v1.4.3` direto sobre origin/main — e o
# passo 3 pusha. O passo 10 escreve o envelope NAO rastreado em .claude/governance/
# (fora do plano) ANTES de se marcar, e um passo 11 que morreu entre o `git add` e o
# `git commit` deixa caminhos da lista literal dele STAGED: SO nesse intervalo (passo 9
# concluido, 11 nao, HEAD == candidato) o G0 admite o envelope exato e esse staging, e
# a retomada do passo 11 desfaz o staging (nada foi commitado) e o refaz.
#
# OS MOMENTOS EM QUE VOCE PARTICIPA:
#   Enter       passos 1 e 15  SO se a carga da maquina estiver alta (o aviso diz)
#   pinentry    passos 1 e 15  a sonda de assinatura do preflight (e a tag, no 15) podem
#                              pedir a senha. Desde a relmeta-142 a sonda chama o gpg com
#                              --yes e nao pergunta «Overwrite?»; o script confere o driver
#                              e so pede o `y` se ele nao tiver o --yes
#   Enter       passo 2   confirmar que releu npm/README.md
#   Enter       passo 6   SO se o re-pass tiver de rodar com OPENAI_API_KEY no ambiente (o
#                         aviso diz; rode este script com  unset OPENAI_API_KEY)
#   Enter       passo 7   ler as condicoes que entram no material assinado
#   Enter       passo 9   depois de ler o conteudo; e o pinentry do verdict-fields
#   SIM         passo 16  confirmar o push da tag (o passo irreversivel)
#
# A rc NAO publica no npm: o job do publish do npm-publish.yml pula tags com `-rc.`; o
# passo 18 confere o controle positivo do gate (o job «Await release-gate» = success,
# casado pelo PREFIXO do nome, que carrega o sufixo « (release.yml)») e, pelo nome
# EXATO, a prova do toolchain da rc (o job «RC toolchain proof (no publish)» =
# success), que a W4 do PLAN-194 acrescentou e que nunca publica.
#
# O QUE ESTE SCRIPT NUNCA FAZ SOZINHO: empurrar a tag sem o SIM, publicar no npm, ou
# editar qualquer pin do codex.
#
# CI VERMELHO so no gate de latencia de hooks, num commit cujo diff contra o pai nao
# tem .py de hooks (o commit do bump e o do veredito nao tem) — inclusive num run
# AGENDADO sobre o mesmo commit: e drift de runner — `gh run rerun <id> --failed`,
# espere o verde e re-rode este script (ele retoma). NUNCA faca patch. Vale para os
# passos 4 e 14 e para os preflights 1 e 15.
#
# Topologia herdada (S349): bump e preflight num clone descartavel de HEAD; o
# candidato e o que o passo 5 GRAVOU, nunca o HEAD do momento; evidencia + fields +
# veredito num commit SO, direto sobre o candidato (o release.yml exige parent_sha ==
# PAI do commit que introduz o veredito).
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

PLAN_DIR=".claude/plans/PLAN-194"
EV="$PLAN_DIR/repass-rc1"
RUNNER="$EV/run-rc1-repass.sh"
PROBE="$EV/probe-conditions-rc1.py"
GEN="$PLAN_DIR/gen-envelope-rc1.py"
TAG="v1.4.3-rc.1"
BASE="1.4.3"
RCN="1"
# A base do re-pass e da faixa da release: o GA v1.4.2 (cortado em 2026-09-30).
BASE_TAG="v1.4.2"
KEY="CFCFACF00335DC74"
# O job da rc que a W4 acrescentou ao npm-publish.yml: o passo 18 exige success nele PELO
# NOME (o `name:` que `gh run view --json jobs` devolve), e o G0 recusa um HEAD sem ele.
RC_PROOF_JOB="RC toolchain proof (no publish)"
VF="$PLAN_DIR/verdict-fields-$TAG.md"
VD=".claude/governance/pair-rail-verdict-$TAG.md"
COND="$EV/CONDITIONS-rc1.md"
STATE="$EV/.cut-state"
RELEASE=".claude/scripts/local/release.sh"
GUARD=".claude/scripts/local/_release_tag_guard.py"
TODAY="$(date -u +%Y-%m-%d)"
# Teto da espera de CI (passos 4 e 14), em minutos: o Smoke Install levou 1h51 no
# candidato da v1.4.1-rc.1 e matou a 3.a tentativa dela com o teto antigo de 90 — e o
# commit do bump (.claude/.framework-version) o dispara.
CI_WAIT_MAX_MIN="${RC1_CI_WAIT_MAX_MIN:-150}"
case "$CI_WAIT_MAX_MIN" in
  ''|*[!0-9]*|0) printf 'FAIL: RC1_CI_WAIT_MAX_MIN invalido: %s\n' "$CI_WAIT_MAX_MIN" >&2; exit 1 ;;
esac
# Onde uma tentativa do re-pass e ARQUIVADA: FORA do repositorio (o G0 recusa arquivo
# nao rastreado no plano fora da evidencia deste corte, e o runner recusa rodar sobre
# evidencia anterior). O diretorio arquivado entra no plano no closeout.
ARCHIVE_ROOT="$HOME/.ceo-rc1-archive"
# O vermelho dos preflights (passos 1 e 15): o driver diz so a frase, e o
# validate-governance.sh roda la dentro com a saida suprimida.
PREFLIGHT_RED_HINT="O preflight conta QUALQUER workflow sobre este commit, agendado (cron) inclusive.
Se o motivo e «a workflow for HEAD is still running»: espere o run terminar e re-rode
este script (ele retoma deste passo).
Se o motivo e «a workflow for HEAD is not green» e o vermelho e SO o gate de latencia
de hooks, num commit cujo diff contra o pai nao tem .py de hooks, e drift de runner: rode
  gh run rerun <run> --failed
espere o verde e re-rode este script (ele retoma deste passo). NUNCA faca patch.
Se o motivo e «hooks test suite failed (serial)»: e a carga da maquina (os testes de
p99 com teto absoluto). Feche o que pesa, espere a carga cair e re-rode este script
(ele retoma deste passo).
Se o motivo e outro «... test suite failed (...)» (hooks nao serial, ou scripts): o
driver suprime a saida do pytest. No diretorio onde o preflight rodou (o passo 1 diz o
clone; o passo 15 roda nesta arvore), rode o MESMO pytest sem a saida suprimida, para
nomear o teste — o dos scripts:
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -m 'not serial' --strict-markers -p no:cacheprovider -q --tb=short
(o dos hooks: .claude/hooks/tests/ no lugar das duas pastas; a passada serial: -m 'serial').
Um teste que falha aqui e passou no CI pode depender das TAGS: o checkout do CI e raso e
o teste pula la. Com o nome do teste, me chame no Claude.
Se o motivo e «validate-governance.sh nonzero» (o preflight suprime a saida), rode
  bash .claude/scripts/validate-governance.sh
e leia as linhas FAIL. Qualquer outro motivo: me chame no Claude."
# O kit que TEM de estar commitado e identico ao HEAD antes do corte (G0): os 9
# arquivos. Um derivador ou harness untracked passaria o G0 e mataria o passo 15.
KIT_TRACKED="$RUNNER $PROBE $GEN $EV/README-rc1.md $COND $EV/.gitignore $PLAN_DIR/OWNER-RC1-CUT.sh"
KIT_TRACKED="$KIT_TRACKED $PLAN_DIR/derive-kit-143.py $PLAN_DIR/test-rc1-kit.sh"

RESTAMP=""
FROM=0
UNTIL=20
G0_ONLY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --restamp) RESTAMP="--restamp" ;;
    --from)
      # Sem valor, o `shift` do fim do laco falharia sob set -e: rc 1 MUDO.
      [ "$#" -ge 2 ] || { printf 'FAIL: --from exige um passo de 1 a 20 (veio: nada)\n' >&2; exit 2; }
      shift; FROM="$1" ;;
    --until)
      [ "$#" -ge 2 ] || { printf 'FAIL: --until exige um passo de 1 a 20 (veio: nada)\n' >&2; exit 2; }
      shift; UNTIL="$1" ;;
    --g0-only) G0_ONLY=1 ;;
    *) printf 'uso: %s [--restamp] [--from <1-20>] [--until <1-20>] [--g0-only]\n' "$0" >&2; exit 2 ;;
  esac
  shift
done
# Passo = inteiro de 1 a 20 (o --from padrao 0 = sem --from). Qualquer outra coisa e
# recusa: um --from nao numerico fazia o `[ -ge ]` de should() falhar em todos os
# passos e o script terminava com o banner sem rodar nada.
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
# O ultimo registro `<CHAVE> <commit>` do .cut-state (vazio se ausente).
state_sha() {
  awk -v k="$1" '$1 == k { v = $2 } END { print v }' "$STATE"
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
  local sha="$1" i info n p b vid vj vs vf vp vo tt vt vq lim
  # O teto de cada consulta pelo commit: uma consulta que volta CHEIA nao prova que nao ha
  # vermelho nem pendente fora da janela, e e recusa nomeada (fail-closed).
  lim=200
  sha="$1"; i=0
  while :; do
    i=$((i+1)); [ "$i" -le "$CI_WAIT_MAX_MIN" ] \
      || die "CI nao terminou em $CI_WAIT_MAX_MIN min — re-rode este script: ele retoma deste passo (RC1_CI_WAIT_MAX_MIN=<min> estica o teto)"
    sleep 60
    info="$(gh run list --commit "$sha" --limit "$lim" --json headSha,status,conclusion \
      --jq "length as \$t | [.[]|select(.headSha==\"$sha\")] | \
{t:\$t, n:length, p:[.[]|select(.status!=\"completed\")]|length, \
b:[.[]|select(.status==\"completed\" and .conclusion!=\"success\" \
and .conclusion!=\"skipped\")]|length}" 2>/dev/null || echo "")"
    [ -n "$info" ] || { printf '  ... gh falhou, tentando de novo\n'; continue; }
    n="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["n"])')" \
      || { printf '  ... resposta do gh ilegivel, tentando de novo\n'; continue; }
    p="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["p"])')" \
      || { printf '  ... resposta do gh ilegivel, tentando de novo\n'; continue; }
    b="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["b"])')" \
      || { printf '  ... resposta do gh ilegivel, tentando de novo\n'; continue; }
    tt="$(printf '%s' "$info" | python3 -c 'import json,sys;print(json.load(sys.stdin)["t"])')" \
      || { printf '  ... resposta do gh ilegivel, tentando de novo\n'; continue; }
    [ "$tt" -lt "$lim" ] || die "consulta cheia: $tt runs no commit $sha (o teto da consulta e $lim); nao da
para provar que nao ha vermelho nem pendente fora da janela — me chame no Claude"
    printf '  ... runs=%s pendentes=%s vermelhos=%s\n' "$n" "$p" "$b"
    if [ "$b" -ne 0 ]; then
      gh run list --commit "$sha" --limit 200 --json headSha,status,conclusion,workflowName,databaseId,event \
        --jq ".[]|select(.headSha==\"$sha\" and .status==\"completed\" and .conclusion!=\"success\" and .conclusion!=\"skipped\")|\"   vermelho: \" + .workflowName + \" (run \" + (.databaseId|tostring) + \", \" + .conclusion + \", evento \" + .event + \")\"" \
        || printf '   (gh nao listou os runs vermelhos)\n'
      die "workflow vermelho para $sha (conta QUALQUER workflow e evento sobre o commit,
inclusive um run AGENDADO (cron) durante o freeze).
Se o vermelho e SO o gate de latencia de hooks e o diff deste commit contra o pai nao
tem .py de hooks (o commit do bump e o do veredito nao tem), e drift de runner: rode
  gh run rerun <run> --failed
espere ficar verde e re-rode este script (ele retoma deste passo). NUNCA faca
patch. Qualquer outro vermelho: me chame no Claude."
    fi
    if [ "$n" -gt 0 ] && [ "$p" -eq 0 ]; then break; fi
  done
  vq="$(gh run list --workflow validate.yml --commit "$sha" --limit "$lim" \
    --json headSha,databaseId,status,conclusion,event,headBranch \
    --jq "(length|tostring) + \" \" + ([.[]|select(.headSha==\"$sha\" and .status==\"completed\" and .conclusion==\"success\" and .event==\"push\" and .headBranch==\"main\")][0].databaseId|tostring)" 2>/dev/null || echo "")"
  vt="${vq%% *}"; vid="${vq#* }"
  [ -n "$vq" ] && [ -n "$vid" ] && [ "$vid" != "null" ] \
    || die "nenhum run COMPLETO e success do validate.yml para $sha"
  case "$vt" in ""|*[!0-9]*) die "resposta do gh run list do validate.yml ilegivel: $vq" ;; esac
  [ "$vt" -lt "$lim" ] || die "consulta cheia: $vt runs do validate.yml no commit $sha (o teto da consulta e $lim);
nao da para provar que nao ha vermelho nem pendente fora da janela — me chame no Claude"
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
  awk '{print $2}' "$EV/MANIFEST-rc1.sha256" | sed "s|^|$EV/|"
  printf '%s\n' "$EV/MANIFEST-rc1.sha256" "$EV/README-rc1.md"
  if [ -f "$COND" ]; then printf '%s\n' "$COND"; fi
}
# Evidencia COMPLETA, verificada e GO para o candidato $1 — o que o CEO deixa
# pronto quando roda o re-pass ANTES desta cerimonia. Quatro fontes concordam:
# MANIFEST (shasum -c), RUNNER-OVERALL rc=0, o candidato da PROVENANCE e o
# CANDIDATE.sha que o runner leu. O gerador revalida todos os vereditos
# e os mesmos bytes de condicoes antes da assinatura e da montagem.
evidence_complete_for() {
  [ -f "$EV/MANIFEST-rc1.sha256" ] || return 1
  ( cd "$EV" && shasum -a 256 -c MANIFEST-rc1.sha256 --status ) 2>/dev/null || return 1
  grep -qE '^RUNNER-OVERALL: rc=0$' "$EV/PROVENANCE-rc1.md" 2>/dev/null || return 1
  grep -qF -- "Candidato: $1 (" "$EV/PROVENANCE-rc1.md" 2>/dev/null || return 1
  [ "$(tr -d ' \t\r\n' < "$EV/CANDIDATE.sha" 2>/dev/null)" = "$1" ] || return 1
}

# --- o kit tem de estar COMMITADO e identico ao HEAD ------------------------
# O README e as condicoes entram no commit do veredito e o passo 11 exige que sejam
# identicos ao HEAD; o preflight roda num clone de HEAD, que nao ve arquivo untracked;
# o runner roda a sonda do CANDIDATO. Um kit derivado e nao commitado so apareceria como
# recusa no passo 11 ou 12 — depois da assinatura. Aqui ele e recusado ANTES, pelo nome.
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
  [ -z "$miss" ] || die "o kit da $TAG nao esta commitado como o HEAD:$miss
Rode derive-kit-143.py --check (tem de dar OK), commite e pushe o kit, espere o
CI verde e re-rode este script."
  printf '   OK: kit da %s commitado e identico ao HEAD\n' "$TAG"
}

# --- a evidencia deste corte e o UNICO untracked tolerado no plano ------------
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

# --- residuo de um corte ANTERIOR: o .tag-push-epoch dele fora do git ----------
# O passo 16 dos cortes deste molde grava `<evidencia>/.tag-push-epoch` (o piso do passo
# 19), que o git nao ignora; ele entra no plano no closeout daquele corte (o da
# v1.4.1-rc.1 entrou em 4606c3df). Sem o closeout ele fica NAO rastreado, e o passo 15
# deste corte (o `release.sh tag` recusa untracked) morreria depois do push do veredito.
# Aqui ele e recusado pelo nome, com a rota; o deste corte (em $EV/) nao conta.
assert_no_foreign_cut_residue() {
  local f line p bad
  f="$(mktemp)" || die "mktemp falhou"
  if ! git status --porcelain=v1 --untracked-files=all -- .claude/plans/ > "$f"; then
    rm -f "$f"; die "git status dos planos falhou — nao vou tratar como limpo"
  fi
  bad=""
  while IFS= read -r line; do
    case "$line" in
      '??'*)
        p="${line#???}"
        case "$p" in
          "$EV/"*) : ;;
          .claude/plans/*/.tag-push-epoch) bad="$bad $p" ;;
        esac ;;
    esac
  done < "$f"
  rm -f "$f"
  [ -z "$bad" ] || die "o .tag-push-epoch de um corte ANTERIOR esta fora do git:$bad
O passo 16 daquele corte o grava (o piso do passo 19 dele); ele entra no git no closeout
daquele corte, e o passo 15 DESTE corte recusaria a arvore com ele. Commite e pushe-o
ANTES deste corte, sem citar plano no assunto (a linha Scope assinada da tag sai dos
PLAN-NNN dos assuntos de commit da faixa):
  git add --$bad
  git commit -m 'closeout do corte anterior: .tag-push-epoch do passo 16'
  git push origin HEAD:refs/heads/main
espere o CI verde e re-rode este script."
}

# --- a BASE: a tag do GA v1.4.2, resolvida (nunca pinada: vale o objeto do momento) ----
# Tag ANOTADA; `git verify-tag` com o signatario (a chave primaria do VALIDSIG) em
# .claude/sentinel-signers.txt; o MESMO objeto no remoto (transporte falhando e erro,
# nunca "ausente"); ancestral do HEAD. Recusa pelo nome quando ela nao existe.
assert_base_tag() {
  local _bt_type _bt_raw _bt_fpr _bt_signers _bt_rls _bt_plain _bt_peel _bt_obj _bt_com
  git rev-parse -q --verify "refs/tags/$BASE_TAG" >/dev/null 2>&1 \
    || die "a tag base $BASE_TAG nao existe neste repositorio: falta git fetch origin tag $BASE_TAG
(o GA v1.4.2 foi cortado em 2026-09-30)"
  _bt_type="$(git cat-file -t "refs/tags/$BASE_TAG")" || die "cat-file da $BASE_TAG falhou"
  [ "$_bt_type" = "tag" ] || die "$BASE_TAG nao e uma tag ANOTADA (tipo: $_bt_type)"
  _bt_obj="$(git rev-parse "refs/tags/$BASE_TAG")" || die "rev-parse da $BASE_TAG falhou"
  _bt_com="$(git rev-parse "refs/tags/$BASE_TAG^{commit}")" || die "rev-parse do commit da $BASE_TAG falhou"
  _bt_raw="$(git verify-tag --raw "$BASE_TAG" 2>&1)" \
    || die "assinatura da $BASE_TAG nao verifica (a chave publica do Owner esta no chaveiro?)"
  _bt_fpr="$(printf '%s\n' "$_bt_raw" | awk '$2=="VALIDSIG"{print $NF; exit}')"
  [ -n "$_bt_fpr" ] || die "a verificacao da $BASE_TAG nao trouxe VALIDSIG"
  _bt_signers="$(grep -v '^[[:space:]]*#' .claude/sentinel-signers.txt | awk 'NF{print toupper($1)}')" \
    || die "leitura de .claude/sentinel-signers.txt falhou"
  if [ "${RC1_SELFTEST:-}" = "1" ]; then
    # Seam de AUTO-TESTE (o MESMO do runner e do gerador do envelope), recusado fora do
    # scratchpad declarado: so troca QUAL fingerprint e aceita para a tag base da fixture.
    local _st_scr
    _st_scr="$(cd "${RC1_SELFTEST_SCRATCH:-/nonexistent}" 2>/dev/null && pwd -P)" || _st_scr=""
    [ -n "$_st_scr" ] || die "RC1_SELFTEST=1 sem RC1_SELFTEST_SCRATCH valido — recusado"
    case "$(pwd -P)/" in
      "$_st_scr"/*) : ;;
      *) die "RC1_SELFTEST=1 fora do scratchpad declarado — recusado" ;;
    esac
    case "${RC1_SELFTEST_SIGNER_FPR:-}" in
      ''|*[!0-9A-F]*) die "auto-teste exige RC1_SELFTEST_SIGNER_FPR (40 hex maiusculos)" ;;
    esac
    [ "${#RC1_SELFTEST_SIGNER_FPR}" -eq 40 ] || die "auto-teste exige RC1_SELFTEST_SIGNER_FPR (40 hex maiusculos)"
    printf '   AVISO: auto-teste — signatario aceito para a %s trocado para %s\n' "$BASE_TAG" "$RC1_SELFTEST_SIGNER_FPR"
    _bt_signers="$RC1_SELFTEST_SIGNER_FPR"
  fi
  grep -qxF -- "$_bt_fpr" <<BTSIG || die "a $BASE_TAG foi assinada por $_bt_fpr, que NAO esta em .claude/sentinel-signers.txt"
$_bt_signers
BTSIG
  _bt_rls="$(git ls-remote origin "refs/tags/$BASE_TAG" "refs/tags/$BASE_TAG^{}")" \
    || die "git ls-remote da $BASE_TAG falhou (transporte) — nao vou assumir ausente; re-rode este script"
  _bt_plain="$(printf '%s\n' "$_bt_rls" | awk -v r="refs/tags/$BASE_TAG" '$2==r{print $1}')"
  _bt_peel="$(printf '%s\n' "$_bt_rls" | awk -v r="refs/tags/$BASE_TAG^{}" '$2==r{print $1}')"
  [ -n "$_bt_plain" ] || die "$BASE_TAG ausente no REMOTO: o push da tag do GA nao aconteceu"
  [ "$_bt_plain" = "$_bt_obj" ] || die "$BASE_TAG remota nao e o objeto assinado local — me chame no Claude"
  [ -z "$_bt_peel" ] || [ "$_bt_peel" = "$_bt_com" ] || die "peel remoto da $BASE_TAG diverge do commit local"
  git merge-base --is-ancestor "$_bt_com" HEAD \
    || die "HEAD nao descende da $BASE_TAG — a 1.4.3 sai da arvore do GA v1.4.2"
  printf '   OK: base %s (tag anotada, assinada por %s, o mesmo objeto no remoto, ancestral do HEAD)\n' \
    "$BASE_TAG" "$(printf '%s' "$_bt_fpr" | cut -c25-40)"
}

# --- o job da prova do toolchain da rc (W4) no npm-publish.yml -------------------
# O passo 18 exige `success` nele PELO NOME, e ele so roda depois do push da tag: sem ele
# na arvore que a tag vai levar, o corte morreria no passo 18 com a tag ja publica. Antes do
# passo 15 a arvore e o HEAD; depois, a da tag.
assert_rc_proof_job() {
  local _ref _wf _v
  _ref="HEAD"
  if done_step 15; then _ref="$TAG^{commit}"; fi
  _wf="$(mktemp)" || die "mktemp falhou"
  git show "$_ref:.github/workflows/npm-publish.yml" > "$_wf" 2>/dev/null \
    || { rm -f "$_wf"; die "o npm-publish.yml nao existe em $_ref (git show falhou)"; }
  _v="$(python3 - "$_wf" "$RC_PROOF_JOB" <<'PYRCJ'
import re, sys
wf = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"(?m)^  rc-toolchain-proof:[ \t]*\n", wf)
if not m:
    print("o job rc-toolchain-proof nao existe")
    sys.exit(0)
rest = wf[m.end():]
nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:[ \t]*$|^[^ \t\n#]", rest)
blk = wf[m.start():m.end() + (nxt.start() if nxt else len(rest))]
names = re.findall(r"(?m)^    name:[ \t]*(.+?)[ \t]*$", blk)
ifs = re.findall(r"(?m)^    if:[ \t]*(.+?)[ \t]*$", blk)
if names != [sys.argv[2]]:
    print("o job rc-toolchain-proof se chama %r" % names)
elif ifs != ["contains(github.ref, '-rc.')"]:
    print("o job rc-toolchain-proof nao roda so nas tags -rc. (if: %r)" % ifs)
else:
    print("OK")
PYRCJ
)" || { rm -f "$_wf"; die "conferencia do job da prova do toolchain da rc falhou"; }
  rm -f "$_wf"
  [ "$_v" = "OK" ] || die "o npm-publish.yml de $_ref nao tem o job «${RC_PROOF_JOB}» (id rc-toolchain-proof, if: contains(github.ref, '-rc.')): $_v.
O passo 18 exige success nele PELO NOME, e ele so roda depois do push da tag. A W4 do
PLAN-194 ainda nao landou (ou o job mudou de nome: re-derive o kit com o nome novo):
lande-a, pushe, espere o CI verde e re-rode este script."
  printf '   OK: o npm-publish.yml de %s tem o job «%s» (so nas tags -rc.)\n' "$_ref" "$RC_PROOF_JOB"
}

# --- o `.gen-*.tmp` orfao de um gerador do envelope MORTO (R3C-01) ---------------
# O gerador escreve os fields (no plano) e o envelope (em .claude/governance/) por um
# temporario `.gen-*.tmp` no MESMO diretorio, e o apaga em todo erro que ele trata; morto
# por sinal (kill -9, a janela fechada no meio da escrita) ele o deixa para tras, e ali ele
# e um arquivo NAO rastreado que o G0 e o `release.sh tag` recusam — sem rota. Aqui ele e
# nomeado, com a rota: nunca e evidencia (o gerador re-escreve os fields e o envelope do
# zero no passo que os gera), e sai do repositorio SEM ser apagado.
assert_no_gen_orphans() {
  local _o _l=""
  for _o in "$PLAN_DIR"/.gen-*.tmp .claude/governance/.gen-*.tmp; do
    if [ -e "$_o" ] || [ -L "$_o" ]; then _l="$_l $_o"; fi
  done
  [ -z "$_l" ] || die "temporario de um gerador do envelope MORTO no meio da escrita:$_l
Nao e evidencia: o gerador re-escreve os fields e o envelope do zero no passo que os gera.
Tire-o do repositorio (sem apagar) e re-rode este script (ele retoma do passo em que parou):
  mkdir -p $ARCHIVE_ROOT/gen-orfaos && mv --$_l $ARCHIVE_ROOT/gen-orfaos/"
  printf '   OK: nenhum .gen-*.tmp orfao de um gerador morto\n'
}

# --- a rota 1 do codex, antes do runner (PLAN-194 D-4) --------------------------
# O runner so resolve o codex pela rota 1 (o binario global com o payload que o oraculo
# ADR-182 confere) e recusa a rota 2 pelo nome. Conferir o ORACULO aqui — sem executar o
# codex — evita uma tentativa parcial a arquivar so porque o codex global nao e o pinado.
assert_route1_available() {
  local _g
  _g="$(command -v codex 2>/dev/null)" || _g=""
  [ -n "$_g" ] || die "rota 1 indisponivel: nenhum codex no PATH. A rota 2 (npx) e recusa nomeada nesta release
(PLAN-194 D-4). Instale globalmente a versao que o manifesto ADR-182 pina (a do re-pin
assinado; nunca npm update -g) e re-rode este script (ele retoma do passo 6). Nada foi rodado."
  CLAUDE_PROJECT_DIR="$ROOT" python3 "$ROOT/.claude/hooks/check_pair_rail.py" --verify-codex-pin "$_g" >/dev/null 2>&1 \
    || die "rota 1 indisponivel: o payload do codex global ($_g) NAO confere com o manifesto ADR-182.
A rota 2 (npx) e recusa nomeada nesta release (PLAN-194 D-4). Instale globalmente a versao
que o manifesto pina (a do re-pin assinado; nunca npm update -g), confira com
  python3 .claude/hooks/check_pair_rail.py --verify-codex-pin \"\$(command -v codex)\"
e re-rode este script (ele retoma do passo 6). Nada foi rodado: nenhuma tentativa a arquivar."
  printf '   rota 1: o payload do codex global confere com o manifesto ADR-182 (conferido sem executa-lo)\n'
}

# --- a arvore limpa na retomada entre os passos 9 e 11 -----------------------------
# Depois do passo 10 o envelope ($VD) existe NAO rastreado FORA do plano (em
# .claude/governance/, por desenho), e um passo 11 que morreu entre o `git add` e o
# `git commit` deixa caminhos da lista literal dele STAGED. tree_clean_except recusaria
# os dois antes de o passo 11 poder retomar. So neste intervalo (o G0 chama esta funcao
# com o passo 9 concluido e o 11 nao: o passo 10 escreve o envelope ANTES de se marcar,
# M3-01) e com o HEAD no candidato gravado, admite:
# `?? $VD` exato (arquivo regular, nunca symlink) e, staged sem mudanca posterior na
# arvore (`A ` ou `M `), so caminhos da lista literal do passo 11 (evidence_list, $VF,
# $VD). O resto segue a regra de tree_clean_except: untracked so no plano; modificacao
# rastreada nunca.
tree_clean_resume_11() {
  local _c f lst line xy p bad
  _c=""
  if [ -f "$EV/CANDIDATE.sha" ] && [ ! -L "$EV/CANDIDATE.sha" ]; then
    _c="$(tr -d ' \t\r\n' < "$EV/CANDIDATE.sha")" || die "leitura de CANDIDATE.sha falhou"
  fi
  [ -n "$_c" ] && [ "$(git rev-parse HEAD)" = "$_c" ] \
    || die "retomada entre os passos 9 e 11 com o HEAD ($(git rev-parse --short HEAD)) fora do candidato gravado (${_c:-<sem CANDIDATE.sha>}) — me chame no Claude"
  if [ -e "$VD" ] || [ -L "$VD" ]; then
    { [ -f "$VD" ] && [ ! -L "$VD" ]; } \
      || die "retomada entre os passos 9 e 11: o envelope $VD nao e arquivo regular — me chame no Claude"
  fi
  lst="$(mktemp)" || die "mktemp falhou"
  evidence_list > "$lst" || { rm -f "$lst"; die "lista de evidencia falhou"; }
  printf '%s\n' "$VF" "$VD" >> "$lst" || { rm -f "$lst"; die "lista de evidencia falhou"; }
  f="$(mktemp)" || { rm -f "$lst"; die "mktemp falhou"; }
  if ! git status --porcelain=v1 --untracked-files=all > "$f"; then
    rm -f "$f" "$lst"; die "git status falhou — nao vou tratar como arvore limpa"
  fi
  bad=""
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    xy="${line:0:2}"
    p="${line#???}"
    case "$xy" in
      '??')
        case "$p" in
          "$PLAN_DIR/"*) : ;;
          *) [ "$p" = "$VD" ] || bad="$bad
   $p (untracked)" ;;
        esac ;;
      'A '|'M ')
        grep -qxF -- "$p" "$lst" || bad="$bad
   $p (staged FORA da lista literal do passo 11)" ;;
      *) bad="$bad
   $p (RASTREADO, modificado)" ;;
    esac
  done < "$f"
  rm -f "$f" "$lst"
  [ -z "$bad" ] || die "arvore nao esta limpa (retomada entre os passos 9 e 11: so o envelope $VD nao rastreado e, staged, a lista literal do passo 11 sao admitidos):$bad
Nada foi commitado (o HEAD e o candidato). Confira com  git status  e me chame no Claude."
  printf '   OK: retomada entre os passos 9 e 11: fora do plano, so o envelope (e o staging da lista literal do passo 11, se houver)\n'
}

# --- a SONDA das condicoes contra um commit ----------------------------------
# $1 = a revisao (o HEAD no G0; o candidato no passo 5). rc 1 = uma condicao declarada
# FALSA (ou uma parte fora do teto); rc 2 = a sonda nao mediu. RC1_PROBE_REPORT_ONLY=1
# existe SO para o harness: o corte segue, e o gerador do envelope recusa a evidencia de
# uma sonda que nao ficou verde no runner — nenhum corte chega aos fields assim.
assert_conditions_probe() {
  local _pout _prc=0
  _pout="$(mktemp)" || die "mktemp falhou"
  PYTHONDONTWRITEBYTECODE=1 python3 "$PROBE" --root "$ROOT" --base "refs/tags/$BASE_TAG" \
    --head "$1" --sizes > "$_pout" 2>&1 || _prc=$?
  sed 's/^/   sonda: /' "$_pout"
  rm -f "$_pout"
  if [ "$_prc" -eq 0 ]; then
    printf '   OK: sonda das condicoes verde contra %s\n' "$(git rev-parse --short "$1")"
    return 0
  fi
  if [ "${RC1_PROBE_REPORT_ONLY:-0}" = "1" ]; then
    printf '   AVISO: sonda rc=%s e RC1_PROBE_REPORT_ONLY=1 (so ensaio): este corte NAO chega aos fields\n' "$_prc"
    return 0
  fi
  [ "$_prc" -eq 1 ] && die "a sonda das condicoes achou afirmacao FALSA (linhas FAIL acima) contra $1.
O texto do $COND tem de dizer o que o codigo faz: corrija o codigo ou as condicoes
(derive-kit-143.py), commite, pushe, espere o CI e re-rode este script. Nunca mande ao
revisor uma condicao falsa — ela e NO-GO na regra do corte."
  die "a sonda das condicoes nao conseguiu medir (rc=$_prc; linhas INFRA acima) — re-rode este
script; persistindo, me chame no Claude."
}

# --- o .cut-state e desta tentativa ------------------------------------------
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
dela, FORA do repositorio ($ARCHIVE_ROOT/; README-rc1.md §5), e re-rode este script —
ele recomeca do passo 1."
    printf '   OK: o .cut-state (passo 5 feito) e o HEAD apontam o mesmo candidato\n'
  fi
}

# --- os passos 1, 2 e 4 conferiram ESTE candidato ------------------------------
# O marcador STEP-N nao diz sobre qual commit o passo rodou. O preflight (1) confere o
# HEAD de onde o bump (2) parte (SHA-1 == SHA-2P); o bump grava o commit em que terminou
# (SHA-2) e o CI (4) o que esperou (SHA-4): os dois tem de ser o candidato. Se o HEAD
# mudou depois deles (um push alheio durante o freeze, e um pull), o preflight, o bump
# ou o CI verde sao de OUTRO commit. Sem a linha (passo feito a mao, ou .cut-state
# anterior a esta regra): AVISO nomeado.
assert_steps_saw_cand() {
  local _s1 _s2p _s2 _s4 _bad=""
  _s1="$(state_sha SHA-1)" || die "leitura do $STATE falhou"
  _s2p="$(state_sha SHA-2P)" || die "leitura do $STATE falhou"
  _s2="$(state_sha SHA-2)" || die "leitura do $STATE falhou"
  _s4="$(state_sha SHA-4)" || die "leitura do $STATE falhou"
  if [ -z "$_s2" ]; then
    printf '   AVISO: o .cut-state nao registra o commit em que o passo 2 terminou (feito a mao?)\n'
  elif [ "$_s2" != "$1" ]; then
    _bad="$_bad
   passo 2: terminou em $_s2 (linhas STEP-2, SHA-2P e SHA-2)"
  fi
  if [ -z "$_s4" ]; then
    printf '   AVISO: o .cut-state nao registra o commit que o passo 4 conferiu (feito a mao?)\n'
  elif [ "$_s4" != "$1" ]; then
    _bad="$_bad
   passo 4: conferiu $_s4 (linhas STEP-4 e SHA-4)"
  fi
  if [ -z "$_s1" ] || [ -z "$_s2p" ]; then
    printf '   AVISO: o .cut-state nao registra o commit que o passo 1 conferiu ou de onde o bump partiu\n'
  elif [ "$_s1" != "$_s2p" ]; then
    _bad="$_bad
   passo 1: conferiu $_s1, e o bump partiu de $_s2p (linhas STEP-1 e SHA-1)"
  fi
  [ -z "$_bad" ] || die "o candidato agora e $1, e passo(s) ja marcado(s) conferiram OUTRO commit:$_bad
O HEAD mudou depois deles. Tire do $STATE as linhas nomeadas e re-rode este script: ele
refaz esses passos sobre o HEAD novo. Se main andou por um push alheio durante o
freeze, me chame no Claude antes."
  printf '   OK: os passos 1, 2 e 4 conferiram o candidato %s (ou nao registraram o commit)\n' \
    "$(printf '%s' "$1" | cut -c1-12)"
}

# --- o prazo do veredito (TTL) -----------------------------------------------
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

# --- carga da maquina antes do preflight (licao da 1.a tentativa da v1.4.1-rc.1) --
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
    printf 'suite serial de hooks: testes de desempenho com teto ABSOLUTO de p99\n'
    printf '(TestOutputScanPerfRigorous::test_p99_*) reprovam sob carga de CPU — foi o\n'
    printf 'que matou a 1.a tentativa da v1.4.1-rc.1. Feche o que pesa (outras sessoes do\n'
    printf 'Claude ou do codex, VMs, builds) e espere a carga cair.\n'
    printf 'Enter para seguir mesmo assim (ctrl-C aborta; o script e resumivel): '
    read -r _
  else
    printf '   carga baixa; mesmo assim, nada pesado em paralelo ate o fim do preflight\n'
  fi
}
gpg_probe_hint() {
  # A relmeta-142 poe `--yes` no gpg da sonda de assinatura do preflight: o `mktemp` cria
  # o arquivo e, sem o --yes, o gpg perguntava «Overwrite?» no terminal. O conselho do `y`
  # so aparece se o driver vivo NAO tiver o --yes.
  if grep -qE 'gpg --yes[^#]*--detach-sign' "$RELEASE" 2>/dev/null; then
    printf '\n>>> O preflight PROVA a chave de assinatura; o pinentry pode pedir a senha aqui.\n'
    printf '>>> (a sonda do driver chama o gpg com --yes: ela nao pergunta «Overwrite?»)\n\n'
    return 0
  fi
  printf '\n>>> O preflight PROVA a chave de assinatura. Se o gpg perguntar NESTE terminal\n'
  printf '>>>     File exists. Overwrite? (y/N)\n'
  printf '>>> responda  y  e Enter. Com N (ou so Enter) o driver diz "the key cannot sign\n'
  printf '>>> right now" — e MENTIRA, e o preflight recusa; re-rode este script (ele\n'
  printf '>>> retoma deste passo). O pinentry pode pedir a senha aqui tambem.\n\n'
}

# --- CLAUDE.md dentro do limite do validate-governance.sh COMPLETO -------------
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

# --- o Scope ASSINADO da tag cobre a faixa -----------------------------------
# RELEASE_SCOPE (release.sh) entra na anotacao ASSINADA da tag no passo 15. Ele e
# DERIVADO dos planos (PLAN-NNN) citados nos assuntos de `git log $BASE_TAG..HEAD` e dos
# ADRs tocados na faixa. Um commit que cite plano fora dele, ou que toque ADR fora dele,
# torna a linha Scope assinada falsa.
assert_release_scope_covers_log() {
  local _lg _adr _miss
  _lg="$(git log --format=%s "$BASE_TAG..HEAD")" || die "git log $BASE_TAG..HEAD falhou"
  _adr="$(git diff --name-only "$BASE_TAG" HEAD -- .claude/adr/)" || die "git diff das ADRs falhou"
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
  [ -z "$_miss" ] || die "a faixa $BASE_TAG..HEAD tem o que o RELEASE_SCOPE do release.sh nao lista: $_miss
A linha Scope da anotacao ASSINADA da tag sai do RELEASE_SCOPE, derivado dos planos
citados nos assuntos de commit da faixa e dos ADRs tocados nela. Com o commit ja em
main, o RELEASE_SCOPE precisa ser re-derivado (a relmeta-143) — me chame no Claude.
Para nao cair aqui: um plano NOVO fica fora do repositorio ate o corte."
  printf '   OK: o Scope assinado da tag cobre os planos e ADRs de %s..HEAD\n' "$BASE_TAG"
}

# ===========================================================================
say "G0 pre-condicoes"
command -v gh >/dev/null 2>&1 || die "gh CLI ausente"
[ -f "$RUNNER" ] || die "runner ausente: $RUNNER"
[ -f "$GEN" ] || die "gerador ausente: $GEN"
[ -f "$PROBE" ] || die "sonda das condicoes ausente: $PROBE"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "nao esta em main"

# A relmeta-143 tem de ter landado: e ela que poe o driver na 1.4.3.
_tb="$(awk -F'"' '/^TARGET_BASE=/{print $2; exit}' "$RELEASE")"
[ "$_tb" = "$BASE" ] || die "TARGET_BASE do release.sh e '$_tb', esperado $BASE.
A relmeta-143 ainda nao landou: assine e lande o pack .claude/plans/PLAN-194/relmeta/
(o README dele diz a ordem), pushe main, espere o CI verde e re-rode este script."

# O manifesto ADR-192 tem de estar consistente com o release.sh vivo.
_man="$(awk -v f="$RELEASE" '$2==f{print $1}' .claude/governance/gate-scripts-manifest.txt)"
[ "$_man" = "$(shasum -a 256 "$RELEASE" | awk '{print $1}')" ] \
  || die "sha do release.sh nao bate com o manifesto ADR-192 — a relmeta-143 landou pela metade"

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
# Retomada entre o passo 2 (o commit do bump trazido a main LOCAL por fast-forward) e o 3
# (o push): o HEAD e o commit que o passo 2 gravou (SHA-2), com UM pai, o commit de onde o
# bump partiu (SHA-2P), que e o origin/main; e o assunto e exatamente `release: v$BASE`.
_g0_bump_unpushed() {
  local _s2 _s2p _hp _sub
  _s2="$(state_sha SHA-2)" || return 1
  _s2p="$(state_sha SHA-2P)" || return 1
  [ -n "$_s2" ] && [ -n "$_s2p" ] && [ "$_s2" != "$_s2p" ] || return 1
  [ "$(git rev-parse HEAD)" = "$_s2" ] || return 1
  git rev-parse -q --verify 'HEAD^2' >/dev/null 2>&1 && return 1
  _hp="$(git rev-parse -q --verify 'HEAD^')" || return 1
  [ "$_hp" = "$_s2p" ] || return 1
  [ "$(git rev-parse origin/main)" = "$_s2p" ] || return 1
  _sub="$(git log -1 --format=%s HEAD)" || return 1
  [ "$_sub" = "release: v$BASE" ]
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
  elif done_step 2 && ! done_step 3 && _g0_bump_unpushed; then
    _g0_ahead=2
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
# FRESCA a existencia e um corte anterior abortado — recusa nomeada.
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
# Release fantasma de tentativa abortada: recusa. Numa retomada depois do passo 16 o
# release.yml o cria como PRE-RELEASE — o esperado. A sonda vive DENTRO do `if`: sob
# `set -e` uma atribuicao com rc!=0 mataria o script antes da classificacao NOT-FOUND.
if _grv="$(gh release view "$TAG" --json isPrerelease,isDraft 2>&1)"; then
  if done_step 16; then
    _g0_rpp="$(printf '%s' "$_grv" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
    [ "$_g0_rpp" = "True" ] \
      || die "retomada pos-tag: o Release do $TAG existe mas isPrerelease='$_g0_rpp' — me chame no Claude"
    printf '   retomada pos-tag: o pre-release do %s existe (o release.yml o cria); os passos 17-19 o conferem\n' "$TAG"
  else
    die "GitHub Release do $TAG JA EXISTE antes do push da tag (corte anterior abortado?) — triagem antes: gh release view $TAG; me chame no Claude"
  fi
else
  printf '%s' "$_grv" | grep -qi "not found\|release not found\|HTTP 404" \
    || die "gh release view falhou sem ser NOT-FOUND (transporte ou API): $_grv
O G0 nao executa passo do corte (no maximo registra o push da tag que ja aconteceu): re-rode este script. Persistindo, me chame no Claude."
fi
assert_no_gen_orphans
assert_kit_committed
assert_no_foreign_cut_residue
assert_plan_untracked_expected
assert_base_tag
assert_cut_state_matches_head
# Scope e CLAUDE.md so importam ate a tag existir (a anotacao e assinada no 15, e o
# preflight so roda no 1 e no 15). Depois, main pode andar sem derrubar a retomada.
if ! done_step 15; then
  assert_release_scope_covers_log
  assert_claude_md_fits
fi
# O job da W4 na arvore que a tag leva (o HEAD antes do 15; a tag depois): o passo 18
# exige success nele pelo nome. Ate o passo 18 concluido.
if ! done_step 18; then
  assert_rc_proof_job
fi
# Untracked e tolerado dentro do namespace do plano: os proprios
# materiais do corte (evidencia, fields, condicoes) nascem ali. Nada
# fora dele, e modificacao RASTREADA nunca e tolerada em lugar nenhum — fora a
# retomada entre os passos 9 e 11 (o envelope em .claude/governance/ e o staging da
# lista literal do passo 11; tree_clean_resume_11, a cura do GA v1.4.2 com a janela do
# M3-01: o passo 10 escreve o envelope ANTES de se marcar).
if done_step 9 && ! done_step 11; then
  tree_clean_resume_11
else
  tree_clean_except "$PLAN_DIR/"
fi
# A sonda das condicoes contra o HEAD, so antes do passo 5: depois dele o passo 5 ja a
# rodou contra o candidato gravado (e o commit do veredito so acrescenta evidencia).
if ! done_step 5; then
  assert_conditions_probe HEAD
fi
if done_step 16; then
  printf '   OK: main; retomada pos-tag (a tag %s no remoto e o objeto assinado local)\n' "$TAG"
elif done_step 15; then
  printf '   OK: main, HEAD==origin/main; tag %s assinada localmente, ainda NAO pushada\n' "$TAG"
elif [ "$_g0_ahead" -eq 1 ]; then
  printf '   OK: main; retomada entre os passos 11 e 13: o commit do veredito (%s) ainda nao foi pushado\n' \
    "$(git rev-parse --short HEAD)"
elif [ "$_g0_ahead" -eq 2 ]; then
  printf '   OK: main; retomada entre os passos 2 e 3: o commit do bump (%s) ainda nao foi pushado — o passo 3 o pusha\n' \
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
  # nao vazio, untracked incluido — e a arvore viva pode carregar a evidencia
  # untracked do re-pass que o CEO rodou antes desta cerimonia. O preflight roda
  # portanto num clone local de HEAD (o MESMO objeto), limpo por construcao — o
  # molde do passo 2. O driver confere o CI de HEAD por `gh`, que exige um remoto do
  # GitHub: o clone local aponta para a arvore viva, entao o remoto do CLONE (config
  # propria; nao e worktree) recebe a URL do remoto vivo.
  _pw="$(mktemp -d)" || die "mktemp falhou"
  git clone --quiet --local --no-hardlinks "$ROOT" "$_pw/wt" \
    || die "clone descartavel para o preflight falhou"
  [ "$(git -C "$_pw/wt" rev-parse HEAD)" = "$(git rev-parse HEAD)" ] \
    || die "o clone descartavel nao esta no HEAD vivo"
  _origin="$(git remote get-url origin)" || die "remoto origin da arvore viva"
  git -C "$_pw/wt" remote set-url origin "$_origin" \
    || die "remoto do clone descartavel"
  gpg_probe_hint
  ( cd "$_pw/wt" && bash "$RELEASE" preflight --rc "$RCN" --today "$TODAY" ) \
    || die "preflight recusou — leia o motivo acima. O clone onde ele rodou fica em
  $_pw/wt
(e ali que o pytest abaixo roda; apague-o depois).
$PREFLIGHT_RED_HINT"
  _s1_sha="$(git -C "$_pw/wt" rev-parse HEAD)" || die "rev-parse do clone do preflight falhou"
  rm -rf -- "$_pw"
  printf 'SHA-1 %s\n' "$_s1_sha" >> "$STATE" || die "gravacao do commit do passo 1 falhou"
  mark_step 1
fi

if should 2; then
  say "2/20 bump dos sitios de versao para $BASE (numa arvore descartavel)"
  printf 'O bump exige que voce tenha RELIDO npm/README.md para esta release.\n'
  printf 'Enter para confirmar que releu (ctrl-C aborta): '; read -r _
  # S349: `release.sh bump` recusa QUALQUER `git status --porcelain` nao vazio,
  # untracked incluido. O bump roda portanto num clone local do HEAD, limpo por
  # construcao. O esperado nesta release: UM commit `release: v$BASE` direto sobre o
  # HEAD (VERSION sai de 1.4.2), trazido para main por fast-forward (o MESMO objeto);
  # um no-op (a arvore ja em $BASE) tambem serve. Qualquer outra forma — arquivo nao
  # commitado, mais de um commit, outro assunto — e recusada ANTES de qualquer
  # fetch/merge/push: nada chega a main.
  _b_from="$(git rev-parse HEAD)" || die "rev-parse do HEAD falhou"
  _bw="$(mktemp -d)" || die "mktemp falhou"
  git clone --quiet --local --no-hardlinks "$ROOT" "$_bw/wt" \
    || die "clone descartavel para o bump falhou"
  [ "$(git -C "$_bw/wt" rev-parse HEAD)" = "$_b_from" ] \
    || die "o clone descartavel nao esta no HEAD vivo"
  _b_rc=0
  # shellcheck disable=SC2086
  ( cd "$_bw/wt" && bash "$RELEASE" bump --rc "$RCN" --today "$TODAY" \
      --npm-readme-reviewed $RESTAMP ) || _b_rc=$?
  [ "$_b_rc" -eq 0 ] || die "bump falhou (rc=$_b_rc) — leia o motivo acima"
  _b_head="$(git -C "$_bw/wt" rev-parse HEAD)" || die "rev-parse do clone do bump falhou"
  _b_st="$(git -C "$_bw/wt" status --porcelain=v1 --untracked-files=all)" \
    || die "git status do clone do bump falhou"
  [ -z "$_b_st" ] || die "o bump deixou arquivo NAO commitado no clone descartavel ($_bw/wt):
$_b_st
NADA foi trazido para main nem pushado. Leia o log acima e me chame no Claude."
  if [ "$_b_head" != "$_b_from" ]; then
    _b_par="$(git -C "$_bw/wt" rev-parse "$_b_head^")" || die "rev-parse do pai do bump falhou"
    _b_sub="$(git -C "$_bw/wt" log -1 --format=%s "$_b_head")" || die "assunto do bump ilegivel"
    [ "$_b_par" = "$_b_from" ] && [ "$_b_sub" = "release: v$BASE" ] \
      || die "o bump nao produziu UM commit 'release: v$BASE' direto sobre o HEAD (pai $_b_par, assunto '$_b_sub').
NADA foi trazido para main nem pushado. Me chame no Claude."
    git fetch --quiet "$_bw/wt" HEAD || die "fetch do commit do bump falhou"
    git merge --ff-only --quiet FETCH_HEAD || die "fast-forward do commit do bump falhou"
    [ "$(git rev-parse HEAD)" = "$_b_head" ] || die "main nao avancou para o commit do bump"
    printf '   bump commitado: %s (trazido por fast-forward)\n' "$(git rev-parse --short HEAD)"
  else
    printf '   bump e no-op: a arvore ja esta em %s\n' "$BASE"
  fi
  rm -rf -- "$_bw"
  printf 'SHA-2P %s\nSHA-2 %s\n' "$_b_from" "$(git rev-parse HEAD)" >> "$STATE" \
    || die "gravacao dos commits do passo 2 falhou"
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
  say "4/20 esperar o CI do candidato ($CAND) — ~15-20 min so com o Validate; ate ~2 h com o Smoke Install, que o commit do bump dispara (teto $CI_WAIT_MAX_MIN min)"
  wait_ci_green "$CAND"
  bell "CI verde no candidato"
  printf 'SHA-4 %s\n' "$CAND" >> "$STATE" || die "gravacao do commit do passo 4 falhou"
  mark_step 4
fi

if should 5; then
  say "5/20 gravar CANDIDATE.sha (o runner le o candidato daqui)"
  assert_steps_saw_cand "$CAND"
  _rm="$(git ls-remote origin refs/heads/main | awk '{print $1}')" \
    || die "ls-remote de main falhou"
  [ "$_rm" = "$CAND" ] || die "origin/main ($_rm) != HEAD ($CAND) — main andou"
  [ "$(git rev-parse HEAD)" = "$CAND" ] || die "HEAD != candidato ($CAND)"
  # A sonda das condicoes contra o CANDIDATO (o commit do bump), antes de gravar.
  assert_conditions_probe "$CAND"
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
  say "6/20 re-pass do codex — 4 partes (RC1_CODEX_JOBS=4 corre-as ao mesmo tempo; cada parte leva ~10-45 min). Deixe rodando."
  if evidence_complete_for "$CAND"; then
    # S349: o CEO rodou o re-pass ANTES desta cerimonia, sobre este MESMO
    # candidato, e deixou a evidencia completa. O runner recusa rodar por cima
    # de evidencia anterior (completa OU parcial), e re-rodar seriam 4
    # sessoes de codex identicas.
    printf '   re-pass ja concluido (rc=0) para %s — nada a rodar\n' "$CAND"
  else
    printf 'O codex roda na versao que o manifesto ADR-182 pina, SO pela rota 1 (PLAN-194 D-4):\n'
    printf 'o binario global, com o payload conferido pelo oraculo antes de executar. Nada e instalado.\n'
    assert_route1_available
    # A cota da CONTA Codex: foi o limite de uso DA CONTA (nao a capacidade do modelo)
    # que matou duas das tres partes de uma tentativa do pre-run do re-pass do GA v1.4.1
    # (2026-09-25; LEDGER do PLAN-192); o re-pass que serviu ao corte foi outro.
    printf '\nAVISO — a COTA DA CONTA Codex: o re-pass roda as 4 partes ao mesmo tempo e GASTA a\n'
    printf 'cota da conta do codex. Com ela esgotada, a parte morre sem veredito com uma\n'
    printf 'linha do codex que comeca com «ERROR:» (numa tentativa do pre-run do GA v1.4.1,\n'
    printf 'em 2026-09-25, ela dizia «hit your usage limit ... try again at 4:43 PM»): e\n'
    printf 'LIMITE DE USO DA CONTA, nao capacidade do modelo; o runner a separa e nao a\n'
    printf 're-tenta (a rota esta na recusa deste passo). O re-pass deve autenticar o codex\n'
    printf 'pela CONTA (o login em ~/.codex/auth.json), sem a chave: rode este script\n'
    printf 'com  unset OPENAI_API_KEY.\n'
    if [ -n "${OPENAI_API_KEY:-}" ]; then
      bell "OPENAI_API_KEY no ambiente antes do re-pass"
      printf '\nOPENAI_API_KEY ESTA neste ambiente. ctrl-C, rode  unset OPENAI_API_KEY  e re-rode\n'
      printf 'este script (ele retoma do passo 6). Enter segue COM ela: '
      read -r _ || die "sem terminal para o Enter do passo 6 (OPENAI_API_KEY no ambiente): rode  unset OPENAI_API_KEY  e re-rode este script (ele retoma do passo 6)"
    fi
    RC1_CODEX_JOBS="${RC1_CODEX_JOBS:-4}" bash "$RUNNER" || die "o re-pass NAO terminou GO nas 4 partes. Leia $EV/PROVENANCE-rc1.md (se existir).
Preserve a tentativa, inclusive parcial, FORA do repositorio: o G0 recusa arquivo nao
rastreado no plano fora da evidencia deste corte, e o runner recusa rodar sobre evidencia
anterior. Crie um diretorio NOVO em $ARCHIVE_ROOT/ e mova para ele os arquivos NAO
rastreados de $EV/, menos o CANDIDATE.sha (fica; copie-o). Liste-os com:
  git status --porcelain --untracked-files=all -- $EV/
O runner, a sonda, as condicoes, o README e o .gitignore sao rastreados e FICAM. O
diretorio arquivado entra no plano no closeout, depois do corte (nunca durante o freeze)
e sem o $STATE.
(a) NO-GO (a linha VERDICT: NO-GO em algum $EV/verdict-rc1-N.txt): PARE — nao ha 2.a
rodada por conta propria. Diretorio: $ARCHIVE_ROOT/repass-rc1-$(date +%Y%m%d)-NOGO-r1/
Mova para la TAMBEM o $STATE (ignorado pelo git, por isso fora da lista): sem ele a
proxima tentativa recomeca do passo 1. Leve ao Owner (me chame no Claude).
(b) Sem NO-GO e com parte SEM veredito, ou o runner morto antes do codex: morte por
CAPACIDADE do modelo (a PROVENANCE diz) ou por INFRAESTRUTURA (rede, git, gpg, a sonda
sem medida). Nao e rodada. Diretorio:
  $ARCHIVE_ROOT/repass-rc1-$(date +%Y%m%dT%H%M%S)-capacidade/  (ou -infra/)
MANTENHA o $STATE e o CANDIDATE.sha e re-rode este script: ele retoma do passo 6.
(c) Caso particular de (b), com rota propria: a parte morreu pelo LIMITE DE USO DA
CONTA Codex. O runner o declara na PROVENANCE, com a linha de erro do codex (ela traz
a hora do reset quando o codex a imprime):
  grep -n 'LIMITE DE USO' $EV/PROVENANCE-rc1.md
Nao e rodada nem capacidade do modelo. Diretorio:
  $ARCHIVE_ROOT/repass-rc1-$(date +%Y%m%dT%H%M%S)-cota/
MANTENHA o $STATE e o CANDIDATE.sha, espere a hora do reset (ou recarregue a cota da
conta) e re-rode este script, com  unset OPENAI_API_KEY : ele retoma do passo 6.
(d) Caso particular de (b): o runner recusou «rota 1 indisponivel» (o codex global deixou
de ser o pinado entre a conferencia deste passo e o runner). Diretorio -infra/ como em (b);
instale globalmente a versao que o manifesto pina e re-rode: ele retoma do passo 6.
Qualquer outro caso (veredito ambiguo, main que andou, sonda com afirmacao FALSA): me
chame no Claude."
  fi
  bell "re-pass GO nas 4 partes"
  mark_step 6
fi

if should 7; then
  say "7/20 condicoes do veredito"
  _agg_gwc=0
  for n in 1 2 3 4; do
    grep -qE '^VERDICT: GO-WITH-CONDITIONS' "$EV/verdict-rc1-$n.txt" && _agg_gwc=1
  done
  if [ "$_agg_gwc" -eq 1 ]; then
    [ -f "$COND" ] || die "algum rail deu GO-WITH-CONDITIONS e $COND nao existe.
As condicoes entram no MATERIAL ASSINADO e devem ser identicas ao snapshot
$EV/CONDITIONS-rc1.reviewed.md. Ajustar ou acrescentar condicoes exige
arquivar a tentativa (FORA do repositorio, $ARCHIVE_ROOT/) e obter os quatro
GO/GWC num NOVO re-pass."
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
  ( cd "$EV" && shasum -a 256 -c MANIFEST-rc1.sha256 --status ) \
    || die "MANIFEST-rc1 nao verifica"
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
  # das releases anteriores. O que liga os BYTES dele a assinatura GPG e so o
  # gerador (passos 10 e 11): ele verifica a assinatura contra os fields e monta
  # o envelope como funcao pura dos fields, da assinatura e do fingerprint. Nada
  # a jusante refaz essa ligacao: o step 15 do release.yml confere que
  # gpg_signature EXISTE (nao que ela assina estes bytes), o guard local do
  # passo 12 confere o delta, e a assinatura da tag (passo 15; git tag --verify
  # no release.yml) cobre a arvore commitada, nao a origem dela. Por isso o
  # envelope que este passo commita e RE-DERIVADO logo antes do staging (abaixo),
  # nunca tomado da arvore.
  # S349: UM commit so, sobre o candidato — ver o passo 8.
  [ "$(git rev-parse HEAD)" = "$CAND" ] \
    || die "HEAD != candidato revisado — algo foi commitado entre o re-pass e o veredito"
  # Retomada de um passo 11 que morreu entre o `git add` e o `git commit` (commit que
  # falhou, ctrl-C): o HEAD ainda e o candidato, entao NADA foi commitado. Um index cujos
  # caminhos staged estao TODOS na lista literal abaixo e desfeito (`git reset -q` so tira
  # do index; a arvore fica) e o staging e refeito. Outro caminho staged e recusa.
  if ! git diff --cached --quiet; then
    _st_list="$(mktemp)" || die "mktemp falhou"
    evidence_list > "$_st_list" || die "lista de evidencia falhou"
    printf '%s\n' "$VF" "$VD" >> "$_st_list"
    _st_names="$(git diff --cached --name-only --no-renames)" || die "git diff --cached falhou"
    _st_out=""
    while IFS= read -r _c; do
      [ -n "$_c" ] || continue
      grep -qxF -- "$_c" "$_st_list" || _st_out="$_st_out
   $_c"
    done <<STAGED
$_st_names
STAGED
    rm -f "$_st_list"
    [ -z "$_st_out" ] || die "o index nao esta vazio antes do staging literal, com caminho FORA da lista:$_st_out
Nada foi commitado (o HEAD e o candidato). Confira com git diff --cached --stat; se o
staging nao e deste passo, desfaca-o com git reset -q (so tira do index) e re-rode este
script (ele retoma deste passo)."
    git reset -q || die "git reset do staging anterior deste passo falhou"
    printf '   staging de uma tentativa anterior deste passo desfeito (so caminhos da lista literal; nada tinha sido commitado)\n'
  fi
  # O envelope RE-DERIVADO dos fields assinados, depois dos guards de HEAD e do index
  # e antes de o .asc sair da arvore: numa retomada entre os passos 9 e 11 o $VD da
  # arvore e um untracked que nada liga a assinatura. Se ele diferia do derivado, e
  # substituido — e e o derivado que o staging abaixo leva ao commit.
  _vd_prev=""
  if [ -f "$VD" ] && [ ! -L "$VD" ]; then
    _vd_prev="$(mktemp)" || die "mktemp falhou"
    cp -- "$VD" "$_vd_prev" || die "copiar o envelope da arvore ($VD) falhou"
  fi
  python3 "$GEN" --stage envelope --sig "$VF.asc" \
    || die "re-derivar o envelope dos fields assinados falhou (nada foi commitado; o .asc segue na arvore) — me chame no Claude"
  [ -f "$VD" ] && [ ! -L "$VD" ] || die "o envelope re-derivado nao e arquivo regular: $VD"
  if [ -n "$_vd_prev" ]; then
    if ! cmp -s -- "$_vd_prev" "$VD"; then
      printf '   AVISO: o envelope da arvore (%s) DIFERIA do derivado dos fields assinados: substituido pelo derivado, que e o que entra no commit\n' "$VD"
    fi
    rm -f "$_vd_prev"
  fi
  printf '   envelope re-derivado dos fields assinados (a assinatura re-verificada): %s\n' "$VD"
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
governance(PLAN-194): verdito pair-rail $TAG assinado + evidencia do re-pass

Decisao agregada DERIVADA dos 4 rails; as condicoes, quando existem, fazem
parte do material assinado (sub-mapa conditions: dos fields) — entre elas a
re-declaracao da divida carregada: o anexo P1 do envelope da v1.4.0 segue
aberto, sem versao prometida para a cura, exceto o CASO da condicao 67, que
esta release declara curado; e o que o envelope do GA v1.4.2 declarou aberto
(o anexo assinado da v1.4.2-rc.1 e os P2 dos vereditos que os envelopes
pinam entre eles) segue sem cura declarada, exceto um P2 da parte 3 do
re-pass do GA, que esta release declara curado.
Contexto da release (CHANGELOG [1.4.3]): o gate de configuracao do harness
curado na cerimonia padrao, a condicao 67 da v1.4.0-rc.1 aposentada, o
re-pin do Codex 0.160.0 e a prova do toolchain do npm nas tags -rc.
Antes do codex, cada afirmacao sobre codigo das condicoes foi conferida
contra o candidato pela sonda do kit (probe-rc1.txt, no MANIFEST).
tool_versions.codex_cli vem da PROVENANCE do run PINADO e e re-validado
contra a faixa do codex-cli-pin.txt pela funcao do proprio validador e contra o
manifesto ADR-182 pelo gerador — nunca de 'codex --version' desta maquina;
tool_versions.claude_code e MEDIDO por 'claude --version' ao gerar os fields.

Evidencia do re-pass no MESMO commit: quatro partes, ordenadas por raio de
dano ao adotante, sobre o delta v1.4.2..$CAND. Reviewer: codex-cli na versao
que o manifesto ADR-182 pina, so pela rota 1 (PLAN-194 D-4): o binario
global, com o payload nativo verificado contra o manifesto antes de executar
(a rota esta na PROVENANCE). Escopo coberto e o que ficou de fora:
repass-rc1/README-rc1.md. Payloads raw NAO commitados; pins em
PROVENANCE-rc1.md. O release.yml exige parent_sha == pai do commit que
introduz o veredito, e o guard local exige o veredito dentro do delta
candidato..tag: um commit so satisfaz os dois.
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
  bash "$RELEASE" preflight --rc "$RCN" --today "$TODAY" || die "preflight pre-tag recusou.
$PREFLIGHT_RED_HINT"
  bash "$RELEASE" tag --rc "$RCN" || die "a fase tag falhou"
  mark_step 15
fi

if should 16; then
  say "16/20 confirmacao do PUSH DA TAG — este e o passo irreversivel"
  printf '\nPushar a tag %s inicia release.yml (o gate, que cria o PRE-RELEASE) E o\n' "$TAG"
  printf 'npm-publish.yml, cujo job do publish PULA tags -rc.: nada vai ao npm; rodam la o\n'
  printf 'job do gate e o da prova do toolchain da rc (os controles positivos do passo 18).\n'
  printf 'O comando que sera executado:\n\n'
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
hooks no diff do commit da tag contra o pai): gh run rerun <run> --failed e espere o
verde. O await-release-gate do npm-publish.yml da tag recusa um gate que terminou sem
success, e essa recusa nao volta sozinha: depois do verde, se o run do npm-publish.yml
da tag terminou vermelho, rode tambem gh run rerun <run dele> --failed; so entao re-rode
este script (ele retoma do passo 17). PRAZO: o release.yml re-valida o veredito na hora
do run — rerun so ate $(verdict_deadline); depois disso ele fica vermelho para sempre.
Vermelho no gate do veredito ou em outro step: me chame no Claude."
    fi
    [ "$s" = "completed" ] && [ "$c" = "success" ] && break
  done
  bell "release.yml verde"
  mark_step 17
fi

if should 18; then
  say "18/20 npm-publish: o gate e a prova do toolchain da rc, pelo nome (a rc nao publica)"
  _repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || echo "")"
  printf '   Numa tag -rc. o npm-publish.yml roda o job do gate («Await release-gate») e o da prova\n'
  printf '   do toolchain («%s»); o publish e pulado. Painel dos runs:\n' "$RC_PROOF_JOB"
  [ -n "$_repo" ] && printf '     https://github.com/%s/actions/workflows/npm-publish.yml\n' "$_repo"
  TAGSHA="$(git rev-parse "$TAG^{commit}")"
  i=0
  while :; do
    i=$((i+1)); [ "$i" -le 60 ] \
      || die "os jobs do npm-publish.yml (o gate e a prova do toolchain) nao concluiram em 60 min — re-rode este script (ele retoma do passo 18)"
    sleep 60
    NID="$(gh run list --workflow npm-publish.yml --limit 10 \
      --json headSha,databaseId,headBranch,event \
      --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].databaseId" 2>/dev/null || echo "")"
    if [ -z "$NID" ] || [ "$NID" = "null" ]; then
      printf '  ... o run do npm-publish ainda nao apareceu (ou o gh falhou; tentando de novo)\n'; continue
    fi
    # Separador `|`: o estado do run, a conclusao do gate, quantos jobs tem o NOME da prova
    # do toolchain e a conclusao dela — uma conclusao VAZIA (em andamento) nao desloca os
    # campos. O nome da PROVA do toolchain e comparado EXATO (o `name:` do job da W4),
    # nunca por prefixo; o do GATE segue por PREFIXO («Await release-gate», herdado do
    # molde: o `name:` dele carrega o sufixo « (release.yml)»).
    _j18="$(gh run view "$NID" --json status,jobs \
      --jq '(.status // "") + "|" + ([.jobs[]|select(.name|startswith("Await release-gate"))][0].conclusion // "") + "|" + ([.jobs[]|select(.name == "'"$RC_PROOF_JOB"'")]|length|tostring) + "|" + ([.jobs[]|select(.name == "'"$RC_PROOF_JOB"'")][0].conclusion // "")' 2>/dev/null || echo "")"
    if [ -z "$_j18" ]; then
      printf '  ... gh run view %s falhou (tentando de novo)\n' "$NID"; continue
    fi
    _rs="$(printf '%s' "$_j18" | awk -F'|' '{print $1}')"
    AC="$(printf '%s' "$_j18" | awk -F'|' '{print $2}')"
    PN="$(printf '%s' "$_j18" | awk -F'|' '{print $3}')"
    PC="$(printf '%s' "$_j18" | awk -F'|' '{print $4}')"
    printf '  ... await-release-gate: %s; prova do toolchain: %s\n' "${AC:-pendente}" "${PC:-pendente}"
    if [ -n "$AC" ] && [ "$AC" != "null" ] && [ "$AC" != "success" ]; then
      die "await-release-gate terminou '$AC' (run $NID do npm-publish.yml).
Se o release.yml da tag foi re-rodado ate o verde (passo 17), esta recusa e a do run
anterior e nao volta sozinha: rode gh run rerun $NID --failed, espere, e re-rode este
script (ele retoma do passo 18). Senao: me chame no Claude."
    fi
    if [ "$_rs" = "completed" ] && [ "$PN" = "0" ]; then
      die "o run $NID do npm-publish.yml terminou SEM o job «${RC_PROOF_JOB}» — o passo 18 exige
success nele PELO NOME. O npm-publish.yml da tag nao tem o job da W4 (o G0 o conferiu antes
da tag: o nome mudou?). A tag ja esta publica: me chame no Claude."
    fi
    if [ -n "$PC" ] && [ "$PC" != "null" ] && [ "$PC" != "success" ]; then
      die "a prova do toolchain da rc («${RC_PROOF_JOB}») terminou '$PC' (run $NID do npm-publish.yml).
Ela nao espera o gate e nunca publica: leia o run com gh run view $NID --log-failed.
Vermelho de infraestrutura (runner, rede): gh run rerun $NID --failed, espere e re-rode
este script (ele retoma do passo 18). Vermelho no toolchain (versao do node ou do npm,
staging, packlist, npm pack --dry-run): o GA publicaria com o MESMO toolchain — me chame
no Claude ANTES do GA."
    fi
    [ "$AC" = "success" ] && [ "$PC" = "success" ] && break
  done
  printf '   controle positivo do gate do npm e prova do toolchain da rc: verdes\n'
  mark_step 18
fi

if should 19; then
  say "19/20 GitHub Release como PRE-RELEASE + rechecks finais (tag, main)"
  # Recheck do OBJETO da tag no remoto: nao pode ter sido deletada/movida.
  _ft="$(git ls-remote origin "refs/tags/$TAG" "refs/tags/$TAG^{}")" \
    || die "ls-remote final da tag falhou (transporte) — re-rode este script (ele retoma do passo 19)"
  _fp="$(printf '%s\n' "$_ft" | awk -v r="refs/tags/$TAG" '$2==r{print $1}')"
  _fpe="$(printf '%s\n' "$_ft" | awk -v r="refs/tags/$TAG^{}" '$2==r{print $1}')"
  [ "$_fp" = "$(git rev-parse "$TAG")" ] \
    || die "a tag remota NAO e mais o objeto assinado local — me chame no Claude"
  [ -z "$_fpe" ] || [ "$_fpe" = "$(git rev-parse "$TAG^{commit}")" ] \
    || die "peel remoto final da tag diverge — me chame no Claude"
  # main nao pode ter sido REVERTIDO: o commit da tag segue na cadeia first-parent
  # de origin/main. Um push de outra sessao DEPOIS do push da tag nao e rollback — e
  # aviso.
  git fetch --quiet origin main || die "fetch final falhou"
  _tc="$(git rev-parse "$TAG^{commit}")" || die "rev-parse do commit da tag falhou"
  if [ "$(git rev-parse origin/main)" != "$_tc" ]; then
    _fpl="$(git rev-list --first-parent origin/main)" || die "rev-list de origin/main falhou"
    grep -qxF -- "$_tc" <<FPL || die "o commit da tag NAO esta na cadeia first-parent de origin/main — rollback ou force-push? Me chame no Claude ANTES de anunciar"
$_fpl
FPL
    printf '   AVISO: main andou depois da tag (%s commit(s) sobre ela); a tag segue na cadeia first-parent\n' \
      "$(git rev-list --count "$_tc..origin/main")"
  fi
  _prerr="$(mktemp)" || die "mktemp falhou"
  _prj_rc=0
  _prj="$(gh release view "$TAG" --json isPrerelease,isDraft,publishedAt 2>"$_prerr")" || _prj_rc=$?
  if [ "$_prj_rc" -ne 0 ]; then
    if grep -qi 'release not found' "$_prerr"; then
      rm -f "$_prerr"
      die "o release.yml nao criou o GitHub Release do $TAG (gh: release not found) — me chame no Claude"
    fi
    _ghe="$(head -c 300 "$_prerr")" || _ghe=""
    rm -f "$_prerr"
    die "gh release view $TAG falhou (rc=$_prj_rc; transporte?): $_ghe
Re-rode este script (ele retoma do passo 19). Persistindo, me chame no Claude."
  fi
  rm -f "$_prerr"
  _pr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isPrerelease"))' 2>/dev/null || echo "")"
  _dr="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("isDraft"))' 2>/dev/null || echo "")"
  _pub="$(printf '%s' "$_prj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("publishedAt") or "")' 2>/dev/null || echo "")"
  { [ "$_pr" = "True" ] && [ "$_dr" = "False" ] && [ -n "$_pub" ]; } \
    || die "Release do $TAG draft, sem a flag pre-release ou sem publishedAt (pre='$_pr' draft='$_dr').
O hold ADR-103 conta de um release PUBLICO — me chame no Claude."
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
  printf '   pre-release confirmado NAO-draft (publishedAt %s)\n' "$_pub"
  mark_step 19
fi

if should 20; then
  say "20/20 npm view (informativo: a rc nao publica; o npm segue no GA anterior)"
  _pkg="$(python3 -c 'import json;print(json.load(open("npm/package.json"))["name"])' 2>/dev/null || echo "")"
  if [ -n "$_pkg" ]; then
    npm view "$_pkg" version 2>/dev/null || printf '   (npm view nao respondeu — confira no site)\n'
  fi
  mark_step 20
fi

# O banner de CORTADA so com os 20 passos concluidos (M3-02: um --from que PULOU um passo
# — o 18, o gate e a prova do toolchain, por exemplo — nunca imprime o banner com ele
# pendente). Sem isso: --until parou antes (rc 0, pendentes listados) ou algum passo ficou
# pendente (rc 3, nunca o banner).
_pend="$(pending_steps)"
if [ -n "$_pend" ]; then
  if [ "$UNTIL" -lt 20 ] && ! done_step 20; then
    printf '\nPARADO depois do passo %s (--until). Passos pendentes:%s\n' "$UNTIL" "$_pend"
    printf 'Re-rode este script (sem --until) para seguir de onde parou.\n'
    exit 0
  fi
  printf '\nFAIL: o corte NAO terminou — passos pendentes:%s\n' "$_pend" >&2
  printf '(um --from pulou passo nao concluido? Re-rode sem --from para retomar.)\n' >&2
  exit 3
fi
bell "$TAG cortada"
cat <<DONE

============================================================
 $TAG CORTADA (pre-release publico; o npm segue no GA anterior).
 - Hold ADR-103: >= 24 h a partir do publishedAt do pre-release.
   O hold e MECANICO no release.yml — o passo "Assert 24h" so
   existe no GA, e ele le esse publishedAt.
 - Ate o GA, main fica congelado.
 - Os adopters podem subir JA para esta tag:
   upgrade.sh --pin $TAG, com a cerimonia gravada ou passada
   (Claude Code 2.1.280 ou mais novo).
 - Depois do hold: o GA repete este fluxo com --stable, e o
   re-pass roda de novo sobre a arvore da rc.1.
 - Me chame no Claude para o fechamento da sessao (o que houver em
   $ARCHIVE_ROOT/ — tentativas arquivadas — entra no plano).
 - No closeout, commite tambem $EV/.tag-push-epoch
   (o piso do passo 19; o git nao o ignora, e o release.sh recusa
   arvore com arquivo nao rastreado) — como o da v1.4.2-rc.1.
============================================================
DONE
