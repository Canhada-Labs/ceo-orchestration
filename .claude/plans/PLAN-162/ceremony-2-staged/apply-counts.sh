#!/bin/bash
# apply-counts.sh — ceremony 2 derived-counts updater (PLAN-162 ceremony-2-staged)
#
# WHAT: bumps every ADR-count doc site 185 -> 187 on the POST-MERGE tree.
# WHEN: run AFTER (a) `git merge plan-165-draft` (docs already at 185/27,
#       adds .claude/adr/ADR-185-night-mode-posture-toggle.md) AND
#       (b) the two AMEND files were copied into .claude/adr/:
#         ADR-110-AMEND-2-rail-timeout-recalibration.md
#         ADR-164-AMEND-1-cache-partition-and-wall-deadline.md
#       Only then is disk truth 187 — the script refuses to run otherwise
#       (fail-closed sequencing guard).
# COMMANDS count (26 -> 27) is fully carried by the merge; this script only
#       VERIFIES the 12 command sites, it never edits them.
# IDEMPOTENT: every sed pattern targets the OLD literal in its exact count
#       context; a second run finds nothing to replace and the controls
#       still pass. Re-running after success is a no-op + green report.
# PORTABLE: bash 3.2 (no mapfile, no assoc arrays); BSD or GNU sed.
#
# Derivation mirrors of the authorities (measurement prints its inputs):
#   ADRs:     ls .claude/adr/ADR-*.md | wc -l        (verify-counts.sh:99)
#   commands: find .claude/commands -maxdepth 1 -name '*.md' | wc -l
#                                                     (verify-counts.sh:180-182)
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT="${1:-$(cd "$SCRIPT_DIR/../../../.." && pwd)}"
OLD_ADRS=185
# codex S292 r8 P1: o alvo NÃO pode ser um literal — quais ADRs entram
# depende de decisões do Owner tomadas DURANTE a cerimônia (AMEND-1 só se
# a Fase B landar; AMEND-2 só se a sonda der GO; ADR-186 só se o Owner
# decidir a política de deadline). Derive do DISCO, que é a autoridade —
# o guard de sequenciamento logo abaixo já exige que o disco seja a
# verdade antes de qualquer edit. Override explícito: NEW_ADRS=<n>.
NEW_ADRS="${NEW_ADRS:-$(ls "$ROOT"/.claude/adr/ADR-*.md 2>/dev/null | wc -l | tr -d ' ')}"
CMDS=27

# BSD sed needs `-i ''`; GNU sed needs `-i`.
if sed --version >/dev/null 2>&1; then SED_INPLACE=(sed -i); else SED_INPLACE=(sed -i ''); fi

echo "== apply-counts.sh: ADR doc sites ${OLD_ADRS} -> ${NEW_ADRS} =="
echo "repo root: $ROOT"

