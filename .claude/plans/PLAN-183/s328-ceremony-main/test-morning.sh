#!/usr/bin/env bash
# test-morning.sh — auto-teste do OWNER-S328-MORNING.sh.
# CEREMONY-LINT: handwritten-exception: harness de teste do orquestrador da manhã; roda tudo num clone descartável, não assina nem empurra nada
#
# TUDO roda num CLONE DESCARTÁVEL sob o scratchpad. A árvore viva nunca é
# tocada — e o clone tem o remote `origin` REMOVIDO logo no início, porque
# `git clone --local` aponta origin para o repo vivo e um push acidental
# subiria daqui.
#
# OS PACOTES SÃO STUBS. O que este harness prova é o comportamento do
# ORQUESTRADOR — ordem, detecção de ausência, dependências, derivação de
# flags, parada no primeiro vermelho, idempotência. Ele NÃO prova que os
# SIGN/LAND reais funcionam: cada pacote tem o próprio harness para isso
# (`test-ceremony-scripts-<P>.sh`). Limite declarado, não descuido.
#
# CENÁRIOS
#   S1  todos os pacotes presentes ...... ordem B→A→C→D, nada pulado, rc 0
#   S2  pacote B ausente ................ avisa que o CI segue vermelho,
#                                         C pulado nomeando B, rc 7
#   S3  pacote A ausente ................ C pulado nomeando A, rc 7
#   S4  pacote D ausente ................ pula avisando, os outros rodam, rc 7
#   S5  SIGN do B devolvendo 1 .......... para NO PRIMEIRO vermelho, rc 12,
#                                         imprime `--from B`, A/C/D não rodam
#   S6  caminho feliz de verdade ........ 4 pacotes landados na ordem, rc 0,
#                                         log em s328-ceremony-main/
#   S7  segunda passada sobre S6 ........ idempotente: reconhece "já landado"
#
# Uso:  bash .claude/plans/PLAN-183/s328-ceremony-main/test-morning.sh
set -uo pipefail   # NÃO -e: as falhas são CLASSIFICADAS, não fatais.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
LIVE="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
MORNING_REL=".claude/plans/PLAN-183/OWNER-S328-MORNING.sh"

