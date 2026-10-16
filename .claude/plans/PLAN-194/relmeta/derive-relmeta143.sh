#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: derivador de UM uso da relmeta da v1.4.3
# (PLAN-194, RM), clonado do derive-relmeta142.sh (PLAN-193); o toolkit do
# PLAN-188 é o que elimina esta classe.
# derive-relmeta143.sh — deriva relmeta.patch do HEAD e grava no sentinel as
# linhas de DADO da derivação (Derivator-SHA256, Hard-SHA256, Derived-From,
# Scope-Derived) e a seção do texto da tag, entre os marcadores dela.
#
# Roda o apply-relmeta143-edits.py num clone DESCARTÁVEL do HEAD (o derivador
# escreve; escrita nunca é ensaiada na árvore viva), extrai o patch por git diff
# de formato fixo e grava os materiais derivados. NÃO grava o sha256 do patch no
# sentinel: o campo Patch-sha256 é preenchido pelo SIGN do molde sign-min, e uma
# segunda linha com o mesmo valor seria redundante.
#
# IDEMPOTENTE. A base da derivação (`Derived-From`) é o último commit que tocou
# algo FORA deste diretório e do sentinel, e o escopo exige que o PLAN-194 já
# esteja no trem: commitar os materiais (que só tocam aqui e no sentinel e citam
# o PLAN-194) não muda nem uma nem outro. Sobre a mesma base, os bytes saem
# iguais e nada é regravado.
#
#   bash .claude/plans/PLAN-194/relmeta/derive-relmeta143.sh            # deriva
#   bash .claude/plans/PLAN-194/relmeta/derive-relmeta143.sh --commit   # deriva e commita (sem push)
#
# Rode DEPOIS de todos os lands da 1.4.3: o derivador recusa, nomeando a peça,
# se a headline afirmar algo que o HEAD não sustenta. Em seguida: push, o rail
# sobre os materiais commitados, o registro do rail e o SIGN do molde
# (.claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh com relmeta/sign.tsv), cuja
# linha hard `apply-relmeta143-edits.py --verify` refaz esta derivação a partir
# das pré-imagens do Anchor e recusa escopo velho e materiais fora do último land.
set -euo pipefail

# o ambiente git HERDADO não escolhe repositório, índice nem objetos deste script
_genv=""
for _v in $(git rev-parse --local-env-vars); do
  if [ -n "${!_v+x}" ]; then _genv="$_genv $_v"; fi
done
if [ -n "$_genv" ]; then
  printf '\nFAIL: variáveis git herdadas redirecionariam este script:%s\n      rode sem elas (unset%s)\n' "$_genv" "$_genv" >&2
  exit 1
fi

case "$#:${1:-}" in
  0:) COMMIT=0 ;;
  1:--commit) COMMIT=1 ;;
  *) printf '\nFAIL: uso: bash %s [--commit]  (recebido: %s)\n' "$0" "$*" >&2; exit 1 ;;
esac

exec 9>&2
die() { printf '\nFAIL: %s\n' "$*" >&9; exit 1; }
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }
# git diff de formato FIXO: os bytes do patch dependem só das árvores, nunca da
# config git do usuário
canon_diff() {  # canon_diff <repo> <caminho>...
  local r="$1"
  shift
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 git -C "$r" \
    -c diff.noprefix=false -c diff.mnemonicPrefix=false -c diff.relative=false -c core.quotePath=true \
    diff --no-ext-diff --no-textconv --no-color --no-renames --no-relative --full-index --binary \
    --src-prefix=a/ --dst-prefix=b/ --unified=3 --inter-hunk-context=0 --diff-algorithm=myers \
    --indent-heuristic -O/dev/null -- "$@"
}
# --commit: depois do primeiro git add, QUALQUER saída que não seja o commit
# (falha, Ctrl-C, TERM, HUP) desfaz o índice dos materiais. FIM=1 só nas saídas
# previstas: o bash 3.2 entrega $?=0 ao trap de EXIT depois de um erro fatal de
# expansão (variável não definida sob set -u), e sem esta marca esse erro sairia
# rc 0, sem desfazer o índice.
FIM=0
STAGING=0
unstage() {
  if [ "$STAGING" = "1" ]; then
    if git reset -q -- $PACK_FILES; then
      printf '\níndice dos materiais desfeito (git reset -q -- materiais de %s e o sentinel)\n' "$D" >&9
    else
      printf '\nFAIL: não consegui desfazer o índice — rode:  git reset -q -- %s\n' "$PACK_FILES" >&9
    fi
  fi
}
trap 'rc=$?; if [ "$FIM" != "1" ]; then [ "$rc" != "0" ] || rc=1; unstage; fi; exit $rc' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
TOP=$(git rev-parse --show-toplevel) || die "não é um checkout git (rode na raiz do checkout)"
cd "$TOP"
ROOT=$(pwd -P)

