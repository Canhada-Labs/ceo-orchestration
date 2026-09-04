#!/usr/bin/env bash
# OWNER-S343-W4A-LAND.sh — land do pacote de cerimonia wave-s343-w4a (PLAN-186 W4a).
# CEREMONY-LINT: handwritten-exception: clone gate-a-gate do
# OWNER-S338-FABLE51-LAND.sh (familia adrgate; curas r1-r8 + rails
# 179close/183batch/fable51 herdadas). Muda o bloco de constantes E o V-block,
# que aqui prova a REPRODUTIBILIDADE do patch (worktree em HEAD + derivador
# versionado == arvore pos-patch, byte a byte, nos 2 paths), a COBERTURA
# re-derivada por node-id (o braco do AC-16 que autoriza a delecao), o lint de
# workflow com os flags EXATOS do step da CI e o NAO-VACUO nomeado — um
# V-block copiado testaria a coisa errada.
#
# `.github/workflows/validate.yml` esta em `_KERNEL_PATHS`
# (check_arbitration_kernel.py). O LAND arma CEO_KERNEL_OVERRIDE ele mesmo, no
# menor escopo, com o par reason-SLUG + I-ACCEPT validado VIVO contra o
# contrato do hook — mecanismo identico ao fable51 (ab56e76), ao adrgate
# (cfab980) e ao 183batch (b7dad83).
#
# Roda de QUALQUER diretorio. Nenhum passo e destrutivo antes de todos os
# gates passarem. Ao fim ele COMMITA (com -F, sem abrir editor) e EMPURRA —
# e ESSE PUSH E A CORRIDA 1/3 da medicao do AC-16.
#
# CUSTO: a re-derivacao de node-ids (~40 s), o verify-counts (~3 min) e a
# governanca completa (~30 s) sao o V-block caro deste pacote. A governanca
# roda SEM --fast de proposito: o modo completo checa o limite de 40k bytes do
# CLAUDE.md que o --fast pula (licao W5, CLAUDE.md par. 5).
#
# Uso:
#   bash .claude/plans/PLAN-186/OWNER-S343-W4A-LAND.sh --dry-run
#   bash .claude/plans/PLAN-186/OWNER-S343-W4A-LAND.sh
set -euo pipefail

# --- argumentos -----------------------------------------------------------
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *)
      printf '\n\033[31mABORT:\033[0m argumento desconhecido: %s\n' "$arg" >&2
      printf '  Formas validas:\n' >&2
      printf '    bash %s --dry-run\n' "$0" >&2
      printf '    bash %s\n' "$0" >&2
      exit 1 ;;
  esac
done

# A raiz resolve por git a partir da LOCALIZACAO DO SCRIPT, nunca por `../..`
# nem pelo cwd (licao S313).
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes da cerimonia (o UNICO bloco que muda entre waves) ----------
PLAN_DIR=".claude/plans/PLAN-186"
CEREMONY_DIR="$PLAN_DIR/s343-ceremony-w4a"
SENTINEL="$PLAN_DIR/wave-s343-w4a-approved.md"
PATCH="$CEREMONY_DIR/W4A.patch"
PROPOSED="$CEREMONY_DIR/PROPOSED-PATCH.md"
COMMIT_MSG="$CEREMONY_DIR/COMMIT-MSG-W4A.txt"
BASELINE_ENV="$CEREMONY_DIR/EXPECTED-BASELINE.txt"
SIGN_SCRIPT="$PLAN_DIR/OWNER-S343-W4A-SIGN.sh"
MEASURE_SCRIPT="$PLAN_DIR/OWNER-S343-W4A-MEASURE.sh"
# Gerador COMPARTILHADO com a cerimonia do PLAN-183 (ja rastreado la).
FINALIZE=".claude/plans/PLAN-183/w5-ceremony/finalize_patch.py"
APPLY="$CEREMONY_DIR/apply-w4a-validate-deletion.py"
RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"
MANIFEST=".claude/governance/gate-scripts-manifest.txt"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
VALIDATE_SH=".claude/scripts/validate-governance.sh"
# A suite alvo: os testes que LEEM os dois workflows vivos (derivada por
# `grep -rn '\.github/workflows/validate\.yml'` sobre os testpaths). Nenhum
# deles parseia os steps hoje — e por isso que o conjunto e pequeno; se um
# passar a parsear, e AQUI que ele fica vermelho, nao na CI do dia seguinte.
UNIT_TESTS=".claude/hooks/tests/test_check_canonical_edit.py \
.claude/hooks/tests/test_kernel_subsumes_security_critical_lib.py \
.claude/scripts/tests/test_release_bump_sites.py \
.claude/scripts/tests/test_check_active_hooks_executable.py \
.claude/scripts/tests/test_validate_template_frozen_subset.py \
.claude/scripts/tests/test_parity_source_resolution.py"
PUSH_REMOTE="origin"
PUSH_BRANCH="main"
# --------------------------------------------------------------------------

die() { printf '\n\033[31mABORT:\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m  ok\033[0m  %s\n' "$*"; }
warn(){ printf '  \033[33mWARN\033[0m %s\n' "$*"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

# --- interruptor de AUTO-TESTE (recusado fora do scratchpad) ---------------
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
  printf '\033[33m  MODO AUTO-TESTE\033[0m — GPG e push desligados.\n'
fi

# NAO ha interruptor de pulo de gate nesta wave, e a ausencia e deliberada:
# um interruptor sem razao de existir e superficie de ataque.

LINT_STATUS="nao-executado"
UNIT_STATUS="nao-executado"
COVERAGE_STATUS="nao-executado"

# Leitor da base esperada: sem `source` (o arquivo nao executa nada), e
# fail-CLOSED quando a chave falta.
_expect() {
  _ev="$(sed -n "s/^$1=//p" "$BASELINE_ENV" | head -1 | sed 's/^"//; s/"$//')"
  if [ -z "$_ev" ]; then
    die "chave '$1' AUSENTE em $BASELINE_ENV — o V-block nao compara contra nada"
  fi
  printf '%s' "$_ev"
}

# ---------------------------------------------------------------------------
step "G-PRE — substrato e base declarada"
# ---------------------------------------------------------------------------
[ -f "$BASELINE_ENV" ] || die "base esperada AUSENTE: $BASELINE_ENV
  Sem ela cada execucao do V-block e ruido. Rode o finalize-w4a.sh."
command -v actionlint >/dev/null 2>&1 || die "G-PRE: actionlint ausente — o V4 roda o MESMO lint do step da CI"
command -v shellcheck >/dev/null 2>&1 || die "G-PRE: shellcheck ausente — o actionlint o chama nos blocos run:"
python3 -c "import yaml" >/dev/null 2>&1 || die "G-PRE: PyYAML ausente — o V4 conta jobs e steps"
[ -f "$APPLY" ] || die "G-PRE: derivador ausente: $APPLY"
[ -f "$MANIFEST" ] || die "G-PRE: manifesto ADR-192 ausente: $MANIFEST"
python3 "$APPLY" --list-paths >/dev/null 2>&1 || die "G-PRE: apply-w4a-validate-deletion.py --list-paths nao responde"
ok "G-PRE: actionlint, shellcheck, PyYAML e derivador presentes"

# ---------------------------------------------------------------------------
step "G0 — insumos, materiais rastreados e arvore limpa"
# ---------------------------------------------------------------------------
# O commit avanca o HEAD ATUAL, e `git push origin main` empurra o ref LOCAL
# main — fora do main o push "sucede" sem levar o commit assinado. Fail-closed.
_cur_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '')"
[ "$_cur_branch" = "$PUSH_BRANCH" ] || die "HEAD esta em '$_cur_branch', nao em '$PUSH_BRANCH' — o land so roda no $PUSH_BRANCH (git checkout $PUSH_BRANCH)"
ok "G0: HEAD em $PUSH_BRANCH"

[ -f "$SENTINEL" ] || die "sentinel ausente: $SENTINEL"
[ -f "$PATCH" ]    || die "patch ausente: $PATCH"
[ -f "$SENTINEL.asc" ] || die "assinatura ausente: $SENTINEL.asc
  O Owner assina com:  bash $ROOT/$SIGN_SCRIPT"
[ -f "$COMMIT_MSG" ] || die "mensagem de commit ausente: $COMMIT_MSG"
[ -f "$ORACLE" ] || die "oraculo de canonicidade ausente: $ORACLE"
ok "sentinel, patch, .asc, mensagem e base esperada presentes"

MATERIALS=(
  "$SIGN_SCRIPT"
  "$PLAN_DIR/OWNER-S343-W4A-LAND.sh"
  "$MEASURE_SCRIPT"
  "$PROPOSED"
  "$COMMIT_MSG"
  "$BASELINE_ENV"
  "$CEREMONY_DIR/BASE-SHA.txt"
  "$CEREMONY_DIR/finalize-w4a.sh"
  "$APPLY"
  "$CEREMONY_DIR/test-ceremony-scripts-w4a.sh"
  "$CEREMONY_DIR/DESIGN-W4A-S343.md"
  "$CEREMONY_DIR/EVIDENCE.md"
  "$FINALIZE"
  "$PATCH"
  "$SENTINEL"
)
for m in "${MATERIALS[@]}"; do
  git ls-files --error-unmatch -- "$m" >/dev/null 2>&1 \
    || die "material de cerimonia NAO commitado: $m — commite os materiais antes de assinar/landar"
done
RAIL_COUNT=0
for r in $RAIL_GLOB; do
  [ -f "$r" ] || continue
  git ls-files --error-unmatch -- "$r" >/dev/null 2>&1 \
    || die "registro de rail NAO commitado: $r"
  RAIL_COUNT=$(( RAIL_COUNT + 1 ))
done
[ "$RAIL_COUNT" -gt 0 ] || die "nenhum registro de rail em $RAIL_GLOB"
ok "materiais e $RAIL_COUNT registro(s) de rail rastreados"