SCRATCH="${MORNING_SELFTEST_SCRATCH:-/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/a78dbd00-249c-447b-b606-677f5fd39e46/scratchpad/morning-selftest}"
case "$SCRATCH" in
  /private/tmp/claude-501/*/scratchpad/*|/private/var/folders/*|/tmp/*) : ;;
  *) printf 'ABORT: SCRATCH fora de um diretório descartável: %s\n' "$SCRATCH" >&2; exit 2 ;;
esac

PASS=0; FAIL=0
_pass() { PASS=$(( PASS + 1 )); printf '    \033[32mPASS\033[0m %s\n' "$*"; }
_fail() { FAIL=$(( FAIL + 1 )); printf '    \033[31mFAIL\033[0m %s\n' "$*"; }
_head() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# Contagem sobre ARQUIVO (nunca `grep -q` no fim de um pipe: sob pipefail o
# SIGPIPE mata o produtor e o rc vira 141 — lição do repo).
_count_in() {  # <arquivo> <literal>
  local n
  n="$( grep -c -F -- "$2" "$1" 2>/dev/null )"
  case "${n:-0}" in ''|*[!0-9]*) n=0 ;; esac
  printf '%s' "$n"
}
_assert_has() {  # <arquivo> <literal> <descrição>
  if [ "$( _count_in "$1" "$2" )" -gt 0 ]; then _pass "$3"; else
    _fail "$3 — não achei no output: $2"
  fi
}
_assert_hasnt() {  # <arquivo> <literal> <descrição>
  if [ "$( _count_in "$1" "$2" )" -eq 0 ]; then _pass "$3"; else
    _fail "$3 — apareceu no output e não devia: $2"
  fi
}
_assert_rc() {  # <esperado> <obtido> <descrição>
  if [ "$1" = "$2" ]; then _pass "$3 (rc=$2)"; else _fail "$3 — esperava rc=$1, veio rc=$2"; fi
}
_assert_eq() {  # <esperado> <obtido> <descrição>
  if [ "$1" = "$2" ]; then _pass "$3"; else _fail "$3 — esperava [$1], veio [$2]"; fi
}
# `cp` segue symlink e grava FORA do destino pretendido (classe do PLAN-185):
# todo cp/mv deste harness passa por aqui.
_safe_cp() {
  if [ -L "$2" ]; then _fail "destino é SYMLINK, recusado: $2"; return 1; fi
  cp "$1" "$2"
}

# ===========================================================================
_head "0 — clone-molde com os 4 pacotes STUB"
# ===========================================================================
# Trava: duas execuções simultâneas compartilhariam $SCRATCH e uma apagaria o
# molde da outra no meio de um `cp -R` — falha que parece defeito do MORNING e
# não é. `mkdir` é atômico; serve de lock.
LOCK="$SCRATCH.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  printf 'ABORT: já existe uma execução deste harness (trava: %s).\n' "$LOCK" >&2
  printf '  Se tiver certeza de que nenhuma está rodando:  rmdir %s\n' "$LOCK" >&2
  exit 2
fi
trap 'rmdir "$LOCK" 2>/dev/null || printf ""' EXIT

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
TPL="$SCRATCH/template"
git clone --quiet --local "$LIVE" "$TPL" || { printf 'clone falhou\n' >&2; exit 2; }
git -C "$TPL" remote remove origin        # NUNCA empurrar para o repo vivo
git -C "$TPL" config user.email "morning-selftest@example.invalid"
git -C "$TPL" config user.name  "morning selftest"
printf '  clone-molde: %s (origin removido)\n' "$TPL"

# O MORNING vive no repo; o clone traz a versão COMMITADA. Enquanto ele for
# untracked (ou tiver mudado), o clone precisa da versão VIVA.
mkdir -p "$TPL/$( dirname "$MORNING_REL" )"
_safe_cp "$LIVE/$MORNING_REL" "$TPL/$MORNING_REL" || exit 2

# --- moldes dos stubs ------------------------------------------------------
TMPL_DIR="$SCRATCH/tmpl"; mkdir -p "$TMPL_DIR"

cat > "$TMPL_DIR/sign-patch.tmpl" <<'STUB'
#!/usr/bin/env bash
# STUB SIGN do pacote @P@ — gerado por test-morning.sh.
# CEREMONY-LINT: handwritten-exception: stub de teste; NAO assina nada.
set -uo pipefail
SD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SD" && git rev-parse --show-toplevel )"
cd "$ROOT"
PLAN_DIR="@PLANDIR@"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-@P@"
SENTINEL="$PLAN_DIR/wave-s328-@P@-approved.md"
PATCH="$CEREMONY_DIR/@P@.patch"
printf 'STUB-SIGN @P@\n'
printf 'SIGN-@P@\n' >> "${MORNING_TEST_ORDER_FILE:-/dev/null}"
RC="${STUB_SIGN_RC_@P@:-0}"
if [ "${STUB_SIGN_PINENTRY_@P@:-0}" = "1" ]; then
  printf 'gpg: signing failed: No pinentry\n' >&2
  exit 1
fi
if [ "$RC" != "0" ]; then
  # SEM a palavra que dispara a retentativa do MORNING: este e o vermelho
  # comum, e a retentativa tem cenario proprio (S5b).
  printf 'gpg: falha simulada pelo harness\n' >&2
  exit "$RC"
fi
printf 'STUB-NOT-A-SIGNATURE\n' > "$SENTINEL.asc"
printf 'PRONTO\n'
STUB

cat > "$TMPL_DIR/sign-manifest.tmpl" <<'STUB'
#!/usr/bin/env bash
# STUB SIGN do pacote @P@ (manifesto) — gerado por test-morning.sh.
# CEREMONY-LINT: handwritten-exception: stub de teste; NAO assina nada.
set -uo pipefail
SD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SD" && git rev-parse --show-toplevel )"
cd "$ROOT"
PLAN_DIR="@PLANDIR@"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-@P@"
DRAFT="$PLAN_DIR/@SENTBASE@-draft.md"
SENTINEL="$PLAN_DIR/@SENTBASE@.md"
printf 'STUB-SIGN @P@\n'
printf 'SIGN-@P@\n' >> "${MORNING_TEST_ORDER_FILE:-/dev/null}"
RC="${STUB_SIGN_RC_@P@:-0}"
if [ "$RC" != "0" ]; then
  printf 'gpg: falha simulada pelo harness\n' >&2
  exit "$RC"
fi
if [ -L "$SENTINEL" ]; then
  printf 'STUB-SIGN @P@: %s e um SYMLINK — recuso escrever atraves dele\n' "$SENTINEL" >&2
  exit 1
fi
cp "$DRAFT" "$SENTINEL"
printf 'STUB-NOT-A-SIGNATURE\n' > "$SENTINEL.asc"
printf 'PRONTO\n'
STUB

cat > "$TMPL_DIR/land-patch.tmpl" <<'STUB'
#!/usr/bin/env bash
# STUB LAND do pacote @P@ — gerado por test-morning.sh.
# CEREMONY-LINT: handwritten-exception: stub de teste; commita num clone descartavel, nunca empurra.
#
# Uso:
#   bash @PLANDIR@/OWNER-S328-@P@-LAND.sh --dry-run @EXTRA@
#   bash @PLANDIR@/OWNER-S328-@P@-LAND.sh @EXTRA@
set -uo pipefail
SD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SD" && git rev-parse --show-toplevel )"
cd "$ROOT"
PLAN_DIR="@PLANDIR@"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-@P@"
SENTINEL="$PLAN_DIR/wave-s328-@P@-approved.md"
PATCH="$CEREMONY_DIR/@P@.patch"
APPLIED="$CEREMONY_DIR/APPLIED-@P@.txt"
NEEDS_OWN="@NEEDSOWN@"
DRY=0
OWN=""
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --ownership-e2e=run|--ownership-e2e=defer) OWN="$a" ;;
    *) printf 'STUB-LAND @P@: argumento desconhecido: %s\n' "$a" >&2; exit 2 ;;
  esac
done
if [ "$NEEDS_OWN" = "1" ] && [ -z "$OWN" ]; then
  printf 'STUB-LAND @P@: --ownership-e2e e OBRIGATORIO e nao tem default.\n' >&2
  exit 1
fi
printf 'STUB-LAND @P@ dry=%s own=%s\n' "$DRY" "${OWN:-<nenhum>}"
printf 'LAND-@P@-dry%s\n' "$DRY" >> "${MORNING_TEST_ORDER_FILE:-/dev/null}"
RC="${STUB_LAND_RC_@P@:-0}"
if [ "$RC" != "0" ]; then
  printf 'STUB-LAND @P@: falha simulada pelo harness\n' >&2
  exit "$RC"
fi
if [ "$DRY" = "1" ]; then
  printf 'DRY-RUN: arvore e index restaurados byte a byte\n'
  exit 0
fi
git apply "$PATCH" || { printf 'STUB-LAND @P@: o patch nao aplicou\n' >&2; exit 1; }
git add -- "$APPLIED"
[ -f "$SENTINEL" ]      && git add -- "$SENTINEL"
[ -f "$SENTINEL.asc" ]  && git add -- "$SENTINEL.asc"
git commit -q -F "$CEREMONY_DIR/COMMIT-MSG-@P@.txt" || { printf 'STUB-LAND @P@: commit falhou\n' >&2; exit 1; }
printf 'LAND OK — %s\n' "$( git rev-parse --short HEAD )"
STUB

cat > "$TMPL_DIR/land-manifest.tmpl" <<'STUB'
#!/usr/bin/env bash
# STUB LAND do pacote @P@ (manifesto) — gerado por test-morning.sh.
# CEREMONY-LINT: handwritten-exception: stub de teste; commita num clone descartavel, nunca empurra.
#
# Uso:
#   bash @PLANDIR@/OWNER-W179-W24-LAND.sh --dry-run
#   bash @PLANDIR@/OWNER-W179-W24-LAND.sh
set -uo pipefail
SD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SD" && git rev-parse --show-toplevel )"
cd "$ROOT"
PLAN_DIR="@PLANDIR@"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-@P@"
SENTINEL="$PLAN_DIR/@SENTBASE@.md"
APPLIED="$CEREMONY_DIR/APPLIED-@P@.txt"
DRY=0
case "${1:-}" in
  --dry-run) DRY=1 ;;
  "")        DRY=0 ;;
  *) printf 'uso: bash %s [--dry-run]\n' "$0" >&2; exit 2 ;;
esac
printf 'STUB-LAND @P@ dry=%s\n' "$DRY"
printf 'LAND-@P@-dry%s\n' "$DRY" >> "${MORNING_TEST_ORDER_FILE:-/dev/null}"
RC="${STUB_LAND_RC_@P@:-0}"
if [ "$RC" != "0" ]; then
  printf 'STUB-LAND @P@: falha simulada pelo harness\n' >&2
  exit "$RC"
fi
if [ "$DRY" = "1" ]; then
  printf 'DRY-RUN: arvore e index restaurados byte a byte\n'
  exit 0
fi
printf 'pacote @P@ aplicado\n' > "$APPLIED"
git add -- "$APPLIED"
[ -f "$SENTINEL" ]     && git add -- "$SENTINEL"
[ -f "$SENTINEL.asc" ] && git add -- "$SENTINEL.asc"
git commit -q -F "$CEREMONY_DIR/COMMIT-MSG-@P@.txt" || { printf 'STUB-LAND @P@: commit falhou\n' >&2; exit 1; }
printf 'LAND OK — %s\n' "$( git rev-parse --short HEAD )"
STUB

cat > "$TMPL_DIR/finalize.tmpl" <<'STUB'
#!/usr/bin/env bash
# STUB finalize do pacote @P@ — gerado por test-morning.sh.
# CEREMONY-LINT: handwritten-exception: stub de teste; nao re-baseia nada de verdade.
set -uo pipefail
printf 'STUB-FINALIZE @P@\n'
printf 'FINALIZE-@P@\n' >> "${MORNING_TEST_ORDER_FILE:-/dev/null}"
RC="${STUB_FINALIZE_RC_@P@:-0}"
[ "$RC" = "0" ] || { printf 'STUB-FINALIZE @P@: o patch NAO re-aplica (falha simulada)\n' >&2; exit "$RC"; }
printf 'PRONTO (no-op)\n'
STUB

_render() {  # <molde> <destino> <P> <PLANDIR> <EXTRA> <NEEDSOWN> <SENTBASE>
  sed -e "s|@P@|$3|g" -e "s|@PLANDIR@|$4|g" -e "s|@EXTRA@|$5|g" \
      -e "s|@NEEDSOWN@|$6|g" -e "s|@SENTBASE@|$7|g" "$1" > "$2"
}

# --- monta um pacote no molde ---------------------------------------------
_mk_patch_pkg() {  # <P> <PLANDIR> <EXTRA-do-LAND> <NEEDSOWN>
  local p="$1" plan="$2" extra="$3" needs="$4"
  local cer="$plan/s328-ceremony-$p" abs="$TPL/$plan/s328-ceremony-$p"
  mkdir -p "$abs"
  _render "$TMPL_DIR/sign-patch.tmpl" "$TPL/$plan/OWNER-S328-$p-SIGN.sh" "$p" "$plan" "$extra" "$needs" ""
  _render "$TMPL_DIR/land-patch.tmpl" "$TPL/$plan/OWNER-S328-$p-LAND.sh" "$p" "$plan" "$extra" "$needs" ""
  _render "$TMPL_DIR/finalize.tmpl"   "$abs/finalize-$p.sh"              "$p" "$plan" "$extra" "$needs" ""
  printf 'ceremony(s328-%s): stub do pacote %s aplicado pelo harness\n' "$p" "$p" > "$abs/COMMIT-MSG-$p.txt"
  printf '# sentinel STUB do pacote %s\n\nApproved-By: TO-FILL\n' "$p" > "$TPL/$plan/wave-s328-$p-approved.md"
  # patch REAL, gerado pelo próprio git: `git apply --reverse --check` sobre
  # ele é o que o MORNING usa para reconhecer um pacote já landado.
  printf 'pacote %s aplicado\n' "$p" > "$TPL/$cer/APPLIED-$p.txt"
  ( cd "$TPL" && git add -N -- "$cer/APPLIED-$p.txt" >/dev/null 2>&1 \
      && git diff -- "$cer/APPLIED-$p.txt" > "$SCRATCH/$p.patch" \
      && git reset -q -- "$cer/APPLIED-$p.txt" >/dev/null 2>&1 )
  rm -f "$TPL/$cer/APPLIED-$p.txt"
  _safe_cp "$SCRATCH/$p.patch" "$abs/$p.patch" || return 1
  ( cd "$TPL" && git add -- \
      "$plan/OWNER-S328-$p-SIGN.sh" "$plan/OWNER-S328-$p-LAND.sh" \
      "$plan/wave-s328-$p-approved.md" \
      "$cer/finalize-$p.sh" "$cer/COMMIT-MSG-$p.txt" "$cer/$p.patch" )
}

_mk_manifest_pkg() {  # <P> <PLANDIR> <SENTBASE>
  local p="$1" plan="$2" sb="$3"
  local cer="$plan/s328-ceremony-$p" abs="$TPL/$plan/s328-ceremony-$p"
  mkdir -p "$abs"
  _render "$TMPL_DIR/sign-manifest.tmpl" "$TPL/$plan/OWNER-W179-W24-SIGN.sh" "$p" "$plan" "" "0" "$sb"
  _render "$TMPL_DIR/land-manifest.tmpl" "$TPL/$plan/OWNER-W179-W24-LAND.sh" "$p" "$plan" "" "0" "$sb"
  printf 'ceremony(s328-%s): stub do pacote %s aplicado pelo harness\n' "$p" "$p" > "$abs/COMMIT-MSG-$p.txt"
  printf '# sentinel-draft STUB do pacote %s\n\nApproved-By: TO-FILL\n' "$p" > "$TPL/$plan/$sb-draft.md"
  ( cd "$TPL" && git add -- \
      "$plan/OWNER-W179-W24-SIGN.sh" "$plan/OWNER-W179-W24-LAND.sh" \
      "$plan/$sb-draft.md" "$cer/COMMIT-MSG-$p.txt" )
}

_mk_patch_pkg B ".claude/plans/PLAN-169" ""                       0 || exit 2
_mk_patch_pkg A ".claude/plans/PLAN-183" "--ownership-e2e=defer"  1 || exit 2
_mk_patch_pkg C ".claude/plans/PLAN-185" ""                       0 || exit 2
_mk_manifest_pkg D ".claude/plans/PLAN-179" "W179-W24-approved"      || exit 2

# EXPECTED-BASELINE do A: é dele que o MORNING deriva o conjunto RED do CI.
printf 'EXPECTED_OWNERSHIP_RED_IDS="OWN-0016 OWN-0024 OWN-0027"\n' \
  > "$TPL/.claude/plans/PLAN-183/s328-ceremony-A/EXPECTED-BASELINE.txt"
( cd "$TPL" && git add -- ".claude/plans/PLAN-183/s328-ceremony-A/EXPECTED-BASELINE.txt" \
    && git add -- "$MORNING_REL" \
    && git commit -q -m "test(harness): pacotes stub do harness do MORNING" ) || {
  printf 'commit dos stubs falhou\n' >&2; exit 2; }

DIRTY_TPL="$( git -C "$TPL" status --porcelain | head -5 )"
if [ -n "$DIRTY_TPL" ]; then
  printf '  \033[33mmolde com árvore suja:\033[0m\n%s\n' "$DIRTY_TPL"
fi
printf '  molde pronto: 4 pacotes stub commitados\n'

# --- helpers de cenário ----------------------------------------------------
RC=0
_new_case() {  # <nome> -> ecoa o diretório
  local d="$SCRATCH/$1"
  rm -rf "$d"
  if [ -L "$d" ]; then printf 'destino é SYMLINK: %s\n' "$d" >&2; return 1; fi
  cp -R "$TPL" "$d" || return 1
  printf '%s' "$d"
}
_drop_pkg() {  # <dir> <P> — remove os DOIS scripts do pacote (ausência real)
  local d="$1" p="$2"
  case "$p" in
    B) rm -f "$d/.claude/plans/PLAN-169/OWNER-S328-B-SIGN.sh" "$d/.claude/plans/PLAN-169/OWNER-S328-B-LAND.sh" ;;
    A) rm -f "$d/.claude/plans/PLAN-183/OWNER-S328-A-SIGN.sh" "$d/.claude/plans/PLAN-183/OWNER-S328-A-LAND.sh" ;;
    C) rm -f "$d/.claude/plans/PLAN-185/OWNER-S328-C-SIGN.sh" "$d/.claude/plans/PLAN-185/OWNER-S328-C-LAND.sh" ;;
    D) rm -f "$d/.claude/plans/PLAN-179/OWNER-W179-W24-SIGN.sh" "$d/.claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh" ;;
  esac
  # O pacote tem de sumir do PONTO DE VISTA DO GIT também: um arquivo apagado
  # e não commitado deixaria a árvore suja e o MORNING abortaria em 3 — que é
  # o comportamento certo dele, mas não é o cenário que quero medir aqui.
  ( cd "$d" && git commit -q -a -m "test: remove o pacote $p" ) || printf ''
}
_run_morning() {  # <dir> <arquivo de saída> [args...]
  local d="$1" out="$2"; shift 2
  ( cd "$d" && MORNING_TEST_ORDER_FILE="$d.order" \
      bash "$d/$MORNING_REL" "$@" ) > "$out" 2>&1
  RC=$?
}
_order_of() {  # <dir> — sequência de etapas executadas, numa linha
  [ -f "$1.order" ] && tr '\n' ' ' < "$1.order" | sed 's/ $//'
}

# ===========================================================================
_head "S1 — todos os pacotes presentes (--dry-run)"
# ===========================================================================
D1="$( _new_case s1 )" || exit 2
_run_morning "$D1" "$SCRATCH/s1.out" --dry-run
_assert_rc 0 "$RC" "rc 0: nada ausente, nada pulado"
_assert_has "$SCRATCH/s1.out" "PACOTE B (PLAN-169" "abriu o pacote B"
_assert_has "$SCRATCH/s1.out" "PACOTE A (PLAN-183" "abriu o pacote A"
_assert_has "$SCRATCH/s1.out" "PACOTE C (PLAN-185" "abriu o pacote C"
_assert_has "$SCRATCH/s1.out" "PACOTE D (PLAN-179" "abriu o pacote D"
_assert_hasnt "$SCRATCH/s1.out" "PACOTE C NÃO RODA" "C não foi pulado"
_assert_has "$SCRATCH/s1.out" "LAND --ownership-e2e=defer" "derivou a flag obrigatória do LAND do A"
_assert_has "$SCRATCH/s1.out" "OWN-0016 OWN-0024 OWN-0027" "leu o conjunto RED do EXPECTED-BASELINE do A"
_assert_has "$SCRATCH/s1.out" "RERUN de madrugada (03:03)" "o baseline aponta o rerun como quem deixa o Validate verde"
_assert_hasnt "$SCRATCH/s1.out" "Validate       esperado VERDE" "NÃO promete Validate verde (fase 1 do B é advisory)"
_assert_hasnt "$SCRATCH/s1.out" "o pacote B curou o gate" "não repete a afirmação refutada pelo README-B"
_assert_eq "" "$( _order_of "$D1" )" "--dry-run global não executou NENHUM script de pacote"
# ordem impressa: B antes de A antes de C antes de D
ORD1="$( grep -n 'PACOTE [BACD] (' "$SCRATCH/s1.out" | sed 's/.*PACOTE \([BACD]\) (.*/\1/' | tr -d '\n' )"
_assert_eq "BACD" "$ORD1" "ordem impressa é B → A → C → D"

