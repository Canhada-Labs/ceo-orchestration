#!/usr/bin/env bash
# finalize-B.sh — RE-BASEIA o pacote B no HEAD vivo antes da assinatura.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao;
# nao ha gerador para o passo de re-base (o generate-ceremony.sh assume o
# layout architect/round-N/approved.md, que esta cerimonia nao usa).
#
# POR QUE ELE EXISTE. O `finalize_patch.py` RECUSA uma sombra cuja base nao
# seja o HEAD vivo, e o SIGN exige que o `Patch-base` seja ancestral do HEAD
# com ZERO drift nos paths tocados. Na manha do land o HEAD ja andou — no
# minimo pelo commit NAO-CANONICO que traz o profiler curado, que este pacote
# pressupoe. Sem este passo o SIGN aborta com uma mensagem correta e inutil.
#
# O QUE ELE FAZ, em ordem:
#   0. exige a metade NAO-CANONICA em HEAD (o profiler com as 4 flags e o
#      teste do gate) — sem ela o pacote nao deve nem ser finalizado;
#   1. recusa se o sentinel JA estiver assinado (re-finalizar invalida o .asc);
#   2. se BASE-SHA.txt == HEAD e o patch aplica limpo => NADA a fazer;
#   3. senao: cria uma arvore-sombra em HEAD (git worktree add --detach),
#      re-aplica o B.patch com `--3way` (conflito => ABORTA nomeando o hunk),
#      roda a bateria curta NA SOMBRA, e re-gera patch + Scope + Patch-base +
#      Patch-sha256 com o finalize_patch.py;
#   4. confere `git apply --check` na arvore viva;
#   5. stageia EXATAMENTE os 4 arquivos regenerados e commita com `-m`
#      (nenhum editor abre em momento nenhum);
#   6. imprime o proximo comando.
#
# Uso:  bash .claude/plans/PLAN-169/s328-ceremony-B/finalize-B.sh
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes do pacote --------------------------------------------------
PLAN_DIR=".claude/plans/PLAN-169"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-B"
SENTINEL="$PLAN_DIR/wave-s328-B-approved.md"
PATCH="$CEREMONY_DIR/B.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S328-B-SIGN.sh"
PROFILER=".claude/scripts/profile-opus-4-7.py"
GATE_TEST=".claude/scripts/tests/test_hook_latency_relative_gate.py"
YML=".github/workflows/validate.yml"
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

SHADOW=""
_cleanup() {
  if [ -n "$SHADOW" ] && [ -d "$SHADOW" ]; then
    git worktree remove --force "$SHADOW" >/dev/null 2>&1 || printf ''
    rm -rf "$SHADOW" 2>/dev/null || printf ''
  fi
  git worktree prune >/dev/null 2>&1 || printf ''
}
trap _cleanup EXIT

step "0 — pre-condicoes"
for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE" "$BASELINE_ENV" "$FINALIZE"; do
  [ -f "$f" ] || die "material ausente: $f"
done

# A metade NAO-CANONICA tem de estar em HEAD. Achado do pair-rail rodadas 1 e 2
# (P1-1): o `validate.yml` deste patch passa flags que so o profiler curado
# conhece; sem ele em HEAD o gate sairia 2 em todo push. Leitura de
# `git show HEAD:`, nunca da arvore de trabalho — hoje a arvore passaria e o
# HEAD nao, e checar a arvore mediria a coisa errada.
_head_profiler="$(git show "HEAD:$PROFILER" 2>/dev/null || printf '')"
[ -n "$_head_profiler" ] || die "$PROFILER nao existe em HEAD"
_flags="$(sed -n 's/^EXPECTED_HELP_FLAGS=//p' "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
[ -n "$_flags" ] || die "EXPECTED_HELP_FLAGS ausente em $BASELINE_ENV"
MISSING_FLAGS=""
for _flag in $_flags; do
  # Ancorado por FRONTEIRA de palavra, nunca substring: um profiler que
  # declarasse `--exec-reference-v2` e NAO `--exec-reference` passaria num
  # `grep -c -- "$_flag"` e reprovaria na CI. O caso T8 do harness planta
  # exatamente essa forma.
  _n="$(printf '%s\n' "$_head_profiler" \
        | grep -cE -- "(^|[^A-Za-z0-9_-])${_flag}([^A-Za-z0-9_-]|\$)" || true)"
  [ "$_n" -ge 1 ] || MISSING_FLAGS="$MISSING_FLAGS $_flag"
