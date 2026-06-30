"""Smoke test — `check_subagent_fabrication.py` import + module-surface sanity.

Per audit-v2 finding C-18-04 (Session 74 close-cosmetic). Behavioral
coverage for the underlying detection library lives in
`test_subagent_fabrication.py` (`.claude/scripts/swarm/_subagent_fabrication.py`).
This stub only guards the hook wrapper against import-time regressions.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent
_MODULE_PATH = _HOOKS_DIR / "check_subagent_fabrication.py"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


class CheckSubagentFabricationImportTest(TestEnvContext):
    def test_module_file_exists(self) -> None:
        self.assertTrue(_MODULE_PATH.is_file())

    def test_module_imports_without_error(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "check_subagent_fabrication", _MODULE_PATH
        )
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]

    def test_module_has_callable_entry_point(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "check_subagent_fabrication", _MODULE_PATH
        )
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        # Thin-wrapper hook: re-exports _cli_main from
        # `swarm._subagent_fabrication`. Accept any of the canonical
        # entry-point names.
        has_entry = (
            hasattr(module, "main")
            or hasattr(module, "decide")
            or hasattr(module, "_cli_main")
        )
        self.assertTrue(has_entry)


if __name__ == "__main__":
    unittest.main()
