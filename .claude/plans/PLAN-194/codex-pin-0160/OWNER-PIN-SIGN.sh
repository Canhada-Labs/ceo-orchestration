#!/usr/bin/env bash
# AUTO-GENERATED por .claude/scripts/re-pin-codex.py em 2026-10-02 a partir de
# .claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh (sha256 09ec1cf8f8efc18a...).
# Não edite à mão: regenere o pack. O corpo é o da fonte, byte a byte,
# exceto este cabeçalho, os valores do bloco de constantes e o guard
# TODO(owner).
#
# OWNER-PIN-SIGN.sh — cerimônia do re-pin do codex-cli (PLAN-194). As
# versões, os digests e os caminhos estão todos no bloco de constantes
# abaixo.
# Passos (lidos do molde): P0 pré-condições · 1/7 Anchor-SHA e Data reais no
# sentinel · 2/7 assinar o sentinel (pinentry) · 3/7 aplicar os dois
# arquivos canônicos · 4/7 ADR-182 §5 passo 4 — o pin verifica contra o
# binário instalado · 5/7 bateria de gates (ambiente de allowlist) · 6/7
# árvore do commit: plumbing, bytes congelados, escopo exato · 7/7 commit
# (plumbing: nenhum hook, nenhum editor; o main só avança por
# compare-and-swap).
#
#   bash .claude/plans/PLAN-194/codex-pin-0160/OWNER-PIN-SIGN.sh            # real
#   bash .claude/plans/PLAN-194/codex-pin-0160/OWNER-PIN-SIGN.sh --dry-run  # ensaio
#   bash .claude/plans/PLAN-194/codex-pin-0160/rehearse-pin-0160.sh  # ensaio ponta a ponta (cópia descartável)
#
# O ensaio (`rehearse-pin-0160.sh`) clona o `main` e roda o script de
# verdade nos controles negativos e no p2: com TODO(owner) pendente cada
# caso aborta no guard TODO(owner), não no padrão que espera. Antes do
# ensaio: gere com `--pin-note`, escreva as seções humanas do sentinel e
# commite o pack.
#
# O que cada guard confere e por quê: o README do pack do molde
# (.claude/plans/PLAN-193/codex-pin-0156/README.md).
# Se o GPG reclamar de pinentry:
#   export GPG_TTY=$(tty)
set -euo pipefail

# o ambiente git HERDADO não escolhe repositório, índice, objetos nem config
# desta cerimônia: qualquer variável que o próprio git declara local ao
# repositório (`git rev-parse --local-env-vars` — inclusive o
# GIT_CONFIG_PARAMETERS, que venceria o core.hooksPath abaixo, e o
# GIT_INDEX_FILE, que trocaria o índice conferido) presente no ambiente =
# recusa, antes de qualquer outra operação git
_genv=""
for _v in $(git rev-parse --local-env-vars); do
  if [ -n "${!_v+x}" ]; then _genv="$_genv $_v"; fi
done
if [ -n "$_genv" ]; then
  printf '\nFAIL: variáveis git herdadas redirecionariam esta cerimônia:%s\n      rode num terminal sem elas (unset%s)\n' "$_genv" "$_genv" >&2
  exit 1
fi
# hooks do git e fsmonitor DESLIGADOS nas operações git desta cerimônia e dos
# processos que herdam este ambiente — o verificador e a phase 6; a bateria do
# passo 5 roda em ambiente de allowlist e NÃO herda isto (escopo de linha de
# comando: vence a config de arquivo; nenhuma variável de config herdada
# sobrou para vencê-lo)
export GIT_CONFIG_COUNT=2 \
  GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null \
  GIT_CONFIG_KEY_1=core.fsmonitor GIT_CONFIG_VALUE_1=false

# só dois usos: sem argumento (REAL) ou exatamente `--dry-run`; qualquer outra
# coisa (`--dryrun`, `-n`, argumento a mais) recusa — nunca cai no run real
case "$#:${1:-}" in
  0:) DRY=0 ;;
  1:--dry-run) DRY=1 ;;
  *) printf '\nFAIL: uso: bash %s [--dry-run]  (recebido: %s)\n' "$0" "$*" >&2; exit 1 ;;
esac
# o stderr do TERMINAL, salvo no fd 9: é por ele que falam o die, o restore e
# o trap de saída. Um sinal que chega durante uma chamada de FUNÇÃO com a
# saída redirecionada (a bateria do passo 5: `clean_env ... >log 2>&1`) roda
# o trap ainda dentro desse redirecionamento — pelo fd 2, a mensagem de
# restauração iria para o log, não para o terminal (medido)
exec 9>&2
TOP=$(git rev-parse --show-toplevel) \
  || { printf '\nFAIL: não é um checkout git (rode na raiz do checkout vivo)\n' >&2; exit 1; }
cd "$TOP"
ROOT=$(pwd -P)

