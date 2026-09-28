#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: ensaio de UM uso da relmeta-142
# (PLAN-193 W6); roda o derive e o OWNER-RELMETA142-SIGN.sh deste diretório
# numa cópia descartável, nunca no checkout de onde foi chamado.
# rehearse-relmeta142.sh — ensaio PONTA A PONTA da relmeta-142.
#
#   bash .claude/plans/PLAN-193/relmeta/rehearse-relmeta142.sh             # sobre o main (manhã, pós-lands)
#   bash .claude/plans/PLAN-193/relmeta/rehearse-relmeta142.sh --sim FILE  # sobre um HEAD SIMULADO
#
# O que faz, tudo dentro de um diretório novo (mktemp) sob $REHEARSE_BASE
# (padrão: $TMPDIR):
#   1. clona o `main` deste repositório num remoto «bare» descartável cujo
#      caminho contém o slug que o P0 exige, e dele um checkout de trabalho;
#      HOME, GNUPGHOME (chave descartável SEM senha) e TMPDIR descartáveis,
#      ambiente limpo (env -i) e pseudo-TTY (`script`) no run real;
#   2. com --sim FILE: cria uma tag FALSA v1.4.1 no HEAD clonado (se a real não
#      existir) e roda FILE (bash, com WORK e SRC_REPO no ambiente) para montar
#      os lands da 1.4.2 por cima; sem --sim, exige a v1.4.1 real no clone;
#   3. põe a chave descartável no allowlist e no registro de signatários DO
#      CLONE, e os materiais deste diretório (os de trabalho, commitados ou
#      não) com o sentinel em RASCUNHO e sem patch — o ensaio deriva do zero;
#   4. roda os controles: âncoras (vermelho na v1.4.1, verde no HEAD), patch
#      nunca derivado, derivação, idempotência (antes e depois do commit dos
#      materiais), SIGN --dry-run, três patches VELHOS recusados pelo nome,
#      TERM durante a bateria (restaura), o run REAL até o commit — nunca o
#      push —, re-run recusado, o --yes do probe GPG (vermelho sem, verde com)
#      e o bump --dry-run do driver já em 1.4.2;
#   5. imprime o placar; sai 0 só se todos os itens passarem.
#
# O único caminho fora de $REHEARSE_BASE é um diretório curto para os sockets
# do gpg-agent (o macOS limita o caminho de socket a ~104 bytes): mktemp sob
# $REHEARSE_SOCK_BASE (padrão: /tmp), esvaziado e removido no fim.
set -euo pipefail

_genv=""
for _v in $(git rev-parse --local-env-vars); do
  if [ -n "${!_v+x}" ]; then _genv="$_genv $_v"; fi
done
[ -z "$_genv" ] || { printf 'variáveis git herdadas:%s — rode sem elas (unset%s)\n' "$_genv" "$_genv" >&2; exit 2; }

SIM=""
case "$#:${1:-}" in
  0:) ;;
  2:--sim) SIM=$(cd "$(dirname "$2")" && pwd -P)/$(basename "$2"); [ -f "$SIM" ] || { printf 'sim ausente: %s\n' "$2" >&2; exit 2; } ;;
  *) printf 'uso: bash %s [--sim FILE]\n' "$0" >&2; exit 2 ;;
esac

PACK_DIR=$(cd "$(dirname "$0")" && pwd -P)
SRC_REPO=$(cd "$PACK_DIR/../../../.." && pwd -P)
[ -e "$SRC_REPO/.git" ] || { printf 'não achei o repo em %s\n' "$SRC_REPO" >&2; exit 2; }
SIGN_SRC="$PACK_DIR/OWNER-RELMETA142-SIGN.sh"
const() { sed -n "s/^$1=//p" "$SIGN_SRC" | head -n 1 | sed "s/^'//; s/'\$//"; }
PLAN=$(const PLAN); BASE_TAG=$(const BASE_TAG); PREV_BASE=$(const PREV_BASE)
TARGET_BASE=$(const TARGET_BASE); REMOTE_SLUG=$(const REMOTE_SLUG)
for v in PLAN BASE_TAG PREV_BASE TARGET_BASE REMOTE_SLUG; do
  [ -n "${!v}" ] || { printf 'constante %s não lida do SIGN\n' "$v" >&2; exit 2; }
