"""Tests for `.claude/scripts/aggregate-changesets.py` (PLAN-068 v2 Phase 1).

Coverage focus:
  - Hardenings #1-#5 from `bench-results.md` §5
  - Idempotency (re-run on already-aggregated → no-op)
  - Fail-CLOSED on malformed frontmatter / bad type / multi-doc
  - Determinism across coarse-mtime filesystems (stable secondary key)
  - --check orphan guard (rc=1 on orphans, rc=0 on clean)
  - CI=true soft warning (does NOT block)
  - Negative version probe (no false positive)
  - Regex contract equivalence with `release.yml:133`

Pattern: `unittest.TestCase` (no pytest fixtures — they don't fire under
`unittest discover` in `validate.yml`; cf. S78 PLAN-066 lesson #4).
File-system isolation via `tempfile.mkdtemp`. Env isolation via
`unittest.mock.patch.dict(os.environ, ...)` for the CI=true case.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

# Ensure `_lib.testing` (TestEnvContext) is importable for env-isolation.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# ---------------------------------------------------------------------------
# Module loading (the script has a hyphenated filename → import via spec).
# ---------------------------------------------------------------------------

_SCRIPT = Path(__file__).resolve().parents[1] / "aggregate-changesets.py"
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "aggregate-changesets"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "aggregate_changesets", _SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Sandbox base — every test gets a fresh tmp dir with a copy of the
# sample CHANGELOG and an empty `.changeset/`.
# ---------------------------------------------------------------------------


class _AggregatorBase(TestEnvContext):
    """Provide an isolated sandbox per test (env-isolated via TestEnvContext)."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = Path(tempfile.mkdtemp(prefix="ceo-agg-test-"))
        self.sandbox_changelog = self._tmp / "CHANGELOG.md"
        shutil.copy(_FIXTURES / "sample-CHANGELOG.md", self.sandbox_changelog)
        self.sandbox_changeset = self._tmp / ".changeset"
        self.sandbox_changeset.mkdir()
        self.mod = _load_module()

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()

    # ---- helpers -----------------------------------------------------------

    def _hash(self, p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def _stage(self, fixture_name: str, target_name: str = "") -> Path:
        """Copy `<_FIXTURES>/<fixture_name>` into the sandbox `.changeset/`."""
        target = self.sandbox_changeset / (target_name or fixture_name)
        shutil.copy(_FIXTURES / fixture_name, target)
        return target

    def _run(self, *argv: str) -> int:
        """Invoke the aggregator's main() with stdout/stderr captured."""
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.mod.main(list(argv))
        # Stash for assertions if the test wants them.
        self._last_stdout = out.getvalue()
        self._last_stderr = err.getvalue()
        return rc


# ---------------------------------------------------------------------------
# Test cases.
# ---------------------------------------------------------------------------


class TestDryRun(_AggregatorBase):
    """`--dry-run` does NOT modify CHANGELOG or delete files."""

    def test_dry_run_preserves_changelog_hash(self) -> None:
        self._stage("single-patch.md")
        before = self._hash(self.sandbox_changelog)
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--dry-run",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._hash(self.sandbox_changelog), before)
        # Changeset file MUST still exist (not consumed).
        self.assertTrue((self.sandbox_changeset / "single-patch.md").is_file())
        self.assertIn("dry-run", self._last_stdout)


class TestEmptyDir(_AggregatorBase):
    """Empty `.changeset/` → no-op exit 0."""

    def test_empty_changeset_dir(self) -> None:
        before = self._hash(self.sandbox_changelog)
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._hash(self.sandbox_changelog), before)
        self.assertIn("no-op", self._last_stdout)


class TestEmptyDirAbsent(_AggregatorBase):
    """Missing `.changeset/` → no-op exit 0 with `absent` notice."""

    def test_absent_changeset_dir(self) -> None:
        absent = self._tmp / "does-not-exist"
        before = self._hash(self.sandbox_changelog)
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(absent),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._hash(self.sandbox_changelog), before)
        self.assertIn("absent", self._last_stdout)


class TestMissingFrontmatter(_AggregatorBase):
    """No leading `---` → fail-CLOSED rc=3."""

    def test_missing_frontmatter(self) -> None:
        self._stage("missing-frontmatter.md")
        before = self._hash(self.sandbox_changelog)
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 3)
        # CHANGELOG unchanged on fail-CLOSED.
        self.assertEqual(self._hash(self.sandbox_changelog), before)
        self.assertIn("missing leading frontmatter", self._last_stderr)


