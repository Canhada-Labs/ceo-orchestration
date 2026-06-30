#!/usr/bin/env python3
"""PLAN-051 Phase 4 B4 — Swarm conformance harness mapping CI check.

Validates that every formally-proved property in
``docs/formal-verification/properties-proved.md`` §9.1 (Swarm-
Coordinator Property Mapping) has:

1. A conformance test matching `test_<prop_id>_*` convention
   under ``tests/formal_verification/test_swarm_coordinator_conformance.py``.
2. A mutation-set under
   ``tests/formal_verification/mutation_fixtures/swarm_coordinator/``
   meeting the per-property minimum budget (I1-I4 + L1-L4 each ≥1
   currently; target 5 per PLAN-051 Phase 4 B3 follow-up).
3. An impl-file reference in §9.1 table pointing at a file that
   actually exists.

Companion to ``check-conformance-harness-mapping.py`` which covers
§2 (breaker). See PLAN-051 Round 1 debate consensus Cluster 2
(Phase 4 B4 — VP Eng P1 risk + QA).

Stdlib-only per ADR-002. Python 3.9+.

Exit codes:
- 0 — all §9.1 mappings clean.
- 1 — mapping drift detected (missing test, missing mutations, stale
  impl reference, malformed mapping).
- 2 — internal error.

Usage:
    python3 .claude/scripts/check-swarm-harness-mapping.py
    python3 .claude/scripts/check-swarm-harness-mapping.py --json
    python3 .claude/scripts/check-swarm-harness-mapping.py --verbose

Designed to run alongside the breaker mapper as a separate CI step
(Phase 4 B4 consensus — parallel mapper, not monolithic extension,
for maintainability).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# -----------------------------------------------------------------
# Configuration — swarm-coordinator §9.1 properties
# -----------------------------------------------------------------

# Per PLAN-050 Phase 7a §9 + PLAN-051 Phase 4 B3 — target 5 per
# property promoted to enforced floor Session 58 (commit 5f47cbd)
# after the mutation budget reached 40/40. Any regression below 5
# per property is a CI failure going forward; EXPECTED-KILLS.json is
# the companion CI manifest with per-mutation kill evidence.
MIN_MUTATIONS_CURRENT: Dict[str, int] = {
    "I1": 5,  # parallel_cap
    "I2": 5,  # iter_ceiling
    "I3": 5,  # tokens_per_iter
    "I4": 5,  # budget_envelope
    "L1": 5,  # no_dead_worker
    "L2": 5,  # progress_guaranteed
    "L3": 5,  # kill_halts
    "L4": 5,  # trip_precedes_propagate
}

# Target 5 per property (matches MIN_MUTATIONS_CURRENT); preserved
# as a separate constant so future raises to e.g. 7 per property
# can be tracked as an aspirational target while the enforcement
# floor is lifted in lockstep.
MIN_MUTATIONS_TARGET: Dict[str, int] = {k: 5 for k in MIN_MUTATIONS_CURRENT}

# Expected test function prefixes per property (matches the conformance
# harness test method naming — each property has at least one
# ``test_<id_lowercase>_*`` test).
PROPERTY_TEST_PREFIXES: Dict[str, List[str]] = {
    "I1": ["test_i1_"],
    "I2": ["test_i2_"],
    "I3": ["test_i3_"],
    "I4": ["test_i4_"],
    "L1": ["test_l1_"],
    "L2": ["test_l2_"],
    "L3": ["test_l3_"],
    "L4": ["test_l4_"],
}

# Markdown table row splitter (unescaped pipe).
_UNESCAPED_PIPE_SPLIT = re.compile(r"(?<!\\)\|")


def _split_table_row(line: str) -> List[str]:
    """Split markdown table row on unescaped pipes, strip empties."""
    parts = _UNESCAPED_PIPE_SPLIT.split(line)
    # Drop leading/trailing empty strings from the `|...|...|` pattern.
    return [p.strip() for p in parts if p.strip()]


def _parse_mapping_table(mapping_file: Path) -> List[Dict[str, str]]:
    """Extract §9.1 table rows as dicts keyed by column header.

    The expected header is:
      `| ID | Kind | TLA+ formula | Implementation anchor |`
    """
    rows: List[Dict[str, str]] = []
    in_section = False
    in_table = False
    header: List[str] = []
    text = mapping_file.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.rstrip()
        # Enter §9.1 section; leave on any section >= 9.2.
        if line.startswith("### 9.1"):
            in_section = True
            continue
        if in_section and (
            line.startswith("### 9.2")
            or line.startswith("## 10")
            or line.startswith("## 9.2")
        ):
            break
        if not in_section:
            continue
        if line.startswith("|"):
            cells = _split_table_row(line)
            if not cells:
                continue
            # Header detection: first line starting with `| ID | ...`.
            if not header and cells[0].lower() == "id":
                header = [c.lower() for c in cells]
                in_table = True
                continue
            # Separator `|----|----|...` — skip.
            if all(set(c) <= {"-", ":"} for c in cells):
                continue
            if in_table and len(cells) == len(header):
                row = dict(zip(header, cells))
                rows.append(row)
    return rows


def _normalize_property_id(raw_id: str) -> str:
    """Extract 'I1', 'L4', etc from cell text like '**I1**' or 'L4 (implicit)'."""
    # Strip bold, italics, parens, whitespace.
    cleaned = re.sub(r"[*_`]", "", raw_id)
    cleaned = re.sub(r"\(.*?\)", "", cleaned).strip()
    # Match the first I<digit> or L<digit>.
    m = re.match(r"^([IL]\d+)", cleaned)
    return m.group(1) if m else cleaned


def _extract_test_methods(tests_file: Path) -> List[str]:
    """Return names of `def test_*` methods found via AST."""
    if not tests_file.exists():
        return []
    try:
        tree = ast.parse(tests_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                names.append(node.name)
    return names


def _count_mutations(mutations_dir: Path) -> Dict[str, int]:
    """Count mutation files per PROPERTY tag.

    Convention: each fixture is a Python module with a module-level
    ``PROPERTY = "I1"`` (or similar) constant. We parse the constant
    via AST to avoid executing the module.
    """
    counts: Dict[str, int] = {}
    if not mutations_dir.is_dir():
        return counts
    for path in sorted(mutations_dir.glob("mut_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "PROPERTY"
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)
                    ):
                        prop = node.value.value
                        counts[prop] = counts.get(prop, 0) + 1
                        break
    return counts


def _check_impl_reference(cell: str, repo_root: Path) -> Optional[str]:
    """Extract file paths from impl cell; return first that doesn't exist."""
    # Paths look like `coordinator.py:38` or `.claude/scripts/swarm/coordinator.py`.
    path_pattern = re.compile(
        r"`([.\w/\-]+\.(?:py|tla|cfg))(?::\d+)?`"
    )
    for m in path_pattern.finditer(cell):
        raw = m.group(1)
        # Try both relative and prefixed paths.
        candidates = [
            repo_root / raw,
            repo_root / ".claude" / "scripts" / "swarm" / raw,
            repo_root / "docs" / "formal-verification" / raw,
        ]
        if not any(c.exists() for c in candidates):
            return raw
    return None