# ===========================================================================
_head "S2 — pacote B ausente"
# ===========================================================================
D2="$( _new_case s2 )" || exit 2
_drop_pkg "$D2" B
_run_morning "$D2" "$SCRATCH/s2.out" --dry-run
_assert_rc 7 "$RC" "rc 7: terminou sem vermelho, mas nem tudo rodou"
_assert_has "$SCRATCH/s2.out" "pacote AUSENTE" "detectou a ausência do B em runtime"
_assert_has "$SCRATCH/s2.out" "SEM O PACOTE B O CI" "avisou que o CI Validate segue vermelho"
_assert_has "$SCRATCH/s2.out" "PACOTE C NÃO RODA" "abortou a etapa C"
_assert_has "$SCRATCH/s2.out" "o pacote B não está no repositório" "nomeou a razão (falta o B)"
_assert_has "$SCRATCH/s2.out" "PACOTE D (PLAN-179" "seguiu para o D mesmo assim"
_assert_has "$SCRATCH/s2.out" "CONTINUA VERMELHO" "o baseline do CI no fim repete que o Validate segue vermelho"

# ===========================================================================
_head "S3 — pacote A ausente"
# ===========================================================================
D3="$( _new_case s3 )" || exit 2
_drop_pkg "$D3" A
_run_morning "$D3" "$SCRATCH/s3.out" --dry-run
_assert_rc 7 "$RC" "rc 7"
_assert_has "$SCRATCH/s3.out" "PACOTE C NÃO RODA" "abortou a etapa C"
_assert_has "$SCRATCH/s3.out" "o pacote A não está no repositório" "nomeou a razão (falta o A)"
_assert_hasnt "$SCRATCH/s3.out" "SEM O PACOTE B O CI" "não avisou de B (que está presente)"

