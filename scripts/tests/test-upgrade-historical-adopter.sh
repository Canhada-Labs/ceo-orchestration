#!/usr/bin/env bash
# scripts/tests/test-upgrade-historical-adopter.sh
# PLAN-183 W5 (S327) — upgrade.sh delivers docs/ + .github/ (D1) and reaches
# the HISTORICAL ADOPTER population (OQ-5 amendment, Owner 2026-08-24).
#
# WHY THIS EXISTS
# ---------------
# Two things landed together and neither is observable by the checks that
# already exist:
#
#   D1     upgrade.sh never delivered docs/ or .github/ (measured S323:
#          `grep -c github scripts/upgrade.sh` = 0). The parity e2e SEES the
#          consequence (STALE 3) but only through the v1.2.0-pinned route, and
#          it says nothing about WHICH ownership verdict produced the write.
#   OQ-5   the amendment fires exactly when there is NO readable install-state,
#          which is precisely the state the pinned parity route can never be
#          in: install.sh @ v1.2.0 writes install-state, so the pinned leg is
#          STRUCTURALLY BLIND to the amendment (debate class C2 — "a Check
#          that only exercises the pinned path passes vacuously").
#
# So this file BLINDS the state deliberately and asserts per-destination
# verdicts, which is the only way to tell "the upgrade delivered" apart from
# "the file happened to be current already".
#
# THE ASSERTIONS THAT ARE NOT ABOUT THE HAPPY PATH
#   H.4  an adopter-edited destination is PRESERVED **byte-identical** — the
#        whole ownership ladder exists to make this true, and a delivery that
#        only ever refreshes would pass every other assertion here.
#   H.5  the inferred ceremony is NOT persisted (upgrade.sh:801-803). Persist
#        it and one missed migration becomes permanent.
#   H.7  a `/`-bearing github_owner in the (UNSIGNED, target-side) state file
#        is REFUSED, never interpolated into sed. PLAN-183 §9.2 reproduced
#        install.sh:1508 aborting with a 0-byte CODEOWNERS on exactly that
#        input, and the file then survives EXISTS-skipped forever.
#   H.8  a DANGLING SYMLINK destination is PRESERVED, never written through.
#        PLAN-183 §9.1 reproduced that write-outside-$TARGET on install.sh
#        (now PLAN-185 F1); the new upgrade route does not get to ship it too.
#   H.27 the RENDERED route (.github/CODEOWNERS) recognises its OWN prior
#        generations — the ladder has to substitute the handle into every
#        historical blob before hashing. Its positive control PLANTS the
#        pre-cure shape (generations hashed unrendered) and requires the
#        adopter to stay stuck on stale bytes; without that plant, "REFRESHED"
#        here is indistinguishable from "the file was already current".
#   N.1  the NEGATIVE control: neither install-state nor .framework-version =>
#        delivery DISABLED. Without it, "delivery enabled" could just be
#        unconditional and every positive assertion above would still pass.
#
# bash-3.2 safe (no associative arrays, no mapfile). Network-free. Writes only
# under mktemp -d. Requires: git, python3.
#
# Run:  bash scripts/tests/test-upgrade-historical-adopter.sh ; echo rc=$?
set -uo pipefail   # NOT -e: every failure is asserted, never fatal-by-default.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
INSTALL="$REPO_ROOT/scripts/install.sh"
UPGRADE="$REPO_ROOT/scripts/upgrade.sh"
ROUTES="$REPO_ROOT/scripts/delivery-routes.tsv"

# The route table is the truth for WHICH destinations exist; the count is
# asserted here (H.1) rather than in the script, where a hardcoded 6 would be
# a second copy of the table that rots silently.
EXPECTED_ROUTES=6

PASS=0
FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

scaffold() { echo "" >&2; echo "SCAFFOLD-ERROR: $*" >&2; exit 9; }

command -v git     >/dev/null 2>&1 || scaffold "git not on PATH"
command -v python3 >/dev/null 2>&1 || scaffold "python3 not on PATH"

# --- rail round-1 F3: git HISTORY is a precondition, not a happy accident ---
# H.3 plants a PRIOR framework generation of templates/docs/BRANCH-PROTECTION.md
# and asserts the upgrade REFRESHES it. The generation is derived from
# `git log` on $REPO_ROOT. In smoke-install.yml the checkout is
# `fetch-depth: 1`, so that log holds exactly ONE commit — whose blob IS the
# current file — and no prior generation can be found.
#
# MEASURED (S327, this repo): templates/docs/BRANCH-PROTECTION.md has TWO
# generations; the current one landed at depth 40 and the only differing one
# is the ROOT commit at depth 502 of 503. There is therefore no honest
# `--deepen=<N>` short of the full history, which is why the workflow uses
# `git fetch --unshallow` (43 MB / 503 commits — seconds, against a 50-minute
# job).
#
# This is a SCAFFOLD error, not an assertion failure: the instrument cannot
# run, which is a different fact from "the product is wrong", and it must never
# degrade into a skip or a vacuous pass.
_IS_SHALLOW="$( git -C "$REPO_ROOT" rev-parse --is-shallow-repository 2>/dev/null || echo unknown )"
if [ "$_IS_SHALLOW" = "true" ]; then
  scaffold "history unavailable: shallow checkout — deepen before running.
                 H.3 needs a PRIOR generation of templates/docs/BRANCH-PROTECTION.md
                 and a depth-1 clone holds exactly one. Remedy:
                     git -C '$REPO_ROOT' fetch --unshallow --no-tags
                 In CI this is the 'Deepen git history' step of smoke-install.yml
                 (rail round-1 F3); if you are seeing this there, that step did
                 not run — check its 'if:' guard."
fi
[ -f "$INSTALL" ] || scaffold "installer missing: $INSTALL"
[ -f "$UPGRADE" ] || scaffold "upgrader missing: $UPGRADE"
[ -f "$ROUTES" ]  || scaffold "route table missing: $ROUTES"

