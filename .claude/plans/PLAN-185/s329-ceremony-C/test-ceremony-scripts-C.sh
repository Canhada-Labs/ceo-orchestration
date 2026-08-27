#!/usr/bin/env bash
# test-ceremony-scripts-C.sh — harness do pacote de cerimonia wave-s329-C.
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
# no macOS, e comparar string mediria formato, nao caminho). Nenhuma chave GPG
# real e usada nem gerada: o modo auto-teste substitui a assinatura por um
# `.asc` sintetico e o LAND pula a verificacao GPG (e SO ela).
#
# POR QUE UM CLONE, E NAO A ARVORE VIVA. Os gates deste pacote sao de CORPUS
# (materiais rastreados, `git ls-files`, oraculo de canonicidade). Rodados
# antes do commit dos materiais eles medem uma arvore que nao e a que sera
# landada — a licao "bateria rodada ANTES da ultima edicao nao e bateria", e a
# licao T-S329-2: um harness que so passa porque o pack em HEAD esta velho nao
# e um harness. Por isso a PRE-CONDICAO abaixo e fail-CLOSED.
#
# OS DOIS GATES CAROS NAO RODAM AQUI por padrao (~20 min somados). O LAND os
# pula SO sob `CEO_C_HARNESS_SKIP_SLOW=1` E o modo auto-teste (dois guardas); o
# T15 prova que o interruptor e RECUSADO fora do auto-teste, e o T17 (opt-in)
# prova que o V5 de fato roda e compara. Ver o RESUMO no fim.
#
# Uso:
#   bash .claude/plans/PLAN-185/s329-ceremony-C/test-ceremony-scripts-C.sh
#   CEO_C_HARNESS_UNCOMMITTED=1 bash .../test-ceremony-scripts-C.sh   # pre-commit
#   CEO_C_HARNESS_WITH_SLOW=1   bash .../test-ceremony-scripts-C.sh   # + T17 (~7 min)
#   CEO_C_HARNESS_WITH_FINALIZE=1 bash .../test-ceremony-scripts-C.sh # + T19
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"

# --- constantes do pacote --------------------------------------------------
PLAN_DIR=".claude/plans/PLAN-185"
CEREMONY_DIR="$PLAN_DIR/s329-ceremony-C"
SENTINEL="$PLAN_DIR/wave-s329-C-approved.md"
PATCH="$CEREMONY_DIR/C.patch"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S329-C-SIGN.sh"
LAND_SCRIPT="$PLAN_DIR/OWNER-S329-C-LAND.sh"
FINALIZE_SCRIPT="$CEREMONY_DIR/finalize-C.sh"
THREAT_MODEL="docs/threat-model.md"
# Um path REQUIRED cuja remocao do patch o G4 tem de acusar. Escolhido por ser
# o alvo canonico central da wave.
SCOPE_PLANT_PATH="scripts/install.sh"
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
# O scratchpad tem de ser o DESTE repositorio. `ls */*/scratchpad | head -1`
# pegava o de OUTRO projeto (medido na S328) e todo caso morria em "Permission
# denied". O slug e o mesmo que o harness usa: caminho absoluto com `/` -> `-`.
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
WORK="$( mktemp -d "$SESSION_DIR/ceremony-selftest-s329C.XXXXXX" )"
trap 'rm -rf "$WORK"' EXIT
printf '  area de teste: %s\n' "$WORK"

# ---------------------------------------------------------------------------
step "PRE — T-S329-2: os materiais estao COMMITADOS na arvore viva?"
# ---------------------------------------------------------------------------
# Um harness que passa sobre um pack UNTRACKED responde uma pergunta que nao e
# a do land. Fail-CLOSED por padrao; o override e explicito e LOGADO.
MATERIAL_LIST=(
  "$SIGN_SCRIPT" "$LAND_SCRIPT"
  "$CEREMONY_DIR/PROPOSED-PATCH.md"
  "$CEREMONY_DIR/COMMIT-MSG-C.txt"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$FINALIZE_SCRIPT"
  "$CEREMONY_DIR/test-ceremony-scripts-C.sh"
  "$CEREMONY_DIR/README-C.md"
  "$PATCH"
  "$SENTINEL"
)
UNCOMMITTED=""
for m in "${MATERIAL_LIST[@]}"; do
  [ -f "$ROOT/$m" ] || die "material AUSENTE na arvore viva: $m
  Rode primeiro:  bash $ROOT/$FINALIZE_SCRIPT"
  git -C "$ROOT" ls-files --error-unmatch -- "$m" >/dev/null 2>&1 \
    || UNCOMMITTED="$UNCOMMITTED  $m
