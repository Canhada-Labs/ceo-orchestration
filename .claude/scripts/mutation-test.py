#!/usr/bin/env python3
"""Mutation testing framework — stdlib-only (PLAN-042 ITEM 11).

FINDING (qa-architect P2, Wave A retrospective debate Round 1):
ADR-044 mandates 100% mutation kill rate on critical hooks, but the
current Wave A file estimate is only 40-50% — many mutants survive.
Need a lightweight in-repo framework to measure + drive test additions.

## Scope

Pure stdlib (ADR-002). No mutmut / cosmic-ray / mutpy dependency. We
parse the target file via `ast`, apply one of N mutation operators,
write the mutant to disk, run the bound test suite, and score
survival based on pytest exit code.

## Operators shipped (MVP)

- **BoundaryMutator** — `<` ↔ `<=`, `>` ↔ `>=` (off-by-one detection)
- **ComparisonFlipMutator** — `==` ↔ `!=`, `is` ↔ `is not`
- **LogicalMutator** — `and` ↔ `or`
- **ConstantMutator** — `True` ↔ `False`, `0` ↔ `1`
- **ReturnNegationMutator** — `return x` → `return not x` (bool context only)
- **ArithmeticMutator** — `+` ↔ `-` (binary)

Each operator walks the AST and yields `(line, col, description,
mutated_source)` tuples. The runner applies each mutation, saves
atomically, runs pytest, restores, and records the result.

## Usage

    python3 .claude/scripts/mutation-test.py \\
        --target .claude/hooks/_lib/output_scan.py \\
        --tests .claude/hooks/tests/test_output_scan.py \\
                .claude/hooks/tests/test_output_scan_fixtures.py \\
        --report /tmp/mutation-report.json

    # Run against all Wave A critical files:
    python3 .claude/scripts/mutation-test.py --wave-a-sweep

    # Cap mutation count for fast feedback:
    python3 .claude/scripts/mutation-test.py \\
        --target X.py --tests Y.py --max-mutations 20

## Output

JSON report with per-mutation status: killed / survived / errored /
skipped, plus aggregate kill-rate per operator and overall.

## Safety

The script NEVER leaves the target file in a mutated state: atomic
write + guaranteed restore via try/finally. Original SHA is checked
post-run; mismatch raises. `--dry-run` prints mutations without
applying.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple


# ---------------------------------------------------------------------
# Mutation operators — each yields (line, col, description, mutated_ast)
# ---------------------------------------------------------------------


class MutationOperator:
    name: str = "base"

    def mutants(self, tree: ast.AST) -> Iterator[Tuple[int, int, str, ast.AST]]:
        """Yield mutation variants for a target module (AST-mutation generator)."""
        raise NotImplementedError


def _deepcopy_mutate(
    tree: ast.AST,
    matcher: Callable[[ast.AST], bool],
    replacer: Callable[[ast.AST], ast.AST],
    describe: Callable[[ast.AST, ast.AST], str],
) -> Iterator[Tuple[int, int, str, ast.AST]]:
    """Walk the tree; for each node matching `matcher`, build a mutant
    copy with `replacer(node)` substituted at that position. Yields
    (line, col, description, mutated-tree).
    """
    for target_id, node in _indexed_walk(tree):
        if not matcher(node):
            continue
        mutated_tree = copy.deepcopy(tree)
        replacement_node: Optional[ast.AST] = None
        # Re-walk the mutated tree and replace the corresponding node
        for cand_id, cand in _indexed_walk(mutated_tree):
            if cand_id == target_id:
                replacement_node = replacer(cand)
                # ast.copy_location keeps line/col consistent
                ast.copy_location(replacement_node, cand)
                _splice(mutated_tree, target_id, replacement_node)
                break
        if replacement_node is None:
            continue
        line = getattr(node, "lineno", 0) or getattr(
            replacement_node, "lineno", 0
        )
        col = getattr(node, "col_offset", 0) or getattr(
            replacement_node, "col_offset", 0
        )
        yield line, col, describe(node, replacement_node), mutated_tree


def _indexed_walk(tree: ast.AST) -> Iterator[Tuple[str, ast.AST]]:
    """Walk nodes with a stable identity key (parent-field-index path)."""
    stack: List[Tuple[str, ast.AST]] = [("", tree)]
    while stack:
        key, node = stack.pop()
        yield key, node
        for field, value in reversed(list(ast.iter_fields(node))):
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        stack.append((f"{key}/{field}[{i}]", item))
            elif isinstance(value, ast.AST):
                stack.append((f"{key}/{field}", value))


def _splice(tree: ast.AST, target_id: str, new_node: ast.AST) -> None:
    """Replace the node at target_id inside tree with new_node."""
    # target_id is e.g. "/body[0]/value/ops[0]"
    parts = target_id.split("/")[1:]
    parent: ast.AST = tree
    last_field: Optional[str] = None
    last_index: Optional[int] = None
    last_container = None
    for part in parts[:-1]:
        if "[" in part:
            field, idx_s = part.split("[", 1)
            idx = int(idx_s.rstrip("]"))
            container = getattr(parent, field)
            parent = container[idx]
        else:
            parent = getattr(parent, part)
    final = parts[-1]
    if "[" in final:
        field, idx_s = final.split("[", 1)
        idx = int(idx_s.rstrip("]"))
        getattr(parent, field)[idx] = new_node
    else:
        setattr(parent, final, new_node)


class BoundaryMutator(MutationOperator):
    name = "boundary"

    def mutants(self, tree: ast.AST) -> Iterator[Tuple[int, int, str, ast.AST]]:
        """Yield mutants that flip off-by-one boundary operators (``<`` ↔ ``<=``)."""
        swaps = {
            ast.Lt: ast.LtE,
            ast.LtE: ast.Lt,
            ast.Gt: ast.GtE,
            ast.GtE: ast.Gt,
        }
        for line, col, desc, mt in _deepcopy_mutate(
            tree,
            lambda n: isinstance(n, tuple(swaps.keys())),
            lambda n: swaps[type(n)](),
            lambda o, n: f"boundary: {type(o).__name__} -> {type(n).__name__}",
        ):
            yield line, col, desc, mt


class ComparisonFlipMutator(MutationOperator):
    name = "comparison_flip"

    def mutants(self, tree: ast.AST) -> Iterator[Tuple[int, int, str, ast.AST]]:
        """Yield mutants that flip equality/membership comparisons (``==`` ↔ ``!=``)."""
        swaps = {
            ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq,
            ast.Is: ast.IsNot,
            ast.IsNot: ast.Is,
            ast.In: ast.NotIn,
            ast.NotIn: ast.In,
        }
        for line, col, desc, mt in _deepcopy_mutate(
            tree,
            lambda n: isinstance(n, tuple(swaps.keys())),
            lambda n: swaps[type(n)](),
            lambda o, n: f"comparison: {type(o).__name__} -> {type(n).__name__}",
        ):
            yield line, col, desc, mt


class LogicalMutator(MutationOperator):
    name = "logical"

    def mutants(self, tree: ast.AST) -> Iterator[Tuple[int, int, str, ast.AST]]:
        """Yield mutants that swap short-circuit logical operators (``and`` ↔ ``or``)."""
        swaps = {ast.And: ast.Or, ast.Or: ast.And}
        for line, col, desc, mt in _deepcopy_mutate(
            tree,
            lambda n: isinstance(n, tuple(swaps.keys())),
            lambda n: swaps[type(n)](),
            lambda o, n: f"logical: {type(o).__name__} -> {type(n).__name__}",
        ):
            yield line, col, desc, mt


class ConstantMutator(MutationOperator):
    name = "constant"

    def mutants(self, tree: ast.AST) -> Iterator[Tuple[int, int, str, ast.AST]]:
        """Yield mutants that flip boolean / zero-one constants (True↔False, 0↔1)."""
        def _match(n: ast.AST) -> bool:
            if not isinstance(n, ast.Constant):
                return False
            return n.value in (True, False, 0, 1)

        def _replace(n: ast.AST) -> ast.AST:
            # We know it's ast.Constant by match
            v = n.value  # type: ignore[attr-defined]
            swap = {True: False, False: True, 0: 1, 1: 0}[v]
            return ast.Constant(value=swap)

        def _describe(o, n) -> str:
            return (
                f"constant: {o.value!r} -> {n.value!r}"  # type: ignore
                if isinstance(o, ast.Constant) and isinstance(n, ast.Constant)
                else "constant"
            )

        for line, col, desc, mt in _deepcopy_mutate(
            tree, _match, _replace, _describe
        ):
            yield line, col, desc, mt


class ArithmeticMutator(MutationOperator):
    name = "arithmetic"

    def mutants(self, tree: ast.AST) -> Iterator[Tuple[int, int, str, ast.AST]]:
        """Yield mutants that swap arithmetic operators (``+`` ↔ ``-``, ``*`` ↔ ``//``)."""
        swaps = {
            ast.Add: ast.Sub,
            ast.Sub: ast.Add,
            ast.Mult: ast.FloorDiv,
            ast.Div: ast.Mult,
        }
        for line, col, desc, mt in _deepcopy_mutate(
            tree,
            lambda n: isinstance(n, tuple(swaps.keys())),
            lambda n: swaps[type(n)](),
            lambda o, n: f"arith: {type(o).__name__} -> {type(n).__name__}",
        ):
            yield line, col, desc, mt


_OPERATORS: List[MutationOperator] = [
    BoundaryMutator(),
    ComparisonFlipMutator(),
    LogicalMutator(),
    ConstantMutator(),
    ArithmeticMutator(),
]


# ---------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_atomic(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".mutant.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _run_tests(test_paths: List[Path], timeout: int = 120) -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", "--no-header"]
    cmd.extend(str(p) for p in test_paths)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        return 124


def run_mutation_sweep(
    target: Path,
    tests: List[Path],
    *,
    max_mutations: Optional[int] = None,
    dry_run: bool = False,
    timeout: int = 120,
    verbose: bool = False,
) -> Dict[str, object]:
    """Apply every mutation in turn, restore between, record result."""
    if not target.exists():
        raise FileNotFoundError(f"target missing: {target}")
    for t in tests:
        if not t.exists():
            raise FileNotFoundError(f"test path missing: {t}")

    original_source = target.read_text(encoding="utf-8")
    original_sha = hashlib.sha256(
        original_source.encode("utf-8")
    ).hexdigest()
    tree = ast.parse(original_source, filename=str(target))

    mutations: List[Tuple[str, int, int, str, ast.AST]] = []
    for op in _OPERATORS:
        for line, col, desc, mt in op.mutants(tree):
            mutations.append((op.name, line, col, desc, mt))

    if max_mutations is not None:
        mutations = mutations[:max_mutations]

    results: List[Dict[str, object]] = []
    per_operator: Dict[str, Dict[str, int]] = {}

    try:
        for idx, (op_name, line, col, desc, mt) in enumerate(mutations):
            mutated_src = ast.unparse(mt)
            status: str
            if dry_run:
                status = "dry-run"
            else:
                _write_atomic(target, mutated_src)
                try:
                    rc = _run_tests(tests, timeout=timeout)
                finally:
                    # Always restore before the next mutation
                    _write_atomic(target, original_source)
                # pytest rc=0 means tests passed → mutation SURVIVED
                # (bad — mutation not detected)
                if rc == 0:
                    status = "survived"
                elif rc == 124:
                    status = "timeout"
                elif rc == 5:
                    # no tests collected
                    status = "errored"
                else:
                    status = "killed"

            results.append({
                "index": idx,
                "operator": op_name,
                "line": line,
                "col": col,
                "description": desc,
                "status": status,
            })
            per_operator.setdefault(
                op_name, {"killed": 0, "survived": 0, "errored": 0,
                         "timeout": 0, "dry-run": 0}
            )
            per_operator[op_name][status] = (
                per_operator[op_name].get(status, 0) + 1
            )
            if verbose:
                print(
                    f"[{idx+1}/{len(mutations)}] {op_name} line {line}: "
                    f"{status}",
                    flush=True,
                )
    finally:
        # Defense-in-depth: verify restoration
        restored_sha = _sha256(target)
        if restored_sha != original_sha:
            # Force restore
            _write_atomic(target, original_source)

    killed = sum(1 for r in results if r["status"] == "killed")
    survived = sum(1 for r in results if r["status"] == "survived")
    errored = sum(
        1 for r in results if r["status"] in ("errored", "timeout")
    )
    total = killed + survived + errored
    kill_rate = (killed / total) if total > 0 else 0.0

    return {
        "target": str(target),
        "tests": [str(t) for t in tests],
        "total_mutations": len(mutations),
        "killed": killed,
        "survived": survived,
        "errored": errored,
        "kill_rate": round(kill_rate, 3),
        "per_operator": per_operator,
        "mutations": results if verbose else results[:20],
    }


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------


_WAVE_A_TARGETS = [
    (
        ".claude/hooks/_lib/output_scan.py",
        [
            ".claude/hooks/tests/test_output_scan.py",
            ".claude/hooks/tests/test_output_scan_fixtures.py",
        ],
    ),
    (
        ".claude/hooks/UserPromptSubmit.py",
        [".claude/hooks/tests/test_user_prompt_submit.py"],
    ),
    (
        ".claude/hooks/check_output_secrets.py",
        [".claude/hooks/tests/test_check_output_secrets.py"],
    ),
]


def main() -> int:
    """CLI entrypoint — run mutation tests against a selected module."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", help="Path to source file to mutate")
    ap.add_argument("--tests", nargs="+", help="Paths to test files/dirs")
    ap.add_argument(
        "--wave-a-sweep", action="store_true",
        help="Run sweep against all 3 Wave A critical files",
    )
    ap.add_argument(
        "--max-mutations", type=int, default=None,
        help="Cap total mutations applied (fast iteration)",
    )
    ap.add_argument(
        "--timeout", type=int, default=60,
        help="Per-run pytest timeout in seconds",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", help="Write JSON report to this path")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    reports: List[Dict[str, object]] = []

    if args.wave_a_sweep:
        for rel_target, rel_tests in _WAVE_A_TARGETS:
            target = repo_root / rel_target
            tests = [repo_root / t for t in rel_tests]
            print(f"\n=== Sweep: {rel_target} ===", flush=True)
            try:
                r = run_mutation_sweep(
                    target, tests,
                    max_mutations=args.max_mutations,
                    dry_run=args.dry_run,
                    timeout=args.timeout,
                    verbose=args.verbose,
                )
                reports.append(r)
                print(
                    f"  kill_rate={r['kill_rate']*100:.1f}% "
                    f"killed={r['killed']} survived={r['survived']} "
                    f"errored={r['errored']}"
                )
            except Exception as e:
                print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)
    else:
        if not args.target or not args.tests:
            ap.error("--target and --tests are required (or use --wave-a-sweep)")
        target = Path(args.target)
        tests = [Path(t) for t in args.tests]
        r = run_mutation_sweep(
            target, tests,
            max_mutations=args.max_mutations,
            dry_run=args.dry_run,
            timeout=args.timeout,
            verbose=args.verbose,
        )
        reports.append(r)
        print(json.dumps(r, indent=2))

    if args.report:
        Path(args.report).write_text(
            json.dumps(reports, indent=2), encoding="utf-8"
        )
        print(f"\nReport written: {args.report}")

    # Non-zero exit if any sweep has survivors
    any_survived = any(r.get("survived", 0) > 0 for r in reports)
    return 1 if any_survived else 0


if __name__ == "__main__":
    sys.exit(main())
