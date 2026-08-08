#!/usr/bin/env bash
# scripts/tests/test-upgrade-spec-ownership.sh
# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record ownership of the three
# conditional framework surfaces (SPEC/v1, root PROTOCOL.md,
# .claude/.framework-version) across install → upgrade → doctor → updater.
#
# AC-3 scenarios exercised:
#   S1  maintainer fresh install: SPEC/v1 + PROTOCOL.md + marker DELIVERED
#       and recorded in the baseline manifest; marker == source VERSION;
#       delivered_* ops journaled in .install-state.json
#   S2  2nd-upgrade FORCED route (r6 — the load-bearing fixture): baseline
#       ALREADY contains SPEC/v1 records, SPEC edited locally => upgrade
#       REPLACES it (backup in .claude.bak/<ts>/SPEC/v1) — the generic
#       classified walk would have PRESERVED the edit; root VERSION
#       sentinel is NOT touched (S238/ADR-155 class)
#   S3  user-ceremony install + `upgrade --no-replay` (r9 MANDATORY):
#       neither install nor upgrade creates SPEC/v1 or a root PROTOCOL.md
#       (the ceremony is read by the replay-INDEPENDENT reader)
#   S4  legacy ADOPTER-FORK (r20): baseline without SPEC records (v1.2-and-
#       earlier shape) + locally edited SPEC => PRESERVED in place + named
#       WARNING + forensic snapshot (no pristine fingerprint match)
#   S5  pre-existing marker (r20) AND pre-existing root PROTOCOL.md (r13/
#       r17) on a MAINTAINER install: both EXISTS-skipped => NO delivery
#       record => neither is inventoried as framework-owned; the checker
#       refuses the unrecorded marker and falls back to VERSION; doctor
#       does not flag the adopter's PROTOCOL.md as an orphan
#   S6  updater no-loop regression (r8): post-upgrade tree with stale root
#       VERSION reports the NEW version via the recorded marker
#       (up-to-date, exit 0); stripping the marker record flips it back to
#       the stale VERSION (behind, exit != 0) — proves marker-first is
#       load-bearing, not decorative
#   S7  doctor, user mode (r19): adopter's OWN SPEC/v1 + root PROTOCOL.md
#       are NOT orphan candidates under --strict-orphans (flags resolved
#       from the baseline, not from a ceremony default)
#   S8  doctor, maintainer mode (r9 P2): a stray file inside the DELIVERED
#       SPEC/v1 IS an orphan candidate (positive control — the enumeration
#       does include SPEC when the record says delivered)
#
# The pristine-match branch of the legacy migration (target SPEC/v1 byte-
# identical to a shipped v1.2.0-or-earlier tree) deliberately lives in the
# F4 install-v1.2.0→upgrade e2e (needs real tag content); it is NOT
# duplicated here.
#
# bash 3.2-safe. mktemp -d only (xdist/parallel safe). Exits 0 on success,
# non-zero on any failed assertion.
#
# Run:  bash scripts/tests/test-upgrade-spec-ownership.sh ; echo rc=$?

set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
# Override points so the test can be pointed at staged/candidate scripts
# while they still live in a plan-staging mirror (PLAN-153 discipline).
# NOTE: an override must point INTO a full framework checkout — install.sh /
# upgrade.sh derive their source tree from their own resolved location.
INSTALL="${CEO_INSTALL_UNDER_TEST:-$SOURCE_DIR/scripts/install.sh}"
UPGRADE="${CEO_UPGRADE_UNDER_TEST:-$SOURCE_DIR/scripts/upgrade.sh}"
DOCTOR="${CEO_DOCTOR_UNDER_TEST:-$SOURCE_DIR/scripts/doctor.sh}"
CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"

export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

if ! command -v python3 >/dev/null 2>&1; then
  echo "==> SKIP: python3 not installed (install-state machinery is python3-backed)"
  exit 0
fi

SRC_VERSION="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
if [ -z "$SRC_VERSION" ]; then
  echo "FATAL: cannot read $SOURCE_DIR/VERSION" >&2
  exit 2
fi
if [ ! -f "$SOURCE_DIR/.claude/.framework-version" ]; then
  echo "FATAL: source has no .claude/.framework-version (F3 marker missing)" >&2
  exit 2
fi

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-f3-own-XXXXXX )"
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