"
done
if [ -n "$UNCOMMITTED" ]; then
  if [ "${CEO_C_HARNESS_UNCOMMITTED:-}" = "1" ]; then
    printf '\033[33m  CEO_C_HARNESS_UNCOMMITTED=1\033[0m — material(is) ainda NAO commitado(s):\n'
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
    printf '    CEO_C_HARNESS_UNCOMMITTED=1 bash %s\n' "$ROOT/$CEREMONY_DIR/test-ceremony-scripts-C.sh" >&2
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
RAIL_COPIED=0
for r in "$ROOT/$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$r" ] || continue
  cp -p "$r" "$SRC/$CEREMONY_DIR/$( basename "$r" )"
  RAIL_COPIED=$(( RAIL_COPIED + 1 ))
done
[ "$RAIL_COPIED" -gt 0 ] || die "nenhum rail-round-*.md na arvore viva — o SIGN abortaria em TODO caso"

git -C "$SRC" add -- "${MATERIAL_LIST[@]}" "$CEREMONY_DIR" \
  >/dev/null 2>&1 || die "git add dos materiais falhou no clone"
# T-S329-2 / classe d9d9cab: materiais ja commitados em HEAD => index vazio,
# e um commit incondicional aborta com "nothing to commit" — vermelho pelo
# motivo errado. Index vazio => segue sem commit.
if git -C "$SRC" diff --cached --quiet; then
  printf '  materiais ja commitados em HEAD — commit sintetico dispensado\n'
else
  git -C "$SRC" -c user.name=selftest -c user.email=selftest@example.invalid \
    commit -q -m "selftest: materiais da cerimonia wave-s329-C" \
    || die "commit sintetico falhou no clone"
fi
SYNTH_HEAD="$( git -C "$SRC" rev-parse HEAD )"
printf '  commit sintetico: %s (%d registro(s) de rail)\n' "$SYNTH_HEAD" "$RAIL_COPIED"

# O patch foi gerado contra o HEAD vivo, que agora e ANCESTRAL do commit
# sintetico. Isso e exatamente a forma que o SIGN/LAND esperam (base ancestral,
# sem drift nos paths tocados), entao nao ha nada a re-gerar.
git -C "$SRC" apply --check "$PATCH" \
  || die "o C.patch nao aplica no clone — o setup do harness esta errado"
printf '  C.patch aplica limpo no clone\n'

# O ultimo registro de rail precisa ser APPROVE para os casos que exigem o SIGN
# VERDE. Se ainda for REJECT, esses casos seriam vermelhos pelo motivo certo mas
# na hora errada — melhor dizer isso na cara.
_last_rail=""; _last_n=-1
for r in "$SRC/$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$r" ] || continue
  _b="$( basename "$r" )"; _n="${_b#rail-round-}"; _n="${_n%.md}"
  case "$_n" in ''|*[!0-9]*) continue ;; esac
  if [ "$_n" -gt "$_last_n" ]; then _last_n="$_n"; _last_rail="$r"; fi
done
RAIL_LAST_VERDICT="$( grep -m1 '^Rail-Verdict:' "$_last_rail" 2>/dev/null | sed 's/^[^:]*: *//' | tr -d '[:space:]' || printf '' )"
printf '  ultimo rail: %s (Rail-Verdict: %s)\n' "$( basename "$_last_rail" )" "${RAIL_LAST_VERDICT:-<ausente>}"
RAIL_IS_APPROVE=0
RAIL_SYNTHETIC=0
[ "$RAIL_LAST_VERDICT" = "APPROVE" ] && RAIL_IS_APPROVE=1
if [ "$RAIL_IS_APPROVE" = "0" ]; then
  # O harness testa os SCRIPTS; ele nao pode ficar refem de uma rodada de rail
  # que ainda nao aconteceu. Planta um APPROVE sintetico NO CLONE para destravar
  # os casos seguintes — e o T10 continua provando que a recusa e real, plantando
  # um REJECT de numero MAIOR. O plant vive so no clone descartavel: a arvore
  # viva nao e tocada, e o SIGN do Owner continua exigindo um APPROVE de verdade.
  RAIL_SYNTHETIC=$(( _last_n + 1 ))
  cat > "$SRC/$CEREMONY_DIR/rail-round-$RAIL_SYNTHETIC.md" <<EOF
# HARNESS ARTIFACT — NAO E UM REGISTRO DE RAIL REAL

Rail-Verdict: APPROVE