done
[ -z "$MISSING_FLAGS" ] || die "o profiler em HEAD NAO conhece a(s) flag(s):$MISSING_FLAGS

  Este pacote canonico faz o $YML passar essas flags. Commite a metade
  NAO-CANONICA primeiro (ela nao precisa de cerimonia — o oraculo responde 0):
    $PROFILER
    $GATE_TEST
  Depois rode este script de novo."
git show "HEAD:$GATE_TEST" >/dev/null 2>&1 \
  || die "$GATE_TEST nao existe em HEAD — a bateria da sombra nao teria o que rodar"
ok "metade nao-canonica presente em HEAD"

# `if`, nao `[ ... ] && die`: sob `set -e` a forma AND-OR cujo teste falha
# devolve 1 no fim do statement, e a semantica de errexit sobre lista AND-OR
# varia entre shells.
if [ -f "$SENTINEL.asc" ]; then
  die "o sentinel JA esta assinado ($SENTINEL.asc).
  Re-finalizar reescreve o sentinel e invalida a assinatura.
  Se voce precisa mesmo re-finalizar, apague o .asc conscientemente e
  re-assine depois:  rm $ROOT/$SENTINEL.asc"
fi

_cur_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '')"
[ "$_cur_branch" = "main" ] || die "HEAD esta em '$_cur_branch', nao em 'main' — o land so roda no main"
HEAD_SHA="$(git rev-parse HEAD)"
ok "HEAD em main: $HEAD_SHA"

RECORDED_BASE="$(sed -n 's/^[[:space:]]*\([0-9a-f]\{40\}\)[[:space:]]*$/\1/p' "$BASE_SHA_FILE" | head -1)"
[ -n "$RECORDED_BASE" ] || die "$BASE_SHA_FILE nao contem um sha de 40 hex"
printf '      BASE-SHA.txt : %s\n' "$RECORDED_BASE"
printf '      HEAD vivo    : %s\n' "$HEAD_SHA"

step "1 — precisa re-basear?"
NEEDS_REBASE=1
if [ "$RECORDED_BASE" = "$HEAD_SHA" ]; then
  if git apply --check "$PATCH" >/dev/null 2>&1; then
    NEEDS_REBASE=0
  else
    die "BASE-SHA.txt casa o HEAD mas o patch NAO aplica limpo.
  A arvore de trabalho tem modificacoes nos paths do patch, ou o patch e
  residuo de outra base. Rode  git status --short  e chame o CEO."
  fi
fi
if [ "$NEEDS_REBASE" = "0" ]; then
  ok "o pacote ja esta baseado no HEAD vivo e o patch aplica limpo — NADA a fazer"
  step "PRONTO (no-op)"
  printf '\n  PROXIMO COMANDO (copie e cole inteiro):\n\n'
  printf '    bash %s/%s\n\n' "$ROOT" "$SIGN_SCRIPT"
  exit 0
fi
printf '  o HEAD andou desde a finalizacao — re-basear\n'

step "2 — arvore-sombra em $HEAD_SHA"
SHADOW="$( mktemp -d "${TMPDIR:-/tmp}/s328B-shadow.XXXXXX" )/wt"
git worktree add --detach --quiet "$SHADOW" "$HEAD_SHA" \
  || die "git worktree add falhou — a arvore-sombra nao foi criada"
ok "sombra: $SHADOW"

