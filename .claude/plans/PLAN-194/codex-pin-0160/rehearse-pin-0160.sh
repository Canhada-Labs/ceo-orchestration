#!/usr/bin/env bash
# AUTO-GENERATED por .claude/scripts/re-pin-codex.py em 2026-10-02 a partir de
# .claude/plans/PLAN-193/codex-pin-0156/rehearse-pin-0156.sh (sha256 f84eb5f0c3d9ae96...).
# Não edite à mão: regenere o pack. O corpo é o da fonte, byte a byte,
# exceto este cabeçalho.
#
# rehearse-pin-0160.sh — ensaio ponta a ponta da cerimônia do re-pin, numa
# cópia descartável; as constantes vêm do OWNER-PIN-SIGN.sh deste diretório.
# O que o ensaio faz, passo a passo: o cabeçalho de
# .claude/plans/PLAN-193/codex-pin-0156/rehearse-pin-0156.sh.
#
#   bash .claude/plans/PLAN-194/codex-pin-0160/rehearse-pin-0160.sh
set -euo pipefail

# nenhuma variável git herdada local ao repositório (GIT_DIR, GIT_INDEX_FILE,
# GIT_CONFIG_PARAMETERS...) pode rotear um git deste ensaio para o repo de
# origem; todo git daqui em diante também roda no ambiente limpo E()
_genv=""
for _v in $(git rev-parse --local-env-vars); do
  if [ -n "${!_v+x}" ]; then _genv="$_genv $_v"; fi
done
[ -z "$_genv" ] || { printf 'variáveis git herdadas:%s — rode sem elas (unset%s)\n' "$_genv" "$_genv" >&2; exit 2; }

PACK_DIR=$(cd "$(dirname "$0")" && pwd -P)
SRC_REPO=$(cd "$PACK_DIR/../../../.." && pwd -P)
SIGN_SRC="$PACK_DIR/OWNER-PIN-SIGN.sh"
[ -f "$SIGN_SRC" ] || { printf 'OWNER-PIN-SIGN.sh ausente em %s\n' "$PACK_DIR" >&2; exit 2; }
# `-e`, não `-d`: num worktree do git o `.git` é um ARQUIVO (gitdir: ...)
[ -e "$SRC_REPO/.git" ] || { printf 'não achei o repo em %s\n' "$SRC_REPO" >&2; exit 2; }

# as constantes vêm do PRÓPRIO script de cerimônia (fonte única)
const() { sed -n "s/^$1=//p" "$SIGN_SRC" | head -n 1 | sed "s/^'//; s/'\$//"; }
PLAN=$(const PLAN); PACK_TAG=$(const PACK_TAG)
OLD_VER=$(const OLD_VER); NEW_VER=$(const NEW_VER)
LOWER=$(const LOWER); NEW_UPPER=$(const NEW_UPPER); OLD_UPPER=$(const OLD_UPPER)
NEW_SHA=$(const NEW_SHA); OLD_SHA=$(const OLD_SHA); NEW_INTEGRITY=$(const NEW_INTEGRITY)
TRIPLE=$(const TRIPLE); GA_TAG=$(const GA_TAG); REMOTE_SLUG=$(const REMOTE_SLUG)
T2_NODE=$(const T2_NODE)
BASE_PIN_SHA256=$(const BASE_PIN_SHA256); BASE_MAN_SHA256=$(const BASE_MAN_SHA256)
SRC_PIN_SHA256=$(const SRC_PIN_SHA256); SRC_MAN_SHA256=$(const SRC_MAN_SHA256)
for v in PLAN PACK_TAG OLD_VER NEW_VER LOWER NEW_UPPER OLD_UPPER NEW_SHA OLD_SHA NEW_INTEGRITY TRIPLE GA_TAG REMOTE_SLUG T2_NODE BASE_PIN_SHA256 BASE_MAN_SHA256 SRC_PIN_SHA256 SRC_MAN_SHA256; do
  [ -n "${!v}" ] || { printf 'constante %s não lida do OWNER-PIN-SIGN.sh\n' "$v" >&2; exit 2; }
done
REL_PACK=".claude/plans/$PLAN/codex-pin-$PACK_TAG"
SIGN_REL="$REL_PACK/OWNER-PIN-SIGN.sh"
SENT_REL="$REL_PACK/pin-$PACK_TAG-approved.md"
PACK_NAMES="OWNER-PIN-SIGN.sh codex-cli-pin.txt.new codex-cli-pin-manifest.json.new pin-$PACK_TAG-approved.md README.md rehearse-pin-$PACK_TAG.sh"
DST_PIN=.claude/governance/codex-cli-pin.txt
DST_MAN=.claude/governance/codex-cli-pin-manifest.json
PAYLOAD_REL="lib/node_modules/@openai/codex/node_modules/@openai/codex-darwin-arm64/vendor/$TRIPLE/bin/codex"

# o codex GLOBAL (o do PATH de quem chama): é ele que a cerimônia executa
GLOBAL_LAUNCHER=${REHEARSE_GLOBAL_CODEX:-$(command -v codex 2>/dev/null || printf '')}
[ -n "$GLOBAL_LAUNCHER" ] && [ -x "$GLOBAL_LAUNCHER" ] \
  || { printf 'codex global ausente do PATH — o ensaio exige o %s já instalado\n' "$NEW_VER" >&2; exit 2; }
GLOBAL_CODEX_DIR=$(cd "$(dirname "$GLOBAL_LAUNCHER")" && pwd -P)
GLOBAL_LAUNCHER="$GLOBAL_CODEX_DIR/$(basename "$GLOBAL_LAUNCHER")"

BASE=${REHEARSE_BASE:-${TMPDIR:-/tmp}}
RUN=$(mktemp -d "${BASE%/}/rehearse-$PACK_TAG.XXXXXX")
SOCK=$(mktemp -d "${REHEARSE_SOCK_BASE:-${TMPDIR:-/tmp}}/g.XXXXXX")
chmod 700 "$SOCK"
mkdir -p "$RUN/home/.codex" "$RUN/tmp" "$RUN/logs" "$RUN/gnupg"
chmod 700 "$RUN/gnupg"
LOGS="$RUN/logs"