WORK="$( mktemp -d -t ceo-hist-adopter-XXXXXX )" || scaffold "mktemp -d failed"
cleanup() {
  [ "${CEO_HIST_KEEP_WORK:-0}" = "1" ] && return 0
  [ -n "${WORK:-}" ] || return 0
  chmod -R u+w "$WORK" 2>/dev/null || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

# rail round-6 F3 — the environment can no longer name the route table: the
# library resolves it from the tree it ships in, unconditionally. An upgrade
# therefore takes a fixture table the only way production could give it one —
# by running from a DIFFERENT CHECKOUT. `_mk_source_copy` builds that checkout;
# every fixture-table leg below runs `$COPY/scripts/upgrade.sh`.
#
# $1 = directory to build; $2 = table to install as its
# scripts/delivery-routes.tsv, or NONE for a checkout with no table.
# Everything but scripts/ is symlinked; scripts/ is a real copy so the table
# (and, for the RED plants, the library) can be replaced. upgrade.sh resolves
# SOURCE_DIR from its own BASH_SOURCE, and the library resolves the table from
# ITS own BASH_SOURCE — which is what makes the copy's table authoritative.
#
# rail round-7 F2 — templates/ joins scripts/ as a REAL copy. Delivery sources
# are now PHYSICALLY confined to the running checkout (_wbm_source_confined),
# and a symlinked templates/ is precisely the escape that predicate refuses:
# every route source would resolve into the REAL repo, outside this fixture's
# SOURCE_DIR. Leaving it a symlink would make every fixture below measure a
# confinement refusal instead of the behaviour it exists to test — a fixture
# that is green for the wrong reason. 360 KB / 34 files, measured.
_mk_source_copy() {  # $1=dir $2=table|NONE
  mkdir -p "$1" || return 1
  for _msc_e in "$REPO_ROOT"/* "$REPO_ROOT"/.[!.]*; do
    [ -e "$_msc_e" ] || continue
    _msc_b="$( basename "$_msc_e" )"
    case "$_msc_b" in scripts|templates) continue ;; esac
    ln -s "$_msc_e" "$1/$_msc_b" 2>/dev/null || true
  done
  cp -R "$REPO_ROOT/scripts" "$1/scripts" || return 1
  cp -R "$REPO_ROOT/templates" "$1/templates" || return 1
  rm -f "$1/scripts/delivery-routes.tsv" || return 1
  if [ "$2" != "NONE" ]; then
    cp "$2" "$1/scripts/delivery-routes.tsv" || return 1
  fi
  return 0
}

echo "=============================================================="
echo " upgrade historical-adopter e2e   (PLAN-183 W5 — D1 + OQ-5)"
echo "=============================================================="
echo "  repo   : $REPO_ROOT"
echo "  workdir: $WORK"
echo "--------------------------------------------------------------"

# --- helpers ---------------------------------------------------------------

# Fresh maintainer install into $1, or a COPY of a cached one.
#
# The cache is not a micro-optimisation: this file needs six independent
# adopter fixtures and a real install is by far the most expensive thing here
# (measured 372 s of wall time for the uncached version under load, which at
# the 2-3x runner factor this workflow sizes with would have been 12-18 CI
# minutes on top of an already 32-minute job). Two bases are cached — one
# without a --github-owner and one with — because that flag changes WHICH
# CODEOWNERS row install.sh delivers, and copying across that boundary would
# fabricate a tree no install ever produces.
#
# A copy is equivalent to a fresh install here for a reason worth stating:
# install.sh substitutes {{PROJECT_NAME}} with basename($TARGET) and EVERY
# fixture below is named ".../adopter", so the substituted bytes are identical.
# The install-state records `target`, but no reader on the upgrade path
# consults it (_read_install_state_ceremony reads request.ceremony;
# _read_install_state_request reads profile/stack/harness), so a stale path in
# that field cannot change any verdict this file asserts.
_INSTALL_CACHE_PLAIN=""
_INSTALL_CACHE_OWNER=""
_install_into() {
  _ii_dir="$1"; shift
  _ii_cache_var="_INSTALL_CACHE_PLAIN"
  [ "$#" -gt 0 ] && _ii_cache_var="_INSTALL_CACHE_OWNER"
  eval "_ii_cached=\"\${$_ii_cache_var}\""
  if [ -n "$_ii_cached" ] && [ -d "$_ii_cached" ]; then
    mkdir -p "$( dirname "$_ii_dir" )"
    cp -R "$_ii_cached" "$_ii_dir" || scaffold "could not copy the cached install into $_ii_dir"
    return 0
  fi
  mkdir -p "$_ii_dir"
  ( cd "$_ii_dir" && git init -q ) || scaffold "git init failed in $_ii_dir"
  bash "$INSTALL" "$_ii_dir" --profile core --ceremony maintainer "$@" \
    > "$_ii_dir.install.log" 2>&1 \
    || { tail -30 "$_ii_dir.install.log" >&2; scaffold "install.sh failed for $_ii_dir"; }
  # Seed the cache from the FIRST install of each flavour.
  _ii_seed="$WORK/cache/$( basename "$_ii_cache_var" )/adopter"
  mkdir -p "$( dirname "$_ii_seed" )"
  cp -R "$_ii_dir" "$_ii_seed" || scaffold "could not seed the install cache"
  eval "$_ii_cache_var=\"\$_ii_seed\""
}

# Upgrade $1 from the working tree. Sets _UP_LOG and _UP_RC in THIS shell —
# never echoes the path, because `LOG=$( _upgrade ... )` would run the whole
# thing in a subshell and _UP_RC would come back unbound (measured: that is
# exactly how the first draft of this file died).
_UP_LOG=""
_UP_RC=0
_UPGRADE_SEQ=0
_upgrade() {
  _u_dir="$1"; shift
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  _UP_LOG="$_u_dir.upgrade.$_UPGRADE_SEQ.log"
  _UP_RC=0
  bash "$UPGRADE" "$_u_dir" --profile core --no-diff-warn "$@" > "$_UP_LOG" 2>&1 || _UP_RC=$?
}

_sha() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }

# The summary field $2 out of the delivery line in log $1 ("" when absent).
_summary_field() {
  awk -v k="$2" '
    /docs\/\.github delivery: routes=/ {
      n = split($0, parts, /[ \t]+/)
      for (i = 1; i <= n; i++) {
        eq = index(parts[i], "=")
        if (eq > 0 && substr(parts[i], 1, eq - 1) == k) { print substr(parts[i], eq + 1); exit }
      }
    }' "$1" 2>/dev/null
}

# --- H.1  route enumeration is not vacuous ---------------------------------
echo ""
echo "==> H.1 — the route table yields exactly $EXPECTED_ROUTES destinations"
ROW_COUNT=0
# rail round-4 F4: `|| [ -n ... ]` — an unterminated final row fills the read
# variables but returns non-zero, so a bare loop silently counts one row short.
# The product's three readers were cured of exactly this; the instrument that
# derives their denominator must not carry the defect it is checking for.
while IFS=$'\t' read -r _r_dest _r_rest || [ -n "${_r_dest:-}" ]; do
  [ -n "${_r_dest:-}" ] || continue
  case "$_r_dest" in \#*|dest) continue ;; esac
  ROW_COUNT=$(( ROW_COUNT + 1 ))
done < "$ROUTES"
if [ "$ROW_COUNT" -eq "$EXPECTED_ROUTES" ]; then
  ok "H.1 delivery-routes.tsv has $EXPECTED_ROUTES data rows"
else
  bad "H.1 delivery-routes.tsv has $ROW_COUNT data rows, expected $EXPECTED_ROUTES — every count below is measured against the wrong denominator"
fi

# --- fixture (a): historical adopter ---------------------------------------
# Install at HEAD, then BLIND the install-state while KEEPING the marker. That
# is the shape of every pre-Wave-B adopter: the framework is installed, but
# nothing recorded how.
echo ""
echo "==> fixture (a) — install at HEAD, blind the install-state, keep the marker"
A="$WORK/hist/adopter"
_install_into "$A"

[ -f "$A/.claude/.framework-version" ] || scaffold "fixture: marker absent after install"
[ -f "$A/docs/BRANCH-PROTECTION.md" ]  || scaffold "fixture: install delivered no docs/BRANCH-PROTECTION.md"

# Plant a PRIOR framework generation so a real REFRESH has something to do.
# Derived from git, never hardcoded: the assertion must survive the next edit
# of the template.
PRIOR_GEN=""
while IFS= read -r _c; do
  [ -n "$_c" ] || continue
  _b="$( git -C "$REPO_ROOT" rev-parse "$_c:templates/docs/BRANCH-PROTECTION.md" 2>/dev/null || true )"
  [ -n "$_b" ] || continue
  git -C "$REPO_ROOT" cat-file blob "$_b" > "$WORK/gen.candidate" 2>/dev/null || continue
  if [ "$( _sha "$WORK/gen.candidate" )" != "$( _sha "$REPO_ROOT/templates/docs/BRANCH-PROTECTION.md" )" ]; then
    PRIOR_GEN="$WORK/gen.candidate"; break
  fi
done < <( git -C "$REPO_ROOT" log --format='%H' -- templates/docs/BRANCH-PROTECTION.md 2>/dev/null || true )

if [ -n "$PRIOR_GEN" ] && [ -f "$PRIOR_GEN" ]; then
  cp "$PRIOR_GEN" "$A/docs/BRANCH-PROTECTION.md"
  ok "fixture: planted a prior framework generation of docs/BRANCH-PROTECTION.md"
else
  # No second generation in history => the REFRESH leg cannot be exercised.
  # rail round-1 F3: this is a SCAFFOLD error, promoted from `bad`. A single
  # FAIL among 33 assertions is easy to read as "one leg regressed"; the truth
  # is that the instrument could not run at all, and a run in that state
  # certifies nothing. The shallow probe above catches the CI shape of this;
  # this branch catches every other way history can come back empty (a
  # tarball export, a filtered clone, a squashed template file).
  scaffold "fixture: templates/docs/BRANCH-PROTECTION.md has NO prior generation
                 in the git history reachable from '$REPO_ROOT' — the REFRESH leg
                 of H.3 would be VACUOUS, so this run proves nothing and exits
                 rather than reporting a partial pass.
                 If this is a shallow or filtered clone: git fetch --unshallow --no-tags
                 (is-shallow-repository reported: $_IS_SHALLOW)"
fi

# --- rail round-3 F4: plant MODE DRIFT on two branches of the ladder -------
# `cat >` and `cp` onto an EXISTING destination both keep that inode's mode,
# and the IDENTICAL branch writes nothing at all — so a destination whose mode
# drifted (or whose exec bit the framework changed between generations) could
# never converge: every future upgrade refreshes the BYTES, reports success,
# and leaves the parity classifier's FATAL MODE_DIFF standing.
# The reference is a FRESH INSTALL's mode read off THIS fixture before the
# drift is planted — never a hardcoded 0644 — so the assertion stays true
# under any umask, on either lane.
MODE_REF_REFRESH="$( ls -l "$A/docs/BRANCH-PROTECTION.md" | cut -c1-10 )"
MODE_IDENT_PATH=".github/workflows/validate.yml.template"
[ -f "$A/$MODE_IDENT_PATH" ] || scaffold "fixture: install delivered no $MODE_IDENT_PATH — the IDENTICAL mode lane would be vacuous"
MODE_REF_IDENT="$( ls -l "$A/$MODE_IDENT_PATH" | cut -c1-10 )"
case "$MODE_REF_REFRESH$MODE_REF_IDENT" in
  *x*) scaffold "fixture: a fresh install already delivers an exec bit ($MODE_REF_REFRESH / $MODE_REF_IDENT) — a planted 0755 drift would be indistinguishable from it" ;;
esac
chmod 0755 "$A/docs/BRANCH-PROTECTION.md"  || scaffold "fixture: could not plant the mode drift on the REFRESH lane"
chmod 0755 "$A/$MODE_IDENT_PATH"           || scaffold "fixture: could not plant the mode drift on the IDENTICAL lane"

# Adopter-owned edit on a DIFFERENT destination.
printf '\nadopter-owned line — must survive the upgrade\n' >> "$A/docs/rotation-log.md"
ADOPTER_SHA="$( _sha "$A/docs/rotation-log.md" )"

rm -f "$A/.claude/.install-state.json"
[ -f "$A/.claude/.install-state.json" ] && scaffold "fixture: install-state still present after blinding"

echo ""
echo "==> H.2..H.6 — upgrade the historical adopter"
_upgrade "$A" --no-replay
LOG_A="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_A" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the historical fixture"; }

# H.2 — the amendment is what enabled delivery, and it says so.
if grep -q 'docs/\.github delivery: ENABLED — OQ-5 amendment' "$LOG_A"; then
  ok "H.2 delivery ENABLED by the OQ-5 amendment (marker present, state blinded)"
else
  bad "H.2 the OQ-5 amendment branch did not decide this run — grep 'docs/.github delivery: ENABLED — OQ-5 amendment' found nothing in $LOG_A"
fi
# ...and the ceremony itself stayed at the fail-safe. Flipping CEREMONY_EFFECTIVE
# would re-open the root-surface writes that re-pass rc.4 t2 P2 closed.
if grep -qE '^ +Ceremony: user ' "$LOG_A"; then
  ok "H.2b CEREMONY_EFFECTIVE stayed 'user' — the amendment widened delivery only, not the root surfaces"
else
  bad "H.2b CEREMONY_EFFECTIVE is no longer the fail-safe 'user' on a blinded state — root .gitignore/PROTOCOL.md/SPEC writes are back for an UNKNOWN ceremony"
fi

# H.3 — the planted prior generation was REFRESHED to the current source.
if grep -q 'REFRESHED (pristine prior generation): docs/BRANCH-PROTECTION\.md' "$LOG_A"; then
  ok "H.3 docs/BRANCH-PROTECTION.md REFRESHED from a pristine prior generation"
else
  bad "H.3 the planted prior generation was NOT refreshed (see $LOG_A)"
fi
if [ "$( _sha "$A/docs/BRANCH-PROTECTION.md" )" = "$( _sha "$REPO_ROOT/templates/docs/BRANCH-PROTECTION.md" )" ]; then
  ok "H.3b docs/BRANCH-PROTECTION.md now byte-identical to the framework source"
else
  bad "H.3b docs/BRANCH-PROTECTION.md differs from templates/docs/BRANCH-PROTECTION.md after the upgrade"
fi

# H.4 — the adopter's own edit survived, byte for byte.
if [ "$( _sha "$A/docs/rotation-log.md" )" = "$ADOPTER_SHA" ]; then
  ok "H.4 adopter-modified docs/rotation-log.md PRESERVED byte-identical"
else
  bad "H.4 docs/rotation-log.md was overwritten — the ownership ladder took an adopter file"
fi
if grep -q 'PRESERVED adopter-modified docs/rotation-log\.md' "$LOG_A"; then
  ok "H.4b the preservation was announced, not silent"
else
  bad "H.4b no PRESERVED line for docs/rotation-log.md — a silent preserve is indistinguishable from a skipped route"
fi

# H.5 — the INFERENCE was not persisted.
PERSISTED="$( python3 - "$A/.claude/.install-state.json" <<'PY' 2>/dev/null || true
import json, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        d = json.load(f)
except Exception:
    print("NOSTATE"); raise SystemExit(0)
req = d.get("request") or {}
print(repr(req.get("ceremony", None)))
PY
)"
case "$PERSISTED" in
  "None"|"''"|'""'|"NOSTATE")
    ok "H.5 the inferred ceremony was NOT persisted (state ceremony=$PERSISTED)" ;;
  *)
    bad "H.5 the state file now records ceremony=$PERSISTED — an INFERENCE was persisted; one missed migration becomes permanent (upgrade.sh:801-803)" ;;
esac

# H.6 — CODEOWNERS exclusivity: no handle recorded => the .template branch, and
# NEVER both files on disk.
if grep -q 'SKIPPED (branch not taken): \.github/CODEOWNERS ' "$LOG_A"; then
  ok "H.6 .github/CODEOWNERS skipped (no recorded --github-owner)"
else
  bad "H.6 the rendered CODEOWNERS route was not skipped although no handle is recorded"
fi
if [ -e "$A/.github/CODEOWNERS" ] && [ -e "$A/.github/CODEOWNERS.template" ]; then
  bad "H.6b BOTH .github/CODEOWNERS and .github/CODEOWNERS.template exist — the two routes are mutually exclusive per run (install.sh:1551 elif vs :1563 else)"
else
  ok "H.6b exactly one of CODEOWNERS / CODEOWNERS.template on disk"
fi

# Summary line + conservation.
S_ROUTES="$( _summary_field "$LOG_A" routes )"
S_INST="$(   _summary_field "$LOG_A" installed )"
S_REFR="$(   _summary_field "$LOG_A" refreshed )"
S_IDEN="$(   _summary_field "$LOG_A" identical )"
S_PRES="$(   _summary_field "$LOG_A" preserved )"
S_SKIP="$(   _summary_field "$LOG_A" skipped )"
if [ -n "$S_ROUTES" ]; then
  ok "H.1b the summary line is present: routes=$S_ROUTES installed=$S_INST refreshed=$S_REFR identical=$S_IDEN preserved=$S_PRES skipped=$S_SKIP"
else
  bad "H.1b no 'docs/.github delivery: routes=...' summary line in $LOG_A"
fi
if [ "${S_ROUTES:-0}" = "$EXPECTED_ROUTES" ]; then
  ok "H.1c the delivery enumerated all $EXPECTED_ROUTES routes (0 would be a vacuous pass, AC-9)"
else
  bad "H.1c the delivery enumerated routes=${S_ROUTES:-<absent>}, expected $EXPECTED_ROUTES"
fi
_SUM=$(( ${S_INST:-0} + ${S_REFR:-0} + ${S_IDEN:-0} + ${S_PRES:-0} + ${S_SKIP:-0} ))
if [ "$_SUM" = "${S_ROUTES:-0}" ]; then
  ok "H.1d conservation: every enumerated route reached exactly one verdict ($_SUM)"
else
  bad "H.1d conservation broken: routes=${S_ROUTES:-0} but verdicts sum to $_SUM — a destination fell through the case analysis"
fi
if [ "${S_REFR:-0}" -ge 1 ]; then
  ok "H.3c at least one destination was actually REFRESHED (refreshed=$S_REFR) — the run was not vacuous"
else
  bad "H.3c refreshed=0 — nothing was delivered, so every green above is about files that were already current"
fi

# --- H.16 (rail round-3 F4) the delivered MODE converges to a fresh install's
# Two lanes, because they fail for two different reasons: REFRESHED writes to a
# pre-existing inode (which keeps its mode), IDENTICAL does not write at all.
MODE_NOW_REFRESH="$( ls -l "$A/docs/BRANCH-PROTECTION.md" | cut -c1-10 )"
if [ "$MODE_NOW_REFRESH" = "$MODE_REF_REFRESH" ]; then
  ok "H.16 REFRESHED docs/BRANCH-PROTECTION.md is back at a fresh install's mode ($MODE_REF_REFRESH)"
else
  bad "H.16 docs/BRANCH-PROTECTION.md is $MODE_NOW_REFRESH after the refresh, a fresh install produces $MODE_REF_REFRESH — the bytes were refreshed and the stale mode kept (parity MODE_DIFF is FATAL)"
fi
# rail round-7 F3 changed WHO makes the REFRESH lane converge, and this leg
# moved with it. The write is now atomic — a same-directory temp file whose
# mode is set BEFORE the rename — so the refreshed destination is a NEW inode
# that already carries the fresh-install mode, and the normaliser finds nothing
# to chmod. MEASURED on this very fixture (S327): `REFRESHED (pristine prior
# generation): docs/BRANCH-PROTECTION.md` with NO MODE-NORMALIZED line, and
# H.16 above green on the mode itself. Asserting the line here would be
# asserting a mechanism the cure removed; the PROPERTY (convergence) is H.16,
# and the auditability property lives on the lane where a chmod still happens.
if grep -q 'MODE-NORMALIZED (.*): docs/BRANCH-PROTECTION\.md$' "$LOG_A"; then
  bad "H.16b the REFRESH lane chmod'ed docs/BRANCH-PROTECTION.md after writing it — the atomic write is supposed to land the fresh-install mode on a new inode (see $LOG_A)"
else
  ok "H.16b the REFRESH lane needed NO chmod (the atomic write lands the fresh-install mode), and H.16 shows the mode converged anyway"
fi
if grep -q "IDENTICAL: $MODE_IDENT_PATH\$" "$LOG_A"; then
  ok "H.16c $MODE_IDENT_PATH took the IDENTICAL branch (the lane that never writes)"
else
  bad "H.16c $MODE_IDENT_PATH did not reach the IDENTICAL branch — H.16d below would be testing a different code path than the one this leg is about"
fi
# The IDENTICAL lane never writes, so a chmod IS what converges it — and a
# silent chmod is unauditable. This is where the per-path announcement the
# round-3 F4 cure introduced still has to appear.
if grep -qE "MODE-NORMALIZED \(.*\): $MODE_IDENT_PATH\$" "$LOG_A"; then
  ok "H.16b2 the IDENTICAL lane announces its chmod per path (a silent chmod is unauditable)"
else
  bad "H.16b2 $MODE_IDENT_PATH converged with no MODE-NORMALIZED line — the one lane that must chmod did it silently (see $LOG_A)"
fi
MODE_NOW_IDENT="$( ls -l "$A/$MODE_IDENT_PATH" | cut -c1-10 )"
if [ "$MODE_NOW_IDENT" = "$MODE_REF_IDENT" ]; then
  ok "H.16d IDENTICAL $MODE_IDENT_PATH is back at a fresh install's mode ($MODE_REF_IDENT)"
else
  bad "H.16d $MODE_IDENT_PATH is $MODE_NOW_IDENT, a fresh install produces $MODE_REF_IDENT — identical BYTES were treated as an identical FILE, so the mode can never converge"
fi

# --- H.9 (AC-10) second consecutive upgrade is a no-op ---------------------
echo ""
echo "==> H.9 — a second consecutive upgrade changes nothing (AC-10)"
cp -R "$A/docs" "$WORK/snap-docs"
cp -R "$A/.github" "$WORK/snap-github"
_upgrade "$A" --no-replay
LOG_A2="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_A2" >&2; scaffold "second upgrade returned rc=$_UP_RC"; }
S2_INST="$( _summary_field "$LOG_A2" installed )"
S2_REFR="$( _summary_field "$LOG_A2" refreshed )"
if [ "${S2_INST:-x}" = "0" ] && [ "${S2_REFR:-x}" = "0" ]; then
  ok "H.9 second upgrade: installed=0 refreshed=0"
else
  bad "H.9 second upgrade still wrote: installed=${S2_INST:-<absent>} refreshed=${S2_REFR:-<absent>} — the delivery is not idempotent"
fi
if diff -r "$WORK/snap-docs" "$A/docs" >/dev/null 2>&1; then
  ok "H.9b docs/ byte-identical across the two consecutive upgrades"
else
  bad "H.9b docs/ changed on the second upgrade"
fi
if diff -r "$WORK/snap-github" "$A/.github" >/dev/null 2>&1; then
  ok "H.9c .github/ byte-identical across the two consecutive upgrades"
else
  bad "H.9c .github/ changed on the second upgrade"
fi

# --- H.7 hostile github_owner ---------------------------------------------
echo ""
echo "==> H.7 — a '/'-bearing github_owner in the UNSIGNED state file is refused"
B="$WORK/hostile/adopter"
_install_into "$B"
python3 - "$B/.claude/.install-state.json" <<'PY' || scaffold "could not rewrite the state file for H.7"
import json, sys
p = sys.argv[1]
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)
d["request"]["github_owner"] = "evil/../../../etc"
with open(p, "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2)
PY
_upgrade "$B"
LOG_B="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_B" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the hostile-handle fixture"; }
if grep -q 'CODEOWNERS handle: none recorded' "$LOG_B"; then
  ok "H.7 the malformed handle was REFUSED (treated as 'none recorded'), never interpolated into sed"
else
  bad "H.7 upgrade.sh accepted a github_owner containing '/' — PLAN-183 §9.2 is the 0-byte-CODEOWNERS class, reproduced on a new route"
fi
if grep -qF 'evil/../../../etc' "$LOG_B"; then
  bad "H.7b the malformed handle reached the log — it was used somewhere"
else
  ok "H.7b the malformed handle appears nowhere in the run"
fi

# --- H.8 dangling symlink destination -------------------------------------
echo ""
echo "==> H.8 — a dangling symlink destination is PRESERVED, never written through"
C="$WORK/symlink/adopter"
_install_into "$C"
rm -f "$C/.claude/.install-state.json"
OUTSIDE="$WORK/symlink/OUTSIDE-THE-TARGET.md"
rm -f "$OUTSIDE"
rm -f "$C/docs/BRANCH-PROTECTION.md"
ln -s "$OUTSIDE" "$C/docs/BRANCH-PROTECTION.md"
_upgrade "$C" --no-replay
LOG_C="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_C" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the symlink fixture"; }
if [ -e "$OUTSIDE" ]; then
  bad "H.8 upgrade.sh wrote THROUGH a dangling symlink to $OUTSIDE — outside \$TARGET (PLAN-183 §9.1 class)"
else
  ok "H.8 nothing was written outside \$TARGET through the dangling symlink"
fi
if grep -q 'PRESERVED docs/BRANCH-PROTECTION\.md (destination is a symlink' "$LOG_C"; then
  ok "H.8b the refusal was announced by name"
else
  bad "H.8b no symlink-refusal line for docs/BRANCH-PROTECTION.md — a silent skip and a refusal look the same"
fi

# --- N.1 NEGATIVE control --------------------------------------------------
# Neither install-state nor .framework-version => today's fail-safe stands and
# NOTHING is delivered. Without this leg, "ENABLED" above could simply be
# unconditional.
echo ""
echo "==> N.1 — NEGATIVE control: no install-state AND no marker => no delivery"
D="$WORK/never/adopter"
_install_into "$D"
rm -f "$D/.claude/.install-state.json" "$D/.claude/.framework-version"
# Prove the delivery WOULD have had work to do, so a "0 delivered" cannot be
# mistaken for "everything was already current".
cp "$WORK/gen.candidate" "$D/docs/BRANCH-PROTECTION.md" 2>/dev/null \
  || printf 'stale-marker\n' > "$D/docs/BRANCH-PROTECTION.md"
D_SHA_BEFORE="$( _sha "$D/docs/BRANCH-PROTECTION.md" )"
_upgrade "$D" --no-replay
LOG_D="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_D" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the never-installed fixture"; }
if grep -q 'docs/\.github delivery: DISABLED' "$LOG_D"; then
  ok "N.1 delivery DISABLED with neither install-state nor marker"
else
  bad "N.1 delivery was NOT disabled — the fail-safe default is gone, so the amendment is unconditional"
fi
if [ "$( _sha "$D/docs/BRANCH-PROTECTION.md" )" = "$D_SHA_BEFORE" ]; then
  ok "N.1b the stale destination was left untouched (a real no-delivery, not a silent one)"
else
  bad "N.1b docs/BRANCH-PROTECTION.md was rewritten although delivery reported DISABLED"
fi
if grep -q 'docs/\.github delivery: routes=' "$LOG_D"; then
  bad "N.1c a delivery summary line was emitted on a DISABLED run"
else
  ok "N.1c no delivery summary line on a DISABLED run"
fi

# --- N.2  the ONE-UPGRADE LATENCY, pinned as intended behaviour ------------
# MEASURED S327: `.claude/.framework-version` enters install.sh at v1.3.0
# (`git show v1.2.0:scripts/install.sh | grep -c framework-version` = 0 vs 13
# at v1.3.0). So an adopter who installed at <= v1.2.0 and lost its state has
# NO marker, and the OQ-5 amendment — which reads exactly that marker —
# cannot fire on its FIRST upgrade. That upgrade CREATES the marker
# (_refresh_framework_marker), so the SECOND one delivers.
#
# The latency is deliberate, not an oversight to paper over: creating the
# marker BEFORE the delivery decision would make the evidence self-fulfilling
# — a never-installed directory would acquire the marker and then be treated
# as an adopter, which is precisely what N.1 forbids. Pinned here so a future
# reordering shows up as a CHANGE instead of a silent behaviour shift.
echo ""
echo "==> N.2 — a marker-less adopter is reached on the SECOND upgrade, not the first"
if [ -f "$D/.claude/.framework-version" ]; then
  ok "N.2 the first upgrade CREATED .claude/.framework-version"
  # Blind the state again: the state written by run 1 records no ceremony
  # (the inference is not persisted), but it must not be the reason run 2
  # decides — remove it so the marker is the only evidence, as for a real
  # historical adopter.
  rm -f "$D/.claude/.install-state.json"
  D2_SHA_BEFORE="$( _sha "$D/docs/BRANCH-PROTECTION.md" )"
  _upgrade "$D" --no-replay
  LOG_D2="$_UP_LOG"
  [ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_D2" >&2; scaffold "second upgrade of the marker-less fixture returned rc=$_UP_RC"; }
  if grep -q 'docs/\.github delivery: ENABLED — OQ-5 amendment' "$LOG_D2"; then
    ok "N.2b the second upgrade DOES deliver (the amendment fires once the marker exists)"
  else
    bad "N.2b the second upgrade still did not deliver — the pre-v1.3.0 population is never reached, not merely reached late"
  fi
  if [ "$( _sha "$D/docs/BRANCH-PROTECTION.md" )" != "$D2_SHA_BEFORE" ]; then
    ok "N.2c the stale destination was actually rewritten on the second upgrade"
  else
    bad "N.2c the stale destination is STILL stale after the second upgrade"
  fi
else
  bad "N.2 the first upgrade did not create .claude/.framework-version — a marker-less adopter would never be reached at all"
fi

# --- H.10 --dry-run writes nothing ----------------------------------------
echo ""
echo "==> H.10 — --dry-run previews the delivery and writes nothing"
E="$WORK/dryrun/adopter"
_install_into "$E"
cp "$WORK/gen.candidate" "$E/docs/BRANCH-PROTECTION.md" 2>/dev/null \
  || printf 'stale-marker\n' > "$E/docs/BRANCH-PROTECTION.md"
E_SHA_BEFORE="$( _sha "$E/docs/BRANCH-PROTECTION.md" )"
_upgrade "$E" --dry-run
LOG_E="$_UP_LOG"
if grep -qE '\(dry-run\) would (REFRESH|INSTALL)' "$LOG_E"; then
  ok "H.10 --dry-run announced the delivery it would perform"
else
  bad "H.10 --dry-run printed no would-INSTALL/would-REFRESH line — the preview is blind to this route"
fi
if [ "$( _sha "$E/docs/BRANCH-PROTECTION.md" )" = "$E_SHA_BEFORE" ]; then
  ok "H.10b --dry-run wrote nothing"
else
  bad "H.10b --dry-run MODIFIED docs/BRANCH-PROTECTION.md"
fi

# --- H.11 the delivered CODEOWNERS carries a fresh install's MODE -----------
# MEASURED (S327): `cp` from a mktemp render buffer produces 0600, because
# mktemp creates 0600 and POSIX cp copies the source's permission bits, while
# install.sh's `sed ... > "$dst"` produces 0666 & ~umask (0644 under the usual
# umask 022). Same bytes, different mode — and MODE_DIFF is a FATAL class in
# the parity gate. Comparing against a FRESH INSTALL rather than against a
# hardcoded "0644" is what keeps this assertion true under any umask.
echo ""
echo "==> H.11 — a re-INSTALLED .github/CODEOWNERS gets a fresh install's mode"
F="$WORK/mode/adopter"
_install_into "$F" --github-owner ceotesthandle
if [ ! -f "$F/.github/CODEOWNERS" ]; then
  bad "H.11 the --github-owner install delivered no .github/CODEOWNERS — nothing to compare"
else
  REF_MODE="$( ls -l "$F/.github/CODEOWNERS" | cut -c1-10 )"
  rm -f "$F/.github/CODEOWNERS"
  _upgrade "$F"
  LOG_F="$_UP_LOG"
  [ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_F" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the mode fixture"; }
  if grep -q 'INSTALLED: \.github/CODEOWNERS$' "$LOG_F"; then
    ok "H.11 the deleted .github/CODEOWNERS was re-INSTALLED by the upgrade (rendered route)"
  else
    bad "H.11 the upgrade did not re-install the deleted .github/CODEOWNERS — the rendered route never wrote, so the mode check below is vacuous"
  fi
  if [ -f "$F/.github/CODEOWNERS" ]; then
    GOT_MODE="$( ls -l "$F/.github/CODEOWNERS" | cut -c1-10 )"
    if [ "$GOT_MODE" = "$REF_MODE" ]; then
      ok "H.11b delivered mode $GOT_MODE matches a fresh install's"
    else
      bad "H.11b delivered mode is $GOT_MODE but a fresh install produces $REF_MODE — same bytes, different mode (MODE_DIFF is FATAL in the parity gate)"
    fi
    if cmp -s "$F/.github/CODEOWNERS" "$WORK/cache/_INSTALL_CACHE_OWNER/adopter/.github/CODEOWNERS" 2>/dev/null; then
      ok "H.11c delivered bytes are byte-identical to the install's rendering"
    else
      bad "H.11c the upgrade rendered DIFFERENT bytes than install.sh does for the same handle"
    fi
  else
    bad "H.11b .github/CODEOWNERS is still missing after the upgrade"
  fi
fi

# --- H.12 (rail round-1 F5) an UNCLAIMED rendered CODEOWNERS suppresses the
# --- .template route, on the first upgrade AND on the second ---------------
# The shape H.6 cannot reach: fixture (a) was installed WITHOUT a handle, so
# it never had a rendered .github/CODEOWNERS at all. Here the adopter HAS one
# — installed with a handle — and then loses the install-state, so this run
# cannot reconstruct or claim it. Pre-cure the CODEOWNERS route answered
# `PRESERVED (unclaimed)` (file stays) and the .template route STILL installed,
# leaving both mutually exclusive files on disk permanently: the next upgrade
# finds the template IDENTICAL and never removes it, which is why the second
# upgrade is asserted too.
echo ""
echo "==> H.12 — unclaimed rendered CODEOWNERS: the .template route is suppressed"
G="$WORK/unclaimed/adopter"
_install_into "$G" --github-owner ceotesthandle
[ -f "$G/.github/CODEOWNERS" ] || scaffold "H.12 fixture: the --github-owner install delivered no .github/CODEOWNERS"
[ -e "$G/.github/CODEOWNERS.template" ] && scaffold "H.12 fixture: install delivered BOTH CODEOWNERS files — the fixture is already the defect"
rm -f "$G/.claude/.install-state.json"
CO_SHA_BEFORE="$( _sha "$G/.github/CODEOWNERS" )"
_upgrade "$G" --no-replay
LOG_G="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_G" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the unclaimed-CODEOWNERS fixture"; }

if grep -q 'PRESERVED (unclaimed): \.github/CODEOWNERS' "$LOG_G"; then
  ok "H.12 the rendered .github/CODEOWNERS was PRESERVED as unclaimed (no recoverable handle)"
else
  bad "H.12 no 'PRESERVED (unclaimed)' line for .github/CODEOWNERS — the fixture did not reach the branch this leg is about (see $LOG_G)"
fi
if grep -q 'SKIPPED (CODEOWNERS present): \.github/CODEOWNERS\.template' "$LOG_G"; then
  ok "H.12b the .template route was suppressed BY NAME (a silent skip and a suppression look alike)"
else
  bad "H.12b .github/CODEOWNERS.template was not suppressed although a rendered CODEOWNERS is on disk"
fi
if [ -e "$G/.github/CODEOWNERS" ] && [ -e "$G/.github/CODEOWNERS.template" ]; then
  bad "H.12c BOTH .github/CODEOWNERS and .github/CODEOWNERS.template are on disk — no install ever produces that pair (rail round-1 F5)"
elif [ -e "$G/.github/CODEOWNERS" ]; then
  ok "H.12c exactly ONE of the two exists after the upgrade (.github/CODEOWNERS, preserved)"
else
  bad "H.12c the rendered .github/CODEOWNERS disappeared — an unclaimed file must be PRESERVED, never removed"
fi
if [ "$( _sha "$G/.github/CODEOWNERS" )" = "$CO_SHA_BEFORE" ]; then
  ok "H.12d the unclaimed .github/CODEOWNERS is byte-identical to before the upgrade"
else
  bad "H.12d the unclaimed .github/CODEOWNERS was rewritten — ownership was unprovable, so it had to be left alone"
fi
# The permanence half: a second upgrade must not accumulate the template either.
_upgrade "$G" --no-replay
LOG_G2="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_G2" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the second unclaimed-CODEOWNERS upgrade"; }
if [ -e "$G/.github/CODEOWNERS" ] && [ -e "$G/.github/CODEOWNERS.template" ]; then
  bad "H.12e the SECOND upgrade produced the mutually exclusive pair — the suppression is not idempotent"
else
  ok "H.12e still exactly one of the two after a second consecutive upgrade"
fi

# --- H.13 (rail round-1 F2) a poisoned route table delivers NOTHING --------
# MEASURED pre-cure (S327): a row with dest=../../outside/PWNED.md put 536 real
# bytes at "$TARGET/../../outside/PWNED.md", before any ownership gate. The
# cure has two independent layers and this leg exercises BOTH through the real
# script: the reader drops the row (so routes < table rows) and the AC-9
# precondition then refuses the WHOLE delivery by name.
#
# rail round-6 F3 — the poisoned table now travels as the table of a COPIED
# CHECKOUT (no environment channel exists any more), which is also the shape a
# real tampered/partial checkout has.
echo ""
echo "==> H.13 — a route row that escapes \$TARGET is refused, nothing is written"
H="$WORK/poison/adopter"
_install_into "$H"
rm -f "$H/.claude/.install-state.json"
POISON_TSV="$WORK/poison/routes-hostile.tsv"
{
  printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
  printf '../../PWNED-OUTSIDE.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tescaping destination\n'
  printf 'docs/rotation-log.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tan otherwise valid row\n'
} > "$POISON_TSV"
ESCAPE_TARGET="$WORK/PWNED-OUTSIDE.md"   # $H is $WORK/poison/adopter => ../.. is $WORK
rm -f "$ESCAPE_TARGET"
H_SRC="$WORK/poison/srccopy"
_mk_source_copy "$H_SRC" "$POISON_TSV" \
  || scaffold "H.13 could not build the copied checkout carrying the poisoned table"
cmp -s "$H_SRC/scripts/delivery-routes.tsv" "$POISON_TSV" \
  || scaffold "H.13 the copied checkout does not carry the poisoned table — the leg would measure the shipped one"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H="$H.upgrade.$_UPGRADE_SEQ.log"
_H_RC=0
bash "$H_SRC/scripts/upgrade.sh" "$H" --profile core --no-diff-warn --no-replay > "$LOG_H" 2>&1 || _H_RC=$?

# rail round-2 F2 (second half) — the rc IS an assertion, not scaffolding.
# Pre-cure this run exited 0: the ERROR block printed, docs/ and .github/ went
# undelivered, and `echo $?` said success. A caller that only reads the exit
# code (every CI step, doctor.sh, an adopter's Makefile) could not tell this
# apart from a complete upgrade. Exit 3 is now the contract (upgrade.sh
# --help, "Exit codes"), and it is asserted BY VALUE: rc=0 is the fail-open
# regressing, any other rc means the run died somewhere else and the three
# assertions below would be proving nothing.
if [ "$_H_RC" -eq 3 ]; then
  ok "H.13d the failed precondition reached the CALLER (rc=3), not just the log"
elif [ "$_H_RC" -eq 0 ]; then
  bad "H.13d upgrade.sh exited 0 on a poisoned route table — the precondition failure never reaches a caller that checks only \$? (rail round-2 F2)"
else
  tail -40 "$LOG_H" >&2
  scaffold "upgrade.sh returned rc=$_H_RC on the poisoned-table fixture — expected 3 (precondition) or 0 (pre-cure); this run died for some OTHER reason"
fi
if grep -q 'precondition=FAILED' "$LOG_H"; then
  ok "H.13e the summary line carries precondition=FAILED (the log-only consumer sees it too)"
else
  bad "H.13e the delivery summary in $LOG_H has no 'precondition=FAILED' field — a log reader cannot tell a refused delivery from an empty one"
fi

if [ -e "$ESCAPE_TARGET" ]; then
  bad "H.13 upgrade.sh wrote OUTSIDE \$TARGET through a poisoned route row — $ESCAPE_TARGET exists"
else
  ok "H.13 nothing was written outside \$TARGET ($ESCAPE_TARGET absent)"
fi
if grep -q 'delivery-route row REJECTED (invalid destination)' "$LOG_H"; then
  ok "H.13b the offending row was REJECTED by name (a silent drop is how D3 happened)"
else
  bad "H.13b no 'delivery-route row REJECTED' breadcrumb — the row was dropped silently or not at all"
fi
if grep -q 'PRECONDITION FAILED (rejected route row)' "$LOG_H"; then
  ok "H.13c the whole delivery was refused, not continued with the surviving row"
else
  bad "H.13c the delivery continued after a row was rejected — half-trusting a poisoned table is the silent-continue this leg forbids"
fi

# --- H.13f/g/h (rail round-3 F2) the PERSISTED record must not claim success -
# The rc and the summary line are both EPHEMERAL: the rc is gone the moment the
# caller returns and the log is gone with the terminal. `.install-state.json`
# is the DURABLE record, and pre-cure _write_upgrade_state ran BEFORE the
# deferred exit and hardcoded `result.upgrade_succeeded: true`, so a poisoned
# or missing route table left a permanent audit entry claiming a full upgrade —
# on the very run whose exit code says otherwise. The banner had the same
# split: "Upgrade complete." printed, then exit 3.
STATE_H="$H/.claude/.install-state.json"
if [ ! -f "$STATE_H" ]; then
  bad "H.13f no .install-state.json after the poisoned-table upgrade — the durable record this leg is about was never written (see $LOG_H)"
else
  _h_state="$( python3 - "$STATE_H" <<'PY' 2>/dev/null || true
import io, json, sys
try:
    d = json.load(io.open(sys.argv[1], encoding="utf-8"))
except Exception:
    print("UNPARSEABLE"); raise SystemExit(0)
r = d.get("result", {})
print("%s|%s" % (r.get("upgrade_succeeded"), r.get("route_delivery")))
PY
  )"
  case "$_h_state" in
    False\|failed\(rejected-route-row\))
      ok "H.13f the persisted record says upgrade_succeeded=false + route_delivery=failed(rejected-route-row)" ;;
    True\|*)
      bad "H.13f the persisted record claims upgrade_succeeded=true on a run that exited 3 ($_h_state) — a durable audit entry contradicting its own exit code (rail round-3 F2)" ;;
    *)
      bad "H.13f unexpected result block in $STATE_H: '$_h_state' — expected 'False|failed(rejected-route-row)'" ;;
  esac
fi
if grep -q '^==> Upgrade complete\.' "$LOG_H"; then
  bad "H.13g the run printed 'Upgrade complete.' and then exited 3 — the banner a human reads and the rc a script reads disagree"
else
  ok "H.13g no 'Upgrade complete.' banner on a run that failed its precondition"
fi
if grep -q '^==> Upgrade INCOMPLETE' "$LOG_H"; then
  ok "H.13h the failure banner is printed by name"
else
  bad "H.13h neither banner appeared — a human reading the tail of $LOG_H cannot tell this run from a successful one"
fi

# --- H.14 (rail round-2 F2) a PINNED upgrade still has its route table -----
# The reader resolves the table at SOURCE time out of the tree upgrade.sh was
# invoked from; the readers stat it ~3300 lines later. `--pin <ref>` checks
# the source out at <ref> in between, and the table only exists from aaf32c7
# onwards — so for every supported historical pin the delivery block enumerated
# ZERO routes, printed a precondition error, and exited 0 with docs/ and
# .github/ undelivered. That is precisely the population --pin serves.
#
# The pin is DERIVED, never hardcoded: the newest release tag that does NOT
# carry scripts/delivery-routes.tsv is by construction a tag exhibiting the
# defect, and it keeps being the right tag after the next release.
echo ""
echo "==> H.14 — a pinned upgrade delivers through a SNAPSHOT of the route table"
PIN_TAG=""
while IFS= read -r _t; do
  [ -n "$_t" ] || continue
  # Release tags only. git's `--sort=-v:refname` orders v1.3.0-rc.4 ABOVE
  # v1.3.0 (it has no versionsort.suffix configured here), and an rc is not
  # what an adopter pins to — the population this leg speaks for is the one
  # running a shipped release.
  case "$_t" in *-*) continue ;; esac
  if ! git -C "$REPO_ROOT" cat-file -e "$_t:scripts/delivery-routes.tsv" 2>/dev/null; then
    PIN_TAG="$_t"; break
  fi
done <<PINTAGS
$( git -C "$REPO_ROOT" tag -l 'v[0-9]*' --sort=-v:refname 2>/dev/null || true )
PINTAGS
if [ -z "$PIN_TAG" ]; then
  scaffold "H.14 found no release tag PREDATING scripts/delivery-routes.tsv.
                 Either no v* tags are present in this checkout (in CI they are
                 fetched by the 'Fetch the parity pin tag' step of
                 smoke-install.yml, which also fetches +refs/tags/v*), or every
                 tag already carries the table — in which case this leg has
                 nothing left to prove and must be RETIRED deliberately, never
                 left to pass vacuously."
fi
echo "    derived pin: $PIN_TAG (newest release tag without scripts/delivery-routes.tsv)"

# A --pin run does `git checkout <ref>` INSIDE the framework source, so the
# source has to be a git repo whose tree is clean and whose HEAD is the
# framework UNDER TEST. Built here from two `git archive` extractions inside
# $WORK (mktemp -d): commit 1 = the pinned tree, tagged; commit 2 = HEAD plus
# the working-tree scripts/ this run is actually exercising. No network, and
# nothing outside $WORK is written or committed.
_git_commit_all() {
  ( cd "$1" \
    && git add -A -- . \
    && git -c user.email=ceo-test@example.invalid -c user.name='CEO Test' \
           -c commit.gpgsign=false commit -q -m "$2" ) >/dev/null 2>&1 \
    || scaffold "H.14 could not commit '$2' into the throwaway pin source $1"
}
PIN_SRC="$WORK/pinsrc"
mkdir -p "$PIN_SRC"
( cd "$PIN_SRC" && git init -q ) || scaffold "H.14 git init failed in $PIN_SRC"
git -C "$REPO_ROOT" archive "$PIN_TAG" 2>/dev/null | tar -x -C "$PIN_SRC" \
  || scaffold "H.14 could not extract the $PIN_TAG tree (git archive | tar)"
[ -f "$PIN_SRC/scripts/upgrade.sh" ] || scaffold "H.14 the $PIN_TAG archive has no scripts/upgrade.sh"
[ -f "$PIN_SRC/scripts/delivery-routes.tsv" ] \
  && scaffold "H.14 the derived pin $PIN_TAG DOES carry the route table — the tag derivation is wrong and this leg would be vacuous"
_git_commit_all "$PIN_SRC" "pinned tree @ $PIN_TAG"
( cd "$PIN_SRC" && git tag "$PIN_TAG" ) || scaffold "H.14 could not tag $PIN_TAG in $PIN_SRC"
# Wipe (keeping .git) so HEAD is the tree under test, not a merge of the two.
for _e in "$PIN_SRC"/* "$PIN_SRC"/.[!.]* "$PIN_SRC"/..?*; do
  [ -e "$_e" ] || continue
  case "$( basename "$_e" )" in .git) continue ;; esac
  rm -rf "$_e"
done
git -C "$REPO_ROOT" archive HEAD 2>/dev/null | tar -x -C "$PIN_SRC" \
  || scaffold "H.14 could not extract the HEAD tree into $PIN_SRC"
# The working tree IS the change under test — scripts/ carries the upgrader,
# the route reader and the table together.
cp -R "$REPO_ROOT/scripts/." "$PIN_SRC/scripts/" \
  || scaffold "H.14 could not overlay the working-tree scripts/ into $PIN_SRC"
[ -f "$PIN_SRC/scripts/delivery-routes.tsv" ] || scaffold "H.14 overlay left no route table in $PIN_SRC"
_git_commit_all "$PIN_SRC" "working tree under test"
if [ -n "$( git -C "$PIN_SRC" status --porcelain 2>/dev/null )" ]; then
  scaffold "H.14 the throwaway pin source is not clean — 'git checkout $PIN_TAG' would refuse and the leg would scaffold-fail for the wrong reason"
fi

P="$WORK/pinned/adopter"
_install_into "$P"
[ -f "$P/docs/BRANCH-PROTECTION.md" ] || scaffold "H.14 fixture: install delivered no docs/BRANCH-PROTECTION.md"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_P="$P.upgrade.$_UPGRADE_SEQ.log"
_P_RC=0
bash "$PIN_SRC/scripts/upgrade.sh" "$P" --profile core --no-diff-warn --no-replay \
  --pin "$PIN_TAG" > "$LOG_P" 2>&1 || _P_RC=$?

P_ROUTES="$( _summary_field "$LOG_P" routes )"
if [ "${P_ROUTES:-0}" = "$EXPECTED_ROUTES" ]; then
  ok "H.14 the pinned upgrade enumerated routes=$P_ROUTES (the table survived the $PIN_TAG checkout)"
else
  bad "H.14 pinned upgrade enumerated routes='${P_ROUTES:-<no summary line>}', expected $EXPECTED_ROUTES — the route table did NOT survive the --pin checkout (see $LOG_P)"
fi
if grep -q 'precondition=FAILED' "$LOG_P"; then
  bad "H.14b the pinned upgrade reported a FAILED delivery precondition — this is the rail round-2 F2 finding, unfixed (see $LOG_P)"
else
  ok "H.14b no failed precondition on the pinned run"
fi
if [ "$_P_RC" -eq 0 ]; then
  ok "H.14c the pinned upgrade exited 0"
else
  tail -30 "$LOG_P" >&2
  bad "H.14c pinned upgrade exited rc=$_P_RC (3 = the delivery precondition failed; anything else = it died elsewhere) — see $LOG_P"
fi
if grep -q 'snapshot taken before any --pin checkout' "$LOG_P"; then
  ok "H.14d the run NAMES the snapshot it resolved routes through (a silent mechanism is one nobody can audit)"
else
  bad "H.14d the 'routes enumerated' line does not name the snapshot — either the snapshot was skipped or the breadcrumb was lost (see $LOG_P)"
fi
# Conservation: with SOURCES read out of the pinned tree, a route the pin
# predates must still reach a verdict — by name — instead of vanishing.
P_SEEN=0
for _k in installed refreshed identical preserved skipped; do
  _v="$( _summary_field "$LOG_P" "$_k" )"
  case "${_v:-}" in ''|*[!0-9]*) _v=0 ;; esac
  P_SEEN=$(( P_SEEN + _v ))
done
if [ "$P_SEEN" -eq "$EXPECTED_ROUTES" ]; then
  ok "H.14e every one of the $EXPECTED_ROUTES pinned routes reached exactly one verdict"
else
  bad "H.14e $P_SEEN verdict(s) for $EXPECTED_ROUTES routes on the pinned run — a destination fell through (see $LOG_P)"
fi
if [ -f "$P/docs/BRANCH-PROTECTION.md" ] && [ -f "$P/.github/workflows/validate.yml.template" ]; then
  ok "H.14f the pinned run left real delivered files on disk (docs/ and .github/ both present)"
else
  bad "H.14f docs/ and/or .github/ destinations are missing after the pinned upgrade — routes enumerated but nothing landed"
fi

# --- H.15 (rail round-2 F3) an unrenderable CODEOWNERS transform is refused -
# Pre-cure the CODEOWNERS branch ignored the reader's rc, re-parsed the row for
# its SOURCE only, and applied the OWNER_HANDLE substitution unconditionally.
# The row below is the consequence made visible: it keeps a VALID (confined)
# source but points it at a different template and declares a transformation
# no renderer here implements. Pre-cure that rendered rotation-log bytes into
# .github/CODEOWNERS via the recorded-baseline REFRESH ladder — "bytes contrary
# to the shared route table", exactly as the finding words it.
echo ""
echo "==> H.15 — a CODEOWNERS row with an unsupported transform renders NOTHING"
T="$WORK/badtransform/adopter"
_install_into "$T" --github-owner ceotesthandle
[ -f "$T/.github/CODEOWNERS" ] || scaffold "H.15 fixture: the --github-owner install delivered no .github/CODEOWNERS"
BAD_TSV="$WORK/badtransform/routes-bad-transform.tsv"
mkdir -p "$( dirname "$BAD_TSV" )"
# A COPY of the real table with ONE field changed: same six destinations, so
# routes == rows and the AC-9 precondition stays green — the refusal under test
# is the per-route one, not the whole-table one H.13 covers.
awk -F '\t' 'BEGIN { OFS = "\t" }
  $1 == ".github/CODEOWNERS" && $2 != "src" {
    $2 = "templates/docs/rotation-log.md"
    $3 = "substitute:{{OWNER_HANDLE}}-NOT-A-REAL-TRANSFORM"
  }
  { print }' "$ROUTES" > "$BAD_TSV" || scaffold "H.15 could not write the hostile table copy"
grep -q 'NOT-A-REAL-TRANSFORM' "$BAD_TSV" || scaffold "H.15 the hostile table copy carries no planted transform — the control would be vacuous"
CO_SHA_T="$( _sha "$T/.github/CODEOWNERS" )"
T_SRC="$WORK/badtransform/srccopy"
_mk_source_copy "$T_SRC" "$BAD_TSV" \
  || scaffold "H.15 could not build the copied checkout carrying the bad-transform table"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_T="$T.upgrade.$_UPGRADE_SEQ.log"
_T_RC=0
bash "$T_SRC/scripts/upgrade.sh" "$T" --profile core --no-diff-warn --no-replay > "$LOG_T" 2>&1 || _T_RC=$?
[ "$_T_RC" -eq 0 ] || { tail -40 "$LOG_T" >&2; scaffold "upgrade.sh returned rc=$_T_RC on the bad-transform fixture (the table is well-formed, so the whole-table precondition must NOT fire here)"; }

if grep -q "SKIPPED (unsupported transform 'substitute:{{OWNER_HANDLE}}-NOT-A-REAL-TRANSFORM')" "$LOG_T"; then
  ok "H.15 the unrenderable transform was refused BY NAME (and by its value, so the message cannot go stale)"
else
  bad "H.15 no 'SKIPPED (unsupported transform ...)' line — the row's transform was ignored and the substitution applied anyway (rail round-2 F3, see $LOG_T)"
fi
if [ "$( _sha "$T/.github/CODEOWNERS" )" = "$CO_SHA_T" ]; then
  ok "H.15b .github/CODEOWNERS is byte-identical to before the upgrade (the hostile row pointed at OTHER template bytes)"
else
  bad "H.15b .github/CODEOWNERS was REWRITTEN from a row declaring a transform this upgrader cannot render — bytes contrary to the shared route table"
fi
T_SEEN=0
for _k in installed refreshed identical preserved skipped; do
  _v="$( _summary_field "$LOG_T" "$_k" )"
  case "${_v:-}" in ''|*[!0-9]*) _v=0 ;; esac
  T_SEEN=$(( T_SEEN + _v ))
done
if [ "$T_SEEN" -eq "$EXPECTED_ROUTES" ]; then
  ok "H.15c the refused route still reached a verdict — $T_SEEN of $EXPECTED_ROUTES accounted for"
else
  bad "H.15c $T_SEEN verdict(s) for $EXPECTED_ROUTES routes — the refusal dropped a destination instead of counting it (see $LOG_T)"
fi

# --- H.17 (rail round-3 F5) a DANGLING CODEOWNERS symlink counts as PRESENT -
# `-e` is FALSE for a dangling symlink. A historical adopter with no recorded
# handle and a dangling .github/CODEOWNERS therefore read as "no CODEOWNERS
# here", and the upgrade installed .github/CODEOWNERS.template NEXT TO the
# link — two mutually exclusive surfaces the moment the link target appears,
# permanently (the next upgrade finds the template IDENTICAL and never removes
# it). Fixture: a plain install (which delivers the .template), then the
# .template removed and the CODEOWNERS path occupied by a dangling link, so
# the ONLY thing that decides is the presence test.
echo ""
echo "==> H.17 — a dangling .github/CODEOWNERS symlink suppresses the .template route"
U="$WORK/danglingco/adopter"
_install_into "$U"
rm -f "$U/.claude/.install-state.json"
[ -f "$U/.claude/.framework-version" ] || scaffold "H.17 fixture: marker absent, delivery would be disabled"
rm -f "$U/.github/CODEOWNERS.template"
DANGLE_TARGET="$U/.github/CODEOWNERS.absent-on-purpose"
rm -f "$DANGLE_TARGET" "$U/.github/CODEOWNERS"
ln -s "$DANGLE_TARGET" "$U/.github/CODEOWNERS" || scaffold "H.17 fixture: could not create the dangling symlink"
[ -L "$U/.github/CODEOWNERS" ] || scaffold "H.17 fixture: .github/CODEOWNERS is not a symlink"
[ -e "$U/.github/CODEOWNERS" ] && scaffold "H.17 fixture: the symlink RESOLVES, so it is not dangling and the leg would prove nothing"
_upgrade "$U" --no-replay
LOG_U="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_U" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the dangling-CODEOWNERS fixture"; }

if [ -e "$U/.github/CODEOWNERS.template" ]; then
  bad "H.17 .github/CODEOWNERS.template was installed while the CODEOWNERS path is occupied by a symlink — two active surfaces the moment the link target appears (rail round-3 F5)"
else
  ok "H.17 the .template route was NOT installed next to the dangling CODEOWNERS link"
fi
if grep -q 'SKIPPED (CODEOWNERS path present as symlink): \.github/CODEOWNERS\.template' "$LOG_U"; then
  ok "H.17b the suppression names the SYMLINK as the reason (a plain skip would hide which rule fired)"
else
  bad "H.17b no symlink-specific suppression line for .github/CODEOWNERS.template in $LOG_U"
fi
if [ -L "$U/.github/CODEOWNERS" ] && [ ! -e "$U/.github/CODEOWNERS.template" ]; then
  ok "H.17c exactly ONE CODEOWNERS surface on disk (the adopter's link, untouched)"
else
  bad "H.17c the CODEOWNERS surfaces are not mutually exclusive after the upgrade"
fi
# The link itself must not have been written THROUGH, or the refusal traded one
# defect for a worse one.
if [ -e "$DANGLE_TARGET" ]; then
  bad "H.17d the upgrade wrote THROUGH the dangling link — $DANGLE_TARGET now exists"
else
  ok "H.17d nothing was written through the dangling link"
fi
U_SEEN=0
for _k in installed refreshed identical preserved skipped; do
  _v="$( _summary_field "$LOG_U" "$_k" )"
  case "${_v:-}" in ''|*[!0-9]*) _v=0 ;; esac
  U_SEEN=$(( U_SEEN + _v ))
done
if [ "$U_SEEN" -eq "$EXPECTED_ROUTES" ]; then
  ok "H.17e conservation holds on the symlink fixture — $U_SEEN of $EXPECTED_ROUTES accounted for"
else
  bad "H.17e $U_SEEN verdict(s) for $EXPECTED_ROUTES routes — the suppression dropped a destination instead of counting it (see $LOG_U)"
fi

# --- H.18 (rail round-4 F1) an ownership record needs a DELIVERY ------------
# The baseline manifest is not a list of files that look like ours: it is the
# framework's claim of ownership, and `uninstall.sh:196` walks it and DELETES
# on a SHA match. The registration fallback used to claim any route whose
# bytes happened to equal the framework source, on runs that delivered
# NOTHING. MEASURED pre-cure (S327): an `install --ceremony user` adopter that
# dropped a copy of the framework's docs/BRANCH-PROTECTION.md into its own
# tree came out of the next upgrade with that path recorded (hits=1) under a
# delivery line reading "DISABLED".
#
# What may be claimed on a non-delivering run is what a PREVIOUS run recorded:
# a prior baseline record for the relpath whose digest still matches the bytes
# on disk. Three things have to hold at once, and a test that checked only the
# refusal would be satisfied by a cure that records nothing at all:
#   H.18a  an UNOWNED byte-identical file is NOT claimed        (the finding)
#   H.18b  OWNED paths SURVIVE a non-delivering upgrade         (continuity)
#   H.18c  an adopter EDIT to an owned path drops the claim     (under-claim)
#   H.18d  a delivering upgrade still registers as before       (no regression)
#   H.18e  a FAILED precondition claims nothing at all          (half-trust)
echo ""
echo "==> H.18 — registration requires delivery or prior ownership evidence"

# Sum of manifest records for the 6 declared destinations of $1.
_route_hits() {
  _rh_man="$1/.claude/.install-manifest.sha256"
  _rh_n=0
  [ -f "$_rh_man" ] || { printf '0\n'; return 0; }
  while IFS=$'\t' read -r _rh_dest _rh_rest || [ -n "${_rh_dest:-}" ]; do
    [ -n "${_rh_dest:-}" ] || continue
    case "$_rh_dest" in \#*|dest) continue ;; esac
    _rh_n=$(( _rh_n + $( grep -c "  $_rh_dest\$" "$_rh_man" ) ))
  done < "$ROUTES"
  printf '%s\n' "$_rh_n"
}
# $1=target $2=relpath -> record count for that ONE path. NOT
# `grep -c ... || printf 0`: grep -c ALREADY prints 0 when it matches nothing
# and exits 1, so the `||` would print a SECOND value and every caller would
# read "0 0" (the two-values footgun this repo has paid for before).
_route_hit() {
  _rho_man="$1/.claude/.install-manifest.sha256"
  [ -f "$_rho_man" ] || { printf '0\n'; return 0; }
  _rho_n="$( grep -c "  $2\$" "$_rho_man" )"
  case "${_rho_n:-}" in ''|*[!0-9]*) _rho_n=0 ;; esac
  printf '%s\n' "$_rho_n"
}

V="$WORK/ownership/adopter"
_install_into "$V"
V_BASE="$( _route_hits "$V" )"
if [ "$V_BASE" -ge 5 ]; then
  ok "H.18-control the maintainer install recorded $V_BASE of $EXPECTED_ROUTES routes (the legs below are not vacuous)"
else
  bad "H.18-control the install recorded only $V_BASE route(s) — with nothing owned, 'survives' and 'is refused' are indistinguishable"
fi

# Make the ceremony a RECORDED `user`: delivery is then disabled by design
# (install.sh gives that population nothing either), which is exactly the run
# the fallback used to fire on.
python3 - "$V/.claude/.install-state.json" <<'PY' 2>/dev/null || scaffold "could not blind the ceremony to user"
import io, json, sys
p = sys.argv[1]
d = json.load(io.open(p, encoding="utf-8"))
d.setdefault("request", {})["ceremony"] = "user"
io.open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2))
PY

# The adopter OWNS docs/rotation-log.md: byte-identical to the framework
# template (it came from the install) but with no ownership record. Dropping
# the record is the fixture — a file the framework did not put there is
# indistinguishable from one it did, by bytes alone, which is the whole point.
UNOWNED="docs/rotation-log.md"
V_MAN="$V/.claude/.install-manifest.sha256"
grep -v "  $UNOWNED\$" "$V_MAN" > "$V_MAN.h18" || true
mv "$V_MAN.h18" "$V_MAN"
if cmp -s "$REPO_ROOT/templates/$UNOWNED" "$V/$UNOWNED" && [ "$( _route_hit "$V" "$UNOWNED" )" -eq 0 ]; then
  ok "H.18-control $UNOWNED is byte-identical to the template and UNRECORDED (the coincidence the fallback used to reward)"
else
  bad "H.18-control fixture wrong: byte-identity or the unrecorded state does not hold for $UNOWNED"
fi
OWNED_KEEP="docs/BRANCH-PROTECTION.md"
V_KEEP_BEFORE="$( _route_hit "$V" "$OWNED_KEEP" )"

_upgrade "$V" --no-replay
LOG_V="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_V" >&2; scaffold "upgrade.sh returned rc=$_UP_RC on the ownership fixture"; }
grep -q 'docs/\.github delivery: DISABLED' "$LOG_V" \
  && ok "H.18-control the ceremony=user upgrade delivered NOTHING (the run under test)" \
  || bad "H.18-control the fixture delivered after all — H.18a/b below are about a different run than intended"

if [ "$( _route_hit "$V" "$UNOWNED" )" -eq 0 ]; then
  ok "H.18a a byte-identical but UNOWNED destination is not claimed by a run that delivered nothing"
else
  bad "H.18a $UNOWNED entered the framework manifest on a DISABLED delivery — an adopter file one 'uninstall.sh' away from deletion (rail round-4 F1)"
fi
if [ "$( _route_hit "$V" "$OWNED_KEEP" )" -eq "$V_KEEP_BEFORE" ] && [ "$V_KEEP_BEFORE" -eq 1 ]; then
  ok "H.18b a path with a prior record and matching digest SURVIVES the non-delivering upgrade (ownership continuity)"
else
  bad "H.18b $OWNED_KEEP went from $V_KEEP_BEFORE to $( _route_hit "$V" "$OWNED_KEEP" ) record(s) — the cure is refusing everything, which drops ownership install.sh established"
fi

# The adopter edits an OWNED path: the digest no longer matches what the
# framework recorded, and this run delivered nothing, so it has no evidence
# about the current bytes. Under-claiming is the recoverable direction — the
# next delivering upgrade re-registers it from a real verdict.
printf '\n<!-- adopter edit, H.18c -->\n' >> "$V/$OWNED_KEEP"
_upgrade "$V" --no-replay
LOG_V2="$_UP_LOG"
[ "$_UP_RC" -eq 0 ] || { tail -40 "$LOG_V2" >&2; scaffold "second ownership upgrade returned rc=$_UP_RC"; }
if [ "$( _route_hit "$V" "$OWNED_KEEP" )" -eq 0 ]; then
  ok "H.18c an adopter EDIT to an owned path drops the claim (digest no longer matches the prior record)"
else
  bad "H.18c $OWNED_KEEP is still claimed after an adopter edit — the record is being carried on relpath alone, not on evidence about these bytes"
fi

# No regression on the run that DID deliver: fixture (a), already upgraded
# twice above with delivery ENABLED. The expectation is DERIVED from that
# run's own summary, never a constant: ADR-194 §3 registers
# INSTALLED+REFRESHED+IDENTICAL and excludes PRESERVED/SKIPPED, and fixture
# (a) deliberately carries one adopter-edited destination (H.4, PRESERVED) and
# one unrenderable CODEOWNERS row (H.6, SKIPPED). A hardcoded 5 here was WRONG
# and said so out loud on first run — the number this must equal is whatever
# the delivery verdicts add up to.
A_EXPECT=0
for _k in installed refreshed identical; do
  _v="$( _summary_field "$LOG_A2" "$_k" )"
  case "${_v:-}" in ''|*[!0-9]*) _v=0 ;; esac
  A_EXPECT=$(( A_EXPECT + _v ))
done
A_HITS="$( _route_hits "$A" )"
if [ "$A_EXPECT" -lt 1 ]; then
  bad "H.18d could not derive an expectation from $LOG_A2 (installed+refreshed+identical = 0) — the leg would be vacuous"
elif [ "$A_HITS" -eq "$A_EXPECT" ]; then
  ok "H.18d the DELIVERING fixture registers $A_HITS routes — exactly its installed+refreshed+identical verdicts (PRESERVED/SKIPPED excluded, ADR-194 §3)"
else
  bad "H.18d the delivering fixture registers $A_HITS route(s) but its last delivery reached $A_EXPECT registerable verdict(s) — the manifest and the run's own verdicts disagree"
fi

# A failed precondition claims NOTHING: the destination list is read from the
# very table the run just refused to trust. $H is the poisoned fixture from
# H.13, which exited 3 after refusing the whole delivery.
H_HITS="$( _route_hits "$H" )"
if [ "$H_HITS" -eq 0 ]; then
  ok "H.18e the poisoned-table run recorded ZERO routes — a refused delivery claims nothing"
else
  bad "H.18e the poisoned-table run recorded $H_HITS route(s) — half-trusting a table this run declared untrustworthy (rail round-1 F2, same class)"
fi

# --- H.19 (rail round-5 F3) scratch never lands inside $TARGET -------------
# `mktemp "${TMPDIR:-/tmp}/..."` is outside the target only while the CALLER's
# TMPDIR is. Point TMPDIR at the adopter repository and every scratch file the
# upgrader takes — the route-table snapshot (round-2 F2), the sanitised
# baseline manifest, the CODEOWNERS render buffer — is created INSIDE it, under
# --dry-run too, which contradicts the CLI's no-modification contract. The EXIT
# trap then hides the write from any final-tree comparison; a SIGKILL leaves it
# behind. _up_tmpbase is the ONE answer to "where is scratch?".
echo ""
echo "==> H.19 — TMPDIR inside \$TARGET does not put scratch inside \$TARGET"
G19="$WORK/tmpdir/adopter"
_install_into "$G19"
mkdir -p "$G19/tmp"
_g19_list() { ( cd "$G19" && find . -path ./.git -prune -o -print ) | LC_ALL=C sort; }
G19_BEFORE="$WORK/tmpdir/before.list"
G19_AFTER="$WORK/tmpdir/after.list"
_g19_list > "$G19_BEFORE"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_G19="$G19.upgrade.$_UPGRADE_SEQ.log"
_G19_RC=0
TMPDIR="$G19/tmp" \
  bash "$UPGRADE" "$G19" --profile core --no-diff-warn --no-replay --dry-run \
  > "$LOG_G19" 2>&1 || _G19_RC=$?
_g19_list > "$G19_AFTER"

if grep -q 'snapshot taken before any --pin checkout' "$LOG_G19"; then
  ok "H.19a the run DID take the route snapshot (so the leg below is about where it landed, not about a code path that never ran)"
else
  bad "H.19a no snapshot marker in $LOG_G19 — the delivery block did not run, so H.19b proves nothing"
fi
if diff -q "$G19_BEFORE" "$G19_AFTER" >/dev/null 2>&1; then
  ok "H.19b with TMPDIR=\$TARGET/tmp a --dry-run upgrade left the target byte-for-byte identical in structure (no scratch file appeared)"
else
  bad "H.19b --dry-run with TMPDIR inside the target CREATED paths in it: $( diff "$G19_BEFORE" "$G19_AFTER" | head -5 | tr '\n' ' ' )"
fi
G19_LEFTOVERS="$( ( cd "$G19" && find . -name 'ceo-upgrade-*' -o -name 'ceo-baseline-manifest*' -o -name 'ceo-upg-*' ) | grep -c . )"
[ "$G19_LEFTOVERS" -eq 0 ] \
  && ok "H.19c no ceo-* scratch file survives anywhere under the target" \
  || bad "H.19c $G19_LEFTOVERS ceo-* scratch file(s) left inside the target"

# The MECHANISM, isolated: _up_tmpbase extracted by name, driven with the two
# TMPDIR shapes that matter. The RED is the pre-cure expression evaluated on
# the SAME inputs — no sabotaged copy of upgrade.sh needed to show the
# difference, because the difference IS this one function.
TB_HARNESS="$WORK/tmpdir/tmpbase.sh"
{
  echo 'set -uo pipefail'
  echo 'TARGET="$1"'
  echo 'TMPDIR="$2"'
  sed -n '/^_up_tmpbase() {$/,/^}$/p' "$UPGRADE"
  echo 'printf "cured=%s precure=%s\n" "$( _up_tmpbase )" "${TMPDIR:-/tmp}"'
} > "$TB_HARNESS"
if ! grep -q '^_up_tmpbase() {' "$TB_HARNESS"; then
  bad "H.19d could not extract _up_tmpbase from upgrade.sh (renamed or removed?) — this leg would prove nothing"
else
  G19_ABS="$( cd "$G19" && pwd -P )"
  TB_IN="$( bash "$TB_HARNESS" "$G19" "$G19/tmp" 2>/dev/null )"
  TB_CURED="${TB_IN#cured=}"; TB_CURED="${TB_CURED%% *}"
  TB_PRE="${TB_IN##* precure=}"
  TB_CURED_ABS="$( cd "$TB_CURED" 2>/dev/null && pwd -P )" || TB_CURED_ABS=""
  TB_PRE_ABS="$( cd "$TB_PRE" 2>/dev/null && pwd -P )" || TB_PRE_ABS=""
  case "${TB_PRE_ABS%/}/" in
    "${G19_ABS%/}/"*) ok "H.19d-RED the pre-cure expression \${TMPDIR:-/tmp} resolves INSIDE the target ($TB_PRE_ABS) — the finding reproduces" ;;
    *) bad "H.19d-RED \${TMPDIR:-/tmp} resolved '$TB_PRE_ABS', not under '$G19_ABS' — the RED does not reproduce, so H.19e is not evidence" ;;
  esac
  case "${TB_CURED_ABS%/}/" in
    "${G19_ABS%/}/"*) bad "H.19e _up_tmpbase returned '$TB_CURED_ABS', which is under the target" ;;
    *) ok "H.19e _up_tmpbase returns a base OUTSIDE the target ($TB_CURED_ABS) on the same inputs" ;;
  esac
  # Anti-over-correction: a TMPDIR outside the target must be left alone, or
  # every run would silently ignore the operator's TMPDIR.
  TB_OUT="$( bash "$TB_HARNESS" "$G19" "$WORK" 2>/dev/null )"
  case "$TB_OUT" in
    "cured=$WORK "*) ok "H.19f a TMPDIR OUTSIDE the target is returned unchanged (the cure is not 'always /tmp')" ;;
    *) bad "H.19f _up_tmpbase rewrote a legitimate TMPDIR: got '$TB_OUT', expected cured=$WORK" ;;
  esac
fi

# --- H.20 (rail round-6 F3) the ENVIRONMENT cannot supply the route table --
# The table drives WRITES, so a supplied one is a write primitive. Rounds 1-4
# hardened what a ROW may say; a WELL-FORMED hostile table breaks none of those
# rules — `.git/hooks/pre-commit <- scripts/install.sh` is relative, confined,
# glob-free, and keeps routes == rows. Round 5 gated the supply channel behind
# a test switch; round 6 REMOVED the channel, because both halves of that gate
# (the switch and $TMPDIR) are settable by anyone who can set the table.
#
# Leg (a): a real upgrade with BOTH retired names — and the retired switch —
# planted in the environment. Leg (b), the non-vacuity control: the SAME table
# delivered the only way that works now, as a copied checkout's own table,
# where the delivery DOMAIN (a code constant) refuses the row.
echo ""
echo "==> H.20 — no environment variable can supply upgrade.sh's route table"
J20="$WORK/noswitch/adopter"
_install_into "$J20"
rm -f "$J20/.claude/.install-state.json"
J20_TSV="$WORK/noswitch/routes-wellformed-hostile.tsv"
{
  printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
  printf '.git/hooks/pre-commit\tscripts/install.sh\tidentity\t-\tx\tconfined, relative, hostile\n'
} > "$J20_TSV"
J20_VICTIM="$J20/.git/hooks/pre-commit"
J20_VICTIM_BEFORE="absent"
[ -e "$J20_VICTIM" ] && J20_VICTIM_BEFORE="$( _sha "$J20_VICTIM" )"

_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_J20="$J20.upgrade.$_UPGRADE_SEQ.log"
_J20_RC=0
env CEO_ROUTES_TABLE_OVERRIDE_FOR_TESTS=1 \
    FMS_DELIVERY_ROUTES_TSV="$J20_TSV" \
    _WBM_ROUTES_TSV="$J20_TSV" \
  bash "$UPGRADE" "$J20" --profile core --no-diff-warn --no-replay \
  > "$LOG_J20" 2>&1 || _J20_RC=$?

[ "$_J20_RC" -eq 0 ] \
  && ok "H.20a the upgrade completes normally (rc=0) with a hostile table in the environment — it never took effect" \
  || bad "H.20a upgrade exited $_J20_RC with a hostile table in the environment — expected 0 (the environment must be inert)"
if grep -q "routes enumerated: $EXPECTED_ROUTES of $EXPECTED_ROUTES" "$LOG_J20"; then
  ok "H.20b the run enumerated the SHIPPED table's $EXPECTED_ROUTES routes, not the hostile table's 1"
else
  bad "H.20b the summary does not show '$EXPECTED_ROUTES of $EXPECTED_ROUTES' routes: $( grep -m1 'routes enumerated' "$LOG_J20" )"
fi
grep -q "$J20_TSV" "$LOG_J20" \
  && bad "H.20c the upgrade log NAMES the environment-supplied table — something still reads it" \
  || ok "H.20c the environment-supplied path appears nowhere in the log (the run never looked at it)"
J20_VICTIM_AFTER="absent"
[ -e "$J20_VICTIM" ] && J20_VICTIM_AFTER="$( _sha "$J20_VICTIM" )"
[ "$J20_VICTIM_AFTER" = "$J20_VICTIM_BEFORE" ] \
  && ok "H.20d the hostile destination is untouched ($J20_VICTIM_AFTER)" \
  || bad "H.20d .git/hooks/pre-commit changed from '$J20_VICTIM_BEFORE' to '$J20_VICTIM_AFTER' — the hostile row reached a write"

# Control: the SAME table, as a copied checkout's own. It IS read there, and
# the row is then refused by the delivery domain — so the pair shows H.20a is
# about the CHANNEL, not about a table nobody would have acted on anyway.
J20_SRC="$WORK/noswitch/srccopy"
_mk_source_copy "$J20_SRC" "$J20_TSV" \
  || scaffold "H.20 could not build the copied checkout carrying the hostile table"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_J20B="$J20.upgrade.$_UPGRADE_SEQ.log"
_J20B_RC=0
bash "$J20_SRC/scripts/upgrade.sh" "$J20" --profile core --no-diff-warn --no-replay \
  > "$LOG_J20B" 2>&1 || _J20B_RC=$?
if [ "$_J20B_RC" -eq 3 ] && grep -q 'routes enumerated: 0 of 1' "$LOG_J20B"; then
  ok "H.20e-control as the checkout's OWN table it IS read, and the row is REFUSED by the delivery domain (rc=3, 0 of 1)"
else
  bad "H.20e-control the copied checkout exited $_J20B_RC / '$( grep -m1 'routes enumerated' "$LOG_J20B" )' — expected rc=3 and '0 of 1'; H.20a is then not attributable to the channel"
fi
grep -q 'outside delivery domain' "$LOG_J20B" \
  && ok "H.20f the domain refusal NAMES the row (routes<rows is visible, not silent)" \
  || bad "H.20f no 'outside delivery domain' breadcrumb in $LOG_J20B"
J20_VICTIM_AFTER2="absent"
[ -e "$J20_VICTIM" ] && J20_VICTIM_AFTER2="$( _sha "$J20_VICTIM" )"
if [ "$J20_VICTIM_AFTER2" = "$J20_VICTIM_BEFORE" ]; then
  ok "H.20g even with the table READ, nothing was written at the hostile destination"
else
  bad "H.20g with the table read the hostile row reached a write: '$J20_VICTIM_BEFORE' -> '$J20_VICTIM_AFTER2'"
fi

# --- H.21 (rail round-6 F2) a corrupted HEADER stops the whole delivery -----
# MEASURED pre-cure (S327): with the header row deleted, or its 2nd/3rd column
# names corrupted, the readers consumed the data rows anyway — dests=6, rows=6,
# `routes == rows`, AC-9 satisfied — and the upgrade DELIVERED and exited 0
# from a table whose columns no longer said what they meant. The gate lives in
# the reader now, so this is an end-to-end assertion of that: same six data
# rows, header broken, whole delivery refused by name.
echo ""
echo "==> H.21 — a corrupted route-table header refuses the delivery (F2)"
H21="$WORK/badheader/adopter"
_install_into "$H21"
rm -f "$H21/.claude/.install-state.json"
H21_TSV="$WORK/badheader/routes-bad-header.tsv"
mkdir -p "$( dirname "$H21_TSV" )"
sed 's/^dest	src	transform/dest	SOURCE	xform/' "$ROUTES" > "$H21_TSV"
cmp -s "$H21_TSV" "$ROUTES" \
  && scaffold "H.21 the header corruption was a no-op — the leg would prove nothing"
_h21_rows="$( grep -cE '^(docs|\.github)/' "$H21_TSV" )"
[ "$_h21_rows" -eq "$EXPECTED_ROUTES" ] \
  || scaffold "H.21 the fixture carries $_h21_rows data rows, expected $EXPECTED_ROUTES — a header-only difference is the whole point"
H21_SRC="$WORK/badheader/srccopy"
_mk_source_copy "$H21_SRC" "$H21_TSV" \
  || scaffold "H.21 could not build the copied checkout carrying the header-corrupted table"
H21_DOC_BEFORE="$( _sha "$H21/docs/BRANCH-PROTECTION.md" 2>/dev/null || echo absent )"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H21="$H21.upgrade.$_UPGRADE_SEQ.log"
_H21_RC=0
bash "$H21_SRC/scripts/upgrade.sh" "$H21" --profile core --no-diff-warn --no-replay \
  > "$LOG_H21" 2>&1 || _H21_RC=$?
[ "$_H21_RC" -eq 3 ] \
  && ok "H.21a the corrupted header reached the CALLER as rc=3 (precondition), not a green run" \
  || bad "H.21a upgrade exited $_H21_RC on a header-corrupted table — expected 3; 0 is the pre-cure fail-open (see $LOG_H21)"
grep -q "routes enumerated: 0 of 0" "$LOG_H21" \
  && ok "H.21b ZERO routes enumerated from a table with $EXPECTED_ROUTES intact data rows — the header is a precondition, not decoration" \
  || bad "H.21b '$( grep -m1 'routes enumerated' "$LOG_H21" )' — expected '0 of 0'; any other count means rows were consumed under a header nobody validated"
grep -q "not 'src'/'transform'" "$LOG_H21" \
  && ok "H.21c the refusal names WHICH columns are wrong" \
  || bad "H.21c the log does not name the offending columns (see $LOG_H21)"
grep -q '^==> Upgrade INCOMPLETE' "$LOG_H21" \
  && ok "H.21d the failure banner is printed (the human and the exit code agree)" \
  || bad "H.21d no INCOMPLETE banner on a run that failed its precondition"
H21_DOC_AFTER="$( _sha "$H21/docs/BRANCH-PROTECTION.md" 2>/dev/null || echo absent )"
[ "$H21_DOC_AFTER" = "$H21_DOC_BEFORE" ] \
  && ok "H.21e nothing was delivered (docs/BRANCH-PROTECTION.md unchanged)" \
  || bad "H.21e a delivery happened despite the failed precondition: '$H21_DOC_BEFORE' -> '$H21_DOC_AFTER'"

# --- H.22 (rail round-6 F4) --dry-run PREVIEWS the mode normalisation -------
# Pre-cure, a destination holding the CURRENT framework bytes with a drifted
# mode printed only `IDENTICAL` under --dry-run, while the same code path in a
# real run also chmod'ed and printed MODE-NORMALIZED. A preview that reports
# LESS than the run it previews is not a preview. Fixture: a fresh install (so
# the bytes are current), then chmod 0755 on one delivered file.
echo ""
echo "==> H.22 — --dry-run previews the mode normalisation it would perform"
H22="$WORK/dryrunmode/adopter"
_install_into "$H22"
H22_REL="docs/BRANCH-PROTECTION.md"
[ -f "$H22/$H22_REL" ] || scaffold "H.22 fixture: install delivered no $H22_REL"
chmod 0755 "$H22/$H22_REL" || scaffold "H.22 fixture: chmod failed"
_h22_mode() { stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1" 2>/dev/null || printf ''; }
H22_MODE_BEFORE="$( _h22_mode "$H22/$H22_REL" )"
[ "$H22_MODE_BEFORE" = "755" ] \
  || scaffold "H.22 fixture: mode is '$H22_MODE_BEFORE', expected 755 — the drift the preview must report does not exist"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H22="$H22.upgrade.$_UPGRADE_SEQ.log"
_H22_RC=0
bash "$UPGRADE" "$H22" --profile core --no-diff-warn --no-replay --dry-run \
  > "$LOG_H22" 2>&1 || _H22_RC=$?
[ "$_H22_RC" -eq 0 ] || { tail -30 "$LOG_H22" >&2; scaffold "H.22 dry-run exited $_H22_RC"; }
grep -q "IDENTICAL: $H22_REL" "$LOG_H22" \
  && ok "H.22-control the dry-run took the IDENTICAL branch (bytes current, mode drifted) — the branch the finding names" \
  || bad "H.22-control no 'IDENTICAL: $H22_REL' in the dry-run — the fixture is not on the branch under test (see $LOG_H22)"
if grep -q "would MODE-NORMALIZE (755 -> " "$LOG_H22"; then
  ok "H.22a the dry-run PREVIEWS the chmod it would perform, with both modes named"
else
  bad "H.22a the dry-run reported no prospective mode normalisation — the preview under-reports what a real run would do (see $LOG_H22)"
fi
H22_MODE_AFTER="$( _h22_mode "$H22/$H22_REL" )"
[ "$H22_MODE_AFTER" = "$H22_MODE_BEFORE" ] \
  && ok "H.22b the dry-run did NOT chmod (mode still $H22_MODE_AFTER) — it previewed, it did not act" \
  || bad "H.22b --dry-run CHANGED the mode from $H22_MODE_BEFORE to $H22_MODE_AFTER — a dry run must not touch the target"

# RED: the pre-cure shape, restored by an anchored plant in a COPIED checkout
# (never the real file). The finding IS the first line of the function — an
# early `return 0` under --dry-run — so putting exactly that line back is the
# reproduction, and its count is asserted so the plant cannot rot into a no-op.
H22_RED_SRC="$WORK/dryrunmode/srccopy-red"
if _mk_source_copy "$H22_RED_SRC" "$ROUTES"; then
  awk '/^_up_tpl_normalize_mode\(\) \{$/ {
         print; print "  [ \"${DRY_RUN:-0}\" -eq 0 ] || return 0  # RED-PLANT"; n++; next }
       { print }
       END { if (n != 1) exit 3 }' "$UPGRADE" > "$H22_RED_SRC/scripts/upgrade.sh"
  _h22_plant_rc=$?
  _h22_plants="$( grep -c 'RED-PLANT' "$H22_RED_SRC/scripts/upgrade.sh" 2>/dev/null )" || _h22_plants=0
  if [ "$_h22_plant_rc" -eq 0 ] && [ "$_h22_plants" -eq 1 ] \
     && bash -n "$H22_RED_SRC/scripts/upgrade.sh" 2>/dev/null; then
    ok "H.22-RED-control the pre-cure early return was planted exactly once in the copy (and it still parses)"
  else
    bad "H.22-RED-control plant rc=$_h22_plant_rc count=$_h22_plants — the anchor missed, so H.22-RED proves nothing"
  fi
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H22R="$H22.upgrade.$_UPGRADE_SEQ.log"
  bash "$H22_RED_SRC/scripts/upgrade.sh" "$H22" --profile core --no-diff-warn --no-replay --dry-run \
    > "$LOG_H22R" 2>&1 || true
  if grep -q "IDENTICAL: $H22_REL" "$LOG_H22R" && ! grep -q 'MODE-NORMALIZE' "$LOG_H22R"; then
    ok "H.22-RED pre-cure the SAME dry-run reports only IDENTICAL and no prospective chmod — the finding reproduces"
  else
    bad "H.22-RED the pre-cure copy did not reproduce the under-report (see $LOG_H22R) — H.22a is not evidence of a fix"
  fi
else
  bad "H.22-RED could not build the pre-cure checkout — the positive control did not run"
fi
# The real run then performs exactly what the preview announced.
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H22B="$H22.upgrade.$_UPGRADE_SEQ.log"
_H22B_RC=0
bash "$UPGRADE" "$H22" --profile core --no-diff-warn --no-replay \
  > "$LOG_H22B" 2>&1 || _H22B_RC=$?
[ "$_H22B_RC" -eq 0 ] || { tail -30 "$LOG_H22B" >&2; scaffold "H.22 real run exited $_H22B_RC"; }
grep -q "MODE-NORMALIZED (755 -> " "$LOG_H22B" \
  && ok "H.22c the real run performs the normalisation the dry-run announced (same modes, same wording)" \
  || bad "H.22c the real run did not normalise the mode — the preview promised something the run does not do (see $LOG_H22B)"
H22_MODE_FINAL="$( _h22_mode "$H22/$H22_REL" )"
[ "$H22_MODE_FINAL" != "755" ] \
  && ok "H.22d the real run converged the mode (755 -> $H22_MODE_FINAL)" \
  || bad "H.22d the mode is still 755 after the real run"

# --- H.23 (rail round-7 F2) a SYMLINKED SOURCE delivers foreign bytes -------
# `[ -f ]`, `cp`, `cat` and sha256 all FOLLOW symlinks, so a `templates/...`
# source that is a link to a regular file OUTSIDE the checkout passed every
# lexical gate and the delivered bytes were the outside file's, sha for sha.
# The fixture is the only shape production could take: a DIFFERENT CHECKOUT
# whose templates/ carries the link (which is why _mk_source_copy now copies
# templates/ for real — a symlinked tree would be refused for its own reason
# and the leg would measure nothing).
echo ""
echo "==> H.23 — a symlinked route SOURCE cannot deliver bytes from outside the checkout"
H23="$WORK/srclink/adopter"
_install_into "$H23"
H23_REL="docs/BRANCH-PROTECTION.md"
[ -f "$H23/$H23_REL" ] || scaffold "H.23 fixture: install delivered no $H23_REL"
H23_DST_BEFORE="$( _sha "$H23/$H23_REL" )"

H23_OUT="$WORK/srclink/outside"
mkdir -p "$H23_OUT/docs"
printf 'FOREIGN BYTES — this file lives outside the framework checkout.\n' \
  > "$H23_OUT/foreign.md"
printf 'FOREIGN ANCESTOR BYTES — reached through a symlinked directory.\n' \
  > "$H23_OUT/docs/BRANCH-PROTECTION.md"
H23_FOREIGN_SHA="$( _sha "$H23_OUT/foreign.md" )"
H23_ANC_SHA="$( _sha "$H23_OUT/docs/BRANCH-PROTECTION.md" )"
[ "$H23_FOREIGN_SHA" != "$H23_DST_BEFORE" ] && [ "$H23_ANC_SHA" != "$H23_DST_BEFORE" ] \
  || scaffold "H.23 fixture: the foreign bytes match the delivered ones — the leg could not discriminate"

# $1 = checkout dir, $2 = leaf|ancestor — plant the link in a copied checkout.
_h23_plant_link() {
  _mk_source_copy "$1" "$ROUTES" || return 1
  case "$2" in
    leaf)
      rm -f "$1/templates/docs/BRANCH-PROTECTION.md" || return 1
      ln -s "$H23_OUT/foreign.md" "$1/templates/docs/BRANCH-PROTECTION.md" || return 1
      [ -L "$1/templates/docs/BRANCH-PROTECTION.md" ] || return 1 ;;
    ancestor)
      rm -rf "$1/templates/docs" || return 1
      ln -s "$H23_OUT/docs" "$1/templates/docs" || return 1
      [ -L "$1/templates/docs" ] || return 1 ;;
  esac
  return 0
}

H23_RED_SRC="$WORK/srclink/srccopy-red"
if _h23_plant_link "$H23_RED_SRC" leaf; then
  # RED = the pre-cure shape: no source-confinement gate at all. Restored by an
  # anchored plant in the COPY (never the real file), count asserted.
  awk '/^_up_src_confined_refuses\(\) \{$/ {
         print; print "  return 1  # RED-PLANT (pre-cure: no source confinement)"; n++; next }
       { print }
       END { if (n != 1) exit 3 }' "$UPGRADE" > "$H23_RED_SRC/scripts/upgrade.sh"
  _h23_prc=$?
  _h23_plants="$( grep -c 'RED-PLANT (pre-cure: no source confinement)' "$H23_RED_SRC/scripts/upgrade.sh" 2>/dev/null )" || _h23_plants=0
  if [ "$_h23_prc" -eq 0 ] && [ "$_h23_plants" -eq 1 ] \
     && bash -n "$H23_RED_SRC/scripts/upgrade.sh" 2>/dev/null; then
    ok "H.23-RED-control the pre-cure shape was planted exactly once in the copy (and it still parses)"
  else
    bad "H.23-RED-control plant rc=$_h23_prc count=$_h23_plants — the anchor missed, so H.23 proves nothing"
  fi
  H23_RED_TGT="$WORK/srclink/adopter-red"
  cp -R "$H23" "$H23_RED_TGT"
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H23R="$H23_RED_TGT.upgrade.$_UPGRADE_SEQ.log"
  bash "$H23_RED_SRC/scripts/upgrade.sh" "$H23_RED_TGT" --profile core --no-diff-warn --no-replay \
    > "$LOG_H23R" 2>&1 || true
  H23_RED_AFTER="$( _sha "$H23_RED_TGT/$H23_REL" 2>/dev/null || echo absent )"
  if [ "$H23_RED_AFTER" = "$H23_FOREIGN_SHA" ]; then
    ok "H.23-RED without the gate the upgrade delivered the OUTSIDE file byte for byte (sha $H23_FOREIGN_SHA) — the escape reproduces"
  else
    bad "H.23-RED the pre-cure copy delivered '$H23_RED_AFTER', expected the foreign '$H23_FOREIGN_SHA' — the finding does not reproduce, so the GREEN below is not evidence"
  fi
else
  bad "H.23-RED could not build the symlinked-source checkout — the positive control did not run"
fi

H23_SRC="$WORK/srclink/srccopy"
if _h23_plant_link "$H23_SRC" leaf; then
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H23="$H23.upgrade.$_UPGRADE_SEQ.log"
  _H23_RC=0
  bash "$H23_SRC/scripts/upgrade.sh" "$H23" --profile core --no-diff-warn --no-replay \
    > "$LOG_H23" 2>&1 || _H23_RC=$?
  H23_DST_AFTER="$( _sha "$H23/$H23_REL" 2>/dev/null || echo absent )"
  [ "$H23_DST_AFTER" = "$H23_DST_BEFORE" ] \
    && ok "H.23a the cured upgrade delivered NOTHING through the symlinked source (destination byte-identical)" \
    || bad "H.23a the destination changed '$H23_DST_BEFORE' -> '$H23_DST_AFTER' (foreign='$H23_FOREIGN_SHA') — the escape is still open"
  grep -q "REFUSED source 'templates/docs/BRANCH-PROTECTION.md'" "$LOG_H23" \
    && ok "H.23b the refusal is NAMED, quoting the offending source relpath" \
    || bad "H.23b no named source refusal in $LOG_H23 — a refusal nobody can see is the D3 silence"
  grep -q "is a symlink" "$LOG_H23" \
    && ok "H.23c the refusal says WHY (symlink component), not just 'refused'" \
    || bad "H.23c the refusal does not name the symlink component (see $LOG_H23)"
  grep -q "PRESERVED $H23_REL" "$LOG_H23" \
    && ok "H.23d the destination is accounted for as PRESERVED (the conservation law still balances)" \
    || bad "H.23d no PRESERVED verdict for $H23_REL (see $LOG_H23)"
  # Scope: the OTHER five routes of the same run are unaffected — this is a
  # per-source refusal, not a delivery-wide abort.
  grep -qE '(INSTALLED|REFRESHED|IDENTICAL): docs/rotation-log\.md' "$LOG_H23" \
    && ok "H.23e the sibling route docs/rotation-log.md still reached a delivery verdict — the refusal is per-source" \
    || bad "H.23e the sibling route got no delivery verdict — one bad source aborted the healthy ones (see $LOG_H23)"
else
  bad "H.23a could not build the cured symlinked-source checkout"
fi

H23_ANC_SRC="$WORK/srclink/srccopy-anc"
if _h23_plant_link "$H23_ANC_SRC" ancestor; then
  H23_ANC_BEFORE="$( _sha "$H23/$H23_REL" )"
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H23A="$H23.upgrade.$_UPGRADE_SEQ.log"
  bash "$H23_ANC_SRC/scripts/upgrade.sh" "$H23" --profile core --no-diff-warn --no-replay \
    > "$LOG_H23A" 2>&1 || true
  H23_ANC_AFTER="$( _sha "$H23/$H23_REL" 2>/dev/null || echo absent )"
  [ "$H23_ANC_AFTER" = "$H23_ANC_BEFORE" ] && [ "$H23_ANC_AFTER" != "$H23_ANC_SHA" ] \
    && ok "H.23f a symlinked ANCESTOR (templates/docs -> outside) delivers nothing either — the per-path lexical checks cannot see it, the physical walk can" \
    || bad "H.23f the ancestor variant changed the destination to '$H23_ANC_AFTER' (foreign ancestor='$H23_ANC_SHA')"
  grep -q "component 'docs' of" "$LOG_H23A" \
    && ok "H.23g the refusal names the ANCESTOR component, not the leaf" \
    || bad "H.23g the ancestor refusal does not name the offending component (see $LOG_H23A)"
else
  bad "H.23f could not build the symlinked-ancestor checkout"
fi

# --- H.24 (rail round-7 F3) a HARD-LINKED destination is an inode escape ----
# _up_tpl_symlink_refuses and _up_tpl_confined_refuses both answer questions
# about the PATH; a hard link is a second NAME for the same inode and neither
# can see it. Pre-cure, `cp`/`cat >` wrote INTO that inode and the file outside
# the target changed. The cure is structural (same-directory temp + rename) and
# the refusal is the named belt on top of it — both are asserted here, and
# separately, so the evidence says WHICH wall is standing.
echo ""
echo "==> H.24 — a hard-linked destination cannot be written through"
H24="$WORK/hardlink/adopter"
_install_into "$H24"
H24_REL="docs/BRANCH-PROTECTION.md"
[ -f "$H24/$H24_REL" ] || scaffold "H.24 fixture: install delivered no $H24_REL"

# A checkout whose template for this route carries a NEW generation, so the
# ownership ladder resolves REFRESH (a write) rather than IDENTICAL (no write).
H24_SRC="$WORK/hardlink/srccopy"
_mk_source_copy "$H24_SRC" "$ROUTES" || scaffold "H.24 could not build the source checkout"
printf '\n<!-- rail round-7 F3 fixture: a newer framework generation -->\n' \
  >> "$H24_SRC/templates/$H24_REL" || scaffold "H.24 could not age the template"
H24_NEW_SHA="$( _sha "$H24_SRC/templates/$H24_REL" )"
[ "$H24_NEW_SHA" != "$( _sha "$H24/$H24_REL" )" ] \
  || scaffold "H.24 fixture: the aged template equals the delivered bytes — no write would be attempted"

# $1 = target dir to prepare. Moves the delivered file OUTSIDE and hard-links
# it back, so the destination path and an outside path share one inode.
H24_OUT="$WORK/hardlink/outside"
mkdir -p "$H24_OUT"
_h24_prepare() {  # $1=target $2=victim name -> echoes the victim path
  mv "$1/$H24_REL" "$H24_OUT/$2" || return 1
  ln "$H24_OUT/$2" "$1/$H24_REL" || return 1
  printf '%s\n' "$H24_OUT/$2"
}

H24_RED_TGT="$WORK/hardlink/adopter-red"
cp -R "$H24" "$H24_RED_TGT"
if H24_RED_VICTIM="$( _h24_prepare "$H24_RED_TGT" victim-red.md )"; then
  H24_RED_BEFORE="$( _sha "$H24_RED_VICTIM" )"
  ok "H.24-control the destination and an OUTSIDE file share one inode (hard link planted)"
  # RED = the pre-cure shape on BOTH walls: the multi-link refusal neutralised
  # AND the atomic write replaced by the direct in-place write it used to be.
  H24_RED_SRC="$WORK/hardlink/srccopy-red"
  _mk_source_copy "$H24_RED_SRC" "$ROUTES" || scaffold "H.24-RED could not build the source checkout"
  cp "$H24_SRC/templates/$H24_REL" "$H24_RED_SRC/templates/$H24_REL" \
    || scaffold "H.24-RED could not carry the aged template into the RED checkout"
  awk '
    /^_up_tpl_multilink_refuses\(\) \{$/ { print; print "  return 1  # RED-PLANT-REFUSAL"; r++; next }
    /^_up_tpl_write\(\) \{$/ {
      print
      print "  # RED-PLANT-WRITE (pre-cure: write straight into the existing inode)"
      print "  if [ -n \"${3:-}\" ]; then cat \"$1\" > \"$2\"; else cp \"$1\" \"$2\"; fi"
      print "  return 0"
      w++; next }
    { print }
    END { if (r != 1 || w != 1) exit 3 }' "$UPGRADE" > "$H24_RED_SRC/scripts/upgrade.sh"
  _h24_prc=$?
  _h24_pr="$( grep -c 'RED-PLANT-REFUSAL' "$H24_RED_SRC/scripts/upgrade.sh" 2>/dev/null )" || _h24_pr=0
  _h24_pw="$( grep -c 'RED-PLANT-WRITE' "$H24_RED_SRC/scripts/upgrade.sh" 2>/dev/null )" || _h24_pw=0
  if [ "$_h24_prc" -eq 0 ] && [ "$_h24_pr" -eq 1 ] && [ "$_h24_pw" -eq 1 ] \
     && bash -n "$H24_RED_SRC/scripts/upgrade.sh" 2>/dev/null; then
    ok "H.24-RED-control both pre-cure shapes planted exactly once each in the copy (and it still parses)"
  else
    bad "H.24-RED-control plant rc=$_h24_prc refusal=$_h24_pr write=$_h24_pw — the anchors missed, so H.24 proves nothing"
  fi
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H24R="$H24_RED_TGT.upgrade.$_UPGRADE_SEQ.log"
  bash "$H24_RED_SRC/scripts/upgrade.sh" "$H24_RED_TGT" --profile core --no-diff-warn --no-replay \
    > "$LOG_H24R" 2>&1 || true
  H24_RED_AFTER="$( _sha "$H24_RED_VICTIM" 2>/dev/null || echo absent )"
  if [ "$H24_RED_AFTER" != "$H24_RED_BEFORE" ] && [ "$H24_RED_AFTER" = "$H24_NEW_SHA" ]; then
    ok "H.24-RED pre-cure the write went THROUGH the shared inode: the file OUTSIDE the target changed to the framework's new bytes — the escape reproduces"
  else
    bad "H.24-RED the outside file went '$H24_RED_BEFORE' -> '$H24_RED_AFTER' (framework bytes '$H24_NEW_SHA') — the finding does not reproduce, so the GREEN below is not evidence"
  fi
else
  bad "H.24-control could not plant the hard link — the positive control did not run"
fi

if H24_VICTIM="$( _h24_prepare "$H24" victim.md )"; then
  H24_BEFORE="$( _sha "$H24_VICTIM" )"
  H24_DST_BEFORE="$( _sha "$H24/$H24_REL" )"
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H24="$H24.upgrade.$_UPGRADE_SEQ.log"
  bash "$H24_SRC/scripts/upgrade.sh" "$H24" --profile core --no-diff-warn --no-replay \
    > "$LOG_H24" 2>&1 || true
  H24_AFTER="$( _sha "$H24_VICTIM" 2>/dev/null || echo absent )"
  [ "$H24_AFTER" = "$H24_BEFORE" ] \
    && ok "H.24a the file OUTSIDE the target is byte-identical after the upgrade" \
    || bad "H.24a the outside file changed '$H24_BEFORE' -> '$H24_AFTER' — the inode escape is still open"
  grep -q "PRESERVED $H24_REL (destination has 2 hard links" "$LOG_H24" \
    && ok "H.24b the refusal is NAMED and reports the link COUNT" \
    || bad "H.24b no named multi-link refusal in $LOG_H24"
  [ "$( _sha "$H24/$H24_REL" 2>/dev/null || echo absent )" = "$H24_DST_BEFORE" ] \
    && ok "H.24c the destination itself was left alone too (refused, not half-written)" \
    || bad "H.24c the destination changed despite the refusal"
else
  bad "H.24a could not plant the hard link on the cured fixture"
fi

# The two walls, separated: with ONLY the refusal neutralised, the ATOMIC write
# still protects the outside file — the write happens, the destination gets the
# new bytes, and the shared inode is detached instead of overwritten. This is
# what makes the cure structural rather than a check somebody can delete.
H24_ATOM_TGT="$WORK/hardlink/adopter-atomic"
# `cp -R` does NOT preserve a hard link whose other name lives outside the
# copied tree, so the copy holds an INDEPENDENT regular file — which is exactly
# what this leg needs before planting its own link.
cp -R "$H24" "$H24_ATOM_TGT"
if H24_ATOM_VICTIM="$( _h24_prepare "$H24_ATOM_TGT" victim-atomic.md )"; then
  H24_ATOM_BEFORE="$( _sha "$H24_ATOM_VICTIM" )"
  H24_ATOM_SRC="$WORK/hardlink/srccopy-atomic"
  _mk_source_copy "$H24_ATOM_SRC" "$ROUTES" || scaffold "H.24d could not build the source checkout"
  cp "$H24_SRC/templates/$H24_REL" "$H24_ATOM_SRC/templates/$H24_REL" \
    || scaffold "H.24d could not carry the aged template"
  awk '/^_up_tpl_multilink_refuses\(\) \{$/ { print; print "  return 1  # RED-PLANT-REFUSAL"; n++; next }
       { print }
       END { if (n != 1) exit 3 }' "$UPGRADE" > "$H24_ATOM_SRC/scripts/upgrade.sh"
  _h24a_prc=$?
  _h24a_n="$( grep -c 'RED-PLANT-REFUSAL' "$H24_ATOM_SRC/scripts/upgrade.sh" 2>/dev/null )" || _h24a_n=0
  [ "$_h24a_prc" -eq 0 ] && [ "$_h24a_n" -eq 1 ] && bash -n "$H24_ATOM_SRC/scripts/upgrade.sh" 2>/dev/null \
    && ok "H.24d-control only the REFUSAL is neutralised in this copy (atomic write intact, still parses)" \
    || bad "H.24d-control plant rc=$_h24a_prc count=$_h24a_n — this leg cannot separate the two walls"
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H24D="$H24_ATOM_TGT.upgrade.$_UPGRADE_SEQ.log"
  bash "$H24_ATOM_SRC/scripts/upgrade.sh" "$H24_ATOM_TGT" --profile core --no-diff-warn --no-replay \
    > "$LOG_H24D" 2>&1 || true
  H24_ATOM_AFTER="$( _sha "$H24_ATOM_VICTIM" 2>/dev/null || echo absent )"
  H24_ATOM_DST="$( _sha "$H24_ATOM_TGT/$H24_REL" 2>/dev/null || echo absent )"
  if [ "$H24_ATOM_AFTER" = "$H24_ATOM_BEFORE" ] && [ "$H24_ATOM_DST" = "$H24_NEW_SHA" ]; then
    ok "H.24d with the refusal removed the ATOMIC write still holds: destination refreshed to the new bytes, outside file untouched"
  else
    bad "H.24d outside '$H24_ATOM_BEFORE' -> '$H24_ATOM_AFTER', destination '$H24_ATOM_DST' (want new '$H24_NEW_SHA') — the structural wall did not carry the case alone"
  fi
else
  bad "H.24d could not plant the hard link for the atomicity leg"
fi

# --- H.25 (rail round-7 F4) --no-replay must reach request.github_owner -----
# The handle is a RECORDED REQUEST field, the same class as profile/stack/
# harness, and --no-replay is the documented opt-out from replaying the
# recorded request. Pre-cure the read was unconditional, so --no-replay still
# rendered .github/CODEOWNERS from the recorded handle.
echo ""
echo "==> H.25 — --no-replay is honoured for request.github_owner"
H25="$WORK/noreplay/adopter"
_install_into "$H25" --github-owner ceotesthandle
[ -f "$H25/.github/CODEOWNERS" ] \
  || scaffold "H.25 fixture: the --github-owner install delivered no .github/CODEOWNERS"
grep -q 'ceotesthandle' "$H25/.github/CODEOWNERS" \
  || scaffold "H.25 fixture: the delivered CODEOWNERS does not carry the recorded handle"
H25_CO_BEFORE="$( _sha "$H25/.github/CODEOWNERS" )"

# Control: WITHOUT --no-replay the handle is still replayed (the option is what
# changes behaviour, not the cure).
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H25C="$H25.upgrade.$_UPGRADE_SEQ.log"
bash "$UPGRADE" "$H25" --profile core --no-diff-warn > "$LOG_H25C" 2>&1 || true
grep -q 'CODEOWNERS handle: @ceotesthandle (recorded install request)' "$LOG_H25C" \
  && ok "H.25-control with replay ON the recorded handle is used (@ceotesthandle)" \
  || bad "H.25-control the default run did not replay the handle (see $LOG_H25C) — the leg below would not be measuring the opt-out"

# RED: the pre-cure shape — the read outside the REPLAY gate.
H25_RED_SRC="$WORK/noreplay/srccopy-red"
if _mk_source_copy "$H25_RED_SRC" "$ROUTES"; then
  awk '/^  if \[ "\$\{REPLAY:-1\}" -eq 1 \]; then$/ { print "  if true; then  # RED-PLANT (pre-cure: unconditional read)"; n++; next }
       { print }
       END { if (n != 1) exit 3 }' "$UPGRADE" > "$H25_RED_SRC/scripts/upgrade.sh"
  _h25_prc=$?
  _h25_n="$( grep -c 'RED-PLANT (pre-cure: unconditional read)' "$H25_RED_SRC/scripts/upgrade.sh" 2>/dev/null )" || _h25_n=0
  if [ "$_h25_prc" -eq 0 ] && [ "$_h25_n" -eq 1 ] && bash -n "$H25_RED_SRC/scripts/upgrade.sh" 2>/dev/null; then
    ok "H.25-RED-control the pre-cure unconditional read was planted exactly once (and it still parses)"
  else
    bad "H.25-RED-control plant rc=$_h25_prc count=$_h25_n — the anchor missed, so H.25 proves nothing"
  fi
  H25_RED_TGT="$WORK/noreplay/adopter-red"
  cp -R "$H25" "$H25_RED_TGT"
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H25R="$H25_RED_TGT.upgrade.$_UPGRADE_SEQ.log"
  bash "$H25_RED_SRC/scripts/upgrade.sh" "$H25_RED_TGT" --profile core --no-diff-warn --no-replay \
    > "$LOG_H25R" 2>&1 || true
  grep -q 'CODEOWNERS handle: @ceotesthandle' "$LOG_H25R" \
    && ok "H.25-RED pre-cure --no-replay STILL loaded the recorded handle — the finding reproduces" \
    || bad "H.25-RED the pre-cure copy did not replay the handle under --no-replay (see $LOG_H25R) — the GREEN below is not evidence"
else
  bad "H.25-RED could not build the pre-cure checkout — the positive control did not run"
fi

_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H25="$H25.upgrade.$_UPGRADE_SEQ.log"
_H25_RC=0
bash "$UPGRADE" "$H25" --profile core --no-diff-warn --no-replay > "$LOG_H25" 2>&1 || _H25_RC=$?
[ "$_H25_RC" -eq 0 ] \
  && ok "H.25a the --no-replay upgrade still succeeds (the opt-out is not an error path)" \
  || bad "H.25a --no-replay exited $_H25_RC (see $LOG_H25)"
grep -q 'CODEOWNERS handle: NOT replayed (--no-replay)' "$LOG_H25" \
  && ok "H.25b the log says the handle was NOT replayed, naming the option responsible" \
  || bad "H.25b no 'NOT replayed' line — the operator cannot see which decision the option made (see $LOG_H25)"
grep -q 'ceotesthandle' "$LOG_H25" \
  && bad "H.25c the recorded handle still appears in a --no-replay run's log (see $LOG_H25)" \
  || ok "H.25c the recorded handle appears NOWHERE in the --no-replay run"
grep -q 'PRESERVED (unclaimed): .github/CODEOWNERS' "$LOG_H25" \
  && ok "H.25d the rendered route resolves PRESERVED (unclaimed) — the same verdict an install without --github-owner produces" \
  || bad "H.25d the rendered CODEOWNERS route took another branch (see $LOG_H25)"
grep -q 'SKIPPED (CODEOWNERS present): .github/CODEOWNERS.template' "$LOG_H25" \
  && ok "H.25e the .template twin stays SKIPPED — the mutual exclusivity invariant survives the opt-out" \
  || bad "H.25e the .template route did not respect exclusivity (see $LOG_H25)"
[ "$( _sha "$H25/.github/CODEOWNERS" )" = "$H25_CO_BEFORE" ] \
  && ok "H.25f .github/CODEOWNERS on disk is byte-identical — nothing was re-rendered" \
  || bad "H.25f .github/CODEOWNERS was rewritten under --no-replay"
[ ! -e "$H25/.github/CODEOWNERS.template" ] \
  && ok "H.25g no second CODEOWNERS surface appeared" \
  || bad "H.25g .github/CODEOWNERS.template was installed next to the rendered file"

# --- H.26 (rail round-7 F3) preview and run agree on the REFRESH lane -------
# round-6 F4's rule is that a preview must not report LESS than the run it
# previews. round-7 F3 moved the mode into the WRITE (atomic replace stages a
# new inode and sets the fresh-install mode before the rename), so the REFRESH
# lane no longer chmods — and a preview announcing a chmod the run does not
# perform is the same defect with the sign flipped. This leg pins BOTH halves
# and the OUTCOME, so neither can drift alone: dry-run silent, run silent, mode
# still converged. Fixture: a destination whose bytes are stale (aged template
# checkout => REFRESH, not IDENTICAL) AND whose mode drifted.
echo ""
echo "==> H.26 — the REFRESH lane previews exactly what it performs (no phantom chmod)"
H26="$WORK/refreshmode/adopter"
_install_into "$H26"
[ -f "$H26/$H24_REL" ] || scaffold "H.26 fixture: install delivered no $H24_REL"
chmod 0755 "$H26/$H24_REL" || scaffold "H.26 fixture: chmod failed"
[ "$( ls -l "$H26/$H24_REL" | cut -c1-10 )" != "$MODE_REF_REFRESH" ] \
  || scaffold "H.26 fixture: the planted mode equals a fresh install's — there is no drift to converge"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H26D="$H26.upgrade.$_UPGRADE_SEQ.log"
bash "$H24_SRC/scripts/upgrade.sh" "$H26" --profile core --no-diff-warn --no-replay --dry-run \
  > "$LOG_H26D" 2>&1 || true
grep -q "would REFRESH .*: $H24_REL" "$LOG_H26D" \
  && ok "H.26-control the dry-run is on the REFRESH lane (the branch this leg is about)" \
  || bad "H.26-control the dry-run did not preview a REFRESH of $H24_REL — the fixture is on another branch (see $LOG_H26D)"
grep -qE "would MODE-NORMALIZE \(.*\): $H24_REL\$" "$LOG_H26D" \
  && bad "H.26a the dry-run announced a chmod the real run no longer performs (see $LOG_H26D)" \
  || ok "H.26a the dry-run announces no chmod on the REFRESH lane"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H26="$H26.upgrade.$_UPGRADE_SEQ.log"
_H26_RC=0
bash "$H24_SRC/scripts/upgrade.sh" "$H26" --profile core --no-diff-warn --no-replay \
  > "$LOG_H26" 2>&1 || _H26_RC=$?
[ "$_H26_RC" -eq 0 ] || { tail -30 "$LOG_H26" >&2; scaffold "H.26 real run exited $_H26_RC"; }
grep -q "REFRESHED .*: $H24_REL" "$LOG_H26" \
  && ok "H.26b the real run REFRESHED the destination" \
  || bad "H.26b the real run did not refresh $H24_REL (see $LOG_H26)"
grep -qE "MODE-NORMALIZED \(.*\): $H24_REL\$" "$LOG_H26" \
  && bad "H.26c the real run chmod'ed after the atomic write — the write is supposed to land the mode itself (see $LOG_H26)" \
  || ok "H.26c the real run performed no chmod either — preview and run agree"
[ "$( _sha "$H26/$H24_REL" )" = "$H24_NEW_SHA" ] \
  && ok "H.26d the destination holds the new framework bytes" \
  || bad "H.26d the destination bytes are not the aged template's — the refresh did not happen"
[ "$( ls -l "$H26/$H24_REL" | cut -c1-10 )" = "$MODE_REF_REFRESH" ] \
  && ok "H.26e and the mode converged to a fresh install's ($MODE_REF_REFRESH) with no chmod in sight — the write set it" \
  || bad "H.26e the mode is $( ls -l "$H26/$H24_REL" | cut -c1-10 ), a fresh install produces $MODE_REF_REFRESH — silence here would mean the drift SURVIVED"

# --- H.27 (S328) the RENDERED route refreshes a PRISTINE PRIOR GENERATION ----
# `.github/CODEOWNERS` is the ONLY rendered destination in the table, and it is
# the only one whose prior-generation evidence has to be MANUFACTURED:
# _up_tpl_generations (upgrade.sh:3714) renders every historical blob through
# the recorded handle BEFORE hashing (:3725-3728), because the bytes on the
# adopter's disk were substituted at install time and exist in no checkout.
# Nothing in this file reached that code with a handle: H.11 DELETES the file
# (INSTALLED lane, no generations consulted), H.12/H.25 have no recoverable
# handle at all (PRESERVED unclaimed), H.15 refuses the row before rendering,
# and H.3/H.24/H.26 exercise the ladder only on VERBATIM templates. So the one
# route whose ownership evidence depends on a substitution had no fixture with
# the power to detect that substitution going away.
#
# MEASURED (S328, this repo): templates/.github/CODEOWNERS.template has exactly
# ONE commit in its history (9777a8d, 2026-06-29) — byte-identical from v1.2.0
# to HEAD. A prior generation therefore cannot be HARVESTED the way H.3 harvests
# one for docs/BRANCH-PROTECTION.md; it has to be PLANTED, in a throwaway git
# history belonging to the COPIED checkout, and the divergence has to be
# ASSERTED (blob_prev != blob_head) rather than assumed — an identical pair
# would silently turn this leg into a restatement of H.11's IDENTICAL lane.
echo ""
echo "==> H.27 — the RENDERED .github/CODEOWNERS refreshes a pristine PRIOR generation"
H27_SRC_REL="templates/.github/CODEOWNERS.template"
H27_HANDLE="ceotesthandle"

# WHICH source renders this destination is answered by the table, never by this
# script: a fixture that plants generations of a file the delivery does not read
# would be green about nothing (the D3 class, PLAN-183 §8).
H27_ROW_SRC="$( awk -F'\t' '$1 == ".github/CODEOWNERS" { print $2; exit }' "$ROUTES" 2>/dev/null )"
[ "${H27_ROW_SRC:-}" = "$H27_SRC_REL" ] \
  || scaffold "H.27 the route table renders .github/CODEOWNERS from '${H27_ROW_SRC:-<no row>}', not '$H27_SRC_REL' —
                 the fixture below would plant generations of a file this delivery never reads"

H27="$WORK/priorgen/adopter"
_install_into "$H27" --github-owner "$H27_HANDLE"
[ -f "$H27/.github/CODEOWNERS" ] \
  || scaffold "H.27 fixture: the --github-owner install delivered no .github/CODEOWNERS"
# install.sh's OWN rendering of the CURRENT template — the oracle for "what the
# upgrade must converge on". Never a sed of ours: that would compare the
# upgrader against a second implementation of the substitution instead of
# against the installer it has to stay in parity with (H.11c, same reason).
H27_HEAD_SHA="$( _sha "$H27/.github/CODEOWNERS" )"

H27_SRC="$WORK/priorgen/srccopy"
_mk_source_copy "$H27_SRC" "$ROUTES" || scaffold "H.27 could not build the source checkout"
# _mk_source_copy SYMLINKS everything but scripts/ and templates/, .git included,
# and _up_tpl_generations resolves history with `git -C "$SOURCE_DIR"`. Left
# alone, that reads the LIVE repository's history — and every commit below would
# land in it. Swap the LINK for a throwaway repo. Guarded on -L, never a blind
# `rm -rf`: a future _mk_source_copy that made .git a real copy would otherwise
# turn this line into a silent delete of framework history.
[ -L "$H27_SRC/.git" ] \
  || scaffold "H.27 expected $H27_SRC/.git to be the symlink _mk_source_copy creates (it is $( [ -e "$H27_SRC/.git" ] && echo 'a real path' || echo absent )) — refusing to touch it"
rm -f "$H27_SRC/.git" || scaffold "H.27 could not detach the symlinked .git"
[ -e "$H27_SRC/.git" ] && scaffold "H.27 .git survived the detach — refusing to git init over it"
( cd "$H27_SRC" && git init -q ) || scaffold "H.27 git init failed in $H27_SRC"

# stderr is kept, not discarded: git DELIBERATELY refuses to read a symlinked
# .gitignore (it reports ELOOP), which is harmless here — one path is staged by
# name — but a real failure must still be readable, so it goes to a log the
# scaffold message names instead of to /dev/null.
H27_GIT_LOG="$WORK/priorgen/git.log"
_h27_commit() {  # $1=message
  git -C "$H27_SRC" add -- "$H27_SRC_REL" >>"$H27_GIT_LOG" 2>&1 \
    || scaffold "H.27 could not stage $H27_SRC_REL in the throwaway history (see $H27_GIT_LOG)"
  git -C "$H27_SRC" -c user.email=ceo-test@example.invalid -c user.name='CEO Test' \
      -c commit.gpgsign=false commit -q -m "$1" >>"$H27_GIT_LOG" 2>&1 \
    || scaffold "H.27 could not commit '$1' into the throwaway history $H27_SRC (see $H27_GIT_LOG)"
}

# Generation 1 — a DIVERGENT prior template that KEEPS the {{OWNER_HANDLE}}
# markers (11 of them, measured). A prior generation without markers would hash
# the same rendered or not, and the RED control below would pass for a reason
# that has nothing to do with the substitution it exists to pin.
H27_PRIOR_TPL="$WORK/priorgen/prior.template"
cp "$REPO_ROOT/$H27_SRC_REL" "$H27_PRIOR_TPL" \
  || scaffold "H.27 could not seed the prior generation from $REPO_ROOT/$H27_SRC_REL"
printf '\n# H.27 fixture: a PRIOR framework generation of this template\n.github/dependabot.yml                  @{{OWNER_HANDLE}}\n' \
  >> "$H27_PRIOR_TPL" || scaffold "H.27 could not age the prior generation"
cp "$H27_PRIOR_TPL" "$H27_SRC/$H27_SRC_REL" || scaffold "H.27 could not stage the prior generation"
_h27_commit "prior generation of $H27_SRC_REL"
H27_BLOB_PREV="$( git -C "$H27_SRC" rev-parse "HEAD:$H27_SRC_REL" 2>/dev/null || true )"
# Generation 2 — the framework's CURRENT bytes, which is both the copy's working
# tree and the target the delivery has to converge on.
cp "$REPO_ROOT/$H27_SRC_REL" "$H27_SRC/$H27_SRC_REL" || scaffold "H.27 could not restore the current generation"
_h27_commit "current generation of $H27_SRC_REL"
H27_BLOB_HEAD="$( git -C "$H27_SRC" rev-parse "HEAD:$H27_SRC_REL" 2>/dev/null || true )"

if [ -n "$H27_BLOB_PREV" ] && [ -n "$H27_BLOB_HEAD" ] && [ "$H27_BLOB_PREV" != "$H27_BLOB_HEAD" ]; then
  ok "H.27-control the copied checkout's history holds TWO DIVERGENT generations of $H27_SRC_REL ($( printf '%s' "$H27_BLOB_PREV" | cut -c1-7 ) != $( printf '%s' "$H27_BLOB_HEAD" | cut -c1-7 ))"
else
  bad "H.27-control blob_prev='${H27_BLOB_PREV:-<none>}' blob_head='${H27_BLOB_HEAD:-<none>}' — an identical or missing pair makes every assertion below a restatement of H.11's IDENTICAL lane"
fi
if cmp -s "$H27_SRC/$H27_SRC_REL" "$REPO_ROOT/$H27_SRC_REL"; then
  ok "H.27-control the copied checkout ships the framework's CURRENT template (the bytes the refresh must land)"
else
  bad "H.27-control $H27_SRC/$H27_SRC_REL is not the framework's current bytes — the leg would measure a convergence onto a fixture, not onto the framework"
fi

# Age the DESTINATION to that prior generation, rendered with the SAME handle —
# the shape of a real historical adopter who installed with an older framework
# and never touched the file. `sed s/{{OWNER_HANDLE}}/<handle>/g` is what
# install.sh:1576 applied then and what _up_tpl_generations:3727 replays now.
H27_PRIOR_RENDER="$WORK/priorgen/prior.rendered"
sed "s/{{OWNER_HANDLE}}/$H27_HANDLE/g" "$H27_PRIOR_TPL" > "$H27_PRIOR_RENDER" \
  || scaffold "H.27 could not render the prior generation for @$H27_HANDLE"
H27_PRIOR_SHA="$( _sha "$H27_PRIOR_RENDER" )"
if [ -n "$H27_PRIOR_SHA" ] && [ "$H27_PRIOR_SHA" != "$H27_HEAD_SHA" ]; then
  ok "H.27-control the RENDERED prior generation differs from install.sh's rendering of the current one — the substitution does not erase the planted divergence"
else
  bad "H.27-control rendered prior '$H27_PRIOR_SHA' equals the install's '$H27_HEAD_SHA' — the divergence vanishes under substitution and the refresh below would have nothing to do"
fi
cp "$H27_PRIOR_RENDER" "$H27/.github/CODEOWNERS" \
  || scaffold "H.27 could not age the destination to the prior generation"

# The RED fixture is snapshotted HERE — after the aging, before any upgrade —
# so both lanes start from byte-identical adopters.
H27_RED_TGT="$WORK/priorgen/adopter-red"
cp -R "$H27" "$H27_RED_TGT" || scaffold "H.27-RED could not snapshot the fixture"

# --- positive control: the pre-cure shape, planted, must REPRODUCE ----------
# RED = generations hashed UNRENDERED. A destination holding a rendered prior
# generation then matches nothing on the ladder and falls to PRESERVED, so the
# adopter never converges. The mutation is planted at the CALLEE rather than at
# the call site for a mechanical reason: the only call site (upgrade.sh:4228)
# sits INSIDE a heredoc, where a `# RED-PLANT` marker would become part of the
# generation LIST instead of a comment. That the two are equivalent is not
# asserted from memory — the handle-passing call site count is MEASURED to be 1.
H27_CALLS="$( grep -c '_up_tpl_generations "\$_udt_src_rel" "\$_udt_handle"' "$UPGRADE" 2>/dev/null )"
case "${H27_CALLS:-}" in ''|*[!0-9]*) H27_CALLS=0 ;; esac
if [ "$H27_CALLS" -eq 1 ]; then
  ok "H.27-RED-control _up_tpl_generations has exactly ONE handle-passing call site — neutralising the callee IS neutralising that call"
else
  bad "H.27-RED-control $H27_CALLS handle-passing call site(s) of _up_tpl_generations (want 1) — the callee plant no longer stands in for the call-site one"
fi
H27_RED_SRC="$WORK/priorgen/srccopy-red"
if cp -R "$H27_SRC" "$H27_RED_SRC"; then
  awk '/^_up_tpl_generations\(\) \{$/ { print; print "  set -- \"$1\" \"\"  # RED-PLANT-NOHANDLE (pre-cure: generations hashed UNRENDERED)"; n++; next }
       { print }
       END { if (n != 1) exit 3 }' "$UPGRADE" > "$H27_RED_SRC/scripts/upgrade.sh"
  _h27_prc=$?
  _h27_pn="$( grep -c 'RED-PLANT-NOHANDLE' "$H27_RED_SRC/scripts/upgrade.sh" 2>/dev/null )" || _h27_pn=0
  if [ "$_h27_prc" -eq 0 ] && [ "$_h27_pn" -eq 1 ] && bash -n "$H27_RED_SRC/scripts/upgrade.sh" 2>/dev/null; then
    ok "H.27-RED-control the pre-cure unrendered-generations shape was planted exactly once (and it still parses)"
  else
    bad "H.27-RED-control plant rc=$_h27_prc count=$_h27_pn — the anchor missed, so the GREEN below is not evidence"
  fi
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  LOG_H27R="$H27_RED_TGT.upgrade.$_UPGRADE_SEQ.log"
  bash "$H27_RED_SRC/scripts/upgrade.sh" "$H27_RED_TGT" --profile core --no-diff-warn \
    > "$LOG_H27R" 2>&1 || true
  if grep -q 'REFRESHED (pristine prior generation): \.github/CODEOWNERS$' "$LOG_H27R"; then
    bad "H.27-RED the pre-cure copy refreshed .github/CODEOWNERS anyway — the finding does not reproduce, so the GREEN below is not evidence"
  elif grep -q 'PRESERVED adopter-modified \.github/CODEOWNERS' "$LOG_H27R"; then
    ok "H.27-RED pre-cure .github/CODEOWNERS falls to PRESERVED adopter-modified: unrendered generations never match a rendered destination — the finding reproduces BY NAME"
  else
    tail -20 "$LOG_H27R" >&2
    bad "H.27-RED the pre-cure run neither refreshed nor preserved .github/CODEOWNERS — it took some third branch (see $LOG_H27R)"
  fi
  if [ "$( _sha "$H27_RED_TGT/.github/CODEOWNERS" 2>/dev/null || echo absent )" = "$H27_PRIOR_SHA" ]; then
    ok "H.27-RED and the stale prior generation is still on disk afterwards — the pre-cure adopter never converges"
  else
    bad "H.27-RED the pre-cure run CHANGED .github/CODEOWNERS — the RED lane is not the shape this leg claims it is"
  fi
else
  bad "H.27-RED could not copy the source checkout — the positive control did not run"
fi

# --- the cured run ---------------------------------------------------------
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H27="$H27.upgrade.$_UPGRADE_SEQ.log"
_H27_RC=0
bash "$H27_SRC/scripts/upgrade.sh" "$H27" --profile core --no-diff-warn > "$LOG_H27" 2>&1 || _H27_RC=$?
[ "$_H27_RC" -eq 0 ] || { tail -40 "$LOG_H27" >&2; scaffold "H.27 upgrade returned rc=$_H27_RC (see $LOG_H27)"; }

grep -q "CODEOWNERS handle: @$H27_HANDLE (recorded install request)" "$LOG_H27" \
  && ok "H.27-control the run replayed the recorded handle — the RENDERED branch is the one under test" \
  || bad "H.27-control the run did not replay @$H27_HANDLE (see $LOG_H27) — everything below would be about the .template branch instead"
grep -q 'REFRESHED (pristine prior generation): \.github/CODEOWNERS$' "$LOG_H27" \
  && ok "H.27a the rendered .github/CODEOWNERS was REFRESHED from a pristine PRIOR generation" \
  || bad "H.27a no 'REFRESHED (pristine prior generation): .github/CODEOWNERS' line — the rendered route cannot recognise its own prior generations (see $LOG_H27)"
[ "$( _sha "$H27/.github/CODEOWNERS" )" = "$H27_HEAD_SHA" ] \
  && ok "H.27b the delivered bytes are byte-identical to install.sh's rendering of the CURRENT template for @$H27_HANDLE" \
  || bad "H.27b the delivered .github/CODEOWNERS is not install.sh's rendering of the current template — the refresh converged somewhere else"

# POSITIVE FIRST, then the negative. `grep -c '{{OWNER_HANDLE}}' = 0` on its own
# is satisfied by an EMPTY file — the 0-byte CODEOWNERS PLAN-183 §9.2 reproduced
# on the install side (debate class C2, W5-b convergence). The handle has to be
# THERE before its absence means anything at all.
H27_HANDLE_HITS="$( grep -c "@$H27_HANDLE" "$H27/.github/CODEOWNERS" 2>/dev/null )"
case "${H27_HANDLE_HITS:-}" in ''|*[!0-9]*) H27_HANDLE_HITS=0 ;; esac
[ "$H27_HANDLE_HITS" -ge 1 ] \
  && ok "H.27c the delivered file NAMES the handle ($H27_HANDLE_HITS line(s) carrying @$H27_HANDLE)" \
  || bad "H.27c the delivered .github/CODEOWNERS carries no @$H27_HANDLE — an empty or truncated file would satisfy H.27d below"
H27_MARKER_HITS="$( grep -c '{{OWNER_HANDLE}}' "$H27/.github/CODEOWNERS" 2>/dev/null )"
case "${H27_MARKER_HITS:-}" in ''|*[!0-9]*) H27_MARKER_HITS=0 ;; esac
[ "$H27_MARKER_HITS" -eq 0 ] \
  && ok "H.27d and no {{OWNER_HANDLE}} marker survived the substitution" \
  || bad "H.27d $H27_MARKER_HITS unsubstituted {{OWNER_HANDLE}} marker(s) in the delivered file — the template was copied, not rendered"

# The manifest record must describe the bytes that were DELIVERED. upgrade.sh
# declares HASH_TARGET for this destination only when the D1 block actually
# registered it (:4763-4764); the continuity lane declares HASH_PRIOR_RECORD and
# would record the digest of the STALE file that was on disk before the refresh.
# Comparing the RECORD against the BYTES is the only way to tell those apart
# from outside — and a wrong record is what uninstall.sh:196 deletes on.
_h27_man_digest() {  # $1=target -> manifest digest for .github/CODEOWNERS ("" if unrecorded)
  _h27m="$1/.claude/.install-manifest.sha256"
  [ -f "$_h27m" ] || { printf ''; return 0; }
  awk '$2 == ".github/CODEOWNERS" { print $1; exit }' "$_h27m" 2>/dev/null
}
H27_MAN="$( _h27_man_digest "$H27" )"
if [ -z "$H27_MAN" ]; then
  bad "H.27e .github/CODEOWNERS has NO record in $H27/.claude/.install-manifest.sha256 — a destination this run refreshed and then declined to claim"
elif [ "$H27_MAN" = "$H27_HEAD_SHA" ]; then
  ok "H.27e the manifest records the digest of the bytes actually DELIVERED (HASH_TARGET, ADR-194 §3)"
else
  bad "H.27e the manifest records $H27_MAN, the delivered file hashes $H27_HEAD_SHA (the stale prior generation hashes $H27_PRIOR_SHA) — the record describes bytes that are not on disk"
fi

# --- and it holds still: a second consecutive upgrade -----------------------
# The stability reference is the state AFTER the first upgrade, not the head
# render: comparing against the head render would make this leg re-assert
# H.27b's convergence and report a CONVERGENCE failure as a STABILITY one.
H27_AFTER1_SHA="$( _sha "$H27/.github/CODEOWNERS" )"
_UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
LOG_H27B="$H27.upgrade.$_UPGRADE_SEQ.log"
_H27B_RC=0
bash "$H27_SRC/scripts/upgrade.sh" "$H27" --profile core --no-diff-warn > "$LOG_H27B" 2>&1 || _H27B_RC=$?
[ "$_H27B_RC" -eq 0 ] || { tail -40 "$LOG_H27B" >&2; scaffold "H.27 second upgrade returned rc=$_H27B_RC (see $LOG_H27B)"; }
grep -q 'IDENTICAL: \.github/CODEOWNERS$' "$LOG_H27B" \
  && ok "H.27f the second upgrade finds .github/CODEOWNERS IDENTICAL — the refresh converged instead of oscillating" \
  || bad "H.27f the second upgrade did not reach the IDENTICAL branch for .github/CODEOWNERS (see $LOG_H27B)"
grep -q 'REFRESHED (pristine prior generation): \.github/CODEOWNERS$' "$LOG_H27B" \
  && bad "H.27g the SECOND upgrade refreshed .github/CODEOWNERS again — the rendered route is not idempotent" \
  || ok "H.27g the second upgrade re-wrote nothing on the rendered route"
[ "$( _sha "$H27/.github/CODEOWNERS" )" = "$H27_AFTER1_SHA" ] \
  && ok "H.27h .github/CODEOWNERS is byte-identical across the two consecutive upgrades" \
  || bad "H.27h .github/CODEOWNERS changed on the second upgrade (was $H27_AFTER1_SHA after the first)"
H27_MAN2="$( _h27_man_digest "$H27" )"
# Same reference discipline as H.27h — and an EMPTY-vs-EMPTY comparison would
# pass vacuously on the very run where H.27e already found no record at all.
if [ -n "$H27_MAN2" ] && [ "$H27_MAN2" = "${H27_MAN:-}" ]; then
  ok "H.27i and the manifest digest is stable across both runs"
else
  bad "H.27i the manifest digest went '${H27_MAN:-<unrecorded>}' -> '${H27_MAN2:-<unrecorded>}' across the two upgrades"
fi

echo ""
echo "=============================================================="
echo "RESULT: $PASS passed, $FAIL failed"
echo "=============================================================="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
