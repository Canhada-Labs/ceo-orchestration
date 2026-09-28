#!/usr/bin/env bash
# CEREMONY-LINT: handwritten-exception: cerimônia de UM uso (PLAN-193 W4b, cura do FN-04),
# clonada do molde OWNER-190-W1-SIGN.sh (PLAN-190 W1, landado em 075beed9) — o último
# SIGN/LAND que tocou estes mesmos arquivos. O que muda em relação ao molde, declarado:
#  (1) o P0 lê o registro da ÚLTIMA rodada do rail (rail-round-N.md, N <= 3, contíguos) e
#      exige que ele nomeie o sha256 deste patch com veredito APPROVE ou DECLARED-P2; o hash
#      desse registro entra no sentinel (Rail-Record-sha256) antes da assinatura;
#  (2) o P0 pina a PRÉ-imagem (o blob de cada caminho tocado no HEAD = o `index` do patch) e o
#      passo 2 confere a PÓS-imagem: os bytes que landam são os que o rail revisou;
#  (3) não há linha de base pré-medida (a árvore em que isto landa só existe na manhã do land):
#      cada falha das suítes é rerrodada ISOLADA com o patch, até 3 vezes (passar em alguma é
#      nota: instável), e, se falhar nas 3, uma vez num worktree
#      destacado do HEAD (a árvore sem o patch) — se lá também falha (pytest rc 1) é nota
#      (pré-existente); qualquer outro resultado sem o patch (passa, não existe, erro) reprova.
#      Um gate de corpus que reprova com o patch é rodado de novo nesse worktree: reprovar lá
#      também é nota; passar lá reprova o SIGN;
#  (4) INT/TERM/HUP passam pelo mesmo desfazer do EXIT; origin/main precisa estar CONTIDO no
#      HEAD (commits locais de cerimônias anteriores da mesma manhã são aceitos);
#  (5) a assinatura usa --local-user com a chave secreta cuja impressão digital está em
#      .claude/sentinel-signers.txt e é conferida contra esse allowlist (GOODSIG + VALIDSIG);
#  (6) o HEAD é reconferido depois da bateria e antes do commit, e os blobs dos caminhos tocados
#      são reconferidos depois da bateria e no índice depois do stage.
#
# OWNER-FN04-SIGN.sh — verifica, assina e landa a cura FN-04 em UM passo.
#
#   bash .claude/plans/PLAN-193/wave-fn04/OWNER-FN04-SIGN.sh                 # real (terminal interativo)
#   bash .claude/plans/PLAN-193/wave-fn04/OWNER-FN04-SIGN.sh --dry-run       # ensaio: não assina, não commita
#   bash .claude/plans/PLAN-193/wave-fn04/OWNER-FN04-SIGN.sh --check-base REV
#        # só leitura, em segundos: a base pinada do patch (o blob pré-imagem de cada caminho)
#        # é a de REV? rc 0 = o patch aplica sobre REV; rc 1 = nomeia o caminho que difere
#
# Ordem (nada é assinado antes de a bateria passar; o passo falível do GPG é o último antes do
# commit): P0 pré-condições + chave de assinatura + registro do rail → 1/7 aplica o patch → 2/7
# bytes aplicados = bytes revisados → 3/7 bateria (gates de corpus + suítes do pytest.ini com a
# divisão de marcadores do CI, falhas julgadas contra a árvore sem o patch) → 4/7 preenche
# Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data no sentinel → 5/7 assina (um pinentry) →
# 6/7 stage EXATO (touched ∪ {sentinel, .asc}) → 7/7 commit.
# NÃO faz push. Qualquer falha (ou Ctrl-C / TERM / HUP) antes do commit desfaz TUDO o que o
# script fez: reverte o patch, restaura o sentinel, remove a .asc e o worktree da base. Os logs
# ficam no diretório temporário que a falha nomeia. Rodar de novo depois de um abort é seguro.
# A bateria roda as suítes do pytest.ini com a divisão de marcadores do CI (paralela
# 'not serial' + serial) — um conjunto MAIOR que o dos jobs do CI; a duração não foi medida nesta
# árvore. O --dry-run é opcional (repete a bateria inteira; o modo real já desfaz tudo numa
# falha). Fique no terminal: o pinentry vem DEPOIS da bateria, e um pinentry que expira desfaz tudo.
# Uma falha nomeada «falhas NOVAS» pode vir de estado da árvore viva (arquivos ignorados, dist/,
# .claude/state/) que o worktree limpo da base não tem: confira o log; a saída é rodar de novo,
# nunca editar o patch.
# Se o GPG reclamar de pinentry:  export GPG_TTY=$(tty)
set -euo pipefail
DRY=0
CHECK_BASE=""
case "${1:-}" in
  "") : ;;
  --dry-run) DRY=1 ;;
  --check-base) CHECK_BASE="${2:-HEAD}" ;;
  *) printf 'uso: bash %s [--dry-run | --check-base [REV]]\n' "$0" >&2; exit 2 ;;
