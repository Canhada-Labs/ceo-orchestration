#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (PLAN-194, cura da corrida no gravador do
# agent_spawn — risco 11, unidade 4 de «Unidades que ganharam dono»), clonada do molde
# OWNER-FN04-SIGN.sh (PLAN-193 W4b, landado em a12a32ae — o land canônico mais recente, também de
# código que entra pelo SIGN). O que muda em relação ao molde, declarado:
#  (1) o bloco de constantes: o pacote, o patch, o sentinel e UM caminho canônico
#      (.claude/hooks/audit_log.py); os outros dois caminhos do patch são testes livres;
#  (2) a bateria roda primeiro os dois arquivos de teste da cura (o arquivo inteiro, inclusive as classes
#      marcadas serial da janela e da corrida entre processos) e depois as suítes do pytest.ini com a divisão de
#      marcadores do CI;
#  (3) o passo 2 confere o bit de execução do hook (.claude/hooks/audit_log.py) depois do apply;
#  (4) KERNEL: audit_log.py está em _KERNEL_PATHS (check_arbitration_kernel.py:217). Do molde de
#      kernel (W3-K, PLAN-169; 179fu, PLAN-179): o P0 recusa rodar com CEO_KERNEL_OVERRIDE ou
#      CEO_KERNEL_OVERRIDE_ACK já no ambiente e confere VIVO, pelas funções do próprio hook, que o
#      caminho é kernel e que o par que o script vai exportar (reason-SLUG + I-ACCEPT) satisfaz
#      _override_granted(); o override é armado só em volta de cada `git apply` (aplicar e, no
#      desfazer, reverter) e desarmado logo depois — o menor escopo do W3-K. Sessão dedicada (regra
#      U-3 do PLAN-169): não encadeie esta cerimônia com outra no mesmo shell;
#  (5) rodada 3 do rail: tolerância ZERO a falha de qualquer teste dos arquivos da cura (sem rerun,
#      sem «instável»); o registro do rail amarra também o TEXTO (Rail-Text-sha256 = sha256 do
#      sentinel com os campos TO-FILL-BY-SIGN, conferido no P0); a evidência que o sentinel cita
#      precisa estar commitada; um patch com cabeçalho estrutural (arquivo novo/removido, troca de
#      modo, rename, cópia, binário) é recusado pelo nome antes de qualquer arme de kernel; o desfazer
#      marca APPLIED antes do `git apply`, distingue «o patch não chegou a aplicar», reconhece um land
#      já feito (sinal depois do commit), ignora novos sinais enquanto roda, e o --dry-run sai ≠ 0 se
#      o desfazer não restaurar a árvore;
#  (6) anexo da rodada 3 (forma da W1): o texto que se assina é o `HEAD:<sentinel>` (o que o
#      Rail-Text-sha256 nomeia), preenchido numa cópia fora da árvore; o sentinel cita o marcador dos
#      campos só nas 4 linhas de campo (recusa no P0, não depois da bateria); o sentinel vivo que muda
#      durante a bateria aborta (com a receita); depois do stage, o blob do sentinel no índice tem de
#      ser o preenchido e a assinatura é reverificada sobre o conteúdo do índice.
# As cópias em staged/ (de onde o patch é derivado por derive-auditrace-patch.sh) NÃO são commitadas
# (.gitignore: «staged/»); o portador dos bytes é o patch, como no molde.
# Todo o resto é o molde: P0 (main, remote, origin/main contido, árvore rastreada limpa, materiais
# commitados, sentinel com os quatro TO-FILL, base pinada pelos blobs pré-imagem, canônicos = os
# declarados, touched = Scope), registro do rail (≤ 3 rodadas, APPROVE ou DECLARED-P2 sobre o sha256
# do patch), falhas julgadas contra a árvore sem o patch, assinatura com --local-user da chave do
# allowlist conferida por GOODSIG + VALIDSIG, stage EXATO, HEAD e blobs reconferidos.
#
# OWNER-AUDITRACE-SIGN.sh — verifica, assina e landa a cura da corrida do agent_spawn em UM passo.
#
#   bash .claude/plans/PLAN-194/w-auditrace/OWNER-AUDITRACE-SIGN.sh                 # real (terminal interativo)
#   bash .claude/plans/PLAN-194/w-auditrace/OWNER-AUDITRACE-SIGN.sh --dry-run       # ensaio: não assina, não commita
#   bash .claude/plans/PLAN-194/w-auditrace/OWNER-AUDITRACE-SIGN.sh --check-base REV
#        # só leitura, em segundos: a base pinada do patch (o blob pré-imagem de cada caminho)
#        # é a de REV? rc 0 = o patch aplica sobre REV; rc 1 = nomeia o caminho que difere
#
# Ordem (nada é assinado antes de a bateria passar; o passo falível do GPG é o último antes do
# commit): P0 pré-condições + chave de assinatura + registro do rail → 1/7 aplica o
# patch → 2/7 bytes aplicados = bytes revisados → 3/7 bateria (gates de corpus + testes da cura +
# suítes do pytest.ini com a divisão de marcadores do CI, falhas julgadas contra a árvore sem o patch)
# → 4/7 preenche Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data no sentinel → 5/7 assina (um
# pinentry) → 6/7 stage EXATO (touched ∪ {sentinel, .asc}) → 7/7 commit.
# NÃO faz push. Qualquer falha (ou Ctrl-C / TERM / HUP) antes do commit desfaz TUDO o que o
# script fez: reverte o patch, restaura o sentinel, remove a .asc e o worktree da base. Os logs
# ficam no diretório temporário que a falha nomeia. Rodar de novo depois de um abort é seguro.
# A bateria roda as suítes do pytest.ini com a divisão de marcadores do CI (paralela
# 'not serial' + serial) — um conjunto MAIOR que o dos jobs do CI. O --dry-run é opcional (repete a
# bateria inteira; o modo real já desfaz tudo numa falha). Fique no terminal: o pinentry vem DEPOIS
# da bateria, e um pinentry que expira desfaz tudo.
# Uma falha nomeada «falhas NOVAS» pode vir de estado da árvore viva (arquivos ignorados, dist/,
# .claude/state/) que o worktree limpo da base não tem: confira o log; a saída é rodar de novo,
# nunca editar o patch.
# Se o GPG reclamar de pinentry:  export GPG_TTY=$(tty)
set -euo pipefail
DRY=0
CHECK_BASE=""
case "${1:-}" in
  "") : ;;
  --dry-run) DRY=1 ;;
  --check-base) CHECK_BASE="${2:-HEAD}" ;;
  *) printf 'uso: bash %s [--dry-run | --check-base [REV]]\n' "$0" >&2; exit 2 ;;
