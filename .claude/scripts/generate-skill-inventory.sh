#!/bin/bash
# generate-skill-inventory.sh — emits a Markdown inventory of all skills across tiers.
#
# Reads each skill's frontmatter (`name`, `description`) and outputs a structured
# inventory grouped by tier: core, frontend, domains/<domain>.
#
# Used by:
#   - Item 1 of PLAN-001 Sprint 1: populates the auto-generated block inside
#     .claude/skills/core/ceo-orchestration/SKILL.md
#   - CI (Sprint 2+): idempotency check — generated block must match committed block
#
# Usage:
#   bash .claude/scripts/generate-skill-inventory.sh          # to stdout
#   bash .claude/scripts/generate-skill-inventory.sh --check  # idempotency check
#
# No arguments = generate and emit to stdout.
# --check mode (PLAN-019 VP-F7): regenerates the auto-generated block
# and diffs it against the current
#   `.claude/skills/core/ceo-orchestration/SKILL.md`
# block between `<!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->` and
# `<!-- END AUTO-GENERATED SKILL INVENTORY -->`. Exits 0 if identical,
# 1 if drift (stderr shows the diff). CI wires this as an advisory gate.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SKILLS_DIR="$REPO_ROOT/.claude/skills"

# Arg parse. `--check` toggles the idempotency verify mode; anything else is
# a usage error (the script has no other options).
MODE="emit"
while [ $# -gt 0 ]; do
  case "$1" in
    --check)
      MODE="check"; shift ;;
    -h|--help)
      sed -n '1,20p' "$0"; exit 0 ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      echo "Usage: $0 [--check]" >&2
      exit 2 ;;
  esac
done

# Extract a single field from YAML frontmatter (handles multi-line values)
# Usage: extract_frontmatter_field <file> <field_name>
extract_frontmatter_field() {
  local file="$1"
  local field="$2"
  python3 - "$file" "$field" <<'PY'
import sys, re
path, field = sys.argv[1], sys.argv[2]
with open(path) as fh:
    content = fh.read()
m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
if not m:
    sys.exit(0)
fm = m.group(1)
# Match `field: value` where value may continue on indented lines (YAML folded)
pattern = rf'^{re.escape(field)}:\s*(.*?)(?=^\w[\w_-]*:|\Z)'
dm = re.search(pattern, fm, re.DOTALL | re.MULTILINE)
if dm:
    # Collapse whitespace
    value = ' '.join(dm.group(1).split())
    print(value)
PY
}

# Extract the first sentence (or first 180 chars) from a description
# Usage: first_sentence "<long description>"
first_sentence() {
  local text="$1"
  # Find first `. ` (period+space) or truncate to 180 chars with ellipsis
  python3 - "$text" <<'PY'
import sys
text = sys.argv[1]
# First sentence up to ". " (period followed by space)
for i, ch in enumerate(text):
    if ch == '.' and i + 1 < len(text) and text[i+1] == ' ':
        print(text[:i+1])
        sys.exit(0)
# No sentence terminator — truncate
if len(text) > 180:
    print(text[:177] + '...')
else:
    print(text)
PY
}

# Emit inventory for a single tier (core, frontend, or a domain)
# Usage: emit_tier <tier-label> <tier-glob>
emit_tier() {
  local label="$1"
  local glob="$2"
  local count=0
  local paths
  # Collect paths, sorted. The `|| true` guards against `set -o pipefail`
  # when the glob matches nothing (e.g. a freshly-created domain with
  # no skills yet, as ships in PLAN-033's `community/` seed) — ls exits
  # 1 on no-match which would otherwise kill the whole script.
  paths=$({ ls -d $glob 2>/dev/null || true; } | sort)
  [ -z "$paths" ] && return 0

  echo "### $label"
  echo ""

  while IFS= read -r skill_dir; do
    [ -d "$skill_dir" ] || continue
    local skill_file="$skill_dir/SKILL.md"
    # Fallback for legacy naming (some skills use SKILL-frontend.md only)
    if [ ! -f "$skill_file" ] && [ -f "$skill_dir/SKILL-frontend.md" ]; then
      skill_file="$skill_dir/SKILL-frontend.md"
    fi
    [ -f "$skill_file" ] || continue
    local name
    local desc
    name=$(basename "$skill_dir")
    desc=$(extract_frontmatter_field "$skill_file" "description" || echo "")
    if [ -z "$desc" ]; then
      desc="(no description in frontmatter)"
    fi
    local hook
    hook=$(first_sentence "$desc")
    echo "- \`$name\` — $hook"
    count=$((count + 1))
  done <<< "$paths"

  echo ""
  echo "_Total in ${label}: ${count} skill(s)._"
  echo ""
}

# --- Main ---

emit_inventory() {
  echo "<!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->"
  echo "<!-- Source: bash .claude/scripts/generate-skill-inventory.sh -->"
  echo "<!-- Regenerate after adding/removing skills. CI will diff in Sprint 2+. -->"
  echo ""

  emit_tier "Core (universal)" "$SKILLS_DIR/core/*"
  emit_tier "Frontend (universal)" "$SKILLS_DIR/frontend/*"

  # Domains — one section per installed domain
  for domain_dir in "$SKILLS_DIR/domains/"*/; do
    [ -d "$domain_dir" ] || continue
    domain_name=$(basename "$domain_dir")
    emit_tier "Domain: $domain_name" "${domain_dir}skills/*"
  done

  echo "<!-- END AUTO-GENERATED SKILL INVENTORY -->"
}

# --check mode: extract current block from ceo-orchestration SKILL.md,
# regenerate in a tempfile, and diff. Exit 1 if they differ.
SKILL_MD="$REPO_ROOT/.claude/skills/core/ceo-orchestration/SKILL.md"
BEGIN_MARK='<!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->'
END_MARK='<!-- END AUTO-GENERATED SKILL INVENTORY -->'

if [ "$MODE" = "check" ]; then
  if [ ! -f "$SKILL_MD" ]; then
    echo "ERROR: SKILL.md not found at $SKILL_MD" >&2
    exit 2
  fi
  tmp_gen="$(mktemp)"
  tmp_cur="$(mktemp)"
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_gen' '$tmp_cur'" EXIT
  emit_inventory > "$tmp_gen"
  # Extract current committed block (inclusive of BEGIN/END markers).
  awk -v b="$BEGIN_MARK" -v e="$END_MARK" '
    $0 == b {printing=1}
    printing {print}
    $0 == e {printing=0}
  ' "$SKILL_MD" > "$tmp_cur"
  if [ ! -s "$tmp_cur" ]; then
    echo "ERROR: BEGIN/END AUTO-GENERATED markers not found in $SKILL_MD" >&2
    exit 2
  fi
  if diff -u "$tmp_cur" "$tmp_gen" >/tmp/.skill-inventory-check.$$ 2>&1; then
    rm -f /tmp/.skill-inventory-check.$$
    echo "PASS: skill inventory is up to date"
    exit 0
  fi
  echo "FAIL: skill inventory drifted. Re-run:" >&2
  echo "      bash $0 > <paste into $SKILL_MD between BEGIN/END markers>" >&2
  cat /tmp/.skill-inventory-check.$$ >&2
  rm -f /tmp/.skill-inventory-check.$$
  exit 1
fi

# Default mode: emit to stdout.
emit_inventory