esac
# A raiz resolve pela LOCALIZAÇÃO do script, nunca pelo cwd: o Owner pode chamar de qualquer lugar.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel)"
cd "$ROOT"
D=.claude/plans/PLAN-193/wave-fn04
SENT=.claude/plans/PLAN-193/wave-fn04-approved.md
ASC="$SENT.asc"
PATCH="$D/fn04.patch"
SELF="$D/OWNER-FN04-SIGN.sh"
ORACLE=.claude/hooks/check_canonical_edit.py
SIGNERS=.claude/sentinel-signers.txt
GPG_VERIFY_LIB=.claude/hooks/_lib/gpg_verify.py
CANON="
.claude/hooks/_lib/launch_ledger.py
.claude/hooks/check_workflow_launch.py
"
RAIL_MAX_ROUNDS=3
APPLIED=0
SENT_TOUCHED=0
SIGN_STARTED=0
BASE_WT=""
BAK=$(mktemp -d "${TMPDIR:-/tmp}/fn04-sign.XXXXXX")
die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n===== %s\n' "$*"; }
patch_blobs() {  # arquivo de saída — uma linha "<caminho> <blob pré-imagem> <blob pós-imagem>" por caminho do patch
  awk '/^diff --git /{p=$3; sub(/^a\//, "", p)} /^index /{split($2, h, /\.\./); print p, h[1], h[2]}' "$PATCH" > "$1"
}

if [ -n "$CHECK_BASE" ]; then
  # Só leitura: nada é aplicado, nada é escrito na árvore. Para a land livre que traz a lane B
  # (a pré-imagem do patch) conferir, ANTES de landar, que os bytes dela são os que este pacote pinou.
  [ -f "$PATCH" ] || die "ausente: $PATCH"
  git rev-parse --verify --quiet "$CHECK_BASE^{commit}" >/dev/null || die "revisão desconhecida: $CHECK_BASE"
  patch_blobs "$BAK/blobs"
  [ -s "$BAK/blobs" ] || die "o patch não tem linhas index"
  CB_BAD=0
  while read -r p old new; do
    cur=$(git rev-parse --verify --quiet "$CHECK_BASE:$p") || cur="(ausente)"
    if [ "${#old}" -eq 40 ] && [ "$cur" = "$old" ]; then
      printf '   igual: %s\n' "$p"
    else
      printf '   DIFERE: %s (em %s: %s; o patch espera %s)\n' "$p" "$CHECK_BASE" "$cur" "$old"
      CB_BAD=1
    fi
  done < "$BAK/blobs"
  rm -f "$BAK/blobs"
  rmdir "$BAK"
  if [ "$CB_BAD" = "1" ]; then
    printf '\nFAIL: a base pinada do FN-04 não é a de %s — o fn04.patch não aplica ali. Re-derivar o\n' "$CHECK_BASE" >&2
    printf 'pacote pede uma rodada de rail além da regra de parada (decisão do Owner); não lande bytes\n' >&2
    printf 'diferentes nesses caminhos sem essa decisão.\n' >&2
    exit 1
  fi
  printf '\nOK: a base pinada do FN-04 é a de %s (o fn04.patch aplica ali).\n' "$CHECK_BASE"
  exit 0