Este arquivo existe SO dentro do clone descartavel do
test-ceremony-scripts-C.sh, para destravar os casos que exigem um SIGN verde
enquanto a rodada de rail de verdade nao foi escrita. Ele nunca e commitado na
arvore viva. Se voce esta lendo isto fora de /private/tmp, algo deu errado.
EOF
  git -C "$SRC" add -- "$CEREMONY_DIR/rail-round-$RAIL_SYNTHETIC.md" >/dev/null 2>&1
  git -C "$SRC" -c user.name=selftest -c user.email=selftest@example.invalid \
    commit -q -m "selftest: rail APPROVE sintetico (so no clone)" \
    || die "nao consegui commitar o rail sintetico no clone"
  SYNTH_HEAD="$( git -C "$SRC" rev-parse HEAD )"
  RAIL_IS_APPROVE=1
  printf '  \033[33mNOTA\033[0m o ultimo rail da arvore VIVA e "%s", nao APPROVE.\n' "${RAIL_LAST_VERDICT:-<ausente>}"
  printf '        Plantei rail-round-%s.md com APPROVE NO CLONE para destravar os\n' "$RAIL_SYNTHETIC"
  printf '        casos seguintes. Isto NAO substitui a rodada real: o SIGN do\n'
  printf '        Owner continua recusando enquanto o rail de verdade nao fechar,\n'
  printf '        e o T10 prova essa recusa.\n'
fi

# ---------------------------------------------------------------------------
# Helpers: cada caso roda numa COPIA fresca do clone, para que um plant nunca
# vaze para o caso seguinte.
# ---------------------------------------------------------------------------
# A unicidade vem do `mktemp`, NAO de um contador. Um contador aqui seria
# incrementado dentro de `$( )` — subshell — e nunca chegaria ao pai: TODO caso
# reusaria `case-1`, e a partir do segundo o `cp -R` copiaria PARA DENTRO do
# diretorio existente, com "Permission denied" nos objetos git read-only.
_fresh() {
  _fr_dir="$( mktemp -d "$WORK/case.XXXXXX" )"
  # `cp -R src/. dir/` (com o `/.`) copia o CONTEUDO para um diretorio que ja
  # existe, em vez de aninhar `src` dentro dele.
  cp -R "$SRC/." "$_fr_dir/"
  printf '%s' "$_fr_dir"
}
# O disco desta maquina fica em 99% de uso; cada copia do clone e ~180 MB.
# Liberar por caso, em vez de so no trap, mantem o pico em uma copia.
_done() { [ -n "${1:-}" ] && rm -rf "$1" 2>/dev/null || printf ''; }
# Os logs vao FORA da arvore do caso. Escreve-los DENTRO dela os torna
# untracked visiveis ao `git status`, e o T2 (restauracao byte a byte) acusaria
# o land por um arquivo que o proprio harness criou.
_logdir() { printf '%s' "$WORK/logs/$( basename "$1" )"; }
_sign() {
  mkdir -p "$( _logdir "$1" )"
  ( cd "$1" && CEREMONY_SELFTEST_NO_GPG=1 bash "$SIGN_SCRIPT" ) >"$( _logdir "$1" )/sign.log" 2>&1
}
_land() {
  _ld="$1"; shift
  mkdir -p "$( _logdir "$_ld" )"
  ( cd "$_ld" && CEREMONY_SELFTEST_NO_GPG=1 CEO_C_HARNESS_SKIP_SLOW="${_SKIP_SLOW:-1}" \
      bash "$LAND_SCRIPT" "$@" ) >"$( _logdir "$_ld" )/land.log" 2>&1
}
# Commita um plant feito ANTES da assinatura. Sem isto o SIGN aborta no P0-c
# ("modificacoes RASTREADAS na arvore") e o caso mede o P0-c em vez do gate que
# ele quer exercitar. `git add -- <arquivo>`, nunca `-A`: o plant e sempre UM
# arquivo conhecido, e `-A` e um add capaz de diretorio — bloqueado pela regra
# R4 do ceremony-lint.
_commit_plant() {
  # T-S329-2 / classe d9d9cab: plant que coincide com o HEAD deixa o index
  # vazio; commit incondicional abortaria "nothing to commit" — vermelho pelo
  # motivo errado. Index vazio => plant ja vigente, seguir sem commit.
  ( cd "$1" && git add -- "$2" \
    && { git diff --cached --quiet \
         || git -c user.name=t -c user.email=t@example.invalid commit -q -m "selftest plant"; } )
}
# Espera VERMELHO com uma razao NOMEADA. Um abort pelo motivo errado e
# indistinguivel de um gate morto se so olharmos o exit code.
_expect_red() {
  _er_dir="$1"; _er_why="$2"; _er_label="$3"; _er_log="${4:-land.log}"
  if [ "$_er_rc" -eq 0 ]; then
    fail "$_er_label — o script saiu 0 com a divergencia plantada (gate MORTO)"
    return
  fi
  # Diagnostico de SETUP, antes do de conteudo. Um caso cujo SIGN nao produziu
  # o `.asc` para no G0 do LAND em "assinatura ausente" — vermelho, mas por um
  # defeito do CENARIO, nao do gate. Sem esta linha o relatorio diz apenas
  # "vermelho por OUTRO motivo" e manda o leitor caçar a causa no log. Foi
  # exatamente essa a confusao do T7 na primeira execucao deste harness.
  if [ "$_er_log" = "land.log" ] \
     && grep -qF 'assinatura ausente' "$( _logdir "$_er_dir" )/$_er_log"; then
    fail "$_er_label — SETUP QUEBRADO: o SIGN nao produziu o .asc, entao o LAND
        parou no G0 sem chegar ao gate sob teste. Ultimas linhas do SIGN:"
    tail -8 "$( _logdir "$_er_dir" )/sign.log" 2>/dev/null | sed 's/^/        /'
    return
  fi
  if grep -qF -- "$_er_why" "$( _logdir "$_er_dir" )/$_er_log"; then
    pass "$_er_label (rc=$_er_rc, razao nomeada)"
  else
    fail "$_er_label — vermelho, mas por OUTRO motivo (esperava '$_er_why'):"
    tail -8 "$( _logdir "$_er_dir" )/$_er_log" | sed 's/^/        /'
  fi
}
# Troca o VALOR de uma chave do EXPECTED-BASELINE.txt no clone do caso.
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
step "T1 — SIGN no modo auto-teste preenche e 'assina'"
# ---------------------------------------------------------------------------
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  if _sign "$D"; then
    if grep -q '^Anchor-SHA: [0-9a-f]\{40\}$' "$D/$SENTINEL" && [ -f "$D/$SENTINEL.asc" ]; then
      pass "T1: Anchor-SHA preenchido e .asc sintetico gerado"
    else
      fail "T1: o SIGN saiu 0 mas nao preencheu o Anchor-SHA / nao gerou o .asc"
    fi
  else
    fail "T1: o SIGN reprovou:"; tail -10 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
  fi
  _done "$D"
