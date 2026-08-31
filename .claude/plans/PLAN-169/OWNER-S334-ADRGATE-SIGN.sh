#!/usr/bin/env bash
# OWNER-S334-ADRGATE-SIGN.sh — assina o sentinel da cerimonia wave-adrgate (PLAN-169).
# CEREMONY-LINT: handwritten-exception: clone gate-a-gate do OWNER-S331-F-SIGN.sh,
# que assinou um land REAL (303ae55); muda o bloco de constantes, o P0-e le o
# veredito do rail em s334-ceremony-adrgate/ e o P0-f troca a checagem de jq
# (que esta wave nao usa) pelo substrato do V3 (o import do checker de cadeia).
# O P0-b (a cura pontual do docs/threat-model.md, portada do
# OWNER-S328-MORNING.sh) segue sem mudanca. O gerador
# `.claude/scripts/generate-ceremony.sh` NAO serve aqui: ele assume o layout
# `architect/round-N/approved.md`, e esta cerimonia usa
# `PLAN-NNN/wave-*-approved.md` com land por PATCH.
# Preenche os campos e assina. NAO aplica nada — o land e o OWNER-S334-ADRGATE-LAND.sh.
#
# Fluxo completo, do zero ao push (4 comandos, nenhum editor):
#
#   bash .claude/plans/PLAN-169/s334-ceremony-adrgate/finalize-adrgate.sh
#   bash .claude/plans/PLAN-169/OWNER-S334-ADRGATE-SIGN.sh
#   bash .claude/plans/PLAN-169/OWNER-S334-ADRGATE-LAND.sh --dry-run
#   bash .claude/plans/PLAN-169/OWNER-S334-ADRGATE-LAND.sh
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
CEREMONY_DIR="$PLAN_DIR/s334-ceremony-adrgate"
SENTINEL="$PLAN_DIR/wave-adrgate-approved.md"
PATCH="$CEREMONY_DIR/ADRGATE.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
LAND_SCRIPT="$PLAN_DIR/OWNER-S334-ADRGATE-LAND.sh"
# O gerador do patch e COMPARTILHADO com a cerimonia do PLAN-183 e ja esta
# rastreado la; copia-lo para ca criaria um segundo original divergente.
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
THREAT_MODEL="docs/threat-model.md"
CHAIN_SCRIPT=".claude/scripts/check-adr-chain.py"
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
warn(){ printf '  \033[33mWARN\033[0m %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# --- interruptor de AUTO-TESTE (recusado fora do scratchpad) ---------------
# Existe so para `s334-ceremony-adrgate/test-ceremony-scripts-adrgate.sh`
# exercitar os gates sem uma chave GPG. A comparacao e por REALPATH dos DOIS
# lados (/tmp e symlink no macOS: comparar formato de string mediria formato,
# nao caminho).
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

# ---------------------------------------------------------------------------
step "P0 — pre-condicoes"
# ---------------------------------------------------------------------------
[ -f "$SENTINEL" ] || die "sentinel ausente: $SENTINEL"
[ -f "$PATCH" ]    || die "patch ausente: $PATCH
  Gere-o com:  bash $ROOT/$CEREMONY_DIR/finalize-adrgate.sh
  (ele deriva o patch da arvore-sombra, re-baseia no HEAD vivo, roda a bateria
   curta e chama o $FINALIZE com --sentinel/--proposed deste pacote)"
[ -f "$PROPOSED" ] || die "registro ausente: $PROPOSED"
[ -f "$ORACLE" ]   || die "oraculo de canonicidade ausente: $ORACLE"
[ -f "$BASELINE_ENV" ] || die "base esperada ausente: $BASELINE_ENV"

# ---------------------------------------------------------------------------
# P0-b — docs/threat-model.md: sujeira que NINGUEM editou.
# ---------------------------------------------------------------------------
# `.claude/scripts/check-threat-model-freshness.py` reescreve o arquivo como
# EFEITO COLATERAL de rodar: `flip_status_to_stale` (`:179-200`) aplica
# `re.sub(r"^(\*\*Status:\*\*)\s+accepted", r"\1 stale", count=1)` e sai 1.
# Como o P0 recusa arvore com modificacao RASTREADA, essa sujeira abortaria a
# cerimonia acusando um arquivo que ninguem tocou (medido na manha da S328).
#
# A cura e PONTUAL e provada por CONTEUDO: so este path, so quando ele e a
# UNICA modificacao rastreada, so quando esta NAO-staged, e so quando o diff e
# exatamente a troca de status na DIRECAO que o checker escreve. Aceitar
# `stale` -> `accepted` reverteria em silencio a edicao de quem RE-ACEITOU o
# modelo de ameacas de proposito — o trabalho que esta cura existe para nao
# destruir. Qualquer outra coisa continua sendo motivo de parada.
_tm_is_only_status_flip() {
  _tm_ns="$( git diff --numstat -- "$THREAT_MODEL" \
             | awk '{ n++; a=$1; d=$2 } END { if (n==1) printf "%s/%s", a, d; else printf "many" }' )"
  [ "$_tm_ns" = "1/1" ] || return 1
  _tm_removed="$( git diff -U0 -- "$THREAT_MODEL" | sed -n 's/^-\([^-].*\)$/\1/p' )"
  _tm_added="$(   git diff -U0 -- "$THREAT_MODEL" | sed -n 's/^+\([^+].*\)$/\1/p' )"
  case "$_tm_removed" in '**Status:** accepted') : ;; *) return 1 ;; esac
  case "$_tm_added"   in '**Status:** stale')    : ;; *) return 1 ;; esac
  return 0
}

