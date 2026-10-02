#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (PLAN-194 W1, CI pronto para o
# Ubuntu 26.04), clonada do molde OWNER-FN04-SIGN.sh (PLAN-193 W4b, o último SIGN que landou
# código pelo próprio SIGN). O que muda em relação ao molde, declarado:
#  (1) um caminho só, canônico: .github/workflows/validate.yml. O conteúdo novo vive em DUAS
#      formas no pacote — a cópia staged (staged-w1/.github/workflows/validate.yml) e o w1.patch
#      (--full-index). O P0 exige que o blob da cópia staged seja o blob pós-imagem do patch:
#      as duas formas são o MESMO conteúdo; o que landa é o patch. Um patch que cria, remove ou
#      renomeia arquivo, ou muda modo, é recusado no P0 com nome;
#  (2) a bateria ganha o controle vermelho→verde da W1 (check-w1-shape.py): o P0 confere que
#      ele REPROVA no HEAD (o controle discrimina) e a bateria, que ele PASSA na árvore com o
#      patch;
#  (3) actionlint OBRIGATÓRIO, nas duas formas de invocação do CI (a do job validate e a do
#      actionlint.yml); ele e o validate-governance são julgados pelo MULTICONJUNTO de achados
#      (com e sem o patch): um achado que só existe com o patch reprova, mesmo se a base também
#      reprovar;
#  (4) o registro do rail é preso a TRÊS sujeitos — o sha256 do patch, o do texto assinável
#      (o sentinel do HEAD, ainda com os TO-FILL-BY-SIGN) e o do controle — e a linha
#      Rail-Reviewer-Verdict tem de ser a ÚLTIMA linha `VERDICT:` da saída verbatim do revisor,
#      coerente com o Rail-Verdict;
#  (5) o sentinel que se assina é gerado do `HEAD:<sentinel>` (não do arquivo vivo), depois de
#      conferir que o arquivo vivo não mudou durante a bateria; depois do stage, o blob do índice é
#      o do arquivo assinado e a assinatura é verificada de novo sobre o conteúdo do índice;
#  (6) as listagens de nomes usam --no-renames; um abort lista os arquivos rastreados que mudaram
#      durante a execução e que o desfazer não restaurou, com a receita; o --dry-run só diz «Ensaio
#      OK» com a árvore limpa depois do desfazer;
#  (6b) rail r2→r3: shellcheck obrigatório e sonda positiva da regra shellcheck do actionlint; o
#      validate-governance julgado pela saída INTEIRA (detalhe de cada violação); execução que não
#      chegou a julgar reprova; controle exige a linha RESUMO; VERDICT lido do bloco verbatim pela
#      gramática estrita (cerca ```text … ```, ÚNICA, lida inteira; cerca mal formada recusa); allowlist
#      e biblioteca de verificação lidas do HEAD; modos 100644 no índice;
#  (7) sem testes próprios do pacote além do controle: as suítes do pytest.ini com a divisão
#      de marcadores do CI cobrem os testes que leem o validate.yml; sem conferência de bit de
#      execução (o validate.yml é 100644 e o patch não muda modo).
# O resto é o molde: P0 (main, origin/main contido no HEAD, árvore rastreada limpa, materiais
# commitados, base pinada pelas linhas index, Scope = tocados, canônicos = o declarado, chave
# do allowlist, último registro do rail com APPROVE/DECLARED-P2), aplicar, conferir pós-imagem,
# bateria julgada contra a árvore sem o patch, preencher o sentinel, assinar (um pinentry), stage
# EXATO, commit sem editor. Sem push.
#
# OWNER-W1-SIGN.sh — verifica, assina e landa a W1 do PLAN-194 em UM passo.
#
#   bash .claude/plans/PLAN-194/wave-w1/OWNER-W1-SIGN.sh                 # real (terminal interativo)
#   bash .claude/plans/PLAN-194/wave-w1/OWNER-W1-SIGN.sh --dry-run       # ensaio: não assina, não commita
#   bash .claude/plans/PLAN-194/wave-w1/OWNER-W1-SIGN.sh --check-base REV
#        # só leitura, em segundos: a base pinada do patch (o blob pré-imagem) é a de REV?
#        # rc 0 = o patch aplica sobre REV; rc 1 = nomeia o caminho que difere
#
# Ordem (nada é assinado antes de a bateria passar; o passo falível do GPG é o último antes do
# commit): P0 pré-condições + chave de assinatura + registro do rail → 1/7 aplica o patch → 2/7
# bytes aplicados = bytes revisados → 3/7 bateria (controle da W1, actionlint nas duas formas,
# gates de corpus e suítes do pytest.ini com a divisão de marcadores do CI, falhas julgadas contra
# a árvore sem o patch) → 4/7 sentinel do HEAD preenchido (Anchor-SHA, Patch-sha256,
# Rail-Record-sha256, Data) → 5/7 assina (um pinentry) → 6/7 stage EXATO (touched ∪ {sentinel,
# .asc}) e reverificação da assinatura no índice → 7/7 commit.
# NÃO faz push. Qualquer falha (ou Ctrl-C / TERM / HUP) antes do commit desfaz o que o SCRIPT
# aplicou: reverte o patch, restaura o sentinel, remove a .asc e o worktree da base; arquivos
# rastreados que a bateria (ou outro processo) mudou fora disso NÃO são revertidos — o abort os
# lista, com a receita. Os logs ficam no diretório temporário que a falha nomeia. Rodar de novo
# depois de um abort é seguro.
# A bateria roda as suítes do pytest.ini com a divisão de marcadores do CI (paralela
# 'not serial' + serial) — um conjunto MAIOR que o dos jobs do CI; o molde mediu ~15 min numa
# máquina quieta. O --dry-run é opcional (repete a bateria inteira; o modo real já desfaz numa
# falha). Fique no terminal: o pinentry vem DEPOIS da bateria, e um pinentry que expira desfaz
# tudo. Uma falha nomeada «falhas NOVAS» pode vir de estado da árvore viva (arquivos ignorados,
# dist/, .claude/state/) que o worktree limpo da base não tem: confira o log; a saída é rodar de
# novo, nunca editar o patch.
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
D=.claude/plans/PLAN-194/wave-w1
SENT=.claude/plans/PLAN-194/wave-w1-approved.md
SENT_REPO="$SENT"
ASC="$SENT.asc"
PATCH="$D/w1.patch"
SELF="$D/OWNER-W1-SIGN.sh"
SHAPE="$D/check-w1-shape.py"
TARGET_PATH=.github/workflows/validate.yml
STAGED="$D/staged-w1/$TARGET_PATH"
ORACLE=.claude/hooks/check_canonical_edit.py
SIGNERS=.claude/sentinel-signers.txt
GPG_VERIFY_LIB=.claude/hooks/_lib/gpg_verify.py
CANON="
.github/workflows/validate.yml
"
# As duas formas do actionlint no CI: a do job validate (validate.yml) e a do actionlint.yml.
AL_SC_FLAGS="-S error -e SC2002,SC2012,SC2016,SC2129"
RAIL_MAX_ROUNDS=3
APPLIED=0
SENT_TOUCHED=0
SIGN_STARTED=0
P0_CLEAN=0
BASE_WT=""
BAK=$(mktemp -d "${TMPDIR:-/tmp}/w1-sign.XXXXXX")
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
patch_blobs() {  # arquivo de saída — uma linha "<caminho> <blob pré-imagem> <blob pós-imagem>" por caminho do patch
  awk '/^diff --git /{p=$3; sub(/^a\//, "", p)} /^index /{split($2, h, /\.\./); print p, h[1], h[2]}' "$PATCH" > "$1"
}

