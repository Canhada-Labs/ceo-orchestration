#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (PLAN-194 W4: publish do npm em Node 24
# com npm 11.20.0 exato, e a rc prova o toolchain sem publicar), clonada do molde OWNER-W3B1-SIGN.sh
# (PLAN-194 W3b.1, o SIGN mais novo), com o actionlint do OWNER-W1-SIGN.sh (PLAN-194 W1, o último SIGN
# que mudou workflow). O que muda em relação ao molde, declarado:
#  (1) DOIS caminhos canônicos (.github/workflows/npm-publish.yml e
#      .claude/governance/npm-trusted-publisher.txt) entre os 5 que o patch toca; os outros 3 são livres
#      (.claude/scripts/tests/test_release_workflow_asserts.py, docs/actions-versions.md,
#      npm/INTEGRITY.md) e landam no MESMO commit. O conteúdo novo de CADA canônico vive em duas formas
#      no pacote — a cópia staged (staged-w4/<caminho>) e o w4.patch (--full-index); o P0 exige, para
#      cada um, blob da cópia staged = blob pós-imagem do patch; o que landa é o patch. Um patch que
#      cria, remove, renomeia ou copia arquivo, ou muda modo, é recusado no P0 com nome (como no molde);
#  (2) o controle vermelho→verde é a classe Plan194W4PublishToolchainTest do teste do pacote — caminho
#      LIVRE do patch, que no HEAD não existe. No P0, um worktree destacado do HEAD recebe SÓ a parte
#      livre do patch (`git apply --exclude` dos 2 canônicos) e a classe, rodada pelo id do nó, tem de
#      REPROVAR ali com exatamente 17 falhas e nenhum passed/skipped/error (os canônicos do HEAD — Node
#      "20", npm ^11.5.1 — reprovam: o controle discrimina); na bateria, com o patch, ela tem de sair
#      rc 0 com exatamente 17 passed e nenhum skip. PyYAML é pré-condição (sem ele a lane YAML da
#      classe PULA e o controle perde metade da prova);
#  (3) passadas DURAS, fora do julgamento «pré-existente» (com o patch, rc != 0 reprova, também se a
#      base reprovar): o controle acima; os 4 arquivos de teste que leem o npm-publish.yml
#      ($HARD_TESTS); `actionlint .github/workflows/npm-publish.yml`; e `git apply --check` do patch
#      DORMENTE de rollback (.claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch). Esse
#      patch NÃO é rastreado (.gitignore `staged/`) e existe só no checkout vivo do Owner: o SIGN o lê
#      pelo caminho ABSOLUTO resolvido da raiz do repositório em que roda (no checkout vivo, o próprio
#      arquivo do Owner), exige arquivo regular com o tamanho e o sha256 pinados abaixo (ausente ou
#      diferente ⇒ recusa nomeada no P0) e exige que ele aplique no HEAD (P0) e com o patch (bateria);
#  (4) actionlint e shellcheck OBRIGATÓRIOS (da W1): sonda positiva da regra shellcheck do actionlint
#      antes da passada dura, e as duas formas de invocação do CI (a do job validate e a do
#      actionlint.yml) sobre todos os workflows, julgadas pelo MULTICONJUNTO de achados com e sem o
#      patch (um achado que só existe com o patch reprova, mesmo com a base vermelha);
#  (5) sem os check-model-* da W3b.1 (o patch não toca modelos); o worktree do controle segue as regras
#      do worktree da base (criado no P0, removido logo depois do controle; o desfazer e uma execução
#      nova removem o que uma execução interrompida deixou).
# Do molde, sem mudança de semântica: P0 (main, origin/main contido no HEAD, árvore rastreada limpa,
# materiais commitados, base pinada pelas linhas index, Scope = tocados, canônicos = o declarado, chave
# do allowlist, marcador de preenchimento só nas 4 linhas de campo); o registro do rail preso ao sha256
# do patch e ao do sentinel do HEAD (ainda com os TO-FILL-BY-SIGN), lido pela gramática estrita do bloco
# verbatim (cerca ```text … ```, ÚNICA, lida inteira; cerca mal formada, duplicada, indentada ou não
# fechada recusa), com a linha Rail-Reviewer-Verdict igual à ÚLTIMA linha `VERDICT:` da saída verbatim
# do revisor; allowlist de signatários e biblioteca de verificação lidas do HEAD; o sentinel que se
# assina é gerado do `HEAD:<sentinel>`, com abort se o arquivo vivo mudar durante a bateria, e a
# assinatura é reverificada sobre o conteúdo do índice; validate-governance julgado pela saída INTEIRA
# com e sem o patch (avisos do produtor excluídos pelo PREFIXO, a linha «Repo:» fora, espaços
# normalizados; com a base vermelha, um detalhe com caminho absoluto reprova por ruído — falha FECHADA);
# stage `--no-renames --name-status` (cada caminho do patch e o sentinel como M, a .asc como A, modo do
# HEAD e 100644 para tudo o que entra); árvore do índice conferido gravada antes do commit e, depois
# dele, a árvore commitada tem de ser ela e o pai, o Anchor-SHA; commit sem editor; o --dry-run só diz
# «Ensaio OK» com a árvore limpa depois do desfazer. Sem push.
#
# OWNER-W4-SIGN.sh — verifica, assina e landa a W4 do PLAN-194 em UM passo.
#
#   bash .claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh                 # real (terminal interativo)
#   bash .claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh --dry-run       # ensaio: não assina, não commita
#   bash .claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh --check-base REV
#        # só leitura, em segundos: a base pinada do patch (o blob pré-imagem de cada caminho) é a
#        # de REV? rc 0 = o patch aplica sobre REV; rc 1 = nomeia o caminho que difere
#
# Ordem (nada é assinado antes de a bateria passar; o passo falível do GPG é o último antes do
# commit): P0 pré-condições + patch dormente de rollback + controle vermelho no HEAD + chave de
# assinatura + registro do rail → 1/7 aplica o patch → 2/7 bytes aplicados = bytes revisados → 3/7
# bateria (as passadas duras, o actionlint nas duas formas do CI, os gates de corpus e as suítes do
# pytest.ini com a divisão de marcadores do CI, falhas destas julgadas contra a árvore sem o patch) →
# 4/7 sentinel do HEAD preenchido (Anchor-SHA, Patch-sha256, Rail-Record-sha256, Data) → 5/7 assina
# (um pinentry) → 6/7 stage EXATO (touched ∪ {sentinel, .asc}, por estado e modo) e reverificação da
# assinatura no índice → 7/7 commit.
# NÃO faz push. Uma falha (ou Ctrl-C / TERM / HUP) antes do commit desfaz o que o SCRIPT aplicou:
# reverte o patch, restaura o sentinel, remove a .asc e os worktrees do controle e da base. Se um
# caminho do patch mudou depois do apply: quando a mudança toca o contexto de um hunk (ou um hunk
# ancorado no fim do arquivo), o patch NÃO é revertido; quando cai fora, o patch é revertido e a mudança
# fica; nos dois casos o desfazer nomeia os caminhos sujos e imprime a receita. Arquivos rastreados que
# a bateria (ou outro processo) mudou fora do patch não são revertidos — o abort os lista, com a
# receita. Os logs ficam no diretório temporário que a falha nomeia. Rodar de novo depois de um abort
# é seguro.
# A bateria roda as suítes do pytest.ini (os `testpaths`) com a divisão de marcadores do CI (paralela
# 'not serial' + serial); elas contêm as raízes que coletam o teste do pacote (.claude/scripts/tests).
# Os 4 arquivos da passada dura levam ~2,5 min nesta máquina (medido em 2026-10-09); o resto, como no
# molde (~15 min numa máquina quieta). O --dry-run é opcional (repete a bateria inteira; o modo real já
# desfaz numa falha). Fique no terminal: o pinentry vem DEPOIS da bateria, e um pinentry que expira
# desfaz tudo. Uma falha nomeada «falhas NOVAS» pode vir de estado da árvore viva (arquivos ignorados,
# dist/, .claude/state/) que o worktree limpo da base não tem: confira o log; a saída é rodar de novo,
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
D=.claude/plans/PLAN-194/w4
SENT=.claude/plans/PLAN-194/w4-approved.md
SENT_REPO="$SENT"
ASC="$SENT.asc"
PATCH="$D/w4.patch"
SELF="$D/OWNER-W4-SIGN.sh"
STAGED_DIR="$D/staged-w4"
ORACLE=.claude/hooks/check_canonical_edit.py
SIGNERS=.claude/sentinel-signers.txt
GPG_VERIFY_LIB=.claude/hooks/_lib/gpg_verify.py
CANON="
.github/workflows/npm-publish.yml
.claude/governance/npm-trusted-publisher.txt
"
WORKFLOW=.github/workflows/npm-publish.yml
# O controle vermelho→verde: a classe nova do teste do pacote, pelo id do nó.
CTRL_FILE=.claude/scripts/tests/test_release_workflow_asserts.py
CTRL_CLASS=Plan194W4PublishToolchainTest
CTRL_N=17
# A passada dura de testes: o arquivo do pacote e os 3 oráculos vizinhos que leem o npm-publish.yml.
HARD_TESTS=".claude/scripts/tests/test_release_workflow_asserts.py
.claude/scripts/tests/test_install_sh_self_sha.py
.claude/scripts/tests/test_await_release_gate.py
.claude/scripts/tests/test_release_bump_sites.py"
# O patch dormente de rollback (PLAN-158 W1): NÃO rastreado, só no checkout vivo; pinado por tamanho e
# sha256 (medidos em 2026-10-09 no checkout vivo do Owner).
ROLLBACK_REL=.claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch
ROLLBACK="$ROOT/$ROLLBACK_REL"
ROLLBACK_SIZE=537
ROLLBACK_SHA=e68a508c86ebe2ac6c2eac444530934e4aa91fe05186f98b6a490d391a845b6a
# As duas formas do actionlint no CI: a do job validate (validate.yml) e a do actionlint.yml.
AL_SC_FLAGS="-S error -e SC2002,SC2012,SC2016,SC2129"
RAIL_MAX_ROUNDS=3
APPLIED=0
SENT_TOUCHED=0
SIGN_STARTED=0
P0_CLEAN=0
BASE_WT=""
CTRL_WT=""
BAK=$(mktemp -d "${TMPDIR:-/tmp}/w4-sign.XXXXXX")
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
patch_blobs() {  # arquivo de saída — uma linha "<caminho> <blob pré-imagem> <blob pós-imagem>" por caminho do patch
  awk '/^diff --git /{p=$3; sub(/^a\//, "", p)} /^index /{split($2, h, /\.\./); print p, h[1], h[2]}' "$PATCH" > "$1"
}
pt_summary() {  # log — a linha de resumo do pytest (a última com « in <n>s»), sem as cercas de «=»
  awk '/ in [0-9.]+s/ {l = $0} END {print l}' "$1" | sed -E 's/^=+ //; s/ =+$//'
}

