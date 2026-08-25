#!/usr/bin/env bash
# OWNER-S327b-LAND.sh — land do pacote de cerimônia wave-w5 (PLAN-183).
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (espelha o OWNER-S326-LAND.sh, gate a gate, incluindo o G4 `touched - scope`
# que so existe automatizado nessa familia de scripts).
#
# Roda de QUALQUER diretorio. Nenhum passo e destrutivo antes de todos os
# gates passarem. Ao fim ele COMMITA (com -F, sem abrir editor) e EMPURRA.
#
# Uso:
#   bash .claude/plans/PLAN-183/OWNER-S327b-LAND.sh --dry-run --ownership-e2e=defer
#   bash .claude/plans/PLAN-183/OWNER-S327b-LAND.sh           --ownership-e2e=defer
#
#   --ownership-e2e=run|defer  OBRIGATORIO, SEM default.
#       run   = roda o e2e de ownership (~25 min) dentro do land
#       defer = deixa para o nightly do CI (o gate compara o conjunto RED)
#     Um parametro que muda o VEREDITO nao tem default (doutrina DevOps):
#     esquecer o argumento tem de ser um erro, nunca uma escolha silenciosa.
set -euo pipefail

# --- argumentos -----------------------------------------------------------
DRY_RUN=0
OWNERSHIP_E2E=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --ownership-e2e=run)   OWNERSHIP_E2E="run" ;;
    --ownership-e2e=defer) OWNERSHIP_E2E="defer" ;;
    --ownership-e2e=*)
      printf '\n\033[31mABORT:\033[0m valor invalido em %s (use run ou defer)\n' "$arg" >&2
      exit 1 ;;
    *)
      printf '\n\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$arg" >&2
      exit 1 ;;
  esac
done
if [ -z "$OWNERSHIP_E2E" ]; then
  printf '\n\033[31mABORT:\033[0m --ownership-e2e e OBRIGATORIO e nao tem default.\n' >&2
  printf '  Rode uma das duas formas:\n' >&2
  printf '    bash %s --ownership-e2e=defer   # ~25 min a menos; o nightly do CI roda\n' "$0" >&2
  printf '    bash %s --ownership-e2e=run     # roda agora, dentro do land\n' "$0" >&2
  exit 1
fi

# A raiz resolve por git a partir da LOCALIZACAO DO SCRIPT, nunca por `../..`
# nem pelo cwd (licao S313).
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes da cerimonia (o UNICO bloco que muda entre waves) ----------
PLAN_DIR=".claude/plans/PLAN-183"
CEREMONY_DIR="$PLAN_DIR/w5-ceremony"
SENTINEL="$PLAN_DIR/wave-w5fix-approved.md"
PATCH="$CEREMONY_DIR/S327b-W5FIX.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH-W5FIX.md"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-W5FIX.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S327b-SIGN.sh"
RAIL_GLOB="$CEREMONY_DIR/rail-*.md"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
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

# ---------------------------------------------------------------------------
step "G0 — insumos, materiais rastreados e arvore limpa"
# Rail (materiais, S327 r1, P1): o commit avanca o HEAD ATUAL, e `git push origin main`
# empurra o ref LOCAL main — fora do main o push "sucede" sem levar o commit assinado.
# Fail-closed: o land so roda com HEAD em $PUSH_BRANCH, e o push e HEAD:$PUSH_BRANCH.
_cur_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '')"
[ "$_cur_branch" = "$PUSH_BRANCH" ] || die "HEAD esta em '$_cur_branch', nao em '$PUSH_BRANCH' — o land so roda no $PUSH_BRANCH (git checkout $PUSH_BRANCH)"
ok "G0: HEAD em $PUSH_BRANCH"
# ---------------------------------------------------------------------------
[ -f "$SENTINEL" ] || die "sentinel ausente: $SENTINEL"
[ -f "$PATCH" ]    || die "patch ausente: $PATCH"
[ -f "$SENTINEL.asc" ] || die "assinatura ausente: $SENTINEL.asc
  O Owner assina com:  bash $ROOT/$SIGN_SCRIPT"
