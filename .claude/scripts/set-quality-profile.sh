#!/usr/bin/env bash
# PLAN-025 Batch L — set-quality-profile.sh
#
# Sets the ceo-orchestration quality profile — rewrites the canonical-5
# native subagent .md files' `model:` frontmatter field per profile:
#
#   max-quality  → 2 VETO-floor + 3 Opus 4.8    (baseline velocity, 100% cost)
#   balanced     → 2 VETO-floor + 3 Sonnet 4.6  (DEFAULT; ~3.5x velocity, ~56% cost)
#   max-speed    → 2 VETO-floor + 3 Haiku 4.5   (~5-6x velocity, ~22% cost)
#
# INVARIANT: code-reviewer + security-engineer ALWAYS carry the VETO-floor
# model DERIVED from tier_policy_cli._constants.VETO_HARDCODE (currently
# claude-fable-5) — never a literal in this file. PLAN-169 W4.3 F1.
# The `balanced` line above used to claim "2 Opus + 2 Sonnet + 1 Haiku";
# the code has always written 3 Sonnet.
#
# Usage:
#   bash .claude/scripts/set-quality-profile.sh max-quality
#   bash .claude/scripts/set-quality-profile.sh balanced
#   bash .claude/scripts/set-quality-profile.sh max-speed
#   bash .claude/scripts/set-quality-profile.sh --show          # print current
#   bash .claude/scripts/set-quality-profile.sh --help
#
# See docs/QUALITY-PROFILES.md for full context.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
AGENTS_DIR="${REPO_ROOT}/.claude/agents"
SETTINGS_JSON="${REPO_ROOT}/.claude/settings.json"

_usage() {
  cat <<'EOF'
Usage: set-quality-profile.sh <profile> | --show | --help

Profiles:
  max-quality   2 VETO-floor + 3 Opus 4.8 (100% cost, baseline velocity)
  balanced      2 VETO-floor + 3 Sonnet 4.6 (~56% cost, 3.5x velocity; DEFAULT)
  max-speed     2 VETO-floor + 3 Haiku 4.5 (~22% cost, 5-6x velocity)

Invariant: code-reviewer + security-engineer ALWAYS on the VETO floor derived
           from tier_policy_cli._constants.VETO_HARDCODE (never a literal).

See docs/QUALITY-PROFILES.md for full details.
EOF
}

# ---- PLAN-169 W4.3 F1 / PLAN-183 W3 — veto-downgrade CURED ----
# The two VETO slots are DERIVED from the authority, never written as a
# literal here.
#
# Before this cure all three profiles pinned code-reviewer and
# security-engineer to the literal `claude-opus-4-8` while
# `.claude/agents/*.md` shipped `claude-fable-5`. Any invocation —
# `max-quality` included — moved the VETO floor two generations DOWN, and
# no rail saw it: the write is `awk`+`mv` inside this script, while
# `check_canonical_edit.py` and `check_tier_policy.py` match on the
# Edit|Write|MultiEdit TOOL, `check_bash_safety._e3_check_canonical_path_write`
# sees no write target on the command line, and
# `.claude/scripts/validate-governance.sh` accepts any member of the
# ADR-149 working set role-AGNOSTICALLY. The downgrade was legal
# everywhere it was checked (F1-P1, PLAN-169/fleet-currency-audit-S298).
#
# Authority: `VETO_HARDCODE` in `.claude/scripts/tier_policy_cli/_constants.py`,
# cross-checked against the INDEPENDENT frozen hex literal
# `FROZEN_SHA256_HEX_LITERAL` in `tier_policy_cli/apply.py`. That hex is the
# real anchor — `_constants.VETO_HARDCODE_FROZEN_SHA256` is RECOMPUTED from
# the very dict it is supposed to pin, so `assert_veto_hardcode_integrity`
# passes tautologically and cannot detect tampering on its own.
# `apply.py` is read as TEXT rather than imported because it pulls
# `_lib.runtime_paths`, which does not exist in the test sandbox.
#
# Fail-CLOSED by design (CLAUDE.md §4: an input-parse failure on a security
# surface is not waved through): unreadable authority means NO profile is
# written. Falling back to a literal is what created this class.
_veto_floor_model() {
  local role="$1" out
  out="$(SCRIPTS_DIR="${REPO_ROOT}/.claude/scripts" python3 - "$role" <<'PY'
import os, re, sys
from pathlib import Path
scripts = Path(os.environ["SCRIPTS_DIR"])
sys.path.insert(0, str(scripts))
try:
    from tier_policy_cli._constants import (
        VETO_HARDCODE, _compute_canonical_sha256)
    apply_src = (scripts / "tier_policy_cli" / "apply.py").read_text(
        encoding="utf-8")
except Exception as exc:
    sys.stderr.write("VETO authority not importable: {0}: {1}\n".format(
        type(exc).__name__, exc))
    sys.exit(4)

# The hex sits several COMMENT lines below the assignment, and those
# comments contain double quotes — a `[^"']*` gap stops at the first one
# and never reaches the anchor. Scan a bounded window instead, and require
# the window to hold EXACTLY one 64-hex literal so a second anchor added
# later cannot be silently picked.
at = apply_src.find("FROZEN_SHA256_HEX_LITERAL")
window = apply_src[at:at + 800] if at >= 0 else ""
hexes = re.findall(r"[\"']([0-9a-f]{64})[\"']", window)
if len(hexes) != 1:
    sys.stderr.write(
        "frozen SHA256 anchor not resolvable in apply.py "
        "(found {0} candidates)\n".format(len(hexes)))
    sys.exit(4)
actual = _compute_canonical_sha256(VETO_HARDCODE)
if actual != hexes[0]:
    sys.stderr.write(
        "VETO_HARDCODE byte-identity violation: expected sha256={0} "
        "got sha256={1}\n".format(hexes[0], actual))
    sys.exit(5)
model = VETO_HARDCODE.get(sys.argv[1], "")
if not model:
    sys.stderr.write("role {0!r} absent from VETO_HARDCODE\n".format(
        sys.argv[1]))
    sys.exit(6)
sys.stdout.write(model)
PY
)" || {
    echo "ERROR: VETO-floor authority unreadable or tampered for role '$role'" >&2
    echo "       (tier_policy_cli._constants.VETO_HARDCODE, anchored by" >&2
    echo "        apply.py FROZEN_SHA256_HEX_LITERAL). Refusing to write a" >&2
    echo "        quality profile — fail-CLOSED, PLAN-169 W4.3 F1." >&2
    return 3
  }
  if [[ -z "$out" ]]; then
    echo "ERROR: empty VETO-floor model for role '$role' — fail-CLOSED." >&2
    return 3
  fi
  printf '%s' "$out"
}

