#!/usr/bin/env python3
"""check-debt-ledger.py — ADVISORY inline-debt ledger (PLAN-139 Wave B).

Greps first-party code for the structured ``# CEO-DEBT:`` marker grammar
and emits a DERIVED ledger of every marker plus which ones are
*ungoverned* (missing an upgrade-trigger). It is purely advisory.

## What this is

A forward-facing governance surface for in-code shortcuts that live
*below* the ADR/PLAN bar — small deliberate compromises that do not merit
a full architecture decision record but still deserve a paper trail. The
marker grammar lets an author annotate such a shortcut inline; this
script harvests them into a ledger so the debt is visible.

**Honest note:** 0 ``# CEO-DEBT:`` markers exist in the tree today, and
that is fine — this is forward-facing infrastructure, not a backlog
report. An empty ledger ("0 markers, 0 ungoverned") is the expected
steady state.

## Grammar

    # CEO-DEBT: <ceiling>, <upgrade-trigger>

- The token is **UPPERCASE** and **line-anchored** (optionally preceded
  by whitespace and/or a Markdown code-fence indent). A bare lowercase
  ``# ceo-debt:`` does NOT match — it would collide with ordinary
  comments. Prose mentions of the word never count; only a real
  line-anchored marker comment does.
- A marker WITH a comma-separated upgrade-trigger after the ceiling is
  **governed** (the author named the condition under which this shortcut
  must be revisited).
- A marker with NO upgrade-trigger (no comma, or an empty second field)
  is **ungoverned debt** and is flagged.

The marker payload is treated as **inert data**: it is never evaled,
exec'd, or shelled out. Parsing is line-by-line with a single
non-backtracking, line-anchored regex (ReDoS-safe — no nested
quantifiers over the payload).

## Where it runs

Nightly only (an 8th read-only dimension of the ``nightly-hygiene``
saved Workflow). There is deliberately **no per-validate step** — the
ledger is derived on demand and never written to a stored file (a stored
ledger would drift from the source of truth).

## Usage

    python3 .claude/scripts/check-debt-ledger.py
    python3 .claude/scripts/check-debt-ledger.py --json
    python3 .claude/scripts/check-debt-ledger.py --repo <path>

Exit code: always 0. Findings are data, not failure (ADVISORY).

## Stdlib-only

Filesystem walk + line-by-line regex. No third-party deps, no network,
no eval/exec/shell over file content (ADR-002, recursively).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Directory names pruned anywhere in the walk. A scanner-specific superset
# inspired by pytest.ini norecursedirs (PLAN-139 Wave B design, Codex C3).
_PRUNE_DIRS = frozenset(
    [
        ".git",
        "npm",
        "dist",
        "node_modules",
        "venv",
        ".codex",
        "staged",
        ".plan138-bak",
        "_lib_archived",
        "__pycache__",
        "archive",
        "worktrees",
    ]
)

# This script own tests dir holds grammar fixtures/examples. Pruning it
# guarantees the scanner never counts its own illustrative markers
# (self-non-match invariant). Resolved relative to the target repo at scan
# time, not hardcoded to the live repo path.
_SELF_FIXTURE_REL = os.path.join(".claude", "scripts", "tests")

# Absolute path of THIS script file. The module docstring and the
# regex-explanation comment legitimately contain the grammar example
# string, so the scanner must skip its own source to honor the
# self-non-match invariant (it would otherwise count its own examples).
_SELF_SCRIPT = Path(__file__).resolve()

# Repo-relative path to this scanner. When --repo points at ANOTHER tree
# that carries its OWN copy of this script (a second checkout, an install
# target), that copy is NOT __file__, so excluding only __file__ would let
# the copy's docstring grammar example be miscounted as real debt. Exclude
# the script resolved relative to the target repo too (Codex pair-rail P2).
_SELF_SCRIPT_REL = os.path.join(".claude", "scripts", "check-debt-ledger.py")

# The grammar reference doc legitimately contains worked marker examples
# inside its code fences. It is part of THIS tool's own documentation, so
# the scanner skips it for the same self-non-match reason as its source.
# Relative to the target repo (resolved at scan time, not hardcoded).
_SELF_DOC_REL = os.path.join("docs", "ceo-debt-grammar.md")

# File extensions worth scanning for first-party source markers. Kept
# narrow on purpose: markers are code/doc comments, not binary assets.
_SCAN_SUFFIXES = frozenset(
    [
        ".py",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".sh",
        ".bash",
        ".md",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".txt",
    ]
)

# Line-anchored, non-backtracking marker regex.
#
#   ^\s*           optional leading whitespace / code-fence indent
#   #\s*           EXACTLY ONE comment mark then optional space
#   CEO-DEBT:      the UPPERCASE sentinel (lowercase will NOT match)
#   \s*(.*)$       the rest of the line is the INERT payload (captured)
#
# Exactly one '#' is required (not '#+'): a code comment marker is a single
# '#', whereas '## CEO-DEBT:' would be a Markdown heading — the grammar doc
# states headings/prose never count, so they must not match (Codex pair-rail
# P2). (.*) is a single greedy match over the remainder of one physical line
# (matching is line-by-line here); there is no nested quantifier and no
# alternation over the payload, so this is linear-time / ReDoS-safe.
_MARKER_RE = re.compile(r"^\s*#\s*CEO-DEBT:\s*(.*)$")


def _iter_source_files(repo: Path) -> List[Path]:
    """Yield first-party source files under ``repo``, pruning vendored /
    generated / self-fixture directories.

    The walk prunes any directory whose *name* is in ``_PRUNE_DIRS`` at any
    depth, this script own ``tests/`` fixtures dir, this script own source
    file, AND this script own grammar doc (all three carry grammar example
    strings) — every path resolved against the target repo so a synthetic
    --repo tree is handled too.
    """
    out: List[Path] = []
    self_fixtures = (repo / _SELF_FIXTURE_REL).resolve()
    self_doc = (repo / _SELF_DOC_REL).resolve()
    # Exclude both the running script (__file__) AND the target repo's own
    # copy of it (relevant when --repo points at a different tree).
    self_scripts = {_SELF_SCRIPT, (repo / _SELF_SCRIPT_REL).resolve()}
    for dirpath, dirnames, filenames in os.walk(repo):
        # Prune in place so os.walk does not descend into them.
        dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS]
        here = Path(dirpath).resolve()
        # Prune the script own fixtures/examples dir (self-non-match).
        if here == self_fixtures or self_fixtures in here.parents:
            dirnames[:] = []
            continue
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix not in _SCAN_SUFFIXES:
                continue
            # Skip THIS script (and the target repo's own copy of it) + its
            # grammar doc (all carry grammar examples).
            rp = p.resolve()
            if rp in self_scripts or rp == self_doc:
                continue
            out.append(p)
    return sorted(out)


def parse_markers_in_text(text: str) -> List[Dict[str, Any]]:
    """Return a list of marker dicts found in ``text`` (one source file).

    Each marker is ``{line, ceiling, trigger, governed, raw}``. The payload
    after ``CEO-DEBT:`` is split on the FIRST comma: the left side is the
    ceiling, the right side (if present and non-empty) is the upgrade
    trigger. A marker with no comma — or an empty trigger field — is
    ``governed=False`` (ungoverned debt).
    """
    markers: List[Dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = _MARKER_RE.match(line)
        if not m:
            continue
        payload = m.group(1).strip()
        ceiling, sep, trigger = payload.partition(",")
        ceiling = ceiling.strip()
        trigger = trigger.strip()
        governed = bool(sep) and bool(trigger)
        markers.append(
            {
                "line": lineno,
                "ceiling": ceiling,
                "trigger": trigger,
                "governed": governed,
                "raw": payload,
            }
        )
    return markers


def build_ledger(repo: Path) -> Dict[str, Any]:
    """Build the derived debt ledger for the tree rooted at ``repo``."""
    repo = repo.resolve()
    findings: List[Dict[str, Any]] = []
    for src in _iter_source_files(repo):
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for marker in parse_markers_in_text(text):
            try:
                rel = str(src.resolve().relative_to(repo))
            except ValueError:
                rel = str(src)
            entry = dict(marker)
            entry["path"] = rel
            findings.append(entry)
    findings.sort(key=lambda f: (f["path"], f["line"]))
    ungoverned = [f for f in findings if not f["governed"]]
    return {
        "markers_count": len(findings),
        "ungoverned_count": len(ungoverned),
        "markers": findings,
        "advisory": True,
    }


def _print_human(ledger: Dict[str, Any]) -> None:
    """Human-readable ledger. Footer mirrors check-staleness.py OUTPUT
    STYLE (not a shared import): ``N markers, M ungoverned``.
    """
    markers = ledger["markers"]
    print("# inline-debt ledger (advisory, derived)")
    if not markers:
        print("  OK: no CEO-DEBT markers found.")
    else:
        for f in markers:
            tag = "governed" if f["governed"] else "UNGOVERNED"
            print("  [%-10s] %s:%d" % (tag, f["path"], f["line"]))
            print("    ceiling: %s" % (f["ceiling"] or "(none)"))
            if f["governed"]:
                print("    trigger: %s" % f["trigger"])
            else:
                print("    trigger: (missing — ungoverned debt)")
            print()
    # Footer (check-staleness.py output-style mirror).
    print(
        "%d markers, %d ungoverned"
        % (ledger["markers_count"], ledger["ungoverned_count"])
    )


def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="ceo-orchestration inline-debt ledger (advisory, derived)"
    )
    parser.add_argument(
        "--repo",
        "--repo-root",
        dest="repo",
        default=".",
        help="project root to scan (default: cwd)",
    )
    parser.add_argument(
        "--json", action="store_true", help="machine-readable output"
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    ledger = build_ledger(repo)

    if args.json:
        print(json.dumps(ledger, indent=2, sort_keys=True))
    else:
        _print_human(ledger)

    # ADVISORY: always exit 0. Findings are data, not failure.
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    return _cli(list(sys.argv[1:]) if argv is None else argv)


if __name__ == "__main__":
    sys.exit(main())
