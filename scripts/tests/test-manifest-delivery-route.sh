#!/usr/bin/env bash
# PLAN-183 W5 (S327) — scripts/_framework_manifest_set.sh resolves the delivery
# SOURCE through the SHARED route table (scripts/delivery-routes.tsv). Defect D3.
#
# What D3 is: the baseline-manifest generator resolved every framework path as
# "$root/$rel", which assumes the SOURCE relpath equals the DESTINATION
# relpath. That is false for every route install.sh delivers out of
# `templates/`. On the UPGRADE path (FMS_HASH_ROOT=$SOURCE_DIR) the two
# consequences are:
#   * docs/BRANCH-PROTECTION.md hashes the ROOT HOMONYM — wrong bytes recorded
#     as the framework baseline; and
#   * .github/workflows/*.template has no homonym at all, hits the `continue`
#     and vanishes from the baseline in SILENCE.
# This file is the third reader's oracle, the sibling of
# scripts/tests/test-doctor-delivery-route.sh (doctor.sh, D4) and
# .claude/scripts/tests/test_parity_source_resolution.py (_parity_classify.py,
# D2).
#
# WHY THE EXPECTATIONS ARE NOT READ FROM THE TSV (debate convergence C3,
# measured S325): pointing a route row at a wrong-but-existing source kept all
# ten existing tests GREEN, because every assertion compared against the
# table's own claim. That is a tautology, not a test. Truth here is derived
# INDEPENDENTLY, by parsing the `install_docs_template` call-sites and the
# CODEOWNERS render site out of scripts/install.sh — the code that actually
# performs the copy. If the table and the installer disagree, this file goes
# RED and names the row.
#
# bash 3.2-safe. mktemp -d only (never a hardcoded path), so parallel runs
# never collide.
#
# Run:  bash scripts/tests/test-manifest-delivery-route.sh ; echo rc=$?
set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
GENERATOR="$SOURCE_DIR/scripts/_framework_manifest_set.sh"
INSTALLER="$SOURCE_DIR/scripts/install.sh"
ROUTES="$SOURCE_DIR/scripts/delivery-routes.tsv"

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-fms-route-XXXXXX )"
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

# rail round-6 F3 — there is NO environment override any more. The generator
# resolves its table from the tree it ships in, unconditionally, and that
# assignment clobbers anything inherited. Two mechanisms replace the retired
# switch, and every fixture leg below uses one of them:
#
#   * READER probes source the library in a child shell and assign the
#     library's INTERNAL _WBM_ROUTES_TSV *after* the source. That is
#     in-process code, the same seam upgrade.sh's snapshot uses — not an
#     environment channel. Assigning it BEFORE the source is now a no-op
#     (S.11f proves it), which is exactly the property under test.
#   * ENTRYPOINT legs (a real upgrade.sh / doctor.sh / install.sh run) get a
#     COPIED framework tree whose own scripts/delivery-routes.tsv is the
#     fixture: `_mk_source_copy`. Production takes no fixture at all.

ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

# ---------------------------------------------------------------------------
# S.0 — extract the reader BY NAME from the generator. A rename or a removal
# makes this RED instead of silently skipping every assertion below.
# ---------------------------------------------------------------------------
echo "==> S.0 — extract _wbm_route_src from _framework_manifest_set.sh"

[ -f "$ROUTES" ] && ok "S.0 shared route table exists at scripts/delivery-routes.tsv" \
                 || bad "S.0 shared route table MISSING at $ROUTES"

# The reader is _wbm_route_src plus the two validators it CALLS (rail round-1
# F2). Extracting only the entry point produced a harness where
# `_wbm_route_row_ok` was undefined — and because the reader is fail-CLOSED,
# the missing helper made EVERY lookup answer rc=2, including the real table's.
# That is the right product behaviour and the wrong instrument: the failure was
# in the harness, not in the table. Each function is extracted BY NAME and its
# presence asserted, so adding a third helper without wiring it here goes RED
# on the extraction rather than silently poisoning 6 assertions.
FRAG="$WORKROOT/wbm_route_src.sh"
: > "$FRAG"
# rail round-6 F2 added _wbm_route_table_gate + _wbm_route_table_ok to the set
# the readers CALL. A fragment without them makes every lookup answer rc=2
# (command-not-found under `|| return 2`), which is a broken harness, not a
# product finding — so they are extracted BY NAME here like the rest.
for _fn in _wbm_route_relpath_ok _wbm_route_domain_ok _wbm_route_row_ok \
           _wbm_route_table_ok _wbm_route_table_gate _wbm_route_meta _wbm_route_src; do
  sed -n "/^${_fn}() {\$/,/^}\$/p" "$GENERATOR" >> "$FRAG"
  if ! grep -q "^${_fn}() {" "$FRAG"; then
    bad "S.0 could not extract $_fn from _framework_manifest_set.sh (renamed or removed?)"
    echo ""
    echo "==> RESULT: $PASS passed, $FAIL failed"
    exit 1
  fi
done
ok "S.0 _wbm_route_src (+ its relpath/row/table validators) extracted from _framework_manifest_set.sh"

# Probe harness: prints "<rc>|<stdout>" for one destination, against whichever
# table $1 names.
#
# rail round-6 F3 — this is a FRAGMENT harness: it carries copies of the reader
# functions and names the table in its own first line, so no environment
# variable and no production entrypoint is involved. `_WBM_ROUTES_TSV` here is
# the library's internal state variable, assigned by the code that hosts the
# functions — the same seam upgrade.sh uses for its snapshot.
HARNESS="$WORKROOT/harness.sh"
{
  echo 'set -uo pipefail'
  echo '_WBM_ROUTES_TSV="$1"'
  cat "$FRAG"
  echo '_probe() { local rc=0 out; out="$( _wbm_route_src "$2" )" || rc=$?; printf "%s|%s\n" "$rc" "${out:-}"; }'
  echo '_probe "$1" "$2"'
} > "$HARNESS"

_probe() {  # $1=table $2=dest -> "<rc>|<src>"
  bash "$HARNESS" "$1" "$2" 2>/dev/null
}