fi
remove_base_wt() {
  if [ -n "$BASE_WT" ]; then
    if [ -d "$BASE_WT" ]; then
      git worktree remove --force "$BASE_WT" >/dev/null 2>&1 \
        || printf 'remova à mão: git worktree remove --force %s\n' "$BASE_WT" >&2
    fi
    git worktree prune >/dev/null 2>&1 || :
    BASE_WT=""
  fi
}
undo() {
  set +e
  local done_what=""
  remove_base_wt
  if [ "$APPLIED" = "1" ]; then
    git reset -q HEAD -- . 2>/dev/null
    if git apply -R --check "$PATCH" 2>/dev/null; then
      git apply -R "$PATCH"; done_what="$done_what patch-revertido"
    else
      done_what="$done_what PATCH-NAO-REVERTIDO"
    fi
    # Um caminho tocado que mudou depois do apply fica diferente do HEAD — reverta o patch limpo ou
    # não. O P0 exigiu árvore rastreada limpa, então a pré-imagem é o HEAD; quem descarta é você.
    if ! xargs git diff --quiet HEAD -- < "$BAK/touched" 2>/dev/null; then
      printf 'caminhos do patch ainda diferem do HEAD (mudaram depois do apply). Confira com «git diff» e\n' >&2
      printf 'restaure a pré-imagem com: git checkout HEAD -- %s\n' "$(tr '\n' ' ' < "$BAK/touched")" >&2
      done_what="$done_what CAMINHOS-DO-PATCH-AINDA-SUJOS"
    fi
    APPLIED=0
  fi
  if [ "$SENT_TOUCHED" = "1" ] && [ "$DRY" != "1" ]; then
    git reset -q HEAD -- "$SENT" 2>/dev/null
    if [ -L "$SENT" ]; then
      printf 'sentinel virou symlink — restaure à mão a partir de %s/sentinel.orig.md\n' "$BAK" >&2; done_what="$done_what SENTINEL-NAO-RESTAURADO"
    else
      cp "$BAK/sentinel.orig.md" "$SENT"; done_what="$done_what sentinel-restaurado"
    fi
    SENT_TOUCHED=0
  fi
  if [ "$SIGN_STARTED" = "1" ] && [ "$DRY" != "1" ]; then
    git reset -q HEAD -- "$ASC" 2>/dev/null
    if [ -f "$ASC" ]; then rm -- "$ASC"; done_what="$done_what asc-removida"; fi
    SIGN_STARTED=0
  fi
  printf '\ndesfeito:%s\n' "${done_what:- nada a desfazer}" >&2
}
# A chave de assinatura e a conferência do signatário usam o allowlist commitado e a biblioteca de
# verificação do próprio repositório (_lib/gpg_verify.py: GOODSIG + VALIDSIG, impressão digital no
# allowlist):
#   signer_tool pick                     -> imprime a impressão digital da chave SECRETA a usar
#   signer_tool verify <arquivo> <.asc>  -> imprime a impressão digital aceita
signer_tool() {
  python3 - "$ROOT" "$GPG_VERIFY_LIB" "$SIGNERS" "$@" <<'PY'
import importlib.util
import subprocess
import sys
from pathlib import Path

root, glib, allow, mode = sys.argv[1:5]
rest = sys.argv[5:]
spec = importlib.util.spec_from_file_location("gpg_verify_fn04", str(Path(root) / glib))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
if mode == "pick":
    fprs, err = g.load_allowlist(Path(root) / allow)
    if err:
        raise SystemExit("allowlist de signatários inválido (%s): %s" % (allow, err))
    out = subprocess.run(["gpg", "--batch", "--with-colons", "--list-secret-keys"],
                         capture_output=True, text=True).stdout
    want = False
    for line in out.splitlines():
        f = line.split(":")
        if f[0] == "sec":
            want = True
        elif f[0] == "fpr" and want:
            want = False
            fpr = g.normalise_fpr(f[9]) if len(f) > 9 else ""
            if fpr and fpr in fprs:
                print(fpr)
                raise SystemExit(0)
    raise SystemExit("nenhuma chave secreta deste GNUPGHOME está em %s" % allow)
if mode == "verify" and len(rest) == 2:
    ok, fpr, reason = g.verify_detached(Path(rest[0]), Path(rest[1]), allowlist_path=Path(root) / allow)
    if not ok:
        raise SystemExit("assinatura recusada: %s" % reason)
    print(fpr)
    raise SystemExit(0)
raise SystemExit("uso interno inválido: %s" % " ".join([mode] + rest))
PY
}
on_exit() {
  # Os dois caminhos de sucesso desarmam este trap antes de sair; então TODA execução dele é um
  # término anormal — inclusive com rc 0: no bash 3.2, um erro de expansão (set -u) dentro de uma
  # lista `a && b || c` encerra o shell com status 0. Desfaz sempre e nunca sai com 0.
  local rc=$?
  undo
  [ "$rc" -ne 0 ] || rc=1
  printf '(rc=%s) abortado; logs em %s; árvore conferível com: git status --short\n' "$rc" "$BAK" >&2
  exit "$rc"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

say "P0 pré-condições"
[ "$DRY" = "1" ] || [ -t 0 ] || die "sem TTY — o pinentry precisa de terminal interativo (rode num terminal, não por pipe)"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "não está em main"
git remote -v | grep -q 'Canhada-Labs/ceo-orchestration' || die "remote inesperado"
git fetch --quiet origin main || die "git fetch falhou"
git merge-base --is-ancestor origin/main HEAD || die "HEAD não contém origin/main (atrás ou divergente) — puxe antes"
AHEAD=$(git rev-list --count origin/main..HEAD)
# Um worktree da base que uma execução anterior INTERROMPIDA (kill -9, queda) deixou é deste script
# (um diretório fn04-sign.*/base-wt que só ele cria): removido antes de começar.
git worktree list --porcelain | awk '/^worktree /{print substr($0, 10)}' > "$BAK/worktrees"
while IFS= read -r wt; do
  case "$wt" in
    */fn04-sign.*/base-wt)
      printf '   removendo o worktree da base de uma execução anterior interrompida: %s\n' "$wt"
      git worktree remove --force "$wt" >/dev/null 2>&1 \
        || printf '   (não removido — depois: git worktree remove --force %s)\n' "$wt" ;;
  esac
