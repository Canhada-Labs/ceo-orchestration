#!/usr/bin/env bash
# =============================================================================
# PLAN-168 — OWNER-LAND (espelhamento por TABELA, fail-closed, com --dry-run)
#
# Uso (da RAIZ do repo, após assinar approved.md):
#   bash .claude/plans/PLAN-168/OWNER-LAND.sh --dry-run   # só verifica
#   bash .claude/plans/PLAN-168/OWNER-LAND.sh             # verifica + aplica
#
# O que ele NUNCA faz: git add -A, git commit, tocar arquivo fora da TABELA.
# O commit é do Owner, com a lista explícita impressa no fim.
#
# Precondição estrutural: a cerimônia do PLAN-166 já LANDADA — as cópias
# staged dos arquivos compartilhados carregam aquele conteúdo por baixo das
# edições deste pack. A tabela de precondições verifica exatamente isso e
# ABORTA em divergência (ordem dos packs é contrato, não sugestão).
# =============================================================================
set -uo pipefail

PLAN_DIR=".claude/plans/PLAN-168"
STAGED="$PLAN_DIR/staged"
MANIFEST="$PLAN_DIR/staged-manifest.sha256"
TABLE="$PLAN_DIR/land-table.tsv"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

[ -f "scripts/_hash_lib.sh" ] && [ -d ".claude/plans" ] || {
  echo "ABORT: rode da RAIZ do repo." >&2; exit 2; }
[ -f "$MANIFEST" ] || { echo "ABORT: manifesto ausente: $MANIFEST" >&2; exit 2; }
[ -f "$TABLE" ]    || { echo "ABORT: tabela ausente: $TABLE" >&2; exit 2; }

sha() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; }

echo "== 1/4 integridade do pack staged (shasum -c, fail-closed) =="
if ! shasum -a 256 -c "$MANIFEST" >/tmp/p168-manifest-check.txt 2>&1; then
  echo "ABORT: manifesto NÃO confere — pack adulterado ou incompleto:" >&2
  grep -v ": OK$" /tmp/p168-manifest-check.txt | head -10 >&2
  exit 1
fi
echo "   OK: $(grep -c ": OK$" /tmp/p168-manifest-check.txt) arquivos staged conferem"

echo "== 2/4 precondições da árvore viva (PLAN-166 landado?) =="
FAILS=0
while IFS=$'\t' read -r rel pre mode; do
  case "$rel" in ''|'#'*) continue ;; esac
  if [ "$pre" = "ABSENT" ]; then
    if [ -e "$rel" ]; then
      echo "   DIVERGE: $rel deveria NÃO existir ainda (arquivo novo do pack)" >&2
      FAILS=$((FAILS+1))
    fi
  else
    got="$( sha "$rel" )"
    if [ "$got" != "$pre" ]; then
      echo "   DIVERGE: $rel" >&2
      echo "            esperado(pré-land)=$pre" >&2
      echo "            observado         =${got:-<ausente>}" >&2
      FAILS=$((FAILS+1))
    fi
  fi
done < "$TABLE"
if [ "$FAILS" -gt 0 ]; then
  echo "ABORT: $FAILS precondição(ões) divergem. Se a cerimônia do PLAN-166" >&2
  echo "       ainda não landou, lande-a PRIMEIRO. Nada foi tocado." >&2
  exit 1
fi
echo "   OK: árvore viva no estado esperado (bytes)"

echo "== 2b/4 arquivos do pack LIMPOS no git (nenhum outro pack não-commitado) =="
# Os shas acima conferem BYTES — mas a sujeira do PLAN-166 já está no disco,
# então bytes certos NÃO provam que o 166 foi commitado. Um apply sobre
# arquivo sujo faria o commit do 168 carregar conteúdo do 166 junto.
DIRTY=""
while IFS=$'\t' read -r rel pre mode; do
  case "$rel" in ''|'#'*) continue ;; esac
  st="$( git status --porcelain -- "$rel" 2>/dev/null )"
  [ -n "$st" ] && DIRTY="$DIRTY$st
"
done < "$TABLE"
if [ -n "$DIRTY" ]; then
  echo "ABORT: arquivo(s) do pack com mudanças NÃO COMMITADAS na árvore viva:" >&2
  printf '%s' "$DIRTY" | head -12 >&2
  echo "       Lande/commite a cerimônia pendente (PLAN-166) primeiro." >&2
  exit 1
fi
echo "   OK: nenhum arquivo do pack sujo no git"

if [ "$DRY" -eq 1 ]; then
  echo "== --dry-run: nada aplicado. Tabela do espelhamento: =="
  awk -F'\t' '!/^#/ && NF>=2 {printf "   %s%s\n", $1, ($3=="x" ? "  (+x)" : "")}' "$TABLE"
  exit 0
fi

echo "== 3/4 aplicando por TABELA (staged -> vivo) =="
while IFS=$'\t' read -r rel pre mode; do
  case "$rel" in ''|'#'*) continue ;; esac
  src="$STAGED/$rel"
  [ -f "$src" ] || { echo "ABORT: staged ausente: $src (nada mais será aplicado)" >&2; exit 1; }
  mkdir -p "$( dirname "$rel" )"
  cp "$src" "$rel" || { echo "ABORT: cp falhou em $rel" >&2; exit 1; }
  [ "$mode" = "x" ] && chmod +x "$rel"
  post="$( sha "$rel" )"; want="$( sha "$src" )"
  [ "$post" = "$want" ] || { echo "ABORT: pós-cópia diverge em $rel" >&2; exit 1; }
done < "$TABLE"
echo "   OK: $(awk -F'\t' '!/^#/ && NF>=2' "$TABLE" | wc -l | tr -d ' ') arquivos aplicados e re-verificados"

echo "== 4/4 gates rápidos pós-apply =="
rc=0
bash scripts/tests/test-ownership-verdict-unit.sh --quiet || rc=1
bash scripts/tests/test-ownership-nightly-gate.sh >/dev/null || rc=1
python3 .claude/scripts/check-claude-md-claims.py >/dev/null || rc=1
bash .claude/scripts/local/verify-counts.sh >/dev/null || rc=1
python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py -q >/dev/null || rc=1
if [ "$rc" -ne 0 ]; then
  echo "ABORT: gate rápido FALHOU pós-apply — NÃO commite; investigue." >&2
  exit 1
fi
echo "   OK: unit 63/63 · gate-control 12/12 · claims · counts · asserts"

echo ""
echo "== PRÓXIMOS PASSOS (manuais, do Owner) =="
echo "1. Bateria pesada (opcional antes do commit; o INV-4 leva ~2 min):"
echo "     bash scripts/tests/test-protocol-pointer-render.sh"
echo "     bash scripts/tests/test-protocol-pointer-inv4.sh"
echo "2. Confira que approved.md assinado cobre o Scope (touched−scope=∅):"
awk -F'\t' '!/^#/ && NF>=2 {print "     "$1}' "$TABLE" | grep -E "workflows|install.sh|upgrade.sh|_framework_manifest_set|ADR-190"
echo "3. git add EXPLÍCITO (nunca -A — a árvore pode carregar outros packs):"
printf '     git add'
awk -F'\t' '!/^#/ && NF>=2 {printf " %s", $1}' "$TABLE"
printf ' %s\n' "$PLAN_DIR"
echo "4. Commit assinado:"
echo "     git commit -S -m 'plan(PLAN-168): CI wiring + INV-4 curada + ADR-190 — pack landado'"
exit 0
