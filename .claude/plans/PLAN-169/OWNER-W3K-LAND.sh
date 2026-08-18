#!/bin/bash
# PLAN-169 W3-K — LAND da cerimônia de KERNEL (Owner-run).
#
# ⚠️  U-3 (regra do próprio PLAN-169): editar o kernel exige
# CEO_KERNEL_OVERRIDE + CEO_KERNEL_OVERRIDE_ACK ALÉM do sentinel. Duas
# cerimônias com posturas de override diferentes na MESMA sessão é onde um
# `export` sobra no ambiente e autoriza o pack seguinte sem ninguém pedir.
# Por isso: este script EXPORTA o override ele mesmo, no menor escopo
# possível, faz `unset` explícito no fim E instala um trap EXIT como
# backstop — e recusa rodar se o override já vier do ambiente do Owner.
#
# Gates: G0 janela · G0b higiene de override · G1 baseline · G2 manifesto ·
#        G2b escopo do sentinel == manifesto · G3 sentinel GPG ·
#        G4 simulação em clone (rc agregado) · G5 apply · G6 escopo vazio +
#        checks vivos · G7 commit.
#
# Uso: bash .claude/plans/PLAN-169/OWNER-W3K-LAND.sh [--dry-run]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ST=.claude/plans/PLAN-169/staged-w3k
APPROVED=.claude/plans/PLAN-169/W3K-approved.md
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
say() { printf '\n== %s\n' "$1"; }

# Backstop: aconteça o que acontecer, o override não sobrevive a este script.
_cleanup() { unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK 2>/dev/null || true; }
trap _cleanup EXIT

[ -d "$ST" ] || { echo "ABORT: pack ausente: $ST"; exit 1; }
[ -f "$ST/MANIFEST.sha256" ] || { echo "ABORT: MANIFEST ausente"; exit 1; }
[ -f "$ST/BASELINE.sha256" ] || { echo "ABORT: BASELINE ausente"; exit 1; }

# Formato do manifesto: "<sha256>  <path>". Extrair por posição do separador —
# `awk '{$1=""}'` reconstrói o registro com OFS e deixa UM espaço à esquerda,
# que o gate G2b detectou como divergência de escopo antes do Owner assinar.
TARGETS="$(sed 's/^[0-9a-f]\{64\}  //' "$ST/MANIFEST.sha256")"

say "G0: confirmação de janela"
echo "   PLAN-169 W3-K — CERIMÔNIA DE KERNEL (override necessário)."
echo "   Esta é uma sessão DEDICADA: não encadeie com outra cerimônia. Prosseguir? (yes/NO)"
read -r _ok
[ "$_ok" = "yes" ] || { echo "ABORT."; exit 1; }

say "G0b: higiene de override"
# Se o override JÁ estiver no ambiente, ele veio de outra cerimônia — é
# exatamente o vazamento que a U-3 descreve. Recusar é o comportamento certo.
if [ -n "${CEO_KERNEL_OVERRIDE:-}" ] || [ -n "${CEO_KERNEL_OVERRIDE_ACK:-}" ]; then
  echo "ABORT: CEO_KERNEL_OVERRIDE/_ACK já estão no ambiente ANTES deste script."
  echo "       Isso é o vazamento que a regra U-3 previne. Abra um shell limpo."
  exit 1
fi
echo "   OK: ambiente limpo — o override nasce e morre dentro deste script"

say "G1: baseline anti-stale"
FAILED=0; N=0
while read -r want path; do
  [ -n "${path:-}" ] || continue
  N=$((N+1))
  if [ ! -f "$path" ]; then echo "   MISSING-LIVE: $path"; FAILED=1; continue; fi
  got=$(shasum -a 256 "$path" | awk '{print $1}')
  [ "$want" = "$got" ] || { echo "   STALE: $path"; FAILED=1; }
done < "$ST/BASELINE.sha256"
[ "$FAILED" -eq 0 ] || { echo "ABORT: main andou — re-stage por ITEM."; exit 1; }
while IFS= read -r p; do
  [ -n "$p" ] || continue
  grep -qF "  $p" "$ST/BASELINE.sha256" || { [ ! -e "$p" ] || { echo "ABORT: STALE-NEW: $p já existe"; exit 1; }; }
done <<TEOF
$TARGETS
TEOF
echo "   OK: $N/$N alvos pré-existentes idênticos"

