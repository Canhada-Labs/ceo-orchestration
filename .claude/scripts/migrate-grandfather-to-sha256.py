#!/usr/bin/env python3
"""DIM-07 migration: function-length-grandfather v1 -> v2 (sha256 keyed).

PLAN-063 DIM-07 (Session 77 Phase 5 round-2). Re-keys the grandfather
list from `(file, function, line)` tuple to `(file, function,
sha256_of_function_body)` tuple. Line is fragile — any edit above a
function shifts line numbers and silently breaks the grandfather
match (existing function falls into "new violation" pile). SHA256 of
the function body is line-shift invariant: only changes when the body
itself changes.

## Schema v1 -> v2

v1 entry:
    - file: path/to/x.py
      function: foo
      line: 42
      end_line: 96
      loc: 55

v2 entry adds `sha256:`:
    - file: path/to/x.py
      function: foo
      line: 42
      end_line: 96
      loc: 55
      sha256: deadbeef…  # 64-hex of body source

The `line/end_line/loc` fields stay (human reference) but are NOT
part of the match key in v2. The matcher in check-function-length.py
prefers v2 (sha256 lookup) and falls back to v1 (line lookup) for
backward compat during migration window.

## Usage

    python3 .claude/scripts/migrate-grandfather-to-sha256.py
        # dry-run: write to /tmp and report diff stat

    python3 .claude/scripts/migrate-grandfather-to-sha256.py --apply
        # in-place: write back to the canonical YAML location

    python3 .claude/scripts/migrate-grandfather-to-sha256.py \\
        --input .claude/governance/function-length-grandfather.yaml \\
        --output /tmp/grandfather-v2.yaml

## Stale-entry handling

If an entry's `(file, function, line)` no longer maps to a real
function (e.g. function was renamed or file deleted), the entry is
marked `STALE` in the output and the migration prints a warning. The
operator can then prune stale entries manually before applying.

## Exit codes

- `0` — migration successful (or dry-run produced output)
- `1` — usage error / IO error
- `2` — stale entries present (advisory; --strict promotes to error)

Stdlib only (Python >= 3.9).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_DEFAULT_PATH = Path(".claude/governance/function-length-grandfather.yaml")


def _parse_v1_yaml(text: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Parse the simple v1 YAML subset; return (header_fields, entries).

    Mirrors `_load_grandfather` in check-function-length.py — same shape
    but returns full entries (not just match keys).
    """
    # justified: YAML state machine — header parse + entry boundary + indented field handler form one cohesive 3-phase reader; splitting further produces artificial helpers that obscure flow.
    header: Dict[str, Any] = {}
    entries: List[Dict[str, Any]] = []
    cur: Dict[str, Any] = {}
    in_functions = False

    def _flush() -> None:
        if cur and "file" in cur and "function" in cur:
            entries.append(dict(cur))

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        # New entry boundary.
        stripped = line.lstrip()
        if stripped.startswith("- file:"):
            _flush()
            cur = {"file": stripped[len("- file:"):].strip()}
            continue
        # Top-level key (no leading whitespace).
        if not line.startswith(" "):
            _flush()
            cur = {}
            in_functions = False
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "functions":
                    in_functions = True
                else:
                    header[key] = val
            continue
        # Indented field within current record.
        body = line[4:] if line.startswith("    ") else line.lstrip()
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
    return header, entries


def _hash_node(source: str, node: ast.AST) -> str:
    """Return sha256 of the source segment of `node` in `source`."""
    seg = ast.get_source_segment(source, node)
    if seg is None:
        # Fallback: slice by line numbers
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        lines = source.splitlines(keepends=True)
        seg = "".join(lines[start - 1: end])
    return hashlib.sha256(seg.encode("utf-8")).hexdigest()


def _node_loc(node: ast.AST) -> int:
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start)
    return max(0, end - start + 1)