else
  skip "T1: o ultimo rail nao e APPROVE (o SIGN recusa por desenho — ver T10)"
fi

# ---------------------------------------------------------------------------
step "T2 — LAND --dry-run: verde E restaura arvore e index byte a byte"
# ---------------------------------------------------------------------------
if [ "$RAIL_IS_APPROVE" = "1" ]; then
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
else
  skip "T2: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T3 — patch adulterado depois da assinatura => G2 vermelho"
# ---------------------------------------------------------------------------
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _sign "$D" || fail "T3: SIGN falhou no setup"
  printf '\n' >> "$D/$PATCH"          # um byte a mais: o sha256 muda
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "patch NAO bate com o sentinel assinado" "T3: G2 pega patch adulterado"
  _done "$D"
else
  skip "T3: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T4 — Scope mais largo do que o patch => G4 vermelho (GHOST)"
# ---------------------------------------------------------------------------
# Autorizacao mais larga do que a revisao e tao invalida quanto autorizacao
# faltando. O plant entra ANTES da assinatura (senao o G2 pegaria primeiro).
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  python3 - "$D/$SENTINEL" "$SCOPE_PLANT_PATH" <<'PY'
import sys
p, anchor = sys.argv[1:3]
s = open(p, encoding="utf-8").read()
line = "  - %s\n" % anchor
if line not in s:
    sys.exit("ancora de Scope nao encontrada: %r" % anchor)
s = s.replace(line, line + "  - scripts/uninstall.sh\n", 1)
open(p, "w", encoding="utf-8").write(s)
PY
  _commit_plant "$D" "$SENTINEL" || fail "T4: nao consegui commitar o plant"
  _sign "$D" || fail "T4: SIGN falhou no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "o Scope autoriza path(s) que o patch NAO toca" "T4: G4 pega Scope largo"
  _done "$D"
else
  skip "T4: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T5 — Scope que NAO cobre um path tocado => G4 vermelho (EXTRA)"
