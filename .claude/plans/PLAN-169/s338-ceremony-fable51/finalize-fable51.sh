#!/usr/bin/env bash
# finalize-fable51.sh — DERIVA o WFABLE51.patch da arvore-sombra e o baseia no HEAD vivo.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao;
# nao ha gerador para o passo de derivacao (o generate-ceremony.sh assume o
# layout architect/round-N/approved.md, que esta cerimonia nao usa).
#
# O QUE ESTA WAVE ENTREGA (PLAN-169 wave-fable51 — cerimonia adopt-fable-5.1,
# rota (c) ratificada pelo Owner na S338): `claude-fable-5-1` APPENDED AT END
# no AVAILABLE_MODELS_WORKING_SET do ADR-149 (Amendment 2); os dois settings
# regenerados do ADR (KERNEL: settings.json esta em _KERNEL_PATHS, o LAND arma
# o override); os tres espelhos independentes que a paridade amarra por
# igualdade de conjunto (case-arm do validate-governance.sh — membro do
# manifesto ADR-192, sha re-derivado —, VALID_MODEL_IDS do tier_policy_cli,
# ALLOWED_MODELS/EXPECTED_AVAILABLE do smoke-install-parity.sh); o upgrade.sh
# com a lista SUPERSEDED (os adopters v1.2.0/v1.3.0 shiparam a lista de 6);
# as tabelas de custo/telemetria + detectores + alias; testes e docs.
# 25 paths, TODOS derivados de um unico material versionado
# (apply-fable51-edits.py) — 5 canonicos e 20 livres.
#
# ESTE SCRIPT E UM CLONE GATE-A-GATE DO finalize-183batch.sh (que landou o
# b7dad83 REAL na S336), e isso e deliberado: os guards dele foram pagos com
# o pacote D abortando duas vezes na S329 e curados por 8 rodadas de rail de
# materiais na S334 (drift-guard, `|| true` nos greps cujo zero e resposta,
# HEAD-andou, backup/restore transacional dos 4 materiais com pre-estado
# EXATO de worktree+index, flags de trap nunca herdadas do ambiente). Eles
# estao aqui byte-a-byte. O que muda e o bloco de constantes e o passo 4:
# a bateria daqui prova REPRODUTIBILIDADE (worktree em HEAD + script ==
# sombra, byte a byte, nos 25 paths), o gerador do ADR, o manifesto, a
# suite declarada, o gate de harness-config e o NAO-VACUO nomeado da wave
# (id ausente em HEAD, ULTIMO nos dois availableModels, floor/pin/fallback
# intactos, superseded presente).
#
# COMO A RE-BASE E FEITA, e por que NAO por `git apply --3way`.
# A re-base e por CONTEUDO: uma arvore-sombra limpa em HEAD recebe os
# arquivos da sombra de trabalho, path a path, e o patch e o diff DESSA arvore
# contra o HEAD. Um patch de `new file mode` aplicado com `--3way` sobre uma
# arvore onde o arquivo ja existe cai em conflito "both added" (medido na
# cerimonia F).
#
# O QUE ELE FAZ, em ordem:
#   0. pre-condicoes (materiais, sombra, HEAD em main);
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
# Uso:  bash .claude/plans/PLAN-169/s338-ceremony-fable51/finalize-fable51.sh
#       bash .../finalize-fable51.sh --no-commit  (gera tudo, NAO stageia nada)
#       bash .../finalize-fable51.sh --with-slow  (roda tambem os gates de
#                                                  corpus lentos: verify-counts,
#                                                  claims, governanca completa,
#                                                  parity smoke)
#       CEO_FABLE51_SHADOW=/caminho/da/sombra bash .../finalize-fable51.sh
set -euo pipefail

