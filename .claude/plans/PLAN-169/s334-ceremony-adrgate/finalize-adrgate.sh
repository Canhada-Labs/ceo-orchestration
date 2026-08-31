#!/usr/bin/env bash
# finalize-adrgate.sh — DERIVA o ADRGATE.patch da arvore-sombra e o baseia no HEAD vivo.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao;
# nao ha gerador para o passo de derivacao (o generate-ceremony.sh assume o
# layout architect/round-N/approved.md, que esta cerimonia nao usa).
#
# O QUE ESTA WAVE ENTREGA (PLAN-169 wave-adrgate, rota rail-round-3 S333): o
# ledger DECLARADO de isencao de supersessao vira DADO revisado no
# `.claude/adr/README.md` (2 entradas, mandatory-fire), os DOIS gates de ADR
# (`check-adr-chain.py` e `generate-adr-index.py --check`) entram no
# `validate.yml`, o ADR-197 recebe o flip textual PROPOSED -> ACCEPTED (a
# ratificacao real ja esta commitada: .asc sobre wave-s330-F-approved.md,
# land 303ae55), e o fixture de corpus flipa "2 erros ADR-111" ->
# "limpo + 2 entradas firing" com assercao bilateral.
#
# ESTE SCRIPT E UM CLONE GATE-A-GATE DO finalize-F.sh, e isso e deliberado.
# Os guards dele foram pagos com o pacote D abortando duas vezes na S329:
#   * o guard de drift (se um path do pacote mudou no HEAD vivo depois que a
#     sombra nasceu, copiar por conteudo REVERTERIA a edicao do outro);
#   * o `|| true` no grep cujo ZERO casamentos e a resposta VERDE (sob
#     `pipefail` o pipeline sairia 1 e o `set -e` mataria o script SEM
#     MENSAGEM, exatamente no caso que o gate existe para aprovar);
#   * a checagem de HEAD-andou entre o inicio da bateria e a derivacao do patch.
# Eles estao aqui byte-a-byte. O que muda e o bloco de constantes e o passo 4
# (a bateria da wave-F validava gerador de settings/jq/plugin; esta valida a
# cadeia de ADRs, o ledger e o wire no CI).
#
# COMO A RE-BASE E FEITA, e por que NAO por `git apply --3way`.
# A re-base e por CONTEUDO: uma arvore-sombra limpa em HEAD recebe os
# arquivos da sombra de trabalho, path a path, e o patch e o diff DESSA arvore
# contra o HEAD. Um patch de `new file mode` aplicado com `--3way` sobre uma
# arvore onde o arquivo ja existe cai em conflito "both added" (medido na
# cerimonia F com o DESIGN commitado em snapshot intermediario).
#
# O QUE ELE FAZ, em ordem:
#   0. pre-condicoes (materiais, gerador, sombra, HEAD em main);
#   1. recusa se o sentinel JA estiver assinado (re-finalizar invalida o .asc);
#   2. le o conjunto EXPECTED de paths do EXPECTED-BASELINE.txt (fonte unica) e
#      recusa se a sombra mexeu em qualquer path FORA dele;
#   3. guard de drift base-da-sombra vs HEAD vivo (o paragrafo acima);
#   4. arvore-sombra em HEAD (git worktree add --detach) + copia por conteudo;
#   5. bateria CURTA na arvore-sombra (os gates CAROS sao o V-block do LAND);
#   6. finalize_patch.py: patch + sha256 + Scope DERIVADO + Patch-base;
#   7. BASE-SHA.txt, `git apply --check` na arvore viva;
#   8. stageia EXATAMENTE os 4 arquivos regenerados e commita com `-m`
#      (nenhum editor abre em momento nenhum). Sem diferenca => NADA a fazer.
#
# Uso:  bash .claude/plans/PLAN-169/s334-ceremony-adrgate/finalize-adrgate.sh
#       bash .../finalize-adrgate.sh --no-commit  (gera tudo, NAO stageia nada)
#       bash .../finalize-adrgate.sh --with-slow  (roda tambem os gates de
#                                                  corpus lentos: verify-counts
#                                                  e claims)
#       CEO_ADRGATE_SHADOW=/caminho/da/sombra bash .../finalize-adrgate.sh
set -euo pipefail