[ -f "$COMMIT_MSG" ] || die "mensagem de commit ausente: $COMMIT_MSG"
[ -f "$ORACLE" ] || die "oraculo de canonicidade ausente: $ORACLE"
[ -f "$BASELINE_ENV" ] || die "base esperada AUSENTE: $BASELINE_ENV

  O V-block compara contra numeros DECLARADOS, nunca contra zero: o main esta
  vermelho hoje por desenho (D1 aberto => STALE 3 na paridade maintainer).
  Sem esse arquivo cada execucao do V-block e ruido. O CEO grava assim:

    EXPECTED_PARITY_MAINTAINER_RC=0
    EXPECTED_PARITY_MAINTAINER_STALE=0
    EXPECTED_PARITY_MAINTAINER_MISSING_IN_B=0
    EXPECTED_PARITY_MAINTAINER_UNCLASSIFIED=0
    EXPECTED_PARITY_MAINTAINER_MODE_DIFF=0
    EXPECTED_PARITY_MAINTAINER_ONLY_IN_B_OUTSIDE_CLAUDE=0
    EXPECTED_PARITY_USER_RC=0
    EXPECTED_PARITY_USER_STALE=0
    EXPECTED_PARITY_USER_MISSING_IN_B=0
    EXPECTED_PARITY_USER_UNCLASSIFIED=0
    EXPECTED_PARITY_USER_MODE_DIFF=0
    EXPECTED_PARITY_USER_ONLY_IN_B_OUTSIDE_CLAUDE=0
    EXPECTED_UNIT_ORACLE_FAIL=0
    EXPECTED_OWNERSHIP_RED_IDS=\"OWN-0016 OWN-0024 OWN-0027\""
ok "sentinel, patch, .asc, mensagem e base esperada presentes"

