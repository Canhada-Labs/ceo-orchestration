#!/usr/bin/env bash
# verify-counts.sh — PLAN-087 W-F.3 + PLAN-112-FOLLOWUP-claude-md-count-drift —
# README/INSTALL/CLAUDE.md numeric-claim drift detector (bidirectional).
#
# Derives the canonical counts at runtime and compares them to the values
# cited in the framework's top-level docs (CLAUDE.md, README.md, INSTALL.md).
# Reports drift as one violation per line; exits 0 on full parity, 1 on any
# drift.
#
# Usage:
#   bash .claude/scripts/local/verify-counts.sh              # human report + exit code
#   bash .claude/scripts/local/verify-counts.sh --quiet      # exit code only
#   bash .claude/scripts/local/verify-counts.sh --json       # machine-readable JSON
#   bash .claude/scripts/local/verify-counts.sh --no-tests   # skip the slow pytest collect
#
# =====================  COUNT CONTRACT (W1, S160/S161)  =====================
# Each metric below is derived from a single live source of truth and then
# checked against EVERY occurrence in the watched docs (all-matches, NOT
# head -1). Three rule kinds:
#   - exact  : the doc number MUST equal the live count.
#   - floor  : the doc states "N+"; the live count MUST be >= N (so adding a
#              test never churns the docs — AC6).
#   - approx : the doc states a ROUNDED figure ("~14,000 collected cases",
#              "~730 test files"). See the APPROX CONTRACT block below.
# The check is BIDIRECTIONAL (a doc number that disagrees with live fails)
# and CROSS-FILE (each doc is checked against the live value, so all docs are
# mutually consistent by transitivity — AC3/AC4).
#
#   metric            live source                                   rule
#   ----------------  --------------------------------------------  -----
#   skills (total)    find .claude/skills -name SKILL.md            exact (166)
#   core skills       find .claude/skills/core -name SKILL.md       exact (42)
#   frontend skills   find .claude/skills/frontend -name SKILL.md   exact (8)
#   domain skills     find .claude/skills/domains -name SKILL.md    exact (116)
#   ADRs              ls .claude/adr/ADR-*.md                        exact (188)
#   hook .py files    ls .claude/hooks/*.py                          exact (57)
#   registered hooks  distinct *.py in settings.json hooks{} tree   exact (46)
#   registrations     total hook entries in settings.json hooks{}   exact (48)
#   _lib modules      ls .claude/hooks/_lib/*.py  (TOP-LEVEL glob)   exact (68)
#   SPEC v1 files     ls SPEC/v1/*.md                                exact (32)
#   tests             pytest --collect-only -q  (DOCUMENTED scope)  floor (N+) + approx (~N)
#   test_files        git ls-files '*test_*.py' '*_test.py'         approx (~N)
#   release_steps     grep -c '      - name:' release.yml           exact (29)
#   commands          find .claude/commands -name '*.md'             exact (27)
#   workflows         find .github/workflows -name '*.yml'           exact (21)
#   mutation_fixtures find tests/formal_verification/mutation_...    exact (85)
#   tla_specs         ls docs/formal-verification/*.tla              exact (4)
#
# =====================  APPROX CONTRACT (PLAN-166 W0 F5)  ===================
# WHY a third kind. Two doc claims are deliberately ROUNDED because the exact
# figure churns on every commit: the collected-case count and the test-file
# count. `exact` would make every new test rewrite six documents; `floor`
# only catches OVERSELL ("docs say 12k, live is 11k") and is blind to
# UNDERSELL — and undersell is precisely the drift observed in the rc.1
# re-pass (npm/README.md, docs/FAQ.md and README.pt-BR.md all sat at
# "~12,000" while the live collect had grown past 14,000; the `floor` rule
# happily reported "no drift" the whole time because 14172 >= 12000).
#
# THE RULE, stated in full:
#   1. BAND. The cited figure, normalized to an integer ("~14,000" / "~14.000"
#      / "~14k" all -> 14000), must sit within +/- 5% of the live value.
#      5% of the collected-case count is ~700 cases, which is why (2) exists.
#   2. CROSS-DOC EQUALITY. Every watched doc must cite the SAME normalized
#      figure for a given approx metric. A pure band check is not enough:
#      "~720 test files" (docs/ARCHITECTURE.md) and "~730 test files"
#      (CLAUDE.md) were BOTH inside a 5% band of the live 736 while
#      contradicting each other in public — a live divergence between two
#      watched docs that the gate could not see. Equality makes the release
#      restate one number, not a range.
#   3. INPUTS ARE PRINTED. A band without its inputs is a licence to drift:
#      +/-700 cases can hide an entire test family. The gate prints, for every
#      approx metric, the exact command used, the observed value, and — for
#      the collect-driven metric — the COLLECTION-ERROR COUNT. errors > 0 is
#      a VIOLATION whenever the band was actually enforced over >=1 doc site
#      this run: the observed count is then measured over a PARTIAL population
#      and a band verdict over the wrong number is untrustworthy — and the
#      automated callers (validate.yml --quiet; the release preflight, which
#      discards output) can only see the exit code, so a warning there is
#      structurally invisible (PLAN-166 W0 re-pass). It stays a named WARNING
#      only when the band is already suspended (--no-tests / observed 0).
#
# COLLECTION SCOPE (load-bearing — the two populations DIVERGE). This block
# is the ONLY measurement snapshot in this file (W0 re-pass round 2: two
# divergent pairs coexisted, one undated — the numeral-espelho class; a
# reader could not tell which measurement backed the scope decision).
# Measured 2026-08-06 on the PLAN-166 W0 tree AFTER the residual-fix round
# (the previous snapshot went stale within its own patch — the residual
# fixers added tests after it was pasted; codex W0-residuals round caught
# it). Both figures are OUTPUTS of the two commands, pasted, not recalled:
#   `python3 -m pytest --collect-only -q`            -> 14263 tests,  0 errors
#   `python3 -m pytest --collect-only -q .claude/`   -> 14310 tests, 22 errors
#   The first is the DOCUMENTED scope: pytest.ini `testpaths` is the single
#   source of truth for collection and `make test-collect` runs exactly that
#   invocation — which is also the command every watched doc tells the reader
#   to run. The second (the pre-PLAN-166 derivation) walks `.claude/`
#   directly, which drags in `.claude/sidecars/**` (hypothesis/lightrag
#   probes that need third-party imports) and therefore reports 22 collection
#   ERRORS plus 47 extra cases the reader can never reproduce. Deriving from
#   the wrong population makes the gate reject a truthful doc or accept a
#   stale one, so the derivation is pinned to the documented scope.
#
# NON-INVENTORY NUMERALS (registered omission, not silence): this gate governs
# FRAMEWORK-INVENTORY COUNTS — things you can count in the tree. Latencies
# ("~0.3-1.0s"), prices ("$30-50"), coverage thresholds ("Tier-1 >= 86%"),
# per-profile skill caps and reading times are NOT inventory counts and are
# deliberately outside the contract; they are governed by the artifacts that
# set them (coverage.yml, the profile config), not by a doc-count gate.
# Guard against that exemption becoming a hiding place: the UNMATCHED-APPROX
# SWEEP below fails the gate (a VIOLATION, not a warning) on any
# thousands-shaped approximation ("~N,NNN", "~N.NNN", "~Nk") in a watched doc
# that NO approx rule consumed, naming the doc and the numeral. It MUST be a
# violation: the automated callers (validate.yml runs --quiet, the release
# preflight discards all output) can only observe the exit code, so an
# advisory sweep is a census nobody reads — a new doc numeral with no matcher
# would ship silently, which is exactly the F5 drift class this gate exists
# to stop (PLAN-166 W0 re-pass).
#
# PENDING SITES (registered exemption, never silence). `APPROX_PENDING` below
# can downgrade ONE (doc, metric, EXACT-frozen-value) triple from violation to
# a printed PENDING line. The mechanism exists for mid-session freezes of
# Gate-1 cache-stable files (CLAUDE.md §0), where a re-statement must land at
# a closeout rather than mid-flight; a pending site is also excluded from the
# cross-doc equality pool so the frozen value cannot drag other docs down.
# The registry is EMPTY today: its one historical entry (CLAUDE.md
# tests=13000, frozen during the PLAN-166 W0 session) was CONSUMED when
# commit 65daff0 restated CLAUDE.md to "~14,000 parametrized cases" — and
# keeping the entry past the restatement would have permanently grandfathered
# the exact stale value (a revert to "~13,000" exited 0, because the pending
# lookup runs BEFORE the band check; found by the W0 adversarial re-pass).
# Rules for any future entry:
#   - key on doc + metric + the EXACT frozen value; any OTHER out-of-band
#     figure at the site stays a hard violation;
#   - DELETE the entry in the same commit that lands the restatement — the
#     exemption is not self-clearing against reverts of that restatement;
#   - it prints on every single run, so it cannot rot unnoticed.
#
# NOTE on the two glob-ambiguous / underivable numbers (code-reviewer P2):
#   - "_lib modules" is pinned to the TOP-LEVEL `_lib/*.py` glob (68). The
#     recursive `_lib/**/*.py` count (incl. adapters/ + subdirs) is larger
#     (~140); docs must state the top-level number to match this gate.
#   - "registered hooks" (46) = distinct `*.py` script basenames appearing in
#     command strings of the settings.json hooks{} SUBTREE, parsed as JSON
#     (matches the hook_live_smoke check). S287: the old whole-file grep with
#     a hyphenless regex captured the statusLine `statusline-ceo.py` as a
#     phantom `ceo.py` (47). This is distinct from "hook .py files on disk"
#     (57) — some on-disk hooks are not wired into settings.json — and from
#     "registrations" (48): total hook ENTRIES incl. non-.py commands (one
#     script can fire on several events).
#
# RULE-LIVENESS CONTRACT (S287 vacuous-gate lesson): a metric whose regexes
# match ZERO watched docs reports "no drift" with a number nobody checks —
# a dead gate. The per-metric match count is exported as `rule_matches` in
# --json, and the real-repo test suite asserts every doc-gated metric
# matches >=1 site (test_verify_counts.py). Synthetic test trees are exempt
# by construction (the assertion lives in the real-repo test, not here).
# The historical "6 core hooks" enumeration in CLAUDE.md is a labelled
# historical subset, NOT a live total — it is not gated here.
# ============================================================================
#
# Bash 3.2 portable (macOS default). Doc-parsing delegated to a stdlib-only
# python3 block (python3 is already required for the test-collect step).

