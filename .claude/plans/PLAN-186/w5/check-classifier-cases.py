#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-classifier-cases.py — the AC-14 consistency oracle (PLAN-186 W5-US2).

WHAT IT ASSERTS, and why each assertion is not vacuous
------------------------------------------------------
Three artefacts have to agree, and each is authored by a different hand:

  the PLAN     ``.claude/plans/PLAN-186-orchestrator-operating-model.md`` §2b
               — the seven-row matrix. THE NORM.
  the DOC      ``docs/task-classifier-2b.md`` — the decision procedure, its
               ``procedure-map`` block, the frozen copy of the rows and the
               case index.
  the FIXTURE  ``.claude/plans/PLAN-186/w5/classifier-cases.json`` — the cases,
               their question paths and their citations.

A classifier whose three copies drift apart is exactly this repo's dominant
defect: a green instrument whose question went stale. So every check below is
a binding between two artefacts, or between an artefact and DISK — never a
statement the fixture makes about itself:

  2B-DRIFT           fixture rows and DOC rows vs the §2b cells parsed out of
                     the plan (whitespace-normalised). If §2b changes, RED.
  PROCEDURE-*        the ``procedure-map`` block is proved to be a TOTAL
                     partition: every question before the last has exactly one
                     terminal branch, the last has two, and the terminals are
                     exactly the §2b rows — each reachable, none twice.
  ROW-UNCOVERED      every §2b row has at least one non-boundary case.
  BOUNDARY-*         at least one case is marked boundary, names exactly two
                     candidate rows (its own among them) and carries a reason.
  PROCEDURE-MISMATCH a case's ``path_taken`` is a monotone Q0..Qk chain whose
                     non-final answers are the CONTINUE branch and whose final
                     answer maps, in the DOC's own map, to the case's row.
  DOC-UNBOUND        every fixture case id appears in the doc's case index with
                     the same row and the same terminal token.
  DOC-DUP            the doc declares a frozen row or a case id twice — a dict
                     would keep the last silently and bind against it.
  CITE-ESCAPE /      every citation resolves on disk INSIDE the checkout (an
  CITE-MISSING /     absolute or ../ path is refused before anything is read),
  CITE-LINE-PINNED / the file exists, and the declared anchor occurs on EXACTLY
  WEAK-ANCHOR /      ONE line of it. A citation is (path, anchor) and NEVER
  ANCHOR-STALE       carries a line number: a line pin is invalidated by any
                     edit ABOVE it, and this fixture is verified by a pytest
                     case that pytest.ini collects, so an unrelated pack that
                     inserts a line into a cited file turns `main` RED for a
                     fact that never moved (measured on the PLAN-186 W1
                     routing patch: 1 ANCHOR-DRIFT + 2 ANCHOR-STALE, S343).
                     A surviving `line` key is REFUSED by name, not ignored,
                     or the class walks back one fixture edit at a time.
                     Uniqueness is both the location proof and the repair
                     instruction (`grep -n` on the anchor prints the line).
                     An anchor shorter than MIN_ANCHOR_CHARS or matching more
                     than one line is WEAK — satisfiable by accident; an
                     anchor nowhere in the file is STALE, a cited fact that
                     died, which is the RED this gate is FOR.

