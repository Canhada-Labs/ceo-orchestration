#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (PLAN-190 W1),
# derivada à mão do molde OWNER-PIN-SIGN.sh (S353) porque o toolkit
# compartilhado do PLAN-188 ainda não landou.
# OWNER-190-W1-SIGN.sh — verifica, assina e landa a W1 do PLAN-190 em UM passo.
#
#   bash .claude/plans/PLAN-190/w1/OWNER-190-W1-SIGN.sh            # real
#   bash .claude/plans/PLAN-190/w1/OWNER-190-W1-SIGN.sh --dry-run  # ensaio
#
# Ordem (nada é assinado antes de a bateria passar; o passo falível do GPG é
# o último antes do commit):
#   P0 pré-condições → 1/7 aplica o patch → 2/7 confere as registrações →
#   3/7 bateria (gates + as MESMAS suítes do CI, comparadas por CONJUNTO EXATO
#   de falhas contra a linha de base medida no main) → 4/7 preenche Anchor-SHA,
#   Patch-sha256 e Data no sentinel → 5/7 assina (um pinentry) → 6/7 stage
#   EXATO (touched ∪ {sentinel, .asc}) → 7/7 commit.
# NÃO faz push. Qualquer falha antes do commit desfaz TUDO o que o script
# fez: reverte o patch, restaura o sentinel a partir da cópia e remove a .asc.
# O --dry-run trabalha numa CÓPIA do sentinel e não assina.
# Se o GPG reclamar de pinentry:  export GPG_TTY=$(tty)
set -euo pipefail
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
cd "$(git rev-parse --show-toplevel)"
D=.claude/plans/PLAN-190/w1
SENT="$D/w1-approved.md"
ASC="$SENT.asc"
PATCH="$D/p190-w1.patch"
BASELINE="$D/suite-baseline.txt"
ORACLE=.claude/hooks/check_canonical_edit.py
CANON="
.claude/hooks/_lib/launch_ledger.py
.claude/hooks/check_workflow_launch.py
.claude/settings.json
templates/settings/settings.base.json
templates/settings/settings.user.json
"
APPLIED=0
SENT_TOUCHED=0
SIGN_STARTED=0
BAK=$(mktemp -d /tmp/p190w1.XXXXXX)
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
undo() {
  local done_what=""
  if [ "$APPLIED" = "1" ]; then
    git reset -q HEAD -- . 2>/dev/null
    if git apply -R --check "$PATCH" 2>/dev/null; then
      git apply -R "$PATCH"; done_what="$done_what patch-revertido"
    else
      printf 'reverter o patch à mão: git apply -R %s\n' "$PATCH" >&2; done_what="$done_what PATCH-NAO-REVERTIDO"
    fi
  fi
  if [ "$SENT_TOUCHED" = "1" ] && [ "$DRY" != "1" ]; then
    if [ -L "$SENT" ]; then
      printf 'sentinel virou symlink — restaure à mão a partir de %s/sentinel.orig.md\n' "$BAK" >&2; done_what="$done_what SENTINEL-NAO-RESTAURADO"
    else
      cp "$BAK/sentinel.orig.md" "$SENT"; done_what="$done_what sentinel-restaurado"
    fi
  fi
  if [ "$SIGN_STARTED" = "1" ] && [ "$DRY" != "1" ] && [ -f "$ASC" ]; then
    rm -- "$ASC"; done_what="$done_what asc-removida"
  fi
  printf '\ndesfeito:%s\n' "${done_what:- nada a desfazer}" >&2
}
trap 'rc=$?; if [ $rc -ne 0 ]; then undo; printf "(rc=%s) árvore conferível com: git status --short\n" "$rc" >&2; fi' EXIT

say "P0 pré-condições"
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
git remote -v | grep -q 'Canhada-Labs/ceo-orchestration' || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "HEAD != origin/main — pushe ou puxe antes"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "há modificação RASTREADA pendente"
[ ! -e "$ASC" ] || die "já existe $ASC — remova a assinatura antiga antes"
for f in "$SENT" "$PATCH" "$ORACLE" "$BASELINE"; do [ -f "$f" ] || die "ausente: $f"; done
git apply --check "$PATCH" || die "git apply --check FALHOU — a árvore divergiu do patch"
for f in $CANON; do
  v=$(python3 "$ORACLE" --is-canonical "$f" 2>/dev/null | awk '{print $2}')
  [ "$v" = "1" ] || die "$f NÃO é canônico (oráculo=$v) — revise o Scope"
