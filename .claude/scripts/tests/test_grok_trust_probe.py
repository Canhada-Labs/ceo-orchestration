"""PLAN-156-FOLLOWUP F4 (consensus C6) — grok trust-probe exact-entry parse.

## The bug class this pins shut

`grok_arming_check` (scripts/_grok_harness.sh) decides between
``VERDICT: ARMED`` and ``VERDICT: NOT-ARMED-(untrusted)`` by probing
``~/.grok/trusted_folders.toml``. The S270 live-fire found the probe was a
substring ``grep -qF "$target"`` over the WHOLE file, so it false-ARMED on:

1. a **prefix sibling** — target ``/x/repo`` matched an entry for
   ``/x/repo-backup`` (the target string is a substring of the entry);
2. a **commented-out entry** — ``# [folders."/x/repo"]`` still matched;
3. (schema-honest extra) a **declined** entry — grok records
   ``trusted = false`` for folders the operator declined; path presence
   alone must never arm.

The fix (``_grok_trust_probe``) parses line-wise against the REAL schema
captured 2026-07-13 from the pinned grok binary (0.2.93, f00f96316d4b):
``[folders."<abs path>"]`` table headers + a ``trusted = true`` key inside
the matching table. Both sides are realpath-normalized, compared for EXACT
equality, and ANY parse ambiguity resolves toward NOT-ARMED (the probe must
never over-claim — C6 red-flag line).

## Which copy is under test

Per the PLAN-156-FOLLOWUP staging protocol, the shell under test resolves
through ``CEO_FU_STAGED_ROOT`` (default
``.claude/plans/PLAN-156-FOLLOWUP/staged/root``) and falls back to the
CANONICAL path when no staged copy exists (post-ceremony canonical mode).
F4 was applied DIRECTLY to canonical ``scripts/_grok_harness.sh`` (the file
is not canonical-guarded), so the fallback branch is the live one today.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Tuple, Union

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parent.parent.parent  # .claude/scripts/tests -> repo
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_SCHEMA_FIXTURE = (
    _REPO_ROOT
    / ".claude"
    / "plans"
    / "PLAN-156-FOLLOWUP"
    / "staged"
    / "fixtures"
    / "trusted_folders.toml"
)


def _file_under_test(rel: str) -> Path:
    """Staged copy if present, else canonical (post-ceremony mode)."""
    staged_root = os.environ.get(
        "CEO_FU_STAGED_ROOT",
        str(_REPO_ROOT / ".claude" / "plans" / "PLAN-156-FOLLOWUP" / "staged" / "root"),
    )
    staged = Path(staged_root) / rel
    if staged.is_file():
        return staged
    return _REPO_ROOT / rel


class _TrustProbeBase(TestEnvContext):
    """Drive the sourced ``_grok_trust_probe`` function hermetically."""

    def _run_probe(self, toml_path: Path, target: "Union[str, Path]") -> Tuple[str, int, str]:
        harness = _file_under_test("scripts/_grok_harness.sh")
        self.assertTrue(harness.is_file(), "harness under test missing: %s" % harness)
        # Source the harness (function definitions only — no side effects)
        # and invoke the probe. Positional args keep the paths un-evaled.
        script = 'source "$1" && _grok_trust_probe "$2" "$3"'
        proc = subprocess.run(
            ["bash", "-c", script, "bash", str(harness), str(toml_path), str(target)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.stdout.strip(), proc.returncode, proc.stderr

    def _write_toml(self, body: str) -> Path:
        tf = self.home_dir / "trusted_folders.toml"
        tf.write_text(body, encoding="utf-8")
        return tf

    @staticmethod
    def _entry(path: Path, trusted: bool = True) -> str:
        return '[folders."%s"]\ntrusted = %s\ndecided_at = 1783903709\n' % (
            path,
            "true" if trusted else "false",
        )


class ExactMatchFixtureTest(_TrustProbeBase):
    """An exact normalized entry with trusted=true — the ONLY arming shape."""

    def test_exact_entry_arms(self):
        repo = self.home_dir / "repo"
        repo.mkdir()
        tf = self._write_toml(self._entry(repo))
        out, rc, err = self._run_probe(tf, repo)
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, "1", "exact trusted entry must arm")

    def test_symlink_and_lexical_forms_normalize_to_the_same_entry(self):
        # macOS realpath class: /tmp vs /private/tmp, ./ segments, symlinks.
        real = self.home_dir / "repo"
        real.mkdir()
        link = self.home_dir / "repo-link"
        link.symlink_to(real)
        tf = self._write_toml(self._entry(real))
        out, _, _ = self._run_probe(tf, link)
        self.assertEqual(out, "1", "realpath-normalization must unify symlink forms")
        # NOTE: built as a raw string — pathlib collapses "./" at construction.
        dotted = "%s/./repo" % self.home_dir
        out, _, _ = self._run_probe(tf, dotted)
        self.assertEqual(out, "1", "lexical ./ segment must normalize")


class PrefixSiblingFixtureTest(_TrustProbeBase):
    """The S270 false-ARMED reproduction: /x/repo vs /x/repo-backup."""

    def test_prefix_sibling_does_not_arm(self):
        repo = self.home_dir / "repo"
        backup = self.home_dir / "repo-backup"
        repo.mkdir()
        backup.mkdir()
        # File trusts ONLY the sibling; target is the shorter prefix path.
        tf = self._write_toml(self._entry(backup))
        # Meta-assert the OLD bug precondition: the target string IS a
        # substring of the fixture (grep -qF would have false-ARMED).
        self.assertIn(str(repo), tf.read_text(encoding="utf-8"))
        out, rc, err = self._run_probe(tf, repo)
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, "0", "prefix sibling must NOT arm (old grep -qF bug)")

    def test_sibling_entry_does_not_shadow_a_real_entry(self):
        repo = self.home_dir / "repo"
        backup = self.home_dir / "repo-backup"
        repo.mkdir()
        backup.mkdir()
        tf = self._write_toml(self._entry(backup) + "\n" + self._entry(repo))
        out, _, _ = self._run_probe(tf, repo)
        self.assertEqual(out, "1", "the real exact entry still arms alongside a sibling")


class CommentedEntryFixtureTest(_TrustProbeBase):
    """Commented-out entries contribute nothing."""

    def test_commented_entry_does_not_arm(self):
        repo = self.home_dir / "repo"
        repo.mkdir()
        body = "".join(
            "# %s" % line if line.strip() else line
            for line in self._entry(repo).splitlines(True)
        )
        tf = self._write_toml(body)
        self.assertIn(str(repo), tf.read_text(encoding="utf-8"))  # old-bug precondition
        out, _, _ = self._run_probe(tf, repo)
        self.assertEqual(out, "0", "a commented entry must NOT arm")

    def test_commented_trusted_line_does_not_arm_a_real_header(self):
        repo = self.home_dir / "repo"
        repo.mkdir()
        body = '[folders."%s"]\n# trusted = true\ndecided_at = 1\n' % repo
        tf = self._write_toml(body)
        out, _, _ = self._run_probe(tf, repo)
        self.assertEqual(out, "0", "header without an uncommented trusted=true stays cold")


class NotArmedBiasTest(_TrustProbeBase):
    """ANY parse ambiguity or schema deviation resolves toward NOT-ARMED."""

    def test_trusted_false_entry_does_not_arm(self):
        repo = self.home_dir / "repo"
        repo.mkdir()
        tf = self._write_toml(self._entry(repo, trusted=False))
        out, _, _ = self._run_probe(tf, repo)
        self.assertEqual(out, "0", "grok records declines; trusted=false must NOT arm")

    def test_unrecognized_table_header_closes_the_section(self):
        repo = self.home_dir / "repo"
        repo.mkdir()
        # trusted=true appears only AFTER an unparseable header — it must
        # not be attributed to the target's table.
        body = self._entry(repo).replace("trusted = true\n", "") + "[weird stuff\ntrusted = true\n"
        tf = self._write_toml(body)
        out, _, _ = self._run_probe(tf, repo)
        self.assertEqual(out, "0", "ambiguous header must close the section (NOT-ARMED bias)")

    def test_empty_and_missing_files_do_not_arm(self):
        repo = self.home_dir / "repo"
        repo.mkdir()
        tf = self._write_toml("")
        out, _, _ = self._run_probe(tf, repo)
        self.assertEqual(out, "0")
        out, _, _ = self._run_probe(self.home_dir / "nope.toml", repo)
        self.assertEqual(out, "0")


@unittest.skipUnless(_SCHEMA_FIXTURE.is_file(), "characterized schema fixture not present")
class CharacterizedSchemaFixtureTest(_TrustProbeBase):
    """Run the probe over the pinned REAL-schema fixture (neutral paths)."""

    def test_fixture_matrix(self):
        cases = {
            "/x/repo": "1",        # exact trusted entry
            "/x/repo-backup": "1",  # its own exact entry (also trusted)
            "/x/rep": "0",         # prefix of an entry
            "/x/repo2": "0",       # entry is a prefix of the target
            "/x/commented": "0",   # commented-out entry
            "/x/denied": "0",      # trusted = false
        }
        for target, expected in cases.items():
            out, rc, err = self._run_probe(_SCHEMA_FIXTURE, Path(target))
            self.assertEqual(rc, 0, err)
            self.assertEqual(
                out, expected, "target %s: expected %s got %s" % (target, expected, out)
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