esac
# A raiz resolve pela LOCALIZAÇÃO do script, nunca pelo cwd: o Owner pode chamar de qualquer lugar.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel)"
cd "$ROOT"
D=.claude/plans/PLAN-194/w-auditrace
SENT=.claude/plans/PLAN-194/wave-auditrace-approved.md
ASC="$SENT.asc"
PATCH="$D/auditrace.patch"
SELF="$D/OWNER-AUDITRACE-SIGN.sh"
ORACLE=.claude/hooks/check_canonical_edit.py
SIGNERS=.claude/sentinel-signers.txt
GPG_VERIFY_LIB=.claude/hooks/_lib/gpg_verify.py
CANON="
.claude/hooks/audit_log.py
"
CURE_TESTS=".claude/hooks/tests/test_two_writer_chain.py .claude/hooks/tests/test_audit_log.py"
# evidência que o texto assinado cita por caminho: tem de estar commitada (Anchor-SHA a contém)
EVIDENCE="$D/red-control.txt $D/lockstress-S361.txt $D/rail-prompt.md $D/test-ceremony-auditrace.sh"
KERNEL_HOOK=.claude/hooks/check_arbitration_kernel.py
# reason-SLUG do override de kernel: o contrato do hook é [A-Za-z0-9._-]{1,120} (_REASON_RE)
KERNEL_REASON="PLAN-194.wave-auditrace.sentinel-wave-auditrace-approved"
RAIL_MAX_ROUNDS=3
APPLIED=0
SENT_TOUCHED=0
SIGN_STARTED=0
BASE_WT=""
HEAD_SHA=""
UNDO_STATUS=""
BAK=$(mktemp -d "${TMPDIR:-/tmp}/auditrace-sign.XXXXXX")
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
patch_blobs() {  # arquivo de saída — uma linha "<caminho> <blob pré-imagem> <blob pós-imagem>" por caminho do patch
  awk '/^diff --git /{p=$3; sub(/^a\//, "", p)} /^index /{split($2, h, /\.\./); print p, h[1], h[2]}' "$PATCH" > "$1"
}

if [ -n "$CHECK_BASE" ]; then
  # Só leitura: nada é aplicado, nada é escrito na árvore. Para uma land livre que toque estes
  # caminhos conferir, ANTES de landar, que os bytes da base são os que este pacote pinou.
  [ -f "$PATCH" ] || die "ausente: $PATCH"
  git rev-parse --verify --quiet "$CHECK_BASE^{commit}" >/dev/null || die "revisão desconhecida: $CHECK_BASE"
  patch_blobs "$BAK/blobs"
  [ -s "$BAK/blobs" ] || die "o patch não tem linhas index"
  CB_BAD=0
  while read -r p old new; do
    cur=$(git rev-parse --verify --quiet "$CHECK_BASE:$p") || cur="(ausente)"
    if [ "${#old}" -eq 40 ] && [ "$cur" = "$old" ]; then
      printf '   igual: %s\n' "$p"
    else
      printf '   DIFERE: %s (em %s: %s; o patch espera %s)\n' "$p" "$CHECK_BASE" "$cur" "$old"
      CB_BAD=1
    fi
  done < "$BAK/blobs"
  rm -f "$BAK/blobs"
  rmdir "$BAK"
  if [ "$CB_BAD" = "1" ]; then
    printf '\nFAIL: a base pinada da cura auditrace não é a de %s — o auditrace.patch não aplica ali.\n' "$CHECK_BASE" >&2
    printf 'Re-derivar o pacote pede uma rodada de rail além da regra de parada (decisão do Owner); não\n' >&2
    printf 'lande bytes diferentes nesses caminhos sem essa decisão.\n' >&2
    exit 1
  fi
  printf '\nOK: a base pinada da cura auditrace é a de %s (o auditrace.patch aplica ali).\n' "$CHECK_BASE"
  exit 0
