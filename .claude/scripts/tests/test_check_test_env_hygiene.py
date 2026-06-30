"""Tests for check-test-env-hygiene.py (PLAN-019 P1-QA-3).

Stdlib only. Uses TestEnvContext for env isolation, so this test file is
itself mandate-compliant.
"""
from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


# --- bootstrap: load the target script by path (it's not a package) -------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".claude" / "scripts" / "check-test-env-hygiene.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "check_test_env_hygiene", _SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MOD = _load_module()


# Attempt to import TestEnvContext from the canonical shim so our own
# tests are mandate-compliant. Fall back to unittest.TestCase if the
# shim isn't importable in this environment (shouldn't happen in CI,
# but keeps us fail-soft).
try:
    from _lib.testing import TestEnvContext  # type: ignore
except Exception:  # pragma: no cover - defensive import-fallback
    _HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    from _lib.testing import TestEnvContext  # type: ignore


# ---------------------------------------------------------------------------
# Helper: build a fake repo tree under a tmp dir
# ---------------------------------------------------------------------------


class _FakeRepo(TestEnvContext):
    """Subclass-shareable helper: each test gets a clean repo fixture."""

    def setUp(self) -> None:  # noqa: D401
        super().setUp()
        self.repo = Path(tempfile.mkdtemp(prefix="ptest_env_hygiene_"))
        self.addCleanup(self._cleanup_repo)
        (self.repo / ".claude" / "hooks" / "tests").mkdir(parents=True)
        (self.repo / ".claude" / "scripts" / "tests").mkdir(parents=True)
        (self.repo / "tests").mkdir(parents=True)

    def _cleanup_repo(self) -> None:
        import shutil

        shutil.rmtree(self.repo, ignore_errors=True)

    def _write(self, rel: str, body: str) -> Path:
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        return p


# ---------------------------------------------------------------------------
# Clean-file acceptance
# ---------------------------------------------------------------------------


class TestCleanFile(_FakeRepo):
    def test_TestEnvContext_subclass_is_clean(self) -> None:
        self._write(
            ".claude/hooks/tests/test_ok.py",
            "import unittest\n"
            "from _lib.testing import TestEnvContext\n"
            "class TestX(TestEnvContext):\n"
            "    def test_ok(self):\n"
            "        self.assertTrue(True)\n",
        )
        rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 0)


# ---------------------------------------------------------------------------
# Bare unittest.TestCase flagging
# ---------------------------------------------------------------------------


