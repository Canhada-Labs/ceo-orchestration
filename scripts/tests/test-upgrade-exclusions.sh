#!/usr/bin/env bash
# scripts/tests/test-upgrade-exclusions.sh
# PLAN-161 W1a (U2/U3 oracle) — upgrade.sh must honor the install.sh
# framework-internal exclusion set, on BOTH adopter shapes, and purge
# mis-installed excluded-tree files ONLY under the opt-in --purge-misinstalled
# flag (hash-gated, backed up, symlink-safe, second-run no-op).
#
# EXPECTED-RED on HEAD (PLAN-161 context item 2b, found live in the 2026-07-21
# adopter upgrade): the union walk (upgrade.sh:888-891 + ADD branch :904-908),
# the legacy no-manifest cp -R branch (:1046-1058) and the manifest writer
# (_framework_manifest_files, _framework_manifest_set.sh:129-134) all ignore
# the exclusion set — the upgrade installs the dogfood test trees (~967 files)
# into the adopter and RE-ADDS them after the adopter deletes.
#
# Markers (PLAN-161 W1 check, codex r5 F2 + r6 F1):
#   REPRO-CONFIRMED  = the seeded HEAD bug reproduced (excluded tree installed
#                      and/or manifest-recorded by the upgrade)
#   SCAFFOLD-ERROR   = the fixture itself broke (never a verdict on the bug)
#
# The U3 purge assertions (E.3) are the STAGED-ORACLE contract for the new
# opt-in flag: plain FAILs on HEAD (feature absent — no marker), green only
# once the W2 pack lands. Staged-oracle hook: UPGRADE_SOURCE_DIR points at a
# patched framework checkout. E.2b (W2 fix-3, codex r3 F11b) is likewise a
# staged-oracle contract: it PROVES adopter-owned excluded-tree content —
# regular files AND symlinks (targets untouched, F11a) — survives a plain
# legacy upgrade; RED on HEAD (wholesale find -delete destroys the seeds).
# E.3d (W2 fix-5, codex r5 U3) folds the r4 F2 ancestor-symlink purge
# regression into the tracked oracle: an excluded-tree ANCESTOR that is an
# adopter symlink must never be walked by the purge scan nor swept by its
# rmdir pass — see the leg's own comment for the full regression shape.
#
# bash 3.2-safe. Run: bash scripts/tests/test-upgrade-exclusions.sh; echo rc=$?

set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="${UPGRADE_SOURCE_DIR:-$( cd "$SCRIPT_DIR/../.." && pwd )}"

export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-p161-excl-XXXXXX )" \
  || { printf 'SCAFFOLD-ERROR: mktemp WORKROOT failed\n' >&2; exit 2; }
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

