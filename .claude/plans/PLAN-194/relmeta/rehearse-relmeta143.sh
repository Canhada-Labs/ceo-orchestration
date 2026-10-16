#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: ensaio de UM uso da relmeta-143
# (PLAN-194, RM da v1.4.3); roda o derive, o derivador, o hard-relmeta.sh e o
# SIGN do molde sign-min numa cópia descartável, nunca no checkout de onde foi
# chamado. Ferramenta do construtor: nenhuma linha hard dos dados a chama.
# rehearse-relmeta143.sh — ensaio PONTA A PONTA da relmeta-143.
#
#   bash .claude/plans/PLAN-194/relmeta/rehearse-relmeta143.sh [--keep] [--sem-sign] [--owner-dir DIR]
#
# Roda sobre o HEAD do checkout de onde é chamado, que tem de ter os materiais
# commitados. Tudo dentro de um diretório novo (mktemp) sob $REHEARSE_BASE
# (padrão: $TMPDIR), com piso de disco de 30 GB livres:
#   E1. um remoto «bare» descartável com o HEAD como `main` e a tag v1.4.2;
#       v1.4.2^{commit} = b55084da;
#   E2. âncoras: 8/8 PASS no HEAD; na árvore da v1.4.2 com o CHANGELOG do HEAD
#       sobreposto, a parte de TEXTO passa em todas e a de CÓDIGO falha nas 6
#       esperadas, cada uma nomeando o motivo esperado (ccfloor e annex passam
#       por desenho); na v1.4.2 pura, toda parte de texto falha; o --verify no
#       HEAD SEM o patch falha;
#   E3. derivação idempotente (duas vezes, e depois do commit dos materiais): o
#       mesmo patch, byte a byte o commitado;
#   E4. num clone com `git apply --index relmeta.patch`, cada linha hard dos
#       dados, em ordem, sai rc 0 (pytest com resumo só de aprovados), e os
#       testes de release (test_release_workflow_asserts.py e
#       test_release_bump_sites.py) passam;
#   E5. vermelhos do verificador, cada um num estado novo: land fora do pacote
#       depois da derivação (assunto com plano novo, e assunto só com PLAN-194),
#       hex do manifesto trocado, palavra da headline trocada, seção do texto
#       da tag alterada, Derivator-SHA256 alterado, CHANGELOG com [Unreleased],
#       anexo citando v1.4.4 ou v2.0.0, o item «no release is assigned» trocado
#       (sobra só a frase histórica), um commit fora do pacote trazido por
#       `merge -s ours` e um commit vazio; e, no E2, a âncora cond67 reprova um
#       append_entry sintético de duas travas;
#   E6. o SIGN do molde em --dry-run num clone feito pelos comandos do roteiro,
#       com HOME vazio e env -i com os nomes do roteiro: uma chave descartável
#       entra no allowlist por um commit «TEST ONLY (PLAN-194)» ANTES de uma
#       re-derivação (o patch tem de sair com o MESMO sha256 do real) e um
#       registro de rail SINTÉTICO fecha o Anchor do ensaio; espera SIGN-ENSAIO
#       e mede o tempo (sem --sem-sign);
#   E6'. sobre o Anchor com o allowlist REAL (o HEAD, se o registro do rail dele
#       já é válido; senão o HEAD mais um registro sintético), um GNUPGHOME só
#       com uma chave descartável FORA do allowlist: o SIGN --dry-run tem de
#       parar exatamente em P-KEY;
#   E7. `release.sh bump --dry-run` na árvore com o patch: rc 0, «target 1.4.3»
#       e árvore restaurada;
#   E8. com --owner-dir DIR (a pasta do roteiro do Owner, fora do repositório:
#       ASSINAR-RM.sh, owner-sign-rm.sh, valores.txt e ceo-f2-e4.py): os pins do
#       lançador e do arquivo de valores conferem; o lançador, no ambiente de
#       login do Owner (`zsh -il -c env` a partir de env -i), passa nas próprias
#       conferências e para na falta de terminal; e o owner-sign-rm.sh roda de
#       ponta a ponta, de verdade, sob `script` (pseudo-TTY), com HOME falso, uma
#       segunda chave descartável no mesmo commit TEST ONLY do E6 e o valores.txt
#       com SÓ a URL (o remoto do E6) e o ANCORA (o Anchor do E6) trocados: espera
#       RM-PUBLICADO, o remoto no commit publicado e o pai dele no Anchor.
# Sai 0 só se todos os itens passarem. Com rc 0 e sem --keep, apaga o próprio
# diretório; com falha (ou --keep) ele fica, com os logs, e o caminho do remoto
# do E6 e o Anchor dele ficam em $RUN/e6-anchor.txt.
#
# O único caminho fora de $REHEARSE_BASE é um diretório curto para os sockets
# do gpg-agent (o macOS limita o caminho de socket a ~104 bytes): mktemp sob
# /tmp, esvaziado e removido no fim.
set -euo pipefail

