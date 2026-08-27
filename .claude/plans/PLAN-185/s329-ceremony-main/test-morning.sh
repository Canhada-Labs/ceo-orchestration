#!/usr/bin/env bash
# test-morning.sh — auto-teste do OWNER-S329-MORNING.sh.
# CEREMONY-LINT: handwritten-exception: harness de teste do orquestrador da manhã; roda tudo num clone descartável, não assina nem empurra nada
#
# TUDO roda num CLONE DESCARTÁVEL sob um diretório temporário. A árvore viva
# nunca é tocada — e o clone tem o remote `origin` REMOVIDO logo no início,
# porque `git clone --local` aponta origin para o repo vivo e um push acidental
# subiria daqui. (O cenário S12, que precisa de um origin, cria um repositório
# NU próprio no scratchpad; nunca o repo vivo.)
#
# ESTADO COMMITADO (T-S329-2)
#   O clone traz só o que está COMMITADO. Se o MORNING ou os materiais de um
#   pacote ainda estiverem untracked/modificados, este harness estaria medindo
#   uma árvore que o Owner não vai ter na mão — então ele PARA e diz quais
#   arquivos faltam. Para rodar mesmo assim (durante a montagem da noite):
#     CEO_MORNING_HARNESS_UNCOMMITTED=1 bash <este arquivo>
#   O modo aparece em voz alta na saída e no resultado final; ele não é
#   silencioso porque um verde tirado dele não vale como o verde do contrato.
#
# OS PACOTES SÃO STUBS. O que este harness prova é o comportamento do
# ORQUESTRADOR — ordem, detecção de ausência, portão do rail, portão do GPG,
# derivação de flags, parada no primeiro vermelho, idempotência. Ele NÃO prova
# que os SIGN/LAND reais funcionam: cada pacote tem o próprio harness para isso
# (`test-ceremony-scripts-<P>.sh`). Limite declarado, não descuido.
#
# O stub do pacote C exige `--ownership-e2e` de propósito, mesmo que o C real
# possa não exigir: é a forma DIFÍCIL da derivação de argumentos, e testar a
# fácil não provaria nada.
#
# CENÁRIOS
#   S1   os dois pacotes presentes ....... ordem C→E, nada pulado, rc 0
#   S2   pacote C ausente ................ avisa alto e pula; E roda; rc 7
#   S3   pacote E ausente ................ avisa alto e pula; C roda; rc 7
#   S4   caminho feliz de verdade ........ 2 pacotes landados na ordem, rc 0,
#                                          log por fase em s329-ceremony-main/
#   S5   segunda passada sobre o S4 ...... idempotente: "nada a fazer"
#   S6   SIGN do C devolvendo 1 .......... para NO PRIMEIRO vermelho, rc 12,
#                                          imprime `--from C`, E não roda
#   S6b  falha de pinentry .............. reinicia o gpg-agent e tenta UMA vez
#   S7   rail do C em REJECT ............. aborta ANTES de assinar, rc 17,
#                                          e ANTES do finalize (nada executado)
#   S7b  rail-round-10 vs rail-round-2 ... escolhe por NÚMERO, não por nome
#   S7c  nenhum registro de rail ......... rc 17 nomeado
#   S8a  GNUPGHOME sem chave secreta ..... avisa no preflight, rc 12 no pacote
#   S8b  `gpg` fora do PATH .............. mesma parada, mensagem própria
#   S9   --from E e --only C ............. escopo respeitado
#   S10  pré-condições e uso ............. branch, árvore suja, argumento ruim
#   S11  docs/threat-model.md ............ reverte SÓ o flip exato (3 pernas)
#   S12  atrás do origin ................. rc 3 nomeado, antes de qualquer land
#   S13  pacote pela METADE .............. distingue de ausente, rc 7
#
# Uso:  bash .claude/plans/PLAN-185/s329-ceremony-main/test-morning.sh
set -uo pipefail   # NÃO -e: as falhas são CLASSIFICADAS, não fatais.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
LIVE="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
MORNING_REL=".claude/plans/PLAN-185/OWNER-S329-MORNING.sh"

