#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: controles de cerimonia autorados a mao;
# nao ha gerador (o generate-ceremony.sh produz o molde SIGN/LAND, nao os
# controles positivos dos achados de uma rodada de rail especifica).
#
# rail-land-controls.sh — controles POSITIVOS das curas que o pair-rail
# do LAND (rodada 1, `rail-land-round-1.md`) exigiu nos materiais LIVRES da
# cerimônia `wave-s343-w4a`.
#
# Por que este arquivo existe e não um caso a mais em
# `test-ceremony-scripts-w4a.sh`: aquele harness roda cerimônias INTEIRAS num
# clone, e as quatro curas vivem em superfícies que um clone não alcança — o
# `M0-d` só é atingido depois do land estar em `HEAD`, e a coleta do `M3` fala
# com a API do GitHub. Estes controles extraem o TEXTO EMBARCADO dos scripts
# que serão assinados (nunca uma cópia dele) e o exercitam com substitutos.
#
# Cada caso tem a forma que este repo exige: VERMELHO sem a cura, VERDE com
# ela. Quando a cura é um estreitamento (o G7), o caso mede as DUAS regras —
# a antiga e a nova — sobre a mesma entrada, e prova que elas DIVERGEM
# exatamente onde o achado dizia.
#
# Uso:  bash .claude/plans/PLAN-186/s343-ceremony-w4a/rail-land-controls.sh
set -u

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT" || exit 2

PLAN_DIR=".claude/plans/PLAN-186"
LAND="$PLAN_DIR/OWNER-S343-W4A-LAND.sh"
MEASURE="$PLAN_DIR/OWNER-S343-W4A-MEASURE.sh"

PASS=0; FAIL=0
pass() { PASS=$(( PASS + 1 )); printf '\033[32m  PASS\033[0m %s\n' "$*"; }
fail() { FAIL=$(( FAIL + 1 )); printf '\033[31m  FAIL\033[0m %s\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

WORK="$( mktemp -d )"
trap 'rm -rf "$WORK"' EXIT

[ -f "$LAND" ]    || { printf 'ABORT: %s ausente\n' "$LAND" >&2; exit 2; }
[ -f "$MEASURE" ] || { printf 'ABORT: %s ausente\n' "$MEASURE" >&2; exit 2; }

# ---------------------------------------------------------------------------
# Extrator de função shell: da linha `^<nome>() {` até o primeiro `^}`.
# ---------------------------------------------------------------------------
_extract_fn() {
  awk -v fn="$2" '
    $0 ~ ("^" fn "\\(\\) \\{") { f=1 }
    f { print }
    f && /^\}$/ { exit }
  ' "$1"
}

# ===========================================================================
step "C1 — G7: um 404 GENÉRICO deixa de ser lido como «sem proteção»"
# ===========================================================================
# Achado P1 do rail. A API do GitHub responde 404 tanto para «este branch não
# tem protection» quanto para «este token não pode LER a protection deste
# repo». A regra ANTIGA casava `Not Found` e `"status": "404"` crus, então
# classificava autorização insuficiente como prova de ausência — e o gate
# seguia sem exigir o reconhecimento. A regra NOVA só aceita a mensagem
# específica; qualquer outra coisa cai em `unreadable`, que é fail-closed.
#
# As duas regras são extraídas: a NOVA do arquivo que vai ser assinado, a
# ANTIGA do registro do achado. O caso mede as duas sobre as MESMAS entradas.
NEW_RE="$( grep -o "grep -q 'Branch not protected'" "$LAND" | head -1 )"
if [ -z "$NEW_RE" ]; then
  fail "C1: não achei a regra NOVA em $LAND — a cura sumiu ou mudou de forma"
