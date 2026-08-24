#!/usr/bin/env bash
# OWNER-S326-LAND.sh — land do pacote de cerimônia wave-cli (PLAN-182).
# CEREMONY-LINT: handwritten-exception: script de cerimonia autorado a mao
# (espelha o OWNER-S321-LAND.sh, gate a gate, incluindo o G4 `touched - scope`
# que so existe automatizado nessa familia de scripts).
#
# Roda a partir da RAIZ do repositório. Nenhum passo é destrutivo antes de
# todos os gates passarem; `--dry-run` para inspecionar sem aplicar.
#
# Uso:
#   bash .claude/plans/PLAN-182/OWNER-S326-LAND.sh --dry-run
#   bash .claude/plans/PLAN-182/OWNER-S326-LAND.sh
set -euo pipefail

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# A raiz resolve por git, nunca por `../..` (lição S313).
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SENTINEL=".claude/plans/PLAN-182/wave-cli-approved.md"
PATCH=".claude/plans/PLAN-182/cli-ceremony/S326-CLI-CEREMONY.patch"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# ---------------------------------------------------------------------------
step "G0 — insumos presentes"
# ---------------------------------------------------------------------------
[[ -f "$SENTINEL" ]] || die "sentinel ausente: $SENTINEL"
[[ -f "$PATCH" ]]    || die "patch ausente: $PATCH"
[[ -f "$SENTINEL.asc" ]] || die "assinatura ausente: $SENTINEL.asc
  O Owner assina com:  bash .claude/plans/PLAN-182/OWNER-S326-SIGN.sh"
ok "sentinel, patch e .asc presentes"

# Os materiais da cerimonia tem de estar RASTREADOS (commitados) antes do
# land (pair-rail r8 P2): o commit do land stageia so o patch + sentinel +
# .asc, entao SIGN/LAND/patch/registros untracked deixariam o commit
# referenciando evidencia ausente do repositorio. Fail-closed aqui.
MATERIALS=(
  ".claude/plans/PLAN-182/OWNER-S326-SIGN.sh"
  ".claude/plans/PLAN-182/OWNER-S326-LAND.sh"
  ".claude/plans/PLAN-182/cli-ceremony/PROPOSED-PATCH.md"
  "$PATCH"
  "$SENTINEL"
)
for m in "${MATERIALS[@]}"; do
  git ls-files --error-unmatch -- "$m" >/dev/null 2>&1 \
    || die "material de cerimonia NAO commitado: $m — commite os materiais antes de assinar/landar"
done
for r in .claude/plans/PLAN-182/cli-ceremony/rail-*.md; do
  git ls-files --error-unmatch -- "$r" >/dev/null 2>&1 \
    || die "registro de rail NAO commitado: $r"
done
ok "materiais e registros de rail rastreados no repositorio"

# Nenhum arquivo QUE O PATCH TOCA pode estar modificado (senao `git apply`
# aterrissa sobre conteudo diferente do assinado). A arvore NAO precisa estar
# limpa: o proprio ato de assinar preenche o sentinel e cria o `.asc`.
DIRTY_FILE="$(mktemp)"; PATCHED_FILE="$(mktemp)"
trap 'rm -f "$DIRTY_FILE" "$PATCHED_FILE"' EXIT
# Porcelain parsed NUL-delimited (rail r4 P1 dos materiais): o corte de 3
# caracteres deixava `old -> new` inteiro num rename, e o oraculo classificava
# pelo path VELHO — um rename PARA dentro de .claude/hooks/ passava como
# tolerado. Aqui: renames/copias ABORTAM (o operador resolve antes do land),
# e um path com newline ABORTA — gate de seguranca falha fechado em entrada
# que nao sabe parsear.
: > "$DIRTY_FILE"
while IFS= read -r -d '' entry; do
  xy="${entry:0:2}"
  entry_path="${entry:3}"
  case "$xy" in
    *R*|*C*)
      # -z: a origem do rename vem no PROXIMO registro; consumi-lo para
      # nao ser lido como um path solto.
      IFS= read -r -d '' _renamed_from || true
      die "rename/copia na arvore suja ($xy: $_renamed_from -> $entry_path) — resolva (commit ou reverta) antes do land" ;;
  esac
  [[ "$entry_path" == *$'\n'* ]] && die "path com newline na arvore suja — recusado"
  printf '%s\n' "$entry_path" >> "$DIRTY_FILE"
