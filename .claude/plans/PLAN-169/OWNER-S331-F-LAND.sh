#!/usr/bin/env bash
# OWNER-S331-F-LAND.sh — land do pacote de cerimônia wave-s330-F (PLAN-169).
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
#   bash .claude/plans/PLAN-169/OWNER-S331-F-LAND.sh --dry-run
#   bash .claude/plans/PLAN-169/OWNER-S331-F-LAND.sh
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
CEREMONY_DIR="$PLAN_DIR/s330-ceremony-F"
SENTINEL="$PLAN_DIR/wave-s330-F-approved.md"
PATCH="$CEREMONY_DIR/F.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-F.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S331-F-SIGN.sh"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
GENERATOR=".claude/scripts/gen-settings-user-template.py"
BUILD_PLUGIN="scripts/build-plugin.py"
YML=".github/workflows/validate.yml"
TEMPLATE="templates/settings/settings.base.json"
TEMPLATE_USER="templates/settings/settings.user.json"
ADR_NEW=".claude/adr/ADR-197-user-profile-derivation.md"
UNIT_TESTS=".claude/scripts/tests/test_gen_settings_user_template.py \
.claude/scripts/tests/test_install_user_skips_governance_hooks.py \
.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py \
.claude/hooks/tests/test_template_dogfood_parity.py \
.claude/scripts/tests/test_build_plugin_idempotency.py \
.claude/scripts/tests/test_check_install_profiles.py \
.claude/scripts/tests/test_generate_adr_index.py"
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
# V3 dele custava ~9 min de instalacao real. O V-block desta wave inteiro roda
# em menos de um minuto — nao ha gate caro para pular, entao nao ha rota para
# calar nenhum. Um interruptor sem razao de existir e superficie de ataque.

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
  Sem ela cada execucao do V-block e ruido. Rode o finalize-F.sh."
# Checagem COMPORTAMENTAL (o binario responde?), nunca por string de versao:
# `jq --version` aqui devolve `jq-1.7.1-apple`, e comparar texto de versao com
# sufixo de vendor ja quebrou neste repositorio.
if [ "$(_expect EXPECTED_JQ_REQUIRED)" = "1" ]; then
  command -v jq >/dev/null 2>&1 \
    || die "G-PRE: jq AUSENTE — o V6 conta os registros dos dois templates com ele"
  printf '{"hooks":{}}' | jq '[.hooks | to_entries[] | .value[]] | length' >/dev/null 2>&1 \
    || die "G-PRE: o jq desta maquina nao executa o programa que o V6 usa."
  ok "G-PRE: jq responde ($( jq --version 2>/dev/null || printf '?' ))"
fi
[ -f "$TEMPLATE" ] || die "G-PRE: $TEMPLATE ausente — o template user e DERIVADO dele"
[ -f "$TEMPLATE_USER" ] || die "G-PRE: $TEMPLATE_USER ausente — e o entregavel da wave"
[ -f "$GENERATOR" ] || die "G-PRE: $GENERATOR ausente — sem ele a paridade nao e verificavel"
ok "G-PRE: os dois templates e o gerador presentes"

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
  "$PLAN_DIR/OWNER-S331-F-LAND.sh"
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
# isto, um patch que perdesse o `templates/settings/settings.user.json` (o
# entregavel da wave!) e carregasse so os testes passaria pelo bloco acima:
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
step "V1 — o que o patch toca compila"
# ---------------------------------------------------------------------------
# Esta wave NAO toca script shell nenhum — e isso e uma afirmacao, nao uma
# omissao. O pacote E tocava dois (`upgrade.sh` e o e2e) e o V1 dele exigia
# `SH_COUNT >= 2`; aqui o numero certo e ZERO, e um `.sh` aparecendo no patch
# significa que o escopo mudou sem ninguem decidir. Os dois gates coexistem
# pela mesma razao: um V1 que aceita qualquer contagem nao mede nada.
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
# Zero .py seria o V1 medindo a coisa errada: o gerador, o guard e o
# build-plugin sao o coracao do patch.
[ "$PY_COUNT" -ge 3 ] || die "V1: so $PY_COUNT arquivo(s) Python no patch — esperava ao menos 3
  ($GENERATOR, $BUILD_PLUGIN e o teste-guard). Um V1 vazio e um gate morto."
