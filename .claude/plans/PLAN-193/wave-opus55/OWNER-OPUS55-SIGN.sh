#!/usr/bin/env bash
# OWNER-OPUS55-SIGN.sh — assina o sentinel da cerimonia wave-opus55 (PLAN-193, S357).
# CEREMONY-LINT: handwritten-exception: clone gate-a-gate do
# OWNER-S338-FABLE51-SIGN.sh (PLAN-169, que assinou o land REAL ab56e76).
# Muda o bloco de constantes e quatro pontos, todos declarados: (1) nao ha
# finalize separado — o P1-b RE-DERIVA o patch do HEAD num worktree
# descartavel (derivador versionado + diff com flags pinadas) e exige
# igualdade byte a byte com o WOPUS55.patch commitado; o mesmo calculo, em
# `--derive-patch`, e o que PRODUZ o patch; (2) o P0-e le as DUAS familias de
# registro de rail (rail-round-* sobre os bytes canonicos e
# rail-materials-round-* sobre os materiais): o ultimo de cada familia
# presente tem de ser APPROVE — ou o veredito de ANEXO com o anexo rastreado,
# SO na familia de materiais e SO na rodada final (4) da familia do patch
# (decisao do Owner OQ-10) — e nenhuma familia passa do teto de rodadas
# nem numera um registro alem da rodada final; (3) o P0-g recusa a mensagem de commit com
# trailer TO-FILL e o P1-c prova Scope == paths do patch ANTES de assinar —
# os dois abortariam o LAND depois da assinatura, e corrigir exigiria commit
# (que invalida o Anchor-SHA); (4) pela mesma razao o P1-d compara, antes do
# pinentry, os paths do patch e a contagem de ADRs com a base declarada
# (EXPECTED_PATCH_PATHS e EXPECTED_ADR_COUNT, o G4 e o V8a do LAND), e o
# P1-e roda a suite do V2 (EXPECTED_UNIT_TESTS) sobre HEAD + derivador quando
# o HEAD difere da base fora dos materiais desta cerimonia.
# O gerador `.claude/scripts/generate-ceremony.sh`
# NAO serve aqui: ele assume `architect/round-N/approved.md`, e esta
# cerimonia usa `PLAN-NNN/wave-*-approved.md` com land por PATCH.
# Preenche os campos e assina. NAO aplica nada — o land e o OWNER-OPUS55-LAND.sh.
#
# Fluxo completo, do zero ao push (3 comandos, nenhum editor):
#
#   bash .claude/plans/PLAN-193/wave-opus55/OWNER-OPUS55-SIGN.sh
#   bash .claude/plans/PLAN-193/wave-opus55/OWNER-OPUS55-LAND.sh --dry-run
#   bash .claude/plans/PLAN-193/wave-opus55/OWNER-OPUS55-LAND.sh
#
# O LAND faz o commit (com `-F`, sem editor) e o push. Voce nao digita `git`.
#
# Modo de manutencao (CEO, antes de commitar os materiais; nao assina nada):
#   bash .claude/plans/PLAN-193/wave-opus55/OWNER-OPUS55-SIGN.sh --derive-patch <arquivo-novo>
#
# ORDEM IMPORTA: o Anchor-SHA e o HEAD no momento da assinatura. Qualquer
# commit entre assinar e landar o invalida (G1 do land aborta). Este script
# e o ULTIMO passo antes do land — nao commite nada depois de roda-lo.
set -euo pipefail

# --- argumentos -----------------------------------------------------------
DERIVE_OUT=""
case "${1:-}" in
  "") : ;;
  --derive-patch)
    [ "$#" -eq 2 ] && [ -n "${2:-}" ] || {
      printf 'uso: bash %s --derive-patch <arquivo-novo>\n' "$0" >&2; exit 1; }
    DERIVE_OUT="$2" ;;
  *)
    printf '\n\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$1" >&2
    printf '  Formas validas:\n    bash %s\n    bash %s --derive-patch <arquivo-novo>\n' "$0" "$0" >&2
    exit 1 ;;
esac

