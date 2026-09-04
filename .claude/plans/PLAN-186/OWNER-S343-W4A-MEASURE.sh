#!/usr/bin/env bash
# OWNER-S343-W4A-MEASURE.sh — o braco de EXECUCAO do AC-16 (PLAN-186 W4a).
# CEREMONY-LINT: handwritten-exception: nao ha molde para este script — ele e o
# instrumento PROPRIO desta wave. Nao aplica patch, nao assina, nao toca
# nenhum path canonico: empurra dois commits VAZIOS, espera cada run do
# `Validate` TERMINAR, e escreve a tabela.
#
# RODA DEPOIS DO LAND, com o Owner presente. O push do LAND ja e a corrida
# 1/3; este script produz as corridas 2 e 3, SERIALIZADAS, e coleta.
#
# POR QUE SERIALIZAR. `validate.yml:20-22` declara
# `concurrency: {group: validate-${{ github.ref }}, cancel-in-progress: true}`.
# Dois pushes seguidos no `main` CANCELAM o run anterior, e um leg cancelado
# reporta `cancelled` — a assinatura que este repo ja confundiu com estouro de
# timeout. Cada corrida so comeca depois que a anterior termina.
#
# O QUE ELE NAO FAZ, por desenho (AGENTS.md:9-11):
#   - nao prediz wall-clock, nao declara speedup, nao compara com um alvo;
#   - a tabela e SUBTRACAO BRUTA: baseline medido menos delecao medida.
#   O AC-6 e o AC-11 sao JULGADOS pelo Owner sobre essa tabela; este script
#   entrega o dado, nao o veredito.
#
# Uso:
#   bash .claude/plans/PLAN-186/OWNER-S343-W4A-MEASURE.sh --dry-run
#   bash .claude/plans/PLAN-186/OWNER-S343-W4A-MEASURE.sh
set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *)
      printf '\n\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$arg" >&2
      printf '  Formas validas:\n    bash %s --dry-run\n    bash %s\n' "$0" "$0" >&2
      exit 1 ;;
  esac
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes da medicao (o UNICO bloco que muda entre waves) ------------
PLAN_DIR=".claude/plans/PLAN-186"
CEREMONY_DIR="$PLAN_DIR/s343-ceremony-w4a"
W4_DIR="$PLAN_DIR/w4"
REPORT_S340="$W4_DIR/validate-deletion-measure-S340.md"
RESULT="$W4_DIR/validate-deletion-RESULT.md"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
WORKFLOW="validate.yml"
VALIDATE_YML=".github/workflows/validate.yml"
SMOKE_YML=".github/workflows/smoke-install.yml"
# Os TRES baselines REGISTRADOS POR ID (§6 do relatorio da S340). Comparar
# contra "os ultimos runs do main" mediria outra coisa: estes tres sao os que
# rodaram a arvore PRE-delecao com a suite que a delecao remove.
BASELINE_IDS="33709753629 33656365016 33630753334"
RUNS_TOTAL=3
PUSH_REMOTE="origin"
PUSH_BRANCH="main"
# Teto de espera por run, em segundos (um Validate ronda 20 min pre-delecao).
WATCH_TIMEOUT_S=5400
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
warn(){ printf '  \033[33mWARN\033[0m %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

_expect() {
  _ev="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
  if [ -z "$_ev" ]; then
    die "chave '$1' AUSENTE em $BASELINE_ENV — a medicao nao compara contra nada"
  fi
  printf '%s' "$_ev"
}

# ---------------------------------------------------------------------------
step "M0 — pre-condicoes (o land JA aconteceu?)"
# ---------------------------------------------------------------------------
command -v gh >/dev/null 2>&1 || die "M0: gh ausente — sem ele nao ha como esperar nem coletar os runs"
gh auth status >/dev/null 2>&1 || die "M0: gh nao esta autenticado (gh auth login)"
python3 -c "import yaml" >/dev/null 2>&1 || die "M0: PyYAML ausente — o mapa job->classe de runner sai do proprio workflow"
[ -f "$BASELINE_ENV" ] || die "M0: base esperada ausente: $BASELINE_ENV"
[ -f "$REPORT_S340" ] || die "M0: relatorio da S340 ausente: $REPORT_S340 — os 3 baselines vivem la"
[ -d "$W4_DIR" ] || die "M0: $W4_DIR ausente"

_cur_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '')"
[ "$_cur_branch" = "$PUSH_BRANCH" ] || die "M0: HEAD esta em '$_cur_branch', nao em '$PUSH_BRANCH'"

# O land TEM de estar em HEAD. Medir a delecao numa arvore que ainda a tem
# seria medir o baseline duas vezes e chamar de resultado.
_step_a="$(_expect EXPECTED_DELETED_STEP_A)"
_step_b="$(_expect EXPECTED_DELETED_STEP_B)"
_a="$( { grep -c -F -- "- name: $_step_a" "$VALIDATE_YML" || true; } )"
_b="$( { grep -c -F -- "- name: $_step_b" "$VALIDATE_YML" || true; } )"
{ [ "$_a" = "0" ] && [ "$_b" = "0" ]; } \
  || die "M0: os dois steps AINDA estao em $VALIDATE_YML (A=$_a, B=$_b).
  O land nao aconteceu. Rode primeiro:
    bash $ROOT/$PLAN_DIR/OWNER-S343-W4A-LAND.sh"