# ===========================================================================
_head "S4 — pacote D ausente"
# ===========================================================================
D4="$( _new_case s4 )" || exit 2
_drop_pkg "$D4" D
_run_morning "$D4" "$SCRATCH/s4.out" --dry-run
_assert_rc 7 "$RC" "rc 7"
_assert_has "$SCRATCH/s4.out" "pacote AUSENTE" "pulou o D avisando"
_assert_has "$SCRATCH/s4.out" "PACOTE C (PLAN-185" "os pacotes anteriores rodaram"
_assert_hasnt "$SCRATCH/s4.out" "PACOTE C NÃO RODA" "C não foi pulado (A e B presentes)"

# ===========================================================================
_head "S5 — SIGN do B devolve 1: para no PRIMEIRO vermelho"
# ===========================================================================
D5="$( _new_case s5 )" || exit 2
( cd "$D5" && MORNING_TEST_ORDER_FILE="$D5.order" STUB_SIGN_RC_B=1 \
    bash "$D5/$MORNING_REL" ) > "$SCRATCH/s5.out" 2>&1
RC=$?
_assert_rc 12 "$RC" "rc 12 = pacote B, etapa SIGN"
_assert_has "$SCRATCH/s5.out" "VERMELHO" "anunciou o vermelho"
_assert_has "$SCRATCH/s5.out" "pacote B, etapa SIGN" "nomeou pacote e etapa"
_assert_has "$SCRATCH/s5.out" "--from B" "imprimiu o comando de retomada"
_assert_has "$SCRATCH/s5.out" "No pinentry" "trouxe a orientação do modo de falha conhecido"
_assert_has "$SCRATCH/s5.out" "RESUMO" "imprimiu o resumo mesmo parando"
_assert_hasnt "$SCRATCH/s5.out" "PACOTE A (PLAN-183" "NÃO seguiu para o pacote A"
_assert_eq "FINALIZE-B SIGN-B" "$( _order_of "$D5" )" "executou só finalize+SIGN do B e parou"

