#!/usr/bin/env bash
# test-ceremony-scripts.sh — auto-teste dos scripts de cerimônia da W5.
# CEREMONY-LINT: handwritten-exception: harness de teste da propria cerimonia
# (le e executa SIGN/LAND num clone descartavel; nao assina nem empurra nada).
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
#
# Uso:  bash .claude/plans/PLAN-183/w5-ceremony/test-ceremony-scripts.sh
set -uo pipefail   # NAO -e: as falhas sao CLASSIFICADAS, nao fatais.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
LIVE="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
SCRATCH="/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/ceremony-selftest-w5fix"

PLAN_DIR=".claude/plans/PLAN-183"
CEREMONY_DIR="$PLAN_DIR/w5-ceremony"
SENTINEL="$PLAN_DIR/wave-w5fix-approved.md"
PATCH_REL="$CEREMONY_DIR/S327b-W5FIX.patch"

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

# Os materiais da cerimonia ainda sao UNTRACKED na arvore viva; o clone nao os
# traz. Copia + commit no clone para reproduzir o estado "materiais commitados".
mkdir -p "$REPO/$CEREMONY_DIR"
for f in "$PLAN_DIR/OWNER-S327b-SIGN.sh" "$PLAN_DIR/OWNER-S327b-LAND.sh" "$SENTINEL" \
         "$CEREMONY_DIR/finalize_patch.py" "$CEREMONY_DIR/PROPOSED-PATCH-W5FIX.md" \
         "$CEREMONY_DIR/COMMIT-MSG-W5FIX.txt" "$CEREMONY_DIR/README-CERIMONIA.md" \
         "$CEREMONY_DIR/test-ceremony-scripts.sh" ; do
  _safe_cp "$LIVE/$f" "$REPO/$f"
done
# Base esperada sintetica: no clone o V-block longo nao roda (o --dry-run para
# no V1), mas o G0 EXIGE o arquivo — e essa exigencia e o T9.
cat > "$REPO/$CEREMONY_DIR/EXPECTED-BASELINE.txt" <<'ENVEOF'
EXPECTED_PARITY_MAINTAINER_RC=0
EXPECTED_PARITY_MAINTAINER_STALE=0
EXPECTED_PARITY_MAINTAINER_MISSING_IN_B=0
EXPECTED_PARITY_MAINTAINER_UNCLASSIFIED=0
EXPECTED_PARITY_MAINTAINER_MODE_DIFF=0
EXPECTED_PARITY_MAINTAINER_ONLY_IN_B_OUTSIDE_CLAUDE=0
EXPECTED_PARITY_USER_RC=0
EXPECTED_PARITY_USER_STALE=0
EXPECTED_PARITY_USER_MISSING_IN_B=0
EXPECTED_PARITY_USER_UNCLASSIFIED=0
EXPECTED_PARITY_USER_MODE_DIFF=0
EXPECTED_PARITY_USER_ONLY_IN_B_OUTSIDE_CLAUDE=0
EXPECTED_UNIT_ORACLE_FAIL=0
EXPECTED_OWNERSHIP_RED_IDS="OWN-0016 OWN-0024 OWN-0027"
ENVEOF

# --------------------------------------------------------------------------
_head "T1 — finalize_patch --self-test (controle positivo do git add -N)"
# --------------------------------------------------------------------------
T1_OUT="$(python3 "$REPO/$CEREMONY_DIR/finalize_patch.py" --self-test 2>&1)"
T1_RC=$?
printf '%s\n' "$T1_OUT" | sed 's/^/    /'
if [ "$T1_RC" -eq 0 ]; then _pass "finalize_patch --self-test verde"
else _fail "finalize_patch --self-test rc=$T1_RC"; fi

# --------------------------------------------------------------------------
_head "T2 — sombra: 1 canonico modificado + 1 arquivo NOVO"
# --------------------------------------------------------------------------
git clone --quiet --local "$REPO" "$SHADOW"
CANON_TARGET=".claude/hooks/_lib/runtime_paths.py"
NEW_TARGET="$CEREMONY_DIR/selftest-new.sh"
# A sombra e um clone do REPO no estado ANTES do commit dos materiais, entao
# o diretorio da cerimonia ainda nao existe la.
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