_to="$( { grep -c -F -- "timeout-minutes: $(_expect EXPECTED_SMOKE_TIMEOUT_POST)" "$SMOKE_YML" || true; } )"
[ "$_to" = "1" ] || die "M0: $SMOKE_YML nao tem o timeout novo — o land nao aconteceu por inteiro"
ok "M0: o land esta em HEAD (os 2 steps fora; timeout do Smoke em $(_expect EXPECTED_SMOKE_TIMEOUT_POST))"

# Os 3 ids de baseline TEM de constar do relatorio: um id digitado errado aqui
# compararia contra um run qualquer, e o erro seria invisivel na tabela.
for _bid in $BASELINE_IDS; do
  grep -qF -- "$_bid" "$REPORT_S340" \
    || die "M0: o baseline $_bid NAO consta de $REPORT_S340.
  Os baselines sao REGISTRADOS por id; um id que nao esta no registro nao e
  um baseline, e a comparacao seria contra 'algum run recente do main'."
done
ok "M0: os $(printf '%s\n' $BASELINE_IDS | wc -l | tr -d ' ') baselines constam do registro da S340"

if ! git diff --quiet || ! git diff --cached --quiet; then
  die "M0: a arvore tem modificacoes — os commits VAZIOS desta medicao nao podem
  arrastar trabalho de terceiros. Commite ou reverta antes."
fi
ok "M0: arvore limpa"

# ---------------------------------------------------------------------------
step "M0-d — os 3 baselines abrangem TRES commits (ressalva do proprio relatorio)"
# ---------------------------------------------------------------------------
# Rail codex do land (r1, P1). O §6 de `$REPORT_S340` diz, com todas as
# letras, que os 3 ids registrados NAO sao o baseline definitivo: rodaram em
# `8efe09b`, `400638e` e `b6dce78`, e `b6dce78` alterou arquivos que o CI
# EXECUTA. Subtrair as corridas pos-delecao desses 3 e depois ler a diferenca
# como efeito DA DELECAO atribui a ela um drift de carga que ela nao causou —
# e um AC-16 fechado sobre isso seria fechado sobre um numero invalido.
#
# O relatorio ja nomeia as DUAS saidas legitimas: (a) re-rodar 3 baselines num
# unico sha ANTES da delecao, ou (b) declarar o drift aceito, com o diff dos
# arquivos que o CI executa. Este gate NAO escolhe por ninguem: ele MEDE o
# drift, imprime, e para. So `CEO_W4A_BASELINE_DRIFT_ACK=I-ACCEPT` segue — e o
# reconhecimento vai carimbado no RESULT, para que quem ler a tabela amanha
# saiba que a comparacao e entre commits diferentes.
grep -q 'nao o baseline definitivo\|não o baseline definitivo' "$REPORT_S340" \
  || die "M0-d: a ressalva do §6 sumiu de $REPORT_S340.
  Este gate existe porque o relatorio DECLARA que os 3 baselines nao sao
  definitivos. Se a declaracao mudou, o gate esta medindo o mundo errado:
  releia o §6 antes de mexer aqui."

BASELINE_SHAS=""
for _b in $BASELINE_IDS; do
  _b_meta="$( gh run view "$_b" --json headSha,event,headBranch \
                -q '.headSha + "|" + .event + "|" + .headBranch' 2>/dev/null || printf '' )"
  [ -n "$_b_meta" ] || die "M0-d: nao consegui ler o baseline $_b pela API.
  Sem o sha de cada baseline nao da para declarar o drift com evidencia."
  _b_sha="${_b_meta%%|*}"
  _b_rest="${_b_meta#*|}"
  case "$_b_rest" in
    "push|$PUSH_BRANCH") : ;;
    *) die "M0-d: o baseline $_b e '$_b_rest', nao 'push|$PUSH_BRANCH'.
  Um baseline que nao e push em $PUSH_BRANCH mede outra carga (a matriz de
  Python abre 4 legs fora do push) e nao serve de referencia." ;;
  esac
  printf '  baseline %s -> %s (push em %s)\n' "$_b" "$( printf '%s' "$_b_sha" | cut -c1-7 )" "$PUSH_BRANCH"
  BASELINE_SHAS="$BASELINE_SHAS $_b_sha"
done
BASELINE_SHAS="${BASELINE_SHAS# }"

# O drift medido: quantos commits e quantos arquivos separam o baseline MAIS
# ANTIGO do HEAD que vai ser medido. Nao ha julgamento aqui — so o numero.
_oldest_sha="$( printf '%s' "$BASELINE_SHAS" | tr ' ' '\n' | tail -1 )"
DRIFT_COMMITS="n/d"; DRIFT_FILES="n/d"
if git cat-file -e "${_oldest_sha}^{commit}" 2>/dev/null; then
  DRIFT_COMMITS="$( git rev-list --count "$_oldest_sha..HEAD" 2>/dev/null || printf 'n/d' )"
  DRIFT_FILES="$( git diff --name-only "$_oldest_sha" HEAD 2>/dev/null | wc -l | tr -d ' ' )"
  printf '  drift entre o baseline mais antigo (%s) e HEAD: %s commit(s), %s arquivo(s)\n' \
         "$( printf '%s' "$_oldest_sha" | cut -c1-7 )" "$DRIFT_COMMITS" "$DRIFT_FILES"
else
  warn "M0-d: o sha do baseline mais antigo nao esta neste checkout (clone raso?) — drift NAO medido"
fi
export BASELINE_SHAS DRIFT_COMMITS DRIFT_FILES

