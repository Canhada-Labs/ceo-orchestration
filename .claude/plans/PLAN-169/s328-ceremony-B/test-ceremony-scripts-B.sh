#!/usr/bin/env bash
# test-ceremony-scripts-B.sh — harness do pacote de cerimonia wave-s328-B.
# CEREMONY-LINT: handwritten-exception: harness de cerimonia autorado a mao;
# nao ha gerador (o generate-ceremony.sh assume o layout
# architect/round-N/approved.md, que esta cerimonia nao usa).
#
# O QUE ELE PROVA. Um V-block verde nao vale nada se ele passaria tambem com a
# resposta ERRADA. Cada caso abaixo PLANTA uma divergencia especifica e exige
# que o LAND fique VERMELHO por ela — e depois exige VERDE sem o plant. O
# `--dry-run` e exercitado com prova de RESTAURACAO byte a byte (arvore E
# index): um dry-run que deixa `git apply` no index e a armadilha da S272.
#
# ONDE ELE RODA. Num CLONE descartavel sob o scratchpad, NUNCA na arvore viva.
# O interruptor `CEREMONY_SELFTEST_NO_GPG=1` que os scripts leem e recusado
# fora do scratchpad (comparacao por REALPATH dos dois lados — /tmp e symlink
# no macOS, e comparar string mediria formato, nao caminho).
#
# POR QUE UM CLONE, E NAO A ARVORE VIVA. Os gates deste pacote sao de CORPUS
# (materiais rastreados, `git ls-files`, oraculo de canonicidade). Rodados
# antes do commit dos materiais eles medem uma arvore que nao e a que sera
# landada — a licao "bateria rodada ANTES da ultima edicao nao e bateria".
# O clone e feito com `git clone --local` a partir de um commit SINTETICO que
# carrega os materiais, entao o corpus visto aqui e o corpus do land.
#
# Uso:  bash .claude/plans/PLAN-169/s328-ceremony-B/test-ceremony-scripts-B.sh
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"

# --- constantes do pacote --------------------------------------------------
PLAN_DIR=".claude/plans/PLAN-169"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-B"
SENTINEL="$PLAN_DIR/wave-s328-B-approved.md"
PATCH="$CEREMONY_DIR/B.patch"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S328-B-SIGN.sh"
LAND_SCRIPT="$PLAN_DIR/OWNER-S328-B-LAND.sh"
PROFILER=".claude/scripts/profile-opus-4-7.py"
GATE_TEST=".claude/scripts/tests/test_hook_latency_relative_gate.py"
PLAN_MD="$PLAN_DIR-closure-and-cross-session-evolution.md"
# --------------------------------------------------------------------------

PASS=0; FAIL=0
die()  { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
pass() { PASS=$(( PASS + 1 )); printf '\033[32m  PASS\033[0m %s\n' "$*"; }
fail() { FAIL=$(( FAIL + 1 )); printf '\033[31m  FAIL\033[0m %s\n' "$*"; }
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
# O scratchpad tem de ser o DESTE repositorio. `ls */*/scratchpad | head -1`
# pegava o de OUTRO projeto (medido: caiu num `-…-42ledger-core`, cujos objetos
# git sao de outra arvore) e todo caso morria em "Permission denied". O slug e
# o mesmo que o harness usa: caminho absoluto com `/` -> `-`.
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
WORK="$( mktemp -d "$SESSION_DIR/ceremony-selftest-s328B.XXXXXX" )"
trap 'rm -rf "$WORK"' EXIT
printf '  area de teste: %s\n' "$WORK"

# ---------------------------------------------------------------------------
step "0 — clone descartavel com os materiais COMMITADOS"
# ---------------------------------------------------------------------------
# Os materiais ainda podem estar untracked na arvore viva. O land exige-os
# RASTREADOS, entao o clone precisa ve-los num commit — senao todo caso
# morreria no G0 por um motivo que nao e o que estamos testando.
SRC="$WORK/src"
git clone --local --quiet --no-hardlinks "$ROOT" "$SRC" \
  || die "git clone --local falhou"
git -C "$SRC" checkout --quiet -B main "$(git -C "$ROOT" rev-parse HEAD)" \
  || die "nao consegui posicionar o clone no HEAD vivo"

MATERIAL_LIST=(
  "$SIGN_SCRIPT" "$LAND_SCRIPT"
  "$CEREMONY_DIR/PROPOSED-PATCH.md"
  "$CEREMONY_DIR/COMMIT-MSG-B.txt"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-B.sh"
  "$CEREMONY_DIR/test-ceremony-scripts-B.sh"
  "$CEREMONY_DIR/README-B.md"
  "$PATCH"
  "$SENTINEL"
)
for m in "${MATERIAL_LIST[@]}"; do
  [ -f "$ROOT/$m" ] || die "material ausente na arvore viva: $m"
  mkdir -p "$SRC/$( dirname "$m" )"
  cp -p "$ROOT/$m" "$SRC/$m"
done
for r in "$ROOT/$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$r" ] || continue
  cp -p "$r" "$SRC/$CEREMONY_DIR/$( basename "$r" )"