class TestBareTestCase(_FakeRepo):
    def test_bare_TestCase_unittest_dotted(self) -> None:
        self._write(
            ".claude/hooks/tests/test_bad.py",
            "import unittest\n"
            "class TestY(unittest.TestCase):\n"
            "    pass\n",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        out = buf.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("bare-testcase", out)
        self.assertIn("test_bad.py", out)

    def test_bare_TestCase_from_import(self) -> None:
        self._write(
            ".claude/hooks/tests/test_bad2.py",
            "from unittest import TestCase\n"
            "class TestZ(TestCase):\n"
            "    pass\n",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 1)
        self.assertIn("bare-testcase", buf.getvalue())


# ---------------------------------------------------------------------------
# Direct env mutation
# ---------------------------------------------------------------------------


class TestEnvMutation(_FakeRepo):
    def test_direct_HOME_assignment_flagged(self) -> None:
        self._write(
            ".claude/hooks/tests/test_env.py",
            "import os\n"
            "from _lib.testing import TestEnvContext\n"
            "class TestA(TestEnvContext):\n"
            "    def test_x(self):\n"
            "        os.environ['HOME'] = '/tmp'\n",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 1)
        self.assertIn("env-write", buf.getvalue())
        self.assertIn("'HOME'", buf.getvalue())

    def test_direct_CLAUDE_PROJECT_DIR_flagged(self) -> None:
        self._write(
            ".claude/hooks/tests/test_env2.py",
            "import os\n"
            "from _lib.testing import TestEnvContext\n"
            "class TestA(TestEnvContext):\n"
            "    def test_x(self):\n"
            "        os.environ['CLAUDE_PROJECT_DIR'] = '/x'\n",
        )
        rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 1)

    def test_CEO_prefix_flagged(self) -> None:
        self._write(
            ".claude/hooks/tests/test_env3.py",
            "import os\n"
            "from _lib.testing import TestEnvContext\n"
            "class TestA(TestEnvContext):\n"
            "    def test_x(self):\n"
            "        os.environ['CEO_AUDIT_LOG_DIR'] = '/x'\n",
        )
        rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 1)

    def test_del_environ_flagged(self) -> None:
        self._write(
            ".claude/hooks/tests/test_env4.py",
            "import os\n"
            "from _lib.testing import TestEnvContext\n"
            "class TestA(TestEnvContext):\n"
            "    def test_x(self):\n"
            "        del os.environ['CEO_X']\n",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 1)
        self.assertIn("env-del", buf.getvalue())

    def test_unrelated_env_key_not_flagged(self) -> None:
        # 'PATH' is not a tracked key/prefix — should not fail.
        self._write(
            ".claude/hooks/tests/test_env5.py",
            "import os\n"
            "from _lib.testing import TestEnvContext\n"
            "class TestA(TestEnvContext):\n"
            "    def test_x(self):\n"
            "        os.environ['PATH'] = '/usr/bin'\n",
        )
        rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 0)

    def test_aug_assign_flagged(self) -> None:
        self._write(
            ".claude/hooks/tests/test_env6.py",
            "import os\n"
            "from _lib.testing import TestEnvContext\n"
            "class TestA(TestEnvContext):\n"
            "    def test_x(self):\n"
            "        os.environ['CEO_Y'] = os.environ.get('CEO_Y', '') + 'x'\n",
        )
        rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 1)

    def test_dynamic_key_flagged_conservatively(self) -> None:
        # Dynamic key — can't prove safe, so flag.
        self._write(
            ".claude/hooks/tests/test_env7.py",
            "import os\n"
            "from _lib.testing import TestEnvContext\n"
            "class TestA(TestEnvContext):\n"
            "    def test_x(self, key='CEO_Z'):\n"
            "        os.environ[key] = 'v'\n",
        )
        rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 1)


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


