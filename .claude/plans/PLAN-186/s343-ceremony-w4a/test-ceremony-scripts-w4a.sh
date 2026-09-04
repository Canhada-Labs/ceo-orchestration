#!/usr/bin/env bash
# test-ceremony-scripts-w4a.sh — harness do pacote de cerimonia wave-s343-w4a.
# CEREMONY-LINT: handwritten-exception: harness de cerimonia autorado a mao;
# nao ha gerador (o generate-ceremony.sh assume o layout
# architect/round-N/approved.md, que esta cerimonia nao usa).
#
# O QUE ELE PROVA. Um V-block verde nao vale nada se ele passaria tambem com a
# resposta ERRADA. Cada caso abaixo PLANTA uma divergencia especifica e exige
# que o SIGN ou o LAND fique VERMELHO por ela — e depois exige VERDE sem o
# plant. O `--dry-run` e exercitado com prova de RESTAURACAO byte a byte
# (arvore E index): um dry-run que deixa `git apply` no index e a armadilha da
# S272.
#
# ONDE ELE RODA. Num CLONE descartavel sob o scratchpad, NUNCA na arvore viva.
# O interruptor `CEREMONY_SELFTEST_NO_GPG=1` que os scripts leem e recusado
# fora do scratchpad (comparacao por REALPATH dos dois lados — /tmp e symlink
# no macOS). Nenhuma chave GPG real e usada nem gerada.
#
# POR QUE UM CLONE, E NAO A ARVORE VIVA. Os gates deste pacote sao de CORPUS
# (materiais rastreados, `git ls-files`, oraculo de canonicidade). Rodados
# antes do commit dos materiais eles medem uma arvore que nao e a que sera
# landada — a licao T-S329-2. Por isso a PRE-CONDICAO abaixo e fail-CLOSED.
#
# Uso:
#   bash .claude/plans/PLAN-186/s343-ceremony-w4a/test-ceremony-scripts-w4a.sh
#   CEO_W4A_HARNESS_UNCOMMITTED=1 bash .../test-ceremony-scripts-w4a.sh  # pre-commit
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"

# --- constantes do pacote --------------------------------------------------
PLAN_DIR=".claude/plans/PLAN-186"
CEREMONY_DIR="$PLAN_DIR/s343-ceremony-w4a"
SENTINEL="$PLAN_DIR/wave-s343-w4a-approved.md"
PATCH="$CEREMONY_DIR/W4A.patch"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S343-W4A-SIGN.sh"
LAND_SCRIPT="$PLAN_DIR/OWNER-S343-W4A-LAND.sh"
MEASURE_SCRIPT="$PLAN_DIR/OWNER-S343-W4A-MEASURE.sh"
APPLY="$CEREMONY_DIR/apply-w4a-validate-deletion.py"
THREAT_MODEL="docs/threat-model.md"
COMMIT_MSG_FILE="$CEREMONY_DIR/COMMIT-MSG-W4A.txt"
# --------------------------------------------------------------------------

PASS=0; FAIL=0; SKIP=0
die()  { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
pass() { PASS=$(( PASS + 1 )); printf '\033[32m  PASS\033[0m %s\n' "$*"; }
fail() { FAIL=$(( FAIL + 1 )); printf '\033[31m  FAIL\033[0m %s\n' "$*"; }
skip() { SKIP=$(( SKIP + 1 )); printf '\033[33m  SKIP\033[0m %s\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# O scratchpad REAL, por realpath. Os scripts comparam `$ROOT` contra este
# padrao; um WORK fora dele faz TODO caso "passar" por recusa do interruptor,
# que seria um verde vazio.
SP_REAL="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
SP_BASE="$SP_REAL/claude-501"
case "$SP_BASE" in
  /private/tmp/claude-501) : ;;
  *) die "scratchpad inesperado: $SP_BASE" ;;
esac
REPO_SLUG="$( printf '%s' "$ROOT" | tr '/' '-' )"
SESSION_DIR=""
for _cand in "$SP_BASE/$REPO_SLUG"/*/scratchpad; do
  [ -d "$_cand" ] || continue
  [ -w "$_cand" ] || continue
  SESSION_DIR="$_cand"
  break
done
[ -n "$SESSION_DIR" ] || die "nao achei um scratchpad GRAVAVEL deste repositorio sob
  $SP_BASE/$REPO_SLUG/*/scratchpad"
