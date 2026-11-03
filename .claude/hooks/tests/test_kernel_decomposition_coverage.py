"""Guard for the KERNEL-DECOMPOSITION rows of ``_KERNEL_PATHS``.

The v1.4.4 train (merge 888e9e6c) moved the code of seven kernel facades
into helper packages below ``_lib/``, and put ``_lib/plan_paths.py`` in
place of the plan-path regexes it removed from ``check_plan_edit.py`` and
``policy_preprocessors.py``. Kernel files now call ``model_currency.py``
(the VETO-floor predicate) as part of their VETO-floor check. Kernel code
also calls ``cli_currency.py``, ``bash_indirect_guard.py`` and
``bash_indirect_telemetry.py``, each added by the train, and the kernel
``adapters/__init__.py`` loads the live-adapter package
``_lib/adapters/live`` (present since v1.0.0). ``_KERNEL_PATHS`` has a
row for each of these. This guard checks:

1. For every package directory strictly below ``_lib/`` (a directory with
   an ``__init__.py``) that a kernel source reaches, every ``.py`` module
   in it, recursively, is kernel. A kernel source is a ``.py`` file under
   ``.claude/hooks`` or ``.claude/dispatcher``, outside any ``tests/``
   directory, that is itself kernel. It reaches a package by an import
   statement (lazy or top-level, absolute or relative) or by a run of
   string literals in a ``/`` chain that, joined to the source's directory
   or to ``.claude/hooks``, names the package directory
   (``<expr> / "_lib" / "<pkg>"``, the exec-by-path form). The packages
   are derived from the code on every run, so a package reached this way
   later needs its row before this test is green.
2. The detector still finds every package in ``_KNOWN_BACKING_PACKAGES``
   (positive control), so check 1 cannot pass by finding nothing.
3. Each module in ``_FLAT_KERNEL_BACKERS`` is kernel and is still imported
   by a kernel source.
"""
from __future__ import annotations

import ast
import functools
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402
from check_arbitration_kernel import _is_kernel_path  # noqa: E402

# Trees that hold kernel Python sources.
_SCAN_TREES = (".claude/hooks", ".claude/dispatcher")
_SKIP_PARTS = frozenset({"tests", "__pycache__"})

# POSITIVE control: packages the detector must keep finding, or it has
# gone blind (green by vacuum). The seven of the v1.4.4 split, plus the
# live-adapter transport package.
_KNOWN_BACKING_PACKAGES = frozenset({
    ".claude/hooks/_lib/canonical_edit",  # check_canonical_edit.py (import)
    ".claude/hooks/_lib/agent_spawn",  # check_agent_spawn.py (import)
    ".claude/hooks/_lib/_policy_parts",  # _lib/policy.py (import)
    ".claude/hooks/_lib/_audit_emit_parts",  # _lib/audit_emit.py (import)
    ".claude/hooks/_lib/_pair_rail_parts",  # check_pair_rail.py (import)
    ".claude/hooks/_lib/_audit_log_parts",  # audit_log.py (exec by path)
    ".claude/hooks/_lib/_bash_safety_parts",  # check_bash_safety.py (exec)
    ".claude/hooks/_lib/adapters/live",  # adapters/__init__.py (lazy import)
})

# These five flat modules each have their own row.
_FLAT_KERNEL_BACKERS = (
    ".claude/hooks/_lib/model_currency.py",  # is_veto_floor_model()
    ".claude/hooks/_lib/cli_currency.py",  # Codex payload-pin currency arm
    ".claude/hooks/_lib/plan_paths.py",  # is_plan_path(), plan_id_from_path()
    ".claude/hooks/_lib/bash_indirect_guard.py",  # indirect-command matcher
    ".claude/hooks/_lib/bash_indirect_telemetry.py",  # disabled-rail record
)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _sources(root: Path) -> List[Path]:
    out: List[Path] = []
    for tree in _SCAN_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if not _SKIP_PARTS.intersection(path.relative_to(base).parts[:-1]):
                out.append(path)
    return out


def _resolve(dotted: str, base: Path) -> List[Path]:
    """Files executed by importing ``dotted`` from ``base`` (package inits too)."""
    found: List[Path] = []
    cur = base
    parts = dotted.split(".")
    for index, part in enumerate(parts):
        if (cur / part / "__init__.py").is_file():
            cur = cur / part
            found.append(cur / "__init__.py")
        elif index == len(parts) - 1 and (cur / (part + ".py")).is_file():
            found.append(cur / (part + ".py"))
        else:
            return []
    return found


def _import_targets(tree: ast.AST, path: Path, hooks: Path) -> Set[Path]:
    package: Optional[List[str]] = None
    if hooks in path.parents:
        package = list(path.parent.relative_to(hooks).parts)
    out: Set[Path] = set()
    for node in ast.walk(tree):
        names: List[str] = []
        bases = (hooks, path.parent)
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                if package is None or node.level - 1 > len(package):
                    continue
                head = package[: len(package) - (node.level - 1)]
                module = ".".join(head + ([module] if module else []))
                bases = (hooks,)
            if module:
                names = [module] + [module + "." + a.name for a in node.names]
        for name in names:
            for base in bases:
                hit = _resolve(name, base)
                if hit:
                    out.update(hit)
                    break
    return out


