#!/usr/bin/env bash
# OWNER-W179-W24-SIGN.sh — assina o sentinel do PACOTE D (PLAN-179 W2+W4).
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (espelha OWNER-S327b-SIGN.sh; o gerador da W3 do PLAN-174 ainda nao emite
# cortes de wave, e este pacote e MANIFEST-based, nao patch-based).
#
# DIFERENCA PARA O MOLDE S327b: aquele pacote e um PATCH (Patch-sha256 /
# Patch-base / `git apply --check`). Este e um PACK por MANIFESTO: o que
# prende a assinatura ao conteudo sao DOIS arquivos, e as duas pernas sao
# verificadas aqui:
#   MANIFEST.sha256 — sha256 de cada arquivo DO PACK (integridade do pack)
#   BASELINE.sha256 — sha256 do arquivo VIVO de cada destino que ja existe
#                     (anti-stale: se o main andou, o pack esta velho)
# Um pack cujo BASELINE nao casa a arvore viva NAO pode ser assinado: a
# assinatura descreveria um land contra outro conteudo.
#
# Fluxo completo, do zero ao push (3 comandos, nenhum editor):
#
#   bash .claude/plans/PLAN-179/OWNER-W179-W24-SIGN.sh
#   bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh --dry-run
#   bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh
#
# O LAND faz o commit (com `-F`, sem editor) e o push. Voce nao digita `git`.
#
# ORDEM IMPORTA: o Anchor-SHA e o HEAD no momento da assinatura. Qualquer
# commit entre assinar e landar o invalida (G3 do land aborta). Este script
# e o ULTIMO passo antes do land — nao commite nada depois de roda-lo.
set -euo pipefail

# A raiz resolve por git a partir da LOCALIZACAO DO SCRIPT, nunca por `../..`
# nem pelo cwd (licao S313): o Owner pode chamar de qualquer diretorio.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes da cerimonia (o UNICO bloco que muda entre waves) ----------
PLAN_DIR=".claude/plans/PLAN-179"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-D"
ST="$PLAN_DIR/staged-w24"
DRAFT="$PLAN_DIR/W179-W24-approved-draft.md"
SENTINEL="$PLAN_DIR/W179-W24-approved.md"
LAND_SCRIPT="$PLAN_DIR/OWNER-W179-W24-LAND.sh"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }
warn(){ printf '\033[33m  WARN\033[0m %s\n' "$*"; }