# ---------------------------------------------------------------- constantes
PLAN=PLAN-194
D=.claude/plans/PLAN-194/relmeta
SENT=.claude/plans/PLAN-194/relmeta-approved.md
BASE_TAG=v1.4.2
BASE_SHA=b55084da6dd8e4a05fc9893b2690df8aebcfd0ca
COAUTHOR='Claude Opus 5.5 <noreply@anthropic.com>'
# ------------------------------------------------------------ fim constantes

APPLY="$D/apply-relmeta143-edits.py"
HARD="$D/hard-relmeta.sh"
PATCH="$D/relmeta.patch"
T_REL=.claude/scripts/local/release.sh
T_MAN=.claude/governance/gate-scripts-manifest.txt
T_TST=.claude/scripts/tests/test_release_bump_sites.py
# os únicos caminhos que o --commit pode levar: os de $D e o sentinel
PACK_FILES="$APPLY $D/derive-relmeta143.sh $HARD $D/sign.tsv $D/red-control.txt $D/rail-record.md $D/rehearse-relmeta143.sh $PATCH $SENT"

for f in "$APPLY" "$HARD" "$SENT"; do
  [ -f "$f" ] && [ ! -L "$f" ] || die "material ausente ou não-regular: $f"
done
[ -z "$(git status --porcelain --untracked-files=no -- "$T_REL" "$T_MAN" "$T_TST" CHANGELOG.md)" ] \
  || die "um dos alvos (ou o CHANGELOG) tem modificação não commitada — a derivação parte do HEAD"
git rev-parse -q --verify "refs/tags/$BASE_TAG" >/dev/null \
  || die "tag $BASE_TAG ausente — a relmeta-143 deriva com a tag do GA $BASE_TAG no repositório"
[ "$(git rev-parse --verify "refs/tags/$BASE_TAG^{commit}")" = "$BASE_SHA" ] \
  || die "a tag $BASE_TAG não descasca para $BASE_SHA"
git merge-base --is-ancestor "$BASE_SHA" HEAD || die "$BASE_TAG ($BASE_SHA) não é ancestral do HEAD"
HEAD_SHA=$(git rev-parse HEAD) || die "git rev-parse HEAD falhou"
BASE_EFF=$(git log -1 --format=%H HEAD -- . ":(exclude)$D" ":(exclude)$SENT") || die "git log da base efetiva falhou"
[ -n "$BASE_EFF" ] || die "não achei o último commit fora de $D e do sentinel"

W=$(mktemp -d "${TMPDIR:-/tmp}/relmeta143-derive.XXXXXX") || die "mktemp falhou"
git -c core.hooksPath=/dev/null -c advice.detachedHead=false clone --quiet --local --no-hardlinks "$ROOT" "$W/wt" \
  || die "clone descartável falhou"
git -C "$W/wt" -c core.hooksPath=/dev/null -c advice.detachedHead=false checkout --quiet --detach "$HEAD_SHA" \
  || die "checkout do HEAD no clone falhou"