# A raiz resolve por git a partir da LOCALIZACAO DO SCRIPT, nunca por `../..`
# nem pelo cwd (licao S313): o Owner pode chamar de qualquer diretorio.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
if [ -n "$DERIVE_OUT" ]; then
  case "$DERIVE_OUT" in /*) : ;; *) DERIVE_OUT="$PWD/$DERIVE_OUT" ;; esac
fi
cd "$ROOT"

# --- constantes da cerimonia (o UNICO bloco que muda entre waves) ----------
PLAN_ID="PLAN-193"
PLAN_DIR=".claude/plans/$PLAN_ID"
CEREMONY_DIR="$PLAN_DIR/wave-opus55"
SENTINEL="$PLAN_DIR/wave-opus55-approved.md"
PATCH="$CEREMONY_DIR/WOPUS55.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-OPUS55.txt"
SIGN_SCRIPT="$CEREMONY_DIR/OWNER-OPUS55-SIGN.sh"
LAND_SCRIPT="$CEREMONY_DIR/OWNER-OPUS55-LAND.sh"
HARNESS="$CEREMONY_DIR/test-ceremony-scripts-opus55.sh"
DESIGN="$CEREMONY_DIR/DESIGN-OPUS55-S357.md"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
APPLY="$CEREMONY_DIR/apply-opus55-edits.py"
APPLY_DATA_CORE="$CEREMONY_DIR/edits_core.py"
APPLY_DATA_PRICING="$CEREMONY_DIR/edits_pricing.py"
# O SIGN e o LAND passam SEMPRE esta flag: sem ela o derivador aplicaria so o
# nucleo se o modulo de preco sumisse.
APPLY_FLAG="--require-pricing"
# As duas familias de registro de rail, sem o sufixo `-<N>.md`.
RAIL_FAMILIES="rail-round rail-materials-round"
# A familia que TEM de existir (o V2 do PROTOCOL: uma rodada sobre o patch).
RAIL_REQUIRED_FAMILY="rail-round"
# Regra de parada PRE-REGISTRADA (PLAN-193, debate da W3, 2026-09-23): no
# maximo 3 rodadas por familia; um P1 achado SO em material vira ANEXO (na
# familia de materiais, com o arquivo de anexo rastreado e nao-vazio).
# Decisao do Owner OQ-10 (2026-09-24, verbatim «Corrigir + rodada 4 final c/
# anexo (Recomendado)»): UMA rodada 4, a ULTIMA — limpa => APPROVE; so P2 =>
# APPROVE-WITH-ANNEX com anexo rastreado e assinado; P0/P1 => REJECT e volta
# ao Owner. Por isso: no maximo RAIL_MAX_ROUNDS registros por familia,
# numerados ate RAIL_MAX_ROUNDS (um `rail-round-5.md` e recusado pelo NOME);
# na familia do patch, o veredito de anexo so vale na rodada FINAL
# (numero RAIL_MAX_ROUNDS) e so com `rail-round-<final>-annex.md` rastreado e
# nao-vazio; nas rodadas 1-3, so APPROVE; REJECT recusa sempre. (O teto de 2
# rodadas por CLASSE e a leitura P0/P1/P2 dos achados sao humanos — o
# registro de rail transcreve os rotulos do codex; este script nao sabe
# classificar.)
RAIL_MAX_ROUNDS=4
RAIL_ANNEX_VERDICT="APPROVE-WITH-ANNEX"
RAIL_ANNEX_FAMILY="rail-materials-round"
RAIL_ANNEX_FILE="$CEREMONY_DIR/rail-annex.md"
# A familia do patch e o anexo da sua rodada final (OQ-10). O anexo casa o
# glob da familia, mas nao e registro de rodada: o P0-e o le pelo NOME.
RAIL_FINAL_FAMILY="rail-round"
RAIL_FINAL_ANNEX_FILE="$CEREMONY_DIR/rail-round-$RAIL_MAX_ROUNDS-annex.md"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
THREAT_MODEL="docs/threat-model.md"
GEN_MODELS=".claude/scripts/generate-available-models.py"
ADR_DIR=".claude/adr"
APPROVED_BY_HANDLE="@Canhada-Labs"
# Prefixo dos diretorios temporarios desta wave.
TMP_TAG="opus55"
# `git diff` com config PINADA: o patch e re-derivado aqui e comparado byte a
# byte; um `diff.algorithm`, `diff.noprefix` ou `core.abbrev` do operador nao
# pode mudar a resposta. --full-index tira o comprimento do hash da equacao.
DIFF_PIN=(-c core.quotepath=true -c diff.noprefix=false -c diff.mnemonicPrefix=false
          -c diff.relative=false -c diff.algorithm=myers -c diff.indentHeuristic=true
          -c diff.suppressBlankEmpty=false -c diff.context=3 -c diff.interHunkContext=0
          -c diff.renames=false -c color.ui=false -c color.diff=false)
DIFF_ARGS=(diff --no-color --no-ext-diff --no-textconv --full-index --no-renames -O/dev/null)
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
warn(){ printf '  \033[33mWARN\033[0m %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# Leitor da base esperada — o MESMO do LAND: sem `source` (o arquivo nao
# executa nada), e fail-CLOSED quando a chave falta.
_expect() {
  _ev="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
  if [ -z "$_ev" ]; then
    die "chave '$1' AUSENTE em $BASELINE_ENV"
  fi
  printf '%s' "$_ev"
}

# --- worktree descartavel da re-derivacao (removido em QUALQUER saida) ------
DERIVE_WT=""
_cleanup() {
  if [ -n "$DERIVE_WT" ] && [ -d "$DERIVE_WT" ]; then
    git worktree remove --force "$DERIVE_WT" >/dev/null 2>&1 || true
    rm -rf "$( dirname "$DERIVE_WT" )" 2>/dev/null || true
    git worktree prune >/dev/null 2>&1 || true
  fi
}
trap _cleanup EXIT

# _derive_patch <saida> [keep] — HEAD + derivador versionado, num worktree
# descartavel; a saida e o `git diff` pinado sobre os paths que o PROPRIO
# derivador declara. Recusa se o derivador tocar qualquer outro path. Com
# `keep`, o worktree (HEAD + derivador = a arvore que o LAND mede) fica em
# $DERIVE_WT para o P1-e; o trap o remove em qualquer saida.
_derive_patch() {
  _dp_out="$1"
  _dp_keep="${2:-}"
  _dp_paths="$( python3 "$ROOT/$APPLY" --list-paths "$APPLY_FLAG" )" \
    || { printf '  derivador --list-paths falhou\n' >&2; return 1; }
  [ -n "$_dp_paths" ] || { printf '  derivador nao declarou path nenhum\n' >&2; return 1; }
  DERIVE_WT="$( mktemp -d "${TMPDIR:-/tmp}/${TMP_TAG}-derive.XXXXXX" )/wt"
  git worktree add --detach --quiet "$DERIVE_WT" HEAD \
    || { printf '  git worktree add falhou\n' >&2; return 1; }
  python3 "$ROOT/$APPLY" --root "$DERIVE_WT" "$APPLY_FLAG" >/dev/null \
    || { printf '  o derivador RECUSOU sobre HEAD (ancora ausente/ambigua ou HEAD ja patchado)\n' >&2; return 1; }
  _dp_extra="$( git -C "$DERIVE_WT" status --porcelain=v1 --untracked-files=all \
                | cut -c4- | LC_ALL=C sort -u \
                | LC_ALL=C comm -23 - <( printf '%s\n' "$_dp_paths" | LC_ALL=C sort -u ) )"
  [ -z "$_dp_extra" ] || { printf '  o derivador tocou fora dos paths declarados:\n%s\n' "$_dp_extra" >&2; return 1; }
  # shellcheck disable=SC2086  # lista controlada, um path por linha, sem espacos
  git -C "$DERIVE_WT" "${DIFF_PIN[@]}" "${DIFF_ARGS[@]}" HEAD -- $_dp_paths > "$_dp_out" \
    || { printf '  git diff falhou\n' >&2; return 1; }
  [ -s "$_dp_out" ] || { printf '  patch derivado vazio\n' >&2; return 1; }
  [ "$_dp_keep" = "keep" ] && return 0
  _drop_derive_wt
  return 0
}
_drop_derive_wt() {
  if [ -n "$DERIVE_WT" ]; then
    git worktree remove --force "$DERIVE_WT" >/dev/null 2>&1 || true
    rm -rf "$( dirname "$DERIVE_WT" )" 2>/dev/null || true
    DERIVE_WT=""
  fi
}

if [ -n "$DERIVE_OUT" ]; then
  step "--derive-patch — HEAD + derivador => patch (nada e assinado)"
  if [ -e "$DERIVE_OUT" ] || [ -L "$DERIVE_OUT" ]; then
    die "o destino ja existe: $DERIVE_OUT (escolha um arquivo NOVO; nada e sobrescrito)"
  fi
  _derive_patch "$DERIVE_OUT" || die "a derivacao falhou (acima)"
  ok "patch derivado: $DERIVE_OUT ($( wc -l < "$DERIVE_OUT" | tr -d ' ' ) linhas, sha256 $( shasum -a 256 "$DERIVE_OUT" | awk '{print $1}' ))"
  exit 0
fi

# --- interruptor de AUTO-TESTE (recusado fora do scratchpad) ---------------
# Existe so para `wave-opus55/test-ceremony-scripts-opus55.sh` exercitar os
# gates sem uma chave GPG. A comparacao e por REALPATH dos DOIS lados (/tmp e
# symlink no macOS: comparar formato de string mediria formato, nao caminho).
SELFTEST=0
if [ "${CEREMONY_SELFTEST_NO_GPG:-}" = "1" ]; then
  _sp_real="$( cd /private/tmp 2>/dev/null && pwd -P || printf '/private/tmp' )"
  case "$ROOT" in
    "$_sp_real"/claude-501/*/scratchpad/*) SELFTEST=1 ;;
    *) die "CEREMONY_SELFTEST_NO_GPG=1 RECUSADO: a arvore
  $ROOT
  nao esta sob o scratchpad de teste ($_sp_real/claude-501/*/scratchpad/).
  Este interruptor NAO existe para a arvore viva." ;;
  esac
  printf '\033[33m  MODO AUTO-TESTE\033[0m — GPG desligado; a arvore e um clone descartavel.\n'
