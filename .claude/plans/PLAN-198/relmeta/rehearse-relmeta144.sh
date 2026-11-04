#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: ensaio de UM uso da relmeta-144
# (PLAN-198, RM da v1.4.4); roda o derive, o derivador, o hard-relmeta.sh e o
# SIGN do molde sign-min numa cópia descartável, nunca no checkout de onde foi
# chamado. Ferramenta do construtor: nenhuma linha hard dos dados a chama.
# rehearse-relmeta144.sh — ensaio PONTA A PONTA da relmeta-144, clonado do
# rehearse-relmeta143.sh (PLAN-194).
#
#   bash .claude/plans/PLAN-198/relmeta/rehearse-relmeta144.sh [--keep] [--sem-sign] [--sem-seco]
#        [--owner-dir DIR] [--gnupg-fonte DIR --chave FPR]
#
# Roda sobre o HEAD do checkout de onde é chamado, que tem de ter os materiais
# commitados. Tudo dentro de um diretório novo (mktemp) sob $REHEARSE_BASE
# (padrão: $TMPDIR), com piso de disco de 30 GB livres:
#   E0. estáticos: bash -n e modo 100644 dos 3 scripts; o derivador compila e passa
#       na própria conferência de nomes (--self-check), e uma cópia dele sem uma
#       constante que ele lê é recusada nomeando-a; nos 3 scripts, toda variável
#       MAIÚSCULA lida é atribuída no próprio arquivo ou é do ambiente; ceremony-lint;
#   E1. um remoto «bare» descartável com o HEAD como `main` e a tag v1.4.2;
#   E2. âncoras: todas PASS no HEAD; na árvore da v1.4.2 com o CHANGELOG do HEAD
#       sobreposto, a parte de TEXTO passa em todas e a de CÓDIGO falha nas
#       esperadas, cada uma nomeando o motivo esperado (ccfloor e annex passam por
#       desenho); na v1.4.2 pura, toda parte de texto falha; no HEAD com o CHANGELOG de
#       PRE_C58 (antes da condição 58 na [1.4.4]), só o texto de kernelfix, redactor,
#       annex e do parágrafo 5 falha; a âncora redactor reprova um envelope da v1.4.0
#       com a condição 58 renumerada; o --verify no HEAD SEM o patch falha; a âncora
#       cond67 reprova um append_entry sintético de duas travas;
#   E3. derivação idempotente (duas vezes): o mesmo patch, byte a byte o commitado;
#   E4. num clone com `git apply --index relmeta.patch`, cada linha hard dos
#       dados, em ordem, sai rc 0 (pytest com resumo só de aprovados), e os
#       testes de release (test_release_workflow_asserts.py e
#       test_release_bump_sites.py) passam;
#   E7. `release.sh bump --dry-run` na árvore com o patch: rc 0, «target 1.4.4» e
#       árvore restaurada;
#   E5. vermelhos do verificador, cada um num estado novo: land fora do pacote
#       depois da derivação (assunto com plano novo, e assunto só com PLAN-198),
#       hex do manifesto trocado, palavra da headline trocada, seção do texto da tag
#       alterada, Derivator-SHA256 alterado, CHANGELOG com [Unreleased], anexo
#       citando v1.4.5 ou v2.0.0, o item «no release is assigned» trocado, a frase
#       de ligação de um parágrafo tirada da [1.4.4], um commit fora do pacote
#       trazido por `merge -s ours` e um commit vazio; em cada um o --verify
#       (python3 -I -B) recusa nomeando o motivo e o hard-relmeta.sh sai rc≠0; e o
#       land fora do pacote mais um commit só do pacote que acrescenta um
#       argparse.py que sai 0: o derivador SEM -I sai rc 0 sem conferir, o
#       hard-relmeta.sh (com -I) recusa; só o argparse.py, com o patch: rc 0;
#   E6'. sobre o Anchor com o allowlist REAL (o HEAD, se o registro do rail dele já é
#       válido; senão o HEAD mais um registro sintético), um GNUPGHOME só com uma
#       chave descartável FORA do allowlist: o SIGN --dry-run para exatamente em P-KEY;
#   E6. a chave descartável entra no allowlist SÓ no clone, por um commit «TEST ONLY
#       (PLAN-198)» ANTES de uma re-derivação com --commit (o patch tem de sair com o
#       MESMO sha256 do real; o sentinel difere só no Derived-From) e um registro de
#       rail SINTÉTICO fecha o Anchor do ensaio; sem --sem-seco, o SIGN em --dry-run
#       num clone feito pelos comandos do roteiro espera SIGN-ENSAIO;
#   E8. com --owner-dir DIR (a pasta do roteiro do Owner, fora do repositório:
#       ASSINAR-RM.sh, owner-sign-rm.sh, valores.txt e ceo-f2-e4.py): os pins
#       conferem; o lançador, no ambiente de login do Owner (`zsh -il -c env` a
#       partir de env -i), passa nas próprias conferências e para na falta de
#       terminal; e o owner-sign-rm.sh roda DUAS vezes, de verdade, sob `script`
#       (pseudo-TTY) e um `zsh -il`, com HOME falso, a chave descartável e o
#       valores.txt com SÓ a URL (o remoto do E6) e o ANCORA (o Anchor do E6)
#       trocados: respondendo NAO (ENCERRADO, rc 2, nada assinado, o remoto e o
#       clone intactos) e respondendo SIM (RM-PUBLICADO, o remoto no commit
#       publicado, o pai dele no Anchor, e o commit só com os 3 alvos, o sentinel e
#       a .asc).
# A chave descartável: com --gnupg-fonte e --chave, a chave secreta FPR desse
# GNUPGHOME é EXPORTADA (só lida) e importada nos GNUPGHOME do ensaio; sem eles, o
# ensaio gera uma, sem senha. A chave FORA do allowlist do E6' é sempre gerada.
# Sai 0 só se todos os itens passarem. Com rc 0 e sem --keep, apaga o próprio
# diretório; com falha (ou --keep) ele fica, com os logs.
#
# O único caminho fora de $REHEARSE_BASE é um diretório curto para os sockets
# do gpg-agent (o macOS limita o caminho de socket a ~104 bytes) e os HOMEs
# curtos do E8: mktemp sob /tmp, removidos no fim.
set -euo pipefail

_genv=""
for _v in $(git rev-parse --local-env-vars); do
  if [ -n "${!_v+x}" ]; then _genv="$_genv $_v"; fi
done
[ -z "$_genv" ] || { printf 'variáveis git herdadas:%s — rode sem elas (unset%s)\n' "$_genv" "$_genv" >&2; exit 2; }

KEEP=0
SEM_SIGN=0
SEM_SECO=0
OWNER_DIR=""
GPG_FONTE=""
CHAVE_FONTE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --keep) KEEP=1; shift ;;
    --sem-sign) SEM_SIGN=1; shift ;;
    --sem-seco) SEM_SECO=1; shift ;;
    --owner-dir)
      [ "$#" -ge 2 ] || { printf 'uso: --owner-dir <pasta do roteiro do Owner>\n' >&2; exit 2; }
      OWNER_DIR=$(cd "$2" && pwd -P) || { printf 'pasta do roteiro ilegível: %s\n' "$2" >&2; exit 2; }
      shift 2 ;;
    --gnupg-fonte)
      [ "$#" -ge 2 ] || { printf 'uso: --gnupg-fonte <GNUPGHOME com a chave descartável>\n' >&2; exit 2; }
      GPG_FONTE=$(cd "$2" && pwd -P) || { printf 'GNUPGHOME ilegível: %s\n' "$2" >&2; exit 2; }
      shift 2 ;;
    --chave)
      [ "$#" -ge 2 ] || { printf 'uso: --chave <fingerprint de 40 hex>\n' >&2; exit 2; }
      CHAVE_FONTE="$2"
      shift 2 ;;
    *) printf 'uso: bash %s [--keep] [--sem-sign] [--sem-seco] [--owner-dir DIR] [--gnupg-fonte DIR --chave FPR]\n' "$0" >&2; exit 2 ;;
  esac
done
if [ -n "$GPG_FONTE$CHAVE_FONTE" ]; then
  [ -n "$GPG_FONTE" ] && [[ "$CHAVE_FONTE" =~ ^[0-9A-F]{40}$ ]] \
    || { printf '--gnupg-fonte e --chave andam juntos; a chave é um fingerprint de 40 hex maiúsculos\n' >&2; exit 2; }
fi

PACK_DIR=$(cd "$(dirname "$0")" && pwd -P)
SRC_REPO=$(cd "$PACK_DIR/../../../.." && pwd -P)
[ -e "$SRC_REPO/.git" ] || { printf 'não achei o repo em %s\n' "$SRC_REPO" >&2; exit 2; }
PLAN=PLAN-198
D=.claude/plans/PLAN-198/relmeta
SENT_REL=.claude/plans/PLAN-198/relmeta-approved.md
APPLY_REL="$D/apply-relmeta144-edits.py"
DERIVE_REL="$D/derive-relmeta144.sh"
HARD_REL="$D/hard-relmeta.sh"
PATCH_REL="$D/relmeta.patch"
DATA_REL="$D/sign.tsv"
RAIL_REL="$D/rail-record.md"
ENTRADA=.claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
NUCLEO=.claude/plans/PLAN-194/sign-min/sign_min.py
BASE_TAG=v1.4.2
BASE_SHA=b55084da6dd8e4a05fc9893b2690df8aebcfd0ca
# o commit antes do que nomeia a condição 58 na [1.4.4] do CHANGELOG (o controle dos parágrafos 5 e 7 da headline)
PRE_C58=e85f7a7f435227e75da8d4a8968368dd43c7ccf7
TARGET_BASE=1.4.4
T_REL=.claude/scripts/local/release.sh
T_MAN=.claude/governance/gate-scripts-manifest.txt
T_TST=.claude/scripts/tests/test_release_bump_sites.py
SIGNERS=.claude/sentinel-signers.txt
REGISTRY=.claude/security/sentinel-signers-registry.yaml

