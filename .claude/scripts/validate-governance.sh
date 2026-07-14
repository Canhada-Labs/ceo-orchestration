#!/bin/bash
set -euo pipefail
# Validates governance file integrity at session start.
# Usage: bash .claude/scripts/validate-governance.sh [--fast] [--json]
# Returns: 0 if all OK, 1 if issues found
#
# --fast --json: PLAN-082 Codex Item A fast profile for ceo-boot Tier-S.
#   Delegates to .claude/scripts/validate_governance_fast.py (Python stdlib,
#   <2s budget). Performs only cheap structural checks; full profile (no
#   --fast) keeps running in CI / pre-commit / explicit ceremonies.
#
# Updated for the tiered skills structure:
#   .claude/skills/core/<skill>/SKILL.md
#   .claude/skills/frontend/<skill>/SKILL.md
#   .claude/skills/domains/<domain>/skills/<skill>/SKILL.md

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# ---- PLAN-082 Codex Item A: --fast --json fast profile dispatch ----
# Triggered explicitly by ceo-boot.py Tier-S check. Bypass the full slow
# walk; exec Python helper that performs only cheap structural checks.
FAST_MODE=0
JSON_MODE=0
for arg in "${@:-}"; do
  case "$arg" in
    --fast) FAST_MODE=1 ;;
    --json) JSON_MODE=1 ;;
  esac
done
if [ "$FAST_MODE" = "1" ]; then
  FAST_ARGS=("--repo" "$REPO_ROOT")
  [ "$JSON_MODE" = "1" ] && FAST_ARGS+=("--json")
  exec python3 "$REPO_ROOT/.claude/scripts/validate_governance_fast.py" "${FAST_ARGS[@]}"
fi

ERRORS=0
WARNINGS=0

echo "=== Governance Validation ==="
echo "Repo: $REPO_ROOT"
echo ""

# ---- 1. Count all skills available across tiers ----

echo "--- Skill inventory ---"
CORE_COUNT=0
FRONTEND_COUNT=0
DOMAIN_COUNT=0