def _path_runs(node: ast.BinOp) -> List[List[str]]:
    """Maximal runs of string operands in an ``a / "x" / "y"`` chain."""
    items: List[Optional[str]] = []
    cur: ast.AST = node
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        right = cur.right
        is_str = isinstance(right, ast.Constant) and isinstance(right.value, str)
        items.insert(0, right.value if is_str else None)
        cur = cur.left
    runs: List[List[str]] = [[]]
    for item in items:
        if item is None:
            runs.append([])
        else:
            runs[-1].extend(seg for seg in item.split("/") if seg)
    return [run for run in runs if run]


def _backing_packages(root: Path) -> Dict[str, Set[str]]:
    """``{package dir below _lib: {kernel sources that reach it}}``."""
    hooks = root / ".claude" / "hooks"
    lib = hooks / "_lib"
    backing: Dict[str, Set[str]] = {}
    for path in _sources(root):
        if not _is_kernel_path(str(path), root):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        dirs = {target.parent for target in _import_targets(tree, path, hooks)}
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                for run in _path_runs(node):
                    dirs.update((path.parent.joinpath(*run), hooks.joinpath(*run)))
        for directory in dirs:
            if lib in directory.parents and (directory / "__init__.py").is_file():
                backing.setdefault(_rel(directory, root), set()).add(_rel(path, root))
    return backing


def _members(root: Path, package: str) -> List[Path]:
    """Python modules of a package, recursively (data files are not code)."""
    return [
        p for p in sorted((root / package).rglob("*.py"))
        if "__pycache__" not in p.parts
    ]


def _uncovered(root: Path, backing: Dict[str, Set[str]]) -> List[str]:
    out: List[str] = []
    for package in sorted(backing):
        for member in _members(root, package):
            rel = _rel(member, root)
            if not _is_kernel_path(str(member), root):
                out.append("%s  (reached from %s)" % (
                    rel, ", ".join(sorted(backing[package]))))
    return out


@functools.lru_cache(maxsize=1)
def _real_backing() -> Dict[str, Set[str]]:
    return _backing_packages(REPO_ROOT)


class KernelDecompositionCoverageTest(TestEnvContext):

    def test_known_backing_packages_are_still_detected(self) -> None:
        missing = sorted(_KNOWN_BACKING_PACKAGES - set(_real_backing()))
        self.assertEqual(missing, [], "detector lost a known backing package "
                         "(a guard that finds nothing passes by vacuum)")

    def test_every_backing_package_is_kernel_in_full(self) -> None:
        uncovered = _uncovered(REPO_ROOT, _real_backing())
        self.assertEqual(uncovered, [], "\n".join(
            ["kernel code lives in files the kernel rail does not guard; add "
             "'<pkg>/**/*' to _KERNEL_PATHS:"]
            + uncovered))

    def test_flat_kernel_backers_are_kernel_and_still_imported(self) -> None:
        importers: Set[str] = set()
        hooks = REPO_ROOT / ".claude" / "hooks"
        for path in _sources(REPO_ROOT):
            if _is_kernel_path(str(path), REPO_ROOT):
                tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
                importers.update(_rel(t, REPO_ROOT)
                                 for t in _import_targets(tree, path, hooks))
        for rel in _FLAT_KERNEL_BACKERS:
            with self.subTest(module=rel):
                self.assertTrue(_is_kernel_path(str(REPO_ROOT / rel), REPO_ROOT))
                self.assertIn(rel, importers, "no kernel source imports it "
                              "any more; revisit its _KERNEL_PATHS row and "
                              "_FLAT_KERNEL_BACKERS")

    def test_detector_catches_import_and_exec_forms(self) -> None:
        # Synthetic tree: a kernel-named facade reaching one package by
        # import and one by exec-by-path; neither package has a kernel row.
        root = self.project_dir
        self.write_project_file(".claude/hooks/check_canonical_edit.py", (
            "from pathlib import Path\n"
            "def _late():\n"
            "    from _lib.fake_pkg import mod  # lazy import form\n"
            "_PARTS = Path(__file__).resolve().parent / '_lib' / 'fake_exec'\n"
        ))
        for rel in ("_lib/__init__.py", "_lib/fake_pkg/__init__.py",
                    "_lib/fake_pkg/mod.py", "_lib/fake_exec/__init__.py",
                    "_lib/fake_exec/part.py", "_lib/unrelated/__init__.py"):
            self.write_project_file(".claude/hooks/" + rel, "X = 1\n")
        backing = _backing_packages(root)
        self.assertEqual(sorted(backing), [".claude/hooks/_lib/fake_exec",
                                           ".claude/hooks/_lib/fake_pkg"])
        uncovered = [line.split()[0] for line in _uncovered(root, backing)]
        self.assertEqual(uncovered, [
            ".claude/hooks/_lib/fake_exec/__init__.py",
            ".claude/hooks/_lib/fake_exec/part.py",
            ".claude/hooks/_lib/fake_pkg/__init__.py",
            ".claude/hooks/_lib/fake_pkg/mod.py",
        ])


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