else
  OLD_PAT='"status": *"404"\|Not Found\|Branch not protected'
  NEW_PAT='Branch not protected'

  _classify() { # $1 = padrão, $2 = corpo
    if printf '%s' "$2" | grep -q "$1"; then printf 'unprotected'; else printf 'unreadable'; fi
  }

  # (a) O que a API viva devolve HOJE para um branch sem proteção — medido
  #     nesta máquina, corpo no stdout e mensagem no stderr.
  BODY_A='{"message":"Branch not protected","documentation_url":"https://docs.github.com/rest","status":"404"}'
  # (b) Um 404 de AUTORIZAÇÃO: mesma classe HTTP, proteção pode EXISTIR.
  BODY_B='{"message":"Not Found","documentation_url":"https://docs.github.com/rest","status":"404"}'
  # (c) Um 403 de escopo: nenhuma das duas regras deve chamar de «sem proteção».
  BODY_C='{"message":"Resource not accessible by integration","status":"403"}'

  _a_old="$( _classify "$OLD_PAT" "$BODY_A" )"; _a_new="$( _classify "$NEW_PAT" "$BODY_A" )"
  _b_old="$( _classify "$OLD_PAT" "$BODY_B" )"; _b_new="$( _classify "$NEW_PAT" "$BODY_B" )"
  _c_old="$( _classify "$OLD_PAT" "$BODY_C" )"; _c_new="$( _classify "$NEW_PAT" "$BODY_C" )"

  if [ "$_a_old" = "unprotected" ] && [ "$_a_new" = "unprotected" ]; then
    pass "C1a: no corpo REAL de hoje as duas regras dizem 'unprotected' (a cura não muda o presente)"
  else
    fail "C1a: divergência no corpo real — antiga='$_a_old' nova='$_a_new' (esperado unprotected/unprotected)"
  fi

  if [ "$_b_old" = "unprotected" ] && [ "$_b_new" = "unreadable" ]; then
    pass "C1b: VERMELHO sem a cura — o 404 de autorização era 'unprotected'; com a cura é 'unreadable' (fail-closed)"
  else
    fail "C1b: a cura não morde — antiga='$_b_old' nova='$_b_new' (esperado unprotected/unreadable)"
  fi

  if [ "$_c_old" = "unreadable" ] && [ "$_c_new" = "unreadable" ]; then
    pass "C1c: o 403 já caía em 'unreadable' nas duas regras (o caso existe para provar que C1b não é ruído do grep)"
  else
    fail "C1c: antiga='$_c_old' nova='$_c_new' (esperado unreadable/unreadable)"
  fi

  # Não-vacuidade: a ALTERNÂNCIA antiga não pode ter sobrado como CÓDIGO no
  # arquivo assinado. A busca é pelo padrão inteiro, não pela frase «Not
  # Found» solta — essa aparece de propósito na PROSA que explica a cura, e
  # um controle que casasse a prosa mediria o comentário, não o comportamento.
  if grep -q 'grep -q .*"status": \*"404"..Not Found' "$LAND"; then
    fail "C1d: a alternância antiga ainda é CÓDIGO em $LAND — o estreitamento não é o único caminho"
  else
    pass "C1d: a alternância antiga não sobrevive como código no arquivo que vai ser assinado"
  fi
fi

# ===========================================================================
step 'C2 — MEASURE: um run que nao e "push" em main e RECUSADO por nome'
# ===========================================================================
# Achado P2 do rail. O workflow também roda no `schedule`, e fora do `push` a
# matriz de Python abre 4 legs em vez de 2 — um run agendado do mesmo sha
# mediria outra carga. A função é EXTRAÍDA do arquivo que vai ser assinado e
# exercitada contra um `gh` substituto.
_extract_fn "$MEASURE" "_assert_push_run" > "$WORK/assert_push_run.sh"
if [ ! -s "$WORK/assert_push_run.sh" ]; then
  fail "C2: não consegui extrair _assert_push_run de $MEASURE"
else
  _run_case() { # $1 = o que o gh devolve; retorna o rc da função
    mkdir -p "$WORK/bin"
    { printf '#!/bin/sh\n'; printf 'printf %s\n' "'$1'"; } > "$WORK/bin/gh"
    chmod +x "$WORK/bin/gh"
    (
      PATH="$WORK/bin:$PATH"
      PUSH_BRANCH="main"
      die() { printf 'DIE: %s\n' "$*"; exit 1; }
      # shellcheck source=/dev/null
      . "$WORK/assert_push_run.sh"
      _assert_push_run 111 "caso"
    ) 2>&1
  }

  _out="$( _run_case 'push|main' )"; _rc=$?
  if [ "$_rc" -eq 0 ]; then
    pass "C2a: controle VERDE — 'push|main' passa (os outros casos não são verdes vazios)"
  else
    fail "C2a: 'push|main' foi recusado: $_out"
  fi

  _out="$( _run_case 'schedule|main' )"; _rc=$?
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -q "nao 'push|main'"; then
    pass "C2b: VERMELHO sem a cura — 'schedule|main' agora é recusado POR NOME"
  else
    fail "C2b: um run de schedule passou (rc=$_rc): $_out"
  fi

  _out="$( _run_case '' )"; _rc=$?
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -q 'nao consegui ler evento/branch'; then
    pass "C2c: leitura vazia é recusa NOMEADA, nunca um verde por omissão"
  else
    fail "C2c: leitura vazia não foi recusada (rc=$_rc): $_out"
  fi

  # A primeira camada (o filtro do servidor) também tem de estar lá: sem ela a
  # função só veria o run que o `gh` já escolheu errado.
  if grep -q -- '--event push' "$MEASURE" && grep -q -- '--branch "\$PUSH_BRANCH"' "$MEASURE"; then
    pass 'C2d: o filtro do servidor (--event push --branch main) esta no gh run list'
  else
    fail 'C2d: o gh run list nao filtra por evento/branch — a segunda camada ficaria sozinha'
  fi
fi

