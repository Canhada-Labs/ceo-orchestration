"""RULE 2 of `check_contamination`: absolute home paths in docs/ and plans/.

The TERM rule exempts those two trees from almost everything — `.claude/plans/*`
is a wholesale glob and most of `docs/` sits on the exact allowlist — so an
absolute `/Users/<name>/` there was invisible to the gate. PLAN-186 §Riscos
recorded the follow-up (Codex P1, S339); RULE 2 of the module is it.

Each class below fails for a DIFFERENT reason, because "the rule works" and
"the rule now scans everything" are otherwise indistinguishable:

  1. DETECTION — a planted path in docs/ and in a plan artifact is reported,
     in all three shapes (`/Users/`, `/home/`, the harness slug), as file:line.
  2. SCOPE — the SAME bytes outside the two trees are NOT reported. Without
     this, deleting the scope tuple would still leave the tests green.
  3. PLACEHOLDERS — `/Users/devuser/`, `/home/runner/`, `/Users/<user>/`, an
     elided segment and a `/home/`-shaped URL route stay clean, so the rule
     does not punish the documented placeholder style.
  4. NOTHING IS EXEMPT BY NAME — the same bytes under an `OWNER-*.sh`
     name, an `.asc` name and a sentinel name are ALL reported, WITH a
     real armoured signature beside the sentinel and a granted
     fingerprint inside it. The signed-sentinel RULE waiver was
     deleted: every one of its four checks was transplantable by
     anyone who could write a file, so it was exemption by the name
     `*-approved.md` in a content-shaped costume. The ONLY waiver left
     is a row pinned to the sha256 of the content it waives.
  5. THE ALLOWLIST — a row makes a file GREEN and its REASON is echoed; a row
     with no reason, a duplicate row, an absolute path and the emitted
     placeholder reason are all MALFORMED and fail closed; a stale row is
     advisory.
  6. FAIL-CLOSED ON INPUT — an unreadable allowlist and an unreadable in-scope
     file are rc 2, not a clean run; undecodable BYTES are still scanned.
  7. NO SECOND COPY OF THE LEAK — the CLI output never contains the planted
     name; findings land in a public CI log.
  8. RULE 1 UNTOUCHED — plan prose carrying a term marker stays exempt.
  9. THE FATAL PATH DOES NOT LEAK EITHER — rc 2 names the file repo-relative
     and never prints `str(OSError)`, whose `filename` is ABSOLUTE. Without
     this, the rule refuses to quote a leak while printing one.
 10. UNKNOWN ARGUMENTS STAY TOLERATED, AND STOP BEING SILENT — the module this
     rule joined ignored argv, and the delivered wrapper execs it with "$@".
 11. THE GATE DOES NOT ECHO WHAT IT WAS HANDED — a waiver REASON, an allowlist
     path outside the repo and an ignored CLI token all pass the rule's own
     predicate before they are printed, and a contaminated waiver row is
     refused at parse time. Four leaking print sites, one choke point.
 12. A TRACKED SYMLINK IS SCANNED AS WHAT GIT STORES — the target STRING. It
     was a false negative: `is_file()` follows the link.
 13. A WAIVER IS PINNED TO CONTENT — a row waives the bytes a human read,
     so one added byte lapses it and the gate goes red naming the digest.
     Without this a row waived a PATH forever, and a second leak in an
     already-waived file landed in silence.
 14. THE GATE HAS NO SPELLING THAT TURNS IT OFF — an abbreviation of the
     rows-only flag used to select it and return 0 without a verdict.

MARKER CONSTRUCTION: the planted owner name is a synthetic word that is not on
the placeholder list and is nobody's handle. No real identity and no real home
path appears in this file; the term-rule markers are the shipped synthetic
placeholders from `_PLACEHOLDER_TERMS`, built by concatenation (this file is
deliberately NOT on the term allowlist).

Isolation: `TestEnvContext` plus a throwaway git repo under
`tempfile.mkdtemp()`. The real `$HOME`, the real project dir and the live audit
log are never touched. Every test that MUTATES anything does so inside that
throwaway repo. One class is deliberately different and says so in its name:
`TestShippedAllowlist` READS this repository (and runs read-only git queries
against it) to assert facts about the shipped file -- claiming otherwise was
a false statement about the file it stands in (pair-rail round 3, P3).
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

import check_contamination as cc  # noqa: E402

#: Synthetic home-directory owner: not a placeholder, not a real handle.
_OWNER = "zzfake"
_MAC = "/Users/" + _OWNER + "/work/repo"
_LINUX = "/home/" + _OWNER + "/work/repo"
_SLUG = "-Users-" + _OWNER + "-work-repo"
#: Term-rule marker, concatenated — see MARKER CONSTRUCTION above.
_TERM_MARKER = "Example" + " " + "Owner"


_ARMOR = (
    "-----BEGIN PGP SIGNATURE-----\n"
    "\n"
    "iQENc3ludGhldGljIGRldGFjaGVkIHNpZ25hdHVyZSBib2R5LCB0ZXN0cyBvbmx5\n"
    "IC0tIG92ZXIgdGhlIHNpemUgZmxvb3I=\n"
    "=zzZZ\n"
    "-----END PGP SIGNATURE-----\n"
)
#: A well-formed armoured detached signature, real base64 opening on an
#: OpenPGP signature packet tag. The gate no longer parses one: the
#: signed-sentinel waiver that did was DELETED because every one of its
#: checks was transplantable. This fixture is kept as the FORGERY
#: material of `TestNoWaiverIsEarnedByAName` — the most convincing
#: sidecar anyone could plant, shown buying nothing.

#: The fingerprint the test allowlist grants, and the `Approved-By` line
#: a fixture sentinel must carry to be exempt at all. Synthetic: 40 hex
#: that is neither the Owner key nor any commit in this repository.
#: A syntactically valid digest for rows the PARSER is driven with
#: directly, where no file exists to hash. Tests that go through the
#: gate use `_Base.row()`, which digests the bytes on disk — a constant
#: there would pass while the code hashed something else entirely.
_SHA = "0" * 64
#: KEPT, though nothing grants it any more: the forgery control plants
#: this fingerprint and a real armoured body to prove that a signature
#: shaped exactly like the deleted rule wanted now buys NOTHING.
_FPR = "BEEF" * 10
_SENTINEL_BODY = "Approved-By: @tester " + _FPR + "\n"



class _Base(TestEnvContext):
    """Throwaway git repo; the rule runs against it, never against this one."""

    def setUp(self) -> None:
        super().setUp()
        # `.resolve()` on BOTH sides: on macOS `/tmp` is a symlink to
        # `/private/tmp`, and an unresolved root turns every later
        # `relative_to` into a comparison of FORMAT instead of identity.
        self.root = Path(
            tempfile.mkdtemp(prefix="ceo-personal-path-")
        ).resolve()
        self.allowlist = self.root / "allowlist.txt"
        # EMPTY, and tracked. The fixture allowlist used to grant a
        # signer fingerprint, because without one no sentinel earned the
        # RULE waiver and the sentinel tests measured the empty case.
        # That directive is deleted with the waiver it fed, and a file
        # with no rows waives nothing — which is the default every test
        # below should start from. Tests that drive the parser overwrite
        # this file whole.
        self.allowlist.write_text("", encoding="utf-8")
        for args in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@t.invalid"],
            ["git", "config", "user.name", "t"],
        ):
            subprocess.run(
                args, cwd=self.root, check=True, capture_output=True)
        # TRACKED, like the shipped one. The gate reads an allowlist
        # git does not know as EMPTY (S344, the trackedness check),
        # so an untracked fixture would quietly turn every waiver
        # test into a test of the empty case.
        subprocess.run(
            ["git", "add", "--", self.allowlist.name],
            cwd=self.root, check=True, capture_output=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        super().tearDown()

    def commit(self, rel: str, content: str) -> Path:
        return self.commit_bytes(rel, content.encode("utf-8"))

    def commit_bytes(self, rel: str, content: bytes) -> Path:
        """Byte-level sibling of `commit`, for the undecodable-input control."""
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "fixture", "-q"], cwd=self.root,
                       check=True, capture_output=True)
        return path

    def scan(self):
        return cc.scan_personal_paths(self.root)

    def hits(self):
        return self.scan().hits

    def unwaived_rels(self):
        """What the gate would REPORT — hits no waiver forgave.

        `rels()` is every file that HIT, waived or not, and in v4 that
        is the point: a waiver forgives a finding, it never prevents
        one, so a file a row waives DOES appear in the scan. A test
        that means 'the gate is silent about this file' asks here, and
        one that means 'the file was read at all' asks `rels()`.
        """
        return sorted(h.rel for h in cc.personal_path_verdict(
            self.scan(), {}).unwaived)

    @contextlib.contextmanager
    def stubbed_walk(self, paths, walker=None):
        """Stub the WALK and the INDEX it is checked against, together.

        Since the S344 rail, `scan_personal_paths` refuses a walk that
        saw fewer files than the git index holds — a partial walk is a
        false green over the files it never reached. A test that stubs
        only the walker therefore describes an INCONSISTENT world: it
        either fails, or (worse) passes for the wrong reason. Both sides
        move together here, so a stub says what it means.
        """
        paths = list(paths)
        if walker is None:
            walker = mock.Mock()
            walker.repo_root = self.root
            walker.iter_files.return_value = iter(paths)
        modes = {}
        for path in paths:
            try:
                rel = Path(path).relative_to(self.root).as_posix()
            except ValueError:
                rel = str(path)
            modes[rel] = "100644"
        with mock.patch.object(cc, "FileWalker", return_value=walker), \
                mock.patch.object(cc, "_personal_path_index_modes",
                                  return_value=modes):
            yield

    def row(self, rel: str, reason: str) -> str:
        """One allowlist row for a fixture file — digest and all.

        The digest is taken from the bytes ON DISK the same way the scan
        takes it (a symlink is its target string), so a fixture that
        waives a file waives the bytes it just wrote. Computing it here
        rather than pasting a constant is what makes the pin tests
        meaningful: a hard-coded digest would pass while the code hashed
        something else entirely.
        """
        path = self.root / rel
        raw = (os.fsencode(os.readlink(path)) if path.is_symlink()
               else path.read_bytes())
        return "%s | sha256:%s | %s\n" % (
            rel, hashlib.sha256(raw).hexdigest(), reason)

    def rels(self):
        return sorted(hit.rel for hit in self.hits())

    def assert_mode_000_is_unreadable(self, path: Path) -> None:
        """Skip rather than lie: root (and some CI images) can read 0o000."""
        try:
            path.read_bytes()
        except OSError:
            return
        self.skipTest("this user can read mode-000 files (root?)")

    def cli(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(Path(cc.__file__).resolve()),
             "--root", str(self.root),
             "--personal-path-allowlist", str(self.allowlist)] + list(extra),
            capture_output=True, text=True, check=False,
        )


class TestDetection(_Base):
    """(1) The three shapes, in both trees, reported as file:line."""

    def test_mac_path_in_docs_is_reported(self) -> None:
        self.commit("docs/guide.md", "run it from " + _MAC + " and retry\n")
        self.assertEqual(self.rels(), ["docs/guide.md"])

    def test_linux_path_in_a_plan_artifact_is_reported(self) -> None:
        self.commit(".claude/plans/PLAN-999/rail/codex-r1.md",
                    "cwd was " + _LINUX + "\n")
        self.assertEqual(self.rels(),
                         [".claude/plans/PLAN-999/rail/codex-r1.md"])

    def test_harness_slug_form_is_reported(self) -> None:
        self.commit("docs/notes.md", "state dir /var/x/" + _SLUG + "/s\n")
        self.assertEqual(self.rels(), ["docs/notes.md"])

    def test_hit_carries_every_line_number(self) -> None:
        self.commit("docs/guide.md",
                    "intro\n" + _MAC + "\nmiddle\n" + _LINUX + "\n")
        self.assertEqual(self.hits()[0].lines, (2, 4))

    def test_cli_reports_file_colon_line(self) -> None:
        """The finding a human can act on: path and line, never the line."""
        self.commit("docs/guide.md", "intro\n" + _MAC + "\n")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout + red.stderr)
        self.assertIn("docs/guide.md:2", red.stdout)

    def test_fullwidth_form_normalises_and_is_reported(self) -> None:
        """NFKC runs before the match, as it does for the term rule."""
        self.commit("docs/guide.md", "／Ｕｓｅｒｓ／" + _OWNER + "／work\n")
        self.assertEqual(self.rels(), ["docs/guide.md"])

    def test_a_binary_suffix_no_longer_skips_anything(self) -> None:
        """v3 skipped a REGULAR file by its extension — the last
        name-shaped skip this rule had. An image carries the author's
        home path in its metadata all the time, so the skip was hiding
        exactly the leak the rule looks for. MEASURED before removing
        it: zero in-scope files on the framework tree carry one of
        those suffixes, so it moved no row.
        """
        self.commit_bytes("docs/shot.png",
                          b"\x89PNG\r\n" + _MAC.encode("utf-8"))
        self.assertEqual(self.rels(), ["docs/shot.png"])

    def test_untracked_file_is_not_scanned(self) -> None:
        self.commit("docs/guide.md", "clean\n")
        (self.root / "docs" / "loose.md").write_text(_MAC, encoding="utf-8")
        self.assertEqual(self.rels(), [])

    def test_tracked_but_absent_file_is_skipped_not_fatal(self) -> None:
        """Absence is not unreadable INPUT — `git ls-files` still lists it.

        THIS TEST PINS A DECLARED BOUNDARY, not a safe behaviour, and the
        pair-rail was right to call it out (round 1, P1, both lanes): the
        rule ENUMERATES the index and READS the worktree, so a leaking
        blob staged and then removed or overwritten in the worktree is
        not scanned, and `git commit` lands it. The same split means a
        row pins WORKTREE bytes, not necessarily the bytes being landed.

        It is DECLARED rather than cured because closing it means reading
        blobs through `git cat-file` instead of the filesystem, which
        changes what every digest in the shipped allowlist means — a wave,
        not a free pack. It is also the pre-existing behaviour of RULE 1
        and of `FileWalker`, not something this rule introduced, and in
        CI — where this gate runs — the index and the worktree are the
        same tree by construction. The module header carries the
        declaration; the follow-up plan carries the work.
        """
        self.commit("docs/guide.md", "clean\n")
        (self.root / "docs" / "guide.md").unlink()
        self.assertEqual(self.rels(), [])


class TestScope(_Base):
    """(2) The rule did NOT start scanning the whole tree."""

    OUT_OF_SCOPE = ("README.md", "src/notes.md", "SPEC/v1/x.md",
                    ".claude/adr/ADR-999-x.md", "docsy/guide.md",
                    "x/docs/guide.md")

    def test_same_bytes_outside_the_two_trees_are_not_reported(self) -> None:
        for rel in self.OUT_OF_SCOPE:
            self.commit(rel, "path " + _MAC + "\n")
        self.assertEqual(self.rels(), [])
        # Non-vacuity: the identical bytes ARE reported inside the scope, so
        # the green above is the scope tuple and not a broken matcher.
        self.commit("docs/guide.md", "path " + _MAC + "\n")
        self.assertEqual(self.rels(), ["docs/guide.md"])

    def test_scope_predicate_is_prefix_exact(self) -> None:
        self.assertTrue(cc.in_personal_path_scope("docs/a.md"))
        self.assertTrue(cc.in_personal_path_scope(".claude/plans/a.md"))
        self.assertTrue(cc.in_personal_path_scope(".claude/plans/P/d/a.log"))
        self.assertFalse(cc.in_personal_path_scope("docsy/a.md"))
        self.assertFalse(cc.in_personal_path_scope("x/docs/a.md"))
        self.assertFalse(cc.in_personal_path_scope(".claude/plansy/a.md"))


class TestPlaceholders(_Base):
    """(3) The documented placeholder style stays clean."""

    def test_placeholder_owners_are_not_hits(self) -> None:
        self.commit("docs/quickstart.md", "\n".join([
            "cd /Users/devuser/ceo-orchestration",
            "export H=/home/runner/work/app",
            "see /Users/.../project/file",
            "state dir -Users-devuser-app-x",
            "cp /home/ubuntu/x /Users/you/y",
        ]) + "\n")
        self.assertEqual(self.rels(), [])

    def test_the_angle_bracket_placeholder_is_not_a_hit(self) -> None:
        """The convention the tree already uses: `<user>` is not a segment."""
        self.commit("docs/guide.md", "\n".join([
            "$ cd /Users/<user>/canhada-labs/repo",
            "ambient HOME before : /Users/<redacted>",
            "log at /home/<username-real>/x",
        ]) + "\n")
        self.assertEqual(self.rels(), [])

    def test_url_route_and_nested_directory_are_not_hits(self) -> None:
        self.commit("docs/site.md", "\n".join([
            "open https://example.invalid/home/index for the dashboard",
            "the /srv/home/index page is generated",
            "docs live at https://example.invalid/Users/list",
        ]) + "\n")
        self.assertEqual(self.rels(), [])

    def test_every_declared_placeholder_is_actually_exempt(self) -> None:
        """Per-entry non-vacuity: no dead entry sitting in the list."""
        for seg in sorted(cc._PERSONAL_PATH_PLACEHOLDERS):
            with self.subTest(seg=seg):
                self.assertFalse(
                    cc.line_is_personal_path_hit("cd /Users/%s/work" % seg))
                self.assertFalse(
                    cc.line_is_personal_path_hit("cd /home/%s/work" % seg))
        self.assertNotIn(_OWNER, cc._PERSONAL_PATH_PLACEHOLDERS)

    def test_predicate_is_case_insensitive_on_the_owner(self) -> None:
        self.assertFalse(cc.line_is_personal_path_hit("/Users/DevUser/x"))
        self.assertTrue(cc.line_is_personal_path_hit("/Users/" + _OWNER + "/x"))

    def test_a_bare_tree_root_is_not_a_hit(self) -> None:
        self.assertFalse(cc.line_is_personal_path_hit("ls /Users/"))
        self.assertFalse(cc.line_is_personal_path_hit("ls /home/"))


class TestLiteralFastPath(_Base):
    """The `in`-based shortcut must not become a filter of its own.

    `line_is_personal_path_hit` rejects a line holding none of
    `_PERSONAL_PATH_LITERALS` before touching a regex. This differential
    control drives the predicate and a REGEX-ONLY reference over the same
    corpus and demands the same verdict.
    """

    CORPUS = (
        "",
        "nothing here at all",
        "/Users/" + _OWNER + "/work",
        "/home/" + _OWNER + "/work",
        "-Users-" + _OWNER + "-work-repo",
        "/Users/devuser/work",
        "/home/runner/work/app",
        "/Users/.../work",
        "ls /Users/",
        "ls /home/",
        "https://example.invalid/home/index",
        "x/Users/" + _OWNER + "/work",
        "prefix-Users-" + _OWNER + "-suffix",
        "/USERS/" + _OWNER + "/work",
        "/users/" + _OWNER + "/work",
        "-users-" + _OWNER + "-work",
        "\t\"/Users/" + _OWNER + "/a\", '/home/" + _OWNER + "/b'",
        "/Users/" + _OWNER + " and /Users/devuser",
        "/Users/devuser and /Users/" + _OWNER,
        "/Users/first.last-x/work",
        "/Users/<user>/work",
    )

    @staticmethod
    def _regex_only_reference(line: str) -> bool:
        segments = [m.group(1)
                    for m in cc._PERSONAL_PATH_HOME_RE.finditer(line)]
        segments += [m.group(1)
                     for m in cc._PERSONAL_PATH_SLUG_RE.finditer(line)]
        return any(seg.lower() not in cc._PERSONAL_PATH_PLACEHOLDERS
                   for seg in segments)

    def test_fast_path_matches_the_regex_only_reference(self) -> None:
        agreed_true = 0
        for line in self.CORPUS:
            with self.subTest(line=line):
                reference = self._regex_only_reference(line)
                self.assertEqual(
                    cc._personal_path_names_a_person(line), reference)
                agreed_true += int(reference)
        # Non-vacuity: the corpus must contain real hits, or "they agree"
        # would just mean "both said no to everything".
        self.assertGreaterEqual(agreed_true, 5)

    def test_each_literal_is_reachable(self) -> None:
        """A literal no shape can produce would be a dead branch."""
        for literal, line in (
            ("/Users/", "/Users/" + _OWNER + "/w"),
            ("/home/", "/home/" + _OWNER + "/w"),
            ("-Users-", "-Users-" + _OWNER + "-w"),
        ):
            with self.subTest(literal=literal):
                self.assertIn(literal, cc._PERSONAL_PATH_LITERALS)
                self.assertTrue(cc.line_is_personal_path_hit(line))


class TestUndecodableByteCannotHide(_Base):
    """An undecodable byte must not read as "the guard found nothing".

    Rail round 1 (codex) drove exactly these three byte strings through the
    matcher and got `()` from all three: `errors="replace"` turns the byte
    into U+FFFD, which TRUNCATES the owner segment to a placeholder prefix
    and SPLITS the literal the fast path looks for. The cure is the second
    reading, with every U+FFFD removed.
    """

    #: (raw bytes of one line, what the FIRST reading alone would answer)
    EVASIONS = (
        b"/Users/dev\xffzzfake/work",     # segment truncated to `dev`
        b"/home/runner\xffzzfake/work",   # segment truncated to `runner`
        b"/Us\xffers/zzfake/work",        # the `/Users/` literal split
        b"-Users-\xffzzfake-work",        # the slug literal split
    )

    def test_the_second_reading_is_still_load_bearing(self) -> None:
        """The control, narrowed by a cure rather than weakened.

        Before the owner class became a DELIMITER class (pair-rail round
        1, P1), the first reading missed ALL FOUR of these: the
        replacement character was not in `[\\w.\\-]`, so a marker inside
        the segment truncated it to a placeholder. The widened class now
        catches the two TRUNCATION shapes on the first pass, because
        U+FFFD is simply part of the segment and the segment is no longer
        a placeholder.

        The two LITERAL-SPLIT shapes are untouched by that: a marker
        inside `/Users/` or inside `-Users-` means no literal is present
        at all, so no regex can run. Those are what the second reading is
        for, and asserting exactly that keeps this control a control
        instead of a test that agrees with whatever the code does.
        """
        missed = []
        for raw in self.EVASIONS:
            with self.subTest(raw=raw):
                line = raw.decode("utf-8", errors="replace")
                # the property that matters, for every shape
                self.assertTrue(cc.line_is_personal_path_hit(line))
                if not cc._personal_path_names_a_person(line):
                    missed.append(raw)
        # WHICH ones the first reading misses is derived, never declared:
        # the widening moved that line once already, and a hard-coded
        # list would have had to be edited to agree with it. What must
        # not change is that the second reading is still doing work.
        self.assertTrue(missed,
                        "the second reading no longer catches anything "
                        "the first one misses — it is now dead code, and "
                        "this control has stopped controlling")

    def test_the_second_reading_catches_them(self) -> None:
        for raw in self.EVASIONS:
            with self.subTest(raw=raw):
                line = raw.decode("utf-8", errors="replace")
                self.assertTrue(cc.line_is_personal_path_hit(line))

    def test_the_second_reading_does_not_invent_hits(self) -> None:
        """Removing U+FFFD must not turn a placeholder line into a finding."""
        for raw in (b"plain \xff text with no path",   # no literal either way
                    b"\xff\xfe\xff\xfe"):                  # markers, nothing else
            with self.subTest(raw=raw):
                line = raw.decode("utf-8", errors="replace")
                self.assertFalse(cc.line_is_personal_path_hit(line))

    def test_a_removal_that_RECONSTRUCTS_a_placeholder_is_a_hit(self) -> None:
        """`/Users/dev<0xFF>user/` is a HIT — pair-rail land round 1, P1.

        This case was written into the suite as intended behaviour and it
        was a false green: the marker truncates the owner to `dev` and its
        removal reconstructs `devuser`, and BOTH are placeholders, so a
        real owner hid behind one byte. The third clause answers it as
        unparseable input, not as a placeholder.
        """
        for raw in (b"/Users/dev\xffuser/work",
                    b"/home/test\xffuser/x",
                    b"-Users-you\xffruser-repo"):
            with self.subTest(raw=raw):
                line = raw.decode("utf-8", errors="replace")
                self.assertTrue(cc.line_is_personal_path_hit(line))

    def test_a_surrogateescaped_byte_is_a_marker_too(self) -> None:
        """What `readlink()` hands back is not U+FFFD (land round 1, P1)."""
        line = b"/Users/dev\xffzzfake/work".decode(
            "utf-8", errors="surrogateescape")
        self.assertNotIn("\ufffd", line)
        self.assertTrue(cc.line_is_personal_path_hit(line))

    def test_a_byte_INSIDE_a_placeholder_is_reported_by_design(self) -> None:
        """`/home/run<0xFF>ner/` IS flagged — and that is the right answer.

        The FIRST reading truncates the segment to `run`, which is not on the
        placeholder list, so the line is a finding before the second reading
        is even consulted. The guard cannot know the bytes spelled `runner`;
        fail-closed means the human looks. Recorded here so a later change
        that "fixes" this false positive is a deliberate loosening, not a
        silent one.
        """
        line = b"/home/run\xffner/work".decode("utf-8", errors="replace")
        self.assertTrue(cc._personal_path_names_a_person(line))
        self.assertTrue(cc.line_is_personal_path_hit(line))

    def test_end_to_end_through_the_file_walk(self) -> None:
        self.commit_bytes("docs/transcript.log",
                          b"clean\n" + self.EVASIONS[0] + b"\n")
        self.assertEqual(self.rels(), ["docs/transcript.log"])
        self.assertEqual(self.hits()[0].lines, (2,))


class TestLineNumbersMatchGrep(_Base):
    """`file:line` must be the line a human resolves with sed/grep."""

    def test_a_vertical_tab_does_not_shift_the_line_number(self) -> None:
        """`splitlines()` would break on \\x0b; `split("\\n")` does not."""
        body = "one\ntwo\x0bstill two\n" + _MAC + "\n"
        self.commit("docs/guide.md", body)
        self.assertEqual(self.hits()[0].lines, (3,))
        # Non-vacuity: `splitlines()` really does answer differently here.
        self.assertNotEqual(len(body.splitlines()), len(body.split("\n")) - 1)

    def test_crlf_input_keeps_the_line_number(self) -> None:
        self.commit_bytes(
            "docs/win.md",
            b"one\r\ntwo\r\n" + _MAC.encode("utf-8") + b"\r\n")
        self.assertEqual(self.hits()[0].lines, (3,))


class TestNothingIsExemptByName(_Base):
    """(4) The P1 that dropped v3: a NAME could keep a file from being read.

    `is_personal_path_exempt` waived any basename `OWNER-*.sh` BEFORE a
    byte was read, so a tracked symlink pointing at a real home path
    walked through the gate that failed the same target under any other
    name. v4 deleted the function: nothing decides a file is not looked
    at. These tests assert the ABSENCE, which is the only form the cure
    can take — enumerating safe names is what failed three times.
    """

    #: Names that USED to waive, and the sibling that never did. Both
    #: halves must now be reported, or the removal was cosmetic.
    CASES = (
        (".claude/plans/PLAN-999/OWNER-S999-LAND.sh",
         ".claude/plans/PLAN-999/finalize-s999.sh"),
        ("docs/OWNER-NOTE.sh", "docs/plain-note.md"),
    )

    def test_the_function_that_waived_by_name_is_gone(self) -> None:
        """Named explicitly: a re-introduction must fail LOUDLY here."""
        self.assertFalse(hasattr(cc, "is_personal_path_exempt"),
                         "exemption-by-name is back")

    def test_an_owner_named_file_is_scanned_like_its_sibling(self) -> None:
        body = "anchor " + _MAC + "\n"
        for named, sibling in self.CASES:
            self.commit(named, body)
            self.commit(sibling, body)
        expected = sorted([n for n, _s in self.CASES]
                          + [s for _n, s in self.CASES])
        self.assertEqual(self.rels(), expected,
                         "a name still decides whether a file is read")
        self.assertEqual(self.cli().returncode, 1)

    def test_a_symlink_named_owner_sh_is_scanned(self) -> None:
        """The reproduction from the land rail, byte for byte.

        Two tracked symlinks with the SAME target and different names.
        On v3: `docs/OWNER-leak.sh` MISSED, `docs/plain-leak.md` HIT.
        """
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        for name in ("OWNER-leak.sh", "plain-leak.md"):
            os.symlink(_MAC + "/repo", self.root / "docs" / name)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        self.assertEqual(self.rels(),
                         ["docs/OWNER-leak.sh", "docs/plain-leak.md"])

    def test_a_binary_suffix_does_not_skip_a_regular_file(self) -> None:
        """The LAST name-shaped skip: `_SKIP_SUFFIXES` on a real file.

        An image carries the author's home path in its metadata all the
        time, which is exactly the leak this rule looks for.
        """
        self.commit_bytes("docs/shot.png",
                          b"\x89PNG\r\n" + _MAC.encode("utf-8") + b"\n")
        self.assertEqual(self.rels(), ["docs/shot.png"])


class TestAllowlistGrammar(_Base):
    """(5) The tracked waiver file: parsed whole, or reported — never dropped."""

    def _load(self, text: str):
        self.allowlist.write_text(text, encoding="utf-8")
        entries, malformed = cc.load_personal_path_allowlist(
            self.allowlist)
        return entries, malformed

    def test_absent_file_is_empty_not_fatal(self) -> None:
        entries, malformed = cc.load_personal_path_allowlist(
            self.root / "nope.txt")
        self.assertEqual((entries, malformed), ({}, []))

    def test_valid_rows_parse(self) -> None:
        entries, malformed = self._load(
            "# comment\n\ndocs/a.md | sha256:%s | frozen transcript\n"
            ".claude/plans/P/x.log | sha256:%s | ceremony log\n"
            % (_SHA, _SHA))
        self.assertEqual(malformed, [])
        self.assertEqual(entries["docs/a.md"].reason, "frozen transcript")
        self.assertEqual(entries["docs/a.md"].sha256, _SHA)
        self.assertEqual(
            entries[".claude/plans/P/x.log"].reason, "ceremony log")

    def test_a_v3_row_without_a_digest_is_malformed(self) -> None:
        """An allowlist carried over from v3 fails LOUDLY, never waives.

        The grammar changed under the operator's feet, so the one thing
        the parser must not do is read an old row as a waiver with no
        pin — that would be the "waives forever" defect surviving the
        cure that was supposed to remove it.
        """
        entries, malformed = self._load(
            "docs/a.md | frozen transcript\n"
            "docs/b.md | sha256:%s | pinned 2026\n" % _SHA)
        self.assertEqual(malformed, [1])
        self.assertEqual(sorted(entries), ["docs/b.md"])

    def test_a_digest_that_is_not_64_hex_is_malformed(self) -> None:
        for bad in ("0" * 63, "0" * 65, "g" * 64, "", "SHA256:" + "0" * 64):
            with self.subTest(bad=bad[:12]):
                entries, malformed = self._load(
                    "docs/a.md | sha256:%s | reason 2026\n" % bad)
                self.assertEqual(malformed, [1])
                self.assertEqual(entries, {})

    def test_the_digest_is_compared_case_insensitively(self) -> None:
        """A human pasting an upper-case digest waives what they meant."""
        entries, malformed = self._load(
            "docs/a.md | sha256:%s | reason 2026\n" % ("ABCDEF" + "0" * 58))
        self.assertEqual(malformed, [])
        self.assertEqual(entries["docs/a.md"].sha256, "abcdef" + "0" * 58)

    def test_reason_may_contain_a_pipe_and_is_stripped(self) -> None:
        entries, malformed = self._load(
            "docs/a.md | sha256:%s |  a | b 2026 review  \n" % _SHA)
        self.assertEqual(malformed, [])
        self.assertEqual(entries["docs/a.md"].reason, "a | b 2026 review")

    def test_rows_that_waive_nothing_are_malformed(self) -> None:
        entries, malformed = self._load("\n".join([
            "docs/ok.md | sha256:%s | fine 2026" % _SHA,
            "docs/no-reason.md | sha256:%s |" % _SHA,
            "docs/no-pipe.md",
            "/abs/path.md | sha256:%s | absolute" % _SHA,
            "docs/../etc/x.md | sha256:%s | traversal" % _SHA,
            "docs/emitted.md | sha256:%s | %s"
            % (_SHA, cc._PERSONAL_PATH_UNREASONED),
            "docs/with space.md | sha256:%s | spaced 2026" % _SHA,
            "docs/no-digest.md | just a reason",
        ]) + "\n")
        self.assertEqual(malformed, [2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(sorted(entries), ["docs/ok.md"])

    def test_duplicate_path_fails_closed(self) -> None:
        """Ambiguity waives NOTHING: the entry is removed, the row named."""
        entries, malformed = self._load(
            "docs/a.md | sha256:%s | one row 2026\n"
            "docs/a.md | sha256:%s | two row 2026\n" % (_SHA, _SHA))
        self.assertEqual(malformed, [2])
        self.assertNotIn("docs/a.md", entries)

    def test_malformed_rows_are_reported_by_number_never_content(self) -> None:
        self.commit("docs/frozen.md", "at " + _MAC + "\n")
        self.allowlist.write_text(
            self.row("docs/frozen.md", "frozen 2026")
            + "not-a-row-" + _OWNER + "\n",
            encoding="utf-8")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout)
        self.assertIn("MALFORMED", red.stdout)
        self.assertIn("row 2", red.stdout)
        self.assertNotIn(_OWNER, red.stdout)


class TestVerdict(_Base):
    """The pure classification, driven directly."""

    #: Two digests that are not each other. Written out rather than
    #: computed, because this class drives the PURE split and must not
    #: depend on a filesystem to say what "the same bytes" means.
    SHA_A = "a" * 64
    SHA_B = "b" * 64

    def _scan(self, hits):
        return cc.PersonalPathScan(hits=hits)

    def test_unwaived_waived_and_stale(self) -> None:
        hits = [cc.PersonalPathHit(rel="docs/new.md", lines=(1,),
                                   sha256=self.SHA_A),
                cc.PersonalPathHit(rel="docs/known.md", lines=(2, 3),
                                   sha256=self.SHA_A)]
        allowlist = {
            "docs/known.md": cc.PersonalPathRow(self.SHA_A, "frozen 2026"),
            "docs/gone.md": cc.PersonalPathRow(self.SHA_A, "archived"),
        }
        verdict = cc.personal_path_verdict(self._scan(hits), allowlist, [7])
        self.assertEqual([h.rel for h in verdict.unwaived], ["docs/new.md"])
        self.assertEqual(verdict.waived, [("docs/known.md", "frozen 2026")])
        self.assertEqual(verdict.stale, ["docs/gone.md"])
        self.assertEqual(verdict.malformed, [7])
        self.assertEqual(verdict.mismatched, [])

    def test_a_row_pinning_other_bytes_is_mismatched_not_unwaived(self) -> None:
        """Its own category: the operator RE-READS, never re-decides."""
        hits = [cc.PersonalPathHit(rel="docs/known.md", lines=(2,),
                                   sha256=self.SHA_B)]
        allowlist = {
            "docs/known.md": cc.PersonalPathRow(self.SHA_A, "frozen 2026")}
        verdict = cc.personal_path_verdict(self._scan(hits), allowlist)
        self.assertEqual(verdict.mismatched, ["docs/known.md"])
        self.assertEqual(verdict.waived, [])
        self.assertEqual(verdict.unwaived, [])

    def test_a_hit_with_no_digest_can_never_be_waived_by_a_row(self) -> None:
        """Fail-closed: nothing to pin means nothing a row can promise."""
        hits = [cc.PersonalPathHit(rel="docs/known.md", lines=(2,))]
        allowlist = {
            "docs/known.md": cc.PersonalPathRow(self.SHA_A, "frozen 2026")}
        verdict = cc.personal_path_verdict(self._scan(hits), allowlist)
        self.assertEqual(verdict.mismatched, ["docs/known.md"])

    def test_a_name_hit_is_waived_by_nothing_at_all(self) -> None:
        """Line 0 short-circuits the ONE waiver channel there is.

        It used to short-circuit two, and the second was the point:
        a rule waiver decided by the scan could have forgiven a NAME
        hit before any row was consulted. That channel is deleted, so
        what is left to prove is that a row -- with a MATCHING digest,
        which is the strongest row there is -- still does not waive a
        path.
        """
        rel = "docs/-Users-someone-x/note.md"
        hits = [cc.PersonalPathHit(
            rel=rel, lines=(cc._PERSONAL_PATH_NAME_LINE, 4),
            sha256=self.SHA_A)]
        verdict = cc.personal_path_verdict(
            self._scan(hits),
            {rel: cc.PersonalPathRow(self.SHA_A, "frozen 2026")})
        self.assertEqual([h.rel for h in verdict.unwaived], [rel])
        self.assertEqual(verdict.waived, [])
        self.assertEqual(verdict.mismatched, [])


class TestCliAllowlist(_Base):
    """(5) RED without a row, GREEN with one, and the REASON is echoed."""

    REASON = "frozen rail transcript, kept verbatim"

    def test_planted_path_is_red_and_a_row_makes_it_green(self) -> None:
        self.commit("docs/leak.md", "one\nsee " + _MAC + "\n")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout + red.stderr)
        self.assertIn("docs/leak.md:2", red.stdout)
        self.allowlist.write_text(
            self.row("docs/leak.md", self.REASON), encoding="utf-8")
        green = self.cli()
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)
        # The reason is ECHOED: a waiver nobody can see is a waiver nobody
        # reviews.
        self.assertIn(self.REASON, green.stdout)
        self.assertIn("honoured allowlist rows (1", green.stdout)

    def test_a_row_waives_only_the_path_it_names(self) -> None:
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        self.commit("docs/other.md", "see " + _MAC + "\n")
        self.allowlist.write_text(
            self.row("docs/leak.md", "frozen 2026"), encoding="utf-8")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout)
        self.assertIn("docs/other.md:1", red.stdout)
        self.assertNotIn("docs/leak.md:", red.stdout)

    def test_removing_a_row_does_not_silence_the_finding(self) -> None:
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        self.allowlist.write_text(
            self.row("docs/leak.md", "frozen 2026"), encoding="utf-8")
        self.assertEqual(self.cli().returncode, 0)
        self.allowlist.write_text("", encoding="utf-8")
        self.assertEqual(self.cli().returncode, 1)

    def test_a_stale_row_is_advisory_and_fatal_only_on_demand(self) -> None:
        self.commit("docs/keep.md", "clean\n")
        self.allowlist.write_text(
            "docs/gone.md | sha256:%s | archived\n" % _SHA,
            encoding="utf-8")
        advisory = self.cli()
        self.assertEqual(advisory.returncode, 0, advisory.stdout)
        self.assertIn("stale", advisory.stdout)
        strict = self.cli("--fail-on-stale")
        self.assertEqual(strict.returncode, 1, strict.stdout)
        self.assertIn("STALE", strict.stdout)

    def test_emitted_rows_are_refused_until_a_reason_is_written(self) -> None:
        """The generator cannot be used to skip the decision."""
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        emitted = self.cli("--emit-personal-path-rows")
        self.assertEqual(emitted.returncode, 0, emitted.stdout)
        self.assertEqual(
            emitted.stdout.strip(),
            self.row("docs/leak.md",
                     cc._PERSONAL_PATH_UNREASONED).rstrip("\n"))
        # Pasted verbatim, it does NOT waive the file.
        self.allowlist.write_text(emitted.stdout, encoding="utf-8")
        pasted = self.cli()
        self.assertEqual(pasted.returncode, 1, pasted.stdout)
        self.assertIn("MALFORMED", pasted.stdout)
        # With a reason written on it, it does.
        self.allowlist.write_text(
            self.row("docs/leak.md", "a real reason"), encoding="utf-8")
        self.assertEqual(self.cli().returncode, 0)

    def test_output_never_quotes_the_matched_line(self) -> None:
        """(7) The gate's findings land in a PUBLIC CI log."""
        self.commit("docs/leak.md", "transcript at " + _MAC + "\n")
        red = self.cli()
        self.assertEqual(red.returncode, 1)
        self.assertNotIn(_OWNER, red.stdout)
        self.assertNotIn(_OWNER, red.stderr)

    def test_red_output_names_the_allowlist_relative_to_the_repo(self) -> None:
        """Printing an absolute path would re-introduce a home directory."""
        self.commit("docs/leak.md", "at " + _MAC + "\n")
        red = self.cli()
        self.assertEqual(red.returncode, 1)
        self.assertNotIn(str(self.root), red.stdout)
        self.assertIn("allowlist.txt", red.stdout)

    def test_display_outside_the_repo_names_the_file_not_the_directory(
            self) -> None:
        """It used to return `str(path)` — the absolute leak, side door 2."""
        outside = self.root.parent / "elsewhere.txt"
        shown = cc._personal_path_display(outside, self.root)
        self.assertIn("elsewhere.txt", shown)
        self.assertNotIn(str(self.root.parent), shown)
        self.assertEqual(
            cc._personal_path_display(self.root / "docs" / "a.md", self.root),
            "docs/a.md")

    def test_term_rule_still_runs_and_plan_prose_stays_exempt(self) -> None:
        """(8) Rule 1 is untouched: the plan tree keeps its term exemption."""
        self.commit(".claude/plans/PLAN-999-x.md",
                    "context: " + _TERM_MARKER + "\n")
        self.assertEqual(self.cli().returncode, 0)
        self.assertEqual(cc.scan(self.root), [])
        # ... while the SAME tree fails on a term hit outside the plan tree,
        # so the green above is the exemption and not a dead rule.
        self.commit("src/leak.md", "context: " + _TERM_MARKER + "\n")
        self.assertEqual(self.cli().returncode, 1)
        self.assertEqual([p.name for p in cc.scan(self.root)], ["leak.md"])

    def test_a_term_hit_does_not_hide_a_path_hit(self) -> None:
        """Both rules always run; the exit code is the worse of the two."""
        self.commit("src/leak.md", "context: " + _TERM_MARKER + "\n")
        self.commit("docs/leak.md", "at " + _MAC + "\n")
        red = self.cli()
        self.assertEqual(red.returncode, 1)
        self.assertIn("Contamination found", red.stdout)
        self.assertIn("docs/leak.md:1", red.stdout)