# ---------------------------------------------------------------------------
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  python3 - "$D/$SENTINEL" "$SCOPE_PLANT_PATH" <<'PY'
import sys
p, anchor = sys.argv[1:3]
s = open(p, encoding="utf-8").read()
line = "  - %s\n" % anchor
if line not in s:
    sys.exit("ancora de Scope nao encontrada: %r" % anchor)
open(p, "w", encoding="utf-8").write(s.replace(line, "", 1))
PY
  _commit_plant "$D" "$SENTINEL" || fail "T5: nao consegui commitar o plant"
  _sign "$D" || fail "T5: SIGN falhou no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "o patch toca path(s) FORA do Scope assinado" "T5: G4 pega Scope incompleto"
  _done "$D"
else
  skip "T5: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T6 — commit depois de assinar => G1 vermelho (ancora velha)"
# ---------------------------------------------------------------------------
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _sign "$D" || fail "T6: SIGN falhou no setup"
  ( cd "$D" && printf 'ruido\n' > .selftest-noise \
    && git add .selftest-noise \
    && git -c user.name=t -c user.email=t@example.invalid commit -q -m "move o HEAD" ) \
    || fail "T6: nao consegui mover o HEAD no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "Anchor-SHA nao bate com HEAD" "T6: G1 pega ancora invalidada"
  _done "$D"
else
  skip "T6: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T7 — chave AUSENTE na base declarada => o V-block ABORTA, nunca vira 0"
# ---------------------------------------------------------------------------
# `_expect` fail-CLOSED: um V-block que le "" e compara contra "" e verde vazio.
# A chave escolhida e lida SO pelo LAND (o SIGN nao a le), entao o caso mede o
# V-block e nao o SIGN.
#
# O plant TEM de ser commitado, como em todo caso deste harness. Sem isso o
# P0-c do SIGN aborta por "modificacao RASTREADA", nenhum `.asc` e produzido, e
# o LAND para no G0 em "assinatura ausente" — vermelho pelo motivo ERRADO, com
# o gate sob teste nunca alcancado. Foi assim que este caso nasceu (medido: 17
# PASS / 1 FAIL na primeira execucao do harness), e e a mesma forma que o
# `_expect_red` existe para pegar.
D="$( _fresh )"
sed -i.bak '/^EXPECTED_SHELL_FILES_IN_PATCH=/d' "$D/$BASELINE_ENV" && rm -f "$D/$BASELINE_ENV.bak"
_commit_plant "$D" "$BASELINE_ENV" || fail "T7: nao consegui commitar o plant"
_sign "$D" || fail "T7: SIGN falhou no setup"
_er_rc=0; _land "$D" --dry-run || _er_rc=$?
_expect_red "$D" "AUSENTE em" "T7: base declarada incompleta ABORTA"
_done "$D"

# ---------------------------------------------------------------------------
step "T8 — threat-model: a troca de status EXATA e revertida, e o SIGN segue"
# ---------------------------------------------------------------------------
# `check-threat-model-freshness.py` reescreve `**Status:** accepted` ->
# `stale` como efeito colateral de rodar, e o P0-c abortaria acusando um
# arquivo que ninguem tocou. Este caso planta EXATAMENTE essa troca.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
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
      tail -10 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
    fi
  else
    skip "T8: $THREAT_MODEL nao esta em '**Status:** accepted' neste checkout"
  fi
  _done "$D"
else
  skip "T8: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T9 — threat-model: uma edicao DIFERENTE NAO e revertida, e o SIGN aborta"
# ---------------------------------------------------------------------------
# A cura tem de ser cirurgica. Reverter por adivinhacao destruiria trabalho de
# outra pessoa — e a direcao importa: `stale` -> `accepted` e alguem RE-ACEITANDO
# o modelo de ameacas de proposito.
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
    tail -10 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
  fi
else
  skip "T9: $THREAT_MODEL ausente neste checkout"
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T10 — ultimo rail sem APPROVE => o SIGN recusa"
# ---------------------------------------------------------------------------
# Contar rodadas nao e ler o veredito. Este caso planta um registro de numero
# MAIOR com REJECT: se o SIGN ordenasse por nome, `rail-round-9` viria depois de
# `rail-round-10` e ele leria o veredito ERRADO.
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
  tail -10 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T11 — V2c: contagem ERRADA de referencias ao e2e no workflow => vermelho"
# ---------------------------------------------------------------------------
# `unwired = no test`. Este caso prova que o V2c COMPARA, em vez de so contar.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _set_expect "$D" EXPECTED_YML_E2E_REFS 7
  _commit_plant "$D" "$BASELINE_ENV" || fail "T11: nao consegui commitar o plant"
  _sign "$D" || fail "T11: SIGN falhou no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "esperado 7" "T11: V2c pega contagem de wiring errada"
  _done "$D"