step "3 — re-aplicando o B.patch na sombra (--3way)"
APPLY_LOG="$SHADOW.apply.log"
if ! git -C "$SHADOW" apply --3way "$ROOT/$PATCH" > "$APPLY_LOG" 2>&1; then
  sed 's/^/    /' "$APPLY_LOG" >&2
  CONFLICTED="$( git -C "$SHADOW" diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ' ' )"
  die "o B.patch NAO re-aplica sobre o HEAD $HEAD_SHA.
  Arquivo(s) em conflito: ${CONFLICTED:-<nenhum registrado; veja o log acima>}
  Alguem editou os mesmos paths depois da finalizacao. NAO force nada:
  chame o CEO com esta saida inteira. Log: $APPLY_LOG"
fi
# `--3way` pode SUCEDER deixando marcadores de conflito quando resolve pela
# base; um patch com '<<<<<<<' assinado seria bytes quebrados no main. A
# varredura e restrita aos paths que o PATCH toca.
while IFS= read -r _tp; do
  [ -z "$_tp" ] && continue
  [ -f "$SHADOW/$_tp" ] || continue
  if grep -q -e '^<<<<<<< ' -e '^>>>>>>> ' -- "$SHADOW/$_tp"; then
    die "a sombra ficou com marcadores de conflito em $_tp depois do --3way — recusado"
  fi
done < <( git apply --numstat "$ROOT/$PATCH" | awk '{print $3}' )
ok "patch re-aplicado sem conflito e sem marcadores"

step "4 — bateria curta NA SOMBRA"
# A bateria LONGA (execucao real do profiler + simulacao do PYSUM) e o V-block
# do LAND; repeti-la aqui dobraria o tempo da manha sem acrescentar informacao.
# O que roda aqui e o que responde "o patch re-aplicado ainda e valido?".

