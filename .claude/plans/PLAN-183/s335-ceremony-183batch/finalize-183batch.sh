#!/usr/bin/env bash
# finalize-183batch.sh — DERIVA o W183BATCH.patch da arvore-sombra e o baseia no HEAD vivo.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao;
# nao ha gerador para o passo de derivacao (o generate-ceremony.sh assume o
# layout architect/round-N/approved.md, que esta cerimonia nao usa).
#
# O QUE ESTA WAVE ENTREGA (PLAN-183 wave-183batch — runbook ratificado
# 2026-08-31, «Batch menor + começar W1»): (1) `.claude/settings.json`
# regenerado pelo skill-budget-generator (--jq-fragment idempotente; +4
# skills 0-dispatch demoted a name-only: cpp-testing, frontend-slides,
# prisma-patterns, ui-demo — KERNEL: settings.json esta em _KERNEL_PATHS,
# o LAND arma o override); (2) header "INERT AS SHIPPED" no
# validate.yml.template (molde benchmarks.yml.template:3-7, comentario
# puro — o frozen-subset de 11 steps + pins fica intacto); (3) AC-5 do
# PLAN-183 fechado por REGISTRO (a metade "canonica" que a nota ◐ dizia
# faltar JA existe: smoke-install.yml:485 invoca o sh inteiro e a perna
# de ativacao vive em smoke-install.sh:180). 3 paths: 1 canonico
# (settings.json) e 2 livres (template, plano).
#
# ESTE SCRIPT E UM CLONE GATE-A-GATE DO finalize-adrgate.sh (que landou o
# cfab980 REAL na manha da S335), e isso e deliberado: os guards dele foram
# pagos com o pacote D abortando duas vezes na S329 e curados por 8 rodadas
# de rail de materiais na S334 (drift-guard, `|| true` nos greps cujo zero e
# resposta, HEAD-andou, backup/restore transacional dos 4 materiais com
# pre-estado EXATO de worktree+index, flags de trap nunca herdadas do
# ambiente). Eles estao aqui byte-a-byte. O que muda e o bloco de constantes
# e o passo 4 (a bateria do adrgate validava cadeia de ADRs/ledger/wire de
# CI; esta valida o registry triplo CODE↔SPEC↔golden, as suites do US7/US8,
# a idempotencia do golden, o flip do plano e a sonda comportamental dos
# modulos patchados — um V-block copiado testaria a coisa errada e seria
# verde vazio).
#
# COMO A RE-BASE E FEITA, e por que NAO por `git apply --3way`.
# A re-base e por CONTEUDO: uma arvore-sombra limpa em HEAD recebe os
# arquivos da sombra de trabalho, path a path, e o patch e o diff DESSA arvore
# contra o HEAD. Um patch de `new file mode` aplicado com `--3way` sobre uma
# arvore onde o arquivo ja existe cai em conflito "both added" (medido na
# cerimonia F).
#
# O QUE ELE FAZ, em ordem:
#   0. pre-condicoes (materiais, gerador, sombra, HEAD em main);
#   1. recusa se o sentinel JA estiver assinado (re-finalizar invalida o .asc);
#   2. le o conjunto EXPECTED de paths do EXPECTED-BASELINE.txt (fonte unica) e
#      recusa se a sombra mexeu em qualquer path FORA dele;
#   3. guard de drift base-da-sombra vs HEAD vivo;
#   4. arvore-sombra em HEAD (git worktree add --detach) + copia por conteudo;
#   5. bateria CURTA na arvore-sombra (os gates CAROS sao o V-block do LAND);
#   6. finalize_patch.py: patch + sha256 + Scope DERIVADO + Patch-base;
#   7. BASE-SHA.txt, `git apply --check` na arvore viva;
#   8. stageia EXATAMENTE os 4 arquivos regenerados e commita com `-m`
#      (nenhum editor abre em momento nenhum). Sem diferenca => NADA a fazer.
#
# Uso:  bash .claude/plans/PLAN-183/s335-ceremony-183batch/finalize-183batch.sh
#       bash .../finalize-183batch.sh --no-commit  (gera tudo, NAO stageia nada)
#       bash .../finalize-183batch.sh --with-slow  (roda tambem os gates de
#                                                   corpus lentos: verify-counts
#                                                   e claims)
#       CEO_183BATCH_SHADOW=/caminho/da/sombra bash .../finalize-183batch.sh
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
PLAN_DIR=".claude/plans/PLAN-183"
CEREMONY_DIR="$PLAN_DIR/s335-ceremony-183batch"
SENTINEL="$PLAN_DIR/wave-183batch-approved.md"
PATCH="$CEREMONY_DIR/W183BATCH.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 W5 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S335-183BATCH-SIGN.sh"
SETTINGS=".claude/settings.json"
TEMPLATE="templates/.github/workflows/validate.yml.template"
PLAN_FILE=".claude/plans/PLAN-183-adopter-fitness.md"
BUDGET_GEN=".claude/scripts/skill-budget-generator.py"
TEMPLATE_BASE="templates/settings/settings.base.json"
UNDEMOTE_MAT="$CEREMONY_DIR/veto-undemote-s335.jq"
UNIT_TESTS=".claude/scripts/tests/test_validate_template_frozen_subset.py \
.claude/scripts/tests/test_veto_skill_map.py"
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
_fin_ok=0        # rail r2 P2-e: nunca herdar do ambiente
_fin_captured=0  # rail r7: mesma classe — a flag do trap tambem nao se herda
_cleanup() {
  # rail-materials r1 P2-b: um abort DEPOIS do gerador restaura os tres
  # materiais vivos ao estado pre-gerador (backup feito no passo 6).
  if [ "${_fin_captured:-0}" = "1" ] && [ "${_fin_ok:-0}" != "1" ]; then
    # rail r5: o aviso de recovery TEM de chegar ao operador — nada de
    # engolir o stderr do restore.
    _fin_restore || printf ''
  fi
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
# `CEO_183BATCH_SHADOW` tem precedencia. Sem ela, a busca e sob o scratchpad
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

SHADOW="${CEO_183BATCH_SHADOW:-}"
if [ -z "$SHADOW" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  _slug="$( printf '%s' "$ROOT" | tr '/' '-' )"
  for _cand in "$_sp_real/claude-501/$_slug"/*/scratchpad/shadow-183batch; do
    [ -d "$_cand" ] || continue
    _is_git_tree "$_cand" || continue
    SHADOW="$_cand"
    break
  done
fi
[ -n "$SHADOW" ] || die "arvore-sombra do pacote 183batch nao encontrada.
  Procurei por  <scratchpad deste repo>/*/scratchpad/shadow-183batch  e nao
  achei um repositorio git. Passe o caminho explicitamente:
    CEO_183BATCH_SHADOW=/caminho/da/sombra bash $ROOT/$CEREMONY_DIR/finalize-183batch.sh"
[ -d "$SHADOW" ] || die "CEO_183BATCH_SHADOW nao existe: $SHADOW"
_is_git_tree "$SHADOW" || die "CEO_183BATCH_SHADOW nao e um repositorio git: $SHADOW"
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
WT="$( mktemp -d "${TMPDIR:-/tmp}/s335w183b-wt.XXXXXX" )/wt"
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

# 4a — o gate central da wave: os DOIS settings do patch sao EXATAMENTE
# derivaveis dos materiais versionados. O gerador e INCREMENTAL, entao os
# fragments EXATOS da mudanca sao MATERIAIS: skill-frag-s335.jq (demotions
# novas, so no settings.json) e veto-undemote-s335.jq (A4, rail 183-r4: as
# 7 chaves VETO-bearing saem dos DOIS alvos). Cadeias:
#   settings.json : base | skill-frag | veto-undemote  == patch (byte a byte)
#   settings.base : base |              veto-undemote  == patch (byte a byte)
FRAG_MAT="$CEREMONY_DIR/skill-frag-s335.jq"
[ -f "$FRAG_MAT" ] || die "4a: fragment versionado ausente: $FRAG_MAT"
[ -f "$UNDEMOTE_MAT" ] || die "4a: undemote versionado ausente: $UNDEMOTE_MAT"
_b1="$WT.settings-base.json"; _d1="$WT.settings-derived.json"
git -C "$WT" show HEAD:.claude/settings.json > "$_b1" || die "4a: base do settings ilegivel"
jq -f "$FRAG_MAT" "$_b1" | jq -f "$UNDEMOTE_MAT" > "$_d1" || die "4a: cadeia jq falhou (settings)"
cmp -s "$_d1" "$WT/$SETTINGS" \
  || die "4a: base|frag|undemote NAO reproduz o settings do patch byte a byte"
_b2="$WT.base-tpl.json"; _d2="$WT.base-tpl-derived.json"
git -C "$WT" show HEAD:templates/settings/settings.base.json > "$_b2" || die "4a: base do template ilegivel"
jq -f "$UNDEMOTE_MAT" "$_b2" > "$_d2" || die "4a: undemote falhou (template)"
cmp -s "$_d2" "$WT/$TEMPLATE_BASE" \
  || die "4a: base|undemote NAO reproduz o settings.base do patch byte a byte"
ok "4a: os DOIS settings == derivacao dos materiais versionados (byte a byte)"

# 4b — o settings parseia e a contagem de overrides e a DECLARADA.
jq -e . "$WT/$SETTINGS" >/dev/null || die "4b: settings.json nao parseia"
_ov_obs="$( jq '.skillOverrides|length' "$WT/$SETTINGS" )"
_ov_exp="$(_expect EXPECTED_SETTINGS_OVERRIDES)"
[ "$_ov_obs" = "$_ov_exp" ] \
  || die "4b: $_ov_obs override(s) no settings, esperado $_ov_exp"
ok "4b: settings parseia; $_ov_obs override(s) (esperado $_ov_exp)"

# 4c — a suite declarada: o frozen-subset do template (11 steps + pins).
UNIT_LOG="$WT.unit.log"
UNIT_RC=0
# shellcheck disable=SC2086  # lista controlada
( cd "$WT" && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest $UNIT_TESTS -q -p no:cacheprovider ) \
  > "$UNIT_LOG" 2>&1 || UNIT_RC=$?
[ "$UNIT_RC" -eq 0 ] || { tail -25 "$UNIT_LOG" | sed 's/^/      /' >&2
                          die "4c: frozen-subset reprovou (rc=$UNIT_RC) — log em $UNIT_LOG"; }
_unit_obs="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$UNIT_LOG" || true; } \
              | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_unit_obs" ] || die "4c: nao consegui ler 'N passed' — log em $UNIT_LOG"
[ "$_unit_obs" = "$(_expect EXPECTED_UNIT_PYTEST_PASSED)" ] \
  || die "4c: $_unit_obs passaram, esperado $(_expect EXPECTED_UNIT_PYTEST_PASSED)"
_skip_obs="$( { grep -oE '[0-9]+ skipped' "$UNIT_LOG" || true; } | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_skip_obs" ] || _skip_obs=0
[ "$_skip_obs" = "$(_expect EXPECTED_UNIT_PYTEST_SKIPPED)" ] \
  || die "4c: $_skip_obs pulados, esperado $(_expect EXPECTED_UNIT_PYTEST_SKIPPED)"