# ---------------------------------------------------------------- constantes
PLAN=PLAN-194
PACK_TAG=0160
OLD_VER=0.156.1
NEW_VER=0.160.0
LOWER=0.128.0
OLD_UPPER=0.157.0
NEW_UPPER=0.161.0
NEW_PUBLISHED=2026-10-01
TRIPLE=aarch64-apple-darwin
OLD_SHA=0196e89fe5a7598f816ee54232c3d7c26d75e502ab5cfe2c9240e81d90f7255a
NEW_SHA=112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b
NEW_INTEGRITY='sha512-aefV6cqZA2REZgR//4McyXlp7zLcTti4CI2v3j9IVgNndPBv2kCeNEcz07qeelXcwOdSFPUKb6roA48vZmDgrQ=='
# sha256 dos dois canônicos VIVOS quando o pack foi montado (guard de deriva)
BASE_PIN_SHA256=11514263cc7c219ca0d40ff8bc294f2d69cd5c837e08f80d1e10e0e73148a6f8
BASE_MAN_SHA256=1828a56abf1acec1dadb6484aa271d263faefafe8827a75a4177f778facc933a
# sha256 dos dois `.new` (os bytes que o sentinel assinado declara)
SRC_PIN_SHA256=cb532824ecabd8357d55799a90306dc2e326a7081a937e892df2454856264269
SRC_MAN_SHA256=e356c3611bf9754f9e313ec644463d7bd765c9ab04ff52ea9569bb5c0b9b92dc
GA_TAG=v1.4.2
COAUTHOR='Claude Opus 5.5 (1M context) <noreply@anthropic.com>'
REMOTE_SLUG='Canhada-Labs/ceo-orchestration'
T2_NODE='.claude/hooks/tests/test_codex_templates.py::TestExecpolicyRules::test_live_execpolicy_check'
SIGNERS=.claude/sentinel-signers.txt
SIGNER_REGISTRY=.claude/security/sentinel-signers-registry.yaml
GPG_VERIFY_LIB=.claude/hooks/_lib/gpg_verify.py
SIGNER_REGISTRY_LIB=.claude/hooks/_lib/sentinel_signers.py
D=.claude/plans/$PLAN/codex-pin-$PACK_TAG
# ------------------------------------------------------------ fim constantes

OLD_RANGE=">=$LOWER,<$OLD_UPPER"
NEW_RANGE=">=$LOWER,<$NEW_UPPER"
SENT_LIVE="$D/pin-$PACK_TAG-approved.md"
ASC_LIVE="$SENT_LIVE.asc"
SENT="$SENT_LIVE"
ASC="$ASC_LIVE"
DST_PIN=.claude/governance/codex-cli-pin.txt
DST_MAN=.claude/governance/codex-cli-pin-manifest.json
SRC_PIN="$D/codex-cli-pin.txt.new"
SRC_MAN="$D/codex-cli-pin-manifest.json.new"
VALIDATOR=.github/scripts/validate-pair-rail-verdict.py
PACK_FILES="$SENT_LIVE $SRC_PIN $SRC_MAN $D/OWNER-PIN-SIGN.sh $D/rehearse-pin-$PACK_TAG.sh $D/README.md"
# costuras de TESTE do verificador e do gate: nunca herdadas pelo verificador
# nem pela phase 6 (que precisam do resto do ambiente: rota de auth do codex)
SEAM_UNSET=(-u CEO_PAIR_RAIL_TEST_MODE -u CEO_PAIR_RAIL_PIN_MANIFEST
            -u CEO_PAIR_RAIL_TARGET_TRIPLE -u CEO_PAIR_RAIL_CODEX_BIN
            -u REPO_ROOT_OVERRIDE -u CLAUDE_PROJECT_DIR_NATIVE)
# a bateria roda com ambiente de ALLOWLIST: só isto é herdado (+ PATH e
# CLAUDE_PROJECT_DIR fixados); qualquer outra variável — redirecionamento de
# raiz, opção do pytest, escape hatch de gate — fica de fora por construção
KEEP_ENV="HOME USER LOGNAME SHELL TERM LANG LC_ALL LC_CTYPE TMPDIR PYTHONUSERBASE VIRTUAL_ENV PYENV_ROOT PYENV_VERSION CODEX_HOME"
BAK=$(mktemp -d "${TMPDIR:-/tmp}/pinbak.XXXXXX") \
  || { printf '\nFAIL: mktemp do diretório de backup falhou\n' >&2; exit 1; }
FZ="$BAK/frozen"
mkdir "$FZ" || { printf '\nFAIL: mkdir %s falhou\n' "$FZ" >&2; exit 1; }
ARMED=0

die() { printf '\nFAIL: %s\n' "$*" >&9; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }
# blob_is <objeto git (ex.: "<tree>:caminho")> <arquivo com os bytes esperados>
blob_is() { git cat-file blob "$1" 2>/dev/null | cmp -s - "$2"; }
restore() {
  # restore best-effort num trap de saída: falha vira aviso, nunca silêncio.
  # O ÍNDICE não é tocado: esta cerimônia nunca stageia antes do commit.
  if [ -f "$BAK/pin" ]; then cp "$BAK/pin" "$DST_PIN" || printf "restore do pin falhou\n" >&9; fi
  if [ -f "$BAK/man" ]; then cp "$BAK/man" "$DST_MAN" || printf "restore do manifesto falhou\n" >&9; fi
  # run REAL abortado: o sentinel volta ao byte do HEAD e a assinatura desta
  # rodada sai — senão o próximo run morreria no P0 (modificação rastreada).
  if [ "$DRY" != "1" ] && [ -f "$BAK/sentinel.orig" ]; then
    cp "$BAK/sentinel.orig" "$SENT_LIVE" || printf "restore do sentinel falhou\n" >&9
    rm -f "$ASC_LIVE" || printf "remoção da assinatura parcial falhou\n" >&9
  fi
}
# ARMED=1 só depois do P0 (antes dele nada mudou). INT, TERM e HUP têm trap
# próprio que sai com 130/143/129: no bash 3.2 do macOS o trap de EXIT roda
# nesses sinais, mas num TERM ou HUP com `$?` = status do último comando
# concluído (0), e um cleanup condicionado a rc≠0 — o do molde — não dispara
# (medido; num Ctrl-C, INT ao grupo, o `$?` já chega 130)
trap 'rc=$?; [ $rc -ne 0 ] && [ "$ARMED" = "1" ] && { restore; printf "\nárvore RESTAURADA. Backup e logs em %s\n" "$BAK" >&9; }' EXIT
# [.claude/scripts/re-pin-codex.py] a justificativa humana do pack fica em TODO(owner):
# o run real recusa assinar enquanto restar um; o ensaio só avisa.
if grep -n 'TODO(owner)' "$SENT" "$SRC_PIN" 2>/dev/null; then
  [ "$DRY" = "1" ] || die "TODO(owner) pendente nos materiais (linhas acima) — escreva a justificativa antes de assinar"
  printf '   AVISO: TODO(owner) pendente — o run real vai recusar\n'