# --- argumentos -----------------------------------------------------------
# `--no-commit` existe para quem monta o pacote com OUTRO trabalho em voo na
# mesma arvore (esta wave nasceu com o pacote S337 STAGED ao lado): ele gera
# patch/Scope/BASE-SHA e NAO toca no index. O fluxo do Owner na manha usa a
# forma SEM flag, que commita.
#
# `--with-slow` roda os gates de CORPUS (`verify-counts.sh`, ~3 min,
# `check-claude-md-claims.py`, `validate-governance.sh` COMPLETO e o
# `smoke-install-parity.sh`, ~35 s de install real) NA ARVORE-SOMBRA e os
# compara com o valor DECLARADO. Eles NAO reescrevem a base — um instrumento
# que ajusta a propria expectativa nao mede nada.
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
CEREMONY_DIR="$PLAN_DIR/s338-ceremony-fable51"
SENTINEL="$PLAN_DIR/wave-fable51-approved.md"
PATCH="$CEREMONY_DIR/WFABLE51.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 W5 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S338-FABLE51-SIGN.sh"
APPLY="$CEREMONY_DIR/apply-fable51-edits.py"
SETTINGS=".claude/settings.json"
TEMPLATE_BASE="templates/settings/settings.base.json"
ADR=".claude/adr/ADR-149-model-id-allowlist.md"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"
GEN_MODELS=".claude/scripts/generate-available-models.py"
GEN_USER=".claude/scripts/gen-settings-user-template.py"
VALIDATE_SH=".claude/scripts/validate-governance.sh"
TYPES_PY=".claude/scripts/tier_policy_cli/_types.py"
PARITY_SH="scripts/local/smoke-install-parity.sh"
UPGRADE_SH="scripts/upgrade.sh"
UNIT_TESTS=".claude/hooks/tests/test_adr149_validator_parity.py \
.claude/hooks/tests/test_available_models_mirror.py \
.claude/hooks/tests/test_veto_floor_bijection.py \
.claude/hooks/tests/test_adr_052_role_to_model_coverage.py \
.claude/hooks/tests/test_template_dogfood_parity.py \
.claude/scripts/tests/test_generate_available_models.py \
.claude/scripts/tests/test_model_fleet_presence.py \
.claude/scripts/tests/test_a4_pricing_doctrine.py \
.claude/scripts/tests/test_gen_settings_user_template.py \
.claude/scripts/tier_policy_cli/tests/test_types.py \
.claude/scripts/tier_policy_cli/tests/test_learn_mutation.py \
.claude/scripts/optimizer/tests/test_optimizer_model_normalize.py \
.claude/scripts/detectors/tests/test_overpowered.py \
.claude/scripts/tests/test_build_canonical_models.py \
.claude/scripts/tests/test_upgrade_settings_migration.py"
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
WT2=""
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
  for _w in "$WT" "$WT2"; do
    if [ -n "$_w" ] && [ -d "$_w" ]; then
      git worktree remove --force "$_w" >/dev/null 2>&1 || printf ''
      rm -rf "$_w" 2>/dev/null || printf ''
    fi
  done
  git worktree prune >/dev/null 2>&1 || printf ''
}
trap _cleanup EXIT

# ---------------------------------------------------------------------------
step "0 — pre-condicoes"
# ---------------------------------------------------------------------------
for f in "$SENTINEL" "$PROPOSED" "$BASELINE_ENV" "$FINALIZE" "$APPLY"; do
  [ -f "$f" ] || die "material ausente: $f"
done
command -v jq >/dev/null 2>&1 || die "jq ausente — a bateria curta nao teria instrumento"
command -v shellcheck >/dev/null 2>&1 || die "shellcheck ausente — a wave toca 3 scripts shell e o 4h exige o lint"

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
# `CEO_FABLE51_SHADOW` tem precedencia. Sem ela, a busca e sob o scratchpad
# DESTE repositorio (slug = caminho absoluto com `/` -> `-`, o mesmo que o
# harness usa): pegar `*/*/scratchpad` cru cairia no scratchpad de OUTRO
# projeto.
#
# A pergunta "isto e um repositorio git?" e feita AO GIT, nunca por
# `[ -d "$x/.git" ]`: num `git worktree` o `.git` e um ARQUIVO com um ponteiro
# `gitdir:`, e o teste de diretorio rejeitaria uma sombra perfeitamente valida.
_is_git_tree() { git -C "$1" rev-parse --git-dir >/dev/null 2>&1; }

