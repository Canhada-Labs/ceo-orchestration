"""PLAN-089 Wave D.3 — anti-regression for PLAN-085 Wave C callsites.

Wave C of PLAN-085 wired two governance primitives into the live
adapter:

- **C.1** `_check_live_adapter_allowlist` — defined on the live
  adapter class in `.claude/hooks/_lib/adapters/live/claude.py`
  and consulted at adapter spawn time.
- **C.2** `emit_credential_rotation_due` — emitted by the live
  adapter on credential-rotation-due audit events
  (ADR-040 §4 / §6.3 wire to the audit pipeline). Function is
  registered in `.claude/hooks/_lib/audit_emit.py`.

PLAN-085 Wave E shipped these callsites; PLAN-089 Wave D.3 protects
them against silent removal during future refactors. The tests are
AST-based (function-name presence, not specific line numbers) so
they tolerate cosmetic reformats and import-reorderings — only
hard regressions (function removed, callsite excised) trigger.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LIVE_ADAPTER = (
    REPO_ROOT / ".claude" / "hooks" / "_lib" / "adapters" / "live" / "claude.py"
)
AUDIT_EMIT = REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"


def _function_names_called(tree: ast.AST) -> set:
    """Return the set of all callable names referenced via Call nodes.

    Captures both `name()` (`Name`) and `obj.name()` (`Attribute`)
    invocations. Self-method calls (`self._foo()`) surface as
    `Attribute` with attr=`_foo`.
    """
    names: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _function_names_defined(tree: ast.AST) -> set:
    """Return the set of all FunctionDef + AsyncFunctionDef names."""
    names: set = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


class TestPlan085WaveCCallsitesPreserved(unittest.TestCase):
    """Anti-regression for PLAN-085 Wave C.1 + C.2 callsites."""

    def setUp(self) -> None:
        self.assertTrue(
            LIVE_ADAPTER.exists(),
            msg=(
                f"live adapter missing: {LIVE_ADAPTER!s}. PLAN-085 Wave C "
                f"contract requires this file to exist."
            ),
        )
        self.assertTrue(
            AUDIT_EMIT.exists(),
            msg=(
                f"audit_emit missing: {AUDIT_EMIT!s}. ADR-040 §4 wire "
                f"requires this registry to exist."
            ),
        )
        self._live_tree = ast.parse(LIVE_ADAPTER.read_text(encoding="utf-8"))
        self._audit_tree = ast.parse(AUDIT_EMIT.read_text(encoding="utf-8"))

    def test_plan_085_c1_check_live_adapter_allowlist_preserved(self) -> None:
        """C.1: `_check_live_adapter_allowlist` is defined or called.

        The function is defined as a method on the live adapter class
        AND called from another method on the same class. Both surface
        via AST `FunctionDef`/`Attribute` walks. The union check is
        tolerant of refactors that move the call inline or extract it
        elsewhere — only full removal trips the test.
        """
        defined = _function_names_defined(self._live_tree)
        called = _function_names_called(self._live_tree)
        union = defined | called
        self.assertIn(
            "_check_live_adapter_allowlist",
            union,
            msg=(
                "PLAN-085 Wave C.1 callsite missing from live/claude.py — "
                "PLAN-089 Wave D.3 anti-regression fail. The "
                "`_check_live_adapter_allowlist` method must remain "
                "defined and/or called in "
                f"{LIVE_ADAPTER.relative_to(REPO_ROOT)!s}."
            ),
        )

    def test_plan_085_c2_emit_credential_rotation_due_preserved(self) -> None:
        """C.2: `emit_credential_rotation_due` is called from the adapter.

        The function is imported from `_lib.audit_emit` and called on the
        credential-rotation-due code path (ADR-040 §4). AST surfaces the
        call as an `Attribute` with attr=`emit_credential_rotation_due`.
        """
        called = _function_names_called(self._live_tree)
        self.assertIn(
            "emit_credential_rotation_due",
            called,
            msg=(
                "PLAN-085 Wave C.2 callsite missing — ADR-040 §4 wire "
                "severed at the live-adapter layer. Restore the "
                "`_audit_emit.emit_credential_rotation_due(...)` call in "
                f"{LIVE_ADAPTER.relative_to(REPO_ROOT)!s}."
            ),
        )

    def test_adr_040_section_4_6_3_wired(self) -> None:
        """Cross-reference: `emit_credential_rotation_due` defined in audit_emit.

        Without the registry-layer definition the live-adapter call is a
        compile-time `AttributeError`. This test guards the registry side
        of the wire (ADR-040 §6.3 audit-emit promotion).
        """
        defined = _function_names_defined(self._audit_tree)
        self.assertIn(
            "emit_credential_rotation_due",
            defined,
            msg=(
                f"{AUDIT_EMIT.relative_to(REPO_ROOT)!s} missing "
                "`emit_credential_rotation_due` — ADR-040 §6.3 audit-emit "
                "registry wire severed. PLAN-085 Wave C.2 cannot resolve "
                "without this function."
            ),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