if [ -n "$CHECK_BASE" ]; then
  # Só leitura: nada é aplicado, nada é escrito na árvore. Para conferir, ANTES de qualquer land que
  # toque um caminho do patch, se os bytes da base ainda são os que este pacote pinou.
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
    printf '\nFAIL: a base pinada da W4 não é a de %s — o w4.patch não aplica ali. Re-derivar o\n' "$CHECK_BASE" >&2
    printf 'pacote pede rail sobre o patch novo; não lande bytes diferentes nesses caminhos sem isso.\n' >&2
    exit 1
  fi
  printf '\nOK: a base pinada da W4 é a de %s (o w4.patch aplica ali).\n' "$CHECK_BASE"
  exit 0
fi
remove_wt() {  # caminho — remove um worktree deste script
  if [ -d "$1" ]; then
    git worktree remove --force "$1" >/dev/null 2>&1 \
      || printf 'remova à mão: git worktree remove --force %s\n' "$1" >&2
  fi
  git worktree prune >/dev/null 2>&1 || :
}
remove_base_wt() {
  if [ -n "$BASE_WT" ]; then
    remove_wt "$BASE_WT"
    BASE_WT=""
  fi
}
remove_ctrl_wt() {
  if [ -n "$CTRL_WT" ]; then
    remove_wt "$CTRL_WT"
    CTRL_WT=""
  fi
}
undo() {
  set +e
  local done_what=""
  remove_ctrl_wt
  remove_base_wt
  if [ "$APPLIED" = "1" ]; then
    git reset -q HEAD -- . 2>/dev/null
    if git apply -R --check "$PATCH" 2>/dev/null; then
      if git apply -R "$PATCH"; then
        done_what="$done_what patch-revertido"
      else
        done_what="$done_what PATCH-NAO-REVERTIDO"
      fi
    else
      done_what="$done_what PATCH-NAO-REVERTIDO"
    fi
    # Um caminho tocado que mudou depois do apply fica diferente do HEAD: se a mudança toca o contexto
    # de um hunk, o `git apply -R` (atômico) recusa e nada é revertido; se cai fora, a reversão passa e
    # a mudança fica. O P0 exigiu árvore rastreada limpa, então a pré-imagem é o HEAD; quem descarta é
    # você.
    if ! xargs git diff --quiet HEAD -- < "$BAK/touched" 2>/dev/null; then
      printf 'caminhos do patch ainda diferem do HEAD (mudaram depois do apply). Confira com «git diff» e\n' >&2
      printf 'restaure a pré-imagem com: git checkout HEAD -- %s\n' "$(tr '\n' ' ' < "$BAK/touched")" >&2
      done_what="$done_what CAMINHOS-DO-PATCH-AINDA-SUJOS"
    fi
    APPLIED=0
  fi
  if [ "$SENT_TOUCHED" = "1" ] && [ "$DRY" != "1" ]; then
    git reset -q HEAD -- "$SENT_REPO" 2>/dev/null
    if [ -L "$SENT_REPO" ]; then
      printf 'sentinel virou symlink — restaure à mão a partir de %s/sentinel.head.md\n' "$BAK" >&2; done_what="$done_what SENTINEL-NAO-RESTAURADO"
    else
      cp "$BAK/sentinel.head.md" "$SENT_REPO"; done_what="$done_what sentinel-restaurado"
    fi
    SENT_TOUCHED=0
  fi
  if [ "$SIGN_STARTED" = "1" ] && [ "$DRY" != "1" ]; then
    git reset -q HEAD -- "$ASC" 2>/dev/null
    if [ -f "$ASC" ]; then rm -- "$ASC"; done_what="$done_what asc-removida"; fi
    SIGN_STARTED=0
  fi
  printf '\ndesfeito:%s\n' "${done_what:- nada a desfazer}" >&2
}
list_leftovers() {  # depois do desfazer: o que mudou durante ESTA execução e ficou diferente do HEAD
  [ "$P0_CLEAN" = "1" ] || return 0
  git diff --name-only --no-renames HEAD -- > "$BAK/leftover" 2>/dev/null || return 0
  [ -s "$BAK/leftover" ] || return 0
  printf '\nATENÇÃO: arquivos rastreados que mudaram durante esta execução e o desfazer NÃO restaurou\n' >&2
  printf '(a bateria ou outro processo os escreveu; confira com «git diff» antes de descartar):\n' >&2
  sed 's/^/   /' "$BAK/leftover" >&2
  printf 'para restaurar: git checkout HEAD -- %s\n' "$(tr '\n' ' ' < "$BAK/leftover")" >&2
}
# A chave de assinatura e a conferência do signatário usam o allowlist commitado e a biblioteca de
# verificação do próprio repositório (_lib/gpg_verify.py: GOODSIG + VALIDSIG, impressão digital no
# allowlist):
#   signer_tool pick                     -> imprime a impressão digital da chave SECRETA a usar
#   signer_tool verify <arquivo> <.asc>  -> imprime a impressão digital aceita
signer_tool() {
  python3 - "$BAK/gpg_verify.head.py" "$BAK/signers.head" "$@" <<'PY'
import importlib.util
import subprocess
import sys
from pathlib import Path

glib, allow, mode = sys.argv[1:4]
rest = sys.argv[4:]
spec = importlib.util.spec_from_file_location("gpg_verify_w4", glib)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
if mode == "pick":
    fprs, err = g.load_allowlist(Path(allow))
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
    ok, fpr, reason = g.verify_detached(Path(rest[0]), Path(rest[1]), allowlist_path=Path(allow))
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
  undo
  list_leftovers
  [ "$rc" -ne 0 ] || rc=1
  printf '(rc=%s) abortado; logs em %s; árvore conferível com: git status --short\n' "$rc" "$BAK" >&2
  exit "$rc"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

say "P0 pré-condições"
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo (rode num terminal, não por pipe)"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
git remote -v | grep -q 'Canhada-Labs/ceo-orchestration' || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
git merge-base --is-ancestor origin/main HEAD || die "HEAD não contém origin/main (atrás ou divergente) — puxe antes"
AHEAD=$(git rev-list --count origin/main..HEAD)
# Um worktree do controle ou da base que uma execução anterior INTERROMPIDA (kill -9, queda) deixou é
# deste script (um diretório w4-sign.*/ctrl-wt ou w4-sign.*/base-wt que só ele cria): removido antes
# de começar.
git worktree list --porcelain | awk '/^worktree /{print substr($0, 10)}' > "$BAK/worktrees"
while IFS= read -r wt; do
  case "$wt" in
    */w4-sign.*/base-wt|*/w4-sign.*/ctrl-wt)
      printf '   removendo o worktree de uma execução anterior interrompida: %s\n' "$wt"
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
  printf 'e, para um arquivo que a bateria de uma execução interrompida sujou: git checkout HEAD -- <arquivo>\n' >&2
  die "há modificação RASTREADA pendente"