FIN_OUT="$( cd "$REPO" && python3 "$REPO/$CEREMONY_DIR/finalize_patch.py" \
  --shadow "$SHADOW" --out "$REPO/$PATCH_REL" \
  --sentinel "$REPO/$SENTINEL" --proposed "$REPO/$CEREMONY_DIR/PROPOSED-PATCH-W5FIX.md" \
  --repo-root "$REPO" 2>&1 )"
FIN_RC=$?
printf '%s\n' "$FIN_OUT" | sed 's/^/    /'
if [ "$FIN_RC" -ne 0 ]; then _fail "finalize_patch falhou (rc=$FIN_RC)"; fi

NEWCOUNT="$(awk '/^new file mode /{n++} END{print n+0}' "$REPO/$PATCH_REL")"
if [ "$NEWCOUNT" -ge 1 ]; then _pass "o patch carrega $NEWCOUNT arquivo(s) novo(s)"
else _fail "o arquivo NOVO sumiu do patch (a perna add -N regrediu)"; fi

SCOPE_HAS_NEW="$(awk '/BEGIN SIGNED SCOPE/{f=1;next} /END SIGNED SCOPE/{f=0} f' "$REPO/$SENTINEL" | grep -c "selftest-new.sh")"
if [ "$SCOPE_HAS_NEW" = "1" ]; then _pass "o arquivo novo entrou no Scope DERIVADO"
else _fail "o arquivo novo nao entrou no Scope (contagem=$SCOPE_HAS_NEW)"; fi

# --------------------------------------------------------------------------
_head "T3 — commit dos materiais, SIGN e LAND --dry-run"
# --------------------------------------------------------------------------
git -C "$REPO" add -- "$PLAN_DIR/OWNER-S327b-SIGN.sh" "$PLAN_DIR/OWNER-S327b-LAND.sh" \
  "$SENTINEL" "$CEREMONY_DIR/finalize_patch.py" "$CEREMONY_DIR/PROPOSED-PATCH-W5FIX.md" \
  "$CEREMONY_DIR/COMMIT-MSG-W5FIX.txt" "$CEREMONY_DIR/README-CERIMONIA.md" \
  "$CEREMONY_DIR/test-ceremony-scripts.sh" "$CEREMONY_DIR/EXPECTED-BASELINE.txt" \
  "$PATCH_REL"
# Registro de rail sintetico: o G0 exige pelo menos um rastreado.
printf '# rail sintetico do auto-teste\n' > "$REPO/$CEREMONY_DIR/rail-round-0-selftest.md"
git -C "$REPO" add -- "$CEREMONY_DIR/rail-round-0-selftest.md"
git -C "$REPO" commit -q -m "selftest: materiais da cerimonia"
# O trailer do COMMIT-MSG e um guard: preenche para o caminho feliz.
sed -i.bak 's/^Pair-Rail-Reviewed: TO-FILL-AFTER-RAIL$/Pair-Rail-Reviewed: APPROVE/' \
  "$REPO/$CEREMONY_DIR/COMMIT-MSG-W5FIX.txt"
rm -f "$REPO/$CEREMONY_DIR/COMMIT-MSG-W5FIX.txt.bak"
git -C "$REPO" commit -q -am "selftest: trailer do rail"

SIGN_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$PLAN_DIR/OWNER-S327b-SIGN.sh" 2>&1 )"
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
DRY_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$PLAN_DIR/OWNER-S327b-LAND.sh" --dry-run --ownership-e2e=defer 2>&1 )"
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
_restore_sentinel() { git -C "$REPO" checkout -- "$SENTINEL" 2>/dev/null; }
SENT_BACKUP="$SCRATCH/sentinel.signed"
_safe_cp "$REPO/$SENTINEL" "$SENT_BACKUP"