ok "4c: frozen-subset $_unit_obs/$(_expect EXPECTED_UNIT_PYTEST_PASSED) (skips $_skip_obs)"

# 4d — o header INERT esta no template, exatamente uma vez.
_in_obs="$( { grep -c 'INERT AS SHIPPED' "$WT/$TEMPLATE" || true; } )"
[ "$_in_obs" = "$(_expect EXPECTED_INERT_REFS)" ] \
  || die "4d: 'INERT AS SHIPPED' aparece $_in_obs vez(es) no template, esperado $(_expect EXPECTED_INERT_REFS)"
ok "4d: header INERT presente ($_in_obs)"

# 4e — nao-vacuidade NOMEADA dos dois materiais, na MESMA prova:
#   frag     : prisma-patterns  ABSENT no base  -> name-only no derivado;
#   undemote : kill-switches    PRESENTE no base -> ABSENT no derivado
#              (e ausente tambem do template derivado).
_fk_base="$( jq -r '.skillOverrides["prisma-patterns"] // "ABSENT"' "$_b1" )"
_fk_der="$( jq -r '.skillOverrides["prisma-patterns"] // "ABSENT"' "$_d1" )"
{ [ "$_fk_base" = "ABSENT" ] && [ "$_fk_der" = "name-only" ]; } \
  || die "4e: frag nao escreve (prisma: base=$_fk_base derivado=$_fk_der)"