fi
P0_CLEAN=1
[ ! -e "$ASC" ] || die "já existe $ASC — remova a assinatura antiga antes (rm $ASC)"
for f in "$SENT" "$PATCH" "$ORACLE" "$SELF" "$SIGNERS" "$GPG_VERIFY_LIB"; do [ -f "$f" ] || die "ausente: $f"; done
for t in $CANON; do [ -f "$STAGED_DIR/$t" ] || die "ausente: $STAGED_DIR/$t"; done
for f in "$SENT" "$PATCH" "$SELF" "$SIGNERS" "$GPG_VERIFY_LIB"; do
  git ls-files --error-unmatch -- "$f" >/dev/null 2>&1 || die "$f não está commitado — lande os materiais do pacote (commit livre) antes"
done
for t in $CANON; do
  git ls-files --error-unmatch -- "$STAGED_DIR/$t" >/dev/null 2>&1 || die "$STAGED_DIR/$t não está commitado — lande os materiais do pacote (commit livre) antes"
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
command -v actionlint >/dev/null 2>&1 || die "actionlint ausente do PATH — este pacote muda workflow e a bateria o exige (brew install actionlint)"
command -v shellcheck >/dev/null 2>&1 || die "shellcheck ausente do PATH — a regra shellcheck do actionlint e a forma do actionlint.yml o exigem (brew install shellcheck)"
command -v gpg >/dev/null 2>&1 || die "gpg ausente"
# A chave é escolhida ANTES da bateria (também no --dry-run): sem chave do allowlist, a falha vem
# agora, não depois de 20 minutos.
# A biblioteca de verificação e o allowlist vêm do HEAD (a árvore está limpa agora), não da árvore
# viva que a bateria pode sujar: a escolha da chave e as duas verificações usam estas cópias.
git show "HEAD:$GPG_VERIFY_LIB" > "$BAK/gpg_verify.head.py" || die "não consegui ler HEAD:$GPG_VERIFY_LIB"
git show "HEAD:$SIGNERS" > "$BAK/signers.head" || die "não consegui ler HEAD:$SIGNERS"
SIGN_KEY=$(signer_tool pick) || die "sem chave secreta do allowlist $SIGNERS neste GNUPGHOME"
if [ "$DRY" != "1" ]; then
  GPG_TTY=$(tty) || die "não consegui ler o terminal (tty) para o GPG_TTY"
  export GPG_TTY
fi
python3 -m pytest --version >/dev/null 2>&1 || die "pytest ausente (python3 -m pip install 'pytest==8.*')"
python3 -c 'import xdist' >/dev/null 2>&1 || die "pytest-xdist ausente (python3 -m pip install pytest-xdist) — as suítes rodam como no CI"
python3 -c 'import yaml' >/dev/null 2>&1 || die "PyYAML ausente (python3 -m pip install pyyaml) — sem ele a lane YAML do controle da W4 PULA e o controle não prova o que declara"
# Forma do patch: só MODIFICAÇÃO de conteúdo de arquivo existente, sem criar, remover, renomear,
# copiar ou mudar modo — qualquer outra forma é recusada com nome (não por acidente de outra conferência).
if grep -nE '^(rename|copy) (from|to) |^(deleted|new) file mode |^(old|new) mode |^similarity index |^GIT binary patch' "$PATCH" > "$BAK/patch-shape" 2>/dev/null; then
  sed 's/^/   /' "$BAK/patch-shape" >&2
  die "o patch cria, remove, renomeia ou copia arquivo, ou muda modo — este SIGN só landa modificação de conteúdo"
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
# As duas formas do conteúdo novo de CADA canônico são o MESMO conteúdo: o blob da cópia staged = o
# pós-imagem do patch para esse caminho.
for t in $CANON; do
  sb=$(git hash-object -- "$STAGED_DIR/$t")
  pb=$(awk -v t="$t" '$1 == t {print $3}' "$BAK/blobs")
  [ -n "$pb" ] || die "o patch não toca $t"
  [ "$sb" = "$pb" ] || die "a cópia staged ($STAGED_DIR/$t, blob $sb) não é o pós-imagem do patch para $t ($pb) — as duas formas divergem"
