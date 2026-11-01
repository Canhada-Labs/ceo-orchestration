"""Compatibility of independently loaded reality-ledger facades."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "reality-ledger.py"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_facade_patch_reaches_detector_and_class(monkeypatch, tmp_path):
    module = load("ledger_patch")
    monkeypatch.setattr(module, "_is_excluded", lambda *args, **kwargs: True)
    (tmp_path / "x.py").write_text("pass")
    assert module._iter_python_files([tmp_path], repo_root=tmp_path) == []
    monkeypatch.setattr(module, "_EnvVarReadFinder", lambda: None)
    assert module._ast_collect_runtime_env_reads([tmp_path / "x.py"]) == {}


def test_independent_imports_and_class_methods(monkeypatch):
    first = load("ledger_first")
    second = load("ledger_second")
    first.DETECTOR_REGISTRY.clear()
    assert second.DETECTOR_REGISTRY
    monkeypatch.setattr(first, "ast", None)
    finder = second._EnvVarReadFinder()
    finder.visit(second.ast.parse("os.getenv('CEO_EXAMPLE')"))
    assert finder.read_vars == {"CEO_EXAMPLE"}
    assert first._EnvVarReadFinder.visit_Call.__globals__ is first.__dict__
    assert second._EnvVarReadFinder.visit_Call.__globals__ is second.__dict__


def test_excludes_extracted_implementation():
    module = load("ledger_exclusion")
    root = SCRIPT.parents[2]
    path = root / ".claude/hooks/_lib/_reality_ledger_parts/environment.py"
    assert module._is_excluded(path, repo_root=root)


def test_static_registry_uses_installed_exports_and_imports(tmp_path):
    module = load("ledger_registry")
    facade = tmp_path / "audit_emit.py"
    parts = tmp_path / "_audit_emit_parts"
    parts.mkdir()
    (parts / "actions.py").write_text(
        "from .renamed_source import _ACTIONS as _CORE\n"
        "__all__ = ('_KNOWN_ACTIONS',)\n_KNOWN_ACTIONS = _CORE | {'second'}\n"
    )
    (parts / "renamed_source.py").write_text("_ACTIONS = {'first'}\n")
    (parts / "actions_core.py").write_text("_ACTIONS = {'decoy'}\n")
    prefix = "from _lib._audit_emit_parts import install as bind\n"
    facade.write_text(prefix + "bind(globals(), ('actions',))\n")
    assert module._read_known_actions(facade) == {"first", "second"}
    facade.write_text(prefix + "bind(globals(), ('renamed_source',))\n")
    assert module._read_known_actions(facade) == set()
