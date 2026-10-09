#!/bin/bash
# CEREMONY-LINT: handwritten-exception: harness do ESTAGIO K1 de
# .claude/plans/PLAN-194/derive-ga-kit-143.py (o derivador do kit do GA v1.4.3). O harness
# COMPLETO do GA v1.4.3 sai do derivador no estagio final — depois do corte da
# v1.4.3-rc.1, quando os fatos e o conteudo da 1.4.3 existem — e substitui este arquivo.
#
# test-ga-kit.sh — prova, sem gastar codex e sem tocar na arvore viva, as CURAS que o
# derivador aplica ao kit do GA v1.4.2 (o molde), cada uma pelo comportamento do bloco
# VERBATIM do arquivo curado, com um stub no lugar do mundo, e cada uma com o GEMEO
# VERMELHO: o mesmo bloco do molde, sobre o mesmo estado, mostra a classe (o controle nao
# e vacuo).
#
#   bash .claude/plans/PLAN-194/test-ga-kit.sh
#
#   GAKIT_SCRATCH_PARENT  pai do scratch (padrao /tmp); o scratch sai na saida, salvo falha.
#
# O que ele faz, em ordem:
#   A.  o derivador: compilacao em memoria; --check-cures (todas as ancoras, e o
#       deslocamento de versao a seco preservando os literais de historia das curas);
#       --emit-cured num scratch; /bin/bash -n e shellcheck -S warning nos shells curados;
#       o check-ceremony-script sobre os shells curados (zero BLOCKING); compilacao do
#       gerador curado.
#   K.  o kit INTEIRO e recusa nomeada no K1 (fatos e conteudo da rc.1 pendentes), e o
#       --emit-cured recusa um destino dentro do repositorio.
#   C1  R3-CLAIMS-01: o prompt do passo 2 nao pede mais que o Owner «releia» o npm/README.md
#       num bump no-op (o molde pede).
#   C2  M3-02: o bloco do banner de PUBLICADO, com o passo 18 pendente (um --from 19): o
#       curado recusa (rc 3, o 18 nomeado); o molde imprime o banner. E os caminhos bons.
#   C3  REGISTRY: o laco do registry do passo 18 com um registry que so mostra a versao na
#       8.a tentativa: o curado espera (padrao 20); o molde desiste na 5.a. E o teto
#       configuravel e o valor invalido recusado pelo nome.
#   C4  M3-01 (corte): o seletor da arvore limpa do G0 com o passo 9 feito, o 10 NAO marcado
#       e o envelope escrito: o curado abre a janela; o molde recusa a arvore. Antes do 9,
#       o curado tambem recusa (a janela nao abre cedo demais).
#   C5  D-4: a secao 2 do runner curado com um codex global PLANTADO: recusa nomeada, e
#       nada executa (nem o lancador nem o npx espiao); o runner do molde executa o npx.
#   C6  M3-01 (ferramentas): as classes de morte com as mensagens MEDIDAS no codex 0.160.0
#       (spend cap; high load): o curado classifica; o molde nao.
#   C7  R3S-02/R3S-01: os textos de historia e o review record, curados.
#   C8  R3H-04: no harness do GA curado, B4c/B4d/R2v/R4c/R4d anotam o id em _red e o indice
#       D os exige; um censo confere que todo id anotado em _red esta num _d_need.
#   D.  o INDICE dos controles vermelhos deste harness.
#
# O que este harness NAO prova: o kit do GA v1.4.3 inteiro (ele so existe depois do corte
# da rc.1); o corte do GA real num clone (o R/T do harness completo); que as curas ficam de
# pe depois do deslocamento de versao e do conteudo da 1.4.3 (o estagio final re-ensaia).
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT" || exit 2

PLAN_DIR=".claude/plans/PLAN-194"
MOLD_DIR=".claude/plans/PLAN-193"
DER="$PLAN_DIR/derive-ga-kit-143.py"
M_CUT="$ROOT/$MOLD_DIR/OWNER-GA-CUT.sh"
M_RUN="$ROOT/$MOLD_DIR/repass-ga/run-ga-repass.sh"
M_GEN="$ROOT/$MOLD_DIR/gen-envelope-ga.py"
M_TEST="$ROOT/$MOLD_DIR/test-ga-kit.sh"

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  PASS  %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$*"; }
say()  { printf '\n===== %s\n' "$*"; }
# Controle por AUSENCIA de texto (R3H-01): o arquivo TEM de existir, regular e nao vazio.
lacks() {  # $1 = arquivo; o resto = os argumentos do grep (flags e padrao)
  local _lf="$1"; shift
  [ -f "$_lf" ] && [ ! -L "$_lf" ] && [ -s "$_lf" ] || return 2
  if grep -q "$@" "$_lf"; then return 1; fi
  return 0
}
# Recusa NOMEADA (R3H-02): rc != 0 E o texto da recusa; o id vai para o indice _red.
_red=""
refused() {  # $1 = id, $2 = rc, $3 = log, $4 = texto FIXO esperado, $5 = o caso
  if [ "$2" -ne 0 ] && [ -f "$3" ] && grep -qF -- "$4" "$3"; then
    ok "$1 (controle vermelho): $5 — recusa nomeada (rc $2; «$4»)"; _red="$_red $1"
  elif [ "$2" -eq 0 ]; then bad "$1: $5 PASSOU (rc 0)"; sed -n '1,8p' "$3" 2>/dev/null
  else bad "$1: $5 recusado (rc $2) SEM o texto «$4»"; sed -n '1,10p' "$3" 2>/dev/null; fi
}
# Gemeo vermelho: o MOLDE, sobre o mesmo estado, mostra a classe. $1 = id, $2 = o que viu.
twin() { ok "$1 (gemeo vermelho, o molde): $2"; _red="$_red $1"; }

