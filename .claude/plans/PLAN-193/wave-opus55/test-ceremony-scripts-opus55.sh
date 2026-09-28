#!/usr/bin/env bash
# test-ceremony-scripts-opus55.sh — harness do pacote de cerimonia wave-opus55.
# CEREMONY-LINT: handwritten-exception: harness de cerimonia autorado a mao,
# clone do test-ceremony-scripts-fable51.sh; nao ha gerador (o
# generate-ceremony.sh assume o layout architect/round-N/approved.md, que esta
# cerimonia nao usa).
#
# O QUE ELE PROVA. Um V-block verde nao vale nada se ele passaria tambem com a
# resposta ERRADA. Cada caso abaixo PLANTA uma divergencia especifica e exige
# que o SIGN ou o LAND fique VERMELHO por ela, NOMEANDO a razao — e o controle
# (T15c) exige VERDE sem plant. O `--dry-run` e exercitado com prova de
# RESTAURACAO byte a byte (arvore E index).
#
# ONDE ELE RODA. Num CLONE descartavel sob o scratchpad, NUNCA na arvore viva.
# O interruptor `CEREMONY_SELFTEST_NO_GPG=1` que os scripts leem e recusado
# fora do scratchpad (comparacao por REALPATH dos dois lados). O clone perde o
# remote `origin` (nenhum push e possivel dele). O harness exporta:
#   - GNUPGHOME descartavel (sob $TMPDIR: o socket do gpg-agent nao cabe num
#     caminho do scratchpad) — nenhum comando toca o chaveiro do Owner; o
#     T23 gera ali uma chave DESCARTAVEL e exercita a perna GPG real;
#   - CLAUDE_PROJECT_DIR_NATIVE sob a area de teste — o estado de runtime
#     (log de auditoria, chaves, spool) que os gates emitem nunca cai em
#     $HOME/.claude/projects/<slug-do-clone>;
#   - identidade git sintetica (o land commita no clone).
#
# POR QUE UM CLONE, E NAO A ARVORE VIVA. Os gates deste pacote sao de CORPUS
# (materiais rastreados, `git ls-files`, oraculo de canonicidade). Rodados
# antes do commit dos materiais eles medem uma arvore que nao e a que sera
# landada — a licao T-S329-2. Por isso a PRE-CONDICAO abaixo e fail-CLOSED.
#
# Uso:
#   bash .claude/plans/PLAN-193/wave-opus55/test-ceremony-scripts-opus55.sh
#   CEO_OPUS55_HARNESS_UNCOMMITTED=1 bash .../test-ceremony-scripts-opus55.sh  # pre-commit
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"

# --- constantes do pacote --------------------------------------------------
PLAN_ID="PLAN-193"
PLAN_DIR=".claude/plans/$PLAN_ID"
CEREMONY_DIR="$PLAN_DIR/wave-opus55"
SENTINEL="$PLAN_DIR/wave-opus55-approved.md"
PATCH="$CEREMONY_DIR/WOPUS55.patch"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$CEREMONY_DIR/OWNER-OPUS55-SIGN.sh"
LAND_SCRIPT="$CEREMONY_DIR/OWNER-OPUS55-LAND.sh"
HARNESS="$CEREMONY_DIR/test-ceremony-scripts-opus55.sh"
APPLY="$CEREMONY_DIR/apply-opus55-edits.py"
APPLY_DATA_CORE="$CEREMONY_DIR/edits_core.py"
APPLY_DATA_PRICING="$CEREMONY_DIR/edits_pricing.py"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
DESIGN="$CEREMONY_DIR/DESIGN-OPUS55-S357.md"
COMMIT_MSG_FILE="$CEREMONY_DIR/COMMIT-MSG-OPUS55.txt"
THREAT_MODEL="docs/threat-model.md"
SIGNERS=".claude/sentinel-signers.txt"
RAIL_FAMILIES="rail-round rail-materials-round"
RAIL_REQUIRED_FAMILY="rail-round"
WORK_TAG="opus55"
# Valores de PLANT — os literais da wave que os casos negativos usam:
PLANT_OLD_PIN="claude-opus-5"          # T16a: o pin das releases anteriores a esta wave
PLANT_OLD_EFFORT="high"                 # T16b: o default do Opus 5
PLANT_OLD_FLOOR_COUNT="3"               # T16d: o piso antes desta wave
PLANT_OLD_MODEL_LEAF='{"old":null,"new":"claude-opus-5"}'   # T16e: a folha de HEAD
PLANT_OLD_EFFORT_LEAF='{"old":null,"new":"xhigh"}'           # T16f: a folha da rodada 1 (sem opt-in)
PLANT_WRONG_HEAD_PIN="claude-opus-5-5"                       # T16g: o pin NOVO no lugar do de HEAD
RAIL_MAX_ROUNDS=4                                            # T10d/T10j: teto e rodada final (OQ-10)
RAIL_ANNEX_VERDICT="APPROVE-WITH-ANNEX"                      # T10e-i, T10k
RAIL_ANNEX_FAMILY="rail-materials-round"                     # T10f/T10g: anexo pre-registrado
RAIL_ANNEX_FILE="$CEREMONY_DIR/rail-annex.md"
RAIL_FINAL_FAMILY="rail-round"                               # T10e/T10h/T10i/T10k: anexo da rodada final (OQ-10)
RAIL_FINAL_ANNEX_FILE="$CEREMONY_DIR/rail-round-$RAIL_MAX_ROUNDS-annex.md"
PLANT_SCOPE_ANCHOR="  - .claude/settings.json"               # T4: linha do Scope
PLANT_SCOPE_EXTRA="  - scripts/doctor.sh"                    # T4: path que o patch NAO toca
PLANT_SCOPE_DROP="  - templates/settings/settings.base.json" # T5: path que o patch toca
PLANT_DRIFT_PATH="docs/ACCELERATORS.md"                      # T24a: um path do pacote
PLANT_EXTRA_ADR="ADR-999-selftest-extra.md"                  # T25a: um ADR a mais
PLANT_UNIT_DRIFT_TEST=".claude/scripts/tests/test_check_model_currency.py"  # T27a: teste do V2 FORA do patch
PLANT_NEUTRAL_DRIFT=".selftest-neutral-drift"                # T27b: deriva fora dos materiais que nao muda o V2
ADR_DIR=".claude/adr"
PLANT_DERIVATOR_OLD='"claude-opus-5-5": {"input": 4.00, "output": 20.00},'   # T19
PLANT_DERIVATOR_NEW='"claude-opus-5-5": {"input": 4.50, "output": 20.00},'
# --------------------------------------------------------------------------

PASS=0; FAIL=0; SKIP=0
die()  { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
pass() { PASS=$(( PASS + 1 )); printf '\033[32m  PASS\033[0m %s\n' "$*"; }
fail() { FAIL=$(( FAIL + 1 )); printf '\033[31m  FAIL\033[0m %s\n' "$*"; }
skip() { SKIP=$(( SKIP + 1 )); printf '\033[33m  SKIP\033[0m %s\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# Constantes que o PROPRIO LAND declara (lidas dele: uma copia aqui derivaria).
_land_const() { sed -n "s/^$1=\"\(.*\)\"\$/\1/p" "$ROOT/$LAND_SCRIPT" | head -1; }
LOG_PREFIX="$( _land_const LOG_PREFIX )"
[ -n "$LOG_PREFIX" ] || die "LOG_PREFIX nao declarado em $LAND_SCRIPT"

# O scratchpad REAL, por realpath. Os scripts comparam `$ROOT` contra este
# padrao; um WORK fora dele faz TODO caso "passar" por recusa do interruptor,
# que seria um verde vazio.
SP_REAL="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
SP_BASE="$SP_REAL/claude-501"
case "$SP_BASE" in
  /private/tmp/claude-501) : ;;
  *) die "scratchpad inesperado: $SP_BASE" ;;
esac
# (a) a raiz JA esta sob um scratchpad (clone descartavel de ensaio): usa
#     esse scratchpad; (b) a raiz e o repositorio vivo: o scratchpad tem de
#     ser o DESTE repositorio (slug = caminho absoluto com `/` -> `-`).
SESSION_DIR=""
case "$ROOT" in
  "$SP_BASE"/*/*/scratchpad/*) SESSION_DIR="${ROOT%%/scratchpad/*}/scratchpad" ;;
esac
if [ -z "$SESSION_DIR" ]; then
  REPO_SLUG="$( printf '%s' "$ROOT" | tr '/' '-' )"
  for _cand in "$SP_BASE/$REPO_SLUG"/*/scratchpad; do
    [ -d "$_cand" ] || continue
    [ -w "$_cand" ] || continue
    SESSION_DIR="$_cand"
    break
  done
fi
[ -n "$SESSION_DIR" ] && [ -d "$SESSION_DIR" ] && [ -w "$SESSION_DIR" ] \
  || die "nao achei um scratchpad GRAVAVEL para esta raiz ($ROOT) sob
  $SP_BASE/*/*/scratchpad
  Este harness so roda sob o scratchpad (os scripts recusam o interruptor de
  auto-teste em qualquer outra arvore)."
WORK="$( mktemp -d "$SESSION_DIR/ceremony-selftest-$WORK_TAG.XXXXXX" )"
GPG_HOME="$( mktemp -d "${TMPDIR:-/tmp}/${WORK_TAG}gpg.XXXXXX" )"
chmod 700 "$GPG_HOME"
export GNUPGHOME="$GPG_HOME"
export CLAUDE_PROJECT_DIR_NATIVE="$WORK/runtime-state"
mkdir -m 700 "$CLAUDE_PROJECT_DIR_NATIVE"
export GIT_AUTHOR_NAME="selftest" GIT_AUTHOR_EMAIL="selftest@example.invalid"
export GIT_COMMITTER_NAME="selftest" GIT_COMMITTER_EMAIL="selftest@example.invalid"
unset CEO_SENTINEL_UNLOCK CEO_SENTINEL_UNLOCK_ACK CEO_SENTINEL_UNLOCK_SHA256 \
      CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK 2>/dev/null || true
