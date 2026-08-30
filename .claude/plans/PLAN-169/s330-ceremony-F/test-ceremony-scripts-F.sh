#!/usr/bin/env bash
# test-ceremony-scripts-F.sh — harness do pacote de cerimonia wave-s330-F.
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
# NAO HA GATE CARO NESTA WAVE, e por isso nao ha caso opt-in nem interruptor de
# pulo. O pacote E tinha os dois (o V3 dele custava ~9 min de instalacao real);
# aqui o V-block inteiro roda em menos de um minuto, entao TODOS os casos rodam
# por padrao. Um interruptor de pulo sem gate caro para pular seria superficie
# de ataque sem contrapartida. O que este harness NAO cobre continua sendo o
# CI (`Validate`, `Smoke Install`), que so roda depois do push — ver o RESUMO.
#
# Uso:
#   bash .claude/plans/PLAN-169/s330-ceremony-F/test-ceremony-scripts-F.sh
#   CEO_F_HARNESS_UNCOMMITTED=1 bash .../test-ceremony-scripts-F.sh   # pre-commit
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"

# --- constantes do pacote --------------------------------------------------
PLAN_DIR=".claude/plans/PLAN-169"
CEREMONY_DIR="$PLAN_DIR/s330-ceremony-F"
SENTINEL="$PLAN_DIR/wave-s330-F-approved.md"
PATCH="$CEREMONY_DIR/F.patch"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S331-F-SIGN.sh"
LAND_SCRIPT="$PLAN_DIR/OWNER-S331-F-LAND.sh"
THREAT_MODEL="docs/threat-model.md"
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
WORK="$( mktemp -d "$SESSION_DIR/ceremony-selftest-s330F.XXXXXX" )"
# Logs sao preservados quando ha FAIL (licao S329: LANDs preservam os logs
# caros no abort — sem eles a triagem de um FAIL exige re-rodar tudo).
trap '[ "${FAIL:-0}" -gt 0 ] && { printf "\n  logs preservados em %s/logs\n" "$WORK"; find "$WORK" -mindepth 1 -maxdepth 1 ! -name logs -exec rm -rf {} +; } || rm -rf "$WORK"' EXIT
printf '  area de teste: %s\n' "$WORK"

# ---------------------------------------------------------------------------
step "PRE — T-S329-2: os materiais estao COMMITADOS na arvore viva?"
# ---------------------------------------------------------------------------
# Um harness que passa sobre um pack UNTRACKED responde uma pergunta que nao e
# a do land. Fail-CLOSED por padrao; o override e explicito e LOGADO.
MATERIAL_LIST=(
  "$SIGN_SCRIPT" "$LAND_SCRIPT"
  "$CEREMONY_DIR/PROPOSED-PATCH.md"
  "$CEREMONY_DIR/COMMIT-MSG-F.txt"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-F.sh"
  "$CEREMONY_DIR/test-ceremony-scripts-F.sh"
  "$CEREMONY_DIR/README-F.md"
  "$PATCH"
  "$SENTINEL"
)
UNCOMMITTED=""
for m in "${MATERIAL_LIST[@]}"; do
  [ -f "$ROOT/$m" ] || die "material AUSENTE na arvore viva: $m
  Rode primeiro:  bash $ROOT/$CEREMONY_DIR/finalize-F.sh"
  git -C "$ROOT" ls-files --error-unmatch -- "$m" >/dev/null 2>&1 \
    || UNCOMMITTED="$UNCOMMITTED  $m
"
done
if [ -n "$UNCOMMITTED" ]; then
  if [ "${CEO_F_HARNESS_UNCOMMITTED:-}" = "1" ]; then
    printf '\033[33m  CEO_F_HARNESS_UNCOMMITTED=1\033[0m — material(is) ainda NAO commitado(s):\n'
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
    printf '    CEO_F_HARNESS_UNCOMMITTED=1 bash %s\n' "$ROOT/$CEREMONY_DIR/test-ceremony-scripts-F.sh" >&2
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
# T-S329-2 / classe d9d9cab: com os materiais JA commitados em HEAD o index
# fica vazio e um commit incondicional aborta com "nothing to commit" — o
# harness estaria vermelho pelo motivo errado. Index vazio => segue sem commit.
if git -C "$SRC" diff --cached --quiet; then
  printf '  materiais ja commitados em HEAD — commit sintetico dispensado\n'
else
  git -C "$SRC" -c user.name=selftest -c user.email=selftest@example.invalid \
    commit -q -m "selftest: materiais da cerimonia wave-s330-F" \
    || die "commit sintetico falhou no clone"
fi
SYNTH_HEAD="$( git -C "$SRC" rev-parse HEAD )"
printf '  commit sintetico: %s (%d registro(s) de rail)\n' "$SYNTH_HEAD" "$RAIL_COPIED"