BASE=${REHEARSE_BASE:-${TMPDIR:-/tmp}}
LIVRE=$(df -Pk "$BASE" | awk 'NR == 2 {print $4}')
[ "$LIVRE" -ge $((30 * 1024 * 1024)) ] || { printf 'disco: %s KiB livres em %s (piso: 30 GB)\n' "$LIVRE" "$BASE" >&2; exit 2; }
RUN=$(mktemp -d "${BASE%/}/rehearse-relmeta144.XXXXXX")
RUN=$(cd "$RUN" && pwd -P)
SOCK=$(mktemp -d /tmp/g.XXXXXX)
chmod 700 "$SOCK"
mkdir -p "$RUN/home" "$RUN/tmp" "$RUN/logs" "$RUN/gnupg" "$RUN/gnupg-fora"
chmod 700 "$RUN/gnupg" "$RUN/gnupg-fora"
LOGS="$RUN/logs"
PASS=0; FAIL=0; TALLY="$RUN/tally.txt"; : >"$TALLY"
OH=""
OHN=""
SOBRAS=""
# FIM=1 só na última linha: o bash 3.2 entrega $?=0 ao trap de EXIT depois de um erro
# fatal de expansão (variável não definida sob set -u); sem esta marca, um ensaio
# interrompido no meio sairia rc 0 e apagaria os próprios logs
FIM=0
ok() { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$*" | tee -a "$TALLY"; }
ko() { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$*" | tee -a "$TALLY"; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else ko "$d"; fi; }
sha256f() { shasum -a 256 "$1" | awk '{print $1}'; }
cleanup() {
  local g
  for g in "$RUN/gnupg" "$RUN/gnupg-fora"; do
    GNUPGHOME="$g" gpgconf --kill gpg-agent >/dev/null 2>&1 || printf 'aviso: gpg-agent de %s não parou\n' "$g" >&2
  done
  for g in "$OH" "$OHN"; do
    if [ -n "$g" ]; then
      GNUPGHOME="$g/.gnupg" gpgconf --kill gpg-agent >/dev/null 2>&1 || printf 'aviso: gpg-agent de %s não parou\n' "$g" >&2
    fi
  done
  for s in "$SOCK"/*; do
    if [ -S "$s" ]; then rm -f "$s"; fi
  done
  rmdir "$SOCK" 2>/dev/null || printf 'aviso: %s não ficou vazio\n' "$SOCK" >&2
  if [ "$FIM" = "1" ] && [ "$FAIL" = "0" ] && [ "$KEEP" = "0" ] && [ "$PASS" -gt 0 ]; then
    # limpeza confinada: o diretório deste ensaio, os HOMEs curtos do E8 e os
    # temporários que os SIGNs e o roteiro deste ensaio anunciaram, pelo caminho
    # exato e pelo prefixo de cada um, sem seguir link
    python3 -I -B -c 'import os, shutil, sys
for p in sys.argv[1:]:
    b = os.path.basename(p)
    if not p or os.path.islink(p) or not os.path.isdir(p):
        continue
    if not b.startswith(("rehearse-relmeta144.", "o.", "sign-min.", "owner-sign-rm.")):
        sys.exit(1)
    shutil.rmtree(p)' "$RUN" ${OH:+"$OH"} ${OHN:+"$OHN"} ${SOBRAS:+$SOBRAS} || printf 'aviso: não apaguei %s\n' "$RUN" >&2
  else
    printf 'diretório do ensaio mantido: %s\n' "$RUN" >&2
    if [ -n "$OH$OHN" ]; then printf 'HOMEs do E8 mantidos: %s %s\n' "$OH" "$OHN" >&2; fi
  fi
}
trap 'rc=$?; if [ "$FIM" != "1" ]; then [ "$rc" != "0" ] || rc=1; printf "ensaio INTERROMPIDO antes do placar (rc %s)\n" "$rc" >&2; fi; cleanup; exit $rc' EXIT
printf 'ensaio em %s\n' "$RUN"
# a regressão de todo harness (caller_repo_guard, item 14 (b) do backlog da 1.4.4): HEAD, symbolic-ref e
# refs do repositório chamador iguais antes e depois; rode-o de um clone próprio, nunca de uma worktree
# que divide refs com outro trabalho em andamento
GUARD="$SRC_REPO/.claude/scripts/caller_repo_guard.py"
python3 -I -B "$GUARD" snapshot --repo "$SRC_REPO" --out "$RUN/caller-antes.json" >"$LOGS/caller-antes.out" 2>&1 \
  || { printf 'caller_repo_guard: sem fotografia do repositório chamador (log: %s)\n' "$LOGS/caller-antes.out" >&2; exit 2; }

TOOLPATH=""
for t in git gpg gpgconf python3 shasum script awk sed bash jq zsh; do
  if command -v "$t" >/dev/null 2>&1; then
    d=$(dirname "$(command -v "$t")")
    case ":$TOOLPATH:" in *":$d:"*) ;; *) TOOLPATH="${TOOLPATH:+$TOOLPATH:}$d" ;; esac
  fi
done
TOOLPATH="$TOOLPATH:/usr/bin:/bin:/usr/sbin:/sbin"
USERBASE=$(python3 -I -c 'import site; print(site.getuserbase())')
# ambiente limpo: nada do shell (nem CLAUDE_*, nem CEO_*) vaza para o ensaio
E() {
  env -i HOME="$RUN/home" PATH="$TOOLPATH" GNUPGHOME="$RUN/gnupg" TMPDIR="$RUN/tmp" \
    PYTHONUSERBASE="$USERBASE" PYTHONDONTWRITEBYTECODE=1 TERM=dumb \
    LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 "$@"
}
# o ambiente do SIGN: só os nomes que o roteiro passa (o P0:env do molde recusa outros)
S() {  # S <gnupghome> <home> comando...
  local g="$1" h="$2"
  shift 2
  env -i PATH="$TOOLPATH" HOME="$h" GNUPGHOME="$g" PYTHONUSERBASE="$USERBASE" USER="${USER:-rehearsal}" \
    LOGNAME="${LOGNAME:-rehearsal}" SHELL=/bin/bash TERM=dumb LANG=en_US.UTF-8 PAGER=cat "$@"
}
# a chave descartável num GNUPGHOME do ensaio: importada da fonte, ou gerada sem senha
chave_em() {  # chave_em <gnupghome> <rótulo> — ecoa o fingerprint
  local g="$1" r="$2"
  if [ -n "$GPG_FONTE" ]; then
    env -i HOME="$RUN/home" PATH="$TOOLPATH" GNUPGHOME="$GPG_FONTE" gpg --batch --armor --export-secret-keys "$CHAVE_FONTE" \
      >"$RUN/chave-$r.asc" 2>"$LOGS/gpg-export-$r.err"
    env -i HOME="$RUN/home" PATH="$TOOLPATH" GNUPGHOME="$g" gpg --batch --import "$RUN/chave-$r.asc" \
      >"$LOGS/gpg-import-$r.out" 2>&1
    rm -f "$RUN/chave-$r.asc"
  else
    env -i HOME="$RUN/home" PATH="$TOOLPATH" GNUPGHOME="$g" gpg --batch --passphrase '' --quick-gen-key \
      'Rehearsal Throwaway <rehearsal@example.invalid>' ed25519 sign never >"$LOGS/gpg-gen-$r.out" 2>&1
  fi
  env -i HOME="$RUN/home" PATH="$TOOLPATH" GNUPGHOME="$g" gpg --with-colons --list-secret-keys 2>"$LOGS/gpg-list-$r.err" \
    | awk -F: '$1=="fpr"{print $10; exit}'
}

# ------------------------------------------------ gpg descartável (duas chaves, dois GNUPGHOME)
for g in gnupg gnupg-fora; do
  for s in S.gpg-agent S.gpg-agent.extra S.gpg-agent.browser S.gpg-agent.ssh; do
    printf '%%Assuan%%\nsocket=%s/%s.%s\n' "$SOCK" "$g" "$s" >"$RUN/$g/$s"
  done
done
KEY_FPR=$(chave_em "$RUN/gnupg" e6)
check "chave descartável no GNUPGHOME do ensaio ($KEY_FPR)" [ -n "$KEY_FPR" ]
if [ -n "$CHAVE_FONTE" ]; then
  check "a chave importada é a pedida ($CHAVE_FONTE)" [ "$KEY_FPR" = "$CHAVE_FONTE" ]
fi
E env GNUPGHOME="$RUN/gnupg-fora" gpg --batch --passphrase '' --quick-gen-key \
  'Rehearsal Outside <outside@example.invalid>' ed25519 sign never >"$LOGS/gpg-gen-fora.out" 2>&1
FORA_FPR=$(E env GNUPGHOME="$RUN/gnupg-fora" gpg --with-colons --list-secret-keys | awk -F: '$1=="fpr"{print $10; exit}')
check "chave descartável FORA do allowlist gerada noutro GNUPGHOME" [ -n "$FORA_FPR" ]
home_falso() {  # home_falso <rótulo> — cria um HOME curto do E8 e ecoa o caminho
  local h
  h=$(mktemp -d /tmp/o.XXXXXX)
  h=$(cd "$h" && pwd -P)
  mkdir -p "$h/.gnupg" "$h/fakebin"
  chmod 700 "$h/.gnupg"
  env -i HOME="$h" PATH="$TOOLPATH" git config --global user.name 'Rehearsal Owner'
  env -i HOME="$h" PATH="$TOOLPATH" git config --global user.email 'owner@example.invalid'
  local ub
  ub=$(env -i HOME="$h" PATH="$TOOLPATH" python3 -I -c 'import site; print(site.getuserbase())')
  mkdir -p "$(dirname "$ub")"
  ln -s "$USERBASE" "$ub"
  # um osascript mudo: o aviso da senha não vira notificação na tela durante o ensaio
  printf '#!/bin/sh\nexit 0\n' >"$h/fakebin/osascript"
  chmod 755 "$h/fakebin/osascript"
  printf '%s' "$h"
}
O_FPR=""
if [ -n "$OWNER_DIR" ] && [ "$SEM_SIGN" = "0" ]; then
  OH=$(home_falso sim)
  OHN=$(home_falso nao)
  O_FPR=$(chave_em "$OH/.gnupg" e8sim)
  ON_FPR=$(chave_em "$OHN/.gnupg" e8nao)
  check "E8: a chave descartável nos dois HOMEs falsos do E8 (SIM e NAO)" \
    eval '[ -n "$O_FPR" ] && [ -n "$ON_FPR" ]'
fi

# ------------------------------------------------ E1: remoto bare + checkout
MAT=$(git -C "$SRC_REPO" rev-parse HEAD)
REAL_PATCH_SHA=$(git -C "$SRC_REPO" cat-file blob "HEAD:$PATCH_REL" | shasum -a 256 | awk '{print $1}')
REMOTE="$RUN/remote/origin.git"
mkdir -p "$(dirname "$REMOTE")"
E git init -q --bare "$REMOTE"
E git -C "$REMOTE" fetch -q --no-tags "$SRC_REPO" "+HEAD:refs/heads/main" "+refs/tags/$BASE_TAG:refs/tags/$BASE_TAG"
check "E1: o remoto do ensaio tem main = HEAD dos materiais ($MAT)" \
  [ "$(E git -C "$REMOTE" rev-parse refs/heads/main)" = "$MAT" ]
check "E1: $BASE_TAG^{commit} = $BASE_SHA no remoto" \
  [ "$(E git -C "$REMOTE" rev-parse "refs/tags/$BASE_TAG^{commit}")" = "$BASE_SHA" ]
E git clone -q "$REMOTE" "$RUN/work"
WORK="$RUN/work"
G() { E git -C "$WORK" "$@"; }
G config user.name 'Rehearsal'
G config user.email 'rehearsal@example.invalid'
G config commit.gpgsign false
G config tag.gpgsign false
G fetch -q origin "refs/tags/$BASE_TAG:refs/tags/$BASE_TAG"
check "E1: checkout de trabalho no HEAD dos materiais" [ "$(G rev-parse HEAD)" = "$MAT" ]

# ------------------------------------------------ E0: estáticos
for f in derive-relmeta144.sh hard-relmeta.sh rehearse-relmeta144.sh; do
  check "bash 3.2 -n $f" /bin/bash -n "$WORK/$D/$f"
  m=$(G ls-files --stage -- "$D/$f" | awk '{print $1}')
  check "modo no índice de $f = 100644 (R8)" [ "$m" = "100644" ]
done
E python3 -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' \
  "$WORK/$APPLY_REL" >"$LOGS/compile.out" 2>&1 && ok "o derivador compila (python3)" || ko "o derivador não compila (log: compile.out)"
E python3 "$WORK/$APPLY_REL" --repo "$WORK" --self-check >"$LOGS/self-check.out" 2>&1 && SC=0 || SC=$?
check "E0: --self-check do derivador: rc=0, nenhum nome lido sem definição (log: self-check.out)" [ "$SC" = "0" ]
# controle vermelho da conferência de nomes: uma cópia sem uma constante que só uma função lê
sed '/^CEO_BOOT_INSTALL = /d' "$WORK/$APPLY_REL" >"$RUN/mutante-nomes.py"
E python3 "$RUN/mutante-nomes.py" --repo "$WORK" --self-check >"$LOGS/self-check-mutante.out" 2>&1 && SM=0 || SM=$?
check "E0: a cópia sem CEO_BOOT_INSTALL é recusada pela conferência de nomes, nomeando-a (log: self-check-mutante.out)" \
  eval '[ "$SM" = "2" ] && grep -qF "CEO_BOOT_INSTALL (linha" "$LOGS/self-check-mutante.out"'
# nos 3 scripts: toda variável MAIÚSCULA lida é atribuída no próprio arquivo ou é do ambiente
cat >"$RUN/bash-nomes.py" <<'PY'
import re, sys
AMBIENTE = {"HOME", "PATH", "TMPDIR", "USER", "LOGNAME", "BASH_SOURCE", "BASH_VERSION", "REHEARSE_BASE",
            "PWD", "TERM", "LANG", "SHELL", "BASH_REMATCH"}
ruim = 0
for arq in sys.argv[1:]:
    t = open(arq, encoding="utf-8").read()
    # o corpo dos heredocs com aspas e dado, nao codigo do shell
    t = re.sub(r"(?ms)(<<'(\w+)'[^\n]*\n).*?^\2$", r"\1", t)
    lidas = set(re.findall(r"\$\{?([A-Z][A-Z0-9_]*)\b", t))
    atrib = set(re.findall(r"(?m)(?:^|[\s;(&|])(?:local\s+|export\s+)?([A-Z][A-Z0-9_]*)\+?=", t))
    atrib |= set(re.findall(r"\bfor\s+([A-Z][A-Z0-9_]*)\s+in\b", t))
    atrib |= set(re.findall(r"\bread\s+(?:-[a-z]+\s+)*([A-Z][A-Z0-9_]*)", t))
    sem = sorted(lidas - atrib - AMBIENTE)
    print(arq.rsplit("/", 1)[-1], "sem atribuição:", sem)
    ruim += len(sem)
sys.exit(1 if ruim else 0)
PY
E python3 "$RUN/bash-nomes.py" "$WORK/$D/derive-relmeta144.sh" "$WORK/$D/hard-relmeta.sh" "$WORK/$D/rehearse-relmeta144.sh" \
  >"$LOGS/bash-nomes.out" 2>&1 && BN=0 || BN=$?
check "E0: nos 3 scripts, toda variável MAIÚSCULA lida é atribuída no arquivo ou é do ambiente (log: bash-nomes.out)" [ "$BN" = "0" ]
# controle vermelho: uma cópia do derive sem a constante D é recusada, nomeando-a
sed '/^D=\.claude\/plans\/PLAN-198\/relmeta$/d' "$WORK/$D/derive-relmeta144.sh" >"$RUN/mutante-derive.sh"
E python3 "$RUN/bash-nomes.py" "$RUN/mutante-derive.sh" >"$LOGS/bash-nomes-mutante.out" 2>&1 && BM=0 || BM=$?
check "E0: a cópia do derive sem D= é recusada pela conferência de variáveis, nomeando-a (log: bash-nomes-mutante.out)" \
  eval '[ "$BM" = "1" ] && grep -qE "sem atribuição: \[.D.\]$" "$LOGS/bash-nomes-mutante.out"'
E bash -c "cd '$WORK' && python3 .claude/scripts/check-ceremony-script.py --json" >"$LOGS/lint.json" 2>"$LOGS/lint.err" && LINT_RC=0 || LINT_RC=$?
check "ceremony-lint rc=0 no checkout com o pack rastreado" [ "$LINT_RC" = "0" ]
E python3 - "$LOGS/lint.json" "$D" >"$LOGS/lint-pack.out" 2>&1 <<'PY' && ok "ceremony-lint: os 3 scripts do pack rastreados, 0 achados" || ko "ceremony-lint nos scripts do pack (log: lint-pack.out)"
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

# ------------------------------------------------ E2: âncoras
E python3 "$WORK/$APPLY_REL" --repo "$WORK" --claims-only >"$LOGS/claims-head.out" 2>&1 && CH=0 || CH=$?
# controle da âncora cond67: duas travas separadas reprovam; uma trava só passa; o gravador real passa
E python3 - "$WORK/$APPLY_REL" "$WORK/.claude/hooks/_lib/_audit_log_parts/rotation_storage.py" >"$LOGS/cond67-controle.out" 2>&1 <<'PY' && C67=0 || C67=$?
import importlib.util, sys
s = importlib.util.spec_from_file_location("a", sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
dois = (
    "def append_entry(paths, line):\n"
    "    with FileLock(paths[\"lock\"], timeout=2.5):\n"
    "        prev = _audit_hmac.read_prev_hmac()\n"
    "    with FileLock(paths[\"lock\"], timeout=2.5):\n"
    "        with open(p, \"a\") as f:\n"
    "            f.write(line)\n"
    "        _audit_hmac.write_last_hmac(d)\n")
um = dois.replace("        prev = _audit_hmac.read_prev_hmac()\n    with FileLock(paths[\"lock\"], timeout=2.5):\n",
                  "        prev = _audit_hmac.read_prev_hmac()\n")
r_dois, r_um, r_real = m.cond67_ast(dois), m.cond67_ast(um), m.cond67_ast(open(sys.argv[2]).read())
print("duas travas:", r_dois); print("uma trava:", r_um); print("real:", r_real)
assert r_dois and "MESMO" in r_dois[0], r_dois
assert r_um == [] and r_real == [], (r_um, r_real)
PY
check "E2: âncora cond67: um append_entry sintético com duas travas reprova; com uma trava passa; o real passa (log: cond67-controle.out)" [ "$C67" = "0" ]
NCLAIMS=$(E python3 -c 'import importlib.util, sys
s = importlib.util.spec_from_file_location("a", sys.argv[1]); m = importlib.util.module_from_spec(s)
s.loader.exec_module(m); print(len(m.CLAIMS) + 1)' "$WORK/$APPLY_REL")
check "E2: âncoras no HEAD: rc=0 e $NCLAIMS/$NCLAIMS PASS (log: claims-head.out)" \
  eval '[ "$CH" = "0" ] && [ "$NCLAIMS" = "17" ] && [ "$(grep -c "^PASS  " "$LOGS/claims-head.out")" = "$NCLAIMS" ]'
E git clone -q --no-hardlinks "$WORK" "$RUN/base"
E git -C "$RUN/base" checkout -q --detach "$BASE_SHA"
G show "HEAD:CHANGELOG.md" >"$RUN/base/CHANGELOG.md"
E python3 "$WORK/$APPLY_REL" --repo "$RUN/base" --claims-only >"$LOGS/claims-base.out" 2>&1 && CB=0 || CB=$?
# o motivo de CÓDIGO esperado por âncora na v1.4.2 (vazio = PASS por desenho)
red_ok() {  # red_ok <arquivo> — confere a parte de código e a de texto de cada âncora
  E python3 - "$1" <<'PY'
import re, sys
esperado = {
    "train": "(commit da v1.4.3-rc.1) nao e ancestral do HEAD",
    "ccfloor": None,
    "harness": "REPLAY_FIXTURES_REL=['.claude/hooks/tests/fixtures/harness-config/replay']",
    "cond67": "audit_log.py ainda define append_entry",
    "defaultmode": "DEFAULT_MODE_BASELINE ausente",
    "cenv": "com kwargs ['action',",
    "fixes": ".claude/scripts/status.py ainda passa --as-json",
    "guard": "posture_scan.py ausente",
    "split": "check_bash_safety.py tem ",
    "spool": "sem exatamente uma linha export CEO_HOOK_BOUNDED_EXIT=1",
    "kernelfix": "_lib/canonical_edit ausente (nenhum arquivo rastreado)",
    "redactor": "gh[REDACTED:github_pat]nd",
    "merges": "(merge do pull request #7) nao e ancestral do HEAD",
    "models": "model_currency.py ausente",
    "codex": "package_version='0.156.1'",
    "annex": None,
    "paragrafos": None,
}
txt = open(sys.argv[1], encoding="utf-8").read()
blocos = re.findall(r"(?m)^(PASS|FAIL)  \[([a-z0-9]+)\][^\n]*\n      codigo: (PASS|FAIL) — ([^\n]*)\n      texto:  (PASS|FAIL) — ([^\n]*)$", txt)
vistos = {}
for geral, chave, cod, cdet, tex, tdet in blocos:
    vistos[chave] = (cod, cdet, tex, tdet)
assert sorted(vistos) == sorted(esperado), sorted(vistos)
for chave, motivo in esperado.items():
    cod, cdet, tex, tdet = vistos[chave]
    assert tex == "PASS", (chave, "texto", tdet)
    if motivo is None:
        assert cod == "PASS", (chave, cdet)
    else:
        assert cod == "FAIL" and motivo in cdet, (chave, cdet)
    print(chave, cod, tex)
PY
}
red_ok "$LOGS/claims-base.out" >"$LOGS/red-check.out" 2>&1 && RB=0 || RB=$?
check "E2: v1.4.2 + CHANGELOG do HEAD: rc=1; texto PASS em todas; código FAIL nas 14 esperadas, cada uma pelo motivo dela; ccfloor, annex e paragrafos PASS (log: claims-base.out, red-check.out)" \
  eval '[ "$CB" = "1" ] && [ "$RB" = "0" ]'
E git -C "$RUN/base" checkout -q -- CHANGELOG.md
E python3 "$WORK/$APPLY_REL" --repo "$RUN/base" --claims-only >"$LOGS/claims-base-pura.out" 2>&1 && CP=0 || CP=$?
check "E2: v1.4.2 pura: rc=1 e a parte de texto FAIL nas $NCLAIMS (sem as seções [1.4.4] e [1.4.3]) (log: claims-base-pura.out)" \
  eval '[ "$CP" = "1" ] && [ "$(grep -c "^      texto:  FAIL" "$LOGS/claims-base-pura.out")" = "$NCLAIMS" ]'
E python3 -I -B -c 'import os, shutil, sys
p = sys.argv[1]
if os.path.basename(p) != "base" or os.path.islink(p):
    sys.exit(1)
shutil.rmtree(p)' "$RUN/base"
# os parágrafos 5 e 7 da headline, que a condição 58 mudou: o HEAD com o CHANGELOG de PRE_C58 (o
# commit antes do que nomeia a condição 58 na [1.4.4]) reprova só as partes de TEXTO de kernelfix,
# redactor, annex e do parágrafo 5, cada uma pelo motivo dela; as de CÓDIGO passam todas
E git clone -q --no-hardlinks "$WORK" "$RUN/c58"
E git -C "$RUN/c58" checkout -q --detach "$MAT"
G show "$PRE_C58:CHANGELOG.md" >"$RUN/c58/CHANGELOG.md"
E python3 "$WORK/$APPLY_REL" --repo "$RUN/c58" --claims-only >"$LOGS/claims-pre-c58.out" 2>&1 && C58=0 || C58=$?
E python3 - "$LOGS/claims-pre-c58.out" >"$LOGS/red-check-c58.out" 2>&1 <<'PY' && RC58=0 || RC58=$?
import re, sys
esperado = {
    "kernelfix": ["the preparation of this release found that the kernel's hard-deny list"],
    "redactor": ["which the signed v1.4.0 verdict had declared as its condition 58",
                 "The signed v1.4.0 verdict declared this defect as its condition 58."],
    "annex": ["diz NOT cured sobre o anexo da v1.4.0",
              "nao diz 'Signed condition 58 is the redactor offsets defect fixed above.'"],
    "paragrafos": ["paragrafo 5 da headline: a secao [1.4.4] nao diz \"Two of the defects this release fixes:"],
}
txt = open(sys.argv[1], encoding="utf-8").read()
blocos = re.findall(r"(?m)^(PASS|FAIL)  \[([a-z0-9]+)\][^\n]*\n      codigo: (PASS|FAIL) — ([^\n]*)\n      texto:  (PASS|FAIL) — ([^\n]*)$", txt)
assert len(blocos) == 17, len(blocos)
for geral, chave, cod, cdet, tex, tdet in blocos:
    assert cod == "PASS", (chave, "codigo", cdet)
    if chave in esperado:
        assert tex == "FAIL" and all(m in tdet for m in esperado[chave]), (chave, tdet)
    else:
        assert tex == "PASS", (chave, "texto", tdet)
    print(chave, cod, tex)
outros = re.findall(r"paragrafo (\d+) da headline", txt)
assert outros == ["5"], outros
PY
check "E2: o HEAD com o CHANGELOG de ${PRE_C58:0:8}: rc=1; código PASS em todas; texto FAIL só em kernelfix, redactor, annex e no parágrafo 5, cada um pelo motivo dele (log: claims-pre-c58.out, red-check-c58.out)" \
  eval '[ "$C58" = "1" ] && [ "$RC58" = "0" ]'
# o acoplamento da âncora redactor com a condição 58: uma cópia do envelope da v1.4.0 com a
# condição renumerada, num caminho fora da governança do clone, reprova; o envelope real passa
E python3 - "$WORK/$APPLY_REL" "$RUN/c58" >"$LOGS/cond58-controle.out" 2>&1 <<'PY' && K58=0 || K58=$?
import importlib.util, pathlib, sys
s = importlib.util.spec_from_file_location("a", sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
repo = pathlib.Path(sys.argv[2])
src = (repo / m.V140_ENVELOPE).read_text(encoding="utf-8")
old = "  - 58. **O redator de saída para o Codex aplica spans NFKC no texto original**"
assert src.count(old) == 1
dst = repo / "probe-c58" / "envelope-renumerado.md"
dst.parent.mkdir()
dst.write_text(src.replace(old, old.replace("58.", "59.", 1), 1), encoding="utf-8")
real = m.code_redactor(repo)
m.V140_ENVELOPE = str(dst.relative_to(repo))
mut = m.code_redactor(repo)
print("envelope real:", real); print("condicao renumerada:", mut)
assert real == [], real
assert len(mut) == 1 and "sem a condicao 58" in mut[0], mut
PY
check "E2: âncora redactor: o envelope da v1.4.0 com a condição 58 renumerada reprova; o real passa (log: cond58-controle.out)" [ "$K58" = "0" ]
E python3 -I -B -c 'import os, shutil, sys
p = sys.argv[1]
if os.path.basename(p) != "c58" or os.path.islink(p):
    sys.exit(1)
shutil.rmtree(p)' "$RUN/c58"
E bash -c "cd '$WORK' && python3 -I -B '$APPLY_REL' --repo=. --verify" >"$LOGS/verify-sem-patch.out" 2>&1 && VS=0 || VS=$?
check "E2: --verify no HEAD SEM o patch: rc≠0, nomeando o release.sh que difere da re-derivação (log: verify-sem-patch.out)" \
  eval '[ "$VS" != "0" ] && grep -qF "release.sh na arvore difere da re-derivacao" "$LOGS/verify-sem-patch.out"'

# ------------------------------------------------ E3: derivação idempotente
derive() {  # derive <nome> [--commit] — ecoa o rc
  local name="$1" rc=0
  shift
  E bash -c "cd '$WORK' && bash '$DERIVE_REL' $*" >"$LOGS/$name.log" 2>&1 || rc=$?
  printf '%s' "$rc"
}
RC=$(derive d1)
check "E3: derive no HEAD dos materiais: rc=0 e «inalterado» (log: d1.log)" \
  eval '[ "$RC" = "0" ] && grep -q "^inalterado" "$LOGS/d1.log"'
RC=$(derive d2)
check "E3: derive de novo: «inalterado», patch byte a byte o commitado ($REAL_PATCH_SHA) e árvore limpa" \
  eval '[ "$RC" = "0" ] && grep -q "^inalterado" "$LOGS/d2.log" && [ "$(sha256f "$WORK/$PATCH_REL")" = "$REAL_PATCH_SHA" ] && [ -z "$(G status --porcelain --untracked-files=no)" ]'
check "E3: o patch toca exatamente os 3 alvos" \
  eval '[ "$(G apply --numstat "$PATCH_REL" | awk "{print \$3}" | sort | tr "\n" " ")" = "$(printf "%s\n" "$T_MAN" "$T_REL" "$T_TST" | sort | tr "\n" " ")" ]'

# ------------------------------------------------ E4: linhas hard e testes de release com o patch
prep() {  # prep <dir> <commit> — clone descartável no commit (com as tags do checkout de trabalho)
  E git clone -q --no-hardlinks "$WORK" "$1"
  E git -C "$1" checkout -q --detach "$2"
}
patch_on() {  # patch_on <dir> — o patch aplicado ao índice e à árvore, como o SIGN o aplica
  E git -C "$1" apply --index "$PATCH_REL"
}
fresh() {  # fresh <dir> <commit> — prep + patch_on
  prep "$1" "$2"
  patch_on "$1"
}
commit_in() {  # commit_in <dir> <mensagem> — commita o que está no índice
  E git -C "$1" -c user.name=R -c user.email=r@example.invalid commit -q -m "$2"
}
drop() {  # drop <dir> — apaga um filho direto de $RUN
  E python3 -I -B -c 'import os, shutil, sys
r, p = sys.argv[1], sys.argv[2]
if os.path.dirname(p) != r or os.path.islink(p):
    sys.exit(1)
shutil.rmtree(p)' "$RUN" "$1"
}
fresh "$RUN/e4" "$MAT"
k=0
while IFS= read -r linha; do
  case "$linha" in hard$'\t'*) ;; *) continue ;; esac
  k=$((k + 1))
  IFS=$'\t' read -r -a campos <<<"${linha#hard$'\t'}"
  t0=$(date +%s)
  ( cd "$RUN/e4" && E "${campos[@]}" ) >"$LOGS/e4-hard-$k.log" 2>&1 && HRC=0 || HRC=$?
  t1=$(date +%s)
  PYT_OK=1
  if [ "${campos[1]:-}" = "-m" ] && [ "${campos[2]:-}" = "pytest" ]; then
    ult=$(awk 'NF {l = $0} END {print l}' "$LOGS/e4-hard-$k.log")
    case "$ult" in *" passed"*) case "$ult" in *failed*|*error*|*skipped*|*xfail*|*xpass*) PYT_OK=0 ;; esac ;; *) PYT_OK=0 ;; esac
  fi
  if [ "$HRC" = "0" ] && [ "$PYT_OK" = "1" ]; then
    ok "E4: hard $k rc=0 em $((t1 - t0)) s: ${campos[*]}"
  else
    ko "E4: hard $k rc=$HRC (resumo pytest ok=$PYT_OK): ${campos[*]} (log: e4-hard-$k.log)"
  fi
done <"$WORK/$DATA_REL"
check "E4: os dados têm 5 linhas hard, todas executadas" [ "$k" = "5" ]
( cd "$RUN/e4" && E python3 -m pytest -p no:cacheprovider -q -rfE --tb=short \
    .claude/scripts/tests/test_release_workflow_asserts.py .claude/scripts/tests/test_release_bump_sites.py ) \
  >"$LOGS/e4-release-tests.log" 2>&1 && RT=0 || RT=$?
check "E4: test_release_workflow_asserts.py + test_release_bump_sites.py com o patch: rc=0 ($(awk 'NF {l = $0} END {print l}' "$LOGS/e4-release-tests.log"))" [ "$RT" = "0" ]
check "E4: a árvore com o patch segue igual ao índice depois das linhas hard (só o patch staged)" \
  eval '[ -z "$(E git -C "$RUN/e4" status --porcelain --untracked-files=no | grep -v "^M  ")" ] && [ "$(E git -C "$RUN/e4" diff --cached --name-only | sort | tr "\n" " ")" = "$(printf "%s\n" "$T_MAN" "$T_REL" "$T_TST" | sort | tr "\n" " ")" ]'

# ------------------------------------------------ E7: o driver em 1.4.4, bump --dry-run
# o bump recusa árvore suja: o patch entra num commit do ensaio, como o SIGN o deixaria
commit_in "$RUN/e4" "ENSAIO: relmeta.patch aplicado"
( cd "$RUN/e4" && E bash "$T_REL" bump --dry-run --npm-readme-reviewed --today "$(date +%F)" ) \
  >"$LOGS/bump-dry.out" 2>&1 && BRC=0 || BRC=$?
NBUMP=$(grep ' | ' "$LOGS/bump-dry.out" | wc -l | tr -d ' ')
check "E7: release.sh bump --dry-run em ${TARGET_BASE}: rc=0, ${NBUMP} arquivo(s) no diffstat, «target ${TARGET_BASE}» e árvore restaurada (log: bump-dry.out)" \
  eval '[ "$BRC" = "0" ] && [ "$NBUMP" -gt 0 ] && grep -q "target $TARGET_BASE" "$LOGS/bump-dry.out" && [ -z "$(E git -C "$RUN/e4" status --porcelain --untracked-files=all)" ]'
drop "$RUN/e4"

# ------------------------------------------------ E5: vermelhos do verificador
verify_in() {  # verify_in <dir> <log> — ecoa o rc do --verify, rodado como o hard-relmeta.sh o roda
  local rc=0
  ( cd "$1" && E python3 -I -B "$APPLY_REL" --repo=. --verify ) >"$2" 2>&1 || rc=$?
  printf '%s' "$rc"
}
hard_in() {  # hard_in <dir> <log> — ecoa o rc do hard-relmeta.sh
  local rc=0
  ( cd "$1" && E bash "$HARD_REL" ) >"$2" 2>&1 || rc=$?
  printf '%s' "$rc"
}
red() {  # red <nome> <dir> <padrão> [antes] — o --verify recusa nomeando, e o hard-relmeta.sh (a linha
  # hard que roda o --verify) sai rc≠0; sem «antes», o log do hard-relmeta.sh nomeia o mesmo motivo (o
  # --verify dele recusou); com «antes», o hard-relmeta.sh recusa num passo anterior ao --verify
  local v h desc="$1" hn=1
  v=$(verify_in "$2" "$LOGS/e5-$1-verify.log")
  h=$(hard_in "$2" "$LOGS/e5-$1-hard.log")
  desc="$desc (e o hard-relmeta.sh rc=$h)"
  if [ "${4:-}" != "antes" ] && ! grep -qF -- "$3" "$LOGS/e5-$1-hard.log"; then hn=0; fi
  if [ "$v" != "0" ] && grep -qF -- "$3" "$LOGS/e5-$1-verify.log" && [ "$h" != "0" ] && [ "$hn" = "1" ]; then
    ok "E5: $desc: --verify rc=$v nomeando «$3»"
  else
    ko "E5: $desc: --verify rc=$v; padrão «$3» $(grep -qF -- "$3" "$LOGS/e5-$1-verify.log" && printf presente || printf AUSENTE) (log: e5-$1-verify.log)"
  fi
}
# edita a seção [1.4.4] do CHANGELOG de um clone: troca UMA ocorrência dentro dela
changelog_144() {  # changelog_144 <arquivo> <velho> <novo>
  E python3 - "$1" "$2" "$3" <<'PY'
import sys
p, velho, novo = sys.argv[1], sys.argv[2].replace("\\n", "\n"), sys.argv[3].replace("\\n", "\n")
t = open(p, encoding="utf-8").read()
i, j = t.index("## [1.4.4]"), t.index("## [1.4.3]")
sec = t[i:j]
assert sec.count(velho) == 1, (velho, sec.count(velho))
open(p, "w", encoding="utf-8").write(t[:i] + sec.replace(velho, novo, 1) + t[j:])
PY
}
# controle verde: o mesmo estado sem nada trocado
fresh "$RUN/e5" "$MAT"
V0=$(verify_in "$RUN/e5" "$LOGS/e5-verde-verify.log"); H0=$(hard_in "$RUN/e5" "$LOGS/e5-verde-hard.log")
check "E5: controle verde: --verify e hard-relmeta.sh rc=0 no Anchor com o patch (logs: e5-verde-*)" \
  eval '[ "$V0" = "0" ] && [ "$H0" = "0" ]'
drop "$RUN/e5"
# os estados que pedem commit commitam ANTES do patch (o SIGN aplica o patch sobre o Anchor)
# (a) land fora do pacote, com plano novo no assunto
prep "$RUN/e5" "$MAT"
printf 'ensaio\n' >"$RUN/e5/docs/relmeta144-probe.txt"
E git -C "$RUN/e5" add -- docs/relmeta144-probe.txt
commit_in "$RUN/e5" "chore(PLAN-199): ENSAIO land fora do pacote"
patch_on "$RUN/e5"
red a-plano-novo "$RUN/e5" "Derived-From do sentinel"
drop "$RUN/e5"
# (b) land fora do pacote citando só PLAN-198 (o escopo não muda; o Derived-From pega)
prep "$RUN/e5" "$MAT"
printf 'ensaio\n' >"$RUN/e5/docs/relmeta144-probe.txt"
E git -C "$RUN/e5" add -- docs/relmeta144-probe.txt
commit_in "$RUN/e5" "docs(PLAN-198): ENSAIO land fora do pacote"
patch_on "$RUN/e5"
red b-so-plan198 "$RUN/e5" "Derived-From do sentinel"
drop "$RUN/e5"
# (c) um hex da linha do release.sh no manifesto trocado
fresh "$RUN/e5" "$MAT"
E python3 - "$RUN/e5/$T_MAN" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read().split("\n")
k = [i for i, ln in enumerate(t) if ln.endswith("  .claude/scripts/local/release.sh")][0]
t[k] = ("0" if t[k][0] != "0" else "1") + t[k][1:]
open(p, "w", encoding="utf-8").write("\n".join(t))
PY
red c-manifesto "$RUN/e5" "gate-scripts-manifest.txt na arvore difere" antes
drop "$RUN/e5"
# (d) uma palavra da headline trocada no driver
fresh "$RUN/e5" "$MAT"
E python3 - "$RUN/e5/$T_REL" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
assert t.count("Maintenance release (PLAN-198)") == 1
open(p, "w", encoding="utf-8").write(t.replace("Maintenance release (PLAN-198)", "MAINTENANCE release (PLAN-198)", 1))
PY
red d-headline "$RUN/e5" "release.sh na arvore difere" antes
drop "$RUN/e5"
# (e) a seção do texto da tag alterada no sentinel (commitada: o --verify lê o sentinel do HEAD)
prep "$RUN/e5" "$MAT"
E python3 - "$RUN/e5/$SENT_REL" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
assert t.count("Headline: Maintenance release (PLAN-198)") == 1
open(p, "w", encoding="utf-8").write(t.replace("Headline: Maintenance release (PLAN-198)", "Headline: Maintenance Release (PLAN-198)", 1))
PY
E git -C "$RUN/e5" add -- "$SENT_REL"
commit_in "$RUN/e5" "plan(PLAN-198): ENSAIO texto da tag alterado"
patch_on "$RUN/e5"
red e-texto-da-tag "$RUN/e5" "secao do texto da tag difere"
drop "$RUN/e5"
# (f1) CHANGELOG com [Unreleased] na árvore; (f2) anexo citando v1.4.5
fresh "$RUN/e5" "$MAT"
E python3 - "$RUN/e5/CHANGELOG.md" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
i = t.index("## [1.4.4]")
open(p, "w", encoding="utf-8").write(t[:i] + "## [Unreleased]\n\n- ensaio\n\n" + t[i:])
PY
red f1-unreleased "$RUN/e5" "[Unreleased]"
E git -C "$RUN/e5" checkout -q -- CHANGELOG.md
ANEXO='  - **The rest stays open, and no release is assigned to their cure.**\n'
changelog_144 "$RUN/e5/CHANGELOG.md" "$ANEXO" "$ANEXO  - Planned for v1.4.5.\n"
red f2-anexo-v145 "$RUN/e5" "nomeia versao posterior do framework (1.4.5)"
# (f3) promessa com OUTRO major (v2.0.0) na seção: a pré-condição recusa (qualquer major)
E git -C "$RUN/e5" checkout -q -- CHANGELOG.md
changelog_144 "$RUN/e5/CHANGELOG.md" "$ANEXO" "$ANEXO  - The framework annex cure is planned for v2.0.0.\n"
red f3-anexo-v200 "$RUN/e5" "nomeia versao posterior do framework (2.0.0)"
# (f4) o item próprio «no release is assigned» trocado: nenhum item do anexo diz que a cura não tem release
E git -C "$RUN/e5" checkout -q -- CHANGELOG.md
changelog_144 "$RUN/e5/CHANGELOG.md" "$ANEXO" '  - The rest stays open; the cure ships later.\n'
red f4-so-frase-historica "$RUN/e5" "num item proprio"
# (f5) a frase de ligação do parágrafo 4 da headline tirada da [1.4.4]
E git -C "$RUN/e5" checkout -q -- CHANGELOG.md
changelog_144 "$RUN/e5/CHANGELOG.md" "- A new scan in the Bash guard blocks" "- A new check in the Bash guard blocks"
red f5-frase-de-ligacao "$RUN/e5" "paragrafo 4 da headline"
drop "$RUN/e5"
# (h) um commit fora do pacote trazido por `merge -s ours` (a árvore fora do pacote não muda)
prep "$RUN/e5" "$MAT"
E git -C "$RUN/e5" checkout -q -b lado "$MAT"
printf 'ensaio\n' >"$RUN/e5/docs/relmeta144-probe.txt"
E git -C "$RUN/e5" add -- docs/relmeta144-probe.txt
commit_in "$RUN/e5" "docs: ENSAIO lado fora do pacote"
E git -C "$RUN/e5" checkout -q --detach "$MAT"
E git -C "$RUN/e5" -c user.name=R -c user.email=r@example.invalid merge -q -s ours --no-edit lado
patch_on "$RUN/e5"
red h-merge-s-ours "$RUN/e5" "tocam fora do pacote"
drop "$RUN/e5"
# (i) um commit vazio depois da derivação
prep "$RUN/e5" "$MAT"
E git -C "$RUN/e5" -c user.name=R -c user.email=r@example.invalid commit -q --allow-empty -m "docs(PLAN-198): ENSAIO commit vazio"
patch_on "$RUN/e5"
red i-commit-vazio "$RUN/e5" "e vazio (nenhum caminho)"
drop "$RUN/e5"
# (g) Derivator-SHA256 alterado no sentinel (commitado): o envoltório recusa no passo 0
prep "$RUN/e5" "$MAT"
E python3 - "$RUN/e5/$SENT_REL" <<'PY'
import re, sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
t, n = re.subn(r"(?m)^Derivator-SHA256: [0-9a-f]", "Derivator-SHA256: x", t, count=1)
assert n == 1
open(p, "w", encoding="utf-8").write(t)
PY
E git -C "$RUN/e5" add -- "$SENT_REL"
commit_in "$RUN/e5" "plan(PLAN-198): ENSAIO Derivator-SHA256 alterado"
patch_on "$RUN/e5"
HG=$(hard_in "$RUN/e5" "$LOGS/e5-g-derivator-hard.log")
check "E5: Derivator-SHA256 alterado no sentinel: hard-relmeta.sh rc≠0 no passo 0 (log: e5-g-derivator-hard.log)" \
  eval '[ "$HG" != "0" ] && grep -qF "Derivator-SHA256" "$LOGS/e5-g-derivator-hard.log"'
drop "$RUN/e5"
# (j) o estado (b) mais um commit só do pacote que acrescenta ao diretório do derivador um argparse.py que sai 0
# (o derivador importa argparse): sem -I, o diretório do script entra no sys.path e o --verify sai rc 0 sem
# conferir nada; o hard-relmeta.sh roda o derivador com -I e recusa o land fora do pacote. Verde: o argparse.py
# sozinho, com o patch, deixa o hard-relmeta.sh em rc 0 (as conferências reais rodam e passam)
prep "$RUN/e5" "$MAT"
printf 'ensaio\n' >"$RUN/e5/docs/relmeta144-probe.txt"
E git -C "$RUN/e5" add -- docs/relmeta144-probe.txt
commit_in "$RUN/e5" "docs(PLAN-198): ENSAIO land fora do pacote"
printf 'raise SystemExit(0)\n' >"$RUN/e5/$D/argparse.py"
E git -C "$RUN/e5" add -- "$D/argparse.py"
commit_in "$RUN/e5" "plan(PLAN-198): ENSAIO argparse.py no diretório do derivador"
patch_on "$RUN/e5"
( cd "$RUN/e5" && E python3 "$APPLY_REL" --repo=. --verify ) >"$LOGS/e5-j-sem-I.log" 2>&1 && JV=0 || JV=$?
JH=$(hard_in "$RUN/e5" "$LOGS/e5-j-hard.log")
check "E5: land fora do pacote + argparse.py no pacote: o derivador SEM -I sai rc 0 sem saída; o hard-relmeta.sh (com -I) rc≠0 nomeando o Derived-From (logs: e5-j-*)" \
  eval '[ "$JV" = "0" ] && [ ! -s "$LOGS/e5-j-sem-I.log" ] && [ "$JH" != "0" ] && grep -qF "Derived-From do sentinel" "$LOGS/e5-j-hard.log"'
drop "$RUN/e5"
prep "$RUN/e5" "$MAT"
printf 'raise SystemExit(0)\n' >"$RUN/e5/$D/argparse.py"
E git -C "$RUN/e5" add -- "$D/argparse.py"
commit_in "$RUN/e5" "plan(PLAN-198): ENSAIO argparse.py no diretório do derivador"
patch_on "$RUN/e5"
JP=$(hard_in "$RUN/e5" "$LOGS/e5-j-hard-verde.log")
check "E5: só o argparse.py no pacote, com o patch: o hard-relmeta.sh (com -I) rc=0, com as 2 linhas verify OK do derivador (log: e5-j-hard-verde.log)" \
  eval '[ "$JP" = "0" ] && [ "$(grep -c "^verify OK: " "$LOGS/e5-j-hard-verde.log")" = "2" ]'
drop "$RUN/e5"

# ------------------------------------------------ registro de rail sintético (quando o do HEAD não vale)
rail_valido() {  # rail_valido <repo> <commit> — rc 0 se o registro no commit confere os 3 sha256 e o veredito
  E python3 - "$1" "$2" "$PATCH_REL" "$SENT_REL" "$DATA_REL" "$RAIL_REL" <<'PY'
import hashlib, subprocess, sys
repo, c, pp, sp, dp, rp = sys.argv[1:7]
blob = lambda p: subprocess.run(["git", "-C", repo, "cat-file", "blob", "%s:%s" % (c, p)], stdout=subprocess.PIPE, check=True).stdout
want = {"Rail-Subject-sha256": hashlib.sha256(blob(pp)).hexdigest(),
        "Rail-Sentinel-sha256": hashlib.sha256(blob(sp)).hexdigest(),
        "Rail-Data-sha256": hashlib.sha256(blob(dp)).hexdigest()}
try:
    linhas = blob(rp).decode("utf-8", "replace").split("\n")
except subprocess.CalledProcessError:
    sys.exit(1)
for k, v in want.items():
    if [ln for ln in linhas if ln.startswith(k + ":")] != ["%s: %s" % (k, v)]:
        sys.exit(1)
ver = [ln for ln in linhas if ln.startswith("Rail-Verdict:")]
sys.exit(0 if len(ver) == 1 and ver[0] in ("Rail-Verdict: APPROVE", "Rail-Verdict: DECLARED-P2") else 1)
PY
}
rail_sintetico() {  # rail_sintetico <repo> — grava e commita um registro SINTÉTICO sobre o HEAD do repo
  E python3 - "$1" "$PATCH_REL" "$SENT_REL" "$DATA_REL" "$RAIL_REL" <<'PY'
import hashlib, os, sys
repo, pp, sp, dp, rp = sys.argv[1:6]
h = lambda p: hashlib.sha256(open(os.path.join(repo, p), "rb").read()).hexdigest()
open(os.path.join(repo, rp), "w", encoding="utf-8").write(
    "# rail-record — ENSAIO (rehearse-relmeta144.sh): registro SINTETICO, nunca o do rail real\n\n"
    "Rail-Subject-sha256: %s\nRail-Sentinel-sha256: %s\nRail-Data-sha256: %s\nRail-Verdict: APPROVE\n"
    % (h(pp), h(sp), h(dp)))
PY
  ( cd "$1" && E git add -- "$RAIL_REL" && E git -c user.name=R -c user.email=r@example.invalid commit -q -m "plan($PLAN): ENSAIO registro de rail sintético" )
}
clone_roteiro() {  # clone_roteiro <remoto> <dir> <home> — os comandos do roteiro (bloco a2/a3)
  ( cd "$RUN" && S "$RUN/gnupg" "$3" git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= \
      --no-checkout --single-branch --branch main "file://$1" "$2" ) \
    && ( cd "$2" && S "$RUN/gnupg" "$3" git config core.hooksPath /dev/null \
      && S "$RUN/gnupg" "$3" git config core.fsmonitor false && S "$RUN/gnupg" "$3" git config core.untrackedCache false \
      && S "$RUN/gnupg" "$3" git config user.name Rehearsal && S "$RUN/gnupg" "$3" git config user.email rehearsal@example.invalid \
      && S "$RUN/gnupg" "$3" git checkout -q main )
}
NSHA=$(sha256f "$WORK/$NUCLEO")

# ------------------------------------------------ E6': P-KEY no Anchor com o allowlist REAL
if rail_valido "$WORK" "$MAT"; then
  ANCHOR_R="$MAT"
  printf 'E6'"'"': o registro do rail do HEAD é válido — Anchor = HEAD\n' >>"$TALLY"
else
  E git clone -q --no-hardlinks "$WORK" "$RUN/anc-r"
  rail_sintetico "$RUN/anc-r"
  ANCHOR_R=$(E git -C "$RUN/anc-r" rev-parse HEAD)
  REMOTE_R="$RUN/remote/r.git"
  E git init -q --bare "$REMOTE_R"
  E git -C "$REMOTE_R" fetch -q "$RUN/anc-r" "+HEAD:refs/heads/main"
  drop "$RUN/anc-r"
  printf 'E6'"'"': registro do rail SINTÉTICO sobre o HEAD — Anchor de ensaio %s\n' "$ANCHOR_R" >>"$TALLY"
fi
REMOTE_R=${REMOTE_R:-$REMOTE}
mkdir -p "$RUN/home-r"
clone_roteiro "$REMOTE_R" "$RUN/sign-r" "$RUN/home-r" >"$LOGS/e6p-clone.out" 2>&1 \
  && ok "E6': clone do roteiro no Anchor $ANCHOR_R" || ko "E6': clone do roteiro falhou (log: e6p-clone.out)"
( cd "$RUN/sign-r" && S "$RUN/gnupg-fora" "$RUN/home-r" bash "$ENTRADA" --nucleo-sha256="$NSHA" --dry-run "$DATA_REL" ) \
  >"$LOGS/e6p-sign.out" 2>&1 && PK=0 || PK=$?
check "E6': SIGN --dry-run com chave FORA do allowlist para exatamente em P-KEY, sem SIGN-PASSO (log: e6p-sign.out)" \
  eval '[ "$PK" = "1" ] && [ "$(sed -n 1p "$LOGS/e6p-sign.out")" = "SIGN-RECUSA: nenhuma chave secreta acessível ao gpg está no allowlist do commit $ANCHOR_R" ] && ! grep -q "SIGN-PASSO" "$LOGS/e6p-sign.out"'
check "E6': o clone ficou intocado (status vazio)" \
  eval '[ -z "$(S "$RUN/gnupg" "$RUN/home-r" git -C "$RUN/sign-r" status --porcelain --untracked-files=all --ignored)" ]'
drop "$RUN/sign-r"

# ------------------------------------------------ E6: o Anchor do ensaio com a chave descartável no allowlist
if [ "$SEM_SIGN" = "1" ]; then
  printf 'E6: pulado (--sem-sign)\n' | tee -a "$TALLY"
else
  # a chave entra no allowlist (SÓ neste clone) por um commit TEST ONLY ANTES de uma re-derivação: o
  # Derived-From passa a ser esse commit e o patch não muda (o escopo é o mesmo)
  DF=$(G cat-file blob "HEAD:$SENT_REL" | sed -n 's/^Derived-From: //p')
  E git clone -q --no-hardlinks "$WORK" "$RUN/anc-t"
  T() { E git -C "$RUN/anc-t" "$@"; }
  T config user.name Rehearsal
  T config user.email rehearsal@example.invalid
  T config commit.gpgsign false
  T checkout -q -B main "$DF"
  # as chaves do ensaio (a do E6 e a do HOME do SIM do E8; iguais quando importadas da mesma fonte), uma vez cada
  VISTAS=" "
  for fpr in "$KEY_FPR" $O_FPR; do
    case "$VISTAS" in *" $fpr "*) continue ;; esac
    VISTAS="$VISTAS$fpr "
    printf '# ENSAIO: chave descartável (rehearse-relmeta144), TEST ONLY\n%s\n' "$fpr" >>"$RUN/anc-t/$SIGNERS"
    if [ -f "$RUN/anc-t/$REGISTRY" ]; then
      printf '\n  - key_id: "%s"\n    key_type: "hot"\n    created_at: "2026-11-03T00:00:00Z"\n    expires_at: "2030-01-01T00:00:00Z"\n    revoked_at: null\n    notes: "ENSAIO: chave descartável (rehearse-relmeta144), TEST ONLY"\n' "$fpr" >>"$RUN/anc-t/$REGISTRY"
    fi
  done
  if [ -f "$RUN/anc-t/$REGISTRY" ]; then T add -- "$REGISTRY"; fi
  T add -- "$SIGNERS"
  T commit -q -m "test($PLAN): TEST ONLY — chave descartável do ensaio no allowlist do clone"
  T checkout -q "$MAT" -- "$D" "$SENT_REL"
  ( cd "$RUN/anc-t" && E bash "$DERIVE_REL" --commit ) >"$LOGS/e6-derive.log" 2>&1 && DR=0 || DR=$?
  check "E6: re-derivação com --commit sobre o TEST ONLY: rc=0, gates de corpus verdes (log: e6-derive.log)" [ "$DR" = "0" ]
  check "E6: o patch re-derivado tem o MESMO sha256 do relmeta.patch real ($REAL_PATCH_SHA)" \
    [ "$(sha256f "$RUN/anc-t/$PATCH_REL")" = "$REAL_PATCH_SHA" ]
  # o diff vai para um arquivo: sob pipefail, o rc 1 do diff (há diferença) reprovaria a cadeia
  G cat-file blob "HEAD:$SENT_REL" >"$RUN/sent-real.md"
  diff "$RUN/sent-real.md" "$RUN/anc-t/$SENT_REL" >"$LOGS/e6-sent.diff" 2>&1 || :
  check "E6: o sentinel re-derivado difere do real só na linha Derived-From (log: e6-sent.diff)" \
    eval '[ "$(grep -c "^[<>]" "$LOGS/e6-sent.diff")" = "2" ] && [ "$(grep -c "^< Derived-From: " "$LOGS/e6-sent.diff")" = "1" ] && [ "$(grep -c "^> Derived-From: " "$LOGS/e6-sent.diff")" = "1" ]'
  rail_sintetico "$RUN/anc-t"
  ANCHOR_T=$(T rev-parse HEAD)
  REMOTE_T="$RUN/remote/t.git"
  E git init -q --bare "$REMOTE_T"
  E git -C "$REMOTE_T" fetch -q "$RUN/anc-t" "+refs/heads/main:refs/heads/main"
  printf 'remoto: %s\nanchor: %s\nchave: %s\ngnupghome: %s\n' "$REMOTE_T" "$ANCHOR_T" "$KEY_FPR" "$RUN/gnupg" >"$RUN/e6-anchor.txt"
  drop "$RUN/anc-t"
  if [ "$SEM_SECO" = "1" ]; then
    printf 'E6: SIGN --dry-run pulado (--sem-seco); o E8 roda o SIGN real\n' | tee -a "$TALLY"
  else
    mkdir -p "$RUN/home-t"
    clone_roteiro "$REMOTE_T" "$RUN/sign-t" "$RUN/home-t" >"$LOGS/e6-clone.out" 2>&1 \
      && ok "E6: clone do roteiro no Anchor de ensaio $ANCHOR_T" || ko "E6: clone do roteiro falhou (log: e6-clone.out)"
    t0=$(date +%s)
    ( cd "$RUN/sign-t" && S "$RUN/gnupg" "$RUN/home-t" bash "$ENTRADA" --nucleo-sha256="$NSHA" --dry-run "$DATA_REL" ) \
      >"$LOGS/e6-sign-dry.out" 2>&1 && SD=0 || SD=$?
    t1=$(date +%s)
    check "E6: SIGN --dry-run: rc=0 e SIGN-ENSAIO em $((t1 - t0)) s (log: e6-sign-dry.out)" \
      eval '[ "$SD" = "0" ] && grep -q "^SIGN-ENSAIO: " "$LOGS/e6-sign-dry.out"'
    SOBRAS="$SOBRAS $(sed -n 's/^SIGN-FATO: logs em //p' "$LOGS/e6-sign-dry.out" | head -n 1)"
    drop "$RUN/sign-t"
  fi
fi

# ------------------------------------------------ E8: o roteiro do Owner, de ponta a ponta (NAO e SIM)
if [ -n "$OWNER_DIR" ] && [ "$SEM_SIGN" = "0" ]; then
  O="$OWNER_DIR"
  for f in ASSINAR-RM.sh owner-sign-rm.sh valores.txt ceo-f2-e4.py; do
    check "E8: $f presente na pasta do roteiro" [ -f "$O/$f" ]
  done
  check "E8: o ASSINAR-RM.sh pina o sha256 ATUAL do owner-sign-rm.sh e do valores.txt" \
    eval 'grep -qF "\"$(sha256f "$O/owner-sign-rm.sh")\"" "$O/ASSINAR-RM.sh" && grep -qF "\"$(sha256f "$O/valores.txt")\"" "$O/ASSINAR-RM.sh"'
  vlr() { sed -n "s/^$1=//p" "$O/valores.txt"; }
  check "E8: valores.txt — SIGN_SHA, CORE_SHA e DADOS_SHA = os do molde e do sign.tsv do HEAD; CONFERENCIA = o ceo-f2-e4.py da pasta, com o sha256 dele" \
    eval '[ "$(vlr SIGN_SHA)" = "$(sha256f "$WORK/$ENTRADA")" ] && [ "$(vlr CORE_SHA)" = "$NSHA" ] && [ "$(vlr DADOS_SHA)" = "$(sha256f "$WORK/$DATA_REL")" ] && [ "$(vlr CONFERENCIA_SHA)" = "$(sha256f "$O/ceo-f2-e4.py")" ] && [ "$(vlr CONFERENCIA)" = "$O/ceo-f2-e4.py" ]'
  check "E8: os caminhos do pacote no owner-sign-rm.sh são os do PLAN-198 (sentinel, dados, patch) e o molde o do PLAN-194" \
    eval 'grep -qxF "SENTINEL_RM=$SENT_REL" "$O/owner-sign-rm.sh" && grep -qxF "DADOS=$DATA_REL" "$O/owner-sign-rm.sh" && grep -qxF "P=$PATCH_REL" "$O/owner-sign-rm.sh" && grep -qxF "SE=$SENT_REL" "$O/owner-sign-rm.sh" && grep -qxF "S=$ENTRADA" "$O/owner-sign-rm.sh" && ! grep -q "PLAN-194/relmeta" "$O/owner-sign-rm.sh"'
  check "E8: o ceo-f2-e4.py da pasta mapeia o pacote relmeta para o PLAN-198" \
    eval 'grep -qF "\"relmeta\": (\"PLAN-198\", \"relmeta\", True)" "$O/ceo-f2-e4.py"'
  # o ambiente de login do Owner: um Terminal novo = zsh -il a partir de env -i
  OE="$RUN/owner-env.txt"
  env -i HOME="$HOME" USER="${USER:-}" LOGNAME="${LOGNAME:-${USER:-}}" SHELL=/bin/zsh TERM=xterm-256color \
    LANG=en_US.UTF-8 /bin/zsh -il -c env >"$OE" 2>/dev/null || :
  check "E8: ambiente de login do Owner capturado por zsh -il ($(cut -d= -f1 "$OE" | sort | tr '\n' ' '))" \
    eval 'grep -q "^PATH=" "$OE"'
  OPATH=$(sed -n 's/^PATH=//p' "$OE")
  LANCA=()
  ROT=()
  while IFS= read -r kv; do
    case "${kv%%=*}" in PWD|OLDPWD|SHLVL|_) continue ;; esac
    LANCA+=("$kv")
    case "${kv%%=*}" in HOME|PATH|GPG_TTY|CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS) continue ;; esac
    ROT+=("$kv")
  done <"$OE"
  # o lançador no ambiente do Owner, sem terminal: passa nos pins e na trava de nomes e para no
  # início do roteiro, antes de criar qualquer coisa
  env -i "${LANCA[@]}" bash "$O/ASSINAR-RM.sh" </dev/null >"$LOGS/e8-lancador.out" 2>&1 && LR=0 || LR=$?
  check "E8: o ASSINAR-RM.sh no ambiente do Owner passa no sha e na trava de nomes e para em «a entrada não é um terminal» (log: e8-lancador.out)" \
    eval '[ "$LR" = "3" ] && grep -qF "motivo: a entrada não é um terminal" "$LOGS/e8-lancador.out" && ! grep -qF "PARE antes de começar" "$LOGS/e8-lancador.out"'
  # o roteiro de verdade, contra o remoto do E6, trocando SÓ a URL e o ANCORA
  sed -e "s|^URL=.*|URL=file://$REMOTE_T|" -e "s|^ANCORA=.*|ANCORA=$ANCHOR_T|" "$O/valores.txt" >"$RUN/valores-ensaio.txt"
  VSHA=$(sha256f "$RUN/valores-ensaio.txt")
  alimenta() {  # alimenta <resposta> <log> — digita a resposta quando a tela pede; mantém o pipe aberto até o roteiro terminar
    local i=0 sent=0
    while [ "$i" -lt 14400 ]; do
      if [ "$sent" = "0" ] && grep -qF "Digite SIM e Enter para assinar." "$2" 2>/dev/null; then
        sleep 3; printf '%s\n' "$1"; sent=1
      fi
      if grep -qE "^RM-PUBLICADO |^PARE|^ENCERRADO" "$2" 2>/dev/null; then sleep 2; return 0; fi
      sleep 0.5; i=$((i + 1))
    done
  }
  roteiro() {  # roteiro <HOME falso> <resposta> <log> — o owner-sign-rm.sh sob script (pseudo-TTY) e zsh -il
    local h="$1"
    # o zsh -il do HOME falso lê só os arquivos do sistema e este .zshrc, que devolve o PATH do login
    # do Owner com o osascript mudo na frente (o path_helper do /etc/zprofile o reordenaria)
    printf 'export PATH=%q\n' "$h/fakebin:$OPATH" >"$h/.zshrc"
    : >"$h/.zshenv"
    : >"$3"
    alimenta "$2" "$3" | env -i "${ROT[@]}" HOME="$h" PATH="$h/fakebin:$OPATH" \
      script -q /dev/null /bin/zsh -il -c 'exec bash "$1" "$2" "$3"' zsh "$O/owner-sign-rm.sh" "$RUN/valores-ensaio.txt" "$VSHA" >"$3" 2>&1
  }
  # 1.ª execução: NAO — nada assinado, nada publicado, o clone intocado
  NLOG="$LOGS/e8-owner-nao.log"
  roteiro "$OHN" NAO "$NLOG" && NRC=0 || NRC=$?
  SOBRAS="$SOBRAS $(tr -d '\r' <"$NLOG" | sed -n 's/^registros desta execução: //p' | head -n 1)"
  check "E8 (NAO): rc=2 e «ENCERRADO: resposta diferente de SIM», sem nenhuma linha SIGN- (log: e8-owner-nao.log)" \
    eval '[ "$NRC" = "2" ] && tr -d "\r" <"$NLOG" | grep -qF "ENCERRADO: resposta diferente de SIM. Nada foi assinado nem publicado." && ! tr -d "\r" <"$NLOG" | grep -q "^SIGN-"'
  check "E8 (NAO): o roteiro chegou à tela do texto da tag (PRE-SIGN-OK e a headline lida do Anchor)" \
    eval 'tr -d "\r" <"$NLOG" | grep -qxF "PRE-SIGN-OK" && tr -d "\r" <"$NLOG" | grep -qF "Headline: Maintenance release (PLAN-198)."'
  check "E8 (NAO): o remoto segue no Anchor do E6 ($ANCHOR_T)" \
    [ "$(E git -C "$REMOTE_T" rev-parse refs/heads/main)" = "$ANCHOR_T" ]
  NCL="$OHN/rm-s366/relmeta"
  check "E8 (NAO): o clone do roteiro segue no Anchor, sem alteração, sem a .asc (status vazio)" \
    eval '[ "$(E git -C "$NCL" rev-parse HEAD)" = "$ANCHOR_T" ] && [ -z "$(E git -C "$NCL" status --porcelain --untracked-files=all)" ] && [ ! -e "$NCL/$SENT_REL.asc" ]'
  # 2.ª execução: SIM — o SIGN, o land, a conferência mecânica, o push e o publicado
  OLOG="$LOGS/e8-owner-sim.log"
  t0=$(date +%s)
  roteiro "$OH" SIM "$OLOG" && ORC=0 || ORC=$?
  t1=$(date +%s)
  PUB=$(tr -d '\r' <"$OLOG" | sed -n 's/^RM-PUBLICADO \([0-9a-f]\{40\}\) .*/\1/p')
  SOBRAS="$SOBRAS $(tr -d '\r' <"$OLOG" | sed -n 's/^registros desta execução: //p' | head -n 1)"
  SOBRAS="$SOBRAS $(tr -d '\r' <"$OLOG" | sed -n 's/^SIGN-FATO: logs em //p' | head -n 1)"
  check "E8 (SIM): owner-sign-rm.sh de ponta a ponta: rc=0 e RM-PUBLICADO em $((t1 - t0)) s (log: e8-owner-sim.log)" \
    eval '[ "$ORC" = "0" ] && [ -n "$PUB" ]'
  check "E8 (SIM): o remoto está no commit publicado, cujo pai único é o Anchor do E6" \
    eval '[ "$(E git -C "$REMOTE_T" rev-parse refs/heads/main)" = "$PUB" ] && [ "$(E git -C "$REMOTE_T" rev-list --parents -n 1 "$PUB")" = "$PUB $ANCHOR_T" ]'
  check "E8 (SIM): o commit publicado difere do Anchor só nos 3 alvos, no sentinel e na .asc" \
    eval '[ "$(E git -C "$REMOTE_T" diff-tree -r --no-commit-id --name-only "$ANCHOR_T" "$PUB" | sort | tr "\n" " ")" = "$(printf "%s\n" "$T_MAN" "$T_REL" "$T_TST" "$SENT_REL" "$SENT_REL.asc" | sort | tr "\n" " ")" ]'
  check "E8 (SIM): o SIGN rodou as 5 linhas hard e as passou (SIGN-FATO hard 1..5 rc 0) e terminou em SIGN-OK" \
    eval '[ "$(tr -d "\r" <"$OLOG" | grep -cE "^SIGN-FATO: hard [1-5] saiu rc 0 ")" = "5" ] && tr -d "\r" <"$OLOG" | grep -q "^SIGN-OK: commit $PUB "'
  check "E8 (SIM): o sentinel publicado tem os 4 campos preenchidos e a .asc verifica com a chave descartável" \
    eval 'E git -C "$REMOTE_T" cat-file blob "$PUB:$SENT_REL" >"$RUN/sent-pub.md" && E git -C "$REMOTE_T" cat-file blob "$PUB:$SENT_REL.asc" >"$RUN/sent-pub.md.asc" && ! grep -q "TO-FILL-BY-SIGN" "$RUN/sent-pub.md" && grep -qx "Anchor-SHA: $ANCHOR_T" "$RUN/sent-pub.md" && env -i HOME="$RUN/home" PATH="$TOOLPATH" GNUPGHOME="$OH/.gnupg" gpg --batch --verify "$RUN/sent-pub.md.asc" "$RUN/sent-pub.md" >"$LOGS/e8-verify.out" 2>&1'
  E git -C "$REMOTE_T" log -1 --format='%H%n%P%n%an <%ae>%n%B' "$PUB" >"$LOGS/e8-land-commit.txt" 2>&1 || :
  E git -C "$REMOTE_T" diff-tree -r --no-commit-id --name-status "$ANCHOR_T" "$PUB" >>"$LOGS/e8-land-commit.txt" 2>&1 || :
  for marca in AMBIENTE-OK PREPARO-OK CADEIA-OK ANCORA-OK PRE-SIGN-OK SIGN-RC=0 LAND-OK "PUSH-LIBERADO $PUB" PUSH-OK PUBLICADO-OK; do
    check "E8 (SIM): o roteiro imprimiu «${marca}»" eval 'tr -d "\r" <"$OLOG" | grep -qxF "$marca"'
  done
fi

python3 -I -B "$GUARD" verify --repo "$SRC_REPO" --from "$RUN/caller-antes.json" >"$LOGS/caller-depois.out" 2>&1 && CG=0 || CG=$?
check "caller_repo_guard: HEAD, symbolic-ref e refs do repositório chamador iguais antes e depois do ensaio (log: caller-depois.out)" [ "$CG" = "0" ]
printf '\n==================== PLACAR: %s PASS / %s FAIL ====================\n' "$PASS" "$FAIL"
printf 'logs: %s\n' "$LOGS"
FIM=1
[ "$FAIL" = "0" ]