_cleanup() {
  # Limpeza: falhar aqui nao muda veredito nenhum (o chaveiro e descartavel).
  gpgconf --kill gpg-agent >/dev/null 2>&1 || printf ''
  rm -rf "$GPG_HOME" 2>/dev/null || true
  # Logs sao preservados quando ha FAIL (licao S329).
  if [ "${FAIL:-0}" -gt 0 ]; then
    printf '\n  logs preservados em %s/logs\n' "$WORK"
    find "$WORK" -mindepth 1 -maxdepth 1 ! -name logs -exec rm -rf {} + 2>/dev/null || true
  else
    rm -rf "$WORK"
  fi
}
trap _cleanup EXIT
printf '  area de teste: %s\n' "$WORK"
printf '  GNUPGHOME descartavel: %s\n' "$GPG_HOME"

# ---------------------------------------------------------------------------
step "PRE — T-S329-2: os materiais estao COMMITADOS na arvore viva?"
# ---------------------------------------------------------------------------
MATERIAL_LIST=(
  "$SIGN_SCRIPT" "$LAND_SCRIPT" "$HARNESS"
  "$PROPOSED"
  "$COMMIT_MSG_FILE"
  "$BASELINE_ENV"
  "$APPLY" "$APPLY_DATA_CORE" "$APPLY_DATA_PRICING"
  "$DESIGN"
  "$PATCH"
  "$SENTINEL"
)
UNCOMMITTED=""
for m in "${MATERIAL_LIST[@]}"; do
  [ -f "$ROOT/$m" ] || die "material AUSENTE na arvore viva: $m"
  git -C "$ROOT" ls-files --error-unmatch -- "$m" >/dev/null 2>&1 \
    || UNCOMMITTED="$UNCOMMITTED  $m
"
done
# O arquivo do plano: um PLAN-NNN/ sem ele e erro do validate-governance.
PLAN_FILE=""
for _pf in "$ROOT/$PLAN_DIR"-*.md; do
  [ -f "$_pf" ] || continue
  [ -z "$PLAN_FILE" ] || die "mais de um arquivo de plano $PLAN_DIR-*.md"
  PLAN_FILE="${_pf#"$ROOT/"}"
done
[ -n "$PLAN_FILE" ] || die "arquivo de plano $PLAN_DIR-*.md AUSENTE — o V9b do LAND reprovaria (orphan subdir)"
git -C "$ROOT" ls-files --error-unmatch -- "$PLAN_FILE" >/dev/null 2>&1 \
  || UNCOMMITTED="$UNCOMMITTED  $PLAN_FILE
"
if [ -n "$UNCOMMITTED" ]; then
  if [ "${CEO_OPUS55_HARNESS_UNCOMMITTED:-}" = "1" ]; then
    printf '\033[33m  CEO_OPUS55_HARNESS_UNCOMMITTED=1\033[0m — arquivo(s) ainda NAO commitado(s):\n'
    printf '%s' "$UNCOMMITTED"
    printf '        Sigo com a copia EM DISCO. Isto responde "os scripts funcionam?",\n'
    printf '        NAO responde "o pack em HEAD esta correto". Rode de novo DEPOIS\n'
    printf '        do commit dos materiais — e o unico resultado que vale.\n'
  else
    printf '\n\033[31mPRE FALHOU:\033[0m arquivo(s) de cerimonia NAO commitado(s):\n' >&2
    printf '%s' "$UNCOMMITTED" >&2
    printf '  Um harness que passa sobre um pack untracked mede outra arvore que\n' >&2
    printf '  nao a que sera landada (licao T-S329-2). Commite os materiais e\n' >&2
    printf '  repita, ou — se voce esta so exercitando os scripts antes do commit:\n' >&2
    printf '    CEO_OPUS55_HARNESS_UNCOMMITTED=1 bash %s\n' "$ROOT/$HARNESS" >&2
    exit 1
  fi
else
  printf '  todos os %d materiais e o arquivo do plano estao rastreados na arvore viva\n' "${#MATERIAL_LIST[@]}"
fi

# ---------------------------------------------------------------------------
step "0 — clone descartavel com os materiais COMMITADOS"
# ---------------------------------------------------------------------------
SRC="$WORK/src"
git clone --local --quiet --no-hardlinks "$ROOT" "$SRC" \
  || die "git clone --local falhou"
git -C "$SRC" checkout --quiet -B main "$(git -C "$ROOT" rev-parse HEAD)" \
  || die "nao consegui posicionar o clone no HEAD vivo"
# Nenhum push e possivel a partir do clone (defesa em profundidade: o LAND so
# empurra fora do auto-teste, e o T23 roda o LAND real SO em --dry-run).
git -C "$SRC" remote remove origin 2>/dev/null || true
[ -z "$(git -C "$SRC" remote)" ] || die "o clone ainda tem remote — recusado"

for m in "${MATERIAL_LIST[@]}" "$PLAN_FILE"; do
  mkdir -p "$SRC/$( dirname "$m" )"
  cp -p "$ROOT/$m" "$SRC/$m"
done
RAIL_COPIED=0
for _fam in $RAIL_FAMILIES; do
  for r in "$ROOT/$CEREMONY_DIR/$_fam"-*.md; do
    [ -f "$r" ] || continue
    cp -p "$r" "$SRC/$CEREMONY_DIR/$( basename "$r" )"
    git -C "$SRC" add -- "$CEREMONY_DIR/$( basename "$r" )" >/dev/null 2>&1 \
      || die "git add do rail falhou no clone"
    RAIL_COPIED=$(( RAIL_COPIED + 1 ))
  done
done
git -C "$SRC" add -- "${MATERIAL_LIST[@]}" "$PLAN_FILE" >/dev/null 2>&1 \
  || die "git add dos materiais falhou no clone"
# T-S329-2 / classe d9d9cab: com os materiais JA commitados em HEAD o index
# fica vazio e um commit incondicional aborta com "nothing to commit".
if git -C "$SRC" diff --cached --quiet; then
  printf '  materiais ja commitados em HEAD — commit sintetico dispensado\n'
else
  git -C "$SRC" commit -q -m "selftest: materiais da cerimonia wave-$WORK_TAG" \
    || die "commit sintetico falhou no clone"
fi
printf '  commit sintetico: %s (%d registro(s) de rail copiados)\n' \
  "$( git -C "$SRC" rev-parse HEAD )" "$RAIL_COPIED"

git -C "$SRC" apply --check "$PATCH" \
  || die "o $PATCH nao aplica no clone — o setup do harness esta errado"
printf '  %s aplica limpo no clone\n' "$( basename "$PATCH" )"

# Os casos que exigem um SIGN VERDE precisam de: o ultimo registro de cada
# familia de rail presente em APPROVE — ou no veredito de anexo que o SIGN
# aceita (materiais com o anexo; a rodada final do patch com o anexo dela,
# OQ-10) — (e a familia obrigatoria presente), e a mensagem de commit sem
# campo TO-FILL. O que faltar e plantado NO CLONE, com nota — e o SIGN real
# do Owner continua recusando (T10a/T15a provam). Quando a rodada final ja
# existe e nao autoriza, o sintetico a SUBSTITUI no clone: um registro alem
# dela seria recusado pelo nome (T10j).
# _rail_annex_ok <familia> <numero do ultimo> — o anexo que o SIGN aceitaria.
_rail_annex_ok() {
  case "$1" in
    "$RAIL_ANNEX_FAMILY") [ -s "$SRC/$RAIL_ANNEX_FILE" ] ;;
    "$RAIL_FINAL_FAMILY") [ "$2" -eq "$RAIL_MAX_ROUNDS" ] && [ -s "$SRC/$RAIL_FINAL_ANNEX_FILE" ] ;;
    *) return 1 ;;
  esac
}
RAIL_SYNTHETIC=""
for _fam in $RAIL_FAMILIES; do
  _last=""; _last_n=-1; _count=0
  for r in "$SRC/$CEREMONY_DIR/$_fam"-*.md; do
    [ -f "$r" ] || continue
    _b="$( basename "$r" )"; _n="${_b#"$_fam"-}"; _n="${_n%.md}"
    case "$_n" in ''|*[!0-9]*) continue ;; esac
    _count=$(( _count + 1 ))
    if [ "$_n" -gt "$_last_n" ]; then _last_n="$_n"; _last="$r"; fi
  done
  _verdict=""
  if [ -n "$_last" ]; then
    _verdict="$( { grep -m1 '^Rail-Verdict:' "$_last" 2>/dev/null || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]' )"
  fi
  printf '  familia %s: %d registro(s); ultimo=%s (Rail-Verdict: %s)\n' "$_fam" "$_count" \
    "${_last:+$( basename "$_last" )}" "${_verdict:-<ausente>}"
  _need=0
  if [ "$_count" -eq 0 ]; then
    [ "$_fam" = "$RAIL_REQUIRED_FAMILY" ] && _need=1
  elif [ "$_verdict" = "APPROVE" ]; then
    _need=0
  elif [ "$_verdict" = "$RAIL_ANNEX_VERDICT" ] && _rail_annex_ok "$_fam" "$_last_n"; then
    _need=0
  else
    _need=1
  fi
  if [ "$_need" = "1" ]; then
    [ "$_last_n" -ge 0 ] || _last_n=0
    if [ $(( _last_n + 1 )) -le "$RAIL_MAX_ROUNDS" ]; then
      _synth="$_fam-$(( _last_n + 1 )).md"
    else
      _synth="$( basename "$_last" )"
    fi
    cat > "$SRC/$CEREMONY_DIR/$_synth" <<EOF
