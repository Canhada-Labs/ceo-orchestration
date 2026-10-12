#!/bin/bash
# hard-w7a.sh — as passadas próprias da W7a (PLAN-183) que pedem mais de um comando: chamado pela 1.ª linha
# `hard` de .claude/plans/PLAN-183/w7a/sign.tsv (forma 2 do molde sign-min: `bash <CAMINHO>.sh`), com cwd na
# raiz do repositório que tem o w7a.patch aplicado. Sai rc 0 só se todas as conferências abaixo passarem; em
# qualquer outro caso sai rc 1. O julgamento é só este rc: o resumo de cada passo vai para a saída padrão, que
# quem chama guarda em log.
#
# Na ordem:
#   1. o gate no modo do CI no repositório (sem argumentos): rc 0 e a última linha
#      «OK: harness-config gate green (static=yes, replay=yes, 0 warning(s))»;
#   2. C7, perna verde: instalação do zero (--profile core) a partir desta árvore num alvo com .git vazio; o gate
#      do alvo (--repo-root <alvo> --replay --no-exec-bit): rc 0 e
#      «OK: harness-config gate green (static=no, replay=yes, 0 warning(s))»; a pasta nova do alvo com
#      exatamente os 3 .json, cada um igual byte a byte ao desta árvore, e nenhum «{{» neles;
#   3. o contrato do /ceo-boot (cwd = alvo, sem argumentos): rc 0 e a última linha começando por
#      «OK: harness-config gate green (static=yes, replay=yes, »;
#   4. C9: a árvore do commit b55084da (v1.4.2), ancestral do HEAD, instalada do zero: o gate do alvo dá rc 1 e
#      «FAIL: 3 RED finding(s) (0 warning(s))»; o scripts/upgrade.sh desta árvore sobre esse alvo: rc 0; os 3
#      .json e o hook iguais byte a byte aos desta árvore; o gate do alvo: rc 0 e a linha verde do passo 2;
#   5. o arquivo de teste do gate: rc 0 e o resumo «39 passed».
# As instalações, o upgrade e os gates rodam sem CEO_SOTA_DISABLE, CLAUDE_PROJECT_DIR e
# CLAUDE_PROJECT_DIR_NATIVE, com HOME próprio dentro do diretório de trabalho deste script, criado sob
# ${TMPDIR:-/tmp} (o TMPDIR recebido não é trocado: os filhos herdam o que quem chama dá). Os alvos são apagados
# depois de conferidos, e o diretório de trabalho, no fim, só com rc 0; com qualquer outro rc ele fica onde
# está, com os logs e, se houver, o alvo do passo que falhou. A limpeza só apaga caminhos dentro desse diretório.
# PYTHONDONTWRITEBYTECODE=1 é exportado para todos os descendentes que herdam o ambiente; os hooks que o gate
# executa no replay recebem o ambiente montado por _replay_env do hook, que não carrega essa variável.
set -u
set -o pipefail
export PYTHONDONTWRITEBYTECODE=1

HOOK=.claude/hooks/check_harness_config.py
TEST_PATH=.claude/hooks/tests/test_check_harness_config.py
NEW_DIR=.claude/hooks/_lib/harness_replay
FIXTURES="agent_spawn_named_no_skill_content.json bash_safety_destructive.json canonical_edit_unauthorized.json"
V142=b55084da6dd8e4a05fc9893b2690df8aebcfd0ca
TESTS_EXPECTED=39
GATE_REPO_LINE="OK: harness-config gate green (static=yes, replay=yes, 0 warning(s))"
GATE_TARGET_LINE="OK: harness-config gate green (static=no, replay=yes, 0 warning(s))"
GATE_RED_LINE="FAIL: 3 RED finding(s) (0 warning(s))"
BOOT_PREFIX="OK: harness-config gate green (static=yes, replay=yes, "

fail() { printf 'FALHOU: %s\n' "$1"; exit 1; }
ok() { printf 'ok: %s\n' "$1"; }