if [ -n "$CHECK_BASE" ]; then
  # Só leitura: nada é aplicado, nada é escrito na árvore. Para conferir, ANTES de qualquer land
  # que toque o validate.yml, se os bytes da base ainda são os que este pacote pinou.
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
    printf '\nFAIL: a base pinada da W1 não é a de %s — o w1.patch não aplica ali. Re-derivar o\n' "$CHECK_BASE" >&2
    printf 'pacote pede rail sobre o patch novo; não lande bytes diferentes nesse caminho sem isso.\n' >&2
    exit 1
  fi
  printf '\nOK: a base pinada da W1 é a de %s (o w1.patch aplica ali).\n' "$CHECK_BASE"
  exit 0
fi
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
  remove_base_wt
  if [ "$APPLIED" = "1" ]; then
    git reset -q HEAD -- . 2>/dev/null
    if git apply -R --check "$PATCH" 2>/dev/null; then
      git apply -R "$PATCH"; done_what="$done_what patch-revertido"
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
spec = importlib.util.spec_from_file_location("gpg_verify_w1", glib)
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
# Um worktree da base que uma execução anterior INTERROMPIDA (kill -9, queda) deixou é deste script
# (um diretório w1-sign.*/base-wt que só ele cria): removido antes de começar.
git worktree list --porcelain | awk '/^worktree /{print substr($0, 10)}' > "$BAK/worktrees"
while IFS= read -r wt; do
  case "$wt" in
    */w1-sign.*/base-wt)
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
  printf 'e, para um arquivo que a bateria de uma execução interrompida sujou: git checkout HEAD -- <arquivo>\n' >&2
  die "há modificação RASTREADA pendente"
