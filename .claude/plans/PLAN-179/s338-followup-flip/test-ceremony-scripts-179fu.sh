#!/usr/bin/env bash
# test-ceremony-scripts-179fu.sh — harness do pacote de cerimonia wave-179fu.
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
# no macOS). Nenhuma chave GPG real e usada nem gerada: o modo auto-teste
# substitui a assinatura por um `.asc` sintetico e o LAND pula a verificacao
# GPG (e SO ela).
#
# POR QUE UM CLONE, E NAO A ARVORE VIVA. Os gates deste pacote sao de CORPUS
# (materiais rastreados, `git ls-files`, oraculo de canonicidade). Rodados
# antes do commit dos materiais eles medem uma arvore que nao e a que sera
# landada — a licao T-S329-2. Por isso a PRE-CONDICAO abaixo e fail-CLOSED.
#
# NAO HA interruptor de pulo: os gates caros (suite de 21 arquivos ~7,5 min,
# verify-counts ~3 min) rodam so nos casos de land COMPLETO (T13, T15a, T15b).
# TODOS os casos rodam por padrao. O que este harness NAO cobre
# continua sendo o CI (`Validate`, `Smoke Install`), que so roda depois do push.
#
# Uso:
#   bash .claude/plans/PLAN-179/s338-followup-flip/test-ceremony-scripts-179fu.sh
#   CEO_179FU_HARNESS_UNCOMMITTED=1 bash .../test-ceremony-scripts-179fu.sh  # pre-commit
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"

# --- constantes do pacote --------------------------------------------------
PLAN_DIR=".claude/plans/PLAN-179"
CEREMONY_DIR="$PLAN_DIR/s338-followup-flip"
SENTINEL="$PLAN_DIR/wave-179fu-approved.md"
PATCH="$CEREMONY_DIR/W179FU.patch"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S338-179FU-SIGN.sh"
LAND_SCRIPT="$PLAN_DIR/OWNER-S338-179FU-LAND.sh"
APPLY="$CEREMONY_DIR/apply-179fu-flip.py"
THREAT_MODEL="docs/threat-model.md"
COMMIT_MSG_FILE="$CEREMONY_DIR/COMMIT-MSG-179FU.txt"
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
# O scratchpad tem de ser o DESTE repositorio (slug = caminho absoluto com
# `/` -> `-`): `ls */*/scratchpad | head -1` pegava o de OUTRO projeto.
REPO_SLUG="$( printf '%s' "$ROOT" | tr '/' '-' )"
SESSION_DIR=""
for _cand in "$SP_BASE/$REPO_SLUG"/*/scratchpad; do
  [ -d "$_cand" ] || continue
  [ -w "$_cand" ] || continue
  SESSION_DIR="$_cand"
  break
done
[ -n "$SESSION_DIR" ] || die "nao achei um scratchpad GRAVAVEL deste repositorio sob
  $SP_BASE/$REPO_SLUG/*/scratchpad
  Este harness so roda sob o scratchpad (os scripts recusam o interruptor de
  auto-teste em qualquer outra arvore)."
WORK="$( mktemp -d "$SESSION_DIR/ceremony-selftest-s338f179.XXXXXX" )"
# Logs sao preservados quando ha FAIL (licao S329).
trap '[ "${FAIL:-0}" -gt 0 ] && { printf "\n  logs preservados em %s/logs\n" "$WORK"; find "$WORK" -mindepth 1 -maxdepth 1 ! -name logs -exec rm -rf {} +; } || rm -rf "$WORK"' EXIT
printf '  area de teste: %s\n' "$WORK"

# ---------------------------------------------------------------------------
step "PRE — T-S329-2: os materiais estao COMMITADOS na arvore viva?"
# ---------------------------------------------------------------------------
MATERIAL_LIST=(
  "$SIGN_SCRIPT" "$LAND_SCRIPT"
  "$CEREMONY_DIR/PROPOSED-PATCH.md"
  "$COMMIT_MSG_FILE"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-179fu.sh"
  "$APPLY"
  "$CEREMONY_DIR/test-ceremony-scripts-179fu.sh"
  "$CEREMONY_DIR/DESIGN-179FU-FLIP-S338.md"
  "$PATCH"
  "$SENTINEL"
)
UNCOMMITTED=""
for m in "${MATERIAL_LIST[@]}"; do
  [ -f "$ROOT/$m" ] || die "material AUSENTE na arvore viva: $m
  Rode primeiro:  bash $ROOT/$CEREMONY_DIR/finalize-179fu.sh"
  git -C "$ROOT" ls-files --error-unmatch -- "$m" >/dev/null 2>&1 \
    || UNCOMMITTED="$UNCOMMITTED  $m
