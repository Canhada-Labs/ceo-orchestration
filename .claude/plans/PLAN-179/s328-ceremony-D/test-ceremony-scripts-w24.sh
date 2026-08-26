#!/usr/bin/env bash
# test-ceremony-scripts-w24.sh — harness dos scripts de cerimonia do PACOTE D.
# CEREMONY-LINT: handwritten-exception: harness de teste autorado a mao; ele
# EXERCITA scripts de cerimonia (por isso o lint o descobre), mas nao assina,
# nao aplica e nao empurra nada — toda operacao acontece num clone descartavel.
#
# O QUE ELE PROVA (cada teste com o vermelho NOMEADO, nunca "nao passou"):
#   T1  bash -n + shellcheck + ceremony-lint blocking 0 nos dois scripts
#   T2  G0 fail-closed fora do branch de push
#   T3  G2b reprova um Scope adulterado (controle POSITIVO)
#   T4  V-block reprova uma contagem que diverge do DECLARADO (controle
#       POSITIVO em CADA chave, uma de cada vez)
#   T5  V-block sem a base declarada ABORTA (nunca compara contra nada)
#   T6  sem plant: V1+V2 verdes e `--dry-run` restaura a arvore E o index
#       byte a byte (fingerprint identico ao de antes do apply)
#   T7  o apply nao muda MODO de arquivo nenhum (classe R8/S314)
#
# Uso: bash .claude/plans/PLAN-179/s328-ceremony-D/test-ceremony-scripts-w24.sh
# Sem argumentos. Exit 0 = tudo verde.
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT" || exit 1

PLAN_DIR=".claude/plans/PLAN-179"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-D"
ST="$PLAN_DIR/staged-w24"
DRAFT="$PLAN_DIR/W179-W24-approved-draft.md"
SENTINEL="$PLAN_DIR/W179-W24-approved.md"
LAND="$PLAN_DIR/OWNER-W179-W24-LAND.sh"
SIGN="$PLAN_DIR/OWNER-W179-W24-SIGN.sh"

PASS=0; FAIL=0
red()   { printf '\033[31m  FAIL\033[0m %s\n' "$*"; FAIL=$(( FAIL + 1 )); }
green() { printf '\033[32m  PASS\033[0m %s\n' "$*"; PASS=$(( PASS + 1 )); }
head2() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# O SELFTEST dos scripts so e honrado sob um diretorio descartavel. mktemp -d
# no macOS entrega /var/folders/... cujo realpath e /private/var/folders/...,
# que e uma das duas formas aceitas. Comparar REALPATH dos dois lados.
WORK="$(mktemp -d)"
WORK="$( cd "$WORK" && pwd -P )"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT
printf 'arvore de teste: %s\n' "$WORK"

# ---------------------------------------------------------------------------
head2 "T1 — sintaxe, shellcheck e ceremony-lint"
# ---------------------------------------------------------------------------
for f in "$LAND" "$SIGN" "$CEREMONY_DIR/test-ceremony-scripts-w24.sh"; do
  if bash -n "$f" 2>/dev/null; then green "bash -n: $f"; else red "bash -n reprovou: $f"; fi
done
if command -v shellcheck >/dev/null 2>&1; then
  for f in "$LAND" "$SIGN" "$CEREMONY_DIR/test-ceremony-scripts-w24.sh"; do
    if shellcheck -S warning "$f" >/dev/null 2>&1; then green "shellcheck: $f"
    else red "shellcheck reprovou: $f"; shellcheck -S warning "$f" | sed 's/^/      /'; fi
  done
else
  printf '  \033[33mSKIP\033[0m shellcheck ausente (o CI executa)\n'
fi
LINT_OUT="$WORK/lint.txt"
python3 .claude/scripts/check-ceremony-script.py >"$LINT_OUT" 2>&1
LINT_RC=$?
MY_BLOCKING="$(grep -E 'OWNER-W179-W24|test-ceremony-scripts-w24' "$LINT_OUT" | grep -c 'BLOCKING')"
if [ "$MY_BLOCKING" = "0" ]; then green "ceremony-lint: 0 BLOCKING nos scripts do pacote D (rc global=$LINT_RC)"
else red "ceremony-lint: $MY_BLOCKING BLOCKING nos scripts do pacote D"; grep -E 'OWNER-W179-W24|test-ceremony-scripts-w24' "$LINT_OUT" | grep 'BLOCKING' | sed 's/^/      /'; fi

