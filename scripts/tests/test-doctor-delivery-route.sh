#!/usr/bin/env bash
# PLAN-183 W5 (S325) — doctor.sh resolves the delivery SOURCE through the
# SHARED route table (scripts/delivery-routes.tsv). Defect D4.
#
# W6 (S327) — doctor stopped OWNING a reader. The route lookup now goes through
# _wbm_route_src in scripts/_framework_manifest_set.sh, the same reader
# install.sh, upgrade.sh and _parity_classify.py use, so this file changed in
# three ways: (1) R.1 extracts the reader from the library, not from doctor,
# and adds anti-rot assertions that no private parser grew back; (2) hostile
# rows (path traversal through the `src` column) are asserted fail-CLOSED at
# the unit AND at the e2e level, with the retired parser recovered from git
# HEAD as the RED leg (R.5/R.6); (3) R.7 covers the new write-site guard.
# The R.2/R.3 fixtures were also repaired: the W5 generator cure now RECORDS
# these destinations, and appending a second record made doctor drop the path
# as ambiguous — see the note at R.2.
#
# What D4 was: doctor.sh resolved every manifest record as "$SOURCE_DIR/$rel",
# which assumes the source relpath EQUALS the destination relpath. That is
# false for every route install.sh delivers from `templates/`. At :507 and
# :553 the consequence is a wrong CLASSIFICATION; at _restore_file it is worse
# — the repair COPIES the wrong bytes, and the post-copy verification
# re-hashes the DESTINATION, so a wrong-source copy that happens to match the
# recorded baseline passes silently.
#
# Why the assertions here observe BYTES, not verdicts: `_restore_file` does not
# classify, it copies. A test that only checked classification would leave the
# wrong-source repair passing. Every repair assertion below compares the
# restored file's digest against BOTH candidate sources and names which one it
# got.
#
# MEASURED LIMIT, recorded so a future reader does not mistake this for full
# coverage: a plain `install.sh` delivers the five routes but records NONE of
# them in `.claude/.install-manifest.sha256` (measured S325: manifest hit
# count = 0 for all of them). That is defect D3/D1, still open and CANONICAL.
# doctor.sh iterates the MANIFEST, so on a stock install these paths are never
# reached and the D4 cure is correct-but-latent. The fixtures below therefore
# append the manifest records D3 fails to write. This is a legitimate fixture
# (the manifest is an input to doctor.sh), and it makes the repair path
# observable TODAY instead of after the canonical ceremony.
#
# bash 3.2-safe. mktemp -d only (never a hardcoded path), so parallel runs
# never collide.
set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
DOCTOR="$SOURCE_DIR/scripts/doctor.sh"
ROUTES="$SOURCE_DIR/scripts/delivery-routes.tsv"

export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-doctor-route-XXXXXX )"
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