"
done
if [ -n "$UNCOMMITTED" ]; then
  if [ "${CEO_179FU_HARNESS_UNCOMMITTED:-}" = "1" ]; then
    printf '\033[33m  CEO_179FU_HARNESS_UNCOMMITTED=1\033[0m — material(is) ainda NAO commitado(s):\n'
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
    printf '    CEO_179FU_HARNESS_UNCOMMITTED=1 bash %s\n' "$ROOT/$CEREMONY_DIR/test-ceremony-scripts-179fu.sh" >&2
    exit 1
  fi
else
  printf '  todos os %d materiais estao rastreados na arvore viva\n' "${#MATERIAL_LIST[@]}"
fi

# ---------------------------------------------------------------------------
step "0 — clone descartavel com os materiais COMMITADOS"
# ---------------------------------------------------------------------------
SRC="$WORK/src"
git clone --local --quiet --no-hardlinks "$ROOT" "$SRC" \
  || die "git clone --local falhou"
git -C "$SRC" checkout --quiet -B main "$(git -C "$ROOT" rev-parse HEAD)" \
  || die "nao consegui posicionar o clone no HEAD vivo"

for m in "${MATERIAL_LIST[@]}"; do
  mkdir -p "$SRC/$( dirname "$m" )"
  cp -p "$ROOT/$m" "$SRC/$m"
done
# O finalize_patch.py compartilhado ja esta em HEAD (PLAN-183); nada a copiar.
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
    commit -q -m "selftest: materiais da cerimonia wave-179fu" \
    || die "commit sintetico falhou no clone"
fi
SYNTH_HEAD="$( git -C "$SRC" rev-parse HEAD )"
printf '  commit sintetico: %s (%d registro(s) de rail)\n' "$SYNTH_HEAD" "$RAIL_COPIED"

git -C "$SRC" apply --check "$PATCH" \
  || die "o W179FU.patch nao aplica no clone — o setup do harness esta errado"