# HARNESS ARTIFACT — NAO E UM REGISTRO DE RAIL REAL

Rail-Verdict: APPROVE

Este arquivo existe SO dentro do clone descartavel do
$( basename "$HARNESS" ), para destravar os casos que exigem um SIGN
verde enquanto a rodada de rail de verdade nao foi escrita. Ele nunca e
commitado na arvore viva.
EOF
    git -C "$SRC" add -- "$CEREMONY_DIR/$_synth" >/dev/null 2>&1
    git -C "$SRC" commit -q -m "selftest: rail APPROVE sintetico (so no clone)" \
      || die "nao consegui commitar o rail sintetico no clone"
    RAIL_SYNTHETIC="$RAIL_SYNTHETIC $_synth"
    printf '  \033[33mNOTA\033[0m plantei %s com APPROVE NO CLONE (nao substitui a rodada real).\n' "$_synth"
  fi
done
MSG_SYNTHETIC=0
if grep -q 'TO-FILL' "$SRC/$COMMIT_MSG_FILE"; then
  python3 - "$SRC/$COMMIT_MSG_FILE" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s2 = re.sub(r"(?m)^(Pair-Rail-Reviewed:)\s*TO-FILL\S*$", r"\1 HARNESS-SYNTHETIC-not-a-rail-record", s)
if "TO-FILL" in s2:
    sys.exit("a mensagem de commit tem TO-FILL fora do trailer Pair-Rail-Reviewed")
open(p, "w", encoding="utf-8").write(s2)
PY
  git -C "$SRC" add -- "$COMMIT_MSG_FILE" >/dev/null 2>&1
  git -C "$SRC" commit -q -m "selftest: trailer sintetico (so no clone)" \
    || die "nao consegui commitar o trailer sintetico no clone"
  MSG_SYNTHETIC=1
  printf '  \033[33mNOTA\033[0m a mensagem de commit viva tem TO-FILL; preenchi o trailer NO CLONE.\n'
fi

# ---------------------------------------------------------------------------
# Helpers: cada caso roda numa COPIA fresca do clone.
# ---------------------------------------------------------------------------
_fresh() {
  _fr_dir="$( mktemp -d "$WORK/case.XXXXXX" )"
  cp -R "$SRC/." "$_fr_dir/"
  printf '%s' "$_fr_dir"
}
_done() { [ -n "${1:-}" ] && rm -rf "$1" 2>/dev/null || printf ''; }
_logdir() { printf '%s' "$WORK/logs/$( basename "$1" )"; }
_reset_sign_fields() {
  python3 - "$1/$SENTINEL" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = re.sub(r"(?m)^Anchor-SHA: .*$", "Anchor-SHA: ANCHOR-PLACEHOLDER", s)
s = re.sub(r"(?m)^Data: .*$", "Data: DATA-PLACEHOLDER", s)
s = re.sub(r"(?m)^Approved-By: .*$", "Approved-By: APPROVED-BY-PLACEHOLDER", s)
open(p, "w", encoding="utf-8").write(s)
PY
  rm -f "$1/$SENTINEL.asc"
}
_sign() {
  mkdir -p "$( _logdir "$1" )"
  ( cd "$1" && CEREMONY_SELFTEST_NO_GPG=1 bash "$SIGN_SCRIPT" ) >"$( _logdir "$1" )/sign.log" 2>&1 </dev/null
}
_land() {
  _ld="$1"; shift
  mkdir -p "$( _logdir "$_ld" )"
  ( cd "$_ld" && CEREMONY_SELFTEST_NO_GPG=1 \
      bash "$LAND_SCRIPT" "$@" ) >"$( _logdir "$_ld" )/land.log" 2>&1 </dev/null
}
_commit_plant() {
  ( _d="$1"; shift; cd "$_d" && git add -- "$@" \
    && { git diff --cached --quiet || git commit -q -m "selftest plant"; } )
}
_commit_drop() {
  ( _d="$1"; shift; cd "$_d" && git rm -q -- "$@" && git commit -q -m "selftest drop" )
}
_expect_red() {
  _er_dir="$1"; _er_why="$2"; _er_label="$3"; _er_log="${4:-land.log}"
  if [ "$_er_rc" -eq 0 ]; then
    fail "$_er_label — o script saiu 0 com a divergencia plantada (gate MORTO)"
    return
  fi
  if grep -qF -- "$_er_why" "$( _logdir "$_er_dir" )/$_er_log"; then
    pass "$_er_label (rc=$_er_rc, razao nomeada)"
  else
    fail "$_er_label — vermelho, mas por OUTRO motivo (esperava '$_er_why'):"
    tail -8 "$( _logdir "$_er_dir" )/$_er_log" | sed 's/^/        /'
  fi
}
_set_expect() {
  python3 - "$1/$BASELINE_ENV" "$2" "$3" <<'PY'
import re, sys
path, key, value = sys.argv[1:4]
s = open(path, encoding="utf-8").read()
new, n = re.subn(r"^%s=.*$" % re.escape(key), lambda m: "%s=%s" % (key, value), s, count=1, flags=re.M)
if n != 1:
    sys.exit("chave %s nao encontrada em %s" % (key, path))
open(path, "w", encoding="utf-8").write(new)
PY
}
# Edita um arquivo trocando UMA ocorrencia exata; aborta se a ancora sumiu
# (plant MORTO nunca vira caso verde).
_replace_once() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
path, old, new = sys.argv[1:4]
old = old.replace("\\n", "\n"); new = new.replace("\\n", "\n")
s = open(path, encoding="utf-8").read()
if s.count(old) != 1:
    sys.exit("plant MORTO: a ancora aparece %d vez(es) em %s" % (s.count(old), path))
open(path, "w", encoding="utf-8").write(s.replace(old, new, 1))
PY
}

# ---------------------------------------------------------------------------
step "T0 — bijecao das chaves EXPECTED (usadas <-> declaradas)"
# ---------------------------------------------------------------------------
_used="$( grep -ohE '_expect [A-Z0-9_]+' "$ROOT/$SIGN_SCRIPT" "$ROOT/$LAND_SCRIPT" \
          | awk '{print $2}' | LC_ALL=C sort -u )"
_declared="$( grep -oE '^[A-Z0-9_]+=' "$ROOT/$BASELINE_ENV" | tr -d '=' | LC_ALL=C sort -u )"
_missing="$( comm -23 <( printf '%s\n' "$_used" ) <( printf '%s\n' "$_declared" ) )"
_orphan="$( comm -13 <( printf '%s\n' "$_used" ) <( printf '%s\n' "$_declared" ) )"
if [ -n "$_missing" ]; then
  printf '  chave(s) LIDA(s) e nao declarada(s):\n' >&2
  printf '%s\n' "$_missing" | sed 's/^/    /' >&2
  fail "T0: o land abortaria no meio do V-block (_expect e fail-CLOSED)"
elif [ -n "$_orphan" ]; then
  printf '  chave(s) declarada(s) que nada le:\n' >&2
  printf '%s\n' "$_orphan" | sed 's/^/    /' >&2
  fail "T0: expectativa sem consumidor — wire-a no V-block ou remova-a"
else
  pass "T0: $( printf '%s\n' "$_used" | wc -l | tr -d ' ' ) chave(s), bijecao fechada"
fi

# ---------------------------------------------------------------------------
step "T1 — SIGN no modo auto-teste preenche e 'assina'"
# ---------------------------------------------------------------------------
D="$( _fresh )"
if _sign "$D"; then
  if grep -q '^Anchor-SHA: [0-9a-f]\{40\}$' "$D/$SENTINEL" && [ -f "$D/$SENTINEL.asc" ] \
     && grep -qF 'P1-b: HEAD + derivador ==' "$( _logdir "$D" )/sign.log" \
     && grep -qF 'P1-e: o HEAD so difere de Patch-base nos materiais' "$( _logdir "$D" )/sign.log"; then
    pass "T1: Anchor-SHA preenchido, .asc sintetico gerado, P1-b (re-derivacao) verde e P1-e sem deriva"
  else
    fail "T1: o SIGN saiu 0 mas nao preencheu o Anchor-SHA / nao gerou o .asc / nao re-derivou / nao nomeou o P1-e"
  fi
else
  fail "T1: o SIGN reprovou:"; tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T2 — LAND --dry-run: verde E restaura arvore e index byte a byte"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T2: SIGN falhou no setup"
_fp() { ( cd "$1" && { git status --porcelain=v1; printf -- '--index--\n'; git diff --cached --name-status; } | shasum -a 256 | awk '{print $1}' ); }
FP_B="$( _fp "$D" )"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
FP_A="$( _fp "$D" )"
if [ "$_er_rc" -ne 0 ]; then
  fail "T2: o --dry-run reprovou (rc=$_er_rc):"; tail -12 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
elif [ "$FP_B" != "$FP_A" ]; then
  fail "T2: o --dry-run NAO restaurou o estado (arvore ou index sujos)"
elif [ -n "$( git -C "$D" worktree list --porcelain | awk '/^worktree /{n++} END{if (n>1) print "extra"}' )" ]; then
  fail "T2: o --dry-run deixou um worktree do V3 registrado"
else
  pass "T2: --dry-run verde, estado restaurado byte a byte e worktree do V3 removido"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T3 — patch adulterado depois da assinatura => G0 (material sujo) e G2 (binding) vermelhos"
