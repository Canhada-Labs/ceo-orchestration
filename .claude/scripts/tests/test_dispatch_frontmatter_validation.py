"""PLAN-137 A3-parse — fail-closed agent frontmatter validation tests.

Covers the promoted-from-dead-code validator in
``.claude/scripts/generate-dispatch.py``:

  * reject-path: malformed maxTurns / isolation / skills values are rejected
    by ``validate_frontmatter`` AND by the ``--validate`` CLI (exit 1).
  * accept-path: valid native fields AND the no-new-fields case (the 13 real
    agents today) validate cleanly (0 errors, ``--validate`` exit 0).
  * regression: ``render_dispatch_md`` output is UNCHANGED whether or not an
    entry carries the new fields — they must NOT leak into the byte-frozen
    ``_dispatch.md`` table (otherwise CI ``--check`` goes stale).

Env-hygiene: no test mutates ``os.environ``. Subprocess invocations pass an
explicit ``env`` dict copy with a per-test tmp ``CLAUDE_PROJECT_DIR``; the
in-process tests call the loaded module functions directly with no env reads.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "generate-dispatch.py"

# Ensure ``_lib.testing`` (TestEnvContext) is importable for env-isolation —
# the test-env-hygiene gate (scan root .claude/scripts/tests) rejects a bare
# unittest.TestCase base; every TestCase here subclasses TestEnvContext.
_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    """Load generate-dispatch.py by path (hyphenated name not importable).

    The module is registered in ``sys.modules`` BEFORE ``exec_module`` so the
    ``@dataclass`` decorator can resolve ``cls.__module__`` during class
    creation — on Python 3.9 ``dataclasses._is_type`` does
    ``sys.modules.get(cls.__module__).__dict__`` and raises AttributeError if
    the module is absent from the registry.
    """
    spec = importlib.util.spec_from_file_location("generate_dispatch", str(SCRIPT))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_MOD = _load_module()


def _write_agent(agents_dir: Path, slug: str, frontmatter_body: str) -> Path:
    """Materialize a minimal agent .md file with the given frontmatter body."""
    agents_dir.mkdir(parents=True, exist_ok=True)
    content = "---\n{}\n---\n\n# {}\n\nbody\n".format(frontmatter_body, slug)
    path = agents_dir / "{}.md".format(slug)
    path.write_text(content, encoding="utf-8")
    return path


def _run_validate(project_dir: Path):
    """Invoke `generate-dispatch.py --validate` with CLAUDE_PROJECT_DIR=tmp.

    Passes an explicit env copy — never mutates os.environ.
    """
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--validate"],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(project_dir),
        env=env,
    )


class ValidateFrontmatterRejectTest(TestEnvContext):
    """In-process reject-path: malformed values produce errors."""

    def test_max_turns_non_integer_rejected(self):
        errs = _MOD.validate_frontmatter({"maxTurns": "abc"}, "bad")
        self.assertTrue(errs)
        self.assertIn("maxTurns", errs[0])

    def test_max_turns_zero_rejected(self):
        errs = _MOD.validate_frontmatter({"maxTurns": "0"}, "bad")
        self.assertTrue(errs, msg="0 is not positive")

    def test_max_turns_negative_rejected(self):
        errs = _MOD.validate_frontmatter({"maxTurns": "-1"}, "bad")
        self.assertTrue(errs)

    def test_max_turns_float_rejected(self):
        errs = _MOD.validate_frontmatter({"maxTurns": "3.5"}, "bad")
        self.assertTrue(errs, msg="3.5 is not an integer")

    def test_isolation_bogus_rejected(self):
        errs = _MOD.validate_frontmatter({"isolation": "bogus"}, "bad")
        self.assertTrue(errs)
        self.assertIn("isolation", errs[0])

    def test_skills_scalar_rejected(self):
        # parse_yaml_simple yields a bare string for `skills: foo`.
        errs = _MOD.validate_frontmatter({"skills": "foo"}, "bad")
        self.assertTrue(errs)
        self.assertIn("skills", errs[0])


class ValidateFrontmatterAcceptTest(TestEnvContext):
    """In-process accept-path: valid + absent fields produce no errors."""

    def test_all_valid_fields_accepted(self):
        fm = {"maxTurns": "5", "isolation": "worktree", "skills": ["a", "b"]}
        self.assertEqual(_MOD.validate_frontmatter(fm, "good"), [])

    def test_isolation_none_accepted(self):
        self.assertEqual(
            _MOD.validate_frontmatter({"isolation": "none"}, "good"), []
        )

    def test_no_new_fields_accepted(self):
        # The 13 real agents carry NONE of these today — must stay valid.
        fm = {"name": "x", "version": "v1", "description": "d"}
        self.assertEqual(_MOD.validate_frontmatter(fm, "real"), [])


class ValidateCliRejectTest(TestEnvContext):
    """Subprocess reject-path: --validate exits 1 on a malformed file."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="test-fm-validate-reject-")
        self.addCleanup(self._cleanup)
        self.project_dir = Path(self._tmp)
        self.agents_dir = self.project_dir / ".claude" / "agents"

    def _cleanup(self):
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_cli_rejects_bad_max_turns(self):
        _write_agent(
            self.agents_dir,
            "bad-turns",
            "name: bad-turns\nversion: v1\ndescription: d\nmaxTurns: abc",
        )
        result = _run_validate(self.project_dir)
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("maxTurns", result.stderr)

    def test_cli_rejects_negative_max_turns(self):
        _write_agent(
            self.agents_dir,
            "neg-turns",
            "name: neg-turns\nversion: v1\ndescription: d\nmaxTurns: -1",
        )
        result = _run_validate(self.project_dir)
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)

    def test_cli_rejects_bad_isolation(self):
        _write_agent(
            self.agents_dir,
            "bad-iso",
            "name: bad-iso\nversion: v1\ndescription: d\nisolation: bogus",
        )
        result = _run_validate(self.project_dir)
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("isolation", result.stderr)

    def test_cli_rejects_scalar_skills(self):
        _write_agent(
            self.agents_dir,
            "bad-skills",
            "name: bad-skills\nversion: v1\ndescription: d\nskills: justone",
        )
        result = _run_validate(self.project_dir)
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("skills", result.stderr)