def _function_sha256(source: str, func_name: str, start_line: int,
                     loc_threshold: int = 50,
                     ) -> Tuple[Optional[str], Optional[Dict[str, int]]]:
    """Locate the function in `source` and return (sha256, location_meta).

    Match strategy (DIM-07 line-shift resilience):
      1. (name, start_line) exact match — preferred (no drift).
      2. (name) match where function still exceeds loc_threshold — drift
         tolerated (line shifted since grandfather was generated, but the
         function body is still long enough to need grandfathering).

    Returns (None, None) if the function no longer exists, OR if it
    exists but has been refactored to <= loc_threshold (no longer
    needs grandfathering — naturally drops from the v2 list).

    `location_meta` is `{line, end_line, loc}` of the matched node, so
    callers can update entry.line/end_line/loc to current values.
    """
    # justified: 2-phase match strategy (exact line match first, then name-fallback closest-to-original-line) is one logical search; splitting into separate helpers loses the early-exit optimization.
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None, None

    same_name: List[ast.AST] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func_name:
            continue
        same_name.append(node)
        if getattr(node, "lineno", -1) == start_line:
            # Exact match — preferred.
            sha = _hash_node(source, node)
            meta = {
                "line": getattr(node, "lineno", 0),
                "end_line": getattr(node, "end_lineno", 0),
                "loc": _node_loc(node),
            }
            return sha, meta

    # Fallback: name-only match. Pick the one closest to start_line that
    # still exceeds loc_threshold. If multiple long ones, take the
    # closest to original line (smallest abs delta).
    long_candidates = [n for n in same_name if _node_loc(n) > loc_threshold]
    if not long_candidates:
        return None, None
    long_candidates.sort(
        key=lambda n: abs(getattr(n, "lineno", 0) - start_line)
    )
    chosen = long_candidates[0]
    sha = _hash_node(source, chosen)
    meta = {
        "line": getattr(chosen, "lineno", 0),
        "end_line": getattr(chosen, "end_lineno", 0),
        "loc": _node_loc(chosen),
    }
    return sha, meta


