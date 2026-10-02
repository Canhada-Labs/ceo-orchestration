#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: harness de ensaio do OWNER-W1-SIGN.sh (PLAN-194 W1),
# clonado do test-ceremony-fn04.sh (PLAN-193 W4b).
# test-ceremony-w1.sh — ensaia o SIGN da W1 em CLONES descartáveis, com uma chave GPG
# descartável; nunca toca o repositório de origem, o chaveiro do Owner nem o $HOME real.
#
#   bash .claude/plans/PLAN-194/wave-w1/test-ceremony-w1.sh [--work <dir>] [--src <repo>] [--full-suite]
#
# Origem: o HEAD do repositório que contém este script (ou --src) — a árvore em que o SIGN vai
# rodar, com os materiais do pacote JÁ commitados. Área de trabalho: --work (criada), ou um
# diretório novo sob ${TMPDIR:-/tmp}. O que o harness monta ali:
#   - um remote bare em <work>/remote/Canhada-Labs/ceo-orchestration.git (o P0 exige esse nome no
#     remote e faz `git fetch origin main` — offline, contra o bare);
#   - um clone novo por cenário, com identidade git sintética;
#   - GNUPGHOME descartável em <work>/gnupg com uma chave ed25519 SEM senha; os sockets do
#     gpg-agent são redirecionados (arquivos «%Assuan%» do próprio GnuPG) para um diretório curto
#     sob ${TMPDIR:-/tmp}, porque o caminho de socket tem limite de tamanho — só os sockets
#     ficam lá, o chaveiro fica em <work>/gnupg; a impressão digital dela é acrescentada ao
#     .claude/sentinel-signers.txt do remote descartável num commit de ensaio (o SIGN só assina com
#     uma chave desse allowlist — o do Owner, na árvore real);
#   - se a origem ainda NÃO tem registro de rail (wave-w1/rail-round-*.md), um registro SINTÉTICO
#     rail-round-1.md entra no mesmo commit de ensaio, marcado como tal, com os sha256 do w1.patch,
#     do sentinel e do controle do HEAD, revisor GO e veredito APPROVE — o rail de verdade é do CEO;
#     com registros reais na origem, eles são usados (precisam ter os campos que o SIGN exige);
#   - HOME falso em <work>/home (PYTHONUSERBASE aponta para o do usuário, onde está o pytest), e o
#     SIGN roda sob `env -i` com esse ambiente mínimo e TMPDIR=<work>/tmp (os logs do SIGN e o
#     worktree da base ficam dentro da área do ensaio);
#   - SEM --full-suite: um `python3` de fachada no PATH responde SÓ às duas passadas inteiras do
#     pytest (paralela e serial) com uma saída sintética controlada pelo cenário; todo o resto
#     (controle da W1, actionlint nas duas formas, gates, reruns isolados, worktree da base) roda de
#     verdade. Com --full-suite as suítes rodam inteiras (máquina quieta, ~15 min por cenário).
# O modo real roda sob `script` (pseudo-TTY): o `[ -t 0 ]` do P0 é o mesmo do Owner.
set -euo pipefail
WORK=""
SRC=""
FULL=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --work) WORK="${2:?--work precisa de um diretório}"; shift 2 ;;
    --src) SRC="${2:?--src precisa de um repositório}"; shift 2 ;;
    --full-suite) FULL=1; shift ;;
    *) printf 'argumento desconhecido: %s\n' "$1" >&2; exit 2 ;;
  esac
done
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
[ -n "$SRC" ] || SRC="$(cd "$HERE" && git rev-parse --show-toplevel)"
SRC_HEAD="$(git -C "$SRC" rev-parse HEAD)"
D=.claude/plans/PLAN-194/wave-w1
SIGN="$D/OWNER-W1-SIGN.sh"
SENT=.claude/plans/PLAN-194/wave-w1-approved.md
PATCH="$D/w1.patch"
STAGED="$D/staged-w1/.github/workflows/validate.yml"
SHAPE="$D/check-w1-shape.py"
TARGET_PATH=.github/workflows/validate.yml
git -C "$SRC" cat-file -e "$SRC_HEAD:$SIGN" 2>/dev/null || { printf 'o HEAD de %s não tem %s commitado — commite os materiais antes do ensaio\n' "$SRC" "$SIGN" >&2; exit 2; }
if [ -n "$WORK" ]; then
  [ ! -e "$WORK" ] || { printf '%s já existe — use um diretório novo\n' "$WORK" >&2; exit 2; }
  mkdir -p "$WORK"