SCRATCH="${MORNING_SELFTEST_SCRATCH:-${TMPDIR:-/tmp}/ceo-morning-s329-selftest}"
# O destino tem de ser descartável E não pode estar dentro do repositório vivo:
# um `rm -rf` apontado para dentro dele apagaria trabalho de verdade. A
# comparação é por REALPATH dos dois lados — no macOS `/tmp` é symlink para
# `/private/tmp`, e comparar strings mediria FORMATO, não caminho.
_real() { ( cd "$1" 2>/dev/null && pwd -P ) || printf '%s' "$1"; }
mkdir -p "$SCRATCH" 2>/dev/null || printf ''
SCRATCH_REAL="$( _real "$SCRATCH" )"
LIVE_REAL="$( _real "$LIVE" )"
case "$SCRATCH_REAL" in
  "$LIVE_REAL"|"$LIVE_REAL"/*)
    printf 'ABORT: SCRATCH está DENTRO do repositório vivo: %s\n' "$SCRATCH_REAL" >&2; exit 2 ;;
esac
case "$SCRATCH_REAL" in
  /private/tmp/*|/tmp/*|/private/var/folders/*|/var/folders/*) : ;;
  *) printf 'ABORT: SCRATCH fora de um diretório descartável: %s\n' "$SCRATCH_REAL" >&2; exit 2 ;;
esac

PASS=0; FAIL=0
_pass() { PASS=$(( PASS + 1 )); printf '    \033[32mPASS\033[0m %s\n' "$*"; }
_fail() { FAIL=$(( FAIL + 1 )); printf '    \033[31mFAIL\033[0m %s\n' "$*"; }
_head() { printf '\n\033[1m%s\033[0m\n' "$*"; }
_note() { printf '    \033[33m..\033[0m   %s\n' "$*"; }

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
# todo cp deste harness passa por aqui.
_safe_cp() {
  if [ -L "$2" ]; then _fail "destino é SYMLINK, recusado: $2"; return 1; fi
  cp "$1" "$2"
}

# ===========================================================================
_head "0a — o que este harness vai medir está COMMITADO? (T-S329-2)"
# ===========================================================================
UNCOMMITTED_OK="${CEO_MORNING_HARNESS_UNCOMMITTED:-0}"
CS_BAD=""
_cs_one() {  # <path relativo ao repo vivo>
  local rel="$1"
  [ -e "$LIVE/$rel" ] || return 0          # ausente é estado legítimo
  if ! git -C "$LIVE" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1; then
    CS_BAD="$CS_BAD  untracked   $rel
"
    return 0
  fi
  if ! git -C "$LIVE" diff --quiet HEAD -- "$rel" 2>/dev/null; then
    CS_BAD="$CS_BAD  modificado  $rel
"
  fi
}
_cs_one "$MORNING_REL"
for _f in \
  ".claude/plans/PLAN-185/OWNER-S329-C-SIGN.sh" \
  ".claude/plans/PLAN-185/OWNER-S329-C-LAND.sh" \
  ".claude/plans/PLAN-169/OWNER-S329-E-SIGN.sh" \
  ".claude/plans/PLAN-169/OWNER-S329-E-LAND.sh"
do _cs_one "$_f"; done
for _f in "$LIVE/.claude/plans/PLAN-185/s329-ceremony-C"/* "$LIVE/.claude/plans/PLAN-169/s329-ceremony-E"/*; do
  [ -f "$_f" ] || continue
  _cs_one "${_f#"$LIVE"/}"
done

if [ -n "$CS_BAD" ]; then
  printf '  \033[33marquivos que o clone NÃO vai enxergar:\033[0m\n%s' "$CS_BAD"
  if [ "$UNCOMMITTED_OK" = "1" ]; then
    printf '\n  \033[33mCEO_MORNING_HARNESS_UNCOMMITTED=1\033[0m — seguindo assim mesmo.\n'
    printf '  O MORNING VIVO será copiado para dentro do clone. Um verde tirado\n'
    printf '  daqui NÃO é o verde do contrato: repita depois de commitar.\n'
  else
    printf '\n\033[31mABORT:\033[0m o harness mede o estado que o Owner terá na mão, e ele\n' >&2
    printf '  ainda não existe: os arquivos acima estão fora do HEAD.\n' >&2
    printf '  Commite-os e rode de novo, ou — só durante a montagem da noite —\n' >&2
    printf '  rode assim, ciente de que o verde vale menos:\n' >&2
    printf '    CEO_MORNING_HARNESS_UNCOMMITTED=1 bash %s\n' "$SCRIPT_DIR/$( basename "${BASH_SOURCE[0]}" )" >&2
    exit 2
  fi
else
  printf '  \033[32mok\033[0m  MORNING e materiais de pacote estão commitados e limpos\n'
fi

# ===========================================================================
_head "0b — clone-molde com os 2 pacotes STUB"
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

if [ -n "$CS_BAD" ]; then
  mkdir -p "$TPL/$( dirname "$MORNING_REL" )"
  _safe_cp "$LIVE/$MORNING_REL" "$TPL/$MORNING_REL" || exit 2
  printf '  MORNING vivo copiado para o clone (modo UNCOMMITTED)\n'
fi
[ -f "$TPL/$MORNING_REL" ] || { printf 'ABORT: %s não existe no clone\n' "$MORNING_REL" >&2; exit 2; }

# --- chave GPG descartável -------------------------------------------------
# O MORNING mede o GPG no preflight (existe? tem chave secreta?). Os stubs não
# assinam nada — esta chave existe só para o caminho feliz ter o que o
# preflight procura, sem tocar no chaveiro real do Owner.
#
# O chaveiro NÃO mora sob $SCRATCH, e a razão é medida: o gpg-agent abre um
# socket UNIX em $GNUPGHOME/S.gpg-agent, e `sun_path` tem ~104 bytes. Com o
# $SCRATCH sob o $TMPDIR do macOS (`/var/folders/<hash>/T/...`, 87 caracteres)
# o socket dá 99 e o agente não sobe: `IPC connect call failed`. Um caminho
# CURTO sob /tmp é o que faz esta parte funcionar.
GPG_ROOT="$( mktemp -d /tmp/ceo-m329.XXXXXX )" || {
  printf 'ABORT: não consegui criar o diretório do chaveiro descartável\n' >&2; exit 2; }
case "$( _real "$GPG_ROOT" )" in
  /private/tmp/*|/tmp/*) : ;;
  *) printf 'ABORT: chaveiro descartável fora de /tmp: %s\n' "$GPG_ROOT" >&2; exit 2 ;;
esac
GPG_KEYED="$GPG_ROOT/k"
GPG_EMPTY="$GPG_ROOT/e"
mkdir -p "$GPG_KEYED" "$GPG_EMPTY"
chmod 700 "$GPG_KEYED" "$GPG_EMPTY"
trap 'GNUPGHOME="$GPG_KEYED" gpgconf --kill gpg-agent >/dev/null 2>&1 || printf ""; rm -rf "$GPG_ROOT" 2>/dev/null || printf ""; rmdir "$LOCK" 2>/dev/null || printf ""' EXIT

GNUPGHOME="$GPG_KEYED" gpg --batch --quiet --passphrase '' \
  --quick-generate-key "morning selftest <selftest@example.invalid>" default default never \
  > "$SCRATCH/gpg-genkey.log" 2>&1 || printf ''
_KEYS="$( GNUPGHOME="$GPG_KEYED" gpg --list-secret-keys --with-colons 2>/dev/null | grep -c '^sec:' )"
case "${_KEYS:-0}" in ''|*[!0-9]*) _KEYS=0 ;; esac
if [ "$_KEYS" -gt 0 ]; then
  printf '  chave GPG descartável em %s (%s chave)\n' "$GPG_KEYED" "$_KEYS"
else
  printf '  \033[31mABORT:\033[0m não consegui gerar a chave GPG descartável — sem ela o\n' >&2
  printf '  caminho feliz mediria o portão do GPG em vez do orquestrador.\n' >&2
  printf '  O que o gpg disse (GNUPGHOME=%s, socket com %s bytes):\n' "$GPG_KEYED" "$(( ${#GPG_KEYED} + 12 ))" >&2
  sed 's/^/    /' "$SCRATCH/gpg-genkey.log" >&2
  exit 2
fi

# --- moldes dos stubs ------------------------------------------------------
TMPL_DIR="$SCRATCH/tmpl"; mkdir -p "$TMPL_DIR"

cat > "$TMPL_DIR/sign.tmpl" <<'STUB'
#!/usr/bin/env bash
# STUB SIGN do pacote @P@ — gerado por test-morning.sh.
# CEREMONY-LINT: handwritten-exception: stub de teste; NAO assina nada.
set -uo pipefail
SD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SD" && git rev-parse --show-toplevel )"
cd "$ROOT"
PLAN_DIR="@PLANDIR@"
CEREMONY_DIR="$PLAN_DIR/s329-ceremony-@P@"
SENTINEL="$PLAN_DIR/wave-s329-@P@-approved.md"
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
  # comum, e a retentativa tem cenario proprio (S6b).
  printf 'gpg: falha simulada pelo harness\n' >&2
  exit "$RC"
fi
if [ -L "$SENTINEL.asc" ]; then
  printf 'STUB-SIGN @P@: %s.asc e um SYMLINK — recuso escrever atraves dele\n' "$SENTINEL" >&2
  exit 1
fi
printf 'STUB-NOT-A-SIGNATURE\n' > "$SENTINEL.asc"
printf 'PRONTO\n'
STUB

cat > "$TMPL_DIR/land.tmpl" <<'STUB'
#!/usr/bin/env bash
# STUB LAND do pacote @P@ — gerado por test-morning.sh.
# CEREMONY-LINT: handwritten-exception: stub de teste; commita num clone descartavel, nunca empurra.
#
# Uso:
#   bash @PLANDIR@/OWNER-S329-@P@-LAND.sh --dry-run @EXTRA@
#   bash @PLANDIR@/OWNER-S329-@P@-LAND.sh @EXTRA@
set -uo pipefail
SD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SD" && git rev-parse --show-toplevel )"
cd "$ROOT"
PLAN_DIR="@PLANDIR@"
CEREMONY_DIR="$PLAN_DIR/s329-ceremony-@P@"
SENTINEL="$PLAN_DIR/wave-s329-@P@-approved.md"
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

_render() {  # <molde> <destino> <P> <PLANDIR> <EXTRA> <NEEDSOWN>
  sed -e "s|@P@|$3|g" -e "s|@PLANDIR@|$4|g" -e "s|@EXTRA@|$5|g" \
      -e "s|@NEEDSOWN@|$6|g" "$1" > "$2"
}

_mk_pkg() {  # <P> <PLANDIR> <EXTRA-do-LAND> <NEEDSOWN>
  local p="$1" plan="$2" extra="$3" needs="$4"
  local cer="$plan/s329-ceremony-$p" abs="$TPL/$plan/s329-ceremony-$p"
  # O clone traz o que estiver COMMITADO — e a noite commita materiais reais
  # deste mesmo pacote enquanto o harness roda. Medido na primeira execução:
  # os `rail-round-2.md`/`rail-round-3.md` REAIS do pacote E (veredito REJECT)
  # sobreviveram ao lado do stub, o MORNING elegeu a rodada 3 (corretamente, a
  # de maior número) e abortou — e 15 asserções falharam medindo o pacote de
  # verdade em vez do orquestrador. O stub só é stub se o diretório for LIMPO.
  if [ -d "$abs" ]; then
    ( cd "$TPL" && git rm -r -q --ignore-unmatch --cached -- "$cer" >/dev/null 2>&1 ) || printf ''
    rm -rf "$abs"
  fi
  ( cd "$TPL" && git rm -q --ignore-unmatch --cached -- \
      "$plan/OWNER-S329-$p-SIGN.sh" "$plan/OWNER-S329-$p-LAND.sh" \
      "$plan/wave-s329-$p-approved.md" "$plan/wave-s329-$p-approved.md.asc" >/dev/null 2>&1 ) || printf ''
  rm -f "$TPL/$plan/wave-s329-$p-approved.md.asc"
  mkdir -p "$abs"
  _render "$TMPL_DIR/sign.tmpl"     "$TPL/$plan/OWNER-S329-$p-SIGN.sh" "$p" "$plan" "$extra" "$needs"
  _render "$TMPL_DIR/land.tmpl"     "$TPL/$plan/OWNER-S329-$p-LAND.sh" "$p" "$plan" "$extra" "$needs"
  _render "$TMPL_DIR/finalize.tmpl" "$abs/finalize-$p.sh"              "$p" "$plan" "$extra" "$needs"
  printf 'ceremony(s329-%s): stub do pacote %s aplicado pelo harness\n' "$p" "$p" > "$abs/COMMIT-MSG-$p.txt"
  printf '# Pacote %s — rail codex rodada 1 (STUB do harness)\n\nRail-Verdict: APPROVE\nAchados: 0\n' \
    "$p" > "$abs/rail-round-1.md"
  printf '# sentinel STUB do pacote %s\n\nApproved-By: TO-FILL\n' "$p" > "$TPL/$plan/wave-s329-$p-approved.md"
  # patch REAL, gerado pelo próprio git: `git apply --reverse --check` sobre
  # ele é uma das provas que o MORNING usa para reconhecer um pacote já landado.
  printf 'pacote %s aplicado\n' "$p" > "$TPL/$cer/APPLIED-$p.txt"
  ( cd "$TPL" && git add -N -- "$cer/APPLIED-$p.txt" >/dev/null 2>&1 \
      && git diff -- "$cer/APPLIED-$p.txt" > "$SCRATCH/$p.patch" \
      && git reset -q -- "$cer/APPLIED-$p.txt" >/dev/null 2>&1 )
  rm -f "$TPL/$cer/APPLIED-$p.txt"
  _safe_cp "$SCRATCH/$p.patch" "$abs/$p.patch" || return 1
  ( cd "$TPL" && git add -- \
      "$plan/OWNER-S329-$p-SIGN.sh" "$plan/OWNER-S329-$p-LAND.sh" \
      "$plan/wave-s329-$p-approved.md" \
      "$cer/finalize-$p.sh" "$cer/COMMIT-MSG-$p.txt" "$cer/$p.patch" "$cer/rail-round-1.md" )
}

_mk_pkg C ".claude/plans/PLAN-185" "--ownership-e2e=defer" 1 || exit 2
_mk_pkg E ".claude/plans/PLAN-169" ""                      0 || exit 2

# Baselines: o C declara o conjunto RED (o MORNING prefere essa fonte); o E
# declara o tempo-limite do Smoke Install. Com o C ausente o MORNING tem de
# cair na tabela RASTREADA que o próprio gate do nightly compara.
printf 'EXPECTED_OWNERSHIP_RED_IDS="OWN-0016 OWN-0024 OWN-0027"\n' \
  > "$TPL/.claude/plans/PLAN-185/s329-ceremony-C/EXPECTED-BASELINE.txt"
printf 'EXPECTED_YML_TIMEOUT_MINUTES=96\n' \
  > "$TPL/.claude/plans/PLAN-169/s329-ceremony-E/EXPECTED-BASELINE.txt"
( cd "$TPL" \
    && git add -- ".claude/plans/PLAN-185/s329-ceremony-C/EXPECTED-BASELINE.txt" \
                  ".claude/plans/PLAN-169/s329-ceremony-E/EXPECTED-BASELINE.txt" \
    && git add -- "$MORNING_REL" \
    && git commit -q -m "test(harness): pacotes stub do harness do MORNING" ) || {
  printf 'commit dos stubs falhou\n' >&2; exit 2; }

DIRTY_TPL="$( git -C "$TPL" status --porcelain | head -5 )"
if [ -n "$DIRTY_TPL" ]; then
  printf '  \033[33mmolde com árvore suja:\033[0m\n%s\n' "$DIRTY_TPL"
fi
printf '  molde pronto: 2 pacotes stub commitados\n'

# --- dublê do `gh` ---------------------------------------------------------
# A seção de CI do MORNING chama `gh run list`. Numa execução real isso é uma
# chamada de REDE: ~2 s cada, resultado diferente a cada minuto, e um `gh`
# lento faria este harness parecer travado. O que se mede aqui é o
# ORQUESTRADOR, não o GitHub — então ele recebe um dublê determinístico, na
# mesma lógica dos pacotes stub. O cenário S8b, que roda com um PATH mínimo,
# exercita de graça o caminho "o gh não está instalado".
FAKEBIN="$SCRATCH/bin"
mkdir -p "$FAKEBIN"
cat > "$FAKEBIN/gh" <<'GHSTUB'
#!/usr/bin/env bash
# Duble de `gh` — gerado por test-morning.sh. Nao fala com a rede.
printf 'completed\tsuccess\tstub do harness\tValidate\tmain\tpush\t0\t1s\n'
exit 0
GHSTUB
chmod +x "$FAKEBIN/gh"

# --- helpers de cenário ----------------------------------------------------
RC=0
MORNING_GPGHOME="$GPG_KEYED"
MORNING_PATH="$FAKEBIN:$PATH"
# `git clone --local` em vez de `cp -R`: o clone usa HARDLINK nos objetos e sai
# em ~6 s onde a cópia levava ~20 s (medido nesta máquina, árvore de 178 MB).
# Com ~20 cenários isso é a diferença entre 2 e 7 minutos de harness.
_new_case() {  # <nome> -> ecoa o diretório
  local d="$SCRATCH/$1"
  rm -rf "$d"
  if [ -L "$d" ]; then printf 'destino é SYMLINK: %s\n' "$d" >&2; return 1; fi
  git clone --quiet --local "$TPL" "$d" >/dev/null 2>&1 || return 1
  # O clone aponta `origin` para o MOLDE. Removido: nenhum cenário empurra, e
  # o S12 traz um repositório NU próprio quando precisa de um origin.
  git -C "$d" remote remove origin >/dev/null 2>&1 || printf ''
  git -C "$d" config user.email "morning-selftest@example.invalid" >/dev/null 2>&1
  git -C "$d" config user.name  "morning selftest" >/dev/null 2>&1
  printf '%s' "$d"
}
_drop_pkg() {  # <dir> <P> — remove os DOIS scripts do pacote (ausência real)
  local d="$1" p="$2" plan
  case "$p" in C) plan=".claude/plans/PLAN-185" ;; E) plan=".claude/plans/PLAN-169" ;; esac
  rm -f "$d/$plan/OWNER-S329-$p-SIGN.sh" "$d/$plan/OWNER-S329-$p-LAND.sh"
  # O pacote tem de sumir do PONTO DE VISTA DO GIT também: um arquivo apagado
  # e não commitado deixaria a árvore suja e o MORNING abortaria em 3 — que é
  # o comportamento certo dele, mas não é o cenário que quero medir aqui.
  ( cd "$d" && git commit -q -a -m "test: remove o pacote $p" ) || printf ''
}
# shellcheck disable=SC2086  # ENVSPEC é do harness e a divisão em palavras é o objetivo
_run_morning_env() {  # <dir> <saída> <ENVSPEC> [args...]
  local d="$1" out="$2" spec="$3"; shift 3
  ( cd "$d" && env $spec \
      GNUPGHOME="$MORNING_GPGHOME" PATH="$MORNING_PATH" \
      MORNING_TEST_ORDER_FILE="$d.order" \
      bash "$d/$MORNING_REL" "$@" ) > "$out" 2>&1
  RC=$?
}
_run_morning() {  # <dir> <saída> [args...]
  local d="$1" out="$2"; shift 2
  _run_morning_env "$d" "$out" "" "$@"
}
_order_of() {  # <dir> — sequência de etapas executadas, numa linha
  [ -f "$1.order" ] && tr '\n' ' ' < "$1.order" | sed 's/ $//'
}
_set_rail() {  # <dir> <P> <arquivo> <veredito>
  local d="$1" p="$2" f="$3" v="$4" plan
  case "$p" in C) plan=".claude/plans/PLAN-185" ;; E) plan=".claude/plans/PLAN-169" ;; esac
  printf '# Pacote %s — %s (STUB)\n\nRail-Verdict: %s\n' "$p" "$f" "$v" \
    > "$d/$plan/s329-ceremony-$p/$f"
  ( cd "$d" && git add -- "$plan/s329-ceremony-$p/$f" && git commit -q -m "test: rail $f=$v" ) || printf ''
}

# ===========================================================================
_head "S1 — os dois pacotes presentes (--dry-run)"
# ===========================================================================
D1="$( _new_case s1 )" || exit 2
_run_morning "$D1" "$SCRATCH/s1.out" --dry-run
_assert_rc 0 "$RC" "rc 0: nada ausente, nada pulado"
_assert_has "$SCRATCH/s1.out" "PACOTE C (PLAN-185" "abriu o pacote C"
_assert_has "$SCRATCH/s1.out" "PACOTE E (PLAN-169" "abriu o pacote E"
_assert_has "$SCRATCH/s1.out" "LAND --ownership-e2e=defer" "derivou a flag obrigatória do LAND do C"
_assert_has "$SCRATCH/s1.out" "a última (rail-round-1.md) é APPROVE" "o portão do rail leu o veredito"
_assert_has "$SCRATCH/s1.out" "OWN-0016 OWN-0024 OWN-0027" "leu o conjunto RED do EXPECTED-BASELINE do C"
_assert_has "$SCRATCH/s1.out" "gpg disponível" "o preflight viu a chave descartável"
_assert_has "$SCRATCH/s1.out" "RESUMO" "imprimiu o resumo"
_assert_hasnt "$SCRATCH/s1.out" "Validate       esperado VERDE" "NÃO promete Validate verde"
_assert_hasnt "$SCRATCH/s1.out" "esperado VERDE." "não promete verde em lugar nenhum"
_assert_eq "" "$( _order_of "$D1" )" "--dry-run global não executou NENHUM script de pacote"
ORD1="$( grep -n 'PACOTE [CE] (' "$SCRATCH/s1.out" | sed 's/.*PACOTE \([CE]\) (.*/\1/' | tr -d '\n' )"
_assert_eq "CE" "$ORD1" "ordem impressa é C → E"

