#!/bin/bash
# OWNER-RC1-META-LAND.sh — aplica e landa a cerimonia wave-relmeta (PLAN-169).
#
#   bash .claude/plans/PLAN-169/OWNER-RC1-META-LAND.sh --dry-run
#   bash .claude/plans/PLAN-169/OWNER-RC1-META-LAND.sh
#
# CEREMONY-LINT: handwritten-exception: escrito contra o corpus
# `.claude/plans/PLAN-188/ceremony-defect-corpus-S348.md`. Curas nomeadas no
# ponto de uso (CM-NN). As tres que mudam o desenho em relacao aos 14 LANDs
# vivos: (CM-07) a mensagem de commit e RELIDA do commit e comparada byte a
# byte com os bytes congelados; (CM-08) o push e pinado ao SHA verificado com
# refspec nomeado, nunca `HEAD:branch`; (CM-13) o rollback e DESARMADO antes
# do commit, e a recuperacao pos-commit e por `git reset --hard` contra o SHA
# registrado, nunca por trap que reverteria arquivos ja commitados.
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT"

PLAN_DIR=".claude/plans/PLAN-169"
CDIR="$PLAN_DIR/s349-ceremony-relmeta"
SENTINEL="$PLAN_DIR/wave-relmeta-approved.md"
SENT_DRAFT="$PLAN_DIR/wave-relmeta-approved-draft.md"
PATCH="$CDIR/RELMETA.patch"
SCOPE="$CDIR/SCOPE.txt"
BASELINE="$CDIR/EXPECTED-BASELINE.txt"
MATERIALS="$CDIR/MATERIALS.sha256"
APPLY="$CDIR/apply-relmeta-edits.py"
FINALIZE="$CDIR/finalize-relmeta.sh"
SIGN_SCRIPT="$PLAN_DIR/OWNER-RC1-META-SIGN.sh"
PUSH_REMOTE="origin"
PUSH_BRANCH="main"
OWNER_FPR="AE9B236FDAF0462874060C6BCFCFACF00335DC74"

