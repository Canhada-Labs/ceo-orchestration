"""PLAN-183: judge the census payload, not its implementation internals."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
HOOKS = ROOT / ".claude/hooks"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from _lib._shipped_path_census import census_shipped_paths  # noqa: E402


@pytest.fixture
def installation(tmp_path):
    installer = tmp_path / "scripts/install.sh"
    installer.parent.mkdir(parents=True)
    installer.write_text((ROOT / "scripts/install.sh").read_text(encoding="utf-8"),
                         encoding="utf-8")
    (tmp_path / ".claude/scripts").mkdir(parents=True)
    (tmp_path / ".claude/hooks/_lib").mkdir(parents=True)
    return tmp_path


def _package(repo, namespace, name):
    folder = repo / namespace / name
    folder.mkdir(parents=True)
    (folder / "__init__.py").write_text("", encoding="utf-8")
    return folder


def _entry(repo, namespace, text):
    source = repo / namespace / "entry.py"
    source.write_text(text, encoding="utf-8")
    return source


def test_real_installer_covers_recursive_lib_and_finds_existing_scripts_gap():
    census = census_shipped_paths(ROOT)
    assert census["installer"]["lib"].startswith("proven:")
    assert any(row["module"] == "_lib._contamination" for row in census["dependencies"])
    assert any(row["package"] == ".claude/scripts/detectors" for row in census["missing"])
    assert any(row["package"] == ".claude/scripts/optimizer" for row in census["missing"])
    assert not census["ok"]


def test_recursive_lib_package_delivered_for_from_and_import(installation):
    _package(installation, ".claude/hooks/_lib", "_pkg")
    _entry(installation, ".claude/scripts", "from _lib._pkg import part\nimport _lib._pkg\n")
    census = census_shipped_paths(installation)
    assert census["ok"], census
    assert len(census["dependencies"]) == 2
    assert {row["delivery"] for row in census["dependencies"]} == {"lib"}


def test_new_scripts_subpackage_not_shipped_by_top_level_glob(installation):
    _package(installation, ".claude/scripts", "new_package")
    _entry(installation, ".claude/scripts", "from new_package import worker\n")
    census = census_shipped_paths(installation)
    assert not census["ok"]
    assert [(row["module"], row["delivery"]) for row in census["missing"]] == [
        ("new_package", "scripts")]
    assert "top-level" in census["missing"][0]["reason"]


def test_removed_lib_copy_is_unproven_even_if_local_source_exists(installation):
    _package(installation, ".claude/hooks/_lib", "_pkg")
    _entry(installation, ".claude/scripts", "from _lib._pkg import worker\n")
    installer = installation / "scripts/install.sh"
    original = installer.read_text(encoding="utf-8")
    assert "  install_lib_selective\n" in original
    installer.write_text(original.replace("  install_lib_selective\n", "  : # mutant removed lib delivery\n", 1),
                         encoding="utf-8")
    census = census_shipped_paths(installation)
    assert not census["ok"]
    assert census["missing"] == []
    assert census["unproven"][0]["module"] == "_lib._pkg"
    assert "recursive" in census["unproven"][0]["reason"]


def test_missing_installer_and_invalid_ast_never_green(installation):
    _entry(installation, ".claude/hooks", "from . import sibling\n")
    broken = installation / ".claude/scripts/bad.py"
    broken.write_text("from (", encoding="utf-8")
    (installation / "scripts/install.sh").unlink()
    census = census_shipped_paths(installation)
    assert not census["ok"]
    assert any("AST unavailable" in row["reason"] for row in census["unproven"])
    assert any("relative import" in row["reason"] for row in census["unproven"])
    assert census["installer"]["lib"].startswith("unproven:")


def test_stdlib_and_external_are_not_local_dependencies(installation):
    _entry(installation, ".claude/scripts", "import os\nfrom pathlib import Path\nimport vendor_unknown\n")
    census = census_shipped_paths(installation)
    assert census["ok"], census
    assert census["dependencies"] == []
    assert census["missing"] == []


def test_hooks_local_package_not_recursive_and_missing_hooks_dispatch(installation):
    _package(installation, ".claude/hooks", "new_hooks_package")
    _entry(installation, ".claude/hooks", "import new_hooks_package.module\n")
    census = census_shipped_paths(installation)
    assert [row["package"] for row in census["missing"]] == [
        ".claude/hooks/new_hooks_package"]
    installer = installation / "scripts/install.sh"
    body = installer.read_text(encoding="utf-8")
    assert "\ninstall_hooks_selective\n" in body
    installer.write_text(body.replace("\ninstall_hooks_selective\n", "\n: # removed hooks invocation\n", 1),
                         encoding="utf-8")
    mutant = census_shipped_paths(installation)
    assert not mutant["ok"]
    assert any("top-level copy or invocation" in row["reason"]
               for row in mutant["unproven"])


def test_empty_root_is_unproven(tmp_path):
    result = census_shipped_paths(tmp_path)
    assert not result["ok"]
    assert any("installer unreadable" in row["reason"] for row in result["unproven"])
    assert any("no top-level Python entrypoints" in row["reason"]
               for row in result["unproven"])


def test_unprefixed_lib_import_from_scripts_and_hooks(installation):
    _package(installation, ".claude/hooks/_lib", "_pkg")
    _entry(installation, ".claude/scripts", "from _pkg import worker\n")
    _entry(installation, ".claude/hooks", "import _pkg.worker\n")
    result = census_shipped_paths(installation)
    assert result["ok"], result
    assert [row["delivery"] for row in result["dependencies"]] == ["lib", "lib"]


def test_excluded_and_symlink_packages_not_proven(installation):
    _package(installation, ".claude/hooks/_lib", "tests")
    outside = installation.parent / "external_package"
    outside.mkdir()
    (outside / "__init__.py").write_text("", encoding="utf-8")
    (installation / ".claude/hooks/_lib/external_package").symlink_to(outside,
                                                                       target_is_directory=True)
    _entry(installation, ".claude/scripts",
           "from _lib.tests import fake\nfrom _lib.external_package import fake\n")
    result = census_shipped_paths(installation)
    assert not result["ok"]
    assert result["missing"][0]["package"].endswith("/_lib/tests")
    assert "symlink" in result["unproven"][0]["reason"]