WORK="$( mktemp -d "$SESSION_DIR/ceremony-selftest-s343w4a.XXXXXX" )"
# Logs sao preservados quando ha FAIL (licao S329).
trap '[ "${FAIL:-0}" -gt 0 ] && { printf "\n  logs preservados em %s/logs\n" "$WORK"; find "$WORK" -mindepth 1 -maxdepth 1 ! -name logs -exec rm -rf {} +; } || rm -rf "$WORK"' EXIT
printf '  area de teste: %s\n' "$WORK"

# ---------------------------------------------------------------------------
step "PRE — T-S329-2: os materiais estao COMMITADOS na arvore viva?"
# ---------------------------------------------------------------------------
MATERIAL_LIST=(
  "$SIGN_SCRIPT" "$LAND_SCRIPT" "$MEASURE_SCRIPT"
  "$CEREMONY_DIR/PROPOSED-PATCH.md"
  "$COMMIT_MSG_FILE"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-w4a.sh"
  "$APPLY"
  "$CEREMONY_DIR/test-ceremony-scripts-w4a.sh"
  "$CEREMONY_DIR/DESIGN-W4A-S343.md"
  "$CEREMONY_DIR/EVIDENCE.md"
  "$PATCH"
  "$SENTINEL"
)
UNCOMMITTED=""
for m in "${MATERIAL_LIST[@]}"; do
  [ -f "$ROOT/$m" ] || die "material AUSENTE na arvore viva: $m
  Rode primeiro:  bash $ROOT/$CEREMONY_DIR/finalize-w4a.sh"
  git -C "$ROOT" ls-files --error-unmatch -- "$m" >/dev/null 2>&1 \
    || UNCOMMITTED="$UNCOMMITTED  $m
"
done
if [ -n "$UNCOMMITTED" ]; then
  if [ "${CEO_W4A_HARNESS_UNCOMMITTED:-}" = "1" ]; then
    printf '\033[33m  CEO_W4A_HARNESS_UNCOMMITTED=1\033[0m — material(is) ainda NAO commitado(s):\n'
    printf '%s' "$UNCOMMITTED"
    printf '        Sigo com a copia EM DISCO. Isto responde "os scripts funcionam?",\n'
    printf '        NAO responde "o pack em HEAD esta correto". Rode de novo DEPOIS\n'
    printf '        do commit dos materiais — e o unico resultado que vale.\n'
  else
    printf '\n\033[31mPRE FALHOU:\033[0m material(is) de cerimonia NAO commitado(s):\n' >&2
    printf '%s' "$UNCOMMITTED" >&2
    printf '  Um harness que passa sobre um pack untracked mede outra arvore que\n' >&2
    printf '  nao a que sera landada (licao T-S329-2). Commite os materiais e\n' >&2
    printf '  repita, ou — se voce esta so exercitando os scripts antes do commit:\n' >&2
    printf '    CEO_W4A_HARNESS_UNCOMMITTED=1 bash %s\n' "$ROOT/$CEREMONY_DIR/test-ceremony-scripts-w4a.sh" >&2
    exit 1
  fi
else
  printf '  todos os %d materiais estao rastreados na arvore viva\n' "${#MATERIAL_LIST[@]}"
fi

# ---------------------------------------------------------------------------
step "0 — clone descartavel com os materiais COMMITADOS"
# ---------------------------------------------------------------------------
SRC="$WORK/src"
git clone --local --quiet --no-hardlinks "$ROOT" "$SRC" || die "git clone --local falhou"
git -C "$SRC" checkout --quiet -B main "$(git -C "$ROOT" rev-parse HEAD)" \
  || die "nao consegui posicionar o clone no HEAD vivo"

for m in "${MATERIAL_LIST[@]}"; do
  mkdir -p "$SRC/$( dirname "$m" )"
  cp -p "$ROOT/$m" "$SRC/$m"
done
RAIL_COPIED=0
for r in "$ROOT/$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$r" ] || continue
  cp -p "$r" "$SRC/$CEREMONY_DIR/$( basename "$r" )"
  RAIL_COPIED=$(( RAIL_COPIED + 1 ))
done
if [ "$RAIL_COPIED" -eq 0 ]; then
  printf '  \033[33mNOTA\033[0m nenhum rail-round-*.md na arvore viva — o plant sintetico\n'
  printf '        abaixo destrava os casos; o SIGN real segue exigindo a rodada.\n'
fi

git -C "$SRC" add -- "${MATERIAL_LIST[@]}" >/dev/null 2>&1 || die "git add dos materiais falhou no clone"
for r in "$SRC/$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$r" ] || continue
  git -C "$SRC" add -- "${r#"$SRC/"}" >/dev/null 2>&1 || die "git add do rail falhou no clone"
