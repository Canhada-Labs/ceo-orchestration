#!/bin/bash
# CEREMONY-LINT: handwritten-exception: gerador de material da cerimonia rel-meta; escrito contra o corpus
# PLAN-188/ceremony-defect-corpus-S348.md, sem molde de origem.
# finalize-relmeta.sh — o UNICO escritor do material da cerimonia rel-meta.
#
#   bash .claude/plans/PLAN-169/s349-ceremony-relmeta/finalize-relmeta.sh
#
# Deriva, nesta ordem, a partir da arvore VIVA e limpa:
#   RELMETA.patch          o diff das 2 edicoes (apply-relmeta-edits.py)
#   SCOPE.txt              o bloco Scope: do sentinel, de `git apply --numstat`
#   EXPECTED-BASELINE.txt  os hashes PRE-edicao dos 2 alvos + o sha do patch
#   MATERIALS.sha256       UMA receita de digest, ordenada, para SIGN e LAND
# e REVERTE a arvore. Nenhum outro script escreve estes arquivos (invariante
# 4 do PLAN-188: `EXPECTED-BASELINE` consumido sem regeneracao foi a classe
# CM-11 do corpus S348).
#
# Curas do corpus aplicadas aqui: rc de TODO produtor conferido (CM-04),
# zero `| head` sob pipefail (CM-05), escrita atomica por temporario +
# rename (CM-17), digest com ordem declarada num lugar so (CM-16).
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

NS=".claude/plans/PLAN-169"
CDIR="$NS/s349-ceremony-relmeta"
APPLY="$CDIR/apply-relmeta-edits.py"
PATCH="$CDIR/RELMETA.patch"
SCOPE="$CDIR/SCOPE.txt"
BASELINE="$CDIR/EXPECTED-BASELINE.txt"
MATERIALS="$CDIR/MATERIALS.sha256"

# DOIS alvos. O CHANGELOG NAO entra: a secao [1.4.0] foi landada pelo
# pacote de docs, e o aplicador a CONFERE em vez de reescreve-la.
TARGETS=(
  ".claude/scripts/local/release.sh"
  ".claude/governance/gate-scripts-manifest.txt"
)

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }

# --- escrita atomica (CM-17) ------------------------------------------------
write_atomic() {
  # $1 = destino, stdin = conteudo. Recusa symlink; temporario no MESMO dir.
  _wa_dst="$1"
  [ -L "$_wa_dst" ] && die "destino e symlink: $_wa_dst"
  _wa_tmp="$(dirname "$_wa_dst")/.finalize.$$.$(basename "$_wa_dst").tmp"
  cat > "$_wa_tmp" || die "escrita do temporario falhou: $_wa_dst"
  mv -f "$_wa_tmp" "$_wa_dst" || die "rename atomico falhou: $_wa_dst"
}

