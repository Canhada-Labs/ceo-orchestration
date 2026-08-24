#!/usr/bin/env bash
# OWNER-S326-SIGN.sh — assina o sentinel da cerimônia wave-cli (PLAN-182).
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (espelha o OWNER-S321-SIGN.sh; o gerador ainda nao emite cortes de wave).
# Preenche os campos e assina. NAO aplica nada — o land e o OWNER-S326-LAND.sh.
#
# Fluxo completo, do zero ao push:
#
#   bash .claude/plans/PLAN-182/OWNER-S326-SIGN.sh          # 1. assina
#   bash .claude/plans/PLAN-182/OWNER-S326-LAND.sh --dry-run # 2. confere
#   bash .claude/plans/PLAN-182/OWNER-S326-LAND.sh           # 3. aplica + STAGING (incl. o .asc)
#   git commit                                               # 4. commita (mensagem sugerida pelo land)
#   git push origin main                                     # 5. empurra
#
# ORDEM IMPORTA: o Anchor-SHA e o HEAD no momento da assinatura. Qualquer
# commit entre assinar e landar o invalida (G3 do land aborta). Este script
# e o ULTIMO passo antes do land — nao commite nada depois de roda-lo.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SENTINEL=".claude/plans/PLAN-182/wave-cli-approved.md"
PATCH=".claude/plans/PLAN-182/cli-ceremony/S326-CLI-CEREMONY.patch"

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

step "P0 — pre-condicoes"
[[ -f "$SENTINEL" ]] || die "sentinel ausente: $SENTINEL"
[[ -f "$PATCH" ]]    || die "patch ausente: $PATCH"
# Arvore: nenhuma modificacao RASTREADA (o Anchor-SHA tem de descrever o que
# sera landado). Arquivos UNTRACKED sao tolerados SO se o oraculo de
# canonicidade responder 0 — o land stageia exatamente o patch + sentinel +
# .asc (passo S), entao um untracked nao-canonico nunca entra no commit; um
# untracked CANONICO (arquivo novo sob .claude/hooks/ etc.) aborta.
ORACLE=".claude/hooks/check_canonical_edit.py"
[[ -f "$ORACLE" ]] || die "oraculo de canonicidade ausente: $ORACLE"
TRACKED_DIRTY=""; UNTRACKED_OK=""
while IFS= read -r -d '' entry; do
  xy="${entry:0:2}"; entry_path="${entry:3}"
  case "$xy" in
    "??")
      verdict="$(python3 "$ORACLE" --is-canonical "$entry_path" 2>/dev/null | awk -F'\t' 'NR==1{print $2}')"
      case "$verdict" in
        0) UNTRACKED_OK+="  $entry_path"$'\n' ;;
        1) die "arquivo UNTRACKED em path CANONICO: $entry_path — commite-o por cerimonia propria ou remova antes de assinar" ;;
        *) die "oraculo nao respondeu 0|1 para: $entry_path" ;;
      esac ;;
    *R*|*C*) IFS= read -r -d '' _from || true; TRACKED_DIRTY+="  $xy $entry_path"$'\n' ;;
    *) TRACKED_DIRTY+="  $xy $entry_path"$'\n' ;;
  esac
done < <(git status --porcelain=v1 -z)
[[ -z "$TRACKED_DIRTY" ]] || die "modificacoes RASTREADAS na arvore — commite ANTES de assinar:
$TRACKED_DIRTY  (assinar com a arvore suja produz um Anchor-SHA que nao descreve o que sera landado)"
if [[ -n "$UNTRACKED_OK" ]]; then
  printf '  \033[33mNOTA\033[0m untracked nao-canonicos tolerados (nao entram no land):\n%s' "$UNTRACKED_OK"
fi
ok "nenhuma modificacao rastreada; untracked (se houver) sao nao-canonicos"
grep -q 'TO-FILL-AT-FINAL-PATCH' "$SENTINEL" && die "Patch-sha256 ainda e placeholder — o patch nao foi finalizado"

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

fill(r"^Anchor-SHA: TO-FILL-AT-SIGN$", f"Anchor-SHA: {head}", "Anchor-SHA")
fill(r"^Data: TO-FILL-AT-SIGN$", f"Data: {today}", "Data")
fill(r"^Approved-By: @Canhada-Labs TO-FILL-AT-SIGN$",
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
    bash .claude/plans/PLAN-182/OWNER-S326-LAND.sh --dry-run

  Se os gates passarem:
    bash .claude/plans/PLAN-182/OWNER-S326-LAND.sh   (aplica, verifica e faz o staging — incl. o .asc)
    git commit   (mensagem sugerida ao fim do land)
    git push origin main
EOF
