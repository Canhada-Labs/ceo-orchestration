#!/usr/bin/env python3
"""Function-length detector — PLAN-044 audit-v2 R4 P1 batch (item #11/#12).

Walks all `.py` files under `.claude/` (or a custom root) and reports
functions that exceed the configured line count without a
`# justified: <reason>` comment within the function body.

## Rationale

`docs/CTO-GUIDE.md` + the framework's own code review checklist
recommend functions ≤50 LoC as a default with explicit
`# justified:` comments for exceptions. The audit-v2 finding C-D-09
"301 functions over 50 LoC, none with `# justified:` comment"
documented the gap. This script makes the rule mechanical.

## Modes

- **Default (advisory):** prints findings, exits 0. Used as a
  reporting step in CI to track trend.
- **`--strict`:** prints findings, exits 1 if ANY un-justified
  function exceeds the threshold. Used as a quality gate after
  the existing 301 are justified or refactored (project decision).

## Justification syntax

A function is exempt from the threshold check if its body contains
a comment line matching:

    # justified: <free-text reason>

The reason should be ≥10 characters (no `# justified:` empty).
Multiple `# justified:` lines are allowed; the first non-empty
match wins.

## Usage

    python3 .claude/scripts/check-function-length.py
    python3 .claude/scripts/check-function-length.py --threshold 75
    python3 .claude/scripts/check-function-length.py --strict
    python3 .claude/scripts/check-function-length.py --json
    python3 .claude/scripts/check-function-length.py --root .claude/scripts

## Exit codes

- `0` — advisory mode OR strict mode with no violations
- `1` — strict mode with violations
- `2` — usage error (bad args, root not a directory)

Stdlib only (Python ≥3.9).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_DEFAULT_THRESHOLD = 50
_JUSTIFIED_PREFIX = "# justified:"
_JUSTIFIED_MIN_REASON = 10
_DEFAULT_GRANDFATHER_PATH = Path(
    ".claude/governance/function-length-grandfather.yaml"
)


def _load_grandfather(path: Path) -> Tuple[set, set]:
    """Parse the grandfather.yaml and return (v1_keys, v2_keys).

    PLAN-063 DIM-07: schema v1 keys by `(file, function, line)` tuple
    (fragile — line shifts break the match). Schema v2 keys by
    `(file, function, sha256)` tuple (line-shift invariant).

    Returns:
      (v1_keys, v2_keys) — both sets are populated for forward+backward
      compat. The matcher prefers v2 lookup; v1 lookup is a fallback so
      a v1-format file still works during the migration window.

    Stdlib-only YAML subset reader: looks for the simple list-of-mappings
    shape we generate. Returns (empty, empty) on any error (fail-open
    per advisory contract).
    """
    empty: Tuple[set, set] = (set(), set())
    if not path.is_file():
        return empty
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return empty

    v1_keys: set = set()
    v2_keys: set = set()
    cur: Dict[str, Any] = {}

    def _flush() -> None:
        if not cur or "file" not in cur or "function" not in cur:
            return
        # v1 key: requires line.
        if "line" in cur:
            v1_keys.add((str(cur["file"]), str(cur["function"]),
                         int(cur["line"])))
        # v2 key: requires sha256.
        if "sha256" in cur:
            v2_keys.add((str(cur["file"]), str(cur["function"]),
                         str(cur["sha256"])))

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        # New entry boundary: "  - file: ..." marks the start of a record.
        stripped = line.lstrip()
        if stripped.startswith("- file:"):
            _flush()
            cur = {"file": stripped[len("- file:"):].strip()}
            continue
        if not line.startswith("    "):
            # Top-level field (schema/total_*) — flush if we had a record.
            _flush()
            cur = {}
            continue
        # Indented field within current record.
        body = line[4:]
        if ":" not in body:
            continue
        key, _, val = body.partition(":")
        key = key.strip()
        val = val.strip()
        if key in ("function", "file", "sha256"):
            cur[key] = val
        elif key in ("line", "end_line", "loc"):
            try:
                cur[key] = int(val)
            except ValueError:
                pass

    _flush()
    return v1_keys, v2_keys


def _function_body_sha256(source: str, node: ast.AST) -> str:
    """Return sha256 of the function source segment.

    Mirrors `_hash_node` in migrate-grandfather-to-sha256.py — same
    extraction strategy so the migrate tool and the matcher produce
    bit-identical hashes for the same function.
    """
    seg = ast.get_source_segment(source, node)
    if seg is None:
        # Fallback: slice by line numbers.
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        lines = source.splitlines(keepends=True)
        seg = "".join(lines[start - 1: end])
    return hashlib.sha256(seg.encode("utf-8")).hexdigest()


_DEFAULT_EXCLUDES = frozenset({
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    ".egg-info",
})

# Path-fragment excludes: skip any file whose path contains one of these.
# Stage areas are not production code and shouldn't gate CI.
_DEFAULT_PATH_FRAGMENT_EXCLUDES = (
    "/staged-code/",
    "/staged-wave-",
    "/staged-spectest/",
    "/staged-spec/",
    "/audit-v2/staged-",
)


def _walk_python_files(root: Path,
                       extra_excludes: Optional[List[str]] = None) -> List[Path]:
    """Yield all `.py` files under root, sorted, skipping cache + staged dirs.

    `extra_excludes` is a list of path fragments; any file whose
    posix-style path contains one is skipped (in addition to the
    DEFAULT_EXCLUDES dirname set + DEFAULT_PATH_FRAGMENT_EXCLUDES).
    """
    if not root.is_dir():
        return []
    files: List[Path] = []
    extras = tuple(extra_excludes or [])
    for p in root.rglob("*.py"):
        try:
            if any(part.startswith(tuple(_DEFAULT_EXCLUDES))
                   for part in p.parts):
                continue
            posix = p.as_posix()
            if any(frag in posix for frag in _DEFAULT_PATH_FRAGMENT_EXCLUDES):
                continue
            if extras and any(frag in posix for frag in extras):
                continue
            if p.is_file():
                files.append(p)
        except OSError:
            continue
    files.sort()
    return files


def _has_justification(source_lines: List[str], start: int, end: int) -> bool:
    """Return True if any line in [start, end] (1-indexed inclusive) has
    a `# justified: <≥10-char reason>` comment.
    """
    if start < 1 or end > len(source_lines):
        return False
    for i in range(start - 1, end):  # 0-indexed slice
        line = source_lines[i].strip()
        if line.startswith(_JUSTIFIED_PREFIX):
            reason = line[len(_JUSTIFIED_PREFIX):].strip()
            if len(reason) >= _JUSTIFIED_MIN_REASON:
                return True
    return False


def _function_loc(node: ast.FunctionDef) -> int:
    """Return the number of source lines from def to last body line.

    Uses ast.end_lineno (Python 3.8+). Includes the def line and the
    closing line of the body. Comments + blank lines INSIDE the
    function count toward the LoC (matches typical PR review
    practice).
    """
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start)
    return max(0, end - start + 1)


def _scan_file(path: Path) -> List[Dict[str, Any]]:
    """Parse a Python file and yield function records.

    Each record: {file, function, line, end_line, loc, sha256, justified}.
    Files that fail to parse are skipped silently (advisory tool).

    The `sha256` field (PLAN-063 DIM-07) is the line-shift-invariant
    match key against grandfather schema v2.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    source_lines = source.splitlines()
    records: List[Dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            loc = _function_loc(node)
            start = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", start)
            justified = _has_justification(source_lines, start, end)
            sha256 = _function_body_sha256(source, node)
            records.append({
                "file": str(path),
                "function": node.name,
                "line": start,
                "end_line": end,
                "loc": loc,
                "sha256": sha256,
                "justified": justified,
            })
    return records


def _filter_violations(
    records: List[Dict[str, Any]],
    threshold: int,
    grandfather_v1: Optional[set] = None,
    grandfather_v2: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """Return records that violate the threshold without justification.

    PLAN-063 DIM-07: a record is exempt if EITHER grandfather match hits:
      - v2: `(file, function, sha256)` (preferred — line-shift invariant)
      - v1: `(file, function, line)` (fallback for un-migrated files)

    `grandfather_v1` and `grandfather_v2` are populated by
    `_load_grandfather()` from the same YAML file. v2 lookup is tried
    first; v1 is the fallback so the matcher works during the
    migration window (PLAN-044 P1 #11 closure / ADR-097 + DIM-07).
    """
    gf_v1 = grandfather_v1 or set()
    gf_v2 = grandfather_v2 or set()
    out: List[Dict[str, Any]] = []
    for r in records:
        if r["loc"] <= threshold:
            continue
        if r["justified"]:
            continue
        # Prefer v2 (sha256 — line-shift invariant).
        if gf_v2:
            v2_key = (str(r["file"]), str(r["function"]),
                      str(r.get("sha256", "")))
            if v2_key in gf_v2:
                continue
        # Fallback v1 (line — fragile, used during migration window).
        if gf_v1:
            v1_key = (str(r["file"]), str(r["function"]),
                      int(r["line"]))
            if v1_key in gf_v1:
                continue
        out.append(r)
    return out


def _format_text(violations: List[Dict[str, Any]],
                 threshold: int,
                 total_funcs: int,
                 limit: int) -> str:
    if not violations:
        return (
            f"OK: function-length check — {total_funcs} functions scanned, "
            f"0 over {threshold} LoC without justification.\n"
        )
    out: List[str] = []
    out.append(
        f"WARN: function-length check — {len(violations)} of {total_funcs} "
        f"functions over {threshold} LoC without `# justified:` comment.\n"
    )
    sorted_v = sorted(violations, key=lambda r: -r["loc"])
    out.append(f"\n  Top {min(limit, len(sorted_v))} (by LoC):\n")
    for r in sorted_v[:limit]:
        out.append(
            f"    {r['file']}:{r['line']}  "
            f"{r['function']!s:50s}  {r['loc']:4d} LoC\n"
        )
    if len(sorted_v) > limit:
        out.append(f"    ... ({len(sorted_v) - limit} more not shown)\n")
    out.append(
        "\n  Add `# justified: <reason ≥10 chars>` inside the function body\n"
        "  to declare an exception. Re-run to confirm.\n"
    )
    return "".join(out)


def _format_json(violations: List[Dict[str, Any]],
                 threshold: int,
                 total_funcs: int) -> str:
    payload = {
        "threshold": threshold,
        "total_functions": total_funcs,
        "violations": len(violations),
        "items": violations,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Function-length detector for `.py` files.",
    )
    parser.add_argument(
        "--root", type=Path, default=Path(".claude"),
        help="Root directory to scan (default: .claude/)",
    )
    parser.add_argument(
        "--threshold", type=int, default=_DEFAULT_THRESHOLD,
        help=f"LoC threshold (default: {_DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 if any violations found (default: advisory, exit 0)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON instead of text",
    )
    parser.add_argument(
        "--limit", type=int, default=10,
        help="Max violations to display in text mode (default: 10)",
    )
    parser.add_argument(
        "--exclude", action="append", default=None,
        metavar="FRAGMENT",
        help="Path fragment to exclude (repeatable; in addition to defaults)",
    )
    parser.add_argument(
        "--grandfather", type=Path, default=_DEFAULT_GRANDFATHER_PATH,
        help=("Grandfather list YAML (default: "
              ".claude/governance/function-length-grandfather.yaml). "
              "Pass /dev/null to disable."),
    )
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"ERROR: root '{args.root}' is not a directory", file=sys.stderr)
        return 2

    files = _walk_python_files(args.root, extra_excludes=args.exclude)
    all_records: List[Dict[str, Any]] = []
    for f in files:
        all_records.extend(_scan_file(f))

    grandfather_v1, grandfather_v2 = _load_grandfather(args.grandfather)
    violations = _filter_violations(
        all_records, args.threshold,
        grandfather_v1=grandfather_v1,
        grandfather_v2=grandfather_v2,
    )

    if args.json:
        print(_format_json(violations, args.threshold, len(all_records)),
              end="")
    else:
        print(_format_text(violations, args.threshold, len(all_records),
                           args.limit), end="")

    if args.strict and violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