else
  skip "T11: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T12 — V3: o invariante do predicado compartilhado e VIVO"
# ---------------------------------------------------------------------------
# Se um segundo corpo do predicado voltar para dentro de install.sh ou
# upgrade.sh, a classe das copias divergentes renasceu. O plant e no NUMERO
# ESPERADO de definicoes: o gate mede o arquivo pos-patch e tem de acusar a
# divergencia — o que prova que ele esta de fato lendo os arquivos.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _set_expect "$D" EXPECTED_PREDICATE_DEFINITIONS_TOTAL 2
  _commit_plant "$D" "$BASELINE_ENV" || fail "T12: nao consegui commitar o plant"
  _sign "$D" || fail "T12: SIGN falhou no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "definido 1 vez(es), esperado 2" "T12: V3 conta as definicoes do predicado"
  _done "$D"
else
  skip "T12: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T13 — V4: o censo e REALMENTE executado e comparado"
# ---------------------------------------------------------------------------
# O ratchet REGENERADO esta sempre limpo, entao a checagem "rc 0 / 0 nova /
# 0 morta" sozinha seria quase tautologica. O que a torna nao-vacua sao as
# contagens EXATAS que o finalize mediu e a assinatura congelou. Este caso
# planta uma delas: se o V4 nao estivesse REALMENTE rodando o instrumento e
# lendo a contagem, o plant passaria despercebido.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _set_expect "$D" EXPECTED_CENSUS_DESGUARDADO_POS 999999
  _commit_plant "$D" "$BASELINE_ENV" || fail "T13: nao consegui commitar o plant"
  _sign "$D" || fail "T13: SIGN falhou no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "o finalize mediu 999999" "T13: V4 roda o censo e compara com o medido"
  _done "$D"
else
  skip "T13: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T14 — G4: um path OBRIGATORIO ausente do patch => vermelho"
# ---------------------------------------------------------------------------
# O bloco AUTO do EXPECTED-BASELINE.txt e DERIVADO do patch, entao sozinho ele
# nao pode acusar um pacote incompleto: um finalize rodado com a metade de
# CI/docs faltando produziria um conjunto AUTO menor, coerente consigo mesmo.
# Quem carrega o julgamento humano e REQUIRED_PATCH_PATHS. Este caso acrescenta
# um path obrigatorio que o patch nao toca e exige que o G4 o nomeie.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  python3 - "$D/$BASELINE_ENV" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
m = re.search(r'^REQUIRED_PATCH_PATHS="([^"]*)"$', s, flags=re.M)
if not m:
    sys.exit("REQUIRED_PATCH_PATHS nao encontrado")
new = 'REQUIRED_PATCH_PATHS="%s scripts/nao-existe-selftest.sh"' % m.group(1)
open(p, "w", encoding="utf-8").write(s[:m.start()] + new + s[m.end():])
PY
  _commit_plant "$D" "$BASELINE_ENV" || fail "T14: nao consegui commitar o plant"
  _sign "$D" || fail "T14: SIGN falhou no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "OBRIGATORIO(s) ausentes do patch" "T14: G4 exige os paths obrigatorios"
  _done "$D"
else
  skip "T14: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T15 — o pulo dos gates caros e RECUSADO fora do modo auto-teste"
# ---------------------------------------------------------------------------
# O V5 e o V6 sao os unicos gates que provam a cura de ponta a ponta. O
# interruptor que o harness usa nao pode existir num land real — nem por um
# `export` esquecido no perfil do Owner.
D="$( _fresh )"
mkdir -p "$( _logdir "$D" )"
_er_rc=0
( cd "$D" && CEO_C_HARNESS_SKIP_SLOW=1 bash "$LAND_SCRIPT" --dry-run ) \
  >"$( _logdir "$D" )/land.log" 2>&1 || _er_rc=$?
_expect_red "$D" "RECUSADO fora do modo auto-teste" "T15: CEO_C_HARNESS_SKIP_SLOW so vale sob auto-teste"
_done "$D"