# --- arvore limpa, com rc CONFERIDO (CM-04) --------------------------------
assert_clean_tree() {
  _act_f="$(mktemp)"
  if ! git status --porcelain --untracked-files=all > "$_act_f"; then
    rm -f "$_act_f"
    die "git status falhou — um gate que nao conseguiu PERGUNTAR nao responde 'limpo'"
  fi
  # Duas regras DISTINTAS, nunca uma so:
  #   - modificacao RASTREADA em qualquer lugar aborta (o baseline PRE-edicao
  #     tem de descrever exatamente o HEAD);
  #   - arquivo UNTRACKED so e tolerado dentro do namespace do plano
  #     ($NS), porque na primeira execucao o kit inteiro — cerimonia,
  #     runner, manifests, harness — ainda nao landou. Fora dele, nada.
  _act_bad=""
  while IFS= read -r _l; do
    [ -n "$_l" ] || continue
    _p="${_l#???}"
    case "$_l" in
      '??'*)
        case "$_p" in
          "$NS"/*) continue ;;
          *) _act_bad="$_act_bad
   $_p (untracked fora do namespace da cerimonia)" ;;
        esac ;;
      *) _act_bad="$_act_bad
   $_p (modificacao RASTREADA)" ;;
    esac
  done < "$_act_f"
  rm -f "$_act_f"
  [ -z "$_act_bad" ] || die "arvore suja fora de $CDIR:$_act_bad"
}

say "0/5 pre-condicoes"
[ -f "$APPLY" ] || die "material ausente: $APPLY"
for t in "${TARGETS[@]}"; do
  [ -f "$t" ] || die "alvo ausente: $t"
  [ -L "$t" ] && die "alvo e symlink: $t"
done
assert_clean_tree
HEADSHA="$(git rev-parse HEAD)" || die "git rev-parse HEAD falhou"
printf '   HEAD = %s\n' "$HEADSHA"

say "1/5 baseline PRE-edicao (hashes dos 2 alvos)"
BL_TMP="$(mktemp)"
{
  printf 'BASE-HEAD %s\n' "$HEADSHA"
  for t in "${TARGETS[@]}"; do
    _h="$(git hash-object -- "$t")" || die "hash-object falhou: $t"
    printf 'PRE %s %s\n' "$_h" "$t"
  done
} > "$BL_TMP" || die "montagem do baseline falhou"

say "2/5 aplicar as 2 edicoes derivadas (o CHANGELOG e so conferido)"
python3 "$APPLY" --repo "$ROOT" || die "apply-relmeta-edits.py rc!=0"

say "3/5 derivar o patch e o escopo"
PATCH_TMP="$(mktemp)"
if ! git diff -- "${TARGETS[@]}" > "$PATCH_TMP"; then
  rm -f "$PATCH_TMP" "$BL_TMP"
  git checkout -- "${TARGETS[@]}" || true
  die "git diff dos alvos falhou"
fi
[ -s "$PATCH_TMP" ] || { git checkout -- "${TARGETS[@]}"; die "patch VAZIO — as edicoes nao mudaram nada"; }
# Escopo DERIVADO do proprio patch (invariante 5: nunca digitado).
SCOPE_TMP="$(mktemp)"
if ! git apply --numstat < "$PATCH_TMP" > "$SCOPE_TMP".raw 2>/dev/null; then
  # `git apply --numstat` nao valida aplicabilidade; um rc!=0 aqui e patch
  # malformado, nunca "sem mudancas".
  git checkout -- "${TARGETS[@]}" || true
  die "git apply --numstat recusou o patch derivado"
fi
{
  printf 'Scope:\n'
  awk '{print "  - " $3}' "$SCOPE_TMP".raw | sort
} > "$SCOPE_TMP" || die "montagem do escopo falhou"
_scope_n="$(grep -c '^  - ' "$SCOPE_TMP")" || _scope_n=0
[ "$_scope_n" = "2" ] || { git checkout -- "${TARGETS[@]}"; die "escopo com $_scope_n paths (esperado 2)"; }

say "4/5 reverter a arvore"
git checkout -- "${TARGETS[@]}" || die "revert dos alvos falhou"
assert_clean_tree

say "5/5 publicar o material (atomico) + digest unico"
write_atomic "$PATCH" < "$PATCH_TMP"
write_atomic "$SCOPE" < "$SCOPE_TMP"
PATCH_SHA="$(shasum -a 256 "$PATCH" | awk '{print $1}')" || die "shasum do patch falhou"
{
  cat "$BL_TMP"
  printf 'PATCH-SHA256 %s\n' "$PATCH_SHA"
  printf 'SCOPE-COUNT %s\n' "$_scope_n"
} | write_atomic "$BASELINE"
rm -f "$PATCH_TMP" "$SCOPE_TMP" "$SCOPE_TMP".raw "$BL_TMP"

# UMA receita de digest (CM-16): membros em ordem LEXICOGRAFICA do basename,
# hash sobre as linhas "<sha>  <basename>". SIGN, LAND e harness chamam esta
# mesma funcao lendo ESTE arquivo — nenhum deles recomputa a lista.
( cd "$CDIR" && shasum -a 256 \
    EXPECTED-BASELINE.txt RELMETA.patch SCOPE.txt apply-relmeta-edits.py \
    finalize-relmeta.sh > .MATERIALS.tmp ) \
  || die "geracao do MATERIALS.sha256 falhou"
mv -f "$CDIR/.MATERIALS.tmp" "$MATERIALS" || die "rename do MATERIALS falhou"
( cd "$CDIR" && shasum -a 256 -c MATERIALS.sha256 --status ) \
  || die "MATERIALS.sha256 nao verifica logo apos ser escrito"

printf '\nMATERIAL PRONTO\n'
printf '  patch      %s  (sha256 %s)\n' "$PATCH" "$PATCH_SHA"
printf '  escopo     %s  (%s paths)\n' "$SCOPE" "$_scope_n"
printf '  baseline   %s\n' "$BASELINE"
printf '  materials  %s  (%s membros)\n' "$MATERIALS" "$(grep -c . "$MATERIALS")"
printf '\nProximo: bash .claude/plans/PLAN-169/OWNER-RC1-META-SIGN.sh\n'