# ===========================================================================
_head "S2 — pacote C ausente (aviso alto, E segue)"
# ===========================================================================
D2="$( _new_case s2 )" || exit 2
_drop_pkg "$D2" C
_run_morning "$D2" "$SCRATCH/s2.out" --dry-run
_assert_rc 7 "$RC" "rc 7: terminou sem vermelho, mas nem tudo rodou"
_assert_has "$SCRATCH/s2.out" "ATENÇÃO" "o aviso é GRANDE, não uma linha perdida"
_assert_has "$SCRATCH/s2.out" "pacote C AUSENTE" "detectou a ausência do C em runtime"
_assert_has "$SCRATCH/s2.out" "Isso NÃO é um erro" "disse ao Owner que a ausência não é culpa dele"
_assert_has "$SCRATCH/s2.out" "PACOTE E (PLAN-169" "seguiu para o E mesmo assim"
_assert_has "$SCRATCH/s2.out" "ownership-expected-reds.txt" "caiu na tabela RASTREADA do nightly para o conjunto RED"
_assert_has "$SCRATCH/s2.out" "OWN-0016" "a tabela rastreada rendeu os ids"
_assert_has "$SCRATCH/s2.out" "96 minutos" "o aviso de tempo-limite veio do EXPECTED-BASELINE do E"

