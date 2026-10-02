#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: harness de ensaio do OWNER-AUDITRACE-SIGN.sh (PLAN-194, cura
# da corrida no gravador do agent_spawn), clonado do test-ceremony-fn04.sh (PLAN-193 W4b). Muda,
# declarado: as constantes; os cenários plantados (caminhos e testes desta cura); o T2 roda os testes
# da cura na árvore landada; o T1/T2 conferem o override de kernel (par validado vivo, armado só em
# volta do git apply) e o T17 o recusa quando já vem do ambiente; rodada 3 do rail: a falha instável do
# T2 é injetada FORA dos arquivos da cura e o T18 prova que a falha de um teste da cura reprova sem
# rerun; o T6 também adultera o Rail-Text-sha256; o T19 recusa um patch com cabeçalho estrutural antes
# de aplicar e o T20 recusa evidência citada que não está commitada; anexo da rodada 3: o T21 muda o
# sentinel vivo durante a bateria (recusa antes do passo 4, com a receita) e o T22 cita o marcador dos
# campos fora das 4 linhas de campo (recusa no P0); e, quando o HEAD da origem ainda não
# tem registro de rail
# (o rail é do CEO, depois do ensaio), a montagem planta um rail-round-1.md SINTÉTICO, rotulado
# «ENSAIO», só no remote descartável — o registro real substitui o sintético e o ensaio é refeito.
# test-ceremony-auditrace.sh — ensaia o SIGN em CLONES descartáveis, com uma chave GPG descartável;
# nunca toca o repositório de origem, o chaveiro do Owner nem o $HOME real.
#
#   bash .claude/plans/PLAN-194/w-auditrace/test-ceremony-auditrace.sh [--work <dir>] [--src <repo>] [--full-suite]
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
#   - HOME falso em <work>/home (PYTHONUSERBASE aponta para o do usuário, onde está o pytest), e o
#     SIGN roda sob `env -i` com esse ambiente mínimo;
#   - SEM --full-suite: um `python3` de fachada no PATH responde SÓ às duas passadas inteiras do
#     pytest (paralela e serial) com uma saída sintética controlada pelo cenário; todo o resto
#     (gates, testes da cura, reruns isolados, worktree da base) roda de verdade. Com
#     --full-suite as suítes rodam inteiras.
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
D=.claude/plans/PLAN-194/w-auditrace
SIGN="$D/OWNER-AUDITRACE-SIGN.sh"
SENT=.claude/plans/PLAN-194/wave-auditrace-approved.md
PATCH="$D/auditrace.patch"
DRIFT=.claude/hooks/tests/test_audit_log.py
git -C "$SRC" cat-file -e "$SRC_HEAD:$SIGN" 2>/dev/null || { printf 'o HEAD de %s não tem %s commitado — commite os materiais antes do ensaio\n' "$SRC" "$SIGN" >&2; exit 2; }
if [ -n "$WORK" ]; then
  [ ! -e "$WORK" ] || { printf '%s já existe — use um diretório novo\n' "$WORK" >&2; exit 2; }
  mkdir -p "$WORK"
else
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/auditrace-rehearsal.XXXXXX")"
fi
WORK="$(cd "$WORK" && pwd -P)"
SOCKDIR="$(mktemp -d "${TMPDIR:-/tmp}/auditraceg.XXXXXX")"
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
mkdir -p "$(dirname "$REMOTE")" "$WORK/home" "$WORK/shim" "$WORK/logs"
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
  --quick-gen-key 'Auditrace Rehearsal Throwaway <auditrace-rehearsal@example.invalid>' ed25519 sign never >"$WORK/logs/keygen.log" 2>&1