fi

# ---------------------------------------------------------------------------
step "P0 — pre-condicoes"
# ---------------------------------------------------------------------------
[ -f "$SENTINEL" ] || die "sentinel ausente: $SENTINEL"
[ -f "$PATCH" ]    || die "patch ausente: $PATCH
  Gere-o com:  bash $ROOT/$SIGN_SCRIPT --derive-patch <arquivo-novo>
  (e mova-o para $PATCH; o sentinel e o PROPOSED-PATCH.md pinam o sha256)"
[ -f "$PROPOSED" ] || die "registro ausente: $PROPOSED"
[ -f "$ORACLE" ]   || die "oraculo de canonicidade ausente: $ORACLE"
[ -f "$BASELINE_ENV" ] || die "base esperada ausente: $BASELINE_ENV"

# ---------------------------------------------------------------------------
# P0-b — docs/threat-model.md: sujeira que NINGUEM editou.
# ---------------------------------------------------------------------------
# `.claude/scripts/check-threat-model-freshness.py` reescreve o arquivo como
# EFEITO COLATERAL de rodar: `flip_status_to_stale` aplica
# `re.sub(r"^(\*\*Status:\*\*)\s+accepted", r"\1 stale", count=1)` e sai 1.
# Como o P0 recusa arvore com modificacao RASTREADA, essa sujeira abortaria a
# cerimonia acusando um arquivo que ninguem tocou (medido na manha da S328).
#
# A cura e PONTUAL e provada por CONTEUDO: so este path, so quando ele e a
# UNICA modificacao rastreada, so quando esta NAO-staged, e so quando o diff e
# exatamente a troca de status na DIRECAO que o checker escreve. Aceitar
# `stale` -> `accepted` reverteria em silencio a edicao de quem RE-ACEITOU o
# modelo de ameacas de proposito. Qualquer outra coisa continua sendo motivo
# de parada.
_tm_is_only_status_flip() {
  _tm_ns="$( git diff --numstat -- "$THREAT_MODEL" \
             | awk '{ n++; a=$1; d=$2 } END { if (n==1) printf "%s/%s", a, d; else printf "many" }' )"
  [ "$_tm_ns" = "1/1" ] || return 1
  _tm_removed="$( git diff -U0 -- "$THREAT_MODEL" | sed -n 's/^-\([^-].*\)$/\1/p' )"
  _tm_added="$(   git diff -U0 -- "$THREAT_MODEL" | sed -n 's/^+\([^+].*\)$/\1/p' )"
  case "$_tm_removed" in '**Status:** accepted') : ;; *) return 1 ;; esac
  case "$_tm_added"   in '**Status:** stale')    : ;; *) return 1 ;; esac
  return 0
}

_tm_dirty_count="$( git status --porcelain=v1 | grep -c -v '^??' || true )"
_tm_xy="$( git status --porcelain=v1 -- "$THREAT_MODEL" | head -1 | cut -c1-2 )"
if [ "$_tm_dirty_count" = "1" ] && [ "$_tm_xy" = " M" ]; then
  if _tm_is_only_status_flip; then
    if git checkout -- "$THREAT_MODEL" 2>/dev/null; then
      warn "$THREAT_MODEL estava modificado e eu REVERTI."
      printf '        Ninguem editou esse arquivo: quem o reescreve e\n'
      printf '        `.claude/scripts/check-threat-model-freshness.py`, que troca\n'
      printf '        `**Status:** accepted` por `stale` como efeito colateral de rodar.\n'
      printf '        Confirmei que o diff era EXATAMENTE essa troca de uma linha, e\n'
      printf '        nada mais, antes de reverter.\n'
    else
      die "tentei reverter $THREAT_MODEL e o \`git checkout\` falhou — chame o CEO"
    fi
  else
    warn "$THREAT_MODEL esta modificado, mas o diff NAO e so a troca de status."
    printf '        NAO vou reverter: ha conteudo real ai que eu destruiria.\n'
    printf '        Veja o que mudou de fato:\n'
    printf '          cd %s && git diff -- %s\n' "$ROOT" "$THREAT_MODEL"
  fi