# ---------------------------------------------------------------------------
head2 "T0 — montando o clone descartavel"
# ---------------------------------------------------------------------------
REPO="$WORK/repo"
git clone --local --quiet . "$REPO" || { red "git clone falhou"; printf '\nresumo: %s pass / %s fail\n' "$PASS" "$FAIL"; exit 1; }

# Os materiais e o pack estao UNTRACKED/modificados na arvore viva; o clone so
# tem o que esta em HEAD. Copiar e COMMITAR no clone — o LAND exige material
# rastreado, e essa exigencia e ela mesma parte do que se quer exercitar.
mkdir -p "$REPO/$CEREMONY_DIR"
rm -rf "${REPO:?}/${ST:?}"
cp -R "$ST" "$REPO/$ST"
find "$REPO/$ST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null
find "$REPO/$ST" -name '*.pyc' -delete 2>/dev/null
for f in "$LAND" "$SIGN" "$DRAFT" \
         "$CEREMONY_DIR/EXPECTED-BASELINE.txt" "$CEREMONY_DIR/COMMIT-MSG-D.txt" \
         "$CEREMONY_DIR/README-D.md" "$CEREMONY_DIR/test-ceremony-scripts-w24.sh"; do
  [ -f "$f" ] || continue
  mkdir -p "$REPO/$(dirname "$f")"
  cp "$f" "$REPO/$f"
done
# rail-round-*.md: o SIGN exige >=1 rastreado. O LAND nao os exige, mas
# copiar mantem o clone fiel ao que o Owner tera na mao.
for r in "$CEREMONY_DIR"/rail-round-*.md; do
  [ -f "$r" ] || continue
  cp "$r" "$REPO/$CEREMONY_DIR/"
done
# T0a — o MANIFEST da arvore VIVA confere? Isto e precondicao de ASSINATURA,
# nao do harness: um pack editado depois da montagem tem de ser re-montado
# antes de assinar. Reportado como assercao propria; o resto do harness segue
# num pack re-montado DENTRO do clone, para nao depender do timing de quem
# monta o pack.
if ( cd "$ROOT/$ST" && shasum -a 256 -c MANIFEST.sha256 --status ); then
  green "T0a MANIFEST da arvore viva confere (pronto para assinar)"
else
  red "T0a MANIFEST da arvore VIVA nao confere — re-rode:
        python3 $PLAN_DIR/assemble_pack.py $ST
      (o SIGN e o G2 do LAND abortam neste estado, corretamente)"
fi
# Re-monta DENTRO do clone (nunca na arvore viva) para o resto do harness
# testar os GATES, e nao o estado transitorio do pack.
( cd "$REPO" && python3 "$PLAN_DIR/assemble_pack.py" "$ST" ) >"$WORK/assemble.log" 2>&1
ASM_RC=$?
if [ "$ASM_RC" -le 1 ]; then
  green "T0b pack re-montado no clone ($(grep -c . "$REPO/$ST/MANIFEST.sha256") entradas no MANIFEST)"
else
  red "T0b assemble_pack.py falhou no clone (rc=$ASM_RC)"; tail -10 "$WORK/assemble.log" | sed 's/^/      /'
fi
# O Scope do draft e derivado do MANIFEST: se o clone re-montou com outro
# conjunto, o draft precisa acompanhar — senao o G2b acusa (corretamente) e
# todos os testes seguintes medem a divergencia em vez do que querem medir.
python3 - "$REPO/$ST" "$REPO/$DRAFT" <<'PY'
import pathlib, re, sys
st = pathlib.Path(sys.argv[1]); draft = pathlib.Path(sys.argv[2])
pm = {}
for raw in (st / "PACKMAP.txt").read_text().splitlines():
    l = raw.strip()
    if l and not l.startswith("#") and " -> " in l:
        s, d = l.split(" -> ", 1); pm[s.strip()] = d.strip()
