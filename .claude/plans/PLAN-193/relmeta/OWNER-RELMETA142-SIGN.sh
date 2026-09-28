#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (relmeta da v1.4.2),
# clonada do OWNER-RELMETA141-SIGN.sh (PLAN-192) com o endurecimento do molde
# mais novo (PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh); o toolkit do PLAN-188 é
# o que elimina esta classe.
# OWNER-RELMETA142-SIGN.sh — o release.sh passa a mirar a v1.4.2.
#
# UM passo: recusa um patch VELHO pelo nome, re-deriva o patch do HEAD num clone
# descartável e confere byte a byte com o material commitado, mostra o texto que
# vai para DENTRO da anotação assinada da tag, preenche Anchor-SHA e Data, assina
# o sentinel com uma chave do allowlist de signatários, aplica o patch, verifica,
# roda a bateria e commita (plumbing, sem editor). NÃO faz push (a decisão é sua).
#
#   bash .claude/plans/PLAN-193/relmeta/OWNER-RELMETA142-SIGN.sh --dry-run  # ensaio
#   bash .claude/plans/PLAN-193/relmeta/OWNER-RELMETA142-SIGN.sh            # real
#
# Antes (DEPOIS de todos os lands da 1.4.2):
#   bash .claude/plans/PLAN-193/relmeta/derive-relmeta142.sh --commit
#   git push origin main
#
# Um pinentry (a assinatura do sentinel). O run real exporta GPG_TTY=$(tty).
# A confirmação depois de ler o texto da tag é a palavra  assino  (e Enter).
# Se um run morrer sem restaurar (kill -9, queda de energia), o próximo run
# diz o que restaurar; à mão:
#   git checkout -- .claude/scripts/local/release.sh .claude/governance/gate-scripts-manifest.txt \
#     .claude/scripts/tests/test_release_bump_sites.py .claude/plans/PLAN-193/relmeta/relmeta142-approved.md
#   rm -f .claude/plans/PLAN-193/relmeta/relmeta142-approved.md.asc
#
# Diferenças para o molde relmeta-141 (motivo de cada uma no sentinel):
#  - patch VELHO recusado pelo NOME e pelo motivo, antes de re-derivar;
#  - a chave que assina tem de estar no allowlist (e no registro ADR-121), antes
#    do pinentry e de novo sobre a assinatura, pelo verificador do guard canônico;
#  - restauração também em INT/TERM/HUP (no bash 3.2 o trap de EXIT roda num TERM
#    com $? = 0, e um cleanup condicionado a rc≠0 não disparava);
#  - a bateria roda em ambiente de ALLOWLIST; variáveis git herdadas = recusa;
#    hooks do git e fsmonitor desligados nas operações git da própria cerimônia;
#  - o commit é montado por plumbing a partir das cópias CONGELADAS da
#    re-derivação e só avança o main por compare-and-swap;
#  - o HEAD é capturado UMA vez no P0: a re-derivação, a assinatura e o
#    compare-and-swap usam esse commit, e um HEAD que muda no meio aborta;
#  - o patch sai de um git diff com formato FIXO (sem a config git do usuário:
#    prefixos, índices, algoritmo) e o git apply --check roda ANTES da
#    assinatura;
#  - a confirmação é a palavra  assino , digitada DEPOIS de descartar o que foi
#    teclado durante a re-derivação (um Enter antecipado nunca assina);
#  - um SIGN interrompido sem trap (kill -9, queda de energia) é reconhecido
#    pela FORMA no P0, que imprime a restauração exata.
set -euo pipefail

_genv=""
for _v in $(git rev-parse --local-env-vars); do
  if [ -n "${!_v+x}" ]; then _genv="$_genv $_v"; fi
done
if [ -n "$_genv" ]; then
  printf '\nFAIL: variáveis git herdadas redirecionariam esta cerimônia:%s\n      rode num terminal sem elas (unset%s)\n' "$_genv" "$_genv" >&2
  exit 1
fi
export GIT_CONFIG_COUNT=2 \
  GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=core.fsmonitor GIT_CONFIG_VALUE_1=false

case "$#:${1:-}" in
  0:) DRY=0 ;;
  1:--dry-run) DRY=1 ;;
  *) printf '\nFAIL: uso: bash %s [--dry-run]  (recebido: %s)\n' "$0" "$*" >&2; exit 1 ;;
esac
# o stderr do TERMINAL, salvo no fd 9: é por ele que falam o die e o restore,
# também quando o sinal chega num passo com a saída redirecionada para log
exec 9>&2
TOP=$(git rev-parse --show-toplevel) \
  || { printf '\nFAIL: não é um checkout git (rode na raiz do checkout vivo)\n' >&2; exit 1; }
cd "$TOP"
ROOT=$(pwd -P)

# ---------------------------------------------------------------- constantes
PLAN=PLAN-193
D=.claude/plans/PLAN-193/relmeta
BASE_TAG=v1.4.1
PREV_BASE=1.4.1
TARGET_BASE=1.4.2
REMOTE_SLUG='Canhada-Labs/ceo-orchestration'
COAUTHOR='Claude Opus 5.5 (1M context) <noreply@anthropic.com>'
SIGNERS=.claude/sentinel-signers.txt
SIGNER_REGISTRY=.claude/security/sentinel-signers-registry.yaml
GPG_VERIFY_LIB=.claude/hooks/_lib/gpg_verify.py
SIGNER_REGISTRY_LIB=.claude/hooks/_lib/sentinel_signers.py
# ------------------------------------------------------------ fim constantes