if [ -d "$REPO_ROOT/.claude/skills/core" ]; then
  CORE_COUNT=$(find "$REPO_ROOT/.claude/skills/core" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
fi
if [ -d "$REPO_ROOT/.claude/skills/frontend" ]; then
  FRONTEND_COUNT=$(find "$REPO_ROOT/.claude/skills/frontend" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
fi
if [ -d "$REPO_ROOT/.claude/skills/domains" ]; then
  for domain in "$REPO_ROOT/.claude/skills/domains"/*/; do
    if [ -d "${domain}skills" ]; then
      count=$(find "${domain}skills" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
      DOMAIN_COUNT=$((DOMAIN_COUNT + count))
    fi
  done
fi

TOTAL_SKILLS=$((CORE_COUNT + FRONTEND_COUNT + DOMAIN_COUNT))
echo "  Core:     $CORE_COUNT skills"
echo "  Frontend: $FRONTEND_COUNT skills"
echo "  Domain:   $DOMAIN_COUNT skills"
echo "  Total:    $TOTAL_SKILLS skills"
echo ""

# Helper: resolve a skill name to its full path, checking all tiers
resolve_skill() {
  local skill="$1"
  # Check core
  if [ -f "$REPO_ROOT/.claude/skills/core/$skill/SKILL.md" ]; then
    echo "core/$skill"
    return 0
  fi
  # Check frontend
  if [ -f "$REPO_ROOT/.claude/skills/frontend/$skill/SKILL.md" ]; then
    echo "frontend/$skill"
    return 0
  fi
  # Check all domain tiers
  for domain_dir in "$REPO_ROOT/.claude/skills/domains"/*/; do
    if [ -f "${domain_dir}skills/$skill/SKILL.md" ]; then
      local domain_name
      domain_name=$(basename "$domain_dir")
      echo "domains/$domain_name/skills/$skill"
      return 0
    fi
  done
  return 1
}

# ---- 2. Check all skills referenced in team.md / frontend-team.md exist ----

echo "--- Checking SKILL MAP references ---"
TEAM_FILES=""
[ -f "$REPO_ROOT/.claude/team.md" ] && TEAM_FILES="$TEAM_FILES $REPO_ROOT/.claude/team.md"
[ -f "$REPO_ROOT/.claude/frontend-team.md" ] && TEAM_FILES="$TEAM_FILES $REPO_ROOT/.claude/frontend-team.md"
# Include domain-specific team rosters. Domain skills are routed via
# their own domain's team-personas.md, not the central team.md.
for domain_team in "$REPO_ROOT/.claude/skills/domains"/*/team-personas.md \
                   "$REPO_ROOT/.claude/skills/domains"/*/frontend-team-personas.md; do
  [ -f "$domain_team" ] && TEAM_FILES="$TEAM_FILES $domain_team"
done

# Always-on meta-skills that do not need to appear in a routing table.
# These are self-activating skills that the CEO loads at session start
# regardless of task routing.
META_SKILLS="ceo-orchestration agent-architect"

is_meta_skill() {
  local name="$1"
  for meta in $META_SKILLS; do
    if [ "$name" = "$meta" ]; then
      return 0
    fi
  done
  return 1
}

# Load grandfathered skills from .claude/skill-governance-grandfather.yaml
# (PLAN-051 Phase 1 A1 — Opção 2). These skills exist on disk but are
# intentionally exempted from the routing-table requirement because they
# are invoked via non-routing mechanisms (slash commands, CEO pre-plan
# hooks, or adopter-opt-in community imports).
GRANDFATHER_FILE="$REPO_ROOT/.claude/skill-governance-grandfather.yaml"
GRANDFATHER_SCRIPT="$REPO_ROOT/.claude/scripts/skill_grandfather_parser.py"
GRANDFATHERED_SKILLS=""
GRANDFATHERED_REASONS=""
if [ -f "$GRANDFATHER_FILE" ] && [ -f "$GRANDFATHER_SCRIPT" ]; then
  GRANDFATHER_OUTPUT=$(python3 "$GRANDFATHER_SCRIPT" "$GRANDFATHER_FILE" 2>/dev/null || echo "")
  if [ -n "$GRANDFATHER_OUTPUT" ]; then
    # Parse `skill:reason` lines.
    while IFS=":" read -r skill reason; do
      if [ -n "$skill" ]; then
        GRANDFATHERED_SKILLS="$GRANDFATHERED_SKILLS $skill"
        GRANDFATHERED_REASONS="$GRANDFATHERED_REASONS $skill=$reason"
      fi
    done <<< "$GRANDFATHER_OUTPUT"
  fi
fi

is_grandfathered_skill() {
  local name="$1"
  local gf_entry
  for gf_entry in $GRANDFATHERED_SKILLS; do
    if [ "$name" = "$gf_entry" ]; then
      return 0
    fi
  done
  return 1
}

get_grandfather_reason() {
  local name="$1"
  local pair
  for pair in $GRANDFATHERED_REASONS; do
    local pair_skill="${pair%%=*}"
    local pair_reason="${pair##*=}"
    if [ "$pair_skill" = "$name" ]; then
      echo "$pair_reason"
      return 0
    fi
  done
  echo ""
}

# Whitelist of known skill names from core/, frontend/, and installed domains.
# The validator only checks these — it does NOT flag every backticked kebab-case
# token in team.md (that would false-positive on HTML attributes like aria-required,
# CSS classes like bg-bg-2, etc.)
KNOWN_SKILLS=""
for dir in "$REPO_ROOT/.claude/skills/core"/*/ "$REPO_ROOT/.claude/skills/frontend"/*/; do
  if [ -d "$dir" ]; then
    KNOWN_SKILLS="$KNOWN_SKILLS $(basename "$dir")"
  fi
done
for domain_dir in "$REPO_ROOT/.claude/skills/domains"/*/; do
  if [ -d "${domain_dir}skills" ]; then
    for skill_dir in "${domain_dir}skills"/*/; do
      if [ -d "$skill_dir" ]; then
        KNOWN_SKILLS="$KNOWN_SKILLS $(basename "$skill_dir")"
      fi
    done
  fi
done

if [ -z "$TEAM_FILES" ]; then
  echo "  ERROR: neither team.md nor frontend-team.md found in .claude/"
  ERRORS=$((ERRORS + 1))
else
  # For each known skill, check if it's referenced anywhere in the team files.
  # Then for each referenced skill, verify it resolves to a real file.
  REFERENCED_SKILLS=""
  for skill in $KNOWN_SKILLS; do
    if grep -q "\`$skill\`" $TEAM_FILES 2>/dev/null; then
      REFERENCED_SKILLS="$REFERENCED_SKILLS $skill"
      path=$(resolve_skill "$skill")
      if [ -n "$path" ]; then
        echo "  OK: $skill -> $path"
      else
        echo "  ERROR: referenced skill '$skill' not found in any tier"
        ERRORS=$((ERRORS + 1))
      fi
    fi
  done

  # Report skills that exist but are NOT referenced anywhere (warning — might be dead).
  # Meta-skills (ceo-orchestration, etc.) are exempted because they don't need a
  # routing-table entry — the CEO loads them at session start regardless.
  # Grandfathered skills (from skill-governance-grandfather.yaml) are also
  # exempted with an explicit reason code (PLAN-051 Phase 1 A1 — Opção 2).
  for skill in $KNOWN_SKILLS; do
    if is_meta_skill "$skill"; then
      echo "  OK: $skill (meta-skill, always-on, no routing entry required)"
      continue
    fi
    if is_grandfathered_skill "$skill"; then
      reason=$(get_grandfather_reason "$skill")
      echo "  OK: $skill (grandfathered: $reason — see .claude/skill-governance-grandfather.yaml)"
      continue
    fi
    if ! echo " $REFERENCED_SKILLS " | grep -q " $skill "; then
      echo "  WARN: skill '$skill' exists on disk but is not referenced in team.md / frontend-team.md / domains/*/team-personas.md"
      WARNINGS=$((WARNINGS + 1))
    fi
  done
fi

echo ""

# ---- 3. Check required governance files exist ----

echo "--- Checking required files ---"
REQUIRED_FILES=(
  ".claude/team.md"
  ".claude/pitfalls-catalog.yaml"
  ".claude/task-chains.yaml"
  ".claude/settings.json"
  ".claude/hooks/check_agent_spawn.py"
  ".claude/hooks/audit_log.py"
  ".claude/hooks/_python-hook.sh"
  # PLAN-081 Phase 2 — Pair-Rail dispatcher canonical surface.
  ".claude/dispatcher/routing-matrix.yaml"
  ".claude/dispatcher/routing-matrix-loader.py"
  ".claude/dispatcher/disable_predicate_eval.py"
)

for f in "${REQUIRED_FILES[@]}"; do
  if [ -f "$REPO_ROOT/$f" ]; then
    echo "  OK: $f"
  else
    echo "  MISSING: $f"
    ERRORS=$((ERRORS + 1))
  fi
done

echo ""

# ---- 4. Check hooks are executable ----

echo "--- Checking hooks ---"
for hook_rel in \
  ".claude/hooks/_python-hook.sh" \
  ".claude/hooks/check_agent_spawn.py" \
  ".claude/hooks/audit_log.py"
do
  hook_abs="$REPO_ROOT/$hook_rel"
  if [ -f "$hook_abs" ]; then
    if [ -x "$hook_abs" ]; then
      echo "  OK: $(basename "$hook_rel") is executable"
    else
      echo "  WARNING: $(basename "$hook_rel") is not executable"
      WARNINGS=$((WARNINGS + 1))
    fi
  fi
done

echo ""

# ---- 5. Squad min-count (ADR-009 bundle contract) ----
#
# Every squad under .claude/skills/domains/<name>/ must ship:
#   - team-personas.md with >= 5 persona sections (### headings)
#   - skills/ with >= 3 SKILL.md subdirectories
#   - pitfalls.yaml with >= 10 entries
#   - task-chains.yaml with >= 2 entries
#   - examples/ with >= 1 .md file
#
# Squads predating ADR-009 may be grandfathered via SQUAD_GRANDFATHER.
# New squads (introduced Sprint 5+) MUST pass the full check — failures
# are ERRORs, not warnings.

echo "--- Squad bundle contract (ADR-009) ---"

# Grandfather list — these squads predate ADR-009 OR have a different
# structural posture that doesn't map to the squad contract (e.g.
# `community` under PLAN-033 / ADR-060 is a meta-bucket for externally
# curated imports, not a self-contained squad). Failures emit WARNINGS
# only for grandfathered squads.
#
# `marketing-global` (added S94 2026-05-07): scaffolded by PLAN-074 Phase 0
# calibration with seo-specialist only (S90 commit e275473). Full populate
# scheduled for PLAN-074 Wave 4 (16 skills + team-personas.md +
# pitfalls.yaml + task-chains.yaml + examples/). Grandfathered until
# Wave 4 closes; remove this entry as part of Wave 4 ceremony.
#
# PLAN-153 Wave D imported squads (added S262 2026-07-09): agents-meta,
# architecture, cpp, data-ml, desktop, dotnet, golang, jvm are skills-only
# clean-room imports (1-2 skills each) — the same externally-imported
# posture as `community` (ADR-060), not /architect-authored squads.
# Graduate each by authoring its bundle via /architect (team-personas +
# pitfalls + task-chains + examples + >=3 skills), then remove it here.
SQUAD_GRANDFATHER="academic-humanities business-support civil-engineering community cpp data-ml devrel embedded finance-accounting fintech golang healthcare hospitality hr i18n-business identity-systems jvm lgpd-heavy-saas marketing-global mobile paid-media project-management real-estate-finance retail saas-platforms supply-chain training-l-and-d voice-ai"

is_grandfathered() {
  local name="$1"
  for g in $SQUAD_GRANDFATHER; do
    [ "$name" = "$g" ] && return 0
  done
  return 1
}

if [ -d "$REPO_ROOT/.claude/skills/domains" ]; then
  for squad_dir in "$REPO_ROOT/.claude/skills/domains"/*/; do
    [ -d "$squad_dir" ] || continue
    squad_name=$(basename "$squad_dir")
    echo "  Squad: $squad_name"

    # Decide bump level (ERROR vs WARN) based on grandfather status
    if is_grandfathered "$squad_name"; then
      BUMP_LABEL="WARN (grandfathered)"
      BUMP_ERR=0
    else
      BUMP_LABEL="ERROR"
      BUMP_ERR=1
    fi

    # 1. Personas
    personas_file="${squad_dir}team-personas.md"
    if [ -f "$personas_file" ]; then
      # grep -c exits 1 on zero matches; tolerate under set -e.
      personas_count=$(grep -cE '^### ' "$personas_file" 2>/dev/null || true)
      [ -n "$personas_count" ] || personas_count=0
      if [ "$personas_count" -ge 5 ]; then
        echo "    OK: personas=$personas_count (>=5)"
      else
        echo "    $BUMP_LABEL: personas=$personas_count (<5) in team-personas.md"
        if [ "$BUMP_ERR" -eq 1 ]; then
          ERRORS=$((ERRORS + 1))
        else
          WARNINGS=$((WARNINGS + 1))
        fi
      fi
    else
      echo "    $BUMP_LABEL: team-personas.md missing"
      if [ "$BUMP_ERR" -eq 1 ]; then
        ERRORS=$((ERRORS + 1))
      else
        WARNINGS=$((WARNINGS + 1))
      fi
    fi

    # 2. Skills
    skills_count=0
    if [ -d "${squad_dir}skills" ]; then
      skills_count=$(find "${squad_dir}skills" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
    fi
    if [ "$skills_count" -ge 3 ]; then
      echo "    OK: skills=$skills_count (>=3)"
    else
      echo "    $BUMP_LABEL: skills=$skills_count (<3)"
      if [ "$BUMP_ERR" -eq 1 ]; then
        ERRORS=$((ERRORS + 1))
      else
        WARNINGS=$((WARNINGS + 1))
      fi
    fi

    # 3. Pitfalls
    pitfalls_file="${squad_dir}pitfalls.yaml"
    if [ -f "$pitfalls_file" ]; then
      # grep -c exits 1 on zero matches; tolerate under set -e.
      pitfalls_count=$(grep -cE '^[[:space:]]*- id:' "$pitfalls_file" 2>/dev/null || true)
      [ -n "$pitfalls_count" ] || pitfalls_count=0
      if [ "$pitfalls_count" -ge 10 ]; then
        echo "    OK: pitfalls=$pitfalls_count (>=10)"
      else
        echo "    $BUMP_LABEL: pitfalls=$pitfalls_count (<10)"
        if [ "$BUMP_ERR" -eq 1 ]; then
          ERRORS=$((ERRORS + 1))
        else
          WARNINGS=$((WARNINGS + 1))
        fi
      fi
    else
      echo "    $BUMP_LABEL: pitfalls.yaml missing"
      if [ "$BUMP_ERR" -eq 1 ]; then
        ERRORS=$((ERRORS + 1))
      else
        WARNINGS=$((WARNINGS + 1))
      fi
    fi

    # 4. Task chains
    chains_file="${squad_dir}task-chains.yaml"
    if [ -f "$chains_file" ]; then
      # grep -c exits 1 on zero matches; tolerate under set -e.
      chains_count=$(grep -cE '^[[:space:]]*- id:' "$chains_file" 2>/dev/null || true)
      [ -n "$chains_count" ] || chains_count=0
      if [ "$chains_count" -ge 2 ]; then
        echo "    OK: task-chains=$chains_count (>=2)"
      else
        echo "    $BUMP_LABEL: task-chains=$chains_count (<2)"
        if [ "$BUMP_ERR" -eq 1 ]; then
          ERRORS=$((ERRORS + 1))
        else
          WARNINGS=$((WARNINGS + 1))
        fi
      fi
    else
      echo "    $BUMP_LABEL: task-chains.yaml missing"
      if [ "$BUMP_ERR" -eq 1 ]; then
        ERRORS=$((ERRORS + 1))
      else
        WARNINGS=$((WARNINGS + 1))
      fi
    fi

    # 5. Examples
    examples_count=0
    if [ -d "${squad_dir}examples" ]; then
      examples_count=$(find "${squad_dir}examples" -maxdepth 1 -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')
    fi
    if [ "$examples_count" -ge 1 ]; then
      echo "    OK: examples=$examples_count (>=1)"
    else
      echo "    $BUMP_LABEL: examples=$examples_count (<1 — need examples/PLAN-*.md)"
      if [ "$BUMP_ERR" -eq 1 ]; then
        ERRORS=$((ERRORS + 1))
      else
        WARNINGS=$((WARNINGS + 1))
      fi
    fi
  done
fi

echo ""

# ---- 5-ter. PLAN-SCHEMA §1 directory + filename invariants (PLAN-019 VP-F4) ----
#
# PLAN-SCHEMA.md §1 documents:
#   - files directly under .claude/plans/ MUST match
#       PLAN-<NNN>-<kebab-case-slug>.md
#       OR one of: README.md, PLAN-SCHEMA.md, AUDIT-LOG-SCHEMA.md, DEBATE-SCHEMA.md
#   - subdirectories directly under .claude/plans/ MUST match
#       PLAN-<NNN>/ | examples/ | archive/
#
# Sprint 1 shipped this as documentary; PLAN-019 VP-F4 promotes to mechanical
# enforcement. Violations are ERRORS (bump ERRORS counter so the script exits 1).

echo "--- PLAN-SCHEMA §1 invariants ---"
PLAN_DIR="$REPO_ROOT/.claude/plans"
if [ -d "$PLAN_DIR" ]; then
  # 1) Subdirectory check
  # PLAN-106 Wave J: accept `_templates/` (reusable ceremony bundles).
  # PLAN-106 fix-up: accept `PLAN-NNN-FOLLOWUP/` pre-existing convention
  # (FOLLOWUP plans may carry their own subdir for staged artifacts;
  # convention never blessed in PLAN-SCHEMA pre-PLAN-106 but in active use).
  invalid_dirs=$(find "$PLAN_DIR" -mindepth 1 -maxdepth 1 -type d \
    ! -name 'PLAN-[0-9][0-9][0-9]' \
    ! -name 'PLAN-[0-9][0-9][0-9]-FOLLOWUP' \
    ! -name 'PLAN-[0-9][0-9][0-9]-FOLLOWUP-*' \
    ! -name '_templates' \
    ! -name 'examples' \
    ! -name 'archive' \
    ! -name 'WAR-ROOM' \
    2>/dev/null || true)
  if [ -n "$invalid_dirs" ]; then
    echo "  FAIL: PLAN-SCHEMA §1 invalid subdir(s) under .claude/plans:"
    # shellcheck disable=SC2001
    echo "$invalid_dirs" | sed 's|^|    |'
    ERRORS=$((ERRORS + 1))
  else
    echo "  OK: no invalid subdirectories"
  fi

  # 1b) Orphan-dir guard (PLAN-152 governance-05 / dead-code-03).
  # PLAN-SCHEMA §1 subdir rule 1: a `PLAN-<NNN>/` subdir is only legal when
  # it matches an EXISTING top-level plan file (`PLAN-<NNN>-<slug>.md` or
  # `PLAN-<NNN>-FOLLOWUP-<slug>.md`). A dir with no plan file at all is an
  # orphan (the PLAN-128 clean-room-migration class) and FAILs.
  orphan_dirs=""
  while IFS= read -r d; do
    [ -z "$d" ] && continue
    nnn=$(basename "$d")   # e.g. PLAN-128
    plan_match=$(find "$PLAN_DIR" -mindepth 1 -maxdepth 1 -type f -name "${nnn}-*.md" 2>/dev/null)
    if [ -z "$plan_match" ]; then
      orphan_dirs="$orphan_dirs\n    $d"
    fi
  done < <(find "$PLAN_DIR" -mindepth 1 -maxdepth 1 -type d -name 'PLAN-[0-9][0-9][0-9]' 2>/dev/null)
  if [ -n "$orphan_dirs" ]; then
    # shellcheck disable=SC2059
    printf "  FAIL: PLAN-SCHEMA §1 orphan PLAN-<NNN> subdir(s) — no matching PLAN-<NNN>-*.md plan file:$orphan_dirs\n"
    ERRORS=$((ERRORS + 1))
  else
    echo "  OK: every PLAN-NNN subdir has a matching plan file"
  fi

  # 2) Filename check (files directly under .claude/plans/)
  KNOWN_GOV_FILES="README.md PLAN-SCHEMA.md AUDIT-LOG-SCHEMA.md DEBATE-SCHEMA.md"
  invalid_files=""
  # -mindepth/-maxdepth 1 keeps us at the top level only.
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    bname=$(basename "$f")
    # PLAN-045 Wave-5 polish: macOS Finder .DS_Store is already
    # gitignored + not tracked in repo; skip silently (test-env
    # hygiene, not a governance signal).
    if [ "$bname" = ".DS_Store" ]; then
      continue
    fi
    # Known governance filename?
    is_known=0
    for g in $KNOWN_GOV_FILES; do
      if [ "$bname" = "$g" ]; then
        is_known=1
        break
      fi
    done
    if [ $is_known -eq 1 ]; then
      continue
    fi
    # PLAN-045 Wave-5 polish: cross-plan roadmap artefacts may sit
    # alongside PLAN-NNN files (e.g. SPRINT-30-ROADMAP.md consolidating
    # PLAN-044/045/046/047 dispatch sequence). Naming convention:
    # SPRINT-<N>-<slug>.md where N is digit(s).
    case "$bname" in
      SPRINT-[0-9]*-*.md)
        continue
        ;;
    esac
    # Must match PLAN-<NNN>-<kebab-case-slug>.md (NNN is exactly 3 digits)
    # PLAN-106 fix-up: also accept PLAN-<NNN>-FOLLOWUP-<slug>.md (pre-existing
    # convention; FOLLOWUP literal is uppercase by design — distinguishes
    # the recursive amendment slot from the parent plan filename).
    if ! echo "$bname" | grep -Eq '^PLAN-[0-9]{3}(-FOLLOWUP)?-[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
      invalid_files="$invalid_files\n    $f"
    fi
  done < <(find "$PLAN_DIR" -mindepth 1 -maxdepth 1 -type f 2>/dev/null)

  if [ -n "$invalid_files" ]; then
    # shellcheck disable=SC2059
    printf "  FAIL: PLAN-SCHEMA §1 invalid filename(s) under .claude/plans:$invalid_files\n"
    ERRORS=$((ERRORS + 1))
  else
    echo "  OK: all filenames match PLAN-<NNN>-<slug>.md or known governance names"
  fi

  # 3) Plan frontmatter governance (PLAN-SCHEMA §1.4 id-uniqueness + §2
  #    required id/status + §4 status legality), delegated to the Python
  #    fast-validator functions so the bash gate and ceo-boot share ONE
  #    tested implementation instead of a parallel awk reimplementation.
  #    Two reasons (S213):
  #      - Correctness: a cross-model review caught two bash<->python
  #        divergences in the separate-awk form (frontmatter not anchored at
  #        file start; blank `id:` accepted). One implementation can't diverge
  #        from itself.
  #      - Perf: the per-file awk passes (3 checks x 155 plans = hundreds of
  #        subprocesses) pushed this script past the 20s test_real_repo_passes
  #        CI timeout. One Python process does all three checks in a single
  #        pass (~0.2s vs ~2s).
  #    Fail-CLOSED: if the helper is present but errors (import/syntax),
  #    report FAIL rather than silently passing. If the helper is ABSENT
  #    (e.g. a stripped-down install or a minimal test fixture that copies
  #    only this script), SKIP gracefully — install.sh ships both files, so
  #    a real adopter always has it.
  VGF_HELPER="$REPO_ROOT/.claude/scripts/validate_governance_fast.py"
  if [ -f "$VGF_HELPER" ]; then
    plan_fm_rc=0
    plan_fm_errors=$(python3 - "$REPO_ROOT" <<'PY'
import importlib.util
import sys
from pathlib import Path

repo = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location(
    "vgf_plan_checks",
    str(repo / ".claude" / "scripts" / "validate_governance_fast.py"),
)
vgf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vgf)
errors = []
vgf._check_plan_id_uniqueness(repo, errors)
vgf._check_plan_frontmatter_status(repo, errors)
vgf._check_plan_id_presence(repo, errors)
vgf._check_plan_vcheck_declarations(repo, errors)
for e in errors:
    print(e)
PY
    ) || plan_fm_rc=$?
    if [ "$plan_fm_rc" -ne 0 ]; then
      echo "  FAIL: PLAN-SCHEMA plan-frontmatter helper errored (rc=$plan_fm_rc)"
      ERRORS=$((ERRORS + 1))
    elif [ -n "$plan_fm_errors" ]; then
      echo "  FAIL: PLAN-SCHEMA §1.4/§2/§4 plan frontmatter violation(s):"
      echo "$plan_fm_errors" | sed 's|^|    |'
      ERRORS=$((ERRORS + 1))
    else
      echo "  OK: all root-level plans have a unique id, a frontmatter id, and a legal status"
    fi
  else
    echo "  SKIP: plan-frontmatter checks (validate_governance_fast.py not present)"
  fi
else
  echo "  SKIP: .claude/plans directory not found"
fi

echo ""

# ---- 5-bis. CLAUDE.md size check (PLAN-010 C16) ----
# CLAUDE.md loaded every session; >40k chars triggers Claude Code perf warning.
# Archive history to CLAUDE_FULL.md (feedback_claude_md_size_limit memory).
echo "--- CLAUDE.md size ---"
CLAUDE_MD_PATH="${CLAUDE_MD_PATH:-CLAUDE.md}"
if [ -f "$CLAUDE_MD_PATH" ]; then
  CLAUDE_MD_BYTES=$(wc -c < "$CLAUDE_MD_PATH" | tr -d ' ')
  CLAUDE_MD_LIMIT="${CLAUDE_MD_SIZE_LIMIT:-40000}"
  if [ "$CLAUDE_MD_BYTES" -ge "$CLAUDE_MD_LIMIT" ]; then
    echo "  FAIL: $CLAUDE_MD_PATH is $CLAUDE_MD_BYTES bytes (limit $CLAUDE_MD_LIMIT)."
    ERRORS=$((ERRORS + 1))
  else
    echo "  OK: $CLAUDE_MD_PATH is $CLAUDE_MD_BYTES bytes (limit $CLAUDE_MD_LIMIT)."
  fi
else
  echo "  SKIP: $CLAUDE_MD_PATH not found"
fi

echo ""

# ---- 5-quater. settings.json JSON parseability (PLAN-019 F-CHAOS-10) ----
#
# A corrupted .claude/settings.json silently disables every hook. This
# check parses it via Python stdlib json and escalates to ERROR on any
# parse failure. Missing-file is only a WARNING — a fresh framework
# checkout before install may legitimately lack the file.

echo "--- settings.json parseability (F-CHAOS-10) ---"
SETTINGS_JSON="$REPO_ROOT/.claude/settings.json"
if [ -f "$SETTINGS_JSON" ]; then
  # Redirect Python traceback to the log; capture rc for the ERROR bump.
  if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$SETTINGS_JSON" 2>/tmp/validate-governance-settings-json-err.$$; then
    echo "  OK: .claude/settings.json parses as JSON"
  else
    echo "  FAIL: .claude/settings.json is not valid JSON — hooks will silently fail to load"
    # Surface the parse error (indented) so operator sees it inline.
    if [ -s /tmp/validate-governance-settings-json-err.$$ ]; then
      sed 's|^|    |' /tmp/validate-governance-settings-json-err.$$
    fi
    ERRORS=$((ERRORS + 1))
  fi
  rm -f /tmp/validate-governance-settings-json-err.$$
else
  echo "  WARN: $SETTINGS_JSON not found"
  WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ---- 5-quinto. PLAN-020 Phase 1+2 — native subagents + skill-reference lint ----

echo "--- PLAN-020 native subagents + skill-reference (ADR-050/051) ---"

AGENTS_DIR="$REPO_ROOT/.claude/agents"
DISPATCH_FILE="$AGENTS_DIR/_dispatch.md"

if [ -d "$AGENTS_DIR" ]; then
  AGENT_COUNT=$(find "$AGENTS_DIR" -maxdepth 1 -name '*.md' -not -name '_*.md' 2>/dev/null | wc -l | tr -d ' ')
  echo "  Native agents found: $AGENT_COUNT"

  # Lint each agent: verify YAML frontmatter + skill reference
  for agent_file in "$AGENTS_DIR"/*.md; do
    [ -f "$agent_file" ] || continue
    base=$(basename "$agent_file")
    # Skip _probe_*, _dispatch.md
    case "$base" in _*) continue ;; esac

    # Frontmatter present
    if ! head -1 "$agent_file" | grep -q '^---$'; then
      echo "  ERROR: $base missing YAML frontmatter (must start with '---')"
      ERRORS=$((ERRORS + 1))
      continue
    fi

    # name + description + version keys present
    for required_key in name description version; do
      if ! grep -qE "^${required_key}:" "$agent_file"; then
        echo "  ERROR: $base frontmatter missing '${required_key}:' key"
        ERRORS=$((ERRORS + 1))
      fi
    done

    # PLAN-021 ADR-052: model field lint (advisory WARNING if missing;
    # ERROR if present but not one of the 4 canonical IDs — ADR-149
    # allowlist: fable-5 flagship + the 3 Claude 4.x IDs, additive).
    model_line=$(grep -E "^model:" "$agent_file" | head -1)
    if [ -z "$model_line" ]; then
      echo "  WARN: $base missing 'model:' frontmatter field (ADR-052 recommends explicit)"
      WARNINGS=$((WARNINGS + 1))
    else
      model_val=$(echo "$model_line" | sed -E 's/^model:[[:space:]]*//' | tr -d '[:space:]')
      case "$model_val" in
        claude-fable-5|claude-opus-4-8|claude-sonnet-4-6|claude-haiku-4-5-20251001|"")
          : ;;
        *)
          echo "  ERROR: $base has invalid model value: '$model_val'"
          echo "    Expected one of: claude-fable-5, claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5-20251001, or empty (inherit)"
          ERRORS=$((ERRORS + 1))
          ;;
      esac
    fi

    # Skill reference (if present): file exists + filename is SKILL.md +
    # under skills root
    skill_ref=$(grep -E '^@[^[:space:]]+[[:space:]]+sha256=[0-9a-f]{64}' "$agent_file" | head -1)
    if [ -n "$skill_ref" ]; then
      # BSD sed (macOS) doesn't support \S; use [^[:space:]] for portability
      ref_path=$(echo "$skill_ref" | sed -E 's/^@([^[:space:]]+).*/\1/')
      ref_hash=$(echo "$skill_ref" | sed -E 's/.*sha256=([0-9a-f]{64}).*/\1/')

      # Resolve path relative to repo root
      if [ "${ref_path:0:1}" = "/" ]; then
        full_path="$ref_path"
      else
        full_path="$REPO_ROOT/$ref_path"
      fi

      if [ ! -f "$full_path" ]; then
        echo "  ERROR: $base references missing file $ref_path"
        ERRORS=$((ERRORS + 1))
      else
        # Verify SKILL.md filename
        if [ "$(basename "$full_path")" != "SKILL.md" ]; then
          echo "  ERROR: $base references non-SKILL.md file: $ref_path"
          ERRORS=$((ERRORS + 1))
        fi
        # Verify under skills root
        case "$ref_path" in
          .claude/skills/*) : ;;
          *)
            echo "  ERROR: $base references path outside .claude/skills/: $ref_path"
            ERRORS=$((ERRORS + 1))
            ;;
        esac
        # Verify SHA-256 hash matches actual file content
        actual_hash=$(python3 -c "
import hashlib, sys
print(hashlib.sha256(open('$full_path', 'rb').read()).hexdigest())
" 2>/dev/null || echo "")
        if [ -z "$actual_hash" ]; then
          echo "  WARN: $base could not compute hash for $ref_path"
          WARNINGS=$((WARNINGS + 1))
        elif [ "$actual_hash" != "$ref_hash" ]; then
          echo "  ERROR: $base SHA-256 mismatch for $ref_path"
          echo "    expected: $ref_hash"
          echo "    actual:   $actual_hash"
          echo "    Fix: regenerate hash via:"
          echo "    python3 -c \"import hashlib; print(hashlib.sha256(open('$ref_path','rb').read()).hexdigest())\""
          ERRORS=$((ERRORS + 1))
        fi
      fi
    fi
  done

  # _dispatch.md must be in sync (auto-generated)
  if [ -f "$DISPATCH_FILE" ]; then
    if [ -f "$REPO_ROOT/.claude/scripts/generate-dispatch.py" ]; then
      if ! python3 "$REPO_ROOT/.claude/scripts/generate-dispatch.py" --check >/dev/null 2>&1; then
        echo "  ERROR: _dispatch.md is stale. Run:"
        echo "    python3 .claude/scripts/generate-dispatch.py --write"
        ERRORS=$((ERRORS + 1))
      else
        echo "  OK: _dispatch.md in sync ($AGENT_COUNT agents)"
      fi
      # PLAN-137 A3-parse: fail-closed frontmatter validation of the
      # optional native fields (maxTurns/isolation/skills). The 13 real
      # agents carry none of these today, so this passes trivially now —
      # it protects every future agent edit from a malformed value.
      if ! validate_out=$(python3 "$REPO_ROOT/.claude/scripts/generate-dispatch.py" --validate 2>&1); then
        echo "  ERROR: agent frontmatter validation failed:"
        echo "$validate_out" | sed 's/^/    /'
        ERRORS=$((ERRORS + 1))
      else
        echo "  OK: agent frontmatter valid (maxTurns/isolation/skills)"
      fi
    fi
  else
    if [ "$AGENT_COUNT" -gt 0 ]; then
      echo "  WARN: $AGENT_COUNT agents but no _dispatch.md (run --write)"
      WARNINGS=$((WARNINGS + 1))
    fi
  fi
else
  echo "  NOTE: .claude/agents/ not present (PLAN-020 Phase 1 not yet installed)"
fi

echo ""

# ---- 5bis. ADR enforcement_commit field (PLAN-045 Wave 3 P0-16) ----
#
# Every ADR with `Status: ACCEPTED` MUST declare an `Enforcement commit:`
# field — either a git commit SHA that touches a file under .claude/hooks/
# or .claude/scripts/ (runtime anchor), OR the literal
# `n/a (documentation-only)` for ADRs that don't claim runtime behaviour.
#
# Closes the "declared but not wired" meta-pattern (PLAN-044 Pattern 1):
# ADRs described mechanisms like CEO_MULTIMODEL_ENABLE kill-switch or
# reset_chain_on_rotation() call site but the code did not enforce them.
#
# ADR back-fill is a Wave 5 polish task — missing field on pre-PLAN-045
# ADRs is a WARNING, not an ERROR. ADRs created AFTER 2026-04-20 (the
# template-amendment date) without the field are ERRORS.
#
# The distinction is encoded via the ADR's Date: field. ADR-000 through
# ADR-064 were all authored before 2026-04-20 — grandfathered. New ADRs
# (ADR-065+) use the amended template and must include the field.

echo "--- ADR enforcement_commit field (PLAN-045 P0-16) ---"
ADR_MISSING_FIELD=0
ADR_GRANDFATHERED=0
if [ -d "$REPO_ROOT/.claude/adr" ]; then
  for adr in "$REPO_ROOT/.claude/adr"/ADR-*.md; do
    [ -f "$adr" ] || continue
    base=$(basename "$adr")
    status_line=$(grep -m1 "^\*\*Status:\*\*" "$adr" 2>/dev/null || echo "")
    # Only enforce on ACCEPTED status.
    case "$status_line" in
      *"ACCEPTED"*) ;;
      *) continue ;;
    esac
    # Accept either format:
    #   (a) `**Enforcement commit:**` bold field (original convention)
    #   (b) `## Enforcement commit` H2 section (PLAN-050 Phase 2 retrofit)
    # Both encode the same semantic — an anchored commit SHA or n/a marker.
    if grep -q "^\*\*Enforcement commit:\*\*" "$adr" \
       || grep -q "^## Enforcement commit" "$adr"; then
      continue  # field or section present — good
    fi
    # Grandfather check: extract ADR number and treat ADR-001..064 as
    # pre-PLAN-045 legacy.
    adr_num=$(echo "$base" | sed -E 's/^ADR-([0-9]+).*/\1/' | sed 's/^0*//')
    if [ -z "$adr_num" ]; then
      adr_num=0
    fi
    if [ "$adr_num" -le 64 ]; then
      ADR_GRANDFATHERED=$((ADR_GRANDFATHERED + 1))
    else
      # audit-v2 C1-P0-08 Path A (2026-04-27): demoted ERROR → WARNING
      echo "  WARN: $base is ACCEPTED but missing 'Enforcement commit:' field"
      echo "    (recommended for ADR-065+; see .claude/adr/README.md §Enforcement)"
      WARNINGS=$((WARNINGS + 1))
      ADR_MISSING_FIELD=$((ADR_MISSING_FIELD + 1))
    fi
  done
  if [ "$ADR_GRANDFATHERED" -gt 0 ]; then
    echo "  INFO: $ADR_GRANDFATHERED legacy ADRs (ADR-001..064) grandfathered"
    echo "    pending Wave 5 polish back-fill sweep."
  fi
  if [ "$ADR_MISSING_FIELD" -eq 0 ] && [ "$ADR_GRANDFATHERED" -eq 0 ]; then
    echo "  OK: every ACCEPTED ADR declares Enforcement commit"
  fi