# Rail r3 do land (P2): a saida (a) que este gate IMPRIME e re-rodar os tres
# baselines num UNICO sha pre-delecao. Se o Owner fizer isso e trocar os
# BASELINE_IDS, exigir o reconhecimento de drift assim mesmo — e carimbar no
# RESULT que "os tres nao rodaram no mesmo commit" — seria publicar uma
# ressalva FALSA e tornar a rota limpa impossivel de seguir. O gate mede a
# unicidade em vez de assumi-la.
_uniq_shas="$( printf '%s' "$BASELINE_SHAS" | tr ' ' '\n' | sort -u | grep -c . )"
if [ "$_uniq_shas" = "1" ]; then
  ok "M0-d: os $RUNS_TOTAL baselines rodaram no MESMO sha ($( printf '%s' "$BASELINE_SHAS" | cut -c1-7 )) — nao ha drift a reconhecer"
  BASELINE_DRIFT_ACK="nao-aplicavel (baseline controlado: 1 sha)"
  DRIFT_COMMITS="0"
elif [ "${CEO_W4A_BASELINE_DRIFT_ACK:-}" = "I-ACCEPT" ]; then
  warn "M0-d: drift de baseline RECONHECIDO pelo Owner (CEO_W4A_BASELINE_DRIFT_ACK=I-ACCEPT)"
  BASELINE_DRIFT_ACK="I-ACCEPT"
else
  die "M0-d: os 3 baselines NAO rodaram no mesmo sha, e o relatorio da S340 diz
  que eles nao sao o baseline definitivo (§6).

  Shas dos baselines: $BASELINE_SHAS
  Drift ate HEAD:     $DRIFT_COMMITS commit(s), $DRIFT_FILES arquivo(s)

  Duas saidas, as duas do Owner:
   (a) RE-RODAR 3 baselines num unico sha PRE-delecao (a rota limpa: um branch
       ancorado nesse sha, sem a copia dos steps, 3 pushes serializados) e
       trocar BASELINE_IDS aqui pelos ids novos.
   (b) ACEITAR o drift conscientemente:
         CEO_W4A_BASELINE_DRIFT_ACK=I-ACCEPT bash \$0
       O reconhecimento e os numeros acima entram CARIMBADOS no $RESULT, e a
       tabela passa a se ler como subtracao ENTRE COMMITS DIFERENTES — nunca
       como efeito isolado da delecao."
fi
export BASELINE_DRIFT_ACK

# ---------------------------------------------------------------------------
step "M1 — a corrida 1/3 e o push do LAND"
# ---------------------------------------------------------------------------
# O commit que trouxe a delecao e o ULTIMO que tocou o validate.yml.
LAND_SHA="$( git log -1 --format=%H -- "$VALIDATE_YML" )"
[ -n "$LAND_SHA" ] || die "M1: nao achei o commit que tocou $VALIDATE_YML"
printf '  commit do land: %s\n' "$LAND_SHA"
git --no-pager log -1 --format='    %h %s' "$LAND_SHA" | sed 's/^/  /'

# Rail codex do land (r2, P2): a versao anterior deste bloco DIZIA que derivar
# o sha assim "tolera commits livres entre o land e esta medicao". Tolerava a
# DERIVACAO, nao a MEDICAO: se um commit qualquer entrar entre o land e aqui
# sem tocar o validate.yml, a corrida 1/3 sai da arvore do land enquanto as
# corridas 2 e 3 (commits VAZIOS sobre o HEAD novo) saem de OUTRA arvore — e a
# media pos-delecao misturaria duas cargas em silencio. As tres corridas tem de
# medir a MESMA arvore.
_head_sha="$( git rev-parse HEAD )"
if [ "$_head_sha" != "$LAND_SHA" ]; then
  _drift_n="$( git rev-list --count "$LAND_SHA..HEAD" 2>/dev/null || printf '?' )"
  if [ "${CEO_W4A_POST_DRIFT_ACK:-}" = "I-ACCEPT" ]; then
    warn "M1: $_drift_n commit(s) entre o land e esta medicao — drift RECONHECIDO (CEO_W4A_POST_DRIFT_ACK=I-ACCEPT)"
    POST_DRIFT_COMMITS="$_drift_n"
  else
    die "M1: HEAD ($( git rev-parse --short HEAD )) nao e o commit do land
  ($( git rev-parse --short "$LAND_SHA" )): ha $_drift_n commit(s) entre os dois.

  A corrida 1/3 e o run do commit do LAND; as corridas 2 e 3 sao commits
  VAZIOS sobre o HEAD. Com commits no meio, as tres nao medem a mesma arvore e
  a media pos-delecao mistura cargas — o mesmo defeito que o M0-d recusa do
  lado do baseline.

  Duas saidas:
   (a) MEDIR AGORA, logo apos o land, com HEAD == commit do land (a rota limpa).
   (b) Se os commits do meio comprovadamente nao tocam nada que o CI executa,
       aceitar conscientemente:
         CEO_W4A_POST_DRIFT_ACK=I-ACCEPT bash \$0
       O numero entra CARIMBADO no $RESULT."
  fi
else
  POST_DRIFT_COMMITS="0"
fi
export POST_DRIFT_COMMITS

