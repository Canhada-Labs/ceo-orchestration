#!/usr/bin/env bash
# OWNER-S329-E-LAND.sh — land do pacote de cerimônia wave-s329-E (PLAN-169).
# CEREMONY-LINT: handwritten-exception: clone gate-a-gate do OWNER-S328-B-LAND.sh
# (por sua vez provado num land REAL, 6304f66 / 738007e / 4bd7def). Muda o bloco
# de constantes E o V-block, que aqui exercita a DERIVACAO DO ROSTER DE HOOKS —
# nao o gate de latencia do pacote B: um V-block copiado testaria a coisa errada
# e seria verde vazio. O gerador `.claude/scripts/generate-ceremony.sh` NAO
# serve: ele assume o layout `architect/round-N/approved.md`, e esta cerimonia
# usa `PLAN-NNN/wave-*-approved.md` com land por PATCH. O G4
# `touched - scope = 0` so existe automatizado nesta familia de scripts.
#
# Roda de QUALQUER diretorio. Nenhum passo e destrutivo antes de todos os
# gates passarem. Ao fim ele COMMITA (com -F, sem abrir editor) e EMPURRA.
#
# CUSTO: o V3 roda o e2e de instalacao real (~9 min). E o gate caro deste
# pacote e ele NAO tem substituto barato — a paridade install/upgrade compara
# as duas na MESMA arvore (um roster faltando nas duas e byte-identico e
# verde), e o dogfood-parity compara dogfood contra template, nunca dogfood
# contra O RESULTADO DE UM UPGRADE. Por isso o achado de origem sobreviveu.
#
# Uso:
#   bash .claude/plans/PLAN-169/OWNER-S329-E-LAND.sh --dry-run
#   bash .claude/plans/PLAN-169/OWNER-S329-E-LAND.sh
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
PLAN_DIR=".claude/plans/PLAN-169"
CEREMONY_DIR="$PLAN_DIR/s329-ceremony-E"
SENTINEL="$PLAN_DIR/wave-s329-E-approved.md"
PATCH="$CEREMONY_DIR/E.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-E.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S329-E-SIGN.sh"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
UPGRADE="scripts/upgrade.sh"
E2E_TEST="scripts/tests/test-upgrade-lifecycle-hooks-derived.sh"
UNIT_TEST=".claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py"
YML=".github/workflows/smoke-install.yml"
TEMPLATE="templates/settings/settings.base.json"
TEMPLATE_USER="templates/settings/settings.user.json"
UPGRADE_FN="_merge_lifecycle_hooks_into_settings"
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

# --- pulo do e2e: SO sob o auto-teste, e NOMEADO em voz alta ---------------
# O e2e custa ~9 min. O harness precisa exercitar os gates sem paga-lo 8 vezes.
# O interruptor e DUPLAMENTE guardado: exige o auto-teste (que ja exige o
# scratchpad) E a variavel propria. Na arvore viva ele nao existe, entao um
# `export` esquecido no perfil do Owner nao consegue calar o gate caro.
SKIP_E2E=0
if [ "${CEO_E_HARNESS_SKIP_E2E:-}" = "1" ]; then
  if [ "$SELFTEST" = "1" ]; then
    SKIP_E2E=1
    printf '\033[33m  CEO_E_HARNESS_SKIP_E2E=1\033[0m — o V3 (e2e, ~9 min) sera PULADO.\n'
    printf '        So o harness usa isto. Um land REAL sempre roda o V3.\n'
  else
    die "CEO_E_HARNESS_SKIP_E2E=1 RECUSADO fora do modo auto-teste.
  O V3 e o unico gate que prova a cura de ponta a ponta. Nao ha rota para
  pula-lo num land real."
  fi
fi

SHELLCHECK_STATUS="nao-executado"
E2E_STATUS="nao-executado"

# Leitor da base esperada: sem `source` (o arquivo nao executa nada), e
# fail-CLOSED quando a chave falta.
_expect() {
  _ev="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
  if [ -z "$_ev" ]; then
    die "chave '$1' AUSENTE em $BASELINE_ENV — o V-block nao compara contra nada"
  fi
  printf '%s' "$_ev"
}

