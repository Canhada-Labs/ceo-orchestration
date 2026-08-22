#!/usr/bin/env bash
# OWNER-S321-LAND.sh — land do pacote de cerimônia W1-followup (PLAN-182).
#
# Roda a partir da RAIZ do repositório. Nenhum passo é destrutivo antes de
# todos os gates passarem; `--dry-run` para inspecionar sem aplicar.
#
# O QUE ESTE SCRIPT ADICIONA em relação ao OWNER-S319-LAND.sh: o gate
# `touched − scope = ∅`. A auditoria da S321 mediu que esse gate — invocado
# DUAS VEZES pelo material de cerimônia anterior como se fosse garantia —
# **não existia automatizado em lugar nenhum**: o G1 do S319 verifica outra
# coisa (que todo alvo do MANIFEST existe na árvore) e nunca lê o bloco
# `Scope:` do sentinel. Aqui ele é o G4, e é fail-closed.
#
# Uso:
#   bash .claude/plans/PLAN-182/OWNER-S321-LAND.sh --dry-run
#   bash .claude/plans/PLAN-182/OWNER-S321-LAND.sh
set -euo pipefail

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# A raiz resolve por git, nunca por `../..` — a lição S313 (um `../..` gradeou
# o STAGED em vez do repo).
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SENTINEL=".claude/plans/PLAN-182/wave-w1-followup-approved.md"
PATCH=".claude/plans/PLAN-182/w1-followup-ceremony/S321-CEREMONY.patch"

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# ---------------------------------------------------------------------------
step "G0 — insumos presentes"
# ---------------------------------------------------------------------------
[[ -f "$SENTINEL" ]] || die "sentinel ausente: $SENTINEL"
[[ -f "$PATCH" ]]    || die "patch ausente: $PATCH"
[[ -f "$SENTINEL.asc" ]] || die "assinatura ausente: $SENTINEL.asc
  O Owner assina com:
    export GPG_TTY=\$(tty); gpgconf --kill gpg-agent
    gpg --armor --detach-sign --yes $SENTINEL"
ok "sentinel, patch e .asc presentes"

# Working tree limpo: um land por cima de mudanças não-commitadas mistura
# o que foi assinado com o que não foi.
[[ -z "$(git status --porcelain)" ]] || die "working tree SUJO — commite ou stash antes do land:
$(git status --short)"
ok "working tree limpo"

# ---------------------------------------------------------------------------
step "G1 — assinatura GPG do sentinel"
# ---------------------------------------------------------------------------
gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /' \
  || die "assinatura GPG NAO verifica"
ok "assinatura verificada"

# Rail de signer: o fingerprint tem de constar da lista rastreada.
SIGNERS=".claude/sentinel-signers.txt"
if [[ -f "$SIGNERS" ]]; then
  FPR="$(gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 \
         | grep -oE '[A-F0-9]{40}' | head -1 || true)"
  [[ -n "$FPR" ]] || die "nao consegui extrair o fingerprint da assinatura"
  grep -qi "$FPR" "$SIGNERS" \
    || die "fingerprint $FPR NAO consta em $SIGNERS"
  ok "signer $FPR consta no rail rastreado"
else
  printf '  \033[33mWARN\033[0m %s ausente — rail de signer nao verificado\n' "$SIGNERS"
fi

# ---------------------------------------------------------------------------
step "G2 — binding do patch (Patch-sha256)"
# ---------------------------------------------------------------------------
DECLARED="$(grep -m1 '^Patch-sha256:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
[[ -n "$DECLARED" ]] || die "sentinel sem campo Patch-sha256"
ACTUAL="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
[[ "$DECLARED" == "$ACTUAL" ]] || die "patch NAO bate com o sentinel assinado
  declarado: $DECLARED
  real     : $ACTUAL
  O patch mudou depois da assinatura. Re-assine ou restaure o patch."
ok "patch casa o sha256 assinado ($ACTUAL)"

# ---------------------------------------------------------------------------
step "G3 — Anchor-SHA == HEAD"
# ---------------------------------------------------------------------------
ANCHOR="$(grep -m1 '^Anchor-SHA:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
HEAD_SHA="$(git rev-parse HEAD)"
[[ -n "$ANCHOR" ]] || die "sentinel sem Anchor-SHA"
[[ "$ANCHOR" == "$HEAD_SHA" ]] || die "Anchor-SHA nao bate com HEAD
  ancora: $ANCHOR
  HEAD  : $HEAD_SHA
  Commits entraram depois da assinatura. Re-gere o Anchor e RE-ASSINE."