# ---------------------------------------------------------------------------
step "T16a — mensagem de commit com o trailer por preencher => vermelho"
# ---------------------------------------------------------------------------
# O `COMMIT-MSG-C.txt` sai desta cerimonia com
# `Pair-Rail-Reviewed: TO-FILL-AFTER-LAST-RAIL-ROUND` de proposito: o CEO so
# sabe QUANTAS rodadas houve depois da ultima. Um land que aceitasse isso
# gravaria no historico um commit que mente sobre a propria revisao.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  if grep -qF 'Pair-Rail-Reviewed: TO-FILL' "$D/$CEREMONY_DIR/COMMIT-MSG-C.txt"; then
    _sign "$D" || fail "T16a: SIGN falhou no setup"
    _er_rc=0; _land "$D" || _er_rc=$?
    _expect_red "$D" "trailer Pair-Rail-Reviewed por preencher" \
                "T16a: o land recusa a mensagem com o trailer por preencher"
  else
    skip "T16a: o trailer ja esta preenchido (o CEO fechou o rail)"
  fi
  _done "$D"
else
  skip "T16a: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T16b — com o trailer preenchido, o LAND COMPLETO e VERDE (nao-vacuidade)"
# ---------------------------------------------------------------------------
# Sem este caso, um harness em que TODOS os casos ficassem vermelhos por um
# defeito comum passaria como "N/N". Aqui o land vai ate o commit (o push e
# pulado no auto-teste) e o `.asc` tem de estar DENTRO do commit.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  python3 - "$D/$CEREMONY_DIR/COMMIT-MSG-C.txt" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = re.sub(r"^Pair-Rail-Reviewed: TO-FILL.*$",
           "Pair-Rail-Reviewed: selftest (trailer preenchido pelo harness)",
           s, count=1, flags=re.M)
open(p, "w", encoding="utf-8").write(s)
PY
  _commit_plant "$D" "$CEREMONY_DIR/COMMIT-MSG-C.txt" || fail "T16b: nao consegui commitar o plant"
  _sign "$D" || fail "T16b: SIGN falhou no setup"
  _er_rc=0; _land "$D" || _er_rc=$?
  if [ "$_er_rc" -ne 0 ]; then
    fail "T16b: o land COMPLETO reprovou SEM divergencia (os outros casos podem ser verdes vazios):"
    tail -24 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
  elif ! ( cd "$D" && git show --stat --name-only --format='' HEAD | grep -qF "$( basename "$SENTINEL" ).asc" ); then
    fail "T16b: o land saiu 0 mas o commit NAO carrega a assinatura .asc"
  else
    pass "T16b: controle — sem divergencia o land completo commita, com o .asc dentro"
  fi
  _done "$D"
else
  skip "T16b: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T17 — V5: o e2e REAL e executado e comparado (opt-in, ~7 min)"
# ---------------------------------------------------------------------------
# Este e o unico caso que prova o gate CARO. Ele nao roda por padrao: 7 min por
# execucao, e o harness inteiro cabe em poucos minutos sem ele. O que roda por
# padrao no lugar dele e o T15 (o interruptor nao abre fora do auto-teste).
if [ "${CEO_C_HARNESS_WITH_SLOW:-}" = "1" ]; then
  if [ "$RAIL_IS_APPROVE" = "1" ]; then
    D="$( _fresh )"
    _set_expect "$D" EXPECTED_E2E_PASSED 9999
    _commit_plant "$D" "$BASELINE_ENV" || fail "T17: nao consegui commitar o plant"
    _sign "$D" || fail "T17: SIGN falhou no setup"
    printf '  rodando o e2e de verdade (~7 min)...\n'
    _SKIP_SLOW=0
    _er_rc=0; _land "$D" || _er_rc=$?
    _SKIP_SLOW=1
    _expect_red "$D" "esperado 9999" "T17: V5 roda o e2e e compara com o declarado"
    _done "$D"
  else
    skip "T17: depende de um SIGN verde"
  fi
else
  skip "T17: e2e real NAO executado (padrao). Para rodar:  CEO_C_HARNESS_WITH_SLOW=1 bash $0"
fi

# ---------------------------------------------------------------------------
step "T18 — o pin do instrumento do censo e VIVO (SIGN aborta)"
# ---------------------------------------------------------------------------
# Contagens de instrumentos diferentes nao sao comparaveis: o DESIGN-C secao 7
# mede com uma copia congelada e publica numeros que o instrumento de HEAD nao
# reproduz. O pin existe para que o gate ABORTE em vez de comparar reguas
# diferentes, e ele tem de abortar cedo — antes de o Owner gastar a senha.
D="$( _fresh )"
_set_expect "$D" EXPECTED_CENSUS_INSTRUMENT_SHA256 \
  "0000000000000000000000000000000000000000000000000000000000000000"