# ===========================================================================
_head "S3 — pacote E ausente"
# ===========================================================================
D3="$( _new_case s3 )" || exit 2
_drop_pkg "$D3" E
_run_morning "$D3" "$SCRATCH/s3.out" --dry-run
_assert_rc 7 "$RC" "rc 7"
_assert_has "$SCRATCH/s3.out" "pacote E AUSENTE" "detectou a ausência do E"
_assert_has "$SCRATCH/s3.out" "PACOTE C (PLAN-185" "o C rodou antes"
_assert_hasnt "$SCRATCH/s3.out" "96 minutos" "sem o E, não fala do tempo-limite que só ele muda"

# ===========================================================================
_head "S4 — caminho feliz de verdade (stubs, sem --dry-run)"
# ===========================================================================
D4="$( _new_case s4 )" || exit 2
_run_morning "$D4" "$SCRATCH/s4.out"
_assert_rc 0 "$RC" "rc 0: os 2 pacotes landaram"
_assert_eq "FINALIZE-C SIGN-C LAND-C-dry1 LAND-C-dry0 FINALIZE-E SIGN-E LAND-E-dry1 LAND-E-dry0" \
  "$( _order_of "$D4" )" "sequência exata: finalize→SIGN→ensaio→land, na ordem C E"
_assert_has "$SCRATCH/s4.out" "LANDADO" "reportou o land"
_assert_has "$SCRATCH/s4.out" "não tem upstream configurado" "degradou o teste de push sem upstream"
_assert_has "$SCRATCH/s4.out" "O CI roda SOZINHO" "lembrou que o CI segue sem o Owner"
LOGN=0
for _lf in "$D4/.claude/plans/PLAN-185/s329-ceremony-main"/morning-*.log; do
  [ -f "$_lf" ] && LOGN=$(( LOGN + 1 ))
