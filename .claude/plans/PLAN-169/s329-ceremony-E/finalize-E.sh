#!/usr/bin/env bash
# finalize-E.sh — DERIVA o E.patch da arvore-sombra e o baseia no HEAD vivo.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao;
# nao ha gerador para o passo de derivacao (o generate-ceremony.sh assume o
# layout architect/round-N/approved.md, que esta cerimonia nao usa).
#
# POR QUE ELE EXISTE, E POR QUE ELE NAO E UM CLONE DO finalize-B.sh.
# O pacote B ja nascia com um `B.patch` no disco e este passo so o RE-BASEAVA.
# O pacote E nasce numa arvore-sombra com um diff NAO-COMMITADO: o patch ainda
# nao existe. Entao aqui ele e DERIVADO — e derivado contra o HEAD VIVO, porque
# o `finalize_patch.py` RECUSA uma sombra cuja base nao seja o HEAD vivo e o
# SIGN exige `Patch-base` ancestral do HEAD com ZERO drift nos paths tocados.
#
# COMO A RE-BASE E FEITA, e por que NAO por `git apply --3way`.
# O `DESIGN-E.md` da sombra JA EXISTE no HEAD vivo (foi commitado num snapshot
# intermediario) com conteudo diferente. Um patch de `new file mode` aplicado
# com `--3way` sobre uma arvore onde o arquivo existe cai em conflito
# "both added" — o `--3way` resolveria o caso errado ou pararia. A re-base aqui
# e por CONTEUDO: uma arvore-sombra limpa em HEAD recebe os arquivos da sombra
# de trabalho, path a path, e o patch e o diff DESSA arvore contra o HEAD.
#
# O GUARD QUE FECHA A LICAO DA S329 (pacote D abortou duas vezes por isto).
# Copiar por conteudo REVERTERIA qualquer edicao que o HEAD tenha recebido nos
# mesmos paths depois que a sombra foi criada. Por isso, para todo path que
# existe TANTO na base da sombra QUANTO no HEAD vivo, os dois blobs tem de ser
# byte-identicos — se divergiram, alguem editou o destino e a cura e re-derivar
# a sombra POR ITEM, nunca deixar o patch reverter o trabalho do outro.
#
# O QUE ELE FAZ, em ordem:
#   0. pre-condicoes (materiais, gerador, sombra, HEAD em main);
#   1. recusa se o sentinel JA estiver assinado (re-finalizar invalida o .asc);
#   2. le o conjunto EXPECTED de paths do EXPECTED-BASELINE.txt (fonte unica) e
#      recusa se a sombra mexeu em qualquer path FORA dele;
#   3. guard de drift base-da-sombra vs HEAD vivo (o paragrafo acima);
#   4. arvore-sombra em HEAD (git worktree add --detach) + copia por conteudo;
#   5. bateria CURTA na arvore-sombra (o e2e de ~9 min e o V-block do LAND);
#   6. finalize_patch.py: patch + sha256 + Scope DERIVADO + Patch-base;
#   7. BASE-SHA.txt, `git apply --check` na arvore viva;
#   8. stageia EXATAMENTE os 4 arquivos regenerados e commita com `-m`
#      (nenhum editor abre em momento nenhum). Sem diferenca => NADA a fazer.
#
# Uso:  bash .claude/plans/PLAN-169/s329-ceremony-E/finalize-E.sh
#       bash .../finalize-E.sh --no-commit  (gera tudo, NAO stageia nada)
#       bash .../finalize-E.sh --with-e2e   (roda o e2e de ~11 min na sombra e
#                                            o compara com a base DECLARADA)
#       CEO_E_SHADOW=/caminho/da/sombra bash .../finalize-E.sh
set -euo pipefail