fi

# ---------------------------------------------------------------------------
# P0-c — arvore: nenhuma modificacao RASTREADA.
# ---------------------------------------------------------------------------
# O Anchor-SHA tem de descrever o que sera landado. Arquivos UNTRACKED sao
# tolerados SO se o oraculo de canonicidade responder 0 — o land stageia
# exatamente o patch + sentinel + .asc (passo S), entao um untracked
# nao-canonico nunca entra no commit; um untracked CANONICO (arquivo novo sob
# .claude/hooks/ etc.) aborta.
TRACKED_DIRTY=""; UNTRACKED_OK=""
while IFS= read -r -d '' entry; do
  xy="${entry:0:2}"; entry_path="${entry:3}"
  case "$xy" in
    "??")
      verdict="$(python3 "$ORACLE" --is-canonical "$entry_path" 2>/dev/null | awk -F'\t' 'NR==1{print $2}')"
      case "$verdict" in
        0) UNTRACKED_OK="$UNTRACKED_OK  $entry_path
" ;;
        1) die "arquivo UNTRACKED em path CANONICO: $entry_path — commite-o por cerimonia propria ou remova antes de assinar" ;;
        *) die "oraculo nao respondeu 0|1 para: $entry_path" ;;
      esac ;;
    *R*|*C*) IFS= read -r -d '' _from || true; TRACKED_DIRTY="$TRACKED_DIRTY  $xy $entry_path
" ;;
    *) TRACKED_DIRTY="$TRACKED_DIRTY  $xy $entry_path
" ;;
  esac
done < <(git status --porcelain=v1 -z)
[ -z "$TRACKED_DIRTY" ] || die "modificacoes RASTREADAS na arvore — commite ANTES de assinar:
$TRACKED_DIRTY  (assinar com a arvore suja produz um Anchor-SHA que nao descreve o que sera landado)"
if [ -n "$UNTRACKED_OK" ]; then
  printf '  \033[33mNOTA\033[0m untracked nao-canonicos tolerados (nao entram no land):\n%s' "$UNTRACKED_OK"
fi
ok "nenhuma modificacao rastreada; untracked (se houver) sao nao-canonicos"

# ---------------------------------------------------------------------------
# P0-d — materiais COMMITADOS (e o arquivo do plano, que a governanca exige).
# ---------------------------------------------------------------------------
# Pair-rail r9 P2 da S326: o LAND exige-os rastreados, e commita-los DEPOIS da
# assinatura muda o HEAD e invalida o Anchor-SHA (G1). Mesma lista do LAND.
MATERIALS=(
  "$SIGN_SCRIPT"
  "$LAND_SCRIPT"
  "$HARNESS"
  "$PROPOSED"
  "$COMMIT_MSG"
  "$BASELINE_ENV"
  "$APPLY"
  "$APPLY_DATA_CORE"
  "$APPLY_DATA_PRICING"
  "$DESIGN"
  "$PATCH"
  "$SENTINEL"
)
MISSING=""
for m in "${MATERIALS[@]}"; do
  if ! git ls-files --error-unmatch -- "$m" >/dev/null 2>&1; then
    MISSING="$MISSING  $m
"
  fi
done
[ -z "$MISSING" ] || die "material(is) de cerimonia NAO commitado(s):
$MISSING  Commite os materiais ANTES de assinar (commitar depois muda o HEAD e invalida a ancora)."
# Um diretorio PLAN-NNN/ sem o PLAN-NNN-*.md rastreado e um ERRO do
# validate-governance.sh (PLAN-SCHEMA §1 orphan subdir): o V9b do LAND
# reprovaria DEPOIS da assinatura. Medido na sombra da S357.
_plan_files="$( git ls-files -- "$PLAN_DIR-*.md" | wc -l | tr -d ' ' )"
[ "$_plan_files" = "1" ] || die "esperava exatamente 1 arquivo de plano rastreado ($PLAN_DIR-*.md), achei $_plan_files.
  Sem ele o validate-governance acusa '$PLAN_DIR/' como orphan subdir e o LAND reprova no V9b."
ok "${#MATERIALS[@]} materiais e o arquivo do $PLAN_ID rastreados"

