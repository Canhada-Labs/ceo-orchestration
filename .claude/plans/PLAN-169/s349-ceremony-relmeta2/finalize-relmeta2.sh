#!/bin/bash
# CEREMONY-LINT: handwritten-exception: gerador de material da cerimonia rel-meta; escrito contra o corpus
# PLAN-188/ceremony-defect-corpus-S348.md, sem molde de origem.
# finalize-relmeta2.sh — o UNICO escritor do material da cerimonia rel-meta.
#
#   bash .claude/plans/PLAN-169/s349-ceremony-relmeta2/finalize-relmeta2.sh
#
# Deriva, nesta ordem, a partir da arvore VIVA e limpa:
#   RELMETA2.patch          o diff da cerimonia inteira
#   SCOPE.txt              o bloco Scope: do sentinel, de `git apply --numstat`
#   EXPECTED-BASELINE.txt  os hashes PRE-edicao dos alvos + o sha do patch
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
CDIR="$NS/s349-ceremony-relmeta2"
APPLY="$CDIR/apply-relmeta2-edits.py"
PATCH="$CDIR/RELMETA2.patch"
SCOPE="$CDIR/SCOPE.txt"
BASELINE="$CDIR/EXPECTED-BASELINE.txt"
MATERIALS="$CDIR/MATERIALS.sha256"

# Alvos da rel-meta-2. Os sitios de versao NAO sao listados a mao: eles saem
# de `_release_bump_sites.py print-sites`, o mesmo modulo que os ESCREVE, mais
# os manifestos de plugin (do gerador) e os dois paths da cerimonia. Uma lista
# digitada aqui seria um segundo censo envelhecendo ao lado do primeiro.
_sites="$(python3 .claude/scripts/local/_release_bump_sites.py print-sites)" \
  || { printf '\nFAIL: print-sites falhou\n' >&2; exit 1; }
TARGETS=()
while IFS= read -r _s; do
  [ -n "$_s" ] || continue
  TARGETS+=("$_s")
done <<SITES
$_sites
SITES
TARGETS+=(".claude-plugin/plugin.json" ".claude-plugin/marketplace.json")
TARGETS+=(".claude/scripts/local/release.sh")
TARGETS+=(".claude/governance/gate-scripts-manifest.txt")
TARGETS+=(".claude/scripts/tests/test_release_bump_sites.py")
TARGETS+=(".claude/adr/README.md")

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

# SNAPSHOT em bytes dos alvos, e um trap que restaura por ESCRITA PYTHON.
# `git checkout --` NAO serve: dois alvos sao canonicos e o interceptor recusa
# o comando, o `|| true` engole a recusa, e a arvore fica suja — foi o defeito
# medido no ensaio do CEO (8 rastreados modificados apos uma recusa).
SNAP="$(mktemp -d)"
RESTORE_ARMED=0
_restore_targets() {
  [ "$RESTORE_ARMED" -eq 1 ] || return 0
  python3 "$CDIR/_restore_targets.py" "$SNAP" "$ROOT" >&2 || true
  RESTORE_ARMED=0
}
_cleanup_snap() { _restore_targets; rm -rf "$SNAP"; }
trap _cleanup_snap EXIT INT TERM

say "1/5 baseline PRE-edicao (hashes dos alvos derivados) + snapshot em bytes"
for t in "${TARGETS[@]}"; do
  cp "$t" "$SNAP/$(printf '%s' "$t" | tr '/' '%')" \
    || die "snapshot de $t falhou"
done
BL_TMP="$(mktemp)"
{
  printf 'BASE-HEAD %s\n' "$HEADSHA"
  for t in "${TARGETS[@]}"; do
    _h="$(git hash-object -- "$t")" || die "hash-object falhou: $t"
    printf 'PRE %s %s\n' "$_h" "$t"
  done
} > "$BL_TMP" || die "montagem do baseline falhou"

say "2/5 aplicar as edicoes (o CHANGELOG e so conferido)"
RESTORE_ARMED=1
# A DATA e material: ela entra nos carimbos que o patch escreve, entao
# quem a escolhe e o finalize, UMA vez, e ela fica gravada no baseline.
# Deixar o SIGN re-derivar `date -u` faz o par divergir na virada do dia
# em UTC — e ai o V1 do LAND regenera um patch diferente e recusa.
CEREMONY_TODAY="${RELMETA2_TODAY:-$(date -u +%Y-%m-%d)}"
python3 "$APPLY" --repo "$ROOT" --today "$CEREMONY_TODAY" \
  || die "apply-relmeta2-edits.py rc!=0"