fi
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

clean_env_path() {  # clean_env_path <PATH> cmd... — ambiente de allowlist
  local p="$1"; shift
  local a=() v
  for v in $KEEP_ENV; do
    if [ -n "${!v+x}" ]; then a+=("$v=${!v}"); fi
  done
  env -i ${a[@]+"${a[@]}"} PATH="$p" CLAUDE_PROJECT_DIR="$ROOT" "$@"
}
clean_env() { clean_env_path "$PATH" "$@"; }
# O verificador do ADR-182 resolve o manifesto por CLAUDE_PROJECT_DIR (ou o
# cwd) e honra costuras de teste sob CEO_PAIR_RAIL_TEST_MODE=1: aqui ele roda
# SEMPRE ancorado neste checkout e sem nenhuma costura herdada.
verify_pin() {  # $1 = arquivo de saída (stdout JSON); ecoa o rc
  local vrc=0
  env "${SEAM_UNSET[@]}" CLAUDE_PROJECT_DIR="$ROOT" \
    python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)" \
    >"$1" 2>"$1.err" || vrc=$?
  printf '%s' "$vrc"
}
# confere os campos do JSON do verificador: status detail sha256 expected
check_verify_json() {  # $1 arquivo  $2 status  $3 detail  $4 sha256  $5 expected
  python3 - "$1" "$2" "$3" "$4" "$5" "$ROOT/$DST_MAN" "$TRIPLE" <<'PY'
import json, sys
path, status, detail, sha, expected, manifest, triple = sys.argv[1:8]
lines = [l for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]
if not lines:
    raise SystemExit("verificador sem saída")
d = json.loads(lines[-1])
want = {"status": status, "detail": detail, "sha256": sha,
        "expected_sha256": expected, "manifest": manifest,
        "target_triple": triple}
bad = {k: (d.get(k), v) for k, v in want.items() if d.get(k) != v}
if bad:
    raise SystemExit("campos inesperados (obtido, esperado): %r" % (bad,))
print(d["path"])
PY
}
# signatário: as DUAS pernas do guard canônico, com as mesmas funções —
# gpg_verify (GOODSIG+VALIDSIG e fingerprint em $SIGNERS) e, se o registro do
# ADR-121 existir, sentinel_signers.is_valid_signer (chave conhecida, não
# expirada, não revogada; registro ilegível = só a perna legada, como o guard
# faz antes da GENESIS).
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
g = load("gpg_verify_pin", glib)
reg_path = Path(root) / reg_rel
registry = None
if reg_path.exists():
    s = load("sentinel_signers_pin", slib)
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
                         capture_output=True, text=True).stdout
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
verify_sig() { signer_tool verify "$1" "$2"; }
pick_sign_key() { signer_tool pick; }

say "P0 pré-condições"
printf '   backup e logs desta rodada: %s\n' "$BAK"
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo"
# o pinentry de terminal precisa saber QUAL terminal: o run real exporta o
# desta cerimônia (sem isso o gpg falha com «No pinentry» depois do P0)
if [ "$DRY" != "1" ]; then
  GPG_TTY=$(tty) || die "não consegui ler o terminal (tty) para o GPG_TTY"
  export GPG_TTY
fi
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
git remote -v | grep -qF "$REMOTE_SLUG" || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "HEAD != origin/main — pushe ou puxe antes"
# o índice é sincronizado com o commit no fim: um lock pendente falharia lá,
# depois do pinentry — melhor saber agora
IDX_LOCK=$(git rev-parse --git-path index.lock) || die "git rev-parse --git-path falhou"
[ ! -e "$IDX_LOCK" ] || die "há $IDX_LOCK — outro git rodando? (ou lock órfão: confira e remova)"
# o override de rotação de chave do pair-rail-gate NÃO é removido (contrato do
# gate: bypass auditado da cadência da chave de API); fica REGISTRADO na saída
# e na mensagem do commit — a verificação do pin (Gate 4) não depende dele
ROT_OVERRIDE=0
if [ "${CEO_CODEX_KEY_ROTATION_OVERRIDE:-}" = "1" ]; then
  ROT_OVERRIDE=1
  printf '   AVISO: CEO_CODEX_KEY_ROTATION_OVERRIDE=1 no ambiente — a phase 6 vai rodar com o bypass da cadência de rotação, e o commit registra isso\n' >&2
