#!/bin/bash
# PLAN-169 W2.8 — LAND do trem gate-scripts + break-glass (Owner-run).
# Ratificado pelo Owner em 2026-08-18 (decisão estruturada S312):
#   (1) família W2.8 rota (b)-narrow: ADR-192 + manifesto + 4 steps;
#   (2) ADR break-glass ACEITO, renumerado 191→193 (191 tomado pelo Lote B).
#
# Gates (fail-closed): G0 janela; G1 baseline anti-stale; G2 MANIFEST do
# pack; G3 sentinel GPG (signer-pin + anchor==HEAD); G4 simulação em
# clone com RC AGREGADO POR COMANDO (cura do defeito do land W3: o
# subshell com fallback || desabilitava set -e e só o último rc
# decidia) e clone FORA do TMPDIR symlinked do macOS; G5 apply +
# manifesto REGENERADO DO VIVO no momento do land (nunca hash staged
# stale); G6 touched-scope=vazio + checks vivos; G7 commit com sentinel
# re-verificado.
#
# Uso: bash .claude/plans/PLAN-169/OWNER-W28-LAND.sh [--dry-run]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ST=.claude/plans/PLAN-169/staged-w28
APPROVED=.claude/plans/PLAN-169/W28-approved.md
MANIFEST_PATH=.claude/governance/gate-scripts-manifest.txt
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
say() { printf '\n== %s\n' "$1"; }

TARGETS=".github/workflows/release.yml
.github/workflows/npm-publish.yml
.github/workflows/smoke-install.yml
.github/workflows/ownership-nightly.yml
RELEASE.md
CLAUDE.md
README.md
README.pt-BR.md
npm/README.md
docs/CTO-GUIDE.md
docs/FAQ.md
docs/GUIA-COMPLETO.md"
NEW_ADRS=".claude/adr/ADR-192-gate-scripts-checksum-manifest.md
.claude/adr/ADR-193-break-glass-repo-kill-switches.md"
MEMBERS=".claude/scripts/local/verify-counts.sh
.claude/scripts/validate-governance.sh
.claude/scripts/local/_release_tag_guard.py
.claude/scripts/check-canonical-doc-freshness.py
scripts/tests/ownership-nightly-gate.sh
scripts/tests/ownership-expected-reds.txt
.claude/scripts/local/release.sh
.github/scripts/validate-pair-rail-verdict.py
.claude/scripts/await_release_gate.py"

regen_manifest() {
  # $1 = repo root. Regenera o manifesto SEMPRE do vivo daquele root —
  # o hash staged é referência, nunca autoridade (stale por construção).
  local root="$1" out="$1/$MANIFEST_PATH"
  mkdir -p "$root/.claude/governance"
  : > "$out"
  local m
  while IFS= read -r m; do
    [ -n "$m" ] || continue
    if [ ! -f "$root/$m" ]; then
      echo "ABORT: membro do manifesto ausente: $m" >&2; return 1
    fi
    ( cd "$root" && shasum -a 256 "$m" ) >> "$out"
  done <<MEOF
$MEMBERS
MEOF
}

say "G0: confirmação de janela"
echo "   Trem W2.8+break-glass (pós-GA v1.3.0, ratificado 2026-08-18). Prosseguir? (yes/NO)"
read -r _ok
[ "$_ok" = "yes" ] || { echo "ABORT."; exit 1; }

say "G1: baseline anti-stale"
FAILED=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  want="${line%%  *}"; path="${line#*  }"
  got=$(shasum -a 256 "$path" | awk '{print $1}')
  [ "$want" = "$got" ] || { echo "   STALE: $path"; FAILED=1; }
done < "$ST/BASELINE.sha256"
[ "$FAILED" -eq 0 ] || { echo "ABORT: main andou — re-stage."; exit 1; }
while IFS= read -r p; do
  [ -n "$p" ] || continue
  [ ! -e "$p" ] || { echo "ABORT: STALE-NEW: $p já existe no vivo"; exit 1; }
done <<NEOF
$NEW_ADRS
NEOF
[ ! -e "$MANIFEST_PATH" ] || { echo "ABORT: STALE-NEW: $MANIFEST_PATH já existe"; exit 1; }
echo "   OK: 12/12 alvos idênticos; 3/3 novos ausentes"