fi
kernel_arm() {  # o override de kernel, só em volta de um `git apply` (menor escopo, molde W3-K)
  export CEO_KERNEL_OVERRIDE="$KERNEL_REASON"
  export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
}
kernel_disarm() {
  unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK
}
remove_base_wt() {
  if [ -n "$BASE_WT" ]; then
    if [ -d "$BASE_WT" ]; then
      git worktree remove --force "$BASE_WT" >/dev/null 2>&1 \
        || printf 'remova à mão: git worktree remove --force %s\n' "$BASE_WT" >&2
    fi
    git worktree prune >/dev/null 2>&1 || :
    BASE_WT=""
  fi
}
undo() {
  set +e
  local done_what=""
  # Um sinal que chega depois do `git commit` (antes de o script desarmar este trap) não desfaz um
  # land: HEAD avançou um commit sobre o Anchor-SHA e esse commit traz a .asc.
  if [ "$DRY" != "1" ] && [ -n "$HEAD_SHA" ] \
     && [ "$(git rev-parse -q --verify HEAD~1 2>/dev/null)" = "$HEAD_SHA" ] \
     && git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | grep -xF -- "$ASC" >/dev/null; then
    UNDO_STATUS="LANDADO"
    printf '\nLANDADO em %s (o sinal chegou depois do commit): nada foi desfeito.\n' "$(git rev-parse --short HEAD)" >&2
    return 0
  fi
  remove_base_wt
  if [ "$APPLIED" = "1" ]; then
    git reset -q HEAD -- . 2>/dev/null
    if git apply -R --check "$PATCH" 2>/dev/null; then
      kernel_arm; git apply -R "$PATCH"; kernel_disarm; done_what="$done_what patch-revertido"
    elif git apply --check "$PATCH" 2>/dev/null && xargs git diff --quiet HEAD -- < "$BAK/touched" 2>/dev/null; then
      done_what="$done_what patch-nao-chegou-a-aplicar"
    else
      done_what="$done_what PATCH-NAO-REVERTIDO"
    fi
    # Um caminho tocado que mudou depois do apply fica diferente do HEAD — reverta o patch limpo ou
    # não. O P0 exigiu árvore rastreada limpa, então a pré-imagem é o HEAD; quem descarta é você.
    if ! xargs git diff --quiet HEAD -- < "$BAK/touched" 2>/dev/null; then
      printf 'caminhos do patch ainda diferem do HEAD (mudaram depois do apply). Confira com «git diff» e\n' >&2
      printf 'restaure a pré-imagem com: git checkout HEAD -- %s\n' "$(tr '\n' ' ' < "$BAK/touched")" >&2
      done_what="$done_what CAMINHOS-DO-PATCH-AINDA-SUJOS"
    fi
    APPLIED=0
  fi
  if [ "$SENT_TOUCHED" = "1" ] && [ "$DRY" != "1" ]; then
    git reset -q HEAD -- "$SENT" 2>/dev/null
    if [ -L "$SENT" ]; then
      printf 'sentinel virou symlink — restaure à mão a partir de %s/sentinel.head.md\n' "$BAK" >&2; done_what="$done_what SENTINEL-NAO-RESTAURADO"
    else
      cp "$BAK/sentinel.head.md" "$SENT"; done_what="$done_what sentinel-restaurado"
    fi
    SENT_TOUCHED=0
  fi
  if [ "$SIGN_STARTED" = "1" ] && [ "$DRY" != "1" ]; then
    git reset -q HEAD -- "$ASC" 2>/dev/null
    if [ -f "$ASC" ]; then rm -- "$ASC"; done_what="$done_what asc-removida"; fi
    SIGN_STARTED=0
  fi
  kernel_disarm
  UNDO_STATUS="$done_what"
  printf '\ndesfeito:%s\n' "${done_what:- nada a desfazer}" >&2
}
# A chave de assinatura e a conferência do signatário usam o allowlist commitado e a biblioteca de
# verificação do próprio repositório (_lib/gpg_verify.py: GOODSIG + VALIDSIG, impressão digital no
# allowlist):
#   signer_tool pick                     -> imprime a impressão digital da chave SECRETA a usar
#   signer_tool verify <arquivo> <.asc>  -> imprime a impressão digital aceita
signer_tool() {
  python3 - "$ROOT" "$GPG_VERIFY_LIB" "$SIGNERS" "$@" <<'PY'
import importlib.util
import subprocess
import sys
from pathlib import Path

root, glib, allow, mode = sys.argv[1:5]
rest = sys.argv[5:]
spec = importlib.util.spec_from_file_location("gpg_verify_auditrace", str(Path(root) / glib))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
if mode == "pick":
    fprs, err = g.load_allowlist(Path(root) / allow)
    if err:
        raise SystemExit("allowlist de signatários inválido (%s): %s" % (allow, err))
    out = subprocess.run(["gpg", "--batch", "--with-colons", "--list-secret-keys"],
                         capture_output=True, text=True).stdout
    want = False
    for line in out.splitlines():
        f = line.split(":")
        if f[0] == "sec":
            want = True
        elif f[0] == "fpr" and want:
            want = False
            fpr = g.normalise_fpr(f[9]) if len(f) > 9 else ""
            if fpr and fpr in fprs:
                print(fpr)
                raise SystemExit(0)
    raise SystemExit("nenhuma chave secreta deste GNUPGHOME está em %s" % allow)
if mode == "verify" and len(rest) == 2:
    ok, fpr, reason = g.verify_detached(Path(rest[0]), Path(rest[1]), allowlist_path=Path(root) / allow)
    if not ok:
        raise SystemExit("assinatura recusada: %s" % reason)
    print(fpr)
    raise SystemExit(0)
raise SystemExit("uso interno inválido: %s" % " ".join([mode] + rest))
PY
}
on_exit() {
  # Os dois caminhos de sucesso desarmam este trap antes de sair; então TODA execução dele é um
  # término anormal — inclusive com rc 0: no bash 3.2, um erro de expansão (set -u) dentro de uma
  # lista `a && b || c` encerra o shell com status 0. Desfaz sempre e nunca sai com 0.
  local rc=$?
  trap '' INT TERM HUP  # um 2.º Ctrl-C não interrompe o desfazer pela metade
  undo
  [ "$rc" -ne 0 ] || rc=1
  printf '(rc=%s) abortado; logs em %s; árvore conferível com: git status --short\n' "$rc" "$BAK" >&2
  exit "$rc"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

say "P0 pré-condições"
# Molde de kernel: um override que já vem do ambiente é sobra de outra cerimônia (regra U-3) e
# autorizaria esta sem ninguém pedir — recusa antes de tudo.
if [ -n "${CEO_KERNEL_OVERRIDE:-}" ] || [ -n "${CEO_KERNEL_OVERRIDE_ACK:-}" ]; then
  die "CEO_KERNEL_OVERRIDE/_ACK já estão no ambiente ANTES deste script — desarme (unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK) e rode de novo; o SIGN arma e desarma o próprio override, no menor escopo"
fi
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo (rode num terminal, não por pipe)"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
git remote -v | grep -q 'Canhada-Labs/ceo-orchestration' || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
git merge-base --is-ancestor origin/main HEAD || die "HEAD não contém origin/main (atrás ou divergente) — puxe antes"
AHEAD=$(git rev-list --count origin/main..HEAD)
# Um worktree da base que uma execução anterior INTERROMPIDA (kill -9, queda) deixou é deste script
# (um diretório auditrace-sign.*/base-wt que só ele cria): removido antes de começar.
git worktree list --porcelain | awk '/^worktree /{print substr($0, 10)}' > "$BAK/worktrees"
while IFS= read -r wt; do
  case "$wt" in
    */auditrace-sign.*/base-wt)
      printf '   removendo o worktree da base de uma execução anterior interrompida: %s\n' "$wt"
      git worktree remove --force "$wt" >/dev/null 2>&1 \
        || printf '   (não removido — depois: git worktree remove --force %s)\n' "$wt" ;;
  esac