# ===========================================================================
step "C3 — MEASURE/M3: run com jobs SKIPPED ou sem timestamp não vira tabela"
# ===========================================================================
# Achado P2 do rail. Com a variável de repositório `CEO_SOTA_DISABLE=1` todo
# job é pulado pela própria condição de job, e o workflow ainda CONCLUI
# `success`: o `_watch` aceitaria esse run, os jobs sem timestamp cairiam num
# `continue` silencioso e a tabela sairia com `n/d` no lugar do número.
#
# O corpo de `measure()` é extraído do heredoc EMBARCADO no script assinado e
# executado com substitutos — nunca reescrito aqui.
python3 - "$MEASURE" <<'PY'
import ast
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"<<'PY'[^\n]*\n(.*?)\nPY\n", src, re.S)
if not m:
    print("  \033[31mFAIL\033[0m C3: nao achei o heredoc PY em MEASURE")
    raise SystemExit(3)
body = m.group(1)

tree = ast.parse(body)
fn = None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "measure":
        fn = node
if fn is None:
    print("  \033[31mFAIL\033[0m C3: nao achei def measure() no heredoc")
    raise SystemExit(3)

fn_src = ast.get_source_segment(body, fn)
ns = {}
RUNS = {}


def gh_json(args):
    return RUNS[args[2]]


def parse(ts):
    from datetime import datetime, timezone
    if not ts:
        return None
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def runner_class(name):
    return "Ceo"


ns.update({
    "gh_json": gh_json,
    "parse": parse,
    "runner_class": runner_class,
    "wf": {"jobs": {"validate": {"name": "Governance, health, contamination, shellcheck"}}},
})
exec(compile(fn_src, "<measure>", "exec"), ns)
measure = ns["measure"]

VALIDATE = "Governance, health, contamination, shellcheck"


def run(jobs, conclusion="success"):
    return {
        "databaseId": 111, "headSha": "0" * 40, "conclusion": conclusion,
        "startedAt": "2026-09-04T00:00:00Z", "updatedAt": "2026-09-04T00:20:00Z",
        "jobs": jobs,
    }


def job(name, conclusion="success", ts=True):
    d = {"name": name, "conclusion": conclusion}
    if ts:
        d["startedAt"] = "2026-09-04T00:00:00Z"
        d["completedAt"] = "2026-09-04T00:19:00Z"
    return d


ok = 0
bad = 0


def check(label, run_obj, want_exit, want_text=None):
    global ok, bad
    RUNS["111"] = run_obj
    try:
        got = measure("111")
    except SystemExit as exc:
        if not want_exit:
            print("  \033[31mFAIL\033[0m %s: recusou quando devia medir: %s" % (label, exc))
            bad += 1
            return
        if want_text and want_text not in str(exc):
            print("  \033[31mFAIL\033[0m %s: recusou por OUTRO motivo: %s" % (label, exc))
            bad += 1
            return
        print("  \033[32mPASS\033[0m %s" % label)
        ok += 1
        return
    if want_exit:
        print("  \033[31mFAIL\033[0m %s: NAO recusou (validate=%r)" % (label, got["validate"]))
        bad += 1
        return
    print("  \033[32mPASS\033[0m %s" % label)
    ok += 1


# Controle VERDE primeiro: sem ele os vermelhos abaixo poderiam ser vacuosos.
check("C3a: controle — run completo e verde MEDE (validate presente)",
      run([job(VALIDATE), job("hook-tests-python-matrix (3.9)")]), False)

# O plant do achado: CEO_SOTA_DISABLE=1 pula TODO job e o run conclui success.
check("C3b: VERMELHO sem a cura — todo job `skipped` num run `success`",
      run([job(VALIDATE, "skipped", ts=False),
           job("hook-tests-python-matrix (3.9)", "skipped", ts=False)]),
      True, "SKIPPED")

# Um job sem timestamp some da soma por classe em silencio.
check("C3c: job sem startedAt/completedAt é recusado (a soma sairia incompleta)",
      run([job(VALIDATE), job("hook-tests-python-matrix (3.9)", "success", ts=False)]),
      True, "sem startedAt/completedAt")

# Sem o job central a coluna da tabela seria `n/d`.
check("C3d: run sem o job `validate` é recusado (a coluna central seria n/d)",
      run([job("hook-tests-python-matrix (3.9)")]), True, "nao tem o job")

print("  __C3__ ok=%d bad=%d" % (ok, bad))
raise SystemExit(0 if bad == 0 else 1)
PY
if [ $? -eq 0 ]; then
  PASS=$(( PASS + 4 ))
else
  fail "C3: pelo menos um caso do M3 reprovou (detalhe acima)"
fi