_ks_base="$( jq -r '.skillOverrides["kill-switches"] // "ABSENT"' "$_b1" )"
_ks_der="$( jq -r '.skillOverrides["kill-switches"] // "ABSENT"' "$_d1" )"
{ [ "$_ks_base" = "name-only" ] && [ "$_ks_der" = "ABSENT" ]; } \
  || die "4e: undemote nao APAGA (kill-switches: base=$_ks_base derivado=$_ks_der)"
_ks_tpl="$( jq -r '.skillOverrides["kill-switches"] // "ABSENT"' "$_d2" )"
[ "$_ks_tpl" = "ABSENT" ] || die "4e: undemote nao apagou no TEMPLATE (kill-switches=$_ks_tpl)"
ok "4e: frag ESCREVE e undemote APAGA, nomeados nos dois alvos"

# 4f — o AC-5 NAO flipa (rail 183-r1: a execucao real segue aberta); o que
# viaja e o REGISTRO. Um [x] aqui seria registro falso de governanca.
_a5x="$( { grep -c -- '- \[x\] AC-5' "$WT/$PLAN_FILE" || true; } )"
[ "$_a5x" = "$(_expect EXPECTED_AC5_CHECKED)" ] \
  || die "4f: '- [x] AC-5' aparece $_a5x vez(es), esperado $(_expect EXPECTED_AC5_CHECKED) — o flip e PROIBIDO nesta wave"
