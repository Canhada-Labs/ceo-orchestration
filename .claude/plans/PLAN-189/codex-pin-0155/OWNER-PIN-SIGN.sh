#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (re-pin do codex
# CLI), clonada à mão do molde `PLAN-189/codex-pin/OWNER-PIN-SIGN.sh` (0.154.0)
# — não há molde compartilhado hoje; o toolkit do PLAN-188 é justamente o que
# elimina esta classe.
# OWNER-PIN-SIGN.sh — cerimônia do re-pin codex-cli 0.154.0 -> 0.155.0.
#
# UM passo: preenche o Anchor-SHA, assina o sentinel, aplica os dois arquivos
# canônicos, verifica o pin (ADR-182 §5 passo 4), roda a bateria e commita.
# NÃO faz push (a decisão é sua).
#
#   bash .claude/plans/PLAN-189/codex-pin-0155/OWNER-PIN-SIGN.sh            # real
#   bash .claude/plans/PLAN-189/codex-pin-0155/OWNER-PIN-SIGN.sh --dry-run  # ensaio
#
# Um pinentry (a assinatura do sentinel). Se o GPG reclamar de pinentry:
#   export GPG_TTY=$(tty)
#
# Diferença para o molde de 0.154.0: o passo 4 (novo) re-roda
# `--verify-codex-pin` e `pair-rail-gate.sh --phase 6` DEPOIS de aplicar — o
# ADR-182 §5 exige os dois e o molde anterior não os rodava. Os logs da bateria
# vão para o diretório de backup (mktemp), não para um caminho fixo em /tmp.
set -euo pipefail

DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
cd "$(git rev-parse --show-toplevel)"

D=.claude/plans/PLAN-189/codex-pin-0155
SENT_LIVE="$D/pin-0155-approved.md"
ASC_LIVE="$SENT_LIVE.asc"
SENT="$SENT_LIVE"
ASC="$ASC_LIVE"
DST_PIN=.claude/governance/codex-cli-pin.txt
DST_MAN=.claude/governance/codex-cli-pin-manifest.json
SRC_PIN="$D/codex-cli-pin.txt.new"
SRC_MAN="$D/codex-cli-pin-manifest.json.new"
NEW_RANGE='>=0.128.0,<0.156.0'
NEW_VERSION='"package_version": "0.155.0"'
NEW_SHA='b0b14f9c1901c1ec44671094b2dc18b39e4bd8d36a6dc2302cc9d961a7e2a197'
BAK=$(mktemp -d /tmp/pinbak.XXXXXX)

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
restore() {
  # restore best-effort num trap de saída: falha vira aviso, nunca silêncio
  if [ -f "$BAK/pin" ]; then cp "$BAK/pin" "$DST_PIN" || printf "restore do pin falhou\n" >&2; fi
  if [ -f "$BAK/man" ]; then cp "$BAK/man" "$DST_MAN" || printf "restore do manifesto falhou\n" >&2; fi
  # run REAL abortado: o sentinel volta ao byte do HEAD e a assinatura desta
  # rodada sai — senão o próximo run morreria no P0 (modificação rastreada).
  if [ "$DRY" != "1" ] && [ -f "$BAK/sentinel.orig" ]; then
    cp "$BAK/sentinel.orig" "$SENT_LIVE" || printf "restore do sentinel falhou\n" >&2
    rm -f "$ASC_LIVE" || printf "remoção da assinatura parcial falhou\n" >&2
  fi
}
unstage() {
  # tira do índice só o que ESTA cerimônia pode ter posto lá; nunca `reset .`
  git reset -q HEAD -- "$DST_PIN" "$DST_MAN" "$SENT_LIVE" "$ASC_LIVE" 2>/dev/null \
    || printf "unstage falhou — confira com git status\n" >&2
}
trap 'rc=$?; [ $rc -ne 0 ] && { unstage; restore; printf "\nárvore RESTAURADA. Backup e logs em %s\n" "$BAK" >&2; }' EXIT

say "P0 pré-condições"
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
git remote -v | grep -q 'Canhada-Labs/ceo-orchestration' || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "HEAD != origin/main — pushe ou puxe antes"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "há modificação RASTREADA pendente"
for f in "$SENT" "$SRC_PIN" "$SRC_MAN" "$DST_PIN" "$DST_MAN"; do
  [ -f "$f" ] || die "ausente: $f"