# ---------------------------------------------------------------------------
# P0-e — registros de rail rastreados; o ULTIMO de cada familia e APPROVE.
# ---------------------------------------------------------------------------
# Duas familias: `rail-round-<N>.md` (rodadas sobre os bytes do patch) e
# `rail-materials-round-<N>.md` (rodadas sobre estes materiais). A primeira
# tem de existir; a segunda, SE existir, tambem tem de terminar em APPROVE —
# uma rodada de materiais com REJECT no fim e um achado aberto sobre o proprio
# instrumento da cerimonia. Contar rodadas nao e ler o veredito; o numero e
# comparado como INTEIRO (lexicograficamente `-10` vem antes de `-2`); o
# veredito e IGUALDADE EXATA com `APPROVE` (uma linha qualificada nunca casa —
# licao paga na wave-F). A excecao e o veredito de ANEXO, por familia: na de
# materiais com `rail-annex.md` (regra pre-registrada); na do patch SO na
# rodada final, com `rail-round-<final>-annex.md` (OQ-10).
RAIL_SUMMARY=""
for _fam in $RAIL_FAMILIES; do
  _count=0; _last=""; _last_n=-1
  for r in "$CEREMONY_DIR/$_fam"-*.md; do
    [ -f "$r" ] || continue
    # O anexo da rodada final casa o glob da familia do patch; ele nao e um
    # registro de rodada, e e lido abaixo pelo NOME.
    if [ "$r" = "$RAIL_FINAL_ANNEX_FILE" ]; then
      continue
    fi
    _b="$( basename "$r" )"
    _n="${_b#"$_fam"-}"; _n="${_n%.md}"
    # As familias nao se sobrepoem (`rail-round-*` nao casa
    # `rail-materials-round-*`): um sufixo nao-decimal e registro mal nomeado.
    case "$_n" in
      ''|*[!0-9]*) die "registro de rail com numero nao-decimal: $r
  O SIGN precisa saber QUAL e o ultimo; renomeie para $_fam-<N>.md." ;;
    esac
    # OQ-10: a rodada $RAIL_MAX_ROUNDS e a ULTIMA. Um registro numerado alem
    # dela e recusado pelo NOME, qualquer que seja o veredito dele.
    [ "$_n" -le "$RAIL_MAX_ROUNDS" ] || die "registro de rail ALEM da rodada final: $r
  A rodada $RAIL_MAX_ROUNDS e a ultima da familia $_fam (decisao do Owner
  OQ-10, verbatim «Corrigir + rodada 4 final c/ anexo (Recomendado)»). Nao
  ha rodada $_n: leve o estado ao Owner em vez de assinar."
    git ls-files --error-unmatch -- "$r" >/dev/null 2>&1 \
      || die "registro de rail NAO commitado: $r — commite ANTES de assinar"
    _count=$(( _count + 1 ))
    if [ "$_n" -gt "$_last_n" ]; then _last_n="$_n"; _last="$r"; fi
  done
  if [ "$_count" -eq 0 ]; then
    [ "$_fam" != "$RAIL_REQUIRED_FAMILY" ] \
      || die "nenhum registro de rail em $CEREMONY_DIR/$_fam-<N>.md — o V2 do PROTOCOL exige pelo menos uma rodada registrada"
    continue
  fi
  # Regra de parada: mais registros do que o teto e laco, nao revisao — a
  # decisao volta ao Owner, nunca a uma rodada a mais. (Com a numeracao
  # limitada acima, so dois registros com o mesmo numero chegam aqui.)
  [ "$_count" -le "$RAIL_MAX_ROUNDS" ] || die "regra de parada: $_count registro(s) na familia $_fam, teto $RAIL_MAX_ROUNDS.
  A regra foi registrada ANTES da primeira rodada ($PLAN_ID) e a rodada
  $RAIL_MAX_ROUNDS e a ultima (OQ-10): no maximo $RAIL_MAX_ROUNDS rodadas por
  familia. Uma rodada alem do teto e laco, nao revisao — leve o estado ao
  Owner em vez de assinar."
  _verdict="$( { grep -m1 '^Rail-Verdict:' "$_last" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]' )"
  [ -n "$_verdict" ] || die "o ultimo registro de rail ($_last) nao tem uma linha 'Rail-Verdict:'.
  Um registro sem veredito nao autoriza nada. Escreva-a e commite."
  if [ "$_verdict" = "$RAIL_ANNEX_VERDICT" ]; then
    if [ "$_fam" = "$RAIL_ANNEX_FAMILY" ]; then
      # Materiais (regra pre-registrada): um P1 SO em material vira anexo.
      _annex="$RAIL_ANNEX_FILE"
    elif [ "$_fam" = "$RAIL_FINAL_FAMILY" ]; then
      # Patch (OQ-10): SO a rodada final, e SO achados P2 (o registro os
      # transcreve com o rotulo do codex); nas rodadas 1-3, so APPROVE.
      [ "$_last_n" -eq "$RAIL_MAX_ROUNDS" ] || die "o ULTIMO registro de rail traz Rail-Verdict: $_verdict
  arquivo: $_last
  Na familia $_fam o veredito de anexo so vale na rodada final
  ($RAIL_MAX_ROUNDS; decisao do Owner OQ-10). A rodada $_last_n exige
  Rail-Verdict: APPROVE — igualdade exata."
      _annex="$RAIL_FINAL_ANNEX_FILE"
    else
      die "o ULTIMO registro de rail traz Rail-Verdict: $_verdict
  arquivo: $_last
  O veredito de anexo so vale na familia $RAIL_ANNEX_FAMILY (achado SO em
  material) e na rodada final da familia $RAIL_FINAL_FAMILY (OQ-10)."
    fi
    [ -s "$_annex" ] || die "o ultimo registro de $_fam pede anexo ($_verdict), mas $_annex esta ausente ou vazio"
    git ls-files --error-unmatch -- "$_annex" >/dev/null 2>&1 \
      || die "o anexo $_annex NAO esta commitado — commite ANTES de assinar"
  elif [ "$_verdict" != "APPROVE" ]; then
    if [ "$_last_n" -ge "$RAIL_MAX_ROUNDS" ]; then
      die "o ULTIMO registro de rail traz Rail-Verdict: $_verdict
  arquivo: $_last
  A rodada $_last_n e a ultima da familia $_fam (OQ-10): nao ha outra rodada.
  O pacote nao e assinavel — leve o estado ao Owner."
    fi
    die "o ULTIMO registro de rail traz Rail-Verdict: $_verdict
  arquivo: $_last
  Um pacote so e assinavel depois de uma rodada de rail APPROVE — igualdade
  exata, sem qualificador. Trate os achados, rode outra rodada e registre-a
  como $_fam-$(( _last_n + 1 )).md (teto: $RAIL_MAX_ROUNDS rodadas)."
  fi
  RAIL_SUMMARY="$RAIL_SUMMARY $_fam:$_count(ultimo $( basename "$_last" ) $_verdict)"
done
ok "rail rastreado, dentro do teto de $RAIL_MAX_ROUNDS rodadas, e o ultimo de cada familia aprovado:$RAIL_SUMMARY"

# ---------------------------------------------------------------------------
# P0-f — substrato: o gerador, o derivador, jq e shellcheck respondem HOJE.
# ---------------------------------------------------------------------------
command -v jq >/dev/null 2>&1 || die "P0-f: jq ausente — o V4/V6 do LAND nao teriam instrumento"
command -v shellcheck >/dev/null 2>&1 || die "P0-f: shellcheck ausente — o V1 do LAND exige o lint dos scripts shell"
[ -f "$GEN_MODELS" ] || die "P0-f: $GEN_MODELS ausente"
# Modo generate (nao --check): pre-patch o --check responde com 7 ids e
# pos-patch com 8 — o que se sonda aqui e se o INSTRUMENTO responde.
python3 "$GEN_MODELS" >/dev/null 2>&1 \
  || die "P0-f: generate-available-models nao responde (modo generate)"
