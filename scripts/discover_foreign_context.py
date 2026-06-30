#!/usr/bin/env python3
"""PLAN-133 G2 — foreign-context-filename DISCOVERY (NOT a settings merge).

Honor an adopter's foreign agent-instruction files (``AGENTS.md``,
``.cursorrules``, and a small allowlist of well-known siblings) by
*reporting* their presence next to ``CLAUDE.md`` at install time.

SECURITY / SCOPE INVARIANTS (PLAN-133 §3 doctrine, rite §2):
  * **Discovery ONLY.** This module NEVER reads the *contents* of a foreign
    file, NEVER copies/overwrites/merges it, and NEVER touches
    ``.claude/settings.json``. It only checks for *existence* of a filename
    in the target ROOT (non-recursive) and prints a human-readable report.
    The whole point (PLAN-133 G2): ``install.sh:~1126`` SKIPS an existing
    ``settings.json`` — so a foreign context file must influence NOTHING
    mechanical; it is surfaced to the adopter, who decides what to do.
  * **No code execution.** Re-implemented from scratch in the stdlib. Nothing
    is fetched from, or executed out of, the ``aaif-goose/goose`` fork. A
    discovered file is never sourced, imported, or run.
  * **Fail-open on infra.** Any OS error (permission, race, weird FS) is
    swallowed: the function returns the best partial result and the CLI exits
    0. Discovery must never break an install.
  * **Default-ON report, but behaviorally inert.** Because the report mutates
    nothing, the env flag ``CEO_FOREIGN_CONTEXT_DISCOVERY`` defaults to ON
    (=report). Set it to ``0``/``false``/``no``/``off`` to silence the report
    entirely. The *behavioral* surface (settings merge) does not exist and is
    not gated by any flag — it is simply never built.

Usage (from install.sh, advisory; also runnable standalone):
    python3 scripts/discover_foreign_context.py <target-root>
    CEO_FOREIGN_CONTEXT_DISCOVERY=0 python3 scripts/discover_foreign_context.py .
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

# The closed allowlist of foreign agent-instruction filenames we DISCOVER.
# Order = report order. Kept deliberately small + well-known. AGENTS.md and
# .cursorrules are the two named in PLAN-133 G2; the rest are common siblings
# in the same "single instruction file at repo root" convention. This is an
# allowlist of *names to look for*, never a list of things to execute.
FOREIGN_CONTEXT_FILENAMES = (
    "AGENTS.md",
    ".cursorrules",
    ".cursor/rules",  # newer Cursor layout (a dir of rules); existence only
    "GEMINI.md",
    ".windsurfrules",
    ".github/copilot-instructions.md",
)

# Env flag (default-ON report; see module docstring).
DISCOVERY_FLAG = "CEO_FOREIGN_CONTEXT_DISCOVERY"

_FALSEY = frozenset({"0", "false", "no", "off", ""})


def discovery_enabled(env: Optional[dict] = None) -> bool:
    """Report enabled unless the flag is explicitly falsey.

    Default-ON because the report mutates nothing (read-only existence check).
    """
    e = os.environ if env is None else env
    raw = e.get(DISCOVERY_FLAG)
    if raw is None:
        return True
    return raw.strip().lower() not in _FALSEY


def discover_foreign_context(target_root: str) -> List[str]:
    """Return the RELATIVE names of foreign-context files present in ``target_root``.

    Discovery is EXISTENCE-ONLY and NON-RECURSIVE in spirit: each candidate is
    a fixed relative path resolved against ``target_root`` (a couple of entries
    live one directory deep, e.g. ``.github/copilot-instructions.md``, but the
    set is a closed allowlist — we never walk the tree). Contents are never
    read. Fail-open: any OS error on a candidate is treated as "absent".

    The result deliberately EXCLUDES ``CLAUDE.md`` — that is the framework's
    own native file, installed separately, not a "foreign" sibling.
    """
    found: List[str] = []
    try:
        root = os.path.abspath(target_root)
    except (OSError, ValueError):
        # Cannot even resolve the root → nothing to discover (fail-open).
        return found

    for name in FOREIGN_CONTEXT_FILENAMES:
        # Reject any candidate that tries to escape the root via ``..`` —
        # the allowlist has none, but be defensive (path-traversal hygiene).
        if name.startswith("/") or ".." in name.replace("\\", "/").split("/"):
            continue
        candidate = os.path.join(root, name)
        try:
            if os.path.exists(candidate):
                found.append(name)
        except OSError:
            # Fail-open: a stat error on one candidate must not abort the rest.
            continue
    return found


def render_report(found: List[str], target_root: str) -> List[str]:
    """Build the advisory report lines (no I/O). Pure → trivially testable."""
    lines: List[str] = []
    lines.append("")
    lines.append("==> Foreign agent-context files (DISCOVERY only — not merged)")
    if not found:
        lines.append(
            "    (none found — only CLAUDE.md governs this repo)"
        )
        return lines
    for name in found:
        lines.append("    FOUND (left untouched): {}".format(name))
    lines.append(
        "    NOTE: these were DISCOVERED, not merged. The CEO framework reads"
    )
    lines.append(
        "          CLAUDE.md; it never auto-imports a foreign context file and"
    )
    lines.append(
        "          never edits your .claude/settings.json from them. If you want"
    )
    lines.append(
        "          their guidance in-session, fold it into CLAUDE.md yourself."
    )
    return lines


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry. Always exits 0 (advisory; never gates an install)."""
    args = sys.argv[1:] if argv is None else argv
    target_root = args[0] if args else "."

    if not discovery_enabled():
        # Flag explicitly silenced → print nothing, succeed.
        return 0

    try:
        found = discover_foreign_context(target_root)
        for line in render_report(found, target_root):
            print(line)
    except Exception:  # noqa: BLE001 — fail-open on ANY infra error.
        # Discovery must never break an install. Swallow and succeed.
        return 0
    return 0


if __name__ == "__main__":  # pragma: no cover — thin CLI shim
    raise SystemExit(main())