_run_for_sha() {
  # id do run mais RECENTE do workflow para um sha. Sem `head` num pipe sob
  # pipefail (SIGPIPE mata o produtor e o `|| true` mascara a diferenca entre
  # "nao achou" e "morreu"): o jq corta.
  #
  # Rail codex do land (r1, P2): o filtro por EVENTO e por BRANCH nao e
  # cosmetico. Este workflow tambem roda no `schedule` diario, e num run que
  # NAO e `push` a matriz de Python abre 4 legs em vez de 2 — um run agendado
  # do mesmo sha mediria OUTRA carga e seria incomparavel com os 3 baselines
  # de `push`. A checagem e em DUAS camadas (o filtro do servidor e a
  # verificacao do campo devolvido), porque um filtro que o `gh` ignorasse
  # em silencio nos devolveria o run errado sem dizer.
  gh run list --workflow="$WORKFLOW" --commit "$1" \
      --event push --branch "$PUSH_BRANCH" --limit 20 \
      --json databaseId,createdAt,event,headBranch \
      -q 'map(select(.event == "push" and .headBranch == "'"$PUSH_BRANCH"'"))
          | sort_by(.createdAt) | reverse | .[0].databaseId' 2>/dev/null || printf ''
}

_assert_push_run() {
  # Segunda camada: confirma no PROPRIO run que evento e branch sao os
  # esperados. `gh run list` filtra do lado do servidor; esta funcao le o
  # registro do run e RECUSA por nome se a forma nao bater.
  _ap_id="$1"; _ap_what="$2"
  _ap_ev="$( gh run view "$_ap_id" --json event,headBranch \
               -q '.event + "|" + .headBranch' 2>/dev/null || printf '' )"
  case "$_ap_ev" in
    "push|$PUSH_BRANCH") : ;;
    "") die "M1: nao consegui ler evento/branch do run $_ap_id ($_ap_what) — sem isso a comparacao nao e defensavel" ;;
    *)  die "M1: o run $_ap_id ($_ap_what) e '$_ap_ev', nao 'push|$PUSH_BRANCH'.
  Num run que nao e de push a matriz de Python abre 4 legs em vez de 2: a
  comparacao com os baselines de push mediria carga diferente, nao a delecao." ;;
  esac
}

RUN_IDS=""
_r1="$( _run_for_sha "$LAND_SHA" )"
[ -n "$_r1" ] || die "M1: nenhum run de PUSH do $WORKFLOW em $PUSH_BRANCH para o commit do land ($LAND_SHA).
  O push chegou? Veja:  gh run list --workflow=$WORKFLOW --event push --limit 5"
_assert_push_run "$_r1" "corrida 1/3"
ok "M1: corrida 1/3 = run $_r1 (evento push em $PUSH_BRANCH, confirmado no proprio run)"

_watch() {
  _w_id="$1"; _w_n="$2"
  printf '  esperando a corrida %s/%s (run %s) terminar (teto %ss)...\n' \
         "$_w_n" "$RUNS_TOTAL" "$_w_id" "$WATCH_TIMEOUT_S"
  printf '    para acompanhar ao vivo noutro terminal:  gh run watch %s\n' "$_w_id"
  # A espera e um LOOP DE POLLING com prazo, e nao `timeout gh run watch`:
  # `timeout(1)` e GNU coreutils e NAO existe no macOS de fabrica (medido
  # nesta maquina: "command not found: timeout"), entao a forma com `timeout`
  # morreria no primeiro uso — na manha do Owner, no meio da cerimonia.
  # O criterio e o MESMO do `--exit-status`: so `completed`+`success` segue.
  _w_waited=0
  while :; do
    _w_st="$( gh run view "$_w_id" --json status,conclusion \
                -q '.status + "|" + (.conclusion // "")' 2>/dev/null || printf '|' )"
    case "$_w_st" in
      completed\|success) break ;;
      completed\|*)
        die "M: a corrida $_w_n/$RUNS_TOTAL (run $_w_id) terminou '${_w_st#completed|}'.
  Uma medicao so soma runs VERDES. Se foi 'cancelled', dois pushes se
  atropelaram (concurrency.cancel-in-progress) — investigue antes de repetir.
    gh run view $_w_id" ;;
    esac
    if [ "$_w_waited" -ge "$WATCH_TIMEOUT_S" ]; then
      die "M: a corrida $_w_n/$RUNS_TOTAL (run $_w_id) nao terminou em ${WATCH_TIMEOUT_S}s.
  NAO empurre a proxima: o concurrency cancelaria esta. Investigue:
    gh run view $_w_id"
    fi
    sleep 30
    _w_waited=$(( _w_waited + 30 ))
    printf '    ... %ss (status: %s)\n' "$_w_waited" "${_w_st%%|*}"
  done
  ok "corrida $_w_n/$RUNS_TOTAL verde (run $_w_id)"
}

if [ "$DRY_RUN" = "1" ]; then
  printf '\n\033[33mDRY-RUN\033[0m — M0/M1 verdes. Corrida 1/3 = run %s.\n' "$_r1"
  printf '  As corridas 2 e 3 (commits VAZIOS + espera) NAO sao executadas em dry-run.\n'
  printf '  A coleta tambem nao: ela precisa das 3 corridas.\n'
  exit 0
fi

_watch "$_r1" 1
RUN_IDS="$_r1"