SHADOW="${CEO_FABLE51_SHADOW:-}"
if [ -z "$SHADOW" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  _slug="$( printf '%s' "$ROOT" | tr '/' '-' )"
  for _cand in "$_sp_real/claude-501/$_slug"/*/scratchpad/shadow-fable51; do
    [ -d "$_cand" ] || continue
    _is_git_tree "$_cand" || continue
    SHADOW="$_cand"
    break
  done
fi
[ -n "$SHADOW" ] || die "arvore-sombra do pacote fable51 nao encontrada.
  Procurei por  <scratchpad deste repo>/*/scratchpad/shadow-fable51  e nao
  achei um repositorio git. Passe o caminho explicitamente:
    CEO_FABLE51_SHADOW=/caminho/da/sombra bash $ROOT/$CEREMONY_DIR/finalize-fable51.sh
  (Para RECRIAR a sombra: git worktree add --detach <dir> HEAD &&
   python3 $APPLY --root <dir>)"
[ -d "$SHADOW" ] || die "CEO_FABLE51_SHADOW nao existe: $SHADOW"
_is_git_tree "$SHADOW" || die "CEO_FABLE51_SHADOW nao e um repositorio git: $SHADOW"
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

# O derivador tem de CONCORDAR com a base declarada: a lista de paths que
# ele toca e o EXPECTED sao a MESMA coisa dita em dois lugares, e a
# bijecao e checada aqui (um path a mais no script = escopo sem decisao;
# um a menos = o EXPECTED envelheceu).
_apply_paths="$( python3 "$APPLY" --list-paths | LC_ALL=C sort -u )"
[ "$_apply_paths" = "$EXPECTED_SORTED" ] || die "apply-fable51-edits.py --list-paths != EXPECTED_PATCH_PATHS
  so no script  : $( comm -23 <( printf '%s\n' "$_apply_paths" ) <( printf '%s\n' "$EXPECTED_SORTED" ) | tr '\n' ' ')
  so no EXPECTED: $( comm -13 <( printf '%s\n' "$_apply_paths" ) <( printf '%s\n' "$EXPECTED_SORTED" ) | tr '\n' ' ')"
ok "derivador e EXPECTED concordam nos $( printf '%s\n' "$EXPECTED_SORTED" | wc -l | tr -d ' ' ) paths"

# Porcelain NUL-delimitado: o corte de 3 caracteres deixaria `old -> new`
# inteiro num rename, e a classificacao usaria o path VELHO.
#
# `-uall` NAO e opcional. Sem ele o porcelain COLAPSA um diretorio inteiramente
# untracked numa unica entrada com barra no fim, e a comparacao contra o
# conjunto EXPECTED — que lista ARQUIVOS — abortaria dizendo que a sombra mexeu
# num path fora do escopo (medido na cerimonia F).
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
    CLASS_B="$CLASS_B  $p
"
  fi
done < <( printf '%s\n' "$EXPECTED_SORTED" )

if [ -n "$DRIFTED" ]; then
  die "path(s) do pacote mudaram no HEAD vivo depois que a sombra foi criada:
$DRIFTED
  Copiar a sombra por cima REVERTERIA essas edicoes — foi exatamente o que
  abortou o pacote D duas vezes na S329. A cura NAO e forcar: e re-derivar a
  sombra sobre o conteudo novo (git worktree add --detach <dir> HEAD &&
  python3 $APPLY --root <dir>) e rodar este script de novo."
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
WT="$( mktemp -d "${TMPDIR:-/tmp}/s338wf51-wt.XXXXXX" )/wt"
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
# A bateria LONGA (verify-counts ~3 min, governanca completa, ceremony-lint,
# parity smoke) e o V-block do LAND; repeti-la aqui dobraria o tempo da manha
# sem acrescentar informacao — salvo sob `--with-slow`, que existe para
# conferir antes. O que roda aqui e o que responde "o conteudo copiado ainda
# e valido, e e EXATAMENTE o que o derivador produz?".

# 4a — REPRODUTIBILIDADE: um SEGUNDO worktree limpo em HEAD recebe o
# derivador versionado; cada path EXPECTED tem de sair byte-identico ao da
# sombra. E a prova de que o patch assinado e a saida do script — e nada
# mais (o analogo do `base | jq-frag == settings` do 183batch, so que sobre
# todos os 25 paths).
WT2="$( mktemp -d "${TMPDIR:-/tmp}/s338wf51-wt2.XXXXXX" )/wt2"
git worktree add --detach --quiet "$WT2" "$HEAD_SHA" \
  || die "4a: git worktree add (reproducao) falhou"
python3 "$APPLY" --root "$WT2" >/dev/null \
  || die "4a: o derivador RECUSOU sobre HEAD limpo — ancora ausente/ambigua ou HEAD ja patchado"
_repro_bad=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  if ! cmp -s "$WT2/$p" "$WT/$p"; then _repro_bad="$_repro_bad  $p
"; fi
done < <( printf '%s\n' "$EXPECTED_SORTED" )
[ -z "$_repro_bad" ] || die "4a: a sombra NAO e a saida do derivador (byte a byte) em:
$_repro_bad  Ou a sombra ganhou edicao manual fora do script, ou o script mudou depois
  da sombra. Nos dois casos re-derive: git worktree add --detach <dir> HEAD &&
  python3 $APPLY --root <dir>"
ok "4a: HEAD + apply-fable51-edits.py == sombra, byte a byte, nos $( printf '%s\n' "$EXPECTED_SORTED" | wc -l | tr -d ' ' ) paths"

# 4b — o gerador do ADR e o gate central da wave: a linha EXATA declarada.
_gen_obs="$( cd "$WT" && python3 "$GEN_MODELS" --check 2>/dev/null | grep '^CHECK availableModels:' || printf 'GENERATOR-FAILED' )"
_gen_exp="$(_expect EXPECTED_GENERATOR_CHECK_LINE)"
[ "$_gen_obs" = "$_gen_exp" ] || die "4b: generate-available-models --check disse '$_gen_obs', esperado '$_gen_exp'"
jq -e . "$WT/$SETTINGS" >/dev/null || die "4b: settings.json nao parseia"
jq -e . "$WT/$TEMPLATE_BASE" >/dev/null || die "4b: settings.base.json nao parseia"
_am_n1="$( jq '.availableModels|length' "$WT/$SETTINGS" )"
_am_n2="$( jq '.availableModels|length' "$WT/$TEMPLATE_BASE" )"
_am_exp="$(_expect EXPECTED_AVAILABLE_MODELS_COUNT)"
{ [ "$_am_n1" = "$_am_exp" ] && [ "$_am_n2" = "$_am_exp" ]; } \
  || die "4b: availableModels com $_am_n1/$_am_n2 ids, esperado $_am_exp nos dois"
_pin1="$( jq -r '.model' "$WT/$SETTINGS" )"; _pin2="$( jq -r '.model' "$WT/$TEMPLATE_BASE" )"
_pin_exp="$(_expect EXPECTED_MODEL_PIN)"
{ [ "$_pin1" = "$_pin_exp" ] && [ "$_pin2" = "$_pin_exp" ]; } \
  || die "4b: pin model = $_pin1/$_pin2, esperado $_pin_exp (rota c: o pin NAO muda)"
_fb1="$( jq -c '.fallbackModel' "$WT/$SETTINGS" )"; _fb2="$( jq -c '.fallbackModel' "$WT/$TEMPLATE_BASE" )"
_fb_exp="$(_expect EXPECTED_FALLBACK_JSON)"
{ [ "$_fb1" = "$_fb_exp" ] && [ "$_fb2" = "$_fb_exp" ]; } \
  || die "4b: fallbackModel = $_fb1/$_fb2, esperado $_fb_exp"
ok "4b: gerador MATCH; $_am_exp ids nos dois settings; pin $_pin_exp e fallback $_fb_exp intactos"

# 4c — a suite declarada (os 5 testes de paridade do hooks/, as 7 suites de
# scripts/ e a migracao do upgrade com a classe SUPERSEDED).
UNIT_LOG="$WT.unit.log"
UNIT_RC=0
# shellcheck disable=SC2086  # lista controlada
( cd "$WT" && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest $UNIT_TESTS -q -p no:cacheprovider ) \
  > "$UNIT_LOG" 2>&1 || UNIT_RC=$?
[ "$UNIT_RC" -eq 0 ] || { tail -25 "$UNIT_LOG" | sed 's/^/      /' >&2
                          die "4c: a suite reprovou (rc=$UNIT_RC) — log em $UNIT_LOG"; }
_unit_obs="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$UNIT_LOG" || true; } \
              | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_unit_obs" ] || die "4c: nao consegui ler 'N passed' — log em $UNIT_LOG"