done
# T-S329-2 / classe d9d9cab: com os materiais JA commitados em HEAD o index
# fica vazio e um commit incondicional aborta com "nothing to commit".
if git -C "$SRC" diff --cached --quiet; then
  printf '  materiais ja commitados em HEAD — commit sintetico dispensado\n'
else
  git -C "$SRC" -c user.name=selftest -c user.email=selftest@example.invalid \
    commit -q -m "selftest: materiais da cerimonia wave-s343-w4a" \
    || die "commit sintetico falhou no clone"
fi
SYNTH_HEAD="$( git -C "$SRC" rev-parse HEAD )"
printf '  commit sintetico: %s (%d registro(s) de rail)\n' "$SYNTH_HEAD" "$RAIL_COPIED"

git -C "$SRC" apply --check "$PATCH" \
  || die "o W4A.patch nao aplica no clone — o setup do harness esta errado"
printf '  W4A.patch aplica limpo no clone\n'

# O ultimo registro de rail precisa ser APPROVE para os casos que exigem o SIGN
# VERDE. Se ainda nao for, plantamos um APPROVE sintetico NO CLONE.
_last_rail=""; _last_n=-1
for r in "$SRC/$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$r" ] || continue
  _b="$( basename "$r" )"; _n="${_b#rail-round-}"; _n="${_n%.md}"
  case "$_n" in ''|*[!0-9]*) continue ;; esac
  if [ "$_n" -gt "$_last_n" ]; then _last_n="$_n"; _last_rail="$r"; fi
done
RAIL_LAST_VERDICT=""
if [ -n "$_last_rail" ]; then
  RAIL_LAST_VERDICT="$( grep -m1 '^Rail-Verdict:' "$_last_rail" 2>/dev/null | sed 's/^[^:]*: *//' | tr -d '[:space:]' || printf '' )"
fi
printf '  ultimo rail: %s (Rail-Verdict: %s)\n' "${_last_rail:+$( basename "$_last_rail" )}" "${RAIL_LAST_VERDICT:-<ausente>}"
RAIL_IS_APPROVE=0
RAIL_SYNTHETIC=0
[ "$RAIL_LAST_VERDICT" = "APPROVE" ] && RAIL_IS_APPROVE=1
if [ "$RAIL_IS_APPROVE" = "0" ]; then
  [ "$_last_n" -ge 0 ] || _last_n=0
  RAIL_SYNTHETIC=$(( _last_n + 1 ))
  cat > "$SRC/$CEREMONY_DIR/rail-round-$RAIL_SYNTHETIC.md" <<EOF
# HARNESS ARTIFACT — NAO E UM REGISTRO DE RAIL REAL

Rail-Verdict: APPROVE

Este arquivo existe SO dentro do clone descartavel do
test-ceremony-scripts-w4a.sh, para destravar os casos que exigem um SIGN verde
enquanto a rodada de rail de verdade nao foi escrita. Ele nunca e commitado na
arvore viva.
EOF
  git -C "$SRC" add -- "$CEREMONY_DIR/rail-round-$RAIL_SYNTHETIC.md" >/dev/null 2>&1
  git -C "$SRC" -c user.name=selftest -c user.email=selftest@example.invalid \
    commit -q -m "selftest: rail APPROVE sintetico (so no clone)" \
    || die "nao consegui commitar o rail sintetico no clone"
  SYNTH_HEAD="$( git -C "$SRC" rev-parse HEAD )"
  RAIL_IS_APPROVE=1
  printf '  \033[33mNOTA\033[0m o ultimo rail da arvore VIVA e "%s", nao APPROVE.\n' "${RAIL_LAST_VERDICT:-<ausente>}"
  printf '        Plantei rail-round-%s.md com APPROVE NO CLONE. Isto NAO substitui a\n' "$RAIL_SYNTHETIC"
  printf '        rodada real: o SIGN do Owner continua recusando (T10 prova).\n'
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
  ( cd "$1" && CEREMONY_SELFTEST_NO_GPG=1 bash "$SIGN_SCRIPT" ) >"$( _logdir "$1" )/sign.log" 2>&1
}
_land() {
  _ld="$1"; shift
  mkdir -p "$( _logdir "$_ld" )"
  # O G7 nao consulta a API em modo auto-teste (o `origin` do clone e um path
  # local), entao ele cai no ramo que EXIGE o reconhecimento. Todos os casos o
  # fornecem, para que cada um fique vermelho pelo SEU motivo — e o T25 o
  # OMITE de proposito, provando que o gate morde.
  _land_ack="I-ACCEPT"
  [ "${CEO_W4A_HARNESS_NO_ACK:-}" = "1" ] && _land_ack=""
  ( cd "$_ld" && CEREMONY_SELFTEST_NO_GPG=1 \
      CEO_W4A_REQUIRED_CHECK_ACK="$_land_ack" \
      bash "$LAND_SCRIPT" "$@" ) >"$( _logdir "$_ld" )/land.log" 2>&1
}
_commit_plant() {
  ( _d="$1"; shift; cd "$_d" && git add -- "$@" \
    && { git diff --cached --quiet \
         || git -c user.name=t -c user.email=t@example.invalid commit -q -m "selftest plant"; } )
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
new, n = re.subn(r"^%s=.*$" % re.escape(key), "%s=%s" % (key, value), s, count=1, flags=re.M)
if n != 1:
    sys.exit("chave %s nao encontrada em %s" % (key, path))
open(path, "w", encoding="utf-8").write(new)
PY
}

