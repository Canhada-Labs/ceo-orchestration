#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: derivador de UM uso da relmeta da v1.4.2
# (PLAN-193 W6), clonado do derive-relmeta141.sh (PLAN-192); o toolkit do
# PLAN-188 é o que elimina esta classe.
# derive-relmeta142.sh — deriva RELMETA142.patch do HEAD e pina no sentinel o
# sha256 do patch, o sha256 do derivador, a base da derivação e o escopo.
#
# Roda o apply-relmeta142-edits.py num clone DESCARTÁVEL do HEAD (o derivador
# escreve; escrita nunca é ensaiada na árvore viva), extrai o patch por git diff
# e grava os dois materiais derivados neste diretório.
#
# IDEMPOTENTE. A base da derivação (`Derived-From`) é o último commit que tocou
# algo FORA deste diretório, e o escopo exige que o PLAN-193 já esteja no trem:
# commitar os materiais (que só tocam aqui e citam o PLAN-193) não muda nem uma
# nem outro. Sobre a mesma base, os bytes saem iguais e nada é regravado.
#
#   bash .claude/plans/PLAN-193/relmeta/derive-relmeta142.sh            # deriva
#   bash .claude/plans/PLAN-193/relmeta/derive-relmeta142.sh --commit   # deriva e commita (sem push)
#
# Rode DEPOIS de todos os lands da 1.4.2 (lands livres, re-pin do Codex,
# wave-opus55, FN-04): o derivador recusa, nomeando a peça, se a headline
# afirmar algo que o HEAD não sustenta. Em seguida: git push origin main e o
# OWNER-RELMETA142-SIGN.sh, que refaz esta derivação e recusa, pelo nome, um
# patch velho.
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
# git diff de formato FIXO — o MESMO do OWNER-RELMETA142-SIGN.sh: os bytes do
# patch dependem só das árvores, nunca da config git do usuário
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
# (falha, Ctrl-C, TERM, HUP) desfaz o índice dos materiais
STAGING=0
unstage() {
  if [ "$STAGING" = "1" ]; then
    if git reset -q -- $PACK_FILES; then
      printf '\níndice dos materiais desfeito (git reset -q -- materiais de %s)\n' "$D" >&9
    else
      printf '\nFAIL: não consegui desfazer o índice — rode:  git reset -q -- %s\n' "$PACK_FILES" >&9
    fi
  fi
}
trap 'rc=$?; [ $rc -eq 0 ] || unstage' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
TOP=$(git rev-parse --show-toplevel) || die "não é um checkout git (rode na raiz do checkout vivo)"
cd "$TOP"
ROOT=$(pwd -P)

# ---------------------------------------------------------------- constantes
PLAN=PLAN-193
D=.claude/plans/PLAN-193/relmeta
BASE_TAG=v1.4.1
COAUTHOR='Claude Opus 5.5 (1M context) <noreply@anthropic.com>'
# ------------------------------------------------------------ fim constantes

APPLY="$D/apply-relmeta142-edits.py"
PATCH="$D/RELMETA142.patch"
SENT="$D/relmeta142-approved.md"
T_REL=.claude/scripts/local/release.sh
T_MAN=.claude/governance/gate-scripts-manifest.txt
T_TST=.claude/scripts/tests/test_release_bump_sites.py
# os únicos caminhos que o --commit pode levar (todos dentro de $D)
PACK_FILES="$APPLY $D/derive-relmeta142.sh $D/OWNER-RELMETA142-SIGN.sh $D/rehearse-relmeta142.sh $SENT $PATCH"

for f in "$APPLY" "$SENT"; do
  [ -f "$f" ] && [ ! -L "$f" ] || die "material ausente ou não-regular: $f"
done
[ -z "$(git status --porcelain --untracked-files=no -- "$T_REL" "$T_MAN" "$T_TST" CHANGELOG.md)" ] \
  || die "um dos alvos (ou o CHANGELOG) tem modificação não commitada — a derivação parte do HEAD"
