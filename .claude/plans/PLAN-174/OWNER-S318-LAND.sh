#!/bin/bash
# Pack SENT-S318 — LAND (Owner-run): emenda ADR-163 (p95 180 hard + p99
# advisory), re-pin codex 0.147.0 (ADR-182 §5) + range <0.148.0, registro
# e reposicao do ceremony_lint_unlock_used (_KNOWN_ACTIONS 326 + SPEC
# v2.57), e emendas ADR-001 (AC-7) + ADR-079 (OQ-4) que destravam a W1
# do PLAN-182.
#
# Gates (fail-closed), mesmo molde do OWNER-S313-LAND.sh: G0 janela; G1
# baseline anti-stale; G2 MANIFEST dos 3 staged; G3 sentinel GPG
# (signer-pin + anchor==HEAD + eleicao locked-corpus preenchida); G4
# simulacao em clone com RC AGREGADO POR COMANDO fora do TMPDIR symlinked
# do macOS; G5 apply (kernel path com CEO_KERNEL_OVERRIDE=1, audited); G6
# touched-scope=vazio + checks vivos (inclui --verify-codex-pin, passo 4
# do ADR-182 §5); G7 commit com sentinel re-verificado.
#
# Uso: bash .claude/plans/PLAN-174/OWNER-S318-LAND.sh [--dry-run]
# -E (errtrace): o trap ERR do G5 tem de herdar em funcoes e substituicoes
# — sem ele, uma falha nua dentro de funcao sai sem rollback (rail S318 r2).
set -Eeuo pipefail
cd "$(git rev-parse --show-toplevel)"

ST174=.claude/plans/PLAN-174/staged-s318
ST169=.claude/plans/PLAN-169/staged-s318
ST182=.claude/plans/PLAN-182/staged-s318
APPROVED=.claude/plans/PLAN-174/S318-approved.md
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
say() { printf '\n== %s\n' "$1"; }

# Fonte executavel do mapa pack->destino (espelho legivel: PACKMAP.txt).
# Formato: <staged-src>|<repo-dst>
MAP="$ST169/validate.yml|.github/workflows/validate.yml
$ST169/profile-opus-4-7.py|.claude/scripts/profile-opus-4-7.py
$ST169/test_profile_opus47_latency_gate.py|.claude/scripts/tests/test_profile_opus47_latency_gate.py
$ST169/wave2-regression-proof.sh|.claude/plans/PLAN-159/wave2-regression-proof.sh
$ST169/ADR-163-hook-latency-gate-percentile-stability.md|.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
$ST174/codex-cli-pin-manifest.json|.claude/governance/codex-cli-pin-manifest.json
$ST174/codex-cli-pin.txt|.claude/governance/codex-cli-pin.txt
$ST174/audit_emit.py|.claude/hooks/_lib/audit_emit.py
$ST174/spec-v1-audit-log.schema.md|SPEC/v1/audit-log.schema.md
$ST174/check-ceremony-script.py|.claude/scripts/check-ceremony-script.py
$ST174/test_audit_emit_ceremony_lint_unlock.py|.claude/hooks/tests/test_audit_emit_ceremony_lint_unlock.py
$ST174/test_w5_scrub_enforcement.py|.claude/hooks/tests/test_w5_scrub_enforcement.py
$ST182/ADR-001-runtime-state-directory.md|.claude/adr/ADR-001-runtime-state-directory.md
$ST182/ADR-079-prompt-sha-salt-hmac-impact.md|.claude/adr/ADR-079-prompt-sha-salt-hmac-impact.md"
NEW_FILES=".claude/hooks/tests/test_audit_emit_ceremony_lint_unlock.py"

say "G0: confirmacao de janela"
echo "   Pack SENT-S318 (ADR-163 + re-pin 0.147.0 + lint_unlock + ADR-001/079)."
echo "   Prosseguir? (yes/NO)"
read -r _ok
[ "$_ok" = "yes" ] || { echo "ABORT."; exit 1; }

say "G1: baseline anti-stale (13 alvos vivos + 1 novo ausente)"
FAILED=0; N=0
while read -r want path; do
  [ -n "$path" ] || continue
  N=$((N+1))
  # Rail S318 P1: alvo tem de ser ARQUIVO REGULAR, nunca symlink — hash e
  # cp seguem links e escreveriam fora do repo com baseline "identico".
  [ -f "$path" ] && [ ! -L "$path" ] || { echo "   NOT-REGULAR: $path"; FAILED=1; continue; }
  got=$(shasum -a 256 "$path" | awk '{print $1}')
  [ "$want" = "$got" ] || { echo "   STALE: $path"; FAILED=1; }
