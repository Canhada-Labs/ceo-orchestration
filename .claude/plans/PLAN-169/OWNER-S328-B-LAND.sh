#!/usr/bin/env bash
# OWNER-S328-B-LAND.sh — land do pacote de cerimônia wave-s328-B (PLAN-169).
# CEREMONY-LINT: handwritten-exception: clone gate-a-gate do OWNER-S328-A-LAND.sh
# (por sua vez provado num land REAL, 6304f66 / 738007e). Muda o bloco de
# constantes E o V-block, que aqui exercita o GATE DE LATENCIA — nao a paridade
# de ownership do PLAN-183: um V-block copiado testaria a coisa errada e seria
# verde vazio. O gerador `.claude/scripts/generate-ceremony.sh` NAO serve: ele
# assume o layout `architect/round-N/approved.md`, e esta cerimonia usa
# `PLAN-NNN/wave-*-approved.md` com land por PATCH. O G4 `touched - scope = 0`
# so existe automatizado nesta familia de scripts.
#
# Roda de QUALQUER diretorio. Nenhum passo e destrutivo antes de todos os
# gates passarem. Ao fim ele COMMITA (com -F, sem abrir editor) e EMPURRA.
#
# Uso:
#   bash .claude/plans/PLAN-169/OWNER-S328-B-LAND.sh --dry-run
#   bash .claude/plans/PLAN-169/OWNER-S328-B-LAND.sh
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
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-B"
SENTINEL="$PLAN_DIR/wave-s328-B-approved.md"
PATCH="$CEREMONY_DIR/B.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-B.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S328-B-SIGN.sh"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la); copia-lo
# para ca criaria um segundo original divergente.
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
# A metade NAO-CANONICA que este pacote pressupoe em HEAD (commit comum do CEO).
PROFILER=".claude/scripts/profile-opus-4-7.py"
GATE_TEST=".claude/scripts/tests/test_hook_latency_relative_gate.py"
PLAN_MD="$PLAN_DIR-closure-and-cross-session-evolution.md"
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
  printf '\033[33m  MODO AUTO-TESTE\033[0m — GPG, V-block longo e push desligados.\n'
fi

SHELLCHECK_STATUS="nao-executado"

# Leitor da base esperada: sem `source` (o arquivo nao executa nada), e
# fail-CLOSED quando a chave falta. Declarado ANTES do G-PRE, que ja o usa.
_expect() {
  _ev="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
  if [ -z "$_ev" ]; then
    die "chave '$1' AUSENTE em $BASELINE_ENV — o V-block nao compara contra nada"
  fi
  printf '%s' "$_ev"
}

# ---------------------------------------------------------------------------
step "G-PRE — a metade NAO-CANONICA tem de estar em HEAD"
# ---------------------------------------------------------------------------
# Este pacote e SO a superficie canonica. A logica (referencia ref_exec,
# classificador, rotulos, exit map) vive no profiler NAO-canonico e no seu
# teste, que entram no main por commit comum do CEO. Se eles nao estiverem em
# HEAD, o workflow passaria flags que o profiler nao conhece e o job ficaria
# vermelho em todo push (pair-rail rodada 1, P1-1).
#
# A checagem e contra `git show HEAD:` e NAO contra a arvore de trabalho: hoje
# a arvore JA tem a cura e o HEAD NAO, entao um `grep` no working tree passaria
# e mediria a coisa errada. O que vai para o CI e o HEAD.
[ -f "$BASELINE_ENV" ] || die "base esperada AUSENTE: $BASELINE_ENV
  Sem ela cada execucao do V-block e ruido. Rode o finalize-B.sh."
_head_profiler="$(git show "HEAD:$PROFILER" 2>/dev/null || printf '')"
[ -n "$_head_profiler" ] || die "G-PRE: $PROFILER nao existe em HEAD"
MISSING_FLAGS=""
for _flag in $(_expect EXPECTED_HELP_FLAGS); do
  # Ancorado por FRONTEIRA de palavra, nunca substring: um profiler que
  # declarasse `--exec-reference-v2` e NAO `--exec-reference` passaria num
  # `grep -c -- "$_flag"` e reprovaria na CI. O caso T8 do harness planta
  # exatamente essa forma.
  _n="$(printf '%s\n' "$_head_profiler" \
        | grep -cE -- "(^|[^A-Za-z0-9_-])${_flag}([^A-Za-z0-9_-]|\$)" || true)"
  [ "$_n" -ge 1 ] || MISSING_FLAGS="$MISSING_FLAGS $_flag"