paths = []
for raw in (st / "MANIFEST.sha256").read_text().splitlines():
    m = re.match(r"^[0-9a-f]{64}  (.+)$", raw)
    if m:
        p = m.group(1); paths.append(pm.get(p, p))
block = "\n".join(sorted(paths))
text = draft.read_text(encoding="utf-8")
new, n = re.subn(r"(## Scope\n\n<!--.*?-->\n```\n).*?(\n```)",
                 lambda m: m.group(1) + block + m.group(2), text, count=1, flags=re.S)
assert n == 1, "bloco Scope nao encontrado no draft"
draft.write_text(new, encoding="utf-8")
print("scope do draft re-derivado: %d paths" % len(paths))
PY
(
  cd "$REPO" || exit 1
  git add -- "$ST" "$LAND" "$SIGN" "$DRAFT" "$CEREMONY_DIR" >/dev/null 2>&1
  git -c user.email=harness@local -c user.name=harness commit -q -m "harness: materiais do pacote D" >/dev/null 2>&1
) || { red "commit dos materiais no clone falhou"; printf '\nresumo: %s pass / %s fail\n' "$PASS" "$FAIL"; exit 1; }
CLONE_HEAD="$( cd "$REPO" && git rev-parse HEAD )"
green "clone montado e materiais commitados (HEAD $CLONE_HEAD)"

# Sentinel sintetico: draft + campos preenchidos + .asc falso. O LAND sob
# SELFTEST pula a verificacao GPG mas AINDA exige anchor == HEAD, entao o
# anchor tem de ser o HEAD do clone.
_make_sentinel() {  # $1 = repo dir
  python3 - "$1/$DRAFT" "$1/$SENTINEL" "$( cd "$1" && git rev-parse HEAD )" <<'PY'
import re, sys
src, dst, head = sys.argv[1:4]
s = open(src, encoding="utf-8").read()
s = s.replace("Anchor-SHA: TO-FILL-AT-SIGN", "Anchor-SHA: %s" % head, 1)
s = s.replace("Data: TO-FILL-AT-SIGN", "Data: 2026-08-25", 1)
s = s.replace("Approved-By: @Canhada-Labs TO-FILL-AT-SIGN",
              "Approved-By: @Canhada-Labs HARNESS0000000000000000000000000000000000", 1)
open(dst, "w", encoding="utf-8").write(s)
PY
  printf 'HARNESS-NOT-A-SIGNATURE\n' > "$1/$SENTINEL.asc"
}
_make_sentinel "$REPO"
green "sentinel sintetico gerado (sem GPG; .asc e um placeholder)"

# Commita o estado atual do clone e REGENERA o sentinel: o G3 exige
# anchor == HEAD, e qualquer commit move o HEAD. Sem isto, plantar um valor
# num material versionado (T4) faria o G0 abortar por "modificacao RASTREADA"
# ANTES do V-block — que foi exatamente o que a primeira corrida do harness
# mediu, e o G0 estava certo.
_commit_and_reanchor() {  # $1 = mensagem; demais args = paths extras a stagear
  # `git add -u` (sem pathspec) stageia modificacoes E delecoes de arquivos
  # JA rastreados, que e exatamente o que os plants produzem. Nada de `-A`:
  # ele varreria untracked (o sentinel sintetico, entre outros) e e BLOCKING
  # no ceremony-lint (R4) alem de proibido pelo CLAUDE.md §4.
  #
  # O `-u` sozinho NAO basta e a razao e o T5: depois que a DELECAO da base
  # declarada e commitada, o arquivo restaurado volta como UNTRACKED, e `-u`
  # so enxerga o que ja e rastreado. Sem o add explicito abaixo, o material
  # ficava fora do indice e os testes seguintes morriam no G0 com
  # "material NAO commitado" — o gate estava certo, o instrumento e que
  # tinha deixado a arvore num estado que ele mesmo criou.
  local _msg="$1"; shift
  ( cd "$REPO" \
      && git add -u >/dev/null 2>&1 \
      && git add -- "$CEREMONY_DIR/EXPECTED-BASELINE.txt" >/dev/null 2>&1 \
      && { [ "$#" -eq 0 ] || git add -- "$@" >/dev/null 2>&1; } \
      && git -c user.email=harness@local -c user.name=harness \
             commit -q --allow-empty -m "$_msg" >/dev/null 2>&1 )
  _make_sentinel "$REPO"
}

