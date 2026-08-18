#!/bin/bash
# PLAN-179 — LAND do pack de continuidade de contexto (Owner-run).
# Cobre W0 + W1 + W1-b (+ W2/W4 se presentes no pack) numa ÚNICA cerimônia,
# exatamente como manda a emenda 8.2 do debate round-1: o sentinel cobre
# TODOS os paths tocados, não só os ADRs.
#
# Gates (fail-closed), molde provado 3× na S313:
#   G0 janela · G1 baseline anti-stale · G2 MANIFEST do pack ·
#   G2b ESCOPO DO SENTINEL == MANIFESTO (cura da classe que abortou o W2.8:
#       lista de superfícies escrita de memória em vez de derivada) ·
#   G3 sentinel GPG (signer-pin + anchor==HEAD) ·
#   G4 simulação em clone, RC AGREGADO POR COMANDO, fora do TMPDIR ·
#   G5 apply · G6 touched-scope=vazio + checks vivos · G7 commit.
#
# Uso: bash .claude/plans/PLAN-179/OWNER-W179-LAND.sh [--dry-run]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ST=.claude/plans/PLAN-179/staged-w01
APPROVED=.claude/plans/PLAN-179/W179-approved.md
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
say() { printf '\n== %s\n' "$1"; }

[ -d "$ST" ] || { echo "ABORT: pack ausente: $ST"; exit 1; }
[ -f "$ST/MANIFEST.sha256" ] || { echo "ABORT: MANIFEST ausente"; exit 1; }
[ -f "$ST/BASELINE.sha256" ] || { echo "ABORT: BASELINE ausente"; exit 1; }

# Alvos DERIVADOS do manifesto — nunca uma lista escrita à mão.
TARGETS="$(awk '{ $1=""; sub(/^  /,""); print }' "$ST/MANIFEST.sha256")"

say "G0: confirmação de janela"
echo "   PLAN-179 W0+W1+W1-b (continuidade de contexto). Prosseguir? (yes/NO)"
read -r _ok
[ "$_ok" = "yes" ] || { echo "ABORT."; exit 1; }

say "G1: baseline anti-stale"
FAILED=0; N=0
while read -r want path; do
  [ -n "${path:-}" ] || continue
  N=$((N+1))
  if [ ! -f "$path" ]; then echo "   MISSING-LIVE: $path"; FAILED=1; continue; fi
  got=$(shasum -a 256 "$path" | awk '{print $1}')
  [ "$want" = "$got" ] || { echo "   STALE: $path"; FAILED=1; }
done < "$ST/BASELINE.sha256"
[ "$FAILED" -eq 0 ] || { echo "ABORT: main andou — re-stage por ITEM (nunca whole-file)."; exit 1; }
echo "   OK: $N/$N alvos pré-existentes idênticos ao baseline"

# Arquivos NOVOS = os do manifesto que não estão no baseline; nenhum pode existir vivo.
NEWCOUNT=0
while IFS= read -r p; do
  [ -n "$p" ] || continue
  if ! grep -qF "  $p" "$ST/BASELINE.sha256"; then
    NEWCOUNT=$((NEWCOUNT+1))
    [ ! -e "$p" ] || { echo "ABORT: STALE-NEW: $p já existe no vivo"; exit 1; }
  fi
done <<TEOF
$TARGETS
TEOF
echo "   OK: $NEWCOUNT arquivo(s) novo(s) ausente(s) no vivo"

