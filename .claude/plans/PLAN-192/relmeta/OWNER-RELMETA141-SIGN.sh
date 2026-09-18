#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (relmeta da v1.4.1),
# na forma de UM script do re-pin do codex (`PLAN-189/codex-pin-0155/`) em vez do
# par SIGN/LAND da v1.4.0 — o patch aqui são 3 arquivos. O toolkit do PLAN-188 é
# o que elimina esta classe.
# OWNER-RELMETA141-SIGN.sh — o release.sh passa a mirar a v1.4.1.
#
# UM passo: re-deriva o patch a partir do HEAD e confere byte a byte com o
# material commitado, mostra o texto que vai para DENTRO da anotação assinada da
# tag, preenche o Anchor-SHA, assina o sentinel, aplica o patch, verifica,
# roda a bateria e commita. NÃO faz push (a decisão é sua).
#
#   bash .claude/plans/PLAN-192/relmeta/OWNER-RELMETA141-SIGN.sh            # real
#   bash .claude/plans/PLAN-192/relmeta/OWNER-RELMETA141-SIGN.sh --dry-run  # ensaio
#
# Um pinentry (a assinatura do sentinel). Se o GPG reclamar de pinentry:
#   export GPG_TTY=$(tty)
set -euo pipefail

DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
cd "$(git rev-parse --show-toplevel)"
ROOT="$(pwd -P)"

D=.claude/plans/PLAN-192/relmeta
SENT_LIVE="$D/relmeta141-approved.md"
ASC_LIVE="$SENT_LIVE.asc"
SENT="$SENT_LIVE"
ASC="$ASC_LIVE"
APPLY="$D/apply-relmeta141-edits.py"
PATCH="$D/RELMETA141.patch"
T_REL=.claude/scripts/local/release.sh
T_MAN=.claude/governance/gate-scripts-manifest.txt
T_TST=.claude/scripts/tests/test_release_bump_sites.py
BAK=$(mktemp -d /tmp/relmeta141.XXXXXX)

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
ARMED=0
restore() {
  # só depois do P0: a árvore rastreada estava limpa, logo HEAD É o estado anterior
  [ "$ARMED" = "1" ] || return 0
  git reset -q HEAD -- "$T_REL" "$T_MAN" "$T_TST" "$SENT_LIVE" "$ASC_LIVE" 2>/dev/null \
    || printf "unstage falhou — confira com git status\n" >&2
  git checkout -q -- "$T_REL" "$T_MAN" "$T_TST" "$SENT_LIVE" \
    || printf "restore dos alvos falhou — confira com git status\n" >&2
  rm -f "$ASC_LIVE" || printf "remoção da assinatura parcial falhou\n" >&2
}
on_exit() {
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    restore
    printf '\nárvore RESTAURADA. Logs em %s\n' "$BAK" >&2
  fi
}
trap on_exit EXIT

say "P0 pré-condições"
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
git remote -v | grep -q 'Canhada-Labs/ceo-orchestration' || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "HEAD != origin/main — pushe ou puxe antes"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "há modificação RASTREADA pendente"
for f in "$SENT_LIVE" "$APPLY" "$PATCH" "$D/OWNER-RELMETA141-SIGN.sh"; do
  [ -f "$f" ] && [ ! -L "$f" ] || die "material ausente ou não-regular: $f"
  git cat-file -e "HEAD:$f" 2>/dev/null || die "material fora do HEAD (commite e pushe antes): $f"
done
for f in "$T_REL" "$T_MAN" "$T_TST"; do
  [ -f "$f" ] && [ ! -L "$f" ] || die "alvo ausente ou não-regular: $f"
done
v=$(python3 .claude/hooks/check_canonical_edit.py --is-canonical "$T_MAN" 2>/dev/null | awk '{print $2}')
[ "$v" = "1" ] || die "$T_MAN NÃO é canônico (oráculo=$v) — não use esta cerimônia"
awk -v f="$T_REL" '$2==f{n++} END{exit !(n==1)}' "$T_MAN" || die "$T_REL não é membro único do manifesto ADR-192"
[ ! -e "$ASC_LIVE" ] || die "já existe $ASC_LIVE — esta cerimônia já rodou? confira com git log"
grep -q '^TARGET_BASE="1.4.0"$' "$T_REL" || die "o driver não está em 1.4.0 — esta cerimônia já landou?"
ARMED=1
printf '   OK: main, sincronizado, árvore limpa, materiais no HEAD, manifesto canônico, driver em 1.4.0\n'

