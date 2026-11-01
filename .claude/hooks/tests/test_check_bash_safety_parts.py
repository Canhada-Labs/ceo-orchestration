"""Facade contracts for the extracted Bash-safety declarations."""
from __future__ import annotations

import builtins
import importlib.util
import inspect
import sys
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext


HOOK = Path(__file__).resolve().parents[1] / "check_bash_safety.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, str(HOOK))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestBashSafetyPartsFacade(TestEnvContext):
    def test_facade_monkeypatch_reaches_extracted_decider(self) -> None:
        module = _load("bash_safety_parts_patch")
        self.addCleanup(sys.modules.pop, "bash_safety_parts_patch", None)
        with mock.patch.object(module, "_check_rm_rf", return_value="probe block"):
            decision = module.decide_command("rm -rf disposable")
        self.assertFalse(decision.allow)
        self.assertEqual(decision.reason, "probe block")

    def test_extracted_function_remains_inspectable(self) -> None:
        module = _load("bash_safety_parts_inspect")
        self.addCleanup(sys.modules.pop, "bash_safety_parts_inspect", None)
        source_path = Path(inspect.getsourcefile(module._rewrite_git_push_force))
        self.assertEqual(source_path.name, "rewrite_citation.py")
        self.assertIn("def _rewrite_git_push_force", inspect.getsource(module._rewrite_git_push_force))

    def test_two_facade_imports_do_not_share_mutable_globals(self) -> None:
        first = _load("bash_safety_parts_first")
        sentinel = "_w6c_bash_shared_namespace"
        self.assertFalse(hasattr(builtins, sentinel))
        setattr(builtins, sentinel, first.__dict__)
        self.addCleanup(delattr, builtins, sentinel)
        second = _load("bash_safety_parts_second")
        self.addCleanup(sys.modules.pop, "bash_safety_parts_first", None)
        self.addCleanup(sys.modules.pop, "bash_safety_parts_second", None)
        first._E3_INTERPRETER_C_FLAGS["probe"] = ("-x",)
        self.assertNotIn("probe", second._E3_INTERPRETER_C_FLAGS)
        self.assertIsNot(first._E3_INTERPRETER_C_FLAGS, second._E3_INTERPRETER_C_FLAGS)