SENT_LIVE="$D/relmeta142-approved.md"
ASC_LIVE="$SENT_LIVE.asc"
SENT="$SENT_LIVE"
ASC="$ASC_LIVE"
APPLY="$D/apply-relmeta142-edits.py"
PATCH="$D/RELMETA142.patch"
DERIVE="$D/derive-relmeta142.sh"
T_REL=.claude/scripts/local/release.sh
T_MAN=.claude/governance/gate-scripts-manifest.txt
T_TST=.claude/scripts/tests/test_release_bump_sites.py
PACK_FILES="$APPLY $DERIVE $D/OWNER-RELMETA142-SIGN.sh $D/rehearse-relmeta142.sh $SENT_LIVE $PATCH"
# a bateria roda com ambiente de ALLOWLIST: só isto é herdado (+ PATH e
# CLAUDE_PROJECT_DIR fixados); redirecionamento de raiz, opção do pytest ou
# escape hatch de gate ficam de fora por construção
KEEP_ENV="HOME USER LOGNAME SHELL TERM LANG LC_ALL LC_CTYPE TMPDIR PYTHONUSERBASE VIRTUAL_ENV PYENV_ROOT PYENV_VERSION"
BAK=$(mktemp -d "${TMPDIR:-/tmp}/relmeta142.XXXXXX") \
  || { printf '\nFAIL: mktemp do diretório de backup falhou\n' >&2; exit 1; }
FZ="$BAK/frozen"
mkdir "$FZ" || { printf '\nFAIL: mkdir %s falhou\n' "$FZ" >&2; exit 1; }
ARMED=0
REDERIVE_HINT="rode  bash $DERIVE --commit  e  git push origin main , e esta cerimônia de novo"

RECOVER_TREE="git checkout -- $T_REL $T_MAN $T_TST $SENT_LIVE && rm -f $ASC_LIVE"
RECOVER_INDEX="git reset -q -- $T_REL $T_MAN $T_TST $SENT_LIVE $ASC_LIVE"

die() { printf '\nFAIL: %s\n' "$*" >&9; exit 1; }
stale() { printf '\nFAIL: %s está VELHO (stale) — %s.\n      Rota: %s.\n' "$PATCH" "$*" "$REDERIVE_HINT" >&9; exit 1; }
interrupted() {  # a forma de um SIGN que morreu sem trap: rota exata, nunca «stale»
  printf '\nFAIL: SIGN INTERROMPIDO antes do commit — %s.\n      Confira com  git status  e restaure, depois rode esta cerimônia de novo:\n        %s\n' "$*" "$RECOVER_TREE" >&9
  exit 1
}
# git diff de formato FIXO: os bytes do patch dependem só das árvores, nunca da
# config git do usuário (diff.noprefix, core.abbrev, diff.algorithm,
# diff.orderFile, color, textconv, driver externo...)
canon_diff() {  # canon_diff <repo> <caminho>...
  local r="$1"
  shift
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 git -C "$r" \
    -c diff.noprefix=false -c diff.mnemonicPrefix=false -c diff.relative=false -c core.quotePath=true \
    diff --no-ext-diff --no-textconv --no-color --no-renames --no-relative --full-index --binary \
    --src-prefix=a/ --dst-prefix=b/ --unified=3 --inter-hunk-context=0 --diff-algorithm=myers \
    --indent-heuristic -O/dev/null -- "$@"
}
canon_apply() {  # canon_apply [--check] <patch> — sem apply.whitespace nem outra config do usuário
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 git apply --whitespace=nowarn "$@"
}
say() { printf '\n===== %s\n' "$*"; }
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }
blob_is() { git cat-file blob "$1" 2>/dev/null | cmp -s - "$2"; }
field() { sed -n "s/^$1: //p" "$SENT_LIVE" | head -n 1; }
restore() {
  # restore best-effort num trap de saída: falha vira aviso, nunca silêncio.
  # O ÍNDICE não é tocado: esta cerimônia nunca stageia antes do commit.
  if [ -f "$BAK/orig-rel" ]; then cp "$BAK/orig-rel" "$T_REL" || printf "restore do release.sh falhou\n" >&9; fi
  if [ -f "$BAK/orig-man" ]; then cp "$BAK/orig-man" "$T_MAN" || printf "restore do manifesto falhou\n" >&9; fi
  if [ -f "$BAK/orig-tst" ]; then cp "$BAK/orig-tst" "$T_TST" || printf "restore do teste falhou\n" >&9; fi
  if [ "$DRY" != "1" ] && [ -f "$BAK/orig-sent" ]; then
    cp "$BAK/orig-sent" "$SENT_LIVE" || printf "restore do sentinel falhou\n" >&9
    rm -f "$ASC_LIVE" || printf "remoção da assinatura parcial falhou\n" >&9
  fi
}
# ARMED=1 só depois do P0 (antes dele nada mudou). INT, TERM e HUP têm trap
# próprio que sai com 130/143/129: no bash 3.2 do macOS o trap de EXIT roda
# nesses sinais, mas num TERM ou HUP com $? = status do último comando concluído
trap 'rc=$?; [ $rc -ne 0 ] && [ "$ARMED" = "1" ] && { restore; printf "\nárvore RESTAURADA. Backup e logs em %s\n" "$BAK" >&9; }' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

