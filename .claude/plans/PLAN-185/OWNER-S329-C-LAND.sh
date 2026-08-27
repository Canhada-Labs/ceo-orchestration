#!/usr/bin/env bash
# OWNER-S329-C-LAND.sh — land do pacote de cerimonia wave-s329-C (PLAN-185).
# CEREMONY-LINT: handwritten-exception: clone gate-a-gate do OWNER-S329-E-LAND.sh
# (por sua vez provado num land REAL, 6304f66 / 738007e / 4bd7def / 3bc3638).
# Muda o bloco de constantes E o V-block, que aqui exercita o CONFINAMENTO DE
# ESCRITA DO INSTALLER — nao a derivacao do roster do pacote E: um V-block
# copiado testaria a coisa errada e seria verde vazio. O gerador
# `.claude/scripts/generate-ceremony.sh` NAO serve: ele assume o layout
# `architect/round-N/approved.md`, e esta cerimonia usa
# `PLAN-NNN/wave-*-approved.md` com land por PATCH. O G4 `touched - scope = 0`
# so existe automatizado nesta familia de scripts.
#
# Roda de QUALQUER diretorio. Nenhum passo e destrutivo antes de todos os
# gates passarem. Ao fim ele COMMITA (com -F, sem abrir editor) e EMPURRA.
#
# CUSTO: ~20 min. DOIS gates caros, e nenhum dos dois tem substituto barato.
#   V5 — o e2e de write-safety (~7 min, 13 installs reais). E o unico que
#        assere sobre BYTES no caminho EXTERNO, e isso importa porque o defeito
#        pre-cura sai 0: uma asercao de exit code teria passado contra ele.
#   V6 — o smoke-install (install real + paridade install/upgrade). Ele responde
#        a outra pergunta: a cura reescreve 26 hunks do caminho de escrita, e
#        "nao escreve fora" nao implica "continua instalando certo".
#
# Uso:
#   bash .claude/plans/PLAN-185/OWNER-S329-C-LAND.sh --dry-run
#   bash .claude/plans/PLAN-185/OWNER-S329-C-LAND.sh
set -euo pipefail

# --- argumentos -----------------------------------------------------------
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *)
      printf '\n\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$arg" >&2
      printf '  Formas validas:\n' >&2
      printf '    bash %s --dry-run\n' "$0" >&2
      printf '    bash %s\n' "$0" >&2
      exit 1 ;;
  esac
done

# A raiz resolve por git a partir da LOCALIZACAO DO SCRIPT, nunca por `../..`
# nem pelo cwd (licao S313).
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes da cerimonia (o UNICO bloco que muda entre waves) ----------
PLAN_DIR=".claude/plans/PLAN-185"
CEREMONY_DIR="$PLAN_DIR/s329-ceremony-C"
SENTINEL="$PLAN_DIR/wave-s329-C-approved.md"
PATCH="$CEREMONY_DIR/C.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-C.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S329-C-SIGN.sh"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
CENSUS=".claude/scripts/check-installer-write-safety.py"
E2E_TEST="scripts/tests/test-installer-write-safety-e2e.sh"
SMOKE_TEST="scripts/tests/smoke-install.sh"
LIB="scripts/_framework_manifest_set.sh"
INSTALLER="scripts/install.sh"
UPGRADER="scripts/upgrade.sh"
DOCTOR="scripts/doctor.sh"
YML_SMOKE=".github/workflows/smoke-install.yml"
YML_VALIDATE=".github/workflows/validate.yml"
CLAUDE_MD="CLAUDE.md"
PUSH_REMOTE="origin"
PUSH_BRANCH="main"
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
warn(){ printf '  \033[33mWARN\033[0m %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# --- interruptor de AUTO-TESTE (recusado fora do scratchpad) ---------------
SELFTEST=0
if [ "${CEREMONY_SELFTEST_NO_GPG:-}" = "1" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  case "$ROOT" in
    "$_sp_real"/claude-501/*/scratchpad/*) SELFTEST=1 ;;
    *) die "CEREMONY_SELFTEST_NO_GPG=1 RECUSADO: a arvore
  $ROOT
  nao esta sob o scratchpad de teste ($_sp_real/claude-501/*/scratchpad/).
  Este interruptor NAO existe para a arvore viva." ;;
  esac
  printf '\033[33m  MODO AUTO-TESTE\033[0m — GPG e push desligados.\n'
fi

# --- pulo dos gates CAROS: SO sob o auto-teste, e NOMEADO em voz alta ------
# Os dois juntos custam ~20 min. O harness precisa exercitar os gates sem
# paga-los a cada caso. O interruptor e DUPLAMENTE guardado: exige o auto-teste
# (que ja exige o scratchpad) E a variavel propria. Na arvore viva ele nao
# existe, entao um `export` esquecido no perfil do Owner nao consegue calar os
# dois unicos gates que provam a cura de ponta a ponta.
SKIP_SLOW=0
if [ "${CEO_C_HARNESS_SKIP_SLOW:-}" = "1" ]; then
  if [ "$SELFTEST" = "1" ]; then
    SKIP_SLOW=1
    printf '\033[33m  CEO_C_HARNESS_SKIP_SLOW=1\033[0m — V5 (e2e) e V6 (smoke) serao PULADOS.\n'
    printf '        So o harness usa isto. Um land REAL sempre roda os dois.\n'
  else
    die "CEO_C_HARNESS_SKIP_SLOW=1 RECUSADO fora do modo auto-teste.
  O e2e e o smoke-install sao os unicos gates que provam a cura de ponta a
  ponta. Nao ha rota para pula-los num land real."
  fi
fi

SHELLCHECK_STATUS="nao-executado"
E2E_STATUS="nao-executado"
SMOKE_STATUS="nao-executado"

# Leitor da base esperada: sem `source` (o arquivo nao executa nada), e
# fail-CLOSED quando a chave falta.
_expect() {
  _ev="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
  if [ -z "$_ev" ]; then
    die "chave '$1' AUSENTE em $BASELINE_ENV — o V-block nao compara contra nada"
  fi
  printf '%s' "$_ev"
}

# ---------------------------------------------------------------------------
step "G-PRE — substrato e base declarada"
# ---------------------------------------------------------------------------
[ -f "$BASELINE_ENV" ] || die "base esperada AUSENTE: $BASELINE_ENV
  Sem ela cada execucao do V-block e ruido. Rode o finalize-C.sh."
case "$(cat "$BASELINE_ENV")" in
  *TO-FILL-AT-FINALIZE*)
    die "G-PRE: o bloco AUTO de $BASELINE_ENV ainda tem placeholder.
  O G4 compararia o conjunto de paths contra a string literal
  'TO-FILL-AT-FINALIZE'. Rode o finalize-C.sh." ;;
esac

# O INSTRUMENTO DO CENSO e pinado por sha256. Contagens de instrumentos
# diferentes nao sao comparaveis: o DESIGN-C secao 7 mede `install.sh`
# desguardado 47 -> 44 com uma copia congelada, e o instrumento em HEAD rende
# 22 -> 18 nos MESMOS arquivos. Os dois estao certos; sao reguas diferentes.
[ -f "$CENSUS" ] || die "G-PRE: instrumento do censo ausente: $CENSUS"
_cs_obs="$( shasum -a 256 "$CENSUS" | awk '{print $1}' )"
_cs_exp="$(_expect EXPECTED_CENSUS_INSTRUMENT_SHA256)"
[ "$_cs_obs" = "$_cs_exp" ] || die "G-PRE: o instrumento do censo MUDOU depois da finalizacao.
    declarado: $_cs_exp
    no disco : $_cs_obs
  Rode o finalize-C.sh de novo: ele re-mede e aborta nomeando o que precisa ser
  atualizado conscientemente. NAO compare numeros de reguas diferentes."
ok "G-PRE: instrumento do censo casa o pin ($_cs_obs)"

for _t in python3 git shasum; do
  command -v "$_t" >/dev/null 2>&1 || die "G-PRE: ferramenta ausente: $_t"
done
ok "G-PRE: python3, git e shasum presentes"

