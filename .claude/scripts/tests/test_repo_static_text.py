"""Cache de fixtures: leituras poupadas, invalidação e isolamento observáveis."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _root_plugin(pytestconfig):
    root = Path(__file__).resolve().parents[3] / "conftest.py"
    return next(plugin for plugin in pytestconfig.pluginmanager.get_plugins()
                if getattr(plugin, "__file__", None) == str(root))


def test_reuses_unchanged_text_without_sharing_mutable_json(tmp_path, pytestconfig):
    source = tmp_path / "settings.json"
    source.write_text('{"hooks": []}', encoding="utf-8")
    reader = _root_plugin(pytestconfig)._StaticRepoText([source])
    with patch.object(Path, "read_text", autospec=True, side_effect=Path.read_text) as reads:
        first = json.loads(reader(source))
        first["hooks"].append("local mutation")
        assert json.loads(reader(source)) == {"hooks": []}
        assert reads.call_count == 1


def test_same_size_edit_and_atomic_replace_invalidate(tmp_path, pytestconfig):
    source = tmp_path / "team.md"
    source.write_text("old", encoding="utf-8")
    reader = _root_plugin(pytestconfig)._StaticRepoText([source])
    assert reader(source) == "old"
    before = source.stat()
    source.write_text("new", encoding="utf-8")
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert reader(source) == "new"
    replacement = tmp_path / "replacement"
    replacement.write_text("end", encoding="utf-8")
    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
    replacement.replace(source)
    assert reader(source) == "end"


def test_missing_unreadable_and_invalid_sources_never_return_cached_text(tmp_path, pytestconfig):
    source = tmp_path / "team.md"
    source.write_text("original", encoding="utf-8")
    reader = _root_plugin(pytestconfig)._StaticRepoText([source])
    assert reader(source) == "original"
    source.unlink()
    with pytest.raises(FileNotFoundError):
        reader(source)
    source.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        reader(source)
    source.write_text("changed", encoding="utf-8")
    with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError):
            reader(source)
    assert reader(source) == "changed"


def test_changed_during_read_is_not_cached(tmp_path, pytestconfig):
    source = tmp_path / "frontend-team.md"
    source.write_text("old", encoding="utf-8")
    reader = _root_plugin(pytestconfig)._StaticRepoText([source])
    original = Path.read_text

    def changing_read(path, **kwargs):
        text = original(path, **kwargs)
        source.write_text("changed during read", encoding="utf-8")
        return text

    with patch.object(Path, "read_text", changing_read):
        assert reader(source) == "old"
    with patch.object(Path, "read_text", autospec=True, side_effect=original) as reads:
        assert reader(source) == "changed during read"
        assert reads.call_count == 1


def test_reader_rejects_undeclared_paths_and_symlink_targets(tmp_path, pytestconfig):
    source = tmp_path / "team.md"
    outside = tmp_path / "other.md"
    outside.write_text("outside", encoding="utf-8")
    reader = _root_plugin(pytestconfig)._StaticRepoText([source])
    with pytest.raises(ValueError):
        reader(outside)
    source.symlink_to(outside)
    with pytest.raises(ValueError):
        reader(source)


def test_fixture_opt_in_restores_reader_and_preserves_environment(pytestconfig, repo_static_text):
    plugin = _root_plugin(pytestconfig)
    original = object()
    module = SimpleNamespace(_USE_STATIC_REPO_TEXT=True, _read_repo_text=original)
    request = SimpleNamespace(module=module, getfixturevalue=lambda name: repo_static_text)
    before = dict(os.environ)
    fixture = plugin.repo_static_text_reader.__wrapped__(request)
    next(fixture)
    assert module._read_repo_text is repo_static_text
    fixture.close()
    assert module._read_repo_text is original
    assert dict(os.environ) == before
    module._USE_STATIC_REPO_TEXT = False
    fixture = plugin.repo_static_text_reader.__wrapped__(request)
    next(fixture)
    assert module._read_repo_text is original
    fixture.close()
