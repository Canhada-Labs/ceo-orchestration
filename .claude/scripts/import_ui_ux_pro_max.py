#!/usr/bin/env python3
"""Re-import upstream ui-ux-pro-max-skill reference CSVs as YAML.

PLAN-035 Wave B. Stdlib-only. Deterministic: byte-identical output on
unchanged inputs (use `git diff` to sanity-check).

Usage:
    python3 .claude/scripts/import_ui_ux_pro_max.py        # fetch + regenerate
    python3 .claude/scripts/import_ui_ux_pro_max.py --offline <src-dir>
        # regenerate from a pre-fetched directory of CSVs (e.g. `/tmp/foo/`)

Upstream: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill (MIT).
License attribution: .claude/skills/frontend/NOTICE.md.
"""
from __future__ import annotations

import csv
import os
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

UPSTREAM_BASE = (
    "https://raw.githubusercontent.com/nextlevelbuilder/"
    "ui-ux-pro-max-skill/main/src/ui-ux-pro-max/data/"
)

# (upstream csv basename, output yaml relative to .claude/skills/frontend/)
IMPORTS: Tuple[Tuple[str, str], ...] = (
    ("colors.csv", "design-system-and-components/reference/palettes.yaml"),
    ("typography.csv", "design-system-and-components/reference/fonts.yaml"),
    ("charts.csv", "accessibility-and-wcag/reference/charts-accessibility.yaml"),
    ("ux-guidelines.csv", "ux-and-user-journeys/reference/guidelines.yaml"),
)


def _escape_yaml_str(s: str) -> str:
    if s == "":
        return '""'
    if "\n" in s:
        lines = s.split("\n")
        return "|-\n" + "\n".join("    " + ln for ln in lines)
    out = s.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "")
    return f'"{out}"'


def _emit_entry(entry: Dict[Optional[str], object]) -> List[str]:
    lines: List[str] = []
    first = True
    extras: List[str] = []
    for key, val in entry.items():
        if key is None:
            if isinstance(val, list):
                extras.extend(str(x) for x in val if x is not None)
            elif val is not None:
                extras.append(str(val))
            continue
        if val is None:
            val = ""
        prefix = "- " if first else "  "
        first = False
        key_safe = str(key).strip().replace('"', "'")
        lines.append(
            f"{prefix}{_escape_yaml_str(key_safe)}: "
            f"{_escape_yaml_str(str(val).strip())}"
        )
    if extras:
        joined = " | ".join(extras)
        lines.append(f"  _extra_fields: {_escape_yaml_str(joined)}")
    return lines


def convert(csv_path: Path, yaml_path: Path, source_relpath: str) -> int:
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    out = [
        "# AUTO-GENERATED from upstream CSV (PLAN-035).",
        f"# Source: github.com/nextlevelbuilder/ui-ux-pro-max-skill ({source_relpath})",
        "# License: MIT © 2024 Next Level Builder. See .claude/skills/frontend/NOTICE.md.",
        "# Do not hand-edit — regenerate via .claude/scripts/import_ui_ux_pro_max.py",
        "",
        f"count: {len(rows)}",
        "entries:",
    ]
    for row in rows:
        out.extend(_emit_entry(row))
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(rows)


def _fetch(url: str, dst: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ceo-orchestration/plan-035"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        dst.write_bytes(resp.read())


def main(argv: List[str]) -> int:
    """CLI entrypoint — import ui-ux-pro-max reference data packs."""
    repo_root = Path(__file__).resolve().parents[2]
    frontend_root = repo_root / ".claude" / "skills" / "frontend"

    offline_dir: Optional[Path] = None
    if len(argv) > 1:
        if argv[1] == "--offline" and len(argv) > 2:
            offline_dir = Path(argv[2]).resolve()
        else:
            print(__doc__, file=sys.stderr)
            return 2

    if offline_dir is not None:
        print(f"Using offline source: {offline_dir}")
        src_dir = offline_dir
    else:
        import tempfile
        tmp = tempfile.mkdtemp(prefix="plan035-")
        src_dir = Path(tmp)
        for csv_name, _ in IMPORTS:
            url = UPSTREAM_BASE + csv_name
            print(f"Fetching {url}")
            _fetch(url, src_dir / csv_name)

    total = 0
    for csv_name, yaml_rel in IMPORTS:
        in_csv = src_dir / csv_name
        out_yaml = frontend_root / yaml_rel
        n = convert(in_csv, out_yaml, f"src/ui-ux-pro-max/data/{csv_name}")
        total += n
        print(f"  wrote {yaml_rel} ({n} entries)")
    print(f"OK: {total} total entries across {len(IMPORTS)} YAML files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