SCRATCH_PARENT="${GAKIT_SCRATCH_PARENT:-/tmp}"
[ -d "$SCRATCH_PARENT" ] || { echo "GAKIT_SCRATCH_PARENT nao e diretorio: $SCRATCH_PARENT" >&2; exit 2; }
SCRATCH="$(mktemp -d "$SCRATCH_PARENT/gakitk1.XXXXXX")" || { echo "mktemp falhou" >&2; exit 2; }
SCRATCH="$(cd "$SCRATCH" && pwd -P)" || { echo "scratch ilegivel" >&2; exit 2; }
PYTHONDONTWRITEBYTECODE=1; export PYTHONDONTWRITEBYTECODE
cleanup() {
  if [ "$FAIL" -ne 0 ]; then
    printf 'Harness incompleto/falho: fixtures e logs preservados em %s\n' "$SCRATCH" >&2
    return
  fi
  chmod -R u+w "$SCRATCH" 2>/dev/null
  rm -rf -- "$SCRATCH" 2>/dev/null
}
trap cleanup EXIT
case "${1:-}" in
  "") : ;;
  *) echo "uso: $0" >&2; exit 2 ;;
esac
CUR="$SCRATCH/cured"; mkdir -p "$CUR"
C_CUT="$CUR/OWNER-GA-CUT.sh.cured-1.4.2"
C_RUN="$CUR/run-ga-repass.sh.cured-1.4.2"
C_GEN="$CUR/gen-envelope-ga.py.cured-1.4.2"
C_TEST="$CUR/test-ga-kit.sh.cured-1.4.2"

# ===========================================================================
say "A. o derivador, as curas e o lint dos curados"
if python3 - "$DER" > /dev/null 2>&1 <<'PYC'
import sys
with open(sys.argv[1], "rb") as fh:
    compile(fh.read(), sys.argv[1], "exec")
PYC
then ok "A0: compile $(basename "$DER") (em memoria, sem .pyc)"; else bad "A0: compile $(basename "$DER")"; fi
if python3 "$DER" --check-cures > "$SCRATCH/check.log" 2>&1 \
   && grep -q -- '--check-cures OK (todas as ancoras aplicadas)' "$SCRATCH/check.log" \
   && [ "$(grep -c '^protect ' "$SCRATCH/check.log")" = "4" ]; then
  ok "A1: --check-cures OK: as curas sobre o kit do GA v1.4.2, por ancora, e o deslocamento a seco preserva os literais de historia"
else bad "A1: --check-cures falhou"; sed -n '1,12p' "$SCRATCH/check.log"; fi
if python3 "$DER" --emit-cured "$CUR" > "$SCRATCH/emit.log" 2>&1 \
   && [ -s "$C_CUT" ] && [ -s "$C_RUN" ] && [ -s "$C_GEN" ] && [ -s "$C_TEST" ]; then
  ok "A2: --emit-cured escreveu os quatro curados no scratch"
else bad "A2: --emit-cured falhou"; sed -n '1,8p' "$SCRATCH/emit.log"; fi
for f in "$C_CUT" "$C_RUN" "$C_TEST"; do
  if /bin/bash -n "$f" 2>/dev/null; then ok "A3: /bin/bash -n $(basename "$f")"; else bad "A3: /bin/bash -n $(basename "$f")"; fi
  if command -v shellcheck >/dev/null 2>&1; then
    if shellcheck -S warning -s bash "$f" >/dev/null 2>&1; then ok "A3: shellcheck $(basename "$f")"
    else bad "A3: shellcheck $(basename "$f")"; shellcheck -S warning -s bash "$f" 2>&1 | sed -n '1,10p'; fi
  else bad "A3: shellcheck ausente — o lint dos shells curados nao rodou"; fi