class TestBadType(_AggregatorBase):
    """`type: garbage` → fail-CLOSED rc=3."""

    def test_bad_type(self) -> None:
        self._stage("bad-type.md")
        before = self._hash(self.sandbox_changelog)
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 3)
        self.assertEqual(self._hash(self.sandbox_changelog), before)
        self.assertIn("garbage", self._last_stderr)


class TestUnknownFrontmatterKey(_AggregatorBase):
    """Codex re-pass P2: extra keys → fail-CLOSED rc=3.

    Contract from `.changeset/README.md` says ONLY `type:` is permitted.
    Aggregator MUST refuse on any unknown key (no silent acceptance).
    """

    def test_unknown_key_rejects(self) -> None:
        self._stage("unknown-key.md")
        before = self._hash(self.sandbox_changelog)
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 3)
        self.assertEqual(self._hash(self.sandbox_changelog), before)
        self.assertIn("priority", self._last_stderr)
        self.assertIn("unknown frontmatter key", self._last_stderr)


class TestRealAggregation(_AggregatorBase):
    """End-to-end: 2 changesets → new `## [1.11.6]` block + consumed."""

    def test_real_aggregation(self) -> None:
        self._stage("single-patch.md")
        self._stage("second-minor.md")
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        text = self.sandbox_changelog.read_text(encoding="utf-8")
        # New block present.
        self.assertIn("## [1.11.6] - 2026-05-02", text)
        # New block is ABOVE `## [1.11.5]`.
        self.assertLess(
            text.index("## [1.11.6]"),
            text.index("## [1.11.5]"),
            "new block must be inserted ABOVE the latest tagged block",
        )
        # Both bullets present (one per type bucket).
        self.assertIn("aggregate-changesets.py", text)
        self.assertIn(".changeset/ convention", text)
        # Consumed files deleted.
        self.assertFalse(
            (self.sandbox_changeset / "single-patch.md").exists()
        )
        self.assertFalse(
            (self.sandbox_changeset / "second-minor.md").exists()
        )


class TestIdempotency(_AggregatorBase):
    """Re-run on already-aggregated CHANGELOG → no-op + identical hash."""

    def test_idempotent_rerun(self) -> None:
        # First run: real aggregation.
        self._stage("single-patch.md")
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        post_first = self._hash(self.sandbox_changelog)
        # Stage another changeset to confirm the gate trips before parsing.
        self._stage("second-minor.md")
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        # Hash unchanged → no-op.
        self.assertEqual(self._hash(self.sandbox_changelog), post_first)
        # The new changeset is NOT consumed (idempotency stops before delete).
        self.assertTrue(
            (self.sandbox_changeset / "second-minor.md").is_file()
        )
        self.assertIn("idempotent", self._last_stdout)


class TestRegexContract(_AggregatorBase):
    """Hardening #4: produced block matches `release.yml:133` literal regex.

    The release.yml step does:
        grep -qE "^## \\[${VERSION}\\]" CHANGELOG.md
    `make_version_regex(version)` MUST match that grep on the produced
    CHANGELOG.
    """

    def test_regex_contract(self) -> None:
        self._stage("single-patch.md")
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        text = self.sandbox_changelog.read_text(encoding="utf-8")
        regex = self.mod.make_version_regex("1.11.6")
        m = regex.search(text)
        self.assertIsNotNone(
            m, "produced CHANGELOG must satisfy release.yml:133 grep"
        )
        # And the matched line literally starts with `## [1.11.6]`.
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.start())
        line = text[line_start:line_end]
        self.assertTrue(line.startswith("## [1.11.6]"))


class TestStableSortOrder(_AggregatorBase):
    """Hardening #1: identical mtime → output ordered by `p.name`.

    We force two files to have the same mtime (down to nanoseconds where
    supported). Because the secondary key is filename, the ordering is
    deterministic regardless of insertion order.
    """

    def test_stable_sort_under_identical_mtime(self) -> None:
        a = self._stage("single-patch.md", "z-late.md")
        b = self._stage("second-minor.md", "a-early.md")
        # Force identical mtime on both files.
        ts = time.time()
        os.utime(a, (ts, ts))
        os.utime(b, (ts, ts))
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        text = self.sandbox_changelog.read_text(encoding="utf-8")
        # `a-early.md` body (`introduce .changeset/`) MUST appear above
        # `z-late.md` body (`add aggregate-changesets.py`) in the produced
        # block — stable secondary sort by `p.name` ascending.
        idx_a = text.index(".changeset/ convention")
        idx_z = text.index("aggregate-changesets.py")
        self.assertLess(
            idx_a, idx_z,
            "secondary sort key must order by `p.name` when mtimes tie",
        )


