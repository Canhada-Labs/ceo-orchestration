"""Unit tests for `check_translations_drift.py` — PLAN-013 Phase B.7.

Subclasses `TestEnvContext` from `_lib/testing.py` per CLAUDE.md §5
Critical Rules + PLAN-013 consensus §S11. Every test runs in an
isolated tmp project_dir.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_ROOT / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = SCRIPT_ROOT / "scripts" / "check_translations_drift.py"


def _git_init(tmpdir: Path) -> None:
    (tmpdir / ".git").mkdir(exist_ok=True)


def _write_pairs_yaml(tmpdir: Path, pairs: list) -> Path:
    path = tmpdir / "pairs.yaml"
    lines = []
    for src, mir in pairs:
        lines.append(f"- source: {src}")
        lines.append(f"  mirror: {mir}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _run(tmpdir: Path, pairs_file: str, json_out: bool = False):
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--repo-root",
        str(tmpdir),
        "--pairs-file",
        pairs_file,
    ]
    if json_out:
        cmd.append("--json")
    return subprocess.run(cmd, capture_output=True, text=True)


class TestTranslationsDrift(TestEnvContext):
    def _setup(self):
        _git_init(self.project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def test_matching_pair_passes(self) -> None:
        self._setup()
        (self.project_dir / "source.md").write_text(
            "# Title\n\n> **EN:** [mirror.md](mirror.md)\n\n## Section\n\n```bash\ncmd\n```\n",
            encoding="utf-8",
        )
        (self.project_dir / "mirror.md").write_text(
            "# Titulo\n\n> **PT:** [source.md](source.md)\n\n## Secao\n\n```bash\ncmd\n```\n",
            encoding="utf-8",
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("source.md", "mirror.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_heading_count_drift_fails(self) -> None:
        self._setup()
        (self.project_dir / "a.md").write_text(
            "# A\n## B\n> cross mirror.md\n", encoding="utf-8"
        )
        (self.project_dir / "b.md").write_text(
            "# A\n> cross a.md\n", encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("a.md", "b.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("heading count drift", result.stdout)

    def test_code_fence_count_drift_fails(self) -> None:
        self._setup()
        (self.project_dir / "a.md").write_text(
            "# T\n> cross b.md\n\n```py\nx\n```\n\n```py\ny\n```\n",
            encoding="utf-8",
        )
        (self.project_dir / "b.md").write_text(
            "# T\n> cross a.md\n\n```py\nx\n```\n", encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("a.md", "b.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("code-fence count drift", result.stdout)

    def test_line_delta_over_threshold_fails(self) -> None:
        self._setup()
        small = "\n".join([f"line {i}" for i in range(10)])
        large = "\n".join([f"line {i}" for i in range(30)])
        (self.project_dir / "a.md").write_text(
            f"# T\n> cross b.md\n{small}\n", encoding="utf-8"
        )
        (self.project_dir / "b.md").write_text(
            f"# T\n> cross a.md\n{large}\n", encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("a.md", "b.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("line-count delta", result.stdout)

    def test_line_delta_within_tolerance_passes(self) -> None:
        self._setup()
        (self.project_dir / "a.md").write_text(
            "# T\n> cross b.md\n" + "x\n" * 100, encoding="utf-8"
        )
        (self.project_dir / "b.md").write_text(
            "# T\n> cross a.md\n" + "y\n" * 105, encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("a.md", "b.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
        )
        self.assertEqual(result.returncode, 0)

    def test_missing_cross_link_fails(self) -> None:
        self._setup()
        (self.project_dir / "a.md").write_text(
            "# T\n## S\n", encoding="utf-8"
        )
        (self.project_dir / "b.md").write_text(
            "# T\n## S\n", encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("a.md", "b.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("cross-link", result.stdout)

    def test_missing_source_file_reports(self) -> None:
        self._setup()
        (self.project_dir / "b.md").write_text(
            "# T\n> cross a.md\n", encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("a.md", "b.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing source", result.stdout)

    def test_missing_mirror_file_reports(self) -> None:
        self._setup()
        (self.project_dir / "a.md").write_text(
            "# T\n> cross b.md\n", encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("a.md", "b.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing mirror", result.stdout)

    def test_empty_pairs_file_returns_2(self) -> None:
        self._setup()
        (self.project_dir / "pairs.yaml").write_text(
            "# empty\n", encoding="utf-8"
        )
        result = _run(self.project_dir, "pairs.yaml")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no pairs found", result.stderr)

    def test_json_output_structure(self) -> None:
        self._setup()
        (self.project_dir / "a.md").write_text(
            "# T\n> cross b.md\n## S\n", encoding="utf-8"
        )
        (self.project_dir / "b.md").write_text(
            "# T\n> cross a.md\n## S\n", encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir, [("a.md", "b.md")]
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
            json_out=True,
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("results", data)
        self.assertIn("drift", data)
        self.assertFalse(data["drift"])
        self.assertEqual(len(data["results"]), 1)
        self.assertTrue(data["results"][0]["ok"])

    def test_multiple_pairs_report_independently(self) -> None:
        self._setup()
        (self.project_dir / "a.md").write_text(
            "# T\n> cross b.md\n", encoding="utf-8"
        )
        (self.project_dir / "b.md").write_text(
            "# T\n> cross a.md\n", encoding="utf-8"
        )
        (self.project_dir / "c.md").write_text(
            "# T\n## S\n> cross d.md\n", encoding="utf-8"
        )
        (self.project_dir / "d.md").write_text(
            "# T\n> cross c.md\n", encoding="utf-8"
        )
        pairs = _write_pairs_yaml(
            self.project_dir,
            [("a.md", "b.md"), ("c.md", "d.md")],
        )
        result = _run(
            self.project_dir,
            pairs.relative_to(self.project_dir).as_posix(),
            json_out=True,
        )
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertTrue(data["results"][0]["ok"])
        self.assertFalse(data["results"][1]["ok"])


if __name__ == "__main__":
    import unittest
    unittest.main()