# Profile → per-agent model map
# Format: "<slug>:<model-id>" space-separated
#
# The profile NAME is validated BEFORE the authority is resolved: callers
# depend on rc=2 + "unknown profile" for a bad name, and resolving first
# would turn a typo into the fail-CLOSED rc=3.
#
# NOTE: `local x="$(cmd)"` is forbidden below — `local` always returns 0, so
# it swallows the command's exit status and the fail-CLOSED path would
# become a silent fail-OPEN.
_profile_models() {
  local profile="$1"
  local cr se
  case "$profile" in
    max-quality|balanced|max-speed) : ;;
    *)
      echo "ERROR: unknown profile '$profile'" >&2
      return 2
      ;;
  esac
  cr="$(_veto_floor_model code-reviewer)" || return 3
  se="$(_veto_floor_model security-engineer)" || return 3
  # The 3 ADVISORY slots stay literal on purpose: their generation target is
  # an Owner DECISION still open (PLAN-169/fleet-currency-audit-S298.md:62 —
  # "does max-quality become fable-5 or opus-5?"). This cure closes only the
  # VETO-floor downgrade, which depends on no decision at all.
  case "$profile" in
    max-quality)
      echo "code-reviewer:${cr} security-engineer:${se} qa-architect:claude-opus-4-8 performance-engineer:claude-opus-4-8 devops:claude-opus-4-8"
      ;;
    balanced)
      echo "code-reviewer:${cr} security-engineer:${se} qa-architect:claude-sonnet-4-6 performance-engineer:claude-sonnet-4-6 devops:claude-sonnet-4-6"
      ;;
    max-speed)
      echo "code-reviewer:${cr} security-engineer:${se} qa-architect:claude-haiku-4-5-20251001 performance-engineer:claude-haiku-4-5-20251001 devops:claude-haiku-4-5-20251001"
      ;;
  esac
}

# PLAN-133 B2 — canonicalize a model id by alias/whitespace/case ONLY.
# Default-OFF behavioral change (env flag `CEO_MODEL_NORMALIZE`): when set to a
# truthy value (1/true/on/yes), a profile's model id is routed through the
# optimizer's `normalize_model_name` before being written to frontmatter, so an
# aliased/date-stamped/cased id folds onto its canonical slug. The major.minor
# version token is PRESERVED (opus-4-1 never collapses to opus-4-8). Fail-open:
# any normalizer error (missing module, bad python) returns the input unchanged
# so the profile write is never blocked on infra.
_normalize_enabled() {
  case "$(printf '%s' "${CEO_MODEL_NORMALIZE:-0}" | tr '[:upper:]' '[:lower:]')" in
    1|true|on|yes) return 0 ;;
    *) return 1 ;;
  esac
}