done
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$BAK/touched"
awk '/^## Scope/{s=1; next} /^## /{s=0} s && /^- `/{sub(/^- `/, ""); sub(/`.*/, ""); print}' "$SENT" | sort -u > "$BAK/scope"
DIFF=$(comm -3 "$BAK/touched" "$BAK/scope")
[ -z "$DIFF" ] || die "touched ≠ Scope do sentinel:$(printf '\n   %s' $DIFF)"
# a linha de base das suítes vale para a árvore em que foi medida: entre a âncora dela e o HEAD
# só podem ter mudado materiais deste pacote — o diretório PLAN-190/ e os arquivos de plano
# PLAN-190-*.md (texto de plano não mascara falha: qualquer efeito aparece como falha NOVA abaixo)
B_ANCHOR=$(awk '/^# anchor: /{print $3; exit}' "$BASELINE")
git cat-file -e "${B_ANCHOR}^{commit}" 2>/dev/null || die "linha de base sem âncora válida — remeça: bash $D/measure-suite-baseline.sh"
git diff --name-only "$B_ANCHOR" HEAD > "$BAK/since-baseline"
OUTSIDE=$(awk '!/^\.claude\/plans\/PLAN-190\// && !/^\.claude\/plans\/PLAN-190-[^\/]*\.md$/' "$BAK/since-baseline")
[ -z "$OUTSIDE" ] || die "o main mudou fora do pacote desde a linha de base ($B_ANCHOR) — remeça: bash $D/measure-suite-baseline.sh$(printf '\n   %s' $OUTSIDE)"
awk '!/^#/ && NF' "$BASELINE" | sort -u > "$BAK/baseline-fails"
PATCH_SHA=$(shasum -a 256 "$PATCH" | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)
printf '   OK: main, sincronizado, árvore limpa, patch aplicável, %s paths = Scope, 5 canônicos\n' "$(wc -l < "$BAK/touched" | tr -d ' ')"
printf '   linha de base %s (%s falhas pré-existentes)\n' "$B_ANCHOR" "$(wc -l < "$BAK/baseline-fails" | tr -d ' ')"
printf '   Patch-sha256 = %s\n' "$PATCH_SHA"

say "1/7 aplicar o patch da sombra"
git apply "$PATCH" || die "git apply falhou"
APPLIED=1
[ -x .claude/hooks/check_workflow_launch.py ] || die "hook não é executável após o apply"

say "2/7 registrações"
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
printf '   2 registrações em cada um dos 3 settings\n'

say "3/7 bateria (gates + suítes do CI por conjunto exato de falhas)"
python3 -m py_compile .claude/hooks/_lib/launch_ledger.py .claude/hooks/check_workflow_launch.py .claude/scripts/ceo-launches.py scripts/build-plugin.py || die "py_compile"
python3 .claude/scripts/check-test-env-hygiene.py >/dev/null 2>&1 || die "test-env-hygiene reprovou"
python3 .claude/scripts/gen-settings-user-template.py --check >/dev/null 2>&1 || die "template user diverge da derivação"
python3 .claude/scripts/gen-command-skill-hook-map.py --check >/dev/null 2>&1 || die "mapa comando→skill→hook fora de sincronia"
python3 .claude/scripts/env-inventory-check.py --check >/dev/null 2>&1 || die "inventário de variáveis de ambiente com drift"
python3 .claude/scripts/check-active-hooks-executable.py >/dev/null 2>&1 || die "hook ativo não executável"
python3 .claude/scripts/check_contamination.py >/dev/null 2>&1 || die "contamination reprovou"
python3 scripts/build-plugin.py --check >/dev/null 2>&1 || die "build-plugin --check reprovou"
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >/dev/null 2>&1 || die "verify-counts reprovou"
python3 .claude/scripts/check-ceremony-script.py >"$BAK/lint.out" 2>&1 || { tail -12 "$BAK/lint.out" >&2; die "ceremony-lint reprovou"; }
bash .claude/scripts/validate-governance.sh >"$BAK/gov.out" 2>&1 || { tail -30 "$BAK/gov.out" >&2; die "validate-governance reprovou (log: $BAK/gov.out)"; }
awk '/Errors:   0/{ok=1} END{exit ok?0:1}' "$BAK/gov.out" || die "governance com erros"
printf '   gates OK; suítes do pytest.ini (paralela e serial, como o CI) — alguns minutos\n'
set +e
python3 -m pytest -n auto -m 'not serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider >"$BAK/suite-parallel.out" 2>&1
P_RC=$?
python3 -m pytest -m 'serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider >"$BAK/suite-serial.out" 2>&1
S_RC=$?
set -e
case "$P_RC" in 0|1) ;; *) die "passada paralela não terminou (rc=$P_RC) — log em $BAK/suite-parallel.out" ;; esac
case "$S_RC" in 0|1) ;; *) die "passada serial não terminou (rc=$S_RC) — log em $BAK/suite-serial.out" ;; esac
awk '$1=="FAILED" || $1=="ERROR" {print $2}' "$BAK/suite-parallel.out" "$BAK/suite-serial.out" | sort -u > "$BAK/now-fails"
comm -13 "$BAK/baseline-fails" "$BAK/now-fails" > "$BAK/new-fails"
: > "$BAK/real-new-fails"
while IFS= read -r test_id; do
  [ -n "$test_id" ] || continue
  # uma falha nova é rerrodada ISOLADA uma vez: instabilidade conhecida sob xdist passa sozinha
  if python3 -m pytest "$test_id" -q -p no:cacheprovider >"$BAK/rerun.out" 2>&1; then
    printf '   instável (passou isolada): %s\n' "$test_id"
  else
    printf '%s\n' "$test_id" >> "$BAK/real-new-fails"
  fi