# ===========================================================================
_head "S5b — falha de pinentry: reinicia o agente e tenta UMA vez, só uma"
# ===========================================================================
D5B="$( _new_case s5b )" || exit 2
( cd "$D5B" && MORNING_TEST_ORDER_FILE="$D5B.order" STUB_SIGN_PINENTRY_B=1 \
    bash "$D5B/$MORNING_REL" ) > "$SCRATCH/s5b.out" 2>&1
RC=$?
_assert_rc 12 "$RC" "rc 12: parou no SIGN do B depois da retentativa"
_assert_has "$SCRATCH/s5b.out" "reiniciando o agente do GPG" "detectou a falha de pinentry"
_assert_eq "FINALIZE-B SIGN-B SIGN-B" "$( _order_of "$D5B" )" "tentou exatamente DUAS vezes (uma retentativa), não um laço"

# ===========================================================================
_head "S6 — caminho feliz de verdade (stubs, sem --dry-run)"
# ===========================================================================
D6="$( _new_case s6 )" || exit 2
_run_morning "$D6" "$SCRATCH/s6.out"
_assert_rc 0 "$RC" "rc 0: os 4 pacotes landaram"
_assert_eq "FINALIZE-B SIGN-B LAND-B-dry1 LAND-B-dry0 FINALIZE-A SIGN-A LAND-A-dry1 LAND-A-dry0 FINALIZE-C SIGN-C LAND-C-dry1 LAND-C-dry0 SIGN-D LAND-D-dry1 LAND-D-dry0" \
  "$( _order_of "$D6" )" "sequência exata: finalize→SIGN→dry-run→land, na ordem B A C D (D sem finalize)"
