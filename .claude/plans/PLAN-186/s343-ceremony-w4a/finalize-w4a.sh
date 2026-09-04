#!/usr/bin/env bash
# finalize-w4a.sh — DERIVA o W4A.patch da arvore-sombra e o baseia no HEAD vivo.
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao;
# nao ha gerador para o passo de derivacao (o generate-ceremony.sh assume o
# layout architect/round-N/approved.md, que esta cerimonia nao usa).
#
# O QUE ESTA WAVE ENTREGA (PLAN-186 W4a): a DELECAO dos dois steps mais caros
# do job `validate` — cuja uniao exata de node-ids o job
# `hook-tests-python-matrix` ja roda, no MESMO evento `push`, em 3.9 e 3.12 —
# mais o bump diferido do `timeout-minutes` do Smoke Install (126 -> 150) com
# a derivacao REESCRITA sobre sete amostras MEDIDAS. 2 paths, os DOIS
# canonicos, TODOS derivados de um unico material versionado
# (apply-w4a-validate-deletion.py, 5 edicoes com ancora exata).
#
# ESTE SCRIPT E UM CLONE GATE-A-GATE DO finalize-fable51.sh (que preparou o
# ab56e76 REAL na S339), e isso e deliberado: os guards dele foram pagos com o
# pacote D abortando duas vezes na S329 e curados por 8 rodadas de rail de
# materiais na S334 (drift-guard, `|| true` nos greps cujo zero e resposta,
# HEAD-andou, backup/restore transacional dos 4 materiais com pre-estado
# EXATO de worktree+index, flags de trap nunca herdadas do ambiente). Eles
# estao aqui byte-a-byte. O que muda e o bloco de constantes e o passo 4: a
# bateria daqui prova REPRODUTIBILIDADE, o lint de workflow com os flags da
# CI, a COBERTURA por conjunto de node-ids e o NAO-VACUO nomeado.
#
# COMO A RE-BASE E FEITA, e por que NAO por `git apply --3way`.
# A re-base e por CONTEUDO: uma arvore-sombra limpa em HEAD recebe os arquivos
# da sombra de trabalho, path a path, e o patch e o diff DESSA arvore contra o
# HEAD.
#
# Uso:  bash .claude/plans/PLAN-186/s343-ceremony-w4a/finalize-w4a.sh
#       bash .../finalize-w4a.sh --no-commit  (gera tudo, NAO stageia nada)
#       bash .../finalize-w4a.sh --with-slow  (roda tambem os gates de corpus)
#       CEO_W4A_SHADOW=/caminho/da/sombra bash .../finalize-w4a.sh
set -euo pipefail

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
PLAN_DIR=".claude/plans/PLAN-186"
CEREMONY_DIR="$PLAN_DIR/s343-ceremony-w4a"
SENTINEL="$PLAN_DIR/wave-s343-w4a-approved.md"
PATCH="$CEREMONY_DIR/W4A.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
BASE_SHA_FILE="$CEREMONY_DIR/BASE-SHA.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 W5 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S343-W4A-SIGN.sh"
APPLY="$CEREMONY_DIR/apply-w4a-validate-deletion.py"
VALIDATE_SH=".claude/scripts/validate-governance.sh"
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
  # rail-materials r1 P2-b: um abort DEPOIS do gerador restaura os quatro
  # materiais vivos ao estado pre-gerador (backup feito no passo 5).
  if [ "${_fin_captured:-0}" = "1" ] && [ "${_fin_ok:-0}" != "1" ]; then
    # rail r5: o aviso de recovery TEM de chegar ao operador.
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
command -v actionlint >/dev/null 2>&1 || die "actionlint ausente — a wave toca 2 workflows e o 4c exige o lint"
command -v shellcheck >/dev/null 2>&1 || die "shellcheck ausente — o actionlint o chama nos blocos run:"
python3 -c "import yaml" >/dev/null 2>&1 || die "PyYAML ausente — o 4b conta jobs e steps"

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
# `CEO_W4A_SHADOW` tem precedencia. Sem ela, a busca e sob o scratchpad DESTE
# repositorio (slug = caminho absoluto com `/` -> `-`, o mesmo que o harness
# usa): pegar `*/*/scratchpad` cru cairia no scratchpad de OUTRO projeto.
#
# A pergunta "isto e um repositorio git?" e feita AO GIT, nunca por
# `[ -d "$x/.git" ]`: num `git worktree` o `.git` e um ARQUIVO com um ponteiro
# `gitdir:`, e o teste de diretorio rejeitaria uma sombra perfeitamente valida.
_is_git_tree() { git -C "$1" rev-parse --git-dir >/dev/null 2>&1; }