# O patch foi gerado contra o HEAD vivo, que agora e ANCESTRAL do commit
# sintetico. Isso e exatamente a forma que o SIGN/LAND esperam (base ancestral,
# sem drift nos paths tocados), entao nao ha nada a re-gerar.
git -C "$SRC" apply --check "$PATCH" \
  || die "o E.patch nao aplica no clone — o setup do harness esta errado"
printf '  E.patch aplica limpo no clone\n'

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
  # `_last_n` fica -1 se nenhum rail-round-<N>.md tiver numero decimal; sem este
  # piso o plant nasceria como `rail-round-0.md` e o proprio SIGN o leria como
  # o ultimo — funcionaria por acidente, o que e pior do que falhar.
  [ "$_last_n" -ge 0 ] || _last_n=0
  RAIL_SYNTHETIC=$(( _last_n + 1 ))
  cat > "$SRC/$CEREMONY_DIR/rail-round-$RAIL_SYNTHETIC.md" <<EOF
# HARNESS ARTIFACT — NAO E UM REGISTRO DE RAIL REAL

Rail-Verdict: APPROVE

Este arquivo existe SO dentro do clone descartavel do
test-ceremony-scripts-F.sh, para destravar os casos que exigem um SIGN verde
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
# Restaura os placeholders de assinatura no clone: o SIGN preenche
# Anchor-SHA/Data/Approved-By por regex ancorado no placeholder e ABORTA se ja
# estiverem preenchidos ("campo nao encontrado ou ja preenchido"). Um caso que
# re-assina (T12/T14) precisa devolver o sentinel ao estado de draft e apagar
# o .asc velho ANTES do commit do plant.
_reset_sign_fields() {
  python3 - "$1/$SENTINEL" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = re.sub(r"(?m)^Anchor-SHA: .*$", "Anchor-SHA: TO-FILL-AT-SIGN", s)
s = re.sub(r"(?m)^Data: .*$", "Data: TO-FILL-AT-SIGN", s)
s = re.sub(r"(?m)^Approved-By: .*$", "Approved-By: @Canhada-Labs TO-FILL-AT-SIGN", s)
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
  # Sem interruptor de pulo: esta wave nao tem gate caro, e o LAND-F nao le
  # variavel nenhuma de skip. Passar uma seria carga morta que sugere, a quem
  # ler, que existe um gate opcional aqui.
  ( cd "$_ld" && CEREMONY_SELFTEST_NO_GPG=1 \
      bash "$LAND_SCRIPT" "$@" ) >"$( _logdir "$_ld" )/land.log" 2>&1
}
# Commita um plant feito ANTES da assinatura. Sem isto o SIGN aborta no P0-c
# ("modificacoes RASTREADAS na arvore") e o caso mede o P0-c em vez do gate que
# ele quer exercitar. `git add -- <arquivo>`, nunca `-A`: o plant e sempre UM
# arquivo conhecido, e `-A` e um add capaz de diretorio — bloqueado pela regra
# R4 do ceremony-lint.
_commit_plant() {
  # T-S329-2 / classe d9d9cab: um plant que coincide com o estado ja commitado
  # em HEAD (ex.: o trailer do COMMIT-MSG ja preenchido na arvore viva) deixa o
  # index vazio, e um commit incondicional abortaria com "nothing to commit" —
  # o cenario ficaria vermelho pelo motivo errado. Index vazio => plant ja
  # vigente, seguir sem commit.
  ( _d="$1"; shift; cd "$_d" && git add -- "$@" \
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
step "T0 — bijecao das chaves EXPECTED (usadas <-> declaradas)"
# ---------------------------------------------------------------------------
# Nos DOIS sentidos, e nenhum e teorico:
#
#   usada mas nao declarada  -> `_expect` e fail-CLOSED, entao o land ABORTA no
#     meio do V-block, DEPOIS de o patch ja estar aplicado. Foi exatamente o
#     que a montagem deste pacote produziu: o V7a herdado do pacote E lia
#     `EXPECTED_CEREMONY_LINT_BLOCKING` e a base de F nao a declarava.
#   declarada mas nao usada  -> uma expectativa que nada compara. E a classe
#     que esta wave inteira existe para fechar, reaparecendo no material de
#     cerimonia.
#
# O caso roda antes de tudo porque um pacote que falha aqui nao merece os
# outros 16 casos.
_used="$( grep -ohE '_expect [A-Z_]+' \
            "$ROOT/$CEREMONY_DIR/finalize-F.sh" \
            "$ROOT/$SIGN_SCRIPT" "$ROOT/$LAND_SCRIPT" \
          | awk '{print $2}' | LC_ALL=C sort -u )"
_declared="$( grep -oE '^[A-Z_]+=' "$ROOT/$BASELINE_ENV" | tr -d '=' | LC_ALL=C sort -u )"
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
if [ "$RAIL_IS_APPROVE" = "1" ]; then
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
    fail "T2: o --dry-run reprovou (rc=$_er_rc):"; tail -12 "$( _logdir "$D" )/land.log" | sed 's/^/        /'
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
  python3 - "$D/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s2 = s.replace("  - scripts/build-plugin.py\n",
               "  - scripts/build-plugin.py\n  - scripts/install.sh\n", 1)
assert s2 != s, "plant T4 MORTO: a ancora nao existe no Scope deste sentinel"
open(p, "w", encoding="utf-8").write(s2)
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
  python3 - "$D/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s2 = s.replace("  - .github/workflows/validate.yml\n", "", 1)
assert s2 != s, "plant T5 MORTO: a ancora nao existe no Scope deste sentinel"
open(p, "w", encoding="utf-8").write(s2)
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
D="$( _fresh )"
sed -i.bak '/^EXPECTED_PATCH_PATHS=/d' "$D/$BASELINE_ENV" && rm -f "$D/$BASELINE_ENV.bak"
# O plant tem de ser COMMITADO e o SIGN tem de PASSAR. Sem isso o SIGN aborta no
# P0-c (modificacao rastreada), o `.asc` nunca nasce, e o land morre no G0 por
# "assinatura ausente" — vermelho pelo motivo ERRADO, que e indistinguivel de
# um `_expect` morto. Medido: foi assim que este caso reprovou na 1a execucao.
_commit_plant "$D" "$BASELINE_ENV" || fail "T7: nao consegui commitar o plant"
_sign "$D" || fail "T7: SIGN falhou no setup (ele nao le esta chave; deveria passar)"
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
      tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
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
    tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
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
  tail -8 "$( _logdir "$D" )/sign.log" | sed 's/^/        /'
fi
_done "$D"

# ---------------------------------------------------------------------------
step "T11 — V4c: contagem ERRADA de referencias ao gate no workflow => vermelho"
# ---------------------------------------------------------------------------
# `unwired = no test`. Este caso prova que o V4c COMPARA, em vez de so contar.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _set_expect "$D" EXPECTED_YML_GEN_CHECK_REFS 7
  _commit_plant "$D" "$BASELINE_ENV" || fail "T11: nao consegui commitar o plant"
  _sign "$D" || fail "T11: SIGN falhou no setup"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "esperado 7" "T11: V4c pega contagem de wiring errada"
  _done "$D"
else
  skip "T11: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T12 — V5a: a paridade da derivacao e VIVA (roda o gerador de verdade)"
# ---------------------------------------------------------------------------
# O gate central da wave. O plant e no ARTEFATO, nao no numero esperado: um
# unico byte alterado no template ja o desalinha do que o `_derivation` produz,
# e o V5a tem de acusar. Se ele passar com o template adulterado, o gate esta
# lendo outra coisa (ou nao esta rodando).
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _sign "$D" || fail "T12: SIGN falhou no setup"
  # O patch e aplicado pelo LAND; o plant tem de sobreviver a isso, entao ele
  # entra depois — via o proprio EXPECTED, que e o que o V5a compara.
  _set_expect "$D" EXPECTED_GEN_CHECK_RC 1
  _reset_sign_fields "$D"
  _commit_plant "$D" "$BASELINE_ENV" "$SENTINEL" || fail "T12: nao consegui commitar o plant"
  _sign "$D" || fail "T12: re-SIGN falhou (o EXPECTED mudou)"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "esperado 1" "T12: V5a roda o gerador e compara o rc declarado"
  _done "$D"
else
  skip "T12: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T13 — V2: a suite de unidade e REALMENTE executada e comparada"
# ---------------------------------------------------------------------------
# LAND COMPLETO (sem --dry-run). O plant e no numero esperado: o V2 roda o
# pytest de verdade, le "N passed" e compara.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _set_expect "$D" EXPECTED_UNIT_PYTEST_PASSED 9999
  _commit_plant "$D" "$BASELINE_ENV" || fail "T13: nao consegui commitar o plant"
  _sign "$D" || fail "T13: SIGN falhou no setup"
  _er_rc=0; _land "$D" || _er_rc=$?
  _expect_red "$D" "esperado 9999" "T13: V2 roda o pytest e compara com o declarado"
  _done "$D"
else
  skip "T13: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T14 — V6d: a tabela ACCEL de volta => o plugin duplica => vermelho"
# ---------------------------------------------------------------------------
# O unico caso que prova a cura do FU-F-ACCEL na CERIMONIA, e nao apenas na
# suite. O plant e o DEFEITO ORIGINAL, reproduzido no mecanismo: a tabela
# literal mais o `extend` que `derive`/`compose` fazia antes. Com ele, os quatro
# aceleradores voltam a ser registrados duas vezes e o V6d tem de acusar
# `duplicata(s)`. Um V6 que passe aqui esta contando outra coisa.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _sign "$D" || fail "T14: SIGN falhou no setup"
  # O plant vive no EXPECTED (o build-plugin.py e reescrito pelo patch do LAND,
  # entao adulterar o arquivo aqui seria desfeito). Declarar 4 duplicatas
  # esperadas com o codigo CURADO produzindo 0 e a mesma prova, pelo outro lado:
  # o gate compara de verdade.
  _set_expect "$D" EXPECTED_PLUGIN_DUPLICATE_TRIPLES 4
  _reset_sign_fields "$D"
  _commit_plant "$D" "$BASELINE_ENV" "$SENTINEL" || fail "T14: nao consegui commitar o plant"
  _sign "$D" || fail "T14: re-SIGN falhou (o EXPECTED mudou)"
  _er_rc=0; _land "$D" --dry-run || _er_rc=$?
  _expect_red "$D" "esperado" "T14: V6d compara as duplicatas do plugin"
  _done "$D"
else
  skip "T14: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T15a — mensagem de commit com o trailer por preencher => vermelho"
# ---------------------------------------------------------------------------
# O `COMMIT-MSG-F.txt` sai desta cerimonia com
# `Pair-Rail-Reviewed: TO-FILL-AFTER-LAST-RAIL-ROUND` de proposito: o CEO so
# sabe QUANTAS rodadas houve depois da ultima. Um land que aceitasse isso
# gravaria no historico um commit que mente sobre a propria revisao.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  if grep -qF 'Pair-Rail-Reviewed: TO-FILL' "$D/$CEREMONY_DIR/COMMIT-MSG-F.txt"; then
    _sign "$D" || fail "T15a: SIGN falhou no setup"
    _er_rc=0; _land "$D" || _er_rc=$?
    _expect_red "$D" "trailer Pair-Rail-Reviewed por preencher" \
                "T15a: o land recusa a mensagem com o trailer por preencher"
  else
    skip "T15a: o trailer ja esta preenchido (o CEO fechou o rail)"
  fi
  _done "$D"
else
  skip "T15a: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T15b — com o trailer preenchido, o LAND COMPLETO e VERDE (nao-vacuidade)"
# ---------------------------------------------------------------------------
# Sem este caso, um harness em que TODOS os casos ficassem vermelhos por um
# defeito comum passaria como "N/N". Aqui o land vai ate o commit (o push e
# pulado no auto-teste) e o `.asc` tem de estar DENTRO do commit.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  python3 - "$D/$CEREMONY_DIR/COMMIT-MSG-F.txt" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = re.sub(r"^Pair-Rail-Reviewed: TO-FILL.*$",
           "Pair-Rail-Reviewed: selftest (trailer preenchido pelo harness)",
           s, count=1, flags=re.M)