done < "$BAK/worktrees"
git worktree prune >/dev/null 2>&1 || :
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  git status --short --untracked-files=no >&2
  printf 'Se isto sobrou de uma execução INTERROMPIDA deste script (kill -9, queda):\n' >&2
  printf '  git reset -q HEAD -- . && git apply -R %s   (se o patch estiver aplicado)\n' "$PATCH" >&2
  printf '  git checkout -- %s ; rm -f %s\n' "$SENT" "$ASC" >&2
  die "há modificação RASTREADA pendente"
fi
[ ! -e "$ASC" ] || die "já existe $ASC — remova a assinatura antiga antes (rm $ASC)"
for f in "$SENT" "$PATCH" "$ORACLE" "$SELF" "$SIGNERS" "$GPG_VERIFY_LIB"; do [ -f "$f" ] || die "ausente: $f"; done
for f in "$SENT" "$PATCH" "$SELF" "$SIGNERS" "$GPG_VERIFY_LIB"; do
  git ls-files --error-unmatch -- "$f" >/dev/null 2>&1 || die "$f não está commitado — lande os materiais do pacote (commit livre) antes"
done
[ ! -L "$SENT" ] || die "sentinel é symlink"
for k in Patch-sha256 Rail-Record-sha256 Anchor-SHA Data; do
  awk -v k="$k" '$0 == k ": TO-FILL-BY-SIGN" {n++} END {exit n == 1 ? 0 : 1}' "$SENT" \
    || die "o sentinel não tem exatamente uma linha '$k: TO-FILL-BY-SIGN' — ele já foi preenchido?"
done
command -v gpg >/dev/null 2>&1 || die "gpg ausente"
# A chave é escolhida ANTES da bateria (também no --dry-run): sem chave do allowlist, a falha vem
# agora, não depois de 15 minutos.
SIGN_KEY=$(signer_tool pick) || die "sem chave secreta do allowlist $SIGNERS neste GNUPGHOME"
if [ "$DRY" != "1" ]; then
  GPG_TTY=$(tty) || die "não consegui ler o terminal (tty) para o GPG_TTY"
  export GPG_TTY
fi
python3 -m pytest --version >/dev/null 2>&1 || die "pytest ausente (python3 -m pip install 'pytest==8.*')"
python3 -c 'import xdist' >/dev/null 2>&1 || die "pytest-xdist ausente (python3 -m pip install pytest-xdist) — as suítes rodam como no CI"
git apply --check "$PATCH" || die "git apply --check FALHOU — a árvore divergiu do patch"
patch_blobs "$BAK/blobs"
git apply --numstat "$PATCH" | awk '{print $3}' | sort -u > "$BAK/touched"
awk '{print $1}' "$BAK/blobs" | sort -u | cmp -s - "$BAK/touched" || die "as linhas index do patch não cobrem exatamente os caminhos tocados"
while read -r p old new; do
  [ "${#old}" -eq 40 ] && [ "${#new}" -eq 40 ] || die "o patch não foi gerado com --full-index ($p)"
  cur=$(git rev-parse "HEAD:$p" 2>/dev/null) || die "$p não existe no HEAD"
  [ "$cur" = "$old" ] || die "a base de $p mudou desde a montagem do pacote (HEAD tem $cur, o patch espera $old) — o pacote precisa ser re-derivado sobre este HEAD"
done < "$BAK/blobs"
: > "$BAK/canon-now"
while read -r f; do
  v=$(python3 "$ORACLE" --is-canonical "$f" 2>/dev/null | awk '{print $2}')
  case "$v" in
    1) printf '%s\n' "$f" >> "$BAK/canon-now" ;;
    0) : ;;
    *) die "o oráculo não respondeu para $f (saída: '$v')" ;;
  esac
done < "$BAK/touched"
printf '%s\n' $CANON | sort -u > "$BAK/canon-expected"
sort -u "$BAK/canon-now" | cmp -s - "$BAK/canon-expected" \
  || die "os caminhos canônicos que o patch toca ≠ os declarados:$(printf '\n   %s' $(comm -3 "$BAK/canon-expected" "$BAK/canon-now"))"