say "G2: integridade do pack"
( cd "$ST" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || { echo "ABORT: pack não confere"; exit 1; }
echo "   OK: $(grep -c . "$ST/MANIFEST.sha256") staged conferem"

say "G2b: escopo do sentinel == manifesto"
[ -f "$APPROVED" ] || { echo "ABORT: assine o draft (W3K-approved-draft.md)"; exit 1; }
SCOPE_S=$(awk '/^## Scope/{f=1;next} f&&/^```/{c++; if(c==2) exit; next} f&&c==1{print}' "$APPROVED" | sed '/^[[:space:]]*$/d' | sort)
SCOPE_M=$(printf '%s\n' "$TARGETS" | sed '/^[[:space:]]*$/d' | sort)
[ "$SCOPE_S" = "$SCOPE_M" ] || { echo "ABORT: escopo do sentinel != manifesto"; diff <(printf '%s\n' "$SCOPE_S") <(printf '%s\n' "$SCOPE_M") || true; exit 1; }
echo "   OK: escopo idêntico ao manifesto"

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

say "G4: simulação em clone (rc agregado; fora do TMPDIR)"
SIMROOT="$HOME/.w3k-landsim"; mkdir -p "$SIMROOT"
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
run_g4() { echo "   -> $*"; ( cd "$SIM/repo" && "$@" ) >"$SIM/last.log" 2>&1 \
  || { echo "   G4-FAIL: $*"; tail -25 "$SIM/last.log"; G4RC=1; }; }
run_g4 python3 -m py_compile .claude/hooks/check_arbitration_kernel.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_arbitration_kernel_grant_emit.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_check_arbitration_kernel_v214.py
run_g4 bash .claude/scripts/validate-governance.sh
run_g4 shasum -a 256 -c .claude/governance/gate-scripts-manifest.txt --status
run_g4 bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
[ "$G4RC" -eq 0 ] || { echo "ABORT: G4 vermelho — nada foi aplicado"; exit 1; }
echo "   OK: simulação verde"
[ "$DRY" -eq 1 ] && { echo "DRY-RUN: parando antes do apply"; exit 0; }

say "G5: apply COM override de kernel (escopo mínimo)"
export CEO_KERNEL_OVERRIDE="PLAN-169 W3-K — audit do grant de override de kernel (sentinel W3K-approved.md)"
export CEO_KERNEL_OVERRIDE_ACK=1
while IFS= read -r p; do
  [ -n "$p" ] || continue
  mkdir -p "$(dirname "$p")"
  cp "$ST/$p" "$p"
  case "$p" in .claude/hooks/*.py) chmod +x "$p" ;; esac
  echo "   applied $p"
done <<BEOF
$TARGETS
BEOF
_cleanup
echo "   override DESARMADO imediatamente após o apply"

say "G6: touched-scope=vazio + checks vivos"
TOUCHED=$(git status --porcelain --untracked-files=all | awk '{print $2}' | sort)
SCOPE=$(printf '%s\n%s\n%s.asc\n' "$TARGETS" "$APPROVED" "$APPROVED" | sed '/^[[:space:]]*$/d' | sort)
EXTRA=$(comm -23 <(printf '%s\n' "$TOUCHED") <(printf '%s\n' "$SCOPE") || true)
[ -z "$EXTRA" ] || { echo "ABORT: fora do escopo:"; echo "$EXTRA"; exit 1; }
G6RC=0
bash .claude/scripts/validate-governance.sh >/dev/null || G6RC=1
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests || G6RC=1
[ "$G6RC" -eq 0 ] || { echo "ABORT: checks vivos vermelhos"; exit 1; }
[ -z "${CEO_KERNEL_OVERRIDE:-}${CEO_KERNEL_OVERRIDE_ACK:-}" ] \
  || { echo "ABORT: override ainda armado após o apply — não commito nesse estado"; exit 1; }
echo "   OK (override confirmado desarmado)"

say "G7: commit"
GPG_OUT7=$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: sentinel mudou após G3"; exit 1; }
printf '%s\n' "$GPG_OUT7" | grep -q '^\[GNUPG:\] VALIDSIG ' || { echo "ABORT: sentinel inválido"; exit 1; }
# shellcheck disable=SC2086
git add $TARGETS "$APPROVED" "$APPROVED.asc"
git commit -m "ceremony(PLAN-169 W3-K): auditoria do grant de override de kernel — branch morto revivido + teste POSITIVO

O ledger suspeitava de emit engolido por \`except Exception: pass\` com
\`ceremony_sha\` recebendo um PATH. A reprodução hermética mostrou que a
premissa estava ERRADA: \`kernel_extension_landed\` está no passthrough do
emit_generic e LANDA normalmente (hmac_error nulo).

O defeito real é outro e é pior: o branch que deveria auditar o uso do
override testa \`decision == \"allow\"\` sobre o JSON que o próprio
\`_emit_allow()\` produz — e esse JSON nunca carrega a chave \`decision\`
(por contrato do harness, \"allow\" no topo é inválido). \`git log -S\`
mostra que a condição nasceu morta: nunca houve regressão. Resultado: o
systemMessage do hook manda o operador procurar um evento
(\`veto_triggered reason_code=kernel_override_used\`) que nunca foi escrito
— uso de override de kernel não era auditado pelo canal documentado.

Cura + o teste POSITIVO que faltava (só o caminho de BLOCK era provado),
com controle negativo no mesmo arquivo.

Sentinel: PLAN-169/W3K-approved.md (GPG). Override de kernel armado e
desarmado dentro do land script, com trap EXIT de backstop (U-3).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
echo
echo "PRONTO. Revise 'git show --stat HEAD' e rode: git push origin main"