FPR="$(GNUPGHOME="$GNUPGHOME" gpg --list-secret-keys --with-colons 2>/dev/null | awk -F: '$1 == "fpr" {print $10; exit}')"
[ -n "$FPR" ] || { tail -5 "$WORK/logs/keygen.log" >&2; printf 'não consegui gerar a chave descartável\n' >&2; exit 1; }
REALPY="$(command -v python3)"
PYUB="$(python3 -m site --user-base)"
cat > "$WORK/shim/python3" <<SHIM
#!/bin/bash
# fachada do ensaio: responde SÓ às duas passadas inteiras do pytest do SIGN; o resto é o python3 real
if [ "\${1:-}" = "-m" ] && [ "\${2:-}" = "pytest" ] && [ "\${3:-}" = "-n" ] && [ "\${4:-}" = "auto" ]; then
  [ -z "\${AUDITRACE_SHIM_MARK:-}" ] || : > "\$AUDITRACE_SHIM_MARK"
  [ -z "\${AUDITRACE_SHIM_SLEEP:-}" ] || sleep "\$AUDITRACE_SHIM_SLEEP"
  # efeitos colaterais de uma bateria longa: outro commit no meio, um arquivo rastreado escrito
  [ -z "\${AUDITRACE_SHIM_COMMIT:-}" ] || git commit -q --allow-empty -m "ensaio: commit durante a bateria"
  [ -z "\${AUDITRACE_SHIM_TOUCH:-}" ] || printf '\n# escrito pela bateria do ensaio\n' >> "\$AUDITRACE_SHIM_TOUCH"
  if [ -n "\${AUDITRACE_SHIM_FAIL_FILE:-}" ]; then
    while IFS= read -r t; do printf 'FAILED %s - injetada pelo ensaio\n' "\$t"; done < "\$AUDITRACE_SHIM_FAIL_FILE"
    printf '1 failed, 10 passed in 0.01s\n'
    exit 1
  fi
  if [ -n "\${AUDITRACE_SHIM_FAIL:-}" ]; then
    for t in \$AUDITRACE_SHIM_FAIL; do printf 'FAILED %s - injetada pelo ensaio\n' "\$t"; done
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
# a chave descartável entra no allowlist de signatários do remote (commit de ensaio, empurrado ao bare)
STAGE="$WORK/c-stage"
git clone --quiet "$REMOTE" "$STAGE"
git -C "$STAGE" config user.name "Auditrace Rehearsal"
git -C "$STAGE" config user.email "auditrace-rehearsal@example.invalid"
printf '# ENSAIO: chave descartável do test-ceremony-auditrace.sh\n%s\n' "$FPR" >> "$STAGE/.claude/sentinel-signers.txt"
git -C "$STAGE" add -- .claude/sentinel-signers.txt
SYNTH_RAIL=0
if ! ls "$STAGE/$D"/rail-round-*.md >/dev/null 2>&1; then
  # Sem registro de rail na origem: um registro SINTÉTICO, só neste remote descartável, para ensaiar
  # o resto do SIGN. Nunca vale para o land real: o SIGN da árvore real lê o registro commitado.
  SYNTH_RAIL=1
  PSHA0="$(shasum -a 256 "$STAGE/$PATCH" | awk '{print $1}')"
  TSHA0="$(shasum -a 256 "$STAGE/$SENT" | awk '{print $1}')"
  {
    printf '# rail-round-1 — ENSAIO (registro SINTÉTICO do test-ceremony-auditrace.sh; não é rail)\n\n'
    printf 'Rail-Round: 1\nRail-Subject: %s\nRail-Subject-sha256: %s\nRail-Text-sha256: %s\n' "$PATCH" "$PSHA0" "$TSHA0"
    printf 'Rail-Reviewer: ENSAIO (nenhum revisor rodou)\nRail-Verdict: APPROVE\nRail-Findings: P0=0 P1=0 P2=0\n'
  } > "$STAGE/$D/rail-round-1.md"
  git -C "$STAGE" add -- "$D/rail-round-1.md"
fi
git -C "$STAGE" commit -q -m "ensaio: chave descartável no allowlist de signatários (e registro de rail sintético, se faltava)"
git -C "$STAGE" push -q origin HEAD:main
printf '  origem %s @ %s\n  área %s\n  chave descartável %s (no allowlist do remote: %s)\n  suítes: %s\n  registro de rail: %s\n' "$SRC" "$SRC_HEAD" "$WORK" "$FPR" \
  "$(git -C "$STAGE" rev-parse --short HEAD)" \
  "$([ "$FULL" = "1" ] && printf 'INTEIRAS' || printf 'fachada (só as duas passadas inteiras)')" \
  "$([ "$SYNTH_RAIL" = "1" ] && printf 'SINTÉTICO (a origem ainda não tem rail-round-*.md)' || printf 'o da origem')"