# Corredor unico para rodar o LAND no clone. Ecoa o log em $WORK/<tag>.log.
# NO_RESTORE_FLAG (variavel de ambiente do harness) e repassado quando o teste
# precisa INSPECIONAR a arvore aplicada.
NO_RESTORE_FLAG=0
_run_land() {  # $1 = tag  $2 = stop-after  resto: argv extra do land
  local tag="$1" stop="$2"; shift 2
  ( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 CEREMONY_SELFTEST_STOP_AFTER="$stop" \
      CEREMONY_SELFTEST_NO_RESTORE="$NO_RESTORE_FLAG" \
      PYTHONDONTWRITEBYTECODE=1 bash "$LAND" "$@" ) >"$WORK/$tag.log" 2>&1
  printf '%s' "$?"
}
_expect_abort() {  # $1 tag  $2 padrao esperado no log  $3 rotulo
  local tag="$1" pat="$2" label="$3"
  if grep -qE "$pat" "$WORK/$tag.log"; then green "$label — vermelho NOMEADO"
  else
    red "$label — abortou, mas sem a mensagem esperada (/$pat/)"
    tail -12 "$WORK/$tag.log" | sed 's/^/      /'
  fi
}
_git_fp() {  # fingerprint da arvore do clone (mesma forma do _restore do LAND)
  ( cd "$REPO" && { git status --porcelain=v1 --untracked-files=all
                    printf -- '--diff--\n'; git diff HEAD
                    printf -- '--index--\n'; git diff --cached --name-status; } \
    | shasum -a 256 | awk '{print $1}' )
}

# ---------------------------------------------------------------------------
head2 "T2 — G0 fail-closed fora do branch de push"
# ---------------------------------------------------------------------------
( cd "$REPO" && git checkout -q -b nao-main ) >/dev/null 2>&1
RC="$(_run_land t2 G3)"
if [ "$RC" != "0" ]; then _expect_abort t2 "HEAD esta em 'nao-main'|nao em 'main'" "T2 G0 branch guard"
else red "T2 G0 branch guard — o land NAO abortou fora do main (rc=0)"; fi
( cd "$REPO" && git checkout -q main ) >/dev/null 2>&1

# ---------------------------------------------------------------------------
head2 "T3 — G2b reprova Scope adulterado (controle POSITIVO)"
# ---------------------------------------------------------------------------
# (a) controle NEGATIVO primeiro: o Scope intacto passa o G2b.
RC="$(_run_land t3a G3)"
if [ "$RC" = "0" ] && grep -q 'escopo identico ao manifesto' "$WORK/t3a.log"; then
  green "T3a Scope intacto — G2b passa (controle negativo)"
else
  red "T3a Scope intacto — G2b NAO passou (rc=$RC)"; tail -15 "$WORK/t3a.log" | sed 's/^/      /'
fi
# (b) PLANT: remove um path do bloco Scope do sentinel.
cp "$REPO/$SENTINEL" "$WORK/sentinel.orig"
python3 - "$REPO/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().splitlines(True)
out, dropped = [], False
for ln in lines:
    if not dropped and ln.strip() == ".claude/data/audit-registry.golden.txt":
        dropped = True
        continue
    out.append(ln)
assert dropped, "plant falhou: path alvo nao estava no Scope"
open(p, "w", encoding="utf-8").write("".join(out))
PY
RC="$(_run_land t3b G3)"
if [ "$RC" != "0" ]; then _expect_abort t3b "escopo do sentinel != manifesto" "T3b Scope adulterado"
else red "T3b Scope adulterado — o land NAO abortou (rc=0): o G2b esta cego"; fi
cp "$WORK/sentinel.orig" "$REPO/$SENTINEL"