say "3/5 derivar o patch e o escopo"
PATCH_TMP="$(mktemp)"
if ! git diff -- "${TARGETS[@]}" > "$PATCH_TMP"; then
  rm -f "$PATCH_TMP" "$BL_TMP"
  git checkout -- "${TARGETS[@]}" || true
  die "git diff dos alvos falhou"
fi
[ -s "$PATCH_TMP" ] || { _restore_targets; die "patch VAZIO — as edicoes nao mudaram nada"; }
# Escopo DERIVADO do proprio patch (invariante 5: nunca digitado).
SCOPE_TMP="$(mktemp)"
if ! git apply --numstat < "$PATCH_TMP" > "$SCOPE_TMP".raw 2>/dev/null; then
  # `git apply --numstat` nao valida aplicabilidade; um rc!=0 aqui e patch
  # malformado, nunca "sem mudancas".
  _restore_targets
  die "git apply --numstat recusou o patch derivado"
fi
{
  printf 'Scope:\n'
  awk '{print "  - " $3}' "$SCOPE_TMP".raw | sort
} > "$SCOPE_TMP" || die "montagem do escopo falhou"
_scope_n="$(grep -c '^  - ' "$SCOPE_TMP")" || _scope_n=0
# O escopo tem de ser SUBCONJUNTO dos alvos declarados: um path fora deles
# significa que a edicao escreveu onde nao devia.
while IFS= read -r _sp; do
  case "$_sp" in "  - "*) : ;; *) continue ;; esac
  _sp="${_sp#  - }"
  _hit=0
  for _tg in "${TARGETS[@]}"; do
    [ "$_sp" = "$_tg" ] && { _hit=1; break; }
  done
  [ "$_hit" -eq 1 ] || { _restore_targets; die "escopo tem path FORA dos alvos: $_sp"; }
done < "$SCOPE_TMP"
[ "$_scope_n" -ge 3 ] || { _restore_targets; die "escopo com so $_scope_n paths"; }

say "4/5 reverter a arvore (pelo snapshot, nao pelo git)"
_restore_targets
assert_clean_tree

say "5/5 publicar o material (atomico) + digest unico"
write_atomic "$PATCH" < "$PATCH_TMP"
write_atomic "$SCOPE" < "$SCOPE_TMP"
PATCH_SHA="$(shasum -a 256 "$PATCH" | awk '{print $1}')" || die "shasum do patch falhou"
{
  cat "$BL_TMP"
  printf 'PATCH-SHA256 %s\n' "$PATCH_SHA"
  printf 'TODAY %s\n' "$CEREMONY_TODAY"
  printf 'SCOPE-COUNT %s\n' "$_scope_n"
} | write_atomic "$BASELINE"
rm -f "$PATCH_TMP" "$SCOPE_TMP" "$SCOPE_TMP".raw "$BL_TMP"

# UMA receita de digest (CM-16): membros em ordem LEXICOGRAFICA do basename,
# hash sobre as linhas "<sha>  <basename>". SIGN, LAND e harness chamam esta
# mesma funcao lendo ESTE arquivo — nenhum deles recomputa a lista.
( cd "$CDIR" && shasum -a 256 \
    EXPECTED-BASELINE.txt RELMETA2.patch SCOPE.txt apply-relmeta2-edits.py \
    finalize-relmeta2.sh _restore_targets.py > .MATERIALS.tmp ) \
  || die "geracao do MATERIALS.sha256 falhou"
mv -f "$CDIR/.MATERIALS.tmp" "$MATERIALS" || die "rename do MATERIALS falhou"
( cd "$CDIR" && shasum -a 256 -c MATERIALS.sha256 --status ) \
  || die "MATERIALS.sha256 nao verifica logo apos ser escrito"

printf '\nMATERIAL PRONTO\n'
printf '  patch      %s  (sha256 %s)\n' "$PATCH" "$PATCH_SHA"
printf '  escopo     %s  (%s paths)\n' "$SCOPE" "$_scope_n"
printf '  baseline   %s\n' "$BASELINE"
printf '  materials  %s  (%s membros)\n' "$MATERIALS" "$(grep -c . "$MATERIALS")"
printf '\nProximo: bash .claude/plans/PLAN-169/OWNER-RC1-META2-SIGN.sh\n'