# --- argumentos -----------------------------------------------------------
# `--no-commit` existe para quem monta o pacote com OUTRO trabalho em voo na
# mesma arvore: ele gera patch/Scope/BASE-SHA e NAO toca no index. Um `git add`
# aqui arrastaria (ou confundiria) o staging de quem estiver trabalhando ao
# lado. O fluxo do Owner na manha usa a forma SEM flag, que commita.
#
# `--with-slow` roda os gates de CORPUS (`verify-counts.sh`, ~3 min, e
# `check-claude-md-claims.py`) NA ARVORE-SOMBRA e os compara com o valor
# DECLARADO. Eles NAO reescrevem a base — um instrumento que ajusta a propria
# expectativa nao mede nada. Existem para quem monta o pacote conferir antes da
# manha do Owner, em vez de descobrir a divergencia no V8 do LAND.
NO_COMMIT=0
WITH_SLOW=0
for arg in "$@"; do
  case "$arg" in
    --no-commit) NO_COMMIT=1 ;;
    --with-slow) WITH_SLOW=1 ;;
    *)
      printf '\n\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$arg" >&2
      printf '  Formas validas:\n' >&2
      printf '    bash %s\n' "$0" >&2
      printf '    bash %s --no-commit\n' "$0" >&2
      printf '    bash %s --with-slow    (roda os gates de corpus na sombra)\n' "$0" >&2
      exit 1 ;;
  esac
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes do pacote (o UNICO bloco que muda entre waves) -------------
PLAN_DIR=".claude/plans/PLAN-169"
CEREMONY_DIR="$PLAN_DIR/s334-ceremony-adrgate"
SENTINEL="$PLAN_DIR/wave-adrgate-approved.md"
PATCH="$CEREMONY_DIR/ADRGATE.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la); copia-lo
# para ca criaria um segundo original divergente.
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S334-ADRGATE-SIGN.sh"
CHAIN_SCRIPT=".claude/scripts/check-adr-chain.py"
INDEX_SCRIPT=".claude/scripts/generate-adr-index.py"
YML=".github/workflows/validate.yml"
ADR_DIR=".claude/adr"
FIXTURE=".claude/scripts/tests/test_check_adr_chain.py"
# O conjunto de suites da bateria. Mais largo que os arquivos que a wave EDITA,
# de proposito: o indice e o frozen-subset do validate.yml sao o que o wire
# novo e a regeneracao da tabela poderiam quebrar SEM tocar num arquivo deles.
UNIT_TESTS=".claude/scripts/tests/test_check_adr_chain.py \
.claude/scripts/tests/test_generate_adr_index.py \
.claude/scripts/tests/test_validate_template_frozen_subset.py"
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
warn(){ printf '  \033[33mWARN\033[0m %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# Leitor da base esperada, fail-CLOSED: chave ausente ABORTA, nunca vira "0".
_expect() {
  _ev="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
  [ -n "$_ev" ] || die "chave '$1' AUSENTE em $BASELINE_ENV"
  printf '%s' "$_ev"
}

WT=""
_cleanup() {
  if [ -n "$WT" ] && [ -d "$WT" ]; then
    git worktree remove --force "$WT" >/dev/null 2>&1 || printf ''
    rm -rf "$WT" 2>/dev/null || printf ''
  fi
  git worktree prune >/dev/null 2>&1 || printf ''
}
trap _cleanup EXIT

# ---------------------------------------------------------------------------
step "0 — pre-condicoes"
# ---------------------------------------------------------------------------
for f in "$SENTINEL" "$PROPOSED" "$BASELINE_ENV" "$FINALIZE"; do
  [ -f "$f" ] || die "material ausente: $f"
done

# `if`, nao `[ ... ] && die`: sob `set -e` a forma AND-OR cujo teste falha
# devolve 1 no fim do statement, e a semantica de errexit sobre lista AND-OR
# varia entre shells.
if [ -f "$SENTINEL.asc" ]; then
  die "o sentinel JA esta assinado ($SENTINEL.asc).
  Re-finalizar reescreve o sentinel e invalida a assinatura.
  Se voce precisa mesmo re-finalizar, apague o .asc conscientemente e
  re-assine depois:  rm $ROOT/$SENTINEL.asc"
fi

_cur_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '')"
[ "$_cur_branch" = "main" ] || die "HEAD esta em '$_cur_branch', nao em 'main' — o land so roda no main"
HEAD_SHA="$(git rev-parse HEAD)"
ok "HEAD em main: $HEAD_SHA"

# --- resolucao da sombra ---------------------------------------------------
# `CEO_ADRGATE_SHADOW` tem precedencia. Sem ela, a busca e sob o scratchpad
# DESTE repositorio (slug = caminho absoluto com `/` -> `-`, o mesmo que o
# harness usa): pegar `*/*/scratchpad` cru cairia no scratchpad de OUTRO
# projeto.
#
# A pergunta "isto e um repositorio git?" e feita AO GIT, nunca por
# `[ -d "$x/.git" ]`: num `git worktree` o `.git` e um ARQUIVO com um ponteiro
# `gitdir:`, e o teste de diretorio rejeitaria uma sombra perfeitamente valida
# (medido — foi assim que a primeira execucao do finalize-F recusou uma
# arvore-sombra criada com `git worktree add`).
_is_git_tree() { git -C "$1" rev-parse --git-dir >/dev/null 2>&1; }

