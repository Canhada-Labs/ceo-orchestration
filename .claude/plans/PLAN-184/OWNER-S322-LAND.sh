#!/usr/bin/env bash
# OWNER-S322-LAND.sh — land do pacote A0 (PLAN-184) + W2 (PLAN-174).
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao;
# adaptado do OWNER-S321-LAND.sh (provado na S321), incluindo o gate
# `touched - scope = vazio` (G4), que nenhum gerador conhece ainda.
#
# Roda a partir da RAIZ do repo. Nenhum passo e destrutivo antes de TODOS os
# gates passarem. `--dry-run` inspeciona sem aplicar.
#
# Uso:
#   bash .claude/plans/PLAN-184/OWNER-S322-LAND.sh --dry-run
#   bash .claude/plans/PLAN-184/OWNER-S322-LAND.sh
set -euo pipefail

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# A raiz resolve por git, nunca por `../..` (licao S313).
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SENTINEL=".claude/plans/PLAN-184/wave-a0-approved.md"
PATCH=".claude/plans/PLAN-184/s322-ceremony/S322-CEREMONY.patch"

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# ---------------------------------------------------------------------------
step "G0 — insumos presentes e nenhuma colisao suja"
# ---------------------------------------------------------------------------
[[ -f "$SENTINEL" ]] || die "sentinel ausente: $SENTINEL"
[[ -f "$PATCH" ]]    || die "patch ausente: $PATCH"
[[ -f "$SENTINEL.asc" ]] || die "assinatura ausente: $SENTINEL.asc — rode o SIGN primeiro"
ok "sentinel, patch e .asc presentes"

# A garantia que este gate PRECISA dar nao e "arvore limpa" — e que nenhum
# arquivo QUE O PATCH TOCA esteja modificado, senao `git apply` aterrissaria
# sobre conteudo diferente do assinado. Exigir porcelain VAZIO seria deadlock:
# o proprio ato de assinar suja a arvore (preenche campos + cria o .asc), e
# commitar para limpar mudaria o HEAD, invalidando o Anchor-SHA (licao S321).
DIRTY_FILE="$(mktemp)"; PATCHED_FILE="$(mktemp)"
trap 'rm -f "$DIRTY_FILE" "$PATCHED_FILE"' EXIT
git status --porcelain | sed 's/^...//' | sort -u > "$DIRTY_FILE"
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$PATCHED_FILE"
COLLIDE="$(comm -12 "$DIRTY_FILE" "$PATCHED_FILE")"
if [[ -n "$COLLIDE" ]]; then
  die "arquivo(s) do patch estao MODIFICADOS na arvore:
$(printf '  %s\n' $COLLIDE)
  O patch aterrissaria sobre conteudo diferente do assinado."
fi