done
# os materiais da cerimônia TÊM de estar no HEAD: o que se assina é o que foi revisto
for f in "$SENT" "$SRC_PIN" "$SRC_MAN" "$D/OWNER-PIN-SIGN.sh"; do
  git cat-file -e "HEAD:$f" 2>/dev/null || die "material fora do HEAD (commite e pushe antes): $f"
done
# os destinos TÊM de ser canônicos — se o oráculo disser 0, esta cerimônia é desnecessária
for f in "$DST_PIN" "$DST_MAN"; do
  v=$(python3 .claude/hooks/check_canonical_edit.py --is-canonical "$f" 2>/dev/null | awk '{print $2}')
  [ "$v" = "1" ] || die "$f NÃO é canônico (oráculo=$v) — não use esta cerimônia"
done
command -v codex >/dev/null 2>&1 || die "codex não está no PATH — o passo 4 precisa do binário instalado"
[ ! -e "$ASC_LIVE" ] || die "já existe $ASC_LIVE — esta cerimônia já rodou? confira com git log"
cp "$DST_PIN" "$BAK/pin"; cp "$DST_MAN" "$BAK/man"; cp "$SENT_LIVE" "$BAK/sentinel.orig"
printf '   OK: main, sincronizado, árvore limpa, materiais no HEAD, 2 destinos canônicos confirmados\n'

say "1/7 Anchor-SHA real no sentinel"
HEAD_SHA=$(git rev-parse HEAD)
# o ENSAIO nunca muta material persistente: trabalha sobre uma cópia, senão
# deixaria o sentinel sujo e o run real abortaria no P0 (medido na S352).
if [ "$DRY" = "1" ]; then
  cp "$SENT" "$BAK/sentinel.md"; SENT="$BAK/sentinel.md"; ASC="$SENT.asc"
fi
python3 - "$SENT" "$HEAD_SHA" <<'PY'
import sys,pathlib,re
p=pathlib.Path(sys.argv[1]); t=p.read_text(encoding="utf-8")
t2,n=re.subn(r'^Anchor-SHA:.*$', 'Anchor-SHA: '+sys.argv[2], t, count=1, flags=re.M)
if n!=1: raise SystemExit("linha Anchor-SHA não encontrada")
p.write_text(t2,encoding="utf-8")
PY
grep -q "^Anchor-SHA: $HEAD_SHA\$" "$SENT" || die "Anchor-SHA não gravou"
printf '   Anchor-SHA = %s\n' "$HEAD_SHA"

say "2/7 assinar o sentinel (pinentry)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura\n'
else
  gpg --armor --detach-sign "$SENT" || die "assinatura falhou"
  gpg --verify "$ASC" "$SENT" || die "a assinatura não verifica"
fi

say "3/7 aplicar os dois arquivos canônicos"
for d in "$DST_PIN" "$DST_MAN"; do [ -L "$d" ] && die "destino é symlink: $d"; done
cp "$SRC_PIN" "$DST_PIN"
cp "$SRC_MAN" "$DST_MAN"
[ "$(tail -n 1 "$DST_PIN")" = "$NEW_RANGE" ] || die "range novo não é a ÚLTIMA linha do pin"
grep -qF "$NEW_VERSION" "$DST_MAN" || die "manifesto novo não aterrissou"
grep -qF "$NEW_SHA" "$DST_MAN" || die "sha256 novo não aterrissou no manifesto"
printf '   aplicados\n'

say "4/7 ADR-182 §5 passo 4 — o pin verifica contra o binário instalado"
python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)" >"$BAK/verify.out" 2>&1 \
  || { cat "$BAK/verify.out" >&2; die "--verify-codex-pin reprovou — o binário instalado NÃO é o que o manifesto pina"; }
grep -q '"status": "verified"' "$BAK/verify.out" || { cat "$BAK/verify.out" >&2; die "--verify-codex-pin saiu 0 sem status verified"; }
bash .claude/scripts/local/pair-rail-gate.sh --phase 6 >"$BAK/phase6.out" 2>&1 \
  || { tail -n 25 "$BAK/phase6.out" >&2; die "pair-rail-gate --phase 6 reprovou"; }
