#!/usr/bin/env bash
# finalize-C.sh — DERIVA o C.patch da arvore-sombra e o baseia no HEAD vivo.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao; nao
# ha gerador para o passo de derivacao (o generate-ceremony.sh assume o layout
# architect/round-N/approved.md, que esta cerimonia nao usa).
#
# ESTE SCRIPT E O finalize-E.sh COM UMA DIFERENCA DE FUNDO, e vale dizer qual.
# O pacote E nascia inteiro numa sombra so, entao a lista de paths podia ser
# CONGELADA a mao no EXPECTED-BASELINE.txt. O pacote C e escrito por DOIS
# autores em paralelo na MESMA sombra — a metade de codigo e a metade de
# CI/docs — e uma lista exata escrita antes da segunda metade existir estaria
# errada por construcao. Entao aqui o humano declara a FRONTEIRA
# (REQUIRED_PATCH_PATHS + ALLOWED_EXTRA_PATCH_PATHS) e este script DERIVA o
# conjunto exato, gravando-o no bloco AUTO do EXPECTED-BASELINE.txt. A
# assinatura congela esse conjunto; o G4 do LAND compara contra ele nos dois
# sentidos. A pergunta que o G4 responde continua sendo a certa: nao "o patch
# toca o que o finalize viu?" e sim "o patch ainda toca o que foi ASSINADO?".
#
# COMO A RE-BASE E FEITA, e por que NAO por `git apply --3way`. O `DESIGN-C.md`
# da sombra pode ja existir no HEAD vivo com conteudo diferente; um patch de
# `new file mode` aplicado com `--3way` sobre uma arvore onde o arquivo existe
# cai em conflito "both added". A re-base aqui e por CONTEUDO: uma arvore-sombra
# limpa em HEAD recebe os arquivos da sombra de trabalho, path a path, e o patch
# e o diff DESSA arvore contra o HEAD.
#
# O GUARD QUE FECHA A LICAO DA S329 (o pacote D abortou duas vezes por isto).
# Copiar por conteudo REVERTERIA qualquer edicao que o HEAD tenha recebido nos
# mesmos paths depois que a sombra foi criada. Por isso, para todo path que
# existe TANTO na base da sombra QUANTO no HEAD vivo, os dois blobs tem de ser
# byte-identicos — se divergiram, alguem editou o destino e a cura e re-derivar
# a sombra POR ITEM, nunca deixar o patch reverter o trabalho do outro.
#
# O QUE ELE FAZ, em ordem:
#   0. pre-condicoes (materiais, gerador, sombra, HEAD em main);
#   1. recusa se o sentinel JA estiver assinado (re-finalizar invalida o .asc);
#   2. fronteira: o que a sombra mexeu tem de caber em REQUIRED + ALLOWED, e
#      REQUIRED tem de estar TODO presente;
#   3. guard de drift base-da-sombra vs HEAD vivo (o paragrafo acima);
#   4. arvore-sombra em HEAD, censo PRE, copia por conteudo, censo POS;
#   5. bateria CURTA na arvore-sombra (o e2e de ~7 min e o V-block do LAND);
#   6. finalize_patch.py: patch + sha256 + Scope DERIVADO + Patch-base;
#   7. bloco AUTO do EXPECTED-BASELINE.txt, BASE-SHA.txt, `git apply --check`;
#   8. stageia EXATAMENTE os 5 materiais regenerados e commita com `-m`
#      (nenhum editor abre em momento nenhum). Sem diferenca => NADA a fazer.
#
# Uso:  bash .claude/plans/PLAN-185/s329-ceremony-C/finalize-C.sh
#       bash .../finalize-C.sh --no-commit          (gera tudo, NAO stageia nada)
#       CEO_C_SHADOW=/caminho/da/sombra bash .../finalize-C.sh
set -euo pipefail