# --- interruptor de AUTO-TESTE (recusado fora do scratchpad) ---------------
# Existe so para `s328-ceremony-D/test-ceremony-scripts-w24.sh` exercitar os
# gates sem a chave do Owner. A comparacao e por REALPATH dos DOIS lados
# (/tmp e symlink no macOS: comparar formato de string mediria formato, nao
# caminho).
SELFTEST=0
if [ "${CEREMONY_SELFTEST_NO_GPG:-}" = "1" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  case "$ROOT" in
    "$_sp_real"/claude-501/*/scratchpad/*) SELFTEST=1 ;;
    /private/var/folders/*) SELFTEST=1 ;;
    *) die "CEREMONY_SELFTEST_NO_GPG=1 RECUSADO: a arvore
  $ROOT
  nao esta sob um diretorio de teste descartavel.
  Este interruptor NAO existe para a arvore viva." ;;
  esac
  printf '\033[33m  MODO AUTO-TESTE\033[0m — GPG desligado; a arvore e um clone descartavel.\n'
fi

step "P0 — pre-condicoes"
[ -d "$ST" ]                  || die "pack ausente: $ST"
[ -f "$ST/MANIFEST.sha256" ]  || die "MANIFEST ausente — monte o pack:
  python3 $PLAN_DIR/assemble_pack.py $ST"
[ -f "$ST/BASELINE.sha256" ]  || die "BASELINE ausente — monte o pack:
  python3 $PLAN_DIR/assemble_pack.py $ST"
[ -f "$DRAFT" ]               || die "sentinel-draft ausente: $DRAFT"
[ -f "$LAND_SCRIPT" ]         || die "land script ausente: $LAND_SCRIPT"
[ -f "$CEREMONY_DIR/COMMIT-MSG-D.txt" ]     || die "mensagem de commit ausente: $CEREMONY_DIR/COMMIT-MSG-D.txt"
[ -f "$CEREMONY_DIR/EXPECTED-BASELINE.txt" ]|| die "base declarada ausente: $CEREMONY_DIR/EXPECTED-BASELINE.txt"
[ -f "$ORACLE" ]              || die "oraculo de canonicidade ausente: $ORACLE"

# Caminhos DENTRO do pack e seus DESTINOS no repo — derivados do manifesto,
# nunca de lista escrita a mao. Formato do manifesto: "<sha256>  <path>".
# Extrair por POSICAO: `awk '{$1=""}'` reconstroi o registro com OFS e deixa
# um espaco a esquerda (bug pego pelo G2b do W3-K antes de qualquer assinatura).
PACKPATHS="$(sed 's/^[0-9a-f]\{64\}  //' "$ST/MANIFEST.sha256")"
_map_dest() {  # $1 = pack path -> ecoa o destino no repo
  local line dest
  if [ -f "$ST/PACKMAP.txt" ]; then
    line=$(grep -F -- "$1 -> " "$ST/PACKMAP.txt" | head -1 || printf '')
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
TARGET_COUNT="$(printf '%s\n' "$TARGETS" | grep -c . || printf '0')"
[ "$TARGET_COUNT" -gt 0 ] || die "manifesto vazio — o pack nao tem payload"
ok "$TARGET_COUNT destino(s) derivado(s) do MANIFEST"

# Arvore: nenhuma modificacao RASTREADA (o Anchor-SHA tem de descrever o que
# sera landado). Arquivos UNTRACKED sao tolerados SO se o oraculo de
# canonicidade responder 0 — o land stageia exatamente TARGETS + sentinel +
# .asc (passo S), entao um untracked nao-canonico nunca entra no commit; um
# untracked CANONICO fora do escopo do pack aborta.
TRACKED_DIRTY=""; UNTRACKED_OK=""
_in_targets() {  # 0 se $1 e um destino do pack
  printf '%s\n' "$TARGETS" | grep -qxF -- "$1"
}
while IFS= read -r -d '' entry; do
  xy="${entry:0:2}"; entry_path="${entry:3}"
  case "$xy" in
    "??")
      if _in_targets "$entry_path"; then
        # Destino NOVO do proprio pack ainda nao aplicado: nao pode existir
        # vivo antes do land (o G1 do land tambem checa). Aqui e erro duro.
        die "destino NOVO do pack ja existe UNTRACKED no vivo: $entry_path
  Alguem aplicou o pack a mao. Remova (ou commite por cerimonia propria) antes de assinar."
      fi
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
ok "nenhuma modificacao rastreada; untracked (se houver) sao nao-canonicos e fora do pack"

# Os materiais tem de estar COMMITADOS antes de assinar (pair-rail r9 P2 da
# S326): o LAND exige-os rastreados, e commita-los DEPOIS da assinatura muda
# o HEAD e invalida o Anchor-SHA. O PACK INTEIRO entra nesta conta — o land
# copia de arquivos que precisam ser os revisados, nao versoes soltas no disco.
MATERIALS=(
  "$PLAN_DIR/OWNER-W179-W24-SIGN.sh"
  "$LAND_SCRIPT"
  "$DRAFT"
  "$CEREMONY_DIR/README-D.md"
  "$CEREMONY_DIR/COMMIT-MSG-D.txt"
  "$CEREMONY_DIR/EXPECTED-BASELINE.txt"
  "$CEREMONY_DIR/test-ceremony-scripts-w24.sh"
  "$ST/MANIFEST.sha256"
  "$ST/BASELINE.sha256"
  "$ST/PACKMAP.txt"
)
MISSING=""
for m in "${MATERIALS[@]}"; do
  if ! git ls-files --error-unmatch -- "$m" >/dev/null 2>&1; then
    MISSING="$MISSING  $m
"
  fi
done
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  if ! git ls-files --error-unmatch -- "$ST/$_p" >/dev/null 2>&1; then
    MISSING="$MISSING  $ST/$_p
"
  fi
done <<MEOF
$PACKPATHS
MEOF
[ -z "$MISSING" ] || die "material(is) de cerimonia NAO commitado(s):
$MISSING  Commite os materiais ANTES de assinar (commitar depois muda o HEAD e invalida a ancora).
  O pacote inteiro de uma vez:
    git -C $ROOT add $ST $PLAN_DIR/OWNER-W179-W24-SIGN.sh $LAND_SCRIPT $DRAFT $CEREMONY_DIR
    git -C $ROOT commit -m 'ceremony(PLAN-179 W2+W4): materiais do pacote D'"
RAIL_COUNT=0; RAIL_LAST=""; RAIL_LAST_N=-1
for r in $RAIL_GLOB; do
  [ -f "$r" ] || continue
  git ls-files --error-unmatch -- "$r" >/dev/null 2>&1 \
    || die "registro de rail NAO commitado: $r — commite ANTES de assinar"
  RAIL_COUNT=$(( RAIL_COUNT + 1 ))
  # Ordem por NUMERO da rodada, nao pela ordem do glob: `rail-round-10.md`
  # ordena antes de `rail-round-9.md` em ASCII, e a ultima rodada e a que
  # decide.
  _n="${r##*rail-round-}"; _n="${_n%.md}"
  case "$_n" in
    ''|*[!0-9]*) die "nome de registro de rail fora do padrao rail-round-<N>.md: $r" ;;
  esac
  if [ "$_n" -gt "$RAIL_LAST_N" ]; then RAIL_LAST_N="$_n"; RAIL_LAST="$r"; fi
done
[ "$RAIL_COUNT" -gt 0 ] || die "nenhum registro de rail em $RAIL_GLOB — o V2 do PROTOCOL exige pelo menos uma rodada registrada"

# CONTAR registros responde a pergunta ERRADA (pair-rail round 2, P1): um
# `rail-round-1.md` cujo veredito e REJECT satisfaz "existe pelo menos um" e
# deixava assinar um pacote reprovado. O que o contrato exige e que a ULTIMA
# rodada tenha fechado. Cada registro declara o veredito numa linha
# `Rail-Verdict: <APPROVE|REJECT|UNAVAILABLE>`; a ultima tem de ser APPROVE.
# Ausencia do campo e ABORT, nao "assume que passou" — fail-closed em input.
RAIL_VERDICT="$(sed -n 's/^Rail-Verdict:[[:space:]]*//p' "$RAIL_LAST" | head -1 | tr -d '[:space:]')"
[ -n "$RAIL_VERDICT" ] || die "o registro da ultima rodada nao declara veredito:
  $RAIL_LAST
  Todo rail-round-<N>.md precisa de uma linha 'Rail-Verdict: APPROVE|REJECT|UNAVAILABLE'."
case "$RAIL_VERDICT" in
  APPROVE) ;;
  REJECT)
    die "a ULTIMA rodada de pair-rail ($RAIL_LAST) fechou em REJECT.
  Rode outra rodada e cure ou registre pushback ate obter APPROVE.
  Assinar aqui contrariaria o contrato de revisao cross-LLM." ;;
  UNAVAILABLE)
    die "a ULTIMA rodada de pair-rail ($RAIL_LAST) ficou UNAVAILABLE.
  O rail nao respondeu; um pacote canonico nao e assinado sem revisao.
  Repita a rodada, ou registre a indisponibilidade e leve a decisao ao Owner." ;;
  *) die "veredito de rail nao reconhecido em $RAIL_LAST: '$RAIL_VERDICT'
  Valores aceitos: APPROVE | REJECT | UNAVAILABLE." ;;