awk '/^## Scope/{s=1; next} /^## /{s=0} s && /^- `/{sub(/^- `/, ""); sub(/`.*/, ""); print}' "$SENT" | sort -u > "$BAK/scope"
DIFF=$(comm -3 "$BAK/touched" "$BAK/scope")
[ -z "$DIFF" ] || die "touched ≠ Scope do sentinel:$(printf '\n   %s' $DIFF)"
PATCH_SHA=$(shasum -a 256 "$PATCH" | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

say "P0 registro do rail"
LAST=0
n=1
while [ -f "$D/rail-round-$n.md" ]; do LAST=$n; n=$((n + 1)); done
[ "$LAST" -ge 1 ] || die "nenhum registro de rail ($D/rail-round-1.md)"
NREC=$(find "$D" -maxdepth 1 -name 'rail-round-*.md' | wc -l | tr -d ' ')
[ "$NREC" = "$LAST" ] || die "registros de rail não contíguos ($NREC arquivos; contíguos de 1 a $LAST)"
[ "$LAST" -le "$RAIL_MAX_ROUNDS" ] || die "$LAST rodadas de rail passam da regra de parada pré-registrada ($RAIL_MAX_ROUNDS)"
REC="$D/rail-round-$LAST.md"
git ls-files --error-unmatch -- "$REC" >/dev/null 2>&1 || die "$REC não está commitado"
field() { awk -v k="$1" 'index($0, k ": ") == 1 {v = substr($0, length(k) + 3); n++} END {if (n != 1) exit 3; print v}' "$REC"; }
R_ROUND=$(field Rail-Round) || die "$REC: linha Rail-Round ausente ou repetida"
R_SUBJ=$(field Rail-Subject-sha256) || die "$REC: linha Rail-Subject-sha256 ausente ou repetida"
R_VERD=$(field Rail-Verdict) || die "$REC: linha Rail-Verdict ausente ou repetida"
R_FIND=$(field Rail-Findings) || die "$REC: linha Rail-Findings ausente ou repetida"
[ "$R_ROUND" = "$LAST" ] || die "$REC declara Rail-Round '$R_ROUND'"
[ "$R_SUBJ" = "$PATCH_SHA" ] || die "o último registro do rail ($REC) revisou outro patch ($R_SUBJ), não este ($PATCH_SHA)"
case "$R_VERD" in
  APPROVE)
    [ "$R_FIND" = "P0=0 P1=0 P2=0" ] || die "APPROVE exige 'P0=0 P1=0 P2=0' (o registro diz '$R_FIND')" ;;
  DECLARED-P2)
    case "$R_FIND" in
      "P0=0 P1=0 P2="[1-9]*) : ;;
      *) die "DECLARED-P2 exige 'P0=0 P1=0 P2=<n>' com n > 0 (o registro diz '$R_FIND')" ;;
    esac
    awk '/^## P2 declarados/{s=1; next} /^## /{s=0} s && /^- /{n++} END {exit n ? 0 : 1}' "$REC" \
      || die "DECLARED-P2 sem itens na seção '## P2 declarados' de $REC" ;;
  *) die "o veredito do último registro do rail é '$R_VERD' — o SIGN só aceita APPROVE ou DECLARED-P2" ;;
esac
RAIL_SHA=$(shasum -a 256 "$REC" | awk '{print $1}')
printf '   OK: main (%s commit(s) à frente de origin/main), árvore limpa, patch aplicável sobre a base pinada,\n' "$AHEAD"
printf '       %s caminhos = Scope, canônicos = os 2 declarados, materiais commitados\n' "$(wc -l < "$BAK/touched" | tr -d ' ')"
printf '   chave de assinatura (em %s): %s\n' "$SIGNERS" "$SIGN_KEY"
printf '   rail: %s = %s (%s), sobre Patch-sha256 %s\n' "$REC" "$R_VERD" "$R_FIND" "$PATCH_SHA"

say "1/7 aplicar o patch"
git apply "$PATCH" || die "git apply falhou"
APPLIED=1

say "2/7 bytes aplicados = bytes revisados"
while read -r p old new; do
  now=$(git hash-object -- "$p")
  [ "$now" = "$new" ] || die "$p depois do apply tem o blob $now; o patch revisado declara $new"
done < "$BAK/blobs"
[ -x .claude/hooks/check_workflow_launch.py ] || die "hook não é executável após o apply"
[ -x .claude/scripts/ceo-launches.py ] || die "CLI não é executável após o apply"
printf '   %s blobs conferidos contra o index pós-imagem do patch\n' "$(wc -l < "$BAK/blobs" | tr -d ' ')"