clean_env_at() {  # clean_env_at <projeto> cmd... — ambiente de allowlist
  local dir="$1" a=() v
  shift
  for v in $KEEP_ENV; do
    if [ -n "${!v+x}" ]; then a+=("$v=${!v}"); fi
  done
  env -i ${a[@]+"${a[@]}"} PATH="$PATH" CLAUDE_PROJECT_DIR="$dir" PYTHONDONTWRITEBYTECODE=1 "$@"
}
clean_env() { clean_env_at "$ROOT" "$@"; }
# signatário: as DUAS pernas do guard canônico, com as mesmas funções —
# gpg_verify (GOODSIG+VALIDSIG e fingerprint em $SIGNERS) e, se o registro do
# ADR-121 existir, sentinel_signers.is_valid_signer.
#   signer_tool pick                      -> ecoa a chave SECRETA a usar
#   signer_tool verify <arquivo> <.asc>   -> ecoa o fingerprint aceito
signer_tool() {
  python3 - "$ROOT" "$GPG_VERIFY_LIB" "$SIGNERS" "$SIGNER_REGISTRY" "$SIGNER_REGISTRY_LIB" "$@" <<'PY'
import importlib.util, subprocess, sys
from pathlib import Path
root, glib, allow, reg_rel, slib, mode = sys.argv[1:7]
rest = sys.argv[7:]
def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, str(Path(root) / rel))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m   # dataclasses resolvem o módulo por nome
    spec.loader.exec_module(m)
    return m
g = load("gpg_verify_relmeta142", glib)
reg_path = Path(root) / reg_rel
registry = None
if reg_path.exists():
    s = load("sentinel_signers_relmeta142", slib)
    try:
        registry = s.load_registry(reg_path)
    except Exception as e:
        sys.stderr.write("aviso: registro %s ilegível (%s) — só a perna legada, como o guard pré-GENESIS\n" % (reg_rel, type(e).__name__))
def registry_ok(fpr):
    if registry is None:
        return True, "sem registro"
    return s.is_valid_signer(fpr, registry=registry)
if mode == "pick":
    fprs, err = g.load_allowlist(Path(root) / allow)
    if err:
        raise SystemExit("allowlist de signatários inválido: %s" % err)
    out = subprocess.run(["gpg", "--batch", "--with-colons", "--list-secret-keys"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         universal_newlines=True).stdout
    want = False
    for line in out.splitlines():
        f = line.split(":")
        if f[0] == "sec":
            want = True
        elif f[0] == "fpr" and want:
            want = False
            fpr = g.normalise_fpr(f[9])
            if fpr in fprs and registry_ok(fpr)[0]:
                print(fpr)
                raise SystemExit(0)
    raise SystemExit("nenhuma chave secreta deste GNUPGHOME está em %s (e válida no registro)" % allow)
if mode == "verify":
    ok, fpr, reason = g.verify_detached(Path(rest[0]), Path(rest[1]), allowlist_path=Path(root) / allow)
    if not ok:
        raise SystemExit("assinatura recusada: %s" % reason)
    valid, why = registry_ok(fpr)
    if not valid:
        raise SystemExit("registro de signatários recusa %s: %s" % (fpr, why))
    print(fpr)
    raise SystemExit(0)
raise SystemExit("modo desconhecido: %s" % mode)
PY
}

say "P0 pré-condições"
printf '   backup e logs desta rodada: %s\n' "$BAK"
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo"
if [ "$DRY" != "1" ]; then
  GPG_TTY=$(tty) || die "não consegui ler o terminal (tty) para o GPG_TTY"
  export GPG_TTY
fi
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
IDX_LOCK=$(git rev-parse --git-path index.lock) || die "git rev-parse --git-path falhou"
[ ! -e "$IDX_LOCK" ] || die "há $IDX_LOCK — outro git rodando? (ou lock órfão: confira e remova)"
# um SIGN que morreu SEM trap (kill -9, queda de energia) deixa uma de duas
# formas; as duas são reconhecidas ANTES do fetch, com a rota exata
if git cat-file -e "HEAD:$ASC_LIVE" 2>/dev/null; then
  # o commit da cerimônia já avançou o main local; o índice pode ter ficado velho
  git diff --cached --quiet HEAD -- \
    || die "o commit da cerimônia já está no main LOCAL, mas o índice ficou velho (SIGN interrompido depois do commit). Rode:  $RECOVER_INDEX  , confira com  git show --stat HEAD  e faça o push"