# ---------------------------------------------------------------------------
step "G0 — insumos, materiais rastreados e arvore limpa"
# ---------------------------------------------------------------------------
# O commit avanca o HEAD ATUAL, e `git push origin main` empurra o ref LOCAL
# main — fora do main o push "sucede" sem levar o commit assinado. Fail-closed.
_cur_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '')"
[ "$_cur_branch" = "$PUSH_BRANCH" ] || die "HEAD esta em '$_cur_branch', nao em '$PUSH_BRANCH' — o land so roda no $PUSH_BRANCH (git checkout $PUSH_BRANCH)"
ok "G0: HEAD em $PUSH_BRANCH"

[ -f "$SENTINEL" ] || die "sentinel ausente: $SENTINEL"
[ -f "$PATCH" ]    || die "patch ausente: $PATCH"
[ -f "$SENTINEL.asc" ] || die "assinatura ausente: $SENTINEL.asc
  O Owner assina com:  bash $ROOT/$SIGN_SCRIPT"
[ -f "$COMMIT_MSG" ] || die "mensagem de commit ausente: $COMMIT_MSG"
[ -f "$ORACLE" ] || die "oraculo de canonicidade ausente: $ORACLE"
ok "sentinel, patch, .asc, mensagem e base esperada presentes"

# Os materiais tem de estar RASTREADOS: o commit do land stageia so o patch +
# sentinel + .asc, entao SIGN/LAND/patch/registros untracked deixariam o commit
# referenciando evidencia ausente do repositorio. Fail-closed aqui.
MATERIALS=(
  "$SIGN_SCRIPT"
  "$PLAN_DIR/OWNER-S329-C-LAND.sh"
  "$PROPOSED"
  "$COMMIT_MSG"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-C.sh"
  "$CEREMONY_DIR/test-ceremony-scripts-C.sh"
  "$CEREMONY_DIR/README-C.md"
  "$FINALIZE"
  "$PATCH"
  "$SENTINEL"
)
for m in "${MATERIALS[@]}"; do
  git ls-files --error-unmatch -- "$m" >/dev/null 2>&1 \
    || die "material de cerimonia NAO commitado: $m — commite os materiais antes de assinar/landar"
done
RAIL_COUNT=0
for r in $RAIL_GLOB; do
  [ -f "$r" ] || continue
  git ls-files --error-unmatch -- "$r" >/dev/null 2>&1 \
    || die "registro de rail NAO commitado: $r"
  RAIL_COUNT=$(( RAIL_COUNT + 1 ))
done
[ "$RAIL_COUNT" -gt 0 ] || die "nenhum registro de rail em $RAIL_GLOB"
ok "materiais e $RAIL_COUNT registro(s) de rail rastreados"