_normalize_model_id() {
  local raw="$1"
  if ! _normalize_enabled; then
    printf '%s' "$raw"
    return 0
  fi
  # stdlib-only; the optimizer package is on .claude/scripts. Fail-open to raw.
  local out
  out="$(SCRIPTS_DIR="${REPO_ROOT}/.claude/scripts" python3 - "$raw" <<'PY' 2>/dev/null
import os, sys
sys.path.insert(0, os.environ["SCRIPTS_DIR"])
raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    from optimizer.model_normalize import normalize_model_name
    out = normalize_model_name(raw)
    # An empty result means "unknown/blank" — never emit empty into frontmatter.
    sys.stdout.write(out or raw)
except Exception:
    sys.stdout.write(raw)
PY
)"
  if [[ -z "$out" ]]; then
    printf '%s' "$raw"
  else
    printf '%s' "$out"
  fi
}

# Rewrite the `model:` frontmatter field of an agent file.
_set_agent_model() {
  local agent_file="$1"
  local new_model
  new_model="$(_normalize_model_id "$2")"
  if [[ ! -f "$agent_file" ]]; then
    echo "WARN: $agent_file does not exist; skipping" >&2
    return 0
  fi
  # Use awk to rewrite only the first `model:` line in the frontmatter
  # (between the first two `---` lines). Preserves everything else.
  awk -v new_model="$new_model" '
    BEGIN { in_fm = 0; fm_seen = 0; patched = 0 }
    /^---$/ {
      if (fm_seen == 0) { in_fm = 1; fm_seen = 1; print; next }
      else if (in_fm == 1) { in_fm = 0; print; next }
    }
    in_fm == 1 && /^model:[[:space:]]*/ {
      if (patched == 0) {
        print "model: " new_model
        patched = 1
        next
      }
    }
    { print }
  ' "$agent_file" > "$agent_file.tmp"
  mv "$agent_file.tmp" "$agent_file"
  echo "  - $(basename "$agent_file") -> $new_model"
}

# Update the `ceo_quality_profile` key in .claude/settings.json.
# Uses stdlib-only Python (no jq dep per ADR-002 stdlib-only invariant).
_set_settings_profile() {
  local profile="$1"
  python3 - "$SETTINGS_JSON" "$profile" <<'PY'
import json, sys
path = sys.argv[1]
profile = sys.argv[2]
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}
data["ceo_quality_profile"] = profile
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"  settings.json .ceo_quality_profile = {profile}")
PY
}

_show_profile() {
  if [[ ! -f "$SETTINGS_JSON" ]]; then
    echo "balanced (default — settings.json not found)"
    return 0
  fi
  python3 - "$SETTINGS_JSON" <<'PY'
import json, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    print(data.get("ceo_quality_profile", "balanced (default)"))
except Exception as e:
    print(f"balanced (default — error reading settings.json: {e})")
PY
}

_regenerate_dispatch() {
  local gen_script="${REPO_ROOT}/.claude/scripts/generate-dispatch.py"
  if [[ -x "$gen_script" ]] || [[ -f "$gen_script" ]]; then
    python3 "$gen_script" --write 2>&1 | tail -5 || \
      echo "WARN: generate-dispatch.py returned non-zero; _dispatch.md may be stale" >&2
  else
    echo "WARN: generate-dispatch.py not found at $gen_script" >&2
  fi
}

main() {
  if [[ $# -eq 0 ]] || [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    _usage
    exit 0
  fi

  if [[ "${1:-}" == "--show" ]]; then
    echo -n "Current profile: "
    _show_profile
    exit 0
  fi

  local profile="$1"
  local models rc=0
  models=$(_profile_models "$profile") || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    # rc=2 → bad profile name (usage helps). rc=3 → VETO authority
    # unreadable (fail-CLOSED; usage would bury the real cause).
    [[ "$rc" -eq 2 ]] && _usage
    exit "$rc"
  fi

  echo "Setting quality profile: $profile"
  echo ""
  echo "Rewriting .claude/agents/*.md model: frontmatter fields..."

  for pair in $models; do
    local slug="${pair%%:*}"
    local model="${pair##*:}"
    _set_agent_model "${AGENTS_DIR}/${slug}.md" "$model"
  done

  echo ""
  echo "Updating .claude/settings.json..."
  _set_settings_profile "$profile"

  echo ""
  echo "Regenerating _dispatch.md..."
  _regenerate_dispatch

  echo ""
  echo "Done. Profile set to: $profile"
  echo ""
  echo "Verify:"
  echo "  bash .claude/scripts/set-quality-profile.sh --show"
  echo "  python3 .claude/scripts/ceo-health.py | grep quality_profile"
}

main "$@"