# ---------------------------------------------------------------------------
step "T0 — bijecao das chaves EXPECTED (usadas <-> declaradas)"
# ---------------------------------------------------------------------------
# O MEASURE tambem le a base declarada — deixa-lo fora do censo faria as
# chaves que so ele consome parecerem orfas, e a "cura" seria apaga-las.
_used="$( grep -ohE '_expect [A-Z0-9_]+' \
            "$ROOT/$CEREMONY_DIR/finalize-w4a.sh" \
            "$ROOT/$SIGN_SCRIPT" "$ROOT/$LAND_SCRIPT" "$ROOT/$MEASURE_SCRIPT" \
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
  if grep -q '^Anchor-SHA: [0-9a-f]\{40\}$' "$D/$SENTINEL" && [ -f "$D/$SENTINEL.asc" ]; then
    pass "T1: Anchor-SHA preenchido e .asc sintetico gerado"
  else
    fail "T1: o SIGN saiu 0 mas nao preencheu o Anchor-SHA / nao gerou o .asc"
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
  fail "T2: o --dry-run reprovou (rc=$_er_rc):"; tail -14 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
elif [ "$FP_B" != "$FP_A" ]; then
  fail "T2: o --dry-run NAO restaurou o estado (arvore ou index sujos)"
else
  pass "T2: --dry-run verde e estado restaurado byte a byte"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T3 — patch adulterado depois da assinatura => G2 vermelho"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T3: SIGN falhou no setup"
printf '\n' >> "$D/$PATCH"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "patch NAO bate com o sentinel assinado" "T3: G2 pega patch adulterado"
_done "$D"

# ---------------------------------------------------------------------------
step "T4 — Scope mais largo do que o patch => G4 vermelho (GHOST)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
python3 - "$D/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s2 = s.replace("  - .github/workflows/validate.yml\n",
               "  - .github/workflows/validate.yml\n  - scripts/install.sh\n", 1)
assert s2 != s, "plant T4 MORTO: a ancora nao existe no Scope deste sentinel"
open(p, "w", encoding="utf-8").write(s2)
PY
_commit_plant "$D" "$SENTINEL" || fail "T4: nao consegui commitar o plant"
_sign "$D" || fail "T4: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "o Scope autoriza path(s) que o patch NAO toca" "T4: G4 pega Scope largo"
_done "$D"

# ---------------------------------------------------------------------------
step "T5 — Scope que NAO cobre um path tocado => G4 vermelho (EXTRA)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
python3 - "$D/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s2 = s.replace("  - .github/workflows/smoke-install.yml\n", "", 1)
assert s2 != s, "plant T5 MORTO: a ancora nao existe no Scope deste sentinel"
open(p, "w", encoding="utf-8").write(s2)
PY
_commit_plant "$D" "$SENTINEL" || fail "T5: nao consegui commitar o plant"
_sign "$D" || fail "T5: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "o patch toca path(s) FORA do Scope assinado" "T5: G4 pega Scope incompleto"
_done "$D"

# ---------------------------------------------------------------------------
step "T6 — commit depois de assinar => G1 vermelho (ancora velha)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T6: SIGN falhou no setup"
( cd "$D" && printf 'ruido\n' > .selftest-noise \
  && git add .selftest-noise \
  && git -c user.name=t -c user.email=t@example.invalid commit -q -m "move o HEAD" ) \
  || fail "T6: nao consegui mover o HEAD no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "Anchor-SHA nao bate com HEAD" "T6: G1 pega ancora invalidada"