# Os materiais tem de estar RASTREADOS: o commit do land stageia so o patch +
# sentinel + .asc, entao SIGN/LAND/patch/registros untracked deixariam o commit
# referenciando evidencia ausente do repositorio. Fail-closed aqui.
MATERIALS=(
  "$SIGN_SCRIPT"
  "$PLAN_DIR/OWNER-S327b-LAND.sh"
  "$PROPOSED"
  "$COMMIT_MSG"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/finalize_patch.py"
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
# ABORTAM, e path com newline ABORTA (gate de seguranca falha FECHADO em
# entrada que nao sabe parsear).
TMPDIR_LAND="$(mktemp -d)"
# Estado do trap declarado ANTES do trap: sob `set -u` uma variavel nao
# inicializada no handler mata o handler, e o dry-run deixaria o patch
# aplicado. O trap entra AQUI, nao depois dos gates, senao um abort no meio
# do G0..G5 vaza o diretorio temporario.
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
# aqui: o espelho da S326 omitia superficies guardadas e deixava o land
# misturar uma edicao canonica nao-assinada. Oraculo indisponivel => ABORTA.
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
# e ancestral do HEAD e nenhum path tocado derivou entre as duas. O G1 ja
# fixou Anchor == HEAD; isto fixa o CONTEUDO sob o patch.
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

# ---------------------------------------------------------------------------
step "G5 — grants do sentinel + coerencia do manifesto ADR-192"
# ---------------------------------------------------------------------------
# Assinatura GPG valida NAO e autorizacao mecanica (licao S318: um sentinel
# verificou e concedia ZERO paths). Aqui cada path CANONICO tocado e provado
# concedido pela MESMA funcao que o hook usa, `_sentinel_grants_path`.
# No AUTO-TESTE o `.asc` e sintetico, entao o rail de assinatura dentro de
# `_sentinel_grants_path` reprovaria por MOTIVO ERRADO e o controle positivo do
# parse de Scope (abaixo) ficaria vacuo. O unlock documentado do ADR-010 vale
# so aqui, e este modo ja e recusado fora do scratchpad.
if [ "$SELFTEST" = "1" ]; then
  # O unlock exige PROVENIENCIA (`_unlock_trusted_text`): sem ela ele nega
  # tudo e o G5 reprovaria por motivo ERRADO — foi o que fez o controle T7
  # "passar" antes desta cura, mascarando o fato de o parse de Scope nunca
  # ter sido exercitado. Com o digest fixado nos bytes EM DISCO, quem decide
  # volta a ser o parse do Scope, que e exatamente o que o T7 testa.
  SELFTEST_SENTINEL_SHA="$(shasum -a 256 "$SENTINEL" | awk '{print $1}')"
  G5_ENV=(env "CEO_SENTINEL_UNLOCK=PLAN-183-adopter-fitness" \
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
print("  %d membro(s) do manifesto ADR-192 tocado(s)%s"
      % (len(touched_members),
         " (manifesto no patch: OK)" if touched_members else ""))
PY
ok "grants provados e manifesto estruturalmente coerente"

# ---------------------------------------------------------------------------
# Impressao digital PRE-mutacao (arvore + index), tirada AGORA — depois de
# todos os gates e antes da primeira mutacao. O `--dry-run` aplica o patch de
# verdade para rodar o V1 sobre o conteudo REAL pos-patch, e restaura no trap
# (dry-run que deixa `git apply` no index e a armadilha da S272: o proximo
# commit do operador carrega o residuo junto).
# ---------------------------------------------------------------------------
FP_BEFORE="$(_fingerprint)"

# ---------------------------------------------------------------------------
step "APLICANDO o patch assinado"
# ---------------------------------------------------------------------------
# S327 (abort real medido): o primeiro land REAL abortou no V4 e deixou a arvore
# com o patch aplicado — so o dry-run restaurava. Agora TODO abort depois do
# apply restaura arvore e index; o land bem-sucedido desliga o restore logo
# apos o commit (o patch passa a viver no commit, nao na arvore).
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
  ok "V1: nenhum script shell no patch"
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

if [ "$DRY_RUN" = "1" ]; then
  printf '\n\033[33mDRY-RUN\033[0m — gates G0..G5 verdes, patch aplicado e V1 executado.\n'
  printf '  O V-block completo (V2..V7) NAO roda em dry-run.\n'
  printf '  Restaurando arvore e index...\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "V2 — manifesto ADR-192 casa byte a byte"
# ---------------------------------------------------------------------------
# `grep -c ... || printf 0` imprime DOIS valores quando nao ha casamento
# (medido: "0\n0"). awk sempre imprime exatamente um e sai 0.
MANIFEST_LINES="$(awk '/^[0-9a-f]{64}/{n++} END{print n+0}' "$MANIFEST")"
[ "$MANIFEST_LINES" -gt 0 ] || die "V2: manifesto ADR-192 sem linha nenhuma"
# Contagem INDEPENDENTE (wc -l sobre as linhas uteis): se as duas divergem, o
# manifesto tem linha que NAO e `<sha256>  <path>` e que o regex acima pularia
# em silencio — um membro fora do formato sairia da verificacao sem ruido.
MANIFEST_USEFUL="$(awk 'NF && $1 !~ /^#/' "$MANIFEST" | wc -l | tr -d ' ')"
[ "$MANIFEST_USEFUL" = "$MANIFEST_LINES" ] \
  || die "V2: o manifesto tem $MANIFEST_USEFUL linha(s) util(eis) mas so $MANIFEST_LINES no formato
  <sha256>  <path> — uma linha malformada sairia da verificacao em silencio"
shasum -a 256 -c "$MANIFEST" > "$TMPDIR_LAND/manifest.out" 2>&1 \
  || { sed 's/^/    /' "$TMPDIR_LAND/manifest.out" >&2
       die "V2: manifesto ADR-192 NAO casa — algum gate-script diverge do assinado"; }
OK_LINES="$(awk '/: OK$/' "$TMPDIR_LAND/manifest.out" | wc -l | tr -d ' ')"
[ "$OK_LINES" -eq "$MANIFEST_LINES" ] \
  || die "V2: o manifesto tem $MANIFEST_LINES membro(s) mas so $OK_LINES foram verificados
  (asserção de CONJUNTO: um 'shasum -c' que verifica menos do que declara e verde vazio)"
ok "V2: $OK_LINES/$MANIFEST_LINES membros do manifesto ADR-192 conferidos"

# ---------------------------------------------------------------------------
step "V3 — oraculo unitario de ownership"
# ---------------------------------------------------------------------------
# Leitor da base esperada: sem `source` (o arquivo nao executa nada), e
# fail-CLOSED quando a chave falta.
_expect() {
  _ev="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
  if [ -z "$_ev" ]; then
    die "chave '$1' AUSENTE em $BASELINE_ENV — o V-block nao compara contra nada"
  fi
  printf '%s' "$_ev"
}
UNIT_LOG="$TMPDIR_LAND/unit.log"
UNIT_RC=0
bash scripts/tests/test-ownership-verdict-unit.sh --quiet > "$UNIT_LOG" 2>&1 || UNIT_RC=$?
sed 's/^/    /' "$UNIT_LOG"
UNIT_FAIL="$(sed -n 's/.*FAIL=\([0-9][0-9]*\).*/\1/p' "$UNIT_LOG" | head -1)"
[ -n "$UNIT_FAIL" ] || die "V3: nao consegui ler FAIL= da saida do oraculo unitario"
EXP_UNIT_FAIL="$(_expect EXPECTED_UNIT_ORACLE_FAIL)"
[ "$UNIT_FAIL" = "$EXP_UNIT_FAIL" ] \
  || die "V3: oraculo unitario FAIL=$UNIT_FAIL, esperado $EXP_UNIT_FAIL"
[ "$UNIT_RC" -eq 0 ] || die "V3: oraculo unitario saiu rc=$UNIT_RC"
ok "V3: oraculo unitario FAIL=$UNIT_FAIL (esperado $EXP_UNIT_FAIL)"

# ---------------------------------------------------------------------------
step "V4 — manifesto de baseline do install"
# ---------------------------------------------------------------------------
BASE_LOG="$TMPDIR_LAND/baseline.log"
BASE_RC=0
bash scripts/tests/test_install_baseline_manifest.sh > "$BASE_LOG" 2>&1 || BASE_RC=$?
tail -15 "$BASE_LOG" | sed 's/^/    /'
# S327 (abort real medido): a suite e 33/1 POR DESENHO — C.6.2 e known-open
# pre-existente (nightly declara o mesmo conjunto). Comparar contra zero era
# ruido e abortou o primeiro land. Mesma semantica do gate nightly: rc
# declarado + conjunto EXATO de ids FAIL, nos dois sentidos (id NOVO =
# regressao; id AUSENTE = a tabela-verdade mudou, atualize a base conscientemente).
_v4_exp_rc="$(_expect EXPECTED_BASELINE_MANIFEST_RC)"
_v4_exp_set="$(_expect EXPECTED_BASELINE_MANIFEST_KNOWN_OPEN | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u | tr '\n' ' ' | sed 's/ $//')"
_v4_obs_set="$(awk '$1 == "FAIL" { print $2 }' "$BASE_LOG" | LC_ALL=C sort -u | tr '\n' ' ' | sed 's/ $//')"
[ "$BASE_RC" -eq "$_v4_exp_rc" ] \
  || die "V4: test_install_baseline_manifest.sh saiu rc=$BASE_RC, esperado rc=$_v4_exp_rc (EXPECTED_BASELINE_MANIFEST_RC) — log em $BASE_LOG"
[ "$_v4_obs_set" = "$_v4_exp_set" ] \
  || die "V4: conjunto FAIL do baseline-manifest MUDOU — declarado [$_v4_exp_set], observado [$_v4_obs_set] — log em $BASE_LOG"
ok "V4: baseline-manifest rc=$BASE_RC com o conjunto known-open EXATO [$_v4_exp_set]"

# ---------------------------------------------------------------------------
step "V5 — paridade install/upgrade (contra a base DECLARADA)"
# ---------------------------------------------------------------------------
# O main esta vermelho por desenho hoje; comparar contra ZERO seria ruido.
# Cada contagem e comparada contra EXPECTED-BASELINE.txt, e o rc tambem.
_parity_mode() {
  _pm_mode="$1"; _pm_upper="$2"
  _pm_log="$TMPDIR_LAND/parity-$_pm_mode.log"
  _pm_rc=0
  bash scripts/tests/test-install-upgrade-parity-e2e.sh --mode "$_pm_mode" \
    > "$_pm_log" 2>&1 || _pm_rc=$?
  _pm_exp_rc="$(_expect "EXPECTED_PARITY_${_pm_upper}_RC")"
  printf '    log: %s\n' "$_pm_log"
  for _cls in STALE MISSING_IN_B UNCLASSIFIED MODE_DIFF ONLY_IN_B_OUTSIDE_CLAUDE; do
    # Ancorado no BLOCO de contagens: `$1==k` solto tambem casaria a secao de
    # detalhe ("STALE divergence ...") e leria uma palavra como se fosse um
    # numero. O bloco comeca em "counts (UNDECLARED" e cada classe aparece
    # uma vez, com o numero em $2.
    _got="$(awk -v k="$_cls" '
        /counts \(UNDECLARED/ { inb = 1; next }
        inb && $1 == k && $2 ~ /^[0-9]+$/ { print $2; exit }
      ' "$_pm_log")"
    if [ -z "$_got" ]; then
      die "V5[$_pm_mode]: nao achei a contagem '$_cls' no log — o e2e nao chegou a classificar (ver $_pm_log)"
    fi
    _exp="$(_expect "EXPECTED_PARITY_${_pm_upper}_${_cls}")"
    if [ "$_got" != "$_exp" ]; then
      tail -40 "$_pm_log" | sed 's/^/      /' >&2
      die "V5[$_pm_mode]: $_cls=$_got, esperado $_exp (base declarada em $BASELINE_ENV)"
    fi
    printf '      %-26s %s  (esperado %s)\n' "$_cls" "$_got" "$_exp"
  done
  [ "$_pm_rc" = "$_pm_exp_rc" ] \
    || die "V5[$_pm_mode]: rc=$_pm_rc, esperado $_pm_exp_rc (0 paridade / 1 fail / 2 known-open / 9 scaffold)"
  ok "V5[$_pm_mode]: rc=$_pm_rc e as 5 contagens fatais casam a base declarada"
}
_parity_mode maintainer MAINTAINER
_parity_mode user USER

# ---------------------------------------------------------------------------
step "V6 — gates de corpus + subconjunto pytest"
# ---------------------------------------------------------------------------
bash .claude/scripts/local/verify-counts.sh --quiet >/dev/null 2>&1 \
  || die "V6a: verify-counts.sh reprovou apos o land (contagens derivadas desatualizadas)"
ok "V6a: verify-counts.sh verde"

if [ -f .claude/scripts/check-claude-md-claims.py ]; then
  python3 .claude/scripts/check-claude-md-claims.py >/dev/null \
    || die "V6b: check-claude-md-claims.py reprovou"
  ok "V6b: check-claude-md-claims.py verde"
else
  warn "V6b: check-claude-md-claims.py ausente — nao verificado"
fi

PYTEST_TARGETS=""
for t in \
  .claude/hooks/tests/test_runtime_paths.py \
  .claude/hooks/tests/test_collect_only_audit_isolation.py \
  .claude/hooks/tests/test_live_audit_isolation.py \
  .claude/scripts/tests/test_templates_use_single_resolver.py \
  .claude/scripts/tests/test_parity_source_resolution.py \
  .claude/scripts/tests/test_delivery_route_consumers.py ; do
  [ -f "$t" ] && PYTEST_TARGETS="$PYTEST_TARGETS $t"
done
[ -n "$PYTEST_TARGETS" ] || die "V6c: nenhum alvo pytest encontrado — o subconjunto ficou vazio"
PY_LOG="$TMPDIR_LAND/pytest.log"
# shellcheck disable=SC2086  # PYTEST_TARGETS e uma lista controlada, sem espacos nos paths
python3 -m pytest $PYTEST_TARGETS -q -p no:cacheprovider > "$PY_LOG" 2>&1 \
  || { tail -30 "$PY_LOG" | sed 's/^/    /' >&2; die "V6c: subconjunto pytest VERMELHO — log em $PY_LOG"; }
ok "V6c: pytest — $(tail -1 "$PY_LOG")"

# ---------------------------------------------------------------------------
step "V7 — e2e de ownership (--ownership-e2e=$OWNERSHIP_E2E)"
# ---------------------------------------------------------------------------
EXP_REDS="$(_expect EXPECTED_OWNERSHIP_RED_IDS)"
if [ "$OWNERSHIP_E2E" = "defer" ]; then
  warn "V7: DIFERIDO por escolha explicita. O nightly do CI (ownership-nightly.yml)"
  printf '        compara o conjunto RED contra scripts/tests/ownership-expected-reds.txt.\n'
  printf '        Conjunto esperado: %s\n' "$EXP_REDS"
  printf '        Encolher o conjunto e FALHA, nao sucesso.\n'
else
  printf '  Rodando o e2e de ownership (~25 min). Nao interrompa.\n'
  E2E_LOG="$TMPDIR_LAND/ownership-e2e.log"
  E2E_RC=0
  CELL_TIMEOUT="${CELL_TIMEOUT:-180}" bash scripts/tests/ownership-nightly-gate.sh \
    > "$E2E_LOG" 2>&1 || E2E_RC=$?
  tail -25 "$E2E_LOG" | sed 's/^/    /'
  [ "$E2E_RC" -eq 0 ] \
    || die "V7: ownership-nightly-gate.sh saiu rc=$E2E_RC — o conjunto RED mudou.
  Esperado: $EXP_REDS
  All-green tambem e FALHA: significa que a tabela-verdade mudou. Log: $E2E_LOG"
  ok "V7: conjunto RED inalterado ($EXP_REDS)"
fi

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
  O CEO preenche APPROVE depois da ultima rodada limpa do rail." ;;
esac

if ! git commit -F "$COMMIT_MSG" --no-edit; then
  die "o commit falhou (hook de pre-commit? veja a saida acima).
  O STAGING esta intacto — nada se perdeu. Chame o CEO.
  Se algum editor abriu: aperte Esc, digite  :q!  e Enter."
fi
NEW_SHA="$(git rev-parse HEAD)"
ok "commit criado: $NEW_SHA"
RESTORE_ON_EXIT=0   # o patch vive no commit a partir daqui; um abort no push NAO reverte a arvore
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
  V7 ownership  : $OWNERSHIP_E2E

  Agora e so acompanhar o CI. Se algum editor abrir em QUALQUER momento:
    aperte Esc, digite  :q!  e Enter  (sai sem salvar; nada se perde).
EOF