ok()       { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()      { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }
scaffold() { printf 'SCAFFOLD-ERROR: %s\n' "$1" >&2; exit 2; }

_git_init_retry() {
  local d="$1" n=0
  while [ "$n" -lt 5 ]; do
    if ( cd "$d" && git init -q 2>/dev/null ); then return 0; fi
    n=$((n+1)); sleep 1
  done
  ( cd "$d" && git init -q )
}

fresh_install() {
  local t
  t="$( mktemp -d "$WORKROOT/tgt-XXXXXX" )" || return 1
  _git_init_retry "$t"
  if ! bash "$SOURCE_DIR/scripts/install.sh" "$t" --profile core \
       > "$t.install.log" 2>&1; then
    tail -30 "$t.install.log" >&2
    return 1
  fi
  printf '%s\n' "$t"
}

# The install.sh framework-internal exclusion set (CF-7): dirs + files that a
# fresh install NEVER ships and an upgrade must therefore never (re)install.
EXCLUDED_PROBES=".claude/hooks/tests
.claude/hooks/legacy
.claude/scripts/tests
.claude/hooks/_lib/tests
.claude/hooks/_lib/test_isolation.py
.claude/hooks/_lib/testing.py"

echo "==> E.0 — fixture premise: excluded trees exist in the framework SOURCE"
[ -d "$SOURCE_DIR/.claude/hooks/tests" ] \
  || scaffold "framework source lacks .claude/hooks/tests (premise gone)"
ACTIVE_PROBES=""
while IFS= read -r p; do
  [ -n "$p" ] || continue
  if [ -e "$SOURCE_DIR/$p" ]; then
    ACTIVE_PROBES="$ACTIVE_PROBES $p"
  else
    printf '  note: probe %s absent in source — skipped\n' "$p"
  fi
done <<EOF
$EXCLUDED_PROBES
EOF

# Assert every active excluded probe is absent from target + manifest.
# $1 = target dir, $2 = section label, $3 = repro flag (1 => REPRO-CONFIRMED)
assert_excluded_absent() {
  local t="$1" label="$2" repro="$3" p hit=0 man="$1/.claude/.install-manifest.sha256"
  for p in $ACTIVE_PROBES; do
    if [ -e "$t/$p" ]; then
      bad "$label excluded path INSTALLED by upgrade: $p"
      hit=1
    else
      ok "$label excluded path not installed: $p"
    fi
    if [ -f "$man" ] && grep -q "  $p" "$man"; then
      bad "$label excluded path RECORDED in the rewritten manifest: $p"
      hit=1
    else
      ok "$label excluded path not manifest-recorded: $p"
    fi
  done
  if [ "$hit" -eq 1 ] && [ "$repro" -eq 1 ]; then
    echo "REPRO-CONFIRMED: upgrade.sh (re)installed and/or manifest-recorded framework-internal excluded trees (PLAN-161 U2 bug 2b — union walk / cp -R / manifest writer)"
  fi
}

echo "==> E.1 — manifest-BEARING adopter: upgrade honors the exclusion set"
T1="$( fresh_install )" || scaffold "E.1 install failed"
for p in $ACTIVE_PROBES; do
  [ -e "$T1/$p" ] && scaffold "E.1 premise broken: install itself shipped $p"
done
if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T1" --profile core \
     > "$WORKROOT/e1-upgrade.log" 2>&1; then
  ok "E.1 upgrade returned 0"
else
  bad "E.1 upgrade failed (see $WORKROOT/e1-upgrade.log)"
  tail -20 "$WORKROOT/e1-upgrade.log" >&2
fi
assert_excluded_absent "$T1" "E.1" 1

echo "==> E.2 — manifest-LESS adopter (legacy cp -R branch, CF-7)"
T2="$( fresh_install )" || scaffold "E.2 install failed"
rm -f "$T2/.claude/.install-manifest.sha256"
if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T2" --profile core \
     > "$WORKROOT/e2-upgrade.log" 2>&1; then
  ok "E.2 upgrade returned 0"
else
  bad "E.2 upgrade failed (see $WORKROOT/e2-upgrade.log)"
  tail -20 "$WORKROOT/e2-upgrade.log" >&2
fi
assert_excluded_absent "$T2" "E.2" 1

echo "==> E.2b — manifest-LESS adopter: pre-existing excluded content SURVIVES a plain upgrade (W2 F11/F11a survivor guarantee)"
# A SECOND manifest-less adopter: seeding survivors into T2 itself would void
# E.2's absence assertions (survivors legitimately keep the excluded tree
# present). This leg proves the F11 contract a plain legacy upgrade (NO flag)
# must honor: adopter-owned excluded-tree content stays byte-identical —
# including symlinks, whose targets must NEVER be touched (F11a: never test
# or delete THROUGH a symlinked dir into adopter data outside the tree).
T2B="$( fresh_install )" || scaffold "E.2b install failed"
rm -f "$T2B/.claude/.install-manifest.sha256"
mkdir -p "$T2B/.claude/hooks/tests" || scaffold "E.2b seed mkdir failed"

# (i) adopter-owned regular file inside an excluded tree (matches nothing)
KEEP2B_REL=".claude/hooks/tests/adopter_keep_p161.py"
printf '# adopter-owned survivor probe p161 — content matches no framework file\n' \
  > "$T2B/$KEEP2B_REL"
cp "$T2B/$KEEP2B_REL" "$WORKROOT/e2b-keep.ref" || scaffold "E.2b keep ref failed"

# (ii) symlink inside the excluded tree -> adopter file OUTSIDE it
LINK2B_TARGET="$T2B/adopter-e2b-link-target.txt"
printf 'e2b sentinel: adopter content behind excluded-tree symlink\n' \
  > "$LINK2B_TARGET"
LINK2B_REL=".claude/hooks/tests/adopter_link_p161.txt"
ln -s ../../../adopter-e2b-link-target.txt "$T2B/$LINK2B_REL" \
  || scaffold "E.2b seed file-symlink failed"

# (iii) F11a probe: a symlinked DIRECTORY at an excluded relpath that SHADOWS
# real excluded source content, pointing OUTSIDE the target tree; the outside
# dir holds a file at the same tail relpath as an excluded source file. An
# unguarded prune resolves dst tests THROUGH the link and deletes the outside
# file; a guarded upgrade must leave link + target byte-identical.
SUBD_ABS="$( find "$SOURCE_DIR/.claude/hooks/tests" -mindepth 1 -maxdepth 1 \
  -type d ! -name '__pycache__' 2>/dev/null | LC_ALL=C sort | head -1 )"
DIRLINK_REL=""; SHADOW_OUT=""; SHADOW_SRC=""
if [ -n "$SUBD_ABS" ]; then
  SHADOW_SRC="$( find "$SUBD_ABS" -type f ! -name '*.pyc' 2>/dev/null \
    | LC_ALL=C sort | head -1 )"
fi
if [ -n "$SHADOW_SRC" ]; then
  SUBD_NAME="$( basename "$SUBD_ABS" )"
  SHADOW_TAIL="${SHADOW_SRC#"$SUBD_ABS"/}"
  OUTSIDE_DIR="$WORKROOT/e2b-outside-tree"
  mkdir -p "$OUTSIDE_DIR/$( dirname "$SHADOW_TAIL" )" \
    || scaffold "E.2b outside mkdir failed"
  SHADOW_OUT="$OUTSIDE_DIR/$SHADOW_TAIL"
  printf 'e2b sentinel: OUTSIDE-tree adopter data shadowing %s\n' "$SHADOW_TAIL" \
    > "$SHADOW_OUT"
  cp "$SHADOW_OUT" "$WORKROOT/e2b-shadow.ref" || scaffold "E.2b shadow ref failed"
  DIRLINK_REL=".claude/hooks/tests/$SUBD_NAME"
  ln -s "$OUTSIDE_DIR" "$T2B/$DIRLINK_REL" \
    || scaffold "E.2b seed dir-symlink failed"
else
  printf '  note: no shadowable subdir under source .claude/hooks/tests — dir-symlink probe skipped\n'
fi

if bash "$SOURCE_DIR/scripts/upgrade.sh" "$T2B" --profile core \
     > "$WORKROOT/e2b-upgrade.log" 2>&1; then
  ok "E.2b upgrade returned 0"
else
  bad "E.2b upgrade failed (see $WORKROOT/e2b-upgrade.log)"
  tail -20 "$WORKROOT/e2b-upgrade.log" >&2
fi
if [ -f "$T2B/$KEEP2B_REL" ] && cmp -s "$T2B/$KEEP2B_REL" "$WORKROOT/e2b-keep.ref"; then
  ok "E.2b adopter file in excluded tree survived byte-identical: $KEEP2B_REL"
else
  bad "E.2b adopter file in excluded tree LOST/ALTERED by plain upgrade: $KEEP2B_REL"
fi
if [ -L "$T2B/$LINK2B_REL" ] \
   && [ "$( readlink "$T2B/$LINK2B_REL" )" = "../../../adopter-e2b-link-target.txt" ]; then
  ok "E.2b excluded-tree symlink survived unchanged: $LINK2B_REL"
else
  bad "E.2b excluded-tree symlink LOST/REWRITTEN by plain upgrade: $LINK2B_REL"
fi
if [ -f "$LINK2B_TARGET" ] && cmp -s "$LINK2B_TARGET" /dev/null; then
  bad "E.2b symlink target EMPTIED by plain upgrade"
elif [ -f "$LINK2B_TARGET" ] \
   && grep -q 'e2b sentinel: adopter content behind excluded-tree symlink' "$LINK2B_TARGET"; then
  ok "E.2b symlink target content untouched"
else
  bad "E.2b symlink TARGET damaged by plain upgrade"
fi
if [ -n "$DIRLINK_REL" ]; then
  if [ -L "$T2B/$DIRLINK_REL" ] \
     && [ "$( readlink "$T2B/$DIRLINK_REL" )" = "$OUTSIDE_DIR" ]; then
    ok "E.2b symlinked DIR at excluded relpath survived: $DIRLINK_REL"
  else
    bad "E.2b symlinked DIR at excluded relpath LOST/REWRITTEN: $DIRLINK_REL"
  fi
  if [ -f "$SHADOW_OUT" ] && cmp -s "$SHADOW_OUT" "$WORKROOT/e2b-shadow.ref"; then
    ok "E.2b OUTSIDE-tree file behind dir-symlink untouched (F11a no delete-through)"
  else
    bad "E.2b OUTSIDE-tree file behind dir-symlink DELETED/ALTERED (F11a: prune followed the link)"
  fi
fi

echo "==> E.3 — opt-in hash-gated purge matrix (U3 staged-oracle contract)"
T3="$( fresh_install )" || scaffold "E.3 install failed"
# Seed the fixture matrix inside excluded trees:
#   misA/misB — bytes == current framework source at the SAME relpath
#               => hash-AUTHORIZED for purge
#   keepC     — adopter-custom content, matches nothing        => keep + warn
#   keepD     — byte-identical to a source file but at the WRONG relpath
#               (outside the provenance rails)                 => keep + warn
#   linkE     — symlink inside an excluded tree                => warn-and-skip
MISA_SRC="$( find "$SOURCE_DIR/.claude/hooks/tests" -maxdepth 1 -type f -name 'test_*.py' 2>/dev/null | LC_ALL=C sort | head -1 )"
[ -n "$MISA_SRC" ] || scaffold "E.3 no source hooks test to seed misA"
MISA_REL=".claude/hooks/tests/$( basename "$MISA_SRC" )"
mkdir -p "$T3/.claude/hooks/tests" || scaffold "E.3 seed mkdir failed"
cp "$MISA_SRC" "$T3/$MISA_REL" || scaffold "E.3 seed misA cp failed"

MISB_SRC="$( find "$SOURCE_DIR/.claude/scripts/tests" -maxdepth 1 -type f -name 'test_*.py' 2>/dev/null | LC_ALL=C sort | head -1 )"
MISB_REL=""
if [ -n "$MISB_SRC" ]; then
  MISB_REL=".claude/scripts/tests/$( basename "$MISB_SRC" )"
  mkdir -p "$T3/.claude/scripts/tests" || scaffold "E.3 seed mkdir failed"
  cp "$MISB_SRC" "$T3/$MISB_REL" || scaffold "E.3 seed misB cp failed"
fi

KEEPC_REL=".claude/hooks/tests/adopter_custom_probe_p161.py"
printf '# adopter-owned probe — must NEVER be purged (matches nothing)\n' \
  > "$T3/$KEEPC_REL"

KEEPD_REL=""
if [ -f "$SOURCE_DIR/.claude/hooks/_lib/testing.py" ]; then
  KEEPD_REL=".claude/hooks/tests/testing_relocated_p161.py"
  cp "$SOURCE_DIR/.claude/hooks/_lib/testing.py" "$T3/$KEEPD_REL" \
    || scaffold "E.3 seed keepD cp failed"
fi

LINK_TARGET="$T3/adopter-owned-link-target.txt"
printf 'adopter content behind a symlink\n' > "$LINK_TARGET"
LINKE_REL=".claude/hooks/tests/link_probe_p161.py"
ln -s ../../../adopter-owned-link-target.txt "$T3/$LINKE_REL" \
  || scaffold "E.3 seed symlink failed"

echo "==> E.3a — default run (NO flag): preview only, nothing deleted"
bash "$SOURCE_DIR/scripts/upgrade.sh" "$T3" --profile core \
  > "$WORKROOT/e3a-upgrade.log" 2>&1
if grep -q -- '--purge-misinstalled' "$WORKROOT/e3a-upgrade.log" \
   && grep -q "$MISA_REL" "$WORKROOT/e3a-upgrade.log"; then
  ok "E.3a would-purge preview names $MISA_REL + the opt-in flag hint"
else
  bad "E.3a no would-purge preview (+ flag hint) for seeded $MISA_REL"
fi
for f in "$MISA_REL" "$MISB_REL" "$KEEPC_REL" "$KEEPD_REL" "$LINKE_REL"; do
  [ -n "$f" ] || continue
  if [ -e "$T3/$f" ] || [ -L "$T3/$f" ]; then
    ok "E.3a still present without the flag: $f"
  else
    bad "E.3a DELETED WITHOUT the opt-in flag: $f"
  fi
done

echo "==> E.3b — --purge-misinstalled: hash-authorized files purged + backed up"
# Anchor the backup assertion to THIS run's backup dir (a prior run's
# whole-tree backup must not satisfy it): record pre-existing bak dirs, then
# require the purged-file backup inside a NEW one. sleep 1 guarantees a
# distinct per-run timestamp dir.
find "$T3/.claude.bak" -mindepth 1 -maxdepth 1 -type d 2>/dev/null \
  | LC_ALL=C sort > "$WORKROOT/bakdirs-before.txt"
sleep 1
bash "$SOURCE_DIR/scripts/upgrade.sh" "$T3" --profile core --purge-misinstalled \
  > "$WORKROOT/e3b-upgrade.log" 2>&1
RC_B=$?
find "$T3/.claude.bak" -mindepth 1 -maxdepth 1 -type d 2>/dev/null \
  | LC_ALL=C sort > "$WORKROOT/bakdirs-after.txt"
NEW_BAK="$( comm -13 "$WORKROOT/bakdirs-before.txt" "$WORKROOT/bakdirs-after.txt" )"
if [ "$RC_B" -eq 0 ]; then
  ok "E.3b upgrade --purge-misinstalled returned 0"
else
  bad "E.3b upgrade --purge-misinstalled exited $RC_B (flag unknown on HEAD?)"
  tail -5 "$WORKROOT/e3b-upgrade.log" >&2
fi
for f in "$MISA_REL" "$MISB_REL"; do
  [ -n "$f" ] || continue
  if [ ! -e "$T3/$f" ]; then
    ok "E.3b hash-authorized mis-install purged: $f"
  else
    bad "E.3b hash-authorized mis-install NOT purged: $f"
  fi
  if [ -n "$NEW_BAK" ] \
     && find $NEW_BAK -type f -path "*${f#.claude/}" 2>/dev/null | grep -q .; then
    ok "E.3b backup exists (in THIS run's bak dir) for purged $f"
  else
    bad "E.3b no backup in this run's bak dir for purged $f"
  fi
done
for f in "$KEEPC_REL" "$KEEPD_REL"; do
  [ -n "$f" ] || continue
  if [ -e "$T3/$f" ]; then
    ok "E.3b outside-provenance file kept: $f"
  else
    bad "E.3b outside-provenance file WRONGLY purged: $f"
  fi
done
if grep -q "$KEEPC_REL" "$WORKROOT/e3b-upgrade.log"; then
  ok "E.3b kept file is WARNED about in the log"
else
  bad "E.3b no keep-warning for $KEEPC_REL in the log"
fi
if [ -L "$T3/$LINKE_REL" ] && [ -f "$LINK_TARGET" ] \
   && grep -q 'adopter content behind a symlink' "$LINK_TARGET"; then
  ok "E.3b symlink in excluded tree skipped; link target untouched"
else
  bad "E.3b symlink probe damaged (symlink purged or target touched)"
fi

echo "==> E.3c — second --purge-misinstalled run: no-op, no new purge backups"
BAK_BEFORE="$( find "$T3/.claude.bak" -type f 2>/dev/null | grep -c "$( basename "$MISA_REL" )" )"
bash "$SOURCE_DIR/scripts/upgrade.sh" "$T3" --profile core --purge-misinstalled \
  > "$WORKROOT/e3c-upgrade.log" 2>&1
BAK_AFTER="$( find "$T3/.claude.bak" -type f 2>/dev/null | grep -c "$( basename "$MISA_REL" )" )"
if grep -q 'PURGED' "$WORKROOT/e3c-upgrade.log"; then
  bad "E.3c second run performed purge actions (not a no-op)"
else
  ok "E.3c second run purged nothing"
fi
if [ "$BAK_BEFORE" = "$BAK_AFTER" ]; then
  ok "E.3c no new backup content for already-purged files"
else
  bad "E.3c backup content grew on the no-op run ($BAK_BEFORE -> $BAK_AFTER)"
fi

echo "==> E.3d — ancestor-SYMLINK excluded tree: purge scan + rmdir sweep never walk through it"
# STAGED-ORACLE contract like the E.3 purge legs (green only with the W2
# pack; plain FAILs on HEAD, where --purge-misinstalled does not exist).
# Regression shape (codex r4 F2, folded into the tracked oracle per r5 U3):
# find(1) resolves its COMMAND-LINE path through symlinked ANCESTORS even
# without -L — only descent below the start point is no-follow. So a
# nominated excluded tree behind an adopter symlink (.claude/hooks ->
# external dir OUTSIDE $TARGET) was walked by the pre-fix scan, and — once
# an authorized purge in any OTHER tree made the global purge count
# positive — the rmdir sweep deleted empty dirs INSIDE the external target.
# This leg makes that regression load-bearing: ancestor symlink + external
# rmdir canary (empty subdir) + external decoy file the pre-fix scan would
# nominate + a hash-authorized mis-install in a DIFFERENT tree to arm the
# sweep. The --skip globs keep the refresh/replace walk off the symlink
# (matching the r4 probe): the leg tests the U3 purge path in isolation.
T3D="$( fresh_install )" || scaffold "E.3d install failed"

# (i) hash-AUTHORIZED mis-install in a DIFFERENT excluded tree — arms the
# rmdir sweep (it only runs when the purge count goes positive).
MISB2_SRC="$( find "$SOURCE_DIR/.claude/scripts/tests" -maxdepth 1 -type f -name 'test_*.py' 2>/dev/null | LC_ALL=C sort | head -1 )"
[ -n "$MISB2_SRC" ] || scaffold "E.3d no source scripts test to seed the sweep-arming mis-install"
MISB2_REL=".claude/scripts/tests/$( basename "$MISB2_SRC" )"
mkdir -p "$T3D/.claude/scripts/tests" || scaffold "E.3d seed mkdir failed"
cp "$MISB2_SRC" "$T3D/$MISB2_REL" || scaffold "E.3d seed misB2 cp failed"

# (ii) make the excluded-tree ANCESTOR .claude/hooks a symlink to an
# external dir OUTSIDE $TARGET: tests/<empty subdir> is the rmdir canary,
# tests/<decoy file> is what the pre-fix scan would nominate as a candidate.
OUT3D="$WORKROOT/e3d-outside-hooks"
mkdir -p "$OUT3D/tests/e3d_empty_canary_p161" || scaffold "E.3d outside mkdir failed"
DECOY3D="$OUT3D/tests/e3d_decoy_probe_p161.py"
printf '# e3d decoy: external adopter data behind a symlinked ancestor\n' \
  > "$DECOY3D"
cp "$DECOY3D" "$WORKROOT/e3d-decoy.ref" || scaffold "E.3d decoy ref failed"
mv "$T3D/.claude/hooks" "$T3D/.claude/hooks.aside" \
  || scaffold "E.3d hooks move-aside failed"
ln -s "$OUT3D" "$T3D/.claude/hooks" || scaffold "E.3d ancestor symlink failed"

bash "$SOURCE_DIR/scripts/upgrade.sh" "$T3D" --profile core --purge-misinstalled \
  --skip='.claude/hooks' --skip='.claude/hooks/*' \
  > "$WORKROOT/e3d-upgrade.log" 2>&1
RC_D=$?
if [ "$RC_D" -eq 0 ]; then
  ok "E.3d upgrade --purge-misinstalled returned 0"
else
  bad "E.3d upgrade --purge-misinstalled exited $RC_D (flag unknown on HEAD?)"
  tail -5 "$WORKROOT/e3d-upgrade.log" >&2
fi
if [ ! -e "$T3D/$MISB2_REL" ] \
   && grep -F 'PURGED' "$WORKROOT/e3d-upgrade.log" | grep -qF "$MISB2_REL"; then
  ok "E.3d different-tree mis-install purged (sweep armed): $MISB2_REL"
else
  bad "E.3d different-tree mis-install NOT purged — sweep never armed: $MISB2_REL"
fi
if grep -F "symlinked ancestor '.claude/hooks'" "$WORKROOT/e3d-upgrade.log" \
     | grep -qF '.claude/hooks/tests'; then
  ok "E.3d KEPT line names the symlinked ancestor for .claude/hooks/tests"
else
  bad "E.3d no KEPT symlinked-ancestor line for .claude/hooks/tests (tree walked?)"
fi
if grep -Eq 'e3d_decoy_probe_p161|e3d_empty_canary_p161' "$WORKROOT/e3d-upgrade.log"; then
  bad "E.3d candidate line(s) from INSIDE the symlinked tree (scan walked the ancestor)"
else
  ok "E.3d zero candidate lines from inside the symlinked tree"
fi
if [ -d "$OUT3D/tests/e3d_empty_canary_p161" ]; then
  ok "E.3d external empty subdir NOT rmdir'd (sweep respected the ancestor)"
else
  bad "E.3d external empty subdir REMOVED (rmdir sweep walked the symlinked ancestor)"
fi
if [ -f "$DECOY3D" ] && cmp -s "$DECOY3D" "$WORKROOT/e3d-decoy.ref"; then
  ok "E.3d external decoy file intact byte-identical"
else
  bad "E.3d external decoy file DELETED/ALTERED through the symlinked ancestor"
fi
if [ -L "$T3D/.claude/hooks" ] \
   && [ "$( readlink "$T3D/.claude/hooks" )" = "$OUT3D" ]; then
  ok "E.3d ancestor symlink itself intact"
else
  bad "E.3d ancestor symlink LOST/REWRITTEN by the upgrade"
fi

echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
