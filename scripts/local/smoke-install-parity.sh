#!/usr/bin/env bash
# PLAN-134 W1 item 6 — adopter-install parity smoke (Codex R4 fix #5,
# E8-F1/F3 class): dogfood must never go green while the installer ships
# STALE model-id pins to adopters.
#
# What it does:
#   1. install.sh into a mktemp target (default/maintainer ceremony,
#      non-interactive — same env knobs as .github/workflows/smoke-install.yml).
#   2. Run the INSTALLED tree's own validate-governance.sh — must pass.
#   3. Frontmatter pin check: every `model:` value inside *.md YAML
#      frontmatter (installed tree + repo templates/) must be in the
#      ADR-149 allowlist + governance tier ids + tier aliases.
#   4. Stale-literal scan: claude-opus-4-7 / claude-opus-4-6 /
#      claude-sonnet-3 / claude-3- anywhere in the installed tree or
#      templates/, minus test/fixture paths and a NARROW commented
#      allowlist of by-design historical-replay tables.
#   5. CLAUDE_CODE_SUBAGENT_MODEL in any installed/template settings
#      JSON must be in the allowed set (ADR-144: frontmatter is SoT;
#      the env knob must never re-pin a stale generation).
#
# Exit 0 = parity OK. Exit 1 = offenders listed on stderr. bash-3.2-safe.
#
# Usage:
#   bash scripts/local/smoke-install-parity.sh

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

TARGET="$(mktemp -d -t ceo-parity-XXXXXX)"
LOG="$(mktemp -t ceo-parity-log-XXXXXX)"
# Always cleanup, even on failure / set -e exit.
trap 'rm -rf "$TARGET" "$LOG"' EXIT

FAIL=0

# ---------------------------------------------------------------------------
# Allowed `model:` values for adopter-facing routing surfaces.
# Mirrors validate-governance.sh agent-frontmatter case (ADR-149 allowlist
# {claude-opus-4-8, claude-fable-5} + the two governance-ratified tier ids)
# plus the harness tier aliases. Empty value == inherit (allowed).
ALLOWED_MODELS="claude-opus-4-8 claude-fable-5 claude-sonnet-4-6 claude-haiku-4-5-20251001 haiku sonnet opus inherit"

is_allowed_model() {
  # $1 = candidate value (already trimmed). Empty == inherit == allowed.
  local v="$1" a
  [ -z "$v" ] && return 0
  for a in $ALLOWED_MODELS; do
    [ "$v" = "$a" ] && return 0
  done
  return 1
}

# Stale model-id literals that must never reach an adopter outside the
# exempted by-design files below.
STALE_RE='claude-opus-4-7|claude-opus-4-6|claude-sonnet-3|claude-3-'

# Path-CLASS exemptions (relative paths): test suites + fixtures keep old
# ids on purpose (negative cases, historical-log replay), backups and
# shadow files are not routing surfaces, logs are noise.
EXEMPT_PATH_RE='(^|/)(tests|fixtures)/|(^|/)test_[^/]*\.py$|_test\.py$|\.bak(\.|$)|\.shadow\.md$|\.log$|^\.git/'

# Per-FILE allowlist (relative paths) — by-design stale-id carriers.
# Keep narrow + commented (smoke-install.sh precedent). Every entry is a
# historical-REPLAY table or instructional content, NOT a routing pin:
#   ceo-cost/cost-table/budget-summary/audit-telemetry/success-receipt/
#   value-dashboard  — RETAINED HISTORICAL pricing rows (S227 rate card)
#   detectors/{wasteful_thinking,overpowered} — replay sets ("4-7 kept for
#     historical-log replay (ADR-142)")
#   optimizer/model_normalize — docstring on stripping claude-3-5- prefixes
#   generate-dispatch — label mapping for pre-4.8 ledger entries
#   spot-check-findings — known-id list for replaying old findings
#   hooks/_lib/adapters/live/claude.py — adaptive-thinking known-id table
#     (must recognize older generations in old transcripts)
#   skills ai-llm-orchestration / security-and-auth (+ owasp benchmark) —
#     instructional examples + model_baseline_version measurement anchor
ALLOWLIST_RE='\.claude/scripts/(ceo-cost\.py|cost-table\.yaml|budget-summary\.py|audit-telemetry\.py|success-receipt\.py|value-dashboard\.py|generate-dispatch\.py|spot-check-findings\.py|detectors/(wasteful_thinking|overpowered)\.py|optimizer/model_normalize\.py)|\.claude/hooks/_lib/adapters/live/claude\.py|\.claude/skills/core/(ai-llm-orchestration/SKILL\.md|security-and-auth/(SKILL\.md|benchmarks/owasp-llm-top-10\.yaml))'