done
if python3 - "$C_GEN" > /dev/null 2>&1 <<'PYC'
import sys
with open(sys.argv[1], "rb") as fh:
    compile(fh.read(), sys.argv[1], "exec")
PYC
then ok "A4: compile do gerador curado"; else bad "A4: compile do gerador curado"; fi
# O ceremony-lint do repositorio, sobre uma raiz de ensaio com os shells curados no lugar do
# plano (o lint descobre os scripts em .claude/plans/).
_lr="$SCRATCH/lintroot"; mkdir -p "$_lr/.claude/plans/PLAN-K1GA"
cp -- "$C_CUT" "$_lr/.claude/plans/PLAN-K1GA/OWNER-GA-CUT.sh" && cp -- "$C_RUN" "$_lr/.claude/plans/PLAN-K1GA/run-ga-repass.sh" \
  && cp -- "$C_TEST" "$_lr/.claude/plans/PLAN-K1GA/test-ga-kit.sh"
# O rc do lint e o do PISO do conjunto rastreado (nao ha arquivo rastreado na raiz de ensaio):
# o que importa e o JSON; o rc fica fora (--floor 0), e o parse decide.
python3 .claude/scripts/check-ceremony-script.py --root "$_lr" --floor 0 --json > "$SCRATCH/lint.json" 2>/dev/null || :
_nb="$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
mine = [f for f in d["files"] if f["file"].startswith(".claude/plans/PLAN-K1GA/")]
if len(mine) < 3:
    print("VACUO"); sys.exit(0)
print(sum(1 for f in mine for x in f["findings"] if x["sev"] == "BLOCKING"))
' "$SCRATCH/lint.json")" || _nb="ERRO"
if [ "$_nb" = "0" ]; then ok "A5: ceremony-lint: 0 BLOCKING nos tres shells curados"
else bad "A5: ceremony-lint: $_nb"; fi

# ===========================================================================
say "K. o kit inteiro e recusa nomeada no K1; o curado nunca vai para dentro do repositorio"
_k_rc=0; python3 "$DER" > "$SCRATCH/k1.log" 2>&1 || _k_rc=$?
refused K1a "$_k_rc" "$SCRATCH/k1.log" "o kit do GA v1.4.3 so deriva INTEIRO depois do corte da v1.4.3-rc.1" \
  "o kit do GA inteiro no K1 (fatos e conteudo pendentes)"
if grep -qF 'RC_PUBLISHED_AT' "$SCRATCH/k1.log" && grep -qF 'as condicoes do GA' "$SCRATCH/k1.log"; then
  ok "K1a: a recusa nomeia os fatos e o conteudo pendentes"
else bad "K1a: a recusa nao nomeia os pendentes"; fi
mkdir -p "$ROOT/$PLAN_DIR/.k1-emit-test"
_k2_rc=0; python3 "$DER" --emit-cured "$ROOT/$PLAN_DIR/.k1-emit-test" > "$SCRATCH/k2.log" 2>&1 || _k2_rc=$?
if [ -d "$ROOT/$PLAN_DIR/.k1-emit-test" ] && [ -z "$(ls -A "$ROOT/$PLAN_DIR/.k1-emit-test")" ]; then
  refused K1b "$_k2_rc" "$SCRATCH/k2.log" "recusa um diretorio DENTRO do repositorio" \
    "o --emit-cured para dentro do repositorio (nada escrito)"
else bad "K1b: o --emit-cured escreveu dentro do repositorio"; fi
rmdir -- "$ROOT/$PLAN_DIR/.k1-emit-test" 2>/dev/null || bad "K1b: limpeza do diretorio de teste falhou"

# ===========================================================================
say "C1. R3-CLAIMS-01: o passo 2 do GA (bump no-op) nao pede releitura do npm/README.md"
_c1() {  # $1 = corte; imprime o que o passo 2 diz ao Owner antes do Enter
  awk '/^if should 2; then$/{f=1} f && /^  read -r _/{exit} f && /^  printf /' "$1" > "$SCRATCH/c1.sh" || return 1
  bash "$SCRATCH/c1.sh"
}
_c1 "$C_CUT" > "$SCRATCH/c1-cured.log" 2>&1
_c1 "$M_CUT" > "$SCRATCH/c1-mold.log" 2>&1
if grep -qF 'O bump do GA e NO-OP: o npm/README.md e o mesmo da rc.1' "$SCRATCH/c1-cured.log" \
   && grep -qF 'Enter para seguir com o bump no-op' "$SCRATCH/c1-cured.log" \
   && lacks "$SCRATCH/c1-cured.log" -F 'RELIDO npm/README.md'; then
  ok "C1: o curado diz que o bump e no-op e que o npm/README.md e o da rc.1, sem pedir releitura"; _red="$_red C1"