_a5n="$( { grep -c 'REGISTRO S335' "$WT/$PLAN_FILE" || true; } )"
[ "$_a5n" = "$(_expect EXPECTED_AC5_NOTE_REFS)" ] \
  || die "4f: a nota 'REGISTRO S335' aparece $_a5n vez(es), esperado $(_expect EXPECTED_AC5_NOTE_REFS)"
ok "4f: AC-5 segue aberto com o REGISTRO no lugar (flip barrado por desenho)"

# 4g — o gate estatico de harness-config sobre o settings POS-PATCH.
HC_LOG="$WT.harness-config.log"
HC_RC=0
( cd "$WT" && python3 .claude/hooks/check_harness_config.py ) > "$HC_LOG" 2>&1 || HC_RC=$?
[ "$HC_RC" = "0" ] || { tail -10 "$HC_LOG" | sed 's/^/      /' >&2
  die "4g: check_harness_config reprovou (rc=$HC_RC) — log em $HC_LOG"; }
ok "4g: harness-config gate verde sobre o settings pos-patch"

# 4k — os gates de CORPUS, so sob --with-slow (rail r1 P2-7: a 1a geracao
# deste clone DROPOU este bloco na substituicao da bateria — WITH_SLOW era
# parseado e nunca lido, e o modo anunciado virava no-op silencioso).
# Mesma leitura que o V8 do LAND faz: se este passa e o V8 reprova, a
# diferenca esta na arvore.
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

# rail-materials r1 P2-b: o gerador sobrescreve patch, sentinel e
# PROPOSED em sequencia; um abort dos checks seguintes NAO pode
# deixar os tres pela metade. Backup antes, restore no abort.
_fin_bak="$(mktemp -d)"
: > "$_fin_bak/.absent-before"   # rail r3 P2-i: ausencia tambem e estado
for _bf in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE"; do
  if [ -f "$_bf" ]; then
    cp -p "$_bf" "$_fin_bak/$(basename "$_bf")"
  else
    printf '%s\n' "$_bf" >> "$_fin_bak/.absent-before"
  fi
done
# rail r4 (REDESENHO, criterio da r3 disparado): o INDEX tambem e
# pre-estado. Captura o diff staged EXATO dos 4 materiais; o rollback
# zera o staged deles e RE-APLICA este patch — index-only content de
# terceiros sobrevive a qualquer abort byte a byte.
if ! git diff --cached --binary -- "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE" \
       > "$_fin_bak/index-prestate.patch" 2>"$_fin_bak/index-capture.err"; then
  # rail r5: fail-CLOSED — sem captura do pre-estado do index, este script
  # NAO muta os materiais (um rollback sem a captura apagaria staging
  # pre-existente em silencio).
  die "nao consegui capturar o pre-estado do INDEX dos materiais:
$( sed 's/^/    /' "$_fin_bak/index-capture.err" 2>/dev/null )
  Recusando mutar qualquer material. Resolva e re-rode."
