#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (PLAN-190 W1),
# derivada à mão do molde OWNER-PIN-SIGN.sh (S353) porque o toolkit
# compartilhado do PLAN-188 ainda não landou.
# OWNER-190-W1-SIGN.sh — assina e landa a W1 do PLAN-190 em UM passo.
#
#   bash .claude/plans/PLAN-190/w1/OWNER-190-W1-SIGN.sh            # real
#   bash .claude/plans/PLAN-190/w1/OWNER-190-W1-SIGN.sh --dry-run  # ensaio
#
# O que faz: P0 pré-condições → 1/6 preenche Anchor-SHA, Patch-sha256 e Data
# no sentinel → 2/6 assina (um pinentry) → 3/6 `git apply` do patch da sombra
# → 4/6 bateria → 5/6 stage EXATO (touched ∪ {sentinel, .asc}) → 6/6 commit.
# NÃO faz push. Qualquer falha após o apply reverte o patch (`git apply -R`)
# e limpa o index; o sentinel do ensaio é uma CÓPIA (o material não suja).
# Se o GPG reclamar de pinentry:  export GPG_TTY=$(tty)
set -euo pipefail
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
cd "$(git rev-parse --show-toplevel)"
D=.claude/plans/PLAN-190/w1
SENT="$D/w1-approved.md"
ASC="$SENT.asc"
PATCH="$D/p190-w1.patch"
ORACLE=.claude/hooks/check_canonical_edit.py
CANON="
.claude/hooks/_lib/launch_ledger.py
.claude/hooks/check_workflow_launch.py
.claude/settings.json
templates/settings/settings.base.json
templates/settings/settings.user.json
"
APPLIED=0
BAK=$(mktemp -d /tmp/p190w1.XXXXXX)
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
undo() {
  if [ "$APPLIED" = "1" ]; then
    git reset -q HEAD -- . 2>/dev/null
    if git apply -R --check "$PATCH" 2>/dev/null; then git apply -R "$PATCH"; else printf 'reverter o patch à mão: git apply -R %s\n' "$PATCH" >&2; fi
  fi
}
trap 'rc=$?; [ $rc -ne 0 ] && { undo; printf "\nárvore REVERTIDA (rc=%s). Backup do sentinel em %s\n" "$rc" "$BAK" >&2; }' EXIT

say "P0 pré-condições"
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
git remote -v | grep -q 'Canhada-Labs/ceo-orchestration' || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "HEAD != origin/main — pushe ou puxe antes"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "há modificação RASTREADA pendente"
for f in "$SENT" "$PATCH" "$ORACLE"; do [ -f "$f" ] || die "ausente: $f"; done
git apply --check "$PATCH" || die "git apply --check FALHOU — a árvore divergiu do patch"
for f in $CANON; do
  v=$(python3 "$ORACLE" --is-canonical "$f" 2>/dev/null | awk '{print $2}')
  [ "$v" = "1" ] || die "$f NÃO é canônico (oráculo=$v) — revise o Scope"
done
# touched(patch) tem de ser EXATAMENTE o bloco Scope do sentinel
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$BAK/touched"
awk '/^## Scope/{s=1; next} /^## /{s=0} s && /^- `/{sub(/^- `/, ""); sub(/`.*/, ""); print}' "$SENT" | sort -u > "$BAK/scope"
DIFF=$(comm -3 "$BAK/touched" "$BAK/scope")
[ -z "$DIFF" ] || die "touched ≠ Scope do sentinel:$(printf '\n   %s' $DIFF)"
PATCH_SHA=$(shasum -a 256 "$PATCH" | awk '{print $1}')
printf '   OK: main, sincronizado, árvore limpa, patch aplicável, %s paths = Scope, 5 canônicos\n' "$(wc -l < "$BAK/touched" | tr -d ' ')"
printf '   Patch-sha256 = %s\n' "$PATCH_SHA"

