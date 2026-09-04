#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The AC-14 classifier oracle's EXIT CODE is the contract (PLAN-186 W5-US2).

Why this file exists
--------------------
`.claude/plans/PLAN-186/w5/check-classifier-cases.py` prints a report and
returns an exit code. The S341 refutation observed it print

    check-classifier-cases: 1 PROBLEM(S)
      [ROW-UNCOVERED] §2b row R2 has no non-boundary worked case ...
    rc=0

A gate that reports and returns success is a false green *by construction*: a
CI step, ``validate-governance.sh`` and a land script all read ``$?``, never
the prose. Prose in the checker's own docstring cannot constrain what ``main``
returns — only an assertion on the rc can. That is this file.

  * a consistent tree                       -> rc 0
  * a §2b row left with no worked case      -> rc 1
  * an input the gate cannot use            -> rc 2  (fail-CLOSED on input,
                                                      CLAUDE.md §4)

Which cases are CURES and which are PINS
----------------------------------------
Measured against the pre-cure oracle (the `ac14-task-classifier` payload at
sha256 9f49e60b…), on this repo at ba15c71:

  case 1  consistent -> 0                     PIN   (0 before, 0 after)
  case 2  row uncovered -> 1                  PIN   (1 before, 1 after) —
          it is the S341 control, and it must stay pinned because that is the
          exact assertion the refuted build failed.
  case 3  fixture absent -> 2                 PIN   (2 before, 2 after)
  case 4  doc present but undecodable -> 2    CURE  (before: an uncaught
          UnicodeDecodeError, i.e. rc 1 — indistinguishable from a finding)
  case 5  fixture is a JSON array -> 2        CURE  (before: an uncaught
          AttributeError on ``fixture.get``, rc 1)
  case 6  absolute citation path -> 1         CURE  (before: rc **0** — the
          sharpest control here: ``root / rel`` discards ``root`` when ``rel``
          is absolute, so a path naming a file inside this checkout verified
          and the gate reported CONSISTENT)
  case 7  ``"citations": [null]`` -> named 1  CURE  (before: AttributeError,
          rc 1 with no named code)
  case 8  a citation with a ``line`` key -> 1  CURE  (S343 v2: the v1 grammar
          ACCEPTED it — line pins are what collided with the W1 routing patch;
          it subsumes the S341 ``"line": true`` control, since the key is now
          refused whatever its type)
  case 9  "N PROBLEM(S)" printed => rc != 0   PIN on the binding itself

Non-vacuity, deliberately
-------------------------
* The mutation in case 2 is **derived**, never recalled: the test reads the
  shipped fixture, finds a row that exactly one non-boundary case covers, and
  drops that case. Hardcoding "drop C2" would rot the day the cases are
  renumbered, and would then assert nothing.
* Every case runs the checker as a **subprocess**, so what is measured is the
  process exit status — the thing a caller sees — not the return value of a
  function the test imported.
* Case 2 additionally asserts the ROW-UNCOVERED *code* appears. Not to pin
  wording (the gating assertion is ``rc == 1``) but to prove the rc came from
  the condition under test rather than from a typo in the temp fixture: a
  non-zero rc for the wrong reason is not evidence.
* The committed fixture and doc are never touched: each case writes a copy
  into a ``TemporaryDirectory`` and points ``--fixture`` / ``--doc`` at it.

Discipline: stdlib-only, Python >= 3.9, ``from __future__ import annotations``,
``typing.Optional`` (no runtime PEP 604, no ``match``). ``TestEnvContext`` for
env isolation. The checker imports nothing from ``_lib`` and writes no file, so
no audit event is emitted and the live HMAC chain is untouched.

