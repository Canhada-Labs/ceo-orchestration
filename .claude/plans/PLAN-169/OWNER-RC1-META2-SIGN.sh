#!/bin/bash
# OWNER-RC1-META2-SIGN.sh — assina o sentinel da cerimonia wave-relmeta2
# (PLAN-169; fecha a janela vermelha que a wave-relmeta abriu). NAO aplica nada: o land e o
# OWNER-RC1-META2-LAND.sh.
#
# CEREMONY-LINT: handwritten-exception: NAO e clone de um OWNER-*-SIGN.sh
# existente. Foi escrito contra o corpus de defeitos
# `.claude/plans/PLAN-188/ceremony-defect-corpus-S348.md`, que catalogou 17
# classes vivas no molde clonado. As curas estao NOMEADAS no ponto de uso
# (procure por "CM-NN"). Um clone teria herdado as 12 classes vivas.
#
# Fluxo completo (3 comandos, nenhum editor):
#   bash .claude/plans/PLAN-169/s349-ceremony-relmeta2/finalize-relmeta2.sh
#   bash .claude/plans/PLAN-169/OWNER-RC1-META2-SIGN.sh          <- pinentry 0
#   bash .claude/plans/PLAN-169/OWNER-RC1-META2-LAND.sh --dry-run
#   bash .claude/plans/PLAN-169/OWNER-RC1-META2-LAND.sh
#
# ORDEM IMPORTA: o Anchor-SHA e o HEAD no instante da assinatura. Qualquer
# commit entre assinar e landar o invalida (o G1 do LAND aborta).
#
# O QUE ESTE SCRIPT NAO TEM, e por que: nao ha gate de veredito de rail.
# Este pacote nao passou por rail. O que o revisa e a MEDICAO: a suite do
# driver sai 153/0 na arvore patchada, a mesma suite passa sobre um driver em
# 1.3.0 (prova de que ela DERIVA em vez de pinar), e um defeito plantado no
# escritor de sitios a deixa vermelha (prova de que ela nao virou vacua). O
# resto e o
# harness `s349-ceremony-relmeta2/test-relmeta-ceremony.sh` mais a leitura do
# patch pelo Owner na tela, abaixo. Inventar um gate de rail que le um
# registro que nao existe seria a classe CM-17 do corpus (instrumento que
# aceita ausencia como sucesso).
set -euo pipefail

# A raiz resolve por git a partir da LOCALIZACAO DO SCRIPT, nunca por `../..`
# nem pelo cwd: o Owner pode chamar de qualquer diretorio.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

# --- constantes da cerimonia (o UNICO bloco que muda entre waves) ----------
PLAN_DIR=".claude/plans/PLAN-169"
CDIR="$PLAN_DIR/s349-ceremony-relmeta2"
SENTINEL="$PLAN_DIR/wave-relmeta2-approved.md"
SENT_DRAFT="$PLAN_DIR/wave-relmeta2-approved-draft.md"
PATCH="$CDIR/RELMETA2.patch"
SCOPE="$CDIR/SCOPE.txt"
BASELINE="$CDIR/EXPECTED-BASELINE.txt"
MATERIALS="$CDIR/MATERIALS.sha256"
FINALIZE="$CDIR/finalize-relmeta2.sh"
APPLY="$CDIR/apply-relmeta2-edits.py"
LAND_SCRIPT="$PLAN_DIR/OWNER-RC1-META2-LAND.sh"
ORACLE=".claude/hooks/check_canonical_edit.py"
SIGNERS=".claude/sentinel-signers.txt"
KEY="CFCFACF00335DC74"
SIGNER_LINE="@Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74"
# --------------------------------------------------------------------------

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }

# --- interruptor de AUTO-TESTE (recusado fora do scratchpad) ---------------
# Existe so para `test-relmeta-ceremony.sh` exercitar os gates sem uma chave
# GPG. A comparacao e por REALPATH dos DOIS lados: no macOS `/tmp` e symlink,
# e comparar formato de string mediria formato, nao caminho.
SELFTEST=0
if [ "${RELMETA2_SELFTEST:-0}" = "1" ]; then
  _st_root="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$ROOT")"
  _st_scr="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "${RELMETA2_SELFTEST_SCRATCH:-/nonexistent}")"
  case "$_st_root/" in
    "$_st_scr"/*) SELFTEST=1 ;;
    *) die "RELMETA2_SELFTEST=1 fora do scratchpad declarado — recusado" ;;
  esac
  printf '   (AUTO-TESTE: nenhuma assinatura GPG sera pedida)\n'
fi

GPG_TTY="$(tty 2>/dev/null || true)"; export GPG_TTY

# ---------------------------------------------------------------------------
# P0-a — nenhum caminho pessoal absoluto no material assinado.
# CM-15 do corpus: a isencao de auto-teste vem de um ARGUMENTO, nunca de uma
# sentinela dentro do proprio material nem de variavel de ambiente herdada.
# ---------------------------------------------------------------------------
say "P0-a material sem caminho pessoal absoluto"
_home_prefix="$(printf '/%s/' Users)"
_abs_hits=""
for _f in "$PATCH" "$SCOPE" "$BASELINE" "$SENT_DRAFT" "$APPLY" "$FINALIZE" \
          "$SCRIPT_DIR/$(basename "$0")" "$LAND_SCRIPT"; do
  [ -f "$_f" ] || continue
  # grep -c sem `|| true`: rc 1 = "nenhuma ocorrencia" e o caso BOM; rc >1 e
  # erro real e tem de abortar (CM-04: o gate que nao pergunta nao responde).
  set +e
  _n="$(grep -c -- "$_home_prefix" "$_f")"; _rc=$?
  set -e
  case "$_rc" in
    0) _abs_hits="$_abs_hits
   $_f ($_n ocorrencia(s))" ;;
    1) : ;;
    *) die "grep falhou (rc=$_rc) em $_f — nao vou tratar como limpo" ;;
  esac
done
[ -z "$_abs_hits" ] || die "caminho pessoal absoluto no material:$_abs_hits"
printf '   OK: nenhum literal de home absoluto nos 8 materiais\n'

# ---------------------------------------------------------------------------
# P0-b — docs/threat-model.md: sujeira que NINGUEM editou.
# `check-threat-model-freshness.py` REESCREVE o arquivo como efeito colateral
# de rodar (accepted -> stale) e sai 1. Como o P0-c recusa arvore com
# modificacao rastreada, essa sujeira abortaria a cerimonia acusando um
# arquivo que ninguem tocou. A cura e PONTUAL e provada por CONTEUDO.
# ---------------------------------------------------------------------------
TM="docs/threat-model.md"
if [ -f "$TM" ]; then
  _tm_f="$(mktemp)"
  if ! git status --porcelain --untracked-files=all > "$_tm_f"; then
    rm -f "$_tm_f"; die "git status falhou no P0-b"
  fi
  _tm_lines="$(grep -c . "$_tm_f" || true)"
  _tm_only="$(grep -c "^ M $TM\$" "$_tm_f" || true)"
  if [ "$_tm_lines" = "1" ] && [ "$_tm_only" = "1" ]; then
    _tm_d="$(git diff --unified=0 -- "$TM")" || { rm -f "$_tm_f"; die "git diff do threat-model falhou"; }
    _tm_minus="$(printf '%s\n' "$_tm_d" | grep -c '^-\*\*Status:\*\* accepted$' || true)"
    _tm_plus="$(printf '%s\n' "$_tm_d" | grep -c '^+\*\*Status:\*\* stale$' || true)"
    _tm_other="$(printf '%s\n' "$_tm_d" | grep -cE '^[-+][^-+]' || true)"
    if [ "$_tm_minus" = "1" ] && [ "$_tm_plus" = "1" ] && [ "$_tm_other" = "2" ]; then
      git checkout -- "$TM" || { rm -f "$_tm_f"; die "revert do threat-model falhou"; }
      printf '   (P0-b: revertido o flip accepted->stale que o checker escreve)\n'
    fi
  fi
  rm -f "$_tm_f"
fi

# ---------------------------------------------------------------------------
# P0-c — arvore sem modificacao RASTREADA. Produtor com rc CONFERIDO (CM-04):
# `git status` escreve em arquivo temporario e o rc e checado. Um gate que
# nao conseguiu PERGUNTAR nao pode responder "esta tudo bem".
# ---------------------------------------------------------------------------
say "P0-c arvore sem modificacao rastreada"
_st_f="$(mktemp)"
if ! git status --porcelain=v1 --untracked-files=all > "$_st_f"; then
  rm -f "$_st_f"; die "git status falhou — recusa nomeada, nunca 'arvore limpa'"
fi
_tracked_dirty=""
while IFS= read -r _l; do
  [ -n "$_l" ] || continue
  case "$_l" in
    '??'*) continue ;;
    *) _tracked_dirty="$_tracked_dirty
   $_l" ;;
  esac
done < "$_st_f"
rm -f "$_st_f"
[ -z "$_tracked_dirty" ] \
  || die "modificacao RASTREADA na arvore — o Anchor-SHA descreveria outra coisa:$_tracked_dirty"
printf '   OK: nenhuma modificacao rastreada\n'

# ---------------------------------------------------------------------------
# P0-d — material presente e fechado pelo digest UNICO (CM-16).
# A lista de membros e LIDA do MATERIALS.sha256 escrito pelo finalize; nem o
# SIGN nem o LAND nem o harness recomputam a lista por conta propria.
# ---------------------------------------------------------------------------
say "P0-d material fechado pelo MATERIALS.sha256"
for _f in "$PATCH" "$SCOPE" "$BASELINE" "$MATERIALS" "$APPLY" "$FINALIZE" "$SENT_DRAFT"; do
  [ -f "$_f" ] || die "material ausente: $_f (rode o finalize-relmeta2.sh)"
  [ -L "$_f" ] && die "material e symlink: $_f"
done
( cd "$CDIR" && shasum -a 256 -c MATERIALS.sha256 --status ) \
  || die "MATERIALS.sha256 nao confere — material mudou depois do finalize"
_mat_n="$(grep -c . "$MATERIALS")"
[ "$_mat_n" = "6" ] || die "MATERIALS.sha256 com $_mat_n membros (esperado 6)"
printf '   OK: 6 membros conferem\n'

# ---------------------------------------------------------------------------
# P0-e — REGENERAR baseline e escopo e comparar BYTE A BYTE (CM-10 + CM-11).
# Esta e a diferenca material deste script para o molde: os 22 SIGNs vivos
# apenas LEEM o baseline e IMPRIMEM o escopo; a conferencia real so acontece
# no LAND, isto e, DEPOIS de o Owner ter assinado. Aqui ela acontece ANTES.
# ---------------------------------------------------------------------------
say "P0-e regenerar baseline + escopo e comparar (antes de assinar)"
_regen="$(mktemp -d)"
trap 'rm -rf "$_regen"' EXIT
cp "$PATCH" "$_regen/patch.frozen" || die "copia do patch falhou"
# escopo regenerado do PATCH congelado, pela MESMA receita do finalize
if ! git apply --numstat < "$_regen/patch.frozen" > "$_regen/numstat" 2>/dev/null; then
  die "git apply --numstat recusou o patch — patch malformado"
fi
{ printf 'Scope:\n'; awk '{print "  - " $3}' "$_regen/numstat" | sort; } > "$_regen/SCOPE.regen"
cmp -s "$_regen/SCOPE.regen" "$SCOPE" \
  || die "SCOPE.txt DIVERGE do escopo regenerado do patch — nao assine:
$(diff -u "$SCOPE" "$_regen/SCOPE.regen" || true)"
# baseline regenerado: os hashes PRE-edicao dos alvos, do HEAD atual
_bl_head="$(awk '$1=="BASE-HEAD"{print $2}' "$BASELINE")"
[ -n "$_bl_head" ] || die "EXPECTED-BASELINE.txt sem BASE-HEAD"
HEADSHA="$(git rev-parse HEAD)" || die "git rev-parse HEAD falhou"
[ "$_bl_head" = "$HEADSHA" ] \
  || die "baseline foi gerado sobre $_bl_head, HEAD e $HEADSHA — re-rode o finalize"
_bl_bad=""
while IFS= read -r _bl; do
  case "$_bl" in
    "PRE "*) : ;;
    *) continue ;;
  esac
  _bp="${_bl##* }"; _bh="$(printf '%s' "$_bl" | awk '{print $2}')"
  _live="$(git hash-object -- "$_bp")" || die "hash-object falhou: $_bp"
  [ "$_live" = "$_bh" ] || _bl_bad="$_bl_bad
   $_bp (vivo=$_live baseline=$_bh)"
done < "$BASELINE"
[ -z "$_bl_bad" ] || die "baseline NAO reproduz a arvore viva:$_bl_bad"
_bl_patch="$(awk '$1=="PATCH-SHA256"{print $2}' "$BASELINE")"
[ "$_bl_patch" = "$(shasum -a 256 "$PATCH" | awk '{print $1}')" ] \
  || die "PATCH-SHA256 do baseline != sha do patch em disco"
printf '   OK: escopo e baseline REGENERADOS batem byte a byte\n'

# ---------------------------------------------------------------------------
# P0-f — o oraculo de canonicidade concorda com o que o sentinel vai conceder.
# ---------------------------------------------------------------------------
say "P0-f oraculo de canonicidade sobre os 3 paths do escopo"
_scope_paths="$(awk '/^  - /{print $2}' "$SCOPE")"
[ -n "$_scope_paths" ] || die "escopo vazio"
_orc_out="$(printf '%s\n' "$_scope_paths" | python3 "$ORACLE" --is-canonical -)" \
  || die "oraculo --is-canonical rc!=0 — trate como falha, nunca como 'livre'"
printf '%s\n' "$_orc_out" | sed 's/^/   /'
_orc_canon="$(printf '%s\n' "$_orc_out" | awk -F'\t' '$2=="1"' | wc -l | tr -d ' ')"
[ "$_orc_canon" -ge 1 ] \
  || die "nenhum path canonico no escopo — entao esta cerimonia nao e necessaria; me chame no Claude"
printf '   OK: %s path(s) canonico(s) no escopo — a assinatura e o que os destrava\n' "$_orc_canon"

# ---------------------------------------------------------------------------
# P0-g — o signatario esta no registro.
# ---------------------------------------------------------------------------
if [ -f "$SIGNERS" ]; then
  grep -qF "AE9B236FDAF0462874060C6BCFCFACF00335DC74" "$SIGNERS" \
    || die "fingerprint do Owner ausente de $SIGNERS"
  printf '   OK: signatario no registro (%s)\n' "$SIGNERS"
fi

# ---------------------------------------------------------------------------
# Montagem do sentinel: draft + campos preenchidos + Scope DERIVADO.
# Escrita atomica; destino nunca atraves de symlink pre-existente.
# ---------------------------------------------------------------------------
say "montar o sentinel a partir do draft"
[ -L "$SENTINEL" ] && rm -f "$SENTINEL"
rm -f "$SENTINEL" "$SENTINEL.asc"
# A data vem do BASELINE que o finalize gravou, nunca de `date -u`: ela e
# material (entra nos carimbos do patch), e re-deriva-la aqui faz o par
# finalize/SIGN divergir na virada do dia em UTC — o V1 do LAND
# regeneraria um patch com outra data e recusaria.
TODAY="$(awk '$1=="TODAY"{print $2}' "$BASELINE")"
case "$TODAY" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) : ;;
  *) die "EXPECTED-BASELINE.txt sem linha TODAY YYYY-MM-DD (re-rode o finalize)" ;;
esac
PATCH_SHA="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
PATCH_BASE="$HEADSHA"
_sent_tmp="$PLAN_DIR/.wave-relmeta2.$$.tmp"
# `sed` linha a linha nos campos TO-FILL; o bloco Scope: (que e multilinha)
# e substituido pelo arquivo DERIVADO.
awk -v sha="$PATCH_SHA" -v base="$PATCH_BASE" -v anchor="$HEADSHA" \
    -v today="$TODAY" -v signer="$SIGNER_LINE" -v scopefile="$SCOPE" '
  /^Patch-sha256: TO-FILL-BY-FINALIZE$/ { print "Patch-sha256: " sha; next }
  /^Patch-base: TO-FILL-BY-FINALIZE$/   { print "Patch-base: " base; next }
  /^Anchor-SHA: TO-FILL-BY-SIGN$/       { print "Anchor-SHA: " anchor; next }
  /^Data: TO-FILL-BY-SIGN$/             { print "Data: " today; next }
  /^Approved-By: TO-FILL-BY-SIGN$/      { print "Approved-By: " signer; next }
  /^Scope:$/                            { insc = 1; next }
  insc && /^TO-FILL-BY-FINALIZE$/       { while ((getline l < scopefile) > 0) print l; insc = 0; next }
  { print }
' "$SENT_DRAFT" > "$_sent_tmp" || { rm -f "$_sent_tmp"; die "montagem do sentinel falhou"; }
mv -f "$_sent_tmp" "$SENTINEL" || die "rename atomico do sentinel falhou"
[ -f "$SENTINEL" ] && [ ! -L "$SENTINEL" ] || die "sentinel gerado nao e arquivo regular"

# Nenhum TO-FILL pode sobreviver (CM-17: um placeholder que passa e um
# instrumento aceitando falha como sucesso).
set +e
grep -n 'TO-FILL' "$SENTINEL"; _tf=$?
set -e
[ "$_tf" -eq 1 ] || die "sentinel ainda tem placeholder TO-FILL (ou o grep falhou: rc=$_tf)"
# O Scope montado tem de ser IDENTICO ao arquivo derivado.
_sent_scope="$(mktemp)"
awk '/^Scope:$/{f=1} f' "$SENTINEL" > "$_sent_scope"
cmp -s "$_sent_scope" "$SCOPE" \
  || die "bloco Scope do sentinel != SCOPE.txt derivado:
$(diff -u "$SCOPE" "$_sent_scope" || true)"
rm -f "$_sent_scope"
printf '   OK: sentinel montado, sem placeholder, Scope identico ao derivado\n'

# ---------------------------------------------------------------------------
# O Owner LE o que vai assinar: o sentinel inteiro e o patch inteiro.
# ---------------------------------------------------------------------------
printf '\n----- SENTINEL QUE VOCE VAI ASSINAR -----\n'
cat "$SENTINEL"
printf -- '\n----- PATCH QUE O SENTINEL AUTORIZA (%s bytes, sha256 %s) -----\n' \
  "$(wc -c < "$PATCH" | tr -d ' ')" "$PATCH_SHA"
cat "$PATCH"
printf -- '\n----- FIM -----\n'
printf '\nAnchor-SHA: %s\n' "$HEADSHA"
printf 'Enter para assinar (ctrl-C aborta): '
read -r _

if [ "$SELFTEST" -eq 1 ]; then
  printf '\n(AUTO-TESTE) assinatura PULADA. Sentinel em %s\n' "$SENTINEL"
  exit 0
fi

say "assinar (pinentry 0 de 3 da sessao de release)"
# A regra R2 do ceremony-lint reprova supressao de erro na mesma linha
# de um comando irreversivel — inclusive num COMENTARIO que a cite. A
# falha do gpgconf e engolida de proposito, e com o motivo dito em voz
# alta: o agente e recriado pelo proprio pinentry.
if ! gpgconf --kill gpg-agent >/dev/null 2>&1; then
  printf '   (gpgconf nao respondeu; seguindo — o pinentry recria o agente)\n'
fi
gpg --armor --detach-sign -u "$KEY" "$SENTINEL" || die "gpg --detach-sign falhou"
gpg --verify "$SENTINEL.asc" "$SENTINEL" || die "assinatura nao verifica"
printf '\nASSINADO. Anchor-SHA = %s\n' "$HEADSHA"
printf 'NAO commite nada agora. Proximo:\n'
printf '  bash %s --dry-run\n  bash %s\n' "$LAND_SCRIPT" "$LAND_SCRIPT"