[ "$_unit_obs" = "$(_expect EXPECTED_UNIT_PYTEST_PASSED)" ] \
  || die "4c: $_unit_obs passaram, esperado $(_expect EXPECTED_UNIT_PYTEST_PASSED)"
_skip_obs="$( { grep -oE '[0-9]+ skipped' "$UNIT_LOG" || true; } | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_skip_obs" ] || _skip_obs=0
[ "$_skip_obs" = "$(_expect EXPECTED_UNIT_PYTEST_SKIPPED)" ] \
  || die "4c: $_skip_obs pulados, esperado $(_expect EXPECTED_UNIT_PYTEST_SKIPPED)"
ok "4c: suite $_unit_obs/$(_expect EXPECTED_UNIT_PYTEST_PASSED) (skips $_skip_obs)"

# 4d — o manifesto ADR-192 bate com o membro editado (shasum -c e o gate da CI).
( cd "$WT" && shasum -a 256 -c "$MANIFEST" >/dev/null 2>&1 ) \
  || die "4d: shasum -a 256 -c $MANIFEST reprovou na arvore pos-patch — o sha do membro nao foi re-derivado"
ok "4d: manifesto ADR-192 casa o validate-governance.sh pos-patch"

# 4e — NAO-VACUO nomeado da wave: o id novo esta ausente em HEAD em TODOS os
# paths, e presente onde a wave diz que esta; floor/superseded contados.
NEW_ID="$(_expect EXPECTED_NEW_MODEL_ID)"
_head_refs=0
while IFS= read -r p; do
  [ -z "$p" ] && continue
  git cat-file -e "HEAD:$p" 2>/dev/null || continue
  _c="$( git show "HEAD:$p" | { grep -c -F -- "$NEW_ID" || true; } )"
  _head_refs=$(( _head_refs + _c ))