# Extrai o corpo de `_merge_lifecycle_hooks_into_settings` por ANCORA de coluna
# 0 — o mesmo idioma que o teste de unidade usa. Sem regex montado por string:
# `index($0, start) == 1` exige que a linha COMECE pela assinatura, e
# `$0 == "}"` fecha na chave de coluna 0.
_fn_body() {
  awk -v start="${UPGRADE_FN}() {" \
      'index($0, start) == 1 { f = 1 }
       f { print }
       f && $0 == "}" { exit }' "$1"
}

# ---------------------------------------------------------------------------
step "G-PRE — substrato e base declarada"
# ---------------------------------------------------------------------------
[ -f "$BASELINE_ENV" ] || die "base esperada AUSENTE: $BASELINE_ENV
  Sem ela cada execucao do V-block e ruido. Rode o finalize-E.sh."
# A derivacao do roster usa `--slurpfile` (jq >= 1.5). Checagem COMPORTAMENTAL,
# nunca por string de versao: `jq --version` aqui devolve `jq-1.7.1-apple`, e
# comparar texto de versao com sufixo de vendor ja quebrou neste repositorio.
if [ "$(_expect EXPECTED_JQ_SLURPFILE_REQUIRED)" = "1" ]; then
  command -v jq >/dev/null 2>&1 || die "G-PRE: jq AUSENTE — o upgrade.sh curado nao roda sem ele"
  printf '{}' | jq --slurpfile _probe /dev/null '.' >/dev/null 2>&1 \
    || die "G-PRE: o jq desta maquina NAO aceita --slurpfile.
  A derivacao do roster depende dessa flag (jq >= 1.5). Atualize o jq."
  ok "G-PRE: jq aceita --slurpfile ($( jq --version 2>/dev/null || printf '?' ))"
