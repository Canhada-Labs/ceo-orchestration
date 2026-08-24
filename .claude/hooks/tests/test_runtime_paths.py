"""Tests for _lib/runtime_paths.py — PLAN-182 W1 resolver contract.

Behavioral oracles only: every assertion exercises the resolver's
OUTPUT for a given env/path input. Grep-for-literal is not used as an
oracle anywhere (W1 check: "grep pelo literal nao e aceito como
oraculo").
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(_LIB.parent) not in sys.path:
    sys.path.insert(0, str(_LIB.parent))

from _lib import runtime_paths  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class TestProjectSlug(TestEnvContext):
    def test_native_derivation_slash_to_dash(self):
        self.assertEqual(
            runtime_paths.project_slug("/Users/u/my-repo"),
            "-Users-u-my-repo",
        )

    def test_single_leading_dash_current_harness_spelling(self):
        """The CURRENT harness spelling: single leading dash, never --."""
        slug = runtime_paths.project_slug("/private/tmp/x")
        self.assertTrue(slug.startswith("-private"))
        self.assertFalse(slug.startswith("--"))

    def test_dots_underscores_dashes_preserved(self):
        """ADR-001 amendment normalizes ONLY the separator."""
        self.assertEqual(
            runtime_paths.project_slug("/srv/my.app_v2-final"),
            "-srv-my.app_v2-final",
        )

    def test_basename_collision_impossible(self):
        """The cured defect: two checkouts sharing a basename collide
        under the bare-name convention; the path slug keeps them apart."""
        a = runtime_paths.project_slug("/Users/a/ceo-orchestration")
        b = runtime_paths.project_slug("/Users/b/ceo-orchestration")
        self.assertNotEqual(a, b)

    def test_relative_path_absolutized(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            slug = runtime_paths.project_slug("rel/dir")
            self.assertTrue(slug.startswith("-"))
            self.assertNotIn("/", slug)

    def test_symlink_spelling_pinned_not_canonicalized(self):
        """§Symlink honesty: abspath, NOT realpath (native alignment)."""
        # /var is a symlink to /private/var on macOS; on other hosts the
        # property still holds: the slug reflects the SPELLING given.
        slug = runtime_paths.project_slug("/var/example-proj")
        self.assertEqual(slug, "-var-example-proj")


class TestProjectDir(TestEnvContext):
    def test_claude_project_dir_wins_over_cwd(self):
        with mock.patch.dict(
            os.environ, {"CLAUDE_PROJECT_DIR": "/srv/proj-a"}, clear=False
        ):
            self.assertEqual(
                runtime_paths.project_dir(), Path("/srv/proj-a")
            )

    def test_cwd_fallback(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                runtime_paths.project_dir(),
                Path(os.path.abspath(os.getcwd())),
            )


class TestRuntimeStateDir(TestEnvContext):
    def test_native_override_wins_whole_directory(self):
        """CLAUDE_PROJECT_DIR_NATIVE: the ADR-001 override gains its
        first consumer (the spec fiction repaired)."""
        with mock.patch.dict(
            os.environ,
            {
                "CLAUDE_PROJECT_DIR_NATIVE": "/tmp/native-override",
                "CLAUDE_PROJECT_DIR": "/srv/proj-a",
                "HOME": "/home/u",
            },
            clear=False,
        ):
            self.assertEqual(
                runtime_paths.runtime_state_dir(),
                Path("/tmp/native-override"),
            )

    def test_default_is_home_projects_slug(self):
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CLAUDE_PROJECT_DIR_NATIVE",)
        }
        env["CLAUDE_PROJECT_DIR"] = "/srv/proj-a"
        env["HOME"] = "/home/u"
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                runtime_paths.runtime_state_dir(),
                Path("/home/u/.claude/projects/-srv-proj-a"),
            )

    def test_two_projects_two_dirs(self):
        """The isolation property the whole W1 exists to buy."""
        dirs = []
        for proj in ("/srv/proj-a", "/srv/proj-b"):
            env = {
                k: v
                for k, v in os.environ.items()
                if k != "CLAUDE_PROJECT_DIR_NATIVE"
            }
            env["CLAUDE_PROJECT_DIR"] = proj
            env["HOME"] = "/home/u"
            with mock.patch.dict(os.environ, env, clear=True):
                dirs.append(runtime_paths.runtime_state_dir())
        self.assertNotEqual(dirs[0], dirs[1])

    def test_never_resolves_to_legacy_literal(self):
        """NEGATIVE control for the cured class: for a project whose
        basename IS the legacy literal, the default resolution still
        lands on the path slug, not the bare-name dir."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "CLAUDE_PROJECT_DIR_NATIVE"
        }
        env["CLAUDE_PROJECT_DIR"] = "/srv/ceo-orchestration"
        env["HOME"] = "/home/u"
        with mock.patch.dict(os.environ, env, clear=True):
            got = runtime_paths.runtime_state_dir()
        self.assertNotEqual(got, runtime_paths.legacy_state_dir())
        self.assertEqual(
            got, Path("/home/u/.claude/projects/-srv-ceo-orchestration")
        )

    def test_legacy_state_dir_is_the_historical_location(self):
        """Migration tooling handle: pinned to the W0-measured literal."""
        with mock.patch.dict(os.environ, {"HOME": "/home/u"}, clear=False):
            self.assertEqual(
                runtime_paths.legacy_state_dir(),
                Path("/home/u/.claude/projects/ceo-orchestration"),
            )