while IFS= read -r f; do
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$f" \
    || die "V1a: py_compile reprovou em $f"
done < "$PY_LIST"
ok "V1a: py_compile verde em $PY_COUNT arquivo(s) Python (0 shell, como esperado)"
SHELLCHECK_STATUS="nao aplicavel (a wave nao toca script shell)"

# ---------------------------------------------------------------------------
step "V4 — o workflow pos-patch e valido E invoca o gate de derivacao"
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
# `unwired = no test`. A cobertura da paridade ja existe pela coleta da suite;
# este step existe para NOMEAR a falha e imprimir o comando de reparo. Se a
# referencia sumir, a wave perdeu o gate que a OQ-F3 pediu.
_gref_obs="$( { grep -c 'gen-settings-user-template.py --check' "$YML" || true; } )"
_gref_exp="$(_expect EXPECTED_YML_GEN_CHECK_REFS)"
[ "$_gref_obs" = "$_gref_exp" ] \
  || die "V4c: o gate de derivacao aparece $_gref_obs vez(es) em $YML, esperado $_gref_exp."
ok "V4c: o workflow invoca o gate de derivacao $_gref_obs vez(es)"

# ---------------------------------------------------------------------------
step "V5 — a paridade da derivacao, no ARQUIVO landado"
# ---------------------------------------------------------------------------
# O gate central da wave, repetido aqui contra a arvore POS-PATCH. A suite tem
# a mesma assercao; se as duas divergirem, uma das duas esta medindo a coisa
# errada. Contrato: 0 in-sync / 1 drift / 2 input inutilizavel.
GEN_RC=0
python3 "$GENERATOR" --check > "$TMPDIR_LAND/gen-check.log" 2>&1 || GEN_RC=$?
_gen_exp="$(_expect EXPECTED_GEN_CHECK_RC)"
[ "$GEN_RC" = "$_gen_exp" ] || { head -20 "$TMPDIR_LAND/gen-check.log" | sed 's/^/    /' >&2
  die "V5a: '$GENERATOR --check' saiu rc=$GEN_RC, esperado $_gen_exp.
  rc 1 = o template no disco NAO e o que o _derivation dele produz;
  rc 2 = o spec sumiu ou perdeu a chave (fail-closed por desenho).
  Reparo:  python3 $GENERATOR --write"; }
ok "V5a: paridade da derivacao verde (rc=$GEN_RC)"

# O guard invertido do FU-F-ACCEL. Ele e a razao de $BUILD_PLUGIN estar no
# patch; se ele nao roda, a reconciliacao entra sem vigia.
GUARD_LOG="$TMPDIR_LAND/plugin-guard.log"
GUARD_RC=0
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  .claude/scripts/tests/test_gen_settings_user_template.py -k PluginHooks \
  -q -p no:cacheprovider > "$GUARD_LOG" 2>&1 || GUARD_RC=$?
[ "$GUARD_RC" -eq 0 ] || { tail -25 "$GUARD_LOG" | sed 's/^/    /' >&2
  die "V5b: o guard PluginHooksHaveNoParallelSource reprovou — log em $GUARD_LOG"; }
_guard_obs="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$GUARD_LOG" || true; } \
               | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_guard_obs" ] || die "V5b: nao consegui ler 'N passed' — log em $GUARD_LOG"
_guard_exp="$(_expect EXPECTED_PLUGIN_GUARD_PASSED)"
[ "$_guard_obs" = "$_guard_exp" ] \
  || die "V5b: o guard rodou $_guard_obs teste(s), esperado $_guard_exp — log em $GUARD_LOG"