# rail round-6 F3 — there is no environment override any more: the library
# resolves its table from the tree it ships in, unconditionally. A doctor.sh
# run therefore takes its fixture the only way a real run could be given one —
# by BEING a different checkout. `_mk_source_copy` builds that checkout.
#
# $1 = directory to build; $2 = the table to install as its
# scripts/delivery-routes.tsv, or the literal NONE for a checkout with NO
# table. Everything except scripts/ is symlinked; scripts/ is a real copy,
# because doctor.sh RESOLVES symlinks to find its own SOURCE_DIR
# (doctor.sh:155-166) — a symlinked doctor.sh would read the REAL repo's table
# and the fixture would measure nothing. That resolution is also why this
# helper cannot be replaced by "symlink everything": it is the reason the R.8
# mirror below always wrote a real doctor.sh.
#
# rail round-7 F2 — templates/ joins scripts/ as a REAL copy: _restore_file now
# requires the SOURCE to be physically confined to the running checkout
# (_wbm_source_confined), and a symlinked templates/ resolves outside it — the
# fixture would measure a refusal instead of the restore under test.
_mk_source_copy() {  # $1=dir $2=table|NONE
  mkdir -p "$1" || return 1
  for _msc_e in "$SOURCE_DIR"/* "$SOURCE_DIR"/.[!.]*; do
    [ -e "$_msc_e" ] || continue
    _msc_b="$( basename "$_msc_e" )"
    case "$_msc_b" in scripts|templates|docs) continue ;; esac
    ln -s "$_msc_e" "$1/$_msc_b" 2>/dev/null || true
  done
  cp -R "$SOURCE_DIR/scripts" "$1/scripts" || return 1
  cp -R "$SOURCE_DIR/templates" "$1/templates" || return 1
  # docs/ is a REAL copy for the same round-7 F2 reason, on the OTHER lane: the
  # identity fallback resolves `$SOURCE_DIR/$rel`, and the D4 reproduction
  # (R.8a) depends on reading the ROOT HOMONYM `docs/BRANCH-PROTECTION.md`.
  # Symlinked, that source resolves into the REAL repo and confinement refuses
  # it — the RED would stop reproducing and the leg would go quietly green for
  # a reason that has nothing to do with D4. A real checkout has ZERO symlinks
  # (measured), so the copy is the faithful fixture, not a workaround. 2.3 MB.
  cp -R "$SOURCE_DIR/docs" "$1/docs" || return 1
  rm -f "$1/scripts/delivery-routes.tsv" || return 1
  if [ "$2" != "NONE" ]; then
    cp "$2" "$1/scripts/delivery-routes.tsv" || return 1
  fi
  return 0
}

ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

_sha() { ( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$1" ); }

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
  t="$( mktemp -d "$WORKROOT/tgt-XXXXXX" )"
  _git_init_retry "$t"
  if ! bash "$SOURCE_DIR/scripts/install.sh" "$t" --profile core >"$t/.install.log" 2>&1; then
    echo "INSTALL_FAILED" >&2
    tail -30 "$t/.install.log" >&2
    return 1
  fi
  printf '%s\n' "$t"
}

# ---------------------------------------------------------------------------
# R.0 — PRECONDITIONS. Every assertion below discriminates "repaired from the
# template" from "repaired from the root homonym". If a pair ever converges,
# the discriminating tests silently stop discriminating and go green while
# blind. So the preconditions are asserted, not assumed.
# ---------------------------------------------------------------------------
echo "==> R.0 — preconditions (a converged pair would make R.2/R.4 vacuous)"

[ -f "$ROUTES" ] && ok "R.0 shared route table exists at scripts/delivery-routes.tsv" \
                 || bad "R.0 shared route table MISSING at $ROUTES"

_r0_pair() {  # $1=template $2=root-homonym $3=label
  local t="$SOURCE_DIR/$1" r="$SOURCE_DIR/$2"
  if [ ! -f "$t" ]; then bad "R.0 $3: template source absent ($1)"; return; fi
  if [ ! -f "$r" ]; then
    ok "R.0 $3: no root homonym (route still meaningful, discrimination trivial)"
    return
  fi
  if [ "$( _sha "$t" )" = "$( _sha "$r" )" ]; then
    bad "R.0 $3: template and root homonym are BYTE-IDENTICAL — every repair assertion below is vacuous"
  else
    ok "R.0 $3: template and root homonym diverge (discrimination is real)"
  fi
}
_r0_pair templates/docs/BRANCH-PROTECTION.md docs/BRANCH-PROTECTION.md "BRANCH-PROTECTION"
_r0_pair templates/docs/rotation-log.md docs/rotation-log.md "rotation-log"
_r0_pair templates/.github/CODEOWNERS.template .github/CODEOWNERS "CODEOWNERS"

# ---------------------------------------------------------------------------
# R.1 — unit: the reader itself. W6 moved WHICH reader that is: doctor no
# longer owns one. The functions are extracted BY NAME from
# _framework_manifest_set.sh and each extraction is asserted, so an upstream
# rename goes RED here instead of leaving the harness with an undefined
# function — which, against a fail-CLOSED reader, would answer rc=2 to
# EVERYTHING and turn six assertions green-for-the-wrong-reason. (That exact
# poisoning happened to the manifest oracle's harness in the S327 rail round;
# this is the same cure applied preventively.)
# ---------------------------------------------------------------------------
echo "==> R.1 — the shared reader resolves each destination"

FMS_LIB="$SOURCE_DIR/scripts/_framework_manifest_set.sh"
FRAG="$WORKROOT/route_reader.sh"
: > "$FRAG"
FRAG_OK=1
# rail round-6 F2 — _wbm_route_table_ok/_wbm_route_table_gate joined the set
# the readers CALL; a fragment without them answers rc=2 to everything.
# rail round-7 F2 — _wbm_source_confined joined the set _restore_refuses CALLS.
# A fragment without it makes the harness die under `set -u` (measured: the
# R.7 legs printed nothing), which reads as "the guard did not refuse".
# PLAN-185-FOLLOWUP FU-7 (S337) — _wbm_dst_refuses (and _wbm_nlink, which it
# calls) joined the set too: _restore_refuses now delegates its DESTINATION
# half to the shared predicate. Measured before this line existed: the R.7
# GREEN leg reported "guard did not refuse (got WROTE)" — an undefined
# function answers non-zero, which the guard reads as "allowed".
for _fn in _wbm_route_relpath_ok _wbm_route_domain_ok _wbm_route_row_ok \
           _wbm_route_table_ok _wbm_route_table_gate _wbm_route_meta \
           _wbm_route_src _wbm_source_confined _wbm_nlink _wbm_dst_refuses; do
  sed -n "/^$_fn() {\$/,/^}\$/p" "$FMS_LIB" >> "$FRAG"
  if grep -q "^$_fn() {\$" "$FRAG"; then
    ok "R.1 $_fn extracted from _framework_manifest_set.sh"
  else
    bad "R.1 could not extract $_fn from _framework_manifest_set.sh (renamed or removed?)"
    FRAG_OK=0
  fi
done

# Anti-rot, W6: the acceptance criterion is ONE reader. A private parser
# growing back in doctor.sh is the defect returning, and it would be invisible
# to every assertion below (they would still pass — against the wrong code).
if grep -qE '^_route_source\(\) \{' "$DOCTOR"; then
  bad "R.1 doctor.sh defines a PRIVATE route parser again (_route_source) — two readers"
else
  ok "R.1 doctor.sh defines no private route parser"
fi
# rail round-5: this leg used to grep EVERY non-comment line, and round 4's own
# named refusal — `echo "       Expected scripts/delivery-routes.tsv next to the
# manifest library," >&2` (doctor.sh:241) — tripped it. MEASURED on the round-4
# tree: 70 passed / 1 failed, the single FAIL being this assertion against a
# diagnostic string. The question the leg exists to ask is whether doctor
# RESOLVES the table path itself; a message printed to an operator does not.
# Diagnostic lines are excluded and the control below proves the narrowed
# pattern still fires on a real resurrection — narrowing a pattern without one
# is how an assertion dies quietly.
_dr_table_code_hits() {  # $1=file -> hits on NON-comment, NON-diagnostic lines
  grep -vE '^[[:space:]]*#' "$1" \
    | grep -vE '^[[:space:]]*(echo|printf|_log)[[:space:]]' \
    | grep -cE 'delivery-routes\.tsv'
}
if [ "$( _dr_table_code_hits "$DOCTOR" )" -ne 0 ]; then
  bad "R.1 doctor.sh resolves the route TABLE path in code — it must go through the reader"
else
  ok "R.1 doctor.sh never touches the route table directly (reader only)"
fi
printf 'DELIVERY_ROUTES_TSV="$SOURCE_DIR/scripts/delivery-routes.tsv"\n' > "$WORKROOT/r1-rot-control.sh"
if [ "$( _dr_table_code_hits "$WORKROOT/r1-rot-control.sh" )" -eq 1 ]; then
  ok "R.1-control the pattern DOES fire on a resurrected private table path (the zero above is not a dead regex)"
else
  bad "R.1-control the pattern missed a planted 'DELIVERY_ROUTES_TSV=.../delivery-routes.tsv' assignment — the anti-rot leg is vacuous"
fi
if grep -q '_wbm_route_src' "$DOCTOR"; then
  ok "R.1 doctor.sh calls the canonical reader (_wbm_route_src)"
else
  bad "R.1 doctor.sh does NOT call _wbm_route_src — route resolution went somewhere else"
fi

if [ "$FRAG_OK" -eq 0 ]; then
  bad "R.1 reader extraction incomplete — the probes below are not trustworthy, skipping them"
else
  HARNESS="$WORKROOT/harness.sh"
  {
    echo 'set -uo pipefail'
    echo "_WBM_ROUTES_TSV=\"$ROUTES\""
    cat "$FRAG"
    echo '_probe() { local rc=0 out; out="$( _wbm_route_src "$1" )" || rc=$?; printf "%s|%s\n" "$rc" "${out:-}"; }'
    echo '_probe "$1"'
  } > "$HARNESS"

  _expect() {  # $1=dest $2=expected "rc|src" $3=label
    local got
    got="$( bash "$HARNESS" "$1" 2>/dev/null )"
    if [ "$got" = "$2" ]; then ok "R.1 $3"; else bad "R.1 $3 — got '$got', want '$2'"; fi
  }
  _expect "docs/BRANCH-PROTECTION.md"  "0|templates/docs/BRANCH-PROTECTION.md"  "docs route -> templates/"
  _expect "docs/rotation-log.md"       "0|templates/docs/rotation-log.md"       "rotation-log -> templates/"
  _expect ".github/workflows/validate.yml.template" \
          "0|templates/.github/workflows/validate.yml.template" \
          ".template suffix survives"
  # The rendered route must NOT resolve to a copyable source: rc=2.
  _expect ".github/CODEOWNERS" "2|" "rendered route reports rc=2 (nothing to copy)"
  # A path with no declared route: identity applies, rc=1, no stdout.
  _expect ".claude/team.md" "1|" "unrouted path -> rc=1 (identity applies)"

  # Malformed rows must be REJECTED, not defaulted to copyable (rail S325
  # P2-1). The dangerous shape is a row for a RENDERED destination whose
  # transform column is missing: defaulting it to `identity` would make
  # doctor restore this repo's live CODEOWNERS into an adopter tree.
  MAL="$WORKROOT/malformed.tsv"
  MAL_HARNESS="$WORKROOT/harness-malformed.sh"
  {
    printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
    printf '.github/CODEOWNERS\t.github/CODEOWNERS\n'
    printf 'docs/a.md\ttemplates/docs/a.md\t\t-\to\tn\n'
    printf 'docs/b.md\t\tidentity\t-\to\tn\n'
    printf 'docs/c.md\ttemplates/docs/c.md\tbogus-transform\t-\to\tn\n'
  } > "$MAL"
  sed "s|^_WBM_ROUTES_TSV=.*|_WBM_ROUTES_TSV=\"$MAL\"|" "$HARNESS" > "$MAL_HARNESS"
  _expect_mal() {  # $1=dest $3=label — anything but rc=0 is acceptable
    local got rc
    got="$( bash "$MAL_HARNESS" "$1" 2>/dev/null )"
    rc="${got%%|*}"
    if [ "$rc" = "0" ]; then
      bad "R.1 malformed row treated as COPYABLE: $2 (got '$got') — fail-open"
    else
      ok "R.1 malformed row rejected: $2 (rc=$rc)"
    fi
  }
  _expect_mal ".github/CODEOWNERS" "rendered dest, transform column missing"
  _expect_mal "docs/a.md"          "transform column empty"
  _expect_mal "docs/b.md"          "identity declared but source empty"
  _expect_mal "docs/c.md"          "unknown transform value"

  # W6 / rail round-1 F2 — HOSTILE rows, the class doctor's retired private
  # parser had no defence against. `malformed` above is an honest mistake;
  # these are a path traversal. doctor's escape vector is the `src` column: it
  # is appended to $SOURCE_DIR and handed to `cp`, so an absolute or
  # `..`-bearing source READS OUTSIDE the framework checkout and delivers those
  # bytes into an adopter tree as framework content. Every one of these must be
  # rc=2 (fail-CLOSED), never rc=0 and never rc=1 — rc=1 is answered by the
  # identity fallback, which puts the caller back on the unvalidated path.
  HOSTILE="$WORKROOT/hostile.tsv"
  HOSTILE_HARNESS="$WORKROOT/harness-hostile.sh"
  {
    printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
    printf 'docs/h1.md\t../../../../etc/passwd\tidentity\t-\to\tabsolute-ish escape via ..\n'
    printf 'docs/h2.md\t/etc/passwd\tidentity\t-\to\tabsolute source\n'
    printf 'docs/h3.md\ttemplates/../../outside/x.md\tidentity\t-\to\tembedded .. segment\n'
    printf '../../outside/PWNED.md\ttemplates/docs/rotation-log.md\tidentity\t-\to\tescaping destination\n'
    printf 'docs/h5.md\t\t\t-\to\tempty source AND empty transform\n'
  } > "$HOSTILE"
  sed "s|^_WBM_ROUTES_TSV=.*|_WBM_ROUTES_TSV=\"$HOSTILE\"|" "$HARNESS" > "$HOSTILE_HARNESS"
  _expect_hostile() {  # $1=dest $2=label — ONLY rc=2 is acceptable
    local got rc
    got="$( bash "$HOSTILE_HARNESS" "$1" 2>/dev/null )"
    rc="${got%%|*}"
    if [ "$rc" = "2" ]; then
      ok "R.1 hostile row rejected fail-CLOSED: $2 (rc=2)"
    else
      bad "R.1 hostile row NOT rejected: $2 (got '$got', want rc=2)"
    fi
  }
  _expect_hostile "docs/h1.md"            "source escapes with ../../../../"
  _expect_hostile "docs/h2.md"            "absolute source"
  _expect_hostile "docs/h3.md"            "source with an embedded .. segment"
  _expect_hostile "../../outside/PWNED.md" "destination escapes the target"
  _expect_hostile "docs/h5.md"            "empty source and empty transform"

  # Anti-over-rejection control: `..` as a SUBSTRING is legitimate in a
  # filename. A predicate that rejected it would be a false positive breaking
  # real routes, so assert the opposite direction too.
  BENIGN="$WORKROOT/benign.tsv"
  BENIGN_HARNESS="$WORKROOT/harness-benign.sh"
  {
    printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
    printf 'docs/a..b.md\ttemplates/docs/a..b.md\tidentity\t-\to\tdots inside a name, not a segment\n'
  } > "$BENIGN"
  sed "s|^_WBM_ROUTES_TSV=.*|_WBM_ROUTES_TSV=\"$BENIGN\"|" "$HARNESS" > "$BENIGN_HARNESS"
  got="$( bash "$BENIGN_HARNESS" "docs/a..b.md" 2>/dev/null )"
  [ "$got" = "0|templates/docs/a..b.md" ] \
    && ok "R.1 'a..b.md' ACCEPTED (rejecting .. by substring would be a false positive)" \
    || bad "R.1 'a..b.md' rejected — got '$got', want '0|templates/docs/a..b.md'"

  # Missing table: rc=2 (fail-CLOSED), never a crash.
  #
  # rail round-6 F2 CHANGED THIS CONTRACT DELIBERATELY, and the change is the
  # cure. It used to be rc=1 — "no row for this destination" — which every
  # caller answers with the identity fallback `$SOURCE_DIR/$rel`. For an ABSENT
  # table that fallback applies to EVERY path, which is defect D4 arriving
  # through a missing file: round 4 F3 had to close it in doctor.sh separately
  # precisely because the reader degraded quietly. "No table" is now one of the
  # ways a table is unusable, and unusable answers 2 in every reader. R.8g
  # measures the consequence end-to-end.
  MISSING_HARNESS="$WORKROOT/harness-missing.sh"
  sed "s|^_WBM_ROUTES_TSV=.*|_WBM_ROUTES_TSV=\"$WORKROOT/absent.tsv\"|" "$HARNESS" > "$MISSING_HARNESS"
  got="$( bash "$MISSING_HARNESS" "docs/BRANCH-PROTECTION.md" 2>/dev/null )"
  [ "$got" = "2|" ] && ok "R.1 absent table -> rc=2 (fail-closed, no crash, no identity fallback)" \
                    || bad "R.1 absent table -> got '$got', want '2|' — rc=1 would send every caller back to \$SOURCE_DIR/\$rel"
fi

# ---------------------------------------------------------------------------
# R.2 — integration: the repair copies the TEMPLATE's bytes, not the root
# homonym's. This is the assertion the whole file exists for.
# ---------------------------------------------------------------------------
echo "==> R.2 — --repair restores from the route's SOURCE (bytes asserted)"

T1="$( fresh_install )" || { bad "R.2 install failed"; T1=""; }
if [ -n "$T1" ]; then
  MAN="$T1/.claude/.install-manifest.sha256"
  REL="docs/BRANCH-PROTECTION.md"
  TPL_SHA="$( _sha "$SOURCE_DIR/templates/$REL" )"
  ROOT_SHA="$( _sha "$SOURCE_DIR/$REL" )"

  # W6 — the fixture the S325 comment asked a future reader to revisit.
  #
  # It used to APPEND the manifest record unconditionally, because D3 recorded
  # none of the routed destinations. The W5 generator cure records them, and a
  # SECOND record for the same relpath is not harmless: doctor treats a
  # duplicate relpath as AMBIGUOUS and drops BOTH copies (the second sanitiser
  # pass in doctor.sh), so the path leaves the run entirely and every assertion
  # below goes vacuous. Measured on this tree before this change: 528 records
  # verified, Missing 0, doctor rc=0 — three FAILs whose cause was the FIXTURE,
  # not the product.
  #
  # So: supply the record only when it is absent, and when it is PRESENT assert
  # the recorded digest is the template's. That turns the old anti-vacuity
  # guard into a stronger claim — it is the D3/D1 cure's own promise (the
  # generator resolved the route SOURCE, not the root homonym) checked here.
  _r2_hits="$( grep -c "  $REL\$" "$MAN" )"
  if [ "$_r2_hits" -eq 0 ]; then
    ok "R.2 precondition: $REL unrecorded by install (pre-D3-cure tree) — fixture supplies the record"
    printf '%s  %s\n' "$TPL_SHA" "$REL" >> "$MAN"
  elif [ "$_r2_hits" -eq 1 ]; then
    ok "R.2 precondition: $REL recorded by install exactly once (D3 cure active)"
    _r2_rec="$( awk -v r="$REL" '$2 == r { print $1 }' "$MAN" )"
    if [ "$_r2_rec" = "$TPL_SHA" ]; then
      ok "R.2 recorded baseline == templates/$REL (generator used the route SOURCE)"
    elif [ "$_r2_rec" = "$ROOT_SHA" ]; then
      bad "R.2 recorded baseline == ROOT homonym — the generator resolved by identity (D3 LIVE)"
    else
      bad "R.2 recorded baseline matches NEITHER source (sha $_r2_rec)"
    fi
  else
    bad "R.2 $REL recorded $_r2_hits times — doctor drops duplicate relpaths; every assertion below would be vacuous"
  fi

  rm -f "$T1/$REL"
  [ ! -e "$T1/$REL" ] && ok "R.2 planted: destination deleted" || bad "R.2 could not delete destination"

  bash "$DOCTOR" "$T1" --repair > "$T1/.repair.log" 2>&1
  R2_RC=$?

  if [ -f "$T1/$REL" ]; then
    GOT="$( _sha "$T1/$REL" )"
    if [ "$GOT" = "$TPL_SHA" ]; then
      ok "R.2 restored bytes == templates/$REL (the delivery source)"
    elif [ "$GOT" = "$ROOT_SHA" ]; then
      bad "R.2 restored bytes == ROOT homonym $REL — D4 is LIVE (repaired with the wrong file)"
    else
      bad "R.2 restored bytes match NEITHER source (sha $GOT)"
    fi
    [ "$( wc -c < "$T1/$REL" | tr -d ' ' )" = "$( wc -c < "$SOURCE_DIR/templates/$REL" | tr -d ' ' )" ] \
      && ok "R.2 restored byte count == template byte count" \
      || bad "R.2 restored byte count != template byte count"
  else
    bad "R.2 file not restored at all (doctor rc=$R2_RC); tail follows"
    tail -15 "$T1/.repair.log" >&2
  fi

  grep -q "RESTORED: $REL" "$T1/.repair.log" \
    && ok "R.2 log reports RESTORED for the routed path" \
    || bad "R.2 log does not report RESTORED for $REL"
fi

# ---------------------------------------------------------------------------
# R.3 — negative control. Revert the route in a COPY of the table and the
# repair must stop landing the template's bytes. Without this, R.2 could pass
# for reasons unrelated to the table.
# ---------------------------------------------------------------------------
echo "==> R.3 — negative control: a reverted route must break R.2"

T3="$( fresh_install )" || { bad "R.3 install failed"; T3=""; }
if [ -n "$T3" ]; then
  REL="docs/BRANCH-PROTECTION.md"
  TPL_SHA="$( _sha "$SOURCE_DIR/templates/$REL" )"
  ROT_SHA="$( _sha "$SOURCE_DIR/templates/docs/rotation-log.md" )"
  # Same duplicate hazard as R.2 — record only if install did not (see R.2).
  if [ "$( grep -c "  $REL\$" "$T3/.claude/.install-manifest.sha256" )" -eq 0 ]; then
    printf '%s  %s\n' "$TPL_SHA" "$REL" >> "$T3/.claude/.install-manifest.sha256"
  fi
  rm -f "$T3/$REL"

  # Sabotage a COPY of the table; the real one is never touched.
  SABOTAGED="$WORKROOT/sabotaged-routes.tsv"
  sed "s|templates/docs/BRANCH-PROTECTION\.md|templates/docs/rotation-log.md|" "$ROUTES" > "$SABOTAGED"
  if cmp -s "$SABOTAGED" "$ROUTES"; then
    bad "R.3 sabotage was a no-op — the control proves nothing"
  else
    ok "R.3 sabotage applied to a table COPY (real table untouched)"
    # rail round-6 F3 — the sabotaged table reaches doctor the only way one
    # can now: as the table of a COPIED checkout. No environment variable is
    # involved, which is also what makes this leg evidence about production.
    R3_SRC="$WORKROOT/src-r3"
    if ! _mk_source_copy "$R3_SRC" "$SABOTAGED"; then
      bad "R.3 could not build the copied checkout carrying the sabotaged table"
    fi
    bash "$R3_SRC/scripts/doctor.sh" "$T3" --repair > "$T3/.sab.log" 2>&1
    if [ -f "$T3/$REL" ] && [ "$( _sha "$T3/$REL" )" = "$TPL_SHA" ]; then
      bad "R.3 repair STILL landed the template bytes with a sabotaged table — doctor.sh is not reading it"
    else
      ok "R.3 sabotaged table changed the outcome (the table is genuinely consulted)"
    fi
    # Non-vacuity: "the outcome changed" must not be satisfied by "nothing
    # happened". Name what the sabotage actually produced — the redirected
    # source's bytes on disk, or an explicit refusal in the log.
    if [ -f "$T3/$REL" ] && [ "$( _sha "$T3/$REL" )" = "$ROT_SHA" ]; then
      ok "R.3 the redirected source's bytes landed (the table drove the copy, not a no-op)"
    elif grep -qE 'RESTORE-FAILED|RESTORE-BLOCKED|not repairable|source diverged' "$T3/.sab.log"; then
      ok "R.3 the sabotage produced a NAMED refusal (not a silent no-op)"
    else
      bad "R.3 sabotage produced neither redirected bytes nor a named refusal — the control may be vacuous"
    fi
  fi
  [ -f "$ROUTES" ] && ok "R.3 real table intact after the control" || bad "R.3 real table damaged"

  # W6 — the retired override must be INERT. If doctor still honoured
  # DELIVERY_ROUTES_TSV there would be two overrides, and the reader would
  # ignore one of them: a caller could poison a table nobody reads and see a
  # green run. Same sabotaged table, retired variable, must behave like the
  # real table.
  T3B="$( fresh_install )" || { bad "R.3 install failed (retired-override leg)"; T3B=""; }
  if [ -n "$T3B" ]; then
    if [ "$( grep -c "  $REL\$" "$T3B/.claude/.install-manifest.sha256" )" -eq 0 ]; then
      printf '%s  %s\n' "$TPL_SHA" "$REL" >> "$T3B/.claude/.install-manifest.sha256"
    fi
    rm -f "$T3B/$REL"
    DELIVERY_ROUTES_TSV="$SABOTAGED" bash "$DOCTOR" "$T3B" --repair > "$T3B/.retired.log" 2>&1
    if [ -f "$T3B/$REL" ] && [ "$( _sha "$T3B/$REL" )" = "$TPL_SHA" ]; then
      ok "R.3 retired DELIVERY_ROUTES_TSV is INERT (real table still used)"
    else
      bad "R.3 retired DELIVERY_ROUTES_TSV still steers doctor — a second override survived W6"
    fi
  fi
fi

# ---------------------------------------------------------------------------
# R.4 — the leak that matters. `.github/CODEOWNERS` is RENDERED at install
# time. Resolving it by identity finds THIS repository's own live CODEOWNERS,
# the one file carrying the maintainer's real handle. Repairing an adopter
# with it would ship the maintainer's identity into their repo — the A3 class
# cured in S322. The cure must refuse to repair, not repair from the wrong
# file.
# ---------------------------------------------------------------------------
echo "==> R.4 — a rendered route must NOT be repaired from the live file"

if [ -f "$SOURCE_DIR/.github/CODEOWNERS" ]; then
  T4="$( fresh_install )" || { bad "R.4 install failed"; T4=""; }
  if [ -n "$T4" ]; then
    REL=".github/CODEOWNERS"
    LIVE_SHA="$( _sha "$SOURCE_DIR/$REL" )"
    # Record the LIVE file's digest as the baseline: the most favourable
    # possible conditions for the defect. Pre-cure, src_hash == base, so
    # doctor would classify "MISSING (restorable)" and copy the live file.
    printf '%s  %s\n' "$LIVE_SHA" "$REL" >> "$T4/.claude/.install-manifest.sha256"
    [ ! -e "$T4/$REL" ] && ok "R.4 precondition: adopter has no $REL (mutually exclusive with .template)" \
                        || bad "R.4 precondition: adopter unexpectedly HAS $REL"

    bash "$DOCTOR" "$T4" --repair > "$T4/.rendered.log" 2>&1

    if [ -f "$T4/$REL" ] && [ "$( _sha "$T4/$REL" )" = "$LIVE_SHA" ]; then
      bad "R.4 LEAK: doctor repaired the adopter with this repo's live CODEOWNERS (maintainer identity shipped)"
    else
      ok "R.4 no leak: the rendered route was not repaired from the live file"
    fi
    grep -qE 'no longer ships|not repairable|RESTORE-BLOCKED|source diverged' "$T4/.rendered.log" \
      && ok "R.4 log names the rendered path as not-repairable" \
      || bad "R.4 log does not explain why the rendered path was skipped"
  fi
else
  ok "R.4 skipped: no live .github/CODEOWNERS in this checkout (nothing to leak)"
fi

# ---------------------------------------------------------------------------
# R.5 — W6, end to end: a HOSTILE route row must not reach `cp`.
#
# doctor's escape vector is the `src` column. It is appended to $SOURCE_DIR and
# handed to `cp`, so `src=../../../../etc/hosts` READS OUTSIDE the framework
# checkout and delivers those bytes into the adopter tree as framework content.
# Asserted on BYTES and on absence, never on a verdict string alone.
# ---------------------------------------------------------------------------
echo "==> R.5 — a hostile route row is refused before the copy (e2e)"

FOREIGN="/etc/hosts"
if [ ! -f "$FOREIGN" ]; then
  ok "R.5 skipped: no $FOREIGN on this platform to stand in for a foreign file"
else
  T5="$( fresh_install )" || { bad "R.5 install failed"; T5=""; }
  if [ -n "$T5" ]; then
    REL="docs/BRANCH-PROTECTION.md"
    TPL_SHA="$( _sha "$SOURCE_DIR/templates/$REL" )"
    FOREIGN_SHA="$( _sha "$FOREIGN" )"
    if [ "$( grep -c "  $REL\$" "$T5/.claude/.install-manifest.sha256" )" -eq 0 ]; then
      printf '%s  %s\n' "$TPL_SHA" "$REL" >> "$T5/.claude/.install-manifest.sha256"
    fi
    rm -f "$T5/$REL"

    # rail round-6 F3 — the hostile table travels in a COPIED checkout, so the
    # `../` depth must be computed from THAT checkout's path, not from
    # $SOURCE_DIR: the copy lives under $WORKROOT and is at a different depth.
    # Building the tree first and writing its table second is what keeps the
    # escape a REAL one on this machine rather than a hopeful string of `../`.
    R5_SRC="$WORKROOT/src-r5"
    if ! _mk_source_copy "$R5_SRC" NONE; then
      bad "R.5 could not build the copied checkout for the hostile table"
    fi
    _up=""; _probe_dir="$R5_SRC"
    while [ "$_probe_dir" != "/" ] && [ -n "$_probe_dir" ]; do
      _up="../$_up"; _probe_dir="$( dirname "$_probe_dir" )"
    done
    HOSTILE_E2E="$WORKROOT/hostile-e2e.tsv"
    sed "s|templates/docs/BRANCH-PROTECTION\.md|${_up}etc/hosts|" "$ROUTES" > "$HOSTILE_E2E"
    cp "$HOSTILE_E2E" "$R5_SRC/scripts/delivery-routes.tsv"
    if cmp -s "$HOSTILE_E2E" "$ROUTES"; then
      bad "R.5 poisoning was a no-op — the control proves nothing"
    else
      ok "R.5 hostile src planted in the copied checkout's table (real table untouched)"
      # Sanity: the escape really does name the foreign file FROM THE COPY.
      [ "$( _sha "$R5_SRC/${_up}etc/hosts" 2>/dev/null || true )" = "$FOREIGN_SHA" ] \
        && ok "R.5 precondition: the planted src DOES resolve to $FOREIGN from the copied SOURCE_DIR" \
        || bad "R.5 precondition: the planted src does not resolve — the control is not hostile"

      bash "$R5_SRC/scripts/doctor.sh" "$T5" --repair > "$T5/.hostile.log" 2>&1

      if [ ! -e "$T5/$REL" ]; then
        ok "R.5 destination NOT written (the hostile row never reached cp)"
      elif [ "$( _sha "$T5/$REL" )" = "$FOREIGN_SHA" ]; then
        bad "R.5 LEAK: doctor copied $FOREIGN into the adopter tree as framework content"
      else
        bad "R.5 destination was written from an unexpected source (sha $( _sha "$T5/$REL" ))"
      fi
      grep -qE 'RESTORE-BLOCKED|not repairable|no longer ships' "$T5/.hostile.log" \
        && ok "R.5 log NAMES the refusal (a rejection nobody can see is the silence D3 was made of)" \
        || bad "R.5 log does not name the refusal"
      # Nothing anywhere in the target may carry the foreign bytes.
      if find "$T5" -type f -exec sh -c '[ "$( shasum -a 256 "$1" 2>/dev/null | cut -d" " -f1 )" = "$2" ]' _ {} "$FOREIGN_SHA" \; -print 2>/dev/null | grep -q .; then
        bad "R.5 foreign bytes found somewhere under the target"
      else
        ok "R.5 no file under the target carries the foreign bytes"
      fi
    fi
  fi
fi

# ---------------------------------------------------------------------------
# R.6 — W6, the MEASURED before/after. The retired private parser is extracted
# from git HEAD and given the same hostile row; today's reader is given it too.
# This reproduces the MECHANISM (the reader's verdict feeding a copy), not the
# appearance, and it is what makes "fail-CLOSED" a measurement instead of a
# claim: the RED leg copies real bytes from outside the checkout.
# ---------------------------------------------------------------------------
echo "==> R.6 — before/after on the retired parser (RED -> GREEN)"

HEAD_DOCTOR="$WORKROOT/doctor-HEAD.sh"
if ( cd "$SOURCE_DIR" && git show HEAD:scripts/doctor.sh ) > "$HEAD_DOCTOR" 2>/dev/null && [ -s "$HEAD_DOCTOR" ]; then
  OLD_FRAG="$WORKROOT/old_route_source.sh"
  sed -n '/^_route_source() {$/,/^}$/p' "$HEAD_DOCTOR" > "$OLD_FRAG"
  if [ ! -s "$OLD_FRAG" ]; then
    ok "R.6 HEAD carries no private parser either — nothing to compare (already consolidated)"
  else
    ok "R.6 retired parser recovered from git HEAD (the RED leg has a real subject)"
    POISON="$WORKROOT/r6-poison.tsv"
    {
      printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
      printf 'docs/victim.md\t../../../../../../../../etc/hosts\tidentity\t-\to\thostile\n'
    } > "$POISON"

    # RED: the retired parser resolves it, so the copy it feeds lands foreign
    # bytes at a destination the adopter believes is framework content.
    OLD_H="$WORKROOT/r6-old.sh"
    {
      echo 'set -uo pipefail'
      echo "DELIVERY_ROUTES_TSV=\"$POISON\""
      cat "$OLD_FRAG"
      echo 'rc=0; out="$( _route_source "docs/victim.md" )" || rc=$?'
      echo 'printf "%s|%s\n" "$rc" "${out:-}"'
    } > "$OLD_H"
    OLD_OUT="$( bash "$OLD_H" 2>/dev/null )"
    case "$OLD_OUT" in
      0\|*)
        ok "R.6 RED reproduced: the retired parser ACCEPTED the hostile row ($OLD_OUT)"
        _r6_src="${OLD_OUT#0|}"
        if [ -f "$SOURCE_DIR/$_r6_src" ]; then
          cp -p "$SOURCE_DIR/$_r6_src" "$WORKROOT/r6-landed.bin" 2>/dev/null || true
          if [ -s "$WORKROOT/r6-landed.bin" ]; then
            ok "R.6 RED measured: $( wc -c < "$WORKROOT/r6-landed.bin" | tr -d ' ' ) bytes copied from OUTSIDE the checkout"
          else
            bad "R.6 RED leg copied nothing — the measurement did not happen"
          fi
        else
          bad "R.6 RED leg: the accepted src did not resolve; measurement incomplete"
        fi
        ;;
      *) bad "R.6 RED leg did not reproduce (got '$OLD_OUT') — the before/after is not comparable" ;;
    esac

    # GREEN: today's reader, same row.
    if [ "$FRAG_OK" -eq 1 ]; then
      NEW_H="$WORKROOT/r6-new.sh"
      {
        echo 'set -uo pipefail'
        echo "_WBM_ROUTES_TSV=\"$POISON\""
        cat "$FRAG"
        echo 'rc=0; out="$( _wbm_route_src "docs/victim.md" )" || rc=$?'
        echo 'printf "%s|%s\n" "$rc" "${out:-}"'
      } > "$NEW_H"
      NEW_OUT="$( bash "$NEW_H" 2>/dev/null )"
      [ "$NEW_OUT" = "2|" ] \
        && ok "R.6 GREEN: the shared reader REFUSES the same row (rc=2, 0 bytes)" \
        || bad "R.6 GREEN: shared reader returned '$NEW_OUT', want '2|'"
    fi
  fi
else
  ok "R.6 skipped: git HEAD:scripts/doctor.sh unavailable (shallow or non-git checkout)"
fi

# ---------------------------------------------------------------------------
# R.7 — W6 write-site guard: never write THROUGH a symlink.
#
# HONEST SCOPE, so a future reader does not overstate this: doctor's manifest
# sanitiser (_relpath_unsafe) already drops a record whose ancestor is a
# symlink AT INGEST, so a full run at HEAD also refused this. What the write-
# site guard adds is coverage of the window the sanitiser cannot see — it runs
# once, before the whole verification loop, and the copy happens later (TOCTOU)
# — plus any future call site that reaches _restore_file another way. The
# control below therefore exercises the GUARD, with a real symlink on disk, and
# the RED leg is the guard removed.
# ---------------------------------------------------------------------------
echo "==> R.7 — the write site refuses a symlinked destination parent"

GUARD_FRAG="$WORKROOT/restore_refuses.sh"
sed -n '/^_restore_refuses() {$/,/^}$/p' "$DOCTOR" > "$GUARD_FRAG"
if [ ! -s "$GUARD_FRAG" ]; then
  bad "R.7 could not extract _restore_refuses from doctor.sh (renamed or removed?)"
elif [ "$FRAG_OK" -eq 0 ]; then
  bad "R.7 skipped: the reader predicate could not be extracted"
else
  ok "R.7 _restore_refuses extracted from doctor.sh"
  R7T="$WORKROOT/r7-target"; R7OUT="$WORKROOT/r7-outside"
  mkdir -p "$R7T" "$R7OUT"
  ln -s "$R7OUT" "$R7T/docs"
  [ -L "$R7T/docs" ] && ok "R.7 planted: target/docs is a symlink to an outside dir" \
                     || bad "R.7 could not plant the symlink"

  _r7_run() {  # $1=harness-file $2=guarded(1)/unguarded(0) — performs the copy
    {
      echo 'set -uo pipefail'
      echo "TARGET=\"$R7T\""
      # rail round-7 F2 — _restore_refuses now confines the SOURCE against
      # SOURCE_DIR, so the harness has to name it or die under `set -u`.
      echo "SOURCE_DIR=\"$SOURCE_DIR\""
      echo '_log() { printf "%s\n" "$*"; }'
      echo 'REFUSED_COUNT=0'   # FU-7: _restore_refuses counts refusals; set -u needs it defined
      cat "$FRAG"
      if [ "$2" -eq 1 ]; then cat "$GUARD_FRAG"; else echo '_restore_refuses() { return 1; }'; fi
      echo 'if _restore_refuses "docs/PWNED.md" "templates/docs/rotation-log.md"; then echo REFUSED; exit 0; fi'
      echo 'mkdir -p "$TARGET/docs"'
      echo "cp -p \"$SOURCE_DIR/templates/docs/rotation-log.md\" \"\$TARGET/docs/PWNED.md\""
      echo 'echo WROTE'
    } > "$1"
  }

  # RED — guard neutralised: the copy follows the link and lands OUTSIDE.
  _r7_run "$WORKROOT/r7-red.sh" 0
  R7_RED="$( bash "$WORKROOT/r7-red.sh" 2>/dev/null | tail -1 )"
  if [ "$R7_RED" = "WROTE" ] && [ -f "$R7OUT/PWNED.md" ]; then
    ok "R.7 RED reproduced: without the guard, $( wc -c < "$R7OUT/PWNED.md" | tr -d ' ' ) bytes landed OUTSIDE the target"
  else
    bad "R.7 RED leg did not reproduce (got '$R7_RED') — the GREEN leg below proves less than it claims"
  fi
  rm -f "$R7OUT/PWNED.md"

  # GREEN — guard in place.
  _r7_run "$WORKROOT/r7-green.sh" 1
  R7_GREEN="$( bash "$WORKROOT/r7-green.sh" 2>/dev/null | tail -1 )"
  [ "$R7_GREEN" = "REFUSED" ] \
    && ok "R.7 GREEN: the guard refuses the symlinked parent" \
    || bad "R.7 GREEN: guard did not refuse (got '$R7_GREEN')"
  [ ! -e "$R7OUT/PWNED.md" ] \
    && ok "R.7 GREEN: nothing was written outside the target" \
    || bad "R.7 GREEN: a file appeared outside the target despite the guard"

  # And the hostile/lexical legs of the same guard, on the same harness.
  _r7_lex() {  # $1=dest $2=src $3=label
    {
      echo 'set -uo pipefail'
      echo "TARGET=\"$R7T\""
      # rail round-7 F2 — _restore_refuses now confines the SOURCE against
      # SOURCE_DIR, so the harness has to name it or die under `set -u`.
      echo "SOURCE_DIR=\"$SOURCE_DIR\""
      echo '_log() { printf "%s\n" "$*"; }'
      echo 'REFUSED_COUNT=0'   # FU-7: _restore_refuses counts refusals; set -u needs it defined
      cat "$FRAG"; cat "$GUARD_FRAG"
      echo "if _restore_refuses \"$1\" \"$2\"; then echo REFUSED; else echo ALLOWED; fi"
    } > "$WORKROOT/r7-lex.sh"
    local got; got="$( bash "$WORKROOT/r7-lex.sh" 2>/dev/null | tail -1 )"
    [ "$got" = "REFUSED" ] && ok "R.7 guard refuses: $3" || bad "R.7 guard ALLOWED: $3 (got '$got')"
  }
  _r7_lex "../../outside/PWNED.md" "templates/docs/rotation-log.md" "escaping destination"
  _r7_lex "docs2/ok.md"            "../../../../etc/hosts"          "escaping source"
  _r7_lex "docs2/ok.md"            "/etc/hosts"                     "absolute source"
  _r7_lex ""                       "templates/docs/rotation-log.md" "empty destination"
  # Anti-over-rejection: an ordinary confined pair must be ALLOWED, or the
  # guard would refuse every real repair and the assertions above would be
  # satisfied by a function that always says no.
  {
    echo 'set -uo pipefail'
    echo "TARGET=\"$R7T\""
    echo "SOURCE_DIR=\"$SOURCE_DIR\""
    echo '_log() { printf "%s\n" "$*"; }'
    echo 'REFUSED_COUNT=0'   # FU-7: _restore_refuses counts refusals; set -u needs it defined
    cat "$FRAG"; cat "$GUARD_FRAG"
    echo 'if _restore_refuses "docs2/ok.md" "templates/docs/rotation-log.md"; then echo REFUSED; else echo ALLOWED; fi'
  } > "$WORKROOT/r7-benign.sh"
  R7_OK="$( bash "$WORKROOT/r7-benign.sh" 2>/dev/null | tail -1 )"
  [ "$R7_OK" = "ALLOWED" ] \
    && ok "R.7 guard ALLOWS an ordinary confined repair (it is not a blanket no)" \
    || bad "R.7 guard refused a benign confined repair (got '$R7_OK') — false positive"
fi

# ---------------------------------------------------------------------------
# R.8 (rail round-4 F3) — a MISSING route table must stop doctor, not degrade
# it to identity.
#
# The W6 startup checks assert the LIBRARY and its three functions. They say
# nothing about the TABLE. _wbm_route_src answers rc=1 ("no row for this
# destination") when the table is absent, and every doctor call site answers
# rc=1 with the identity fallback `$SOURCE_DIR/$rel` — so on a partial
# checkout the classification hashes the root homonym and, whenever the
# recorded baseline happens to equal it, `_restore_file` COPIES the wrong
# source. That last case is not hypothetical: a manifest written by a
# pre-D3-cure generator recorded exactly the root homonym's digest for these
# destinations (that IS defect D3), so the fixture below is the population
# this cure exists for, and the same path applied to `.github/CODEOWNERS`
# copies THIS repo's live maintainer file into an adopter tree.
#
# RED is produced by neutralising the cure in a COPY of doctor.sh (the R.3
# idiom: sabotage a copy, never the real file) and asserting the bytes.
# ---------------------------------------------------------------------------
echo ""
echo "==> R.8 — a missing route table refuses the run (never identity fallback)"

T8="$( fresh_install )" || { bad "R.8 install failed"; T8=""; }
if [ -n "$T8" ]; then
  REL="docs/BRANCH-PROTECTION.md"
  TPL_SHA="$( _sha "$SOURCE_DIR/templates/$REL" )"
  ROOT_SHA="$( _sha "$SOURCE_DIR/$REL" )"
  # rail round-6 F3 — "table absent" is now a property of the CHECKOUT, not of
  # an environment variable: `_mk_source_copy ... NONE` builds a tree with no
  # scripts/delivery-routes.tsv at all, which is exactly the partial checkout
  # this leg speaks for. MIRROR is that tree with doctor.sh replaced by the
  # gate-stripped copy (the R.3 idiom: sabotage a copy, never the real file).
  MIRROR="$WORKROOT/src-nogate"
  if ! _mk_source_copy "$MIRROR" NONE; then
    bad "R.8 could not build the table-less copied checkout — every leg below is scaffolding"
  fi
  [ -e "$MIRROR/scripts/delivery-routes.tsv" ] \
    && bad "R.8-control the table-less copy DOES carry a route table — the fixture is not what it claims" \
    || ok "R.8-control the copied checkout genuinely has no scripts/delivery-routes.tsv"
  # The RED tree needs BOTH gates removed. doctor's startup gate is round 4 F3;
  # the READER's own gate is round 6 F2, and it alone is now enough to refuse a
  # missing table (R.8g asserts exactly that, which is why leaving it in would
  # make this RED stop reproducing and the leg would go quietly green).
  _r8_strip_doctor() {  # $1 = copied checkout
    awk 'BEGIN{skip=0}
         /^# rail round-4 F3 — the READER being present/{skip=1}
         skip==1 && /^fi$/{skip=0; next}
         skip==1{next}
         {print}' "$SOURCE_DIR/scripts/doctor.sh" > "$1/scripts/doctor.sh"
  }
  _r8_strip_reader() {  # $1 = copied checkout
    awk '/^  _wbm_route_table_gate \|\|/ { print "  true  # RED-PLANT"; next } { print }' \
      "$SOURCE_DIR/scripts/_framework_manifest_set.sh" > "$1/scripts/_framework_manifest_set.sh"
  }
  _r8_strip_doctor "$MIRROR"
  _r8_strip_reader "$MIRROR"

  _real_gate="$( grep -c '^if ! _wbm_route_table_gate; then$' "$SOURCE_DIR/scripts/doctor.sh" )"
  _red_gate="$( grep -c '^if ! _wbm_route_table_gate; then$' "$MIRROR/scripts/doctor.sh" )"
  _real_rgate="$( grep -cE '^  _wbm_route_table_gate \|\|' "$SOURCE_DIR/scripts/_framework_manifest_set.sh" )"
  _red_rgate="$( grep -cE '^  _wbm_route_table_gate \|\|' "$MIRROR/scripts/_framework_manifest_set.sh" )"
  if [ "$_real_gate" -eq 1 ] && [ "$_red_gate" -eq 0 ] \
     && [ "$_real_rgate" -eq 3 ] && [ "$_red_rgate" -eq 0 ] \
     && bash -n "$MIRROR/scripts/doctor.sh" 2>/dev/null \
     && bash -n "$MIRROR/scripts/_framework_manifest_set.sh" 2>/dev/null; then
    ok "R.8-control both gates are present once/three times in the real files and removed in the RED copy (which still parses)"
  else
    bad "R.8-control gate sites: doctor real=$_real_gate red=$_red_gate, reader real=$_real_rgate red=$_red_rgate (want 1/0 and 3/0) — the RED plant rotted, so R.8a proves nothing"
  fi

  # Fixture: a pre-D3-cure manifest — the generator resolved by identity, so it
  # recorded the ROOT homonym's digest for this destination.
  _r8_seed() {  # $1 = target dir
    _m="$1/.claude/.install-manifest.sha256"
    grep -v "  $REL\$" "$_m" > "$_m.r8" || true    # grep exits 1 when it drops everything
    mv "$_m.r8" "$_m"
    printf '%s  %s\n' "$ROOT_SHA" "$REL" >> "$_m"
    rm -f "$1/$REL"
  }
  if [ "$TPL_SHA" = "$ROOT_SHA" ]; then
    bad "R.8-control template and root homonym have converged — this leg cannot discriminate the two sources"
  else
    T8_RED="$WORKROOT/r8-red"; cp -R "$T8" "$T8_RED"; _r8_seed "$T8_RED"
    bash "$MIRROR/scripts/doctor.sh" "$T8_RED" --repair \
      > "$T8_RED/.r8red.log" 2>&1
    if [ -f "$T8_RED/$REL" ]; then
      GOT="$( _sha "$T8_RED/$REL" )"
      if [ "$GOT" = "$ROOT_SHA" ]; then
        ok "R.8a RED (gate removed, table absent): --repair wrote the ROOT homonym, $( wc -c < "$T8_RED/$REL" | tr -d ' ' ) bytes — D4 through a missing file"
      else
        bad "R.8a RED wrote bytes matching neither source (sha $GOT) — the reproduction is not the one this leg describes"
      fi
    else
      bad "R.8a RED wrote nothing — the pre-cure defect did not reproduce, so the GREEN below is not evidence"
    fi

    # The missing TABLE is the cause, not the missing gates: same stripped
    # doctor AND stripped reader, same fixture, table PRESENT.
    MIRROR_TBL="$WORKROOT/src-nogate-withtable"
    if _mk_source_copy "$MIRROR_TBL" "$ROUTES"; then
      _r8_strip_doctor "$MIRROR_TBL"
      _r8_strip_reader "$MIRROR_TBL"
      T8_CTL="$WORKROOT/r8-ctl"; cp -R "$T8" "$T8_CTL"; _r8_seed "$T8_CTL"
      bash "$MIRROR_TBL/scripts/doctor.sh" "$T8_CTL" --repair \
        > "$T8_CTL/.r8ctl.log" 2>&1
      if [ -e "$T8_CTL/$REL" ]; then
        bad "R.8b the stripped doctor restored the path even WITH the table — the RED above is not attributable to the missing table"
      else
        ok "R.8b with the table present the same stripped doctor restores NOTHING (the route resolves to the template, which diverges from the bad baseline)"
      fi
    else
      bad "R.8b could not build the stripped-but-tabled checkout — the attribution control did not run"
    fi

    # R.8g (rail round-6 F2) — the READER's gate alone closes it. Same
    # table-less checkout, doctor's OWN startup gate stripped, but the library
    # untouched: pre-round-6 this was the R.8a RED; now the reader answers
    # rc=2 and _restore_file blocks. Defence in depth measured, not asserted.
    MIRROR_RGATE="$WORKROOT/src-readergate"
    if _mk_source_copy "$MIRROR_RGATE" NONE; then
      _r8_strip_doctor "$MIRROR_RGATE"     # reader gate deliberately INTACT
      _rg_doctor="$( grep -c '^if ! _wbm_route_table_gate; then$' "$MIRROR_RGATE/scripts/doctor.sh" )"
      _rg_reader="$( grep -cE '^  _wbm_route_table_gate \|\|' "$MIRROR_RGATE/scripts/_framework_manifest_set.sh" )"
      if [ "$_rg_doctor" -eq 0 ] && [ "$_rg_reader" -eq 3 ]; then
        ok "R.8g-control the checkout has doctor's gate removed and the reader's three intact"
      else
        bad "R.8g-control doctor gate=$_rg_doctor reader gates=$_rg_reader (want 0 and 3) — R.8g measures the wrong tree"
      fi
      T8_RG="$WORKROOT/r8-rgate"; cp -R "$T8" "$T8_RG"; _r8_seed "$T8_RG"
      bash "$MIRROR_RGATE/scripts/doctor.sh" "$T8_RG" --repair > "$T8_RG/.r8rgate.log" 2>&1
      if [ -e "$T8_RG/$REL" ]; then
        bad "R.8g the reader's gate did NOT stop the identity fallback: --repair wrote $( _sha "$T8_RG/$REL" ) with doctor's own gate removed"
      else
        ok "R.8g with ONLY the reader's gate the same run writes nothing — the missing table is refused at the reader, not just at doctor's door"
      fi
    else
      bad "R.8g could not build the reader-gate-only checkout"
    fi

    # GREEN: the real doctor, same fixture, table absent.
    T8_GRN="$WORKROOT/r8-green"; cp -R "$T8" "$T8_GRN"; _r8_seed "$T8_GRN"
    GREEN_SRC="$WORKROOT/src-notable"
    _mk_source_copy "$GREEN_SRC" NONE \
      || bad "R.8c could not build the table-less checkout for the GREEN leg"
    bash "$GREEN_SRC/scripts/doctor.sh" "$T8_GRN" --repair \
      > "$T8_GRN/.r8green.log" 2>&1
    R8_RC=$?
    [ "$R8_RC" -eq 2 ] \
      && ok "R.8c GREEN: doctor exits 2 (infra) when the route table is absent" \
      || bad "R.8c GREEN: doctor exited $R8_RC with no route table — expected 2; rc 0/1 means it verified or repaired blind"
    grep -q 'delivery-route table is unusable' "$T8_GRN/.r8green.log" \
      && ok "R.8d GREEN: the refusal NAMES the table and the reason" \
      || bad "R.8d GREEN: no named refusal in the log — an operator cannot tell this from an ordinary failure"
    [ -e "$T8_GRN/$REL" ] \
      && bad "R.8e GREEN: the destination was written despite the refusal" \
      || ok "R.8e GREEN: nothing was written — the refusal precedes verification, not just repair"
  fi

  # Anti-over-rejection: the gate must not refuse a healthy run. R.2 already
  # proves a healthy repair, but only with the table at its default location;
  # this asserts the gate itself is satisfied by the real table.
  bash "$SOURCE_DIR/scripts/doctor.sh" "$T8" > "$T8/.r8ok.log" 2>&1
  R8_OK_RC=$?
  if [ "$R8_OK_RC" -eq 2 ] && grep -q 'delivery-route table is unusable' "$T8/.r8ok.log"; then
    bad "R.8f the gate refused a NORMAL run against the real table — it is a blanket no"
  else
    ok "R.8f the gate passes on an ordinary run (rc=$R8_OK_RC, no table refusal)"
  fi

  # -------------------------------------------------------------------------
  # R.9 (rail round-6 F3) — the ENVIRONMENT cannot hand doctor a table.
  #
  # doctor --repair COPIES from whatever source the table names, so an ambient
  # variable naming the table was a write primitive: rounds 1-4 hardened what a
  # ROW may say, round 5 gated who may supply the table, round 6 removed the
  # supply channel. The two legs are the SAME command; the only difference is
  # which CHECKOUT runs it, which is the only difference production has.
  # -------------------------------------------------------------------------
  echo ""
  echo "==> R.9 — no environment variable can steer doctor's route table (F3)"

  R9_NO_TABLE="$WORKROOT/no-such-delivery-routes.tsv"   # deliberately never created
  # Both retired names planted, plus the retired switch: this is the exact
  # shape that used to work, so anything left of the old gate wakes up here.
  env CEO_ROUTES_TABLE_OVERRIDE_FOR_TESTS=1 \
      _WBM_ROUTES_TSV="$R9_NO_TABLE" \
      FMS_DELIVERY_ROUTES_TSV="$R9_NO_TABLE" \
    bash "$SOURCE_DIR/scripts/doctor.sh" "$T8" > "$T8/.r9env.log" 2>&1
  R9_RC=$?
  if grep -q 'delivery-route table is unusable' "$T8/.r9env.log"; then
    bad "R.9a doctor consumed a table named in the ENVIRONMENT (rc=$R9_RC, table refusal) — the override is back"
  else
    ok "R.9a a table named in the environment is inert (rc=$R9_RC) — doctor read the table of the checkout it ran from"
  fi
  # Non-vacuity: the SAME absent table, delivered the only way that works now
  # (as the checkout's own table), MUST produce the refusal this leg just
  # asserted was absent. Without this the R.9a green could mean "doctor never
  # refuses anything".
  R9_SRC="$WORKROOT/src-r9-notable"
  if _mk_source_copy "$R9_SRC" NONE; then
    bash "$R9_SRC/scripts/doctor.sh" "$T8" > "$T8/.r9copy.log" 2>&1
    R9_CP_RC=$?
    if [ "$R9_CP_RC" -eq 2 ] && grep -q 'delivery-route table is unusable' "$T8/.r9copy.log"; then
      ok "R.9b-control the SAME missing table, as the checkout's own, DOES refuse (rc=2) — R.9a measured the channel, not doctor's silence"
    else
      bad "R.9b-control the copied table-less checkout exited $R9_CP_RC without the refusal — R.9a proves nothing"
    fi
  else
    bad "R.9b-control could not build the table-less checkout"
  fi
fi

# ---------------------------------------------------------------------------
# R.10 (rail round-7 F2) — `cp -p` follows symlinks, so the SOURCE needs
# PHYSICAL confinement, not just the lexical predicate. A `templates/...`
# source whose leaf or ancestor links to a regular file outside the checkout
# would be copied into the adopter as framework content — the same escape
# measured on the upgrade side, and the same class as D4/A3 arriving by
# another door. This covers BOTH lanes: the route lane and the identity
# fallback that answers for every `.claude/**` manifest record.
# ---------------------------------------------------------------------------
echo ""
echo "==> R.10 — the restore refuses a source that resolves outside the checkout (F2)"

if [ "$FRAG_OK" -eq 0 ]; then
  bad "R.10 skipped: the reader predicate could not be extracted"
else
  R10_SRC="$WORKROOT/r10-src"
  R10_OUT="$WORKROOT/r10-outside"
  R10_TGT="$WORKROOT/r10-target"
  mkdir -p "$R10_SRC/templates/docs" "$R10_SRC/templates/.github" \
           "$R10_OUT/docs" "$R10_TGT/docs"
  printf 'FRAMEWORK BYTES\n'  > "$R10_SRC/templates/docs/rotation-log.md"
  printf 'FOREIGN LEAF\n'     > "$R10_OUT/foreign.md"
  printf 'FOREIGN ANCESTOR\n' > "$R10_OUT/docs/BRANCH-PROTECTION.md"
  ln -s "$R10_OUT/foreign.md" "$R10_SRC/templates/docs/BRANCH-PROTECTION.md"
  ln -s "$R10_OUT/docs" "$R10_SRC/templates/.github/docs"
  [ -L "$R10_SRC/templates/docs/BRANCH-PROTECTION.md" ] \
    && ok "R.10-control the symlinked source is planted (leaf -> outside the checkout)" \
    || bad "R.10-control could not plant the symlinked source"

  # $1 = guarded(1)/unguarded(0), $2 = source relpath -> REFUSED | WROTE
  _r10_run() {
    {
      echo 'set -uo pipefail'
      echo "TARGET=\"$R10_TGT\""
      echo "SOURCE_DIR=\"$R10_SRC\""
      echo '_log() { printf "%s\n" "$*"; }'
      echo 'REFUSED_COUNT=0'   # FU-7: _restore_refuses counts refusals; set -u needs it defined
      cat "$FRAG"
      if [ "$1" -eq 1 ]; then
        cat "$GUARD_FRAG"
      else
        # RED = the pre-cure guard: the SAME function with the physical
        # source check removed and nothing else touched. Anchored on the
        # call, so a rename here goes RED on the plant count below.
        awk '/_wbm_source_confined "\$SOURCE_DIR" "\$_rr_src"/ { skip=3; next }
             skip > 0 { skip--; next }
             { print }' "$GUARD_FRAG"
      fi
      echo "if _restore_refuses \"docs/out.md\" \"$2\"; then echo REFUSED; exit 0; fi"
      echo "cp -p \"\$SOURCE_DIR/$2\" \"\$TARGET/docs/out.md\""
      echo 'echo WROTE'
    } > "$WORKROOT/r10-run.sh"
    bash "$WORKROOT/r10-run.sh" 2>/dev/null | tail -1
  }

  # The RED fragment must differ from the guarded one by exactly the check.
  awk '/_wbm_source_confined "\$SOURCE_DIR" "\$_rr_src"/ { skip=3; next }
       skip > 0 { skip--; next }
       { print }' "$GUARD_FRAG" > "$WORKROOT/r10-guard-red.sh"
  _r10_calls="$( grep -c '_wbm_source_confined "\$SOURCE_DIR" "\$_rr_src"' "$GUARD_FRAG" )"
  _r10_red_calls="$( grep -c '_wbm_source_confined' "$WORKROOT/r10-guard-red.sh" 2>/dev/null )" || _r10_red_calls=0
  if [ "$_r10_calls" -eq 1 ] && [ "$_r10_red_calls" -eq 0 ] \
     && bash -n "$WORKROOT/r10-guard-red.sh" 2>/dev/null; then
    ok "R.10-control the guard calls the confinement predicate exactly once and the RED copy removes it (still parses)"
  else
    bad "R.10-control calls real=$_r10_calls red=$_r10_red_calls — the RED plant rotted, so R.10 proves nothing"
  fi

  R10_RED="$( _r10_run 0 "templates/docs/BRANCH-PROTECTION.md" )"
  if [ "$R10_RED" = "WROTE" ] \
     && [ "$( _sha "$R10_TGT/docs/out.md" 2>/dev/null )" = "$( _sha "$R10_OUT/foreign.md" )" ]; then
    ok "R.10-RED without the check the restore copies the OUTSIDE file byte for byte — the escape reproduces"
  else
    bad "R.10-RED the unguarded restore answered '$R10_RED' — the finding does not reproduce, so the GREEN below is not evidence"
  fi
  rm -f "$R10_TGT/docs/out.md"

  [ "$( _r10_run 1 "templates/docs/BRANCH-PROTECTION.md" )" = "REFUSED" ] \
    && ok "R.10a the cured guard refuses a symlinked LEAF source" \
    || bad "R.10a the cured guard allowed a symlinked leaf source"
  [ ! -e "$R10_TGT/docs/out.md" ] \
    && ok "R.10b nothing was written from outside the checkout" \
    || bad "R.10b a file was restored from outside the checkout despite the guard"
  [ "$( _r10_run 1 "templates/.github/docs/BRANCH-PROTECTION.md" )" = "REFUSED" ] \
    && ok "R.10c a symlinked ANCESTOR is refused too" \
    || bad "R.10c the guard allowed a symlinked ancestor"
  # Anti-over-rejection: a real source inside the checkout is still restorable,
  # or the assertions above would be satisfied by a function that always says no.
  R10_OK="$( _r10_run 1 "templates/docs/rotation-log.md" )"
  if [ "$R10_OK" = "WROTE" ] \
     && [ "$( _sha "$R10_TGT/docs/out.md" 2>/dev/null )" = "$( _sha "$R10_SRC/templates/docs/rotation-log.md" )" ]; then
    ok "R.10d a CONFINED source is still restored (the guard is not a blanket no)"
  else
    bad "R.10d a legitimate confined restore was refused (got '$R10_OK') — false positive"
  fi
fi

# ---------------------------------------------------------------------------
# R.11 (rail round-8) — the two HASH sites need the same PHYSICAL source
# confinement the WRITE site got in round 7. `_hash_file` follows symlinks
# exactly as `cp -p` does, so a source whose leaf OR ancestor links to a
# regular file outside the checkout was hashed as framework content and the
# VERDICT flipped:
#
#   DRIFT lane   — `cur` and the foreign `src_hash` agree, so the run reports
#                  `DRIFT (baseline-stale: ... run upgrade.sh to refresh the
#                  baseline)`. That is an instruction to the OPERATOR to bless
#                  bytes from outside the checkout into the adopter's recorded
#                  framework baseline: laundering, by verdict.
#   MISSING lane — the foreign digest matches the recorded baseline, so the run
#                  reports `MISSING (restorable)` for a file `_restore_file`
#                  then refuses to write: a verdict the repair cannot honour.
#
# The exposure is a WRONG ANSWER, not a write — round 7 closed the write — so
# the RED legs below keep the WRITE guard INTACT (asserted on the plant). That
# makes the reproduction attributable to the hash sites alone, and it lets every
# leg re-assert the byte claim: the count of adopter files carrying the foreign
# digest is asserted EXACTLY (0 where nothing was planted, 1 where the fixture
# itself planted it), never inferred from an exit code.
#
# Fixture shape follows R.8: a COPIED checkout, never the live tree. The
# predicate resolves against the SOURCE_DIR of the doctor.sh that RUNS, so a
# symlink planted under the real templates/ would poison the repository.
# ---------------------------------------------------------------------------
echo ""
echo "==> R.11 — the HASH sites refuse a source resolving outside the checkout (round 8)"

R11_REL="docs/BRANCH-PROTECTION.md"
R11_SRC_REL="templates/docs/BRANCH-PROTECTION.md"
R11_TPL_SHA="$( _sha "$SOURCE_DIR/$R11_SRC_REL" )"
R11_OUT="$WORKROOT/r11-outside"
mkdir -p "$R11_OUT/anc"
printf 'FOREIGN LEAF BYTES — outside the framework checkout (R.11)\n' \
  > "$R11_OUT/leaf.md"
printf 'FOREIGN ANCESTOR BYTES — outside the framework checkout (R.11)\n' \
  > "$R11_OUT/anc/BRANCH-PROTECTION.md"

# Count adopter files carrying a given file's exact bytes. Size-prefiltered so
# the whole tree can be scanned cheaply; `-size Nc` is exact bytes on both BSD
# and GNU find. Fed by heredoc, not a pipe, so the counter survives (bash 3.2).
_r11_foreign_hits() {  # $1 = adopter root, $2 = the foreign file
  _fh_sha="$( _sha "$2" )"
  _fh_sz="$( wc -c < "$2" | tr -d ' ' )"
  _fh_n=0
  while IFS= read -r _fh_f; do
    [ -n "$_fh_f" ] || continue
    [ -f "$_fh_f" ] || continue
    if [ "$( _sha "$_fh_f" 2>/dev/null )" = "$_fh_sha" ]; then
      _fh_n=$(( _fh_n + 1 ))
    fi
  done <<EOF
$( find "$1" -type f -size "${_fh_sz}c" 2>/dev/null )
EOF
  printf '%s\n' "$_fh_n"
}

# $1 = mirror dir, $2 = leaf|ancestor. Everything else is _mk_source_copy's
# faithful checkout; only the ONE source path is made hostile.
_r11_mk_mirror() {
  _mk_source_copy "$1" "$ROUTES" || return 1
  case "$2" in
    leaf)
      rm -f "$1/$R11_SRC_REL" || return 1
      ln -s "$R11_OUT/leaf.md" "$1/$R11_SRC_REL" || return 1
      [ -L "$1/$R11_SRC_REL" ] || return 1
      ;;
    ancestor)
      rm -rf "$1/templates/docs" || return 1
      ln -s "$R11_OUT/anc" "$1/templates/docs" || return 1
      [ -L "$1/templates/docs" ] || return 1
      ;;
    *) return 1 ;;
  esac
  return 0
}

# RED = the pre-cure doctor: the SAME file with the two hash-site guards
# removed and the guarded `_hash_file` line kept in place, nothing else
# touched. Anchored on the call, so a rename goes RED on the counts below.
_r11_strip_hash_guards() {  # $1 = real doctor.sh, $2 = RED output
  awk '/^ *if _wbm_source_confined "\$SOURCE_DIR" "\$src_rel"; then$/ {
         getline hashline; print hashline; skip = 4; next
       }
       skip > 0 { skip--; next }
       { print }' "$1" > "$2"
}

# Fixtures. Both rewrite the ONE manifest record (never append a second — a
# duplicate relpath makes doctor drop the path as ambiguous, the R.2 lesson).
_r11_seed_drift() {  # $1 = adopter, $2 = foreign file. dest = foreign bytes, baseline = template
  _sd_m="$1/.claude/.install-manifest.sha256"
  grep -v "  $R11_REL\$" "$_sd_m" > "$_sd_m.r11" || true
  mv "$_sd_m.r11" "$_sd_m" || return 1
  printf '%s  %s\n' "$R11_TPL_SHA" "$R11_REL" >> "$_sd_m"
  cp "$2" "$1/$R11_REL" || return 1
  return 0
}
_r11_seed_missing() {  # $1 = adopter, $2 = foreign file. dest deleted, baseline = foreign digest
  _sm_m="$1/.claude/.install-manifest.sha256"
  grep -v "  $R11_REL\$" "$_sm_m" > "$_sm_m.r11" || true
  mv "$_sm_m.r11" "$_sm_m" || return 1
  printf '%s  %s\n' "$( _sha "$2" )" "$R11_REL" >> "$_sm_m"
  rm -f "$1/$R11_REL" || return 1
  return 0
}

T11="$( fresh_install )" || { bad "R.11 install failed"; T11=""; }
if [ -n "$T11" ]; then
  if [ "$R11_TPL_SHA" = "$( _sha "$R11_OUT/leaf.md" )" ] \
     || [ "$R11_TPL_SHA" = "$( _sha "$R11_OUT/anc/BRANCH-PROTECTION.md" )" ]; then
    bad "R.11-control the foreign bytes collide with the template's — every verdict below would be vacuous"
  else
    ok "R.11-control the foreign files diverge from templates/$R11_REL (the verdicts discriminate)"
  fi
  [ "$( _r11_foreign_hits "$T11" "$R11_OUT/leaf.md" )" = "0" ] \
    && ok "R.11-control a pristine adopter carries ZERO files with the foreign digest (the byte counter has a real zero)" \
    || bad "R.11-control the pristine adopter already carries the foreign digest — the byte assertions cannot discriminate"

  for _r11_v in leaf ancestor; do
    R11_MIR="$WORKROOT/r11-mir-$_r11_v"
    if [ "$_r11_v" = "leaf" ]; then
      R11_FOR="$R11_OUT/leaf.md"
    else
      R11_FOR="$R11_OUT/anc/BRANCH-PROTECTION.md"
    fi
    if ! _r11_mk_mirror "$R11_MIR" "$_r11_v"; then
      bad "R.11[$_r11_v] could not build the hostile mirror — the legs below are scaffolding"
      continue
    fi
    ok "R.11[$_r11_v]-control the hostile source is planted (symlink on the $_r11_v, resolving outside the mirror)"

    R11_RED_DOC="$R11_MIR/scripts/doctor-red.sh"
    _r11_strip_hash_guards "$R11_MIR/scripts/doctor.sh" "$R11_RED_DOC"
    _r11_real="$( grep -c '_wbm_source_confined "\$SOURCE_DIR" "\$src_rel"' "$R11_MIR/scripts/doctor.sh" )"
    _r11_red="$( grep -c '_wbm_source_confined "\$SOURCE_DIR" "\$src_rel"' "$R11_RED_DOC" )" || _r11_red=0
    _r11_red_hash="$( grep -c '_hash_file "\$SOURCE_DIR/\$src_rel"' "$R11_RED_DOC" )" || _r11_red_hash=0
    _r11_red_write="$( grep -c '_wbm_source_confined "\$SOURCE_DIR" "\$_rr_src"' "$R11_RED_DOC" )" || _r11_red_write=0
    if [ "$_r11_real" -eq 2 ] && [ "$_r11_red" -eq 0 ] \
       && [ "$_r11_red_hash" -eq 2 ] && [ "$_r11_red_write" -eq 1 ] \
       && bash -n "$R11_RED_DOC" 2>/dev/null; then
      ok "R.11[$_r11_v]-control the RED removes both hash guards (2->0), keeps both _hash_file calls and the WRITE guard, and still parses"
    else
      bad "R.11[$_r11_v]-control plant rotted: guards real=$_r11_real red=$_r11_red, hash calls=$_r11_red_hash, write guard=$_r11_red_write (want 2/0/2/1) — the RED proves nothing"
      continue
    fi

    # ---- DRIFT lane (the site the finding named) --------------------------
    T11D_RED="$WORKROOT/r11-$_r11_v-drift-red"
    cp -R "$T11" "$T11D_RED" && _r11_seed_drift "$T11D_RED" "$R11_FOR"
    bash "$R11_RED_DOC" "$T11D_RED" --repair > "$T11D_RED/.r11.log" 2>&1
    if grep -q "DRIFT (baseline-stale" "$T11D_RED/.r11.log"; then
      ok "R.11[$_r11_v]-RED-drift the unguarded hash site reports 'DRIFT (baseline-stale ... run upgrade.sh)' — the wrong verdict reproduces"
    else
      bad "R.11[$_r11_v]-RED-drift no baseline-stale verdict appeared — the finding does not reproduce, so the GREEN below is not evidence"
    fi

    T11D="$WORKROOT/r11-$_r11_v-drift"
    cp -R "$T11" "$T11D" && _r11_seed_drift "$T11D" "$R11_FOR"
    bash "$R11_MIR/scripts/doctor.sh" "$T11D" --repair > "$T11D/.r11.log" 2>&1
    grep -q "DRIFT (baseline-stale" "$T11D/.r11.log" \
      && bad "R.11[$_r11_v]a the cured doctor still reports baseline-stale — the foreign source was hashed as framework content" \
      || ok "R.11[$_r11_v]a no 'baseline-stale' verdict: the cured doctor never hashed the unconfined source"
    grep -q "DRIFT (framework checkout no longer ships this file — not repairable): $R11_REL" "$T11D/.r11.log" \
      && ok "R.11[$_r11_v]b the cured doctor falls back to the EXISTING conservative verdict (not repairable)" \
      || bad "R.11[$_r11_v]b the conservative verdict is absent for $R11_REL — the refusal went somewhere else"
    grep -q "SOURCE-BLOCKED (source '$R11_SRC_REL' is not confined" "$T11D/.r11.log" \
      && ok "R.11[$_r11_v]c the refusal NAMES itself and the offending source (auditable, not silent)" \
      || bad "R.11[$_r11_v]c the refusal is silent — no SOURCE-BLOCKED breadcrumb names $R11_SRC_REL"
    _r11_hits="$( _r11_foreign_hits "$T11D" "$R11_FOR" )"
    [ "$_r11_hits" = "1" ] \
      && ok "R.11[$_r11_v]d exactly ONE adopter file carries the foreign digest — the one the fixture planted; doctor added none" \
      || bad "R.11[$_r11_v]d $_r11_hits adopter files carry the foreign digest (want 1, the planted one) — bytes moved"

    # ---- MISSING lane (the other hash site) -------------------------------
    T11M_RED="$WORKROOT/r11-$_r11_v-missing-red"
    cp -R "$T11" "$T11M_RED" && _r11_seed_missing "$T11M_RED" "$R11_FOR"
    bash "$R11_RED_DOC" "$T11M_RED" --repair > "$T11M_RED/.r11.log" 2>&1
    if grep -q "MISSING (restorable): $R11_REL" "$T11M_RED/.r11.log"; then
      ok "R.11[$_r11_v]-RED-missing the unguarded hash site calls the path 'MISSING (restorable)' from the OUTSIDE file's digest"
    else
      bad "R.11[$_r11_v]-RED-missing no 'MISSING (restorable)' verdict — the finding does not reproduce on this lane"
    fi
    _r11_red_hits="$( _r11_foreign_hits "$T11M_RED" "$R11_FOR" )"
    [ "$_r11_red_hits" = "0" ] \
      && ok "R.11[$_r11_v]-RED-missing even RED wrote zero foreign bytes — round 7's WRITE guard held, so this finding is a VERDICT flip, not a write" \
      || bad "R.11[$_r11_v]-RED-missing $_r11_red_hits foreign-digest files reached the adopter — the write guard regressed"

    T11M="$WORKROOT/r11-$_r11_v-missing"
    cp -R "$T11" "$T11M" && _r11_seed_missing "$T11M" "$R11_FOR"
    bash "$R11_MIR/scripts/doctor.sh" "$T11M" --repair > "$T11M/.r11.log" 2>&1
    grep -q "MISSING (restorable): $R11_REL" "$T11M/.r11.log" \
      && bad "R.11[$_r11_v]e the cured doctor still calls it restorable — the unconfined source was hashed" \
      || ok "R.11[$_r11_v]e the cured doctor no longer calls the path restorable"
    grep -q "MISSING (framework checkout no longer ships this file): $R11_REL" "$T11M/.r11.log" \
      && ok "R.11[$_r11_v]f the MISSING site falls back to the EXISTING conservative verdict too" \
      || bad "R.11[$_r11_v]f the conservative MISSING verdict is absent for $R11_REL"
    [ ! -e "$T11M/$R11_REL" ] \
      && ok "R.11[$_r11_v]g the destination stayed absent (no repair from outside the checkout)" \
      || bad "R.11[$_r11_v]g the destination was recreated despite the refusal"
    _r11_hits="$( _r11_foreign_hits "$T11M" "$R11_FOR" )"
    [ "$_r11_hits" = "0" ] \
      && ok "R.11[$_r11_v]h ZERO adopter files carry the foreign digest (bytes compared across the whole tree, not an exit code)" \
      || bad "R.11[$_r11_v]h $_r11_hits adopter files carry the foreign digest (want 0) — bytes from outside the checkout landed"
  done

  # Anti-over-rejection: the same cured doctor, a mirror with NO hostile
  # symlink, and a genuinely stale baseline must still reach baseline-stale.
  # Without this the greens above are satisfied by a doctor that refuses
  # everything.
  R11_CLEAN="$WORKROOT/r11-mir-clean"
  if _mk_source_copy "$R11_CLEAN" "$ROUTES"; then
    T11C="$WORKROOT/r11-clean-drift"
    cp -R "$T11" "$T11C"
    _r11_cm="$T11C/.claude/.install-manifest.sha256"
    grep -v "  $R11_REL\$" "$_r11_cm" > "$_r11_cm.r11" || true
    mv "$_r11_cm.r11" "$_r11_cm"
    # Baseline = a digest matching NEITHER side; destination = the real
    # template's bytes. That is exactly "the file matches the CURRENT
    # framework, the baseline is behind" — the verdict under test.
    printf '%s  %s\n' "0000000000000000000000000000000000000000000000000000000000000000" "$R11_REL" >> "$_r11_cm"
    cp "$SOURCE_DIR/$R11_SRC_REL" "$T11C/$R11_REL"
    bash "$R11_CLEAN/scripts/doctor.sh" "$T11C" --repair > "$T11C/.r11.log" 2>&1
    grep -q "DRIFT (baseline-stale" "$T11C/.r11.log" \
      && ok "R.11i a CONFINED source still reaches baseline-stale — the guard is not a blanket no" \
      || bad "R.11i the cured doctor refused a legitimate confined source — false positive on the hash sites"
    grep -q "SOURCE-BLOCKED" "$T11C/.r11.log" \
      && bad "R.11j the cured doctor emitted SOURCE-BLOCKED on a checkout with no symlinked source — the predicate over-fires" \
      || ok "R.11j no SOURCE-BLOCKED breadcrumb on a clean checkout (zero cost in production)"
  else
    bad "R.11i could not build the clean mirror — the anti-over-rejection control did not run"
  fi
fi

# ---------------------------------------------------------------------------
echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