done < "$BAK/new-fails"
[ ! -s "$BAK/real-new-fails" ] || die "falhas NOVAS em relação à linha de base, confirmadas isoladas (logs em $BAK):$(printf '\n   %s' $(cat "$BAK/real-new-fails"))"
GONE=$(comm -23 "$BAK/baseline-fails" "$BAK/now-fails")
PASSED=$(awk 'match($0, /[0-9]+ passed/) { v = substr($0, RSTART, RLENGTH) } END { print v }' "$BAK/suite-parallel.out")
printf '   suítes: %s na paralela; falhas = subconjunto das %s da linha de base\n' "$PASSED" "$(wc -l < "$BAK/baseline-fails" | tr -d ' ')"
[ -z "$GONE" ] || printf '   nota: falhas da linha de base que agora passam:%s\n' "$(printf '\n     %s' $GONE)"

say "4/7 Anchor-SHA, Patch-sha256 e Data no sentinel"
if [ "$DRY" = "1" ]; then
  cp "$SENT" "$BAK/sentinel.md"; SENT="$BAK/sentinel.md"; ASC="$SENT.asc"
else
  [ ! -L "$SENT" ] || die "sentinel é symlink"
  cp "$SENT" "$BAK/sentinel.orig.md"
  SENT_TOUCHED=1
fi
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
awk -v a="Anchor-SHA: $HEAD_SHA" -v b="Patch-sha256: $PATCH_SHA" '$0==a{x=1} $0==b{y=1} END{exit (x&&y)?0:1}' "$SENT" || die "Anchor-SHA/Patch-sha256 não gravaram"
printf '   Anchor-SHA = %s\n' "$HEAD_SHA"

say "5/7 assinar o sentinel (pinentry)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura\n'
else
  SIGN_STARTED=1
  gpg --armor --detach-sign "$SENT" || die "assinatura falhou"
  gpg --verify "$ASC" "$SENT" || die "a assinatura não verifica"
fi

say "6/7 stage EXATO + conferência touched ∪ {sentinel, .asc}"
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

say "7/7 commit (nunca abre editor)"
git commit -q -F - <<MSG
ceremony(PLAN-190 W1): ledger de lançamento de Workflow + guard de retomada

Hook PreToolUse/PostToolUse na tool Workflow grava o manifesto de cada
chamada (sha256 e snapshot dos bytes do script, args literais com ausente
!= null e sem truncamento, resumeFromRunId; revisão git do cwd depois, com
orçamento de 1,2 s; args também na ordem original das chaves) e vincula o
run id devolvido (rótulo Run ID do harness; por tool_use_id; sem ele, só com
um único lançamento pendente e não bloqueado na sessão; o resto vira orphan).
Retomada sobre args diferentes do manifesto vinculado por tool_use_id ou
manual, e validado, é BLOQUEADA com motivo só de contagens que nomeia a rota
da mudança deliberada;
script diferente com args iguais é advisory (CEO_WORKFLOW_SCRIPT_GUARD=enforce
bloqueia); com args iguais, hash indisponível é inconclusivo; registro
inconsistente ou exceção no guard são inconclusivos registrados; vínculo
heurístico nunca sustenta bloqueio. Override numa rota só, carregada pela
chamada ou pelo processo e nunca por estado em disco: description com o
prefixo exato CEO_WORKFLOW_RESUME_FORCE: e um motivo, ou
CEO_WORKFLOW_RESUME_FORCE=1 no ambiente; registrado como mismatch_forced e
anunciado ao modelo e ao usuário. CEO_WORKFLOW_RESUME_GUARD=0 põe o guard em advisory mantendo o
ledger; CEO_WORKFLOW_LEDGER=0 desliga. Fail-open em infraestrutura.
Registrações no settings do framework e no template base (user derivado, com
o hook em blocking_inclusions e na lista ratificada do teste do template);
o build do plugin leva o CLI de recuperação junto com o guard. Contagens
59->60 hooks, 48->49 ligados, 50->52 registrações, 71->72 _lib em 10 docs.

Baseline medida num consumidor (S354): 15,5 % das fases iniciadas sem
resultado, 16 % dos starts reexecuções; a classe fechada é a retomada sobre
entradas diferentes sem o operador saber (11 regressões por args de memória;
12/12 retomadas com args exatos). Revisão: debate r1 (3x ADJUST, PROCEED);
rail Codex r1-r5 NO-GO com 7, 3, 2, 4 e 3 achados; troca de arquitetura do
override decidida pelo Owner após r4; revisão adversarial multi-lente com
dupla refutação e crítico de completude; fatos do substrato sondados no
harness; r6 sobre os bytes finais.

Sentinel: $SENT (assinado, Anchor-SHA $HEAD_SHA, Patch-sha256 $PATCH_SHA)
Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG
APPLIED=0; SENT_TOUCHED=0; SIGN_STARTED=0
trap - EXIT
printf '\nLANDADO em %s. Push é decisão sua: git push origin main\n' "$(git rev-parse --short HEAD)"
