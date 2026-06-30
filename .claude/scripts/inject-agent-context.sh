#!/bin/bash
# Usage: bash .claude/scripts/inject-agent-context.sh \
#          [--skill-retrieve] [--mode=inline|reference] [--dispatch=native|mitigated] \
#          "AgentName" "task description"
# Outputs: Full agent context ready for Agent tool prompt
#
# Resolves the agent's primary skill through all tiers:
#   .claude/skills/core/<skill>/SKILL.md
#   .claude/skills/frontend/<skill>/SKILL.md
#   .claude/skills/domains/<domain>/skills/<skill>/SKILL.md
#
# Security: AGENT_NAME is user-controlled (reaches here via the /spawn
# slash command). We validate it against a strict whitelist and use
# grep -F (fixed-string) for all matches to prevent regex injection.
#
# PLAN-011 Phase 2: opt-in --skill-retrieve flag.
#   When passed, the script calls .claude/scripts/skill-retrieve.py and
#   emits a "## RETRIEVED SKILLS" section listing the top-3 lexical tf-idf
#   matches for the task description (in addition to the archetype's
#   primary skill). Default behavior is unchanged.
#
# PLAN-060 Layer 7c (ADR-080): --dispatch=mitigated flag.
#   Emits a header instructing the caller to dispatch via
#   subagent_type=general-purpose to bypass the H4 rail anomaly
#   (custom subagent_types qa/pe/se/devops receive only Grep+Glob
#   from the Claude Code runtime despite frontmatter declaring full
#   tools). general-purpose has full tool universe; persona injected
#   via ## SKILL CONTENT in the prompt body. Empirically 13/13 success.
#   Env-var fallback: CEO_DISPATCHER_MODE=native|mitigated.
#   Kill-switch: CEO_MITIGATION_DISABLE=1 forces native universally.
#
# PLAN-061 (ADR-082): default flips to per-archetype.
#   - Default `native` for `code-reviewer` archetype (full tool grant
#     works empirically; preserves ADR-052 VETO floor).
#   - Default `mitigated` for non-`code-reviewer` archetypes
#     (qa-architect, performance-engineer, security-engineer, devops).
#   Resolution precedence (highest first):
#     kill-switch > --dispatch flag > CEO_DISPATCHER_MODE env > archetype default

set -euo pipefail

USE_SKILL_RETRIEVE=0
# PLAN-059 / ADR-090 #1 (Session 67): Format B SKILL REFERENCE is now
# the default for canonical-5 archetypes. Default flips per archetype
# during the SKILL MAP lookup below; CEO_SKILL_REFERENCE_MODE=0 reverts
# universally to inline. Adopters can also pass --mode=inline per-call.
SKILL_INJECTION_MODE="reference"  # PLAN-059 ADR-090 #1: default flipped from "inline"
# DISPATCH_MODE is resolved per-archetype below (see PLAN-061 / ADR-082).
# Empty until resolution; the literal default flag-from-flag is tracked
# separately to enforce precedence.
DISPATCH_MODE=""
DISPATCH_MODE_FROM_FLAG=""

# PLAN-081 Phase 2 — Pair-Rail dispatcher mode.
#   --pair-mode             Activate Pair-Rail routing via .claude/dispatcher/
#                           routing-matrix.yaml. Looks up archetype's coder+
#                           reviewer providers + sandbox + fallback policy.
#                           Emits `## PAIR-RAIL DISPATCH` header instructing
#                           caller to dispatch coder via primary rail and
#                           pair the reviewer provider via PostToolUse hook.
#   --coder=<provider>      Override the matrix-resolved coder provider.
#                           Honored only when --pair-mode is active.
#   --reviewer=<provider>   Override the matrix-resolved reviewer provider.
#                           Honored only when --pair-mode is active.
#
# Resolution precedence (highest first):
#   1. CEO_PAIR_RAIL_DISABLE=1   (kill-switch — forces single-LLM Claude)
#   2. --pair-mode flag absent   (legacy single-rail path; no dispatcher
#                                consultation; no dispatcher_route)
#   3. disable_predicate fired   (matrix's predicates evaluated;
#                                 fallback_provider engaged)
#   4. --coder= / --reviewer=    (Owner override; emitted as reason_code
#                                  override_<arg>)
#   5. matrix archetype entry    (default coder+reviewer per spec.md §10)
PAIR_MODE=0
PAIR_CODER_OVERRIDE=""
PAIR_REVIEWER_OVERRIDE=""

# Parse leading flags. Order-independent. Positional args validated below.
while [ "${1:-}" = "--skill-retrieve" ] \
   || [ "${1:-}" = "--mode=reference" ] \
   || [ "${1:-}" = "--mode=inline" ] \
   || [ "${1:-}" = "--dispatch=mitigated" ] \
   || [ "${1:-}" = "--dispatch=native" ] \
   || [ "${1:-}" = "--pair-mode" ] \
   || [[ "${1:-}" == --coder=* ]] \
   || [[ "${1:-}" == --reviewer=* ]]; do
  case "${1}" in
    --skill-retrieve)
      USE_SKILL_RETRIEVE=1
      shift
      ;;
    --mode=reference)
      # PLAN-020 Phase 2 (ADR-051): emit ## SKILL REFERENCE with hash-pin
      # instead of inline ## SKILL CONTENT. Smaller, cache-friendlier
      # spawn prompts; sub-agent Reads SKILL.md and re-hashes for forensic
      # observation via check_skill_reference_read.py.
      SKILL_INJECTION_MODE="reference"
      shift
      ;;
    --mode=inline)
      SKILL_INJECTION_MODE="inline"
      shift
      ;;
    --dispatch=mitigated)
      # PLAN-060 Layer 7c (ADR-080): emit header instructing caller to
      # dispatch via subagent_type=general-purpose to bypass H4 rail
      # anomaly (custom subagent_types qa/pe/se/devops receive only
      # Grep+Glob from runtime despite frontmatter declaring full tools).
      # Persona is injected via ## SKILL CONTENT; general-purpose has
      # full tool universe (Bash+Edit+Read+Write+...).
      DISPATCH_MODE_FROM_FLAG="mitigated"
      shift
      ;;
    --dispatch=native)
      DISPATCH_MODE_FROM_FLAG="native"
      shift
      ;;
    --pair-mode)
      PAIR_MODE=1
      shift
      ;;
    --coder=*)
      PAIR_CODER_OVERRIDE="${1#--coder=}"
      shift
      ;;
    --reviewer=*)
      PAIR_REVIEWER_OVERRIDE="${1#--reviewer=}"
      shift
      ;;
  esac