class ValidateCliAcceptTest(TestEnvContext):
    """Subprocess accept-path: --validate exits 0 on valid / no-field files."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="test-fm-validate-accept-")
        self.addCleanup(self._cleanup)
        self.project_dir = Path(self._tmp)
        self.agents_dir = self.project_dir / ".claude" / "agents"

    def _cleanup(self):
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_cli_accepts_valid_fields(self):
        _write_agent(
            self.agents_dir,
            "good",
            "name: good\nversion: v1\ndescription: d\n"
            "maxTurns: 5\nisolation: worktree\nskills: [a, b]",
        )
        result = _run_validate(self.project_dir)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_cli_accepts_no_new_fields(self):
        # Mirrors the real agents (none carry the new fields).
        _write_agent(
            self.agents_dir,
            "plain",
            "name: plain\nversion: v1\ndescription: d\ntools: [Read, Grep]",
        )
        result = _run_validate(self.project_dir)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


class RenderRegressionTest(TestEnvContext):
    """Regression: the new fields must NOT leak into _dispatch.md output."""

    def _entry(self, **overrides):
        base = dict(
            slug="x",
            name="X",
            version="v1",
            description="desc",
            tools=["Read"],
            skill_path=None,
            skill_hash=None,
            model="claude-sonnet-4-6",
            skills=[],
            max_turns=None,
            isolation="",
        )
        base.update(overrides)
        return _MOD.AgentEntry(**base)

    def test_render_identical_with_and_without_new_fields(self):
        without = self._entry()
        with_fields = self._entry(
            skills=["alpha", "beta"], max_turns=9, isolation="worktree"
        )
        out_without = _MOD.render_dispatch_md([without])
        out_with = _MOD.render_dispatch_md([with_fields])
        self.assertEqual(
            out_without,
            out_with,
            msg="new native fields leaked into the dispatch table",
        )

    def test_render_does_not_mention_new_field_names(self):
        out = _MOD.render_dispatch_md(
            [self._entry(skills=["s"], max_turns=3, isolation="none")]
        )
        self.assertNotIn("maxTurns", out)
        self.assertNotIn("isolation", out)
        # The literal skill token must not appear in the rendered table.
        self.assertNotIn("alpha", out)


if __name__ == "__main__":
    unittest.main()
