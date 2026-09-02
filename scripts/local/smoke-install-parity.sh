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
#      claude-opus-4-1 / claude-sonnet-3 / claude-3- anywhere in the
#      installed tree or templates/, minus test/fixture paths and a NARROW
#      commented allowlist of by-design historical-replay tables.
#   5. CLAUDE_CODE_SUBAGENT_MODEL in any installed/template settings
#      JSON must be in the allowed set (ADR-144: frontmatter is SoT;
#      the env knob must never re-pin a stale generation).
#   6. Installed availableModels/fallbackModel assert (PLAN-163 T1.7,
#      codex F9): the installed .claude/settings.json must carry the
#      ADR-149 working set EXACTLY and IN ORDER (order is normative —
#      the first entry participates in default resolution) and the
#      fallback chain must be exactly ["claude-opus-5"] (ADR-181/OQ1=b).
#      ALLOWED_MODELS membership alone is NOT evidence — this step
#      byte-compares the arrays. It ALSO asserts the installed top-level
#      default `model` == claude-opus-5 (PLAN-163 T1.1 pin; R2-B3): a
#      stale default can regress post-install WITHOUT touching the arrays
#      above, so array parity alone does not prove the default pin. The
#      default must additionally be a member of the installed
#      availableModels (an unresolvable default is a parity failure).
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
# PLAN-163 T1.7 (ADR-181): claude-opus-5 + claude-sonnet-5 appended —
# Claude 5 refresh working-set members (additive; membership here is a
# frontmatter/env lint only, NOT the availableModels evidence — see [6/6]).
# ADR-149 Amendment 2 (S338): claude-fable-5-1 appended (working set only).
ALLOWED_MODELS="claude-opus-4-8 claude-fable-5 claude-sonnet-4-6 claude-haiku-4-5-20251001 claude-opus-5 claude-sonnet-5 claude-fable-5-1 haiku sonnet opus inherit"

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
# PLAN-163 T1.8 (CF-11): += claude-opus-4-1 — retires 2026-08-05
# (model-deprecations.json fuse). Born-green in the live tree, so the
# addition is proven by the planted positive control in
# scripts/tests/test-parity-stale-planted.sh (FOLLOWUP planted-fixture
# pattern). Allowlist-delta audit (static enumeration + live-fire run of
# THIS script, 2026-07-28): model-deprecations.json and
# .claude/data/canonical_models.json carry the id by design but sit
# OUTSIDE this scan's scope (not installed / not under templates/) — no
# delta; check-model-deprecations.py IS installed and its build_matcher
# docstring carries opus-4-1 literals by design → ALLOWLIST_RE delta below
# (the static audit missed it; the live-fire run caught it).
STALE_RE='claude-opus-4-7|claude-opus-4-6|claude-opus-4-1|claude-sonnet-3|claude-3-'

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
#   check-model-deprecations — the deprecation instrument itself; its
#     build_matcher docstring cites retired ids by design (PLAN-163 T1.8;
#     mirrors the ledger's own 'deprecation-instrument' inert rule)
#   hooks/_lib/adapters/live/claude.py — adaptive-thinking known-id table
#     (must recognize older generations in old transcripts)
#   skills ai-llm-orchestration / security-and-auth (+ owasp benchmark +
#     references/owasp.md) — instructional examples +
#     model_baseline_version measurement anchor (references/owasp.md added
#     PLAN-163 T1.8: the PLAN-153 skill import landed it AFTER this scan
#     was authored — latent pre-existing offender caught by live-fire)
ALLOWLIST_RE='\.claude/scripts/(ceo-cost\.py|cost-table\.yaml|budget-summary\.py|audit-telemetry\.py|success-receipt\.py|value-dashboard\.py|generate-dispatch\.py|spot-check-findings\.py|check-model-deprecations\.py|detectors/(wasteful_thinking|overpowered)\.py|optimizer/model_normalize\.py)|\.claude/hooks/_lib/adapters/live/claude\.py|\.claude/skills/core/(ai-llm-orchestration/SKILL\.md|security-and-auth/(SKILL\.md|benchmarks/owasp-llm-top-10\.yaml|references/owasp\.md))'

