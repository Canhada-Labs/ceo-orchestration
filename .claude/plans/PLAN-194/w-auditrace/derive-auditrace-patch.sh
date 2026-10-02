#!/usr/bin/env bash
# derive-auditrace-patch.sh — deriva o auditrace.patch das cópias em staged/ sobre uma base, sem
# tocar a árvore de trabalho (PLAN-194, cura da corrida no gravador do agent_spawn).
#
#   bash .claude/plans/PLAN-194/w-auditrace/derive-auditrace-patch.sh <arquivo-de-saída> [BASE]
#
# BASE = a revisão sobre a qual o patch vai aplicar (padrão: HEAD). O conteúdo novo de cada caminho
# vive em .claude/plans/PLAN-194/w-auditrace/staged/<caminho> (caminho NÃO canônico); o modo do
# arquivo é o da BASE. Um índice temporário recebe os blobs das cópias e o diff sai com flags pinadas
# (--full-index, prefixos a/ b/, myers, sem cor, sem renomes, sem ordem de arquivos do usuário,
# contexto entre hunks 0, heurística de indentação ligada, linhas vazias de contexto não suprimidas),
# para que o mesmo par (base, staged) dê os mesmos bytes também sob outra configuração do git. Uso de
# manutenção (CEO, depois de uma rodada de rail que mude staged/): derive, confira o diff contra o
# anterior e commite SÓ o patch — staged/ fica fora do git (.gitignore: «staged/»). O SIGN não deriva
# e não lê staged/: confere a pré-imagem de cada caminho contra o HEAD e a pós-imagem contra o
# `index` do próprio patch.
set -euo pipefail
OUT="${1:?uso: bash $0 <arquivo-de-saída> [BASE]}"
BASE="${2:-HEAD}"
case "$OUT" in /*) : ;; *) OUT="$PWD/$OUT" ;; esac
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel)"
cd "$ROOT"
D=.claude/plans/PLAN-194/w-auditrace
PATHS="
.claude/hooks/audit_log.py
.claude/hooks/tests/test_audit_log.py
.claude/hooks/tests/test_two_writer_chain.py
"
[ ! -e "$OUT" ] || { printf 'já existe: %s — escolha um arquivo novo\n' "$OUT" >&2; exit 1; }
git rev-parse --verify --quiet "$BASE^{commit}" >/dev/null || { printf 'revisão desconhecida: %s\n' "$BASE" >&2; exit 1; }
TMPD="$(mktemp -d "${TMPDIR:-/tmp}/auditrace-derive.XXXXXX")"
cleanup() { rm -f "$TMPD/index"; rmdir "$TMPD" 2>/dev/null || :; }
trap cleanup EXIT
IDX="$TMPD/index"
GIT_INDEX_FILE="$IDX" git read-tree "$BASE"
for p in $PATHS; do
  [ -f "$D/staged/$p" ] || { printf 'cópia ausente: %s/staged/%s\n' "$D" "$p" >&2; exit 1; }
  mode="$(git ls-tree "$BASE" -- "$p" | awk '{print $1}')"
  [ -n "$mode" ] || { printf '%s não existe em %s\n' "$p" "$BASE" >&2; exit 1; }
  blob="$(git hash-object -w -- "$D/staged/$p")"
  GIT_INDEX_FILE="$IDX" git update-index --cacheinfo "$mode,$blob,$p"
done
TREE="$(GIT_INDEX_FILE="$IDX" git write-tree)"
# shellcheck disable=SC2086 # PATHS é uma lista de caminhos sem espaço, partida de propósito
git -c core.quotepath=on -c diff.suppressBlankEmpty=false diff --full-index --no-color --no-ext-diff \
  --no-textconv --no-renames -O/dev/null --inter-hunk-context=0 --indent-heuristic \
  --diff-algorithm=myers --unified=3 --src-prefix=a/ --dst-prefix=b/ \
  "$BASE" "$TREE" -- $PATHS > "$OUT"
[ -s "$OUT" ] || { rm -f "$OUT"; printf 'o patch saiu vazio: staged/ = base\n' >&2; exit 1; }
printf 'patch: %s\nsha256: %s\nbase: %s\n' "$OUT" "$(shasum -a 256 "$OUT" | awk '{print $1}')" "$(git rev-parse "$BASE")"
