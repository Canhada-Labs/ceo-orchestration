"""check-doc-skill-paths.sh unit tests.

PLAN-112-FOLLOWUP-install-md-skill-path W3 / AC5 — covers the
broken-skill-path doc gate that closes F-4.2 (INSTALL.md once cited
`.claude/skills/ceo-orchestration/SKILL.md`, missing the `core/` tier).

Cases (AC5): valid path passes / placeholder skipped / broken path
fails / allowlisted entry skipped. Plus a guard that the REAL repo docs
currently resolve (regression sentinel for the L262 fix).
"""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "local" / "check-doc-skill-paths.sh"


def _run(root: Path | None = None, allowlist: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if root is not None:
        env["CHECK_DOC_SKILL_PATHS_ROOT"] = str(root)
    if allowlist is not None:
        env["CHECK_DOC_SKILL_PATHS_ALLOWLIST"] = allowlist
    return subprocess.run(
        ["bash", str(SCRIPT), "--quiet"],
        capture_output=True, text=True, timeout=30, env=env,
    )


def _scaffold(root: Path, *, install_ref: str) -> None:
    """Create a minimal tree: a real skill on disk + 3 docs citing a ref."""
    skill_dir = root / ".claude" / "skills" / "core" / "ceo-orchestration"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# real skill\n", encoding="utf-8")
    # README + CLAUDE cite the valid path; INSTALL cites the test ref.
    valid = ".claude/skills/core/ceo-orchestration/SKILL.md"
    (root / "README.md").write_text(f"see `{valid}`\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text(f"see `{valid}`\n", encoding="utf-8")
    (root / "INSTALL.md").write_text(f"Invoke from `{install_ref}`\n", encoding="utf-8")


class TestCheckDocSkillPaths(unittest.TestCase):

    def test_script_exists_and_executable(self):
        self.assertTrue(SCRIPT.is_file(), f"missing {SCRIPT}")

    def test_valid_path_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _scaffold(root, install_ref=".claude/skills/core/ceo-orchestration/SKILL.md")
            r = _run(root)
            self.assertEqual(r.returncode, 0, f"expected pass; stderr={r.stderr}")

    def test_broken_path_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # missing `core/` tier — the exact F-4.2 bug shape
            _scaffold(root, install_ref=".claude/skills/ceo-orchestration/SKILL.md")
            r = _run(root)
            self.assertEqual(r.returncode, 1, "broken path should fail the gate")

    def test_placeholder_skipped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # a `<domain>` placeholder must NOT be flagged (char-class excludes `<`)
            _scaffold(root, install_ref=".claude/skills/domains/<domain>/skills/SKILL.md")
            r = _run(root)
            self.assertEqual(r.returncode, 0, "template placeholder must be skipped")

    def test_allowlisted_entry_skipped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            broken = ".claude/skills/legacy/retired/SKILL.md"
            _scaffold(root, install_ref=broken)
            # without allowlist -> fail
            self.assertEqual(_run(root).returncode, 1)
            # with allowlist -> pass
            self.assertEqual(_run(root, allowlist=broken).returncode, 0)

    def test_real_repo_docs_resolve(self):
        """Regression sentinel: the live repo docs all resolve (L262 fix)."""
        r = _run()
        self.assertEqual(
            r.returncode, 0,
            f"live repo docs have a broken skill path; stdout={r.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