done
D=".claude/plans/$PLAN/relmeta"
SIGN_REL="$D/OWNER-RELMETA142-SIGN.sh"
DERIVE_REL="$D/derive-relmeta142.sh"
APPLY_REL="$D/apply-relmeta142-edits.py"
SENT_REL="$D/relmeta142-approved.md"
PATCH_REL="$D/RELMETA142.patch"
PACK_SCRIPTS="apply-relmeta142-edits.py derive-relmeta142.sh OWNER-RELMETA142-SIGN.sh rehearse-relmeta142.sh"
T_REL=.claude/scripts/local/release.sh
T_MAN=.claude/governance/gate-scripts-manifest.txt
T_TST=.claude/scripts/tests/test_release_bump_sites.py

BASE=${REHEARSE_BASE:-${TMPDIR:-/tmp}}
RUN=$(mktemp -d "${BASE%/}/rehearse-relmeta142.XXXXXX")
SOCK=$(mktemp -d "${REHEARSE_SOCK_BASE:-/tmp}/g.XXXXXX")
chmod 700 "$SOCK"
mkdir -p "$RUN/home" "$RUN/tmp" "$RUN/logs" "$RUN/gnupg"
chmod 700 "$RUN/gnupg"
LOGS="$RUN/logs"
PASS=0; FAIL=0; TALLY="$RUN/tally.txt"; : >"$TALLY"
ok() { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$*" | tee -a "$TALLY"; }
ko() { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$*" | tee -a "$TALLY"; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else ko "$d"; fi; }
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }
cleanup() {
  GNUPGHOME="$RUN/gnupg" gpgconf --kill gpg-agent >/dev/null 2>&1 || printf 'aviso: gpg-agent do ensaio não parou\n' >&2
  for s in S.gpg-agent S.gpg-agent.extra S.gpg-agent.browser S.gpg-agent.ssh; do
    if [ -S "$SOCK/$s" ]; then rm -f "$SOCK/$s"; fi
  done
  rmdir "$SOCK" 2>/dev/null || printf 'aviso: %s não ficou vazio\n' "$SOCK" >&2
}
trap 'rc=$?; cleanup; exit $rc' EXIT
printf 'ensaio em %s\n' "$RUN"

TOOLPATH=""
for t in git gpg gpgconf python3 shasum script awk sed bash; do
  d=$(dirname "$(command -v "$t")")
  case ":$TOOLPATH:" in *":$d:"*) ;; *) TOOLPATH="${TOOLPATH:+$TOOLPATH:}$d" ;; esac
done
TOOLPATH="$TOOLPATH:/usr/bin:/bin:/usr/sbin:/sbin"
USERBASE=$(python3 -m site --user-base)
# ambiente limpo: nada do shell (nem CLAUDE_*, nem CEO_*) vaza para a cerimônia
E() {
  env -i HOME="$RUN/home" PATH="$TOOLPATH" GNUPGHOME="$RUN/gnupg" TMPDIR="$RUN/tmp" \
    PYTHONUSERBASE="$USERBASE" PYTHONDONTWRITEBYTECODE=1 TERM=dumb \
    LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 "$@"
}

# ------------------------------------------------ gpg descartável
for s in S.gpg-agent S.gpg-agent.extra S.gpg-agent.browser S.gpg-agent.ssh; do
  printf '%%Assuan%%\nsocket=%s/%s\n' "$SOCK" "$s" >"$RUN/gnupg/$s"
done
E gpg --batch --passphrase '' --quick-gen-key \
  'Rehearsal Throwaway <rehearsal@example.invalid>' ed25519 sign never >"$LOGS/gpg-gen.out" 2>&1
KEY_FPR=$(E gpg --with-colons --list-secret-keys | awk -F: '$1=="fpr"{print $10; exit}')
check "chave descartável gerada no GNUPGHOME do ensaio" [ -n "$KEY_FPR" ]

# ------------------------------------------------ remoto bare + checkout
REMOTE="$RUN/remote/$REMOTE_SLUG.git"
mkdir -p "$(dirname "$REMOTE")"
E git clone -q --bare --no-hardlinks --single-branch --branch main "$SRC_REPO" "$REMOTE"
E git clone -q "$REMOTE" "$RUN/work"
WORK="$RUN/work"
G() { E git -C "$WORK" "$@"; }
G config user.name 'Rehearsal'
G config user.email 'rehearsal@example.invalid'
G config commit.gpgsign false
G config tag.gpgsign false
printf 'main clonado: %s\n' "$(G rev-parse HEAD)"

if [ -n "$SIM" ]; then
  if ! G rev-parse -q --verify "refs/tags/$BASE_TAG" >/dev/null; then
    G tag -a "$BASE_TAG" -m "ENSAIO: tag FALSA do GA (rehearse-relmeta142)" HEAD
    printf 'AVISO: %s ainda não existe — o ensaio usou uma tag FALSA no main clonado\n' "$BASE_TAG"
  fi
  E WORK="$WORK" SRC_REPO="$SRC_REPO" bash "$SIM" >"$LOGS/sim.out" 2>&1 \
    || { tail -n 30 "$LOGS/sim.out"; ko "montagem do HEAD simulado (log: $LOGS/sim.out)"; exit 1; }
  ok "HEAD simulado montado por $(basename "$SIM") ($(G rev-list --count "$BASE_TAG..HEAD") commits sobre $BASE_TAG)"
