#!/usr/bin/env python3
"""PLAN-084 Wave 0.7 — validate-findings (schema-check all wave YAML).

Stdlib-only JSON-Schema-equivalent validator. Hard-fails on any entry
missing required fields or violating enum constraints (closed-world per
CR-P1-4).

Per R2-iter-3 CODEX-P1 propagation — nested per-archetype subdirs:
- findings-A/<archetype>/{triage,deep,triage-partial-*,deep-partial-*}.yaml
- gap-B/B.*.yaml
- per-subsystem-C/C.*.yaml
- codex-verdicts-D/batch-*.yaml

Usage:
  python3 .claude/scripts/local/validate-findings.py \
    --schema .claude/plans/PLAN-084/finding-schema.json \
    --plan-dir .claude/plans/PLAN-084
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


def load_schema(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_yaml_findings(path: Path) -> List[Dict]:
    """Minimal YAML list-of-dicts parser. Each entry begins with `- ` or `- id:`."""
    entries: List[Dict] = []
    current: Dict = {}
    current_key: str = ""
    multiline_buf: List[str] = []
    in_multiline = False

    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.rstrip()
        if not s or s.lstrip().startswith("#"):
            continue
        if re.match(r"^\s*-\s+id:", s) or re.match(r"^\s*- id:", s):
            if current:
                if in_multiline and current_key:
                    current[current_key] = "\n".join(multiline_buf).rstrip()
                entries.append(current)
            current = {}
            in_multiline = False
            multiline_buf = []
            # parse `- id: VALUE`
            val = s.split("id:", 1)[1].strip().strip('"').strip("'")
            current["id"] = val
            current_key = "id"
        elif re.match(r"^\s+([a-z_]+):\s*\|\s*$", s):
            if in_multiline and current_key:
                current[current_key] = "\n".join(multiline_buf).rstrip()
            current_key = s.strip().rstrip(":").rstrip(" |")
            current_key = re.match(r"\s*([a-z_]+):", s).group(1) if re.match(r"\s*([a-z_]+):", s) else current_key
            multiline_buf = []
            in_multiline = True
        elif in_multiline and (s.startswith("      ") or s.startswith("    ")):
            multiline_buf.append(s.lstrip())
        elif re.match(r"^\s+([a-z_]+):\s+(.+)$", s):
            if in_multiline and current_key:
                current[current_key] = "\n".join(multiline_buf).rstrip()
                in_multiline = False
                multiline_buf = []
            m = re.match(r"^\s+([a-z_]+):\s+(.+)$", s)
            if m:
                key = m.group(1)
                val = m.group(2).strip().strip('"').strip("'")
                current[key] = val
                current_key = key
        elif in_multiline:
            multiline_buf.append(s.lstrip())

    if current:
        if in_multiline and current_key:
            current[current_key] = "\n".join(multiline_buf).rstrip()
        entries.append(current)

    return entries


def validate_entry(entry: Dict, schema: Dict, path: Path) -> List[str]:
    errors: List[str] = []
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    for field in required:
        if field not in entry:
            errors.append(f"{path}: entry id={entry.get('id', '?')} missing required field '{field}'")

    for field, value in entry.items():
        prop = properties.get(field, {})
        # enum check
        if "enum" in prop:
            enum_values = prop["enum"]
            if value not in enum_values and not (value is None and None in enum_values):
                errors.append(f"{path}: entry id={entry.get('id', '?')} field '{field}'='{value}' not in enum {enum_values}")
        # pattern check
        if "pattern" in prop and isinstance(value, str):
            if not re.match(prop["pattern"], value):
                errors.append(f"{path}: entry id={entry.get('id', '?')} field '{field}'='{value}' does not match pattern {prop['pattern']}")
        # minLength
        if "minLength" in prop and isinstance(value, str):
            if len(value) < prop["minLength"]:
                errors.append(f"{path}: entry id={entry.get('id', '?')} field '{field}' length={len(value)} < min {prop['minLength']}")
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--schema", type=Path, default=Path(".claude/plans/PLAN-084/finding-schema.json"))
    p.add_argument("--plan-dir", type=Path, default=Path(".claude/plans/PLAN-084"))
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.schema.exists():
        print(f"schema not found: {args.schema}", file=sys.stderr)
        return 3

    schema = load_schema(args.schema)

    all_files: List[Path] = []
    for sub in ("findings-A", "gap-B", "per-subsystem-C", "codex-verdicts-D"):
        d = args.plan_dir / sub
        if d.exists():
            all_files.extend(d.rglob("*.yaml"))

    all_errors: List[str] = []
    total_entries = 0
    file_count = 0
    for f in all_files:
        file_count += 1
        try:
            entries = parse_yaml_findings(f)
        except Exception as e:
            all_errors.append(f"{f}: parse error: {e}")
            continue
        for entry in entries:
            total_entries += 1
            errors = validate_entry(entry, schema, f)
            all_errors.extend(errors)

    result = {
        "files_validated": file_count,
        "entries_validated": total_entries,
        "errors_count": len(all_errors),
        "errors": all_errors[:50],
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"files: {file_count}, entries: {total_entries}, errors: {len(all_errors)}")
        for e in all_errors[:20]:
            print(f"  {e}")

    return 0 if len(all_errors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