done

# Honor CEO_SOTA_DISABLE master kill — forces inline regardless of flag.
if [ "${CEO_SOTA_DISABLE:-}" = "1" ]; then
  SKILL_INJECTION_MODE="inline"
fi
# Honor CEO_SKILL_REFERENCE_MODE=0 explicit opt-out.
if [ "${CEO_SKILL_REFERENCE_MODE:-}" = "0" ]; then
  SKILL_INJECTION_MODE="inline"
fi

AGENT_NAME="${1:-}"
TASK_DESC="${2:-}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ -z "$AGENT_NAME" ]; then
  echo "Usage: inject-agent-context.sh <AgentName> [task description]" >&2
  echo "  <AgentName> must match: ^[A-Za-z][A-Za-z0-9 _-]{0,60}$" >&2
  exit 1
fi

# Whitelist validation: allow letters, digits, space, underscore, dash.
# First character must be a letter. Max 61 chars.
# This rejects shell metacharacters, regex metacharacters, newlines,
# null bytes, and path traversal attempts.
if ! printf '%s' "$AGENT_NAME" | grep -qE '^[A-Za-z][A-Za-z0-9 _-]{0,60}$'; then
  echo "ERROR: Invalid AgentName '$AGENT_NAME'" >&2
  echo "  Must start with a letter and contain only letters, digits, spaces, underscores, and dashes (max 61 chars)." >&2
  exit 2
fi

# Resolve a skill name to its full SKILL.md path across all tiers.
resolve_skill_path() {
  local skill="$1"
  local f
  # Check core
  f="$REPO_ROOT/.claude/skills/core/$skill/SKILL.md"
  if [ -f "$f" ]; then
    echo "$f"
    return 0
  fi
  # Check frontend
  f="$REPO_ROOT/.claude/skills/frontend/$skill/SKILL.md"
  if [ -f "$f" ]; then
    echo "$f"
    return 0
  fi
  # Check domains
  for domain_dir in "$REPO_ROOT/.claude/skills/domains/"*/; do
    f="${domain_dir}skills/$skill/SKILL.md"
    if [ -f "$f" ]; then
      echo "$f"
      return 0
    fi
  done
  return 1
}

# Build the TEAM_FILES list once, used both for archetype detection
# (PLAN-061 / ADR-082 default-on resolution below) and for emitting
# the AGENT PROFILE / SKILL MAP sections later.
TEAM_FILES=(
  "$REPO_ROOT/.claude/team.md"
  "$REPO_ROOT/.claude/frontend-team.md"
)
# Include domain persona files (fintech example + any others)
for f in "$REPO_ROOT"/.claude/skills/domains/*/team-personas.md \
         "$REPO_ROOT"/.claude/skills/domains/*/frontend-team-personas.md; do
  [ -f "$f" ] && TEAM_FILES+=("$f")
done

# PLAN-061 (ADR-082) — Resolve DISPATCH_MODE per archetype before
# emitting any output. Look up the archetype's primary skill from the
# SKILL MAP; if it's `code-review-checklist`, the archetype default is
# `native` (full tool grant works empirically + ADR-052 VETO floor).
# Otherwise default is `mitigated` (qa-architect, performance-engineer,
# security-engineer, devops all suffer the H4 rail anomaly).
DETECTED_SKILL=""
for team_file in "${TEAM_FILES[@]}"; do
  [ -f "$team_file" ] || continue
  # grep -F (fixed-string) on bold-wrapped name; AGENT_NAME has been
  # whitelist-validated above. Pipeline tolerated under set -e/pipefail
  # via `|| true` so no-match doesn't abort.
  DETECTED_SKILL=$(grep -iF "**$AGENT_NAME**" "$team_file" 2>/dev/null \
    | head -1 \
    | grep -oE '`[a-z][a-z0-9]*-[a-z0-9-]+`' \
    | head -1 \
    | tr -d '`' || true)
  if [ -n "$DETECTED_SKILL" ]; then
    break
  fi
done

if [ "$DETECTED_SKILL" = "code-review-checklist" ]; then
  ARCHETYPE_DEFAULT="native"
elif [ "$DETECTED_SKILL" = "incident-management" ] \
  || [ "$DETECTED_SKILL" = "identity-and-trust-architecture" ]; then
  # PLAN-074 Wave 1c: VETO-floor archetypes routed native per team.md
  # ROUTING TABLE. Skills are unique to one archetype each so the
  # skill-based check is sufficient.
  ARCHETYPE_DEFAULT="native"
elif printf '%s' "$AGENT_NAME" | grep -qE 'Threat Detection'; then
  # PLAN-074 Wave 1c: threat-detection-engineer shares the
  # security-and-auth skill with Security Engineer but routes native
  # per team.md ROUTING TABLE. Disambiguate by archetype name.
  ARCHETYPE_DEFAULT="native"
else
  # Catches every non-cr archetype + the unknown-archetype fallback.
  # Unknown archetype defaults to mitigated as the safer prod posture
  # (general-purpose has full tool universe; native subset risk avoided).
  ARCHETYPE_DEFAULT="mitigated"