printf '  W179FU.patch aplica limpo no clone\n'

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
test-ceremony-scripts-179fu.sh, para destravar os casos que exigem um SIGN
verde enquanto a rodada de rail de verdade nao foi escrita. Ele nunca e
commitado na arvore viva.
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
  ( cd "$_ld" && CEREMONY_SELFTEST_NO_GPG=1 \
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
_used="$( grep -ohE '_expect [A-Z0-9_]+' \
            "$ROOT/$CEREMONY_DIR/finalize-179fu.sh" \
            "$ROOT/$SIGN_SCRIPT" "$ROOT/$LAND_SCRIPT" \
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
  fail "T2: o --dry-run reprovou (rc=$_er_rc):"; tail -12 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
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
s2 = s.replace("  - .claude/hooks/SessionStart.py\n",
               "  - .claude/hooks/SessionStart.py\n  - scripts/install.sh\n", 1)
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
s2 = s.replace("  - .claude/hooks/tests/test_session_end_memory_delta.py\n", "", 1)
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
step "T11 — V4a: a linha do hook-stdout-schema e COMPARADA de verdade"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_HOOK_SCHEMA_LINE '"hook-stdout-schema: 99 wired script(s), 4 registration(s), 0 violation(s)"'
_commit_plant "$D" "$BASELINE_ENV" || fail "T11: nao consegui commitar o plant"
_sign "$D" || fail "T11: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "99 wired" "T11: V4a compara a linha do hook-stdout-schema"
_done "$D"

# ---------------------------------------------------------------------------
step "T12 — V6c: a suite do arquivo tocado e COMPARADA (caminho de re-sign)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T12: SIGN falhou no setup"
_set_expect "$D" EXPECTED_TOUCHED_SUITE_PASSED 999
_reset_sign_fields "$D"
_commit_plant "$D" "$BASELINE_ENV" "$SENTINEL" || fail "T12: nao consegui commitar o plant"
_sign "$D" || fail "T12: re-SIGN falhou (o EXPECTED mudou)"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 999" "T12: V6c compara a suite do arquivo tocado"
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
step "T15a — mensagem de commit com o trailer por preencher => vermelho"
# ---------------------------------------------------------------------------
D="$( _fresh )"
printf '\nPair-Rail-Reviewed: TO-FILL-AFTER-LAST-RAIL-ROUND\n' >> "$D/$COMMIT_MSG_FILE"
_commit_plant "$D" "$COMMIT_MSG_FILE" || fail "T15a: nao consegui commitar o plant"
_sign "$D" || fail "T15a: SIGN falhou no setup"
_er_rc=0; _land "$D" || _er_rc=$?
_expect_red "$D" "trailer Pair-Rail-Reviewed por preencher" \
            "T15a: o land recusa a mensagem com o trailer por preencher"
_done "$D"

# ---------------------------------------------------------------------------
step "T15b — sem divergencia, o LAND COMPLETO e VERDE (nao-vacuidade)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T15b: SIGN falhou no setup"
_er_rc=0; _land "$D" || _er_rc=$?
if [ "$_er_rc" -ne 0 ]; then
  fail "T15b: o land COMPLETO reprovou SEM divergencia (os outros casos podem ser verdes vazios):"
  tail -20 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
elif ! ( cd "$D" && git show --stat --name-only --format='' HEAD | grep -qF "$( basename "$SENTINEL" ).asc" ); then
  fail "T15b: o land saiu 0 mas o commit NAO carrega a assinatura .asc"
else
  pass "T15b: controle — sem divergencia o land completo commita, com o .asc dentro"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T16 — V6a: o NAO-VACUO do marcador e COMPARADO — plant => vermelho"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_MARKER_REFS_HEAD 5
_commit_plant "$D" "$BASELINE_ENV" || fail "T16: nao consegui commitar o plant"
_sign "$D" || fail "T16: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperado 5" "T16: V6a compara as referencias do marcador em HEAD"
_done "$D"

# ---------------------------------------------------------------------------
step "T17 — V1: o numero de arquivos Python do patch e DECLARADO e comparado"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_PATCH_PY_FILES 3
_commit_plant "$D" "$BASELINE_ENV" || fail "T17: nao consegui commitar o plant"
_sign "$D" || fail "T17: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperava exatamente 3" "T17: V1 compara a contagem declarada de Python"
_done "$D"

# ---------------------------------------------------------------------------
step "T18 — V1: o numero de scripts shell do patch e DECLARADO e comparado"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_PATCH_SH_FILES 3
_commit_plant "$D" "$BASELINE_ENV" || fail "T18: nao consegui commitar o plant"
_sign "$D" || fail "T18: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "esperava exatamente 3 shell" "T18: V1 compara a contagem declarada de shell"
_done "$D"

# ---------------------------------------------------------------------------
step "T19 — V3: o derivador e a VERDADE — um derivador diferente => vermelho"
# ---------------------------------------------------------------------------
# O patch (assinado) carrega o comentario do flip no SessionEnd; o derivador
# do clone passa a produzir outro texto. HEAD + derivador != pos-patch byte a
# byte => o V3 tem de ficar vermelho NOMEANDO o path.
D="$( _fresh )"
python3 - "$D/$APPLY" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
old = 'SessionStart producer of the day. PLAN-179-FOLLOWUP (S338) flips the'
new = 'SessionStart producer of the day. PLAN-179-FOLLOWUP (S338) FLIPS the'
assert s.count(old) == 1, "plant T19 MORTO: o comentario do flip nao esta no derivador"
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
awk '/if \[ "\$NO_COMMIT" = "1" \]; then/,/^else$/' "$ROOT/$CEREMONY_DIR/finalize-179fu.sh" \
  | grep -q '_fin_ok=1' || { echo "  T20a: _fin_ok=1 SUMIU do ramo --no-commit"; _t20_fail=1; }
# (b) _fin_ok inicializado (P2-e)
grep -q '^_fin_ok=0' "$ROOT/$CEREMONY_DIR/finalize-179fu.sh" \
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
# (e) VIVO: os valores exportados satisfazem _override_granted() do hook real
_t20_reason="$( sed -n 's/^export CEO_KERNEL_OVERRIDE="\(.*\)"$/\1/p' "$ROOT/$LAND_SCRIPT" | head -1 )"
_t20_ack="$( sed -n 's/^export CEO_KERNEL_OVERRIDE_ACK="\(.*\)"$/\1/p' "$ROOT/$LAND_SCRIPT" | head -1 )"
if ! python3 - "$_t20_reason" "$_t20_ack" <<'T20PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "cak", Path(".claude/hooks/check_arbitration_kernel.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
env = {"CEO_KERNEL_OVERRIDE": sys.argv[1], "CEO_KERNEL_OVERRIDE_ACK": sys.argv[2]}
sys.exit(0 if m._override_granted(env) else 1)
T20PY
then
  echo "  T20e: o par exportado NAO satisfaz _override_granted() do hook (reason='$_t20_reason' ack='$_t20_ack')"
  _t20_fail=1
fi
if [ "$_t20_fail" = "0" ]; then
  pass "T20: as 5 curas herdadas wired (incl. override avaliado VIVO no hook)"
else
  fail "T20: regressao de cura herdada (acima)"
fi

# ---------------------------------------------------------------------------
step "T21 — abort do LAND PRESERVA o log do gate que falhou (rail r2 P2-h)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_set_expect "$D" EXPECTED_ACTIVE_HOOKS_RC 99
_commit_plant "$D" "$BASELINE_ENV" || fail "T21: nao consegui commitar o plant"
_sign "$D" || fail "T21: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
if [ "$_er_rc" -eq 0 ]; then
  fail "T21: o land deveria ter abortado (EXPECTED plantado) e saiu 0"
else
  _t21_kept="$( find "$D/$CEREMONY_DIR" -maxdepth 1 -name 'land-179fu-*.log' 2>/dev/null | head -1 )"
  if [ -n "$_t21_kept" ]; then
    pass "T21: abort preservou o log ($( basename "$_t21_kept" ))"
  else
    fail "T21: abort NAO deixou land-179fu-*.log no ceremony dir (regressao P2-h)"
  fi
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T22 — abort do finalize PRESERVA index pre-existente (redesenho r4)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_t22_shadow="$D.shadow"
_t22_prop="$CEREMONY_DIR/PROPOSED-PATCH.md"
if git -C "$D" worktree add --detach "$_t22_shadow" HEAD >/dev/null 2>&1 \
   && git -C "$_t22_shadow" apply "$D/$PATCH" >/dev/null 2>&1; then
  ( cd "$D" \
    && printf '\nINDEXMARK-T22\n' >> "$_t22_prop" \
    && git add -- "$_t22_prop" \
    && git checkout -- "$_t22_prop" ) 2> "$WORK/t22-setup.err" || {
      sed 's/^/        setup-err: /' "$WORK/t22-setup.err" >&2
      fail "T22: setup do index-only falhou (stderr acima)"
    }
  _t22_wt_before="$( shasum -a 256 "$D/$_t22_prop" | awk '{print $1}' )"
  mkdir -p "$( _logdir "$D" )"
  _er_rc=0
  ( cd "$D" && CEO_179FU_SHADOW="$_t22_shadow" \
      bash "$CEREMONY_DIR/finalize-179fu.sh" \
      > "$( _logdir "$D" )/finalize-t22.log" 2>&1 ) || _er_rc=$?
  _t22_log="$( _logdir "$D" )/finalize-t22.log"
  if [ "$_er_rc" -eq 0 ]; then
    fail "T22: o finalize deveria ter abortado no guard de index nao-vazio e saiu 0"
  else
    _t22_fail=0
    grep -q "patch, Scope, Patch-base e Patch-sha256" "$_t22_log" \
      || { echo "  T22: o gerador NUNCA rodou (abort pre-gerador) — caso vacuo; log: $_t22_log"; _t22_fail=1; }
    grep -q "index ja carrega path(s) staged de outro trabalho" "$_t22_log" \
      || { echo "  T22: o abort nao foi o guard pre-add — razao errada; log: $_t22_log"; _t22_fail=1; }
    grep -q "INDEXMARK-T22" <( cd "$D" && git diff --cached -- "$_t22_prop" ) \
      || { echo "  T22: o INDEXMARK sumiu do cached (index pre-existente DESTRUIDO)"; _t22_fail=1; }
    _t22_wt_after="$( shasum -a 256 "$D/$_t22_prop" | awk '{print $1}' )"
    [ "$_t22_wt_before" = "$_t22_wt_after" ] \
      || { echo "  T22: worktree do PROPOSED nao voltou byte a byte"; _t22_fail=1; }
    if [ "$_t22_fail" = "0" ]; then
      pass "T22: abort REAL pos-gerador (guard pre-add) preservou index + worktree byte a byte"
    else
      fail "T22: pre-estado NAO preservado ou caso vacuo (acima); log: $_t22_log"
    fi
  fi
  git -C "$D" worktree remove --force "$_t22_shadow" >/dev/null 2>&1 || true
else
  fail "T22: nao consegui montar a sombra do clone a partir do W179FU.patch"
fi
_done "$D"

step "RESUMO"
# ---------------------------------------------------------------------------
printf '\n  PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
printf '\n  O que NAO e coberto por padrao, e por que:\n'
printf '    - Os gates CAROS (suite de 21 arquivos ~7,5 min, verify-counts ~3 min)\n'
printf '      rodam so nos casos de land COMPLETO (T13, T15a, T15b). O que o\n'
printf '      harness NAO cobre e o `Validate` do CI (hook-latency, corpus), que\n'
printf '      so roda depois do push; e a perna GPG.\n'
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