S343 — where this file lives, and one case more
-----------------------------------------------
The S341 build of this test sat in ``tests/unit/``; it now sits in
``.claude/scripts/tests/``. **The reason first written here was
false and the v2 rail caught it**: at this base ``tests/unit`` IS in
``pytest.ini``'s ``testpaths`` and validate.yml runs it explicitly,
so the S341 file was collected. The real reason for the move is
convention — script-facing tests live beside the scripts, in the
directory validate.yml and release.yml run by name — and the real
consequence is the one that matters: whichever of the two it sits
in, this file GATES CI, which is why v2 dropped the line pins.
Case 10 pins the S343 DATA cure: §2b row R3 is the only row whose
cell enumerates a LIST of destination formats, so one worked case
exercises only part of it while ROW-UNCOVERED stays silent —
coverage counts CASES. It is a claim about DESTINATIONS, not about
the discriminant: B1 decided the row by the artefact PRODUCED.

S343 v2 — the citation grammar, and two cases more
--------------------------------------------------
v1 shipped citations pinned to path+LINE+anchor and case 1 runs
against the SHIPPED tree, so any pack editing ABOVE a cited line in
one of 16 mutable files turned ``main`` RED. The PLAN-186 W1 routing
patch does exactly that (measured: 2 ANCHOR-STALE + 1 ANCHOR-DRIFT).
v2's grammar is (path, anchor) located by UNIQUENESS. Case 11 pins
the DATA (no shipped citation carries a line), case 12 pins the
ARCHITECTURE (shift every cited file by three lines: still rc 0) —
the refutation's own control, made permanent — and case 13 confines
case 12's writes, the only writes in this file.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

# S343: this file lives at `.claude/scripts/tests/`, which pytest.ini
# lists in `testpaths` and which BOTH validate.yml (script unit
# tests) and release.yml (tag gate) run by name. parents[3] is the
# checkout root from here.
REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402

_W5 = REPO_ROOT / ".claude" / "plans" / "PLAN-186" / "w5"
CHECKER = _W5 / "check-classifier-cases.py"
FIXTURE = _W5 / "classifier-cases.json"
DOC = REPO_ROOT / "docs" / "task-classifier-2b.md"
PLAN = (REPO_ROOT / ".claude" / "plans"
        / "PLAN-186-orchestrator-operating-model.md")


def _run(fixture: Optional[Path] = None,
         doc: Optional[Path] = None,
         root: Optional[Path] = None) -> Tuple[int, str, str]:
    """Run the oracle as a subprocess; return (rc, stdout, stderr).

    ``root`` is the tree the CITATIONS are resolved against. When it is not
    the checkout, the plan/doc/fixture are still the shipped ones (they are
    passed explicitly), so what varies between such a run and the default one
    is exactly the cited files — which is what case 12 measures.
    """
    cite_root = REPO_ROOT if root is None else root
    argv = [sys.executable, str(CHECKER), "--root", str(cite_root)]
    if root is not None:
        argv += ["--plan", str(PLAN)]
        if fixture is None:
            argv += ["--fixture", str(FIXTURE)]
        if doc is None:
            argv += ["--doc", str(DOC)]
    if fixture is not None:
        argv += ["--fixture", str(fixture)]
    if doc is not None:
        argv += ["--doc", str(doc)]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(argv, capture_output=True, text=True, env=env,
                          cwd=str(REPO_ROOT))
    return proc.returncode, proc.stdout, proc.stderr


def _detail(rc: int, out: str, err: str) -> str:
    return "rc=%d\n--- stdout ---\n%s\n--- stderr ---\n%s" % (rc, out, err)


def _confined_dst(root: Path, rel: str) -> Path:
    """``root/rel``, or AssertionError if ``rel`` would escape ``root``.

    A test that writes must confine its own destination. `Path.__truediv__`
    DISCARDS the left side when the right is absolute, and `..` walks out, so
    a citation path taken from the fixture — checked input, not trusted input
    — is validated before any directory is created (v2 rail [P2]).
    """
    parts = PurePosixPath(rel).parts
    if PurePosixPath(rel).is_absolute() or Path(rel).is_absolute():
        raise AssertionError("citation path %r is absolute; refusing to "
                             "build a write destination from it" % rel)
    if ".." in parts or ".." in Path(rel).parts:
        raise AssertionError("citation path %r carries a parent traversal; "
                             "refusing to build a write destination from it"
                             % rel)
    dst = root / PurePosixPath(rel)
    root_res = root.resolve()
    try:
        dst.resolve().relative_to(root_res)
    except ValueError:
        raise AssertionError("citation path %r resolves outside %s" % (rel, root))
    return dst