_git_init_retry() {
  local d="$1" n=0
  while [ "$n" -lt 5 ]; do
    if ( cd "$d" && git init -q 2>/dev/null ); then return 0; fi
    n=$((n+1)); sleep 1
  done
  ( cd "$d" && git init -q )
}

run_install() {
  local t="$1"; shift
  bash "$INSTALL" "$t" "$@" >"$t.install.log" 2>&1
}

run_upgrade() {
  local t="$1"; shift
  bash "$UPGRADE" "$t" --no-deprecation-warn "$@" >"$t.upgrade.log" 2>&1
}

fresh_install() {
  # $1 = leg tag, rest = install args. Echoes the target path.
  local tag="$1"; shift
  local t
  t="$( mktemp -d "$WORKROOT/tgt-$tag-XXXXXX" )"
  _git_init_retry "$t"
  if ! run_install "$t" "$@"; then
    echo "INSTALL_FAILED ($tag)" >&2
    tail -30 "$t.install.log" >&2
    return 1
  fi
  printf '%s\n' "$t"
}

MANIFEST_REL=".claude/.install-manifest.sha256"
MARKER_REL=".claude/.framework-version"

manifest_has() {  # $1 = target, $2 = ERE fragment at the relpath position
  grep -Eq "^([0-9a-f]{64}|LINK)  $2" "$1/$MANIFEST_REL" 2>/dev/null
}

# --------------------------------------------------------------------------
# S1 — maintainer fresh install: delivery recorded end-to-end.
# --------------------------------------------------------------------------
echo "==> S1: maintainer install — SPEC/marker/PROTOCOL delivered + recorded"
T1="$( fresh_install m1 --profile core )" || exit 1

[ -d "$T1/SPEC/v1" ]            && ok "SPEC/v1 installed"            || bad "SPEC/v1 missing after maintainer install"
[ -f "$T1/PROTOCOL.md" ]        && ok "root PROTOCOL.md installed"   || bad "root PROTOCOL.md missing"
[ -f "$T1/$MARKER_REL" ]        && ok "marker installed"             || bad "marker missing"
[ "$(tr -d '[:space:]' < "$T1/$MARKER_REL" 2>/dev/null)" = "$SRC_VERSION" ] \
  && ok "marker == source VERSION ($SRC_VERSION)" \
  || bad "marker != source VERSION (got: $(cat "$T1/$MARKER_REL" 2>/dev/null))"

manifest_has "$T1" 'SPEC/v1/'                              && ok "baseline records SPEC/v1/"    || bad "baseline has NO SPEC/v1/ record"
manifest_has "$T1" 'PROTOCOL\.md(  |$)'                    && ok "baseline records PROTOCOL.md" || bad "baseline has NO PROTOCOL.md record"
manifest_has "$T1" '\.claude/\.framework-version(  |$)'    && ok "baseline records marker"      || bad "baseline has NO marker record"

grep -q '"delivered_spec_v1"' "$T1/.claude/.install-state.json" 2>/dev/null \
  && ok "install-state journals delivered_spec_v1" \
  || bad "install-state missing delivered_spec_v1 op"
grep -q '"delivered_framework_marker"' "$T1/.claude/.install-state.json" 2>/dev/null \
  && ok "install-state journals delivered_framework_marker" \
  || bad "install-state missing delivered_framework_marker op"

# --------------------------------------------------------------------------
# S2 — 2nd-upgrade forced route: record-owned edited SPEC is REPLACED with
# backup; root VERSION sentinel untouched (AC-3 load-bearing fixture).
# --------------------------------------------------------------------------
echo "==> S2: 2nd upgrade — forced SPEC refresh (baseline already has SPEC)"
SPEC_FILE="$( ls "$T1"/SPEC/v1/*.md 2>/dev/null | head -1 )"
if [ -z "$SPEC_FILE" ]; then
  bad "no SPEC file found to edit"
else
  printf '\nADOPTER-EDIT sentinel S2\n' >> "$SPEC_FILE"
fi
printf '1.0.0\n' > "$T1/VERSION"   # adopter-owned root VERSION sentinel

if run_upgrade "$T1"; then ok "upgrade rc=0 (record-owned fixture)"; else bad "upgrade failed (see $T1.upgrade.log)"; fi