done < <(git status --porcelain=v1 -z)
sort -u -o "$DIRTY_FILE" "$DIRTY_FILE"
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$PATCHED_FILE"
COLLIDE="$(comm -12 "$DIRTY_FILE" "$PATCHED_FILE")"
if [[ -n "$COLLIDE" ]]; then
  die "arquivo(s) do patch estao MODIFICADOS na arvore:
$(printf '  %s\n' $COLLIDE)
  O patch aterrissaria sobre conteudo diferente do assinado.
  Commite ou reverta esses arquivos antes do land."
fi
# Allowlist FECHADA: so os artefatos da propria cerimonia podem estar sujos
# entre os paths guardados (achado P1 do pair-rail S321, materializado no
# land real daquela sessao). A canonicidade de cada path sujo vem do ORACULO
# (`check_canonical_edit.py --is-canonical`, a mesma _CANONICAL_GUARDS que o
# hook aplica) — NAO de uma lista espelhada aqui. Revisao cross-model dos
# materiais (S326, P1): o espelho anterior omitia superficies guardadas
# (.github/CODEOWNERS, scripts/install-npm.sh, scripts/_hash_lib.sh,
# .claude/team.md, ...), que caiam em "toleradas" e deixavam o land misturar
# uma edicao canonica nao-assinada. Oraculo indisponivel => ABORTA.
CEREMONY_OK=(
  "$SENTINEL"
  "$SENTINEL.asc"
  "$PATCH"
)
ORACLE=".claude/hooks/check_canonical_edit.py"
[[ -f "$ORACLE" ]] || die "oraculo de canonicidade ausente: $ORACLE"
GUARDED_DIRTY=""
OTHER_DIRTY=""
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  skip=0
  for allowed in "${CEREMONY_OK[@]}"; do
    [[ "$f" == "$allowed" ]] && skip=1 && break
  done
  [[ "$skip" == "1" ]] && continue
  verdict="$(python3 "$ORACLE" --is-canonical "$f" 2>/dev/null | awk -F'\t' 'NR==1{print $2}')"
  case "$verdict" in
    1) GUARDED_DIRTY+="  $f"$'\n' ;;
    0) OTHER_DIRTY+="  $f"$'\n' ;;
    *) die "oraculo de canonicidade nao respondeu 0|1 para: $f (saida: '$verdict')" ;;
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
ok "nenhum arquivo do patch sujo; nenhum path canonico sujo fora do Scope"

# ---------------------------------------------------------------------------
step "G1 — assinatura GPG do sentinel"
# ---------------------------------------------------------------------------
gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /' \
  || die "assinatura GPG NAO verifica"
ok "assinatura verificada"

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
step "G4 — touched MENOS scope = vazio"
# ---------------------------------------------------------------------------
SCOPE_FILE="$(mktemp)"; TOUCHED_FILE="$(mktemp)"
trap 'rm -f "$SCOPE_FILE" "$TOUCHED_FILE" "$DIRTY_FILE" "$PATCHED_FILE"' EXIT

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
step "V — verificação pós-land (cada passo fail-closed)"
# ---------------------------------------------------------------------------
V_LOG="$(mktemp)"
python3 -m pytest \
  .claude/hooks/tests/test_runtime_paths.py \
  .claude/hooks/tests/test_collect_only_audit_isolation.py \
  .claude/hooks/tests/test_live_audit_isolation.py \
  .claude/scripts/tests/test_templates_use_single_resolver.py \
  -q -p no:cacheprovider > "$V_LOG" 2>&1 \
  || die "V1: suites-alvo VERMELHAS — ver $V_LOG
  ATENCAO: os 3 testes do Axis 3 ficam vermelhos num land PARCIAL — isso e o guard, nao regressao."
ok "V1 suites-alvo: $(tail -1 "$V_LOG")"

shasum -a 256 -c "$MANIFEST" >/dev/null 2>&1 \
  || die "V2: manifesto ADR-192 NAO casa — algum gate-script diverge do assinado"
ok "V2 manifesto ADR-192 casa"

python3 .claude/scripts/derive-audit-family.py --assert-migrated >/dev/null \
  || die "V3a: --assert-migrated ficou VERMELHO"
CEO_AUDIT_FAMILY_M4_REQUIRED=1 \
  python3 .claude/scripts/derive-audit-family.py --assert-no-local-slug >/dev/null \
  || die "V3b: classe M4 reaberta"
ok "V3 --assert-migrated 0 e M4 0 sob enforcement"