_tm_dirty_count="$( git status --porcelain=v1 | grep -c -v '^??' || true )"
_tm_xy="$( git status --porcelain=v1 -- "$THREAT_MODEL" | head -1 | cut -c1-2 )"
if [ "$_tm_dirty_count" = "1" ] && [ "$_tm_xy" = " M" ]; then
  if _tm_is_only_status_flip; then
    if git checkout -- "$THREAT_MODEL" 2>/dev/null; then
      warn "$THREAT_MODEL estava modificado e eu REVERTI."
      printf '        Ninguem editou esse arquivo: quem o reescreve e\n'
      printf '        `.claude/scripts/check-threat-model-freshness.py`, que troca\n'
      printf '        `**Status:** accepted` por `stale` como efeito colateral de rodar.\n'
      printf '        Confirmei que o diff era EXATAMENTE essa troca de uma linha, e\n'
      printf '        nada mais, antes de reverter.\n'
    else
      die "tentei reverter $THREAT_MODEL e o \`git checkout\` falhou — chame o CEO"
    fi
  else
    warn "$THREAT_MODEL esta modificado, mas o diff NAO e so a troca de status."
    printf '        NAO vou reverter: ha conteudo real ai que eu destruiria.\n'
    printf '        Veja o que mudou de fato:\n'
    printf '          cd %s && git diff -- %s\n' "$ROOT" "$THREAT_MODEL"
  fi
fi

# ---------------------------------------------------------------------------
# P0-c — arvore: nenhuma modificacao RASTREADA.
# ---------------------------------------------------------------------------
# O Anchor-SHA tem de descrever o que sera landado. Arquivos UNTRACKED sao
# tolerados SO se o oraculo de canonicidade responder 0 — o land stageia
# exatamente o patch + sentinel + .asc (passo S), entao um untracked
# nao-canonico nunca entra no commit; um untracked CANONICO (arquivo novo sob
# .claude/hooks/ etc.) aborta.
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

# ---------------------------------------------------------------------------
# P0-d — materiais COMMITADOS.
# ---------------------------------------------------------------------------
# Pair-rail r9 P2 da S326: o LAND exige-os rastreados, e commita-los DEPOIS da
# assinatura muda o HEAD e invalida o Anchor-SHA (G1). Mesma lista do LAND.
MATERIALS=(
  "$PLAN_DIR/OWNER-S334-ADRGATE-SIGN.sh"
  "$LAND_SCRIPT"
  "$PROPOSED"
  "$CEREMONY_DIR/COMMIT-MSG-ADRGATE.txt"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-adrgate.sh"
  "$CEREMONY_DIR/test-ceremony-scripts-adrgate.sh"
  "$CEREMONY_DIR/DESIGN-ADRGATE-S334.md"
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

# ---------------------------------------------------------------------------
# P0-e — registros de rail rastreados, e o ULTIMO tem de ser APPROVE.
# ---------------------------------------------------------------------------
# Contar rodadas nao e ler o veredito: um pacote com 5 registros cujo ULTIMO e
# REJECT tem 5 rodadas e nenhuma aprovacao. O numero e comparado como INTEIRO,
# nunca por ordem de nome — lexicograficamente `rail-round-10` vem antes de
# `rail-round-2`, e o SIGN leria o veredito ERRADO. A comparacao do veredito e
# IGUALDADE EXATA com `APPROVE`: uma linha qualificada
# (`APPROVE com ressalvas`) nunca casa — licao paga na wave-F.
RAIL_COUNT=0
LAST_RAIL=""
LAST_N=-1
for r in $RAIL_GLOB; do
  [ -f "$r" ] || continue
  git ls-files --error-unmatch -- "$r" >/dev/null 2>&1 \
    || die "registro de rail NAO commitado: $r — commite ANTES de assinar"
  RAIL_COUNT=$(( RAIL_COUNT + 1 ))
  _b="$( basename "$r" )"
  _n="${_b#rail-round-}"; _n="${_n%.md}"
  case "$_n" in
    ''|*[!0-9]*) die "registro de rail com numero nao-decimal: $r
  O SIGN precisa saber QUAL e o ultimo; renomeie para rail-round-<N>.md." ;;
  esac
  if [ "$_n" -gt "$LAST_N" ]; then LAST_N="$_n"; LAST_RAIL="$r"; fi