_assert_has "$SCRATCH/s6.out" "LANDADO" "reportou o land"
_assert_has "$SCRATCH/s6.out" "não tem upstream configurado" "degradou o teste de push sem upstream (clone sem origin)"
_assert_has "$SCRATCH/s6.out" "NÃO é regressão do land" "com B landado, avisa que o Validate ainda pode reprovar"
_assert_hasnt "$SCRATCH/s6.out" "Validate       esperado VERDE" "mesmo com B landado, NÃO promete CI verde"
LOGN=0
for _lf in "$D6/.claude/plans/PLAN-183/s328-ceremony-main"/morning-*.log; do
  [ -f "$_lf" ] && LOGN=$(( LOGN + 1 ))
done
if [ "$LOGN" -ge 1 ]; then _pass "gravou o log em s328-ceremony-main/ ($LOGN arquivo)"; else
  _fail "não gravou o log em s328-ceremony-main/"; fi
COMMITS="$( git -C "$D6" log --format=%s -n 6 | grep -c 'stub do pacote' )"
_assert_eq "4" "$COMMITS" "4 commits de cerimônia no clone"

# ===========================================================================
_head "S7 — segunda passada sobre o S6: idempotente"
# ===========================================================================
rm -f "$D6.order"
_run_morning "$D6" "$SCRATCH/s7.out"
_assert_rc 0 "$RC" "rc 0 na segunda passada"
IDEM="$( _count_in "$SCRATCH/s7.out" "JÁ está no repositório" )"
_assert_eq "4" "$IDEM" "reconheceu os 4 pacotes como já landados"
_assert_eq "" "$( _order_of "$D6" )" "não re-executou NENHUM script de pacote"