SHADOW="${CEO_ADRGATE_SHADOW:-}"
if [ -z "$SHADOW" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  _slug="$( printf '%s' "$ROOT" | tr '/' '-' )"
  for _cand in "$_sp_real/claude-501/$_slug"/*/scratchpad/shadow-adrgate; do
    [ -d "$_cand" ] || continue
    _is_git_tree "$_cand" || continue
    SHADOW="$_cand"
    break
  done
fi
[ -n "$SHADOW" ] || die "arvore-sombra do pacote adrgate nao encontrada.
  Procurei por  <scratchpad deste repo>/*/scratchpad/shadow-adrgate  e nao
  achei um repositorio git. Passe o caminho explicitamente:
    CEO_ADRGATE_SHADOW=/caminho/da/sombra bash $ROOT/$CEREMONY_DIR/finalize-adrgate.sh"
[ -d "$SHADOW" ] || die "CEO_ADRGATE_SHADOW nao existe: $SHADOW"
_is_git_tree "$SHADOW" || die "CEO_ADRGATE_SHADOW nao e um repositorio git: $SHADOW"
_shadow_rp="$( cd "$SHADOW" && pwd -P )"
_root_rp="$( cd "$ROOT" && pwd -P )"
[ "$_shadow_rp" != "$_root_rp" ] || die "a sombra aponta para a arvore VIVA — recusado"
SHADOW="$_shadow_rp"
SHADOW_BASE="$( git -C "$SHADOW" rev-parse HEAD )"
ok "sombra: $SHADOW (base $SHADOW_BASE)"

# ---------------------------------------------------------------------------
step "1 — conjunto EXPECTED e o que a sombra mexeu"
# ---------------------------------------------------------------------------
# O conjunto vem do EXPECTED-BASELINE.txt: fonte UNICA. Uma segunda lista aqui
# divergiria da que o LAND compara, e a divergencia seria silenciosa.
EXPECTED_PATHS="$(_expect EXPECTED_PATCH_PATHS)"
EXPECTED_SORTED="$( printf '%s\n' $EXPECTED_PATHS | sed '/^$/d' | LC_ALL=C sort -u )"
printf '      %s path(s) esperados:\n' "$( printf '%s\n' "$EXPECTED_SORTED" | wc -l | tr -d ' ' )"
printf '%s\n' "$EXPECTED_SORTED" | sed 's/^/        /'

# Porcelain NUL-delimitado: o corte de 3 caracteres deixaria `old -> new`
# inteiro num rename, e a classificacao usaria o path VELHO.
#
# `-uall` NAO e opcional. Sem ele o porcelain COLAPSA um diretorio inteiramente
# untracked numa unica entrada com barra no fim, e a comparacao contra o
# conjunto EXPECTED — que lista ARQUIVOS — abortaria dizendo que a sombra mexeu
# num path fora do escopo. Medido na cerimonia F: uma sombra recem-criada
# reproduz isso; a sombra de trabalho nao, porque la os arquivos novos ja estao
# staged. Um gate que so falha em sombra nova e um gate que falha na hora
# errada.
CHANGED=""
while IFS= read -r -d '' entry; do
  [ -z "$entry" ] && continue
  xy="${entry:0:2}"
  epath="${entry:3}"
  case "$xy" in
    *R*|*C*)
      IFS= read -r -d '' _from || true
      die "rename/copia na arvore-sombra ($xy: $_from -> $epath).
  O Scope assinado nao expressa rename. Resolva na sombra antes de finalizar." ;;
  esac
  case "$epath" in
    *$'\n'*) die "path com newline na arvore-sombra — recusado" ;;
  esac
  CHANGED="$CHANGED$epath
"
done < <( git -C "$SHADOW" status --porcelain=v1 -z -uall )
CHANGED_SORTED="$( printf '%s' "$CHANGED" | sed '/^$/d' | LC_ALL=C sort -u )"
[ -n "$CHANGED_SORTED" ] || die "a sombra nao tem diferenca contra a propria base — nada a finalizar"

OUTSIDE="$( comm -23 <( printf '%s\n' "$CHANGED_SORTED" ) <( printf '%s\n' "$EXPECTED_SORTED" ) )"
if [ -n "$OUTSIDE" ]; then
  die "a sombra mexeu em path(s) FORA do conjunto EXPECTED:
$( printf '  %s\n' $OUTSIDE )
  O conjunto vive em $BASELINE_ENV (EXPECTED_PATCH_PATHS). Ou a sombra
  ganhou trabalho que esta cerimonia nao revisou, ou o conjunto ficou velho.
  Nos DOIS casos a decisao e do CEO — este script nao alarga escopo sozinho."
fi
ok "a sombra mexeu em $( printf '%s\n' "$CHANGED_SORTED" | wc -l | tr -d ' ' ) path(s), todos dentro do EXPECTED"

