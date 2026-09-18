#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: derivador de UM uso da relmeta da v1.4.1
# (PLAN-192); o toolkit do PLAN-188 é o que elimina esta classe.
# derive-relmeta141.sh — deriva RELMETA141.patch do HEAD e pina o sha256 no sentinel.
#
# Roda o apply-relmeta141-edits.py num clone DESCARTÁVEL do HEAD (o derivador
# escreve; escrita nunca é ensaiada na árvore viva), extrai o patch por git diff e
# grava os dois materiais derivados neste diretório. O OWNER-RELMETA141-SIGN.sh
# refaz exatamente esta derivação e exige igualdade byte a byte.
#
#   bash .claude/plans/PLAN-192/relmeta/derive-relmeta141.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
ROOT="$(pwd -P)"
D=.claude/plans/PLAN-192/relmeta
APPLY="$D/apply-relmeta141-edits.py"
PATCH="$D/RELMETA141.patch"
SENT="$D/relmeta141-approved.md"
T_REL=.claude/scripts/local/release.sh
T_MAN=.claude/governance/gate-scripts-manifest.txt
T_TST=.claude/scripts/tests/test_release_bump_sites.py
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }

[ -f "$APPLY" ] && [ -f "$SENT" ] || die "materiais ausentes em $D"
[ -z "$(git status --porcelain --untracked-files=no -- "$T_REL" "$T_MAN" "$T_TST" CHANGELOG.md)" ] \
  || die "um dos alvos (ou o CHANGELOG) tem modificação não commitada — a derivação parte do HEAD"
W="$(mktemp -d /tmp/relmeta141-derive.XXXXXX)"
git clone --quiet --local --no-hardlinks "$ROOT" "$W/wt" || die "clone descartável falhou"
# o derivador pode ainda não estar no HEAD: leve ESTE para o clone, no mesmo caminho
mkdir -p "$W/wt/$D" || die "mkdir no clone falhou"
cp "$APPLY" "$W/wt/$APPLY" || die "cópia do derivador para o clone falhou"
( cd "$W/wt" && python3 "$APPLY" --repo . ) || die "o derivador recusou"
git -C "$W/wt" diff --binary -- "$T_REL" "$T_MAN" "$T_TST" > "$W/RELMETA141.patch" || die "git diff falhou"
[ -s "$W/RELMETA141.patch" ] || die "patch vazio"
[ ! -L "$PATCH" ] || die "destino é symlink: $PATCH"
cp "$W/RELMETA141.patch" "$PATCH" || die "gravação do patch falhou"
PSHA="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
python3 - "$SENT" "$PSHA" <<'PY'
import sys, pathlib, re
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
t2, n = re.subn(r"^Patch-SHA256:.*$", "Patch-SHA256: " + sys.argv[2], t, count=1, flags=re.M)
if n != 1:
    raise SystemExit("linha Patch-SHA256 não encontrada no sentinel")
p.write_text(t2, encoding="utf-8")
PY
grep -q "^Patch-SHA256: $PSHA\$" "$SENT" || die "Patch-SHA256 não gravou"
printf '\npatch derivado: %s (%s linhas)\nPatch-SHA256 = %s\n' "$PATCH" "$(wc -l < "$PATCH" | tr -d ' ')" "$PSHA"
git apply --stat "$PATCH"