fi

echo ""

# ---- 5ter. CLAUDE.md / README count-drift advisory (PLAN-045 F-06-01) ----
#
# CLAUDE.md §4 Quick Reference and architecture diagram cite fixed skill
# and ADR counts. The validate-governance script already knows the disk
# truth (§1 above). Here we cross-check that the prose numbers match.
# Divergence is WARNING — drift is a doc-hygiene issue, not a governance
# break.
#
# Regex matches:
#   - "N core" where N is the integer disk count
#   - "N frontend"
#   - "N ADRs" (first column in a quick-ref table row)
#   - Total "N skills" (20+9+24=53 today)

echo "--- CLAUDE.md count-drift advisory (PLAN-045 F-06-01) ---"
CLAUDE_MD="$REPO_ROOT/CLAUDE.md"
DRIFTS=0

# Temporarily relax pipefail so grep-no-match within assignments doesn't
# terminate the script under set -euo pipefail.
set +e

if [ -f "$CLAUDE_MD" ]; then
  # ADR count
  ADR_DISK=$(find "$REPO_ROOT/.claude/adr" -maxdepth 1 -name 'ADR-*.md' 2>/dev/null | wc -l | tr -d ' ')
  if ! grep -qE "\*\*${ADR_DISK} ADRs?\*\*" "$CLAUDE_MD" 2>/dev/null; then
    PROSE_ADR=$(grep -oE '\*\*[0-9]+ ADRs?\*\*' "$CLAUDE_MD" 2>/dev/null | head -1 | tr -cd '0-9' || true)
    if [ -n "$PROSE_ADR" ] && [ "$PROSE_ADR" != "$ADR_DISK" ]; then
      echo "  WARN: CLAUDE.md prose says $PROSE_ADR ADRs; disk has $ADR_DISK"
      WARNINGS=$((WARNINGS + 1))
      DRIFTS=$((DRIFTS + 1))
    fi
  fi

  # Core skill count
  if [ "$CORE_COUNT" -gt 0 ]; then
    if ! grep -qE "${CORE_COUNT} core" "$CLAUDE_MD" 2>/dev/null; then
      PROSE_CORE=$(grep -oE '[0-9]+ core' "$CLAUDE_MD" 2>/dev/null | head -1 | awk '{print $1}' || true)
      if [ -n "$PROSE_CORE" ] && [ "$PROSE_CORE" != "$CORE_COUNT" ]; then
        echo "  WARN: CLAUDE.md says $PROSE_CORE core skills; disk has $CORE_COUNT"
        WARNINGS=$((WARNINGS + 1))
        DRIFTS=$((DRIFTS + 1))
      fi
    fi
  fi

  # Frontend skill count
  if [ "$FRONTEND_COUNT" -gt 0 ]; then
    if ! grep -qE "${FRONTEND_COUNT} frontend" "$CLAUDE_MD" 2>/dev/null; then
      PROSE_FRONT=$(grep -oE '[0-9]+ frontend' "$CLAUDE_MD" 2>/dev/null | head -1 | awk '{print $1}' || true)
      if [ -n "$PROSE_FRONT" ] && [ "$PROSE_FRONT" != "$FRONTEND_COUNT" ]; then
        echo "  WARN: CLAUDE.md says $PROSE_FRONT frontend skills; disk has $FRONTEND_COUNT"
        WARNINGS=$((WARNINGS + 1))
        DRIFTS=$((DRIFTS + 1))
      fi
    fi
  fi

  # Total-skill count
  if ! grep -qE "\*\*${TOTAL_SKILLS} skills\*\*" "$CLAUDE_MD" 2>/dev/null; then
    PROSE_TOTAL=$(grep -oE '\*\*[0-9]+ skills\*\*' "$CLAUDE_MD" 2>/dev/null | head -1 | tr -cd '0-9' || true)
    if [ -n "$PROSE_TOTAL" ] && [ "$PROSE_TOTAL" != "$TOTAL_SKILLS" ]; then
      echo "  WARN: CLAUDE.md says $PROSE_TOTAL total skills; disk has $TOTAL_SKILLS"
      WARNINGS=$((WARNINGS + 1))
      DRIFTS=$((DRIFTS + 1))
    fi
  fi

  if [ "$DRIFTS" -eq 0 ]; then
    echo "  OK: CLAUDE.md prose counts match disk (ADRs=$ADR_DISK / core=$CORE_COUNT / frontend=$FRONTEND_COUNT / total=$TOTAL_SKILLS)"
  fi
