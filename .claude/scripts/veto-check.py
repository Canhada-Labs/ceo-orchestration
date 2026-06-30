#!/usr/bin/env python3
"""`/veto-check` backing script — machine-verifiable veto scan.

PLAN-010 Phase 5 (debate C11 ask). Runs a set of regex-based red-flag
patterns against a single file and emits a structured JSON report so
Claude (or CI) can assert outcomes instead of interpreting prose.

Patterns are grouped by domain (code-review / security) and drawn
from the `code-review-checklist` + `security-and-auth` skills. Ship
with a compact, high-signal set — easy to extend by appending to the
`_RULES` list below.

Usage:
    python3 .claude/scripts/veto-check.py --file path/to/code.ts
    python3 .claude/scripts/veto-check.py --file path/to/code.ts --format json

Exit codes:
    0 — scanned, no vetoes triggered
    1 — scanned, at least one veto triggered
    2 — usage error (missing/unreadable file)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Rule table
# ---------------------------------------------------------------------------
#
# Each rule:
#     id:       stable short identifier (string)
#     domain:   "code-review" | "security"
#     pattern:  compiled regex
#     message:  one-line human explanation
#
# To extend, append a new dict. Patterns run line-by-line; the first
# match per rule per line is reported (multiple distinct lines → multiple
# entries).

_RULES: List[Dict[str, Any]] = [
    # --- code-review checklist (financial-math / correctness) ---
    {
        "id": "CR-001-parseFloat",
        "domain": "code-review",
        "pattern": re.compile(r"\bparseFloat\s*\("),
        "message": "parseFloat on financial/untyped values — use a decimal lib or safe helper.",
    },
    {
        "id": "CR-002-number-cast",
        "domain": "code-review",
        "pattern": re.compile(r"\bNumber\s*\(\s*[A-Za-z_]"),
        "message": "Number(x) coercion can silently produce NaN; use typed parsing.",
    },
    {
        "id": "CR-003-ts-ignore",
        "domain": "code-review",
        "pattern": re.compile(r"@ts-ignore|@ts-nocheck"),
        "message": "TypeScript suppression directive — fix the type error instead.",
    },
    {
        "id": "CR-004-console-log",
        "domain": "code-review",
        "pattern": re.compile(r"\bconsole\.log\s*\("),
        "message": "console.log in committed code — use a structured logger.",
    },
    # --- security-and-auth ---
    {
        "id": "SEC-001-dangerously-set-html",
        "domain": "security",
        "pattern": re.compile(r"dangerouslySetInnerHTML"),
        "message": "dangerouslySetInnerHTML is an XSS sink; sanitize or avoid.",
    },
    {
        "id": "SEC-002-eval",
        "domain": "security",
        "pattern": re.compile(r"\beval\s*\("),
        "message": "eval() enables code injection; replace with safe parsing.",
    },
    {
        "id": "SEC-003-rm-rf",
        "domain": "security",
        "pattern": re.compile(r"\brm\s+-rf\b"),
        "message": "rm -rf in tracked code/scripts — require explicit review.",
    },
    {
        "id": "SEC-004-env-leak",
        "domain": "security",
        "pattern": re.compile(
            r"(?:AWS_SECRET_ACCESS_KEY|ANTHROPIC_API_KEY|OPENAI_API_KEY)\s*=\s*[\"']?[A-Za-z0-9_\-/+]{16,}"
        ),
        "message": "Hardcoded secret-looking env assignment — use a secrets manager.",
    },
    {
        "id": "SEC-005-shell-true",
        "domain": "security",
        "pattern": re.compile(r"shell\s*=\s*True"),
        "message": "subprocess(..., shell=True) invites injection; pass an argv list.",
    },
    {
        "id": "SEC-006-md5",
        "domain": "security",
        "pattern": re.compile(r"\b(?:md5|sha1)\s*\("),
        "message": "MD5/SHA1 are broken for security use; prefer SHA-256+.",
    },
]


def scan_text(text: str) -> List[Dict[str, Any]]:
    """Run every rule against each line. Return list of triggered hits."""
    hits: List[Dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule in _RULES:
            m = rule["pattern"].search(line)
            if m:
                hits.append(
                    {
                        "id": rule["id"],
                        "domain": rule["domain"],
                        "pattern": rule["pattern"].pattern,
                        "triggered": True,
                        "line": lineno,
                        "match": m.group(0),
                        "message": rule["message"],
                    }
                )
    return hits


def build_report(file_path: str, hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Group hits by domain into the documented envelope."""
    by_domain: Dict[str, List[Dict[str, Any]]] = {}
    for h in hits:
        by_domain.setdefault(h["domain"], []).append(
            {
                "id": h["id"],
                "pattern": h["pattern"],
                "triggered": h["triggered"],
                "line": h["line"],
                "match": h["match"],
                "message": h["message"],
            }
        )

    # Also include domains with zero hits so consumers see a closed set
    known_domains = sorted({r["domain"] for r in _RULES})
    vetoes = []
    for domain in known_domains:
        vetoes.append({"domain": domain, "rules": by_domain.get(domain, [])})

    return {
        "file": file_path,
        "triggered_count": len(hits),
        "vetoes": vetoes,
    }


def render_text(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# veto-check — {report['file']}")
    if report["triggered_count"] == 0:
        lines.append("no vetoes triggered")
        return "\n".join(lines) + "\n"
    lines.append(f"{report['triggered_count']} veto hit(s)")
    for block in report["vetoes"]:
        if not block["rules"]:
            continue
        lines.append(f"\n## {block['domain']}")
        for r in block["rules"]:
            lines.append(f"- [{r['id']}] line {r['line']}: {r['message']}")
            lines.append(f"    match: {r['match']!r}")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — scan a file for VETO-worthy code-review or security patterns."""
    parser = argparse.ArgumentParser(
        prog="veto-check",
        description="Scan a file for veto-worthy patterns (code-review + security).",
    )
    parser.add_argument("--file", required=True, help="path to file to scan")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="json",
        help="output format (default: json)",
    )
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.is_file():
        sys.stderr.write(f"error: file not found: {args.file}\n")
        return 2

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        sys.stderr.write(f"error: cannot read {args.file}: {exc}\n")
        return 2

    hits = scan_text(text)
    report = build_report(str(path), hits)

    if args.format == "json":
        sys.stdout.write(json.dumps(report, ensure_ascii=True, indent=2) + "\n")
    else:
        sys.stdout.write(render_text(report))

    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