class TestAllowlist(_FakeRepo):
    def test_allowlisted_file_passes(self) -> None:
        self._write(
            ".claude/hooks/tests/test_bad.py",
            "import unittest\nclass TestY(unittest.TestCase):\n    pass\n",
        )
        (self.repo / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
        (self.repo / ".claude" / "scripts" / "test-env-hygiene-allowlist.yaml").write_text(
            "file: .claude/hooks/tests/test_bad.py\n  - bare-testcase\n",
            encoding="utf-8",
        )
        rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 0)

    def test_allowlist_covers_one_kind_but_not_another(self) -> None:
        # File has BOTH bare-testcase AND env-write; allowlist only
        # approves bare-testcase. Expect env-write to fail the check.
        self._write(
            ".claude/hooks/tests/test_mixed.py",
            "import os\n"
            "import unittest\n"
            "class TestY(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        os.environ['HOME'] = '/x'\n",
        )
        (self.repo / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
        (self.repo / ".claude" / "scripts" / "test-env-hygiene-allowlist.yaml").write_text(
            "file: .claude/hooks/tests/test_mixed.py\n  - bare-testcase\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 1)
        self.assertIn("env-write", buf.getvalue())
        self.assertNotIn("bare-testcase —", buf.getvalue())  # only unlisted reported

    def test_unknown_kind_in_allowlist_rejected(self) -> None:
        self._write(
            ".claude/hooks/tests/test_bad.py",
            "import unittest\nclass TestY(unittest.TestCase):\n    pass\n",
        )
        (self.repo / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
        (self.repo / ".claude" / "scripts" / "test-env-hygiene-allowlist.yaml").write_text(
            "file: .claude/hooks/tests/test_bad.py\n  - bogus-kind\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 2)
        self.assertIn("unknown violation kind", buf.getvalue())

    def test_malformed_allowlist_entry_rejected(self) -> None:
        (self.repo / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
        (self.repo / ".claude" / "scripts" / "test-env-hygiene-allowlist.yaml").write_text(
            "  - bare-testcase\n",  # entry before any file: header
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 2)

    def test_empty_file_header_rejected(self) -> None:
        (self.repo / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
        (self.repo / ".claude" / "scripts" / "test-env-hygiene-allowlist.yaml").write_text(
            "file:\n  - bare-testcase\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc, 2)


# ---------------------------------------------------------------------------
# --init flag
# ---------------------------------------------------------------------------


class TestInitFlag(_FakeRepo):
    def test_init_creates_allowlist_from_scan(self) -> None:
        self._write(
            ".claude/hooks/tests/test_bad.py",
            "import unittest\n"
            "class TestX(unittest.TestCase):\n"
            "    pass\n",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _MOD.main(["--repo-root", str(self.repo), "--init"])
        self.assertEqual(rc, 0)
        allowlist = self.repo / ".claude" / "scripts" / "test-env-hygiene-allowlist.yaml"
        self.assertTrue(allowlist.exists())
        body = allowlist.read_text(encoding="utf-8")
        self.assertIn("file: .claude/hooks/tests/test_bad.py", body)
        self.assertIn("- bare-testcase", body)

    def test_init_and_then_check_is_clean(self) -> None:
        self._write(
            ".claude/hooks/tests/test_bad.py",
            "import os\n"
            "import unittest\n"
            "class TestX(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        os.environ['HOME'] = '/tmp'\n",
        )
        rc = _MOD.main(["--repo-root", str(self.repo), "--init"])
        self.assertEqual(rc, 0)
        rc2 = _MOD.main(["--repo-root", str(self.repo)])
        self.assertEqual(rc2, 0)

    def test_init_regenerates_overwriting_prior_state(self) -> None:
        # Seed the allowlist with a bogus entry then re-init; the bogus
        # entry should disappear because --init replaces the file.
        allowlist = self.repo / ".claude" / "scripts" / "test-env-hygiene-allowlist.yaml"
        allowlist.parent.mkdir(parents=True, exist_ok=True)
        allowlist.write_text(
            "file: nonexistent/file.py\n  - bare-testcase\n", encoding="utf-8"
        )
        self._write(
            ".claude/hooks/tests/test_bad.py",
            "import unittest\nclass TestX(unittest.TestCase): pass\n",
        )
        rc = _MOD.main(["--repo-root", str(self.repo), "--init"])
        self.assertEqual(rc, 0)
        body = allowlist.read_text(encoding="utf-8")
        self.assertNotIn("nonexistent/file.py", body)
        self.assertIn("test_bad.py", body)


# ---------------------------------------------------------------------------
# Verbose flag
# ---------------------------------------------------------------------------


class TestVerbose(_FakeRepo):
    def test_verbose_lists_allowed_and_violating_files(self) -> None:
        self._write(
            ".claude/hooks/tests/test_bad.py",
            "import unittest\nclass TestX(unittest.TestCase): pass\n",
        )
        (self.repo / ".claude" / "scripts" / "test-env-hygiene-allowlist.yaml").write_text(
            "file: .claude/hooks/tests/test_bad.py\n  - bare-testcase\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _MOD.main(["--repo-root", str(self.repo), "--verbose"])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("[ALLOW]", out)


# ---------------------------------------------------------------------------
# End-to-end: scan the real repo, expect PASS with the shipped allowlist.
# ---------------------------------------------------------------------------


class TestRepoBaseline(TestEnvContext):
    """The repo's committed allowlist MUST pass the check as-of today."""

    def test_shipped_allowlist_is_current(self) -> None:
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = _MOD.main(["--repo-root", str(_REPO_ROOT)])
        self.assertEqual(
            rc,
            0,
            msg=f"shipped allowlist drifted — stdout:\n{buf_out.getvalue()}\n"
            f"stderr:\n{buf_err.getvalue()}",
        )


# ---------------------------------------------------------------------------
# Parse error / bad syntax is fail-soft
# ---------------------------------------------------------------------------


class TestFailSoft(_FakeRepo):
    def test_syntax_error_file_skipped(self) -> None:
        self._write(
            ".claude/hooks/tests/test_broken.py",
            "def oops(:\n    pass\n",  # bad syntax
        )
        buf_err = io.StringIO()
        with redirect_stderr(buf_err):
            rc = _MOD.main(["--repo-root", str(self.repo)])
        # Clean repo otherwise → rc 0, warning on stderr.
        self.assertEqual(rc, 0)
        self.assertIn("syntax error", buf_err.getvalue())


if __name__ == "__main__":
    unittest.main()