# ---------------------------------------------------------------------------
step "M2 — corridas 2 e 3: commits VAZIOS, uma de cada vez"
# ---------------------------------------------------------------------------
_n=2
while [ "$_n" -le "$RUNS_TOTAL" ]; do
  _msg="chore(PLAN-186 W4a): corrida de medição $_n/$RUNS_TOTAL — commit vazio"
  git commit --allow-empty -q -m "$_msg" || die "M2: o commit vazio $_n falhou"
  _sha="$( git rev-parse HEAD )"
  ok "commit vazio $_n/$RUNS_TOTAL: $( git rev-parse --short HEAD )"
  git push "$PUSH_REMOTE" "HEAD:$PUSH_BRANCH" >/dev/null \
    || die "M2: o push da corrida $_n falhou. O commit $_sha esta LOCAL.
  Repita:  git -C $ROOT push $PUSH_REMOTE HEAD:$PUSH_BRANCH"
  # O run pode demorar alguns segundos para aparecer na API.
  _rid=""
  _tries=0
  while [ -z "$_rid" ] && [ "$_tries" -lt 20 ]; do
    sleep 6
    _rid="$( _run_for_sha "$_sha" )"
    _tries=$(( _tries + 1 ))
  done
  [ -n "$_rid" ] || die "M2: o run de PUSH da corrida $_n nao apareceu em ~2 min para o sha $_sha"
  _assert_push_run "$_rid" "corrida $_n/$RUNS_TOTAL"
  _watch "$_rid" "$_n"
  RUN_IDS="$RUN_IDS $_rid"
  _n=$(( _n + 1 ))
done
ok "3 corridas pos-delecao, SERIALIZADAS e verdes: $RUN_IDS"

# ---------------------------------------------------------------------------
step "M3 — coleta e tabela (subtracao bruta, sem previsao)"
# ---------------------------------------------------------------------------
python3 - "$ROOT" "$RESULT" "$VALIDATE_YML" "$LAND_SHA" \
         "$BASELINE_IDS" "$RUN_IDS" <<'PY' || die "M3: a coleta falhou"
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

root, result_rel, workflow_rel, land_sha, baseline_ids, run_ids = sys.argv[1:7]
BASE = baseline_ids.split()
POST = run_ids.split()

import yaml  # noqa: E402  (probado no M0)


def gh_json(args):
    proc = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("gh %s falhou: %s" % (" ".join(args), proc.stderr[-500:]))
    return json.loads(proc.stdout)