PASS=0; FAIL=0; TALLY="$RUN/tally.txt"; : >"$TALLY"
ok() { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$*" | tee -a "$TALLY"; }
ko() { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$*" | tee -a "$TALLY"; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else ko "$d"; fi; }
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }
sri() { printf 'sha512-%s' "$(openssl dgst -sha512 -binary "$1" | base64 | tr -d '\n')"; }
cleanup() {
  GNUPGHOME="$RUN/gnupg" gpgconf --kill gpg-agent >/dev/null 2>&1 || printf 'aviso: gpg-agent do ensaio não parou\n' >&2
  for s in S.gpg-agent S.gpg-agent.extra S.gpg-agent.browser S.gpg-agent.ssh; do
    if [ -S "$SOCK/$s" ]; then rm -f "$SOCK/$s"; fi
  done
  rmdir "$SOCK" 2>/dev/null || printf 'aviso: %s não ficou vazio\n' "$SOCK" >&2
}
trap 'rc=$?; cleanup; exit $rc' EXIT

printf 'ensaio em %s\n' "$RUN"
printf 'codex global (PATH da cerimônia): %s\n' "$GLOBAL_LAUNCHER"
GLOBAL_LINK_BEFORE=$(readlink "$GLOBAL_LAUNCHER" || printf '(não é symlink)')

# ------------------------------------------------ 1. cópias do registry (sem instalar)
fetch_prefix() {  # fetch_prefix <versão> <dir> — npm pack + layout do global em <dir>/prefix
  local v="$1" d="$2"
  mkdir -p "$d/dl" "$d/main" "$d/plat" "$d/npm-cache"
  ( cd "$d/dl" && npm_config_cache="$d/npm-cache" npm pack --silent "@openai/codex@$v" "@openai/codex@$v-darwin-arm64" >"$LOGS/npm-pack-$v.out" 2>&1 )
  tar xzf "$d/dl/openai-codex-$v.tgz" -C "$d/main"
  tar xzf "$d/dl/openai-codex-$v-darwin-arm64.tgz" -C "$d/plat"
  mkdir -p "$d/prefix/bin" "$d/prefix/lib/node_modules/@openai"
  mv "$d/main/package" "$d/prefix/lib/node_modules/@openai/codex"
  mkdir -p "$d/prefix/lib/node_modules/@openai/codex/node_modules/@openai"
  mv "$d/plat/package" "$d/prefix/lib/node_modules/@openai/codex/node_modules/@openai/codex-darwin-arm64"
  ln -s ../lib/node_modules/@openai/codex/bin/codex.js "$d/prefix/bin/codex"
}
if [ -n "${REHEARSE_CODEX_PREFIX:-}" ]; then
  PREFIX=$(cd "$REHEARSE_CODEX_PREFIX" && pwd -P)
  printf 'AVISO: prefixo novo pronto (%s) — o sha512 do tarball NÃO é conferido nesta rodada\n' "$PREFIX"
else
  fetch_prefix "$NEW_VER" "$RUN/npm-new"
  PREFIX="$RUN/npm-new/prefix"
  check "tarball de plataforma $NEW_VER confere com o npm_integrity pinado" \
    [ "$(sri "$RUN/npm-new/dl/openai-codex-$NEW_VER-darwin-arm64.tgz")" = "$NEW_INTEGRITY" ]
fi
check "cópia do registry: payload tem o sha256 pinado ($NEW_VER)" [ "$(sha256f "$PREFIX/$PAYLOAD_REL")" = "$NEW_SHA" ]
LIVE_INTEGRITY=$(sed -n 's/^ *"npm_integrity": "\([^"]*\)".*/\1/p' "$SRC_REPO/$DST_MAN")
if [ -n "${REHEARSE_OLD_CODEX_PREFIX:-}" ]; then
  OLD_PREFIX=$(cd "$REHEARSE_OLD_CODEX_PREFIX" && pwd -P)
  printf 'AVISO: prefixo antigo pronto (%s) — o sha512 do tarball NÃO é conferido nesta rodada\n' "$OLD_PREFIX"
else
  fetch_prefix "$OLD_VER" "$RUN/npm-old"
  OLD_PREFIX="$RUN/npm-old/prefix"
  check "tarball de plataforma $OLD_VER confere com o npm_integrity do manifesto vivo" \
    [ "$(sri "$RUN/npm-old/dl/openai-codex-$OLD_VER-darwin-arm64.tgz")" = "$LIVE_INTEGRITY" ]
fi
check "codex antigo ($OLD_VER): payload tem o sha256 do manifesto vivo" [ "$(sha256f "$OLD_PREFIX/$PAYLOAD_REL")" = "$OLD_SHA" ]
# um codex que NÃO é nenhum dos dois pinados: payload falso, só para o P0
# conferir por hash — se for EXECUTADO, deixa um marcador (M4 violado)
FAKE_PREFIX="$RUN/fake/prefix"
mkdir -p "$FAKE_PREFIX/bin" "$FAKE_PREFIX/lib/node_modules/@openai/codex/bin" "$(dirname "$FAKE_PREFIX/$PAYLOAD_REL")"
cp "$PREFIX/lib/node_modules/@openai/codex/bin/codex.js" "$FAKE_PREFIX/lib/node_modules/@openai/codex/bin/codex.js"
printf '#!/bin/sh\ntouch "%s/fake-codex-ran"\nexit 97\n' "$RUN" >"$FAKE_PREFIX/$PAYLOAD_REL"
chmod 755 "$FAKE_PREFIX/$PAYLOAD_REL"
ln -s ../lib/node_modules/@openai/codex/bin/codex.js "$FAKE_PREFIX/bin/codex"

# ferramentas: diretórios das que a cerimônia usa; o codex resolvido é o do
# primeiro diretório de cada PATH abaixo
TOOLPATH=""
for t in node gpg git python3 shasum openssl script awk sed; do
  d=$(dirname "$(command -v "$t")")
  case ":$TOOLPATH:" in *":$d:"*) ;; *) TOOLPATH="${TOOLPATH:+$TOOLPATH:}$d" ;; esac
done
TOOLPATH="$TOOLPATH:/usr/bin:/bin:/usr/sbin:/sbin"
NEW_PATH="$GLOBAL_CODEX_DIR:$TOOLPATH"
OLD_PATH="$OLD_PREFIX/bin:$TOOLPATH"
FAKE_PATH="$FAKE_PREFIX/bin:$TOOLPATH"
USERBASE=$(python3 -m site --user-base)
printf '{"rehearsal": true}\n' >"$RUN/home/.codex/auth.json"

# ambiente limpo: nada do shell (nem CLAUDE_*, nem CEO_*) vaza para a cerimônia
E() {  # E <PATH> [VAR=val ...] -- cmd...
  local p="$1"; shift
  env -i HOME="$RUN/home" PATH="$p" GNUPGHOME="$RUN/gnupg" TMPDIR="$RUN/tmp" \
    CODEX_HOME="$RUN/home/.codex" PYTHONUSERBASE="$USERBASE" TERM=dumb \
    LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 "$@"
}
check "PATH da cerimônia resolve o codex GLOBAL" [ "$(E "$NEW_PATH" sh -c 'command -v codex')" = "$GLOBAL_LAUNCHER" ]
check "PATH do controle antigo resolve o codex $OLD_VER do registry" [ "$(E "$OLD_PATH" sh -c 'command -v codex')" = "$OLD_PREFIX/bin/codex" ]
check "PATH do controle falso resolve o codex falso" [ "$(E "$FAKE_PATH" sh -c 'command -v codex')" = "$FAKE_PREFIX/bin/codex" ]

# ------------------------------------------------ gpg descartável
for s in S.gpg-agent S.gpg-agent.extra S.gpg-agent.browser S.gpg-agent.ssh; do
  printf '%%Assuan%%\nsocket=%s/%s\n' "$SOCK" "$s" >"$RUN/gnupg/$s"
done
E "$TOOLPATH" gpg --batch --passphrase '' --quick-gen-key \
  'Rehearsal Throwaway <rehearsal@example.invalid>' ed25519 sign never >"$LOGS/gpg-gen.out" 2>&1
KEY_FPR=$(E "$TOOLPATH" gpg --with-colons --list-secret-keys | awk -F: '$1=="fpr"{print $10; exit}')
check "chave descartável gerada no GNUPGHOME do ensaio" [ -n "$KEY_FPR" ]

