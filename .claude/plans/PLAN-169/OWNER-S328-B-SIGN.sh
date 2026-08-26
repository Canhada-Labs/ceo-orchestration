#!/usr/bin/env bash
# OWNER-S328-B-SIGN.sh — assina o sentinel da cerimônia wave-s328-B (PLAN-169).
# CEREMONY-LINT: handwritten-exception: clone gate-a-gate do OWNER-S328-A-SIGN.sh,
# que por sua vez espelha o OWNER-S327b-SIGN.sh ja exercitado num land REAL
# (6304f66 / 738007e); so o bloco de constantes muda. O gerador
# `.claude/scripts/generate-ceremony.sh` NAO serve aqui: ele assume o layout
# `architect/round-N/approved.md`, e esta cerimonia usa
# `PLAN-NNN/wave-*-approved.md` com land por PATCH.
# Preenche os campos e assina. NAO aplica nada — o land e o OWNER-S328-B-LAND.sh.
#
# Fluxo completo, do zero ao push (4 comandos, nenhum editor):
#
#   bash .claude/plans/PLAN-169/s328-ceremony-B/finalize-B.sh
#   bash .claude/plans/PLAN-169/OWNER-S328-B-SIGN.sh
#   bash .claude/plans/PLAN-169/OWNER-S328-B-LAND.sh --dry-run
#   bash .claude/plans/PLAN-169/OWNER-S328-B-LAND.sh
#
# O LAND faz o commit (com `-F`, sem editor) e o push. Voce nao digita `git`.
#
# ORDEM IMPORTA: o Anchor-SHA e o HEAD no momento da assinatura. Qualquer
# commit entre assinar e landar o invalida (G1 do land aborta). Este script
# e o ULTIMO passo antes do land — nao commite nada depois de roda-lo.
set -euo pipefail

# A raiz resolve por git a partir da LOCALIZACAO DO SCRIPT, nunca por `../..`
# nem pelo cwd (licao S313): o Owner pode chamar de qualquer diretorio.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes da cerimonia (o UNICO bloco que muda entre waves) ----------
PLAN_DIR=".claude/plans/PLAN-169"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-B"
SENTINEL="$PLAN_DIR/wave-s328-B-approved.md"
PATCH="$CEREMONY_DIR/B.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
LAND_SCRIPT="$PLAN_DIR/OWNER-S328-B-LAND.sh"
# O gerador do patch e COMPARTILHADO com a cerimonia do PLAN-183 e ja esta
# rastreado la; copia-lo para ca criaria um segundo original divergente.
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
# A metade NAO-CANONICA que este pacote pressupoe em HEAD.
PROFILER=".claude/scripts/profile-opus-4-7.py"
GATE_TEST=".claude/scripts/tests/test_hook_latency_relative_gate.py"
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# --- interruptor de AUTO-TESTE (recusado fora do scratchpad) ---------------
# Existe so para `s328-ceremony-B/test-ceremony-scripts-B.sh` exercitar os gates
# sem uma chave GPG. A comparacao e por REALPATH dos DOIS lados (/tmp e symlink
# no macOS: comparar formato de string mediria formato, nao caminho).
SELFTEST=0
if [ "${CEREMONY_SELFTEST_NO_GPG:-}" = "1" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  case "$ROOT" in
    "$_sp_real"/claude-501/*/scratchpad/*) SELFTEST=1 ;;
    *) die "CEREMONY_SELFTEST_NO_GPG=1 RECUSADO: a arvore
  $ROOT
  nao esta sob o scratchpad de teste ($_sp_real/claude-501/*/scratchpad/).
  Este interruptor NAO existe para a arvore viva." ;;
  esac
  printf '\033[33m  MODO AUTO-TESTE\033[0m — GPG desligado; a arvore e um clone descartavel.\n'
fi