fresh() {  # clone novo em main, com identidade sintética; imprime o caminho
  local c="$WORK/c-$1"
  git clone --quiet "$REMOTE" "$c"
  git -C "$c" config user.name "Auditrace Rehearsal"
  git -C "$c" config user.email "auditrace-rehearsal@example.invalid"
  printf '%s' "$c"
}
sign_env() {  # o ambiente mínimo do SIGN no ensaio
  printf '%s\n' "HOME=$WORK/home" "PATH=$SPATH" "TMPDIR=${TMPDIR:-/tmp}" "GNUPGHOME=$GNUPGHOME" \
    "PYTHONUSERBASE=$PYUB" "LANG=en_US.UTF-8" "LC_ALL=en_US.UTF-8" "TERM=${TERM:-xterm}" "USER=${USER:-rehearsal}" \
    "AUDITRACE_SHIM_FAIL=${AUDITRACE_SHIM_FAIL:-}" "AUDITRACE_SHIM_SLEEP=${AUDITRACE_SHIM_SLEEP:-}" "AUDITRACE_SHIM_MARK=${AUDITRACE_SHIM_MARK:-}" \
    "AUDITRACE_SHIM_FAIL_FILE=${AUDITRACE_SHIM_FAIL_FILE:-}" "AUDITRACE_SHIM_COMMIT=${AUDITRACE_SHIM_COMMIT:-}" "AUDITRACE_SHIM_TOUCH=${AUDITRACE_SHIM_TOUCH:-}"
  if [ -n "${AUDITRACE_KERNEL_PRESET:-}" ]; then
    printf '%s\n' "CEO_KERNEL_OVERRIDE=sobra-de-outra-cerimonia" "CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT"
  fi
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
FLAKY=".claude/hooks/tests/test_audit_rotation.py::TestRotateIfNeeded::test_missing_file_returns_none"  # FORA da cura
CURE_ID=".claude/hooks/tests/test_two_writer_chain.py::TestTwoWriterChain::test_append_entry_writes_hmac_field"

step "T0 ceremony-lint e bits de execução no índice"
C="$(fresh lint)"
if (cd "$C" && python3 .claude/scripts/check-ceremony-script.py) >"$WORK/logs/t0.log" 2>&1; then ok "T0: ceremony-lint 0 BLOCKING"; else ko "T0: ceremony-lint reprovou"; tail -12 "$WORK/logs/t0.log" | sed 's/^/        | /'; fi
for f in "$SIGN" "$D/test-ceremony-auditrace.sh" "$D/derive-auditrace-patch.sh"; do
  m="$(git -C "$C" ls-files -s -- "$f" | awk '{print $1}')"
  [ "$m" = "100644" ] && ok "T0: $f modo $m no índice" || ko "T0: $f modo '$m' no índice (esperado 100644)"
  # classe bash 3.2: numa locale UTF-8 o byte seguinte a `$nome` conta como parte do nome
  if LC_ALL=C grep -nE '\$[A-Za-z_][A-Za-z0-9_]*[^ -~]' "$C/$f" >"$WORK/logs/t0-adj.log" 2>&1; then
    ko "T0: $f tem variável colada a caractere não-ASCII (use \${nome}):"; sed 's/^/        | /' "$WORK/logs/t0-adj.log"
  else
    ok "T0: $f sem variável colada a caractere não-ASCII"
  fi
done

step "T1 --dry-run no caminho feliz"
C="$(fresh dry)"
H0="$(git -C "$C" rev-parse HEAD)"
rc=0; run_dry "$C" "$WORK/logs/t1.log" || rc=$?
[ "$rc" = "0" ] && ok "T1: rc 0" || ko "T1: rc $rc"
has "$WORK/logs/t1.log" "Ensaio OK" "T1: ensaio concluído"
has "$WORK/logs/t1.log" "blobs conferidos contra o index pós-imagem" "T1: pós-imagem conferida"
has "$WORK/logs/t1.log" "testes da cura:" "T1: os testes da cura rodaram de verdade"
has "$WORK/logs/t1.log" "par do override validado vivo contra o hook" "T1: o par do override de kernel foi validado vivo no hook"
has "$WORK/logs/t1.log" "override de kernel armado só em volta do git apply (desarmado agora)" "T1: o override de kernel foi armado e desarmado em volta do apply"
[ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T1: HEAD inalterado" || ko "T1: HEAD mudou"
clean_tree "$C" "T1"

step "T2 modo REAL sob pseudo-TTY, chave descartável, uma falha instável injetada"
C="$(fresh real)"
H0="$(git -C "$C" rev-parse HEAD)"
rc=0; AUDITRACE_SHIM_FAIL="$FLAKY" run_real_tty "$C" "$WORK/logs/t2.log" || rc=$?
[ "$rc" = "0" ] && ok "T2: rc 0" || ko "T2: rc $rc"
has "$WORK/logs/t2.log" "LANDADO em" "T2: landou"
if [ "$FULL" = "0" ]; then has "$WORK/logs/t2.log" "instável (passou isolada, com o patch" "T2: a falha injetada foi julgada instável pelo rerun isolado"; fi
[ "$(git -C "$C" rev-parse HEAD~1)" = "$H0" ] && ok "T2: exatamente um commit novo sobre o HEAD" || ko "T2: HEAD~1 != HEAD anterior"
git -C "$C" show --name-only --format= HEAD | sort > "$WORK/logs/t2.committed"
{ awk '/^diff --git /{p=$3; sub(/^a\//, "", p); print p}' "$C/$PATCH"; printf '%s\n%s\n' "$SENT" "$SENT.asc"; } | sort -u > "$WORK/logs/t2.expected"
cmp -s "$WORK/logs/t2.committed" "$WORK/logs/t2.expected" && ok "T2: o commit tem exatamente os 3 caminhos + sentinel + .asc" || ko "T2: conjunto commitado inesperado: $(comm -3 "$WORK/logs/t2.committed" "$WORK/logs/t2.expected" | tr '\n' ' ')"
if GNUPGHOME="$GNUPGHOME" gpg --verify "$C/$SENT.asc" "$C/$SENT" >"$WORK/logs/t2.verify" 2>&1; then ok "T2: a assinatura verifica"; else ko "T2: a assinatura não verifica"; fi
grep -qF "$FPR" "$WORK/logs/t2.verify" && ok "T2: assinada pela chave descartável" || ko "T2: signatário inesperado"
awk '/^diff --git /{p=$3; sub(/^a\//, "", p)} /^index /{split($2, h, /\.\./); print p, h[2]}' "$C/$PATCH" > "$WORK/logs/t2.blobs"
bad=0
while read -r p new; do
  [ "$(git -C "$C" rev-parse "HEAD:$p")" = "$new" ] || { bad=1; ko "T2: $p landou com blob diferente do revisado"; }
done < "$WORK/logs/t2.blobs"
[ "$bad" = "0" ] && ok "T2: os 3 blobs landados são os do index pós-imagem do patch"
[ "$(git -C "$C" ls-files -s -- .claude/hooks/audit_log.py | awk '{print $1}')" = "100755" ] && ok "T2: o hook landou com modo 100755" || ko "T2: o hook perdeu o bit de execução"
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
grep -qF "Cura o caso da condição 67" "$WORK/logs/t2.msg" && ok "T2: a mensagem declara o CASO" || ko "T2: a mensagem não declara o caso"
grep -qF "Kernel: audit_log.py está em _KERNEL_PATHS" "$WORK/logs/t2.msg" && ok "T2: a mensagem registra o override de kernel" || ko "T2: a mensagem não registra o override de kernel"
has "$WORK/logs/t2.log" "override de kernel armado só em volta do git apply (desarmado agora)" "T2: o override de kernel foi armado e desarmado em volta do apply"
[ -z "$(git -C "$C" status --porcelain --untracked-files=no)" ] && ok "T2: árvore limpa depois do land" || ko "T2: árvore suja depois do land"
[ "$(git -C "$C" worktree list | wc -l | tr -d ' ')" = "1" ] && ok "T2: nenhum worktree da base sobrou" || ko "T2: worktree sobrou"
if (cd "$C" && env HOME="$WORK/home" PYTHONUSERBASE="$PYUB" PYTHONPATH=. python3 -m pytest .claude/hooks/tests/test_two_writer_chain.py .claude/hooks/tests/test_audit_log.py -q -p no:cacheprovider) >"$WORK/logs/t2.cure" 2>&1; then
  ok "T2: os testes da cura passam na árvore landada (censo por AST incluído)"
else
  ko "T2: os testes da cura reprovam na árvore landada"; tail -8 "$WORK/logs/t2.cure" | sed 's/^/        | /'
fi

if [ "$FULL" = "0" ]; then
  step "T3 falha NOVA (passa sem o patch, falha com ele) aborta e restaura"
  C="$(fresh newfail)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_auditrace_plant_new.py" <<'PY'
"""Ensaio auditrace: passa na árvore SEM o patch (o elo é lido antes da trava)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


class Plant(TestEnvContext):
    def test_prev_read_comes_before_the_lock(self):
        src = (Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "audit_log.py").read_text()
        self.assertLess(src.index("read_prev_hmac()"), src.index('with FileLock(paths["lock"]'))
PY
  commit_file "$C" tests/unit/test_zz_auditrace_plant_new.py "ensaio: plant (falha nova)"
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; AUDITRACE_SHIM_FAIL="tests/unit/test_zz_auditrace_plant_new.py::Plant::test_prev_read_comes_before_the_lock" run_dry "$C" "$WORK/logs/t3.log" || rc=$?
  [ "$rc" = "1" ] && ok "T3: rc 1" || ko "T3: rc $rc (esperado 1)"
  has "$WORK/logs/t3.log" "falhas NOVAS" "T3: a falha nova foi nomeada"
  has "$WORK/logs/t3.log" "patch-revertido" "T3: o desfazer reverteu o patch"
  [ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T3: HEAD inalterado" || ko "T3: HEAD mudou"
  clean_tree "$C" "T3"

  step "T4 falha PRÉ-EXISTENTE (falha com e sem o patch) é nota, não bloqueio"
  C="$(fresh prefail)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_auditrace_plant_pre.py" <<'PY'
"""Ensaio auditrace: falha nas duas árvores (vermelho pré-existente)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


class Plant(TestEnvContext):
    def test_always_red(self):
        self.fail("vermelho pré-existente plantado pelo ensaio")
PY
  commit_file "$C" tests/unit/test_zz_auditrace_plant_pre.py "ensaio: plant (pré-existente)"
  rc=0; AUDITRACE_SHIM_FAIL="tests/unit/test_zz_auditrace_plant_pre.py::Plant::test_always_red" run_dry "$C" "$WORK/logs/t4.log" || rc=$?
  [ "$rc" = "0" ] && ok "T4: rc 0" || ko "T4: rc $rc (esperado 0)"
  has "$WORK/logs/t4.log" "PRÉ-EXISTENTE (falha também sem o patch)" "T4: nomeada como pré-existente"
  has "$WORK/logs/t4.log" "ATENÇÃO — vermelhos PRÉ-EXISTENTES" "T4: resumo final avisa"
  clean_tree "$C" "T4"
fi

step "T5 base derivada (um caminho do patch mudou fora dos hunks) recusa no P0"
C="$(fresh drift)"
printf '\n# deriva plantada pelo ensaio\n' >> "$C/$DRIFT"
commit_file "$C" "$DRIFT" "ensaio: deriva da base"
rc=0; run_dry "$C" "$WORK/logs/t5.log" || rc=$?
[ "$rc" = "1" ] && ok "T5: rc 1" || ko "T5: rc $rc (esperado 1)"
has "$WORK/logs/t5.log" "a base de $DRIFT mudou" "T5: a deriva é nomeada pelo caminho"
has "$WORK/logs/t5.log" "nada a desfazer" "T5: nada foi aplicado"
clean_tree "$C" "T5"

step "T6 registro de rail de OUTRO patch, e veredito não aceito, recusam no P0"
for v in subject verdict text; do
  C="$(fresh "rail-$v")"
  REC="$(ls "$C/$D"/rail-round-*.md | awk -F'rail-round-' '{sub(/\.md$/, "", $2); print $2}' | sort -n | awk 'END {print}')"
  REC="$D/rail-round-$REC.md"
  if [ "$v" = "subject" ]; then
    awk '{ if (index($0, "Rail-Subject-sha256: ") == 1) print "Rail-Subject-sha256: " sprintf("%064d", 0); else print }' "$C/$REC" > "$C/$REC.tmp"
    want="revisou outro patch"
  elif [ "$v" = "text" ]; then
    awk '{ if (index($0, "Rail-Text-sha256: ") == 1) print "Rail-Text-sha256: " sprintf("%064d", 0); else print }' "$C/$REC" > "$C/$REC.tmp"
    want="revisou outro texto assinável"
  else
    awk '{ if (index($0, "Rail-Verdict: ") == 1) print "Rail-Verdict: NO-GO"; else print }' "$C/$REC" > "$C/$REC.tmp"
    want="só aceita APPROVE ou DECLARED-P2"
  fi
  mv "$C/$REC.tmp" "$C/$REC"
  commit_file "$C" "$REC" "ensaio: registro de rail adulterado ($v)"
  rc=0; run_dry "$C" "$WORK/logs/t6-$v.log" || rc=$?
  [ "$rc" = "1" ] && ok "T6-$v: rc 1" || ko "T6-$v: rc $rc (esperado 1)"
  has "$WORK/logs/t6-$v.log" "$want" "T6-$v: recusa nomeada"
  clean_tree "$C" "T6-$v"
done

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
  ( cd "$C" && AUDITRACE_SHIM_SLEEP=15 AUDITRACE_SHIM_MARK="$MARK" sign_env > "$WORK/logs/env-t8" \
      && exec env -i $(cat "$WORK/logs/env-t8") bash "$SIGN" --dry-run ) >"$WORK/logs/t8.log" 2>&1 </dev/null &
  PID=$!
  i=0
  while [ ! -e "$MARK" ] && [ "$i" -lt 900 ] && kill -0 "$PID" 2>/dev/null; do sleep 1; i=$((i + 1)); done
  if [ -e "$MARK" ]; then
    kill -TERM "$PID"
    rc=0; wait "$PID" || rc=$?
    [ "$rc" = "143" ] && ok "T8: rc 143 (TERM)" || ko "T8: rc $rc (esperado 143)"
    has "$WORK/logs/t8.log" "patch-revertido" "T8: o desfazer reverteu o patch"
    clean_tree "$C" "T8"
  else
    kill -TERM "$PID" 2>/dev/null || printf ''
    ko "T8: o SIGN não chegou à passada paralela (terminou antes ou passou de 900 s):"; tail -8 "$WORK/logs/t8.log" | sed 's/^/        | /'
  fi

  step "T9 SIGKILL deixa sobra; a nova execução a nomeia e a receita impressa a desfaz"
  C="$(fresh sigkill)"
  MARK="$WORK/logs/t9.mark"
  ( cd "$C" && AUDITRACE_SHIM_SLEEP=5 AUDITRACE_SHIM_MARK="$MARK" sign_env > "$WORK/logs/env-t9" \
      && exec env -i $(cat "$WORK/logs/env-t9") bash "$SIGN" --dry-run ) >"$WORK/logs/t9a.log" 2>&1 </dev/null &
  PID=$!
  i=0
  while [ ! -e "$MARK" ] && [ "$i" -lt 900 ] && kill -0 "$PID" 2>/dev/null; do sleep 1; i=$((i + 1)); done
  [ -e "$MARK" ] && ok "T9: o SIGN chegou à passada paralela" || ko "T9: o SIGN não chegou à passada paralela"
  kill -KILL "$PID" 2>/dev/null || printf ''
  wait "$PID" 2>/dev/null || printf ''
  sleep 6
  [ -n "$(git -C "$C" status --porcelain --untracked-files=no)" ] && ok "T9: o kill -9 deixou o patch aplicado (sem desfazer)" || ko "T9: nada sobrou (o cenário não exercitou a sobra)"
  # a mesma sobra de um kill -9 durante o julgamento de uma falha: um worktree da base registrado
  STALE="$(mktemp -d "${TMPDIR:-/tmp}/auditrace-sign.XXXXXX")/base-wt"
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

step "T17 override de kernel que já vem do ambiente recusa no P0, antes de aplicar"
C="$(fresh kpreset)"
rc=0; AUDITRACE_KERNEL_PRESET=1 run_dry "$C" "$WORK/logs/t17.log" || rc=$?
[ "$rc" = "1" ] && ok "T17: rc 1" || ko "T17: rc $rc (esperado 1)"
has "$WORK/logs/t17.log" "já estão no ambiente ANTES deste script" "T17: recusa nomeada"
has "$WORK/logs/t17.log" "nada a desfazer" "T17: nada foi aplicado"
clean_tree "$C" "T17"

if [ "$FULL" = "0" ]; then
  step "T18 a falha de um teste da CURA reprova sem rerun (tolerância zero) e desfaz"
  C="$(fresh curefail)"
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; AUDITRACE_SHIM_FAIL="$CURE_ID" run_dry "$C" "$WORK/logs/t18.log" || rc=$?
  [ "$rc" = "1" ] && ok "T18: rc 1" || ko "T18: rc $rc (esperado 1)"
  has "$WORK/logs/t18.log" "teste da cura falhou: $CURE_ID — tolerância zero" "T18: recusa nomeada pelo id"
  has "$WORK/logs/t18.log" "patch-revertido" "T18: o desfazer reverteu o patch"
  grep -qF "instável (passou isolada" "$WORK/logs/t18.log" && ko "T18: o teste da cura foi tratado como instável" || ok "T18: nenhum rerun de «instável»"
  [ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T18: HEAD inalterado" || ko "T18: HEAD mudou"
  clean_tree "$C" "T18"
fi

step "T19 patch com cabeçalho estrutural recusa no P0, pelo nome, antes de aplicar"
C="$(fresh structural)"
awk '{ print } index($0, "diff --git a/.claude/hooks/tests/test_audit_log.py ") == 1 { print "old mode 100644"; print "new mode 100755" }' \
  "$C/$PATCH" > "$C/$PATCH.tmp" && mv "$C/$PATCH.tmp" "$C/$PATCH"
commit_file "$C" "$PATCH" "ensaio: patch com troca de modo"
rc=0; run_dry "$C" "$WORK/logs/t19.log" || rc=$?
[ "$rc" = "1" ] && ok "T19: rc 1" || ko "T19: rc $rc (esperado 1)"
has "$WORK/logs/t19.log" "cabeçalho estrutural" "T19: recusa nomeada"
has "$WORK/logs/t19.log" "nada a desfazer" "T19: nada foi aplicado"
grep -qF "override de kernel armado" "$WORK/logs/t19.log" && ko "T19: o kernel foi armado" || ok "T19: o kernel não foi armado"
clean_tree "$C" "T19"

step "T20 evidência citada pelo sentinel fora do git recusa no P0"
C="$(fresh evidence)"
git -C "$C" rm -q --cached -- "$D/red-control.txt"
git -C "$C" commit -q -m "ensaio: evidência fora do git"
rc=0; run_dry "$C" "$WORK/logs/t20.log" || rc=$?
[ "$rc" = "1" ] && ok "T20: rc 1" || ko "T20: rc $rc (esperado 1)"
has "$WORK/logs/t20.log" "$D/red-control.txt não está commitado" "T20: recusa nomeada"
has "$WORK/logs/t20.log" "nada a desfazer" "T20: nada foi aplicado"

step "T22 o sentinel cita o marcador dos campos fora das 4 linhas de campo: recusa no P0"
C="$(fresh markerprose)"
printf '\nNota do ensaio: os campos TO-FILL-BY-SIGN acima.\n' >> "$C/$SENT"
commit_file "$C" "$SENT" "ensaio: marcador na prosa do sentinel"
rc=0; run_dry "$C" "$WORK/logs/t22.log" || rc=$?
[ "$rc" = "1" ] && ok "T22: rc 1" || ko "T22: rc $rc (esperado 1)"
has "$WORK/logs/t22.log" "o sentinel cita TO-FILL-BY-SIGN fora das 4 linhas de campo" "T22: recusa nomeada"
has "$WORK/logs/t22.log" "nada a desfazer" "T22: nada foi aplicado"
clean_tree "$C" "T22"

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
has "$WORK/logs/t15a.log" "OK: a base pinada da cura auditrace" "T15: OK nomeado"
printf '\n# deriva plantada pelo ensaio\n' >> "$C/$DRIFT"
commit_file "$C" "$DRIFT" "ensaio: deriva da base (check-base)"
rc=0; cb "$C" "$WORK/logs/t15b.log" HEAD || rc=$?
[ "$rc" = "1" ] && ok "T15: base derivada, rc 1" || ko "T15: base derivada, rc $rc (esperado 1)"
has "$WORK/logs/t15b.log" "DIFERE: $DRIFT" "T15: o caminho derivado é nomeado"
rc=0; cb "$C" "$WORK/logs/t15c.log" HEAD~1 || rc=$?
[ "$rc" = "0" ] && ok "T15: a revisão anterior à deriva, rc 0" || ko "T15: HEAD~1, rc $rc (esperado 0)"
clean_tree "$C" "T15"

if [ "$FULL" = "0" ]; then
  step "T11 id parametrizado com « - » no parâmetro é rerrodado pelo id inteiro"
  C="$(fresh dashid)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_auditrace_plant_dash.py" <<'PY'
"""Ensaio auditrace: um id parametrizado cujo parâmetro contém « - » (passa nas duas árvores)."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("v", ["a - b"])
def test_dash_param(v):
    assert v == "a - b"
PY
  commit_file "$C" tests/unit/test_zz_auditrace_plant_dash.py "ensaio: plant (id com « - »)"
  DASH_ID="tests/unit/test_zz_auditrace_plant_dash.py::test_dash_param[a - b]"
  printf '%s\n' "$DASH_ID" > "$WORK/logs/t11.fail"
  rc=0; AUDITRACE_SHIM_FAIL_FILE="$WORK/logs/t11.fail" run_dry "$C" "$WORK/logs/t11.log" || rc=$?
  [ "$rc" = "0" ] && ok "T11: rc 0" || ko "T11: rc $rc (esperado 0)"
  has "$WORK/logs/t11.log" "instável (passou isolada, com o patch, na tentativa 1 de 3): $DASH_ID" "T11: rerrodado pelo id inteiro (com « - »)"
  clean_tree "$C" "T11"

  step "T12 o HEAD muda durante a bateria: recusa antes do sentinel e desfaz"
  C="$(fresh headmove)"
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; AUDITRACE_SHIM_COMMIT=1 run_dry "$C" "$WORK/logs/t12.log" || rc=$?
  [ "$rc" = "1" ] && ok "T12: rc 1" || ko "T12: rc $rc (esperado 1)"
  has "$WORK/logs/t12.log" "o HEAD mudou durante a bateria" "T12: recusa nomeada"
  has "$WORK/logs/t12.log" "patch-revertido" "T12: o desfazer reverteu o patch"
  [ "$(git -C "$C" rev-parse HEAD~1)" = "$H0" ] && ok "T12: só o commit plantado a mais" || ko "T12: histórico inesperado"
  clean_tree "$C" "T12"

  step "T13 um caminho do patch muda durante a bateria: recusa; a receita impressa restaura"
  C="$(fresh touchpatched)"
  rc=0; AUDITRACE_SHIM_TOUCH="$DRIFT" run_dry "$C" "$WORK/logs/t13.log" || rc=$?
  [ "$rc" = "1" ] && ok "T13: rc 1" || ko "T13: rc $rc (esperado 1)"
  has "$WORK/logs/t13.log" "$DRIFT mudou durante a bateria" "T13: recusa nomeada pelo caminho"
  has "$WORK/logs/t13.log" "CAMINHOS-DO-PATCH-AINDA-SUJOS" "T13: o desfazer diz que um caminho do patch ficou sujo"
  has "$WORK/logs/t13.log" "restaure a pré-imagem com: git checkout HEAD --" "T13: a receita é impressa"
  awk '/^diff --git /{p=$3; sub(/^a\//, "", p); print p}' "$C/$PATCH" > "$WORK/logs/t13.touched"
  ( cd "$C" && xargs git checkout HEAD -- < "$WORK/logs/t13.touched" ) >"$WORK/logs/t13c.log" 2>&1 && ok "T13: a receita restaura" || ko "T13: a receita falhou"
  clean_tree "$C" "T13"

  step "T21 o sentinel vivo muda durante a bateria: recusa antes do passo 4; a receita restaura"
  C="$(fresh senttouch)"
  rc=0; AUDITRACE_SHIM_TOUCH="$SENT" run_dry "$C" "$WORK/logs/t21.log" || rc=$?
  [ "$rc" = "1" ] && ok "T21: rc 1" || ko "T21: rc $rc (esperado 1)"
  has "$WORK/logs/t21.log" "o sentinel mudou durante a bateria" "T21: recusa nomeada"
  has "$WORK/logs/t21.log" "restaure com: git checkout HEAD -- $SENT" "T21: a receita é impressa"
  has "$WORK/logs/t21.log" "patch-revertido" "T21: o desfazer reverteu o patch"
  grep -qF "===== 4/7" "$WORK/logs/t21.log" && ko "T21: chegou ao passo 4" || ok "T21: não chegou ao passo 4"
  ( cd "$C" && git checkout HEAD -- "$SENT" ) >"$WORK/logs/t21c.log" 2>&1 && ok "T21: a receita restaura" || ko "T21: a receita falhou"
  clean_tree "$C" "T21"

  step "T14 modo REAL: um arquivo rastreado FORA do patch sujo pela bateria — commit exato, aviso nomeado"
  C="$(fresh realdirty)"
  OUTSIDE=README.md
  git -C "$C" ls-files --error-unmatch -- "$OUTSIDE" >/dev/null 2>&1 || { ko "T14: $OUTSIDE não é rastreado"; }
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; AUDITRACE_SHIM_TOUCH="$OUTSIDE" run_real_tty "$C" "$WORK/logs/t14.log" || rc=$?
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
[ "$SYNTH_RAIL" = "1" ] && printf '  ATENÇÃO: registro de rail SINTÉTICO — refaça o ensaio com o rail-round-N.md real commitado\n'
[ "$FAIL" = "0" ]