say "1/8 re-derivar o patch do HEAD e conferir com o material commitado"
# num clone descartável: o derivador ESCREVE, e teste de escrita não roda na árvore viva
git clone --quiet --local --no-hardlinks "$ROOT" "$BAK/wt" || die "clone descartável falhou"
[ "$(git -C "$BAK/wt" rev-parse HEAD)" = "$(git rev-parse HEAD)" ] || die "o clone não está no HEAD vivo"
( cd "$BAK/wt" && python3 "$APPLY" --repo . ) >"$BAK/derive.out" 2>&1 \
  || { cat "$BAK/derive.out" >&2; die "o derivador recusou (baseline defasado? CHANGELOG?)"; }
git -C "$BAK/wt" diff --binary -- "$T_REL" "$T_MAN" "$T_TST" >"$BAK/rederived.patch" \
  || die "git diff no clone falhou"
[ -s "$BAK/rederived.patch" ] || die "o derivador não mudou nada — nada a assinar"
EXTRA="$(git -C "$BAK/wt" status --porcelain | awk -v a="$T_REL" -v b="$T_MAN" -v c="$T_TST" '{p=$2} p!=a && p!=b && p!=c {print p}')"
[ -z "$EXTRA" ] || die "o derivador tocou fora do escopo: $EXTRA"
cmp -s "$BAK/rederived.patch" "$PATCH" \
  || die "o patch re-derivado do HEAD difere do material commitado — um land depois dos materiais mudou a derivação (escopo do trem ou pré-imagem). Re-derive, commite e re-ensaie."
sed 's/^/   /' "$BAK/derive.out"

say "2/8 o sentinel pina ESTE patch"
PSHA=$(shasum -a 256 "$PATCH" | awk '{print $1}')
grep -q "^Patch-SHA256: $PSHA\$" "$SENT_LIVE" || die "o sentinel não pina o sha256 do patch ($PSHA)"
printf '   Patch-SHA256 = %s\n' "$PSHA"

say "3/8 o texto que vai para DENTRO da anotação assinada da tag"
( cd "$BAK/wt" && awk '/^TARGET_BASE=/{f=1} f{print} /^RC_NUM=/{exit}' "$T_REL" ) | sed '$d' | sed 's/^/   | /'
if [ "$DRY" != "1" ]; then
  printf '\nEnter para assinar (ctrl-C aborta): '; read -r _
fi

say "4/8 Anchor-SHA real no sentinel"
HEAD_SHA=$(git rev-parse HEAD)
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

say "5/8 assinar o sentinel (pinentry)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura\n'
else
  gpg --armor --detach-sign "$SENT" || die "assinatura falhou"
  gpg --verify "$ASC" "$SENT" || die "a assinatura não verifica"
fi

say "6/8 aplicar o patch e verificar"
git apply --check "$PATCH" || die "o patch não aplica sobre o HEAD"
git apply "$PATCH" || die "git apply falhou"
grep -q '^TARGET_BASE="1.4.1"$' "$T_REL" || die "TARGET_BASE não foi para 1.4.1"
shasum -a 256 -c "$T_MAN" >"$BAK/manifest.out" 2>&1 \
  || { cat "$BAK/manifest.out" >&2; die "manifesto ADR-192 não confere (o mesmo comando do CI)"; }
bash -n "$T_REL" || die "release.sh não passa em bash -n"
bash "$T_REL" --help >"$BAK/help.out" 2>&1 || { cat "$BAK/help.out" >&2; die "release.sh --help falhou"; }
grep -q 'target base version: 1.4.1' "$BAK/help.out" || die "o driver não anuncia 1.4.1"
python3 -m pytest "$T_TST" -q -p no:cacheprovider >"$BAK/pytest.out" 2>&1 \
  || { tail -n 30 "$BAK/pytest.out" >&2; die "a suíte do driver reprovou (log: $BAK/pytest.out)"; }