fi
# as rotas de auth da phase 6 (Gates 1 e 2 do pair-rail-gate.sh), conferidas
# AQUI, antes do pinentry, pela MESMA regra do gate e sem executar o codex —
# senão a phase 6 do passo 4 reprovaria depois da assinatura. A phase 6 do
# passo 4 roda de novo e segue sendo a autoridade.
auth_precheck() {
  local last dcmd ts days
  if [ -z "${OPENAI_API_KEY:-}" ]; then
    # rota login: sessão persistida em ~/.codex/auth.json, não vazia
    [ -s "${HOME}/.codex/auth.json" ] \
      || die "sem rota de auth do codex (nem OPENAI_API_KEY nem ~/.codex/auth.json) — o Gate 1 da phase 6 reprovaria DEPOIS do pinentry; rode codex login antes"
    return 0
  fi
  [ "${#OPENAI_API_KEY}" -ge 16 ] \
    || die "OPENAI_API_KEY com ${#OPENAI_API_KEY} caracteres — o Gate 1 da phase 6 reprovaria DEPOIS do pinentry"
  [ "$ROT_OVERRIDE" = "1" ] && return 0
  [ -f docs/rotation-log.md ] || return 0
  last=$(grep -E '^\| [0-9]{4}-[0-9]{2}-[0-9]{2} \| OPENAI_API_KEY' docs/rotation-log.md \
         | tail -n 1 | awk -F'|' '{gsub(/ /,"",$2); print $2}') || last=""
  [ -n "$last" ] || die "OPENAI_API_KEY no ambiente e nenhuma rotação dela em docs/rotation-log.md — o Gate 2 da phase 6 reprovaria DEPOIS do pinentry. Rode sem ela (unset OPENAI_API_KEY; rota login por ~/.codex/auth.json) ou com CEO_CODEX_KEY_ROTATION_OVERRIDE=1 (bypass registrado no commit)"
  if command -v gdate >/dev/null 2>&1; then dcmd=gdate; else dcmd=date; fi
  ts=$($dcmd -d "$last" +%s 2>/dev/null || $dcmd -j -f "%Y-%m-%d" "$last" +%s 2>/dev/null || printf '0')
  [ "$ts" != "0" ] || return 0
  days=$(( ($($dcmd +%s) - ts) / 86400 ))
  [ "$days" -lt 90 ] || die "OPENAI_API_KEY no ambiente e a última rotação registrada é de $last ($days dias; limite 90) — o Gate 2 da phase 6 reprovaria DEPOIS do pinentry. Rode sem ela (unset OPENAI_API_KEY; rota login por ~/.codex/auth.json), ou rotacione a chave e registre em docs/rotation-log.md (commitado e pushado antes), ou use CEO_CODEX_KEY_ROTATION_OVERRIDE=1 (bypass registrado no commit)"
}
auth_precheck
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "há modificação RASTREADA pendente"
# ...e por CONTEÚDO contra o HEAD, sem confiar no índice de quem rodou (os
# bits assume-unchanged/skip-worktree escondem do `git status` uma edição — no
# sentinel, num `.new` ou em qualquer arquivo que a cerimônia lê): um índice
# TEMPORÁRIO lido do HEAD, comparado com a árvore de trabalho inteira
GIT_INDEX_FILE="$BAK/p0-index" git read-tree HEAD || die "read-tree do HEAD num índice temporário falhou"
GIT_INDEX_FILE="$BAK/p0-index" git diff --quiet HEAD -- \
  || die "a árvore de trabalho difere do HEAD sem aparecer no git status (bit assume-unchanged/skip-worktree?) — confira: git ls-files -v | grep -E '^([a-z]|S) '"
for f in $PACK_FILES "$DST_PIN" "$DST_MAN" "$VALIDATOR" "$SIGNERS" "$GPG_VERIFY_LIB" "$SIGNER_REGISTRY_LIB"; do
  [ -f "$f" ] || die "ausente: $f"
done
# os materiais da cerimônia TÊM de estar no HEAD: o que se assina é o que foi revisto
for f in $PACK_FILES; do
  git cat-file -e "HEAD:$f" 2>/dev/null || die "material fora do HEAD (commite e pushe antes): $f"
done
# o subdiretório do pack exige o arquivo do plano no HEAD (PLAN-SCHEMA §1:
# subdiretório órfão reprova o validate-governance do passo 5, já com o pinentry gasto)
[ -n "$(git ls-files -- ".claude/plans/$PLAN-*.md")" ] || die "o plano .claude/plans/$PLAN-*.md não está no HEAD — commite-o junto com os materiais"
# só DEPOIS do GA: a tag existe, é ancestral do HEAD e é o MESMO objeto no remoto
GA_OBJ=$(git rev-parse -q --verify "refs/tags/$GA_TAG") || die "tag $GA_TAG ausente — o re-pin só entra DEPOIS do corte do GA"
git merge-base --is-ancestor "$GA_TAG" HEAD || die "$GA_TAG não é ancestral do HEAD"
GA_REMOTE=$(git ls-remote --tags origin "refs/tags/$GA_TAG" | awk -v r="refs/tags/$GA_TAG" '$2==r{print $1}') \
  || die "git ls-remote do origin falhou (rede?) — nada foi alterado"
[ "$GA_REMOTE" = "$GA_OBJ" ] || die "$GA_TAG no remoto ($GA_REMOTE) difere da local ($GA_OBJ) — o GA foi publicado?"
# os destinos TÊM de ser canônicos — se o oráculo disser 0, esta cerimônia é desnecessária
for f in "$DST_PIN" "$DST_MAN"; do
  v=$(clean_env python3 .claude/hooks/check_canonical_edit.py --is-canonical "$f" 2>/dev/null | awk '{print $2}') \
    || die "o oráculo --is-canonical falhou para $f"
  [ "$v" = "1" ] || die "$f NÃO é canônico (oráculo=$v) — não use esta cerimônia"