# ---------------------------------------------------------------------------
echo "==> [1/6] install.sh (maintainer ceremony) into: $TARGET"
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
echo "==> [2/6] installed validate-governance.sh"
if ! ( cd "$TARGET" && bash .claude/scripts/validate-governance.sh >"$LOG" 2>&1 ); then
  echo "ERROR: validate-governance.sh FAILED in installed tree" >&2
  tail -40 "$LOG" >&2
  exit 1
fi
echo "    validate-governance rc=0"

# ---------------------------------------------------------------------------
echo "==> [3/6] frontmatter model: pin check (installed tree + templates/)"
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
echo "==> [4/6] stale model-id literal scan (installed tree + templates/)"
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
echo "==> [5/6] CLAUDE_CODE_SUBAGENT_MODEL in settings JSON"
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
echo "==> [6/6] installed model pin + availableModels order + fallbackModel assert"
INSTALLED_SETTINGS="$TARGET/.claude/settings.json"
if [ ! -f "$INSTALLED_SETTINGS" ]; then
  echo "OFFENDER(models): installed .claude/settings.json missing" >&2
  FAIL=1
elif ! python3 - "$INSTALLED_SETTINGS" <<'PY'
import json, sys

# ADR-149 AVAILABLE_MODELS_WORKING_SET — order is normative (ADR-149
# Amendment 1 A1.1; new ids appended at the end per ADR-181). Regen via
# python3 .claude/scripts/generate-available-models.py on drift.
EXPECTED_AVAILABLE = [
    "claude-opus-4-8",
    "claude-fable-5",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-fable-5-1",  # ADR-149 Amendment 2 (S338) — appended at the end
]
# ADR-149 FALLBACK_MODEL_CHAIN (ADR-181 / PLAN-163 OQ1=b).
EXPECTED_FALLBACK = ["claude-opus-5"]
# PLAN-163 T1.1 (ADR-181) — the installed top-level default `model` pin.
# This is the value the harness resolves to when no per-turn override is
# given; a stale default can regress post-install WITHOUT perturbing the
# arrays above, so it is asserted independently (R2-B3).
EXPECTED_MODEL = "claude-opus-5"

try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:  # unreadable/invalid settings = parity failure
    sys.stderr.write("OFFENDER(models): settings unreadable: %s\n" % exc)
    sys.exit(1)

rc = 0
avail = data.get("availableModels")
if avail != EXPECTED_AVAILABLE:
    sys.stderr.write(
        "OFFENDER(models): installed availableModels != ADR-149 working "
        "set (ORDER included)\n  expected: %s\n  actual  : %s\n"
        % (EXPECTED_AVAILABLE, avail)
    )
    rc = 1
fb = data.get("fallbackModel")
if isinstance(fb, str):
    fb = [fb]
if fb != EXPECTED_FALLBACK:
    sys.stderr.write(
        "OFFENDER(models): installed fallbackModel != %s (actual: %s)\n"
        % (EXPECTED_FALLBACK, fb)
    )
    rc = 1
# PLAN-163 T1.1 / R2-B3 — top-level default `model` pin. Full equality
# (order-irrelevant scalar); membership in availableModels is NOT the
# same evidence — the pin can regress without touching the arrays.
model = data.get("model")
if model != EXPECTED_MODEL:
    sys.stderr.write(
        "OFFENDER(models): installed top-level model != %r (actual: %r)\n"
        % (EXPECTED_MODEL, model)
    )
    rc = 1
# The pinned default must also be a member of the installed working set
# (a default outside availableModels is unresolvable at runtime).
if isinstance(avail, list) and model is not None and model not in avail:
    sys.stderr.write(
        "OFFENDER(models): installed top-level model %r not in "
        "installed availableModels %s\n" % (model, avail)
    )
    rc = 1
sys.exit(rc)
PY
then
  FAIL=1
fi
echo "    model/availableModels/fallbackModel assert done"

# ---------------------------------------------------------------------------
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAIL — stale model pins above must be fixed (canonical files" >&2
  echo "        via Owner ceremony; templates/ directly)." >&2
  exit 1
fi
echo "RESULT: PASS — adopter install carries no stale model pins"
