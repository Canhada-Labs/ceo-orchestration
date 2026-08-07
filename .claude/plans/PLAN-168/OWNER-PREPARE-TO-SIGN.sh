#!/usr/bin/env bash
# =============================================================================
# PLAN-168 — prepara o approved.md para assinatura.
#
#   bash .claude/plans/PLAN-168/OWNER-PREPARE-TO-SIGN.sh
#
# Faz só o trabalho mecânico: confere o manifesto, ENSAIA o land (dry-run —
# que também exige o PLAN-166 já COMMITADO; ele aborta com pack files sujos),
# fixa o Anchor-SHA no HEAD atual e gera approved.md do draft. NÃO assina —
# a assinatura é sua, com a sua chave, e é ela que autoriza a edição canônica.
# =============================================================================
set -euo pipefail

D=".claude/plans/PLAN-168"
[ -f "scripts/install.sh" ] || { echo "ABORT: rode da raiz do repositório" >&2; exit 1; }

echo "== 1. o manifesto do pack confere? =="
shasum -a 256 -c "$D/staged-manifest.sha256" >/dev/null 2>&1 \
  || { echo "ABORT: o manifesto NÃO confere — não assine" >&2; exit 1; }
echo "   ok — $(wc -l < "$D/staged-manifest.sha256" | tr -d ' ') arquivos íntegros"

echo "== 2. o pack aplica sem conflito? (ensaio; exige PLAN-166 LANDADO) =="
if ! bash "$D/OWNER-LAND.sh" --dry-run >/tmp/p168-rehearsal.out 2>&1; then
  echo "ABORT: o ensaio falhou — não assine. Motivo:" >&2
  tail -6 /tmp/p168-rehearsal.out >&2
  echo "       (Se listou arquivos sujos: lande a cerimônia do PLAN-166 primeiro.)" >&2
  exit 1
fi
echo "   ok — ensaio limpo (precondições de bytes + git limpos)"

echo "== 3. fixando o Anchor-SHA no HEAD atual =="
HEAD_SHA="$( git rev-parse HEAD )"
sed "s|^Anchor-SHA: .*|Anchor-SHA: $HEAD_SHA|" "$D/W-approved-draft.md" > "$D/approved.md"
grep -q "Anchor-SHA: $HEAD_SHA" "$D/approved.md" \
  || { echo "ABORT: não consegui fixar o anchor" >&2; rm -f "$D/approved.md"; exit 1; }
echo "   ok — $HEAD_SHA"

cat <<EOF

────────────────────────────────────────────────────────────────────
PRONTO PARA ASSINAR.

O que a sua assinatura autoriza (Scope, 6 canônicos):
  .github/workflows/smoke-install.yml      (+9 paths, 3 steps por-PR)
  .github/workflows/ownership-nightly.yml  (NOVO — e2e nightly com gate)
  scripts/install.sh                        (ponteiro via gerador único)
  scripts/upgrade.sh                        (idem + cura do degradado)
  scripts/_framework_manifest_set.sh        (gerador + degraded no Stage B)
  .claude/adr/ADR-190-*.md                  (o contrato da tabela)

Evidência: e2e completo 62 GREEN / 3 RED exatos {0016,0024,0027} —
OWN-0074 verde pela 1ª vez; INV-4 4/4 pernas; render 8/8 (paridade
byte-a-byte com install real); unit 63/63; gate-control 12/12; rail
cross-model 3 rodadas (16 aceitos / 1 refutado). Nuance D2 que a sua
assinatura ratifica está em approved.md §"D2 scope nuance".

Agora rode estes dois comandos:

  gpg --detach-sign --armor $D/approved.md
  bash $D/OWNER-LAND.sh

Se o gpg reclamar de "No pinentry":
  export GPG_TTY=\$(tty); gpgconf --kill gpg-agent
────────────────────────────────────────────────────────────────────
EOF
