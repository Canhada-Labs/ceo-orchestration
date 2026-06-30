#!/usr/bin/env python3
"""PLAN-013 Phase B.7 — Translations drift detector.

Verifies that each configured EN/PT document pair stays within bounded
structural drift. Enforces:
- Heading count equality (byte-identical `^#+` count).
- Code-fence count equality (byte-identical `` ``` `` count).
- Line-count delta ≤10% (translation expansion tolerance).
- Each file contains a top-level cross-link to its mirror.

Stdlib only per ADR-002 Python discipline. Exits 0 (clean) or 1 (drift).

Config: `.claude/scripts/translations-pairs.yaml` declares pairs as a
YAML-like list (parsed with stdlib — minimal subset, no external yaml
dep). A pair entry looks like:

    - source: docs/QUICKSTART.md
      mirror: docs/QUICKSTART.pt-BR.md

The script resolves paths relative to the repo root (determined by
finding `.git`).

Debate §C6 (PLAN-013): drift-checker MUST surface which file diverged
and which metric failed — not just "drift detected". Machine-readable
JSON on `--json` flag for CI integration.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

HEADING_RE = re.compile(r"^#+\s", re.MULTILINE)
CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)
LINE_DELTA_TOLERANCE = 0.10


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"no .git ancestor of {start}")


def _parse_pairs_yaml(path: Path) -> List[Tuple[str, str]]:
    """Minimal YAML subset parser: `- source: ...` + `  mirror: ...` only."""
    pairs: List[Tuple[str, str]] = []
    if not path.exists():
        return pairs
    source: Optional[str] = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("- source:"):
            source = line.split(":", 1)[1].strip()
        elif line.lstrip().startswith("mirror:") and source is not None:
            mirror = line.split(":", 1)[1].strip()
            pairs.append((source, mirror))
            source = None
    return pairs


def _count_matches(pattern: re.Pattern, text: str) -> int:
    return len(pattern.findall(text))


def _cross_link_present(text: str, mirror_basename: str) -> bool:
    """Check top 15 lines for a cross-link reference to the mirror."""
    head = "\n".join(text.splitlines()[:15])
    return mirror_basename in head


def check_pair(
    root: Path,
    source_rel: str,
    mirror_rel: str,
) -> Tuple[bool, List[str]]:
    """Return (ok, issues_list)."""
    source = root / source_rel
    mirror = root / mirror_rel
    issues: List[str] = []

    if not source.exists():
        issues.append(f"missing source: {source_rel}")
    if not mirror.exists():
        issues.append(f"missing mirror: {mirror_rel}")
    if issues:
        return False, issues

    src_text = source.read_text(encoding="utf-8")
    mir_text = mirror.read_text(encoding="utf-8")

    src_headings = _count_matches(HEADING_RE, src_text)
    mir_headings = _count_matches(HEADING_RE, mir_text)
    if src_headings != mir_headings:
        issues.append(
            f"heading count drift: source={src_headings} mirror={mir_headings}"
        )

    src_fences = _count_matches(CODE_FENCE_RE, src_text)
    mir_fences = _count_matches(CODE_FENCE_RE, mir_text)
    if src_fences != mir_fences:
        issues.append(
            f"code-fence count drift: source={src_fences} mirror={mir_fences}"
        )

    src_lines = src_text.count("\n")
    mir_lines = mir_text.count("\n")
    if src_lines > 0:
        delta = abs(mir_lines - src_lines) / src_lines
        if delta > LINE_DELTA_TOLERANCE:
            issues.append(
                f"line-count delta {delta:.1%} > {LINE_DELTA_TOLERANCE:.0%} "
                f"(source={src_lines} mirror={mir_lines})"
            )

    src_base = Path(source_rel).name
    mir_base = Path(mirror_rel).name
    if not _cross_link_present(mir_text, src_base):
        issues.append(f"mirror missing cross-link to source ({src_base})")
    if not _cross_link_present(src_text, mir_base):
        issues.append(f"source missing cross-link to mirror ({mir_base})")

    return (len(issues) == 0), issues


def main(argv: Optional[Iterable[str]] = None) -> int:
    """CLI entrypoint — assert PT-BR/EN doc pairs stay in sync."""
    parser = argparse.ArgumentParser(
        description="Check EN/PT translation pair drift."
    )
    parser.add_argument(
        "--pairs-file",
        default=".claude/scripts/translations-pairs.yaml",
        help="YAML file with pair list (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON report on stdout (for CI)",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Override repo root (default: detect via .git)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.repo_root:
        root = Path(args.repo_root).resolve()
    else:
        root = _find_repo_root(Path(__file__).parent)

    pairs = _parse_pairs_yaml(root / args.pairs_file)
    if not pairs:
        print(
            f"ERROR: no pairs found in {args.pairs_file}",
            file=sys.stderr,
        )
        return 2

    results = []
    any_drift = False
    for source, mirror in pairs:
        ok, issues = check_pair(root, source, mirror)
        results.append(
            {
                "source": source,
                "mirror": mirror,
                "ok": ok,
                "issues": issues,
            }
        )
        if not ok:
            any_drift = True

    if args.json:
        print(json.dumps({"results": results, "drift": any_drift}, indent=2))
    else:
        for r in results:
            status = "OK" if r["ok"] else "DRIFT"
            print(f"{status:6s} {r['source']} <-> {r['mirror']}")
            for issue in r["issues"]:
                print(f"       - {issue}")
        if any_drift:
            print("\nFAIL: translation drift detected", file=sys.stderr)

    return 1 if any_drift else 0


if __name__ == "__main__":
    sys.exit(main())