done
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
# shellcheck disable=SC2046  # a lista de caminhos vira argumentos do printf de propósito (sem espaço nos caminhos)
sort -u "$BAK/canon-now" | cmp -s - "$BAK/canon-expected" \
  || die "os caminhos canônicos que o patch toca ≠ os declarados:$(printf '\n   %s' $(comm -3 "$BAK/canon-expected" "$BAK/canon-now"))"
# O texto assinável é o do HEAD (a árvore está limpa: o arquivo vivo é o mesmo agora). Tudo que se
# lê dele daqui em diante vem dessa cópia.
git show "HEAD:$SENT" > "$BAK/sentinel.head.md" || die "não consegui ler HEAD:$SENT"
SENT_HEAD_SHA=$(shasum -a 256 "$BAK/sentinel.head.md" | awk '{print $1}')
awk '/^## Scope/{s=1; next} /^## /{s=0} s && /^- `/{sub(/^- `/, ""); sub(/`.*/, ""); print}' "$BAK/sentinel.head.md" | sort -u > "$BAK/scope"
DIFF=$(comm -3 "$BAK/touched" "$BAK/scope")
[ -z "$DIFF" ] || die "touched ≠ Scope do sentinel:$(printf '\n   %s' $DIFF)"
# O patch dormente de rollback: arquivo regular, NÃO rastreado por desenho, com tamanho e sha256 pinados;
# precisa aplicar no HEAD agora (e com o patch, na bateria).
[ -e "$ROLLBACK" ] || die "o patch dormente de rollback está ausente: $ROLLBACK — ele não é rastreado (.gitignore staged/) e vive só no checkout vivo; rode o SIGN no checkout que o tem"
[ -f "$ROLLBACK" ] && [ ! -L "$ROLLBACK" ] || die "o patch dormente de rollback não é arquivo regular: $ROLLBACK"
RB_SIZE=$(wc -c < "$ROLLBACK" | tr -d ' ')
RB_SHA=$(shasum -a 256 "$ROLLBACK" | awk '{print $1}')
[ "$RB_SIZE" = "$ROLLBACK_SIZE" ] && [ "$RB_SHA" = "$ROLLBACK_SHA" ] \
  || die "o patch dormente de rollback não é o pinado ($ROLLBACK: $RB_SIZE bytes, sha256 $RB_SHA; o pacote pinou $ROLLBACK_SIZE bytes, sha256 $ROLLBACK_SHA)"
git apply --check "$ROLLBACK" >"$BAK/rollback-head.out" 2>&1 \
  || { sed 's/^/   /' "$BAK/rollback-head.out" >&2; die "o patch dormente de rollback não aplica no HEAD ($ROLLBACK)"; }
# O controle vermelho→verde só vale se discrimina: a classe FINAL (do patch), contra os canônicos do
# HEAD, REPROVA — num worktree destacado do HEAD com só a parte livre do patch.
CTRL_WT="$BAK/ctrl-wt"
git worktree add --quiet --detach "$CTRL_WT" HEAD >/dev/null 2>&1 || die "não consegui criar o worktree do controle em $CTRL_WT"
EXCL=""
for t in $CANON; do EXCL="$EXCL --exclude=$t"; done
# shellcheck disable=SC2086
(cd "$CTRL_WT" && git apply $EXCL "$ROOT/$PATCH") >"$BAK/ctrl-apply.out" 2>&1 \
  || { sed 's/^/   /' "$BAK/ctrl-apply.out" >&2; die "a parte livre do patch não aplica no worktree do controle"; }
(cd "$CTRL_WT" && git diff --name-only --no-renames HEAD --) | sort -u > "$BAK/ctrl-touched"
# shellcheck disable=SC2046  # a lista de caminhos vira argumentos do printf de propósito (sem espaço nos caminhos)
comm -23 "$BAK/touched" "$BAK/canon-expected" | cmp -s - "$BAK/ctrl-touched" \
  || die "o worktree do controle não recebeu exatamente a parte livre do patch:$(printf '\n   %s' $(comm -3 "$BAK/ctrl-touched" "$BAK/touched"))"
set +e
(cd "$CTRL_WT" && python3 -m pytest "$CTRL_FILE::$CTRL_CLASS" -q -rfE --tb=no -p no:cacheprovider) > "$BAK/ctrl-head.out" 2>&1
CTRL_HEAD_RC=$?
set -e
remove_ctrl_wt
CTRL_HEAD_SUM=$(pt_summary "$BAK/ctrl-head.out")
CTRL_HEAD_FAILS=$(grep -c "^FAILED $CTRL_FILE::$CTRL_CLASS::" "$BAK/ctrl-head.out" || :)
# rc 1 E o resumo do pytest começando por exatamente $CTRL_N falhas, sem passed/skipped/error, E as
# $CTRL_N linhas FAILED da classe (uma coleta quebrada sai rc 2; um skip geral sai rc 0).
if [ "$CTRL_HEAD_RC" != "1" ] || ! printf '%s\n' "$CTRL_HEAD_SUM" | grep -Eq "^$CTRL_N failed(,| in )" \
   || printf '%s\n' "$CTRL_HEAD_SUM" | grep -Eq 'passed|skipped|error|xfailed|xpassed' \
   || [ "$CTRL_HEAD_FAILS" != "$CTRL_N" ]; then
  tail -8 "$BAK/ctrl-head.out" >&2
  die "o controle da W4 ($CTRL_CLASS contra os canônicos do HEAD) não reprova como deve (rc=$CTRL_HEAD_RC, resumo '$CTRL_HEAD_SUM', $CTRL_HEAD_FAILS linha(s) FAILED da classe; esperado rc 1 com exatamente $CTRL_N falhas e nada mais) — ou o HEAD já tem a W4, ou o controle não discrimina"