python3 "$APPLY" --list-paths "$APPLY_FLAG" >/dev/null 2>&1 \
  || die "P0-f: $APPLY --list-paths $APPLY_FLAG nao responde"
ok "substrato da wave responde (jq, shellcheck, gerador do ADR-149, derivador)"

# ---------------------------------------------------------------------------
# P0-g — a mensagem de commit nao tem trailer por preencher.
# ---------------------------------------------------------------------------
# O LAND recusa o trailer TO-FILL; descobrir isso DEPOIS de assinar obriga a
# um commit, que invalida o Anchor-SHA. Recusa aqui, antes do pinentry.
[ -f "$COMMIT_MSG" ] || die "mensagem de commit ausente: $COMMIT_MSG"
case "$(cat "$COMMIT_MSG")" in
  *"TO-FILL"*)
    die "a mensagem de commit ainda tem um campo TO-FILL por preencher:
  $COMMIT_MSG
  O CEO preenche o trailer Pair-Rail-Reviewed depois da ultima rodada do rail,
  commita, e so entao este script roda." ;;
esac
ok "mensagem de commit sem campo por preencher"

case "$(cat "$SENTINEL")" in
  *TO-FILL*)
    die "o sentinel ainda tem campo TO-FILL — re-derive o patch e re-pine o sha256" ;;
esac
ok "sentinel sem campo de patch por preencher"

if [ -f "$SENTINEL.asc" ]; then
  printf '  \033[33mWARN\033[0m ja existe %s — ele sera SOBRESCRITO.\n' "$SENTINEL.asc"
  if [ "$SELFTEST" = "0" ]; then
    read -r -p "  continuar? [y/N] " a
    case "$a" in y|Y) : ;; *) die "abortado pelo operador" ;; esac
  fi
fi

# ---------------------------------------------------------------------------
step "P1 — binding do patch (o que voce esta assinando)"
# ---------------------------------------------------------------------------
DECLARED="$( { grep -m1 '^Patch-sha256:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
ACTUAL="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
[ "$DECLARED" = "$ACTUAL" ] || die "o patch NAO casa o sha256 do sentinel
  no sentinel: $DECLARED
  no arquivo : $ACTUAL
  Alguem mexeu no patch. NAO assine ate reconciliar."
ok "patch casa o sha256 do sentinel"

# O MESMO sha tem de constar do registro PROPOSED-PATCH.md: o registro e o que
# a revisao leu; um registro apontando para outro patch e evidencia falsa.
PROPOSED_SHA="$( { grep -m1 '^Patch-sha256:' "$PROPOSED" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
[ -n "$PROPOSED_SHA" ] || die "$PROPOSED sem campo Patch-sha256"
[ "$PROPOSED_SHA" = "$ACTUAL" ] || die "o registro de revisao aponta para OUTRO patch
  em $PROPOSED: $PROPOSED_SHA
  no arquivo         : $ACTUAL"
ok "PROPOSED-PATCH.md aponta para o mesmo patch"

# A base contra a qual o patch foi gerado nao precisa ser o HEAD literal — o
# commit dos MATERIAIS acontece depois de derivar o patch e move o HEAD de
# proposito. O que precisa valer e mais preciso do que igualdade:
#   (1) a base e ancestral do HEAD (nao e uma linha paralela), e
#   (2) NENHUM path que o patch toca mudou entre a base e o HEAD.
HEAD_SHA="$(git rev-parse HEAD)"
PATCH_BASE="$( { grep -m1 '^Patch-base:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
[ -n "$PATCH_BASE" ] || die "sentinel sem campo Patch-base"
git merge-base --is-ancestor "$PATCH_BASE" "$HEAD_SHA" \
  || die "a base do patch NAO e ancestral do HEAD
  Patch-base: $PATCH_BASE
  HEAD atual: $HEAD_SHA
  A arvore andou por outro caminho. Re-derive o patch e repita."
DRIFT_TMP="$(mktemp)"
git diff --name-only "$PATCH_BASE" "$HEAD_SHA" | sort -u > "$DRIFT_TMP"
TOUCHED_TMP="$(mktemp)"
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$TOUCHED_TMP"
DRIFTED="$(comm -12 "$DRIFT_TMP" "$TOUCHED_TMP")"
rm -f "$DRIFT_TMP"
if [ -n "$DRIFTED" ]; then
  rm -f "$TOUCHED_TMP"
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "path(s) do patch mudaram entre a base e o HEAD:
$(printf '  %s\n' $DRIFTED)
  O patch foi revisado sobre outro conteudo. Re-derive e repita.
  (Foi esta a classe que abortou o pacote D duas vezes na S329: enquanto um
   pacote espera assinatura, nenhum dos seus destinos pode ser editado.)"
fi
ok "base $PATCH_BASE e ancestral do HEAD e nenhum path do patch derivou"

# P1-b — o patch commitado E a saida do derivador sobre o HEAD de agora.
# (O LAND prova o mesmo no V3, sobre a arvore pos-patch; aqui a prova vem
# ANTES do pinentry: o que voce assina e o que o script produz.)
REDERIVED="$(mktemp)"
rm -f "$REDERIVED"
_derive_patch "$REDERIVED" keep || { rm -f "$REDERIVED"; die "P1-b: a re-derivacao do patch a partir do HEAD falhou (acima)"; }
if ! cmp -s "$REDERIVED" "$PATCH"; then
  rm -f "$REDERIVED" "$TOUCHED_TMP"
  die "P1-b: o patch re-derivado do HEAD DIFERE do $PATCH commitado.
  O material commitado nao e a saida do derivador versionado — um land depois
  dos materiais mudou a pre-imagem, ou alguem editou o patch/derivador.
  Re-derive (--derive-patch), re-pine o sha256, commite e repita."
fi
rm -f "$REDERIVED"
ok "P1-b: HEAD + derivador == $PATCH, byte a byte"

# P1-c — o Scope assinado e EXATAMENTE o conjunto de paths do patch (o G4 do
# LAND checa o mesmo; recusar aqui evita uma assinatura que o land recusaria).
SCOPE_TMP="$(mktemp)"
awk '/BEGIN SIGNED SCOPE/{f=1;next} /END SIGNED SCOPE/{f=0} f' "$SENTINEL" \
  | sed -n 's/^[[:space:]]*-[[:space:]]*//p' | sed 's/[[:space:]]*$//' \
  | sort -u > "$SCOPE_TMP"