done < <( printf '%s\n' "$EXPECTED_SORTED" )
[ "$_head_refs" = "$(_expect EXPECTED_NEW_ID_REFS_HEAD)" ] \
  || die "4e: $NEW_ID aparece $_head_refs vez(es) em HEAD nos paths do patch, esperado $(_expect EXPECTED_NEW_ID_REFS_HEAD) (a wave nao e mais um append)"
_last1="$( jq -r '.availableModels[-1]' "$WT/$SETTINGS" )"
_last2="$( jq -r '.availableModels[-1]' "$WT/$TEMPLATE_BASE" )"
{ [ "$_last1" = "$NEW_ID" ] && [ "$_last2" = "$NEW_ID" ]; } \
  || die "4e: availableModels[-1] = $_last1/$_last2, esperado $NEW_ID (append at END)"
grep -qF -- "|$NEW_ID|" "$WT/$VALIDATE_SH" || die "4e: case-arm do $VALIDATE_SH sem |$NEW_ID|"
grep -qE "^    \"$NEW_ID\",$" "$WT/$TYPES_PY" || die "4e: VALID_MODEL_IDS em $TYPES_PY sem \"$NEW_ID\""
grep -qE "^ALLOWED_MODELS=\".* $NEW_ID .*\"$" "$WT/$PARITY_SH" || die "4e: ALLOWED_MODELS em $PARITY_SH sem $NEW_ID"
_bl="$( cd "$WT" && bash "$UPGRADE_SH" --print-settings-baselines )"
_bl_last="$( printf '%s' "$_bl" | jq -r '.availableModels.new[-1]' )"
[ "$_bl_last" = "$NEW_ID" ] || die "4e: upgrade.sh baseline new[-1] = $_bl_last, esperado $NEW_ID"
_sup_obs="$( printf '%s' "$_bl" | jq '.availableModels.superseded|length' )"
[ "$_sup_obs" = "$(_expect EXPECTED_SUPERSEDED_COUNT)" ] \
  || die "4e: superseded com $_sup_obs lista(s), esperado $(_expect EXPECTED_SUPERSEDED_COUNT)"
_floor_obs="$( awk '/^VETO_FLOOR_ALLOWED: frozenset = frozenset\(\{/{f=1;next} f&&/^\}\)/{exit} f&&/^[[:space:]]*"claude-/{n++} END{print n+0}' "$WT/$ADR" )"
[ "$_floor_obs" = "$(_expect EXPECTED_VETO_FLOOR_COUNT)" ] \
  || die "4e: VETO_FLOOR_ALLOWED com $_floor_obs membros, esperado $(_expect EXPECTED_VETO_FLOOR_COUNT) (rota c: o floor NAO muda)"
ok "4e: id ausente em HEAD, ULTIMO nos dois settings, presente nos 3 espelhos + baseline; floor=$_floor_obs; superseded=$_sup_obs"

# 4f — o gate estatico de harness-config sobre o settings POS-PATCH.
HC_LOG="$WT.harness-config.log"
HC_RC=0
( cd "$WT" && python3 .claude/hooks/check_harness_config.py ) > "$HC_LOG" 2>&1 || HC_RC=$?
[ "$HC_RC" = "$(_expect EXPECTED_HARNESS_CONFIG_RC)" ] || { tail -10 "$HC_LOG" | sed 's/^/      /' >&2
  die "4f: check_harness_config saiu rc=$HC_RC, esperado $(_expect EXPECTED_HARNESS_CONFIG_RC) — log em $HC_LOG"; }
