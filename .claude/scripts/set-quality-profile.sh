#!/usr/bin/env bash
# PLAN-025 Batch L — set-quality-profile.sh
#
# Sets the ceo-orchestration quality profile — rewrites the canonical-5
# native subagent .md files' `model:` frontmatter field per profile:
#
#   max-quality  → all 5 on Opus 4.8         (baseline velocity, 100% cost)
#   balanced     → 2 Opus + 2 Sonnet + 1 Haiku  (DEFAULT; ~3.5x velocity, ~56% cost)
#   max-speed    → 2 Opus + 3 Haiku          (~5-6x velocity, ~22% cost)
#
# INVARIANT: code-reviewer + security-engineer ALWAYS stay Opus 4.8 (VETO floor).
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
  max-quality   All canonical-5 on Opus 4.8 (100% cost, baseline velocity)
  balanced      2 Opus + 2 Sonnet + 1 Haiku (~56% cost, 3.5x velocity; DEFAULT)
  max-speed     2 Opus + 3 Haiku (~22% cost, 5-6x velocity)

Invariant: code-reviewer + security-engineer ALWAYS on Opus 4.8 (VETO floor).

See docs/QUALITY-PROFILES.md for full details.
EOF
}

# Profile → per-agent model map
# Format: "<slug>:<model-id>" space-separated
_profile_models() {
  local profile="$1"
  case "$profile" in
    max-quality)
      echo "code-reviewer:claude-opus-4-8 security-engineer:claude-opus-4-8 qa-architect:claude-opus-4-8 performance-engineer:claude-opus-4-8 devops:claude-opus-4-8"
      ;;
    balanced)
      echo "code-reviewer:claude-opus-4-8 security-engineer:claude-opus-4-8 qa-architect:claude-sonnet-4-6 performance-engineer:claude-sonnet-4-6 devops:claude-sonnet-4-6"
      ;;
    max-speed)
      echo "code-reviewer:claude-opus-4-8 security-engineer:claude-opus-4-8 qa-architect:claude-haiku-4-5-20251001 performance-engineer:claude-haiku-4-5-20251001 devops:claude-haiku-4-5-20251001"
      ;;
    *)
      echo "ERROR: unknown profile '$profile'" >&2
      return 2
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
  local models
  if ! models=$(_profile_models "$profile"); then
    _usage
    exit 2
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