say "G2: integridade do pack"
( cd "$ST" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || { echo "ABORT: staged-w28 não confere"; exit 1; }
echo "   OK: $(grep -c . "$ST/MANIFEST.sha256") staged conferem"

say "G3: sentinel GPG"
OWNER_KEYID="CFCFACF00335DC74"
[ -f "$APPROVED" ] || { echo "ABORT: assine o draft (W28-approved-draft.md)"; exit 1; }
GPG_OUT=$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: gpg rc!=0"; printf '%s\n' "$GPG_OUT"; exit 1; }
printf '%s\n' "$GPG_OUT" | grep '^\[GNUPG:\] VALIDSIG ' \
  | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
  || { echo "ABORT: assinatura não é do Owner"; exit 1; }
[ "$(sed -n 's/^Anchor-SHA: //p' "$APPROVED" | head -1)" = "$(git rev-parse HEAD)" ] \
  || { echo "ABORT: anchor != HEAD — re-assine"; exit 1; }
echo "   OK: assinatura + anchor"

say "G4: simulação em clone (rc agregado por comando; fora do TMPDIR)"
SIMROOT="$HOME/.w28-landsim"
mkdir -p "$SIMROOT"
SIM=$(mktemp -d "$SIMROOT/sim.XXXXXX")
git clone --local --quiet . "$SIM/repo"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  cp "$ST/$p" "$SIM/repo/$p"
done <<TEOF
$TARGETS
$NEW_ADRS
TEOF
regen_manifest "$SIM/repo" || { echo "ABORT: regen no clone falhou"; exit 1; }
G4RC=0
run_g4() {  # rc AGREGADO por comando — a cura do defeito do land W3
  echo "   -> $*"
  ( cd "$SIM/repo" && "$@" ) || { echo "   G4-FAIL: $*"; G4RC=1; }
}
run_g4 shasum -a 256 -c "$MANIFEST_PATH" --status
run_g4 python3 -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"
run_g4 bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
run_g4 python3 .claude/scripts/check-claude-md-claims.py
[ "$G4RC" -eq 0 ] || { echo "ABORT: G4 vermelho (rc agregado) — nada foi aplicado"; exit 1; }
echo "   OK: simulação verde (todos os comandos, não só o último)"
[ "$DRY" -eq 1 ] && { echo "DRY-RUN: parando antes do apply"; exit 0; }

say "G5: apply + manifesto regenerado DO VIVO"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  mkdir -p "$(dirname "$p")"
  cp "$ST/$p" "$p"
  echo "   applied $p"
done <<AEOF
$TARGETS
$NEW_ADRS
AEOF
regen_manifest "$(pwd)" || { echo "ABORT: regen no vivo falhou"; exit 1; }
echo "   created $MANIFEST_PATH (regenerado do vivo)"

say "G6: touched-scope=vazio + checks vivos"
TOUCHED=$(git status --porcelain | awk '{print $2}' | sort)
SCOPE=$(printf '%s\n%s\n%s\n%s\n%s.asc\n' "$TARGETS" "$NEW_ADRS" "$MANIFEST_PATH" "$APPROVED" "$APPROVED" | sort)
EXTRA=$(comm -23 <(printf '%s\n' "$TOUCHED") <(printf '%s\n' "$SCOPE") || true)
[ -z "$EXTRA" ] || { echo "ABORT: fora do escopo:"; echo "$EXTRA"; exit 1; }
G6RC=0
shasum -a 256 -c "$MANIFEST_PATH" --status || G6RC=1
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests || G6RC=1
python3 .claude/scripts/check-claude-md-claims.py || G6RC=1
[ "$G6RC" -eq 0 ] || { echo "ABORT: checks vivos vermelhos"; exit 1; }
echo "   OK"

say "G7: commit"
GPG_OUT7=$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: sentinel mudou após G3"; exit 1; }
printf '%s\n' "$GPG_OUT7" | grep '^\[GNUPG:\] VALIDSIG ' \
  | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
  || { echo "ABORT: signer mudou"; exit 1; }
[ "$(sed -n 's/^Anchor-SHA: //p' "$APPROVED" | head -1)" = "$(git rev-parse HEAD)" ] \
  || { echo "ABORT: anchor != HEAD"; exit 1; }
git add $TARGETS $NEW_ADRS "$MANIFEST_PATH" "$APPROVED" "$APPROVED.asc"
git commit -m "ceremony(PLAN-169 W2.8): gate-scripts checksum manifest (ADR-192, rota (b)-narrow) + ADR-193 break-glass — 4 workflows fail-loud, manifesto regenerado no land

Ratificado pelo Owner 2026-08-18 (decisão estruturada S312, verbatim no
PLAN-169 secao OQ). ADR-193 = break-glass renumerado (191 tomado pelo
spawn-contract do Lote B). release.yml 31->32 steps (RELEASE.md idem).
Manifesto com 9 membros, hashes DO VIVO no momento do land.

Sentinel: PLAN-169/W28-approved.md (GPG).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
echo
echo "PRONTO. Revise 'git show --stat HEAD' e rode: git push origin main"