# ===========================================================================
step "C4 — MEASURE/M0-d: sem o reconhecimento do drift, a medição PARA"
# ===========================================================================
# Achado P1 do rail, e o mais caro: os três baselines rodaram em TRÊS commits,
# e o §6 do relatório da S340 diz literalmente que eles «não são o baseline
# definitivo». Subtrair contra eles e ler a diferença como efeito da deleção
# atribui à deleção um drift de carga que ela não causou.
#
# O bloco é EXTRAÍDO do arquivo que vai ser assinado, entre a checagem da
# ressalva e o `export BASELINE_DRIFT_ACK`, e rodado com um `gh` substituto.
awk '/^grep -q .nao o baseline definitivo/{f=1} f{print} /^export BASELINE_DRIFT_ACK$/{if(f) exit}' \
  "$MEASURE" > "$WORK/m0d.sh"
if [ ! -s "$WORK/m0d.sh" ]; then
  fail "C4: não consegui extrair o bloco M0-d de $MEASURE"
else
  # `$2` = o que o `gh run view` devolve. A forma `SHA-POR-ID` faz o
  # substituto derivar um sha DIFERENTE de cada id — o caso com DRIFT, que e o
  # que o M0-d existe para pegar. Um substituto que devolvesse o mesmo sha
  # sempre cairia no ramo "baseline controlado" (C8) e estes casos mediriam
  # outra coisa.
  _m0d_case() { # $1 = valor do ACK, $2 = resposta do gh (ou SHA-POR-ID)
    mkdir -p "$WORK/bin"
    if [ "$2" = "SHA-POR-ID" ]; then
      {
        printf '#!/bin/sh\n'
        printf 'for a in "$@"; do case "$a" in [0-9]*) id="$a";; esac; done\n'
        printf 'printf "%%s|push|main" "$( printf "%%s" "${id}00000000000000000000000000000000" | cut -c1-40 )"\n'
      } > "$WORK/bin/gh"
    else
      { printf '#!/bin/sh\n'; printf 'printf %s\n' "'$2'"; } > "$WORK/bin/gh"
    fi
    chmod +x "$WORK/bin/gh"
    (
      PATH="$WORK/bin:$PATH"
      # Estas quatro sao lidas pelo BLOCO EXTRAIDO (o `.` abaixo), nao por
      # este arquivo — o shellcheck nao enxerga o consumidor e acusaria SC2034.
      # shellcheck disable=SC2034
      PUSH_BRANCH="main"
      # shellcheck disable=SC2034
      BASELINE_IDS="33709753629 33656365016 33630753334"
      # shellcheck disable=SC2034
      RUNS_TOTAL=3
      # shellcheck disable=SC2034
      REPORT_S340=".claude/plans/PLAN-186/w4/validate-deletion-measure-S340.md"
      # shellcheck disable=SC2034
      RESULT=".claude/plans/PLAN-186/w4/validate-deletion-RESULT.md"
      if [ -n "$1" ]; then CEO_W4A_BASELINE_DRIFT_ACK="$1"; export CEO_W4A_BASELINE_DRIFT_ACK; fi
      die()  { printf 'DIE: %s\n' "$*"; exit 1; }
      ok()   { printf 'ok %s\n' "$*"; }
      warn() { printf 'WARN %s\n' "$*"; }
      # shellcheck source=/dev/null
      . "$WORK/m0d.sh"
      printf 'REACHED-END ack=%s\n' "${BASELINE_DRIFT_ACK:-}"
    ) 2>&1
  }

  _sha="8efe09b8efe09b8efe09b8efe09b8efe09b8efe0"
  _out="$( _m0d_case "" "SHA-POR-ID" )"; _rc=$?
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -q 'M0-d'; then
    pass "C4a: VERMELHO sem a cura — sem CEO_W4A_BASELINE_DRIFT_ACK a medição para em M0-d"
  else
    fail "C4a: a medição seguiu sem o reconhecimento (rc=$_rc): $_out"
  fi

  _out="$( _m0d_case "I-ACCEPT" "SHA-POR-ID" )"; _rc=$?
  if [ "$_rc" -eq 0 ] && printf '%s' "$_out" | grep -q 'REACHED-END ack=I-ACCEPT'; then
    pass "C4b: controle VERDE — com o reconhecimento explícito o gate libera e carimba o ACK"
  else
    fail "C4b: com o ACK o gate não liberou (rc=$_rc): $_out"
  fi

  _out="$( _m0d_case "I-ACCEPT" "$_sha|schedule|main" )"; _rc=$?
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -q "nao 'push|main'"; then
    pass "C4c: um baseline que não é push em main é recusado mesmo COM o reconhecimento"
  else
    fail "C4c: baseline de schedule passou (rc=$_rc): $_out"
  fi

  _out="$( _m0d_case "sim" "SHA-POR-ID" )"; _rc=$?
  if [ "$_rc" -ne 0 ]; then
    pass 'C4d: o reconhecimento e a string EXATA I-ACCEPT — o valor "sim" nao serve'
  else
    fail "C4d: um valor qualquer do ACK liberou a medição: $_out"
  fi
fi