done < "$ST174/BASELINE.sha256"
[ "$FAILED" -eq 0 ] || { echo "ABORT: main andou — re-stage."; exit 1; }
while IFS= read -r p; do
  [ -n "$p" ] || continue
  [ ! -e "$p" ] || { echo "ABORT: STALE-NEW: $p ja existe no vivo"; exit 1; }
done <<NEOF
$NEW_FILES
NEOF
echo "   OK: $N/$N alvos identicos; novos ausentes"

say "G2: integridade dos 3 staged"
for st in "$ST169" "$ST174" "$ST182"; do
  ( cd "$st" && shasum -a 256 -c MANIFEST.sha256 --status ) \
    || { echo "ABORT: pack nao confere: $st"; exit 1; }
done
echo "   OK: manifests dos 3 staged conferem"

say "G3: sentinel GPG"
OWNER_KEYID="CFCFACF00335DC74"
[ -f "$APPROVED" ] || { echo "ABORT: assine o draft (S318-approved-draft.md)"; exit 1; }
GPG_OUT=$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: gpg rc!=0"; printf '%s\n' "$GPG_OUT"; exit 1; }
printf '%s\n' "$GPG_OUT" | grep '^\[GNUPG:\] VALIDSIG ' \
  | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
  || { echo "ABORT: assinatura nao e do Owner"; exit 1; }
[ "$(sed -n 's/^Anchor-SHA: //p' "$APPROVED" | head -1)" = "$(git rev-parse HEAD)" ] \
  || { echo "ABORT: anchor != HEAD — re-assine"; exit 1; }
# O miolo do rotulo tem acentos (o sentinel e prosa pt-BR); o parser casa
# pelo PREFIXO ASCII estavel + "[^:]*: " para nao depender de acentuacao —
# a divergencia eleicao/eleição abortou o primeiro dry-run (S318).
_elect="$(sed -n 's/^Locked-corpus catch_rate[^:]*: //p' "$APPROVED" | head -1)"
case "$_elect" in RUN|DEFER) : ;; *) echo "ABORT: eleicao locked-corpus nao preenchida (RUN/DEFER); re-assine via SIGN"; exit 1 ;; esac
# Rail S318 P0: o Scope ASSINADO tem de autorizar exatamente o MAP
# executavel — set-equality NOME-a-nome (licao S272). Sem isto, um MAP
# alterado neste script aplicaria destinos fora do texto assinado sob um
# sentinel valido.
SIGNED_SCOPE=$(awk '/^```/{n++; next} n==1' "$APPROVED" | sed '/^[[:space:]]*$/d' | sort -u)
MAP_DESTS=$(printf '%s\n' "$MAP" | awk -F'|' '{print $2}' | sort -u)
if [ "$SIGNED_SCOPE" != "$MAP_DESTS" ]; then
  echo "ABORT: Scope assinado != destinos do MAP:"
  diff <(printf '%s\n' "$SIGNED_SCOPE") <(printf '%s\n' "$MAP_DESTS") || true
  exit 1
fi
echo "   OK: assinatura + anchor + eleicao=$_elect + Scope==MAP ($(printf '%s\n' "$MAP_DESTS" | wc -l | tr -d ' ') destinos)"

say "G4: simulacao em clone (rc agregado por comando; fora do TMPDIR)"
SIMROOT="$HOME/.s318-landsim"
mkdir -p "$SIMROOT"
SIM=$(mktemp -d "$SIMROOT/s318.XXXXXX")
git clone --local --quiet . "$SIM/repo"
while IFS='|' read -r src dst; do
  [ -n "$src" ] || continue
  mkdir -p "$SIM/repo/$(dirname "$dst")"
  cp "$src" "$SIM/repo/$dst"
done <<MEOF
$MAP
MEOF
G4RC=0
run_g4() {
  echo "   -> $*"
  ( cd "$SIM/repo" && "$@" ) >"$SIM/last.log" 2>&1 || { echo "   G4-FAIL: $*"; tail -20 "$SIM/last.log"; G4RC=1; }
}
run_g4 python3 -m py_compile .claude/hooks/_lib/audit_emit.py .claude/scripts/profile-opus-4-7.py .claude/scripts/check-ceremony-script.py
run_g4 bash -n .claude/plans/PLAN-159/wave2-regression-proof.sh
run_g4 python3 .claude/scripts/check-audit-registry-coverage.py
run_g4 python3 -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"
run_g4 python3 -m pytest -q -p no:cacheprovider \
  .claude/hooks/tests/test_audit_emit_ceremony_lint_unlock.py \
  .claude/hooks/tests/test_w5_scrub_enforcement.py \
  .claude/scripts/tests/test_profile_opus47_latency_gate.py \
  .claude/scripts/tests/test_check_ceremony_script.py \
  .claude/hooks/tests/test_check_pair_rail_payload_pin.py \
  .github/scripts/tests/test_validate_pair_rail_verdict.py
