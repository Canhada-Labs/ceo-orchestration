#!/usr/bin/env python3
"""fan-plan-parser — parse spec-kit-style AC lines `[P?][USn][path]`.

PLAN-138 Wave B (ADR-151) — the parser explicitly reserved by ADR-138's
§Future Work clause. It reads the AC-line grammar formalized in ADR-138
(lines 54-70):

    - [P0] [US1] [.claude/skills/core/<name>/SKILL.md] Description ...

Where:

- ``[P0]/[P1]/[P2]/[P3]`` — optional priority (defaults to ``P1``).
- ``[USn]`` — optional user-story group (defaults to ``null``).
- ``[path]`` — optional file anchor (defaults to ``null``).

## Design invariants (PLAN-138 Wave B, ADR-138 g1/g3)

- **stdlib-only, py3.9-safe** — no third-party imports, no runtime ``X | Y``
  unions, no ``match``.
- **ReDoS-safe** — every regex is anchored and linear-time. Bracket tokens
  are extracted by a fixed, non-backtracking single-character scan (NOT a
  nested/unbounded quantifier). Each line is length-capped (``MAX_LINE_LEN``)
  BEFORE any matching, so a pathological 100k-char line completes in well
  under 0.5s.
- **Lenient / fail-open** — a malformed line never raises; it degrades to the
  defaults (``P1``/``null``/``null``). This preserves backward-compat for all
  existing plans (ADR-138 g3): scanning the full corpus yields zero raised
  exceptions and zero rejected lines.
- **No fan-out here.** This module ONLY parses + reports. It never calls
  ``parallel()``/``agent()`` and never spawns. The advisory ``/fan-plan``
  command (``commands/fan-plan.md``) consumes this parser's JSON and PRINTS a
  proposed read-only fan-out for Owner confirmation.

## CLI

    python3 fan-plan-parser.py --line '- [P0] [US1] [src/x.py] do thing' --json
    python3 fan-plan-parser.py --scan-plans .claude/plans/ --json

``--scan-plans`` is constrained to the repo ``.claude/plans/`` tree; an
absolute or arbitrary directory is rejected. Plans are enumerated by parsed
numeric id (NOT a ``PLAN-0[0-9][0-9]`` glob, which misses PLAN-100..109) so
the full corpus 001-current is covered.

## Exit codes

- 0 — success (always, when input is well-formed at the CLI level; parsing
  itself is lenient and never fails a line).
- 2 — CLI usage error (bad args, or ``--scan-plans`` outside the plans tree).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# A defensive per-line cap applied BEFORE any regex/scan. ReDoS defense: even
# a pathological adversarial line is truncated to a bounded prefix, so the
# fixed single-pass bracket scan is O(MAX_LINE_LEN) per line, not O(n) in the
# raw (possibly 100k-char) input.
MAX_LINE_LEN = 4096

VALID_PRIORITIES = ("P0", "P1", "P2", "P3")
DEFAULT_PRIORITY = "P1"

# Anchored, linear-time validators (NO nested/unbounded quantifiers).
# Priority token: exactly P followed by a single digit 0-3.
_PRIORITY_RE = re.compile(r"^P[0-3]$")
# User-story token: US followed by 1..6 digits (bounded — no unbounded +).
_STORY_RE = re.compile(r"^US[0-9]{1,6}$")
# Plan filename id parser (bounded digit run).
_PLAN_ID_RE = re.compile(r"^PLAN-([0-9]{1,4})")


def _extract_leading_bracket_tokens(line: str) -> Tuple[List[str], str]:
    """Extract leading ``[...]`` tokens via a fixed single-pass scan.

    Returns ``(tokens, remainder)`` where ``tokens`` is the ordered list of
    bracket contents found at the start of the line (after an optional ``- ``
    list marker and surrounding whitespace) and ``remainder`` is the rest of
    the line after the last consumed bracket.

    This is deliberately NOT a regex with nested quantifiers (the classic
    ReDoS trap). It walks the string once, character by character, with a
    hard bound of ``MAX_LINE_LEN``. Each ``[`` must close with a matching
    ``]`` before the next token begins; an unterminated ``[`` stops the scan
    (the rest is treated as description), so the function is total and
    linear-time.
    """
    tokens: List[str] = []
    i = 0
    n = len(line)

    # Skip an optional leading list marker ("- ", "* ", "+ ") + whitespace.
    while i < n and line[i] in " \t":
        i += 1
    if i < n and line[i] in "-*+":
        i += 1
        while i < n and line[i] in " \t":
            i += 1

    while i < n:
        # Skip inter-token whitespace.
        while i < n and line[i] in " \t":
            i += 1
        if i >= n or line[i] != "[":
            break
        # Find the matching close bracket via a single forward scan.
        j = i + 1
        closed = False
        while j < n:
            ch = line[j]
            if ch == "]":
                closed = True
                break
            if ch == "[":
                # A nested/unclosed open before a close: stop treating this
                # as a leading-token region (lenient; not an error).
                break
            j += 1
        if not closed:
            break
        tokens.append(line[i + 1:j])
        i = j + 1

    remainder = line[i:].strip()
    return tokens, remainder


def parse_ac_line(raw_line: str) -> Dict[str, Optional[str]]:
    """Parse a single AC line into priority/story/path/description.

    Lenient: never raises. Unknown/missing tokens degrade to defaults
    (priority ``P1``, story ``None``, path ``None``). A ``warnings`` list
    records non-fatal observations (e.g. an unrecognized leading bracket
    token) for diagnostics; its presence never changes exit status.
    """
    result: Dict[str, Optional[str]] = {
        "priority": DEFAULT_PRIORITY,
        "story": None,
        "path": None,
        "description": "",
    }
    warnings: List[str] = []

    if raw_line is None:
        result["warnings"] = warnings  # type: ignore[assignment]
        return result

    # ReDoS defense: cap BEFORE any scanning/matching.
    line = raw_line
    if len(line) > MAX_LINE_LEN:
        line = line[:MAX_LINE_LEN]
        warnings.append("line_truncated_to_max_len")

    # Strip a trailing newline only; preserve interior content.
    line = line.rstrip("\r\n")

    tokens, remainder = _extract_leading_bracket_tokens(line)

    saw_priority = False
    saw_story = False
    saw_path = False
    for tok in tokens:
        tok_stripped = tok.strip()
        if _PRIORITY_RE.match(tok_stripped):
            if not saw_priority:
                result["priority"] = tok_stripped
                saw_priority = True
            continue
        if _STORY_RE.match(tok_stripped):
            if not saw_story:
                result["story"] = tok_stripped
                saw_story = True
            continue
        # Anything else in a leading bracket is treated as the path anchor
        # (first occurrence wins). spec-kit's [path] has no fixed charset, so
        # we accept it verbatim rather than over-validate.
        if not saw_path and tok_stripped:
            result["path"] = tok_stripped
            saw_path = True
            continue
        warnings.append("ignored_extra_bracket_token")

    result["description"] = remainder
    result["warnings"] = warnings  # type: ignore[assignment]
    return result


def _plans_dir_is_within_repo(plans_dir: Path, repo_root: Path) -> bool:
    """Return True iff ``plans_dir`` resolves inside ``repo_root/.claude/plans``.

    Rejects absolute/arbitrary directories that escape the plans tree
    (path-traversal hardening for ``--scan-plans``).
    """
    expected = (repo_root / ".claude" / "plans").resolve()
    try:
        resolved = plans_dir.resolve()
    except OSError:
        return False
    if resolved == expected:
        return True
    # Allow the exact plans dir only; not a parent, not a sibling.
    return False


def _numeric_id_from_name(name: str) -> Optional[int]:
    """Parse the numeric plan id from a filename, or None if not a plan file."""
    m = _PLAN_ID_RE.match(name)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def scan_plans(plans_dir: Path, repo_root: Path) -> Dict[str, object]:
    """Scan every ``PLAN-*.md`` in ``plans_dir`` by parsed numeric id.

    Backward-compat (ADR-138 g3): enumerates plans by parsed numeric id (NOT
    a ``PLAN-0[0-9][0-9]`` glob — that misses PLAN-100..109), so the full
    corpus 001-current is covered. Every AC-shaped line is parsed leniently;
    a parse that hits an unexpected condition is counted as a *warning*, never
    a raised exception and never a rejected line.

    Returns a JSON-serializable summary:
        {
          "plans_scanned": int,        # every PLAN-*.md file walked (incl. the
                                       # non-numeric PLAN-SCHEMA.md) — matches
                                       # `find ... -name 'PLAN-*.md' | wc -l`
          "ac_lines_parsed": int,
          "rejected": int,             # always 0 (lenient)
          "plan_ids": [int, ...],      # sorted NUMERIC ids covered (100+ incl.)
          "warnings": int,
        }
    """
    summary: Dict[str, object] = {
        "plans_scanned": 0,
        "ac_lines_parsed": 0,
        "rejected": 0,
        "plan_ids": [],
        "warnings": 0,
    }

    if not _plans_dir_is_within_repo(plans_dir, repo_root):
        # Constrained to the repo plans tree; refuse arbitrary dirs.
        summary["error"] = "scan_plans_dir_outside_repo_plans_tree"
        return summary

    plan_ids: List[int] = []
    plans_scanned = 0
    ac_lines = 0
    warn_count = 0

    # Enumerate over the broad, bounded ``PLAN-*.md`` glob (top-level only).
    # ``plans_scanned`` counts every ``PLAN-*.md`` file the scan walks (this
    # matches `find .claude/plans -maxdepth 1 -type f -name 'PLAN-*.md'`, which
    # INCLUDES the non-numeric ``PLAN-SCHEMA.md`` definition file). ``plan_ids``
    # collects ONLY parsed numeric ids — covering 001..current including 100+
    # (the glob, not a `PLAN-0[0-9][0-9]` pattern, is what reaches 100+).
    try:
        candidates = sorted(plans_dir.glob("PLAN-*.md"))
    except OSError:
        candidates = []

    for path in candidates:
        if not path.is_file():
            continue
        plans_scanned += 1
        num = _numeric_id_from_name(path.name)
        if num is not None:
            plan_ids.append(num)
        # Read leniently; a binary/garbage plan must not crash the scan. We
        # parse AC lines from every walked file (numeric or the schema doc);
        # a non-numeric file simply contributes no id but is still scanned.
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            warn_count += 1
            continue
        for raw in text.splitlines():
            stripped = raw.lstrip()
            # Only consider lines that look like a checklist/AC line; this is
            # a cheap prefix test, not a regex backtrack.
            if not (stripped.startswith("- ") or stripped.startswith("* ")):
                continue
            parsed = parse_ac_line(raw)
            ac_lines += 1
            warns = parsed.get("warnings")
            if isinstance(warns, list) and warns:
                warn_count += len(warns)

    summary["plans_scanned"] = plans_scanned
    summary["ac_lines_parsed"] = ac_lines
    summary["rejected"] = 0
    summary["plan_ids"] = sorted(plan_ids)
    summary["warnings"] = warn_count
    return summary


def _repo_root() -> Path:
    """Resolve the repo root from this script's location (.claude/scripts/)."""
    return Path(__file__).resolve().parent.parent.parent


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint. Lenient parsing; exit 2 only on CLI usage errors."""
    parser = argparse.ArgumentParser(
        description="Parse spec-kit-style AC lines [P?][USn][path] (advisory).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--line", help="parse a single AC line")
    group.add_argument(
        "--scan-plans",
        metavar="DIR",
        help="scan all PLAN-*.md in DIR (must be the repo .claude/plans tree)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    repo_root = _repo_root()

    if args.line is not None:
        parsed = parse_ac_line(args.line)
        if args.json:
            print(json.dumps(parsed, sort_keys=True))
        else:
            print(
                "priority={p} story={s} path={pa} description={d}".format(
                    p=parsed["priority"],
                    s=parsed["story"],
                    pa=parsed["path"],
                    d=parsed["description"],
                )
            )
        return 0

    # --scan-plans
    plans_dir = Path(os.path.expanduser(args.scan_plans))
    if not plans_dir.is_absolute():
        plans_dir = (Path.cwd() / plans_dir)
    summary = scan_plans(plans_dir, repo_root)
    if summary.get("error"):
        # Constraint violation — CLI usage error.
        if args.json:
            print(json.dumps(summary, sort_keys=True))
        else:
            print("error: {e}".format(e=summary["error"]), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(
            "plans_scanned={ps} ac_lines_parsed={al} rejected={r} warnings={w}".format(
                ps=summary["plans_scanned"],
                al=summary["ac_lines_parsed"],
                r=summary["rejected"],
                w=summary["warnings"],
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