# ---------------------------------------------------------------------------
# T3a — o patch editado na arvore depois da assinatura: o G0 recusa material
# de cerimonia modificado em relacao ao HEAD assinado (rail r1 A-R1M9-04).
D="$( _fresh )"
_sign "$D" || fail "T3a: SIGN falhou no setup"
printf '\n' >> "$D/$PATCH"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "MODIFICADO(s) em relacao ao HEAD assinado" "T3a: G0 pega o patch adulterado na arvore"
_done "$D"
# T3b — o binding em si: o sha pinado no sentinel (o unico material que pode
# estar sujo) deixa de casar o patch => G2.
D="$( _fresh )"
_sign "$D" || fail "T3b: SIGN falhou no setup"
_t3_sha="$( sed -n 's/^Patch-sha256: //p' "$D/$SENTINEL" | head -1 | tr -d '[:space:]' )"
if [ -z "$_t3_sha" ]; then
  fail "T3b: setup falhou (sem Patch-sha256 no sentinel)"
else
  _replace_once "$D/$SENTINEL" "Patch-sha256: $_t3_sha" "Patch-sha256: $( printf '%064d' 0 )" \
    || fail "T3b: plant falhou"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "patch NAO bate com o sentinel assinado" "T3b: G2 compara o sha assinado com o patch"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T4 — Scope mais largo do que o patch => SIGN (P1-c) e LAND (G4) vermelhos"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_replace_once "$D/$SENTINEL" "$PLANT_SCOPE_ANCHOR\\n" "$PLANT_SCOPE_ANCHOR\\n$PLANT_SCOPE_EXTRA\\n" \
  || fail "T4a: plant falhou"
_commit_plant "$D" "$SENTINEL" || fail "T4a: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "P1-c: o Scope do sentinel difere" "T4a: o SIGN recusa Scope largo ANTES de assinar" sign.log
_done "$D"
D="$( _fresh )"
_sign "$D" || fail "T4b: SIGN falhou no setup"
_replace_once "$D/$SENTINEL" "$PLANT_SCOPE_ANCHOR\\n" "$PLANT_SCOPE_ANCHOR\\n$PLANT_SCOPE_EXTRA\\n" \
  || fail "T4b: plant falhou"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "o Scope autoriza path(s) que o patch NAO toca" "T4b: G4 pega Scope largo editado depois de assinar"
_done "$D"

# ---------------------------------------------------------------------------
step "T5 — Scope que NAO cobre um path tocado => SIGN (P1-c) e LAND (G4) vermelhos"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_replace_once "$D/$SENTINEL" "$PLANT_SCOPE_DROP\\n" "" || fail "T5a: plant falhou"
_commit_plant "$D" "$SENTINEL" || fail "T5a: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "P1-c: o Scope do sentinel difere" "T5a: o SIGN recusa Scope incompleto ANTES de assinar" sign.log
_done "$D"
D="$( _fresh )"
_sign "$D" || fail "T5b: SIGN falhou no setup"
_replace_once "$D/$SENTINEL" "$PLANT_SCOPE_DROP\\n" "" || fail "T5b: plant falhou"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "o patch toca path(s) FORA do Scope assinado" "T5b: G4 pega Scope incompleto editado depois de assinar"
_done "$D"

# ---------------------------------------------------------------------------
step "T6 — commit depois de assinar => G1 vermelho (ancora velha)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T6: SIGN falhou no setup"
( cd "$D" && printf 'ruido\n' > .selftest-noise \
  && git add .selftest-noise \
  && git commit -q -m "move o HEAD" ) \
  || fail "T6: nao consegui mover o HEAD no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "Anchor-SHA nao bate com HEAD" "T6: G1 pega ancora invalidada"
_done "$D"

# ---------------------------------------------------------------------------
step "T7 — chave AUSENTE na base declarada => o V-block ABORTA, nunca vira 0"
# ---------------------------------------------------------------------------
D="$( _fresh )"
# Uma chave que so o V-block le (o SIGN le EXPECTED_PATCH_PATHS e
# EXPECTED_ADR_COUNT no P1-d — o T25 cobre as duas — e as EXPECTED_UNIT_* no
# P1-e, so quando ha deriva fora dos materiais — o T27 cobre).
sed -i.bak '/^EXPECTED_GENERATOR_CHECK_LINE=/d' "$D/$BASELINE_ENV" && rm -f "$D/$BASELINE_ENV.bak"
_commit_plant "$D" "$BASELINE_ENV" || fail "T7: nao consegui commitar o plant"
_sign "$D" || fail "T7: SIGN falhou no setup (ele nao le esta chave; deveria passar)"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "AUSENTE em" "T7: base declarada incompleta ABORTA"
_done "$D"

# ---------------------------------------------------------------------------
step "T8 — threat-model: a troca de status EXATA e revertida, e o SIGN segue"
# ---------------------------------------------------------------------------
D="$( _fresh )"
if grep -q '^\*\*Status:\*\* accepted$' "$D/$THREAT_MODEL" 2>/dev/null; then
  python3 - "$D/$THREAT_MODEL" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s2, n = re.subn(r"^(\*\*Status:\*\*)\s+accepted", r"\1 stale", s, count=1, flags=re.M)
if n != 1:
    sys.exit("nao consegui plantar a troca de status")
open(p, "w", encoding="utf-8").write(s2)
PY
  if _sign "$D"; then
    if grep -q '^\*\*Status:\*\* accepted$' "$D/$THREAT_MODEL" \
       && grep -qF 'REVERTI' "$( _logdir "$D" )/sign.log"; then
      pass "T8: o SIGN reverteu a troca de status e seguiu (razao NOMEADA no log)"
    else
      fail "T8: o SIGN saiu 0 mas o arquivo nao voltou a 'accepted' (ou nao nomeou a reversao)"
    fi
  else
    fail "T8: o SIGN abortou com o flip exato plantado:"
    tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
  fi
else
  skip "T8: $THREAT_MODEL nao esta em '**Status:** accepted' neste checkout"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T9 — threat-model: uma edicao DIFERENTE NAO e revertida, e o SIGN aborta"
# ---------------------------------------------------------------------------
D="$( _fresh )"
if [ -f "$D/$THREAT_MODEL" ]; then
  printf '\nlinha plantada pelo selftest\n' >> "$D/$THREAT_MODEL"
  _er_rc=0; _sign "$D" || _er_rc=$?
  if [ "$_er_rc" -eq 0 ]; then
    fail "T9: o SIGN aceitou uma arvore com $THREAT_MODEL editado de verdade"
  elif grep -qF "$THREAT_MODEL" "$( _logdir "$D" )/sign.log"; then
    pass "T9: o SIGN abortou NOMEANDO $THREAT_MODEL (rc=$_er_rc)"
  else
    fail "T9: vermelho, mas sem nomear $THREAT_MODEL:"
    tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
  fi
else
  skip "T9: $THREAT_MODEL ausente neste checkout"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T10 — rail: ultimo de CADA familia sem APPROVE, mal nomeado, alem do teto ou da rodada final, anexo fora da regra => SIGN recusa (OQ-10)"
# ---------------------------------------------------------------------------
# _rail_last <dir> <familia> — o registro de numero MAIOR da familia (ou o
# <familia>-1.md, se nao ha nenhum). Plantar SOBRE ele mantem a contagem de
# rodadas: o caso fica vermelho pela SUA razao mesmo depois que rodadas reais
# existirem (senao o teto da regra de parada dispararia antes).
_rail_last() {
  _rl_best=""; _rl_n=-1
  for _rl_f in "$1/$CEREMONY_DIR/$2"-*.md; do
    [ -f "$_rl_f" ] || continue
    _rl_b="$( basename "$_rl_f" )"; _rl_k="${_rl_b#"$2"-}"; _rl_k="${_rl_k%.md}"
    case "$_rl_k" in ''|*[!0-9]*) continue ;; esac
    if [ "$_rl_k" -gt "$_rl_n" ]; then _rl_n="$_rl_k"; _rl_best="$_rl_b"; fi
  done
  printf '%s' "${_rl_best:-$2-1.md}"
}
D="$( _fresh )"
_t10_r="$CEREMONY_DIR/$( _rail_last "$D" rail-round )"
printf '# rail plantado pelo selftest\n\nRail-Verdict: REJECT\nAchados: 1 P1 sintetico\n' > "$D/$_t10_r"
# REJECT recusa sempre — mesmo com o anexo da rodada final presente e rastreado.
printf '# anexo plantado pelo selftest\n\n1 P2 sintetico.\n' > "$D/$RAIL_FINAL_ANNEX_FILE"
_commit_plant "$D" "$_t10_r" "$RAIL_FINAL_ANNEX_FILE" || fail "T10a: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "Rail-Verdict: REJECT" "T10a: familia rail-round com REJECT no fim" sign.log
_done "$D"
D="$( _fresh )"
_t10_m="$CEREMONY_DIR/$( _rail_last "$D" rail-materials-round )"
printf '# rail plantado pelo selftest\n\nRail-Verdict: APPROVE com ressalvas\n' > "$D/$_t10_m"
_commit_plant "$D" "$_t10_m" || fail "T10b: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "$( basename "$_t10_m" )" "T10b: familia rail-materials-round lida (APPROVE qualificado recusado)" sign.log
_done "$D"
# T10d — a regra de parada pela CONTAGEM: dois registros com o MESMO numero
# (`rail-round-01.md` ao lado de `rail-round-1.md`) passam do teto sem numerar
# nenhum alem da rodada final — recusados mesmo com APPROVE.
D="$( _fresh )"
_t10_n=0
for _t10_f in "$D/$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$_t10_f" ] || continue
  if [ "$_t10_f" = "$D/$RAIL_FINAL_ANNEX_FILE" ]; then
    continue
  fi
  _t10_n=$(( _t10_n + 1 ))