done

# A metade NAO-CANONICA tem de estar no commit sintetico: o G-PRE le de
# `git show HEAD:` e sem ela TODO caso abortaria NO G-PRE, pelo motivo errado —
# e o T10 (controle de nao-vacuidade) ficaria vermelho, denunciando o harness.
# Sao TRES arquivos, nao dois: o `PLAN-169-…md` carrega as OQ-7..OQ-12 que o
# G-PRE tambem exige.
NONCANON=( "$PROFILER" "$GATE_TEST" "$PLAN_MD" )
NONCANON_PRESENT=()
for m in "${NONCANON[@]}"; do
  if [ -f "$ROOT/$m" ]; then
    mkdir -p "$SRC/$( dirname "$m" )"
    cp -p "$ROOT/$m" "$SRC/$m"
    NONCANON_PRESENT+=( "$m" )
  else
    printf '  \033[33mNOTA\033[0m metade nao-canonica ausente na arvore viva: %s\n' "$m"
  fi
done

git -C "$SRC" add -- "${MATERIAL_LIST[@]}" "$CEREMONY_DIR" "${NONCANON_PRESENT[@]}" \
  >/dev/null 2>&1 || die "git add dos materiais falhou no clone"
git -C "$SRC" -c user.name=selftest -c user.email=selftest@example.invalid \
  commit -q -m "selftest: materiais da cerimonia wave-s328-B + metade nao-canonica" \
  || die "commit sintetico falhou no clone"
SYNTH_HEAD="$( git -C "$SRC" rev-parse HEAD )"
printf '  commit sintetico: %s\n' "$SYNTH_HEAD"

# O patch foi gerado contra o HEAD vivo, que agora e ANCESTRAL do commit
# sintetico. Isso e exatamente a forma que o SIGN/LAND esperam (base ancestral,
# sem drift nos paths tocados), entao nao ha nada a re-gerar.
git -C "$SRC" apply --check "$PATCH" \
  || die "o B.patch nao aplica no clone — o setup do harness esta errado"
printf '  B.patch aplica limpo no clone\n'

# ---------------------------------------------------------------------------
# Helpers: cada caso roda numa COPIA fresca do clone, para que um plant nunca
# vaze para o caso seguinte.
# ---------------------------------------------------------------------------
# A unicidade vem do `mktemp`, NAO de um contador. Um contador aqui seria
# incrementado dentro de `$( )` — subshell — e nunca chegaria ao pai: TODO caso
# reusaria `case-1`, e a partir do segundo o `cp -R` copiaria PARA DENTRO do
# diretorio existente (`case-1/src`), com "Permission denied" nos objetos git
# read-only. Foi exatamente o modo de falha medido na primeira execucao deste
# harness: 11 FAIL, todos por esse mesmo motivo.
_fresh() {
  _fr_dir="$( mktemp -d "$WORK/case.XXXXXX" )"
  # `cp -R src/. dir/` (com o `/.`) copia o CONTEUDO para um diretorio que ja
  # existe, em vez de aninhar `src` dentro dele.
  cp -R "$SRC/." "$_fr_dir/"
  printf '%s' "$_fr_dir"
}
# Os logs vao FORA da arvore do caso. Escreve-los DENTRO dela os torna
# untracked visiveis ao `git status`, e o T2 (restauracao byte a byte) acusaria
# o land por um arquivo que o proprio harness criou — medido: T2 vermelho por
# `.land.log`, nao por defeito do land.
_logdir() { printf '%s' "$WORK/logs/$( basename "$1" )"; }
# Assina o sentinel no modo AUTO-TESTE (gera .asc sintetico e preenche campos).
_sign() {
  mkdir -p "$( _logdir "$1" )"
  ( cd "$1" && CEREMONY_SELFTEST_NO_GPG=1 bash "$SIGN_SCRIPT" ) >"$( _logdir "$1" )/sign.log" 2>&1
}
_land() {
  _ld="$1"; shift
  mkdir -p "$( _logdir "$_ld" )"
  ( cd "$_ld" && CEREMONY_SELFTEST_NO_GPG=1 bash "$LAND_SCRIPT" "$@" ) >"$( _logdir "$_ld" )/land.log" 2>&1
}
# Commita um plant feito ANTES da assinatura. Sem isto o SIGN aborta no P0
# ("modificacoes RASTREADAS na arvore") e o caso mede o P0 em vez do gate que
# ele quer exercitar — medido: T4/T5 vermelhos pelo motivo errado.
# `git add -- <arquivo>`, nunca `-A`: o plant e sempre UM arquivo conhecido, e
# `-A` e um add capaz de diretorio — bloqueado pela regra R4 do ceremony-lint
# (medido: 1 blocking nao-waivado com os materiais rastreados).
_commit_plant() {
  ( cd "$1" && git add -- "$2" \
    && git -c user.name=t -c user.email=t@example.invalid commit -q -m "selftest plant" )
}
# Espera VERMELHO com uma razao NOMEADA. Um abort pelo motivo errado e
# indistinguivel de um gate morto se so olharmos o exit code.
_expect_red() {
  _er_dir="$1"; _er_why="$2"; _er_label="$3"
  if [ "$_er_rc" -eq 0 ]; then
    fail "$_er_label — o land saiu 0 com a divergencia plantada (gate MORTO)"
    return
  fi
  if grep -qF -- "$_er_why" "$( _logdir "$_er_dir" )/land.log"; then
    pass "$_er_label (rc=$_er_rc, razao nomeada)"
  else
    fail "$_er_label — vermelho, mas por OUTRO motivo (esperava '$_er_why'):"
    tail -6 "$( _logdir "$_er_dir" )/land.log" | sed 's/^/        /'
  fi
}