# --- rail round-6 F3: a COPIED FRAMEWORK TREE ------------------------------
# The mechanism that replaces the retired environment override for any leg
# that must run a REAL entrypoint. $1 = directory to build; $2 = the table to
# install as its scripts/delivery-routes.tsv, or the literal NONE to leave the
# copy with NO table at all.
#
# Everything except scripts/ is symlinked (cheap, and the trees are read-only
# on these paths); scripts/ is a real copy, because the entrypoint must be a
# real file: doctor.sh RESOLVES symlinks to find its own SOURCE_DIR
# (doctor.sh:155-166), so a symlinked doctor.sh would silently read the REAL
# repo's table and the fixture would measure nothing. install.sh/upgrade.sh
# use BASH_SOURCE as given, and the library derives _WBM_ROUTES_TSV from its
# OWN BASH_SOURCE — which is what makes the copy's table authoritative for the
# copy's run.
#
# rail round-7 F2 — templates/ joins scripts/ as a REAL copy: delivery sources
# are now PHYSICALLY confined to the running checkout (_wbm_source_confined),
# so a symlinked templates/ would resolve every route source into the REAL
# repo, outside this fixture's SOURCE_DIR, and every leg would measure a
# confinement refusal instead of its subject. 360 KB / 34 files, measured.
_mk_source_copy() {  # $1=dir $2=table|NONE
  mkdir -p "$1" || return 1
  for _msc_e in "$SOURCE_DIR"/* "$SOURCE_DIR"/.[!.]*; do
    [ -e "$_msc_e" ] || continue
    _msc_b="$( basename "$_msc_e" )"
    case "$_msc_b" in scripts|templates) continue ;; esac
    ln -s "$_msc_e" "$1/$_msc_b" 2>/dev/null || true
  done
  cp -R "$SOURCE_DIR/scripts" "$1/scripts" || return 1
  cp -R "$SOURCE_DIR/templates" "$1/templates" || return 1
  rm -f "$1/scripts/delivery-routes.tsv" || return 1
  if [ "$2" != "NONE" ]; then
    cp "$2" "$1/scripts/delivery-routes.tsv" || return 1
  fi
  return 0
}

# ---------------------------------------------------------------------------
# S.1 — INDEPENDENT TRUTH: what does install.sh actually copy?
# Parsed from the installer's call-sites, never from the table.
# ---------------------------------------------------------------------------
echo "==> S.1 — derive (source -> destination) truth from install.sh call-sites"

TRUTH="$WORKROOT/truth.tsv"        # dest \t src \t kind(identity|rendered)
REGISTRATIONS="$WORKROOT/reg.tsv"  # dest \t src   (from _register_delivered_template)
python3 - "$INSTALLER" "$TRUTH" "$REGISTRATIONS" <<'PY'
import io, re, sys

installer, truth_out, reg_out = sys.argv[1], sys.argv[2], sys.argv[3]
src = io.open(installer, encoding="utf-8").read()
# Join backslash line-continuations so multi-line calls parse as one.
flat = re.sub(r"\\\n\s*", " ", src)

def pairs(fn):
    out = []
    for m in re.finditer(r'\b%s\s+"([^"]+)"\s+"([^"]+)"' % fn, flat):
        out.append((m.group(1), m.group(2)))
    return out

# install_docs_template <src_rel> <dst_rel> — the verbatim copy call-site.
identity = [(dst, s) for (s, dst) in pairs("install_docs_template")]

# _register_delivered_template <dst_rel> <src_rel> — the W5 registration
# call-site. Extracted separately so a typo there is caught by S.2b instead of
# silently agreeing with itself.
regs = pairs("_register_delivered_template")

# The RENDERED site: sed s/{{OWNER_HANDLE}}/.../ <codeowners_src> > <dst>.
# Both operands are variables, so resolve them from their assignments rather
# than assuming the literal paths.
rendered = []
co_src = re.search(r'codeowners_src="\$SOURCE_DIR/([^"]+)"', flat)
co_dst = re.search(r'local dst="\$TARGET/(\.github/CODEOWNERS)"', flat)
has_sed = re.search(r'sed "s/\{\{OWNER_HANDLE\}\}/\$GITHUB_OWNER/g" "\$codeowners_src" > "\$dst"', flat)
if co_src and co_dst and has_sed:
    rendered.append((co_dst.group(1), co_src.group(1)))

with io.open(truth_out, "w", encoding="utf-8") as fh:
    for dst, s in identity:
        fh.write("%s\t%s\tidentity\n" % (dst, s))
    for dst, s in rendered:
        fh.write("%s\t%s\trendered\n" % (dst, s))
with io.open(reg_out, "w", encoding="utf-8") as fh:
    for dst, s in regs:
        fh.write("%s\t%s\n" % (dst, s))
PY

TRUTH_N="$( grep -c . "$TRUTH" 2>/dev/null || echo 0 )"
if [ "$TRUTH_N" -ge 5 ]; then
  ok "S.1 parsed $TRUTH_N delivery call-sites out of install.sh"
else
  bad "S.1 parsed only $TRUTH_N delivery call-sites out of install.sh (expected >= 5) — the parser drifted from the installer; every assertion below would be vacuous"
fi

# The rendered site must be found, or S.4 silently stops testing anything.
if grep -q "	rendered\$" "$TRUTH"; then
  ok "S.1 the RENDERED CODEOWNERS call-site was located (S.4 is not vacuous)"
else
  bad "S.1 the RENDERED CODEOWNERS call-site was NOT located in install.sh — S.4 would be vacuous"
fi

# ---------------------------------------------------------------------------
# S.2 — the reader agrees with the installer, route by route.
# ---------------------------------------------------------------------------
echo "==> S.2 — _wbm_route_src answers match the install.sh call-sites"

while IFS="$( printf '\t' )" read -r t_dest t_src t_kind; do
  [ -n "${t_dest:-}" ] || continue
  res="$( _probe "$ROUTES" "$t_dest" )"
  rc="${res%%|*}"; got="${res#*|}"
  case "$t_kind" in
    identity)
      if [ "$rc" = "0" ] && [ "$got" = "$t_src" ]; then
        ok "S.2 $t_dest -> $t_src (rc=0)"
      else
        bad "S.2 $t_dest: install.sh copies from '$t_src' but the route table answers rc=$rc src='$got' — fix the row for '$t_dest' in scripts/delivery-routes.tsv"
      fi
      ;;
    rendered)
      if [ "$rc" = "2" ] && [ -z "$got" ]; then
        ok "S.2 $t_dest is RENDERED -> rc=2, no copiable source"
      else
        bad "S.2 $t_dest is RENDERED in install.sh but the route table answers rc=$rc src='$got' — a rendered destination must never be copiable (row '$t_dest')"
      fi
      ;;
  esac
done < "$TRUTH"

echo "==> S.2b — the W5 registration call-sites name the same source as the copy"
while IFS="$( printf '\t' )" read -r r_dest r_src; do
  [ -n "${r_dest:-}" ] || continue
  exp="$( awk -F'\t' -v d="$r_dest" '$1 == d { print $2; exit }' "$TRUTH" )"
  if [ -z "$exp" ]; then
    bad "S.2b _register_delivered_template names destination '$r_dest', which no install_docs_template call-site delivers"
  elif [ "$exp" = "$r_src" ]; then
    ok "S.2b registration of $r_dest names the copied source"
  else
    bad "S.2b _register_delivered_template '$r_dest' '$r_src' disagrees with the copy call-site ('$exp') — the byte-compare would compare the WRONG file"
  fi
done < "$REGISTRATIONS"

# ---------------------------------------------------------------------------
# S.3 — POSITIVE CONTROL: a row pointed at a wrong-but-existing source must
# turn this file RED and name the row. Runs against a COPY; the real table is
# never mutated.
# ---------------------------------------------------------------------------
echo "==> S.3 — positive control: wrong-but-existing source"

BAD_TSV="$WORKROOT/routes-wrong-source.tsv"
# Re-point docs/BRANCH-PROTECTION.md at a DIFFERENT file that really exists,
# so the failure cannot be blamed on a missing path.
DECOY="templates/docs/rotation-log.md"
if [ ! -f "$SOURCE_DIR/$DECOY" ]; then
  bad "S.3 decoy source $DECOY does not exist — the control would test 'missing file', not 'wrong file'"
else
  awk -F'\t' -v OFS='\t' -v decoy="$DECOY" '
    $1 == "docs/BRANCH-PROTECTION.md" { $2 = decoy } { print }' "$ROUTES" > "$BAD_TSV"
  res="$( _probe "$BAD_TSV" "docs/BRANCH-PROTECTION.md" )"
  rc="${res%%|*}"; got="${res#*|}"
  real="$( awk -F'\t' '$1 == "docs/BRANCH-PROTECTION.md" { print $2; exit }' "$TRUTH" )"
  if [ "$rc" = "0" ] && [ "$got" = "$DECOY" ] && [ "$got" != "$real" ]; then
    ok "S.3 the sabotaged table answers '$got' while install.sh copies '$real' — S.2 would go RED naming the row"
  else
    bad "S.3 sabotage did not take effect (rc=$rc src='$got'): the S.2 assertions are NOT discriminating and this suite is blind"
  fi
fi

# ---------------------------------------------------------------------------
# S.4 — POSITIVE CONTROL: a rendered row must never become copiable, however
# the row is damaged. `${_wbm_rs_transform:-identity}` was the rail S325
# fail-OPEN finding; a truncated row must stay rc=2.
# ---------------------------------------------------------------------------
echo "==> S.4 — positive control: rendered + malformed rows stay non-copiable"

TRUNC_TSV="$WORKROOT/routes-truncated.tsv"
awk -F'\t' -v OFS='\t' '
  $1 == "docs/rotation-log.md" { print $1, $2; next } { print }' "$ROUTES" > "$TRUNC_TSV"
res="$( _probe "$TRUNC_TSV" "docs/rotation-log.md" )"
rc="${res%%|*}"; got="${res#*|}"
if [ "$rc" = "2" ] && [ -z "$got" ]; then
  ok "S.4 a truncated row (transform column absent) is rc=2, not silently identity"
else
  bad "S.4 truncated row answered rc=$rc src='$got' — fail-OPEN: an absent transform became copiable"
fi

EMPTYSRC_TSV="$WORKROOT/routes-emptysrc.tsv"
awk -F'\t' -v OFS='\t' '
  $1 == "docs/rotation-log.md" { $2 = "" } { print }' "$ROUTES" > "$EMPTYSRC_TSV"
res="$( _probe "$EMPTYSRC_TSV" "docs/rotation-log.md" )"
rc="${res%%|*}"
if [ "$rc" = "2" ]; then
  ok "S.4 an identity row with an EMPTY source is rc=2 (malformed), not rc=0 with an empty path"
else
  bad "S.4 empty-source row answered rc=$rc — a malformed row became copiable"
fi

res="$( _probe "$ROUTES" "PROTOCOL.md" )"
rc="${res%%|*}"
if [ "$rc" = "1" ]; then
  ok "S.4 a path with NO row answers rc=1 (identity-mapped: callers keep today's behaviour)"
else
  bad "S.4 an unrouted path answered rc=$rc, expected rc=1 — every framework path would change resolution"
fi

# ---------------------------------------------------------------------------
# S.5 — POSITIVE CONTROL: table missing => fail-CLOSED. The reader answers
# rc=2, and the generator must then record NOTHING at all rather than silently
# resolving every path as "$root/$rel" (D3 itself).
#
# rail round-6 F2 CHANGED THIS CONTRACT DELIBERATELY: a missing table used to
# answer rc=1, and rc=1 is the "no row for this destination" answer every
# caller resolves with the identity fallback — which for an ABSENT table means
# the fallback applies to EVERY path, i.e. D3/D4 arriving through a missing
# file (that is round 4 F3, which had to be closed in doctor.sh separately
# because the reader itself degraded). "No table" is now one of the ways a
# table is unusable, and unusable answers 2 everywhere.
# ---------------------------------------------------------------------------
echo "==> S.5 — positive control: table missing is fail-CLOSED"

res="$( _probe "$WORKROOT/does-not-exist.tsv" "docs/BRANCH-PROTECTION.md" )"
rc="${res%%|*}"; got="${res#*|}"
if [ "$rc" = "2" ] && [ -z "$got" ]; then
  ok "S.5 reader with no table answers rc=2 (fail-closed) and no source"
else
  bad "S.5 reader with no table answered rc=$rc src='$got' — want rc=2; rc=1 would send every caller to the identity fallback"
fi

# The generator-level half: FMS_DELIVERED_TEMPLATES non-empty + no table must
# record nothing at all and say so on stderr.
GEN_OUT="$WORKROOT/gen.out"
GEN_ERR="$WORKROOT/gen.err"
GEN_ROOT="$WORKROOT/genroot"
mkdir -p "$GEN_ROOT/docs"
printf 'adopter bytes\n' > "$GEN_ROOT/docs/BRANCH-PROTECTION.md"
(
  # shellcheck source=/dev/null
  . "$SOURCE_DIR/scripts/_hash_lib.sh"
  # shellcheck source=/dev/null
  . "$GENERATOR"
  # Read by _wbm_route_src at CALL time, and assigned AFTER the source so it
  # replaces the shipped table the library resolved at source time (rail
  # round-6 F3: a pre-source assignment is a no-op). Not exported — it is the
  # library's internal state, not an environment knob.
  # shellcheck disable=SC2034
  _WBM_ROUTES_TSV="$WORKROOT/does-not-exist.tsv"
  export FMS_ROOT="$GEN_ROOT"
  export FMS_HASH_ROOT="$SOURCE_DIR"
  export FMS_PROFILE_PARTS="core"
  export FMS_DELIVERED_TEMPLATES="docs/BRANCH-PROTECTION.md"
  _write_baseline_manifest "$GEN_ROOT/.manifest" >/dev/null 2>"$GEN_ERR"
) > "$GEN_OUT" 2>&1
if [ -f "$GEN_ROOT/.manifest" ] && grep -q "  docs/BRANCH-PROTECTION.md\$" "$GEN_ROOT/.manifest" 2>/dev/null; then
  bad "S.5 generator RECORDED docs/BRANCH-PROTECTION.md with no route table — fail-OPEN, this is D3 itself"
else
  ok "S.5 generator recorded nothing for the delivered template with no route table (fail-closed)"
fi
# rail round-6 F2 — the whole WRITE is abandoned now, not just the delivered
# templates: on the FMS_HASH_ROOT lane every path would resolve through the
# identity fallback, and a near-empty manifest replacing a correct one is what
# uninstall and doctor read next. The message says so by name.
if [ -f "$GEN_ROOT/.manifest" ]; then
  bad "S.5 a manifest was WRITTEN with no usable route table — the previous one would have been replaced by a near-empty file"
else
  ok "S.5 no manifest written at all with no usable route table (the one on disk survives)"
fi
if grep -q "baseline manifest NOT written" "$GEN_ERR" 2>/dev/null \
   && grep -q "delivery-route table is" "$GEN_ERR" 2>/dev/null; then
  ok "S.5 generator said so on stderr, naming the table (the refusal is not silent)"
else
  bad "S.5 generator refused SILENTLY — an unusable table must be named on stderr (see $GEN_ERR)"
fi

# ---------------------------------------------------------------------------
# S.6 — the rendered route never copies bytes THROUGH the generator: enumerate
# .github/CODEOWNERS on the FMS_HASH_ROOT lane and assert no record appears and
# the path is NAMED.
#
# LANE-AGNOSTIC ON PURPOSE (OQ-4). The generator can refuse a rendered
# destination on either lane, with a different message each time:
#   * non-conditional lane -> "delivered through a TRANSFORM" (the route
#     reader's rc=2 breadcrumb);
#   * conditional lane     -> "declared no hash_source" (the pre-existing
#     fail-closed branch, when no FMS_HASH_SOURCE_* is exported).
# The CONTRACT this file defends is neither of those wordings: it is "never
# recorded from source bytes, and never dropped in SILENCE". Asserting one
# wording would make the suite a vote for one lane and turn the other into a
# false RED — the measurement, not the test, is where the lane is decided.
# ---------------------------------------------------------------------------
echo "==> S.6 — a RENDERED destination is never recorded from source bytes"

GEN2="$WORKROOT/genroot2"
GEN2_ERR="$WORKROOT/gen2.err"
mkdir -p "$GEN2/.github"
printf '# rendered for @someone\n' > "$GEN2/.github/CODEOWNERS"
(
  # shellcheck source=/dev/null
  . "$SOURCE_DIR/scripts/_hash_lib.sh"
  # shellcheck source=/dev/null
  . "$GENERATOR"
  export FMS_ROOT="$GEN2"
  export FMS_HASH_ROOT="$SOURCE_DIR"
  export FMS_PROFILE_PARTS="core"
  export FMS_DELIVERED_TEMPLATES=".github/CODEOWNERS"
  _write_baseline_manifest "$GEN2/.manifest" >/dev/null 2>"$GEN2_ERR"
) >/dev/null 2>&1
if [ -f "$GEN2/.manifest" ] && grep -q "  \.github/CODEOWNERS\$" "$GEN2/.manifest" 2>/dev/null; then
  recorded="$( awk '{ i = index($0, "  "); if (i && substr($0, i+2) == ".github/CODEOWNERS") print substr($0, 1, i-1) }' "$GEN2/.manifest" )"
  live="$( ( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$SOURCE_DIR/.github/CODEOWNERS" 2>/dev/null ) || true )"
  if [ -n "$live" ] && [ "$recorded" = "$live" ]; then
    bad "S.6 the generator recorded THIS repository's live .github/CODEOWNERS ($recorded) as the adopter's baseline — the maintainer-handle leak class (A3)"
  else
    bad "S.6 a RENDERED destination was recorded ($recorded); rendered bytes exist in no checkout, so any source-derived digest is wrong"
  fi
else
  ok "S.6 rendered .github/CODEOWNERS is NOT recorded from source bytes on the FMS_HASH_ROOT lane"
fi
if grep -q "\.github/CODEOWNERS" "$GEN2_ERR" 2>/dev/null \
   && grep -qE "delivered through a TRANSFORM|declared no hash_source" "$GEN2_ERR" 2>/dev/null; then
  ok "S.6 the skip is NAMED on stderr (silence was the defect, not the skip)"
else
  bad "S.6 the rendered destination was dropped SILENTLY — the path must be named on stderr with a refusal reason"
fi

# ---------------------------------------------------------------------------
# S.7 (rail round-1 F2) — the table is UNTRUSTED INPUT.
#
# The table is a FILE the framework ships, and a shipped file is still input:
# a partial checkout, a bad merge or a tampered tree all reach these fields.
# Round 6 F3 closed the ENVIRONMENT channel; the row validators below are what
# the CONTENT has to satisfy, and they are what these legs exercise (through a
# fragment harness, never a production entrypoint).
# MEASURED PRE-CURE (S327), with the SAME harness
# used below: a row with `dest=../../outside/PWNED.md` was accepted rc=0 by
# both readers and upgrade.sh's `_up_deliver_template` wrote 536 real bytes to
# "$TARGET/../../outside/PWNED.md" — outside the requested target, before any
# ownership gate. A `src=../../../../etc/passwd` row reached
# `cp "$SOURCE_DIR/$src"` the same way.
#
# Two layers are asserted, independently, because either alone is one bug from
# being useless:
#   S.7a  the READER refuses the row (rc=2 fail-closed, NEVER rc=1: rc=1 means
#         "no row" and the callers answer that with the identity fallback,
#         which for a poisoned row hands back exactly the D3 behaviour).
#   S.7b  the WRITE SITE refuses it too, and NOTHING lands outside the target.
#         Driven through upgrade.sh's own _up_deliver_template, extracted BY
#         NAME so a rename goes RED here instead of quietly proving nothing.
# ---------------------------------------------------------------------------
echo "==> S.7 — route rows that escape the target are refused (F2)"

HOSTILE="$WORKROOT/hostile.tsv"
{
  printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
  printf '../../outside/PWNED.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tescaping dest\n'
  printf 'docs/rotation-log.md\t../../../../etc/passwd\tidentity\t-\tx\tescaping src\n'
  printf '/etc/cron.d/pwn\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tabsolute dest\n'
  printf 'docs/a/../../../b.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tembedded dotdot\n'
} > "$HOSTILE"

for hostile_dest in "../../outside/PWNED.md" "docs/rotation-log.md" "/etc/cron.d/pwn" "docs/a/../../../b.md"; do
  got="$( _probe "$HOSTILE" "$hostile_dest" )"
  case "$got" in
    2\|*) ok "S.7a reader refuses '$hostile_dest' fail-closed (rc=2)" ;;
    1\|*) bad "S.7a reader answered rc=1 (no row) for '$hostile_dest' — callers read that as 'identity route', which is the D3 fallback returning" ;;
    *)    bad "S.7a reader ACCEPTED '$hostile_dest' (got '$got') — a route row can name a path outside the target" ;;
  esac
done

# The VALID table must still answer, or S.7a would pass by refusing everything.
good="$( _probe "$ROUTES" "docs/BRANCH-PROTECTION.md" )"
case "$good" in
  0\|templates/docs/BRANCH-PROTECTION.md) ok "S.7a-control the real table still resolves normally (rc=0)" ;;
  *) bad "S.7a-control the validator broke the REAL table: docs/BRANCH-PROTECTION.md -> '$good'" ;;
esac

# _wbm_route_dests must DROP the rejected rows, and _wbm_route_rows_total must
# still count them — that difference is what upgrade.sh turns into a named
# PRECONDITION FAILED instead of a silent continue.
DESTS_HARNESS="$WORKROOT/dests.sh"
{
  echo 'set -uo pipefail'
  echo '_WBM_ROUTES_TSV="$1"'
  sed -n '/^_wbm_route_relpath_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_domain_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_row_ok() {$/,/^}$/p' "$GENERATOR"
  # rail round-6 F2 — the table gate the three readers call.
  sed -n '/^_wbm_route_table_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_table_gate() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_dests() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_rows_total() {$/,/^}$/p' "$GENERATOR"
  echo 'printf "dests=%s rows=%s\n" "$( _wbm_route_dests 2>/dev/null | grep -c . )" "$( _wbm_route_rows_total 2>/dev/null )"'
} > "$DESTS_HARNESS"
counts="$( bash "$DESTS_HARNESS" "$HOSTILE" 2>/dev/null )"
if [ "$counts" = "dests=0 rows=4" ]; then
  ok "S.7a-counts every hostile row is dropped but still counted ($counts) — the drop is OBSERVABLE"
else
  bad "S.7a-counts expected 'dests=0 rows=4' from the hostile table, got '$counts' — a silent drop is indistinguishable from an empty table"
fi
counts_real="$( bash "$DESTS_HARNESS" "$ROUTES" 2>/dev/null )"
case "$counts_real" in
  "dests=6 rows=6") ok "S.7a-counts-control the real table yields 6 of 6 (no valid row is collateral damage)" ;;
  *) bad "S.7a-counts-control the real table yields '$counts_real', expected 'dests=6 rows=6'" ;;
esac

# --- S.7b: drive the WRITE SITE ------------------------------------------
WRITE_ROOT="$WORKROOT/writesite"
FAKE_TARGET="$WRITE_ROOT/deep/target"
mkdir -p "$FAKE_TARGET"
WRITE_HARNESS="$WORKROOT/writesite.sh"
UPGRADER="$SOURCE_DIR/scripts/upgrade.sh"
{
  echo 'set -uo pipefail'
  echo '_WBM_ROUTES_TSV="$1"'
  echo 'TARGET="$2"'
  echo 'SOURCE_DIR="$3"'
  echo 'DRY_RUN=0'
  echo 'BAK_DIR="$TARGET/.bak"'
  sed -n '/^_wbm_route_relpath_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_domain_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_row_ok() {$/,/^}$/p' "$GENERATOR"
  # rail round-6 F2 — the table gate the three readers call.
  sed -n '/^_wbm_route_table_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_table_gate() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_meta() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_src() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_dests() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_up_tpl_symlink_refuses() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_tpl_confined_refuses() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_tpl_write() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_tpl_register() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_tpl_generations() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_deliver_template() {$/,/^}$/p' "$UPGRADER"
  echo '_hash_file() { shasum -a 256 "$1" 2>/dev/null | cut -d" " -f1; }'
  echo '_hash_stdin() { shasum -a 256 2>/dev/null | cut -d" " -f1; }'
  echo '_path_is_skipped() { return 1; }'
  echo '_baseline_lookup() { printf ""; }'
  echo '_UP_TPL_SKIPPED=0; _UP_TPL_PRESERVED=0; _UP_TPL_INSTALLED=0'
  echo '_UP_TPL_REFRESHED=0; _UP_TPL_IDENTICAL=0'
  echo '_D1_DELIVERED_TEMPLATES=""; _D1_CODEOWNERS_REGISTERED=0'
  # Deliberately bypass _wbm_route_dests here: this leg must prove the WRITE
  # SITE refuses on its own, not that the reader filtered the row first.
  echo 'for d in "../../outside/PWNED.md" "docs/rotation-log.md"; do'
  echo '  _up_deliver_template "$d" "$SOURCE_DIR/templates/docs/rotation-log.md" "templates/docs/rotation-log.md" ""'
  echo 'done'
} > "$WRITE_HARNESS"
for fn in _up_tpl_confined_refuses _up_deliver_template; do
  if ! grep -q "^${fn}() {" "$WRITE_HARNESS"; then
    bad "S.7b could not extract $fn from upgrade.sh (renamed or removed?) — this leg would prove nothing"
  fi
done
bash "$WRITE_HARNESS" "$HOSTILE" "$FAKE_TARGET" "$SOURCE_DIR" > "$WORKROOT/writesite.log" 2>&1
if [ -e "$WRITE_ROOT/outside/PWNED.md" ]; then
  bad "S.7b _up_deliver_template WROTE outside the target: $WRITE_ROOT/outside/PWNED.md exists"
else
  ok "S.7b _up_deliver_template wrote NOTHING outside the target"
fi
if grep -q 'resolves outside the target\|not a confined relative path' "$WORKROOT/writesite.log" 2>/dev/null; then
  ok "S.7b the write-site refusal is NAMED on stderr"
else
  bad "S.7b the escaping destination was dropped with no named refusal (see $WORKROOT/writesite.log)"
fi
# Control: the legitimate destination in the SAME run still got delivered, so
# S.7b is not passing because the harness delivers nothing at all.
if [ -f "$FAKE_TARGET/docs/rotation-log.md" ]; then
  ok "S.7b-control the confined destination WAS delivered in the same run (the refusal is targeted, not blanket)"
else
  bad "S.7b-control docs/rotation-log.md was not delivered — the harness refused everything, so S.7b is vacuous"
fi

# ---------------------------------------------------------------------------
# S.8 (rail round-3 F1) — FMS_DELIVERED_TEMPLATES is UNTRUSTED, and the shape
# predicate alone was not enough.
#
# MEASURED PRE-CURE (S327): the generator consumed the list with an UNQUOTED
# `for` under IFS=newline, so every word was PATHNAME-EXPANDED before the
# predicate ever saw it. With `FMS_DELIVERED_TEMPLATES='docs/*'` and the repo
# root as the working directory, `_framework_target_entries` emitted 125
# `docs/...` relpaths — each one perfectly confined, perfectly relative, and
# every one an ADOPTER file recorded as framework-owned. A manifest-honouring
# uninstall deletes on a hash match.
#
# The cure is three walls and this section asserts each independently:
#   S.8a/b  no pathname expansion (quoted read loop + `set -f`);
#   S.8c    the predicate refuses glob metacharacters outright;
#   S.8d    the WHITELIST — only a destination the shared table DECLARES may
#           be recorded, whatever its shape. That is the wall that does not
#           need the next unsafe shape to be imagined first.
# ---------------------------------------------------------------------------
echo "==> S.8 — the delivered-template list is untrusted (F1)"

# Emit _framework_target_entries with $1 as FMS_DELIVERED_TEMPLATES, from the
# REPO ROOT as cwd (the cwd is what makes a glob expand to something).
_entries_from_root() {
  (
    cd "$SOURCE_DIR" || exit 9
    # shellcheck source=/dev/null
    . "$GENERATOR"
    export FMS_PROFILE_PARTS="core"
    FMS_DELIVERED_TEMPLATES="$1"
    _framework_target_entries 2>"$WORKROOT/s8.err"
  )
}

# Not vacuous: the glob must have material to expand to, or S.8a proves nothing.
GLOB_HITS=0
for _g in "$SOURCE_DIR"/docs/*.md; do
  [ -f "$_g" ] && GLOB_HITS=$(( GLOB_HITS + 1 ))
done
if [ "$GLOB_HITS" -ge 2 ]; then
  ok "S.8-control 'docs/*' has $GLOB_HITS files to expand to from the repo root (the leg below is not vacuous)"
else
  bad "S.8-control only $GLOB_HITS file(s) under docs/ — a glob with nothing to match cannot demonstrate the defect"
fi

GOT="$( _entries_from_root 'docs/*' | grep -c '^docs/' )"
if [ "$GOT" -eq 0 ]; then
  ok "S.8a an env-injected 'docs/*' records ZERO entries (pre-cure: $GLOB_HITS adopter files became framework-owned)"
else
  bad "S.8a an env-injected 'docs/*' recorded $GOT docs/ entries — the list is still pathname-expanded, and every hit is an adopter file a manifest-honouring uninstall may delete"
fi
if grep -q "delivered-template entry REJECTED" "$WORKROOT/s8.err" 2>/dev/null; then
  ok "S.8b the rejection is NAMED on stderr (a silent drop and a refusal look identical)"
else
  bad "S.8b 'docs/*' was dropped SILENTLY — see $WORKROOT/s8.err"
fi

# The predicate itself, driven through the extracted fragment: glob
# metacharacters are refused even when nothing expands them.
for _meta in 'docs/*' 'docs/a?.md' 'docs/x[1].md' 'docs/]y.md'; do
  if bash -c '
      set -uo pipefail
      '"$( sed -n '/^_wbm_route_relpath_ok() {$/,/^}$/p' "$GENERATOR" )"'
      _wbm_route_relpath_ok "$1"' _ "$_meta" 2>/dev/null; then
    bad "S.8c the relpath predicate ACCEPTED '$_meta' — a glob metacharacter is not a path this framework ships"
  else
    ok "S.8c the relpath predicate refuses '$_meta'"
  fi
done

# THE WHITELIST. `docs/adopter-owned.md` is confined, relative, glob-free and
# entirely legitimate-looking — it is simply not a destination the table
# declares, and that alone must be disqualifying.
GOT="$( _entries_from_root 'docs/adopter-owned.md' | grep -c '^docs/adopter-owned\.md$' )"
if [ "$GOT" -eq 0 ]; then
  ok "S.8d an UNDECLARED but well-formed relpath is refused (the whitelist, not the shape rules)"
else
  bad "S.8d 'docs/adopter-owned.md' entered the manifest set — any confined relpath can still be baselined from the environment"
fi
if grep -q "not a destination declared in" "$WORKROOT/s8.err" 2>/dev/null; then
  ok "S.8d-named the whitelist refusal names the path and the table"
else
  bad "S.8d-named the undeclared entry was dropped without naming the reason"
fi

# Control: every REAL destination still passes, or S.8 would be passing by
# refusing everything.
# Header and comment rows are skipped exactly as the readers skip them
# (`case "$dest" in \#*|dest)`) — `NR > 1` is NOT that rule: the table carries
# comment lines ABOVE the header, so the header itself survives NR>1 and the
# control then measures 7 destinations where the table declares 6.
DECLARED="$( awk -F '\t' '$1 != "" && $1 != "dest" && $1 !~ /^#/ { print $1 }' "$ROUTES" )"
DECL_N="$( printf '%s\n' "$DECLARED" | grep -c . )"
KEPT="$( _entries_from_root "$DECLARED" | grep -cE '^(docs|\.github)/' )"
if [ "$KEPT" -eq "$DECL_N" ] && [ "$DECL_N" -gt 0 ]; then
  ok "S.8e-control all $DECL_N declared destinations are still recorded (the refusal is targeted, not blanket)"
else
  bad "S.8e-control only $KEPT of $DECL_N declared destinations survived — the whitelist is rejecting the table's own rows"
fi

# Fail-CLOSED: no table => no declared destinations => nothing is recorded,
# even for a path the REAL table declares.
GOT="$(
  (
    cd "$SOURCE_DIR" || exit 9
    # shellcheck source=/dev/null
    . "$GENERATOR"
    export FMS_PROFILE_PARTS="core"
    _WBM_ROUTES_TSV="$WORKROOT/does-not-exist.tsv"
    FMS_DELIVERED_TEMPLATES="docs/BRANCH-PROTECTION.md"
    _framework_target_entries 2>/dev/null
  ) | grep -c '^docs/BRANCH-PROTECTION\.md$'
)"
if [ "$GOT" -eq 0 ]; then
  ok "S.8f with no route table the whitelist is EMPTY, so nothing is recorded (fail-closed)"
else
  bad "S.8f a delivered template was recorded with no route table to declare it — the whitelist fails OPEN"
fi

# ---------------------------------------------------------------------------
# S.9 (rail round-4 F4) — an UNTERMINATED final row must not vanish.
#
# `while read` returns non-zero on a final line with no trailing newline even
# though it FILLED the variables, so a bare loop drops that row. All three
# readers had the same shape, which is what made the loss invisible:
# _wbm_route_dests dropped the row (numerator) and _wbm_route_rows_total
# dropped it too (denominator), so upgrade.sh's AC-9 precondition compared
# 5 against 5, passed, and the run shipped omitting the last delivery at
# exit 0. A disagreement is observable; two wrong numbers agreeing is not.
# ---------------------------------------------------------------------------
echo "==> S.9 — an unterminated final route row is read, not dropped (F4)"

NONL="$WORKROOT/routes-no-final-newline.tsv"
printf '%s' "$( cat "$ROUTES" )" > "$NONL"
# Anti-vacuity: the fixture must actually lack the newline, and must differ
# from the real table by exactly that one byte.
_nonl_last="$( tail -c 1 "$NONL" | od -An -c | tr -d ' \n' )"
_real_bytes="$( wc -c < "$ROUTES" | tr -d ' ' )"
_nonl_bytes="$( wc -c < "$NONL" | tr -d ' ' )"
if [ "$_nonl_last" != '\n' ] && [ "$(( _real_bytes - _nonl_bytes ))" -eq 1 ]; then
  ok "S.9-control the fixture is the real table minus exactly its trailing newline ($_real_bytes -> $_nonl_bytes bytes)"
else
  bad "S.9-control fixture is not 'the real table minus one trailing newline' (last char '$_nonl_last', $_real_bytes -> $_nonl_bytes) — every leg below would be vacuous"
fi

# The LAST data row, derived from the table (never hardcoded: a new row at the
# bottom must move this assertion, not silently keep testing the old one).
LAST_DEST=""
while IFS="$( printf '\t' )" read -r _l_dest _l_rest || [ -n "${_l_dest:-}" ]; do
  [ -n "${_l_dest:-}" ] || continue
  case "$_l_dest" in \#*|dest) continue ;; esac
  LAST_DEST="$_l_dest"
done < "$ROUTES"
[ -n "$LAST_DEST" ] && ok "S.9-control last data row derived from the table: $LAST_DEST" \
                    || bad "S.9-control could not derive the last data row from $ROUTES"

# Probe all three readers against a table, in one child shell.
_route_probe() {  # $1=generator $2=table -> "<dests>|<rows>|<rc of src(LAST_DEST)>"
  bash -c '
    set -uo pipefail
    # shellcheck source=/dev/null
    . "$1"
    # rail round-6 F3 — AFTER the source, deliberately: the library resolves
    # its SHIPPED table unconditionally at source time, so a pre-source
    # assignment is a no-op now (S.11f asserts exactly that). This is the
    # in-process seam upgrade.sh uses for its snapshot, not an env channel.
    _WBM_ROUTES_TSV="$2"
    d="$( _wbm_route_dests 2>/dev/null | grep -c . )"
    r="$( _wbm_route_rows_total 2>/dev/null )"
    rc=0; _wbm_route_src "$3" >/dev/null 2>&1 || rc=$?
    printf "%s|%s|%s\n" "$d" "$r" "$rc"
  ' _ "$1" "$2" "$LAST_DEST" 2>/dev/null
}

CURED="$( _route_probe "$GENERATOR" "$NONL" )"
_c_dests="${CURED%%|*}"; _c_rest="${CURED#*|}"; _c_rows="${_c_rest%%|*}"; _c_rc="${_c_rest#*|}"
REAL="$( _route_probe "$GENERATOR" "$ROUTES" )"
_r_dests="${REAL%%|*}"; _r_rest="${REAL#*|}"; _r_rows="${_r_rest%%|*}"
if [ "$_c_dests" = "$_r_dests" ] && [ "$_c_rows" = "$_r_rows" ]; then
  ok "S.9a the unterminated table enumerates exactly what the real one does ($_c_dests routes / $_c_rows rows)"
else
  bad "S.9a unterminated table gave $_c_dests routes / $_c_rows rows; the terminated one gives $_r_dests / $_r_rows — the final row is still being dropped"
fi
if [ "$_c_rc" = "0" ]; then
  ok "S.9b _wbm_route_src resolves the unterminated final row (rc=0), not the identity fallback"
else
  bad "S.9b _wbm_route_src answered rc=$_c_rc for '$LAST_DEST' on the unterminated table — rc=1 is 'no row', which the callers answer with the identity fallback (D3/D4)"
fi

# RED leg: neutralise ONLY the `|| [ -n "$first" ]` guards and watch the row
# come back off the table. python3 rather than sed so the edit is anchored and
# counted — an anchor that matches nothing must fail the control, not pass it.
NOGATE="$WORKROOT/generator-nogate.sh"
_ng_hits="$( python3 - "$GENERATOR" "$NOGATE" <<'PY'
import io, re, sys
src = io.open(sys.argv[1], encoding="utf-8").read()
pat = re.compile(r'[ \t]*\|\|[ \t]*\[[ \t]*-n[ \t]*"\$\{_wbm_r[a-z]+_dest:-\}"[ \t]*\][ \t]*;[ \t]*do')
out, n = pat.subn('; do', src)
io.open(sys.argv[2], "w", encoding="utf-8").write(out)
sys.stdout.write(str(n))
PY
)"
if [ "${_ng_hits:-0}" -ge 3 ]; then
  ok "S.9-control the RED plant removed the guard from $_ng_hits reader loop(s)"
else
  bad "S.9-control the RED plant matched $_ng_hits loop(s), expected >= 3 — the anchor rotted and the leg below proves nothing"
fi
RED9="$( _route_probe "$NOGATE" "$NONL" )"
_x_dests="${RED9%%|*}"; _x_rest="${RED9#*|}"; _x_rows="${_x_rest%%|*}"; _x_rc="${_x_rest#*|}"
if [ "$_x_dests" -lt "$_r_dests" ] && [ "$_x_dests" = "$_x_rows" ]; then
  ok "S.9c RED (guard removed): $_x_dests routes of $_x_rows rows — the undercount is INVISIBLE to routes==rows, which is why it shipped"
else
  bad "S.9c the RED plant did not reproduce the drop ($_x_dests routes / $_x_rows rows vs $_r_dests real) — the cure above may be passing for another reason"
fi
[ "$_x_rc" = "1" ] && ok "S.9d RED: _wbm_route_src fell back to rc=1 (identity) for the dropped row" \
                   || bad "S.9d RED: expected rc=1 for the dropped row, got rc=$_x_rc"

# A malformed unterminated row is still REJECTED — "processed" is not
# "trusted". Two shapes: a hostile dest (must drop out of dests while the row
# counter still counts it, so routes<rows makes it observable), and a
# TRUNCATED row missing the transform field (must resolve rc=2, never rc=0).
HOSTILE_NONL="$WORKROOT/routes-hostile-no-newline.tsv"
{ printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
  printf 'docs/ok.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tvalid\n'
  printf '../../PWNED.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\thostile+unterminated'; } > "$HOSTILE_NONL"
H9="$( bash -c '
  set -uo pipefail
  # shellcheck source=/dev/null
  . "$1"
  # rail round-6 F3 — AFTER the source (see _route_probe).
  _WBM_ROUTES_TSV="$2"
  d="$( _wbm_route_dests 2>/dev/null | grep -c . )"
  r="$( _wbm_route_rows_total 2>/dev/null )"
  rc=0; _wbm_route_src "../../PWNED.md" >/dev/null 2>&1 || rc=$?
  printf "%s|%s|%s\n" "$d" "$r" "$rc"' _ "$GENERATOR" "$HOSTILE_NONL" 2>/dev/null )"
[ "$H9" = "1|2|2" ] \
  && ok "S.9e an unterminated HOSTILE row is counted (rows=2) but not enumerated (routes=1) and resolves rc=2 — the precondition sees the gap" \
  || bad "S.9e unterminated hostile row gave '$H9', expected '1|2|2' — a rejected row must stay visible in the denominator"

TRUNC_NONL="$WORKROOT/routes-truncated-no-newline.tsv"
{ printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
  printf 'docs/ok.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tvalid\n'
  printf 'docs/trunc.md\ttemplates/docs/rotation-log.md'; } > "$TRUNC_NONL"
T9="$( bash -c '
  set -uo pipefail
  # shellcheck source=/dev/null
  . "$1"
  # rail round-6 F3 — AFTER the source (see _route_probe).
  _WBM_ROUTES_TSV="$2"
  rc=0; _wbm_route_src "docs/trunc.md" >/dev/null 2>&1 || rc=$?
  printf "%s\n" "$rc"' _ "$GENERATOR" "$TRUNC_NONL" 2>/dev/null )"
[ "$T9" = "2" ] \
  && ok "S.9f an unterminated TRUNCATED row (no transform field) resolves rc=2, fail-closed" \
  || bad "S.9f truncated unterminated row resolved rc=$T9, expected 2 — reading the row must not mean trusting it"

# ---------------------------------------------------------------------------
# S.10 (rail round-4 F3/F1) — two predicates the callers now depend on.
# ---------------------------------------------------------------------------
echo "==> S.10 — _wbm_route_table_ok and the exact-match prior-digest lookup"

_table_ok() {  # $1=table -> "<rc>|<reason>"
  bash -c '
    set -uo pipefail
    # shellcheck source=/dev/null
    . "$1"
    # rail round-6 F3 — AFTER the source, deliberately: the library resolves
    # its SHIPPED table unconditionally at source time, so a pre-source
    # assignment is a no-op now (S.11f asserts exactly that). This is the
    # in-process seam upgrade.sh uses for its snapshot, not an env channel.
    _WBM_ROUTES_TSV="$2"
    rc=0; _wbm_route_table_ok || rc=$?
    printf "%s|%s\n" "$rc" "${_WBM_ROUTE_TABLE_WHY:-}"' _ "$GENERATOR" "$1" 2>/dev/null
}

R="$( _table_ok "$ROUTES" )"
[ "${R%%|*}" = "0" ] && ok "S.10a the real table passes _wbm_route_table_ok" \
                     || bad "S.10a the REAL table was rejected ($R) — the gate would refuse every legitimate run"
R="$( _table_ok "$NONL" )"
[ "${R%%|*}" = "0" ] && ok "S.10b an unterminated (but complete) table still passes" \
                     || bad "S.10b unterminated table rejected ($R)"

printf 'a\tb\tc\n'                                  > "$WORKROOT/t-nohdr.tsv"
printf 'dest\tsrc\ttransform\n'                     > "$WORKROOT/t-hdronly.tsv"
printf 'dest\tSRCX\ttransform\nd\ts\tidentity\n'    > "$WORKROOT/t-badhdr.tsv"
: > "$WORKROOT/t-empty.tsv"
for _case in "t-missing.tsv:no such file" "t-nohdr.tsv:no header" "t-hdronly.tsv:header but no data rows" \
             "t-badhdr.tsv:wrong header fields" "t-empty.tsv:empty file"; do
  _f="${_case%%:*}"; _w="${_case#*:}"
  R="$( _table_ok "$WORKROOT/$_f" )"
  if [ "${R%%|*}" = "1" ] && [ -n "${R#*|}" ]; then
    ok "S.10c rejected + reason given ($_w)"
  else
    bad "S.10c '$_w' gave '$R' — expected rc=1 with a named reason; a gate that cannot say WHY is a gate nobody can act on"
  fi
done

# _wbm_prior_digest: the manifest relpaths carry `.` (`.github/CODEOWNERS`),
# and the retired `grep -E "^[0-9a-f]{64}  $1$"` treated them as a REGEX, so a
# record for `Xgithub/CODEOWNERS` answered a query for `.github/CODEOWNERS`.
D64="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
PRIORMAN="$WORKROOT/prior-manifest.sha256"
printf '%s  Xgithub/CODEOWNERS\n' "$D64" > "$PRIORMAN"
printf '%s  .github/CODEOWNERS.template\n' "${D64%f}1" >> "$PRIORMAN"
_pd() {  # $1=want
  bash -c '
    set -uo pipefail
    FMS_PRIOR_MANIFEST="$2"
    # shellcheck source=/dev/null
    . "$1"
    printf "%s\n" "$( _wbm_prior_digest "$3" )"' _ "$GENERATOR" "$PRIORMAN" "$1" 2>/dev/null
}
# RED: the retired implementation, recovered verbatim, on the same fixture.
RED_PD="$( grep -E "^[0-9a-f]{64}  .github/CODEOWNERS\$" "$PRIORMAN" 2>/dev/null | head -1 | cut -d' ' -f1 )"
[ -n "$RED_PD" ] \
  && ok "S.10-control the retired grep DOES answer for '.github/CODEOWNERS' off an 'Xgithub/CODEOWNERS' record (the leg below is not hypothetical)" \
  || bad "S.10-control the retired grep matched nothing — the fixture does not reproduce the regex hazard, so S.10d proves nothing"
[ -z "$( _pd ".github/CODEOWNERS" )" ] \
  && ok "S.10d _wbm_prior_digest returns NOTHING for '.github/CODEOWNERS' (exact match, not a regex)" \
  || bad "S.10d _wbm_prior_digest answered for '.github/CODEOWNERS' from an 'Xgithub/...' record — the '.' is still a wildcard"
[ "$( _pd ".github/CODEOWNERS.template" )" = "${D64%f}1" ] \
  && ok "S.10e _wbm_prior_digest still answers a genuine exact match (it is not a blanket empty)" \
  || bad "S.10e _wbm_prior_digest failed on a genuine record — the lookup now under-answers"
printf 'not-a-digest  docs/x.md\n' > "$WORKROOT/prior-bad.sha256"
[ -z "$( bash -c 'set -uo pipefail; FMS_PRIOR_MANIFEST="$2"; . "$1"; printf "%s\n" "$( _wbm_prior_digest "docs/x.md" )"' _ "$GENERATOR" "$WORKROOT/prior-bad.sha256" 2>/dev/null )" ] \
  && ok "S.10f a record whose first field is not a 64-hex digest is ignored" \
  || bad "S.10f a malformed digest field was returned as a digest"

# ---------------------------------------------------------------------------
# S.11 (rail round-5 F1) — a WELL-FORMED hostile table.
#
# Rounds 1-4 hardened what a row may SAY: no `..`, no absolute path, no glob,
# no unterminated undercount. Round 5 supplied a table that breaks NONE of
# those rules and still drives an arbitrary write:
#
#     .git/hooks/pre-commit  <-  scripts/install.sh  (identity)
#
# Every lexical gate agrees (relative, confined, no metacharacters),
# `routes == rows` holds so the AC-9 precondition is satisfied, the file is
# copied into the absent destination, recorded in the manifest, and the upgrade
# exits 0. `_wbm_route_dest_declared` is not a whitelist against this, because
# it reads the SAME table: a hostile table simply declares its own
# destinations.
#
# The cure is the one property no input can supply: a delivery DOMAIN fixed in
# CODE (`docs/` and `.github/` destinations, `templates/` sources) — plus a
# gate on the override itself, so a production run cannot be handed a table at
# all. Both are asserted here, each with the control that makes it non-vacuous.
# ---------------------------------------------------------------------------
echo "==> S.11 — the delivery domain is fixed in code, and the override is gated (F1)"

WELLFORMED="$WORKROOT/wellformed-hostile.tsv"
{
  printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
  printf '.git/hooks/pre-commit\tscripts/install.sh\tidentity\t-\tx\tconfined, relative, hostile\n'
} > "$WELLFORMED"

got11="$( _probe "$WELLFORMED" ".git/hooks/pre-commit" )"
case "$got11" in
  2\|*) ok "S.11a the reader refuses a CONFINED hostile destination fail-closed (rc=2)" ;;
  1\|*) bad "S.11a reader answered rc=1 for '.git/hooks/pre-commit' — callers read that as 'no route' and fall back to identity" ;;
  *)    bad "S.11a reader ACCEPTED '.git/hooks/pre-commit' (got '$got11') — a well-formed table can name any destination" ;;
esac

counts11="$( bash "$DESTS_HARNESS" "$WELLFORMED" 2>/dev/null )"
[ "$counts11" = "dests=0 rows=1" ] \
  && ok "S.11a-counts the hostile row is dropped but still counted ($counts11) — routes<rows, so AC-9 fails the whole delivery" \
  || bad "S.11a-counts expected 'dests=0 rows=1', got '$counts11' — an invisible drop cannot fail the precondition"

# --- S.11a-RED: the same table against a generator whose domain predicate is
# neutralised. Without this the leg above could be passing for some unrelated
# reason. The plant is ANCHORED (exactly one function body replaced) and lives
# in a COPY — the shipped generator is never touched.
NODOMAIN="$WORKROOT/generator-nodomain.sh"
python3 - "$GENERATOR" "$NODOMAIN" <<'PY'
import io, re, sys
src = io.open(sys.argv[1], encoding="utf-8").read()
pat = re.compile(r"^_wbm_route_domain_ok\(\) \{\n.*?^\}\n", re.S | re.M)
out, n = pat.subn("_wbm_route_domain_ok() {\n  return 0\n}\n", src)
if n != 1:
    sys.stderr.write("ANCHOR-MISS %d\n" % n)
    sys.exit(3)
io.open(sys.argv[2], "w", encoding="utf-8").write(out)
PY
if [ ! -s "$NODOMAIN" ]; then
  bad "S.11a-RED could not plant the neutralised domain predicate (anchor missed) — the control below would prove nothing"
else
  RED_FRAG="$WORKROOT/red_frag.sh"
  : > "$RED_FRAG"
  for _fn in _wbm_route_relpath_ok _wbm_route_domain_ok _wbm_route_row_ok \
             _wbm_route_table_ok _wbm_route_table_gate _wbm_route_meta _wbm_route_src; do
    sed -n "/^${_fn}() {\$/,/^}\$/p" "$NODOMAIN" >> "$RED_FRAG"
  done
  RED_HARNESS="$WORKROOT/red_harness.sh"
  {
    echo 'set -uo pipefail'
    echo '_WBM_ROUTES_TSV="$1"'
    cat "$RED_FRAG"
    echo '_probe() { local rc=0 out; out="$( _wbm_route_src "$2" )" || rc=$?; printf "%s|%s\n" "$rc" "${out:-}"; }'
    echo '_probe "$1" "$2"'
  } > "$RED_HARNESS"
  red11="$( bash "$RED_HARNESS" "$WELLFORMED" ".git/hooks/pre-commit" 2>/dev/null )"
  case "$red11" in
    0\|scripts/install.sh) ok "S.11a-RED with the domain predicate neutralised the SAME row is ACCEPTED (rc=0 -> scripts/install.sh) — the leg above is load-bearing" ;;
    *) bad "S.11a-RED the neutralised generator answered '$red11', expected '0|scripts/install.sh' — the positive control does not reproduce the finding" ;;
  esac
fi

# --- S.11b/c: the two halves of the domain, each on its own.
MIXED="$WORKROOT/mixed-domain.tsv"
{
  printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
  printf 'docs/ok.md\tscripts/install.sh\tidentity\t-\tx\tsource outside templates/\n'
  printf '.claude/settings.json\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tdestination outside the two trees\n'
  printf 'docs/rotation-log.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tlegitimate\n'
} > "$MIXED"
b11="$( _probe "$MIXED" "docs/ok.md" )"
case "$b11" in
  2\|*) ok "S.11b a source outside templates/ is refused (rc=2) even with a legitimate destination" ;;
  *)    bad "S.11b 'docs/ok.md <- scripts/install.sh' resolved '$b11' — any repo file could be delivered as framework content" ;;
esac
c11="$( _probe "$MIXED" ".claude/settings.json" )"
case "$c11" in
  2\|*) ok "S.11c a destination outside docs/ and .github/ is refused (rc=2)" ;;
  *)    bad "S.11c '.claude/settings.json' resolved '$c11' — the delivery domain is not enforced" ;;
esac
counts_mixed="$( bash "$DESTS_HARNESS" "$MIXED" 2>/dev/null )"
[ "$counts_mixed" = "dests=1 rows=3" ] \
  && ok "S.11c-counts only the legitimate row survives ($counts_mixed) — the refusal is per-row, and the gap is visible" \
  || bad "S.11c-counts expected 'dests=1 rows=3', got '$counts_mixed'"

# --- S.11-control: the six REAL routes are untouched by the domain rule.
counts_real11="$( bash "$DESTS_HARNESS" "$ROUTES" 2>/dev/null )"
[ "$counts_real11" = "dests=6 rows=6" ] \
  && ok "S.11-control the real table still yields 6 of 6 — the domain contains every shipped route" \
  || bad "S.11-control the real table yields '$counts_real11' — the domain rule is collateral damage on a legitimate route"

# --- S.11-write: the WRITE SITE refuses the same destination, and no bytes
# land. Driven through upgrade.sh's own _up_deliver_template, bypassing
# _wbm_route_dests on purpose: this leg must prove the write site refuses on
# its own, not that the reader filtered the row first.
W11_ROOT="$WORKROOT/writesite11"
W11_TARGET="$W11_ROOT/target"
mkdir -p "$W11_TARGET"
W11_HARNESS="$WORKROOT/writesite11.sh"
{
  echo 'set -uo pipefail'
  echo '_WBM_ROUTES_TSV="$1"'
  echo 'TARGET="$2"'
  echo 'SOURCE_DIR="$3"'
  echo 'DRY_RUN=0'
  echo 'BAK_DIR="$TARGET/.bak"'
  sed -n '/^_wbm_route_relpath_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_domain_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_row_ok() {$/,/^}$/p' "$GENERATOR"
  # rail round-6 F2 — the table gate the three readers call.
  sed -n '/^_wbm_route_table_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_table_gate() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_meta() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_route_src() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_up_tpl_symlink_refuses() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_tpl_confined_refuses() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_tpl_write() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_tpl_register() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_tpl_generations() {$/,/^}$/p' "$UPGRADER"
  sed -n '/^_up_deliver_template() {$/,/^}$/p' "$UPGRADER"
  echo '_hash_file() { shasum -a 256 "$1" 2>/dev/null | cut -d" " -f1; }'
  echo '_hash_stdin() { shasum -a 256 2>/dev/null | cut -d" " -f1; }'
  echo '_path_is_skipped() { return 1; }'
  echo '_baseline_lookup() { printf ""; }'
  echo '_UP_TPL_SKIPPED=0; _UP_TPL_PRESERVED=0; _UP_TPL_INSTALLED=0'
  echo '_UP_TPL_REFRESHED=0; _UP_TPL_IDENTICAL=0'
  echo '_D1_DELIVERED_TEMPLATES=""; _D1_CODEOWNERS_REGISTERED=0'
  echo 'for d in ".git/hooks/pre-commit" "docs/rotation-log.md"; do'
  echo '  _up_deliver_template "$d" "$SOURCE_DIR/templates/docs/rotation-log.md" "templates/docs/rotation-log.md" ""'
  echo 'done'
} > "$W11_HARNESS"
for fn in _wbm_route_domain_ok _up_tpl_confined_refuses _up_deliver_template; do
  grep -q "^${fn}() {" "$W11_HARNESS" \
    || bad "S.11-write could not extract $fn (renamed or removed?) — this leg would prove nothing"
done
bash "$W11_HARNESS" "$WELLFORMED" "$W11_TARGET" "$SOURCE_DIR" > "$WORKROOT/writesite11.log" 2>&1
if [ -e "$W11_TARGET/.git/hooks/pre-commit" ]; then
  bad "S.11-write _up_deliver_template WROTE the hostile destination: $W11_TARGET/.git/hooks/pre-commit exists"
else
  ok "S.11-write _up_deliver_template wrote NOTHING at the hostile destination"
fi
grep -q 'outside the delivery domain' "$WORKROOT/writesite11.log" 2>/dev/null \
  && ok "S.11-write the write-site refusal is NAMED on stderr" \
  || bad "S.11-write the hostile destination was dropped with no named refusal (see $WORKROOT/writesite11.log)"
[ -f "$W11_TARGET/docs/rotation-log.md" ] \
  && ok "S.11-write-control the in-domain destination WAS delivered in the same run (the refusal is targeted, not blanket)" \
  || bad "S.11-write-control docs/rotation-log.md was not delivered — the harness refused everything, so S.11-write is vacuous"

# ---------------------------------------------------------------------------
# S.11d-h (rail round-6 F3) — the ENVIRONMENT is not a channel into the table.
#
# Round 5 kept an override behind two conditions (an opt-in switch, and a
# candidate path physically under ${TMPDIR:-/tmp}). Both are settable by
# whoever can influence the environment of an upgrade — setting TMPDIR is the
# same gesture as setting the table — so the pair was a fixture loader inside a
# production entrypoint, not a trust boundary. Round 6 REMOVED the mechanism;
# these legs assert the removal from four directions, and the last two are what
# stop it from growing back.
#
# `_effective_table` prints the table the generator settled on, which is the
# only thing that matters here.
_effective_table() {  # $1=value planted in the ENVIRONMENT
  env _WBM_ROUTES_TSV="$1" CEO_ROUTES_TABLE_OVERRIDE_FOR_TESTS=1 \
    bash -c 'set -uo pipefail
             # shellcheck source=/dev/null
             . "$1"
             printf "%s\n" "${_WBM_ROUTES_TSV:-<unset>}"' _ "$GENERATOR" 2>/dev/null
}
# The retired switch is set TOO, on purpose: if any part of the old gate
# survived, this is the shape that would wake it up.
eff_env="$( _effective_table "$WELLFORMED" )"
[ "$eff_env" = "$ROUTES" ] \
  && ok "S.11d a table planted in the ENVIRONMENT is inert — the generator resolves the SHIPPED table" \
  || bad "S.11d the environment steered the generator to '$eff_env' (expected the shipped '$ROUTES') — the override is back"
# Same, with the fixture under $TMPDIR: that LOCATION was half of the retired
# gate, so it is the case most likely to still be honoured.
TMP_ENV_FIXTURE="$WORKROOT/env-planted-routes.tsv"
cp "$WELLFORMED" "$TMP_ENV_FIXTURE"
eff_env_tmp="$( _effective_table "$TMP_ENV_FIXTURE" )"
[ "$eff_env_tmp" = "$ROUTES" ] \
  && ok "S.11d-tmpdir a fixture under \$TMPDIR is inert too — location no longer buys an override" \
  || bad "S.11d-tmpdir a \$TMPDIR fixture resolved '$eff_env_tmp' — the retired location rule is still live"

# S.11e — the REPLACEMENT mechanism, proved POSITIVELY: a copied framework tree
# reads its OWN table. Asserted by BEHAVIOUR (a destination only the copy's
# table declares resolves rc=0 there and rc=1 against the shipped one), not by
# comparing paths — a path comparison would pass on a library that read the
# right file and ignored it.
COPY_TREE="$WORKROOT/srccopy"
COPY_TBL="$WORKROOT/copy-routes.tsv"
{
  printf 'dest\tsrc\ttransform\tflag_dep\torigin\tnote\n'
  printf 'docs/copytree-probe.md\ttemplates/docs/rotation-log.md\tidentity\t-\tx\tfixture-only route\n'
} > "$COPY_TBL"
if _mk_source_copy "$COPY_TREE" "$COPY_TBL"; then
  _copy_probe() {  # $1=generator path -> "<rc>|<src>"
    bash -c 'set -uo pipefail
             # shellcheck source=/dev/null
             . "$1"
             rc=0; out="$( _wbm_route_src "$2" )" || rc=$?
             printf "%s|%s\n" "$rc" "${out:-}"' _ "$1" "docs/copytree-probe.md" 2>/dev/null
  }
  got_copy="$( _copy_probe "$COPY_TREE/scripts/_framework_manifest_set.sh" )"
  [ "$got_copy" = "0|templates/docs/rotation-log.md" ] \
    && ok "S.11e the COPIED tree's library reads the COPY's table (fixture route resolves rc=0)" \
    || bad "S.11e the copied tree answered '$got_copy' for its own fixture route, want '0|templates/docs/rotation-log.md' — fixtures cannot be exercised this way"
  got_real="$( _copy_probe "$GENERATOR" )"
  [ "${got_real%%|*}" = "1" ] \
    && ok "S.11e-control the SHIPPED library does not know that route (rc=1) — S.11e measured the copy, not a route both tables carry" \
    || bad "S.11e-control the shipped library answered '$got_real' for a fixture-only route — S.11e is vacuous"
else
  bad "S.11e could not build the copied framework tree at $COPY_TREE — the replacement mechanism is untested"
fi

# S.11f — a PRE-source assignment is a no-op. This is the property every reader
# probe in this file relies on being FALSE for its own (post-source) assignment,
# and it is the exact shape a caller with environment control would use.
pre_src="$( bash -c 'set -uo pipefail
                     _WBM_ROUTES_TSV="$2"
                     # shellcheck source=/dev/null
                     . "$1"
                     printf "%s\n" "${_WBM_ROUTES_TSV:-<unset>}"' _ "$GENERATOR" "$WELLFORMED" 2>/dev/null )"
[ "$pre_src" = "$ROUTES" ] \
  && ok "S.11f an assignment BEFORE the source is clobbered — the library resolves its own table unconditionally" \
  || bad "S.11f a pre-source assignment survived as '$pre_src' — the source-time resolution is conditional again"

# S.11g — ANTI-ROT: the two retired names are GONE from production code. A raw
# grep, comments included: prose that names them is how the next author learns
# they are legal again.
# `grep -c` PRINTS 0 and EXITS 1 on no match, so `$( grep -c ... || echo 0 )`
# yields TWO lines and every arithmetic test downstream dies. Capture, then
# correct the variable — never append a second value to the substitution.
_ovr_hits=0
for _p in "$SOURCE_DIR"/scripts/*.sh; do
  _n="$( grep -c 'OVERRIDE_FOR_TESTS\|FMS_DELIVERY_ROUTES_TSV' "$_p" 2>/dev/null )" || _n=0
  case "$_n" in ''|*[!0-9]*) _n=0 ;; esac
  [ "$_n" -eq 0 ] || { _ovr_hits=$(( _ovr_hits + _n )); echo "        hit: $( basename "$_p" ) x$_n" >&2; }
done
[ "$_ovr_hits" -eq 0 ] \
  && ok "S.11g the retired override names appear NOWHERE in scripts/*.sh (0 hits)" \
  || bad "S.11g $_ovr_hits occurrence(s) of the retired override names in scripts/*.sh — the environment channel is being rebuilt"
# Non-vacuity: the pattern must fire on the construct that was removed.
printf 'if [ "${CEO_ROUTES_TABLE_OVERRIDE_FOR_TESTS:-0}" = "1" ]; then FMS_DELIVERY_ROUTES_TSV="$1"; fi\n' \
  > "$WORKROOT/ovr-control.sh"
_ovr_ctl="$( grep -c 'OVERRIDE_FOR_TESTS\|FMS_DELIVERY_ROUTES_TSV' "$WORKROOT/ovr-control.sh" 2>/dev/null )" || _ovr_ctl=0
[ "$_ovr_ctl" -eq 1 ] \
  && ok "S.11g-control the pattern DOES match the retired override construct (the zero above is not a dead regex)" \
  || bad "S.11g-control the pattern did not match a planted override line (got $_ovr_ctl) — S.11g is vacuous"

# S.11h — exactly ONE production assignment of the reader's table variable
# outside the library: upgrade.sh's round-2 snapshot. A second one is a second
# steering wheel, which is how the override was born.
_asg_total=0
for _p in "$SOURCE_DIR"/scripts/*.sh; do
  case "$( basename "$_p" )" in _framework_manifest_set.sh) continue ;; esac
  _n="$( grep -cE '^[[:space:]]*_WBM_ROUTES_TSV=' "$_p" 2>/dev/null )" || _n=0
  case "$_n" in ''|*[!0-9]*) _n=0 ;; esac
  _asg_total=$(( _asg_total + _n ))
  [ "$_n" -eq 0 ] || echo "        assignment: $( basename "$_p" ) x$_n" >&2
done
_asg_upgrade="$( grep -cE '^[[:space:]]*_WBM_ROUTES_TSV=' "$SOURCE_DIR/scripts/upgrade.sh" 2>/dev/null )" || _asg_upgrade=0
case "$_asg_upgrade" in ''|*[!0-9]*) _asg_upgrade=0 ;; esac
if [ "$_asg_total" -eq 1 ] && [ "$_asg_upgrade" -eq 1 ]; then
  ok "S.11h exactly one production re-point of the table variable, and it is upgrade.sh's --pin snapshot"
else
  bad "S.11h $_asg_total assignment(s) of _WBM_ROUTES_TSV outside the library (upgrade.sh: $_asg_upgrade) — expected exactly 1, in upgrade.sh"
fi

# ---------------------------------------------------------------------------
# S.12 (rail round-5 F4) — ANTI-ROT: no second parser of the route table.
#
# ADR-194 §1 vetoes a fourth route implementation by name, and round 5 found
# one hiding in upgrade.sh's rendered-CODEOWNERS branch: two `awk` calls
# straight over the environment-overridable TSV, inheriting none of the
# reader's validators. The metadata now comes from _wbm_route_meta. This
# assertion is what stops the next one from being written.
#
# Comment lines are stripped first: the question is about CODE, and the prose
# in these files legitimately DISCUSSES the awk that was removed.
# ---------------------------------------------------------------------------
echo "==> S.12 — the shared table has no second parser outside the canonical reader (F4)"

for _consumer in "$SOURCE_DIR/scripts/upgrade.sh" "$SOURCE_DIR/scripts/install.sh" "$SOURCE_DIR/scripts/doctor.sh"; do
  _cn="$( basename "$_consumer" )"
  if [ ! -f "$_consumer" ]; then
    bad "S.12 $_cn not found at $_consumer — the assertion cannot run"
    continue
  fi
  _hits="$( grep -v '^[[:space:]]*#' "$_consumer" | grep -cE 'awk.*(delivery-routes|ROUTES_TSV)' )"
  [ "$_hits" -eq 0 ] \
    && ok "S.12 $_cn parses the route table through the shared reader only (0 awk call-sites over it)" \
    || bad "S.12 $_cn has $_hits awk call-site(s) parsing the route table directly — ADR-194 §1 vetoes a second implementation"
done
# Non-vacuity: the pattern must actually FIRE on the retired construct.
printf '_X="$( awk -F "\\t" -v want="x" "\\$1 == want { print \\$2 }" "${_WBM_ROUTES_TSV:-/dev/null}" )"\n' > "$WORKROOT/rot-control.sh"
[ "$( grep -v '^[[:space:]]*#' "$WORKROOT/rot-control.sh" | grep -cE 'awk.*(delivery-routes|ROUTES_TSV)' )" -eq 1 ] \
  && ok "S.12-control the pattern DOES match the retired awk construct (the zeros above are not a dead regex)" \
  || bad "S.12-control the pattern did not match a planted awk-over-the-table line — S.12 is vacuous"

# ---------------------------------------------------------------------------
# S.13 (rail round-6 F2) — the HEADER is a precondition for EVERY reader.
#
# Round 4 F3 put _wbm_route_table_ok in front of doctor.sh alone. MEASURED
# pre-cure (S327), on the two readers it did not guard: with the header row
# deleted, or with its 2nd/3rd column names corrupted, _wbm_route_dests still
# enumerated all 6 destinations, _wbm_route_rows_total counted 6, `routes ==
# rows` held — so upgrade.sh's AC-9 precondition PASSED — and _wbm_route_src
# resolved a source rc=0. A header is the statement that column 2 means
# "source" and column 3 means "transform"; without it the rows are an
# unlabelled tuple the reader is guessing at, and the guess drives writes.
#
# RED is produced by neutralising the gate CALL-SITES in a COPY of the library
# (the R.3/S.11a idiom: sabotage a copy, never the real file), with the plant
# count asserted so the control cannot rot into a no-op.
# ---------------------------------------------------------------------------
echo "==> S.13 — a corrupted or missing header stops every reader (F2)"

S13_NOHDR="$WORKROOT/routes-no-header.tsv"
S13_BADHDR="$WORKROOT/routes-bad-header.tsv"
grep -v '^dest	' "$ROUTES" > "$S13_NOHDR"
sed 's/^dest	src	transform/dest	SOURCE	xform/' "$ROUTES" > "$S13_BADHDR"
# Anti-vacuity: each fixture must differ from the real table by exactly the
# header, and must still CARRY its data rows — a fixture that lost the rows
# would make every reader answer 0 for the wrong reason.
_s13_rows_real="$( grep -cE '^(docs|\.github)/' "$ROUTES" )"
_s13_rows_nohdr="$( grep -cE '^(docs|\.github)/' "$S13_NOHDR" )"
_s13_rows_badhdr="$( grep -cE '^(docs|\.github)/' "$S13_BADHDR" )"
if [ "$_s13_rows_nohdr" -eq "$_s13_rows_real" ] && [ "$_s13_rows_badhdr" -eq "$_s13_rows_real" ] \
   && [ "$_s13_rows_real" -gt 0 ] \
   && ! cmp -s "$ROUTES" "$S13_NOHDR" && ! cmp -s "$ROUTES" "$S13_BADHDR"; then
  ok "S.13-control both fixtures keep all $_s13_rows_real data rows and differ from the real table only in the header"
else
  bad "S.13-control fixtures are wrong (rows real=$_s13_rows_real nohdr=$_s13_rows_nohdr badhdr=$_s13_rows_badhdr) — every leg below would be vacuous"
fi

# RED: the same library with the three gate call-sites neutralised.
S13_RED="$WORKROOT/red-lib-nogate.sh"
awk '/^  _wbm_route_table_gate \|\|/ { print "  true  # RED-PLANT"; next } { print }' \
  "$GENERATOR" > "$S13_RED"
_s13_plants="$( grep -c 'RED-PLANT' "$S13_RED" 2>/dev/null )" || _s13_plants=0
_s13_sites="$( grep -cE '^  _wbm_route_table_gate \|\|' "$GENERATOR" 2>/dev/null )" || _s13_sites=0
if [ "$_s13_sites" -eq 3 ] && [ "$_s13_plants" -eq 3 ] && bash -n "$S13_RED" 2>/dev/null; then
  ok "S.13-control the library has 3 reader gate call-sites and the RED copy neutralises all 3 (and still parses)"
else
  bad "S.13-control gate call-sites=$_s13_sites planted=$_s13_plants — the RED plant rotted (a fourth reader added without the gate would also land here)"
fi

for _s13_fx in "$S13_NOHDR" "$S13_BADHDR"; do
  _s13_lbl="$( basename "$_s13_fx" )"
  red13="$( _route_probe "$S13_RED" "$_s13_fx" )"
  case "$red13" in
    "$_s13_rows_real|$_s13_rows_real|0")
      ok "S.13-RED ($_s13_lbl) without the gate the readers consume the rows: dests=rows=$_s13_rows_real and src rc=0 — routes==rows, so AC-9 would PASS" ;;
    *)
      bad "S.13-RED ($_s13_lbl) neutralised library answered '$red13', expected '$_s13_rows_real|$_s13_rows_real|0' — the finding does not reproduce, so the GREEN below is not evidence" ;;
  esac
  grn13="$( _route_probe "$GENERATOR" "$_s13_fx" )"
  case "$grn13" in
    "0|0|2")
      ok "S.13 ($_s13_lbl) the cured readers enumerate ZERO routes, count ZERO rows and answer rc=2 (fail-closed)" ;;
    *)
      bad "S.13 ($_s13_lbl) cured library answered '$grn13', expected '0|0|2' — an unusable table must never resolve to the identity fallback" ;;
  esac
done

# The refusal is NAMED, and named ONCE: the gate memoises per table path, so a
# doctor run asking several hundred times gets one line, not a wall.
S13_LOG="$WORKROOT/s13-refusal.log"
bash -c 'set -uo pipefail
         # shellcheck source=/dev/null
         . "$1"
         _WBM_ROUTES_TSV="$2"
         # No warm-up call may be stderr-suppressed here: the gate memoises,
         # so a suppressed FIRST call would eat the one line this leg counts
         # (measured — that is how this control was born vacuous).
         _wbm_route_dests
         _wbm_route_rows_total
         _wbm_route_src "docs/BRANCH-PROTECTION.md"
         _wbm_route_src "docs/rotation-log.md"
         true' _ "$GENERATOR" "$S13_BADHDR" > /dev/null 2>"$S13_LOG"
_s13_named="$( grep -c 'delivery-route table REFUSED' "$S13_LOG" 2>/dev/null )" || _s13_named=0
[ "$_s13_named" -eq 1 ] \
  && ok "S.13-named exactly ONE named refusal for four reader calls in one process (memoised per table path)" \
  || bad "S.13-named $_s13_named refusal line(s) for four reader calls — 0 is the D3 silence, >1 is a wall an operator stops reading"
grep -q "not 'src'/'transform'" "$S13_LOG" 2>/dev/null \
  && ok "S.13-named the line names WHICH column is wrong, not just 'bad table'" \
  || bad "S.13-named the refusal does not name the offending columns (see $S13_LOG)"

# Anti-over-rejection: the real table is untouched by any of this.
real13="$( _route_probe "$GENERATOR" "$ROUTES" )"
[ "$real13" = "$_s13_rows_real|$_s13_rows_real|0" ] \
  && ok "S.13-control the REAL table still yields $_s13_rows_real of $_s13_rows_real with rc=0 — the gate is not a blanket no" \
  || bad "S.13-control the real table answered '$real13' — the header gate is collateral damage on a healthy run"

# ---------------------------------------------------------------------------
# S.14 (rail round-7 F1) — the delivery DOMAIN is the set of INERT FORMS, not
# a subtree. Pre-cure the predicate accepted anything under `docs/` or
# `.github/`, so the shipped `validate.yml.template` route with four characters
# removed from its destination — `.github/workflows/validate.yml` — passed,
# kept routes == rows, and delivery would have written a LIVE workflow into the
# adopter while the upgrade exited 0.
#
# RED is produced by restoring the pre-cure predicate BODY in a COPY of the
# library (the S.11a/S.13 idiom: sabotage a copy, never the real file), with
# the plant asserted so the control cannot rot into a no-op.
# ---------------------------------------------------------------------------
echo "==> S.14 — .github/ delivery is restricted to INERT forms (F1)"

S14_TBL="$WORKROOT/routes-live-workflow.tsv"
sed 's#^\.github/workflows/validate\.yml\.template	templates/#.github/workflows/validate.yml	templates/#' \
  "$ROUTES" > "$S14_TBL"
_s14_rows_real="$( grep -cE '^(docs|\.github)/' "$ROUTES" )"
_s14_rows_fx="$( grep -cE '^(docs|\.github)/' "$S14_TBL" )"
_s14_live="$( grep -cE '^\.github/workflows/validate\.yml	' "$S14_TBL" )" || _s14_live=0
if [ "$_s14_rows_fx" -eq "$_s14_rows_real" ] && [ "$_s14_live" -eq 1 ] \
   && ! cmp -s "$ROUTES" "$S14_TBL"; then
  ok "S.14-control the fixture keeps all $_s14_rows_real rows and differs only by targeting the LIVE .github/workflows/validate.yml"
else
  bad "S.14-control fixture is wrong (rows real=$_s14_rows_real fixture=$_s14_rows_fx live-rows=$_s14_live) — every leg below would be vacuous"
fi

# RED: the library with the pre-cure domain body restored.
S14_RED="$WORKROOT/red-lib-broad-domain.sh"
awk '
  /^_wbm_route_domain_ok\(\) \{$/ { print; inside=1; depth=0; next }
  inside && /^  case "\$\{1:-\}" in$/ {
    print "  case \"${1:-}\" in    # RED-PLANT (pre-cure body)"
    print "    docs/?*|.github/?*) ;;"
    print "    *) return 1 ;;"
    print "  esac"
    skip=1; next
  }
  skip && /^  if \[ "\$#" -ge 2 \]; then$/ { skip=0; inside=0 }
  skip { next }
  { print }
' "$GENERATOR" > "$S14_RED"
_s14_plants="$( grep -c 'RED-PLANT (pre-cure body)' "$S14_RED" 2>/dev/null )" || _s14_plants=0
if [ "$_s14_plants" -eq 1 ] && bash -n "$S14_RED" 2>/dev/null \
   && grep -q '^_wbm_route_domain_ok() {' "$S14_RED"; then
  ok "S.14-control the RED copy carries exactly 1 pre-cure domain body and still parses"
else
  bad "S.14-control planted=$_s14_plants — the RED plant rotted (predicate renamed or reshaped?); the GREEN below would not be evidence"
fi

_s14_probe() {  # $1=generator $2=table $3=dest -> "<dests>|<rows>|<rc>"
  bash -c '
    set -uo pipefail
    # shellcheck source=/dev/null
    . "$1"
    _WBM_ROUTES_TSV="$2"
    d="$( _wbm_route_dests 2>/dev/null | grep -c . )"
    r="$( _wbm_route_rows_total 2>/dev/null )"
    rc=0; _wbm_route_src "$3" >/dev/null 2>&1 || rc=$?
    printf "%s|%s|%s\n" "$d" "$r" "$rc"
  ' _ "$1" "$2" "$3" 2>/dev/null
}

red14="$( _s14_probe "$S14_RED" "$S14_TBL" ".github/workflows/validate.yml" )"
case "$red14" in
  "$_s14_rows_real|$_s14_rows_real|0")
    ok "S.14-RED with the pre-cure domain the LIVE workflow row is ACCEPTED: dests=rows=$_s14_rows_real and src rc=0 — routes==rows, so AC-9 would PASS and delivery would write it" ;;
  *)
    bad "S.14-RED pre-cure library answered '$red14', expected '$_s14_rows_real|$_s14_rows_real|0' — the finding does not reproduce, so the GREEN below is not evidence" ;;
esac

_s14_survivors=$(( _s14_rows_real - 1 ))
grn14="$( _s14_probe "$GENERATOR" "$S14_TBL" ".github/workflows/validate.yml" )"
case "$grn14" in
  "$_s14_survivors|$_s14_rows_real|2")
    ok "S.14 the cured domain REJECTS .github/workflows/validate.yml: dests=$_s14_survivors of $_s14_rows_real rows (routes<rows => AC-9 refuses the whole delivery) and src rc=2" ;;
  *)
    bad "S.14 cured library answered '$grn14', expected '$_s14_survivors|$_s14_rows_real|2' — an ACTIVE workflow destination must never be in domain" ;;
esac

S14_LOG="$WORKROOT/s14-refusal.log"
bash -c 'set -uo pipefail
         # shellcheck source=/dev/null
         . "$1"
         _WBM_ROUTES_TSV="$2"
         _wbm_route_dests
         true' _ "$GENERATOR" "$S14_TBL" > /dev/null 2>"$S14_LOG"
grep -q 'outside delivery domain' "$S14_LOG" 2>/dev/null \
  && ok "S.14-named the rejection is a NAMED breadcrumb (outside delivery domain), not a silent drop" \
  || bad "S.14-named no named refusal in $S14_LOG — a rejection nobody can see is the D3 silence"

# The predicate itself, form by form. The ACCEPT list is the ENUMERATION the
# cure is built on; every REJECT is a form the pre-cure subtree rule allowed.
S14_PRED="$WORKROOT/s14-pred.sh"
{
  echo 'set -uo pipefail'
  sed -n '/^_wbm_route_domain_ok() {$/,/^}$/p' "$GENERATOR"
  echo 'if _wbm_route_domain_ok "$1" "templates/x"; then echo ACCEPT; else echo REJECT; fi'
} > "$S14_PRED"
_s14_form() { bash "$S14_PRED" "$1" 2>/dev/null; }

_s14_bad_forms=0
for _s14_d in .github/workflows/validate.yml .github/workflows/pwn.yml \
              .github/dependabot.yml .github/workflows/deep/x.template \
              .github/workflows/.template .github/CODEOWNERS.templatex \
              docs/deep/nested.md docs/evil.sh docs/.md docs/ .github/; do
  [ "$( _s14_form "$_s14_d" )" = "REJECT" ] || { _s14_bad_forms=$(( _s14_bad_forms + 1 )); echo "       still in domain: $_s14_d" >&2; }
done
[ "$_s14_bad_forms" -eq 0 ] \
  && ok "S.14-forms 11 non-inert destinations (live workflows, nested paths, non-.md, bare suffixes) are ALL out of domain" \
  || bad "S.14-forms $_s14_bad_forms destination form(s) are still in domain"

# Anti-over-rejection, derived from the SHIPPED table so it cannot drift out of
# sync with what this framework actually delivers.
_s14_missing=0
_s14_checked=0
while IFS="$( printf '\t' )" read -r _s14_dest _s14_rest; do
  case "$_s14_dest" in ''|'#'*|dest) continue ;; esac
  _s14_checked=$(( _s14_checked + 1 ))
  [ "$( _s14_form "$_s14_dest" )" = "ACCEPT" ] || { _s14_missing=$(( _s14_missing + 1 )); echo "       shipped route now REFUSED: $_s14_dest" >&2; }
done < "$ROUTES"
if [ "$_s14_checked" -eq "$_s14_rows_real" ] && [ "$_s14_missing" -eq 0 ]; then
  ok "S.14-control all $_s14_checked SHIPPED destinations are still in domain — the enumeration is not a blanket no"
else
  bad "S.14-control checked=$_s14_checked (want $_s14_rows_real), refused=$_s14_missing — the cure narrowed past the product"
fi

# ---------------------------------------------------------------------------
# S.15 (rail round-7 F2) — the SOURCE is PHYSICALLY confined. `[ -f ]`, `cp`,
# `cat`, `sed` and sha256 all FOLLOW symlinks, so a `templates/...` source that
# is a link (or has a symlinked ancestor) to a regular file outside the
# checkout delivered FOREIGN bytes as framework content. RED here is the
# MECHANISM measured directly (the pre-cure code had no predicate to
# neutralise: `-f` was the whole check), and GREEN is the predicate refusing
# the same fixture.
# ---------------------------------------------------------------------------
echo "==> S.15 — delivery sources are physically confined to the checkout (F2)"

# The framework's own hasher, so this leg cannot disagree with what the
# product would have computed on the same bytes.
_sha_probe() { ( . "$SOURCE_DIR/scripts/_hash_lib.sh"; _hash_file "$1" ); }

S15_ROOT="$WORKROOT/s15"
mkdir -p "$S15_ROOT/src/templates/docs" "$S15_ROOT/src/templates/.github" \
         "$S15_ROOT/outside/docs"
printf 'FRAMEWORK BYTES\n'      > "$S15_ROOT/src/templates/docs/rotation-log.md"
printf 'FOREIGN LEAF BYTES\n'   > "$S15_ROOT/outside/foreign.md"
printf 'FOREIGN ANCESTOR\n'     > "$S15_ROOT/outside/docs/BRANCH-PROTECTION.md"
ln -s "$S15_ROOT/outside/foreign.md" "$S15_ROOT/src/templates/docs/BRANCH-PROTECTION.md"
ln -s "$S15_ROOT/outside/docs" "$S15_ROOT/src/templates/.github/docs"

# RED — the pre-cure test, executed: `-f` follows the link and the bytes that
# arrive are the OUTSIDE file's, sha for sha.
if [ -f "$S15_ROOT/src/templates/docs/BRANCH-PROTECTION.md" ]; then
  cp "$S15_ROOT/src/templates/docs/BRANCH-PROTECTION.md" "$S15_ROOT/delivered.bin" 2>/dev/null
  _s15_got="$( _sha_probe "$S15_ROOT/delivered.bin" )"
  _s15_foreign="$( _sha_probe "$S15_ROOT/outside/foreign.md" )"
  if [ -n "$_s15_got" ] && [ "$_s15_got" = "$_s15_foreign" ]; then
    ok "S.15-RED pre-cure ([ -f ] + cp) delivers the OUTSIDE file byte for byte (sha ${_s15_got%"${_s15_got#??????????}"}…) — the escape reproduces"
  else
    bad "S.15-RED delivered sha '$_s15_got' != foreign '$_s15_foreign' — the mechanism does not reproduce, so the GREEN below is not evidence"
  fi
else
  bad "S.15-RED [ -f ] answered FALSE on the symlinked source — this platform does not reproduce the finding"
fi

S15_PRED="$WORKROOT/s15-pred.sh"
{
  echo 'set -uo pipefail'
  sed -n '/^_wbm_route_relpath_ok() {$/,/^}$/p' "$GENERATOR"
  sed -n '/^_wbm_source_confined() {$/,/^}$/p' "$GENERATOR"
  echo 'if _wbm_source_confined "$1" "$2"; then echo "OK|"; else echo "REFUSED|$_WBM_SRC_CONFINE_WHY"; fi'
} > "$S15_PRED"
if grep -q '^_wbm_source_confined() {' "$S15_PRED"; then
  ok "S.15-control _wbm_source_confined extracted from the library by name"
else
  bad "S.15-control could not extract _wbm_source_confined (renamed or removed?) — every leg below is vacuous"
fi
_s15_probe() { bash "$S15_PRED" "$1" "$2" 2>/dev/null; }

case "$( _s15_probe "$S15_ROOT/src" "templates/docs/BRANCH-PROTECTION.md" )" in
  REFUSED*symlink*) ok "S.15 a symlinked LEAF source is REFUSED, naming the component" ;;
  *) bad "S.15 symlinked leaf answered '$( _s15_probe "$S15_ROOT/src" "templates/docs/BRANCH-PROTECTION.md" )' — foreign bytes would still be delivered" ;;
esac
case "$( _s15_probe "$S15_ROOT/src" "templates/.github/docs/BRANCH-PROTECTION.md" )" in
  REFUSED*symlink*) ok "S.15 a symlinked ANCESTOR is REFUSED too (the per-path lexical checks cannot see it)" ;;
  *) bad "S.15 symlinked ancestor answered '$( _s15_probe "$S15_ROOT/src" "templates/.github/docs/BRANCH-PROTECTION.md" )'" ;;
esac
case "$( _s15_probe "$S15_ROOT/src" "../outside/foreign.md" )" in
  REFUSED*confined\ relative\ path*) ok "S.15 a lexical .. escape is still refused by the relpath predicate" ;;
  *) bad "S.15 '..' source answered '$( _s15_probe "$S15_ROOT/src" "../outside/foreign.md" )'" ;;
esac
[ "$( _s15_probe "$S15_ROOT/src" "templates/docs/rotation-log.md" )" = "OK|" ] \
  && ok "S.15-control a REAL source inside the checkout is accepted — the predicate is not a blanket no" \
  || bad "S.15-control a legitimate source was refused: $( _s15_probe "$S15_ROOT/src" "templates/docs/rotation-log.md" )"
# The --pin lane: an ABSENT source must keep its "SKIPPED (source missing)"
# verdict, so the predicate resolves the DEEPEST EXISTING ancestor rather than
# the parent. Renaming that skip into a confinement refusal would be a
# regression against rail round-2 F2.
[ "$( _s15_probe "$S15_ROOT/src" "templates/docs/absent.md" )" = "OK|" ] \
  && ok "S.15-control an ABSENT source is NOT a confinement refusal (the --pin lane keeps 'source missing')" \
  || bad "S.15-control an absent source was refused: $( _s15_probe "$S15_ROOT/src" "templates/docs/absent.md" ) — this renames the round-2 F2 verdict"
[ "$( _s15_probe "$S15_ROOT/src" "templates/absent-dir/absent.md" )" = "OK|" ] \
  && ok "S.15-control an absent DIRECTORY + file is not a refusal either" \
  || bad "S.15-control absent dir answered $( _s15_probe "$S15_ROOT/src" "templates/absent-dir/absent.md" )"

# Anti-over-rejection on the real product: every SHIPPED route source must pass
# against this checkout, or the cure narrowed past the framework.
_s15_bad=0
_s15_seen=0
while IFS="$( printf '\t' )" read -r _s15_dest _s15_src _s15_rest; do
  case "$_s15_dest" in ''|'#'*|dest) continue ;; esac
  _s15_seen=$(( _s15_seen + 1 ))
  [ "$( _s15_probe "$SOURCE_DIR" "$_s15_src" )" = "OK|" ] \
    || { _s15_bad=$(( _s15_bad + 1 )); echo "       shipped source REFUSED: $_s15_src" >&2; }
done < "$ROUTES"
if [ "$_s15_seen" -gt 0 ] && [ "$_s15_bad" -eq 0 ]; then
  ok "S.15-control all $_s15_seen SHIPPED route sources pass confinement against this checkout"
else
  bad "S.15-control seen=$_s15_seen refused=$_s15_bad — the cure refuses the framework's own sources"
fi

# ---------------------------------------------------------------------------
# S.16 (rail round-7 F2) — install.sh honours the SAME confinement, in a REAL
# run. The predicate legs above are the unit; this is the wiring. install.sh
# reads the very same `templates/...` sources (five call-sites, measured), so a
# cure that lived only in upgrade.sh would leave the FIRST delivery — the one
# that creates the adopter's files — free to install foreign bytes.
# One real install (~26 s measured), from a COPIED checkout whose template for
# one route is a symlink out of the tree.
# ---------------------------------------------------------------------------
echo "==> S.16 — a real install.sh refuses an unconfined template source (F2)"

S16_SRC="$WORKROOT/s16-src"
S16_OUT="$WORKROOT/s16-outside"
mkdir -p "$S16_OUT"
printf 'FOREIGN BYTES — outside the framework checkout.\n' > "$S16_OUT/foreign.md"
S16_FOREIGN_SHA="$( _sha_probe "$S16_OUT/foreign.md" )"
if _mk_source_copy "$S16_SRC" "$ROUTES" \
   && rm -f "$S16_SRC/templates/docs/BRANCH-PROTECTION.md" \
   && ln -s "$S16_OUT/foreign.md" "$S16_SRC/templates/docs/BRANCH-PROTECTION.md" \
   && [ -L "$S16_SRC/templates/docs/BRANCH-PROTECTION.md" ]; then
  ok "S.16-control the copied checkout carries a symlinked template source"
  S16_TGT="$WORKROOT/s16-target"
  mkdir -p "$S16_TGT"
  ( cd "$S16_TGT" && git init -q ) 2>/dev/null
  S16_LOG="$WORKROOT/s16-install.log"
  CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    bash "$S16_SRC/scripts/install.sh" "$S16_TGT" --profile core --ceremony maintainer \
      > "$S16_LOG" 2>&1
  _s16_rc=$?
  if [ ! -e "$S16_TGT/docs/BRANCH-PROTECTION.md" ]; then
    ok "S.16a the install delivered NOTHING at the unconfined route (rc=$_s16_rc)"
  elif [ "$( _sha_probe "$S16_TGT/docs/BRANCH-PROTECTION.md" )" = "$S16_FOREIGN_SHA" ]; then
    bad "S.16a the install delivered the OUTSIDE file's bytes — install.sh did not inherit the confinement"
  else
    bad "S.16a something was delivered at the unconfined route that is neither absent nor the foreign bytes"
  fi
  grep -q 'source not confined to the framework checkout' "$S16_LOG" \
    && ok "S.16b the refusal is NAMED in the install log" \
    || bad "S.16b no named confinement refusal in $S16_LOG — a silent SKIP is indistinguishable from a missing template"
  # Scope: the OTHER routes of the SAME install are unaffected — this is a
  # per-source refusal, not an installer-wide abort.
  [ -f "$S16_TGT/docs/rotation-log.md" ] \
    && ok "S.16c the sibling route docs/rotation-log.md was still delivered — the refusal is per-source" \
    || bad "S.16c the sibling route was not delivered — one bad source aborted the healthy ones (see $S16_LOG)"
  [ -f "$S16_TGT/.github/workflows/validate.yml.template" ] \
    && ok "S.16d the .github/ routes were still delivered" \
    || bad "S.16d the .github/ routes were not delivered (see $S16_LOG)"
  # And the refused destination is NOT claimed in the baseline manifest: an
  # absent file recorded as framework-owned is what uninstall deletes on.
  if [ -f "$S16_TGT/.claude/.install-manifest.sha256" ]; then
    _s16_claim="$( grep -c '  docs/BRANCH-PROTECTION\.md$' "$S16_TGT/.claude/.install-manifest.sha256" )" || _s16_claim=0
    [ "$_s16_claim" -eq 0 ] \
      && ok "S.16e the refused destination is NOT recorded in the baseline manifest" \
      || bad "S.16e the manifest claims $_s16_claim record(s) for a destination the install refused to write"
  else
    bad "S.16e the install wrote no baseline manifest — S.16e cannot measure the claim"
  fi
else
  bad "S.16 could not build the symlinked-template checkout — the install wiring is untested"
fi

echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
