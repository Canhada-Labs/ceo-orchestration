#!/bin/bash
# generate-ceremony.sh — synthesize an Owner-GPG ceremony script from a
# plan-id + sentinel-scope + canonical-paths input. Codifies all S80+S81
# lessons as mechanical guards so future ceremonies don't reinvent them.
#
# PLAN-073 §2 deliverable. Replaces hand-writing OWNER-CEREMONY.sh from
# scratch each time.
#
# Usage:
#   bash .claude/scripts/local/generate-ceremony.sh \
#     --plan PLAN-NNN \
#     --round N \
#     --scope-file path/to/sentinel-scope.md \
#     --canonical-paths "path1,path2,path3" \
#     --output OWNER-CEREMONY.sh \
#     [--ignore "path-glob1,path-glob2"]
#
# Generator-level guards (fail-fast pre-emit):
#  G1. --canonical-paths each matches a _CANONICAL_GUARDS pattern in
#      check_canonical_edit.py. Misspelled paths or non-canonical paths
#      that don't actually need a sentinel are rejected.
#  G2. --scope-file exists AND lives under
#      .claude/plans/PLAN-NNN/architect/round-N/ AND is named approved.md
#      AND parses cleanly per check_canonical_edit.py::_sentinel_grants_path
#      (literal Scope: + Approved-By: + matching path declarations).
#  G3. --ignore globs don't match any of --canonical-paths (would mask
#      real edits inside the ceremony).
#  G4. Generated script is bash -n clean.
#  G5. PLAN-NNN dir exists at .claude/plans/PLAN-NNN/.
#  G6. Sentinel scope file declares EVERY canonical path the user passed.
#
# Generated ceremony's runtime guards (codified in the script body):
#  R1. GPG_TTY auto-setup + gpg-agent reload (S80 PINENTRY-timeout fix)
#  R2. SKIP_PREFLIGHT_PYTEST=1 retry-after-fail support (S80 lesson)
#  R3. Customizable dirty-filter via --ignore (S80 PLAN-074 race-safe)
#  R4. CLAUDE.md size pre-check before any amendment (S80 size-cap fix)
#  R5. Idempotent sentinel sign (skip if .asc already present)
#  R6. Atomic single-commit Block 5 with explicit-add (S81 lesson:
#      git add -A would bundle other-terminal drift like PLAN-074)
#  R7. Smoke gate Block 4 with kernel-override UNSET before pytest +
#      governance + targeted byte-identity tests when present
#  R8. Block 3 patches stub — user fills in patches between markers;
#      no silent assumptions about what to patch
#
# Exit codes:
#   0  success
#   1  generator-guard failure (G1-G6)
#   2  bash -n syntax error in generated output (G4)
#   3  user-error (missing flags, malformed input)

set -euo pipefail

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------

PLAN=""
ROUND=""
SCOPE_FILE=""
CANONICAL_PATHS=""
OUTPUT=""
IGNORE_GLOBS=""

usage() {
  cat <<USAGE
Usage:
  bash $0 \\
    --plan PLAN-NNN \\
    --round N \\
    --scope-file <path> \\
    --canonical-paths "path1,path2[,...]" \\
    --output <path> \\
    [--ignore "glob1,glob2"]

Required flags:
  --plan             PLAN-NNN identifier (e.g. PLAN-073)
  --round            integer round number (e.g. 2)
  --scope-file       path to sentinel approved.md (must live under
                     .claude/plans/PLAN-NNN/architect/round-N/)
  --canonical-paths  comma-separated list of canonical paths the
                     ceremony will patch (each must match a guard
                     pattern in check_canonical_edit.py)
  --output           where to write the generated ceremony script

Optional flags:
  --ignore           comma-separated extra path globs the dirty-filter
                     should tolerate (e.g. ".claude/plans/PLAN-074")

See PLAN-073 §2 for the full design.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --plan) PLAN="$2"; shift 2 ;;
    --round) ROUND="$2"; shift 2 ;;
    --scope-file) SCOPE_FILE="$2"; shift 2 ;;
    --canonical-paths) CANONICAL_PATHS="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --ignore) IGNORE_GLOBS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "FATAL: unknown flag: $1"; usage >&2; exit 3 ;;
  esac