else
  if [ -e "$ASC_LIVE" ]; then interrupted "há uma assinatura $ASC_LIVE fora do HEAD"; fi
  if [ -f "$SENT_LIVE" ] && git cat-file -e "HEAD:$SENT_LIVE" 2>/dev/null; then
    A_DISK=$(sed -n 's/^Anchor-SHA: //p' "$SENT_LIVE" | head -n 1)
    A_HEAD=$(git show "HEAD:$SENT_LIVE" | sed -n 's/^Anchor-SHA: //p' | head -n 1)
    [ "$A_DISK" = "$A_HEAD" ] || interrupted "o sentinel no disco tem Anchor-SHA $A_DISK (no HEAD: $A_HEAD)"
  fi
  git diff --quiet HEAD -- "$T_REL" "$T_MAN" "$T_TST" \
    || interrupted "os alvos da cerimônia diferem do HEAD (um ensaio ou SIGN morreu depois de aplicar o patch)"
fi
git remote -v | grep -qF "$REMOTE_SLUG" || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
HEAD0=$(git rev-parse HEAD) || die "git rev-parse HEAD falhou"
[ "$HEAD0" = "$(git rev-parse origin/main)" ] || die "HEAD != origin/main — pushe ou puxe antes"
git diff --quiet HEAD -- "$SENT_LIVE" \
  || stale "o sentinel no disco difere do HEAD — uma derivação ficou sem commit"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "há modificação RASTREADA pendente"
# ...e por CONTEÚDO contra o HEAD, sem confiar nos bits assume-unchanged/skip-worktree
GIT_INDEX_FILE="$BAK/p0-index" git read-tree HEAD || die "read-tree do HEAD num índice temporário falhou"
GIT_INDEX_FILE="$BAK/p0-index" git diff --quiet HEAD -- \
  || die "a árvore de trabalho difere do HEAD sem aparecer no git status (bit assume-unchanged/skip-worktree?)"
for f in $PACK_FILES "$T_REL" "$T_MAN" "$T_TST" "$SIGNERS" "$GPG_VERIFY_LIB" "$SIGNER_REGISTRY_LIB"; do
  [ -f "$f" ] && [ ! -L "$f" ] || {
    [ "$f" = "$PATCH" ] && stale "o patch não existe — nunca foi derivado"
    die "ausente ou não-regular: $f"
  }
done
for f in $PACK_FILES; do
  git cat-file -e "HEAD:$f" 2>/dev/null || {
    [ "$f" = "$PATCH" ] && stale "o patch não está no HEAD — derivado mas nunca commitado"
    die "material fora do HEAD (commite e pushe antes): $f"
  }
done
[ -n "$(git ls-files -- ".claude/plans/$PLAN-*.md")" ] || die "o plano .claude/plans/$PLAN-*.md não está no HEAD"
git rev-parse -q --verify "refs/tags/$BASE_TAG" >/dev/null || die "tag $BASE_TAG ausente — a relmeta-142 só entra DEPOIS do corte do GA"
git merge-base --is-ancestor "$BASE_TAG" HEAD || die "$BASE_TAG não é ancestral do HEAD"
v=$(clean_env python3 .claude/hooks/check_canonical_edit.py --is-canonical "$T_MAN" 2>/dev/null | awk '{print $2}') \
  || die "o oráculo --is-canonical falhou para $T_MAN"
[ "$v" = "1" ] || die "$T_MAN NÃO é canônico (oráculo=$v) — não use esta cerimônia"
awk -v f="$T_REL" '$2==f{n++} END{exit !(n==1)}' "$T_MAN" || die "$T_REL não é membro único do manifesto ADR-192"
[ ! -e "$ASC_LIVE" ] || die "já existe $ASC_LIVE — esta cerimônia já rodou? confira com git log"
grep -q "^TARGET_BASE=\"$PREV_BASE\"\$" "$T_REL" || die "o driver não está em $PREV_BASE — esta cerimônia já landou?"
SIGN_KEY=$(signer_tool pick) || die "sem chave autorizada para assinar (allowlist: $SIGNERS)"
cp "$T_REL" "$BAK/orig-rel" && cp "$T_MAN" "$BAK/orig-man" && cp "$T_TST" "$BAK/orig-tst" \
  && cp "$SENT_LIVE" "$BAK/orig-sent" || die "não consegui copiar os originais (backup: $BAK)"
ARMED=1
printf '   OK: main sincronizado, árvore limpa, materiais no HEAD, %s ancestral, manifesto canônico,\n' "$BASE_TAG"
printf '       driver em %s, chave de assinatura no allowlist: %s\n' "$PREV_BASE" "$SIGN_KEY"
if [ "$DRY" != "1" ]; then printf '       GPG_TTY=%s\n' "$GPG_TTY"; fi

say "1/8 o patch commitado é a derivação DESTE HEAD? (motivo pelo nome)"
PSHA_PIN=$(field Patch-SHA256); ASHA_PIN=$(field Derivator-SHA256)
FROM_PIN=$(field Derived-From); SCOPE_PIN=$(field Scope-Derived)
for x in "$PSHA_PIN" "$ASHA_PIN" "$FROM_PIN" "$SCOPE_PIN"; do
  case "$x" in ''|DERIVE-PLACEHOLDER) stale "o sentinel não tem as linhas derivadas — o patch nunca foi derivado" ;; esac