else bad "C1: o prompt curado do passo 2"; cat "$SCRATCH/c1-cured.log"; fi
if grep -qF 'O bump exige que voce tenha RELIDO npm/README.md para esta release.' "$SCRATCH/c1-mold.log"; then
  twin C1m "o passo 2 do molde pede que o Owner releia o npm/README.md num bump no-op"
else bad "C1m: o molde nao mostrou a classe (o controle seria vacuo)"; fi
if grep -qF "Enter para seguir com o bump no-op" "$C_TEST" && lacks "$C_TEST" -F "Enter para confirmar que releu"; then
  ok "C1: o T2 do harness do GA curado confere o texto novo do passo 2"
else bad "C1: o T2 do harness do GA curado ainda confere o texto velho"; fi

# ===========================================================================
say "C2. M3-02: o banner de PUBLICADO so com os 20 passos concluidos"
_c2() {  # $1 = corte, $2 = estado (passos feitos, separados por espaco), $3 = UNTIL, $4 = log
  local _s
  : > "$SCRATCH/c2.state"
  for _s in $2; do printf 'STEP-%s\n' "$_s" >> "$SCRATCH/c2.state"; done
  { printf '#!/bin/bash\nset -uo pipefail\nSTATE="%s"; UNTIL=%s; TAG=vX\n' "$SCRATCH/c2.state" "$3"
    printf 'bell() { :; }\n'
    awk '/^done_step\(\) \{/' "$1"
    awk '/^pending_steps\(\) \{$/{f=1} f{print} f && /^\}$/{exit}' "$1"
    awk '/^# O banner de PUBLICADO so com/{f=1} /^bell "\$TAG cortada"$/{exit} f' "$1"
    printf 'printf "BANNER-PUBLICADO\\n"\n'; } > "$SCRATCH/c2.sh"
  bash "$SCRATCH/c2.sh" > "$4" 2>&1
}
_all="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20"
_no18="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 19 20"
_c2_rc=0; _c2 "$C_CUT" "$_no18" 20 "$SCRATCH/c2-no18.log" || _c2_rc=$?
if lacks "$SCRATCH/c2-no18.log" -F 'BANNER-PUBLICADO'; then
  refused M302 "$_c2_rc" "$SCRATCH/c2-no18.log" "o corte NAO terminou — passos pendentes: 18" \
    "o passo 18 pendente com o 20 concluido (um --from 19), sem o banner"
else bad "M302: o curado imprimiu o banner com o passo 18 pendente"; fi
_c2 "$M_CUT" "$_no18" 20 "$SCRATCH/c2-mold.log" || :
if grep -qF 'BANNER-PUBLICADO' "$SCRATCH/c2-mold.log"; then
  twin M302m "com o passo 18 pendente e o 20 concluido, o molde imprime o banner de PUBLICADO"
else bad "M302m: o molde nao mostrou a classe"; sed -n '1,6p' "$SCRATCH/c2-mold.log"; fi
if _c2 "$C_CUT" "$_all" 20 "$SCRATCH/c2-all.log" && grep -qF 'BANNER-PUBLICADO' "$SCRATCH/c2-all.log"; then
  ok "C2: com os 20 passos concluidos o curado imprime o banner"
else bad "C2: o caminho bom do banner falhou"; fi
if _c2 "$C_CUT" "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19" 19 "$SCRATCH/c2-until.log" \
   && grep -qF 'PARADO depois do passo 19 (--until). Passos pendentes: 20' "$SCRATCH/c2-until.log" \
   && lacks "$SCRATCH/c2-until.log" -F 'BANNER-PUBLICADO'; then
  ok "C2: --until 19 para (rc 0), lista o 20 pendente e nao imprime o banner"
else bad "C2: o --until 19 do curado"; fi