fi

# PLAN-069 S80 lesson: when DISPATCH=mitigated, the sub-agent inherits
# parent model (CEO Opus → all sub-agents Opus). The custom-agent
# frontmatter routing (qa-architect:sonnet, devops:haiku, etc.) is
# DORMANT under mitigated rail. CEO must pass `model:` param explicit
# on the Agent() tool call. This block emits a recommended model based
# on detected skill so the CEO can copy/paste.
case "$DETECTED_SKILL" in
  # VETO floor (ADR-052) — Opus mandatory
  code-review-checklist|security-and-auth)
    MODEL_HINT="opus"
    MODEL_HINT_REASON="VETO floor (ADR-052) — Opus mandatory"
    ;;
  # Reasoning-heavy / debate / architectural decisions
  architecture-decisions|pre-plan-brainstorm|agent-architect|ai-llm-orchestration)
    MODEL_HINT="opus"
    MODEL_HINT_REASON="reasoning L3+ multi-step / debate Round N"
    ;;
  # Financial / legal / correctness-critical (VETO-eligible per domain)
  financial-correctness-and-math|monetization-and-billing|compliance-lgpd|consent-lifecycle|dpo-reporting|pii-data-flow|state-machines-and-invariants|data-schema-design)
    MODEL_HINT="opus"
    MODEL_HINT_REASON="VETO-eligible domain (financial / legal / correctness)"
    ;;
  # Mechanical / measurement / API design
  testing-strategy|performance-engineering|public-api-design|chaos-and-resilience|incremental-refactoring|observability-and-ops|product-conversion-readiness|growth-and-launch)
    MODEL_HINT="sonnet"
    MODEL_HINT_REASON="mechanical work / measurement / API enumeration; CEO Opus reviews report"
    ;;
  # CI/CD security-adjacent — Sonnet (NOT haiku)
  devops-ci-cd)
    MODEL_HINT="sonnet"
    MODEL_HINT_REASON="CI/CD is security-adjacent (SHA-pin, OIDC, secrets); haiku risky without tournament evidence"
    ;;
  # Listings / output economy
  terse-mode)
    MODEL_HINT="sonnet"
    MODEL_HINT_REASON="output economy / listings"
    ;;
  # Default for unknown / general-purpose mechanical
  *)
    MODEL_HINT="sonnet"
    MODEL_HINT_REASON="default for unknown archetype (mechanical fallback); upgrade to opus if reasoning-heavy"
    ;;
esac

# Resolve final DISPATCH_MODE — precedence (highest first):
#   1. CEO_MITIGATION_DISABLE=1  (universal kill-switch → native)
#   2. --dispatch=native|mitigated flag
#   3. CEO_DISPATCHER_MODE=native|mitigated env var
#   4. archetype default (per the table above)
if [ "${CEO_MITIGATION_DISABLE:-}" = "1" ]; then
  DISPATCH_MODE="native"
elif [ -n "$DISPATCH_MODE_FROM_FLAG" ]; then
  DISPATCH_MODE="$DISPATCH_MODE_FROM_FLAG"
elif [ "${CEO_DISPATCHER_MODE:-}" = "mitigated" ]; then
  DISPATCH_MODE="mitigated"
elif [ "${CEO_DISPATCHER_MODE:-}" = "native" ]; then
  DISPATCH_MODE="native"
else
  DISPATCH_MODE="$ARCHETYPE_DEFAULT"
fi

# 0a. PLAN-081 Phase 2 — Pair-Rail dispatcher resolution (--pair-mode).
#     When --pair-mode is set AND CEO_PAIR_RAIL_DISABLE != 1, this block:
#       1. Loads .claude/dispatcher/routing-matrix.yaml via
#          routing-matrix-loader.py.
#       2. Resolves the archetype's matrix entry to get coder + reviewer
#          + sandbox + fallback_provider.
#       3. Evaluates disable_predicates via disable_predicate_eval (bounded
#          tail-scan of audit-log).
#       4. Honors --coder= / --reviewer= overrides (post-matrix).
#       5. Emits dispatcher_route audit event with the decision.
#       6. Sets PAIR_RAIL_HEADER which is printed as "## PAIR-RAIL DISPATCH"
#          section instructing the caller to spawn coder via primary rail
#          and pair the reviewer (via mcp__codex__codex PostToolUse) per
#          ADR-106 advisory semantics.
#
#     Fail-OPEN invariant: any error loading the matrix or evaluating
#     predicates → log breadcrumb + skip pair-mode (no header emitted,
#     legacy single-rail path preserved). Pair-Rail NEVER blocks the
#     dispatch chain on its own bug.
PAIR_RAIL_HEADER=""
PAIR_RAIL_AUDIT_RAIL=""
PAIR_RAIL_AUDIT_REASON=""
PAIR_RAIL_AUDIT_CODER=""
PAIR_RAIL_AUDIT_REVIEWER=""
PAIR_RAIL_AUDIT_CODER_MODEL=""
PAIR_RAIL_AUDIT_SANDBOX=""
PAIR_RAIL_AUDIT_FALLBACK=""
PAIR_RAIL_AUDIT_SHA_PREFIX=""
PAIR_RAIL_AUDIT_SHA_MATCH="false"
PAIR_RAIL_WALL_CLOCK_MS="0"