# ------------------------------------------------ 2. remoto bare + checkout
REMOTE="$RUN/remote/$REMOTE_SLUG.git"
mkdir -p "$(dirname "$REMOTE")"
E "$TOOLPATH" git clone -q --bare --no-hardlinks --single-branch --branch main "$SRC_REPO" "$REMOTE"
E "$TOOLPATH" git clone -q "$REMOTE" "$RUN/work"
WORK="$RUN/work"
G() { E "$TOOLPATH" git -C "$WORK" "$@"; }
G config user.name 'Rehearsal'
G config user.email 'rehearsal@example.invalid'
G config commit.gpgsign false
G config tag.gpgsign false
BASE_HEAD=$(G rev-parse HEAD)
printf 'HEAD clonado: %s\n' "$BASE_HEAD"

# o codex GLOBAL pelo verificador REAL do clone, contra o manifesto vivo do
# clone (sem costura): mismatch com exatamente o sha256 novo; e o payload que
# ele resolve é byte a byte o do tarball do registry
E "$TOOLPATH" CLAUDE_PROJECT_DIR="$WORK" python3 "$WORK/.claude/hooks/check_pair_rail.py" --verify-codex-pin "$GLOBAL_LAUNCHER" >"$LOGS/global-pre.json" 2>&1 && GR=0 || GR=$?
python3 - "$LOGS/global-pre.json" "$NEW_SHA" "$OLD_SHA" >"$LOGS/global-payload.txt" 2>&1 <<'PY' && GP_OK=1 || GP_OK=0
import json, sys
lines = [l for l in open(sys.argv[1], encoding="utf-8").read().splitlines() if l.strip()]
d = json.loads(lines[-1])
assert d["status"] == "mismatch" and d["detail"] == "payload_sha256_mismatch", d
assert d["sha256"] == sys.argv[2] and d["expected_sha256"] == sys.argv[3], d
print(d["path"])
PY
check "codex GLOBAL: mismatch (rc=1) contra o manifesto vivo, com o sha256 de $NEW_VER" [ "$GP_OK$GR" = "11" ]
GLOBAL_PAYLOAD=$(tail -n 1 "$LOGS/global-payload.txt")
check "codex GLOBAL: payload byte a byte igual ao do tarball do registry" cmp -s "$GLOBAL_PAYLOAD" "$PREFIX/$PAYLOAD_REL"

# ------------------------------------------------ 3. tag do GA + materiais
FAKE_TAG=0
if ! G rev-parse -q --verify "refs/tags/$GA_TAG" >/dev/null; then
  G tag -a "$GA_TAG" -m "ENSAIO: tag FALSA do GA (rehearse-pin-$PACK_TAG)" HEAD
  FAKE_TAG=1
fi
# o arquivo do plano entra junto (PLAN-SCHEMA §1: subdiretório sem plano é órfão)
for pf in "$SRC_REPO"/.claude/plans/"$PLAN"-*.md; do
  [ -f "$pf" ] || continue
  cp "$pf" "$WORK/.claude/plans/$(basename "$pf")"
  G add -- ".claude/plans/$(basename "$pf")"
done
# o plano que o README manda commitar junto NÃO pode ter linha de instalação
# GLOBAL de outro codex (o MESMO detector do bloco do passo 2 do README, com a
# versão vinda da constante): seguir esse plano trocaria o binário e o P0 do
# SIGN recusaria. Por linha: `npm` + verbo de instalação + flag global +
# `@openai/codex`, em qualquer ordem; sobra de `@openai/codex` que não seja
# exatamente `@openai/codex@<NEW_VER>` = recusa
NEW_VER_RE=$(printf '%s' "$NEW_VER" | sed 's/[.]/[.]/g')
install_lines() {  # install_lines <arquivo>... — ecoa as linhas culpadas
  awk -v ok="@openai/codex@$NEW_VER_RE([^0-9.a-z-]|[.]([^0-9]|\$)|\$)" '
    /npm/ && /@openai\/codex/ &&
    /(^|[^[:alnum:]_-])(-g|--global|--location[= ]global)([^[:alnum:]_-]|$)/ &&
    /(^|[^[:alnum:]_-])(i|in|ins|inst|insta|instal|install|isnt|isnta|isntal|isntall|add|up|update|udpate|upgrade)([^[:alnum:]_-]|$)/ {
      s = $0; gsub(ok, "#", s)
      if (s ~ /@openai\/codex/) print FILENAME ":" FNR ": " $0
    }' "$@" || printf 'ERRO: o detector (awk) falhou\n'
}
PLAN_BAD=$(install_lines "$WORK"/.claude/plans/"$PLAN"-*.md)
printf '%s\n' "$PLAN_BAD" >"$LOGS/plan-install-lines.out"
check "o plano não tem linha de instalação global de um codex diferente do $NEW_VER (log: plan-install-lines.out)" [ -z "$PLAN_BAD" ]
# o detector em si: controle positivo (as formas que ele TEM de recusar) e
# negativo (as que ele tem de aceitar), para o check acima não ser verde-vácuo
printf '%s\n' "npm i -g @openai/codex@latest" "npm update -g @openai/codex" \
  "npm install @openai/codex@$NEW_VER.9 --global" "npm -g i @openai/codex@$OLD_VER" \
  "npm install --location=global @openai/codex" >"$RUN/detector-bad.txt"
printf '%s\n' "npm i -g @openai/codex@$NEW_VER" "rode \`npm i -g @openai/codex@$NEW_VER\`." \
  "npx -y @openai/codex@$OLD_VER --version" "nunca \`npm update -g\` casual" >"$RUN/detector-good.txt"
DET_BAD=$(install_lines "$RUN/detector-bad.txt" | grep -c . || printf '')
DET_GOOD=$(install_lines "$RUN/detector-good.txt" | grep -c . || printf '')
check "detector de instalação: recusa as 5 formas ruins e aceita as 4 boas ($DET_BAD/$DET_GOOD)" \
  [ "$DET_BAD:$DET_GOOD" = "5:0" ]
mkdir -p "$WORK/$REL_PACK"
for f in $PACK_NAMES; do
  cp "$PACK_DIR/$f" "$WORK/$REL_PACK/$f"
  chmod 644 "$WORK/$REL_PACK/$f"
  G add -- "$REL_PACK/$f"
done
if ! G diff --cached --quiet; then
  G commit -q -m "ENSAIO: materiais do pack codex-pin-$PACK_TAG"
fi
G push -q origin main "refs/tags/$GA_TAG"
check "checkout de trabalho sincronizado com o remoto do ensaio" [ "$(G rev-parse HEAD)" = "$(G rev-parse origin/main)" ]
[ "$FAKE_TAG" = "1" ] && printf 'AVISO: %s ainda não existe no repo — o ensaio usou uma tag FALSA\n' "$GA_TAG"

# ------------------------------------------------ estáticos
check "bash -n OWNER-PIN-SIGN.sh" bash -n "$WORK/$SIGN_REL"
check "bash -n rehearse-pin-$PACK_TAG.sh" bash -n "$WORK/$REL_PACK/rehearse-pin-$PACK_TAG.sh"
awk '/^# -+ constantes$/{inb=1; next} /^# -+ fim constantes$/{inb=0; next} !inb{print FILENAME":"FNR": "$0}' \
  "$WORK/$SIGN_REL" | grep -E '0\.1[0-9][0-9]\.[0-9]|[0-9a-f]{64}|sha512-|v[0-9]+\.[0-9]+\.[0-9]+|Opus|Fable' >"$LOGS/literals.out" || printf ''
