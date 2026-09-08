#!/bin/bash
# CEREMONY-LINT: handwritten-exception: molde `s349-ceremony-relmeta2`, adaptado
# de cerimonia-por-DERIVADOR para cerimonia-por-PATCH; sem gerador para este shape.
#
# bind-patch.sh — CONGELA o pack `rc1-cure` como material de cerimonia.
#
#   bash <ceremony>/bind-patch.sh <pack-dir> [--today YYYY-MM-DD] [--patch <f>]
#
# A rel-meta-2 derivava o patch de um script (`HEAD + script == patch`). Aqui o
# patch e DADO pelo agente que construiu as curas, entao o que precisa ser
# provado muda: nao «o derivador reproduz», e sim **«o patch aplica em HEAD e
# toca EXATAMENTE o escopo assinado»**. Este script produz o material que
# sustenta essa prova, e nada mais:
#
#   RC1CURE2.patch          copia CONGELADA do rc1-cure.patch do pack
#   SCOPE.txt              bloco `Scope:` do sentinel, DERIVADO do patch por
#                          `git apply --numstat`: TODOS os paths tocados,
#                          canonicos e livres. O SCOPE.txt do PACK declara o
#                          subconjunto CANONICO, e e cruzado com a saida do
#                          oraculo nos dois sentidos — divergencia aborta
#   EXPECTED-BASELINE.txt  BASE-HEAD, os hashes PRE-edicao de cada alvo, o
#                          sha256 do patch e o TODAY PINADO
#   payload/PAYLOAD.sha256 vazio por desenho aqui (ver NOTA), mantido para o
#                          staging derivado do LAND ter uma fonte unica
#   MATERIALS.sha256       digest dos membros, UMA receita
#
# NOTA sobre payload: a rel-meta-2 carregava a suite derivada como payload
# porque o conteudo novo era prosa/codigo revisado que o derivador nao podia
# gerar. Aqui TODO o conteudo novo esta no proprio patch, entao o payload
# nasce vazio — e o manifesto existe mesmo assim, para o LAND continuar
# derivando a lista de staging de uma fonte so em vez de enumerar.
#
# TODAY e PINADO aqui (licao da S348: o `finalize` escolhia uma data e o SIGN
# re-derivava `date -u`; na virada do dia em UTC os dois divergiam e o V1 do
# LAND recusava um patch que estava certo).
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || true )"
[ -n "$ROOT" ] || ROOT="$(git rev-parse --show-toplevel)"

PACK="${1:-}"
shift || true
TODAY=""
PATCH_ARG=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --today) shift; TODAY="${1:-}" ;;
    --patch) shift; PATCH_ARG="${1:-}" ;;
    *) printf 'uso: bind-patch.sh <pack-dir> [--today YYYY-MM-DD] [--patch <arquivo>]\n' >&2; exit 2 ;;
  esac
  shift
done

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }

[ -n "$PACK" ] || die "uso: bind-patch.sh <pack-dir> [--today YYYY-MM-DD]"
[ -d "$PACK" ] || die "pack inexistente: $PACK"
# O NOME do patch e DERIVADO do pack, nunca adivinhado: o pack 1 entregou
# `rc1-cure.patch` e o pack 2 `rc1-cure-2.patch`. Codificar um nome so adia o
# problema para o pack seguinte. Zero ou mais de um candidato e recusa
# nomeada — nunca uma escolha silenciosa.
if [ -n "$PATCH_ARG" ]; then
  SRC_PATCH="$PATCH_ARG"
else
  _cands="$(mktemp)"
  find "$PACK" -maxdepth 1 -type f -name '*.patch' > "$_cands" \
    || { rm -f "$_cands"; die "busca por *.patch no pack falhou"; }
  _nc="$(grep -c . "$_cands")"
  case "$_nc" in
    1) SRC_PATCH="$(cat "$_cands")" ;;
    0) rm -f "$_cands"; die "nenhum *.patch em $PACK — o pack ainda nao congelou" ;;
    *) printf '\ncandidatos:\n' >&2; sed 's/^/   /' "$_cands" >&2; rm -f "$_cands"
       die "$_nc arquivos *.patch em $PACK — passe --patch <arquivo>" ;;
  esac
  rm -f "$_cands"
fi
SRC_SCOPE="$PACK/SCOPE.txt"
[ -f "$SRC_PATCH" ] || die "$SRC_PATCH ausente — o pack ainda nao congelou"
printf '   patch do pack: %s\n' "$SRC_PATCH"
[ -f "$SRC_SCOPE" ] || die "$SRC_SCOPE ausente — o pack ainda nao congelou"
[ -L "$SRC_PATCH" ] && die "rc1-cure.patch e symlink"
[ -L "$SRC_SCOPE" ] && die "SCOPE.txt do pack e symlink"