# 4a — o YAML pos-patch continua parseavel. Um patch que quebra o workflow so
# apareceria no push; e barato pegar aqui.
if python3 -c 'import yaml' >/dev/null 2>&1; then
  ( cd "$SHADOW" && python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$YML" ) \
    || die "4a: yaml.safe_load reprovou em $YML na sombra"
  ok "4a: yaml.safe_load OK"
else
  printf '  \033[33mWARN\033[0m 4a: PyYAML ausente — o actionlint abaixo tambem cobre\n'
fi

# 4b — actionlint, se existir nesta maquina.
if command -v actionlint >/dev/null 2>&1; then
  AL_LOG="$SHADOW.actionlint.log"
  ( cd "$SHADOW" && actionlint "$YML" ) > "$AL_LOG" 2>&1 \
    || { sed 's/^/      /' "$AL_LOG" >&2; die "4b: actionlint reprovou em $YML"; }
  ok "4b: actionlint verde"
else
  printf '  \033[33mWARN\033[0m 4b: actionlint AUSENTE — o CI executa\n'
fi

# 4c — literais de compatibilidade preservados, contagem DECLARADA.
_lit_exp="$(sed -n 's/^EXPECTED_YML_BOTH_ATTEMPTS_LITERAL=//p' "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
[ -n "$_lit_exp" ] || die "EXPECTED_YML_BOTH_ATTEMPTS_LITERAL ausente em $BASELINE_ENV"
_lit_obs="$(grep -c 'FAILED on BOTH attempts (rc1=' "$SHADOW/$YML" || true)"
[ "$_lit_obs" = "$_lit_exp" ] \
  || die "4c: literal 'FAILED on BOTH attempts (rc1=' aparece $_lit_obs vez(es), esperado $_lit_exp
  Os provadores PLAN-161/proof-retry-matrix.sh e PLAN-159/wave2-regression-proof.sh
  casam esse texto; mudar a contagem os quebra em silencio."
ok "4c: literal de compatibilidade preservado ($_lit_obs)"

# 4d — a suite do gate relativo, NA SOMBRA, contra a contagem declarada.
_exp_passed="$(sed -n 's/^EXPECTED_GATE_PYTEST_PASSED=//p' "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
[ -n "$_exp_passed" ] || die "EXPECTED_GATE_PYTEST_PASSED ausente em $BASELINE_ENV"
PY_LOG="$SHADOW.pytest.log"
PY_RC=0
( cd "$SHADOW" && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest "$GATE_TEST" -q -p no:cacheprovider ) \
  > "$PY_LOG" 2>&1 || PY_RC=$?
[ "$PY_RC" -eq 0 ] || { tail -25 "$PY_LOG" | sed 's/^/      /' >&2
                        die "4d: a suite do gate reprovou na sombra (rc=$PY_RC) — log em $PY_LOG"; }
# "N deselected" NAO e "N passed" (licao S325): o numero vem do campo `passed`.
# A linha do `pytest -q` COMECA pelo numero ("62 passed in 63.81s") — o sed
# anterior exigia um nao-digito antes dele e abortava com a suite VERDE
# (medido na manha de 2026-08-26, 1a execucao do MORNING). Aceita inicio de
# linha OU um nao-digito antes; o numero e sempre o imediatamente antes de
# " passed" (nunca o de "deselected"/"failed").
_obs_passed="$(grep -oE '(^|[^0-9])[0-9]+ passed' "$PY_LOG" | head -1 | grep -oE '[0-9]+')"
[ -n "$_obs_passed" ] || die "4d: nao consegui ler 'N passed' — log em $PY_LOG"
[ "$_obs_passed" = "$_exp_passed" ] \
  || die "4d: $_obs_passed teste(s) passaram, esperado $_exp_passed (EXPECTED_GATE_PYTEST_PASSED).
  Menos e regressao; mais significa que a suite cresceu — atualize
  $BASELINE_ENV conscientemente. Log: $PY_LOG"
ok "4d: suite do gate $_obs_passed/$_exp_passed na sombra"

step "5 — re-gerando patch, Scope, Patch-base e Patch-sha256"
python3 "$FINALIZE" \
  --shadow "$SHADOW" \
  --out "$ROOT/$PATCH" \
  --sentinel "$ROOT/$SENTINEL" \
  --proposed "$ROOT/$PROPOSED" \
  --repo-root "$ROOT" \
  || die "finalize_patch.py recusou — leia a mensagem acima; nada foi commitado"

printf '%s\n' "$HEAD_SHA" > "$BASE_SHA_FILE"
ok "BASE-SHA.txt atualizado"

git apply --check "$PATCH" || die "o patch re-gerado NAO aplica na arvore viva"
ok "git apply --check verde na arvore viva"

step "6 — commit dos materiais regenerados (sem editor)"
# Staging EXPLICITO, arquivo a arquivo. Um staging por DIRETORIO (ou o
# add-tudo) arrastaria o trabalho de outros pacotes que ainda esteja na
# arvore; o conjunto e conferido logo abaixo e um path a mais ABORTA.
for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE"; do
  git add -- "$f"
done
STAGED="$( git diff --cached --name-only | sort -u )"
if [ -z "$STAGED" ]; then
  ok "os 4 materiais sairam byte-identicos — nada a commitar"
else
  printf '%s\n' "$STAGED" | sed 's/^/    staged: /'
  # Conjunto FECHADO: se algo alem dos 4 esta staged, alguem tinha index sujo.
  EXTRA="$( printf '%s\n' "$STAGED" \
            | grep -v -x -e "$PATCH" -e "$SENTINEL" -e "$PROPOSED" -e "$BASE_SHA_FILE" \
            || printf '' )"
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  [ -z "$EXTRA" ] || die "index carrega path(s) fora dos 4 materiais:
$( printf '  %s\n' $EXTRA )
  Rode  git reset  e comece de novo."
  git commit -q -m "chore(PLAN-169 s328-B): re-base do pacote B em $HEAD_SHA (finalize-B.sh)" \
    || die "o commit falhou — o staging esta intacto; chame o CEO"
  ok "commit criado: $( git rev-parse --short HEAD )"
fi

step "PRONTO"
cat <<EOF

  O pacote B esta baseado em  $( git rev-parse HEAD )  e o patch aplica limpo.

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$SIGN_SCRIPT

EOF