SPEC_REL="${SPEC_FILE#"$T1"/}"
if [ -n "$SPEC_FILE" ]; then
  cmp -s "$SOURCE_DIR/$SPEC_REL" "$SPEC_FILE" \
    && ok "edited SPEC file was FORCE-replaced with source bytes" \
    || bad "edited SPEC file NOT replaced (classified walk preserved the fork?)"
  BAK_HIT="$( ls -d "$T1"/.claude.bak/*/SPEC/v1 2>/dev/null | head -1 )"
  if [ -n "$BAK_HIT" ] && grep -rq 'ADOPTER-EDIT sentinel S2' "$BAK_HIT" 2>/dev/null; then
    ok "backup of the edited SPEC present under .claude.bak/<ts>/SPEC/v1"
  else
    bad "no .claude.bak backup carrying the edited SPEC content"
  fi
fi
grep -q 'REFRESHED (forced' "$T1.upgrade.log" \
  && ok "upgrade log names the forced route" \
  || bad "upgrade log has no 'REFRESHED (forced' line"
[ "$(tr -d '[:space:]' < "$T1/VERSION" 2>/dev/null)" = "1.0.0" ] \
  && ok "root VERSION sentinel untouched by upgrade (ADR-155-AMEND-1)" \
  || bad "root VERSION was modified by upgrade (got: $(cat "$T1/VERSION" 2>/dev/null))"
[ "$(tr -d '[:space:]' < "$T1/$MARKER_REL" 2>/dev/null)" = "$SRC_VERSION" ] \
  && ok "marker refreshed to source VERSION post-upgrade" \
  || bad "marker not refreshed post-upgrade"
manifest_has "$T1" 'SPEC/v1/' \
  && ok "rewritten baseline still records SPEC/v1/ (ownership continuity)" \
  || bad "rewritten baseline dropped the SPEC/v1 records"

# --------------------------------------------------------------------------
# S6 — updater no-loop (r8) on the S2 fixture: marker-first wins over the
# stale root VERSION; stripping the marker record flips the source back.
# --------------------------------------------------------------------------
echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
STUB="$WORKROOT/stub-upstream"
mkdir -p "$STUB"
_git_init_retry "$STUB"
( cd "$STUB" \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m x \
  && git tag "v$SRC_VERSION" ) 2>/dev/null \
  && ok "stub upstream tagged v$SRC_VERSION" \
  || bad "stub upstream construction failed"

CHK_OUT="$WORKROOT/chk1.out"; CHK_ERR="$WORKROOT/chk1.err"
( cd "$T1" && bash "$CHECKER" --upstream "$STUB" ) >"$CHK_OUT" 2>"$CHK_ERR"
CHK_RC=$?
[ "$CHK_RC" -eq 0 ] && grep -q 'up-to-date' "$CHK_OUT" \
  && ok "post-upgrade tree reports up-to-date via marker (no behind-minor loop)" \
  || bad "updater loop regression: rc=$CHK_RC (expected 0/up-to-date via marker; VERSION=1.0.0 is stale by design)"
grep -q 'version source: marker' "$CHK_ERR" \
  && ok "checker names the marker as its version source" \
  || bad "checker did not use the marker (stderr: $(head -3 "$CHK_ERR" 2>/dev/null | tr '\n' ' '))"

# Negative control: strip the marker record => fallback to stale VERSION.
sed -i.bak '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null \
  || sed -i '' '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null
( cd "$T1" && bash "$CHECKER" --upstream "$STUB" ) >"$WORKROOT/chk2.out" 2>"$WORKROOT/chk2.err"
CHK2_RC=$?
[ "$CHK2_RC" -ne 0 ] \
  && ok "marker record stripped => fallback to stale VERSION => behind (rc=$CHK2_RC)" \
  || bad "checker still up-to-date after stripping the marker record — record gate is dead"
grep -q 'falling back to VERSION' "$WORKROOT/chk2.err" \
  && ok "checker names the r20 fallback" \
  || bad "no 'falling back to VERSION' note on stripped record"

# --------------------------------------------------------------------------
# S8 — doctor, maintainer mode: delivered SPEC IS enumerated (orphan
# positive control).
# --------------------------------------------------------------------------
echo "==> S8: doctor maintainer mode — stray file in delivered SPEC is an orphan"
# Restore the marker record stripped by S6's negative control (the .bak of
# the GNU-sed branch, if present, is the pristine manifest).
if [ -f "$T1/$MANIFEST_REL.bak" ]; then mv "$T1/$MANIFEST_REL.bak" "$T1/$MANIFEST_REL"; fi
printf 'stray\n' > "$T1/SPEC/v1/zz-orphan-probe.md"
DOC_OUT="$WORKROOT/doc1.out"
bash "$DOCTOR" "$T1" --strict-orphans >"$DOC_OUT" 2>&1
DOC_RC=$?
grep -q 'ORPHAN?: SPEC/v1/zz-orphan-probe.md' "$DOC_OUT" && [ "$DOC_RC" -ne 0 ] \
  && ok "delivered SPEC is enumerated: stray file flagged, rc=$DOC_RC" \
  || bad "stray file in delivered SPEC NOT flagged (rc=$DOC_RC) — FMS_DELIVERED_SPEC resolution dead"
