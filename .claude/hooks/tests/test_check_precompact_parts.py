"""Facade contracts for the split PreCompact continuity hook."""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext


HOOK = Path(__file__).resolve().parents[1] / "check_precompact_continuity.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(HOOK))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestPrecompactPartsFacade(TestEnvContext):
    def test_fu144_facade_monkeypatch_reaches_extracted_helper(self):
        module = _load("precompact_parts_patch")
        self.addCleanup(sys.modules.pop, "precompact_parts_patch", None)
        with mock.patch.object(module, "_git", return_value="/resolved") as git:
            with mock.patch.object(
                module.os.path, "isdir", side_effect=lambda path: path == "/resolved"
            ):
                self.assertEqual(module._resolve_project_root("/unresolved"), "/resolved")
        git.assert_called_once_with(["rev-parse", "--show-toplevel"], "/unresolved")

    def test_fu144_facade_import_namespaces_are_independent(self):
        first = _load("precompact_parts_first")
        second = _load("precompact_parts_second")
        self.addCleanup(sys.modules.pop, "precompact_parts_first", None)
        self.addCleanup(sys.modules.pop, "precompact_parts_second", None)
        first._w6j_facade_probe = []
        first._w6j_facade_probe.append("first")
        self.assertNotIn("_w6j_facade_probe", second.__dict__)

    def test_fu144_extracted_function_has_real_source_file(self):
        module = _load("precompact_parts_source")
        self.addCleanup(sys.modules.pop, "precompact_parts_source", None)
        source = Path(inspect.getsourcefile(module._context_pct_from_sidecar))
        self.assertEqual(source.parent.name, "_precompact_parts")
        self.assertIn("def _context_pct_from_sidecar", inspect.getsource(module._context_pct_from_sidecar))
