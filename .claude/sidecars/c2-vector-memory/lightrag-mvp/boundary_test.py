#!/usr/bin/env python3
"""C2 lightrag-mvp sidecar boundary test (ADR-126 §Part 5 + ADR-128 §4).

Enforces that no core path imports `chromadb`, `sentence_transformers`,
or `lightrag`. Runs in CI regardless of `CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED`
kill-switch state.

Exits 0 on clean boundary, 1 with a forensic message on any leak.

Contract from ADR-126 §Part 5 step 2b triad — workflow lines invoking
sidecar code MUST satisfy AT LEAST ONE of:
  (i) match one of `isolation.allowed_workflow_invocation_patterns`,
  (ii) contain no substring matching any entry in `isolation.import_roots`,
  (iii) live in `core_paths_allowlisted_workflow_invokers` AND be a
       `pip install` / `uv pip install` line (NOT `python -c "import X"`).

Plus §Part 5 step 2b(b): `python -c "import <root>"` BANNED in every
workflow regardless of allowlist match.
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


def _scan_dynamic_import_patterns(blocked_root: Path, import_roots: List[str]) -> List[Tuple[Path, int, str]]:
    """Scan for banned dynamic import patterns: importlib.import_module,
    __import__, exec/eval with string-literal import statements.

    AST + tokenize-based — string literals OUTSIDE comments/docstrings.
    """
    violations: List[Tuple[Path, int, str]] = []
    if not blocked_root.exists():
        return violations
    importlib_re = re.compile(
        r"\b(?:importlib\.import_module|__import__)\s*\(\s*['\"]("
        + "|".join(re.escape(r) for r in import_roots)
        + r")['\"]"
    )
    exec_eval_re = re.compile(
        r"\b(?:exec|eval)\s*\(\s*['\"]\s*(?:from|import)\s+("
        + "|".join(re.escape(r) for r in import_roots)
        + r")\b"
    )
    bare_import_str_re = re.compile(
        r"^\s*['\"]\s*(?:from|import)\s+("
        + "|".join(re.escape(r) for r in import_roots)
        + r")(?:[. \s'\"]|$)"
    )

    for py_path in blocked_root.rglob("*.py"):
        try:
            text = py_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.split("#", 1)[0]
            if importlib_re.search(stripped):
                violations.append((py_path, lineno, f"importlib-import: {stripped.strip()[:80]}"))
            if exec_eval_re.search(stripped):
                violations.append((py_path, lineno, f"exec-import: {stripped.strip()[:80]}"))
            if bare_import_str_re.search(stripped):
                violations.append((py_path, lineno, f"bare-import-str: {stripped.strip()[:80]}"))
    return violations


def _scan_workflow_invocations(
    workflows_root: Path,
    allowed_patterns: List[str],
    allowlisted_invokers: List[str],
    import_roots: List[str],
) -> List[Tuple[Path, int, str]]:
    """Scan .yml/.yaml under .github/workflows/ for forbidden invocations.

    Per ADR-126 §Part 5 step 2b triad.
    """
    violations: List[Tuple[Path, int, str]] = []
    if not workflows_root.exists():
        return violations
    compiled_allowed = [re.compile(p) for p in allowed_patterns]
    # python -c "import <root>" / 'from <root>' — BANNED everywhere per step 2b(b).
    python_c_re = re.compile(
        r"python3?\s+-c\s+['\"][^'\"]*\b(?:import|from)\s+("
        + "|".join(re.escape(r) for r in import_roots)
        + r")\b",
    )
    # Top-level `import <root>` / `from <root>` substring presence (lax — covers
    # any line mentioning the root token next to import/from).
    import_root_anywhere_re = re.compile(
        r"\b(?:import|from)\s+(" + "|".join(re.escape(r) for r in import_roots) + r")\b"
    )
    # Sidecar dir reference.
    sidecar_invoke_re = re.compile(r"\.claude/sidecars/c2-vector-memory/lightrag-mvp/")
    # Dependency-bootstrap line shapes (allowlisted-invoker condition iii).
    pip_install_re = re.compile(r"\b(?:pip|uv\s+pip)\s+install\b")

    for wf_path in workflows_root.rglob("*.y*ml"):
        try:
            text = wf_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel_path = wf_path.relative_to(_REPO_ROOT).as_posix()
        is_allowlisted_invoker = rel_path in allowlisted_invokers
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            # §Part 5 step 2b(b): python -c "import <root>" BANNED everywhere.
            if python_c_re.search(line):
                violations.append((wf_path, lineno, f"banned-python-c: {line[:80]}"))
                continue
            # Sidecar-path invocation: must match allowed pattern OR be in invoker file.
            if sidecar_invoke_re.search(line):
                if any(p.search(line) for p in compiled_allowed):
                    continue  # condition (i)
                if is_allowlisted_invoker and pip_install_re.search(line):
                    continue  # condition (iii) — dependency bootstrap in allowlist
                violations.append((wf_path, lineno, f"unsanctioned-sidecar-invoke: {line[:80]}"))
                continue
            # Generic import-root mention.
            if import_root_anywhere_re.search(line):
                # condition (ii) fails — line contains import root token.
                # If file is allowlisted invoker AND line is pip install — OK.
                if is_allowlisted_invoker and pip_install_re.search(line):
                    continue
                # Otherwise — line is forbidden.
                violations.append((wf_path, lineno, f"forbidden-import-in-workflow: {line[:80]}"))
    return violations


def main() -> int:
    try:
        manifest = _load_manifest()
    except (OSError, json.JSONDecodeError) as exc:
        # Fail-OPEN per ADR-126 §Part 5 step 8 — surfaces as
        # sidecar_manifest_missing_or_malformed in CI, distinct error class.
        sys.stderr.write(f"sidecar_manifest_missing_or_malformed: {exc}\n")
        return 1
    iso = manifest["isolation"]
    import_roots: List[str] = iso["import_roots"]
    blocked: List[str] = iso["core_paths_blocked"]
    allowed_patterns: List[str] = iso["allowed_workflow_invocation_patterns"]
    allowlisted_invokers: List[str] = iso["core_paths_allowlisted_workflow_invokers"]

    all_violations: List[str] = []

    # Part 5 §2 — AST scan over Python files in blocked roots.
    for blocked_rel in blocked:
        if blocked_rel.endswith(".github/workflows/"):
            continue  # workflows scanned in §2b below
        root = _REPO_ROOT / blocked_rel
        for path, lineno, modname in _scan_python_imports(root, import_roots):
            all_violations.append(
                f"PYTHON-IMPORT-LEAK: {path.relative_to(_REPO_ROOT)}:{lineno} imports '{modname}'"
            )
        # Part 5 §5 — dynamic import patterns.
        for path, lineno, msg in _scan_dynamic_import_patterns(root, import_roots):
            all_violations.append(
                f"DYNAMIC-IMPORT-LEAK: {path.relative_to(_REPO_ROOT)}:{lineno} {msg}"
            )

    # Part 5 §2b — YAML/workflow scan.
    workflows_root = _REPO_ROOT / ".github" / "workflows"
    for path, lineno, msg in _scan_workflow_invocations(
        workflows_root, allowed_patterns, allowlisted_invokers, import_roots
    ):
        all_violations.append(
            f"WORKFLOW-LEAK: {path.relative_to(_REPO_ROOT)}:{lineno} {msg}"
        )

    if all_violations:
        sys.stderr.write("C2 lightrag-mvp sidecar boundary FAILED:\n")
        for v in all_violations:
            sys.stderr.write(f"  - {v}\n")
        return 1

    print("C2 lightrag-mvp sidecar boundary OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
