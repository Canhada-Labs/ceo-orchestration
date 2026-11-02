#!/usr/bin/env python3
"""List subprocess-test debt and reject sites absent from the checked-in ratchet."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _subprocess_census import KINDS, load_baseline, new_findings, scan_tree


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--baseline", type=Path, default=Path(__file__).with_name("subprocess-test-baseline.json"))
    parser.add_argument("--kind", choices=(*KINDS, "all"), default="all")
    parser.add_argument("--list", action="store_true", help="emit all current findings as JSON")
    args = parser.parse_args(argv)
    try:
        findings = [f for f in scan_tree(args.root) if args.kind in ("all", f.kind)]
        additions = new_findings(findings, load_baseline(args.baseline))
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        print(f"subprocess census: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.list:
        print(json.dumps([f._asdict() for f in findings], indent=2))
    for finding in additions:
        print(f"NEW {finding.kind} {finding.path}:{finding.line} {finding.scope}", file=sys.stderr)
    if not args.list:
        print(f"subprocess census: {len(findings)} existing sites; {len(additions)} new sites")
    return 1 if additions else 0


if __name__ == "__main__":
    raise SystemExit(main())