git rev-parse -q --verify "refs/tags/$BASE_TAG" >/dev/null \
  || die "tag $BASE_TAG ausente — a relmeta-142 só deriva DEPOIS do corte do GA $BASE_TAG"
git merge-base --is-ancestor "$BASE_TAG" HEAD || die "$BASE_TAG não é ancestral do HEAD"
HEAD_SHA=$(git rev-parse HEAD) || die "git rev-parse HEAD falhou"
BASE_EFF=$(git log -1 --format=%H HEAD -- . ":(exclude)$D") || die "git log da base efetiva falhou"
[ -n "$BASE_EFF" ] || die "não achei o último commit fora de $D"

W=$(mktemp -d "${TMPDIR:-/tmp}/relmeta142-derive.XXXXXX") || die "mktemp falhou"
git -c core.hooksPath=/dev/null clone --quiet --local --no-hardlinks "$ROOT" "$W/wt" \
  || die "clone descartável falhou"
[ "$(git -C "$W/wt" rev-parse HEAD)" = "$HEAD_SHA" ] || die "o clone não está no HEAD vivo"
# o derivador pode ainda não estar no HEAD: leve ESTE para o clone, no mesmo caminho
mkdir -p "$W/wt/$D" || die "mkdir no clone falhou"
[ ! -L "$W/wt/$APPLY" ] || die "destino é symlink no clone: $APPLY"
cp "$APPLY" "$W/wt/$APPLY" || die "cópia do derivador para o clone falhou"
# o MESMO ambiente de allowlist em que o SIGN re-deriva: o que passa aqui passa lá
KEEP_ENV="HOME USER LOGNAME SHELL TERM LANG LC_ALL LC_CTYPE TMPDIR PYTHONUSERBASE VIRTUAL_ENV PYENV_ROOT PYENV_VERSION"
envs=()
for v in $KEEP_ENV; do
  if [ -n "${!v+x}" ]; then envs+=("$v=${!v}"); fi
done
( cd "$W/wt" && env -i ${envs[@]+"${envs[@]}"} PATH="$PATH" CLAUDE_PROJECT_DIR="$W/wt" \
    PYTHONDONTWRITEBYTECODE=1 python3 "$APPLY" --repo . ) >"$W/derive.out" 2>&1 \
  || { cat "$W/derive.out" >&2; die "o derivador recusou (log: $W/derive.out)"; }
canon_diff "$W/wt" "$T_REL" "$T_MAN" "$T_TST" >"$W/patch" || die "git diff falhou"
[ -s "$W/patch" ] || die "patch vazio"
# o patch derivado tem de aplicar sobre a árvore viva (o SIGN o aplica nela)
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 git apply --check --whitespace=nowarn "$W/patch" \
  || die "o patch derivado não aplica sobre a árvore viva (log: $W/derive.out)"
EXTRA=$(git -C "$W/wt" status --porcelain --untracked-files=all \
  | awk -v a="$T_REL" -v b="$T_MAN" -v c="$T_TST" -v d="$D/" \
      '{p=$2} p!=a && p!=b && p!=c && index(p, d)!=1 {print p}')
[ -z "$EXTRA" ] || die "o derivador tocou fora do escopo: $EXTRA"
SCOPE=$(sed -n 's/^scope: //p' "$W/derive.out")
[ -n "$SCOPE" ] || die "o derivador não imprimiu o escopo (log: $W/derive.out)"
PSHA=$(sha256f "$W/patch")
ASHA=$(sha256f "$APPLY")