# ===========================================================================
say "C3. REGISTRY: a espera do registry no passo 18 (o CDN do npm)"
_c3() {  # $1 = corte, $2 = a chamada do npm view em que o registry passa a mostrar a versao, $3 = log, $4.. = env
  local _c="$1" _at="$2" _log="$3"; shift 3
  { printf '#!/bin/bash\nset -uo pipefail\n'
    printf 'die() { printf "FATAL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'NPM_PKG=pkg; BASE=9.9.9; TAG=v9.9.9; TERMINAL_MODE=0\n'
    printf 'sleep() { printf "x\\n" >> "%s/c3.sleeps"; }\n' "$SCRATCH"
    printf 'gh_release_edit_idem() { printf "DRAFT-MANTIDO\\n"; return 0; }\n'
    printf 'npm_view_version() { local n; n="$(cat "%s/c3.calls" 2>/dev/null || echo 0)"; n=$((n+1)); printf "%%s" "$n" > "%s/c3.calls"; if [ "$n" -ge %s ]; then printf "9.9.9\\n"; else printf "9.9.8\\n"; fi; }\n' "$SCRATCH" "$SCRATCH" "$_at"
    awk '/^NPM_VIEW_TRIES="/{f=1} f{print} f && /^esac$/{n++; if (n == 2) exit}' "$_c"
    awk '/^  NPMV=""; NPML=""; _nv=0$/{f=1} f{print} f && /^  fi$/{exit}' "$_c"
    printf 'printf "REGISTRY-OK %%s\\n" "$_nv"\n'; } > "$SCRATCH/c3.sh"
  rm -f "$SCRATCH/c3.calls" "$SCRATCH/c3.sleeps"
  env "$@" bash "$SCRATCH/c3.sh" > "$_log" 2>&1
}
# o registry so mostra a versao na 15.a chamada (8.a tentativa: cada uma le a versao e o latest)
if _c3 "$C_CUT" 15 "$SCRATCH/c3-cured.log" GA_NPM_VIEW_WAIT_SECONDS=0 \
   && grep -qF 'REGISTRY-OK 8' "$SCRATCH/c3-cured.log" && grep -qF 'tentativa 7/20' "$SCRATCH/c3-cured.log"; then
  ok "C3: o curado espera ate a 8.a tentativa (padrao 20) e segue com o registry confirmado"; _red="$_red REG"
else bad "C3: o curado nao esperou o registry"; sed -n '1,12p' "$SCRATCH/c3-cured.log"; fi
_c3m_rc=0; _c3 "$M_CUT" 15 "$SCRATCH/c3-mold.log" || _c3m_rc=$?
if [ "$_c3m_rc" -ne 0 ] && grep -qF 'apos 5 tentativas' "$SCRATCH/c3-mold.log"; then
  twin REGm "o molde desiste do registry na 5.a tentativa (5 x 30 s) com o publish ja feito"
else bad "REGm: o molde nao mostrou a classe"; sed -n '1,6p' "$SCRATCH/c3-mold.log"; fi
_c3n_rc=0; _c3 "$C_CUT" 999 "$SCRATCH/c3-never.log" GA_NPM_VIEW_TRIES=3 GA_NPM_VIEW_WAIT_SECONDS=0 || _c3n_rc=$?
if [ "$(grep -c . "$SCRATCH/c3.sleeps" 2>/dev/null)" = "3" ] && grep -qF 'DRAFT-MANTIDO' "$SCRATCH/c3-never.log"; then
  refused REG3 "$_c3n_rc" "$SCRATCH/c3-never.log" "como latest apos 3 tentativas de 0s" \
    "o registry que nunca confirma, com o teto configurado em 3 (o Release fica em DRAFT)"
else bad "REG3: o teto configurado nao foi respeitado ou o draft nao foi mantido"; fi
_c3b_rc=0; _c3 "$C_CUT" 1 "$SCRATCH/c3-bad.log" GA_NPM_VIEW_TRIES=abc || _c3b_rc=$?
refused REGbad "$_c3b_rc" "$SCRATCH/c3-bad.log" "FAIL: GA_NPM_VIEW_TRIES invalido: abc" "um teto do registry nao numerico"

# ===========================================================================
say "C4. M3-01 (corte): a janela de retomada do G0 comeca no passo 9"
# Fixture: um repositorio com o candidato gravado, o envelope ESCRITO pelo passo 10 (NAO
# rastreado em .claude/governance/) e o passo 10 sem o marcador (morto entre os dois).
_c4="$SCRATCH/c4"
_c4_ok=1
git init --quiet "$_c4" && git -C "$_c4" config --local user.name k1 && git -C "$_c4" config --local user.email k1@invalid \
  && git -C "$_c4" config --local commit.gpgsign false && printf 'x\n' > "$_c4/README" \
  && git -C "$_c4" add README && git -C "$_c4" commit -q -m base || _c4_ok=0
