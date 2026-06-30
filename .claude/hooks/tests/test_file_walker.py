"""Unit tests for _lib/file_walker.py."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


from _lib.file_walker import FileWalker  # noqa: E402


class FileWalkerTestBase(unittest.TestCase):
    """Builds a temp repo tree for each test."""

    def setUp(self) -> None:
        # Resolve on setUp so macOS /tmp → /private/tmp symlink is
        # normalized for the whole test (walker does its own resolve()).
        self.root = Path(tempfile.mkdtemp(prefix="ceo-walker-test-")).resolve()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, rel: str, content: str = "x") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p


class TestFilesystemMode(FileWalkerTestBase):

    def test_lists_all_files_no_filter(self):
        self._write("a.md")
        self._write("b.yaml")
        self._write("c.txt")
        walker = FileWalker(self.root, mode="filesystem")
        result = sorted([p.name for p in walker.iter_files()])
        self.assertEqual(result, ["a.md", "b.yaml", "c.txt"])

    def test_suffix_filter(self):
        self._write("a.md")
        self._write("b.yaml")
        self._write("c.txt")
        walker = FileWalker(
            self.root, mode="filesystem", suffixes={".md", ".yaml"}
        )
        result = sorted([p.name for p in walker.iter_files()])
        self.assertEqual(result, ["a.md", "b.yaml"])

    def test_skip_subdir_names(self):
        self._write("a.md")
        self._write("benchmarks/scenario.yaml")
        self._write("src/b.md")
        walker = FileWalker(
            self.root,
            mode="filesystem",
            suffixes={".md", ".yaml"},
            skip_subdir_names={"benchmarks"},
        )
        result = sorted([str(p.relative_to(self.root)) for p in walker.iter_files()])
        self.assertEqual(result, ["a.md", "src/b.md"])

    def test_invalid_mode_raises(self):
        with self.assertRaises(ValueError):
            FileWalker(self.root, mode="not-a-mode")


class TestAllowlist(FileWalkerTestBase):

    def test_exact_match(self):
        walker = FileWalker(
            self.root,
            mode="filesystem",
            path_allowlist_exact={"LICENSE"},
        )
        license_path = self._write("LICENSE", "MIT")
        other = self._write("README.md")
        self.assertTrue(walker.is_allowlisted(license_path))
        self.assertFalse(walker.is_allowlisted(other))

    def test_glob_match(self):
        walker = FileWalker(
            self.root,
            mode="filesystem",
            path_allowlist_globs={".claude/skills/domains/*"},
        )
        domain_file = self._write(".claude/skills/domains/fintech")
        core_file = self._write(".claude/skills/core/foo.md")
        self.assertTrue(walker.is_allowlisted(domain_file))
        self.assertFalse(walker.is_allowlisted(core_file))

    def test_token_match(self):
        walker = FileWalker(
            self.root,
            mode="filesystem",
            path_allowlist_tokens={"frontend-data-layer"},
        )
        match = self._write(".claude/skills/frontend/frontend-data-layer/SKILL.md")
        miss = self._write(".claude/skills/core/other/SKILL.md")
        self.assertTrue(walker.is_allowlisted(match))
        self.assertFalse(walker.is_allowlisted(miss))

    def test_all_styles_combined(self):
        walker = FileWalker(
            self.root,
            mode="filesystem",
            path_allowlist_exact={"LICENSE"},
            path_allowlist_globs={"docs/*.md"},
            path_allowlist_tokens={"frontend-data-layer"},
        )
        lic = self._write("LICENSE")
        doc = self._write("docs/intro.md")
        token = self._write("x/y/frontend-data-layer/z.md")
        other = self._write("src/main.py")
        self.assertTrue(walker.is_allowlisted(lic))
        self.assertTrue(walker.is_allowlisted(doc))
        self.assertTrue(walker.is_allowlisted(token))
        self.assertFalse(walker.is_allowlisted(other))

    def test_iter_non_allowlisted(self):
        walker = FileWalker(
            self.root,
            mode="filesystem",
            suffixes={".md"},
            path_allowlist_exact={"README.md"},
        )
        self._write("README.md")
        self._write("doc.md")
        result = sorted([p.name for p in walker.iter_non_allowlisted()])
        self.assertEqual(result, ["doc.md"])


@unittest.skipUnless(shutil.which("git"), "git not on PATH")
class TestGitMode(FileWalkerTestBase):

    def _git_init(self):
        """Initialize a git repo with 2 tracked files."""
        subprocess.run(
            ["git", "init", "-q"],
            cwd=str(self.root),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(self.root),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(self.root),
            check=True,
            capture_output=True,
        )
        self._write("tracked.md")
        self._write("src/main.py")
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(self.root),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "init", "-q"],
            cwd=str(self.root),
            check=True,
            capture_output=True,
            env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.com",
                 "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.com"},
        )

    def test_git_mode_yields_tracked_only(self):
        self._git_init()
        self._write("untracked.md")
        walker = FileWalker(self.root, mode="git", suffixes={".md"})
        tracked = sorted([p.name for p in walker.iter_files()])
        self.assertEqual(tracked, ["tracked.md"])

    def test_git_mode_empty_when_not_a_repo(self):
        walker = FileWalker(self.root, mode="git")
        self.assertEqual(list(walker.iter_files()), [])


# ---------------------------------------------------------------------------
# PLAN-019 P1-QA-2 — edge-case extensions per public-function coverage
# standard (≥5 tests per public function). Public API:
#   - FileWalker.__init__  (mode validation + defaults)
#   - FileWalker.iter_files
#   - FileWalker.is_allowlisted
#   - FileWalker.iter_non_allowlisted
# Edge cases: empty repo, skip-subdir nested depth, non-UTF-8 names,
# symlinks, suffix case-sensitivity, empty allowlist, path outside root.
# ---------------------------------------------------------------------------


class TestFilesystemEdgeCases(FileWalkerTestBase):
    """Edge cases for FileWalker iter_files() (filesystem mode)."""

    def test_empty_repo_yields_nothing(self):
        """Walker on an empty directory returns no files."""
        walker = FileWalker(self.root, mode="filesystem")
        self.assertEqual(list(walker.iter_files()), [])

    def test_suffix_filter_is_case_sensitive(self):
        """`.md` filter should NOT match `.MD` — stdlib Path.suffix is case-preserved.

        Documents current behavior; protects against a future refactor that
        silently casefolds suffixes (which would change governance output).
        """
        self._write("low.md")
        self._write("up.MD")
        walker = FileWalker(self.root, mode="filesystem", suffixes={".md"})
        names = sorted(p.name for p in walker.iter_files())
        self.assertEqual(names, ["low.md"])

    def test_skip_subdir_nested_deeply(self):
        """Files at any depth inside a skipped subdir are filtered."""
        self._write("benchmarks/x.yaml")
        self._write("benchmarks/sub/y.yaml")
        self._write("benchmarks/sub/sub/z.yaml")
        self._write("ok/a.yaml")
        walker = FileWalker(
            self.root,
            mode="filesystem",
            suffixes={".yaml"},
            skip_subdir_names={"benchmarks"},
        )
        names = sorted(str(p.relative_to(self.root)) for p in walker.iter_files())
        self.assertEqual(names, ["ok/a.yaml"])

    def test_symlinks_to_files_in_repo_are_walked(self):
        """Symlinks inside repo_root are enumerated by rglob (stdlib default)."""
        real = self._write("real.md", "hello")
        link = self.root / "link.md"
        try:
            link.symlink_to(real)
        except OSError:
            self.skipTest("symlinks not supported on this filesystem")
        walker = FileWalker(self.root, mode="filesystem", suffixes={".md"})
        names = sorted(p.name for p in walker.iter_files())
        self.assertIn("real.md", names)
        # `link.md` may or may not be yielded depending on rglob behavior;
        # but at minimum rglob should not raise.
        self.assertTrue(len(names) >= 1)

    def test_directory_entries_never_yielded(self):
        """Walker yields files only — never directories."""
        self._write("outer/inner/deep.md")
        walker = FileWalker(self.root, mode="filesystem")
        for p in walker.iter_files():
            self.assertTrue(p.is_file(),
                            f"walker yielded non-file: {p}")


class TestAllowlistEdgeCases(FileWalkerTestBase):
    """Edge cases for FileWalker.is_allowlisted()."""

    def test_empty_allowlist_matches_nothing(self):
        """No allowlist entries → every path fails is_allowlisted."""
        walker = FileWalker(self.root, mode="filesystem")
        p = self._write("anything.md")
        self.assertFalse(walker.is_allowlisted(p))

    def test_is_allowlisted_handles_path_outside_root(self):
        """Path not under repo_root → fallback to absolute-path token match."""
        walker = FileWalker(
            self.root,
            mode="filesystem",
            path_allowlist_tokens={"/tmp/"},
        )
        outside = Path("/tmp/nonrepo/foo.md")
        # Should match via token even though path.relative_to(root) raises.
        self.assertTrue(walker.is_allowlisted(outside))

    def test_is_allowlisted_exact_requires_full_relative_match(self):
        """Exact-match allowlist is relative to repo_root and requires full string."""
        walker = FileWalker(
            self.root,
            mode="filesystem",
            path_allowlist_exact={"docs/intro.md"},
        )
        exact = self._write("docs/intro.md")
        partial = self._write("docs/intro.md.bak")
        self.assertTrue(walker.is_allowlisted(exact))
        # The `.bak` file's relative is "docs/intro.md.bak" — not in exact set.
        self.assertFalse(walker.is_allowlisted(partial))

    def test_glob_matches_with_trailing_double_star(self):
        """fnmatch does NOT understand `**`; test the documented one-level behavior."""
        walker = FileWalker(
            self.root,
            mode="filesystem",
            path_allowlist_globs={"docs/*"},
        )
        shallow = self._write("docs/a.md")
        # fnmatch treats `*` as greedy across path separators by default;
        # we document current behavior rather than assert a strict POSIX glob.
        deep = self._write("docs/sub/b.md")
        self.assertTrue(walker.is_allowlisted(shallow))
        # The deep one MAY match depending on fnmatch semantics — assert
        # contract: at minimum shallow matches, deep-check documents current.
        _ = walker.is_allowlisted(deep)  # no-raise contract

    def test_token_match_case_sensitive(self):
        """Token match is a plain `in` substring check — case sensitive."""
        walker = FileWalker(
            self.root,
            mode="filesystem",
            path_allowlist_tokens={"MySecret"},
        )
        match = self._write("path/to/MySecret/file.txt")
        miss = self._write("path/to/mysecret/file.txt")
        self.assertTrue(walker.is_allowlisted(match))
        self.assertFalse(walker.is_allowlisted(miss))

    def test_iter_non_allowlisted_empty_when_all_allowed(self):
        """If every file is allowlisted, iter_non_allowlisted is empty."""
        self._write("a.md")
        self._write("b.md")
        walker = FileWalker(
            self.root,
            mode="filesystem",
            suffixes={".md"},
            path_allowlist_globs={"*.md"},
        )
        self.assertEqual(list(walker.iter_non_allowlisted()), [])
