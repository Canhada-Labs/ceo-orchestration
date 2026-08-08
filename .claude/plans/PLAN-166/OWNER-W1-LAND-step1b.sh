#!/bin/bash
# =============================================================================
# PLAN-166 W1 — LAND step 1b (SUBSTITUI o step1, obsoleto em 07/08).
#
# Por que o step1 original não pode rodar mais (auditado S297-noite):
#   - G4 dele exige árvore LIMPA e faria os applies — mas a árvore JÁ carrega
#     os applies como sujeira desde a pausa de S296 (12 arquivos byte-==
#     staged, verificado), e
#   - 3 arquivos do apply-list (install.sh, upgrade.sh,
#     _framework_manifest_set.sh) foram SUBSUMIDOS pelo land do PLAN-167
#     (`7c0828a`) — re-aplicar as cópias staged de 06/08 REVERTERIA aquele
#     land. Eles estão LIMPOS no git e assim devem ficar.
#
# Este script portanto NÃO aplica nada: ele AUDITA que a sujeira é exatamente
# o pack, roda os gates na árvore de hoje e imprime a lista de commit.
#
#   bash .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh
# =============================================================================
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

APPROVED=.claude/plans/PLAN-166/architect/round-1/approved.md
S=.claude/plans/PLAN-166/staged

echo "== G1: assinatura GPG do sentinel"
GPG_OUT=$(gpg --verify "$APPROVED.asc" "$APPROVED" 2>&1) || { echo "FAIL: gpg --verify rc!=0"; echo "$GPG_OUT"; exit 1; }
case "$GPG_OUT" in
  *"Good signature"*) echo "   OK" ;;
  *) echo "FAIL: assinatura inválida"; echo "$GPG_OUT"; exit 1 ;;
esac

echo "== G2: anchor == HEAD"
ANCHOR=$(grep '^Anchor-SHA:' "$APPROVED" | awk '{print $2}')
HEAD_SHA=$(git rev-parse HEAD)
[ "$ANCHOR" = "$HEAD_SHA" ] || { echo "FAIL: anchor $ANCHOR != HEAD $HEAD_SHA — re-instanciar e re-assinar (ver W1-approved-draft.md, passos 1-4 do header)"; exit 1; }
echo "   OK ($ANCHOR)"

echo "== G3: manifesto staged fail-closed"
shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 > /dev/null || { echo "FAIL: manifesto"; exit 1; }
echo "   OK (32 entradas)"

echo "== G4b: a sujeira É o pack (inventário + bytes), e os 3 subsumidos estão limpos"
# 12 arquivos que DEVEM estar sujos e byte-idênticos ao staged:
PACK12=".github/workflows/npm-publish.yml
.github/workflows/smoke-install.yml
.claude/governance/npm-trusted-publisher.txt
.claude/governance/pair-rail-verdict-template.md
.claude/scripts/tests/test_release_workflow_asserts.py
.claude/.framework-version
.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
.claude/scripts/check-framework-updates.sh
INSTALL.md
scripts/doctor.sh
scripts/tests/_parity_classify.py
scripts/tests/test-upgrade-spec-ownership.sh"
# Arquivos do sweep de contagens (sed na árvore em S296; validados pelo gate
# verify-counts abaixo, não por bytes) + release.yml (rota kernel, step 2):
SWEEP="README.md
README.pt-BR.md
RELEASE.md
docs/ARCHITECTURE.md
docs/CTO-GUIDE.md
docs/FAQ.md
docs/GUIA-COMPLETO.md
docs/README.md
npm/README.md
.github/workflows/release.yml"
FAILS=0
while IFS= read -r f; do
  if ! cmp -s "$f" "$S/$f"; then echo "   FAIL: $f difere do staged"; FAILS=$((FAILS+1)); fi
done <<< "$PACK12"
for f in scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh; do
  st=$(git status --porcelain -- "$f")
  [ -z "$st" ] || { echo "   FAIL: $f deveria estar LIMPO (subsumido pelo PLAN-167)"; FAILS=$((FAILS+1)); }