# Controle positivo do p99-advisory nos DOIS sentidos, no CLI real
# (iterations=22 = minimo pos-precondition; p99 ceiling impossivel força
# breach sintetico em toda entry; ~40s total):
_adv_rc=0
( cd "$SIM/repo" && python3 .claude/scripts/profile-opus-4-7.py --hook-latency \
    --latency-iterations 22 --p95-ceiling-ms 99999 --p99-ceiling-ms 0.0001 ) \
    >"$SIM/adv-off.json" 2>"$SIM/adv-off.err" || _adv_rc=$?
if [ "$_adv_rc" -eq 1 ] && grep -q "FAIL: hook latency gate" "$SIM/adv-off.err"; then
  echo "   -> controle positivo p99 HARD (sem flag): FAIL esperado — OK"
else
  echo "   G4-FAIL: p99 hard sem flag devolveu rc=$_adv_rc (esperado 1)"; G4RC=1
fi
_adv2_rc=0
( cd "$SIM/repo" && python3 .claude/scripts/profile-opus-4-7.py --hook-latency \
    --latency-iterations 22 --p95-ceiling-ms 99999 --p99-ceiling-ms 0.0001 \
    --p99-advisory ) >"$SIM/adv-on.json" 2>"$SIM/adv-on.err" || _adv2_rc=$?
if [ "$_adv2_rc" -eq 0 ] && grep -q "WARN: hook latency p99 advisory breach" "$SIM/adv-on.err"; then
  echo "   -> controle positivo p99 ADVISORY (com flag): exit 0 + WARN — OK"
else
  echo "   G4-FAIL: advisory devolveu rc=$_adv2_rc sem WARN (esperado 0+WARN)"; G4RC=1
fi
run_g4 env CEO_PERF_GATE_BACKOFF_S=0 bash .claude/plans/PLAN-161/proof-retry-matrix.sh
run_g4 shasum -a 256 -c .claude/governance/gate-scripts-manifest.txt --status
run_g4 bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
run_g4 python3 .claude/scripts/check-claude-md-claims.py
run_g4 python3 .claude/hooks/check_pair_rail.py --verify-codex-pin
[ "$G4RC" -eq 0 ] || { echo "ABORT: G4 vermelho (rc agregado) — nada foi aplicado"; exit 1; }
echo "   OK: simulacao verde (todos os comandos, nao so o ultimo)"
[ "$DRY" -eq 1 ] && { echo "DRY-RUN: parando antes do apply"; exit 0; }

say "G5: apply (kernel path com CEO_KERNEL_OVERRIDE=1, audited)"
# Rail S318 P1: apply nao-atomico ganha rollback explicito — qualquer
# abort pos-apply restaura os tracked (git checkout) e remove os novos,
# em vez de deixar um pack meio-aplicado na arvore viva.
rollback_apply() {
  trap - ERR  # sem recursao se o proprio rollback falhar
  echo "   ROLLBACK: restaurando alvos aplicados"
  _tracked=$(printf '%s\n' "$MAP" | awk -F'|' '{print $2}' | grep -vxF "$NEW_FILES" || true)
  # `checkout HEAD --` restaura INDEX+worktree do HEAD — cobre tambem o
  # abort pos-`git add` do G7 (checkout sem HEAD restauraria do index ja
  # populado com o conteudo novo, um rollback inocuo).
  # shellcheck disable=SC2086
  [ -z "$_tracked" ] || git checkout --quiet HEAD -- $_tracked || true
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    rm -f "$p"
  done <<RNEOF
$NEW_FILES
RNEOF
}
# Rail S318 r2 (sentinel check, P1): falha NUA no meio do apply (cp/mkdir
# com disco cheio, permissao, git add/commit) morria via set -e SEM
# rollback — o trap ERR fecha esse residuo; os aborts explicitos (exit 1)
# de G5/G6/G7 nao disparam ERR e por isso mantem as chamadas diretas.
trap 'echo "   FALHA nua pos-apply — executando rollback"; rollback_apply; exit 1' ERR
while IFS='|' read -r src dst; do
  [ -n "$src" ] || continue
  mkdir -p "$(dirname "$dst")"
  # Rail S318 P1: destino symlink e recusado tambem no apply (defesa em
  # profundidade com o G1 — cobre destino trocado entre G1 e G5).
  [ ! -L "$dst" ] || { echo "ABORT: destino e symlink: $dst"; rollback_apply; exit 1; }
  if [ "$dst" = ".claude/hooks/_lib/audit_emit.py" ]; then
    # audit_emit.py esta em _KERNEL_PATHS — o override e a rota ADR-031
    # §kernel-override para o apply sob sentinel; emite kernel_override_used.
    CEO_KERNEL_OVERRIDE=1 cp "$src" "$dst"
  else
    cp "$src" "$dst"
  fi
  echo "   applied $dst"
