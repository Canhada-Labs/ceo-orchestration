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
# checked against EVERY occurrence in the three docs (all-matches, NOT
# head -1). Two rule kinds:
#   - exact : the doc number MUST equal the live count.
#   - floor : the doc states "N+"; the live count MUST be >= N (so adding a
#             test never churns the docs — AC6).
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
#   tests             pytest --collect-only -q .claude/             floor (N+)
#   release_steps     grep -c '      - name:' release.yml           exact (29)
#   commands          find .claude/commands -name '*.md'             exact (27)
#   workflows         find .github/workflows -name '*.yml'           derived only (no doc cites it — not doc-gated)
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
      sed -n '2,75p' "$0"
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

# Test count: collect-only across .claude/. Collection errors in plan-specific
# fixture suites are tolerated (they don't represent code regressions). The
# collected integer is the load-bearing floor signal.
DERIVED_TESTS=0
if [ "$NO_TESTS" -eq 0 ]; then
  DERIVED_TESTS=$(
    cd "$REPO_ROOT" && \
    python3 -m pytest --collect-only -q .claude/ 2>&1 | \
    awk '/[0-9]+ tests? collected/ {
      for (i = 1; i <= NF; i++) {
        gsub(/\x1b\[[0-9;]*m/, "", $i)
        if ($i ~ /^[0-9]+$/) { print $i; exit }
      }
    }' || true
  )
  DERIVED_TESTS=${DERIVED_TESTS:-0}
fi

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
export VC_RELEASE_STEPS="$DERIVED_RELEASE_STEPS" VC_COMMANDS="$DERIVED_COMMANDS"
export VC_WORKFLOWS="$DERIVED_WORKFLOWS"
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
    "release_steps": iv("VC_RELEASE_STEPS"),
    "commands": iv("VC_COMMANDS"),
    "workflows": iv("VC_WORKFLOWS"),
    "lib_recursive": iv("VC_LIB_RECURSIVE"),
}
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
DOCS = [
    "CLAUDE.md", "README.md", "INSTALL.md",
    "docs/ARCHITECTURE.md", "docs/GUIA-COMPLETO.md", "docs/FAQ.md",
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
    ]),
    ("core", "exact", [
        r'\((\d+) universal\)', r'\((\d+)\s+universais\)',
        r'# (\d+) universal skills', r'\((\d+) core ',
        r'CORE\*\* \(universal\) \| (\d+)',
        r'(\d+) core \+',   # "42 core + 8 frontend + 116 domain" split cells
    ]),
    ("frontend", "exact", [
        r'\((\d+) universal frontend\)', r'\((\d+) frontend skills',
        r'# (\d+) universal frontend', r'# (\d+) frontend skills',
        r'(\d+) frontend universais', r'(\d+) frontend \+',
    ]),
    ("domain", "exact", [
        r'(\d+) domain across',
        r'\+ (\d+) domain',      # "42 core + 8 frontend + 116 domain" split cells
        r'# (\d+) skills across', # ARCHITECTURE.md domains/ tree comment
    ]),
    ("adrs", "exact", [r'(\d+) ADRs total', r'(\d+) ADRs on disk']),
    ("hook_py", "exact", [
        r'(\d+) hooks total', r'(\d+) Python hook scripts', r'(\d+) hook scripts',
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
    ]),
    # Total hook ENTRIES in the hooks{} subtree (one script can fire on
    # several events; includes non-.py commands). CLAUDE.md §1 +
    # ARCHITECTURE prose + the README/npm table Notes cells.
    ("registrations", "exact", [r'(\d+) event registrations']),
    ("lib", "exact", [
        r'(\d+) shared (?:Python )?modules',
        r'(\d+) [`]?_lib[`/]* modules',   # catches "N `_lib/` modules" / "N _lib modules"
        r'(\d+) stdlib-only shared modules',   # ARCHITECTURE.md tree comment
    ]),
    ("schema_files", "exact", [r'(\d+) schema files']),
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
    # "workflows" is deliberately NOT doc-gated: no watched doc cites the
    # workflow count (S287 liveness sweep). The derived value stays in the
    # --json/human output; re-add a rule here TOGETHER with the doc claim.
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
    ("lib",       "exact", r'^(?:_lib modules|Shared library modules)\b'),
    ("commands",  "exact", r'^Slash commands\b'),
    ("skills",    "exact", r'^(?:Skills|Skill checklists)\b'),
    ("spec_v1",   "exact", r'^SPEC/v1 files\b'),
    # S287: README/npm "| Hooks wired in `settings.json` | **46** | ..." and
    # ARCHITECTURE "| Hook registrations | 46 wired into `settings.json`|".
    ("registered", "exact", r'^(?:Hooks wired in|Hook registrations)\b'),
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
    ]
    _live_minor = ".".join(live_version.split(".")[:2])
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
        _expected = live_version if mode == "full" else _live_minor
        for m in re.finditer(rx, _text):
            _hits += 1
            if m.group(1) != _expected:
                violations.append(
                    f"{doc}: cites version={m.group(1)}, live VERSION={_expected}"
                    f" ({mode})  (rule: exact)"
                )
        rule_matches["version:" + doc] = _hits
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
                      "rule_matches": rule_matches,
                      "rule_matches_by_doc": rule_matches_by_doc}, indent=2))
    sys.exit(1 if violations else 0)

if not quiet:
    print("=== verify-counts.sh — bidirectional drift check ===")
    print("Live-derived counts:")
    for k in ("skills", "core", "frontend", "domain", "adrs", "hook_py",
              "registered", "registrations", "lib", "lib_recursive",
              "spec_v1", "schema_files",
              "tests", "release_steps", "commands", "workflows"):
        v = live[k]
        if k == "tests" and no_tests:
            v = "(skipped)"
        print(f"  {k:16s} = {v}")
    print(f"  {'version':16s} = {live_version}")
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