done
if [ -n "$MISSING_FLAGS" ]; then
  die "G-PRE: o profiler em HEAD NAO conhece a(s) flag(s):$MISSING_FLAGS

  Este pacote canonico faz o \`validate.yml\` passar essas flags. Sem a metade
  nao-canonica em HEAD, o gate sairia 2 (\"unrecognized arguments\") em TODO
  push. Commite antes:
    $PROFILER
    $GATE_TEST
  (sao NAO-canonicos — o oraculo responde 0 — e nao precisam de cerimonia)."
fi
git show "HEAD:$GATE_TEST" >/dev/null 2>&1 \
  || die "G-PRE: $GATE_TEST nao existe em HEAD — a suite que o V2 roda nao esta commitada"
ok "G-PRE: profiler em HEAD conhece as $(_expect EXPECTED_HELP_FLAGS | wc -w | tr -d ' ') flags; teste do gate presente"

# As emendas apontam para PLAN-169 §Open questions OQ-7..OQ-12. Um ADR canonico
# que referencia uma secao inexistente e evidencia quebrada (pair-rail r1, P2-4).
_oq_n="$(git show "HEAD:$PLAN_MD" 2>/dev/null | grep -cE 'OQ-(7|8|9|10|11|12)' || true)"
_oq_min="$(_expect EXPECTED_PLAN_OQ_MIN)"
[ "$_oq_n" -ge "$_oq_min" ] \
  || die "G-PRE: $PLAN_MD em HEAD tem $_oq_n referencia(s) a OQ-7..OQ-12, minimo $_oq_min.
  As duas emendas deste patch apontam para essas perguntas; sem elas em HEAD o
  ADR canonico referenciaria uma secao que nao existe. Commite o plano antes."
ok "G-PRE: OQ-7..OQ-12 presentes em HEAD ($_oq_n ocorrencia(s), minimo $_oq_min)"

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
  "$PLAN_DIR/OWNER-S328-B-LAND.sh"
  "$PROPOSED"
  "$COMMIT_MSG"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-B.sh"
  "$CEREMONY_DIR/test-ceremony-scripts-B.sh"
  "$CEREMONY_DIR/README-B.md"
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
  die "o patch toca path(s) FORA do Scope assinado:
$(printf '  %s\n' $EXTRA)
  Um Scope que nao cobre um path tocado invalida a autorizacao."
fi
GHOST="$(comm -13 "$TOUCHED_FILE" "$SCOPE_FILE")"
if [ -n "$GHOST" ]; then
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

# Conjunto EXATO de paths tocados, contra a base declarada. Uma cerimonia que
# so conta arquivos aceitaria um patch com os 3 paths ERRADOS.
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

# O numero de membros tocados tambem e comparado contra a base DECLARADA: o
# bloco acima so aborta quando ha membro tocado SEM o manifesto no patch; se um
# membro entrasse no patch em silencio, o gate estrutural passaria.
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
# verdade para rodar o V1/V6 sobre o conteudo REAL pos-patch, e restaura no
# trap (dry-run que deixa `git apply` no index e a armadilha da S272).
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
if [ "$SH_COUNT" -eq 0 ]; then
  ok "V1: nenhum script shell no patch (esperado: o patch e 1 yml + 2 ADRs)"
  SHELLCHECK_STATUS="nao-aplicavel"
else
  while IFS= read -r f; do
    bash -n "$f" || die "V1: 'bash -n' reprovou em $f"
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
fi

# ---------------------------------------------------------------------------
step "V6 — o workflow pos-patch e valido e os literais sobreviveram"
# ---------------------------------------------------------------------------
# Roda no dry-run TAMBEM: e barato, e e o gate que pega um patch que quebrou o
# YAML — exatamente o erro que so apareceria no push.
YML=".github/workflows/validate.yml"
python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$YML" 2>/dev/null \
  && ok "V6a: yaml.safe_load OK" \
  || warn "V6a: PyYAML ausente ou parse falhou — o actionlint abaixo tambem cobre"
if command -v actionlint >/dev/null 2>&1; then
  actionlint "$YML" > "$TMPDIR_LAND/actionlint.log" 2>&1 || {
    sed 's/^/    /' "$TMPDIR_LAND/actionlint.log" >&2
    die "V6b: actionlint reprovou em $YML"; }
  ok "V6b: actionlint verde"
else
  warn "V6b: actionlint AUSENTE — o CI executa"
fi
# Literais de compatibilidade: `proof-retry-matrix.sh` e `wave2-regression-proof.sh`
# casam por TEXTO. Contagem DECLARADA, nunca ">0".
_lit_exp="$(_expect EXPECTED_YML_BOTH_ATTEMPTS_LITERAL)"
_lit_obs="$(grep -c 'FAILED on BOTH attempts (rc1=' "$YML" || true)"
[ "$_lit_obs" = "$_lit_exp" ] \
  || die "V6c: literal 'FAILED on BOTH attempts (rc1=' aparece $_lit_obs vez(es) em $YML, esperado $_lit_exp
  Os provadores PLAN-161/proof-retry-matrix.sh e PLAN-159/wave2-regression-proof.sh
  casam esse texto; mudar a contagem os quebra em silencio."
ok "V6c: literal de compatibilidade preservado ($_lit_obs ocorrencia(s))"

if [ "$DRY_RUN" = "1" ]; then
  printf '\n\033[33mDRY-RUN\033[0m — G-PRE, G0..G5 verdes; patch aplicado; V1 e V6 executados.\n'
  printf '  O V-block longo (V2..V5, V7) NAO roda em dry-run.\n'
  printf '  Restaurando arvore e index...\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "V2 — suite do gate relativo (conjunto DECLARADO, nunca 'passou')"
# ---------------------------------------------------------------------------
PY_LOG="$TMPDIR_LAND/pytest.log"
PY_RC=0
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest "$GATE_TEST" -q -p no:cacheprovider \
  > "$PY_LOG" 2>&1 || PY_RC=$?
tail -5 "$PY_LOG" | sed 's/^/    /'
_exp_pytest_rc="$(_expect EXPECTED_GATE_PYTEST_RC)"
[ "$PY_RC" = "$_exp_pytest_rc" ] \
  || die "V2: pytest saiu rc=$PY_RC, esperado $_exp_pytest_rc — log em $PY_LOG"
# "N deselected" NAO e "N passed" (licao S325): o numero vem do campo `passed`.
# A linha do `pytest -q` COMECA pelo numero ("62 passed in 63.81s") — o sed
# anterior exigia um nao-digito antes dele e abortaria com a suite VERDE
# (a mesma classe derrubou o finalize-B na manha de 2026-08-26).
_obs_passed="$(grep -oE '(^|[^0-9])[0-9]+ passed' "$PY_LOG" | head -1 | grep -oE '[0-9]+')"
[ -n "$_obs_passed" ] || die "V2: nao consegui ler 'N passed' da saida do pytest — log em $PY_LOG"
_exp_passed="$(_expect EXPECTED_GATE_PYTEST_PASSED)"
[ "$_obs_passed" = "$_exp_passed" ] \
  || die "V2: $_obs_passed teste(s) passaram, esperado $_exp_passed.
  Um numero MENOR e regressao; um numero MAIOR significa que a suite cresceu —
  atualize $BASELINE_ENV conscientemente. Log: $PY_LOG"
ok "V2: $_obs_passed/$_exp_passed testes do gate verdes (rc=$PY_RC)"

# ---------------------------------------------------------------------------
step "V3 — o profiler EM DISCO conhece as flags que o workflow passa"
# ---------------------------------------------------------------------------
HELP_OUT="$TMPDIR_LAND/help.txt"
python3 "$PROFILER" --help > "$HELP_OUT" 2>&1 \
  || die "V3: '$PROFILER --help' saiu diferente de 0"
MISSING=""
for _flag in $(_expect EXPECTED_HELP_FLAGS); do
  grep -q -- "$_flag" "$HELP_OUT" || MISSING="$MISSING $_flag"
done
[ -z "$MISSING" ] || die "V3: flag(s) ausente(s) no --help do profiler:$MISSING"
ok "V3: as $(_expect EXPECTED_HELP_FLAGS | wc -w | tr -d ' ') flags constam do --help"

# ---------------------------------------------------------------------------
step "V4 — execucao REAL curta: as chaves da segunda chave existem"
# ---------------------------------------------------------------------------
# Teto DELIBERADAMENTE alto: o objetivo deste passo e provar que a superficie
# NOVA e emitida e legivel, nao re-rodar o gate absoluto (que a suite do V2 ja
# cobre por predicado). Com o teto de producao o rc dependeria da carga da
# maquina e a assercao mediria o runner, nao o pacote.
REAL_JSON="$TMPDIR_LAND/real.json"
REAL_RC=0
PYTHONDONTWRITEBYTECODE=1 python3 "$PROFILER" --hook-latency \
  --latency-iterations "$(_expect EXPECTED_VBLOCK_ITERATIONS)" \
  --p95-ceiling-ms 100000 --p99-ceiling-ms 100000 --p99-advisory \
  --exec-reference --relative-advisory > "$REAL_JSON" 2>"$TMPDIR_LAND/real.err" || REAL_RC=$?
_exp_real_rc="$(_expect EXPECTED_VBLOCK_RUN_RC)"
[ "$REAL_RC" = "$_exp_real_rc" ] || {
  sed 's/^/    /' "$TMPDIR_LAND/real.err" >&2
  die "V4: execucao real saiu rc=$REAL_RC, esperado $_exp_real_rc (teto alto: o rc nao deveria depender da carga)"; }
CEO_V4_PHASE="$(_expect EXPECTED_VBLOCK_RUN_PHASE)" \
CEO_V4_ENTRIES="$(_expect EXPECTED_VBLOCK_RUN_ENTRIES)" \
CEO_V4_KEYS="$(_expect EXPECTED_VBLOCK_PERHOOK_KEYS)" \
CEO_V4_LABELS="$(_expect EXPECTED_OUTCOME_LABELS)" \
python3 - "$REAL_JSON" <<'PY' || die "V4 reprovou"
import json, os, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
want_phase = os.environ["CEO_V4_PHASE"]
want_entries = int(os.environ["CEO_V4_ENTRIES"])
want_keys = sorted(os.environ["CEO_V4_KEYS"].split())
want_labels = set(os.environ["CEO_V4_LABELS"].split())
problems = []
if d.get("phase") != want_phase:
    problems.append("phase=%r, esperado %r" % (d.get("phase"), want_phase))
entries = {n: h for n, h in d.get("hooks", {}).items()
           if isinstance(h, dict) and "p95_ms" in h}
if len(entries) != want_entries:
    problems.append("%d entrada(s) com p95_ms, esperado %d" % (len(entries), want_entries))
for name, h in sorted(entries.items()):
    missing = [k for k in want_keys if k not in h]
    if missing:
        problems.append("%s sem a(s) chave(s) %s" % (name, ", ".join(missing)))
    lbl = h.get("verdict_label")
    if lbl is not None and lbl not in want_labels:
        problems.append("%s: verdict_label=%r fora do conjunto fechado" % (name, lbl))
top = d.get("verdict_label")
if top is not None and top not in want_labels:
    problems.append("topo: verdict_label=%r fora do conjunto fechado" % (top,))
if problems:
    sys.stderr.write("".join("    %s\n" % p for p in problems))
    sys.exit(1)
print("  phase=%s, %d entrada(s), todas com %s" % (want_phase, len(entries), ", ".join(want_keys)))
PY
ok "V4: relatorio real carrega a segunda chave em todas as entradas"

# ---------------------------------------------------------------------------
step "V5 — o PYSUM do workflow LE esse relatorio"
# ---------------------------------------------------------------------------
# O bloco e EXTRAIDO do validate.yml pos-patch (nunca reescrito aqui): um
# espelho a mao provaria o espelho, nao o workflow. Mesma forma que o
# wave2-regression-proof.sh usa para o run-block.
PYSUM_PY="$TMPDIR_LAND/pysum.py"
awk "/python3 - \"\\\$1\" <<'PYSUM'/{f=1;next} /^ *PYSUM\$/{f=0} f" "$YML" \
  | sed 's/^          //' > "$PYSUM_PY"
[ -s "$PYSUM_PY" ] || die "V5: nao consegui extrair o bloco PYSUM de $YML"
# O PYSUM le um path ABSOLUTO fixo; a simulacao so e fiel nesse path.
PYSUM_ATT="s328b$$"
cp "$REAL_JSON" "/tmp/hook-latency-attempt-$PYSUM_ATT.json"
PYSUM_SUMMARY="$TMPDIR_LAND/step-summary.md"
: > "$PYSUM_SUMMARY"
PYSUM_RC=0
GITHUB_STEP_SUMMARY="$PYSUM_SUMMARY" python3 "$PYSUM_PY" "$PYSUM_ATT" || PYSUM_RC=$?
rm -f "/tmp/hook-latency-attempt-$PYSUM_ATT.json"
_exp_pysum_rc="$(_expect EXPECTED_PYSUM_RC)"
[ "$PYSUM_RC" = "$_exp_pysum_rc" ] \
  || die "V5: o PYSUM saiu rc=$PYSUM_RC, esperado $_exp_pysum_rc"
_marker="$(_expect EXPECTED_PYSUM_MARKER)"
grep -qF -- "$_marker" "$PYSUM_SUMMARY" \
  || { sed 's/^/    /' "$PYSUM_SUMMARY" >&2
       die "V5: o step-summary NAO contem o marcador '$_marker' — a note() nova nao publicou"; }
grep -qF -- 'R_e=' "$PYSUM_SUMMARY" \
  || die "V5: o step-summary nao carrega 'R_e=' — a serie que alimenta a OQ-9 nao seria publicada"
ok "V5: o PYSUM publicou a linha da segunda chave (marcador '$_marker' presente)"

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

python3 .claude/scripts/validate_governance_fast.py >/dev/null \
  || die "V7b: validate_governance_fast FALHOU"
ok "V7b: validate_governance_fast verde"

if [ -f .claude/scripts/check-claude-md-claims.py ]; then
  python3 .claude/scripts/check-claude-md-claims.py >/dev/null \
    || die "V7c: check-claude-md-claims.py reprovou"
  ok "V7c: check-claude-md-claims.py verde"
else
  warn "V7c: check-claude-md-claims.py ausente — nao verificado"
fi

bash .claude/scripts/local/verify-counts.sh --quiet >/dev/null 2>&1 \
  || die "V7d: verify-counts.sh reprovou apos o land (contagens derivadas desatualizadas)"
ok "V7d: verify-counts.sh verde"

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
  V2 suite gate : $_obs_passed teste(s)

  Ultimos runs de CI:
EOF
if command -v gh >/dev/null 2>&1 && [ "$SELFTEST" = "0" ]; then
  gh run list --limit 3 2>&1 | sed 's/^/    /' || printf '    (gh run list indisponivel)\n'
else
  printf '    (gh ausente — acompanhe em https://github.com/Canhada-Labs/ceo-orchestration/actions)\n'
fi
cat <<'EOF'

  LEMBRETE — o que fazer com este land:
  Apos o land, o proximo `Validate` publica no step-summary, POR ENTRADA, o
  rotulo e o `ref_p50` (e o `R_e`). Colete >= 10 runs VERDES ao longo de >= 3
  dias antes de tentar fixar K (OQ-9). Um K escrito antes dessa janela e
  INVENTADO — e a fase 1 nao muda veredito nenhum, entao o verde de hoje vem do
  rerun, nao deste pacote.

  Se algum editor abrir em QUALQUER momento:
    aperte Esc, digite  :q!  e Enter  (sai sem salvar; nada se perde).
EOF