done
PSHA=$(sha256f "$PATCH")
[ "$PSHA" = "$PSHA_PIN" ] || stale "o sha256 do patch ($PSHA) não é o que o sentinel pina ($PSHA_PIN) — patch e sentinel descasados"
[ "$(sha256f "$APPLY")" = "$ASHA_PIN" ] || stale "o derivador no HEAD não é o que gerou o patch (Derivator-SHA256 $ASHA_PIN)"
BASE_EFF=$(git log -1 --format=%H "$HEAD0" -- . ":(exclude)$D") || die "git log da base efetiva falhou"
if [ "$BASE_EFF" != "$FROM_PIN" ]; then
  if git merge-base --is-ancestor "$FROM_PIN" "$HEAD0" 2>/dev/null; then
    LATE=$(git log --oneline "$FROM_PIN..$HEAD0" -- . ":(exclude)$D") || LATE="(git log falhou)"
    printf '%s\n' "$LATE" | sed 's/^/      landou depois: /' >&9
    stale "$(printf '%s\n' "$LATE" | grep -c .) commit(s) fora de $D landaram depois da derivação (Derived-From $FROM_PIN)"
  fi
  stale "a base da derivação ($FROM_PIN) não é ancestral do HEAD"
fi
printf '   Patch-SHA256, Derivator-SHA256 e Derived-From batem com o HEAD\n'

say "2/8 re-derivar do HEAD (clone descartável) e conferir byte a byte"
git clone --quiet --local --no-hardlinks "$ROOT" "$BAK/wt" || die "clone descartável falhou"
[ "$(git -C "$BAK/wt" rev-parse HEAD)" = "$HEAD0" ] || die "o clone não está no HEAD do P0 ($HEAD0) — o main mudou durante a cerimônia; rode de novo"
( cd "$BAK/wt" && clean_env_at "$BAK/wt" python3 "$APPLY" --repo . ) >"$BAK/derive.out" 2>&1 \
  || { cat "$BAK/derive.out" >&9; die "o derivador recusou sobre o HEAD (log: $BAK/derive.out) — uma âncora ou pré-condição falhou; NÃO assine"; }
canon_diff "$BAK/wt" "$T_REL" "$T_MAN" "$T_TST" >"$BAK/rederived.patch" \
  || die "git diff no clone falhou"
[ -s "$BAK/rederived.patch" ] || die "o derivador não mudou nada — nada a assinar"
EXTRA=$(git -C "$BAK/wt" status --porcelain --untracked-files=all \
  | awk -v a="$T_REL" -v b="$T_MAN" -v c="$T_TST" '{p=$2} p!=a && p!=b && p!=c {print p}')
[ -z "$EXTRA" ] || die "o derivador tocou fora do escopo: $EXTRA"
SCOPE_NOW=$(sed -n 's/^scope: //p' "$BAK/derive.out")
if ! cmp -s "$BAK/rederived.patch" "$PATCH"; then
  printf '      escopo pinado     : %s\n      escopo re-derivado: %s\n' "$SCOPE_PIN" "$SCOPE_NOW" >&9
  stale "a re-derivação do HEAD difere, byte a byte, do patch commitado (escopo do trem ou pré-imagem mudou)"
fi
[ "$SCOPE_NOW" = "$SCOPE_PIN" ] || stale "o escopo re-derivado ($SCOPE_NOW) não é o pinado ($SCOPE_PIN)"
# o patch tem de aplicar sobre a árvore viva ANTES do pinentry, não depois
canon_apply --check "$PATCH" || die "o patch commitado não aplica sobre a árvore viva — NADA assinado"
for p in rel:"$T_REL" man:"$T_MAN" tst:"$T_TST"; do
  cp "$BAK/wt/${p#*:}" "$FZ/${p%%:*}" || die "não consegui congelar ${p#*:}"
done
sed 's/^/   /' "$BAK/derive.out"

say "3/8 o texto que vai para DENTRO da anotação assinada da tag"
awk '/^TARGET_BASE=/{f=1} f{print} /^RC_NUM=/{exit}' "$FZ/rel" | sed '$d' | sed 's/^/   | /'
if [ "$DRY" != "1" ]; then
  # o que foi teclado DURANTE a re-derivação (um Enter antecipado) é descartado:
  # só uma resposta digitada depois do bloco impresso conta
  while read -r -t 1 _ 2>/dev/null; do :; done
  printf '\nLeia o bloco acima. Para assinar, digite  assino  e Enter (outra resposta, ou ctrl-C, aborta e restaura): '
  read -r ANSWER || die "sem resposta no terminal — nada assinado"
  # ${...}: no bash 3.2 um byte não-ASCII colado ao nome entra no nome da variável
  [ "${ANSWER}" = "assino" ] || die "resposta «${ANSWER}» (não é  assino ) — nada assinado"
fi

say "4/8 Anchor-SHA e Data reais no sentinel"
HEAD_SHA="$HEAD0"
[ "$(git rev-parse HEAD)" = "$HEAD0" ] || die "o HEAD mudou durante a cerimônia (era $HEAD0) — nada assinado; rode de novo"
TODAY=$(date +%Y-%m-%d) || die "date falhou"
# o ENSAIO nunca muta material persistente: trabalha sobre uma cópia
if [ "$DRY" = "1" ]; then
  cp "$SENT" "$BAK/sentinel.md" || die "não consegui copiar o sentinel para o ensaio"
  SENT="$BAK/sentinel.md"; ASC="$SENT.asc"