# --- argumentos -----------------------------------------------------------
# `--no-commit` existe para quem monta o pacote com OUTRO trabalho em voo na
# mesma arvore: ele gera patch/Scope/BASE-SHA e NAO toca no index. Um `git add`
# aqui arrastaria (ou confundiria) o staging de quem estiver trabalhando ao
# lado. O fluxo do Owner na manha usa a forma SEM flag, que commita.
NO_COMMIT=0
for arg in "$@"; do
  case "$arg" in
    --no-commit) NO_COMMIT=1 ;;
    *)
      printf '\n\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$arg" >&2
      printf '  Formas validas:\n' >&2
      printf '    bash %s\n' "$0" >&2
      printf '    bash %s --no-commit\n' "$0" >&2
      exit 1 ;;
  esac
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes do pacote (o UNICO bloco que muda entre waves) -------------
PLAN_DIR=".claude/plans/PLAN-185"
CEREMONY_DIR="$PLAN_DIR/s329-ceremony-C"
SENTINEL="$PLAN_DIR/wave-s329-C-approved.md"
PATCH="$CEREMONY_DIR/C.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la); copia-lo
# para ca criaria um segundo original divergente.
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S329-C-SIGN.sh"
CENSUS=".claude/scripts/check-installer-write-safety.py"
# O RATCHET do censo. Este script o REGENERA na arvore-sombra e o inclui no
# patch — ver o passo 4f e a secao 5 do EXPECTED-BASELINE.txt.
BASELINE_DATA=".claude/scripts/data/installer-write-safety-baseline.txt"
E2E_TEST="scripts/tests/test-installer-write-safety-e2e.sh"
LIB="scripts/_framework_manifest_set.sh"
INSTALLER="scripts/install.sh"
UPGRADER="scripts/upgrade.sh"
DOCTOR="scripts/doctor.sh"
YML_SMOKE=".github/workflows/smoke-install.yml"
YML_VALIDATE=".github/workflows/validate.yml"
AUTO_BEGIN="# <<<AUTO-DERIVED-BY-FINALIZE-C>>>"
AUTO_END="# <<<END-AUTO-DERIVED-BY-FINALIZE-C>>>"
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
# `CEO_C_SHADOW` tem precedencia. Sem ela, a busca e sob o scratchpad DESTE
# repositorio (slug = caminho absoluto com `/` -> `-`, o mesmo que o harness
# usa): pegar `*/*/scratchpad` cru cairia no scratchpad de OUTRO projeto.
SHADOW="${CEO_C_SHADOW:-}"
if [ -z "$SHADOW" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  _slug="$( printf '%s' "$ROOT" | tr '/' '-' )"
  for _cand in "$_sp_real/claude-501/$_slug"/*/scratchpad/shadow-185; do
    [ -d "$_cand/.git" ] || continue
    SHADOW="$_cand"
    break
  done
fi
[ -n "$SHADOW" ] || die "arvore-sombra do pacote C nao encontrada.
  Procurei por  <scratchpad deste repo>/*/scratchpad/shadow-185  e nao achei um
  repositorio git. Passe o caminho explicitamente:
    CEO_C_SHADOW=/caminho/da/sombra bash $ROOT/$CEREMONY_DIR/finalize-C.sh"
[ -d "$SHADOW/.git" ] || die "CEO_C_SHADOW nao e um repositorio git: $SHADOW"
_shadow_rp="$( cd "$SHADOW" && pwd -P )"
_root_rp="$( cd "$ROOT" && pwd -P )"
[ "$_shadow_rp" != "$_root_rp" ] || die "a sombra aponta para a arvore VIVA — recusado"
SHADOW="$_shadow_rp"
SHADOW_BASE="$( git -C "$SHADOW" rev-parse HEAD )"
ok "sombra: $SHADOW (base $SHADOW_BASE)"

# ---------------------------------------------------------------------------
step "1 — fronteira de paths: REQUIRED presente, nada fora de ALLOWED"
# ---------------------------------------------------------------------------
# `tr ' ' '\n'` em vez de deixar o shell dividir a palavra: a divisao por IFS
# funcionaria, mas depende de o IFS estar no default e o shellcheck reprova
# (SC2046) com razao — o mesmo idioma do LAND, para as duas leituras casarem.
REQ_SORTED="$( _expect REQUIRED_PATCH_PATHS | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u )"
EXTRA_SORTED="$( _expect ALLOWED_EXTRA_PATCH_PATHS | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u )"
# Os GERADOS tem uma terceira polaridade: este script os PRODUZ na arvore-sombra,
# entao a sombra de trabalho legitimamente nao os carrega. Eles entram no
# conjunto TOLERADO (para o passo 1 nao acusar) e no conjunto EXIGIDO DO PATCH
# (para o passo 5 acusar se a producao falhou) — nunca no exigido da SOMBRA.
GEN_SORTED="$( _expect GENERATED_PATCH_PATHS | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u )"
ALLOWED_SORTED="$( printf '%s\n%s\n%s\n' "$REQ_SORTED" "$EXTRA_SORTED" "$GEN_SORTED" | sed '/^$/d' | LC_ALL=C sort -u )"
printf '      %s obrigatorio(s), %s tolerado(s), %s gerado(s) por este script\n' \
  "$( printf '%s\n' "$REQ_SORTED" | wc -l | tr -d ' ' )" \
  "$( printf '%s\n' "$EXTRA_SORTED" | wc -l | tr -d ' ' )" \
  "$( printf '%s\n' "$GEN_SORTED" | wc -l | tr -d ' ' )"

# Porcelain NUL-delimitado: o corte de 3 caracteres deixaria `old -> new`
# inteiro num rename, e a classificacao usaria o path VELHO.
#
# `-uall` NAO e opcional. Sem ele o porcelain COLAPSA um diretorio inteiramente
# untracked numa unica entrada com barra no fim, e a comparacao contra um
# conjunto que lista ARQUIVOS abortaria dizendo que a sombra mexeu num path
# fora do escopo. Um gate que so falha em sombra nova falha na hora errada.
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

OUTSIDE="$( comm -23 <( printf '%s\n' "$CHANGED_SORTED" ) <( printf '%s\n' "$ALLOWED_SORTED" ) )"
if [ -n "$OUTSIDE" ]; then
  die "a sombra mexeu em path(s) FORA da fronteira declarada:
$( printf '  %s\n' $OUTSIDE )
  A fronteira vive em $BASELINE_ENV
  (REQUIRED_PATCH_PATHS + ALLOWED_EXTRA_PATCH_PATHS). Ou a sombra ganhou
  trabalho que esta cerimonia nao revisou, ou a fronteira ficou velha. Nos DOIS
  casos a decisao e do CEO — este script nao alarga escopo sozinho."
fi

MISSING_REQ="$( comm -13 <( printf '%s\n' "$CHANGED_SORTED" ) <( printf '%s\n' "$REQ_SORTED" ) )"
if [ -n "$MISSING_REQ" ]; then
  die "path(s) OBRIGATORIO(s) que a sombra NAO carrega:
$( printf '  %s\n' $MISSING_REQ )
  O pacote C tem duas metades escritas em paralelo: a de codigo
  (install.sh / upgrade.sh / _framework_manifest_set.sh / o e2e / DESIGN-C.md)
  e a de CI e docs (os dois workflows, o threat-model e o ADR-196). Se os que
  faltam sao os da segunda metade, ela ainda nao entrou na sombra — espere o
  outro autor terminar e rode este script de novo. NAO remova o path da lista
  REQUIRED para destravar: um teste sem wiring de CI e um teste que nunca roda,
  e um predicado compartilhado sem ADR e uma decisao transversal sem registro."
fi
ok "a sombra mexeu em $( printf '%s\n' "$CHANGED_SORTED" | wc -l | tr -d ' ' ) path(s); os $( printf '%s\n' "$REQ_SORTED" | wc -l | tr -d ' ' ) obrigatorios estao presentes"

# ---------------------------------------------------------------------------
step "2 — guard de drift (a licao da S329: o pack nao pode REVERTER o destino)"
# ---------------------------------------------------------------------------
# Para cada path que a sombra mexeu: se ele existe na BASE DA SOMBRA e tambem
# no HEAD vivo, os dois blobs tem de ser byte-identicos. Se divergiram, alguem
# editou o destino depois que a sombra foi criada e a copia por conteudo
# REVERTERIA essa edicao. A leitura da base e feita DENTRO da sombra
# (`git -C "$SHADOW" show`): o HEAD vivo pode nem conter o commit da base.
#
# EXCECAO, e ela e estrutural: os paths GERADOS ficam de fora deste guard. O
# guard existe para impedir que a copia por conteudo REVERTA a edicao de outra
# pessoa no destino. Um path que este script REGERA do zero (o ratchet do
# censo) nao pode reverter nada: o conteudo que vai para o patch nao vem da
# sombra, vem da regeneracao sobre o HEAD do momento. Medido na S329: a 6a
# passada do censo landou em HEAD e mudou o baseline; sem esta excecao o
# finalize abortaria acusando drift num arquivo que ele proprio ia reescrever —
# um vermelho que nao protege nada e que nenhuma acao do operador resolveria.
DRIFTED=""
CLASS_B=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  case "
$GEN_SORTED
" in
    *"
$p
"*) continue ;;
  esac
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
done < <( printf '%s\n' "$CHANGED_SORTED" )

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
step "3 — arvore-sombra em $HEAD_SHA, censo PRE, copia por conteudo"
# ---------------------------------------------------------------------------
WT="$( mktemp -d "${TMPDIR:-/tmp}/s329C-wt.XXXXXX" )/wt"
git worktree add --detach --quiet "$WT" "$HEAD_SHA" \
  || die "git worktree add falhou — a arvore-sombra nao foi criada"
ok "arvore-sombra: $WT"

# --- o censo, medido ANTES de copiar: esta e a arvore PRE-patch --------------
# O instrumento e um alvo MOVEL: nesta noite ele mudou duas vezes, e o mesmo
# `scripts/` byte-identico rendeu 341 sitios numa versao e 799 na outra. Por
# isso o sha do instrumento NAO e declarado a mao: ele e DERIVADO aqui, gravado
# no bloco AUTO e congelado pela assinatura. O que ele garante e o que importa:
# que os numeros que o LAND compara foram medidos com o MESMO instrumento que o
# LAND vai executar. Se ele andar entre assinar e landar, o V4 aborta.
CENSUS_OK=0
# Inicializados AQUI, nao dentro do ramo que os preenche: sob `set -u` uma
# variavel nao inicializada mata o script no ponto de uso — e o ponto de uso
# (o bloco AUTO, passo 6) fica FORA do `if` que os define.
CENSUS_SHA=""
CENSUS_POS_DESG=""
CENSUS_POS_SITES=""
if [ -f "$WT/$CENSUS" ]; then
  CENSUS_SHA="$( shasum -a 256 "$WT/$CENSUS" | awk '{print $1}' )"
  CENSUS_OK=1
  ok "instrumento do censo em HEAD: $CENSUS_SHA"
else
  die "instrumento do censo AUSENTE em HEAD ($CENSUS).
  O baseline do ratchet e regenerado por ele, e sem regeneracao este pacote
  deixaria o step do censo do validate.yml vermelho no main. Sem rota de
  contorno: ou o instrumento existe, ou a cerimonia precisa ser re-desenhada."
fi

CENSUS_PRE_DESG=""
if [ "$CENSUS_OK" = "1" ]; then
  _pre_json="$WT.census-pre.json"
  python3 "$WT/$CENSUS" --repo-root "$WT" --json > "$_pre_json" 2>/dev/null || printf ''
  CENSUS_PRE_DESG="$( python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["counts"]["desguardado"])' "$_pre_json" 2>/dev/null || printf '' )"
  [ -n "$CENSUS_PRE_DESG" ] || die "nao consegui ler o censo PRE-patch — saida em $_pre_json"
  ok "censo PRE-patch (arvore limpa em HEAD): desguardado=$CENSUS_PRE_DESG"
fi

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
done < <( printf '%s\n' "$CHANGED_SORTED" )
ok "$COPIED arquivo(s) copiados, $REMOVED removido(s)"

# --- normalizacao do bit de execucao ---------------------------------------
# `scripts/tests/*.sh` e executavel neste repositorio (medido: 100755 na grande
# maioria dos vizinhos). A copia na sombra nasceu 100644. O `cp -p` preserva o
# modo da origem, entao sem esta linha o patch carregaria `new file mode
# 100644` e o passo S do LAND abortaria — corretamente, mas na hora errada e
# sem que ninguem pudesse consertar sem editar a sombra. Normalizo AQUI e digo
# em voz alta que normalizei.
_e2e_mode_exp="$(_expect EXPECTED_E2E_INDEX_MODE)"
if [ -f "$WT/$E2E_TEST" ] && [ "$_e2e_mode_exp" = "100755" ] && [ ! -x "$WT/$E2E_TEST" ]; then
  chmod +x "$WT/$E2E_TEST" || die "falhei ao por o bit de execucao em $E2E_TEST"
  warn "pus o bit de execucao em $E2E_TEST (a sombra o trazia 644;"
  printf '        os vizinhos de scripts/tests/ sao 755 e o passo S do LAND confere)\n'
fi

# `cp` nao inventa marcadores de conflito, mas uma sombra deixada no meio de um
# merge carregaria os dela — e um patch com marcadores assinado seria bytes
# quebrados no main. A varredura e restrita aos paths copiados.
while IFS= read -r p; do
  [ -z "$p" ] && continue
  [ -f "$WT/$p" ] || continue
  if grep -q -e '^<<<<<<< ' -e '^>>>>>>> ' -- "$WT/$p"; then
    die "a arvore-sombra ficou com marcadores de conflito em $p — recusado"
  fi
done < <( printf '%s\n' "$CHANGED_SORTED" )
ok "nenhum marcador de conflito nos paths copiados"

# ---------------------------------------------------------------------------
step "4 — bateria CURTA na arvore-sombra"
# ---------------------------------------------------------------------------
# A bateria LONGA (o e2e de ~7 min, o smoke-install, os gates de corpus) e o
# V-block do LAND; repeti-la aqui dobraria o tempo da manha sem acrescentar
# informacao. O que roda aqui e o que responde "o conteudo copiado ainda e
# valido?".

# 4a — sintaxe dos scripts shell tocados.
SH_IN_PATCH=0
SH_LIST="$WT.shfiles"
: > "$SH_LIST"
while IFS= read -r p; do
  [ -z "$p" ] && continue
  [ -f "$WT/$p" ] || continue
  case "$p" in
    *.sh) printf '%s\n' "$p" >> "$SH_LIST"; SH_IN_PATCH=$(( SH_IN_PATCH + 1 )) ;;
  esac