python3 - "$SENT" "$W/sentinel" "$PSHA" "$ASHA" "$BASE_EFF" "$SCOPE" <<'PY' || die "não consegui montar o sentinel derivado"
import pathlib, re, sys
src, dst, psha, asha, base, scope = sys.argv[1:7]
t = pathlib.Path(src).read_text(encoding="utf-8")
for key, val in (("Patch-SHA256", psha), ("Derivator-SHA256", asha),
                 ("Derived-From", base), ("Scope-Derived", scope)):
    t, n = re.subn(r"^" + key + r":.*$", lambda _m: key + ": " + val, t, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("linha %s não encontrada no sentinel" % key)
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
grep -q "^Patch-SHA256: $PSHA\$" "$SENT" || die "Patch-SHA256 não gravou"
printf '   Scope-Derived    = %s\n' "$SCOPE"
printf '   Derived-From     = %s (último commit fora de %s)\n' "$BASE_EFF" "$D"
printf '   Patch-SHA256     = %s (%s linhas)\n' "$PSHA" "$(wc -l <"$PATCH" | tr -d ' ')"
printf '   Derivator-SHA256 = %s\n' "$ASHA"
sed -n 's/^claim PASS /   âncora OK /p' "$W/derive.out"
git apply --stat "$PATCH"
printf '   log da derivação: %s\n' "$W/derive.out"

[ "$COMMIT" = "1" ] || exit 0

# ------------------------------------------------------------------ --commit
# um índice que já leva SÓ materiais de $D (um --commit anterior interrompido
# antes do trap, ou um git add à mão) segue: eles são re-adicionados abaixo;
# qualquer caminho FORA de $D no índice recusa, com a rota
PRE=$(git diff --cached --name-only) || die "git diff --cached falhou"
PRE_BAD=$(printf '%s\n' "$PRE" | awk -v d="$D/" 'NF && index($0, d)!=1')
[ -z "$PRE_BAD" ] || die "há caminho FORA de $D no índice — o commit dos materiais leva SÓ o que é de $D:
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
  exit 0
fi
BAD=$(printf '%s\n' "$STAGED" | awk -v d="$D/" 'index($0, d)!=1')
[ -z "$BAD" ] || die "o índice ganhou caminho fora de $D: $BAD"
# gates de CORPUS sobre a árvore JÁ stageada (CLAUDE.md §4), antes do commit;
# uma reprovação (ou um sinal) desfaz o índice pelo trap
python3 .claude/scripts/check_contamination.py >"$W/contam.out" 2>&1 \
  || { tail -n 20 "$W/contam.out" >&2; die "contamination reprovou (log: $W/contam.out)"; }
python3 .claude/scripts/check-ceremony-script.py >"$W/lint.out" 2>&1 \
  || { tail -n 20 "$W/lint.out" >&2; die "ceremony-lint reprovou (log: $W/lint.out)"; }
{
  printf 'plan(%s): relmeta-142 — patch e sentinel derivados do HEAD pós-lands\n\n' "$PLAN"
  printf 'RELMETA142.patch e as quatro linhas derivadas do relmeta142-approved.md\n'
  printf '(Patch-SHA256, Derivator-SHA256, Derived-From, Scope-Derived), gerados por\n'
  printf 'derive-relmeta142.sh num clone descartável sobre a base %s.\n' "$(git rev-parse --short "$BASE_EFF")"
  printf 'Escopo derivado de git log %s..HEAD: %s.\n\n' "$BASE_TAG" "$SCOPE"
  printf 'Só caminhos de %s entram neste commit; a assinatura e o land\n' "$D"
  printf 'são o OWNER-RELMETA142-SIGN.sh, que re-deriva do HEAD e recusa um patch velho.\n\n'
  printf 'Co-Authored-By: %s\n' "$COAUTHOR"
} >"$W/commit-msg.txt" || die "não consegui escrever a mensagem do commit"
git commit -q -F "$W/commit-msg.txt" || die "git commit falhou"
STAGING=0
printf '\nmateriais commitados em %s:\n' "$(git rev-parse --short HEAD)"
printf '%s\n' "$STAGED" | sed 's/^/   /'
printf '\nPróximo: git push origin main  — depois  bash %s/OWNER-RELMETA142-SIGN.sh --dry-run  e sem --dry-run\n' "$D"
