"""Tests for _lib/runtime_paths.py — PLAN-182 W1 resolver contract.

Behavioral oracles only: every assertion exercises the resolver's
OUTPUT for a given env/path input. Grep-for-literal is not used as an
oracle anywhere (W1 check: "grep pelo literal nao e aceito como
oraculo").
"""

from __future__ import annotations

import os
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


if __name__ == "__main__":
    unittest.main()