fi
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
git diff --quiet HEAD -- "$REC" || die "$REC difere do HEAD"
field() { awk -v k="$1" 'index($0, k ": ") == 1 {v = substr($0, length(k) + 3); n++} END {if (n != 1) exit 3; print v}' "$REC"; }
R_ROUND=$(field Rail-Round) || die "$REC: linha Rail-Round ausente ou repetida"
R_SUBJ=$(field Rail-Subject-sha256) || die "$REC: linha Rail-Subject-sha256 ausente ou repetida"
R_SENT=$(field Rail-Sentinel-sha256) || die "$REC: linha Rail-Sentinel-sha256 ausente ou repetida"
R_REV=$(field Rail-Reviewer-Verdict) || die "$REC: linha Rail-Reviewer-Verdict ausente ou repetida"
R_VERD=$(field Rail-Verdict) || die "$REC: linha Rail-Verdict ausente ou repetida"
R_FIND=$(field Rail-Findings) || die "$REC: linha Rail-Findings ausente ou repetida"
[ "$R_ROUND" = "$LAST" ] || die "$REC declara Rail-Round '$R_ROUND'"
[ "$R_SUBJ" = "$PATCH_SHA" ] || die "o último registro do rail ($REC) revisou outro patch ($R_SUBJ), não este ($PATCH_SHA)"
[ "$R_SENT" = "$SENT_HEAD_SHA" ] || die "o último registro do rail ($REC) está preso a outro texto assinável ($R_SENT), não ao sentinel do HEAD ($SENT_HEAD_SHA)"
# A linha VERDICT literal do revisor. Gramática do registro (a mesma da W1 e da W3b.1):
#   - exatamente UMA linha igual a «## Saída do revisor»;
#   - nessa seção, exatamente UM bloco verbatim: abre com uma linha IGUAL a «```text» e fecha com a
#     próxima linha IGUAL a «```»; o bloco é lido INTEIRO até o fechamento, e nada dentro dele
#     (título «## …», prosa) encerra a seção;
#   - dentro do bloco, nenhuma OUTRA linha pode ser cerca — uma linha que, sem os espaços e tabs
#     iniciais, começa com ``` (indentar NÃO é rota: quem copia a saída do revisor troca as crases
#     dessas linhas e declara a troca na triagem); fora do bloco, na seção, idem;
#   - o veredito é a ÚLTIMA linha do bloco que começa com «VERDICT: », e o valor é GO,
#     GO-WITH-CONDITIONS ou NO-GO;
#   - seção ausente ou repetida, cerca ausente, duplicada, mal formada (inclusive indentada) ou não
#     fechada, ou bloco sem linha VERDICT: o registro é RECUSADO.
LAST_VERDICT=$(awk '
  # estado: 0 antes da seção; 1 na seção, antes do bloco; 2 dentro do bloco; 3 bloco fechado; 4 depois
  { s = $0; sub(/^[ \t]+/, "", s) }
  state == 2 {
    if ($0 == "```") { state = 3; next }
    if (s ~ /^```/) { bad = "linha de cerca mal formada DENTRO do bloco verbatim"; exit }
    if ($0 ~ /^VERDICT: /) v = substr($0, 10)
    next
  }
  $0 == "## Saída do revisor" { sec++; if (state == 0) state = 1; next }
  (state == 1 || state == 3) && /^## / { state = 4; next }
  state == 1 && s ~ /^```/ {
    if ($0 == "```text") { state = 2; blocks++; next }
    bad = "abertura de cerca mal formada (esperado uma linha igual a ```text)"; exit
  }
  state == 3 && s ~ /^```/ { bad = "segunda cerca na seção (bloco verbatim duplicado ou fechado antes da hora)"; exit }
  END {
    if (bad != "") { print bad; exit 3 }
    if (sec != 1) { print "seção «## Saída do revisor» ausente ou repetida"; exit 3 }
    if (state == 2) { print "bloco verbatim não fechado (falta a linha ```)"; exit 3 }
    if (blocks != 1) { print "seção sem bloco verbatim (```text … ```)"; exit 3 }
    if (v == "") { print "bloco verbatim sem linha VERDICT"; exit 3 }
    print v
  }' "$REC") || die "$REC: registro recusado — $LAST_VERDICT"
case "$LAST_VERDICT" in
  GO|GO-WITH-CONDITIONS|NO-GO) : ;;
  *) die "$REC: a última linha VERDICT do bloco verbatim tem valor inválido '$LAST_VERDICT'" ;;
esac
[ "$LAST_VERDICT" = "$R_REV" ] || die "$REC: Rail-Reviewer-Verdict '$R_REV' ≠ a última linha VERDICT do revisor '$LAST_VERDICT'"
case "$R_VERD" in
  APPROVE)
    [ "$R_REV" = "GO" ] || die "APPROVE exige o revisor em GO (o registro diz '$R_REV')"
    [ "$R_FIND" = "P0=0 P1=0 P2=0" ] || die "APPROVE exige 'P0=0 P1=0 P2=0' (o registro diz '$R_FIND')" ;;
  DECLARED-P2)
    case "$R_REV" in
      GO|GO-WITH-CONDITIONS) : ;;
      *) die "DECLARED-P2 exige o revisor em GO ou GO-WITH-CONDITIONS (o registro diz '$R_REV')" ;;
    esac
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
printf '       %s caminho(s) = Scope, canônicos = os declarados (%s), cópias staged = pós-imagem, materiais commitados,\n' \
  "$(wc -l < "$BAK/touched" | tr -d ' ')" "$(wc -l < "$BAK/canon-expected" | tr -d ' ')"
printf '       patch dormente de rollback = o pinado e aplica no HEAD, controle da W4 reprova no HEAD (como deve: %s)\n' "$CTRL_HEAD_SUM"
printf '   chave de assinatura (em %s): %s\n' "$SIGNERS" "$SIGN_KEY"
printf '   rail: %s = %s (%s; revisor %s), sobre Patch-sha256 %s,\n' "$REC" "$R_VERD" "$R_FIND" "$R_REV" "$PATCH_SHA"
printf '         sentinel %s\n' "$SENT_HEAD_SHA"

say "1/7 aplicar o patch"
git apply "$PATCH" || die "git apply falhou"
APPLIED=1

say "2/7 bytes aplicados = bytes revisados"
while read -r p old new; do
  now=$(git hash-object -- "$p")
  [ "$now" = "$new" ] || die "$p depois do apply tem o blob $now; o patch revisado declara $new"
done < "$BAK/blobs"
for t in $CANON; do
  cmp -s "$STAGED_DIR/$t" "$t" || die "o canônico aplicado $t difere da cópia staged $STAGED_DIR/$t"
done
printf '   %s blob(s) conferido(s) contra o index pós-imagem do patch (os canônicos = as cópias staged)\n' "$(wc -l < "$BAK/blobs" | tr -d ' ')"