ok "V5b: guard do plugin $_guard_obs/$_guard_exp"

# ---------------------------------------------------------------------------
step "V6 — os rosters: os dois templates e o que o plugin emite"
# ---------------------------------------------------------------------------
if command -v jq >/dev/null 2>&1; then
  _reg_obs="$( jq '[.hooks | to_entries[] | .value[]] | length' "$TEMPLATE" )"
  _reg_exp="$(_expect EXPECTED_TEMPLATE_REGISTRATIONS)"
  [ "$_reg_obs" = "$_reg_exp" ] \
    || die "V6a: $TEMPLATE enumera $_reg_obs registro(s), esperado $_reg_exp."
  ok "V6a: $TEMPLATE enumera $_reg_obs registro(s)"
  _regu_obs="$( jq '[.hooks | to_entries[] | .value[]] | length' "$TEMPLATE_USER" )"
  _regu_exp="$(_expect EXPECTED_TEMPLATE_REGISTRATIONS_USER)"
  [ "$_regu_obs" = "$_regu_exp" ] \
    || die "V6b: $TEMPLATE_USER enumera $_regu_obs registro(s), esperado $_regu_exp.
  Este numero E o produto da wave (20 -> 30): 10 registros novos chegam ao
  adopter --ceremony user no proximo upgrade. Se ele mudou de novo, alguem
  mexeu no spec _derivation — decida conscientemente antes de tocar
  $BASELINE_ENV."
  ok "V6b: $TEMPLATE_USER enumera $_regu_obs registro(s)"
else
  die "V6: jq AUSENTE — o G-PRE deveria ter abortado antes daqui"
fi

# O que o PLUGIN emite. A metrica da cura do FU-F-ACCEL medida no entregavel e
# nao no teste: antes da cura os quatro aceleradores apareciam DUAS vezes cada
# (o template registrava, o ACCEL re-adicionava com outro timeout) e este
# numero era 4.
PLUG_OUT="$( python3 - <<'PYEOF' 2>/dev/null || true
import importlib.util
spec = importlib.util.spec_from_file_location("bp", "scripts/build-plugin.py")
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
hooks = bp.compose_plugin_hooks(bp.USER_TEMPLATE)
t = [(e, b.get("matcher", ""), h.get("command", ""))
     for e, a in hooks.items() for b in a for h in b.get("hooks", [])]
blob = bp.dump_manifest_hooks(hooks)
print("%d %d %d" % (len(t), len(t) - len(set(t)),
                    1 if "_derivation" in blob else 0))
PYEOF
)"
[ -n "$PLUG_OUT" ] || die "V6c: nao consegui compor os hooks do plugin — $BUILD_PLUGIN mudou de forma?"
_plug_n="$( printf '%s' "$PLUG_OUT" | awk '{print $1}' )"
_plug_d="$( printf '%s' "$PLUG_OUT" | awk '{print $2}' )"
_plug_s="$( printf '%s' "$PLUG_OUT" | awk '{print $3}' )"
[ "$_plug_n" = "$(_expect EXPECTED_PLUGIN_REGISTRATIONS)" ] \
  || die "V6c: o plugin registra $_plug_n hook(s), esperado $(_expect EXPECTED_PLUGIN_REGISTRATIONS)"
[ "$_plug_d" = "$(_expect EXPECTED_PLUGIN_DUPLICATE_TRIPLES)" ] \
  || die "V6d: o plugin tem $_plug_d registracao(oes) DUPLICADA(s), esperado
  $(_expect EXPECTED_PLUGIN_DUPLICATE_TRIPLES). Valor > 0 significa que uma
  segunda fonte de registros voltou ao $BUILD_PLUGIN — o defeito que o
  FU-F-ACCEL fechou."
[ "$_plug_s" = "0" ] \
  || die "V6e: a chave _derivation (~20 KB de spec) VAZOU para o hooks.json do
  plugin. So .hooks deve viajar."