done
[ "$RAIL_COUNT" -gt 0 ] || die "nenhum registro de rail em $RAIL_GLOB — o V2 do PROTOCOL exige pelo menos uma rodada registrada"
RAIL_VERDICT="$( { grep -m1 '^Rail-Verdict:' "$LAST_RAIL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]' )"
[ -n "$RAIL_VERDICT" ] || die "o ultimo registro de rail ($LAST_RAIL) nao tem uma linha 'Rail-Verdict:'.
  Um registro sem veredito nao autoriza nada. Escreva-a e commite."
[ "$RAIL_VERDICT" = "APPROVE" ] || die "o ULTIMO registro de rail traz Rail-Verdict: $RAIL_VERDICT
  arquivo: $LAST_RAIL
  Um pacote so e assinavel depois de uma rodada de rail APPROVE — igualdade
  exata, sem qualificador. Trate os achados, rode outra rodada e registre-a
  como rail-round-$(( LAST_N + 1 )).md."
ok "$RAIL_COUNT registro(s) de rail rastreados; o ultimo ($( basename "$LAST_RAIL" )) e APPROVE"

# ---------------------------------------------------------------------------
# P0-f — substrato: o checker de cadeia carrega e expoe o ledger.
# ---------------------------------------------------------------------------
# O V3 do LAND importa o modulo HIFENIZADO por importlib e chama
# `_load_declared_exemptions`. A checagem e COMPORTAMENTAL (o import responde?),
# nunca por versao ou grep: se o checker mudar de forma, melhor descobrir aqui
# do que no meio do V-block com o patch ja aplicado. Nenhum valor e comparado
# neste passo — o sentinel ainda nao esta aplicado e o ledger do HEAD pode
# legitimamente estar vazio; quem compara contra a base declarada e o LAND.
python3 - "$CHAIN_SCRIPT" <<'PY' || die "P0-f: o substrato do V3 nao responde — veja a mensagem acima"
import importlib.util, sys
script = sys.argv[1]
spec = importlib.util.spec_from_file_location("cac_sign_probe", script)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception as exc:
    sys.exit("o import de %s falhou: %r" % (script, exc))
if not hasattr(mod, "_load_declared_exemptions"):
    sys.exit("%s nao expoe _load_declared_exemptions — o V3 do LAND nao teria sujeito" % script)
print("  checker importa e expoe _load_declared_exemptions")
PY
ok "substrato do V3 responde ($CHAIN_SCRIPT)"

case "$(cat "$SENTINEL")" in
  *TO-FILL-AT-FINAL-PATCH*)
    die "o sentinel ainda tem placeholder de patch — rode o finalize-adrgate.sh primeiro" ;;
esac
case "$(cat "$SENTINEL")" in
  *"  - placeholder"*)
    die "o bloco Scope ainda e placeholder — rode o finalize-adrgate.sh primeiro" ;;
esac
ok "sentinel finalizado (sem placeholders de patch)"

if [ -f "$SENTINEL.asc" ]; then
  printf '  \033[33mWARN\033[0m ja existe %s — ele sera SOBRESCRITO.\n' "$SENTINEL.asc"
  if [ "$SELFTEST" = "0" ]; then
    read -r -p "  continuar? [y/N] " a
    case "$a" in y|Y) : ;; *) die "abortado pelo operador" ;; esac
  fi
fi