check "nenhum literal de versão/digest/tag/autor fora do bloco de constantes" [ ! -s "$LOGS/literals.out" ]
python3 - "$WORK" "$REL_PACK" "$LOWER" "$OLD_UPPER" "$NEW_UPPER" "$NEW_VER" "$NEW_INTEGRITY" "$NEW_SHA" >"$LOGS/derive.out" 2>&1 <<'PY' && ok "os .new derivam do vivo (manifesto: 3 valores; pin: prefixo intacto + comentários + range novo)" || ko "derivação dos .new (log: derive.out)"
import json, re, sys
work, rel, lower, old_up, new_up, ver, integ, sha = sys.argv[1:9]
live_man = open(f"{work}/.claude/governance/codex-cli-pin-manifest.json", encoding="utf-8").read()
new_man = open(f"{work}/{rel}/codex-cli-pin-manifest.json.new", encoding="utf-8").read()
exp = re.sub(r'("package_version": ")[^"]*(")', lambda m: m.group(1) + ver + m.group(2), live_man)
exp = re.sub(r'("npm_integrity": ")[^"]*(")', lambda m: m.group(1) + integ + m.group(2), exp)
exp = re.sub(r'("sha256": ")[0-9a-f]{64}(")', lambda m: m.group(1) + sha + m.group(2), exp)
assert exp == new_man, "manifesto .new != vivo com os 3 valores trocados"
live_pin = open(f"{work}/.claude/governance/codex-cli-pin.txt", encoding="utf-8").read().split("\n")[:-1]
new_pin = open(f"{work}/{rel}/codex-cli-pin.txt.new", encoding="utf-8").read()
assert new_pin.endswith("\n")
nl = new_pin.split("\n")[:-1]
assert live_pin[-1] == f">={lower},<{old_up}", live_pin[-1]
assert nl[:len(live_pin) - 1] == live_pin[:-1], "prefixo do vivo alterado"
assert nl[-1] == f">={lower},<{new_up}", nl[-1]
mid = nl[len(live_pin) - 1:-1]
assert mid and all(l == "" or l.startswith("#") for l in mid), "linha não-comentário no meio"
print("ok", len(mid), "linhas novas de cabeçalho")
PY

# ceremony-lint no checkout (lá os materiais estão RASTREADOS, como estarão no repo)
E "$TOOLPATH" bash -c "cd '$WORK' && python3 .claude/scripts/check-ceremony-script.py --json" >"$LOGS/lint.json" 2>"$LOGS/lint.err" && LINT_RC=0 || LINT_RC=$?
check "ceremony-lint rc=0 no checkout com o pack rastreado" [ "$LINT_RC" = "0" ]
python3 - "$LOGS/lint.json" "$REL_PACK" >"$LOGS/lint-pack.out" 2>&1 <<'PY' && ok "ceremony-lint: 0 BLOCKING e 0 ADVISORY nos scripts do pack, ambos rastreados" || ko "ceremony-lint nos scripts do pack (log: lint-pack.out)"
import json, sys
d = json.load(open(sys.argv[1])); rel = sys.argv[2]
mine = [f for f in d["files"] if f["file"].startswith(rel + "/")]
names = sorted(f["file"].rsplit("/", 1)[1] for f in mine)
print(names)
assert len(mine) == 2, names
for f in mine:
    print(f["file"], f["tracked"], f["findings"])
    assert f["tracked"], f["file"]
    assert not f["findings"], f["findings"]
PY
for f in OWNER-PIN-SIGN.sh "rehearse-pin-$PACK_TAG.sh"; do
  m=$(G ls-files --stage -- "$REL_PACK/$f" | awk '{print $1}')
  check "modo no índice de $f = 100644 (R8)" [ "$m" = "100644" ]
done

# ------------------------------------------------ runner da cerimônia
state_clean() {  # a árvore voltou exatamente ao HEAD: nada rastreado mudou, sem .asc
  [ -z "$(G status --porcelain --untracked-files=no)" ] \
    && [ ! -e "$WORK/$SENT_REL.asc" ] \
    && G diff --quiet HEAD -- "$SENT_REL" "$DST_PIN" "$DST_MAN"
}
run_sign() {  # run_sign <nome> <PATH> [VAR=val ...] -- [--dry-run]
  local name="$1" p="$2"; shift 2
  local envs=()
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do envs+=("$1"); shift; done
  [ "${1:-}" = "--" ] && shift
  local rc=0
  E "$p" ${envs[@]+"${envs[@]}"} bash -c "cd '$WORK' && script -q /dev/null bash '$SIGN_REL' $*" \
    </dev/null >"$LOGS/$name.log" 2>&1 || rc=$?
  printf '%s' "$rc"
}
# run REAL em SEGUNDO PLANO, para os controles de sinal e de corrida. O
# lançador põe INT/TERM/HUP/QUIT em SIG_DFL antes do exec: um `&` de shell não
# interativo herda o SIGINT IGNORADO, e o bash não captura sinal ignorado na
# entrada — sem isso, um Ctrl-C de ensaio seria ignorado e a cerimônia
# seguiria até o commit (o controle mediria o lançador, não o SIGN)
printf '%s\n' 'import os, signal, sys' \
  'for s in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM, signal.SIGHUP):' \
  '    signal.signal(s, signal.SIG_DFL)' \
  'os.execvp(sys.argv[1], sys.argv[1:])' >"$RUN/sigdfl.py"
run_sign_bg() {  # run_sign_bg <nome> <PATH> — define BG_PID (o lançador)
  local name="$1" p="$2"
  rm -f "$RUN/$name.spid"
  E "$p" python3 "$RUN/sigdfl.py" bash -c "cd '$WORK' && printf '%s' \$\$ >'$RUN/$name.spid' && exec script -q /dev/null bash '$SIGN_REL'" \
    </dev/null >"$LOGS/$name.log" 2>&1 &
  BG_PID=$!
}
wait_for_log() {  # wait_for_log <arquivo> <padrão> <segundos> — desiste se a cerimônia acabar antes
  local i=0
  while [ "$i" -lt $(($3 * 2)) ]; do
    if grep -qF -- "$2" "$1" 2>/dev/null; then return 0; fi
    kill -0 "$BG_PID" 2>/dev/null || return 1
    sleep 0.5; i=$((i + 1))
  done
  return 1
}
# o bash da cerimônia é o filho do `script` (que o põe numa sessão própria,
# com o grupo de processos = o pid dele): é esse grupo que um Ctrl-C atinge
ceremony_pgid() {  # ceremony_pgid <nome> — ecoa o pgid do bash da cerimônia
  local spid cb
  spid=$(cat "$RUN/$1.spid" 2>/dev/null || printf '')
  [ -n "$spid" ] || return 1
  cb=$(pgrep -P "$spid" | head -n 1)
  [ -n "$cb" ] || return 1
  ps -o pgid= -p "$cb" | tr -d ' '
}
expect_abort() {  # expect_abort <nome> <padrão esperado no log> <PATH> [VAR=val ...] -- [args]
  local name="$1" pat="$2" p="$3"; shift 3
  local rc; rc=$(run_sign "$name" "$p" "$@")
  if [ "$rc" != "0" ] && grep -qF -- "$pat" "$LOGS/$name.log" && state_clean; then
    ok "$name: abortou (rc=$rc) com «${pat}» e árvore intacta"
  else
    ko "$name: rc=$rc; padrão «${pat}» $(grep -qF -- "$pat" "$LOGS/$name.log" && printf 'presente' || printf 'AUSENTE'); árvore $(state_clean && printf 'intacta' || printf 'SUJA') (log: $LOGS/$name.log)"
  fi
}