# ---------------------------------------------------------------------------
head2 "T4 — V-block reprova contagem divergente do DECLARADO (uma chave por vez)"
# ---------------------------------------------------------------------------
BASE_IN_CLONE="$REPO/$CEREMONY_DIR/EXPECTED-BASELINE.txt"
cp "$BASE_IN_CLONE" "$WORK/expected.orig"
_plant_key() {  # $1 chave  $2 valor absurdo
  python3 - "$BASE_IN_CLONE" "$1" "$2" <<'PY'
import re, sys
p, key, val = sys.argv[1:4]
s = open(p, encoding="utf-8").read()
new, n = re.subn(r"^%s=.*$" % re.escape(key), "%s=%s" % (key, val), s, count=1, flags=re.M)
assert n == 1, "chave %s nao encontrada" % key
open(p, "w", encoding="utf-8").write(new)
PY
}
for pair in "EXPECTED_KNOWN_ACTIONS 999" \
            "EXPECTED_GOLDEN_LINES 4242" \
            "EXPECTED_ADRS 9999" \
            "EXPECTED_LIB 4444"; do
  key="${pair%% *}"; val="${pair##* }"
  cp "$WORK/expected.orig" "$BASE_IN_CLONE"
  _plant_key "$key" "$val"
  # O plant tem de estar COMMITADO: o G0 aborta com a arvore suja (e faz bem).
  _commit_and_reanchor "harness: plant $key=$val"
  RC="$(_run_land "t4_$key" V2)"
  if [ "$RC" != "0" ]; then
    _expect_abort "t4_$key" "observado .*, DECLARADO $val" "T4 $key=$val"
  else
    red "T4 $key=$val — o V-block NAO abortou (rc=0): a chave nao esta sendo comparada"
  fi
done
cp "$WORK/expected.orig" "$BASE_IN_CLONE"
_commit_and_reanchor "harness: restaura a base declarada"

# ---------------------------------------------------------------------------
head2 "T5 — sem base declarada, o land ABORTA (nunca compara contra nada)"
# ---------------------------------------------------------------------------
mv "$BASE_IN_CLONE" "$WORK/expected.hidden"
_commit_and_reanchor "harness: remove a base declarada"
RC="$(_run_land t5 V2)"
if [ "$RC" != "0" ]; then _expect_abort t5 "base declarada AUSENTE" "T5 base declarada ausente"
else red "T5 — o land rodou SEM base declarada (rc=0)"; fi
mv "$WORK/expected.hidden" "$BASE_IN_CLONE"
_commit_and_reanchor "harness: devolve a base declarada"

# ---------------------------------------------------------------------------
head2 "T6 — sem plant: V1+V2 verdes e a arvore volta byte a byte"
# ---------------------------------------------------------------------------
FP_ANTES="$(_git_fp)"
RC="$(_run_land t6 V2)"
FP_DEPOIS="$(_git_fp)"
if [ "$RC" = "0" ]; then green "T6 sem plant — V1 e V2 verdes (rc=0)"
else red "T6 sem plant — o land abortou (rc=$RC)"; tail -20 "$WORK/t6.log" | sed 's/^/      /'; fi
if grep -q 'restaurados byte a byte' "$WORK/t6.log"; then green "T6 restauracao — o proprio land declarou fingerprint identico"
else red "T6 restauracao — o land NAO declarou restauracao byte a byte"; fi
if [ "$FP_ANTES" = "$FP_DEPOIS" ]; then green "T6 restauracao — fingerprint externo identico ($FP_ANTES)"
else
  red "T6 restauracao — a arvore do clone MUDOU: $FP_ANTES -> $FP_DEPOIS"
  ( cd "$REPO" && git status --short | head -20 ) | sed 's/^/      /'