step "P0 — pre-condicoes"
[ -f "$SENTINEL" ] || die "sentinel ausente: $SENTINEL"
[ -f "$PATCH" ]    || die "patch ausente: $PATCH
  Gere-o com:  bash $ROOT/$CEREMONY_DIR/finalize-B.sh
  (ele recria a sombra a partir do HEAD, re-aplica o patch, re-roda a bateria
   curta e chama o $FINALIZE com --sentinel/--proposed deste pacote)"
[ -f "$PROPOSED" ] || die "registro ausente: $PROPOSED"
[ -f "$ORACLE" ]   || die "oraculo de canonicidade ausente: $ORACLE"
[ -f "$BASELINE_ENV" ] || die "base esperada ausente: $BASELINE_ENV"

# A metade NAO-CANONICA tem de estar em HEAD ANTES da assinatura: o Anchor-SHA
# fixa o HEAD, e commitar o profiler DEPOIS de assinar invalidaria a ancora.
# Achado do pair-rail rodadas 1 e 2 (P1-1): sem ela, o workflow assinado passaria
# flags que o profiler nao conhece e o gate sairia 2 em todo push.
# A leitura e de `git show HEAD:` — a arvore de trabalho hoje passaria e o HEAD
# nao, entao checar a arvore mediria a coisa errada.
_head_profiler="$(git show "HEAD:$PROFILER" 2>/dev/null || printf '')"
[ -n "$_head_profiler" ] || die "$PROFILER nao existe em HEAD"
_flags="$(sed -n 's/^EXPECTED_HELP_FLAGS=//p' "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
[ -n "$_flags" ] || die "EXPECTED_HELP_FLAGS ausente em $BASELINE_ENV"
MISSING_FLAGS=""
for _flag in $_flags; do
  # Ancorado por FRONTEIRA de palavra, nunca substring: um profiler que
  # declarasse `--exec-reference-v2` e NAO `--exec-reference` passaria num
  # `grep -c -- "$_flag"` e reprovaria na CI. O caso T8 do harness planta
  # exatamente essa forma.
  _n="$(printf '%s\n' "$_head_profiler" \
        | grep -cE -- "(^|[^A-Za-z0-9_-])${_flag}([^A-Za-z0-9_-]|\$)" || true)"
  [ "$_n" -ge 1 ] || MISSING_FLAGS="$MISSING_FLAGS $_flag"
done
[ -z "$MISSING_FLAGS" ] || die "o profiler em HEAD NAO conhece a(s) flag(s):$MISSING_FLAGS
  Commite a metade NAO-CANONICA ANTES de assinar (ela nao precisa de cerimonia,
  o oraculo responde 0 para os dois):
    $PROFILER
    $GATE_TEST
  Commitar DEPOIS de assinar move o HEAD e invalida o Anchor-SHA (G1 do land)."
git show "HEAD:$GATE_TEST" >/dev/null 2>&1 \
  || die "$GATE_TEST nao existe em HEAD — a suite que o V2 do land roda nao esta commitada"
ok "metade nao-canonica presente em HEAD (profiler com as flags + teste do gate)"

# Arvore: nenhuma modificacao RASTREADA (o Anchor-SHA tem de descrever o que
# sera landado). Arquivos UNTRACKED sao tolerados SO se o oraculo de
# canonicidade responder 0 — o land stageia exatamente o patch + sentinel +
# .asc (passo S), entao um untracked nao-canonico nunca entra no commit; um
# untracked CANONICO (arquivo novo sob .claude/hooks/ etc.) aborta.
TRACKED_DIRTY=""; UNTRACKED_OK=""
while IFS= read -r -d '' entry; do
  xy="${entry:0:2}"; entry_path="${entry:3}"
  case "$xy" in
    "??")
      verdict="$(python3 "$ORACLE" --is-canonical "$entry_path" 2>/dev/null | awk -F'\t' 'NR==1{print $2}')"
      case "$verdict" in
        0) UNTRACKED_OK="$UNTRACKED_OK  $entry_path
" ;;
        1) die "arquivo UNTRACKED em path CANONICO: $entry_path — commite-o por cerimonia propria ou remova antes de assinar" ;;
        *) die "oraculo nao respondeu 0|1 para: $entry_path" ;;
      esac ;;
    *R*|*C*) IFS= read -r -d '' _from || true; TRACKED_DIRTY="$TRACKED_DIRTY  $xy $entry_path
