"""Smoke test — `check_webfetch_injection.py` import + module-surface sanity.

Per audit-v2 finding C-18-04 (Session 74 close-cosmetic). The WebFetch
/ WebSearch injection scanner (PLAN-058 Phase A1, incident response
2026-04-24) lives here as a PostToolUse advisory. Behavioral coverage
sits in `test_check_webfetch_injection_*.py` siblings + the underlying
`scan-injection.py` family. This stub only guards import-time
regressions on the hook entry-point.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent
_MODULE_PATH = _HOOKS_DIR / "check_webfetch_injection.py"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


class CheckWebFetchInjectionImportTest(TestEnvContext):
    def test_module_file_exists(self) -> None:
        self.assertTrue(_MODULE_PATH.is_file())

    def test_module_imports_without_error(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "check_webfetch_injection", _MODULE_PATH
        )
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]

    def test_module_has_main_entry_point(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "check_webfetch_injection", _MODULE_PATH
        )
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        has_entry = hasattr(module, "main") or hasattr(module, "decide")
        self.assertTrue(has_entry)


if __name__ == "__main__":
    unittest.main()
