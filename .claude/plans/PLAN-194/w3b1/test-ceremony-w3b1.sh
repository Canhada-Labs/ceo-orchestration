#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: harness de ensaio do OWNER-W3B1-SIGN.sh (PLAN-194 W3b.1),
# clonado do test-ceremony-w1.sh (PLAN-194 W1). Muda em relação ao molde: caminhos e nomes; sem
# controle próprio (o controle é check-model-deprecations.py, do repositório) e sem actionlint;
# T17 (controle que não discrimina; gate duro vermelho com o patch; controle que quebra) com plantas
# no ledger e no script; T25 (modo REAL que falha DEPOIS da assinatura); T27 (hook pre-commit que
# stageia a mais); a deriva plantada (T5/T15) e as marcas do T26 ficam no topo do
# .claude/data/model-currency-expected-reds.txt, fora dos hunks do patch. Da W1 r3: a gramática do
# registro (T6-innerheading/badopen/unclosed/twofences/innerfence, mais T6-afterfence e o controle
# positivo T6-headingok) e o T26 (validate-governance pela saída inteira). Anexo da r3: T28 (hook que
# troca só a .asc ⇒ a árvore commitada não é a do índice conferido).
# test-ceremony-w3b1.sh — ensaia o SIGN da metade canônica da W3b.1 em CLONES descartáveis, com uma
# chave GPG descartável; nunca toca o repositório de origem, o chaveiro do Owner nem o $HOME real.
#
#   bash .claude/plans/PLAN-194/w3b1/test-ceremony-w3b1.sh [--work <dir>] [--src <repo>] [--full-suite]
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
#   - se a origem ainda NÃO tem registro de rail (w3b1/rail-round-*.md), um registro SINTÉTICO
#     rail-round-1.md entra no mesmo commit de ensaio, marcado como tal, com os sha256 do w3b1.patch
#     e do sentinel do HEAD, revisor GO e veredito APPROVE — o rail de verdade é do CEO; com
#     registros reais na origem, eles são usados (precisam ter os campos que o SIGN exige);
#   - HOME falso em <work>/home (PYTHONUSERBASE aponta para o do usuário, onde está o pytest), e o
#     SIGN roda sob `env -i` com esse ambiente mínimo e TMPDIR=<work>/tmp (os logs do SIGN e o
#     worktree da base ficam dentro da área do ensaio);
#   - SEM --full-suite: um `python3` de fachada no PATH responde SÓ às duas passadas inteiras do
#     pytest (paralela e serial) com uma saída sintética controlada pelo cenário; todo o resto
#     (controle da W3b, check-model-currency, testes do pacote, gates, reruns isolados, worktree da
#     base) roda de verdade. Com --full-suite as suítes rodam inteiras (~15 min por cenário).
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
D=.claude/plans/PLAN-194/w3b1
SIGN="$D/OWNER-W3B1-SIGN.sh"
SENT=.claude/plans/PLAN-194/w3b1-approved.md
PATCH="$D/w3b1.patch"
TARGET_PATH=.claude/hooks/_lib/codex_cli_shape.py
STAGED="$D/staged-w3b1/$TARGET_PATH"
LEDGER=.claude/scripts/model-deprecations.json
DRIFT=.claude/data/model-currency-expected-reds.txt
git -C "$SRC" cat-file -e "$SRC_HEAD:$SIGN" 2>/dev/null || { printf 'o HEAD de %s não tem %s commitado — commite os materiais antes do ensaio\n' "$SRC" "$SIGN" >&2; exit 2; }
if [ -n "$WORK" ]; then
  [ ! -e "$WORK" ] || { printf '%s já existe — use um diretório novo\n' "$WORK" >&2; exit 2; }
  mkdir -p "$WORK"
else
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/w3b1-rehearsal.XXXXXX")"
fi
WORK="$(cd "$WORK" && pwd -P)"
SOCKDIR="$(mktemp -d "${TMPDIR:-/tmp}/w3b1g.XXXXXX")"
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
  --quick-gen-key 'W3B1 Rehearsal Throwaway <w3b1-rehearsal@example.invalid>' ed25519 sign never >"$WORK/logs/keygen.log" 2>&1
FPR="$(GNUPGHOME="$GNUPGHOME" gpg --list-secret-keys --with-colons 2>/dev/null | awk -F: '$1 == "fpr" {print $10; exit}')"
[ -n "$FPR" ] || { tail -5 "$WORK/logs/keygen.log" >&2; printf 'não consegui gerar a chave descartável\n' >&2; exit 1; }
REALPY="$(command -v python3)"
PYUB="$(python3 -m site --user-base)"
cat > "$WORK/shim/python3" <<SHIM
#!/bin/bash
# fachada do ensaio: responde SÓ às duas passadas inteiras do pytest do SIGN; o resto é o python3 real
if [ "\${1:-}" = "-m" ] && [ "\${2:-}" = "pytest" ] && [ "\${3:-}" = "-n" ] && [ "\${4:-}" = "auto" ]; then
  [ -z "\${W3B1_SHIM_MARK:-}" ] || : > "\$W3B1_SHIM_MARK"
  [ -z "\${W3B1_SHIM_SLEEP:-}" ] || sleep "\$W3B1_SHIM_SLEEP"
  # efeitos colaterais de uma bateria longa: outro commit no meio, um arquivo rastreado escrito
  [ -z "\${W3B1_SHIM_COMMIT:-}" ] || git commit -q --allow-empty -m "ensaio: commit durante a bateria"
  [ -z "\${W3B1_SHIM_TOUCH:-}" ] || printf '\n# escrito pela bateria do ensaio\n' >> "\$W3B1_SHIM_TOUCH"
  if [ -n "\${W3B1_SHIM_FAIL_FILE:-}" ]; then
    while IFS= read -r t; do printf 'FAILED %s - injetada pelo ensaio\n' "\$t"; done < "\$W3B1_SHIM_FAIL_FILE"
    printf '1 failed, 10 passed in 0.01s\n'
    exit 1
  fi
  if [ -n "\${W3B1_SHIM_FAIL:-}" ]; then
    for t in \$W3B1_SHIM_FAIL; do printf 'FAILED %s - injetada pelo ensaio\n' "\$t"; done
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
git -C "$STAGE" config user.name "W3B1 Rehearsal"
git -C "$STAGE" config user.email "w3b1-rehearsal@example.invalid"
printf '# ENSAIO: chave descartável do test-ceremony-w3b1.sh\n%s\n' "$FPR" >> "$STAGE/.claude/sentinel-signers.txt"
git -C "$STAGE" add -- .claude/sentinel-signers.txt
RAIL_NOTE="registros reais da origem"
if ! ls "$STAGE/$D"/rail-round-*.md >/dev/null 2>&1; then
  PSHA0="$(shasum -a 256 "$STAGE/$PATCH" | awk '{print $1}')"
  SSHA0="$(git -C "$STAGE" show "HEAD:$SENT" | shasum -a 256 | awk '{print $1}')"
  cat > "$STAGE/$D/rail-round-1.md" <<REC
