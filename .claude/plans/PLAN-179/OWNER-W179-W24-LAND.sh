#!/bin/bash
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (o gerador da W3 do PLAN-174 ainda nao emite cortes de wave; o wire dele
# esta no pacote da S322). Marca adicionada pelo CEO na S322: o R1 do
# ceremony-lint apontou este arquivo como BLOCKING no mesmo instante em que
# ele passou a ser RASTREADO — untracked nao gateia, e o gate so falou depois
# do commit. E a razao pela qual a bateria de corpus roda DEPOIS do
# `git add`, nunca antes (CLAUDE.md §4).
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
# Uso: bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh [--dry-run]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ST=.claude/plans/PLAN-179/staged-w24
APPROVED=.claude/plans/PLAN-179/W179-approved.md
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
say() { printf '\n== %s\n' "$1"; }

[ -d "$ST" ] || { echo "ABORT: pack ausente: $ST"; exit 1; }
[ -f "$ST/MANIFEST.sha256" ] || { echo "ABORT: MANIFEST ausente"; exit 1; }
[ -f "$ST/BASELINE.sha256" ] || { echo "ABORT: BASELINE ausente"; exit 1; }

# Caminhos DENTRO do pack, derivados do manifesto — nunca lista escrita à mão.
# Formato: "<sha256>  <path>". Extrair por posição — `awk '{$1=""}'` reconstrói
# o registro com OFS e deixa UM espaço à esquerda (bug pego pelo G2b do W3-K
# antes de qualquer assinatura).
PACKPATHS="$(sed 's/^[0-9a-f]\{64\}  //' "$ST/MANIFEST.sha256")"

# PACKMAP: um pack path pode ter um DESTINO diferente no repo. Existe por um
# motivo só, e ele é explícito: `.claude/settings.json` nega `Edit(SPEC/**)`,
# e esse glob casa com qualquer path que contenha um segmento `SPEC/` —
# inclusive uma cópia dentro do pack. O deny está CERTO (o SPEC só é escrito
# pela cerimônia assinada), então o artefato do pack tem nome plano e o
# DESTINO real aparece aqui. Formato: `<pack-path> -> <repo-path>`.
_map_dest() {  # $1 = pack path -> ecoa o destino no repo
  local line dest
  if [ -f "$ST/PACKMAP.txt" ]; then
    line=$(grep -F -- "$1 -> " "$ST/PACKMAP.txt" | head -1 || true)
    if [ -n "$line" ]; then
      dest=${line#* -> }
      printf '%s\n' "$dest"
      return 0
    fi
  fi
  printf '%s\n' "$1"
}
TARGETS=""
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  case "$_p" in PACKMAP.txt) continue ;; esac
  TARGETS="$TARGETS$(_map_dest "$_p")
"
done <<PEOF
$PACKPATHS
PEOF
TARGETS="$(printf '%s' "$TARGETS" | sed '/^[[:space:]]*$/d')"

say "G0: confirmação de janela"
echo "   PLAN-179 W2+W4 (ledger de trabalho + governança do estado). Prosseguir? (yes/NO)"
read -r _ok
# Aceita yes/YES/Yes/y. O gate existe para exigir uma confirmação DELIBERADA,
# não para exigir a tecla shift: exigir minúscula exata custou uma cerimônia
# inteira (S313 — o Owner digitou YES depois de um dry-run verde e o land
# abortou). Qualquer coisa que não seja um "sim" explícito continua abortando.
case "$(printf '%s' "$_ok" | tr '[:upper:]' '[:lower:]')" in
  yes|y) ;;
  *) echo "ABORT."; exit 1 ;;
esac

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
  case "$p" in PACKMAP.txt) continue ;; esac
  d="$(_map_dest "$p")"
  mkdir -p "$SIM/repo/$(dirname "$d")"
  cp "$ST/$p" "$SIM/repo/$d"
done <<AEOF
$PACKPATHS
AEOF
G4RC=0
run_g4() {
  echo "   -> $*"
  ( cd "$SIM/repo" && "$@" ) >"$SIM/last.log" 2>&1 \
    || { echo "   G4-FAIL: $*"; tail -25 "$SIM/last.log"; G4RC=1; }
}
run_g4 python3 -m py_compile .claude/hooks/check_ledger_checkpoint.py \
  .claude/hooks/_lib/ledger_provenance.py .claude/hooks/_lib/audit_emit.py
run_g4 python3 -c "import json;json.load(open('.claude/settings.json'))"
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_check_ledger_checkpoint.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_ledger_provenance.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_audit_emit_api_contract.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_w5_scrub_enforcement.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_git_bypass_guard.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_codex_egress_proof_telemetry.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py
run_g4 python3 -m pytest -q -p no:cacheprovider .claude/hooks/tests/test_template_dogfood_parity.py
run_g4 python3 .claude/scripts/check-audit-registry-coverage.py --check
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
  case "$p" in PACKMAP.txt) continue ;; esac
  d="$(_map_dest "$p")"
  mkdir -p "$(dirname "$d")"
  cp "$ST/$p" "$d"
  if [ "$d" = "$p" ]; then echo "   applied $d"; else echo "   applied $d  (do pack: $p)"; fi
done <<BEOF
$PACKPATHS
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
# TODO(cerimônia W2+W4): esta mensagem é um PLACEHOLDER — preencher com a
# decisão real de GAP-3 (2 ou 3 ações registradas em audit_emit.py; se 3,
# nomear a terceira e seu residual breadcrumb) antes de assinar o sentinel.
# NÃO copiar aqui a narrativa do commit do staged-w01 (ADR-153 /
# resolve_plan_id / continuidade de contexto) — é de OUTRO pack, outra
# janela, já landado em outro commit; colar aquele texto aqui commitaria uma
# descrição falsa do que este land realmente aplica.
git commit -m "ceremony(PLAN-179 W2+W4): ledger de trabalho (check_ledger_checkpoint.py
+ ledger_provenance.py) e governança do estado durável (ADR-194)

PREENCHER antes de assinar: quais ações novas em audit_emit._KNOWN_ACTIONS
(2: ledger_checkpoint_recorded + ledger_checkpoint_skipped; ou 3, incluindo
ledger_entry_rejected — GAP-3 do README-COMO-MONTAR.md), a linha SPEC nova
(v2.59), e o resultado do check-audit-registry-coverage.py --write-golden.

Sentinel: PLAN-179/W179-approved.md (GPG). Emenda 8.2: um sentinel, todos
os paths tocados.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
echo
echo "PRONTO. Revise 'git show --stat HEAD' e rode: git push origin main"
