"""The plan tree's blanket contamination exemption does NOT cover LEDGER files.

`check_contamination._ALLOWLIST_GLOBS` carries `.claude/plans/*`, and fnmatch's
`*` crosses `/` — so the ENTIRE plan tree is exempt from the scan. That was
written for plan PROSE, which a maintainer reads before committing.

PLAN-179 W2 puts a different kind of file in that same tree: a per-plan
`LEDGER.md` appended INCREMENTALLY, mid-session, by the model, from material
that includes agent returns and tool output — in a PUBLIC repository. These
tests hold down the NEGATIVE exception that cures it, and they are written so
each one fails for a DIFFERENT reason:

  1. the positive control — a planted marker in a plan `LEDGER.md` is REPORTED,
     and the report names that path;
  2. the scope control — the SAME bytes in a sibling plan file stay exempt.
     Without this, "the exception works" is indistinguishable from "somebody
     deleted `.claude/plans/*` and the whole tree is being scanned now";
  3. the clean control — a ledger with no marker is green, so the rule is not
     just "LEDGER.md always fails";
  4. the deny-wins control — the walker STILL answers `is_allowlisted=True` for
     the very path `scan()` reports. The two decisions disagree by design, and
     asserting that directly is what proves the override is real rather than an
     accident of some other filter;
  5. depth + basename controls on the pure predicate, because a rule an author
     can sidestep by moving the file one directory down is not a rule.

MARKER CONSTRUCTION: the detector strings are built by CONCATENATION at
runtime, never written as literals. This file is not on the exact-path
allowlist (deliberately — self-exemption is the defect PLAN-183 W2 A7 removed
from this very module), so a literal marker here would make the guard fail on
its own test. The markers are the shipped synthetic placeholders from
`_PLACEHOLDER_TERMS`; no real identity is used anywhere in this file.

Isolation: `TestEnvContext` + a throwaway git repo under `tempfile.mkdtemp()`.
The real `$HOME` and the real project dir are never touched, and no git command
in this file runs against the working repository.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.file_walker import FileWalker  # noqa: E402

import check_contamination as cc  # noqa: E402

# Built at runtime so the literal never appears in this file — see the
# MARKER CONSTRUCTION note in the module docstring. Matches the shipped
# `Example\s+Owner` alternative of `_PLACEHOLDER_TERMS`.
_MARKER = "Example" + " " + "Owner"
_CLEAN = "PLAN-999 checkpoint: unit AC-3, commit 0123abc, no blockers.\n"


class _LedgerExceptionBase(TestEnvContext):
    """Throwaway git repo; `scan()` runs against it, never against this repo."""

    def setUp(self) -> None:
        super().setUp()
        # `.resolve()` on BOTH sides: on macOS `/tmp` is a symlink to
        # `/private/tmp`, and an unresolved root makes every later
        # `relative_to` comparison measure FORMAT instead of identity.
        self.root = Path(
            tempfile.mkdtemp(prefix="ceo-ledger-contam-")
        ).resolve()
        for args in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@t.invalid"],
            ["git", "config", "user.name", "t"],
        ):
            subprocess.run(
                args, cwd=self.root, check=True, capture_output=True
            )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        super().tearDown()

    def commit(self, rel: str, content: str) -> Path:
        return self.commit_bytes(rel, content.encode("utf-8"))

    def commit_bytes(self, rel: str, content: bytes) -> Path:
        """Byte-level sibling of `commit`.

        The undecodable-ledger controls below need to plant a byte that is
        not valid UTF-8, so they cannot go through `write_text` — which
        would refuse to encode it in the first place.
        """
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        subprocess.run(
            ["git", "add", "-A"], cwd=self.root, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "fixture", "-q"],
            cwd=self.root, check=True, capture_output=True,
        )
        return path

    def rels(self):
        return sorted(
            p.resolve().relative_to(self.root).as_posix()
            for p in cc.scan(self.root)
        )


class TestPlanLedgerIsScanned(_LedgerExceptionBase):

    def test_contaminated_plan_ledger_is_reported(self) -> None:
        """(i) POSITIVE CONTROL — the finding names the ledger path."""
        self.commit(
            ".claude/plans/PLAN-999/LEDGER.md",
            "checkpoint written by an agent return mentioning %s\n" % _MARKER,
        )
        self.assertEqual(
            self.rels(), [".claude/plans/PLAN-999/LEDGER.md"]
        )

    def test_ledger_archive_is_scanned_too(self) -> None:
        """The archive is the same class — it is where old entries GO."""
        self.commit(
            ".claude/plans/PLAN-999/LEDGER-ARCHIVE.md",
            "archived: %s\n" % _MARKER,
        )
        self.assertEqual(
            self.rels(), [".claude/plans/PLAN-999/LEDGER-ARCHIVE.md"]
        )

    def test_a_deeper_ledger_is_scanned(self) -> None:
        """Depth-independent: moving the file one level down is not an out."""
        self.commit(
            ".claude/plans/PLAN-999/w0/LEDGER.md", "deep: %s\n" % _MARKER
        )
        self.assertEqual(
            self.rels(), [".claude/plans/PLAN-999/w0/LEDGER.md"]
        )

    def test_clean_ledger_is_green(self) -> None:
        """(iii) The rule is 'scan it', not 'always fail it'."""
        self.commit(".claude/plans/PLAN-999/LEDGER.md", _CLEAN)
        self.assertEqual(self.rels(), [])


class TestTheExemptionSurvivesForEverythingElse(_LedgerExceptionBase):

    def test_sibling_plan_file_with_the_same_bytes_stays_exempt(self) -> None:
        """(ii) SCOPE CONTROL — the cure is a class, not 'drop the glob'.

        Same content, same directory, different basename. If this ever goes
        RED the exception stopped being surgical and the whole plan tree is
        back in the scan.
        """
        body = "note mentioning %s\n" % _MARKER
        self.commit(".claude/plans/PLAN-999/notas.md", body)
        self.assertEqual(self.rels(), [])

    def test_plan_markdown_at_the_top_level_stays_exempt(self) -> None:
        self.commit(
            ".claude/plans/PLAN-999-work-boundary.md", "plan: %s\n" % _MARKER
        )
        self.assertEqual(self.rels(), [])

    def test_a_non_plan_file_is_scanned_as_before(self) -> None:
        """Control for the control: the detector itself still fires."""
        self.commit("src/notes.md", "prose naming %s\n" % _MARKER)
        self.assertEqual(self.rels(), ["src/notes.md"])


class TestDenyWinsOverAllow(_LedgerExceptionBase):

    def test_the_walker_still_allowlists_the_path_scan_reports(self) -> None:
        """(iv) The two decisions disagree BY DESIGN — assert both halves.

        A test that only checked `scan()` could pass because some unrelated
        filter changed. This one pins the actual mechanism: the allowlist
        says "exempt", the negative exception overrides it, and the file is
        scanned anyway.
        """
        path = self.commit(
            ".claude/plans/PLAN-999/LEDGER.md", "x %s\n" % _MARKER
        )
        walker = FileWalker(
            repo_root=self.root,
            mode="git",
            path_allowlist_exact=cc._ALLOWLIST_EXACT,
            path_allowlist_globs=cc._ALLOWLIST_GLOBS,
        )
        self.assertTrue(
            walker.is_allowlisted(path),
            "`.claude/plans/*` should still exempt this path — if it does "
            "not, the exemption was deleted rather than narrowed",
        )
        self.assertEqual(self.rels(), [".claude/plans/PLAN-999/LEDGER.md"])


class TestAnUndecodableProtectedLedgerFailsClosed(_LedgerExceptionBase):
    """(vi) rail round-1 P1 — 'could not parse it' must not read as 'clean'.

    `scan()` decodes every candidate as UTF-8 and skips the file on
    `UnicodeDecodeError`. For an allowlisted file that is harmless. For the
    never-allowlisted class it was a FAIL-OPEN with a one-byte trigger, and
    it was reachable: a `LEDGER.md` is appended by the model mid-session
    from agent returns and tool output, so a stray byte is a plausible
    accident and NOBODY reads the file before it is committed.

    These four fail for different reasons on purpose: the first is the
    reproduction, the second pins that the rule is about parseability and
    not about the marker, and the last two pin that the fail-closed arm did
    NOT leak outside the protected class.
    """

    # One 0xFF — never valid UTF-8 in any position.
    _BAD = b"\xff"

    def test_undecodable_ledger_carrying_a_marker_is_reported(self) -> None:
        """POSITIVE CONTROL — this is the exact escape the rail named.

        Pre-cure this returned `[]`: the decode raised on line 1 and the
        marker two lines below was never looked at.
        """
        self.commit_bytes(
            ".claude/plans/PLAN-999/LEDGER.md",
            b"checkpoint " + self._BAD + b" stray byte\n"
            b"agent return mentioning " + _MARKER.encode("utf-8") + b"\n",
        )
        self.assertEqual(
            self.rels(), [".claude/plans/PLAN-999/LEDGER.md"],
            "an undecodable protected ledger must be REPORTED — skipping it "
            "makes an unverified file indistinguishable from a clean one",
        )

    def test_undecodable_ledger_without_a_marker_is_reported_too(self) -> None:
        """The verdict keys on PARSEABILITY, not on finding a marker.

        If this were green only when a marker is present, the guard would
        still be trusting a file it never managed to read.
        """
        self.commit_bytes(
            ".claude/plans/PLAN-999/LEDGER.md",
            _CLEAN.encode("utf-8") + self._BAD + b"\n",
        )
        self.assertEqual(self.rels(), [".claude/plans/PLAN-999/LEDGER.md"])

    def test_an_undecodable_sibling_plan_file_stays_exempt(self) -> None:
        """NEGATIVE CONTROL — the fail-closed arm is scoped to the class.

        Same bytes, same directory, different basename. RED here would mean
        the cure widened into the plan tree the exemption exists to keep out.
        """
        self.commit_bytes(
            ".claude/plans/PLAN-999/notas.md",
            b"note " + self._BAD + b" " + _MARKER.encode("utf-8") + b"\n",
        )
        self.assertEqual(self.rels(), [])

    def test_an_undecodable_non_plan_file_is_still_skipped(self) -> None:
        """NEGATIVE CONTROL — the GLOBAL decode behaviour is untouched.

        Outside the protected class an undecodable blob is still skipped,
        exactly as before the cure. This is what makes the change a narrow
        exception rather than a new repo-wide failure mode.
        """
        self.commit_bytes(
            "src/notes.md",
            b"prose " + self._BAD + b" " + _MARKER.encode("utf-8") + b"\n",
        )
        self.assertEqual(self.rels(), [])


class TestIsNeverAllowlistedPredicate(TestEnvContext):
    """Pure-function boundary cases, no filesystem involved."""

    def test_true_for_plan_ledgers_at_any_depth(self) -> None:
        for rel in (
            ".claude/plans/PLAN-179/LEDGER.md",
            ".claude/plans/PLAN-179/LEDGER-ARCHIVE.md",
            ".claude/plans/PLAN-179/w0/LEDGER.md",
            ".claude/plans/archive/PLAN-100/LEDGER.md",
        ):
            self.assertTrue(cc.is_never_allowlisted(rel), rel)

    def test_false_outside_the_plan_tree(self) -> None:
        for rel in (
            "LEDGER.md",
            "docs/LEDGER.md",
            ".claude/LEDGER.md",
            ".claude/adr/LEDGER.md",
        ):
            self.assertFalse(cc.is_never_allowlisted(rel), rel)

    def test_false_for_a_merely_similar_basename(self) -> None:
        for rel in (
            ".claude/plans/PLAN-179/LEDGER-NOTES.md",
            ".claude/plans/PLAN-179/ledger.md",
            ".claude/plans/PLAN-179/MY-LEDGER.md",
            ".claude/plans/PLAN-179/LEDGER.md.bak",
        ):
            self.assertFalse(cc.is_never_allowlisted(rel), rel)

    def test_false_for_the_plans_directory_itself(self) -> None:
        self.assertFalse(cc.is_never_allowlisted(".claude/plans"))

    def test_true_for_a_ledger_directly_under_plans(self) -> None:
        """The shallowest case, and the reason this is not a glob.

        `.claude/plans/*/LEDGER.md` would NOT match this path (fnmatch's
        `*` cannot match the empty segment), so a ledger parked one level
        UP would slip back under the blanket exemption. Same class, same
        risk, so the basename rule covers it.
        """
        self.assertTrue(cc.is_never_allowlisted(".claude/plans/LEDGER.md"))

    def test_the_basenames_mirror_the_producer(self) -> None:
        """The two names come from `check_ledger_checkpoint.py`.

        Skipped until the W2 ceremony lands that hook — a test that
        silently passes on a missing module is not a test.
        """
        hook = _REPO_ROOT / ".claude" / "hooks" / "check_ledger_checkpoint.py"
        if not hook.is_file():
            self.skipTest("check_ledger_checkpoint.py not landed yet")
        src = hook.read_text(encoding="utf-8")
        for name in sorted(cc._NEVER_ALLOWLISTED_BASENAMES):
            self.assertIn(
                '"%s"' % name, src,
                "%r is not a basename the ledger hook actually writes" % name,
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