esac
ok "materiais + pack ($TARGET_COUNT arquivo(s)) e $RAIL_COUNT rodada(s); ultima ($RAIL_LAST) = APPROVE"

step "P1 — frescor do pack (o que voce esta assinando)"
# (a) integridade do PACK. ORDEM DELIBERADA: primeiro o CONJUNTO, depois o
# conteudo — o modo de verificacao do shasum so olha as linhas que EXISTEM no
# manifesto e nao diz nada sobre um arquivo acrescentado ao pack DEPOIS da
# montagem (classe S272 / R6 do ceremony-lint).
PACK_FILES="$(cd "$ST" && find . -type f \
    ! -name 'MANIFEST.sha256' ! -name 'BASELINE.sha256' ! -name 'PACKMAP.txt' \
    ! -name '*-COMO-MONTAR.md' ! -name '*-NOTE.md' ! -name '*.pyc' \
    ! -path './__pycache__/*' ! -path '*/__pycache__/*' ! -name '.DS_Store' \
    | sed 's|^\./||' | sort)"
MAN_SET="$(printf '%s\n' "$PACKPATHS" | sed '/^[[:space:]]*$/d' | sort)"
if [ "$PACK_FILES" != "$MAN_SET" ]; then
  printf '  so no disco    : %s\n' "$(comm -23 <(printf '%s\n' "$PACK_FILES") <(printf '%s\n' "$MAN_SET") | tr '\n' ' ')"
  printf '  so no manifesto: %s\n' "$(comm -13 <(printf '%s\n' "$PACK_FILES") <(printf '%s\n' "$MAN_SET") | tr '\n' ' ')"
  die "o CONJUNTO de arquivos do pack != o conjunto do MANIFEST.
  Re-monte:  python3 $PLAN_DIR/assemble_pack.py $ST"