# --- interruptor de AUTO-TESTE (recusado fora do scratchpad declarado) -----
# Existe so para `test-rc1-kit.sh` exercitar o LAND com uma chave GPG
# DESCARTAVEL. Relaxa EXATAMENTE uma coisa — qual fingerprint e aceita — e
# NUNCA a exigencia de VALIDSIG: um `.asc` que nao verifica continua sendo
# recusa tambem em auto-teste. A comparacao e por REALPATH dos DOIS lados (no
# macOS `/tmp` e symlink; comparar formato de string mediria formato, nao
# caminho). E o interruptor exige que a fingerprint substituta venha por
# ARGUMENTO explicito (CM-15), nunca por sentinela dentro do material.
if [ "${RELMETA_SELFTEST:-0}" = "1" ]; then
  _st_root="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$ROOT")"
  _st_scr="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "${RELMETA_SELFTEST_SCRATCH:-/nonexistent}")"
  case "$_st_root/" in
    "$_st_scr"/*) : ;;
    *) printf 'FAIL: RELMETA_SELFTEST=1 fora do scratchpad declarado\n' >&2; exit 1 ;;
  esac
  if [ -z "${RELMETA_SELFTEST_FPR:-}" ]; then
    printf 'FAIL: auto-teste exige RELMETA_SELFTEST_FPR explicito\n' >&2; exit 1
  fi
  OWNER_FPR="$RELMETA_SELFTEST_FPR"
  printf '   (AUTO-TESTE: fingerprint aceita = %s; VALIDSIG segue exigido)\n' \
    "${OWNER_FPR:0:12}"
fi

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

die() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }

RESTORE_ON_EXIT=0
_restore() {
  [ "$RESTORE_ON_EXIT" -eq 1 ] || return 0
  printf '\n  (revertendo os alvos do patch para o estado PRE-edicao)\n' >&2
  while IFS= read -r _bl; do
    case "$_bl" in "PRE "*) : ;; *) continue ;; esac
    _bp="${_bl##* }"
    git checkout -- "$_bp" 2>/dev/null || true
  done < "$BASELINE"
}
trap _restore EXIT

# ---------------------------------------------------------------------------
# G0 — material presente, fechado, e arvore sem modificacao rastreada.
# ---------------------------------------------------------------------------
say "G0 material + arvore"
for _f in "$SENTINEL" "$SENTINEL.asc" "$PATCH" "$SCOPE" "$BASELINE" \
          "$MATERIALS" "$APPLY" "$FINALIZE" "$SENT_DRAFT" "$SIGN_SCRIPT" ; do
  [ -f "$_f" ] || die "ausente: $_f"
  [ -L "$_f" ] && die "symlink no lugar de arquivo regular: $_f"
done
( cd "$CDIR" && shasum -a 256 -c MATERIALS.sha256 --status ) \
  || die "MATERIALS.sha256 nao confere — material mudou depois do finalize"

_g0_f="$(mktemp)"
if ! git status --porcelain=v1 --untracked-files=all > "$_g0_f"; then
  rm -f "$_g0_f"; die "git status falhou (CM-04) — nao vou tratar como limpo"
fi
_g0_bad=""
while IFS= read -r _l; do
  [ -n "$_l" ] || continue
  _p="${_l#???}"
  case "$_l" in '??'*) : ;; *) _g0_bad="$_g0_bad
   $_l" ;; esac
  # Untracked so e tolerado dentro do namespace do plano ($PLAN_DIR): na
  # primeira execucao o kit inteiro — cerimonia, runner, manifests, harness —
  # ainda nao landou. Isso NAO alarga o commit: o passo S stageia uma lista
  # LITERAL e assere que nada staged esta fora dela.
  case "$_l" in
    '??'*)
      case "$_p" in
        "$PLAN_DIR"/*) : ;;
        *) _g0_bad="$_g0_bad
   $_l (untracked fora do namespace do plano)" ;;
      esac ;;
  esac
done < "$_g0_f"
rm -f "$_g0_f"
[ -z "$_g0_bad" ] || die "arvore nao esta no estado esperado:$_g0_bad"
printf '   OK: material fechado, nenhuma modificacao rastreada\n'

# ---------------------------------------------------------------------------
# G1 — assinatura verificada E CONGELADA (CM-09).
# Os 13 LANDs vivos verificam o sentinel aqui e o RELEEM do worktree ~550
# linhas depois, no staging, sem nenhum digest congelado. Aqui o digest e
# congelado agora e re-conferido imediatamente antes do `git add`.
# ---------------------------------------------------------------------------
say "G1 assinatura GPG do sentinel (verificada e congelada)"
_gpg_out="$(gpg --status-fd 1 --verify "$SENTINEL.asc" "$SENTINEL" 2>/dev/null)" \
  || die "assinatura do sentinel NAO verifica"
_validsig="$(printf '%s\n' "$_gpg_out" | grep '^\[GNUPG:\] VALIDSIG ' || true)"
[ -n "$_validsig" ] || die "gpg nao emitiu VALIDSIG"
printf '%s\n' "$_validsig" | grep -q "$OWNER_FPR" \
  || die "assinatura de OUTRO signatario: $_validsig"
FROZEN_SENT="$(git hash-object -- "$SENTINEL")" || die "hash-object do sentinel falhou"
FROZEN_ASC="$(git hash-object -- "$SENTINEL.asc")" || die "hash-object do .asc falhou"
printf '   OK: VALIDSIG do Owner; congelados sentinel=%s .asc=%s\n' \
  "${FROZEN_SENT:0:12}" "${FROZEN_ASC:0:12}"

# ---------------------------------------------------------------------------
# G2 — Anchor-SHA do sentinel == HEAD, e Patch-sha256 == patch em disco.
# ---------------------------------------------------------------------------
say "G2 anchor + binding do patch"
_anchor="$(awk '/^Anchor-SHA:/{print $2; exit}' "$SENTINEL")"
HEADSHA="$(git rev-parse HEAD)" || die "git rev-parse HEAD falhou"
[ "$_anchor" = "$HEADSHA" ] \
  || die "Anchor-SHA do sentinel ($_anchor) != HEAD ($HEADSHA) — main andou depois da assinatura; RE-ASSINE"
_psha_sent="$(awk '/^Patch-sha256:/{print $2; exit}' "$SENTINEL")"
_psha_disk="$(shasum -a 256 "$PATCH" | awk '{print $1}')"
[ "$_psha_sent" = "$_psha_disk" ] \
  || die "Patch-sha256 do sentinel ($_psha_sent) != patch em disco ($_psha_disk)"
printf '   OK: anchor %s, patch %s\n' "${HEADSHA:0:12}" "${_psha_disk:0:12}"

# ---------------------------------------------------------------------------
# G3 — o escopo assinado, nos DOIS sentidos, contra o patch.
# ---------------------------------------------------------------------------
say "G3 escopo assinado == paths do patch (bidirecional)"
_g3="$(mktemp -d)"
awk '/^Scope:$/{f=1;next} f && /^  - /{print $2}' "$SENTINEL" | sort > "$_g3/signed"
git apply --numstat < "$PATCH" 2>/dev/null | awk '{print $3}' | sort > "$_g3/patch"
cmp -s "$_g3/signed" "$_g3/patch" \
  || die "escopo assinado != paths do patch:
$(diff -u "$_g3/signed" "$_g3/patch" || true)"
SCOPE_PATHS="$(cat "$_g3/patch")"
_scope_n="$(grep -c . "$_g3/patch")"
rm -rf "$_g3"
[ "$_scope_n" = "2" ] || die "escopo com $_scope_n paths (esperado 2)"
printf '   OK: 2 paths, conjuntos identicos nos dois sentidos\n'

# ---------------------------------------------------------------------------
# G4 — a arvore viva ainda esta no estado PRE-edicao do baseline.
# ---------------------------------------------------------------------------
say "G4 baseline PRE-edicao reproduz a arvore viva"
_bl_head="$(awk '$1=="BASE-HEAD"{print $2}' "$BASELINE")"
[ "$_bl_head" = "$HEADSHA" ] || die "BASE-HEAD do baseline ($_bl_head) != HEAD"
while IFS= read -r _bl; do
  case "$_bl" in "PRE "*) : ;; *) continue ;; esac
  _bp="${_bl##* }"; _bh="$(printf '%s' "$_bl" | awk '{print $2}')"
  _live="$(git hash-object -- "$_bp")" || die "hash-object falhou: $_bp"
  [ "$_live" = "$_bh" ] || die "alvo ja modificado: $_bp (vivo=$_live baseline=$_bh)"
done < "$BASELINE"
printf '   OK: os 2 alvos estao no estado PRE-edicao\n'

# ---------------------------------------------------------------------------
# APLICAR o patch (a partir daqui o rollback esta ARMADO).
# ---------------------------------------------------------------------------
say "aplicar o patch"
git apply --check "$PATCH" || die "git apply --check recusou o patch"
RESTORE_ON_EXIT=1
git apply "$PATCH" || die "git apply falhou"
printf '   patch aplicado\n'

# ---------------------------------------------------------------------------
# V — o material versionado REPRODUZ o patch: HEAD + apply-relmeta-edits.py
# tem de dar a mesma arvore. Um patch editado a mao morre aqui.
# ---------------------------------------------------------------------------
say "V1 o script derivador reproduz o patch (HEAD + script == patch)"
_v="$(mktemp -d)"
git worktree add --detach --quiet "$_v/wt" "$HEADSHA" \
  || { rm -rf "$_v"; die "worktree de verificacao falhou"; }
_v_rc=0
python3 "$ROOT/$APPLY" --repo "$_v/wt" --today "$(awk '/^Data:/{print $2; exit}' "$SENTINEL")" >/dev/null 2>&1 || _v_rc=$?
if [ "$_v_rc" -eq 0 ]; then
  ( cd "$_v/wt" && git diff -- $SCOPE_PATHS > "$_v/regen.patch" ) || _v_rc=90
fi
git worktree remove --force "$_v/wt" >/dev/null 2>&1 || true
[ "$_v_rc" -eq 0 ] || { rm -rf "$_v"; die "derivador nao rodou no worktree (rc=$_v_rc)"; }
if ! cmp -s "$_v/regen.patch" "$PATCH"; then
  _v_diff="$(diff -u "$PATCH" "$_v/regen.patch" | sed -n '1,40p')"
  rm -rf "$_v"
  die "o patch NAO e reproduzivel pelo derivador — foi editado a mao?
$_v_diff"
fi
rm -rf "$_v"
printf '   OK: HEAD + apply-relmeta-edits.py == RELMETA.patch (byte a byte)\n'

# ---------------------------------------------------------------------------
# V2 — os gates que o corte vai rodar, agora, sobre a arvore JA patchada.
# ---------------------------------------------------------------------------
say "V2 gates sobre a arvore patchada"
bash -n .claude/scripts/local/release.sh || die "bash -n do release.sh falhou"
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -S warning .claude/scripts/local/release.sh \
    || die "shellcheck -S warning do release.sh falhou"
  printf '   ok   shellcheck do release.sh\n'
fi
# o sha do manifesto ADR-192 bate com o release.sh patchado
_man_sha="$(awk '$2==".claude/scripts/local/release.sh"{print $1}' \
  .claude/governance/gate-scripts-manifest.txt)"
_rel_sha="$(shasum -a 256 .claude/scripts/local/release.sh | awk '{print $1}')"
[ "$_man_sha" = "$_rel_sha" ] \
  || die "manifesto ADR-192 pina $_man_sha, release.sh vale $_rel_sha"
printf '   ok   manifesto ADR-192 re-pinado corretamente\n'
# TARGET_BASE mudou de verdade
_tb="$(awk -F'"' '/^TARGET_BASE=/{print $2; exit}' .claude/scripts/local/release.sh)"
[ "$_tb" = "1.4.0" ] || die "TARGET_BASE do release.sh e '$_tb', esperado 1.4.0"
printf '   ok   TARGET_BASE = %s\n' "$_tb"
# O CHANGELOG e PRE-CONDICAO, nao alvo: a secao [1.4.0] veio do pacote de
# docs e este patch NAO a toca. O que se confere e que ela continua la e que
# o CHANGELOG nao entrou no escopo por acidente.
grep -q '^## \[1.4.0\]' CHANGELOG.md \
  || die "CHANGELOG sem secao [1.4.0] — o pacote de docs regrediu?"
printf '%s\n' $SCOPE_PATHS | grep -qx 'CHANGELOG.md' \
  && die "CHANGELOG.md entrou no escopo — esta cerimonia nao o escreve"
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >/dev/null 2>&1 \
  || die "verify-counts reporta drift sobre a arvore patchada"
printf '   ok   CHANGELOG [1.4.0] + verify-counts sem drift\n'
python3 .claude/scripts/check-claude-md-claims.py >/dev/null 2>&1 \
  || die "check-claude-md-claims.py nonzero"
printf '   ok   claims do CLAUDE.md\n'
bash .claude/scripts/check-contamination.sh >/dev/null 2>&1 \
  || die "check-contamination.sh nonzero"
printf '   ok   check-contamination\n'

if [ "$DRY" -eq 1 ]; then
  say "DRY-RUN: nada sera commitado"
  git --no-pager diff --stat -- $SCOPE_PATHS
  printf '\nDRY-RUN VERDE. Rode sem --dry-run para landar.\n'
  exit 0
fi

# ---------------------------------------------------------------------------
# S — staging LITERAL. CM-09: re-conferir os digests congelados no G1
# IMEDIATAMENTE antes do `git add`. CM-§2b: o `.asc` entra por NOME, porque
# `git add -u` nunca inclui um arquivo novo.
# ---------------------------------------------------------------------------
say "S staging literal (escopo + material da cerimonia)"
[ "$(git hash-object -- "$SENTINEL")" = "$FROZEN_SENT" ] \
  || die "o SENTINEL mudou entre o G1 e o staging — recusado (CM-09)"
[ "$(git hash-object -- "$SENTINEL.asc")" = "$FROZEN_ASC" ] \
  || die "o .asc mudou entre o G1 e o staging — recusado (CM-09)"

STAGE_LIST="$(mktemp)"
{
  printf '%s\n' $SCOPE_PATHS
  printf '%s\n' "$SENTINEL" "$SENTINEL.asc" "$SENT_DRAFT"
  printf '%s\n' "$PATCH" "$SCOPE" "$BASELINE" "$MATERIALS" "$APPLY" "$FINALIZE"
  printf '%s\n' "$SIGN_SCRIPT" "$SCRIPT_DIR/$(basename "$0")"
} | sed "s|^$ROOT/||" | sort -u > "$STAGE_LIST"
while IFS= read -r _p; do
  [ -n "$_p" ] || continue
  [ -f "$_p" ] || die "arquivo da lista de staging ausente: $_p"
  [ -L "$_p" ] && die "symlink na lista de staging: $_p"
  git add -- "$_p" || die "git add falhou: $_p"
done < "$STAGE_LIST"

# touched - scope = 0: nada staged fora da lista literal.
_cached="$(git diff --cached --name-only)" || die "git diff --cached falhou"
_extra=""
while IFS= read -r _c; do
  [ -n "$_c" ] || continue
  grep -qxF "$_c" "$STAGE_LIST" || _extra="$_extra
   $_c"
done <<CACHED
$_cached
CACHED
[ -z "$_extra" ] || die "caminho staged FORA da lista literal:$_extra"
git diff --quiet || die "sobrou mudanca rastreada NAO-staged apos o staging literal"
printf '   OK: %s caminhos staged, nada fora da lista\n' "$(grep -c . "$STAGE_LIST")"

# ---------------------------------------------------------------------------
# COMMIT. CM-13: o rollback e DESARMADO antes do commit — um trap que reverte
# arquivos ja commitados deixa a arvore suja contra um HEAD que ja andou.
# ---------------------------------------------------------------------------
say "commit"
MSGF="$(mktemp)"
cat > "$MSGF" <<MSGEOF
governance(PLAN-169 wave-relmeta): release.sh mira a v1.4.0 + re-pin do manifesto ADR-192

O bloco PER-RELEASE do driver estava hardcoded em 1.3.0, e com ele
\`release.sh preflight --rc 1\` morre em "tag v1.3.0-rc.1 already exists".
Este land troca o bloco inteiro por um DERIVADO (planos citados em
\`git log v1.3.0..HEAD\`; ADRs tocados na mesma faixa, LISTADOS e nao como
faixa) e re-pina o sha de \`release.sh\` no manifesto ADR-192 — que e
canonico, e por isso a assinatura.

O CHANGELOG NAO e tocado: a secao [1.4.0] e o rotulo do preambulo vieram
do pacote de docs, e o aplicador apenas os CONFERE (uma secao, rotulo na
versao alvo, quatro contagens batendo \`verify-counts.sh --json\`).

As duas edicoes sao derivadas por
\`.claude/plans/PLAN-169/s349-ceremony-relmeta/apply-relmeta-edits.py\`;
o V1 deste LAND prova \`HEAD + script == patch\` byte a byte.

Sentinel: wave-relmeta-approved.md (assinado, anchor $HEADSHA).
MSGEOF
MSG_FROZEN="$(shasum -a 256 "$MSGF" | awk '{print $1}')"
RESTORE_ON_EXIT=0   # CM-13: desarmado ANTES do commit
git commit -q -F "$MSGF" || die "git commit falhou (o patch segue aplicado na arvore)"
NEW_SHA="$(git rev-parse HEAD)" || die "git rev-parse HEAD pos-commit falhou"

# CM-07: RELER a mensagem do commit e comparar com os bytes congelados.
# Os 14 LANDs vivos congelam a mensagem e nunca a releem; um hook commit-msg
# que acrescenta uma linha passa despercebido e e empurrado.
_msg_back="$(mktemp)"
git log -1 --format=%B "$NEW_SHA" > "$_msg_back" || die "git log -1 %B falhou"
# `git commit` normaliza a mensagem (apara a linha final em branco); comparar
# os bytes APARADOS dos dois lados mede conteudo, nao formatacao do git.
_a="$(mktemp)"; _b="$(mktemp)"
python3 -c 'import sys;sys.stdout.write(open(sys.argv[1],encoding="utf-8").read().rstrip("\n")+"\n")' "$MSGF" > "$_a"
python3 -c 'import sys;sys.stdout.write(open(sys.argv[1],encoding="utf-8").read().rstrip("\n")+"\n")' "$_msg_back" > "$_b"
if ! cmp -s "$_a" "$_b"; then
  printf '\nFAIL: a mensagem do commit %s DIVERGE dos bytes congelados (%s).\n' \
    "$NEW_SHA" "${MSG_FROZEN:0:12}" >&2
  diff -u "$_a" "$_b" >&2 || true
  printf '\nO commit e LOCAL e NAO foi empurrado. Recuperacao:\n' >&2
  printf '  git reset --soft %s\n' "$HEADSHA" >&2
  exit 1
fi
rm -f "$MSGF" "$_msg_back" "$_a" "$_b"
printf '   OK: commit %s, mensagem relida e identica\n' "${NEW_SHA:0:12}"

# ---------------------------------------------------------------------------
# PUSH — CM-08: pinado ao SHA verificado, com remoto e refspec NOMEADOS.
# `HEAD:main` resolveria HEAD no instante do push, nao no da verificacao.
# ---------------------------------------------------------------------------
say "push"
_hp="$(git config --get core.hooksPath || true)"
[ -z "$_hp" ] || printf '   (aviso: core.hooksPath = %s)\n' "$_hp"
git fetch --quiet "$PUSH_REMOTE" "$PUSH_BRANCH" || die "git fetch falhou"
_remote="$(git rev-parse "$PUSH_REMOTE/$PUSH_BRANCH")" || die "rev-parse do remoto falhou"
[ "$_remote" = "$HEADSHA" ] \
  || die "$PUSH_REMOTE/$PUSH_BRANCH ($_remote) != o anchor assinado ($HEADSHA) — main andou; o commit $NEW_SHA fica LOCAL"
git push "$PUSH_REMOTE" "$NEW_SHA:refs/heads/$PUSH_BRANCH" \
  || die "push recusado — o commit $NEW_SHA fica local"

printf '\n============================================================\n'
printf ' wave-relmeta LANDADA: %s\n' "$NEW_SHA"
printf ' release.sh agora mira 1.4.0; o manifesto ADR-192 esta re-pinado.\n'
printf ' Proximo: espere o CI verde e rode\n'
printf '   bash .claude/plans/PLAN-169/OWNER-RC1-CUT.sh\n'
printf '============================================================\n'