# ------------------------------------------------ 5. controles negativos
# c11: a chave do GNUPGHOME NÃO está no allowlist de signatários — aborta no
# P0, antes do pinentry; depois o ensaio põe a chave descartável no allowlist
# DO CLONE (commit de ensaio) para os demais casos
expect_abort "c11-chave-fora-do-allowlist" "sem chave autorizada para assinar" "$NEW_PATH" --
printf '# ENSAIO: chave descartável (rehearse-pin-%s)\n%s\n' "$PACK_TAG" "$KEY_FPR" >>"$WORK/.claude/sentinel-signers.txt"
G commit -q -am "ENSAIO: chave descartável no allowlist legado do clone"
G push -q origin main
# c12: no allowlist legado mas FORA do registro do ADR-121 — a 2.ª perna recusa
expect_abort "c12-chave-fora-do-registro" "sem chave autorizada para assinar" "$NEW_PATH" --
REG="$WORK/.claude/security/sentinel-signers-registry.yaml"
if [ -f "$REG" ]; then
  printf '\n  - key_id: "%s"\n    key_type: "hot"\n    created_at: "2026-09-22T00:00:00Z"\n    expires_at: "2030-01-01T00:00:00Z"\n    revoked_at: null\n    notes: "ENSAIO: chave descartável (rehearse-pin-%s)"\n' "$KEY_FPR" "$PACK_TAG" >>"$REG"
  G commit -q -am "ENSAIO: chave descartável no registro de signatários do clone"
  G push -q origin main
fi

# c20: argumento desconhecido ou a mais — recusa ANTES de tudo, nunca cai no
# run real (o molde rodava a cerimônia REAL com `--dryrun`)
for a in "--dryrun" "--dry-run extra"; do
  n="c20-argumento-invalido-$(printf '%s' "$a" | tr -c 'a-z' '_')"
  expect_abort "$n" "uso: bash" "$NEW_PATH" -- $a
  check "$n: recusou antes do P0" [ -z "$(grep -F 'P0 pré-condições' "$LOGS/$n.log" || printf '')" ]
done

# c18: rota api-key (OPENAI_API_KEY no ambiente) com a última rotação > 90
# dias e sem override — o Gate 2 da phase 6 reprovaria DEPOIS do pinentry;
# o P0 recusa antes. Linha de rotação velha só no clone (commit de ensaio,
# desfeito em seguida), para o controle não depender da data de hoje
printf '| 2000-01-01 | OPENAI_API_KEY     | ensaio          | @rehearsal    | ok      | ENSAIO: rotação velha (rehearse-pin-%s) |\n' "$PACK_TAG" >>"$WORK/docs/rotation-log.md"
G commit -q -am "ENSAIO: rotação velha da OPENAI_API_KEY"
G push -q origin main
expect_abort "c18-api-key-rotacao-velha" "o Gate 2 da phase 6 reprovaria DEPOIS do pinentry" "$NEW_PATH" OPENAI_API_KEY=rehearsal-fake-key-0123456789 --
check "c18: nada assinado" [ -z "$(grep -F 'assinado por' "$LOGS/c18-api-key-rotacao-velha.log" || printf '')" ]
G reset -q --hard HEAD~1
G push -q -f origin main
check "c18: rotation-log de volta ao HEAD do ensaio" state_clean
# c19: nenhuma rota de auth (sem OPENAI_API_KEY e sem ~/.codex/auth.json)
mv "$RUN/home/.codex/auth.json" "$RUN/auth.json.away"
expect_abort "c19-sem-rota-de-auth" "sem rota de auth do codex" "$NEW_PATH" --
mv "$RUN/auth.json.away" "$RUN/home/.codex/auth.json"

# c1: o codex do PATH é o ANTIGO (o que o manifesto vivo pina)
expect_abort "c1-codex-antigo-instalado" "ainda é o que o manifesto vivo pina" "$OLD_PATH" --
# c13: o codex do PATH não é nenhum dos pinados — o P0 recusa por HASH, sem
# executar o payload (o falso deixaria um marcador se rodasse)
expect_abort "c13-codex-nao-pinado" "NÃO é o $NEW_VER medido no registry" "$FAKE_PATH" --
check "c13: o payload não pinado NÃO foi executado (M4)" [ ! -e "$RUN/fake-codex-ran" ]

# c2 induz a própria sujeira (README.md): o predicado é «a cerimônia não
# tocou em mais nada», não «árvore limpa»
printf 'x\n' >>"$WORK/README.md"
rc=$(run_sign "c2-modificacao-rastreada" "$NEW_PATH" --)
if [ "$rc" != "0" ] && grep -qF "há modificação RASTREADA pendente" "$LOGS/c2-modificacao-rastreada.log" \
   && [ "$(G status --porcelain --untracked-files=no)" = " M README.md" ] \
   && [ ! -e "$WORK/$SENT_REL.asc" ] && G diff --quiet HEAD -- "$SENT_REL" "$DST_PIN" "$DST_MAN"; then
  ok "c2-modificacao-rastreada: abortou (rc=$rc) sem tocar em nada além da sujeira induzida"
else ko "c2-modificacao-rastreada: rc=$rc (log: $LOGS/c2-modificacao-rastreada.log)"; fi
G checkout -q -- README.md
check "c2: README restaurado" state_clean

G tag -d "$GA_TAG" >/dev/null
expect_abort "c3-sem-tag-do-ga" "o re-pin só entra DEPOIS do corte do GA" "$NEW_PATH" --
G tag -a "$GA_TAG" -m "ENSAIO: objeto DIFERENTE do remoto" HEAD~1
expect_abort "c4-tag-diferente-do-remoto" "difere da local" "$NEW_PATH" --
G tag -d "$GA_TAG" >/dev/null
G fetch -q origin "refs/tags/$GA_TAG:refs/tags/$GA_TAG"

printf '# ENSAIO: edição tardia do pin vivo\n' >>"$WORK/$DST_PIN"
G commit -q -am "ENSAIO: deriva do pin vivo depois dos materiais"
G push -q origin main
expect_abort "c5-deriva-do-pin-vivo" "$DST_PIN mudou depois que o pack foi montado" "$NEW_PATH" --
G reset -q --hard HEAD~1
G push -q -f origin main
check "c5: deriva desfeita no ensaio" [ "$(sha256f "$WORK/$DST_PIN")" = "$BASE_PIN_SHA256" ]

# c21-c23: um commit DEPOIS dos materiais muda o que o sentinel assinaria
# sem mudar o script — o manifesto vivo (guard de deriva), um `.new` (sha
# declarado no script) ou o próprio sentinel (perde um digest que o script
# declara). Cada um aborta no P0, antes do pinentry
commit_then_abort() {  # commit_then_abort <nome> <padrão> <rótulo do commit>
  G commit -q -am "ENSAIO: $3"
  G push -q origin main
  expect_abort "$1" "$2" "$NEW_PATH" --
  G reset -q --hard HEAD~1
  G push -q -f origin main
}
printf '\n' >>"$WORK/$DST_MAN"
commit_then_abort "c21-deriva-do-manifesto-vivo" "$DST_MAN mudou depois que o pack foi montado" "deriva do manifesto vivo depois dos materiais"
check "c21: deriva do manifesto desfeita no ensaio" [ "$(sha256f "$WORK/$DST_MAN")" = "$BASE_MAN_SHA256" ]
printf '# ENSAIO: edição tardia do .new\n' >>"$WORK/$REL_PACK/codex-cli-pin.txt.new"
commit_then_abort "c22-new-editado-depois-dos-materiais" "codex-cli-pin.txt.new não é o byte declarado no script" "edição do .new depois dos materiais"
check "c22: .new de volta ao byte declarado" [ "$(sha256f "$WORK/$REL_PACK/codex-cli-pin.txt.new")" = "$SRC_PIN_SHA256" ]
grep -vF -- "$SRC_MAN_SHA256" "$WORK/$SENT_REL" >"$RUN/sentinel-sem-digest.md"
cp "$RUN/sentinel-sem-digest.md" "$WORK/$SENT_REL"
commit_then_abort "c23-sentinel-sem-um-digest" "o sentinel não declara $SRC_MAN_SHA256" "sentinel sem o digest do manifesto .new"
check "c23: sentinel de volta ao HEAD dos materiais, com o digest" grep -qF -- "$SRC_MAN_SHA256" "$WORK/$SENT_REL"

