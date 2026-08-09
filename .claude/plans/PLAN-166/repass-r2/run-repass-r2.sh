#!/bin/bash
# =============================================================================
# PLAN-166 W2 / PLAN-169 W6.1 — re-pass codex round 2 (pré-rc.2).
#
# Revisa o DELTA v1.3.0-rc.1..CANDIDATO (W0+W1+W2 do PLAN-169) a partir de
# um WORKTREE DETACHED LIMPO no SHA candidato (nota de protocolo r3/r17 do
# PLAN-166 W2 — a tag rc.2 ainda não existe; worktree da TAG é só no
# re-pass final pós-hold). Pipeline idêntico ao r1: prompt + diff →
# redactor ADR-114 → controles anti-truncamento → codex read-only.
#
# Uso: bash .claude/plans/PLAN-166/repass-r2/run-repass-r2.sh
# Saída: verdict-r2.txt + transcript-r2.log + PROVENANCE-r2.md neste dir.
# Codex leva ~10-15 min. Espere o ARTEFATO (verdict-r2.txt não-vazio),
# nunca pgrep (lição feedback-pgrep-waiter-matches-itself).
# =============================================================================
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
OUT="$REPO_ROOT/.claude/plans/PLAN-166/repass-r2"
BASE_TAG="v1.3.0-rc.1"
CAND_SHA="$(git rev-parse HEAD)"

# Worktree limpo detached no candidato (a leitura viva do reviewer sob
# --sandbox read-only enxerga a árvore de onde ele roda — tem de ser o
# SNAPSHOT LIMPO do candidato, não a árvore de trabalho).
WT="$(mktemp -d "${TMPDIR:-/tmp}/repass-r2.XXXXXX")/wt"
git worktree add --detach "$WT" "$CAND_SHA" >/dev/null
trap 'git worktree remove --force "$WT" >/dev/null 2>&1 || true' EXIT
[ -z "$(git -C "$WT" status --porcelain)" ] || { echo "FATAL: worktree sujo"; exit 1; }

RAW="$OUT/payload.raw.txt"; RED="$OUT/payload.redacted.txt"
DIFF="$OUT/delta-rc1-to-candidate.diff"

git diff "$BASE_TAG".."$CAND_SHA" > "$DIFF"
DIFF_LINES=$(wc -l < "$DIFF" | tr -d ' ')
[ "$DIFF_LINES" -ge 50 ] || { echo "FATAL: diff só $DIFF_LINES linhas — escopo colapsou"; exit 1; }

{
  cat <<'PROMPT'
You are the cross-model release re-pass reviewer (round 2) for the
v1.3.0-rc.2 cut of a governance framework. Below is the COMPLETE diff
from the already-reviewed v1.3.0-rc.1 parent to the rc.2 candidate.
The delta is closure work: plan bookkeeping (W0), a Linux port of an
e2e test harness with fail-closed mtime riders (W1), and verified
fixes on free surfaces — perf-probe N/percentile hygiene, an exact-
resolution ladder for an agent-context injector, a pair-rail preflight
auth-route fix, release bump-site coverage, doc-count watchers,
debate-convergence semantics, and current-fleet model-id data fixes
(W2). Staged-but-NOT-applied ceremony material under
.claude/plans/PLAN-169/staged-w3/ ships as plan evidence only — it is
NOT live code; review it only for "would landing this later be sane",
not as active surface.

Your job: find anything in this delta that makes cutting rc.2 UNSAFE —
regressions, gates weakened, fail-open introduced, claims the diff
does not support, release mechanics broken. Classify findings P1
(blocks the cut) / P2 (fix-forward acceptable) / P3 (note). End with
exactly one line: VERDICT: APPROVE or VERDICT: NEEDS-CHANGES, followed
by a one-paragraph justification.
PROMPT
  echo ""
  echo "=== DIFF ${BASE_TAG}..${CAND_SHA} (${DIFF_LINES} lines) ==="
  cat "$DIFF"
} > "$RAW"

python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing < "$RAW" > "$RED"
RC=$?; [ "$RC" -eq 0 ] || { echo "FATAL: redactor rc=$RC (fail-closed)"; exit 1; }
[ -s "$RED" ] || { echo "FATAL: payload redigido vazio"; exit 1; }
RAW_HUNKS=$(grep -c '^@@' "$RAW" || true); RED_HUNKS=$(grep -c '^@@' "$RED" || true)
[ "$RAW_HUNKS" = "$RED_HUNKS" ] || { echo "FATAL: hunks $RAW_HUNKS -> $RED_HUNKS (estrutura perdida)"; exit 1; }

shasum -a 256 "$RED" "$DIFF" > "$OUT/MANIFEST-r2.sha256"

cat > "$OUT/PROVENANCE-r2.md" <<PROV
# Proveniência do re-pass round 2 — candidato rc.2

- Base: ${BASE_TAG} · Candidato: ${CAND_SHA}
- Worktree detached limpo: sim (assert vazio de git status)
- Payload: prompt + diff completo → codex_egress_redact.py --outgoing
- Controles: diff >=50 linhas; hunks preservados pós-redação; manifest
  sha256 em MANIFEST-r2.sha256 (inputs_hash = sha256 do payload.redacted)
- Invocação (executada do WORKTREE):
  nohup codex exec --sandbox read-only --color never \\
    --output-last-message $OUT/verdict-r2.txt \\
    - < $RED > $OUT/transcript-r2.log 2>&1 &
- Data: $(date -u +%Y-%m-%dT%H:%MZ)
PROV

cd "$WT"
nohup codex exec --sandbox read-only --color never \
  --output-last-message "$OUT/verdict-r2.txt" \
  - < "$RED" > "$OUT/transcript-r2.log" 2>&1 &
CODEX_PID=$!
echo "codex re-pass r2 lançado (pid $CODEX_PID) do worktree limpo $WT"
echo "candidato: $CAND_SHA · payload: $(wc -c < "$RED" | tr -d ' ') bytes"
echo "acompanhe: tail -f $OUT/transcript-r2.log · verdito: $OUT/verdict-r2.txt"
# Segura o trap até o codex terminar para não remover o worktree sob ele.
wait "$CODEX_PID" || true
echo "codex terminou. Verdito:"
tail -3 "$OUT/verdict-r2.txt" 2>/dev/null || echo "(verdict-r2.txt vazio — inspecione o transcript)"