ok "ancora casa HEAD ($HEAD_SHA)"

# ---------------------------------------------------------------------------
step "G4 — touched MENOS scope = vazio   (o gate que nao existia)"
# ---------------------------------------------------------------------------
# Scope: as linhas `  - <path>` entre os marcadores do bloco assinado.
# O parser casa por PREFIXO ASCII e tolera acento no resto da linha
# (lição S318: script ASCII-safe vs prosa acentuada abortou um G3 com o
# campo CORRETO).
SCOPE_FILE="$(mktemp)"; TOUCHED_FILE="$(mktemp)"
trap 'rm -f "$SCOPE_FILE" "$TOUCHED_FILE"' EXIT

awk '/BEGIN SIGNED SCOPE/{f=1;next} /END SIGNED SCOPE/{f=0} f' "$SENTINEL" \
  | sed -n 's/^[[:space:]]*-[[:space:]]*//p' | sed 's/[[:space:]]*$//' \
  | sort -u > "$SCOPE_FILE"
[[ -s "$SCOPE_FILE" ]] || die "bloco Scope vazio ou nao encontrado no sentinel"

git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$TOUCHED_FILE"
[[ -s "$TOUCHED_FILE" ]] || die "o patch nao toca arquivo nenhum"

EXTRA="$(comm -23 "$TOUCHED_FILE" "$SCOPE_FILE")"
if [[ -n "$EXTRA" ]]; then
  die "o patch toca path(s) FORA do Scope assinado:
$(printf '  %s\n' $EXTRA)
  Um Scope que nao cobre um path tocado invalida a autorizacao."
fi
ok "$(wc -l < "$TOUCHED_FILE" | tr -d ' ') path(s) tocado(s), todos dentro do Scope"

# Controle na direção oposta: um Scope inflado (path assinado que o patch NAO
# toca) é aviso, não abort — pode ser deliberado, mas o Owner precisa ver.
UNUSED="$(comm -13 "$TOUCHED_FILE" "$SCOPE_FILE")"
if [[ -n "$UNUSED" ]]; then
  printf '  \033[33mWARN\033[0m Scope autoriza path(s) que o patch nao toca:\n'
  printf '        %s\n' $UNUSED
fi

# ---------------------------------------------------------------------------
step "G5 — o patch aplica limpo"
# ---------------------------------------------------------------------------
git apply --check "$PATCH" || die "git apply --check FALHOU — a arvore divergiu do patch"
ok "aplica limpo"

if [[ "$DRY_RUN" == "1" ]]; then
  printf '\n\033[33mDRY-RUN\033[0m — todos os gates passaram; nada foi aplicado.\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "APLICANDO"
# ---------------------------------------------------------------------------
git apply "$PATCH"
ok "patch aplicado"

# ---------------------------------------------------------------------------
step "V — verificação pós-land"
# ---------------------------------------------------------------------------
# Cada verificação é fail-closed com `|| die`, nunca `|| echo advisory`
# (lição: gate em runbook é `|| die`).
python3 .claude/scripts/derive-audit-family.py --assert-migrated >/dev/null \
  || die "V1: --assert-migrated ficou VERMELHO"
ok "V1 --assert-migrated verde"

CEO_AUDIT_FAMILY_M4_REQUIRED=1 \
  python3 .claude/scripts/derive-audit-family.py --assert-no-local-slug >/dev/null \
  || die "V2: a classe M4 NAO fechou — algum modulo runtime ainda re-deriva o slug"
ok "V2 classe M4 FECHADA sob enforcement"

python3 -m pytest tests/unit/test_runtime_state_sandbox_confinement.py \
  -q -p no:cacheprovider > /tmp/s321-v3.txt 2>&1 \
  || die "V3: guard de confinamento VERMELHO — ver /tmp/s321-v3.txt
  ATENCAO: 3 passed e o esperado. Se voce aplicou so parte do pacote, o
  guard INVERTIDO fica vermelho — isso e o guard funcionando, nao regressao."
ok "V3 confinamento: $(tail -1 /tmp/s321-v3.txt)"

python3 .claude/scripts/validate_governance_fast.py >/dev/null \
  || die "V4: validate_governance_fast FALHOU"
ok "V4 governanca verde"

printf '\n\033[32mLAND OK.\033[0m Revise `git diff --cached` e commite com o hint da wave.\n'
printf 'Sugestao de mensagem: "feat(PLAN-182 W1-followup): cura estrutural do carrier + atribuicao + fecho da classe M4"\n'