done < "$BAK/worktrees"
git worktree prune >/dev/null 2>&1 || :
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  git status --short --untracked-files=no >&2
  printf 'Se isto sobrou de uma execução INTERROMPIDA deste script (kill -9, queda):\n' >&2
  printf '  git reset -q HEAD -- . && git apply -R %s   (se o patch estiver aplicado)\n' "$PATCH" >&2
  printf '  git checkout -- %s ; rm -f %s\n' "$SENT" "$ASC" >&2
  die "há modificação RASTREADA pendente"
fi
[ ! -e "$ASC" ] || die "já existe $ASC — remova a assinatura antiga antes (rm $ASC)"
# shellcheck disable=SC2086 # EVIDENCE é uma lista de caminhos sem espaço, partida de propósito
for f in "$SENT" "$PATCH" "$ORACLE" "$SELF" "$SIGNERS" "$GPG_VERIFY_LIB" $EVIDENCE; do [ -f "$f" ] || die "ausente: $f"; done
# shellcheck disable=SC2086
for f in "$SENT" "$PATCH" "$SELF" "$SIGNERS" "$GPG_VERIFY_LIB" $EVIDENCE; do
  git ls-files --error-unmatch -- "$f" >/dev/null 2>&1 || die "$f não está commitado — lande os materiais do pacote (commit livre) antes"
done
[ ! -L "$SENT" ] || die "sentinel é symlink"
for k in Patch-sha256 Rail-Record-sha256 Anchor-SHA Data; do
  awk -v k="$k" '$0 == k ": TO-FILL-BY-SIGN" {n++} END {exit n == 1 ? 0 : 1}' "$SENT" \
    || die "o sentinel não tem exatamente uma linha '$k: TO-FILL-BY-SIGN' — ele já foi preenchido?"
done
# O marcador só pode aparecer nas 4 linhas de campo: o preenchimento (passo 4) recusa sobra, e essa
# recusa tem de vir AGORA, não depois da bateria.
[ "$(awk '{n += gsub(/TO-FILL-BY-SIGN/, "")} END {print n + 0}' "$SENT")" = "4" ] \
  || die "o sentinel cita TO-FILL-BY-SIGN fora das 4 linhas de campo — o preenchimento recusaria a sobra"
# O texto a assinar é o do HEAD (o que o rail revisou), não o arquivo vivo; com a árvore rastreada
# limpa os dois são iguais agora, e o passo 3 aborta se o vivo mudar durante a bateria.
git show "HEAD:$SENT" > "$BAK/sentinel.head.md" || die "não consegui ler HEAD:$SENT"
cmp -s "$BAK/sentinel.head.md" "$SENT" || die "o sentinel vivo difere do HEAD:$SENT"
command -v gpg >/dev/null 2>&1 || die "gpg ausente"
# A chave é escolhida ANTES da bateria (também no --dry-run): sem chave do allowlist, a falha vem
# agora, não depois de meia hora.
SIGN_KEY=$(signer_tool pick) || die "sem chave secreta do allowlist $SIGNERS neste GNUPGHOME"
if [ "$DRY" != "1" ]; then
  GPG_TTY=$(tty) || die "não consegui ler o terminal (tty) para o GPG_TTY"
  export GPG_TTY
fi
python3 -m pytest --version >/dev/null 2>&1 || die "pytest ausente (python3 -m pip install 'pytest==8.*')"
python3 -c 'import xdist' >/dev/null 2>&1 || die "pytest-xdist ausente (python3 -m pip install pytest-xdist) — as suítes rodam como no CI"
if grep -nE '^(new file mode|deleted file mode|old mode|new mode|rename (from|to)|copy (from|to)|similarity index|dissimilarity index|Binary files|GIT binary patch)' "$PATCH" > "$BAK/structural"; then
  sed 's/^/   /' "$BAK/structural" >&2
  die "o patch tem cabeçalho estrutural (arquivo novo ou removido, troca de modo, rename, cópia ou binário) — este pacote só edita o conteúdo de arquivos existentes"
fi
git apply --check "$PATCH" || die "git apply --check FALHOU — a árvore divergiu do patch"
patch_blobs "$BAK/blobs"
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$BAK/touched"
awk '{print $1}' "$BAK/blobs" | sort -u | cmp -s - "$BAK/touched" || die "as linhas index do patch não cobrem exatamente os caminhos tocados"
while read -r p old new; do
  [ "${#old}" -eq 40 ] && [ "${#new}" -eq 40 ] || die "o patch não foi gerado com --full-index ($p)"
  cur=$(git rev-parse "HEAD:$p" 2>/dev/null) || die "$p não existe no HEAD"
  [ "$cur" = "$old" ] || die "a base de $p mudou desde a montagem do pacote (HEAD tem $cur, o patch espera $old) — o pacote precisa ser re-derivado sobre este HEAD"
done < "$BAK/blobs"
: > "$BAK/canon-now"
while read -r f; do
  v=$(python3 "$ORACLE" --is-canonical "$f" 2>/dev/null | awk '{print $2}')
  case "$v" in
    1) printf '%s\n' "$f" >> "$BAK/canon-now" ;;
    0) : ;;
    *) die "o oráculo não respondeu para $f (saída: '$v')" ;;
  esac
done < "$BAK/touched"
printf '%s\n' $CANON | sort -u > "$BAK/canon-expected"
sort -u "$BAK/canon-now" | cmp -s - "$BAK/canon-expected" \
  || die "os caminhos canônicos que o patch toca ≠ os declarados:$(printf '\n   %s' $(comm -3 "$BAK/canon-expected" "$BAK/canon-now"))"