done
# nenhuma sujeira tracked fora do inventário (plan files têm carona §7):
while IFS= read -r line; do
  [ -z "$line" ] && continue
  p="${line:3}"
  case "$p" in .claude/plans/*) continue ;; esac
  if ! grep -qxF "$p" <<< "$PACK12"$'\n'"$SWEEP"; then
    echo "   FAIL: sujeira tracked FORA do inventário do pack: $line"; FAILS=$((FAILS+1))
  fi
done <<< "$(git status --porcelain | grep -v '^??')"
[ "$FAILS" -eq 0 ] || { echo "FAIL: G4b — $FAILS divergência(s); não commite"; exit 1; }
echo "   OK (12 byte-== staged; 3 subsumidos limpos; zero sujeira estranha)"

echo "== G5: gates na árvore de HOJE"
python3 .claude/scripts/check-claude-md-claims.py >/dev/null || { echo "FAIL: claims"; exit 1; }
bash .claude/scripts/local/verify-counts.sh >/dev/null || { echo "FAIL: verify-counts"; exit 1; }
python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py -q >/dev/null || { echo "FAIL: asserts"; exit 1; }
echo "   OK: claims · verify-counts · asserts 52/52"

echo "== G6: e2e parity (≈4 min)"
bash scripts/tests/test-install-upgrade-parity-e2e.sh >/tmp/p166-parity-land.log 2>&1 || { echo "FAIL: parity"; tail -5 /tmp/p166-parity-land.log; exit 1; }
echo "   OK: parity PASS"

echo "== G7: e2e F3 spec-ownership (≈4 min) — 45/45, OU 44/45 com a ÚNICA exceção nomeada"
bash scripts/tests/test-upgrade-spec-ownership.sh >/tmp/p166-f3-land.log 2>&1 || true
RESULT=$(grep -E '^==> RESULT' /tmp/p166-f3-land.log || true)
if grep -q "pass=45 fail=0" <<< "$RESULT"; then
  echo "   OK: 45/45 (a regressão ADOPTER-FORK já foi curada — provavelmente o PLAN-168 landou antes)"
elif grep -q "pass=44 fail=1" <<< "$RESULT" \
     && [ "$(grep -c '^  FAIL' /tmp/p166-f3-land.log)" -eq 1 ] \
     && grep -q "FAIL no ADOPTER-FORK warning" /tmp/p166-f3-land.log; then
  echo "   OK (exceção NOMEADA): 44/45 — a única falha é a WARNING sem o token"
  echo "   ADOPTER-FORK, regressão do rewrite do PLAN-167 (7c0828a), corrigida"
  echo "   no pack do PLAN-168 (staged/scripts/upgrade.sh; provado 45/45 no overlay)."
else
  echo "FAIL: F3 fora do contrato ($RESULT) — investigue antes de commitar"
  grep '^  FAIL' /tmp/p166-f3-land.log | head -5
  exit 1
fi

echo ""
echo "==== STEP 1b VERDE — commit da cerimônia ===="
echo "Confira touched−scope=∅ (exceção §7: .claude/plans/PLAN-166/**):"
git status --porcelain | grep -v '^??' | awk '{print "   "$2}'
echo ""
echo "git add explícito (NUNCA -A):"
printf '  git add '
{ git status --porcelain | grep -v '^??' | awk '{print $2}'; echo ".claude/plans/PLAN-166"; } | tr '\n' ' '
echo ""
echo "  git commit -S -m 'ceremony(PLAN-166 W1): findings-closure landada — applies+sweep commitados; install/upgrade/FMS subsumidos pelo PLAN-167; F3 44/45 com exceção nomeada (fecha no PLAN-168)'"
echo ""
echo "⚠️  NÃO PUSHE AINDA. Lande o PLAN-168 em seguida (PREPARE-TO-SIGN → gpg →"
echo "    OWNER-LAND) e pushe os DOIS commits juntos: o smoke-install roda o F3"
echo "    no push, e entre os dois lands ele daria 44/45 (vermelho transitório)."