class TestFailClosedOnInput(_Base):
    """(6) Unreadable input is fatal; undecodable bytes are still scanned."""

    def test_undecodable_file_in_scope_is_still_scanned(self) -> None:
        self.commit_bytes(
            "docs/transcript.log",
            b"\xff\xfe binary noise\n" + _MAC.encode("utf-8") + b"\n",
        )
        self.assertEqual(self.rels(), ["docs/transcript.log"])
        self.assertEqual(self.hits()[0].lines, (2,))

    def test_unreadable_allowlist_is_fatal_not_clean(self) -> None:
        self.commit("docs/keep.md", "clean\n")
        self.allowlist.write_text(
            self.row("docs/keep.md", "kept 2026"), encoding="utf-8")
        self.allowlist.chmod(0o000)
        try:
            self.assert_mode_000_is_unreadable(self.allowlist)
            fatal = self.cli()
            self.assertEqual(fatal.returncode, 2, fatal.stdout + fatal.stderr)
            self.assertIn("FATAL", fatal.stderr)
        finally:
            self.allowlist.chmod(0o600)

    def test_unreadable_in_scope_file_is_fatal_not_clean(self) -> None:
        target = self.commit("docs/frozen.md", "clean\n")
        target.chmod(0o000)
        try:
            self.assert_mode_000_is_unreadable(target)
            fatal = self.cli()
            self.assertEqual(fatal.returncode, 2, fatal.stdout + fatal.stderr)
            self.assertIn("FATAL", fatal.stderr)
            self.assertIn("docs/frozen.md", fatal.stderr)
            self.assertRaises(cc.PersonalPathUnreadable,
                              cc.scan_personal_paths, self.root)
        finally:
            target.chmod(0o600)