# T5 — remove um bullet: o patch passa a tocar path FORA do Scope.
python3 - "$REPO/$SENTINEL" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
lines = s.split("\n")
out, dropped = [], False
inb = False
for ln in lines:
    if "BEGIN SIGNED SCOPE" in ln: inb = True
    if "END SIGNED SCOPE" in ln: inb = False
    if inb and ln.startswith("  - ") and not dropped:
        dropped = True
        continue
    out.append(ln)
open(p, "w", encoding="utf-8").write("\n".join(out))
sys.exit(0 if dropped else 1)
PY
T5_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$PLAN_DIR/OWNER-S327b-LAND.sh" --dry-run --ownership-e2e=defer 2>&1 )"
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
T6_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$PLAN_DIR/OWNER-S327b-LAND.sh" --dry-run --ownership-e2e=defer 2>&1 )"
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
T7_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$PLAN_DIR/OWNER-S327b-LAND.sh" --dry-run --ownership-e2e=defer 2>&1 )"
T7_RC=$?
# O T7 so prova alguma coisa se o G4 tiver ficado VERDE: e a DISCORDANCIA
# entre o awk (que le todos os bullets) e o parser do hook (que para no
# terminador `Plans:`) que da razao de existir ao G5. Exigir as duas metades.
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
_restore_sentinel >/dev/null 2>&1

# --------------------------------------------------------------------------
_head "T8/T9 — argumentos e insumos obrigatorios"
# --------------------------------------------------------------------------
_safe_cp "$SENT_BACKUP" "$REPO/$SENTINEL"
T8_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$PLAN_DIR/OWNER-S327b-LAND.sh" --dry-run 2>&1 )"
T8_RC=$?
case "$T8_OUT" in
  *"--ownership-e2e e OBRIGATORIO"*) _pass "T8: sem --ownership-e2e o land ABORTA (rc=$T8_RC)" ;;
  *) _fail "T8: o land aceitou rodar sem --ownership-e2e (rc=$T8_RC)" ;;
esac

mv "$REPO/$CEREMONY_DIR/EXPECTED-BASELINE.txt" "$SCRATCH/baseline.hidden"
T9_OUT="$( cd "$REPO" && CEREMONY_SELFTEST_NO_GPG=1 bash "$REPO/$PLAN_DIR/OWNER-S327b-LAND.sh" --dry-run --ownership-e2e=defer 2>&1 )"
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
_safe_cp "$LIVE/$PLAN_DIR/OWNER-S327b-LAND.sh" "$OUTSIDE/$PLAN_DIR/OWNER-S327b-LAND.sh"
T10_OUT="$( cd "$OUTSIDE" && CEREMONY_SELFTEST_NO_GPG=1 bash "$OUTSIDE/$PLAN_DIR/OWNER-S327b-LAND.sh" --dry-run --ownership-e2e=defer 2>&1 )"
T10_RC=$?
case "$T10_OUT" in
  *"CEREMONY_SELFTEST_NO_GPG=1 RECUSADO"*) _pass "T10: interruptor recusado fora do scratchpad (rc=$T10_RC)" ;;
  *) _fail "T10: o interruptor foi ACEITO fora do scratchpad (rc=$T10_RC) — abuso possivel" ;;
esac
rm -rf "$OUTSIDE"

# --------------------------------------------------------------------------
_head "RESUMO"
# --------------------------------------------------------------------------
printf '  PASS=%d  FAIL=%d\n' "$PASS" "$FAIL"
printf '  arvore viva intocada: %s\n' \
  "$( git -C "$LIVE" rev-parse HEAD )"
if [ "$FAIL" -eq 0 ]; then
  printf '\n\033[32mAUTO-TESTE VERDE\033[0m — 4 controles positivos deram vermelho como deviam.\n'
  exit 0
fi
printf '\n\033[31mAUTO-TESTE VERMELHO\033[0m — %d asserção(oes) falharam.\n' "$FAIL"
exit 1