else
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/w1-rehearsal.XXXXXX")"
fi
WORK="$(cd "$WORK" && pwd -P)"
SOCKDIR="$(mktemp -d "${TMPDIR:-/tmp}/w1g.XXXXXX")"
chmod 700 "$SOCKDIR"
PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); printf '  PASS %s\n' "$*"; }
ko() { FAIL=$((FAIL + 1)); printf '  FAIL %s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
COMPLETED=0
cleanup() {
  local rc=$?
  GNUPGHOME="$WORK/gnupg" gpgconf --kill all >/dev/null 2>&1 || printf ''
  rm -f "$SOCKDIR"/S.* 2>/dev/null || printf ''
  rmdir "$SOCKDIR" 2>/dev/null || printf ''
  printf '\n(área do ensaio preservada para inspeção: %s)\n' "$WORK"
  if [ "$COMPLETED" != "1" ]; then
    # bash 3.2: um erro de expansão numa lista `a && b || c` sai com 0 — nunca é um ensaio verde
    printf 'ENSAIO ABORTADO antes do resumo (rc=%s) — não é verde\n' "$rc" >&2
    [ "$rc" -ne 0 ] || rc=1
    exit "$rc"
  fi
}
trap cleanup EXIT

step "montagem"
REMOTE="$WORK/remote/Canhada-Labs/ceo-orchestration.git"
mkdir -p "$(dirname "$REMOTE")" "$WORK/home" "$WORK/shim" "$WORK/logs" "$WORK/tmp"
BR="$(git -C "$SRC" rev-parse --abbrev-ref HEAD)"
if [ "$BR" = "HEAD" ]; then
  git clone --quiet --bare --no-local "$SRC" "$REMOTE"
else
  git clone --quiet --bare --no-local --single-branch --branch "$BR" "$SRC" "$REMOTE"
fi
git -C "$REMOTE" update-ref refs/heads/main "$SRC_HEAD"
git -C "$REMOTE" symbolic-ref HEAD refs/heads/main
GNUPGHOME="$WORK/gnupg"
mkdir -p "$GNUPGHOME"
chmod 700 "$GNUPGHOME"
for s in S.gpg-agent S.gpg-agent.extra S.gpg-agent.browser S.gpg-agent.ssh S.keyboxd S.dirmngr S.scdaemon; do
  printf '%%Assuan%%\nsocket=%s/%s\n' "$SOCKDIR" "$s" > "$GNUPGHOME/$s"
done
GNUPGHOME="$GNUPGHOME" gpg --batch --pinentry-mode loopback --passphrase '' \
  --quick-gen-key 'W1 Rehearsal Throwaway <w1-rehearsal@example.invalid>' ed25519 sign never >"$WORK/logs/keygen.log" 2>&1
FPR="$(GNUPGHOME="$GNUPGHOME" gpg --list-secret-keys --with-colons 2>/dev/null | awk -F: '$1 == "fpr" {print $10; exit}')"
[ -n "$FPR" ] || { tail -5 "$WORK/logs/keygen.log" >&2; printf 'não consegui gerar a chave descartável\n' >&2; exit 1; }
REALPY="$(command -v python3)"
PYUB="$(python3 -m site --user-base)"
cat > "$WORK/shim/python3" <<SHIM
#!/bin/bash
# fachada do ensaio: responde SÓ às duas passadas inteiras do pytest do SIGN; o resto é o python3 real
if [ "\${1:-}" = "-m" ] && [ "\${2:-}" = "pytest" ] && [ "\${3:-}" = "-n" ] && [ "\${4:-}" = "auto" ]; then
  [ -z "\${W1_SHIM_MARK:-}" ] || : > "\$W1_SHIM_MARK"
  [ -z "\${W1_SHIM_SLEEP:-}" ] || sleep "\$W1_SHIM_SLEEP"
  # efeitos colaterais de uma bateria longa: outro commit no meio, um arquivo rastreado escrito
  [ -z "\${W1_SHIM_COMMIT:-}" ] || git commit -q --allow-empty -m "ensaio: commit durante a bateria"
  [ -z "\${W1_SHIM_TOUCH:-}" ] || printf '\n# escrito pela bateria do ensaio\n' >> "\$W1_SHIM_TOUCH"
  if [ -n "\${W1_SHIM_FAIL_FILE:-}" ]; then
    while IFS= read -r t; do printf 'FAILED %s - injetada pelo ensaio\n' "\$t"; done < "\$W1_SHIM_FAIL_FILE"
    printf '1 failed, 10 passed in 0.01s\n'
    exit 1
  fi
  if [ -n "\${W1_SHIM_FAIL:-}" ]; then
    for t in \$W1_SHIM_FAIL; do printf 'FAILED %s - injetada pelo ensaio\n' "\$t"; done
    printf '1 failed, 10 passed in 0.01s\n'
    exit 1
  fi
  printf '10 passed in 0.01s\n'
  exit 0
fi
if [ "\${1:-}" = "-m" ] && [ "\${2:-}" = "pytest" ] && [ "\${3:-}" = "-m" ] && [ "\${4:-}" = "serial" ]; then
  printf '5 passed in 0.01s\n'
  exit 0
fi
exec "$REALPY" "\$@"
SHIM
chmod 755 "$WORK/shim/python3"
GPGDIR="$(dirname "$(command -v gpg)")"
if [ "$FULL" = "1" ]; then SPATH="$GPGDIR:/usr/bin:/bin:/usr/sbin:/sbin"; else SPATH="$WORK/shim:$GPGDIR:/usr/bin:/bin:/usr/sbin:/sbin"; fi
# a chave descartável entra no allowlist de signatários do remote (commit de ensaio, empurrado ao bare);
# sem registro de rail na origem, um registro SINTÉTICO entra no mesmo commit
STAGE="$WORK/c-stage"
git clone --quiet "$REMOTE" "$STAGE"
git -C "$STAGE" config user.name "W1 Rehearsal"
git -C "$STAGE" config user.email "w1-rehearsal@example.invalid"
printf '# ENSAIO: chave descartável do test-ceremony-w1.sh\n%s\n' "$FPR" >> "$STAGE/.claude/sentinel-signers.txt"
git -C "$STAGE" add -- .claude/sentinel-signers.txt
RAIL_NOTE="registros reais da origem"
if ! ls "$STAGE/$D"/rail-round-*.md >/dev/null 2>&1; then
  PSHA0="$(shasum -a 256 "$STAGE/$PATCH" | awk '{print $1}')"
  SSHA0="$(git -C "$STAGE" show "HEAD:$SENT" | shasum -a 256 | awk '{print $1}')"
  CSHA0="$(git -C "$STAGE" show "HEAD:$SHAPE" | shasum -a 256 | awk '{print $1}')"
  cat > "$STAGE/$D/rail-round-1.md" <<REC
# rail-round-1 — REGISTRO SINTÉTICO DO ENSAIO (test-ceremony-w1.sh); não é revisão

Rail-Round: 1
Rail-Subject: $PATCH
Rail-Subject-sha256: $PSHA0
Rail-Sentinel-sha256: $SSHA0
Rail-Control-sha256: $CSHA0
Rail-Reviewer-Verdict: GO
Rail-Verdict: APPROVE
Rail-Findings: P0=0 P1=0 P2=0

## Saída do revisor

\`\`\`text
NENHUM ACHADO
VERDICT: GO
\`\`\`
REC
  git -C "$STAGE" add -- "$D/rail-round-1.md"
  RAIL_NOTE="registro SINTÉTICO (a origem ainda não tem rail)"
fi
git -C "$STAGE" commit -q -m "ensaio: chave descartável no allowlist de signatários (+ rail sintético, se faltava)"
git -C "$STAGE" push -q origin HEAD:main
printf '  origem %s @ %s\n  área %s\n  chave descartável %s (no allowlist do remote: %s)\n  rail: %s\n  suítes: %s\n' "$SRC" "$SRC_HEAD" "$WORK" "$FPR" \
  "$(git -C "$STAGE" rev-parse --short HEAD)" "$RAIL_NOTE" \
  "$([ "$FULL" = "1" ] && printf 'INTEIRAS' || printf 'fachada (só as duas passadas inteiras)')"

fresh() {  # clone novo em main, com identidade sintética; imprime o caminho
  local c="$WORK/c-$1"
  git clone --quiet "$REMOTE" "$c"
  git -C "$c" config user.name "W1 Rehearsal"
  git -C "$c" config user.email "w1-rehearsal@example.invalid"
  printf '%s' "$c"
}
sign_env() {  # o ambiente mínimo do SIGN no ensaio
  printf '%s\n' "HOME=$WORK/home" "PATH=$SPATH" "TMPDIR=$WORK/tmp" "GNUPGHOME=$GNUPGHOME" \
    "PYTHONUSERBASE=$PYUB" "LANG=en_US.UTF-8" "LC_ALL=en_US.UTF-8" "TERM=${TERM:-xterm}" "USER=${USER:-rehearsal}" \
    "W1_SHIM_FAIL=${W1_SHIM_FAIL:-}" "W1_SHIM_SLEEP=${W1_SHIM_SLEEP:-}" "W1_SHIM_MARK=${W1_SHIM_MARK:-}" \
    "W1_SHIM_FAIL_FILE=${W1_SHIM_FAIL_FILE:-}" "W1_SHIM_COMMIT=${W1_SHIM_COMMIT:-}" "W1_SHIM_TOUCH=${W1_SHIM_TOUCH:-}"
}
run_dry() {  # clone log → rc do SIGN --dry-run (sem TTY)
  local rc=0
  local ef="$WORK/logs/env-$(basename "$1")"
  ( cd "$1" && sign_env > "$ef" && exec env -i $(cat "$ef") bash "$SIGN" --dry-run ) >"$2" 2>&1 </dev/null || rc=$?
  return "$rc"
}
run_real_tty() {  # clone log → rc do SIGN real sob pseudo-TTY
  local rc=0
  local ef="$WORK/logs/env-$(basename "$1")"
  ( cd "$1" && sign_env > "$ef" && exec script -q /dev/null env -i $(cat "$ef") bash "$SIGN" ) >"$2" 2>&1 </dev/null || rc=$?
  return "$rc"
}
clean_tree() {  # clone rótulo — árvore rastreada limpa, sem .asc, sentinel intacto, um worktree só
  local c="$1" label="$2"
  [ -z "$(git -C "$c" status --porcelain --untracked-files=no)" ] && ok "$label: árvore rastreada limpa" || ko "$label: árvore suja: $(git -C "$c" status --short --untracked-files=no | tr '\n' ' ')"
  [ ! -e "$c/$SENT.asc" ] && ok "$label: sem .asc" || ko "$label: sobrou $SENT.asc"
  git -C "$c" diff --quiet HEAD -- "$SENT" && ok "$label: sentinel intacto" || ko "$label: sentinel alterado"
  [ "$(git -C "$c" worktree list | wc -l | tr -d ' ')" = "1" ] && ok "$label: nenhum worktree da base sobrou" || ko "$label: worktree sobrou: $(git -C "$c" worktree list | tr '\n' ' ')"
}
has() {  # log padrão rótulo
  if grep -qF -- "$2" "$1"; then ok "$3"; else ko "$3 (esperava «$2» em $1)"; tail -15 "$1" | sed 's/^/        | /'; fi
}
commit_file() {  # clone caminho mensagem — commit LOCAL (não empurrado: o P0 aceita HEAD à frente de origin/main)
  git -C "$1" add -- "$2"
  git -C "$1" commit -q -m "$3"
}
last_rec() {  # clone → caminho relativo do último registro de rail
  printf '%s/rail-round-%s.md' "$D" "$(ls "$1/$D"/rail-round-*.md | awk -F'rail-round-' '{sub(/\.md$/, "", $2); print $2}' | sort -n | awk 'END {print}')"
}
set_rec_line() {  # clone prefixo-da-linha linha-nova — troca a(s) linha(s) que começam com o prefixo no último registro
  local rec
  rec="$(last_rec "$1")"
  awk -v p="$2" -v l="$3" '{ if (index($0, p) == 1) print l; else print }' "$1/$rec" > "$1/$rec.tmp"
  mv "$1/$rec.tmp" "$1/$rec"
  printf '%s' "$rec"
}
rec_awk() {  # clone programa-awk — reescreve o último registro com o awk; imprime o caminho relativo
  local rec
  rec="$(last_rec "$1")"
  awk "$2" "$1/$rec" > "$1/$rec.tmp"
  mv "$1/$rec.tmp" "$1/$rec"
  printf '%s' "$rec"
}
plant_actionlint_red() {  # clone — um achado de actionlint PRÉ-EXISTENTE (fora do patch), commitado
  awk '{ if (!done && $0 ~ /runs-on: ubuntu-latest/) { sub(/ubuntu-latest/, "ubuntu-99.04"); done = 1 } print }' \
    "$1/.github/workflows/benchmarks.yml" > "$1/.github/workflows/benchmarks.yml.tmp"
  mv "$1/.github/workflows/benchmarks.yml.tmp" "$1/.github/workflows/benchmarks.yml"
  commit_file "$1" .github/workflows/benchmarks.yml "ensaio: achado de actionlint pré-existente"
}
rederive() {  # clone programa-awk — reaplica o patch sobre o HEAD do clone, edita a pós-imagem com
  # o awk, regenera patch e cópia staged e prende o registro sintético ao patch novo (commit)
  local c="$1" prog="$2" rec
  ( cd "$c" && git apply "$PATCH" \
      && awk "$prog" "$TARGET_PATH" > "$TARGET_PATH.tmp" && mv "$TARGET_PATH.tmp" "$TARGET_PATH" \
      && git diff --full-index -- "$TARGET_PATH" > "$PATCH.new" \
      && cp "$TARGET_PATH" "$STAGED" \
      && git checkout -q HEAD -- "$TARGET_PATH" \
      && mv "$PATCH.new" "$PATCH" ) >>"$WORK/logs/rederive.log" 2>&1 || return 1
  rec="$(set_rec_line "$c" "Rail-Subject-sha256: " "Rail-Subject-sha256: $(shasum -a 256 "$c/$PATCH" | awk '{print $1}')")"
  git -C "$c" add -- "$PATCH" "$STAGED" "$rec"
  git -C "$c" commit -q -m "ensaio: patch re-derivado"
}
base_edit() {  # clone programa-awk mensagem — edita o validate.yml do HEAD do clone (a base) e commita
  awk "$2" "$1/$TARGET_PATH" > "$1/$TARGET_PATH.tmp" && mv "$1/$TARGET_PATH.tmp" "$1/$TARGET_PATH"
  commit_file "$1" "$TARGET_PATH" "$3"
}
FLAKY=".claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_non_workflow_tool_is_noop"

step "T0 ceremony-lint e bits de execução no índice"
C="$(fresh lint)"
if (cd "$C" && python3 .claude/scripts/check-ceremony-script.py) >"$WORK/logs/t0.log" 2>&1; then ok "T0: ceremony-lint 0 BLOCKING"; else ko "T0: ceremony-lint reprovou"; tail -12 "$WORK/logs/t0.log" | sed 's/^/        | /'; fi
for f in "$SIGN" "$D/test-ceremony-w1.sh" "$SHAPE"; do
  m="$(git -C "$C" ls-files -s -- "$f" | awk '{print $1}')"
  [ "$m" = "100644" ] && ok "T0: $f modo $m no índice" || ko "T0: $f modo '$m' no índice (esperado 100644)"
done
for f in "$SIGN" "$D/test-ceremony-w1.sh"; do
  # classe bash 3.2: numa locale UTF-8 o byte seguinte a `$nome` conta como parte do nome
  if LC_ALL=C grep -nE '\$[A-Za-z_][A-Za-z0-9_]*[^ -~]' "$C/$f" >"$WORK/logs/t0-adj.log" 2>&1; then
    ko "T0: $f tem variável colada a caractere não-ASCII (use \${nome}):"; sed 's/^/        | /' "$WORK/logs/t0-adj.log"
  else
    ok "T0: $f sem variável colada a caractere não-ASCII"
  fi
done
SB="$(git -C "$C" hash-object -- "$STAGED")"
PB="$(awk '/^index /{split($2, h, /\.\./); print h[2]}' "$C/$PATCH")"
[ -n "$PB" ] && [ "$SB" = "$PB" ] && ok "T0: cópia staged = pós-imagem do patch ($SB)" || ko "T0: cópia staged $SB ≠ pós-imagem $PB"

step "T1 --dry-run no caminho feliz"
C="$(fresh dry)"
H0="$(git -C "$C" rev-parse HEAD)"
rc=0; run_dry "$C" "$WORK/logs/t1.log" || rc=$?
[ "$rc" = "0" ] && ok "T1: rc 0" || ko "T1: rc $rc"
has "$WORK/logs/t1.log" "Ensaio OK" "T1: ensaio concluído"
has "$WORK/logs/t1.log" "controle da W1 reprova no HEAD (como deve)" "T1: o P0 viu o controle vermelho no HEAD"
has "$WORK/logs/t1.log" "ok: controle da W1 (vermelho no HEAD, verde com o patch)" "T1: controle verde com o patch"
has "$WORK/logs/t1.log" "blob(s) conferido(s) contra o index pós-imagem" "T1: pós-imagem conferida"
has "$WORK/logs/t1.log" "ok: sonda da regra shellcheck do actionlint" "T1: a regra shellcheck do actionlint executou"
has "$WORK/logs/t1.log" "ok: actionlint (forma do job validate)" "T1: actionlint (forma do job validate) passou"
has "$WORK/logs/t1.log" "ok: actionlint (forma do actionlint.yml)" "T1: actionlint (forma do actionlint.yml) passou"
has "$WORK/logs/t1.log" "ok: validate-governance (Errors: 0)" "T1: validate-governance passou"
has "$WORK/logs/t1.log" "e controle $(git -C "$C" show "HEAD:$SHAPE" | shasum -a 256 | awk '{print $1}')" "T1: o P0 prendeu o rail ao controle do HEAD"
has "$WORK/logs/t1.log" "sentinel $(git -C "$C" show "HEAD:$SENT" | shasum -a 256 | awk '{print $1}')" "T1: o P0 prendeu o rail ao sentinel do HEAD"
[ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T1: HEAD inalterado" || ko "T1: HEAD mudou"
clean_tree "$C" "T1"

step "T2 modo REAL sob pseudo-TTY, chave descartável, uma falha instável injetada"
C="$(fresh real)"
H0="$(git -C "$C" rev-parse HEAD)"
rc=0; W1_SHIM_FAIL="$FLAKY" run_real_tty "$C" "$WORK/logs/t2.log" || rc=$?
[ "$rc" = "0" ] && ok "T2: rc 0" || ko "T2: rc $rc"
has "$WORK/logs/t2.log" "LANDADO em" "T2: landou"
if [ "$FULL" = "0" ]; then has "$WORK/logs/t2.log" "instável (passou isolada, com o patch" "T2: a falha injetada foi julgada instável pelo rerun isolado"; fi
[ "$(git -C "$C" rev-parse HEAD~1)" = "$H0" ] && ok "T2: exatamente um commit novo sobre o HEAD" || ko "T2: HEAD~1 != HEAD anterior"
git -C "$C" show --name-only --format= HEAD | sort > "$WORK/logs/t2.committed"
{ awk '/^diff --git /{p=$3; sub(/^a\//, "", p); print p}' "$C/$PATCH"; printf '%s\n%s\n' "$SENT" "$SENT.asc"; } | sort -u > "$WORK/logs/t2.expected"
cmp -s "$WORK/logs/t2.committed" "$WORK/logs/t2.expected" && ok "T2: o commit tem exatamente o validate.yml + sentinel + .asc" || ko "T2: conjunto commitado inesperado: $(comm -3 "$WORK/logs/t2.committed" "$WORK/logs/t2.expected" | tr '\n' ' ')"
if GNUPGHOME="$GNUPGHOME" gpg --verify "$C/$SENT.asc" "$C/$SENT" >"$WORK/logs/t2.verify" 2>&1; then ok "T2: a assinatura verifica"; else ko "T2: a assinatura não verifica"; fi
grep -qF "$FPR" "$WORK/logs/t2.verify" && ok "T2: assinada pela chave descartável" || ko "T2: signatário inesperado"
NEWB="$(awk '/^index /{split($2, h, /\.\./); print h[2]}' "$C/$PATCH")"
[ "$(git -C "$C" rev-parse "HEAD:$TARGET_PATH")" = "$NEWB" ] && ok "T2: o validate.yml landado é o blob do pós-imagem revisado" || ko "T2: o validate.yml landou com blob diferente do revisado"
[ "$(git -C "$C" rev-parse "HEAD:$TARGET_PATH")" = "$(git -C "$C" hash-object -- "$STAGED")" ] && ok "T2: o landado é byte a byte a cópia staged" || ko "T2: o landado difere da cópia staged"
[ "$(git -C "$C" ls-files -s -- "$TARGET_PATH" | awk '{print $1}')" = "100644" ] && ok "T2: modo do validate.yml segue 100644" || ko "T2: modo do validate.yml mudou"
PSHA="$(shasum -a 256 "$C/$PATCH" | awk '{print $1}')"
LASTREC="$(ls "$C/$D"/rail-round-*.md | awk -F'rail-round-' '{sub(/\.md$/, "", $2); print $2}' | sort -n | awk 'END {print}')"
RSHA="$(shasum -a 256 "$C/$D/rail-round-$LASTREC.md" | awk '{print $1}')"
for kv in "Anchor-SHA: $H0" "Patch-sha256: $PSHA" "Rail-Record-sha256: $RSHA" "Data: $(date -u +%Y-%m-%d)"; do
  grep -qxF -- "$kv" "$C/$SENT" && ok "T2: sentinel tem «${kv}»" || ko "T2: sentinel sem «${kv}»"
done
grep -q "TO-FILL-BY-SIGN" "$C/$SENT" && ko "T2: sobrou TO-FILL-BY-SIGN" || ok "T2: nenhum TO-FILL-BY-SIGN no sentinel assinado"
git -C "$C" log -1 --format=%B > "$WORK/logs/t2.msg"
grep -q "^Co-Authored-By: " "$WORK/logs/t2.msg" && ok "T2: mensagem de commit completa (trailer presente)" || ko "T2: mensagem de commit sem trailer"
has "$WORK/logs/t2.log" "assinado por $FPR" "T2: o SIGN conferiu o signatário contra o allowlist"
grep -qF "assinado por $FPR" "$WORK/logs/t2.msg" && ok "T2: a mensagem nomeia o signatário" || ko "T2: a mensagem não nomeia o signatário"
grep -qF "perna 3.9 em ubuntu-24.04" "$WORK/logs/t2.msg" && ok "T2: a mensagem nomeia a mudança" || ko "T2: a mensagem não nomeia a mudança"
[ -z "$(git -C "$C" status --porcelain --untracked-files=no)" ] && ok "T2: árvore limpa depois do land" || ko "T2: árvore suja depois do land"
[ "$(git -C "$C" worktree list | wc -l | tr -d ' ')" = "1" ] && ok "T2: nenhum worktree da base sobrou" || ko "T2: worktree sobrou"
if (cd "$C" && env HOME="$WORK/home" PYTHONUSERBASE="$PYUB" python3 "$SHAPE" "$TARGET_PATH") >"$WORK/logs/t2.shape" 2>&1; then
  ok "T2: o controle da W1 passa na árvore landada"
else
  ko "T2: o controle da W1 reprova na árvore landada"; tail -5 "$WORK/logs/t2.shape" | sed 's/^/        | /'
fi

if [ "$FULL" = "0" ]; then
  step "T3 falha NOVA (passa sem o patch, falha com ele) aborta e restaura"
  C="$(fresh newfail)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_w1_plant_new.py" <<'PY'
"""Ensaio W1: passa na árvore SEM o patch (o validate.yml não citava o rótulo 26.04)."""
from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def test_validate_yml_names_no_26_04_label():
    text = (_REPO / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
    assert "ubuntu-26.04" not in text
PY
  commit_file "$C" tests/unit/test_zz_w1_plant_new.py "ensaio: plant (falha nova)"
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; W1_SHIM_FAIL="tests/unit/test_zz_w1_plant_new.py::test_validate_yml_names_no_26_04_label" run_dry "$C" "$WORK/logs/t3.log" || rc=$?
  [ "$rc" = "1" ] && ok "T3: rc 1" || ko "T3: rc $rc (esperado 1)"
  has "$WORK/logs/t3.log" "falhas NOVAS" "T3: a falha nova foi nomeada"
  has "$WORK/logs/t3.log" "patch-revertido" "T3: o desfazer reverteu o patch"
  [ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T3: HEAD inalterado" || ko "T3: HEAD mudou"
  clean_tree "$C" "T3"

  step "T4 falha PRÉ-EXISTENTE (falha com e sem o patch) é nota, não bloqueio"
  C="$(fresh prefail)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_w1_plant_pre.py" <<'PY'
"""Ensaio W1: falha nas duas árvores (vermelho pré-existente)."""
from __future__ import annotations


def test_always_red():
    raise AssertionError("vermelho pré-existente plantado pelo ensaio")
PY
  commit_file "$C" tests/unit/test_zz_w1_plant_pre.py "ensaio: plant (pré-existente)"
  rc=0; W1_SHIM_FAIL="tests/unit/test_zz_w1_plant_pre.py::test_always_red" run_dry "$C" "$WORK/logs/t4.log" || rc=$?
  [ "$rc" = "0" ] && ok "T4: rc 0" || ko "T4: rc $rc (esperado 0)"
  has "$WORK/logs/t4.log" "PRÉ-EXISTENTE (falha também sem o patch)" "T4: nomeada como pré-existente"
  has "$WORK/logs/t4.log" "ATENÇÃO — vermelhos PRÉ-EXISTENTES" "T4: resumo final avisa"
  clean_tree "$C" "T4"
fi

step "T5 base derivada (o validate.yml mudou fora dos hunks) recusa no P0"
C="$(fresh drift)"
printf '\n# deriva plantada pelo ensaio\n' >> "$C/$TARGET_PATH"
commit_file "$C" "$TARGET_PATH" "ensaio: deriva da base"
rc=0; run_dry "$C" "$WORK/logs/t5.log" || rc=$?
[ "$rc" = "1" ] && ok "T5: rc 1" || ko "T5: rc $rc (esperado 1)"
has "$WORK/logs/t5.log" "a base de $TARGET_PATH mudou" "T5: a deriva é nomeada pelo caminho"
has "$WORK/logs/t5.log" "nada a desfazer" "T5: nada foi aplicado"
clean_tree "$C" "T5"

step "T6 registro de rail que não prende os três sujeitos, ou com veredito incoerente, recusa no P0"
Z64="$(printf '%064d' 0)"
for v in subject sentinel control verdict reviewer lastline innerheading badopen unclosed twofences innerfence indentedtwo indentedinner; do
  C="$(fresh "rail-$v")"
  case "$v" in
    subject)  REC="$(set_rec_line "$C" "Rail-Subject-sha256: " "Rail-Subject-sha256: $Z64")"; want="revisou outro patch" ;;
    sentinel) REC="$(set_rec_line "$C" "Rail-Sentinel-sha256: " "Rail-Sentinel-sha256: $Z64")"; want="revisou outro texto assinável" ;;
    control)  REC="$(set_rec_line "$C" "Rail-Control-sha256: " "Rail-Control-sha256: $Z64")"; want="revisou outro controle" ;;
    verdict)  REC="$(set_rec_line "$C" "Rail-Verdict: " "Rail-Verdict: NO-GO")"; want="só aceita APPROVE ou DECLARED-P2" ;;
    reviewer)  # revisor em NO-GO (campo e linha verbatim coerentes) com o Rail-Verdict do registro
      RV="$(awk 'index($0, "Rail-Verdict: ") == 1 {print substr($0, 15)}' "$C/$(last_rec "$C")")"
      REC="$(set_rec_line "$C" "Rail-Reviewer-Verdict: " "Rail-Reviewer-Verdict: NO-GO")"
      REC="$(set_rec_line "$C" "VERDICT: " "VERDICT: NO-GO")"
      if [ "$RV" = "DECLARED-P2" ]; then want="DECLARED-P2 exige o revisor em GO ou GO-WITH-CONDITIONS"; else want="APPROVE exige o revisor em GO"; fi ;;
    lastline)  # a última linha VERDICT do revisor diz outra coisa que o campo (que é GO ou GO-WITH-CONDITIONS)
      REC="$(set_rec_line "$C" "VERDICT: " "VERDICT: NO-GO")"; want="≠ a última linha VERDICT do revisor" ;;
    innerheading)  # um título «## …» DENTRO da saída verbatim não encerra o bloco: vale a última VERDICT
      REC="$(rec_awk "$C" '!done && $0 == "```text" { print; print "VERDICT: GO"; print "## Achados"; print "VERDICT: NO-GO"; inb = 1; next }
        inb { if ($0 == "```") { print; inb = 0; done = 1 } next }
        { print }')"; want="≠ a última linha VERDICT do revisor" ;;
    badopen)  # abertura de cerca mal formada
      REC="$(rec_awk "$C" '!done && $0 == "```text" { print "```txt"; done = 1; next } { print }')"; want="abertura de cerca mal formada" ;;
    unclosed)  # o bloco verbatim nunca fecha
      REC="$(rec_awk "$C" '$0 == "```text" { inb = 1; print; next } inb && $0 == "```" && !done { inb = 0; done = 1; next } { print }')"; want="registro recusado —" ;;
    twofences)  # um segundo bloco cercado na mesma seção
      REC="$(rec_awk "$C" '$0 == "```text" { inb = 1 } { print } inb && $0 == "```" && !done { print "```text"; print "VERDICT: GO"; print "```"; inb = 0; done = 1 }')"; want="segunda cerca na seção" ;;
    indentedtwo)  # um segundo bloco com cercas INDENTADAS e NO-GO depois do canônico com GO (sonda do Codex r3)
      REC="$(rec_awk "$C" '$0 == "```text" { inb = 1 } { print } inb && $0 == "```" && !done { print " ```text"; print "VERDICT: NO-GO"; print " ```"; inb = 0; done = 1 }')"; want="segunda cerca na seção" ;;
    indentedinner)  # uma cerca INDENTADA dentro do bloco verbatim (indentar não escapa)
      REC="$(rec_awk "$C" '{ print } !done && $0 == "```text" { print "    ```python"; done = 1 }')"; want="linha de cerca mal formada DENTRO do bloco verbatim" ;;
    innerfence)  # uma linha de cerca mal formada DENTRO do bloco verbatim
      REC="$(rec_awk "$C" '{ print } !done && $0 == "```text" { print "```python"; done = 1 }')"; want="linha de cerca mal formada DENTRO do bloco verbatim" ;;
  esac
  commit_file "$C" "$REC" "ensaio: registro de rail adulterado ($v)"
  rc=0; run_dry "$C" "$WORK/logs/t6-$v.log" || rc=$?
  [ "$rc" = "1" ] && ok "T6-$v: rc 1" || ko "T6-$v: rc $rc (esperado 1)"
  has "$WORK/logs/t6-$v.log" "$want" "T6-$v: recusa nomeada"
  clean_tree "$C" "T6-$v"