awk '/^## Scope/{s=1; next} /^## /{s=0} s && /^- `/{sub(/^- `/, ""); sub(/`.*/, ""); print}' "$BAK/sentinel.head.md" | sort -u > "$BAK/scope"
DIFF=$(comm -3 "$BAK/touched" "$BAK/scope")
[ -z "$DIFF" ] || die "touched ≠ Scope do sentinel:$(printf '\n   %s' $DIFF)"
PATCH_SHA=$(shasum -a 256 "$PATCH" | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

say "P0 registro do rail"
LAST=0
n=1
while [ -f "$D/rail-round-$n.md" ]; do LAST=$n; n=$((n + 1)); done
[ "$LAST" -ge 1 ] || die "nenhum registro de rail ($D/rail-round-1.md)"
NREC=$(find "$D" -maxdepth 1 -name 'rail-round-*.md' | wc -l | tr -d ' ')
[ "$NREC" = "$LAST" ] || die "registros de rail não contíguos ($NREC arquivos; contíguos de 1 a $LAST)"
[ "$LAST" -le "$RAIL_MAX_ROUNDS" ] || die "$LAST rodadas de rail passam da regra de parada pré-registrada ($RAIL_MAX_ROUNDS)"
REC="$D/rail-round-$LAST.md"
git ls-files --error-unmatch -- "$REC" >/dev/null 2>&1 || die "$REC não está commitado"
field() { awk -v k="$1" 'index($0, k ": ") == 1 {v = substr($0, length(k) + 3); n++} END {if (n != 1) exit 3; print v}' "$REC"; }
R_ROUND=$(field Rail-Round) || die "$REC: linha Rail-Round ausente ou repetida"
R_SUBJ=$(field Rail-Subject-sha256) || die "$REC: linha Rail-Subject-sha256 ausente ou repetida"
R_VERD=$(field Rail-Verdict) || die "$REC: linha Rail-Verdict ausente ou repetida"
R_FIND=$(field Rail-Findings) || die "$REC: linha Rail-Findings ausente ou repetida"
R_TEXT=$(field Rail-Text-sha256) || die "$REC: linha Rail-Text-sha256 ausente ou repetida"
[ "$R_ROUND" = "$LAST" ] || die "$REC declara Rail-Round '$R_ROUND'"
[ "$R_SUBJ" = "$PATCH_SHA" ] || die "o último registro do rail ($REC) revisou outro patch ($R_SUBJ), não este ($PATCH_SHA)"
SENT_SHA=$(shasum -a 256 "$BAK/sentinel.head.md" | awk '{print $1}')
[ "$R_TEXT" = "$SENT_SHA" ] || die "o último registro do rail ($REC) revisou outro texto assinável ($R_TEXT), não o sentinel do HEAD ($SENT_SHA)"
case "$R_VERD" in
  APPROVE)
    [ "$R_FIND" = "P0=0 P1=0 P2=0" ] || die "APPROVE exige 'P0=0 P1=0 P2=0' (o registro diz '$R_FIND')" ;;
  DECLARED-P2)
    case "$R_FIND" in
      "P0=0 P1=0 P2="[1-9]*) : ;;
      *) die "DECLARED-P2 exige 'P0=0 P1=0 P2=<n>' com n > 0 (o registro diz '$R_FIND')" ;;
    esac
    awk '/^## P2 declarados/{s=1; next} /^## /{s=0} s && /^- /{n++} END {exit n ? 0 : 1}' "$REC" \
      || die "DECLARED-P2 sem itens na seção '## P2 declarados' de $REC" ;;
  *) die "o veredito do último registro do rail é '$R_VERD' — o SIGN só aceita APPROVE ou DECLARED-P2" ;;
esac
RAIL_SHA=$(shasum -a 256 "$REC" | awk '{print $1}')
printf '   OK: main (%s commit(s) à frente de origin/main), árvore limpa, patch aplicável sobre a base pinada,\n' "$AHEAD"
printf '       %s caminhos = Scope, canônico = o declarado, materiais commitados\n' "$(wc -l < "$BAK/touched" | tr -d ' ')"
printf '   chave de assinatura (em %s): %s\n' "$SIGNERS" "$SIGN_KEY"
# VIVO, pelas funções do próprio hook de kernel: o caminho canônico é kernel e o par que o script
# exporta em volta do `git apply` satisfaz _override_granted() (molde 179fu, T20e).
python3 - "$ROOT" "$KERNEL_HOOK" "$KERNEL_REASON" $CANON <<'PY' || die "contrato do override de kernel não confere (acima)"
import importlib.util
import sys
from pathlib import Path

root, hook, reason = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("cak_auditrace", str(root / hook))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
for p in sys.argv[4:]:
    if not m._is_kernel_path(str(root / p), root):
        raise SystemExit("%s não está mais em _KERNEL_PATHS — o texto assinado (seção Kernel) ficaria falso" % p)
if not m._override_granted({"CEO_KERNEL_OVERRIDE": reason, "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT"}):
    raise SystemExit("o par (%r, I-ACCEPT) não satisfaz _override_granted() do hook" % reason)
if m._override_granted({}):
    raise SystemExit("_override_granted() concede sem o par — o contrato do hook mudou")
PY
printf '   kernel: %s em _KERNEL_PATHS; par do override validado vivo contra o hook (reason %s)\n' "$(printf '%s' $CANON)" "$KERNEL_REASON"
printf '   rail: %s = %s (%s), sobre Patch-sha256 %s e o sentinel %s\n' "$REC" "$R_VERD" "$R_FIND" "$PATCH_SHA" "$SENT_SHA"

say "1/7 aplicar o patch"
APPLIED=1  # antes do apply: um sinal no meio dele ainda passa pelo desfazer
kernel_arm
git apply "$PATCH" || die "git apply falhou"
kernel_disarm
[ -z "${CEO_KERNEL_OVERRIDE:-}${CEO_KERNEL_OVERRIDE_ACK:-}" ] || die "o override de kernel não desarmou"
printf '   override de kernel armado só em volta do git apply (desarmado agora)\n'

say "2/7 bytes aplicados = bytes revisados"
while read -r p old new; do
  now=$(git hash-object -- "$p")
  [ "$now" = "$new" ] || die "$p depois do apply tem o blob $now; o patch revisado declara $new"