# ---------------------------------------------------------------------------
step "T1 — SIGN no modo auto-teste preenche e 'assina'"
# ---------------------------------------------------------------------------
D="$( _fresh )"
if _sign "$D"; then
  if grep -q '^Anchor-SHA: [0-9a-f]\{40\}$' "$D/$SENTINEL" \
     && [ -f "$D/$SENTINEL.asc" ]; then
    pass "T1: Anchor-SHA preenchido e .asc sintetico gerado"
  else
    fail "T1: o SIGN saiu 0 mas nao preencheu o Anchor-SHA / nao gerou o .asc"
  fi
else
  fail "T1: o SIGN reprovou:"; tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
fi

# ---------------------------------------------------------------------------
step "T2 — LAND --dry-run: verde E restaura arvore e index byte a byte"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || { fail "T2: SIGN falhou no setup"; }
_fp() { ( cd "$1" && { git status --porcelain=v1; printf -- '--index--\n'; git diff --cached --name-status; } | shasum -a 256 | awk '{print $1}' ); }
FP_BEFORE="$( _fp "$D" )"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
FP_AFTER="$( _fp "$D" )"
if [ "$_er_rc" -ne 0 ]; then
  fail "T2: o --dry-run reprovou (rc=$_er_rc):"; tail -10 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
elif [ "$FP_BEFORE" != "$FP_AFTER" ]; then
  fail "T2: o --dry-run NAO restaurou o estado (arvore ou index sujos)"
else
  pass "T2: --dry-run verde e estado restaurado byte a byte"
fi

# ---------------------------------------------------------------------------
step "T3 — patch adulterado depois da assinatura => G2 vermelho"
# ---------------------------------------------------------------------------
D="$( _fresh )"
_sign "$D" || fail "T3: SIGN falhou no setup"
printf '\n' >> "$D/$PATCH"          # um byte a mais: o sha256 muda
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "patch NAO bate com o sentinel assinado" "T3: G2 pega patch adulterado"

# ---------------------------------------------------------------------------
step "T4 — Scope mais largo do que o patch => G4 vermelho (GHOST)"
# ---------------------------------------------------------------------------
# Autorizacao mais larga do que a revisao e tao invalida quanto autorizacao
# faltando. O plant entra ANTES da assinatura (senao o G2 pegaria primeiro, e o
# caso mediria o G2 de novo em vez do G4).
D="$( _fresh )"
python3 - "$D/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = s.replace("  - .github/workflows/validate.yml\n",
              "  - .github/workflows/validate.yml\n  - scripts/install.sh\n", 1)
open(p, "w", encoding="utf-8").write(s)
PY
_commit_plant "$D" "$SENTINEL" || fail "T4: nao consegui commitar o plant"
_sign "$D" || fail "T4: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "o Scope autoriza path(s) que o patch NAO toca" "T4: G4 pega Scope largo"

# ---------------------------------------------------------------------------
step "T5 — Scope que NAO cobre um path tocado => G4 vermelho (EXTRA)"
# ---------------------------------------------------------------------------
D="$( _fresh )"
python3 - "$D/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = s.replace("  - .claude/adr/ADR-144-subagent-model-tiering-frontmatter.md\n", "", 1)
open(p, "w", encoding="utf-8").write(s)
PY
_commit_plant "$D" "$SENTINEL" || fail "T5: nao consegui commitar o plant"
_sign "$D" || fail "T5: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "o patch toca path(s) FORA do Scope assinado" "T5: G4 pega Scope incompleto"

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