# ---------------------------------------------------------------------------
step "2 — guard de drift (a licao da S329: o pack nao pode REVERTER o destino)"
# ---------------------------------------------------------------------------
# Para cada path EXPECTED: se ele existe na BASE DA SOMBRA e tambem no HEAD
# vivo, os dois blobs tem de ser byte-identicos. Se divergiram, alguem editou o
# destino depois que a sombra foi criada e a copia por conteudo REVERTERIA essa
# edicao. A leitura da base e feita DENTRO da sombra (`git -C "$SHADOW" show`):
# o HEAD vivo pode nem conter o commit da base.
DRIFTED=""
CLASS_B=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  _in_base=0; _in_head=0
  git -C "$SHADOW" cat-file -e "$SHADOW_BASE:$p" 2>/dev/null && _in_base=1 || _in_base=0
  git cat-file -e "HEAD:$p" 2>/dev/null && _in_head=1 || _in_head=0
  if [ "$_in_base" = "1" ] && [ "$_in_head" = "1" ]; then
    _b="$( git -C "$SHADOW" show "$SHADOW_BASE:$p" | shasum -a 256 | awk '{print $1}' )"
    _h="$( git show "HEAD:$p" | shasum -a 256 | awk '{print $1}' )"
    [ "$_b" = "$_h" ] || DRIFTED="$DRIFTED  $p
"
  elif [ "$_in_head" = "1" ]; then
    # Existe no HEAD vivo mas NAO na base da sombra: e material deste pacote
    # (commitado num snapshot intermediario). A sombra e a autoridade — mas a
    # mudanca fica VISIVEL no log, e uma edicao viva NAO-COMMITADA aborta.
    CLASS_B="$CLASS_B  $p
"
  fi
done < <( printf '%s\n' "$EXPECTED_SORTED" )

if [ -n "$DRIFTED" ]; then
  die "path(s) do pacote mudaram no HEAD vivo depois que a sombra foi criada:
$DRIFTED
  Copiar a sombra por cima REVERTERIA essas edicoes — foi exatamente o que
  abortou o pacote D duas vezes na S329. A cura NAO e forcar: e re-derivar a
  sombra POR ITEM sobre o conteudo novo e rodar este script de novo.
    git -C $SHADOW diff $SHADOW_BASE HEAD -- <path>   (o que a sombra mudou)
    git show HEAD:<path>                              (o que o vivo tem hoje)"
fi
if [ -n "$CLASS_B" ]; then
  warn "path(s) que existem no HEAD vivo mas NAO na base da sombra (a sombra manda):"
  printf '%s' "$CLASS_B"
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    if ! git diff --quiet -- "$p" 2>/dev/null; then
      die "$p tem modificacao NAO-COMMITADA na arvore viva.
  Este path e re-escrito a partir da sombra; a sua edicao viva seria perdida.
  Commite-a (e re-derive a sombra) ou reverta-a antes de finalizar."
    fi
  done < <( printf '%s' "$CLASS_B" | sed 's/^  //' )
fi
ok "nenhum path do pacote derivou entre a base da sombra e o HEAD vivo"

# ---------------------------------------------------------------------------
step "3 — arvore-sombra em $HEAD_SHA + copia por conteudo"
# ---------------------------------------------------------------------------
WT="$( mktemp -d "${TMPDIR:-/tmp}/s334adrgate-wt.XXXXXX" )/wt"
git worktree add --detach --quiet "$WT" "$HEAD_SHA" \
  || die "git worktree add falhou — a arvore-sombra nao foi criada"
ok "arvore-sombra: $WT"

COPIED=0; REMOVED=0
while IFS= read -r p; do
  [ -z "$p" ] && continue
  if [ -f "$SHADOW/$p" ]; then
    mkdir -p "$WT/$( dirname "$p" )"
    cp -p "$SHADOW/$p" "$WT/$p" || die "falhei ao copiar $p da sombra"
    COPIED=$(( COPIED + 1 ))
  elif [ -f "$WT/$p" ]; then
    # A sombra APAGOU o path. Reproduzir a remocao, nunca ignora-la.
    rm -f -- "$WT/$p" || die "falhei ao remover $p na arvore-sombra"
    REMOVED=$(( REMOVED + 1 ))
  fi
done < <( printf '%s\n' "$EXPECTED_SORTED" )
ok "$COPIED arquivo(s) copiados, $REMOVED removido(s)"

# `cp` nao inventa marcadores de conflito, mas uma sombra deixada no meio de um
# merge carregaria os dela — e um patch com '<<<<<<<' assinado seria bytes
# quebrados no main. A varredura e restrita aos paths copiados.
while IFS= read -r p; do
  [ -z "$p" ] && continue
  [ -f "$WT/$p" ] || continue
  if grep -q -e '^<<<<<<< ' -e '^>>>>>>> ' -- "$WT/$p"; then
    die "a arvore-sombra ficou com marcadores de conflito em $p — recusado"
  fi