fi

set -e

echo ""

# ---- 5quater. Cross-doc drift (PLAN-045 F-05-01/02/03) ----
#
# Advisory check across canonical docs (README + INSTALL + ROADMAP +
# HONEST-LIMITATIONS + CTO-GUIDE + GUIA-COMPLETO + CLAUDE.md). Reports
# skill/ADR count claims that don't match disk truth. WARN-only.

if [ -x "$REPO_ROOT/.claude/scripts/check-docs-drift.py" ]; then
  echo "--- Cross-doc drift advisory (PLAN-045 F-05-01/02/03) ---"
  # shellcheck disable=SC2034  # DRIFT_EXIT captured for future strict-mode use; advisory now.
  DRIFT_EXIT=0
  # shellcheck disable=SC2034
  "$REPO_ROOT/.claude/scripts/check-docs-drift.py" > "$REPO_ROOT/.docs-drift.out" 2>&1 || DRIFT_EXIT=$?
  DRIFT_WARN=$({ grep "claims" "$REPO_ROOT/.docs-drift.out" 2>/dev/null || true; } | wc -l | tr -d ' ')
  if [ "${DRIFT_WARN:-0}" -gt 0 ]; then
    echo "  WARN: $DRIFT_WARN doc-drift findings (see full report below)"
    grep "claims" "$REPO_ROOT/.docs-drift.out" | head -10 | sed 's/^/    /'
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  OK: no count-drift in canonical docs"
  fi
  rm -f "$REPO_ROOT/.docs-drift.out"
  echo ""