done
if [ "$LOGN" -ge 1 ]; then _pass "gravou o log da execução em s329-ceremony-main/ ($LOGN arquivo)"; else
  _fail "não gravou o log da execução em s329-ceremony-main/"; fi
PHASEN=0; PHASE_MISS=""
for _ph in step-C-finalize step-C-sign step-C-land-dry step-C-land \
           step-E-finalize step-E-sign step-E-land-dry step-E-land; do
  if [ -f "$D4/.claude/plans/PLAN-185/s329-ceremony-main/$_ph.log" ]; then
    PHASEN=$(( PHASEN + 1 ))
  else
    PHASE_MISS="$PHASE_MISS $_ph"
  fi
done
_assert_eq "8" "$PHASEN" "um log por FASE (faltaram:${PHASE_MISS:- nenhum})"
COMMITS="$( git -C "$D4" log --format=%s -n 6 | grep -c 'stub do pacote' )"
_assert_eq "2" "$COMMITS" "2 commits de cerimônia no clone"

# ===========================================================================
_head "S5 — segunda passada sobre o S4: idempotente"
# ===========================================================================
rm -f "$D4.order"
_run_morning "$D4" "$SCRATCH/s5.out"
_assert_rc 0 "$RC" "rc 0 na segunda passada"
IDEM="$( _count_in "$SCRATCH/s5.out" "JÁ está no repositório — nada a fazer" )"
_assert_eq "2" "$IDEM" "reconheceu os 2 pacotes como já landados"
_assert_eq "" "$( _order_of "$D4" )" "não re-executou NENHUM script de pacote"
# Um "já landado" errado pula o pacote em silêncio. O MORNING tem de dizer qual
# das três provas respondeu, senão o erro é invisível.
PROOFS="$( _count_in "$SCRATCH/s5.out" "como eu sei:" )"
_assert_eq "2" "$PROOFS" "declarou, para cada pacote, COMO sabe que já estava landado"
_assert_has "$SCRATCH/s5.out" "está commitada (só o LAND a commita)" \
  "a prova usada é a assinatura commitada — o mecanismo que só o land produz"