say "G2: integridade do pack"
( cd "$ST" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || { echo "ABORT: pack não confere"; exit 1; }
echo "   OK: $(grep -c . "$ST/MANIFEST.sha256") staged conferem"

say "G2b: escopo do sentinel == manifesto (derivado, não recordado)"
[ -f "$APPROVED" ] || { echo "ABORT: assine o draft (W179-approved-draft.md)"; exit 1; }
# O bloco ```...``` sob '## Scope' do sentinel tem de ser EXATAMENTE o conjunto
# de paths do manifesto. Divergência nos DOIS sentidos é abort (o W2.8 abortou
# porque a lista humana tinha 7 onde o gate exigia 10).
SCOPE_SENTINEL=$(awk '/^## Scope/{f=1;next} f&&/^```/{c++; if(c==2) exit; next} f&&c==1{print}' "$APPROVED" | sed '/^[[:space:]]*$/d' | sort)
SCOPE_MANIFEST=$(printf '%s\n' "$TARGETS" | sed '/^[[:space:]]*$/d' | sort)
if [ "$SCOPE_SENTINEL" != "$SCOPE_MANIFEST" ]; then
  echo "ABORT: escopo do sentinel != manifesto do pack."
  echo "--- só no sentinel:"; comm -23 <(printf '%s\n' "$SCOPE_SENTINEL") <(printf '%s\n' "$SCOPE_MANIFEST") || true
  echo "--- só no manifesto:"; comm -13 <(printf '%s\n' "$SCOPE_SENTINEL") <(printf '%s\n' "$SCOPE_MANIFEST") || true
  exit 1
fi
echo "   OK: escopo idêntico ao manifesto ($(printf '%s\n' "$SCOPE_MANIFEST" | grep -c .) paths)"

say "G3: sentinel GPG"
OWNER_KEYID="CFCFACF00335DC74"
GPG_OUT=$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: gpg rc!=0"; printf '%s\n' "$GPG_OUT"; exit 1; }
printf '%s\n' "$GPG_OUT" | grep '^\[GNUPG:\] VALIDSIG ' \
  | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
  || { echo "ABORT: assinatura não é do Owner"; exit 1; }
[ "$(sed -n 's/^Anchor-SHA: //p' "$APPROVED" | head -1)" = "$(git rev-parse HEAD)" ] \
  || { echo "ABORT: anchor != HEAD — re-assine"; exit 1; }
echo "   OK: assinatura + anchor"

say "G4: simulação em clone (rc agregado por comando; fora do TMPDIR)"
SIMROOT="$HOME/.w179-landsim"; mkdir -p "$SIMROOT"
SIM=$(mktemp -d "$SIMROOT/sim.XXXXXX")
git clone --local --quiet . "$SIM/repo"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  mkdir -p "$SIM/repo/$(dirname "$p")"
  cp "$ST/$p" "$SIM/repo/$p"
done <<AEOF
$TARGETS
AEOF
G4RC=0
run_g4() {
  echo "   -> $*"
  ( cd "$SIM/repo" && "$@" ) >"$SIM/last.log" 2>&1 \
    || { echo "   G4-FAIL: $*"; tail -25 "$SIM/last.log"; G4RC=1; }
}
run_g4 python3 -m py_compile .claude/hooks/check_precompact_continuity.py \
  .claude/hooks/check_postcompact_reinject.py .claude/hooks/_lib/audit_emit.py \
  .claude/hooks/_lib/scratchpad_lib.py
run_g4 python3 -c "import json;json.load(open('.claude/settings.json'))"
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_check_compaction_continuity.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_audit_emit_api_contract.py
run_g4 bash .claude/scripts/validate-governance.sh
run_g4 shasum -a 256 -c .claude/governance/gate-scripts-manifest.txt --status
run_g4 bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
run_g4 python3 .claude/scripts/check-claude-md-claims.py
[ "$G4RC" -eq 0 ] || { echo "ABORT: G4 vermelho (rc agregado) — nada foi aplicado"; exit 1; }
echo "   OK: simulação verde (todos os comandos, não só o último)"
[ "$DRY" -eq 1 ] && { echo "DRY-RUN: parando antes do apply"; exit 0; }

say "G5: apply"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  mkdir -p "$(dirname "$p")"
  cp "$ST/$p" "$p"
  echo "   applied $p"
done <<BEOF
$TARGETS
BEOF
# hooks precisam do bit de execução (cp não o garante entre árvores)
while IFS= read -r p; do
  case "$p" in .claude/hooks/*.py) chmod +x "$p" ;; esac
done <<CEOF
$TARGETS
CEOF

say "G6: touched-scope=vazio + checks vivos"
TOUCHED=$(git status --porcelain --untracked-files=all | awk '{print $2}' | sort)
SCOPE=$(printf '%s\n%s\n%s.asc\n' "$TARGETS" "$APPROVED" "$APPROVED" | sed '/^[[:space:]]*$/d' | sort)
EXTRA=$(comm -23 <(printf '%s\n' "$TOUCHED") <(printf '%s\n' "$SCOPE") || true)
[ -z "$EXTRA" ] || { echo "ABORT: fora do escopo:"; echo "$EXTRA"; exit 1; }
G6RC=0
bash .claude/scripts/validate-governance.sh >/dev/null || G6RC=1
shasum -a 256 -c .claude/governance/gate-scripts-manifest.txt --status || G6RC=1
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests || G6RC=1
python3 .claude/scripts/check-claude-md-claims.py >/dev/null || G6RC=1
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
git add $TARGETS "$APPROVED" "$APPROVED.asc"
git commit -m "ceremony(PLAN-179 W0+W1+W1-b): continuidade de contexto — fallback por escopo de SESSÃO, Constraint Pinning por canal próprio, sonda de canal e ADR-153-AMEND-1

A prova viva do ADR-153 foi cumprida e deu NEGATIVO: o autocompact real
disparou os dois hooks e entregou nada (plan_id=unknown,
snapshot_outcome=scratchpad_unavailable, snapshot_found=false,
pointer_count=1). Causa estrutural: resolve_plan_id exige um
plan_transition da PRÓPRIA sessão — 2 eventos em 12.515 linhas. O
residual #3 do ADR era o caminho DOMINANTE.

Curas: escrita de continuidade cai para escopo de SESSÃO quando não há
plano resolvido (store separado, nunca sobrecarregando plan_id; session_id
só do input do hook, nunca de env); novo outcome written_session_scope;
restrições de governança viram CONSTANTE DE CÓDIGO entregue por canal
próprio (SessionStart matcher=compact) com orçamento separado dos
ponteiros — o cap nunca trunca governança; claim secrets-redacted, hoje
FALSA no caminho de bytes, corrigida na mesma cerimônia.

Sentinel: PLAN-179/W179-approved.md (GPG). Emenda 8.2: um sentinel, todos
os paths tocados.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
echo
echo "PRONTO. Revise 'git show --stat HEAD' e rode: git push origin main"
