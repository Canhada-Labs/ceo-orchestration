"""Focused regressions for the release-hold upgrade examples."""
from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path

from _lib.testing import TestEnvContext
from _subprocess_helpers import run_in_process_group


REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL = REPO_ROOT / "INSTALL.md"
SITES = REPO_ROOT / ".claude" / "scripts" / "local" / "_release_bump_sites.py"


def _release() -> str:
    """The release the live INSTALL.md example names: `release.sh bump` rewrites it to VERSION."""
    return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _load_sites():
    spec = importlib.util.spec_from_file_location("fu144_release_sites", str(SITES))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_upgrade(source: Path, target: Path, ref: str, env):
    return run_in_process_group(
        [
            "bash", str(source / "scripts" / "upgrade.sh"), str(target),
            "--pin", ref, "--dry-run", "--allow-old-claude-code",
        ],
        cwd=str(source), env=env, capture_output=True, text=True, timeout=30,
    )


def _git(repo: Path, env, *args: str):
    return run_in_process_group(
        ["git", *args], cwd=str(repo), env=env, timeout=15,
        capture_output=True, text=True, check=True,
    )


def _make_source(root: Path, env, ordinal: int, release: str) -> Path:
    source = root / ("source-%d" % ordinal)
    (source / "scripts").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "scripts" / "upgrade.sh", source / "scripts")
    (source / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(source, env, "init", "-q")
    _git(source, env, "config", "user.name", "Release Test")
    _git(source, env, "config", "user.email", "release-test@example.invalid")
    _git(source, env, "add", ".")
    _git(source, env, "commit", "-q", "-m", "fixture")
    _git(source, env, "tag", "v%s-rc.1" % release)
    if ordinal == 2:
        _git(source, env, "tag", "v%s-rc.2" % release)
    return source


class TestFu144ReleaseExamples(TestEnvContext):
    """The documented refs remain valid before and after the GA promotion."""

    def test_fu144_install_pin_examples_cover_rc_hold_and_ga(self):
        release = _release()
        self.assertRegex(release, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        ga = "v%s" % release
        rc_glob = "%s-rc.*" % ga
        text = INSTALL.read_text(encoding="utf-8")
        self.assertIn("git tag --list '%s' --sort=-v:refname" % rc_glob, text)
        self.assertIn("--pin %s" % ga, text)
        env = dict(os.environ)
        env["TMPDIR"] = str(self._tmp_root)
        for ordinal in (1, 2):
            source = _make_source(self._tmp_root, env, ordinal, release)
            target = self.project_dir / ("adopter-%d" % ordinal)
            target.mkdir()
            resolved = _git(
                source, env, "tag", "--list", rc_glob, "--sort=-v:refname"
            )
            ref = resolved.stdout.splitlines()[0]
            self.assertEqual(ref, "%s-rc.%d" % (ga, ordinal))
            missing = run_in_process_group(
                ["git", "rev-parse", "--verify", ga], cwd=str(source),
                env=env, timeout=15, capture_output=True, text=True,
            )
            self.assertNotEqual(missing.returncode, 0)
            rc_head = _git(source, env, "rev-parse", ref).stdout.strip()
            proc = _run_upgrade(source, target, ref, env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("Dry-run: diff between current source and --pin %s" % ref, proc.stdout)
            _git(source, env, "tag", ga)
            self.assertEqual(_git(source, env, "rev-parse", ga).stdout.strip(), rc_head)
            proc = _run_upgrade(source, target, ga, env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


def test_fu144_bump_keeps_rc_and_ga_examples_on_same_release(tmp_path):
    """The shared version matcher must rewrite both documented pin references."""
    repo = tmp_path / "repo"
    repo.mkdir()
    install = repo / "INSTALL.md"
    install.write_text(
        "git tag --list 'v1.4.2-rc.*'\n--pin v1.4.2\n", encoding="utf-8"
    )
    module = _load_sites()
    assert module.bump("1.4.3", "2026-11-01", root=str(repo)) == 1
    text = install.read_text(encoding="utf-8")
    assert "git tag --list 'v1.4.3-rc.*'" in text
    assert "--pin v1.4.3" in text
