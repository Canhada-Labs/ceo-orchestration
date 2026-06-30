#!/usr/bin/env bash
# OWNER-CEREMONY-S82-V1120.sh
# Session 82 paralelo ceremony lote — bundle v1.12.0-rc.1
# 3 GPG sentinel signs (PLAN-069 Wave D + PLAN-074 Wave 0 + PLAN-065 Phase 2)
# + apply 3 canonical diffs (audit_emit register + canonical_guards extends + VETO_FLOOR_ROLES)
# + commit + tag v1.12.0-rc.1
#
# Owner physical: 3 GPG passphrase prompts consecutive (~30s each).
# Total Owner time: ~2 minutes. Total wall-clock: ~3-5 minutes.
#
# Pre-flight verified by main thread CEO:
# - All 3 sentinels at canonical paths (.claude/plans/PLAN-{065,069,074}/architect/.../approved.md)
# - All 3 canonical diffs at /tmp/track-{C,H}-canonical.diff + /tmp/track-H-veto-floor.diff
# - ADR-098 DRAFT at .claude/plans/PLAN-065/architect/phase-2/ADR-098-DRAFT-...md
# - 30/30 ceo-boot tests + 104+6 ceo-boot-related tests pass
# - Codex MCP final pass GO (threadId 019df3cb-7cd0-7ea3-9b18-b7e6cb36215d)
# - validate-governance.sh: 0 errors / 6 warnings advisory

set -euo pipefail

cd "$(dirname "$0")/../.."

OWNER_KEY="0000000000000000000000000000000000000000"
REPO_ROOT="$(pwd)"

# Pre-flight checks
echo "=== Pre-flight ==="
test -f .claude/plans/PLAN-069/architect/wave-d/approved.md  || { echo "MISSING PLAN-069 sentinel"; exit 1; }
test -f .claude/plans/PLAN-074/architect/round-1/approved.md || { echo "MISSING PLAN-074 sentinel"; exit 1; }
test -f .claude/plans/PLAN-065/architect/phase-2/approved.md || { echo "MISSING PLAN-065 sentinel"; exit 1; }
test -f /tmp/track-C-canonical.diff   || { echo "MISSING track-C canonical diff"; exit 1; }
test -f /tmp/track-H-canonical.diff   || { echo "MISSING track-H canonical diff"; exit 1; }
test -f /tmp/track-H-veto-floor.diff  || { echo "MISSING track-H veto-floor diff"; exit 1; }
echo "OK: 3 sentinels + 3 diffs ready."

# Ensure clean tree (only the 3 sentinels are new, plus pre-existing untracked from S82)
echo "=== Pre-flight: git status ==="
git status -sb | head -20

# === GPG SIGN 1/3: PLAN-069 Wave D ===
echo
echo "=== GPG SIGN 1/3: PLAN-069 Wave D approved.md ==="
echo "    Owner key: ${OWNER_KEY:0:16}..."
gpg --local-user "$OWNER_KEY" --detach-sign --armor \
    --output .claude/plans/PLAN-069/architect/wave-d/approved.md.asc \
    .claude/plans/PLAN-069/architect/wave-d/approved.md
gpg --verify \
    .claude/plans/PLAN-069/architect/wave-d/approved.md.asc \
    .claude/plans/PLAN-069/architect/wave-d/approved.md
echo "OK: PLAN-069 sentinel signed + verified."

# === GPG SIGN 2/3: PLAN-074 Wave 0 ===
echo
echo "=== GPG SIGN 2/3: PLAN-074 Wave 0 approved.md ==="
gpg --local-user "$OWNER_KEY" --detach-sign --armor \
    --output .claude/plans/PLAN-074/architect/round-1/approved.md.asc \
    .claude/plans/PLAN-074/architect/round-1/approved.md
gpg --verify \
    .claude/plans/PLAN-074/architect/round-1/approved.md.asc \
    .claude/plans/PLAN-074/architect/round-1/approved.md
echo "OK: PLAN-074 sentinel signed + verified."

# === GPG SIGN 3/3: PLAN-065 Phase 2 ===
echo
echo "=== GPG SIGN 3/3: PLAN-065 Phase 2 approved.md ==="
gpg --local-user "$OWNER_KEY" --detach-sign --armor \
    --output .claude/plans/PLAN-065/architect/phase-2/approved.md.asc \
    .claude/plans/PLAN-065/architect/phase-2/approved.md
gpg --verify \
    .claude/plans/PLAN-065/architect/phase-2/approved.md.asc \
    .claude/plans/PLAN-065/architect/phase-2/approved.md
echo "OK: PLAN-065 sentinel signed + verified."