ok "4f: harness-config gate verde sobre o settings pos-patch"

# 4g — o perfil user segue DERIVADO da base sem drift (a _derivation exclui
# availableModels: o template NAO deve mudar, e o --check prova).
UT_RC=0
( cd "$WT" && python3 "$GEN_USER" --check ) >/dev/null 2>&1 || UT_RC=$?
[ "$UT_RC" = "$(_expect EXPECTED_USER_TEMPLATE_CHECK_RC)" ] \
  || die "4g: gen-settings-user-template --check saiu rc=$UT_RC, esperado $(_expect EXPECTED_USER_TEMPLATE_CHECK_RC)"
ok "4g: settings.user.json == derivacao da base pos-patch"

# 4h — os 3 scripts shell tocados: shellcheck (warning+) e bash -n.
for sh in "$UPGRADE_SH" "$PARITY_SH" "$VALIDATE_SH"; do
  ( cd "$WT" && bash -n "$sh" ) || die "4h: bash -n reprovou em $sh"
  ( cd "$WT" && shellcheck -S warning "$sh" ) || die "4h: shellcheck reprovou em $sh"
done
ok "4h: shellcheck + bash -n verdes nos 3 scripts shell"

# 4i — o ratchet installer-write-safety: a wave toca scripts/, entao o gate e
# devido no MESMO patch. Medido: rc 0 SEM regenerar o baseline (edicoes de
# literal/branch nao criam sitio de escrita). Um sitio novo ficaria vermelho.
RT_RC=0
( cd "$WT" && python3 .claude/scripts/check-installer-write-safety.py ) >/dev/null 2>&1 || RT_RC=$?
[ "$RT_RC" = "$(_expect EXPECTED_RATCHET_RC)" ] \
  || die "4i: check-installer-write-safety saiu rc=$RT_RC, esperado $(_expect EXPECTED_RATCHET_RC).
  Se um sitio novo entrou, regenere o baseline no MESMO patch."
ok "4i: ratchet installer-write-safety verde (baseline intacto)"

# 4k — os gates de CORPUS, so sob --with-slow (rail r1 P2-7 do 179close: a
# 1a geracao de um clone DROPOU este bloco — WITH_SLOW parseado e nunca
# lido). Mesma leitura que o V8/V9 do LAND fazem.
if [ "$WITH_SLOW" = "1" ]; then
  printf '  4k: rodando os gates de corpus na arvore-sombra (~5 min)...\n'
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
  GOV_LOG="$WT.validate-governance.log"
  ( cd "$WT" && bash "$VALIDATE_SH" ) > "$GOV_LOG" 2>&1 \
    || { tail -20 "$GOV_LOG" | sed 's/^/      /' >&2; die "4k: validate-governance.sh FALHOU — log em $GOV_LOG"; }
  _gov_obs="$( { grep -oiE '^[[:space:]]*errors:[[:space:]]+[0-9]+' "$GOV_LOG" || true; } | { grep -oE '[0-9]+' || true; } | head -1 )"
  [ -n "$_gov_obs" ] || die "4k: nao consegui ler a contagem de erros em $GOV_LOG"
  [ "$_gov_obs" = "$(_expect EXPECTED_GOVERNANCE_ERRORS)" ] \
    || die "4k: validate-governance reporta $_gov_obs erro(s), esperado $(_expect EXPECTED_GOVERNANCE_ERRORS)"
  PS_LOG="$WT.parity-smoke.log"
  PS_RC=0
  ( cd "$WT" && bash "$PARITY_SH" ) > "$PS_LOG" 2>&1 || PS_RC=$?
  [ "$PS_RC" = "$(_expect EXPECTED_PARITY_SMOKE_RC)" ] \
    || { tail -12 "$PS_LOG" | sed 's/^/      /' >&2; die "4k: smoke-install-parity saiu rc=$PS_RC, esperado $(_expect EXPECTED_PARITY_SMOKE_RC) — log em $PS_LOG"; }
  BP_RC=0
  ( cd "$WT" && python3 scripts/build-plugin.py --check ) >/dev/null 2>&1 || BP_RC=$?
  [ "$BP_RC" = "$(_expect EXPECTED_BUILD_PLUGIN_CHECK_RC)" ] \
    || die "4k: build-plugin.py --check saiu rc=$BP_RC, esperado $(_expect EXPECTED_BUILD_PLUGIN_CHECK_RC)"
  ok "4k: claims, verify-counts, governanca completa, parity smoke e manifestos do plugin verdes"