# Nao basta "nao colide com o patch": um path GUARDADO sujo e FORA do Scope
# assinado misturaria edicao canonica nao-assinada no mesmo land (achado P1 do
# pair-rail na S321, que se MATERIALIZOU no land real). Tolerancia = allowlist
# fechada dos artefatos da propria cerimonia; qualquer outro guardado ABORTA.
CEREMONY_OK=( "$SENTINEL" "$SENTINEL.asc" "$PATCH" )
GUARDED_DIRTY=""; OTHER_DIRTY=""
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  skip=0
  for allowed in "${CEREMONY_OK[@]}"; do
    [[ "$f" == "$allowed" ]] && skip=1 && break
  done
  [[ "$skip" == "1" ]] && continue
  case "$f" in
    .claude/hooks/*|.claude/adr/ADR-*.md|SPEC/*|.github/workflows/*|.claude/settings.json|.claude/agents/*.md|.claude/policies/*|.claude/dispatcher/*|PROTOCOL.md|scripts/install.sh|scripts/upgrade.sh|scripts/_framework_manifest_set.sh|templates/settings/*.json)
      GUARDED_DIRTY+="  $f"$'\n' ;;
    *)
      OTHER_DIRTY+="  $f"$'\n' ;;
  esac
done < "$DIRTY_FILE"
if [[ -n "$GUARDED_DIRTY" ]]; then
  die "path(s) CANONICOS sujos fora do Scope assinado:
$GUARDED_DIRTY  Commite-os SEPARADAMENTE antes, ou inclua-os no Scope e re-assine."
fi
if [[ -n "$OTHER_DIRTY" ]]; then
  printf '  \033[33mNOTA\033[0m mudancas nao-guardadas fora do patch (toleradas):\n'
  printf '%s' "$OTHER_DIRTY"
fi
ok "nenhum arquivo do patch sujo; nenhum canonico sujo fora do Scope"

# ---------------------------------------------------------------------------
step "G1 — assinatura GPG do sentinel + rail de signer"
# ---------------------------------------------------------------------------
gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /' \
  || die "assinatura GPG NAO verifica"
ok "assinatura verificada"

SIGNERS=".claude/sentinel-signers.txt"
if [[ -f "$SIGNERS" ]]; then
  # Sem `|| true` cru: o R2 do ceremony-lint o classifica como BLOCKING, e ele
  # esconderia uma falha do gpg dentro da substituicao. A saida e capturada em
  # duas etapas, com o fallback EXPLICITO por variavel — e `grep`/`head` sob
  # pipefail podem matar o produtor com SIGPIPE(141), por isso o texto e
  # capturado ANTES de ser filtrado.
  _gpg_out=""
  _gpg_out="$(gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1)" || _gpg_out=""
  FPR="$(printf '%s\n' "$_gpg_out" | grep -oE '[A-F0-9]{40}' | head -1)" || FPR=""
  [[ -n "$FPR" ]] || die "nao consegui extrair o fingerprint da assinatura"
  grep -qi "$FPR" "$SIGNERS" || die "fingerprint $FPR NAO consta em $SIGNERS"
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
  real     : $ACTUAL"
ok "patch casa o sha256 assinado ($ACTUAL)"

# ---------------------------------------------------------------------------
step "G3 — Anchor-SHA == HEAD"
# ---------------------------------------------------------------------------
ANCHOR="$(grep -m1 '^Anchor-SHA:' "$SENTINEL" | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
HEAD_SHA="$(git rev-parse HEAD)"
[[ -n "$ANCHOR" ]] || die "sentinel sem Anchor-SHA"
[[ "$ANCHOR" != "ANCHOR-PLACEHOLDER" ]] || die "Anchor-SHA ainda e o PLACEHOLDER — rode o SIGN"
[[ "$ANCHOR" == "$HEAD_SHA" ]] || die "Anchor-SHA nao bate com HEAD
  ancora: $ANCHOR
  HEAD  : $HEAD_SHA
  Commits entraram depois da assinatura. Re-gere o Anchor e RE-ASSINE."
ok "ancora casa HEAD ($HEAD_SHA)"

# ---------------------------------------------------------------------------
step "G4 — touched MENOS scope = vazio"
# ---------------------------------------------------------------------------
# O parser casa por PREFIXO ASCII e tolera acento no resto da linha
# (licao S318: script ASCII-safe vs prosa acentuada abortou um G3 com o
# campo CORRETO).
SCOPE_FILE="$(mktemp)"; TOUCHED_FILE="$(mktemp)"
trap 'rm -f "$DIRTY_FILE" "$PATCHED_FILE" "$SCOPE_FILE" "$TOUCHED_FILE"' EXIT

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
step "V — verificacao pos-land (cada uma fail-closed com || die)"
# ---------------------------------------------------------------------------
python3 - <<'PY' || die "V1: o validate.yml perdeu o backstop ou a matriz"
import sys, yaml
d = yaml.safe_load(open(".github/workflows/validate.yml"))
on = d[[k for k in d if k in ("on", True)][0]]
assert "schedule" in on, "V1a: `schedule:` AUSENTE — o corte da matriz ficaria sem backstop"
assert on["schedule"], "V1b: schedule vazio"
m = d["jobs"]["hook-tests-python-matrix"]["strategy"]["matrix"]["python-version"]
assert "fromJSON" in str(m), "V1c: matriz nao e a expressao condicional"
assert "3.9" in str(m) and "3.12" in str(m), "V1d: fronteiras ausentes da expressao"
assert len(d["jobs"]) == 7, "V1e: contagem de jobs mudou (%d)" % len(d["jobs"])
print("  V1 validate.yml: schedule presente, matriz condicional, 7 jobs")
PY
ok "V1 validate.yml coerente"

python3 - <<'PY' || die "V2: ceremony-lint.yml invalido"
import yaml
d = yaml.safe_load(open(".github/workflows/ceremony-lint.yml"))
jobs = list(d.get("jobs", {}).keys())
assert jobs, "V2a: nenhum job"
print("  V2 ceremony-lint.yml: jobs =", jobs)
PY
ok "V2 ceremony-lint.yml valido"

bash -n .claude/scripts/local/install-ceremony-precommit.sh \
  || die "V3: install-ceremony-precommit.sh nao passa bash -n"
[[ -x .claude/scripts/local/install-ceremony-precommit.sh ]] \
  || die "V3b: o installer perdeu o bit executavel (o `cp` perde; o patch carrega o modo)"
ok "V3 installer: bash -n OK e executavel"

if command -v actionlint >/dev/null 2>&1; then
  actionlint .github/workflows/validate.yml .github/workflows/ceremony-lint.yml \
    || die "V4: actionlint VERMELHO nos workflows"
  ok "V4 actionlint verde nos dois workflows"
else
  printf '  \033[33mWARN\033[0m actionlint ausente localmente — o CI e o gate real\n'
fi

python3 .claude/scripts/validate_governance_fast.py >/dev/null \
  || die "V5: validate_governance_fast FALHOU"
ok "V5 governanca verde"

CEO_OVERHEAD_ACK=1 python3 .claude/scripts/check-ceremony-script.py >/dev/null \
  || die "V6: ceremony-lint reprovou os proprios scripts de cerimonia"
ok "V6 ceremony-lint verde (inclui estes scripts)"

printf '\n\033[32mLAND OK.\033[0m Revise `git diff` e commite.\n'
printf 'Sugestao: "feat(PLAN-184 A0 + PLAN-174 W2): matriz de Python no push com backstop nightly + wire do ceremony-lint"\n'
printf '\nATENCAO — o primeiro fire do cron precisa de inspecao a mao: se a matriz\n'
printf 'vier VAZIA no schedule, o job passa VACUAMENTE. Confirme 4 entradas.\n'