# === APPLY CANONICAL DIFFS (sentinels grant permission) ===
echo
echo "=== APPLY: Track H canonical_guards extends ==="
git apply --check /tmp/track-H-canonical.diff
git apply /tmp/track-H-canonical.diff

echo "=== APPLY: Track H VETO_FLOOR_ROLES register ==="
git apply --check /tmp/track-H-veto-floor.diff
git apply /tmp/track-H-veto-floor.diff

echo "=== APPLY: Track C audit_emit register (ceo_boot_emitted + check_skipped) ==="
git apply --check /tmp/track-C-canonical.diff
git apply /tmp/track-C-canonical.diff

# === ADR-098 git mv DRAFT → canonical path ===
echo
echo "=== git mv: ADR-098 DRAFT → canonical ==="
git mv .claude/plans/PLAN-065/architect/phase-2/ADR-098-DRAFT-ceo-boot-audit-emit-register.md \
       .claude/adr/ADR-098-ceo-boot-audit-emit-register.md

# === Run validation ===
echo
echo "=== Validate governance + run tests ==="
bash .claude/scripts/validate-governance.sh 2>&1 | tail -3
python3 -m pytest .claude/hooks/tests/test_audit_emit.py .claude/scripts/tests/test_ceo_boot.py .claude/scripts/tests/test_ceo_boot_audit_emit.py .claude/scripts/tests/test_extract_skill.py -q 2>&1 | tail -3

# === Bump VERSION 1.11.7 → 1.12.0 ===
echo
echo "=== Bump VERSION 1.11.7 → 1.12.0 ==="
echo "1.12.0" > VERSION
python3 -c "
import json
with open('npm/package.json') as f:
    pkg = json.load(f)
pkg['version'] = '1.12.0'
with open('npm/package.json', 'w') as f:
    json.dump(pkg, f, indent=2)
    f.write('\n')
"

# === Stage + commit ===
echo
echo "=== Commit canonical bundle ==="
git add -A
git status -sb | head -20

git commit -m "feat(v1.12.0): bundle Tracks B/C/H + PLAN-065 Phase 2 canonical + PLAN-069 Wave D + PLAN-074 Wave 0 (S82 ceremony)

Single ceremony lote signs 3 sentinels + applies 3 canonical diffs:

PLAN-065 Phase 2 audit_emit canonical register
- _KNOWN_ACTIONS adds ceo_boot_emitted + ceo_boot_check_skipped (97 → 99)
- 2 emit functions with Sec MF-3 field allowlist (gate_pass / duration_ms /
  checks_total / checks_failed / cache_hit; denies tokens/cost/paths/prompt/SKILL/env)
- ADR-098 ACCEPTED (was DRAFT)
- SPEC v1 audit-log.schema.md v2.16 → v2.17
- Closes Reality-Ledger fixture #4 (declared-but-not-wired) per PLAN-071 Phase 0
- 6 Track C tests flip skip → pass automatically (TestRealityLedgerClosure)

PLAN-069 Wave D plan-close
- frontmatter status: draft → reviewed
- adrs_proposed slug correction: ADR-101-snapshot-review-helper → ADR-101-replay-redact-helper
- external_wait: codex-re-pass-pre-tag → v1.12.0-train-assembly

PLAN-074 Wave 0 hardening
- _CANONICAL_GUARDS extends to .claude/agents/*.md + .claude/skills/domains/**/SKILL.md recursive
- VETO_FLOOR_ROLES adds 4 slugs (threat-detection-engineer / identity-trust-architect /
  incident-commander / llm-finops-architect)
- 4 Track H mutation-pin tests flip skip → pass

3 GPG sentinels signed by Owner key 0000000000000000000000000000000000000000.
Sentinel approved.md.asc files cover canonical-edit hook scope per ADR-051.

Bundle authorized via S82 paralelo Owner directive 2026-05-04 'velocidade
maxima objetivo terminar TODOS os planos em 24h humanas'.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"

# === Tag v1.12.0-rc.1 ===
echo
echo "=== Tag v1.12.0-rc.1 ==="
git tag -a v1.12.0-rc.1 -m "v1.12.0-rc.1 — S82 ceremony lote bundle (Tracks B/C/H canonical + closures)"

# === Push (Owner confirms) ===
echo
echo "=== READY TO PUSH ==="
echo "Run manually:"
echo "  git push origin main"
echo "  git push origin v1.12.0-rc.1"
echo
echo "After Codex MCP re-pass GREEN (main thread will run):"
echo "  git tag -a v1.12.0 -m 'v1.12.0 GA — S82 ceremony lote bundle'"
echo "  git push origin v1.12.0"
echo
echo "=== CEREMONY COMPLETE ==="
git log -1 --oneline