" ;;
    *) TRACKED_DIRTY="$TRACKED_DIRTY  $xy $entry_path
" ;;
  esac
done < <(git status --porcelain=v1 -z)
[ -z "$TRACKED_DIRTY" ] || die "modificacoes RASTREADAS na arvore — commite ANTES de assinar:
$TRACKED_DIRTY  (assinar com a arvore suja produz um Anchor-SHA que nao descreve o que sera landado)"
if [ -n "$UNTRACKED_OK" ]; then
  printf '  \033[33mNOTA\033[0m untracked nao-canonicos tolerados (nao entram no land):\n%s' "$UNTRACKED_OK"
fi
ok "nenhuma modificacao rastreada; untracked (se houver) sao nao-canonicos"

# Os materiais da cerimonia tem de estar COMMITADOS antes de assinar (pair-rail
# r9 P2 da S326): o LAND exige-os rastreados, e commita-los DEPOIS da assinatura
# muda o HEAD e invalida o Anchor-SHA (G1). Mesma lista do LAND.
MATERIALS=(
  "$PLAN_DIR/OWNER-S328-B-SIGN.sh"
  "$LAND_SCRIPT"
  "$PROPOSED"
  "$CEREMONY_DIR/COMMIT-MSG-B.txt"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-B.sh"
  "$CEREMONY_DIR/test-ceremony-scripts-B.sh"
  "$CEREMONY_DIR/README-B.md"
  "$FINALIZE"
  "$PATCH"
  "$SENTINEL"
)
MISSING=""
for m in "${MATERIALS[@]}"; do
  if ! git ls-files --error-unmatch -- "$m" >/dev/null 2>&1; then
    MISSING="$MISSING  $m
"
  fi
done
[ -z "$MISSING" ] || die "material(is) de cerimonia NAO commitado(s):
$MISSING  Commite os materiais ANTES de assinar (commitar depois muda o HEAD e invalida a ancora)."
RAIL_COUNT=0
for r in $RAIL_GLOB; do
  [ -f "$r" ] || continue
  git ls-files --error-unmatch -- "$r" >/dev/null 2>&1 \
    || die "registro de rail NAO commitado: $r — commite ANTES de assinar"
  RAIL_COUNT=$(( RAIL_COUNT + 1 ))
done
[ "$RAIL_COUNT" -gt 0 ] || die "nenhum registro de rail em $RAIL_GLOB — o V2 do PROTOCOL exige pelo menos uma rodada registrada"
ok "materiais e $RAIL_COUNT registro(s) de rail rastreados"

case "$(cat "$SENTINEL")" in
  *TO-FILL-AT-FINAL-PATCH*)
    die "o sentinel ainda tem placeholder TO-FILL-AT-FINAL-PATCH — rode o finalize-B.sh primeiro" ;;
esac
case "$(cat "$SENTINEL")" in
  *"  - placeholder"*)
    die "o bloco Scope ainda e placeholder — rode o finalize-B.sh primeiro" ;;
esac
ok "sentinel finalizado (sem placeholders de patch)"

if [ -f "$SENTINEL.asc" ]; then
  printf '  \033[33mWARN\033[0m ja existe %s — ele sera SOBRESCRITO.\n' "$SENTINEL.asc"
  if [ "$SELFTEST" = "0" ]; then
    read -r -p "  continuar? [y/N] " a
    case "$a" in y|Y) : ;; *) die "abortado pelo operador" ;; esac
  fi
fi

step "P1 — binding do patch (o que voce esta assinando)"
DECLARED="$(grep -m1 '^Patch-sha256:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
ACTUAL="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
[ "$DECLARED" = "$ACTUAL" ] || die "o patch NAO casa o sha256 do sentinel
  no sentinel: $DECLARED
  no arquivo : $ACTUAL
  Alguem mexeu no patch. NAO assine ate reconciliar."
ok "patch casa o sha256 do sentinel"

