#!/bin/bash
# =============================================================================
# PLAN-166 W2 / PLAN-169 W6.1 — re-pass codex round 2 (pré-rc.2), MULTI-PART.
#
# O delta vivo rc.1→candidato tem ~790KB — acima do cap de 256KB do
# redactor ADR-114 (r2 v1: truncamento pego pelo controle de hunks;
# r2 v2: marcador CODEX-OUTPUT-TRUNCATED explícito). Partição em 5
# sub-payloads coerentes, revisados SEQUENCIALMENTE pelo mesmo pipeline
# do r1 (prompt + diff → redactor → controles → codex read-only de
# worktree detached limpo). O verdito agregado exige APPROVE em TODAS
# as partes — qualquer NEEDS-CHANGES bloqueia o corte até triagem.
#
# `.claude/plans/**` fica FORA por escopo (evidência de plano, não
# código ativo — mesmo princípio do paths.manifest.txt do r1).
#
# Uso: bash .claude/plans/PLAN-166/repass-r2/run-repass-r2.sh
# Saída por parte: payload-<p>.redacted.txt, transcript-<p>.log,
# verdict-<p>.txt; agregado em VERDICTS-SUMMARY.txt + PROVENANCE-r2.md.
# ~10-15 min/parte ⇒ 50-75 min total. Espere o ARTEFATO
# (VERDICTS-SUMMARY.txt), nunca pgrep.
# =============================================================================
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
OUT="$REPO_ROOT/.claude/plans/PLAN-166/repass-r2"
BASE_TAG="v1.3.0-rc.1"
CAND_SHA="$(git rev-parse HEAD)"

WT="$(mktemp -d "${TMPDIR:-/tmp}/repass-r2.XXXXXX")/wt"
git worktree add --detach "$WT" "$CAND_SHA" >/dev/null || exit 2
trap 'git worktree remove --force "$WT" >/dev/null 2>&1 || true' EXIT
[ -z "$(git -C "$WT" status --porcelain)" ] || { echo "FATAL: worktree sujo"; exit 2; }

# Partes: nome + pathspec (negações excluem sobreposição). plans/** fora.
part_paths() {
  case "$1" in
    a) echo "scripts/ :!scripts/tests/ .gitignore AGENTS.md" ;;
    b) echo "scripts/tests/" ;;
    c) echo ".claude/scripts/ :!.claude/scripts/tests/ :!.claude/scripts/model-deprecations.json" ;;
    d) echo ".claude/scripts/tests/" ;;
    e) echo ".claude/hooks/ docs/ .github/ README.md README.pt-BR.md CHANGELOG.md :!.claude/plans/" ;;
  esac
}
part_label() {
  case "$1" in
    a) echo "framework scripts (install/upgrade/generator) + root hygiene" ;;
    b) echo "e2e harness scripts/tests (W1 Linux port + riders)" ;;
    c) echo "governance scripts .claude/scripts (W2 fixes)" ;;
    d) echo "script test suites .claude/scripts/tests" ;;
    e) echo "hooks tests + docs + workflows + root docs" ;;
  esac
}

