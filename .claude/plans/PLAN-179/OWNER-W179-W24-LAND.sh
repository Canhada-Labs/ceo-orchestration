#!/usr/bin/env bash
# OWNER-W179-W24-LAND.sh — LAND do PACOTE D (PLAN-179 W2 + W4), Owner-run.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (o gerador da W3 do PLAN-174 ainda nao emite cortes de wave; este pacote e
# MANIFEST-based e nao patch-based, entao o molde patch nao se aplica).
#
# O que este pacote aplica (decisao do Owner de 2026-08-25, AskUserQuestion):
#   TRES acoes novas em audit_emit._KNOWN_ACTIONS (327 -> 330):
#     ledger_checkpoint_recorded / ledger_checkpoint_skipped / ledger_entry_rejected
#   + hook check_ledger_checkpoint.py, _lib/ledger_provenance.py, ADR-195,
#     SPEC/v1 v2.59, registracao em settings.json + espelho no template.
#
# Gates (fail-closed):
#   G0 branch/insumos/materiais/arvore · G1 baseline anti-stale ·
#   G2 integridade do pack (conteudo E conjunto) · G2b Scope == MANIFEST ·
#   G3 sentinel GPG (signer-pin + anchor == HEAD) · G4 smoke em clone ·
#   G5 apply (modos derivados, nunca `chmod +x` cego) ·
#   V1..V6 bateria DO PROPRIO PACOTE contra conjuntos DECLARADOS em
#          s328-ceremony-D/EXPECTED-BASELINE.txt (nunca contra zero) ·
#   S stage EXATO verificado por cmp · C commit -F (sem editor) · P push.
#
# `--dry-run` faz TUDO ate o V6 e depois DESFAZ: arvore e index voltam byte a
# byte (trap armado ANTES do apply). Um abort em qualquer ponto restaura do
# mesmo jeito — a licao 1 da S327 foi um abort no V4 que deixou a arvore suja.
#
# Uso:
#   bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh --dry-run
#   bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes da cerimonia (o UNICO bloco que muda entre waves) ----------
PLAN_DIR=".claude/plans/PLAN-179"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-D"
ST="$PLAN_DIR/staged-w24"
DRAFT="$PLAN_DIR/W179-W24-approved-draft.md"
APPROVED="$PLAN_DIR/W179-W24-approved.md"
SIGN_SCRIPT="$PLAN_DIR/OWNER-W179-W24-SIGN.sh"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-D.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
ORACLE=".claude/hooks/check_canonical_edit.py"
OWNER_KEYID="CFCFACF00335DC74"
PUSH_REMOTE="origin"
PUSH_BRANCH="main"
# --------------------------------------------------------------------------

DRY=0
case "${1:-}" in
  --dry-run) DRY=1 ;;
  "")        DRY=0 ;;
  *) printf 'uso: bash %s [--dry-run]\n' "$0" >&2; exit 2 ;;
esac

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }
warn(){ printf '\033[33m  WARN\033[0m %s\n' "$*"; }

# --- interruptor de AUTO-TESTE (recusado fora de arvore descartavel) -------
# Existe so para s328-ceremony-D/test-ceremony-scripts-w24.sh exercitar os
# gates sem a chave do Owner e sem pagar a suite inteira. Comparacao por
# REALPATH dos DOIS lados (/tmp e symlink no macOS).
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
  warn "MODO AUTO-TESTE — GPG e push desligados; a arvore e um clone descartavel."
fi
# STOP_AFTER e NO_RESTORE so sao honrados sob SELFTEST (que ja exige arvore
# descartavel). O NO_RESTORE existe para o harness poder INSPECIONAR a arvore
# aplicada — modos de arquivo, por exemplo — que a restauracao apagaria antes
# de qualquer assercao. Fora do auto-teste os dois sao inertes.
STOP_AFTER=""; NO_RESTORE=0
if [ "$SELFTEST" = "1" ]; then
  STOP_AFTER="${CEREMONY_SELFTEST_STOP_AFTER:-}"
  [ "${CEREMONY_SELFTEST_NO_RESTORE:-}" = "1" ] && NO_RESTORE=1
fi
_stop_here() {  # $1 = nome do passo recem-concluido
  [ -n "$STOP_AFTER" ] || return 0
  [ "$STOP_AFTER" = "$1" ] || return 0
  if [ "$NO_RESTORE" = "1" ]; then
    warn "AUTO-TESTE: parando depois de $1 e MANTENDO o apply (CEREMONY_SELFTEST_NO_RESTORE)"
    RESTORE_ON_EXIT=0
  else
    warn "AUTO-TESTE: parando depois de $1 (CEREMONY_SELFTEST_STOP_AFTER)"
    RESTORE_ON_EXIT=1
  fi
  exit 0
}

# ---------------------------------------------------------------------------
step "G0 — branch, insumos, materiais e arvore"
# ---------------------------------------------------------------------------
# O commit avanca o HEAD ATUAL e `git push origin HEAD:main` empurra o ref
# LOCAL. Fora do main o push "sucede" sem levar o commit assinado — fail-closed.
_cur_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '')"
[ "$_cur_branch" = "$PUSH_BRANCH" ] \
  || die "HEAD esta em '$_cur_branch', nao em '$PUSH_BRANCH' — o land so roda no $PUSH_BRANCH (git checkout $PUSH_BRANCH)"
