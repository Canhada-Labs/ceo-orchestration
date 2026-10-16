#!/bin/bash
# CEREMONY-LINT: handwritten-exception: conferências próprias da relmeta-143 (PLAN-194, RM da v1.4.3) que pedem mais de um comando, chamadas por uma linha hard do molde sign-min
# hard-relmeta.sh — chamado pela 2.ª linha `hard` de .claude/plans/PLAN-194/relmeta/sign.tsv (forma 2 do
# molde sign-min: `bash <CAMINHO>.sh`), com cwd na raiz do clone que tem o relmeta.patch aplicado e o HEAD no
# Anchor. Sai rc 0 só se todas as conferências abaixo passarem; em qualquer outro caso sai rc 1. O julgamento é só
# este rc: o resumo de cada passo vai para a saída padrão, que quem chama guarda em log.
#
# Na ordem:
#   0. o sha256 do derivador (apply-relmeta143-edits.py) é o da linha Derivator-SHA256 do sentinel no HEAD, e o
#      sha256 deste arquivo é o da linha Hard-SHA256 (cada linha uma vez, 64 hex): o código que a bateria roda é
#      o que gerou o patch;
#   1. `shasum -a 256 -c` do manifesto ADR-192 sai rc 0 e o número de linhas «: OK» (contado por wc -l) é igual
#      ao de linhas não vazias do manifesto (asserção de conjunto);
#   2. exatamente uma linha do manifesto termina em «  .claude/scripts/local/release.sh», e o sha256 dela é o do
#      arquivo em disco;
#   3. a linha `TARGET_BASE="1.4.3"` aparece exatamente uma vez no driver, e nenhuma linha `TARGET_BASE="1.4.2"`;
#   4. `bash .claude/scripts/local/release.sh --help` sai rc 0 e a primeira linha é
#      «release.sh — operator release driver (target base version: 1.4.3)» (o --help imprime e sai, sem
#      efeito colateral);
#   5. o commit da v1.4.2 (b55084da) é ancestral do HEAD.
# Só leitura: nada é escrito no clone. O git roda com GIT_OPTIONAL_LOCKS=0, e PYTHONDONTWRITEBYTECODE=1 vale
# para os descendentes que herdam o ambiente.
set -u
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0

SENT=.claude/plans/PLAN-194/relmeta-approved.md
APPLY=.claude/plans/PLAN-194/relmeta/apply-relmeta143-edits.py
SELF=.claude/plans/PLAN-194/relmeta/hard-relmeta.sh
MAN=.claude/governance/gate-scripts-manifest.txt
REL=.claude/scripts/local/release.sh
V142=b55084da6dd8e4a05fc9893b2690df8aebcfd0ca
HELP_LINE="release.sh — operator release driver (target base version: 1.4.3)"

fail() { printf 'FALHOU: %s\n' "$1"; exit 1; }
ok() { printf 'ok: %s\n' "$1"; }
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }

for f in "$SENT" "$APPLY" "$SELF" "$MAN" "$REL"; do
  [ -f "$f" ] && [ ! -L "$f" ] || fail "o diretório atual não é a raiz do clone, ou $f falta"
done

# 0. o código que a bateria roda é o que gerou o patch
SENT_TXT=$(git cat-file blob "HEAD:$SENT" </dev/null) || fail "git cat-file do sentinel no HEAD"
pinned() {  # pinned <campo> — o valor de uma linha «<campo>: <64 hex>» única do sentinel do HEAD
  local n v
  n=$(printf '%s\n' "$SENT_TXT" | grep -c "^$1: ")
  [ "$n" = "1" ] || return 1
  v=$(printf '%s\n' "$SENT_TXT" | sed -n "s/^$1: \\([0-9a-f]\\{64\\}\\)\$/\\1/p")
  [ -n "$v" ] || return 1
  printf '%s' "$v"
}
DSHA=$(pinned Derivator-SHA256) || fail "o sentinel do HEAD não tem uma linha Derivator-SHA256 única com 64 hex"
HSHA=$(pinned Hard-SHA256) || fail "o sentinel do HEAD não tem uma linha Hard-SHA256 única com 64 hex"
[ "$(sha256f "$APPLY")" = "$DSHA" ] || fail "o sha256 de $APPLY difere do Derivator-SHA256 do sentinel"
[ "$(sha256f "$SELF")" = "$HSHA" ] || fail "o sha256 de $SELF difere do Hard-SHA256 do sentinel"
ok "derivador e este arquivo com os sha256 pinados no sentinel do HEAD"

# 1. o manifesto inteiro confere, linha a linha
OUT=$(shasum -a 256 -c "$MAN" </dev/null 2>&1) || fail "shasum -c do manifesto saiu rc diferente de 0: $OUT"
N_OK=$(printf '%s\n' "$OUT" | grep ': OK$' | wc -l | tr -d ' ')
N_LIN=$(grep . "$MAN" | wc -l | tr -d ' ')
[ "$N_OK" = "$N_LIN" ] && [ "$N_LIN" -gt 0 ] || fail "manifesto: $N_OK linha(s) OK para $N_LIN linha(s) não vazias"
ok "manifesto ADR-192: $N_OK/$N_LIN linhas OK"

# 2. a linha do driver no manifesto é o sha do driver em disco
LINHAS=$(grep -c "  $REL\$" "$MAN")
[ "$LINHAS" = "1" ] || fail "manifesto com $LINHAS linha(s) para $REL (exigido: 1)"
[ "$(grep "  $REL\$" "$MAN" | awk '{print $1}')" = "$(sha256f "$REL")" ] \
  || fail "o sha256 da linha de $REL no manifesto difere do arquivo"
ok "a linha de $REL no manifesto é o sha256 do arquivo"

# 3. o driver mira a 1.4.3
[ "$(grep -c '^TARGET_BASE="1.4.3"$' "$REL")" = "1" ] || fail "TARGET_BASE=\"1.4.3\" não aparece exatamente uma vez"
[ "$(grep -c 'TARGET_BASE="1.4.2"' "$REL")" = "0" ] || fail "o driver ainda tem TARGET_BASE=\"1.4.2\""
ok "TARGET_BASE=\"1.4.3\" uma vez, nenhum 1.4.2"

# 4. o --help anuncia o alvo
HELP=$(bash "$REL" --help </dev/null 2>&1) || fail "release.sh --help saiu rc diferente de 0"
[ "$(printf '%s\n' "$HELP" | head -n 1)" = "$HELP_LINE" ] \
  || fail "release.sh --help: primeira linha «$(printf '%s\n' "$HELP" | head -n 1)»"
ok "release.sh --help: $HELP_LINE"

# 5. a base da faixa
git merge-base --is-ancestor "$V142" HEAD </dev/null >/dev/null 2>&1 || fail "$V142 (v1.4.2) não é ancestral do HEAD"
ok "$V142 (v1.4.2) ancestral do HEAD"
exit 0