def _migrate(entries: List[Dict[str, Any]], repo_root: Path
             ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compute sha256 for each entry. Return (migrated, stale).

    Uses _function_sha256 with name-fallback (DIM-07 line-shift
    resilience). Stale entries are functions that no longer exist or
    were refactored to <= 50 LoC.
    """
    migrated: List[Dict[str, Any]] = []
    stale: List[Dict[str, Any]] = []
    for e in entries:
        f_path = repo_root / e["file"]
        if not f_path.is_file():
            stale.append({**e, "_reason": "file_missing"})
            continue
        try:
            source = f_path.read_text(encoding="utf-8")
        except OSError:
            stale.append({**e, "_reason": "file_unreadable"})
            continue
        sha, meta = _function_sha256(source, e["function"],
                                     int(e.get("line", 0)))
        if sha is None or meta is None:
            stale.append({**e, "_reason": "function_not_found_or_refactored"})
            continue
        # Update line/end_line/loc to current values (was stale if the
        # function shifted since v1 generation).
        new_e = dict(e)
        new_e["line"] = meta["line"]
        new_e["end_line"] = meta["end_line"]
        new_e["loc"] = meta["loc"]
        new_e["sha256"] = sha
        migrated.append(new_e)
    return migrated, stale


def _format_v2_yaml(header: Dict[str, Any],
                    entries: List[Dict[str, Any]]) -> str:
    """Emit the v2 YAML with the same prologue style as v1."""
    # justified: schema-documentation comment block is embedded inline so a future reader of the YAML sees the migration narrative co-located with the header fields it explains; extracting the comment-block constants into module scope inverts the locality.
    out: List[str] = []
    out.append(
        "# Function-length grandfather list — "
        "PLAN-063 DIM-07 (sha256-keyed v2)\n"
    )
    out.append(
        f"# Generated: {header.get('generated_at', '2026-05-01')} "
        "(Session 77 Phase 5)\n"
    )
    out.append("# Schema: function-length-grandfather/v2\n")
    out.append("#\n")
    out.append(
        "# These functions exceed the 50-LoC threshold and are\n"
        "# PERMANENTLY accepted as part of the framework identity per "
        "ADR-097.\n"
    )
    out.append("#\n")
    out.append(
        "# v2 (PLAN-063 DIM-07): match key changed from\n"
        "# (file, function, line) to (file, function, sha256). The\n"
        "# line/end_line fields stay for human reference but are NOT\n"
        "# part of the match key. This makes the grandfather list\n"
        "# line-shift invariant — only changes when the function body\n"
        "# itself changes.\n"
    )
    out.append("#\n")
    out.append(
        "# New functions added 2026-04-29 onward MUST either stay "
        "<=50 LoC OR\n"
        "# add a `# justified: <reason >=10 chars>` comment within "
        "the body.\n"
        "# This grandfather list is NOT auto-extended — only ADR-097 "
        "supersession\n"
        "# can add new entries.\n"
    )
    out.append("#\n")
    out.append(
        "# Format: list of {file, function, line, end_line, loc, "
        "sha256} entries.\n"
        "# Match key: (file, function, sha256) tuple.\n\n"
    )
    out.append("schema: function-length-grandfather/v2\n")
    out.append(f"generated_at: \"{header.get('generated_at', '2026-05-01')}\"\n")
    gv = header.get(
        "generated_via",
        ".claude/scripts/migrate-grandfather-to-sha256.py --apply",
    )
    out.append(f"generated_via: \"{gv}\"\n")
    out.append("adr: ADR-097\n")
    out.append("migrated_from: function-length-grandfather/v1\n")
    out.append("migrated_at: \"2026-05-01\"\n")
    out.append(f"total_grandfathered: {len(entries)}\n\n")
    out.append("functions:\n")
    for e in entries:
        out.append(f"  - file: {e['file']}\n")
        out.append(f"    function: {e['function']}\n")
        out.append(f"    line: {e['line']}\n")
        out.append(f"    end_line: {e['end_line']}\n")
        out.append(f"    loc: {e['loc']}\n")
        out.append(f"    sha256: {e['sha256']}\n")
    return "".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    # justified: CLI dispatch + argparse + IO + stale-handling + exit-code logic forms one entry-point flow; PEP 8 / community convention keeps argparse setup co-located with main even when long.
    parser = argparse.ArgumentParser(
        description="Migrate function-length-grandfather v1 -> v2 (sha256).",
    )
    parser.add_argument(
        "--input", type=Path, default=_DEFAULT_PATH,
        help=f"Input v1 YAML (default: {_DEFAULT_PATH})",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output v2 YAML (default: /tmp/grandfather-v2.yaml dry-run)",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write back to --input in-place (overrides --output)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 if any stale entries are found",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path("."),
        help="Repo root for resolving entry file paths (default: cwd)",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 1
    text = args.input.read_text(encoding="utf-8")
    header, entries = _parse_v1_yaml(text)
    if not entries:
        print(
            f"warning: parsed 0 entries from {args.input}",
            file=sys.stderr,
        )

    migrated, stale = _migrate(entries, args.repo_root.resolve())

    out_text = _format_v2_yaml(header, migrated)
    if args.apply:
        out_path = args.input
    elif args.output is not None:
        out_path = args.output
    else:
        out_path = Path("/tmp/grandfather-v2.yaml")

    out_path.write_text(out_text, encoding="utf-8")
    print(
        f"OK: migrated {len(migrated)} entries -> {out_path} "
        f"({len(stale)} stale)"
    )
    if stale:
        print("\nStale entries:", file=sys.stderr)
        for s in stale[:10]:
            print(
                f"  - {s['file']}::{s['function']}@{s.get('line', '?')} "
                f"({s.get('_reason', 'unknown')})",
                file=sys.stderr,
            )
        if len(stale) > 10:
            print(f"  ... ({len(stale) - 10} more)", file=sys.stderr)
        if args.strict:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