fi
_fin_restore() {
  # rail r4 (REDESENHO): restaura o pre-estado EXATO — worktree (bytes ou
  # ausencia) E index (o diff staged capturado) — dos QUATRO materiais.
  # Nao ha mais boolean por caso: o estado capturado E a verdade.
  for _bf in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE"; do
    git reset -q -- "$_bf" >/dev/null 2>&1 || true
    if [ -f "$_fin_bak/$(basename "$_bf")" ]; then
      cp -p "$_fin_bak/$(basename "$_bf")" "$_bf"
    elif grep -qxF "$_bf" "$_fin_bak/.absent-before" 2>/dev/null; then
      rm -f "$_bf" 2>/dev/null || true
    fi
  done
  if [ -s "$_fin_bak/index-prestate.patch" ]; then
    if git apply --cached "$_fin_bak/index-prestate.patch" >/dev/null 2>&1; then
      printf '  finalize: index pre-existente dos materiais RE-APLICADO byte a byte\n' >&2
    else
      printf '  finalize: AVISO — nao consegui re-aplicar o index pre-existente;\n' >&2
      printf '            o patch capturado esta preservado em %s\n' "$_fin_bak/index-prestate.patch" >&2
    fi
  fi
  printf '  finalize: materiais RESTAURADOS ao pre-estado exato (worktree + index)\n' >&2
}
# rail r6: a flag so liga quando captura E funcao existem — o caminho de
# falha-da-captura aborta ANTES daqui e o trap nao chama nada indefinido.
_fin_captured=1
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
  # rail r2 P1-d: no modo --no-commit os materiais mutados SAO o produto —
  # sem isto o EXIT "bem-sucedido" restauraria os 4 e o modo viraria um
  # no-op destrutivo silencioso.
  _fin_ok=1
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
# rail-materials r1 P2-b: o guard de index roda ANTES do add — um abort
# depois do add deixaria os 4 staged, e o remedio antigo (git reset global)
# des-stagearia trabalho de terceiros junto.
_PRE_STAGED="$( git diff --cached --name-only | LC_ALL=C sort -u )"
[ -z "$_PRE_STAGED" ] || die "o index ja carrega path(s) staged de outro trabalho:
$( printf '  %s\n' $_PRE_STAGED )
  Commite ou des-stageie (git reset -- <path>) ANTES do finalize — o commit
  dos materiais nao pode arrastar staging alheio."
for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE"; do
  git add -- "$f"
done
STAGED="$( git diff --cached --name-only | LC_ALL=C sort -u )"
if [ -z "$STAGED" ]; then
  # rail r3 P2-j: este caminho e SUCESSO — sem a flag, o EXIT trataria
  # o "nada a fazer" como abort e imprimiria um RESTAURADOS confuso
  # depois do PRONTO.
  _fin_ok=1
  ok "os 4 materiais sairam byte-identicos — NADA a fazer"
else
  printf '%s\n' "$STAGED" | sed 's/^/    staged: /'
  EXTRA="$( printf '%s\n' "$STAGED" \
            | grep -v -x -F -e "$PATCH" -e "$SENTINEL" -e "$PROPOSED" -e "$BASE_SHA_FILE" \
            || printf '' )"
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  [ -z "$EXTRA" ] || die "index carrega path(s) fora dos 4 materiais:
$( printf '  %s\n' $EXTRA )
  Des-stageie SO esses paths (git reset -- <path>) e re-rode — nunca um
  git reset global (arrastaria staging de terceiros; rail-materials r1)."
  git commit -q -m "chore(PLAN-183 s335-183batch): patch derivado da sombra e baseado em $HEAD_SHA (finalize-183batch.sh)" \
    || die "o commit falhou — o staging esta intacto; chame o CEO"
  _fin_ok=1
  ok "commit criado: $( git rev-parse --short HEAD )"
fi
fi

step "PRONTO"
cat <<EOF

  O pacote 183batch esta baseado em  $( git rev-parse HEAD )  e o patch aplica limpo.
    patch  : $PATCH
    sha256 : $NEW_PATCH_SHA
    paths  : $( printf '%s\n' "$PATCH_PATHS" | wc -l | tr -d ' ' )

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$SIGN_SCRIPT

EOF
