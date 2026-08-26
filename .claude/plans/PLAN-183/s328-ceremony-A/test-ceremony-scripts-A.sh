#!/usr/bin/env bash
# test-ceremony-scripts-A.sh — auto-teste dos scripts de cerimônia do PACOTE A.
# CEREMONY-LINT: handwritten-exception: harness de teste da propria cerimonia
# (le e executa SIGN/LAND/finalize num clone descartavel; nao assina nem
# empurra nada). Nao ha gerador para harness de cerimonia.
#
# TUDO roda num CLONE DESCARTAVEL sob o scratchpad. A arvore viva nunca e
# tocada — e o clone tem o remote `origin` REMOVIDO na primeira linha util,
# porque `git clone --local` aponta origin para o repo vivo e um push
# acidental subiria daqui.
#
# O que este harness prova (cada asserção nomeia o defeito que ela reproduz):
#   T1  finalize_patch --self-test (controle positivo do `git add -N`)
#   T2  arquivo NOVO da sombra chega ao patch E ao Scope derivado
#   T3  SIGN preenche Anchor/Data/Approved-By e o LAND --dry-run passa G0..G5
#   T4  --dry-run deixa arvore E index byte-identicos (armadilha S272)
#   T5  G4 pega path tocado FORA do Scope (bullet removido do sentinel)
#   T6  G4 pega Scope que autoriza path que o patch NAO toca
#   T7  G5 nao e decorativo: `Plans:` DEPOIS de `Scope:` trunca a lista para o
#       parser do hook, o G4 (awk) nao ve, o G5 ve
#   T8  --ownership-e2e ausente ABORTA (parametro sem default)
#   T9  EXPECTED-BASELINE.txt ausente ABORTA
#   T10 CEREMONY_SELFTEST_NO_GPG=1 e RECUSADO fora do scratchpad
#   T11 V3  compara o FAIL= do oraculo unitario contra o valor DECLARADO
#   T12 V4  compara o CONJUNTO known-open contra o DECLARADO, NOS DOIS
#       SENTIDOS (id novo = regressao; id ausente = a verdade mudou) e o rc
#   T13 V5  compara as 5 contagens fatais da paridade contra as DECLARADAS,
#       e reprova quando o bloco de contagens nem aparece no log
#   T14 finalize-A.sh: no-op quando ja esta no HEAD; RECUSA quando o sentinel
#       ja esta assinado; re-base real quando o HEAD andou
#   T15 BASE-SHA.txt discordando do Patch-base ABORTA no SIGN
#   T16 o guard do trailer Pair-Rail-Reviewed, nos dois sentidos
#
# LIMITE DECLARADO: T11-T13 exercitam os COMPARADORES do V-block extraidos por
# ANCORA DE CONTEUDO do proprio LAND, com logs sinteticos. Eles NAO rodam as
# suites por tras (paridade, baseline-manifest, oraculo unitario) — essas rodam
# de verdade na bateria da noite e de novo no LAND. O que se prova aqui e a
# unica coisa que o LAND poderia errar sozinho: comparar contra o conjunto
# errado, ou contra zero.
#
# Uso:  bash .claude/plans/PLAN-183/s328-ceremony-A/test-ceremony-scripts-A.sh
set -uo pipefail   # NAO -e: as falhas sao CLASSIFICADAS, nao fatais.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
LIVE="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
# O SIGN/LAND recusam CEREMONY_SELFTEST_NO_GPG=1 fora de
# /private/tmp/claude-501/*/scratchpad/*, entao o clone TEM de nascer la.
# `mkdir -p` cria a cadeia inteira mesmo numa sessao com outro UUID.
SCRATCH="${CEREMONY_SELFTEST_SCRATCH:-/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/a78dbd00-249c-447b-b606-677f5fd39e46/scratchpad/ceremony-selftest-s328A}"
case "$SCRATCH" in
  /private/tmp/claude-501/*/scratchpad/*) : ;;
  *) printf 'ABORT: SCRATCH fora do padrao aceito pelo SIGN/LAND: %s\n' "$SCRATCH" >&2; exit 2 ;;
esac

PLAN_DIR=".claude/plans/PLAN-183"
CEREMONY_DIR="$PLAN_DIR/s328-ceremony-A"
SENTINEL="$PLAN_DIR/wave-s328-A-approved.md"
PATCH_REL="$CEREMONY_DIR/A.patch"
LAND_REL="$PLAN_DIR/OWNER-S328-A-LAND.sh"
SIGN_REL="$PLAN_DIR/OWNER-S328-A-SIGN.sh"
LIVE_LAND="$LIVE/$LAND_REL"

PASS=0; FAIL=0
_pass() { PASS=$(( PASS + 1 )); printf '  \033[32mPASS\033[0m %s\n' "$*"; }
_fail() { FAIL=$(( FAIL + 1 )); printf '  \033[31mFAIL\033[0m %s\n' "$*"; }
_head() { printf '\n\033[1m%s\033[0m\n' "$*"; }
# Escrita atraves de SYMLINK e a classe do PLAN-185: `cp` segue o link e grava
# FORA do destino pretendido. Todo `cp` deste harness passa por aqui.
_safe_cp() {
  if [ -L "$2" ]; then
    _fail "destino e SYMLINK, recusado: $2"
    return 1
  fi
  cp "$1" "$2"
}

# --------------------------------------------------------------------------
_head "0 — clone descartavel"
# --------------------------------------------------------------------------
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
REPO="$SCRATCH/repo"
SHADOW="$SCRATCH/shadow"
git clone --quiet --local "$LIVE" "$REPO" || { echo "clone falhou"; exit 2; }
git -C "$REPO" remote remove origin        # NUNCA empurrar para o repo vivo
git -C "$REPO" config user.email "selftest@example.invalid"
git -C "$REPO" config user.name "ceremony selftest"
printf '  clone: %s (origin removido)\n' "$REPO"

# Os materiais do pacote A ainda sao UNTRACKED na arvore viva; o clone nao os
# traz. Copia + commit no clone para reproduzir o estado "materiais commitados".
mkdir -p "$REPO/$CEREMONY_DIR"
for f in "$SIGN_REL" "$LAND_REL" "$SENTINEL" \
         "$CEREMONY_DIR/PROPOSED-PATCH.md" "$CEREMONY_DIR/COMMIT-MSG-A.txt" \
         "$CEREMONY_DIR/EXPECTED-BASELINE.txt" "$CEREMONY_DIR/BASE-SHA.txt" \
         "$CEREMONY_DIR/finalize-A.sh" "$CEREMONY_DIR/README-A.md" \
         "$CEREMONY_DIR/test-ceremony-scripts-A.sh" ; do
  _safe_cp "$LIVE/$f" "$REPO/$f"
done
# `finalize_patch.py` NAO e copiado: ele vive em w5-ceremony/ e ja e rastreado,
# entao o clone o traz. Copia-lo criaria um segundo original divergente.

# --------------------------------------------------------------------------
_head "T1 — finalize_patch --self-test (controle positivo do git add -N)"
# --------------------------------------------------------------------------
T1_OUT="$(python3 "$REPO/$PLAN_DIR/w5-ceremony/finalize_patch.py" --self-test 2>&1)"
T1_RC=$?
printf '%s\n' "$T1_OUT" | sed 's/^/    /'
if [ "$T1_RC" -eq 0 ]; then _pass "finalize_patch --self-test verde"
else _fail "finalize_patch --self-test rc=$T1_RC"; fi

# --------------------------------------------------------------------------
_head "T2 — sombra: 1 canonico modificado + 1 arquivo NOVO"
# --------------------------------------------------------------------------
git clone --quiet --local "$REPO" "$SHADOW"
SHADOW_BASE="$(git -C "$SHADOW" rev-parse HEAD)"
CANON_TARGET=".claude/hooks/_lib/runtime_paths.py"
NEW_TARGET="$CEREMONY_DIR/selftest-new.sh"
mkdir -p "$SHADOW/$CEREMONY_DIR"
printf '\n# selftest marker (nao e conteudo real)\n' >> "$SHADOW/$CANON_TARGET"
cat > "$SHADOW/$NEW_TARGET" <<'NEWEOF'
#!/usr/bin/env bash
# arquivo NOVO do auto-teste: existe para provar que `git add -N` o carrega.
set -euo pipefail
printf 'selftest\n'
NEWEOF

# Sanidade: o alvo canonico e mesmo canonico pelo oraculo (senao o T7 e vacuo).
CANON_FLAG="$(python3 "$REPO/.claude/hooks/check_canonical_edit.py" --is-canonical "$CANON_TARGET" 2>/dev/null | awk -F'\t' 'NR==1{print $2}')"
if [ "$CANON_FLAG" = "1" ]; then _pass "alvo $CANON_TARGET e canonico (oraculo=1)"
else _fail "alvo $CANON_TARGET NAO e canonico (oraculo='$CANON_FLAG') — T7 seria vacuo"; fi

FIN_OUT="$( cd "$REPO" && python3 "$REPO/$PLAN_DIR/w5-ceremony/finalize_patch.py" \
  --shadow "$SHADOW" --out "$REPO/$PATCH_REL" \
  --sentinel "$REPO/$SENTINEL" --proposed "$REPO/$CEREMONY_DIR/PROPOSED-PATCH.md" \
  --repo-root "$REPO" 2>&1 )"
FIN_RC=$?
printf '%s\n' "$FIN_OUT" | sed 's/^/    /'
if [ "$FIN_RC" -ne 0 ]; then _fail "finalize_patch falhou (rc=$FIN_RC)"; fi
# O SIGN cruza BASE-SHA.txt com o Patch-base; no clone a base e o HEAD da
# SOMBRA (o commit dos materiais so acontece depois).
printf '%s\n' "$SHADOW_BASE" > "$REPO/$CEREMONY_DIR/BASE-SHA.txt"

NEWCOUNT="$(awk '/^new file mode /{n++} END{print n+0}' "$REPO/$PATCH_REL")"
if [ "$NEWCOUNT" -ge 1 ]; then _pass "o patch carrega $NEWCOUNT arquivo(s) novo(s)"
else _fail "o arquivo NOVO sumiu do patch (a perna add -N regrediu)"; fi

SCOPE_HAS_NEW="$(awk '/BEGIN SIGNED SCOPE/{f=1;next} /END SIGNED SCOPE/{f=0} f' "$REPO/$SENTINEL" | grep -c "selftest-new.sh")"
if [ "$SCOPE_HAS_NEW" = "1" ]; then _pass "o arquivo novo entrou no Scope DERIVADO"
else _fail "o arquivo novo nao entrou no Scope (contagem=$SCOPE_HAS_NEW)"; fi

# --------------------------------------------------------------------------
_head "T3 — commit dos materiais, SIGN e LAND --dry-run"
# --------------------------------------------------------------------------
git -C "$REPO" add -- "$SIGN_REL" "$LAND_REL" "$SENTINEL" \
  "$CEREMONY_DIR/PROPOSED-PATCH.md" "$CEREMONY_DIR/COMMIT-MSG-A.txt" \
  "$CEREMONY_DIR/EXPECTED-BASELINE.txt" "$CEREMONY_DIR/BASE-SHA.txt" \
  "$CEREMONY_DIR/finalize-A.sh" "$CEREMONY_DIR/README-A.md" \
  "$CEREMONY_DIR/test-ceremony-scripts-A.sh" "$PATCH_REL"
printf '# rail sintetico do auto-teste\n' > "$REPO/$CEREMONY_DIR/rail-round-0-selftest.md"
git -C "$REPO" add -- "$CEREMONY_DIR/rail-round-0-selftest.md"
git -C "$REPO" commit -q -am "selftest: materiais da cerimonia"
# O trailer do rail e um GUARD do passo C do land. Aqui so se afirma que ele
# nao ficou por preencher; o guard em si e exercitado nos dois sentidos no T16
# (o passo C nao roda em --dry-run, entao o guard tem de ser extraido).
case "$( cat "$REPO/$CEREMONY_DIR/COMMIT-MSG-A.txt" )" in
  *"Pair-Rail-Reviewed: TO-FILL"*)
    _fail "COMMIT-MSG-A.txt ainda tem o trailer Pair-Rail-Reviewed por preencher — o land abortaria no passo C" ;;
  *"Pair-Rail-Reviewed:"*)
    _pass "COMMIT-MSG-A.txt tem o trailer Pair-Rail-Reviewed preenchido" ;;
  *)
    _fail "COMMIT-MSG-A.txt nao tem trailer Pair-Rail-Reviewed nenhum" ;;
esac

SIGN_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$SIGN_REL" 2>&1 )"
SIGN_RC=$?
if [ "$SIGN_RC" -eq 0 ]; then _pass "SIGN concluiu (modo auto-teste)"
else _fail "SIGN rc=$SIGN_RC"; printf '%s\n' "$SIGN_OUT" | tail -20 | sed 's/^/      /'; fi
ANCHOR_LINE="$(grep -m1 '^Anchor-SHA:' "$REPO/$SENTINEL")"
case "$ANCHOR_LINE" in
  *TO-FILL*) _fail "SIGN nao preencheu o Anchor-SHA" ;;
  *) _pass "Anchor preenchido: ${ANCHOR_LINE:0:26}..." ;;
esac

# --------------------------------------------------------------------------
_head "T4 — --dry-run deixa arvore E index byte-identicos"
# --------------------------------------------------------------------------
_fp() {
  { git -C "$REPO" status --porcelain=v1
    printf -- '--index--\n'
    git -C "$REPO" diff --cached --name-status
  } | shasum -a 256 | awk '{print $1}'
}
FP0="$(_fp)"
DRY_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$LAND_REL" --dry-run --ownership-e2e=defer 2>&1 )"
DRY_RC=$?
printf '%s\n' "$DRY_OUT" | grep -E '^( *ok|ABORT|DRY-RUN|G[0-9]|V1)' | sed 's/^/    /'
FP1="$(_fp)"
if [ "$DRY_RC" -eq 0 ]; then _pass "LAND --dry-run rc=0 (G0..G5 + V1 verdes)"
else _fail "LAND --dry-run rc=$DRY_RC"; printf '%s\n' "$DRY_OUT" | tail -25 | sed 's/^/      /'; fi
# A asserção de fingerprint so significa alguma coisa se o dry-run TIVER
# aplicado o patch. Um abort no G0 deixa a arvore intacta e faria este teste
# passar pelo motivo errado — o mecanismo tem de ser reproduzido, nao a
# aparencia.
case "$DRY_OUT" in
  *"patch aplicado"*)
    if [ "$FP0" = "$FP1" ]; then _pass "dry-run APLICOU e restaurou: arvore + index byte-identicos"
    else _fail "o dry-run aplicou e deixou residuo (fingerprint mudou)"; fi ;;
  *)
    _fail "T4 VACUO: o dry-run nem chegou a aplicar o patch — a asserção de fingerprint nao prova nada" ;;
esac

# --------------------------------------------------------------------------
_head "T5/T6/T7 — controles POSITIVOS dos gates (cada um tem de dar VERMELHO)"
# --------------------------------------------------------------------------
SENT_BACKUP="$SCRATCH/sentinel.signed"
_safe_cp "$REPO/$SENTINEL" "$SENT_BACKUP"

# T5 — remove um bullet: o patch passa a tocar path FORA do Scope.
python3 - "$REPO/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
out, dropped, inb = [], False, False
for ln in s.split("\n"):
    if "BEGIN SIGNED SCOPE" in ln: inb = True
    if "END SIGNED SCOPE" in ln: inb = False
    if inb and ln.startswith("  - ") and not dropped:
        dropped = True
        continue
    out.append(ln)
open(p, "w", encoding="utf-8").write("\n".join(out))
sys.exit(0 if dropped else 1)
PY
T5_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$LAND_REL" --dry-run --ownership-e2e=defer 2>&1 )"
T5_RC=$?
case "$T5_OUT" in
  *"FORA do Scope assinado"*) _pass "T5: G4 pegou path tocado fora do Scope (rc=$T5_RC)" ;;
  *) _fail "T5: G4 NAO pegou o path fora do Scope (rc=$T5_RC)" ;;
esac
_safe_cp "$SENT_BACKUP" "$REPO/$SENTINEL"

# T6 — adiciona um bullet fantasma: Scope autoriza mais do que o patch toca.
python3 - "$REPO/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = s.replace("<!-- END SIGNED SCOPE -->",
              "  - docs/PATH-QUE-O-PATCH-NAO-TOCA.md\n<!-- END SIGNED SCOPE -->")
open(p, "w", encoding="utf-8").write(s)
PY
T6_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$LAND_REL" --dry-run --ownership-e2e=defer 2>&1 )"
T6_RC=$?
case "$T6_OUT" in
  *"Scope autoriza path(s) que o patch NAO toca"*) _pass "T6: G4 pegou o Scope fantasma (rc=$T6_RC)" ;;
  *) _fail "T6: G4 NAO pegou o Scope fantasma (rc=$T6_RC)" ;;
esac
_safe_cp "$SENT_BACKUP" "$REPO/$SENTINEL"

# T7 — `Plans:` DEPOIS de `Scope:`: terminador do bloco para o parser do hook,
# invisivel para o awk do G4. Prova que o G5 nao e decorativo.
python3 - "$REPO/$SENTINEL" <<'PY'
import sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().split("\n")
out, inb, plans = [], False, None
for ln in lines:
    if "BEGIN SIGNED SCOPE" in ln: inb = True
    if "END SIGNED SCOPE" in ln: inb = False
    if inb and ln.startswith("Plans:"):
        plans = ln
        continue
    if inb and ln.startswith("Scope:"):
        out.append(ln)
        if plans:
            out.append(plans)   # terminador plantado DENTRO do bloco
        continue
    out.append(ln)
open(p, "w", encoding="utf-8").write("\n".join(out))
sys.exit(0 if plans else 1)
PY
T7_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$LAND_REL" --dry-run --ownership-e2e=defer 2>&1 )"
T7_RC=$?
T7_G4_GREEN=0
case "$T7_OUT" in
  *"touched == scope nos dois sentidos"*) T7_G4_GREEN=1 ;;
esac
case "$T7_OUT" in
  *"G5 reprovou"*|*"NAO concede"*)
    if [ "$T7_G4_GREEN" = "1" ]; then
      _pass "T7: G4 verde + G5 vermelho — o G5 ve o Scope truncado que o awk nao ve (rc=$T7_RC)"
    else
      _fail "T7 VACUO: G5 reprovou, mas o G4 nao ficou verde — a discordancia nao foi exercitada"
    fi ;;
  *"FORA do Scope assinado"*)
    _fail "T7: parou no G4 — o controle nao chegou ao G5 (rc=$T7_RC)" ;;
  *) _fail "T7: NINGUEM pegou o Scope truncado (rc=$T7_RC) — G5 seria decorativo" ;;
esac
_safe_cp "$SENT_BACKUP" "$REPO/$SENTINEL"

# --------------------------------------------------------------------------
_head "T8/T9 — argumentos e insumos obrigatorios"
# --------------------------------------------------------------------------
T8_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$LAND_REL" --dry-run 2>&1 )"
T8_RC=$?
case "$T8_OUT" in
  *"--ownership-e2e e OBRIGATORIO"*) _pass "T8: sem --ownership-e2e o land ABORTA (rc=$T8_RC)" ;;
  *) _fail "T8: o land aceitou rodar sem --ownership-e2e (rc=$T8_RC)" ;;
esac

mv "$REPO/$CEREMONY_DIR/EXPECTED-BASELINE.txt" "$SCRATCH/baseline.hidden"
T9_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$LAND_REL" --dry-run --ownership-e2e=defer 2>&1 )"
T9_RC=$?
case "$T9_OUT" in
  *"base esperada AUSENTE"*) _pass "T9: sem EXPECTED-BASELINE.txt o land ABORTA (rc=$T9_RC)" ;;
  *) _fail "T9: o land rodou sem base esperada (rc=$T9_RC)" ;;
esac
mv "$SCRATCH/baseline.hidden" "$REPO/$CEREMONY_DIR/EXPECTED-BASELINE.txt"

# --------------------------------------------------------------------------
_head "T10 — o interruptor de auto-teste e RECUSADO fora do scratchpad"
# --------------------------------------------------------------------------
OUTSIDE="$(mktemp -d)"     # macOS: /var/folders/... — fora do scratchpad
mkdir -p "$OUTSIDE/$PLAN_DIR"
git -C "$OUTSIDE" init -q .
_safe_cp "$LIVE_LAND" "$OUTSIDE/$LAND_REL"
T10_OUT="$( cd "$OUTSIDE" && CEREMONY_SELFTEST_NO_GPG=1 bash "$OUTSIDE/$LAND_REL" --dry-run --ownership-e2e=defer 2>&1 )"
T10_RC=$?
case "$T10_OUT" in
  *"CEREMONY_SELFTEST_NO_GPG=1 RECUSADO"*) _pass "T10: interruptor recusado fora do scratchpad (rc=$T10_RC)" ;;
  *) _fail "T10: o interruptor foi ACEITO fora do scratchpad (rc=$T10_RC) — abuso possivel" ;;
esac
rm -rf "$OUTSIDE"

# ==========================================================================
_head "T11/T12/T13 — o V-block compara contra os conjuntos DECLARADOS"
# ==========================================================================
# Os comparadores sao EXTRAIDOS do LAND por ancora de CONTEUDO (nunca por
# numero de linha) e rodados sobre logs SINTETICOS. As suites por tras nao
# rodam aqui — o que se testa e a unica coisa que o LAND pode errar sozinho:
# comparar contra o conjunto errado, ou contra zero.
VDIR="$SCRATCH/vblock"
mkdir -p "$VDIR/scripts/tests" "$VDIR/tmp"
EXPECT_FN="$VDIR/expect.sh"
sed -n '/^_expect() {$/,/^}$/p' "$LIVE_LAND" > "$EXPECT_FN"
V3_BODY="$VDIR/v3.sh"
sed -n '/^UNIT_LOG=/,/^ok "V3:/p' "$LIVE_LAND" > "$V3_BODY"
V4_BODY="$VDIR/v4.sh"
sed -n '/^BASE_LOG=/,/^ok "V4:/p' "$LIVE_LAND" > "$V4_BODY"
V5_BODY="$VDIR/v5.sh"
sed -n '/^_parity_mode() {$/,/^}$/p' "$LIVE_LAND" > "$V5_BODY"

_extract_ok=1
[ -s "$EXPECT_FN" ] && grep -q 'BASELINE_ENV' "$EXPECT_FN" || _extract_ok=0
[ -s "$V3_BODY" ] && grep -q 'EXPECTED_UNIT_ORACLE_FAIL' "$V3_BODY" || _extract_ok=0
[ -s "$V4_BODY" ] && grep -q 'EXPECTED_BASELINE_MANIFEST_KNOWN_OPEN' "$V4_BODY" || _extract_ok=0
[ -s "$V5_BODY" ] && grep -q 'EXPECTED_PARITY_' "$V5_BODY" || _extract_ok=0
if [ "$_extract_ok" = "1" ]; then
  _pass "comparadores V3/V4/V5 + _expect extraidos do LAND por ancora de conteudo"
else
  _fail "NAO consegui extrair os comparadores do LAND (renomeado ou movido?) — T11/T12/T13 sao VACUOS"
fi

# Scaffold: mesmo entorno para todos os corpos. `die` sai 1 e imprime ABORT.
_vharness() {   # $1=corpo  $2=script de saida
  {
    printf 'set -uo pipefail\n'
    printf 'die() { printf "\\nABORT: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'ok()  { printf "  ok  %%s\\n" "$*"; }\n'
    printf 'warn(){ printf "  WARN %%s\\n" "$*"; }\n'
    printf 'BASELINE_ENV="$1"\n'
    printf 'TMPDIR_LAND="$2"\n'
    cat "$EXPECT_FN"
    cat "$1"
  } > "$2"
}
# Cuidado: dentro de _vharness o "$1" impresso e do SCRIPT GERADO, e o `cat
# "$1"` e do proprio _vharness. As duas leituras sao intencionais.
_vharness "$V3_BODY" "$VDIR/run-v3.sh"
_vharness "$V4_BODY" "$VDIR/run-v4.sh"
{ _vharness "$V5_BODY" "$VDIR/run-v5.sh"; printf '_parity_mode "$3" "$4"\n' >> "$VDIR/run-v5.sh"; }

_mkbaseline() {  # $1=arquivo  $2..=linhas KEY=VALUE
  local out="$1"; shift
  : > "$out"
  for kv in "$@"; do printf '%s\n' "$kv" >> "$out"; done
}
# Parametros dos stubs, declarados AQUI para nao dependerem de ordem de
# atribuicao (e para o shellcheck ve-los definidos).
BM_RC=1; PAR_RC=0; PAR_BLOCK=1

# --- T11: V3 (FAIL= do oraculo unitario) ----------------------------------
_head "T11 — V3 compara o FAIL= contra o DECLARADO"
_stub_unit() {   # $1=FAIL a imprimir  $2=rc
  cat > "$VDIR/scripts/tests/test-ownership-verdict-unit.sh" <<STUB
printf 'unit oracle: PASS=63  FAIL=$1\n'
exit $2
STUB
}
_run_v() {  # $1=script  $2=baseline  ... extras
  local s="$1" b="$2"; shift 2
  ( cd "$VDIR" && bash "$s" "$b" "$VDIR/tmp" "$@" 2>&1 )
}
_mkbaseline "$VDIR/base-ok.env" "EXPECTED_UNIT_ORACLE_FAIL=0"
_stub_unit 0 0
T11A="$( _run_v "$VDIR/run-v3.sh" "$VDIR/base-ok.env" )"; T11A_RC=$?
if [ "$T11A_RC" -eq 0 ]; then _pass "T11a FAIL=0 == declarado 0 => V3 VERDE"
else _fail "T11a V3 reprovou com FAIL igual ao declarado (rc=$T11A_RC): $T11A"; fi
_stub_unit 1 1
T11B="$( _run_v "$VDIR/run-v3.sh" "$VDIR/base-ok.env" )"; T11B_RC=$?
case "$T11B" in
  *"oraculo unitario FAIL=1, esperado 0"*) _pass "T11b FAIL=1 != declarado 0 => V3 VERMELHO (rc=$T11B_RC)" ;;
  *) _fail "T11b V3 NAO reprovou com FAIL divergente (rc=$T11B_RC): $T11B" ;;
esac
_mkbaseline "$VDIR/base-empty.env" "EXPECTED_PARITY_USER_RC=0"
_stub_unit 0 0
T11C="$( _run_v "$VDIR/run-v3.sh" "$VDIR/base-empty.env" )"; T11C_RC=$?
case "$T11C" in
  *"AUSENTE em"*) _pass "T11c chave ausente na base => V3 ABORTA fail-closed (rc=$T11C_RC)" ;;
  *) _fail "T11c V3 rodou com a chave AUSENTE (rc=$T11C_RC): $T11C" ;;
esac

# --- T12: V4 (conjunto known-open, NOS DOIS SENTIDOS) ----------------------
_head "T12 — V4 compara o CONJUNTO known-open nos dois sentidos"
_stub_baseline() {  # $1..=ids FAIL   (rc vem de $BM_RC)
  { printf '#!/usr/bin/env bash\n'
    for id in "$@"; do printf "printf 'FAIL %s alguma mensagem\\\\n'\n" "$id"; done
    printf 'printf "==> RESULT\\n"\n'
    printf 'exit %s\n' "$BM_RC"
  } > "$VDIR/scripts/tests/test_install_baseline_manifest.sh"
}
_mkbaseline "$VDIR/base-v4.env" \
  'EXPECTED_BASELINE_MANIFEST_RC=1' \
  'EXPECTED_BASELINE_MANIFEST_KNOWN_OPEN="C.6.2"'
BM_RC=1; _stub_baseline "C.6.2"
T12A="$( _run_v "$VDIR/run-v4.sh" "$VDIR/base-v4.env" )"; T12A_RC=$?
if [ "$T12A_RC" -eq 0 ]; then _pass "T12a conjunto {C.6.2} == declarado => V4 VERDE"
else _fail "T12a V4 reprovou com o conjunto EXATO declarado (rc=$T12A_RC): $T12A"; fi
BM_RC=1; _stub_baseline "C.6.2" "D.9.9"
T12B="$( _run_v "$VDIR/run-v4.sh" "$VDIR/base-v4.env" )"; T12B_RC=$?
case "$T12B" in
  *"conjunto FAIL do baseline-manifest MUDOU"*) _pass "T12b id NOVO (regressao) => V4 VERMELHO (rc=$T12B_RC)" ;;
  *) _fail "T12b V4 aceitou um id NOVO (rc=$T12B_RC): $T12B" ;;
esac
BM_RC=1; _stub_baseline
T12C="$( _run_v "$VDIR/run-v4.sh" "$VDIR/base-v4.env" )"; T12C_RC=$?
case "$T12C" in
  *"conjunto FAIL do baseline-manifest MUDOU"*) _pass "T12c id AUSENTE (verde demais) => V4 VERMELHO (rc=$T12C_RC)" ;;
  *) _fail "T12c V4 aceitou um conjunto ENCOLHIDO — 'ficou verde' passaria calado (rc=$T12C_RC): $T12C" ;;
esac
BM_RC=0; _stub_baseline "C.6.2"
T12D="$( _run_v "$VDIR/run-v4.sh" "$VDIR/base-v4.env" )"; T12D_RC=$?
case "$T12D" in
  *"saiu rc=0, esperado rc=1"*) _pass "T12d rc divergente => V4 VERMELHO (rc=$T12D_RC)" ;;
  *) _fail "T12d V4 ignorou o rc divergente (rc=$T12D_RC): $T12D" ;;
esac

# --- T13: V5 (5 contagens fatais da paridade) ------------------------------
_head "T13 — V5 compara as 5 contagens fatais contra as DECLARADAS"
_stub_parity() {  # $1=STALE  (as demais 0); $PAR_RC = rc; $PAR_BLOCK=0 omite o bloco
  { printf '#!/usr/bin/env bash\n'
    if [ "${PAR_BLOCK:-1}" = "1" ]; then
      printf "printf '  counts (UNDECLARED residue):\\\\n'\n"
      printf "printf '    IDENTICAL 530\\\\n'\n"
      printf "printf '    STALE %s\\\\n'\n" "$1"
      printf "printf '    MISSING_IN_B 0\\\\n'\n"
      printf "printf '    UNCLASSIFIED 0\\\\n'\n"
      printf "printf '    MODE_DIFF 0\\\\n'\n"
      printf "printf '    ONLY_IN_B_OUTSIDE_CLAUDE 0\\\\n'\n"
    else
      printf "printf 'scaffold quebrou antes de classificar\\\\n'\n"
    fi
    printf 'exit %s\n' "${PAR_RC:-0}"
  } > "$VDIR/scripts/tests/test-install-upgrade-parity-e2e.sh"
}
_mkbaseline "$VDIR/base-v5.env" \
  'EXPECTED_PARITY_MAINTAINER_RC=0' \
  'EXPECTED_PARITY_MAINTAINER_STALE=0' \
  'EXPECTED_PARITY_MAINTAINER_MISSING_IN_B=0' \
  'EXPECTED_PARITY_MAINTAINER_UNCLASSIFIED=0' \
  'EXPECTED_PARITY_MAINTAINER_MODE_DIFF=0' \
  'EXPECTED_PARITY_MAINTAINER_ONLY_IN_B_OUTSIDE_CLAUDE=0'
PAR_RC=0; PAR_BLOCK=1; _stub_parity 0
T13A="$( _run_v "$VDIR/run-v5.sh" "$VDIR/base-v5.env" maintainer MAINTAINER )"; T13A_RC=$?
if [ "$T13A_RC" -eq 0 ]; then _pass "T13a as 5 contagens == declaradas => V5 VERDE"
else _fail "T13a V5 reprovou com as contagens declaradas (rc=$T13A_RC): $T13A"; fi
PAR_RC=0; PAR_BLOCK=1; _stub_parity 3
T13B="$( _run_v "$VDIR/run-v5.sh" "$VDIR/base-v5.env" maintainer MAINTAINER )"; T13B_RC=$?
case "$T13B" in
  *"STALE=3, esperado 0"*) _pass "T13b STALE=3 != declarado 0 => V5 VERMELHO (rc=$T13B_RC)" ;;
  *) _fail "T13b V5 aceitou STALE divergente (rc=$T13B_RC): $T13B" ;;
esac
PAR_RC=0; PAR_BLOCK=0; _stub_parity 0
T13C="$( _run_v "$VDIR/run-v5.sh" "$VDIR/base-v5.env" maintainer MAINTAINER )"; T13C_RC=$?
case "$T13C" in
  *"nao chegou a classificar"*) _pass "T13c sem o bloco de contagens => V5 ABORTA, nao passa vazio (rc=$T13C_RC)" ;;
  *) _fail "T13c V5 passou com o log SEM bloco de contagens — verde vazio (rc=$T13C_RC): $T13C" ;;
esac

# ==========================================================================
_head "T14 — finalize-A.sh"
# ==========================================================================
# (a) o sentinel do clone JA esta assinado (T3 gerou o .asc sintetico):
#     re-finalizar invalidaria a assinatura => tem de RECUSAR.
T14A="$( cd "$REPO" && bash "$REPO/$CEREMONY_DIR/finalize-A.sh" 2>&1 )"; T14A_RC=$?
case "$T14A" in
  *"JA esta assinado"*) _pass "T14a finalize-A RECUSA quando o .asc existe (rc=$T14A_RC)" ;;
  *) _fail "T14a finalize-A rodou com o sentinel assinado (rc=$T14A_RC): $( printf '%s' "$T14A" | tail -5 )" ;;
esac
rm -f "$REPO/$SENTINEL.asc"

# (b) no-op: BASE-SHA.txt == HEAD e o patch aplica limpo. O arquivo e escrito
#     SEM commitar de proposito — commitar moveria o HEAD e o par nunca
#     convergiria (foi a primeira forma deste teste, e ela nao fecha).
git -C "$REPO" rev-parse HEAD > "$REPO/$CEREMONY_DIR/BASE-SHA.txt"
T14B="$( cd "$REPO" && bash "$REPO/$CEREMONY_DIR/finalize-A.sh" 2>&1 )"; T14B_RC=$?
case "$T14B" in
  *"NADA a fazer"*) _pass "T14b finalize-A e no-op quando ja esta no HEAD (rc=$T14B_RC)" ;;
  *) _fail "T14b finalize-A nao reconheceu o no-op (rc=$T14B_RC): $( printf '%s' "$T14B" | tail -8 )" ;;
esac

# (c) re-base real: commitar o BASE-SHA (mais o sentinel que o SIGN sujou) move
#     o HEAD e desalinha o par — exatamente o estado da manha depois do land do
#     pacote B. O commit NAO toca nenhum path do patch.
git -C "$REPO" commit -q -am "selftest: move o HEAD sem tocar o patch"
NEW_HEAD="$( git -C "$REPO" rev-parse HEAD )"
T14C="$( cd "$REPO" && bash "$REPO/$CEREMONY_DIR/finalize-A.sh" 2>&1 )"; T14C_RC=$?
printf '%s\n' "$T14C" | grep -E '^( *ok|ABORT)' | sed 's/^/    /'
REBASED="$( sed -n 's/^[[:space:]]*\([0-9a-f]\{40\}\)[[:space:]]*$/\1/p' "$REPO/$CEREMONY_DIR/BASE-SHA.txt" | head -1 )"
if [ "$T14C_RC" -eq 0 ] && [ "$REBASED" = "$NEW_HEAD" ]; then
  _pass "T14c finalize-A re-baseou o pacote no HEAD novo ($REBASED)"
else
  _fail "T14c finalize-A nao re-baseou (rc=$T14C_RC, BASE-SHA=$REBASED, HEAD=$NEW_HEAD)"
  printf '%s\n' "$T14C" | tail -12 | sed 's/^/      /'
fi
if git -C "$REPO" diff --quiet && git -C "$REPO" diff --cached --quiet; then
  _pass "T14c finalize-A commitou os materiais regenerados (arvore limpa)"
else
  _fail "T14c finalize-A deixou a arvore suja depois do re-base"
fi

# ==========================================================================
_head "T15 — BASE-SHA.txt discordando do Patch-base ABORTA no SIGN"
# ==========================================================================
printf '%s\n' "0000000000000000000000000000000000000000" > "$REPO/$CEREMONY_DIR/BASE-SHA.txt"
git -C "$REPO" commit -q -am "selftest: BASE-SHA divergente"
T15="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$SIGN_REL" 2>&1 )"; T15_RC=$?
case "$T15" in
  *"BASE-SHA.txt discorda do Patch-base"*) _pass "T15: SIGN aborta com BASE-SHA divergente (rc=$T15_RC)" ;;
  *) _fail "T15: SIGN aceitou BASE-SHA divergente (rc=$T15_RC): $( printf '%s' "$T15" | tail -5 )" ;;
esac

# ==========================================================================
_head "T16 — o guard do trailer Pair-Rail-Reviewed, nos dois sentidos"
# ==========================================================================
# O guard vive no passo C do land, DEPOIS do V-block inteiro — rodar o land
# ate la custaria duas instalacoes reais. Extraido por ancora de conteudo e
# acionado com dois COMMIT_MSG sinteticos, como os comparadores V3/V4/V5.
TRAILER_BODY="$VDIR/trailer.sh"
sed -n '/^case "\$(cat "\$COMMIT_MSG")" in$/,/^esac$/p' "$LIVE_LAND" > "$TRAILER_BODY"
if [ -s "$TRAILER_BODY" ] && grep -q 'Pair-Rail-Reviewed' "$TRAILER_BODY"; then
  _pass "guard do trailer extraido do LAND por ancora de conteudo"
else
  _fail "NAO consegui extrair o guard do trailer (movido ou renomeado?) — T16 e VACUO"
fi
{
  printf 'set -uo pipefail\n'
  printf 'die() { printf "\\nABORT: %%s\\n" "$*" >&2; exit 1; }\n'
  printf 'COMMIT_MSG="$1"\n'
  cat "$TRAILER_BODY"
  printf 'printf "guard passou\\n"\n'
} > "$VDIR/run-trailer.sh"
printf 'msg\n\nPair-Rail-Reviewed: TO-FILL-AFTER-RAIL\n' > "$VDIR/msg-tofill.txt"
T16A="$( bash "$VDIR/run-trailer.sh" "$VDIR/msg-tofill.txt" 2>&1 )"; T16A_RC=$?
case "$T16A" in
  *"trailer Pair-Rail-Reviewed por preencher"*) _pass "T16a trailer TO-FILL => guard ABORTA (rc=$T16A_RC)" ;;
  *) _fail "T16a o guard deixou passar um trailer TO-FILL (rc=$T16A_RC): $T16A" ;;
esac
T16B="$( bash "$VDIR/run-trailer.sh" "$REPO/$CEREMONY_DIR/COMMIT-MSG-A.txt" 2>&1 )"; T16B_RC=$?
case "$T16B" in
  *"guard passou"*) _pass "T16b o COMMIT-MSG-A.txt REAL passa o guard (rc=$T16B_RC)" ;;
  *) _fail "T16b o COMMIT-MSG-A.txt real NAO passa o guard (rc=$T16B_RC): $T16B" ;;
esac

# --------------------------------------------------------------------------
_head "RESUMO"
# --------------------------------------------------------------------------
printf '  PASS=%d  FAIL=%d\n' "$PASS" "$FAIL"
printf '  arvore viva intocada: %s\n' "$( git -C "$LIVE" rev-parse HEAD )"
if [ "$FAIL" -eq 0 ]; then
  printf '\n\033[32mAUTO-TESTE VERDE\033[0m — 12 controles positivos deram vermelho como deviam.\n'
  exit 0
fi
printf '\n\033[31mAUTO-TESTE VERMELHO\033[0m — %d asserção(oes) falharam.\n' "$FAIL"
exit 1