# ===========================================================================
step "C5 — LAND/G7: a remediação impressa ADICIONA contexts, nunca SUBSTITUI"
# ===========================================================================
# Achado P1 da rodada 2. O `PATCH` em `.../protection/required_status_checks`
# trata `contexts` como a configuração INTEIRA: seguir a receita antiga
# APAGARIA o `validate` e todo o resto dos required checks. A receita impressa
# é o que o Owner vai colar às 3 da manhã — ela tem de estar certa.
if grep -q "gh api -X PATCH repos/<owner>/<repo>/branches/\$PUSH_BRANCH/protection/required_status_checks \\\\" "$LAND"; then
  fail 'C5a: a receita DESTRUTIVA (PATCH em required_status_checks) ainda está impressa no LAND'
else
  pass 'C5a: a receita destrutiva (PATCH que substitui a lista inteira) não sobrevive'
fi
if grep -q 'required_status_checks/contexts' "$LAND" && grep -q 'gh api -X POST' "$LAND"; then
  pass 'C5b: a receita impressa usa o endpoint ADITIVO .../required_status_checks/contexts'
else
  fail 'C5b: o LAND não imprime o endpoint aditivo — a remediação continuaria perigosa'
fi

# ===========================================================================
step "C6 — MEASURE/M1: as 3 corridas têm de medir a MESMA árvore"
# ===========================================================================
# Achado P2 da rodada 2. Se um commit entrar entre o land e a medição sem tocar
# o `validate.yml`, a corrida 1/3 sai da árvore do land e as corridas 2 e 3
# (commits vazios sobre o HEAD novo) saem de outra — a média mistura cargas.
_extract_m1() {
  awk '/^_head_sha="\$\( git rev-parse HEAD \)"$/{f=1} f{print} /^export POST_DRIFT_COMMITS$/{if(f) exit}' \
    "$MEASURE"
}
_extract_m1 > "$WORK/m1drift.sh"
if [ ! -s "$WORK/m1drift.sh" ]; then
  fail "C6: não consegui extrair o bloco de drift pós-land de $MEASURE"
else
  _m1_case() { # $1 = ACK, $2 = LAND_SHA a fingir
    (
      # shellcheck disable=SC2034
      LAND_SHA="$2"
      # shellcheck disable=SC2034
      RESULT=".claude/plans/PLAN-186/w4/validate-deletion-RESULT.md"
      if [ -n "$1" ]; then CEO_W4A_POST_DRIFT_ACK="$1"; export CEO_W4A_POST_DRIFT_ACK; fi
      die()  { printf 'DIE: %s\n' "$*"; exit 1; }
      warn() { printf 'WARN %s\n' "$*"; }
      # shellcheck source=/dev/null
      . "$WORK/m1drift.sh"
      printf 'REACHED-END drift=%s\n' "${POST_DRIFT_COMMITS:-}"
    ) 2>&1
  }

  _head="$( git rev-parse HEAD )"
  _prev="$( git rev-parse HEAD~1 )"

  _out="$( _m1_case "" "$_head" )"; _rc=$?
  if [ "$_rc" -eq 0 ] && printf '%s' "$_out" | grep -q 'REACHED-END drift=0'; then
    pass 'C6a: controle VERDE — com HEAD == commit do land o gate não reclama'
  else
    fail "C6a: HEAD == land foi recusado (rc=$_rc): $_out"
  fi

  _out="$( _m1_case "" "$_prev" )"; _rc=$?
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -q 'nao e o commit do land'; then
    pass 'C6b: VERMELHO sem a cura — um commit entre o land e a medição PARA o MEASURE'
  else
    fail "C6b: o drift pós-land passou (rc=$_rc): $_out"
  fi

  _out="$( _m1_case "I-ACCEPT" "$_prev" )"; _rc=$?
  if [ "$_rc" -eq 0 ] && printf '%s' "$_out" | grep -q 'REACHED-END drift=1'; then
    pass 'C6c: com CEO_W4A_POST_DRIFT_ACK=I-ACCEPT o gate libera e CARIMBA o número'
  else
    fail "C6c: o reconhecimento não liberou nem carimbou (rc=$_rc): $_out"
  fi
fi