_c4ev="$PLAN_DIR/repass-ga"
mkdir -p "$_c4/$_c4ev" "$_c4/.claude/governance" || _c4_ok=0
git -C "$_c4" rev-parse HEAD > "$_c4/$_c4ev/CANDIDATE.sha" || _c4_ok=0
: > "$_c4/$_c4ev/MANIFEST-ga.sha256"
printf 'envelope do passo 10\n' > "$_c4/.claude/governance/pair-rail-verdict-vX.md"
_c4sel() {  # $1 = corte, $2 = passos feitos, $3 = log
  local _s
  : > "$_c4/$_c4ev/.cut-state"
  for _s in $2; do printf 'STEP-%s\n' "$_s" >> "$_c4/$_c4ev/.cut-state"; done
  { printf '#!/bin/bash\nset -uo pipefail\n'
    printf 'die() { printf "\\nFAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'PLAN_DIR=%s; EV=%s; STATE="$EV/.cut-state"; COND="$EV/CONDITIONS-ga.md"\n' "$PLAN_DIR" "$_c4ev"
    printf 'VF="$PLAN_DIR/verdict-fields-vX.md"; VD=".claude/governance/pair-rail-verdict-vX.md"\n'
    awk '/^done_step\(\) \{/' "$1"
    for _fn in tree_clean_except evidence_list tree_clean_resume_11; do
      awk -v fn="$_fn" '$0 == fn "() {" {f=1} f{print} f && /^\}$/{exit}' "$1"
    done
    awk '/^if done_step (9|10) && ! done_step 11; then$/{f=1} f{print} f && /^fi$/{exit}' "$1"
    printf 'printf "G0-ARVORE-OK\\n"\n'; } > "$SCRATCH/c4.sh"
  ( cd "$_c4" && bash "$SCRATCH/c4.sh" ) > "$3" 2>&1
}
if [ "$_c4_ok" -eq 1 ]; then
  if _c4sel "$C_CUT" "1 2 3 4 5 6 7 8 9" "$SCRATCH/c4-cured.log" \
     && grep -qF 'G0-ARVORE-OK' "$SCRATCH/c4-cured.log" \
     && grep -qF 'OK: retomada entre os passos 10 e 11: fora do plano, so o envelope' "$SCRATCH/c4-cured.log"; then
    ok "W11: passo 9 feito, o 10 sem marcador e o envelope escrito: o curado abre a janela e o G0 segue"; _red="$_red W11"
  else bad "W11: o curado nao abriu a janela de retomada"; sed -n '1,10p' "$SCRATCH/c4-cured.log"; fi
  _c4m_rc=0; _c4sel "$M_CUT" "1 2 3 4 5 6 7 8 9" "$SCRATCH/c4-mold.log" || _c4m_rc=$?
  if [ "$_c4m_rc" -ne 0 ] && grep -qF '.claude/governance/pair-rail-verdict-vX.md (untracked)' "$SCRATCH/c4-mold.log" \
     && lacks "$SCRATCH/c4-mold.log" -F 'G0-ARVORE-OK'; then
    twin W11m "no mesmo estado o molde recusa a arvore (o envelope untracked) — a retomada fica sem rota"
  else bad "W11m: o molde nao mostrou a classe"; sed -n '1,8p' "$SCRATCH/c4-mold.log"; fi
  _c4e_rc=0; _c4sel "$C_CUT" "1 2 3 4 5 6 7 8" "$SCRATCH/c4-early.log" || _c4e_rc=$?
  refused W11b "$_c4e_rc" "$SCRATCH/c4-early.log" ".claude/governance/pair-rail-verdict-vX.md (untracked)" \
    "o envelope fora do plano ANTES do passo 9 (a janela nao abre cedo)"
else bad "C4: fixture do repositorio falhou"; fi