done
_t10_k=0
while [ "$_t10_n" -le "$RAIL_MAX_ROUNDS" ]; do
  _t10_k=$(( _t10_k + 1 ))
  printf '# rail plantado pelo selftest\n\nRail-Verdict: APPROVE\n' > "$D/$CEREMONY_DIR/rail-round-0$_t10_k.md"
  _commit_plant "$D" "$CEREMONY_DIR/rail-round-0$_t10_k.md" || fail "T10d: nao consegui commitar o plant"
  _t10_n=$(( _t10_n + 1 ))
done
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "regra de parada: $_t10_n registro(s)" "T10d: registros alem do teto ($RAIL_MAX_ROUNDS) recusados pela contagem, mesmo com APPROVE" sign.log
_done "$D"
# T10e — OQ-10: na familia do patch o veredito de anexo so vale na rodada
# FINAL. A rodada 3 como ultima — com o anexo da rodada final presente e
# rastreado, para que a unica razao seja o numero da rodada — exige APPROVE.
D="$( _fresh )"
for _t10_f in "$D/$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$_t10_f" ] || continue
  _t10_b="$( basename "$_t10_f" )"; _t10_k="${_t10_b#rail-round-}"; _t10_k="${_t10_k%.md}"
  case "$_t10_k" in ''|*[!0-9]*) continue ;; esac
  if [ "$_t10_k" -ge "$RAIL_MAX_ROUNDS" ]; then
    _commit_drop "$D" "$CEREMONY_DIR/$_t10_b" || fail "T10e: nao consegui retirar $_t10_b do clone"
  fi
done
_t10_r="$CEREMONY_DIR/rail-round-$(( RAIL_MAX_ROUNDS - 1 )).md"
printf '# rail plantado pelo selftest\n\nRail-Verdict: %s\n' "$RAIL_ANNEX_VERDICT" > "$D/$_t10_r"
printf '# anexo plantado pelo selftest\n\n1 P2 sintetico.\n' > "$D/$RAIL_FINAL_ANNEX_FILE"
_commit_plant "$D" "$_t10_r" "$RAIL_FINAL_ANNEX_FILE" || fail "T10e: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "so vale na rodada final" "T10e: anexo na rodada $(( RAIL_MAX_ROUNDS - 1 )) da familia do patch recusado" sign.log
_done "$D"
# T10f — anexo na familia de materiais SEM o arquivo de anexo.
D="$( _fresh )"
_t10_m="$CEREMONY_DIR/$( _rail_last "$D" rail-materials-round )"
printf '# rail plantado pelo selftest\n\nRail-Verdict: %s\n' "$RAIL_ANNEX_VERDICT" > "$D/$_t10_m"
_commit_plant "$D" "$_t10_m" || fail "T10f: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "esta ausente ou vazio" "T10f: anexo pedido sem o arquivo de anexo" sign.log
_done "$D"
# T10g — CONTROLE: anexo na familia de materiais COM o anexo rastreado => verde.
D="$( _fresh )"
_t10_m="$CEREMONY_DIR/$( _rail_last "$D" rail-materials-round )"
printf '# rail plantado pelo selftest\n\nRail-Verdict: %s\n' "$RAIL_ANNEX_VERDICT" > "$D/$_t10_m"
printf '# anexo plantado pelo selftest\n\n1 P1 so em material.\n' > "$D/$RAIL_ANNEX_FILE"
_commit_plant "$D" "$_t10_m" "$RAIL_ANNEX_FILE" || fail "T10g: nao consegui commitar o plant"
if _sign "$D"; then
  pass "T10g: controle — anexo na familia de materiais com o anexo rastreado assina"
else
  fail "T10g: o SIGN recusou o anexo legitimo:"; tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
fi
_done "$D"
# T10h — OQ-10: anexo na rodada final SEM o `rail-round-<final>-annex.md` —
# o anexo da familia de materiais, presente e rastreado, nao o substitui.
D="$( _fresh )"
if [ -f "$D/$RAIL_FINAL_ANNEX_FILE" ]; then
  _commit_drop "$D" "$RAIL_FINAL_ANNEX_FILE" || fail "T10h: nao consegui retirar o anexo do clone"
fi
_t10_r="$CEREMONY_DIR/rail-round-$RAIL_MAX_ROUNDS.md"
printf '# rail plantado pelo selftest\n\nRail-Verdict: %s\n' "$RAIL_ANNEX_VERDICT" > "$D/$_t10_r"
printf '# anexo plantado pelo selftest\n\n1 P1 so em material.\n' > "$D/$RAIL_ANNEX_FILE"
_commit_plant "$D" "$_t10_r" "$RAIL_ANNEX_FILE" || fail "T10h: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "$( basename "$RAIL_FINAL_ANNEX_FILE" ) esta ausente ou vazio" "T10h: anexo da rodada final pedido sem o arquivo dela" sign.log
_done "$D"
# T10k — OQ-10: o anexo da rodada final presente, mas NAO rastreado.
D="$( _fresh )"
if [ -f "$D/$RAIL_FINAL_ANNEX_FILE" ]; then
  _commit_drop "$D" "$RAIL_FINAL_ANNEX_FILE" || fail "T10k: nao consegui retirar o anexo do clone"
fi
_t10_r="$CEREMONY_DIR/rail-round-$RAIL_MAX_ROUNDS.md"
printf '# rail plantado pelo selftest\n\nRail-Verdict: %s\n' "$RAIL_ANNEX_VERDICT" > "$D/$_t10_r"
_commit_plant "$D" "$_t10_r" || fail "T10k: nao consegui commitar o plant"
printf '# anexo plantado pelo selftest\n\n1 P2 sintetico.\n' > "$D/$RAIL_FINAL_ANNEX_FILE"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "o anexo $RAIL_FINAL_ANNEX_FILE NAO esta commitado" "T10k: anexo da rodada final nao rastreado recusado" sign.log
_done "$D"
# T10i — CONTROLE (OQ-10): a rodada FINAL com APPROVE-WITH-ANNEX e o anexo
# dela rastreado e nao-vazio => o SIGN assina, e o LAND --dry-run, que
# reaplica o teto, nao conta o anexo como registro.
D="$( _fresh )"
_t10_r="$CEREMONY_DIR/rail-round-$RAIL_MAX_ROUNDS.md"
printf '# rail plantado pelo selftest\n\nRail-Verdict: %s\n' "$RAIL_ANNEX_VERDICT" > "$D/$_t10_r"
printf '# anexo plantado pelo selftest\n\n1 P2 sintetico, verbatim do codex.\n' > "$D/$RAIL_FINAL_ANNEX_FILE"
_commit_plant "$D" "$_t10_r" "$RAIL_FINAL_ANNEX_FILE" || fail "T10i: nao consegui commitar o plant"
if _sign "$D"; then
  if grep -qF "ultimo rail-round-$RAIL_MAX_ROUNDS.md $RAIL_ANNEX_VERDICT" "$( _logdir "$D" )/sign.log"; then
    pass "T10i: controle — anexo na rodada final ($RAIL_MAX_ROUNDS) com o anexo rastreado assina"
  else
    fail "T10i: o SIGN assinou, mas nao nomeou a rodada final com o veredito de anexo"
  fi
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  if [ "$_er_rc" -eq 0 ]; then
    pass "T10i: controle — o LAND --dry-run aceita a rodada final com anexo (o anexo nao conta no teto)"
  else
    fail "T10i: o LAND --dry-run reprovou a rodada final com anexo (rc=$_er_rc):"
    tail -8 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
  fi
else
  fail "T10i: o SIGN recusou o anexo legitimo da rodada final:"; tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
fi
_done "$D"
# T10j — OQ-10: a rodada 4 e a ULTIMA. Um `rail-round-5.md`, mesmo APPROVE,
# e recusado pelo NOME no SIGN; e no LAND, plantado depois da assinatura.
D="$( _fresh )"
_t10_r="$CEREMONY_DIR/rail-round-$(( RAIL_MAX_ROUNDS + 1 )).md"
printf '# rail plantado pelo selftest\n\nRail-Verdict: APPROVE\n' > "$D/$_t10_r"
_commit_plant "$D" "$_t10_r" || fail "T10j: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "ALEM da rodada final: $_t10_r" "T10j: $( basename "$_t10_r" ) recusado pelo nome no SIGN" sign.log
_done "$D"
D="$( _fresh )"
_sign "$D" || fail "T10j: SIGN falhou no setup"
_t10_r="$CEREMONY_DIR/rail-round-$(( RAIL_MAX_ROUNDS + 1 )).md"
printf '# rail plantado pelo selftest\n\nRail-Verdict: APPROVE\n' > "$D/$_t10_r"
_commit_plant "$D" "$_t10_r" || fail "T10j: nao consegui commitar o plant"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "ALEM da rodada final ($RAIL_MAX_ROUNDS): $_t10_r" "T10j: $( basename "$_t10_r" ) recusado pelo nome no LAND"
_done "$D"
# T10l — o teto e UM so: o SIGN, o LAND e este harness declaram o mesmo.
_t10_sign="$( sed -n 's/^RAIL_MAX_ROUNDS=\([0-9][0-9]*\)$/\1/p' "$ROOT/$SIGN_SCRIPT" )"
_t10_land="$( sed -n 's/^RAIL_MAX_ROUNDS=\([0-9][0-9]*\)$/\1/p' "$ROOT/$LAND_SCRIPT" )"
if [ "$_t10_sign" = "$RAIL_MAX_ROUNDS" ] && [ "$_t10_land" = "$RAIL_MAX_ROUNDS" ]; then
  pass "T10l: SIGN, LAND e harness declaram o mesmo teto ($RAIL_MAX_ROUNDS)"