done < <( printf '%s\n' "$CHANGED_SORTED" )
_sh_exp="$(_expect EXPECTED_SHELL_FILES_IN_PATCH)"
[ "$SH_IN_PATCH" = "$_sh_exp" ] \
  || die "4a: $SH_IN_PATCH script(s) shell no pacote, esperado $_sh_exp.
  Menos significa que um dos tres escritores (ou o e2e) saiu do patch; mais
  significa que o pacote cresceu para superficie que a revisao nao leu."
while IFS= read -r f; do
  ( cd "$WT" && bash -n "$f" ) || die "4a: 'bash -n' reprovou em $f"
done < "$SH_LIST"
ok "4a: bash -n verde em $SH_IN_PATCH script(s)"

if command -v shellcheck >/dev/null 2>&1; then
  while IFS= read -r f; do
    ( cd "$WT" && shellcheck -S warning "$f" ) || die "4b: shellcheck reprovou em $f"
  done < "$SH_LIST"
  ok "4b: shellcheck -S warning verde em $SH_IN_PATCH script(s)"
else
  warn "4b: shellcheck AUSENTE nesta maquina — o LAND e o CI executam"
fi

# 4c — os workflows pos-copia continuam parseaveis.
YML_CHECKED=0
for y in "$YML_SMOKE" "$YML_VALIDATE"; do
  [ -f "$WT/$y" ] || continue
  if python3 -c 'import yaml' >/dev/null 2>&1; then
    ( cd "$WT" && python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$y" ) \
      || die "4c: yaml.safe_load reprovou em $y"
    YML_CHECKED=$(( YML_CHECKED + 1 ))
  elif command -v ruby >/dev/null 2>&1; then
    ( cd "$WT" && ruby -ryaml -e 'YAML.safe_load(File.read(ARGV[0]), aliases: true)' "$y" ) \
      || die "4c: ruby -ryaml reprovou em $y"
    YML_CHECKED=$(( YML_CHECKED + 1 ))
  fi
done
if [ "$YML_CHECKED" -gt 0 ]; then
  ok "4c: $YML_CHECKED workflow(s) parseiam"
else
  warn "4c: nem PyYAML nem ruby disponiveis — o actionlint do CI cobre"
fi
if command -v actionlint >/dev/null 2>&1; then
  for y in "$YML_SMOKE" "$YML_VALIDATE"; do
    [ -f "$WT/$y" ] || continue
    AL_LOG="$WT.actionlint.log"
    ( cd "$WT" && actionlint "$y" ) > "$AL_LOG" 2>&1 \
      || { sed 's/^/      /' "$AL_LOG" >&2; die "4d: actionlint reprovou em $y"; }
  done
  ok "4d: actionlint verde"
else
  warn "4d: actionlint AUSENTE — o CI executa"
fi

# 4e — o invariante anti-rot desta wave, medido no ARQUIVO que sera landado.
# A classe que a wave fecha nao e "falta uma guarda": e "cada escritor tem a SUA
# guarda, e elas divergem". Um segundo corpo do predicado dentro de install.sh
# ou upgrade.sh e a classe renascendo — a mesma forma dos quatro D1..D4 da S323.
PRED="$(_expect EXPECTED_PREDICATE_NAME)"
PRED_FILE="$(_expect EXPECTED_PREDICATE_DEFINITION_FILE)"
_defs_total=0
for f in "$LIB" "$INSTALLER" "$UPGRADER"; do
  [ -f "$WT/$f" ] || continue
  _n="$( grep -c "^${PRED}() {" "$WT/$f" || true )"
  _defs_total=$(( _defs_total + _n ))
  if [ "$f" != "$PRED_FILE" ] && [ "$_n" != "0" ]; then
    die "4e: $f DEFINE $PRED ($_n vez(es)).
  O predicado vive numa biblioteca e os escritores o CONSULTAM. Um segundo
  corpo aqui recria a classe das copias divergentes que esta wave fecha."
  fi
done
_defs_exp="$(_expect EXPECTED_PREDICATE_DEFINITIONS_TOTAL)"
[ "$_defs_total" = "$_defs_exp" ] \
  || die "4e: $PRED e definido $_defs_total vez(es), esperado $_defs_exp"
_consumers=0
for f in "$INSTALLER" "$UPGRADER"; do
  [ -f "$WT/$f" ] || continue
  _n="$( grep -c -- "$PRED" "$WT/$f" || true )"
  [ "$_n" -ge 1 ] || die "4e: $f NAO referencia $PRED.
  Um consumidor com zero referencias e um consumidor que nao consome: o
  predicado existiria e nao guardaria nada."
  _consumers=$(( _consumers + 1 ))
done
_cons_exp="$(_expect EXPECTED_PREDICATE_CONSUMER_FILES)"
[ "$_consumers" = "$_cons_exp" ] \
  || die "4e: $_consumers consumidor(es) do predicado, esperado $_cons_exp"
ok "4e: $PRED definido 1x em $PRED_FILE e consumido por $_consumers arquivo(s)"

# `scripts/doctor.sh` e o TERCEIRO consumidor previsto e NAO foi convertido
# (FU-7 do DESIGN-C). Registrado como numero para que a conversao futura
# apareca como divergencia consciente, nunca como surpresa.
if [ -f "$WT/$DOCTOR" ]; then
  _doc_obs="$( grep -c -- "$PRED" "$WT/$DOCTOR" || true )"
  _doc_exp="$(_expect EXPECTED_PREDICATE_DOCTOR_REFS)"
  [ "$_doc_obs" = "$_doc_exp" ] \
    || die "4e: $DOCTOR referencia $PRED $_doc_obs vez(es), declarado $_doc_exp.
  Se o doctor foi convertido (FU-7), isso e boa noticia — mas e mudanca de
  escopo: atualize $BASELINE_ENV e o registro de revisao conscientemente."
  ok "4e: $DOCTOR referencia o predicado $_doc_obs vez(es) (FU-7 em aberto por desenho)"
fi

# 4f — o RATCHET do censo: regenerar na arvore-sombra e PROVAR que sai limpo.
#
# Ordem do CEO (S329). Sem isto o pacote instalaria, no mesmo commit, um step de
# CI que roda o censo fail-closed E o baseline pre-cura que o faz sair 1 — a
# classe que manteve o main vermelho da S322 a S327.
#
# A regeneracao e CONFINADA por medicao, nao por leitura do --help: com
# `--repo-root <arvore-sombra>` o instrumento escreve
# `<arvore-sombra>/.claude/scripts/data/...` (o caminho aparece na saida) e a
# arvore VIVA fica byte-identica. Numa arvore pristina em HEAD a regeneracao
# reproduz o baseline de HEAD byte a byte, entao todo delta que aparece no patch
# vem do conteudo da cura — de mais nada.
if [ "$CENSUS_OK" = "1" ]; then
  [ -f "$WT/$BASELINE_DATA" ] || die "4f: baseline do censo ausente na arvore-sombra ($BASELINE_DATA)"
  _bl_before="$( shasum -a 256 "$WT/$BASELINE_DATA" | awk '{print $1}' )"
  _live_before="$( shasum -a 256 "$ROOT/$BASELINE_DATA" 2>/dev/null | awk '{print $1}' )"

  _wb_log="$WT.write-baseline.log"
  python3 "$WT/$CENSUS" --repo-root "$WT" --write-baseline > "$_wb_log" 2>&1 \
    || { sed 's/^/      /' "$_wb_log" >&2; die "4f: --write-baseline reprovou — saida em $_wb_log"; }

  # Controle de CONFINAMENTO, toda vez: se a regeneracao tivesse escrito na
  # arvore viva, isto seria uma edicao canonica fora de qualquer cerimonia.
  # Barato, e a pergunta e boa demais para ser feita so uma vez.
  _live_after="$( shasum -a 256 "$ROOT/$BASELINE_DATA" 2>/dev/null | awk '{print $1}' )"
  [ "$_live_before" = "$_live_after" ] \
    || die "4f: --write-baseline MODIFICOU a arvore VIVA ($BASELINE_DATA).
  Isso e uma escrita canonica fora de cerimonia. Restaure com
    git -C $ROOT checkout -- $BASELINE_DATA
  e NAO finalize ate entender por que o --repo-root nao confinou."

  _bl_after="$( shasum -a 256 "$WT/$BASELINE_DATA" | awk '{print $1}' )"
  if [ "$_bl_before" = "$_bl_after" ]; then
    warn "4f: o baseline regenerado saiu byte-identico ao de HEAD."
    printf '        A cura nao moveu nenhum fingerprint. E possivel, e nesse caso\n'
    printf '        o path simplesmente nao viaja no patch — o passo 5 sabe disso.\n'
  else
    ok "4f: baseline do ratchet REGENERADO na arvore-sombra ($( sed -n 's/^wrote \([0-9][0-9]*\) .*/\1/p' "$_wb_log" | head -1 ) entradas)"
  fi

  # A prova. Rodar o censo EXATAMENTE como o step do validate.yml roda — sem
  # flags — e exigir rc 0. Nao ha valor aceitavel diferente de limpo: qualquer
  # outro e o CI vermelho no primeiro push.
  _pos_json="$WT.census-pos.json"
  _pos_rc=0
  python3 "$WT/$CENSUS" --repo-root "$WT" --json > "$_pos_json" 2>/dev/null || _pos_rc=$?
  _cen="$( python3 - "$_pos_json" <<'PY' || printf ''
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
c = d["counts"]
print("%d %d %d %d" % (c["desguardado"], c["sites"],
                       len(d["new_blocking"]), len(d["dead_baseline_entries"])))
PY
)"
  [ -n "$_cen" ] || die "4f: nao consegui ler o censo POS-patch — saida em $_pos_json"
  set -- $_cen
  CENSUS_POS_DESG="$1"; CENSUS_POS_SITES="$2"; _c_new="$3"; _c_dead="$4"

  if [ "$(_expect EXPECTED_CENSUS_RATCHET_CLEAN)" = "1" ]; then
    if [ "$_pos_rc" != "0" ] || [ "$_c_new" != "0" ] || [ "$_c_dead" != "0" ]; then
      die "4f: o ratchet do censo NAO saiu limpo DEPOIS de regenerado.
    rc                    : $_pos_rc
    new_blocking          : $_c_new
    dead_baseline_entries : $_c_dead
  Regenerar e a cura; se depois dela ainda sobra diferenca, o instrumento nao e
  determinista sobre a mesma arvore, ou alguem escreveu em scripts/ entre a
  regeneracao e a medicao. Chame o CEO — NAO relaxe este gate: e ele que
  responde a mesma pergunta que o step do validate.yml fara no primeiro push.
  Saida do censo: $_pos_json"
    fi
    ok "4f: ratchet LIMPO pos-regeneracao (rc=$_pos_rc, 0 nova(s), 0 morta(s)) — o step do CI sai verde"
  fi

  _sites_min="$(_expect EXPECTED_CENSUS_SITES_MIN)"
  [ "$CENSUS_POS_SITES" -ge "$_sites_min" ] \
    || die "4f: o censo achou so $CENSUS_POS_SITES sitio(s), minimo $_sites_min.
  Zero (ou quase) significa que a BUSCA quebrou, nao que o corpus esta limpo —
  e um gate verde sobre um censo vazio e o pior resultado possivel."

  if [ "$(_expect EXPECTED_CENSUS_DESGUARDADO_MUST_NOT_INCREASE)" = "1" ]; then
    [ "$CENSUS_POS_DESG" -le "$CENSUS_PRE_DESG" ] \
      || die "4f: desguardado subiu de $CENSUS_PRE_DESG para $CENSUS_POS_DESG.
  A cura ABRIU sitio(s) de escrita sem guarda — o inverso do que a wave existe
  para fazer. Isto NAO e um numero a atualizar; e um defeito a investigar."
  fi
  ok "4f: desguardado $CENSUS_PRE_DESG -> $CENSUS_POS_DESG, sites=$CENSUS_POS_SITES"
fi

# ---------------------------------------------------------------------------
step "5 — patch, Scope, Patch-base e Patch-sha256"
# ---------------------------------------------------------------------------
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

# Conjunto de paths do patch FINAL contra a FRONTEIRA. O passo 1 checou a
# SOMBRA; este checa o ENTREGAVEL, que e outra coisa: um path pode sair do
# patch por ficar byte-identico ao HEAD.
PATCH_PATHS="$( git apply --numstat "$PATCH" | awk '{print $3}' | LC_ALL=C sort -u )"
[ -n "$PATCH_PATHS" ] || die "o patch gerado nao toca arquivo nenhum"
_extra="$( comm -23 <( printf '%s\n' "$PATCH_PATHS" ) <( printf '%s\n' "$ALLOWED_SORTED" ) )"
[ -z "$_extra" ] || die "o patch toca path(s) fora da fronteira:
$( printf '  %s\n' $_extra )"
# O conjunto que o patch TEM de tocar = os obrigatorios da sombra MAIS os
# GERADOS por este script. Um gerado que sai byte-identico ao HEAD nao viajaria
# no patch, e o G4 do LAND — que exige os gerados — abortaria de manha. Entao a
# divergencia e resolvida AQUI, e para o lado fail-closed: se a regeneracao do
# ratchet nao mudou nada enquanto a cura reescreve 26 hunks, ou o instrumento
# nao esta vendo a cura, ou o baseline nao foi regenerado de fato. Nos dois
# casos e melhor parar do que landar e descobrir no push.
MUST_TOUCH="$REQ_SORTED"
GEN_IN_PATCH=0
while IFS= read -r p; do
  [ -z "$p" ] && continue
  [ -f "$WT/$p" ] || die "path GERADO ausente da arvore-sombra: $p
  O passo 4f deveria te-lo produzido. Nao finalize."
  _h="$( git show "HEAD:$p" 2>/dev/null | shasum -a 256 | awk '{print $1}' )"
  _w="$( shasum -a 256 "$WT/$p" | awk '{print $1}' )"
  [ "$_h" != "$_w" ] || die "o path GERADO $p saiu byte-identico ao de HEAD.
  A cura reescreve 26 hunks de install.sh e acrescenta 177 linhas a biblioteca;
  um baseline de censo identico ao anterior significa que o instrumento nao esta
  enxergando a cura, ou que a regeneracao nao aconteceu. O G4 do LAND exige este
  path, entao seguir aqui so adiaria o vermelho para a manha.
  Se isto for legitimo um dia, tire o path de GENERATED_PATCH_PATHS em
  $BASELINE_ENV conscientemente — nunca em silencio."
  MUST_TOUCH="$MUST_TOUCH
$p"
  GEN_IN_PATCH=$(( GEN_IN_PATCH + 1 ))
done < <( printf '%s\n' "$GEN_SORTED" )
MUST_TOUCH="$( printf '%s\n' "$MUST_TOUCH" | sed '/^$/d' | LC_ALL=C sort -u )"

_ghost="$( comm -13 <( printf '%s\n' "$PATCH_PATHS" ) <( printf '%s\n' "$MUST_TOUCH" ) )"
if [ -n "$_ghost" ]; then
  die "path(s) que o patch TINHA de tocar e nao toca:
$( printf '  %s\n' $_ghost )
  Ou o conteudo ja esta no HEAD (a cura landou parcialmente e o pacote ficou
  velho), ou a sombra perdeu a mudanca, ou a regeneracao do ratchet nao entrou.
  Chame o CEO — o G4 do LAND recusa um Scope mais largo que o patch, entao isto
  abortaria de manha."
fi
PATCH_PATH_COUNT="$( printf '%s\n' "$PATCH_PATHS" | wc -l | tr -d ' ' )"
ok "o patch toca $PATCH_PATH_COUNT path(s), dentro da fronteira; $GEN_IN_PATCH gerado(s) presente(s)"

# Canonicidade OBSERVADA, contra o piso declarado. Sem isto, um patch que
# perdesse os tres scripts de `scripts/` e carregasse so os testes passaria pelo
# G5: zero canonicos tocados e trivialmente "todos concedidos".
CANON_COUNT=0
while IFS= read -r p; do
  [ -z "$p" ] && continue
  _v="$( python3 .claude/hooks/check_canonical_edit.py --is-canonical "$p" 2>/dev/null | awk -F'\t' 'NR==1{print $2}' )"
  case "$_v" in
    1) CANON_COUNT=$(( CANON_COUNT + 1 )) ;;
    0) : ;;
    *) die "o oraculo de canonicidade nao respondeu 0|1 para: $p" ;;
  esac