say "1/6 Anchor-SHA, Patch-sha256 e Data no sentinel"
HEAD_SHA=$(git rev-parse HEAD)
if [ "$DRY" = "1" ]; then cp "$SENT" "$BAK/sentinel.md"; SENT="$BAK/sentinel.md"; ASC="$SENT.asc"; fi
python3 - "$SENT" "$HEAD_SHA" "$PATCH_SHA" "$(date -u +%Y-%m-%d)" <<'PY'
import sys, pathlib, re
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
for key, val in (("Anchor-SHA", sys.argv[2]), ("Patch-sha256", sys.argv[3]), ("Data", sys.argv[4])):
    t2 = re.sub(r"^%s:.*$" % key, "%s: %s" % (key, val), t, count=1, flags=re.M)
    if t2 == t and not re.search(r"^%s: %s$" % (key, re.escape(val)), t, flags=re.M):
        raise SystemExit("linha %s não encontrada" % key)
    t = t2
p.write_text(t, encoding="utf-8")
PY
grep -q "Anchor-SHA: $HEAD_SHA" "$SENT" || die "Anchor-SHA não gravou"
grep -q "Patch-sha256: $PATCH_SHA" "$SENT" || die "Patch-sha256 não gravou"
printf '   Anchor-SHA = %s\n' "$HEAD_SHA"

say "2/6 assinar o sentinel (pinentry)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura\n'
else
  [ -f "$ASC" ] && rm "$ASC"
  gpg --armor --detach-sign "$SENT" || die "assinatura falhou"
  gpg --verify "$ASC" "$SENT" || die "a assinatura não verifica"
fi

say "3/6 aplicar o patch da sombra"
git apply "$PATCH" || die "git apply falhou"
APPLIED=1
[ -x .claude/hooks/check_workflow_launch.py ] || die "hook não é executável após o apply"
for f in .claude/settings.json templates/settings/settings.base.json templates/settings/settings.user.json; do
  # conta REGISTRAÇÕES (entradas Pre/Post na tool Workflow cujo comando termina no hook), não
  # ocorrências do nome: o template `user` também nomeia o hook em `_derivation.blocking_inclusions`
  n=$(python3 - "$f" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
n = 0
for ev in ("PreToolUse", "PostToolUse"):
    for e in d.get("hooks", {}).get(ev, []):
        if e.get("matcher") == "Workflow":
            n += sum(1 for h in e.get("hooks", []) if str(h.get("command", "")).endswith("check_workflow_launch.py"))
print(n)
PY
)
  [ "$n" = "2" ] || die "$f: esperava 2 registrações do hook (Pre+Post na tool Workflow), achei $n"
done
printf '   aplicado: hook executável, 2 registrações em cada um dos 3 settings\n'

say "4/6 bateria"
python3 -m py_compile .claude/hooks/_lib/launch_ledger.py .claude/hooks/check_workflow_launch.py .claude/scripts/ceo-launches.py || die "py_compile"
python3 -m pytest .claude/hooks/tests/test_check_workflow_launch.py tests/unit/test_launch_ledger.py .claude/hooks/tests/test_template_dogfood_parity.py .claude/scripts/tests/test_gen_command_skill_hook_map.py -q -p no:cacheprovider >/tmp/p190-tests.out 2>&1 || { tail -20 /tmp/p190-tests.out >&2; die "testes da W1 reprovaram"; }
python3 .claude/scripts/check-test-env-hygiene.py >/dev/null 2>&1 || die "test-env-hygiene reprovou"
python3 .claude/scripts/gen-settings-user-template.py --check >/dev/null 2>&1 || die "template user diverge da derivação"
python3 .claude/scripts/check-active-hooks-executable.py >/dev/null 2>&1 || die "hook ativo não executável"
python3 .claude/scripts/check_contamination.py >/dev/null 2>&1 || die "contamination reprovou"
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >/dev/null 2>&1 || die "verify-counts reprovou"
python3 .claude/scripts/check-ceremony-script.py >/tmp/p190-lint.out 2>&1 || { tail -12 /tmp/p190-lint.out >&2; die "ceremony-lint reprovou"; }
bash .claude/scripts/validate-governance.sh >/tmp/p190-gov.out 2>&1 || { tail -30 /tmp/p190-gov.out >&2; die "validate-governance reprovou (log: /tmp/p190-gov.out)"; }
grep -q 'Errors:   0' /tmp/p190-gov.out || die "governance com erros"
PASSED=$(awk 'match($0, /[0-9]+ passed/) { v = substr($0, RSTART, RLENGTH) } END { print v }' /tmp/p190-tests.out)
printf '   testes (%s: e2e, unit, paridade, mapa), higiene, template user, hooks executáveis, contamination, counts, ceremony-lint, governance 0 erros\n' "$PASSED"