done <<AEOF
$MAP
AEOF

say "G6: touched-scope=vazio + checks vivos"
TOUCHED=$(git status --porcelain --untracked-files=all | awk '{print $2}' | sort)
SCOPE=$(printf '%s\n' "$MAP" | awk -F'|' '{print $2}'; printf '%s\n%s.asc\n' "$APPROVED" "$APPROVED")
SCOPE=$(printf '%s\n' "$SCOPE" | sort -u)
EXTRA=$(comm -23 <(printf '%s\n' "$TOUCHED") <(printf '%s\n' "$SCOPE") || true)
[ -z "$EXTRA" ] || { echo "ABORT: fora do escopo:"; echo "$EXTRA"; rollback_apply; exit 1; }
G6RC=0
python3 .claude/scripts/check-audit-registry-coverage.py || G6RC=1
python3 .claude/hooks/check_pair_rail.py --verify-codex-pin || G6RC=1
python3 -m pytest -q -p no:cacheprovider \
  .claude/hooks/tests/test_audit_emit_ceremony_lint_unlock.py \
  .claude/hooks/tests/test_w5_scrub_enforcement.py >/dev/null || G6RC=1
bash .claude/scripts/local/verify-counts.sh --quiet --no-tests || G6RC=1
python3 .claude/scripts/check-claude-md-claims.py || G6RC=1
[ "$G6RC" -eq 0 ] || { echo "ABORT: checks vivos vermelhos"; rollback_apply; exit 1; }
echo "   OK"

say "G7: commit"
GPG_OUT7=$(gpg --status-fd 1 --verify "$APPROVED.asc" "$APPROVED" 2>&1) \
  || { echo "ABORT: sentinel mudou apos G3"; rollback_apply; exit 1; }
printf '%s\n' "$GPG_OUT7" | grep '^\[GNUPG:\] VALIDSIG ' \
  | awk -v k="$OWNER_KEYID" '{ if ($3 ~ k"$" || $NF ~ k"$") found=1 } END { exit found?0:1 }' \
  || { echo "ABORT: signer mudou"; rollback_apply; exit 1; }
[ "$(sed -n 's/^Anchor-SHA: //p' "$APPROVED" | head -1)" = "$(git rev-parse HEAD)" ] \
  || { echo "ABORT: anchor != HEAD"; rollback_apply; exit 1; }
# shellcheck disable=SC2046
git add $(printf '%s\n' "$MAP" | awk -F'|' '{print $2}') "$APPROVED" "$APPROVED.asc"
git commit -m "ceremony(SENT-S318): emenda ADR-163 (p95 180 hard + p99 advisory com evidencia 2026-08-20) + re-pin codex 0.147.0 (ADR-182 §5) + registro/reposicao ceremony_lint_unlock_used (_KNOWN_ACTIONS 326, SPEC v2.57) + emendas ADR-001/ADR-079 que destravam PLAN-182 W1

Evidencia do gate: run 32408847458 falhou 3 attempts (110.6/302/162.1ms
p95) com local em 70.6ms — o runner mudou, nao os hooks; artifacts
N=1000 de 18-20/ago mostram a distribuicao movendo 1.5-2.3x entre
janelas. p99 num runner compartilhado precifica o runner (avenida
'demote p99 to advisory' ja deferida no proprio ADR-163). Provas:
wave2 PROOF GREEN com teto 180; retry-matrix 11/11; advisory com
controle positivo nos 2 sentidos; registry gate 0; 128 testes verdes
nas suites-alvo. Re-pin: payload 19c4f144... (0.147.0/darwin-arm64),
range <0.148.0 widen-upper-only fora de janela de release. Registro
do lint_unlock encerra a parcagem de 908707e no mesmo pack assinado
(shape kwargs top-level — o fields= de 7d467a8 nunca rodou vivo).

Sentinel: PLAN-174/S318-approved.md (GPG).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
trap - ERR  # commit feito — rollback deixa de ser o comportamento certo
echo
echo "PRONTO. Revise 'git show --stat HEAD' e rode: git push origin main"
