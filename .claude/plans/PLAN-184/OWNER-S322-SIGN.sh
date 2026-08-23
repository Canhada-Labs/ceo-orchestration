#!/usr/bin/env bash
# OWNER-S322-SIGN.sh — assina o sentinel do pacote A0 (PLAN-184) + W2 (PLAN-174).
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (o gerador da W3 do PLAN-174 ainda nao emite cortes de wave — e este pacote
# JUSTAMENTE landa o wire que precede esse gerador); adaptado dos
# OWNER-S321-{SIGN,LAND}.sh, provados na S321.
#
# Este script faz UMA coisa e para: preenche Data / Approved-By / Anchor-SHA
# no sentinel e gera o `.asc`. Ele NAO toca a arvore e NAO aplica nada.
#
# Fluxo completo:
#   bash .claude/plans/PLAN-184/OWNER-S322-SIGN.sh           # 1. assina
#   bash .claude/plans/PLAN-184/OWNER-S322-LAND.sh --dry-run # 2. confere
#   bash .claude/plans/PLAN-184/OWNER-S322-LAND.sh           # 3. aplica
#   git add -u && git commit                                 # 4. commita
#   git push origin main                                     # 5. empurra
#
# ORDEM IMPORTA, e o motivo esta medido: o Anchor-SHA e o HEAD no momento da
# assinatura. Qualquer commit entre assinar e landar o invalida e o G3 aborta.
# NAO COMMITE NADA depois de rodar este script.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SENTINEL=".claude/plans/PLAN-184/wave-a0-approved.md"
PATCH=".claude/plans/PLAN-184/s322-ceremony/S322-CEREMONY.patch"

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

step "P0 — pre-condicoes"
[[ -f "$SENTINEL" ]] || die "sentinel ausente: $SENTINEL"
[[ -f "$PATCH" ]]    || die "patch ausente: $PATCH"
# A arvore tem de estar limpa para que o Anchor-SHA descreva o que sera landado.
[[ -z "$(git status --porcelain)" ]] || die "working tree SUJO — commite ANTES de assinar:
$(git status --short)"
ok "working tree limpo"

if [[ -f "$SENTINEL.asc" ]]; then
  printf '  \033[33mWARN\033[0m ja existe %s — sera SOBRESCRITO.\n' "$SENTINEL.asc"
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
  FPR="$(gpg --list-secret-keys --with-colons 2>/dev/null | awk -F: '/^fpr:/{print $10; exit}')"
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
        sys.exit("campo %s nao encontrado ou ja preenchido — inspecione %s" % (label, path))
    s = new

fill(r"^Anchor-SHA: .*$", "Anchor-SHA: " + head, "Anchor-SHA")
fill(r"^Data: .*$", "Data: " + today, "Data")
fill(r"^Approved-By: @Canhada-Labs .*$",
     "Approved-By: @Canhada-Labs " + fpr, "Approved-By")
open(path, "w", encoding="utf-8").write(s)
print("  campos preenchidos")
PY
ok "Anchor-SHA=$HEAD_SHA  Data=$TODAY"

printf '\n  Bloco que sera assinado:\n'
awk '/BEGIN SIGNED SCOPE/,/END SIGNED SCOPE/' "$SENTINEL" | sed 's/^/      /'

step "P4 — assinando"
# "No pinentry" e o modo de falha conhecido deste setup.
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
    bash .claude/plans/PLAN-184/OWNER-S322-LAND.sh --dry-run

  Se os 6 gates passarem:
    bash .claude/plans/PLAN-184/OWNER-S322-LAND.sh
    git add -u
    git commit -m "feat(PLAN-184 A0 + PLAN-174 W2): matriz de Python no push com backstop nightly + wire do ceremony-lint"

  O push leva os commits da noite S322 junto — o CI valida o conjunto.
EOF