_genv=""
for _v in $(git rev-parse --local-env-vars); do
  if [ -n "${!_v+x}" ]; then _genv="$_genv $_v"; fi
done
[ -z "$_genv" ] || { printf 'variáveis git herdadas:%s — rode sem elas (unset%s)\n' "$_genv" "$_genv" >&2; exit 2; }

KEEP=0
SEM_SIGN=0
OWNER_DIR=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --keep) KEEP=1; shift ;;
    --sem-sign) SEM_SIGN=1; shift ;;
    --owner-dir)
      [ "$#" -ge 2 ] || { printf 'uso: --owner-dir <pasta do roteiro do Owner>\n' >&2; exit 2; }
      OWNER_DIR=$(cd "$2" && pwd -P) || { printf 'pasta do roteiro ilegível: %s\n' "$2" >&2; exit 2; }
      shift 2 ;;
    *) printf 'uso: bash %s [--keep] [--sem-sign] [--owner-dir DIR]\n' "$0" >&2; exit 2 ;;
  esac
done

PACK_DIR=$(cd "$(dirname "$0")" && pwd -P)
SRC_REPO=$(cd "$PACK_DIR/../../../.." && pwd -P)
[ -e "$SRC_REPO/.git" ] || { printf 'não achei o repo em %s\n' "$SRC_REPO" >&2; exit 2; }
PLAN=PLAN-194
D=.claude/plans/PLAN-194/relmeta
SENT_REL=.claude/plans/PLAN-194/relmeta-approved.md
APPLY_REL="$D/apply-relmeta143-edits.py"
DERIVE_REL="$D/derive-relmeta143.sh"
HARD_REL="$D/hard-relmeta.sh"
PATCH_REL="$D/relmeta.patch"
DATA_REL="$D/sign.tsv"
RAIL_REL="$D/rail-record.md"
ENTRADA=.claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
NUCLEO=.claude/plans/PLAN-194/sign-min/sign_min.py
BASE_TAG=v1.4.2
BASE_SHA=b55084da6dd8e4a05fc9893b2690df8aebcfd0ca
TARGET_BASE=1.4.3
T_REL=.claude/scripts/local/release.sh
T_MAN=.claude/governance/gate-scripts-manifest.txt
T_TST=.claude/scripts/tests/test_release_bump_sites.py
SIGNERS=.claude/sentinel-signers.txt
REGISTRY=.claude/security/sentinel-signers-registry.yaml