say "3/7 bateria (passadas duras do pacote, actionlint, gates de corpus + suítes do pytest.ini julgadas contra a árvore sem o patch)"
NOTES=""
ensure_base_wt() {  # a árvore SEM o patch: worktree destacado do HEAD, criado uma vez, removido no fim
  if [ -z "$BASE_WT" ]; then
    BASE_WT="$BAK/base-wt"
    git worktree add --quiet --detach "$BASE_WT" HEAD >/dev/null 2>&1 || die "não consegui criar o worktree da base em $BASE_WT"
  fi
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
findings() {  # tipo log — o MULTICONJUNTO normalizado dos achados (ordenado, com repetições)
  case "$1" in
    actionlint)  # arquivo:linha:coluna: mensagem [regra] → arquivo: mensagem [regra] (o patch desloca linhas)
      sed -E -n 's/^([^:]+):[0-9]+:[0-9]+: (.*)$/\1: \2/p' "$2" | LC_ALL=C sort ;;
    governance)  # TODA linha da saída (cabeçalho, DETALHE de cada violação, contagem), fora as linhas
      # de AVISO do produtor — pelo PREFIXO diagnóstico com que o validate-governance as emite
      # («  WARN: », «  WARNING: », «    WARN (grandfathered): », «  V<n> WARN [», «  Warnings: »),
      # nunca por substring: um detalhe de erro que contenha «WARN» fica — e fora a linha «Repo:»
      # (o único texto que muda entre a árvore viva e o worktree da base); espaços normalizados. Sem
      # normalização de caminho: com a base vermelha, um detalhe que traga o caminho absoluto da árvore
      # difere entre as duas e reprova por ruído (falha FECHADA).
      awk '!/^  WARN: / && !/^  WARNING: / && !/^    WARN \(grandfathered\): / && !/^  V[0-9]+ WARN \[/ && !/^  Warnings: / && !/^Repo: / {gsub(/[[:space:]]+/, " "); print}' "$2" | LC_ALL=C sort ;;
    *) die "findings: tipo desconhecido '$1'" ;;
  esac
}
passes() {  # tipo rc log — o gate passou?
  [ "$2" = "0" ] || return 1
  case "$1" in
    governance) grep -q 'Errors:   0' "$3" ;;
    *) return 0 ;;
  esac
}
gate_set() {  # rótulo tipo comando... — julgado pelo conjunto de achados, não só pelo rc
  local label="$1" kind="$2" rc_p=0 rc_b=0
  shift 2
  "$@" >"$BAK/gs.out" 2>&1 || rc_p=$?
  if passes "$kind" "$rc_p" "$BAK/gs.out"; then printf '   ok: %s\n' "$label"; return 0; fi
  cp "$BAK/gs.out" "$BAK/gate-set-fail.out"
  ensure_base_wt
  (cd "$BASE_WT" && "$@") >"$BAK/gs-base.out" 2>&1 || rc_b=$?
  if passes "$kind" "$rc_b" "$BAK/gs-base.out"; then
    tail -12 "$BAK/gate-set-fail.out" >&2
    die "$label reprovou com o patch e passa sem ele (log: $BAK/gate-set-fail.out)"
  fi
  # Uma execução que não chegou a julgar (actionlint com rc fora de 0/1; governance sem a linha
  # «Errors:») nunca é «pré-existente»: reprova.
  case "$kind" in
    actionlint)
      case "$rc_p$rc_b" in 00|01|10|11) : ;; *) die "$label não chegou a lintar (rc com o patch $rc_p, sem $rc_b) — logs: $BAK/gate-set-fail.out, $BAK/gs-base.out" ;; esac ;;
    governance)
      grep -q 'Errors:' "$BAK/gate-set-fail.out" && grep -q 'Errors:' "$BAK/gs-base.out" \
        || die "$label não chegou ao resumo 'Errors:' numa das árvores — logs: $BAK/gate-set-fail.out, $BAK/gs-base.out" ;;
  esac
  findings "$kind" "$BAK/gate-set-fail.out" > "$BAK/gs-f-patch"
  findings "$kind" "$BAK/gs-base.out" > "$BAK/gs-f-base"
  [ -s "$BAK/gs-f-patch" ] || die "$label reprovou com o patch sem nenhum achado legível (log: $BAK/gate-set-fail.out)"
  LC_ALL=C comm -23 "$BAK/gs-f-patch" "$BAK/gs-f-base" > "$BAK/gs-f-new"
  if [ -s "$BAK/gs-f-new" ]; then
    sed 's/^/   NOVO: /' "$BAK/gs-f-new" >&2
    die "$label: achado(s) que só existe(m) com o patch (a base também reprova, mas por outros achados; logs: $BAK/gate-set-fail.out, $BAK/gs-base.out)"
  fi
  printf '   PRÉ-EXISTENTE (mesmo conjunto de achados com e sem o patch): %s (log: %s)\n' "$label" "$BAK/gs-base.out"
  NOTES="$NOTES
   - $label"
}
gov_run() { bash .claude/scripts/validate-governance.sh; }
judge_fails() {  # julga os ids em now-fails: isolado com o patch; se falhar de novo, na árvore sem o patch
  sort -u "$BAK/now-fails" > "$BAK/now-fails.sorted"
  : > "$BAK/now-fails"
  : > "$BAK/real-new-fails"
  local test_id brc tries passed
  while IFS= read -r test_id; do
    [ -n "$test_id" ] || continue
    # até 3 reruns isolados com o patch: um teste sensível a tempo pode falhar de novo numa máquina
    # carregada (medido no molde: o de orçamento de 0,6 s do git falso falhou 2x seguidas)
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
# shellcheck disable=SC2086
python3 -m py_compile $HARD_TESTS || die "py_compile"
# As passadas DURAS do pacote: com o patch, rc != 0 reprova — sem julgamento de pré-existente.
# (a) o controle da W4, verde com o patch: rc 0 e exatamente $CTRL_N passed, nada mais.
set +e
python3 -m pytest "$CTRL_FILE::$CTRL_CLASS" -q -rfE --tb=short -p no:cacheprovider >"$BAK/ctrl-applied.out" 2>&1
CTRL_APPLIED_RC=$?
set -e
CTRL_APPLIED_SUM=$(pt_summary "$BAK/ctrl-applied.out")
if [ "$CTRL_APPLIED_RC" != "0" ] || ! printf '%s\n' "$CTRL_APPLIED_SUM" | grep -Eq "^$CTRL_N passed(,| in )" \
   || printf '%s\n' "$CTRL_APPLIED_SUM" | grep -Eq 'failed|skipped|error|xfailed|xpassed'; then
  tail -15 "$BAK/ctrl-applied.out" >&2
  die "o controle da W4 não sai verde com o patch (rc=$CTRL_APPLIED_RC, resumo '$CTRL_APPLIED_SUM'; esperado rc 0 com exatamente $CTRL_N passed e nada mais; log: $BAK/ctrl-applied.out)"
fi
printf '   ok: controle da W4 (vermelho no HEAD, verde com o patch: %s)\n' "$CTRL_APPLIED_SUM"
# (b) os 4 arquivos de teste que leem o npm-publish.yml.
# shellcheck disable=SC2086
python3 -m pytest $HARD_TESTS -q -rfE --tb=short -p no:cacheprovider >"$BAK/suite-hard.out" 2>&1 \
  || { tail -15 "$BAK/suite-hard.out" >&2; die "os testes que leem o npm-publish.yml não passam com o patch (passada dura; log: $BAK/suite-hard.out)"; }
printf '   ok: testes que leem o npm-publish.yml (%s)\n' "$(pt_summary "$BAK/suite-hard.out")"
# (c) actionlint no workflow do pacote. Sonda positiva primeiro: com o shellcheck no PATH a regra
# precisa EXECUTAR (sem ele o actionlint sai rc 0 em silêncio). Um workflow mínimo com um SC conhecido
# tem de produzir um achado [shellcheck].
printf '   actionlint local: %s; shellcheck: %s\n' "$(actionlint -version 2>/dev/null | awk 'NR == 1')" \
  "$(shellcheck --version 2>/dev/null | awk '/^version:/{print $2}')"
printf 'name: sonda\non: [push]\njobs:\n  a:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo $sonda_sem_aspas\n' > "$BAK/al-probe.yml"
actionlint -no-color "$BAK/al-probe.yml" > "$BAK/al-probe.out" 2>&1 || :
grep -q '\[shellcheck\]' "$BAK/al-probe.out" \
  || die "a regra shellcheck do actionlint não executou na sonda (log: $BAK/al-probe.out) — o actionlint do pacote não seria o que declara"
printf '   ok: sonda da regra shellcheck do actionlint (achado [shellcheck] na sonda)\n'
actionlint "$WORKFLOW" >"$BAK/al-workflow.out" 2>&1 \
  || { tail -15 "$BAK/al-workflow.out" >&2; die "actionlint $WORKFLOW não saiu 0 com o patch (passada dura; log: $BAK/al-workflow.out)"; }
printf '   ok: actionlint %s\n' "$WORKFLOW"
# (d) o patch dormente de rollback segue aplicável sobre o workflow novo (bytes conferidos de novo).
[ "$(shasum -a 256 "$ROLLBACK" | awk '{print $1}')" = "$ROLLBACK_SHA" ] \
  || die "o patch dormente de rollback mudou durante a execução ($ROLLBACK)"
git apply --check "$ROLLBACK" >"$BAK/rollback-applied.out" 2>&1 \
  || { sed 's/^/   /' "$BAK/rollback-applied.out" >&2; die "o patch dormente de rollback não aplica com o patch (passada dura; $ROLLBACK)"; }
printf '   ok: o patch dormente de rollback aplica sobre o workflow novo (git apply --check)\n'
# actionlint nas duas formas do CI, sobre todos os workflows, julgadas pelo conjunto de achados. A do
# job validate passa as flags do shellcheck em -shellcheck, o que (medido no 1.7.12, -verbose) DESLIGA
# a regra shellcheck; a do actionlint.yml a mantém.
gate_set "actionlint (forma do job validate)" actionlint actionlint -no-color -config-file .github/actionlint.yaml \
  -shellcheck="$AL_SC_FLAGS" .github/workflows/*.yml
gate_set "actionlint (forma do actionlint.yml)" actionlint actionlint -no-color -config-file .github/actionlint.yaml \
  .github/workflows/*.yml
gate "test-env-hygiene" python3 .claude/scripts/check-test-env-hygiene.py
gate "inventário de variáveis de ambiente" python3 .claude/scripts/env-inventory-check.py --check
gate "hooks ativos executáveis" python3 .claude/scripts/check-active-hooks-executable.py
gate "contamination" bash .claude/scripts/check-contamination.sh
gate "build-plugin --check" python3 scripts/build-plugin.py --check
gate "mapa comando→skill→hook" python3 .claude/scripts/gen-command-skill-hook-map.py --check
gate "docs-freshness" python3 .claude/scripts/check-docs-freshness.py --format=text
gate "verify-counts" bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
gate "claims do CLAUDE.md" python3 .claude/scripts/check-claude-md-claims.py
gate "ceremony-lint" python3 .claude/scripts/check-ceremony-script.py
gate_set "validate-governance (Errors: 0)" governance gov_run
: > "$BAK/now-fails"
printf '   suítes do pytest.ini com a divisão de marcadores do CI (paralela e serial)\n'
run_pass "passada paralela" "$BAK/suite-parallel.out" -n auto -m 'not serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider
run_pass "passada serial" "$BAK/suite-serial.out" -m 'serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider
judge_fails
remove_base_wt
printf '   bateria: nenhuma falha nova em relação à árvore sem o patch\n'
if [ -n "$NOTES" ]; then
  printf '   ATENÇÃO — vermelhos PRÉ-EXISTENTES (reprovam também sem este patch; não bloqueiam este land):%s\n' "$NOTES"
fi
# Depois da bateria (longa): o HEAD, os bytes a landar e o texto a assinar precisam ser os de antes dela.
[ "$(git rev-parse HEAD)" = "$HEAD_SHA" ] \
  || die "o HEAD mudou durante a bateria (era $HEAD_SHA) — o Anchor-SHA não seria o pai do commit; rode de novo sobre o HEAD atual"
while read -r p old new; do
  now=$(git hash-object -- "$p")
  [ "$now" = "$new" ] || die "$p mudou durante a bateria (blob $now; o patch revisado declara $new) — os bytes a landar deixaram de ser os revisados"
done < "$BAK/blobs"
[ ! -L "$SENT" ] || die "o sentinel virou symlink durante a bateria"
git diff --quiet HEAD -- "$SENT" \
  || die "o sentinel mudou durante a bateria — o texto a assinar deixou de ser o do HEAD (o que o rail revisou); restaure com: git checkout HEAD -- $SENT"
# Arquivos rastreados FORA do patch e do sentinel modificados durante a execução (um teste que
# escreve na árvore, ou outro processo): não entram no commit (o stage é exato), mas deixam a árvore
# suja — aviso no fim.
git diff --name-only --no-renames HEAD -- | sort -u > "$BAK/dirty-now"
comm -23 "$BAK/dirty-now" "$BAK/touched" > "$BAK/dirty-other"
if [ -s "$BAK/dirty-other" ]; then
  printf '   AVISO: arquivos rastreados fora do patch mudaram durante a bateria (não entram no commit):\n'
  sed 's/^/     /' "$BAK/dirty-other"
fi

say "4/7 sentinel do HEAD preenchido: Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data"
python3 - "$BAK/sentinel.head.md" "$BAK/sentinel.filled.md" "$HEAD_SHA" "$PATCH_SHA" "$RAIL_SHA" "$(date -u +%Y-%m-%d)" <<'PY'
import pathlib
import re
import sys

# Leitura e escrita SEM tradução de fim de linha (newline=""): fora das 4 linhas de campo, o texto
# assinado é byte a byte o do HEAD.
with open(sys.argv[1], encoding="utf-8", newline="") as fh:
    t = fh.read()
for key, val in (("Anchor-SHA", sys.argv[3]), ("Patch-sha256", sys.argv[4]),
                 ("Rail-Record-sha256", sys.argv[5]), ("Data", sys.argv[6])):
    t2, n = re.subn(r"^%s: TO-FILL-BY-SIGN$" % re.escape(key), "%s: %s" % (key, val), t, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("linha %s: TO-FILL-BY-SIGN não encontrada" % key)
    t = t2
if "TO-FILL-BY-SIGN" in t:
    raise SystemExit("sobrou TO-FILL-BY-SIGN no sentinel")
with open(sys.argv[2], "w", encoding="utf-8", newline="") as fh:
    fh.write(t)
PY
for kv in "Anchor-SHA: $HEAD_SHA" "Patch-sha256: $PATCH_SHA" "Rail-Record-sha256: $RAIL_SHA"; do
  awk -v l="$kv" '$0 == l {n++} END {exit n == 1 ? 0 : 1}' "$BAK/sentinel.filled.md" || die "o campo '$kv' não gravou no sentinel"
done
FILLED_BLOB=$(git hash-object -- "$BAK/sentinel.filled.md")
if [ "$DRY" = "1" ]; then
  SENT="$BAK/sentinel.filled.md"; ASC="$SENT.asc"
else
  if [ -L "$SENT" ]; then die "o sentinel virou symlink"; fi
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

say "6/7 stage EXATO + conferência touched ∪ {sentinel, .asc}, por estado e modo"
xargs git add -- < "$BAK/touched"
[ "$DRY" = "1" ] || git add -- "$SENT" "$ASC"
# Estado de cada caminho no índice, sem detecção de rename: os do patch e o sentinel são M; a .asc é A.
git diff --cached --no-renames --name-status | LC_ALL=C sort > "$BAK/staged"
{ awk '{printf "M\t%s\n", $0}' "$BAK/touched"; [ "$DRY" = "1" ] || printf 'M\t%s\nA\t%s\n' "$SENT" "$ASC"; } | LC_ALL=C sort > "$BAK/expected"
cmp -s "$BAK/staged" "$BAK/expected" \
  || die "conjunto staged (estado e caminho) ≠ patch + sentinel:$(printf '\n   %s' "$(LC_ALL=C comm -3 "$BAK/staged" "$BAK/expected" | tr '\t' ' ')")"
while read -r p old new; do
  st=$(git rev-parse --verify --quiet ":$p") || die "$p não está no índice depois do stage"
  [ "$st" = "$new" ] || die "$p no índice tem o blob $st; o patch revisado declara $new"
  mh=$(git ls-tree HEAD -- "$p" | awk '{print $1}')
  mi=$(git ls-files -s -- "$p" | awk '{print $1}')
  [ "$mh" = "$mi" ] || die "$p muda de modo no índice ($mh → $mi); este SIGN não landa mudança de modo"
done < "$BAK/blobs"
if [ "$DRY" != "1" ]; then
  # O que vai para o commit é o que foi assinado: blob do índice = o preenchido; assinatura reverificada
  # sobre o CONTEÚDO DO ÍNDICE (não sobre o arquivo vivo).
  [ "$(git rev-parse --verify --quiet ":$SENT")" = "$FILLED_BLOB" ] || die "o sentinel no índice não é o assinado"
  git show ":$SENT" > "$BAK/sentinel.index.md"
  git show ":$ASC" > "$BAK/sentinel.index.asc"
  SIGNER2=$(signer_tool verify "$BAK/sentinel.index.md" "$BAK/sentinel.index.asc") || die "a assinatura no índice não verifica"
  [ "$SIGNER2" = "$SIGNER" ] || die "o signatário no índice ($SIGNER2) ≠ o da assinatura ($SIGNER)"
fi
# Modo no índice: 100644 para tudo o que entra (um chmod +x durante a bateria não passa).
while IFS="$(printf '\t')" read -r _st p; do
  m=$(git ls-files -s -- "$p" | awk '{print $1}')
  [ "$m" = "100644" ] || die "$p entra no índice com modo '$m' (esperado 100644)"
done < "$BAK/staged"
sed 's/^/   /' "$BAK/staged"
printf '   %s blob(s) e modo(s) no índice conferido(s) contra o patch e o HEAD; modos 100644\n' "$(wc -l < "$BAK/blobs" | tr -d ' ')"
if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada assinado nem commitado; revertendo o patch"
  undo
  trap - EXIT INT TERM HUP
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    list_leftovers
    printf '\nFAIL: o ensaio passou, mas o desfazer não deixou a árvore rastreada limpa (acima)\n' >&2
    exit 1
  fi
  printf '\nEnsaio OK (logs em %s). Rode sem --dry-run para valer.\n' "$BAK"
  exit 0
fi

say "7/7 commit (nunca abre editor)"
# O pinentry pode ter levado minutos: o pai do commit precisa ser o Anchor-SHA assinado.
[ "$(git rev-parse HEAD)" = "$HEAD_SHA" ] \
  || die "o HEAD mudou antes do commit (era $HEAD_SHA) — o Anchor-SHA assinado não seria o pai do commit"
# A árvore do índice CONFERIDO (patch, sentinel assinado, .asc, modos): o commit tem de ser exatamente ela.
INDEX_TREE=$(git write-tree) || die "git write-tree falhou"
git commit -q -F - <<MSG
ceremony(PLAN-194 W4): publish do npm em Node 24 com npm 11.20.0 exato; a rc prova o toolchain sem publicar

W4.1 (D-12): o npm-publish.yml declara o toolchain do publish UMA vez, no
env do workflow — PUBLISH_NODE_MAJOR "24" e PUBLISH_NPM_VERSION "11.20.0"
(o npm que publicou o GA 1.4.2, run 36719886734) —, com o MESMO SHA do
setup-node (48b55a01, v6.4.0); o passo do npm instala a versão EXATA (era
o intervalo ^11.5.1) e confere Node e npm antes de qualquer empacotamento.
Os checkouts não deixam o token do job no .git/config.

W4.3: um job novo, rc-toolchain-proof, roda só em tag rc
(contains(github.ref, '-rc.')), com permissions contents: read, sem
environment, sem id-token e sem passo que escreva no registry: o mesmo
toolchain, o staging, o trailer do install.sh, o gate do packlist e um
npm pack --dry-run. Os passos que ele divide com o publish são cópias byte
a byte, e o teste pina isso. A regra «rc não publica» do job publish fica
intacta. Resíduo (OQ-5): a troca OIDC e a escrita no registry só são
exercidas no GA, com o playbook do PLAN-158 como rede.

W4.2: npm-trusted-publisher.txt registra que a configuração do publicador
confiável no npmjs.com precisa permitir publicação direta (npm publish):
uma criada depois de 2026-09-03 só permite «npm stage publish», e
recriá-la ou editá-la sem marcar a publicação direta quebra o publish do
GA, sem rc que pegue isso. A configuração em si não muda.

Livres no mesmo commit: a classe Plan194W4PublishToolchainTest em
test_release_workflow_asserts.py (17 testes: reprovam com os canônicos
anteriores, passam com estes), docs/actions-versions.md (o pin real do
setup-node e o bump para 24 que o Sprint 6 nunca landou) e
npm/INTEGRITY.md (Node 24 + npm exato). O patch dormente de rollback do
PLAN-158 segue aplicável.

Sentinel: $SENT (assinado por $SIGNER; Anchor-SHA $HEAD_SHA;
Patch-sha256 $PATCH_SHA; Rail-Record-sha256 $RAIL_SHA, $REC)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
# O commit é o índice conferido: árvore commitada = a gravada antes do commit (o que cobre a .asc, os
# modos e todo caminho) e pai = o Anchor-SHA. Um hook (pre-commit que stageia, por exemplo) que mude o
# commit faz o SIGN desfazê-lo (`reset --soft` para o Anchor-SHA, sem tocar a árvore) e o abort desfaz
# o resto.
if [ "$(git rev-parse 'HEAD^{tree}')" != "$INDEX_TREE" ] || [ "$(git rev-parse HEAD~1)" != "$HEAD_SHA" ]; then
  git diff --no-renames --name-status "$INDEX_TREE" 'HEAD^{tree}' > "$BAK/tree-diff" 2>&1 || :
  git reset -q --soft "$HEAD_SHA"
  die "o commit não é o índice conferido (árvore ou pai diferente; um hook mudou o commit?) — commit desfeito com reset --soft para o Anchor-SHA:$(printf '\n   %s' "$(tr '\t' ' ' < "$BAK/tree-diff")")"
fi
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