done
# guard de DERIVA: os vivos são os de quando o pack foi montado; os .new são os declarados
[ "$(sha256f "$DST_PIN")" = "$BASE_PIN_SHA256" ] || die "$DST_PIN mudou depois que o pack foi montado — o .new reverteria a mudança em silêncio; remonte o pack"
[ "$(sha256f "$DST_MAN")" = "$BASE_MAN_SHA256" ] || die "$DST_MAN mudou depois que o pack foi montado — o .new reverteria a mudança em silêncio; remonte o pack"
# os .new são CONGELADOS aqui: tudo daqui em diante (aplicar, montar o commit)
# lê a cópia congelada, conferida contra o sha declarado
cp "$SRC_PIN" "$FZ/pin" && cp "$SRC_MAN" "$FZ/man" || die "não consegui congelar os .new (em $FZ)"
[ "$(sha256f "$FZ/pin")" = "$SRC_PIN_SHA256" ] || die "$SRC_PIN não é o byte declarado no script"
[ "$(sha256f "$FZ/man")" = "$SRC_MAN_SHA256" ] || die "$SRC_MAN não é o byte declarado no script"
for v in "$BASE_PIN_SHA256" "$BASE_MAN_SHA256" "$SRC_PIN_SHA256" "$SRC_MAN_SHA256" "$NEW_SHA" "$NEW_INTEGRITY" "$NEW_RANGE"; do
  grep -qF -- "$v" "$SENT" || die "o sentinel não declara $v — script e sentinel divergem"
done
command -v codex >/dev/null 2>&1 || die "codex não está no PATH — instale o $NEW_VER antes (README)"
# o binário instalado TEM de ser o que o manifesto novo pina — conferido por
# HASH contra o manifesto VIVO, sem executar o payload (M4)
prc=$(verify_pin "$BAK/pre.out")
if [ "$prc" = "0" ]; then
  die "o codex instalado ainda é o que o manifesto vivo pina ($OLD_VER) — rode antes: npm i -g @openai/codex@$NEW_VER"
fi
[ "$prc" = "1" ] || { cat "$BAK/pre.out" "$BAK/pre.out.err" >&2; die "verificador saiu rc=$prc (infra) — confira a instalação"; }
check_verify_json "$BAK/pre.out" mismatch payload_sha256_mismatch "$NEW_SHA" "$OLD_SHA" >/dev/null \
  || { cat "$BAK/pre.out" >&2; die "o payload instalado NÃO é o $NEW_VER medido no registry — não assine"; }
[ ! -e "$ASC_LIVE" ] || die "já existe $ASC_LIVE — esta cerimônia já rodou? confira com git log"
# a chave que vai assinar está no allowlist — ANTES de gastar o pinentry
SIGN_KEY=$(pick_sign_key) || die "sem chave autorizada para assinar (allowlist: $SIGNERS)"
cp "$DST_PIN" "$BAK/pin" && cp "$DST_MAN" "$BAK/man" && cp "$SENT_LIVE" "$BAK/sentinel.orig" \
  || die "não consegui copiar os originais para o backup $BAK"