# ---------------------------------------------------------------------------
step "P1 — binding do patch (o que voce esta assinando)"
# ---------------------------------------------------------------------------
DECLARED="$( { grep -m1 '^Patch-sha256:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
ACTUAL="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
[ "$DECLARED" = "$ACTUAL" ] || die "o patch NAO casa o sha256 do sentinel
  no sentinel: $DECLARED
  no arquivo : $ACTUAL
  Alguem mexeu no patch. NAO assine ate reconciliar."
ok "patch casa o sha256 do sentinel"

# O MESMO sha tem de constar do registro PROPOSED-PATCH.md: o registro e o que
# a revisao leu; um registro apontando para outro patch e evidencia falsa.
PROPOSED_SHA="$( { grep -m1 '^Patch-sha256:' "$PROPOSED" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
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
PATCH_BASE="$( { grep -m1 '^Patch-base:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
[ -n "$PATCH_BASE" ] || die "sentinel sem campo Patch-base (o finalize_patch.py grava)"
git merge-base --is-ancestor "$PATCH_BASE" "$HEAD_SHA" \
  || die "a base do patch NAO e ancestral do HEAD
  Patch-base: $PATCH_BASE
  HEAD atual: $HEAD_SHA
  A arvore andou por outro caminho. Refinalize (finalize-adrgate.sh) e repita."
DRIFT_TMP="$(mktemp)"
git diff --name-only "$PATCH_BASE" "$HEAD_SHA" | sort -u > "$DRIFT_TMP"
TOUCHED_TMP="$(mktemp)"
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$TOUCHED_TMP"
DRIFTED="$(comm -12 "$DRIFT_TMP" "$TOUCHED_TMP")"
rm -f "$DRIFT_TMP" "$TOUCHED_TMP"
if [ -n "$DRIFTED" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "path(s) do patch mudaram entre a base e o HEAD:
$(printf '  %s\n' $DRIFTED)
  O patch foi revisado sobre outro conteudo. Refinalize e repita.
  (Foi esta a classe que abortou o pacote D duas vezes na S329: enquanto um
   pacote espera assinatura, nenhum dos seus destinos pode ser editado.)"
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
  Rode o finalize-adrgate.sh de novo (ele reescreve os dois)."
ok "BASE-SHA.txt casa o Patch-base assinado"

git apply --check "$PATCH" || die "git apply --check FALHOU — a arvore divergiu do patch"
ok "o patch aplica limpo na arvore atual"

PATCH_FILES="$(git apply --numstat "$PATCH" | wc -l | tr -d ' ')"
printf '      %s arquivo(s) no patch:\n' "$PATCH_FILES"
git apply --numstat "$PATCH" | awk '{printf "        %s\n", $3}'

# ---------------------------------------------------------------------------
step "P2 — identidade do signer"
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
step "P3 — preenchendo os campos"
# ---------------------------------------------------------------------------
# Os placeholders deste sentinel-draft sao ANCHOR-PLACEHOLDER /
# DATA-PLACEHOLDER / APPROVED-BY-PLACEHOLDER (nao os TO-FILL-AT-SIGN da
# wave-F) — o regex ancora no placeholder REAL e ABORTA se o campo ja estiver
# preenchido (re-assinar sem reset e erro, nao sobrescrita silenciosa).
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

fill(r"^Anchor-SHA: ANCHOR-PLACEHOLDER$", "Anchor-SHA: %s" % head, "Anchor-SHA")
fill(r"^Data: DATA-PLACEHOLDER$", "Data: %s" % today, "Data")
fill(r"^Approved-By: APPROVED-BY-PLACEHOLDER$",
     "Approved-By: @Canhada-Labs %s" % fpr, "Approved-By")
open(path, "w", encoding="utf-8").write(s)
print("  campos preenchidos")
PY
ok "Anchor-SHA=$HEAD_SHA  Data=$TODAY"

printf '\n  Bloco que sera assinado:\n'
awk '/BEGIN SIGNED SCOPE/,/END SIGNED SCOPE/' "$SENTINEL" | sed 's/^/      /'

# ---------------------------------------------------------------------------
step "P4 — assinando"
# ---------------------------------------------------------------------------
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
    # P0-c ("modificacao rastreada") e a recuperacao seria manual (pair-rail r9
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
  empurra (voce nao digita 'git' em momento nenhum). O V-block completo demora
  alguns minutos: verify-counts (~3 min) e a governanca completa sao os gates
  de corpus deste pacote.

    bash $ROOT/$LAND_SCRIPT
EOF