else
  check "a tag $BASE_TAG real existe no main clonado" G rev-parse -q --verify "refs/tags/$BASE_TAG"
fi

# a chave descartável no allowlist e no registro de signatários DO CLONE
printf '# ENSAIO: chave descartável (rehearse-relmeta142)\n%s\n' "$KEY_FPR" >>"$WORK/.claude/sentinel-signers.txt"
REG="$WORK/.claude/security/sentinel-signers-registry.yaml"
if [ -f "$REG" ]; then
  printf '\n  - key_id: "%s"\n    key_type: "hot"\n    created_at: "2026-09-24T00:00:00Z"\n    expires_at: "2030-01-01T00:00:00Z"\n    revoked_at: null\n    notes: "ENSAIO: chave descartável (rehearse-relmeta142)"\n' "$KEY_FPR" >>"$REG"
fi
G add -- .claude/sentinel-signers.txt
if [ -f "$REG" ]; then G add -- .claude/security/sentinel-signers-registry.yaml; fi
G commit -q -m "ENSAIO: chave descartável no allowlist de signatários do clone"

# os materiais de TRABALHO deste diretório, sentinel em rascunho, sem patch
mkdir -p "$WORK/$D"
for f in $PACK_SCRIPTS relmeta142-approved.md; do
  cp "$PACK_DIR/$f" "$WORK/$D/$f"
  chmod 644 "$WORK/$D/$f"
done
python3 - "$WORK/$SENT_REL" <<'PY'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
for key in ("Anchor-SHA", "Data", "Patch-SHA256", "Derivator-SHA256", "Derived-From", "Scope-Derived"):
    ph = "ANCHOR-PLACEHOLDER" if key == "Anchor-SHA" else ("DATA-PLACEHOLDER" if key == "Data" else "DERIVE-PLACEHOLDER")
    t, n = re.subn(r"^" + key + r":.*$", key + ": " + ph, t, count=1, flags=re.M)
    assert n == 1, key
p.write_text(t, encoding="utf-8")
PY
for f in $PACK_SCRIPTS relmeta142-approved.md; do G add -- "$D/$f"; done
if [ -e "$WORK/$PATCH_REL" ]; then G rm -q -- "$PATCH_REL"; fi
if [ -e "$WORK/$SENT_REL.asc" ]; then G rm -q -- "$SENT_REL.asc"; fi
if ! G diff --cached --quiet; then
  G commit -q -m "ENSAIO: materiais da relmeta-142 ($PLAN; sentinel em rascunho)"
fi
G push -q origin main "refs/tags/$BASE_TAG"
check "checkout de trabalho sincronizado com o remoto do ensaio" [ "$(G rev-parse HEAD)" = "$(G rev-parse origin/main)" ]

# ------------------------------------------------ estáticos
for f in derive-relmeta142.sh OWNER-RELMETA142-SIGN.sh rehearse-relmeta142.sh; do
  check "bash 3.2 -n $f" /bin/bash -n "$WORK/$D/$f"
  m=$(G ls-files --stage -- "$D/$f" | awk '{print $1}')
  check "modo no índice de $f = 100644 (R8)" [ "$m" = "100644" ]
done
python3 - "$WORK/$APPLY_REL" <<'PY' >"$LOGS/compile.out" 2>&1 && ok "o derivador compila (python3)" || ko "o derivador não compila (log: compile.out)"
import sys
compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")
PY
E bash -c "cd '$WORK' && python3 .claude/scripts/check-ceremony-script.py --json" >"$LOGS/lint.json" 2>"$LOGS/lint.err" && LINT_RC=0 || LINT_RC=$?
check "ceremony-lint rc=0 no checkout com o pack rastreado" [ "$LINT_RC" = "0" ]
python3 - "$LOGS/lint.json" "$D" >"$LOGS/lint-pack.out" 2>&1 <<'PY' && ok "ceremony-lint: os 3 scripts do pack rastreados, 0 BLOCKING e 0 ADVISORY" || ko "ceremony-lint nos scripts do pack (log: lint-pack.out)"
import json, sys
d = json.load(open(sys.argv[1])); rel = sys.argv[2]
mine = [f for f in d["files"] if f["file"].startswith(rel + "/")]
print(sorted(f["file"].rsplit("/", 1)[1] for f in mine))
assert len(mine) == 3, len(mine)
for f in mine:
    print(f["file"], f["tracked"], f["findings"])
    assert f["tracked"], f["file"]
    assert not f["findings"], f["findings"]