_RESOLVER_FILE = Path(runtime_paths.__file__).resolve()


class TestCli(TestEnvContext):
    """PLAN-182 OQ-6 (S326) — the CLI is a thin printer over the functions."""

    def _run(self, *args, env=None, cwd=None):
        if env is None:
            env = self.subprocess_env()  # the sanctioned isolated-env builder
        return subprocess.run(
            [sys.executable, str(_RESOLVER_FILE), *args],
            env=env, cwd=cwd, capture_output=True, text=True, timeout=60,
        )

    def test_default_prints_state_dir_identical_to_the_function(self):
        env = self.subprocess_env()
        res = self._run(env=env)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        expected = str(Path(env["HOME"]) / ".claude" / "projects"
                       / runtime_paths.project_slug(env["CLAUDE_PROJECT_DIR"]))
        self.assertEqual(res.stdout, expected + "\n")
        self.assertEqual(res.stderr, "")

    def test_slug_and_project_dir_modes(self):
        env = self.subprocess_env()
        slug = self._run("--slug", env=env)
        pdir = self._run("--project-dir", env=env)
        self.assertEqual(slug.stdout.rstrip("\n"),
                         runtime_paths.project_slug(env["CLAUDE_PROJECT_DIR"]))
        self.assertEqual(pdir.stdout.rstrip("\n"),
                         os.path.abspath(env["CLAUDE_PROJECT_DIR"]))

    def test_project_flag_replaces_the_slug_input_only(self):
        env = self.subprocess_env()
        other = self._tmp_root / "other-repo"
        other.mkdir()
        res = self._run("--state-dir", "--project", str(other), env=env)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertEqual(
            res.stdout.rstrip("\n"),
            str(Path(env["HOME"]) / ".claude" / "projects" / runtime_paths.project_slug(other)))
        slug = self._run("--slug", "--project", str(other), env=env)
        self.assertEqual(slug.stdout.rstrip("\n"), runtime_paths.project_slug(other))

    def test_native_override_wins_for_state_dir_even_with_project(self):
        env = self.subprocess_env()
        native = self._tmp_root / "native-override"
        env["CLAUDE_PROJECT_DIR_NATIVE"] = str(native)
        res = self._run("--project", str(self._tmp_root / "x"), env=env)
        self.assertEqual(res.stdout.rstrip("\n"), str(native))
        # ...but the slug is untouched by the whole-dir override.
        slug = self._run("--slug", env=env)
        self.assertEqual(slug.stdout.rstrip("\n"),
                         runtime_paths.project_slug(env["CLAUDE_PROJECT_DIR"]))

    def test_usage_errors_exit_2_with_empty_stdout(self):
        for argv in (["--bogus"], ["--project"], ["--slug", "--state-dir"], ["--project", ""],
                     ["--project", "--slug"], ["--project", "--help"], ["--project", "-h"]):
            res = self._run(*argv)
            self.assertEqual(res.returncode, 2, msg="argv=%r" % (argv,))
            self.assertEqual(res.stdout, "", msg="argv=%r leaked prose on stdout" % (argv,))
            self.assertIn("usage:", res.stderr)
        helped = self._run("--help")
        self.assertEqual(helped.returncode, 0)
        self.assertIn("usage:", helped.stdout)

    def test_module_invocation_from_the_hooks_dir(self):
        env = self.subprocess_env()
        hooks_dir = _RESOLVER_FILE.parent.parent
        res = subprocess.run(
            [sys.executable, "-m", "_lib.runtime_paths", "--slug"],
            env=env, cwd=str(hooks_dir), capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertEqual(res.stdout.rstrip("\n"),
                         runtime_paths.project_slug(env["CLAUDE_PROJECT_DIR"]))

    def test_cli_keeps_the_module_a_leaf(self):
        """The resolver must stay importable from any hook: stdlib only, no
        ``_lib`` sibling imports (the CLI must not have smuggled one in)."""
        tree = ast.parse(_RESOLVER_FILE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertFalse((node.module or "").startswith("_lib"), ast.dump(node))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(alias.name.startswith("_lib"), alias.name)


if __name__ == "__main__":
    unittest.main()