done < <( printf '%s\n' "$EXPECTED_SORTED" )
ok "nenhum marcador de conflito nos paths copiados"

# ---------------------------------------------------------------------------
step "4 — bateria CURTA na arvore-sombra"
# ---------------------------------------------------------------------------
# A bateria LONGA (verify-counts ~3 min, governanca completa, ceremony-lint)
# e o V-block do LAND; repeti-la aqui dobraria o tempo da manha sem acrescentar
# informacao — salvo sob `--with-slow`, que existe para conferir antes.
# O que roda aqui e o que responde "o conteudo copiado ainda e valido?".

# 4a — o gate central da wave: a cadeia de ADRs sai LIMPA com o ledger.
# A saida do checker vai para STDERR (medido: main() escreve PASS/FAIL la),
# entao o log captura 2>&1 — um grep so em stdout seria vacuo.
CHAIN_LOG="$WT.chain.log"
CHAIN_RC=0
( cd "$WT" && python3 "$CHAIN_SCRIPT" ) > "$CHAIN_LOG" 2>&1 || CHAIN_RC=$?
_chain_exp="$(_expect EXPECTED_ADR_CHAIN_RC)"
[ "$CHAIN_RC" = "$_chain_exp" ] \
  || { tail -8 "$CHAIN_LOG" | sed 's/^/      /' >&2
       die "4a: '$CHAIN_SCRIPT' saiu rc=$CHAIN_RC, esperado $_chain_exp.
  Era FAIL 2 (ambos ADR-111) desde f348ee9; o ledger com as 2 entradas zera.
  Log: $CHAIN_LOG"; }
grep -qF 'PASS: ADR chain clean' "$CHAIN_LOG" \
  || die "4a: rc=$CHAIN_RC mas a saida nao traz 'PASS: ADR chain clean' — o
  checker mudou de forma; um gate que so olha o rc aceitaria isso. Log: $CHAIN_LOG"
ok "4a: cadeia de ADRs limpa (rc=$CHAIN_RC, PASS nomeado)"

# 4b — os dois scripts-sujeito e o fixture tocado compilam.
for _pyf in "$CHAIN_SCRIPT" "$INDEX_SCRIPT" "$FIXTURE"; do
  ( cd "$WT" && PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$_pyf" ) \
    || die "4b: py_compile reprovou em $_pyf"
done
ok "4b: $CHAIN_SCRIPT, $INDEX_SCRIPT e o fixture compilam"

# 4c — a suite de unidade, contra a contagem DECLARADA.
UNIT_LOG="$WT.unit.log"
UNIT_RC=0
# shellcheck disable=SC2086  # $UNIT_TESTS e uma lista controlada, sem espacos
( cd "$WT" && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest $UNIT_TESTS -q -p no:cacheprovider ) \
  > "$UNIT_LOG" 2>&1 || UNIT_RC=$?
[ "$UNIT_RC" -eq 0 ] || { tail -25 "$UNIT_LOG" | sed 's/^/      /' >&2
                          die "4c: a suite de unidade reprovou (rc=$UNIT_RC) — log em $UNIT_LOG"; }
# "N deselected" NAO e "N passed" (licao S325). A linha do `pytest -q` COMECA
# pelo numero, entao o padrao aceita inicio de linha OU um nao-digito antes.
# O `|| true` faz a mensagem NOMEADA abaixo disparar; sem ele uma saida sem
# "N passed" mataria o script mudo.
_unit_obs="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$UNIT_LOG" || true; } \
              | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_unit_obs" ] || die "4c: nao consegui ler 'N passed' — log em $UNIT_LOG"
_unit_exp="$(_expect EXPECTED_UNIT_PYTEST_PASSED)"
[ "$_unit_obs" = "$_unit_exp" ] \
  || die "4c: $_unit_obs teste(s) de unidade passaram, esperado $_unit_exp.
  Menos e regressao; mais significa que a suite cresceu — atualize
  $BASELINE_ENV conscientemente. Log: $UNIT_LOG"
# Skips: um skip a MAIS significa que uma suite parou de rodar, e um gate que
# so olha 'passed' aceitaria isso em silencio.
_skip_obs="$( { grep -oE '[0-9]+ skipped' "$UNIT_LOG" || true; } | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_skip_obs" ] || _skip_obs=0
_skip_exp="$(_expect EXPECTED_UNIT_PYTEST_SKIPPED)"
[ "$_skip_obs" = "$_skip_exp" ] \
  || die "4c: $_skip_obs teste(s) pulados, esperado $_skip_exp — uma suite parou de rodar. Log: $UNIT_LOG"
ok "4c: suite de unidade $_unit_obs/$_unit_exp (skips $_skip_obs)"