[ "$(git -C "$W/wt" rev-parse HEAD)" = "$HEAD_SHA" ] || die "o clone não está no HEAD"
# o derivador pode ainda não estar no HEAD: leve ESTE para o clone, no mesmo caminho
mkdir -p "$W/wt/$D" || die "mkdir no clone falhou"
[ ! -L "$W/wt/$APPLY" ] || die "destino é symlink no clone: $APPLY"
cp "$APPLY" "$W/wt/$APPLY" || die "cópia do derivador para o clone falhou"
# um ambiente de allowlist: nada de CLAUDE_*, CEO_* nem PYTHONPATH chega ao derivador
KEEP_ENV="HOME USER LOGNAME SHELL TERM LANG LC_ALL LC_CTYPE TMPDIR PYTHONUSERBASE VIRTUAL_ENV PYENV_ROOT PYENV_VERSION"
envs=()
for v in $KEEP_ENV; do
  if [ -n "${!v+x}" ]; then envs+=("$v=${!v}"); fi
done
( cd "$W/wt" && env -i ${envs[@]+"${envs[@]}"} PATH="$PATH" \
    PYTHONDONTWRITEBYTECODE=1 python3 "$APPLY" --repo . ) >"$W/derive.out" 2>&1 \
  || { cat "$W/derive.out" >&2; die "o derivador recusou (log: $W/derive.out)"; }
( cd "$W/wt" && env -i ${envs[@]+"${envs[@]}"} PATH="$PATH" \
    PYTHONDONTWRITEBYTECODE=1 python3 "$APPLY" --repo . --tag-text ) >"$W/tag-text" 2>"$W/tag-text.err" \
  || { cat "$W/tag-text.err" >&2; die "o derivador não imprimiu o texto da tag"; }
canon_diff "$W/wt" "$T_REL" "$T_MAN" "$T_TST" >"$W/patch" || die "git diff falhou"
[ -s "$W/patch" ] || die "patch vazio"
# o patch derivado tem de aplicar sobre a árvore viva (o SIGN o aplica no clone do Anchor)
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 git apply --check --whitespace=nowarn "$W/patch" \
  || die "o patch derivado não aplica sobre a árvore viva (log: $W/derive.out)"
EXTRA=$(git -C "$W/wt" status --porcelain --untracked-files=all \
  | awk -v a="$T_REL" -v b="$T_MAN" -v c="$T_TST" -v d="$D/" \
      '{p=$2} p!=a && p!=b && p!=c && index(p, d)!=1 {print p}')
[ -z "$EXTRA" ] || die "o derivador tocou fora do escopo: $EXTRA"
SCOPE=$(sed -n 's/^scope: //p' "$W/derive.out")
[ -n "$SCOPE" ] || die "o derivador não imprimiu o escopo (log: $W/derive.out)"
ASHA=$(sha256f "$APPLY")
HSHA=$(sha256f "$HARD")

python3 - "$SENT" "$W/sentinel" "$ASHA" "$HSHA" "$BASE_EFF" "$SCOPE" "$W/tag-text" <<'PY' || die "não consegui montar o sentinel derivado"
import pathlib, re, sys
src, dst, asha, hsha, base, scope, tagp = sys.argv[1:8]
t = pathlib.Path(src).read_text(encoding="utf-8")
for key, val in (("Derivator-SHA256", asha), ("Hard-SHA256", hsha),
                 ("Derived-From", base), ("Scope-Derived", scope)):
    if len(re.findall(r"(?m)^" + key + r":", t)) != 1:
        raise SystemExit("linha %s ausente ou repetida no sentinel" % key)
    t = re.sub(r"(?m)^" + key + r":.*$", lambda _m: key + ": " + val, t, count=1)
beg, end = "<!-- texto-da-tag: derivado -->\n", "<!-- fim do texto-da-tag -->\n"
sec = pathlib.Path(tagp).read_text(encoding="utf-8")
if not (sec.startswith(beg) and sec.endswith(end)):
    raise SystemExit("o texto da tag derivado não vem entre os marcadores")