if ! cmp -s "$SCOPE_TMP" "$TOUCHED_TMP"; then
  _sc_extra="$(comm -23 "$TOUCHED_TMP" "$SCOPE_TMP" | tr '\n' ' ')"
  _sc_ghost="$(comm -13 "$TOUCHED_TMP" "$SCOPE_TMP" | tr '\n' ' ')"
  rm -f "$SCOPE_TMP" "$TOUCHED_TMP"
  die "P1-c: o Scope do sentinel difere dos paths do patch
  tocados fora do Scope: $_sc_extra
  no Scope sem toque   : $_sc_ghost"
fi
ok "P1-c: Scope == $(wc -l < "$TOUCHED_TMP" | tr -d ' ') path(s) do patch"

# P1-d — o que o LAND so compararia DEPOIS da assinatura, e e barato checar,
# e checado AQUI, antes do pinentry: o conjunto EXATO de paths tocados (o G4
# do LAND) e a contagem de ADRs no disco (o V8a do LAND) contra a base
# declarada. Um land livre que acrescente um ADR entre o commit dos
# materiais e a assinatura abortaria o LAND depois do V-block inteiro; a
# cura pede um commit dos materiais, que invalidaria o Anchor-SHA.
_sg_exp_paths="$(_expect EXPECTED_PATCH_PATHS | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u)"
_sg_obs_paths="$(LC_ALL=C sort -u "$TOUCHED_TMP")"
if [ "$_sg_obs_paths" != "$_sg_exp_paths" ]; then
  rm -f "$SCOPE_TMP" "$TOUCHED_TMP"
  die "P1-d: os paths do patch diferem de EXPECTED_PATCH_PATHS em $BASELINE_ENV
  declarado: $(printf '%s' "$_sg_exp_paths" | tr '\n' ' ')
  observado: $(printf '%s' "$_sg_obs_paths" | tr '\n' ' ')
  O G4 do LAND recusaria depois da assinatura. Reconcilie a base e repita."
fi
_sg_adr_obs="$(find "$ADR_DIR" -maxdepth 1 -name 'ADR-*.md' | wc -l | tr -d ' ')"
_sg_adr_exp="$(_expect EXPECTED_ADR_COUNT)"
if [ "$_sg_adr_obs" != "$_sg_adr_exp" ]; then
  rm -f "$SCOPE_TMP" "$TOUCHED_TMP"
  die "P1-d: $_sg_adr_obs ADR(s) no disco, EXPECTED_ADR_COUNT=$_sg_adr_exp em $BASELINE_ENV
  Um ADR entrou (ou saiu) depois do commit dos materiais: o V8a do LAND
  recusaria depois da assinatura. Atualize a base CONSCIENTEMENTE e repita."
fi
ok "P1-d: paths == EXPECTED_PATCH_PATHS e $_sg_adr_obs ADR(s) == EXPECTED_ADR_COUNT"
rm -f "$SCOPE_TMP" "$TOUCHED_TMP"

