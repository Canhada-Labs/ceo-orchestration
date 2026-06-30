"""PLAN-133 G2 — unit tests for scripts/discover_foreign_context.py.

The G2 acceptance criterion: foreign context filenames (AGENTS.md /
.cursorrules) are DISCOVERY-ONLY — surfaced in a report, never merged into
settings.json, never overwritten, never read for content. These tests pin:

  * existence-only discovery of the allowlisted filenames (and the CLAUDE.md
    exclusion);
  * the default-ON report flag + the explicit-falsey silence path;
  * fail-open behavior on a non-existent / unreadable root;
  * the report text asserts the "not merged" invariant;
  * NO file is created/modified by discovery (read-only guarantee);
  * the CLI exits 0 even when silenced or pointed at a missing dir.

Env hygiene (PLAN-117 WS-C / S221 gate): the suite-wide TestEnvContext base
isolates $HOME / $CLAUDE_PROJECT_DIR, and every env mutation goes through
mock.patch.dict (never a bare os.environ[...] = assignment).
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

MODULE_PATH = REPO_ROOT / "scripts" / "discover_foreign_context.py"


def _load_module():
    """Import the hyphen-free standalone helper as a module object."""
    spec = importlib.util.spec_from_file_location(
        "discover_foreign_context", str(MODULE_PATH)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


dfc = _load_module()


class DiscoverForeignContextTest(TestEnvContext):
    # ---- existence-only discovery -------------------------------------

    def test_finds_agents_md(self) -> None:
        with TemporaryDirectory() as td:
            (Path(td) / "AGENTS.md").write_text("foreign instructions\n")
            found = dfc.discover_foreign_context(td)
            self.assertIn("AGENTS.md", found)

    def test_finds_cursorrules(self) -> None:
        with TemporaryDirectory() as td:
            (Path(td) / ".cursorrules").write_text("cursor rules\n")
            found = dfc.discover_foreign_context(td)
            self.assertIn(".cursorrules", found)

    def test_finds_nested_allowlisted_file(self) -> None:
        with TemporaryDirectory() as td:
            ghdir = Path(td) / ".github"
            ghdir.mkdir()
            (ghdir / "copilot-instructions.md").write_text("copilot\n")
            found = dfc.discover_foreign_context(td)
            self.assertIn(".github/copilot-instructions.md", found)

    def test_empty_root_finds_nothing(self) -> None:
        with TemporaryDirectory() as td:
            self.assertEqual(dfc.discover_foreign_context(td), [])

    def test_claude_md_is_not_treated_as_foreign(self) -> None:
        """CLAUDE.md is the framework's native file, never reported foreign."""
        with TemporaryDirectory() as td:
            (Path(td) / "CLAUDE.md").write_text("# native\n")
            found = dfc.discover_foreign_context(td)
            self.assertEqual(found, [])
            self.assertNotIn("CLAUDE.md", found)

    def test_discovery_preserves_allowlist_order(self) -> None:
        with TemporaryDirectory() as td:
            # Create out of allowlist order; result must follow allowlist order.
            (Path(td) / "GEMINI.md").write_text("g\n")
            (Path(td) / "AGENTS.md").write_text("a\n")
            found = dfc.discover_foreign_context(td)
            self.assertEqual(found, ["AGENTS.md", "GEMINI.md"])

    # ---- discovery is READ-ONLY (the security invariant) --------------

    def test_discovery_does_not_read_contents_or_mutate(self) -> None:
        """Discovery must not create/modify/delete anything, and the foreign
        file's bytes are left exactly as-is (no merge, no rewrite)."""
        with TemporaryDirectory() as td:
            root = Path(td)
            original = "DO NOT TOUCH\n"
            agents = root / "AGENTS.md"
            agents.write_text(original)
            before = {p.name: p.read_bytes() for p in root.iterdir()}

            dfc.discover_foreign_context(td)

            after = {p.name: p.read_bytes() for p in root.iterdir()}
            self.assertEqual(before, after, "discovery mutated the tree")
            self.assertEqual(agents.read_text(), original)
            # No settings.json was ever created by discovery.
            self.assertFalse((root / ".claude").exists())

    # ---- flag handling (default-ON report) ----------------------------

    def test_flag_default_on(self) -> None:
        # Inject an env WITHOUT the flag → default-ON (no ambient-env reliance).
        self.assertTrue(dfc.discovery_enabled(env={}))

    def test_flag_explicit_falsey_silences(self) -> None:
        for val in ("0", "false", "no", "off", "OFF", "False"):
            with mock.patch.dict(os.environ, {dfc.DISCOVERY_FLAG: val}):
                self.assertFalse(
                    dfc.discovery_enabled(), msg="value %r should silence" % val
                )

    def test_flag_truthy_enables(self) -> None:
        for val in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {dfc.DISCOVERY_FLAG: val}):
                self.assertTrue(dfc.discovery_enabled())

    # ---- report rendering --------------------------------------------

    def test_report_states_not_merged(self) -> None:
        lines = dfc.render_report(["AGENTS.md"], "/some/root")
        joined = "\n".join(lines)
        self.assertIn("DISCOVERY", joined)
        self.assertIn("not merged", joined)
        self.assertIn("AGENTS.md", joined)

    def test_report_empty_case(self) -> None:
        lines = dfc.render_report([], "/some/root")
        joined = "\n".join(lines)
        self.assertIn("none found", joined)
        self.assertNotIn("FOUND", joined)

    # ---- fail-open on infra ------------------------------------------

    def test_missing_root_is_fail_open(self) -> None:
        found = dfc.discover_foreign_context("/nonexistent/path/xyzzy-987")
        self.assertEqual(found, [])

    def test_traversal_candidate_rejected(self) -> None:
        """Defensive: a candidate with '..' is skipped (allowlist has none)."""
        with mock.patch.object(
            dfc, "FOREIGN_CONTEXT_FILENAMES", ("../escape.md", "AGENTS.md")
        ):
            with TemporaryDirectory() as td:
                (Path(td) / "AGENTS.md").write_text("a\n")
                # Make a sibling file that '..' would reach, to prove it is NOT
                # picked up.
                parent = Path(td).parent
                escape = parent / "escape.md"
                created = False
                if not escape.exists():
                    escape.write_text("x\n")
                    created = True
                try:
                    found = dfc.discover_foreign_context(td)
                    self.assertEqual(found, ["AGENTS.md"])
                finally:
                    if created:
                        escape.unlink()

    # ---- CLI contract (always exit 0; advisory) -----------------------

    def _run_cli(self, target, env=None):
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), target],
            env={**os.environ, **(env or {})},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def test_cli_reports_and_exits_zero(self) -> None:
        with TemporaryDirectory() as td:
            (Path(td) / "AGENTS.md").write_text("a\n")
            r = self._run_cli(td)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertIn("AGENTS.md", r.stdout)
            self.assertIn("DISCOVERY", r.stdout)

    def test_cli_silenced_prints_nothing(self) -> None:
        with TemporaryDirectory() as td:
            (Path(td) / "AGENTS.md").write_text("a\n")
            r = self._run_cli(td, env={dfc.DISCOVERY_FLAG: "0"})
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertEqual(r.stdout.strip(), "")

    def test_cli_missing_dir_exits_zero(self) -> None:
        r = self._run_cli("/nonexistent/path/xyzzy-987")
        self.assertEqual(r.returncode, 0, msg=r.stderr)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
