#!/bin/bash
# CEREMONY-LINT: handwritten-exception: molde `s349-ceremony-relmeta2`, adaptado
# para cerimonia-por-PATCH; sem gerador para este shape.
#
# finalize-rc1cure.sh — prova, na arvore VIVA, que o material congelado pelo
# `bind-patch.sh` ainda descreve esta arvore, e que a aplicacao POR ITEM que o
# LAND vai fazer produz exatamente o patch congelado.
#
#   bash <ceremony>/finalize-rc1cure.sh
#
# POR QUE ESTE PASSO EXISTE NUMA CERIMONIA POR PATCH. O LAND nao aplica o
# patch de uma vez: ele aplica `git apply --include=<path>` por item do escopo,
# para que um path fora do escopo nao possa entrar de carona. Essa decomposicao
# PRECISA produzir a mesma arvore que o patch inteiro — senao o que o Owner
# assina e o que o LAND escreve sao coisas diferentes. Aqui isso e MEDIDO:
# aplica por item, compara `git diff` contra o patch congelado byte a byte, e
# restaura.
#
# Curas do corpus S348 aplicadas: rc de todo produtor conferido (CM-04), zero
# `| head` sob pipefail (CM-05), escrita atomica (CM-17), UMA receita de digest
# (CM-16), e — a que a S348 pagou caro — restauracao por SNAPSHOT em bytes num
# trap, porque `git checkout --` e recusado sobre caminho canonico e o
# `|| true` engolia a recusa, deixando a arvore suja (CM-13).
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || true )"
[ -n "$ROOT" ] || ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

CDIR="$SCRIPT_DIR"
PATCH="$CDIR/RC1CURE.patch"
SCOPE="$CDIR/SCOPE.txt"
BASELINE="$CDIR/EXPECTED-BASELINE.txt"
MATERIALS="$CDIR/MATERIALS.sha256"
RESTORE="$CDIR/_restore_targets.py"

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }

say "0/5 material do bind presente e fechado"
for f in "$PATCH" "$SCOPE" "$BASELINE" "$MATERIALS" "$RESTORE"; do
  [ -f "$f" ] || die "material ausente: $f (rode o bind-patch.sh primeiro)"
  [ -L "$f" ] && die "material e symlink: $f"
done
( cd "$CDIR" && shasum -a 256 -c MATERIALS.sha256 --status ) \
  || die "MATERIALS.sha256 nao confere — material mudou depois do bind"

SCOPE_PATHS="$(awk '/^  - /{print $2}' "$SCOPE")"
[ -n "$SCOPE_PATHS" ] || die "escopo vazio"
SCOPE_N="$(printf '%s\n' "$SCOPE_PATHS" | grep -c .)"

say "1/5 arvore, HEAD e baseline"
_st="$(mktemp)"
if ! git status --porcelain=v1 --untracked-files=all > "$_st"; then
  rm -f "$_st"; die "git status falhou — um gate que nao conseguiu PERGUNTAR nao responde 'limpo'"
fi
_bad=""
while IFS= read -r _l; do
  [ -n "$_l" ] || continue
  _p="${_l#???}"
  case "$_l" in
    '??'*) : ;;                       # untracked e tolerado; o commit e literal
    *) _bad="$_bad
   $_l (modificacao RASTREADA)" ;;
  esac
done < "$_st"
rm -f "$_st"
[ -z "$_bad" ] || die "arvore com modificacao rastreada:$_bad"

HEADSHA="$(git rev-parse HEAD)" || die "git rev-parse HEAD falhou"
# BASE-HEAD e fato REGISTRADO, nao invariante enforcado: entre o bind e a
# assinatura o CEO landa os materiais como arquivos livres, e esse commit move
# o HEAD sem tocar alvo nenhum. Exigir igualdade aqui bloquearia o caminho
# documentado. Os invariantes de verdade sao o `git apply --check` e os hashes
# PRE por alvo, ambos logo abaixo — se um commit intermediario tocasse um
# alvo, e o hash que pega.
_bh="$(awk '$1=="BASE-HEAD"{print $2}' "$BASELINE")"
[ -n "$_bh" ] || die "EXPECTED-BASELINE.txt sem BASE-HEAD"
if [ "$_bh" != "$HEADSHA" ]; then
  printf '   (HEAD andou desde o bind: %s -> %s; os hashes PRE decidem)\n' \
    "${_bh:0:12}" "${HEADSHA:0:12}"