done < "$BAK/blobs"
[ -x .claude/hooks/audit_log.py ] || die "o hook não é executável após o apply"
printf '   %s blobs conferidos contra o index pós-imagem do patch\n' "$(wc -l < "$BAK/blobs" | tr -d ' ')"

say "3/7 bateria (gates de corpus + testes da cura + suítes do pytest.ini, julgados contra a árvore sem o patch)"
NOTES=""
ensure_base_wt() {  # a árvore SEM o patch: worktree destacado do HEAD, criado uma vez, removido no fim
  if [ -z "$BASE_WT" ]; then
    BASE_WT="$BAK/base-wt"
    git worktree add --quiet --detach "$BASE_WT" HEAD >/dev/null 2>&1 || die "não consegui criar o worktree da base em $BASE_WT"
  fi
}
gov_check() {  # validate-governance completo, e o resumo precisa dizer "Errors:   0"
  bash .claude/scripts/validate-governance.sh 2>&1 | tee "$BAK/gov-last.out" | awk '/Errors:   0/{ok=1} END{exit ok ? 0 : 1}'
}
gate() {  # rótulo, comando... — reprova o SIGN só o gate que passa na árvore sem o patch
  local label="$1"
  shift
  if "$@" >"$BAK/g.out" 2>&1; then printf '   ok: %s\n' "$label"; return 0; fi
  cp "$BAK/g.out" "$BAK/gate-fail.out"
  ensure_base_wt
  if (cd "$BASE_WT" && "$@") >"$BAK/g-base.out" 2>&1; then
    tail -12 "$BAK/gate-fail.out" >&2
    die "$label reprovou com o patch e passa sem ele (log: $BAK/gate-fail.out)"
  fi
  printf '   PRÉ-EXISTENTE: %s reprova também sem o patch — não é deste pacote (log: %s)\n' "$label" "$BAK/g-base.out"
  NOTES="$NOTES
   - $label"
}
judge_fails() {  # julga os ids em now-fails: isolado com o patch; se falhar de novo, na árvore sem o patch
  sort -u "$BAK/now-fails" > "$BAK/now-fails.sorted"
  : > "$BAK/now-fails"
  : > "$BAK/real-new-fails"
  local test_id brc tries passed
  while IFS= read -r test_id; do
    [ -n "$test_id" ] || continue
    for cf in $CURE_TESTS; do  # tolerância ZERO: um vermelho intermitente aqui é o sinal da corrida
      case "$test_id" in
        "$cf"|"$cf"::*) die "teste da cura falhou: $test_id — tolerância zero, sem rerun (logs em $BAK)" ;;
      esac
    done
    # até 3 reruns isolados com o patch: um teste sensível a tempo pode falhar de novo numa máquina
    # carregada
    tries=0
    passed=0
    while [ "$tries" -lt 3 ]; do
      tries=$((tries + 1))
      if python3 -m pytest "$test_id" -q -p no:cacheprovider >"$BAK/rerun.out" 2>&1; then passed=1; break; fi
    done
    if [ "$passed" = "1" ]; then
      printf '   instável (passou isolada, com o patch, na tentativa %s de 3): %s\n' "$tries" "$test_id"
      continue
    fi
    ensure_base_wt
    set +e
    (cd "$BASE_WT" && python3 -m pytest "$test_id" -q -p no:cacheprovider) >"$BAK/rerun-base.out" 2>&1
    brc=$?
    set -e
    if [ "$brc" = "1" ]; then
      printf '   PRÉ-EXISTENTE (falha também sem o patch): %s\n' "$test_id"
      NOTES="$NOTES
   - $test_id"
    else
      printf '%s  (sem o patch: rc=%s)\n' "$test_id" "$brc" >> "$BAK/real-new-fails"
    fi
  done < "$BAK/now-fails.sorted"
  if [ -s "$BAK/real-new-fails" ]; then
    sed 's/^/   /' "$BAK/real-new-fails" >&2
    die "falhas NOVAS: falham com o patch e passam (ou não existem) sem ele — logs em $BAK"
  fi
}
run_pass() {  # rótulo, log, argumentos do pytest — anota os ids que falharam
  local label="$1" log="$2" rc before after
  shift 2
  before=$(wc -l < "$BAK/now-fails" | tr -d ' ')
  set +e
  python3 -m pytest "$@" >"$log" 2>&1
  rc=$?
  set -e
  case "$rc" in 0|1) ;; *) die "$label não terminou (rc=$rc) — log em $log" ;; esac
  # O id vai até o primeiro " - " (a mensagem vem depois); num id parametrizado ("…::nome[…]"), até
  # o primeiro "]" seguido de " - " ou do fim da linha — o parâmetro pode conter " - ".
  awk '/^(FAILED|ERROR) / {
    l = $0; sub(/^(FAILED|ERROR) /, "", l); id = ""
    c = index(l, "::"); b = 0
    if (c > 0) { b = index(substr(l, c), "["); if (b > 0) b = b + c - 1 }
    if (b > 0) {
      n = length(l)
      for (i = b; i <= n; i++) {
        if (substr(l, i, 1) == "]" && (i == n || substr(l, i + 1, 3) == " - ")) { id = substr(l, 1, i); break }
      }
    }
    if (id == "") { id = l; sub(/ - .*$/, "", id) }
    print id
  }' "$log" >> "$BAK/now-fails"
  after=$(wc -l < "$BAK/now-fails" | tr -d ' ')
  if [ "$rc" = "1" ] && [ "$after" = "$before" ]; then die "$label saiu rc=1 sem nenhum id de falha — log em $log"; fi
  printf '   %s: %s\n' "$label" "$(awk 'match($0, /[0-9]+ (passed|failed)[^=]*/) {v = substr($0, RSTART, RLENGTH)} END {print v}' "$log")"
}
python3 -m py_compile .claude/hooks/audit_log.py $CURE_TESTS || die "py_compile"
gate "test-env-hygiene" python3 .claude/scripts/check-test-env-hygiene.py
gate "inventário de variáveis de ambiente" python3 .claude/scripts/env-inventory-check.py --check
gate "hooks ativos executáveis" python3 .claude/scripts/check-active-hooks-executable.py
gate "contamination" bash .claude/scripts/check-contamination.sh
gate "build-plugin --check" python3 scripts/build-plugin.py --check
gate "mapa comando→skill→hook" python3 .claude/scripts/gen-command-skill-hook-map.py --check
gate "docs-freshness" python3 .claude/scripts/check-docs-freshness.py --format=text
gate "verify-counts" bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
gate "ceremony-lint" python3 .claude/scripts/check-ceremony-script.py
gate "validate-governance (Errors: 0)" gov_check
: > "$BAK/now-fails"
# shellcheck disable=SC2086 # CURE_TESTS é uma lista de caminhos sem espaço, partida de propósito
run_pass "testes da cura" "$BAK/suite-cure.out" $CURE_TESTS -q -rfE --tb=no -p no:cacheprovider
judge_fails
printf '   suítes do pytest.ini com a divisão de marcadores do CI (paralela e serial)\n'
run_pass "passada paralela" "$BAK/suite-parallel.out" -n auto -m 'not serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider
run_pass "passada serial" "$BAK/suite-serial.out" -m 'serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider
judge_fails
remove_base_wt
printf '   bateria: nenhuma falha nova em relação à árvore sem o patch\n'
if [ -n "$NOTES" ]; then
  printf '   ATENÇÃO — vermelhos PRÉ-EXISTENTES (reprovam também sem este patch; não bloqueiam este land):%s\n' "$NOTES"