python3 .claude/scripts/check-test-audit-isolation.py >/dev/null \
  || die "V4a: check-test-audit-isolation VERMELHO"
python3 .claude/scripts/check-test-env-hygiene.py >/dev/null \
  || die "V4b: check-test-env-hygiene VERMELHO"
python3 .claude/scripts/validate_governance_fast.py >/dev/null \
  || die "V4c: validate_governance_fast FALHOU"
ok "V4 gates estaticos verdes"

python3 scripts/build-plugin.py >/dev/null 2>&1 \
  || die "V5: build-plugin.py falhou"
cmp -s .claude/hooks/_lib/runtime_paths.py dist/ceo-plugin/hooks/_lib/runtime_paths.py \
  || die "V5: espelho dist/ do resolvedor NAO e byte-identico a fonte"
ok "V5 espelho dist/ regenerado e identico"

# Live-fire: a bateria pre-commit que gravava 124 elos por run agora grava 0.
LIVE_LOG="$(python3 .claude/hooks/_lib/runtime_paths.py --state-dir)/audit-log.jsonl"
BEFORE="$( [[ -f "$LIVE_LOG" ]] && wc -l < "$LIVE_LOG" || echo 0 )"
bash .claude/scripts/local/verify-counts.sh --quiet >/dev/null 2>&1 \
  || die "V6: verify-counts.sh reprovou apos o land"
sleep 2
AFTER="$( [[ -f "$LIVE_LOG" ]] && wc -l < "$LIVE_LOG" || echo 0 )"
DELTA=$(( AFTER - BEFORE ))
[[ "$DELTA" -eq 0 ]] || die "V6: verify-counts.sh gravou $DELTA linha(s) na cadeia VIVA (esperado 0; antes da S326 eram 124)"
ok "V6 live-fire: verify-counts.sh completo, delta 0 na cadeia viva"

# ---------------------------------------------------------------------------
step "S — staging explicito (pair-rail r5 P1)"
# ---------------------------------------------------------------------------
# `git add -u` sozinho NUNCA inclui a assinatura: o `.asc` nasce UNTRACKED no
# SIGN, e um commit canonico sem ele sobe sem a evidencia que a governanca
# exige (AGENTS.md §sentinel). O land faz o staging COMPLETO e nomeado —
# paths explicitos, nunca diretorio (ceremony-lint R4) — e o Owner so commita.
# Stage EXATAMENTE os paths que o patch assinado toca + os artefatos do
# sentinel — nunca `git add -u` (pair-rail r6 P1: um path rastreado sujo fora
# do patch, tolerado no G0, entraria no commit sem revisao nem assinatura).
EXPECTED_FILE="$(mktemp)"; STAGED_FILE="$(mktemp)"
trap 'rm -f "$SCOPE_FILE" "$TOUCHED_FILE" "$DIRTY_FILE" "$PATCHED_FILE" "$EXPECTED_FILE" "$STAGED_FILE"' EXIT
{ cat "$TOUCHED_FILE"; printf '%s\n' "$SENTINEL" "$SENTINEL.asc"; } | sort -u > "$EXPECTED_FILE"
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  git add -- "$f"
done < "$EXPECTED_FILE"
git diff --cached --name-only | sort -u > "$STAGED_FILE"
git diff --cached --name-only | sed 's/^/    staged: /'
if ! cmp -s "$EXPECTED_FILE" "$STAGED_FILE"; then
  die "conjunto staged != patch + sentinel:
  so no esperado: $(comm -23 "$EXPECTED_FILE" "$STAGED_FILE" | tr '\n' ' ')
  so no staged  : $(comm -13 "$EXPECTED_FILE" "$STAGED_FILE" | tr '\n' ' ')
  (um path do patch identico ao HEAD nao aparece no staged — isso tambem e erro: o patch nao deveria toca-lo)"
fi
grep -qx "$SENTINEL.asc" "$STAGED_FILE" || die "a assinatura $SENTINEL.asc NAO ficou staged"
ok "$(wc -l < "$STAGED_FILE" | tr -d ' ') path(s) staged == patch + sentinel + .asc"

printf '\n\033[32mLAND OK.\033[0m Revise `git diff --cached` e commite (o staging ja esta feito).\n'
printf 'Sugestao de mensagem:\n'
printf '  feat(PLAN-182 wave-cli): CLI do resolvedor unico (OQ-6) + Axis 3 do isolamento de testes (S326)\n'
printf '  Pair-Rail-Reviewed: APPROVE\n'
