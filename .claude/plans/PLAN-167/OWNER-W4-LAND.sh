#!/usr/bin/env bash
# =============================================================================
# PLAN-167 W4 — Owner land script.
#
# Run from the repo root, AFTER signing W4-approved.md:
#
#   bash .claude/plans/PLAN-167/OWNER-W4-LAND.sh            # apply + gates
#   bash .claude/plans/PLAN-167/OWNER-W4-LAND.sh --dry-run  # check only
#
# It applies, gates, and STOPS before the commit — the commit is yours to make
# (it needs your GPG key). The exact command is printed at the end.
#
# Preflight failures abort BEFORE anything is copied.
# =============================================================================
set -euo pipefail

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

PLAN_DIR=".claude/plans/PLAN-167"
STAGED="$PLAN_DIR/staged"
MANIFEST="$PLAN_DIR/staged-manifest.sha256"

# The path→destination table. Adding a file is ONE line here, and §3 fails if a
# staged file is missing from it — the S296 mirror script covered 2 of 4 files
# with no gate noticing, because the list was hand-written prose.
MAP="
_framework_manifest_set.sh|scripts/_framework_manifest_set.sh
install.sh|scripts/install.sh
upgrade.sh|scripts/upgrade.sh
test-ownership-verdict-unit.sh|scripts/tests/test-ownership-verdict-unit.sh
check-model-deprecations.py|.claude/scripts/check-model-deprecations.py
"

die() { echo "ABORT: $*" >&2; exit 1; }
ok()  { echo "  ok   $*"; }

echo "== §0 preflight =="
[ -f "scripts/install.sh" ] || die "run me from the repo root"
[ -d "$STAGED" ] || die "$STAGED not found (the pack is gitignored — restore it before landing)"

shasum -c "$MANIFEST" >/dev/null 2>&1 || die "staged manifest does not verify (run: shasum -c $MANIFEST)"
ok "staged manifest verifies from the repo root"

if [ -f "$PLAN_DIR/W4-approved.md.asc" ]; then
  gpg --verify "$PLAN_DIR/W4-approved.md.asc" "$PLAN_DIR/W4-approved.md" 2>/dev/null \
    || die "GPG signature does not verify"
  ANCHOR="$( grep -E '^Anchor-SHA:' "$PLAN_DIR/W4-approved.md" | awk '{print $2}' )"
  case "$ANCHOR" in
    *PLACEHOLDER*|"") die "Anchor-SHA is still the placeholder — pin it to HEAD before signing" ;;
  esac
  [ "$ANCHOR" = "$( git rev-parse HEAD )" ] || die "Anchor-SHA ($ANCHOR) != HEAD ($( git rev-parse HEAD ))"
  ok "signature verifies and the anchor matches HEAD"
else
  echo "  NOTE: W4-approved.md.asc absent — signature check skipped (dry-run posture)" >&2
  [ "$DRY_RUN" -eq 1 ] || die "refusing to apply without a signature; use --dry-run to rehearse"
fi

[ -z "$( git diff --cached --name-only )" ] || die "the index is not clean"
ok "index is clean"

# Every staged file must be in the table, and vice versa.
echo "== §1 staged ↔ table coverage =="
for f in "$STAGED"/*; do
  b="$( basename "$f" )"
  case "$b" in *.patch) continue ;; esac
  printf '%s' "$MAP" | grep -q "^$b|" || die "staged file NOT in the table: $b"
  ok "$b"
done
printf '%s' "$MAP" | while IFS='|' read -r src _; do
  [ -n "$src" ] || continue
  [ -f "$STAGED/$src" ] || die "table names a file that is not staged: $src"
done

if [ "$DRY_RUN" -eq 1 ]; then
  echo ""
  echo "DRY RUN — nothing was copied. Preflight and coverage both pass."
  exit 0
fi

echo "== §2 apply =="
printf '%s' "$MAP" | while IFS='|' read -r src dst; do
  [ -n "$src" ] || continue
  cp "$STAGED/$src" "$dst"
  echo "  applied: $dst"
done
chmod +x scripts/tests/test-ownership-verdict-unit.sh

echo "== §3 gates =="
bash -n scripts/install.sh && bash -n scripts/upgrade.sh && bash -n scripts/_framework_manifest_set.sh
ok "bash -n"
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -S warning scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh
  ok "shellcheck"
fi
python3 -c 'import ast;ast.parse(open(".claude/scripts/check-model-deprecations.py").read())'
ok "python syntax"

./scripts/tests/test-ownership-verdict-unit.sh --quiet || die "unit oracle failed (expected 60/60)"
ok "unit oracle 60/60"

echo ""
echo "  Now the e2e (~25 min, 62 real installs/upgrades)."
echo "  EXPECTED: 58 green / 4 red. The 4 reds are DELIBERATE and named in"
echo "  W4-approved-draft.md — two of them are defects in the TEST, not the"
echo "  product. An all-green run means the table changed: STOP and find out why."
echo ""
./scripts/tests/test-ownership-table.sh || true

echo "== §4 touched − scope =="
git status --porcelain | sed 's/^...//' | grep -v '^[[:space:]]*$' | sort > /tmp/p167-touched.txt
printf '%s' "$MAP" | while IFS='|' read -r _ dst; do [ -n "$dst" ] && echo "$dst"; done | sort > /tmp/p167-scope.txt
echo "  Outside this pack's scope (the PLAN-166 ceremony files are EXPECTED here):"
comm -23 /tmp/p167-touched.txt /tmp/p167-scope.txt | sed 's/^/    /'

cat <<'EOF'

== §5 commit — yours to run (needs your key) ==

  git add scripts/_framework_manifest_set.sh scripts/install.sh scripts/upgrade.sh \
          scripts/tests/test-ownership-verdict-unit.sh \
          .claude/scripts/check-model-deprecations.py
  git commit -S -m "feat(PLAN-167): ownership decision table — one function decides, callers execute"

Explicit adds only. NEVER `git add -A` — this tree carries another ceremony's
dirty canonical files.
EOF