done < <( printf '%s\n' "$PATCH_PATHS" )
_canon_min="$(_expect EXPECTED_PATCH_CANONICAL_MIN)"
[ "$CANON_COUNT" -ge "$_canon_min" ] \
  || die "o patch tem $CANON_COUNT path(s) CANONICOS, minimo $_canon_min.
  Menos significa que um alvo canonico da wave saiu do patch."
ok "$CANON_COUNT path(s) canonico(s) (minimo $_canon_min)"

# ---------------------------------------------------------------------------
step "6 — bloco AUTO do EXPECTED-BASELINE.txt"
# ---------------------------------------------------------------------------
# O conjunto EXATO e a contagem canonica sao gravados AQUI e congelados pela
# assinatura. So o bloco entre os dois marcadores e reescrito: as duas listas
# humanas e todos os numeros medidos ficam intactos.
python3 - "$ROOT/$BASELINE_ENV" "$AUTO_BEGIN" "$AUTO_END" \
         "$( printf '%s' "$PATCH_PATHS" | tr '\n' ' ' | sed 's/ *$//' )" \
         "$CANON_COUNT" "$HEAD_SHA" \
         "$CENSUS_SHA" "$CENSUS_PRE_DESG" "$CENSUS_POS_DESG" "$CENSUS_POS_SITES" \
         <<'PY' || die "nao consegui reescrever o bloco AUTO"
