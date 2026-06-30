#!/usr/bin/env python3
"""`/pitfall` backing script — list pitfalls from catalogs.

PLAN-010 Phase 5. Parses `.claude/pitfalls-catalog.yaml` (universal)
and optionally `.claude/skills/domains/<domain>/pitfalls.yaml` and
prints them in text or JSON.

Stdlib only (YAML parsed with a minimal purpose-built parser that
handles the catalog format). Falls back gracefully on unknown domains.

Usage:
    python3 .claude/scripts/pitfall-query.py
    python3 .claude/scripts/pitfall-query.py --domain fintech
    python3 .claude/scripts/pitfall-query.py --format json

Exit codes:
    0 — success
    2 — usage error / unknown domain
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIVERSAL_CATALOG = REPO_ROOT / ".claude" / "pitfalls-catalog.yaml"
DOMAINS_DIR = REPO_ROOT / ".claude" / "skills" / "domains"


def _strip_comment(line: str) -> str:
    """Remove trailing comments that are NOT inside double-quoted strings."""
    out: List[str] = []
    in_quote = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            in_quote = not in_quote
            out.append(ch)
        elif ch == "#" and not in_quote:
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        inner = value[1:-1]
        # Minimal escape handling: \" and \\
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return value


def _parse_agents(value: str) -> List[str]:
    """Parse a YAML flow-style list like `[A, B, C]`."""
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_unquote(part).strip() for part in inner.split(",") if part.strip()]


def parse_pitfalls_yaml(path: Path) -> List[Dict[str, Any]]:
    """Parse a pitfalls YAML file into a list of dicts.

    Expected item structure:
        - id: FOO-001
          rule: "..."
          whenToUse: "..."
          agents: [A, B]

    The parser is deliberately small: stdlib only and tailored to this
    specific schema. It tolerates blank lines, inline `#` comments,
    and arbitrary leading whitespace.
    """
    if not path.is_file():
        return []
    pitfalls: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    inside_pitfalls_block = False

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = _strip_comment(raw.rstrip("\n"))
            if not line.strip():
                continue

            stripped = line.strip()

            # Top-level "pitfalls:" marker
            if re.match(r"^pitfalls\s*:\s*$", stripped):
                inside_pitfalls_block = True
                continue

            if not inside_pitfalls_block:
                continue

            # New list item
            m = re.match(r"^(\s*)- +id\s*:\s*(.+)$", line)
            if m:
                if current is not None:
                    pitfalls.append(current)
                current = {"id": _unquote(m.group(2))}
                continue

            # Field within the current item
            m = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
            if m and current is not None:
                key = m.group(1)
                value = m.group(2)
                if key == "agents":
                    current[key] = _parse_agents(value)
                else:
                    current[key] = _unquote(value)

    if current is not None:
        pitfalls.append(current)
    return pitfalls


def list_available_domains() -> List[str]:
    if not DOMAINS_DIR.is_dir():
        return []
    names = []
    for entry in sorted(DOMAINS_DIR.iterdir()):
        if entry.is_dir() and (entry / "pitfalls.yaml").is_file():
            names.append(entry.name)
    return names


def collect(domain: Optional[str] = None) -> Dict[str, Any]:
    universal = parse_pitfalls_yaml(UNIVERSAL_CATALOG)
    result: Dict[str, Any] = {
        "universal": universal,
        "domain": None,
        "domain_pitfalls": [],
    }
    if domain:
        domain_path = DOMAINS_DIR / domain / "pitfalls.yaml"
        if not domain_path.is_file():
            raise FileNotFoundError(domain)
        result["domain"] = domain
        result["domain_pitfalls"] = parse_pitfalls_yaml(domain_path)
    return result


def render_text(data: Dict[str, Any]) -> str:
    """Render pitfall query results as plain text."""
    lines: List[str] = []
    universal = data.get("universal") or []
    lines.append(f"# Universal pitfalls ({len(universal)})")
    for p in universal:
        lines.append(f"- [{p.get('id','?')}] {p.get('rule','')}")
        when = p.get("whenToUse")
        if when:
            lines.append(f"    whenToUse: {when}")
        agents = p.get("agents") or []
        if agents:
            lines.append(f"    agents: {', '.join(agents)}")
    if data.get("domain"):
        dp = data.get("domain_pitfalls") or []
        lines.append("")
        lines.append(f"# Domain pitfalls — {data['domain']} ({len(dp)})")
        for p in dp:
            lines.append(f"- [{p.get('id','?')}] {p.get('rule','')}")
            when = p.get("whenToUse")
            if when:
                lines.append(f"    whenToUse: {when}")
            agents = p.get("agents") or []
            if agents:
                lines.append(f"    agents: {', '.join(agents)}")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — list pitfalls from the universal + optional domain catalog."""
    parser = argparse.ArgumentParser(
        prog="pitfall-query",
        description="List pitfalls from universal catalog + optional domain.",
    )
    parser.add_argument("--domain", default=None, help="domain name (e.g. fintech)")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format",
    )
    args = parser.parse_args(argv)

    try:
        data = collect(args.domain)
    except FileNotFoundError:
        available = list_available_domains()
        sys.stderr.write(
            f"error: unknown domain '{args.domain}'. "
            f"Available: {', '.join(available) if available else '(none)'}\n"
        )
        return 2

    if args.format == "json":
        sys.stdout.write(json.dumps(data, ensure_ascii=True, indent=2) + "\n")
    else:
        sys.stdout.write(render_text(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