class TestClassifierCheckExitCodes(TestEnvContext):
    """The oracle's rc, for every outcome a caller can be handed."""

    def setUp(self) -> None:  # noqa: D102
        super().setUp()
        for label, path in (("oracle", CHECKER), ("fixture", FIXTURE),
                            ("doc", DOC)):
            # An assert, never a skip: this file pins the oracle's rc, so a
            # skip when the oracle is absent would be a false green of its own.
            self.assertTrue(path.is_file(),
                            "the %s is missing at %s" % (label, path))

    # -- case 1 -----------------------------------------------------------
    def test_consistent_tree_exits_0(self) -> None:
        """The shipped plan/doc/fixture agree, so the gate must succeed."""
        rc, out, err = _run()
        self.assertEqual(rc, 0,
                         "the shipped tree must be CONSISTENT\n%s"
                         % _detail(rc, out, err))

    # -- case 2 -----------------------------------------------------------
    def test_row_left_uncovered_exits_1(self) -> None:
        """A §2b row with no worked case is a PROBLEM, and a problem is rc 1.

        This is the exact control the S341 refutation ran, where the oracle
        printed the finding and exited 0. Here the assertion IS the rc.
        """
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases: List[dict] = list(data.get("cases") or [])
        worked: Dict[str, List[dict]] = {}
        for case in cases:
            if isinstance(case, dict) and not case.get("boundary"):
                worked.setdefault(str(case.get("row", "")), []).append(case)
        # v2 rail r2 [P2]: the victim used to be a row covered by EXACTLY
        # one worked case, so the day every row gains a second one — a
        # legitimate improvement, AC-14 asks for at least one — this test
        # would fail before reaching the checker. Any covered row will do if
        # ALL of its worked cases are dropped.
        victims = [row for row in sorted(worked) if worked[row]]
        self.assertTrue(
            victims,
            "no §2b row has a non-boundary worked case, so nothing can be "
            "uncovered — re-derive this mutation instead of asserting an rc "
            "the tree would return anyway")
        victim_row = victims[0]
        victim_ids = sorted(str(c.get("id", "")) for c in worked[victim_row])
        data["cases"] = [c for c in cases
                         if not (isinstance(c, dict)
                                 and str(c.get("id", "")) in victim_ids)]
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "classifier-cases.json"
            mutated.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")
            rc, out, err = _run(fixture=mutated)
        self.assertEqual(
            rc, 1,
            "dropping every worked case of %s (%s) must FAIL the gate, not "
            "merely be reported\n%s"
            % (victim_row, ", ".join(victim_ids), _detail(rc, out, err)))
        self.assertIn(
            "ROW-UNCOVERED", err,
            "rc 1 arrived for some reason other than the row we uncovered "
            "(%s) — a non-zero rc for the wrong reason is not evidence\n%s"
            % (victim_row, _detail(rc, out, err)))

    # -- case 3 -----------------------------------------------------------
    def test_missing_fixture_exits_2(self) -> None:
        """An input the gate cannot find is rc 2 — never 0, never 1."""
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "no-such-fixture.json"
            rc, out, err = _run(fixture=absent)
        self.assertEqual(rc, 2,
                         "a missing fixture must be fail-CLOSED usage (rc 2)\n%s"
                         % _detail(rc, out, err))

    # -- case 4 (CURE) -----------------------------------------------------
    def test_undecodable_doc_exits_2(self) -> None:
        """A present-but-undecodable doc is rc 2, not an unnamed traceback.

        Positive control: without the ``_read_text`` guard this raises
        UnicodeDecodeError out of ``run()`` and the process exits 1, which a
        caller cannot tell apart from a real finding.
        """
        with tempfile.TemporaryDirectory() as tmp:
            bad_doc = Path(tmp) / "task-classifier-2b.md"
            bad_doc.write_bytes(DOC.read_bytes() + b"\xff\xfe")
            self.assertTrue(bad_doc.is_file(),
                            "the undecodable input must still be a FILE, or "
                            "this degenerates into the missing-file case")
            rc, out, err = _run(doc=bad_doc)
        self.assertEqual(
            rc, 2,
            "an undecodable doc must be fail-CLOSED usage (rc 2), never an "
            "uncaught traceback (rc 1)\n%s" % _detail(rc, out, err))
        self.assertNotIn("Traceback", err,
                         "rc 2 must be a NAMED refusal, not a traceback\n%s"
                         % _detail(rc, out, err))

    # -- case 5 (CURE) -----------------------------------------------------
    def test_fixture_that_is_not_an_object_exits_2(self) -> None:
        """A JSON array where an object is required is rc 2, named.

        Positive control: without the ``isinstance(fixture, dict)`` guard the
        very next line is ``fixture.get("rows")`` and the process dies with
        AttributeError at rc 1.
        """
        with tempfile.TemporaryDirectory() as tmp:
            array = Path(tmp) / "classifier-cases.json"
            array.write_text("[]\n", encoding="utf-8")
            rc, out, err = _run(fixture=array)
        self.assertEqual(
            rc, 2,
            "a fixture that is not a JSON object must be fail-CLOSED usage "
            "(rc 2)\n%s" % _detail(rc, out, err))
        self.assertNotIn("Traceback", err,
                         "rc 2 must be a NAMED refusal, not a traceback\n%s"
                         % _detail(rc, out, err))

    # -- case 6 (CURE) -----------------------------------------------------
    def test_absolute_citation_path_exits_1(self) -> None:
        """An ABSOLUTE citation path is refused even when it points inside.

        Positive control, and the sharpest one here: before the grammar check,
        ``root / rel`` DISCARDS ``root`` when ``rel`` is absolute, so an
        absolute path naming a file inside this very checkout resolved fine,
        passed containment, matched its anchor, and the gate returned **0** —
        a false green that also lets a machine-specific path be committed into
        the fixture (the no-contamination rule).
        """
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        target = None
        for case in data.get("cases") or []:
            for cit in (case.get("citations") or []):
                if isinstance(cit, dict) and cit.get("path"):
                    cit["path"] = str(REPO_ROOT / str(cit["path"]))
                    target = cit["path"]
                    break
            if target is not None:
                break
        self.assertIsNotNone(target,
                             "no citation to absolutise — the fixture shape "
                             "changed and this control asserts nothing")
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "classifier-cases.json"
            mutated.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")
            rc, out, err = _run(fixture=mutated)
        self.assertEqual(
            rc, 1,
            "an absolute citation path must FAIL the gate even though it "
            "points inside the checkout\n%s" % _detail(rc, out, err))
        self.assertIn("CITE-ESCAPE", err,
                      "rc 1 arrived for some other reason than the absolute "
                      "path\n%s" % _detail(rc, out, err))

    # -- case 7 (CURE) -----------------------------------------------------
    def test_non_object_citation_is_named_not_a_traceback(self) -> None:
        """``"citations": [null]`` is a named finding, not AttributeError.

        Positive control: before the guard, the loop calls ``cit.get`` on the
        scalar and the process dies at rc 1 with no named code — unusable
        input that a caller cannot tell apart from a real inconsistency.
        """
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases = data.get("cases") or []
        self.assertTrue(cases, "the fixture has no cases to corrupt")
        cases[0]["citations"] = [None]
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "classifier-cases.json"
            mutated.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")
            rc, out, err = _run(fixture=mutated)
        self.assertEqual(rc, 1,
                         "a malformed citation is content, so rc 1\n%s"
                         % _detail(rc, out, err))
        self.assertNotIn("Traceback", err,
                         "the finding must be NAMED, not a traceback\n%s"
                         % _detail(rc, out, err))
        self.assertIn("CITE-MISSING", err,
                      "the named code for a malformed citation is missing\n%s"
                      % _detail(rc, out, err))

    # -- case 8 (S343 v2 CURE) ---------------------------------------------
    def test_line_pinned_citation_is_refused_by_name(self) -> None:
        """A citation carrying a ``line`` key is REFUSED, never tolerated.

        v1 of this pack pinned every citation to path+line+anchor, which made
        the shipped fixture — the one case 1 verifies against the SHIPPED tree
        — RED for any edit ABOVE a cited line in one of 16 mutable files. The
        PLAN-186 W1 routing patch does exactly that: measured on a worktree
        with W1 applied, v1's fixture returns 2 ANCHOR-STALE + 1 ANCHOR-DRIFT
        and this pytest file turns ``main`` red. v2's grammar is
        (path, anchor), located by UNIQUENESS; a stray ``line`` key is a named
        PROBLEM so the class cannot walk back one fixture edit at a time.

        Positive control: on the v1 oracle this same mutation is ACCEPTED
        (rc 0 when the pinned line is the real one) — that acceptance is what
        made the collision possible. Here it is rc 1 with CITE-LINE-PINNED.
        """
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        touched = False
        for case in data.get("cases") or []:
            for cit in (case.get("citations") or []):
                if isinstance(cit, dict) and isinstance(cit.get("path"), str):
                    cit["line"] = 1
                    touched = True
                    break
            if touched:
                break
        self.assertTrue(touched,
                        "no citation object was found to mutate — the fixture "
                        "shape changed and this control asserts nothing")
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "classifier-cases.json"
            mutated.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")
            rc, out, err = _run(fixture=mutated)
        self.assertEqual(rc, 1,
                         "a line-pinned citation must FAIL the gate\n%s"
                         % _detail(rc, out, err))
        self.assertIn(
            "CITE-LINE-PINNED", err,
            "a line pin must be refused BY NAME, not ignored and not reported "
            "as some other defect\n%s" % _detail(rc, out, err))

    # -- case 9 -----------------------------------------------------------
    def test_reported_problems_imply_a_failing_rc(self) -> None:
        """Whenever the oracle prints "N PROBLEM(S)", the rc is non-zero.

        The refuted build printed the count and returned 0. This binds the two
        halves together so a future edit cannot separate them again.
        """
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["cases"] = []
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "classifier-cases.json"
            mutated.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")
            rc, out, err = _run(fixture=mutated)
        self.assertIn("PROBLEM(S)", err,
                      "an empty case list must be REPORTED\n%s"
                      % _detail(rc, out, err))
        self.assertNotEqual(
            rc, 0,
            "the oracle printed PROBLEM(S) and returned success — this is "
            "exactly the S341 false green\n%s" % _detail(rc, out, err))


    # -- case 10 (S343 DATA cure) -----------------------------------
    def test_r3_worked_cases_exercise_distinct_destinations(self) -> None:
        """R3's cell enumerates destination formats; one case covers part.

        What this asserts, precisely: R3 carries at least TWO non-boundary
        worked cases, and the second one exercises a destination format the
        first does not — so the union of the formats cited across R3's worked
        cases is strictly larger than what any single case cites.

        What it does NOT assert: which row a task belongs to. B1 decided that
        by the artefact PRODUCED (both C3 and C8 produce a ``.py`` deriver),
        and this test does not re-open it (rail r1 [P2]). Destinations are
        read off the CITATIONS, never off a case id, so renaming a case
        cannot make it vacuous.

        Positive control: drop C8 from the shipped fixture and this test is
        RED while ``check-classifier-cases.py`` stays rc 0 — which is exactly
        why the data cure needs a pin the oracle cannot give it.
        """
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        worked = [c for c in (data.get("cases") or [])
                  if isinstance(c, dict) and str(c.get("row", "")) == "R3"
                  and c.get("boundary") is not True]
        self.assertGreaterEqual(
            len(worked), 2,
            "R3 carries %d non-boundary worked case(s); its cell enumerates a "
            "LIST of destination formats and one case exercises part of it"
            % len(worked))
        # v2 rail r2 [P2]: this used to read the suffix of EVERY citation, so
        # swapping C8's `.yaml` destination for any unique `.md` citation kept
        # the union wider and the test green while the CONFIG-format coverage
        # it claims to pin was gone. Formats are now read ONLY from citations
        # the fixture DECLARES to be destinations, and a case without one is a
        # named failure rather than an empty set that quietly passes.
        # v2 rail r4 [P2]: counting ANY destination suffix let a `.md`
        # destination widen the union, so the test passed while no second
        # CODE/CONFIG format was exercised — the very false green the cure
        # above was for. The admissible formats are DERIVED from §2b's own R3
        # cell (the extensions it enumerates in backticks), never recalled.
        cell = ""
        for row in (data.get("rows") or []):
            if isinstance(row, dict) and str(row.get("id")) == "R3":
                cell = str(row.get("artefact_cell", ""))
        cell_exts = {"." + m for m in re.findall(r"`\.(\w+)`", cell)}
        self.assertTrue(
            cell_exts,
            "§2b's R3 cell enumerates no `.ext` formats (%r); this test reads "
            "them from the cell, so it would assert nothing" % cell[:120])
        # `.yaml` is the on-disk spelling of the cell's `.yml`; the alias is
        # declared here rather than silently normalised away.
        aliases = {".yaml": ".yml"}
        per_case = []
        for case in worked:
            formats = set()
            for cit in (case.get("citations") or []):
                if (isinstance(cit, dict)
                        and isinstance(cit.get("path"), str)
                        and cit.get("role") == "destination"):
                    suffix = PurePosixPath(cit["path"]).suffix
                    suffix = aliases.get(suffix, suffix)
                    if suffix in cell_exts:
                        formats.add(suffix)
            cid = str(case.get("id"))
            self.assertTrue(
                formats,
                'R3 worked case %s declares no "role": "destination" citation '
                "whose format is one of §2b's R3 formats %s; a prose "
                "destination does not exercise the code/config cell"
                % (cid, sorted(cell_exts)))
            per_case.append((cid, formats))
        union = set()
        for _cid, formats in per_case:
            union |= formats
        widest = max(len(formats) for _cid, formats in per_case)
        self.assertGreater(
            len(union), widest,
            "R3's worked cases cite the destinations %s: every case exercises "
            "the same formats, so the second one pins nothing"
            % ", ".join("%s=%s" % (cid, sorted(f)) for cid, f in per_case))

    # -- case 11 (S343 v2 cure, in the DATA) -------------------------------
    def test_no_shipped_citation_carries_a_line_pin(self) -> None:
        """The shipped fixture uses the (path, anchor) grammar, everywhere.

        Case 8 proves the oracle REFUSES a line pin; this proves the shipped
        data has none, which is the half that actually keeps CI green. Read
        off the fixture, so it cannot rot into a statement about nothing.
        """
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        pinned = []
        n_cit = 0
        for case in data.get("cases") or []:
            for cit in (case.get("citations") or []):
                if isinstance(cit, dict):
                    n_cit += 1
                    if "line" in cit:
                        pinned.append((str(case.get("id")), cit.get("path")))
        self.assertGreaterEqual(
            n_cit, 2, "the fixture carries %d citation(s); this assertion "
                      "needs some to be about" % n_cit)
        self.assertEqual(
            pinned, [],
            "these citations still pin a line number: %s — a line pin rots "
            "on any edit above it and reddens this file for a fact that "
            "never moved" % pinned)

    # -- case 12 (S343 v2 cure, in the ARCHITECTURE) -----------------------
    def test_a_line_shift_in_every_cited_file_stays_green(self) -> None:
        """Shift EVERY cited file down by three lines: still rc 0.

        This is the refutation's own control, made permanent. On v1 it is RED
        (each citation reports ANCHOR-DRIFT, rc 1); here the anchors are
        located by uniqueness, so a line shift is invisible — which is what
        keeps this pytest file from reddening ``main`` when an unrelated pack
        edits a cited file. What still fails, by design, is DELETION of the
        anchored text (case 1 would catch it against the real tree).
        """
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cited = sorted({cit["path"]
                        for case in (data.get("cases") or [])
                        for cit in (case.get("citations") or [])
                        if isinstance(cit, dict)
                        and isinstance(cit.get("path"), str)})
        self.assertGreaterEqual(
            len(cited), 2,
            "only %d cited file(s) — this control would prove little" % len(cited))
        with tempfile.TemporaryDirectory() as tmp:
            shifted = Path(tmp) / "shifted-root"
            for rel in cited:
                src = REPO_ROOT / rel
                self.assertTrue(src.is_file(),
                                "cited file is missing from the checkout: %s"
                                % rel)
                # v2 rail [P2]: this is the only case here that WRITES, and
                # `shifted / PurePosixPath(rel)` DISCARDS `shifted` when rel
                # is absolute -- the write would land on the cited file
                # itself. The fixture is checked input, not trusted input
                # (case 6 exists precisely because an absolute path can
                # appear), so the destination is confined before it is used.
                dst = _confined_dst(shifted, rel)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text("\n\n\n" + src.read_text(encoding="utf-8"),
                               encoding="utf-8")
            rc, out, err = _run(root=shifted)
        self.assertEqual(
            rc, 0,
            "every cited file was shifted by three lines and nothing else "
            "changed; a citation grammar that reddens here is the class that "
            "collided with the W1 routing patch\n%s" % _detail(rc, out, err))
        self.assertIn("CONSISTENT", out,
                      "rc 0 without the CONSISTENT report is not evidence\n%s"
                      % _detail(rc, out, err))

    # -- case 13 (v2 rail [P2], the write-confinement control) -------------
    def test_the_shift_helper_refuses_an_escaping_citation_path(self) -> None:
        """The only WRITING case cannot be steered out of its tmp tree.

        Positive control, in two lines of Python that hold with or without
        this file: ``Path('/tmp/x') / PurePosixPath('/etc/passwd')`` is
        ``/etc/passwd`` — the left side is DISCARDED. So case 12, which reads
        its paths from the fixture, would have written over the cited file
        itself for an absolute citation (the very shape case 6 exists to
        catch). The helper refuses first; here is the proof it does.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            # the pre-cure behaviour, asserted so the control cannot rot
            self.assertEqual(str(root / PurePosixPath("/etc/passwd")),
                             "/etc/passwd",
                             "Path.__truediv__ no longer discards the left "
                             "side on an absolute right side — re-derive this "
                             "control before trusting the guard")
            for bad in ("/etc/passwd", "../outside.txt", "a/../../b"):
                with self.assertRaises(AssertionError):
                    _confined_dst(root, bad)
            good = _confined_dst(root, "docs/x.md")
            self.assertEqual(good, root / "docs" / "x.md")

    # -- case 14 (land rail r2 [P2], the rc-contract hole) -----------------
    def test_deeply_nested_fixture_exits_2(self) -> None:
        """Valid JSON nested past the decoder limit is rc 2, named.

        Positive control, measured on the pre-cure bytes: a fixture of 2000
        nested arrays makes ``json.loads`` raise ``RecursionError``, which is
        not a ``ValueError`` and so walked straight out of ``run()`` as a
        traceback with rc 1 -- the code this file reserves for a NAMED
        inconsistency. The assertion below is on the PROCESS exit status and
        on the ABSENCE of a traceback, because a message alone cannot
        constrain either.
        """
        depth = 2000
        with tempfile.TemporaryDirectory() as tmp:
            deep = Path(tmp) / "classifier-cases.json"
            deep.write_text("[" * depth + "]" * depth, encoding="utf-8")
            rc, out, err = _run(fixture=deep)
        self.assertEqual(
            rc, 2,
            "a fixture the JSON decoder cannot walk must be fail-CLOSED usage "
            "(rc 2), never an uncaught traceback (rc 1)\n%s"
            % _detail(rc, out, err))
        self.assertNotIn("Traceback", err,
                         "rc 2 must be a NAMED refusal, not a traceback\n%s"
                         % _detail(rc, out, err))


if __name__ == "__main__":
    unittest.main()
