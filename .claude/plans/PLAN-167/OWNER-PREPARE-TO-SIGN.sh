#!/usr/bin/env bash
# =============================================================================
# ⛔ OBSOLETO — EVIDÊNCIA HISTÓRICA DA CERIMÔNIA DO PLAN-167. NÃO EXECUTAR.
#
# Preservado (S298, PLAN-169 W0.1) apenas para reprodutibilidade documental
# do W4-approved.md commitado em ad9cc3a. Na árvore pós-PLAN-168 este script
# É PERIGOSO: a validação da assinatura antiga aborta (anchor anterior ao
# HEAD) e, se contornada, o comando de land que ele anuncia copiaria os 5
# arquivos STALE de PLAN-167/staged por cima de destinos mais novos —
# REVERTENDO o PLAN-168 (achado P1 do rail codex r1 do PLAN-169).
# =============================================================================
echo "⛔ OBSOLETO: evidência histórica do PLAN-167. Re-executar reverteria o PLAN-168. Abortando." >&2
exit 1
# ===== texto original preservado abaixo (inalcançável por design) ===========
# PLAN-167 — prepara o approved.md para assinatura.
#
#   bash .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
#
# Faz só o trabalho mecânico: confere o manifesto, fixa o Anchor-SHA no HEAD
# atual e gera W4-approved.md a partir do draft. NÃO assina — a assinatura é
# sua, com a sua chave, e é ela que autoriza a edição canônica.
# =============================================================================
set -euo pipefail

D=".claude/plans/PLAN-167"
[ -f "scripts/install.sh" ] || { echo "ABORT: rode da raiz do repositório" >&2; exit 1; }

echo "== 1. o manifesto do pack confere? =="
shasum -c "$D/staged-manifest.sha256" >/dev/null 2>&1 \
  || { echo "ABORT: o manifesto NÃO confere — não assine" >&2; exit 1; }
echo "   ok — $(wc -l < "$D/staged-manifest.sha256" | tr -d ' ') arquivos íntegros"

echo "== 2. o pack aplica sem conflito? (ensaio, não altera nada) =="
bash "$D/OWNER-W4-LAND.sh" --dry-run >/dev/null 2>&1 \
  || { echo "ABORT: o ensaio falhou — não assine" >&2; exit 1; }
echo "   ok — ensaio limpo"

echo "== 3. fixando o Anchor-SHA no HEAD atual =="
HEAD_SHA="$( git rev-parse HEAD )"
sed "s|^Anchor-SHA: .*|Anchor-SHA: $HEAD_SHA|" "$D/W4-approved-draft.md" > "$D/W4-approved.md"
grep -q "Anchor-SHA: $HEAD_SHA" "$D/W4-approved.md" \
  || { echo "ABORT: não consegui fixar o anchor" >&2; rm -f "$D/W4-approved.md"; exit 1; }
echo "   ok — $HEAD_SHA"

cat <<EOF

────────────────────────────────────────────────────────────────────
PRONTO PARA ASSINAR.

O que a sua assinatura autoriza: substituir a lógica de decisão de
propriedade em scripts/install.sh, scripts/upgrade.sh e
scripts/_framework_manifest_set.sh — código que TODO ADOTANTE executa.

Evidência: 58 de 62 células verdes, 0 regressões, 4 rodadas de revisão
cross-model. Os 4 vermelhos são deliberados (2 são defeito do TESTE) e
estão nomeados em W4-approved-draft.md.

Agora rode estes dois comandos:

  gpg --detach-sign --armor $D/W4-approved.md
  bash $D/OWNER-W4-LAND.sh

Se o gpg reclamar de "No pinentry":
  export GPG_TTY=\$(tty); gpgconf --kill gpg-agent
────────────────────────────────────────────────────────────────────
EOF