say "3/7 bateria (gates de corpus + suítes do pytest.ini, julgados contra a árvore sem o patch)"
NOTES=""
ensure_base_wt() {  # a árvore SEM o patch: worktree destacado do HEAD, criado uma vez, removido no fim
  if [ -z "$BASE_WT" ]; then
    BASE_WT="$BAK/base-wt"
    git worktree add --quiet --detach "$BASE_WT" HEAD >/dev/null 2>&1 || die "não consegui criar o worktree da base em $BASE_WT"
  fi
}
gov_check() {  # validate-governance completo, e o resumo precisa dizer "Errors:   0"
  bash .claude/scripts/validate-governance.sh 2>&1 | tee "$BAK/gov-last.out" | awk '/Errors:   0/{ok=1} END{exit ok ? 0 : 1}'
}
gate() {  # rótulo, comando... — reprova o SIGN só o gate que passa na árvore sem o patch
  local label="$1"
  shift
  if "$@" >"$BAK/g.out" 2>&1; then printf '   ok: %s\n' "$label"; return 0; fi
  cp "$BAK/g.out" "$BAK/gate-fail.out"
  ensure_base_wt
  if (cd "$BASE_WT" && "$@") >"$BAK/g-base.out" 2>&1; then
    tail -12 "$BAK/gate-fail.out" >&2
    die "$label reprovou com o patch e passa sem ele (log: $BAK/gate-fail.out)"
  fi
  printf '   PRÉ-EXISTENTE: %s reprova também sem o patch — não é deste pacote (log: %s)\n' "$label" "$BAK/g-base.out"
  NOTES="$NOTES
   - $label"
}
judge_fails() {  # julga os ids em now-fails: isolado com o patch; se falhar de novo, na árvore sem o patch
  sort -u "$BAK/now-fails" > "$BAK/now-fails.sorted"
  : > "$BAK/now-fails"
  : > "$BAK/real-new-fails"
  local test_id brc tries passed
  while IFS= read -r test_id; do
    [ -n "$test_id" ] || continue
    # até 3 reruns isolados com o patch: um teste sensível a tempo pode falhar de novo numa máquina
    # carregada (medido no ensaio: o de orçamento de 0,6 s do git falso falhou 2x seguidas)
    tries=0
    passed=0
    while [ "$tries" -lt 3 ]; do
      tries=$((tries + 1))
      if python3 -m pytest "$test_id" -q -p no:cacheprovider >"$BAK/rerun.out" 2>&1; then passed=1; break; fi
    done
    if [ "$passed" = "1" ]; then
      printf '   instável (passou isolada, com o patch, na tentativa %s de 3): %s\n' "$tries" "$test_id"
      continue
    fi
    ensure_base_wt
    set +e
    (cd "$BASE_WT" && python3 -m pytest "$test_id" -q -p no:cacheprovider) >"$BAK/rerun-base.out" 2>&1
    brc=$?
    set -e
    if [ "$brc" = "1" ]; then
      printf '   PRÉ-EXISTENTE (falha também sem o patch): %s\n' "$test_id"
      NOTES="$NOTES
   - $test_id"
    else
      printf '%s  (sem o patch: rc=%s)\n' "$test_id" "$brc" >> "$BAK/real-new-fails"
    fi
  done < "$BAK/now-fails.sorted"
  if [ -s "$BAK/real-new-fails" ]; then
    sed 's/^/   /' "$BAK/real-new-fails" >&2
    die "falhas NOVAS: falham com o patch e passam (ou não existem) sem ele — logs em $BAK"
  fi
}
run_pass() {  # rótulo, log, argumentos do pytest — anota os ids que falharam
  local label="$1" log="$2" rc before after
  shift 2
  before=$(wc -l < "$BAK/now-fails" | tr -d ' ')
  set +e
  python3 -m pytest "$@" >"$log" 2>&1
  rc=$?
  set -e
  case "$rc" in 0|1) ;; *) die "$label não terminou (rc=$rc) — log em $log" ;; esac
  # O id vai até o primeiro " - " (a mensagem vem depois); num id parametrizado ("…::nome[…]"), até
  # o primeiro "]" seguido de " - " ou do fim da linha — o parâmetro pode conter " - ".
  awk '/^(FAILED|ERROR) / {
    l = $0; sub(/^(FAILED|ERROR) /, "", l); id = ""
    c = index(l, "::"); b = 0
    if (c > 0) { b = index(substr(l, c), "["); if (b > 0) b = b + c - 1 }
    if (b > 0) {
      n = length(l)
      for (i = b; i <= n; i++) {
        if (substr(l, i, 1) == "]" && (i == n || substr(l, i + 1, 3) == " - ")) { id = substr(l, 1, i); break }
      }
    }
    if (id == "") { id = l; sub(/ - .*$/, "", id) }
    print id
  }' "$log" >> "$BAK/now-fails"
  after=$(wc -l < "$BAK/now-fails" | tr -d ' ')
  if [ "$rc" = "1" ] && [ "$after" = "$before" ]; then die "$label saiu rc=1 sem nenhum id de falha — log em $log"; fi
  printf '   %s: %s\n' "$label" "$(awk 'match($0, /[0-9]+ (passed|failed)[^=]*/) {v = substr($0, RSTART, RLENGTH)} END {print v}' "$log")"
}
python3 -m py_compile .claude/hooks/_lib/launch_ledger.py .claude/hooks/check_workflow_launch.py .claude/scripts/ceo-launches.py || die "py_compile"
gate "test-env-hygiene" python3 .claude/scripts/check-test-env-hygiene.py
gate "inventário de variáveis de ambiente" python3 .claude/scripts/env-inventory-check.py --check
gate "hooks ativos executáveis" python3 .claude/scripts/check-active-hooks-executable.py
gate "contamination" bash .claude/scripts/check-contamination.sh
gate "build-plugin --check" python3 scripts/build-plugin.py --check
gate "mapa comando→skill→hook" python3 .claude/scripts/gen-command-skill-hook-map.py --check
gate "docs-freshness" python3 .claude/scripts/check-docs-freshness.py --format=text
gate "verify-counts" bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
gate "ceremony-lint" python3 .claude/scripts/check-ceremony-script.py
gate "validate-governance (Errors: 0)" gov_check
: > "$BAK/now-fails"
run_pass "testes do ledger" "$BAK/suite-ledger.out" .claude/hooks/tests/test_check_workflow_launch.py tests/unit/test_launch_ledger.py \
  -q -rfE --tb=no -p no:cacheprovider