# ===========================================================================
_head "S6 — SIGN do C devolve 1: para no PRIMEIRO vermelho"
# ===========================================================================
D6="$( _new_case s6 )" || exit 2
_run_morning_env "$D6" "$SCRATCH/s6.out" "STUB_SIGN_RC_C=1"
_assert_rc 12 "$RC" "rc 12 = pacote C, etapa SIGN"
_assert_has "$SCRATCH/s6.out" "pacote C, etapa SIGN" "nomeou pacote e etapa"
_assert_has "$SCRATCH/s6.out" "--from C" "imprimiu o comando de retomada"
_assert_has "$SCRATCH/s6.out" "No pinentry" "trouxe a orientação do modo de falha conhecido"
_assert_has "$SCRATCH/s6.out" "RESUMO" "imprimiu o resumo mesmo parando"
_assert_hasnt "$SCRATCH/s6.out" "PACOTE E (PLAN-169" "NÃO seguiu para o pacote E"
_assert_eq "FINALIZE-C SIGN-C" "$( _order_of "$D6" )" "executou só finalize+SIGN do C e parou"

# ===========================================================================
_head "S6b — falha de pinentry: reinicia o agente e tenta UMA vez, só uma"
# ===========================================================================
D6B="$( _new_case s6b )" || exit 2
_run_morning_env "$D6B" "$SCRATCH/s6b.out" "STUB_SIGN_PINENTRY_C=1"
_assert_rc 12 "$RC" "rc 12: parou no SIGN do C depois da retentativa"
_assert_has "$SCRATCH/s6b.out" "reiniciando o agente do GPG" "detectou a falha de pinentry"
_assert_eq "FINALIZE-C SIGN-C SIGN-C" "$( _order_of "$D6B" )" "tentou exatamente DUAS vezes, não um laço"

# ===========================================================================
_head "S7 — rail em REJECT: PULA o pacote e segue; não assina, não re-baseia"
# ===========================================================================
# Um rail em REJECT não é um vermelho de etapa: repetir o comando bate na MESMA
# parede. Se ele parasse a manhã, o pacote APROVADO não landaria e o Owner
# receberia um `--from` que não pode funcionar. Medido na árvore viva em
# 2026-08-26: o C estava em REJECT e o E em APPROVE — exatamente esta forma.
D7="$( _new_case s7 )" || exit 2
_set_rail "$D7" C "rail-round-2.md" "REJECT"
_run_morning "$D7" "$SCRATCH/s7.out"
_assert_rc 7 "$RC" "rc 7: pulado, não vermelho"
_assert_has "$SCRATCH/s7.out" "ATENÇÃO" "o aviso é GRANDE"
_assert_has "$SCRATCH/s7.out" "a revisão cruzada NÃO aprovou" "nomeou a razão"
_assert_has "$SCRATCH/s7.out" "terminou em \`REJECT\`" "nomeou o veredito encontrado"
_assert_has "$SCRATCH/s7.out" "rail-round-2.md" "nomeou o registro que decidiu"
_assert_has "$SCRATCH/s7.out" "NÃO se resolve repetindo o comando" "disse que retomar não adianta"
_assert_hasnt "$SCRATCH/s7.out" "--from C" "NÃO ofereceu uma retomada que bateria na mesma parede"
_assert_has "$SCRATCH/s7.out" "PACOTE E (PLAN-169" "o pacote APROVADO seguiu mesmo assim"
_assert_eq "FINALIZE-E SIGN-E LAND-E-dry1 LAND-E-dry0" "$( _order_of "$D7" )" \
  "o C não rodou NEM o finalize; o E landou inteiro"
if [ -f "$D7/.claude/plans/PLAN-185/wave-s329-C-approved.md.asc" ]; then
  _fail "assinou o C apesar do rail em REJECT"
else
  _pass "nenhuma assinatura do C foi produzida"
fi

# ===========================================================================
_head "S7b — rail-round-10 vs rail-round-2: escolhe por NÚMERO, não por nome"
# ===========================================================================
# Controle positivo do bug lexicográfico: como texto, `rail-round-10` vem ANTES
# de `rail-round-2`, e um MORNING que ordenasse por nome leria o REJECT da
# rodada 2 como se fosse o último veredito e abortaria.
D7B="$( _new_case s7b )" || exit 2
_set_rail "$D7B" C "rail-round-2.md"  "REJECT"
_set_rail "$D7B" C "rail-round-10.md" "APPROVE"
_run_morning "$D7B" "$SCRATCH/s7b.out" --dry-run
_assert_rc 0 "$RC" "seguiu: a ÚLTIMA rodada (10) é APPROVE"
_assert_has "$SCRATCH/s7b.out" "a última (rail-round-10.md) é APPROVE" "elegeu a rodada 10, não a 2"
_assert_hasnt "$SCRATCH/s7b.out" "terminou em \`REJECT\`" "não leu o veredito da rodada errada"

