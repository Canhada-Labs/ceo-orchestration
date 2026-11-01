"""Facade-binding regressions for the split policy engine."""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext


POLICY = Path(__file__).resolve().parents[1] / "_lib" / "policy.py"

_DOCUMENT = '''schema: "policy-dsl/v1"
id: facade-test
description: "Facade test"
kind: deny_list
defaults:
  decision: allow
rules: []
error_model:
  reasons: {}
'''


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, POLICY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestPolicyPartsFacade(TestEnvContext):
    def test_fu144_facade_monkeypatch_reaches_extracted_load(self):
        module = _load("_lib.policy_parts_patch")
        self.addCleanup(sys.modules.pop, "_lib.policy_parts_patch", None)
        policy_path = self.project_dir / "policy.yaml"
        policy_path.write_text(_DOCUMENT, encoding="utf-8")
        with mock.patch.object(module, "_estimate_size", return_value=2 ** 30):
            with self.assertRaises(module.PolicyLoadError) as raised:
                module.load(policy_path)
        self.assertEqual(raised.exception.error_kind, "size_limit")

    def test_fu144_policy_imports_do_not_share_parser_class_state(self):
        first = _load("_lib.policy_parts_first")
        second = _load("_lib.policy_parts_second")
        self.addCleanup(sys.modules.pop, "_lib.policy_parts_first", None)
        self.addCleanup(sys.modules.pop, "_lib.policy_parts_second", None)
        first._YamlParser._facade_probe = object()
        self.assertFalse(hasattr(second._YamlParser, "_facade_probe"))

    def test_fu144_parser_method_keeps_real_part_source(self):
        module = _load("_lib.policy_parts_inspect")
        self.addCleanup(sys.modules.pop, "_lib.policy_parts_inspect", None)
        source_path = Path(inspect.getsourcefile(module._YamlParser._parse_block_mapping))
        self.assertEqual(source_path.name, "yaml_blocks.py")
        self.assertIn(
            "def _parse_block_mapping",
            inspect.getsource(module._YamlParser._parse_block_mapping),
        )