# ===========================================================================
step "C7 — apply: uma escrita que FALHA restaura tudo (garantia transacional)"
# ===========================================================================
# Achado P2 da rodada 2. Sem o `try`, uma falha ao escrever o SEGUNDO path
# deixaria o PRIMEIRO já sobrescrito, e nem as pós-condições nem o rollback
# seriam alcançados. O caso monta uma árvore descartável e torna o segundo
# arquivo NÃO-ESCREVÍVEL — o mecanismo real, não uma aparência dele.
APPLY_PY="$SCRIPT_DIR/apply-w4a-validate-deletion.py"
_tree="$WORK/tree"
mkdir -p "$_tree/.github/workflows"
cp "$ROOT/.github/workflows/validate.yml"      "$_tree/.github/workflows/validate.yml"
cp "$ROOT/.github/workflows/smoke-install.yml" "$_tree/.github/workflows/smoke-install.yml"
# O script recusa uma raiz que não seja árvore git (proteção dele, não deste
# controle) — a árvore descartável precisa de um `.git` de verdade.
git -C "$_tree" init --quiet >/dev/null 2>&1 || fail "C7: git init na árvore descartável falhou"
_v_before="$( shasum -a 256 "$_tree/.github/workflows/validate.yml" | cut -d' ' -f1 )"
_s_before="$( shasum -a 256 "$_tree/.github/workflows/smoke-install.yml" | cut -d' ' -f1 )"
# O `paths()` do script devolve os dois em ordem alfabética: smoke antes de
# validate. Travamos o SEGUNDO (validate) para que o primeiro já tenha sido
# escrito quando a falha acontecer.
chmod 444 "$_tree/.github/workflows/validate.yml"
_ap_out="$( python3 "$APPLY_PY" --root "$_tree" 2>&1 )"; _ap_rc=$?
chmod 644 "$_tree/.github/workflows/validate.yml"
_v_after="$( shasum -a 256 "$_tree/.github/workflows/validate.yml" | cut -d' ' -f1 )"
_s_after="$( shasum -a 256 "$_tree/.github/workflows/smoke-install.yml" | cut -d' ' -f1 )"
if [ "$_ap_rc" -eq 0 ]; then
  fail "C7a: a escrita num arquivo somente-leitura SUCEDEU — o caso não exercitou nada"
elif [ "$_v_after" != "$_v_before" ] || [ "$_s_after" != "$_s_before" ]; then
  fail "C7a: a árvore ficou MEIO-APLICADA após a falha (validate mudou=$([ "$_v_after" != "$_v_before" ] && echo sim || echo nao), smoke mudou=$([ "$_s_after" != "$_s_before" ] && echo sim || echo nao))"
elif printf '%s' "$_ap_out" | grep -q 'RESTAURADA'; then
  pass 'C7a: VERMELHO sem a cura — a falha de escrita restaura os DOIS arquivos e diz que restaurou'
else
  fail "C7a: os bytes voltaram, mas a recusa não foi NOMEADA: $_ap_out"
fi
# Controle verde na MESMA árvore: com os dois graváveis, aplica.
_ap_out="$( python3 "$APPLY_PY" --root "$_tree" 2>&1 )"; _ap_rc=$?
if [ "$_ap_rc" -eq 0 ] && printf '%s' "$_ap_out" | grep -q '11 edicao'; then
  pass 'C7b: controle VERDE — na mesma árvore, com os dois graváveis, as 11 edições aplicam'
else
  fail "C7b: a aplicação limpa falhou (rc=$_ap_rc): $_ap_out"
fi

# ===========================================================================
step "C8 — MEASURE/M0-d: baseline CONTROLADO (1 sha) não pede reconhecimento"
# ===========================================================================
# Achado P2 da rodada 3. A saída (a) que o próprio gate imprime é re-rodar os
# três baselines num único sha. Exigir o ACK mesmo assim — e carimbar no
# RESULT que «os três não rodaram no mesmo commit» — publicaria uma ressalva
# FALSA e tornaria a rota limpa impossível de seguir.
if [ -s "$WORK/m0d.sh" ]; then
  _out="$( _m0d_case "" "${_sha}|push|main" )"; _rc=$?
  if [ "$_rc" -eq 0 ] && printf '%s' "$_out" | grep -q 'MESMO sha'; then
    pass 'C8a: com os 3 baselines no MESMO sha o gate passa SEM o ACK (a rota limpa é seguível)'
  else
    fail "C8a: baseline controlado ainda exige reconhecimento (rc=$_rc): $_out"
  fi
  # Contraste na MESMA superfície: shas diferentes seguem exigindo o ACK. O
  # `gh` substituto devolve um sha derivado do id que recebe.
  mkdir -p "$WORK/bin"
  {
    printf '#!/bin/sh\n'
    printf 'for a in "$@"; do case "$a" in [0-9]*) id="$a";; esac; done\n'
    printf 'printf "%%s|push|main" "$( printf "%%s" "${id}00000000000000000000000000000000" | cut -c1-40 )"\n'
  } > "$WORK/bin/gh"
  chmod +x "$WORK/bin/gh"
  _out="$( (
      PATH="$WORK/bin:$PATH"
      # shellcheck disable=SC2034
      PUSH_BRANCH="main"
      # shellcheck disable=SC2034
      BASELINE_IDS="33709753629 33656365016 33630753334"
      # shellcheck disable=SC2034
      RUNS_TOTAL=3
      # shellcheck disable=SC2034
      REPORT_S340=".claude/plans/PLAN-186/w4/validate-deletion-measure-S340.md"
      # shellcheck disable=SC2034
      RESULT=".claude/plans/PLAN-186/w4/validate-deletion-RESULT.md"
      die() { printf 'DIE: %s\n' "$*"; exit 1; }
      ok() { printf 'ok %s\n' "$*"; }
      warn(){ printf 'WARN %s\n' "$*"; }
      # shellcheck source=/dev/null
      . "$WORK/m0d.sh"
      printf 'REACHED-END\n'
    ) 2>&1 )"; _rc=$?
  if [ "$_rc" -ne 0 ] && printf '%s' "$_out" | grep -q 'NAO rodaram no mesmo sha'; then
    pass 'C8b: contraste — com shas DIFERENTES o gate continua exigindo o reconhecimento'
  else
    fail "C8b: shas diferentes passaram sem ACK (rc=$_rc): $_out"
  fi