def check_mapping(
    repo_root: Path,
    mapping_file: Path,
    tests_file: Path,
    mutations_dir: Path,
    verbose: bool = False,
) -> Tuple[int, List[str], Dict[str, int]]:
    """Run all checks. Returns (exit_code, errors, mutation_counts)."""

    errors: List[str] = []
    info: List[str] = []

    if not mapping_file.exists():
        return 2, [f"mapping file not found: {mapping_file}"], {}
    if not tests_file.exists():
        return 2, [f"tests file not found: {tests_file}"], {}

    rows = _parse_mapping_table(mapping_file)
    if not rows:
        return 2, ["§9.1 table not found or empty in mapping file"], {}

    test_methods = _extract_test_methods(tests_file)
    mutation_counts = _count_mutations(mutations_dir)

    seen_props: set = set()
    for row in rows:
        raw_id = row.get("id", "")
        prop = _normalize_property_id(raw_id)
        if not prop:
            continue
        if prop not in MIN_MUTATIONS_CURRENT:
            continue  # skip non-mapped rows silently
        seen_props.add(prop)

        # 1. Test coverage — at least one matching test method.
        prefixes = PROPERTY_TEST_PREFIXES.get(prop, [])
        has_test = any(
            any(name.startswith(pref) for pref in prefixes)
            for name in test_methods
        )
        if not has_test:
            errors.append(
                f"property {prop}: no test method matching prefixes "
                f"{prefixes} found in {tests_file.name}"
            )
        elif verbose:
            info.append(f"  OK test coverage: {prop}")

        # 2. Mutation coverage — at least MIN_MUTATIONS_CURRENT[prop].
        actual = mutation_counts.get(prop, 0)
        expected_min = MIN_MUTATIONS_CURRENT[prop]
        target = MIN_MUTATIONS_TARGET[prop]
        if actual < expected_min:
            errors.append(
                f"property {prop}: {actual} mutations found, "
                f"minimum {expected_min} required"
            )
        elif actual < target:
            info.append(
                f"  INFO {prop}: {actual}/{target} mutations — "
                f"target 5 per Phase 4 B3"
            )
        elif verbose:
            info.append(
                f"  OK mutations: {prop} has {actual} (≥target {target})"
            )

        # 3. Impl reference existence.
        impl_cell = row.get("implementation anchor", "")
        missing_path = _check_impl_reference(impl_cell, repo_root)
        if missing_path:
            errors.append(
                f"property {prop}: impl reference `{missing_path}` does "
                f"not resolve under repo root"
            )

    # 4. Property coverage — every MIN_MUTATIONS_CURRENT key in table.
    missing_props = set(MIN_MUTATIONS_CURRENT.keys()) - seen_props
    if missing_props:
        errors.append(
            f"§9.1 table missing rows for: {sorted(missing_props)}"
        )

    # Emit INFO lines in verbose mode.
    if verbose:
        for line in info:
            print(line)

    return (1 if errors else 0, errors, mutation_counts)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate §9.1 swarm-coordinator harness mapping."
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path.cwd(),
    )
    parser.add_argument(
        "--mapping-file", type=Path, default=None,
    )
    parser.add_argument(
        "--tests-file", type=Path, default=None,
    )
    parser.add_argument(
        "--mutations-dir", type=Path, default=None,
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    defaults = {
        "mapping_file": repo_root / "docs" / "formal-verification" / "properties-proved.md",
        "tests_file": repo_root / "tests" / "formal_verification" / "test_swarm_coordinator_conformance.py",
        "mutations_dir": repo_root / "tests" / "formal_verification" / "mutation_fixtures" / "swarm_coordinator",
    }
    mapping_file = args.mapping_file or defaults["mapping_file"]
    tests_file = args.tests_file or defaults["tests_file"]
    mutations_dir = args.mutations_dir or defaults["mutations_dir"]

    exit_code, errors, mutation_counts = check_mapping(
        repo_root=repo_root,
        mapping_file=mapping_file,
        tests_file=tests_file,
        mutations_dir=mutations_dir,
        verbose=args.verbose,
    )

    if args.json:
        out = {
            "exit_code": exit_code,
            "errors": errors,
            "mutation_counts": mutation_counts,
            "min_current": MIN_MUTATIONS_CURRENT,
            "min_target": MIN_MUTATIONS_TARGET,
        }
        print(json.dumps(out, indent=2))
    else:
        if errors:
            print("FAIL swarm harness mapping check:", file=sys.stderr)
            for err in errors:
                print(f"  {err}", file=sys.stderr)
            print(f"\nMutation counts: {mutation_counts}")
            print(f"Target per property: {MIN_MUTATIONS_TARGET}")
        else:
            total = sum(mutation_counts.values())
            print(
                f"PASS swarm harness mapping: "
                f"{len(MIN_MUTATIONS_CURRENT)} properties mapped, "
                f"{total} mutations total"
            )
            if args.verbose:
                for prop, cnt in sorted(mutation_counts.items()):
                    target = MIN_MUTATIONS_TARGET.get(prop, 0)
                    print(f"  {prop}: {cnt}/{target}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
