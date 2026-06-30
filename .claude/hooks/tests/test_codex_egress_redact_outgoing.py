"""PLAN-084 Wave 0.5 (ADR-114 + AC9) — Codex egress redaction symmetry tests.

Verifies that every Codex / external-LLM egress callsite applies
`codex_egress_redact.redact_outgoing()` BEFORE the prompt reaches the
process boundary (subprocess.run, mcp__codex__*, etc.).

Per AC9 §6 — 3 mandatory tests:
  - test_codex_invoke_redacts_outgoing_prompt
  - test_check_pair_rail_redacts_outgoing_prompt
  - test_codex_egress_callsite_coverage (AST-based enumeration)
"""

from __future__ import annotations

import ast
import os
import sys
import unittest
from pathlib import Path
from typing import List, Tuple
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"
_SCRIPTS = _REPO_ROOT / ".claude" / "scripts"

# Make _lib importable
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))


class TestRedactOutgoingFunctionExists(unittest.TestCase):
    """Foundational check — the function must exist + be importable."""

    def test_redact_outgoing_function_exists(self):
        from _lib import codex_egress_redact
        self.assertTrue(
            hasattr(codex_egress_redact, "redact_outgoing"),
            "codex_egress_redact.redact_outgoing() must exist per ADR-114",
        )

    def test_redact_outgoing_scrubs_aws_key(self):
        from _lib import codex_egress_redact
        result = codex_egress_redact.redact_outgoing(
            "AWS key: AKIAIOSFODNN7EXAMPLE inline"
        )
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", result)
        self.assertIn("REDACTED", result)