else
  fail "C8: o bloco M0-d não foi extraído (ver C4)"
fi

# ===========================================================================
step 'C9 — MEASURE/M3: baseline que nao concluiu "success" nao entra na tabela'
# ===========================================================================
# Achado P2 da rodada 3. As corridas pós-deleção passam pelo `_watch`, que
# exige `completed|success`; os baselines são ids REGISTRADOS e não passavam
# por ele — um baseline re-rodado e vermelho entraria na subtração calado.
python3 - "$MEASURE" <<'PY'
import ast
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"<<'PY'[^\n]*\n(.*?)\nPY\n", src, re.S)
body = m.group(1)
fn = [n for n in ast.parse(body).body
      if isinstance(n, ast.FunctionDef) and n.name == "measure"][0]
ns = {}
RUNS = {}


def gh_json(args):
    return RUNS[args[2]]


def parse(ts):
    from datetime import datetime, timezone
    if not ts:
        return None
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


ns.update({"gh_json": gh_json, "parse": parse, "runner_class": lambda n: "Ceo",
           "wf": {"jobs": {"validate": {"name": "V"}}}})
exec(compile(ast.get_source_segment(body, fn), "<measure>", "exec"), ns)

JOBS = [{"name": "V", "conclusion": "success",
         "startedAt": "2026-09-04T00:00:00Z", "completedAt": "2026-09-04T00:19:00Z"}]


def run(concl):
    return {"databaseId": 1, "headSha": "0" * 40, "conclusion": concl,
            "startedAt": "2026-09-04T00:00:00Z", "updatedAt": "2026-09-04T00:20:00Z",
            "jobs": JOBS}


bad = 0
RUNS["1"] = run("success")
try:
    ns["measure"]("1")
    print("  \033[32mPASS\033[0m C9a: controle VERDE — um run `success` entra na tabela")
except SystemExit as exc:
    print("  \033[31mFAIL\033[0m C9a: um run verde foi recusado: %s" % exc)
    bad += 1
for concl in ("failure", "cancelled", ""):
    RUNS["1"] = run(concl)
    try:
        ns["measure"]("1")
        print("  \033[31mFAIL\033[0m C9b(%s): um run NAO-verde entrou na tabela" % (concl or "vazio"))
        bad += 1
    except SystemExit as exc:
        if "nao 'success'" in str(exc):
            print("  \033[32mPASS\033[0m C9b(%s): recusado por nome" % (concl or "vazio"))
        else:
            print("  \033[31mFAIL\033[0m C9b(%s): recusado por OUTRO motivo: %s" % (concl, exc))
            bad += 1
raise SystemExit(0 if bad == 0 else 1)
PY
if [ $? -eq 0 ]; then
  PASS=$(( PASS + 4 ))
else
  fail "C9: pelo menos um caso reprovou (detalhe acima)"
fi

# ===========================================================================
step "C10 — LAND: material de cerimônia SUJO é recusa, e o dry-run re-emite o status"
# ===========================================================================
# Achados P1 e P2 da rodada 3. O primeiro: o oráculo diz que
# `EXPECTED-BASELINE.txt` é NÃO-canônico — verdade e irrelevante, porque o LAND
# lê esse arquivo da ÁRVORE DE TRABALHO enquanto o `Anchor-SHA` amarra o HEAD:
# editá-lo entre o SIGN e o LAND afrouxaria os limiares com a assinatura ainda
# casando. O segundo: o bash preserva o status de entrada do trap EXIT, então
# um `_land_rc=4` sem `exit` seria decorativo.
if grep -q 'MATERIALS_DIRTY' "$LAND" \
   && grep -q 'material(is) de cerimonia MODIFICADO(S) depois da assinatura' "$LAND"; then
  pass 'C10a: o G0 recusa material de cerimônia sujo por nome (não é mais "tolerado")'
else
  fail 'C10a: materiais sujos continuariam caindo no ramo tolerado do G0'
fi
# O balde novo tem de pegar o que NÃO tinha dono e deixar passar o que tem gate
# próprio. A primeira versão dele pegava TUDO — inclusive o sentinel, que o
# SIGN muta na árvore de trabalho por desenho — e derrubou 20 dos 27 casos do
# harness. O caso abaixo roda o laço EXTRAÍDO contra um `DIRTY_FILE` sintético.
awk '/^MATERIALS_DIRTY=""$/{f=1} f{print} /^done < "\$DIRTY_FILE"$/{if(f) exit}' \
  "$LAND" > "$WORK/matdirty.sh"