import sys, time

(path, begin, end, paths, canon, head,
 census_sha, pre_desg, pos_desg, pos_sites) = sys.argv[1:11]
text = open(path, encoding="utf-8").read()
if text.count(begin) != 1 or text.count(end) != 1:
    sys.exit("marcador AUTO ausente ou duplicado em %s" % path)
head_part, rest = text.split(begin, 1)
_, tail = rest.split(end, 1)
block = "\n".join([
    'EXPECTED_PATCH_PATHS="%s"' % paths,
    "EXPECTED_PATCH_CANONICAL_PATHS=%s" % canon,
    "EXPECTED_CENSUS_INSTRUMENT_SHA256=%s" % census_sha,
    "EXPECTED_CENSUS_DESGUARDADO_PRE=%s" % pre_desg,
    "EXPECTED_CENSUS_DESGUARDADO_POS=%s" % pos_desg,
    "EXPECTED_CENSUS_SITES_POS=%s" % pos_sites,
    "FINALIZED_AT=%s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "FINALIZED_AGAINST_HEAD=%s" % head,
])
open(path, "w", encoding="utf-8").write(
    head_part + begin + "\n" + block + "\n" + end + tail)
print("  bloco AUTO reescrito: %d path(s), %s canonico(s), censo %s -> %s desguardado(s)"
      % (len(paths.split()), canon, pre_desg, pos_desg))