# ---------------------------------------------------------------------------
# 0. Sequencing guard: disk truth must already BE the target (fail-closed).
# ---------------------------------------------------------------------------
echo "-- inputs --"
DISK_ADRS=$(ls "$ROOT"/.claude/adr/ADR-*.md 2>/dev/null | wc -l | tr -d ' ')
DISK_CMDS=$(find "$ROOT/.claude/commands" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
echo "ls .claude/adr/ADR-*.md | wc -l              = $DISK_ADRS (need $NEW_ADRS)"
echo "find .claude/commands -maxdepth 1 -name *.md = $DISK_CMDS (need $CMDS)"
for must in \
  ".claude/adr/ADR-185-night-mode-posture-toggle.md" \
  ".claude/adr/ADR-110-AMEND-2-rail-timeout-recalibration.md" \
  ".claude/adr/ADR-164-AMEND-1-cache-partition-and-wall-deadline.md" \
  ".claude/commands/night-mode.md"; do
  if [ -f "$ROOT/$must" ]; then echo "present: $must"; else
    echo "ABORT: missing $must — run only after merge + AMEND copy." >&2; exit 2; fi
done
if [ "$DISK_ADRS" != "$NEW_ADRS" ] || [ "$DISK_CMDS" != "$CMDS" ]; then
  echo "ABORT: disk truth is $DISK_ADRS ADRs / $DISK_CMDS commands," >&2
  echo "       expected $NEW_ADRS / $CMDS. Wrong sequencing point." >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# 1. Site-by-site substitutions (post-merge tree: all sites read 185 or 187).
#    Patterns are anchored to the count CONTEXT so literal "ADR-185"
#    references are never touched.
# ---------------------------------------------------------------------------
sub() { # file, sed -E expression
  local f="$1" expr="$2"
  [ -f "$ROOT/$f" ] || { echo "ABORT: $f not found" >&2; exit 2; }
  "${SED_INPLACE[@]}" -E "$expr" "$ROOT/$f"
  echo "sed:  $f  s>>> $expr"
}

# CLAUDE.md:54 — "**185 ADRs** (architecture decision records..."
sub "CLAUDE.md"            "s/\*\*${OLD_ADRS} ADRs\*\*/**${NEW_ADRS} ADRs**/"
# README.md:59 table row + :186 verify-block comment
sub "README.md"            "s/^(\| Architecture decision records \| \*\*)${OLD_ADRS}(\*\* \|)/\1${NEW_ADRS}\2/"
sub "README.md"            "s/# ${OLD_ADRS} ADRs/# ${NEW_ADRS} ADRs/"
# README.pt-BR.md:57 table row + :166 verify-block comment
sub "README.pt-BR.md"      "s/^(\| Architecture decision records \| \*\*)${OLD_ADRS}(\*\* \|)/\1${NEW_ADRS}\2/"
sub "README.pt-BR.md"      "s/# ${OLD_ADRS} ADRs/# ${NEW_ADRS} ADRs/"
# docs/ARCHITECTURE.md:56 tree comment, :71 table row, :237 prose
sub "docs/ARCHITECTURE.md" "s/# ${OLD_ADRS} architecture decision records/# ${NEW_ADRS} architecture decision records/"
sub "docs/ARCHITECTURE.md" "s/^(\| ADRs +\| )${OLD_ADRS}( +\|)/\1${NEW_ADRS}\2/"
sub "docs/ARCHITECTURE.md" "s/\(${OLD_ADRS} to date\)/(${NEW_ADRS} to date)/"
# docs/FAQ.md:107 verify-block comment
sub "docs/FAQ.md"          "s/# ${OLD_ADRS} ADRs/# ${NEW_ADRS} ADRs/"
# docs/GUIA-COMPLETO.md:167 prose
sub "docs/GUIA-COMPLETO.md" "s/${OLD_ADRS} ADRs document/${NEW_ADRS} ADRs document/"
# npm/README.md:59 table row + :122 verify-block comment
sub "npm/README.md"        "s/^(\| Architecture decision records \| \*\*)${OLD_ADRS}(\*\* \|)/\1${NEW_ADRS}\2/"
sub "npm/README.md"        "s/# ${OLD_ADRS} ADRs/# ${NEW_ADRS} ADRs/"

# ---------------------------------------------------------------------------
# 2. Controls. (a) ZERO old sites remain; (b) EXACT new-site counts;
#    (c) EXACT command-site counts (merge-provided, untouched here).
# ---------------------------------------------------------------------------
fail=0
old_total=0

chk() { # file  ERE-pattern  expected  label
  local f="$1" pat="$2" exp="$3" label="$4" got
  got=$(grep -cE "$pat" "$ROOT/$f" || true)
  if [ "$got" -eq "$exp" ]; then
    echo "OK    $f: $label = $got"
  else
    echo "FAIL  $f: $label — expected $exp, got $got  (/$pat/)"
    fail=1
  fi
}

echo "-- control A: old ADR-count sites remaining (must ALL be 0) --"
OLD_RE="\*\*${OLD_ADRS} ADRs\*\*|# ${OLD_ADRS} ADRs|\| \*\*${OLD_ADRS}\*\* |# ${OLD_ADRS} architecture decision records|\(${OLD_ADRS} to date\)|${OLD_ADRS} ADRs document|^\| ADRs +\| ${OLD_ADRS} "
for f in CLAUDE.md README.md README.pt-BR.md docs/ARCHITECTURE.md docs/FAQ.md docs/GUIA-COMPLETO.md npm/README.md; do
  n=$(grep -cE "$OLD_RE" "$ROOT/$f" || true)
  old_total=$((old_total + n))
  echo "old-sites $f = $n"
done
if [ "$old_total" -eq 0 ]; then echo "OK    old ADR sites remaining = 0"; else
  echo "FAIL  old ADR sites remaining = $old_total (must be 0)"; fail=1; fi

echo "-- control B: new ADR-count sites (12 total) --"
chk "CLAUDE.md"             "\*\*${NEW_ADRS} ADRs\*\*"                                       1 "**187 ADRs** prose"
chk "README.md"             "^\| Architecture decision records \| \*\*${NEW_ADRS}\*\* \|"    1 "table row"
chk "README.md"             "# ${NEW_ADRS} ADRs"                                             1 "verify-block comment"
chk "README.pt-BR.md"       "^\| Architecture decision records \| \*\*${NEW_ADRS}\*\* \|"    1 "table row"
chk "README.pt-BR.md"       "# ${NEW_ADRS} ADRs"                                             1 "verify-block comment"
chk "docs/ARCHITECTURE.md"  "# ${NEW_ADRS} architecture decision records"                    1 "tree comment"
chk "docs/ARCHITECTURE.md"  "^\| ADRs +\| ${NEW_ADRS} "                                      1 "table row"
chk "docs/ARCHITECTURE.md"  "\(${NEW_ADRS} to date\)"                                        1 "prose (to date)"
chk "docs/FAQ.md"           "# ${NEW_ADRS} ADRs"                                             1 "verify-block comment"
chk "docs/GUIA-COMPLETO.md" "${NEW_ADRS} ADRs document"                                      1 "prose"
chk "npm/README.md"         "^\| Architecture decision records \| \*\*${NEW_ADRS}\*\* \|"    1 "table row"
chk "npm/README.md"         "# ${NEW_ADRS} ADRs"                                             1 "verify-block comment"

echo "-- control C: command-count sites at ${CMDS} (12 total, merge-provided) --"
chk "CLAUDE.md"                     "\*\*${CMDS} slash commands\*\*"          1 "prose"
chk "README.md"                     "^\| Slash commands \| \*\*${CMDS}\*\* \|" 1 "table row"
chk "README.md"                     "# ${CMDS} slash commands"                1 "verify-block comment"
chk "README.pt-BR.md"               "^\| Slash commands \| \*\*${CMDS}\*\* \|" 1 "table row"
chk "README.pt-BR.md"               "# ${CMDS} slash commands"                1 "verify-block comment"
chk "docs/ARCHITECTURE.md"          "# ${CMDS} slash commands"                1 "tree comment"
chk "docs/ARCHITECTURE.md"          "^\| Slash commands +\| ${CMDS} "         1 "table row"
chk "docs/ARCHITECTURE.md"          "\(${CMDS} of them"                       1 "prose (of them)"
chk "docs/FAQ.md"                   "# ${CMDS} slash commands"                1 "verify-block comment"
chk "docs/COMMAND-SKILL-HOOK-MAP.md" "^- Commands: ${CMDS}\$"                 1 "catalog totals"
chk "npm/README.md"                 "^\| Slash commands \| \*\*${CMDS}\*\* \|" 1 "table row"
chk "npm/README.md"                 "# ${CMDS} slash commands"                1 "verify-block comment"

echo "-- summary --"
if [ "$fail" -eq 0 ]; then
  echo "PASS: 0 old ADR sites remain; 12 ADR sites @ ${NEW_ADRS}; 12 command sites @ ${CMDS}."
  echo "Next gates to run before committing (same commit as the AMEND files):"
  echo "  bash .claude/scripts/local/verify-counts.sh --no-tests"
  echo "  python3 .claude/scripts/check-claude-md-claims.py"
  echo "  python3 -m pytest .claude/scripts/tests/test_verify_counts.py -q"
  exit 0
else
  echo "FAIL: controls above did not converge — do NOT commit."
  exit 1
fi