PLAN_REL=$(G ls-files -- ".claude/plans/$PLAN-*.md" | head -n 1)
if [ -n "$PLAN_REL" ]; then
  G rm -q -- "$PLAN_REL"
  G commit -q -m "ENSAIO: plano ausente do HEAD"
  G push -q origin main
  expect_abort "c7-plano-fora-do-head" "não está no HEAD — commite-o junto" "$NEW_PATH" --
  G reset -q --hard HEAD~1
  G push -q -f origin main
  check "c7: plano de volta ao HEAD do ensaio" [ -n "$(G ls-files -- ".claude/plans/$PLAN-*.md")" ]
else
  ko "c7: o plano $PLAN-*.md não existe nem no checkout de origem"
fi

# falha DEPOIS da assinatura: o restore tem de devolver sentinel, .asc e canônicos
expect_abort "c6-falha-apos-assinar" "pair-rail-gate --phase 6 reprovou" "$NEW_PATH" CEO_PAIR_RAIL_DISABLE=1 --
grep -qF "assinado por $KEY_FPR" "$LOGS/c6-falha-apos-assinar.log" \
  && ok "c6: a falha veio DEPOIS da assinatura (restore exercitado)" \
  || ko "c6: a assinatura não aconteceu antes da falha"

# c24: Ctrl-C (SIGINT ao grupo de processos da cerimônia) no início da
# bateria do passo 5 — uma chamada de FUNÇÃO com a saída redirecionada para
# log. Tem de sair 130, restaurar tudo e dizer «árvore RESTAURADA» no
# TERMINAL (o log do `script`), não no log da bateria
MARK5="5/7 bateria"
PRE24=$(G rev-parse HEAD)
run_sign_bg "c24-ctrl-c-no-passo-5" "$NEW_PATH"
if wait_for_log "$LOGS/c24-ctrl-c-no-passo-5.log" "$MARK5" 300 && PG24=$(ceremony_pgid "c24-ctrl-c-no-passo-5"); then
  kill -INT -- "-$PG24" || printf 'aviso: kill -INT -%s falhou\n' "$PG24" >&2
else
  PG24=""
fi
wait "$BG_PID" && rc=0 || rc=$?
if [ -n "$PG24" ] && [ "$rc" = "130" ] && grep -qF "assinado por $KEY_FPR" "$LOGS/c24-ctrl-c-no-passo-5.log" \
   && grep -qF "árvore RESTAURADA" "$LOGS/c24-ctrl-c-no-passo-5.log" \
   && state_clean && [ "$(G rev-parse HEAD)" = "$PRE24" ]; then
  ok "c24-ctrl-c-no-passo-5: rc=130, depois da assinatura, «árvore RESTAURADA» no terminal, árvore intacta, HEAD parado"
else
  ko "c24-ctrl-c-no-passo-5: pgid=${PG24:-?} rc=$rc; RESTAURADA no terminal: $(grep -qF 'árvore RESTAURADA' "$LOGS/c24-ctrl-c-no-passo-5.log" && printf sim || printf NÃO); árvore $(state_clean && printf intacta || printf SUJA) (log: $LOGS/c24-ctrl-c-no-passo-5.log)"
fi

# c25: o HEAD anda DURANTE a bateria (um commit vazio, mesma árvore) — o
# compare-and-swap do passo 7 recusa, nada é commitado e a árvore é
# restaurada; depois o ensaio descarta o commit vazio
PRE25=$(G rev-parse HEAD)
run_sign_bg "c25-head-move-durante-a-cerimonia" "$NEW_PATH"
MOVED=""
if wait_for_log "$LOGS/c25-head-move-durante-a-cerimonia.log" "$MARK5" 300; then
  G commit -q --allow-empty -m "ENSAIO: o HEAD anda durante a cerimônia" && MOVED=$(G rev-parse HEAD)
fi
wait "$BG_PID" && rc=0 || rc=$?
if [ -n "$MOVED" ] && [ "$rc" != "0" ] \
   && grep -qF "o HEAD mudou durante a cerimônia — nada foi commitado" "$LOGS/c25-head-move-durante-a-cerimonia.log" \
   && grep -qF "árvore RESTAURADA" "$LOGS/c25-head-move-durante-a-cerimonia.log" \
   && [ "$(G rev-parse HEAD)" = "$MOVED" ] && state_clean; then
  ok "c25-head-move-durante-a-cerimonia: o compare-and-swap recusou (rc=$rc), nada commitado, árvore restaurada"
else
  ko "c25-head-move-durante-a-cerimonia: rc=$rc; HEAD $(G rev-parse --short HEAD) (movido: ${MOVED:-nada}) (log: $LOGS/c25-head-move-durante-a-cerimonia.log)"
fi
if [ "$(G rev-parse HEAD)" != "$PRE25" ]; then G reset -q --hard "$PRE25"; fi
check "c25: HEAD de volta ao do remoto do ensaio" [ "$(G rev-parse HEAD)" = "$(G rev-parse origin/main)" ]

# c8: modificação STAGED pré-existente num caminho do escopo — o abort no P0
# não pode desfazer o índice de quem rodou (o trap só arma depois do P0)
printf '# ENSAIO: edição staged pré-existente\n' >>"$WORK/$DST_PIN"
G add -- "$DST_PIN"
rc=$(run_sign "c8-staged-preexistente" "$NEW_PATH" --)
if [ "$rc" != "0" ] && grep -qF "há modificação RASTREADA pendente" "$LOGS/c8-staged-preexistente.log" \
   && [ "$(G diff --cached --name-only)" = "$DST_PIN" ] \
   && [ "$(G status --porcelain --untracked-files=no)" = "M  $DST_PIN" ]; then
  ok "c8-staged-preexistente: abortou (rc=$rc) e a mudança STAGED de quem rodou continua staged"
else ko "c8-staged-preexistente: rc=$rc; índice: $(G diff --cached --name-only | tr '\n' ' ') (log: $LOGS/c8-staged-preexistente.log)"; fi
G reset -q HEAD -- "$DST_PIN"
G checkout -q -- "$DST_PIN"
check "c8: pin de volta ao HEAD" state_clean