# ===========================================================================
_head "S8 — --only e --from"
# ===========================================================================
D8="$( _new_case s8 )" || exit 2
_run_morning "$D8" "$SCRATCH/s8.out" --dry-run --only D
_assert_rc 7 "$RC" "rc 7: só um pacote rodou"
_assert_has "$SCRATCH/s8.out" "PACOTE D (PLAN-179" "rodou o D"
_assert_hasnt "$SCRATCH/s8.out" "PACOTE B (PLAN-169" "não rodou o B"
D9="$( _new_case s9 )" || exit 2
_run_morning "$D9" "$SCRATCH/s9.out" --dry-run --from C
_assert_rc 7 "$RC" "rc 7: B e A pulados por --from"
_assert_has "$SCRATCH/s9.out" "pulado por --from C" "marcou os anteriores como pulados"
_assert_has "$SCRATCH/s9.out" "PACOTE C NÃO RODA" "C respeita a dependência mesmo com --from"

# ===========================================================================
_head "S10 — pré-condições e uso"
# ===========================================================================
DA="$( _new_case s10 )" || exit 2
( cd "$DA" && git checkout -q -b nao-main )
_run_morning "$DA" "$SCRATCH/s10.out"
_assert_rc 3 "$RC" "rc 3 fora do main"
_assert_has "$SCRATCH/s10.out" "não em \"main\"" "nomeou a pré-condição"
DB="$( _new_case s11 )" || exit 2
printf 'sujeira\n' >> "$DB/README.md"
_run_morning "$DB" "$SCRATCH/s11.out" --dry-run
_assert_rc 3 "$RC" "rc 3 com árvore suja"
_assert_has "$SCRATCH/s11.out" "modificações RASTREADAS" "nomeou a árvore suja"
_run_morning "$DB" "$SCRATCH/s12.out" --from Z
_assert_rc 2 "$RC" "rc 2 para pacote inexistente em --from"

# ===========================================================================
_head "S12 — docs/threat-model.md sujo pelo checker de frescor"
# ===========================================================================
# Controle POSITIVO com o instrumento REAL: quem suja o arquivo é
# `check-threat-model-freshness.py` (`:188-195`), não um sed do harness. Se um
# dia ele parar de flipar, o cenário reprova aqui em vez de passar vazio.
TM="docs/threat-model.md"
DC="$( _new_case s12a )" || exit 2
( cd "$DC" && python3 .claude/scripts/check-threat-model-freshness.py ) > "$SCRATCH/s12a.checker" 2>&1
TM_DIRTY="$( git -C "$DC" status --porcelain=v1 -- "$TM" )"
if [ -n "$TM_DIRTY" ]; then
  _pass "o checker real sujou $TM (controle positivo vivo)"
else
  _fail "o checker NÃO sujou $TM — o cenário virou vazio; a pergunta do instrumento envelheceu"
fi
_run_morning "$DC" "$SCRATCH/s12a.out" --dry-run
_assert_rc 0 "$RC" "seguiu normalmente depois de reverter"
_assert_has "$SCRATCH/s12a.out" "estava modificado e eu REVERTI" "anunciou a reversão e a razão"
_assert_has "$SCRATCH/s12a.out" "check-threat-model-freshness.py" "nomeou quem escreveu no arquivo"
_assert_eq "" "$( git -C "$DC" status --porcelain=v1 -- "$TM" )" "o arquivo voltou ao original"