# ===========================================================================
say "C5. D-4: a rota 1 SO no runner do GA (lancador plantado, npx espiao)"
_c5="$SCRATCH/c5"; mkdir -p "$_c5/bin" "$_c5/sys" "$_c5/out" "$_c5/out-m"
printf '#!/bin/bash\nprintf "EXEC planted %%s\\n" "$*" >> "%s/planted.log"\necho "codex-cli 0.160.0"\n' "$_c5" > "$_c5/bin/codex"
printf '#!/bin/bash\nprintf "EXEC npx %%s\\n" "$*" >> "%s/npx.log"\necho "codex-cli 0.160.0"\n' "$_c5" > "$_c5/bin/npx"
chmod 0755 "$_c5/bin/codex" "$_c5/bin/npx"
_c5py="$(command -v python3)" || _c5py=""
_c5git="$(command -v git)" || _c5git=""
[ -n "$_c5py" ] && ln -sf "$_c5py" "$_c5/sys/python3"
[ -n "$_c5git" ] && ln -sf "$_c5git" "$_c5/sys/git"
_c5path="$_c5/bin:$_c5/sys:/usr/bin:/bin:/usr/sbin:/sbin"
_c5sect() {  # $1 = runner, $2 = destino
  { printf '#!/bin/bash\nset -uo pipefail\n'
    printf 'die() { printf "FATAL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'REPO_ROOT="$C5_REPO"; OUT="$C5_OUT"\n'
    printf 'PIN_MANIFEST="$REPO_ROOT/.claude/governance/codex-cli-pin-manifest.json"\n'
    printf 'CODEX_VER="$(python3 -c '"'"'import json,sys; print(json.load(open(sys.argv[1]))["package_version"])'"'"' "$PIN_MANIFEST")"\n'
    printf 'CODEX_PKG="@openai/codex@$CODEX_VER"\n'
    awk '/^# --- 2\. resolver e VERIFICAR o codex pinado/{f=1} /^# --- 3\. worktree DETACHED/{f=0} f' "$1"
    printf 'printf "C5-ROTA %%s\\n" "$CODEX_ROUTE"\n'; } > "$2"
}
if [ -n "$_c5py" ] && git clone --quiet --local --shared "$ROOT" "$_c5/repo" 2>/dev/null; then
  _c5sect "$C_RUN" "$_c5/sect.sh"; _c5sect "$M_RUN" "$_c5/sect-m.sh"
  rm -f "$_c5/planted.log" "$_c5/npx.log"; _c5_rc=0
  ( cd "$_c5/repo" && env -u CODEX_BIN -u CLAUDE_PROJECT_DIR PATH="$_c5path" C5_REPO="$_c5/repo" \
      C5_OUT="$_c5/out" bash "$_c5/sect.sh" ) > "$_c5/cured.log" 2>&1 || _c5_rc=$?
  if [ ! -e "$_c5/planted.log" ] && [ ! -e "$_c5/npx.log" ]; then
    refused RT "$_c5_rc" "$_c5/cured.log" "e RECUSA NOMEADA nesta release (PLAN-194 D-4): nada foi baixado nem executado" \
      "o codex global plantado no runner do GA curado (nada executa)"
  else bad "RT: o lancador plantado ou o npx EXECUTOU no runner curado"; fi
  rm -f "$_c5/planted.log" "$_c5/npx.log"
  ( cd "$_c5/repo" && env -u CODEX_BIN -u CLAUDE_PROJECT_DIR PATH="$_c5path" C5_REPO="$_c5/repo" \
      C5_OUT="$_c5/out-m" bash "$_c5/sect-m.sh" ) > "$_c5/mold.log" 2>&1 || :
  if [ -s "$_c5/npx.log" ]; then twin RTm "o runner do GA do molde EXECUTA o npx plantado antes de verificar ($(head -n 1 "$_c5/npx.log"))"
  else bad "RTm: o npx nao executou no runner do molde — o RT seria vacuo"; sed -n '1,6p' "$_c5/mold.log"; fi
else bad "C5: clone do repositorio (oraculo e manifesto) falhou"; fi

# ===========================================================================
say "C6. M3-01 (ferramentas): as classes de morte com as mensagens medidas no codex 0.160.0"
_c6() {  # $1 = runner, $2 = funcao, $3 = transcript; imprime a saida e devolve o rc dela
  { printf '#!/bin/bash\nset -uo pipefail\n'
    grep -E "^CODEX_(ACCOUNT_LIMIT|CAPACITY)_RE='" "$1"
    for _fn in codex_error_tail codex_account_limit codex_capacity_death; do
      awk -v fn="$_fn" '$0 == fn "() {" {f=1} f{print} f && /^\}$/{exit}' "$1"
    done
    printf '%s "$1"\n' "$2"; } > "$SCRATCH/c6.sh"
  bash "$SCRATCH/c6.sh" "$3"
}
printf 'OpenAI Codex\nERROR: You hit your spend cap set in your workspace. Increase your spend cap to continue.\n' > "$SCRATCH/c6-spend.log"
printf 'OpenAI Codex\nERROR: Codex is currently experiencing high load.\n' > "$SCRATCH/c6-load.log"
if _c6 "$C_RUN" codex_account_limit "$SCRATCH/c6-spend.log" > "$SCRATCH/c6a.out" 2>&1 \
   && grep -qF 'ERROR: You hit your spend cap' "$SCRATCH/c6a.out"; then
  ok "AL: o curado classifica o spend cap (0.160.0) como LIMITE DE USO da CONTA (sem re-tentativa)"; _red="$_red AL"
else bad "AL: o curado nao classificou o spend cap"; fi
if _c6 "$M_RUN" codex_account_limit "$SCRATCH/c6-spend.log" > /dev/null 2>&1; then
  bad "ALm: o molde classificou o spend cap (o controle seria vacuo)"
else twin ALm "o molde nao ve o spend cap como limite da conta (a morte ficaria sem classe)"; fi
if _c6 "$C_RUN" codex_capacity_death "$SCRATCH/c6-load.log" > /dev/null 2>&1; then
  ok "CAP: o curado classifica a alta carga (0.160.0) como capacidade (re-tentada)"; _red="$_red CAP"
else bad "CAP: o curado nao classificou a alta carga"; fi
if _c6 "$M_RUN" codex_capacity_death "$SCRATCH/c6-load.log" > /dev/null 2>&1; then
  bad "CAPm: o molde classificou a alta carga (o controle seria vacuo)"
else twin CAPm "o molde nao ve a alta carga como capacidade"; fi