fi

# ---- 5quinquies. Rule-invariant phrase-deletion guard (PLAN-139 Wave A) ----
#
# FAIL-CLOSED parity detector: load-bearing spine phrases (GATE protocol /
# Critical Rules / Spawn protocol) must not be silently dropped from the
# tracked canonical docs (CLAUDE.md / PROTOCOL.md) during a careless closeout
# compaction. This is a DELETION/parity detector, NOT a tamper guard — a
# present-but-neutered phrase passes (substring presence cannot verify
# surrounding semantics). The script auto-SKIPs in adopter installs (keyed on
# the framework-only ADR-001 marker), so adopter validate stays green.
if [ -x "$REPO_ROOT/.claude/scripts/check-rule-invariants.py" ]; then
  echo "--- Rule-invariant phrase-deletion guard (PLAN-139 Wave A) ---"
  RULE_INV_EXIT=0
  "$REPO_ROOT/.claude/scripts/check-rule-invariants.py" --repo "$REPO_ROOT" \
    > "$REPO_ROOT/.rule-invariants.out" 2>&1 || RULE_INV_EXIT=$?
  if [ "${RULE_INV_EXIT:-0}" -ne 0 ]; then
    echo "  ERROR: rule-invariant guard failed (a pinned spine phrase is missing):"
    head -20 "$REPO_ROOT/.rule-invariants.out" | sed 's/^/    /'
    ERRORS=$((ERRORS + 1))
  else
    echo "  OK: $(head -1 "$REPO_ROOT/.rule-invariants.out")"
  fi
  rm -f "$REPO_ROOT/.rule-invariants.out"
  echo ""