fi
python3 - "$SENT" "$HEAD_SHA" "$TODAY" <<'PY' || die "não consegui gravar Anchor-SHA e Data no sentinel"
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
for key, val in (("Anchor-SHA", sys.argv[2]), ("Data", sys.argv[3])):
    t, n = re.subn(r"^" + key + r":.*$", lambda _m: key + ": " + val, t, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("linha %s não encontrada" % key)
p.write_text(t, encoding="utf-8")
PY
grep -q "^Anchor-SHA: $HEAD_SHA\$" "$SENT" || die "Anchor-SHA não gravou"
grep -q "^Data: $TODAY\$" "$SENT" || die "Data não gravou"
grep -q "^Patch-SHA256: $PSHA\$" "$SENT" || die "o sentinel deixou de pinar o patch"
printf '   Anchor-SHA = %s   Data = %s\n' "$HEAD_SHA" "$TODAY"

say "5/8 assinar o sentinel (pinentry)"
SIGNER_FPR="(ensaio: sem assinatura)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura (chave: %s)\n' "$SIGN_KEY"
  cp "$SENT" "$FZ/sentinel" || die "não consegui congelar o sentinel"
else
  gpg --armor --detach-sign --local-user "$SIGN_KEY" "$SENT" \
    || die "assinatura falhou (GPG_TTY=$GPG_TTY) — se o gpg reclamou de pinentry, rode: gpgconf --kill gpg-agent; export GPG_TTY=\$(tty)"
  cp "$SENT" "$FZ/sentinel" && cp "$ASC" "$FZ/asc" || die "não consegui congelar o par assinado"
  SIGNER_FPR=$(signer_tool verify "$FZ/sentinel" "$FZ/asc") || die "a assinatura não verifica contra $SIGNERS"
  printf '   assinado por %s (no allowlist)\n' "$SIGNER_FPR"
fi

say "6/8 aplicar o patch e verificar"
for t in "$T_REL" "$T_MAN" "$T_TST"; do if [ -L "$t" ]; then die "alvo é symlink: $t"; fi; done
[ "$(git rev-parse HEAD)" = "$HEAD0" ] || die "o HEAD mudou durante a cerimônia (era $HEAD0)"
canon_apply --check "$PATCH" || die "o patch não aplica sobre o HEAD"
canon_apply "$PATCH" || die "git apply falhou"
cmp -s "$T_REL" "$FZ/rel" && cmp -s "$T_MAN" "$FZ/man" && cmp -s "$T_TST" "$FZ/tst" \
  || die "o patch aplicado não reproduz os bytes da re-derivação"
grep -q "^TARGET_BASE=\"$TARGET_BASE\"\$" "$T_REL" || die "TARGET_BASE não foi para $TARGET_BASE"
clean_env shasum -a 256 -c "$T_MAN" >"$BAK/manifest.out" 2>&1 \
  || { cat "$BAK/manifest.out" >&9; die "manifesto ADR-192 não confere (o mesmo comando do CI)"; }
# conjunto: toda linha do manifesto conferida OK, nem uma a menos
MAN_N=$(grep . "$T_MAN" | wc -l | tr -d ' ')
OK_N=$(grep ': OK$' "$BAK/manifest.out" | wc -l | tr -d ' ')
[ "$OK_N" = "$MAN_N" ] || die "manifesto: $OK_N linhas OK para $MAN_N linhas (log: $BAK/manifest.out)"
bash -n "$T_REL" || die "release.sh não passa em bash -n"
clean_env bash "$T_REL" --help >"$BAK/help.out" 2>&1 || { cat "$BAK/help.out" >&9; die "release.sh --help falhou"; }
grep -q "target base version: $TARGET_BASE" "$BAK/help.out" || die "o driver não anuncia $TARGET_BASE"
clean_env python3 -m pytest "$T_TST" -q -p no:cacheprovider >"$BAK/pytest.out" 2>&1 \
  || { tail -n 30 "$BAK/pytest.out" >&9; die "a suíte do driver reprovou (log: $BAK/pytest.out)"; }
printf '   bytes = re-derivação, manifesto OK, bash -n OK, --help anuncia %s, %s\n' "$TARGET_BASE" "$(tail -n 1 "$BAK/pytest.out")"

say "7/8 bateria de gates (ambiente de allowlist)"
clean_env bash .claude/scripts/validate-governance.sh >"$BAK/gov.out" 2>&1 \
  || { tail -n 40 "$BAK/gov.out" >&9; die "validate-governance reprovou (log: $BAK/gov.out)"; }
grep -q 'Errors:   0' "$BAK/gov.out" || die "governance com erros (log: $BAK/gov.out)"
clean_env python3 .claude/scripts/check_contamination.py >"$BAK/contam.out" 2>&1 \
  || { tail -n 20 "$BAK/contam.out" >&9; die "contamination reprovou (log: $BAK/contam.out)"; }
clean_env bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >"$BAK/counts.out" 2>&1 \
  || { tail -n 20 "$BAK/counts.out" >&9; die "verify-counts reprovou (log: $BAK/counts.out)"; }
clean_env python3 .claude/scripts/check-ceremony-script.py >"$BAK/lint.out" 2>&1 \
  || { tail -n 20 "$BAK/lint.out" >&9; die "ceremony-lint reprovou (log: $BAK/lint.out)"; }
clean_env python3 .claude/scripts/check-claude-md-claims.py >"$BAK/claims.out" 2>&1 \
  || { tail -n 20 "$BAK/claims.out" >&9; die "check-claude-md-claims reprovou (log: $BAK/claims.out)"; }
# a bateria não pode ter mexido em NADA rastreado fora do escopo...
OUTSIDE=$(git status --porcelain --untracked-files=no | awk '{print $NF}' \
  | grep -vxF -e "$T_REL" -e "$T_MAN" -e "$T_TST" -e "$SENT_LIVE" || printf '')
[ -z "$OUTSIDE" ] || die "a bateria modificou arquivo rastreado fora do escopo:
$OUTSIDE"
# ...nem nos arquivos do escopo
cmp -s "$T_REL" "$FZ/rel" && cmp -s "$T_MAN" "$FZ/man" && cmp -s "$T_TST" "$FZ/tst" \
  || die "um alvo mudou durante a bateria"
cmp -s "$SENT" "$FZ/sentinel" || die "o sentinel mudou depois da assinatura"
if [ "$DRY" != "1" ]; then cmp -s "$ASC" "$FZ/asc" || die "a assinatura mudou depois de gerada"; fi
printf '   governance 0 erros, contamination OK, counts OK, ceremony-lint OK, claims OK\n'

say "8/8 árvore do commit: plumbing, bytes congelados, escopo exato"
TMPIDX="$BAK/index"
GIT_INDEX_FILE="$TMPIDX" git read-tree "$HEAD_SHA" || die "read-tree do HEAD no índice temporário falhou"
add_blob() {  # add_blob <caminho no repo> <arquivo congelado> — modo do HEAD, ou 100644 se novo
  local b m
  m=$(git ls-tree "$HEAD_SHA" -- "$1" | awk '{print $1}')
  [ -n "$m" ] || m=100644
  b=$(git hash-object -w --no-filters -- "$2") || die "hash-object de $2 falhou"
  GIT_INDEX_FILE="$TMPIDX" git update-index --add --cacheinfo "$m,$b,$1" \
    || die "update-index de $1 no índice temporário falhou"
}
add_blob "$T_REL" "$FZ/rel"
add_blob "$T_MAN" "$FZ/man"
add_blob "$T_TST" "$FZ/tst"
if [ "$DRY" = "1" ]; then
  EXPECTED=$(printf '%s\n' "$T_REL" "$T_MAN" "$T_TST" | sort)
else
  add_blob "$SENT_LIVE" "$FZ/sentinel"
  add_blob "$ASC_LIVE" "$FZ/asc"
  EXPECTED=$(printf '%s\n' "$T_REL" "$T_MAN" "$T_TST" "$SENT_LIVE" "$ASC_LIVE" | sort)
fi
TREE=$(GIT_INDEX_FILE="$TMPIDX" git write-tree) || die "write-tree do índice temporário falhou"
TOUCHED=$(git diff-tree -r --no-renames --name-only "$HEAD_SHA" "$TREE" | sort) || die "diff-tree da árvore montada falhou"
[ "$TOUCHED" = "$EXPECTED" ] || die "árvore diferente do escopo exato:
--- na árvore
$TOUCHED
--- esperado
$EXPECTED"
blob_is "$TREE:$T_REL" "$FZ/rel" && blob_is "$TREE:$T_MAN" "$FZ/man" && blob_is "$TREE:$T_TST" "$FZ/tst" \
  || die "um blob da árvore não é o byte da re-derivação"
[ "$(git ls-tree "$TREE" -- "$T_REL" | awk '{print $1}')" = "$(git ls-tree "$HEAD_SHA" -- "$T_REL" | awk '{print $1}')" ] \
  || die "o modo de $T_REL mudou na árvore montada"
if [ "$DRY" != "1" ]; then
  blob_is "$TREE:$SENT_LIVE" "$FZ/sentinel" || die "o blob do sentinel não é o byte assinado"
  blob_is "$TREE:$ASC_LIVE" "$FZ/asc" || die "o blob da assinatura não é o gerado"
fi
printf '%s\n' "$TOUCHED" | sed 's/^/   /'

if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada commitado; desfazendo"
  restore
  [ -z "$(git status --porcelain --untracked-files=no)" ] || die "o ensaio deixou a árvore suja"
  ARMED=0
  printf '\nEnsaio OK. Rode sem --dry-run para valer.\n'
  trap - EXIT; exit 0
fi

SIGNER_FPR2=$(signer_tool verify "$FZ/sentinel" "$FZ/asc") || die "a assinatura congelada deixou de verificar"
[ "$SIGNER_FPR2" = "$SIGNER_FPR" ] || die "fingerprint mudou entre as verificações"
SCOPE_SHOWN=$(sed -n 's/^RELEASE_SCOPE="\(.*\)"$/\1/p' "$FZ/rel")
MSG="$BAK/commit-msg.txt"
# heredoc, não printf: um formato que começa com "--" vira OPÇÃO do printf e a
# linha some em silêncio (medido no ensaio)
cat >"$MSG" <<EOF_MSG || die "não consegui escrever a mensagem do commit (em: $MSG)"
governance($PLAN relmeta-142): release.sh mira a v$TARGET_BASE + re-pin do manifesto ADR-192

O bloco por-release do driver passa a descrever a v$TARGET_BASE: título, escopo do
trem DERIVADO de git log $BASE_TAG..HEAD depois de todos os lands da release e a
headline que entra na anotação ASSINADA da tag — inclusive a parte honesta: a
cura do anexo P1 do envelope da v1.4.0 não faz parte desta release e segue sem
release atribuída ($PLAN OQ-3), e a limpeza do Claude Code pode apagar o log de
auditoria, sem plano de cura. Cada parágrafo da headline tem âncoras que o
derivador conferiu sobre esta árvore (duas são sondas de runtime: o FN-04 e o
piso do Claude Code); o sentinel as lista e diz o que elas não provam.

Escopo: $SCOPE_SHOWN

Uma mudança de lógica: --yes no gpg do probe de assinatura do preflight. O
mktemp cria o arquivo, e gpg --output sobre arquivo existente perguntava
Overwrite? no terminal; a resposta padrão fazia o probe dizer que uma chave
íntegra não conseguia assinar. O controle novo do teste do driver exige
--yes em todo gpg --output do driver.
Ele lê os comandos gpg por comando, não por linha, e o instrumento tem
controle próprio (comentário, heredoc, separadores e caminho absoluto).

release.sh é membro do manifesto ADR-192 (canônico): o sha do driver é
re-pinado no mesmo commit, e o teste que fixa o escopo da anotação é re-pinado
de forma consciente, com o trem da v$PREV_BASE virando asserção negativa.

Verificado na cerimônia, depois de aplicar: patch re-derivado do HEAD byte a
byte igual ao material commitado e ao sha pinado no sentinel; arquivos
aplicados iguais aos da re-derivação; o manifesto conferido pelo mesmo comando
do CI, linha a linha; bash -n; --help anunciando $TARGET_BASE; a suíte do driver
inteira; validate-governance, contamination, verify-counts, ceremony-lint e
check-claude-md-claims. Árvore montada por plumbing a partir das cópias
congeladas, conferida em nomes e bytes antes do commit.

Sentinel: $SENT_LIVE (assinado,
Anchor-SHA $HEAD_SHA,
Patch-SHA256 $PSHA,
chave $SIGNER_FPR, no allowlist $SIGNERS)

Co-Authored-By: $COAUTHOR
EOF_MSG
for l in "governance($PLAN relmeta-142): " "Escopo: $SCOPE_SHOWN" "--yes em todo gpg --output do driver." "Co-Authored-By: $COAUTHOR"; do
  grep -qF -- "$l" "$MSG" || die "a mensagem do commit perdeu a linha: $l"
done
NEWC=$(git commit-tree "$TREE" -p "$HEAD_SHA" -F "$MSG") || die "commit-tree falhou — nada foi commitado"
[ "$(git rev-parse "$NEWC^{tree}")" = "$TREE" ] || die "o commit criado não aponta para a árvore conferida"
[ "$(git rev-parse "$NEWC^1")" = "$HEAD_SHA" ] || die "o commit criado não tem o HEAD pré-cerimônia como pai"
post_commit_fail() {
  printf '\nFAIL: %s\n' "$*" >&9
  printf 'O commit %s está no main LOCAL mas o estado não é o esperado. NÃO faça push.\n' "$(git rev-parse --short HEAD)" >&9
  printf 'Confira com git show --stat HEAD; para desfazer só o commit: git reset --soft %s\n' "$HEAD_SHA" >&9
  printf 'Backup dos originais e logs: %s\n' "$BAK" >&9
  exit 1
}
# SEÇÃO CRÍTICA — o ref avança, a restauração desarma e o índice sincroniza com
# INT/TERM/HUP IGNORADOS: um sinal no meio não pode restaurar arquivos com o
# commit já no main, nem deixar o índice velho sem aviso
trap '' INT TERM HUP
git update-ref -m "ceremony($PLAN): relmeta-142" HEAD "$NEWC" "$HEAD_SHA" \
  || die "o HEAD mudou durante a cerimônia — nada foi commitado"
ARMED=0
trap - EXIT
IDX_SYNC=0
git reset -q -- "$T_REL" "$T_MAN" "$T_TST" "$SENT_LIVE" "$ASC_LIVE" && IDX_SYNC=1
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
[ "$IDX_SYNC" = "1" ] || post_commit_fail "o índice não sincronizou com o commit — quando o git estiver livre: git reset -q -- $T_REL $T_MAN $T_TST $SENT_LIVE $ASC_LIVE"
[ "$(git rev-parse HEAD)" = "$NEWC" ] || post_commit_fail "o HEAD não é o commit criado"
[ "$(git diff-tree -r --no-renames --name-only HEAD~1 HEAD | sort)" = "$EXPECTED" ] || post_commit_fail "o commit não tem exatamente o escopo esperado"
[ -z "$(git status --porcelain --untracked-files=no)" ] || post_commit_fail "a árvore de trabalho não bate com o commit"
printf '\n============================================================\n'
printf ' RELMETA-142 COMMITADA. Falta só:  git push origin main\n'
printf ' Backup dos originais e logs: %s\n' "$BAK"
printf '============================================================\n'