_commit_plant "$D" "$BASELINE_ENV" || fail "T18: nao consegui commitar o plant"
_er_rc=0; _sign "$D" || _er_rc=$?
_expect_red "$D" "instrumento do censo MUDOU" "T18: o SIGN aborta quando o pin nao casa" "sign.log"
_done "$D"

# ---------------------------------------------------------------------------
step "T19 — finalize-C.sh e IDEMPOTENTE (opt-in)"
# ---------------------------------------------------------------------------
# O Owner roda o finalize antes de assinar; o CEO o roda de novo depois que os
# autores terminam. Duas execucoes sobre a MESMA sombra tem de render o MESMO
# patch — senao o sha256 do sentinel muda entre a leitura e a assinatura.
#
# O caso e opt-in porque ele LE a arvore-sombra viva, que os outros autores
# podem estar editando: uma diferenca entre as duas execucoes pode ser trabalho
# novo deles, nao um defeito do script. Roda-lo quando a sombra esta parada e o
# unico resultado que discrimina.
if [ "${CEO_C_HARNESS_WITH_FINALIZE:-}" = "1" ]; then
  _sh="${CEO_C_SHADOW:-}"
  if [ -z "$_sh" ]; then
    for _cand in "$SP_BASE/$REPO_SLUG"/*/scratchpad/shadow-185; do
      [ -d "$_cand/.git" ] || continue
      _sh="$_cand"; break
    done
  fi
  if [ -z "$_sh" ] || [ ! -d "$_sh/.git" ]; then
    skip "T19: arvore-sombra nao encontrada (passe CEO_C_SHADOW=<caminho>)"
  else
    D="$( _fresh )"
    mkdir -p "$( _logdir "$D" )"
    _f1=0
    ( cd "$D" && CEO_C_SHADOW="$_sh" bash "$FINALIZE_SCRIPT" --no-commit ) \
      >"$( _logdir "$D" )/finalize-1.log" 2>&1 || _f1=$?
    if [ "$_f1" -ne 0 ] \
       && grep -qF 'RATCHET do censo esta sujo' "$( _logdir "$D" )/finalize-1.log"; then
      # Enquanto a baseline do censo nao for regenerada na sombra, o passo 4f
      # aborta ANTES de gerar o patch — e ai nao ha patch para comparar. Isso e
      # o gate funcionando, nao um defeito de determinismo: reportar FAIL aqui
      # acusaria o finalize de algo que ele nao fez.
      skip "T19: o finalize aborta no ratchet do censo (esperado enquanto a baseline nao entrar no patch) — nada a comparar"
    elif [ "$_f1" -ne 0 ]; then
      fail "T19: a primeira execucao do finalize reprovou (rc=$_f1):"
      tail -14 "$( _logdir "$D" )/finalize-1.log" | sed 's/^/        /'
    else
      _sha1="$( shasum -a 256 "$D/$PATCH" | awk '{print $1}' )"
      _f2=0
      ( cd "$D" && CEO_C_SHADOW="$_sh" bash "$FINALIZE_SCRIPT" --no-commit ) \
        >"$( _logdir "$D" )/finalize-2.log" 2>&1 || _f2=$?
      _sha2="$( shasum -a 256 "$D/$PATCH" | awk '{print $1}' )"
      if [ "$_f2" -ne 0 ]; then
        fail "T19: a SEGUNDA execucao do finalize reprovou (rc=$_f2):"
        tail -14 "$( _logdir "$D" )/finalize-2.log" | sed 's/^/        /'
      elif [ "$_sha1" != "$_sha2" ]; then
        fail "T19: o patch MUDOU entre duas execucoes ($_sha1 -> $_sha2).
        Ou o finalize nao e determinista, ou a sombra foi editada no meio."
      else
        pass "T19: duas execucoes do finalize renderam o mesmo patch ($_sha1)"
      fi
    fi
    _done "$D"
  fi
else
  skip "T19: finalize NAO exercitado (padrao). Para rodar:  CEO_C_HARNESS_WITH_FINALIZE=1 bash $0"
fi

# ---------------------------------------------------------------------------
step "RESUMO"
# ---------------------------------------------------------------------------
printf '\n  PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
printf '\n  O que NAO e coberto por padrao, e por que:\n'
printf '    - T17 (o e2e real, ~7 min) e opt-in, e o V6 (smoke-install) nao tem\n'
printf '      caso proprio: os dois sao pulados juntos pelo MESMO interruptor, e o\n'
printf '      T15 prova que ele nao abre fora do auto-teste. O land REAL roda os dois.\n'
printf '    - T19 (idempotencia do finalize) e opt-in porque le a sombra VIVA.\n'
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