rm -f "$T1/SPEC/v1/zz-orphan-probe.md"

# --------------------------------------------------------------------------
# S4 — legacy ADOPTER-FORK (fresh fixture; simulate the v1.2-and-earlier
# baseline shape by stripping SPEC records, then fork the SPEC).
# --------------------------------------------------------------------------
echo "==> S4: legacy baseline (no SPEC records) + edited SPEC => preserve + WARNING"
T2="$( fresh_install m2 --profile core )" || exit 1
sed -i.bak '/  SPEC\/v1\//d' "$T2/$MANIFEST_REL" 2>/dev/null \
  || sed -i '' '/  SPEC\/v1\//d' "$T2/$MANIFEST_REL" 2>/dev/null
rm -f "$T2/$MANIFEST_REL.bak"
SPEC2="$( ls "$T2"/SPEC/v1/*.md 2>/dev/null | head -1 )"
printf '\nADOPTER-FORK sentinel S4\n' >> "$SPEC2"

if run_upgrade "$T2"; then ok "upgrade rc=0 (fork is preserved, never fatal)"; else bad "upgrade failed on adopter-fork fixture"; fi
grep -q 'ADOPTER-FORK' "$T2.upgrade.log" \
  && ok "named ADOPTER-FORK warning emitted" \
  || bad "no ADOPTER-FORK warning in upgrade log"
grep -q 'ADOPTER-FORK sentinel S4' "$SPEC2" 2>/dev/null \
  && ok "forked SPEC preserved in place" \
  || bad "forked SPEC was clobbered despite missing delivery record"
manifest_has "$T2" 'SPEC/v1/' \
  && bad "rewritten baseline claims the adopter-fork SPEC as framework-owned" \
  || ok "rewritten baseline does NOT claim the adopter-fork SPEC"
SNAP_HIT="$( ls -d "$T2"/.claude.bak/*/SPEC/v1 2>/dev/null | head -1 )"
[ -n "$SNAP_HIT" ] \
  && ok "forensic snapshot of the fork present under .claude.bak" \
  || bad "no forensic snapshot of the preserved fork"

# --------------------------------------------------------------------------
# S3 — user ceremony + upgrade --no-replay (r9): no SPEC, no root files.
# --------------------------------------------------------------------------
echo "==> S3: --ceremony user install + upgrade --no-replay"
T3="$( fresh_install u1 --profile core --ceremony user )" || exit 1
[ ! -e "$T3/SPEC" ]        && ok "user install has no SPEC/"            || bad "user install received SPEC/"
[ ! -e "$T3/PROTOCOL.md" ] && ok "user install has no root PROTOCOL.md" || bad "user install received root PROTOCOL.md"
[ -f "$T3/$MARKER_REL" ]   && ok "user install DOES receive the marker (inside .claude/)" \
                           || bad "user install missing the marker"
manifest_has "$T3" '\.claude/\.framework-version(  |$)' \
  && ok "user baseline records the marker" || bad "user baseline missing marker record"

if run_upgrade "$T3" --no-replay; then ok "upgrade --no-replay rc=0 on user fixture"; else bad "upgrade --no-replay failed on user fixture"; fi
[ ! -e "$T3/SPEC" ] \
  && ok "upgrade --no-replay did NOT deliver SPEC (ceremony read is replay-independent)" \
  || bad "r9 REGRESSION: upgrade --no-replay forced SPEC into a user install"
[ ! -e "$T3/PROTOCOL.md" ] \
  && ok "upgrade --no-replay did NOT create root PROTOCOL.md (gated _refresh_protocol_pointer)" \
  || bad "r13 REGRESSION: protocol pointer created on a user install"
grep -Eq 'Ceremony: user' "$T3.upgrade.log" \
  && ok "upgrade banner names the recorded user ceremony" \
  || bad "upgrade banner missing 'Ceremony: user'"