# ===========================================================================
_head "S7c — nenhum registro de rail"
# ===========================================================================
D7C="$( _new_case s7c )" || exit 2
rm -f "$D7C/.claude/plans/PLAN-185/s329-ceremony-C/rail-round-1.md"
( cd "$D7C" && git commit -q -a -m "test: sem registro de rail" ) || printf ''
_run_morning "$D7C" "$SCRATCH/s7c.out"
_assert_rc 7 "$RC" "rc 7: pulado por falta de revisão registrada"
_assert_has "$SCRATCH/s7c.out" "nenhuma revisão cruzada foi registrada" "nomeou a razão"
_assert_has "$SCRATCH/s7c.out" "PACOTE E (PLAN-169" "o outro pacote seguiu"
_assert_eq "FINALIZE-E SIGN-E LAND-E-dry1 LAND-E-dry0" "$( _order_of "$D7C" )" \
  "o C não executou nada; o E landou inteiro"

# ===========================================================================
_head "S8a — GNUPGHOME sem chave secreta"
# ===========================================================================
D8="$( _new_case s8a )" || exit 2
MORNING_GPGHOME="$GPG_EMPTY"
_run_morning "$D8" "$SCRATCH/s8a.out"
MORNING_GPGHOME="$GPG_KEYED"
_assert_rc 12 "$RC" "rc 12: parou no passo da assinatura"
_assert_has "$SCRATCH/s8a.out" "não vou conseguir assinar" "avisou no preflight"
_assert_has "$SCRATCH/s8a.out" "NENHUMA chave secreta" "nomeou a causa exata"
_assert_has "$SCRATCH/s8a.out" "gpg --list-secret-keys" "deu o comando de diagnóstico"
_assert_eq "" "$( _order_of "$D8" )" "parou ANTES do finalize — nada foi re-baseado"

# ===========================================================================
_head "S8b — o programa \`gpg\` fora do PATH"
# ===========================================================================
if env PATH="/usr/bin:/bin:/usr/sbin:/sbin" sh -c 'command -v git >/dev/null && command -v python3 >/dev/null && ! command -v gpg >/dev/null'; then
  D8B="$( _new_case s8b )" || exit 2
  MORNING_PATH="/usr/bin:/bin:/usr/sbin:/sbin"
  _run_morning "$D8B" "$SCRATCH/s8b.out"
  MORNING_PATH="$PATH"
  _assert_rc 12 "$RC" "rc 12: parou no passo da assinatura"
  _assert_has "$SCRATCH/s8b.out" "não está instalado" "nomeou a ausência do programa"
  _assert_eq "" "$( _order_of "$D8B" )" "parou ANTES do finalize"
else
  _note "pulado: neste PATH mínimo faltam git/python3 ou sobra o gpg — o cenário mediria outra coisa"
fi

# ===========================================================================
_head "S9 — --from e --only"
# ===========================================================================
D9="$( _new_case s9 )" || exit 2
_run_morning "$D9" "$SCRATCH/s9.out" --dry-run --from E
_assert_rc 7 "$RC" "rc 7: o C foi pulado por --from"
_assert_has "$SCRATCH/s9.out" "pulado por --from E" "marcou o C como pulado"
_assert_has "$SCRATCH/s9.out" "PACOTE E (PLAN-169" "rodou o E"
_assert_hasnt "$SCRATCH/s9.out" "PACOTE C (PLAN-185" "não abriu o pacote C"
D9B="$( _new_case s9b )" || exit 2
_run_morning "$D9B" "$SCRATCH/s9b.out" --dry-run --only C
_assert_rc 7 "$RC" "rc 7: só um pacote rodou"
_assert_has "$SCRATCH/s9b.out" "PACOTE C (PLAN-185" "rodou o C"
_assert_hasnt "$SCRATCH/s9b.out" "PACOTE E (PLAN-169" "não rodou o E"

# ===========================================================================
_head "S10 — pré-condições e uso"
# ===========================================================================
DA="$( _new_case s10a )" || exit 2
( cd "$DA" && git checkout -q -b nao-main )
_run_morning "$DA" "$SCRATCH/s10a.out"
_assert_rc 3 "$RC" "rc 3 fora do main"
_assert_has "$SCRATCH/s10a.out" "não em \"main\"" "nomeou a pré-condição"
DB="$( _new_case s10b )" || exit 2
printf 'sujeira\n' >> "$DB/README.md"
_run_morning "$DB" "$SCRATCH/s10b.out" --dry-run
_assert_rc 3 "$RC" "rc 3 com árvore suja"
_assert_has "$SCRATCH/s10b.out" "modificações RASTREADAS" "nomeou a árvore suja"
_run_morning "$DB" "$SCRATCH/s10c.out" --from Z
_assert_rc 2 "$RC" "rc 2 para pacote inexistente em --from"
_run_morning "$DB" "$SCRATCH/s10d.out" --from C --only E
_assert_rc 2 "$RC" "rc 2 para --from junto com --only"

# ===========================================================================
_head "S11 — docs/threat-model.md sujo pelo checker de frescor"
# ===========================================================================
# Controle POSITIVO com o instrumento REAL: quem suja o arquivo é
# `check-threat-model-freshness.py`, não um sed do harness. Se um dia ele parar
# de flipar, o cenário reprova aqui em vez de passar vazio.
TM="docs/threat-model.md"
DC="$( _new_case s11a )" || exit 2
( cd "$DC" && python3 .claude/scripts/check-threat-model-freshness.py ) > "$SCRATCH/s11a.checker" 2>&1
TM_DIRTY="$( git -C "$DC" status --porcelain=v1 -- "$TM" )"
if [ -n "$TM_DIRTY" ]; then
  _pass "o checker real sujou $TM (controle positivo vivo)"
else
  _fail "o checker NÃO sujou $TM — o cenário virou vazio; a pergunta do instrumento envelheceu"
