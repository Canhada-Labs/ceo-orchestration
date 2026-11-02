"""Facade binding regressions for the split ``ceo-boot`` implementation."""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

from _lib.testing import TestEnvContext


SCRIPT = Path(__file__).resolve().parents[1] / "ceo-boot.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestCeoBootParts(TestEnvContext):
    def test_fu144_extracted_functions_keep_facade_globals(self):
        module = _load("ceo_boot_parts_globals")
        self.addCleanup(sys.modules.pop, "ceo_boot_parts_globals", None)
        plan = self.project_dir / ".claude/plans/PLAN-201-live.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("---\nstatus: executing\n---\n", encoding="utf-8")
        module._get_plan_paths = lambda: [plan]
        status, summary, detail = module.check_plans_executing()
        self.assertEqual((status, detail), ("yellow", ["PLAN-201-live"]))
        self.assertIn("1 executing", summary)

    def test_fu144_each_facade_import_gets_independent_mutable_state(self):
        first = _load("ceo_boot_parts_first")
        second = _load("ceo_boot_parts_second")
        self.addCleanup(sys.modules.pop, "ceo_boot_parts_first", None)
        self.addCleanup(sys.modules.pop, "ceo_boot_parts_second", None)
        first.PER_CHECK_TIMEOUT_OVERRIDES_S["isolation_probe"] = 0.01
        self.assertNotIn("isolation_probe", second.PER_CHECK_TIMEOUT_OVERRIDES_S)

    def test_fu144_function_source_points_to_real_part_file(self):
        module = _load("ceo_boot_parts_source")
        self.addCleanup(sys.modules.pop, "ceo_boot_parts_source", None)
        filename = Path(module.check_plans_executing.__code__.co_filename)
        self.assertEqual(filename.parent.name, "_ceo_boot_parts")
        self.assertTrue(filename.is_file())
        source = inspect.getsource(module.check_plans_executing)
        self.assertIn("plans = _get_plan_paths()", source)