ROOT=$(pwd -P) || fail "diretório atual ilegível"
[ -f "$ROOT/$HOOK" ] && [ -f "$ROOT/scripts/install.sh" ] && [ -f "$ROOT/scripts/upgrade.sh" ] \
  || fail "o diretório atual não é a raiz do repositório"
W=$(mktemp -d "${TMPDIR:-/tmp}/w7a-hard.XXXXXX") || fail "mktemp"
W=$(cd "$W" && pwd -P) || fail "diretório de trabalho ilegível"
printf 'diretório de trabalho: %s\n' "$W"

drop() {  # caminho — apaga um caminho que é filho direto de $W
  python3 -I -B -c 'import os, shutil, sys
w, p = sys.argv[1], sys.argv[2]
if os.path.dirname(p) != w or os.path.islink(p):
    sys.exit(1)
shutil.rmtree(p)' "$W" "$1" </dev/null || fail "limpeza de $1"
}
clean_run() {  # home comando... — sem as três variáveis e com HOME=$W/<home>
  local h="$W/$1"
  shift
  mkdir -p "$h" || fail "mkdir $h"
  env -u CEO_SOTA_DISABLE -u CLAUDE_PROJECT_DIR -u CLAUDE_PROJECT_DIR_NATIVE HOME="$h" "$@" </dev/null
}
install_into() {  # árvore-fonte alvo log — instalação do zero (--profile core) num alvo novo com .git vazio
  mkdir -p "$2/.git" || fail "mkdir $2/.git"
  clean_run "home-$(basename "$2")" bash "$1/scripts/install.sh" "$2" --profile core > "$3" 2>&1
}
gate_on() {  # alvo log — o gate do alvo instalado, contra o próprio alvo
  clean_run "home-gate-$(basename "$1")" python3 -B "$1/$HOOK" --repo-root "$1" --replay --no-exec-bit > "$2" 2>&1
}
last_line() { awk 'NF {l = $0} END {print l}' "$1"; }

# 1. o gate no modo do CI, no repositório
RC=0; clean_run home-repo python3 -B "$HOOK" > "$W/gate-repo.out" 2>&1 || RC=$?
[ "$RC" = "0" ] && [ "$(last_line "$W/gate-repo.out")" = "$GATE_REPO_LINE" ] \
  || fail "gate no repositório: rc=$RC, última linha «$(last_line "$W/gate-repo.out")»"
ok "gate no modo do CI no repositório: $GATE_REPO_LINE"

# 2. C7, perna verde
TP="$W/t-patched"
RC=0; install_into "$ROOT" "$TP" "$W/install-patched.log" || RC=$?
[ "$RC" = "0" ] || fail "C7: instalação a partir desta árvore saiu rc=$RC"
RC=0; gate_on "$TP" "$W/gate-patched.out" || RC=$?
[ "$RC" = "0" ] && [ "$(last_line "$W/gate-patched.out")" = "$GATE_TARGET_LINE" ] \
  || fail "C7: gate do alvo: rc=$RC, última linha «$(last_line "$W/gate-patched.out")»"
LISTA=$(ls -A "$TP/$NEW_DIR" 2>/dev/null | LC_ALL=C sort | tr '\n' ' ')
[ "$LISTA" = "$(printf '%s\n' $FIXTURES | LC_ALL=C sort | tr '\n' ' ')" ] \
  || fail "C7: a pasta nova do alvo tem «${LISTA}»"
for fx in $FIXTURES; do
  cmp -s "$ROOT/$NEW_DIR/$fx" "$TP/$NEW_DIR/$fx" || fail "C7: $fx no alvo difere desta árvore"
done
RC=0; grep -RIl '{{' "$TP/$NEW_DIR" >/dev/null 2>&1 || RC=$?
case "$RC" in
  0) fail "C7: um .json da pasta nova do alvo contém «{{»" ;;
  1) ;;
  *) fail "C7: a busca de «{{» na pasta nova do alvo saiu rc=$RC" ;;
esac
ok "C7 perna verde: $GATE_TARGET_LINE; os 3 .json iguais byte a byte, nada além deles, nenhum «{{»"