fi
# Os 5 destinos NOVOS nao podem ter sobrado no disco.
LEFT=0
for n in .claude/hooks/check_ledger_checkpoint.py \
         .claude/hooks/_lib/ledger_provenance.py \
         .claude/hooks/tests/test_check_ledger_checkpoint.py \
         .claude/hooks/tests/test_ledger_provenance.py \
         .claude/adr/ADR-195-work-boundary-persistence.md; do
  [ -e "$REPO/$n" ] && { printf '      sobrou: %s\n' "$n"; LEFT=$(( LEFT + 1 )); }
done
if [ "$LEFT" = "0" ]; then green "T6 restauracao — os 5 destinos NOVOS foram removidos"
else red "T6 restauracao — $LEFT destino(s) novo(s) sobrou/sobraram no disco"; fi

# ---------------------------------------------------------------------------
head2 "T7 — o apply nao muda MODO de arquivo (classe R8/S314)"
# ---------------------------------------------------------------------------
# `_lib/audit_emit.py` e 100644 no indice e `check_bash_safety.py` e 100755.
# O molde anterior fazia `chmod +x` com o glob `.claude/hooks/*.py`, e em
# `case` do bash o `*` ATRAVESSA `/` — aquilo tornava audit_emit.py 755.
MODE_BEFORE="$( cd "$REPO" && git ls-files -s -- .claude/hooks/_lib/audit_emit.py | awk '{print $1}' )"
# MANTER o apply: sem isto o trap do land restaura antes de qualquer stat, e o
# teste mede uma arvore ja limpa — foi o que a primeira corrida do harness fez
# (o hook novo saiu como '???' porque tinha acabado de ser removido).
NO_RESTORE_FLAG=1
RC="$(_run_land t7 G5)"
NO_RESTORE_FLAG=0
MODE_DISK="$( stat -f '%Lp' "$REPO/.claude/hooks/_lib/audit_emit.py" 2>/dev/null || printf '???' )"
NEW_HOOK_MODE="$( stat -f '%Lp' "$REPO/.claude/hooks/check_ledger_checkpoint.py" 2>/dev/null || printf '???' )"
if [ "$RC" = "0" ]; then green "T7 apply — G5 concluiu (rc=0)"
else red "T7 apply — G5 abortou (rc=$RC)"; tail -15 "$WORK/t7.log" | sed 's/^/      /'; fi
if [ "$MODE_BEFORE" = "100644" ] && [ "$MODE_DISK" = "644" ]; then
  green "T7 modo — _lib/audit_emit.py continua 644 depois do apply"
else
  red "T7 modo — _lib/audit_emit.py: indice=$MODE_BEFORE disco-pos-apply=$MODE_DISK (esperado 100644/644)"
fi
if [ "$NEW_HOOK_MODE" = "755" ]; then green "T7 modo — o hook NOVO nasceu 755 (como os 59 hooks vivos)"
else red "T7 modo — check_ledger_checkpoint.py nasceu $NEW_HOOK_MODE (esperado 755)"; fi

# O T7 sai com o pack APLICADO de proposito (e o unico jeito de medir modos).
# Desfazer isso e responsabilidade do harness: o T8 roda o SIGN, e o SIGN
# aborta — corretamente — se um destino NOVO do pack ja existe na arvore.
# Sem esta limpeza o T8 mediria o gate errado.
head2 "T7-limpeza — desfazendo o apply que o T7 manteve"
python3 - "$REPO" "$ST" <<'PY'
import pathlib, re, subprocess, sys
repo = pathlib.Path(sys.argv[1]); st = repo / sys.argv[2]
pm = {}
for raw in (st / "PACKMAP.txt").read_text().splitlines():
    l = raw.strip()
    if l and not l.startswith("#") and " -> " in l:
        s, d = l.split(" -> ", 1); pm[s.strip()] = d.strip()
new, mod = [], []
for raw in (st / "MANIFEST.sha256").read_text().splitlines():
    m = re.match(r"^[0-9a-f]{64}  (.+)$", raw)
    if not m:
        continue
    rel = pm.get(m.group(1), m.group(1))
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", rel],
                             cwd=repo, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL).returncode == 0
    (mod if tracked else new).append(rel)
for rel in new:
    p = repo / rel
    if p.exists():
        p.unlink()
