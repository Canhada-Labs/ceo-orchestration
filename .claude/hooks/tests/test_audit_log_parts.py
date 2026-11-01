"""Facade binding contracts for the split PostToolUse audit hook."""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _lib.testing import TestEnvContext


HOOK = Path(__file__).resolve().parents[1] / "audit_log.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(HOOK))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestAuditLogPartsFacade(TestEnvContext):
    def test_fu144_facade_monkeypatch_reaches_extracted_builder(self) -> None:
        module = _load("audit_log_parts_patch")
        self.addCleanup(sys.modules.pop, "audit_log_parts_patch", None)
        event = SimpleNamespace(
            tool_name="Agent", description="probe", prompt="SKILL: original",
            session_id="session", subagent_type="", tool_response={},
        )
        with mock.patch.object(module, "extract_skill", return_value="patched-skill"):
            entry = module.build_entry(event=event, project_dir="/project", hook_duration_ms=1)
        self.assertEqual(entry["skill"], "patched-skill")

    def test_fu144_imports_keep_mutable_skill_map_independent(self) -> None:
        first = _load("audit_log_parts_first")
        second = _load("audit_log_parts_second")
        self.addCleanup(sys.modules.pop, "audit_log_parts_first", None)
        self.addCleanup(sys.modules.pop, "audit_log_parts_second", None)
        first._ARCHETYPE_TO_SKILL["probe"] = "probe-skill"
        self.assertNotIn("probe", second._ARCHETYPE_TO_SKILL)

    def test_fu144_inspect_reads_the_real_extracted_source(self) -> None:
        module = _load("audit_log_parts_inspect")
        self.addCleanup(sys.modules.pop, "audit_log_parts_inspect", None)
        self.assertIn("PostToolUse Agent audit log", module.__doc__)
        source_path = Path(inspect.getsourcefile(module.build_entry))
        self.assertEqual(source_path.name, "entries_usage.py")
        self.assertIn("def build_entry", inspect.getsource(module.build_entry))