fi
# Depois da bateria (longa): o HEAD e os bytes a landar precisam ser os de antes dela.
[ "$(git rev-parse HEAD)" = "$HEAD_SHA" ] \
  || die "o HEAD mudou durante a bateria (era $HEAD_SHA) — o Anchor-SHA não seria o pai do commit; rode de novo sobre o HEAD atual"
while read -r p old new; do
  now=$(git hash-object -- "$p")
  [ "$now" = "$new" ] || die "$p mudou durante a bateria (blob $now; o patch revisado declara $new) — os bytes a landar deixaram de ser os revisados"
done < "$BAK/blobs"
git diff --name-only --no-renames HEAD -- | sort -u > "$BAK/dirty-now"
[ ! -L "$SENT" ] || die "o sentinel virou symlink durante a bateria"
if grep -qxF -- "$SENT" "$BAK/dirty-now" \
   || [ "$(shasum -a 256 "$SENT" | awk '{print $1}')" != "$SENT_SHA" ]; then
  die "o sentinel mudou durante a bateria — o texto a assinar deixou de ser o do HEAD (o que o rail revisou); restaure com: git checkout HEAD -- $SENT"
fi
# Arquivos rastreados FORA do patch e do sentinel modificados durante a execução (um teste que
# escreve na árvore, ou outro processo): não entram no commit (o stage é exato), mas deixam a árvore
# suja — aviso no fim.
comm -23 "$BAK/dirty-now" "$BAK/touched" > "$BAK/dirty-other"
if [ -s "$BAK/dirty-other" ]; then
  printf '   AVISO: arquivos rastreados fora do patch mudaram durante a bateria (não entram no commit):\n'
  sed 's/^/     /' "$BAK/dirty-other"
fi

say "4/7 Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data no sentinel"
python3 - "$BAK/sentinel.head.md" "$BAK/sentinel.filled.md" "$HEAD_SHA" "$PATCH_SHA" "$RAIL_SHA" "$(date -u +%Y-%m-%d)" <<'PY'
import pathlib
import re
import sys

t = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
for key, val in (("Anchor-SHA", sys.argv[3]), ("Patch-sha256", sys.argv[4]),
                 ("Rail-Record-sha256", sys.argv[5]), ("Data", sys.argv[6])):
    t2, n = re.subn(r"^%s: TO-FILL-BY-SIGN$" % re.escape(key), "%s: %s" % (key, val), t, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("linha %s: TO-FILL-BY-SIGN não encontrada" % key)
    t = t2
if "TO-FILL-BY-SIGN" in t:
    raise SystemExit("sobrou TO-FILL-BY-SIGN no sentinel")
pathlib.Path(sys.argv[2]).write_text(t, encoding="utf-8")
PY
for kv in "Anchor-SHA: $HEAD_SHA" "Patch-sha256: $PATCH_SHA" "Rail-Record-sha256: $RAIL_SHA"; do
  awk -v l="$kv" '$0 == l {n++} END {exit n == 1 ? 0 : 1}' "$BAK/sentinel.filled.md" || die "o campo '$kv' não gravou no sentinel"
done
FILLED_BLOB=$(git hash-object -- "$BAK/sentinel.filled.md")
if [ "$DRY" = "1" ]; then
  SENT="$BAK/sentinel.filled.md"; ASC="$SENT.asc"
else
  [ ! -L "$SENT" ] || die "o sentinel virou symlink"
  SENT_TOUCHED=1
  cp "$BAK/sentinel.filled.md" "$SENT"
  [ "$(git hash-object -- "$SENT")" = "$FILLED_BLOB" ] || die "o sentinel gravado não é o preenchido a partir do HEAD"
fi
printf '   Anchor-SHA = %s\n   Patch-sha256 = %s\n   Rail-Record-sha256 = %s\n' "$HEAD_SHA" "$PATCH_SHA" "$RAIL_SHA"

say "5/7 assinar o sentinel (pinentry)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura\n'
else
  SIGN_STARTED=1
  gpg --armor --detach-sign --local-user "$SIGN_KEY" --output "$ASC" "$SENT" || die "assinatura falhou"
  SIGNER=$(signer_tool verify "$SENT" "$ASC") || die "a assinatura não verifica contra $SIGNERS"
  printf '   assinado por %s (no allowlist %s)\n' "$SIGNER" "$SIGNERS"
fi

say "6/7 stage EXATO + conferência touched ∪ {sentinel, .asc}"
xargs git add -- < "$BAK/touched"
[ "$DRY" = "1" ] || git add -- "$SENT" "$ASC"
git diff --cached --name-only --no-renames | sort > "$BAK/staged"
{ cat "$BAK/touched"; [ "$DRY" = "1" ] || printf '%s\n%s\n' "$SENT" "$ASC"; } | sort -u > "$BAK/expected"
EXTRA=$(comm -3 "$BAK/staged" "$BAK/expected")
[ -z "$EXTRA" ] || die "conjunto staged ≠ patch + sentinel:$(printf '\n   %s' $EXTRA)"
while read -r p old new; do
  st=$(git rev-parse --verify --quiet ":$p") || die "$p não está no índice depois do stage"
  [ "$st" = "$new" ] || die "$p no índice tem o blob $st; o patch revisado declara $new"
done < "$BAK/blobs"
if [ "$DRY" != "1" ]; then
  # O que vai para o commit é o que foi assinado: blob do índice = o preenchido; assinatura
  # reverificada sobre o CONTEÚDO DO ÍNDICE (não sobre o arquivo vivo).
  [ "$(git rev-parse --verify --quiet ":$SENT")" = "$FILLED_BLOB" ] || die "o sentinel no índice não é o assinado"
  git show ":$SENT" > "$BAK/sentinel.index.md"
  git show ":$ASC" > "$BAK/sentinel.index.asc"
  SIGNER2=$(signer_tool verify "$BAK/sentinel.index.md" "$BAK/sentinel.index.asc") || die "a assinatura no índice não verifica"
  [ "$SIGNER2" = "$SIGNER" ] || die "o signatário no índice ($SIGNER2) ≠ o da assinatura ($SIGNER)"
fi
sed 's/^/   /' "$BAK/staged"
printf '   %s blobs no índice conferidos contra o index pós-imagem do patch\n' "$(wc -l < "$BAK/blobs" | tr -d ' ')"
if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada assinado nem commitado; revertendo o patch"
  trap '' INT TERM HUP  # um Ctrl-C aqui não reentra no desfazer pelo on_exit
  undo
  trap - EXIT INT TERM HUP
  case "$UNDO_STATUS" in
    *NAO*|*SUJOS*) printf '\nFAIL: o desfazer do ensaio não restaurou a árvore (%s) — logs em %s\n' "$UNDO_STATUS" "$BAK" >&2; exit 1 ;;
  esac
  printf '\nEnsaio OK (logs em %s). Rode sem --dry-run para valer.\n' "$BAK"
  exit 0
