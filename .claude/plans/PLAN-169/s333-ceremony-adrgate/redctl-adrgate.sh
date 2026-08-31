#!/usr/bin/env bash
# Controles VERMELHOS dos tres skips, cada um numa COPIA descartavel da arvore
# de ADRs — nunca na arvore do repositorio (licao S331: caso que escreve roda
# em arvore descartavel).
#
# Cada controle remove UMA perna da cura e exige que o erro correspondente
# VOLTE, nomeado. Um controle que nao fica vermelho prova que a cura nao e a
# razao do verde.
set -uo pipefail
SH="$1"
CHAIN="$SH/.claude/scripts/check-adr-chain.py"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  \033[32mRED-OK\033[0m %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf '  \033[31mVACUO\033[0m %s\n' "$*"; }

_fresh() { d="$(mktemp -d)"; cp -R "$SH/.claude/adr" "$d/adr"; printf '%s' "$d/adr"; }
_errs() { python3 "$CHAIN" --adr-dir "$1" 2>&1 | grep -c '^ERROR:' || true; }

# --- baseline: a arvore curada sai 0 erros --------------------------------
D="$(_fresh)"; B="$(_errs "$D")"
[ "$B" = "0" ] && ok "baseline: 0 erro(s) na copia intacta" \
                || bad "baseline ja tem $B erro(s) — os controles abaixo nao medem nada"
rm -rf "$D"

# --- RC-1: o slug renomeado VOLTA a existir => a rota nao completou -------
D="$(_fresh)"
cp "$D/ADR-111-locked-corpus-governance.md" "$D/ADR-111-pii-core-promotion.md"
N="$(_errs "$D")"
[ "$N" -ge 1 ] && ok "RC-1 rename: com o slug antigo no disco, o erro VOLTA ($N)" \
               || bad "RC-1 rename: nenhum erro — o skip ignora a perna do arquivo"
rm -rf "$D"

# --- RC-2: o alvo deixa de declarar amended_by => emenda nao declarada ----
D="$(_fresh)"
python3 - "$D/ADR-111-locked-corpus-governance.md" <<'PY'
import io, sys
p = sys.argv[1]
t = io.open(p, encoding="utf-8").read()
assert "amended_by: ADR-182\n" in t, "plant sem alvo"
io.open(p, "w", encoding="utf-8").write(t.replace("amended_by: ADR-182\n", "", 1))
PY
N="$(_errs "$D")"
[ "$N" -ge 1 ] && ok "RC-2 amended_by: sem a declaracao reciproca, o erro VOLTA ($N)" \
               || bad "RC-2 amended_by: nenhum erro — o skip nao depende do dado"
rm -rf "$D"

# --- RC-3: um ADR bullet-form perde o campo => 'missing Status' VOLTA -----
D="$(_fresh)"
python3 - "$D/ADR-163-hook-latency-gate-percentile-stability.md" <<'PY'
import io, re, sys
p = sys.argv[1]
t = io.open(p, encoding="utf-8").read()
t2 = re.sub(r"(?im)^[-*#\s]*\**\s*status\s*\**\s*:.*$", "", t, count=1)
assert t2 != t, "plant nao removeu o campo"
io.open(p, "w", encoding="utf-8").write(t2)
PY
OUT="$(python3 "$CHAIN" --adr-dir "$D" 2>&1 | grep -c 'missing `Status:` field' || true)"
[ "$OUT" -ge 1 ] && ok "RC-3 status: sem o campo, 'missing Status' VOLTA ($OUT)" \
                 || bad "RC-3 status: o gate de status ficou vacuo"
rm -rf "$D"

printf '\n  RED CONTROLS: %d ok, %d vacuo(s)\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