if t.count(beg) != 1 or t.count(end) != 1 or t.find(end) < t.find(beg):
    raise SystemExit("marcadores do texto da tag ausentes, repetidos ou fora de ordem no sentinel")
i, j = t.find(beg), t.find(end) + len(end)
t = t[:i] + sec + t[j:]
pathlib.Path(dst).write_text(t, encoding="utf-8")
PY

if [ -f "$PATCH" ] && cmp -s "$W/patch" "$PATCH" && cmp -s "$W/sentinel" "$SENT"; then
  printf '\ninalterado: %s e o sentinel já são a derivação desta base\n' "$PATCH"
else
  for f in "$PATCH" "$SENT"; do
    [ ! -L "$f" ] || die "destino é symlink: $f"
  done
  cp "$W/patch" "$PATCH" || die "gravação do patch falhou"
  cp "$W/sentinel" "$SENT" || die "gravação do sentinel falhou"
  cmp -s "$W/patch" "$PATCH" && cmp -s "$W/sentinel" "$SENT" || die "os materiais gravados não são os derivados"
  printf '\nderivado e gravado: %s + sentinel\n' "$PATCH"
fi
grep -q "^Derived-From: $BASE_EFF\$" "$SENT" || die "Derived-From não gravou"
printf '   Scope-Derived    = %s\n' "$SCOPE"
printf '   Derived-From     = %s (último commit fora de %s e do sentinel)\n' "$BASE_EFF" "$D"
printf '   relmeta.patch    = sha256 %s (%s linhas)\n' "$(sha256f "$PATCH")" "$(wc -l <"$PATCH" | tr -d ' ')"
printf '   Derivator-SHA256 = %s\n' "$ASHA"
printf '   Hard-SHA256      = %s\n' "$HSHA"
sed -n 's/^claim PASS /   âncora OK /p' "$W/derive.out"
git apply --stat "$PATCH"

# o clone descartável (centenas de MB) sai quando a execução termina bem; numa
# falha ele fica, com os logs. Limpeza confinada: só o diretório deste script,
# pelo prefixo do mktemp e sem seguir link.
limpa_w() {
  python3 -I -B -c 'import os, shutil, sys
w = sys.argv[1]
if not os.path.basename(w).startswith("relmeta143-derive.") or os.path.islink(w):
    sys.exit(1)
shutil.rmtree(w)' "$W" || die "não consegui apagar o diretório da derivação $W"
}

if [ "$COMMIT" != "1" ]; then
  limpa_w
  FIM=1
  exit 0
fi

# ------------------------------------------------------------------ --commit
# um índice que já leva SÓ materiais do pacote (um --commit anterior interrompido
# antes do trap, ou um git add à mão) segue: eles são re-adicionados abaixo;
# qualquer caminho FORA da lista no índice recusa, com a rota
inpack() {  # inpack <caminho> — rc 0 se o caminho é um dos materiais do pacote
  local f
  for f in $PACK_FILES; do
    if [ "$1" = "$f" ]; then return 0; fi
  done
  return 1
}
PRE=$(git diff --cached --name-only) || die "git diff --cached falhou"
PRE_BAD=""
while IFS= read -r p; do
  if [ -n "$p" ] && ! inpack "$p"; then PRE_BAD="$PRE_BAD $p"; fi
done <<EOF_PRE
$PRE
EOF_PRE
[ -z "$PRE_BAD" ] || die "há caminho FORA dos materiais no índice — o commit dos materiais leva SÓ $D e o sentinel:
$PRE_BAD
      confira com  git status  e desfaça com  git reset -q -- <caminho>  (ou  git reset -q  para o índice inteiro)"
STAGING=1
for f in $PACK_FILES; do
  if [ -e "$f" ]; then
    [ ! -L "$f" ] || die "material é symlink: $f"
    git add -- "$f" || die "git add $f falhou"
  fi