# Porcelain parsed NUL-delimited: o corte de 3 caracteres deixaria `old -> new`
# inteiro num rename, e o oraculo classificaria pelo path VELHO — um rename
# PARA dentro de .claude/hooks/ passaria como tolerado. Aqui: renames/copias
# ABORTAM, e path com newline ABORTA.
TMPDIR_LAND="$(mktemp -d)"
# Estado do trap declarado ANTES do trap: sob `set -u` uma variavel nao
# inicializada no handler mata o handler, e o dry-run deixaria o patch
# aplicado. O trap entra AQUI, nao depois dos gates.
APPLIED=0
RESTORE_ON_EXIT=0
FP_BEFORE=""
_fingerprint() {
  {
    git status --porcelain=v1
    printf -- '--index--\n'
    git diff --cached --name-status
  } | shasum -a 256 | awk '{print $1}'
}
_restore() {
  # exit status na ENTRADA do trap: != 0 significa que um die/abort disparou.
  # Logs caros so sao preservados nesse caso — um dry-run VERDE nao pode
  # deixar arquivo novo na arvore (o harness T2 confere byte a byte).
  _land_rc=$?
  if [ "$RESTORE_ON_EXIT" = "1" ] && [ "$APPLIED" = "1" ]; then
    git reset -q >/dev/null 2>&1 || true   # um abort DEPOIS do staging deixaria o index sujo
    if git apply -R "$PATCH" >/dev/null 2>&1; then
      APPLIED=0
      _fp_after="$(_fingerprint)"
      if [ "$_fp_after" = "$FP_BEFORE" ]; then
        printf '\033[32m  ok\033[0m  arvore e index restaurados byte a byte (patch revertido; nada foi commitado)\n'
      else
        printf '\n\033[31mRESTAURACAO INCOMPLETA\033[0m — o estado difere do inicial.\n' >&2
        printf '  Inspecione:  git -C %s status\n' "$ROOT" >&2
      fi
    else
      printf '\n\033[31mFALHA AO RESTAURAR\033[0m — a arvore ficou com o patch aplicado.\n' >&2
      printf '  Restaure a mao:  git -C %s apply -R %s\n' "$ROOT" "$PATCH" >&2
    fi
  fi
  # Licao S329-manha: o abort do V-block apagava o UNICO log do e2e junto com o
  # tmpdir -- o Owner ficou sem a assercao que falhou. Preserva os logs caros
  # (e2e/smoke) no dir de logs de cerimonia ANTES de remover o tmpdir.
  _keep_dir="$ROOT/.claude/plans/PLAN-185/s329-ceremony-main"
  if [ "$_land_rc" != "0" ] && [ -d "$TMPDIR_LAND" ] && [ -d "$_keep_dir" ] && [ -w "$_keep_dir" ]; then
    for _l in "$TMPDIR_LAND"/*.log; do
      [ -f "$_l" ] || continue
      _kept="$_keep_dir/land-C-$(date +%Y%m%d-%H%M%S)-$(basename "$_l")"
      cp -p "$_l" "$_kept" 2>/dev/null && printf '  log preservado: %s\n' "$_kept"
    done
  fi
  rm -rf "$TMPDIR_LAND"
}
trap _restore EXIT

DIRTY_FILE="$TMPDIR_LAND/dirty"
PATCHED_FILE="$TMPDIR_LAND/patched"
SCOPE_FILE="$TMPDIR_LAND/scope"
TOUCHED_FILE="$TMPDIR_LAND/touched"
EXPECTED_FILE="$TMPDIR_LAND/expected"
STAGED_FILE="$TMPDIR_LAND/staged"
: > "$DIRTY_FILE"
while IFS= read -r -d '' entry; do
  xy="${entry:0:2}"
  entry_path="${entry:3}"
  case "$xy" in
    *R*|*C*)
      IFS= read -r -d '' _renamed_from || true
      die "rename/copia na arvore suja ($xy: $_renamed_from -> $entry_path) — resolva (commit ou reverta) antes do land" ;;
  esac
  # `$(printf '\n')` NAO serve aqui: a substituicao come a newline final, o
  # padrao vira `**` e TODO path passaria a "conter newline" (medido).
  case "$entry_path" in
    *$'\n'*) die "path com newline na arvore suja — recusado" ;;
  esac
  printf '%s\n' "$entry_path" >> "$DIRTY_FILE"
done < <(git status --porcelain=v1 -z)
sort -u -o "$DIRTY_FILE" "$DIRTY_FILE"

git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$PATCHED_FILE"
COLLIDE="$(comm -12 "$DIRTY_FILE" "$PATCHED_FILE")"
if [ -n "$COLLIDE" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "arquivo(s) do patch estao MODIFICADOS na arvore:
$(printf '  %s\n' $COLLIDE)
  O patch aterrissaria sobre conteudo diferente do assinado.
  Commite ou reverta esses arquivos antes do land."
fi

# Allowlist FECHADA: so os artefatos da propria cerimonia podem estar sujos
# entre os paths guardados. A canonicidade de cada path sujo vem do ORACULO
# (a mesma _CANONICAL_GUARDS que o hook aplica) — NUNCA de uma lista espelhada
# aqui: o espelho da S326 omitia superficies guardadas. Oraculo indisponivel
# => ABORTA.
CEREMONY_OK=(
  "$SENTINEL"
  "$SENTINEL.asc"
  "$PATCH"
)
GUARDED_DIRTY=""
OTHER_DIRTY=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  skip=0
  for allowed in "${CEREMONY_OK[@]}"; do
    if [ "$f" = "$allowed" ]; then skip=1; break; fi
  done
  [ "$skip" = "1" ] && continue
  verdict="$(python3 "$ORACLE" --is-canonical "$f" 2>/dev/null | awk -F'\t' 'NR==1{print $2}')"
  case "$verdict" in
    1) GUARDED_DIRTY="$GUARDED_DIRTY  $f
" ;;
    0) OTHER_DIRTY="$OTHER_DIRTY  $f
" ;;
    *) die "oraculo de canonicidade nao respondeu 0|1 para: $f (saida: '$verdict')" ;;
  esac
done < "$DIRTY_FILE"

if [ -n "$GUARDED_DIRTY" ]; then
  die "path(s) CANONICOS sujos fora do Scope assinado:
$GUARDED_DIRTY  Commite-os SEPARADAMENTE antes, ou inclua-os no Scope e re-assine."
fi
if [ -n "$OTHER_DIRTY" ]; then
  warn "mudancas nao-guardadas fora do patch (toleradas, NAO entram no commit):"
  printf '%s' "$OTHER_DIRTY"
fi
ok "nenhum arquivo do patch sujo; nenhum path canonico sujo fora do Scope"

# ---------------------------------------------------------------------------
step "G1 — assinatura GPG + ancora"
# ---------------------------------------------------------------------------
if [ "$SELFTEST" = "1" ]; then
  warn "AUTO-TESTE: verificacao GPG PULADA (o .asc e sintetico)"
else
  gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /' \
    || die "assinatura GPG NAO verifica"
  ok "assinatura verificada"

  if [ -f "$SIGNERS" ]; then
    # Sem `grep | head || true`: sob pipefail o `head` mata o produtor com
    # SIGPIPE(141) e o `|| true` mascara a diferenca entre "nao achou" e
    # "morreu". awk casa e sai por conta propria, exit 0 sempre.
    GPG_OUT="$(gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1)"
    FPR="$(printf '%s\n' "$GPG_OUT" \
           | awk 'match($0, /[A-F0-9]{40}/) { print substr($0, RSTART, RLENGTH); exit }')"
    [ -n "$FPR" ] || die "nao consegui extrair o fingerprint da assinatura"
    grep -qi "$FPR" "$SIGNERS" || die "fingerprint $FPR NAO consta em $SIGNERS"
    ok "signer $FPR consta no rail rastreado"
  else
    warn "$SIGNERS ausente — rail de signer nao verificado"
  fi
fi

# Campos obrigatorios preenchidos (um sentinel com placeholder foi assinado
# antes da finalizacao — a assinatura seria valida e a autorizacao, vazia).
for field in "Approved-By" "Anchor-SHA" "Data" "Patch-sha256" "Patch-base"; do
  val="$(grep -m1 "^$field:" "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
  [ -n "$val" ] || die "sentinel sem campo '$field:'"
  case "$val" in
    *TO-FILL*) die "campo '$field:' ainda e placeholder ($val) — o sentinel nao foi assinado pelo SIGN" ;;
  esac
done

ANCHOR="$(grep -m1 '^Anchor-SHA:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
HEAD_SHA="$(git rev-parse HEAD)"
[ "$ANCHOR" = "$HEAD_SHA" ] || die "Anchor-SHA nao bate com HEAD
  ancora: $ANCHOR
  HEAD  : $HEAD_SHA
  Commits entraram depois da assinatura. Re-gere o Anchor e RE-ASSINE."
ok "ancora casa HEAD ($HEAD_SHA)"

# ---------------------------------------------------------------------------
step "G2 — binding do patch (Patch-sha256)"
# ---------------------------------------------------------------------------
DECLARED="$(grep -m1 '^Patch-sha256:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
ACTUAL="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
[ "$DECLARED" = "$ACTUAL" ] || die "patch NAO bate com o sentinel assinado
  declarado: $DECLARED
  real     : $ACTUAL
  O patch mudou depois da assinatura. Re-assine ou restaure o patch."
ok "patch casa o sha256 assinado ($ACTUAL)"

# ---------------------------------------------------------------------------
step "G3 — o patch aplica limpo (modo checagem, nada muda ainda)"
# ---------------------------------------------------------------------------
git apply --check "$PATCH" || die "git apply --check FALHOU — a arvore divergiu do patch"
ok "aplica limpo"

# ---------------------------------------------------------------------------
step "G4 — touched == scope (NOS DOIS SENTIDOS)"
# ---------------------------------------------------------------------------
# Sem filtro de canonicidade: TODO path tocado tem de estar no Scope assinado,
# canonico ou nao. E o inverso tambem e fatal — um Scope que autoriza o que o
# patch nao toca e uma autorizacao mais larga do que a revisao.
awk '/BEGIN SIGNED SCOPE/{f=1;next} /END SIGNED SCOPE/{f=0} f' "$SENTINEL" \
  | sed -n 's/^[[:space:]]*-[[:space:]]*//p' | sed 's/[[:space:]]*$//' \
  | sort -u > "$SCOPE_FILE"
[ -s "$SCOPE_FILE" ] || die "bloco Scope vazio ou nao encontrado no sentinel"

git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$TOUCHED_FILE"
[ -s "$TOUCHED_FILE" ] || die "o patch nao toca arquivo nenhum"

EXTRA="$(comm -23 "$TOUCHED_FILE" "$SCOPE_FILE")"
if [ -n "$EXTRA" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "o patch toca path(s) FORA do Scope assinado:
$(printf '  %s\n' $EXTRA)
  Um Scope que nao cobre um path tocado invalida a autorizacao."
fi
GHOST="$(comm -13 "$TOUCHED_FILE" "$SCOPE_FILE")"
if [ -n "$GHOST" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "o Scope autoriza path(s) que o patch NAO toca:
$(printf '  %s\n' $GHOST)
  Autorizacao mais larga do que o patch revisado. Refinalize o patch
  (finalize_patch.py deriva o Scope) e RE-ASSINE."
fi
ok "$(wc -l < "$TOUCHED_FILE" | tr -d ' ') path(s): touched == scope nos dois sentidos"

# Defesa em profundidade sobre o mesmo par que o SIGN checou: a base do patch
# e ancestral do HEAD e nenhum path tocado derivou entre as duas.
PATCH_BASE="$(grep -m1 '^Patch-base:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
git merge-base --is-ancestor "$PATCH_BASE" "$HEAD_SHA" \
  || die "a base do patch ($PATCH_BASE) NAO e ancestral do HEAD ($HEAD_SHA)"
git diff --name-only "$PATCH_BASE" "$HEAD_SHA" | sort -u > "$TMPDIR_LAND/drift"
DRIFTED="$(comm -12 "$TMPDIR_LAND/drift" "$TOUCHED_FILE")"
if [ -n "$DRIFTED" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "path(s) do patch mudaram entre a base assinada e o HEAD:
$(printf '  %s\n' $DRIFTED)
  O patch foi revisado sobre outro conteudo."
fi
ok "base $PATCH_BASE ancestral do HEAD; nenhum path do patch derivou"

# Conjunto EXATO de paths tocados, contra o bloco AUTO que o finalize derivou e
# que a assinatura congelou. Uma cerimonia que so CONTA arquivos aceitaria um
# patch com o mesmo numero de paths ERRADOS.
_exp_paths="$(_expect EXPECTED_PATCH_PATHS | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u)"
_obs_paths="$(LC_ALL=C sort -u "$TOUCHED_FILE")"
[ "$_obs_paths" = "$_exp_paths" ] || die "G4: conjunto de paths tocados difere do DECLARADO
  declarado: $(printf '%s' "$_exp_paths" | tr '\n' ' ')
  observado: $(printf '%s' "$_obs_paths" | tr '\n' ' ')"
ok "G4: conjunto de paths casa EXPECTED_PATCH_PATHS"

# E os obrigatorios continuam todos presentes. O bloco AUTO e derivado; esta
# linha e a que carrega o JULGAMENTO humano sobre o que o pacote precisa
# entregar — sem ela um finalize rodado com a metade de CI faltando produziria
# um conjunto AUTO menor, coerente consigo mesmo, e o G4 passaria.
# Os OBRIGATORIOS da sombra MAIS os GERADOS pelo finalize. O ratchet do censo
# nasce no finalize, nao na sombra, mas ele e tao obrigatorio quanto o resto: um
# patch sem ele deixa o step do censo do validate.yml vermelho no push.
_req_paths="$( { _expect REQUIRED_PATCH_PATHS; printf ' '; _expect GENERATED_PATCH_PATHS; } \
               | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u)"
# LC_ALL=C nos DOIS lados: `comm` exige a MESMA ordenacao nas duas entradas, e
# o TOUCHED_FILE foi ordenado com o `sort` do locale corrente. Misturar
# colacoes faz o `comm` reportar diferencas que nao existem.
_missing_req="$(LC_ALL=C comm -13 <(LC_ALL=C sort -u "$TOUCHED_FILE") <(printf '%s\n' "$_req_paths"))"
if [ -n "$_missing_req" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "G4: path(s) OBRIGATORIO(s) ausentes do patch:
$(printf '  %s\n' $_missing_req)
  A metade de CI/docs deste pacote (workflows, threat-model, ADR-196) nao pode
  ficar de fora: um teste sem wiring de CI e um teste que nunca roda."
fi
ok "G4: os $(printf '%s\n' "$_req_paths" | wc -l | tr -d ' ') path(s) obrigatorios estao no patch"

# ---------------------------------------------------------------------------
step "G5 — grants do sentinel + coerencia do manifesto ADR-192"
# ---------------------------------------------------------------------------
# Assinatura GPG valida NAO e autorizacao mecanica (licao S318: um sentinel
# verificou e concedia ZERO paths). Aqui cada path CANONICO tocado e provado
# concedido pela MESMA funcao que o hook usa, `_sentinel_grants_path`.
if [ "$SELFTEST" = "1" ]; then
  # O unlock exige PROVENIENCIA: sem ela ele nega tudo e o G5 reprovaria por
  # motivo ERRADO, deixando o controle positivo do parse de Scope VACUO. Com o
  # digest fixado nos bytes EM DISCO, quem decide volta a ser o parse do Scope.
  SELFTEST_SENTINEL_SHA="$(shasum -a 256 "$SENTINEL" | awk '{print $1}')"
  G5_ENV=(env "CEO_SENTINEL_UNLOCK=PLAN-185-installer-write-safety" \
              "CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT" \
              "CEO_SENTINEL_UNLOCK_SHA256=$SELFTEST_SENTINEL_SHA")
else
  G5_ENV=(env)
fi
"${G5_ENV[@]}" python3 - "$ROOT" "$SENTINEL" "$TOUCHED_FILE" "$MANIFEST" <<'PY' || die "G5 reprovou"
import importlib.util, os, sys
from pathlib import Path

root, sentinel_rel, touched_file, manifest_rel = sys.argv[1:5]
os.environ["CLAUDE_PROJECT_DIR"] = root
sys.path.insert(0, os.path.join(root, ".claude", "hooks"))
spec = importlib.util.spec_from_file_location(
    "_cce_land", os.path.join(root, ".claude/hooks/check_canonical_edit.py"))
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception as exc:
    sys.exit("nao consegui carregar o oraculo de sentinel: %r" % (exc,))

sentinel = Path(root) / sentinel_rel
repo_root = Path(root)
with open(touched_file, encoding="utf-8") as fh:
    touched = [ln.strip() for ln in fh if ln.strip()]

canonical, ungranted = [], []
for rel in touched:
    try:
        is_canon = mod._is_canonical(rel, repo_root)
    except Exception:
        is_canon = True          # fail-CLOSED: inclassificavel conta como canonico
    if not is_canon:
        continue
    canonical.append(rel)
    if not mod._sentinel_grants_path(sentinel, rel):
        ungranted.append(rel)

if ungranted:
    sys.stderr.write(
        "  paths CANONICOS tocados que o sentinel NAO concede:\n"
        + "".join("    %s\n" % p for p in ungranted)
        + "  Assinatura valida que concede zero paths nao autoriza nada (S318).\n")
    sys.exit(1)

# Membro do manifesto ADR-192 tocado exige bump do sha NO MESMO patch.
members = set()
with open(os.path.join(root, manifest_rel), encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            members.add(parts[1].strip())
touched_members = sorted(set(touched) & members)
if touched_members and manifest_rel not in set(touched):
    sys.stderr.write(
        "  membro(s) do manifesto ADR-192 tocado(s) sem tocar o manifesto:\n"
        + "".join("    %s\n" % p for p in touched_members)
        + "  O oraculo responde 0 para um membro, mas editar membro passa pela\n"
          "  cerimonia E exige bump do sha em %s (licao S326).\n" % manifest_rel)
    sys.exit(1)

print("  %d path(s) canonico(s), todos concedidos pelo sentinel" % len(canonical))
print("  %d membro(s) do manifesto ADR-192 tocado(s)" % len(touched_members))
PY
ok "grants provados e manifesto estruturalmente coerente"

# O NUMERO de paths canonicos tambem e comparado, contra o valor DERIVADO pelo
# finalize E contra o piso HUMANO. Sem isto, um patch que perdesse os tres
# escritores de `scripts/` e carregasse so os testes passaria pelo bloco acima:
# zero canonicos tocados e trivialmente "todos concedidos".
_obs_canon="$(python3 - "$ROOT" "$TOUCHED_FILE" <<'PY'
import importlib.util, os, sys
from pathlib import Path
root, touched_file = sys.argv[1:3]
os.environ["CLAUDE_PROJECT_DIR"] = root
sys.path.insert(0, os.path.join(root, ".claude", "hooks"))
spec = importlib.util.spec_from_file_location(
    "_cce_count", os.path.join(root, ".claude/hooks/check_canonical_edit.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
with open(touched_file, encoding="utf-8") as fh:
    touched = [ln.strip() for ln in fh if ln.strip()]
n = 0
for rel in touched:
    try:
        if mod._is_canonical(rel, Path(root)):
            n += 1
    except Exception:
        n += 1        # fail-CLOSED
print(n)
PY
)"
_exp_canon="$(_expect EXPECTED_PATCH_CANONICAL_PATHS)"
[ "$_obs_canon" = "$_exp_canon" ] \
  || die "G5: $_obs_canon path(s) CANONICOS no patch, esperado $_exp_canon (bloco AUTO).
  Menos significa que o alvo canonico da wave saiu do patch; mais significa que
  o patch cresceu para superficie que a revisao nao leu."
_min_canon="$(_expect EXPECTED_PATCH_CANONICAL_MIN)"
[ "$_obs_canon" -ge "$_min_canon" ] \
  || die "G5: $_obs_canon path(s) CANONICOS, piso HUMANO $_min_canon.
  Os tres escritores de scripts/, os dois workflows e o ADR sao canonicos: um
  pacote com menos que isso nao entrega a wave."
ok "G5: $_obs_canon path(s) canonico(s) (AUTO $_exp_canon, piso $_min_canon)"

# O numero de membros do manifesto tocados tambem e comparado: o bloco acima so
# aborta quando ha membro tocado SEM o manifesto no patch; se um membro entrasse
# no patch em silencio, o gate estrutural passaria.
_obs_members="$(python3 - "$ROOT" "$TOUCHED_FILE" "$MANIFEST" <<'PY'
import os, sys
root, touched_file, manifest_rel = sys.argv[1:4]
members = set()
with open(os.path.join(root, manifest_rel), encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            members.add(parts[1].strip())
with open(touched_file, encoding="utf-8") as fh:
    touched = {ln.strip() for ln in fh if ln.strip()}
print(len(touched & members))
PY
)"
_exp_members="$(_expect EXPECTED_MANIFEST_MEMBERS_TOUCHED)"
[ "$_obs_members" = "$_exp_members" ] \
  || die "G5: $_obs_members membro(s) do manifesto ADR-192 tocado(s), esperado $_exp_members"
ok "G5: membros do manifesto tocados = $_obs_members (esperado $_exp_members)"

# ---------------------------------------------------------------------------
# Impressao digital PRE-mutacao (arvore + index), tirada AGORA — depois de
# todos os gates e antes da primeira mutacao. O `--dry-run` aplica o patch de
# verdade para rodar V1..V4 sobre o conteudo REAL pos-patch, e restaura no trap
# (dry-run que deixa `git apply` no index e a armadilha da S272).
# ---------------------------------------------------------------------------
FP_BEFORE="$(_fingerprint)"

# ---------------------------------------------------------------------------
step "APLICANDO o patch assinado"
# ---------------------------------------------------------------------------
# S327 (abort real medido): o primeiro land REAL abortou no V4 e deixou a arvore
# com o patch aplicado — so o dry-run restaurava. Agora TODO abort depois do
# apply restaura arvore e index; o land bem-sucedido desliga o restore logo
# apos o commit.
RESTORE_ON_EXIT=1
git apply "$PATCH"
APPLIED=1
ok "patch aplicado ($(wc -l < "$TOUCHED_FILE" | tr -d ' ') paths)"

# ---------------------------------------------------------------------------
step "V1 — sintaxe dos scripts shell tocados"
# ---------------------------------------------------------------------------
SH_COUNT=0
SH_LIST="$TMPDIR_LAND/shfiles"
: > "$SH_LIST"
while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ -f "$f" ] || continue
  case "$f" in
    *.sh) printf '%s\n' "$f" >> "$SH_LIST"; SH_COUNT=$(( SH_COUNT + 1 )) ;;
    *)
      head_line="$(head -1 "$f" 2>/dev/null || printf '')"
      case "$head_line" in
        "#!"*sh*) printf '%s\n' "$f" >> "$SH_LIST"; SH_COUNT=$(( SH_COUNT + 1 )) ;;
      esac ;;
  esac
done < "$TOUCHED_FILE"
# Este pacote SEMPRE toca quatro scripts shell (a biblioteca, os dois
# escritores e o e2e). Um numero diferente aqui e o V1 medindo a coisa errada,
# nao "nada a fazer" — e o step de shellcheck do validate.yml varre so
# `.claude/scripts` e `.claude/hooks`, entao `scripts/` NAO tem outra cobertura
# (FU-4 do DESIGN-C). Este V1 e a unica rede.
_sh_exp="$(_expect EXPECTED_SHELL_FILES_IN_PATCH)"
[ "$SH_COUNT" = "$_sh_exp" ] || die "V1: $SH_COUNT script(s) shell no patch, esperado $_sh_exp
  ($LIB, $INSTALLER, $UPGRADER e $E2E_TEST). Um V1 vazio e um gate morto."
while IFS= read -r f; do
  bash -n "$f" || die "V1a: 'bash -n' reprovou em $f"
done < "$SH_LIST"
ok "V1a: bash -n verde em $SH_COUNT script(s)"
if command -v shellcheck >/dev/null 2>&1; then
  while IFS= read -r f; do
    shellcheck -S warning "$f" || die "V1b: shellcheck reprovou em $f"
  done < "$SH_LIST"
  SHELLCHECK_STATUS="verde ($SH_COUNT arquivo(s))"
  ok "V1b: shellcheck verde em $SH_COUNT script(s)"
else
  SHELLCHECK_STATUS="INDISPONIVEL nesta maquina — o CI NAO cobre scripts/ (FU-4)"
  warn "V1b: shellcheck AUSENTE — e o validate.yml varre so .claude/; scripts/ fica SEM cobertura"
fi

# ---------------------------------------------------------------------------
step "V2 — os workflows pos-patch sao validos E enxergam o teste"
# ---------------------------------------------------------------------------
# Roda no dry-run TAMBEM: e barato, e e o gate que pega um patch que quebrou o
# YAML — exatamente o erro que so apareceria no push.
for y in "$YML_SMOKE" "$YML_VALIDATE"; do
  [ -f "$y" ] || die "V2: workflow ausente pos-patch: $y"
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$y" 2>/dev/null \
    && ok "V2a: yaml.safe_load OK em $y" \
    || warn "V2a: PyYAML ausente ou parse falhou em $y — o actionlint abaixo tambem cobre"
done
if command -v actionlint >/dev/null 2>&1; then
  for y in "$YML_SMOKE" "$YML_VALIDATE"; do
    actionlint "$y" > "$TMPDIR_LAND/actionlint.log" 2>&1 || {
      sed 's/^/    /' "$TMPDIR_LAND/actionlint.log" >&2
      die "V2b: actionlint reprovou em $y"; }
  done
  ok "V2b: actionlint verde nos 2 workflows"
else
  warn "V2b: actionlint AUSENTE — o CI executa"
fi
# `unwired = no test` e a regra escrita no proprio workflow. As referencias
# esperadas sao: lista de paths do `pull_request`, lista de paths do `push`, e o
# step que EXECUTA. Faltando um filtro, o job nao dispara quando o teste muda;
# faltando o step, o teste nao roda. Contagem DECLARADA, nunca ">0".
_refs_obs="$(grep -cF -- "$(basename "$E2E_TEST")" "$YML_SMOKE" || true)"
_refs_exp="$(_expect EXPECTED_YML_E2E_REFS)"
[ "$_refs_obs" = "$_refs_exp" ] \
  || die "V2c: $(basename "$E2E_TEST") aparece $_refs_obs vez(es) em $YML_SMOKE, esperado $_refs_exp.
  Sem as DUAS listas de paths e o step, a cura entra sem vigilancia e a classe
  volta — e o FU-2 do DESIGN-C."
ok "V2c: o smoke-install.yml referencia o e2e $_refs_obs vez(es)"
_to_obs="$(grep -m1 'timeout-minutes:' "$YML_SMOKE" | sed 's/[^0-9]//g')"
_to_exp="$(_expect EXPECTED_YML_TIMEOUT_MINUTES)"
[ "$_to_obs" = "$_to_exp" ] \
  || die "V2d: timeout-minutes do job e $_to_obs, esperado $_to_exp.
  Um timeout de job que corta um run VERDE aparece como 'cancelled' num passo
  INOCENTE. Re-apertar so no p95 real de CI, nunca na aritmetica."
ok "V2d: timeout-minutes = $_to_obs (esperado $_to_exp)"
_cen_obs="$(grep -cF -- "$(basename "$CENSUS" .py)" "$YML_VALIDATE" || true)"
_cen_exp="$(_expect EXPECTED_VALIDATE_YML_CENSUS_REFS)"
[ "$_cen_obs" = "$_cen_exp" ] \
  || die "V2e: o censo aparece $_cen_obs vez(es) em $YML_VALIDATE, esperado $_cen_exp.
  Sem a linha do censo no validate.yml (FU-3), a contagem de sitios inseguros
  nao vira ratchet e um sitio NOVO entra calado."
ok "V2e: o validate.yml referencia o censo $_cen_obs vez(es)"

# ---------------------------------------------------------------------------
step "V3 — o predicado compartilhado (o invariante anti-rot desta wave)"
# ---------------------------------------------------------------------------
# A classe que esta wave fecha nao e "falta uma guarda": e "cada escritor tem a
# SUA guarda, e elas divergem". A cura poe UM predicado numa biblioteca e faz os
# escritores o consultarem. Um segundo corpo dentro de install.sh ou upgrade.sh
# recria exatamente a forma dos quatro defeitos D1..D4 da S323.
PRED="$(_expect EXPECTED_PREDICATE_NAME)"
PRED_FILE="$(_expect EXPECTED_PREDICATE_DEFINITION_FILE)"
_defs_total=0
for f in "$LIB" "$INSTALLER" "$UPGRADER"; do
  [ -f "$f" ] || die "V3: arquivo ausente pos-patch: $f"
  _n="$( grep -c "^${PRED}() {" "$f" || true )"
  _defs_total=$(( _defs_total + _n ))
  if [ "$f" != "$PRED_FILE" ] && [ "$_n" != "0" ]; then
    die "V3: $f DEFINE $PRED ($_n vez(es)).
  O predicado vive numa biblioteca e os escritores o CONSULTAM. Um segundo
  corpo aqui recria a classe das copias divergentes que esta wave fecha."
  fi
done
_defs_exp="$(_expect EXPECTED_PREDICATE_DEFINITIONS_TOTAL)"
[ "$_defs_total" = "$_defs_exp" ] \
  || die "V3: $PRED e definido $_defs_total vez(es), esperado $_defs_exp.
  Zero significa que a ancora nao casou (gate VERDE medindo nada) ou que a
  definicao sumiu; mais de um e a classe renascendo."
_consumers=0
for f in "$INSTALLER" "$UPGRADER"; do
  _n="$( grep -c -- "$PRED" "$f" || true )"
  [ "$_n" -ge 1 ] || die "V3: $f NAO referencia $PRED.
  Um consumidor com zero referencias e um consumidor que nao consome: o
  predicado existiria e nao guardaria nada."
  _consumers=$(( _consumers + 1 ))
done
_cons_exp="$(_expect EXPECTED_PREDICATE_CONSUMER_FILES)"
[ "$_consumers" = "$_cons_exp" ] \
  || die "V3: $_consumers consumidor(es) do predicado, esperado $_cons_exp"
ok "V3: $PRED definido 1x em $PRED_FILE e consumido por $_consumers arquivo(s)"
if [ -f "$DOCTOR" ]; then
  _doc_obs="$( grep -c -- "$PRED" "$DOCTOR" || true )"
  _doc_exp="$(_expect EXPECTED_PREDICATE_DOCTOR_REFS)"
  [ "$_doc_obs" = "$_doc_exp" ] \
    || die "V3: $DOCTOR referencia $PRED $_doc_obs vez(es), declarado $_doc_exp.
  Se o doctor foi convertido (FU-7 do DESIGN-C), isso e boa noticia — mas e
  mudanca de escopo: atualize $BASELINE_ENV conscientemente."
  ok "V3: $DOCTOR referencia o predicado $_doc_obs vez(es) (FU-7 aberto por desenho)"
fi

# ---------------------------------------------------------------------------
step "V4 — o censo de escrita insegura (ratchet, NUNCA contra zero)"
# ---------------------------------------------------------------------------
CEN_JSON="$TMPDIR_LAND/census.json"
CEN_RC=0
python3 "$CENSUS" --repo-root "$ROOT" --json > "$CEN_JSON" 2>"$TMPDIR_LAND/census.err" || CEN_RC=$?
_cen="$(python3 - "$CEN_JSON" <<'PY' || printf ''
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
c = d["counts"]
print("%d %d %d %d" % (c["desguardado"], c["sites"],
                       len(d["new_blocking"]), len(d["dead_baseline_entries"])))
PY
)"
[ -n "$_cen" ] || { sed 's/^/    /' "$TMPDIR_LAND/census.err" >&2
                    die "V4: nao consegui ler o censo — saida em $CEN_JSON"; }
set -- $_cen
_c_desg="$1"; _c_sites="$2"; _c_new="$3"; _c_dead="$4"

# ---------------------------------------------------------------------------
# A pergunta CENTRAL, e ela e literalmente a que o CI fara.
# ---------------------------------------------------------------------------
# O `validate.yml` deste patch instala um step que roda este mesmo comando, sem
# flags, com `set -euo pipefail` e SEM `continue-on-error`. Se ele sai != 0
# aqui, ele sai != 0 la — e o main fica vermelho no primeiro push, por um gate
# que o proprio commit instalou. O `finalize-C.sh` REGENERA o baseline do
# ratchet dentro do patch exatamente para que esta checagem passe; se ela falha,
# ou o finalize nao rodou, ou o corpus andou depois dele.
if [ "$(_expect EXPECTED_CENSUS_RATCHET_CLEAN)" = "1" ]; then
  if [ "$CEN_RC" != "0" ] || [ "$_c_new" != "0" ] || [ "$_c_dead" != "0" ]; then
    die "V4: o RATCHET do censo NAO esta limpo na arvore patchada.
    rc                    : $CEN_RC
    new_blocking          : $_c_new
    dead_baseline_entries : $_c_dead

  Este e o MESMO comando que o step do validate.yml deste patch executa
  fail-closed. Landar assim deixa o Validate VERMELHO no main no primeiro push,
  por um gate que este proprio commit instala — a classe que manteve o main
  vermelho da S322 a S327.

  A CURA: rode o finalize-C.sh de novo (ele regenera o baseline do ratchet
  dentro do patch) e RE-ASSINE. Se ele ja rodou, entao o corpus scripts/ andou
  entre a finalizacao e agora — o que tambem exige refinalizar.
  Saida completa do censo: $CEN_JSON"
  fi
  ok "V4: ratchet LIMPO (rc=$CEN_RC, 0 nova(s), 0 morta(s)) — o step do CI sai verde"
fi

# Piso de nao-vacuidade: zero sitios significa que a BUSCA quebrou, nao que o
# corpus esta limpo — o proprio instrumento diz isso e sai 2.
_sites_min="$(_expect EXPECTED_CENSUS_SITES_MIN)"
[ "$_c_sites" -ge "$_sites_min" ] \
  || die "V4: o censo achou so $_c_sites sitio(s), minimo $_sites_min.
  Um gate verde sobre um censo vazio e o pior resultado possivel."

# Contagens EXATAS contra o que o finalize mediu e a assinatura congelou. Sem
# isto o V4 aceitaria qualquer corpus, desde que o ratchet estivesse limpo — e
# um ratchet regenerado esta SEMPRE limpo, entao a checagem acima sozinha seria
# quase tautologica. Estas duas linhas sao o que a torna nao-vacua.
_desg_pos="$(_expect EXPECTED_CENSUS_DESGUARDADO_POS)"
[ "$_c_desg" = "$_desg_pos" ] \
  || die "V4: $_c_desg sitio(s) desguardado(s), o finalize mediu $_desg_pos.
  O corpus scripts/ mudou entre a finalizacao e o land. Refinalize e RE-ASSINE."
_sites_pos="$(_expect EXPECTED_CENSUS_SITES_POS)"
[ "$_c_sites" = "$_sites_pos" ] \
  || die "V4: o censo achou $_c_sites sitio(s), o finalize mediu $_sites_pos.
  O corpus scripts/ mudou entre a finalizacao e o land. Refinalize e RE-ASSINE."

# A DIRECAO: a cura nao pode AUMENTAR o numero de desguardados.
if [ "$(_expect EXPECTED_CENSUS_DESGUARDADO_MUST_NOT_INCREASE)" = "1" ]; then
  _desg_pre="$(_expect EXPECTED_CENSUS_DESGUARDADO_PRE)"
  [ "$_c_desg" -le "$_desg_pre" ] \
    || die "V4: desguardado subiu de $_desg_pre (pre-cura) para $_c_desg.
  A cura ABRIU sitio(s) de escrita sem guarda — o inverso do que a wave existe
  para fazer. NAO landar."
  ok "V4: desguardado $_desg_pre -> $_c_desg (nao aumentou), sites=$_c_sites"
fi

if [ "$DRY_RUN" = "1" ]; then
  printf '\n\033[33mDRY-RUN\033[0m — G-PRE, G0..G5 verdes; patch aplicado; V1..V4 executados.\n'
  printf '  O V-block CARO (V5 e2e ~7 min, V6 smoke-install, V7 governanca) NAO roda em dry-run.\n'
  printf '  Restaurando arvore e index...\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "V5 — e2e de write-safety (~7 min; o gate que assere sobre BYTES)"
# ---------------------------------------------------------------------------
if [ "$SKIP_SLOW" = "1" ]; then
  E2E_STATUS="PULADO por CEO_C_HARNESS_SKIP_SLOW=1 (so o harness)"
  warn "V5 PULADO — CEO_C_HARNESS_SKIP_SLOW=1 sob o modo auto-teste."
  warn "        Isto NAO e possivel num land real; o gate abortaria antes."
else
  printf '  isto demora ~7 min (15 fixtures, aprox. 13 installs reais)...\n'
  E2E_LOG="$TMPDIR_LAND/e2e.log"
  E2E_RC=0
  bash "$E2E_TEST" > "$E2E_LOG" 2>&1 || E2E_RC=$?
  tail -8 "$E2E_LOG" | sed 's/^/    /'
  _exp_e2e_rc="$(_expect EXPECTED_E2E_RC)"
  [ "$E2E_RC" = "$_exp_e2e_rc" ] \
    || die "V5: o e2e saiu rc=$E2E_RC, esperado $_exp_e2e_rc — log em $E2E_LOG"
  # O sumario tem a forma exata `    passed         : <N>` / `    failed : <M>`.
  _e2e_passed="$(sed -n 's/^ *passed *: *\([0-9][0-9]*\) *$/\1/p' "$E2E_LOG" | head -1)"
  _e2e_failed="$(sed -n 's/^ *failed *: *\([0-9][0-9]*\) *$/\1/p' "$E2E_LOG" | head -1)"
  [ -n "$_e2e_passed" ] && [ -n "$_e2e_failed" ] \
    || die "V5: nao consegui ler o sumario do e2e — log em $E2E_LOG"
  _exp_e2e_passed="$(_expect EXPECTED_E2E_PASSED)"
  _exp_e2e_failed="$(_expect EXPECTED_E2E_FAILED)"
  [ "$_e2e_failed" = "$_exp_e2e_failed" ] \
    || die "V5: $_e2e_failed asercao(oes) do e2e falharam, esperado $_exp_e2e_failed — log em $E2E_LOG"
  [ "$_e2e_passed" = "$_exp_e2e_passed" ] \
    || die "V5: $_e2e_passed asercao(oes) do e2e passaram, esperado $_exp_e2e_passed.
  Um numero MENOR e regressao (ou uma perna que degradou para SKIP). Um numero
  MAIOR significa que a suite cresceu: atualize $BASELINE_ENV
  conscientemente. Log: $E2E_LOG"
  E2E_STATUS="$_e2e_passed passed / $_e2e_failed failed"
  ok "V5: e2e $_e2e_passed/$_exp_e2e_passed passed, $_e2e_failed failed (rc=$E2E_RC)"
fi

# ---------------------------------------------------------------------------
step "V6 — smoke-install: a cura nao quebrou o install"
# ---------------------------------------------------------------------------
# O V5 responde "nao escreve fora". Esta e OUTRA pergunta: a cura reescreve 26
# hunks do caminho de escrita, e nao escrever fora nao implica continuar
# instalando certo. O smoke roda um install real e a paridade install/upgrade.
if [ "$SKIP_SLOW" = "1" ]; then
  SMOKE_STATUS="PULADO por CEO_C_HARNESS_SKIP_SLOW=1 (so o harness)"
  warn "V6 PULADO — CEO_C_HARNESS_SKIP_SLOW=1 sob o modo auto-teste."
else
  [ -f "$SMOKE_TEST" ] || die "V6: $SMOKE_TEST ausente"
  printf '  install real + paridade install/upgrade (alguns minutos)...\n'
  SMOKE_LOG="$TMPDIR_LAND/smoke.log"
  SMOKE_RC=0
  bash "$SMOKE_TEST" > "$SMOKE_LOG" 2>&1 || SMOKE_RC=$?
  tail -6 "$SMOKE_LOG" | sed 's/^/    /'
  _exp_smoke_rc="$(_expect EXPECTED_SMOKE_INSTALL_RC)"
  [ "$SMOKE_RC" = "$_exp_smoke_rc" ] \
    || die "V6: o smoke-install saiu rc=$SMOKE_RC, esperado $_exp_smoke_rc — log em $SMOKE_LOG"
  # rc 0 e necessario e NAO suficiente: a asercao e a linha final. Sem ela, um
  # script que saisse cedo com 0 passaria.
  _marker="$(_expect EXPECTED_SMOKE_INSTALL_MARKER)"
  grep -qF -- "$_marker" "$SMOKE_LOG" \
    || die "V6: o smoke-install saiu 0 mas NAO imprimiu '$_marker' — log em $SMOKE_LOG"
  SMOKE_STATUS="OK (rc=$SMOKE_RC, marcador presente)"
  ok "V6: smoke-install verde e com o marcador final"
fi

# ---------------------------------------------------------------------------
step "V7 — gates de governanca do repositorio"
# ---------------------------------------------------------------------------
CLINT_JSON="$TMPDIR_LAND/ceremony-lint.json"
python3 .claude/scripts/check-ceremony-script.py --json > "$CLINT_JSON" 2>&1 \
  || die "V7a: check-ceremony-script.py saiu diferente de 0 — saida em $CLINT_JSON"
_clint_obs="$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
v=d['blocking_unwaived']
print(len(v) if isinstance(v,list) else v)
" "$CLINT_JSON")"
_clint_exp="$(_expect EXPECTED_CEREMONY_LINT_BLOCKING)"
[ "$_clint_obs" = "$_clint_exp" ] \
  || die "V7a: check-ceremony-script.py com $_clint_obs blocking, esperado $_clint_exp — saida em $CLINT_JSON"
ok "V7a: ceremony-lint blocking=$_clint_obs (esperado $_clint_exp)"

# O CLAUDE.md e medido AQUI, explicitamente, alem de dentro do governance
# completo. O `--fast` NAO checa o tamanho — foi a licao da S327 — e um abort
# vindo do meio de um log de 900 linhas e um abort que ninguem le.
_cmd_bytes="$(wc -c < "$CLAUDE_MD" | tr -d ' ')"
_cmd_max="$(_expect EXPECTED_CLAUDE_MD_MAX_BYTES)"
[ "$_cmd_bytes" -le "$_cmd_max" ] \
  || die "V7b: $CLAUDE_MD tem $_cmd_bytes bytes, limite $_cmd_max.
  Corte antes de landar: o governance COMPLETO reprova, e este pacote escreve
  no CLAUDE.md."
ok "V7b: $CLAUDE_MD com $_cmd_bytes bytes (limite $_cmd_max)"

# COMPLETO, nao `--fast`: o `--fast` delega a um validador Python que NAO checa
# o tamanho do CLAUDE.md nem varios gates de corpus. Custa ~2 min e e o unico
# modo que responde a pergunta certa.
VG_LOG="$TMPDIR_LAND/validate-governance.log"
VG_RC=0
bash .claude/scripts/validate-governance.sh > "$VG_LOG" 2>&1 || VG_RC=$?
_vg_exp="$(_expect EXPECTED_VALIDATE_GOVERNANCE_RC)"
[ "$VG_RC" = "$_vg_exp" ] || { tail -25 "$VG_LOG" | sed 's/^/    /' >&2
                               die "V7c: validate-governance.sh (COMPLETO) saiu rc=$VG_RC, esperado $_vg_exp — log em $VG_LOG"; }
grep -m1 '  Errors:' "$VG_LOG" | sed 's/^/    /' || printf ''
ok "V7c: validate-governance.sh COMPLETO verde (rc=$VG_RC)"

# O land do pacote D (S329) deixou o main VERMELHO porque um doc GERADO nao foi
# regenerado: `docs/COMMAND-SKILL-HOOK-MAP.md` nao continha o hook novo.
_gm_rc=0
python3 .claude/scripts/gen-command-skill-hook-map.py --check >/dev/null 2>&1 || _gm_rc=$?
_gm_exp="$(_expect EXPECTED_GENMAP_RC)"
[ "$_gm_rc" = "$_gm_exp" ] \
  || die "V7d: gen-command-skill-hook-map.py --check saiu rc=$_gm_rc, esperado $_gm_exp.
  Regenere (sem --check) e inclua o doc no patch — foi assim que o land do
  pacote D deixou o main vermelho na S329."
ok "V7d: COMMAND-SKILL-HOOK-MAP.md sem drift"

_eh_rc=0
python3 .claude/scripts/check-test-env-hygiene.py >/dev/null 2>&1 || _eh_rc=$?
_eh_exp="$(_expect EXPECTED_ENV_HYGIENE_RC)"
[ "$_eh_rc" = "$_eh_exp" ] \
  || die "V7e: check-test-env-hygiene.py saiu rc=$_eh_rc, esperado $_eh_exp — um teste novo toca o \$HOME real"
ok "V7e: check-test-env-hygiene.py verde"

if [ -f .claude/scripts/check-claude-md-claims.py ]; then
  _cc_rc=0
  python3 .claude/scripts/check-claude-md-claims.py >/dev/null 2>&1 || _cc_rc=$?
  _cc_exp="$(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)"
  [ "$_cc_rc" = "$_cc_exp" ] \
    || die "V7f: check-claude-md-claims.py saiu rc=$_cc_rc, esperado $_cc_exp"
  ok "V7f: check-claude-md-claims.py verde"
else
  warn "V7f: check-claude-md-claims.py ausente — nao verificado"
fi

_vc_rc=0
bash .claude/scripts/local/verify-counts.sh --quiet >/dev/null 2>&1 || _vc_rc=$?
_vc_exp="$(_expect EXPECTED_VERIFY_COUNTS_RC)"
[ "$_vc_rc" = "$_vc_exp" ] \
  || die "V7g: verify-counts.sh saiu rc=$_vc_rc, esperado $_vc_exp.
  Contagens derivadas desatualizadas: este pacote acrescenta um ADR, e as
  superficies que citam o numero de ADRs precisam entrar no MESMO patch."
ok "V7g: verify-counts.sh verde"

# ADVISORY de proposito. Medido: `--strict` sai 1 no main de hoje, por planos e
# ADRs que nada tem a ver com esta wave — um gate que ja nasce vermelho nao e um
# gate, e um abort com outro nome. O que exigimos e que o checker EXECUTE.
_st_rc=0
python3 .claude/scripts/check-staleness.py >/dev/null 2>&1 || _st_rc=$?
_st_exp="$(_expect EXPECTED_STALENESS_RC)"
[ "$_st_rc" = "$_st_exp" ] \
  || die "V7h: check-staleness.py saiu rc=$_st_rc, esperado $_st_exp (modo advisory)"
ok "V7h: check-staleness.py verde (advisory)"

# ---------------------------------------------------------------------------
step "S — staging explicito (nunca 'git add -u')"
# ---------------------------------------------------------------------------
# `git add -u` sozinho NUNCA inclui a assinatura: o `.asc` nasce UNTRACKED no
# SIGN, e um commit canonico sem ele sobe sem a evidencia que a governanca
# exige. E `-u` tambem arrastaria um path rastreado sujo tolerado no G0.
# Stage EXATAMENTE: paths do patch + sentinel + .asc, com prova por `cmp`.
{ cat "$TOUCHED_FILE"; printf '%s\n' "$SENTINEL" "$SENTINEL.asc"; } | sort -u > "$EXPECTED_FILE"
while IFS= read -r f; do
  [ -z "$f" ] && continue
  git add -- "$f"
done < "$EXPECTED_FILE"
git diff --cached --name-only | sort -u > "$STAGED_FILE"
git diff --cached --name-only | sed 's/^/    staged: /'
if ! cmp -s "$EXPECTED_FILE" "$STAGED_FILE"; then
  die "conjunto staged != patch + sentinel:
  so no esperado: $(comm -23 "$EXPECTED_FILE" "$STAGED_FILE" | tr '\n' ' ')
  so no staged  : $(comm -13 "$EXPECTED_FILE" "$STAGED_FILE" | tr '\n' ' ')
  (um path do patch identico ao HEAD nao aparece no staged — isso tambem e erro:
   o patch nao deveria toca-lo)"
fi
grep -qx "$SENTINEL.asc" "$STAGED_FILE" || die "a assinatura $SENTINEL.asc NAO ficou staged"
ok "$(wc -l < "$STAGED_FILE" | tr -d ' ') path(s) staged == patch + sentinel + .asc"

# O bit de execucao do e2e tem de viajar no index. `git apply` preserva o modo
# do patch, mas um `update-index --chmod` anterior no checkout do Owner poderia
# diverge-lo (licao CLAUDE.md secao 4: o chmod sozinho nao gruda). O
# finalize-C.sh normaliza o bit na arvore-sombra; aqui a conferencia e no index.
_mode_exp="$(_expect EXPECTED_E2E_INDEX_MODE)"
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    "$E2E_TEST")
      _mode="$(git ls-files --stage -- "$f" | awk '{print $1}')"
      [ "$_mode" = "$_mode_exp" ] || die "o modo de $f no index e $_mode, esperado $_mode_exp.
  O CI invoca com 'bash <path>', mas os vizinhos de scripts/tests/ sao
  executaveis e a divergencia confunde quem le 'ls -l'." ;;
  esac
done < "$STAGED_FILE"
ok "modo de execucao do e2e coerente no index ($_mode_exp)"

# ---------------------------------------------------------------------------
step "C — commit (sem editor) e push"
# ---------------------------------------------------------------------------
# O Owner NAO e usuario de terminal: um `git commit` cru abre o vim e o prende
# la (S326, verbatim: "vc tinha que fazer script sou leigo"). O commit sai
# daqui, com -F e --no-edit; nada abre editor.
case "$(cat "$COMMIT_MSG")" in
  *"Pair-Rail-Reviewed: TO-FILL"*)
    die "a mensagem de commit ainda tem o trailer Pair-Rail-Reviewed por preencher:
  $COMMIT_MSG
  O CEO preenche depois da ultima rodada do rail." ;;
esac

if ! git commit -F "$COMMIT_MSG" --no-edit; then
  die "o commit falhou (hook de pre-commit? veja a saida acima).
  O STAGING esta intacto — nada se perdeu. Chame o CEO.
  Se algum editor abriu: aperte Esc, digite  :q!  e Enter."
fi
NEW_SHA="$(git rev-parse HEAD)"
ok "commit criado: $NEW_SHA"
RESTORE_ON_EXIT=0   # o patch vive no commit a partir daqui
git --no-pager log -1 --format='    %h %s' | sed 's/^/  /'

if [ "$SELFTEST" = "1" ]; then
  warn "AUTO-TESTE: push PULADO"
else
  step "PUSH"
  if ! git push "$PUSH_REMOTE" "HEAD:$PUSH_BRANCH"; then
    die "o push falhou. O commit $NEW_SHA esta LOCAL e intacto.
  Tente de novo:  git -C $ROOT push $PUSH_REMOTE HEAD:$PUSH_BRANCH"
  fi
  ok "empurrado para $PUSH_REMOTE/$PUSH_BRANCH"
fi

step "LAND OK"
cat <<EOF

  commit : $NEW_SHA
  paths  : $(wc -l < "$STAGED_FILE" | tr -d ' ')
  V1 shellcheck : $SHELLCHECK_STATUS
  V5 e2e        : $E2E_STATUS
  V6 smoke      : $SMOKE_STATUS
  V4 censo      : desguardado $_c_desg, $_c_sites sitios, ratchet limpo ($_c_new/$_c_dead)

  Ultimos runs de CI:
EOF
if command -v gh >/dev/null 2>&1 && [ "$SELFTEST" = "0" ]; then
  gh run list --limit 3 2>&1 | sed 's/^/    /' || printf '    (gh run list indisponivel)\n'
else
  printf '    (gh ausente — acompanhe em https://github.com/Canhada-Labs/ceo-orchestration/actions)\n'
fi
cat <<'EOF'

  LEMBRETE — o que observar depois deste land:
  1. O `Smoke Install` passa a rodar um e2e a mais (~7 min locais). O
     `timeout-minutes` do job e uma ESTIMATIVA no fator 2-3x de runner; a
     PRIMEIRA execucao real e o numero que deve substitui-la. Re-apertar no p95
     observado, nunca na aritmetica.
  2. O step novo do `validate.yml` roda o censo FAIL-CLOSED. Se este land
     chegou ao fim, o V4 provou que o ratchet estava LIMPO — mas ele so
     responde pelo `scripts/` deste commit. Qualquer wave seguinte que mexa
     em `scripts/` precisa regenerar a baseline no MESMO patch
     (`--write-baseline`), ou o `Validate` fica vermelho no push.
  3. Ficam ABERTOS por desenho: FU-1 (ensinar ao censo a forma
     `predicado-de-confinamento-domina`, sem o que os escritores curados seguem
     contados como desguardado/indeterminado), FU-7 (`scripts/doctor.sh` e o
     terceiro consumidor previsto e NAO foi convertido) e a OQ-6 (o AC-3 do
     plano foi escrito sobre uma regua que a 4a passada do censo trocou).
  4. TOCTOU permanece: entre o predicado e a escrita nada impede o destino de
     VIRAR symlink. Bash nao oferece openat/O_NOFOLLOW; a guarda ESTREITA a
     janela, nao a fecha. Esta declarado no sentinel.

  Se algum editor abrir em QUALQUER momento:
    aperte Esc, digite  :q!  e Enter  (sai sem salvar; nada se perde).
EOF