done

if [ -z "$PLAN" ] || [ -z "$ROUND" ] || [ -z "$SCOPE_FILE" ] \
    || [ -z "$CANONICAL_PATHS" ] || [ -z "$OUTPUT" ]; then
  echo "FATAL: missing required flag(s)" >&2
  usage >&2
  exit 3
fi

# Validate PLAN format
if ! printf '%s' "$PLAN" | grep -qE '^PLAN-[0-9]{3}$'; then
  echo "FATAL: --plan must match 'PLAN-NNN' (3 zero-padded digits)" >&2
  exit 3
fi

# Validate ROUND is positive integer
if ! printf '%s' "$ROUND" | grep -qE '^[0-9]+$'; then
  echo "FATAL: --round must be a positive integer" >&2
  exit 3
fi

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

# -----------------------------------------------------------------------------
# Generator guard G5: PLAN-NNN dir exists
# -----------------------------------------------------------------------------
PLAN_DIR=".claude/plans/$PLAN"
# Glob expansion for the plan-file fallback (SC2144 — `[ -f glob ]` is broken).
# Use shopt-style nullglob via a for-loop check.
PLAN_FILE_FOUND=0
for candidate in .claude/plans/${PLAN}-*.md; do
  [ -f "$candidate" ] && PLAN_FILE_FOUND=1 && break
done
if [ ! -d "$PLAN_DIR" ] && [ "$PLAN_FILE_FOUND" -eq 0 ]; then
  echo "FATAL [G5]: PLAN-NNN dir or file not found at $PLAN_DIR or .claude/plans/${PLAN}-*.md" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Generator guard G2: sentinel-scope file location + format validation
# -----------------------------------------------------------------------------
if [ ! -f "$SCOPE_FILE" ]; then
  echo "FATAL [G2]: scope file not found at $SCOPE_FILE" >&2
  exit 1
fi

EXPECTED_DIR=".claude/plans/$PLAN/architect/round-$ROUND"
SCOPE_REL=$(python3 -c "import os,sys; print(os.path.relpath('$SCOPE_FILE', '$REPO_ROOT'))")
SCOPE_BASENAME=$(basename "$SCOPE_REL")

if [ "$SCOPE_BASENAME" != "approved.md" ]; then
  echo "FATAL [G2]: scope file basename must be 'approved.md' (got '$SCOPE_BASENAME')" >&2
  echo "       The canonical-edit guard discovers only files named approved.md." >&2
  exit 1
fi

if [[ "$SCOPE_REL" != "$EXPECTED_DIR/approved.md" ]]; then
  echo "FATAL [G2]: scope file must live at $EXPECTED_DIR/approved.md" >&2
  echo "       (got $SCOPE_REL — would not be discovered by _find_sentinels glob)" >&2
  exit 1
fi

# Parser-compat check via the actual hook code
PARSER_OK=$(python3 - <<PYEOF
import sys, os
from pathlib import Path
sys.path.insert(0, "$REPO_ROOT/.claude/hooks")
import check_canonical_edit as cc

text = Path("$SCOPE_FILE").read_text(encoding="utf-8")
appr = cc._APPROVED_BY_RE.search(text)
scope = cc._SCOPE_HEADER_RE.search(text)
if not appr:
    print("missing 'Approved-By: @user <token>' literal line")
    sys.exit(0)
if not scope:
    print("missing 'Scope:' literal line (markdown ## headings reject)")
    sys.exit(0)
print("OK")
PYEOF
)
if [ "$PARSER_OK" != "OK" ]; then
  echo "FATAL [G2]: scope file fails parser compatibility — $PARSER_OK" >&2
  echo "       See .claude/plans/PLAN-019/architect/round-2/approved.md as reference." >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Generator guard G1 + G6: canonical-paths each match _CANONICAL_GUARDS AND
# all are declared in the sentinel scope
# -----------------------------------------------------------------------------
IFS=',' read -r -a CANONICAL_ARR <<< "$CANONICAL_PATHS"