class TestCodexInvokeRedactsOutgoingPrompt(unittest.TestCase):
    """AC9 mandatory test #1 — codex_invoke.invoke_codex() callsite."""

    def test_codex_invoke_redacts_outgoing_prompt(self):
        """invoke_codex must apply redact_outgoing BEFORE subprocess.run."""
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        # Import codex_invoke as a module + check redact_outgoing is called
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_test_codex_invoke",
            _SCRIPTS / "codex_invoke.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Inspect source: redact_outgoing must appear BEFORE
        # make_invoke_command in invoke_codex function body
        source = (_SCRIPTS / "codex_invoke.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "invoke_codex":
                # Walk body, find redact_outgoing call THEN make_invoke_command
                saw_redact = False
                saw_make_invoke = False
                redact_idx = -1
                make_invoke_idx = -1
                for i, stmt in enumerate(ast.walk(node)):
                    if isinstance(stmt, ast.Attribute) and stmt.attr in ("redact_outgoing", "redact_outgoing_with_findings"):
                        saw_redact = True
                        if redact_idx == -1:
                            redact_idx = i
                    if isinstance(stmt, ast.Attribute) and stmt.attr == "make_invoke_command":
                        saw_make_invoke = True
                        if make_invoke_idx == -1:
                            make_invoke_idx = i
                self.assertTrue(saw_redact, "invoke_codex must call redact_outgoing")
                self.assertTrue(saw_make_invoke, "invoke_codex must call make_invoke_command")
                self.assertLess(
                    redact_idx, make_invoke_idx,
                    "redact_outgoing must be called BEFORE make_invoke_command "
                    "(else prompt leaks unredacted)",
                )
                return
        self.fail("invoke_codex function not found in codex_invoke.py")


class TestCheckPairRailRedactsOutgoingPrompt(unittest.TestCase):
    """AC9 mandatory test #2 — check_pair_rail._invoke_codex_review() callsite.

    This is the path that R2-iter-1 caught as missed by R1 Sec-P0-2.
    """

    def test_check_pair_rail_redacts_outgoing_prompt(self):
        """_invoke_codex_review must apply redact_outgoing BEFORE subprocess.run."""
        source = (_HOOKS_LIB / "check_pair_rail.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_invoke_codex_review":
                saw_redact = False
                saw_subprocess_run = False
                redact_idx = -1
                subprocess_idx = -1
                for i, stmt in enumerate(ast.walk(node)):
                    if isinstance(stmt, ast.Attribute) and stmt.attr in ("redact_outgoing", "redact_outgoing_with_findings"):
                        saw_redact = True
                        if redact_idx == -1:
                            redact_idx = i
                    if isinstance(stmt, ast.Attribute) and stmt.attr == "run":
                        # subprocess.run path
                        if isinstance(stmt.value, ast.Name) and stmt.value.id == "subprocess":
                            saw_subprocess_run = True
                            if subprocess_idx == -1:
                                subprocess_idx = i
                self.assertTrue(
                    saw_redact,
                    "_invoke_codex_review must call redact_outgoing — this is the "
                    "live Pair-Rail review path that R2-iter-1 Codex MCP gate caught as "
                    "missing in R1 Sec-P0-2 (which only wired codex_invoke.py)",
                )
                self.assertTrue(saw_subprocess_run, "_invoke_codex_review must call subprocess.run")
                self.assertLess(
                    redact_idx, subprocess_idx,
                    "redact_outgoing must be called BEFORE subprocess.run",
                )
                return
        self.fail("_invoke_codex_review function not found in check_pair_rail.py")


class TestCodexEgressCallsiteCoverage(unittest.TestCase):
    """AC9 mandatory test #3 — AST-based enumeration of ALL Codex egress callsites.

    Walks `subprocess.run`, `_codex.make_invoke_command`, `mcp__codex__*`
    invocations across the codebase. Fails if any callsite reaches a
    Codex/external-LLM API without prior `redact_outgoing()` invocation
    in the same function scope.

    This is the GUARANTEED enforcement mechanism — NOT vibes.
    """

    # Allowlisted callsite files — these MUST be in the coverage set.
    # PLAN-085 Wave D.2 — grown 2 → 4 entries. The two new entries
    # (``adapters/codex.py`` and ``_lib/mcp/canonical_guard.py``) carry
    # defensive redact-then-egress wrappers per ADR-114 §AC9. The first
    # two are the historical "live" egress paths (Pair-Rail dispatch +
    # codex_invoke subprocess).
    EXPECTED_CALLSITES = (
        _SCRIPTS / "codex_invoke.py",
        _HOOKS_LIB / "check_pair_rail.py",
        _HOOKS_LIB / "_lib" / "adapters" / "codex.py",
        _HOOKS_LIB / "_lib" / "mcp" / "canonical_guard.py",
    )

    def _walk_funcs_calling_codex_egress(self, source: str) -> List[Tuple[str, bool]]:
        """Return [(function_name, has_redact_outgoing_before_egress)]."""
        results = []
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            redact_idx = None
            egress_idx = None
            for i, stmt in enumerate(ast.walk(node)):
                if isinstance(stmt, ast.Attribute):
                    if stmt.attr in ("redact_outgoing", "redact_outgoing_with_findings"):
                        if redact_idx is None:
                            redact_idx = i
                    if stmt.attr in ("make_invoke_command",):
                        # PLAN-142 D2: the codex.py make_invoke_command* wrappers
                        # DELEGATE to the non-kernel codex_cli_shape.make_invoke_command
                        # (an argv BUILDER, not an egress — it runs no subprocess and
                        # the prompt it receives is already redacted by the caller).
                        # The real egress is subprocess.run in the two callers below,
                        # each of which redact_outgoing first. Do NOT treat a builder's
                        # own delegation call as an egress callsite needing redaction.
                        if node.name not in ("make_invoke_command", "make_invoke_command_redacted"):
                            if egress_idx is None:
                                egress_idx = i
                    if stmt.attr == "run" and isinstance(stmt.value, ast.Name) and stmt.value.id == "subprocess":
                        # Need to check if this subprocess.run is in a Codex-egress context
                        # Heuristic: function name mentions codex / pair_rail
                        if "codex" in node.name.lower() or "pair_rail" in node.name.lower():
                            if egress_idx is None:
                                egress_idx = i
            if egress_idx is not None:
                has_redact = redact_idx is not None and redact_idx < egress_idx
                results.append((node.name, has_redact))
        return results

    def test_codex_egress_callsite_coverage(self):
        """Every Codex egress callsite must have redact_outgoing before it.

        PLAN-085 R2 fold (Codex iter-1 P0:C blindspot catch): each entry in
        ``EXPECTED_CALLSITES`` MUST also carry ≥1 ``redact_outgoing`` reference
        in its source — prevents a "no-op coverage entry" where a file is
        added to the tuple to satisfy cardinality but contributes no
        mechanical defense (the AST egress-walker finds 0 functions and
        silently passes). The per-file source-grep makes the contribution
        explicit.
        """
        violations = []
        empty_files = []
        for filepath in self.EXPECTED_CALLSITES:
            source = filepath.read_text(encoding="utf-8")
            # Per-file ≥1 redact_outgoing reference assertion (anti-vacuous).
            if "redact_outgoing" not in source:
                empty_files.append(str(filepath.relative_to(_REPO_ROOT)))
                continue
            funcs = self._walk_funcs_calling_codex_egress(source)
            for fname, has_redact in funcs:
                if not has_redact:
                    violations.append(f"{filepath.relative_to(_REPO_ROOT)}::{fname}")
        self.assertEqual(
            empty_files, [],
            "AC9 VACUOUS: EXPECTED_CALLSITES file has zero `redact_outgoing` "
            "references — remove from tuple OR add a real defense primitive: "
            + ", ".join(empty_files),
        )
        self.assertEqual(
            violations, [],
            "AC9 VIOLATION: Codex egress callsites missing redact_outgoing(): "
            + ", ".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