BASE=${REHEARSE_BASE:-${TMPDIR:-/tmp}}
LIVRE=$(df -Pk "$BASE" | awk 'NR == 2 {print $4}')
[ "$LIVRE" -ge $((30 * 1024 * 1024)) ] || { printf 'disco: %s KiB livres em %s (piso: 30 GB)\n' "$LIVRE" "$BASE" >&2; exit 2; }
RUN=$(mktemp -d "${BASE%/}/rehearse-relmeta143.XXXXXX")
RUN=$(cd "$RUN" && pwd -P)
SOCK=$(mktemp -d /tmp/g.XXXXXX)
chmod 700 "$SOCK"
mkdir -p "$RUN/home" "$RUN/tmp" "$RUN/logs" "$RUN/gnupg" "$RUN/gnupg-fora"
chmod 700 "$RUN/gnupg" "$RUN/gnupg-fora"
LOGS="$RUN/logs"
PASS=0; FAIL=0; TALLY="$RUN/tally.txt"; : >"$TALLY"
OH=""
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
  if [ -n "$OH" ]; then
    GNUPGHOME="$OH/.gnupg" gpgconf --kill gpg-agent >/dev/null 2>&1 || printf 'aviso: gpg-agent do E8 não parou\n' >&2
  fi
  for s in "$SOCK"/*; do
    if [ -S "$s" ]; then rm -f "$s"; fi
  done
  rmdir "$SOCK" 2>/dev/null || printf 'aviso: %s não ficou vazio\n' "$SOCK" >&2
  if [ "$FIM" = "1" ] && [ "$FAIL" = "0" ] && [ "$KEEP" = "0" ] && [ "$PASS" -gt 0 ]; then
    # limpeza confinada: o diretório deste ensaio, o HOME curto do E8 e os
    # temporários que os SIGNs e o roteiro deste ensaio anunciaram, pelo caminho
    # exato e pelo prefixo de cada um, sem seguir link
    python3 -I -B -c 'import os, shutil, sys
for p in sys.argv[1:]:
    b = os.path.basename(p)
    if not p or os.path.islink(p) or not os.path.isdir(p):
        continue
    if not b.startswith(("rehearse-relmeta143.", "o.", "sign-min.", "owner-sign-rm.")):
        sys.exit(1)
    shutil.rmtree(p)' "$RUN" ${OH:+"$OH"} ${SOBRAS:+$SOBRAS} || printf 'aviso: não apaguei %s\n' "$RUN" >&2
  else
    printf 'diretório do ensaio mantido: %s\n' "$RUN" >&2
  fi
}
trap 'rc=$?; if [ "$FIM" != "1" ]; then [ "$rc" != "0" ] || rc=1; printf "ensaio INTERROMPIDO antes do placar (rc %s)\n" "$rc" >&2; fi; cleanup; exit $rc' EXIT
printf 'ensaio em %s\n' "$RUN"

TOOLPATH=""
for t in git gpg gpgconf python3 shasum script awk sed bash jq; do
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

# ------------------------------------------------ gpg descartável (duas chaves, dois GNUPGHOME)
for g in gnupg gnupg-fora; do
  for s in S.gpg-agent S.gpg-agent.extra S.gpg-agent.browser S.gpg-agent.ssh; do
    printf '%%Assuan%%\nsocket=%s/%s.%s\n' "$SOCK" "$g" "$s" >"$RUN/$g/$s"
  done
done
E gpg --batch --passphrase '' --quick-gen-key \
  'Rehearsal Throwaway <rehearsal@example.invalid>' ed25519 sign never >"$LOGS/gpg-gen.out" 2>&1
KEY_FPR=$(E gpg --with-colons --list-secret-keys | awk -F: '$1=="fpr"{print $10; exit}')
check "chave descartável gerada no GNUPGHOME do ensaio" [ -n "$KEY_FPR" ]
E env GNUPGHOME="$RUN/gnupg-fora" gpg --batch --passphrase '' --quick-gen-key \
  'Rehearsal Outside <outside@example.invalid>' ed25519 sign never >"$LOGS/gpg-gen-fora.out" 2>&1
FORA_FPR=$(E env GNUPGHOME="$RUN/gnupg-fora" gpg --with-colons --list-secret-keys | awk -F: '$1=="fpr"{print $10; exit}')
check "chave descartável FORA do allowlist gerada noutro GNUPGHOME" [ -n "$FORA_FPR" ]
O_FPR=""
if [ -n "$OWNER_DIR" ] && [ "$SEM_SIGN" = "0" ]; then
  # E8: HOME falso CURTO (os sockets do gpg-agent vivem no próprio GNUPGHOME), com
  # uma chave descartável sem senha, a identidade git e a base de usuário do python
  # (o roteiro a lê por `python3 -I`, que ignora PYTHONUSERBASE) apontando para a real
  OH=$(mktemp -d /tmp/o.XXXXXX)
  OH=$(cd "$OH" && pwd -P)
  mkdir -p "$OH/.gnupg" "$OH/fakebin"
  chmod 700 "$OH/.gnupg"
  env -i HOME="$OH" PATH="$TOOLPATH" GNUPGHOME="$OH/.gnupg" LANG=en_US.UTF-8 gpg --batch --passphrase '' \
    --quick-gen-key 'Rehearsal Owner <owner@example.invalid>' ed25519 sign never >"$LOGS/gpg-gen-e8.out" 2>&1
  O_FPR=$(env -i HOME="$OH" PATH="$TOOLPATH" GNUPGHOME="$OH/.gnupg" gpg --with-colons --list-secret-keys \
    | awk -F: '$1=="fpr"{print $10; exit}')
  check "E8: chave descartável do Owner gerada no HOME falso do E8" [ -n "$O_FPR" ]
  env -i HOME="$OH" PATH="$TOOLPATH" git config --global user.name 'Rehearsal Owner'
  env -i HOME="$OH" PATH="$TOOLPATH" git config --global user.email 'owner@example.invalid'
  UB_FALSO=$(env -i HOME="$OH" PATH="$TOOLPATH" python3 -I -c 'import site; print(site.getuserbase())')
  mkdir -p "$(dirname "$UB_FALSO")"
  ln -s "$USERBASE" "$UB_FALSO"
  # um osascript mudo: o aviso da senha não vira notificação na tela durante o ensaio
  printf '#!/bin/sh\nexit 0\n' >"$OH/fakebin/osascript"
  chmod 755 "$OH/fakebin/osascript"
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

# ------------------------------------------------ estáticos
for f in derive-relmeta143.sh hard-relmeta.sh rehearse-relmeta143.sh; do
  check "bash 3.2 -n $f" /bin/bash -n "$WORK/$D/$f"
  m=$(G ls-files --stage -- "$D/$f" | awk '{print $1}')
  check "modo no índice de $f = 100644 (R8)" [ "$m" = "100644" ]
done
E python3 -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' \
  "$WORK/$APPLY_REL" >"$LOGS/compile.out" 2>&1 && ok "o derivador compila (python3)" || ko "o derivador não compila (log: compile.out)"
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
# controle da âncora cond67: duas travas separadas reprovam; uma trava só passa; o audit_log.py real passa
E python3 - "$WORK/$APPLY_REL" "$WORK/.claude/hooks/audit_log.py" >"$LOGS/cond67-controle.out" 2>&1 <<'PY' && C67=0 || C67=$?
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
s.loader.exec_module(m); print(len(m.CLAIMS))' "$WORK/$APPLY_REL")
check "E2: âncoras no HEAD: rc=0 e $NCLAIMS/$NCLAIMS PASS (log: claims-head.out)" \
  eval '[ "$CH" = "0" ] && [ "$NCLAIMS" = "8" ] && [ "$(grep -c "^PASS  " "$LOGS/claims-head.out")" = "$NCLAIMS" ]'
E git clone -q --no-hardlinks "$WORK" "$RUN/base"
E git -C "$RUN/base" checkout -q --detach "$BASE_SHA"
G show "HEAD:CHANGELOG.md" >"$RUN/base/CHANGELOG.md"
E python3 "$WORK/$APPLY_REL" --repo "$RUN/base" --claims-only >"$LOGS/claims-base.out" 2>&1 && CB=0 || CB=$?
# o motivo de CÓDIGO esperado por âncora na v1.4.2 (vazio = PASS por desenho)
red_ok() {  # red_ok <arquivo> — confere a parte de código e a de texto de cada âncora
  E python3 - "$1" <<'PY'
import re, sys
esperado = {
    "ccfloor": None,
    "harness": "REPLAY_FIXTURES_REL=['.claude/hooks/tests/fixtures/harness-config/replay']",
    "cond67": "append_entry chama read_prev_hmac FORA do with FileLock",
    "defaultmode": "DEFAULT_MODE_BASELINE ausente",
    "cenv": "com kwargs ['action',",
    "fixes": ".claude/scripts/status.py ainda passa --as-json",
    "codex": "package_version='0.156.1'",
    "annex": None,
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
check "E2: v1.4.2 + CHANGELOG do HEAD: rc=1; texto PASS nas 8; código FAIL nas 6 esperadas, cada uma pelo motivo dela; ccfloor e annex PASS (log: claims-base.out, red-check.out)" \
  eval '[ "$CB" = "1" ] && [ "$RB" = "0" ]'
E git -C "$RUN/base" checkout -q -- CHANGELOG.md
E python3 "$WORK/$APPLY_REL" --repo "$RUN/base" --claims-only >"$LOGS/claims-base-pura.out" 2>&1 && CP=0 || CP=$?
check "E2: v1.4.2 pura: rc=1 e a parte de texto FAIL nas 8 (sem a seção [1.4.3]) (log: claims-base-pura.out)" \
  eval '[ "$CP" = "1" ] && [ "$(grep -c "^      texto:  FAIL" "$LOGS/claims-base-pura.out")" = "8" ]'
E python3 -I -B -c 'import os, shutil, sys
p = sys.argv[1]
if os.path.basename(p) != "base" or os.path.islink(p):
    sys.exit(1)
shutil.rmtree(p)' "$RUN/base"
E bash -c "cd '$WORK' && python3 '$APPLY_REL' --repo=. --verify" >"$LOGS/verify-sem-patch.out" 2>&1 && VS=0 || VS=$?
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
check "E4: os dados têm 6 linhas hard, todas executadas" [ "$k" = "6" ]
( cd "$RUN/e4" && E python3 -m pytest -p no:cacheprovider -q -rfE --tb=short \
    .claude/scripts/tests/test_release_workflow_asserts.py .claude/scripts/tests/test_release_bump_sites.py ) \
  >"$LOGS/e4-release-tests.log" 2>&1 && RT=0 || RT=$?
check "E4: test_release_workflow_asserts.py + test_release_bump_sites.py com o patch: rc=0 ($(awk 'NF {l = $0} END {print l}' "$LOGS/e4-release-tests.log"))" [ "$RT" = "0" ]
check "E4: a árvore com o patch segue igual ao índice depois das linhas hard (só o patch staged)" \
  eval '[ -z "$(E git -C "$RUN/e4" status --porcelain --untracked-files=no | grep -v "^M  ")" ] && [ "$(E git -C "$RUN/e4" diff --cached --name-only | sort | tr "\n" " ")" = "$(printf "%s\n" "$T_MAN" "$T_REL" "$T_TST" | sort | tr "\n" " ")" ]'

# ------------------------------------------------ E7: o driver em 1.4.3, bump --dry-run
# o bump recusa árvore suja: o patch entra num commit do ensaio, como o SIGN o deixaria
commit_in "$RUN/e4" "ENSAIO: relmeta.patch aplicado"
( cd "$RUN/e4" && E bash "$T_REL" bump --dry-run --npm-readme-reviewed --today 2026-10-16 ) \
  >"$LOGS/bump-dry.out" 2>&1 && BRC=0 || BRC=$?
NBUMP=$(grep ' | ' "$LOGS/bump-dry.out" | wc -l | tr -d ' ')
check "E7: release.sh bump --dry-run em ${TARGET_BASE}: rc=0, ${NBUMP} arquivo(s) no diffstat, «target ${TARGET_BASE}» e árvore restaurada (log: bump-dry.out)" \
  eval '[ "$BRC" = "0" ] && [ "$NBUMP" -gt 0 ] && grep -q "target $TARGET_BASE" "$LOGS/bump-dry.out" && [ -z "$(E git -C "$RUN/e4" status --porcelain --untracked-files=all)" ]'
drop "$RUN/e4"

# ------------------------------------------------ E5: vermelhos do verificador
verify_in() {  # verify_in <dir> <log> — ecoa o rc do --verify
  local rc=0
  ( cd "$1" && E python3 "$APPLY_REL" --repo=. --verify ) >"$2" 2>&1 || rc=$?
  printf '%s' "$rc"
}
hard_in() {  # hard_in <dir> <log> — ecoa o rc do hard-relmeta.sh
  local rc=0
  ( cd "$1" && E bash "$HARD_REL" ) >"$2" 2>&1 || rc=$?
  printf '%s' "$rc"
}
red() {  # red <nome> <dir> <padrão> [hard] — o --verify (e, com hard, o envoltório) recusa nomeando
  local v h=0 desc="$1"
  v=$(verify_in "$2" "$LOGS/e5-$1-verify.log")
  if [ "${4:-}" = "hard" ]; then h=$(hard_in "$2" "$LOGS/e5-$1-hard.log"); desc="$desc (e o hard-relmeta.sh rc=$h)"; fi
  if [ "$v" != "0" ] && grep -qF -- "$3" "$LOGS/e5-$1-verify.log" && { [ "${4:-}" != "hard" ] || [ "$h" != "0" ]; }; then
    ok "E5: $desc: --verify rc=$v nomeando «$3»"
  else
    ko "E5: $desc: --verify rc=$v; padrão «$3» $(grep -qF -- "$3" "$LOGS/e5-$1-verify.log" && printf presente || printf AUSENTE) (log: e5-$1-verify.log)"
  fi
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
printf 'ensaio\n' >"$RUN/e5/docs/relmeta143-probe.txt"
E git -C "$RUN/e5" add -- docs/relmeta143-probe.txt
commit_in "$RUN/e5" "chore(PLAN-196): ENSAIO land fora do pacote"
patch_on "$RUN/e5"
red a-plano-novo "$RUN/e5" "Derived-From do sentinel"
drop "$RUN/e5"
# (b) land fora do pacote citando só PLAN-194 (o escopo não muda; o Derived-From pega)
prep "$RUN/e5" "$MAT"
printf 'ensaio\n' >"$RUN/e5/docs/relmeta143-probe.txt"
E git -C "$RUN/e5" add -- docs/relmeta143-probe.txt
commit_in "$RUN/e5" "docs(PLAN-194): ENSAIO land fora do pacote"
patch_on "$RUN/e5"
red b-so-plan194 "$RUN/e5" "Derived-From do sentinel"
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
red c-manifesto "$RUN/e5" "gate-scripts-manifest.txt na arvore difere" hard
drop "$RUN/e5"
# (d) uma palavra da headline trocada no driver
fresh "$RUN/e5" "$MAT"
E python3 - "$RUN/e5/$T_REL" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
assert t.count("Release de manutencao") == 1
open(p, "w", encoding="utf-8").write(t.replace("Release de manutencao", "Release de MANUTENCAO", 1))
PY
red d-headline "$RUN/e5" "release.sh na arvore difere" hard
drop "$RUN/e5"
# (e) a seção do texto da tag alterada no sentinel (commitada: o --verify lê o sentinel do HEAD)
prep "$RUN/e5" "$MAT"
E python3 - "$RUN/e5/$SENT_REL" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
assert t.count("Headline: Release de manutencao") == 1
open(p, "w", encoding="utf-8").write(t.replace("Headline: Release de manutencao", "Headline: Release de Manutencao", 1))
PY
E git -C "$RUN/e5" add -- "$SENT_REL"
commit_in "$RUN/e5" "plan(PLAN-194): ENSAIO texto da tag alterado"
patch_on "$RUN/e5"
red e-texto-da-tag "$RUN/e5" "secao do texto da tag difere"
drop "$RUN/e5"
# (f1) CHANGELOG com [Unreleased] na árvore; (f2) anexo citando v1.4.4
fresh "$RUN/e5" "$MAT"
E python3 - "$RUN/e5/CHANGELOG.md" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
i = t.index("## [1.4.3]")
open(p, "w", encoding="utf-8").write(t[:i] + "## [Unreleased]\n\n- ensaio\n\n" + t[i:])
PY
red f1-unreleased "$RUN/e5" "[Unreleased]"
E git -C "$RUN/e5" checkout -q -- CHANGELOG.md
E python3 - "$RUN/e5/CHANGELOG.md" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
old = "  - **The rest stays open, and no release is assigned to their cure.**\n"
assert t.count(old) == 1
open(p, "w", encoding="utf-8").write(t.replace(old, old + "  - Planned for v1.4.4.\n", 1))
PY
red f2-anexo-v144 "$RUN/e5" "nomeia versao posterior do framework (1.4.4)"
# (f3) promessa com OUTRO major (v2.0.0) na seção: a pré-condição recusa (qualquer major)
E git -C "$RUN/e5" checkout -q -- CHANGELOG.md
E python3 - "$RUN/e5/CHANGELOG.md" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
old = "  - **The rest stays open, and no release is assigned to their cure.**\n"
assert t.count(old) == 1
open(p, "w", encoding="utf-8").write(t.replace(old, old + "  - The framework annex cure is planned for v2.0.0.\n", 1))
PY
red f3-anexo-v200 "$RUN/e5" "nomeia versao posterior do framework (2.0.0)"
# (f4) o item próprio «no release is assigned» trocado: a frase histórica (que cita a [1.4.2]) não basta
E git -C "$RUN/e5" checkout -q -- CHANGELOG.md
E python3 - "$RUN/e5/CHANGELOG.md" <<'PY'
import sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
old = "  - **The rest stays open, and no release is assigned to their cure.**\n"
assert t.count(old) == 1
open(p, "w", encoding="utf-8").write(t.replace(old, "  - The rest stays open; the cure ships later.\n", 1))
PY
red f4-so-frase-historica "$RUN/e5" "num item proprio"
drop "$RUN/e5"
# (h) um commit fora do pacote trazido por `merge -s ours` (a árvore fora do pacote não muda)
prep "$RUN/e5" "$MAT"
E git -C "$RUN/e5" checkout -q -b lado "$MAT"
printf 'ensaio\n' >"$RUN/e5/docs/relmeta143-probe.txt"
E git -C "$RUN/e5" add -- docs/relmeta143-probe.txt
commit_in "$RUN/e5" "docs: ENSAIO lado fora do pacote"
E git -C "$RUN/e5" checkout -q --detach "$MAT"
E git -C "$RUN/e5" -c user.name=R -c user.email=r@example.invalid merge -q -s ours --no-edit lado
patch_on "$RUN/e5"
red h-merge-s-ours "$RUN/e5" "tocam fora do pacote"
drop "$RUN/e5"
# (i) um commit vazio depois da derivação
prep "$RUN/e5" "$MAT"
E git -C "$RUN/e5" -c user.name=R -c user.email=r@example.invalid commit -q --allow-empty -m "docs(PLAN-194): ENSAIO commit vazio"
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
commit_in "$RUN/e5" "plan(PLAN-194): ENSAIO Derivator-SHA256 alterado"
patch_on "$RUN/e5"
HG=$(hard_in "$RUN/e5" "$LOGS/e5-g-derivator-hard.log")
check "E5: Derivator-SHA256 alterado no sentinel: hard-relmeta.sh rc≠0 no passo 0 (log: e5-g-derivator-hard.log)" \
  eval '[ "$HG" != "0" ] && grep -qF "Derivator-SHA256" "$LOGS/e5-g-derivator-hard.log"'
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
    "# rail-record — ENSAIO (rehearse-relmeta143.sh): registro SINTETICO, nunca o do rail real\n\n"
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

# ------------------------------------------------ E6: SIGN --dry-run com a chave descartável no allowlist
if [ "$SEM_SIGN" = "1" ]; then
  printf 'E6: pulado (--sem-sign)\n' | tee -a "$TALLY"
else
  # a chave entra no allowlist por um commit TEST ONLY ANTES de uma re-derivação: o Derived-From
  # passa a ser esse commit e o patch não muda (o escopo é o mesmo)
  DF=$(G cat-file blob "HEAD:$SENT_REL" | sed -n 's/^Derived-From: //p')
  E git clone -q --no-hardlinks "$WORK" "$RUN/anc-t"
  T() { E git -C "$RUN/anc-t" "$@"; }
  T config user.name Rehearsal
  T config user.email rehearsal@example.invalid
  T checkout -q -B main "$DF"
  for fpr in "$KEY_FPR" $O_FPR; do
    printf '# ENSAIO: chave descartável (rehearse-relmeta143), TEST ONLY\n%s\n' "$fpr" >>"$RUN/anc-t/$SIGNERS"
    if [ -f "$RUN/anc-t/$REGISTRY" ]; then
      printf '\n  - key_id: "%s"\n    key_type: "hot"\n    created_at: "2026-10-15T00:00:00Z"\n    expires_at: "2030-01-01T00:00:00Z"\n    revoked_at: null\n    notes: "ENSAIO: chave descartável (rehearse-relmeta143), TEST ONLY"\n' "$fpr" >>"$RUN/anc-t/$REGISTRY"
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

# ------------------------------------------------ E8: o roteiro do Owner, de ponta a ponta
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
  OLOG="$LOGS/e8-owner.log"
  : >"$OLOG"
  alimenta() {  # digita SIM quando a tela pede; mantém o pipe aberto até o roteiro terminar
    local i=0 sent=0
    while [ "$i" -lt 14400 ]; do
      if [ "$sent" = "0" ] && grep -qF "Digite SIM e Enter para assinar." "$OLOG" 2>/dev/null; then
        sleep 3; printf 'SIM\n'; sent=1
      fi
      if grep -qE "^RM-PUBLICADO |^PARE|^ENCERRADO" "$OLOG" 2>/dev/null; then sleep 2; return 0; fi
      sleep 0.5; i=$((i + 1))
    done
  }
  t0=$(date +%s)
  alimenta | env -i "${ROT[@]}" HOME="$OH" PATH="$OH/fakebin:$OPATH" \
    script -q /dev/null bash "$O/owner-sign-rm.sh" "$RUN/valores-ensaio.txt" "$VSHA" >"$OLOG" 2>&1 && ORC=0 || ORC=$?
  t1=$(date +%s)
  PUB=$(tr -d '\r' <"$OLOG" | sed -n 's/^RM-PUBLICADO \([0-9a-f]\{40\}\) .*/\1/p')
  SOBRAS="$SOBRAS $(tr -d '\r' <"$OLOG" | sed -n 's/^registros desta execução: //p' | head -n 1)"
  SOBRAS="$SOBRAS $(tr -d '\r' <"$OLOG" | sed -n 's/^SIGN-FATO: logs em //p' | head -n 1)"
  check "E8: owner-sign-rm.sh de ponta a ponta: rc=0 e RM-PUBLICADO em $((t1 - t0)) s (log: e8-owner.log)" \
    eval '[ "$ORC" = "0" ] && [ -n "$PUB" ]'
  check "E8: o remoto está no commit publicado, cujo pai único é o Anchor do E6" \
    eval '[ "$(E git -C "$REMOTE_T" rev-parse refs/heads/main)" = "$PUB" ] && [ "$(E git -C "$REMOTE_T" rev-list --parents -n 1 "$PUB")" = "$PUB $ANCHOR_T" ]'
  check "E8: o commit publicado difere do Anchor só nos 3 alvos, no sentinel e na .asc" \
    eval '[ "$(E git -C "$REMOTE_T" diff-tree -r --no-commit-id --name-only "$ANCHOR_T" "$PUB" | sort | tr "\n" " ")" = "$(printf "%s\n" "$T_MAN" "$T_REL" "$T_TST" "$SENT_REL" "$SENT_REL.asc" | sort | tr "\n" " ")" ]'
  for marca in AMBIENTE-OK PREPARO-OK CADEIA-OK ANCORA-OK PRE-SIGN-OK SIGN-RC=0 LAND-OK "PUSH-LIBERADO $PUB" PUSH-OK PUBLICADO-OK; do
    check "E8: o roteiro imprimiu «${marca}»" eval 'tr -d "\r" <"$OLOG" | grep -qxF "$marca"'
  done
fi

printf '\n==================== PLACAR: %s PASS / %s FAIL ====================\n' "$PASS" "$FAIL"
printf 'logs: %s\n' "$LOGS"
FIM=1
[ "$FAIL" = "0" ]