for cp in "${CANONICAL_ARR[@]}"; do
  cp_trim=$(printf '%s' "$cp" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  RESULT=$(python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT/.claude/hooks")
import check_canonical_edit as cc
print("YES" if cc._is_canonical("$cp_trim", __import__("pathlib").Path("$REPO_ROOT")) else "NO")
PYEOF
)
  if [ "$RESULT" != "YES" ]; then
    echo "FATAL [G1]: '$cp_trim' is NOT canonical (does not match any pattern in _CANONICAL_GUARDS)" >&2
    echo "       Either it doesn't need a ceremony OR the path is misspelled." >&2
    exit 1
  fi

  # G6: declared in scope
  if ! grep -qE "^[[:space:]]*-[[:space:]]*${cp_trim}([[:space:]]|$)" "$SCOPE_FILE"; then
    echo "FATAL [G6]: canonical path '$cp_trim' not declared under Scope: in $SCOPE_FILE" >&2
    echo "       The hook's _sentinel_grants_path will return False for this path." >&2
    exit 1
  fi
done

# -----------------------------------------------------------------------------
# Generator guard G3: --ignore globs don't shadow any canonical path
# -----------------------------------------------------------------------------
if [ -n "$IGNORE_GLOBS" ]; then
  IFS=',' read -r -a IGNORE_ARR <<< "$IGNORE_GLOBS"
  for ig in "${IGNORE_ARR[@]}"; do
    ig_trim=$(printf '%s' "$ig" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    for cp in "${CANONICAL_ARR[@]}"; do
      cp_trim=$(printf '%s' "$cp" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
      MATCH=$(python3 -c "
import fnmatch, sys
print('YES' if fnmatch.fnmatch('$cp_trim', '$ig_trim') else 'NO')
")
      if [ "$MATCH" = "YES" ]; then
        echo "FATAL [G3]: --ignore glob '$ig_trim' would shadow canonical path '$cp_trim'" >&2
        echo "       Dirty-filter must NEVER ignore the files the ceremony patches." >&2
        exit 1
      fi
    done
  done
fi

# -----------------------------------------------------------------------------
# All generator guards passed — emit the ceremony script
# -----------------------------------------------------------------------------

# Compose ignore-extension regex fragment (safe pipe-join after
# escaping fnmatch globs to grep-friendly literals; we only support
# directory-prefix globs like ".claude/plans/PLAN-074*").
IGNORE_RE_FRAG=""
if [ -n "$IGNORE_GLOBS" ]; then
  IFS=',' read -r -a IGNORE_ARR <<< "$IGNORE_GLOBS"
  for ig in "${IGNORE_ARR[@]}"; do
    ig_trim=$(printf '%s' "$ig" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
                                       -e 's/[].[^$+(){}|]/\\&/g' -e 's/\*/.*/g')
    IGNORE_RE_FRAG="${IGNORE_RE_FRAG}|\\?\\? ${ig_trim}"
  done
fi

CANONICAL_LIST_QUOTED=""
for cp in "${CANONICAL_ARR[@]}"; do
  cp_trim=$(printf '%s' "$cp" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  CANONICAL_LIST_QUOTED="${CANONICAL_LIST_QUOTED}  \"${cp_trim}\" \\
"
done

CEREMONY_SLUG=$(echo "${PLAN}-round-${ROUND}" | tr '[:upper:]' '[:lower:]')
SENTINEL_DIR_REL=".claude/plans/$PLAN/architect/round-$ROUND"

# Generate the ceremony script via heredoc with literal markers
cat > "$OUTPUT" <<CEREMONY_EOF
#!/bin/bash
# AUTO-GENERATED by .claude/scripts/local/generate-ceremony.sh
# Plan: $PLAN
# Round: $ROUND
# Generated at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
#
# Codifies S80+S81 ceremony lessons:
#   - GPG_TTY auto-setup + gpg-agent reload (PINENTRY timeout fix)
#   - SKIP_PREFLIGHT_PYTEST retry-after-GPG-fail support
#   - Configurable dirty-filter (parallel-terminal race-safe)
#   - CLAUDE.md size pre-check (40k cap with 200-byte headroom)
#   - Idempotent sentinel sign
#   - Block 4 smoke gate with CEO_KERNEL_OVERRIDE unset before pytest
#   - Atomic Block 5 commit with explicit-add (no -A bundling)
#   - Sentinel format compliance pre-validated by generator
#
# DO NOT hand-edit Block 3 patches without re-running the generator AND
# updating the sentinel scope + .asc signature accordingly.

set -euo pipefail

REPO_ROOT="\$(cd "\$(dirname "\$0")/../../.." && pwd)"
# Allow override for users running from a different cwd:
REPO_ROOT="\${REPO_ROOT_OVERRIDE:-\$REPO_ROOT}"
cd "\$REPO_ROOT"

# ============================================================
# GPG-agent setup (S80 PINENTRY-timeout fix)
# ============================================================
export GPG_TTY=\$(tty 2>/dev/null || echo "")
if [ -n "\$GPG_TTY" ] && [ "\$GPG_TTY" != "not a tty" ]; then
  echo "GPG_TTY set to: \$GPG_TTY"
  gpgconf --reload gpg-agent 2>/dev/null || true
else
  echo "WARNING: cannot determine TTY — gpg --pinentry-mode=loopback fallback"
  GPG_PINENTRY_FALLBACK="--pinentry-mode=loopback"
fi
GPG_PINENTRY_FALLBACK="\${GPG_PINENTRY_FALLBACK:-}"

SKIP_PREFLIGHT_PYTEST="\${SKIP_PREFLIGHT_PYTEST:-0}"

echo "============================================"
echo "$PLAN round-$ROUND ceremony (auto-generated)"
echo "============================================"
echo ""
echo "Working dir: \$(pwd)"
echo "Branch: \$(git branch --show-current)"
echo "HEAD: \$(git rev-parse --short HEAD)"
echo "GPG_TTY: \${GPG_TTY:-<unset>}"
echo "Skip pre-flight pytest: \$SKIP_PREFLIGHT_PYTEST"
echo ""

# ============================================================
# Block 1 — Pre-flight checks
# ============================================================
echo "Block 1 — Pre-flight checks"
echo "----------------------------"

# 1a. Working tree clean (allow npm/* + .claude/architect/ + custom ignores)
DIRTY=\$(git status --porcelain | grep -vE "^(\\?\\? npm/|.M npm/| M npm/| D npm/|\\?\\? \\.claude/architect/${IGNORE_RE_FRAG})" || true)
if [ -n "\$DIRTY" ]; then
  echo "FAIL: working tree has uncommitted changes outside ceremony-safe ignore list"
  echo "\$DIRTY"
  exit 1
fi
echo "  OK: working tree clean"

# 1b. Required canonical paths exist
for f in \\
$CANONICAL_LIST_QUOTED  "$SENTINEL_DIR_REL/approved.md"; do
  if [ ! -f "\$f" ]; then
    echo "FAIL: missing required path \$f"
    exit 1
  fi
done
echo "  OK: all canonical paths + sentinel scope present"

# 1c. CLAUDE.md size pre-check (S80 lesson — fail BEFORE patches if near cap)
PRE_SIZE=\$(wc -c < CLAUDE.md)
if [ "\$PRE_SIZE" -gt 39800 ]; then
  echo "FAIL: CLAUDE.md size \$PRE_SIZE > 39800 (need 200B headroom for amendments)"
  echo "      Compact CLAUDE.md before re-running ceremony."
  exit 1
fi
echo "  OK: CLAUDE.md pre-size \$PRE_SIZE ≤ 39800"

# 1d. Pre-ceremony pytest baseline (skippable on retry)
if [ "\$SKIP_PREFLIGHT_PYTEST" = "1" ]; then
  echo "  SKIP: pre-ceremony pytest (SKIP_PREFLIGHT_PYTEST=1)"
else
  echo "  Running pre-ceremony pytest (~6 min)..."
  PRE_RESULT=\$(CLAUDE_PROJECT_DIR="\$REPO_ROOT" python3 -m pytest -q 2>&1 | tail -1)
  echo "  \$PRE_RESULT"
  if echo "\$PRE_RESULT" | grep -qE "[0-9]+ failed"; then
    echo "FAIL: pre-ceremony pytest has failures — abort"
    exit 1
  fi
  echo "  OK: pre-ceremony pytest baseline green"
fi

# ============================================================
# Block 2 — Sentinel sign (Owner GPG passphrase)
# ============================================================
echo ""
echo "Block 2 — Sentinel sign"
echo "------------------------"
echo "Owner GPG passphrase will be requested NOW (or used from agent cache)."
echo ""

SENTINEL_DIR="$SENTINEL_DIR_REL"
SENTINEL_FILE="\$SENTINEL_DIR/approved.md"
SIGNATURE="\$SENTINEL_DIR/approved.md.asc"

# Read Owner key fingerprint from .claude/sentinel-signers.txt (first uncommented entry)
GPG_KEY=\$(grep -vE '^\\s*(#|\$)' .claude/sentinel-signers.txt | head -1 | awk '{print \$1}')
if [ -z "\$GPG_KEY" ]; then
  echo "FAIL: cannot determine Owner GPG key from .claude/sentinel-signers.txt"
  exit 1
fi
echo "  Owner GPG key: \$GPG_KEY"

# Idempotent: skip sign if .asc is non-empty + verify-clean
if [ -f "\$SIGNATURE" ] && [ "\$(wc -c < "\$SIGNATURE" | tr -d '[:space:]')" -gt 100 ] \\
   && gpg --verify "\$SIGNATURE" "\$SENTINEL_FILE" >/dev/null 2>&1; then
  echo "  SKIP: \$SIGNATURE already signed + verifies clean"
else
  echo "  GPG passphrase prompt expected on TTY: \${GPG_TTY:-<loopback>}"
  gpg --batch --yes \\
      \$GPG_PINENTRY_FALLBACK \\
      --local-user "\$GPG_KEY" \\
      --armor --detach-sign \\
      --output "\$SIGNATURE" \\
      "\$SENTINEL_FILE"
fi

if [ ! -f "\$SIGNATURE" ] || [ "\$(wc -c < "\$SIGNATURE" | tr -d '[:space:]')" -lt 100 ]; then
  echo "FAIL: sentinel signature missing or empty"
  exit 1
fi
echo "  OK: sentinel signed at \$SIGNATURE"

# ============================================================
# Block 3 — Apply canonical patches
# ============================================================
echo ""
echo "Block 3 — Apply canonical patches"
echo "----------------------------------"

export CEO_KERNEL_OVERRIDE=1

# >>>>> CEREMONY-PATCHES-BEGIN >>>>>
# Fill in patches between the BEGIN/END markers below. Each canonical
# path declared in --canonical-paths should have a corresponding patch
# step. Patterns:
#   - Python heredoc exact-replace (preferred — see PLAN-072 OWNER-CEREMONY.sh
#     for canonical examples; uses find-and-replace via str.replace with
#     fail-CLOSED on missing anchor).
#   - 'git mv <src> <dst>' for canonical file moves.
#   - 'cp staging/path canonical/path' for promote-from-staging flows.
#
# Canonical paths to patch (declared in --canonical-paths):
$(for cp in "${CANONICAL_ARR[@]}"; do
  cp_trim=$(printf '%s' "$cp" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  echo "#   - $cp_trim"
done)

echo "  TODO: fill in Block 3 patches between BEGIN/END markers"
echo "  Generated ceremony will exit 1 here until patches are filled in."
exit 1

# <<<<< CEREMONY-PATCHES-END <<<<<

# ============================================================
# Block 4 — Intra-ceremony smoke gate (UNSET kernel override)
# ============================================================
echo ""
echo "Block 4 — Intra-ceremony smoke gate"
echo "------------------------------------"

unset CEO_KERNEL_OVERRIDE

# 4a. Python AST + YAML + JSON syntax sanity on patched canonical paths
for f in \\
$CANONICAL_LIST_QUOTED  "/dev/null"; do
  case "\$f" in
    /dev/null) continue ;;
    *.py)   python3 -c "import ast; ast.parse(open('\$f').read())" ;;
    *.yml|*.yaml) python3 -c "import yaml; yaml.safe_load(open('\$f'))" ;;
    *.json) python3 -c "import json; json.load(open('\$f'))" ;;
    *) ;;  # markdown/sh — skip programmatic syntax check
  esac
done
echo "  OK: AST/YAML/JSON syntax clean on patched canonical paths"

# 4b. actionlint (advisory if not installed)
if ls .github/workflows/*.yml >/dev/null 2>&1 && command -v actionlint >/dev/null 2>&1; then
  for wf in .github/workflows/*.yml; do
    actionlint "\$wf" || true
  done
  echo "  OK: actionlint advisory pass"
fi

# 4c. Full pytest re-run
echo "  Running full pytest..."
POST=\$(CLAUDE_PROJECT_DIR="\$REPO_ROOT" python3 -m pytest -q 2>&1 | tail -1)
echo "  \$POST"
if echo "\$POST" | grep -qE "[0-9]+ failed"; then
  echo "FAIL: post-patch pytest failed"
  exit 1
fi
echo "  OK: post-patch pytest green"

# 4d. validate-governance
echo "  Running validate-governance..."
bash .claude/scripts/validate-governance.sh > /tmp/$CEREMONY_SLUG-validate.log 2>&1 || true
echo "  validate-governance log: /tmp/$CEREMONY_SLUG-validate.log"

# 4e. CLAUDE.md size post-check
POST_SIZE=\$(wc -c < CLAUDE.md)
if [ "\$POST_SIZE" -gt 40000 ]; then
  echo "FAIL: CLAUDE.md size \$POST_SIZE > 40000 cap (compact required)"
  exit 1
fi
echo "  OK: CLAUDE.md size \$POST_SIZE ≤ 40000"

echo ""
echo "Block 4 smoke gate: ALL PASS"

# ============================================================
# Block 5 — Atomic commit (explicit-add to avoid foreign drift)
# ============================================================
echo ""
echo "Block 5 — Atomic commit"
echo "-----------------------"

# Explicit-add — only the canonical paths + sentinel + signature
git add \\
$CANONICAL_LIST_QUOTED  "\$SENTINEL_DIR/approved.md" \\
  "\$SENTINEL_DIR/approved.md.asc"

# Plus any non-canonical extras the user committed via Block 3 (e.g. tests,
# CHANGELOG, VERSION, npm/package.json) — uncomment + add as needed:
#   git add CHANGELOG.md VERSION npm/package.json

git status --short

git commit -m "ceremony($PLAN): round-$ROUND auto-generated

Auto-generated ceremony for $PLAN round-$ROUND. Sentinel signed at
$SENTINEL_DIR_REL/approved.md.asc.

Canonical paths patched:
$(for cp in "${CANONICAL_ARR[@]}"; do
  cp_trim=$(printf '%s' "$cp" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  echo "  - $cp_trim"
done)

Generated by .claude/scripts/local/generate-ceremony.sh

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"

echo ""
echo "============================================"
echo "$PLAN round-$ROUND ceremony complete"
echo "Commit: \$(git rev-parse --short HEAD)"
echo "============================================"
CEREMONY_EOF

chmod +x "$OUTPUT"

# -----------------------------------------------------------------------------
# Generator guard G4: bash -n syntax check on emitted output
# -----------------------------------------------------------------------------
if ! bash -n "$OUTPUT" 2>/dev/null; then
  echo "FATAL [G4]: generated script has bash syntax errors:" >&2
  bash -n "$OUTPUT" >&2 || true
  exit 2
fi

echo "OK: ceremony script generated at $OUTPUT"
echo "OK: bash -n syntax check passed"
echo ""
echo "Next steps:"
echo "  1. Open $OUTPUT and fill in Block 3 patches between"
echo "     CEREMONY-PATCHES-BEGIN / CEREMONY-PATCHES-END markers."
echo "  2. Re-run bash -n $OUTPUT to confirm syntax stays clean."
echo "  3. Owner runs: bash $OUTPUT"