class TestCheckMode(_AggregatorBase):
    """Hardening #2: `--check` returns rc=1 on orphans."""

    def test_check_returns_one_with_orphans(self) -> None:
        self._stage("single-patch.md")
        rc = self._run(
            "--check",
            "--changeset-dir", str(self.sandbox_changeset),
        )
        self.assertEqual(rc, 1)
        self.assertIn("orphan", self._last_stderr)
        self.assertIn("single-patch.md", self._last_stderr)


class TestCheckModeNoOrphans(_AggregatorBase):
    """Hardening #2: `--check` returns rc=0 when changeset dir is clean."""

    def test_check_returns_zero_when_clean(self) -> None:
        rc = self._run(
            "--check",
            "--changeset-dir", str(self.sandbox_changeset),
        )
        self.assertEqual(rc, 0)
        self.assertIn("no orphan", self._last_stdout)


class TestCIWarning(_AggregatorBase):
    """Hardening #3: CI=true triggers stderr warning but does NOT abort."""

    def test_ci_env_warns_but_does_not_block(self) -> None:
        with patch.dict(os.environ, {"CI": "true"}):
            rc = self._run(
                "--version", "1.11.6",
                "--date", "2026-05-02",
                "--changeset-dir", str(self.sandbox_changeset),
                "--changelog", str(self.sandbox_changelog),
            )
        self.assertEqual(rc, 0, "CI=true must be advisory only")
        self.assertIn("LOCAL-ONLY", self._last_stderr)


class TestNegativeVersion(_AggregatorBase):
    """Negative control — `9.9.9` not present → idempotency gate does NOT trip.

    With no changesets, this still no-ops (rc=0), but the regex
    `make_version_regex("9.9.9")` MUST return None against the seeded
    CHANGELOG (which has `1.11.5`/`1.11.4`/`1.11.3`).
    """

    def test_unrelated_version_does_not_match(self) -> None:
        text = self.sandbox_changelog.read_text(encoding="utf-8")
        regex = self.mod.make_version_regex("9.9.9")
        self.assertIsNone(regex.search(text))


class TestMultiDocFailClosed(_AggregatorBase):
    """`---` fence inside body → multi-doc detected → fail-CLOSED rc=3."""

    def test_multidoc_body(self) -> None:
        self._stage("multidoc.md")
        before = self._hash(self.sandbox_changelog)
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 3)
        self.assertEqual(self._hash(self.sandbox_changelog), before)
        self.assertIn("multi-doc", self._last_stderr)


class TestInvalidCli(_AggregatorBase):
    """Invalid `--version` / `--date` patterns → rc=2."""

    def test_invalid_version_format(self) -> None:
        rc = self._run(
            "--version", "not-a-version",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 2)

    def test_invalid_date_format(self) -> None:
        rc = self._run(
            "--version", "1.11.6",
            "--date", "May 2",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 2)

    def test_missing_version(self) -> None:
        rc = self._run(
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 2)

    def test_missing_date(self) -> None:
        rc = self._run(
            "--version", "1.11.6",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 2)

    def test_changelog_missing(self) -> None:
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self._tmp / "no-such-file.md"),
        )
        self.assertEqual(rc, 2)