PY

# Re-leitura fail-closed: o que o LAND vai comparar tem de bater com o que
# acabamos de medir. Um bloco escrito e nao relido e uma afirmacao, nao um fato.
_auto_paths="$( _expect EXPECTED_PATCH_PATHS | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u )"
[ "$_auto_paths" = "$PATCH_PATHS" ] \
  || die "o bloco AUTO nao releu igual ao medido — nao assine.
    medido: $( printf '%s' "$PATCH_PATHS" | tr '\n' ' ' )
    relido: $( printf '%s' "$_auto_paths" | tr '\n' ' ' )"
[ "$(_expect EXPECTED_PATCH_CANONICAL_PATHS)" = "$CANON_COUNT" ] \
  || die "o bloco AUTO nao releu a contagem canonica igual ao medido"
ok "bloco AUTO relido e coerente"

printf '%s\n' "$HEAD_SHA" > "$BASE_SHA_FILE"
ok "BASE-SHA.txt atualizado"

git apply --check "$PATCH" || die "o patch gerado NAO aplica na arvore viva"
ok "git apply --check verde na arvore viva"

# ---------------------------------------------------------------------------
step "7 — commit dos materiais regenerados (sem editor)"
# ---------------------------------------------------------------------------
if [ "$NO_COMMIT" = "1" ]; then
  warn "--no-commit: nada foi staged nem commitado."
  printf '        Os 5 materiais estao no disco, prontos para o commit de quem\n'
  printf '        estiver conduzindo a cerimonia:\n'
  for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE" "$BASELINE_ENV"; do
    printf '          %s\n' "$f"
  done
  printf '        O SIGN exige os materiais RASTREADOS — sem esse commit ele aborta.\n'
