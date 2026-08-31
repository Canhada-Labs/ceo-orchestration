#!/usr/bin/env bash
# OWNER-S335-183BATCH-LAND.sh — land do pacote de cerimonia wave-183batch (PLAN-183).
# CEREMONY-LINT: handwritten-exception: clone gate-a-gate do
# OWNER-S335-179CLOSE-LAND.sh (familia adrgate, curas r1-r8 + rails
# 179close herdadas). Muda o bloco de constantes E o V-block, que aqui
# exercita o SETTINGS regenerado (idempotencia sob o skill-budget-generator,
# contagem de overrides, harness-config gate), o header INERT do template e
# o flip por REGISTRO do AC-5 — um V-block copiado testaria a coisa errada.
# O G4 `touched - scope = 0` so existe automatizado nesta familia.
#
# `.claude/settings.json` esta em `_KERNEL_PATHS` (ADR-116: hook
# configuration disable e o vetor 1+2). O LAND arma CEO_KERNEL_OVERRIDE ele
# mesmo, no menor escopo, com o par reason-SLUG + I-ACCEPT validado VIVO
# contra o contrato do hook — mecanismo identico ao adrgate (cfab980) e ao
# 179close.
#
# Roda de QUALQUER diretorio. Nenhum passo e destrutivo antes de todos os
# gates passarem. Ao fim ele COMMITA (com -F, sem abrir editor) e EMPURRA.
#
# CUSTO: os gates de corpus (verify-counts ~3 min, governanca completa ~30 s)
# sao o V-block caro deste pacote. A governanca roda SEM --fast de proposito:
# o modo completo checa o limite de 40k bytes do CLAUDE.md que o --fast pula
# (licao W5, CLAUDE.md par. 5) — e o valor comparado vem da base declarada.
#
# `.claude/hooks/_lib/audit_emit.py` esta em `_KERNEL_PATHS` do
# check_arbitration_kernel.py ("hook library primitives that back the
# governance hooks") — o runbook da S334 dizia que este pack nao tocava
# kernel e estava ERRADO nesta metade: os hooks de compactacao e o SessionEnd
# de fato nao sao kernel, mas o audit_emit e. O mecanismo aqui e O MESMO do
# adrgate (que armou o override para o validate.yml no land real cfab980):
# o G5 prova cada path canonico concedido pelo sentinel via
# `_sentinel_grants_path`, e o LAND arma CEO_KERNEL_OVERRIDE ele mesmo, no
# menor escopo (export antes do apply, unset apos o commit, backstop no
# trap), com o par reason-SLUG + ACK literal validado VIVO contra o contrato
# do hook (_REASON_RE + _ACK_TOKEN). Nenhum mecanismo novo foi inventado.
#
# Uso:
#   bash .claude/plans/PLAN-183/OWNER-S335-183BATCH-LAND.sh --dry-run
#   bash .claude/plans/PLAN-183/OWNER-S335-183BATCH-LAND.sh
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
PLAN_DIR=".claude/plans/PLAN-183"
CEREMONY_DIR="$PLAN_DIR/s335-ceremony-183batch"
SENTINEL="$PLAN_DIR/wave-183batch-approved.md"
PATCH="$CEREMONY_DIR/W183BATCH.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-183BATCH.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S335-183BATCH-SIGN.sh"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
SETTINGS=".claude/settings.json"
TEMPLATE="templates/.github/workflows/validate.yml.template"
PLAN_FILE=".claude/plans/PLAN-183-adopter-fitness.md"
BUDGET_GEN=".claude/scripts/skill-budget-generator.py"
ADR_DIR=".claude/adr"
UNIT_TESTS=".claude/scripts/tests/test_validate_template_frozen_subset.py"
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

# NAO ha interruptor de pulo de gate nesta wave, e a ausencia e deliberada.
# O pacote E tinha um (`CEO_E_HARNESS_SKIP_E2E`, duplamente guardado) porque o
# V3 dele custava ~9 min de instalacao real. O gate mais caro daqui e o
# verify-counts (~3 min) — abaixo do limiar que justificaria uma rota de pulo.
# Um interruptor sem razao de existir e superficie de ataque.

SHELLCHECK_STATUS="nao-executado"
UNIT_STATUS="nao-executado"

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
  Sem ela cada execucao do V-block e ruido. Rode o finalize-183batch.sh."