TODAY="${TODAY:-$(date -u +%Y-%m-%d)}"
case "$TODAY" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) : ;;
  *) die "--today deve ser YYYY-MM-DD (recebido '$TODAY')" ;;
esac

CDIR="$SCRIPT_DIR"
PATCH="$CDIR/RC1CURE2.patch"
SCOPE="$CDIR/SCOPE.txt"
BASELINE="$CDIR/EXPECTED-BASELINE.txt"
MATERIALS="$CDIR/MATERIALS.sha256"
PAYDIR="$CDIR/payload"
PAYMAN="$PAYDIR/PAYLOAD.sha256"

cd "$ROOT"

say "0/5 arvore e HEAD"
_st="$(mktemp)"
if ! git status --porcelain=v1 --untracked-files=all > "$_st"; then
  rm -f "$_st"; die "git status falhou — nao vou tratar como arvore limpa"
fi
_dirty=""
while IFS= read -r _l; do
  [ -n "$_l" ] || continue
  case "$_l" in '??'*) continue ;; esac
  _dirty="$_dirty
   $_l"
done < "$_st"
rm -f "$_st"
[ -z "$_dirty" ] || die "modificacao RASTREADA na arvore — o baseline descreveria outra coisa:$_dirty"
HEADSHA="$(git rev-parse HEAD)" || die "git rev-parse HEAD falhou"
printf '   HEAD = %s\n   TODAY = %s\n' "$HEADSHA" "$TODAY"

say "1/5 congelar o patch"
mkdir -p "$PAYDIR" || die "mkdir do payload falhou"
cp "$SRC_PATCH" "$PATCH.tmp" || die "copia do patch falhou"
mv -f "$PATCH.tmp" "$PATCH" || die "rename do patch falhou"
PATCH_SHA="$(shasum -a 256 "$PATCH" | awk '{print $1}')" || die "shasum do patch falhou"
printf '   RC1CURE2.patch sha256 %s\n' "$PATCH_SHA"

say "2/5 o patch APLICA em HEAD, e toca exatamente o escopo"
git apply --check "$PATCH" || die "git apply --check recusou o patch contra HEAD $HEADSHA"
_ns="$(mktemp)"
git apply --numstat < "$PATCH" > "$_ns" || { rm -f "$_ns"; die "git apply --numstat recusou o patch"; }
{ printf 'Scope:\n'; awk '{print "  - " $3}' "$_ns" | sort; } > "$SCOPE.tmp" \
  || { rm -f "$_ns"; die "montagem do escopo falhou"; }
rm -f "$_ns"
mv -f "$SCOPE.tmp" "$SCOPE" || die "rename do escopo falhou"
_n="$(grep -c '^  - ' "$SCOPE")" || _n=0
[ "$_n" -ge 1 ] || die "escopo vazio — o patch nao toca arquivo nenhum"

printf '   %s path(s) tocados pelo patch\n' "$_n"

say "3/5 quais desses paths sao CANONICOS"
_orc="$(mktemp)"
awk '/^  - /{print $2}' "$SCOPE" \
  | python3 "$ROOT/.claude/hooks/check_canonical_edit.py" --is-canonical - > "$_orc" \
  || { rm -f "$_orc"; die "oraculo --is-canonical rc!=0 — trate como falha, nunca como 'livre'"; }
sed 's/^/   /' "$_orc"
_canon_list="$(mktemp)"
awk -F'\t' '$2=="1"{print $1}' "$_orc" | sort -u > "$_canon_list"
_canon="$(grep -c . "$_canon_list" || true)"
rm -f "$_orc"
printf '   %s canonico(s) de %s no escopo\n' "$_canon" "$_n"

# CRUZAMENTO com o SCOPE.txt do pack, que declara o subconjunto CANONICO.
# Nos DOIS sentidos: um canonico que o autor esqueceu de declarar e um
# declarado que nao e canonico (ou que o patch nao toca) abortam igual.
# O `Scope:` ASSINADO, esse, cobre os $_n paths — canonicos e livres — porque
# e ele que autoriza o staging literal do LAND; omitir os livres faria a cura
# chegar ao main pela metade.
_declared="$(mktemp)"
grep -oE '[^[:space:]]+' "$SRC_SCOPE" | grep -vE '^(Scope:|-)$' | sed 's|^- ||' | sort -u > "$_declared"
if ! cmp -s "$_declared" "$_canon_list"; then
  printf '\nSCOPE.txt do pack != conjunto CANONICO que o patch toca:\n' >&2
  diff -u "$_declared" "$_canon_list" >&2 || true
  rm -f "$_declared" "$_canon_list"
  die "declaracao de canonicos divergente — nao congelo material sobre isso"