class TestFatalPathNeverPrintsAnAbsolutePath(_Base):
    """(9) An rc 2 must not print the path the rule exists to keep unprinted.

    Measured on the pre-cure build of this rule: `str(OSError)` renders as
    `[Errno 13] Permission denied: <ABSOLUTE filename>`, so the fatal line read
    `FATAL: cannot read in-scope file docs/frozen.md: [Errno 13] Permission
    denied: <ABS>/docs/frozen.md`. On an operator machine that second copy is a
    home directory — the exact shape `_personal_path_display` refuses to print
    three lines above the defect. All THREE fatal paths of the module are
    driven here, including the term rule terms-file one, because the leak is a
    CLASS (`% exc`), not the one site that was reported.
    """

    def assert_no_absolute_path(self, proc) -> None:
        blob = proc.stdout + proc.stderr
        self.assertNotIn(str(self.root), blob,
                         "the fatal output carries the absolute scan root")
        self.assertNotIn(str(self.root.parent), blob,
                         "the fatal output carries an absolute parent path")

    def test_unreadable_in_scope_file_names_the_file_relative(self) -> None:
        target = self.commit("docs/frozen.md", "clean\n")
        target.chmod(0o000)
        try:
            self.assert_mode_000_is_unreadable(target)
            fatal = self.cli()
            self.assertEqual(fatal.returncode, 2, fatal.stdout + fatal.stderr)
            self.assertIn("docs/frozen.md", fatal.stderr)
            self.assertIn("FATAL", fatal.stderr)
            self.assert_no_absolute_path(fatal)
        finally:
            target.chmod(0o600)

    def test_unreadable_allowlist_does_not_print_its_absolute_path(self) -> None:
        self.commit("docs/keep.md", "clean\n")
        self.allowlist.write_text(
            self.row("docs/keep.md", "kept 2026"), encoding="utf-8")
        self.allowlist.chmod(0o000)
        try:
            self.assert_mode_000_is_unreadable(self.allowlist)
            fatal = self.cli()
            self.assertEqual(fatal.returncode, 2, fatal.stdout + fatal.stderr)
            self.assertIn("allowlist.txt", fatal.stderr)
            self.assert_no_absolute_path(fatal)
        finally:
            self.allowlist.chmod(0o600)

    def test_unreadable_terms_file_does_not_print_its_absolute_path(self) -> None:
        """The TERM rule fatal, pre-existing, cured by the same helper."""
        terms = self.commit(cc._PRIVATE_TERMS_RELPATH, "zzsyntheticterm\n")
        terms.chmod(0o000)
        try:
            self.assert_mode_000_is_unreadable(terms)
            fatal = self.cli()
            self.assertEqual(fatal.returncode, 2, fatal.stdout + fatal.stderr)
            self.assertIn(cc._PRIVATE_TERMS_RELPATH, fatal.stderr)
            self.assert_no_absolute_path(fatal)
        finally:
            terms.chmod(0o600)

    def test_an_undecodable_allowlist_is_rc_2_not_a_traceback(self) -> None:
        """UnicodeDecodeError is not an OSError — it escaped the fail-closed."""
        self.commit("docs/keep.md", "clean\n")
        self.allowlist.write_bytes(
            self.row("docs/keep.md", "fine 2026").encode("utf-8") + b"\xff\n")
        fatal = self.cli()
        blob = fatal.stdout + fatal.stderr
        self.assertEqual(fatal.returncode, 2, blob)
        self.assertIn("FATAL", fatal.stderr)
        self.assertNotIn("Traceback", blob)
        self.assert_no_absolute_path(fatal)

    def test_an_undecodable_terms_file_is_rc_2_not_a_traceback(self) -> None:
        """The same class on the TERM rule's own input."""
        self.commit_bytes(cc._PRIVATE_TERMS_RELPATH, b"zzterm\n\xff\n")
        fatal = self.cli()
        blob = fatal.stdout + fatal.stderr
        self.assertEqual(fatal.returncode, 2, blob)
        self.assertNotIn("Traceback", blob)
        self.assert_no_absolute_path(fatal)

    def test_the_traceback_does_not_leak_it_either(self) -> None:
        """The other exit: an uncaught exception prints its chained context."""
        target = self.commit("docs/frozen.md", "clean\n")
        target.chmod(0o000)
        try:
            self.assert_mode_000_is_unreadable(target)
            with self.assertRaises(cc.PersonalPathUnreadable) as caught:
                cc.scan_personal_paths(self.root)
            rendered = "".join(traceback.format_exception(
                type(caught.exception), caught.exception,
                caught.exception.__traceback__))
            self.assertIn("docs/frozen.md", rendered)
            self.assertNotIn(str(self.root), rendered)
            self.assertNotIn("During handling of the above exception",
                             rendered)
        finally:
            target.chmod(0o600)

    def test_reason_helper_keeps_the_reason_and_drops_the_path(self) -> None:
        leaky = OSError(13, "Permission denied", "/Users/zzfake/x/docs/a.md")
        self.assertEqual(cc._oserror_reason(leaky), "Permission denied")
        self.assertNotIn("/Users/", cc._oserror_reason(leaky))
        # str() is what the pre-cure code interpolated — this is the control
        # that the helper is not decorative.
        self.assertIn("/Users/", str(leaky))
        # No errno, no strerror: the class name, never the args.
        self.assertEqual(
            cc._oserror_reason(OSError("/Users/zzfake/x boom")), "OSError")


class TestUnknownArgumentTolerance(_Base):
    """(10) An unknown argument must not become a new rc-2 failure mode.

    The module this rule joined took NO arguments and ignored argv entirely,
    and the delivered `check-contamination.sh` execs it with "$@" — so a strict
    parser would redden an adopter CI over an argument that used to do nothing.
    The tolerance is kept; the silence is not, because a swallowed
    `--fail-on-stalee` reads exactly like a check that ran and passed.
    """

    def test_an_unknown_flag_does_not_change_the_exit_code(self) -> None:
        self.commit("docs/keep.md", "clean\n")
        clean = self.cli()
        tolerant = self.cli("--not-a-real-flag")
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
        self.assertEqual(tolerant.returncode, clean.returncode,
                         tolerant.stdout + tolerant.stderr)

    def test_the_ignored_token_is_named_on_stderr(self) -> None:
        self.commit("docs/keep.md", "clean\n")
        tolerant = self.cli("--not-a-real-flag")
        self.assertIn("--not-a-real-flag", tolerant.stderr)
        self.assertIn("ignoring unrecognised argument", tolerant.stderr)

    def test_a_finding_still_fails_when_an_unknown_flag_is_present(self) -> None:
        self.commit("docs/leak.md", "at " + _MAC + "\n")
        red = self.cli("--not-a-real-flag")
        self.assertEqual(red.returncode, 1, red.stdout + red.stderr)

    def test_a_known_flag_is_still_parsed_not_swallowed(self) -> None:
        """Anti-vacuity: tolerance must not degrade into ignoring EVERY flag."""
        self.commit("docs/keep.md", "clean\n")
        self.allowlist.write_text(
            "docs/gone.md | sha256:%s | CONTROL: matches no file\n" % _SHA,
            encoding="utf-8")
        self.assertEqual(self.cli().returncode, 0)
        strict = self.cli("--fail-on-stale")
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)


class TestNoSpellingTurnsTheGateOff(_Base):
    """(14) An ABBREVIATION selected the rows-only mode and returned 0.

    argparse accepts a unique PREFIX of a long option by default, so
    `--emit-personal-path-row` — one character short, and a plausible
    typo — put the gate into a mode that prints rows and never judges.
    A security matcher must not have a spelling that switches it off.
    """

    def test_an_abbreviation_of_the_mode_flag_is_refused(self) -> None:
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        for tok in ("--emit-personal-path-ro",
                    "--emit-personal-path-row",
                    "--fail-on-stal",
                    "--personal-path-allowlis"):
            with self.subTest(tok=tok):
                refused = self.cli(tok)
                self.assertEqual(refused.returncode, 2,
                                 refused.stdout + refused.stderr)
                self.assertIn("PREFIX of a real option", refused.stderr)

    def test_the_full_flag_still_works(self) -> None:
        """Anti-vacuity: the refusal must not eat the real option."""
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        emitted = self.cli("--emit-personal-path-rows")
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        self.assertIn("docs/leak.md | sha256:", emitted.stdout)

    def test_an_unrelated_unknown_flag_is_still_tolerated(self) -> None:
        """The base module ignored argv; the wrapper execs it with "$@"."""
        self.commit("docs/keep.md", "clean\n")
        tolerant = self.cli("--not-a-real-flag")
        self.assertEqual(tolerant.returncode, 0, tolerant.stderr)
        self.assertIn("ignoring unrecognised argument", tolerant.stderr)

    def test_the_known_options_come_from_the_parser_not_a_list(self) -> None:
        """A flag added later must not leave this check behind."""
        parser = argparse.ArgumentParser(allow_abbrev=False)
        parser.add_argument("--brand-new-option", action="store_true")
        self.assertTrue(cc._personal_path_option_near_miss(
            parser, "--brand-new-opt"))
        self.assertFalse(cc._personal_path_option_near_miss(
            parser, "--brand-new-option"))
        for neutral in ("--", "-", "-x", "--totally-different"):
            with self.subTest(tok=neutral):
                self.assertFalse(cc._personal_path_option_near_miss(
                    parser, neutral))

    def test_argparse_own_error_does_not_quote_the_token(self) -> None:
        """Found by probe, not by brief: the fourth site of one shape.

        `ArgumentParser.error()` prints `ignored explicit argument
        '<value>'`, and a value on this CLI can BE a home path. The
        gate refuses to quote the leak it FINDS; it must not quote one
        while refusing to run.
        """
        self.commit("docs/keep.md", "clean\n")
        refused = self.cli("--emit-personal-path-rows=" + _MAC)
        blob = refused.stdout + refused.stderr
        self.assertEqual(refused.returncode, 2, blob)
        self.assertNotIn(_OWNER, blob)
        self.assertIn("redacted", blob)


class TestS344LandRailCures(_Base):
    """Every defect the S344 rail found on v4, and the shape it belongs to.

    Both lanes REJECTED round 1. Each test below reproduces one finding
    and pins its cure; each was RED on the reviewed tree before the cure
    landed, verified by probe.

    Named for the ROUND rather than numbered: `TestRailRound1Cures` and
    `TestRailRound2Cures` already exist below, for the rounds on the
    PREVIOUS version, and a duplicate class name silently SHADOWS one of
    them — every test in it dropped, with a green run to show for it.
    """

    def test_a_symlink_replacing_a_scope_root_is_scanned(self) -> None:
        """[P1] The SCOPE TEST was itself a way out of the scope.

        Git stores no directories, so a tracked entry named exactly
        `docs` can only be a symlink — and `startswith("docs/")`
        answered False for it.
        """
        for rel in ("docs", ".claude/plans", ".claude"):
            with self.subTest(rel=rel):
                self.assertTrue(cc.in_personal_path_scope(rel))
        for rel in ("d", "doc", ".claud", "README.md"):
            with self.subTest(rel=rel):
                self.assertFalse(cc.in_personal_path_scope(rel))
        os.symlink(_MAC, self.root / "docs")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        self.assertEqual(self.rels(), ["docs"])
        self.assertEqual(self.cli().returncode, 1)

    def test_link_status_comes_from_the_git_index(self) -> None:
        """[P1] `core.symlinks=false` materialises a link as a FILE.

        The filesystem is not an authority on what git stores. Both
        shapes of the same mode-120000 entry must classify as a link,
        or a link's target is scanned as file content on one checkout and
        is refused on another from the same commit.
        """
        self.commit("docs/keep.md", "clean\n")
        os.symlink(_MAC, self.root / "docs" / "link.md")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        modes = cc._personal_path_index_modes(self.root)
        self.assertEqual(modes.get("docs/link.md"),
                         cc._PERSONAL_PATH_LINK_MODE)
        blob = cc._personal_path_blob(
            self.root / "docs/link.md", "docs/link.md", index_is_link=True)
        self.assertTrue(blob.is_symlink)
        self.assertEqual(blob.raw, _MAC.encode("utf-8"))
        # the core.symlinks=false shape: same index mode, regular file
        (self.root / "docs" / "link.md").unlink()
        (self.root / "docs" / "link.md").write_bytes(_MAC.encode("utf-8"))
        blob = cc._personal_path_blob(
            self.root / "docs/link.md", "docs/link.md", index_is_link=True)
        self.assertTrue(blob.is_symlink,
                        "the filesystem overruled the index")
        self.assertEqual(blob.raw, _MAC.encode("utf-8"))

    def test_a_link_swapped_in_after_the_index_is_not_followed(self) -> None:
        """[P1] `is_symlink()` then `read_bytes()` are two moments."""
        self.commit("docs/f.md", "clean\n")
        (self.root / "docs" / "f.md").unlink()
        os.symlink(_MAC, self.root / "docs" / "f.md")
        blob = cc._personal_path_blob(
            self.root / "docs/f.md", "docs/f.md", index_is_link=False)
        self.assertTrue(blob.is_symlink,
                        "O_NOFOLLOW did not catch the swap")
        self.assertEqual(blob.raw, _MAC.encode("utf-8"))

    def test_the_owner_segment_is_not_truncated_to_a_placeholder(self):
        """[P1] `[\\w.\\-]+` stopped at the first character it did not know.

        A segment read HALFWAY is worse than one not read: `dev+<real>`
        truncated to `dev`, which the placeholder list forgives.
        """
        for glue in ("+", "$", "~", "!", "%", "@", "^", "&", "="):
            with self.subTest(glue=glue):
                self.assertTrue(cc.line_is_personal_path_hit(
                    "/Users/dev" + glue + _OWNER + "/work"))
        # the documented placeholder style is still clean, and it is
        # clean because `<` DELIMITS — not because a list forgives it
        for clean in ("/Users/<user>/x", "/Users/<name>/repo",
                      "/Users/devuser)", "/Users/runner/work",
                      "/home/ubuntu; ls", "/Users/me]"):
            with self.subTest(clean=clean):
                self.assertFalse(cc.line_is_personal_path_hit(clean))

    def test_the_trackedness_probe_takes_a_path_not_a_pathspec(self):
        """[P1] `--` ends OPTION parsing; it does not make it literal."""
        tracked = self.root / "allow-good.txt"
        tracked.write_text("# tracked\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        self.assertTrue(cc._personal_path_allowlist_is_tracked(
            self.root, tracked))
        for magic in ("allow-*.txt", "*", ":(glob)allow-*.txt"):
            with self.subTest(magic=magic):
                self.assertFalse(cc._personal_path_allowlist_is_tracked(
                    self.root, self.root / magic))

    def test_an_empty_walk_over_a_nonempty_index_is_fatal(self) -> None:
        """[P1] The retry checked the RETURN CODE and not the output.

        A transient first failure followed by a working retry returned
        a CLEAN verdict over zero files — the false green the assertion
        exists to stop.
        """
        self.commit("docs/keep.md", "clean\n")
        with self.assertRaises(cc.PersonalPathUnreadable) as caught:
            cc._personal_path_assert_enumerable(self.root)
        self.assertIn("yielded NOTHING", str(caught.exception))

    def test_a_genuinely_empty_repository_is_still_clean(self) -> None:
        """Anti-vacuity: the fatal is about ENUMERATION, not emptiness.

        A repository of its own, because the fixture root has a TRACKED
        allowlist by construction — asserting on it would assert the
        opposite of what this test is named for.
        """
        empty = Path(tempfile.mkdtemp(prefix="ceo-empty-repo-")).resolve()
        try:
            subprocess.run(["git", "init", "-q"], cwd=empty, check=True,
                           capture_output=True)
            cc._personal_path_assert_enumerable(empty)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_a_malformed_private_term_does_not_print_the_path(self):
        """[P1] A private term is a RAW REGEX, and re.error quotes it."""
        terms = self.root / cc._PRIVATE_TERMS_RELPATH
        terms.parent.mkdir(parents=True, exist_ok=True)
        terms.write_text("(?P<%s>)\n" % _MAC, encoding="utf-8")
        subprocess.run(["git", "add", "-A", "-f"], cwd=self.root,
                       check=True, capture_output=True)
        fatal = self.cli()
        blob = fatal.stdout + fatal.stderr
        self.assertEqual(fatal.returncode, 2, blob)
        self.assertNotIn(_OWNER, blob)
        self.assertNotIn("Traceback", blob)
        self.assertIn("invalid regular expression", fatal.stderr)

    def test_emit_mode_reports_a_mixed_name_and_body_hit(self) -> None:
        """[P2] A waiver was consulted BEFORE the unwaivable name.

        A mixed hit HAS a digest, so "no digest" was never the full test
        for a name hit either.
        """
        rel = "docs/-Users-" + _OWNER + "-x/wave-approved.md"
        hit = cc.PersonalPathHit(rel=rel, lines=(0, 3), sha256="a" * 64)
        scan = cc.PersonalPathScan(hits=[hit])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            rc = cc._emit_personal_path_rows(scan, {})
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "",
                         "a row that the parser refuses is not a row")
        self.assertIn("rename them", err.getvalue())
        verdict = cc.personal_path_verdict(scan, {})
        self.assertEqual([h.rel for h in verdict.unwaived], [rel])

    def test_the_printed_term_allowlist_matches_the_code(self) -> None:
        """[P2] The report claimed a NARROWER exemption than the glob."""
        self.commit(".claude/scripts/x.md",
                    "term " + _TERM_MARKER + "\n")
        out = self.cli().stdout
        self.assertIn("Contamination found", out)
        self.assertNotIn("PLAN-*.md (all plan files)", out)
        self.assertIn(".claude/plans/*", out)