else
  fail "T10l: teto divergente — SIGN='$_t10_sign' LAND='$_t10_land' harness='$RAIL_MAX_ROUNDS'"
fi
D="$( _fresh )"
printf '# rail plantado pelo selftest\n\nRail-Verdict: APPROVE\n' > "$D/$CEREMONY_DIR/rail-round-final.md"
_commit_plant "$D" "$CEREMONY_DIR/rail-round-final.md" || fail "T10c: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "numero nao-decimal" "T10c: registro de rail mal nomeado" sign.log
_done "$D"

# ---------------------------------------------------------------------------
step "T11 — V4a: a linha do gerador e COMPARADA de verdade"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_GENERATOR_CHECK_LINE '"CHECK availableModels: MATCH (99 ids, ADR order preserved)"'
_commit_plant "$D" "$BASELINE_ENV" || fail "T11: nao consegui commitar o plant"
_sign "$D" || fail "T11: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "99 ids" "T11: V4a compara a linha do gerador"
_done "$D"

# ---------------------------------------------------------------------------
step "T12 — V4a: a contagem de availableModels e COMPARADA (caminho de re-sign)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T12: SIGN falhou no setup"
_set_expect "$D" EXPECTED_AVAILABLE_MODELS_COUNT 999
_reset_sign_fields "$D"
_commit_plant "$D" "$BASELINE_ENV" "$SENTINEL" || fail "T12: nao consegui commitar o plant"
_sign "$D" || fail "T12: re-SIGN falhou (o EXPECTED mudou)"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 999" "T12: V4a compara a contagem de ids"
_done "$D"

# ---------------------------------------------------------------------------
step "T13 — V2: a suite de unidade e REALMENTE executada e comparada"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_UNIT_PYTEST_PASSED 9999
_commit_plant "$D" "$BASELINE_ENV" || fail "T13: nao consegui commitar o plant"
_sign "$D" || fail "T13: SIGN falhou no setup"
_er_rc=0; _land "$D" || _er_rc=$?
_expect_red "$D" "esperado 9999" "T13: V2 roda o pytest e compara com o declarado"
_done "$D"

# ---------------------------------------------------------------------------
step "T14 — G5: a contagem de canonicos e COMPARADA de verdade"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T14: SIGN falhou no setup"
_set_expect "$D" EXPECTED_PATCH_CANONICAL_PATHS 7
_reset_sign_fields "$D"
_commit_plant "$D" "$BASELINE_ENV" "$SENTINEL" || fail "T14: nao consegui commitar o plant"
_sign "$D" || fail "T14: re-SIGN falhou (o EXPECTED mudou)"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 7" "T14: G5 compara a contagem de canonicos"
_done "$D"

# ---------------------------------------------------------------------------
step "T15 — trailer TO-FILL: SIGN recusa, LAND recusa no G0; controle VERDE"
# ---------------------------------------------------------------------------
D="$( _fresh )"
printf '\nPair-Rail-Reviewed: TO-FILL-AFTER-LAST-RAIL-ROUND\n' >> "$D/$COMMIT_MSG_FILE"
_commit_plant "$D" "$COMMIT_MSG_FILE" || fail "T15a: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "campo TO-FILL por preencher" "T15a: o SIGN recusa a mensagem com trailer por preencher" sign.log
_done "$D"
D="$( _fresh )"
_sign "$D" || fail "T15b: SIGN falhou no setup"
printf '\nPair-Rail-Reviewed: TO-FILL-AFTER-LAST-RAIL-ROUND\n' >> "$D/$COMMIT_MSG_FILE"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "trailer Pair-Rail-Reviewed por preencher" \
            "T15b: o LAND recusa o trailer por preencher no G0 (antes de aplicar)"
_done "$D"
D="$( _fresh )"
_sign "$D" || fail "T15c: SIGN falhou no setup"
_er_rc=0; _land "$D" || _er_rc=$?
_t15_paths="$( ( cd "$D" && git show --name-only --format='' HEAD | sed '/^$/d' | wc -l | tr -d ' ' ) )"
_t15_exp="$(( $( sed -n 's/^EXPECTED_PATCH_PATHS=//p' "$D/$BASELINE_ENV" | tr -d '"' | wc -w | tr -d ' ' ) + 2 ))"
if [ "$_er_rc" -ne 0 ]; then
  fail "T15c: o land COMPLETO reprovou SEM divergencia (os outros casos podem ser verdes vazios):"
  tail -20 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
elif ! ( cd "$D" && git show --stat --name-only --format='' HEAD | grep -qF "$( basename "$SENTINEL" ).asc" ); then
  fail "T15c: o land saiu 0 mas o commit NAO carrega a assinatura .asc"
elif [ "$_t15_paths" != "$_t15_exp" ]; then
  fail "T15c: o commit carrega $_t15_paths path(s), esperado $_t15_exp (patch + sentinel + .asc)"
elif [ -n "$( cd "$D" && git status --porcelain=v1 --untracked-files=no )" ]; then
  fail "T15c: o land commitou mas deixou modificacao rastreada na arvore"
else
  pass "T15c: controle — sem divergencia o land completo commita $_t15_paths paths, com o .asc dentro"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T16 — V4a/V6: o que a wave MUDA e provado (plant do valor ANTIGO => vermelho)"
# ---------------------------------------------------------------------------
_t16() {  # $1 rotulo, $2 chave, $3 valor plantado, $4 razao esperada
  D="$( _fresh )"
  _set_expect "$D" "$2" "$3"
  _commit_plant "$D" "$BASELINE_ENV" || fail "$1: nao consegui commitar o plant"
  _sign "$D" || fail "$1: SIGN falhou no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "$4" "$1"
  _done "$D"
}
_t16 "T16a: V4a compara o pin nos tres settings" EXPECTED_MODEL_PIN "$PLANT_OLD_PIN" \
     "esperado $PLANT_OLD_PIN nos tres settings"
_t16 "T16b: V4a compara o effortLevel nos tres settings" EXPECTED_EFFORT_LEVEL "$PLANT_OLD_EFFORT" \
     "esperado $PLANT_OLD_EFFORT nos tres settings"
_t16 "T16c: V4a prova que nenhum settings commitado carrega ultracode" EXPECTED_ULTRACODE_FILES 1 \
     "com a chave ultracode, esperado 1"
_t16 "T16d: V6e compara o tamanho do piso de VETO" EXPECTED_VETO_FLOOR_COUNT "$PLANT_OLD_FLOOR_COUNT" \
     "VETO_FLOOR_ALLOWED do ADR com"
_t16 "T16f: V6d compara a folha effortLevel (opt-in) da tabela T5.4" EXPECTED_BASELINE_EFFORT_LEAF_JSON "$PLANT_OLD_EFFORT_LEAF" \
     "folha effortLevel da tabela T5.4"
_t16 "T16g: V6g compara o pin de HEAD (a MUDANCA, nao so o estado final)" EXPECTED_HEAD_MODEL_PIN "$PLANT_WRONG_HEAD_PIN" \
     "V6g: o pin de HEAD e"
_t16 "T16e: V6d compara a folha model da tabela T5.4" EXPECTED_BASELINE_MODEL_LEAF_JSON "$PLANT_OLD_MODEL_LEAF" \
     "folha model da tabela T5.4"

# ---------------------------------------------------------------------------
step "T17/T18 — V1: os numeros de arquivos Python e shell sao DECLARADOS e comparados"
# ---------------------------------------------------------------------------
_t16 "T17: V1 compara a contagem declarada de Python" EXPECTED_PATCH_PY_FILES 3 "esperava exatamente 3"
_t16 "T18: V1 compara a contagem declarada de shell" EXPECTED_PATCH_SH_FILES 0 "esperava exatamente 0 shell"

# ---------------------------------------------------------------------------
step "T19 — o derivador e a VERDADE: SIGN (P1-b) e LAND (V3) recusam um derivador diferente"
# ---------------------------------------------------------------------------
# O patch (assinado) carrega 4.00 na linha do audit-telemetry; o modulo de
# dados do derivador passa a produzir 4.50.
D="$( _fresh )"
_replace_once "$D/$APPLY_DATA_PRICING" "$PLANT_DERIVATOR_OLD" "$PLANT_DERIVATOR_NEW" \
  || fail "T19a: plant falhou"
_commit_plant "$D" "$APPLY_DATA_PRICING" || fail "T19a: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "P1-b: o patch re-derivado do HEAD DIFERE" "T19a: o SIGN recusa patch que nao e a saida do derivador" sign.log
_done "$D"
# T19b — o mesmo modulo editado na arvore DEPOIS da assinatura: o G0 recusa
# o material sujo antes de aplicar (rail r1 A-R1M9-04). O V3 fica como
# defesa em profundidade: com o G0 e o G1 (ancora) fechando a arvore e o
# HEAD, nenhum plant alcanca o V3 sem ser pego antes; o T2 e o T15c o
# exercitam em verde.
D="$( _fresh )"
_sign "$D" || fail "T19b: SIGN falhou no setup"
_replace_once "$D/$APPLY_DATA_PRICING" "$PLANT_DERIVATOR_OLD" "$PLANT_DERIVATOR_NEW" \
  || fail "T19b: plant falhou"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "MODIFICADO(s) em relacao ao HEAD assinado" "T19b: G0 recusa o derivador editado depois da assinatura"
if grep -qF 'G1 — assinatura GPG' "$( _logdir "$D" )/land.log"; then
  fail "T19b: o LAND passou do G0 com um material sujo"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T20 — curas herdadas WIRED + nenhum literal da wave fora do bloco de constantes"