judge_fails
printf '   suítes do pytest.ini com a divisão de marcadores do CI (paralela e serial) — duração não medida nesta árvore\n'
run_pass "passada paralela" "$BAK/suite-parallel.out" -n auto -m 'not serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider
run_pass "passada serial" "$BAK/suite-serial.out" -m 'serial' --strict-markers --tb=no -q -rfE -p no:cacheprovider
judge_fails
remove_base_wt
printf '   bateria: nenhuma falha nova em relação à árvore sem o patch\n'
if [ -n "$NOTES" ]; then
  printf '   ATENÇÃO — vermelhos PRÉ-EXISTENTES (reprovam também sem este patch; não bloqueiam este land):%s\n' "$NOTES"
fi
# Depois da bateria (longa): o HEAD e os bytes a landar precisam ser os de antes dela.
[ "$(git rev-parse HEAD)" = "$HEAD_SHA" ] \
  || die "o HEAD mudou durante a bateria (era $HEAD_SHA) — o Anchor-SHA não seria o pai do commit; rode de novo sobre o HEAD atual"
while read -r p old new; do
  now=$(git hash-object -- "$p")
  [ "$now" = "$new" ] || die "$p mudou durante a bateria (blob $now; o patch revisado declara $new) — os bytes a landar deixaram de ser os revisados"
done < "$BAK/blobs"
# Arquivos rastreados FORA do patch modificados durante a execução (um teste que escreve na árvore,
# ou outro processo): não entram no commit (o stage é exato), mas deixam a árvore suja — aviso no fim.
git diff --name-only HEAD -- | sort -u > "$BAK/dirty-now"
comm -23 "$BAK/dirty-now" "$BAK/touched" > "$BAK/dirty-other"
if [ -s "$BAK/dirty-other" ]; then
  printf '   AVISO: arquivos rastreados fora do patch mudaram durante a bateria (não entram no commit):\n'
  sed 's/^/     /' "$BAK/dirty-other"
fi

say "4/7 Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data no sentinel"
if [ "$DRY" = "1" ]; then
  cp "$SENT" "$BAK/sentinel.md"; SENT="$BAK/sentinel.md"; ASC="$SENT.asc"
else
  cp "$SENT" "$BAK/sentinel.orig.md"
  SENT_TOUCHED=1
fi
python3 - "$SENT" "$HEAD_SHA" "$PATCH_SHA" "$RAIL_SHA" "$(date -u +%Y-%m-%d)" <<'PY'
import pathlib
import re
import sys

