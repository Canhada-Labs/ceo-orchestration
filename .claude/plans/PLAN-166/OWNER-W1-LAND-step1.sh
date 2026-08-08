#!/bin/bash
# PLAN-166 W1 — LAND step 1 (Owner-run): applies NÃO-kernel + sweep de contagens.
# Espelho exato dos comandos validados na simulação em clone limpo (land-sim.sh,
# 2026-08-06: verify-counts EXIT=0, asserts 52/52, e2e 45/45, bateria 5010 pass,
# touched−scope=∅). release.yml fica FORA — rota kernel-override (step 2).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

APPROVED=.claude/plans/PLAN-166/architect/round-1/approved.md

# ---- Guards fail-closed (R-rail essencial do generate-ceremony, inline) ----
echo "== G1: assinatura GPG do sentinel"
# NUNCA `| grep -q` sob pipefail (SIGPIPE mata o produtor — lição
# feedback-grep-q-pipefail-kills-producer): capture e case.
GPG_OUT=$(gpg --verify "$APPROVED.asc" "$APPROVED" 2>&1) || { echo "FAIL: gpg --verify rc!=0"; echo "$GPG_OUT"; exit 1; }
case "$GPG_OUT" in
  *"Good signature"*) echo "   OK" ;;
  *) echo "FAIL: assinatura inválida"; echo "$GPG_OUT"; exit 1 ;;
esac

echo "== G2: anchor == HEAD"
ANCHOR=$(grep '^Anchor-SHA:' "$APPROVED" | awk '{print $2}')
HEAD_SHA=$(git rev-parse HEAD)
[ "$ANCHOR" = "$HEAD_SHA" ] || { echo "FAIL: anchor $ANCHOR != HEAD $HEAD_SHA — re-instanciar e re-assinar"; exit 1; }
echo "   OK ($ANCHOR)"

echo "== G3: manifesto staged fail-closed"
shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 > /dev/null || { echo "FAIL: manifesto"; exit 1; }
echo "   OK (32 entradas)"

echo "== G4: árvore limpa antes do apply"
DIRT=$(git status --porcelain | grep -v '^?? .claude/plans/PLAN-166/' || true)
[ -z "$DIRT" ] || { echo "FAIL: árvore suja fora de PLAN-166/:"; echo "$DIRT"; exit 1; }
echo "   OK"

S=.claude/plans/PLAN-166/staged

# ---- §3 applies (grupo A menos release.yml; grupo B; template 15º) ----
echo "== applies"
for f in \
  .github/workflows/npm-publish.yml \
  .github/workflows/smoke-install.yml \
  .claude/governance/npm-trusted-publisher.txt \
  .claude/governance/pair-rail-verdict-template.md \
  .claude/scripts/tests/test_release_workflow_asserts.py \
  .claude/.framework-version \
  .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md \
  .claude/scripts/check-framework-updates.sh \
  INSTALL.md \
  scripts/_framework_manifest_set.sh \
  scripts/doctor.sh \
  scripts/install.sh \
  scripts/tests/_parity_classify.py \
  scripts/tests/test-upgrade-spec-ownership.sh \
  scripts/upgrade.sh
do
  cp -p "$S/$f" "$f"
  echo "   applied $f"
done
chmod +x scripts/install.sh scripts/upgrade.sh scripts/doctor.sh \
  scripts/tests/test-upgrade-spec-ownership.sh .claude/scripts/check-framework-updates.sh

# ---- §4 sweep (BSD sed; content-anchored — validado na simulação) ----
echo "== sweep 188->189 + 29->31"
sed -i '' 's/\*\*188 ADRs\*\*/**189 ADRs**/' CLAUDE.md
sed -i '' 's/# 188 ADRs/# 189 ADRs/' README.md README.pt-BR.md npm/README.md docs/FAQ.md
sed -i '' 's/| Architecture decision records | \*\*188\*\*/| Architecture decision records | **189**/' README.md README.pt-BR.md docs/README.md npm/README.md
sed -i '' 's/| ADRs shipped | 188 |/| ADRs shipped | 189 |/' docs/CTO-GUIDE.md
sed -i '' 's/# 188 ADRs on disk/# 189 ADRs on disk/' docs/CTO-GUIDE.md
sed -i '' -E 's/(\| ADRs +\| )188/\1189/' docs/ARCHITECTURE.md
sed -i '' 's/# 188 architecture decision records/# 189 architecture decision records/' docs/ARCHITECTURE.md
sed -i '' 's/(188 to date)/(189 to date)/' docs/ARCHITECTURE.md
sed -i '' 's/188 ADRs document every architectural decision/189 ADRs document every architectural decision/' docs/GUIA-COMPLETO.md
sed -i '' 's/188 Architecture Decision Records/189 Architecture Decision Records/' docs/GUIA-COMPLETO.md
sed -i '' 's/release-gate + publish-release (29 steps,/release-gate + publish-release (31 steps,/' RELEASE.md

echo "== census pós-sweep (tem de sair 'sweep clean')"
grep -rn "188" CLAUDE.md README.md README.pt-BR.md docs/ARCHITECTURE.md \
  docs/FAQ.md docs/README.md docs/CTO-GUIDE.md docs/GUIA-COMPLETO.md \
  npm/README.md INSTALL.md 2>/dev/null \
  | grep -iv "S188\|PLAN-188\|#188\|0188\|1188" | grep -i "adr\|decision record" || echo "sweep clean"

echo "==== STEP 1 CONCLUÍDO — volte para a sessão: o CEO roda os gates §6 ===="