SHADOW="${CEO_W4A_SHADOW:-}"
if [ -z "$SHADOW" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  _slug="$( printf '%s' "$ROOT" | tr '/' '-' )"
  for _cand in "$_sp_real/claude-501/$_slug"/*/scratchpad/shadow-w4a; do
    [ -d "$_cand" ] || continue
    _is_git_tree "$_cand" || continue
    SHADOW="$_cand"
    break
  done
fi
[ -n "$SHADOW" ] || die "arvore-sombra do pacote w4a nao encontrada.
  Procurei por  <scratchpad deste repo>/*/scratchpad/shadow-w4a  e nao achei
  um repositorio git. Passe o caminho explicitamente:
    CEO_W4A_SHADOW=/caminho/da/sombra bash $ROOT/$CEREMONY_DIR/finalize-w4a.sh
  (Para RECRIAR a sombra: git worktree add --detach <dir> HEAD &&
   python3 $APPLY --root <dir>)"
[ -d "$SHADOW" ] || die "CEO_W4A_SHADOW nao existe: $SHADOW"
_is_git_tree "$SHADOW" || die "CEO_W4A_SHADOW nao e um repositorio git: $SHADOW"
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
# shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
EXPECTED_SORTED="$( printf '%s\n' $EXPECTED_PATHS | sed '/^$/d' | LC_ALL=C sort -u )"
printf '      %s path(s) esperados:\n' "$( printf '%s\n' "$EXPECTED_SORTED" | wc -l | tr -d ' ' )"
printf '%s\n' "$EXPECTED_SORTED" | sed 's/^/        /'

# O derivador tem de CONCORDAR com a base declarada: a lista de paths que ele
# toca e o EXPECTED sao a MESMA coisa dita em dois lugares, e a bijecao e
# checada aqui (um path a mais no script = escopo sem decisao; um a menos = o
# EXPECTED envelheceu).
_apply_paths="$( python3 "$APPLY" --list-paths | LC_ALL=C sort -u )"
[ "$_apply_paths" = "$EXPECTED_SORTED" ] || die "apply-w4a-validate-deletion.py --list-paths != EXPECTED_PATCH_PATHS
  so no script  : $( comm -23 <( printf '%s\n' "$_apply_paths" ) <( printf '%s\n' "$EXPECTED_SORTED" ) | tr '\n' ' ')
  so no EXPECTED: $( comm -13 <( printf '%s\n' "$_apply_paths" ) <( printf '%s\n' "$EXPECTED_SORTED" ) | tr '\n' ' ')"
ok "derivador e EXPECTED concordam nos $( printf '%s\n' "$EXPECTED_SORTED" | wc -l | tr -d ' ' ) paths"

# Porcelain NUL-delimitado: o corte de 3 caracteres deixaria `old -> new`
# inteiro num rename, e a classificacao usaria o path VELHO.
# `-uall` NAO e opcional: sem ele o porcelain COLAPSA um diretorio inteiramente
# untracked numa unica entrada com barra no fim.
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
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "a sombra mexeu em path(s) FORA do conjunto EXPECTED:
$( printf '  %s\n' $OUTSIDE )
  O conjunto vive em $BASELINE_ENV (EXPECTED_PATCH_PATHS). Ou a sombra ganhou
  trabalho que esta cerimonia nao revisou, ou o conjunto ficou velho. Nos DOIS
  casos a decisao e do CEO — este script nao alarga escopo sozinho."
fi
ok "a sombra mexeu em $( printf '%s\n' "$CHANGED_SORTED" | wc -l | tr -d ' ' ) path(s), todos dentro do EXPECTED"

# ---------------------------------------------------------------------------
step "2 — guard de drift (a licao da S329: o pack nao pode REVERTER o destino)"
# ---------------------------------------------------------------------------
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
  Este path e re-escrito a partir da sombra; a sua edicao viva seria perdida."
    fi
  done < <( printf '%s' "$CLASS_B" | sed 's/^  //' )
fi
ok "nenhum path do pacote derivou entre a base da sombra e o HEAD vivo"

# ---------------------------------------------------------------------------
step "3 — arvore-sombra em $HEAD_SHA + copia por conteudo"
# ---------------------------------------------------------------------------
WT="$( mktemp -d "${TMPDIR:-/tmp}/s343w4a-wt.XXXXXX" )/wt"
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
    rm -f -- "$WT/$p" || die "falhei ao remover $p na arvore-sombra"
    REMOVED=$(( REMOVED + 1 ))
  fi
done < <( printf '%s\n' "$EXPECTED_SORTED" )
ok "$COPIED arquivo(s) copiados, $REMOVED removido(s)"

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
# A bateria LONGA (verify-counts ~3 min, governanca completa, ceremony-lint) e
# o V-block do LAND; repeti-la aqui dobraria o tempo da manha sem acrescentar
# informacao — salvo sob `--with-slow`.

# 4a — REPRODUTIBILIDADE: um SEGUNDO worktree limpo em HEAD recebe o derivador
# versionado; cada path EXPECTED tem de sair byte-identico ao da sombra.
WT2="$( mktemp -d "${TMPDIR:-/tmp}/s343w4a-wt2.XXXXXX" )/wt2"
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
  da sombra. Nos dois casos re-derive."
ok "4a: HEAD + apply-w4a-validate-deletion.py == sombra, byte a byte, nos $( printf '%s\n' "$EXPECTED_SORTED" | wc -l | tr -d ' ' ) paths"

# 4b — os DOIS workflows parseiam e a topologia e a DECLARADA.
( cd "$WT" && python3 - "$(_expect EXPECTED_VALIDATE_YML_REL)" "$(_expect EXPECTED_SMOKE_YML_REL)" \
    "$(_expect EXPECTED_YAML_JOBS_VALIDATE)" "$(_expect EXPECTED_YAML_JOBS_SMOKE)" \
    "$(_expect EXPECTED_VALIDATE_STEPS_POST)" "$(_expect EXPECTED_SMOKE_TIMEOUT_POST)" \
    "$(_expect EXPECTED_MATRIX_JOB_NAME)" <<'PY' ) || die "4b reprovou"
import sys, yaml
v_rel, s_rel, njobs_v, njobs_s, nsteps_v, smoke_to, matrix_job = sys.argv[1:8]
v = yaml.safe_load(open(v_rel, encoding="utf-8"))
s = yaml.safe_load(open(s_rel, encoding="utf-8"))
bad = []
if len(v["jobs"]) != int(njobs_v):
    bad.append("%s: %d jobs, esperado %s" % (v_rel, len(v["jobs"]), njobs_v))
if len(s["jobs"]) != int(njobs_s):
    bad.append("%s: %d jobs, esperado %s" % (s_rel, len(s["jobs"]), njobs_s))
n = len(v["jobs"]["validate"]["steps"])
if n != int(nsteps_v):
    bad.append("job validate: %d steps, esperado %s" % (n, nsteps_v))
to = s["jobs"]["smoke"].get("timeout-minutes")
if str(to) != str(smoke_to):
    bad.append("job smoke: timeout-minutes=%r, esperado %s" % (to, smoke_to))
if matrix_job not in v["jobs"]:
    bad.append("o job %s SUMIU" % matrix_job)
if bad:
    sys.stderr.write("".join("      %s\n" % b for b in bad))
    sys.exit(1)
print("      %s: %d jobs / validate %d steps; smoke timeout %s"
      % (v_rel, len(v["jobs"]), n, to))
PY
ok "4b: topologia dos dois workflows conforme a base declarada"

# 4c — o MESMO lint que o step da CI roda.
AL_RC=0
( cd "$WT" && actionlint -shellcheck="$(_expect EXPECTED_ACTIONLINT_FLAGS)" .github/workflows/*.yml ) \
  > "$WT.actionlint.log" 2>&1 || AL_RC=$?
[ "$AL_RC" = "$(_expect EXPECTED_ACTIONLINT_RC)" ] \
  || { tail -20 "$WT.actionlint.log" | sed 's/^/      /' >&2
       die "4c: actionlint saiu rc=$AL_RC, esperado $(_expect EXPECTED_ACTIONLINT_RC) — log em $WT.actionlint.log"; }
ASD_RC=0
( cd "$WT" && python3 .claude/scripts/check-action-sha-drift.py --offline ) >/dev/null 2>&1 || ASD_RC=$?
[ "$ASD_RC" = "$(_expect EXPECTED_ACTION_SHA_DRIFT_RC)" ] \
  || die "4c: check-action-sha-drift saiu rc=$ASD_RC, esperado $(_expect EXPECTED_ACTION_SHA_DRIFT_RC)"
ok "4c: actionlint + pins de action verdes"

# 4d — COBERTURA por CONJUNTO de node-ids. E o oraculo que AUTORIZA a delecao,
# e ele e re-derivado aqui, sobre esta arvore — nunca citado de um relatorio.
COV_RC=0
( cd "$WT2" && PYTHONDONTWRITEBYTECODE=1 python3 - \
    "$(_expect EXPECTED_NODEID_HOOKS)" "$(_expect EXPECTED_NODEID_SCRIPTS)" \
    "$(_expect EXPECTED_NODEID_MATRIX)" "$(_expect EXPECTED_NODEID_OVERLAP)" \
    "$(_expect EXPECTED_NODEID_SERIAL_HOOKS)" "$(_expect EXPECTED_NODEID_SERIAL_SCRIPTS)" \
    "$(_expect EXPECTED_NODEID_SERIAL_MATRIX)" <<'PY' ) > "$WT.coverage.log" 2>&1 || COV_RC=$?
import hashlib, subprocess, sys
exp = [int(x) for x in sys.argv[1:8]]
HOOKS = [".claude/hooks/tests/"]
SCRIPTS = [".claude/scripts/tests/", ".claude/scripts/optimizer/tests/"]


def collect(roots, marker):
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q",
           "-p", "no:cacheprovider"] + list(roots)
    if marker:
        cmd += ["-m", marker]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-3000:] + proc.stderr[-3000:])
        raise SystemExit("collect-only FALHOU para %s (marker=%r)" % (roots, marker))
    ids = {ln.strip() for ln in proc.stdout.splitlines()
           if "::" in ln.strip() and " " not in ln.strip().split("::")[0]}
    if not ids:
        raise SystemExit("collect-only devolveu ZERO node-ids para %s — gate vacuo" % roots)
    return ids


def sha(s):
    return hashlib.sha256("\n".join(sorted(s)).encode("utf-8")).hexdigest()


bad = []
for label, marker, (ea, eb, em, eo) in (
        ("todos", None, (exp[0], exp[1], exp[2], exp[3])),
        ("serial", "serial", (exp[4], exp[5], exp[6], exp[3]))):
    A, B = collect(HOOKS, marker), collect(SCRIPTS, marker)
    M = collect(HOOKS + SCRIPTS, marker)
    U, inter = A | B, A & B
    print("      [%s] |A|=%d |B|=%d |A&B|=%d |AuB|=%d |matriz|=%d sha(U)=%s sha(M)=%s"
          % (label, len(A), len(B), len(inter), len(U), len(M), sha(U)[:16], sha(M)[:16]))
    if U != M:
        bad.append("[%s] a UNIAO dos dois steps NAO e a matriz (so-uniao=%d, so-matriz=%d)"
                   % (label, len(U - M), len(M - U)))
    if len(inter) != eo:
        bad.append("[%s] |A&B|=%d, esperado %d" % (label, len(inter), eo))
    for got, want, what in ((len(A), ea, "|A|"), (len(B), eb, "|B|"), (len(M), em, "|matriz|")):
        if got != want:
            bad.append("[%s] %s = %d, DECLARADO %d — a suite mudou de tamanho; atualize o "
                       "EXPECTED-BASELINE.txt CONSCIENTEMENTE, nunca relaxando" % (label, what, got, want))
if bad:
    sys.stderr.write("".join("      %s\n" % b for b in bad))
    raise SystemExit(1)
print("      a delecao NAO e recusada por cobertura")
PY
[ "$COV_RC" = "0" ] || { sed 's/^/      /' "$WT.coverage.log" >&2
                         die "4d: a re-derivacao de cobertura reprovou — log em $WT.coverage.log"; }
sed 's/^/  /' "$WT.coverage.log"
ok "4d: uniao dos dois steps == matriz, por CONJUNTO, nos 2 recortes"

# 4e — NAO-VACUO nomeado: o que sai existia em HEAD e sumiu; o que fica, ficou.
_v_rel="$(_expect EXPECTED_VALIDATE_YML_REL)"
_s_rel="$(_expect EXPECTED_SMOKE_YML_REL)"
_step_a="$(_expect EXPECTED_DELETED_STEP_A)"
_step_b="$(_expect EXPECTED_DELETED_STEP_B)"
_ha="$( git show "HEAD:$_v_rel" | { grep -c -F -- "- name: $_step_a" || true; } )"
_hb="$( git show "HEAD:$_v_rel" | { grep -c -F -- "- name: $_step_b" || true; } )"
{ [ "$_ha" = "1" ] && [ "$_hb" = "1" ]; } \
  || die "4e: em HEAD o step A aparece $_ha vez(es) e o B $_hb — esperado 1 e 1 (a wave nao esta deletando o que diz)"
_pa="$( { grep -c -F -- "- name: $_step_a" "$WT/$_v_rel" || true; } )"
_pb="$( { grep -c -F -- "- name: $_step_b" "$WT/$_v_rel" || true; } )"
{ [ "$_pa" = "$(_expect EXPECTED_DELETED_STEP_REFS_POST)" ] && [ "$_pb" = "$(_expect EXPECTED_DELETED_STEP_REFS_POST)" ]; } \
  || die "4e: pos-patch A=$_pa e B=$_pb, esperado $(_expect EXPECTED_DELETED_STEP_REFS_POST) nos dois"
_p126="$( { grep -c -F -- "timeout-minutes: $(_expect EXPECTED_SMOKE_TIMEOUT_HEAD)" "$WT/$_s_rel" || true; } )"
_p150="$( { grep -c -F -- "timeout-minutes: $(_expect EXPECTED_SMOKE_TIMEOUT_POST)" "$WT/$_s_rel" || true; } )"
{ [ "$_p126" = "0" ] && [ "$_p150" = "1" ]; } \
  || die "4e: timeout velho=$_p126 e novo=$_p150 pos-patch, esperado 0 e 1"
grep -qF -- "PLAN-186 W4a (S343): 126 -> 150" "$WT/$_s_rel" \
  || die "4e: o bloco novo de derivacao MEDIDA nao esta no smoke-install.yml"
for _m in "PLAN-185 W1+W2 (AC-3): 68 -> 83" "PLAN-169 W-E (S329, rail rounds 1-3): 83 -> 126"; do
  grep -qF -- "$_m" "$WT/$_s_rel" || die "4e: o ledger da derivacao aditiva perdeu '$_m'"
done
ok "4e: 2 steps fora, timeout $(_expect EXPECTED_SMOKE_TIMEOUT_POST) com ledger preservado"

# 4f — os gates de CORPUS, so sob --with-slow.
if [ "$WITH_SLOW" = "1" ]; then
  printf '  4f: rodando os gates de corpus na arvore-sombra (~5 min)...\n'
  CLAIMS_RC=0
  ( cd "$WT" && python3 .claude/scripts/check-claude-md-claims.py ) >/dev/null 2>&1 || CLAIMS_RC=$?
  [ "$CLAIMS_RC" = "$(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)" ] \
    || die "4f: check-claude-md-claims saiu rc=$CLAIMS_RC, esperado $(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)"
  CONTAM_RC=0
  ( cd "$WT" && python3 .claude/scripts/check_contamination.py ) >/dev/null 2>&1 || CONTAM_RC=$?
  [ "$CONTAM_RC" = "$(_expect EXPECTED_CONTAMINATION_RC)" ] \
    || die "4f: check_contamination saiu rc=$CONTAM_RC, esperado $(_expect EXPECTED_CONTAMINATION_RC)"
  VC_RC=0
  ( cd "$WT" && bash .claude/scripts/local/verify-counts.sh ) > "$WT.verify-counts.log" 2>&1 || VC_RC=$?
  [ "$VC_RC" = "$(_expect EXPECTED_VERIFY_COUNTS_RC)" ] \
    || { grep -E 'DRIFT|Exit' "$WT.verify-counts.log" | head -20 | sed 's/^/      /' >&2
         die "4f: verify-counts saiu rc=$VC_RC, esperado $(_expect EXPECTED_VERIFY_COUNTS_RC)"; }
  ( cd "$WT" && bash "$VALIDATE_SH" ) > "$WT.gov.log" 2>&1 \
    || { tail -20 "$WT.gov.log" | sed 's/^/      /' >&2; die "4f: validate-governance.sh FALHOU"; }
  _gov_obs="$( { grep -oiE '^[[:space:]]*errors:[[:space:]]+[0-9]+' "$WT.gov.log" || true; } | { grep -oE '[0-9]+' || true; } | head -1 )"
  [ -n "$_gov_obs" ] || die "4f: nao consegui ler a contagem de erros em $WT.gov.log"
  [ "$_gov_obs" = "$(_expect EXPECTED_GOVERNANCE_ERRORS)" ] \
    || die "4f: validate-governance reporta $_gov_obs erro(s), esperado $(_expect EXPECTED_GOVERNANCE_ERRORS)"
  BP_RC=0
  ( cd "$WT" && python3 scripts/build-plugin.py --check ) >/dev/null 2>&1 || BP_RC=$?
  [ "$BP_RC" = "$(_expect EXPECTED_BUILD_PLUGIN_CHECK_RC)" ] \
    || die "4f: build-plugin.py --check saiu rc=$BP_RC, esperado $(_expect EXPECTED_BUILD_PLUGIN_CHECK_RC)"
  TEH_RC=0
  ( cd "$WT" && python3 .claude/scripts/check-test-env-hygiene.py ) >/dev/null 2>&1 || TEH_RC=$?
  [ "$TEH_RC" = "$(_expect EXPECTED_TEST_ENV_HYGIENE_RC)" ] \
    || die "4f: check-test-env-hygiene saiu rc=$TEH_RC, esperado $(_expect EXPECTED_TEST_ENV_HYGIENE_RC)"
  CSHM_RC=0
  ( cd "$WT" && python3 .claude/scripts/gen-command-skill-hook-map.py --check ) >/dev/null 2>&1 || CSHM_RC=$?
  [ "$CSHM_RC" = "$(_expect EXPECTED_CSHM_CHECK_RC)" ] \
    || die "4f: gen-command-skill-hook-map --check saiu rc=$CSHM_RC, esperado $(_expect EXPECTED_CSHM_CHECK_RC)"
  ok "4f: claims, contaminacao, verify-counts, governanca completa, plugin, env-hygiene e map verdes"
else
  printf '  \033[33mNOTA\033[0m 4f: gates de corpus NAO executados (padrao). O V8/V9 do LAND os rodam.\n'
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

# rail-materials r1 P2-b: o gerador sobrescreve patch, sentinel e PROPOSED em
# sequencia; um abort dos checks seguintes NAO pode deixar os tres pela
# metade. Backup antes, restore no abort.
_fin_bak="$(mktemp -d)"
: > "$_fin_bak/.absent-before"   # rail r3 P2-i: ausencia tambem e estado
for _bf in "$PATCH" "$SENTINEL" "$PROPOSED" "$BASE_SHA_FILE"; do
  if [ -f "$_bf" ]; then
    cp -p "$_bf" "$_fin_bak/$(basename "$_bf")"
  else
    printf '%s\n' "$_bf" >> "$_fin_bak/.absent-before"
  fi
done
# rail r4 (REDESENHO): o INDEX tambem e pre-estado.
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

PATCH_PATHS="$( git apply --numstat "$PATCH" | awk '{print $3}' | LC_ALL=C sort -u )"
_extra="$( comm -23 <( printf '%s\n' "$PATCH_PATHS" ) <( printf '%s\n' "$EXPECTED_SORTED" ) )"
# shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
[ -z "$_extra" ] || die "o patch toca path(s) fora do EXPECTED:
$( printf '  %s\n' $_extra )"
_ghost="$( comm -13 <( printf '%s\n' "$PATCH_PATHS" ) <( printf '%s\n' "$EXPECTED_SORTED" ) )"
if [ -n "$_ghost" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
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
# shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
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
  git commit -q -m "chore(PLAN-186 s343-w4a): patch derivado da sombra e baseado em $HEAD_SHA (finalize-w4a.sh)" \
    || die "o commit falhou — o staging esta intacto; chame o CEO"
  _fin_ok=1
  ok "commit criado: $( git rev-parse --short HEAD )"
fi
fi

step "PRONTO"
cat <<EOF

  O pacote w4a esta baseado em  $( git rev-parse HEAD )  e o patch aplica limpo.
    patch  : $PATCH
    sha256 : $NEW_PATCH_SHA
    paths  : $( printf '%s\n' "$PATCH_PATHS" | wc -l | tr -d ' ' )

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$SIGN_SCRIPT

EOF