_done "$D"

# ---------------------------------------------------------------------------
step "T7 — chave AUSENTE na base declarada => o V-block ABORTA, nunca vira 0"
# ---------------------------------------------------------------------------
D="$( _fresh )"
sed -i.bak '/^EXPECTED_PATCH_PATHS=/d' "$D/$BASELINE_ENV" && rm -f "$D/$BASELINE_ENV.bak"
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
step "T10 — ultimo rail sem APPROVE => o SIGN recusa"
# ---------------------------------------------------------------------------
D="$( _fresh )"
printf '# rail plantado pelo selftest\n\nRail-Verdict: REJECT\nAchados: 1 P1 sintetico\n' \
  > "$D/$CEREMONY_DIR/rail-round-99.md"
_commit_plant "$D" "$CEREMONY_DIR/rail-round-99.md" || fail "T10: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
if [ "$_er_rc" -eq 0 ]; then
  fail "T10: o SIGN assinou com o ULTIMO registro de rail em REJECT"
elif grep -qF "Rail-Verdict: REJECT" "$( _logdir "$D" )/sign.log"; then
  pass "T10: o SIGN recusou nomeando o veredito do ultimo rail (rc=$_er_rc)"
else
  fail "T10: vermelho, mas sem nomear o veredito do rail:"
  tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T11 — V1c: a contagem de steps do job validate e COMPARADA de verdade"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_VALIDATE_STEPS_POST 99
_commit_plant "$D" "$BASELINE_ENV" || fail "T11: nao consegui commitar o plant"
_sign "$D" || fail "T11: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 99" "T11: V1c compara os steps do job validate"
_done "$D"

# ---------------------------------------------------------------------------
step "T12 — V1c: o timeout do Smoke e COMPARADO (o bump nao passa por acaso)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_SMOKE_TIMEOUT_POST 999
_commit_plant "$D" "$BASELINE_ENV" || fail "T12: nao consegui commitar o plant"
_sign "$D" || fail "T12: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 999" "T12: V1c compara o timeout-minutes do job smoke"
_done "$D"

# ---------------------------------------------------------------------------
step "T13 — V5: a COBERTURA e re-derivada de verdade (o oraculo da wave)"
# ---------------------------------------------------------------------------
# Este e o caso que impede o gate central da wave de virar decorativo: se o V5
# nao rodasse `pytest --collect-only`, um numero absurdo na base passaria.
D="$( _fresh )"
_set_expect "$D" EXPECTED_NODEID_HOOKS 999999
_commit_plant "$D" "$BASELINE_ENV" || fail "T13: nao consegui commitar o plant"
_sign "$D" || fail "T13: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "DECLARADO 999999" "T13: V5 coleta os node-ids e compara"
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
step "T15 — V1: a contagem de shell do patch e DECLARADA e comparada"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_PATCH_SH_FILES 3
_commit_plant "$D" "$BASELINE_ENV" || fail "T15: nao consegui commitar o plant"
_sign "$D" || fail "T15: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperava exatamente 3 shell" "T15: V1 compara a contagem declarada de shell"
_done "$D"

# ---------------------------------------------------------------------------
step "T16 — V6a: o NAO-VACUO pos-patch e comparado (0 referencias)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_DELETED_STEP_REFS_POST 1
_commit_plant "$D" "$BASELINE_ENV" || fail "T16: nao consegui commitar o plant"
_sign "$D" || fail "T16: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 1 nos dois" "T16: V6a conta as referencias aos steps deletados"
_done "$D"

# ---------------------------------------------------------------------------
step "T17 — G6: o NAO-VACUO em HEAD e comparado (a wave deleta algo que existe)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_VALIDATE_STEPS_HEAD 999
_commit_plant "$D" "$BASELINE_ENV" || fail "T17: nao consegui commitar o plant"
_sign "$D" || fail "T17: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "steps em HEAD, esperado 999" "T17: G6 le o HEAD antes de mutar"
_done "$D"

# ---------------------------------------------------------------------------
step "T18 — V4a: o actionlint e REALMENTE executado e comparado"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_ACTIONLINT_RC 9
_commit_plant "$D" "$BASELINE_ENV" || fail "T18: nao consegui commitar o plant"
_sign "$D" || fail "T18: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 9" "T18: V4a roda o actionlint e compara o rc"
_done "$D"