fi
MAN_LINES="$(printf '%s\n' "$MAN_SET" | wc -l | tr -d ' ')"
( cd "$ST" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || die "MANIFEST nao confere — algum arquivo do pack mudou depois da montagem.
  Re-monte:  python3 $PLAN_DIR/assemble_pack.py $ST"
ok "MANIFEST: $MAN_LINES arquivo(s), conjunto E conteudo conferem"

# (b) anti-stale: o BASELINE e o hash dos arquivos VIVOS na hora da montagem.
#     Drift = o main andou = o pack esta velho. Abortar, nunca "consertar".
STALE=""; BASE_N=0
while read -r want path; do
  [ -n "${path:-}" ] || continue
  BASE_N=$(( BASE_N + 1 ))
  if [ ! -f "$path" ]; then STALE="$STALE  SUMIU-NO-VIVO: $path
"; continue; fi
  got="$(shasum -a 256 "$path" | awk '{print $1}')"
  [ "$want" = "$got" ] || STALE="$STALE  DERIVOU: $path
"
done < "$ST/BASELINE.sha256"
[ -z "$STALE" ] || die "o BASELINE nao descreve mais a arvore viva:
$STALE  O main andou depois da montagem. RE-MONTE O PACK e repita a revisao:
    python3 $PLAN_DIR/assemble_pack.py $ST
  (re-stage por ITEM — nunca whole-file por cima de um destino que mudou)"
ok "BASELINE: $BASE_N destino(s) pre-existente(s) identico(s) ao momento da montagem"

# (c) destinos NOVOS (no manifesto, ausentes do baseline) nao podem existir vivos
NEW_N=0; NEW_EXISTS=""
while IFS= read -r p; do
  [ -n "$p" ] || continue
  if ! grep -qF "  $p" "$ST/BASELINE.sha256"; then
    NEW_N=$(( NEW_N + 1 ))
    [ ! -e "$p" ] || NEW_EXISTS="$NEW_EXISTS  $p
"
  fi
done <<TEOF
$TARGETS
TEOF
[ -z "$NEW_EXISTS" ] || die "destino(s) NOVO(s) ja existe(m) no vivo:
$NEW_EXISTS  O pack criaria um arquivo que ja esta la. Reconcilie antes de assinar."
ok "$NEW_N destino(s) novo(s) ausente(s) no vivo"

step "P1b — Scope do sentinel == MANIFEST (derivado, nunca recordado)"
# O G2b do LAND compara de novo; falhar AQUI e barato, falhar la e depois da
# assinatura. Divergencia nos DOIS sentidos aborta (o W2.8 abortou porque a
# lista humana tinha 7 onde o gate exigia 10).
SCOPE_DRAFT="$(awk '/^## Scope/{f=1;next} f&&/^```/{c++; if(c==2) exit; next} f&&c==1{print}' "$DRAFT" | sed '/^[[:space:]]*$/d' | sort)"
SCOPE_MANIFEST="$(printf '%s\n' "$TARGETS" | sed '/^[[:space:]]*$/d' | sort)"
if [ "$SCOPE_DRAFT" != "$SCOPE_MANIFEST" ]; then
  printf '  so no draft    : %s\n' "$(comm -23 <(printf '%s\n' "$SCOPE_DRAFT") <(printf '%s\n' "$SCOPE_MANIFEST") | tr '\n' ' ')"
  printf '  so no manifesto: %s\n' "$(comm -13 <(printf '%s\n' "$SCOPE_DRAFT") <(printf '%s\n' "$SCOPE_MANIFEST") | tr '\n' ' ')"
  die "o bloco '## Scope' do draft nao casa o MANIFEST — o land abortaria no G2b.
  Regenere o bloco a partir do manifesto (nunca a mao):
    sed 's/^[0-9a-f]\\{64\\}  //' $ST/MANIFEST.sha256"
fi
ok "Scope do draft == manifesto ($TARGET_COUNT paths)"

step "P2 — identidade do signer"
if [ "$SELFTEST" = "1" ]; then
  FPR="${CEO_SIGNER_FPR:-SELFTEST0000000000000000000000000000000000}"
  printf '  \033[33mAUTO-TESTE\033[0m signer: %s\n' "$FPR"
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
    grep -qi -- "$FPR" "$SIGNERS" \
      || die "o fingerprint $FPR NAO consta em $SIGNERS — o land abortaria no G3"
    ok "consta no rail rastreado"
  fi
fi

step "P3 — materializando o sentinel e preenchendo os campos"
# O sentinel ASSINADO e um arquivo PROPRIO, gerado do draft. O draft fica
# rastreado e intacto (e o que a revisao leu); o sentinel + .asc sao criados
# aqui e commitados pelo LAND, dentro do escopo declarado.
if [ -f "$SENTINEL" ]; then
  warn "ja existe $SENTINEL — ele sera REGERADO do draft."
  if [ "$SELFTEST" = "0" ]; then
    read -r -p "  continuar? [y/N] " a
    case "$a" in y|Y) : ;; *) die "abortado pelo operador" ;; esac
  fi