done
STAGED=$(git diff --cached --name-only)
if [ -z "$STAGED" ]; then
  STAGING=0
  printf '\nnada a commitar: os materiais no HEAD já são esta derivação.\n'
  limpa_w
  FIM=1
  exit 0
fi
BAD=""
while IFS= read -r p; do
  if [ -n "$p" ] && ! inpack "$p"; then BAD="$BAD $p"; fi
done <<EOF_STAGED
$STAGED
EOF_STAGED
[ -z "$BAD" ] || die "o índice ganhou caminho fora dos materiais:$BAD"
# R8 do ceremony-lint: nenhum material com bit de execução no índice
EXEC=$(git ls-files --stage -- $PACK_FILES | awk '$1 != "100644" {print $4}')
[ -z "$EXEC" ] || die "material com modo diferente de 100644 no índice: $EXEC (tire o bit do arquivo E do índice)"
# gates de CORPUS sobre a árvore JÁ stageada (CLAUDE.md §4), antes do commit;
# uma reprovação (ou um sinal) desfaz o índice pelo trap
python3 .claude/scripts/check-test-env-hygiene.py >"$W/hygiene.out" 2>&1 \
  || { tail -n 20 "$W/hygiene.out" >&2; die "check-test-env-hygiene reprovou (log: $W/hygiene.out)"; }
bash .claude/scripts/check-contamination.sh >"$W/contam.out" 2>&1 \
  || { tail -n 20 "$W/contam.out" >&2; die "check-contamination reprovou (log: $W/contam.out)"; }
python3 .claude/scripts/check-ceremony-script.py >"$W/lint.out" 2>&1 \
  || { tail -n 20 "$W/lint.out" >&2; die "ceremony-lint reprovou (log: $W/lint.out)"; }
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >"$W/counts.out" 2>&1 \
  || { tail -n 20 "$W/counts.out" >&2; die "verify-counts reprovou (log: $W/counts.out)"; }
python3 .claude/scripts/check-staleness.py >"$W/stale.out" 2>&1 \
  || { tail -n 20 "$W/stale.out" >&2; die "check-staleness reprovou (log: $W/stale.out)"; }
{
  printf 'plan(%s): relmeta-143 — materiais do RM da v1.4.3, patch e sentinel derivados do HEAD\n\n' "$PLAN"
  printf 'relmeta.patch e as linhas derivadas de relmeta-approved.md (Derivator-SHA256,\n'
  printf 'Hard-SHA256, Derived-From, Scope-Derived e a seção do texto da tag), gerados por\n'
  printf 'derive-relmeta143.sh num clone descartável sobre a base %s.\n' "$(git rev-parse --short=12 "$BASE_EFF")"
  printf 'Escopo derivado de git log %s..HEAD (planos citados nos assuntos, inclusive os\n' "$BASE_TAG"
  printf 'abandonados e os de fechamento; ADRs tocados): %s.\n\n' "$SCOPE"
  printf 'Só caminhos de %s e o sentinel entram neste commit. A assinatura é o\n' "$D"
  printf 'SIGN do molde sign-min (.claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh com\n'
  printf 'relmeta/sign.tsv), cuja linha hard apply-relmeta143-edits.py --verify re-deriva\n'
  printf 'a partir das pré-imagens do Anchor e recusa escopo velho e lands depois destes\n'
  printf 'materiais. O registro do rail vem depois do rail.\n\n'
  printf 'Co-Authored-By: %s\n' "$COAUTHOR"
} >"$W/commit-msg.txt" || die "não consegui escrever a mensagem do commit"
git commit -q -F "$W/commit-msg.txt" || die "git commit falhou"
STAGING=0
printf '\nmateriais commitados em %s:\n' "$(git rev-parse --short=12 HEAD)"
printf '%s\n' "$STAGED" | sed 's/^/   /'
printf '\nPróximo: push; rail sobre os materiais commitados; registro do rail; SIGN do molde.\n'
limpa_w
FIM=1
exit 0
