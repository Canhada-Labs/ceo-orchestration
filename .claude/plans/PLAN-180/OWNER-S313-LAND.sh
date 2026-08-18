#!/bin/bash
# PLAN-180 — LAND do trem S313 (Owner-run): cura do smoke-install vermelho
# (schema-generation pin ausente no upgrade.sh + guard de classe + wire no
# workflow) + carona PLAN-180 W3 (ADR-081 enforcement_commit + bullet
# ADR-081 no brief das lanes externas do council-audit).
#
# Gates (fail-closed), mesmo molde do OWNER-W28-LAND.sh (provado 3x na
# S313): G0 janela; G1 baseline anti-stale; G2 MANIFEST do pack; G3
# sentinel GPG (signer-pin + anchor==HEAD); G4 simulação em clone com RC
# AGREGADO POR COMANDO fora do TMPDIR symlinked do macOS; G5 apply (+ exec
# bit no teste novo); G6 touched-scope=vazio + checks vivos; G7 commit com
# sentinel re-verificado.
#
# Uso: bash .claude/plans/PLAN-180/OWNER-S313-LAND.sh [--dry-run]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ST=.claude/plans/PLAN-180/staged-s313
APPROVED=.claude/plans/PLAN-180/S313-approved.md
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
say() { printf '\n== %s\n' "$1"; }

TARGETS="scripts/upgrade.sh
.github/workflows/smoke-install.yml
.claude/adr/ADR-081-token-as-time-unit.md
.claude/workflows/council-audit.js"
NEW_FILES="scripts/tests/test-schema-generation-pins-unit.sh"

say "G0: confirmação de janela"
echo "   Trem S313 (cura smoke-install + carona PLAN-180 W3). Prosseguir? (yes/NO)"
read -r _ok
[ "$_ok" = "yes" ] || { echo "ABORT."; exit 1; }

say "G1: baseline anti-stale"
FAILED=0; N=0
while read -r want path; do
  [ -n "$path" ] || continue
  N=$((N+1))
  got=$(shasum -a 256 "$path" | awk '{print $1}')
  [ "$want" = "$got" ] || { echo "   STALE: $path"; FAILED=1; }
done < "$ST/BASELINE.sha256"
[ "$FAILED" -eq 0 ] || { echo "ABORT: main andou — re-stage."; exit 1; }
while IFS= read -r p; do
  [ -n "$p" ] || continue
  [ ! -e "$p" ] || { echo "ABORT: STALE-NEW: $p já existe no vivo"; exit 1; }
done <<NEOF
$NEW_FILES
NEOF
echo "   OK: $N/$N alvos idênticos; novos ausentes"