# ---------------------------------------------------------------------------
step "T19 — V3: o derivador e a VERDADE — um derivador diferente => vermelho"
# ---------------------------------------------------------------------------
# O patch (assinado) carrega a amostra `92m32s` no bloco de derivacao MEDIDA;
# o derivador do clone passa a produzir `92m33s`. HEAD + derivador != pos-patch
# byte a byte => o V3 fica vermelho NOMEANDO o path.
#
# O plant e num BYTE que as pos-condicoes do proprio derivador NAO checam, de
# proposito: plantar num byte checado faria o derivador RECUSAR e o V3
# morreria com "o derivador RECUSOU sobre HEAD limpo" — vermelho, mas provando
# a pos-condicao do script, nao a comparacao byte a byte do V3.
D="$( _fresh )"
python3 - "$D/$APPLY" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
old = "33809424817  92m32s"
new = "33809424817  92m33s"
assert s.count(old) == 1, "plant T19 MORTO: a amostra medida nao esta no derivador"
open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
PY
_commit_plant "$D" "$APPLY" || fail "T19: nao consegui commitar o plant"
_sign "$D" || fail "T19: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "V3: a arvore pos-patch NAO e a saida do derivador" "T19: V3 prova a reprodutibilidade byte a byte"
_done "$D"

# ---------------------------------------------------------------------------
step "T20 — curas herdadas do rail-materials seguem WIRED (contrato executavel)"
# ---------------------------------------------------------------------------
_t20_fail=0
# (a) _fin_ok=1 dentro do ramo --no-commit (P1-d)
awk '/if \[ "\$NO_COMMIT" = "1" \]; then/,/^else$/' "$ROOT/$CEREMONY_DIR/finalize-w4a.sh" \
  | grep -q '_fin_ok=1' || { echo "  T20a: _fin_ok=1 SUMIU do ramo --no-commit"; _t20_fail=1; }
# (b) _fin_ok inicializado (P2-e)
grep -q '^_fin_ok=0' "$ROOT/$CEREMONY_DIR/finalize-w4a.sh" \
  || { echo "  T20b: init _fin_ok=0 ausente"; _t20_fail=1; }
# (c) _land_rc=$? e a PRIMEIRA instrucao de _restore (P2-h)
_t20_first="$( awk '/^_restore\(\) \{/{f=1;next} f && !/^[[:space:]]*#/ && NF {print; exit}' "$ROOT/$LAND_SCRIPT" )"
case "$_t20_first" in
  *'_land_rc=$?'*) : ;;
  *) echo "  T20c: _land_rc=\$? nao e a primeira instrucao de _restore (era: $_t20_first)"; _t20_fail=1 ;;
esac
# (d) disarm pos-commit presente (P1-c)
grep -A3 'o patch vive no commit a partir daqui' "$ROOT/$LAND_SCRIPT" \
  | grep -q 'unset CEO_KERNEL_OVERRIDE' || { echo "  T20d: disarm pos-commit ausente"; _t20_fail=1; }
# (e) VIVO: os valores exportados satisfazem _override_granted() do hook real.
#     Esta wave TOCA .github/workflows/validate.yml, que esta em _KERNEL_PATHS —
#     um par reason/ack invalido faria o land abortar no `git apply`.
_t20_reason="$( sed -n 's/^export CEO_KERNEL_OVERRIDE="\(.*\)"$/\1/p' "$ROOT/$LAND_SCRIPT" | head -1 )"
_t20_ack="$( sed -n 's/^export CEO_KERNEL_OVERRIDE_ACK="\(.*\)"$/\1/p' "$ROOT/$LAND_SCRIPT" | head -1 )"
if ! ( cd "$ROOT" && python3 - "$_t20_reason" "$_t20_ack" <<'T20PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "cak", Path(".claude/hooks/check_arbitration_kernel.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
env = {"CEO_KERNEL_OVERRIDE": sys.argv[1], "CEO_KERNEL_OVERRIDE_ACK": sys.argv[2]}
sys.exit(0 if m._override_granted(env) else 1)
T20PY
)
then
  echo "  T20e: o par exportado NAO satisfaz _override_granted() do hook (reason='$_t20_reason' ack='$_t20_ack')"
  _t20_fail=1
