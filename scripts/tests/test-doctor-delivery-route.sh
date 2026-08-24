#!/usr/bin/env bash
# PLAN-183 W5 (S325) — doctor.sh resolves the delivery SOURCE through the
# SHARED route table (scripts/delivery-routes.tsv). Defect D4.
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
# R.1 — unit: the reader itself. Extracted by name from doctor.sh, so this
# also guards the function's existence: a rename or a move makes R.1 red
# instead of silently skipping.
# ---------------------------------------------------------------------------
echo "==> R.1 — _route_source resolves each destination"

FRAG="$WORKROOT/route_source.sh"
sed -n '/^_route_source() {$/,/^}$/p' "$DOCTOR" > "$FRAG"
if [ ! -s "$FRAG" ]; then
  bad "R.1 could not extract _route_source from doctor.sh (renamed or removed?)"
else
  ok "R.1 _route_source extracted from doctor.sh"
  HARNESS="$WORKROOT/harness.sh"
  {
    echo 'set -uo pipefail'
    echo "DELIVERY_ROUTES_TSV=\"$ROUTES\""
    cat "$FRAG"
    echo '_probe() { local rc=0 out; out="$( _route_source "$1" )" || rc=$?; printf "%s|%s\n" "$rc" "${out:-}"; }'
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
  sed "s|^DELIVERY_ROUTES_TSV=.*|DELIVERY_ROUTES_TSV=\"$MAL\"|" "$HARNESS" > "$MAL_HARNESS"
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

  # Missing table: rc=1 (identity fallback), never a crash. doctor.sh must
  # keep working on an adopter checkout that predates the table.
  MISSING_HARNESS="$WORKROOT/harness-missing.sh"
  sed "s|^DELIVERY_ROUTES_TSV=.*|DELIVERY_ROUTES_TSV=\"$WORKROOT/absent.tsv\"|" "$HARNESS" > "$MISSING_HARNESS"
  got="$( bash "$MISSING_HARNESS" "docs/BRANCH-PROTECTION.md" 2>/dev/null )"
  [ "$got" = "1|" ] && ok "R.1 absent table -> rc=1 (identity fallback, no crash)" \
                    || bad "R.1 absent table -> got '$got', want '1|'"
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

  # Anti-vacuity: the route must be UNRECORDED today (D3). If a future change
  # starts recording it, this fixture is redundant and should be simplified —
  # fail loudly rather than double-record.
  if [ "$( grep -c "  $REL\$" "$MAN" )" -ne 0 ]; then
    bad "R.2 $REL is ALREADY in the manifest — D3 changed; revisit this fixture"
  else
    ok "R.2 precondition: $REL unrecorded by install (D3, as measured)"
  fi

  printf '%s  %s\n' "$TPL_SHA" "$REL" >> "$MAN"
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
  printf '%s  %s\n' "$TPL_SHA" "$REL" >> "$T3/.claude/.install-manifest.sha256"
  rm -f "$T3/$REL"

  # Sabotage a COPY of the table; the real one is never touched.
  SABOTAGED="$WORKROOT/sabotaged-routes.tsv"
  sed "s|templates/docs/BRANCH-PROTECTION\.md|templates/docs/rotation-log.md|" "$ROUTES" > "$SABOTAGED"
  if cmp -s "$SABOTAGED" "$ROUTES"; then
    bad "R.3 sabotage was a no-op — the control proves nothing"
  else
    ok "R.3 sabotage applied to a table COPY (real table untouched)"
    DELIVERY_ROUTES_TSV="$SABOTAGED" bash "$DOCTOR" "$T3" --repair > "$T3/.sab.log" 2>&1
    if [ -f "$T3/$REL" ] && [ "$( _sha "$T3/$REL" )" = "$TPL_SHA" ]; then
      bad "R.3 repair STILL landed the template bytes with a sabotaged table — doctor.sh is not reading it"
    else
      ok "R.3 sabotaged table changed the outcome (the table is genuinely consulted)"
    fi
  fi
  [ -f "$ROUTES" ] && ok "R.3 real table intact after the control" || bad "R.3 real table damaged"
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
echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