# O MESMO sha tem de constar do registro PROPOSED-PATCH.md: o registro e o que
# a revisao leu; um registro apontando para outro patch e evidencia falsa.
PROPOSED_SHA="$(grep -m1 '^Patch-sha256:' "$PROPOSED" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
[ -n "$PROPOSED_SHA" ] || die "$PROPOSED sem campo Patch-sha256"
[ "$PROPOSED_SHA" = "$ACTUAL" ] || die "o registro de revisao aponta para OUTRO patch
  em $PROPOSED: $PROPOSED_SHA
  no arquivo         : $ACTUAL"
ok "PROPOSED-PATCH.md aponta para o mesmo patch"

# A base contra a qual o patch foi gerado nao precisa ser o HEAD literal — o
# commit dos MATERIAIS acontece depois de finalizar o patch e move o HEAD de
# proposito. O que precisa valer e mais preciso do que igualdade:
#   (1) a base e ancestral do HEAD (nao e uma linha paralela), e
#   (2) NENHUM path que o patch toca mudou entre a base e o HEAD.
HEAD_SHA="$(git rev-parse HEAD)"
PATCH_BASE="$(grep -m1 '^Patch-base:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
[ -n "$PATCH_BASE" ] || die "sentinel sem campo Patch-base (o finalize_patch.py grava)"
git merge-base --is-ancestor "$PATCH_BASE" "$HEAD_SHA" \
  || die "a base do patch NAO e ancestral do HEAD
  Patch-base: $PATCH_BASE
  HEAD atual: $HEAD_SHA
  A arvore andou por outro caminho. Refinalize (finalize-B.sh) e repita."
DRIFT_TMP="$(mktemp)"
git diff --name-only "$PATCH_BASE" "$HEAD_SHA" | sort -u > "$DRIFT_TMP"
TOUCHED_TMP="$(mktemp)"
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$TOUCHED_TMP"
DRIFTED="$(comm -12 "$DRIFT_TMP" "$TOUCHED_TMP")"
rm -f "$DRIFT_TMP" "$TOUCHED_TMP"
if [ -n "$DRIFTED" ]; then
  die "path(s) do patch mudaram entre a base e o HEAD:
$(printf '  %s\n' $DRIFTED)
  O patch foi revisado sobre outro conteudo. Refinalize e repita."
fi
ok "base $PATCH_BASE e ancestral do HEAD e nenhum path do patch derivou"

# BASE-SHA.txt e material RASTREADO do pacote: se ele discorda do Patch-base
# assinado, um dos dois e residuo de uma finalizacao anterior. Fail-closed —
# evidencia que se contradiz nao e evidencia.
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
RECORDED_BASE="$(sed -n 's/^[[:space:]]*\([0-9a-f]\{40\}\)[[:space:]]*$/\1/p' "$BASE_SHA_FILE" | head -1)"
[ -n "$RECORDED_BASE" ] || die "$BASE_SHA_FILE nao contem um sha de 40 hex"
[ "$RECORDED_BASE" = "$PATCH_BASE" ] || die "BASE-SHA.txt discorda do Patch-base do sentinel
  em $BASE_SHA_FILE: $RECORDED_BASE
  no sentinel        : $PATCH_BASE
  Rode o finalize-B.sh de novo (ele reescreve os dois)."
ok "BASE-SHA.txt casa o Patch-base assinado"

git apply --check "$PATCH" || die "git apply --check FALHOU — a arvore divergiu do patch"
ok "o patch aplica limpo na arvore atual"

PATCH_FILES="$(git apply --numstat "$PATCH" | wc -l | tr -d ' ')"
printf '      %s arquivo(s) no patch:\n' "$PATCH_FILES"
git apply --numstat "$PATCH" | awk '{printf "        %s\n", $3}'

step "P2 — identidade do signer"
if [ "$SELFTEST" = "1" ]; then
  FPR="SELFTEST0000000000000000000000000000000000"
  printf '  \033[33mAUTO-TESTE\033[0m signer sintetico: %s\n' "$FPR"
