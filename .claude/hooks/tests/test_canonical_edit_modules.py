"""Behavior across the canonical hook's extracted component boundaries."""
from __future__ import annotations

import builtins
import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext


_HOOK = Path(__file__).resolve().parents[1] / "check_canonical_edit.py"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestComponentCompatibility(TestEnvContext):
    def test_guard_changes_affect_only_the_owning_import(self):
        first = _load("canonical_components_first")
        second = _load("canonical_components_second")
        target = str(self.project_dir / "local.cfg")
        with mock.patch.object(first, "_CANONICAL_GUARDS_FOLDED", ["local.cfg"]), \
                mock.patch.object(first, "_CANONICAL_PREFIXES_FOLDED", {"local.cfg"}):
            blocked = json.loads(first.decide(file_path=target, repo_root=self.project_dir))
            allowed = json.loads(second.decide(file_path=target, repo_root=self.project_dir))
        self.assertEqual(blocked["decision"], "block")
        self.assertIn("local.cfg", blocked["reason"])
        self.assertEqual(allowed, {})

    def test_signature_cache_uses_live_dependencies_and_stays_per_import(self):
        first = _load("canonical_cache_first")
        second = _load("canonical_cache_second")
        sentinel = self.project_dir / "approved.md"
        key = ("same-sentinel",)
        with mock.patch.object(first, "_compute_sig_cache_key", return_value=key), \
                mock.patch.object(second, "_compute_sig_cache_key", return_value=key), \
                mock.patch.object(first, "_verify_signature_rail", return_value=True) as accept, \
                mock.patch.object(second, "_verify_signature_rail", return_value=False) as reject:
            self.assertTrue(first._signature_rail_ok(sentinel))
            self.assertTrue(first._signature_rail_ok(sentinel))
            self.assertFalse(second._signature_rail_ok(sentinel))
        self.assertEqual(first._SIG_VERIFY_CACHE, {key: True})
        self.assertEqual(second._SIG_VERIFY_CACHE, {key: False})
        accept.assert_called_once_with(sentinel)
        reject.assert_called_once_with(sentinel)

    def test_missing_component_emits_allow_and_infrastructure_breadcrumb(self):
        original_import = builtins.__import__

        def unavailable(name, *args, **kwargs):
            if name == "_lib.canonical_edit":
                raise ImportError("component unavailable")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=unavailable):
            module = _load("canonical_component_missing")
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(module.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), {})
        self.assertIn("component import unavailable (ImportError)", errors.getvalue())
