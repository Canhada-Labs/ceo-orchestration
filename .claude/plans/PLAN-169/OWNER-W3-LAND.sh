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
scripts/install.sh
scripts/tests/test-protocol-pointer-render.sh
.github/workflows/smoke-install.yml
.github/workflows/ownership-nightly.yml
.github/workflows/release.yml
.github/workflows/npm-publish.yml
.claude/hooks/check_anti_ceo_overhead.py
.claude/hooks/check_codex_stop_review.py
.claude/hooks/audit_log.py
.claude/hooks/check_agent_spawn.py
.claude/hooks/tests/test_codex_stop_review.py
.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
.claude/adr/ADR-186-hook-deadline-policy.md
CLAUDE.md
README.md
README.pt-BR.md
docs/CTO-GUIDE.md
docs/FAQ.md
docs/GUIA-COMPLETO.md
docs/ARCHITECTURE.md
docs/README.md
npm/README.md
RELEASE.md"
NEW_FILES=".claude/adr/ADR-191-break-glass-repo-kill-switches.md
.claude/adr/ADR-192-gate-scripts-checksum-manifest.md
.claude/governance/gate-scripts-manifest.txt
scripts/tests/test-w3-vcures.sh"

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
NB=$(grep -c . "$ST/BASELINE.sha256")
echo "   OK: $NB/$NB alvos byte-idênticos ao staging"
# Anti-stale dos NOVOS (pair-rail S300 r19): o BASELINE só cobre
# TARGETS; um NEW_FILE que passou a existir em main depois do staging
# (ex.: ADR-192 criado por outra via) seria sobrescrito sem aviso no
# G5. Novo tem que estar AUSENTE na árvore viva.
for p in $NEW_FILES; do
  if [ -e "$p" ]; then
    echo "   STALE-NEW: $p JÁ existe na árvore viva — main andou; re-stage antes de aplicar"
    FAILED=1
  fi
done
[ "$FAILED" -eq 0 ] || { echo "ABORT: NEW_FILES pré-existentes (acima)."; exit 1; }
NN=$(printf '%s\n' "$NEW_FILES" | grep -c .)
echo "   OK: $NN/$NN novos ausentes da árvore viva (nada a sobrescrever)"

