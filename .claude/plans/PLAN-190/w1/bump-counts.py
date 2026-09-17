#!/usr/bin/env python3
"""PLAN-190 W1 — derivator: bump the inventory counts that
``.claude/scripts/local/verify-counts.sh`` cross-checks, after ONE hook
(``check_workflow_launch.py``), ONE ``_lib`` module (``launch_ledger.py``) and
TWO settings registrations (PreToolUse + PostToolUse on ``Workflow``) enter the
tree.

It applies the SAME citation regexes the gate uses (copied from
``verify-counts.sh`` — prose "exact" rules, table-row rules and the CHANGELOG
header rule) and replaces a captured number ONLY when it equals the expected
old value, so a doc that already moved (or cites a different inventory) is
never touched by accident. Idempotent: a second run changes nothing.

Usage: ``python3 bump-counts.py <repo-root> [--check]`` — ``--check`` lists what
would change and exits 3 if anything would. Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# metric -> (old, new)
BUMPS: Dict[str, Tuple[int, int]] = {
    "hook_py": (59, 60),
    "registered": (48, 49),
    "registrations": (50, 52),
    "lib": (71, 72),
}

# Prose "exact" citation regexes — verbatim from verify-counts.sh (metric families we bump).
PROSE: Dict[str, List[str]] = {
    "hook_py": [
        r"(\d+) hooks total", r"(\d+) Python hook scripts",
        r"(\d+)\**\s*hook\s+scripts",
        r"(\d+) em disco",
    ],
    "registered": [
        r"(\d+) registered hooks",
        r"(\d+) wired into",
        r"(\d+) hooks wired in\b",
        r"(\d+)\**\s*distinct scripts",
        r"(\d+) ligados\b",
    ],
    "registrations": [
        r"(\d+) event registrations",
        r"(\d+) registros de evento",
    ],
    "lib": [
        r"(\d+) shared (?:Python )?modules",
        r"(\d+) [`]?_lib[`/]* modules",
        r"(\d+) stdlib-only shared modules",
        r"(\d+) `_lib` modules\)",  # CHANGELOG header rule
    ],
}

# Table-row rules: a line starting with `| <label>` cites the metric in its first numeric cell.
ROWS: List[Tuple[str, str]] = [
    ("hook_py", r"^\|\s*Hook scripts\b"),
    ("hook_py", r"^\|\s*Hooks\s*\|"),
    ("hook_py", r"^\|\s*Scripts de hook\b"),
    ("registered", r"^\|\s*Hooks ligados em\b"),
    ("registered", r"^\|\s*(?:Hooks wired in|Hook registrations|Hooks registered)\b"),
    ("lib", r"^\|\s*(?:Shared library modules|M[oó]dulos de biblioteca compartilhada|`_lib/` stdlib-only modules|`_lib` modules)\b"),
]

DOCS = [
    "CLAUDE.md", "README.md", "README.pt-BR.md", "INSTALL.md", "CHANGELOG.md",
    "docs/ARCHITECTURE.md", "docs/README.md", "docs/GUIA-COMPLETO.md", "docs/CTO-GUIDE.md",
    "npm/README.md",
]


def _sub_prose(text: str, metric: str) -> Tuple[str, int]:
    old, new = BUMPS[metric]
    n = 0
    for rx in PROSE[metric]:
        def repl(m: "re.Match[str]") -> str:
            nonlocal n
            if int(m.group(1)) != old:
                return m.group(0)
            n += 1
            s, e = m.span(1)
            return m.group(0)[: s - m.start()] + str(new) + m.group(0)[e - m.start():]
        text = re.sub(rx, repl, text)
    return text, n


def _sub_rows(text: str, metric: str, row_rx: str) -> Tuple[str, int]:
    old, new = BUMPS[metric]
    n = 0
    out: List[str] = []
    num_rx = re.compile(r"(\*\*)?\b(\d+)\b(\*\*)?")
    for line in text.splitlines(keepends=True):
        if re.match(row_rx, line):
            cells = line.split("|")
            # the first numeric token after the label cell
            for i in range(2, len(cells)):
                m = num_rx.search(cells[i])
                if m:
                    if int(m.group(2)) == old:
                        cells[i] = cells[i][: m.start(2)] + str(new) + cells[i][m.end(2):]
                        n += 1
                    break
            line = "|".join(cells)
        out.append(line)
    return "".join(out), n


def main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    root = Path(argv[0]).resolve()
    check = "--check" in argv[1:]
    total = 0
    for rel in DOCS:
        p = root / rel
        if not p.is_file():
            continue
        original = p.read_text(encoding="utf-8")
        text = original
        changed = 0
        for metric, row_rx in ROWS:
            text, k = _sub_rows(text, metric, row_rx)
            changed += k
        for metric in BUMPS:
            text, k = _sub_prose(text, metric)
            changed += k
        if text != original:
            total += changed
            print("%s: %d substitution(s)%s" % (rel, changed, " (would change)" if check else ""))
            if not check:
                p.write_text(text, encoding="utf-8")
    if total == 0:
        print("no changes (already bumped)")
    return 3 if (check and total) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