fi
if [ -L "$SENTINEL" ]; then die "$SENTINEL e um SYMLINK — recuso escrever atraves dele"; fi
cp "$DRAFT" "$SENTINEL"
HEAD_SHA="$(git rev-parse HEAD)"
TODAY="$(date -u +%Y-%m-%d)"

# Rotulos ASCII-safe: o parser de sentinel casa o rotulo por PREFIXO ASCII
# seguido de `[^:]*:` (licao S326 — script ASCII-safe vs prosa acentuada
# abortou um G3 com o campo CORRETO preenchido).
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
# O titulo do draft anuncia-se como DRAFT; o sentinel assinado nao e um draft.
s = s.replace("(DRAFT — assinar como W179-W24-approved.md)", "(ASSINADO)", 1)
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
  export GPG_TTY="${GPG_TTY:-$(tty 2>/dev/null || printf '')}"
  if command -v gpgconf >/dev/null 2>&1; then
    gpgconf --kill gpg-agent >/dev/null 2>&1 || printf ''
  fi
  if ! gpg --armor --detach-sign --yes --local-user "$FPR" "$SENTINEL"; then
    # O P3 ja materializou o sentinel; sem este rollback um re-run acharia
    # um sentinel meio-pronto e o operador teria de limpar a mao.
    rm -f -- "$SENTINEL" "$SENTINEL.asc"
    die "gpg falhou — sentinel REMOVIDO (nada assinado, nada aplicado).
  Modo de falha conhecido: 'No pinentry'. Rode NO SEU TERMINAL, nao via agente:
    export GPG_TTY=\$(tty); gpgconf --kill gpg-agent
  e repita este script do zero."
  fi
  ok "assinatura gerada: $SENTINEL.asc"
  gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /'
fi

step "PRONTO"
cat <<EOF

  A assinatura cobre o HEAD $HEAD_SHA e $TARGET_COUNT path(s) do pack.
  NAO commite nada agora — qualquer commit invalida o Anchor-SHA.

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$LAND_SCRIPT --dry-run

  O dry-run aplica o pack, roda a bateria INTEIRA e depois DESFAZ tudo
  (arvore e index voltam byte a byte). Se ele terminar verde, o comando
  seguinte aplica, verifica, commita e empurra — voce nao digita 'git':

    bash $ROOT/$LAND_SCRIPT
EOF