# ---------------------------------------------------------------------------
step "T7 — chave AUSENTE na base declarada => o V-block ABORTA, nunca vira 0"
# ---------------------------------------------------------------------------
# `_expect` fail-CLOSED: um V-block que le "" e compara contra "" e verde vazio.
D="$( _fresh )"
sed -i.bak '/^EXPECTED_HELP_FLAGS=/d' "$D/$BASELINE_ENV" && rm -f "$D/$BASELINE_ENV.bak"
_sign "$D" >/dev/null 2>&1 || true    # o SIGN tambem le a chave; pode abortar
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "AUSENTE em" "T7: base declarada incompleta ABORTA"

# ---------------------------------------------------------------------------
step "T8 — metade NAO-CANONICA fora do HEAD => G-PRE vermelho"
# ---------------------------------------------------------------------------
# O achado do pair-rail rodadas 1 e 2. O plant remove as flags do profiler EM
# COMMIT (nao na arvore de trabalho): o gate le `git show HEAD:`, entao um
# plant so na arvore nao provaria nada.
D="$( _fresh )"
if [ -f "$D/$PROFILER" ]; then
  python3 - "$D/$PROFILER" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
# Plant ADVERSARIAL: renomeia com SUFIXO. Um `grep -c -- "--exec-reference"`
# de substring casaria `--exec-reference-DISABLED` e o gate ficaria VERDE com
# o profiler quebrado. O G-PRE ancora por fronteira de palavra; este caso e o
# controle POSITIVO dessa ancoragem.
s = s.replace("--exec-reference", "--exec-reference-DISABLED-BY-SELFTEST")
open(p, "w", encoding="utf-8").write(s)
PY
  ( cd "$D" && git add -- "$PROFILER" \
    && git -c user.name=t -c user.email=t@example.invalid commit -q -m "selftest: remove a flag do HEAD" ) \
    || fail "T8: nao consegui commitar o plant"
  _sign "$D" >/dev/null 2>&1 || true
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "NAO conhece a(s) flag(s)" "T8: G-PRE pega profiler sem a flag em HEAD"
else
  printf '  \033[33mSKIP\033[0m T8: %s ausente na arvore viva (a metade nao-canonica ainda nao existe)\n' "$PROFILER"
fi

# ---------------------------------------------------------------------------
step "T9 — literal de compatibilidade removido do yml => V6c vermelho"
# ---------------------------------------------------------------------------
# `proof-retry-matrix.sh` e `wave2-regression-proof.sh` casam esse texto por
# grep. O plant e no PATCH (o land aplica o patch e mede o resultado), e por
# isso ele muda o sha256 — o sentinel e re-assinado DEPOIS do plant.
D="$( _fresh )"
python3 - "$D/$PATCH" <<'PY'
import sys
p = sys.argv[1]
b = open(p, "rb").read()
# Acrescenta um hunk que apaga uma das duas ocorrencias? Mais simples e
# honesto: o V6c conta no ARQUIVO pos-patch, entao basta o patch mudar o
# arquivo. Aqui trocamos o literal na propria linha de contexto e deixamos o
# `git apply` recusar OU o V6c contar errado. Se o apply recusar, o caso ainda
# e vermelho por razao nomeada, que e o que o gate deve garantir.
b = b.replace(b"FAILED on BOTH attempts (rc1=", b"FAILED on BOTH tries (rc1=", 1)
open(p, "wb").write(b)
PY
_sign "$D" >/dev/null 2>&1 || true
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
if [ "$_er_rc" -ne 0 ]; then
  pass "T9: patch que mexe no literal de compatibilidade fica VERMELHO (rc=$_er_rc)"
else
  fail "T9: o land aceitou um patch que altera o literal de compatibilidade"
fi

# ---------------------------------------------------------------------------
step "T10 — sem plant nenhum, o --dry-run e VERDE (controle de nao-vacuidade)"
# ---------------------------------------------------------------------------
# Sem este caso, um harness em que TODOS os casos ficassem vermelhos por um
# defeito comum passaria como "10/10".
D="$( _fresh )"
_sign "$D" || fail "T10: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
if [ "$_er_rc" -eq 0 ]; then
  pass "T10: controle — sem divergencia o --dry-run sai 0"
else
  fail "T10: o --dry-run reprovou SEM plant (os outros casos podem ser verdes vazios):"
  tail -12 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
fi

# ---------------------------------------------------------------------------
step "RESUMO"
# ---------------------------------------------------------------------------
printf '\n  PASS=%d  FAIL=%d\n\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
