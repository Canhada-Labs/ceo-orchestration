#!/bin/bash
# Espelha os fixes do round codex (árvore viva -> cópias staged), regenera
# os patches e o manifesto. Só ESCREVE sob .claude/plans/PLAN-166/.
#
# O round 7 tocou um TERCEIRO canônico (o checker), que também tem cópia
# staged e patch próprio no pack — espelhar só install/upgrade deixaria o
# staged divergente do vivo sem nenhum gate acusar. Tabela path->patch para
# que acrescentar um arquivo seja uma linha, não uma edição em 4 lugares.
set -euo pipefail
cd /Users/joaocanhada/canhada-labs/ceo-orchestration
S=.claude/plans/PLAN-166/staged

MIRRORED="
scripts/install.sh|f3-install-delivery-record.patch
scripts/upgrade.sh|f3-upgrade-spec-forced-refresh.patch
.claude/scripts/check-framework-updates.sh|f3-check-framework-updates-marker-first.patch
scripts/_framework_manifest_set.sh|f3-fms-conditional-entries.patch
.github/workflows/smoke-install.yml|smoke-install-parity-e2e-wiring.patch
"

echo "$MIRRORED" | while IFS='|' read -r src patch; do
  [ -n "$src" ] || continue
  mkdir -p "$S/$( dirname "$src" )"
  cp -p "$src" "$S/$src"
  git diff HEAD -- "$src" > "$S/patches/$patch"
  git apply --check --reverse "$S/patches/$patch" \
    && echo "reverse-apply OK (patch == vivo): $src"
  cmp -s "$src" "$S/$src" && echo "staged == vivo: $src"
done

( cd "$S" && find . -type f ! -name '.DS_Store' | sed 's|^\./||' | LC_ALL=C sort \
  | while read -r f; do shasum -a 256 "$f"; done ) \
  | awk -v pre="$S/" '{print $1 "  " pre $2}' > .claude/plans/PLAN-166/staged-manifest.sha256

BAD=$(shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 | grep -cv ': OK$' || true)
echo "manifesto não-OK: $BAD  |  entradas: $(wc -l < .claude/plans/PLAN-166/staged-manifest.sha256 | tr -d ' ')"
[ "$BAD" = "0" ]