def parse(ts):
    if not ts:
        return None
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def hhmmss(seconds):
    if seconds is None:
        return "n/d"
    seconds = int(round(seconds))
    return "%dm%02ds" % (seconds // 60, seconds % 60)


# Mapa job -> classe de runner, DERIVADO do proprio workflow. `gh run view
# --json jobs` NAO expoe o label do runner (medido no gh 2.98.x), entao a
# classe vem do `runs-on` de cada job, casado pelo nome de exibicao: `name:`
# se houver, senao a chave; legs de matriz chegam como "<nome> (<leg>)".
wf = yaml.safe_load(open(workflow_rel, encoding="utf-8"))
display_to_class = {}
for key, jd in wf["jobs"].items():
    display = jd.get("name") or key
    display_to_class[display] = str(jd.get("runs-on"))


def runner_class(job_name):
    if job_name in display_to_class:
        return display_to_class[job_name]
    # leg de matriz: "<display> (<leg>)"
    if job_name.endswith(")") and " (" in job_name:
        head = job_name[: job_name.rindex(" (")]
        if head in display_to_class:
            return display_to_class[head]
    return "DESCONHECIDO"


def measure(run_id):
    run = gh_json(["run", "view", run_id, "--json",
                   "databaseId,displayTitle,headSha,conclusion,startedAt,updatedAt,jobs"])
    started, updated = parse(run.get("startedAt")), parse(run.get("updatedAt"))
    wall = (updated - started).total_seconds() if started and updated else None
    per_class = {}
    validate_job = None
    biggest = (None, -1.0)
    # Rail codex do land (r1, P2): um run pode CONCLUIR `success` com todos os
    # jobs `skipped` — basta a variavel de repo `CEO_SOTA_DISABLE=1`, que e a
    # condicao de job de `validate` E de `hook-tests-python-matrix`. Sem esta
    # recusa, os jobs sem timestamp cairiam no `continue` em silencio, o
    # `validate_job` ficaria `None`, e a tabela seria commitada com `n/d` no
    # lugar do numero — uma medicao vazia com cara de medicao.
    _skipped = [j.get("name") for j in run.get("jobs", [])
                if (j.get("conclusion") or "") == "skipped"]
    if _skipped:
        raise SystemExit(
            "M3: o run %s concluiu com %d job(s) SKIPPED (%s).\n"
            "  Um run com jobs pulados nao mediu a carga que esta medicao compara.\n"
            "  Causa tipica: a variavel de repositorio CEO_SOTA_DISABLE=1, que e a\n"
            "  condicao de job do `validate` e da matriz. Desligue-a e repita."
            % (run_id, len(_skipped), ", ".join(sorted(set(_skipped))[:6])))
    for job in run.get("jobs", []):
        js, jc = parse(job.get("startedAt")), parse(job.get("completedAt"))
        if not (js and jc):
            continue
        dur = (jc - js).total_seconds()
        cls = runner_class(job["name"])
        per_class[cls] = per_class.get(cls, 0.0) + dur
        if job["name"] == (wf["jobs"]["validate"].get("name") or "validate"):
            validate_job = dur
        if dur > biggest[1]:
            biggest = (job["name"], dur)
    # Nenhum job pode sumir em silencio da soma por classe, e o job cuja
    # duracao e a COLUNA CENTRAL da tabela tem de existir: `n/d` ali seria uma
    # linha publicada sem medicao por tras.
    _no_ts = [j.get("name") for j in run.get("jobs", [])
              if not (parse(j.get("startedAt")) and parse(j.get("completedAt")))]
    if _no_ts:
        raise SystemExit(
            "M3: o run %s tem %d job(s) sem startedAt/completedAt (%s).\n"
            "  A soma por classe de runner sairia INCOMPLETA e a tabela mentiria\n"
            "  por omissao. Investigue o run antes de publicar o resultado."
            % (run_id, len(_no_ts), ", ".join(sorted(set(_no_ts))[:6])))
    # Rail r3 do land (P2): as corridas POS-delecao passam pelo `_watch`, que
    # so segue em `completed|success`. Os BASELINES nao passam por ele — sao
    # ids registrados. Um baseline re-rodado que hoje esteja VERMELHO entraria
    # na comparacao sem uma linha de aviso. A exigencia e a mesma dos dois
    # lados: so run verde entra na tabela.
    _concl = run.get("conclusion") or ""
    if _concl != "success":
        raise SystemExit(
            "M3: o run %s concluiu '%s', nao 'success'.\n"
            "  Uma medicao so soma runs VERDES — dos dois lados da subtracao.\n"
            "  Se este e um baseline registrado que foi re-rodado e falhou,\n"
            "  escolha outro id verde ou re-rode o baseline." % (run_id, _concl or "n/d"))
    if validate_job is None:
        raise SystemExit(
            "M3: o run %s nao tem o job '%s'.\n"
            "  Sem ele a coluna central da tabela seria `n/d`: nao ha o que comparar."
            % (run_id, wf["jobs"]["validate"].get("name") or "validate"))
    return {
        "id": str(run.get("databaseId")),
        "sha": (run.get("headSha") or "")[:7],
        "conclusion": run.get("conclusion"),
        "wall": wall,
        "validate": validate_job,
        "biggest": biggest,
        "per_class": per_class,
    }


base = [measure(r) for r in BASE]
post = [measure(r) for r in POST]

unknown = sorted({c for m in base + post for c in m["per_class"] if c == "DESCONHECIDO"})
classes = sorted({c for m in base + post for c in m["per_class"]})


def avg(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def rows(group):
    out = []
    for m in group:
        cells = ["`%s`" % m["id"], m["sha"], m["conclusion"] or "?",
                 hhmmss(m["wall"]), hhmmss(m["validate"])]
        for c in classes:
            cells.append("%.2f" % (m["per_class"].get(c, 0.0) / 60.0))
        cells.append("%s — %s" % (hhmmss(m["biggest"][1]), m["biggest"][0]))
        out.append("| " + " | ".join(cells) + " |")
    return out


def mean_row(label, group):
    cells = [label, "—", "—", hhmmss(avg([m["wall"] for m in group])),
             hhmmss(avg([m["validate"] for m in group]))]
    for c in classes:
        cells.append("%.2f" % (avg([m["per_class"].get(c, 0.0) for m in group]) / 60.0))
    cells.append("—")
    return "| " + " | ".join(cells) + " |"


header = ["run", "sha", "conclusion", "RUN wall", "job `validate`"]
header += ["min `%s`" % c for c in classes]
header += ["maior job restante"]

L = []
L.append("# PLAN-186 W4a — RESULTADO da deleção dos dois steps duplicados\n")
L.append("> Gerado por `%s/OWNER-S343-W4A-MEASURE.sh` na cerimônia `wave-s343-w4a`.\n"
         "> **Este documento é subtração bruta de medições. Não há previsão, alvo\n"
         "> nem claim de velocidade** (`AGENTS.md:9-11`): os números abaixo dizem o\n"
         "> que as seis execuções custaram, e o AC-6/AC-11 são julgados pelo Owner\n"
         "> sobre eles.\n" % ".claude/plans/PLAN-186")
L.append("")
L.append("## 1. O que foi comparado")
L.append("")
L.append("- **Baseline (pré-deleção):** os TRÊS runs REGISTRADOS por id no §6 de")
L.append("  `validate-deletion-measure-S340.md` — nunca «os últimos runs do main».")
L.append("")
_bl_shas = (os.environ.get("BASELINE_SHAS", "") or "").split()
if len(set(_bl_shas)) == 1:
    # Baseline CONTROLADO: os 3 rodaram no mesmo sha. Carimbar aqui a ressalva
    # de drift seria publicar uma ressalva FALSA (rail r3, P2).
    L.append("> **Baseline CONTROLADO.** Os %d runs de baseline rodaram no MESMO"
             % len(_bl_shas))
    L.append("> commit (`%s`), então a subtração abaixo não carrega drift de" % _bl_shas[0][:7])
    L.append("> árvore entre os baselines.")
else:
    L.append("> **RESSALVA CARIMBADA — leia antes de subtrair.** Os baselines NÃO")
    L.append("> rodaram no mesmo commit: `%s`." % (os.environ.get("BASELINE_SHAS", "n/d") or "n/d"))
    L.append("> Entre o baseline mais antigo e o `HEAD` medido há **%s commit(s)** e"
             % (os.environ.get("DRIFT_COMMITS", "n/d") or "n/d"))
    L.append("> **%s arquivo(s)** de diferença, e um deles alterou arquivos que o CI"
             % (os.environ.get("DRIFT_FILES", "n/d") or "n/d"))
    L.append("> executa (§6 do relatório da S340 declara, literalmente, que esta tabela")
    L.append("> «é o registro do que existia, não o baseline definitivo»). O Owner")
    L.append("> reconheceu o drift com `CEO_W4A_BASELINE_DRIFT_ACK=%s`."
             % (os.environ.get("BASELINE_DRIFT_ACK", "n/d") or "n/d"))
    L.append("> **Consequência:** a subtração abaixo é entre commits DIFERENTES. Parte")
    L.append("> da diferença é carga que mudou entre eles, não a deleção. Fechar o")
    L.append("> AC-6/AC-11 sobre ela sem descontar isso atribuiria à deleção um efeito")
    L.append("> que ela não teve.")
L.append("")
L.append("- **Deleção (pós):** a corrida 1/3 é o push do LAND (`%s`); as corridas" % land_sha[:7])
L.append("  2 e 3 são commits VAZIOS, empurrados SERIALIZADOS (o")
L.append("  `concurrency.cancel-in-progress` do `validate.yml` cancela runs")
L.append("  consecutivos, e um leg cancelado reporta `cancelled`).")
L.append("- **Wall do RUN** = `startedAt`→`updatedAt` do run (`completedAt` não é")
L.append("  campo de run no `gh`; é campo de JOB). **Minutos por classe de runner**")
L.append("  = soma de `startedAt`→`completedAt` de cada JOB, com a classe DERIVADA")
L.append("  do `runs-on` do próprio `validate.yml` (o `gh` não expõe o label).")
L.append("")
if unknown:
    L.append("> **Atenção:** %d job(s) não casaram nenhum `runs-on` do workflow e caíram"
             % len(unknown))
    L.append("> em `DESCONHECIDO`. A soma por classe está INCOMPLETA — não some as")
    L.append("> colunas como se fossem o total.")
    L.append("")
L.append("## 2. Baseline (pré-deleção, 3 runs registrados)")
L.append("")
L.append("| " + " | ".join(header) + " |")
L.append("|" + "---|" * len(header))
L.extend(rows(base))
L.append(mean_row("**média**", base))
L.append("")
L.append("## 3. Deleção (pós, 3 runs serializados)")
L.append("")
L.append("| " + " | ".join(header) + " |")
L.append("|" + "---|" * len(header))
L.extend(rows(post))
L.append(mean_row("**média**", post))
L.append("")
L.append("## 4. Subtração (média pós − média baseline)")
L.append("")
L.append("| grandeza | baseline | deleção | delta |")
L.append("|---|---|---|---|")


def delta_line(label, key, minutes=False, cls=None):
    if cls is not None:
        b = avg([m["per_class"].get(cls, 0.0) for m in base])
        p = avg([m["per_class"].get(cls, 0.0) for m in post])
        fmt = lambda v: "n/d" if v is None else "%.2f" % (v / 60.0)  # noqa: E731
        d = None if (b is None or p is None) else (p - b)
        return "| %s | %s | %s | %s |" % (label, fmt(b), fmt(p),
                                          "n/d" if d is None else "%+.2f" % (d / 60.0))
    b = avg([m[key] for m in base])
    p = avg([m[key] for m in post])
    d = None if (b is None or p is None) else (p - b)
    ds = "n/d" if d is None else ("%s%s" % ("−" if d < 0 else "+", hhmmss(abs(d))))
    return "| %s | %s | %s | %s |" % (label, hhmmss(b), hhmmss(p), ds)


L.append(delta_line("RUN wall", "wall"))
L.append(delta_line("job `validate`", "validate"))
for c in classes:
    L.append(delta_line("minutos `%s`" % c, None, cls=c))
L.append("")
L.append("**Como ler — e o que estes números NÃO dizem.** As colunas acima são a")
L.append("SUBTRAÇÃO BRUTA entre dois conjuntos de runs. Elas **não** isolam o custo")
L.append("dos dois steps deletados: os baselines rodaram em commits diferentes")
L.append("(ressalva carimbada na §1), e parte do delta é carga que mudou entre")
L.append("eles. Atribuir o delta inteiro à deleção seria um claim de velocidade")
L.append("sem baseline controlado — proibido por `AGENTS.md:9-11`.")
L.append("")
L.append("O que se pode dizer com o que está medido: o delta do RUN wall tende a")
L.append("ser MENOR que o delta do job `validate`, porque o run termina quando o")
L.append("ÚLTIMO job termina e o piso passa a ser outro job — a coluna «maior job")
L.append("restante» diz qual. Um número causal exige o que o §6 do relatório da")
L.append("S340 já pedia: três baselines RE-RODADOS num único sha pré-deleção.")
if (os.environ.get("POST_DRIFT_COMMITS", "0") or "0") != "0":
    L.append("")
    L.append("> **Atenção:** houve %s commit(s) entre o commit do land e esta"
             % os.environ["POST_DRIFT_COMMITS"])
    L.append("> medição, reconhecidos com `CEO_W4A_POST_DRIFT_ACK`. A corrida 1/3 e")
    L.append("> as corridas 2 e 3 saíram de árvores diferentes: a média pós-deleção")
    L.append("> mistura essas árvores.")
L.append("")
L.append("## 5. Cobertura — o que NÃO mudou")
L.append("")
L.append("A união exata dos node-ids dos dois steps deletados é o que")
L.append("`hook-tests-python-matrix` já roda, em 3.9 e 3.12. A igualdade foi")
L.append("RE-DERIVADA por conjunto (sha256 da lista ordenada) no V5 do LAND, sobre")
L.append("a árvore que foi landada — não citada de um relatório anterior.")
L.append("")
L.append("## 6. Perdas de ambiente ACEITAS e declaradas")
L.append("")
L.append("| variável | antes | depois | por quê |")
L.append("|---|---|---|---|")
L.append("| `PYTHONPATH: \".\"` | ausente nos 2 steps, presente na matriz | SEMPRE presente | recuperar exigiria dimensão de matriz que dobra o custo do job pago |")
L.append("| `CEO_HOOK_ADAPTER: claude` | só no step A (que rodava só hooks) | SEMPRE ausente | a matriz roda hooks+scripts+optimizer num único pytest; setá-la ALTERARIA o ambiente de scripts/optimizer. É o default documentado do adapter |")
L.append("")
open(result_rel, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("  escrito: %s" % result_rel)
for m in base + post:
    print("    run %s  %s  wall=%s  validate=%s" %
          (m["id"], m["conclusion"], hhmmss(m["wall"]), hhmmss(m["validate"])))
PY
ok "M3: $RESULT escrito"

# ---------------------------------------------------------------------------
step "M4 — commit do resultado (sem editor)"
# ---------------------------------------------------------------------------
# NOTA HONESTA: este commit dispara um QUARTO run do Validate. Ele NAO faz
# parte da medicao — as tres corridas ja terminaram e estao na tabela.
git add -- "$RESULT"
_staged="$( git diff --cached --name-only )"
[ "$_staged" = "$RESULT" ] || die "M4: o index carrega mais do que o resultado:
$_staged"
_msgf="$( mktemp )"
{
  printf 'docs(PLAN-186 W4a): RESULTADO das 3 corridas da deleção — subtração bruta\n\n'
  printf 'Braço de EXECUÇÃO do AC-16. Baselines POR ID (%s) contra as\n' "$BASELINE_IDS"
  printf '3 corridas pós-deleção SERIALIZADAS (%s), medidas em\n' "$RUN_IDS"
  printf 'startedAt->updatedAt do RUN e startedAt->completedAt por JOB, com a\n'
  printf 'classe de runner DERIVADA do runs-on do proprio validate.yml.\n\n'
  printf 'Sem previsão e sem claim de velocidade (AGENTS.md:9-11): a tabela é a\n'
  printf 'subtração medida, e o AC-6/AC-11 são julgados pelo Owner sobre ela.\n'
} > "$_msgf"
git commit -q -F "$_msgf" --no-edit || { rm -f "$_msgf"; die "M4: o commit do resultado falhou"; }
rm -f "$_msgf"
ok "M4: commit $( git rev-parse --short HEAD )"
git push "$PUSH_REMOTE" "HEAD:$PUSH_BRANCH" >/dev/null \
  || die "M4: o push do resultado falhou — o commit esta LOCAL.
  Repita:  git -C $ROOT push $PUSH_REMOTE HEAD:$PUSH_BRANCH"
ok "M4: empurrado (este push dispara um 4o run, que NAO entra na medicao)"

step "AC-16 — checklist para o Owner"
cat <<EOF

  Leia $RESULT e decida, item a item:

  [ ] AC-16 — as TRES corridas serializadas aconteceram e a tabela esta
      preenchida (runs $RUN_IDS contra os baselines $BASELINE_IDS).
      A recusa por cobertura NAO ocorreu: a uniao de node-ids foi re-derivada
      no V5 do LAND e bate com a matriz, por conjunto.
      => se o item acima e verdade, o AC-16 sai de ◐ para ✓ no PLAN-186.

  [ ] AC-6  — «Validate <= 14 min ... medidos em startedAt->completedAt do RUN».
      Julgue sobre a coluna «RUN wall» da secao 3. Lembre do que o proprio AC
      diz: o piso e o job «hook-tests-python-matrix (3.9)», FORA do escopo
      desta wave — um AC-6 vermelho aqui nao e um defeito desta delecao.

  [ ] AC-11 — minutos por CLASSE de runner (secao 4). O criterio ratificado
      pelo Owner em 2026-09-02 e «<= 1,3x o baseline pre-W4, medido
      localmente». «Ceo» e PAGO; «ubuntu-latest» e GRATIS em repo publico e
      e REPORTADO, nunca gated por custo.

  [ ] REQUIRED CHECK — o item que a delecao torna urgente e esta wave NAO
      resolve (achado r24 P1 do relatorio da S340, verificado hoje em
      docs/BRANCH-PROTECTION.md:101-105): o UNICO check obrigatorio e
      «validate / Governance, health, contamination, shellcheck».
      Depois desta delecao esse check NAO roda mais as suites de
      hooks/scripts — quem as roda e «hook-tests-python-matrix (3.9)» e
      «(3.12)», que NAO sao checks obrigatorios. Numa PR, uma matriz
      VERMELHA passaria a coexistir com um Validate «verde».
      Isso e config SERVER-SIDE (nao volta com «git revert») mais a linha
      do doc. Decida: adicionar os dois legs aos required checks agora, ou
      registrar a janela no PLAN-186 e fecha-la na W4b.

  [ ] W4b — o split em 3 jobs continua justificado por ATRIBUICAO DE FALHA
      (K21), nao por velocidade. Nada nesta tabela muda essa justificativa.
EOF
