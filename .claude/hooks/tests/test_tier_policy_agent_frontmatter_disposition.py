"""PLAN-113 W7 finding F-6-6.9 — tier_policy._agent_frontmatter disposition.

Codifies the A2/W7 dead-code disposition for
``.claude/hooks/_lib/tier_policy/_agent_frontmatter.py``:

* It has NO production-hook runtime importer (only its own test suite +
  the ``check_arbitration_kernel.py`` canonical-guard string list).
* It is NOT a duplicate of the similarly-named
  ``.claude/scripts/tier_policy_cli/_agent_frontmatter.py`` — they share a
  filename only and expose entirely different, non-overlapping public APIs,
  so it must NOT be de-duplicated by re-export.
* It is RETAINED-by-design (dispositioned-dead-for-runtime); the module is
  not to be deleted.

The finding's premise ("two ``_agent_frontmatter.py`` with different
content; one dead, dedupe by re-export") is corrected here: the modules are
distinct by purpose, and the ``_lib`` copy is a kernel-guarded security
parser whose attack-surface tests are load-bearing.

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

# Repo root: this file is .claude/hooks/tests/<name>.py
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
_LIB_MODULE = _HOOKS_DIR / "_lib" / "tier_policy" / "_agent_frontmatter.py"
_CLI_MODULE = (
    _REPO_ROOT / ".claude" / "scripts" / "tier_policy_cli" / "_agent_frontmatter.py"
)
_KERNEL_HOOK = _HOOKS_DIR / "check_arbitration_kernel.py"


def _public_symbols(path: Path) -> set:
    """Return top-level public def/class names declared in a module file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                out.add(node.name)
    return out


def _iter_production_hook_files():
    """Yield production (non-test) hook .py files under .claude/hooks/."""
    for p in sorted(_HOOKS_DIR.rglob("*.py")):
        parts = p.parts
        if "tests" in parts:
            continue
        if "__pycache__" in parts:
            continue
        yield p


class TierPolicyAgentFrontmatterDispositionTest(unittest.TestCase):

    def test_modules_exist(self) -> None:
        self.assertTrue(_LIB_MODULE.is_file(), f"missing {_LIB_MODULE}")
        self.assertTrue(_CLI_MODULE.is_file(), f"missing {_CLI_MODULE}")

    def test_no_production_hook_imports_lib_agent_frontmatter(self) -> None:
        """No production hook (non-test) imports the _lib parser at runtime.

        Tests + the kernel-guard string list are exempt. If a future hook
        legitimately wires this parser into a runtime path, update the
        module docstring + this test together — the disposition changes.
        """
        # We care about *real runtime use*: an import of the module, or an
        # actual call to its entrypoint. AST gives us that precisely without
        # tripping on docstring / comment references (e.g. _constants.py
        # documents the parser in prose, but does not import it).
        offenders = []
        for p in _iter_production_hook_files():
            if p.resolve() == _LIB_MODULE.resolve():
                continue  # the module itself
            if p.resolve() == _KERNEL_HOOK.resolve():
                # Kernel hook references the path as a guarded string literal,
                # not an import — assert that explicitly below.
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                # `import x.tier_policy._agent_frontmatter`
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.endswith("tier_policy._agent_frontmatter"):
                            offenders.append((str(p), f"import {alias.name}"))
                # `from x.tier_policy._agent_frontmatter import ...`
                # `from x.tier_policy import _agent_frontmatter`
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod.endswith("tier_policy._agent_frontmatter"):
                        offenders.append((str(p), f"from {mod} import ..."))
                    elif mod.endswith("tier_policy"):
                        for alias in node.names:
                            if alias.name == "_agent_frontmatter":
                                offenders.append(
                                    (str(p), f"from {mod} import _agent_frontmatter")
                                )
                # `parse_agent_frontmatter(...)` call site
                elif isinstance(node, ast.Call):
                    fn = node.func
                    name = None
                    if isinstance(fn, ast.Name):
                        name = fn.id
                    elif isinstance(fn, ast.Attribute):
                        name = fn.attr
                    if name == "parse_agent_frontmatter":
                        offenders.append((str(p), "parse_agent_frontmatter(...) call"))
        self.assertEqual(
            offenders,
            [],
            "production hook now imports tier_policy._agent_frontmatter at "
            "runtime; the dead-for-runtime disposition no longer holds — "
            f"update the module docstring + this test. Offenders: {offenders}",
        )

    def test_kernel_guard_protects_lib_module_as_string_literal(self) -> None:
        """check_arbitration_kernel.py lists the file (string), not imports it."""
        text = _KERNEL_HOOK.read_text(encoding="utf-8")
        rel = ".claude/hooks/_lib/tier_policy/_agent_frontmatter.py"
        self.assertIn(
            rel,
            text,
            "kernel canonical-guard no longer protects the _lib parser path; "
            "the retained-by-design rationale weakens.",
        )
        # Confirm it is a guarded string literal, NOT a python import statement.
        self.assertNotRegex(
            text,
            r"(?m)^\s*(?:from|import)\s+.*tier_policy\._agent_frontmatter",
        )

    def test_lib_and_cli_modules_have_distinct_apis(self) -> None:
        """The two same-named modules expose non-overlapping public APIs.

        This is the evidence that they are NOT duplicates and must NOT be
        de-duplicated by re-export.
        """
        lib_syms = _public_symbols(_LIB_MODULE)
        cli_syms = _public_symbols(_CLI_MODULE)
        self.assertIn("parse_agent_frontmatter", lib_syms)
        self.assertIn("parse_model_field", cli_syms)
        self.assertIn("detect_adopter_override", cli_syms)
        # The CLI's narrow API is absent from the _lib hardened parser.
        self.assertNotIn("parse_model_field", lib_syms)
        self.assertNotIn("detect_adopter_override", lib_syms)
        # And the _lib hardened entrypoint is absent from the CLI helper.
        self.assertNotIn("parse_agent_frontmatter", cli_syms)
        # No public-symbol overlap at all → genuinely distinct modules.
        self.assertEqual(
            lib_syms & cli_syms,
            set(),
            "the two _agent_frontmatter modules share public symbols; "
            "re-investigate whether they should be unified.",
        )

    def test_lib_module_documents_its_disposition(self) -> None:
        """The module docstring records the retained-by-design disposition."""
        text = _LIB_MODULE.read_text(encoding="utf-8")
        self.assertIn("Dispositioned-dead-for-runtime", text)
        self.assertIn("RETAINED-by-design", text)
        self.assertIn("F-6-6.9", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
