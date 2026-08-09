#!/bin/bash
# =============================================================================
# PLAN-169 W3 — LAND do pack canônico (Owner-run, DEPOIS do GA v1.3.0).
#
# ORDEM PINADA: este pack SÓ landa após o GA da v1.3.0 (W6.1) — durante o
# hold de 24h, NENHUM commit em main. Conteúdo = v1.4.0.
#
# O que ele faz, nesta ordem, TUDO fail-closed:
#   G0  main não está congelado (você confirma interativamente)
#   G1  BASELINE anti-stale: cada alvo VIVO ainda é byte-idêntico ao que o
#       pack viu no staging — se main andou por cima de um alvo, ABORTA
#       (a lição do step1 do PLAN-166: staged stale reverte trabalho novo)
#   G2  MANIFEST: shasum -c dos 12 staged (integridade do pack)
#   G3  Sentinel GPG: W3-approved.md assinado + Scope cobre exatamente os
#       alvos (touched − scope = ∅ é verificado APÓS o apply)
#   G4  Simulação em clone: aplica o pack num git clone --local e roda a
#       bateria (render 9/9 + pytest dos hooks tocados + INV-4) ANTES de
#       tocar a árvore viva
#   G5  Apply por TABELA (cp staged → vivo), preservando modo executável
#   G6  touched − scope = ∅ + bateria na árvore viva + verify-counts
#   G7  Commit (mensagem pronta) — push fica MANUAL (pre-push roda gates)
#
# Uso:  bash .claude/plans/PLAN-169/OWNER-W3-LAND.sh [--dry-run]
#   --dry-run: para após G4 (nada toca a árvore viva).
# =============================================================================
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ST=.claude/plans/PLAN-169/staged-w3
APPROVED=.claude/plans/PLAN-169/W3-approved.md
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1

say() { printf '\n== %s\n' "$1"; }

# Tabela staged→vivo (única fonte do apply; espelha BASELINE.sha256)
TARGETS="scripts/upgrade.sh
scripts/_framework_manifest_set.sh
scripts/tests/test-protocol-pointer-render.sh
.github/workflows/smoke-install.yml
.github/workflows/ownership-nightly.yml
.claude/hooks/check_anti_ceo_overhead.py
.claude/hooks/check_codex_stop_review.py
.claude/hooks/audit_log.py
.claude/hooks/check_agent_spawn.py
.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
.claude/adr/ADR-186-hook-deadline-policy.md"
NEW_FILES=".claude/adr/ADR-191-break-glass-repo-kill-switches.md"

say "G0: confirmação de janela"
echo "   Este pack é conteúdo v1.4.0. O GA da v1.3.0 JÁ saiu e o hold acabou? (yes/NO)"
read -r _ok
[ "$_ok" = "yes" ] || { echo "ABORT: fora da janela."; exit 1; }

say "G1: baseline anti-stale (alvos vivos == o que o pack viu)"
FAILED=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  want="${line%%  *}"; path="${line#*  }"
  got=$(shasum -a 256 "$path" | awk '{print $1}')
  if [ "$want" != "$got" ]; then
    echo "   STALE: $path mudou desde o staging (esperado ${want:0:12}…, vivo ${got:0:12}…)"
    FAILED=1
  fi
done < "$ST/BASELINE.sha256"
if [ "$FAILED" -ne 0 ]; then
  echo "ABORT: main andou por cima de alvo(s) do pack — re-stage (re-rodar o"
  echo "builder da S299 sobre o HEAD novo) em vez de aplicar staged velho."
  exit 1
fi
echo "   OK: 11/11 alvos byte-idênticos ao staging"

say "G2: integridade do staged (MANIFEST)"
( cd "$ST" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || { echo "ABORT: staged não confere com MANIFEST"; exit 1; }
echo "   OK: 12/12 staged conferem"

say "G3: sentinel GPG"
[ -f "$APPROVED" ] || { echo "ABORT: $APPROVED ausente — assine o draft (W3-approved-draft.md → W3-approved.md + .asc)"; exit 1; }
GPG_OUT=$(gpg --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: gpg --verify rc!=0"; echo "$GPG_OUT"; exit 1; }
ANCHOR=$(sed -n 's/^Anchor-SHA: //p' "$APPROVED" | head -1)
HEAD_SHA=$(git rev-parse HEAD)
[ "$ANCHOR" = "$HEAD_SHA" ] \
  || { echo "ABORT: Anchor-SHA do sentinel ($ANCHOR) != HEAD ($HEAD_SHA). Re-assine sobre o HEAD atual."; exit 1; }
echo "   OK: assinatura válida + anchor == HEAD"

say "G4: simulação em clone limpo"
SIM=$(mktemp -d "${TMPDIR:-/tmp}/w3-landsim.XXXXXX")
git clone --local --quiet . "$SIM/repo"
for p in $TARGETS; do cp "$ST/$p" "$SIM/repo/$p"; done
for p in $NEW_FILES; do mkdir -p "$SIM/repo/$(dirname "$p")"; cp "$ST/$p" "$SIM/repo/$p"; done
(
  cd "$SIM/repo"
  bash scripts/tests/test-protocol-pointer-render.sh
  bash scripts/tests/test-protocol-pointer-inv4.sh
  python3 -m pytest .claude/hooks/tests/test_anti_ceo_overhead.py \
    .claude/hooks/tests/test_check_codex_stop_review.py \
    .claude/hooks/tests/test_check_agent_spawn*.py -q 2>&1 | tail -2
) || { echo "ABORT: bateria da simulação falhou — NADA foi aplicado na árvore viva"; exit 1; }
echo "   OK: simulação verde"
[ "$DRY" -eq 1 ] && { echo "DRY-RUN: parando antes do apply (árvore viva intocada)"; exit 0; }

say "G5: apply por tabela (com CEO_SENTINEL_UNLOCK se o hook exigir)"
for p in $TARGETS; do
  if [ -x "$p" ]; then cp "$ST/$p" "$p"; chmod +x "$p"; else cp "$ST/$p" "$p"; fi
  echo "   applied $p"
done
for p in $NEW_FILES; do cp "$ST/$p" "$p"; echo "   created $p"; done

say "G6: touched−scope=∅ + bateria viva"
TOUCHED=$(git status --porcelain | awk '{print $2}' | sort)
SCOPE=$(printf '%s\n%s\n' "$TARGETS" "$NEW_FILES" | sort)
EXTRA=$(comm -23 <(printf '%s\n' "$TOUCHED") <(printf '%s\n' "$SCOPE") || true)
if [ -n "$EXTRA" ]; then
  echo "ABORT: arquivos tocados FORA do escopo:"; echo "$EXTRA"
  echo "(git checkout -- <path> para reverter; investigue antes de seguir)"
  exit 1
fi
bash scripts/tests/test-protocol-pointer-render.sh
bash .claude/scripts/local/verify-counts.sh --quiet
python3 -m pytest .claude/hooks/tests/ -q 2>&1 | tail -2
echo "   OK: escopo exato + bateria viva verde"

say "G7: commit"
git add $TARGETS $NEW_FILES
git commit -m "ceremony(PLAN-169 W3): pack canonico landado — B.a allowlist+D3 loud, parity 2o fator causal, P4 advisory no apply-step, fleet F4/F8/D1/D2, ADR-163 amend + ADR-186 nota + ADR-191 break-glass

Sentinel: PLAN-169/W3-approved.md (GPG). Escopo: 11 alvos + 1 novo.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
echo ""
echo "PRONTO. Revise 'git show --stat HEAD' e rode: git push origin main"