ok "V6c-e: plugin $_plug_n registro(s), $_plug_d duplicata(s), spec nao vaza"
# Os quatro aceleradores do PLAN-128 chegam pela derivacao, cada um UMA vez.
# Antes do FU-F-ACCEL vinham da tabela ACCEL; um 0 aqui significa que o spec
# passou a exclui-los — decisao legitima, mas NAO uma que passe em silencio.
_plug_a="$( python3 - <<'PYEOF' 2>/dev/null || true
import importlib.util
spec = importlib.util.spec_from_file_location("bp", "scripts/build-plugin.py")
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
gen = importlib.util.spec_from_file_location(
    "gen", ".claude/scripts/gen-settings-user-template.py")
g = importlib.util.module_from_spec(gen); gen.loader.exec_module(g)
hooks = bp.compose_plugin_hooks(bp.USER_TEMPLATE)
accel = {"accel_dispatch.py", "codex_review_user_code.py",
         "review_loop.py", "turbo_sessionstart.py"}
print(sum(1 for e, a in hooks.items() for b in a for h in b.get("hooks", [])
          if g.hook_basename(h.get("command")) in accel))
PYEOF
)"
[ -n "$_plug_a" ] || die "V6f: nao consegui contar os aceleradores no plugin"
[ "$_plug_a" = "$(_expect EXPECTED_PLUGIN_ACCELERATORS)" ] \
  || die "V6f: o plugin registra $_plug_a acelerador(es), esperado
  $(_expect EXPECTED_PLUGIN_ACCELERATORS). Um a menos e perda silenciosa do
  loop de aceleracao; um a mais e uma segunda fonte de registros."
ok "V6f: $_plug_a acelerador(es) do PLAN-128 chegam pela derivacao"

# Basenames DISTINTOS no template user. O numero de registros (V6b) e o de
# basenames respondem coisas diferentes: dois eventos podem registrar o mesmo
# hook, e uma queda so nos basenames seria um hook inteiro sumindo enquanto a
# contagem de registros se mantem.
_regu_b="$( jq -r '[.hooks | to_entries[] | .value[] | .hooks[] | .command] | length' "$TEMPLATE_USER" >/dev/null 2>&1 && python3 - <<'PYEOF' 2>/dev/null || true
import importlib.util, json
gen = importlib.util.spec_from_file_location(
    "gen", ".claude/scripts/gen-settings-user-template.py")
g = importlib.util.module_from_spec(gen); gen.loader.exec_module(g)
doc = json.load(open("templates/settings/settings.user.json"))
print(len({g.hook_basename(h.get("command"))
           for e, a in doc["hooks"].items() for b in a for h in b.get("hooks", [])}))
PYEOF
)"
[ -n "$_regu_b" ] || die "V6g: nao consegui contar os basenames do template user"
[ "$_regu_b" = "$(_expect EXPECTED_TEMPLATE_USER_BASENAMES)" ] \
  || die "V6g: $TEMPLATE_USER tem $_regu_b basename(s) distinto(s), esperado
  $(_expect EXPECTED_TEMPLATE_USER_BASENAMES)."
ok "V6g: $_regu_b basename(s) distinto(s) no template user"