# P1-e — a suite do V2, ANTES do pinentry, quando o HEAD difere da base
# declarada FORA dos materiais desta cerimonia (rail r1, A-R1M9-05).
# EXPECTED_UNIT_PYTEST_* foi medido sobre Patch-base + patch; um land livre
# que mude, fora do patch, um teste da lista ou algo que ele le mudaria a
# contagem, e o V2 do LAND abortaria DEPOIS da assinatura. A suite roda no
# worktree do P1-b — HEAD + derivador, a mesma arvore que o LAND mede — e so
# quando ha essa deriva: sem ela, a medicao da base vale para o HEAD.
_sg_drift=""
while IFS= read -r _sg_p; do
  [ -n "$_sg_p" ] || continue
  case "$_sg_p" in
    "$PLAN_DIR"/*|"$PLAN_DIR"-*.md) : ;;
    *) _sg_drift="$_sg_drift $_sg_p" ;;
  esac
done < <( git diff --name-only "$PATCH_BASE" "$HEAD_SHA" )
if [ -z "$_sg_drift" ]; then
  ok "P1-e: o HEAD so difere de Patch-base nos materiais de $PLAN_ID — a contagem do V2 medida na base vale"
else
  [ -n "$DERIVE_WT" ] && [ -d "$DERIVE_WT" ] || die "P1-e: o worktree da re-derivacao sumiu"
  _sg_unit_tests="$(_expect EXPECTED_UNIT_TESTS)"
  _sg_pass_exp="$(_expect EXPECTED_UNIT_PYTEST_PASSED)"
  _sg_skip_exp="$(_expect EXPECTED_UNIT_PYTEST_SKIPPED)"
  _sg_unit_log="$(mktemp)"
  _sg_unit_rc=0
  # shellcheck disable=SC2086  # lista controlada, um path por palavra, sem espacos
  ( cd "$DERIVE_WT" && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest $_sg_unit_tests -q -p no:cacheprovider ) \
    > "$_sg_unit_log" 2>&1 || _sg_unit_rc=$?
  _sg_pass="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$_sg_unit_log" || true; } \
               | head -1 | { grep -oE '[0-9]+' || true; } )"
  _sg_skip="$( { grep -oE '[0-9]+ skipped' "$_sg_unit_log" || true; } | head -1 | { grep -oE '[0-9]+' || true; } )"
  [ -n "$_sg_skip" ] || _sg_skip=0
  if [ "$_sg_unit_rc" -ne 0 ] || [ "$_sg_pass" != "$_sg_pass_exp" ] || [ "$_sg_skip" != "$_sg_skip_exp" ]; then
    tail -15 "$_sg_unit_log" | sed 's/^/    /' >&2
    rm -f "$_sg_unit_log"
    die "P1-e: o HEAD difere de Patch-base fora dos materiais de $PLAN_ID:
 $(printf '%s' "$_sg_drift" | tr ' ' '\n' | sed '/^$/d; s/^/   /')
  e a suite do V2 sobre HEAD + derivador saiu rc=$_sg_unit_rc com ${_sg_pass:-?} passed / $_sg_skip skipped —
  esperado $_sg_pass_exp passed / $_sg_skip_exp skipped. O V2 do LAND recusaria DEPOIS da
  assinatura. Re-meca a base CONSCIENTEMENTE (ou re-derive sobre o HEAD novo) e repita."
  fi
  rm -f "$_sg_unit_log"
  ok "P1-e: deriva fora dos materiais; a suite do V2 sobre HEAD + derivador = $_sg_pass passed / $_sg_skip skipped (o declarado)"
fi
_drop_derive_wt

git apply --check "$PATCH" || die "git apply --check FALHOU — a arvore divergiu do patch"
ok "o patch aplica limpo na arvore atual"

PATCH_FILES="$(git apply --numstat "$PATCH" | wc -l | tr -d ' ')"
printf '      %s arquivo(s) no patch:\n' "$PATCH_FILES"
git apply --numstat "$PATCH" | awk '{printf "        %s\n", $3}'

# ---------------------------------------------------------------------------
step "P2 — identidade do signer"
# ---------------------------------------------------------------------------
if [ "$SELFTEST" = "1" ]; then
  FPR="SELFTEST0000000000000000000000000000000000"
  printf '  \033[33mAUTO-TESTE\033[0m signer sintetico: %s\n' "$FPR"
else
  FPR="${CEO_SIGNER_FPR:-}"
  if [ -z "$FPR" ]; then
    FPR="$(gpg --list-secret-keys --with-colons 2>/dev/null \
          | awk -F: '/^fpr:/{print $10; exit}')"
  fi
  [ -n "$FPR" ] || die "nenhuma chave GPG secreta encontrada.
  Passe explicitamente:  CEO_SIGNER_FPR=<fingerprint> bash $0"
  ok "signer: $FPR"

  if [ -f "$SIGNERS" ]; then
    grep -qi "$FPR" "$SIGNERS" \
      || die "o fingerprint $FPR NAO consta em $SIGNERS — o land abortaria no G1"
    ok "consta no rail rastreado"
  fi
fi

# ---------------------------------------------------------------------------
step "P3 — preenchendo os campos"
# ---------------------------------------------------------------------------
# Os placeholders deste sentinel-draft sao ANCHOR-PLACEHOLDER /
# DATA-PLACEHOLDER / APPROVED-BY-PLACEHOLDER — o regex ancora no placeholder
# REAL e ABORTA se o campo ja estiver preenchido (re-assinar sem reset e
# erro, nao sobrescrita silenciosa).
TODAY="$(date -u +%Y-%m-%d)"

python3 - "$SENTINEL" "$HEAD_SHA" "$TODAY" "$FPR" "$APPROVED_BY_HANDLE" <<'PY'
import re, sys
path, head, today, fpr, handle = sys.argv[1:6]
s = open(path, encoding="utf-8").read()

def fill(pattern, value, label):
    global s
    new, n = re.subn(pattern, value, s, count=1, flags=re.M)
    if n != 1:
        sys.exit("campo %s nao encontrado ou ja preenchido - inspecione %s"
                 % (label, path))
    s = new

fill(r"^Anchor-SHA: ANCHOR-PLACEHOLDER$", "Anchor-SHA: %s" % head, "Anchor-SHA")
fill(r"^Data: DATA-PLACEHOLDER$", "Data: %s" % today, "Data")
fill(r"^Approved-By: APPROVED-BY-PLACEHOLDER$",
     "Approved-By: %s %s" % (handle, fpr), "Approved-By")
open(path, "w", encoding="utf-8").write(s)
print("  campos preenchidos")
PY
ok "Anchor-SHA=$HEAD_SHA  Data=$TODAY"

printf '\n  Bloco que sera assinado:\n'
awk '/BEGIN SIGNED SCOPE/,/END SIGNED SCOPE/' "$SENTINEL" | sed 's/^/      /'

# ---------------------------------------------------------------------------
step "P4 — assinando"
# ---------------------------------------------------------------------------
if [ "$SELFTEST" = "1" ]; then
  printf 'SELFTEST-NOT-A-SIGNATURE\n' > "$SENTINEL.asc"
  ok "AUTO-TESTE: .asc sintetico gerado (nao e assinatura)"
else
  # "No pinentry" e o modo de falha conhecido deste setup (memoria do projeto).
  export GPG_TTY="${GPG_TTY:-$(tty 2>/dev/null || true)}"
  if command -v gpgconf >/dev/null 2>&1; then
    gpgconf --kill gpg-agent >/dev/null 2>&1 || printf ''
  fi
  if ! gpg --armor --detach-sign --yes --local-user "$FPR" "$SENTINEL"; then
    # O P3 ja reescreveu o sentinel; sem este rollback um re-run abortaria no
    # P0-c ("modificacao rastreada") e a recuperacao seria manual (pair-rail r9
    # P2 da S326). Restaura o sentinel do HEAD, byte a byte, e sai.
    git checkout -- "$SENTINEL"
    rm -f -- "$SENTINEL.asc"
    die "gpg falhou — sentinel RESTAURADO do HEAD (nada assinado).
  Modo de falha conhecido: 'No pinentry'. Rode NO SEU TERMINAL, nao via agente:
    export GPG_TTY=\$(tty); gpgconf --kill gpg-agent
  e repita este script do zero."
  fi
  ok "assinatura gerada: $SENTINEL.asc"
  gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /'
fi

step "PRONTO"
cat <<EOF

  A assinatura cobre o HEAD $HEAD_SHA.
  NAO commite nada agora — qualquer commit invalida o Anchor-SHA.

  PROXIMO COMANDO (copie e cole inteiro):

    bash $ROOT/$LAND_SCRIPT --dry-run

  Se todos os gates passarem, o comando seguinte aplica, verifica, commita e
  empurra (voce nao digita 'git' em momento nenhum). O V-block completo demora
  alguns minutos: verify-counts (~3 min), a governanca completa (~30 s) e o
  parity smoke (~35 s de install real) sao os gates de corpus deste pacote.

    bash $ROOT/$LAND_SCRIPT
EOF