fi

# ---- 6. Wave 0 validators (PLAN-074 ADJ-B4 / ADJ-F2 / ADJ-C4) ----
#
# Three frontmatter validators staged as part of PLAN-074 Wave 0 hardening:
#
#  V1 — inspired_by: completeness (ADJ-B4)
#       Every SKILL.md with 'inspired_by:' must have source/license/relationship/
#       authored_by/authored_at fields, and source must carry a 40-hex SHA pin.
#
#  V2 — runtime_mechanism: false lint (ADJ-F2 + Codex S90 P2-02 STRICT)
#       Files under docs/playbooks/ MUST have frontmatter key 'runtime_mechanism:'
#       PRESENT and set to 'false'. Three behaviors:
#         - 'runtime_mechanism: false' → PASS
#         - 'runtime_mechanism: true'  → ERROR (elevation requires a new ADR)
#         - key ABSENT                  → ERROR per P2-02 strict (explicit marker)
#
#  V3 — PII inheritance (ADJ-C4)
#       Skills in PII-required domains (legal/healthcare/real-estate-finance/hr/
#       finance-accounting) MUST declare 'inherits: [core/compliance-lgpd]' AND
#       'pii_handling: required'. Retail/hospitality domains: WARN only.
#
# Implementation: Python helper at .claude/scripts/validate-skill-frontmatter.py
# (staged from .claude/plans/PLAN-074/staging/ — promoted via Wave 0 ceremony).