if [ "$PAIR_MODE" = "1" ] && [ "${CEO_PAIR_RAIL_DISABLE:-}" != "1" ]; then
  # ARCHETYPE_KEY converts AGENT_NAME to a matrix lookup key. The matrix
  # uses lowercase-hyphenated archetype IDs (per spec.md §10). We map
  # known display names to the canonical IDs; unknown names cause the
  # block to skip pair-mode (legacy fallback).
  ARCHETYPE_KEY=""
  case "$AGENT_NAME" in
    *"Code Reviewer"*|*"code-reviewer"*) ARCHETYPE_KEY="code-reviewer" ;;
    *"Security Engineer"*|*"security-engineer"*) ARCHETYPE_KEY="security-engineer" ;;
    *"QA Architect"*|*"qa-architect"*) ARCHETYPE_KEY="qa-architect" ;;
    *"Performance Engineer"*|*"performance-engineer"*) ARCHETYPE_KEY="performance-engineer" ;;
    *"Refactoring"*|*"refactoring"*) ARCHETYPE_KEY="refactoring" ;;
    *"Docs Writer"*|*"docs-writer"*) ARCHETYPE_KEY="docs-writer" ;;
    *"Test Author"*|*"test-author"*) ARCHETYPE_KEY="test-author" ;;
    *"Threat Detection"*|*"threat-detection-engineer"*) ARCHETYPE_KEY="threat-detection-engineer" ;;
  esac
  if [ -n "$ARCHETYPE_KEY" ]; then
    # Resolve the routing decision via Python (loader + predicate-eval).
    # Output format (one tab-separated line):
    # Output format (10 fields separated by ASCII Unit Separator \x1f
    # per Codex iter 1 P1-5 — bash word-splitting on \t drops empty
    # trailing fields; \x1f + `read -ra` preserves all 10 even if some
    # are sentinel "-" placeholders):
    #   <rail>\x1f<reason_code>\x1f<coder>\x1f<reviewer>\x1f<coder_model>\x1f
    #   <reviewer_sandbox>\x1f<fallback_provider>\x1f<sha_prefix>\x1f
    #   <sha_match>\x1f<wall_clock_ms>
    # Per Codex iter 1 P0-1, wall_clock_ms is an integer (milliseconds),
    # NOT a float — canonical_json forbids floats in HMAC-covered fields.
    PAIR_DECISION=$(python3 - "$REPO_ROOT" "$ARCHETYPE_KEY" "$PAIR_CODER_OVERRIDE" "$PAIR_REVIEWER_OVERRIDE" <<'PYEOF' 2>/dev/null || true
import sys, time, importlib.util, os
from pathlib import Path

repo_root = Path(sys.argv[1])
archetype = sys.argv[2]
coder_override = sys.argv[3]
reviewer_override = sys.argv[4]

t0 = time.monotonic()

# Codex iter 2 P1-1: every early-exit row MUST use the same \x1f
# separator + integer wall_clock_ms (NOT \t and 0.000) so Bash
# parsing via `read -ra` IFS=$'\x1f' produces the full 10-field
# vector. \t-separated rows produce 1 field, fail the >=10 check,
# and skip audit + header emission. Centralized helper closes drift.
_SEP = "\x1f"


def _emit_fallback(reason_code, coder="claude"):
    """Emit a 10-field \\x1f-separated fallback decision row."""
    print(_SEP.join([
        "fallback_claude_only",
        reason_code,
        coder,
        "-",        # reviewer placeholder (caller coerces back to "")
        "",         # coder_model
        "read-only",
        "claude",   # fallback_provider
        "",         # sha_prefix
        "false",    # sha_match
        "0",        # wall_clock_ms (int per Codex iter 1 P0-1)
    ]))


loader_path = repo_root / ".claude" / "dispatcher" / "routing-matrix-loader.py"
if not loader_path.exists():
    _emit_fallback("matrix_missing")
    sys.exit(0)

spec = importlib.util.spec_from_file_location("rml", loader_path)
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except Exception as e:
    _emit_fallback(f"loader_error_{type(e).__name__}")
    sys.exit(0)

try:
    matrix = m.load_routing_matrix()
except Exception as e:
    _emit_fallback("matrix_load_error")
    sys.exit(0)

try:
    route = m.get_archetype_route(matrix, archetype)
except Exception:
    _emit_fallback("unknown_archetype")
    sys.exit(0)

# SHA-pin status (R1 T-4 mitigation #2 + Codex iter 1 P1-4 fix)
expected_pin = os.environ.get("CEO_PAIR_RAIL_MATRIX_SHA256", "").strip()
sha_prefix = matrix.sha256[:16]
sha_match = bool(expected_pin) and expected_pin == matrix.sha256
sha_pin_set_but_mismatch = bool(expected_pin) and not sha_match

# Provider override validation (Codex iter 1 P1-6 + iter 2 P2-1).
# `_KNOWN_PROVIDERS` mirror of ADAPTER_REGISTRY in `_lib/contract.py`.
# Reject any --coder=<provider> / --reviewer=<provider> not in registry —
# arbitrary string would otherwise inject into the prompt header and
# downstream audit-log records.
#
# Codex iter 2 P2-1 + R-NEW-5: sanitize override values BEFORE
# embedding into reason_code. The internal decision protocol uses
# \x1f as field separator; any control char (including \x1f, \n, \t,
# \r, \0) in an override value would corrupt the row. Truncate +
# strip control chars deterministically.
_KNOWN_PROVIDERS = ("claude", "codex")


def _sanitize_override(value):
    """Strip control chars + truncate to 24 chars for safe embedding."""
    if not value:
        return ""
    safe = "".join(ch for ch in value if 32 <= ord(ch) < 127)
    return safe[:24]


coder_override_safe = _sanitize_override(coder_override)
reviewer_override_safe = _sanitize_override(reviewer_override)
override_invalid = ""
if coder_override and coder_override not in _KNOWN_PROVIDERS:
    override_invalid = f"invalid_coder_override_{coder_override_safe}"
if reviewer_override and reviewer_override not in _KNOWN_PROVIDERS:
    if not override_invalid:
        override_invalid = f"invalid_reviewer_override_{reviewer_override_safe}"

# Predicate evaluation
fired_predicate_id = None
try:
    enabled = m.is_pair_rail_enabled(matrix, archetype)
    if not enabled:
        # Find which predicate fired
        try:
            dpe_path = repo_root / ".claude" / "dispatcher" / "disable_predicate_eval.py"
            spec2 = importlib.util.spec_from_file_location("dpe", dpe_path)
            dpe = importlib.util.module_from_spec(spec2)
            spec2.loader.exec_module(dpe)
            for pred in route.disable_predicates:
                try:
                    if dpe.evaluate_predicate(pred):
                        fired_predicate_id = pred.id
                        break
                except Exception:
                    pass
        except Exception:
            pass
except Exception:
    enabled = True

# Decide rail (precedence: invalid override > sha_mismatch > predicate > override > matrix)
coder = route.coder
reviewer = route.reviewer
reason_code = "ok"
rail = "pair_rail"

if override_invalid:
    # Reject the dispatch routing entirely; fall back single-LLM Claude
    # (safest default). Audit emit captures the invalid override for
    # forensic review.
    coder = "claude"
    reviewer = "-"
    rail = "fallback_claude_only"
    reason_code = override_invalid
elif sha_pin_set_but_mismatch:
    # Codex iter 1 P1-4: SHA pin set + mismatch must surface as
    # `matrix_sha_mismatch` reason_code (NOT silently fall through to
    # `ok`). The threat-model v0.2 §2 T-4 detection prose explicitly
    # references this reason_code as a SOC alert signal.
    coder = "claude"
    reviewer = "-"
    rail = "fallback_claude_only"
    reason_code = "matrix_sha_mismatch"
elif not enabled:
    coder = route.fallback_provider
    reviewer = "-"
    rail = "fallback_claude_only" if route.fallback_provider == "claude" else "fallback_codex_only"
    reason_code = f"predicate_{fired_predicate_id}_fired" if fired_predicate_id else "predicate_fired"
else:
    # Apply overrides (post-matrix, only when override path is valid)
    if coder_override:
        coder = coder_override
        reason_code = f"override_coder_{coder_override}"
    if reviewer_override:
        reviewer = reviewer_override
        if reason_code == "ok":
            reason_code = f"override_reviewer_{reviewer_override}"

# Codex iter 1 P0-1: emit wall-clock as integer milliseconds (NOT
# float seconds) — canonical_json forbids floats in HMAC-covered fields
# (`_lib/canonical_json.py:85`). Aggregator divides by 1000 to recover
# seconds for percentile compare.
wall_clock_ms = int(round((time.monotonic() - t0) * 1000))

# Codex iter 1 P1-5: emit fields as a delimited record using a
# rare-byte separator (\x1f, ASCII Unit Separator) instead of \t —
# bash word-splitting via IFS=\t silently drops empty trailing fields,
# making fallback rows emit fewer than 10 parts and bypass audit emit.
# \x1f is unambiguous and bash IFS handles empty fields when fed via
# `read -ra` with explicit IFS=$'\x1f'.
SEP = "\x1f"
print(SEP.join([
    rail,
    reason_code,
    coder,
    reviewer,
    route.coder_model or "",
    route.reviewer_sandbox,
    route.fallback_provider,
    sha_prefix,
    "true" if sha_match else "false",
    str(wall_clock_ms),
]))
PYEOF
    )
    if [ -n "$PAIR_DECISION" ]; then
      # Codex iter 1 P1-5: parse \x1f-separated output via `read -ra`
      # with IFS=$'\x1f'. Bash word-splitting on \t silently drops empty
      # trailing fields; `read -ra` preserves all 10 fields including
      # any empties (the `-` placeholder reserves the slot for empty
      # reviewer on fallback rows).
      OLD_IFS="$IFS"
      IFS=$'\x1f' read -ra PAIR_PARTS <<< "$PAIR_DECISION"
      IFS="$OLD_IFS"
      if [ "${#PAIR_PARTS[@]}" -ge 10 ]; then
        PAIR_RAIL_AUDIT_RAIL="${PAIR_PARTS[0]}"
        PAIR_RAIL_AUDIT_REASON="${PAIR_PARTS[1]}"
        PAIR_RAIL_AUDIT_CODER="${PAIR_PARTS[2]}"
        # Coerce sentinel "-" placeholder back to empty string for
        # downstream consumers (Reviewer header omits the section when
        # rail is fallback).
        if [ "${PAIR_PARTS[3]}" = "-" ]; then
          PAIR_RAIL_AUDIT_REVIEWER=""
        else
          PAIR_RAIL_AUDIT_REVIEWER="${PAIR_PARTS[3]}"
        fi
        PAIR_RAIL_AUDIT_CODER_MODEL="${PAIR_PARTS[4]}"
        PAIR_RAIL_AUDIT_SANDBOX="${PAIR_PARTS[5]}"
        PAIR_RAIL_AUDIT_FALLBACK="${PAIR_PARTS[6]}"
        PAIR_RAIL_AUDIT_SHA_PREFIX="${PAIR_PARTS[7]}"
        PAIR_RAIL_AUDIT_SHA_MATCH="${PAIR_PARTS[8]}"
        # Codex iter 1 P0-1: wall-clock now integer milliseconds.
        PAIR_RAIL_WALL_CLOCK_MS="${PAIR_PARTS[9]}"

        # Audit-emit dispatcher_route (best-effort; never blocks dispatch).
        python3 - "$REPO_ROOT" \
          "$ARCHETYPE_KEY" \
          "$PAIR_RAIL_AUDIT_RAIL" \
          "$PAIR_RAIL_AUDIT_REASON" \
          "$PAIR_RAIL_AUDIT_SHA_PREFIX" \
          "$PAIR_RAIL_AUDIT_SHA_MATCH" \
          "$PAIR_RAIL_AUDIT_CODER" \
          "$PAIR_RAIL_AUDIT_REVIEWER" \
          "$PAIR_RAIL_AUDIT_CODER_MODEL" \
          "$PAIR_RAIL_AUDIT_SANDBOX" \
          "$PAIR_RAIL_AUDIT_FALLBACK" \
          "$PAIR_RAIL_WALL_CLOCK_MS" <<'PYEOF' 2>/dev/null || true
