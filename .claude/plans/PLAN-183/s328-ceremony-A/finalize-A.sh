#!/usr/bin/env bash
# finalize-A.sh — RE-BASEIA o pacote A no HEAD vivo antes da assinatura.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao;
# nao ha gerador para o passo de re-base (o generate-ceremony.sh assume o
# layout architect/round-N/approved.md, que esta cerimonia nao usa).
#
# POR QUE ELE EXISTE. O `finalize_patch.py` RECUSA uma sombra cuja base nao
# seja o HEAD vivo, e o SIGN exige que o `Patch-base` seja ancestral do HEAD
# com ZERO drift nos paths tocados. Na manha do land o HEAD ja andou: o pacote
# B entra antes de A, e outros commits nao-canonicos da noite podem ter
# entrado. Sem este passo o SIGN aborta com uma mensagem correta e inutil.
#
# O QUE ELE FAZ, em ordem:
#   1. recusa se o sentinel JA estiver assinado (re-finalizar invalida o .asc);
#   2. se BASE-SHA.txt == HEAD e o patch aplica limpo => NADA a fazer;
#   3. senao: cria uma arvore-sombra em HEAD (git worktree add --detach),
#      re-aplica o A.patch com `--3way` (conflito => ABORTA nomeando o hunk),
#      roda a bateria curta NA SOMBRA, e re-gera patch + Scope + Patch-base +
#      Patch-sha256 com o finalize_patch.py;
#   4. confere `git apply --check` na arvore viva;
#   5. stageia EXATAMENTE os 4 arquivos regenerados e commita com `-m`
#      (nenhum editor abre em momento nenhum);
#   6. imprime o proximo comando.
#
# Uso:  bash .claude/plans/PLAN-183/s328-ceremony-A/finalize-A.sh
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes do pacote --------------------------------------------------
PLAN_DIR=".claude/plans/PLAN-183"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-A"
SENTINEL="$PLAN_DIR/wave-s328-A-approved.md"
PATCH="$CEREMONY_DIR/A.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
FINALIZE="$PLAN_DIR/w5-ceremony/finalize_patch.py"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S328-A-SIGN.sh"
# Bateria curta rodada NA SOMBRA. A longa (paridade install/upgrade, baseline
# manifest, ownership) e o V-block do LAND — repeti-la aqui dobraria o tempo
# da manha sem acrescentar informacao.
BATTERY=(
  "scripts/tests/test-ownership-verdict-unit.sh"
  "scripts/tests/test-manifest-delivery-route.sh"
)
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
for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE" "$FINALIZE"; do
  [ -f "$f" ] || die "material ausente: $f"
done
# `if`, nao `[ ... ] && die`: sob `set -e` a forma AND-OR cujo teste falha
# devolve 1 no fim do statement, e a semantica de errexit sobre lista AND-OR
# varia entre shells. Um guard que MATA o script quando a condicao e FALSA
# seria o pior modo de falha possivel aqui.
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
SHADOW="$( mktemp -d "${TMPDIR:-/tmp}/s328A-shadow.XXXXXX" )/wt"
git worktree add --detach --quiet "$SHADOW" "$HEAD_SHA" \
  || die "git worktree add falhou — a arvore-sombra nao foi criada"
ok "sombra: $SHADOW"

step "3 — re-aplicando o A.patch na sombra (--3way)"
APPLY_LOG="$SHADOW.apply.log"
if ! git -C "$SHADOW" apply --3way "$ROOT/$PATCH" > "$APPLY_LOG" 2>&1; then
  sed 's/^/    /' "$APPLY_LOG" >&2
  CONFLICTED="$( git -C "$SHADOW" diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ' ' )"
  die "o A.patch NAO re-aplica sobre o HEAD $HEAD_SHA.
  Arquivo(s) em conflito: ${CONFLICTED:-<nenhum registrado; veja o log acima>}
  Alguem editou os mesmos paths depois da finalizacao. NAO force nada:
  chame o CEO com esta saida inteira. Log: $APPLY_LOG"
fi
# `--3way` pode SUCEDER deixando marcadores de conflito quando resolve pela
# base; um patch com '<<<<<<<' assinado seria bytes quebrados no main. A
# varredura e restrita aos paths que o PATCH toca — `git grep` nao veria um
# arquivo NOVO (untracked na sombra) e um `grep -R` na arvore inteira seria
# lento e cheio de falso-positivo em fixtures.
while IFS= read -r _tp; do
  [ -z "$_tp" ] && continue
  [ -f "$SHADOW/$_tp" ] || continue
  if grep -q -e '^<<<<<<< ' -e '^>>>>>>> ' -- "$SHADOW/$_tp"; then
    die "a sombra ficou com marcadores de conflito em $_tp depois do --3way — recusado"
  fi
done < <( git apply --numstat "$ROOT/$PATCH" | awk '{print $3}' )
ok "patch re-aplicado sem conflito e sem marcadores"

step "4 — bateria curta NA SOMBRA"
if ! ( cd "$SHADOW" && PYTHONDONTWRITEBYTECODE=1 bash -n scripts/install.sh ); then
  die "bash -n reprovou em scripts/install.sh na sombra"
fi
ok "bash -n scripts/install.sh"
for t in "${BATTERY[@]}"; do
  [ -f "$SHADOW/$t" ] || die "teste da bateria ausente na sombra: $t"
  T_LOG="$SHADOW.$( basename "$t" ).log"
  T_RC=0
  ( cd "$SHADOW" && PYTHONDONTWRITEBYTECODE=1 bash "$t" ) > "$T_LOG" 2>&1 || T_RC=$?
  if [ "$T_RC" -ne 0 ]; then
    tail -25 "$T_LOG" | sed 's/^/      /' >&2
    die "$t reprovou na sombra (rc=$T_RC) — log em $T_LOG"
  fi
  ok "$t (rc=0)"
done

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
  git commit -q -m "chore(PLAN-183 s328-A): re-base do pacote A em $HEAD_SHA (finalize-A.sh)" \
    || die "o commit falhou — o staging esta intacto; chame o CEO"
  ok "commit criado: $( git rev-parse --short HEAD )"
fi

step "PRONTO"
cat <<EOF

  O pacote A esta baseado em  $( git rev-parse HEAD )  e o patch aplica limpo.

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$SIGN_SCRIPT

EOF