FRONTMATTER_VALIDATOR="$REPO_ROOT/.claude/scripts/validate-skill-frontmatter.py"
# Fallback to staging path if ceremony has not yet promoted the file.
if [ ! -f "$FRONTMATTER_VALIDATOR" ]; then
  FRONTMATTER_VALIDATOR="$REPO_ROOT/.claude/plans/PLAN-074/staging/validate-skill-frontmatter.py"
fi

if [ ! -f "$FRONTMATTER_VALIDATOR" ]; then
  echo "  SKIP: validate-skill-frontmatter.py not found (Wave 0 not yet applied)"
else

  # --- V1: inspired_by: validator (runs on all SKILL.md files) ---
  echo "--- V1: inspired_by: frontmatter validator (PLAN-074 ADJ-B4) ---"
  V1_ERRORS=0
  set +e
  while IFS= read -r skill_file; do
    result=$(python3 "$FRONTMATTER_VALIDATOR" --v1 "$skill_file" 2>&1)
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "$result" | sed 's/^/  /'
      V1_ERRORS=$((V1_ERRORS + 1))
      ERRORS=$((ERRORS + 1))
    fi
  done < <(find "$REPO_ROOT/.claude/skills" -name "SKILL.md" 2>/dev/null)
  set -e
  if [ "$V1_ERRORS" -eq 0 ]; then
    echo "  OK: all SKILL.md files pass inspired_by: validator"
  fi
  echo ""

  # --- V2: runtime_mechanism: false lint (runs on docs/playbooks/*.md) ---
  echo "--- V2: runtime_mechanism lint for docs/playbooks/ (PLAN-074 ADJ-F2) ---"
  V2_ERRORS=0
  set +e
  if [ -d "$REPO_ROOT/docs/playbooks" ]; then
    while IFS= read -r pb_file; do
      result=$(python3 "$FRONTMATTER_VALIDATOR" --v2 "$pb_file" 2>&1)
      rc=$?
      if [ $rc -ne 0 ]; then
        echo "$result" | sed 's/^/  /'
        V2_ERRORS=$((V2_ERRORS + 1))
        ERRORS=$((ERRORS + 1))
      fi
    done < <(find "$REPO_ROOT/docs/playbooks" -name "*.md" 2>/dev/null)
  fi
  set -e
  if [ "$V2_ERRORS" -eq 0 ]; then
    echo "  OK: every docs/playbooks/ file declares 'runtime_mechanism: false' explicitly"
  fi
  echo ""

  # --- V3: PII inheritance (runs on PII-domain SKILL.md files) ---
  echo "--- V3: PII inheritance for sensitive domains (PLAN-074 ADJ-C4) ---"
  V3_ERRORS=0
  set +e
  for domain_dir in "$REPO_ROOT/.claude/skills/domains"/*/; do
    [ -d "$domain_dir" ] || continue
    domain_name=$(basename "$domain_dir")
    if [ -d "${domain_dir}skills" ]; then
      while IFS= read -r skill_file; do
        result=$(python3 "$FRONTMATTER_VALIDATOR" --v3 --domain "$domain_name" "$skill_file" 2>&1)
        rc=$?
        if [ $rc -ne 0 ]; then
          echo "$result" | sed 's/^/  /'
          V3_ERRORS=$((V3_ERRORS + 1))
          ERRORS=$((ERRORS + 1))
        else
          # Surface warnings (exit 0 but may have WARN output)
          if [ -n "$result" ]; then
            echo "$result" | sed 's/^/  /'
            WARNINGS=$((WARNINGS + 1))
          fi
        fi
      done < <(find "${domain_dir}skills" -name "SKILL.md" 2>/dev/null)
    fi
  done
  set -e
  if [ "$V3_ERRORS" -eq 0 ]; then
    echo "  OK: PII-domain skills pass inheritance check"
  fi
  echo ""

fi  # end FRONTMATTER_VALIDATOR present check

# ---- 6b. WS-C (PLAN-117): SKILL.md description-length + strict-YAML gate ----
# Enforces description <= 1024 chars (LINT-FM-04, stdlib) + strict-YAML
# validity (LINT-FM-05, best-effort PyYAML — no-ops in bare stdlib-only
# adopter envs). Scoped via --only-rules so pre-existing UNRELATED lint
# findings (e.g. LINT-FM-10) do not gate here (PLAN-117 WS-C AC-C3).
# PLAN-135 W3 K1: scope extended with the optional auto-activation fields —
# paths: non-empty list of non-empty glob strings (LINT-FM-40) + context:
# enum fork|main (LINT-FM-41). Both optional: absent fields produce nothing,
# so the pre-K1 corpus stays green (backward compatible).
LINT_SKILLS="$REPO_ROOT/.claude/scripts/lint-skills.py"
if [ -f "$LINT_SKILLS" ]; then
  echo "--- WS-C: SKILL.md description<=1024 + strict-YAML gate (PLAN-117) + K1 paths:/context: (PLAN-135) ---"
  set +e
  ws_c_out=$(python3 "$LINT_SKILLS" --quiet --strict-yaml --max-description=1024 \
    --only-rules=LINT-FM-04,LINT-FM-05,LINT-FM-40,LINT-FM-41 "$REPO_ROOT/.claude/skills" 2>&1)
  ws_c_rc=$?
  set -e
  if [ "$ws_c_rc" -ne 0 ]; then
    echo "$ws_c_out" | sed 's/^/  /'
    ws_c_n=$(printf '%s\n' "$ws_c_out" | grep -cE "LINT-FM-(0[45]|4[01])" || true)
    # Fail-CLOSED on linter infra error: a nonzero rc with no FM-04/05/40/41
    # lines means the linter itself crashed (argparse/IO/traceback) — count it
    # as >=1 so the gate goes red rather than silently passing (Codex 019e6b54 P1).
    if [ "$ws_c_n" -eq 0 ]; then
      ws_c_n=1
    fi
    ERRORS=$((ERRORS + ws_c_n))
  else
    echo "  OK: all SKILL.md descriptions <= 1024 chars + valid under strict YAML + K1 paths:/context: fields valid"
  fi
  echo ""
fi

# ---- 6-ter. PLAN-119 WS-A/C/E — test-harness audit-isolation gate ----
# Fail-CLOSED. Keeps the durable test/probe → LIVE-audit-log isolation from
# silently regressing: (a) the suite-wide redirect fixture stays registered in
# all three conftests; (b) the allow_live_audit_dir escape hatch stays at ZERO
# uses; (c) no test spawns a hook subprocess with a minimal env omitting the
# audit carriers. See docs/test-isolation.md + .claude/hooks/_lib/test_isolation.py.
#
# DOGFOOD-ONLY: this gate enforces the FRAMEWORK's own test-suite isolation. It
# is gated on the presence of the hooks TEST TREE — an INDEPENDENT dogfood shape,
# deliberately NOT the PLAN-119 artifact itself, so that deleting the isolation
# helper is REPORTED rather than silently skipping the whole gate (Codex
# pair-rail P1). Adopter installs / validate-governance FIXTURE trees ship no
# hooks test tree → skip (keeps test_plan_schema_enforcement green).
if [ -d "$REPO_ROOT/.claude/hooks/tests" ]; then
echo "--- PLAN-119 audit-isolation gate (WS-A/C/E) ---"
# The WS-A isolation helper MUST exist in a dogfood tree — its absence means the
# suite-wide audit-dir redirect is gone (do not silently skip).
if [ ! -f "$REPO_ROOT/.claude/hooks/_lib/test_isolation.py" ]; then
  echo "  FAIL: WS-A isolation helper .claude/hooks/_lib/test_isolation.py is MISSING in a dogfood tree (suite-wide audit-dir redirect removed)"
  ERRORS=$((ERRORS + 1))
fi
for cf in "conftest.py" ".claude/hooks/tests/conftest.py" ".claude/scripts/tests/conftest.py"; do
  if ! grep -q "_ceo_audit_isolation_session" "$REPO_ROOT/$cf" 2>/dev/null; then
    echo "  FAIL: $cf missing the WS-A audit-isolation fixture (_ceo_audit_isolation_session)"
    ERRORS=$((ERRORS + 1))
  fi
done
set +e
p119_allow_uses=$(grep -rnE "mark\.allow_live_audit_dir" \
  "$REPO_ROOT/.claude/hooks/tests" "$REPO_ROOT/.claude/scripts/tests" "$REPO_ROOT/tests" 2>/dev/null \
  | grep -vc "get_closest_marker")
set -e
p119_allow_uses=${p119_allow_uses:-0}
if [ "$p119_allow_uses" -ne 0 ]; then
  echo "  FAIL: $p119_allow_uses use(s) of @pytest.mark.allow_live_audit_dir (must be 0 at ship; CODEOWNERS security-engineer review required to add one)"
  ERRORS=$((ERRORS + p119_allow_uses))
fi
P119_ISO_CHECK="$REPO_ROOT/.claude/scripts/check-test-audit-isolation.py"
if [ -f "$P119_ISO_CHECK" ]; then
  set +e
  p119_iso_out=$(python3 "$P119_ISO_CHECK" 2>&1)
  p119_iso_rc=$?
  set -e
  if [ "$p119_iso_rc" -ne 0 ]; then
    echo "$p119_iso_out" | sed 's/^/  /'
    ERRORS=$((ERRORS + 1))
  else
    echo "  OK: fixtures present in 3 conftests; 0 escape-hatch uses; 0 unsafe subprocess spawns"
  fi
else
  echo "  WARN: check-test-audit-isolation.py missing (WS-C subprocess gate skipped)"
  WARNINGS=$((WARNINGS + 1))
fi
echo ""
fi  # end PLAN-119 dogfood-only audit-isolation gate

# ---- PLAN-138 Wave A: unresolved [NEEDS CLARIFICATION] marker advisory ----
# WARNING-ONLY (never touches ERRORS). Counts LIVE markers — the actionable
# colon-question-bracket form OUTSIDE fenced code + inline-backtick spans —
# across root-level plan files, excluding PLAN-SCHEMA.md (the definition
# file). Single source of truth: reuse check-staleness.py's
# `live_clarification_markers` so the code-span + PLAN-SCHEMA exclusion can
# never drift from the staleness detector. Fully fail-open: any error
# (missing helper, binary/garbage plan, bad UTF-8) degrades to zero markers
# and never crashes the validator (`2>/dev/null` + in-Python try/except).
if [ -d "$REPO_ROOT/.claude/plans" ]; then
  echo "--- PLAN-138 unresolved-clarification marker advisory ---"
  set +e
  p138_markers=$(CS_SCRIPT="$REPO_ROOT/.claude/scripts/check-staleness.py" \
    PLANS_DIR="$REPO_ROOT/.claude/plans" python3 - <<'PY' 2>/dev/null
import os, importlib.util
from pathlib import Path
total = 0
try:
    cs = os.environ["CS_SCRIPT"]
    plans = Path(os.environ["PLANS_DIR"])
    spec = importlib.util.spec_from_file_location("cs_markers", cs)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = mod.live_clarification_markers
    for pf in sorted(plans.glob("PLAN-*.md")):
        if pf.name == "PLAN-SCHEMA.md":
            continue
        try:
            text = pf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total += fn(text, is_definition_file=False)
except Exception:
    total = 0
print(total)
PY
)
  set -e
  # Strip to digits only; empty/garbage -> 0 (fail-open under set -u).
  p138_markers=$(printf '%s' "${p138_markers:-0}" | tr -cd '0-9')
  p138_markers=${p138_markers:-0}
  if [ "$p138_markers" -gt 0 ]; then
    echo "  WARN: $p138_markers LIVE [NEEDS CLARIFICATION] marker(s) in plan(s) — resolve via /spawn spec-clarify before reviewed (PLAN-SCHEMA §14)"
    WARNINGS=$((WARNINGS + p138_markers))
  else
    echo "  OK: no unresolved [NEEDS CLARIFICATION] markers"
  fi
  echo ""
fi
# ---- end PLAN-138 Wave A advisory ----

# ---- 7. Summary ----

echo "--- Summary ---"
echo "  Skills referenced: $(echo "$REFERENCED_SKILLS" | wc -w | tr -d ' ') / $TOTAL_SKILLS installed"
echo "  Errors:   $ERRORS"
echo "  Warnings: $WARNINGS"

if [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "FAIL: $ERRORS errors found. Fix before starting work."
  exit 1
else
  echo ""
  echo "PASS: Governance files validated."
  exit 0
fi