# 4d — o ledger, medido no CONSUMIDOR. O import e por importlib (o arquivo e
# hifenizado); a assercao cobre os dois lados: exatamente N entradas E zero
# parse errors — entrada malformada e fail-closed por desenho.
_ledger_exp="$(_expect EXPECTED_LEDGER_ENTRIES)"
( cd "$WT" && python3 - "$CHAIN_SCRIPT" "$_ledger_exp" <<'PYEOF'
import importlib.util, sys
from pathlib import Path
script, want = sys.argv[1], int(sys.argv[2])
spec = importlib.util.spec_from_file_location("cac_finalize", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
entries, parse_errors = mod._load_declared_exemptions(Path(".claude/adr"))
if parse_errors:
    sys.exit("parse_errors nao-vazio: %r" % (parse_errors,))
if len(entries) != want:
    sys.exit("%d entrada(s) no ledger, esperado %d" % (len(entries), want))
print("  %d entrada(s), 0 parse errors" % len(entries))
PYEOF
) || die "4d: o ledger nao bate a base declarada (EXPECTED_LEDGER_ENTRIES=$_ledger_exp)"
ok "4d: ledger com $_ledger_exp entrada(s), zero parse errors"

# 4e — controle NEGATIVO mandatory-fire, em COPIA descartavel do .claude/adr
# da propria arvore-sombra — NUNCA no vivo. Uma entrada orfa tem de derrubar o
# run com razao nomeada; um ledger que aceita entrada morta e um ledger que
# apodrece em silencio. A entrada de controle e a que o EXPECTED-BASELINE
# prescreve: pos-cura r1 (2858924) o declarante tem de estar PRESENTE no
# corpus — declarante ausente e N/A por desenho (o ledger semeado no adopter
# nao pode quebrar o CI dele) e NAO dispara mais.
FIRE_DIR="$( mktemp -d "${TMPDIR:-/tmp}/s334adrgate-fire.XXXXXX" )"
cp -R "$WT/$ADR_DIR" "$FIRE_DIR/adr"
python3 - "$FIRE_DIR/adr/README.md" <<'PYEOF' || { rm -rf "$FIRE_DIR"; die "4e: nao consegui plantar a entrada orfa na copia"; }
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
anchor = "## Declared supersession exemptions"
i = s.find(anchor)
if i < 0:
    sys.exit("secao do ledger nao encontrada na copia")
j = s.find("\n", i)
s = s[: j + 1] + "\n**ADR-120 -> ADR-197: stale**\n" + s[j + 1 :]
open(p, "w", encoding="utf-8").write(s)
PYEOF
FIRE_LOG="$WT.fire.log"
FIRE_RC=0
( cd "$WT" && python3 "$CHAIN_SCRIPT" --adr-dir "$FIRE_DIR/adr" ) > "$FIRE_LOG" 2>&1 || FIRE_RC=$?
rm -rf "$FIRE_DIR"
_fire_exp="$(_expect EXPECTED_MANDATORY_FIRE_CONTROL_RC)"
[ "$FIRE_RC" = "$_fire_exp" ] \
  || die "4e: o controle negativo mandatory-fire saiu rc=$FIRE_RC, esperado $_fire_exp.
  rc 0 aqui significa que o ledger ACEITOU uma entrada morta. Log: $FIRE_LOG"
grep -qF 'did not fire' "$FIRE_LOG" \
  || die "4e: rc=$FIRE_RC mas sem a razao 'did not fire' nomeada — o checker
  reprovou por OUTRO motivo, e o controle ficou vacuo. Log: $FIRE_LOG"
ok "4e: entrada orfa derruba o run com 'did not fire' (rc=$FIRE_RC)"

# 4f — o YAML pos-copia continua parseavel, e os steps novos continuam VISIVEIS.
if python3 -c 'import yaml' >/dev/null 2>&1; then
  ( cd "$WT" && python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$YML" ) \
    || die "4f: yaml.safe_load reprovou em $YML"
  ok "4f: yaml.safe_load OK"
else
  warn "4f: PyYAML ausente — o actionlint abaixo e o CI tambem cobrem"
fi
if command -v actionlint >/dev/null 2>&1; then
  AL_LOG="$WT.actionlint.log"
  ( cd "$WT" && actionlint "$YML" ) > "$AL_LOG" 2>&1 \
    || { sed 's/^/      /' "$AL_LOG" >&2; die "4g: actionlint reprovou em $YML"; }
  ok "4g: actionlint verde"
else
  warn "4g: actionlint AUSENTE — o CI executa"
fi
# `grep -c` sai 1 quando nao casa nada, e sob `pipefail` isso mataria o script
# mudo — o `|| true` faz a mensagem NOMEADA disparar (mesma licao do 4g de E).
_cref_obs="$( { grep -c 'check-adr-chain.py' "$WT/$YML" || true; } )"
_cref_exp="$(_expect EXPECTED_YML_CHAIN_REFS)"
[ "$_cref_obs" = "$_cref_exp" ] \
  || die "4h: o gate de cadeia aparece $_cref_obs vez(es) em $YML, esperado $_cref_exp.
  Zero significa que o step saiu do CI e a cadeia volta a apodrecer invisivel —
  'unwired = no test'."
_iref_obs="$( { grep -c 'generate-adr-index.py --check' "$WT/$YML" || true; } )"
_iref_exp="$(_expect EXPECTED_YML_INDEX_CHECK_REFS)"
[ "$_iref_obs" = "$_iref_exp" ] \
  || die "4h: o gate de indice aparece $_iref_obs vez(es) em $YML, esperado $_iref_exp."
ok "4h: o workflow invoca cadeia $_cref_obs vez(es) e indice $_iref_obs vez(es)"

# 4i — a contagem de ADRs (o patch NAO adiciona ADR) e o indice em dia.
_adr_obs="$( find "$WT/$ADR_DIR" -maxdepth 1 -name 'ADR-*.md' | wc -l | tr -d ' ' )"
_adr_exp="$(_expect EXPECTED_ADR_COUNT)"
[ "$_adr_obs" = "$_adr_exp" ] \
  || die "4i: $_adr_obs ADR(s) no disco, esperado $_adr_exp — as citacoes em
  docs ficariam defasadas e o verify-counts do LAND reprovaria."
IDX_RC=0
( cd "$WT" && python3 "$INDEX_SCRIPT" --check ) >/dev/null 2>&1 || IDX_RC=$?
_idx_exp="$(_expect EXPECTED_ADR_INDEX_CHECK_RC)"
[ "$IDX_RC" = "$_idx_exp" ] \
  || die "4i: o indice de ADRs saiu rc=$IDX_RC, esperado $_idx_exp.
  O flip do ADR-197 muda a linha dele na tabela — a primeira bateria da sombra
  REPROVOU exatamente aqui. Repare com:  python3 $INDEX_SCRIPT --write"
ok "4i: $_adr_obs ADRs, indice em dia"

# 4k — os gates de CORPUS, so sob --with-slow. Mesma leitura que o V8 do
# LAND faz: se este passa e o V8 reprova, a diferenca esta na arvore.
if [ "$WITH_SLOW" = "1" ]; then
  printf '  4k: rodando os gates de corpus na arvore-sombra (~4 min)...\n'
  CLAIMS_RC=0
  ( cd "$WT" && python3 .claude/scripts/check-claude-md-claims.py ) >/dev/null 2>&1 || CLAIMS_RC=$?
  [ "$CLAIMS_RC" = "$(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)" ] \
    || die "4k: check-claude-md-claims saiu rc=$CLAIMS_RC, esperado $(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)"
  VC_LOG="$WT.verify-counts.log"
  VC_RC=0
  ( cd "$WT" && bash .claude/scripts/local/verify-counts.sh ) > "$VC_LOG" 2>&1 || VC_RC=$?
  [ "$VC_RC" = "$(_expect EXPECTED_VERIFY_COUNTS_RC)" ] \
    || { grep -E 'DRIFT|Exit' "$VC_LOG" | head -20 | sed 's/^/      /' >&2
         die "4k: verify-counts saiu rc=$VC_RC, esperado $(_expect EXPECTED_VERIFY_COUNTS_RC) — log em $VC_LOG"; }
  ok "4k: check-claude-md-claims e verify-counts verdes"
else
  printf '  \033[33mNOTA\033[0m 4k: gates de corpus NAO executados (padrao). O V8 do LAND os roda.\n'
  printf '        Para conferir antes da manha do Owner:\n'
  printf '          bash %s --with-slow\n' "$0"
fi

# ---------------------------------------------------------------------------
step "5 — patch, Scope, Patch-base e Patch-sha256"
# ---------------------------------------------------------------------------
# O HEAD pode ter ANDADO enquanto a bateria rodava — com `--with-slow` a janela
# e de varios minutos, e mais de um agente pode commitar no mesmo checkout. O
# `finalize_patch.py` recusa (corretamente) uma sombra cuja base nao seja o HEAD
# VIVO, mas a mensagem dele descreve o sintoma, nao a causa. Aqui a causa e
# NOMEADA, e o custo de descobrir e zero: a checagem e um `rev-parse`.
HEAD_NOW="$( git rev-parse HEAD )"
if [ "$HEAD_NOW" != "$HEAD_SHA" ]; then
  die "o HEAD ANDOU enquanto a bateria rodava:
    quando este script comecou : $HEAD_SHA
    agora                      : $HEAD_NOW
  A arvore-sombra foi montada sobre o HEAD antigo, entao o patch descreveria
  outra base. Nada foi escrito. Rode este script DE NOVO — ele re-monta a
  sombra sobre o HEAD novo. Se isso se repetir, e porque alguem esta commitando
  no mesmo checkout: combine uma janela antes de re-rodar com --with-slow, que e
  o modo lento e o mais exposto a esta corrida."
fi

OLD_PATCH_SHA=""
[ -f "$PATCH" ] && OLD_PATCH_SHA="$( shasum -a 256 "$PATCH" | awk '{print $1}' )"

python3 "$FINALIZE" \
  --shadow "$WT" \
  --out "$ROOT/$PATCH" \
  --sentinel "$ROOT/$SENTINEL" \
  --proposed "$ROOT/$PROPOSED" \
  --repo-root "$ROOT" \
  || die "finalize_patch.py recusou — leia a mensagem acima; nada foi commitado"

NEW_PATCH_SHA="$( shasum -a 256 "$PATCH" | awk '{print $1}' )"
if [ -n "$OLD_PATCH_SHA" ] && [ "$OLD_PATCH_SHA" = "$NEW_PATCH_SHA" ]; then
  printf '      patch inalterado (%s)\n' "$NEW_PATCH_SHA"
fi

# Conjunto de paths do patch FINAL == EXPECTED, nos dois sentidos. O passo 1
# checou a SOMBRA; este checa o ENTREGAVEL, que e outra coisa: um path pode
# sair do patch por ficar byte-identico ao HEAD.
PATCH_PATHS="$( git apply --numstat "$PATCH" | awk '{print $3}' | LC_ALL=C sort -u )"
_extra="$( comm -23 <( printf '%s\n' "$PATCH_PATHS" ) <( printf '%s\n' "$EXPECTED_SORTED" ) )"
[ -z "$_extra" ] || die "o patch toca path(s) fora do EXPECTED:
$( printf '  %s\n' $_extra )"
_ghost="$( comm -13 <( printf '%s\n' "$PATCH_PATHS" ) <( printf '%s\n' "$EXPECTED_SORTED" ) )"
if [ -n "$_ghost" ]; then
  die "path(s) do EXPECTED que o patch NAO toca:
$( printf '  %s\n' $_ghost )
  Ou o conteudo ja esta no HEAD (a cura landou parcialmente e o pacote ficou
  velho), ou a sombra perdeu a mudanca. Chame o CEO — o G4 do LAND recusa um
  Scope mais largo que o patch, entao isto abortaria de manha."
fi
ok "conjunto de paths do patch == EXPECTED ($( printf '%s\n' "$PATCH_PATHS" | wc -l | tr -d ' ' ) paths)"

printf '%s\n' "$HEAD_SHA" > "$BASE_SHA_FILE"
ok "BASE-SHA.txt atualizado"

git apply --check "$PATCH" || die "o patch gerado NAO aplica na arvore viva"
ok "git apply --check verde na arvore viva"

# ---------------------------------------------------------------------------
step "6 — commit dos materiais regenerados (sem editor)"
# ---------------------------------------------------------------------------
if [ "$NO_COMMIT" = "1" ]; then
  warn "--no-commit: nada foi staged nem commitado."
  printf '        Os 4 materiais estao no disco, prontos para o commit de quem\n'
  printf '        estiver conduzindo a cerimonia:\n'
  for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE"; do
    printf '          %s\n' "$f"
  done
  printf '        O SIGN exige os materiais RASTREADOS — sem esse commit ele aborta.\n'
else
# Staging EXPLICITO, arquivo a arquivo. Um staging por DIRETORIO (ou o add-tudo)
# arrastaria o trabalho de outros pacotes que ainda esteja na arvore; o conjunto
# e conferido logo abaixo e um path a mais ABORTA.
for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE"; do
  git add -- "$f"
done
STAGED="$( git diff --cached --name-only | LC_ALL=C sort -u )"
if [ -z "$STAGED" ]; then
  ok "os 4 materiais sairam byte-identicos — NADA a fazer"
else
  printf '%s\n' "$STAGED" | sed 's/^/    staged: /'
  EXTRA="$( printf '%s\n' "$STAGED" \
            | grep -v -x -F -e "$PATCH" -e "$SENTINEL" -e "$PROPOSED" -e "$BASE_SHA_FILE" \
            || printf '' )"
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  [ -z "$EXTRA" ] || die "index carrega path(s) fora dos 4 materiais:
$( printf '  %s\n' $EXTRA )
  Rode  git reset  e comece de novo."
  git commit -q -m "chore(PLAN-169 s334-adrgate): patch derivado da sombra e baseado em $HEAD_SHA (finalize-adrgate.sh)" \
    || die "o commit falhou — o staging esta intacto; chame o CEO"
  ok "commit criado: $( git rev-parse --short HEAD )"
fi
fi

step "PRONTO"
cat <<EOF

  O pacote adrgate esta baseado em  $( git rev-parse HEAD )  e o patch aplica limpo.
    patch  : $PATCH
    sha256 : $NEW_PATCH_SHA
    paths  : $( printf '%s\n' "$PATCH_PATHS" | wc -l | tr -d ' ' )

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$SIGN_SCRIPT

EOF