fi
# (f) VIVO: o validate.yml E kernel-guarded — se deixar de ser, o override
#     acima passa a ser cerimonia sem sujeito e o comentario mente.
if ! ( cd "$ROOT" && python3 - <<'T20PY2'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "cak2", Path(".claude/hooks/check_arbitration_kernel.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
paths = set(getattr(m, "_KERNEL_PATHS", []))
sys.exit(0 if ".github/workflows/validate.yml" in paths else 1)
T20PY2
)
then
  echo "  T20f: .github/workflows/validate.yml NAO esta em _KERNEL_PATHS — o LAND arma um override sem sujeito"
  _t20_fail=1
fi
# (g) o slug do unlock do auto-teste casa a gramatica do hook (um slug com
#     maiuscula derruba o G5 inteiro em SILENCIO — licao da S338)
_t20_slug="$( sed -n 's/.*CEO_SENTINEL_UNLOCK=\([A-Za-z0-9-]*\).*/\1/p' "$ROOT/$LAND_SCRIPT" | head -1 )"
case "$_t20_slug" in
  PLAN-[0-9][0-9][0-9]-*[A-Z]*) echo "  T20g: slug de unlock com MAIUSCULA: $_t20_slug"; _t20_fail=1 ;;
  PLAN-[0-9][0-9][0-9]-*) : ;;
  *) echo "  T20g: slug de unlock fora da gramatica PLAN-NNN-<slug>: '$_t20_slug'"; _t20_fail=1 ;;
esac
if [ "$_t20_fail" = "0" ]; then
  pass "T20: 7 curas/contratos herdados wired (incl. override e kernel avaliados VIVOS)"
else
  fail "T20: regressao de cura herdada (acima)"
fi

# ---------------------------------------------------------------------------
step "T21 — mensagem de commit com o trailer por preencher => vermelho"
# ---------------------------------------------------------------------------
D="$( _fresh )"
printf '\nPair-Rail-Reviewed: TO-FILL-AFTER-LAST-RAIL-ROUND\n' >> "$D/$COMMIT_MSG_FILE"
_commit_plant "$D" "$COMMIT_MSG_FILE" || fail "T21: nao consegui commitar o plant"
_sign "$D" || fail "T21: SIGN falhou no setup"
_er_rc=0; _land "$D" || _er_rc=$?
_expect_red "$D" "trailer Pair-Rail-Reviewed por preencher" \
            "T21: o land recusa a mensagem com o trailer por preencher"
_done "$D"

# ---------------------------------------------------------------------------
step "T22 — abort do LAND PRESERVA o log do gate que falhou (rail r2 P2-h)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_ACTIONLINT_RC 9
_commit_plant "$D" "$BASELINE_ENV" || fail "T22: nao consegui commitar o plant"
_sign "$D" || fail "T22: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
if [ "$_er_rc" -eq 0 ]; then
  fail "T22: o land deveria ter abortado (EXPECTED plantado) e saiu 0"
else
  _t22_kept="$( find "$D/$CEREMONY_DIR" -maxdepth 1 -name 'land-w4a-*.log' 2>/dev/null | head -1 )"
  if [ -n "$_t22_kept" ]; then
    pass "T22: abort preservou o log ($( basename "$_t22_kept" ))"
  else
    fail "T22: abort NAO deixou land-w4a-*.log no ceremony dir (regressao P2-h)"
  fi
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T23 — MEASURE: sem o land em HEAD, ele RECUSA (nunca mede o baseline 2x)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
mkdir -p "$( _logdir "$D" )"
_er_rc=0
( cd "$D" && bash "$MEASURE_SCRIPT" --dry-run ) > "$( _logdir "$D" )/measure.log" 2>&1 || _er_rc=$?
if [ "$_er_rc" -eq 0 ]; then
  fail "T23: o MEASURE rodou numa arvore que AINDA tem os dois steps"
elif grep -qF "O land nao aconteceu" "$( _logdir "$D" )/measure.log"; then
  pass "T23: o MEASURE recusou nomeando a pre-condicao (rc=$_er_rc)"
elif grep -qE "gh (ausente|nao esta autenticado)" "$( _logdir "$D" )/measure.log"; then
  skip "T23: o MEASURE parou antes, no substrato (gh ausente/nao autenticado)"
else
  fail "T23: vermelho, mas por OUTRO motivo:"
  tail -8 "$( _logdir "$D" )/measure.log" | sed 's/^/        /'
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T26 — V6c: a contagem do censo de comentarios e COMPARADA de verdade"
# ---------------------------------------------------------------------------
# Controle positivo do achado P2 do rail codex r2. O V6c tem duas pernas: a
# AUSENCIA dos literais velhos e a PRESENCA do nome do job que virou dono da
# cobertura. Este caso planta a segunda — sem ela, comentarios APAGADOS (em
# vez de reescritos) passariam.
D="$( _fresh )"
_set_expect "$D" EXPECTED_MATRIX_JOB_MENTIONS 42
_commit_plant "$D" "$BASELINE_ENV" || fail "T26: nao consegui commitar o plant"
_sign "$D" || fail "T26: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 42" "T26: V6c compara as mencoes ao job da matriz"
_done "$D"