import sys
from pathlib import Path
repo_root = Path(sys.argv[1])
hooks_dir = repo_root / ".claude" / "hooks"
sys.path.insert(0, str(hooks_dir))
try:
    from _lib import audit_emit as ae
except Exception:
    sys.exit(0)
if not hasattr(ae, "emit_dispatcher_route"):
    sys.exit(0)
try:
    # Codex iter 1 P0-1: pass wall_clock_ms as int (canonical_json
    # no-float invariant). Reviewer placeholder "-" coerced back to
    # empty string.
    reviewer_arg = sys.argv[8]
    if reviewer_arg == "-":
        reviewer_arg = ""
    try:
        wall_ms = int(sys.argv[12])
    except (TypeError, ValueError):
        wall_ms = 0
    ae.emit_dispatcher_route(
        archetype=sys.argv[2],
        rail=sys.argv[3],
        reason_code=sys.argv[4],
        matrix_sha256_prefix=sys.argv[5],
        matrix_sha256_match=(sys.argv[6] == "true"),
        coder=sys.argv[7],
        reviewer=reviewer_arg,
        coder_model=sys.argv[9] if sys.argv[9] else None,
        reviewer_sandbox=sys.argv[10],
        fallback_provider=sys.argv[11],
        wall_clock_ms=wall_ms,
    )