fi
P0_CLEAN=1
[ ! -e "$ASC" ] || die "já existe $ASC — remova a assinatura antiga antes (rm $ASC)"
for f in "$SENT" "$PATCH" "$STAGED" "$SHAPE" "$ORACLE" "$SELF" "$SIGNERS" "$GPG_VERIFY_LIB"; do [ -f "$f" ] || die "ausente: $f"; done
for f in "$SENT" "$PATCH" "$STAGED" "$SHAPE" "$SELF" "$SIGNERS" "$GPG_VERIFY_LIB"; do
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
command -v actionlint >/dev/null 2>&1 || die "actionlint ausente do PATH — este pacote só muda workflow e a bateria o exige (brew install actionlint)"
command -v shellcheck >/dev/null 2>&1 || die "shellcheck ausente do PATH — a forma do actionlint.yml roda o shellcheck e a bateria o exige (brew install shellcheck)"
command -v gpg >/dev/null 2>&1 || die "gpg ausente"
# A chave é escolhida ANTES da bateria (também no --dry-run): sem chave do allowlist, a falha vem
# agora, não depois de 15 minutos.
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
python3 -c 'import yaml' >/dev/null 2>&1 || die "PyYAML ausente (python3 -m pip install 'PyYAML>=6.0') — o controle da W1 lê o YAML"
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
# As duas formas do conteúdo novo são o MESMO conteúdo: o blob da cópia staged = o pós-imagem do patch.
STAGED_BLOB=$(git hash-object -- "$STAGED")
POST_BLOB=$(awk -v t="$TARGET_PATH" '$1 == t {print $3}' "$BAK/blobs")
[ -n "$POST_BLOB" ] || die "o patch não toca $TARGET_PATH"
[ "$STAGED_BLOB" = "$POST_BLOB" ] || die "a cópia staged ($STAGED, blob $STAGED_BLOB) não é o pós-imagem do patch ($POST_BLOB) — as duas formas divergem"
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
# O texto assinável é o do HEAD (a árvore está limpa: o arquivo vivo é o mesmo agora). Tudo que se
# lê dele daqui em diante vem dessa cópia.
git show "HEAD:$SENT" > "$BAK/sentinel.head.md" || die "não consegui ler HEAD:$SENT"
SENT_HEAD_SHA=$(shasum -a 256 "$BAK/sentinel.head.md" | awk '{print $1}')
SHAPE_HEAD_SHA=$(git show "HEAD:$SHAPE" | shasum -a 256 | awk '{print $1}')
awk '/^## Scope/{s=1; next} /^## /{s=0} s && /^- `/{sub(/^- `/, ""); sub(/`.*/, ""); print}' "$BAK/sentinel.head.md" | sort -u > "$BAK/scope"
DIFF=$(comm -3 "$BAK/touched" "$BAK/scope")
[ -z "$DIFF" ] || die "touched ≠ Scope do sentinel:$(printf '\n   %s' $DIFF)"
# O controle vermelho→verde só vale se discrimina: no HEAD (sem o patch) ele REPROVA.
set +e
python3 "$SHAPE" "$TARGET_PATH" > "$BAK/shape-head.out" 2>&1
SHAPE_HEAD_RC=$?
set -e
# rc 1 E a linha de resumo do próprio controle (uma exceção do Python também sai com rc 1).
if [ "$SHAPE_HEAD_RC" != "1" ] || ! grep -qE '^RESUMO: [0-9]+ falha' "$BAK/shape-head.out"; then
  tail -5 "$BAK/shape-head.out" >&2
  die "o controle da W1 não reprova no HEAD (rc=$SHAPE_HEAD_RC, sem 'RESUMO: N falha(s)') — ou o HEAD já tem a W1, ou o controle não discrimina"
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
R_CTRL=$(field Rail-Control-sha256) || die "$REC: linha Rail-Control-sha256 ausente ou repetida"
R_REV=$(field Rail-Reviewer-Verdict) || die "$REC: linha Rail-Reviewer-Verdict ausente ou repetida"
R_VERD=$(field Rail-Verdict) || die "$REC: linha Rail-Verdict ausente ou repetida"
R_FIND=$(field Rail-Findings) || die "$REC: linha Rail-Findings ausente ou repetida"
[ "$R_ROUND" = "$LAST" ] || die "$REC declara Rail-Round '$R_ROUND'"
[ "$R_SUBJ" = "$PATCH_SHA" ] || die "o último registro do rail ($REC) revisou outro patch ($R_SUBJ), não este ($PATCH_SHA)"
[ "$R_SENT" = "$SENT_HEAD_SHA" ] || die "o último registro do rail ($REC) revisou outro texto assinável ($R_SENT), não o sentinel do HEAD ($SENT_HEAD_SHA)"
[ "$R_CTRL" = "$SHAPE_HEAD_SHA" ] || die "o último registro do rail ($REC) revisou outro controle ($R_CTRL), não o $SHAPE do HEAD ($SHAPE_HEAD_SHA)"
# A linha VERDICT literal do revisor. Gramática do registro (a mesma da W3b.1):
#   - exatamente UMA linha igual a «## Saída do revisor»;
#   - nessa seção, exatamente UM bloco verbatim: abre com uma linha IGUAL a «```text» e fecha com a
#     próxima linha IGUAL a «```»; o bloco é lido INTEIRO até o fechamento, e nada dentro dele
#     (título «## …», prosa) encerra a seção;
#   - na seção, nenhuma OUTRA linha pode começar com ``` — nem depois de espaços (indentar NÃO
#     escapa); quem copia a saída do revisor cita essas linhas com o prefixo «> »;
#   - o veredito é a ÚLTIMA linha do bloco que começa com «VERDICT: », e o valor é GO,
#     GO-WITH-CONDITIONS ou NO-GO;
#   - seção ausente ou repetida, cerca ausente, duplicada, mal formada ou não fechada, ou bloco sem
#     linha VERDICT: o registro é RECUSADO.
LAST_VERDICT=$(awk '
  # estado: 0 antes da seção; 1 na seção, antes do bloco; 2 dentro do bloco; 3 bloco fechado; 4 depois
  state == 2 {
    if ($0 == "```") { state = 3; next }
    t = $0; sub(/^[[:space:]]+/, "", t)
    if (t ~ /^```/) { bad = "linha de cerca mal formada DENTRO do bloco verbatim (crases no início, mesmo indentadas)"; exit }
    if ($0 ~ /^VERDICT: /) v = substr($0, 10)
    next
  }
  $0 == "## Saída do revisor" { sec++; if (state == 0) state = 1; next }
  (state == 1 || state == 3) && /^## / { state = 4; next }
  state == 1 || state == 3 { t = $0; sub(/^[[:space:]]+/, "", t) }
  state == 1 && t ~ /^```/ {
    if ($0 == "```text") { state = 2; blocks++; next }
    bad = "abertura de cerca mal formada (esperado uma linha igual a ```text, sem espaços)"; exit
  }
  state == 3 && t ~ /^```/ { bad = "segunda cerca na seção (bloco verbatim duplicado ou fechado antes da hora; indentada ou não)"; exit }
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
printf '       %s caminho(s) = Scope, canônico = o declarado, cópia staged = pós-imagem, materiais commitados,\n' "$(wc -l < "$BAK/touched" | tr -d ' ')"
printf '       controle da W1 reprova no HEAD (como deve)\n'
printf '   chave de assinatura (em %s): %s\n' "$SIGNERS" "$SIGN_KEY"
printf '   rail: %s = %s (%s; revisor %s), sobre Patch-sha256 %s,\n' "$REC" "$R_VERD" "$R_FIND" "$R_REV" "$PATCH_SHA"
printf '         sentinel %s e controle %s\n' "$SENT_HEAD_SHA" "$SHAPE_HEAD_SHA"

say "1/7 aplicar o patch"
git apply "$PATCH" || die "git apply falhou"
APPLIED=1

say "2/7 bytes aplicados = bytes revisados"
while read -r p old new; do
  now=$(git hash-object -- "$p")
  [ "$now" = "$new" ] || die "$p depois do apply tem o blob $now; o patch revisado declara $new"
done < "$BAK/blobs"
printf '   %s blob(s) conferido(s) contra o index pós-imagem do patch\n' "$(wc -l < "$BAK/blobs" | tr -d ' ')"

say "3/7 bateria (controle da W1, actionlint, gates de corpus + suítes do pytest.ini, julgados contra a árvore sem o patch)"
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
    governance)  # TODA linha da saída (cabeçalho, DETALHE de cada violação, contagem), menos: as linhas
      # de AVISO pelo prefixo diagnóstico do produtor (depois dos espaços, «WARN: », «WARNING: » ou
      # «WARN (grandfathered): » — nunca por substring: um detalhe de erro pode conter «WARN»), a
      # contagem «Warnings: N» e a linha «Repo:». Uma linha de detalhe com caminho absoluto da árvore
      # também difere entre a viva e o worktree da base: com a base vermelha, reprova (fail-closed).
      awk '{ t = $0; sub(/^[[:space:]]+/, "", t) }
        t ~ /^(WARN|WARNING|WARN \(grandfathered\)): / { next }
        t ~ /^Warnings: [0-9]+$/ { next }
        /^Repo: / { next }
        { gsub(/[[:space:]]+/, " "); print }' "$2" | LC_ALL=C sort ;;
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
# O controle da W1 sobre os bytes aplicados: verde aqui (no P0 ele reprovou no HEAD).
python3 "$SHAPE" "$TARGET_PATH" > "$BAK/shape-applied.out" 2>&1 \
  || { tail -12 "$BAK/shape-applied.out" >&2; die "o controle da W1 reprova na árvore com o patch (log: $BAK/shape-applied.out)"; }
grep -qx 'RESUMO: verde' "$BAK/shape-applied.out" || die "o controle da W1 saiu rc 0 sem 'RESUMO: verde' (log: $BAK/shape-applied.out)"
printf '   ok: controle da W1 (vermelho no HEAD, verde com o patch)\n'
# actionlint nas duas formas do CI. A do job validate passa as flags do shellcheck em -shellcheck,
# o que (medido no 1.7.12, -verbose) DESLIGA a regra shellcheck; a do actionlint.yml a mantém.
printf '   actionlint local: %s; shellcheck: %s\n' "$(actionlint -version 2>/dev/null | awk 'NR == 1')" \
  "$(shellcheck --version 2>/dev/null | awk '/^version:/{print $2}')"
# Sonda positiva: com o shellcheck no PATH a regra precisa EXECUTAR (sem ele o actionlint sai rc 0
# em silêncio). Um workflow mínimo com um SC conhecido tem de produzir um achado [shellcheck].
printf 'name: sonda\non: [push]\njobs:\n  a:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo $sonda_sem_aspas\n' > "$BAK/al-probe.yml"
actionlint -no-color "$BAK/al-probe.yml" > "$BAK/al-probe.out" 2>&1 || :
grep -q '\[shellcheck\]' "$BAK/al-probe.out" \
  || die "a regra shellcheck do actionlint não executou na sonda (log: $BAK/al-probe.out) — a forma do actionlint.yml não seria reproduzida"
printf '   ok: sonda da regra shellcheck do actionlint (achado [shellcheck] na sonda)\n'
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
  # O que vai para o commit é o que foi assinado: blob do índice = o preenchido; assinatura reverificada
  # sobre o CONTEÚDO DO ÍNDICE (não sobre o arquivo vivo).
  [ "$(git rev-parse --verify --quiet ":$SENT")" = "$FILLED_BLOB" ] || die "o sentinel no índice não é o assinado"
  git show ":$SENT" > "$BAK/sentinel.index.md"
  git show ":$ASC" > "$BAK/sentinel.index.asc"
  SIGNER2=$(signer_tool verify "$BAK/sentinel.index.md" "$BAK/sentinel.index.asc") || die "a assinatura no índice não verifica"
  [ "$SIGNER2" = "$SIGNER" ] || die "o signatário no índice ($SIGNER2) ≠ o da assinatura ($SIGNER)"
fi
# Modo no índice: 100644 para tudo o que entra (um chmod +x durante a bateria não passa).
while read -r p; do
  m=$(git ls-files -s -- "$p" | awk '{print $1}')
  [ "$m" = "100644" ] || die "$p entra no índice com modo '$m' (esperado 100644)"
done < "$BAK/staged"
sed 's/^/   /' "$BAK/staged"
printf '   %s blob(s) no índice conferido(s) contra o index pós-imagem do patch; modos 100644\n' "$(wc -l < "$BAK/blobs" | tr -d ' ')"
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
git commit -q -F - <<MSG
ceremony(PLAN-194 W1): CI pronto para o Ubuntu 26.04 — perna 3.9 em ubuntu-24.04, canário 3.14

No validate.yml, o job hook-tests-python-matrix passa a escolher o runner
por versão: a perna 3.9 (piso do contrato) roda no rótulo fixo
ubuntu-24.04, porque o setup-python não tem 3.9 para o 26.04 e o
ubuntu-latest vira 26.04 a partir de 2026-10-19; uma perna 3.14 em
ubuntu-26.04 entra só no schedule, como canário do sistema novo; 3.10,
3.11 e 3.12 seguem no Ceo. As pernas nos runners padrão ganham 45 min de
timeout (as do Ceo seguem com 25). No job validate, o step que confere
settings.json e os catálogos YAML vai para depois do setup-python e do
pip que instala o PyYAML: os dois import yaml deixam de depender de um
PyYAML da imagem do runner. Controle vermelho→verde em
.claude/plans/PLAN-194/wave-w1/check-w1-shape.py (vermelho no HEAD anterior,
verde neste).

Fora deste patch, declarado no sentinel: o template do adopter (a
medição W0.1 no 26.04 saiu verde), os outros workflows em ubuntu-latest
e a imagem do runner Ceo (o Owner a fixa em 24.04 nas configurações da
organização).

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