# c9: um filtro clean do git que trocaria o sha256 do payload NOVO pelo ANTIGO
# no blob do manifesto — a árvore é montada com `hash-object --no-filters` a
# partir da cópia congelada e conferida em bytes, então o filtro NÃO chega ao
# commit: o dry-run completa e a árvore conferida é a do .new
ATTR="$WORK/.git/info/attributes"
[ ! -e "$ATTR" ] || cp "$ATTR" "$RUN/attributes.orig"
G config filter.ensaio.clean "sed s/$NEW_SHA/$OLD_SHA/"
printf '%s filter=ensaio\n' "$DST_MAN" >>"$ATTR"
rc=$(run_sign "c9-filtro-clean-ignorado" "$NEW_PATH" -- --dry-run)
if [ "$rc" = "0" ] && grep -qF "Ensaio OK" "$LOGS/c9-filtro-clean-ignorado.log" && state_clean; then
  ok "c9-filtro-clean-ignorado: dry-run completo (rc=0) com o filtro ativo — a árvore conferida é a do .new"
else ko "c9-filtro-clean-ignorado: rc=$rc (log: $LOGS/c9-filtro-clean-ignorado.log)"; fi
G config --unset filter.ensaio.clean
if [ -e "$RUN/attributes.orig" ]; then cp "$RUN/attributes.orig" "$ATTR"; else rm -f "$ATTR"; fi
check "c9: filtro removido e árvore limpa" state_clean

# c10: lock do índice pendente — o índice só é sincronizado no FIM (depois do
# pinentry e do commit), então o P0 tem de recusar logo
LOCK="$WORK/.git/index.lock"
: >"$LOCK"
expect_abort "c10-index-lock-pendente" "outro git rodando" "$NEW_PATH" --
rm -f "$LOCK"
check "c10: lock removido, árvore limpa" state_clean

# c14: GIT_CONFIG_PARAMETERS herdado apontando core.hooksPath para hooks
# hostis (ele venceria o GIT_CONFIG_COUNT da cerimônia) — run REAL: recusa
# antes de qualquer git, e nenhum hook hostil roda
mkdir -p "$RUN/evilhooks"
for h in pre-commit commit-msg post-commit reference-transaction post-index-change; do
  printf '#!/bin/sh\ntouch "%s/evil-ran-%s"\nexit 0\n' "$RUN" "$h" >"$RUN/evilhooks/$h"
  chmod +x "$RUN/evilhooks/$h"
done
expect_abort "c14-git-config-parameters-herdado" "variáveis git herdadas redirecionariam" "$NEW_PATH" "GIT_CONFIG_PARAMETERS='core.hooksPath=$RUN/evilhooks'" --
check "c14: nenhum hook hostil executou" [ -z "$(ls "$RUN" | grep '^evil-ran-' || printf '')" ]
# c15: GIT_INDEX_FILE herdado (índice alternativo) — recusa
expect_abort "c15-git-index-file-herdado" "variáveis git herdadas redirecionariam" "$NEW_PATH" GIT_INDEX_FILE="$RUN/alt-index" --

# c16/c17: edição ESCONDIDA do git status por bit do índice — no sentinel
# (assume-unchanged, mantendo todos os digests que o P0 procura nele) e no
# allowlist de signatários (skip-worktree). O P0 confere a árvore em bytes
# contra o HEAD: aborta sem assinar e sem tocar em nada além da edição induzida
hidden_edit_control() {  # hidden_edit_control <nome> <caminho> <bit>
  local name="$1" rel="$2" bit="$3" rc want
  printf '\nEDITADO DEPOIS DA REVISÃO (ensaio %s)\n' "$name" >>"$WORK/$rel"
  G update-index "--$bit" -- "$rel"
  want=$(sha256f "$WORK/$rel")
  rc=$(run_sign "$name" "$NEW_PATH" --)
  if [ "$rc" != "0" ] && grep -qF "difere do HEAD sem aparecer no git status" "$LOGS/$name.log" \
     && [ -z "$(G status --porcelain --untracked-files=no)" ] \
     && [ "$(sha256f "$WORK/$rel")" = "$want" ] && [ ! -e "$WORK/$SENT_REL.asc" ] \
     && [ "$(G show "HEAD:$DST_PIN" | shasum -a 256 | awk '{print $1}')" = "$(sha256f "$WORK/$DST_PIN")" ] \
     && [ "$(G show "HEAD:$DST_MAN" | shasum -a 256 | awk '{print $1}')" = "$(sha256f "$WORK/$DST_MAN")" ]; then
    ok "$name: abortou (rc=$rc) pela conferência contra o HEAD, com o git status LIMPO e nada assinado"
  else ko "$name: rc=$rc (log: $LOGS/$name.log)"; fi
  G update-index "--no-$bit" -- "$rel"
  G checkout -q -- "$rel"
  check "$name: bit removido e arquivo de volta ao byte do HEAD" [ "$(G show "HEAD:$rel" | shasum -a 256 | awk '{print $1}')" = "$(sha256f "$WORK/$rel")" ]
}
hidden_edit_control "c16-sentinel-editado-assume-unchanged" "$SENT_REL" assume-unchanged
hidden_edit_control "c17-allowlist-editado-skip-worktree" ".claude/sentinel-signers.txt" skip-worktree
check "c16/c17: árvore limpa e sem bits no índice" [ -z "$(G ls-files -v | grep -E '^([a-z]|S) ' || printf '')" ]

# ------------------------------------------------ 5b. dry-run e run real
# p1 herda variáveis HOSTIS para a bateria (raiz do verify-counts em outro
# lugar; pytest só coletando, o que tiraria a T2 do PASSED): o ambiente de
# allowlist tem de descartá-las, e o dry-run completa
rc=$(run_sign "p1-dry-run" "$NEW_PATH" VERIFY_COUNTS_ROOT="$RUN/nao-existe" PYTEST_ADDOPTS=--collect-only CEO_CODEX_KEY_ROTATION_OVERRIDE=1 OPENAI_API_KEY=rehearsal-fake-key-0123456789 -- --dry-run)
if [ "$rc" = "0" ] && grep -qF "Ensaio OK" "$LOGS/p1-dry-run.log" && state_clean; then
  ok "p1: --dry-run completo (rc=0) com VERIFY_COUNTS_ROOT/PYTEST_ADDOPTS hostis herdados, árvore intacta"
else
  ko "p1: --dry-run rc=$rc (log: $LOGS/p1-dry-run.log)"
fi
check "p1: o override de rotação herdado é ANUNCIADO, não silencioso" grep -qF "AVISO: CEO_CODEX_KEY_ROTATION_OVERRIDE=1" "$LOGS/p1-dry-run.log"
P1BAK=$(sed -n 's/.*backup e logs desta rodada: //p' "$LOGS/p1-dry-run.log" | tr -d '\r' | head -n 1)
cp "$P1BAK/phase6.out" "$LOGS/p1-phase6.out" 2>/dev/null || printf ''
check "p1: com OPENAI_API_KEY + override o P0 deixou passar e a phase 6 rodou na rota api-key" \
  grep -qF "route=api-key" "$LOGS/p1-phase6.out"

# p2 com hooks do git instalados — de commit E reference-transaction (que
# roda até em update-ref): com core.hooksPath=/dev/null nenhum executa
HOOKS="pre-commit prepare-commit-msg commit-msg post-commit reference-transaction post-index-change"
for h in $HOOKS; do
  printf '#!/bin/sh\ntouch "%s/hook-ran-%s"\nprintf "x\\n" >>README.md\nexit 0\n' "$RUN" "$h" >"$WORK/.git/hooks/$h"
  chmod +x "$WORK/.git/hooks/$h"