fi

say "7/7 commit (nunca abre editor)"
# O pinentry pode ter levado minutos: o pai do commit precisa ser o Anchor-SHA assinado.
[ "$(git rev-parse HEAD)" = "$HEAD_SHA" ] \
  || die "o HEAD mudou antes do commit (era $HEAD_SHA) — o Anchor-SHA assinado não seria o pai do commit"
git commit -q -F - <<MSG
ceremony(PLAN-194): o gravador do agent_spawn lê o elo anterior dentro da trava

append_entry (.claude/hooks/audit_log.py) passa a ler o elo anterior
(audit-log.last-hmac), calcular o HMAC da linha, anexá-la e atualizar o
sidecar sob UMA mesma trava do log, a mesma sob a qual o audit_emit e a
drenagem do spool já leem o elo anterior e anexam. Antes, o elo era lido
e o HMAC calculado antes da trava: um gravador que anexasse no meio (outro
agent_spawn em paralelo ou um evento do audit_emit) deixava a linha
encadeada num elo velho, e verify_chain() acusava hmac_mismatch sem
adulteração. Numa rotação feita por este gravador, a linha 1 do log novo
passa a ser o chain_reset_marker do ADR-055-AMEND-2 (mesmo auxiliar do
audit_emit), e o agent_spawn encadeia nele; se o marcador não fica no
disco, a linha do agent_spawn sai sem HMAC
(hmac_error=chain_reset_marker_missing). Estouro da trava segue
descartando a linha com breadcrumb, sem bloquear a sessão e sem mexer no
estado da cadeia.

Testes: censo por AST, janela leitura→anexo, estouro da trava, rotação
com e sem cadeia, falha do anexo do marcador e corrida entre processos (4
gravadores de agent_spawn e 2 do audit_emit, síncrono e spool) com
verify_chain() íntegro. O censo, a janela, a rotação com cadeia, a falha
do marcador e a corrida são vermelhos sobre o código anterior; o estouro
da trava e a rotação sem cadeia guardam comportamento que já valia.

Cura o caso da condição 67 da v1.4.0-rc.1 (risco 11 do PLAN-194). As
quebras já gravadas pela corrida seguem no histórico; o sentinel declara
pela forma o que fica fora.

Kernel: audit_log.py está em _KERNEL_PATHS; o override de kernel
(reason-SLUG $KERNEL_REASON + I-ACCEPT, validado vivo contra o hook)
foi armado só em volta do git apply e desarmado logo depois.

Sentinel: $SENT (assinado por $SIGNER; Anchor-SHA $HEAD_SHA;
Patch-sha256 $PATCH_SHA; Rail-Record-sha256 $RAIL_SHA, $REC)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
APPLIED=0; SENT_TOUCHED=0; SIGN_STARTED=0
trap - EXIT INT TERM HUP
printf '\nLANDADO em %s. Push é decisão sua: git push origin main\n' "$(git rev-parse --short HEAD)"
[ "$(git rev-parse HEAD~1)" = "$HEAD_SHA" ] \
  || printf 'ATENÇÃO: o pai do commit não é o Anchor-SHA %s — confira com: git log -2 --format=%%H\n' "$HEAD_SHA" >&2
git status --porcelain --untracked-files=no > "$BAK/dirty-after"
if [ -s "$BAK/dirty-after" ]; then
  printf '\nATENÇÃO: a árvore rastreada ficou suja (a bateria ou outro processo mudou estes arquivos; eles NÃO\n' >&2
  printf 'estão no commit). A próxima cerimônia recusa árvore suja. Confira com «git diff» e, se for sobra\n' >&2
  printf 'da bateria, restaure com «git checkout -- <arquivo>»:\n' >&2
  sed 's/^/   /' "$BAK/dirty-after" >&2
fi