printf '   manifesto OK, bash -n OK, --help anuncia 1.4.1, %s\n' "$(tail -n 1 "$BAK/pytest.out")"

say "7/8 bateria de gates"
bash .claude/scripts/validate-governance.sh >"$BAK/gov.out" 2>&1 \
  || { tail -n 40 "$BAK/gov.out" >&2; die "validate-governance reprovou (log: $BAK/gov.out)"; }
grep -q 'Errors:   0' "$BAK/gov.out" || die "governance com erros (log: $BAK/gov.out)"
python3 .claude/scripts/check_contamination.py >"$BAK/contam.out" 2>&1 || { tail -n 20 "$BAK/contam.out" >&2; die "contamination reprovou"; }
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >"$BAK/counts.out" 2>&1 || { tail -n 20 "$BAK/counts.out" >&2; die "verify-counts reprovou"; }
python3 .claude/scripts/check-ceremony-script.py >"$BAK/lint.out" 2>&1 || { tail -n 20 "$BAK/lint.out" >&2; die "ceremony-lint reprovou"; }
python3 .claude/scripts/check-claude-md-claims.py >"$BAK/claims.out" 2>&1 || { tail -n 20 "$BAK/claims.out" >&2; die "check-claude-md-claims reprovou"; }
printf '   governance 0 erros, contamination OK, counts OK, ceremony-lint OK, claims OK\n'

say "8/8 stage EXATO + commit (nunca abre editor)"
git add -- "$T_REL" "$T_MAN" "$T_TST"
[ "$DRY" = "1" ] || git add -- "$SENT" "$ASC"
TOUCHED=$(git diff --cached --name-only | sort)
if [ "$DRY" = "1" ]; then
  EXPECTED=$(printf '%s\n' "$T_REL" "$T_MAN" "$T_TST" | sort)
else
  EXPECTED=$(printf '%s\n' "$T_REL" "$T_MAN" "$T_TST" "$SENT" "$ASC" | sort)
fi
[ "$TOUCHED" = "$EXPECTED" ] || die "índice diferente do escopo exato:
--- staged
$TOUCHED
--- esperado
$EXPECTED"
printf '%s\n' "$TOUCHED" | sed 's/^/   /'

if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada commitado; desfazendo"
  restore
  [ -z "$(git status --porcelain --untracked-files=no)" ] || die "o ensaio deixou a árvore suja"
  printf '\nEnsaio OK. Rode sem --dry-run para valer.\n'
  trap - EXIT; exit 0
fi

git commit -q -F - <<MSG
governance(PLAN-192 relmeta-141): release.sh mira a v1.4.1 + re-pin do manifesto ADR-192

O bloco por-release do driver passa a descrever a v1.4.1: título, escopo do
trem DERIVADO de git log v1.4.0..HEAD (planos citados nos assuntos; ADRs
tocados na faixa: nenhum) e a headline que entra na anotação ASSINADA da tag —
inclusive a parte honesta: o anexo P1 do envelope da v1.4.0 NÃO é curado nesta
release e a cura fica re-alvejada para a v1.4.2 (PLAN-192 OQ-1, decisão do Owner).

release.sh é membro do manifesto ADR-192 (canônico): o sha do driver é re-pinado
no mesmo commit, e o teste que fixa o escopo da anotação é re-pinado de forma
consciente, com o trem anterior virando asserção negativa.

Verificado na cerimônia, depois de aplicar: patch re-derivado do HEAD byte a
byte igual ao material commitado e ao sha pinado no sentinel; shasum -c do
manifesto (o comando do CI); bash -n; a suíte do driver inteira.

Sentinel: $SENT (assinado, Anchor-SHA $HEAD_SHA, Patch-SHA256 $PSHA)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
MSG
trap - EXIT
printf '\n============================================================\n'
printf ' RELMETA-141 COMMITADA. Falta só:  git push origin main\n'
printf ' Logs: %s\n' "$BAK"
printf '============================================================\n'