class TestS344LandRailRound2Cures(_Base):
    """Round 2 REJECTED the cures of round 1. These are those findings.

    Two are the same SHAPE as a round-1 cure, one regex or one exception
    type over — which this repository reads as "change the architecture
    of the cure", never "extend the list".
    """

    def test_both_matchers_share_one_delimiter_set(self) -> None:
        """[P1] Round 1 widened the DIRECT matcher and left the SLUG one.

        Same defect, one regex over: `-Users-dev+<real>-repo` still read
        as the placeholder `dev`. Two matchers of the same thing that CAN
        be edited apart WILL be, so they are built from one constant and
        this test asserts the constant is load-bearing in both.
        """
        for glue in ("+", "$", "~", "!", "%", "@", "^", "&", "="):
            with self.subTest(glue=glue):
                self.assertTrue(cc.line_is_personal_path_hit(
                    "-Users-dev" + glue + _OWNER + "-repo"))
                self.assertTrue(cc.line_is_personal_path_hit(
                    "/Users/dev" + glue + _OWNER + "/repo"))
        for clean in ("-Users-runner-work", "-Users-<user>-x",
                      "-Users-devuser-repo"):
            with self.subTest(clean=clean):
                self.assertFalse(cc.line_is_personal_path_hit(clean))
        self.assertIn(cc._PERSONAL_PATH_SEG_DELIMS,
                      cc._PERSONAL_PATH_HOME_RE.pattern)
        self.assertIn(cc._PERSONAL_PATH_SEG_DELIMS,
                      cc._PERSONAL_PATH_SLUG_RE.pattern)

    def test_any_failure_of_the_term_scan_is_a_sanitised_rc_2(self):
        """[P1] Enumerating exception types is not a boundary.

        `re.error` was named after round 1; round 2 answered with
        RecursionError (2000 open parens in a private term), which
        escaped as an rc-1 traceback carrying the checkout path.
        """
        terms = self.root / cc._PRIVATE_TERMS_RELPATH
        terms.parent.mkdir(parents=True, exist_ok=True)
        for body in ("(" * 2000, "(?P<%s>)" % _MAC, "[" + _MAC):
            with self.subTest(body=body[:24]):
                terms.write_text(body + "\n", encoding="utf-8")
                subprocess.run(["git", "add", "-A", "-f"], cwd=self.root,
                               check=True, capture_output=True)
                fatal = self.cli()
                blob = fatal.stdout + fatal.stderr
                self.assertEqual(fatal.returncode, 2, blob)
                self.assertNotIn("Traceback", blob)
                self.assertNotIn(_OWNER, blob)
                # either message is correct: the KNOWN input failures
                # still name the terms file, and the catch-all names
                # only that the scan did not finish. What must hold for
                # every one of them is rc 2, no traceback, no owner.
                self.assertTrue(
                    "term scan did not complete" in fatal.stderr
                    or cc._PRIVATE_TERMS_RELPATH in fatal.stderr,
                    fatal.stderr)

    def test_an_untracked_symlink_allowlist_waives_nothing(self) -> None:
        """[P1] `resolve()` follows the link, so git saw the TARGET."""
        real = self.root / "tracked-allow.txt"
        real.write_text("# tracked\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        self.assertTrue(
            cc._personal_path_allowlist_is_tracked(self.root, real))
        link = self.root / "loose-allow.txt"
        link.symlink_to(real)
        self.assertFalse(
            cc._personal_path_allowlist_is_tracked(self.root, link),
            "an untracked symlink borrowed a tracked file trust")

    def test_a_partial_walk_is_refused_like_an_empty_one(self) -> None:
        """[P1] Zero was only the loudest case of an unverified walk."""
        self.commit("docs/a.md", "clean\n")
        self.commit("docs/b.md", "clean\n")
        only_one = [self.root / "docs" / "a.md"]
        with mock.patch.object(cc, "FileWalker") as walker:
            walker.return_value.repo_root = self.root
            walker.return_value.iter_files.return_value = iter(only_one)
            with self.assertRaises(cc.PersonalPathUnreadable) as caught:
                cc.scan_personal_paths(self.root)
        self.assertIn("of the", str(caught.exception))

    def test_an_in_repo_allowlist_path_is_masked_when_printed(self):
        """[P2] Only the OUTSIDE-repo branch went through the boundary."""
        rel = "docs/" + _SLUG + "/allow.txt"
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# not tracked\n", encoding="utf-8")
        shown = cc._personal_path_display(target, self.root)
        self.assertNotIn(_OWNER, shown)

    def test_emit_mode_and_fail_on_stale_are_incompatible(self) -> None:
        """[P2] One suppresses the verdict, the other tightens it."""
        self.commit("docs/keep.md", "clean\n")
        refused = self.cli("--emit-personal-path-rows", "--fail-on-stale")
        self.assertEqual(refused.returncode, 2,
                         refused.stdout + refused.stderr)
        self.assertIn("contradict", refused.stderr)

    def test_emit_mode_does_not_hide_a_malformed_allowlist(self) -> None:
        """[P2] rc 0 told an operator the rc 1 they just saw went away."""
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        self.allowlist.write_text("this-is-not-a-row\n", encoding="utf-8")
        self.assertEqual(self.cli().returncode, 1)
        emitted = self.cli("--emit-personal-path-rows")
        self.assertEqual(emitted.returncode, 1,
                         emitted.stdout + emitted.stderr)
        self.assertIn("malformed allowlist row", emitted.stderr)
        self.assertIn("docs/leak.md | sha256:", emitted.stdout)

    def test_a_root_that_cannot_be_resolved_is_rc_2(self) -> None:
        """[P2] `resolve()` raised BEFORE any guarded path."""
        loop = self.root / "loop"
        loop.symlink_to(loop)
        proc = subprocess.run(
            [sys.executable, str(Path(cc.__file__).resolve()),
             "--root", str(loop / "x")],
            capture_output=True, text=True, check=False)
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 2, blob)
        self.assertNotIn("Traceback", blob)


class TestAWaiverIsPinnedToContent(_Base):
    """(13) A row waives the BYTES a human read, not the path forever."""

    REASON = "CEREMONY: frozen transcript"

    def test_an_edit_lapses_the_waiver_and_a_restore_returns_it(self) -> None:
        rel = "docs/frozen.md"
        original = "see " + _MAC + "\n"
        self.commit(rel, original)
        self.allowlist.write_text(self.row(rel, self.REASON),
                                  encoding="utf-8")
        self.assertEqual(self.cli().returncode, 0)
        # ONE byte, and the allowlist is not touched at all.
        self.commit(rel, original + "\n")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout)
        self.assertIn("sha256 no longer matches", red.stdout)
        self.assertIn(rel, red.stdout)
        self.commit(rel, original)
        self.assertEqual(self.cli().returncode, 0,
                         "the same bytes must be waived again")

    def test_a_row_pinning_another_file_bytes_waives_nothing(self) -> None:
        """A digest copied from the wrong file is a mismatch, not a pass."""
        self.commit("docs/a.md", "see " + _MAC + "\n")
        self.commit("docs/b.md", "also " + _MAC + "\n")
        other = self.row("docs/b.md", self.REASON).split(" | ")[1]
        self.allowlist.write_text(
            "docs/a.md | %s | %s\n" % (other, self.REASON),
            encoding="utf-8")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout)
        self.assertIn("sha256 no longer matches", red.stdout)

    def test_the_emitted_row_carries_the_digest_of_the_scanned_bytes(self):
        """A generator that re-read the file could pin content nobody scanned."""
        rel = "docs/leak.md"
        body = "see " + _MAC + "\n"
        self.commit(rel, body)
        emitted = self.cli("--emit-personal-path-rows")
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        self.assertIn(
            hashlib.sha256(body.encode("utf-8")).hexdigest(),
            emitted.stdout)

    def test_a_re_emitted_row_cures_a_lapsed_waiver(self) -> None:
        """The ordinary workflow: edit, re-emit, re-approve."""
        rel = "docs/frozen.md"
        self.commit(rel, "see " + _MAC + "\n")
        self.allowlist.write_text(self.row(rel, self.REASON),
                                  encoding="utf-8")
        self.commit(rel, "see " + _MAC + "\nand again\n")
        self.assertEqual(self.cli().returncode, 1)
        emitted = self.cli("--emit-personal-path-rows")
        self.assertIn(rel + " | sha256:", emitted.stdout)
        self.allowlist.write_text(
            emitted.stdout.replace(cc._PERSONAL_PATH_UNREASONED,
                                   self.REASON),
            encoding="utf-8")
        self.assertEqual(self.cli().returncode, 0)


class TestTheGateDoesNotEchoWhatItWasHanded(_Base):
    """(11) Four print sites the pair-rail measured leaking, one predicate.

    Each of these was a string the gate did not compose: a human-written
    waiver reason echoed on a GREEN run, an allowlist path outside the repo
    rendered by the display fallback, an ignored CLI token. The rule that
    refuses to quote a finding now runs over the gate's own output.
    """

    def test_a_reason_naming_a_home_directory_is_refused_at_parse_time(
            self) -> None:
        self.commit("docs/leak.md", "at " + _MAC + "\n")
        self.allowlist.write_text(
            self.row("docs/leak.md", "archived from " + _MAC),
            encoding="utf-8")
        red = self.cli()
        blob = red.stdout + red.stderr
        # The row waives nothing (it is MALFORMED) and nothing echoes it.
        self.assertEqual(red.returncode, 1, blob)
        self.assertIn("MALFORMED", red.stdout)
        self.assertNotIn(_OWNER, blob)

    def test_the_sanitiser_replaces_only_what_names_a_person(self) -> None:
        self.assertEqual(cc._personal_path_safe("frozen rail log"),
                         "frozen rail log")
        self.assertEqual(cc._personal_path_safe("/Users/devuser/x"),
                         "/Users/devuser/x")
        self.assertNotIn(_OWNER, cc._personal_path_safe("from " + _MAC))
        self.assertIn("redacted", cc._personal_path_safe("from " + _MAC))

    def test_a_waived_reason_is_sanitised_before_the_green_report(self) -> None:
        """Belt AND braces: the printer is safe even if a row got through."""
        allow = {"docs/a.md": cc.PersonalPathRow(
            sha256="c" * 64, reason="archived from " + _MAC, rowno=1)}
        self.assertNotIn(
            _OWNER,
            "".join(cc._personal_path_honoured_rows(
                [("docs/a.md", "archived from " + _MAC)], allow)[0]),
        )

    def test_emitted_rows_do_not_print_a_contaminated_PATH(self) -> None:
        """A file whose own NAME carries the slug gets NO row at all.

        v3 emitted a redacted row for it. That row was unusable by
        construction — the parser refuses a row naming a home directory —
        so handing it to an operator whose next step is to paste it was
        the wrong help. The cure for the mixed name/body hit (pair-rail
        round 1, P2) made this consistent: a hit carrying line 0 is
        COUNTED on stderr as needing a rename, never printed as a row.
        Either way the owner segment never reaches the output.
        """
        rel = "docs/" + _SLUG + "/notes.md"
        self.commit(rel, "at " + _MAC + "\n")
        emitted = self.cli("--emit-personal-path-rows")
        self.assertEqual(emitted.returncode, 0,
                         emitted.stdout + emitted.stderr)
        self.assertEqual(emitted.stdout, "",
                         "an unusable row is not a row")
        self.assertIn("rename them", emitted.stderr)
        self.assertNotIn(_OWNER, emitted.stdout + emitted.stderr)
        # and the file is still a FINDING in the normal run
        self.assertEqual(self.cli().returncode, 1)

    def test_an_ignored_token_that_is_a_home_path_is_redacted(self) -> None:
        self.commit("docs/keep.md", "clean\n")
        tolerant = self.cli(_MAC)
        blob = tolerant.stdout + tolerant.stderr
        self.assertEqual(tolerant.returncode, 0, blob)
        self.assertIn("redacted", tolerant.stderr)
        self.assertNotIn(_OWNER, blob)


class TestTrackedSymlink(_Base):
    """(12) A symlink is stored by git as its TARGET STRING — scan that."""

    def _commit_symlink(self, rel: str, target: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "fixture", "-q"],
                       cwd=self.root, check=True, capture_output=True)
        return path

    def test_a_symlink_target_with_an_undecodable_byte_is_reported(self) -> None:
        """`readlink()` returns SURROGATES, not U+FFFD — land round 1, P1.

        Pre-cure the payload reached the matcher as a surrogateescaped
        string, whose marker the second reading did not recognise, so
        `/Users/dev<0xFF>zzfake/` read as the placeholder owner `dev` and
        the link walked through clean.
        """
        import os as _os
        target = _os.fsdecode(b"/Users/dev\xffzzfake/work/photo.png")
        self._commit_symlink("docs/photo.png", target)
        self.assertEqual(self.rels(), ["docs/photo.png"])
        self.assertEqual(self.hits()[0].lines, (1,))

    def test_a_dangling_symlink_to_a_home_path_is_reported(self) -> None:
        """`is_file()` is False for it — pre-cure it was silently skipped."""
        self._commit_symlink("docs/link.md", _MAC + "/nowhere.md")
        self.assertEqual(self.rels(), ["docs/link.md"])
        self.assertEqual(self.hits()[0].lines, (1,))

    def test_a_resolvable_symlink_is_judged_by_its_target_string(self) -> None:
        """Pre-cure the TARGET's bytes were scanned instead of the payload."""
        outside = self.root.parent / ("zz-outside-%s.md" % self.root.name)
        outside.write_text("nothing to see\n", encoding="utf-8")
        try:
            self._commit_symlink("docs/link.md", str(outside))
            # The link text is not a home path, so no hit — and, crucially,
            # the OUTSIDE file was not read in its place either.
            self.assertEqual(self.rels(), [])
            outside.write_text("at " + _MAC + "\n", encoding="utf-8")
            self.assertEqual(
                self.rels(), [],
                "the target's CONTENT is not this file's committed payload")
        finally:
            outside.unlink()

    def test_a_symlink_with_a_binary_NAME_is_still_scanned(self) -> None:
        """The suffix skip is about CONTENT; a link payload is always text."""
        self._commit_symlink("docs/photo.png", _MAC + "/photo.png")
        self.assertEqual(self.rels(), ["docs/photo.png"])

    def test_a_regular_binary_file_is_scanned_like_a_link(self) -> None:
        """One rule for every input: v3 read the link and skipped the file."""
        self.commit_bytes("docs/real.png", ("x " + _MAC + "\n").encode())
        self.assertEqual(self.rels(), ["docs/real.png"])
        self.assertEqual(self.hits()[0].lines, (1,))

    def test_an_unsearchable_ancestor_is_fatal_not_a_traceback(self) -> None:
        """`is_symlink()` itself raises there — it must not escape the try."""
        self.commit("docs/locked/frozen.md", "clean\n")
        locked = self.root / "docs" / "locked"
        locked.chmod(0o000)
        try:
            self.assert_mode_000_is_unreadable(locked / "frozen.md")
            fatal = self.cli()
            blob = fatal.stdout + fatal.stderr
            self.assertEqual(fatal.returncode, 2, blob)
            self.assertNotIn("Traceback", blob)
            self.assertNotIn(str(self.root), blob)
        finally:
            locked.chmod(0o700)

    def test_the_symlink_payload_is_what_the_cli_reports(self) -> None:
        self._commit_symlink("docs/link.md", _MAC + "/x.md")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout + red.stderr)
        self.assertIn("docs/link.md:1", red.stdout)
        self.assertNotIn(_OWNER, red.stdout + red.stderr)


class TestTheAllowlistMustBeTrackedByGit(_Base):
    """(12) The waiver's whole claim is REVIEWABILITY — so git is asked.

    Cross-vendor lane, S344, P2: every document said the allowlist is
    TRACKED, and no code asked git. Reproduced on the framework's own tree —
    `git rm --cached` the allowlist and it is still on disk, byte for byte,
    unknown to git, and the gate still waived 242 files and still granted
    the signer. `touch` was a signer grant.

    Each method carries its own POSITIVE leg on the same tree, so a green
    here cannot come from the fixture never waiving anything.
    """

    def _add_allowlist(self) -> None:
        subprocess.run(["git", "add", "--", self.allowlist.name],
                       cwd=self.root, check=True, capture_output=True)

    def _untrack(self) -> None:
        """On disk, byte-identical, gone from the INDEX. The control."""
        subprocess.run(
            ["git", "rm", "--cached", "-q", "--", self.allowlist.name],
            cwd=self.root, check=True, capture_output=True)
        self.assertTrue(self.allowlist.is_file(),
                        "the control must leave the bytes on disk")

    def test_an_untracked_allowlist_waives_no_row(self) -> None:
        self.commit("docs/leak.md", "at " + _MAC + "\n")
        self.allowlist.write_text(
            self.row("docs/leak.md", "frozen 2026"), encoding="utf-8")
        self._add_allowlist()
        green = self.cli()
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)

        self._untrack()
        red = self.cli()
        blob = red.stdout + red.stderr
        self.assertEqual(red.returncode, 1, blob)
        self.assertIn("not tracked by git", red.stdout)
        self.assertIn("docs/leak.md:1", red.stdout)
        self.assertNotIn(_OWNER, blob)

    def test_the_parser_still_reads_a_file_handed_to_it_directly(self) -> None:
        """The gate decides trust; the PARSER stays pure and testable.

        The trackedness question needs a repo root, and pushing it into
        `load_personal_path_allowlist` would have made every unit test of
        the grammar a test of git instead.
        """
        self.allowlist.write_text(
            "docs/x.md | sha256:%s | frozen 2026\n" % _SHA,
            encoding="utf-8")
        subprocess.run(
            ["git", "add", "--", self.allowlist.name],
            cwd=self.root, check=True, capture_output=True)
        self._untrack()
        entries, malformed = cc.load_personal_path_allowlist(
            self.allowlist)
        self.assertEqual((list(entries), malformed),
                         (["docs/x.md"], []))

    def test_the_helper_is_fail_closed_on_every_unconfirmable_answer(
            self) -> None:
        self.commit("docs/keep.md", "clean\n")
        self.assertTrue(
            cc._personal_path_allowlist_is_tracked(self.root, self.allowlist),
            "anti-vacuity: a tracked allowlist answers True")

        self.assertFalse(cc._personal_path_allowlist_is_tracked(
            self.root, self.root / "never-added.txt"))

        outside = Path(tempfile.mkdtemp(prefix="ceo-outside-")).resolve()
        try:
            stray = outside / "allowlist.txt"
            stray.write_text("signer-fingerprint: %s\n" % _FPR,
                             encoding="utf-8")
            self.assertFalse(
                cc._personal_path_allowlist_is_tracked(self.root, stray),
                "outside the repository git is not its reviewer")
        finally:
            shutil.rmtree(outside, ignore_errors=True)

        for boom in (OSError("no git"),
                     subprocess.TimeoutExpired(cmd="git", timeout=30)):
            with self.subTest(failure=type(boom).__name__):
                with mock.patch.object(cc.subprocess, "run",
                                       side_effect=boom):
                    self.assertFalse(
                        cc._personal_path_allowlist_is_tracked(
                            self.root, self.allowlist))

    def test_an_out_of_repo_allowlist_waives_nothing_and_names_no_home(
            self) -> None:
        """The override must be tracked too — and the display stays masked."""
        self.commit("docs/leak.md", "at " + _MAC + "\n")
        outside = Path(tempfile.mkdtemp(prefix="ceo-outside-")).resolve()
        try:
            stray = outside / "allowlist.txt"
            stray.write_text(
                self.row("docs/leak.md", "frozen 2026"), encoding="utf-8")
            red = subprocess.run(
                [sys.executable, str(Path(cc.__file__).resolve()),
                 "--root", str(self.root),
                 "--personal-path-allowlist", str(stray)],
                capture_output=True, text=True, check=False)
            blob = red.stdout + red.stderr
            self.assertEqual(red.returncode, 1, blob)
            self.assertIn("outside the repository", red.stdout)
            self.assertNotIn(str(outside), blob)
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_the_notice_does_not_pollute_the_emitted_rows(self) -> None:
        """`--emit-personal-path-rows` exists to be PASTED, so it stays clean."""
        self.commit("docs/leak.md", "at " + _MAC + "\n")
        self._untrack()
        emitted = self.cli("--emit-personal-path-rows")
        self.assertEqual(emitted.returncode, 0,
                         emitted.stdout + emitted.stderr)
        for line in emitted.stdout.splitlines():
            if line.strip():
                self.assertIn("|", line, "stdout must be pasteable rows only")
        self.assertIn("not tracked by git", emitted.stderr)


class TestShippedAllowlist(TestEnvContext):
    """The framework's own tracked allowlist must be well-formed and honest.

    Read-only over this checkout — but still `TestEnvContext`, because the
    env-hygiene gate is about the CLASS, not about what a given method
    happens to touch today.
    """

    def setUp(self) -> None:
        super().setUp()
        self.path = _REPO_ROOT / cc._PERSONAL_PATH_ALLOWLIST_REL
        if not self.path.is_file():
            self.skipTest("no shipped allowlist in this checkout")

    def test_the_shipped_allowlist_is_tracked_in_this_checkout(
            self) -> None:
        """The claim the whole waiver rests on, asserted on OUR tree.

        Not a coupling to the corpus: it asserts a PROPERTY of the
        shipped file, not a count of anything, so no unrelated
        commit can move it. A tarball with no git skips.
        """
        probe = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(_REPO_ROOT), capture_output=True, check=False)
        if probe.returncode != 0:
            self.skipTest("not a git checkout")
        self.assertTrue(cc._personal_path_allowlist_is_tracked(
            _REPO_ROOT, self.path))

    def test_every_row_parses(self) -> None:
        entries, malformed = cc.load_personal_path_allowlist(
            self.path)
        self.assertEqual(malformed, [], "malformed rows in the shipped file")
        self.assertTrue(entries, "an empty allowlist waives nothing")

    def test_the_allowlist_carries_no_personal_path_in_cleartext(self) -> None:
        """The waiver file must not become a second copy of the leak."""
        for lineno, row in enumerate(
                self.path.read_text(encoding="utf-8").splitlines(), 1):
            with self.subTest(row=lineno):
                self.assertFalse(
                    cc.line_is_personal_path_hit(row),
                    "row %d names a home directory in cleartext" % lineno,
                )



def _armour(raw: bytes) -> str:
    """An armoured detached signature carrying exactly ``raw``."""
    body = base64.b64encode(raw).decode("ascii")
    return ("-----BEGIN PGP SIGNATURE-----\n\n%s\n=zzZZ\n"
            "-----END PGP SIGNATURE-----\n"
            % "\n".join(body[i:i + 64] for i in range(0, len(body), 64)))


class TestPathIsASubject(_Base):
    """(10) G3 — the repo-relative PATH is scanned, and cannot be waived."""

    REL = "docs/-Users-" + _OWNER + "-project/note.md"

    def test_a_slug_in_a_directory_name_is_a_hit_at_line_zero(self) -> None:
        self.commit(self.REL, "a body with nothing in it\n")
        hits = self.hits()
        self.assertEqual([h.rel for h in hits], [self.REL])
        self.assertEqual(hits[0].lines, (cc._PERSONAL_PATH_NAME_LINE,))
        self.assertEqual(self.cli().returncode, 1)

    def test_a_clean_name_beside_it_is_not_a_hit(self) -> None:
        """Anti-vacuity: the same body under a name that says nothing."""
        self.commit("docs/plain/note.md", "a body with nothing in it\n")
        self.assertEqual(self.rels(), [])

    def test_a_row_naming_that_path_is_refused_so_it_cannot_be_waived(self):
        """The row is WELL-FORMED and still refused -- for its PATH.

        It used to be written two-field, which v4 rejects as malformed
        before the path is ever looked at: the assertion held for the
        wrong reason and never reached the predicate it names (pair-rail
        round 3, P3). A correctly pinned row makes the refusal mean what
        the test says it means.
        """
        self.allowlist.write_text(
            "%s | sha256:%s | frozen 2026\n" % (self.REL, "a" * 64),
            encoding="utf-8")
        entries, malformed = cc.load_personal_path_allowlist(
            self.allowlist)
        self.assertEqual((entries, malformed), ({}, [1]),
                         "a hit in the NAME is a rename, not a waiver")
        # Anti-vacuity: the SAME grammar with a clean path parses.
        self.allowlist.write_text(
            "docs/plain.md | sha256:%s | frozen 2026\n" % ("a" * 64),
            encoding="utf-8")
        entries, malformed = cc.load_personal_path_allowlist(
            self.allowlist)
        self.assertEqual((list(entries), malformed),
                         (["docs/plain.md"], []))

    def test_the_report_masks_the_owner_and_keeps_the_rest(self) -> None:
        self.commit(self.REL, "clean\n")
        out = self.cli().stdout
        self.assertNotIn(_OWNER, out, "the report must not quote the owner")
        self.assertIn("<redacted-owner>", out)
        self.assertIn("docs/-Users-<redacted-owner>-project/note.md:0", out)
        self.assertIn(":0", out)

    def test_body_and_name_hits_are_both_reported(self) -> None:
        self.commit(self.REL, "line one\nsee " + _LINUX + "\n")
        hits = self.hits()
        self.assertEqual(hits[0].lines,
                         (cc._PERSONAL_PATH_NAME_LINE, 2))