if [ ! -s "$WORK/matdirty.sh" ]; then
  fail "C10d: não consegui extrair o laço de materiais sujos de $LAND"
else
  _md_case() { # $1..$n = paths "sujos"
    (
      SENTINEL=".claude/plans/PLAN-186/wave-s343-w4a-approved.md"
      PATCH=".claude/plans/PLAN-186/s343-ceremony-w4a/W4A.patch"
      # Consumida pelo laço EXTRAÍDO abaixo, que o shellcheck não enxerga.
      # shellcheck disable=SC2034
      MATERIALS=(
        "$SENTINEL"
        "$PATCH"
        ".claude/plans/PLAN-186/s343-ceremony-w4a/EXPECTED-BASELINE.txt"
        ".claude/plans/PLAN-186/s343-ceremony-w4a/COMMIT-MSG-W4A.txt"
      )
      DIRTY_FILE="$WORK/dirty.txt"
      printf '%s\n' "$@" > "$DIRTY_FILE"
      # shellcheck source=/dev/null
      . "$WORK/matdirty.sh"
      printf '%s' "$MATERIALS_DIRTY"
    )
  }
  if [ -z "$( _md_case ".claude/plans/PLAN-186/wave-s343-w4a-approved.md" )" ]; then
    pass 'C10d: o sentinel sujo NÃO é pego aqui (o SIGN o muta por desenho; o .asc e o G1 o protegem)'
  else
    fail 'C10d: o sentinel caiu no balde novo — o SIGN legítimo derrubaria o LAND'
  fi
  if [ -z "$( _md_case ".claude/plans/PLAN-186/s343-ceremony-w4a/W4A.patch" )" ]; then
    pass 'C10e: o patch sujo NÃO é pego aqui — ele tem o G2, com mensagem específica'
  else
    fail 'C10e: o patch caiu no balde novo e roubaria a mensagem precisa do G2'
  fi
  if printf '%s' "$( _md_case ".claude/plans/PLAN-186/s343-ceremony-w4a/EXPECTED-BASELINE.txt" )" \
       | grep -q 'EXPECTED-BASELINE.txt'; then
    pass 'C10f: a base esperada suja É pega — é dela que saem todos os limiares do V-block'
  else
    fail 'C10f: um EXPECTED-BASELINE.txt editado após o SIGN passaria'
  fi
  if printf '%s' "$( _md_case ".claude/plans/PLAN-186/s343-ceremony-w4a/COMMIT-MSG-W4A.txt" "docs/qualquer.md" )" \
       | grep -q 'COMMIT-MSG-W4A.txt'; then
    pass 'C10g: a mensagem de commit suja É pega, e um path de fora não vira falso-positivo'
  else
    fail 'C10g: o laço não distingue material de path qualquer'
  fi
fi
if awk '/^_restore\(\) \{/{f=1} f && /^  exit "\$_land_rc"$/{ok=1} f && /^\}$/{exit} END{exit !ok}' "$LAND"; then
  pass 'C10b: o trap EXIT re-emite $_land_rc — a escalada do dry-run deixa de ser decorativa'
else
  fail 'C10b: o trap não re-emite o status; um dry-run que não restaurou sairia 0'
fi
# Controle comportamental do C10b: um trap que SÓ atribui não muda o status.
_probe_no_exit="$( bash -c 'f(){ _rc=$?; _rc=4; }; trap f EXIT; true' >/dev/null 2>&1; printf '%s' "$?" )"
_probe_exit="$( bash -c 'f(){ _rc=$?; _rc=4; exit "$_rc"; }; trap f EXIT; true' >/dev/null 2>&1; printf '%s' "$?" )"
if [ "$_probe_no_exit" = "0" ] && [ "$_probe_exit" = "4" ]; then
  pass 'C10c: medido no bash desta máquina — sem o `exit` no trap o status fica 0 (o defeito é real)'
else
  fail "C10c: a sonda do trap não reproduziu (sem exit=$_probe_no_exit, com exit=$_probe_exit)"
fi

# ===========================================================================
step "RESUMO"
# ===========================================================================
printf '\n  PASS=%d  FAIL=%d\n' "$PASS" "$FAIL"
printf '\n  O que estes controles NÃO cobrem, e por quê:\n'
printf '    - O ramo `covered` do G7 (os dois legs da matriz JÁ obrigatórios)\n'
printf '      só é exercitável contra uma proteção de branch LIGADA — hoje a\n'
printf '      API responde «Branch not protected».\n'
printf '    - As três corridas do MEASURE não são exercitáveis fora do land\n'
printf '      real: o que este arquivo prova é a RECUSA, não a medição.\n'
[ "$FAIL" -eq 0 ] || exit 1
exit 0