# ---------------------------------------------------------------------------
step "T25 — G7: sem o reconhecimento da janela de required-check, o LAND recusa"
# ---------------------------------------------------------------------------
# Controle POSITIVO do achado P1 do rail codex r1 (que confirmou o r24 da
# S340). Sem `CEO_W4A_REQUIRED_CHECK_ACK=I-ACCEPT`, e com a API inacessivel
# (o `origin` do clone e um path local), o gate tem de PARAR o land — nao
# imprimir um aviso no meio de um V-block de varios minutos.
D="$( _fresh )"
_sign "$D" || fail "T25: SIGN falhou no setup"
# A atribuicao vai numa linha PROPRIA, com `unset` explicito depois: um
# prefixo `VAR=1 minha_funcao` PERSISTE apos o retorno em bash (a semantica de
# funcao nao e a de comando externo), e o vazamento derrubaria o T24 abaixo
# pelo motivo errado.
CEO_W4A_HARNESS_NO_ACK=1
export CEO_W4A_HARNESS_NO_ACK
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
unset CEO_W4A_HARNESS_NO_ACK
_expect_red "$D" "janela de required-check esta ABERTA" \
            "T25: G7 exige o reconhecimento explicito do Owner"
_done "$D"

# ---------------------------------------------------------------------------
step "T24 — sem divergencia, o LAND COMPLETO e VERDE (nao-vacuidade)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T24: SIGN falhou no setup"
_er_rc=0; _land "$D" || _er_rc=$?
if [ "$_er_rc" -ne 0 ]; then
  fail "T24: o land COMPLETO reprovou SEM divergencia (os outros casos podem ser verdes vazios):"
  tail -25 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
elif ! ( cd "$D" && git show --stat --name-only --format='' HEAD | grep -qF "$( basename "$SENTINEL" ).asc" ); then
  fail "T24: o land saiu 0 mas o commit NAO carrega a assinatura .asc"
else
  pass "T24: controle — sem divergencia o land completo commita, com o .asc dentro"
fi
_done "$D"

step "RESUMO"
# ---------------------------------------------------------------------------
printf '\n  PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
printf '\n  O que NAO e coberto por padrao, e por que:\n'
printf '    - Os gates CAROS (V2 suite ~1 min, verify-counts ~3 min, governanca\n'
printf '      completa) rodam so nos casos de land COMPLETO (T21, T24). O V2 nao\n'
printf '      tem plant proprio: ele nao compara contagem (decisao declarada no\n'
printf '      LAND), e o T24 ja prova que ele EXECUTA.\n'
printf '    - As 3 CORRIDAS do MEASURE nao sao exercitaveis num clone: elas\n'
printf '      empurram para o `main` remoto. O T23 cobre a pre-condicao — a unica\n'
printf '      perna do MEASURE que decide alguma coisa antes do push.\n'
printf '    - O `Validate` e o `Smoke Install` do CI so rodam depois do push.\n'
printf '    - O G7 NAO consulta a API do GitHub em modo auto-teste (o origin do\n'
printf '      clone e um path local): o T25 prova o ramo que EXIGE o\n'
printf '      reconhecimento; o ramo `covered` (os dois legs ja obrigatorios)\n'
printf '      so e exercitavel contra a config viva, no land real.\n'
if [ "$RAIL_SYNTHETIC" != "0" ]; then
printf '    - O ultimo rail da arvore VIVA nao e APPROVE; os casos que exigem um\n'
printf '      SIGN verde rodaram sobre um rail-round-%s.md SINTETICO, plantado so\n' "$RAIL_SYNTHETIC"
printf '      no clone. Eles provam os gates do LAND, NAO que o pacote esta\n'
printf '      aprovado. Repita depois da rodada real de rail.\n'
fi
printf '    - Nenhuma chave GPG real e exercitada: o modo auto-teste substitui a\n'
printf '      assinatura por um .asc sintetico e o LAND pula a verificacao GPG\n'
printf '      (e SO ela). A perna GPG e exercitada pelo land real do Owner.\n'
printf '\n'
[ "$FAIL" -eq 0 ] || exit 1