fi
_run_morning "$DC" "$SCRATCH/s11a.out" --dry-run
_assert_rc 0 "$RC" "seguiu normalmente depois de reverter"
_assert_has "$SCRATCH/s11a.out" "estava modificado e eu REVERTI" "anunciou a reversão e a razão"
_assert_has "$SCRATCH/s11a.out" "check-threat-model-freshness.py" "nomeou quem escreveu no arquivo"
_assert_eq "" "$( git -C "$DC" status --porcelain=v1 -- "$TM" )" "o arquivo voltou ao original"

# (b) mesma troca de status MAIS outra linha: não é o flip puro ⇒ não reverte
DD="$( _new_case s11b )" || exit 2
( cd "$DD" && python3 .claude/scripts/check-threat-model-freshness.py ) >/dev/null 2>&1
printf '\nlinha que alguem escreveu de verdade\n' >> "$DD/$TM"
_run_morning "$DD" "$SCRATCH/s11b.out" --dry-run
_assert_rc 3 "$RC" "abortou: o diff não é só a troca de status"
_assert_has "$SCRATCH/s11b.out" "docs/threat-model.md" "nomeou o path no abort"
_assert_has "$SCRATCH/s11b.out" "NÃO é só a troca de status" "explicou por que não reverteu"
_assert_has "$SCRATCH/s11b.out" "git checkout -- docs/threat-model.md" "deu o comando de recuperação"
if [ -n "$( git -C "$DD" status --porcelain=v1 -- "$TM" )" ]; then
  _pass "NÃO reverteu o arquivo com conteúdo real dentro"
else
  _fail "reverteu um arquivo que tinha mudança de verdade — destruiu trabalho"
fi

# (c) DIREÇÃO INVERSA (stale -> accepted): é edição deliberada de gente, não do
# checker — que só escreve accepted -> stale. Reverter aqui destruiria o
# trabalho de quem RE-ACEITOU o modelo de ameaças.
DG="$( _new_case s11c )" || exit 2
( cd "$DG" && python3 .claude/scripts/check-threat-model-freshness.py ) >/dev/null 2>&1
( cd "$DG" && git commit -q -a -m "test: threat-model em stale no HEAD" ) || printf ''
if [ -L "$DG/$TM" ]; then _fail "destino é SYMLINK: $DG/$TM"; else
  sed 's/^\*\*Status:\*\* stale$/**Status:** accepted/' "$DG/$TM" > "$DG/$TM.tmp"
  mv "$DG/$TM.tmp" "$DG/$TM"
fi
INV="$( git -C "$DG" diff -U0 -- "$TM" | grep -c -F -e '-**Status:** stale' -e '+**Status:** accepted' )"
case "${INV:-0}" in ''|*[!0-9]*) INV=0 ;; esac
_assert_eq "2" "$INV" "o diff plantado é mesmo o inverso (stale -> accepted, 1 linha)"
_run_morning "$DG" "$SCRATCH/s11c.out" --dry-run
_assert_rc 3 "$RC" "abortou: a direção inversa NÃO é a do checker"
_assert_hasnt "$SCRATCH/s11c.out" "eu REVERTI" "não reverteu"
if [ -n "$( git -C "$DG" status --porcelain=v1 -- "$TM" )" ]; then
  _pass "preservou a re-aceitação deliberada (stale -> accepted intacta)"
else
  _fail "DESTRUIU uma edição deliberada: reverteu um flip stale -> accepted"
fi

# ===========================================================================
_head "S12 — checkout ATRÁS do origin"
# ===========================================================================
# O land empurra. Se o origin já andou, o push seria recusado DEPOIS de gastar
# a assinatura e a bateria inteira. O origin aqui é um repositório NU do
# scratchpad — nunca o repo vivo.
DH="$( _new_case s12 )" || exit 2
BARE="$SCRATCH/s12-origin.git"
git init --bare --quiet "$BARE"
git -C "$BARE" symbolic-ref HEAD refs/heads/main
git -C "$DH" remote add origin "$BARE"
git -C "$DH" push --quiet origin main
WORK="$SCRATCH/s12-work"
git clone --quiet "$BARE" "$WORK"
git -C "$WORK" config user.email "other@example.invalid"
git -C "$WORK" config user.name  "outra pessoa"
printf 'commit de outra pessoa\n' >> "$WORK/README.md"
git -C "$WORK" commit -q -a -m "test: alguem empurrou antes de voce"
git -C "$WORK" push --quiet origin main
_run_morning "$DH" "$SCRATCH/s12.out" --dry-run
_assert_rc 3 "$RC" "rc 3: atrás do origin"
_assert_has "$SCRATCH/s12.out" "ATRÁS do origin/main" "nomeou a pré-condição"
_assert_has "$SCRATCH/s12.out" "push recusado" "explicou a consequência"
_assert_eq "" "$( _order_of "$DH" )" "não executou nada"

# ===========================================================================
_head "S13 — pacote pela METADE (só um dos dois scripts)"
# ===========================================================================
DI="$( _new_case s13 )" || exit 2
rm -f "$DI/.claude/plans/PLAN-185/OWNER-S329-C-SIGN.sh"
( cd "$DI" && git commit -q -a -m "test: pacote C sem o SIGN" ) || printf ''
_run_morning "$DI" "$SCRATCH/s13.out" --dry-run
_assert_rc 7 "$RC" "rc 7: pacote incompleto conta como pulado"
_assert_has "$SCRATCH/s13.out" "pacote C INCOMPLETO" "distinguiu incompleto de ausente"
_assert_has "$SCRATCH/s13.out" "OWNER-S329-C-LAND.sh" "listou o script que existe"
_assert_has "$SCRATCH/s13.out" "PACOTE E (PLAN-169" "seguiu para o E"

# ===========================================================================
_head "RESULTADO"
# ===========================================================================
printf '\n  PASS=%s  FAIL=%s\n' "$PASS" "$FAIL"
if [ -n "$CS_BAD" ]; then
  printf '  \033[33mMODO UNCOMMITTED\033[0m — o MORNING veio da árvore viva, não do HEAD.\n'
  printf '  Este verde NÃO é o verde do contrato; repita depois de commitar.\n'
fi
printf '  artefatos: %s\n\n' "$SCRATCH"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