else
# Staging EXPLICITO, arquivo a arquivo. Um staging por DIRETORIO (ou o add-tudo)
# arrastaria o trabalho de outros pacotes que ainda esteja na arvore; o conjunto
# e conferido logo abaixo e um path a mais ABORTA.
for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE" "$BASELINE_ENV"; do
  git add -- "$f"
done
STAGED="$( git diff --cached --name-only | LC_ALL=C sort -u )"
if [ -z "$STAGED" ]; then
  ok "os 5 materiais sairam byte-identicos — NADA a fazer"
else
  printf '%s\n' "$STAGED" | sed 's/^/    staged: /'
  EXTRA="$( printf '%s\n' "$STAGED" \
            | grep -v -x -F -e "$PATCH" -e "$SENTINEL" -e "$PROPOSED" \
                           -e "$BASE_SHA_FILE" -e "$BASELINE_ENV" \
            || printf '' )"
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  [ -z "$EXTRA" ] || die "index carrega path(s) fora dos 5 materiais:
$( printf '  %s\n' $EXTRA )
  Rode  git reset  e comece de novo."
  git commit -q -m "chore(PLAN-185 s329-C): patch derivado da sombra e baseado em $HEAD_SHA (finalize-C.sh)" \
    || die "o commit falhou — o staging esta intacto; chame o CEO"
  ok "commit criado: $( git rev-parse --short HEAD )"
fi
fi

step "PRONTO"
cat <<EOF

  O pacote C esta baseado em  $( git rev-parse HEAD )  e o patch aplica limpo.
    patch  : $PATCH
    sha256 : $NEW_PATCH_SHA
    paths  : $PATCH_PATH_COUNT  ($CANON_COUNT canonico(s))

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$SIGN_SCRIPT

EOF