# --------------------------------------------------------------------------
# S7 — doctor, user mode: adopter's own SPEC + root PROTOCOL.md are not
# orphan candidates.
# --------------------------------------------------------------------------
echo "==> S7: doctor user mode — adopter SPEC/PROTOCOL not orphans"
mkdir -p "$T3/SPEC/v1"
printf 'the ADOPTERs own contract\n' > "$T3/SPEC/v1/own.md"
printf 'the ADOPTERs own protocol\n' > "$T3/PROTOCOL.md"
DOC3_OUT="$WORKROOT/doc3.out"
bash "$DOCTOR" "$T3" --strict-orphans >"$DOC3_OUT" 2>&1
DOC3_RC=$?
if grep -Eq 'ORPHAN\?: (SPEC/v1/|PROTOCOL\.md)' "$DOC3_OUT"; then
  bad "r19 REGRESSION: doctor flags the adopter's own SPEC/PROTOCOL as orphans (rc=$DOC3_RC)"
else
  ok "adopter's own SPEC/PROTOCOL not flagged (rc=$DOC3_RC)"
fi
[ "$DOC3_RC" -eq 0 ] \
  && ok "doctor --strict-orphans clean on the user fixture" \
  || bad "doctor --strict-orphans rc=$DOC3_RC on user fixture (see $DOC3_OUT)"
rm -f "$T3/PROTOCOL.md"

# --------------------------------------------------------------------------
# S5 — pre-existing marker (r20): EXISTS-skip => no record => VERSION wins.
# --------------------------------------------------------------------------
echo "==> S5: pre-existing marker + pre-existing root PROTOCOL.md not delivered, not trusted"
T4="$( mktemp -d "$WORKROOT/tgt-m3-XXXXXX" )"
_git_init_retry "$T4"
mkdir -p "$T4/.claude"
printf '9.9.9\n' > "$T4/$MARKER_REL"
printf '# the ADOPTERs own protocol (pre-existing)\n' > "$T4/PROTOCOL.md"
if run_install "$T4" --profile core; then ok "install rc=0 with pre-existing marker+protocol"; else bad "install failed (see $T4.install.log)"; fi
[ "$(tr -d '[:space:]' < "$T4/$MARKER_REL" 2>/dev/null)" = "9.9.9" ] \
  && ok "pre-existing marker EXISTS-skipped (adopter bytes intact)" \
  || bad "install overwrote a pre-existing marker"
manifest_has "$T4" '\.claude/\.framework-version(  |$)' \
  && bad "baseline claims a marker the install never wrote (r17/r20)" \
  || ok "baseline does NOT record the skipped marker"
grep -q 'ADOPTERs own protocol' "$T4/PROTOCOL.md" 2>/dev/null \
  && ok "pre-existing root PROTOCOL.md EXISTS-skipped (adopter bytes intact)" \
  || bad "install overwrote a pre-existing root PROTOCOL.md"
manifest_has "$T4" 'PROTOCOL\.md(  |$)' \
  && bad "r13/r17 REGRESSION: baseline claims a PROTOCOL.md the install never wrote" \
  || ok "baseline does NOT record the skipped PROTOCOL.md"
DOC4_OUT="$WORKROOT/doc4.out"
bash "$DOCTOR" "$T4" --strict-orphans >"$DOC4_OUT" 2>&1
DOC4_RC=$?
if grep -Eq 'ORPHAN\?: PROTOCOL\.md' "$DOC4_OUT"; then
  bad "doctor flags the adopter's pre-existing PROTOCOL.md as an orphan (rc=$DOC4_RC)"
else
  ok "doctor does not orphan-flag the adopter's pre-existing PROTOCOL.md (rc=$DOC4_RC)"
fi
( cd "$T4" && bash "$CHECKER" --upstream "$STUB" ) >"$WORKROOT/chk3.out" 2>"$WORKROOT/chk3.err"
CHK3_RC=$?
grep -q 'falling back to VERSION' "$WORKROOT/chk3.err" \
  && ok "checker refuses the unrecorded marker (r20)" \
  || bad "checker trusted an unrecorded marker (stderr: $(head -3 "$WORKROOT/chk3.err" 2>/dev/null | tr '\n' ' '))"
[ "$CHK3_RC" -eq 0 ] && grep -q 'up-to-date' "$WORKROOT/chk3.out" \
  && ok "fallback VERSION ($SRC_VERSION) matches stub upstream — up-to-date" \
  || bad "fallback path wrong rc=$CHK3_RC"

echo ""
echo "==> RESULT: pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
