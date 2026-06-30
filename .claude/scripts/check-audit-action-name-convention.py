#!/usr/bin/env python3
"""ADR-065 advisory linter — audit-event naming convention.

Imports `_KNOWN_ACTIONS` from `.claude/hooks/_lib/audit_emit` at runtime
and checks each action literal against the `<surface>_<verb>[_modifier]`
regex. Entries matching the rule pass silently; entries that DON'T match
are emitted as advisory findings unless they appear in the grandfathered
allowlist (ADR-065 §Enforcement).

This is a pure structural check — no AST parse, no import of audit_emit's
heavy dependencies. The script reads audit_emit.py as text and extracts
the `_KNOWN_ACTIONS = { ... }` block via a literal-eval-safe regex.

stdlib-only. Python 3.9+. ADR-065 enforcement artifact.

Usage
-----

    python3 .claude/scripts/check-audit-action-name-convention.py

    # Strict mode — non-zero exit on any non-grandfathered violation
    python3 .claude/scripts/check-audit-action-name-convention.py --strict

    # List all action names + convention match status + exit 0
    python3 .claude/scripts/check-audit-action-name-convention.py --audit

CI wiring
---------

The `validate.yml` workflow runs this script as an advisory step
(non-blocking in SPEC v1 per ADR-065; promoted to fail-on-finding in v2).
Adding the step costs ~1s wall-clock and pins the naming convention
without blocking additive ADR-065-compliant contributions.

Exit codes
----------

  0 — no convention violations (or --audit mode)
  1 — violations found AND --strict set
  2 — internal error (file I/O, regex parse)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_EMIT_PATH = (
    REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"
)

# Naming convention per ADR-065:
#   <surface>_<verb>[_<modifier>]
# - surface: lowercase slug (1+ letters starting)
# - verb: lowercase slug
# - modifier: optional, 1 or 2 additional lowercase segments
# - Separator: single underscore; no double underscores; no camelCase
_CONVENTION_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+){1,3}$")

# ADR-065 §Enforcement grandfathered allowlist. The ADR documents 1
# primary entry (tier_policy_promote_cost_gated — the semantic-ambiguity
# outlier); 4 additional entries capture names that exceed the documented
# regex slot-count (>3 slots after surface) but are semantically correct
# per the surface+verb+modifier rubric when the surface itself is
# compound (e.g. "tier_policy_*", "mcp_server_*"). ADR-065 treats these
# as "freeze as-is" per the decision paragraph. Future exceptions
# require an ADR-065 amendment.
_GRANDFATHERED: Set[str] = {
    "tier_policy_promote_cost_gated",
    # Compound-surface outliers (ADR-065 freeze; 5-6 segments total).
    "mcp_server_disabled_by_kill_switch",
    "tier_policy_hmac_verify_failed",
    "tier_policy_adopter_override_respected",
    "tier_policy_dry_run_complete",
}

# Regex to extract a string literal from _KNOWN_ACTIONS block. We accept
# single or double quoted strings and allow a trailing comma + comment.
_LITERAL_RE = re.compile(
    r'^\s*["\']([a-zA-Z_][a-zA-Z0-9_]*)["\']\s*,',
    flags=re.MULTILINE,
)


def _read_actions() -> List[str]:
    """Return ordered list of action literals from audit_emit._KNOWN_ACTIONS."""
    if not AUDIT_EMIT_PATH.is_file():
        raise FileNotFoundError(
            f"audit_emit.py not found at {AUDIT_EMIT_PATH}"
        )
    text = AUDIT_EMIT_PATH.read_text(encoding="utf-8")
    # Locate the _KNOWN_ACTIONS block boundaries.
    start_match = re.search(r"^_KNOWN_ACTIONS\s*=\s*\{", text, flags=re.MULTILINE)
    if not start_match:
        raise ValueError("_KNOWN_ACTIONS declaration not found")
    # Scan forward to the matching closing brace. Naive but enough for a
    # flat set literal; nested braces in comments would confuse, but the
    # audit_emit source doesn't use those.
    depth = 0
    body_start = start_match.end() - 1  # index of '{'
    body_end = -1
    for i in range(body_start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                body_end = i
                break
    if body_end < 0:
        raise ValueError("_KNOWN_ACTIONS block not closed")
    block = text[body_start + 1 : body_end]
    actions = _LITERAL_RE.findall(block)
    # De-dupe while preserving order.
    seen: Set[str] = set()
    ordered: List[str] = []
    for a in actions:
        if a not in seen:
            seen.add(a)
            ordered.append(a)
    return ordered


def classify(actions: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """Split actions into (compliant, grandfathered, violating)."""
    compliant: List[str] = []
    grandfathered: List[str] = []
    violating: List[str] = []
    for a in actions:
        if _CONVENTION_RE.match(a):
            compliant.append(a)
        elif a in _GRANDFATHERED:
            grandfathered.append(a)
        else:
            violating.append(a)
    return compliant, grandfathered, violating


def _print_violations(violating: List[str]) -> None:
    print("ADR-065 convention violations (non-grandfathered):")
    for a in violating:
        print(f"  - {a!r} does not match {_CONVENTION_RE.pattern}")
    print("")
    print(
        "To fix: rename the action to `<surface>_<verb>[_modifier]` OR "
        "add to ADR-065 allowlist via amendment."
    )


def _print_audit(
    compliant: List[str], grandfathered: List[str], violating: List[str]
) -> None:
    print(f"_KNOWN_ACTIONS audit (total: {len(compliant) + len(grandfathered) + len(violating)})")
    print("")
    print(f"Compliant ({len(compliant)}):")
    for a in compliant:
        print(f"  OK   {a}")
    if grandfathered:
        print("")
        print(f"Grandfathered ({len(grandfathered)}):")
        for a in grandfathered:
            print(f"  GRAND {a}")
    if violating:
        print("")
        print(f"Violating ({len(violating)}):")
        for a in violating:
            print(f"  VIOL {a}")


def main(argv: List[str] = None) -> int:
    """CLI entrypoint."""
    ap = argparse.ArgumentParser(
        description="ADR-065 audit-action naming-convention advisory linter.",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any non-grandfathered violation found.",
    )
    ap.add_argument(
        "--audit",
        action="store_true",
        help="Print all action names with compliance status; always exit 0.",
    )
    args = ap.parse_args(argv)

    try:
        actions = _read_actions()
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2

    compliant, grandfathered, violating = classify(actions)

    if args.audit:
        _print_audit(compliant, grandfathered, violating)
        return 0

    if violating:
        _print_violations(violating)
        print("")
        print(
            f"Summary: {len(compliant)} compliant, "
            f"{len(grandfathered)} grandfathered, "
            f"{len(violating)} violating."
        )
        return 1 if args.strict else 0

    print(
        f"OK: {len(compliant)} actions compliant with ADR-065 "
        f"({len(grandfathered)} grandfathered)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