ok "HEAD em $PUSH_BRANCH"

[ -d "$ST" ]                 || die "pack ausente: $ST"
[ -f "$ST/MANIFEST.sha256" ] || die "MANIFEST ausente: $ST/MANIFEST.sha256"
[ -f "$ST/BASELINE.sha256" ] || die "BASELINE ausente: $ST/BASELINE.sha256"
[ -f "$APPROVED" ]     || die "sentinel ausente: $APPROVED
  O Owner assina com:  bash $ROOT/$SIGN_SCRIPT"
[ -f "$APPROVED.asc" ] || die "assinatura ausente: $APPROVED.asc
  O Owner assina com:  bash $ROOT/$SIGN_SCRIPT"
[ -f "$COMMIT_MSG" ]   || die "mensagem de commit ausente: $COMMIT_MSG"
[ -f "$BASELINE_ENV" ] || die "base declarada AUSENTE: $BASELINE_ENV
  O V-block compara contra conjuntos DECLARADOS; sem eles ele compararia
  contra nada, que e a forma do falso-verde que a S327 pagou."
[ -f "$ORACLE" ]       || die "oraculo de canonicidade ausente: $ORACLE"

# Caminhos do pack e destinos no repo — DERIVADOS do manifesto.
# Formato: "<sha256>  <path>". Extrair por POSICAO (awk '{$1=""}' deixaria um
# espaco a esquerda — bug pego pelo G2b do W3-K).
PACKPATHS="$(sed 's/^[0-9a-f]\{64\}  //' "$ST/MANIFEST.sha256")"
_map_dest() {
  local line dest
  if [ -f "$ST/PACKMAP.txt" ]; then
    line=$(grep -F -- "$1 -> " "$ST/PACKMAP.txt" | head -1 || printf '')
    if [ -n "$line" ]; then dest=${line#* -> }; printf '%s\n' "$dest"; return 0; fi
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

# Nenhum destino pode escapar do repo (confinamento fisico; classe PLAN-185 F1).
while IFS= read -r d; do
  [ -n "$d" ] || continue
  case "$d" in
    /*|*..*) die "destino ILEGAL no manifesto/PACKMAP: $d" ;;
  esac
done <<DEOF
$TARGETS
DEOF
ok "$TARGET_COUNT destino(s) derivado(s) do MANIFEST, todos dentro do repo"

# Materiais rastreados: o land copia de arquivos que TEM de ser os revisados.
MATERIALS=(
  "$SIGN_SCRIPT" "$PLAN_DIR/OWNER-W179-W24-LAND.sh" "$DRAFT"
  "$COMMIT_MSG" "$BASELINE_ENV" "$CEREMONY_DIR/README-D.md"
  "$ST/MANIFEST.sha256" "$ST/BASELINE.sha256" "$ST/PACKMAP.txt"
)
MISSING=""
for m in "${MATERIALS[@]}"; do
  git ls-files --error-unmatch -- "$m" >/dev/null 2>&1 || MISSING="$MISSING  $m
"
done
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  git ls-files --error-unmatch -- "$ST/$_p" >/dev/null 2>&1 || MISSING="$MISSING  $ST/$_p
"
done <<MEOF
$PACKPATHS
MEOF
[ -z "$MISSING" ] || die "material(is)/arquivo(s) do pack NAO commitado(s):
$MISSING  Commite-os e re-assine (o Anchor-SHA tem de ser o HEAD com os materiais dentro)."
ok "materiais e ${TARGET_COUNT} arquivo(s) do pack rastreados"

# Arvore: nenhuma modificacao RASTREADA. Untracked so passa se o oraculo de
# canonicidade responder 0 (nao-canonico) — o passo S stageia EXATAMENTE
# TARGETS + sentinel + .asc, entao untracked nao-canonico nunca entra.
_in_targets() { printf '%s\n' "$TARGETS" | grep -qxF -- "$1"; }
TRACKED_DIRTY=""; UNTRACKED_TOL=0
while IFS= read -r -d '' entry; do
  xy="${entry:0:2}"; entry_path="${entry:3}"
  case "$xy" in
    "??")
      if _in_targets "$entry_path"; then
        die "destino NOVO do pack ja existe UNTRACKED no vivo: $entry_path
  Alguem aplicou o pack a mao. Remova antes de landar."
      fi
      verdict="$(python3 "$ORACLE" --is-canonical "$entry_path" 2>/dev/null | awk -F'\t' 'NR==1{print $2}')"
      case "$verdict" in
        0) UNTRACKED_TOL=$(( UNTRACKED_TOL + 1 )) ;;
        1) die "arquivo UNTRACKED em path CANONICO fora do pack: $entry_path" ;;
        *) die "oraculo nao respondeu 0|1 para: $entry_path" ;;
      esac ;;
    *R*|*C*) IFS= read -r -d '' _from || true; TRACKED_DIRTY="$TRACKED_DIRTY  $xy $entry_path
" ;;
    *) TRACKED_DIRTY="$TRACKED_DIRTY  $xy $entry_path
" ;;
  esac
done < <(git status --porcelain=v1 -z)
[ -z "$TRACKED_DIRTY" ] || die "modificacoes RASTREADAS na arvore antes do apply:
$TRACKED_DIRTY  Commite ou reverta; o land nao mistura trabalho alheio no commit assinado."
ok "arvore sem modificacao rastreada ($UNTRACKED_TOL untracked nao-canonico(s) tolerado(s))"

# ---------------------------------------------------------------------------
step "G1 — baseline anti-stale"
# ---------------------------------------------------------------------------
FAILED=""; BASE_N=0
while read -r want path; do
  [ -n "${path:-}" ] || continue
  BASE_N=$(( BASE_N + 1 ))
  if [ ! -f "$path" ]; then FAILED="$FAILED  SUMIU-NO-VIVO: $path
"; continue; fi
  got="$(shasum -a 256 "$path" | awk '{print $1}')"
  [ "$want" = "$got" ] || FAILED="$FAILED  DERIVOU: $path
"
done < "$ST/BASELINE.sha256"
[ -z "$FAILED" ] || die "o main andou depois da montagem do pack:
$FAILED  Re-monte por ITEM (nunca whole-file):  python3 $PLAN_DIR/assemble_pack.py $ST
  e re-assine — o Anchor-SHA atual descreve outra arvore."
ok "$BASE_N/$BASE_N destino(s) pre-existente(s) identico(s) ao baseline"

NEWCOUNT=0
while IFS= read -r p; do
  [ -n "$p" ] || continue
  if ! grep -qF "  $p" "$ST/BASELINE.sha256"; then
    NEWCOUNT=$(( NEWCOUNT + 1 ))
    [ ! -e "$p" ] || die "STALE-NEW: $p ja existe no vivo"
  fi
done <<TEOF
$TARGETS
TEOF
ok "$NEWCOUNT arquivo(s) novo(s) ausente(s) no vivo"

# ---------------------------------------------------------------------------
step "G2 — integridade do pack (conteudo E conjunto)"
# ---------------------------------------------------------------------------
# ORDEM DELIBERADA: primeiro o CONJUNTO, depois o conteudo. O modo de
# verificacao do shasum so olha as linhas que EXISTEM no manifesto; ele nao
# afirma nada sobre um arquivo acrescentado ao pack DEPOIS da montagem
# (classe S272 / R6 do ceremony-lint).
PACK_FILES="$(cd "$ST" && find . -type f \
    ! -name 'MANIFEST.sha256' ! -name 'BASELINE.sha256' ! -name 'PACKMAP.txt' \
    ! -name '*-COMO-MONTAR.md' ! -name '*-NOTE.md' ! -name '*.pyc' \
    ! -path './__pycache__/*' ! -path '*/__pycache__/*' ! -name '.DS_Store' \
    | sed 's|^\./||' | sort)"
MAN_SET="$(printf '%s\n' "$PACKPATHS" | sed '/^[[:space:]]*$/d' | sort)"
if [ "$PACK_FILES" != "$MAN_SET" ]; then
  printf '  so no disco    : %s\n' "$(comm -23 <(printf '%s\n' "$PACK_FILES") <(printf '%s\n' "$MAN_SET") | tr '\n' ' ')"
  printf '  so no manifesto: %s\n' "$(comm -13 <(printf '%s\n' "$PACK_FILES") <(printf '%s\n' "$MAN_SET") | tr '\n' ' ')"
  die "o CONJUNTO de arquivos do pack != o conjunto do MANIFEST"
fi
MAN_N="$(printf '%s\n' "$MAN_SET" | wc -l | tr -d ' ')"
( cd "$ST" && shasum -a 256 -c MANIFEST.sha256 --status ) \
  || die "pack nao confere com o MANIFEST — algum arquivo mudou depois da montagem"
ok "$MAN_N arquivo(s) conferem em conjunto E conteudo"

# ---------------------------------------------------------------------------
step "G2b — escopo do sentinel == manifesto (derivado, nao recordado)"
# ---------------------------------------------------------------------------
SCOPE_SENTINEL="$(awk '/^## Scope/{f=1;next} f&&/^```/{c++; if(c==2) exit; next} f&&c==1{print}' "$APPROVED" | sed '/^[[:space:]]*$/d' | sort)"
SCOPE_MANIFEST="$(printf '%s\n' "$TARGETS" | sed '/^[[:space:]]*$/d' | sort)"
if [ "$SCOPE_SENTINEL" != "$SCOPE_MANIFEST" ]; then
  printf '  so no sentinel : %s\n' "$(comm -23 <(printf '%s\n' "$SCOPE_SENTINEL") <(printf '%s\n' "$SCOPE_MANIFEST") | tr '\n' ' ')"
  printf '  so no manifesto: %s\n' "$(comm -13 <(printf '%s\n' "$SCOPE_SENTINEL") <(printf '%s\n' "$SCOPE_MANIFEST") | tr '\n' ' ')"
  die "escopo do sentinel != manifesto do pack — a assinatura nao cobre o que seria escrito"
fi
ok "escopo identico ao manifesto ($TARGET_COUNT paths)"

# ---------------------------------------------------------------------------
step "G3 — sentinel GPG (signer-pin + anchor == HEAD)"
# ---------------------------------------------------------------------------
HEAD_SHA="$(git rev-parse HEAD)"
if [ "$SELFTEST" = "1" ]; then
  warn "AUTO-TESTE: verificacao GPG PULADA"
  _anchor="$(sed -n 's/^Anchor-SHA[^:]*: //p' "$APPROVED" | head -1)"
  [ "$_anchor" = "$HEAD_SHA" ] || die "anchor != HEAD ($_anchor != $HEAD_SHA)"
else
  GPG_OUT="$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1)" \
    || { printf '%s\n' "$GPG_OUT" >&2; die "gpg rc!=0 — assinatura invalida"; }
  printf '%s\n' "$GPG_OUT" | grep '^\[GNUPG:\] VALIDSIG ' \
    | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
    || die "assinatura valida mas NAO e do Owner ($OWNER_KEYID)"
  # Rotulo casado por PREFIXO ASCII + `[^:]*:` (licao S326: prosa acentuada
  # depois do rotulo abortava o gate com o campo CORRETO preenchido).
  _anchor="$(sed -n 's/^Anchor-SHA[^:]*: //p' "$APPROVED" | head -1)"
  [ "$_anchor" = "$HEAD_SHA" ] \
    || die "anchor != HEAD — re-assine
  no sentinel: $_anchor
  HEAD atual : $HEAD_SHA"
fi
ok "assinatura do Owner + anchor == HEAD ($HEAD_SHA)"
_stop_here G3

# ---------------------------------------------------------------------------
step "G4 — smoke em clone (rc AGREGADO por comando, fora do TMPDIR)"
# ---------------------------------------------------------------------------
# Smoke barato ANTES de qualquer mutacao viva: se o apply produz uma arvore
# que nao importa, isso aparece aqui e nada foi tocado. A bateria COMPLETA
# (com os conjuntos declarados) roda no V-block, sobre a arvore real.
SIMROOT="$HOME/.w179-landsim"; mkdir -p "$SIMROOT"
SIM="$(mktemp -d "$SIMROOT/sim.XXXXXX")"
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
  printf '   -> %s\n' "$*"
  ( cd "$SIM/repo" && PYTHONDONTWRITEBYTECODE=1 "$@" ) >"$SIM/last.log" 2>&1 \
    || { printf '   \033[31mG4-FAIL\033[0m %s\n' "$*"; tail -25 "$SIM/last.log"; G4RC=1; }
}
run_g4 python3 -m py_compile .claude/hooks/check_ledger_checkpoint.py \
  .claude/hooks/_lib/ledger_provenance.py .claude/hooks/_lib/audit_emit.py
run_g4 python3 -c "import json;json.load(open('.claude/settings.json'))"
run_g4 python3 -c "import json;json.load(open('templates/settings/settings.base.json'))"
run_g4 python3 -m pytest -q -p no:cacheprovider --tb=short .claude/hooks/tests/test_check_ledger_checkpoint.py
run_g4 python3 -m pytest -q -p no:cacheprovider --tb=short .claude/hooks/tests/test_ledger_provenance.py
run_g4 python3 -m pytest -q -p no:cacheprovider --tb=short .claude/hooks/tests/test_audit_emit_api_contract.py
run_g4 python3 .claude/scripts/check-audit-registry-coverage.py --check
run_g4 python3 .claude/scripts/validate_governance_fast.py
[ "$G4RC" -eq 0 ] || { rm -rf "$SIM"; die "G4 vermelho (rc agregado) — NADA foi aplicado"; }
rm -rf "$SIM"
ok "smoke em clone verde (todos os comandos, nao so o ultimo)"
_stop_here G4

# ---------------------------------------------------------------------------
# Trap ANTES do apply. Estado declarado ANTES do trap: sob `set -u` uma
# variavel nao inicializada dentro do handler mata o handler e o dry-run
# deixaria o pack aplicado (licao 1 da S327 — o primeiro land real abortou
# no V4 e a arvore ficou suja).
# ---------------------------------------------------------------------------
APPLIED=0
RESTORE_ON_EXIT=0
FP_BEFORE=""
NEW_LIST=""      # destinos que o pack CRIA (a restauracao remove)
MOD_LIST=""      # destinos que o pack MODIFICA (a restauracao faz checkout)
_fingerprint() {
  {
    git status --porcelain=v1 --untracked-files=all
    printf -- '--diff--\n'
    git diff HEAD
    printf -- '--index--\n'
    git diff --cached --name-status
  } | shasum -a 256 | awk '{print $1}'
}
_restore() {
  local rc_keep=$?
  if [ "$RESTORE_ON_EXIT" = "1" ] && [ "$APPLIED" = "1" ]; then
    git reset -q >/dev/null 2>&1 || printf ''
    while IFS= read -r _n; do
      [ -n "$_n" ] || continue
      rm -f -- "$_n"
    done <<NEOF
$NEW_LIST
NEOF
    if [ -n "$MOD_LIST" ]; then
      while IFS= read -r _m; do
        [ -n "$_m" ] || continue
        git checkout -- "$_m" >/dev/null 2>&1 || printf ''
      done <<MOEOF
$MOD_LIST
MOEOF
    fi
    APPLIED=0
    _fp_after="$(_fingerprint)"
    if [ "$_fp_after" = "$FP_BEFORE" ]; then
      printf '\033[32m  ok\033[0m  arvore e index restaurados byte a byte (nada foi commitado)\n'
    else
      printf '\n\033[31mRESTAURACAO INCOMPLETA\033[0m — o estado difere do inicial.\n' >&2
      printf '  Inspecione:  git -C %s status\n' "$ROOT" >&2
    fi
  fi
  return "$rc_keep"
}
trap _restore EXIT

FP_BEFORE="$(_fingerprint)"

# ---------------------------------------------------------------------------
step "G5 — apply (modos derivados, nunca chmod cego)"
# ---------------------------------------------------------------------------
# O molde anterior fazia `case "$p" in .claude/hooks/*.py) chmod +x`. Em `case`
# do bash o `*` ATRAVESSA `/`: aquilo tambem casava `_lib/audit_emit.py` e
# `tests/test_*.py`, que sao 100644 no indice — o land staged um MODE CHANGE
# 644->755 num arquivo canonico (a classe R8/S314 que o ceremony-lint bloqueia).
# Aqui o modo e DERIVADO: destino ja rastreado herda o modo do INDICE; destino
# novo em `.claude/hooks/<nome>.py` (profundidade 1) nasce 755 — os 59 hooks
# vivos sao uniformemente 755; qualquer outro nasce 644.
RESTORE_ON_EXIT=1
APPLIED=1
while IFS= read -r p; do
  [ -n "$p" ] || continue
  case "$p" in PACKMAP.txt) continue ;; esac
  d="$(_map_dest "$p")"
  _idx_mode="$(git ls-files -s -- "$d" 2>/dev/null | awk 'NR==1{print $1}')"
  if [ -n "$_idx_mode" ]; then
    MOD_LIST="$MOD_LIST$d
"
  else
    NEW_LIST="$NEW_LIST$d
"
  fi
  mkdir -p "$(dirname "$d")"
  # Escrita atraves de symlink (classe PLAN-185 F1): um destino — ou o
  # diretorio que o contem — que seja link simbolico faria o `cp` aterrissar
  # FORA do repo, num path que a assinatura nao cobre. Fail-closed nos dois.
  if [ -L "$d" ]; then die "destino e um SYMLINK: $d — recuso escrever atraves dele"; fi
  _ddir="$(dirname "$d")"
  if [ -L "$_ddir" ]; then die "o diretorio de $d e um SYMLINK — recuso escrever atraves dele"; fi
  cp "$ST/$p" "$d"
  case "$_idx_mode" in
    100755) chmod 755 "$d" ;;
    100644) chmod 644 "$d" ;;
    "")
      case "$d" in
        .claude/hooks/*/*) chmod 644 "$d" ;;
        .claude/hooks/*.py) chmod 755 "$d" ;;
        *) chmod 644 "$d" ;;
      esac ;;
    *) die "modo inesperado no indice para $d: $_idx_mode" ;;
  esac
  if [ "$d" = "$p" ]; then printf '   applied %s\n' "$d"
  else printf '   applied %s  (do pack: %s)\n' "$d" "$p"; fi
done <<BEOF
$PACKPATHS
BEOF
MOD_LIST="$(printf '%s' "$MOD_LIST" | sed '/^[[:space:]]*$/d')"
NEW_LIST="$(printf '%s' "$NEW_LIST" | sed '/^[[:space:]]*$/d')"
ok "aplicado: $(printf '%s\n' "$MOD_LIST" | grep -c . || printf 0) modificado(s), $(printf '%s\n' "$NEW_LIST" | grep -c . || printf 0) novo(s)"
_stop_here G5

# --- leitor da base DECLARADA ----------------------------------------------
_exp() {
  local v
  v="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | tr -d '"' | tr -d '\r')"
  [ -n "$v" ] || die "chave $1 AUSENTE em $BASELINE_ENV — o V-block nao compara contra nada"
  printf '%s\n' "$v"
}
_assert_num() {  # $1 rotulo  $2 observado  $3 esperado
  [ "$2" = "$3" ] || die "$1: observado $2, DECLARADO $3 (base: $BASELINE_ENV)
  Se a mudanca e intencional, edite a base declarada e re-assine — nunca
  afrouxe o gate para caber no numero."
  printf '\033[32m  ok\033[0m  %s = %s (declarado)\n' "$1" "$2"
}

# ---------------------------------------------------------------------------
step "V1 — o codigo aplicado importa e os JSON carregam"
# ---------------------------------------------------------------------------
# Checagem de sintaxe SEM ESCRITA NENHUMA. `py_compile` estava errado aqui e
# a medicao e direta: com `PYTHONDONTWRITEBYTECODE=1` E `sys.dont_write_bytecode`
# True, `python3 -m py_compile x.py` AINDA gravou o `.pyc` — no macOS deste
# setup em `~/Library/Caches/com.apple.python/...`, fora do repo; no Linux
# seria `__pycache__` dentro da arvore aplicada. A env var governa a escrita
# do IMPORTADOR, nao a compilacao explicita. Nenhum dos dois destinos e
# desfeito pelo `_restore`, e o fingerprint dele e `git status` — que nao ve
# nem arquivo ignorado nem nada fora do repo. Resultado: o `--dry-run`
# anunciava "restaurados byte a byte" depois de ter mexido no sistema de
# arquivos. (pair-rail do main, rodada 2, P2.)
# A builtin `compile()` faz a MESMA pergunta e nao escreve nada — verificado
# com controle A/B.
python3 - .claude/hooks/check_ledger_checkpoint.py \
         .claude/hooks/_lib/ledger_provenance.py \
         .claude/hooks/_lib/audit_emit.py <<'PYC' || die "V1: sintaxe reprovou"
import sys
for path in sys.argv[1:]:
    with open(path, "rb") as fh:
        compile(fh.read(), path, "exec", dont_inherit=True)
PYC
python3 -c "import json;json.load(open('.claude/settings.json'))" \
  || die "V1: .claude/settings.json nao e JSON valido"
python3 -c "import json;json.load(open('templates/settings/settings.base.json'))" \
  || die "V1: templates/settings/settings.base.json nao e JSON valido"
# A registracao tem de existir NOS DOIS (o buraco que a suite pegou no w01).
for _f in .claude/settings.json templates/settings/settings.base.json; do
  grep -qF 'check_ledger_checkpoint.py' "$_f" \
    || die "V1: check_ledger_checkpoint.py NAO registrado em $_f — o adopter receberia o hook morto"
done
ok "V1: sintaxe (sem escrita) + 2 JSON + registracao presente nos dois settings"

# ---------------------------------------------------------------------------
step "V2 — contagens contra os conjuntos DECLARADOS"
# ---------------------------------------------------------------------------
OBS_ACTIONS="$(PYTHONDONTWRITEBYTECODE=1 python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('ae', '.claude/hooks/_lib/audit_emit.py')
m = importlib.util.module_from_spec(spec); sys.modules['ae'] = m
spec.loader.exec_module(m)
print(len(m._KNOWN_ACTIONS))
")" || die "V2: nao consegui carregar audit_emit.py para medir _KNOWN_ACTIONS"
_assert_num "len(_KNOWN_ACTIONS)" "$OBS_ACTIONS" "$(_exp EXPECTED_KNOWN_ACTIONS)"

# As 3 acoes tem de estar registradas E fora do passthrough generico.
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' || die "V2: registro das 3 acoes reprovou"
import importlib.util, sys
spec = importlib.util.spec_from_file_location('ae', '.claude/hooks/_lib/audit_emit.py')
m = importlib.util.module_from_spec(spec); sys.modules['ae'] = m
spec.loader.exec_module(m)
want = ("ledger_checkpoint_recorded", "ledger_checkpoint_skipped", "ledger_entry_rejected")
bad = []
for a in want:
    if a not in m._KNOWN_ACTIONS:
        bad.append("%s AUSENTE de _KNOWN_ACTIONS" % a)
    if a in getattr(m, "_EMIT_GENERIC_PASSTHROUGH", ()):
        bad.append("%s esta em _EMIT_GENERIC_PASSTHROUGH (proibido)" % a)
if bad:
    sys.exit("  " + "\n  ".join(bad))
print("  3 acoes registradas, nenhuma em _EMIT_GENERIC_PASSTHROUGH")
PY
ok "V2: as 3 acoes estao registradas e fora do passthrough"

OBS_GOLDEN="$(grep -c . .claude/data/audit-registry.golden.txt || printf 0)"
_assert_num "linhas do audit-registry.golden.txt" "$OBS_GOLDEN" "$(_exp EXPECTED_GOLDEN_LINES)"

OBS_SPEC="$(grep -c "^| $(_exp EXPECTED_SPEC_VERSION) |" SPEC/v1/audit-log.schema.md || printf 0)"
_assert_num "linhas de historico do SPEC $(_exp EXPECTED_SPEC_VERSION)" "$OBS_SPEC" "1"

VC_JSON="$(bash .claude/scripts/local/verify-counts.sh --no-tests --json 2>/dev/null)" \
  || die "V2: verify-counts.sh --json reprovou (contagens derivadas desatualizadas)"
_vc() { printf '%s' "$VC_JSON" | python3 -c "
import json,sys
print(json.load(sys.stdin)['live'][sys.argv[1]])" "$1"; }
_assert_num "hooks .py"          "$(_vc hook_py)"       "$(_exp EXPECTED_HOOKS_PY)"
_assert_num "hooks ligados"      "$(_vc registered)"    "$(_exp EXPECTED_HOOKS_REGISTERED)"
_assert_num "registros de hook"  "$(_vc registrations)" "$(_exp EXPECTED_HOOK_REGISTRATIONS)"
_assert_num "modulos _lib"       "$(_vc lib)"           "$(_exp EXPECTED_LIB)"
_assert_num "ADRs"               "$(_vc adrs)"          "$(_exp EXPECTED_ADRS)"
_stop_here V2

# ---------------------------------------------------------------------------
step "V3 — cobertura do registro de auditoria (SPEC <-> codigo)"
# ---------------------------------------------------------------------------
python3 .claude/scripts/check-audit-registry-coverage.py --check \
  || die "V3: check-audit-registry-coverage.py --check reprovou — golden e/ou SPEC fora de sincronia"
ok "V3: registro de auditoria coerente"

# ---------------------------------------------------------------------------
step "V4 — pytest .claude/hooks/tests (split do CI: 'not serial' + 'serial')"
# ---------------------------------------------------------------------------
V_LOG_DIR="$(mktemp -d)"
_run_pytest() {  # $1 rotulo  $2 log  resto: argv
  local label="$1" log="$2"; shift 2
  printf '   -> %s\n' "$*"
  set +e
  PYTHONDONTWRITEBYTECODE=1 "$@" >"$log" 2>&1
  local rc=$?
  set -e
  [ "$rc" -eq 0 ] || { tail -30 "$log" | sed 's/^/    /' >&2; rm -rf "$V_LOG_DIR"; die "$label: pytest rc=$rc"; }
  printf '\033[32m  ok\033[0m  %s — %s\n' "$label" "$(tail -1 "$log")"
}
_run_pytest "V4a hooks/tests not-serial" "$V_LOG_DIR/v4a.log" \
  python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q -p no:cacheprovider
_run_pytest "V4b hooks/tests serial" "$V_LOG_DIR/v4b.log" \
  python3 -m pytest .claude/hooks/tests/ -m 'serial' --strict-markers --tb=no -q -p no:cacheprovider

# ---------------------------------------------------------------------------
step "V5 — pytest .claude/hooks/_lib/tests (mesmo split)"
# ---------------------------------------------------------------------------
_run_pytest "V5a _lib/tests not-serial" "$V_LOG_DIR/v5a.log" \
  python3 -m pytest .claude/hooks/_lib/tests -n auto -m 'not serial' --strict-markers --tb=no -q -p no:cacheprovider
_run_pytest "V5b _lib/tests serial" "$V_LOG_DIR/v5b.log" \
  python3 -m pytest .claude/hooks/_lib/tests -m 'serial' --strict-markers --tb=no -q -p no:cacheprovider
rm -rf "$V_LOG_DIR"

# ---------------------------------------------------------------------------
step "V6 — gates de corpus sobre a arvore aplicada"
# ---------------------------------------------------------------------------
# O governance COMPLETO, nao o --fast: este pacote toca CLAUDE.md, e o limite
# de 40.000 bytes so e checado no completo (licao 4 da S327).
bash .claude/scripts/validate-governance.sh >/dev/null \
  || die "V6a: validate-governance.sh (COMPLETO) reprovou"
ok "V6a: validate-governance.sh completo verde"
_cm_bytes="$(wc -c < CLAUDE.md | tr -d ' ')"
[ "$_cm_bytes" -le 40000 ] || die "V6a: CLAUDE.md tem $_cm_bytes bytes (limite 40000)"
ok "V6a: CLAUDE.md $_cm_bytes bytes (<= 40000)"
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests \
  || die "V6b: verify-counts.sh reprovou"
ok "V6b: verify-counts.sh verde"
python3 .claude/scripts/check-claude-md-claims.py >/dev/null \
  || die "V6c: check-claude-md-claims.py reprovou"
ok "V6c: check-claude-md-claims.py verde"
python3 .claude/scripts/check-test-env-hygiene.py >/dev/null \
  || die "V6d: check-test-env-hygiene.py reprovou"
ok "V6d: check-test-env-hygiene.py verde"
# Set-equality ANTES do conteudo (mesma disciplina do G2): um manifesto com
# linhas em formato inesperado passaria calado por `-c --status`.
_gm_useful="$(grep -cE '^[0-9a-f]{64}  ' .claude/governance/gate-scripts-manifest.txt || printf 0)"
_gm_all="$(grep '[^[:space:]]' .claude/governance/gate-scripts-manifest.txt | wc -l | tr -d ' ')" || _gm_all=0
[ "$_gm_useful" -gt 0 ] || die "V6e: manifesto ADR-192 sem nenhuma linha no formato esperado"
[ "$_gm_useful" = "$_gm_all" ] \
  || die "V6e: o manifesto ADR-192 tem $_gm_all linha(s) util(eis) mas so $_gm_useful no formato '<sha256>  <path>' — linhas nao verificaveis"
# NOTA: o ceremony-lint marca a linha abaixo com R6 (ADVISORY) porque a
# assercao de conjunto esta 3 linhas acima, fora da janela de proximidade dele.
# A assercao EXISTE e e mais forte do que a que ele procura; nao vou reordenar
# codigo correto para caber na janela de um lint advisory.
shasum -a 256 -c .claude/governance/gate-scripts-manifest.txt --status \
  || die "V6e: manifesto ADR-192 nao casa — algum gate-script diverge do assinado"
ok "V6e: manifesto ADR-192 casa ($_gm_useful/$_gm_all membro(s) verificados)"

if [ "$DRY" -eq 1 ]; then
  printf '\n\033[33mDRY-RUN\033[0m — G0..G5 e V1..V6 verdes. Desfazendo o apply agora.\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "S — staging EXATO (TARGETS + sentinel + .asc), verificado"
# ---------------------------------------------------------------------------
# `git add` de PATHS, nunca de diretorio (R4 do ceremony-lint).
while IFS= read -r t; do
  [ -n "$t" ] || continue
  git add -- "$t"
done <<SEOF
$TARGETS
SEOF
git add -- "$APPROVED" "$APPROVED.asc"

S_TMP="$(mktemp -d)"
printf '%s\n%s\n%s\n' "$TARGETS" "$APPROVED" "$APPROVED.asc" \
  | sed '/^[[:space:]]*$/d' | sort -u > "$S_TMP/expected"
git diff --cached --name-only | sort -u > "$S_TMP/staged"
if ! cmp -s "$S_TMP/expected" "$S_TMP/staged"; then
  printf '  so no esperado: %s\n' "$(comm -23 "$S_TMP/expected" "$S_TMP/staged" | tr '\n' ' ')"
  printf '  so no staged  : %s\n' "$(comm -13 "$S_TMP/expected" "$S_TMP/staged" | tr '\n' ' ')"
  rm -rf "$S_TMP"
  die "conjunto staged != manifesto + sentinel + .asc
  (um destino identico ao HEAD nao aparece no staged — isso tambem e erro: o
   pack nao deveria carregar um arquivo que ja esta igual no vivo)"
fi
grep -qx -- "$APPROVED.asc" "$S_TMP/staged" || { rm -rf "$S_TMP"; die "a assinatura NAO ficou staged"; }
_STAGED_N="$(grep -c . "$S_TMP/staged")"
rm -rf "$S_TMP"
# Nenhuma MUDANCA DE MODO pode entrar no commit (classe R8/S314): o raw do
# index traz ":<modo-antigo> <modo-novo> ..." — antigo 000000 e arquivo novo.
MODE_CHANGES="$(git diff --cached --raw | awk '{ old=substr($1,2); if (old != "000000" && old != $2) print $NF " (" old " -> " $2 ")" }')"
[ -z "$MODE_CHANGES" ] || die "mudanca(s) de MODO no index — este pacote e de conteudo, nao de permissao:
$(printf '  %s\n' "$MODE_CHANGES")"
ok "$_STAGED_N path(s) staged == manifesto + sentinel + .asc; zero mudanca de modo"

# ---------------------------------------------------------------------------
step "C — commit (sem editor) e push"
# ---------------------------------------------------------------------------
# O Owner NAO e usuario de terminal: um `git commit` cru abre o vim e o prende
# la (S326, verbatim). O commit sai daqui, com -F e --no-edit.
case "$(cat "$COMMIT_MSG")" in
  *TO-FILL*|*PREENCHER*)
    die "a mensagem de commit ainda tem placeholder:
  $COMMIT_MSG" ;;
esac
GPG_OUT7=""
if [ "$SELFTEST" = "0" ]; then
  GPG_OUT7="$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1)" \
    || die "sentinel mudou depois do G3"
  printf '%s\n' "$GPG_OUT7" | grep '^\[GNUPG:\] VALIDSIG ' \
    | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
    || die "signer mudou depois do G3"
fi
[ "$(sed -n 's/^Anchor-SHA[^:]*: //p' "$APPROVED" | head -1)" = "$(git rev-parse HEAD)" ] \
  || die "anchor != HEAD no momento do commit"

if ! git commit -F "$COMMIT_MSG" --no-edit; then
  die "o commit falhou (hook de pre-commit? veja a saida acima).
  O STAGING esta intacto — nada se perdeu.
  Se algum editor abriu: aperte Esc, digite  :q!  e Enter."
fi
NEW_SHA="$(git rev-parse HEAD)"
RESTORE_ON_EXIT=0   # o pack vive no commit a partir daqui
ok "commit criado: $NEW_SHA"
git --no-pager log -1 --format='    %h %s' | sed 's/^/  /'

if [ "$SELFTEST" = "1" ]; then
  warn "AUTO-TESTE: push PULADO"
else
  step "PUSH"
  [ "$(git rev-parse --abbrev-ref HEAD)" = "$PUSH_BRANCH" ] \
    || die "HEAD saiu de $PUSH_BRANCH antes do push — nao empurro daqui"
  if ! git push "$PUSH_REMOTE" "HEAD:$PUSH_BRANCH"; then
    die "o push falhou. O commit $NEW_SHA esta LOCAL e intacto.
  Tente de novo:  git -C $ROOT push $PUSH_REMOTE HEAD:$PUSH_BRANCH"
  fi
  ok "empurrado para $PUSH_REMOTE/$PUSH_BRANCH"
  printf '\n  CI (ultimos 5 runs):\n'
  if command -v gh >/dev/null 2>&1; then
    gh run list --limit 5 2>/dev/null | sed 's/^/    /' || warn "gh run list falhou (rede?) — confira em github.com/Canhada-Labs/ceo-orchestration/actions"
  else
    warn "gh nao instalado — confira em github.com/Canhada-Labs/ceo-orchestration/actions"
  fi
fi

step "LAND OK"
cat <<EOF

  commit : $NEW_SHA
  paths  : $_STAGED_N   (manifesto $TARGET_COUNT + sentinel + .asc)

  Baseline esperada do CI: Validate verde; se o unico vermelho for o gate de
  latencia de hook, e o drift de runner ja conhecido (S327 licao 3) — nao e
  este pacote.

  Se algum editor abrir em QUALQUER momento:
    aperte Esc, digite  :q!  e Enter  (sai sem salvar; nada se perde).
EOF
