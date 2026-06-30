"""Smoke test — `SessionEnd.py` import + module-surface sanity.

Per audit-v2 finding C-18-04 (Session 74 close-cosmetic): every hook
under `.claude/hooks/*.py` should have at least one same-named test
file. This stub asserts the hook imports cleanly and exposes the
expected entry-point symbol.

Real behavioral coverage lives in:
- `test_session_end_full_branch.py` (full-branch lifecycle coverage)
- `test_session_end_branch_coverage.py` (edge cases)
- `test_session_end_audit_tokens_smoke.py` (audit-tokens emit)
- `test_audit_emit_session_end.py` (audit emit downstream)

This stub only guards against import-time regressions.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent
_MODULE_PATH = _HOOKS_DIR / "SessionEnd.py"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


class SessionEndImportTest(TestEnvContext):
    """Smoke: hook imports cleanly and has the expected entry-point."""

    def test_module_file_exists(self) -> None:
        self.assertTrue(
            _MODULE_PATH.is_file(),
            f"Expected {_MODULE_PATH} to exist on disk",
        )

    def test_module_imports_without_error(self) -> None:
        spec = importlib.util.spec_from_file_location("SessionEnd", _MODULE_PATH)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)  # type: ignore[union-attr]

    def test_module_has_main_entry_point(self) -> None:
        spec = importlib.util.spec_from_file_location("SessionEnd", _MODULE_PATH)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        # Hooks expose either `main()` or `decide()` as the entry-point.
        has_entry = hasattr(module, "main") or hasattr(module, "decide")
        self.assertTrue(has_entry, "hook must expose `main()` or `decide()`")


if __name__ == "__main__":
    unittest.main()