fi
rm -f "$_declared" "$_canon_list"
printf '   OK: os %s canonicos batem o SCOPE.txt declarado pelo pack\n' "$_canon"

# Regra (5) do CEO: o manifesto ADR-192 so entra se algum MEMBRO for tocado.
say "3b/5 algum membro do manifesto ADR-192 no escopo?"
GSM=".claude/governance/gate-scripts-manifest.txt"
_hits=""
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  if awk -v f="$_p" '$2==f{found=1} END{exit !found}' "$GSM" 2>/dev/null; then
    _hits="$_hits $_p"
  fi
done <<SCOPEPATHS
$(awk '/^  - /{print $2}' "$SCOPE")
SCOPEPATHS
if [ -n "$_hits" ]; then
  printf '   MEMBRO(S) tocado(s):%s\n' "$_hits"
  if awk '/^  - /{print $2}' "$SCOPE" | grep -qx "$GSM"; then
    printf '   OK: o manifesto esta no escopo, como tem de estar\n'
  else
    die "o patch toca membro(s) do manifesto ADR-192 (%s) mas NAO re-pina o sha em $GSM — o gate 'Gate-scripts integrity' do release.yml reprovaria" "$_hits"
  fi
else
  printf '   nenhum membro tocado — o manifesto NAO entra no escopo\n'
fi

say "4/5 baseline PRE-edicao + TODAY pinado"
{
  printf 'BASE-HEAD %s\n' "$HEADSHA"
  while IFS= read -r _p; do
    [ -n "$_p" ] || continue
    [ -e "$_p" ] || die "alvo do escopo nao existe em HEAD: $_p"
    [ -L "$_p" ] && die "alvo do escopo e symlink: $_p"
    _h="$(git hash-object -- "$_p")" || die "hash-object falhou: $_p"
    printf 'PRE %s %s\n' "$_h" "$_p"
  done <<SCOPEPATHS2
$(awk '/^  - /{print $2}' "$SCOPE")
SCOPEPATHS2
  printf 'PATCH-SHA256 %s\n' "$PATCH_SHA"
  printf 'SCOPE-COUNT %s\n' "$_n"
  printf 'CANONICAL-COUNT %s\n' "$_canon"
  printf 'TODAY %s\n' "$TODAY"
} > "$BASELINE.tmp" || die "montagem do baseline falhou"
mv -f "$BASELINE.tmp" "$BASELINE" || die "rename do baseline falhou"

say "5/5 manifestos (UMA receita)"
# Payload vazio por desenho: todo o conteudo novo vem do patch. O manifesto
# existe para o LAND derivar a lista de staging de uma fonte so.
: > "$PAYMAN.tmp" || die "escrita do PAYLOAD.sha256 falhou"
mv -f "$PAYMAN.tmp" "$PAYMAN" || die "rename do PAYLOAD.sha256 falhou"
( cd "$CDIR" && shasum -a 256 \
    EXPECTED-BASELINE.txt RC1CURE2.patch SCOPE.txt _restore_targets.py \
    bind-patch.sh finalize-rc1cure2.sh > .MATERIALS.tmp ) \
  || die "geracao do MATERIALS.sha256 falhou"
mv -f "$CDIR/.MATERIALS.tmp" "$MATERIALS" || die "rename do MATERIALS falhou"
( cd "$CDIR" && shasum -a 256 -c MATERIALS.sha256 --status ) \
  || die "MATERIALS.sha256 nao verifica logo apos ser escrito"

printf '\nBIND PRONTO\n'
printf '  patch      %s  (sha256 %s)\n' "$PATCH" "$PATCH_SHA"
printf '  escopo     %s  (%s paths, %s canonico(s))\n' "$SCOPE" "$_n" "$_canon"
printf '  baseline   %s  (BASE-HEAD %s, TODAY %s)\n' "$BASELINE" "$HEADSHA" "$TODAY"
printf '  materials  %s  (%s membros)\n' "$MATERIALS" "$(grep -c . "$MATERIALS")"
printf '\nProximo: bash <ceremony>/finalize-rc1cure2.sh\n'