printf '   verified; pair-rail-gate --phase 6 OK\n'

say "5/7 bateria de gates"
bash .claude/scripts/validate-governance.sh >"$BAK/gov.out" 2>&1 \
  || { tail -n 40 "$BAK/gov.out" >&2; die "validate-governance reprovou (log: $BAK/gov.out)"; }
grep -q 'Errors:   0' "$BAK/gov.out" || die "governance com erros (log: $BAK/gov.out)"
python3 .claude/scripts/check_contamination.py >"$BAK/contam.out" 2>&1 || { tail -n 20 "$BAK/contam.out" >&2; die "contamination reprovou"; }
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >"$BAK/counts.out" 2>&1 || { tail -n 20 "$BAK/counts.out" >&2; die "verify-counts reprovou"; }
python3 .claude/scripts/check-ceremony-script.py >"$BAK/lint.out" 2>&1 || { tail -n 20 "$BAK/lint.out" >&2; die "ceremony-lint reprovou"; }
printf '   governance 0 erros, contamination OK, counts OK, ceremony-lint OK\n'

say "6/7 stage EXATO + conferência touched ⊆ scope"
git add -- "$DST_PIN" "$DST_MAN"
[ "$DRY" = "1" ] || git add -- "$SENT"
[ "$DRY" = "1" ] || git add -- "$ASC"     # `git add -u` NUNCA pegaria o .asc novo
TOUCHED=$(git diff --cached --name-only | sort)
if [ "$DRY" = "1" ]; then
  EXPECTED=$(printf '%s\n' "$DST_PIN" "$DST_MAN" | sort)
else
  EXPECTED=$(printf '%s\n' "$DST_PIN" "$DST_MAN" "$SENT" "$ASC" | sort)
fi
[ "$TOUCHED" = "$EXPECTED" ] || die "índice diferente do escopo exato:
--- staged
$TOUCHED
--- esperado
$EXPECTED"
printf '%s\n' "$TOUCHED" | sed 's/^/   /'

if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada commitado; desfazendo"
  unstage; restore
  [ -z "$(git status --porcelain --untracked-files=no)" ] || die "o ensaio deixou a árvore suja"
  printf '\nEnsaio OK. Rode sem --dry-run para valer.\n'
  trap - EXIT; exit 0
fi

say "7/7 commit (nunca abre editor)"
git commit -q -F - <<MSG
ceremony(PLAN-189): re-pin codex-cli 0.154.0 -> 0.155.0

O codex-cli 0.155.0 saiu no npm em 2026-09-17; com o manifesto de versão exata
do ADR-182 o pair-rail deste repo ficou fail-CLOSED (--verify-codex-pin ->
payload_sha256_mismatch) e o corte da v1.4.1 não tinha como produzir veredito.

Digests regenerados do tarball real do registry (npm pack + shasum sobre o
binário extraído; o sha512 do tarball confere com o dist.integrity); os comandos
de reprodução estão no sentinel assinado. O binário instalado tem o MESMO sha256.

npm_integrity volta a ser o do artefato de PLATAFORMA (ADR-182 §5 passo 2); o
re-pin de 0.154.0 tinha gravado o do pacote principal — desvio declarado no
sentinel, sem alcance mecânico (o campo não tem leitor; o gate é o sha256).

Widen-upper-only (<0.155.0 -> <0.156.0), fora de janela de release aberta: a
v1.4.1-rc.1 só é cortada depois deste commit. ADR-111 §pin-update-protocol:
alargar o limite superior não dispara re-run da Phase 4-bis.

Consequência DECLARADA: troca o INSTRUMENTO do rail — medições antes/depois
deste commit não são comparáveis.

Verificado na cerimônia, depois de aplicar: --verify-codex-pin = verified;
pair-rail-gate.sh --phase 6 OK.

Sentinel: $SENT (assinado, Anchor-SHA $HEAD_SHA)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
trap - EXIT
printf '\n============================================================\n'
printf ' RE-PIN COMMITADO. Falta só:  git push origin main\n'
printf ' Backup dos originais e logs: %s\n' "$BAK"
printf '============================================================\n'