DECLARED FALSE NEGATIVES (see docs/task-classifier-2b.md §6)
  * no CI step invokes this file DIRECTLY — that would edit ``.github/**``, a
    signed ceremony surface. It is enforced INDIRECTLY and the difference
    matters: ``.claude/scripts/tests/test_ac14_classifier_check_rc.py`` runs
    the oracle against the checked-out tree, and that directory is run by
    ``.github/workflows/validate.yml`` (the "script unit tests" steps) and by
    ``.github/workflows/release.yml`` (the tag gate). So a citation whose
    anchored text DIES turns CI red. The v2 grammar is what makes that
    tolerable: a line shift cannot do it, only the loss of the cited fact;
  * a live citation is not a live argument: the anchor can survive while the
    reasoning rots;
  * R2-vs-R4 misclassification is cost-neutral (same model, same effort), so
    no assertion here can punish it;
  * THE PROSE IS NOT BOUND TO THE MAP (rail round 2 [P2], declared not cured).
    A reader routes from the human Q0..Q5 sections of the doc; this file
    parses only the ``procedure-map`` fence, the frozen rows and the case
    index. Change a terminal in the prose while the fence stays put and the
    gate still reports CONSISTENT. Curing it means giving the prose a
    machine-parseable shape and comparing edge by edge — a re-architecture of
    the doc, not of the exit code, so it is DECLARED here and left open
    rather than half-done. Until then the fence, not the prose, is the norm
    this gate defends.

Usage
    python3 .claude/plans/PLAN-186/w5/check-classifier-cases.py [--root DIR]
        [--fixture PATH] [--doc PATH] [--plan PATH] [--list-cases]

THE EXIT CODE IS THE CONTRACT (S341 refutation)
  0  consistent — and ONLY then.
  1  at least one named inconsistency; every one of them is printed. A gate
     that prints a PROBLEM and returns success is a false green: a CI step,
     ``validate-governance.sh`` and a land script all read ``$?``, never the
     report.
  2  the gate could not READ its own inputs — root not derivable, or the
     plan/doc/fixture missing, undecodable or not a JSON object. Fail-CLOSED
     on input (CLAUDE.md §4), and never an uncaught traceback, whose rc 1
     would be indistinguishable from a real finding.

The rc is PINNED by ``.claude/scripts/tests/test_ac14_classifier_check_rc.py``,
which asserts the exit code of a real subprocess for all three outcomes —
prose in this docstring cannot constrain what ``main`` returns. That
directory is in ``pytest.ini``'s ``testpaths`` AND is run explicitly by
``validate.yml`` and by ``release.yml``'s tag gate, so the assertions there
are enforced, not decorative.

Stdlib-only, Python >= 3.9, no runtime PEP 604.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

REL_PLAN = ".claude/plans/PLAN-186-orchestrator-operating-model.md"
REL_DOC = "docs/task-classifier-2b.md"
REL_FIXTURE = ".claude/plans/PLAN-186/w5/classifier-cases.json"

SECTION_2B = "## 2b."
MAP_FENCE_OPEN = "```procedure-map"
FENCE_CLOSE = "```"
TOKEN_RE = re.compile(r"^Q(\d+)=(yes|no)$")
ROW_ID_RE = re.compile(r"^R\d+$")
MIN_REASON_CHARS = 40
#: The fixture declares `"schema"`; this oracle reads exactly this
#: version and refuses any other, so a future format cannot be read
#: under v1 assumptions (rail r3 [P2]).
SCHEMA_SUPPORTED = 1
#: An anchor shorter than this, or one that matches more than one line of
#: the cited file, asserts nothing: the substring test would be satisfiable
#: by accident, and — since S343 v2 dropped the line pin — an anchor
#: matching two lines would leave the citation with NO location at all.
#: Measured at base 76578f33 (S343 v2): all 20 shipped anchors are
#: unique in their file and >= 9 chars (the shortest is C3's `SITES = [`),
#: both at that base and with the PLAN-186 W1 routing patch applied — so
#: this bound is GREEN on the shipped fixture and only refuses NEW weak
#: anchors.
MIN_ANCHOR_CHARS = 8
#: ...and at least this many of the anchor's characters must be NON-WHITESPACE.
#: v2 rail r2 [P2]: `len(anchor)` counts spaces, so eight blanks passed the
#: bound and, where that exact indentation happened to be unique in a file, the
#: citation verified while identifying no fact at all. Measured over the 20
#: shipped anchors, the smallest non-whitespace content is 7 characters (C3's
#: `SITES = [`), so this floor sits one below the shipped minimum: GREEN here,
#: and padding-as-anchor is refused.
MIN_ANCHOR_SIGNIFICANT = 6
#: Optional per-citation role, a CLOSED set. A citation of an R3 case is either
#: the SUBJECT of the derivation or one of its DESTINATIONS, and the
#: destination FORMAT is what the R3 coverage test reads (v2 rail r2 [P2]: it
#: used to read every citation's suffix, so an unrelated `.md` citation
#: satisfied a test that claims to pin CONFIG-format coverage). An unknown role
#: is refused, never ignored: a typo would silently drop the citation from that
#: test and leave it green over nothing.
CITATION_ROLES = ("subject", "destination")


class Usage(Exception):
    pass


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _cells(line: str) -> List[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_sep(cell: str) -> bool:
    return bool(re.match(r"^:?-{2,}:?$", cell))


def _no_dupe_pairs(pairs):
    """`object_pairs_hook` that REFUSES a repeated key.

    rail r3 [P2]: `json.loads` keeps the LAST value silently, so a
    hand-edited fixture carrying both `"row": "BROKEN"` and
    `"row": "R1"` validated as if the first line were not there.
    An ambiguous fixture is unusable input, not a finding.
    """
    seen = set()
    for key, _value in pairs:
        if key in seen:
            raise Usage("fixture: duplicate JSON key %r — the file "
                        "is ambiguous and json would keep only the "
                        "last value" % key)
        seen.add(key)
    return dict(pairs)


def _read_text(label: str, path: Path) -> str:
    """UTF-8 text, or `Usage` — never an uncaught read error.

    Fail-CLOSED on input (CLAUDE.md §4). An input this gate cannot READ is
    rc 2 with a named reason; letting OSError/UnicodeDecodeError escape would
    exit 1, which a caller cannot tell apart from a real finding.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Usage("%s is unreadable (%s): %s"
                    % (label, type(exc).__name__, path))


def find_root(start: Path) -> Optional[Path]:
    """Walk up from `start` to the checkout that owns this file.

    Deliberately structural (a directory with both ``.claude/`` and
    ``PROTOCOL.md``) so no absolute path is ever baked into the repo.
    """
    for cand in [start] + list(start.parents):
        if (cand / ".claude").is_dir() and (cand / "PROTOCOL.md").is_file():
            return cand
    return None


def parse_2b_rows(plan_text: str) -> List[Tuple[str, str, str]]:
    """The §2b matrix, as ordered (artefact, model, effort) normalised cells."""
    lines = plan_text.splitlines()
    start = None
    # rail r3 [P2]: binding the FIRST match let a plan with two §2b
    # sections (a merge, a partial rewrite) verify against one matrix
    # while the other was live. An ambiguous norm is rc 2.
    starts = [i for i, line in enumerate(lines)
              if line.startswith(SECTION_2B)]
    if len(starts) > 1:
        raise Usage("plan: %d sections start with %r — the normative "
                    "matrix must be unique (lines %s)"
                    % (len(starts), SECTION_2B,
                       ", ".join(str(i + 1) for i in starts)))
    start = starts[0] if starts else None
    if start is None:
        raise Usage("plan: section %r not found" % SECTION_2B)
    rows: List[Tuple[str, str, str]] = []
    seen_header = False
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            continue
        cells = _cells(stripped)
        if cells and all(_is_sep(c) for c in cells):
            continue
        if len(cells) != 3:
            raise Usage("plan §2b: a table row tokenizes to %d cells, "
                        "expected 3 — the normative table cannot be read "
                        "and a skipped row would be silent 2B-DRIFT: %r"
                        % (len(cells), stripped[:90]))
        if not seen_header:
            seen_header = True
            continue
        rows.append((_norm(cells[0]), _norm(cells[1]), _norm(cells[2])))
    if not rows:
        raise Usage("plan: §2b table parsed to zero rows")
    return rows


def parse_procedure_map(doc_text: str) -> List[Tuple[str, str]]:
    """The doc's ``procedure-map`` fenced block, as ordered (token, row)."""
    lines = doc_text.splitlines()
    openers = [i for i, ln in enumerate(lines)
               if ln.strip() == MAP_FENCE_OPEN]
    if len(openers) > 1:
        raise Usage("doc: %d %r blocks — the machine-readable norm "
                    "must be unique"
                    % (len(openers), MAP_FENCE_OPEN))
    inside = False
    closed = False
    pairs: List[Tuple[str, str]] = []
    for line in lines:
        if not inside:
            if line.strip() == MAP_FENCE_OPEN:
                inside = True
            continue
        if line.strip() == FENCE_CLOSE:
            closed = True
            break
        if line.strip().startswith(FENCE_CLOSE):
            raise Usage("doc procedure-map: closed by %r, which is "
                        "not a closing fence — the rest of the "
                        "document stays inside the block"
                        % line.strip()[:40])
        stripped = line.strip()
        if not stripped:
            continue
        if "->" not in stripped:
            raise Usage("doc procedure-map: line without '->': %r" % stripped)
        left, right = stripped.split("->", 1)
        pairs.append((left.strip(), right.strip()))
    if not inside:
        raise Usage("doc: fenced block %r not found" % MAP_FENCE_OPEN)
    if not closed:
        raise Usage("doc procedure-map: the block is never closed — the "
                    "rest of the document is inside the fence")
    if not pairs:
        raise Usage("doc: procedure-map is empty")
    return pairs


def parse_doc_rows(doc_text: str):
    """The doc's frozen copy of §2b: (id -> cells, duplicate ids).

    Duplicates are RETURNED, not overwritten: a dict silently keeps the last
    definition, so a doc carrying two R3 rows would bind against whichever came
    second and read as consistent (rail round 1 [P2]).
    """
    out: Dict[str, Tuple[str, str, str]] = {}
    dupes: List[str] = []
    for line in doc_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _cells(stripped)
        if len(cells) != 4 or not ROW_ID_RE.match(cells[0]):
            continue
        if cells[0] in out:
            dupes.append(cells[0])
        out[cells[0]] = (_norm(cells[1]), _norm(cells[2]), _norm(cells[3]))
    return out, sorted(set(dupes))


def parse_doc_case_index(doc_text: str):
    """The doc's case index: (id -> (row, terminal token), duplicate ids)."""
    out: Dict[str, Tuple[str, str]] = {}
    dupes: List[str] = []
    for line in doc_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _cells(stripped)
        if len(cells) != 4 or not ROW_ID_RE.match(cells[1]):
            continue
        if ROW_ID_RE.match(cells[0]) or not TOKEN_RE.match(cells[2]):
            continue
        if cells[0] in out:
            dupes.append(cells[0])
        out[cells[0]] = (cells[1], cells[2])
    return out, sorted(set(dupes))


def check_procedure(pairs: List[Tuple[str, str]],
                    row_ids: List[str]) -> List[Tuple[str, str]]:
    """Prove the published procedure is a total partition over the rows."""
    problems: List[Tuple[str, str]] = []
    by_q: Dict[int, Dict[str, str]] = {}
    for token, row in pairs:
        m = TOKEN_RE.match(token)
        if m is None:
            problems.append(("PROCEDURE-TOKEN",
                             "procedure-map: %r is not Q<n>=yes|no" % token))
            continue
        if not ROW_ID_RE.match(row):
            problems.append(("PROCEDURE-ROW",
                             "procedure-map: %r maps to %r, not a row id"
                             % (token, row)))
            continue
        idx, ans = int(m.group(1)), m.group(2)
        slot = by_q.setdefault(idx, {})
        if ans in slot:
            problems.append(("PROCEDURE-DUP",
                             "procedure-map: %r declared twice" % token))
        slot[ans] = row
    if problems:
        return problems
    qs = sorted(by_q)
    if qs != list(range(len(qs))):
        problems.append(("PROCEDURE-GAP",
                         "procedure-map: questions are %s, expected a "
                         "contiguous Q0..Q%d chain" % (qs, len(qs) - 1)))
        return problems
    last = qs[-1]
    for idx in qs[:-1]:
        if len(by_q[idx]) != 1:
            problems.append((
                "PROCEDURE-BRANCH",
                "procedure-map: Q%d has %d terminal branch(es) (%s); every "
                "question but the last must have exactly one, or the walk "
                "cannot continue" % (idx, len(by_q[idx]),
                                     ",".join(sorted(by_q[idx])))))
    if sorted(by_q[last]) != ["no", "yes"]:
        problems.append((
            "PROCEDURE-NOT-TOTAL",
            "procedure-map: the last question Q%d has branch(es) %s; it must "
            "have BOTH, otherwise some task reaches no row"
            % (last, ",".join(sorted(by_q[last])) or "none")))
    terminals: List[str] = []
    for idx in qs:
        for ans in sorted(by_q[idx]):
            terminals.append(by_q[idx][ans])
    dupes = sorted({r for r in terminals if terminals.count(r) > 1})
    if dupes:
        problems.append(("PROCEDURE-AMBIGUOUS",
                         "procedure-map: row(s) %s reachable by more than one "
                         "terminal" % ",".join(dupes)))
    missing = [r for r in row_ids if r not in terminals]
    extra = sorted(set(terminals) - set(row_ids))
    if missing:
        problems.append(("PROCEDURE-UNREACHABLE",
                         "procedure-map: §2b row(s) %s have no terminal"
                         % ",".join(missing)))
    if extra:
        problems.append(("PROCEDURE-ROW",
                         "procedure-map: terminal row(s) %s are not in §2b"
                         % ",".join(extra)))
    return problems


def check_path_taken(case_id: str, row: str, path_taken: List[str],
                     terminal: Dict[str, str]) -> List[Tuple[str, str]]:
    problems: List[Tuple[str, str]] = []
    if not path_taken:
        return [("PROCEDURE-MISMATCH", "%s: path_taken is empty" % case_id)]
    for i, token in enumerate(path_taken):
        m = TOKEN_RE.match(token)
        if m is None:
            problems.append(("PROCEDURE-MISMATCH",
                             "%s: %r is not Q<n>=yes|no" % (case_id, token)))
            return problems
        if int(m.group(1)) != i:
            problems.append(("PROCEDURE-MISMATCH",
                             "%s: step %d is %r — the walk must answer the "
                             "questions in order from Q0" % (case_id, i, token)))
            return problems
        is_last = (i == len(path_taken) - 1)
        if not is_last and token in terminal:
            problems.append(("PROCEDURE-MISMATCH",
                             "%s: %r is a TERMINAL answer (-> %s) but the path "
                             "continues" % (case_id, token, terminal[token])))
        if is_last:
            if token not in terminal:
                problems.append(("PROCEDURE-MISMATCH",
                                 "%s: last answer %r is not terminal — the walk "
                                 "never lands" % (case_id, token)))
            elif terminal[token] != row:
                problems.append(("PROCEDURE-MISMATCH",
                                 "%s: %r lands in %s, but the case claims %s"
                                 % (case_id, token, terminal[token], row)))
    return problems


def check_citations(root: Path, case_id: str,
                    citations: List[Dict[str, object]]) -> List[Tuple[str, str]]:
    problems: List[Tuple[str, str]] = []
    if not citations:
        return [("CITE-MISSING", "%s: no citation" % case_id)]
    for cit in citations:
        if not isinstance(cit, dict):
            problems.append(("CITE-MISSING",
                             "%s: a citation entry is a %s, not an object"
                             % (case_id, type(cit).__name__)))
            continue
        raw_path = cit.get("path")
        raw_anchor = cit.get("anchor")
        # S343 v2, the CI-collision cure: a citation is (path, anchor), never
        # (path, line, anchor). A `line` key is REFUSED by name rather than
        # ignored -- ignoring it would let the rot class back in one fixture
        # edit at a time, and this file is pinned by a pytest case that runs
        # against the SHIPPED tree. (It subsumes the rail-r3 lesson it
        # replaces: `isinstance(True, int)` is True in Python, so a JSON
        # boolean used to sail through as line 1 and the gate reported
        # CONSISTENT. The key is now refused WHATEVER its type.)
        if "line" in cit:
            problems.append(("CITE-LINE-PINNED",
                             "%s: citation carries a 'line' key (%r); a "
                             "citation is (path, anchor) and locates by "
                             "UNIQUE anchor -- a line pin rots on any edit "
                             "above it. Drop the key."
                             % (case_id, cit.get("line"))))
            continue
        # `str()` used to wave malformed input through (rail round 3 [P2]): it
        # turns 123 or None into a "path".
        if (not isinstance(raw_path, str) or not raw_path
                or not isinstance(raw_anchor, str) or not raw_anchor):
            problems.append(("CITE-MISSING",
                             "%s: citation needs path (str) and anchor (str); "
                             "got %r" % (case_id, cit)))
            continue
        rel = raw_path
        anchor = raw_anchor
        # A declared role must be one of the CLOSED set; an unknown value is a
        # named PROBLEM rather than a citation quietly excluded from the R3
        # destination-format test (v2 rail r2 [P2]).
        raw_role = cit.get("role")
        if raw_role is not None and raw_role not in CITATION_ROLES:
            problems.append(("CITE-ROLE",
                             "%s: citation role %r is not one of %s; an "
                             "unrecognised role reads as ABSENT downstream, "
                             "which is a green over nothing"
                             % (case_id, raw_role, list(CITATION_ROLES))))
            continue
        # Containment BEFORE existence (rail round 1 [P2]): an absolute or
        # `../` relpath resolves outside the checkout and would then pass every
        # line and anchor check against a machine-specific file. resolve() on
        # both sides also catches an escape through a symlinked ancestor.
        # `root / rel` DISCARDS root when rel is absolute, so an absolute
        # path pointing INSIDE the checkout passes the containment test below
        # and the citation verifies -- on one machine only. That is a false
        # GREEN plus a contamination vector (a personal absolute path
        # committed into the fixture), so the grammar is refused first, before
        # any path arithmetic (rail round 1 [P2]).
        if PurePosixPath(rel).is_absolute() or Path(rel).is_absolute():
            problems.append(("CITE-ESCAPE",
                             "%s: %r is an ABSOLUTE path; a citation must be "
                             "repo-relative or it names a machine, not a repo"
                             % (case_id, rel)))
            continue
        if ".." in PurePosixPath(rel).parts or ".." in Path(rel).parts:
            problems.append(("CITE-ESCAPE",
                             "%s: %r carries a parent-traversal component; a "
                             "citation must be repo-relative without it"
                             % (case_id, rel)))
            continue
        target = root / rel
        try:
            resolved = target.resolve()
            root_resolved = root.resolve()
            resolved.relative_to(root_resolved)
        # v2 rail r4 [P2]: `Path.resolve()` raises RuntimeError on a symlink
        # LOOP (Python 3.9), which is neither ValueError nor OSError — it
        # escaped `main()` as an unnamed traceback with rc 1, i.e. a finding
        # and a crash became indistinguishable, which is the exact contract
        # the rc docstring makes. A cited path the filesystem cannot resolve
        # is a citation problem, and it is now NAMED.
        except (ValueError, OSError, RuntimeError):
            problems.append(("CITE-ESCAPE",
                             "%s: %r does not resolve INSIDE the checkout; a "
                             "citation must be a repo-relative path"
                             % (case_id, rel)))
            continue
        if not target.is_file():
            problems.append(("CITE-MISSING",
                             "%s: %s does not exist under the root" % (case_id, rel)))
            continue
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(("CITE-MISSING",
                             "%s: %s exists but cannot be read (%s)"
                             % (case_id, rel, type(exc).__name__)))
            continue
        found = [i + 1 for i, line in enumerate(lines) if anchor in line]
        significant = len("".join(anchor.split()))
        if (len(anchor) < MIN_ANCHOR_CHARS
                or significant < MIN_ANCHOR_SIGNIFICANT
                or len(found) > 1):
            problems.append((
                "WEAK-ANCHOR",
                "%s: %s anchor %r is %d char(s) (%d non-whitespace) and "
                "matches %d line(s); an anchor must be >= %d chars, carry "
                ">= %d non-whitespace characters and match EXACTLY ONE line, "
                "or it verifies nothing and the citation cannot be located"
                % (case_id, rel, anchor, len(anchor), significant, len(found),
                   MIN_ANCHOR_CHARS, MIN_ANCHOR_SIGNIFICANT)))
            continue
        if not found:
            problems.append(("ANCHOR-STALE",
                             "%s: %s — anchor %r is nowhere in the file; the "
                             "cited fact moved or died"
                             % (case_id, rel, anchor)))
    return problems


def run(root: Path, plan_path: Path, doc_path: Path,
        fixture_path: Path, list_cases: bool) -> int:
    for label, path in (("plan", plan_path), ("doc", doc_path),
                        ("fixture", fixture_path)):
        if not path.is_file():
            raise Usage("%s not found: %s" % (label, path))
    plan_rows = parse_2b_rows(_read_text("plan", plan_path))
    doc_text = _read_text("doc", doc_path)
    doc_rows, doc_row_dupes = parse_doc_rows(doc_text)
    doc_index, doc_case_dupes = parse_doc_case_index(doc_text)
    pairs = parse_procedure_map(doc_text)
    try:
        fixture = json.loads(_read_text("fixture", fixture_path),
                             object_pairs_hook=_no_dupe_pairs)
    # land rail r2 [P2]: `json.loads` raises RecursionError -- which is NOT a
    # ValueError -- on a document that is syntactically VALID but nested deeper
    # than the decoder's recursion limit (measured: 2000 nested arrays under
    # CPython 3.9). It escaped `run()` as an uncaught traceback at rc 1, the
    # code the contract above reserves for a NAMED finding, so a decoder crash
    # and a real inconsistency became indistinguishable. Same class as the
    # symlink-loop RuntimeError cured in v2 rail r4: an input this gate cannot
    # DECODE is rc 2, and it says which exception said so.
    except (ValueError, RecursionError) as exc:
        raise Usage("fixture is not decodable as JSON (%s): %s"
                    % (type(exc).__name__, exc))
    if not isinstance(fixture, dict):
        raise Usage("fixture must be a JSON object, got %s"
                    % type(fixture).__name__)
    # rail r3 [P2]: the fixture DECLARES a schema and nothing read it,
    # so a v2 file would have been interpreted under v1 assumptions.
    # v2 rail [P2]: `!=` alone is not a version check in Python -- `True == 1`
    # and `1.0 == 1`, so a fixture declaring `"schema": true` was READ as
    # schema 1 and the gate exited 0. This is the same bool-is-an-int class
    # the citation grammar hit; the type is checked BEFORE the value, and
    # bool is excluded because it SUBCLASSES int.
    _schema = fixture.get("schema")
    if type(_schema) is not int or _schema != SCHEMA_SUPPORTED:
        raise Usage("fixture schema is %r (%s); this oracle reads the "
                    "INTEGER schema %r only — a different version, or a "
                    "value that merely compares equal to it, must not be "
                    "read under v%d assumptions"
                    % (_schema, type(_schema).__name__, SCHEMA_SUPPORTED,
                       SCHEMA_SUPPORTED))

    problems: List[Tuple[str, str]] = []
    fix_rows = fixture.get("rows")
    cases = fixture.get("cases")
    if not isinstance(fix_rows, list) or not isinstance(cases, list):
        raise Usage("fixture must carry a 'rows' list and a 'cases' list")

    # ---- rows: plan vs fixture vs doc ---------------------------------
    if len(fix_rows) != len(plan_rows):
        problems.append(("2B-DRIFT",
                         "fixture declares %d rows, §2b has %d"
                         % (len(fix_rows), len(plan_rows))))
    row_ids: List[str] = []
    for i, declared in enumerate(fix_rows):
        if not isinstance(declared, dict):
            problems.append(("2B-DRIFT",
                             "fixture row %d is a %s, not an object"
                             % (i, type(declared).__name__)))
            continue
        rid = str(declared.get("id", "?"))
        row_ids.append(rid)
        expect_id = "R%d" % (i + 1)
        if rid != expect_id:
            problems.append(("2B-DRIFT",
                             "fixture row %d has id %r, expected %r (row ids "
                             "are the §2b table order)" % (i, rid, expect_id)))
        if i >= len(plan_rows):
            continue
        got = (_norm(str(declared.get("artefact_cell", ""))),
               _norm(str(declared.get("model_cell", ""))),
               _norm(str(declared.get("effort_cell", ""))))
        for field, g, p in zip(("artefact_cell", "model_cell", "effort_cell"),
                               got, plan_rows[i]):
            if g != p:
                problems.append(("2B-DRIFT",
                                 "%s.%s\n      fixture: %s\n      §2b    : %s"
                                 % (rid, field, g, p)))
        if rid in doc_rows:
            for field, d, p in zip(("artefact_cell", "model_cell", "effort_cell"),
                                   doc_rows[rid], plan_rows[i]):
                if d != p:
                    problems.append(("2B-DRIFT",
                                     "doc %s.%s\n      doc : %s\n      §2b : %s"
                                     % (rid, field, d, p)))
        else:
            problems.append(("2B-DRIFT",
                             "doc has no frozen row for %s" % rid))

    # ---- the procedure itself -----------------------------------------
    problems.extend(check_procedure(pairs, row_ids))
    terminal = dict(pairs)

    # ---- cases ---------------------------------------------------------
    seen_ids: Dict[str, int] = {}
    covered: Dict[str, int] = {r: 0 for r in row_ids}
    boundary_count = 0
    for case in cases:
        if not isinstance(case, dict):
            problems.append(("CASE-SHAPE",
                             "a case entry is a %s, not an object"
                             % type(case).__name__))
            continue
        # The case fields are TYPE-checked before they are used for
        # anything: coercion here is fail-OPEN. bool("false") is
        # True, bool(None) is False and let a malformed case COUNT as
        # coverage, and str(None) == "None" passed the non-empty
        # test — all three reachable with rc 0 (rail r1 [P2]).
        raw_id = case.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            problems.append(("CASE-SHAPE",
                             "a case id is %r (%s); it must be a "
                             "non-empty string"
                             % (raw_id, type(raw_id).__name__)))
        cid = raw_id if isinstance(raw_id, str) else "?"
        seen_ids[cid] = seen_ids.get(cid, 0) + 1
        raw_row = case.get("row")
        if not isinstance(raw_row, str):
            problems.append(("CASE-SHAPE",
                             "%s: row is %r (%s); it must be a string"
                             % (cid, raw_row, type(raw_row).__name__)))
        row = raw_row if isinstance(raw_row, str) else "?"
        # v2 rail r3 [P2]: `.get("boundary", False)` made a MISSING flag
        # mean "worked case", so a boundary case that loses the key is
        # counted as row coverage and ROW-UNCOVERED goes quiet — measured:
        # drop C1 and unflag B2 and the pre-cure oracle reports R1=1,
        # CONSISTENT, rc 0. The field is now REQUIRED.
        has_boundary = "boundary" in case
        if not has_boundary:
            problems.append(("CASE-SHAPE",
                             "%s: no 'boundary' field; the flag decides "
                             "whether this case COUNTS as row coverage, so "
                             "it must be declared, not defaulted" % cid))
        raw_boundary = case.get("boundary", False)
        if not isinstance(raw_boundary, bool):
            problems.append(("CASE-SHAPE",
                             "%s: boundary is %r (%s); it must be a "
                             "JSON boolean — anything else silently "
                             "decides whether this case counts as "
                             "coverage"
                             % (cid, raw_boundary,
                                type(raw_boundary).__name__)))
        is_boundary = raw_boundary is True
        if row not in covered:
            problems.append(("CASE-SHAPE",
                             "%s: row %r is not a §2b row id" % (cid, row)))
        elif (has_boundary and not is_boundary
              and isinstance(raw_boundary, bool)):
            covered[row] += 1
        for field in ("task", "why"):
            value = case.get(field)
            if not isinstance(value, str) or not value.strip():
                problems.append((
                    "CASE-SHAPE",
                    "%s: %s is %s; it must be a non-empty string"
                    % (cid, field,
                       "empty" if isinstance(value, str)
                       else "a %s" % type(value).__name__)))
        path_taken = case.get("path_taken")
        if not isinstance(path_taken, list):
            problems.append(("CASE-SHAPE", "%s: path_taken must be a list" % cid))
        else:
            problems.extend(check_path_taken(cid, row, [str(t) for t in path_taken],
                                             terminal))
            if path_taken:
                last = str(path_taken[-1])
                if cid in doc_index:
                    doc_row, doc_term = doc_index[cid]
                    if doc_row != row or doc_term != last:
                        problems.append((
                            "DOC-UNBOUND",
                            "%s: doc index says (%s, %s), fixture says (%s, %s)"
                            % (cid, doc_row, doc_term, row, last)))
                else:
                    problems.append(("DOC-UNBOUND",
                                     "%s: no row in the doc's case index" % cid))
        citations = case.get("citations")
        if not isinstance(citations, list):
            problems.append(("CITE-MISSING", "%s: citations must be a list" % cid))
        else:
            problems.extend(check_citations(root, cid, citations))
        if is_boundary:
            boundary_count += 1
            between = case.get("between")
            # rail r3 [P2]: `str()` on a 50-digit integer produced 50
            # characters and satisfied MIN_REASON_CHARS — a decided
            # boundary with no argument, reported CONSISTENT.
            raw_reason = case.get("reason", "")
            if not isinstance(raw_reason, str):
                problems.append(("BOUNDARY-REASON",
                                 "%s: reason is a %s; a decided "
                                 "boundary carries a written argument, "
                                 "not a value that stringifies to one"
                                 % (cid, type(raw_reason).__name__)))
            reason = raw_reason.strip() if isinstance(raw_reason, str) \
                else ""
            if (not isinstance(between, list) or len(between) != 2
                    or len(set(str(b) for b in between)) != 2):
                problems.append(("BOUNDARY-SHAPE",
                                 "%s: 'between' must name exactly two distinct "
                                 "rows; got %r" % (cid, between)))
            else:
                names = [str(b) for b in between]
                for name in names:
                    if name not in covered:
                        problems.append(("BOUNDARY-SHAPE",
                                         "%s: %r in 'between' is not a §2b row"
                                         % (cid, name)))
                if row not in names:
                    problems.append(("BOUNDARY-SHAPE",
                                     "%s: decided row %s is not one of the two "
                                     "candidates %s — a boundary must be decided "
                                     "IN FAVOUR of one of its sides"
                                     % (cid, row, names)))
            if len(reason) < MIN_REASON_CHARS:
                problems.append(("BOUNDARY-REASON",
                                 "%s: reason is %d chars; a decided boundary "
                                 "carries its argument (>= %d)"
                                 % (cid, len(reason), MIN_REASON_CHARS)))
    for cid, n in sorted(seen_ids.items()):
        if n > 1:
            problems.append(("CASE-SHAPE", "case id %r appears %dx" % (cid, n)))
    # The doc <-> fixture binding is EQUALITY, not containment (rail round 1
    # [P2]): iterating fixture ids alone left a renamed or deleted case, and an
    # extra frozen row, alive in the doc with the check still green.
    for dup in doc_row_dupes:
        problems.append(("DOC-DUP",
                         "the doc declares frozen row %s more than once; a dict "
                         "would keep only the last and bind against it" % dup))
    for dup in doc_case_dupes:
        problems.append(("DOC-DUP",
                         "the doc case index declares %s more than once" % dup))
    for extra in sorted(set(doc_rows) - set(row_ids)):
        problems.append(("DOC-UNBOUND",
                         "the doc freezes row %s, which §2b/the fixture do not "
                         "have — a stale row nothing verifies" % extra))
    for extra in sorted(set(doc_index) - set(seen_ids)):
        problems.append(("DOC-UNBOUND",
                         "the doc case index lists %s, which the fixture does "
                         "not — a stale case nothing verifies" % extra))
    for rid in row_ids:
        if covered.get(rid, 0) == 0:
            problems.append(("ROW-UNCOVERED",
                             "§2b row %s has no non-boundary worked case — the "
                             "row is normative but not exercised" % rid))
    if boundary_count == 0:
        problems.append(("NO-BOUNDARY",
                         "no case is marked boundary; AC-14 requires at least "
                         "one boundary DECIDED in writing"))

    if list_cases:
        for case in cases:
            if not isinstance(case, dict):
                continue
            print("%-4s %-3s %-8s %s"
                  % (case.get("id"), case.get("row"),
                     "boundary" if case.get("boundary") else "worked",
                     str(case.get("task", ""))[:96]))

    if problems:
        sys.stderr.write("check-classifier-cases: %d PROBLEM(S)\n" % len(problems))
        for code, msg in problems:
            sys.stderr.write("  [%s] %s\n" % (code, msg))
        return 1
    n_cit = sum(len(c.get("citations") or []) for c in cases)
    print("check-classifier-cases: CONSISTENT")
    print("  rows      : %d (§2b order, cells identical in plan, doc and fixture)"
          % len(row_ids))
    print("  procedure : %d terminals over %d questions — total partition proved"
          % (len(pairs), len({TOKEN_RE.match(t).group(1) for t, _ in pairs})))
    print("  cases     : %d (%d worked, %d boundary); coverage %s"
          % (len(cases), len(cases) - boundary_count, boundary_count,
             " ".join("%s=%d" % (r, covered[r]) for r in row_ids)))
    print("  citations : %d verified on disk (path + anchor, each anchor "
          "unique in its file; no line pin)" % n_cit)
    return 0


def _resolve_arg(value: Optional[str], default: Path, flag: str) -> Path:
    """Resolve an operator-supplied path, or raise Usage (rc 2).

    v2 rail r5 [P2]: `Path.resolve()` raises RuntimeError on a symlink loop
    and OSError on other resolution failures. Both used to escape as a
    traceback with rc 1 — a crash wearing the exit code of a finding.
    """
    # rail r6 [P2]: `--fixture ""` (an unset shell variable) is NOT the same
    # as an omitted flag. Treating it as omitted made the gate check the
    # COMMITTED default and answer rc 0 CONSISTENT about a file the caller
    # never named — a false green produced by a typo in the caller.
    if value is None:
        return default
    if not value.strip():
        raise Usage("%s was given an EMPTY path; an omitted flag falls back "
                    "to the committed default, an empty one is unusable "
                    "input" % flag)
    try:
        return Path(value).resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise Usage("%s %r cannot be resolved (%s); the gate cannot read its "
                    "own inputs" % (flag, value, type(exc).__name__))


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None,
                    help="checkout to verify citations against "
                         "(default: derived by walking up from this file)")
    ap.add_argument("--fixture", default=None, help="override the fixture path")
    ap.add_argument("--doc", default=None, help="override the doc path")
    ap.add_argument("--plan", default=None, help="override the plan path")
    ap.add_argument("--list-cases", action="store_true",
                    help="print one line per case")
    args = ap.parse_args(argv)
    try:
        # rail r7 [P2]: `if args.root:` let `--root ""` (an unset shell
        # variable) fall through to the DERIVED root — the gate then answered
        # about a tree the caller never named, bypassing the empty-path
        # refusal below. Omitted and empty are different inputs.
        if args.root is not None:
            root = _resolve_arg(args.root, Path.cwd(), "--root")
        else:
            found = find_root(Path(__file__).resolve().parent)
            if found is None:
                raise Usage("could not derive the checkout root from %s; pass "
                            "--root" % Path(__file__).resolve().parent)
            root = found
        # v2 rail r5 [P2]: `.resolve()` on an operator-supplied path can
        # raise RuntimeError (symlink loop) or OSError, BEFORE any read — so
        # the process died with a traceback and rc 1, the code reserved for
        # named inconsistencies, on input it simply could not use. Unusable
        # input is rc 2, and that includes the path itself.
        plan_path = _resolve_arg(args.plan, root / REL_PLAN, "--plan")
        doc_path = _resolve_arg(args.doc, root / REL_DOC, "--doc")
        fixture_path = _resolve_arg(args.fixture, root / REL_FIXTURE,
                                    "--fixture")
        return run(root, plan_path, doc_path, fixture_path, args.list_cases)
    except Usage as exc:
        sys.stderr.write("check-classifier-cases: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