# ===========================================================================
say "C7. R3S-02, M3-01 (ferramentas) e R3S-01: os textos curados"
if lacks "$C_RUN" -F 'mensagens do codex 0.156.1' \
   && lacks "$C_RUN" -F 'terminou no limite de uso da conta com a PROVENANCE' \
   && grep -qF 'medidos por `strings`' "$C_RUN" && grep -qF 'matou duas das tres partes' "$C_RUN"; then
  ok "C7: o comentario do runner cita as mensagens MEDIDAS na 0.160.0 e a historia como o corte a registra"; _red="$_red TXT"
else bad "C7: o comentario do runner curado"; fi
if grep -qF 'mensagens do codex 0.156.1' "$M_RUN" && grep -qF 'terminou no limite de uso da conta com a PROVENANCE' "$M_RUN"; then
  twin TXTm "o molde atribui as mensagens ao 0.156.1 sem medida e diz que o pre-run «terminou» no limite"
else bad "TXTm: o molde nao mostrou a classe"; fi
if lacks "$C_GEN" -F 'descrevia a falha enquanto a tag do GA nao existe' \
   && grep -qF 'forma, e este registro nao caracteriza nenhum deles.' "$C_GEN" \
   && lacks "$C_GEN" -F 'senao npx num cache proprio'; then
  ok "C7: o review record curado nao caracteriza P2 e diz a rota 1 so"; _red="$_red GEN"
else bad "C7: o review record curado"; fi
if grep -qF 'descrevia a falha enquanto a tag do GA nao existe' "$M_GEN"; then
  twin GENm "o review record do molde caracteriza um P2 do anexo"
else bad "GENm: o molde nao mostrou a classe"; fi

# ===========================================================================
say "C8. R3H-04: o indice D do harness do GA cobre os controles vermelhos que ele anota"
cat > "$SCRATCH/c8.py" <<'PYC8'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
want = sys.argv[2].split()
red = set(re.findall(r'_red="\$_red ([A-Za-z0-9-]+)"', text))
need = set()
for m in re.finditer(r'(?m)^_d_need "[^"]*" (.+)$', text):
    need.update(m.group(1).split())
# os do achado: anotados E exigidos; e todo id anotado em _red esta num _d_need (censo)
miss_red = [w for w in want if w not in red]
miss_need = [w for w in want if w not in need]
orphan = sorted(red - need - {"$_c", "$1"})
print("anotados-ausentes=%s exigidos-ausentes=%s orfaos=%s" % (miss_red, miss_need, orphan))
sys.exit(0 if not miss_red and not miss_need and not orphan else 1)
PYC8
if python3 "$SCRATCH/c8.py" "$C_TEST" "B4c B4d R2v R4c R4d" > "$SCRATCH/c8-cured.log" 2>&1; then
  ok "IX: no harness do GA curado B4c/B4d/R2v/R4c/R4d estao anotados e exigidos, e nenhum id anotado fica fora do indice"; _red="$_red IX"
else bad "IX: o indice do harness curado: $(cat "$SCRATCH/c8-cured.log")"; fi
if python3 "$SCRATCH/c8.py" "$M_TEST" "B4c B4d R2v R4c R4d" > "$SCRATCH/c8-mold.log" 2>&1; then
  bad "IXm: o censo nao achou a lacuna no molde (o controle seria vacuo)"
else twin IXm "no molde o indice nao cobre B4c/B4d/R2v/R4c/R4d ($(cat "$SCRATCH/c8-mold.log"))"; fi

# ===========================================================================
say "D. o indice dos controles vermelhos deste harness"
_d_need() {  # $1 = rotulo, $2.. = controles que tem de ter passado
  local _g="$1" _m="" _c; shift
  for _c in "$@"; do
    case " $_red " in *" $_c "*) : ;; *) _m="$_m $_c" ;; esac
  done
  if [ -z "$_m" ]; then ok "$_g: controles exercitados e verdes ($*)"
  else bad "$_g: controle(s) que NAO rodaram ou NAO ficaram verdes:$_m"; fi
}
_d_need "D1 o kit inteiro recusado no K1" K1a K1b
_d_need "D2 R3-CLAIMS-01 (passo 2)" C1 C1m
_d_need "D3 M3-02 (banner)" M302 M302m
_d_need "D4 a espera do registry (passo 18)" REG REGm REG3 REGbad
_d_need "D5 M3-01 (a janela do G0)" W11 W11m W11b
_d_need "D6 D-4 (a rota 1 so no runner do GA)" RT RTm
_d_need "D7 M3-01 (as classes medidas na 0.160.0)" AL ALm CAP CAPm
_d_need "D8 R3S-02/R3S-01 (os textos)" TXT TXTm GEN GENm
_d_need "D9 R3H-04 (o indice do harness do GA)" IX IXm

# ===========================================================================
printf '\n===== RESULTADO: %s PASS, %s FAIL\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
