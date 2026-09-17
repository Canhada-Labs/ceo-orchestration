#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: instrumento de UM pacote (PLAN-190 W1).
# measure-suite-baseline.sh — mede, no main SEM o patch, o conjunto exato de
# testes que já falham nas suítes do pytest.ini (as mesmas duas passadas do
# CI: paralela `not serial` e `serial`) e grava em suite-baseline.txt com a
# âncora do commit medido. O OWNER-190-W1-SIGN.sh compara o conjunto de falhas
# DEPOIS do patch contra este arquivo: falha nova reprova; falha que some é nota.
#
#   bash .claude/plans/PLAN-190/w1/measure-suite-baseline.sh
#
# Roda num worktree destacado e descartável do HEAD (a árvore de trabalho não
# é tocada). Grava só .claude/plans/PLAN-190/w1/suite-baseline.txt.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT=.claude/plans/PLAN-190/w1/suite-baseline.txt
ANCHOR=$(git rev-parse HEAD)
WORK=$(mktemp -d /tmp/p190-baseline.XXXXXX)
WT="$WORK/tree"
cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1 || printf 'remova à mão: git worktree remove --force %s\n' "$WT" >&2; }
trap cleanup EXIT
git worktree add --detach -q "$WT" "$ANCHOR"
set +e
(cd "$WT" && python3 -m pytest -n auto -m 'not serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider) >"$WORK/parallel.out" 2>&1
P_RC=$?
(cd "$WT" && python3 -m pytest -m 'serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider) >"$WORK/serial.out" 2>&1
S_RC=$?
set -e
case "$P_RC" in 0|1) ;; *) printf 'FAIL: passada paralela não terminou (rc=%s); log %s\n' "$P_RC" "$WORK/parallel.out" >&2; exit 1 ;; esac
case "$S_RC" in 0|1) ;; *) printf 'FAIL: passada serial não terminou (rc=%s); log %s\n' "$S_RC" "$WORK/serial.out" >&2; exit 1 ;; esac
P_SUM=$(awk '/ in [0-9.]+s/{v=$0} END{print v}' "$WORK/parallel.out")
S_SUM=$(awk '/ in [0-9.]+s/{v=$0} END{print v}' "$WORK/serial.out")
{
  printf '# anchor: %s\n' "$ANCHOR"
  printf '# measured: %s (UTC) on a detached worktree of the anchor, python %s\n' "$(date -u +%Y-%m-%dT%H:%M:%S)" "$(python3 -c 'import platform; print(platform.python_version())')"
  printf '# command: pytest -n auto -m "not serial" | pytest -m serial  (pytest.ini testpaths, --strict-markers, -rfE)\n'
  printf '# parallel: %s\n' "$P_SUM"
  printf '# serial: %s\n' "$S_SUM"
  awk '$1=="FAILED" || $1=="ERROR" {print $2}' "$WORK/parallel.out" "$WORK/serial.out" | sort -u
} > "$OUT"
printf 'linha de base gravada em %s: %s falha(s) pré-existente(s)\n' "$OUT" "$(awk '!/^#/ && NF' "$OUT" | wc -l | tr -d ' ')"
