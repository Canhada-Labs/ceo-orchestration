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
# patched framework checkout.
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

echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
