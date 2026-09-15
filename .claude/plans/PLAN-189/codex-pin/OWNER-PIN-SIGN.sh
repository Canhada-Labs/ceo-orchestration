#!/usr/bin/env bash
# OWNER-PIN-SIGN.sh — cerimônia do re-pin codex-cli 0.147.0 -> 0.154.0.
#
# UM passo: preenche o Anchor-SHA, assina o sentinel, aplica os dois arquivos
# canônicos, roda a bateria e commita. NÃO faz push (a decisão é sua).
#
#   bash .claude/plans/PLAN-189/codex-pin/OWNER-PIN-SIGN.sh            # real
#   bash .claude/plans/PLAN-189/codex-pin/OWNER-PIN-SIGN.sh --dry-run  # ensaio
#
# Um pinentry (a assinatura do sentinel). Se o GPG reclamar de pinentry:
#   export GPG_TTY=$(tty)
set -euo pipefail

DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
cd "$(git rev-parse --show-toplevel)"

D=.claude/plans/PLAN-189/codex-pin
SENT="$D/pin-0154-approved.md"
ASC="$SENT.asc"
DST_PIN=.claude/governance/codex-cli-pin.txt
DST_MAN=.claude/governance/codex-cli-pin-manifest.json
SRC_PIN="$D/codex-cli-pin.txt.new"
SRC_MAN="$D/codex-cli-pin-manifest.json.new"
BAK=$(mktemp -d /tmp/pinbak.XXXXXX)

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
restore() {
  [ -f "$BAK/pin" ] && cp "$BAK/pin" "$DST_PIN" || true
  [ -f "$BAK/man" ] && cp "$BAK/man" "$DST_MAN" || true
}
trap 'rc=$?; [ $rc -ne 0 ] && { restore; printf "\nárvore RESTAURADA. Backup em %s\n" "$BAK" >&2; }' EXIT

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
# os destinos TÊM de ser canônicos — se o oráculo disser 0, esta cerimônia é desnecessária
for f in "$DST_PIN" "$DST_MAN"; do
  v=$(python3 .claude/hooks/check_canonical_edit.py --is-canonical "$f" 2>/dev/null | awk '{print $2}')
  [ "$v" = "1" ] || die "$f NÃO é canônico (oráculo=$v) — não use esta cerimônia"
done
cp "$DST_PIN" "$BAK/pin"; cp "$DST_MAN" "$BAK/man"
printf '   OK: main, sincronizado, árvore limpa, 2 destinos canônicos confirmados\n'

say "1/6 Anchor-SHA real no sentinel"
HEAD_SHA=$(git rev-parse HEAD)
# o ENSAIO nunca muta material persistente: trabalha sobre uma cópia, senão
# deixaria o sentinel sujo e o run real abortaria no P0 (medido na S352).
if [ "$DRY" = "1" ]; then
  cp "$SENT" "$BAK/sentinel.md"; SENT="$BAK/sentinel.md"; ASC="$SENT.asc"
fi
python3 - "$SENT" "$HEAD_SHA" <<'PY'
import sys,pathlib,re
p=pathlib.Path(sys.argv[1]); t=p.read_text(encoding="utf-8")
t2=re.sub(r'^Anchor-SHA:.*$', 'Anchor-SHA: '+sys.argv[2], t, count=1, flags=re.M)
if t2==t: raise SystemExit("linha Anchor-SHA não encontrada")
p.write_text(t2,encoding="utf-8")
PY
grep -q "Anchor-SHA: $HEAD_SHA" "$SENT" || die "Anchor-SHA não gravou"
printf '   Anchor-SHA = %s\n' "$HEAD_SHA"

say "2/6 assinar o sentinel (pinentry)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura\n'
else
  [ -f "$ASC" ] && rm "$ASC"     # sem --output: evita o prompt de overwrite do gpg
  gpg --armor --detach-sign "$SENT" || die "assinatura falhou"
  gpg --verify "$ASC" "$SENT" || die "a assinatura não verifica"
fi

say "3/6 aplicar os dois arquivos canônicos"
cp "$SRC_PIN" "$DST_PIN"
cp "$SRC_MAN" "$DST_MAN"
grep -q '>=0.128.0,<0.155.0' "$DST_PIN" || die "range novo não aterrissou"
grep -q '"package_version": "0.154.0"' "$DST_MAN" || die "manifesto novo não aterrissou"
printf '   aplicados\n'

say "4/6 bateria de gates"
bash .claude/scripts/validate-governance.sh >/tmp/pin-gov.out 2>&1 \
  || { cat /tmp/pin-gov.out >&2; die "validate-governance reprovou (log: /tmp/pin-gov.out)"; }
grep -q 'Errors:   0' /tmp/pin-gov.out || die "governance com erros"
python3 .claude/scripts/check_contamination.py >/dev/null 2>&1 || die "contamination reprovou"
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >/dev/null 2>&1 || die "verify-counts reprovou"
printf '   governance 0 erros, contamination OK, counts OK\n'

say "5/6 stage EXATO + conferência touched ⊆ scope"
git add -- "$DST_PIN" "$DST_MAN"
[ "$DRY" = "1" ] || git add -- "$SENT"
[ "$DRY" = "1" ] || git add -- "$ASC"     # `git add -u` NUNCA pegaria o .asc novo
TOUCHED=$(git diff --cached --name-only | sort)
EXPECTED=$(printf '%s\n' "$DST_PIN" "$DST_MAN" $([ "$DRY" = "1" ] || printf '%s\n%s' "$SENT" "$ASC") | sort)
EXTRA=$(comm -23 <(printf '%s\n' "$TOUCHED") <(printf '%s\n' "$EXPECTED"))
[ -z "$EXTRA" ] || die "fora do escopo:$(printf '\n   %s' $EXTRA)"
printf '%s\n' "$TOUCHED" | sed 's/^/   /'

if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada commitado; desfazendo"
  git reset -q HEAD -- . && restore
  printf '\nEnsaio OK. Rode sem --dry-run para valer.\n'
  trap - EXIT; exit 0
fi

say "6/6 commit (nunca abre editor)"
git commit -q -F - <<MSG
ceremony(PLAN-189): re-pin codex-cli 0.147.0 -> 0.154.0

O rail rodava sobre um revisor SETE releases mais velho que o CLI global do
Owner. O modelo já estava atual (gpt-6-astra, effort max, herdado do config);
o defasado era o binário.

Digests regenerados do tarball real do registry (npm pack + shasum sobre o
binário extraído); os comandos de reprodução estão no sentinel assinado.

Consequência DECLARADA no cabeçalho do pin: isto troca o INSTRUMENTO do rail,
logo medições antes/depois não são comparáveis — a série de validade 93/93/91
da S352 foi medida sob 0.147.0.

ADR-111 §pin-update-protocol: alargar o limite superior não dispara re-run da
Phase 4-bis (nenhuma medição nova de corpus travado foi tomada).

Sentinel: $SENT (assinado, Anchor-SHA $HEAD_SHA)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
trap - EXIT
printf '\n============================================================\n'
printf ' RE-PIN COMMITADO. Falta só:  git push origin main\n'
printf ' Backup dos originais: %s\n' "$BAK"
printf '============================================================\n'