class TestUndecodableTrackedPath(_Base):
    """(11) G2 — a path the scan cannot ADDRESS is fatal, and names nothing.

    `FileWalker` decodes `git ls-files -z` with `errors="replace"`, so a
    tracked name that is not valid UTF-8 arrives as a path that does not
    exist: `is_file()` answered False and the file was skipped IN SILENCE.
    This filesystem refuses to create such a name (EILSEQ), so the walker —
    the collaborator whose OUTPUT is the defect — is the thing stubbed. What
    is driven is the scan, unmodified.
    """

    class _Walker(object):
        def __init__(self, paths, repo_root):
            self.repo_root = repo_root
            self._paths = paths

        def iter_files(self):
            return iter(self._paths)

    def _scan_with(self, names):
        paths = [self.root / n for n in names]
        walker = self._Walker(paths, self.root)
        with self.stubbed_walk(paths, walker=walker):
            return cc.scan_personal_paths(self.root)

    def test_an_undecodable_tracked_path_is_fatal(self) -> None:
        with self.assertRaises(cc.PersonalPathUnreadable) as ctx:
            self._scan_with(["docs/a\ufffdb.md"])
        message = str(ctx.exception)
        self.assertIn("not valid UTF-8", message)
        self.assertNotIn("\ufffd", message,
                         "the fatal must not echo the mangled name")
        self.assertNotIn(str(self.root), message)

    def test_a_decodable_path_is_scanned_not_refused(self) -> None:
        """Anti-vacuity: the same stub, a name the scan can address."""
        self.commit("docs/ok.md", "see " + _MAC + "\n")
        scan = self._scan_with(["docs/ok.md"])
        self.assertEqual([h.rel for h in scan.hits], ["docs/ok.md"])

    def test_the_surrogate_form_is_fatal_too(self) -> None:
        """`errors="surrogateescape"` leaves U+DC80-U+DCFF, not U+FFFD."""
        with self.assertRaises(cc.PersonalPathUnreadable):
            self._scan_with(["docs/a\udcffb.md"])


class TestRemediationTellsTheTruth(_Base):
    """(12) G5 — the printed cure stops claiming an exemption that is gone."""

    def test_the_remediation_claims_no_exemption_by_name(self):
        """The printed cure is part of the contract, so it is asserted.

        v3 printed "Exempt by rule, never by row: OWNER-*.sh ceremony
        scripts" — a sentence that was TRUE of the code and was the
        bypass. Text and behaviour move together or the next reader
        trusts the wrong one.
        """
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        out = self.cli().stdout
        self.assertIn("NOTHING is exempt by NAME, by SUFFIX or by "
                      "SIGNATURE", out)
        self.assertNotIn("OWNER-*.sh ceremony", out,
                         "the remediation still promises the v3 bypass")
        self.assertNotIn("*.asc signatures", out,
                         "the blanket exemption was removed in v2 round 1")
        self.assertIn("sha256:<64 hex>", out,
                      "the cure must name the grammar it now requires")
        self.assertNotIn("signer-fingerprint", out,
                         "the cure still offers the deleted directive")
        self.assertNotIn("approved.md / *-approved.md) passing", out,
                         "the cure still promises the deleted waiver")

    def test_the_shipped_allowlist_header_matches_the_rule(self) -> None:
        header = (_SCRIPTS_DIR / cc._PERSONAL_PATH_ALLOWLIST_REL.rsplit(
            "/", 1)[-1]).read_text(encoding="utf-8")
        self.assertNotIn("their `*.asc` signatures, and", header)
        self.assertIn("UPGRADING FROM v4.0", header,
                      "the header must tell an adopter what to delete")

    def test_the_followup_plan_the_module_names_exists(self) -> None:
        """A comment that names a plan file is a claim about the tree."""
        module = Path(cc.__file__).resolve()
        text = module.read_text(encoding="utf-8")
        self.assertIn("PLAN-186-FOLLOWUP-sentinel-gpg-verification", text)
        plan = (_REPO_ROOT / ".claude" / "plans"
                / "PLAN-186-FOLLOWUP-sentinel-gpg-verification.md")
        self.assertTrue(plan.is_file(), "%s is missing" % plan.name)



class TestRailRound1Cures(_Base):
    """(13) The six findings of the v3 pair-rail, one leg each.

    Every one of them was REPRODUCED on the applied shadow before the cure
    was written, and each test below fails on the pre-cure module for the
    reason the round named -- a class that only asserts the cured behaviour
    cannot say which defect it is guarding.
    """

    CONTAM_DIR = "docs/-Users-" + _OWNER + "-project"

    # --- P1: a waiver waives the BODY, never the NAME ---------------------
    # --- P2: the owner segment is matched WHOLE ---------------------------
    def test_a_non_ascii_owner_segment_is_a_hit(self) -> None:
        self.assertTrue(cc.line_is_personal_path_hit("/Users/\u00e9va/work"))
        self.assertTrue(cc.line_is_personal_path_hit("/home/\u7528\u6237/w"))

    def test_a_placeholder_prefix_no_longer_forgives_a_real_owner(self) -> None:
        """`/Users/dev<accent>/` used to TRUNCATE to the placeholder `dev`."""
        self.assertTrue(cc.line_is_personal_path_hit("/Users/dev\u00e9/work"))

    def test_the_placeholders_themselves_stay_clean(self) -> None:
        """Anti-vacuity: widening the class must not flag the documented style."""
        for line in ("/Users/dev/work", "/home/runner/work", "/Users/.../x"):
            self.assertFalse(cc.line_is_personal_path_hit(line), line)

    # --- P2: an enumeration that failed is not a verdict -------------------
    def test_a_tree_git_cannot_enumerate_is_fatal(self) -> None:
        outside = Path(tempfile.mkdtemp(prefix="ceo-not-a-repo-")).resolve()
        try:
            with self.assertRaises(cc.PersonalPathUnreadable) as ctx:
                cc.scan_personal_paths(outside)
        finally:
            shutil.rmtree(outside, ignore_errors=True)
        self.assertNotIn(str(outside), str(ctx.exception),
                         "the fatal path must not print an absolute path")

    def test_an_empty_repository_is_still_clean(self) -> None:
        """Anti-vacuity: the fatal is about ENUMERATION, not emptiness.

        The fixture stages an allowlist, so `self.root` is NOT empty and
        this ran over a one-file index while claiming to cover the empty
        one (pair-rail round 3, P3). A genuinely empty repository is
        built here on purpose.
        """
        self.assertEqual(cc.scan_personal_paths(self.root).hits,
                         [])
        empty = Path(tempfile.mkdtemp(prefix="ceo-pp-empty-")).resolve()
        try:
            subprocess.run(["git", "init", "-q"], cwd=empty, check=True,
                           capture_output=True)
            self.assertEqual(
                cc._personal_path_index_modes(empty), {},
                "the control is only a control while the index is empty")
            self.assertEqual(
                cc.scan_personal_paths(empty).hits, [])
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    # --- P2: no speed claim -----------------------------------------------
    def test_the_module_makes_no_speed_claim(self) -> None:
        """CLAUDE.md/AGENTS.md: this framework makes no speed claim."""
        text = Path(cc.__file__).resolve().read_text(encoding="utf-8")
        for banned in ("2.7s", "0.4s", "order of magnitude"):
            self.assertNotIn(banned, text, banned)