# --- argumentos -----------------------------------------------------------
# `--no-commit` existe para quem monta o pacote com OUTRO trabalho em voo na
# mesma arvore: ele gera patch/Scope/BASE-SHA e NAO toca no index. Um `git add`
# aqui arrastaria (ou confundiria) o staging de quem estiver trabalhando ao
# lado. O fluxo do Owner na manha usa a forma SEM flag, que commita.
#
# `--with-e2e` roda o e2e de ~11 min NA ARVORE-SOMBRA e o compara com o numero
# DECLARADO. Ele NAO reescreve a base declarada — um instrumento que ajusta a
# propria expectativa nao mede nada. Ele ABORTA imprimindo o valor observado,
# para que a atualizacao seja uma decisao consciente, com a medicao nova
# registrada num rail-round. Existe para quem monta o pacote conferir o gate
# CARO antes da manha do Owner, em vez de descobrir a divergencia no V3.
NO_COMMIT=0
WITH_E2E=0
for arg in "$@"; do
  case "$arg" in
    --no-commit) NO_COMMIT=1 ;;
    --with-e2e)  WITH_E2E=1 ;;
    *)
      printf '\n\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$arg" >&2
      printf '  Formas validas:\n' >&2
      printf '    bash %s\n' "$0" >&2
      printf '    bash %s --no-commit\n' "$0" >&2
      printf '    bash %s --with-e2e     (roda o e2e de ~11 min na sombra)\n' "$0" >&2
      exit 1 ;;
  esac
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes do pacote (o UNICO bloco que muda entre waves) -------------
PLAN_DIR=".claude/plans/PLAN-169"
CEREMONY_DIR="$PLAN_DIR/s329-ceremony-E"
SENTINEL="$PLAN_DIR/wave-s329-E-approved.md"
PATCH="$CEREMONY_DIR/E.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la); copia-lo
# para ca criaria um segundo original divergente.
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S329-E-SIGN.sh"
UPGRADE="scripts/upgrade.sh"
E2E_TEST="scripts/tests/test-upgrade-lifecycle-hooks-derived.sh"
UNIT_TEST=".claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py"
YML=".github/workflows/smoke-install.yml"
TEMPLATE="templates/settings/settings.base.json"
TEMPLATE_USER="templates/settings/settings.user.json"
UPGRADE_FN="_merge_lifecycle_hooks_into_settings"
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
# `CEO_E_SHADOW` tem precedencia. Sem ela, a busca e sob o scratchpad DESTE
# repositorio (slug = caminho absoluto com `/` -> `-`, o mesmo que o harness
# usa): pegar `*/*/scratchpad` cru cairia no scratchpad de OUTRO projeto.
#
# A pergunta "isto e um repositorio git?" e feita AO GIT, nunca por
# `[ -d "$x/.git" ]`: num `git worktree` o `.git` e um ARQUIVO com um ponteiro
# `gitdir:`, e o teste de diretorio rejeitaria uma sombra perfeitamente valida
# (medido — foi assim que a primeira execucao deste script recusou uma
# arvore-sombra criada com `git worktree add`).
_is_git_tree() { git -C "$1" rev-parse --git-dir >/dev/null 2>&1; }