set -euo pipefail

REPO_ROOT="${VERIFY_COUNTS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"

QUIET=0
JSON=0
NO_TESTS=0
for arg in "$@"; do
  case "$arg" in
    --quiet)    QUIET=1 ;;
    --json)     JSON=1 ;;
    --no-tests) NO_TESTS=1 ;;
    -h|--help)
      # Usage + the full COUNT/APPROX contract. Keep this range in sync with
      # the header: it ends at the line before "NOTE on the two
      # glob-ambiguous" (S294 — the old '2,75p' truncated mid-sentence once
      # the APPROX CONTRACT block landed).
      sed -n "2,$(( $(grep -n '^# NOTE on the two glob-ambiguous' "$0" | head -1 | cut -d: -f1) - 1 ))p" "$0"
      exit 0
      ;;
    *)
      echo "verify-counts.sh: unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

# -------------------------- derive canonical counts -------------------------

DERIVED_SKILLS=$(find "$REPO_ROOT/.claude/skills" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
DERIVED_CORE=$(find "$REPO_ROOT/.claude/skills/core" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
DERIVED_FRONTEND=$(find "$REPO_ROOT/.claude/skills/frontend" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
DERIVED_DOMAIN=$(find "$REPO_ROOT/.claude/skills/domains" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
DERIVED_ADRS=$(ls "$REPO_ROOT"/.claude/adr/ADR-*.md 2>/dev/null | wc -l | tr -d ' ')
DERIVED_HOOK_PY=$(ls "$REPO_ROOT"/.claude/hooks/*.py 2>/dev/null | wc -l | tr -d ' ')
# "_lib modules" = importable application modules, which EXCLUDES the
# package marker __init__.py (the docs cite "68 modules, excluding the
# package __init__.py"; the raw glob is 69 incl. __init__.py). Aligns the
# live count to the documented contract (header note: exact 68).
DERIVED_LIB=$( { find "$REPO_ROOT/.claude/hooks/_lib" -maxdepth 1 -name '*.py' ! -name '__init__.py' 2>/dev/null || true; } | wc -l | tr -d ' ')
# Recursive _lib count (E9-F10 i): find descends adapters/ + subdirs. Guard the
# pipeline against set -e/pipefail when the tree has zero matches.
DERIVED_LIB_RECURSIVE=$(
  { find "$REPO_ROOT/.claude/hooks/_lib" -name '*.py' 2>/dev/null || true; } \
    | wc -l | tr -d ' '
)
# Live SPEC VERSION (E9-F10 iii): single source of truth = the VERSION file.
# Trim whitespace/newlines so the string compares cleanly against doc literals.
DERIVED_VERSION=$(tr -d ' \t\n\r' < "$REPO_ROOT/VERSION" 2>/dev/null || true)
DERIVED_SPEC_V1=$(ls "$REPO_ROOT"/SPEC/v1/*.md 2>/dev/null | wc -l | tr -d ' ')
# "schema files" = the *.schema.md subset (excludes README/compat/cli/shim docs).
# Use find (not ls glob) so a zero-match tree does not trip set -e/pipefail.
DERIVED_SCHEMA_FILES=$(find "$REPO_ROOT/SPEC/v1" -maxdepth 1 -name '*.schema.md' 2>/dev/null | wc -l | tr -d ' ')
# Registered hooks (46) + registrations (48) — parsed from the settings.json
# hooks{} SUBTREE as JSON, never a whole-file grep (S287: the old grep +
# hyphenless regex counted the statusLine `statusline-ceo.py` as a phantom
# `ceo.py`). registered = distinct *.py basenames across hook command
# strings (hyphens admitted); registrations = total hook entries (incl.
# non-.py commands). Unparseable settings.json derives 0/0 (a synthetic
# tree citing non-zero then fails loud — fail-closed on input).
_reg_out=$(python3 - "$REPO_ROOT/.claude/settings.json" <<'PYREG' 2>/dev/null
import json, os, re, sys
try:
    s = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print("0 0"); raise SystemExit(0)
hooks = s.get("hooks", {})
distinct, total = set(), 0
if isinstance(hooks, dict):
    for _event, matchers in hooks.items():
        if not isinstance(matchers, list):
            continue
        for m in matchers:
            if not isinstance(m, dict):
                continue
            for h in m.get("hooks", []):
                if not isinstance(h, dict):
                    continue
                total += 1
                for tok in re.findall(r"[A-Za-z0-9_.-]+\.py", str(h.get("command", ""))):
                    distinct.add(os.path.basename(tok))
print("%d %d" % (len(distinct), total))
PYREG
) || _reg_out="0 0"
DERIVED_REGISTERED=${_reg_out% *}
DERIVED_REGISTRATIONS=${_reg_out#* }

# Test count: collect-only over the DOCUMENTED scope — no path argument, so
# pytest.ini `testpaths` decides, which is byte-for-byte what `make
# test-collect` runs and what every watched doc tells the reader to run.
# The previous derivation passed `.claude/` explicitly; that walks
# `.claude/sidecars/**` too and reports COLLECTION ERRORS plus phantom
# cases the reader can never reproduce — a different population from the
# one the docs cite. The single dated measurement of BOTH populations
# lives in the COLLECTION SCOPE header block above; do not paste a second
# pair here (W0 re-pass round 2: an undated pair in this comment drifted
# from the dated header pair — one file, one snapshot).
#
# Both the collected count AND the collection-error count are derived: the
# error count is an INPUT of the approx rule (a band applied to a partially
# collected population is meaningless), so it is printed and exported, and
# errors > 0 is a VIOLATION whenever the band was actually enforced over
# >=1 doc site this run — it stays a named WARNING only when the band is
# already suspended (--no-tests / observed 0). That is APPROX CONTRACT
# clause 3 in the header, verbatim; the enforcement is the collect-errors
# branch in the python block below. (W0 re-pass round 2: this comment used
# to say "WARNING when non-zero" — the superseded pre-round-1 contract —
# while header and code both said VIOLATION.)
DERIVED_TESTS=0
DERIVED_TESTS_ERRORS=0
DERIVED_TESTS_CMD='python3 -m pytest --collect-only -q   # pytest.ini testpaths == `make test-collect`'
if [ "$NO_TESTS" -eq 0 ]; then
  _collect_out=$( { cd "$REPO_ROOT" && python3 -m pytest --collect-only -q 2>&1 | tail -5; } || true )
  DERIVED_TESTS=$(
    printf '%s\n' "$_collect_out" | \
    awk '/[0-9]+ tests? collected/ {
      for (i = 1; i <= NF; i++) {
        gsub(/\x1b\[[0-9;]*m/, "", $i)
        if ($i ~ /^[0-9]+$/) { print $i; exit }
      }
    }' || true
  )
  DERIVED_TESTS=${DERIVED_TESTS:-0}
  # "N errors" appears in the same -q summary line ("14219 tests collected,
  # 22 errors in 3.98s"). No match => 0 (a clean collect prints no "errors").
  DERIVED_TESTS_ERRORS=$(
    printf '%s\n' "$_collect_out" | \
    sed -e 's/\x1b\[[0-9;]*m//g' | \
    awk 'match($0, /[0-9]+ error/) {
      s = substr($0, RSTART, RLENGTH); sub(/ error/, "", s); print s; exit
    }' || true
  )
  DERIVED_TESTS_ERRORS=${DERIVED_TESTS_ERRORS:-0}
fi

# Test-FILE count (PLAN-166 W0 F5). Live source is the derivation the docs
# already print in their own "how to verify" cell, verbatim. `git ls-files`
# needs a git work tree; a synthetic fixture tree is not one, so a failure
# derives 0 and the metric simply matches no doc there (fail-quiet on
# INFRASTRUCTURE, per CLAUDE.md §4 — an absent git repo is not doc drift).
DERIVED_TEST_FILES_CMD="git ls-files '*test_*.py' '*_test.py' | wc -l"
DERIVED_TEST_FILES=$(
  { cd "$REPO_ROOT" && git ls-files '*test_*.py' '*_test.py' 2>/dev/null || true; } \
    | wc -l | tr -d ' '
)
DERIVED_TEST_FILES=${DERIVED_TEST_FILES:-0}

# Release steps = count of "      - name:" lines in release.yml (proper 6-space indent
# distinguishes job-level steps from nested lines). Use grep -c for portability.
DERIVED_RELEASE_STEPS=$(
  grep -c '      - name:' "$REPO_ROOT/.github/workflows/release.yml" 2>/dev/null || echo 0
)

# Slash-command count = number of *.md files under .claude/commands/
# The || echo 0 guards against find returning non-zero when dir is absent
# (can happen in synthetic test trees that don't create all directories).
DERIVED_COMMANDS=$(
  { find "$REPO_ROOT/.claude/commands" -maxdepth 1 -name '*.md' 2>/dev/null || true; } \
    | wc -l | tr -d ' '
)

# Workflow count = number of *.yml files under .github/workflows/
DERIVED_WORKFLOWS=$(
  { find "$REPO_ROOT/.github/workflows" -maxdepth 1 -name '*.yml' 2>/dev/null || true; } \
    | wc -l | tr -d ' '
)

# PLAN-166 W0 F5 — two counts docs/CTO-GUIDE.md cited with NO live metric
# behind them ("45 fixtures", "1 component fully specified"). Both were wrong
# (85 / 4) and invisible because the doc was outside DOCS. Given the choice
# the plan offers — live metric + matcher, or delete the claim — these two are
# cheap to derive and load-bearing for an evaluator, so they get metrics.
# Mutation fixtures = every fixture module under the conformance fixture tree,
# excluding package markers.
DERIVED_MUTATION_FIXTURES=$(
  { find "$REPO_ROOT/tests/formal_verification/mutation_fixtures" -name '*.py' \
      ! -name '__init__.py' 2>/dev/null || true; } \
    | wc -l | tr -d ' '
)
# Published TLA+ specifications (files, not model-checked components — CI does
# not model-check any of them; see CLAUDE.md §5).
DERIVED_TLA_SPECS=$(
  { find "$REPO_ROOT/docs/formal-verification" -maxdepth 1 -name '*.tla' 2>/dev/null || true; } \
    | wc -l | tr -d ' '
)

# ADR existence-by-status gate (E9-F10 ii). bash-3.2 portable: no assoc arrays;
# the inventory is space-separated lists + glob-with-[-e]-guard (the canonical
# nullglob-free idiom). Each violation is appended as one newline-terminated
# line and handed to the python3 block via VC_ADR_VIOLATIONS for merge.
ADR_PRESENT_ACCEPTED="127 128 131"   # MUST exist on disk with status: ACCEPTED
ADR_RESERVED_ABSENT="130 134"        # MUST be ABSENT (a file = lifecycle drift)
ADR_VIOLATIONS=""

_adr_file() {  # echo the first ADR-<n>-*.md path that actually exists, else ""
  local n="$1" hit
  for hit in "$REPO_ROOT"/.claude/adr/ADR-"$n"-*.md; do
    if [ -e "$hit" ]; then printf '%s\n' "$hit"; return 0; fi
  done
  return 0
}

# The ADR-lifecycle gate is real-repo-specific: it asserts the fixed
# {127,128,131}-present / {130,134}-absent inventory that only the real repo
# (and the E9-F10 remediation test scaffold) carry. A generic synthetic tree
# (e.g. test_verify_counts.py, ADR-000..004) legitimately lacks it — gate it on
# the RESERVED-ADR enumeration being present in CLAUDE.md so it stays robust and
# does not break the existing clean-synthetic-tree contract.
if grep -q 'RESERVED (no file' "$REPO_ROOT/CLAUDE.md" 2>/dev/null; then
for _n in $ADR_PRESENT_ACCEPTED; do
  _f=$(_adr_file "$_n")
  if [ -z "$_f" ]; then
    ADR_VIOLATIONS="${ADR_VIOLATIONS}adr_lifecycle: ADR-${_n} expected present with status: ACCEPTED, but NO file on disk
"
  elif ! grep -qiE '^status:[[:space:]]*ACCEPTED' "$_f"; then
    ADR_VIOLATIONS="${ADR_VIOLATIONS}adr_lifecycle: ADR-${_n} present but its status: frontmatter is not ACCEPTED
"
  fi
done
for _n in $ADR_RESERVED_ABSENT; do
  _f=$(_adr_file "$_n")
  if [ -n "$_f" ]; then
    ADR_VIOLATIONS="${ADR_VIOLATIONS}adr_lifecycle: ADR-${_n} is a RESERVED slot and MUST be ABSENT on disk, but a file exists (presence = drift)
"
  fi
done
fi

# -------------------------- bidirectional doc check -------------------------
# Delegated to a stdlib python3 block: reads the 3 docs, applies the
# all-matches exact/floor rules, prints violations, exits 1 on any drift.

export VC_REPO_ROOT="$REPO_ROOT"
export VC_SKILLS="$DERIVED_SKILLS" VC_CORE="$DERIVED_CORE" VC_FRONTEND="$DERIVED_FRONTEND"
export VC_DOMAIN="$DERIVED_DOMAIN" VC_ADRS="$DERIVED_ADRS" VC_HOOK_PY="$DERIVED_HOOK_PY"
export VC_LIB="$DERIVED_LIB" VC_SPEC="$DERIVED_SPEC_V1" VC_REGISTERED="$DERIVED_REGISTERED"
export VC_REGISTRATIONS="$DERIVED_REGISTRATIONS"
export VC_SCHEMA="$DERIVED_SCHEMA_FILES"
export VC_TESTS="$DERIVED_TESTS" VC_QUIET="$QUIET" VC_JSON="$JSON" VC_NO_TESTS="$NO_TESTS"
export VC_TESTS_ERRORS="$DERIVED_TESTS_ERRORS" VC_TESTS_CMD="$DERIVED_TESTS_CMD"
export VC_TEST_FILES="$DERIVED_TEST_FILES" VC_TEST_FILES_CMD="$DERIVED_TEST_FILES_CMD"
export VC_RELEASE_STEPS="$DERIVED_RELEASE_STEPS" VC_COMMANDS="$DERIVED_COMMANDS"
export VC_WORKFLOWS="$DERIVED_WORKFLOWS"
export VC_MUTATION_FIXTURES="$DERIVED_MUTATION_FIXTURES" VC_TLA_SPECS="$DERIVED_TLA_SPECS"
export VC_LIB_RECURSIVE="$DERIVED_LIB_RECURSIVE" VC_VERSION="$DERIVED_VERSION"
export VC_ADR_VIOLATIONS="$ADR_VIOLATIONS"
# Inventory echoed so the python3 block can assert CLAUDE.md's RESERVED list.
export VC_ADR_RESERVED_ABSENT="$ADR_RESERVED_ABSENT"

python3 - <<'PYEOF'
import os, re, json, sys

root = os.environ["VC_REPO_ROOT"]
def iv(k): return int(os.environ.get(k, "0") or "0")
live = {
    "skills": iv("VC_SKILLS"), "core": iv("VC_CORE"), "frontend": iv("VC_FRONTEND"),
    "domain": iv("VC_DOMAIN"), "adrs": iv("VC_ADRS"), "hook_py": iv("VC_HOOK_PY"),
    "lib": iv("VC_LIB"), "spec_v1": iv("VC_SPEC"), "registered": iv("VC_REGISTERED"),
    "registrations": iv("VC_REGISTRATIONS"),
    "schema_files": iv("VC_SCHEMA"),
    "tests": iv("VC_TESTS"),
    "test_files": iv("VC_TEST_FILES"),
    "release_steps": iv("VC_RELEASE_STEPS"),
    "commands": iv("VC_COMMANDS"),
    "workflows": iv("VC_WORKFLOWS"),
    "mutation_fixtures": iv("VC_MUTATION_FIXTURES"),
    "tla_specs": iv("VC_TLA_SPECS"),
    "lib_recursive": iv("VC_LIB_RECURSIVE"),
}

# ---- APPROX rule: band + inputs (PLAN-166 W0 F5) ----
# The band is DECLARED here and reproduced in every violation message and in
# the human/JSON report. See the APPROX CONTRACT block at the top of the file
# for why +/-5% and why the inputs must be printed.
APPROX_BAND = 0.05
# Per-metric measurement provenance. `errors` is None for metrics whose
# derivation cannot partially fail; for `tests` it is the pytest
# collection-error count, which is the difference between "the number is
# rounded" and "the number is measured over a population with holes in it".
APPROX_INPUTS = {
    "tests": {
        "command": os.environ.get("VC_TESTS_CMD", ""),
        "observed": iv("VC_TESTS"),
        "collect_errors": iv("VC_TESTS_ERRORS"),
        "skipped": os.environ.get("VC_NO_TESTS") == "1",
    },
    "test_files": {
        "command": os.environ.get("VC_TEST_FILES_CMD", ""),
        "observed": iv("VC_TEST_FILES"),
        "collect_errors": None,
        "skipped": False,
    },
}

# The numeral shape an approx claim MUST be written in: a tilde, then digits
# with optional thousands separators (`,` EN / `.` pt-BR) or a `k` suffix.
# One capturing group, always.
_APPROX_NUM = r'~\s*(\d[\d.,]*\s*[kKmM]?)'


def approx_norm(raw):
    """'14,000' / '14.000' / '14k' / '730' -> int. None when unparseable.

    Separator-agnostic on purpose: README.md writes ~14,000 and
    README.pt-BR.md writes ~14.000 and they are the SAME claim, so the
    cross-doc equality check must see the same integer for both.
    """
    s = (raw or "").strip().lower().replace(" ", "").rstrip(".,")
    mult = 1
    if s.endswith("k"):
        mult, s = 1000, s[:-1]
        # Decimal-k (PLAN-166 W0 re-pass): a '.'/',' followed by 1-2 digits
        # before the k is a DECIMAL, not a thousands separator — "~1.4k" is
        # 1,400. The old separator-strip path normalized it to 14,000, a
        # 10x error in the FALSE-PASS direction (a doc citing ~1.4k sailed
        # through a band around a live ~14,000). Integer math, no float.
        _dm = re.fullmatch(r'(\d+)[.,](\d{1,2})', s)
        if _dm:
            _whole, _frac = _dm.group(1), _dm.group(2)
            return int(_whole) * 1000 + int(_frac) * (10 ** (3 - len(_frac)))
    s = s.replace(",", "").replace(".", "")
    if not s.isdigit():
        return None
    return int(s) * mult


# Prose forms, per metric. Every regex embeds _APPROX_NUM exactly once.
# Adding a phrasing here is cheap; inventing one that matches nothing is a
# dead rule, so each entry below is pinned to a site that exists today (see
# the APPROX SITES table printed by --json `approx_sites`).
APPROX_RULES = [
    ("tests", [
        # "~14,000 cases" / "~14,000 collected cases" / "~14,000 parametrized
        # cases" / "~14,000 test cases" / "~14.000 casos" / '"~14k tests."'
        # The \** absorbs markdown bold that sits BETWEEN the numeral and its
        # noun ("reports **~14,000** collected cases" in docs/README.md).
        _APPROX_NUM + r'\**\s*(?:collected\s+|parametrized\s+|test\s+'
                      r'|hand-written\s+)?(?:cases|casos|tests)\b',
    ]),
    ("test_files", [
        _APPROX_NUM + r'\**\s*test files\b',
    ]),
]

# Table-cell forms: the numeral is alone in the VALUE cell, so no noun follows
# it and the prose regexes above cannot see it.
APPROX_TABLE_RULES = [
    ("tests", r'^Python tests collected\b'),
    ("test_files", r'^Test files\b'),
]

# Registered exemptions. See "PENDING SITES" in the header.
# (doc, metric, frozen_value, why) — EMPTY today. The one historical entry
# (CLAUDE.md tests=13000, frozen mid-session under Gate-1 cache discipline)
# was consumed when commit 65daff0 restated CLAUDE.md to ~14,000; left in
# place it permanently grandfathered the exact stale value — a revert of
# CLAUDE.md to "~13,000" exited 0 because this lookup runs BEFORE the band
# check (PLAN-166 W0 re-pass). Delete any future entry in the same commit
# that lands its restatement.
APPROX_PENDING = []
_pending_index = dict(((d, m), (v, w)) for d, m, v, w in APPROX_PENDING)
# VERSION is a dotted string, not an int — kept separate from the int `live` map.
live_version = os.environ.get("VC_VERSION", "") or ""
quiet = os.environ.get("VC_QUIET") == "1"
as_json = os.environ.get("VC_JSON") == "1"
no_tests = os.environ.get("VC_NO_TESTS") == "1"

# Docs scanned for ALL count rules (live-count claims must be exact/floor).
# RELEASE.md is RETIRED — its body has historical numbers; only scan it for
# the release_steps rule via RELEASE_DOCS below to avoid false positives.
# PLAN-161 V1 ([[feedback-adr-count-drift-unwatched-docs]], S275): the four
# previously-unwatched drift-prone docs are now first-class scan targets —
# they drifted silently twice (GA v1.1.0 and again by S278).
# PLAN-166 W0 F5 (S294): four MORE unwatched drift-prone docs promoted to
# first-class scan targets. README.pt-BR.md carried a v1.0.0-era table (55
# hooks / 44 wired / ~12.000 casos) purely because no rule spoke Portuguese;
# docs/README.md, docs/WHAT-WE-ARE.md and docs/CTO-GUIDE.md were the
# outward-facing "verify every claim" set and had drifted a full MINOR line
# behind (151 skills / 171 ADRs / 53 hooks / 22 commands).
# NOTE for whoever adds the next doc here: joining DOCS activates EVERY
# matcher, not just the one you came for — and it does NOT retro-activate
# claims whose phrasing no matcher knows. Run the gate, read
# `rule_matches_by_doc`, and add a matcher (or delete the claim) for every
# number the new doc carries.
DOCS = [
    "CLAUDE.md", "README.md", "README.pt-BR.md", "INSTALL.md",
    "docs/ARCHITECTURE.md", "docs/GUIA-COMPLETO.md", "docs/FAQ.md",
    "docs/README.md", "docs/WHAT-WE-ARE.md", "docs/CTO-GUIDE.md",
    "npm/README.md",
]
# Additional docs scanned for the subset of rules that reference them.
RELEASE_DOCS = ["RELEASE.md"]  # only release_steps rule applies
texts = {}
for d in DOCS + RELEASE_DOCS:
    p = os.path.join(root, d)
    try:
        texts[d] = open(p, encoding="utf-8").read()
    except OSError:
        texts[d] = ""

# Per-metric doc scope: most metrics only scan DOCS; release_steps also scans RELEASE_DOCS.
_RELEASE_STEPS_EXTRA_DOCS = set(RELEASE_DOCS)

# (metric, kind, [regexes]) — each regex has exactly one capturing integer group.
# kind: "exact" (value must == live) or "floor" (live must >= value).
RULES = [
    ("skills", "exact", [
        r'(\d+) reusable skills', r'(\d+)-skill inventory',
        r'(\d+) skill folders', r'(\d+) skills organizadas',
        r'(\d+) skills retained',
        # PLAN-161 V1 — phrasings carried by the four newly-watched docs.
        # "# N skills across" is the DOMAIN tree comment, not the total.
        r'# (\d+) skills(?! across)', r'(\d+) skill files',
        # PLAN-166 W0 F5 — docs/WHAT-WE-ARE.md §1.4 calls them checklists.
        r'(\d+) reusable checklists',
        # PLAN-166 W0 F5 (pt) — README.pt-BR.md prose "166 arquivos de skill".
        r'(\d+) arquivos de skill',
    ]),
    ("core", "exact", [
        r'\((\d+) universal\)', r'\((\d+)\s+universais\)',
        r'# (\d+) universal skills', r'\((\d+) core ',
        r'CORE\*\* \(universal\) \| (\d+)',
        r'(\d+) core \+',   # "42 core + 8 frontend + 116 domain" split cells
        r'(\d+) core \(universal\)',   # WHAT-WE-ARE.md §1.4 three-tier prose
    ]),
    ("frontend", "exact", [
        r'\((\d+) universal frontend\)', r'\((\d+) frontend skills',
        r'# (\d+) universal frontend', r'# (\d+) frontend skills',
        r'(\d+) frontend universais', r'(\d+) frontend \+',
        # WHAT-WE-ARE.md §1.4 — \s+ because the doc wraps the phrase across a
        # newline ("8 frontend (universal\nfrontend)"); a literal space
        # matched ZERO sites while core/domain in the SAME sentence were
        # watched (PLAN-166 W0 re-pass, dead-regex class).
        r'(\d+) frontend \(universal\s+frontend\)',
    ]),
    ("domain", "exact", [
        r'(\d+) domain across',
        r'\+ (\d+) domain',      # "42 core + 8 frontend + 116 domain" split cells
        r'# (\d+) skills across', # ARCHITECTURE.md domains/ tree comment
        r'(\d+) domain \(fintech',  # WHAT-WE-ARE.md §1.4 three-tier prose
        # pt split cell: "42 core + 8 frontend + 116 de domínio"
        r'\+ (\d+) de domínio',
    ]),
    # PLAN-166 W0 F5: `# (\d+) ADRs` is the "verify it yourself" comment that
    # both READMEs put next to `ls .claude/adr | grep -c '^ADR-'`. It matched
    # nothing before — the same vacuous-site class as S287, found by diffing
    # the grep census of the docs against `rule_matches_by_doc`.
    # PLAN-169 W2.7 (ledger E.3): the TWO GUIA-COMPLETO phrasings the
    # ledger named — "N ADRs document ..." (prose, sat stale at 189) and
    # "N Architecture Decision Records" (directory listing, ALSO stale at
    # 189 — missed by the first W2.7 pass and caught by the repass-r2
    # part-e reviewer; the ledger said "duas frases" and it meant it).
    # The \**\s* tolerates bold-wrapped numerals like hook_py below.
    ("adrs", "exact", [r'(\d+) ADRs total', r'(\d+) ADRs on disk',
                       r'#\s*(\d+) ADRs\b',
                       r'(\d+)\**\s*ADRs\**\s+document',
                       r'(\d+)\**\s*Architecture Decision Records\b']),
    ("hook_py", "exact", [
        r'(\d+) hooks total', r'(\d+) Python hook scripts',
        # \**\s*…\s+ tolerates bold-wrapped numerals and line wraps:
        # docs/README.md writes "the **57** hook\nscripts on disk" — the
        # plain '(\d+) hook scripts' form saw NEITHER (PLAN-166 W0 re-pass).
        r'(\d+)\**\s*hook\s+scripts',
        r'(\d+) em disco',   # pt: "**57 em disco**" (README.pt-BR.md)
    ]),
    # S287 vacuous-gate fix: no watched doc ever used the literal
    # "N registered hooks" — the real phrasings are "46 wired into
    # `.claude/settings.json`" (CLAUDE.md §1, ARCHITECTURE prose + table)
    # and the "Hooks wired in" table rows (README/npm, TABLE_RULES below).
    ("registered", "exact", [
        r'(\d+) registered hooks',
        # BOTH prepositions: CLAUDE.md/ARCHITECTURE say "46 wired into
        # `.claude/settings.json`", GUIA-COMPLETO says "46 hooks wired in
        # `settings.json`". The pair-rail caught the missing `wired in`
        # form against a doc that was stale at 44 — the vacuous-gate class
        # one layer deeper (a rule that matches SOME docs looks alive
        # while the doc it misses drifts).
        r'(\d+) wired into',
        r'(\d+) hooks wired in\b',
        # PLAN-166 W0 F5 — docs/README.md states the same number twice, once
        # in the "Hooks registered" table row and once in the prose that
        # explains the 57-vs-46 gap. Both BOLD-WRAP the numeral
        # ("**46** distinct scripts"), so the matcher absorbs the closing
        # `**` — the plain-space form matched ZERO sites (PLAN-166 W0
        # re-pass, dead-regex class; the approx rules already knew this
        # via their own \** — the fix just reached the exact rules too).
        r'(\d+)\**\s*distinct scripts',
        r'(\d+) ligados\b',   # pt: "**46 ligados**" (README.pt-BR.md)
    ]),
    # Total hook ENTRIES in the hooks{} subtree (one script can fire on
    # several events; includes non-.py commands). CLAUDE.md §1 +
    # ARCHITECTURE prose + the README/npm table Notes cells.
    ("registrations", "exact", [
        r'(\d+) event registrations',
        r'(\d+) registros de evento',   # pt (README.pt-BR.md table cell)
    ]),
    ("lib", "exact", [
        r'(\d+) shared (?:Python )?modules',
        r'(\d+) [`]?_lib[`/]* modules',   # catches "N `_lib/` modules" / "N _lib modules"
        r'(\d+) stdlib-only shared modules',   # ARCHITECTURE.md tree comment
    ]),
    # PLAN-166 W0 F5: spec_v1 had TABLE_RULES coverage only; README.pt-BR.md
    # states it in prose ("em `SPEC/v1/` (32 arquivos — ...").
    ("spec_v1", "exact", [r'SPEC/v1/`\s*\((\d+) arquivos']),
    ("schema_files", "exact", [
        r'(\d+) schema files',
        # "32 (28 `*.schema.md`)" in the ARCHITECTURE/CTO-GUIDE tables and
        # the pt prose "32 arquivos — 28 `*.schema.md`".
        r'(\d+) `\*\.schema\.md`',
    ]),
    ("tests", "floor", [r'(\d+)\+ tests', r'(\d+)\+ unit tests']),
    # New mechanics-derived counts (F-3.2/F-4 blind-spot closure — PLAN-113 RW-E)
    # S287 vacuous-gate fix: the two historical phrasings matched no doc
    # (rule dead since the RELEASE.md rewrite); the live citation site is
    # RELEASE.md's pointer block "`release.yml` — release-gate +
    # publish-release (N steps, ...)".
    ("release_steps", "exact", [
        r'release\.yml[^()\n]*\((\d+) steps',
    ]),
    ("commands", "exact", [
        r'(\d+) slash commands',
    ]),
    # PLAN-166 W0 F5: "workflows" IS doc-gated now. It was exempt because no
    # watched doc cited it — but docs/CTO-GUIDE.md §2 always did ("| Workflows
    # | 20 |", live 21), and the doc simply was not in DOCS. The claim is
    # carried in a table cell, so the live rule is the TABLE_RULE below and
    # there is deliberately no prose regex here (a prose regex matching
    # nothing is the dead-gate class this file exists to prevent).
    # PLAN-166 W0 F5: two counts docs/CTO-GUIDE.md §2 asserted with nothing
    # behind them. "45 fixtures" (live 85) and "1 component fully specified"
    # (live 4 published .tla specs).
    ("mutation_fixtures", "exact", [r'(\d+) mutation fixtures']),
    ("tla_specs", "exact", [r'(\d+) TLA\+ specs published']),
    # E9-F10 (i): recursive `_lib` count. Only CLAUDE.md states "N recursive";
    # README/INSTALL lack the literal, so scanning all DOCS is safe.
    ("lib_recursive", "exact", [
        r'(\d+) recursive',
    ]),
]

# ---- PLAN-161 V1: markdown-table-cell rules (the S275 miss class) ----
# A prose regex like "(\d+) ADRs" never matches "| ADRs | 178 |" — the number
# and its label sit in SEPARATE cells. These rules match on the LABEL cell
# (first cell, markdown emphasis stripped) and read the FIRST integer of the
# VALUE cell (second cell). Applied to every doc in DOCS. Tolerance 0.
TABLE_RULES = [
    ("adrs",      "exact", r'^(?:ADRs|Architecture decision records)\b'),
    ("hook_py",   "exact", r'^Hook scripts\b'),
    # PLAN-166 W0 F5: docs/CTO-GUIDE.md §2 labels the row just "Hooks" and
    # puts BOTH numbers in the value cell ("57 .py on disk; 46 wired into
    # `settings.json`"). The table extractor reads the FIRST integer, so this
    # row feeds hook_py; the second number is picked up by the `(\d+) wired
    # into` prose regex. The `$` anchor is load-bearing — an unanchored
    # `^Hooks\b` would also swallow "Hooks registered" / "Hooks wired in"
    # and assert the REGISTERED count against the on-disk metric.
    ("hook_py",   "exact", r'^Hooks$'),
    ("lib",       "exact",
     r'^(?:_lib modules|_lib/ stdlib-only modules|Shared library modules)\b'),
    ("commands",  "exact", r'^Slash commands\b'),
    ("skills",    "exact", r'^(?:Skills|Skill checklists)\b'),
    ("spec_v1",   "exact", r'^SPEC/v1 files\b'),
    ("workflows", "exact", r'^Workflows\b'),
    # ---- PLAN-166 W0 F5: README.pt-BR.md label rules (pt) ----
    # The pt-BR README carried a v1.0.0-era table (55 hooks on disk / 44 wired)
    # for one reason only: no rule spoke Portuguese. These label matchers are
    # deliberately SEPARATE entries rather than alternations bolted onto the
    # English ones, so a pt/EN LABEL COLLISION is impossible to introduce by
    # accident — see the collision audit in the header of this block:
    #   * "Architecture decision records" and "Slash commands" are identical in
    #     both languages AND mean the same metric, so the existing English
    #     rules already cover them correctly (true positives, not collisions).
    #   * every other pt label is lexically disjoint from every English label
    #     ("Scripts de hook" vs "Hook scripts", "Checklists de skills" vs
    #     "Skills"/"Skill checklists", "Módulos de biblioteca compartilhada" vs
    #     "Shared library modules", "Hooks ligados em" vs "Hooks wired in").
    #     No English regex can match a pt label and vice versa.
    ("hook_py",    "exact", r'^Scripts de hook\b'),
    ("registered", "exact", r'^Hooks ligados em\b'),
    ("lib",        "exact", r'^Módulos de biblioteca compartilhada\b'),
    ("skills",     "exact", r'^Checklists de skills\b'),
    # S287: README/npm "| Hooks wired in `settings.json` | **46** | ..." and
    # ARCHITECTURE "| Hook registrations | 46 wired into `settings.json`|".
    # PLAN-166 W0 F5 adds docs/README.md's "| Hooks registered | **46** ... |".
    ("registered", "exact",
     r'^(?:Hooks wired in|Hook registrations|Hooks registered)\b'),
]

def iter_table_rows(text):
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith('|') and s.endswith('|') and s.count('|') >= 3):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) >= 2:
            yield cells

violations = []
# S287 rule-liveness accounting: per-metric count of doc sites each rule
# actually matched (prose + table cells). Exported in --json as
# `rule_matches`; the real-repo test asserts every doc-gated metric >= 1
# (a metric at 0 is a dead gate reporting "no drift" unchecked).
rule_matches = {m: 0 for m, _, _ in RULES}
for m, _, _ in TABLE_RULES:
    rule_matches.setdefault(m, 0)
# PER-DOCUMENT accounting (pair-rail R3, P2). Aggregate-per-metric
# liveness is a FLOOR, not the proof: a rule matching 5 of 6 watched docs
# looks alive while the 6th drifts — which is exactly how
# `docs/GUIA-COMPLETO.md` sat stale at 44 hooks after the metric-level
# rule was "fixed". `rule_matches_by_doc[(metric, doc)]` lets the
# real-repo test assert an explicit expectation SET, so a document that
# silently stops matching is a failure rather than an invisible hole.
rule_matches_by_doc = {}


def _note(metric, doc):
    rule_matches[metric] = rule_matches.get(metric, 0) + 1
    key = "%s@%s" % (metric, doc)
    rule_matches_by_doc[key] = rule_matches_by_doc.get(key, 0) + 1

for metric, kind, label_rx in TABLE_RULES:
    lv = live[metric]
    for doc in DOCS:
        for cells in iter_table_rows(texts.get(doc, "")):
            label = re.sub(r'[*`]', '', cells[0]).strip()
            if not re.match(label_rx, label, re.IGNORECASE):
                continue
            value_cell = re.sub(r'[*`,]', '', cells[1])
            m = re.search(r'(\d+)', value_cell)
            if m is None:
                continue
            _note(metric, doc)
            v = int(m.group(1))
            if kind == "exact" and v != lv:
                violations.append(
                    f"{doc}: table row '{label}' cites {metric}={v}, live={lv}  (rule: exact/table-cell)"
                )

for metric, kind, regexes in RULES:
    # tests under --no-tests: still COUNT matches (liveness stays
    # observable) but never enforce against the skipped live value.
    enforce = not (metric == "tests" and no_tests)
    lv = live[metric]
    # release_steps scans both DOCS and RELEASE_DOCS; all others scan only DOCS.
    scan_docs = (DOCS + list(_RELEASE_STEPS_EXTRA_DOCS)
                 if metric == "release_steps" else DOCS)
    for doc in scan_docs:
        text = texts.get(doc, "")
        for rx in regexes:
            for m in re.finditer(rx, text):
                _note(metric, doc)
                if not enforce:
                    continue
                v = int(m.group(1))
                if kind == "exact" and v != lv:
                    violations.append(
                        f"{doc}: cites {metric}={v}, live={lv}  (rule: exact)"
                    )
                elif kind == "floor" and lv < v:
                    violations.append(
                        f"{doc}: cites {metric}>={v}+ but live={lv} (regression; rule: floor)"
                    )

# ============================  APPROX EVALUATION  ===========================
# Three failure modes (band, cross-doc equality, missing `~` marker), one
# non-failure mode (registered PENDING site), and a printed input record for
# every metric. See the APPROX CONTRACT block at the top of the file.
warnings = []
pending = []
approx_sites = []        # [{metric, doc, cited, pending}]
_approx_consumed = {}    # doc -> set of char offsets of `~` already consumed


def _consume(doc, off):
    _approx_consumed.setdefault(doc, set()).add(off)


def _record_approx(metric, doc, raw, off):
    _note(metric, doc)
    _consume(doc, off)
    cited = approx_norm(raw)
    if cited is None:
        violations.append(
            "%s: %s approx claim '~%s' is not a parseable figure"
            "  (rule: approx/shape)" % (doc, metric, raw)
        )
        return
    approx_sites.append({"metric": metric, "doc": doc, "cited": cited})


for _metric, _regexes in APPROX_RULES:
    for _doc in DOCS:
        _text = texts.get(_doc, "")
        for _rx in _regexes:
            for _m in re.finditer(_rx, _text):
                _record_approx(_metric, _doc, _m.group(1), _m.start())

# Table-cell sites: the numeral sits alone in the VALUE cell with no noun
# after it, so the prose regexes above are structurally blind to it.
for _doc in DOCS:
    _off = 0
    for _line in texts.get(_doc, "").splitlines(True):
        _s = _line.strip()
        if _s.startswith('|') and _s.endswith('|') and _s.count('|') >= 3:
            _cells = [c.strip() for c in _s.strip('|').split('|')]
            if len(_cells) >= 2:
                _label = re.sub(r'[*`]', '', _cells[0]).strip()
                for _metric, _label_rx in APPROX_TABLE_RULES:
                    if not re.match(_label_rx, _label, re.IGNORECASE):
                        continue
                    _cm = re.search(_APPROX_NUM, _cells[1])
                    if _cm is None:
                        # An approx metric written as a bare exact integer
                        # claims a precision this gate cannot honour, and the
                        # row would otherwise go completely unchecked (that is
                        # how docs/CTO-GUIDE.md sat at "| Test files | 676 |").
                        if re.search(r'\d', _cells[1]):
                            violations.append(
                                "%s: table row '%s' cites %s WITHOUT the '~' "
                                "marker (%r); approx metrics must be written "
                                "'~N'  (rule: approx/table-cell)"
                                % (_doc, _label, _metric, _cells[1])
                            )
                        continue
                    _lm = re.search(_APPROX_NUM, _line)
                    _record_approx(_metric, _doc, _cm.group(1),
                                   _off + (_lm.start() if _lm else 0))
        _off += len(_line)

_by_metric = {}
for _site in approx_sites:
    _by_metric.setdefault(_site["metric"], []).append(_site)

for _metric in sorted(_by_metric):
    _sites = _by_metric[_metric]
    _in = APPROX_INPUTS.get(_metric)
    _lv = _in["observed"] if _in else live.get(_metric, 0)
    # A live value of 0 means the derivation could not run in this tree (no
    # git work tree, --no-tests). A +/-5% band around 0 rejects every possible
    # doc figure, so enforcement is suspended and the fact is WARNED, never
    # silently skipped.
    _skip = bool(_in and _in["skipped"]) or _lv <= 0
    _tol = _lv * APPROX_BAND
    _pool = {}
    for _site in _sites:
        _frozen = _pending_index.get((_site["doc"], _metric))
        if _frozen is not None and _site["cited"] == _frozen[0]:
            _site["pending"] = True
            pending.append(
                "%s: %s=~%d is a REGISTERED PENDING site (live=%d, band "
                "+/-%d%%). %s" % (_site["doc"], _metric, _site["cited"],
                                  _lv, int(APPROX_BAND * 100), _frozen[1])
            )
            continue
        _site["pending"] = False
        _pool.setdefault(_site["cited"], []).append(_site["doc"])
        if _skip:
            continue
        if abs(_site["cited"] - _lv) > _tol:
            violations.append(
                "%s: cites %s=~%d, live=%d — OUTSIDE the +/-%d%% band "
                "[%d..%d]  (rule: approx; measured by `%s`)"
                % (_site["doc"], _metric, _site["cited"], _lv,
                   int(APPROX_BAND * 100), int(_lv - _tol), int(_lv + _tol),
                   (_in or {}).get("command", "n/a"))
            )
    if len(_pool) > 1:
        _detail = "; ".join(
            "~%d in %s" % (v, ", ".join(sorted(set(ds))))
            for v, ds in sorted(_pool.items())
        )
        violations.append(
            "approx metric '%s' is cited with DIFFERENT figures across "
            "watched docs: %s  (rule: approx/cross-doc-equality)"
            % (_metric, _detail)
        )

# Inputs of the band, surfaced as named WARNINGs (contract clause 3).
for _metric in sorted(APPROX_INPUTS):
    _in = APPROX_INPUTS[_metric]
    if _in["skipped"]:
        warnings.append(
            "approx metric '%s': live measurement SKIPPED (--no-tests) — the "
            "band is NOT enforced this run" % _metric
        )
        continue
    if _in["collect_errors"]:
        _msg = (
            "approx metric '%s': %d COLLECTION ERROR(S) in `%s` — the observed "
            "value (%d) is measured over a PARTIAL population, so the +/-%d%% "
            "band is being applied to the wrong number. Fix the collection "
            "errors before trusting this rule."
            % (_metric, _in["collect_errors"], _in["command"],
               _in["observed"], int(APPROX_BAND * 100))
        )
        # Contract clause 3 (PLAN-166 W0 re-pass): when the band was actually
        # ENFORCED over >=1 doc site this run, a partial population makes the
        # verdict untrustworthy — and the automated callers (validate.yml
        # --quiet, the release preflight piping to /dev/null) can only see
        # the exit code, so this MUST fail the gate, not warn into a void.
        # It stays a warning only when the band is already suspended
        # (observed<=0) — there is no verdict to corrupt then.
        _enforced_sites = [
            s for s in approx_sites
            if s["metric"] == _metric and not s.get("pending")
        ]
        if _enforced_sites and _in["observed"] > 0:
            violations.append(_msg + "  (rule: approx/collect-errors)")
        else:
            warnings.append(_msg)
    if _in["observed"] <= 0:
        warnings.append(
            "approx metric '%s': `%s` returned 0 — the rule is VACUOUS in this "
            "tree (band suspended)" % (_metric, _in["command"])
        )

# ---- UNMATCHED-APPROX SWEEP ----
# The "non-inventory numerals" exemption in the header must not become a
# hiding place. Any thousands-shaped approximation in a watched doc that no
# approx rule consumed is named here, with its line, as a VIOLATION — it
# fails the gate. A warning here was a dead census (PLAN-166 W0 re-pass):
# validate.yml runs --quiet and the release preflight discards output, so
# no automated caller can see anything but the exit code, and an unmatched
# "~9k" planted in a watched doc shipped through both in total silence.
# Decimal-k belongs to the family (W0 re-pass round 2): approx_norm already
# PARSES '~1.4k' / '~13,5k' as 1400/13500 (round-1 finding 7 declared the
# form part of the ~Nk family), so a CONSUMED site in that shape is
# band-checked — but this sweep did not recognize it, and an UNCONSUMED
# '~1.4k widgets' in a watched doc shipped with EXIT=0: the exact F5
# false-pass class the sweep was upgraded to VIOLATION to stop. The
# `[.,]\d{1,2}` alternative admits both EN ('.') and pt (',') decimals;
# 3-digit groups stay with the thousands alternative.
_THOUSANDS_RX = re.compile(
    r'~\s*(?:\d+[.,]\d{3}\b|\d+[.,]\d{1,2}\s*[kK]\b|\d+\s*[kK]\b)')
for _doc in DOCS:
    _text = texts.get(_doc, "")
    _consumed = _approx_consumed.get(_doc, set())
    for _m in _THOUSANDS_RX.finditer(_text):
        if _m.start() in _consumed:
            continue
        violations.append(
            "%s:%d: thousands-shaped approximation '%s' is consumed by NO "
            "approx rule — give it a live metric + matcher, or delete the "
            "numeral  (rule: approx/unmatched-sweep)"
            % (_doc, _text.count("\n", 0, _m.start()) + 1, _m.group(0).strip())
        )

# ---- E9-F10 (iii): VERSION-string coherence ----
# Anchored to the current-version DECLARATION sites ONLY (not historical
# CHANGELOG prose). Each (doc, regex) yields the literal version string, which
# must equal the live VERSION file. npm/package.json is read here (it is not in
# DOCS). A doc with zero matches contributes no violation.
if live_version:
    # S291 (pair-rail R2, P2): `VERSION=` NEVER existed in CLAUDE.md or
    # README.md — `git log -S 'VERSION='` finds no commit that added or
    # removed it. Both rules were dead from birth (the `registered` class
    # again), while the release checklist advertised them as checked.
    # Removed rather than faked: neither doc declares a version literal by
    # design (they point at the VERSION file). Every remaining site is
    # liveness-accounted below — a site that matches nothing now FAILS.
    VERSION_SITES = [
        ("INSTALL.md", r'--pin v(\d+\.\d+\.\d+)', "full"),
        # PLAN-161 V1 — current-version declaration sites in the newly-watched
        # docs (the npm README review stamp is a deliberate release tripwire:
        # a version bump forces a fresh review of the npm-facing copy).
        ("docs/ARCHITECTURE.md", r'currently\s+v(\d+\.\d+\.\d+), aligned with the repo', "full"),
        ("npm/README.md", r'last-reviewed: \d{4}-\d{2}-\d{2} v(\d+\.\d+\.\d+)', "full"),
        # S293 (codex NO-GO no rc.1 do v1.3.0 — P0s 2-4): TRÊS declarações de
        # versão corrente que estavam FORA desta lista e ficaram stale no
        # bump (a classe unwatched-doc de S291, de novo). SBOM declara o
        # triple completo; SECURITY/VERSIONING declaram a janela de suporte
        # como vMAJOR.MINOR.x — comparadas ao major.minor do VERSION vivo.
        ("SBOM.md", r'\*\*Version:\*\* `(\d+\.\d+\.\d+)`', "full"),
        ("SECURITY.md", r'\*\*Current MINOR\*\* \(`v(\d+\.\d+)\.x`\)', "minor"),
        ("VERSIONING.md", r'Current MINOR \(`v(\d+\.\d+)\.x`\)', "minor"),
        # S293 r3 P1: vigiar SÓ o Current deixa o PREVIOUS envelhecer em
        # silêncio — e a janela de suporte publicada é uma promessa a
        # adopters, não decoração. Previous = minor imediatamente anterior
        # ao vivo (rebase de MAJOR não é expressável aqui e falharia alto,
        # que é o comportamento correto para uma transição que exige juízo).
        ("SECURITY.md", r'\*\*Previous MINOR\*\* \(`v(\d+\.\d+)\.x`\)', "prev_minor"),
        ("VERSIONING.md", r'Previous MINOR \(`v(\d+\.\d+)\.x`\)', "prev_minor"),
        # PLAN-169 W2.6: the framework-version MARKER is a bump site (the
        # updater reads it marker-first); desync marker != VERSION must be
        # RED here, fail-closed, or check-framework-updates.sh loops
        # behind-minor on every adopter after a GA that skipped it.
        (".claude/.framework-version", r'\A(\d+\.\d+\.\d+)\s*\Z', "full"),
    ]
    _live_minor = ".".join(live_version.split(".")[:2])
    try:
        _maj, _min = (int(x) for x in _live_minor.split("."))
        _prev_minor = "%d.%d" % (_maj, _min - 1) if _min > 0 else ""
    except ValueError:
        _prev_minor = ""
    for doc, rx, mode in VERSION_SITES:
        _text = texts.get(doc, "")
        # S293: SBOM/SECURITY/VERSIONING não estão em DOCS (as regras de
        # contagem não se aplicam a eles) — carregue direto, senão o site
        # nasce "morto" sobre texto nunca lido.
        if not _text:
            _p = os.path.join(root, doc)
            if os.path.isfile(_p):
                try:
                    _text = open(_p, encoding="utf-8").read()
                except OSError:
                    _text = ""
        _hits = 0
        if mode == "full":
            _expected = live_version
        elif mode == "prev_minor":
            _expected = _prev_minor
        else:
            _expected = _live_minor
        if not _expected:
            # Sem previous derivável (X.0): o site não é checável por valor;
            # a liveness abaixo ainda exige que ele EXISTA.
            _expected = None
        for m in re.finditer(rx, _text):
            _hits += 1
            if _expected is not None and m.group(1) != _expected:
                violations.append(
                    f"{doc}: cites version={m.group(1)}, live VERSION={_expected}"
                    f" ({mode})  (rule: exact)"
                )
        rule_matches["version:" + doc + ":" + mode] = _hits
        # Liveness for the version family (pair-rail R2 P2 / R3 P1). The
        # discrimination that matters: a doc that EXISTS but no longer
        # carries its version literal is a DEAD release gate reporting
        # "clean" — fail loudly. A doc that does not exist at all is a
        # site that does not apply to this tree (synthetic fixtures ship
        # a subset of the docs by design) — skip, do not invent a
        # violation. The first pass of this gate failed unconditionally
        # and red-lit two existing fixture tests; the pair-rail caught
        # it because I added the gate without re-running the suite that
        # covers it.
        # EXISTENCE, not truthiness (pair-rail R4 P2): an empty file has
        # falsy text, so the truthiness form reported "clean" after any
        # version site was truncated to zero bytes — the exact opposite
        # of the stated exists-without-literal contract.
        if _hits == 0 and os.path.isfile(os.path.join(root, doc)):
            violations.append(
                f"{doc}: version site declared but matched ZERO occurrences "
                f"— dead release gate (rule: version-liveness)"
            )
    pkg_path = os.path.join(root, "npm", "package.json")
    try:
        pkg_text = open(pkg_path, encoding="utf-8").read()
    except OSError:
        pkg_text = ""
    _pkg_hits = 0
    for m in re.finditer(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', pkg_text):
        _pkg_hits += 1
        if m.group(1) != live_version:
            violations.append(
                f"npm/package.json: cites version={m.group(1)}, live VERSION={live_version}  (rule: exact)"
            )
    rule_matches["version:npm/package.json"] = _pkg_hits
    if _pkg_hits == 0 and os.path.isfile(pkg_path):
        violations.append(
            "npm/package.json: version field matched ZERO occurrences "
            "— dead release gate (rule: version-liveness)"
        )
    # OSS-D1: pyproject.toml [project] version must equal live VERSION.
    # Read independently (it is not in DOCS/texts), mirroring the
    # npm/package.json site above -- closes the silent-drift gap that let
    # pyproject lag (was 1.39.3 while VERSION was 1.46.1).
    pyproject_path = os.path.join(root, "pyproject.toml")
    try:
        pyproject_text = open(pyproject_path, encoding="utf-8").read()
    except OSError:
        pyproject_text = ""
    _pyp_hits = 0
    for m in re.finditer(r'^version\s*=\s*"(\d+\.\d+\.\d+)"', pyproject_text, re.M):
        _pyp_hits += 1
        if m.group(1) != live_version:
            violations.append(
                f"pyproject.toml: cites version={m.group(1)}, live VERSION={live_version}  (rule: exact)"
            )
    rule_matches["version:pyproject.toml"] = _pyp_hits
    if _pyp_hits == 0 and os.path.isfile(pyproject_path):
        violations.append(
            "pyproject.toml: version field matched ZERO occurrences "
            "— dead release gate (rule: version-liveness)"
        )

# ---- E9-F10 (ii): CLAUDE.md §1 RESERVED-ADR list must be exactly {130,134} ----
# Parse the "ADR-<a>/<b> RESERVED (no file ..." enumeration (PLAN-120-FOLLOWUP
# WS-A doc-truth phrasing) and compare the id-set to the live reserved-absent
# inventory exported by the bash layer.
_reserved_expected = set(
    (os.environ.get("VC_ADR_RESERVED_ABSENT", "") or "").split()
)
_rm = re.search(r'ADR-([\d/]+)\s+RESERVED \(no file', texts.get("CLAUDE.md", ""))
# A tree that does not declare the RESERVED-ADR enumeration (generic synthetic
# trees) is out of scope for this gate — skip rather than violate. The real repo
# + the E9-F10 remediation scaffold both carry the enumeration, so they ARE
# checked; this keeps the existing clean-synthetic-tree contract intact.
if _reserved_expected and _rm is not None:
    _cited = set(p for p in _rm.group(1).split("/") if p)
    if _cited != _reserved_expected:
        violations.append(
            f"CLAUDE.md: RESERVED-ADR list cites {{{','.join(sorted(_cited))}}}, "
            f"live reserved-absent set is {{{','.join(sorted(_reserved_expected))}}}  (rule: adr_lifecycle)"
        )

# ---- E9-F10 (ii): merge ADR existence-by-status violations from the bash layer ----
for _line in (os.environ.get("VC_ADR_VIOLATIONS", "") or "").splitlines():
    _line = _line.strip()
    if _line:
        violations.append(_line)

if as_json:
    out_live = dict(live)
    out_live["version"] = live_version
    print(json.dumps({"live": out_live, "violations": violations,
                      "warnings": warnings, "pending": pending,
                      "approx": {"band": APPROX_BAND,
                                 "inputs": APPROX_INPUTS,
                                 "sites": approx_sites},
                      "rule_matches": rule_matches,
                      "rule_matches_by_doc": rule_matches_by_doc}, indent=2))
    sys.exit(1 if violations else 0)

if not quiet:
    print("=== verify-counts.sh — bidirectional drift check ===")
    print("Live-derived counts:")
    for k in ("skills", "core", "frontend", "domain", "adrs", "hook_py",
              "registered", "registrations", "lib", "lib_recursive",
              "spec_v1", "schema_files",
              "tests", "test_files", "release_steps", "commands", "workflows",
              "mutation_fixtures", "tla_specs"):
        v = live[k]
        if k == "tests" and no_tests:
            v = "(skipped)"
        print(f"  {k:18s} = {v}")
    print(f"  {'version':18s} = {live_version}")
    print("")
    # Contract clause 3: an approx band without its inputs is a licence to
    # drift, so the inputs are printed on every run — command, observed
    # value, collection-error count — next to the figure the docs cite.
    print(f"Approx metrics (band +/-{int(APPROX_BAND * 100)}%):")
    for _k in sorted(APPROX_INPUTS):
        _i = APPROX_INPUTS[_k]
        _cited = sorted(set(s["cited"] for s in approx_sites
                            if s["metric"] == _k and not s.get("pending")))
        _obs = "(skipped)" if _i["skipped"] else _i["observed"]
        _lo = int(_i["observed"] * (1 - APPROX_BAND))
        _hi = int(_i["observed"] * (1 + APPROX_BAND))
        print(f"  {_k}")
        print(f"    command        = {_i['command']}")
        print(f"    observed       = {_obs}")
        print(f"    collect errors = "
              f"{'n/a' if _i['collect_errors'] is None else _i['collect_errors']}")
        print(f"    accepted band  = [{_lo}..{_hi}]")
        print(f"    cited in docs  = "
              f"{', '.join('~%d' % c for c in _cited) if _cited else '(no site)'}")
    print("")
    if pending:
        print("Pending (registered exemptions — NOT failures, but they expire):")
        for pen in pending:
            print(f"  PENDING: {pen}")
        print("")
    if warnings:
        print("Warnings (advisory — do not affect the exit code):")
        for war in warnings:
            print(f"  WARN: {war}")
        print("")
    if violations:
        print("Drift / regressions:")
        for vio in violations:
            print(f"  DRIFT: {vio}")
        print("")
        print("Exit 1: doc count(s) disagree with the live source of truth.")
        print("Update the doc number (CLAUDE.md edits land at the closeout")
        print("ceremony per Gate-1 cache discipline).")
    else:
        print("  (no drift detected — all doc counts match the live source)")

sys.exit(1 if violations else 0)
PYEOF
