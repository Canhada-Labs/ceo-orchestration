#!/usr/bin/env bash
# OWNER-S321-SIGN.sh — assina o sentinel da cerimônia W1-followup (PLAN-182).
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (o gerador da W3 do PLAN-174 ainda nao emite cortes de wave); preenche os
# campos e assina, mas NAO aplica nada — o land e o OWNER-S321-LAND.sh.
#
# Este script faz UMA coisa e para: preenche Data / Approved-By / Anchor-SHA
# no sentinel e gera o `.asc`. Ele nao toca a arvore nem empurra nada.
#
# Fluxo completo, do zero ao push:
#
#   bash .claude/plans/PLAN-182/OWNER-S321-SIGN.sh          # 1. assina
#   bash .claude/plans/PLAN-182/OWNER-S321-LAND.sh --dry-run # 2. confere
#   bash .claude/plans/PLAN-182/OWNER-S321-LAND.sh           # 3. aplica
#   git add -u && git commit                                 # 4. commita
#   git push origin main                                     # 5. empurra
#
# ORDEM IMPORTA e o motivo esta medido: o Anchor-SHA e o HEAD no momento da
# assinatura. Qualquer commit entre assinar e landar o invalida, e o G3 do
# land aborta. Por isso este script e o ULTIMO passo antes do land — nao
# commite nada depois de rodar ele.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SENTINEL=".claude/plans/PLAN-182/wave-w1-followup-approved.md"
PATCH=".claude/plans/PLAN-182/w1-followup-ceremony/S321-CEREMONY.patch"

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

step "P0 — pre-condicoes"
[[ -f "$SENTINEL" ]] || die "sentinel ausente: $SENTINEL"
[[ -f "$PATCH" ]]    || die "patch ausente: $PATCH"
[[ -z "$(git status --porcelain)" ]] || die "working tree SUJO — commite ANTES de assinar:
$(git status --short)
  (assinar com a arvore suja produz um Anchor-SHA que nao descreve o que sera landado)"
ok "working tree limpo"

if [[ -f "$SENTINEL.asc" ]]; then
  printf '  \033[33mWARN\033[0m ja existe %s — ele sera SOBRESCRITO.\n' "$SENTINEL.asc"
  read -r -p "  continuar? [y/N] " a; [[ "$a" == "y" || "$a" == "Y" ]] || die "abortado pelo operador"
fi

step "P1 — binding do patch (o que voce esta assinando)"
DECLARED="$(grep -m1 '^Patch-sha256:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
ACTUAL="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
[[ "$DECLARED" == "$ACTUAL" ]] || die "o patch NAO casa o sha256 do sentinel
  no sentinel: $DECLARED
  no arquivo : $ACTUAL
  Alguem mexeu no patch. NAO assine ate reconciliar."
ok "patch casa o sha256 declarado"
printf '      %s arquivo(s) no patch:\n' "$(git apply --numstat "$PATCH" | wc -l | tr -d ' ')"
git apply --numstat "$PATCH" | awk '{printf "        %s\n", $3}'

step "P2 — identidade do signer"
FPR="${CEO_SIGNER_FPR:-}"
if [[ -z "$FPR" ]]; then
  FPR="$(gpg --list-secret-keys --with-colons 2>/dev/null \
        | awk -F: '/^fpr:/{print $10; exit}')"
fi
[[ -n "$FPR" ]] || die "nenhuma chave GPG secreta encontrada.
  Passe explicitamente:  CEO_SIGNER_FPR=<fingerprint> bash $0"
ok "signer: $FPR"

SIGNERS=".claude/sentinel-signers.txt"
if [[ -f "$SIGNERS" ]]; then
  grep -qi "$FPR" "$SIGNERS" \
    || die "o fingerprint $FPR NAO consta em $SIGNERS — o land abortaria no G1"
  ok "consta no rail rastreado"
fi

step "P3 — preenchendo os campos"
HEAD_SHA="$(git rev-parse HEAD)"
TODAY="$(date -u +%Y-%m-%d)"

python3 - "$SENTINEL" "$HEAD_SHA" "$TODAY" "$FPR" <<'PY'
import re, sys
path, head, today, fpr = sys.argv[1:5]
s = open(path, encoding="utf-8").read()

def fill(pattern, value, label):
    global s
    new, n = re.subn(pattern, value, s, count=1, flags=re.M)
    if n != 1:
        sys.exit(f"campo {label} nao encontrado ou ja preenchido — inspecione {path}")
    s = new

fill(r"^Anchor-SHA: .*$", f"Anchor-SHA: {head}", "Anchor-SHA")
fill(r"^Data: .*$", f"Data: {today}", "Data")
fill(r"^Approved-By: @Canhada-Labs .*$",
     f"Approved-By: @Canhada-Labs {fpr}", "Approved-By")
open(path, "w", encoding="utf-8").write(s)
print("  campos preenchidos")
PY
ok "Anchor-SHA=$HEAD_SHA  Data=$TODAY"

printf '\n  Bloco que sera assinado:\n'
awk '/BEGIN SIGNED SCOPE/,/END SIGNED SCOPE/' "$SENTINEL" | sed 's/^/      /'

step "P4 — assinando"
# "No pinentry" e o modo de falha conhecido deste setup (memoria do projeto).
export GPG_TTY="${GPG_TTY:-$(tty 2>/dev/null || true)}"
if command -v gpgconf >/dev/null 2>&1; then
  gpgconf --kill gpg-agent >/dev/null 2>&1 || printf ''
fi
gpg --armor --detach-sign --yes --local-user "$FPR" "$SENTINEL" \
  || die "gpg falhou.
  Modo de falha conhecido: 'No pinentry'. Rode NO SEU TERMINAL, nao via agente:
    export GPG_TTY=\$(tty); gpgconf --kill gpg-agent
  e repita."
ok "assinatura gerada: $SENTINEL.asc"

gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /'

step "PRONTO"
cat <<EOF

  A assinatura cobre o HEAD $HEAD_SHA.
  NAO commite nada agora — qualquer commit invalida o Anchor-SHA.

  Proximo passo:
    bash .claude/plans/PLAN-182/OWNER-S321-LAND.sh --dry-run

  Se os 5 gates passarem:
    bash .claude/plans/PLAN-182/OWNER-S321-LAND.sh
    git add -u
    git commit -m "feat(PLAN-182 W1-followup): cura estrutural do carrier + atribuicao + fecho da classe M4"
    git push origin main

  O push leva os 16 commits acumulados (incluindo este land) de uma vez,
  que e a ordem que voce escolheu: CI valida o conjunto completo.
EOF