# ---------------------------------------------------------------------------
_t20_fail=0
# (c) _land_rc=$? e a PRIMEIRA instrucao de _restore (P2-h)
_t20_first="$( awk '/^_restore\(\) \{/{f=1;next} f && !/^[[:space:]]*#/ && NF {print; exit}' "$ROOT/$LAND_SCRIPT" )"
case "$_t20_first" in
  *'_land_rc=$?'*) : ;;
  *) echo "  T20c: _land_rc=\$? nao e a primeira instrucao de _restore (era: $_t20_first)"; _t20_fail=1 ;;
esac
# (d) disarm pos-commit presente (P1-c)
grep -A3 'o patch vive no commit a partir daqui' "$ROOT/$LAND_SCRIPT" \
  | grep -q 'unset CEO_KERNEL_OVERRIDE' || { echo "  T20d: disarm pos-commit ausente"; _t20_fail=1; }
# (e) VIVO: os valores que o LAND exporta satisfazem _override_granted() do hook real
grep -q '^export CEO_KERNEL_OVERRIDE="\$KERNEL_OVERRIDE_REASON"$' "$ROOT/$LAND_SCRIPT" \
  && grep -q '^export CEO_KERNEL_OVERRIDE_ACK="\$KERNEL_OVERRIDE_ACK"$' "$ROOT/$LAND_SCRIPT" \
  || { echo "  T20e: o LAND nao exporta o par a partir das constantes"; _t20_fail=1; }
_t20_reason="$( _land_const KERNEL_OVERRIDE_REASON )"
_t20_ack="$( _land_const KERNEL_OVERRIDE_ACK )"
if ! ( cd "$SRC" && python3 - "$_t20_reason" "$_t20_ack" <<'T20PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "cak", Path(".claude/hooks/check_arbitration_kernel.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
env = {"CEO_KERNEL_OVERRIDE": sys.argv[1], "CEO_KERNEL_OVERRIDE_ACK": sys.argv[2]}
sys.exit(0 if m._override_granted(env) else 1)
T20PY
) then
  echo "  T20e: o par NAO satisfaz _override_granted() do hook (reason='$_t20_reason' ack='$_t20_ack')"
  _t20_fail=1
fi
# (f) o slug do unlock do auto-teste casa a regex do hook (VIVO, pelo modulo)
_t20_slug="$( _land_const SELFTEST_UNLOCK_SLUG )"
if ! ( cd "$SRC" && python3 - "$_t20_slug" <<'T20PY'
import re, sys
from pathlib import Path
src = Path(".claude/hooks/check_canonical_edit.py").read_text(encoding="utf-8")
m = re.search(r"re\.match\(r'(\^\(ADR[^']+)'", src)
if not m:
    sys.exit("regex do unlock nao encontrada no hook")
sys.exit(0 if re.match(m.group(1), sys.argv[1]) else 1)
T20PY
) then
  echo "  T20f: SELFTEST_UNLOCK_SLUG='$_t20_slug' NAO casa a regex do CEO_SENTINEL_UNLOCK do hook"
  _t20_fail=1
fi
# (g) nenhum literal da wave (ou do molde) fora do bloco de constantes: linha
#     nao-comentario fora de "# --- constantes ... # ----" citando a wave e
#     literal que a proxima clonagem esqueceria de mover.
for _t20_script in "$SIGN_SCRIPT" "$LAND_SCRIPT"; do
  _t20_hits="$( awk '
    /^# --- constantes da cerimonia/ {inblk=1; next}
    inblk && /^# ----------+$/ {inblk=0; next}
    inblk {next}
    /^[[:space:]]*#/ {next}
    /PLAN-193|PLAN-169|wave-opus55|opus55|opus-5-5|fable|FABLE|S338/ {printf "    %d: %s\n", NR, $0}
  ' "$ROOT/$_t20_script" )"
  if [ -n "$_t20_hits" ]; then
    echo "  T20g: literal da wave fora do bloco de constantes em $_t20_script:"
    printf '%s\n' "$_t20_hits"
    _t20_fail=1
  fi
done
if [ "$_t20_fail" = "0" ]; then
  pass "T20: curas herdadas wired (override e unlock avaliados VIVOS no hook) e zero literal da wave fora das constantes"
else
  fail "T20: regressao (acima)"
fi

# ---------------------------------------------------------------------------
step "T21 — abort do LAND PRESERVA o log do gate que falhou (rail r2 P2-h)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_HARNESS_CONFIG_RC 99
_commit_plant "$D" "$BASELINE_ENV" || fail "T21: nao consegui commitar o plant"
_sign "$D" || fail "T21: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
if [ "$_er_rc" -eq 0 ]; then
  fail "T21: o land deveria ter abortado (EXPECTED plantado) e saiu 0"
else
  _t21_kept="$( find "$D/$CEREMONY_DIR" -maxdepth 1 -name "$LOG_PREFIX-*.log" 2>/dev/null | head -1 )"
  if [ -n "$_t21_kept" ]; then
    pass "T21: abort preservou o log ($( basename "$_t21_kept" ))"
  else
    fail "T21: abort NAO deixou $LOG_PREFIX-*.log no ceremony dir (regressao P2-h)"
  fi
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T22 — SIGN --derive-patch: produz EXATAMENTE o patch commitado; nunca sobrescreve"
# ---------------------------------------------------------------------------
D="$( _fresh )"
mkdir -p "$( _logdir "$D" )"
_t22_out="$WORK/t22-derived.patch"
_er_rc=0
( cd "$D" && bash "$SIGN_SCRIPT" --derive-patch "$_t22_out" ) >"$( _logdir "$D" )/derive.log" 2>&1 </dev/null || _er_rc=$?
if [ "$_er_rc" -ne 0 ]; then
  fail "T22a: --derive-patch reprovou (rc=$_er_rc):"; tail -8 "$( _logdir "$D" )/derive.log" | sed 's/^/        /'
elif ! cmp -s "$_t22_out" "$D/$PATCH"; then
  fail "T22a: --derive-patch produziu bytes DIFERENTES do $PATCH commitado"
else
  pass "T22a: HEAD + derivador (flags pinadas) == $PATCH, byte a byte"
fi
_er_rc=0
( cd "$D" && bash "$SIGN_SCRIPT" --derive-patch "$_t22_out" ) >"$( _logdir "$D" )/derive2.log" 2>&1 </dev/null || _er_rc=$?
_expect_red "$D" "o destino ja existe" "T22b: --derive-patch recusa destino existente" derive2.log
if [ -n "$( git -C "$D" worktree list --porcelain | awk '/^worktree /{n++} END{if (n>1) print "extra"}' )" ]; then
  fail "T22c: --derive-patch deixou um worktree registrado"
else
  pass "T22c: nenhum worktree da derivacao sobrou"
fi
rm -f "$_t22_out"
_done "$D"

# ---------------------------------------------------------------------------
step "T24 — Patch-base: path do patch derivado depois da base, ou base nao-ancestral => SIGN recusa"
# ---------------------------------------------------------------------------
# T24a — um land livre muda um path do pacote DEPOIS da base: o patch foi
# revisado sobre outro conteudo. Recusa ANTES da re-derivacao (P1-b).
D="$( _fresh )"
printf '\n<!-- selftest: drift de um path do pacote -->\n' >> "$D/$PLANT_DRIFT_PATH"
_commit_plant "$D" "$PLANT_DRIFT_PATH" || fail "T24a: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "mudaram entre a base e o HEAD" "T24a: o SIGN recusa um path do patch que derivou depois da base" sign.log
if grep -qF 'P1-b:' "$( _logdir "$D" )/sign.log"; then
  fail "T24a: o SIGN chegou ao P1-b — a checagem de deriva nao veio antes"
fi
_done "$D"
# T24b — a base declarada nao e ancestral do HEAD (linha paralela).
D="$( _fresh )"
_t24_cur="$( sed -n 's/^Patch-base: //p' "$D/$SENTINEL" | head -1 | tr -d '[:space:]' )"
_t24_orphan="$( cd "$D" && git commit-tree -m 'selftest: raiz paralela' 'HEAD^{tree}' )"
if [ -z "$_t24_cur" ] || [ -z "$_t24_orphan" ]; then
  fail "T24b: setup falhou (Patch-base='$_t24_cur', raiz='$_t24_orphan')"
else
  _replace_once "$D/$SENTINEL" "Patch-base: $_t24_cur" "Patch-base: $_t24_orphan" \
    || fail "T24b: plant falhou"
  _commit_plant "$D" "$SENTINEL" || fail "T24b: nao consegui commitar o plant"
  _er_rc=0; _sign "$D" || _er_rc=$?
  _expect_red "$D" "NAO e ancestral do HEAD" "T24b: o SIGN recusa uma Patch-base que nao e ancestral do HEAD" sign.log
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T25 — P1-d: base declarada defasada (paths, contagem de ADRs) => SIGN recusa ANTES do pinentry"
# ---------------------------------------------------------------------------
D="$( _fresh )"
printf '# ADR selftest\n' > "$D/$ADR_DIR/$PLANT_EXTRA_ADR"
_commit_plant "$D" "$ADR_DIR/$PLANT_EXTRA_ADR" || fail "T25a: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "P1-d: " "T25a: o SIGN recusa um ADR a mais que o V8a do LAND recusaria depois" sign.log
grep -qF "EXPECTED_ADR_COUNT" "$( _logdir "$D" )/sign.log" \
  || fail "T25a: a recusa nao nomeia EXPECTED_ADR_COUNT"