if mod:
    subprocess.run(["git", "checkout", "--"] + mod, cwd=repo,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("  desfeito: %d novo(s) removido(s), %d modificado(s) restaurado(s)"
      % (len(new), len(mod)))
PY
if [ -z "$( cd "$REPO" && git status --porcelain --untracked-files=all \
            -- .claude/hooks .claude/adr .claude/data SPEC templates docs npm \
               CLAUDE.md README.md README.pt-BR.md INSTALL.md )" ]; then
  green "T7-limpeza — a arvore do clone voltou ao estado pre-apply"
else
  red "T7-limpeza — sobrou estado aplicado; o T8 vai medir o gate errado"
  ( cd "$REPO" && git status --short | head -10 ) | sed 's/^/      /'
fi

# ---------------------------------------------------------------------------
head2 "T8 — o SIGN exige APPROVE na ULTIMA rodada de rail (controle POSITIVO)"
# ---------------------------------------------------------------------------
# Contar registros de rail responde "houve rail?"; o contrato pergunta "o rail
# FECHOU?". O gate antigo contava, e por isso deixava assinar um pacote cuja
# unica rodada registrada era REJECT (pair-rail round 2, P1).
_run_sign() {  # $1 = tag
  ( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 PYTHONDONTWRITEBYTECODE=1 \
      bash "$SIGN" </dev/null ) >"$WORK/$1.log" 2>&1
  printf '%s' "$?"
}
# (a) PLANT: a ultima (e unica) rodada e REJECT -> tem de ABORTAR.
RC="$(_run_sign t8a)"
if [ "$RC" != "0" ]; then
  _expect_abort t8a "fechou em REJECT" "T8a ultima rodada REJECT"
else
  red "T8a — o SIGN assinou com a ultima rodada em REJECT (rc=0): o gate esta cego"
fi
# (b) uma rodada POSTERIOR com APPROVE -> o gate de veredito deixa passar.
cat > "$REPO/$CEREMONY_DIR/rail-round-99.md" <<'EOF'
# rodada sintetica do harness — NAO e um registro real de rail
Rail-Verdict: APPROVE
EOF
_commit_and_reanchor "harness: rodada 99 sintetica (APPROVE)" "$CEREMONY_DIR/rail-round-99.md"
RC="$(_run_sign t8b)"
if grep -q 'rail-round-99.md) = APPROVE' "$WORK/t8b.log"; then
  green "T8b rodada mais NOVA com APPROVE — o gate de veredito libera"
else
  red "T8b — o gate nao reconheceu a rodada 99 como a ultima (ordenacao por NUMERO?)"
  tail -12 "$WORK/t8b.log" | sed 's/^/      /'
fi
# (c) campo ausente -> ABORT (fail-closed em input, nunca "assume que passou").
printf '# sem veredito declarado\n' > "$REPO/$CEREMONY_DIR/rail-round-99.md"
_commit_and_reanchor "harness: rodada 99 sem veredito" "$CEREMONY_DIR/rail-round-99.md"
RC="$(_run_sign t8c)"
if [ "$RC" != "0" ]; then
  _expect_abort t8c "nao declara veredito" "T8c veredito ausente"
else
  red "T8c — o SIGN assinou com a ultima rodada SEM veredito declarado (rc=0)"
fi
rm -f "$REPO/$CEREMONY_DIR/rail-round-99.md"
_commit_and_reanchor "harness: remove a rodada sintetica"

printf '\n\033[1mRESUMO\033[0m  %s pass / %s fail   (logs em %s)\n' "$PASS" "$FAIL" "$WORK"
if [ "$FAIL" -gt 0 ]; then
  printf '\033[31mHARNESS VERMELHO\033[0m — os logs ficam onde a mensagem acima indica ate este processo sair.\n'
  cp -R "$WORK" "${TMPDIR:-/tmp}/w24-harness-fail.$$" 2>/dev/null && \
    printf '  copia dos logs: %s\n' "${TMPDIR:-/tmp}/w24-harness-fail.$$"
  exit 1
fi
printf '\033[32mHARNESS VERDE\033[0m\n'
exit 0
