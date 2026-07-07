"""
Unit tests for .claude/scripts/check-agents-md.py.

AGENTS.md (repo root) is the cross-LLM reviewer contract; the checker
flags drift between its repo-map / guarded-surfaces tables and the
on-disk tree. Stdlib-only, Python >= 3.9. The script itself reads only
--root (no env), but the test classes subclass TestEnvContext for
env-hygiene gate compliance (the tree forbids bare unittest.TestCase).
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check-agents-md.py"
REPO_ROOT = Path(__file__).resolve().parents[3]

# Ensure ``_lib.testing`` (TestEnvContext) is importable for env-isolation.
_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load():
    spec = importlib.util.spec_from_file_location("check_agents_md", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CAM = _load()

_MINIMAL_TEMPLATE = """# AGENTS.md — fixture

{repo_map_begin}

| Path | What it is |
|---|---|
{repo_map_rows}

{repo_map_end}

{guarded_begin}

| Path | Why guarded |
|---|---|
{guarded_rows}

{guarded_end}
"""


def _write_fixture(root: Path, repo_map_rows: str, guarded_rows: str) -> None:
    (root / "AGENTS.md").write_text(
        _MINIMAL_TEMPLATE.format(
            repo_map_begin=CAM.REPO_MAP_BEGIN,
            repo_map_end=CAM.REPO_MAP_END,
            guarded_begin=CAM.GUARDED_BEGIN,
            guarded_end=CAM.GUARDED_END,
            repo_map_rows=repo_map_rows,
            guarded_rows=guarded_rows,
        ),
        encoding="utf-8",
    )


def _run_main(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = CAM.main(argv)
    return rc, buf.getvalue()


class TestRealRepo(TestEnvContext):
    """The live freshness gate: the committed AGENTS.md must be clean."""

    def test_repo_agents_md_is_fresh(self):
        rc, out = _run_main(["--root", str(REPO_ROOT)])
        self.assertEqual(rc, 0, f"AGENTS.md drift against disk:\n{out}")
        self.assertIn("OK:", out)

    def test_repo_json_output_shape(self):
        rc, out = _run_main(["--root", str(REPO_ROOT), "--format", "json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["problem_count"], 0)
        self.assertEqual(payload["problems"], [])
        self.assertGreater(payload["checked_paths"], 0)


class TestFixtureRepo(TestEnvContext):
    def test_clean_fixture_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "real_dir").mkdir()
            (root / "guarded.md").write_text("x\n", encoding="utf-8")
            _write_fixture(
                root,
                repo_map_rows="| `real_dir/` | a real directory |",
                guarded_rows="| `guarded.md` | a real file |",
            )
            rc, out = _run_main(["--root", str(root)])
            self.assertEqual(rc, 0)
            self.assertIn("OK:", out)

    def test_missing_repo_map_dir_is_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "real_dir").mkdir()
            (root / "guarded.md").write_text("x\n", encoding="utf-8")
            _write_fixture(
                root,
                repo_map_rows=(
                    "| `real_dir/` | exists |\n"
                    "| `ghost_dir/` | does not exist |"
                ),
                guarded_rows="| `guarded.md` | a real file |",
            )
            rc, out = _run_main(["--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("DRIFT", out)
            self.assertIn("ghost_dir", out)

    def test_repo_map_entry_that_is_a_file_is_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "not_a_dir.txt").write_text("x\n", encoding="utf-8")
            (root / "guarded.md").write_text("x\n", encoding="utf-8")
            _write_fixture(
                root,
                repo_map_rows="| `not_a_dir.txt` | file, not dir |",
                guarded_rows="| `guarded.md` | a real file |",
            )
            rc, out = _run_main(["--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("not-a-dir", out)

    def test_missing_guarded_path_is_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "real_dir").mkdir()
            _write_fixture(
                root,
                repo_map_rows="| `real_dir/` | exists |",
                guarded_rows="| `phantom_guarded.py` | missing on disk |",
            )
            rc, out = _run_main(["--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("guarded-surfaces-missing", out)
            self.assertIn("phantom_guarded.py", out)

    def test_absolute_path_row_is_drift_not_false_green(self):
        # Codex pair-rail P2 (S261): an absolute path that exists on the HOST
        # must surface as drift — the contract is repo-root-relative only.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "real_dir").mkdir()
            (root / "guarded.md").write_text("x\n", encoding="utf-8")
            _write_fixture(
                root,
                repo_map_rows="| `real_dir/` | exists |",
                guarded_rows="| `/etc/hosts` | exists on host, not repo-relative |",
            )
            rc, out = _run_main(["--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("escapes-root", out)

    def test_dotdot_escape_row_is_drift_not_false_green(self):
        with tempfile.TemporaryDirectory() as td:
            outer = Path(td)
            (outer / "outside.md").write_text("x\n", encoding="utf-8")
            root = outer / "repo"
            root.mkdir()
            (root / "real_dir").mkdir()
            _write_fixture(
                root,
                repo_map_rows="| `real_dir/` | exists |",
                guarded_rows="| `../outside.md` | escapes the repo root |",
            )
            rc, out = _run_main(["--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("escapes-root", out)

    def test_missing_agents_md_is_drift(self):
        with tempfile.TemporaryDirectory() as td:
            rc, out = _run_main(["--root", td])
            self.assertEqual(rc, 1)
            self.assertIn("missing-agents-md", out)

    def test_missing_markers_is_drift_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "AGENTS.md").write_text(
                "# AGENTS.md\n\nno markers here\n", encoding="utf-8"
            )
            rc, out = _run_main(["--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("missing-markers", out)

    def test_empty_section_is_drift_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_fixture(root, repo_map_rows="", guarded_rows="")
            rc, out = _run_main(["--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("empty-section", out)

    def test_json_reports_problems(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "real_dir").mkdir()
            _write_fixture(
                root,
                repo_map_rows="| `real_dir/` | exists |",
                guarded_rows="| `phantom.py` | missing |",
            )
            rc, out = _run_main(["--root", str(root), "--format", "json"])
            self.assertEqual(rc, 1)
            payload = json.loads(out)
            self.assertEqual(payload["problem_count"], 1)
            self.assertEqual(payload["problems"][0]["path"], "phantom.py")

    def test_nonexistent_root_is_usage_error(self):
        rc, _ = _run_main(["--root", "/nonexistent/definitely/missing"])
        self.assertEqual(rc, 2)


class TestHelpers(TestEnvContext):
    def test_extract_paths_skips_header_and_separator(self):
        section = (
            "\n| Path | What |\n"
            "|---|---|\n"
            "| `a/b/` | thing |\n"
            "| plain cell no backticks | x |\n"
            "| `c.md` | file |\n"
        )
        self.assertEqual(CAM.extract_paths(section), ["a/b", "c.md"])

    def test_extract_section_absent_returns_none(self):
        self.assertIsNone(
            CAM.extract_section("no markers", CAM.REPO_MAP_BEGIN, CAM.REPO_MAP_END)
        )

    def test_extract_section_unterminated_returns_none(self):
        text = CAM.REPO_MAP_BEGIN + "\n| `x/` | y |\n"
        self.assertIsNone(
            CAM.extract_section(text, CAM.REPO_MAP_BEGIN, CAM.REPO_MAP_END)
        )


if __name__ == "__main__":
    unittest.main()