SHADOW="${CEO_E_SHADOW:-}"
if [ -z "$SHADOW" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  _slug="$( printf '%s' "$ROOT" | tr '/' '-' )"
  for _cand in "$_sp_real/claude-501/$_slug"/*/scratchpad/shadow-E; do
    [ -d "$_cand" ] || continue
    _is_git_tree "$_cand" || continue
    SHADOW="$_cand"
    break
  done
fi
[ -n "$SHADOW" ] || die "arvore-sombra do pacote E nao encontrada.
  Procurei por  <scratchpad deste repo>/*/scratchpad/shadow-E  e nao achei um
  repositorio git. Passe o caminho explicitamente:
    CEO_E_SHADOW=/caminho/da/sombra bash $ROOT/$CEREMONY_DIR/finalize-E.sh"
[ -d "$SHADOW" ] || die "CEO_E_SHADOW nao existe: $SHADOW"
_is_git_tree "$SHADOW" || die "CEO_E_SHADOW nao e um repositorio git: $SHADOW"
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
# untracked numa unica entrada com barra no fim
# (`?? .claude/plans/PLAN-169/s329-ceremony-E/`), e a comparacao contra o
# conjunto EXPECTED — que lista ARQUIVOS — abortaria dizendo que a sombra mexeu
# num path fora do escopo. Medido: uma sombra recem-criada reproduz isso; a
# sombra de trabalho nao, porque la os arquivos novos ja estao staged. Um gate
# que so falha em sombra nova e um gate que falha na hora errada.
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
WT="$( mktemp -d "${TMPDIR:-/tmp}/s329E-wt.XXXXXX" )/wt"
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
# A bateria LONGA (o e2e de ~9 min, os gates de corpus) e o V-block do LAND;
# repeti-la aqui dobraria o tempo da manha sem acrescentar informacao. O que
# roda aqui e o que responde "o conteudo copiado ainda e valido?".

# 4a — sintaxe dos dois scripts shell.
for f in "$UPGRADE" "$E2E_TEST"; do
  [ -f "$WT/$f" ] || die "4a: $f ausente na arvore-sombra"
  ( cd "$WT" && bash -n "$f" ) || die "4a: 'bash -n' reprovou em $f"
done
ok "4a: bash -n verde nos 2 scripts"

if command -v shellcheck >/dev/null 2>&1; then
  for f in "$UPGRADE" "$E2E_TEST"; do
    ( cd "$WT" && shellcheck -S warning "$f" ) || die "4b: shellcheck reprovou em $f"
  done
  ok "4b: shellcheck -S warning verde nos 2 scripts"
else
  warn "4b: shellcheck AUSENTE nesta maquina — o LAND e o CI executam"
fi

# 4c — o teste de unidade compila e RODA, contra a contagem DECLARADA.
( cd "$WT" && PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$UNIT_TEST" ) \
  || die "4c: py_compile reprovou em $UNIT_TEST"
UNIT_LOG="$WT.unit.log"
UNIT_RC=0
( cd "$WT" && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest "$UNIT_TEST" -q -p no:cacheprovider ) \
  > "$UNIT_LOG" 2>&1 || UNIT_RC=$?
[ "$UNIT_RC" -eq 0 ] || { tail -25 "$UNIT_LOG" | sed 's/^/      /' >&2
                          die "4c: a suite de unidade reprovou (rc=$UNIT_RC) — log em $UNIT_LOG"; }
# "N deselected" NAO e "N passed" (licao S325). A linha do `pytest -q` COMECA
# pelo numero ("33 passed in 1.08s"), entao o padrao aceita inicio de linha OU
# um nao-digito antes; o numero e sempre o imediatamente antes de " passed".
# O `|| true` faz a mensagem NOMEADA abaixo disparar. Sem ele, uma saida de
# pytest sem "N passed" mataria o script mudo na propria atribuicao.
_unit_obs="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$UNIT_LOG" || true; } \
              | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_unit_obs" ] || die "4c: nao consegui ler 'N passed' — log em $UNIT_LOG"
_unit_exp="$(_expect EXPECTED_UNIT_PYTEST_PASSED)"
[ "$_unit_obs" = "$_unit_exp" ] \
  || die "4c: $_unit_obs teste(s) de unidade passaram, esperado $_unit_exp.
  Menos e regressao; mais significa que a suite cresceu — atualize
  $BASELINE_ENV conscientemente. Log: $UNIT_LOG"
ok "4c: suite de unidade $_unit_obs/$_unit_exp"

# 4d — o YAML pos-copia continua parseavel, e o teste continua VISIVEL nele.
if python3 -c 'import yaml' >/dev/null 2>&1; then
  ( cd "$WT" && python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$YML" ) \
    || die "4d: yaml.safe_load reprovou em $YML"
  ok "4d: yaml.safe_load OK"
else
  warn "4d: PyYAML ausente — o actionlint abaixo e o CI tambem cobrem"
fi
if command -v actionlint >/dev/null 2>&1; then
  AL_LOG="$WT.actionlint.log"
  ( cd "$WT" && actionlint "$YML" ) > "$AL_LOG" 2>&1 \
    || { sed 's/^/      /' "$AL_LOG" >&2; die "4e: actionlint reprovou em $YML"; }
  ok "4e: actionlint verde"
else
  warn "4e: actionlint AUSENTE — o CI executa"
fi
_refs_obs="$( grep -cF -- "$( basename "$E2E_TEST" )" "$WT/$YML" || true )"
_refs_exp="$(_expect EXPECTED_YML_E2E_REFS)"
[ "$_refs_obs" = "$_refs_exp" ] \
  || die "4f: $( basename "$E2E_TEST" ) aparece $_refs_obs vez(es) em $YML, esperado $_refs_exp.
  Sao as DUAS listas de paths (push e pull_request) mais o step que EXECUTA.
  Faltando um filtro o job nao dispara na mudanca do teste; faltando o step o
  teste nao roda — 'unwired = no test', a regra escrita no proprio workflow."
ok "4f: o workflow referencia o e2e $_refs_obs vez(es)"

# 4g — o invariante anti-rot, medido no ARQUIVO que sera landado.
# A extracao e por ANCORA de coluna 0, sem regex montado por string: o mesmo
# idioma que o teste de unidade usa (e que `test-upgrade-historical-adopter.sh`
# ja usava para `_up_tmpbase`). `index($0, start) == 1` exige que a linha
# COMECE pela assinatura; `$0 == "}"` fecha na chave de coluna 0.
#
# O `|| true` no grep NAO e decoracao. `grep -o` sai 1 quando nao casa NADA, e
# ZERO literais e justamente a resposta VERDE deste gate: sob `pipefail` o
# pipeline inteiro sairia 1, a atribuicao falharia e o `set -e` mataria o
# script SEM MENSAGEM — o gate morreria exatamente no caso que ele existe para
# aprovar. Medido: foi assim que a primeira execucao real deste script saiu
# rc=1 mudo depois do 4f.
_lit_obs="$( awk -v start="${UPGRADE_FN}() {" \
                 'index($0, start) == 1 { f = 1 }
                  f { print }
                  f && $0 == "}" { exit }' "$WT/$UPGRADE" \
             | { grep -oE '[A-Za-z0-9_]+\.py' || true; } \
             | LC_ALL=C sort -u | wc -l | tr -d ' ' )"
_lit_exp="$(_expect EXPECTED_UPGRADE_FN_HOOK_LITERALS)"
[ "$_lit_obs" = "$_lit_exp" ] \
  || die "4g: a funcao $UPGRADE_FN cita $_lit_obs nome(s) de arquivo .py, esperado $_lit_exp.
  Um roster literal dentro do upgrader e EXATAMENTE a classe que esta wave
  fecha. Se um nome voltou, a cura regrediu."
ok "4g: $UPGRADE_FN cita $_lit_obs nome(s) .py (esperado $_lit_exp)"

# 4h — o roster que a derivacao entrega. O template e a FONTE agora; se ele
# encolheu, o merge derivado entrega menos, e isso e mudanca de produto — nao
# detalhe. Barato aqui, e evita descobrir de manha no V6 do LAND.
if command -v jq >/dev/null 2>&1; then
  _reg_obs="$( jq '[.hooks | to_entries[] | .value[]] | length' "$WT/$TEMPLATE" )"
  _reg_exp="$(_expect EXPECTED_TEMPLATE_REGISTRATIONS)"
  [ "$_reg_obs" = "$_reg_exp" ] \
    || die "4h: $TEMPLATE enumera $_reg_obs registro(s), esperado $_reg_exp.
  Atualize $BASELINE_ENV conscientemente, com a medicao nova num rail-round."
  ok "4h: $TEMPLATE enumera $_reg_obs registro(s) (esperado $_reg_exp)"
  # 4h-bis — o template USER, pela mesma razao (rail round 6, P1): a cerimonia
  # seleciona o template, entao um adopter `--ceremony user` recebe ESTE
  # roster. Um template user que encolha, ou que ganhe por engano um dos 10
  # hooks que ele omite de proposito, chegaria ao adopter em silencio.
  [ -r "$WT/$TEMPLATE_USER" ] || die "4h-bis: $TEMPLATE_USER ausente na arvore-sombra — a selecao por cerimonia nao tem de onde derivar"
  _regu_obs="$( jq '[.hooks | to_entries[] | .value[]] | length' "$WT/$TEMPLATE_USER" )"
  _regu_exp="$(_expect EXPECTED_TEMPLATE_REGISTRATIONS_USER)"
  [ "$_regu_obs" = "$_regu_exp" ] \
    || die "4h-bis: $TEMPLATE_USER enumera $_regu_obs registro(s), esperado $_regu_exp.
  Atualize $BASELINE_ENV conscientemente, com a medicao nova num rail-round."
  ok "4h-bis: $TEMPLATE_USER enumera $_regu_obs registro(s) (esperado $_regu_exp)"
else
  warn "4h: jq AUSENTE — o G-PRE do SIGN e do LAND aborta por isso"
fi

# 4i — o gate CARO, so sob --with-e2e. Mesma leitura que o V3 do LAND faz, na
# MESMA forma de linha (`RESULT: <N> passed, <M> failed`): se este passa e o V3
# reprova, a diferenca esta na arvore, nao no parser.
#
# Ele roda na ARVORE-SOMBRA ($WT), e a escolha e load-bearing: o $WT esta em
# HEAD (PRE-cura) com os 5 arquivos copiados por cima — exatamente a condicao
# do V3, onde o patch vive na arvore de trabalho e o HEAD ainda e a ancora. E
# nessa condicao que E.3/E.9 rendem as 4 asercoes; num checkout onde a cura ja
# esta COMMITADA eles viram SKIP e o total cai 2. Ver o bloco V3 do
# EXPECTED-BASELINE.txt.
if [ "$WITH_E2E" = "1" ]; then
  printf '  4i: rodando o e2e na arvore-sombra (~11 min)...\n'
  E2E_LOG="$WT.e2e.log"
  E2E_RC=0
  ( cd "$WT" && bash "$E2E_TEST" ) > "$E2E_LOG" 2>&1 || E2E_RC=$?
  _e2e_exp_rc="$(_expect EXPECTED_E2E_RC)"
  [ "$E2E_RC" = "$_e2e_exp_rc" ] || { tail -12 "$E2E_LOG" | sed 's/^/      /' >&2
    die "4i: o e2e saiu rc=$E2E_RC, esperado $_e2e_exp_rc — log em $E2E_LOG"; }
  _res_line="$( { grep -m1 '^RESULT:' "$E2E_LOG" || true; } )"
  [ -n "$_res_line" ] || die "4i: o e2e nao imprimiu a linha 'RESULT:' — log em $E2E_LOG"
  _e2e_p="$( printf '%s' "$_res_line" | sed -n 's/^RESULT: \([0-9][0-9]*\) passed.*/\1/p' )"
  _e2e_f="$( printf '%s' "$_res_line" | sed -n 's/^RESULT: [0-9][0-9]* passed, \([0-9][0-9]*\) failed.*/\1/p' )"
  [ -n "$_e2e_p" ] && [ -n "$_e2e_f" ] \
    || die "4i: nao consegui parsear '$_res_line' — log em $E2E_LOG"
  [ "$_e2e_f" = "$(_expect EXPECTED_E2E_FAILED)" ] \
    || die "4i: $_e2e_f asercao(oes) do e2e falharam — log em $E2E_LOG"
  [ "$_e2e_p" = "$(_expect EXPECTED_E2E_PASSED)" ] \
    || die "4i: o e2e passou $_e2e_p asercao(oes), a base declara $(_expect EXPECTED_E2E_PASSED).
  NAO vou reescrever a base sozinho — um instrumento que ajusta a propria
  expectativa nao mede nada. Atualize EXPECTED_E2E_PASSED em
  $BASELINE_ENV para $_e2e_p CONSCIENTEMENTE, com a medicao nova num
  rail-round, e rode este script de novo. Log: $E2E_LOG"
  ok "4i: e2e $_e2e_p passed / $_e2e_f failed (bate a base declarada)"
else
  printf '  \033[33mNOTA\033[0m 4i: e2e NAO executado (padrao). O V3 do LAND o roda.\n'
  printf '        Para conferir a base declarada antes da manha do Owner:\n'
  printf '          bash %s --with-e2e\n' "$0"
fi

# ---------------------------------------------------------------------------
step "5 — patch, Scope, Patch-base e Patch-sha256"
# ---------------------------------------------------------------------------
# O HEAD pode ter ANDADO enquanto a bateria rodava — com `--with-e2e` a janela
# e de ~11 min, e nesta noite varios agentes commitam no mesmo checkout. O
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
  no mesmo checkout: combine uma janela antes de re-rodar com --with-e2e, que e
  o modo de ~11 min e o mais exposto a esta corrida."
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
  git commit -q -m "chore(PLAN-169 s329-E): patch derivado da sombra e baseado em $HEAD_SHA (finalize-E.sh)" \
    || die "o commit falhou — o staging esta intacto; chame o CEO"
  ok "commit criado: $( git rev-parse --short HEAD )"
fi
fi

step "PRONTO"
cat <<EOF

  O pacote E esta baseado em  $( git rev-parse HEAD )  e o patch aplica limpo.
    patch  : $PATCH
    sha256 : $NEW_PATCH_SHA
    paths  : $( printf '%s\n' "$PATCH_PATHS" | wc -l | tr -d ' ' )

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$SIGN_SCRIPT

EOF