class TestRailRound2Cures(_Base):
    """(14) The three cured findings of the v3 pair-rail round 2.

    Round 2 returned four P2 and no P1. The fourth (the allowlist not being
    delivered by `scripts/install.sh`) is this pack DECLARED residual: that
    file is canonical and travels in a signed ceremony, so it has no test
    here -- it has a line in DESIGN and in EVIDENCE section K.
    """

    MARKER = "\ufffd"

    # --- the term report masks a PATH hit too ------------------------------
    def test_the_term_report_masks_an_owner_in_the_path(self) -> None:
        """RULE 1 printed the path VERBATIM, so RULE 2 masking came too late."""
        rel = ".claude/plans/-Users-" + _OWNER + "-x/LEDGER.md"
        self.commit(rel, "a body with " + _TERM_MARKER + "\n")
        out = self.cli().stdout
        self.assertNotIn(_OWNER, out, "the owner must not reach the log")
        self.assertIn("<redacted-owner>", out)

    def test_a_clean_violation_path_is_still_printed_verbatim(self) -> None:
        """Anti-vacuity: the mask is a no-op for every other file."""
        rel = ".claude/plans/PLAN-999/LEDGER.md"
        self.commit(rel, "a body with " + _TERM_MARKER + "\n")
        self.assertIn("  - " + rel, self.cli().stdout)

    # --- an undecodable path is fatal only inside the declared scope -------
    def test_an_undecodable_path_in_scope_is_fatal(self) -> None:
        with self.stubbed_walk(
                [self.root / ("docs/note" + self.MARKER + ".md")]):
            with self.assertRaises(cc.PersonalPathUnreadable):
                cc.scan_personal_paths(self.root)

    def test_an_undecodable_path_out_of_scope_is_not_this_rule_business(self):
        """A legal byte-name under `assets/` must not turn the gate rc 2."""
        with self.stubbed_walk(
                [self.root / ("assets/img" + self.MARKER + ".png")]):
            self.assertEqual(
                cc.scan_personal_paths(self.root).hits, [])

    def test_an_undecodable_scope_prefix_is_fatal(self) -> None:
        """Undecidable counts as in scope: the prefix itself is unreadable."""
        with self.stubbed_walk(
                [self.root / ("do" + self.MARKER + "s/note.md")]):
            with self.assertRaises(cc.PersonalPathUnreadable):
                cc.scan_personal_paths(self.root)

    def test_the_decision_follows_the_scope_tuple_not_a_typed_constant(self):
        """Every prefix in the tuple is honoured, alive-prefix by alive-prefix."""
        for prefix in cc._PERSONAL_PATH_SCOPE:
            half = prefix[:max(1, len(prefix) // 2)]
            self.assertTrue(
                cc._personal_path_undecodable_in_scope(
                    half + self.MARKER + "x/note.md"), prefix)
        self.assertFalse(
            cc._personal_path_undecodable_in_scope("zz/note" + self.MARKER))

    # --- the follow-up plan does not carry a stale census ------------------
    def test_the_followup_does_not_hardcode_a_stale_sentinel_count(self):
        plan = (_REPO_ROOT / ".claude" / "plans"
                / "PLAN-186-FOLLOWUP-sentinel-gpg-verification.md")
        text = plan.read_text(encoding="utf-8")
        self.assertNotIn("74 sentinels", text)
        self.assertIn("DERIVADO DO DISCO", text)


class TestRailRound3Cures(_Base):
    """One guard per pair-rail round-3 finding, each reproduced first."""

    def test_a_tracked_symlink_allowlist_is_refused_by_index_mode(self):
        """P1, both lanes: `core.symlinks=false` defeats is_symlink()."""
        body = ("/" + "Users" + "/" + _OWNER + "/repo\n").encode()
        self.commit_bytes("docs/leak.md", body)
        row = "docs/leak.md | sha256:%s | frozen" % (
            hashlib.sha256(body).hexdigest())
        link = self.root / "linked-allow.txt"
        os.symlink(row, link)
        subprocess.run(["git", "add", "--", link.name], cwd=self.root,
                       check=True, capture_output=True)
        # The materialisation `core.symlinks=false` produces: git still
        # records mode 120000, the filesystem holds a REGULAR file.
        link.unlink()
        link.write_text(row, encoding="utf-8")
        self.assertEqual(
            cc._personal_path_index_modes(self.root)["linked-allow.txt"],
            "120000", "the control needs a mode-120000 index entry")
        self.assertFalse(link.is_symlink(),
                         "the control needs a REGULAR file on disk")
        self.assertFalse(
            cc._personal_path_allowlist_is_tracked(self.root, link),
            "a link payload must never be read as an allowlist")
        self.assertEqual(
            cc.report_personal_paths(self.root, link), 1,
            "the leaking file must stay unwaived")

    def test_a_regular_tracked_allowlist_is_still_accepted(self) -> None:
        """Anti-vacuity for the index-mode check."""
        self.assertTrue(cc._personal_path_allowlist_is_tracked(
            self.root, self.allowlist))

    def test_the_ancestor_budget_refuses_when_it_is_exhausted(self) -> None:
        """P1, lane B: falling through a spent budget skipped the link."""
        deep = self.root
        for i in range(cc._PERSONAL_PATH_ANCESTOR_CAP + 2):
            deep = deep / ("d%d" % i)
        deep.mkdir(parents=True)
        far = deep / "allow.txt"
        far.write_text("# nothing\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        self.assertFalse(
            cc._personal_path_allowlist_is_tracked(self.root, far),
            "an unfinished ancestor walk is not a yes")

    def test_completeness_is_identity_not_cardinality(self) -> None:
        """P1, lane B: one path yielded twice satisfied `seen == len`."""
        self.commit("docs/a.md", "clean\n")
        self.commit("docs/b.md", "clean\n")
        root = self.root

        class _DoubleWalker:
            def __init__(self, repo_root, mode="git"):
                self.repo_root = Path(repo_root)

            def iter_files(self):
                seen = sorted(cc._personal_path_index_modes(root))
                # every tracked path but ONE, and the first twice: the
                # count matches while a file is never read.
                yield self.repo_root / seen[0]
                for rel in seen[:-1]:
                    yield self.repo_root / rel

        with mock.patch.object(cc, "FileWalker", _DoubleWalker):
            with self.assertRaises(cc.PersonalPathUnreadable) as ctx:
                cc.scan_personal_paths(self.root)
        self.assertIn("MISSED", str(ctx.exception))
        self.assertNotIn(str(self.root), str(ctx.exception),
                         "the fatal must name no absolute path")

    def test_an_index_mode_this_rule_cannot_read_is_a_refusal(self) -> None:
        """P1, lane B: a gitlink was skipped silently and still counted."""
        self.commit("docs/keep.md", "clean\n")
        modes = dict(cc._personal_path_index_modes(self.root))
        # the mode is faked on a path the walk DOES yield: a mode
        # on a phantom path would trip the completeness check
        # first and never reach the branch under test.
        modes["docs/keep.md"] = "160000"
        with mock.patch.object(cc, "_personal_path_index_modes",
                               return_value=modes):
            with self.assertRaises(cc.PersonalPathUnreadable) as ctx:
                cc.scan_personal_paths(self.root)
        self.assertIn("160000", str(ctx.exception))

    def test_a_fifo_is_refused_and_does_not_block(self) -> None:
        """Round 3 P2 + round 4 P1: no hang, and no CLEAN scan either.

        `O_NONBLOCK` stopped the hang; returning None then made a
        tracked path replaced by a FIFO a SILENT SKIP that reported
        clean. Both halves are asserted here: the call returns inside
        the deadline, AND it returns by refusing.
        """
        path = self.commit("docs/pipe.md", "clean\n")
        path.unlink()
        os.mkfifo(str(path))
        try:
            done = []

            import threading as _threading

            def _run():
                try:
                    cc.scan_personal_paths(self.root)
                    done.append("returned")
                except cc.PersonalPathUnreadable as exc:
                    done.append(str(exc))

            worker = _threading.Thread(target=_run, daemon=True)
            worker.start()
            worker.join(20)
            self.assertTrue(done, "the scan blocked on the FIFO")
            self.assertIn("not a regular file", done[0])
            self.assertNotIn(str(self.root), done[0])
        finally:
            os.unlink(str(path))

    def test_a_directory_in_place_of_a_tracked_file_is_refused(self):
        """Round 4 P1: the same shape with EISDIR."""
        path = self.commit("docs/dir.md", "clean\n")
        path.unlink()
        path.mkdir()
        with self.assertRaises(cc.PersonalPathUnreadable) as ctx:
            cc.scan_personal_paths(self.root)
        # macOS opens a directory read-only without EISDIR, so the
        # fstat leg names it; Linux raises EISDIR and the errno leg
        # does. Either way it is a REFUSAL, which is the property.
        self.assertRegex(str(ctx.exception),
                         "not a regular file|is a DIRECTORY")

    def test_an_absent_worktree_file_is_still_not_fatal(self) -> None:
        """Anti-vacuity: ABSENCE is declared, and stays declared."""
        path = self.commit("docs/gone.md", "clean\n")
        path.unlink()
        self.assertEqual(
            cc.scan_personal_paths(self.root).hits, [])

    def test_a_diff_deletion_line_is_a_hit(self) -> None:
        """Round 4 P1: `-` before the path made a removed line clean."""
        home = "/" + "Users" + "/" + _OWNER + "/work"
        self.assertTrue(cc.line_is_personal_path_hit("-" + home))
        self.assertTrue(cc.line_is_personal_path_hit("+" + home))
        # the forms the lookbehind still excludes, unchanged
        for prefix in ("~", ".", "a", "1", "_"):
            self.assertFalse(cc.line_is_personal_path_hit(prefix + home),
                             prefix)

    def test_an_empty_path_option_is_a_usage_error(self) -> None:
        """Round 4 P1: truthiness read `--root ""` as NOT GIVEN."""
        for argv in (["--root", ""],
                     ["--personal-path-allowlist", ""],
                     ["--root", "   "]):
            with self.assertRaises(cc.PersonalPathUsage, msg=argv):
                cc._parse_args(argv)
        # anti-vacuity: OMITTING them is still fine
        args = cc._parse_args([])
        self.assertIsNone(args.root)

    def test_the_allowlist_is_read_through_the_nofollow_helper(self):
        """Round 4 P1: a re-open by NAME was a second inode."""
        src = (_SCRIPTS_DIR / "check_contamination.py").read_text(
            encoding="utf-8")
        head = src[src.index("def load_personal_path_allowlist"):]
        body = head[:head.index("def personal_path_verdict")]
        self.assertIn("_personal_path_read_nofollow(path)", body)
        self.assertNotIn("path.read_text(", body)
        self.assertNotIn("if not path.is_file():", body)

    def test_an_in_scope_path_absent_from_the_snapshot_refuses(self):
        """Round 4 P2: a missing mode skipped the whole check."""
        self.commit("docs/keep.md", "clean\n")
        modes = dict(cc._personal_path_index_modes(self.root))
        modes.pop("docs/keep.md")
        with mock.patch.object(cc, "_personal_path_index_modes",
                               return_value=modes):
            with self.assertRaises(cc.PersonalPathUnreadable) as ctx:
                cc.scan_personal_paths(self.root)
        self.assertIn("absent from the index snapshot",
                      str(ctx.exception))

    def test_a_git_failure_in_the_mode_lookup_is_not_a_traceback(self):
        """Round 4 P2: the second git call sat outside every boundary."""
        with mock.patch.object(
                cc, "_personal_path_index_modes",
                side_effect=cc.PersonalPathUnreadable("git failed")):
            self.assertFalse(cc._personal_path_allowlist_is_tracked(
                self.root, self.allowlist))

    def test_an_eol_only_mismatch_is_named_and_still_fails(self) -> None:
        """R3 P2 + R4 P3: the line reports the OBSERVATION, not a cause.

        No EOL filter is configured here, and none needs to be: what
        the code can observe is that the bytes differ only in line
        endings, which is exactly what the message now says.
        """
        lf = ("/" + "Users" + "/" + _OWNER + "/repo\n").encode()
        crlf = lf.replace(b"\n", b"\r\n")
        self.commit_bytes("docs/eol.md", crlf)
        self.allowlist.write_text(
            "signer-fingerprint: %s\ndocs/eol.md | sha256:%s | frozen 2026\n"
            % (_FPR, hashlib.sha256(lf).hexdigest()), encoding="utf-8")
        subprocess.run(["git", "add", "--", self.allowlist.name],
                       cwd=self.root, check=True, capture_output=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cc.report_personal_paths(self.root, self.allowlist)
        out = buf.getvalue()
        self.assertEqual(rc, 1, "an EOL-only mismatch is NOT a waiver")
        self.assertIn("ONLY in line endings", out)
        self.assertIn("not why", out)
        self.assertIn("core.autocrlf", out)

    def test_a_real_edit_is_not_reported_as_an_eol_artifact(self) -> None:
        """Anti-vacuity: the diagnosis must not fire on a true edit."""
        self.commit_bytes(
            "docs/edit.md",
            ("/" + "Users" + "/" + _OWNER + "/repo\n").encode())
        self.allowlist.write_text(
            "signer-fingerprint: %s\ndocs/edit.md | sha256:%s | frozen 2026\n"
            % (_FPR, "b" * 64), encoding="utf-8")
        subprocess.run(["git", "add", "--", self.allowlist.name],
                       cwd=self.root, check=True, capture_output=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cc.report_personal_paths(self.root, self.allowlist)
        self.assertEqual(rc, 1)
        self.assertNotIn("ONLY in line endings", buf.getvalue())

    def test_an_unreadable_root_is_named_not_traced(self) -> None:
        """P2, lane B: the boundary ended before the .git test."""
        with mock.patch.object(
                cc.Path, "exists",
                side_effect=PermissionError(13, "denied")):
            rc = cc.main(["--root", str(self.root)])
        self.assertEqual(rc, 2)

    def test_the_help_does_not_promise_an_unconditional_zero(self) -> None:
        """P3, lane B: emit mode returns 1 over a malformed allowlist."""
        buf = io.StringIO()
        parser_text = ""
        try:
            with contextlib.redirect_stdout(buf):
                cc._parse_args(["--help"])
        except SystemExit:
            parser_text = buf.getvalue()
        self.assertIn("--emit-personal-path-rows", parser_text)
        # the help must name every code this mode can return
        for code in ("exit 0", "1 when", "2 when"):
            self.assertIn(code, parser_text, code)


class TestNoWaiverIsEarnedByAName(_Base):
    """The refuter's F1, as a control: the forgery, and its twin.

    The deleted rule asked four questions of CONTENT, but it asked them
    only of a file whose BASENAME was `approved.md` / `*-approved.md`,
    and every answer was transplantable by anyone who could write a
    file. These tests plant the FULL forgery — a real armoured
    signature body in a tracked sibling `.asc`, and an `Approved-By:`
    line naming the fingerprint the fixture allowlist used to grant —
    and then plant the identical bytes under a name that is not
    sentinel-shaped. Same verdict, both times, is the whole claim.
    """

    BODY = "frozen: " + _MAC + "\n"

    def _plant(self, rel: str, with_sidecar: bool) -> None:
        self.commit(rel, _SENTINEL_BODY + self.BODY)
        if with_sidecar:
            self.commit(rel + ".asc", _ARMOR)

    def test_the_full_forgery_is_still_a_finding(self) -> None:
        rel = ".claude/plans/PLAN-999/wave-forged-approved.md"
        self._plant(rel, with_sidecar=True)
        proc = self.cli()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn(rel, proc.stdout,
                      "a transplanted signature waived the file by NAME")

    def test_the_same_bytes_under_another_name_are_the_same_finding(self):
        """The NAME is not a variable any more.

        Byte-for-byte the same document and the same sidecar, once under
        a sentinel-shaped name and once not. Under v4.0 the first was
        WAIVED and the second was a finding; that difference WAS the
        defect, and this test fails if it ever comes back.
        """
        sentinel = ".claude/plans/PLAN-999/wave-twin-approved.md"
        plain = ".claude/plans/PLAN-999/wave-twin-note.md"
        self._plant(sentinel, with_sidecar=True)
        self._plant(plain, with_sidecar=True)
        out = self.cli().stdout
        self.assertIn(sentinel, out)
        self.assertIn(plain, out)

    def test_a_row_pinned_to_the_content_still_waives_it(self) -> None:
        """Anti-vacuity: the file is waivABLE, just not by its name."""
        rel = ".claude/plans/PLAN-999/wave-row-approved.md"
        self._plant(rel, with_sidecar=True)
        self.allowlist.write_text(
            self.row(rel, "frozen, reviewed") + "\n", encoding="utf-8")
        proc = self.cli()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_no_identifier_of_the_deleted_waiver_survives(self) -> None:
        """A deletion that leaves its plumbing behind is a pause, not a cure."""
        source = Path(cc.__file__).read_text(encoding="utf-8")
        for dead in ("_sentinel_rule_waiver", "_is_detached_signature",
                     "_sentinel_signer_fingerprint", "_PGP_SIG_",
                     "_PERSONAL_PATH_SENTINEL_REASON",
                     "_PERSONAL_PATH_SIGNER_", "rule_waived"):
            self.assertNotIn(dead, source, dead)

    def test_a_leftover_v40_signer_directive_is_malformed(self) -> None:
        """An adopter upgrading is TOLD, not silently ignored."""
        self.commit("docs/plain.md", "clean\n")
        self.allowlist.write_text(
            "signer-fingerprint: %s\n" % _FPR, encoding="utf-8")
        proc = self.cli()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("MALFORMED", proc.stdout)
        self.assertIn("row 1", proc.stdout)


class TestAWaiverIsVisibleByPath(_Base):
    """F1b: a green run says WHAT it forgave, not just how many."""

    def _waive(self, count: int) -> None:
        rows = []
        for i in range(count):
            rel = "docs/waived-%02d.md" % i
            self.commit(rel, "frozen %d: %s\n" % (i, _MAC))
            rows.append(self.row(rel, "frozen artifact"))
        self.allowlist.write_text("\n".join(rows) + "\n", encoding="utf-8")

    def test_the_green_run_names_each_waived_path(self) -> None:
        self._waive(2)
        proc = self.cli()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("honoured allowlist rows (2", proc.stdout)
        self.assertIn("docs/waived-00.md | sha256:", proc.stdout)
        self.assertIn("docs/waived-01.md | sha256:", proc.stdout)

    def test_each_honoured_row_prints_its_own_reason(self) -> None:
        self.commit("docs/a.md", "a: %s\n" % _MAC)
        self.commit("docs/b.md", "b: %s\n" % _MAC)
        self.allowlist.write_text(
            self.row("docs/a.md", "reason A 2026") + "\n"
            + self.row("docs/b.md", "reason B 2026") + "\n",
            encoding="utf-8")
        out = self.cli().stdout
        self.assertIn("docs/a.md | sha256:", out)
        self.assertIn("| reason A 2026", out)
        self.assertIn("docs/b.md | sha256:", out)
        self.assertIn("| reason B 2026", out)
        self.assertLess(out.index("docs/a.md |"), out.index("docs/b.md |"))

    def test_the_honoured_inventory_is_NOT_capped(self) -> None:
        """A cap is a place a waiver hides; that is the r13 M1 decision."""
        waived = [("docs/x-%03d.md" % i, "same reason 2026")
                  for i in range(500)]
        allow = {rel: cc.PersonalPathRow(sha256="a" * 64, reason=reason,
                                         rowno=i + 1)
                 for i, (rel, reason) in enumerate(waived)}
        rows, digest = cc._personal_path_honoured_rows(waived, allow)
        self.assertEqual(len(rows), 500)
        self.assertEqual(len(digest), 64)
        self.assertFalse(hasattr(cc, "_PERSONAL_PATH_WAIVED_PRINT_CAP"))

    def test_a_waived_reason_naming_a_person_is_still_redacted(self) -> None:
        """The choke point survives the new per-row printing."""
        allow = {"docs/x.md": cc.PersonalPathRow(
            sha256="b" * 64, reason="archived from " + _MAC, rowno=1)}
        rows, _ = cc._personal_path_honoured_rows(
            [("docs/x.md", "archived from " + _MAC)], allow)
        self.assertNotIn(_OWNER, rows[0])
        self.assertIn("<redacted: names a home directory>", rows[0])


class TestRailRound10Cures(_Base):
    """Round 10, lane A: the three defects that were REPRODUCED on disk.

    Each test re-creates the mechanism the lane described and asserts the
    cured code refuses it BY NAME; each has a companion asserting that the
    legitimate case next door still passes, because a refusal that also
    refuses the normal case is not a cure.
    """

    def _commit_symlink(self, rel: str, target: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "fixture", "-q"],
                       cwd=self.root, check=True, capture_output=True)
        return path

    # ---- A-P1-1 -------------------------------------------------------
    def test_an_indexed_link_replaced_by_a_directory_is_fatal(self) -> None:
        """rc 1 -> rc 0 was the pre-cure measurement; now it is rc 2.

        git keeps mode 120000 for the entry; the working tree holds a
        directory. Pre-cure the reader answered None, which the scan reads
        as ABSENT, and the leaking payload was never matched.
        """
        link = self._commit_symlink("docs/link.md", _MAC + "/secret.md")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout + red.stderr)
        self.assertIn("docs/link.md", red.stdout)
        link.unlink()
        link.mkdir()
        fatal = self.cli()
        blob = fatal.stdout + fatal.stderr
        self.assertEqual(fatal.returncode, 2, blob)
        self.assertNotIn("Traceback", blob)
        self.assertNotIn(str(self.root), blob)
        self.assertIn("holds no blob", blob)

    def test_an_absent_indexed_link_is_still_not_an_error(self) -> None:
        """The companion: absence is NOT unreadable input, and stays None."""
        link = self._commit_symlink("docs/link.md", _MAC + "/secret.md")
        link.unlink()
        green = self.cli()
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)

    # ---- A-P2-1 -------------------------------------------------------
    def test_an_allowlist_that_is_a_directory_is_a_named_fatal(self) -> None:
        """Pre-cure: rc 1 and a traceback naming the checkout."""
        self.commit("docs/ok.md", "clean\n")
        self.allowlist.unlink()
        self.allowlist.mkdir()
        try:
            fatal = self.cli()
            blob = fatal.stdout + fatal.stderr
            self.assertEqual(fatal.returncode, 2, blob)
            self.assertNotIn("Traceback", blob)
            self.assertNotIn(str(self.root), blob)
            self.assertIn("cannot read", blob)
        finally:
            self.allowlist.rmdir()
            self.allowlist.write_text("", encoding="utf-8")

    def test_a_readable_allowlist_is_still_loaded(self) -> None:
        """The companion: the same tree with a FILE there is green."""
        self.commit("docs/ok.md", "clean\n")
        green = self.cli()
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)

    # ---- A-P2-2 -------------------------------------------------------
    def test_a_comment_naming_a_home_directory_is_malformed(self) -> None:
        """The one place a home path was examined by nothing."""
        self.commit("docs/ok.md", "clean\n")
        self.allowlist.write_text(
            "# archived from " + _MAC + "/notes\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        red = self.cli()
        blob = red.stdout + red.stderr
        self.assertEqual(red.returncode, 1, blob)
        self.assertIn("MALFORMED allowlist rows", blob)
        self.assertIn("row 1", blob)
        self.assertNotIn(_OWNER, blob)

    def test_an_ordinary_comment_is_not_malformed(self) -> None:
        """The companion: placeholders and prose stay legal.

        The shipped allowlist carries 76 comment lines; this is the shape
        of them, and it must not become a rejection.
        """
        self.commit("docs/ok.md", "clean\n")
        self.allowlist.write_text(
            "# Waivers are pinned to sha256 of the CONTENT.\n"
            "# A placeholder such as /Users/<user>/x says the same thing.\n",
            encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        green = self.cli()
        blob = green.stdout + green.stderr
        self.assertEqual(green.returncode, 0, blob)
        self.assertNotIn("MALFORMED", blob)


class TestRailRound10Refutations(_Base):
    """Round 10, lane A: the two claims that were RECORDED, NOT EXECUTED.

    Both were executed here, and both are refuted. The evidence is pinned as
    a test rather than argued in a record, because a refutation nobody can
    re-run is an opinion.
    """

    def test_a_doubled_separator_is_a_HIT_on_purpose(self) -> None:
        """A-P2-3 claimed a false positive on `https://host//home/jdoe`.

        `//home/jdoe` is a real path to the same file POSIX resolves
        `/home/jdoe` to, so refusing to match it would create an EVASION
        that costs one keystroke -- a far worse defect than matching a URL
        that happens to embed a home path. This rule grants no exemption for
        CONTEXT (no URL shape, no comment, no fenced block), by design.
        """
        self.assertTrue(
            cc.line_is_personal_path_hit("see https://host//home/jdoe/x"))
        self.assertTrue(cc.line_is_personal_path_hit("//home/jdoe/x"))
        self.assertTrue(cc.line_is_personal_path_hit("/home/jdoe/x"))

    def test_a_fullwidth_placeholder_owner_names_no_person(self) -> None:
        """A-P2-4 claimed a false negative folding an owner into `dev`.

        What folds into `dev` IS the placeholder `dev`: NFKC turns the
        full-width owner segment into the generic word this rule ships as a
        non-person. A full-width segment naming an actual person still hits,
        raw and normalised alike -- which is the property the claim doubted.
        """
        person = "/Users/ｊｄｏｅ/work"
        self.assertTrue(cc.line_is_personal_path_hit(person))
        self.assertTrue(cc.line_is_personal_path_hit(
            unicodedata.normalize("NFKC", person)))
        placeholder = "/Users/ｄｅｖ/work"
        self.assertFalse(cc.line_is_personal_path_hit(
            unicodedata.normalize("NFKC", placeholder)))


class TestTheEntryPointIsLast(TestEnvContext):
    """A-P3: `unittest.main()` ran 157 of 166 tests, and said OK.

    The nine it skipped were the two classes proving the v4.1 deletion: they
    were defined AFTER the entry point, so direct execution never saw them
    and reported success. CI is pytest-only, so the loss was invisible there.
    This test reads its own module's SOURCE, because the defect is a property
    of the file's layout that no import can observe.
    """

    def test_no_class_is_defined_after_unittest_main(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8").splitlines()
        entry = [i for i, line in enumerate(source)
                 if line.startswith('if __name__ == "__main__":')]
        self.assertEqual(len(entry), 1, "one entry point, exactly")
        after = [line for line in source[entry[0]:]
                 if line.startswith("class ") or line.startswith("def ")]
        self.assertEqual(
            after, [],
            "a class defined after the entry point does not run under "
            "`python3 <module>`, and reports OK anyway")


class TestRailRound11Cures(_Base):
    """Round 11, lane A: the two findings this pack cured.

    Both are about the pack's OWN new lines -- one is a defect the round-10
    cure introduced, which is the reason a cure gets its own review round.
    """

    def _commit_symlink(self, rel: str, target: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "fixture", "-q"],
                       cwd=self.root, check=True, capture_output=True)
        return path

    def test_an_indexed_link_under_a_locked_ancestor_is_fatal(self) -> None:
        """No `lexists`: an entry that cannot be STATTED is not ABSENT.

        On this Python `is_symlink()` raises here, so the v4.2 shape also
        reached a fatal. The cure is that the verdict no longer depends on
        which errors pathlib swallows: the errno classification is explicit
        and lives in one reader.
        """
        self._commit_symlink("docs/locked/link.md", _MAC + "/secret.md")
        locked = self.root / "docs" / "locked"
        locked.chmod(0o000)
        try:
            self.assert_mode_000_is_unreadable(locked / "link.md")
            fatal = self.cli()
            blob = fatal.stdout + fatal.stderr
            self.assertEqual(fatal.returncode, 2, blob)
            self.assertNotIn("Traceback", blob)
            self.assertNotIn(str(self.root), blob)
        finally:
            locked.chmod(0o700)

    def test_the_link_branch_asks_the_filesystem_once(self) -> None:
        """The regression guard for the shape, not only for the outcome."""
        source = Path(cc.__file__).read_text(encoding="utf-8")
        start = source.index("        if index_is_link:")
        end = source.index("        return _personal_path_read_nofollow(path)",
                           start)
        branch = "\n".join(
            line for line in source[start:end].splitlines()
            if not line.strip().startswith("#"))
        for banned in ("is_symlink()", "is_file()", "lexists", "read_bytes()"):
            self.assertNotIn(
                banned, branch,
                "the indexed-link branch classifies by errno, in one open")

    def test_a_path_the_row_grammar_cannot_express_is_not_emitted(self) -> None:
        """A row the parser refuses is not something to paste."""
        self.commit("docs/frozen log.md", "at " + _MAC + "\n")
        emitted = self.cli("--emit-personal-path-rows")
        self.assertEqual(emitted.returncode, 0,
                         emitted.stdout + emitted.stderr)
        self.assertEqual(emitted.stdout.strip(), "")
        self.assertIn("cannot offer as a row", emitted.stderr)
        # and the reason it matters: the row it USED to print does not parse
        row = "docs/frozen log.md | sha256:%s | reason" % ("a" * 64)
        self.assertIsNone(cc._PERSONAL_PATH_ROW_RE.match(row))

    def test_an_ordinary_path_is_still_emitted(self) -> None:
        """The companion: the emitter still emits what the parser accepts."""
        self.commit("docs/frozen.md", "at " + _MAC + "\n")
        emitted = self.cli("--emit-personal-path-rows")
        self.assertEqual(emitted.returncode, 0,
                         emitted.stdout + emitted.stderr)
        self.assertTrue(emitted.stdout.startswith("docs/frozen.md | sha256:"),
                        emitted.stdout)
        row = emitted.stdout.strip()
        self.assertIsNotNone(cc._PERSONAL_PATH_ROW_RE.match(row))


class TestRailRound12Cures(_Base):
    """Round 12, the text lane: one bypass in three places, and one leak."""

    def test_a_fullwidth_owner_in_a_comment_is_refused(self) -> None:
        """The round-10 cure asked only the FOLDED reading and let it in."""
        self.commit("docs/ok.md", "clean\n")
        self.allowlist.write_text(
            "# archived from /Users/\uff44\uff45\uff56/private\n",
            encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        red = self.cli()
        blob = red.stdout + red.stderr
        self.assertEqual(red.returncode, 1, blob)
        self.assertIn("MALFORMED allowlist rows", blob)
        self.assertIn("row 1", blob)

    def test_a_fullwidth_owner_is_redacted_not_echoed(self) -> None:
        """The choke point asked the same one-sided question."""
        value = "/Users/\uff44\uff45\uff56/private"
        self.assertEqual(cc._personal_path_safe(value),
                         "<redacted: names a home directory>")
        self.assertTrue(cc._personal_path_hit_either(value))
        # and the placeholder it folds INTO is still not a person
        self.assertFalse(cc._personal_path_hit_either("/Users/dev/private"))

    def test_a_reason_naming_a_private_term_is_malformed(self) -> None:
        """The leak v4.1 opened, closed where the reasons are READ."""
        leak = self.commit("docs/frozen.md", "at " + _MAC + "\n")
        digest = hashlib.sha256(leak.read_bytes()).hexdigest()
        (self.root / "scripts").mkdir(parents=True, exist_ok=True)
        (self.root / "scripts" / "contamination-terms.txt").write_text(
            "zzsecretcorp\n", encoding="utf-8")
        self.allowlist.write_text(
            "docs/frozen.md | sha256:%s | archived from the zzsecretcorp "
            "migration\n" % digest, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        red = self.cli()
        blob = red.stdout + red.stderr
        self.assertEqual(red.returncode, 1, blob)
        self.assertIn("MALFORMED allowlist rows", blob)
        self.assertIn("row 1", blob)
        self.assertNotIn("zzsecretcorp", blob)

    def test_a_clean_reason_still_waives(self) -> None:
        """The companion: the row that says nothing private still forgives."""
        leak = self.commit("docs/frozen.md", "at " + _MAC + "\n")
        digest = hashlib.sha256(leak.read_bytes()).hexdigest()
        (self.root / "scripts").mkdir(parents=True, exist_ok=True)
        (self.root / "scripts" / "contamination-terms.txt").write_text(
            "zzsecretcorp\n", encoding="utf-8")
        self.allowlist.write_text(
            "docs/frozen.md | sha256:%s | frozen evidence\n" % digest,
            encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        green = self.cli()
        blob = green.stdout + green.stderr
        self.assertEqual(green.returncode, 0, blob)
        self.assertIn("frozen evidence", blob)


class TestRailRound12MechanismCure(_Base):
    """Round 12, lane A: a workflow command forged by a tracked filename."""

    def test_a_newline_in_a_reported_path_is_escaped(self) -> None:
        """`::warning::` at the start of a line is a GitHub Actions command."""
        forged = "docs/ok\n::warning::forged.md"
        self.assertNotIn("\n", cc._personal_path_safe(forged))
        self.assertIn("\\x0a", cc._personal_path_safe(forged))

    def test_an_escape_sequence_in_a_reason_is_escaped(self) -> None:
        """ESC rewrites the rendered inventory this pack added."""
        reason = "frozen \x1b[2Kevidence"
        safe = cc._personal_path_safe(reason)
        self.assertNotIn("\x1b", safe)
        self.assertIn("\\x1b", safe)

    def test_ordinary_text_is_returned_unchanged(self) -> None:
        """The companion: escaping costs a green run nothing."""
        for value in ("docs/frozen.md", "archived evidence, 2026-01",
                      "docs/naïve/über.md"):
            self.assertEqual(cc._personal_path_safe(value), value)

    def test_the_shipped_allowlist_carries_no_control_characters(self) -> None:
        """The measurement the cure was chosen on, kept as a test."""
        shipped = (Path(cc.__file__).resolve().parent
                   / "contamination-personal-path-allowlist.txt")
        text = shipped.read_text(encoding="utf-8")
        controls = [line for line in text.splitlines()
                    if not cc._personal_path_renders_as_itself(line)]
        self.assertEqual(controls, [])


class TestRailRound13Cure(_Base):
    """Round 13: the escape has to be INJECTIVE, not merely safe."""

    def test_a_newline_and_its_literal_spelling_differ(self) -> None:
        """Two different files must not render as one line."""
        real = cc._personal_path_safe("docs/x\ny.md")
        literal = cc._personal_path_safe("docs/x" + chr(92) + "x0ay.md")
        self.assertNotEqual(real, literal)
        self.assertEqual(real, "docs/x" + chr(92) + "x0ay.md")
        self.assertEqual(literal, "docs/x" + chr(92) * 2 + "x0ay.md")

    def test_the_escape_is_reversible(self) -> None:
        """Every rendering has exactly one source string."""
        seen = {}
        for value in ("docs/a.md", "docs/a\nb.md",
                      "docs/a" + chr(92) + "x0ab.md",
                      "docs/a" + chr(92) + "b.md",
                      "docs/a\x1bb.md", "docs/a" + chr(92) * 2 + "b.md"):
            rendered = cc._personal_path_safe(value)
            self.assertNotIn(rendered, seen,
                             "%r and %r render alike"
                             % (value, seen.get(rendered)))
            seen[rendered] = value

    def test_a_path_with_no_backslash_is_unchanged(self) -> None:
        """The companion: the shipped tree pays nothing for this."""
        for value in ("docs/frozen.md", "archived evidence, 2026-01"):
            self.assertEqual(cc._personal_path_safe(value), value)

    def test_the_shipped_allowlist_has_no_backslash_either(self) -> None:
        """The measurement the second cure was chosen on."""
        shipped = (Path(cc.__file__).resolve().parent
                   / "contamination-personal-path-allowlist.txt")
        text = shipped.read_text(encoding="utf-8")
        self.assertNotIn(chr(92), text)


class TestRailRound14Cures(_Base):
    """Round 14: the fold was still one-sided where it decides GREEN."""

    def test_the_scan_folds_first_and_that_is_a_measured_choice(self) -> None:
        """Round 14 asked for raw-OR-folded HERE too. It was MEASURED first.

        The bypass it names (a full-width owner folding into the
        placeholder `dev`) and this repository own anonymising convention
        (an ellipsis owner folding into `/Users/.../x`) are the SAME
        mechanism. Asking the raw reading in the SCAN closes the first and
        opens the second: measured on this tree, 10 findings in 3 files of
        the repository own plan prose. So the scan still folds first, the
        residual is DECLARED, and this test pins BOTH halves of the trade
        instead of leaving it to a sentence.
        """
        self.commit("docs/note.md",
                    "archived from /Users/…/ceo-orchestration\n")
        self.assertEqual(self.rels(), [],
                         "the anonymised form must stay clean")
        self.commit("docs/wide.md",
                    "archived from /Users/ｄｅｖ/private\n")
        self.assertEqual(self.rels(), [],
                         "and the residual is that this one is clean too")

    def test_a_fullwidth_PERSON_is_still_reported(self) -> None:
        """The half that is NOT a residual: folding a person changes nothing."""
        self.commit("docs/person.md",
                    "archived from /Users/ｊｄｏｅ/x\n")
        self.assertEqual(self.rels(), ["docs/person.md"])

    def test_an_ascii_placeholder_is_still_not_a_person(self) -> None:
        """The companion: the placeholder list still works."""
        self.commit("docs/ok.md", "see /Users/dev/private\n")
        self.assertEqual(self.rels(), [])

    def test_a_fullwidth_private_term_in_a_reason_is_malformed(self) -> None:
        """The reason check asked only the raw spelling."""
        leak = self.commit("docs/frozen.md", "at " + _MAC + "\n")
        digest = hashlib.sha256(leak.read_bytes()).hexdigest()
        (self.root / "scripts").mkdir(parents=True, exist_ok=True)
        (self.root / "scripts" / "contamination-terms.txt").write_text(
            "zzsecretcorp\n", encoding="utf-8")
        wide = "".join(chr(0xFF00 + ord(ch) - 0x20) for ch in "zzsecretcorp")
        self.allowlist.write_text(
            "docs/frozen.md | sha256:%s | archived from the %s migration\n"
            % (digest, wide), encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        red = self.cli()
        blob = red.stdout + red.stderr
        self.assertEqual(red.returncode, 1, blob)
        self.assertIn("MALFORMED allowlist rows", blob)

    def test_a_special_inode_fatal_names_the_subject(self) -> None:
        """The operator cannot repair an input the fatal does not name."""
        path = self.commit("docs/frozen.md", "clean\n")
        path.unlink()
        path.mkdir()
        try:
            fatal = self.cli()
            blob = fatal.stdout + fatal.stderr
            self.assertEqual(fatal.returncode, 2, blob)
            self.assertIn("docs/frozen.md", blob)
            self.assertNotIn("Traceback", blob)
        finally:
            path.rmdir()


class TestRailRound13MechanismCure(_Base):
    """A waiver hidden inside a line a reviewer reads as a comment."""

    def _digest(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_a_row_after_a_bare_CR_waives_nothing(self) -> None:
        """git counts one line; `splitlines()` counted two."""
        leak = self.commit("docs/leak.md", "at " + _MAC + "\n")
        row = "# reviewed\rdocs/leak.md | sha256:%s | concealed\n" % (
            self._digest(leak))
        self.allowlist.write_text(row, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        red = self.cli()
        blob = red.stdout + red.stderr
        # rc 2, not 1: since round 20 an interior CR refuses the WHOLE
        # allowlist rather than making one row malformed. Either way the
        # concealed row waives nothing, which is what this test is about.
        self.assertEqual(red.returncode, 2, blob)
        self.assertIn("carriage return INSIDE row 1", blob)

    def test_the_same_row_on_its_own_LF_line_still_waives(self) -> None:
        """The companion: an honest row is unaffected."""
        leak = self.commit("docs/leak.md", "at " + _MAC + "\n")
        row = "# reviewed\ndocs/leak.md | sha256:%s | frozen 2026\n" % (
            self._digest(leak))
        self.allowlist.write_text(row, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        green = self.cli()
        blob = green.stdout + green.stderr
        self.assertEqual(green.returncode, 0, blob)
        self.assertIn("frozen", blob)

    def test_a_CRLF_allowlist_still_parses(self) -> None:
        """The other companion: `strip()` handles the trailing CR."""
        leak = self.commit("docs/leak.md", "at " + _MAC + "\n")
        row = "docs/leak.md | sha256:%s | frozen 2026\r\n" % self._digest(leak)
        self.allowlist.write_text(row, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        green = self.cli()
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)

    def test_a_row_split_by_U2028_is_malformed(self) -> None:
        """Every separator `splitlines()` knows, and git does not."""
        self.commit("docs/leak.md", "at " + _MAC + "\n")
        self.allowlist.write_text(
            "docs/leak.md | sha256:\u2028deadbeef | x\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        red = self.cli()
        blob = red.stdout + red.stderr
        self.assertEqual(red.returncode, 1, blob)
        self.assertIn("MALFORMED allowlist rows", blob)



class CaseVariantHomeRootTest(_Base):
    """The root token decides by DIRECTORY, not by spelling (round 16, P2).

    `_Base`, not `unittest.TestCase`: the env-hygiene gate of this
    repository refuses a bare `TestCase` in a test module, and it is
    right to -- a matcher test that reads the ambient `$HOME` is a test
    of the machine it runs on.
    """

    def test_every_case_spelling_of_the_root_hits(self):
        for line in ("/Users/" + _OWNER + "/x", "/users/" + _OWNER + "/x",
                     "/USERS/" + _OWNER + "/x", "/UsErS/" + _OWNER + "/x",
                     "/home/" + _OWNER + "/x", "/Home/" + _OWNER + "/x",
                     "/HOME/" + _OWNER + "/x"):
            self.assertTrue(cc.line_is_personal_path_hit(line), line)

    def test_case_variant_slug_hits(self):
        self.assertTrue(cc.line_is_personal_path_hit("-users-" + _OWNER + "-repo"))
        self.assertTrue(cc.line_is_personal_path_hit("-Users-" + _OWNER + "-repo"))

    def test_placeholders_stay_clean_in_every_spelling(self):
        """The measured reason this cure costs nothing on this repository."""
        for line in ("/users/me", "GET /users/me HTTP/1.1", "/Users/me/x",
                     "/users/alice/x", "/USERS/dev/x", "/home/runner/work"):
            self.assertFalse(cc.line_is_personal_path_hit(line), line)

    def test_the_captured_owner_segment_keeps_its_own_case(self):
        """The fold is on the ROOT; the capture is untouched.

        This used to be named for a claim that is not true --
        `re.IGNORECASE` does not lowercase captured text either, so it
        would not have broken this. What the test actually pins is the
        contract callers depend on: the owner segment comes back as it
        was written, and the lowercasing happens once, in
        `_personal_path_owner_segments`, where the placeholder list is
        compared.
        """
        segs = cc._personal_path_owner_segments("/users/ZzFake/x")
        self.assertEqual(segs, ["zzfake"])
        match = cc._PERSONAL_PATH_HOME_RE.search("/UsErS//ZzFake/x")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "ZzFake")

    def test_literal_fast_path_is_derived_from_the_tuple(self):
        """One authority: the folded fast path is built FROM the literals."""
        for literal in cc._PERSONAL_PATH_LITERALS:
            self.assertTrue(cc._PERSONAL_PATH_LITERAL_RE.search(literal),
                            literal)
            self.assertTrue(
                cc._PERSONAL_PATH_LITERAL_RE.search(literal.upper()), literal)
            self.assertTrue(
                cc._PERSONAL_PATH_LITERAL_RE.search(literal.lower()), literal)

    def test_a_non_home_root_is_still_not_a_home_path(self):
        for line in ("/usr/local/bin", "/houses/" + _OWNER + "/x",
                     "example.com/users/" + _OWNER, "./Users/" + _OWNER):
            self.assertFalse(cc.line_is_personal_path_hit(line), line)


class RailRound18MechanismCures(_Base):
    """The three round-18 mechanism findings, each with its own probe.

    `_Base`, not a bare `unittest.TestCase`: the env-hygiene gate of
    this repository refuses one, and a matcher test that reads the
    ambient `$HOME` is a test of the machine it runs on.
    """

    def test_a_utf16_document_is_refused_not_read_clean(self):
        """M1: the same content, two encodings, one hit and one refusal."""
        body = "# probe\n/Users/" + _OWNER + "/secret/repo\n"
        self.commit_bytes("docs/probe-utf8.md", body.encode("utf-8"))
        self.assertEqual(self.unwaived_rels(), ["docs/probe-utf8.md"])
        self.commit_bytes("docs/probe-utf16.md", body.encode("utf-16"))
        with self.assertRaises(cc.PersonalPathUnreadable) as caught:
            self.scan()
        message = str(caught.exception)
        self.assertIn("NUL", message)
        self.assertIn("probe-utf16.md", message)
        self.assertNotIn(_OWNER, message)

    def test_the_refusal_is_about_the_bytes_not_the_suffix(self):
        """A UTF-8 file with an embedded NUL is refused the same way."""
        self.commit_bytes("docs/nul.md", b"# ok\n\x00\n")
        with self.assertRaises(cc.PersonalPathUnreadable):
            self.scan()

    def test_a_control_character_in_the_allowlist_waives_nothing(self):
        """M2: the row parsed and granted while git rendered it binary."""
        body = "/Users/" + _OWNER + "/secret/repo\n"
        path = self.commit_bytes("docs/frozen.md", body.encode("utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        row = "docs/frozen.md | sha256:%s | frozen artifact" % digest
        self.allowlist.write_text(row + "\n", encoding="utf-8")
        entries, malformed = cc.load_personal_path_allowlist(self.allowlist)
        self.assertEqual(sorted(entries), ["docs/frozen.md"])
        self.assertEqual(malformed, [])
        self.allowlist.write_bytes(
            ("# reviewed\n" + row + "\x00hidden\n").encode("utf-8"))
        with self.assertRaises(cc.PersonalPathUnreadable) as caught:
            cc.load_personal_path_allowlist(self.allowlist)
        message = str(caught.exception)
        self.assertIn("U+0000", message)
        self.assertIn("row 2", message)
        self.assertNotIn("frozen artifact", message)
        self.assertNotIn("hidden", message)

    def test_tab_and_newline_are_still_ordinary_text_in_the_list(self):
        """The class excludes exactly the three characters it must."""
        for ok in ("\t", "\n", "\r"):
            self.assertIsNone(
                cc._PERSONAL_PATH_ALLOWLIST_CONTROL_RE.search(ok), repr(ok))
        for bad in ("\x00", "\x1b", "\x0b", "\x0c", "\x7f", "\x9f"):
            self.assertIsNotNone(
                cc._PERSONAL_PATH_ALLOWLIST_CONTROL_RE.search(bad), repr(bad))

    def test_a_backslash_path_gets_a_row_the_parser_accepts(self):
        """M3: the emitted row round-trips to the SAME path."""
        rel = "docs/a\\b.md"
        body = "/Users/" + _OWNER + "/secret/repo\n"
        path = self.commit_bytes(rel, body.encode("utf-8"))
        scan = self.scan()
        hits = [h for h in scan.hits if h.rel == rel]
        self.assertEqual(len(hits), 1, [h.rel for h in scan.hits])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        candidate = "%s | sha256:%s | %s" % (
            rel, digest, cc._PERSONAL_PATH_UNREASONED)
        probe = cc._PERSONAL_PATH_ROW_RE.match(candidate)
        self.assertIsNotNone(probe)
        self.assertEqual(probe.group(1), rel)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cc._emit_personal_path_rows(scan, {})
        emitted = [line for line in buffer.getvalue().splitlines()
                   if line.startswith(rel + " |")]
        self.assertEqual(len(emitted), 1, buffer.getvalue())
        self.assertNotIn("a\\\\b", buffer.getvalue())

    def test_a_control_character_in_a_path_is_still_refused_a_row(self):
        """The property display owned here is kept as an explicit refusal."""
        rel = "docs/a\nb.md"
        body = "/Users/" + _OWNER + "/secret/repo\n"
        self.commit_bytes(rel, body.encode("utf-8"))
        scan = self.scan()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cc._emit_personal_path_rows(scan, {})
        self.assertNotIn("\nb.md |", buffer.getvalue())


class RailRound19MechanismCures(_Base):
    """The two round-19 mechanism findings, each with its own probe."""

    def _waive(self, rel="docs/frozen.md", reason="frozen artifact"):
        """Commit an in-scope leak and return an exact-digest row for it."""
        body = "at /Users/" + _OWNER + "/work/repo\n"
        path = self.commit_bytes(rel, body.encode("utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return "%s | sha256:%s | %s" % (rel, digest, reason)

    def test_a_reason_of_zero_width_spaces_waives_nothing(self):
        row = self._waive(reason="​​")
        self.allowlist.write_text(row + "\n", encoding="utf-8")
        entries, malformed = cc.load_personal_path_allowlist(self.allowlist)
        self.assertEqual(entries, {})
        self.assertEqual(malformed, [1])

    def test_a_reason_carrying_a_bidi_override_waives_nothing(self):
        row = self._waive(reason="reviewed‮DEWEIVERNU")
        self.allowlist.write_text(row + "\n", encoding="utf-8")
        entries, malformed = cc.load_personal_path_allowlist(self.allowlist)
        self.assertEqual(entries, {})
        self.assertEqual(malformed, [1])

    def test_an_ordinary_reason_still_waives(self):
        """The control that keeps the cure from being a blanket refusal."""
        row = self._waive(reason="frozen transcript, reviewed 2026-09-05")
        self.allowlist.write_text(row + "\n", encoding="utf-8")
        entries, malformed = cc.load_personal_path_allowlist(self.allowlist)
        self.assertEqual(sorted(entries), ["docs/frozen.md"])
        self.assertEqual(malformed, [])

    def test_the_visibility_predicate_answers_both_halves(self):
        """Round 19's cases, re-asked of the POSITIVE predicate (r13 M2)."""
        for bad in ("​", "⁠", " \t ", "", "ok‮", "ok﻿",
                    "frozen", "a", "não-ascii"):
            self.assertFalse(
                cc._personal_path_reason_is_visible(bad), repr(bad))
        for good in ("reviewed 2026", "frozen artifact",
                     "não-ascii mas com ink"):
            self.assertTrue(
                cc._personal_path_reason_is_visible(good), repr(good))


class RailRound19TextCures(_Base):
    """The behaviour half of the round-19 text lane: an interior control."""

    def test_a_carriage_return_inside_a_reason_waives_nothing(self):
        body = "at /Users/" + _OWNER + "/work/repo\n"
        path = self.commit_bytes("docs/frozen.md", body.encode("utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        row = "docs/frozen.md | sha256:%s | reviewed\rHIDDEN" % digest
        self.allowlist.write_text(row + "\n", encoding="utf-8")
        # Since round 20 the interior CR is caught on the PHYSICAL row,
        # before the grammar can strip it into a clean-looking reason.
        with self.assertRaises(cc.PersonalPathUnreadable) as caught:
            cc.load_personal_path_allowlist(self.allowlist)
        self.assertIn("carriage return INSIDE row 1", str(caught.exception))

    def test_the_predicate_rejects_the_control_class_too(self):
        for bad in ("reviewed\rHIDDEN", "a\x1b[2Kb", "a\tb", "a\x7fb"):
            self.assertFalse(
                cc._personal_path_reason_is_visible(bad), repr(bad))

    def test_a_trailing_carriage_return_is_still_only_a_line_ending(self):
        """The FILE class keeps `\r`; only a reason refuses it."""
        body = "at /Users/" + _OWNER + "/work/repo\n"
        path = self.commit_bytes("docs/frozen.md", body.encode("utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        row = "docs/frozen.md | sha256:%s | frozen artifact" % digest
        self.allowlist.write_bytes((row + "\r\n").encode("utf-8"))
        entries, malformed = cc.load_personal_path_allowlist(self.allowlist)
        self.assertEqual(sorted(entries), ["docs/frozen.md"])
        self.assertEqual(malformed, [])


class RailRound20MechanismCures(_Base):
    """The two round-20 mechanism findings, each with its own probe."""

    def test_a_slug_ends_at_any_delimiter_not_only_a_hyphen(self):
        for line in ("~/.claude/projects/-Users-" + _OWNER + "/memory/",
                     "docs/-Users-" + _OWNER + "/note.md",
                     '"-Users-' + _OWNER + '"',
                     "see -Users-" + _OWNER + ", then",
                     "-Users-" + _OWNER + "-repo",
                     "-Users-" + _OWNER):
            self.assertTrue(cc.line_is_personal_path_hit(line), line)

    def test_the_elided_spelling_stays_clean_in_both_forms(self):
        """The measured reason this widening costs nothing on this repo."""
        for line in ("-Users-...-repo", "-Users-…-repo",
                     "/Users/.../project", "/Users/…/project",
                     "-Users-me/x", "-Users-dev/x"):
            self.assertFalse(cc.line_is_personal_path_hit(line), line)

    def test_the_owner_capture_still_stops_at_the_delimiter(self):
        match = cc._PERSONAL_PATH_SLUG_RE.search(
            "-Users-" + _OWNER + "/memory")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), _OWNER)

    def test_a_reason_of_combining_marks_waives_nothing(self):
        body = "at /Users/" + _OWNER + "/work/repo\n"
        path = self.commit_bytes("docs/frozen.md", body.encode("utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for reason in ("͏", "͏͏", "️"):
            row = "docs/frozen.md | sha256:%s | %s" % (digest, reason)
            self.allowlist.write_text(row + "\n", encoding="utf-8")
            entries, malformed = cc.load_personal_path_allowlist(
                self.allowlist)
            self.assertEqual(entries, {}, reason.encode("unicode_escape"))
            self.assertEqual(malformed, [1])

    def test_the_predicate_asks_for_ink_not_for_absence(self):
        """Round 20's cases under the r13 M2 predicate: a WORD, not a mark."""
        for bad in ("͏", "️", "​", "\r", " ", "",
                    "frozen", "2026", "-", "#", "é", "a͏"):
            self.assertFalse(
                cc._personal_path_reason_is_visible(bad), repr(bad))
        for good in ("frozen 26", "reviewed 2026", "a͏bcdefgh"):
            self.assertTrue(
                cc._personal_path_reason_is_visible(good), repr(good))


class RailRound20TextCures(_Base):
    """The three P1 visibility failures of the round-20 text lane."""

    def _row(self, reason="frozen artifact"):
        body = "at /Users/" + _OWNER + "/work/repo\n"
        path = self.commit_bytes("docs/frozen.md", body.encode("utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return "docs/frozen.md | sha256:%s | %s" % (digest, reason)

    def test_a_carriage_return_inside_the_separators_waives_nothing(self):
        row = self._row()
        head, _, tail = row.rpartition("| ")
        self.allowlist.write_bytes(
            (head + "| \r# reviewed\n").encode("utf-8"))
        with self.assertRaises(cc.PersonalPathUnreadable) as caught:
            cc.load_personal_path_allowlist(self.allowlist)
        self.assertIn("carriage return INSIDE row 1", str(caught.exception))

    def test_a_row_ending_in_cr_is_still_a_line_ending(self):
        self.allowlist.write_bytes((self._row() + "\r\n").encode("utf-8"))
        entries, malformed = cc.load_personal_path_allowlist(self.allowlist)
        self.assertEqual(sorted(entries), ["docs/frozen.md"])
        self.assertEqual(malformed, [])

    def test_an_oserror_reason_naming_a_home_is_redacted(self):
        leak = "cannot open /Users/" + _OWNER + "/secret/repo"
        self.assertNotIn(
            _OWNER, cc._personal_path_safe(leak))


class RailRound21CuresTheR13Architecture(_Base):
    """The Owner's r13 decision, one probe per move.

    Round 21 was the registered CAP: its findings were reproduced and NOT
    cured, because curing at a cap ships code no round reviewed. The CEO
    then decided the architecture rather than the next enumeration, and
    this class is that decision made falsifiable.
    """

    def _row(self, reason="frozen ceremony artifact 2026"):
        body = "at /Users/" + _OWNER + "/work/repo\n"
        path = self.commit_bytes("docs/frozen.md", body.encode("utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return "docs/frozen.md | sha256:%s | %s" % (digest, reason)

    # --- M1: the git-rendering premise is GONE, not enumerated further ---

    def test_the_module_asks_git_nothing_about_rendering(self):
        for gone in ("_personal_path_require_diffable",
                     "_personal_path_allowlist_is_diffable",
                     "_personal_path_diff_attribute",
                     "_personal_path_waived_summary",
                     "_PERSONAL_PATH_WAIVED_PRINT_CAP"):
            self.assertFalse(hasattr(cc, gone), gone)
        source = Path(cc.__file__).read_text(encoding="utf-8")
        self.assertNotIn("check-attr", source)

    def test_a_driver_named_unspecified_no_longer_decides_anything(self):
        """Round 21's P1, replayed: the gate has no opinion to defeat."""
        self.allowlist.write_text(self._row() + "\n", encoding="utf-8")
        subprocess.run(["git", "config", "diff.unspecified.binary", "true"],
                       cwd=self.root, check=True, capture_output=True)
        (self.root / ".gitattributes").write_text(
            "* diff=unspecified\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True,
                       capture_output=True)
        proc = self.cli()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        # git renders the list as binary; the gate STATES what it granted.
        self.assertIn("honoured allowlist rows (1", proc.stdout)
        self.assertIn("docs/frozen.md | sha256:", proc.stdout)

    def test_the_honoured_set_prints_on_a_RED_run_too(self):
        self.commit("docs/leak.md", "b: %s\n" % _MAC)
        self.allowlist.write_text(self._row() + "\n", encoding="utf-8")
        proc = self.cli()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("honoured allowlist rows (1", proc.stdout)
        self.assertIn("docs/frozen.md | sha256:", proc.stdout)

    def test_emit_mode_keeps_stdout_rows_only(self):
        self.allowlist.write_text(self._row() + "\n", encoding="utf-8")
        self.commit("docs/leak.md", "b: %s\n" % _MAC)
        proc = self.cli("--emit-personal-path-rows")
        self.assertNotIn("honoured allowlist rows", proc.stdout)
        self.assertIn("honoured allowlist rows (1", proc.stderr)

    def test_the_digest_is_over_the_row_values_not_the_display(self):
        allow = {"docs/a.md": cc.PersonalPathRow(
            sha256="a" * 64, reason="reviewed ceremony 2026", rowno=1)}
        rows, digest = cc._personal_path_honoured_rows(
            [("docs/a.md", "reviewed ceremony 2026")], allow)
        self.assertEqual(len(rows), 1)
        expected = hashlib.sha256(
            ("docs/a.md\0" + "a" * 64
             + "\0reviewed ceremony 2026").encode("utf-8")).hexdigest()
        self.assertEqual(digest, expected)

    def test_the_honoured_order_is_by_path(self):
        allow = {}
        waived = []
        for rel in ("docs/c.md", "docs/a.md", "docs/b.md"):
            allow[rel] = cc.PersonalPathRow(
                sha256="d" * 64, reason="frozen artifact 2026", rowno=1)
            waived.append((rel, "frozen artifact 2026"))
        rows, _ = cc._personal_path_honoured_rows(waived, allow)
        self.assertEqual([r.split(" |")[0] for r in rows],
                         ["docs/a.md", "docs/b.md", "docs/c.md"])

    # --- M2: the reason predicate is POSITIVE ---

    def test_fillers_of_any_category_carry_no_ink(self):
        for filler in ("ㅤ" * 40, "⠀" * 40, "ᅟ" * 40,
                       "͏" * 40, "​" * 40, "️" * 40):
            self.assertFalse(
                cc._personal_path_reason_is_visible(filler),
                filler.encode("unicode_escape"))

    def test_a_filler_reason_waives_nothing_end_to_end(self):
        """Round 21's P2, at the CLI: `Lo`/`So` fillers granted at rc 0."""
        for filler in ("ㅤ" * 20, "⠀" * 20):
            self.allowlist.write_text(
                self._row(reason=filler) + "\n", encoding="utf-8")
            proc = self.cli()
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("MALFORMED", proc.stdout)
            self.assertIn("honoured allowlist rows (0", proc.stdout)

    def test_eight_ascii_letters_or_digits_are_required(self):
        self.assertEqual(cc._PERSONAL_PATH_REASON_MIN_INK, 8)
        self.assertFalse(cc._personal_path_reason_is_visible("frozen"))
        self.assertFalse(cc._personal_path_reason_is_visible("rail 20"))
        self.assertTrue(cc._personal_path_reason_is_visible("frozen 26"))
        self.assertTrue(
            cc._personal_path_reason_is_visible("ceremonia congelada"))

    def test_the_ink_is_counted_after_NFKC(self):
        wide = "".join(chr(0xFF21 + i) for i in range(8))
        self.assertEqual(len(wide), 8)
        self.assertTrue(cc._personal_path_reason_is_visible(wide))

    def test_an_interior_control_is_still_refused(self):
        self.assertFalse(
            cc._personal_path_reason_is_visible("reviewed 2026\rHIDDEN"))

    # --- M3: linear matcher, and a deadline for the general case ---

    def test_a_long_separator_run_is_no_longer_quadratic(self):
        """1.833 s at 16 000 slashes before this cure (round 21, A1)."""
        line = "/" * 16000 + " not-root /Users/devuser/x"
        start = time.perf_counter()
        cc.line_is_personal_path_hit(line)
        elapsed = time.perf_counter() - start
        # The measured figure is two orders of magnitude under this bound;
        # the bound is loose ON PURPOSE, because a timing assertion tight
        # enough to be impressive is a flake on a loaded runner. The
        # quadratic shape is what is being refused, and 0.5 s refuses it.
        self.assertLess(elapsed, 0.5, elapsed)

    def test_the_matcher_answers_the_same_on_every_boundary_form(self):
        for line, expected in (
                ("/Users/" + _OWNER + "/x", True),
                ("//Users/" + _OWNER + "/x", True),
                ("///Users/" + _OWNER + "/x", True),
                ("a/Users/" + _OWNER + "/x", False),
                ("a//Users/" + _OWNER + "/x", True),
                ("./Users/" + _OWNER + "/x", False),
                ("~/Users/" + _OWNER + "/x", False),
                ('"/Users/' + _OWNER + '/x"', True),
                ("/users/" + _OWNER + "/x", True),
                ("/home/" + _OWNER + "/x", True),
                ("/Users/devuser/x", False)):
            self.assertEqual(
                cc.line_is_personal_path_hit(line), expected, line)

    def test_the_mask_still_replaces_the_leading_slash(self):
        self.assertEqual(
            cc._personal_path_mask_rel("/Users/" + _OWNER + "/x"),
            "/home/<redacted-owner>/x")

    def test_the_file_deadline_refuses_rather_than_returns_partial(self):
        with self.assertRaises(cc.PersonalPathUnreadable) as caught:
            cc.personal_path_hit_lines("x\n" * 4096, deadline=0.0)
        self.assertIn("deadline", str(caught.exception))
        self.assertEqual(
            cc.personal_path_hit_lines("x\n" * 4096, deadline=None), ())
        # A budget that has NOT passed refuses nothing, on a file of any
        # shape: the control for the two assertions above.
        far = time.monotonic() + 3600.0
        self.assertEqual(
            cc.personal_path_hit_lines("x\n" * 4096, deadline=far), ())
        self.assertEqual(
            cc.personal_path_hit_lines("one single line", deadline=far), ())


class RailRound22MechanismCures(_Base):
    """The four round-22 findings, each with the probe that reproduced it."""

    def test_the_row_parser_is_not_quadratic(self):
        row = ("docs/a.md | sha256:" + "a" * 64 + " | reviewed"
               + " " * 64000 + "artifact")
        start = time.perf_counter()
        match = cc._PERSONAL_PATH_ROW_RE.match(row)
        elapsed = time.perf_counter() - start
        self.assertIsNotNone(match)
        # 16.687 s before the cure. The bound is loose on purpose: a
        # timing assertion tight enough to be impressive is a flake on a
        # loaded runner, and the shape being refused is quadratic growth.
        self.assertLess(elapsed, 1.0, elapsed)

    def test_the_two_row_patterns_accept_the_same_rows(self):
        """The differential the cure is justified by, as a test."""
        old = re.compile(
            r"^([^\s|]+)\s*\|\s*sha256:([0-9A-Fa-f]{64})\s*\|\s*(\S.*?)\s*$")
        sha = "a" * 64
        shapes = [
            "docs/a.md | sha256:%s | reviewed 2026" % sha,
            "docs/a.md|sha256:%s|reviewed 2026" % sha,
            "docs/a.md   |   sha256:%s   |   reviewed 2026" % sha,
            "docs/a.md | sha256:%s |  a | b 2026 review" % sha,
            "docs/a.md | sha256:%s | reviewed  2026  x" % sha,
            "docs/a.md | sha256:%s |" % sha,
            "docs/a.md | sha256:%s | " % sha,
            "docs/a.md | sha256:%s" % sha,
            "docs/a.md | reviewed 2026",
            "docs/with space.md | sha256:%s | reviewed 2026" % sha,
            "# a comment",
            "",
        ]
        shipped = (Path(cc.__file__).resolve().parent
                   / "contamination-personal-path-allowlist.txt")
        shapes.extend(
            line.strip()
            for line in shipped.read_text(encoding="utf-8").splitlines())
        for shape in shapes:
            a = old.match(shape)
            b = cc._PERSONAL_PATH_ROW_RE.match(shape)
            self.assertEqual(a is None, b is None, shape[:60])
            if a is not None:
                self.assertEqual(a.groups(), b.groups(), shape[:60])

    def test_the_deadline_fires_on_a_one_line_file(self):
        """A one-line file is checked ONCE, after its line (v62).

        With the check at the TOP of the loop body this passed while the
        gate still returned 0 on the input the finding named: the single
        check ran before any work, and the loop ended without another.
        The assertion below therefore names the line NUMBER, which only
        an after-the-line check can report.
        """
        with self.assertRaises(cc.PersonalPathUnreadable) as caught:
            cc.personal_path_hit_lines("one single line", deadline=0.0)
        self.assertIn("deadline", str(caught.exception))
        self.assertIn("after line 1", str(caught.exception))

    def test_the_deadline_refusal_names_the_file(self):
        self.commit("docs/slow.md", "ordinary text\n")
        with mock.patch.object(
                cc, "personal_path_hit_lines",
                side_effect=cc.PersonalPathUnreadable("matching timed out")):
            with self.assertRaises(cc.PersonalPathUnreadable) as caught:
                cc.scan_personal_paths(self.root)
        self.assertIn("docs/slow.md", str(caught.exception))
        self.assertIn("matching timed out", str(caught.exception))

    def test_a_bidi_override_in_a_PATH_is_escaped(self):
        raw = "docs/a\u202eb.md"
        shown = cc._personal_path_escape_controls(raw)
        self.assertNotIn("\u202e", shown)
        self.assertIn("\\u202e", shown)

    def test_the_escape_stays_injective_at_every_width(self):
        pairs = (
            ("docs/x\ny.md", "docs/x" + chr(92) + "x0ay.md"),
            ("docs/x\u202ey.md", "docs/x" + chr(92) + "u202ey.md"),
        )
        for real, literal in pairs:
            self.assertNotEqual(
                cc._personal_path_escape_controls(real),
                cc._personal_path_escape_controls(literal))

    def test_ordinary_text_including_accents_is_untouched(self):
        for value in ("docs/naïve/über.md", "archived evidence, 2026-01",
                      "docs/日本語.md"):
            self.assertEqual(cc._personal_path_escape_controls(value), value)

    def test_a_path_that_does_not_render_gets_no_row(self):
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        bad = "docs/a\u202eb.md"
        self.commit(bad, "see " + _MAC + "\n")
        proc = self.cli("--emit-personal-path-rows")
        self.assertNotIn("\u202e", proc.stdout)
        self.assertIn("no row form", proc.stderr)


class RailRound23OneEscapingBoundary(_Base):
    """One path becomes text ONCE, and the same way in every section."""

    def test_a_newline_path_and_its_literal_spelling_stay_distinct(self):
        """The collision reproduced in round 23, as a regression test."""
        newline = "docs/x\ny.md"
        literal = "docs/x" + chr(92) + "x0ay.md"
        finding = cc._personal_path_mask_rel(newline)
        honoured = cc._personal_path_mask_rel(literal)
        self.assertNotEqual(finding, honoured)

    def test_the_group_printer_does_not_escape(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cc._print_personal_path_group("file:line", ["docs/a" + chr(92)
                                                        + "x0ab.md:2"])
        self.assertIn("docs/a" + chr(92) + "x0ab.md:2", buf.getvalue())

    def test_a_stale_row_is_masked_at_its_call_site(self):
        """The one call site that used to hand the printer raw rels."""
        self.commit("docs/keep.md", "frozen: %s\n" % _MAC)
        self.allowlist.write_text(
            self.row("docs/keep.md", "frozen 2026") + "\n"
            + "docs/gone.md | sha256:%s | frozen 2026\n" % ("a" * 64),
            encoding="utf-8")
        proc = self.cli("--fail-on-stale")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("docs/gone.md", proc.stdout)
        self.assertNotIn(_OWNER, proc.stdout)

    def test_every_printed_path_crosses_the_boundary_once(self):
        """End to end: the same file, waived and unwaived, one spelling."""
        self.commit("docs/leak.md", "see " + _MAC + "\n")
        red = self.cli()
        self.assertEqual(red.returncode, 1, red.stdout)
        self.assertIn("docs/leak.md:1", red.stdout)
        self.allowlist.write_text(
            self.row("docs/leak.md", "frozen 2026"), encoding="utf-8")
        green = self.cli()
        self.assertEqual(green.returncode, 0, green.stdout)
        self.assertIn("docs/leak.md | sha256:", green.stdout)


class RailRound23TextCures(_Base):
    """The round-23 text findings that live in the shipped module."""

    def test_no_fatal_path_prints_a_raw_oserror_reason(self):
        """T3: four handlers in main() bypassed the redaction boundary."""
        source = Path(cc.__file__).read_text(encoding="utf-8")
        raw = [line.strip() for line in source.splitlines()
               if "_oserror_reason(exc)" in line
               and "_personal_path_safe" not in line
               and not line.strip().startswith("#")]
        # The one that remains is the RAISE inside the blob reader, whose
        # message is redacted by the handler that prints it.
        self.assertEqual(
            [r for r in raw if r.startswith("print") or r.startswith("%")],
            [], raw)

    def test_an_unresolvable_root_naming_a_home_is_redacted(self):
        proc = subprocess.run(
            [sys.executable, str(Path(cc.__file__).resolve()),
             "--root", "/Users/" + _OWNER + "/no/such/tree"],
            capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertNotIn(_OWNER, proc.stdout + proc.stderr)

    def test_the_predicate_claims_only_printability(self):
        """T4: printable is not the same as visible, and both are true."""
        for blank in ("\u2800", "\u034f", "\u3164"):
            self.assertTrue(cc._personal_path_renders_as_itself(blank))
            self.assertFalse(cc._personal_path_reason_is_visible(blank * 20))

    def test_the_module_no_longer_claims_the_removed_premise(self):
        source = Path(cc.__file__).read_text(encoding="utf-8")
        for gone in ("reviewable DIFF and not a",
                     "ONE NUL inside the first 8000",
                     "The two lookbehinds"):
            self.assertNotIn(gone, source)

    def test_a_fatal_input_prints_no_honoured_set(self):
        """T5: the claim is every run that reaches a VERDICT."""
        self.allowlist.write_bytes(b"docs/a.md | sha256:\x00 | x\n")
        proc = self.cli()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertNotIn("honoured allowlist rows", proc.stdout)


class RailRound23ModuleClaims(_Base):
    """The three facts the round-23 corrections rest on."""

    def test_a_replacement_character_does_not_truncate_the_owner(self):
        """T7: the capture is the WHOLE segment, and the line still hits."""
        line = "/Users/dev�name/work"
        match = cc._PERSONAL_PATH_HOME_RE.search(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "dev�name")
        self.assertTrue(cc.line_is_personal_path_hit(line))

    def test_the_explicit_class_is_narrower_than_ignorecase(self):
        """T8: U+017F is the counter-example the note now names."""
        self.assertIsNone(
            cc._PERSONAL_PATH_HOME_RE.search("/uſers/" + _OWNER + "/x"))
        self.assertIsNotNone(
            re.search(r"/users/", "/uſers/x", re.IGNORECASE))


class RailRound24PlaceholderMask(_Base):
    """The mask redacts people and leaves PLACEHOLDERS legible.

    Round 24 found the report collapsing three distinct tracked files onto
    one line. Every test here fails for a different half of the cure, so
    "the owners are preserved" and "a person still never survives" cannot
    be satisfied by deleting the other.
    """

    def test_two_placeholder_owners_stay_two_different_paths(self):
        """T1: the finding says WHICH file (the round-24 reproduction)."""
        alice = cc._personal_path_mask_rel("docs/-Users-alice-repo/log.md")
        bob = cc._personal_path_mask_rel("docs/-Users-bob-repo/log.md")
        self.assertEqual(alice, "docs/-Users-alice-repo/log.md")
        self.assertEqual(bob, "docs/-Users-bob-repo/log.md")
        self.assertNotEqual(alice, bob)

    def test_a_real_owner_never_survives_the_mask(self):
        """T2: containment is what the preservation must not cost.

        The three forms that are HITS as a repo-relative path: the slug,
        and the two absolute spellings reached where the matcher accepts
        them -- after a separator, never after a word character (see T6).
        """
        for rel in ("docs/" + _SLUG + "/log.md",
                    "docs/" + _MAC + "/log.md",
                    "docs/" + _LINUX + "/log.md"):
            self.assertTrue(cc.line_is_personal_path_hit(rel), rel)
            masked = cc._personal_path_mask_rel(rel)
            self.assertNotIn(_OWNER, masked, rel)
            self.assertIn("<redacted-owner>", masked, rel)

    def test_a_relative_users_directory_is_not_a_hit_to_begin_with(self):
        """T6: the mask leaves it alone because the RULE never claimed it.

        `docs/Users/<name>/x` reads as a directory called `Users`, not as
        an absolute home path: the matcher requires the `/Users/` not to
        follow a word character. So nothing is masked there and nothing
        should be -- a mask cannot redact what the rule never called a
        leak. Written down because reading the OWNER out of such a path
        and calling it a leak is a false alarm this pack hit twice while
        curing round 24, once in a fixture and once in an instrument.
        """
        rel = "docs/Users/" + _OWNER + "/work/log.md"
        self.assertFalse(cc.line_is_personal_path_hit(rel))
        self.assertEqual(cc._personal_path_mask_rel(rel), rel)

    def test_one_path_carrying_both_keeps_only_the_placeholder(self):
        """T3: the decision is per SEGMENT, not per path."""
        masked = cc._personal_path_mask_rel(
            "docs/-Users-alice-repo/-Users-" + _OWNER + "-x.md")
        self.assertEqual(
            masked, "docs/-Users-alice-repo/-Users-<redacted-owner>-x.md")

    def test_a_folded_owner_is_not_treated_as_a_placeholder(self):
        """T4: the RAW reading decides; folding would be the bypass."""
        wide = "\uff44\uff45\uff56"          # full-width `dev`
        masked = cc._personal_path_mask_rel("docs/-Users-" + wide + "-r/x.md")
        self.assertNotIn(wide, masked)
        self.assertIn("<redacted-owner>", masked)

    def test_the_mask_asks_the_matcher_s_own_list(self):
        """T5: one predicate, so a widening cannot leave the mask behind."""
        for owner in sorted(cc._PERSONAL_PATH_PLACEHOLDERS):
            if not owner.isalnum():
                continue
            rel = "docs/-Users-" + owner + "-repo/x.md"
            self.assertFalse(cc.line_is_personal_path_hit(rel), rel)
            self.assertEqual(cc._personal_path_mask_rel(rel), rel, rel)


class TestWalkerFailureIsSanitised(TestEnvContext):
    """The ENUMERATION can fail, not just one file (land round 1, text lane).

    `PersonalPathUnreadable` names a file the rule could not READ. The walker
    itself -- the index query underneath it -- can fail for its own reasons,
    and that escaped as an UNCAUGHT exception whose TRACEBACK frame lines
    carry the absolute checkout path. The frames are printed by the
    interpreter, so no redaction inside the rule can reach them: the only
    cure is not to let the exception out.
    """

    def _run_main_with_walker_failing(self, exc):
        import io
        import contextlib
        err = io.StringIO()
        real = cc.scan_personal_paths

        def boom(_root):
            raise exc

        cc.scan_personal_paths = boom
        try:
            with contextlib.redirect_stderr(err):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = cc.main([])
        finally:
            cc.scan_personal_paths = real
        return rc, err.getvalue()

    def test_permission_error_exits_2_without_a_traceback(self):
        """The cure: rc 2 and a named FATAL, not an uncaught exception."""
        rc, err = self._run_main_with_walker_failing(
            PermissionError(13, "Permission denied"))
        self.assertEqual(rc, 2, err)
        self.assertIn("cannot enumerate in-scope files", err)
        self.assertNotIn("Traceback", err)

    def test_the_owner_segment_never_survives_the_message(self):
        """POSITIVE CONTROL: the message goes through the same choke point."""
        rc, err = self._run_main_with_walker_failing(
            OSError(5, "Input/output error",
                    "/Users/" + _OWNER + "/canhada-labs/x"))
        self.assertEqual(rc, 2, err)
        self.assertNotIn(_OWNER, err)
        self.assertIn("<redacted: names a home directory>", err)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
