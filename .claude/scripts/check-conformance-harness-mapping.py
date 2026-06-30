#!/usr/bin/env python3
"""PLAN-013 Phase D.8 — Conformance harness mapping CI check.

Validates that every formally-proved property in
``docs/formal-verification/properties-proved.md`` §2 has:

1. A conformance test by the exact name claimed in the table
   (discoverable as a Python function/method in
   ``tests/formal_verification/test_breaker_conformance.py``).
2. A mutation-set under
   ``tests/formal_verification/mutation_fixtures/breaker/`` (renamed
   from ``mutations/`` in PLAN-019 Phase 1 P0-04) meeting the
   per-property minimum budget (S1:6, S2:5, S3:5, L1:5).
3. An impl-file reference in the table pointing at a file that actually
   exists (line-number range is taken as-is).

Stdlib-only per ADR-002. Python 3.9+.

Exit codes:
- 0 — all mappings clean.
- 1 — mapping drift detected (missing test, missing mutations, stale
  impl reference, malformed mapping).
- 2 — internal error (unparseable mapping table, missing files, IOError).

Usage:
    python3 .claude/scripts/check-conformance-harness-mapping.py
    python3 .claude/scripts/check-conformance-harness-mapping.py --json
    python3 .claude/scripts/check-conformance-harness-mapping.py \\
        --mapping-file path/to/properties-proved.md \\
        --tests-file path/to/test_breaker_conformance.py \\
        --mutations-dir path/to/mutation_fixtures/breaker/ \\
        --repo-root path/to/repo
    python3 .claude/scripts/check-conformance-harness-mapping.py --verbose
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Per ADR-044 §Decision-drivers + rationale.md §Mutation budget.
MIN_MUTATIONS: Dict[str, int] = {
    "S1": 6,
    "S2": 5,
    "S3": 5,
    "L1": 5,
}


# Markdown table cells can contain escaped pipes `\|`. We split on
# UNESCAPED pipes only: a pipe preceded by a backslash is literal.
# This regex matches the start-of-line pipe plus the six cells that
# form a property mapping row (id, TLA+ form, test ref, impl ref,
# log hash, mutation count). Escaped pipes inside cells are preserved.
_UNESCAPED_PIPE_SPLIT = re.compile(r"(?<!\\)\|")

# Property-id cell pattern (first cell). Tolerates bold markers.
_PROPERTY_ID_RE = re.compile(r"^\s*\**\s*(S[1-9]|L[1-9])\s*\**\s*$")

# Extracts `test_<method_name>` — we intentionally exclude file-basename
# matches like `test_breaker_conformance` (a module name) by preferring
# the token after `::` when the cell looks like a pytest node id
# (`path/file.py::test_x` or `path/file.py::Class::method`). Fallback:
# any `test_*` identifier token.
_PYTEST_NODE_RE = re.compile(
    r"""::\s*(?:[A-Za-z_][A-Za-z0-9_]*::)?(test_[a-zA-Z0-9_]+)"""
)
_FREE_TEST_NAME_RE = re.compile(r"\btest_[a-zA-Z0-9_]+\b")

# Extracts `path/to/file.py` (with optional backticks) from impl cell.
# Grabs ALL .py refs in the cell so complex refs with multiple helpers
# can be validated. Requires a leading `/` or directory component to
# avoid matching bare `file.py` as a top-level path. Bare filenames in
# follow-on references (e.g. "+ `audit_emit.py:977`") are skipped — the
# row is expected to carry at least one fully-qualified path.
_IMPL_PATH_RE = re.compile(r"`?([A-Za-z0-9_./-]+\.py)(?::(\d+)(?:-(\d+))?)?`?")

# Extracts a bold-or-plain integer count from mutation cell, tolerating
# surrounding markup.
_MUTATION_COUNT_RE = re.compile(r"(\d+)")


def _split_table_row(line: str) -> List[str]:
    """Split a markdown table row on UNESCAPED pipes.

    Strips the leading/trailing cell wrappers (the outer pipes produce
    empty cells on each end). Preserves escaped-pipe sequences inside
    cells by replacing them back to literal ``|`` AFTER splitting.
    """
    # Ignore blank / non-row lines up-front.
    if "|" not in line:
        return []
    parts = _UNESCAPED_PIPE_SPLIT.split(line)
    # Outer pipes produce empty leading/trailing cells.
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    # Collapse escape sequences.
    return [cell.replace("\\|", "|").strip() for cell in parts]


def _extract_test_names(test_cell: str) -> List[str]:
    """Return test-function names referenced in a mapping cell.

    Prefer pytest-node-id parsing (``file.py::TestCls::test_name``) so
    we do NOT pick up the file basename as a "test name". If no
    pytest-node form is present, fall back to any bare ``test_*`` token.
    """
    node_hits = _PYTEST_NODE_RE.findall(test_cell)
    if node_hits:
        return node_hits
    return _FREE_TEST_NAME_RE.findall(test_cell)


def parse_mapping(mapping_text: str) -> List[Dict[str, Any]]:
    """Parse §2 mapping table into a list of row-dicts.

    We walk each line independently; a row qualifies when:
      - it contains at least 6 UNESCAPED pipe-separated cells, AND
      - the first cell matches ``_PROPERTY_ID_RE`` (S1..S9 or L1..L9), AND
      - the property id is in MIN_MUTATIONS.
    """
    rows: List[Dict[str, Any]] = []
    for raw_line in mapping_text.splitlines():
        if "|" not in raw_line:
            continue
        cells = _split_table_row(raw_line)
        if len(cells) < 6:
            continue
        m = _PROPERTY_ID_RE.match(cells[0])
        if not m:
            continue
        property_id = m.group(1)
        if property_id not in MIN_MUTATIONS:
            continue
        # cells = [id, tla, test, impl, log_hash, mutations, ...]
        _tla_cell = cells[1]
        test_cell = cells[2]
        impl_cell = cells[3]
        _log_hash_cell = cells[4]
        mutation_cell = cells[5]

        test_names = _extract_test_names(test_cell)
        impl_refs: List[Tuple[str, Optional[int], Optional[int]]] = []
        for rm in _IMPL_PATH_RE.finditer(impl_cell):
            path = rm.group(1)
            start = int(rm.group(2)) if rm.group(2) else None
            end = int(rm.group(3)) if rm.group(3) else None
            impl_refs.append((path, start, end))

        count_m = _MUTATION_COUNT_RE.search(mutation_cell)
        mutation_count = int(count_m.group(1)) if count_m else 0

        rows.append(
            {
                "property": property_id,
                "test_cell": test_cell,
                "test_names": test_names,
                "impl_cell": impl_cell,
                "impl_refs": impl_refs,
                "mutation_cell": mutation_cell,
                "mutation_count": mutation_count,
            }
        )
    return rows


def discover_test_names(tests_file: Path) -> List[str]:
    """Return every ``test_*`` method name defined in the file via AST.

    We use AST (not regex) so we do not get false positives from
    docstrings / strings inside other methods.
    """
    try:
        source = tests_file.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"tests file not found: {tests_file}") from e
    tree = ast.parse(source, filename=str(tests_file))
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            names.append(node.name)
    return names


def count_mutations(mutations_dir: Path, property_id: str) -> int:
    """Count mutation files tagged with ``PROPERTY == property_id``.

    Reads the module source and extracts ``PROPERTY = "<id>"`` via AST.
    """
    if not mutations_dir.is_dir():
        return 0
    count = 0
    for py_file in mutations_dir.glob("mut_*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "PROPERTY"
                        and isinstance(node.value, ast.Constant)
                        and node.value.value == property_id
                    ):
                        count += 1
                        break
    return count


# Common search roots for "partial" paths like `_lib/audit_emit.py`
# that are documentation shorthand for files living deeper in the tree.
# Order matters: first match wins.
_IMPL_FALLBACK_ROOTS: Tuple[str, ...] = (
    ".claude/hooks",
    ".claude",
)


def _resolve_impl_path(path: str, repo_root: Path) -> Optional[Path]:
    """Try to locate an impl file under the repo root.

    Order:
      1. Literal resolution `<repo_root>/<path>`.
      2. Fallback under each entry in ``_IMPL_FALLBACK_ROOTS``.
    Returns the resolved Path on success, or None if no variant exists.
    """
    primary = (repo_root / path).resolve()
    try:
        primary.relative_to(repo_root.resolve())
        if primary.is_file():
            return primary
    except ValueError:
        return None
    # Try fallback roots for partial paths (`_lib/foo.py` etc.).
    for root in _IMPL_FALLBACK_ROOTS:
        candidate = (repo_root / root / path).resolve()
        try:
            candidate.relative_to(repo_root.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    return None


def check_impl_refs(
    impl_refs: List[Tuple[str, Optional[int], Optional[int]]],
    repo_root: Path,
) -> List[str]:
    """Return list of error strings for missing/stale impl references.

    Rules:
      - Any path with a directory separator (``/``) MUST resolve to an
        existing file under repo_root, either literally or via the
        fallback roots (see ``_IMPL_FALLBACK_ROOTS``). Path-escapes
        outside the root are rejected.
      - Bare filenames (no ``/``) are treated as shorthand for a
        previously-qualified path within the same cell and are
        skipped — they are documentation, not authoritative refs.
      - A row with ZERO qualified paths fails (caller enforces this
        separately; we only flag path-existence issues here).
    """
    errors: List[str] = []
    for path, _start, _end in impl_refs:
        if "/" not in path:
            # Bare filename shorthand — skip existence check.
            continue
        # Reject path-escape attempts up-front.
        primary = (repo_root / path).resolve()
        try:
            primary.relative_to(repo_root.resolve())
        except ValueError:
            errors.append(f"impl ref escapes repo_root: {path}")
            continue
        resolved = _resolve_impl_path(path, repo_root)
        if resolved is None:
            errors.append(f"impl ref points at missing file: {path}")
    return errors


def run_check(
    mapping_file: Path,
    tests_file: Path,
    mutations_dir: Path,
    repo_root: Path,
) -> Tuple[int, Dict[str, Any]]:
    """Run all checks. Return (exit_code, report_dict)."""
    report: Dict[str, Any] = {
        "ok": True,
        "errors": [],
        "rows": [],
        "mapping_file": str(mapping_file),
        "tests_file": str(tests_file),
        "mutations_dir": str(mutations_dir),
    }

    # Read mapping
    try:
        mapping_text = mapping_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        report["ok"] = False
        report["errors"].append(f"mapping file not found: {mapping_file}")
        return 2, report
    except OSError as e:
        report["ok"] = False
        report["errors"].append(f"mapping file read error: {e}")
        return 2, report

    rows = parse_mapping(mapping_text)
    if not rows:
        report["ok"] = False
        report["errors"].append("no property rows parsed from mapping file")
        return 2, report

    # Discover test names
    try:
        existing_tests = set(discover_test_names(tests_file))
    except FileNotFoundError as e:
        report["ok"] = False
        report["errors"].append(str(e))
        return 2, report
    except SyntaxError as e:
        report["ok"] = False
        report["errors"].append(f"tests file has syntax error: {e}")
        return 2, report

    # Per-row checks
    for row in rows:
        row_report: Dict[str, Any] = {
            "property": row["property"],
            "issues": [],
        }

        # 1. Test existence — only property-scoped tests (e.g. test_s1_*).
        # Ignore any `test_<module_basename>` token that may sneak in
        # via ``tests/.../test_breaker_conformance.py::test_foo`` parsing
        # when the node-id regex misses.
        property_scope_prefix = "test_" + row["property"].lower() + "_"
        scoped_tests = [
            tn for tn in row["test_names"] if tn.startswith(property_scope_prefix)
        ]
        if not scoped_tests:
            row_report["issues"].append(
                f"no {property_scope_prefix}* name found in mapping cell"
            )
        for tn in scoped_tests:
            if tn not in existing_tests:
                row_report["issues"].append(
                    f"mapped test `{tn}` not found in {tests_file.name}"
                )

        # 2. Mutation count
        expected_min = MIN_MUTATIONS.get(row["property"], 0)
        declared = row["mutation_count"]
        actual = count_mutations(mutations_dir, row["property"])
        row_report["declared_mutations"] = declared
        row_report["actual_mutations"] = actual
        row_report["min_mutations"] = expected_min
        if declared < expected_min:
            row_report["issues"].append(
                f"declared mutation count {declared} < min {expected_min} for {row['property']}"
            )
        if actual < expected_min:
            row_report["issues"].append(
                f"actual mutation files ({actual}) tagged {row['property']} < min {expected_min}"
            )
        if declared != actual:
            row_report["issues"].append(
                f"declared mutation count ({declared}) != actual count on disk ({actual})"
            )

        # 3. Impl refs
        impl_errors = check_impl_refs(row["impl_refs"], repo_root)
        row_report["issues"].extend(impl_errors)
        qualified_paths = [p for p, _s, _e in row["impl_refs"] if "/" in p]
        if not qualified_paths:
            row_report["issues"].append(
                "no qualified impl file:line reference found in mapping cell"
            )

        if row_report["issues"]:
            report["ok"] = False

        report["rows"].append(row_report)

    # Property-coverage check: every MIN_MUTATIONS key MUST appear in rows.
    seen_props = {r["property"] for r in rows}
    missing = set(MIN_MUTATIONS.keys()) - seen_props
    if missing:
        report["ok"] = False
        report["errors"].append(
            f"mapping file missing rows for properties: {sorted(missing)}"
        )

    return (0 if report["ok"] else 1), report


def _render_human(report: Dict[str, Any]) -> str:
    """Render a human-readable summary."""
    lines: List[str] = []
    if report["ok"]:
        lines.append("check-conformance-harness-mapping: OK")
    else:
        lines.append("check-conformance-harness-mapping: DRIFT DETECTED")
    if report["errors"]:
        lines.append("top-level errors:")
        for e in report["errors"]:
            lines.append(f"  - {e}")
    for row in report["rows"]:
        prop = row["property"]
        if not row["issues"]:
            lines.append(
                f"  [{prop}] OK "
                f"(declared={row['declared_mutations']}, "
                f"actual={row['actual_mutations']}, "
                f"min={row['min_mutations']})"
            )
            continue
        lines.append(f"  [{prop}] ISSUES:")
        for issue in row["issues"]:
            lines.append(f"    - {issue}")
    return "\n".join(lines)


def _default_paths(repo_root: Path) -> Dict[str, Path]:
    return {
        "mapping_file": repo_root / "docs" / "formal-verification" / "properties-proved.md",
        "tests_file": repo_root / "tests" / "formal_verification" / "test_breaker_conformance.py",
        "mutations_dir": repo_root / "tests" / "formal_verification" / "mutation_fixtures" / "breaker",
        "repo_root": repo_root,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — assert TLA+ conformance harness maps to live invariants."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--mapping-file", type=Path, default=None)
    parser.add_argument("--tests-file", type=Path, default=None)
    parser.add_argument("--mutations-dir", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    # Resolve repo root
    if args.repo_root:
        repo_root = args.repo_root.resolve()
    else:
        # Default: walk up from this script to find the repo (has `.claude/`).
        here = Path(__file__).resolve().parent
        for parent in [here, *here.parents]:
            if (parent / ".claude").is_dir() and (parent / "tests").is_dir():
                repo_root = parent
                break
        else:
            repo_root = Path.cwd()

    defaults = _default_paths(repo_root)
    mapping_file = (args.mapping_file or defaults["mapping_file"]).resolve()
    tests_file = (args.tests_file or defaults["tests_file"]).resolve()
    mutations_dir = (args.mutations_dir or defaults["mutations_dir"]).resolve()

    try:
        exit_code, report = run_check(
            mapping_file=mapping_file,
            tests_file=tests_file,
            mutations_dir=mutations_dir,
            repo_root=repo_root,
        )
    except Exception as exc:  # pragma: no cover — internal errors
        if args.as_json:
            sys.stdout.write(json.dumps({"ok": False, "internal_error": str(exc)}))
            sys.stdout.write("\n")
        else:
            sys.stderr.write(f"internal error: {exc}\n")
        return 2

    if args.as_json:
        sys.stdout.write(json.dumps(report, indent=2))
        sys.stdout.write("\n")
    elif args.verbose or exit_code != 0:
        sys.stdout.write(_render_human(report))
        sys.stdout.write("\n")
    else:
        sys.stdout.write("check-conformance-harness-mapping: OK\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