# O corte do dry-run. Ele fica AQUI, depois dos gates baratos que operam sobre
# a arvore JA PATCHADA (V1, V4, V5, V6) e antes dos caros — a mesma posicao que
# o pacote E usava. Sem ele o `--dry-run` seguiria ate o staging e o commit,
# que e o oposto exato do que a flag promete. O trap restaura arvore e index.
if [ "$DRY_RUN" = "1" ]; then
  printf '\n\033[33mDRY-RUN\033[0m — G-PRE, G0..G5 verdes; patch aplicado; V1, V4, V5 e V6 executados.\n'
  printf '  O V-block CARO (V2 unidade, V3 ADRs, V7 governanca) NAO roda em dry-run.\n'
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
step "V3 — o ADR e o indice que o verify-counts cobra"
# ---------------------------------------------------------------------------
# Esta wave nao tem e2e de instalacao (o pacote F tinha). O gate que ocupa este
# lugar e o que o land do pacote D mostrou ser caro esquecer: um doc GERADO que
# nao foi regenerado deixa o main VERMELHO depois do push.
[ -f "$ADR_NEW" ] || die "V3a: $ADR_NEW ausente na arvore pos-patch"
_adr_obs="$( find .claude/adr -maxdepth 1 -name 'ADR-*.md' | wc -l | tr -d ' ' )"
_adr_exp="$(_expect EXPECTED_ADR_COUNT)"
[ "$_adr_obs" = "$_adr_exp" ] \
  || die "V3a: $_adr_obs ADR(s) no disco, esperado $_adr_exp — as 15 citacoes em
  docs ficariam defasadas e o V8 reprovaria."
ok "V3a: $_adr_obs ADRs no disco"
IDX_RC=0
python3 .claude/scripts/generate-adr-index.py --check >/dev/null 2>&1 || IDX_RC=$?
[ "$IDX_RC" = "$(_expect EXPECTED_ADR_INDEX_CHECK_RC)" ] \
  || die "V3b: o indice de ADRs saiu rc=$IDX_RC, esperado $(_expect EXPECTED_ADR_INDEX_CHECK_RC).
  Reparo:  python3 .claude/scripts/generate-adr-index.py --write
  (Nota: este gate NAO roda em CI — FU-F-ADRGATE, DESIGN-F §7.4. Ele existe
  aqui porque o patch mexe no indice.)"
ok "V3b: indice de ADRs em dia"
# `check-adr-chain.py` sai 1 com 11 erros PRE-EXISTENTES no main. O gate compara
# o NUMERO, nao exige zero: exigir zero reprovaria um patch inocente, e ignorar
# deixaria o patch introduzir um 12o erro em silencio.
CHAIN_LOG="$TMPDIR_LAND/adr-chain.log"
python3 .claude/scripts/check-adr-chain.py > "$CHAIN_LOG" 2>&1 || true
_chain_obs="$( { grep -oE '^FAIL: [0-9]+ error' "$CHAIN_LOG" || true; } | { grep -oE '[0-9]+' || true; } | head -1 )"
[ -n "$_chain_obs" ] || _chain_obs=0
_chain_exp="$(_expect EXPECTED_ADR_CHAIN_ERRORS)"
[ "$_chain_obs" -le "$_chain_exp" ] \
  || die "V3c: check-adr-chain acusa $_chain_obs erro(s), a base declara $_chain_exp.
  O patch introduziu erro(s) NOVO(s) na cadeia de ADRs — log em $CHAIN_LOG."
ok "V3c: cadeia de ADRs com $_chain_obs erro(s) (base pre-existente: $_chain_exp)"

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

GOV_LOG="$TMPDIR_LAND/validate-governance.log"
bash .claude/scripts/validate-governance.sh --fast > "$GOV_LOG" 2>&1 \
  || { tail -20 "$GOV_LOG" | sed 's/^/    /' >&2
       die "V7b: validate-governance.sh --fast FALHOU — log em $GOV_LOG"; }
# rc 0 nao e a resposta inteira: o script reporta "Errors: N" e a base declara
# o N esperado. Um gate que so olha o rc aceitaria um relatorio que passou a
# contar erros sem mudar o exit.
# `-i` e ancora de linha, medidos: o modo `--fast` imprime `errors:   0` em
# MINUSCULO (o modo completo usa `Errors:`), e sem a ancora o `-i` casaria
# tambem a palavra dentro de uma frase de relatorio. E o fallback para 0 saiu:
# ele transformava "nao consegui ler" em "zero erros" — um gate que passa por
# nao encontrar o proprio sujeito e a definicao de vacuo.
_gov_obs="$( { grep -oiE '^[[:space:]]*errors:[[:space:]]+[0-9]+' "$GOV_LOG" || true; } \
             | { grep -oE '[0-9]+' || true; } | head -1 )"