# rail-round-1 — REGISTRO SINTÉTICO DO ENSAIO (test-ceremony-w3b1.sh); não é revisão

Rail-Round: 1
Rail-Subject: $PATCH
Rail-Subject-sha256: $PSHA0
Rail-Sentinel-sha256: $SSHA0
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
  git -C "$c" config user.name "W3B1 Rehearsal"
  git -C "$c" config user.email "w3b1-rehearsal@example.invalid"
  printf '%s' "$c"
}
sign_env() {  # o ambiente mínimo do SIGN no ensaio
  printf '%s\n' "HOME=$WORK/home" "PATH=$SPATH" "TMPDIR=$WORK/tmp" "GNUPGHOME=$GNUPGHOME" \
    "PYTHONUSERBASE=$PYUB" "LANG=en_US.UTF-8" "LC_ALL=en_US.UTF-8" "TERM=${TERM:-xterm}" "USER=${USER:-rehearsal}" \
    "W3B1_SHIM_FAIL=${W3B1_SHIM_FAIL:-}" "W3B1_SHIM_SLEEP=${W3B1_SHIM_SLEEP:-}" "W3B1_SHIM_MARK=${W3B1_SHIM_MARK:-}" \
    "W3B1_SHIM_FAIL_FILE=${W3B1_SHIM_FAIL_FILE:-}" "W3B1_SHIM_COMMIT=${W3B1_SHIM_COMMIT:-}" "W3B1_SHIM_TOUCH=${W3B1_SHIM_TOUCH:-}"
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
base_edit() {  # clone programa-awk mensagem — edita o $DRIFT do HEAD do clone (a base) e commita
  awk "$2" "$1/$DRIFT" > "$1/$DRIFT.tmp" && mv "$1/$DRIFT.tmp" "$1/$DRIFT"
  commit_file "$1" "$DRIFT" "$3"
}
rederive() {  # clone programa-awk — reaplica o patch sobre o HEAD do clone, edita a pós-imagem do $DRIFT
  # com o awk, regenera o patch (os 7 caminhos, --full-index) e prende o registro sintético a ele
  local c="$1" prog="$2" rec
  ( cd "$c" && git apply "$PATCH" \
      && awk "$prog" "$DRIFT" > "$DRIFT.tmp" && mv "$DRIFT.tmp" "$DRIFT" \
      && git diff --full-index > "$PATCH.new" \
      && git checkout -q HEAD -- . \
      && mv "$PATCH.new" "$PATCH" ) >>"$WORK/logs/rederive.log" 2>&1 || return 1
  rec="$(set_rec_line "$c" "Rail-Subject-sha256: " "Rail-Subject-sha256: $(shasum -a 256 "$c/$PATCH" | awk '{print $1}')")"
  git -C "$c" add -- "$PATCH" "$rec"
  git -C "$c" commit -q -m "ensaio: patch re-derivado"
}
plant_drift() {  # clone — uma linha a mais no TOPO do $DRIFT: fora dos hunks do patch (o hunk dele é no fim)
  { printf '# deriva plantada pelo ensaio\n'; cat "$1/$DRIFT"; } > "$1/$DRIFT.ensaio"
  mv "$1/$DRIFT.ensaio" "$1/$DRIFT"
}
edit_ledger() {  # clone modo — reescreve o ledger (fora do patch): openai-out tira as linhas OpenAI; gpt55-row põe uma linha para o gpt-5.5
  python3 - "$1/$LEDGER" "$2" <<'PY'
import json
import sys

path, mode = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
if mode == "openai-out":
    data["models"] = [m for m in data["models"] if m["model_id"].startswith("claude-")]
elif mode == "gpt55-row":
    data["models"].append({"model_id": "gpt-5.5", "aliases": [], "deprecated": "2026-10-01",
                           "retirement": "2026-10-20", "replacement": "gpt-5.6-sol",
                           "note": "ENSAIO (test-ceremony-w3b1.sh): linha plantada, não é fonte"})
else:
    raise SystemExit("modo desconhecido: %s" % mode)
with open(path, "w", encoding="utf-8") as fh:
    fh.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
PY
}
post_blob() {  # clone caminho → blob pós-imagem que o patch declara para o caminho
  awk -v t="$2" '/^diff --git /{p=$3; sub(/^a\//, "", p)} /^index /{split($2, h, /\.\./); if (p == t) print h[2]}' "$1/$PATCH"
}
FLAKY=".claude/hooks/tests/test_codex_cli_shape.py::TestCoercion::test_model_none_omits"
NEWFAIL_ID="tests/unit/test_zz_w3b1_plant_new.py::test_old_tuple_accepts_o3"
plant_newfail() {  # clone — um teste que passa SEM o patch (a tupla antiga aceitava o3) e falha com ele, commitado
  mkdir -p "$1/tests/unit"
  cat > "$1/tests/unit/test_zz_w3b1_plant_new.py" <<'PY'
"""Ensaio W3b.1: passa na árvore SEM o patch (a tupla antiga aceitava o3)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / ".claude" / "hooks"))
from _lib import codex_cli_shape as shape  # noqa: E402


def test_old_tuple_accepts_o3():
    assert "o3" in shape._VALID_MODELS
PY
  commit_file "$1" tests/unit/test_zz_w3b1_plant_new.py "ensaio: plant (falha nova)"
}

step "T0 ceremony-lint e bits de execução no índice"
C="$(fresh lint)"
if (cd "$C" && python3 .claude/scripts/check-ceremony-script.py) >"$WORK/logs/t0.log" 2>&1; then ok "T0: ceremony-lint 0 BLOCKING"; else ko "T0: ceremony-lint reprovou"; tail -12 "$WORK/logs/t0.log" | sed 's/^/        | /'; fi
for f in "$SIGN" "$D/test-ceremony-w3b1.sh"; do
  m="$(git -C "$C" ls-files -s -- "$f" | awk '{print $1}')"
  [ "$m" = "100644" ] && ok "T0: $f modo $m no índice" || ko "T0: $f modo '$m' no índice (esperado 100644)"
  # classe bash 3.2: numa locale UTF-8 o byte seguinte a `$nome` conta como parte do nome
  if LC_ALL=C grep -nE '\$[A-Za-z_][A-Za-z0-9_]*[^ -~]' "$C/$f" >"$WORK/logs/t0-adj.log" 2>&1; then
    ko "T0: $f tem variável colada a caractere não-ASCII (use \${nome}):"; sed 's/^/        | /' "$WORK/logs/t0-adj.log"
  else
    ok "T0: $f sem variável colada a caractere não-ASCII"
  fi
done
SB="$(git -C "$C" hash-object -- "$STAGED")"
PB="$(post_blob "$C" "$TARGET_PATH")"
[ -n "$PB" ] && [ "$SB" = "$PB" ] && ok "T0: cópia staged = pós-imagem do patch ($SB)" || ko "T0: cópia staged $SB ≠ pós-imagem $PB"

step "T1 --dry-run no caminho feliz"
C="$(fresh dry)"
H0="$(git -C "$C" rev-parse HEAD)"
rc=0; run_dry "$C" "$WORK/logs/t1.log" || rc=$?
[ "$rc" = "0" ] && ok "T1: rc 0" || ko "T1: rc $rc"
has "$WORK/logs/t1.log" "Ensaio OK" "T1: ensaio concluído"
has "$WORK/logs/t1.log" "controle da W3b reprova no HEAD (como deve)" "T1: o P0 viu o controle vermelho no HEAD"
has "$WORK/logs/t1.log" "ok: controle da W3b (vermelho no HEAD, verde com o patch)" "T1: controle verde com o patch"
has "$WORK/logs/t1.log" "ok: check-model-currency --expected-reds (RED-IDS: 6)" "T1: conjunto de vermelhos esperado confere"
has "$WORK/logs/t1.log" "ok: testes do pacote" "T1: testes do pacote (passada dura) verdes"
has "$WORK/logs/t1.log" "blob(s) conferido(s) contra o index pós-imagem" "T1: pós-imagem conferida"
has "$WORK/logs/t1.log" "ok: validate-governance (Errors: 0)" "T1: validate-governance passou"
has "$WORK/logs/t1.log" "sentinel $(git -C "$C" show "HEAD:$SENT" | shasum -a 256 | awk '{print $1}')" "T1: o P0 prendeu o rail ao sentinel do HEAD"
has "$WORK/logs/t1.log" "blob(s) e modo(s) no índice conferido(s)" "T1: estado e modo do stage conferidos"
[ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T1: HEAD inalterado" || ko "T1: HEAD mudou"
clean_tree "$C" "T1"

step "T2 modo REAL sob pseudo-TTY, chave descartável, uma falha instável injetada"
C="$(fresh real)"
H0="$(git -C "$C" rev-parse HEAD)"
rc=0; W3B1_SHIM_FAIL="$FLAKY" run_real_tty "$C" "$WORK/logs/t2.log" || rc=$?
[ "$rc" = "0" ] && ok "T2: rc 0" || ko "T2: rc $rc"
has "$WORK/logs/t2.log" "LANDADO em" "T2: landou"
if [ "$FULL" = "0" ]; then has "$WORK/logs/t2.log" "instável (passou isolada, com o patch" "T2: a falha injetada foi julgada instável pelo rerun isolado"; fi
[ "$(git -C "$C" rev-parse HEAD~1)" = "$H0" ] && ok "T2: exatamente um commit novo sobre o HEAD" || ko "T2: HEAD~1 != HEAD anterior"
git -C "$C" show --name-only --format= HEAD | sort > "$WORK/logs/t2.committed"
{ awk '/^diff --git /{p=$3; sub(/^a\//, "", p); print p}' "$C/$PATCH"; printf '%s\n%s\n' "$SENT" "$SENT.asc"; } | sort -u > "$WORK/logs/t2.expected"
cmp -s "$WORK/logs/t2.committed" "$WORK/logs/t2.expected" && ok "T2: o commit tem exatamente os 7 caminhos + sentinel + .asc" || ko "T2: conjunto commitado inesperado: $(comm -3 "$WORK/logs/t2.committed" "$WORK/logs/t2.expected" | tr '\n' ' ')"
if GNUPGHOME="$GNUPGHOME" gpg --verify "$C/$SENT.asc" "$C/$SENT" >"$WORK/logs/t2.verify" 2>&1; then ok "T2: a assinatura verifica"; else ko "T2: a assinatura não verifica"; fi
grep -qF "$FPR" "$WORK/logs/t2.verify" && ok "T2: assinada pela chave descartável" || ko "T2: signatário inesperado"
awk '/^diff --git /{p=$3; sub(/^a\//, "", p)} /^index /{split($2, h, /\.\./); print p, h[2]}' "$C/$PATCH" > "$WORK/logs/t2.blobs"
bad=0
while read -r p new; do
  [ "$(git -C "$C" rev-parse "HEAD:$p")" = "$new" ] || { bad=1; ko "T2: $p landou com blob diferente do revisado"; }
  [ "$(git -C "$C" ls-tree HEAD -- "$p" | awk '{print $1}')" = "$(git -C "$C" ls-tree HEAD~1 -- "$p" | awk '{print $1}')" ] || { bad=1; ko "T2: $p mudou de modo"; }
done < "$WORK/logs/t2.blobs"
[ "$bad" = "0" ] && ok "T2: os 7 blobs landados são os do index pós-imagem do patch, sem mudança de modo"
[ "$(git -C "$C" rev-parse "HEAD:$TARGET_PATH")" = "$(git -C "$C" hash-object -- "$STAGED")" ] && ok "T2: o canônico landado é byte a byte a cópia staged" || ko "T2: o canônico landado difere da cópia staged"
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
grep -qF "argv padrão do rail não muda" "$WORK/logs/t2.msg" && ok "T2: a mensagem declara que o argv padrão não muda" || ko "T2: a mensagem não declara o argv padrão"
[ -z "$(git -C "$C" status --porcelain --untracked-files=no)" ] && ok "T2: árvore limpa depois do land" || ko "T2: árvore suja depois do land"
[ "$(git -C "$C" worktree list | wc -l | tr -d ' ')" = "1" ] && ok "T2: nenhum worktree da base sobrou" || ko "T2: worktree sobrou"
if (cd "$C" && env HOME="$WORK/home" python3 .claude/scripts/check-model-deprecations.py --check --today 2026-10-13) >"$WORK/logs/t2.dep" 2>&1; then
  ok "T2: check-model-deprecations --check --today 2026-10-13 rc 0 na árvore landada"
else
  ko "T2: check-model-deprecations não saiu 0 na árvore landada"
fi
if (cd "$C" && env HOME="$WORK/home" python3 .claude/scripts/check-model-currency.py --expected-reds "$DRIFT") >"$WORK/logs/t2.cur" 2>&1; then
  ok "T2: check-model-currency --expected-reds rc 0 na árvore landada"
else
  ko "T2: check-model-currency --expected-reds não saiu 0 na árvore landada"
fi

if [ "$FULL" = "0" ]; then
  step "T3 falha NOVA (passa sem o patch, falha com ele) aborta e restaura"
  C="$(fresh newfail)"
  plant_newfail "$C"
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; W3B1_SHIM_FAIL="$NEWFAIL_ID" run_dry "$C" "$WORK/logs/t3.log" || rc=$?
  [ "$rc" = "1" ] && ok "T3: rc 1" || ko "T3: rc $rc (esperado 1)"
  has "$WORK/logs/t3.log" "falhas NOVAS" "T3: a falha nova foi nomeada"
  has "$WORK/logs/t3.log" "patch-revertido" "T3: o desfazer reverteu o patch"
  [ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T3: HEAD inalterado" || ko "T3: HEAD mudou"
  clean_tree "$C" "T3"

  step "T4 falha PRÉ-EXISTENTE (falha com e sem o patch) é nota, não bloqueio"
  C="$(fresh prefail)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_w3b1_plant_pre.py" <<'PY'
"""Ensaio W3b.1: falha nas duas árvores (vermelho pré-existente)."""
from __future__ import annotations


def test_always_red():
    raise AssertionError("vermelho pré-existente plantado pelo ensaio")
PY
  commit_file "$C" tests/unit/test_zz_w3b1_plant_pre.py "ensaio: plant (pré-existente)"
  rc=0; W3B1_SHIM_FAIL="tests/unit/test_zz_w3b1_plant_pre.py::test_always_red" run_dry "$C" "$WORK/logs/t4.log" || rc=$?
  [ "$rc" = "0" ] && ok "T4: rc 0" || ko "T4: rc $rc (esperado 0)"
  has "$WORK/logs/t4.log" "PRÉ-EXISTENTE (falha também sem o patch)" "T4: nomeada como pré-existente"
  has "$WORK/logs/t4.log" "ATENÇÃO — vermelhos PRÉ-EXISTENTES" "T4: resumo final avisa"
  clean_tree "$C" "T4"
fi

step "T5 base derivada (um caminho do patch mudou fora dos hunks) recusa no P0"
C="$(fresh drift)"
plant_drift "$C"
commit_file "$C" "$DRIFT" "ensaio: deriva da base"
rc=0; run_dry "$C" "$WORK/logs/t5.log" || rc=$?
[ "$rc" = "1" ] && ok "T5: rc 1" || ko "T5: rc $rc (esperado 1)"
has "$WORK/logs/t5.log" "a base de $DRIFT mudou" "T5: a deriva é nomeada pelo caminho"
has "$WORK/logs/t5.log" "nada a desfazer" "T5: nada foi aplicado"
clean_tree "$C" "T5"

step "T6 registro de rail que não prende os dois sujeitos, ou com veredito incoerente, recusa no P0"
Z64="$(printf '%064d' 0)"
for v in subject sentinel verdict reviewer lastline innerheading badopen unclosed twofences innerfence afterfence indentinner indentafter; do
  C="$(fresh "rail-$v")"
  case "$v" in
    subject)  REC="$(set_rec_line "$C" "Rail-Subject-sha256: " "Rail-Subject-sha256: $Z64")"; want="revisou outro patch" ;;
    sentinel) REC="$(set_rec_line "$C" "Rail-Sentinel-sha256: " "Rail-Sentinel-sha256: $Z64")"; want="revisou outro texto assinável" ;;
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
    innerfence)  # uma linha de cerca mal formada DENTRO do bloco verbatim
      REC="$(rec_awk "$C" '{ print } !done && $0 == "```text" { print "```python"; done = 1 }')"; want="linha de cerca mal formada DENTRO do bloco verbatim" ;;
    afterfence)  # o bloco verbatim termina em NO-GO e uma linha «VERDICT: GO» vem DEPOIS da cerca: não vale
      REC="$(rec_awk "$C" '$0 == "```text" { inb = 1; print; next }
        inb && /^VERDICT: / { print "VERDICT: NO-GO"; next }
        inb && $0 == "```" { print; print "VERDICT: GO"; inb = 0; next }
        { print }')"; want="≠ a última linha VERDICT do revisor" ;;
    indentinner)  # uma cerca INDENTADA dentro do bloco verbatim (indentar não é rota)
      REC="$(rec_awk "$C" '{ print } !done && $0 == "```text" { print "    ```"; done = 1 }')"; want="linha de cerca mal formada DENTRO do bloco verbatim" ;;
    indentafter)  # uma cerca INDENTADA na seção, depois do bloco
      REC="$(rec_awk "$C" '$0 == "```text" { inb = 1 } { print } inb && $0 == "```" && !done { print "  ```text"; inb = 0; done = 1 }')"; want="segunda cerca na seção" ;;
  esac
  commit_file "$C" "$REC" "ensaio: registro de rail adulterado ($v)"
  rc=0; run_dry "$C" "$WORK/logs/t6-$v.log" || rc=$?
  [ "$rc" = "1" ] && ok "T6-$v: rc 1" || ko "T6-$v: rc $rc (esperado 1)"
  has "$WORK/logs/t6-$v.log" "$want" "T6-$v: recusa nomeada"
  clean_tree "$C" "T6-$v"
done
# controle POSITIVO da gramática: um título «## …» dentro do bloco verbatim e a última VERDICT = GO ⇒ aceito
C="$(fresh rail-headingok)"
REC="$(rec_awk "$C" '!done && $0 == "```text" { print; print "## Achados"; print "NENHUM ACHADO"; inb = 1; next }
  inb { if ($0 == "```") { print "VERDICT: GO"; print; inb = 0; done = 1 } next }
  { print }')"
commit_file "$C" "$REC" "ensaio: título dentro da saída verbatim, VERDICT final GO"
rc=0; run_dry "$C" "$WORK/logs/t6-headingok.log" || rc=$?
[ "$rc" = "0" ] && ok "T6-headingok: rc 0 (o título dentro do bloco não encerra a seção)" || ko "T6-headingok: rc $rc (esperado 0)"
has "$WORK/logs/t6-headingok.log" "Ensaio OK" "T6-headingok: ensaio concluído"
clean_tree "$C" "T6-headingok"
# o texto assinável muda DEPOIS da rodada (o registro segue o mesmo): recusa no P0
C="$(fresh rail-senttext)"
printf '\nFrase acrescentada depois da rodada do rail (ensaio).\n' >> "$C/$SENT"
commit_file "$C" "$SENT" "ensaio: sentinel editado depois do rail"
rc=0; run_dry "$C" "$WORK/logs/t6-senttext.log" || rc=$?
[ "$rc" = "1" ] && ok "T6-senttext: rc 1" || ko "T6-senttext: rc $rc (esperado 1)"
has "$WORK/logs/t6-senttext.log" "revisou outro texto assinável" "T6-senttext: o texto editado depois do rail é recusado"
has "$WORK/logs/t6-senttext.log" "nada a desfazer" "T6-senttext: nada foi aplicado"
clean_tree "$C" "T6-senttext"

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
  ( cd "$C" && W3B1_SHIM_SLEEP=15 W3B1_SHIM_MARK="$MARK" sign_env > "$WORK/logs/env-t8" \
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
  ( cd "$C" && W3B1_SHIM_SLEEP=5 W3B1_SHIM_MARK="$MARK" sign_env > "$WORK/logs/env-t9" \
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
  STALE="$(mktemp -d "$WORK/tmp/w3b1-sign.XXXXXX")/base-wt"
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
has "$WORK/logs/t15a.log" "OK: a base pinada da W3b.1" "T15: OK nomeado"
plant_drift "$C"
commit_file "$C" "$DRIFT" "ensaio: deriva da base (check-base)"
rc=0; cb "$C" "$WORK/logs/t15b.log" HEAD || rc=$?
[ "$rc" = "1" ] && ok "T15: base derivada, rc 1" || ko "T15: base derivada, rc $rc (esperado 1)"
has "$WORK/logs/t15b.log" "DIFERE: $DRIFT" "T15: o caminho derivado é nomeado"
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

step "T17 controle que não discrimina recusa no P0; gate duro vermelho com o patch recusa na bateria"
C="$(fresh ctrlgreen)"
edit_ledger "$C" openai-out
commit_file "$C" "$LEDGER" "ensaio: ledger sem as linhas OpenAI (o controle fica verde no HEAD)"
rc=0; run_dry "$C" "$WORK/logs/t17a.log" || rc=$?
[ "$rc" = "1" ] && ok "T17a: rc 1" || ko "T17a: rc $rc (esperado 1)"
has "$WORK/logs/t17a.log" "não reprova no HEAD" "T17a: recusa nomeada"
has "$WORK/logs/t17a.log" "nada a desfazer" "T17a: nada foi aplicado"
clean_tree "$C" "T17a"
C="$(fresh hardgate)"
edit_ledger "$C" gpt55-row
commit_file "$C" "$LEDGER" "ensaio: linha do gpt-5.5 no ledger (o gate duro fica vermelho com o patch)"
rc=0; run_dry "$C" "$WORK/logs/t17b.log" || rc=$?
[ "$rc" = "1" ] && ok "T17b: rc 1" || ko "T17b: rc $rc (esperado 1)"
has "$WORK/logs/t17b.log" "check-model-deprecations --check --today 2026-10-13 não saiu 0 com o patch" "T17b: recusa nomeada"
has "$WORK/logs/t17b.log" "patch-revertido" "T17b: o desfazer reverteu o patch"
clean_tree "$C" "T17b"
C="$(fresh ctrlcrash)"
# rc 1 por EXCEÇÃO (sem a linha SUMMARY): não prova que o controle discrimina
printf '#!/usr/bin/env python3\n"""ensaio: controle que quebra"""\nraise KeyError("ensaio")\n' > "$C/.claude/scripts/check-model-deprecations.py"
commit_file "$C" .claude/scripts/check-model-deprecations.py "ensaio: controle que quebra com exceção"
rc=0; run_dry "$C" "$WORK/logs/t17c.log" || rc=$?
[ "$rc" = "1" ] && ok "T17c: rc 1" || ko "T17c: rc $rc (esperado 1)"
has "$WORK/logs/t17c.log" "não reprova no HEAD (rc=1, acertos BREAK+WARN no 'SUMMARY: breaks=': x" "T17c: rc 1 de exceção não conta como vermelho do controle"
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

step "T24 sentinel que cita o marcador de preenchimento fora das 4 linhas de campo recusa no P0"
C="$(fresh tofillprose)"
printf '\nNota do ensaio: o marcador TO-FILL-BY-SIGN citado em prosa.\n' >> "$C/$SENT"
commit_file "$C" "$SENT" "ensaio: marcador citado em prosa no sentinel"
rc=0; run_dry "$C" "$WORK/logs/t24.log" || rc=$?
[ "$rc" = "1" ] && ok "T24: rc 1" || ko "T24: rc $rc (esperado 1)"
has "$WORK/logs/t24.log" "cita TO-FILL-BY-SIGN fora das 4 linhas de campo" "T24: recusa nomeada, antes da bateria"
has "$WORK/logs/t24.log" "nada a desfazer" "T24: nada foi aplicado"
clean_tree "$C" "T24"

step "T25 modo REAL: falha DEPOIS da assinatura (o commit recusa) — sentinel restaurado, .asc removida, patch revertido"
C="$(fresh realfail)"
H0="$(git -C "$C" rev-parse HEAD)"
printf '#!/bin/sh\necho "ensaio: pre-commit recusa o commit" >&2\nexit 1\n' > "$C/.git/hooks/pre-commit"
chmod 755 "$C/.git/hooks/pre-commit"
rc=0; run_real_tty "$C" "$WORK/logs/t25.log" || rc=$?
[ "$rc" != "0" ] && ok "T25: rc $rc (≠ 0)" || ko "T25: rc 0 (esperado ≠ 0)"
has "$WORK/logs/t25.log" "assinado por $FPR" "T25: a falha veio DEPOIS da assinatura"
has "$WORK/logs/t25.log" "ensaio: pre-commit recusa o commit" "T25: quem falhou foi o commit"
has "$WORK/logs/t25.log" "patch-revertido" "T25: o desfazer reverteu o patch"
has "$WORK/logs/t25.log" "sentinel-restaurado" "T25: o desfazer restaurou o sentinel"
has "$WORK/logs/t25.log" "asc-removida" "T25: o desfazer removeu a .asc"
[ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T25: HEAD inalterado" || ko "T25: HEAD mudou"
grep -q "TO-FILL-BY-SIGN" "$C/$SENT" && ok "T25: o sentinel vivo voltou a ter os campos por preencher" || ko "T25: o sentinel vivo ficou preenchido"
clean_tree "$C" "T25"
rm -f "$C/.git/hooks/pre-commit"

step "T27 modo REAL: um hook pre-commit que stageia um arquivo a mais — o commit é desfeito (reset --soft) e o abort desfaz"
C="$(fresh hookstage)"
H0="$(git -C "$C" rev-parse HEAD)"
printf '#!/bin/sh\nprintf "\\n# acrescentado pelo hook do ensaio\\n" >> README.md\ngit add README.md\n' > "$C/.git/hooks/pre-commit"
chmod 755 "$C/.git/hooks/pre-commit"
rc=0; run_real_tty "$C" "$WORK/logs/t27.log" || rc=$?
[ "$rc" = "1" ] && ok "T27: rc 1" || ko "T27: rc $rc (esperado 1)"
has "$WORK/logs/t27.log" "o commit não é o índice conferido" "T27: recusa nomeada depois do commit"
has "$WORK/logs/t27.log" "README.md" "T27: o caminho a mais é nomeado"
has "$WORK/logs/t27.log" "sentinel-restaurado" "T27: o desfazer restaurou o sentinel"
has "$WORK/logs/t27.log" "asc-removida" "T27: o desfazer removeu a .asc"
has "$WORK/logs/t27.log" "patch-revertido" "T27: o desfazer reverteu o patch"
[ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T27: o commit foi desfeito (HEAD = o de antes)" || ko "T27: HEAD mudou"
has "$WORK/logs/t27.log" "para restaurar: git checkout HEAD -- README.md" "T27: o abort lista o arquivo que o hook sujou"
rm -f "$C/.git/hooks/pre-commit"
( cd "$C" && git checkout HEAD -- README.md ) >"$WORK/logs/t27c.log" 2>&1 && ok "T27: a receita restaura" || ko "T27: a receita falhou"
clean_tree "$C" "T27"

step "T28 modo REAL: um hook pre-commit que troca SÓ a .asc — a árvore commitada não é a do índice conferido; desfeito"
C="$(fresh hookasc)"
H0="$(git -C "$C" rev-parse HEAD)"
printf '#!/bin/sh\nprintf "# alterada pelo hook do ensaio\\n" >> %s.asc\ngit add %s.asc\n' "$SENT" "$SENT" > "$C/.git/hooks/pre-commit"
chmod 755 "$C/.git/hooks/pre-commit"
rc=0; run_real_tty "$C" "$WORK/logs/t28.log" || rc=$?
[ "$rc" = "1" ] && ok "T28: rc 1" || ko "T28: rc $rc (esperado 1)"
has "$WORK/logs/t28.log" "o commit não é o índice conferido" "T28: recusa nomeada depois do commit"
has "$WORK/logs/t28.log" "$SENT.asc" "T28: a .asc trocada é nomeada"
has "$WORK/logs/t28.log" "sentinel-restaurado" "T28: o desfazer restaurou o sentinel"
has "$WORK/logs/t28.log" "asc-removida" "T28: o desfazer removeu a .asc"
has "$WORK/logs/t28.log" "patch-revertido" "T28: o desfazer reverteu o patch"
[ "$(git -C "$C" rev-parse HEAD)" = "$H0" ] && ok "T28: o commit foi desfeito (HEAD = o de antes)" || ko "T28: HEAD mudou"
rm -f "$C/.git/hooks/pre-commit"
clean_tree "$C" "T28"

if [ "$FULL" = "0" ]; then
  step "T26 validate-governance: violação nova DENTRO do mesmo grupo (mesma contagem de erros) reprova"
  C="$(fresh govsamegroup)"
  # um grupo de violação plantado no validate-governance do clone: UM erro, uma linha de detalhe por marca
  awk '{ if ($0 == "echo \"  Errors:   $ERRORS\"") {
      print "if grep -q \"ENSAIO-GOV-MARCA\" .claude/data/model-currency-expected-reds.txt; then"
      print "  echo \"  FAIL: ensaio: marcas no model-currency-expected-reds.txt:\""
      print "  grep \"ENSAIO-GOV-MARCA\" .claude/data/model-currency-expected-reds.txt | sed \"s|^|    |\""
      print "  ERRORS=$((ERRORS + 1))"
      print "fi" }
    print }' "$C/.claude/scripts/validate-governance.sh" > "$C/vg.tmp" && mv "$C/vg.tmp" "$C/.claude/scripts/validate-governance.sh"
  commit_file "$C" .claude/scripts/validate-governance.sh "ensaio: grupo de violação plantado no validate-governance"
  # o detalhe traz «status: WARN»: a exclusão de avisos é pelo PREFIXO do produtor, não por substring
  base_edit "$C" 'NR == 1 { print "# ENSAIO-GOV-MARCA a status: WARN" } { print }' "ensaio: violação pré-existente (marca a)"
  rederive "$C" 'NR == 1 { print "# ENSAIO-GOV-MARCA b status: WARN" } { print }' || ko "T26: a montagem do patch falhou"
  rc=0; run_dry "$C" "$WORK/logs/t26.log" || rc=$?
  [ "$rc" = "1" ] && ok "T26: rc 1" || ko "T26: rc $rc (esperado 1)"
  has "$WORK/logs/t26.log" "NOVO:  # ENSAIO-GOV-MARCA b status: WARN" "T26: o detalhe novo do mesmo grupo (com «status: WARN») é listado"
  has "$WORK/logs/t26.log" "validate-governance (Errors: 0): achado(s) que só existe(m) com o patch" "T26: o governance reprova pelo detalhe"
  has "$WORK/logs/t26.log" "patch-revertido" "T26: o desfazer reverteu o patch"
  clean_tree "$C" "T26"

  step "T22 o sentinel muda durante a bateria: recusa antes de assinar; o abort nomeia e dá a receita"
  C="$(fresh senttouch)"
  rc=0; W3B1_SHIM_TOUCH="$SENT" run_dry "$C" "$WORK/logs/t22.log" || rc=$?
  [ "$rc" = "1" ] && ok "T22: rc 1" || ko "T22: rc $rc (esperado 1)"
  has "$WORK/logs/t22.log" "o sentinel mudou durante a bateria" "T22: recusa nomeada"
  has "$WORK/logs/t22.log" "patch-revertido" "T22: o desfazer reverteu o patch"
  has "$WORK/logs/t22.log" "para restaurar: git checkout HEAD -- $SENT" "T22: o abort lista o sentinel com a receita"
  ( cd "$C" && git checkout HEAD -- "$SENT" ) >"$WORK/logs/t22c.log" 2>&1 && ok "T22: a receita restaura" || ko "T22: a receita falhou"
  clean_tree "$C" "T22"

  step "T23 abort no meio da bateria com arquivo de FORA sujo: o abort o lista com a receita"
  C="$(fresh abortdirty)"
  plant_newfail "$C"
  rc=0; W3B1_SHIM_TOUCH=README.md W3B1_SHIM_FAIL="$NEWFAIL_ID" run_dry "$C" "$WORK/logs/t23.log" || rc=$?
  [ "$rc" = "1" ] && ok "T23: rc 1" || ko "T23: rc $rc (esperado 1)"
  has "$WORK/logs/t23.log" "falhas NOVAS" "T23: a falha nova abortou"
  has "$WORK/logs/t23.log" "o desfazer NÃO restaurou" "T23: o abort avisa do que sobrou"
  has "$WORK/logs/t23.log" "para restaurar: git checkout HEAD -- README.md" "T23: o abort lista o README.md com a receita"
  ( cd "$C" && git checkout HEAD -- README.md ) >"$WORK/logs/t23c.log" 2>&1 && ok "T23: a receita restaura" || ko "T23: a receita falhou"
  clean_tree "$C" "T23"

  step "T11 id parametrizado com « - » no parâmetro é rerrodado pelo id inteiro"
  C="$(fresh dashid)"
  mkdir -p "$C/tests/unit"
  cat > "$C/tests/unit/test_zz_w3b1_plant_dash.py" <<'PY'
"""Ensaio W3b.1: um id parametrizado cujo parâmetro contém « - » (passa nas duas árvores)."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("v", ["a - b"])
def test_dash_param(v):
    assert v == "a - b"
PY
  commit_file "$C" tests/unit/test_zz_w3b1_plant_dash.py "ensaio: plant (id com « - »)"
  DASH_ID="tests/unit/test_zz_w3b1_plant_dash.py::test_dash_param[a - b]"
  printf '%s\n' "$DASH_ID" > "$WORK/logs/t11.fail"
  rc=0; W3B1_SHIM_FAIL_FILE="$WORK/logs/t11.fail" run_dry "$C" "$WORK/logs/t11.log" || rc=$?
  [ "$rc" = "0" ] && ok "T11: rc 0" || ko "T11: rc $rc (esperado 0)"
  has "$WORK/logs/t11.log" "instável (passou isolada, com o patch, na tentativa 1 de 3): $DASH_ID" "T11: rerrodado pelo id inteiro (com « - »)"
  clean_tree "$C" "T11"

  step "T12 o HEAD muda durante a bateria: recusa antes do sentinel e desfaz"
  C="$(fresh headmove)"
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; W3B1_SHIM_COMMIT=1 run_dry "$C" "$WORK/logs/t12.log" || rc=$?
  [ "$rc" = "1" ] && ok "T12: rc 1" || ko "T12: rc $rc (esperado 1)"
  has "$WORK/logs/t12.log" "o HEAD mudou durante a bateria" "T12: recusa nomeada"
  has "$WORK/logs/t12.log" "patch-revertido" "T12: o desfazer reverteu o patch"
  [ "$(git -C "$C" rev-parse HEAD~1)" = "$H0" ] && ok "T12: só o commit plantado a mais" || ko "T12: histórico inesperado"
  clean_tree "$C" "T12"

  step "T13 um caminho do patch muda durante a bateria: recusa; o desfazer nomeia o caminho sujo; a receita impressa restaura"
  C="$(fresh touchpatched)"
  rc=0; W3B1_SHIM_TOUCH="$TARGET_PATH" run_dry "$C" "$WORK/logs/t13.log" || rc=$?
  [ "$rc" = "1" ] && ok "T13: rc 1" || ko "T13: rc $rc (esperado 1)"
  has "$WORK/logs/t13.log" "$TARGET_PATH mudou durante a bateria" "T13: recusa nomeada pelo caminho"
  has "$WORK/logs/t13.log" "CAMINHOS-DO-PATCH-AINDA-SUJOS" "T13: o desfazer diz que um caminho do patch ficou sujo"
  has "$WORK/logs/t13.log" "restaure a pré-imagem com: git checkout HEAD --" "T13: a receita é impressa"
  awk '/^diff --git /{p=$3; sub(/^a\//, "", p); print p}' "$C/$PATCH" > "$WORK/logs/t13.touched"
  ( cd "$C" && xargs git checkout HEAD -- < "$WORK/logs/t13.touched" ) >"$WORK/logs/t13c.log" 2>&1 && ok "T13: a receita restaura" || ko "T13: a receita falhou"
  clean_tree "$C" "T13"

  step "T13b a mudança cai no contexto de um hunk: o patch NÃO é revertido, o desfazer diz isso e a receita restaura"
  C="$(fresh touchhunk)"
  rc=0; W3B1_SHIM_TOUCH="$DRIFT" run_dry "$C" "$WORK/logs/t13b.log" || rc=$?
  [ "$rc" = "1" ] && ok "T13b: rc 1" || ko "T13b: rc $rc (esperado 1)"
  has "$WORK/logs/t13b.log" "$DRIFT mudou durante a bateria" "T13b: recusa nomeada pelo caminho"
  has "$WORK/logs/t13b.log" "PATCH-NAO-REVERTIDO" "T13b: o desfazer diz que o patch não foi revertido"
  has "$WORK/logs/t13b.log" "CAMINHOS-DO-PATCH-AINDA-SUJOS" "T13b: o desfazer diz que caminhos do patch ficaram sujos"
  awk '/^diff --git /{p=$3; sub(/^a\//, "", p); print p}' "$C/$PATCH" > "$WORK/logs/t13b.touched"
  ( cd "$C" && xargs git checkout HEAD -- < "$WORK/logs/t13b.touched" ) >"$WORK/logs/t13bc.log" 2>&1 && ok "T13b: a receita restaura" || ko "T13b: a receita falhou"
  clean_tree "$C" "T13b"

  step "T14 modo REAL: um arquivo rastreado FORA do patch sujo pela bateria — commit exato, aviso nomeado"
  C="$(fresh realdirty)"
  OUTSIDE=README.md
  git -C "$C" ls-files --error-unmatch -- "$OUTSIDE" >/dev/null 2>&1 || { ko "T14: $OUTSIDE não é rastreado"; }
  H0="$(git -C "$C" rev-parse HEAD)"
  rc=0; W3B1_SHIM_TOUCH="$OUTSIDE" run_real_tty "$C" "$WORK/logs/t14.log" || rc=$?
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