PY

# ------------------------------------------------ âncoras da headline
E git -C "$WORK" worktree add -q --detach "$RUN/base" "$BASE_TAG" >"$LOGS/base-wt.out" 2>&1
E python3 "$WORK/$APPLY_REL" --repo "$RUN/base" --claims-only >"$LOGS/claims-base.out" 2>&1 && CB=0 || CB=$?
check "âncoras sobre a $BASE_TAG: rc=1 (vermelho) e a sonda do FN-04 ACHA os bytes do canário gravados no PreToolUse" \
  eval '[ "$CB" = "1" ] && grep -q "^FAIL  \[fn04\].*gravou os bytes do scriptPath" "$LOGS/claims-base.out"'
E git -C "$WORK" worktree remove --force "$RUN/base" >>"$LOGS/base-wt.out" 2>&1 || printf 'aviso: worktree da base ficou\n'
E python3 "$WORK/$APPLY_REL" --repo "$WORK" --claims-only >"$LOGS/claims-head.out" 2>&1 && CH=0 || CH=$?
NCLAIMS=$(E python3 -c 'import importlib.util, sys
s = importlib.util.spec_from_file_location("a", sys.argv[1]); m = importlib.util.module_from_spec(s)
s.loader.exec_module(m); print(len(m.CLAIMS))' "$WORK/$APPLY_REL")
check "âncoras sobre o HEAD: rc=0 e $NCLAIMS PASS, uma por âncora do derivador (log: claims-head.out)" \
  eval '[ "$CH" = "0" ] && [ "$NCLAIMS" -ge 7 ] && [ "$(grep -c "^PASS  " "$LOGS/claims-head.out")" = "$NCLAIMS" ]'

# ------------------------------------------------ runner da cerimônia
state_clean() {  # a árvore voltou exatamente ao HEAD: nada rastreado mudou, sem .asc
  [ -z "$(G status --porcelain --untracked-files=no)" ] \
    && [ ! -e "$WORK/$SENT_REL.asc" ] \
    && G diff --quiet HEAD -- "$SENT_REL" "$T_REL" "$T_MAN" "$T_TST"
}
# O Enter do run real chega por um PIPE que o alimentador mantém ABERTO até a
# cerimônia sair: o `script` do macOS converte o fim de um stdin em ^D (medido:
# um arquivo com "\n" chega ao `read` como EOF) e recusa um FIFO nomeado como
# stdin (medido: «tcgetattr/ioctl: Operation not supported on socket»).
# FEED_ANSWER é o que o alimentador digita no prompt (padrão: assino);
# FEED_EARLY, se não vazio, é digitado CEDO — quando o passo 2 começa, antes do
# prompt existir — para provar que a cerimônia o descarta.
FEED_ANSWER=assino
FEED_EARLY=""
feeder() {  # feeder <nome> — a resposta no prompt; fecha o pipe quando o passo 4 começou ou a cerimônia acabou
  local i=0 sent=0 early=0
  while [ "$i" -lt 2400 ]; do
    if [ -n "$FEED_EARLY" ] && [ "$early" = "0" ] && grep -qF "2/8 re-derivar" "$LOGS/$1.log" 2>/dev/null; then
      printf '%s\n' "$FEED_EARLY"; early=1
    fi
    if [ "$sent" = "0" ] && grep -qF "digite  assino" "$LOGS/$1.log" 2>/dev/null; then
      printf '%s\n' "$FEED_ANSWER"; sent=1
    fi
    if [ "$sent" = "1" ] && grep -qF "4/8 Anchor-SHA" "$LOGS/$1.log" 2>/dev/null; then return 0; fi
    if grep -qE "FAIL:|Ensaio OK|COMMITADA|RESTAURADA" "$LOGS/$1.log" 2>/dev/null; then return 0; fi
    sleep 0.5; i=$((i + 1))
  done
}
run_sign() {  # run_sign <nome> [--dry-run] — pseudo-TTY; Enter pelo pipe do alimentador
  local name="$1" rc=0
  shift
  : >"$LOGS/$name.log"
  feeder "$name" | E bash -c "cd '$WORK' && script -q /dev/null bash '$SIGN_REL' $*" \
    >"$LOGS/$name.log" 2>&1 || rc=$?
  printf '%s' "$rc"
}
expect_abort() {  # expect_abort <nome> <padrão esperado no log> [--dry-run]
  local name="$1" pat="$2" rc
  shift 2
  rc=$(run_sign "$name" "$@")
  if [ "$rc" != "0" ] && grep -qF -- "$pat" "$LOGS/$name.log" && state_clean; then
    ok "$name: abortou (rc=$rc) com «${pat}» e árvore intacta"
  else
    ko "$name: rc=$rc; padrão «${pat}» $(grep -qF -- "$pat" "$LOGS/$name.log" && printf 'presente' || printf 'AUSENTE'); árvore $(state_clean && printf 'intacta' || printf 'SUJA') (log: $LOGS/$name.log)"
  fi
}
derive() {  # derive <nome> [--commit] — ecoa o rc
  local name="$1" rc=0
  shift
  E bash -c "cd '$WORK' && bash '$DERIVE_REL' $*" >"$LOGS/$name.log" 2>&1 || rc=$?
  printf '%s' "$rc"
}

# ------------------------------------------------ derivação
expect_abort "c01-nunca-derivado" "nunca foi derivado" --dry-run
RC=$(derive d1)
check "derive: rc=0, patch gravado e as 4 linhas do sentinel preenchidas (log: d1.log)" \
  eval '[ "$RC" = "0" ] && [ -s "$WORK/$PATCH_REL" ] && ! grep -qE "^(Patch-SHA256|Derivator-SHA256|Derived-From|Scope-Derived): DERIVE-PLACEHOLDER" "$WORK/$SENT_REL"'
check "derive: o patch aplica sobre o HEAD" G apply --check "$PATCH_REL"
check "derive: o patch toca exatamente os 3 alvos" \
  eval '[ "$(G apply --numstat "$PATCH_REL" | awk "{print \$3}" | sort | tr "\n" " ")" = "$(printf "%s\n" "$T_MAN" "$T_REL" "$T_TST" | sort | tr "\n" " ")" ]'
P1=$(sha256f "$WORK/$PATCH_REL"); S1=$(sha256f "$WORK/$SENT_REL")
RC=$(derive d2)
check "derive idempotente: 2.ª rodada «inalterado», patch e sentinel byte a byte iguais" \
  eval '[ "$RC" = "0" ] && grep -q "^inalterado" "$LOGS/d2.log" && [ "$(sha256f "$WORK/$PATCH_REL")" = "$P1" ] && [ "$(sha256f "$WORK/$SENT_REL")" = "$S1" ]'
PRE=$(G rev-parse HEAD)
# um caminho FORA do pack no índice: recusa com a rota, sem commitar nem mexer no índice
printf '\n' >>"$WORK/README.md"
G add -- README.md
RC=$(derive c10-fora-do-pack --commit)
check "c10: derive --commit com caminho fora de $D no índice recusa com a rota, sem commit, índice intacto (log: c10-fora-do-pack.log)" \
  eval '[ "$RC" != "0" ] && grep -qF "FORA de $D no índice" "$LOGS/c10-fora-do-pack.log" && grep -qF "git reset -q --" "$LOGS/c10-fora-do-pack.log" && [ "$(G rev-parse HEAD)" = "$PRE" ] && [ "$(G diff --cached --name-only)" = "README.md" ]'
G reset -q -- README.md
G checkout -- README.md
# um material do pack JÁ no índice (um --commit anterior interrompido) não bloqueia
G add -- "$SENT_REL"
RC=$(derive d3 --commit)
check "derive --commit (com o sentinel pré-stageado): um commit só com o patch e o sentinel, assunto citando $PLAN (log: d3.log)" \
  eval '[ "$RC" = "0" ] && [ "$(G rev-parse HEAD~1)" = "$PRE" ] && [ "$(G diff-tree -r --no-commit-id --name-only HEAD | sort | tr "\n" " ")" = "$(printf "%s\n" "$PATCH_REL" "$SENT_REL" | sort | tr "\n" " ")" ] && G log -1 --format=%s | grep -q "$PLAN"'
G push -q origin main
RC=$(derive d4)
check "derive idempotente DEPOIS do commit dos materiais: «inalterado» e árvore limpa" \
  eval '[ "$RC" = "0" ] && grep -q "^inalterado" "$LOGS/d4.log" && [ -z "$(G status --porcelain --untracked-files=no)" ]'
MAT=$(G rev-parse HEAD)

# ------------------------------------------------ SIGN --dry-run
RC=$(run_sign g1-dry --dry-run)
check "SIGN --dry-run: rc=0, «Ensaio OK», árvore intacta (log: g1-dry.log)" \
  eval '[ "$RC" = "0" ] && grep -q "Ensaio OK" "$LOGS/g1-dry.log" && state_clean'
check "SIGN --dry-run: a suíte do driver passou com o patch aplicado" grep -q "passed" "$LOGS/g1-dry.log"

# ------------------------------------------------ patches VELHOS, pelo nome
reset_to_mat() { G reset -q --hard "$MAT"; G push -q -f origin main; }
printf 'ensaio\n' >"$WORK/.claude/plans/$PLAN/relmeta-stale-probe.txt"
G add -- ".claude/plans/$PLAN/relmeta-stale-probe.txt"
G commit -q -m "docs($PLAN): ENSAIO land fora do pack depois da derivação"
G push -q origin main
expect_abort "c02-velho-land-depois" "landaram depois da derivação" --dry-run
reset_to_mat
G commit -q --allow-empty -m "plan(PLAN-194): ENSAIO commit vazio citando um plano FORA do trem"
G push -q origin main
expect_abort "c03-velho-escopo-mudou" "re-derivação do HEAD difere" --dry-run
check "c03: o SIGN mostra o escopo pinado e o re-derivado (com PLAN-194)" grep -q "escopo re-derivado: .*PLAN-194" "$LOGS/c03-velho-escopo-mudou.log"
reset_to_mat
printf '# ENSAIO: derivador alterado depois da derivação\n' >>"$WORK/$APPLY_REL"
G commit -q -am "plan($PLAN): ENSAIO derivador alterado"
G push -q origin main
expect_abort "c04-velho-derivador" "o derivador no HEAD não é o que gerou o patch" --dry-run
reset_to_mat

# ------------------------------------------------ SIGN morto SEM trap (kill -9), antes do commit
# a forma que ele deixa: Anchor-SHA real no sentinel, .asc fora do HEAD, patch aplicado
python3 - "$WORK/$SENT_REL" "$MAT" <<'PY'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
t, n = re.subn(r"(?m)^Anchor-SHA:.*$", "Anchor-SHA: " + sys.argv[2], t, count=1)
assert n == 1
p.write_text(t, encoding="utf-8")
PY
printf 'ENSAIO: assinatura parcial\n' >"$WORK/$SENT_REL.asc"
G apply "$PATCH_REL"
RC=$(run_sign c08-interrompido --dry-run)
REC=$(tr -d '\r' <"$LOGS/c08-interrompido.log" | sed -n 's/^ *\(git checkout -- .* && rm -f .*\)$/\1/p' | head -n 1)
check "c08: SIGN morto sem trap — o próximo run recusa com «SIGN INTERROMPIDO» e imprime a restauração (log: c08-interrompido.log)" \
  eval '[ "$RC" != "0" ] && grep -qF "SIGN INTERROMPIDO" "$LOGS/c08-interrompido.log" && [ -n "$REC" ]'
E bash -c "cd '$WORK' && $REC" >"$LOGS/c08-restore.out" 2>&1 || printf 'aviso: a restauração impressa falhou\n'
check "c08: a restauração IMPRESSA devolve a árvore exatamente ao HEAD" state_clean

# ------------------------------------------------ TERM durante a bateria (run real)
printf '%s\n' 'import os, signal, sys' \
  'for s in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM, signal.SIGHUP):' \
  '    signal.signal(s, signal.SIG_DFL)' \
  'os.execvp(sys.argv[1], sys.argv[1:])' >"$RUN/sigdfl.py"
: >"$LOGS/c05-term.log"
feeder c05-term | E python3 "$RUN/sigdfl.py" bash -c "cd '$WORK' && printf '%s' \$\$ >'$RUN/c05.spid' && exec script -q /dev/null bash '$SIGN_REL'" \
  >"$LOGS/c05-term.log" 2>&1 &
BG_PID=$!
i=0; HIT=0
while [ "$i" -lt 1200 ]; do
  if grep -qF "7/8 bateria" "$LOGS/c05-term.log" 2>/dev/null; then HIT=1; break; fi
  kill -0 "$BG_PID" 2>/dev/null || break
  sleep 0.5; i=$((i + 1))
done
if [ "$HIT" = "1" ]; then
  SPID=$(cat "$RUN/c05.spid" 2>/dev/null || printf '')
  CB=$(pgrep -P "$SPID" | head -n 1 || printf '')
  PG=$(ps -o pgid= -p "$CB" 2>/dev/null | tr -d ' ' || printf '')
  if [ -n "$PG" ]; then kill -TERM -- "-$PG" 2>/dev/null || printf 'aviso: kill falhou\n'; fi
fi
wait "$BG_PID" && RC=0 || RC=$?
check "c05: TERM durante a bateria do run real — rc≠0, «RESTAURADA» e árvore intacta, sem .asc (log: c05-term.log)" \
  eval '[ "$HIT" = "1" ] && [ "$RC" != "0" ] && grep -q "RESTAURADA" "$LOGS/c05-term.log" && state_clean'

# ------------------------------------------------ resposta antecipada NÃO assina
# «assino» digitado DURANTE a re-derivação é descartado; a resposta no prompt é «nao»
FEED_EARLY=assino; FEED_ANSWER=nao
RC=$(run_sign c07-resposta-antecipada)
FEED_EARLY=""; FEED_ANSWER=assino
check "c07: «assino» digitado antes do prompt é descartado; «nao» no prompt aborta sem assinar e a árvore fica intacta (log: c07-resposta-antecipada.log)" \
  eval '[ "$RC" != "0" ] && grep -qF "nada assinado" "$LOGS/c07-resposta-antecipada.log" && ! grep -qF "5/8 assinar" "$LOGS/c07-resposta-antecipada.log" && state_clean'

# ------------------------------------------------ run REAL
RC=$(run_sign g2-real)
check "SIGN real: rc=0 e «RELMETA-142 COMMITADA» (log: g2-real.log)" \
  eval '[ "$RC" = "0" ] && grep -q "RELMETA-142 COMMITADA" "$LOGS/g2-real.log"'
check "SIGN real: o commit é filho do HEAD dos materiais e não foi pushado" \
  eval '[ "$(G rev-parse HEAD~1)" = "$MAT" ] && [ "$(G rev-parse origin/main)" = "$MAT" ]'
check "SIGN real: o commit toca EXATAMENTE os 3 alvos + sentinel + .asc" \
  eval '[ "$(G diff-tree -r --no-commit-id --name-only HEAD | sort | tr "\n" " ")" = "$(printf "%s\n" "$T_REL" "$T_MAN" "$T_TST" "$SENT_REL" "$SENT_REL.asc" | sort | tr "\n" " ")" ]'
check "SIGN real: a assinatura verifica com a chave descartável" \
  E gpg --verify "$WORK/$SENT_REL.asc" "$WORK/$SENT_REL"
check "SIGN real: Anchor-SHA = HEAD dos materiais e Patch-SHA256 = sha do patch" \
  eval 'grep -q "^Anchor-SHA: $MAT\$" "$WORK/$SENT_REL" && grep -q "^Patch-SHA256: $(sha256f "$WORK/$PATCH_REL")\$" "$WORK/$SENT_REL"'
check "SIGN real: TARGET_BASE=\"$TARGET_BASE\" e o --yes no probe do driver" \
  eval 'grep -q "^TARGET_BASE=\"$TARGET_BASE\"\$" "$WORK/$T_REL" && grep -q "gpg --yes --local-user" "$WORK/$T_REL"'
check "SIGN real: o modo do release.sh (100755) foi preservado" \
  eval '[ "$(G ls-tree HEAD -- "$T_REL" | awk "{print \$1}")" = "100755" ]'
( cd "$WORK" && E shasum -a 256 -c "$T_MAN" ) >"$LOGS/manifest-after.out" 2>&1 && MRC=0 || MRC=$?
MAN_N=$(grep . "$WORK/$T_MAN" | wc -l | tr -d ' '); OK_N=$(grep ': OK$' "$LOGS/manifest-after.out" | wc -l | tr -d ' ')
check "SIGN real: o manifesto ADR-192 confere no commit, linha a linha ($OK_N/$MAN_N OK)" \
  eval '[ "$MRC" = "0" ] && [ "$OK_N" = "$MAN_N" ]'
check "SIGN real: árvore limpa depois do commit" eval '[ -z "$(G status --porcelain --untracked-files=no)" ]'
G log -1 --format=%B >"$LOGS/landed-msg.txt"
check "SIGN real: a mensagem do commit tem o escopo, a linha do --yes e o coautor" \
  eval 'grep -qF "Escopo: " "$LOGS/landed-msg.txt" && grep -qF -- "--yes em todo gpg --output do driver." "$LOGS/landed-msg.txt" && grep -q "^Co-Authored-By: " "$LOGS/landed-msg.txt"'
# o Owner pusha depois do SIGN; o re-run seguinte acontece sobre o main já pushado
G push -q origin main
LANDED=$(G rev-parse HEAD)
RC=$(run_sign c06-rerun-depois-do-land --dry-run)
check "c06: re-run depois do land recusa («já existe» o .asc), HEAD e árvore intactos (log: c06-rerun-depois-do-land.log)" \
  eval '[ "$RC" != "0" ] && grep -qF "já existe" "$LOGS/c06-rerun-depois-do-land.log" && [ "$(G rev-parse HEAD)" = "$LANDED" ] && [ -z "$(G status --porcelain --untracked-files=no)" ]'
# SIGN morto DEPOIS do update-ref e antes de sincronizar o índice: o índice fica o da árvore anterior
G read-tree HEAD~1
RC=$(run_sign c09-indice-velho --dry-run)
REC=$(tr -d '\r' <"$LOGS/c09-indice-velho.log" | sed -n 's/.*Rode:  \(git reset -q -- [^,]*[^ ,]\) *,.*/\1/p' | head -n 1)
check "c09: commit no main com o índice velho — o próximo run recusa nomeando o git reset exato (log: c09-indice-velho.log)" \
  eval '[ "$RC" != "0" ] && grep -qF "índice ficou velho" "$LOGS/c09-indice-velho.log" && [ -n "$REC" ]'
E bash -c "cd '$WORK' && $REC" >"$LOGS/c09-restore.out" 2>&1 || printf 'aviso: o git reset impresso falhou\n'
check "c09: o git reset IMPRESSO sincroniza o índice com o commit (HEAD intacto, status limpo)" \
  eval '[ "$(G rev-parse HEAD)" = "$LANDED" ] && G diff --cached --quiet HEAD -- && [ -z "$(G status --porcelain --untracked-files=no)" ]'

# ------------------------------------------------ o --yes do probe GPG, medido
# o comando do probe EXATO de cada driver, sem terminal de controle (setsid):
# sem --yes, o gpg precisa perguntar «Overwrite?» e não tem onde; com --yes, assina
printf '%s\n' 'import os, sys' 'os.setsid()' 'os.execvp(sys.argv[1], sys.argv[1:])' >"$RUN/setsid.py"
G show "$BASE_TAG:$T_REL" >"$RUN/release-old.sh"
probe_cmd() { sed -n 's/^ *| \(gpg .*--output "\$sig_probe"\) \\$/\1/p' "$1" | head -n 1; }
OLD_CMD=$(probe_cmd "$RUN/release-old.sh"); NEW_CMD=$(probe_cmd "$WORK/$T_REL")
run_probe() {  # run_probe <comando gpg> — ecoa rc:tamanho da assinatura
  local rc=0
  E SIGN_KEY="$KEY_FPR" python3 "$RUN/setsid.py" bash -c \
    "sig_probe=\$(mktemp); printf 'release-preflight-probe' | $1 >/dev/null 2>&1; r=\$?; wc -c <\"\$sig_probe\" | tr -d ' '; rm -f \"\$sig_probe\"; exit \$r" \
    >"$RUN/probe.out" 2>&1 </dev/null || rc=$?
  printf '%s:%s' "$rc" "$(tail -n 1 "$RUN/probe.out")"
}
OLD_R=$(run_probe "$OLD_CMD"); NEW_R=$(run_probe "$NEW_CMD")
printf 'probe antigo: %s -> %s\nprobe novo:   %s -> %s\n' "$OLD_CMD" "$OLD_R" "$NEW_CMD" "$NEW_R" >"$LOGS/probe.out"
check "probe GPG: o comando da $BASE_TAG (sem --yes) FALHA sobre o arquivo do mktemp ($OLD_R)" \
  eval '[ -n "$OLD_CMD" ] && [ "${OLD_R%%:*}" != "0" ]'
check "probe GPG: o comando novo (com --yes) assina sobre o arquivo do mktemp ($NEW_R)" \
  eval '[ -n "$NEW_CMD" ] && [ "${NEW_R%%:*}" = "0" ] && [ "${NEW_R#*:}" -gt 0 ]'

# ------------------------------------------------ o driver em 1.4.2: bump --dry-run
E bash -c "cd '$WORK' && bash '$T_REL' bump --dry-run --npm-readme-reviewed --today 2026-09-24" \
  >"$LOGS/bump-dry.out" 2>&1 && BRC=0 || BRC=$?
NBUMP=$(grep ' | ' "$LOGS/bump-dry.out" | wc -l | tr -d ' ')
check "release.sh bump --dry-run em $TARGET_BASE: rc=0, sítios reescritos ($NBUMP arquivos no diffstat) e árvore restaurada (log: bump-dry.out)" \
  eval '[ "$BRC" = "0" ] && [ "$NBUMP" -gt 0 ] && grep -q "target $TARGET_BASE" "$LOGS/bump-dry.out" && [ -z "$(G status --porcelain --untracked-files=no)" ]'

printf '\n==================== PLACAR: %s PASS / %s FAIL ====================\n' "$PASS" "$FAIL"
printf 'logs: %s\n' "$LOGS"
[ "$FAIL" = "0" ]
