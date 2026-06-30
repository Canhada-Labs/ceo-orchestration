#!/usr/bin/env python3
"""C5 hypothesis sidecar boundary test (ADR-126 §Part 5 + ADR-131 §C5.1).

Enforces that no core path imports `hypothesis` or `jsonschema`. Runs in CI
regardless of `CEO_SIDECAR_HYPOTHESIS_ENABLED` kill-switch state.

Exits 0 on clean boundary, 1 with a forensic message on any leak.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent.parent
_MANIFEST = _HERE / "manifest.json"


def _load_manifest() -> dict:
    with _MANIFEST.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _scan_python_imports(blocked_root: Path, import_roots: List[str]) -> List[Tuple[Path, int, str]]:
    """Return list of (path, lineno, module) for any import of a blocked module."""
    violations: List[Tuple[Path, int, str]] = []
    if not blocked_root.exists():
        return violations
    for py_path in blocked_root.rglob("*.py"):
        # Skip the sidecar's own internal tests if they happen to live within
        # an otherwise-blocked tree (defensive — current layout puts them in
        # .claude/sidecars/ which is not blocked).
        try:
            text = py_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            tree = ast.parse(text, filename=str(py_path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in import_roots:
                        violations.append((py_path, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    if top in import_roots:
                        violations.append((py_path, node.lineno, node.module))
    return violations


def _scan_workflow_invocations(
    workflows_root: Path,
    allowed_patterns: List[str],
    allowlisted_invokers: List[str],
    import_roots: List[str],
) -> List[Tuple[Path, int, str]]:
    """Scan .yml/.yaml under .github/workflows/ for hypothesis/jsonschema invocations.

    A `run:`-body line that mentions an import root or invokes a python file
    under the sidecar dir must EITHER match an allowed pattern OR live in an
    allowlisted invoker workflow file.
    """
    violations: List[Tuple[Path, int, str]] = []
    if not workflows_root.exists():
        return violations
    compiled = [re.compile(p) for p in allowed_patterns]
    import_root_re = re.compile(r"\b(?:import|from)\s+(" + "|".join(re.escape(r) for r in import_roots) + r")\b")
    sidecar_invoke_re = re.compile(r"\.claude/sidecars/c5-dev-tools/hypothesis/")

    for wf_path in workflows_root.rglob("*.y*ml"):
        try:
            text = wf_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel_path = wf_path.relative_to(_REPO_ROOT).as_posix()
        is_allowlisted_invoker = rel_path in allowlisted_invokers
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if import_root_re.search(line):
                # explicit `import hypothesis` / `from jsonschema import ...`
                # in any workflow body — disallowed even in allowlisted
                # invokers (sidecar is the only legitimate import site).
                violations.append((wf_path, lineno, f"forbidden-import: {line[:80]}"))
                continue
            if sidecar_invoke_re.search(line):
                if is_allowlisted_invoker:
                    continue
                if any(pat.search(line) for pat in compiled):
                    continue
                violations.append((wf_path, lineno, f"unsanctioned-sidecar-invoke: {line[:80]}"))
    return violations


def main() -> int:
    manifest = _load_manifest()
    iso = manifest["isolation"]
    import_roots: List[str] = iso["import_roots"]
    blocked: List[str] = iso["core_paths_blocked"]
    allowed_patterns: List[str] = iso["allowed_workflow_invocation_patterns"]
    allowlisted_invokers: List[str] = iso["core_paths_allowlisted_workflow_invokers"]

    all_violations: List[str] = []

    # Part 5 §2: AST scan over Python files in blocked roots.
    for blocked_rel in blocked:
        if blocked_rel.endswith(".github/workflows/"):
            continue  # workflows scanned in §2b below
        root = _REPO_ROOT / blocked_rel
        for path, lineno, modname in _scan_python_imports(root, import_roots):
            all_violations.append(
                f"PYTHON-IMPORT-LEAK: {path.relative_to(_REPO_ROOT)}:{lineno} imports '{modname}'"
            )

    # Part 5 §2b: YAML/workflow scan.
    workflows_root = _REPO_ROOT / ".github" / "workflows"
    for path, lineno, msg in _scan_workflow_invocations(
        workflows_root, allowed_patterns, allowlisted_invokers, import_roots
    ):
        all_violations.append(
            f"WORKFLOW-LEAK: {path.relative_to(_REPO_ROOT)}:{lineno} {msg}"
        )

    if all_violations:
        sys.stderr.write("C5 hypothesis sidecar boundary FAILED:\n")
        for v in all_violations:
            sys.stderr.write(f"  - {v}\n")
        return 1

    print("C5 hypothesis sidecar boundary OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