fi
git apply --check "$PATCH" \
  || die "o patch congelado NAO aplica mais nesta arvore — re-rode o bind-patch.sh"
_bp="$(awk '$1=="PATCH-SHA256"{print $2}' "$BASELINE")"
[ "$_bp" = "$(shasum -a 256 "$PATCH" | awk '{print $1}')" ] \
  || die "PATCH-SHA256 do baseline != sha do patch congelado"
_bn="$(awk '$1=="SCOPE-COUNT"{print $2}' "$BASELINE")"
[ "$_bn" = "$SCOPE_N" ] || die "SCOPE-COUNT do baseline ($_bn) != escopo atual ($SCOPE_N)"
_today="$(awk '$1=="TODAY"{print $2}' "$BASELINE")"
case "$_today" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) : ;;
  *) die "EXPECTED-BASELINE.txt sem linha TODAY YYYY-MM-DD" ;;
esac
while IFS= read -r _bl; do
  case "$_bl" in "PRE "*) : ;; *) continue ;; esac
  _p="${_bl##* }"; _h="$(printf '%s' "$_bl" | awk '{print $2}')"
  _live="$(git hash-object -- "$_p")" || die "hash-object falhou: $_p"
  [ "$_live" = "$_h" ] || die "alvo ja modificado desde o bind: $_p"
done < "$BASELINE"
printf '   OK: HEAD %s, %s paths, TODAY %s, baseline reproduz a arvore\n' \
  "${HEADSHA:0:12}" "$SCOPE_N" "$_today"

# --- snapshot em bytes + trap (CM-13) --------------------------------------
SNAP="$(mktemp -d)"
RESTORE_ARMED=0
_restore_targets() {
  [ "$RESTORE_ARMED" -eq 1 ] || return 0
  python3 "$RESTORE" "$SNAP" "$ROOT" >&2 || true
  RESTORE_ARMED=0
}
_cleanup() { _restore_targets; rm -rf "$SNAP"; }
trap _cleanup EXIT INT TERM

say "2/5 snapshot em bytes dos alvos"
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  cp "$_p" "$SNAP/$(printf '%s' "$_p" | tr '/' '%')" || die "snapshot de $_p falhou"
done <<SP
$SCOPE_PATHS
SP

say "3/5 aplicacao POR ITEM == patch inteiro (a decomposicao que o LAND usa)"
RESTORE_ARMED=1
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  git apply --include="$_p" "$PATCH" \
    || die "git apply --include=$_p falhou — a decomposicao por item nao aplica"
done <<SP2
$SCOPE_PATHS
SP2
_regen="$(mktemp)"
# shellcheck disable=SC2086
git diff -- $SCOPE_PATHS > "$_regen" || { rm -f "$_regen"; die "git diff dos alvos falhou"; }
if ! cmp -s "$_regen" "$PATCH"; then
  _d="$(diff -u "$PATCH" "$_regen" | sed -n '1,40p')"
  rm -f "$_regen"
  die "a aplicacao POR ITEM nao reproduz o patch congelado:
$_d"
fi
rm -f "$_regen"
printf '   OK: %s aplicacoes --include reproduzem RC1CURE.patch byte a byte\n' "$SCOPE_N"

say "4/5 restaurar a arvore (pelo snapshot, nunca pelo git)"
_restore_targets
_st2="$(mktemp)"
if ! git status --porcelain=v1 > "$_st2"; then rm -f "$_st2"; die "git status falhou pos-restauracao"; fi
_left="$(grep -v '^??' "$_st2" || true)"
rm -f "$_st2"
[ -z "$_left" ] || die "restauracao incompleta:
$_left"
printf '   OK: arvore de volta ao estado PRE-edicao\n'

say "5/5 material verificado"
printf '\nFINALIZE VERDE\n'
printf '  patch      %s  (sha256 %s)\n' "$PATCH" "$_bp"
printf '  escopo     %s  (%s paths)\n' "$SCOPE" "$SCOPE_N"
printf '  baseline   %s  (TODAY %s)\n' "$BASELINE" "$_today"
printf '  materials  %s  (%s membros)\n' "$MATERIALS" "$(grep -c . "$MATERIALS")"
printf '\nProximo: bash <plan-dir>/OWNER-RC1-CURE-SIGN.sh\n'