say "G2: integridade do pack"
( cd "$ST" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || { echo "ABORT: pack não confere"; exit 1; }
echo "   OK: $(wc -l < "$ST/MANIFEST.sha256" | tr -d ' ') staged conferem"

say "G3: sentinel GPG"
OWNER_KEYID="CFCFACF00335DC74"
[ -f "$APPROVED" ] || { echo "ABORT: assine o draft (S313-approved-draft.md)"; exit 1; }
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
SIM=$(mktemp -d "$SIMROOT/s313.XXXXXX")
git clone --local --quiet . "$SIM/repo"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  mkdir -p "$SIM/repo/$(dirname "$p")"
  cp "$ST/$p" "$SIM/repo/$p"
done <<TEOF
$TARGETS
$NEW_FILES
TEOF
chmod +x "$SIM/repo/scripts/tests/test-schema-generation-pins-unit.sh"
G4RC=0
run_g4() {
  echo "   -> $*"
  ( cd "$SIM/repo" && "$@" ) >"$SIM/last.log" 2>&1 || { echo "   G4-FAIL: $*"; tail -20 "$SIM/last.log"; G4RC=1; }
}
run_g4 bash -n scripts/upgrade.sh
# controle NEGATIVO do guard: contra o upgrade.sh de HEAD (sem a cura) tem
# de devolver 1 — um guard que passa nos dois é um guard morto (S313 pegou
# exatamente isso na 1ª versão do teste, que resolvia o root pelo path).
_neg_rc=0
( cd "$SIM/repo" && git show HEAD:scripts/upgrade.sh > "$SIM/upgrade.live.sh" \
    && UPGRADE_SH="$SIM/upgrade.live.sh" bash scripts/tests/test-schema-generation-pins-unit.sh --quiet ) >"$SIM/neg.log" 2>&1 || _neg_rc=$?
if [ "$_neg_rc" -eq 1 ]; then echo "   -> controle negativo do guard (upgrade.sh de HEAD): FAIL esperado — OK"
else echo "   G4-FAIL: controle negativo do guard devolveu rc=$_neg_rc (esperado 1) — guard morto"; G4RC=1; fi
run_g4 bash scripts/tests/test-schema-generation-pins-unit.sh --quiet
run_g4 actionlint .github/workflows/smoke-install.yml
run_g4 python3 -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"
run_g4 shasum -a 256 -c .claude/governance/gate-scripts-manifest.txt --status
run_g4 bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
run_g4 python3 .claude/scripts/check-claude-md-claims.py
run_g4 python3 -m pytest -q -p no:cacheprovider \
  .claude/hooks/tests/test_workflows_class_guard.py \
  .claude/scripts/tests/test_council_verify_semantics.py \
  .claude/scripts/tests/test_redactor_cli_matrix.py \
  .claude/hooks/_lib/tests/test_redactor_cli.py
run_g4 bash scripts/tests/test-council-grok-artifact.sh
run_g4 node scripts/tests/test-council-fixture.mjs
[ "$G4RC" -eq 0 ] || { echo "ABORT: G4 vermelho (rc agregado) — nada foi aplicado"; exit 1; }
echo "   OK: simulação verde (todos os comandos, não só o último)"
[ "$DRY" -eq 1 ] && { echo "DRY-RUN: parando antes do apply"; exit 0; }

say "G5: apply"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  mkdir -p "$(dirname "$p")"
  cp "$ST/$p" "$p"
  echo "   applied $p"
done <<AEOF
$TARGETS
$NEW_FILES
AEOF
chmod +x scripts/tests/test-schema-generation-pins-unit.sh

say "G6: touched-scope=vazio + checks vivos"
TOUCHED=$(git status --porcelain --untracked-files=all | awk '{print $2}' | sort)
SCOPE=$(printf '%s\n%s\n%s\n%s.asc\n' "$TARGETS" "$NEW_FILES" "$APPROVED" "$APPROVED" | sort)
EXTRA=$(comm -23 <(printf '%s\n' "$TOUCHED") <(printf '%s\n' "$SCOPE") || true)
[ -z "$EXTRA" ] || { echo "ABORT: fora do escopo:"; echo "$EXTRA"; exit 1; }
G6RC=0
bash scripts/tests/test-schema-generation-pins-unit.sh --quiet || G6RC=1
shasum -a 256 -c .claude/governance/gate-scripts-manifest.txt --status || G6RC=1
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
# shellcheck disable=SC2086
git add $TARGETS $NEW_FILES "$APPROVED" "$APPROVED.asc"
git commit -m "ceremony(S313): cura smoke-install — pin da geração v1.2.0/v1.3.0 do PLAN-SCHEMA no upgrade.sh + guard de classe (gerações derivadas de tags/histórico) wired no smoke-install; carona PLAN-180 W3 (ADR-081 enforcement_commit + bullet ADR-081 no brief das lanes externas)

Causa: 996d72b (PLAN-180 W0-W2) mudou PLAN-SCHEMA.md sem apendar o hash
da geração que substituiu à lista hash-gated do _refresh_schema_doc —
todo adopter na v1.2.0/v1.3.0 ficava PRESERVED (STALE), parity e2e
vermelho nos dois modos. Guard novo deriva o conjunto de gerações de
git (release tags + histórico), controle negativo no G4 do land, zero
gerações = falha de scaffold (exit 2), nunca skip verde; smoke-install
busca todas as tags v* e acende no diff dos dois schema docs.

Sentinel: PLAN-180/S313-approved.md (GPG).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
echo
echo "PRONTO. Revise 'git show --stat HEAD' e rode: git push origin main"