# O substrato que o V-block usa JA vive no HEAD (o patch traz o settings
# regenerado, o header e o registro — nunca o gerador). Ausencia aqui
# significa arvore errada, nao patch incompleto.
command -v jq >/dev/null 2>&1 || die "G-PRE: jq ausente — V3/V4 sem instrumento"
[ -f "$BUDGET_GEN" ] || die "G-PRE: $BUDGET_GEN ausente"
[ -f "$SETTINGS" ] || die "G-PRE: $SETTINGS ausente"
[ -d "$ADR_DIR" ] || die "G-PRE: $ADR_DIR ausente — o V8a nao teria corpus"
python3 "$BUDGET_GEN" --jq-fragment >/dev/null 2>&1 \
  || die "G-PRE: skill-budget-generator --jq-fragment nao responde"
ok "G-PRE: jq, gerador e settings presentes; gerador responde"

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
  "$PLAN_DIR/OWNER-S335-183BATCH-LAND.sh"
  "$PROPOSED"
  "$COMMIT_MSG"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-183batch.sh"
  "$CEREMONY_DIR/test-ceremony-scripts-183batch.sh"
  "$CEREMONY_DIR/DESIGN-183BATCH-S335.md"
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
STAGED_BY_LAND=0   # rail r4: NUNCA herdado do ambiente
FP_BEFORE=""
_fingerprint() {
  {
    git status --porcelain=v1
    printf -- '--index--\n'
    git diff --cached --name-status
  } | shasum -a 256 | awk '{print $1}'
}
_restore() {
  # exit status na ENTRADA do trap — capturado na PRIMEIRA linha (rail r2
  # P2-h: qualquer comando antes daqui zera o $? e os logs de um abort
  # jamais seriam preservados). != 0 significa que um die/abort disparou.
  _land_rc=$?
  # Backstop do override de kernel (r1 P1): qualquer saida desarma.
  unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK 2>/dev/null || true
  if [ "$RESTORE_ON_EXIT" = "1" ] && [ "$APPLIED" = "1" ]; then
    # Reset SCOPED aos paths do patch (rail-materials r1 P2-a): o G0
    # tolera staged nao-canonico de terceiros, e um reset global o
    # des-stagearia junto. Deriva os paths do proprio patch.
    git apply --numstat "$PATCH" 2>/dev/null | cut -f3 | while IFS= read -r _pp; do
      [ -n "$_pp" ] && git reset -q -- "$_pp" >/dev/null 2>&1 || true
    done
    # O passo S tambem stageia sentinel + .asc (rail r2 P2-g) — mas SO
    # este script pode des-stagear o que ELE stageou (rail r3 P2-k): num
    # dry-run que nunca chega ao passo S, um reset incondicional
    # destruiria staged pre-existente que o G0 tolera.
    if [ "${STAGED_BY_LAND:-0}" = "1" ]; then
      git reset -q -- "$SENTINEL" "$SENTINEL.asc" >/dev/null 2>&1 || true
    fi
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
  # Licao S329-manha: o abort do V-block apagava o UNICO log do gate caro junto
  # com o tmpdir — o Owner ficou sem a assercao que falhou. Preserva os logs
  # no dir DESTA cerimonia (o F apontava para o dir de logs de OUTRA cerimonia,
  # que pode nem existir — e a preservacao falhava em silencio) ANTES de
  # remover o tmpdir.
  _keep_dir="$ROOT/$CEREMONY_DIR"
  if [ "$_land_rc" != "0" ] && [ -d "$TMPDIR_LAND" ] && [ -d "$_keep_dir" ] && [ -w "$_keep_dir" ]; then
    _logs_kept=0
    for _l in "$TMPDIR_LAND"/*.log; do
      [ -f "$_l" ] || continue
      _kept="$_keep_dir/land-183batch-$(date +%Y%m%d-%H%M%S)-$(basename "$_l")"
      # rail-materials r1 P2-a: destino pre-existente ou symlink e
      # RECUSADO (cp -p seguiria o link para fora do repo).
      if [ -e "$_kept" ] || [ -L "$_kept" ]; then
        printf '  log NAO preservado (destino ja existe): %s\n' "$_kept" >&2
        continue
      fi
      cp -p "$_l" "$_kept" 2>/dev/null && { _logs_kept=$((_logs_kept+1)); printf '  log preservado: %s\n' "$_kept"; }
    done
    if [ "$_logs_kept" -gt 0 ]; then
      printf '  NOTA: %s log(s) preservados na arvore DE PROPOSITO (abort com evidencia);\n' "$_logs_kept"
      printf '        a restauracao acima cobre os paths do patch, nao estes logs.\n'
    fi
  fi
  rm -rf "$TMPDIR_LAND"
}
trap _restore EXIT

# --- kernel-override hygiene (molde W3K; rail-materials r1 P1) -------
# O patch toca .claude/settings.json (_KERNEL_PATHS). A
# cerimonia de kernel ARMA o override ELA MESMA, no menor escopo
# (export logo antes do apply, unset apos o commit, backstop no trap)
# — e RECUSA rodar se o override ja vier do ambiente: duas cerimonias
# na mesma sessao e onde um export sobra e autoriza o pack seguinte
# sem ninguem pedir.
if [ -n "${CEO_KERNEL_OVERRIDE:-}" ] || [ -n "${CEO_KERNEL_OVERRIDE_ACK:-}" ]; then
  die "CEO_KERNEL_OVERRIDE/_ACK ja estao no ambiente ANTES deste script.
  Desarme (unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK) e re-rode —
  este LAND arma e desarma o proprio override, no menor escopo."
fi

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
# Este sentinel-draft usa placeholders *-PLACEHOLDER alem dos TO-FILL-* da
# familia F; o case cobre os dois.
for field in "Approved-By" "Anchor-SHA" "Data" "Patch-sha256" "Patch-base"; do
  val="$( { grep -m1 "^$field:" "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
  [ -n "$val" ] || die "sentinel sem campo '$field:'"
  case "$val" in
    *TO-FILL*|*PLACEHOLDER*) die "campo '$field:' ainda e placeholder ($val) — o sentinel nao foi assinado pelo SIGN" ;;
  esac
done

ANCHOR="$( { grep -m1 '^Anchor-SHA:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
HEAD_SHA="$(git rev-parse HEAD)"
[ "$ANCHOR" = "$HEAD_SHA" ] || die "Anchor-SHA nao bate com HEAD
  ancora: $ANCHOR
  HEAD  : $HEAD_SHA
  Commits entraram depois da assinatura. Re-gere o Anchor e RE-ASSINE."
ok "ancora casa HEAD ($HEAD_SHA)"

# ---------------------------------------------------------------------------
step "G2 — binding do patch (Patch-sha256)"
# ---------------------------------------------------------------------------
DECLARED="$( { grep -m1 '^Patch-sha256:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
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
PATCH_BASE="$( { grep -m1 '^Patch-base:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
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

# Conjunto EXATO de paths tocados, contra a base declarada. Uma cerimonia que
# so conta arquivos aceitaria um patch com os 4 paths ERRADOS.
_exp_paths="$(_expect EXPECTED_PATCH_PATHS | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u)"
_obs_paths="$(LC_ALL=C sort -u "$TOUCHED_FILE")"
[ "$_obs_paths" = "$_exp_paths" ] || die "G4: conjunto de paths tocados difere do DECLARADO
  declarado: $(printf '%s' "$_exp_paths" | tr '\n' ' ')
  observado: $(printf '%s' "$_obs_paths" | tr '\n' ' ')"
ok "G4: conjunto de paths casa EXPECTED_PATCH_PATHS"

# ---------------------------------------------------------------------------
step "G5 — grants do sentinel + coerencia do manifesto ADR-192"
# ---------------------------------------------------------------------------
# Assinatura GPG valida NAO e autorizacao mecanica (licao S318: um sentinel
# verificou e concedia ZERO paths). Aqui cada path CANONICO tocado e provado
# concedido pela MESMA funcao que o hook usa, `_sentinel_grants_path`.
# `.claude/settings.json` e KERNEL (`_KERNEL_PATHS`) — o mecanismo e o
# MESMO que landou o adrgate e o 179close: nada novo aqui.
if [ "$SELFTEST" = "1" ]; then
  # O unlock exige PROVENIENCIA: sem ela ele nega tudo e o G5 reprovaria por
  # motivo ERRADO, deixando o controle positivo do parse de Scope VACUO. Com o
  # digest fixado nos bytes EM DISCO, quem decide volta a ser o parse do Scope.
  SELFTEST_SENTINEL_SHA="$(shasum -a 256 "$SENTINEL" | awk '{print $1}')"
  G5_ENV=(env "CEO_SENTINEL_UNLOCK=PLAN-183-closure-and-cross-session-evolution" \
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

# O NUMERO de paths canonicos tambem e comparado contra a base DECLARADA. Sem
# isto, um patch que perdesse o `settings.json` (o SUJEITO do batch!) e
# carregasse so o template passaria pelo bloco acima: zero canonicos tocados
# e trivialmente "todos concedidos".
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
  || die "G5: $_obs_canon path(s) CANONICOS no patch, esperado $_exp_canon.
  Menos significa que um alvo canonico da wave saiu do patch; mais significa que
  o patch cresceu para superficie que a revisao nao leu."
ok "G5: $_obs_canon path(s) canonico(s) (esperado $_exp_canon)"

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
# verdade para rodar o V1/V3/V4/V6 sobre o conteudo REAL pos-patch, e restaura
# no trap (dry-run que deixa `git apply` no index e a armadilha da S272).
# ---------------------------------------------------------------------------
FP_BEFORE="$(_fingerprint)"

# ---------------------------------------------------------------------------
step "APLICANDO o patch assinado"
# ---------------------------------------------------------------------------
# S327 (abort real medido): o primeiro land REAL abortou no V4 e deixou a arvore
# com o patch aplicado — so o dry-run restaurava. Agora TODO abort depois do
# apply restaura arvore e index; o land bem-sucedido desliga o restore logo
# apos o commit.
# Arma o override de kernel SO agora (menor escopo — rail-materials r1
# P1, molde W3K). O Scope assinado que o G5 acabou de validar NOMEIA o
# validate.yml; o override e a segunda chave, nunca a primeira.
# Contrato do hook (check_arbitration_kernel.py: _REASON_RE + _ACK_TOKEN):
# reason e um SLUG [A-Za-z0-9._-]{1,120}; o ACK e o literal I-ACCEPT.
# Valores fora do contrato = override NAO concedido em silencio (medido
# pelo rail r2 avaliando _override_granted() = False com o valor antigo).
export CEO_KERNEL_OVERRIDE="PLAN-183-wave-183batch-settings-json-regen.sentinel-wave-183batch-approved"
export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
RESTORE_ON_EXIT=1
git apply "$PATCH"
APPLIED=1
ok "patch aplicado ($(wc -l < "$TOUCHED_FILE" | tr -d ' ') paths)"

# ---------------------------------------------------------------------------
step "V1 — o que o patch toca compila"
# ---------------------------------------------------------------------------
# Esta wave NAO toca script shell nenhum — e isso e uma afirmacao, nao uma
# omissao: um `.sh` aparecendo no patch significa que o escopo mudou sem
# ninguem decidir (e o ratchet installer-write-safety passaria a ser devido no
# MESMO patch, regra do CLAUDE.md). E ela toca EXATAMENTE o numero DECLARADO
# de arquivos Python — ZERO: settings.json + template + plano. Um .py
# aparecendo aqui e escopo novo sem decisao.
SH_COUNT=0
PY_COUNT=0
PY_LIST="$TMPDIR_LAND/pyfiles"
: > "$PY_LIST"
while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ -f "$f" ] || continue
  case "$f" in
    *.sh) SH_COUNT=$(( SH_COUNT + 1 )) ;;
    *.py) printf '%s\n' "$f" >> "$PY_LIST"; PY_COUNT=$(( PY_COUNT + 1 )) ;;
    *)
      head_line="$(head -1 "$f" 2>/dev/null || printf '')"
      case "$head_line" in
        "#!"*sh*)     SH_COUNT=$(( SH_COUNT + 1 )) ;;
        "#!"*python*) printf '%s\n' "$f" >> "$PY_LIST"; PY_COUNT=$(( PY_COUNT + 1 )) ;;
      esac ;;
  esac
done < "$TOUCHED_FILE"
[ "$SH_COUNT" -eq 0 ] || die "V1: o patch toca $SH_COUNT script(s) shell — esta wave nao toca nenhum.
  Se um .sh entrou de proposito, o ratchet installer-write-safety passa a ser
  devido no MESMO patch (a regra do CLAUDE.md) e este gate tem de ser
  atualizado conscientemente."
_py_exp="$(_expect EXPECTED_PATCH_PY_FILES)"
[ "$PY_COUNT" -eq "$_py_exp" ] || die "V1: $PY_COUNT arquivo(s) Python no patch — esperava exatamente $_py_exp.
  Menos significa que um sujeito da wave saiu do patch; mais significa escopo
  novo sem decisao."
while IFS= read -r f; do
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$f" \
    || die "V1a: py_compile reprovou em $f"
done < "$PY_LIST"
ok "V1a: py_compile verde em $PY_COUNT arquivo(s) Python (0 shell, como esperado)"
SHELLCHECK_STATUS="nao aplicavel (a wave nao toca script shell)"

# ---------------------------------------------------------------------------
step "V6 — o wire da wave: header INERT, comment do gerador e AC-5"
# ---------------------------------------------------------------------------
# Roda no dry-run TAMBEM. `grep -c` sai 1 quando nao casa nada e sob
# pipefail isso mataria o script mudo — o `|| true` faz a mensagem NOMEADA
# disparar (forma herdada da familia).
_in_obs="$( { grep -c 'INERT AS SHIPPED' "$TEMPLATE" || true; } )"
[ "$_in_obs" = "$(_expect EXPECTED_INERT_REFS)" ] \
  || die "V6a: 'INERT AS SHIPPED' aparece $_in_obs vez(es) no template, esperado $(_expect EXPECTED_INERT_REFS)."
_jc_obs="$( { grep -c '_skill_budget_comment' "$SETTINGS" || true; } )"
[ "$_jc_obs" = "$(_expect EXPECTED_BUDGET_COMMENT_REFS)" ] \
  || die "V6b: '_skill_budget_comment' aparece $_jc_obs vez(es) no settings, esperado $(_expect EXPECTED_BUDGET_COMMENT_REFS)."
ok "V6a-b: header INERT e comment do gerador no lugar"
_a5x="$( { grep -c -- '- \[x\] AC-5' "$PLAN_FILE" || true; } )"
[ "$_a5x" = "$(_expect EXPECTED_AC5_CHECKED)" ] \
  || die "V6c: '- [x] AC-5' aparece $_a5x vez(es) no plano, esperado $(_expect EXPECTED_AC5_CHECKED) — o flip e PROIBIDO (rail 183-r1)."
_a5n="$( { grep -c 'REGISTRO S335' "$PLAN_FILE" || true; } )"
[ "$_a5n" = "$(_expect EXPECTED_AC5_NOTE_REFS)" ] \
  || die "V6d: a nota 'REGISTRO S335' aparece $_a5n vez(es), esperado $(_expect EXPECTED_AC5_NOTE_REFS)."
ok "V6c-d: AC-5 aberto com registro (flip barrado)"

# ---------------------------------------------------------------------------
step "V3 — o settings sob o gerador, nos DOIS sentidos"
# ---------------------------------------------------------------------------
# (a) IDEMPOTENTE: re-gerar o fragment e re-aplica-lo ao settings POS-PATCH
#     nao muda um byte — o settings shipado E o derivado do codigo;
# (b) NAO-VACUO: numa copia descartavel sem uma das chaves novas, o
#     fragment tem de RECUPERA-LA — um fragment que nada escreve seria
#     idempotente por vacuidade.
FRAG="$TMPDIR_LAND/skill-frag.jq"
python3 "$BUDGET_GEN" --jq-fragment > "$FRAG" 2>"$TMPDIR_LAND/frag.err" \
  || { sed 's/^/    /' "$TMPDIR_LAND/frag.err" >&2; die "V3a: gerador falhou"; }
_s_before="$( shasum -a 256 "$SETTINGS" | awk '{print $1}' )"
jq -f "$FRAG" "$SETTINGS" > "$TMPDIR_LAND/settings.regen" \
  || die "V3a: jq -f do fragment falhou"
_s_after="$( shasum -a 256 "$TMPDIR_LAND/settings.regen" | awk '{print $1}' )"
[ "$_s_before" = "$_s_after" ] \
  || die "V3a: re-aplicar o fragment MUDA o settings pos-patch — o patch nao
  carrega o derivado do gerador. Refinalize com o regen."
ok "V3a: settings idempotente sob o gerador"
FIRE_JSON="$TMPDIR_LAND/settings-fire.json"
jq 'del(.skillOverrides["prisma-patterns"])' "$SETTINGS" > "$FIRE_JSON" \
  || die "V3b: nao consegui montar a copia mutilada"
jq -f "$FRAG" "$FIRE_JSON" > "$FIRE_JSON.re" || die "V3b: re-aplicacao falhou"
_fk="$( jq -r '.skillOverrides["prisma-patterns"] // "ABSENT"' "$FIRE_JSON.re" )"
[ "$_fk" = "name-only" ] \
  || die "V3b: a chave apagada NAO foi recuperada (veio: $_fk) — regen vacuo"
ok "V3b: fragment recupera chave apagada (nao-vacuo)"

# ---------------------------------------------------------------------------
step "V4 — sonda comportamental: harness-config gate + contagem de overrides"
# ---------------------------------------------------------------------------
# O gate REAL que consome o settings roda sobre a arvore POS-PATCH (roda no
# dry-run porque custa <1s), e a contagem de overrides e comparada com a
# DECLARADA.
jq -e . "$SETTINGS" >/dev/null || die "V4: settings.json nao parseia"
_ov_obs="$( jq '.skillOverrides|length' "$SETTINGS" )"
[ "$_ov_obs" = "$(_expect EXPECTED_SETTINGS_OVERRIDES)" ] \
  || die "V4: $_ov_obs override(s), esperado $(_expect EXPECTED_SETTINGS_OVERRIDES)"
HC_LOG="$TMPDIR_LAND/harness-config.log"
HC_RC=0
python3 .claude/hooks/check_harness_config.py > "$HC_LOG" 2>&1 || HC_RC=$?
[ "$HC_RC" = "0" ] || { tail -10 "$HC_LOG" | sed 's/^/    /' >&2
  die "V4: check_harness_config reprovou (rc=$HC_RC) — log em $HC_LOG"; }
ok "V4: settings parseia ($_ov_obs overrides); harness-config gate verde"

# O corte do dry-run. Ele fica AQUI, depois dos gates baratos que operam sobre
# a arvore JA PATCHADA (V1, V6, V3, V4) e antes dos caros — a mesma posicao que
# o pacote F usava. Sem ele o `--dry-run` seguiria ate o staging e o commit,
# que e o oposto exato do que a flag promete. O trap restaura arvore e index.
if [ "$DRY_RUN" = "1" ]; then
  printf '\n\033[33mDRY-RUN\033[0m — G-PRE, G0..G5 verdes; patch aplicado; V1, V6, V3 e V4 executados.\n'
  printf '  O V-block CARO (V2 unidade, V8 contagens, V9 governanca) NAO roda em dry-run.\n'
  printf '  Restaurando arvore e index...\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "V2 — suite de unidade (conjunto DECLARADO, nunca 'passou')"
# ---------------------------------------------------------------------------
UNIT_LOG="$TMPDIR_LAND/unit.log"
UNIT_RC=0
# shellcheck disable=SC2086  # $UNIT_TESTS e uma lista controlada, sem espacos
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest $UNIT_TESTS -q -p no:cacheprovider \
  > "$UNIT_LOG" 2>&1 || UNIT_RC=$?
[ "$UNIT_RC" -eq 0 ] || { tail -30 "$UNIT_LOG" | sed 's/^/    /' >&2
                          die "V2: a suite reprovou (rc=$UNIT_RC) — log em $UNIT_LOG"; }
_unit_obs="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$UNIT_LOG" || true; } \
              | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_unit_obs" ] || die "V2: nao consegui ler 'N passed' — log em $UNIT_LOG"
_unit_exp="$(_expect EXPECTED_UNIT_PYTEST_PASSED)"
[ "$_unit_obs" = "$_unit_exp" ] \
  || die "V2: $_unit_obs teste(s) passaram, esperado $_unit_exp.
  Menos e regressao; mais significa que a suite cresceu — atualize
  $BASELINE_ENV CONSCIENTEMENTE, nunca relaxe o numero. Log: $UNIT_LOG"
_skip_obs="$( { grep -oE '[0-9]+ skipped' "$UNIT_LOG" || true; } | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_skip_obs" ] || _skip_obs=0
[ "$_skip_obs" = "$(_expect EXPECTED_UNIT_PYTEST_SKIPPED)" ] \
  || die "V2: $_skip_obs teste(s) pulados, esperado $(_expect EXPECTED_UNIT_PYTEST_SKIPPED)
  — uma suite parou de rodar, e um gate que so olha 'passed' aceitaria isso em
  silencio. Log: $UNIT_LOG"
UNIT_STATUS="$_unit_obs teste(s), $_skip_obs skip(s)"
ok "V2: suite $_unit_obs/$_unit_exp (skips $_skip_obs)"

# ---------------------------------------------------------------------------
step "V5 — o AC-5 viaja VERDADEIRO (registro SEM flip — rail 183-r1)"
# ---------------------------------------------------------------------------
# O texto do AC exige EXECUTAR o CI entregue; a execucao real segue aberta
# (W0-US3/OQ-2). O gate garante as DUAS metades da honestidade: o registro
# com evidencia nomeada ESTA no plano, e o checkbox NAO flipou.
_a5x="$( { grep -c -- '- \[x\] AC-5' "$PLAN_FILE" || true; } )"
[ "$_a5x" = "$(_expect EXPECTED_AC5_CHECKED)" ] \
  || die "V5: '- [x] AC-5' aparece $_a5x vez(es), esperado $(_expect EXPECTED_AC5_CHECKED) — flip proibido nesta wave"
_a5n="$( { grep -c 'REGISTRO S335' "$PLAN_FILE" || true; } )"
[ "$_a5n" = "$(_expect EXPECTED_AC5_NOTE_REFS)" ] \
  || die "V5: nota 'REGISTRO S335' aparece $_a5n vez(es), esperado $(_expect EXPECTED_AC5_NOTE_REFS)"
grep -qF 'smoke-install.yml:485' "$PLAN_FILE" \
  || die "V5: a evidencia (yml:485) nao esta nomeada no registro"
ok "V5: registro com evidencia presente; checkbox intacto (aberto)"

# ---------------------------------------------------------------------------
step "V8 — os gates de contagem do corpus"
# ---------------------------------------------------------------------------
# O patch NAO adiciona ADR (esta wave nao toca o corpus de ADRs): a contagem
# tem de ficar parada — um delta aqui significa contaminacao de escopo.
_adr_obs="$( find "$ADR_DIR" -maxdepth 1 -name 'ADR-*.md' | wc -l | tr -d ' ' )"
_adr_exp="$(_expect EXPECTED_ADR_COUNT)"
[ "$_adr_obs" = "$_adr_exp" ] \
  || die "V8a: $_adr_obs ADR(s) no disco, esperado $_adr_exp — as citacoes em
  docs ficariam defasadas e o verify-counts abaixo reprovaria."
ok "V8a: $_adr_obs ADRs no disco"

CLAIMS_RC=0
python3 .claude/scripts/check-claude-md-claims.py >/dev/null 2>&1 || CLAIMS_RC=$?
[ "$CLAIMS_RC" = "$(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)" ] \
  || die "V8b: check-claude-md-claims saiu rc=$CLAIMS_RC, esperado $(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)"
ok "V8b: check-claude-md-claims verde"

VC_LOG="$TMPDIR_LAND/verify-counts.log"
VC_RC=0
bash .claude/scripts/local/verify-counts.sh > "$VC_LOG" 2>&1 || VC_RC=$?
[ "$VC_RC" = "$(_expect EXPECTED_VERIFY_COUNTS_RC)" ] \
  || { grep -E 'DRIFT|Exit' "$VC_LOG" | head -20 | sed 's/^/    /' >&2
       die "V8c: verify-counts.sh saiu rc=$VC_RC, esperado $(_expect EXPECTED_VERIFY_COUNTS_RC) — log em $VC_LOG"; }
ok "V8c: verify-counts.sh verde (rc=$VC_RC)"

# ---------------------------------------------------------------------------
step "V9 — gates de governanca do repositorio"
# ---------------------------------------------------------------------------
CLINT_JSON="$TMPDIR_LAND/ceremony-lint.json"
python3 .claude/scripts/check-ceremony-script.py --json > "$CLINT_JSON" 2>&1 \
  || die "V9a: check-ceremony-script.py saiu diferente de 0 — saida em $CLINT_JSON"
_clint_obs="$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
v=d['blocking_unwaived']
print(len(v) if isinstance(v,list) else v)
" "$CLINT_JSON")"
_clint_exp="$(_expect EXPECTED_CEREMONY_LINT_BLOCKING)"
[ "$_clint_obs" = "$_clint_exp" ] \
  || die "V9a: check-ceremony-script.py com $_clint_obs blocking, esperado $_clint_exp — saida em $CLINT_JSON"
ok "V9a: ceremony-lint blocking=$_clint_obs (esperado $_clint_exp)"

# A governanca roda COMPLETA (sem --fast): o modo completo checa o limite de
# 40k bytes do CLAUDE.md que o --fast pula (licao W5). rc 0 nao e a resposta
# inteira: o script reporta "Errors: N" e a base declara o N esperado. A ancora
# de linha + `-i` cobrem as duas grafias medidas (`Errors:` no completo,
# `errors:` no fast); o fallback para 0 NAO existe — um gate que passa por nao
# encontrar o proprio sujeito e a definicao de vacuo.
GOV_LOG="$TMPDIR_LAND/validate-governance.log"
bash .claude/scripts/validate-governance.sh > "$GOV_LOG" 2>&1 \
  || { tail -20 "$GOV_LOG" | sed 's/^/    /' >&2
       die "V9b: validate-governance.sh FALHOU — log em $GOV_LOG"; }
_gov_obs="$( { grep -oiE '^[[:space:]]*errors:[[:space:]]+[0-9]+' "$GOV_LOG" || true; } \
             | { grep -oE '[0-9]+' || true; } | head -1 )"
[ -n "$_gov_obs" ] || die "V9b: nao consegui ler a contagem de erros em $GOV_LOG —
  o relatorio mudou de forma. Um gate que nao acha o proprio sujeito nao passa."
[ "$_gov_obs" = "$(_expect EXPECTED_GOVERNANCE_ERRORS)" ] \
  || die "V9b: validate-governance reporta $_gov_obs erro(s), esperado
  $(_expect EXPECTED_GOVERNANCE_ERRORS) — log em $GOV_LOG"
ok "V9b: validate-governance.sh completo verde ($_gov_obs erro(s))"

# O land do pacote D (S329) deixou o main VERMELHO porque um doc GERADO nao foi
# regenerado. Este pacote nao adiciona hook, mas o gate custa milissegundos e a
# licao foi paga: docs GERADOS entram na bateria de TODO land.
python3 .claude/scripts/gen-command-skill-hook-map.py --check >/dev/null \
  || die "V9c: gen-command-skill-hook-map.py --check acusou DRIFT.
  Regenere (sem --check) e inclua o doc no patch — foi assim que o land do
  pacote D deixou o main vermelho na S329."
ok "V9c: COMMAND-SKILL-HOOK-MAP.md sem drift"

python3 .claude/scripts/check-test-env-hygiene.py >/dev/null \
  || die "V9d: check-test-env-hygiene.py reprovou — um teste novo toca o \$HOME real"
ok "V9d: check-test-env-hygiene.py verde"

# O ratchet do censo installer-write-safety. Esta wave nao toca `scripts/`,
# entao a regra "wave que toca scripts/ regenera o baseline" NAO dispara. O
# gate roda mesmo assim: e barato, e um `.sh` que entre no patch sem
# regeneracao e exatamente o que ele existe para pegar.
RATCHET_RC=0
python3 .claude/scripts/check-installer-write-safety.py >/dev/null 2>&1 || RATCHET_RC=$?
[ "$RATCHET_RC" = "$(_expect EXPECTED_RATCHET_RC)" ] \
  || die "V9e: check-installer-write-safety saiu rc=$RATCHET_RC, esperado
  $(_expect EXPECTED_RATCHET_RC). Se um sitio novo entrou, regenere o baseline
  no MESMO patch:  python3 .claude/scripts/check-installer-write-safety.py --write-baseline"
ok "V9e: ratchet installer-write-safety verde"

# ---------------------------------------------------------------------------
step "S — staging explicito (nunca 'git add -u')"
# ---------------------------------------------------------------------------
# `git add -u` sozinho NUNCA inclui a assinatura: o `.asc` nasce UNTRACKED no
# SIGN, e um commit canonico sem ele sobe sem a evidencia que a governanca
# exige. E `-u` tambem arrastaria um path rastreado sujo tolerado no G0.
# Stage EXATAMENTE: paths do patch + sentinel + .asc, com prova por `cmp`.
{ cat "$TOUCHED_FILE"; printf '%s\n' "$SENTINEL" "$SENTINEL.asc"; } | sort -u > "$EXPECTED_FILE"
STAGED_BY_LAND=1   # rail r4: ANTES do loop — um add parcial ja autoriza o des-stage
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

# Esta wave nao adiciona script executavel, entao o gate de modo do pacote E
# nao tem sujeito aqui. O que ele checa em seu lugar: NENHUM path do patch
# entrou no index com o bit de execucao ligado por acidente — um `.md` ou um
# `.yml` executavel e ruido que um add-tudo de um dia carrega adiante
# (CLAUDE.md par. 4: o `--chmod=-x` sozinho nao gruda).
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    *.py|*.sh) continue ;;
  esac
  _mode="$(git ls-files --stage -- "$f" | awk '{print $1}')"
  [ -n "$_mode" ] || continue
  case "$_mode" in
    100755) die "o modo de $f no index e 100755 (executavel).
  Este path nao e um script. Corrija nos DOIS lados — o filesystem E o index:
    chmod -x $f && git update-index --chmod=-x -- $f" ;;
  esac
done < "$STAGED_FILE"
ok "nenhum arquivo nao-script staged como executavel"

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
# Desarma o override de kernel AGORA (rail r2 P1-c): o menor escopo termina
# no commit — o push e os comandos seguintes rodam sem a chave no ambiente.
unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK 2>/dev/null || true
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
  V1 sintaxe    : $SHELLCHECK_STATUS
  V2 unidade    : $UNIT_STATUS

  Ultimos runs de CI:
EOF
if command -v gh >/dev/null 2>&1 && [ "$SELFTEST" = "0" ]; then
  gh run list --limit 3 2>&1 | sed 's/^/    /' || printf '    (gh run list indisponivel)\n'
else
  printf '    (gh ausente — acompanhe em https://github.com/Canhada-Labs/ceo-orchestration/actions)\n'
fi
cat <<'EOF'

  LEMBRETE — o que observar depois deste land:
  1. O settings.json mudou (KERNEL): a PROXIMA sessao carrega os 4 skills
     novos como name-only. Se um deles voltar a ser despachado, o gerador
     re-promove na proxima regen — isso e o desenho, nao um bug.
  2. O template do adopter agora nasce com o header INERT: a ativacao e um
     `git mv` explicito documentado no proprio header. O frozen-subset (11
     steps + pins) esta intacto — o Smoke Install prova.
  3. AC-5 do PLAN-183 segue ABERTO por desenho (rail 183-r1 barrou o flip:
     o texto exige EXECUTAR o CI entregue). O que landou e o REGISTRO com a
     evidencia do wiring (yml:485 -> sh:180); a execucao real e W0-US3/OQ-2
     — decisao sua.
  4. W1 do PLAN-183 segue na fila (itens 1-5 em sombra; o re-baseline de
     ownership por ultimo) — «avancar sem promessa», como ratificado.

  Se algum editor abrir em QUALQUER momento:
    aperte Esc, digite  :q!  e Enter  (sai sem salvar; nada se perde).
EOF