fi
[ -f "$TEMPLATE" ] || die "G-PRE: $TEMPLATE ausente — a cura DERIVA o roster desse arquivo"
ok "G-PRE: $TEMPLATE presente"

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
  "$PLAN_DIR/OWNER-S329-E-LAND.sh"
  "$PROPOSED"
  "$COMMIT_MSG"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-E.sh"
  "$CEREMONY_DIR/test-ceremony-scripts-E.sh"
  "$CEREMONY_DIR/README-E.md"
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
  _keep_dir="$ROOT/.claude/plans/PLAN-169/s329-ceremony-main"
  if [ "$_land_rc" != "0" ] && [ -d "$TMPDIR_LAND" ] && [ -d "$_keep_dir" ] && [ -w "$_keep_dir" ]; then
    for _l in "$TMPDIR_LAND"/*.log; do
      [ -f "$_l" ] || continue
      _kept="$_keep_dir/land-E-$(date +%Y%m%d-%H%M%S)-$(basename "$_l")"
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
  val="$( { grep -m1 "^$field:" "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
  [ -n "$val" ] || die "sentinel sem campo '$field:'"
  case "$val" in
    *TO-FILL*) die "campo '$field:' ainda e placeholder ($val) — o sentinel nao foi assinado pelo SIGN" ;;
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
# so conta arquivos aceitaria um patch com os 5 paths ERRADOS.
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
if [ "$SELFTEST" = "1" ]; then
  # O unlock exige PROVENIENCIA: sem ela ele nega tudo e o G5 reprovaria por
  # motivo ERRADO, deixando o controle positivo do parse de Scope VACUO. Com o
  # digest fixado nos bytes EM DISCO, quem decide volta a ser o parse do Scope.
  SELFTEST_SENTINEL_SHA="$(shasum -a 256 "$SENTINEL" | awk '{print $1}')"
  G5_ENV=(env "CEO_SENTINEL_UNLOCK=PLAN-169-closure-and-cross-session-evolution" \
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
# isto, um patch que perdesse o `scripts/upgrade.sh` (o alvo da wave!) e
# carregasse so os testes passaria pelo bloco acima: zero canonicos tocados e
# trivialmente "todos concedidos".
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
  Menos significa que o alvo canonico da wave saiu do patch; mais significa que
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
# verdade para rodar o V1/V4/V5/V6 sobre o conteudo REAL pos-patch, e restaura
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
# Este pacote SEMPRE toca dois scripts shell (o upgrader e o e2e). Zero aqui
# seria o V1 medindo a coisa errada, nao "nada a fazer".
[ "$SH_COUNT" -ge 2 ] || die "V1: so $SH_COUNT script(s) shell no patch — esperava ao menos 2
  ($UPGRADE e $E2E_TEST). Um V1 vazio e um gate morto."
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
  SHELLCHECK_STATUS="INDISPONIVEL nesta maquina — o CI executa"
  warn "V1b: shellcheck AUSENTE — NAO verificado localmente (o CI executa)"
fi

# ---------------------------------------------------------------------------
step "V4 — o workflow pos-patch e valido E enxerga o teste"
# ---------------------------------------------------------------------------
# Roda no dry-run TAMBEM: e barato, e e o gate que pega um patch que quebrou o
# YAML — exatamente o erro que so apareceria no push.
python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$YML" 2>/dev/null \
  && ok "V4a: yaml.safe_load OK" \
  || warn "V4a: PyYAML ausente ou parse falhou — o actionlint abaixo tambem cobre"
if command -v actionlint >/dev/null 2>&1; then
  actionlint "$YML" > "$TMPDIR_LAND/actionlint.log" 2>&1 || {
    sed 's/^/    /' "$TMPDIR_LAND/actionlint.log" >&2
    die "V4b: actionlint reprovou em $YML"; }
  ok "V4b: actionlint verde"
else
  warn "V4b: actionlint AUSENTE — o CI executa"
fi
# `unwired = no test` e a regra escrita no proprio workflow. As TRES referencias
# sao: lista de paths do `pull_request`, lista de paths do `push`, e o step que
# EXECUTA. Faltando um filtro, o job nao dispara quando o teste muda; faltando o
# step, o teste nao roda. Contagem DECLARADA, nunca ">0".
_refs_obs="$(grep -cF -- "$(basename "$E2E_TEST")" "$YML" || true)"
_refs_exp="$(_expect EXPECTED_YML_E2E_REFS)"
[ "$_refs_obs" = "$_refs_exp" ] \
  || die "V4c: $(basename "$E2E_TEST") aparece $_refs_obs vez(es) em $YML, esperado $_refs_exp.
  Sem as DUAS listas de paths e o step, a cura entra sem vigilancia e a classe
  volta — foi achado do pair-rail (rodada 1, P2) e era a OQ-E4 do desenho."
ok "V4c: o workflow referencia o e2e $_refs_obs vez(es)"
_to_obs="$( { grep -m1 'timeout-minutes:' "$YML" || true; } | sed 's/[^0-9]//g')"
_to_exp="$(_expect EXPECTED_YML_TIMEOUT_MINUTES)"
[ -n "$_to_obs" ] || die "V4d: $YML nao declara 'timeout-minutes:' — um job sem teto e outra classe de problema"
[ "$_to_obs" = "$_to_exp" ] \
  || die "V4d: timeout-minutes do job e $_to_obs, esperado $_to_exp.
  Um timeout de job que corta um run VERDE aparece como 'cancelled' num passo
  INOCENTE (a licao S2xx). Re-apertar so no p95 real de CI, nunca na aritmetica."
ok "V4d: timeout-minutes = $_to_obs (esperado $_to_exp)"

# ---------------------------------------------------------------------------
step "V5 — o invariante anti-rot no ARQUIVO landado"
# ---------------------------------------------------------------------------
# A funcao NAO pode citar nenhum nome de hook. E a regra que impede a classe de
# renascer: um segundo roster literal dentro do upgrader e exatamente o defeito
# que esta wave fecha. O teste de unidade tem a mesma assercao; aqui ela e
# repetida contra o arquivo POS-PATCH — se as duas divergirem, uma das duas
# esta medindo a coisa errada.
FN_BODY="$TMPDIR_LAND/fn-body.txt"
_fn_body "$UPGRADE" > "$FN_BODY"
_fn_lines="$(wc -l < "$FN_BODY" | tr -d ' ')"
_fn_min="$(_expect EXPECTED_UPGRADE_FN_MIN_LINES)"
# Piso de nao-vacuidade: se a ancora nao casar, o corpo sai VAZIO e o grep
# abaixo acharia zero literais — verde por medir nada.
[ "$_fn_lines" -ge "$_fn_min" ] \
  || die "V5: a extracao de $UPGRADE_FN devolveu $_fn_lines linha(s), minimo $_fn_min.
  A ancora nao casou. Um corpo vazio faria o contador de literais sair 0 e o
  gate ficaria VERDE medindo nada."
# O `|| true` no grep NAO e decoracao. `grep -o` sai 1 quando nao casa NADA, e
# ZERO literais e justamente a resposta VERDE deste gate: sob `pipefail` o
# pipeline sairia 1, a atribuicao falharia e o `set -e` mataria o land SEM
# MENSAGEM, no caso que o gate existe para aprovar. Medido no finalize-E.sh,
# que tem a mesma linha e saiu rc=1 mudo na primeira execucao real.
_lit_obs="$( { grep -oE '[A-Za-z0-9_]+\.py' "$FN_BODY" || true; } \
             | LC_ALL=C sort -u | wc -l | tr -d ' ')"
_lit_exp="$(_expect EXPECTED_UPGRADE_FN_HOOK_LITERALS)"
# O `|| true` no grep DO RAMO DE ERRO tambem e obrigatorio, e por um motivo
# menos obvio: quando o observado e 0 e o ESPERADO nao e (base declarada errada),
# este grep nao casa nada, sai 1, e sob `set -e` mataria o land ANTES do `die` —
# o gate ficaria vermelho MUDO justamente no caso em que ele tem algo a dizer.
# Achado pelo T12 do harness, que e o caso que planta exatamente esse par.
[ "$_lit_obs" = "$_lit_exp" ] \
  || { { grep -oE '[A-Za-z0-9_]+\.py' "$FN_BODY" || true; } \
         | LC_ALL=C sort -u | sed 's/^/      /' >&2
       die "V5: $UPGRADE_FN cita $_lit_obs nome(s) de arquivo .py, esperado $_lit_exp.
  Um roster literal dentro do upgrader e a classe que esta wave fecha."; }
ok "V5: $UPGRADE_FN tem $_fn_lines linhas e cita $_lit_obs nome(s) .py"

# ---------------------------------------------------------------------------
step "V6 — o roster que a derivacao entrega"
# ---------------------------------------------------------------------------
_reg_obs="$(jq '[.hooks | to_entries[] | .value[]] | length' "$TEMPLATE")"
_reg_exp="$(_expect EXPECTED_TEMPLATE_REGISTRATIONS)"
[ "$_reg_obs" = "$_reg_exp" ] \
  || die "V6: o template enumera $_reg_obs registro(s), esperado $_reg_exp.
  Um numero MENOR significa que o template encolheu — e mudanca de produto, nao
  detalhe. Atualize $BASELINE_ENV conscientemente."
ok "V6: $TEMPLATE enumera $_reg_obs registro(s) (esperado $_reg_exp)"
# V6-bis — o template USER (rail round 6, P1). A cerimonia seleciona o template
# que o merge deriva, entao um adopter `--ceremony user` recebe ESTE roster; um
# template user que encolha, ou que ganhe por engano um dos 10 hooks que ele
# omite de proposito, chegaria ao adopter em silencio. Mesmo gate, mesma razao.
[ -r "$TEMPLATE_USER" ] || die "V6-bis: $TEMPLATE_USER ausente — a selecao por cerimonia nao tem de onde derivar"
_regu_obs="$(jq '[.hooks | to_entries[] | .value[]] | length' "$TEMPLATE_USER")"
_regu_exp="$(_expect EXPECTED_TEMPLATE_REGISTRATIONS_USER)"
[ "$_regu_obs" = "$_regu_exp" ] \
  || die "V6-bis: $TEMPLATE_USER enumera $_regu_obs registro(s), esperado $_regu_exp.
  Atualize $BASELINE_ENV conscientemente."
ok "V6-bis: $TEMPLATE_USER enumera $_regu_obs registro(s) (esperado $_regu_exp)"

if [ "$DRY_RUN" = "1" ]; then
  printf '\n\033[33mDRY-RUN\033[0m — G-PRE, G0..G5 verdes; patch aplicado; V1, V4, V5 e V6 executados.\n'
  printf '  O V-block CARO (V2 unidade, V3 e2e, V7 governanca) NAO roda em dry-run.\n'
  printf '  Restaurando arvore e index...\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "V2 — suite de unidade (conjunto DECLARADO, nunca 'passou')"
# ---------------------------------------------------------------------------
PY_LOG="$TMPDIR_LAND/pytest.log"
PY_RC=0
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest "$UNIT_TEST" -q -p no:cacheprovider \
  > "$PY_LOG" 2>&1 || PY_RC=$?
tail -5 "$PY_LOG" | sed 's/^/    /'
_exp_pytest_rc="$(_expect EXPECTED_UNIT_PYTEST_RC)"
[ "$PY_RC" = "$_exp_pytest_rc" ] \
  || die "V2: pytest saiu rc=$PY_RC, esperado $_exp_pytest_rc — log em $PY_LOG"
# "N deselected" NAO e "N passed" (licao S325): o numero vem do campo `passed`.
# A linha do `pytest -q` COMECA pelo numero ("33 passed in 1.08s"), entao o
# padrao aceita inicio de linha OU um nao-digito antes.
# O `|| true` faz a mensagem NOMEADA abaixo disparar: sem ele, uma saida de
# pytest sem "N passed" mataria o land mudo na propria atribuicao.
_obs_passed="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$PY_LOG" || true; } \
                | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_obs_passed" ] || die "V2: nao consegui ler 'N passed' da saida do pytest — log em $PY_LOG"
_exp_passed="$(_expect EXPECTED_UNIT_PYTEST_PASSED)"
[ "$_obs_passed" = "$_exp_passed" ] \
  || die "V2: $_obs_passed teste(s) passaram, esperado $_exp_passed.
  Um numero MENOR e regressao; um numero MAIOR significa que a suite cresceu —
  atualize $BASELINE_ENV conscientemente. Log: $PY_LOG"
ok "V2: $_obs_passed/$_exp_passed testes de unidade verdes (rc=$PY_RC)"

# ---------------------------------------------------------------------------
step "V3 — e2e com install e upgrade REAIS (~9 min; o gate caro)"
# ---------------------------------------------------------------------------
if [ "$SKIP_E2E" = "1" ]; then
  E2E_STATUS="PULADO por CEO_E_HARNESS_SKIP_E2E=1 (so o harness)"
  warn "V3 PULADO — CEO_E_HARNESS_SKIP_E2E=1 sob o modo auto-teste."
  warn "        Isto NAO e possivel num land real; o gate abortaria antes."
else
  printf '  isto demora ~9 min (8 fixtures de adopter, 10 upgrades reais)...\n'
  E2E_LOG="$TMPDIR_LAND/e2e.log"
  E2E_RC=0
  bash "$E2E_TEST" > "$E2E_LOG" 2>&1 || E2E_RC=$?
  tail -6 "$E2E_LOG" | sed 's/^/    /'
  _exp_e2e_rc="$(_expect EXPECTED_E2E_RC)"
  [ "$E2E_RC" = "$_exp_e2e_rc" ] \
    || die "V3: o e2e saiu rc=$E2E_RC, esperado $_exp_e2e_rc — log em $E2E_LOG"
  # A linha final tem a forma EXATA `RESULT: <N> passed, <M> failed`.
  _res_line="$(grep -m1 '^RESULT:' "$E2E_LOG" || printf '')"
  [ -n "$_res_line" ] || die "V3: o e2e nao imprimiu a linha 'RESULT:' — log em $E2E_LOG"
  _e2e_passed="$(printf '%s' "$_res_line" | sed -n 's/^RESULT: \([0-9][0-9]*\) passed.*/\1/p')"
  _e2e_failed="$(printf '%s' "$_res_line" | sed -n 's/^RESULT: [0-9][0-9]* passed, \([0-9][0-9]*\) failed.*/\1/p')"
  [ -n "$_e2e_passed" ] && [ -n "$_e2e_failed" ] \
    || die "V3: nao consegui parsear '$_res_line' — log em $E2E_LOG"
  _exp_e2e_passed="$(_expect EXPECTED_E2E_PASSED)"
  _exp_e2e_failed="$(_expect EXPECTED_E2E_FAILED)"
  [ "$_e2e_failed" = "$_exp_e2e_failed" ] \
    || die "V3: $_e2e_failed asercao(oes) do e2e falharam, esperado $_exp_e2e_failed — log em $E2E_LOG"
  [ "$_e2e_passed" = "$_exp_e2e_passed" ] \
    || die "V3: $_e2e_passed asercao(oes) do e2e passaram, esperado $_exp_e2e_passed.
  Um numero MENOR e regressao (ou um caso que degradou para SKIP: E.3 e E.9
  comparam contra \`git HEAD\` e viram SKIP DEPOIS deste land — antes dele nao
  deveriam). Um numero MAIOR significa que a suite cresceu: atualize
  $BASELINE_ENV conscientemente. Log: $E2E_LOG"
  E2E_STATUS="$_e2e_passed passed / $_e2e_failed failed"
  ok "V3: e2e $_e2e_passed/$_exp_e2e_passed passed, $_e2e_failed failed (rc=$E2E_RC)"
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

bash .claude/scripts/validate-governance.sh --fast >/dev/null \
  || die "V7b: validate-governance.sh --fast FALHOU"
ok "V7b: validate-governance.sh --fast verde"

# O land do pacote D (S329) deixou o main VERMELHO porque um doc GERADO nao foi
# regenerado: `docs/COMMAND-SKILL-HOOK-MAP.md` nao continha o hook novo. Este
# pacote nao adiciona hook, mas o gate custa milissegundos e a licao foi paga.
python3 .claude/scripts/gen-command-skill-hook-map.py --check >/dev/null \
  || die "V7c: gen-command-skill-hook-map.py --check acusou DRIFT.
  Regenere (sem --check) e inclua o doc no patch — foi assim que o land do
  pacote D deixou o main vermelho na S329."
ok "V7c: COMMAND-SKILL-HOOK-MAP.md sem drift"

python3 .claude/scripts/check-test-env-hygiene.py >/dev/null \
  || die "V7d: check-test-env-hygiene.py reprovou — um teste novo toca o \$HOME real"
ok "V7d: check-test-env-hygiene.py verde"

if [ -f .claude/scripts/check-claude-md-claims.py ]; then
  python3 .claude/scripts/check-claude-md-claims.py >/dev/null \
    || die "V7e: check-claude-md-claims.py reprovou"
  ok "V7e: check-claude-md-claims.py verde"
else
  warn "V7e: check-claude-md-claims.py ausente — nao verificado"
fi

bash .claude/scripts/local/verify-counts.sh --quiet >/dev/null 2>&1 \
  || die "V7f: verify-counts.sh reprovou apos o land (contagens derivadas desatualizadas)"
ok "V7f: verify-counts.sh verde"

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

# O bit de execucao dos dois scripts shell tem de viajar no index. `git apply`
# preserva o modo do patch, mas um `update-index --chmod` anterior no checkout
# do Owner poderia diverge-lo (licao CLAUDE.md §4: o chmod sozinho nao gruda).
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    "$E2E_TEST")
      _mode="$(git ls-files --stage -- "$f" | awk '{print $1}')"
      case "$_mode" in
        100755) : ;;
        *) die "o modo de $f no index e $_mode, esperado 100755.
  O CI invoca com \`bash <path>\`, mas os vizinhos deste diretorio sao
  executaveis e a divergencia confunde quem le \`ls -l\`." ;;
      esac ;;
  esac
done < "$STAGED_FILE"
ok "modo de execucao do e2e coerente no index"

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
  V2 unidade    : $_obs_passed teste(s)
  V3 e2e        : $E2E_STATUS

  Ultimos runs de CI:
EOF
if command -v gh >/dev/null 2>&1 && [ "$SELFTEST" = "0" ]; then
  gh run list --limit 3 2>&1 | sed 's/^/    /' || printf '    (gh run list indisponivel)\n'
else
  printf '    (gh ausente — acompanhe em https://github.com/Canhada-Labs/ceo-orchestration/actions)\n'
fi
cat <<'EOF'

  LEMBRETE — o que observar depois deste land:
  1. O `Smoke Install` passa a rodar um e2e a mais. O `timeout-minutes` de 96 e
     uma ESTIMATIVA no fator 2-3x de runner; a PRIMEIRA execucao real e o
     numero que deve substitui-la. Re-apertar no p95 observado, nunca na
     aritmetica — um timeout que corta um run verde reporta como `cancelled`
     num passo inocente.
  2. Os casos `E.3` e `E.9` do e2e comparam contra `git HEAD`. Com a cura em
     HEAD eles degradam para SKIP explicito, com instrucao de re-armar. Isso e
     por desenho (sao medicoes historicas), mas e um verde que muda de
     significado — a classe "instrumento verde cuja PERGUNTA envelheceu".
  3. Ficam abertas as OQ-E1 (denylist de opt-out por hook) e OQ-E6 (quem REPARA
     um registro deformado — hoje ninguem). As duas sao chamada do Owner.

  Se algum editor abrir em QUALQUER momento:
    aperte Esc, digite  :q!  e Enter  (sai sem salvar; nada se perde).
EOF