[ -n "$_gov_obs" ] || die "V7b: nao consegui ler a contagem de erros em $GOV_LOG —
  o relatorio mudou de forma. Um gate que nao acha o proprio sujeito nao passa." 
[ "$_gov_obs" = "$(_expect EXPECTED_GOVERNANCE_ERRORS)" ] \
  || die "V7b: validate-governance reporta $_gov_obs erro(s), esperado
  $(_expect EXPECTED_GOVERNANCE_ERRORS) — log em $GOV_LOG"
ok "V7b: validate-governance.sh --fast verde ($_gov_obs erro(s))"

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

# O ratchet do censo installer-write-safety. Esta wave nao toca `.sh`, entao a
# regra "wave que toca scripts/ regenera o baseline" NAO dispara — medido: o
# censo varre `.sh` e `build-plugin.py` e Python, com zero entradas no baseline.
# O gate roda mesmo assim: e barato, e um `.sh` que entre no patch sem
# regeneracao e exatamente o que ele existe para pegar.
RATCHET_RC=0
python3 .claude/scripts/check-installer-write-safety.py >/dev/null 2>&1 || RATCHET_RC=$?
[ "$RATCHET_RC" = "$(_expect EXPECTED_RATCHET_RC)" ] \
  || die "V7g: check-installer-write-safety saiu rc=$RATCHET_RC, esperado
  $(_expect EXPECTED_RATCHET_RC). Se um sitio novo entrou, regenere o baseline
  no MESMO patch:  python3 .claude/scripts/check-installer-write-safety.py --write-baseline"
ok "V7g: ratchet installer-write-safety verde"

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

# Esta wave nao adiciona script executavel, entao o gate de modo do pacote E
# nao tem sujeito aqui. O que ele checa em seu lugar: NENHUM path do patch
# entrou no index com o bit de execucao ligado por acidente — um `.json`, um
# `.md` ou um `.yml` executavel e ruido que o `git add -A` de um dia carrega
# adiante (CLAUDE.md §4: o `--chmod=-x` sozinho nao gruda).
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
  1. O proximo `upgrade.sh` de um adopter `--ceremony user` REGISTRA 10 HOOKS
     NOVOS (o roster vai de 20 para 30). E o ponto da OQ-E5, nao um efeito
     colateral — mas e mudanca de produto em campo, e os riscos por hook estao
     na classificacao §5. Dois merecem atencao: `check_config_change.py` entra
     com `CEO_CONFIG_CHANGE_GUARD=1` explicito, e `codex_review_user_code.py` e
     DETECT-ONLY por default.
  2. O plugin passa a rodar `review_loop.py` com 15 s e `turbo_sessionstart.py`
     com 5 s (eram 60 e 10 na tabela ACCEL removida). Alinhado a base e ao
     `.claude/settings.json` vivo — mas e mudanca de comportamento, registrada
     no ADR-197 §Consequences.
  3. `EXPECTED_TEMPLATE_REGISTRATIONS_USER=20` em
     `s329-ceremony-E/EXPECTED-BASELINE.txt:182` fica DEFASADO POR DECISAO.
     Nao o reescreva: e baseline historica de cerimonia ja landada.
  4. FU-F-ADRGATE fica ABERTO: `check-adr-chain.py` e `generate-adr-index.py`
     NAO rodam em CI. O indice estava congelado em 170 ADRs com 198 no disco, e
     a cadeia sai com 11 erros pre-existentes. Wave propria.
  5. O ADR-197 entra como PROPOSED. O flip para ACCEPTED e cerimonia propria —
     a ratificacao real e o `.asc` sobre o sentinel, nao o commit que reescreve
     o campo (o mesmo que ADR-194 e ADR-196 registraram).

  Se algum editor abrir em QUALQUER momento:
    aperte Esc, digite  :q!  e Enter  (sai sem salvar; nada se perde).
EOF