class TestParseChangesetUnits(TestEnvContext):
    """Direct unit coverage for `parse_changeset` edge cases."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def setUp(self) -> None:
        super().setUp()
        self._tmp = Path(tempfile.mkdtemp(prefix="ceo-agg-pc-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()

    def _write(self, name: str, content: str) -> Path:
        p = self._tmp / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_missing_closing_delimiter(self) -> None:
        p = self._write(
            "no-close.md",
            "---\ntype: patch\nbody but no closing fence\n",
        )
        with self.assertRaises(self.mod.ChangesetError) as cm:
            self.mod.parse_changeset(p)
        self.assertIn("closing", str(cm.exception))

    def test_malformed_frontmatter_line(self) -> None:
        p = self._write(
            "bad-fm.md",
            "---\ntype patch\n---\nbody\n",  # missing colon
        )
        with self.assertRaises(self.mod.ChangesetError) as cm:
            self.mod.parse_changeset(p)
        self.assertIn("malformed", str(cm.exception))

    def test_missing_type_field(self) -> None:
        p = self._write(
            "no-type.md",
            "---\nfoo: bar\n---\nbody\n",
        )
        with self.assertRaises(self.mod.ChangesetError) as cm:
            self.mod.parse_changeset(p)
        self.assertIn("type", str(cm.exception))

    def test_empty_body(self) -> None:
        p = self._write(
            "empty-body.md",
            "---\ntype: patch\n---\n   \n",  # whitespace-only body
        )
        with self.assertRaises(self.mod.ChangesetError) as cm:
            self.mod.parse_changeset(p)
        self.assertIn("empty body", str(cm.exception))

    def test_comment_in_frontmatter_ignored(self) -> None:
        p = self._write(
            "comment-fm.md",
            "---\n# this is a comment\ntype: patch\n---\nbody line\n",
        )
        tp, body = self.mod.parse_changeset(p)
        self.assertEqual(tp, "patch")
        self.assertEqual(body, "body line")

    def test_valid_minor(self) -> None:
        p = self._write(
            "ok-minor.md",
            "---\ntype: minor\n---\nadd new feature\n",
        )
        tp, body = self.mod.parse_changeset(p)
        self.assertEqual(tp, "minor")
        self.assertEqual(body, "add new feature")

    def test_valid_major(self) -> None:
        p = self._write(
            "ok-major.md",
            "---\ntype: major\n---\nbreaking change line\n",
        )
        tp, body = self.mod.parse_changeset(p)
        self.assertEqual(tp, "major")
        self.assertEqual(body, "breaking change line")

    def test_trailing_dash_dash_dash_no_newline(self) -> None:
        # File ends with `---` on last line (no trailing newline).
        p = self._write(
            "trailing.md",
            "---\ntype: patch\n---\nbody only\n---",
        )
        # This now has two `---` markers: open at line 0 and another at
        # the very end. The body becomes "body only\n---" and the
        # multi-doc detector trips fail-CLOSED. That's the correct
        # safe-default behaviour per PoC §5 risk #4.
        with self.assertRaises(self.mod.ChangesetError):
            self.mod.parse_changeset(p)


class TestSkipFilenames(_AggregatorBase):
    """`README.md` and `config.json` and non-.md files are excluded."""

    def test_skips_readme_and_non_md(self) -> None:
        # Add real changeset + skip-able siblings.
        self._stage("single-patch.md")
        (self.sandbox_changeset / "README.md").write_text(
            "should be skipped\n", encoding="utf-8"
        )
        (self.sandbox_changeset / "config.json").write_text(
            "{}\n", encoding="utf-8"
        )
        (self.sandbox_changeset / "notes.txt").write_text(
            "non-md, also skipped\n", encoding="utf-8"
        )
        rc = self._run(
            "--version", "1.11.6",
            "--date", "2026-05-02",
            "--changeset-dir", str(self.sandbox_changeset),
            "--changelog", str(self.sandbox_changelog),
        )
        self.assertEqual(rc, 0)
        # Real changeset consumed.
        self.assertFalse(
            (self.sandbox_changeset / "single-patch.md").exists()
        )
        # Skipped siblings preserved.
        self.assertTrue(
            (self.sandbox_changeset / "README.md").is_file()
        )
        self.assertTrue(
            (self.sandbox_changeset / "config.json").is_file()
        )
        self.assertTrue(
            (self.sandbox_changeset / "notes.txt").is_file()
        )


class TestRenderInsert(TestEnvContext):
    """Direct unit coverage for `render_block` + `insert_block`."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def test_render_orders_buckets_major_minor_patch(self) -> None:
        block = self.mod.render_block(
            "1.0.0",
            "2026-01-01",
            [
                ("patch", "p1"),
                ("major", "m1"),
                ("minor", "n1"),
            ],
        )
        # Major appears before Minor, which appears before Patch.
        self.assertLess(block.index("### Major"), block.index("### Minor"))
        self.assertLess(block.index("### Minor"), block.index("### Patch"))
        self.assertIn("- m1", block)
        self.assertIn("- n1", block)
        self.assertIn("- p1", block)

    def test_render_skips_empty_buckets(self) -> None:
        block = self.mod.render_block(
            "1.0.0", "2026-01-01", [("patch", "x")]
        )
        self.assertNotIn("### Major", block)
        self.assertNotIn("### Minor", block)
        self.assertIn("### Patch", block)

    def test_insert_block_appends_when_no_tagged_block(self) -> None:
        text = "# Changelog\n\nNo tagged blocks at all\n"
        block = "## [1.0.0] - 2026-01-01\n\n### Patch\n\n- x\n\n"
        out = self.mod.insert_block(text, block)
        # Block was appended at the end (defensive path).
        self.assertTrue(out.rstrip().endswith("- x"))


if __name__ == "__main__":
    unittest.main()