# 3. contrato do /ceo-boot
RC=0; (cd "$TP" && clean_run home-boot python3 -B "$HOOK") > "$W/gate-boot.out" 2>&1 || RC=$?
case "$(last_line "$W/gate-boot.out")" in "$BOOT_PREFIX"*) BOOT_OK=1 ;; *) BOOT_OK=0 ;; esac
[ "$RC" = "0" ] && [ "$BOOT_OK" = "1" ] || fail "C7: contrato do /ceo-boot: rc=$RC, última linha «$(last_line "$W/gate-boot.out")»"
ok "C7 contrato do /ceo-boot: rc 0, $(last_line "$W/gate-boot.out")"
drop "$TP"

# 4. C9: v1.4.2 → upgrade.sh desta árvore
git merge-base --is-ancestor "$V142" HEAD </dev/null >/dev/null 2>&1 || fail "C9: $V142 não é ancestral do HEAD"
SRC="$W/v142-src"
mkdir "$SRC" || fail "mkdir $SRC"
git archive "$V142" </dev/null 2>/dev/null | tar -x -C "$SRC" 2>/dev/null || fail "C9: extração da árvore de $V142"
TV="$W/t-v142"
RC=0; install_into "$SRC" "$TV" "$W/install-v142.log" || RC=$?
[ "$RC" = "0" ] || fail "C9: instalação da v1.4.2 saiu rc=$RC"
drop "$SRC"
RC=0; gate_on "$TV" "$W/gate-v142-antes.out" || RC=$?
[ "$RC" = "1" ] && [ "$(last_line "$W/gate-v142-antes.out")" = "$GATE_RED_LINE" ] \
  || fail "C9: gate do alvo da v1.4.2 antes do upgrade: rc=$RC, última linha «$(last_line "$W/gate-v142-antes.out")»"
RC=0; clean_run home-upgrade bash "$ROOT/scripts/upgrade.sh" "$TV" > "$W/upgrade-v142.log" 2>&1 || RC=$?
[ "$RC" = "0" ] || fail "C9: upgrade.sh desta árvore saiu rc=$RC"
for fx in $FIXTURES; do
  cmp -s "$ROOT/$NEW_DIR/$fx" "$TV/$NEW_DIR/$fx" || fail "C9: $fx no alvo atualizado difere desta árvore"
done
cmp -s "$ROOT/$HOOK" "$TV/$HOOK" || fail "C9: o hook no alvo atualizado difere desta árvore"
RC=0; gate_on "$TV" "$W/gate-v142-depois.out" || RC=$?
[ "$RC" = "0" ] && [ "$(last_line "$W/gate-v142-depois.out")" = "$GATE_TARGET_LINE" ] \
  || fail "C9: gate do alvo atualizado: rc=$RC, última linha «$(last_line "$W/gate-v142-depois.out")»"
ok "C9: antes do upgrade «${GATE_RED_LINE}»; depois, os 3 .json e o hook iguais byte a byte e «${GATE_TARGET_LINE}»"
drop "$TV"

# 5. o arquivo de teste do gate
RC=0; env -u CEO_SOTA_DISABLE python3 -m pytest "$TEST_PATH" -q -p no:cacheprovider </dev/null > "$W/teste-gate.out" 2>&1 || RC=$?
[ "$RC" = "0" ] && grep -qE "^$TESTS_EXPECTED passed in [0-9.]+s" "$W/teste-gate.out" \
  || fail "teste do gate: rc=$RC, última linha «$(last_line "$W/teste-gate.out")»"
ok "teste do gate: $(last_line "$W/teste-gate.out")"

python3 -I -B -c 'import os, shutil, sys
w = sys.argv[1]
if not os.path.basename(w).startswith("w7a-hard.") or os.path.islink(w):
    sys.exit(1)
shutil.rmtree(w)' "$W" </dev/null || fail "limpeza do diretório de trabalho"
ok "diretório de trabalho apagado"
exit 0