ARMED=1
printf '   OK: main sincronizado, árvore limpa, materiais no HEAD, %s publicado e ancestral,\n' "$GA_TAG"
printf '       2 destinos canônicos sem deriva, payload instalado = %s (%s...),\n' "$NEW_VER" "${NEW_SHA%"${NEW_SHA#????????}"}"
printf '       chave de assinatura no allowlist: %s\n' "$SIGN_KEY"
if [ "$DRY" != "1" ]; then printf '       GPG_TTY=%s\n' "$GPG_TTY"; fi

say "1/7 Anchor-SHA e Data reais no sentinel"
HEAD_SHA=$(git rev-parse HEAD) || die "git rev-parse HEAD falhou"
TODAY=$(date +%Y-%m-%d) || die "date falhou"
# o ENSAIO nunca muta material persistente: trabalha sobre uma cópia, senão
# deixaria o sentinel sujo e o run real abortaria no P0 (medido na S352).
if [ "$DRY" = "1" ]; then
  cp "$SENT" "$BAK/sentinel.md" || die "não consegui copiar o sentinel para o ensaio"
  SENT="$BAK/sentinel.md"; ASC="$SENT.asc"
fi
python3 - "$SENT" "$HEAD_SHA" "$TODAY" <<'PY' || die "não consegui gravar Anchor-SHA e Data no sentinel"
import sys, pathlib, re
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
for key, val in (("Anchor-SHA", sys.argv[2]), ("Data", sys.argv[3])):
    t, n = re.subn(r'^' + key + r':.*$', key + ': ' + val, t, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("linha %s não encontrada" % key)
p.write_text(t, encoding="utf-8")
PY
grep -q "^Anchor-SHA: $HEAD_SHA\$" "$SENT" || die "Anchor-SHA não gravou"
grep -q "^Data: $TODAY\$" "$SENT" || die "Data não gravou"
printf '   Anchor-SHA = %s   Data = %s\n' "$HEAD_SHA" "$TODAY"

say "2/7 assinar o sentinel (pinentry)"
SIGNER_FPR="(ensaio: sem assinatura)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura (chave: %s)\n' "$SIGN_KEY"
  cp "$SENT" "$FZ/sentinel" || die "não consegui congelar o sentinel"
else
  gpg --armor --detach-sign --local-user "$SIGN_KEY" "$SENT" \
    || die "assinatura falhou (GPG_TTY=$GPG_TTY) — se o gpg reclamou de pinentry, confira a pinentry do gpg-agent e rode de novo"
  # o par assinado é CONGELADO e verificado na cópia congelada: é dela que o
  # commit é montado, então nada que mexa no arquivo de trabalho depois entra
  cp "$SENT" "$FZ/sentinel" && cp "$ASC" "$FZ/asc" || die "não consegui congelar o par assinado"
  SIGNER_FPR=$(verify_sig "$FZ/sentinel" "$FZ/asc") || die "a assinatura não verifica contra $SIGNERS"
  printf '   assinado por %s (no allowlist)\n' "$SIGNER_FPR"
fi

say "3/7 aplicar os dois arquivos canônicos"
for d in "$DST_PIN" "$DST_MAN"; do if [ -L "$d" ]; then die "destino é symlink: $d"; fi; done
cp "$FZ/pin" "$DST_PIN" || die "não consegui aplicar $DST_PIN"
cp "$FZ/man" "$DST_MAN" || die "não consegui aplicar $DST_MAN"
[ "$(sha256f "$DST_PIN")" = "$SRC_PIN_SHA256" ] || die "o pin aplicado não é o byte do .new"
[ "$(sha256f "$DST_MAN")" = "$SRC_MAN_SHA256" ] || die "o manifesto aplicado não é o byte do .new"
# a semântica, pela função do PRÓPRIO validador do release.yml (primeira linha
# com range) e pelo leitor de última linha: os dois só concordam enquanto o
# arquivo tiver UMA linha fora de comentário
python3 - "$VALIDATOR" "$DST_PIN" "$DST_MAN" "$NEW_RANGE" "$LOWER" "$NEW_UPPER" "$OLD_VER" "$NEW_VER" "$NEW_INTEGRITY" "$TRIPLE" "$NEW_SHA" "$BAK/man" <<'PY' || die "a semântica do pin/manifesto aplicados reprovou"
import importlib.util, json, sys
from pathlib import Path
(vpath, pin, man, new_range, lower, upper, old_v, new_v, integ, triple,
 new_sha, base_man) = sys.argv[1:13]
spec = importlib.util.spec_from_file_location("validator_prv", vpath)
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
lo, hi = v.parse_pin_range(Path(pin))
assert (lo, hi) == (lower, upper), ("range do validador", lo, hi)
assert v.semver_in_range(new_v, lo, hi), ("versão nova fora do range", new_v)
assert v.semver_in_range(old_v, lo, hi), ("versão antiga fora do range (não é widen-upper-only)", old_v)
body = [l.strip() for l in open(pin, encoding="utf-8").read().splitlines()
        if l.strip() and not l.lstrip().startswith("#")]
assert body == [new_range], ("linhas fora de comentário", body)
m = json.load(open(man, encoding="utf-8")); b = json.load(open(base_man, encoding="utf-8"))
assert m.get("schema") == 1 and m.get("package_version") == new_v, "versão do manifesto"
assert m.get("npm_integrity") == integ, "npm_integrity"
assert sorted(m["payloads"]) == [triple], ("triples", sorted(m["payloads"]))
assert m["payloads"][triple]["sha256"] == new_sha, "sha256 do payload"
assert m["payloads"][triple]["path"] == b["payloads"][triple]["path"], "path do payload mudou"
PY
printf '   aplicados: range %s -> %s (inferior inalterado), manifesto %s\n' "$OLD_RANGE" "$NEW_RANGE" "$NEW_VER"

say "4/7 ADR-182 §5 passo 4 — o pin verifica contra o binário instalado"
vrc=$(verify_pin "$BAK/verify.out")
[ "$vrc" = "0" ] || { cat "$BAK/verify.out" "$BAK/verify.out.err" >&2; die "--verify-codex-pin reprovou (rc=$vrc) — o binário instalado NÃO é o que o manifesto pina"; }
VERIFIED_PAYLOAD=$(check_verify_json "$BAK/verify.out" verified ok "$NEW_SHA" "$NEW_SHA") \
  || { cat "$BAK/verify.out" >&2; die "--verify-codex-pin saiu 0 com campos inesperados"; }
[ -f "$VERIFIED_PAYLOAD" ] && [ "$(sha256f "$VERIFIED_PAYLOAD")" = "$NEW_SHA" ] || die "payload resolvido não confere: $VERIFIED_PAYLOAD"
# tudo que EXECUTA o codex daqui em diante (gate da phase 6, sonda T2) roda o
# payload verificado pelo caminho resolvido — como o hook do rail — e não o
# launcher do PATH, que o manifesto não pina
mkdir "$BAK/verified-bin" && ln -s "$VERIFIED_PAYLOAD" "$BAK/verified-bin/codex" \
  || die "não consegui montar o link do payload verificado"
VPATH="$BAK/verified-bin:$PATH"
# (CEO_PAIR_RAIL_DISABLE NÃO é removido: se estiver ligado, o gate sai 2 e a
# cerimônia aborta, como no molde — um re-pin não se verifica com o rail desligado)
env "${SEAM_UNSET[@]}" PATH="$VPATH" CLAUDE_PROJECT_DIR="$ROOT" \
  bash .claude/scripts/local/pair-rail-gate.sh --phase 6 >"$BAK/phase6.out" 2>&1 \
  || { tail -n 25 "$BAK/phase6.out" >&2; die "pair-rail-gate --phase 6 reprovou"; }
grep -qF "codex-cli $NEW_VER" "$BAK/phase6.out" || { tail -n 25 "$BAK/phase6.out" >&2; die "phase 6 não reportou codex-cli $NEW_VER"; }
printf '   verified (%s); pair-rail-gate --phase 6 OK com codex-cli %s (payload verificado)\n' "$DST_MAN" "$NEW_VER"
ROT_NOTE=""
if [ "$ROT_OVERRIDE" = "1" ]; then
  ROT_NOTE=" (com CEO_CODEX_KEY_ROTATION_OVERRIDE=1: cadência de rotação da chave de API NÃO conferida)"
  printf '   AVISO: phase 6 rodou%s\n' "$ROT_NOTE" >&2
fi

say "5/7 bateria de gates (ambiente de allowlist)"
clean_env bash .claude/scripts/validate-governance.sh >"$BAK/gov.out" 2>&1 \
  || { tail -n 40 "$BAK/gov.out" >&2; die "validate-governance reprovou (log: $BAK/gov.out)"; }
grep -q 'Errors:   0' "$BAK/gov.out" || die "governance com erros (log: $BAK/gov.out)"
clean_env python3 .claude/scripts/check_contamination.py >"$BAK/contam.out" 2>&1 || { tail -n 20 "$BAK/contam.out" >&2; die "contamination reprovou"; }
clean_env bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >"$BAK/counts.out" 2>&1 || { tail -n 20 "$BAK/counts.out" >&2; die "verify-counts reprovou"; }
clean_env python3 .claude/scripts/check-ceremony-script.py >"$BAK/lint.out" 2>&1 || { tail -n 20 "$BAK/lint.out" >&2; die "ceremony-lint reprovou"; }
# os testes que LEEM o pin vivo (acoplamento fixture<->pin; veredito com os
# pins vivos pelo validador do step 15; a sonda T2 que executa o codex já
# verificado). `-rA` lista cada teste com o resultado: a sonda T2 PULADA
# deixaria o rc em 0 — por isso ela tem de constar PASSED.
clean_env_path "$VPATH" python3 -m pytest -q -rA -p no:cacheprovider \
    .claude/hooks/tests/test_adapter_golden.py \
    .claude/scripts/tests/test_release_bump_sites.py \
    .claude/hooks/tests/test_codex_templates.py \
    -k "PinCoupling or ci_validator or codex_templates" >"$BAK/pytest.out" 2>&1 \
  || { tail -n 30 "$BAK/pytest.out" >&2; die "testes que leem o pin reprovaram (log: $BAK/pytest.out)"; }
grep -qxF "PASSED $T2_NODE" "$BAK/pytest.out" \
  || { tail -n 15 "$BAK/pytest.out" >&2; die "a sonda T2 ($T2_NODE) não consta PASSED — pulada ou ausente (log: $BAK/pytest.out)"; }
# a bateria não pode ter mexido em NADA rastreado fora do escopo...
OUTSIDE=$(git status --porcelain --untracked-files=no | awk '{print $NF}' | grep -vxF -e "$DST_PIN" -e "$DST_MAN" -e "$SENT_LIVE" || printf '')
[ -z "$OUTSIDE" ] || die "a bateria modificou arquivo rastreado fora do escopo:
$OUTSIDE"
# ...nem nos arquivos do escopo: o de trabalho tem de ser o congelado
cmp -s "$DST_PIN" "$FZ/pin" || die "$DST_PIN mudou durante a bateria"
cmp -s "$DST_MAN" "$FZ/man" || die "$DST_MAN mudou durante a bateria"
cmp -s "$SENT" "$FZ/sentinel" || die "o sentinel mudou depois da assinatura"
if [ "$DRY" != "1" ]; then cmp -s "$ASC" "$FZ/asc" || die "a assinatura mudou depois de gerada"; fi
printf '   governance 0 erros, contamination OK, counts OK, ceremony-lint OK, testes do pin OK (T2 PASSED)\n'

say "6/7 árvore do commit: plumbing, bytes congelados, escopo exato"
# índice TEMPORÁRIO (o de quem rodou não é tocado) + blobs gravados SEM filtros
TMPIDX="$BAK/index"
GIT_INDEX_FILE="$TMPIDX" git read-tree "$HEAD_SHA" || die "read-tree do HEAD no índice temporário falhou"
add_blob() {  # add_blob <caminho no repo> <arquivo congelado>
  local b
  b=$(git hash-object -w --no-filters -- "$2") || die "hash-object de $2 falhou"
  GIT_INDEX_FILE="$TMPIDX" git update-index --add --cacheinfo "100644,$b,$1" \
    || die "update-index de $1 no índice temporário falhou"
}
add_blob "$DST_PIN" "$FZ/pin"
add_blob "$DST_MAN" "$FZ/man"
if [ "$DRY" = "1" ]; then
  EXPECTED=$(printf '%s\n' "$DST_PIN" "$DST_MAN" | sort)
else
  add_blob "$SENT_LIVE" "$FZ/sentinel"
  add_blob "$ASC_LIVE" "$FZ/asc"
  EXPECTED=$(printf '%s\n' "$DST_PIN" "$DST_MAN" "$SENT_LIVE" "$ASC_LIVE" | sort)
fi
TREE=$(GIT_INDEX_FILE="$TMPIDX" git write-tree) || die "write-tree do índice temporário falhou"
TOUCHED=$(git diff-tree -r --no-renames --name-only "$HEAD_SHA" "$TREE" | sort) || die "diff-tree da árvore montada falhou"
[ "$TOUCHED" = "$EXPECTED" ] || die "árvore diferente do escopo exato:
--- na árvore
$TOUCHED
--- esperado
$EXPECTED"
blob_is "$TREE:$DST_PIN" "$FZ/pin" || die "o blob de $DST_PIN na árvore não é o byte do .new"
blob_is "$TREE:$DST_MAN" "$FZ/man" || die "o blob de $DST_MAN na árvore não é o byte do .new"
if [ "$DRY" != "1" ]; then
  blob_is "$TREE:$SENT_LIVE" "$FZ/sentinel" || die "o blob do sentinel na árvore não é o byte assinado"
  blob_is "$TREE:$ASC_LIVE" "$FZ/asc" || die "o blob da assinatura na árvore não é o gerado"
fi
printf '%s\n' "$TOUCHED" | sed 's/^/   /'

if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada commitado; desfazendo"
  restore
  [ -z "$(git status --porcelain --untracked-files=no)" ] || die "o ensaio deixou a árvore suja"
  printf '\nEnsaio OK. Rode sem --dry-run para valer.\n'
  trap - EXIT; exit 0
fi

say "7/7 commit (plumbing: nenhum hook, nenhum editor; o main só avança por compare-and-swap)"
# o par assinado ainda verifica, sobre as MESMAS cópias que viraram blobs
SIGNER_FPR2=$(verify_sig "$FZ/sentinel" "$FZ/asc") || die "a assinatura congelada deixou de verificar"
[ "$SIGNER_FPR2" = "$SIGNER_FPR" ] || die "fingerprint mudou entre as verificações"
MSG="$BAK/commit-msg.txt"
{
  printf 'ceremony(%s): re-pin codex-cli %s -> %s\n\n' "$PLAN" "$OLD_VER" "$NEW_VER"
  printf 'O codex-cli %s saiu no npm em %s; com o manifesto de versão exata do\n' "$NEW_VER" "$NEW_PUBLISHED"
  printf 'ADR-182, instalar o binário novo sem este re-pin deixa o pair-rail\n'
  printf 'fail-CLOSED (--verify-codex-pin -> payload_sha256_mismatch).\n\n'
  printf 'Digests tirados do tarball real do registry (npm pack + shasum sobre o\n'
  printf 'binário extraído; o sha512 do tarball confere com o dist.integrity do\n'
  printf 'artefato de PLATAFORMA, que é o que o manifesto grava — ADR-182 §5 passo 2).\n'
  printf 'Antes de assinar, a cerimônia conferiu por hash, sem executar o payload,\n'
  printf 'que o binário instalado é o %s medido (sha256 %s).\n\n' "$NEW_VER" "$NEW_SHA"
  printf 'Widen-upper-only (%s -> %s; inferior inalterado em >=%s), depois da\n' "<$OLD_UPPER" "<$NEW_UPPER" "$LOWER"
  printf 'tag %s: o step 15 do release.yml confere o veredito do GA contra o\n' "$GA_TAG"
  printf 'manifesto da árvore tagueada. ADR-111 §2 (repetido no ADR-182 §5 passo 5):\n'
  printf 'o corpus só reabre com desvio MEDIDO de catch_rate > 5 pp; nenhuma rodada\n'
  printf 'de corpus foi feita (gatilho não avaliado, não aprovado); o checklist do\n'
  printf 'ADR-161 fica para a wave de substrato — os motivos medidos estão no sentinel.\n\n'
  printf 'Consequência DECLARADA: troca o INSTRUMENTO do rail — medições antes/depois\n'
  printf 'deste commit não são comparáveis.\n\n'
  printf 'Verificado na cerimônia, depois de aplicar: --verify-codex-pin = verified;\n'
  printf 'pair-rail-gate.sh --phase 6 OK com codex-cli %s%s; bateria e testes que leem\n' "$NEW_VER" "$ROT_NOTE"
  printf 'o pin verdes, com a sonda T2 PASSED (gate e sonda executando o payload\n'
  printf 'verificado); árvore montada por plumbing a partir das cópias congeladas dos\n'
  printf 'bytes verificados e assinados, conferida em nomes e bytes antes do commit.\n\n'
  printf 'Sentinel: %s (assinado, Anchor-SHA %s,\n' "$SENT_LIVE" "$HEAD_SHA"
  printf 'chave %s, no allowlist %s)\n\n' "$SIGNER_FPR" "$SIGNERS"
  printf 'Co-Authored-By: %s\n' "$COAUTHOR"
} >"$MSG" || die "não consegui escrever a mensagem do commit em $MSG"
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
# SEÇÃO CRÍTICA — o ref avança, a restauração desarma e o índice sincroniza
# com INT/TERM/HUP IGNORADOS: um sinal no meio não pode restaurar arquivos com
# o commit já no main, nem deixar o índice velho sem aviso
trap '' INT TERM HUP
# compare-and-swap: só avança se o HEAD ainda for o da cerimônia (falhou =
# nada commitado; o trap de EXIT, ainda armado, restaura a árvore)
git update-ref -m "ceremony($PLAN): re-pin codex-cli $OLD_VER -> $NEW_VER" HEAD "$NEWC" "$HEAD_SHA" \
  || die "o HEAD mudou durante a cerimônia — nada foi commitado"
# a partir daqui a árvore bate com o commit: nada é restaurado
ARMED=0
trap - EXIT
# o índice de quem rodou passa a refletir o commit (só os 4 caminhos do escopo)
IDX_SYNC=0
git reset -q -- "$DST_PIN" "$DST_MAN" "$SENT_LIVE" "$ASC_LIVE" && IDX_SYNC=1
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
[ "$IDX_SYNC" = "1" ] || post_commit_fail "o índice não sincronizou com o commit — quando o git estiver livre: git reset -q -- $DST_PIN $DST_MAN $SENT_LIVE $ASC_LIVE"
[ "$(git rev-parse HEAD)" = "$NEWC" ] || post_commit_fail "o HEAD não é o commit criado"
[ "$(git diff-tree -r --no-renames --name-only HEAD~1 HEAD | sort)" = "$EXPECTED" ] || post_commit_fail "o commit não tem exatamente o escopo esperado"
[ -z "$(git status --porcelain --untracked-files=no)" ] || post_commit_fail "a árvore de trabalho não bate com o commit"
printf '\n============================================================\n'
printf ' RE-PIN COMMITADO (%s -> %s). Falta só:  git push origin main\n' "$OLD_VER" "$NEW_VER"
printf ' Backup dos originais e logs: %s\n' "$BAK"
printf '============================================================\n'