else
  FPR="${CEO_SIGNER_FPR:-}"
  if [ -z "$FPR" ]; then
    FPR="$(gpg --list-secret-keys --with-colons 2>/dev/null \
          | awk -F: '/^fpr:/{print $10; exit}')"
  fi
  [ -n "$FPR" ] || die "nenhuma chave GPG secreta encontrada.
  Passe explicitamente:  CEO_SIGNER_FPR=<fingerprint> bash $0"
  ok "signer: $FPR"

  if [ -f "$SIGNERS" ]; then
    grep -qi "$FPR" "$SIGNERS" \
      || die "o fingerprint $FPR NAO consta em $SIGNERS — o land abortaria no G1"
    ok "consta no rail rastreado"
  fi
fi

step "P3 — preenchendo os campos"
TODAY="$(date -u +%Y-%m-%d)"

python3 - "$SENTINEL" "$HEAD_SHA" "$TODAY" "$FPR" <<'PY'
import re, sys
path, head, today, fpr = sys.argv[1:5]
s = open(path, encoding="utf-8").read()

def fill(pattern, value, label):
    global s
    new, n = re.subn(pattern, value, s, count=1, flags=re.M)
    if n != 1:
        sys.exit("campo %s nao encontrado ou ja preenchido - inspecione %s"
                 % (label, path))
    s = new

fill(r"^Anchor-SHA: TO-FILL-AT-SIGN$", "Anchor-SHA: %s" % head, "Anchor-SHA")
fill(r"^Data: TO-FILL-AT-SIGN$", "Data: %s" % today, "Data")
fill(r"^Approved-By: @Canhada-Labs TO-FILL-AT-SIGN$",
     "Approved-By: @Canhada-Labs %s" % fpr, "Approved-By")
open(path, "w", encoding="utf-8").write(s)
print("  campos preenchidos")
PY
ok "Anchor-SHA=$HEAD_SHA  Data=$TODAY"

printf '\n  Bloco que sera assinado:\n'
awk '/BEGIN SIGNED SCOPE/,/END SIGNED SCOPE/' "$SENTINEL" | sed 's/^/      /'

step "P4 — assinando"
if [ "$SELFTEST" = "1" ]; then
  printf 'SELFTEST-NOT-A-SIGNATURE\n' > "$SENTINEL.asc"
  ok "AUTO-TESTE: .asc sintetico gerado (nao e assinatura)"
else
  # "No pinentry" e o modo de falha conhecido deste setup (memoria do projeto).
  export GPG_TTY="${GPG_TTY:-$(tty 2>/dev/null || true)}"
  if command -v gpgconf >/dev/null 2>&1; then
    gpgconf --kill gpg-agent >/dev/null 2>&1 || printf ''
  fi
  if ! gpg --armor --detach-sign --yes --local-user "$FPR" "$SENTINEL"; then
    # O P3 ja reescreveu o sentinel; sem este rollback um re-run abortaria no
    # P0 ("modificacao rastreada") e a recuperacao seria manual (pair-rail r9
    # P2 da S326). Restaura o sentinel do HEAD, byte a byte, e sai.
    git checkout -- "$SENTINEL"
    rm -f -- "$SENTINEL.asc"
    die "gpg falhou — sentinel RESTAURADO do HEAD (nada assinado).
  Modo de falha conhecido: 'No pinentry'. Rode NO SEU TERMINAL, nao via agente:
    export GPG_TTY=\$(tty); gpgconf --kill gpg-agent
  e repita este script do zero."
  fi
  ok "assinatura gerada: $SENTINEL.asc"
  gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /'
fi

step "PRONTO"
cat <<EOF

  A assinatura cobre o HEAD $HEAD_SHA.
  NAO commite nada agora — qualquer commit invalida o Anchor-SHA.

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$LAND_SCRIPT --dry-run

  Se todos os gates passarem, o comando seguinte aplica, verifica, commita e
  empurra (voce nao digita 'git' em momento nenhum):

    bash $ROOT/$LAND_SCRIPT
EOF