_done "$D"
D="$( _fresh )"
_t25_paths="$( sed -n 's/^EXPECTED_PATCH_PATHS=//p' "$D/$BASELINE_ENV" | head -1 | tr -d '"' )"
_set_expect "$D" EXPECTED_PATCH_PATHS "\"${_t25_paths% *}\""
_commit_plant "$D" "$BASELINE_ENV" || fail "T25b: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "P1-d: os paths do patch diferem de EXPECTED_PATCH_PATHS" \
            "T25b: o SIGN recusa uma lista de paths declarada que o G4 do LAND recusaria depois" sign.log
_done "$D"

# ---------------------------------------------------------------------------
step "T26 — G0: um path de terceiro ja STAGED => LAND recusa antes de mutar"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T26: SIGN falhou no setup"
( cd "$D" && printf 'staged\n' > .selftest-staged && git add -- .selftest-staged ) \
  || fail "T26: nao consegui stagear o plant"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "ja STAGED fora da cerimonia" "T26: o G0 recusa um path de terceiro staged"
if grep -qF 'G1 — assinatura GPG' "$( _logdir "$D" )/land.log"; then
  fail "T26: o LAND passou do G0 — a recusa veio tarde"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T27 — P1-e: deriva FORA dos materiais => o SIGN roda a suite do V2 antes do pinentry"
# ---------------------------------------------------------------------------
# T27a — um land livre acrescenta um teste a um arquivo da lista do V2 que o
# patch nao toca: a contagem medida na base deixa de valer. O SIGN recusa
# ANTES do pinentry (rail r1 A-R1M9-05), em vez de o V2 do LAND abortar
# depois da assinatura.
D="$( _fresh )"
printf '\n\ndef test_selftest_unit_drift():\n    assert True\n' >> "$D/$PLANT_UNIT_DRIFT_TEST"
_commit_plant "$D" "$PLANT_UNIT_DRIFT_TEST" || fail "T27a: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "P1-e: o HEAD difere de Patch-base fora dos materiais" \
            "T27a: o SIGN roda o V2 sobre HEAD + derivador e recusa a contagem que mudou" sign.log
if [ -f "$D/$SENTINEL.asc" ]; then
  fail "T27a: o SIGN gerou o .asc apesar da recusa"
fi
_done "$D"
# T27b — CONTROLE: deriva fora dos materiais que nao muda a suite => o SIGN
# roda o V2, casa o declarado e assina.
D="$( _fresh )"
printf 'deriva neutra do selftest\n' > "$D/$PLANT_NEUTRAL_DRIFT"
_commit_plant "$D" "$PLANT_NEUTRAL_DRIFT" || fail "T27b: nao consegui commitar o plant"
if _sign "$D"; then
  if grep -qF 'P1-e: deriva fora dos materiais; a suite do V2' "$( _logdir "$D" )/sign.log"; then
    pass "T27b: controle — deriva neutra fora dos materiais: o V2 rodou, casou e o SIGN assinou"
  else
    fail "T27b: o SIGN assinou sem rodar o V2 apesar da deriva fora dos materiais"
  fi
else
  fail "T27b: o SIGN recusou uma deriva neutra:"; tail -12 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T28 — G0: um material editado DEPOIS da assinatura => LAND recusa antes de mutar"
# ---------------------------------------------------------------------------
# A base declarada relaxada na arvore depois do SIGN seria lida pelo V-block
# sem ter sido assinada (rail r1 A-R1M9-04).
D="$( _fresh )"
_sign "$D" || fail "T28: SIGN falhou no setup"
_set_expect "$D" EXPECTED_UNIT_PYTEST_PASSED 1 || fail "T28: plant falhou"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "MODIFICADO(s) em relacao ao HEAD assinado" "T28: o G0 recusa a base declarada editada depois da assinatura"
if grep -qF 'G1 — assinatura GPG' "$( _logdir "$D" )/land.log"; then
  fail "T28: o LAND passou do G0 — a recusa veio tarde"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T29 — o derivador so EXECUTA depois do G0 provar os materiais limpos"
# ---------------------------------------------------------------------------
# Rail r2 (R2M-05): o G-PRE executava o derivador (Python dos materiais)
# ANTES da recusa de material sujo. Plant: o derivador editado DEPOIS da
# assinatura ganha um efeito colateral no import (um arquivo-marcador). O
# LAND tem de recusar no G0 e o marcador NAO pode existir. VERMELHO no LAND
# da r10 (o G-PRE rodava `--list-paths` antes do G0).
D="$( _fresh )"
_sign "$D" || fail "T29: SIGN falhou no setup"
_t29_marker="$D/$CEREMONY_DIR/T29-DERIVATOR-EXECUTED"
_replace_once "$D/$APPLY" "from __future__ import annotations\\n\\nimport argparse\\n" \
  "from __future__ import annotations\\n\\nimport pathlib as _t29\\n_t29.Path(__file__).with_name('T29-DERIVATOR-EXECUTED').write_text('x')\\nimport argparse\\n" \
  || fail "T29: plant falhou"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "MODIFICADO(s) em relacao ao HEAD assinado" "T29: o G0 recusa o derivador sujo"
if [ -e "$_t29_marker" ]; then
  fail "T29: o derivador sujo EXECUTOU antes da recusa do G0 (marcador presente)"
else
  pass "T29: o derivador sujo nao executou (marcador ausente)"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T23 — perna GPG REAL (chave DESCARTAVEL, GNUPGHOME descartavel)"
# ---------------------------------------------------------------------------
# O modo auto-teste pula o GPG. Aqui o SIGN real assina com uma chave gerada
# agora (sem senha) e o LAND --dry-run real verifica: o G1 tem de ACEITAR a
# assinatura e o signer (a chave foi plantada no .claude/sentinel-signers.txt
# DO CLONE) e o G5 tem de RECUSAR — o trilho duplo do hook
# (`.claude/security/sentinel-signers-registry.yaml`) nao conhece a chave
# descartavel. Assinatura valida NAO e autorizacao mecanica (S318).
if ! command -v gpg >/dev/null 2>&1; then
  skip "T23: gpg ausente"
else
  _t23_krc=0
  gpg --batch --pinentry-mode loopback --passphrase '' \
      --quick-gen-key 'Ceremony Harness Throwaway <harness@example.invalid>' ed25519 sign never \
      >"$WORK/t23-keygen.log" 2>&1 || _t23_krc=$?
  _t23_fpr="$( gpg --list-secret-keys --with-colons 2>/dev/null | awk -F: '/^fpr:/{print $10; exit}' )"
  if [ -z "$_t23_fpr" ]; then
    fail "T23: nao consegui gerar a chave descartavel (rc=$_t23_krc):"; tail -5 "$WORK/t23-keygen.log" | sed 's/^/        /'
  else
    D="$( _fresh )"
    printf '%s\n' "$_t23_fpr" >> "$D/$SIGNERS"
    _commit_plant "$D" "$SIGNERS" || fail "T23: nao consegui commitar o plant do signer"
    mkdir -p "$( _logdir "$D" )"
    _er_rc=0
    ( cd "$D" && CEO_SIGNER_FPR="$_t23_fpr" bash "$SIGN_SCRIPT" ) \
      >"$( _logdir "$D" )/sign.log" 2>&1 </dev/null || _er_rc=$?
    if [ "$_er_rc" -ne 0 ] || ! grep -q 'BEGIN PGP SIGNATURE' "$D/$SENTINEL.asc" 2>/dev/null; then
      fail "T23a: o SIGN real nao produziu uma assinatura (rc=$_er_rc):"
      tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
    else
      pass "T23a: o SIGN real assinou o sentinel com a chave descartavel"
      _er_rc=0
      ( cd "$D" && bash "$LAND_SCRIPT" --dry-run ) >"$( _logdir "$D" )/land.log" 2>&1 </dev/null || _er_rc=$?
      _t23_log="$( _logdir "$D" )/land.log"
      if grep -qF 'assinatura verificada' "$_t23_log" && grep -qF 'consta no rail rastreado' "$_t23_log"; then
        pass "T23b: G1 verificou a assinatura GPG real e o signer no rail .txt"
      else
        fail "T23b: G1 nao verificou a assinatura real:"; tail -8 "$_t23_log" | sed 's/^/        /'
      fi
      _expect_red "$D" "NAO concede" "T23c: G5 recusa a chave que o registro do hook nao conhece"
    fi
    _done "$D"
  fi
fi

step "RESUMO"
# ---------------------------------------------------------------------------
printf '\n  PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
printf '\n  O que NAO e coberto por padrao, e por que:\n'
printf '    - Os gates CAROS (verify-counts ~3 min, parity smoke ~35 s) rodam so\n'
printf '      nos casos de land COMPLETO (T13 ate o V2, T15c inteiro). O que o harness\n'
printf '      NAO cobre e o `Smoke Install` (parity e2e do upgrade) e o `Validate` do\n'
printf '      CI, que so rodam depois do push.\n'
if [ -n "$RAIL_SYNTHETIC" ]; then
printf '    - Registro(s) de rail SINTETICO(s) plantado(s) so no clone:%s.\n' "$RAIL_SYNTHETIC"
printf '      Os casos provam os gates, NAO que o pacote esta aprovado. Repita depois\n'
printf '      da rodada real de rail.\n'
fi
if [ "$MSG_SYNTHETIC" = "1" ]; then
printf '    - A mensagem de commit viva tem TO-FILL; o trailer foi preenchido SO no\n'
printf '      clone. O SIGN real recusa ate o CEO preencher (T15a prova).\n'
fi
printf '    - A perna GPG real (T23) usa uma chave DESCARTAVEL: prova que o SIGN\n'
printf '      assina, que o G1 verifica e que o G5 recusa o que o registro nao\n'
printf '      conhece — NAO exercita a chave do Owner (isso e o land real).\n'
printf '\n'
[ "$FAIL" -eq 0 ] || exit 1