PROMPT_HEADER='You are the cross-model release re-pass reviewer (round 2) for the
v1.3.0-rc.2 cut of a governance framework. The live-surface delta from
the reviewed v1.3.0-rc.1 parent is SPLIT across 5 scoped payloads
(this is one of them; each is judged independently and the cut needs
APPROVE on all). Everything under .claude/plans/** is plan evidence
(debate records, staged-NOT-applied ceremony material, runbooks) and
is excluded by scope, as round 1 scoped by path manifest. The delta
is closure work landed since rc.1: the PLAN-167/168 ownership-decision
rewrite of install/upgrade, a Linux port of the e2e harness with
fail-closed mtime riders, and verified free-surface fixes (perf-probe
percentile hygiene, injector exact-resolution, pair-rail auth routes,
bump-site coverage, count watchers, debate-convergence semantics,
current-fleet model-id data, doc cures). One payload exclusion, by
provenance: .claude/scripts/model-deprecations.json (10 replacement
values mechanically bumped to the current fleet, W2.10 F9) is excluded
because the egress redactor rewrites model-ledger content and destroys
the diff structure (round-2 part-c FATAL control); judge that change
from this description.

Your job: find anything in THIS payload that makes cutting rc.2
UNSAFE — regressions, weakened gates, fail-open introduced, claims the
diff does not support, broken release mechanics. Classify P1 (blocks
the cut) / P2 (fix-forward acceptable) / P3 (note). End with exactly
one line: VERDICT: APPROVE or VERDICT: NEEDS-CHANGES, plus one
justification paragraph.'

: > "$OUT/VERDICTS-SUMMARY.txt"
{
  echo "# Proveniência do re-pass round 2 (multi-part) — candidato rc.2"
  echo "- Base: ${BASE_TAG} · Candidato: ${CAND_SHA}"
  echo "- Worktree detached limpo: sim · Pipeline: prompt+diff → codex_egress_redact --outgoing → controles → codex exec --sandbox read-only"
  echo "- Partição por cap do redactor (256KB): 5 partes; hunks preservados assertados por parte; truncamento = FATAL"
  echo "- Data: $(date -u +%Y-%m-%dT%H:%MZ)"
  echo ""
} > "$OUT/PROVENANCE-r2.md"

OVERALL=0
for P in a b c d e; do
  PATHS="$(part_paths "$P")"; LABEL="$(part_label "$P")"
  RAW="$OUT/payload-$P.raw.txt"; RED="$OUT/payload-$P.redacted.txt"
  # shellcheck disable=SC2086
  git diff "$BASE_TAG".."$CAND_SHA" -- $PATHS > "$OUT/diff-$P.patch"
  DL=$(wc -l < "$OUT/diff-$P.patch" | tr -d ' ')
  if [ "$DL" -lt 5 ]; then
    echo "part $P: diff vazio ($DL linhas) — pulando" | tee -a "$OUT/VERDICTS-SUMMARY.txt"
    continue
  fi
  {
    printf '%s\n\n' "$PROMPT_HEADER"
    printf 'PAYLOAD %s/5: %s\n' "$P" "$LABEL"
    printf '=== DIFF %s..%s (parte %s, %s linhas) ===\n' "$BASE_TAG" "$CAND_SHA" "$P" "$DL"
    cat "$OUT/diff-$P.patch"
  } > "$RAW"
  RAWB=$(wc -c < "$RAW" | tr -d ' ')
  if [ "$RAWB" -ge 250000 ]; then
    echo "FATAL part $P: payload ${RAWB}B >= 250KB — re-particione" | tee -a "$OUT/VERDICTS-SUMMARY.txt"
    OVERALL=1; continue
  fi
  python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing < "$RAW" > "$RED" \
    || { echo "FATAL part $P: redactor rc!=0" | tee -a "$OUT/VERDICTS-SUMMARY.txt"; OVERALL=1; continue; }
  if grep -q 'CODEX-OUTPUT-TRUNCATED' "$RED"; then
    echo "FATAL part $P: truncado no redactor" | tee -a "$OUT/VERDICTS-SUMMARY.txt"; OVERALL=1; continue
  fi
  RH=$(grep -c '^@@' "$RAW" || true); DH=$(grep -c '^@@' "$RED" || true)
  if [ "$RH" != "$DH" ]; then
    echo "FATAL part $P: hunks $RH -> $DH" | tee -a "$OUT/VERDICTS-SUMMARY.txt"; OVERALL=1; continue
  fi
  echo "part $P ($LABEL): payload ${RAWB}B, $RH hunks — codex rodando..."
  ( cd "$WT" && codex exec --sandbox read-only --color never \
      --output-last-message "$OUT/verdict-$P.txt" \
      - < "$RED" > "$OUT/transcript-$P.log" 2>&1 )
  CRC=$?
  VLINE=$(grep -E '^VERDICT:' "$OUT/verdict-$P.txt" 2>/dev/null | tail -1 || true)
  [ -n "$VLINE" ] || VLINE="(sem linha VERDICT — inspecionar transcript; rc=$CRC)"
  echo "part $P ($LABEL): $VLINE [codex rc=$CRC]" | tee -a "$OUT/VERDICTS-SUMMARY.txt"
  case "$VLINE" in *APPROVE*) : ;; *) OVERALL=1 ;; esac
done

shasum -a 256 "$OUT"/payload-*.redacted.txt "$OUT"/diff-*.patch > "$OUT/MANIFEST-r2.sha256" 2>/dev/null || true
{
  echo ""
  echo "## Resultado agregado"
  cat "$OUT/VERDICTS-SUMMARY.txt" | sed 's/^/- /'
  echo "- OVERALL: $( [ "$OVERALL" -eq 0 ] && echo 'ALL-APPROVE (corte liberado pelo rail; verdito assinado é do Owner)' || echo 'HÁ PARTE SEM APPROVE — triagem antes do corte' )"
} >> "$OUT/PROVENANCE-r2.md"
echo ""
echo "=== AGREGADO ==="
cat "$OUT/VERDICTS-SUMMARY.txt"
exit "$OVERALL"