say "G2: integridade do staged (MANIFEST)"
( cd "$ST" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || { echo "ABORT: staged não confere com MANIFEST"; exit 1; }
NM=$(grep -c . "$ST/MANIFEST.sha256")
echo "   OK: $NM/$NM staged conferem"

say "G3: sentinel GPG (assinatura valida E do Owner)"
OWNER_KEYID="CFCFACF00335DC74"
[ -f "$APPROVED" ] || { echo "ABORT: $APPROVED ausente — assine o draft (W3-approved-draft.md → W3-approved.md + .asc)"; exit 1; }
GPG_OUT=$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: gpg --verify rc!=0"; echo "$GPG_OUT"; exit 1; }
# Pin do SIGNATARIO (pair-rail S300 r14 P1): assinatura valida de
# QUALQUER chave do keyring nao autoriza cerimonia canonica — o
# VALIDSIG tem que terminar no keyid do Owner.
printf '%s\n' "$GPG_OUT" | grep '^\[GNUPG:\] VALIDSIG ' \
  | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
  || { echo "ABORT: sentinel assinado por chave que NAO e a do Owner ($OWNER_KEYID)"; exit 1; }
ANCHOR=$(sed -n 's/^Anchor-SHA: //p' "$APPROVED" | head -1)
HEAD_SHA=$(git rev-parse HEAD)
[ "$ANCHOR" = "$HEAD_SHA" ] \
  || { echo "ABORT: Anchor-SHA do sentinel ($ANCHOR) != HEAD ($HEAD_SHA). Re-assine sobre o HEAD atual."; exit 1; }
echo "   OK: assinatura válida + anchor == HEAD"

say "G4: simulação em clone limpo"
SIM=$(mktemp -d "${TMPDIR:-/tmp}/w3-landsim.XXXXXX")
git clone --local --quiet . "$SIM/repo"
for p in $TARGETS; do cp "$ST/$p" "$SIM/repo/$p"; done
for p in $NEW_FILES; do
  mkdir -p "$SIM/repo/$(dirname "$p")"; cp "$ST/$p" "$SIM/repo/$p"
  if [ -x "$ST/$p" ]; then chmod +x "$SIM/repo/$p"; fi
done
(
  cd "$SIM/repo"
  bash scripts/tests/test-protocol-pointer-render.sh
  bash scripts/tests/test-protocol-pointer-inv4.sh
  bash scripts/tests/test-w3-vcures.sh .
  shasum -a 256 -c .claude/governance/gate-scripts-manifest.txt --status \
    && echo "   gate-scripts: $(grep -c . .claude/governance/gate-scripts-manifest.txt)/$(grep -c . .claude/governance/gate-scripts-manifest.txt) conferem no clone"
  bash .claude/scripts/local/verify-counts.sh --quiet --no-tests \
    && echo "   verify-counts: claims coerentes com 192 ADRs no clone"
  python3 .claude/scripts/check-claude-md-claims.py \
    && echo "   check-claude-md-claims: OK no clone"
  python3 -m pytest .claude/hooks/tests/test_anti_ceo_overhead.py \
    .claude/hooks/tests/test_codex_stop_review.py \
    .claude/hooks/tests/test_check_agent_spawn*.py -q 2>&1 | tail -2
) || { echo "ABORT: bateria da simulação falhou — NADA foi aplicado na árvore viva"; exit 1; }
echo "   OK: simulação verde"
[ "$DRY" -eq 1 ] && { echo "DRY-RUN: parando antes do apply (árvore viva intocada)"; exit 0; }

say "G5: apply por tabela (com CEO_SENTINEL_UNLOCK se o hook exigir)"
for p in $TARGETS; do
  if [ -x "$p" ]; then cp "$ST/$p" "$p"; chmod +x "$p"; else cp "$ST/$p" "$p"; fi
  echo "   applied $p"
done
for p in $NEW_FILES; do
  cp "$ST/$p" "$p"
  if [ -x "$ST/$p" ]; then chmod +x "$p"; fi
  echo "   created $p"
done

say "G6: touched−scope=∅ + bateria viva"
TOUCHED=$(git status --porcelain | awk '{print $2}' | sort)
# O SENTINEL (md+asc) faz parte do registro da cerimonia e e criado
# untracked pelo proprio fluxo de assinatura — sem ele no SCOPE o G6
# abortaria SEMPRE, depois de o G5 ja ter aplicado o pack na arvore
# viva (pair-rail S300 r4 P1; defeito latente desde o staging original).
SCOPE=$(printf '%s\n%s\n%s\n%s.asc\n' "$TARGETS" "$NEW_FILES" "$APPROVED" "$APPROVED" | sort)
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

say "G7: commit (pack + sentinel assinado)"
# Re-verificacao do sentinel IMEDIATAMENTE antes do commit (pair-rail
# S300 r5 P1): entre G3 e aqui correm minutos de bateria — um sentinel
# editado nesse intervalo entraria no registro da cerimonia com
# assinatura invalida. Mesmos dois asserts do G3.
GPG_OUT7=$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: sentinel mudou apos o G3 — assinatura nao verifica mais"; exit 1; }
printf '%s\n' "$GPG_OUT7" | grep '^\[GNUPG:\] VALIDSIG ' \
  | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
  || { echo "ABORT: sentinel re-assinado por chave que NAO e a do Owner"; exit 1; }
[ "$(sed -n 's/^Anchor-SHA: //p' "$APPROVED" | head -1)" = "$(git rev-parse HEAD)" ] \
  || { echo "ABORT: anchor do sentinel != HEAD no momento do commit"; exit 1; }
git add $TARGETS $NEW_FILES "$APPROVED" "$APPROVED.asc"
git commit -m "ceremony(PLAN-169 W3): pack canonico landado — B.a allowlist+D3 loud, parity 2o fator causal, P4 advisory no apply-step, fleet F4/F8/D1/D2, curas V1/V2/V4/V5 do verdito rc.2, release.yml P2 byte-exato, W2.8 gate-scripts manifest (ADR-192), ADR-163 amend + ADR-186 nota + ADR-191 break-glass

Sentinel: PLAN-169/W3-approved.md (GPG). Escopo: $(printf '%s\n' "$TARGETS" | grep -c .) alvos + $(printf '%s\n' "$NEW_FILES" | grep -c .) novos.
Excecoes nomeadas do verdito v1.3.0-rc.2 CURADAS aqui (V1/V2/V4/V5;
probes: scripts/tests/test-w3-vcures.sh).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
echo ""
echo "PRONTO. Revise 'git show --stat HEAD' e rode: git push origin main"