say "5/6 stage EXATO + conferência touched ∪ {sentinel, .asc}"
xargs git add -- < "$BAK/touched"
[ "$DRY" = "1" ] || git add -- "$SENT" "$ASC"
git diff --cached --name-only | sort > "$BAK/staged"
{ cat "$BAK/touched"; [ "$DRY" = "1" ] || printf '%s\n%s\n' "$SENT" "$ASC"; } | sort -u > "$BAK/expected"
EXTRA=$(comm -3 "$BAK/staged" "$BAK/expected")
[ -z "$EXTRA" ] || die "conjunto staged ≠ patch + sentinel:$(printf '\n   %s' $EXTRA)"
sed 's/^/   /' "$BAK/staged"
if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada assinado nem commitado; revertendo o patch"
  undo; APPLIED=0
  printf '\nEnsaio OK. Rode sem --dry-run para valer.\n'
  trap - EXIT; exit 0
fi

say "6/6 commit (nunca abre editor)"
git commit -q -F - <<MSG
ceremony(PLAN-190 W1): ledger de lançamento de Workflow + guard de retomada
Hook PreToolUse/PostToolUse na tool Workflow grava o manifesto ANTES do
despacho (sha256 e snapshot dos bytes do script, args literais com ausente
!= null e sem truncamento, resumeFromRunId; revisão git do cwd depois, com
orçamento de 1,2 s) e vincula o run id devolvido (por tool_use_id; sem ele,
só com um único lançamento pendente na sessão, nunca uma tentativa
bloqueada; o resto vira orphan). Retomada sobre args diferentes do manifesto
vinculado por tool_use_id ou manual é BLOQUEADA com motivo só de contagens
(as chaves ficam no manifesto); script diferente com args iguais é advisory
(CEO_WORKFLOW_SCRIPT_GUARD=enforce bloqueia); hash indisponível é
inconclusivo; vínculo heurístico nunca sustenta bloqueio. Uma rota de
override para todo bloqueio: CEO_WORKFLOW_RESUME_FORCE=1 no ambiente, ou o
token one-shot de ceo-launches.py force com motivo (validado por um esquema,
até 30 min, gasto só ao liberar), registrado como mismatch_forced e
anunciado. CEO_WORKFLOW_RESUME_GUARD=0 põe o guard em advisory mantendo o
ledger; CEO_WORKFLOW_LEDGER=0 desliga. Fail-open em infraestrutura.
Registrações no settings do framework e no template base (user derivado,
com o hook em blocking_inclusions). Contagens 59->60 hooks, 48->49 ligados,
50->52 registrações, 71->72 _lib em 10 docs.
Baseline medida num consumidor (S354): 15,5 % das fases iniciadas sem
resultado, 16 % dos starts reexecuções; a classe fechada é a retomada sobre
entradas diferentes sem o operador saber (11 regressões por args de memória;
12/12 retomadas com args exatos).
Revisão: debate r1 (3x ADJUST, PROCEED); rail Codex r1-r3 NO-GO com 7, 3 e
2 achados, todos curados com regressões; r4 sobre os bytes finais.
Sentinel: $SENT (assinado, Anchor-SHA $HEAD_SHA, Patch-sha256 $PATCH_SHA)
Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
APPLIED=0
trap - EXIT
printf '\nLANDADO em %s. Push é decisão sua: git push origin main\n' "$(git rev-parse --short HEAD)"