except Exception:
    pass
PYEOF

        # Build the PAIR-RAIL DISPATCH header output. Only emitted when
        # the rail is `pair_rail` (active engagement); fallback paths
        # don't emit a special header — caller dispatches single-LLM as
        # normal.
        if [ "$PAIR_RAIL_AUDIT_RAIL" = "pair_rail" ]; then
          PAIR_RAIL_HEADER=$(cat <<PAIR_HEADER
## PAIR-RAIL DISPATCH — PLAN-081 Phase 2 (ADR-106 + ADR-107 + ADR-108)

This dispatch is routed via the Pair-Rail capability matrix
(\`.claude/dispatcher/routing-matrix.yaml\`) for archetype
\`$ARCHETYPE_KEY\`.

  Coder    (primary author):    **$PAIR_RAIL_AUDIT_CODER**${PAIR_RAIL_AUDIT_CODER_MODEL:+ (model: \`$PAIR_RAIL_AUDIT_CODER_MODEL\`)}
  Reviewer (cross-LLM check):   **$PAIR_RAIL_AUDIT_REVIEWER** (sandbox: \`$PAIR_RAIL_AUDIT_SANDBOX\`)
  Fallback provider:             $PAIR_RAIL_AUDIT_FALLBACK
  Matrix SHA prefix:             \`$PAIR_RAIL_AUDIT_SHA_PREFIX\` (pin match: $PAIR_RAIL_AUDIT_SHA_MATCH)

The reviewer engages via the PostToolUse hook
\`check_codex_response.py\` per ADR-106 (advisory-only at L2; Phase 3
PreToolUse extension on \`check_pair_rail.py\` for asymmetric VETO
matrix Cases A-F is the hard-enforcement surface).

Per spec.md §11 asymmetric VETO matrix:
  - Case A (both PASS) → dispatch proceeds.
  - Case B (Claude PASS / Codex BLOCK with file:line + rubric_violation_id)
    → auto Round 2; Owner cannot dismiss without ADR rebut.
  - Case C (Claude BLOCK / Codex PASS) → Claude VETO floor preserved
    per ADR-052.
  - Case D (both BLOCK) → hard-block; escalate.
  - Case E (divergent ≤ Jaccard 0.3) → flag for human review.
  - Case F (timeout / outage) → fail-open per ADR-106; predicate
    \`codex_outage_5min\` may have already triggered fallback.

Kill-switch: export CEO_PAIR_RAIL_DISABLE=1 to revert to single-LLM
Claude (legacy path) for incident response.

---

PAIR_HEADER
)
        elif [ "$PAIR_RAIL_AUDIT_RAIL" = "fallback_claude_only" ] || [ "$PAIR_RAIL_AUDIT_RAIL" = "fallback_codex_only" ]; then
          PAIR_RAIL_HEADER=$(cat <<PAIR_FALLBACK_HEADER
## PAIR-RAIL FALLBACK — PLAN-081 Phase 2

Pair-Rail is **disabled** for archetype \`$ARCHETYPE_KEY\` per
\`.claude/dispatcher/routing-matrix.yaml\` disable-predicate evaluation:

  Reason:                       \`$PAIR_RAIL_AUDIT_REASON\`
  Active rail:                  $PAIR_RAIL_AUDIT_RAIL
  Coder (single-LLM):           **$PAIR_RAIL_AUDIT_CODER**${PAIR_RAIL_AUDIT_CODER_MODEL:+ (model: \`$PAIR_RAIL_AUDIT_CODER_MODEL\`)}
  Cross-LLM review:             SKIPPED (will resume when predicate clears)

Forensic: \`audit-query.py dispatcher-routes-summary --window 24h\`
will reflect \`reason_code: $PAIR_RAIL_AUDIT_REASON\` for this dispatch.

---

PAIR_FALLBACK_HEADER
)
        fi
      fi
    fi
  fi
fi

if [ -n "$PAIR_RAIL_HEADER" ]; then
  printf '%s\n' "$PAIR_RAIL_HEADER"
fi

# 0. PLAN-060 Layer 7c (ADR-080) — Mitigation dispatch header.
#    When DISPATCH_MODE=mitigated, emit a header instructing the caller
#    to dispatch via subagent_type=general-purpose with this entire
#    block as the prompt body. Native subagent_types qa-architect,
#    performance-engineer, security-engineer, devops suffer a runtime
#    tool-grant divergence (receive Grep+Glob only despite frontmatter
#    declaring Read,Grep,Glob,Bash). general-purpose receives the full
#    tool universe (Bash,Edit,Read,Write,Glob,Grep,ScheduleWakeup,
#    Skill,ToolSearch). Confirmed empirically 13/13 dispatches in
#    PLAN-060 Layer 7c (.claude/plans/PLAN-060/audit/round-2/h4-layer7c-
#    mitigation-via-general-purpose.md).
if [ "$DISPATCH_MODE" = "mitigated" ]; then
  cat <<'MITIGATION_HEADER'
## DISPATCH MITIGATION — PLAN-060 Layer 7c (ADR-080)

This prompt is constructed for dispatch via the BUILT-IN subagent_type
"general-purpose" to bypass the H4 rail anomaly (custom subagent_types
receive only Grep+Glob from the Claude Code runtime despite frontmatter
declaring full tools). The persona below is injected via ## SKILL CONTENT;
general-purpose has the full tool universe and executes Bash/Read/Edit
correctly.

CALLER MUST DISPATCH AS:
  Task(subagent_type="general-purpose", prompt=<this entire block>)

NOT AS:
  Task(subagent_type="<original-archetype>", prompt=<this entire block>)

Kill-switch: export CEO_MITIGATION_DISABLE=1 to revert to native dispatch
(fails with tool-grant subset for non-cr archetypes).

---

MITIGATION_HEADER

  # PLAN-069 S80 lesson: under mitigated rail, sub-agent inherits parent
  # model unless `model:` param is passed explicit. Emit recommendation.
  cat <<MODEL_HINT_HEADER
## DISPATCH MODEL — recommendation per archetype (S80 lesson)

CALLER MUST PASS \`model:\` param on the Agent tool call:

  Task(
    subagent_type="general-purpose",
    model="${MODEL_HINT}",
    prompt=<this entire block>
  )

Recommendation: **${MODEL_HINT}** for skill \`${DETECTED_SKILL:-unknown}\`
Reason: ${MODEL_HINT_REASON}

If omitted: sub-agent INHERITS parent CEO model (Opus 4.8 by default).
Custom-agent frontmatter (\`.claude/agents/<archetype>.md\`) routing is
DORMANT under mitigated rail (PLAN-061 / ADR-082 trade-off).

VETO holders (CR + Sec) MUST be Opus per ADR-052 — never downgrade.
Override per-call: pass \`model: "opus"\` explicit if Owner judges
adversarial reasoning required.

---

MODEL_HINT_HEADER
fi

# 1. Extract agent profile from team.md (and fintech personas if present).
#    TEAM_FILES was built earlier (before DISPATCH_MODE resolution).
echo "## AGENT PROFILE"
echo ""

FOUND_PROFILE=0
for team_file in "${TEAM_FILES[@]}"; do
  [ -f "$team_file" ] || continue
  # Find a persona section matching AgentName. Uses awk's `index()`
  # (substring search, NOT regex) to eliminate regex metachar surface.
  # The AGENT_NAME has already been whitelist-validated above.
  section=$(awk -v name="$AGENT_NAME" '
    BEGIN { found=0 }
    function matches(line,    l, n) {
      l = tolower(line); n = tolower(name); return index(l, n) > 0
    }
    /^### [0-9]+\./ && matches($0) { found=1 }
    /^### [A-Za-zÀ-Ý]/ && matches($0) && !/^### [0-9]/ { found=1 }
    found && /^---$/ { found=0; print; next }
    found { print }
  ' "$team_file")
  if [ -n "$section" ]; then
    echo "$section"
    FOUND_PROFILE=1
    break
  fi
done

if [ "$FOUND_PROFILE" -eq 0 ]; then
  echo "WARNING: No persona section found for '$AGENT_NAME' in any team file."
  echo "Looked in: ${TEAM_FILES[*]}"
fi
echo ""

# 2. Find the agent's primary skill from the SKILL MAP. The lookup was
#    already performed above for DISPATCH_MODE archetype detection; reuse
#    DETECTED_SKILL here to avoid re-grepping the team files.
SKILL_NAME="$DETECTED_SKILL"

if [ -z "$SKILL_NAME" ]; then
  echo "WARNING: Could not find a primary skill for $AGENT_NAME in the SKILL MAP."
  echo "Confirm the SKILL MAP in team.md lists this agent with a backtick-quoted skill name."
else
  # resolve_skill_path returns 1 when the skill is not found in any tier;
  # tolerate under set -e so the WARNING branch can still print.
  SKILL_FILE=$(resolve_skill_path "$SKILL_NAME" || true)

  if [ "$SKILL_INJECTION_MODE" = "reference" ] && [ -n "$SKILL_FILE" ]; then
    # PLAN-020 Phase 2 (ADR-051): emit ## SKILL REFERENCE with SHA-256 hash.
    # Sub-agent must Read the file post-spawn; check_skill_reference_read.py
    # observes the Read and emits forensic breadcrumb.
    SKILL_REL=${SKILL_FILE#"$REPO_ROOT/"}
    SKILL_HASH=$(python3 -c "
import hashlib, sys
print(hashlib.sha256(open('$SKILL_FILE', 'rb').read()).hexdigest())
" 2>/dev/null || echo "")
    if [ -z "$SKILL_HASH" ]; then
      # Fall back to inline if hash computation failed (defensive).
      echo "## SKILL CONTENT"
      echo "SKILL: $SKILL_NAME"
      echo ""
      cat "$SKILL_FILE"
    else
      echo "## SKILL REFERENCE"
      echo ""
      echo "@$SKILL_REL sha256=$SKILL_HASH"
      echo ""
      echo "(Sub-agent: Read this file via the Read tool to load the full"
      echo "$SKILL_NAME skill. The PostToolUse observer check_skill_reference_read.py"
      echo "will re-hash and emit a forensic breadcrumb. The skill content is"
      echo "the authoritative source — this prompt only references it.)"
      echo ""
      # Optional summary block (≥256 bytes for sub-agent context priming).
      # Extract the skill description from frontmatter or first H2 if present.
      SKILL_SUMMARY=$(awk '/^description:/ {sub(/^description: */, ""); print; exit}' "$SKILL_FILE" 2>/dev/null || true)
      if [ -n "$SKILL_SUMMARY" ]; then
        echo "Skill summary: $SKILL_SUMMARY"
      fi
    fi
  else
    echo "## SKILL CONTENT"
    echo "SKILL: $SKILL_NAME"
    echo ""
    if [ -n "$SKILL_FILE" ]; then
      cat "$SKILL_FILE"
    else
      echo "WARNING: SKILL.md not found for skill '$SKILL_NAME' in any tier."
      echo "Checked: core/, frontend/, domains/*/skills/"
    fi
  fi
fi
echo ""

# 3. Inject relevant pitfalls from the universal catalog AND any installed domain catalogs.
PITFALL_FILES=(
  "$REPO_ROOT/.claude/pitfalls-catalog.yaml"
)
for f in "$REPO_ROOT"/.claude/skills/domains/*/pitfalls.yaml; do
  [ -f "$f" ] && PITFALL_FILES+=("$f")
done

PITFALLS_OUTPUT=""
for pitfall_file in "${PITFALL_FILES[@]}"; do
  [ -f "$pitfall_file" ] || continue
  block=$(awk -v name="$AGENT_NAME" '
    /^  - id:/ { block="" }
    { block = block "\n" $0 }
    /agents:/ && $0 ~ name { print block; block="" }
  ' "$pitfall_file")
  if [ -n "$block" ]; then
    PITFALLS_OUTPUT="$PITFALLS_OUTPUT\n[from $(basename "$pitfall_file")]$block"
  fi
done

if [ -n "$PITFALLS_OUTPUT" ]; then
  echo "## RELEVANT PITFALLS"
  echo ""
  echo -e "$PITFALLS_OUTPUT"
  echo ""
fi

# 4. Inject top-K past lessons (Reflexion — Sprint 3 Item A; PLAN-008 Phase 3)
#    Silent on failure: if lessons.py is missing or no lessons exist,
#    the injection is skipped without error. PLAN-008 Phase 3 additions:
#    - Task description words ≥4 chars extend the keyword seed
#    - When CEO_LESSON_CONSUMER is set, emit a lesson_read audit event
LESSONS_SCRIPT="$REPO_ROOT/.claude/scripts/lessons.py"
if [ -f "$LESSONS_SCRIPT" ] && [ -n "$SKILL_NAME" ]; then
  # Consumer tag: Architect flow sets CEO_ARCHITECT_ACTIVE; map it to
  # 'architect'. Generic spawn flow defaults to 'spawn'. Callers can
  # override by exporting CEO_LESSON_CONSUMER.
  CONSUMER="${CEO_LESSON_CONSUMER:-}"
  if [ -z "$CONSUMER" ]; then
    if [ "${CEO_ARCHITECT_ACTIVE:-0}" = "1" ]; then
      CONSUMER="architect"
    else
      CONSUMER="spawn"
    fi
  fi
  # PLAN-009 P5.2 — ranking mode opt-in. Default stays `recency` (zero
  # behavior diff). Sprint 10 decides whether to flip default to
  # `effectiveness` after measured data justifies it. Consumers may
  # override via env var `CEO_LESSON_RANKING_MODE`.
  RANKING_MODE="${CEO_LESSON_RANKING_MODE:-recency}"
  LESSONS_OUTPUT=$(python3 "$LESSONS_SCRIPT" top3 \
    --archetype "$AGENT_NAME" \
    --keywords "$SKILL_NAME" \
    --task-desc "$TASK_DESC" \
    --ranking-mode "$RANKING_MODE" \
    --emit-consumer "$CONSUMER" 2>/dev/null || true)
  if [ -n "$LESSONS_OUTPUT" ] && [ "$LESSONS_OUTPUT" != "No relevant lessons found." ]; then
    echo "$LESSONS_OUTPUT"
    echo ""
  fi
fi

# 5. Optional: retrieved skills via lexical tf-idf (PLAN-011 Phase 2).
#    Opt-in via --skill-retrieve; default behavior unchanged. Honors
#    CEO_SOTA_DISABLE=1 through skill-retrieve.py itself. Silent on
#    failure — if the index is missing or the script errors, we do
#    not block the spawn.
if [ "$USE_SKILL_RETRIEVE" -eq 1 ] && [ -n "$TASK_DESC" ]; then
  RETRIEVE_SCRIPT="$REPO_ROOT/.claude/scripts/skill-retrieve.py"
  if [ -f "$RETRIEVE_SCRIPT" ]; then
    RETRIEVED=$(python3 "$RETRIEVE_SCRIPT" \
      --task "$TASK_DESC" \
      --top-k 3 \
      --archetype "$AGENT_NAME" \
      --repo-root "$REPO_ROOT" 2>/dev/null || true)
    if [ -n "$RETRIEVED" ]; then
      echo "## RETRIEVED SKILLS (lexical tf-idf top-3)"
      echo ""
      echo "$RETRIEVED"
      echo ""
    fi
  fi
fi

# 6. Task description
echo "## TASK"
if [ -n "$TASK_DESC" ]; then
  echo "$TASK_DESC"
else
  echo "[CEO: define task here]"
fi