p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
for key, val in (("Anchor-SHA", sys.argv[2]), ("Patch-sha256", sys.argv[3]),
                 ("Rail-Record-sha256", sys.argv[4]), ("Data", sys.argv[5])):
    t2, n = re.subn(r"^%s: TO-FILL-BY-SIGN$" % re.escape(key), "%s: %s" % (key, val), t, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("linha %s: TO-FILL-BY-SIGN não encontrada" % key)
    t = t2
if "TO-FILL-BY-SIGN" in t:
    raise SystemExit("sobrou TO-FILL-BY-SIGN no sentinel")
p.write_text(t, encoding="utf-8")
PY
for kv in "Anchor-SHA: $HEAD_SHA" "Patch-sha256: $PATCH_SHA" "Rail-Record-sha256: $RAIL_SHA"; do
  awk -v l="$kv" '$0 == l {n++} END {exit n == 1 ? 0 : 1}' "$SENT" || die "o campo '$kv' não gravou no sentinel"
done
printf '   Anchor-SHA = %s\n   Patch-sha256 = %s\n   Rail-Record-sha256 = %s\n' "$HEAD_SHA" "$PATCH_SHA" "$RAIL_SHA"

say "5/7 assinar o sentinel (pinentry)"
if [ "$DRY" = "1" ]; then
  printf '   [dry-run] pularia a assinatura\n'
else
  SIGN_STARTED=1
  gpg --armor --detach-sign --local-user "$SIGN_KEY" --output "$ASC" "$SENT" || die "assinatura falhou"
  SIGNER=$(signer_tool verify "$SENT" "$ASC") || die "a assinatura não verifica contra $SIGNERS"
  printf '   assinado por %s (no allowlist %s)\n' "$SIGNER" "$SIGNERS"
fi

say "6/7 stage EXATO + conferência touched ∪ {sentinel, .asc}"
xargs git add -- < "$BAK/touched"
[ "$DRY" = "1" ] || git add -- "$SENT" "$ASC"
git diff --cached --name-only | sort > "$BAK/staged"
{ cat "$BAK/touched"; [ "$DRY" = "1" ] || printf '%s\n%s\n' "$SENT" "$ASC"; } | sort -u > "$BAK/expected"
EXTRA=$(comm -3 "$BAK/staged" "$BAK/expected")
[ -z "$EXTRA" ] || die "conjunto staged ≠ patch + sentinel:$(printf '\n   %s' $EXTRA)"
while read -r p old new; do
  st=$(git rev-parse --verify --quiet ":$p") || die "$p não está no índice depois do stage"
  [ "$st" = "$new" ] || die "$p no índice tem o blob $st; o patch revisado declara $new"
done < "$BAK/blobs"
sed 's/^/   /' "$BAK/staged"
printf '   %s blobs no índice conferidos contra o index pós-imagem do patch\n' "$(wc -l < "$BAK/blobs" | tr -d ' ')"
if [ "$DRY" = "1" ]; then
  say "DRY-RUN — nada assinado nem commitado; revertendo o patch"
  undo
  trap - EXIT INT TERM HUP
  printf '\nEnsaio OK (logs em %s). Rode sem --dry-run para valer.\n' "$BAK"
  exit 0
fi

say "7/7 commit (nunca abre editor)"
# O pinentry pode ter levado minutos: o pai do commit precisa ser o Anchor-SHA assinado.
[ "$(git rev-parse HEAD)" = "$HEAD_SHA" ] \
  || die "o HEAD mudou antes do commit (era $HEAD_SHA) — o Anchor-SHA assinado não seria o pai do commit"
git commit -q -F - <<MSG
ceremony(PLAN-193 W4b): cura do FN-04 — o PreToolUse do Workflow não grava bytes de scriptPath

No PreToolUse da tool Workflow, o ledger (check_workflow_launch.py por
_lib/launch_ledger.py) deixa de gravar os bytes do arquivo que
tool_input.scriptPath nomeia: registra caminho, sha256 e tamanho. O snapshot
desse arquivo passa ao PostToolUse da mesma chamada (vínculo por
tool_use_id, id rotulado pelo harness), relido e gravado só quando o sha256
é o gravado antes do despacho; vínculo heurístico e bind manual não leem o
arquivo. O texto de um script inline segue com snapshot no PreToolUse. Um
registro de scriptPath sem snapshot segue válido para a comparação de args
(args diferentes seguem bloqueados sob vínculo forte), mas a comparação de
script dele é inconclusiva: nunca match, advisory ou bloqueio de script,
também sob CEO_WORKFLOW_SCRIPT_GUARD=enforce. ceo-launches.py relaunch dele
sai rc 7 e --out recusa nomeando o motivo. Testes com o canário S357
(vermelhos sobre o código anterior) e docs/workflow-recovery.md com os
limites declarados: o PreToolUse ainda lê o arquivo para o hash e grava
sha256 e tamanho; o snapshot relê o caminho; snapshots de versões
anteriores não são removidos.

Cura o caso que a condição 23 do GA v1.4.1 descreve: o ledger do hook do
Workflow gravava, antes da decisão de permissão, bytes de um caminho que o
harness pode negar. A classe não se esgota neste hook: o sentinel declara
pela forma o que fica fora e os limites desta cura.

Sentinel: $SENT (assinado por $SIGNER; Anchor-SHA $HEAD_SHA;
Patch-sha256 $PATCH_SHA; Rail-Record-sha256 $RAIL_SHA, $REC)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
MSG
APPLIED=0; SENT_TOUCHED=0; SIGN_STARTED=0
trap - EXIT INT TERM HUP
printf '\nLANDADO em %s. Push é decisão sua: git push origin main\n' "$(git rev-parse --short HEAD)"
[ "$(git rev-parse HEAD~1)" = "$HEAD_SHA" ] \
  || printf 'ATENÇÃO: o pai do commit não é o Anchor-SHA %s — confira com: git log -2 --format=%%H\n' "$HEAD_SHA" >&2
git status --porcelain --untracked-files=no > "$BAK/dirty-after"
if [ -s "$BAK/dirty-after" ]; then
  printf '\nATENÇÃO: a árvore rastreada ficou suja (a bateria ou outro processo mudou estes arquivos; eles NÃO\n' >&2
  printf 'estão no commit). A próxima cerimônia recusa árvore suja. Confira com «git diff» e, se for sobra\n' >&2
  printf 'da bateria, restaure com «git checkout -- <arquivo>»:\n' >&2
  sed 's/^/   /' "$BAK/dirty-after" >&2
fi