done

step "T6-quoted cerca da saída do revisor citada com «> » dentro do bloco: registro ACEITO"
C="$(fresh rail-quoted)"
REC="$(rec_awk "$C" '{ print } !done && $0 == "```text" { print "> ```python"; print "> exemplo"; print "> ```"; done = 1 }')"
commit_file "$C" "$REC" "ensaio: cerca da saída do revisor citada"
rc=0; run_dry "$C" "$WORK/logs/t6-quoted.log" || rc=$?
[ "$rc" = "0" ] && ok "T6-quoted: rc 0" || ko "T6-quoted: rc $rc (esperado 0)"
has "$WORK/logs/t6-quoted.log" "Ensaio OK" "T6-quoted: a cerca citada não recusa o registro"
clean_tree "$C" "T6-quoted"

step "T7 modo real SEM TTY recusa antes de tudo"
C="$(fresh notty)"
rc=0
( cd "$C" && sign_env > "$WORK/logs/env-t7" && exec env -i $(cat "$WORK/logs/env-t7") bash "$SIGN" ) >"$WORK/logs/t7.log" 2>&1 </dev/null || rc=$?
[ "$rc" = "1" ] && ok "T7: rc 1" || ko "T7: rc $rc (esperado 1)"
has "$WORK/logs/t7.log" "sem TTY" "T7: recusa nomeada"
clean_tree "$C" "T7"

if [ "$FULL" = "0" ]; then
  step "T8 SIGTERM durante a bateria: o desfazer roda e a árvore volta"
  C="$(fresh sigterm)"
  MARK="$WORK/logs/t8.mark"
  ( cd "$C" && W1_SHIM_SLEEP=15 W1_SHIM_MARK="$MARK" sign_env > "$WORK/logs/env-t8" \
      && exec env -i $(cat "$WORK/logs/env-t8") bash "$SIGN" --dry-run ) >"$WORK/logs/t8.log" 2>&1 </dev/null &
  PID=$!
  i=0
  while [ ! -e "$MARK" ] && [ "$i" -lt 600 ] && kill -0 "$PID" 2>/dev/null; do sleep 1; i=$((i + 1)); done
  if [ -e "$MARK" ]; then
    kill -TERM "$PID"
    rc=0; wait "$PID" || rc=$?
    [ "$rc" = "143" ] && ok "T8: rc 143 (TERM)" || ko "T8: rc $rc (esperado 143)"
    has "$WORK/logs/t8.log" "patch-revertido" "T8: o desfazer reverteu o patch"
    clean_tree "$C" "T8"
  else
    kill -TERM "$PID" 2>/dev/null || printf ''
    ko "T8: o SIGN não chegou à passada paralela (terminou antes ou passou de 600 s):"; tail -8 "$WORK/logs/t8.log" | sed 's/^/        | /'
  fi

  step "T9 SIGKILL deixa sobra; a nova execução a nomeia e a receita impressa a desfaz"
  C="$(fresh sigkill)"
  MARK="$WORK/logs/t9.mark"
  ( cd "$C" && W1_SHIM_SLEEP=5 W1_SHIM_MARK="$MARK" sign_env > "$WORK/logs/env-t9" \
      && exec env -i $(cat "$WORK/logs/env-t9") bash "$SIGN" --dry-run ) >"$WORK/logs/t9a.log" 2>&1 </dev/null &
  PID=$!
  i=0
  while [ ! -e "$MARK" ] && [ "$i" -lt 600 ] && kill -0 "$PID" 2>/dev/null; do sleep 1; i=$((i + 1)); done
  [ -e "$MARK" ] && ok "T9: o SIGN chegou à passada paralela" || ko "T9: o SIGN não chegou à passada paralela"
  kill -KILL "$PID" 2>/dev/null || printf ''
  wait "$PID" 2>/dev/null || printf ''
  sleep 6
  [ -n "$(git -C "$C" status --porcelain --untracked-files=no)" ] && ok "T9: o kill -9 deixou o patch aplicado (sem desfazer)" || ko "T9: nada sobrou (o cenário não exercitou a sobra)"
  # a mesma sobra de um kill -9 durante o julgamento de uma falha: um worktree da base registrado
  STALE="$(mktemp -d "$WORK/tmp/w1-sign.XXXXXX")/base-wt"
  git -C "$C" worktree add --quiet --detach "$STALE" HEAD >/dev/null 2>&1 && ok "T9: worktree da base órfão plantado" || ko "T9: não consegui plantar o worktree órfão"
  rc=0; run_dry "$C" "$WORK/logs/t9b.log" || rc=$?
  [ "$rc" = "1" ] && ok "T9: a nova execução recusa (rc 1)" || ko "T9: rc $rc (esperado 1)"
  has "$WORK/logs/t9b.log" "removendo o worktree da base de uma execução anterior interrompida" "T9: o P0 removeu o worktree órfão antes de tudo"
  has "$WORK/logs/t9b.log" "execução INTERROMPIDA" "T9: a recusa imprime a receita de recuperação"
  ( cd "$C" && git reset -q HEAD -- . && git apply -R "$PATCH" ) >"$WORK/logs/t9c.log" 2>&1 && ok "T9: a receita impressa desfaz a sobra" || ko "T9: a receita impressa falhou"
  rc=0; run_dry "$C" "$WORK/logs/t9d.log" || rc=$?
  [ "$rc" = "0" ] && ok "T9: depois da receita o ensaio passa (rc 0)" || ko "T9: rc $rc depois da receita"
  clean_tree "$C" "T9"
fi

step "T10 chave de assinatura fora do allowlist recusa no P0, antes de aplicar"
C="$(fresh nokey)"
awk -v f="$FPR" '$0 != f' "$C/.claude/sentinel-signers.txt" > "$WORK/logs/t10.signers"
cp "$WORK/logs/t10.signers" "$C/.claude/sentinel-signers.txt"
commit_file "$C" .claude/sentinel-signers.txt "ensaio: allowlist sem a chave descartável"
rc=0; run_dry "$C" "$WORK/logs/t10.log" || rc=$?
[ "$rc" = "1" ] && ok "T10: rc 1" || ko "T10: rc $rc (esperado 1)"
has "$WORK/logs/t10.log" "sem chave secreta do allowlist" "T10: recusa nomeada"
has "$WORK/logs/t10.log" "nada a desfazer" "T10: nada foi aplicado"
clean_tree "$C" "T10"

step "T15 --check-base: só leitura; nomeia o caminho cuja base difere"
C="$(fresh checkbase)"
cb() {  # clone log revisão → rc do --check-base
  local rc=0
  ( cd "$1" && sign_env > "$WORK/logs/env-cb" && exec env -i $(cat "$WORK/logs/env-cb") bash "$SIGN" --check-base "$3" ) >"$2" 2>&1 </dev/null || rc=$?
  return "$rc"
}
rc=0; cb "$C" "$WORK/logs/t15a.log" HEAD || rc=$?
[ "$rc" = "0" ] && ok "T15: base = HEAD, rc 0" || ko "T15: base = HEAD, rc $rc (esperado 0)"
has "$WORK/logs/t15a.log" "OK: a base pinada da W1" "T15: OK nomeado"
printf '\n# deriva plantada pelo ensaio\n' >> "$C/$TARGET_PATH"
commit_file "$C" "$TARGET_PATH" "ensaio: deriva da base (check-base)"
rc=0; cb "$C" "$WORK/logs/t15b.log" HEAD || rc=$?
[ "$rc" = "1" ] && ok "T15: base derivada, rc 1" || ko "T15: base derivada, rc $rc (esperado 1)"
has "$WORK/logs/t15b.log" "DIFERE: $TARGET_PATH" "T15: o caminho derivado é nomeado"
rc=0; cb "$C" "$WORK/logs/t15c.log" HEAD~1 || rc=$?
[ "$rc" = "0" ] && ok "T15: a revisão anterior à deriva, rc 0" || ko "T15: HEAD~1, rc $rc (esperado 0)"
clean_tree "$C" "T15"

step "T16 cópia staged diferente do pós-imagem do patch recusa no P0"
C="$(fresh stageddiverge)"
printf '\n# a cópia staged diverge do patch (ensaio)\n' >> "$C/$STAGED"
commit_file "$C" "$STAGED" "ensaio: cópia staged divergente"
rc=0; run_dry "$C" "$WORK/logs/t16.log" || rc=$?
[ "$rc" = "1" ] && ok "T16: rc 1" || ko "T16: rc $rc (esperado 1)"
has "$WORK/logs/t16.log" "as duas formas divergem" "T16: recusa nomeada"
has "$WORK/logs/t16.log" "nada a desfazer" "T16: nada foi aplicado"
clean_tree "$C" "T16"

step "T17 controle da W1 que não discrimina: verde no HEAD recusa no P0; vermelho com o patch recusa na bateria"
C="$(fresh shapegreen)"
printf '#!/usr/bin/env python3\n"""ensaio: controle que sempre aprova"""\nraise SystemExit(0)\n' > "$C/$SHAPE"
commit_file "$C" "$SHAPE" "ensaio: controle sempre verde"
rc=0; run_dry "$C" "$WORK/logs/t17a.log" || rc=$?
[ "$rc" = "1" ] && ok "T17a: rc 1" || ko "T17a: rc $rc (esperado 1)"
has "$WORK/logs/t17a.log" "o controle da W1 não reprova no HEAD" "T17a: recusa nomeada"
has "$WORK/logs/t17a.log" "nada a desfazer" "T17a: nada foi aplicado"
clean_tree "$C" "T17a"
C="$(fresh shapered)"
printf '#!/usr/bin/env python3\n"""ensaio: controle que sempre reprova (com a linha de resumo)"""\nprint("RESUMO: 1 falha(s)")\nraise SystemExit(1)\n' > "$C/$SHAPE"
commit_file "$C" "$SHAPE" "ensaio: controle sempre vermelho"
# o registro passa a nomear ESTE controle (como se o rail o tivesse revisado): o que se testa é a bateria
REC="$(set_rec_line "$C" "Rail-Control-sha256: " "Rail-Control-sha256: $(git -C "$C" show "HEAD:$SHAPE" | shasum -a 256 | awk '{print $1}')")"
commit_file "$C" "$REC" "ensaio: registro nomeia o controle novo"
rc=0; run_dry "$C" "$WORK/logs/t17b.log" || rc=$?
[ "$rc" = "1" ] && ok "T17b: rc 1" || ko "T17b: rc $rc (esperado 1)"
has "$WORK/logs/t17b.log" "o controle da W1 reprova na árvore com o patch" "T17b: recusa nomeada"
has "$WORK/logs/t17b.log" "patch-revertido" "T17b: o desfazer reverteu o patch"
clean_tree "$C" "T17b"
C="$(fresh shapecrash)"
# rc 1 por EXCEÇÃO (sem a linha de resumo): não prova que o controle discrimina
printf '#!/usr/bin/env python3\n"""ensaio: controle que quebra"""\nraise KeyError("ensaio")\n' > "$C/$SHAPE"
commit_file "$C" "$SHAPE" "ensaio: controle que quebra com exceção"
REC="$(set_rec_line "$C" "Rail-Control-sha256: " "Rail-Control-sha256: $(git -C "$C" show "HEAD:$SHAPE" | shasum -a 256 | awk '{print $1}')")"
commit_file "$C" "$REC" "ensaio: registro nomeia o controle novo"
rc=0; run_dry "$C" "$WORK/logs/t17c.log" || rc=$?
[ "$rc" = "1" ] && ok "T17c: rc 1" || ko "T17c: rc $rc (esperado 1)"
has "$WORK/logs/t17c.log" "sem 'RESUMO: N falha(s)'" "T17c: rc 1 de exceção não conta como vermelho do controle"
has "$WORK/logs/t17c.log" "nada a desfazer" "T17c: nada foi aplicado"
clean_tree "$C" "T17c"

step "T18 patch que CRIA arquivo recusa no P0, com nome"
C="$(fresh newfilepatch)"
cat >> "$C/$PATCH" <<'EOP'
diff --git a/zz-ensaio-novo.txt b/zz-ensaio-novo.txt
new file mode 100644
index 0000000000000000000000000000000000000000..587be6b4c3f93f93c489c0111bba5596147a26cb
--- /dev/null
+++ b/zz-ensaio-novo.txt
@@ -0,0 +1 @@
+x
EOP
commit_file "$C" "$PATCH" "ensaio: patch que cria arquivo"
rc=0; run_dry "$C" "$WORK/logs/t18.log" || rc=$?
[ "$rc" = "1" ] && ok "T18: rc 1" || ko "T18: rc $rc (esperado 1)"
has "$WORK/logs/t18.log" "o patch cria, remove, renomeia ou copia arquivo, ou muda modo" "T18: recusa nomeada"
has "$WORK/logs/t18.log" "nada a desfazer" "T18: nada foi aplicado"
clean_tree "$C" "T18"

step "T19 sem actionlint no PATH recusa no P0"
C="$(fresh noactionlint)"
rc=0
( cd "$C" && sign_env | sed "s#^PATH=.*#PATH=$WORK/shim:/usr/bin:/bin:/usr/sbin:/sbin#" > "$WORK/logs/env-t19" \
    && exec env -i $(cat "$WORK/logs/env-t19") bash "$SIGN" --dry-run ) >"$WORK/logs/t19.log" 2>&1 </dev/null || rc=$?
[ "$rc" = "1" ] && ok "T19: rc 1" || ko "T19: rc $rc (esperado 1)"
has "$WORK/logs/t19.log" "actionlint ausente do PATH" "T19: recusa nomeada"
clean_tree "$C" "T19"

step "T19b sem shellcheck no PATH (com actionlint) recusa no P0"
C="$(fresh noshellcheck)"
mkdir -p "$WORK/only-actionlint"
[ -e "$WORK/only-actionlint/actionlint" ] || ln -s "$(command -v actionlint)" "$WORK/only-actionlint/actionlint"
rc=0
( cd "$C" && sign_env | sed "s#^PATH=.*#PATH=$WORK/shim:$WORK/only-actionlint:/usr/bin:/bin:/usr/sbin:/sbin#" > "$WORK/logs/env-t19b" \
    && exec env -i $(cat "$WORK/logs/env-t19b") bash "$SIGN" --dry-run ) >"$WORK/logs/t19b.log" 2>&1 </dev/null || rc=$?
[ "$rc" = "1" ] && ok "T19b: rc 1" || ko "T19b: rc $rc (esperado 1)"
has "$WORK/logs/t19b.log" "shellcheck ausente do PATH" "T19b: recusa nomeada"
clean_tree "$C" "T19b"

step "T24 sentinel que cita o marcador de preenchimento fora das 4 linhas de campo recusa no P0"
C="$(fresh tofillprose)"
printf '\nNota do ensaio: o marcador TO-FILL-BY-SIGN citado em prosa.\n' >> "$C/$SENT"
commit_file "$C" "$SENT" "ensaio: marcador citado em prosa no sentinel"
rc=0; run_dry "$C" "$WORK/logs/t24.log" || rc=$?
[ "$rc" = "1" ] && ok "T24: rc 1" || ko "T24: rc $rc (esperado 1)"
has "$WORK/logs/t24.log" "cita TO-FILL-BY-SIGN fora das 4 linhas de campo" "T24: recusa nomeada, antes da bateria"
has "$WORK/logs/t24.log" "nada a desfazer" "T24: nada foi aplicado"
clean_tree "$C" "T24"

if [ "$FULL" = "0" ]; then
  step "T20 achado de actionlint PRÉ-EXISTENTE (mesmo conjunto com e sem o patch) é nota, não bloqueio"
  C="$(fresh alpre)"
  plant_actionlint_red "$C"
  rc=0; run_dry "$C" "$WORK/logs/t20.log" || rc=$?
  [ "$rc" = "0" ] && ok "T20: rc 0" || ko "T20: rc $rc (esperado 0)"
  has "$WORK/logs/t20.log" "PRÉ-EXISTENTE (mesmo conjunto de achados com e sem o patch): actionlint (forma do job validate)" "T20: forma do job validate julgada pelo conjunto"
  has "$WORK/logs/t20.log" "PRÉ-EXISTENTE (mesmo conjunto de achados com e sem o patch): actionlint (forma do actionlint.yml)" "T20: forma do actionlint.yml julgada pelo conjunto"
  clean_tree "$C" "T20"

  step "T21 achado NOVO de actionlint com a base também vermelha reprova (o rc sozinho não basta)"
  C="$(fresh alnew)"
  plant_actionlint_red "$C"
  # um patch que também introduz um achado (timeout-minutes inválido em OUTRO job), rail sintético preso a ele
  rederive "$C" '{ if (!done && $0 == "    timeout-minutes: 8") { print "    timeout-minutes: oito"; done = 1 } else print }' \
    || ko "T21: a montagem do patch com achado falhou"
  rc=0; run_dry "$C" "$WORK/logs/t21.log" || rc=$?
  [ "$rc" = "1" ] && ok "T21: rc 1" || ko "T21: rc $rc (esperado 1)"
  has "$WORK/logs/t21.log" "achado(s) que só existe(m) com o patch" "T21: achado novo nomeado"
  has "$WORK/logs/t21.log" "NOVO: .github/workflows/validate.yml:" "T21: o achado novo é listado"
  has "$WORK/logs/t21.log" "patch-revertido" "T21: o desfazer reverteu o patch"
  clean_tree "$C" "T21"

  step "T25 achado de actionlint com o MESMO texto de um pré-existente, a mais: a contagem sobe e reprova"
  C="$(fresh alsametext)"
  base_edit "$C" '{ if (!done && $0 == "    timeout-minutes: 8") { print "    timeout-minutes: oito"; done = 1 } else print }' "ensaio: achado pré-existente no validate.yml"
  rederive "$C" '{ if (!done && $0 == "    timeout-minutes: 10") { print "    timeout-minutes: oito"; done = 1 } else print }' \
    || ko "T25: a montagem do patch falhou"
  rc=0; run_dry "$C" "$WORK/logs/t25.log" || rc=$?
  [ "$rc" = "1" ] && ok "T25: rc 1" || ko "T25: rc $rc (esperado 1)"
  has "$WORK/logs/t25.log" "achado(s) que só existe(m) com o patch" "T25: a segunda ocorrência do mesmo texto é nova"
  has "$WORK/logs/t25.log" "patch-revertido" "T25: o desfazer reverteu o patch"
  clean_tree "$C" "T25"

  step "T26 validate-governance: violação nova DENTRO do mesmo grupo (mesma contagem de erros) reprova"
  C="$(fresh govsamegroup)"
  # um grupo de violação plantado no validate-governance do clone: UM erro, uma linha de detalhe por marca
  awk '{ if ($0 == "echo \"  Errors:   $ERRORS\"") {
      print "if grep -q \"ENSAIO-GOV-MARCA\" .github/workflows/validate.yml; then"
      print "  echo \"  FAIL: ensaio: marcas no validate.yml:\""
      print "  grep \"ENSAIO-GOV-MARCA\" .github/workflows/validate.yml | sed \"s|^|    |\""
      print "  ERRORS=$((ERRORS + 1))"
      print "fi" }
    print }' "$C/.claude/scripts/validate-governance.sh" > "$C/vg.tmp" && mv "$C/vg.tmp" "$C/.claude/scripts/validate-governance.sh"
  commit_file "$C" .claude/scripts/validate-governance.sh "ensaio: grupo de violação plantado no validate-governance"
  base_edit "$C" '{ print } END { print "# ENSAIO-GOV-MARCA a" }' "ensaio: violação pré-existente (marca a)"
  rederive "$C" '{ print } END { print "# ENSAIO-GOV-MARCA b" }' || ko "T26: a montagem do patch falhou"
  rc=0; run_dry "$C" "$WORK/logs/t26.log" || rc=$?
  [ "$rc" = "1" ] && ok "T26: rc 1" || ko "T26: rc $rc (esperado 1)"
  has "$WORK/logs/t26.log" "NOVO:  # ENSAIO-GOV-MARCA b" "T26: o detalhe novo do mesmo grupo é listado"
  has "$WORK/logs/t26.log" "validate-governance (Errors: 0): achado(s) que só existe(m) com o patch" "T26: o governance reprova pelo detalhe"
  has "$WORK/logs/t26.log" "patch-revertido" "T26: o desfazer reverteu o patch"
  clean_tree "$C" "T26"

  step "T26b validate-governance: detalhe novo que CONTÉM «WARN» (não é linha de aviso) reprova"
  C="$(fresh govwarndetail)"
  awk '{ if ($0 == "echo \"  Errors:   $ERRORS\"") {
      print "if grep -q \"ENSAIO-GOV-MARCA\" .github/workflows/validate.yml; then"
      print "  echo \"  FAIL: ensaio: marcas no validate.yml:\""
      print "  grep \"ENSAIO-GOV-MARCA\" .github/workflows/validate.yml | sed \"s|^|    |\""
      print "  ERRORS=$((ERRORS + 1))"
      print "fi" }
    print }' "$C/.claude/scripts/validate-governance.sh" > "$C/vg.tmp" && mv "$C/vg.tmp" "$C/.claude/scripts/validate-governance.sh"
  commit_file "$C" .claude/scripts/validate-governance.sh "ensaio: grupo de violação plantado no validate-governance"
  base_edit "$C" '{ print } END { print "# ENSAIO-GOV-MARCA a" }' "ensaio: violação pré-existente (marca a)"
  rederive "$C" '{ print } END { print "# ENSAIO-GOV-MARCA status: WARN" }' || ko "T26b: a montagem do patch falhou"
  rc=0; run_dry "$C" "$WORK/logs/t26b.log" || rc=$?
  [ "$rc" = "1" ] && ok "T26b: rc 1" || ko "T26b: rc $rc (esperado 1)"
  has "$WORK/logs/t26b.log" "NOVO:  # ENSAIO-GOV-MARCA status: WARN" "T26b: o detalhe com WARN é listado (aviso só pelo prefixo)"
  has "$WORK/logs/t26b.log" "patch-revertido" "T26b: o desfazer reverteu o patch"
  clean_tree "$C" "T26b"

  step "T22 o sentinel muda durante a bateria: recusa antes de assinar; o abort nomeia e dá a receita"
  C="$(fresh senttouch)"
  rc=0; W1_SHIM_TOUCH="$SENT" run_dry "$C" "$WORK/logs/t22.log" || rc=$?
  [ "$rc" = "1" ] && ok "T22: rc 1" || ko "T22: rc $rc (esperado 1)"
  has "$WORK/logs/t22.log" "o sentinel mudou durante a bateria" "T22: recusa nomeada"
  has "$WORK/logs/t22.log" "patch-revertido" "T22: o desfazer reverteu o patch"
  has "$WORK/logs/t22.log" "para restaurar: git checkout HEAD -- $SENT" "T22: o abort lista o sentinel com a receita"
  ( cd "$C" && git checkout HEAD -- "$SENT" ) >"$WORK/logs/t22c.log" 2>&1 && ok "T22: a receita restaura" || ko "T22: a receita falhou"
  clean_tree "$C" "T22"

  step "T23 abort no meio da bateria com arquivo de FORA sujo: o abort o lista com a receita"
  C="$(fresh abortdirty)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_w1_plant_new.py" <<'PY'
"""Ensaio W1: passa na árvore SEM o patch (o validate.yml não citava o rótulo 26.04)."""
from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def test_validate_yml_names_no_26_04_label():
    text = (_REPO / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
    assert "ubuntu-26.04" not in text
PY
  commit_file "$C" tests/unit/test_zz_w1_plant_new.py "ensaio: plant (falha nova)"
  rc=0; W1_SHIM_TOUCH=README.md W1_SHIM_FAIL="tests/unit/test_zz_w1_plant_new.py::test_validate_yml_names_no_26_04_label" run_dry "$C" "$WORK/logs/t23.log" || rc=$?
  [ "$rc" = "1" ] && ok "T23: rc 1" || ko "T23: rc $rc (esperado 1)"
  has "$WORK/logs/t23.log" "falhas NOVAS" "T23: a falha nova abortou"
  has "$WORK/logs/t23.log" "o desfazer NÃO restaurou" "T23: o abort avisa do que sobrou"
  has "$WORK/logs/t23.log" "para restaurar: git checkout HEAD -- README.md" "T23: o abort lista o README.md com a receita"
  ( cd "$C" && git checkout HEAD -- README.md ) >"$WORK/logs/t23c.log" 2>&1 && ok "T23: a receita restaura" || ko "T23: a receita falhou"
  clean_tree "$C" "T23"
fi

if [ "$FULL" = "0" ]; then
  step "T11 id parametrizado com « - » no parâmetro é rerrodado pelo id inteiro"
  C="$(fresh dashid)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_w1_plant_dash.py" <<'PY'
"""Ensaio W1: um id parametrizado cujo parâmetro contém « - » (passa nas duas árvores)."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("v", ["a - b"])
def test_dash_param(v):
    assert v == "a - b"
PY
  commit_file "$C" tests/unit/test_zz_w1_plant_dash.py "ensaio: plant (id com « - »)"
  DASH_ID="tests/unit/test_zz_w1_plant_dash.py::test_dash_param[a - b]"
  printf '%s\n' "$DASH_ID" > "$WORK/logs/t11.fail"
  rc=0; W1_SHIM_FAIL_FILE="$WORK/logs/t11.fail" run_dry "$C" "$WORK/logs/t11.log" || rc=$?
  [ "$rc" = "0" ] && ok "T11: rc 0" || ko "T11: rc $rc (esperado 0)"
  has "$WORK/logs/t11.log" "instável (passou isolada, com o patch, na tentativa 1 de 3): $DASH_ID" "T11: rerrodado pelo id inteiro (com « - »)"
  clean_tree "$C" "T11"

  step "T12 o HEAD muda durante a bateria: recusa antes do sentinel e desfaz"
  C="$(fresh headmove)"
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; W1_SHIM_COMMIT=1 run_dry "$C" "$WORK/logs/t12.log" || rc=$?
  [ "$rc" = "1" ] && ok "T12: rc 1" || ko "T12: rc $rc (esperado 1)"
  has "$WORK/logs/t12.log" "o HEAD mudou durante a bateria" "T12: recusa nomeada"
  has "$WORK/logs/t12.log" "patch-revertido" "T12: o desfazer reverteu o patch"
  [ "$(git -C "$C" rev-parse HEAD~1)" = "$H0" ] && ok "T12: só o commit plantado a mais" || ko "T12: histórico inesperado"
  clean_tree "$C" "T12"

  step "T13 o caminho do patch muda durante a bateria: recusa; a receita impressa restaura"
  C="$(fresh touchpatched)"
  rc=0; W1_SHIM_TOUCH="$TARGET_PATH" run_dry "$C" "$WORK/logs/t13.log" || rc=$?
  [ "$rc" = "1" ] && ok "T13: rc 1" || ko "T13: rc $rc (esperado 1)"
  has "$WORK/logs/t13.log" "$TARGET_PATH mudou durante a bateria" "T13: recusa nomeada pelo caminho"
  has "$WORK/logs/t13.log" "CAMINHOS-DO-PATCH-AINDA-SUJOS" "T13: o desfazer diz que um caminho do patch ficou sujo"
  has "$WORK/logs/t13.log" "restaure a pré-imagem com: git checkout HEAD --" "T13: a receita é impressa"
  ( cd "$C" && git checkout HEAD -- "$TARGET_PATH" ) >"$WORK/logs/t13c.log" 2>&1 && ok "T13: a receita restaura" || ko "T13: a receita falhou"
  clean_tree "$C" "T13"

  step "T14 modo REAL: um arquivo rastreado FORA do patch sujo pela bateria — commit exato, aviso nomeado"
  C="$(fresh realdirty)"
  OUTSIDE=README.md
  git -C "$C" ls-files --error-unmatch -- "$OUTSIDE" >/dev/null 2>&1 || { ko "T14: $OUTSIDE não é rastreado"; }
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; W1_SHIM_TOUCH="$OUTSIDE" run_real_tty "$C" "$WORK/logs/t14.log" || rc=$?
  [ "$rc" = "0" ] && ok "T14: rc 0" || ko "T14: rc $rc"
  has "$WORK/logs/t14.log" "LANDADO em" "T14: landou"
  has "$WORK/logs/t14.log" "AVISO: arquivos rastreados fora do patch mudaram durante a bateria" "T14: aviso depois da bateria"
  has "$WORK/logs/t14.log" "ATENÇÃO: a árvore rastreada ficou suja" "T14: aviso depois do commit"
  [ "$(git -C "$C" rev-parse HEAD~1)" = "$H0" ] && ok "T14: exatamente um commit novo" || ko "T14: HEAD~1 != HEAD anterior"
  git -C "$C" show --name-only --format= HEAD | sort > "$WORK/logs/t14.committed"
  { awk '/^diff --git /{p=$3; sub(/^a\//, "", p); print p}' "$C/$PATCH"; printf '%s\n%s\n' "$SENT" "$SENT.asc"; } | sort -u > "$WORK/logs/t14.expected"
  cmp -s "$WORK/logs/t14.committed" "$WORK/logs/t14.expected" && ok "T14: o commit NÃO inclui o arquivo de fora" || ko "T14: conjunto commitado inesperado: $(comm -3 "$WORK/logs/t14.committed" "$WORK/logs/t14.expected" | tr '\n' ' ')"
  [ "$(git -C "$C" diff --name-only)" = "$OUTSIDE" ] && ok "T14: só o arquivo de fora ficou sujo" || ko "T14: sujeira inesperada: $(git -C "$C" diff --name-only | tr '\n' ' ')"
fi

COMPLETED=1
step "RESUMO"
printf '  %s PASS / %s FAIL (logs em %s/logs)\n' "$PASS" "$FAIL" "$WORK"
[ "$FAIL" = "0" ]