# ---------------------------------------------------------------------------
echo "==> [1/5] install.sh (maintainer ceremony) into: $TARGET"
( cd "$TARGET" && git init -q )
if ! CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    bash "$REPO_ROOT/scripts/install.sh" "$TARGET" --profile core,frontend \
    >"$LOG" 2>&1; then
  echo "ERROR: install.sh failed (last 40 log lines follow)" >&2
  tail -40 "$LOG" >&2
  exit 1
fi
echo "    install.sh rc=0"

# ---------------------------------------------------------------------------
echo "==> [2/5] installed validate-governance.sh"
if ! ( cd "$TARGET" && bash .claude/scripts/validate-governance.sh >"$LOG" 2>&1 ); then
  echo "ERROR: validate-governance.sh FAILED in installed tree" >&2
  tail -40 "$LOG" >&2
  exit 1
fi
echo "    validate-governance rc=0"

# ---------------------------------------------------------------------------
echo "==> [3/5] frontmatter model: pin check (installed tree + templates/)"
scan_frontmatter() {
  # $1 = scan root, $2 = label for offender lines
  local root="$1" label="$2" f val
  while IFS= read -r f; do
    # Only YAML frontmatter: line 1 must be ---, stop at the closing ---.
    val="$(awk 'NR==1 { if ($0 != "---") exit; next }
                /^---[ \t]*$/ { exit }
                /^model:/ { sub(/^model:[ \t]*/, ""); sub(/[ \t\r]+$/, ""); print; exit }' "$f")"
    if ! is_allowed_model "$val"; then
      echo "OFFENDER(frontmatter): $label:${f#"$root"/}: model: $val" >&2
      FAIL=1
    fi
  done < <(find "$root" -name '*.md' -not -path '*/.git/*' -type f)
}
scan_frontmatter "$TARGET" "installed"
scan_frontmatter "$REPO_ROOT/templates" "templates"
echo "    frontmatter scan done"

# ---------------------------------------------------------------------------
echo "==> [4/5] stale model-id literal scan (installed tree + templates/)"
scan_stale_literals() {
  # $1 = scan root, $2 = label. Filter at the FILE level (paths only) so
  # exemption regexes can never accidentally match line content.
  local root="$1" label="$2" f rel
  while IFS= read -r f; do
    rel="${f#./}"
    if echo "$rel" | grep -Eq "$EXEMPT_PATH_RE"; then continue; fi
    if echo "$rel" | grep -Eq "^($ALLOWLIST_RE)$"; then continue; fi
    (cd "$root" && grep -nE "$STALE_RE" "$rel" 2>/dev/null || true) \
      | while IFS= read -r line; do
          echo "OFFENDER(stale-literal): $label:$rel:$line" >&2
        done
    FAIL=1
  done < <(cd "$root" && grep -rlE "$STALE_RE" . 2>/dev/null || true)
}
scan_stale_literals "$TARGET" "installed"
scan_stale_literals "$REPO_ROOT/templates" "templates"
echo "    literal scan done"

# ---------------------------------------------------------------------------
echo "==> [5/5] CLAUDE_CODE_SUBAGENT_MODEL in settings JSON"
scan_settings_env() {
  # $1 = scan root, $2 = label
  local root="$1" label="$2" f val
  while IFS= read -r f; do
    val="$(grep -hoE '"CLAUDE_CODE_SUBAGENT_MODEL"[[:space:]]*:[[:space:]]*"[^"]*"' "$f" \
      | sed -E 's/^"CLAUDE_CODE_SUBAGENT_MODEL"[[:space:]]*:[[:space:]]*"([^"]*)"$/\1/' \
      | head -1 || true)"
    # No key in this file → nothing to assert.
    if grep -q '"CLAUDE_CODE_SUBAGENT_MODEL"' "$f" && ! is_allowed_model "$val"; then
      echo "OFFENDER(settings-env): $label:${f#"$root"/}: CLAUDE_CODE_SUBAGENT_MODEL=$val" >&2
      FAIL=1
    fi
  done < <(find "$root" -name 'settings*.json' -not -path '*/.git/*' -type f)
}
scan_settings_env "$TARGET" "installed"
scan_settings_env "$REPO_ROOT/templates" "templates"
echo "    settings scan done"

# ---------------------------------------------------------------------------
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAIL — stale model pins above must be fixed (canonical files" >&2
  echo "        via Owner ceremony; templates/ directly)." >&2
  exit 1
fi
echo "RESULT: PASS — adopter install carries no stale model pins"