# Porcelain parsed NUL-delimited: o corte de 3 caracteres deixaria `old -> new`
# inteiro num rename, e o oraculo classificaria pelo path VELHO. Aqui:
# renames/copias ABORTAM, e path com newline ABORTA.
TMPDIR_LAND="$(mktemp -d)"
# Estado do trap declarado ANTES do trap: sob `set -u` uma variavel nao
# inicializada no handler mata o handler, e o dry-run deixaria o patch
# aplicado. O trap entra AQUI, nao depois dos gates.
APPLIED=0
RESTORE_ON_EXIT=0
STAGED_BY_LAND=0   # rail r4: NUNCA herdado do ambiente
WT_REPRO=""        # worktree do V2/V3 — removido no trap
FP_BEFORE=""
_fingerprint() {
  {
    git status --porcelain=v1
    printf -- '--index--\n'
    git diff --cached --name-status
  } | shasum -a 256 | awk '{print $1}'
}
_restore() {
  # exit status na ENTRADA do trap — capturado na PRIMEIRA linha (rail r2
  # P2-h: qualquer comando antes daqui zera o $? e os logs de um abort
  # jamais seriam preservados).
  _land_rc=$?
  # Backstop do override de kernel (r1 P1): qualquer saida desarma.
  unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK 2>/dev/null || true
  if [ -n "$WT_REPRO" ] && [ -d "$WT_REPRO" ]; then
    git worktree remove --force "$WT_REPRO" >/dev/null 2>&1 || true
    rm -rf "$WT_REPRO" 2>/dev/null || true
    git worktree prune >/dev/null 2>&1 || true
  fi
  if [ "$RESTORE_ON_EXIT" = "1" ] && [ "$APPLIED" = "1" ]; then
    # Reset SCOPED aos paths do patch (rail-materials r1 P2-a): o G0 tolera
    # staged nao-canonico de terceiros, e um reset global o des-stagearia
    # junto. Deriva os paths do proprio patch.
    git apply --numstat "$PATCH" 2>/dev/null | cut -f3 | while IFS= read -r _pp; do
      [ -n "$_pp" ] && git reset -q -- "$_pp" >/dev/null 2>&1 || true
    done
    # O passo S tambem stageia sentinel + .asc (rail r2 P2-g) — mas SO este
    # script pode des-stagear o que ELE stageou (rail r3 P2-k).
    if [ "${STAGED_BY_LAND:-0}" = "1" ]; then
      git reset -q -- "$SENTINEL" "$SENTINEL.asc" >/dev/null 2>&1 || true
    fi
    if git apply -R "$PATCH" >/dev/null 2>&1; then
      APPLIED=0
      _fp_after="$(_fingerprint)"
      if [ "$_fp_after" = "$FP_BEFORE" ]; then
        printf '\033[32m  ok\033[0m  arvore e index restaurados byte a byte (patch revertido; nada foi commitado)\n'
      else
        printf '\n\033[31mRESTAURACAO INCOMPLETA\033[0m — o estado difere do inicial.\n' >&2
        printf '  Inspecione:  git -C %s status\n' "$ROOT" >&2
        # Rail r3 do land (P2): sem esta linha o `--dry-run` sairia 0. O bash
        # PRESERVA o status que o processo tinha ao entrar no trap EXIT, e num
        # dry-run VERDE esse status e 0 — entao uma restauracao que falhou
        # deixaria os workflows CANONICOS mutados com a cerimonia anunciando
        # sucesso. Um dry-run que nao restaurou nao e um dry-run.
        _land_rc=4
      fi
    else
      printf '\n\033[31mFALHA AO RESTAURAR\033[0m — a arvore ficou com o patch aplicado.\n' >&2
      printf '  Restaure a mao:  git -C %s apply -R %s\n' "$ROOT" "$PATCH" >&2
      _land_rc=4
    fi
  fi
  # Licao S329-manha: o abort do V-block apagava o UNICO log do gate caro junto
  # com o tmpdir. Preserva os logs no dir DESTA cerimonia ANTES de remover.
  _keep_dir="$ROOT/$CEREMONY_DIR"
  if [ "$_land_rc" != "0" ] && [ -d "$TMPDIR_LAND" ] && [ -d "$_keep_dir" ] && [ -w "$_keep_dir" ]; then
    _logs_kept=0
    for _l in "$TMPDIR_LAND"/*.log; do
      [ -f "$_l" ] || continue
      _kept="$_keep_dir/land-w4a-$(date +%Y%m%d-%H%M%S)-$(basename "$_l")"
      # rail-materials r1 P2-a: destino pre-existente ou symlink e RECUSADO.
      if [ -e "$_kept" ] || [ -L "$_kept" ]; then
        printf '  log NAO preservado (destino ja existe): %s\n' "$_kept" >&2
        continue
      fi
      cp -p "$_l" "$_kept" 2>/dev/null && { _logs_kept=$((_logs_kept+1)); printf '  log preservado: %s\n' "$_kept"; }
    done
    if [ "$_logs_kept" -gt 0 ]; then
      printf '  NOTA: %s log(s) preservados na arvore DE PROPOSITO (abort com evidencia);\n' "$_logs_kept"
      printf '        a restauracao acima cobre os paths do patch, nao estes logs.\n'
    fi
  fi
  rm -rf "$TMPDIR_LAND"
  # Rail r3 do land (P2): o trap TEM de re-emitir o status. O bash preserva o
  # status de entrada do trap EXIT, entao um `_land_rc=4` atribuido la em cima
  # seria decorativo — o `--dry-run` sairia 0 mesmo com os workflows canonicos
  # ainda mutados. Quando nada escalou, `_land_rc` E o status de entrada e este
  # `exit` e um no-op.
  exit "$_land_rc"
}
trap _restore EXIT

# --- kernel-override hygiene (molde W3K; rail-materials r1 P1) -------------
# O patch toca .github/workflows/validate.yml (_KERNEL_PATHS). A cerimonia de
# kernel ARMA o override ELA MESMA, no menor escopo — e RECUSA rodar se o
# override ja vier do ambiente: duas cerimonias na mesma sessao e onde um
# export sobra e autoriza o pack seguinte sem ninguem pedir.
if [ -n "${CEO_KERNEL_OVERRIDE:-}" ] || [ -n "${CEO_KERNEL_OVERRIDE_ACK:-}" ]; then
  die "CEO_KERNEL_OVERRIDE/_ACK ja estao no ambiente ANTES deste script.
  Desarme (unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK) e re-rode —
  este LAND arma e desarma o proprio override, no menor escopo."
fi

DIRTY_FILE="$TMPDIR_LAND/dirty"
PATCHED_FILE="$TMPDIR_LAND/patched"
SCOPE_FILE="$TMPDIR_LAND/scope"
TOUCHED_FILE="$TMPDIR_LAND/touched"
EXPECTED_FILE="$TMPDIR_LAND/expected"
STAGED_FILE="$TMPDIR_LAND/staged"
: > "$DIRTY_FILE"
while IFS= read -r -d '' entry; do
  xy="${entry:0:2}"
  entry_path="${entry:3}"
  case "$xy" in
    *R*|*C*)
      IFS= read -r -d '' _renamed_from || true
      die "rename/copia na arvore suja ($xy: $_renamed_from -> $entry_path) — resolva (commit ou reverta) antes do land" ;;
  esac
  case "$entry_path" in
    *$'\n'*) die "path com newline na arvore suja — recusado" ;;
  esac
  printf '%s\n' "$entry_path" >> "$DIRTY_FILE"
done < <(git status --porcelain=v1 -z)
sort -u -o "$DIRTY_FILE" "$DIRTY_FILE"

git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$PATCHED_FILE"
COLLIDE="$(comm -12 "$DIRTY_FILE" "$PATCHED_FILE")"
if [ -n "$COLLIDE" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "arquivo(s) do patch estao MODIFICADOS na arvore:
$(printf '  %s\n' $COLLIDE)
  O patch aterrissaria sobre conteudo diferente do assinado.
  Commite ou reverta esses arquivos antes do land."
fi

# Allowlist FECHADA: so os artefatos da propria cerimonia podem estar sujos
# entre os paths guardados. A canonicidade de cada path sujo vem do ORACULO
# (a mesma _CANONICAL_GUARDS que o hook aplica) — NUNCA de uma lista espelhada
# aqui. Oraculo indisponivel => ABORTA.
CEREMONY_OK=(
  "$SENTINEL"
  "$SENTINEL.asc"
  "$PATCH"
)
GUARDED_DIRTY=""
OTHER_DIRTY=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  skip=0
  for allowed in "${CEREMONY_OK[@]}"; do
    if [ "$f" = "$allowed" ]; then skip=1; break; fi
  done
  [ "$skip" = "1" ] && continue
  verdict="$(python3 "$ORACLE" --is-canonical "$f" 2>/dev/null | awk -F'\t' 'NR==1{print $2}')"
  case "$verdict" in
    1) GUARDED_DIRTY="$GUARDED_DIRTY  $f
" ;;
    0) OTHER_DIRTY="$OTHER_DIRTY  $f
" ;;
    *) die "oraculo de canonicidade nao respondeu 0|1 para: $f (saida: '$verdict')" ;;
  esac
done < "$DIRTY_FILE"

if [ -n "$GUARDED_DIRTY" ]; then
  die "path(s) CANONICOS sujos fora do Scope assinado:
$GUARDED_DIRTY  Commite-os SEPARADAMENTE antes, ou inclua-os no Scope e re-assine."
fi
# Rail r3 do land (P1): um MATERIAL de cerimonia sujo NAO e "mudanca
# nao-guardada tolerada". O oraculo diz que `EXPECTED-BASELINE.txt` e
# `COMMIT-MSG-W4A.txt` sao nao-canonicos — verdade, e irrelevante: o
# `Anchor-SHA` amarra o HEAD, e um material editado DEPOIS da assinatura e
# consumido pelo LAND a partir da ARVORE DE TRABALHO. Editar a base esperada
# entre o SIGN e o LAND afrouxaria os limiares do V-block inteiro com a
# assinatura ainda casando. Materiais sujos sao RECUSA, nao aviso.
# DOIS materiais ficam DE FORA, e nao por conveniencia:
#  - o SENTINEL e mutado pelo proprio SIGN na arvore de trabalho (Anchor-SHA,
#    Data, Approved-By) e e exatamente esse conteudo que o `.asc` assina —
#    qualquer edicao posterior derruba o G1 na verificacao GPG;
#  - o PATCH tem gate PROPRIO e mais especifico, o G2, que compara o sha256
#    contra o `Patch-sha256` do sentinel assinado. Recusar aqui trocaria uma
#    mensagem precisa por uma generica.
# O que sobra e justamente o que NAO tinha dono: a base esperada, a mensagem de
# commit, o derivador, os scripts e a documentacao da wave.
MATERIALS_DIRTY=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  case "$f" in
    "$SENTINEL"|"$SENTINEL.asc"|"$PATCH") continue ;;
  esac
  for m in "${MATERIALS[@]}"; do
    if [ "$f" = "$m" ]; then
      MATERIALS_DIRTY="$MATERIALS_DIRTY  $f
"
    fi
  done
done < "$DIRTY_FILE"
if [ -n "$MATERIALS_DIRTY" ]; then
  die "material(is) de cerimonia MODIFICADO(S) depois da assinatura:
$MATERIALS_DIRTY  O Anchor-SHA amarra o COMMIT, mas o LAND le estes arquivos da arvore de
  trabalho — uma edicao aqui muda o que os gates comparam sem invalidar o
  .asc. Commite a mudanca e RE-ASSINE, ou desfaca:
    git -C $ROOT restore --staged --worktree -- <paths acima>"
fi

if [ -n "$OTHER_DIRTY" ]; then
  warn "mudancas nao-guardadas fora do patch (toleradas, NAO entram no commit):"
  printf '%s' "$OTHER_DIRTY"
fi
ok "nenhum arquivo do patch sujo; nenhum path canonico sujo fora do Scope; nenhum material de cerimonia sujo"

# ---------------------------------------------------------------------------
step "G1 — assinatura GPG + ancora"
# ---------------------------------------------------------------------------
if [ "$SELFTEST" = "1" ]; then
  warn "AUTO-TESTE: verificacao GPG PULADA (o .asc e sintetico)"
else
  gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1 | sed 's/^/    /' \
    || die "assinatura GPG NAO verifica"
  ok "assinatura verificada"

  if [ -f "$SIGNERS" ]; then
    # Sem `grep | head || true`: sob pipefail o `head` mata o produtor com
    # SIGPIPE(141) e o `|| true` mascara a diferenca entre "nao achou" e
    # "morreu". awk casa e sai por conta propria, exit 0 sempre.
    GPG_OUT="$(gpg --verify "$SENTINEL.asc" "$SENTINEL" 2>&1)"
    FPR="$(printf '%s\n' "$GPG_OUT" \
           | awk 'match($0, /[A-F0-9]{40}/) { print substr($0, RSTART, RLENGTH); exit }')"
    [ -n "$FPR" ] || die "nao consegui extrair o fingerprint da assinatura"
    grep -qi "$FPR" "$SIGNERS" || die "fingerprint $FPR NAO consta em $SIGNERS"
    ok "signer $FPR consta no rail rastreado"
  else
    warn "$SIGNERS ausente — rail de signer nao verificado"
  fi
fi

# Campos obrigatorios preenchidos (um sentinel com placeholder foi assinado
# antes da finalizacao — a assinatura seria valida e a autorizacao, vazia).
for field in "Approved-By" "Anchor-SHA" "Data" "Patch-sha256" "Patch-base"; do
  val="$( { grep -m1 "^$field:" "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
  [ -n "$val" ] || die "sentinel sem campo '$field:'"
  case "$val" in
    *TO-FILL*|*PLACEHOLDER*) die "campo '$field:' ainda e placeholder ($val) — o sentinel nao foi assinado pelo SIGN" ;;
  esac
done

ANCHOR="$( { grep -m1 '^Anchor-SHA:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
HEAD_SHA="$(git rev-parse HEAD)"
[ "$ANCHOR" = "$HEAD_SHA" ] || die "Anchor-SHA nao bate com HEAD
  ancora: $ANCHOR
  HEAD  : $HEAD_SHA
  Commits entraram depois da assinatura. Re-gere o Anchor e RE-ASSINE."
ok "ancora casa HEAD ($HEAD_SHA)"

# ---------------------------------------------------------------------------
step "G2 — binding do patch (Patch-sha256)"
# ---------------------------------------------------------------------------
DECLARED="$( { grep -m1 '^Patch-sha256:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
ACTUAL="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
[ "$DECLARED" = "$ACTUAL" ] || die "patch NAO bate com o sentinel assinado
  declarado: $DECLARED
  real     : $ACTUAL
  O patch mudou depois da assinatura. Re-assine ou restaure o patch."
ok "patch casa o sha256 assinado ($ACTUAL)"

# ---------------------------------------------------------------------------
step "G3 — o patch aplica limpo (modo checagem, nada muda ainda)"
# ---------------------------------------------------------------------------
git apply --check "$PATCH" || die "git apply --check FALHOU — a arvore divergiu do patch"
ok "aplica limpo"

# ---------------------------------------------------------------------------
step "G4 — touched == scope (NOS DOIS SENTIDOS)"
# ---------------------------------------------------------------------------
# Sem filtro de canonicidade: TODO path tocado tem de estar no Scope assinado,
# canonico ou nao. E o inverso tambem e fatal — um Scope que autoriza o que o
# patch nao toca e uma autorizacao mais larga do que a revisao.
awk '/BEGIN SIGNED SCOPE/{f=1;next} /END SIGNED SCOPE/{f=0} f' "$SENTINEL" \
  | sed -n 's/^[[:space:]]*-[[:space:]]*//p' | sed 's/[[:space:]]*$//' \
  | sort -u > "$SCOPE_FILE"
[ -s "$SCOPE_FILE" ] || die "bloco Scope vazio ou nao encontrado no sentinel"

git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$TOUCHED_FILE"
[ -s "$TOUCHED_FILE" ] || die "o patch nao toca arquivo nenhum"

EXTRA="$(comm -23 "$TOUCHED_FILE" "$SCOPE_FILE")"
if [ -n "$EXTRA" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "o patch toca path(s) FORA do Scope assinado:
$(printf '  %s\n' $EXTRA)
  Um Scope que nao cobre um path tocado invalida a autorizacao."
fi
GHOST="$(comm -13 "$TOUCHED_FILE" "$SCOPE_FILE")"
if [ -n "$GHOST" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "o Scope autoriza path(s) que o patch NAO toca:
$(printf '  %s\n' $GHOST)
  Autorizacao mais larga do que o patch revisado. Refinalize o patch
  (finalize_patch.py deriva o Scope) e RE-ASSINE."
fi
ok "$(wc -l < "$TOUCHED_FILE" | tr -d ' ') path(s): touched == scope nos dois sentidos"

# Defesa em profundidade sobre o mesmo par que o SIGN checou: a base do patch
# e ancestral do HEAD e nenhum path tocado derivou entre as duas.
PATCH_BASE="$( { grep -m1 '^Patch-base:' "$SENTINEL" || true; } | sed 's/^[^:]*: *//' | tr -d '[:space:]')"
git merge-base --is-ancestor "$PATCH_BASE" "$HEAD_SHA" \
  || die "a base do patch ($PATCH_BASE) NAO e ancestral do HEAD ($HEAD_SHA)"
git diff --name-only "$PATCH_BASE" "$HEAD_SHA" | sort -u > "$TMPDIR_LAND/drift"
DRIFTED="$(comm -12 "$TMPDIR_LAND/drift" "$TOUCHED_FILE")"
if [ -n "$DRIFTED" ]; then
  # shellcheck disable=SC2086  # lista controlada, sem espacos nos paths
  die "path(s) do patch mudaram entre a base assinada e o HEAD:
$(printf '  %s\n' $DRIFTED)
  O patch foi revisado sobre outro conteudo."
fi
ok "base $PATCH_BASE ancestral do HEAD; nenhum path do patch derivou"

# Conjunto EXATO de paths tocados, contra a base declarada.
_exp_paths="$(_expect EXPECTED_PATCH_PATHS | tr ' ' '\n' | sed '/^$/d' | LC_ALL=C sort -u)"
_obs_paths="$(LC_ALL=C sort -u "$TOUCHED_FILE")"
[ "$_obs_paths" = "$_exp_paths" ] || die "G4: conjunto de paths tocados difere do DECLARADO
  declarado: $(printf '%s' "$_exp_paths" | tr '\n' ' ')
  observado: $(printf '%s' "$_obs_paths" | tr '\n' ' ')"
ok "G4: conjunto de paths casa EXPECTED_PATCH_PATHS"

# ---------------------------------------------------------------------------
step "G5 — grants do sentinel + coerencia do manifesto ADR-192"
# ---------------------------------------------------------------------------
# Assinatura GPG valida NAO e autorizacao mecanica (licao S318: um sentinel
# verificou e concedia ZERO paths). Aqui cada path CANONICO tocado e provado
# concedido pela MESMA funcao que o hook usa, `_sentinel_grants_path`.
if [ "$SELFTEST" = "1" ]; then
  # O unlock exige PROVENIENCIA: sem ela ele nega tudo e o G5 reprovaria por
  # motivo ERRADO, deixando o controle positivo do parse de Scope VACUO.
  SELFTEST_SENTINEL_SHA="$(shasum -a 256 "$SENTINEL" | awk '{print $1}')"
  G5_ENV=(env "CEO_SENTINEL_UNLOCK=PLAN-186-wave-s343-w4a" \
              "CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT" \
              "CEO_SENTINEL_UNLOCK_SHA256=$SELFTEST_SENTINEL_SHA")
else
  G5_ENV=(env)
fi
"${G5_ENV[@]}" python3 - "$ROOT" "$SENTINEL" "$TOUCHED_FILE" "$MANIFEST" <<'PY' || die "G5 reprovou"
import importlib.util, os, sys
from pathlib import Path

root, sentinel_rel, touched_file, manifest_rel = sys.argv[1:5]
os.environ["CLAUDE_PROJECT_DIR"] = root
sys.path.insert(0, os.path.join(root, ".claude", "hooks"))
spec = importlib.util.spec_from_file_location(
    "_cce_land", os.path.join(root, ".claude/hooks/check_canonical_edit.py"))
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception as exc:
    sys.exit("nao consegui carregar o oraculo de sentinel: %r" % (exc,))

sentinel = Path(root) / sentinel_rel
repo_root = Path(root)
with open(touched_file, encoding="utf-8") as fh:
    touched = [ln.strip() for ln in fh if ln.strip()]

canonical, ungranted = [], []
for rel in touched:
    try:
        is_canon = mod._is_canonical(rel, repo_root)
    except Exception:
        is_canon = True          # fail-CLOSED: inclassificavel conta como canonico
    if not is_canon:
        continue
    canonical.append(rel)
    if not mod._sentinel_grants_path(sentinel, rel):
        ungranted.append(rel)

if ungranted:
    sys.stderr.write(
        "  paths CANONICOS tocados que o sentinel NAO concede:\n"
        + "".join("    %s\n" % p for p in ungranted)
        + "  Assinatura valida que concede zero paths nao autoriza nada (S318).\n")
    sys.exit(1)

# Membro do manifesto ADR-192 tocado exige bump do sha NO MESMO patch.
members = set()
with open(os.path.join(root, manifest_rel), encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            members.add(parts[1].strip())
touched_members = sorted(set(touched) & members)
if touched_members and manifest_rel not in set(touched):
    sys.stderr.write(
        "  membro(s) do manifesto ADR-192 tocado(s) sem tocar o manifesto:\n"
        + "".join("    %s\n" % p for p in touched_members)
        + "  O oraculo responde 0 para um membro, mas editar membro passa pela\n"
          "  cerimonia E exige bump do sha em %s (licao S326).\n" % manifest_rel)
    sys.exit(1)

print("  %d path(s) canonico(s), todos concedidos pelo sentinel" % len(canonical))
print("  %d membro(s) do manifesto ADR-192 tocado(s)" % len(touched_members))
PY
ok "grants provados e manifesto estruturalmente coerente"

# O NUMERO de paths canonicos tambem e comparado contra a base DECLARADA.
_obs_canon="$(python3 - "$ROOT" "$TOUCHED_FILE" <<'PY'
import importlib.util, os, sys
from pathlib import Path
root, touched_file = sys.argv[1:3]
os.environ["CLAUDE_PROJECT_DIR"] = root
sys.path.insert(0, os.path.join(root, ".claude", "hooks"))
spec = importlib.util.spec_from_file_location(
    "_cce_count", os.path.join(root, ".claude/hooks/check_canonical_edit.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
with open(touched_file, encoding="utf-8") as fh:
    touched = [ln.strip() for ln in fh if ln.strip()]
n = 0
for rel in touched:
    try:
        if mod._is_canonical(rel, Path(root)):
            n += 1
    except Exception:
        n += 1        # fail-CLOSED
print(n)
PY
)"
_exp_canon="$(_expect EXPECTED_PATCH_CANONICAL_PATHS)"
[ "$_obs_canon" = "$_exp_canon" ] \
  || die "G5: $_obs_canon path(s) CANONICOS no patch, esperado $_exp_canon.
  Menos significa que um alvo canonico da wave saiu do patch; mais significa que
  o patch cresceu para superficie que a revisao nao leu."
ok "G5: $_obs_canon path(s) canonico(s) (esperado $_exp_canon)"

_obs_members="$(python3 - "$ROOT" "$TOUCHED_FILE" "$MANIFEST" <<'PY'
import os, sys
root, touched_file, manifest_rel = sys.argv[1:4]
members = set()
with open(os.path.join(root, manifest_rel), encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            members.add(parts[1].strip())
with open(touched_file, encoding="utf-8") as fh:
    touched = {ln.strip() for ln in fh if ln.strip()}
print(len(touched & members))
PY
)"
_exp_members="$(_expect EXPECTED_MANIFEST_MEMBERS_TOUCHED)"
[ "$_obs_members" = "$_exp_members" ] \
  || die "G5: $_obs_members membro(s) do manifesto ADR-192 tocado(s), esperado $_exp_members"
ok "G5: membros do manifesto tocados = $_obs_members (esperado $_exp_members)"

# ---------------------------------------------------------------------------
step "G6 — NAO-VACUO em HEAD (o que a wave apaga TEM de existir ANTES)"
# ---------------------------------------------------------------------------
# Antes de mutar: os dois steps e o timeout velho existem no HEAD, cada um
# UMA vez. Se ja nao existirem, o patch nao esta deletando nada e a wave e
# vacua — um land verde sobre uma delecao que ja aconteceu.
_v_rel="$(_expect EXPECTED_VALIDATE_YML_REL)"
_s_rel="$(_expect EXPECTED_SMOKE_YML_REL)"
_step_a="$(_expect EXPECTED_DELETED_STEP_A)"
_step_b="$(_expect EXPECTED_DELETED_STEP_B)"
_head_a="$( git show "HEAD:$_v_rel" | { grep -c -F -- "- name: $_step_a" || true; } )"
_head_b="$( git show "HEAD:$_v_rel" | { grep -c -F -- "- name: $_step_b" || true; } )"
{ [ "$_head_a" = "1" ] && [ "$_head_b" = "1" ]; } \
  || die "G6: em HEAD o step A aparece $_head_a vez(es) e o step B $_head_b — esperado 1 e 1.
  A wave nao esta deletando o que diz deletar."
_head_to="$( git show "HEAD:$_s_rel" | { grep -c -F -- "timeout-minutes: $(_expect EXPECTED_SMOKE_TIMEOUT_HEAD)" || true; } )"
[ "$_head_to" = "1" ] \
  || die "G6: 'timeout-minutes: $(_expect EXPECTED_SMOKE_TIMEOUT_HEAD)' aparece $_head_to vez(es) em HEAD:$_s_rel, esperado 1"
_head_steps="$( git show "HEAD:$_v_rel" | python3 -c "
import sys, yaml
d = yaml.safe_load(sys.stdin)
print(len(d['jobs']['validate']['steps']))
" )"
[ "$_head_steps" = "$(_expect EXPECTED_VALIDATE_STEPS_HEAD)" ] \
  || die "G6: o job validate tem $_head_steps steps em HEAD, esperado $(_expect EXPECTED_VALIDATE_STEPS_HEAD)"
ok "G6: HEAD tem os 2 steps (1 cada), o timeout $(_expect EXPECTED_SMOKE_TIMEOUT_HEAD) e $_head_steps steps no job validate"

# ---------------------------------------------------------------------------
step "G7 — a janela de required-check: MEDIDA, nunca assumida"
# ---------------------------------------------------------------------------
# ACHADO P1 do rail codex r1, que CONFIRMOU independentemente o r24 do
# relatorio da S340: `docs/BRANCH-PROTECTION.md:101-105` documenta UM status
# check obrigatorio — o do job `validate`, cujo `name:` e a frase «Governance,
# health, contamination, ...». Depois desta delecao as suites de hooks e de
# scripts rodam SO em `hook-tests-python-matrix (3.9)` e `(3.12)`, que sao
# OUTROS status. Numa PR, uma matriz VERMELHA passaria a coexistir com um
# required check VERDE.
# (A frase do `name:` fica truncada de proposito neste comentario: uma linha
#  de comentario que COMECE com a palavra que o linter reserva vira diretiva
#  malformada e derruba o lint do arquivo inteiro — medido.)
#
# Este gate nao imprime um aviso: ele MEDE a config viva pela API e, quando a
# janela existe, exige um reconhecimento EXPLICITO do Owner. Um aviso impresso
# no meio de um V-block de varios minutos e um aviso que ninguem le.
#
# Por que nao curar no patch: a metade que decide e SERVER-SIDE (nao volta com
# `git revert`) e nao e um path; e documentar o conjunto novo em
# `docs/BRANCH-PROTECTION.md` sem flipar a config documentaria um estado que
# nao existe. As duas metades sao do Owner, e o lugar de exigi-las e aqui.
_rq_a="$(_expect EXPECTED_REQUIRED_CHECK_MATRIX_39)"
_rq_b="$(_expect EXPECTED_REQUIRED_CHECK_MATRIX_312)"
_rq_state="unreadable"
_rq_detail=""
if [ "$SELFTEST" = "1" ]; then
  _rq_state="selftest"
  _rq_detail="modo auto-teste: a API nao e consultada"
elif command -v gh >/dev/null 2>&1; then
  _rq_url="$(git remote get-url "$PUSH_REMOTE" 2>/dev/null || printf '')"
  case "$_rq_url" in
    *github.com[:/]*)
      _rq_slug="$(printf '%s' "$_rq_url" | sed -e 's#^.*github\.com[:/]##' -e 's#\.git$##')"
      # O codigo de saida vai numa variavel PROPRIA, e nao numa sentinela de
      # texto anexada ao stdout: MEDIDO nesta maquina contra a API viva — num
      # 404 o `gh` sai 1, escreve a mensagem humana no stderr E o CORPO JSON do
      # erro no stdout. A forma `_rq_out="$(gh ... || printf '__GH_FAILED__')"`
      # produziria `{"message":...}__GH_FAILED__`, a comparacao com a sentinela
      # falharia, e o gate classificaria um 404 como janela ABERTA — pedindo um
      # reconhecimento com uma explicacao falsa.
      _rq_rc=0
      _rq_out="$(gh api "repos/$_rq_slug/branches/$PUSH_BRANCH/protection/required_status_checks" \
                   --jq '.contexts // [] | .[]' 2>"$TMPDIR_LAND/gh-protection.err")" || _rq_rc=$?
      if [ "$_rq_rc" != "0" ]; then
        # Rail codex do land (r1, P1): um 404 GENERICO nao prova ausencia de
        # protecao. A API do GitHub responde 404 tanto para «este branch nao
        # tem protection» quanto para «este token nao pode LER a protection
        # deste repo» — e no segundo caso a protecao pode existir, a janela
        # estar ABERTA, e o push seguir funcionando por SSH. Casar `Not Found`
        # ou `"status": "404"` cru trataria autorizacao insuficiente como prova
        # de ausencia, exatamente o contrario do fail-closed declarado em
        # `s343-ceremony-w4a/DESIGN-W4A-S343.md:139-142`. So a mensagem
        # ESPECIFICA classifica; qualquer outro erro cai em `unreadable`, que e
        # fail-closed e exige o reconhecimento. MEDIDO nesta maquina contra a
        # API viva: um branch sem protecao devolve `Branch not protected` no
        # stderr E no corpo JSON do stdout — logo o ramo de hoje nao muda.
        if grep -q 'Branch not protected' \
             "$TMPDIR_LAND/gh-protection.err" 2>/dev/null \
           || printf '%s' "$_rq_out" | grep -q 'Branch not protected'; then
          _rq_state="unprotected"
          _rq_detail="a API respondeu «Branch not protected» para $_rq_slug@$PUSH_BRANCH"
        else
          # Inclui o CORPO do erro, e nao so o stderr: num 404 de autorizacao a
          # mensagem util («Not Found», «Resource not accessible...») vem no
          # JSON do stdout, e um detalhe vazio deixaria o Owner sem o motivo.
          _rq_state="unreadable"
          _rq_detail="rc=$_rq_rc; stderr: $(head -2 "$TMPDIR_LAND/gh-protection.err" 2>/dev/null | tr '\n' ' '); corpo: $(printf '%s' "$_rq_out" | head -c 200 | tr '\n' ' ')"
        fi
      elif [ -z "$_rq_out" ]; then
        # Protecao LIGADA e a lista de contexts VAZIA. Isso nao e a janela do
        # achado: sem nenhum check obrigatorio nao existe o «verde obrigatorio
        # enquanto a matriz esta vermelha» — nao ha verde obrigatorio nenhum.
        # Sem este ramo o estado cairia em `window` e o gate pediria um
        # reconhecimento com uma explicacao FALSA.
        _rq_state="unprotected"
        _rq_detail="ha branch protection, mas com ZERO required status checks"
      elif printf '%s\n' "$_rq_out" | grep -qxF "$_rq_a" \
           && printf '%s\n' "$_rq_out" | grep -qxF "$_rq_b"; then
        _rq_state="covered"
        _rq_detail="os dois legs da matriz JA sao required checks"
      else
        _rq_state="window"
        _rq_detail="contexts obrigatorios hoje: $(printf '%s' "$_rq_out" | tr '\n' '|')"
      fi ;;
    *) _rq_state="unreadable"; _rq_detail="o remote '$PUSH_REMOTE' nao aponta para github.com ($_rq_url)" ;;
  esac
else
  _rq_detail="gh ausente"
fi

case "$_rq_state" in
  covered)
    ok "G7: $_rq_detail — a janela NAO existe" ;;
  unprotected)
    warn "G7: NAO ha branch protection em $PUSH_BRANCH ($_rq_detail)."
    printf '        Sem required checks nenhum, nao existe o «verde obrigatorio\n'
    printf '        enquanto a matriz esta vermelha» — a janela do achado nao se\n'
    printf '        abre hoje. Ela ABRE no dia em que a protecao for ligada com a\n'
    printf '        configuracao do docs/BRANCH-PROTECTION.md:101-105.\n' ;;
  *)
    if [ "${CEO_W4A_REQUIRED_CHECK_ACK:-}" = "I-ACCEPT" ]; then
      warn "G7: janela de required-check RECONHECIDA pelo Owner (CEO_W4A_REQUIRED_CHECK_ACK=I-ACCEPT)"
      printf '        estado medido: %s — %s\n' "$_rq_state" "$_rq_detail"
    else
      die "G7: a janela de required-check esta ABERTA ou NAO E LEGIVEL (estado: $_rq_state).
  $_rq_detail
  (\`unreadable\` = o gate NAO conseguiu ler a protecao viva. Nao ler nao e o
   mesmo que nao existir: um 404 de AUTORIZACAO tem a mesma cara de um branch
   sem protecao, e por isso este ramo e fail-closed.)

  Depois desta delecao, as suites de hooks/scripts rodam SO em:
    $_rq_a
    $_rq_b
  e o UNICO required check documentado e
    validate / Governance, health, contamination, shellcheck
  Numa PR, uma matriz VERMELHA coexistiria com um required check VERDE.

  Duas saidas, as duas do Owner:
   (a) FECHAR a janela agora — ADICIONE os dois contexts aos required checks
       (Settings > Branches > main).
       Pela API, use o endpoint ADITIVO — o \`PATCH\` em
       .../protection/required_status_checks trata \`contexts\` como a
       configuracao INTEIRA e SUBSTITUI a lista: mandar so os dois novos
       APAGARIA o \`validate\` e todo o resto (achado P1 do rail do land):
         gh api -X POST \\
           repos/<owner>/<repo>/branches/$PUSH_BRANCH/protection/required_status_checks/contexts \\
           -f 'contexts[]=$_rq_a' -f 'contexts[]=$_rq_b'
       Confira antes e depois com:
         gh api repos/<owner>/<repo>/branches/$PUSH_BRANCH/protection/required_status_checks --jq '.contexts'
       e atualize docs/BRANCH-PROTECTION.md:101-105 na MESMA janela. Config
       server-side NAO volta com \`git revert\`.
   (b) ACEITAR a janela conscientemente e landar assim:
         CEO_W4A_REQUIRED_CHECK_ACK=I-ACCEPT bash $0
       Nota de escopo: o \`main\` deste repo recebe push direto por cerimonia,
       entao a janela e a rota de PR — nao a rota que este land usa."
    fi ;;
esac

# ---------------------------------------------------------------------------
# Impressao digital PRE-mutacao (arvore + index), tirada AGORA — depois de
# todos os gates e antes da primeira mutacao.
# ---------------------------------------------------------------------------
FP_BEFORE="$(_fingerprint)"

# ---------------------------------------------------------------------------
step "APLICANDO o patch assinado"
# ---------------------------------------------------------------------------
# Arma o override de kernel SO agora (menor escopo). O Scope assinado que o G5
# acabou de validar NOMEIA o validate.yml; o override e a segunda chave, nunca
# a primeira. Contrato do hook (check_arbitration_kernel.py: _REASON_RE +
# _ACK_TOKEN): reason e um SLUG [A-Za-z0-9._-]{1,120}; o ACK e o literal
# I-ACCEPT.
export CEO_KERNEL_OVERRIDE="PLAN-186-wave-s343-w4a-validate-step-deletion.sentinel-wave-s343-w4a-approved"
export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
RESTORE_ON_EXIT=1
git apply "$PATCH"
APPLIED=1
ok "patch aplicado ($(wc -l < "$TOUCHED_FILE" | tr -d ' ') paths)"

# ---------------------------------------------------------------------------
step "V1 — o que o patch toca PARSEIA, e o escopo por extensao e DECLARADO"
# ---------------------------------------------------------------------------
# Esta wave toca EXATAMENTE 0 scripts shell e 0 arquivos Python — as duas
# contagens sao GUARDA DE ESCOPO, nao decoracao: um `.sh` ou um `.py` neste
# patch e superficie que a revisao nao leu (e o ratchet installer-write-safety
# passaria a ser devido no mesmo patch). Quando a contagem for > 0, os loops
# abaixo rodam de verdade.
SH_COUNT=0
PY_COUNT=0
PY_LIST="$TMPDIR_LAND/pyfiles"
SH_LIST="$TMPDIR_LAND/shfiles"
: > "$PY_LIST"; : > "$SH_LIST"
while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ -f "$f" ] || continue
  case "$f" in
    *.sh) printf '%s\n' "$f" >> "$SH_LIST"; SH_COUNT=$(( SH_COUNT + 1 )) ;;
    *.py) printf '%s\n' "$f" >> "$PY_LIST"; PY_COUNT=$(( PY_COUNT + 1 )) ;;
    *)
      head_line="$(head -1 "$f" 2>/dev/null || printf '')"
      case "$head_line" in
        "#!"*sh*)     printf '%s\n' "$f" >> "$SH_LIST"; SH_COUNT=$(( SH_COUNT + 1 )) ;;
        "#!"*python*) printf '%s\n' "$f" >> "$PY_LIST"; PY_COUNT=$(( PY_COUNT + 1 )) ;;
      esac ;;
  esac
done < "$TOUCHED_FILE"
_sh_exp="$(_expect EXPECTED_PATCH_SH_FILES)"
[ "$SH_COUNT" -eq "$_sh_exp" ] || die "V1: $SH_COUNT script(s) shell no patch — esperava exatamente $_sh_exp shell.
  Mais e escopo novo (e o ratchet installer-write-safety passa a ser devido no
  MESMO patch); menos significa que um espelho da wave saiu do patch."
_py_exp="$(_expect EXPECTED_PATCH_PY_FILES)"
[ "$PY_COUNT" -eq "$_py_exp" ] || die "V1: $PY_COUNT arquivo(s) Python no patch — esperava exatamente $_py_exp.
  Mais significa escopo novo sem decisao; menos, sujeito da wave fora do patch."
while IFS= read -r f; do
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$f" || die "V1a: py_compile reprovou em $f"
done < "$PY_LIST"
while IFS= read -r f; do
  bash -n "$f" || die "V1b: bash -n reprovou em $f"
  shellcheck -S warning "$f" || die "V1b: shellcheck reprovou em $f"
done < "$SH_LIST"
ok "V1a/V1b: $PY_COUNT Python + $SH_COUNT shell no patch (esperado $_py_exp/$_sh_exp)"

# V1c — os DOIS workflows parseiam como YAML e a topologia de jobs e a
# DECLARADA. Um `.yml` que nao parseia derruba TODA a CI em silencio (o
# GitHub reporta "workflow file issue", nao um step vermelho).
python3 - "$_v_rel" "$_s_rel" "$(_expect EXPECTED_YAML_JOBS_VALIDATE)" \
                    "$(_expect EXPECTED_YAML_JOBS_SMOKE)" \
                    "$(_expect EXPECTED_VALIDATE_STEPS_POST)" \
                    "$(_expect EXPECTED_SMOKE_TIMEOUT_POST)" \
                    "$(_expect EXPECTED_MATRIX_JOB_NAME)" <<'PY' || die "V1c reprovou"
import sys, yaml
v_rel, s_rel, njobs_v, njobs_s, nsteps_v, smoke_to, matrix_job = sys.argv[1:8]
v = yaml.safe_load(open(v_rel, encoding="utf-8"))
s = yaml.safe_load(open(s_rel, encoding="utf-8"))
bad = []
if len(v["jobs"]) != int(njobs_v):
    bad.append("%s: %d jobs, esperado %s" % (v_rel, len(v["jobs"]), njobs_v))
if len(s["jobs"]) != int(njobs_s):
    bad.append("%s: %d jobs, esperado %s" % (s_rel, len(s["jobs"]), njobs_s))
n = len(v["jobs"]["validate"]["steps"])
if n != int(nsteps_v):
    bad.append("job validate: %d steps, esperado %s" % (n, nsteps_v))
to = s["jobs"]["smoke"].get("timeout-minutes")
if str(to) != str(smoke_to):
    bad.append("job smoke: timeout-minutes=%r, esperado %s" % (to, smoke_to))
if matrix_job not in v["jobs"]:
    bad.append("o job %s SUMIU — ele e o unico consumidor restante dos node-ids" % matrix_job)
else:
    mj = v["jobs"][matrix_job]
    runs = [st.get("run", "") for st in mj["steps"]]
    body = "\n".join(runs)
    if body.count("python3 -m pytest") != 2:
        bad.append("o job %s nao tem os DOIS passes de pytest (achei %d)"
                   % (matrix_job, body.count("python3 -m pytest")))
    for root in (".claude/hooks/tests/", ".claude/scripts/tests/",
                 ".claude/scripts/optimizer/tests/"):
        if root not in body:
            bad.append("o job %s nao roda a raiz %s" % (matrix_job, root))
if bad:
    sys.stderr.write("".join("    %s\n" % b for b in bad))
    sys.exit(1)
print("  %s: %d jobs / job validate %d steps; %s: %d job / smoke timeout %s"
      % (v_rel, len(v["jobs"]), n, s_rel, len(s["jobs"]), to))
PY
LINT_STATUS="YAML OK; job validate $(_expect EXPECTED_VALIDATE_STEPS_POST) steps; smoke timeout $(_expect EXPECTED_SMOKE_TIMEOUT_POST)"
ok "V1c: $LINT_STATUS"

# ---------------------------------------------------------------------------
step "V3 — REPRODUTIBILIDADE: HEAD + derivador versionado == arvore pos-patch"
# ---------------------------------------------------------------------------
# Um worktree limpo em HEAD (pre-patch) recebe o apply-w4a-validate-deletion.py;
# cada path tocado tem de sair byte-identico ao da arvore viva pos-patch. E a
# prova de que o patch assinado e a saida do script — e nada mais.
WT_REPRO="$( mktemp -d "${TMPDIR:-/tmp}/s343-land-repro.XXXXXX" )/wt"
git worktree add --detach --quiet "$WT_REPRO" "$HEAD_SHA" \
  || die "V3: git worktree add (reproducao) falhou"
python3 "$APPLY" --root "$WT_REPRO" >/dev/null \
  || die "V3: o derivador RECUSOU sobre HEAD limpo — ancora ausente/ambigua ou HEAD ja patchado"
_repro_bad=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if ! cmp -s "$WT_REPRO/$f" "$f"; then _repro_bad="$_repro_bad  $f
"; fi
done < "$TOUCHED_FILE"
[ -z "$_repro_bad" ] || die "V3: a arvore pos-patch NAO e a saida do derivador (byte a byte) em:
$_repro_bad  O patch assinado carrega algo que o apply-w4a-validate-deletion.py nao produz."
ok "V3: HEAD + apply-w4a-validate-deletion.py == pos-patch, byte a byte, nos $(wc -l < "$TOUCHED_FILE" | tr -d ' ') paths"

# ---------------------------------------------------------------------------
step "V4 — o lint de workflow, com os flags EXATOS do step da CI"
# ---------------------------------------------------------------------------
# O step `actionlint` do validate.yml roda com estes flags; usar outros aqui
# mediria outro lint. Nota honesta: a CI baixa o binario 1.7.7 PINADO por
# sha256, e este gate usa o actionlint instalado nesta maquina — o gate e uma
# ANTECIPACAO do step da CI, nao um substituto dele.
AL_LOG="$TMPDIR_LAND/actionlint.log"
AL_RC=0
# shellcheck disable=SC2046,SC2086  # os flags vem da base declarada, sem espacos internos
actionlint -shellcheck="$(_expect EXPECTED_ACTIONLINT_FLAGS)" .github/workflows/*.yml \
  > "$AL_LOG" 2>&1 || AL_RC=$?
[ "$AL_RC" = "$(_expect EXPECTED_ACTIONLINT_RC)" ] \
  || { tail -20 "$AL_LOG" | sed 's/^/    /' >&2
       die "V4a: actionlint saiu rc=$AL_RC, esperado $(_expect EXPECTED_ACTIONLINT_RC) — log em $AL_LOG"; }
ok "V4a: actionlint verde sobre .github/workflows/*.yml (rc=$AL_RC, actionlint $(actionlint -version 2>/dev/null | head -1))"

ASD_RC=0
python3 .claude/scripts/check-action-sha-drift.py --offline >/dev/null 2>&1 || ASD_RC=$?
[ "$ASD_RC" = "$(_expect EXPECTED_ACTION_SHA_DRIFT_RC)" ] \
  || die "V4b: check-action-sha-drift --offline saiu rc=$ASD_RC, esperado $(_expect EXPECTED_ACTION_SHA_DRIFT_RC)"
ok "V4b: pins de action sem drift de formato"

# ---------------------------------------------------------------------------
step "V5 — COBERTURA: a uniao dos dois steps deletados == a matriz, por CONJUNTO"
# ---------------------------------------------------------------------------
# Este e o braco do AC-16 que AUTORIZA a delecao, e ele e RE-DERIVADO aqui,
# agora, sobre esta arvore — nunca citado do relatorio da S341 (a suite cresceu
# desde entao e os numeros de la ja nao descrevem esta arvore).
#
# A comparacao e por CONJUNTO de node-ids (sha256 da lista ordenada), NAO por
# contagem: dois conjuntos diferentes podem ter o mesmo tamanho, e um gate que
# so soma aceitaria uma troca 1-por-1 em silencio. As contagens DECLARADAS sao
# a segunda perna — elas pegam o caso em que os dois lados encolhem juntos.
#
# Roda dentro do worktree do V3 (arvore pos-derivador): as raizes de teste nao
# sao tocadas pelo patch, e coletar la mantem a coleta fora do estado da
# arvore viva (licao S326 — `--collect-only` ja escreveu na cadeia viva uma
# vez; a cura landou, e nao depender dela custa zero).
COV_LOG="$TMPDIR_LAND/coverage.log"
COV_RC=0
( cd "$WT_REPRO" && PYTHONDONTWRITEBYTECODE=1 python3 - \
    "$(_expect EXPECTED_NODEID_HOOKS)" "$(_expect EXPECTED_NODEID_SCRIPTS)" \
    "$(_expect EXPECTED_NODEID_MATRIX)" "$(_expect EXPECTED_NODEID_OVERLAP)" \
    "$(_expect EXPECTED_NODEID_SERIAL_HOOKS)" "$(_expect EXPECTED_NODEID_SERIAL_SCRIPTS)" \
    "$(_expect EXPECTED_NODEID_SERIAL_MATRIX)" <<'PY' ) > "$COV_LOG" 2>&1 || COV_RC=$?
import hashlib, subprocess, sys

exp = [int(x) for x in sys.argv[1:8]]
HOOKS = [".claude/hooks/tests/"]
SCRIPTS = [".claude/scripts/tests/", ".claude/scripts/optimizer/tests/"]


def collect(roots, marker):
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q",
           "-p", "no:cacheprovider"] + list(roots)
    if marker:
        cmd += ["-m", marker]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-3000:] + proc.stderr[-3000:])
        raise SystemExit("collect-only FALHOU para %s (marker=%r)" % (roots, marker))
    ids = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if "::" in line and " " not in line.split("::")[0]:
            ids.add(line)
    if not ids:
        raise SystemExit("collect-only devolveu ZERO node-ids para %s — gate vacuo" % roots)
    return ids


def sha(s):
    return hashlib.sha256("\n".join(sorted(s)).encode("utf-8")).hexdigest()


bad = []
for label, marker, (ea, eb, em, eo) in (
        ("todos", None, (exp[0], exp[1], exp[2], exp[3])),
        ("serial", "serial", (exp[4], exp[5], exp[6], exp[3]))):
    A = collect(HOOKS, marker)
    B = collect(SCRIPTS, marker)
    M = collect(HOOKS + SCRIPTS, marker)
    U = A | B
    inter = A & B
    print("  [%s] |A|=%d |B|=%d |A&B|=%d |AuB|=%d |matriz|=%d"
          % (label, len(A), len(B), len(inter), len(U), len(M)))
    print("        sha(AuB)=%s" % sha(U)[:16])
    print("        sha(M)  =%s" % sha(M)[:16])
    if U != M:
        bad.append("[%s] a UNIAO dos dois steps NAO e a matriz: so na uniao=%d, so na matriz=%d"
                   % (label, len(U - M), len(M - U)))
    if len(inter) != eo:
        bad.append("[%s] |A&B|=%d, esperado %d" % (label, len(inter), eo))
    for got, want, what in ((len(A), ea, "|A| hooks"), (len(B), eb, "|B| scripts+optimizer"),
                            (len(M), em, "|matriz|")):
        if got != want:
            bad.append("[%s] %s = %d, DECLARADO %d — a suite mudou de tamanho; "
                       "atualize o EXPECTED-BASELINE.txt CONSCIENTEMENTE, com a "
                       "propriedade re-verificada, nunca relaxando o numero"
                       % (label, what, got, want))
if bad:
    sys.stderr.write("".join("    %s\n" % b for b in bad))
    raise SystemExit(1)
print("  a delecao NAO e recusada por cobertura")
PY
[ "$COV_RC" = "0" ] || { cat "$COV_LOG" | sed 's/^/    /' >&2
                         die "V5: a re-derivacao de cobertura reprovou (rc=$COV_RC) — log em $COV_LOG"; }
sed 's/^/  /' "$COV_LOG"
COVERAGE_STATUS="uniao == matriz nos 2 recortes (todos + serial), por conjunto"
ok "V5: $COVERAGE_STATUS"

# ---------------------------------------------------------------------------
step "V6 — NAO-VACUO pos-patch: o que sai, saiu; o que fica, ficou"
# ---------------------------------------------------------------------------
_refs_exp="$(_expect EXPECTED_DELETED_STEP_REFS_POST)"
_post_a="$( { grep -c -F -- "- name: $_step_a" "$_v_rel" || true; } )"
_post_b="$( { grep -c -F -- "- name: $_step_b" "$_v_rel" || true; } )"
{ [ "$_post_a" = "$_refs_exp" ] && [ "$_post_b" = "$_refs_exp" ]; } \
  || die "V6a: pos-patch o step A aparece $_post_a vez(es) e o B $_post_b — esperado $_refs_exp nos dois"
_post_adapter="$( { grep -c -F -- "CEO_HOOK_ADAPTER: claude" "$_v_rel" || true; } )"
[ "$_post_adapter" = "0" ] \
  || die "V6a: 'CEO_HOOK_ADAPTER: claude' ainda aparece $_post_adapter vez(es) em $_v_rel —
  a perna do delta de ambiente que a wave DECLARA como perda aceita nao pode
  reaparecer como setting."
_post_126="$( { grep -c -F -- "timeout-minutes: $(_expect EXPECTED_SMOKE_TIMEOUT_HEAD)" "$_s_rel" || true; } )"
_post_150="$( { grep -c -F -- "timeout-minutes: $(_expect EXPECTED_SMOKE_TIMEOUT_POST)" "$_s_rel" || true; } )"
{ [ "$_post_126" = "0" ] && [ "$_post_150" = "1" ]; } \
  || die "V6b: em $_s_rel o timeout velho aparece $_post_126 vez(es) e o novo $_post_150 — esperado 0 e 1"
# O ledger da derivacao aditiva NAO pode ter sido apagado junto com o numero:
# a wave REESCREVE a conclusao e PRESERVA a historia.
for _marker in "PLAN-185 W1+W2 (AC-3): 68 -> 83" "PLAN-169 W-E (S329, rail rounds 1-3): 83 -> 126"; do
  grep -qF -- "$_marker" "$_s_rel" \
    || die "V6b: o ledger da derivacao aditiva perdeu a linha '$_marker'.
  Esta wave acrescenta uma base MEDIDA; ela nao apaga como se chegou a 126."
done
grep -qF -- "PLAN-186 W4a (S343): 126 -> 150" "$_s_rel" \
  || die "V6b: o bloco novo de derivacao MEDIDA nao esta em $_s_rel — trocar so o numero
  deixa o arquivo se contradizendo (feedback-reconcile-the-conclusions-not-just-the-table)."
# V6c — o CENSO da classe que o rail codex r2 achou. O E1 reconciliou UM
# comentario; o arquivo tinha SETE apontando para os steps deletados. Um
# arquivo que se contradiz e a classe
# `feedback-reconcile-the-conclusions-not-just-the-table`, e a cura de uma
# ocorrencia nao fecha a classe — «rail acha a CLASSE, censo MECANICO a
# fecha». Os literais abaixo sao o censo FECHADO: cada um tem de dar ZERO.
_v6c_bad=""
while IFS= read -r _lit; do
  [ -z "$_lit" ] && continue
  _n="$( { grep -c -F -- "$_lit" "$_v_rel" || true; } )"
  [ "$_n" = "0" ] || _v6c_bad="$_v6c_bad  ($_n×) $_lit
"
done <<'V6CLITERALS'
ALREADY collected by "Run Python script unit tests" below
step below runs the whole
is dir-collected above
`serial` split above
directory pins in the pytest steps
Step: Python hook unit tests
V6CLITERALS
[ -z "$_v6c_bad" ] || die "V6c: $_v_rel ainda tem comentario(s) apontando para os steps deletados:
$_v6c_bad  A delecao tem de reconciliar TODOS os sitios, nao um."
# E o contrapositivo: cada sitio reconciliado NOMEIA o job que virou o dono da
# cobertura. Um censo que so conta AUSENCIA passaria com os comentarios
# APAGADOS em vez de reescritos.
_v6c_named="$( { grep -c -F -- "$(_expect EXPECTED_MATRIX_JOB_NAME)" "$_v_rel" || true; } )"
_v6c_exp="$(_expect EXPECTED_MATRIX_JOB_MENTIONS)"
[ "$_v6c_named" = "$_v6c_exp" ] || die "V6c: $_v6c_named mencao(oes) a $(_expect EXPECTED_MATRIX_JOB_NAME) em $_v_rel, esperado $_v6c_exp
  (1 definicao do job + 7 comentarios reconciliados). Menos significa comentario
  APAGADO em vez de reescrito; mais, escopo que a revisao nao leu."
ok "V6: 2 steps fora, adapter fora, timeout $(_expect EXPECTED_SMOKE_TIMEOUT_POST) com ledger preservado, comentario reconciliado"

# O corte do dry-run. Ele fica AQUI, depois dos gates que operam sobre a
# arvore JA PATCHADA (V1, V3, V4, V5, V6) e antes dos de corpus. O trap
# restaura arvore e index.
if [ "$DRY_RUN" = "1" ]; then
  printf '\n\033[33mDRY-RUN\033[0m — G-PRE, G0..G6 verdes; patch aplicado; V1, V3, V4, V5 e V6 executados.\n'
  printf '  O V-block de CORPUS (V2 suite, V8 contagens, V9 governanca) NAO roda em dry-run.\n'
  printf '  Restaurando arvore e index...\n'
  exit 0
fi

# ---------------------------------------------------------------------------
step "V2 — a suite que LE os dois workflows vivos"
# ---------------------------------------------------------------------------
# Conjunto DERIVADO por grep sobre os testpaths, nao lembrado. Hoje nenhum
# desses testes parseia os STEPS — o conjunto e pequeno de proposito e existe
# para que, no dia em que um deles passar a parsear, o vermelho apareca AQUI.
UNIT_LOG="$TMPDIR_LAND/unit.log"
UNIT_RC=0
# shellcheck disable=SC2086  # $UNIT_TESTS e uma lista controlada, sem espacos
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest $UNIT_TESTS -q -p no:cacheprovider \
  > "$UNIT_LOG" 2>&1 || UNIT_RC=$?
[ "$UNIT_RC" -eq 0 ] || { tail -30 "$UNIT_LOG" | sed 's/^/    /' >&2
                          die "V2: a suite reprovou (rc=$UNIT_RC) — log em $UNIT_LOG"; }
_unit_obs="$( { grep -oE '(^|[^0-9])[0-9]+ passed' "$UNIT_LOG" || true; } \
              | head -1 | { grep -oE '[0-9]+' || true; } )"
[ -n "$_unit_obs" ] || die "V2: nao consegui ler 'N passed' — log em $UNIT_LOG"
# NAO ha um `EXPECTED_UNIT_PYTEST_PASSED` aqui, e a ausencia e uma decisao,
# nao um esquecimento: estes 6 arquivos crescem por trabalho ALHEIO a esta
# wave, entao um numero congelado abortaria o land por um teste que alguem
# adicionou de madrugada — um gate que reprova pelo motivo errado. O que um
# numero pegaria e um arquivo que parou de coletar em silencio ("N deselected"
# nao e "N passed"), e ISSO e checado por conjunto abaixo: cada um dos 6
# arquivos tem de contribuir com pelo menos um node-id.
_uf_exp="$(_expect EXPECTED_UNIT_TEST_FILES)"
_uf_obs=0
for _uf in $UNIT_TESTS; do
  _uf_n="$( PYTHONDONTWRITEBYTECODE=1 python3 -m pytest "$_uf" --collect-only -q \
              -p no:cacheprovider 2>/dev/null | { grep -c '::' || true; } )"
  [ "$_uf_n" -gt 0 ] || die "V2: $_uf coletou ZERO node-ids — o arquivo parou de contribuir
  para a suite em silencio, e um gate que so le 'N passed' aceitaria isso."
  _uf_obs=$(( _uf_obs + 1 ))
done
[ "$_uf_obs" = "$_uf_exp" ] \
  || die "V2: $_uf_obs arquivo(s) na suite alvo, esperado $_uf_exp — o conjunto e
  DERIVADO por grep sobre os testpaths; re-derive-o e atualize a base."
UNIT_STATUS="$_unit_obs teste(s) verdes em $_uf_obs arquivo(s) que leem os workflows"
ok "V2: $UNIT_STATUS"

# ---------------------------------------------------------------------------
step "V8 — os gates de contagem do corpus"
# ---------------------------------------------------------------------------
CLAIMS_RC=0
python3 .claude/scripts/check-claude-md-claims.py >/dev/null 2>&1 || CLAIMS_RC=$?
[ "$CLAIMS_RC" = "$(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)" ] \
  || die "V8a: check-claude-md-claims saiu rc=$CLAIMS_RC, esperado $(_expect EXPECTED_CLAUDE_MD_CLAIMS_RC)"
ok "V8a: check-claude-md-claims verde"

VC_LOG="$TMPDIR_LAND/verify-counts.log"
VC_RC=0
bash .claude/scripts/local/verify-counts.sh > "$VC_LOG" 2>&1 || VC_RC=$?
[ "$VC_RC" = "$(_expect EXPECTED_VERIFY_COUNTS_RC)" ] \
  || { grep -E 'DRIFT|Exit' "$VC_LOG" | head -20 | sed 's/^/    /' >&2
       die "V8b: verify-counts.sh saiu rc=$VC_RC, esperado $(_expect EXPECTED_VERIFY_COUNTS_RC) — log em $VC_LOG"; }
ok "V8b: verify-counts.sh verde (rc=$VC_RC)"

CONTAM_RC=0
python3 .claude/scripts/check_contamination.py >/dev/null 2>&1 || CONTAM_RC=$?
[ "$CONTAM_RC" = "$(_expect EXPECTED_CONTAMINATION_RC)" ] \
  || die "V8c: check_contamination saiu rc=$CONTAM_RC, esperado $(_expect EXPECTED_CONTAMINATION_RC)"
ok "V8c: sem contaminacao fora das zonas permitidas"

# ---------------------------------------------------------------------------
step "V9 — gates de governanca do repositorio"
# ---------------------------------------------------------------------------
CLINT_JSON="$TMPDIR_LAND/ceremony-lint.json"
python3 .claude/scripts/check-ceremony-script.py --json > "$CLINT_JSON" 2>&1 \
  || die "V9a: check-ceremony-script.py saiu diferente de 0 — saida em $CLINT_JSON"
_clint_obs="$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
v=d['blocking_unwaived']
print(len(v) if isinstance(v,list) else v)
" "$CLINT_JSON")"
_clint_exp="$(_expect EXPECTED_CEREMONY_LINT_BLOCKING)"
[ "$_clint_obs" = "$_clint_exp" ] \
  || die "V9a: check-ceremony-script.py com $_clint_obs blocking, esperado $_clint_exp — saida em $CLINT_JSON"
ok "V9a: ceremony-lint blocking=$_clint_obs (esperado $_clint_exp)"

# A governanca roda COMPLETA (sem --fast): o modo completo checa o limite de
# 40k bytes do CLAUDE.md que o --fast pula (licao W5). rc 0 nao e a resposta
# inteira: o script reporta "Errors: N" e a base declara o N esperado.
GOV_LOG="$TMPDIR_LAND/validate-governance.log"
bash "$VALIDATE_SH" > "$GOV_LOG" 2>&1 \
  || { tail -20 "$GOV_LOG" | sed 's/^/    /' >&2
       die "V9b: validate-governance.sh FALHOU — log em $GOV_LOG"; }
_gov_obs="$( { grep -oiE '^[[:space:]]*errors:[[:space:]]+[0-9]+' "$GOV_LOG" || true; } \
             | { grep -oE '[0-9]+' || true; } | head -1 )"
[ -n "$_gov_obs" ] || die "V9b: nao consegui ler a contagem de erros em $GOV_LOG —
  o relatorio mudou de forma. Um gate que nao acha o proprio sujeito nao passa."
[ "$_gov_obs" = "$(_expect EXPECTED_GOVERNANCE_ERRORS)" ] \
  || die "V9b: validate-governance reporta $_gov_obs erro(s), esperado
  $(_expect EXPECTED_GOVERNANCE_ERRORS) — log em $GOV_LOG"
ok "V9b: validate-governance.sh completo verde ($_gov_obs erro(s))"

CSHM_RC=0
python3 .claude/scripts/gen-command-skill-hook-map.py --check >/dev/null 2>&1 || CSHM_RC=$?
[ "$CSHM_RC" = "$(_expect EXPECTED_CSHM_CHECK_RC)" ] \
  || die "V9c: gen-command-skill-hook-map.py --check saiu rc=$CSHM_RC, esperado $(_expect EXPECTED_CSHM_CHECK_RC).
  Regenere (sem --check) e inclua o doc no patch — foi assim que o land do
  pacote D deixou o main vermelho na S329."
ok "V9c: COMMAND-SKILL-HOOK-MAP.md sem drift"

TEH_RC=0
python3 .claude/scripts/check-test-env-hygiene.py >/dev/null 2>&1 || TEH_RC=$?
[ "$TEH_RC" = "$(_expect EXPECTED_TEST_ENV_HYGIENE_RC)" ] \
  || die "V9d: check-test-env-hygiene.py saiu rc=$TEH_RC, esperado $(_expect EXPECTED_TEST_ENV_HYGIENE_RC)"
ok "V9d: check-test-env-hygiene.py verde"

# Os manifestos GERADOS do plugin (.claude-plugin/) sao um gate do Validate.
# Esta wave nao deveria toca-los, e o gate custa segundos: um manifesto que
# derivasse dos workflows ficaria vermelho AQUI e nao na CI do dia seguinte.
BP_RC=0
python3 scripts/build-plugin.py --check >/dev/null 2>&1 || BP_RC=$?
[ "$BP_RC" = "$(_expect EXPECTED_BUILD_PLUGIN_CHECK_RC)" ] \
  || die "V9e: build-plugin.py --check saiu rc=$BP_RC, esperado $(_expect EXPECTED_BUILD_PLUGIN_CHECK_RC) — regenere os manifestos (scripts/build-plugin.py --write-manifests) e inclua-os no patch"
ok "V9e: manifestos do plugin sem drift"

# ---------------------------------------------------------------------------
step "S — staging explicito (nunca 'git add -u')"
# ---------------------------------------------------------------------------
# `git add -u` sozinho NUNCA inclui a assinatura: o `.asc` nasce UNTRACKED no
# SIGN, e um commit canonico sem ele sobe sem a evidencia que a governanca
# exige. E `-u` tambem arrastaria um path rastreado sujo tolerado no G0.
# Stage EXATAMENTE: paths do patch + sentinel + .asc, com prova por `cmp`.
{ cat "$TOUCHED_FILE"; printf '%s\n' "$SENTINEL" "$SENTINEL.asc"; } | sort -u > "$EXPECTED_FILE"
STAGED_BY_LAND=1   # rail r4: ANTES do loop — um add parcial ja autoriza o des-stage
while IFS= read -r f; do
  [ -z "$f" ] && continue
  git add -- "$f"
done < "$EXPECTED_FILE"
git diff --cached --name-only | sort -u > "$STAGED_FILE"
git diff --cached --name-only | sed 's/^/    staged: /'
if ! cmp -s "$EXPECTED_FILE" "$STAGED_FILE"; then
  die "conjunto staged != patch + sentinel:
  so no esperado: $(comm -23 "$EXPECTED_FILE" "$STAGED_FILE" | tr '\n' ' ')
  so no staged  : $(comm -13 "$EXPECTED_FILE" "$STAGED_FILE" | tr '\n' ' ')
  (um path do patch identico ao HEAD nao aparece no staged — isso tambem e erro:
   o patch nao deveria toca-lo)"
fi
grep -qx "$SENTINEL.asc" "$STAGED_FILE" || die "a assinatura $SENTINEL.asc NAO ficou staged"
ok "$(wc -l < "$STAGED_FILE" | tr -d ' ') path(s) staged == patch + sentinel + .asc"

# Nenhum path do patch entrou no index com o bit de execucao ligado por
# acidente (CLAUDE.md par. 4: o `--chmod=-x` sozinho nao gruda).
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    *.py|*.sh) continue ;;
  esac
  _mode="$(git ls-files --stage -- "$f" | awk '{print $1}')"
  [ -n "$_mode" ] || continue
  case "$_mode" in
    100755) die "o modo de $f no index e 100755 (executavel).
  Este path nao e um script. Corrija nos DOIS lados — o filesystem E o index:
    chmod -x $f && git update-index --chmod=-x -- $f" ;;
  esac
done < "$STAGED_FILE"
ok "nenhum arquivo nao-script staged como executavel"

# ---------------------------------------------------------------------------
step "C — commit (sem editor) e push"
# ---------------------------------------------------------------------------
# O Owner NAO e usuario de terminal: um `git commit` cru abre o vim e o prende
# la (S326). O commit sai daqui, com -F e --no-edit; nada abre editor.
case "$(cat "$COMMIT_MSG")" in
  *"Pair-Rail-Reviewed: TO-FILL"*)
    die "a mensagem de commit ainda tem o trailer Pair-Rail-Reviewed por preencher:
  $COMMIT_MSG
  O CEO preenche depois da ultima rodada do rail." ;;
esac

if ! git commit -F "$COMMIT_MSG" --no-edit; then
  die "o commit falhou (hook de pre-commit? veja a saida acima).
  O STAGING esta intacto — nada se perdeu. Chame o CEO.
  Se algum editor abriu: aperte Esc, digite  :q!  e Enter."
fi
NEW_SHA="$(git rev-parse HEAD)"
ok "commit criado: $NEW_SHA"
RESTORE_ON_EXIT=0   # o patch vive no commit a partir daqui
# Desarma o override de kernel AGORA (rail r2 P1-c): o menor escopo termina no
# commit — o push e os comandos seguintes rodam sem a chave no ambiente.
unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK 2>/dev/null || true
git --no-pager log -1 --format='    %h %s' | sed 's/^/  /'

if [ "$SELFTEST" = "1" ]; then
  warn "AUTO-TESTE: push PULADO"
else
  step "PUSH — e esta e a corrida 1/3 da medicao"
  if ! git push "$PUSH_REMOTE" "HEAD:$PUSH_BRANCH"; then
    die "o push falhou. O commit $NEW_SHA esta LOCAL e intacto.
  Tente de novo:  git -C $ROOT push $PUSH_REMOTE HEAD:$PUSH_BRANCH"
  fi
  ok "empurrado para $PUSH_REMOTE/$PUSH_BRANCH"
fi

step "LAND OK"
cat <<EOF

  commit : $NEW_SHA
  paths  : $(wc -l < "$STAGED_FILE" | tr -d ' ')
  V1 forma      : $LINT_STATUS
  V5 cobertura  : $COVERAGE_STATUS
  V2 suite      : $UNIT_STATUS

  PROXIMO COMANDO — a medicao (ele espera cada run terminar; leva ~1h):

    bash $ROOT/$MEASURE_SCRIPT

  Ultimos runs de CI:
EOF
if command -v gh >/dev/null 2>&1 && [ "$SELFTEST" = "0" ]; then
  gh run list --limit 3 2>&1 | sed 's/^/    /' || printf '    (gh run list indisponivel)\n'
else
  printf '    (gh ausente — acompanhe em https://github.com/Canhada-Labs/ceo-orchestration/actions)\n'
fi
cat <<'EOF'

  LEMBRETE — o que observar depois deste land:
  1. O job `validate` perdeu 2 steps. A COBERTURA nao mudou: quem roda aqueles
     node-ids agora e `hook-tests-python-matrix`, em 3.9 E 3.12. Se um teste
     ficar vermelho la, a atribuicao e por PERNA DE PYTHON, nao por step.
  2. O delta de ambiente e DUPLO e ACEITO: `PYTHONPATH: "."` passa a estar
     SEMPRE presente (antes a suite rodava com e sem) e `CEO_HOOK_ADAPTER`
     passa a estar SEMPRE ausente (caminho default do adapter). Um vermelho
     novo em hooks/tests que NAO reproduza localmente e o primeiro lugar onde
     olhar.
  3. O `Smoke Install` agora tem 150 min de teto. O ledger da derivacao
     aditiva continua no arquivo, acima do bloco novo.
  4. O AC-16 so fecha quando o MEASURE escrever
     .claude/plans/PLAN-186/w4/validate-deletion-RESULT.md — ate la ele e ◐.

  Se algum editor abrir em QUALQUER momento:
    aperte Esc, digite  :q!  e Enter  (sai sem salvar; nada se perde).
EOF