open(p, "w", encoding="utf-8").write(s)
PY
  _commit_plant "$D" "$CEREMONY_DIR/COMMIT-MSG-F.txt" || fail "T15b: nao consegui commitar o plant"
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
else
  skip "T15b: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "T16 — V3b: o indice de ADRs e comparado de verdade (nao so contado)"
# ---------------------------------------------------------------------------
# O land do pacote D (S329) deixou o main VERMELHO por um doc GERADO que nao foi
# regenerado. Este caso prova que o V3b roda `generate-adr-index.py --check` e
# compara o rc declarado, em vez de assumir.
if [ "$RAIL_IS_APPROVE" = "1" ]; then
  D="$( _fresh )"
  _set_expect "$D" EXPECTED_ADR_INDEX_CHECK_RC 1
  _commit_plant "$D" "$BASELINE_ENV" || fail "T16: nao consegui commitar o plant"
  _sign "$D" || fail "T16: SIGN falhou no setup"
  _er_rc=0; _land "$D" || _er_rc=$?
  _expect_red "$D" "esperado 1" "T16: V3b roda o gerador de indice e compara"
  _done "$D"
else
  skip "T16: depende de um SIGN verde"
fi

# ---------------------------------------------------------------------------
step "RESUMO"
# ---------------------------------------------------------------------------
printf '\n  PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
printf '\n  O que NAO e coberto por padrao, e por que:\n'
printf '    - Esta wave nao tem gate CARO: todo o V-block roda em menos de um\n'
printf '      minuto, entao nao ha caso opt-in nem interruptor de pulo. O que o\n'
printf '      harness NAO cobre e o `Smoke Install` e o `Validate` do CI, que so\n'
printf '      rodam depois do push.\n'
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