# (b) mesma troca de status MAIS outra linha: não é o flip puro ⇒ não reverte
DD="$( _new_case s12b )" || exit 2
( cd "$DD" && python3 .claude/scripts/check-threat-model-freshness.py ) >/dev/null 2>&1
printf '\nlinha que alguem escreveu de verdade\n' >> "$DD/$TM"
_run_morning "$DD" "$SCRATCH/s12b.out" --dry-run
_assert_rc 3 "$RC" "abortou: o diff não é só a troca de status"
_assert_has "$SCRATCH/s12b.out" "docs/threat-model.md" "nomeou o path no abort"
_assert_has "$SCRATCH/s12b.out" "NÃO é só a troca de status" "explicou por que não reverteu"
_assert_has "$SCRATCH/s12b.out" "git checkout -- docs/threat-model.md" "deu o comando de recuperação"
if [ -n "$( git -C "$DD" status --porcelain=v1 -- "$TM" )" ]; then
  _pass "NÃO reverteu o arquivo com conteúdo real dentro"
else
  _fail "reverteu um arquivo que tinha mudança de verdade — destruiu trabalho"
fi

# (c) flip + OUTRO arquivo sujo: a cura não dispara, e nada é revertido
DE="$( _new_case s12c )" || exit 2
( cd "$DE" && python3 .claude/scripts/check-threat-model-freshness.py ) >/dev/null 2>&1
printf 'sujeira de outra pessoa\n' >> "$DE/README.md"
_run_morning "$DE" "$SCRATCH/s12c.out" --dry-run
_assert_rc 3 "$RC" "abortou com dois paths sujos"
_assert_has "$SCRATCH/s12c.out" "README.md" "nomeou o outro path"
if [ -n "$( git -C "$DE" status --porcelain=v1 -- "$TM" )" ]; then
  _pass "não reverteu nada quando havia mais de um arquivo sujo"
else
  _fail "reverteu $TM mesmo com outro arquivo sujo — a cura tem de ser pontual"
fi

# (d) DIREÇÃO INVERSA (stale -> accepted): é edição deliberada de gente, não
# do checker — que só escreve accepted -> stale. Reverter aqui destruiria o
# trabalho de quem RE-ACEITOU o modelo de ameaças. Este é o controle positivo
# do achado P1 do rail: com a versão anterior (que aceitava as duas direções)
# o arquivo era revertido em silêncio e este cenário ficava vermelho.
DG="$( _new_case s12d )" || exit 2
( cd "$DG" && python3 .claude/scripts/check-threat-model-freshness.py ) >/dev/null 2>&1
( cd "$DG" && git commit -q -a -m "test: threat-model em stale no HEAD" ) || printf ''
if [ -L "$DG/$TM" ]; then _fail "destino é SYMLINK: $DG/$TM"; else
  sed 's/^\*\*Status:\*\* stale$/**Status:** accepted/' "$DG/$TM" > "$DG/$TM.tmp"
  mv "$DG/$TM.tmp" "$DG/$TM"
fi
INV="$( git -C "$DG" diff -U0 -- "$TM" | grep -c -F -e '-**Status:** stale' -e '+**Status:** accepted' )"
case "${INV:-0}" in ''|*[!0-9]*) INV=0 ;; esac
_assert_eq "2" "$INV" "o diff plantado é mesmo o inverso (stale -> accepted, 1 linha)"
_run_morning "$DG" "$SCRATCH/s12d.out" --dry-run
_assert_rc 3 "$RC" "abortou: a direção inversa NÃO é a do checker"
_assert_has "$SCRATCH/s12d.out" "docs/threat-model.md" "nomeou o path"
_assert_hasnt "$SCRATCH/s12d.out" "eu REVERTI" "não reverteu"
if [ -n "$( git -C "$DG" status --porcelain=v1 -- "$TM" )" ]; then
  _pass "preservou a re-aceitação deliberada (stale -> accepted intacta)"
else
  _fail "DESTRUIU uma edição deliberada: reverteu um flip stale -> accepted"
fi

# ===========================================================================
_head "S13 — pacote pela METADE (só um dos dois scripts)"
# ===========================================================================
DF="$( _new_case s13 )" || exit 2
rm -f "$DF/.claude/plans/PLAN-169/OWNER-S328-B-SIGN.sh"
( cd "$DF" && git commit -q -a -m "test: pacote B sem o SIGN" ) || printf ''
_run_morning "$DF" "$SCRATCH/s13.out" --dry-run
_assert_rc 7 "$RC" "rc 7: pacote incompleto conta como pulado"
_assert_has "$SCRATCH/s13.out" "pacote INCOMPLETO" "distinguiu incompleto de ausente"
_assert_has "$SCRATCH/s13.out" "OWNER-S328-B-LAND.sh" "listou o script que existe"
_assert_has "$SCRATCH/s13.out" "SEM O PACOTE B O CI" "avisou do CI mesmo assim"
_assert_has "$SCRATCH/s13.out" "PACOTE C NÃO RODA" "C continua bloqueado pela dependência"

# ===========================================================================
_head "RESULTADO"
# ===========================================================================
printf '\n  PASS=%s  FAIL=%s\n' "$PASS" "$FAIL"
printf '  artefatos: %s\n\n' "$SCRATCH"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