done
PRE=$(G rev-parse HEAD)
rc=$(run_sign "p2-real" "$NEW_PATH" --)
check "p2: run REAL rc=0" [ "$rc" = "0" ]
check "p2: o run real exportou GPG_TTY com o terminal da cerimônia" grep -qE 'GPG_TTY=/dev/' "$LOGS/p2-real.log"
for h in $HOOKS; do rm -f "$WORK/.git/hooks/$h"; done
check "p2: nenhum hook do git executou (commit nem reference-transaction)" [ -z "$(ls "$RUN" | grep '^hook-ran-' || printf '')" ]
if [ "$(G rev-parse HEAD~1)" = "$PRE" ] && [ "$(G rev-parse origin/main)" = "$PRE" ]; then
  ok "p2: um commit novo, NÃO empurrado (HEAD~1 = origin/main)"
else ko "p2: HEAD~1/origin/main inesperados"; fi
EXPECTED=$(printf '%s\n' "$DST_PIN" "$DST_MAN" "$SENT_REL" "$SENT_REL.asc" | sort)
check "p2: o commit toca exatamente os 4 caminhos do escopo" [ "$(G diff --name-only HEAD~1 HEAD | sort)" = "$EXPECTED" ]
check "p2: pin commitado = bytes do .new" [ "$(G show "HEAD:$DST_PIN" | shasum -a 256 | awk '{print $1}')" = "$(sha256f "$WORK/$REL_PACK/codex-cli-pin.txt.new")" ]
check "p2: manifesto commitado = bytes do .new" [ "$(G show "HEAD:$DST_MAN" | shasum -a 256 | awk '{print $1}')" = "$(sha256f "$WORK/$REL_PACK/codex-cli-pin-manifest.json.new")" ]
G diff -U0 HEAD~1 HEAD -- "$SENT_REL" | grep -E '^[-+][^-+]' >"$LOGS/sentinel-delta.out" || printf ''
if [ "$(grep -cvE '^[-+](Anchor-SHA|Data): ' "$LOGS/sentinel-delta.out")" = "0" ] && [ "$(wc -l <"$LOGS/sentinel-delta.out" | tr -d ' ')" = "4" ]; then
  ok "p2: sentinel mudou só em Anchor-SHA e Data"
else ko "p2: delta do sentinel inesperado (log: sentinel-delta.out)"; fi
check "p2: Anchor-SHA = HEAD pré-cerimônia" grep -qx "Anchor-SHA: $PRE" "$WORK/$SENT_REL"
E "$TOOLPATH" gpg --status-fd 1 --verify "$WORK/$SENT_REL.asc" "$WORK/$SENT_REL" >"$LOGS/p2-gpg.out" 2>&1 && GV=0 || GV=$?
if [ "$GV" = "0" ] && grep -q "VALIDSIG $KEY_FPR" "$LOGS/p2-gpg.out"; then
  ok "p2: .asc verifica com a chave descartável"
else ko "p2: .asc não verifica (log: p2-gpg.out)"; fi
G log -1 --format=%B >"$LOGS/p2-commit-msg.txt"
check "p2: assunto do commit" [ "$(head -n 1 "$LOGS/p2-commit-msg.txt")" = "ceremony($PLAN): re-pin codex-cli $OLD_VER -> $NEW_VER" ]
check "p2: mensagem nomeia a chave que assinou" grep -qF "chave $KEY_FPR" "$LOGS/p2-commit-msg.txt"
check "p2: mensagem termina com Co-Authored-By" grep -qE '^Co-Authored-By: ' "$LOGS/p2-commit-msg.txt"
check "p2: árvore rastreada limpa depois do commit" [ -z "$(G status --porcelain --untracked-files=no)" ]
E "$TOOLPATH" CLAUDE_PROJECT_DIR="$WORK" python3 "$WORK/.claude/hooks/check_pair_rail.py" --verify-codex-pin "$GLOBAL_LAUNCHER" >"$LOGS/p2-verify.out" 2>&1 && VR=0 || VR=$?
if [ "$VR" = "0" ] && grep -qF '"status": "verified"' "$LOGS/p2-verify.out"; then
  ok "p2: --verify-codex-pin = verified (rc=0) para o codex GLOBAL no checkout re-pinado"
else ko "p2: --verify-codex-pin do global rc=$VR (log: p2-verify.out)"; fi
E "$TOOLPATH" CLAUDE_PROJECT_DIR="$WORK" python3 "$WORK/.claude/hooks/check_pair_rail.py" --verify-codex-pin "$PREFIX/bin/codex" >"$LOGS/p2-verify-registry.out" 2>&1 && VR=0 || VR=$?
check "p2: e para a cópia do registry também (rc=0)" [ "$VR" = "0" ]
E "$OLD_PATH" CLAUDE_PROJECT_DIR="$WORK" python3 "$WORK/.claude/hooks/check_pair_rail.py" --verify-codex-pin >"$LOGS/p2-verify-old.out" 2>&1 && VR=0 || VR=$?
check "p2: e o $OLD_VER antigo agora é mismatch (rc=1)" [ "$VR" = "1" ]
BAKDIR=$(sed -n 's/.*Backup dos originais e logs: //p' "$LOGS/p2-real.log" | tr -d '\r' | tail -n 1)
if [ -n "$BAKDIR" ] && [ -f "$BAKDIR/pytest.out" ]; then
  cp "$BAKDIR/pytest.out" "$LOGS/p2-pytest.out"
  printf 'pytest da bateria: %s\n' "$(tail -n 1 "$LOGS/p2-pytest.out")"
  check "p2: testes que leem o pin passaram" grep -qE '[0-9]+ passed' "$LOGS/p2-pytest.out"
  # `-rA` lista cada teste com o resultado; pulada, a sonda aparece como SKIPPED
  check "p2: a sonda T2 consta PASSED ($T2_NODE)" grep -qxF "PASSED $T2_NODE" "$LOGS/p2-pytest.out"
  cp "$BAKDIR/phase6.out" "$LOGS/p2-phase6.out" 2>/dev/null || printf ''
  check "p2: a phase 6 reportou codex-cli $NEW_VER" grep -qF "codex-cli $NEW_VER" "$LOGS/p2-phase6.out"
else
  ko "p2: não achei o log do pytest da cerimônia"
fi
HEAD_AFTER=$(G rev-parse HEAD)
rc=$(run_sign "p3-rerun" "$NEW_PATH" --)
if [ "$rc" != "0" ] && [ "$(G rev-parse HEAD)" = "$HEAD_AFTER" ] && [ -z "$(G status --porcelain --untracked-files=no)" ]; then
  ok "p3: re-rodar depois do commit aborta sem mexer em nada"
else ko "p3: re-run rc=$rc ou estado mudou (log: $LOGS/p3-rerun.log)"; fi

# ------------------------------------------------ 6. o codex global saiu intacto
check "o codex global saiu do ensaio com o mesmo alvo de link" [ "$(readlink "$GLOBAL_LAUNCHER" || printf '(não é symlink)')" = "$GLOBAL_LINK_BEFORE" ]
check "o payload global saiu do ensaio com o sha256 de $NEW_VER" [ "$(sha256f "$GLOBAL_PAYLOAD")" = "$NEW_SHA" ]

# ------------------------------------------------ 7. placar
printf '\n==================== PLACAR: %s PASS / %s FAIL ====================\n' "$PASS" "$FAIL"
printf 'logs: %s\n' "$LOGS"
[ "$FAIL" = "0" ]