else
  printf '  \033[33mNOTA\033[0m 4k: gates de corpus NAO executados (padrao). O V7/V8/V9 do LAND os rodam.\n'
  printf '        Para conferir antes da manha do Owner:\n'
  printf '          bash %s --with-slow\n' "$0"
fi

# ---------------------------------------------------------------------------
step "5 — patch, Scope, Patch-base e Patch-sha256"
# ---------------------------------------------------------------------------
# O HEAD pode ter ANDADO enquanto a bateria rodava. O `finalize_patch.py`
# recusa (corretamente) uma sombra cuja base nao seja o HEAD VIVO, mas a
# mensagem dele descreve o sintoma, nao a causa. Aqui a causa e NOMEADA.
HEAD_NOW="$( git rev-parse HEAD )"
if [ "$HEAD_NOW" != "$HEAD_SHA" ]; then
  die "o HEAD ANDOU enquanto a bateria rodava:
    quando este script comecou : $HEAD_SHA
    agora                      : $HEAD_NOW
  A arvore-sombra foi montada sobre o HEAD antigo, entao o patch descreveria
  outra base. Nada foi escrito. Rode este script DE NOVO."
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
# rail r4 (REDESENHO): o INDEX tambem e pre-estado. Captura o diff staged
# EXATO dos 4 materiais; o rollback zera o staged deles e RE-APLICA este
# patch — index-only content de terceiros sobrevive a qualquer abort.
if ! git diff --cached --binary -- "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE" \
       > "$_fin_bak/index-prestate.patch" 2>"$_fin_bak/index-capture.err"; then
  die "nao consegui capturar o pre-estado do INDEX dos materiais:
$( sed 's/^/    /' "$_fin_bak/index-capture.err" 2>/dev/null )
  Recusando mutar qualquer material. Resolva e re-rode."
fi
_fin_restore() {
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
# rail r6: a flag so liga quando captura E funcao existem.
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

# Conjunto de paths do patch FINAL == EXPECTED, nos dois sentidos.
PATCH_PATHS="$( git apply --numstat "$PATCH" | awk '{print $3}' | LC_ALL=C sort -u )"
_extra="$( comm -23 <( printf '%s\n' "$PATCH_PATHS" ) <( printf '%s\n' "$EXPECTED_SORTED" ) )"
[ -z "$_extra" ] || die "o patch toca path(s) fora do EXPECTED:
$( printf '  %s\n' $_extra )"
_ghost="$( comm -13 <( printf '%s\n' "$PATCH_PATHS" ) <( printf '%s\n' "$EXPECTED_SORTED" ) )"
if [ -n "$_ghost" ]; then
  die "path(s) do EXPECTED que o patch NAO toca:
$( printf '  %s\n' $_ghost )
  Ou o conteudo ja esta no HEAD (a cura landou parcialmente e o pacote ficou
  velho), ou a sombra perdeu a mudanca. Chame o CEO."
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
  _fin_ok=1
  warn "--no-commit: nada foi staged nem commitado."
  printf '        Os 4 materiais estao no disco, prontos para o commit de quem\n'
  printf '        estiver conduzindo a cerimonia:\n'
  for f in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE"; do
    printf '          %s\n' "$f"
  done
  printf '        O SIGN exige os materiais RASTREADOS — sem esse commit ele aborta.\n'
else
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
  git commit -q -m "chore(PLAN-169 s338-fable51): patch derivado da sombra e baseado em $HEAD_SHA (finalize-fable51.sh)" \
    || die "o commit falhou — o staging esta intacto; chame o CEO"
  _fin_ok=1
  ok "commit criado: $( git rev-parse --short HEAD )"
fi
fi

step "PRONTO"
cat <<EOF

  O pacote fable51 esta baseado em  $( git rev-parse HEAD )  e o patch aplica limpo.
    patch  : $PATCH
    sha256 : $NEW_PATCH_SHA
    paths  : $( printf '%s\n' "$PATCH_PATHS" | wc -l | tr -d ' ' )

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$SIGN_SCRIPT

EOF
