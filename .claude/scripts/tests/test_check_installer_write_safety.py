"""PLAN-185 W0 (4th pass, INVERTED rule) — oracle for the installer write-safety census.

Covers ``.claude/scripts/check-installer-write-safety.py``.

WHAT CHANGED, AND WHY THE TEST FILE CHANGED SHAPE WITH IT
---------------------------------------------------------
Passes 1..3 of the instrument credited ``guardado``/``nao-aplicavel`` to every
form they did not recognise, so each review round found another unrecognised
form: 8, then 7, then 9, then 10, then 16 findings, all one class — "a shape
the parser does not model comes out safe".  The 4th pass INVERTS the rule:
safety is a theorem provable only by a named form, and everything else is
``indeterminado``, which blocks.

That inversion is only real if the test file asserts it in two directions, so
every safe form below appears TWICE:

* a POSITIVE CONTROL — the form with its guard intact must come out
  NON-BLOCKING and carry the form's id, proving the instrument can still say
  "safe" and has not degenerated into a matcher that flags every line;
* a MUTATION — the same fixture with the guard removed, weakened, or renamed
  must come out BLOCKING and NAME the planted path.  The mutation reproduces
  the MECHANISM the prover inspects (the ``-L`` test, the escaping
  replacement, the dominating scope), never merely its appearance
  ([[feedback-positive-control-must-reproduce-the-mechanism]]).

``TestRailRegressions`` then replays every open pair-rail finding about this
instrument as a fixture.  Each of those forms was classified NON-blocking by
the old rule; each must block now.  The mapping from test to finding id is in
the docstring of each test and, in full, in
``.claude/plans/PLAN-185/w0-censo-S329.md`` §5.

Hermetic: every mechanism assertion builds its own shell corpus under a
tempdir and points the census at it with ``--repo-root``.  The live-repo
assertions are READ-ONLY: this file never executes an installer and never
writes outside the tempdir.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
CENSUS = REPO / ".claude" / "scripts" / "check-installer-write-safety.py"
BASELINE = REPO / ".claude" / "scripts" / "data" / "installer-write-safety-baseline.txt"

# Env isolation is not optional here: every assertion shells out to the census,
# and a leaked HOME or CLAUDE_PROJECT_DIR would let this file read or write
# state belonging to the real session.
_HOOKS_DIR = REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

BLOCKING = ("desguardado", "indeterminado")


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------


class Census(object):
    """One census run over a shadow corpus."""

    def __init__(self, rc: int, payload: Optional[dict], stdout: str,
                 stderr: str, root: Path) -> None:
        self.rc = rc
        self.payload = payload or {"sites": []}
        self.stdout = stdout
        self.stderr = stderr
        self.root = root

    def sites(self, name: Optional[str] = None) -> List[dict]:
        out = self.payload.get("sites", [])
        if name is not None:
            out = [s for s in out if s["path"].endswith(name)]
        return out

    def at(self, name: str, snippet: str,
           operand: Optional[str] = None,
           cls: Optional[str] = None) -> dict:
        hits = [s for s in self.sites(name) if snippet in s["snippet"]]
        if operand is not None:
            hits = [s for s in hits if operand in s["operand"]]
        if cls is not None:
            hits = [s for s in hits if s["class"] == cls]
        elif len(hits) > 1:
            # The 5th pass added `write-candidate`, a class that asks a
            # DIFFERENT question about the same line: not "is this tested path
            # written unguarded" but "does this command write at all".  An
            # assertion that named neither is asking the older, more specific
            # question, so answer that one; the new class has its own
            # assertions in TestFailClosedDiscovery.
            specific = [s for s in hits if s["class"] != "write-candidate"]
            if len(specific) == 1:
                hits = specific
        if len(hits) != 1:
            raise AssertionError(
                "expected exactly 1 site matching %r in %s, got %d:\n%s"
                % (snippet, name, len(hits),
                   "\n".join("  %s:%d %s %s %s"
                             % (s["path"], s["line"], s["class"], s["verdict"],
                                s["form"])
                             for s in self.sites(name))))
        return hits[0]

    def blocking(self, name: Optional[str] = None) -> List[dict]:
        return [s for s in self.sites(name) if s["blocking"]]

    def describe(self) -> str:
        return "\n".join(
            "  %s:%d %-14s %-14s %-26s %s"
            % (s["path"], s["line"], s["class"], s["verdict"], s["form"],
               s["snippet"][:60])
            for s in self.sites())


def run_census(tmp: Path, files: Dict[str, str],
               args: Sequence[str] = (),
               baseline_text: Optional[str] = None) -> Census:
    root = tmp / "corpus"
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        target = root / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    bl = root / "baseline.txt"
    bl.write_text(baseline_text or "", encoding="utf-8")
    cmd = [sys.executable, str(CENSUS), "--repo-root", str(root),
           "--baseline", str(bl), "--json"] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    payload = None
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
        except ValueError:
            payload = None
    if payload is None and proc.returncode not in (2,):
        # A crash used to arrive here as an empty site list, so every
        # assertion about a planted defect passed vacuously — the census
        # "found nothing" because it never ran. Fail LOUDLY instead.
        raise AssertionError(
            "census produced no JSON (rc=%d)\nstdout: %s\nstderr: %s"
            % (proc.returncode, proc.stdout[-2000:], proc.stderr[-4000:]))
    return Census(proc.returncode, payload, proc.stdout, proc.stderr, root)


class CensusCase(TestEnvContext):
    """Base class giving each test its own tempdir and corpus helper."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def census(self, files: Dict[str, str], args: Sequence[str] = (),
               baseline_text: Optional[str] = None) -> Census:
        return run_census(self.tmp, files, args, baseline_text)

    def assertSafe(self, c: Census, name: str, snippet: str,
                   form: str, operand: Optional[str] = None,
                   cls: Optional[str] = None) -> dict:
        site = c.at(name, snippet, operand, cls)
        self.assertFalse(
            site["blocking"],
            "expected the guarded form to be PROVEN safe, got %s (%s)\n%s"
            % (site["verdict"], site["detail"], c.describe()))
        self.assertEqual(
            form, site["form"],
            "proven safe by the wrong form: %r\n%s" % (site["form"], c.describe()))
        return site

    def assertBlocks(self, c: Census, name: str, snippet: str,
                     verdict: Optional[str] = None,
                     operand: Optional[str] = None,
                     cls: Optional[str] = None) -> dict:
        site = c.at(name, snippet, operand, cls)
        self.assertIn(
            site["verdict"], BLOCKING,
            "expected the mutated form to BLOCK, got %s (%s)\n%s"
            % (site["verdict"], site["form"], c.describe()))
        self.assertEqual(name, Path(site["path"]).name,
                         "the finding must NAME the planted file")
        if verdict is not None:
            self.assertEqual(verdict, site["verdict"], c.describe())
        return site


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

HEAD = "#!/usr/bin/env bash\nset -euo pipefail\nSRC=/src\n\n"


def sh(body: str) -> str:
    return HEAD + body.strip() + "\n"


# --------------------------------------------------------------------------
# A. the allowlist, one positive control + one mutation per form
# --------------------------------------------------------------------------


class TestFormA1NofollowTestDominates(CensusCase):
    """a1 — a `-L` test whose branch aborts, dominating the write."""

    GUARDED = sh("""
deliver() {
  local dst="$1"
  if [ -L "$dst" ]; then
    return 1
  fi
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")

    MUTATED = sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")

    def test_guard_present_is_proven_safe(self) -> None:
        c = self.census({"a1.sh": self.GUARDED})
        self.assertSafe(c, "a1.sh", '-e "$dst"', "a1-nofollow-test-dominates")

    def test_guard_removed_blocks_and_names_the_path(self) -> None:
        c = self.census({"a1.sh": self.MUTATED})
        site = self.assertBlocks(c, "a1.sh", '-e "$dst"', "desguardado")
        self.assertIn("cp", site["detail"])

    def test_guard_on_a_different_path_is_not_credited(self) -> None:
        """The `-L` must be on the SAME path, not merely present nearby."""
        c = self.census({"a1.sh": sh("""
deliver() {
  local dst="$1"
  local other="$2"
  if [ -L "$other" ]; then
    return 1
  fi
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "a1.sh", '-e "$dst"', "desguardado")


class TestFormA2NofollowHelperDominates(CensusCase):
    """a2 — a helper crediting requires reading its BODY.

    Rail findings: S326 §7-quater Q5; PLAN-183 rail-materials-round-1
    "Validate helper behavior before granting guard status"; S328 rail rounds
    1 and 3 ("Verify helper behavior before crediting a guard").  The previous
    pass credited ANY command whose name matched
    ``symlink|nofollow|lstat|deref``.
    """

    REAL = sh("""
_root_guard() {
  if [ -L "$1" ]; then
    echo "refusing to write through a symlink" >&2
    return 1
  fi
  return 0
}

deliver() {
  local dst="$1"
  _root_guard "$dst" || return 1
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")

    # Same call shape, same suggestive NAME, body that only warns.
    NAME_ONLY = sh("""
_symlink_nofollow_lstat_guard() {
  echo "checking $1" >&2
  return 0
}

deliver() {
  local dst="$1"
  _symlink_nofollow_lstat_guard "$dst" || return 1
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")

    # A real body, but the call site ignores the refusal.
    UNCHECKED_CALL = sh("""
_root_guard() {
  if [ -L "$1" ]; then
    return 1
  fi
  return 0
}

deliver() {
  local dst="$1"
  _root_guard "$dst"
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")

    def test_real_helper_is_proven_safe(self) -> None:
        c = self.census({"a2.sh": self.REAL})
        self.assertSafe(c, "a2.sh", '-e "$dst"', "a2-nofollow-helper-dominates")

    def test_name_alone_is_never_evidence(self) -> None:
        c = self.census({"a2.sh": self.NAME_ONLY})
        self.assertBlocks(c, "a2.sh", '-e "$dst"')

    def test_helper_whose_refusal_is_ignored_is_not_a_guard(self) -> None:
        c = self.census({"a2.sh": self.UNCHECKED_CALL})
        self.assertBlocks(c, "a2.sh", '-e "$dst"')


class TestFormA3NoWriteToOperand(CensusCase):
    """a3 — every occurrence of the tested path is at a proven non-writing spot."""

    READ_ONLY = sh("""
check() {
  local probe="$1"
  if [ -f "$probe" ]; then
    grep -q marker "$probe"
  fi
}
""")

    WITH_WRITE = sh("""
check() {
  local probe="$1"
  if [ -f "$probe" ]; then
    grep -q marker "$probe"
  fi
  cp "$SRC" "$probe"
}
""")

    UNMODELLED_USE = sh("""
check() {
  local probe="$1"
  if [ -f "$probe" ]; then
    grep -q marker "$probe"
  fi
  some_external_tool --into "$probe"
}
""")

    def test_no_write_is_proven_not_assumed(self) -> None:
        c = self.census({"a3.sh": self.READ_ONLY})
        self.assertSafe(c, "a3.sh", '-f "$probe"', "a3-no-write-to-operand")

    def test_a_write_anywhere_in_the_region_voids_the_proof(self) -> None:
        c = self.census({"a3.sh": self.WITH_WRITE})
        self.assertBlocks(c, "a3.sh", '-f "$probe"', "desguardado")

    def test_one_unmodelled_occurrence_voids_the_proof(self) -> None:
        """The inversion in one assertion: an unknown command is not a
        non-writer, so it cannot leave the site non-blocking."""
        c = self.census({"a3.sh": self.UNMODELLED_USE})
        site = self.assertBlocks(c, "a3.sh", '-f "$probe"', "indeterminado")
        self.assertEqual("i-unmodeled-occurrence", site["form"])

    def test_alias_through_an_assignment_is_followed(self) -> None:
        c = self.census({"a3.sh": sh("""
check() {
  local probe="$1"
  local twin="$probe"
  if [ -f "$probe" ]; then
    grep -q marker "$probe"
  fi
  cp "$SRC" "$twin"
}
""")})
        self.assertBlocks(c, "a3.sh", '-f "$probe"')

    def test_local_helper_that_does_not_write_keeps_the_proof(self) -> None:
        """One level of interprocedural analysis, so a read-only local helper
        does not degrade every caller to indeterminate."""
        c = self.census({"a3.sh": sh("""
_note() {
  echo "note: $1" >&2
}

check() {
  local probe="$1"
  if [ -f "$probe" ]; then
    _note "$probe"
  fi
}
""")})
        self.assertSafe(c, "a3.sh", '-f "$probe"', "a3-no-write-to-operand")

    def test_local_helper_that_writes_is_a_write(self) -> None:
        c = self.census({"a3.sh": sh("""
_emit() {
  cp "$SRC" "$1"
}

check() {
  local probe="$1"
  if [ -f "$probe" ]; then
    return 0
  fi
  _emit "$probe"
}
""")})
        self.assertBlocks(c, "a3.sh", '-f "$probe"', "desguardado")


class TestFormA4ConfinementPredicateDominates(CensusCase):
    """a4 — a confinement predicate living in a SHARED library.

    Requested by the PLAN-185 W1 cure, whose predicate deliberately lives in
    `scripts/_framework_manifest_set.sh` rather than in each writer: one
    original consulted by install/upgrade/doctor, instead of the per-writer
    copies that produced the PLAN-183 D1..D4 divergence.  a2 could not express
    it (same-file only, `|| abort` polarity only).

    Everything else about a2's doctrine survives: the body is inspected, the
    name proves nothing, and the arguments must actually BIND the destination.
    """

    LIB = sh("""
_wbm_dst_refuses() {
  _wbm_root="$1"
  _wbm_rel="$2"
  _wbm_probe="$_wbm_root/$_wbm_rel"
  if [ -L "$_wbm_probe" ]; then
    _WBM_DST_REFUSE_WHY="destination is a symlink"
    return 0
  fi
  return 1
}
""")

    # Refusal polarity: rc 0 = refuse, consulted as the condition of an `if`.
    CONSUMER = sh("""
deliver() {
  local rel="$1"
  local dst="$TARGET/$rel"
  if _wbm_dst_refuses "$TARGET" "$rel"; then
    echo "    SKIP: $_WBM_DST_REFUSE_WHY" >&2
    return
  fi
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")

    def test_shared_predicate_is_proven_safe(self) -> None:
        c = self.census({"lib.sh": self.LIB, "consumer.sh": self.CONSUMER})
        self.assertSafe(c, "consumer.sh", '-e "$dst"',
                        "a4-confinement-predicate-dominates")

    def test_predicate_defined_nowhere_is_not_a_guard(self) -> None:
        """The library is not in the corpus, so the body cannot be read."""
        c = self.census({"consumer.sh": self.CONSUMER})
        self.assertBlocks(c, "consumer.sh", '-e "$dst"')

    def test_two_definitions_are_ambiguous(self) -> None:
        """Two files defining one name: the census cannot know which body
        runs, and a guard whose body is unknown proves nothing."""
        c = self.census({"lib.sh": self.LIB,
                         "lib2.sh": self.LIB,
                         "consumer.sh": self.CONSUMER})
        self.assertBlocks(c, "consumer.sh", '-e "$dst"')

    def test_a_body_that_only_warns_is_not_a_guard(self) -> None:
        """Same NAME, same call shape, body with no symlink check at all."""
        c = self.census({"lib.sh": sh("""
_wbm_dst_refuses() {
  echo "checking $1/$2" >&2
  return 1
}
"""), "consumer.sh": self.CONSUMER})
        self.assertBlocks(c, "consumer.sh", '-e "$dst"')

    def test_arguments_must_bind_the_destination(self) -> None:
        """The predicate was told about a DIFFERENT path than the one written.

        `"$TARGET" + "$rel"` confines `$TARGET/$rel`, but the write lands at
        `$TARGET/.github/$rel` — a path the predicate never saw."""
        c = self.census({"lib.sh": self.LIB, "consumer.sh": sh("""
deliver() {
  local rel="$1"
  local dst="$TARGET/.github/$rel"
  if _wbm_dst_refuses "$TARGET" "$rel"; then
    return
  fi
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        site = self.assertBlocks(c, "consumer.sh", '-e "$dst"')
        self.assertEqual("i-predicate-arg-unbound", site["form"])

    def test_a_discarded_refusal_is_not_a_guard(self) -> None:
        """A bare call whose status nobody reads.  This one nearly shipped:
        `_find_then_uid` picked up the `then` of the FOLLOWING `if`, so a4
        briefly became a bypass around the a2 mutation control."""
        c = self.census({"lib.sh": self.LIB, "consumer.sh": sh("""
deliver() {
  local rel="$1"
  local dst="$TARGET/$rel"
  _wbm_dst_refuses "$TARGET" "$rel"
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "consumer.sh", '-e "$dst"')

    def test_the_other_polarity_also_works(self) -> None:
        """`<pred> ... || <abort>` — rc != 0 = refuse."""
        c = self.census({"lib.sh": sh("""
_wbm_dst_allows() {
  _wbm_probe="$1/$2"
  if [ -L "$_wbm_probe" ]; then
    return 1
  fi
  return 0
}
"""), "consumer.sh": sh("""
deliver() {
  local rel="$1"
  local dst="$TARGET/$rel"
  _wbm_dst_allows "$TARGET" "$rel" || return
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertSafe(c, "consumer.sh", '-e "$dst"',
                        "a4-confinement-predicate-dominates")

    def test_the_destination_itself_binds(self) -> None:
        """The simpler call shape: the predicate is handed the destination."""
        c = self.census({"lib.sh": sh("""
_wbm_dst_refuses() {
  if [ -L "$1" ]; then
    return 0
  fi
  return 1
}
"""), "consumer.sh": sh("""
deliver() {
  local dst="$1"
  if _wbm_dst_refuses "$dst"; then
    return
  fi
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertSafe(c, "consumer.sh", '-e "$dst"',
                        "a4-confinement-predicate-dominates")


class TestA4DelegationBoundary(CensusCase):
    """Where a4 stops, measured against the SHAPE of the PLAN-185 W1 cure.

    The cure's real call chain has three levels: the writer calls a local
    wrapper (`_dst_refuses <rel>`), which supplies the target root and
    delegates to the shared predicate (`_wbm_dst_refuses <root> <rel>`) in
    another file.  a4 inspects the body of the function actually CALLED, and
    the wrapper checks no parameter of its own — it delegates.  So a4 stops at
    the wrapper.

    Both directions are asserted.  The negative one is not a wish for the cure
    to fail: it is a guard, so that widening a4 to bless a delegation chain has
    to be a deliberate change with its own controls rather than something that
    quietly starts passing.
    """

    LIB = sh("""
_wbm_dst_refuses() {
  _wbm_dr_root="${1:-}"
  _wbm_dr_rel="${2:-}"
  _wbm_dr_walk="$_wbm_dr_root/$_wbm_dr_rel"
  if [ -L "$_wbm_dr_walk" ]; then
    _WBM_DST_REFUSE_WHY="component is a symlink"
    return 0
  fi
  return 1
}
""")

    def test_a_direct_call_to_the_shared_predicate_is_credited(self) -> None:
        c = self.census({"lib.sh": self.LIB, "writer.sh": sh("""
install_docs_template() {
  local dst_rel="$1"
  local dst="$TARGET/$dst_rel"
  if _wbm_dst_refuses "$TARGET" "$dst_rel"; then
    return
  fi
  if [[ -e "$dst" ]]; then
    return
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertSafe(c, "writer.sh", '-e "$dst"',
                        "a4-confinement-predicate-dominates")

    def test_a_delegating_wrapper_is_not_credited(self) -> None:
        """The wrapper's own body checks nothing, so a4 cannot prove it.

        Widening this is an allowlist decision, not a bug fix: it would mean
        trusting that a wrapper's return value faithfully carries a delegate's
        verdict, which needs its own positive control and its own mutations.
        """
        c = self.census({"lib.sh": self.LIB, "writer.sh": sh("""
_dst_refuses() {
  local dst_rel="$1"
  local why=""
  if ! command -v _wbm_dst_refuses >/dev/null 2>&1; then
    why="predicate unavailable"
  elif _wbm_dst_refuses "$TARGET" "$dst_rel"; then
    why="${_WBM_DST_REFUSE_WHY:-unknown}"
  else
    return 1
  fi
  return 0
}

install_docs_template() {
  local dst_rel="$1"
  local dst="$TARGET/$dst_rel"
  if _dst_refuses "$dst_rel"; then
    return
  fi
  if [[ -e "$dst" ]]; then
    return
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "writer.sh", '-e "$dst"')


class TestFormB1DelimiterEscapeDominates(CensusCase):
    """b1 — every assignment escapes THIS delimiter, and one dominates."""

    ESCAPED = sh("""
render() {
  local esc
  esc="$( printf '%s' "$HANDLE" | sed 's/[|&\\]/\\\\&/g' )"
  sed "s|{{H}}|$esc|g" "$SRC" > "$DST"
}
""")

    # Rail Q7 / M9 / N12: the class is right but the replacement re-inserts the
    # match unchanged, so nothing is escaped.
    NOOP_REPLACEMENT = sh("""
render() {
  local esc
  esc="$( printf '%s' "$HANDLE" | sed 's/[|&\\]/&/g' )"
  sed "s|{{H}}|$esc|g" "$SRC" > "$DST"
}
""")

    def test_real_escape_is_proven_safe(self) -> None:
        c = self.census({"b1.sh": self.ESCAPED})
        self.assertSafe(c, "b1.sh", 's|{{H}}|', "b1-delimiter-escape-dominates",
                        operand="{{H}}")

    def test_noop_replacement_is_not_an_escape(self) -> None:
        c = self.census({"b1.sh": self.NOOP_REPLACEMENT})
        self.assertBlocks(c, "b1.sh", 's|{{H}}|', operand="{{H}}")


class TestFormB2ClosedCharsetValidated(CensusCase):
    """b2 — a dominating validation against a literal closed class."""

    CASE_FORM = sh("""
render() {
  case "$HANDLE" in
    *[!A-Za-z0-9_-]*)
      echo "bad handle" >&2
      exit 2
      ;;
  esac
  sed "s/{{H}}/$HANDLE/g" "$SRC" > "$DST"
}
""")

    REGEX_FORM = sh("""
render() {
  [[ "$HANDLE" =~ ^[A-Za-z0-9_-]+$ ]] || exit 2
  sed "s/{{H}}/$HANDLE/g" "$SRC" > "$DST"
}
""")

    # The class ADMITS the delimiter, so validation proves nothing here.
    LEAKY_CLASS = sh("""
render() {
  case "$HANDLE" in
    *[!A-Za-z0-9_/-]*)
      exit 2
      ;;
  esac
  sed "s/{{H}}/$HANDLE/g" "$SRC" > "$DST"
}
""")

    NO_ABORT = sh("""
render() {
  case "$HANDLE" in
    *[!A-Za-z0-9_-]*)
      echo "warning: odd handle" >&2
      ;;
  esac
  sed "s/{{H}}/$HANDLE/g" "$SRC" > "$DST"
}
""")

    def test_case_validation_is_proven_safe(self) -> None:
        c = self.census({"b2.sh": self.CASE_FORM})
        self.assertSafe(c, "b2.sh", 's/{{H}}/', "b2-closed-charset-validated")

    def test_regex_validation_is_proven_safe(self) -> None:
        c = self.census({"b2.sh": self.REGEX_FORM})
        self.assertSafe(c, "b2.sh", 's/{{H}}/', "b2-closed-charset-validated")

    def test_class_admitting_the_delimiter_proves_nothing(self) -> None:
        c = self.census({"b2.sh": self.LEAKY_CLASS})
        self.assertBlocks(c, "b2.sh", 's/{{H}}/')

    def test_validation_that_only_warns_is_not_a_validation(self) -> None:
        c = self.census({"b2.sh": self.NO_ABORT})
        self.assertBlocks(c, "b2.sh", 's/{{H}}/')


class TestFormB3LiteralOnly(CensusCase):
    """b3 — the interpolated variable is only ever a safe literal."""

    LITERAL = sh("""
render() {
  local marker="ok-value"
  sed "s/{{H}}/$marker/g" "$SRC" > "$DST"
}
""")

    LITERAL_WITH_DELIMITER = sh("""
render() {
  local marker="a/b"
  sed "s/{{H}}/$marker/g" "$SRC" > "$DST"
}
""")

    def test_safe_literal_is_proven_safe(self) -> None:
        c = self.census({"b3.sh": self.LITERAL})
        self.assertSafe(c, "b3.sh", 's/{{H}}/', "b3-literal-only")

    def test_literal_carrying_the_delimiter_blocks(self) -> None:
        c = self.census({"b3.sh": self.LITERAL_WITH_DELIMITER})
        self.assertBlocks(c, "b3.sh", 's/{{H}}/')


class TestFormB4InlineEscapeSubstitution(CensusCase):
    """b4 — the escape applied in place, the idiom this corpus already uses."""

    INLINE = sh("""
render() {
  sed "s|{{H}}|$( printf '%s' "$V" | sed 's/[|&\\]/\\\\&/g' )|g" "$SRC" > "$DST"
}
""")

    BARE = sh("""
render() {
  sed "s|{{H}}|$( printf '%s' "$V" )|g" "$SRC" > "$DST"
}
""")

    def test_inline_escape_is_proven_safe(self) -> None:
        c = self.census({"b4.sh": self.INLINE})
        self.assertSafe(c, "b4.sh", 's|{{H}}|', "b4-inline-escape-substitution",
                        operand="{{H}}")

    def test_bare_substitution_blocks(self) -> None:
        c = self.census({"b4.sh": self.BARE})
        site = self.assertBlocks(c, "b4.sh", 's|{{H}}|', "indeterminado",
                                 operand="{{H}}")
        self.assertEqual("i-command-substitution", site["form"])


class TestFormN0NoInterpolation(CensusCase):
    """n0 — a fully literal stream-editor script."""

    def test_literal_script_is_proven_safe(self) -> None:
        c = self.census({"n0.sh": sh("""
show() {
  sed -n '2,59p' "$SRC" > "$DST"
}
""")})
        self.assertSafe(c, "n0.sh", "sed -n '2,59p'", "n0-no-interpolation")

    def test_sed_dollar_inside_single_quotes_is_not_an_expansion(self) -> None:
        """sed's own `$` (last line) must not be read as a shell variable."""
        c = self.census({"n0.sh": sh("""
show() {
  sed -n '$p' "$SRC" > "$DST"
}
""")})
        self.assertSafe(c, "n0.sh", "sed -n '$p'", "n0-no-interpolation")

    def test_expansion_outside_a_substitution_still_blocks(self) -> None:
        c = self.census({"n0.sh": sh("""
show() {
  sed -n "2,${N}p" "$SRC" > "$DST"
}
""")})
        self.assertBlocks(c, "n0.sh", "sed -n", "indeterminado")

    def test_awk_program_with_an_interpolation_blocks(self) -> None:
        c = self.census({"n0.sh": sh("""
show() {
  awk "/$PATTERN/ { print }" "$SRC" > "$DST"
}
""")})
        site = self.assertBlocks(c, "n0.sh", "awk", "indeterminado")
        self.assertEqual("i-awk-program-interpolated", site["form"])


# --------------------------------------------------------------------------
# B. every open pair-rail finding, replayed as a regression fixture
# --------------------------------------------------------------------------


class TestRailRegressions(CensusCase):
    """Each fixture is a form the OLD rule classified non-blocking.

    Finding ids: ``Q*`` = ``PLAN-185/w0-censo-S326.md`` §7-quater;
    ``M*`` = ``PLAN-183/w5-ceremony/rail-materials-round-1.md``;
    ``N*`` = the S328 main-tree rail rounds 1..5.
    """

    def test_write_candidate_cap_is_gone(self) -> None:
        """Q1 / M2 / N5 / N16 — the 11th write past a cap of 10 was invisible.

        There is no cap any more: the proof is "no write to this path
        anywhere in the region", which cannot be satisfied by truncation.
        """
        body = ["deliver() {", '  local d="$1"', '  if [ -e "$d" ]; then']
        for i in range(10):
            body.append('    cp "$SRC/f%d" "$d"' % i)
        body.append("  fi")
        body.append('  cp "$SRC/final" "$d"')
        body.append("}")
        c = self.census({"cap.sh": sh("\n".join(body))})
        self.assertBlocks(c, "cap.sh", '-e "$d"', "desguardado")

    def test_command_level_negation_with_brackets(self) -> None:
        """N2 — `if ! [ -e "$dst" ]` read as non-negated, so the branch that a
        dangling link DOES take was reported unreachable."""
        c = self.census({"neg.sh": sh("""
deliver() {
  local dst="$1"
  if ! [ -e "$dst" ]; then
    cp "$SRC" "$dst"
  fi
}
""")})
        self.assertBlocks(c, "neg.sh", '-e "$dst"', "desguardado")

    def test_negated_test_command_form(self) -> None:
        """Q2 / M5 / N8 — the same defect through `test` instead of `[`."""
        c = self.census({"neg.sh": sh("""
deliver() {
  local dst="$1"
  if ! test -e "$dst"; then
    cp "$SRC" "$dst"
  fi
}
""")})
        self.assertBlocks(c, "neg.sh", "test -e", "desguardado")

    def test_nested_jump_is_not_an_unconditional_abort(self) -> None:
        """Q3 / M6 / N9 — a `return` inside a deeper `if` set `then_jumps`,
        so the copy after `fi` was called unreachable."""
        c = self.census({"nested.sh": sh("""
deliver() {
  local d="$1"
  if [ ! -e "$d" ]; then
    if is_pinned; then
      return
    fi
  fi
  cp "$SRC" "$d"
}
""")})
        self.assertBlocks(c, "nested.sh", '-e "$d"')

    def test_guard_must_dominate_the_write(self) -> None:
        """Q4 / M7 / N10 — a `-L` guard inside an earlier optional branch was
        credited for a write that branch does not dominate."""
        c = self.census({"dom.sh": sh("""
deliver() {
  local d="$1"
  if [ -e "$d" ]; then
    if [ -L "$d" ]; then
      return 1
    fi
  fi
  cp "$SRC" "$d"
}
""")})
        site = self.assertBlocks(c, "dom.sh", '-e "$d"')
        self.assertEqual("i-guard-not-dominating", site["form"])

    def test_guard_does_not_dominate_across_a_function_boundary(self) -> None:
        """Found while curing Q4: a top-level guard sits at scope `()`, which
        is a prefix of EVERY scope, so without a function check it dominated
        every write in every function defined below it — and function bodies
        do not run in source order."""
        c = self.census({"dom.sh": sh("""
[ -L "$BOOT" ] && exit 1

deliver() {
  if [ -e "$BOOT" ]; then
    return 0
  fi
  cp "$SRC" "$BOOT"
}
""")})
        self.assertBlocks(c, "dom.sh", '-e "$BOOT"')

    def test_sed_with_a_line_continuation_is_seen(self) -> None:
        """Q6 / M1 / N4 — the continuation lines carried no `sed` token, so a
        raw substitution split across lines was skipped entirely.  The rail
        named a live instance: `scripts/_grok_harness.sh:112-115`."""
        c = self.census({"cont.sh": sh("""
render() {
  printf '%s' "$BODY" \\
    | sed "s/{{H}}/$HANDLE/g" \\
    > "$DST"
}
""")})
        self.assertBlocks(c, "cont.sh", "s/{{H}}/", "desguardado")

    def test_every_same_line_write_is_evaluated(self) -> None:
        """M3 / N6 — the loop stopped at the first destination on the line and
        ignored the dangerous fallback copy."""
        c = self.census({"chain.sh": sh("""
deliver() {
  local d="$1"
  [ -e "$d" ] && cp "$SRC/a" "$d" || cp "$SRC/b" "$d"
}
""")})
        self.assertBlocks(c, "chain.sh", '-e "$d"', "desguardado")

    def test_command_prefix_before_a_writer(self) -> None:
        """M4 / N7 — `command cp ...` parsed with `command` as the program, so
        the `cp` was never recognised and the site came out non-applicable."""
        c = self.census({"prefix.sh": sh("""
deliver() {
  local d="$1"
  if [ -e "$d" ]; then
    return 0
  fi
  command cp "$SRC" "$d"
}
""")})
        self.assertBlocks(c, "prefix.sh", '-e "$d"', "desguardado")

    def test_unmodelled_prefix_option_blocks(self) -> None:
        """The other half of M4/N7: a prefix option the model does not know
        must make the command UNKNOWN, not silently non-writing."""
        c = self.census({"prefix.sh": sh("""
deliver() {
  local d="$1"
  if [ -e "$d" ]; then
    return 0
  fi
  env --unknown-option cp "$SRC" "$d"
}
""")})
        self.assertBlocks(c, "prefix.sh", '-e "$d"', "indeterminado")

    def test_delimiter_is_bound_to_its_own_substitution(self) -> None:
        """Q8 / M10 / N13 — only the first substitution's delimiter was used,
        so a value escaped for `|` passed as safe inside an `s/.../`."""
        c = self.census({"delim.sh": sh("""
render() {
  local esc
  esc="$( printf '%s' "$V" | sed 's/[|&\\]/\\\\&/g' )"
  sed "s|x|ok|g; s/y/$esc/g" "$SRC" > "$DST"
}
""")})
        self.assertBlocks(c, "delim.sh", "s|x|ok|g", operand="s|x|ok|g")

    def test_escape_on_only_one_branch_is_not_reaching(self) -> None:
        """Q9 / M11 / N14 — the last assignment was picked lexically, so a
        value escaped only inside an optional `if` counted on every path."""
        c = self.census({"branch.sh": sh("""
render() {
  esc="$RAW"
  if [ -n "${STRICT:-}" ]; then
    esc="$( printf '%s' "$RAW" | sed 's/[|&\\]/\\\\&/g' )"
  fi
  sed "s|{{H}}|$esc|g" "$SRC" > "$DST"
}
""")})
        self.assertBlocks(c, "branch.sh", 's|{{H}}|', operand="{{H}}")

    def test_sed_inside_a_command_substitution_is_seen(self) -> None:
        """N1 / N15 — the baseline was missing a live `sed-interp` site in
        `scripts/upgrade.sh` because the substitution lived inside `$( ... )`,
        which no pass of this instrument had ever descended into."""
        c = self.census({"subst.sh": sh("""
render() {
  local out
  out="$( cat "$SRC" | sed "s/{{H}}/$HANDLE/g" )"
  printf '%s' "$out" > "$DST"
}
""")})
        self.assertBlocks(c, "subst.sh", "s/{{H}}/", "desguardado")


class TestPassTwoSelfReview(CensusCase):
    """Paths found by re-reading the instrument adversarially before delivery.

    Every one of them is the same class the rail keeps finding — a form that
    would have left a site NON-blocking — so each gets its own control here
    rather than a line in the report.
    """

    def test_sed_long_in_place_flag_is_a_write(self) -> None:
        """`--in-place` did not match the short-flag pattern, so an editor
        that rewrites its operand was classified read-only."""
        c = self.census({"p2.sh": sh("""
deliver() {
  local d="$1"
  if [ -e "$d" ]; then
    return 0
  fi
  sed --in-place 's/a/b/' "$d"
}
""")})
        self.assertBlocks(c, "p2.sh", '-e "$d"', "desguardado")

    def test_find_with_an_acting_primary_is_not_read_only(self) -> None:
        c = self.census({"p2.sh": sh("""
sweep() {
  local root="$1"
  if [ -d "$root" ]; then
    find "$root" -name '*.tmp' -delete
  fi
}
""")})
        self.assertBlocks(c, "p2.sh", '-d "$root"')

    def test_find_without_one_stays_read_only(self) -> None:
        c = self.census({"p2.sh": sh("""
sweep() {
  local root="$1"
  if [ -d "$root" ]; then
    find "$root" -name '*.tmp' -print
  fi
}
""")})
        self.assertSafe(c, "p2.sh", '-d "$root"', "a3-no-write-to-operand")

    def test_conjoined_nofollow_test_is_not_a_guard(self) -> None:
        """`[[ -f "$d" && -L "$d" ]] && return 1` refuses a symlink that is
        ALSO a regular file and lets a dangling one through — the very shape
        this census exists to catch, so it cannot prove safety."""
        c = self.census({"p2.sh": sh("""
deliver() {
  local d="$1"
  [[ -f "$d" && -L "$d" ]] && return 1
  if [ -e "$d" ]; then
    return 0
  fi
  cp "$SRC" "$d"
}
""")})
        self.assertBlocks(c, "p2.sh", '-e "$d"')

    def test_disjoined_nofollow_test_still_counts(self) -> None:
        """The negative control for the line above: `||` is inclusive, so the
        abort does fire for every symlink and the guard is real."""
        c = self.census({"p2.sh": sh("""
deliver() {
  local d="$1"
  [[ -L "$d" || -h "$d" ]] && return 1
  if [ -e "$d" ]; then
    return 0
  fi
  cp "$SRC" "$d"
}
""")})
        self.assertSafe(c, "p2.sh", '-e "$d"', "a1-nofollow-test-dominates")

    def test_a_raw_interpolation_in_a_second_e_script_is_judged(self) -> None:
        """`sed -e A -e B` runs both scripts; reading only the first left a
        raw interpolation in B unexamined."""
        c = self.census({"p2.sh": sh("""
render() {
  sed -e 's/x/ok/' -e "s/y/$HANDLE/" "$SRC" > "$DST"
}
""")})
        self.assertBlocks(c, "p2.sh", "sed -e", "desguardado")

    def test_a_script_read_from_a_file_blocks(self) -> None:
        c = self.census({"p2.sh": sh("""
render() {
  sed -f "$RULES" "$SRC" > "$DST"
}
""")})
        self.assertBlocks(c, "p2.sh", "sed -f", "indeterminado")

    def test_a_symlinked_shell_file_blocks_instead_of_being_skipped(self) -> None:
        """Discovery used to skip symlinked `.sh` files silently, which is a
        hole the size of one `ln -s`."""
        root = self.tmp / "corpus"
        (root / "scripts").mkdir(parents=True)
        real = root / "elsewhere.sh"
        real.write_text(TestFormA1NofollowTestDominates.MUTATED, encoding="utf-8")
        (root / "scripts" / "linked.sh").symlink_to(real)
        (root / "scripts" / "plain.sh").write_text(
            TestFormA3NoWriteToOperand.READ_ONLY, encoding="utf-8")
        bl = root / "baseline.txt"
        bl.write_text("", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(CENSUS), "--repo-root", str(root),
             "--baseline", str(bl), "--json"],
            capture_output=True, text=True)
        payload = json.loads(proc.stdout)
        linked = [s for s in payload["sites"] if s["path"].endswith("linked.sh")]
        self.assertTrue(linked, "a symlinked shell file must still emit a site")
        self.assertTrue(all(s["blocking"] for s in linked))

    def test_a_malformed_baseline_row_fails_the_gate(self) -> None:
        """A row the loader cannot read waives nothing and reports nothing;
        dropping it in silence would let a corrupted baseline look healthy."""
        c = self.census({"g.sh": TestFormA1NofollowTestDominates.MUTATED},
                        baseline_text="this is not a baseline row\n")
        self.assertEqual(1, c.rc)
        self.assertTrue(c.payload["malformed_baseline_rows"])


# --------------------------------------------------------------------------
# C. fail-closed parsing
# --------------------------------------------------------------------------


class TestRailRoundFive(CensusCase):
    """The 16 findings of the 5th pair-rail round, one fixture per rail line.

    Ids ``R5-01``..``R5-16`` map to
    ``/private/tmp/.../rail-u1-1-commit-843eb57.txt`` and to §12 of
    ``.claude/plans/PLAN-185/w0-censo-S329.md``.  Every one of them was
    NON-blocking under the 4th pass — thirteen because the evidence rule was
    too generous, three (R5-01..R5-03) because the site did not EXIST.
    """

    # -- discovery: the form produced no site at all ------------------------

    def test_r5_01_unsupported_file_test_form_blocks(self) -> None:
        """R5-01 — `test -a "$dst"` recorded no site, so a later write through
        `$dst` was invisible rather than indeterminate."""
        c = self.census({"r501.sh": sh("""
deliver() {
  local dst="$1"
  if test -a "$dst"; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r501.sh", 'test -a "$dst"', "desguardado",
                          cls="symlink-follow")

    def test_r5_01_path_qualified_test_is_a_test(self) -> None:
        """R5-01 — the host scan matched the bare word `test` only."""
        c = self.census({"r501b.sh": sh("""
deliver() {
  local dst="$1"
  if /bin/test -e "$dst"; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r501b.sh", "/bin/test -e", "desguardado",
                          cls="symlink-follow")

    def test_r5_01_unmodelled_test_operator_is_a_site(self) -> None:
        """R5-01 — an operator the model does not know must SAY so."""
        c = self.census({"r501c.sh": sh("""
deliver() {
  local dst="$1"
  if [ -Q "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        site = self.assertBlocks(c, "r501c.sh", '-Q "$dst"', "indeterminado",
                                 cls="symlink-follow")
        self.assertEqual("i-unmodeled-test-form", site["form"])

    def test_r5_01_a_redirection_on_a_test_is_not_unmodelled(self) -> None:
        """Negative control for the line above: `[ ... ] 2>/dev/null` is an
        ordinary test, and reporting it would put healthy lines in the
        baseline."""
        c = self.census({"r501d.sh": sh("""
check() {
  local n="$1"
  if [ "$n" -gt 1 ] 2>/dev/null; then
    echo many
  fi
}
""")})
        self.assertEqual(
            [], [s for s in c.sites("r501d.sh")
                 if s["form"] == "i-unmodeled-test-form"], c.describe())

    def test_r5_02_path_qualified_stream_editor_is_judged(self) -> None:
        """R5-02 — `/usr/bin/sed` matched no editor name, so the interpolation
        was never looked at."""
        c = self.census({"r502.sh": sh("""
render() {
  local value="$1"
  /usr/bin/sed "s|x|$value|g" "$SRC" > /tmp/out
}
""")})
        self.assertBlocks(c, "r502.sh", "/usr/bin/sed", "desguardado",
                          cls="sed-interp")

    def test_r5_03_positional_expansion_is_an_expansion(self) -> None:
        """R5-03 — `$1` was not identifier-shaped, so `sed "s|x|$1|g"` came out
        `n0-no-interpolation`: the verdict meaning "nothing to reason about"."""
        c = self.census({"r503.sh": sh("""
render() {
  sed "s|x|$1|g" "$SRC" > /tmp/out
}
""")})
        site = self.assertBlocks(c, "r503.sh", "s|x|$1|g", "desguardado",
                                 cls="sed-interp")
        self.assertIn("$1", site["detail"])

    def test_r5_03_special_parameters_too(self) -> None:
        """R5-03 — `$@`, `$*`, `$#`, `$?` and `$$` were equally invisible."""
        for name in ("$@", "$*", "$#", "$?"):
            c = self.census({"r503b.sh": sh("""
render() {
  sed "s|x|%s|g" "$SRC" > /tmp/out
}
""" % name)})
            self.assertBlocks(c, "r503b.sh", "s|x|%s|g" % name,
                              operand=None, cls="sed-interp")

    def test_r5_03_literal_only_proof_sees_positionals(self) -> None:
        """The same gap survived INSIDE the b3 proof: `local v="$1"` was read
        as a safe literal, so a caller-controlled value was proven safe.  Found
        by the positive-control probe, not by the rail."""
        c = self.census({"r503c.sh": sh("""
render() {
  local v="$1"
  sed "s|x|$v|g" "$SRC" > /tmp/out
}
""")})
        self.assertBlocks(c, "r503c.sh", "s|x|$v|g", "desguardado",
                          cls="sed-interp")

    # -- evidence bound to the exact operation ------------------------------

    def test_r5_04_bracket_internal_negation_is_not_a_guard(self) -> None:
        """R5-04 — `[ ! -L "$dst" ] && return 1` aborts for everything EXCEPT a
        symlink, so the symlink case is the one that continues."""
        c = self.census({"r504.sh": sh("""
deliver() {
  local dst="$1"
  [ ! -L "$dst" ] && return 1
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r504.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r5_04_legacy_conjunction_is_not_a_guard(self) -> None:
        """R5-04 — `[ -f x -a -L x ]` is the `&&` case in legacy spelling."""
        c = self.census({"r504b.sh": sh("""
deliver() {
  local dst="$1"
  [ -f "$dst" -a -L "$dst" ] && return 1
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r504b.sh", '[ -e "$dst" ]', operand=None,
                          cls="symlink-follow")

    def test_r5_05_abort_is_credited_to_its_own_command(self) -> None:
        """R5-05 — `split_commands` made fresh objects, so `c is t.cmd` never
        matched and the operand-text fallback credited the abort attached to
        `-e` to a standalone `-L` later on the same line."""
        c = self.census({"r505.sh": sh("""
deliver() {
  local dst="$1"
  [ -e "$dst" ] && return 1; [ -L "$dst" ]
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r505.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r5_06_guard_is_invalidated_by_a_reassignment(self) -> None:
        """R5-06 — dominance says the guard RAN, not that the value it looked
        at is the one the write opens."""
        c = self.census({"r506.sh": sh("""
deliver() {
  dst=/safe
  [ -L "$dst" ] && return
  dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        site = self.assertBlocks(c, "r506.sh", '[ -e "$dst" ]',
                                 "indeterminado", cls="symlink-follow")
        self.assertEqual("i-guard-value-rebound", site["form"])

    def test_r5_06_without_the_reassignment_the_guard_holds(self) -> None:
        """Negative control: the same fixture minus the rebinding must stay
        PROVEN safe, or the rule would just be "block everything"."""
        c = self.census({"r506b.sh": sh("""
deliver() {
  local dst="$1"
  [ -L "$dst" ] && return
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertSafe(c, "r506b.sh", '[ -e "$dst" ]',
                        "a1-nofollow-test-dominates", cls="symlink-follow")

    def test_r5_06_a_read_rebinds_too(self) -> None:
        """R5-06 — `read` is a reaching definition the assignment index never
        carried."""
        c = self.census({"r506c.sh": sh("""
deliver() {
  local dst=/safe
  [ -L "$dst" ] && return
  read -r dst
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r506c.sh", '[ -e "$dst" ]', "indeterminado",
                          cls="symlink-follow")

    def test_r5_07_redirect_to_a_filename_is_a_write(self) -> None:
        """R5-07 — `>& "$dst"` opens $dst for output; treating every `>&` as a
        descriptor dup threw the filename away."""
        c = self.census({"r507.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  echo hi >& "$dst"
}
""")})
        self.assertBlocks(c, "r507.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r5_07_numeric_descriptor_is_still_a_dup(self) -> None:
        """Negative control: `2>&1` must NOT become a write to a file named 1."""
        c = self.census({"r507b.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    echo present >&2
    return 0
  fi
  echo "$dst" 2>&1
}
""")})
        self.assertSafe(c, "r507b.sh", '[ -e "$dst" ]',
                        "a3-no-write-to-operand", cls="symlink-follow")

    def test_r5_08_sort_o_writes_its_operand(self) -> None:
        """R5-08 — `sort` sat in the read-only set, so `sort -o "$dst"` was
        recorded as a READ."""
        c = self.census({"r508.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  sort -o "$dst" "$SRC"
}
""")})
        self.assertBlocks(c, "r508.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r5_08_uniq_second_operand_writes(self) -> None:
        """R5-08 — `uniq IN OUT` writes OUT."""
        c = self.census({"r508b.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  uniq "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r508b.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r5_08_yq_in_place_writes(self) -> None:
        """R5-08 — `yq -i` edits its operand."""
        c = self.census({"r508c.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  yq -i '.a=1' "$dst"
}
""")})
        self.assertBlocks(c, "r508c.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r5_08_sort_without_an_output_option_still_reads(self) -> None:
        """Negative control: option-AWARE, not name-based.  `sort "$dst"` with
        no `-o` writes nothing, and must stay provably safe."""
        c = self.census({"r508d.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    sort "$dst"
  fi
}
""")})
        self.assertSafe(c, "r508d.sh", '[ -e "$dst" ]',
                        "a3-no-write-to-operand", cls="symlink-follow")

    def test_r5_09_attached_target_directory_is_the_destination(self) -> None:
        """R5-09 — quoting the option VALUE marked the whole token quoted, so
        it bypassed option parsing and the SOURCE became the destination."""
        c = self.census({"r509.sh": sh("""
deliver() {
  local dst="$1"
  if [ -d "$dst" ]; then
    return 0
  fi
  cp --target-directory="$dst" "$SRC"
}
""")})
        self.assertBlocks(c, "r509.sh", '[ -d "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r5_10_b3_needs_a_reaching_assignment(self) -> None:
        """R5-10 — a safe assignment AFTER the use, or in a branch that may not
        run, was accepted as "only ever assigned safe literals"."""
        c = self.census({"r510.sh": sh("""
render() {
  sed "s|x|$v|g" "$SRC" > /tmp/out
  v=safe
}
""")})
        site = self.assertBlocks(c, "r510.sh", "s|x|$v|g", "indeterminado",
                                 cls="sed-interp")
        self.assertEqual("i-escape-unproven", site["form"])

    def test_r5_11_backslash_ampersand_is_not_an_escape(self) -> None:
        """R5-11 — in sed, `\\&` emits a LITERAL ampersand.  Accepting any
        replacement starting with one backslash called that an escape."""
        c = self.census({"r511.sh": sh("""
render() {
  local raw="$1"
  value="$(printf '%s' "$raw" | sed 's/[|&\\]/\\&/g')"
  sed "s|x|$value|g" "$SRC" > /tmp/out
}
""")})
        self.assertBlocks(c, "r511.sh", "s|x|$value|g", "desguardado",
                          cls="sed-interp")

    def test_r5_12_b4_requires_the_sole_producer(self) -> None:
        """R5-12 — the substitution must produce the escaped value and nothing
        else; here a second `printf` appends the RAW one."""
        c = self.census({"r512.sh": sh("""
render() {
  local raw="$1"
  sed "s|x|$(printf '%s' "$raw" | sed 's/[|&\\]/\\\\&/g'; printf %s "$raw")|g" "$SRC" > /tmp/out
}
""")})
        hits = [s for s in c.sites("r512.sh")
                if s["class"] == "sed-interp" and s["blocking"]]
        self.assertTrue(hits, c.describe())
        self.assertEqual("i-command-substitution", hits[0]["form"],
                         c.describe())

    def test_r5_13_validation_must_name_the_exact_variable(self) -> None:
        """R5-13 — the substring test made a validation of `$value` cover a
        later raw interpolation of `$v`."""
        c = self.census({"r513.sh": sh("""
render() {
  local value="$1"
  local v="$2"
  [[ "$value" =~ ^[A-Za-z]+$ ]] || exit 1
  sed "s|x|$v|g" "$SRC" > /tmp/out
}
""")})
        self.assertBlocks(c, "r513.sh", "s|x|$v|g", "desguardado",
                          cls="sed-interp")

    def test_r5_14_validation_must_be_start_anchored(self) -> None:
        """R5-14 — `[[ "$v" =~ [A-Za-z]+$ ]]` passes for `|safe`, which still
        carries the delimiter."""
        c = self.census({"r514.sh": sh("""
render() {
  local v="$1"
  [[ "$v" =~ [A-Za-z]+$ ]] || exit 1
  sed "s|x|$v|g" "$SRC" > /tmp/out
}
""")})
        self.assertBlocks(c, "r514.sh", "s|x|$v|g", "desguardado",
                          cls="sed-interp")

    def test_r5_15_abort_must_be_bound_to_the_validation(self) -> None:
        """R5-15 — any later `|| abort` on the line was accepted, so in
        `[[ ... ]]; true || exit 1` the abort belongs to `true` and never
        fires."""
        c = self.census({"r515.sh": sh("""
render() {
  local v="$1"
  [[ "$v" =~ ^[A-Za-z]+$ ]]; true || exit 1
  sed "s|x|$v|g" "$SRC" > /tmp/out
}
""")})
        self.assertBlocks(c, "r515.sh", "s|x|$v|g", "desguardado",
                          cls="sed-interp")

    def test_r5_15_a_bound_abort_is_still_a_proof(self) -> None:
        """Negative control for R5-13/14/15 together: the anchored, exactly
        matched, directly aborted form must still come out PROVEN safe."""
        c = self.census({"r515b.sh": sh("""
render() {
  local v="$1"
  [[ "$v" =~ ^[A-Za-z]+$ ]] || exit 1
  sed "s|x|$v|g" "$SRC" > /tmp/out
}
""")})
        self.assertSafe(c, "r515b.sh", "s|x|$v|g", "b2-closed-charset-validated",
                        cls="sed-interp")

    def test_r5_16_every_discovered_file_is_listed(self) -> None:
        """R5-16 — a file with zero sites was indistinguishable from a file
        discovery never reached."""
        c = self.census({"withsites.sh": sh("""
deliver() {
  local d="$1"
  cp "$SRC" "$d"
}
"""), "quiet.sh": "#!/usr/bin/env bash\necho hello\n"})
        listed = {f["path"]: f for f in c.payload.get("files", [])}
        self.assertIn("scripts/quiet.sh", listed, listed)
        self.assertEqual(0, listed["scripts/quiet.sh"]["sites"], listed)
        self.assertEqual("scanned", listed["scripts/quiet.sh"]["status"])
        self.assertIn("scripts/withsites.sh", listed, listed)

    def test_r5_16_the_file_list_reaches_the_text_output_too(self) -> None:
        c = self.census({"quiet.sh": "#!/usr/bin/env bash\necho hello\n",
                         "one.sh": sh('cp "$SRC" "$OUT"')}, args=())
        proc = subprocess.run(
            [sys.executable, str(CENSUS), "--repo-root", str(c.root),
             "--baseline", str(c.root / "baseline.txt")],
            capture_output=True, text=True)
        self.assertIn("discovered shell files:", proc.stdout)
        self.assertIn("scripts/quiet.sh", proc.stdout)


class TestRailRoundSix(CensusCase):
    """The 6th pass — the SEVEN specific circumventions of the fail-closed rule.

    Round 2 of the pair-rail (over commit ``7383518``) accepted the fail-closed
    DISCOVERY architecture and then named seven concrete paths around it: a
    write that reached a non-blocking verdict, or produced no site at all,
    because one branch normalised, filtered, split or trusted something it had
    not proven.  Each is replayed here as a fixture whose id is the finding id.

    Every cure carries a NEGATIVE control in the same class.  A cure that only
    made the census stricter would be indistinguishable from "block
    everything", and the R5 pass already paid for learning that the negative
    direction is the half that keeps the instrument usable.

    ``R6-07`` is the one finding that REMOVES a block: `patch -i FILE` reads
    the patch document, so listing it as a destination was a blocking false
    positive.  Its positive control asserts that the POSITIONAL target of
    `patch` still blocks, so the removal cannot widen into an amnesty.
    """

    # -- R6-01: basename trust ------------------------------------------

    def test_r6_01_untrusted_path_qualified_command_is_unknown(self) -> None:
        """R6-01 — `./grep` executes THAT file.  Normalising it to the
        allowlisted basename reached `a3-no-write-to-operand` with no write
        candidate at all."""
        c = self.census({"r601.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  ./grep --output "$dst" "$SRC"
}
""")})
        self.assertBlocks(c, "r601.sh", '[ -e "$dst" ]', cls="symlink-follow")

    def test_r6_01_an_absolute_untrusted_path_is_unknown_too(self) -> None:
        """R6-01 — `/tmp/printf` is not the printf any rule describes."""
        c = self.census({"r601b.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  /tmp/printf '%s' "$dst"
}
""")})
        self.assertBlocks(c, "r601b.sh", '[ -e "$dst" ]', cls="symlink-follow")

    def test_r6_01_a_trusted_system_path_is_still_normalised(self) -> None:
        """Negative control: `/usr/bin/grep` IS the grep the allowlist proves
        read-only.  Without this the cure would just be "distrust paths"."""
        c = self.census({"r601c.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    /usr/bin/grep -q needle "$dst"
  fi
}
""")})
        self.assertSafe(c, "r601c.sh", '[ -e "$dst" ]',
                        "a3-no-write-to-operand", cls="symlink-follow")

    # -- R6-02: positional destinations ---------------------------------

    def test_r6_02_traditional_tar_create_writes_its_archive(self) -> None:
        """R6-02 — `tar czf "$dst" .` carries no dash, so the key letters were
        filed as a positional and the command fell through to READ-ONLY.
        This exact form is live in scripts/uninstall.sh."""
        c = self.census({"r602.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  tar czf "$dst" .
}
""")})
        self.assertBlocks(c, "r602.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r6_02_zip_writes_its_first_positional(self) -> None:
        """R6-02 — `zip ARCHIVE file...`."""
        c = self.census({"r602b.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  zip "$dst" "$SRC"
}
""")})
        self.assertBlocks(c, "r602b.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r6_02_split_writes_its_prefix_operand(self) -> None:
        """R6-02 — `split INPUT PREFIX` writes files at PREFIX."""
        c = self.census({"r602c.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  split "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r602c.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r6_02_an_unmodelled_output_command_is_unknown(self) -> None:
        """R6-02 — the fallback must be UNKNOWN, never read-only: `csplit` has
        an output mode this pass does not model."""
        c = self.census({"r602d.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  csplit "$SRC" "$dst"
}
""")})
        self.assertBlocks(c, "r602d.sh", '[ -e "$dst" ]', cls="symlink-follow")

    def test_r6_02_tar_list_reads_its_archive(self) -> None:
        """Negative control: the key letters DISCRIMINATE.  `tar tf "$dst"`
        lists the archive and writes nothing, so it must stay provably safe."""
        c = self.census({"r602e.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    tar tf "$dst"
  fi
}
""")})
        self.assertSafe(c, "r602e.sh", '[ -e "$dst" ]',
                        "a3-no-write-to-operand", cls="symlink-follow")

    def test_r6_02_tar_extract_is_not_absolved(self) -> None:
        """Pass-2 self-audit: `tar xf "$dst"` READS that operand but extracts
        files into the working directory.  No rule here can name that
        destination, so read-only would have absolved a real write."""
        c = self.census({"r602f.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    tar xf "$dst"
  fi
}
""")})
        self.assertBlocks(c, "r602f.sh", '[ -e "$dst" ]', cls="symlink-follow")

    def test_r6_02_a_dest_bearing_option_is_not_an_input(self) -> None:
        """Pass-2 self-audit: `patch -r FILE` WRITES the reject file.  It sat
        in the input-option table, which would have re-opened the fail-open
        that R6-07 came from, in the opposite direction."""
        c = self.census({"r602g.sh": sh("""
apply() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  patch -r "$dst" /fixed/target
}
""")})
        self.assertBlocks(c, "r602g.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    # -- R6-03: nested expansions ---------------------------------------

    def test_r6_03_nested_default_expansion_is_collected(self) -> None:
        """R6-03 — `${safe:-$RAW}` with `safe` null substitutes RAW.  Reading
        the braced form as ONE token proved the interpolation guarded by
        looking only at `safe`."""
        c = self.census({"r603.sh": sh("""
build() {
  local safe=
  sed "s|x|${safe:-$RAW}|g" "$SRC"
}
""")})
        self.assertBlocks(c, "r603.sh", 'sed "s|x|', cls="sed-interp")

    def test_r6_03_a_nested_command_substitution_is_collected(self) -> None:
        """R6-03 — `${x:=$(cmd)}` runs a command inside the expansion."""
        c = self.census({"r603b.sh": sh("""
build() {
  local safe=
  sed "s|x|${safe:=$(cat /etc/hostname)}|g" "$SRC"
}
""")})
        self.assertBlocks(c, "r603b.sh", 'sed "s|x|', cls="sed-interp")

    def test_r6_03_a_subscript_expansion_is_collected(self) -> None:
        """R6-03 — `${a[$i]}` reads `i` as well as `a`."""
        c = self.census({"r603c.sh": sh("""
build() {
  local a=safe
  sed "s|x|${a[$RAW]}|g" "$SRC"
}
""")})
        self.assertBlocks(c, "r603c.sh", 'sed "s|x|', cls="sed-interp")

    def test_r6_03_a_literal_default_is_still_proven(self) -> None:
        """Negative control: `${safe:-fallback}` has no nested expansion, so
        the b3 proof about `safe` still stands."""
        c = self.census({"r603d.sh": sh("""
build() {
  local safe=ok
  sed "s|x|${safe:-fallback}|g" "$SRC"
}
""")})
        self.assertSafe(c, "r603d.sh", 'sed "s|x|', "b3-literal-only",
                        cls="sed-interp")

    # -- R6-04: opaque commands before the expansion filter --------------

    def test_r6_04_eval_of_a_literal_string_is_a_site(self) -> None:
        """R6-04 — `eval 'cp "$SRC" "$DST"'` has NO outer expansion, so the
        operand filter dropped the command and the census emitted nothing.
        The inner shell expands both variables."""
        c = self.census({"r604.sh": sh("""
deliver() {
  eval 'cp "$SRC" "$DST"'
}
""")})
        site = c.at("r604.sh", "eval")
        self.assertTrue(site["blocking"], c.describe())
        self.assertEqual("i-opaque-command", site["form"], c.describe())

    def test_r6_04_source_of_a_literal_operand_is_a_site(self) -> None:
        """R6-04 — a literal `source` has the same omission."""
        c = self.census({"r604b.sh": sh("""
deliver() {
  source .claude/lib.sh
}
""")})
        site = c.at("r604b.sh", "source")
        self.assertTrue(site["blocking"], c.describe())
        self.assertEqual("i-opaque-command", site["form"], c.describe())

    def test_r6_04_xargs_is_opaque(self) -> None:
        """R6-04 — `xargs` runs a command line assembled from stdin.  This
        form is live in scripts/measure-repo-size.sh."""
        c = self.census({"r604c.sh": sh("""
deliver() {
  printf '%s' "$SRC" | xargs wc -l
}
""")})
        site = c.at("r604c.sh", "xargs")
        self.assertTrue(site["blocking"], c.describe())
        self.assertEqual("i-opaque-command", site["form"], c.describe())

    def test_r6_04_a_shell_handed_a_script_is_opaque(self) -> None:
        """R6-04 — `bash -c STRING` and `bash SCRIPT` both run text this model
        never reads.  Live in scripts/install.sh."""
        c = self.census({"r604d.sh": sh("""
deliver() {
  bash -c 'cp "$SRC" "$DST"'
}
""")})
        site = c.at("r604d.sh", "bash")
        self.assertTrue(site["blocking"], c.describe())
        self.assertEqual("i-opaque-command", site["form"], c.describe())

    def test_r6_04_opaque_does_not_cap_a_proven_write(self) -> None:
        """R6-04 — opaque FLOORS the verdict at indeterminate, it does not CAP
        it: a redirection the model DID prove keeps `desguardado`.  Collapsing
        every opaque command to "indeterminate" would discard a write the
        instrument actually knows about (live: smoke-install-parity.sh:126)."""
        c = self.census({"r604e.sh": sh("""
deliver() {
  local dst="$1"
  bash .claude/run.sh >"$dst" 2>&1
}
""")})
        site = c.at("r604e.sh", "bash .claude/run.sh")
        self.assertEqual("desguardado", site["verdict"], c.describe())

    def test_r6_04_a_shell_running_nothing_of_ours_is_not_a_site(self) -> None:
        """Negative control: `bash --version` is handed no script.  Without
        this the cure would emit a site for every mention of a shell."""
        c = self.census({"r604f.sh": sh("""
deliver() {
  bash --version
}
""")})
        self.assertEqual([], [s for s in c.sites("r604f.sh")], c.describe())

    def test_r6_04_a_literal_redirection_is_not_a_proven_write(self) -> None:
        """Negative control: `2>/dev/null` on an opaque command is a literal
        path the SCRIPT chose — the outer shell resolves it, so the discovery
        narrowing still applies.  Crediting it as a proven unguarded write was
        a blocking false positive this pass introduced and then removed."""
        c = self.census({"r604g.sh": sh("""
deliver() {
  printf '%s' "$SRC" | xargs wc -l 2>/dev/null
}
""")})
        site = c.at("r604g.sh", "xargs")
        self.assertEqual("indeterminado", site["verdict"], c.describe())
        self.assertEqual("i-opaque-command", site["form"], c.describe())

    # -- R6-05: quoted regex RHS ----------------------------------------

    def test_r6_05_a_quoted_regex_is_not_validation(self) -> None:
        """R6-05 — bash treats a QUOTED `=~` right-hand side as a literal
        STRING.  `[[ "$v" =~ "^[A-Za-z]+$" ]]` accepts every value except the
        literal regex text, yet was credited as closed-charset validation."""
        c = self.census({"r605.sh": sh("""
build() {
  local v="$1"
  [[ "$v" =~ "^[A-Za-z]+$" ]] || exit 1
  sed "s|x|$v|g" "$SRC"
}
""")})
        self.assertBlocks(c, "r605.sh", 'sed "s|x|', cls="sed-interp")

    def test_r6_05_an_unquoted_regex_is_still_validation(self) -> None:
        """Negative control: the UNQUOTED form really is a regex, and b2 must
        still prove it."""
        c = self.census({"r605b.sh": sh("""
build() {
  local v="$1"
  [[ "$v" =~ ^[A-Za-z]+$ ]] || exit 1
  sed "s|x|$v|g" "$SRC"
}
""")})
        self.assertSafe(c, "r605b.sh", 'sed "s|x|',
                        "b2-closed-charset-validated", cls="sed-interp")

    # -- R6-06: braces are syntax only in command position ---------------

    def test_r6_06_a_brace_outside_command_position_is_an_operand(self) -> None:
        """R6-06 — an unquoted `{` is a reserved word only in command
        position.  `tee { "$dst"` writes BOTH files, but splitting there tore
        `tee` from its destination and the write disappeared."""
        c = self.census({"r606.sh": sh("""
deliver() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  printf data | tee { "$dst"
}
""")})
        self.assertBlocks(c, "r606.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")

    def test_r6_06_a_function_body_brace_still_opens_a_group(self) -> None:
        """Negative control: after a function header's `)` the brace IS in
        command position, so the body is still analysed as commands of its
        own.  Losing this would make every helper in the corpus opaque."""
        c = self.census({"r606b.sh": sh("""
deliver() { cp "$SRC" "$1"; }
""")})
        site = c.at("r606b.sh", "cp ")
        self.assertEqual("write-candidate", site["class"], c.describe())

    # -- R6-07: `patch -i` is an INPUT ----------------------------------

    def test_r6_07_patch_input_option_is_a_read(self) -> None:
        """R6-07 — `patch -i FILE` READS the patch document.  Listing it as a
        destination reported `$patchfile` as an unguarded write: a blocking
        FALSE POSITIVE.  This is the only block this pass removes."""
        c = self.census({"r607.sh": sh("""
apply() {
  local patchfile="$1"
  if [ -e "$patchfile" ]; then
    patch -i "$patchfile" /fixed/target
  fi
}
""")})
        self.assertSafe(c, "r607.sh", '[ -e "$patchfile" ]',
                        "a3-no-write-to-operand", cls="symlink-follow")

    def test_r6_07_positional_patch_target_still_blocks(self) -> None:
        """R6-07 — paired positive control for the removal above: the
        POSITIONAL target of `patch` is still a destination, so the fix cannot
        widen into an amnesty for `patch`."""
        c = self.census({"r607b.sh": sh("""
apply() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  patch "$dst" "$SRC"
}
""")})
        self.assertBlocks(c, "r607b.sh", '[ -e "$dst" ]', "desguardado",
                          cls="symlink-follow")


class TestFailClosedDiscovery(CensusCase):
    """The 5th pass's architectural change, asserted in both directions.

    Discovery is now the ALLOWLIST: a command is skipped only when its name is
    PROVEN read-only.  Each rule below has a positive control (the form is
    seen) and a negative one (the proven-safe shape produces no site, so the
    census has not degenerated into flagging every line).
    """

    def test_an_unknown_command_with_an_expansion_is_a_candidate(self) -> None:
        c = self.census({"d1.sh": sh("""
deliver() {
  local dst="$1"
  some_unmodelled_tool --out "$dst"
}
""")})
        site = self.assertBlocks(c, "d1.sh", "some_unmodelled_tool",
                                 "indeterminado", cls="write-candidate")
        self.assertEqual("i-write-candidate-unproven", site["form"])

    def test_a_proven_readonly_command_produces_no_candidate(self) -> None:
        """The negative control that keeps the rule honest."""
        c = self.census({"d2.sh": sh("""
check() {
  local d="$1"
  grep -q foo "$d"
  echo "$d"
  basename "$d"
}
""")})
        self.assertEqual([], c.sites("d2.sh"), c.describe())

    def test_a_literal_path_is_not_a_candidate(self) -> None:
        """Discovery narrows on EXPANSION, the one property the threat model
        cares about: a fully literal destination is chosen by the script."""
        c = self.census({"d3.sh": sh("""
deliver() {
  cp /a/fixed/src /a/fixed/dst
}
""")})
        self.assertEqual([], c.sites("d3.sh"), c.describe())

    def test_eval_is_always_a_candidate(self) -> None:
        c = self.census({"d4.sh": sh("""
deliver() {
  eval "$1"
}
""")})
        site = self.assertBlocks(c, "d4.sh", "eval", "indeterminado",
                                 cls="write-candidate")
        self.assertEqual("i-opaque-command", site["form"])

    def test_a_write_no_test_ever_pointed_at_is_still_found(self) -> None:
        """The whole point of the class: before it, a site existed only where
        some `-e`/`-f` test had already named the path."""
        c = self.census({"d5.sh": sh("""
deliver() {
  local dst="$1"
  cp "$SRC" "$dst"
}
""")})
        site = self.assertBlocks(c, "d5.sh", 'cp "$SRC" "$dst"', "desguardado",
                                 cls="write-candidate")
        self.assertIn("$dst", site["detail"])

    def test_a_guarded_write_with_no_test_is_proven_safe(self) -> None:
        """Negative control for the line above."""
        c = self.census({"d6.sh": sh("""
deliver() {
  local dst="$1"
  [ -L "$dst" ] && return 1
  cp "$SRC" "$dst"
}
""")})
        self.assertSafe(c, "d6.sh", 'cp "$SRC" "$dst"',
                        "a1-nofollow-test-dominates", cls="write-candidate")

    def test_a_reading_command_is_not_reported_as_writing(self) -> None:
        """A proven destination and an unplaceable operand are different
        facts: `diff -q "$a" "$b" >/dev/null` writes neither operand."""
        c = self.census({"d7.sh": sh("""
compare() {
  local a="$1"
  local b="$2"
  diff -q "$a" "$b" >/dev/null 2>&1
}
""")})
        site = self.assertBlocks(c, "d7.sh", "diff -q", "indeterminado",
                                 cls="write-candidate")
        self.assertEqual("i-write-candidate-unproven", site["form"])

    def test_a_local_helper_that_only_logs_is_not_a_candidate(self) -> None:
        """Depth-one interprocedural analysis, same as class A: a callee whose
        positionals are only ever READ clears its callers, even when it
        reshuffles them with `$*`."""
        c = self.census({"d8.sh": sh("""
_log() { printf '%s\\n' "$*"; }

deliver() {
  local dst="$1"
  _log "target: $dst"
}
""")})
        self.assertEqual([], [s for s in c.sites("d8.sh")
                              if "_log" in s["operand"]], c.describe())

    def test_a_local_helper_that_writes_is_a_candidate(self) -> None:
        """Negative control for the line above: the NAME is never evidence."""
        c = self.census({"d9.sh": sh("""
_log() { cp "$SRC" "$1"; }

deliver() {
  local dst="$1"
  _log "$dst"
}
""")})
        hits = [s for s in c.sites("d9.sh")
                if s["class"] == "write-candidate" and s["blocking"]
                and s["line"] >= 8]
        self.assertTrue(hits, c.describe())

    def test_mkdir_p_writes_through_a_symlinked_component(self) -> None:
        """Pass-2 self-audit of the 5th pass: `mkdir` was declared benign
        because it cannot write through a link — true of the FINAL component
        only.  `mkdir -p "$dst/sub"` resolves `$dst` and creates `sub` on the
        other side of it, and the probe returned NO SITE for that line."""
        c = self.census({"d11.sh": sh("""
deliver() {
  local dst="$1"
  mkdir -p "$dst/sub"
}
""")})
        self.assertBlocks(c, "d11.sh", "mkdir -p", "desguardado",
                          cls="write-candidate")

    def test_a_guarded_mkdir_is_still_proven_safe(self) -> None:
        c = self.census({"d12.sh": sh("""
deliver() {
  local dst="$1"
  [ -L "$dst" ] && return 1
  mkdir -p "$dst"
}
""")})
        self.assertSafe(c, "d12.sh", "mkdir -p", "a1-nofollow-test-dominates",
                        cls="write-candidate")

    def test_rmdir_is_decided_by_the_operand_not_the_name(self) -> None:
        """`rmdir "$d"` removes the LINK; `rmdir "$d/"` acts on its target."""
        plain = self.census({"d13.sh": sh("""
deliver() {
  local d="$1"
  rmdir "$d"
}
""")})
        self.assertEqual([], plain.sites("d13.sh"), plain.describe())
        slashed = self.census({"d14.sh": sh("""
deliver() {
  local d="$1"
  rmdir "$d/"
}
""")})
        self.assertBlocks(slashed, "d14.sh", 'rmdir "$d/"', "desguardado",
                          cls="write-candidate")

    def test_a_function_definition_is_not_a_call(self) -> None:
        """`_log() { printf ... }` names no command; reading its head as one
        made every helper in the corpus a candidate write."""
        c = self.census({"d10.sh": sh("""
_emit() { printf '%s\\n' "$1"; }
""")})
        self.assertEqual([], c.sites("d10.sh"), c.describe())


class TestParseIsFailClosed(CensusCase):
    def test_unterminated_quote_makes_the_file_block(self) -> None:
        c = self.census({"bad.sh": HEAD + 'echo "never closed\n'})
        sites = c.sites("bad.sh")
        self.assertTrue(sites, "an unparseable file must still emit a site")
        self.assertTrue(all(s["blocking"] for s in sites), c.describe())
        self.assertEqual("parse", sites[0]["class"])

    def test_unbalanced_block_makes_the_file_block(self) -> None:
        c = self.census({"bad.sh": sh("""
deliver() {
  if [ -e "$d" ]; then
    cp "$SRC" "$d"
}
""")})
        self.assertTrue(all(s["blocking"] for s in c.sites("bad.sh")),
                        c.describe())

    def test_a_parse_failure_never_hides_the_other_files(self) -> None:
        c = self.census({
            "bad.sh": HEAD + "echo 'unterminated\n",
            "good.sh": TestFormA1NofollowTestDominates.MUTATED,
        })
        self.assertTrue(c.blocking("bad.sh"))
        self.assertTrue(c.blocking("good.sh"))

    def test_undecodable_file_blocks_rather_than_being_skipped(self) -> None:
        root = self.tmp / "corpus"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "raw.sh").write_bytes(b"#!/bin/sh\ncp \xff\xfe x\n")
        bl = root / "baseline.txt"
        bl.write_text("", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(CENSUS), "--repo-root", str(root),
             "--baseline", str(bl), "--json"],
            capture_output=True, text=True)
        payload = json.loads(proc.stdout)
        sites = [s for s in payload["sites"] if s["path"].endswith("raw.sh")]
        self.assertTrue(sites)
        self.assertTrue(all(s["blocking"] for s in sites))


# --------------------------------------------------------------------------
# D. the gate contract
# --------------------------------------------------------------------------


class TestGateContract(CensusCase):
    UNGUARDED = TestFormA1NofollowTestDominates.MUTATED

    def test_zero_sites_fails_with_exit_2(self) -> None:
        """A corpus with no sites is a BROKEN SEARCH, never a clean repo."""
        c = self.census({})
        self.assertEqual(2, c.rc, c.stdout + c.stderr)

    def test_a_new_blocking_site_fails_with_exit_1(self) -> None:
        c = self.census({"g.sh": self.UNGUARDED})
        self.assertEqual(1, c.rc, c.describe())
        self.assertTrue(c.payload["new_blocking"])

    def test_a_recorded_site_passes_with_exit_0(self) -> None:
        first = self.census({"g.sh": self.UNGUARDED})
        entries = "\n".join(
            "%s:%d:%s:%s:%s:%s" % (s["path"], s["line"], s["class"],
                                   s["verdict"], s["form"] or "-",
                                   s["fingerprint"])
            for s in first.blocking())
        second = self.census({"g.sh": self.UNGUARDED},
                             baseline_text=entries + "\n")
        self.assertEqual(0, second.rc, second.stdout + second.stderr)

    def test_a_dead_baseline_entry_fails(self) -> None:
        """Rot is drift too: an entry matching nothing must not sit forever."""
        c = self.census(
            {"g.sh": self.UNGUARDED},
            baseline_text="scripts/gone.sh:1:symlink-follow:desguardado:-:dead0000dead0000\n")
        self.assertEqual(1, c.rc)
        self.assertTrue(c.payload["dead_baseline_entries"])

    def test_strict_does_not_let_the_baseline_waive_indeterminate(self) -> None:
        files = {"g.sh": sh("""
deliver() {
  local d="$1"
  if [ -e "$d" ]; then
    return 0
  fi
  some_external_tool --into "$d"
}
""")}
        first = self.census(files)
        entries = "\n".join(
            "%s:%d:%s:%s:%s:%s" % (s["path"], s["line"], s["class"],
                                   s["verdict"], s["form"] or "-",
                                   s["fingerprint"])
            for s in first.blocking())
        self.assertTrue(entries, first.describe())
        ok = self.census(files, baseline_text=entries + "\n")
        self.assertEqual(0, ok.rc, ok.stdout)
        strict = self.census(files, args=("--strict",),
                             baseline_text=entries + "\n")
        self.assertEqual(1, strict.rc, strict.stdout)
        self.assertTrue(strict.payload["strict_indeterminate"])

    def test_baseline_is_never_regenerated_implicitly(self) -> None:
        c = self.census({"g.sh": self.UNGUARDED})
        self.assertEqual(1, c.rc)
        self.assertEqual("", (c.root / "baseline.txt").read_text())

    def test_identical_sites_get_distinct_fingerprints(self) -> None:
        """Three byte-identical predicates guarding three identical copies
        must occupy three baseline rows.  Collapsing them onto one key is how
        a FOURTH identical defect would have matched an existing entry and
        left the gate green."""
        c = self.census({"twins.sh": sh("""
one() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}

two() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}

three() {
  local dst="$1"
  if [ -e "$dst" ]; then
    return 0
  fi
  cp "$SRC" "$dst"
}
""")})
        blocking = c.blocking("twins.sh")
        # Six, not three: the 5th pass sees each `cp` as a write candidate in
        # its own right, independently of the `-e` test that points at it.
        # The distinctness claim is what this test is for, and it holds per
        # class and across them.
        self.assertEqual(
            3, len([s for s in blocking if s["class"] == "symlink-follow"]),
            c.describe())
        self.assertEqual(
            3, len([s for s in blocking if s["class"] == "write-candidate"]),
            c.describe())
        self.assertEqual(6, len(blocking), c.describe())
        self.assertEqual(6, len({s["fingerprint"] for s in blocking}))

    def test_rules_surface_lists_every_allowlisted_form(self) -> None:
        proc = subprocess.run([sys.executable, str(CENSUS), "--rules"],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode)
        for form in ("a1-nofollow-test-dominates", "a2-nofollow-helper-dominates",
                     "a3-no-write-to-operand", "b1-delimiter-escape-dominates",
                     "b2-closed-charset-validated", "b3-literal-only",
                     "b4-inline-escape-substitution", "n0-no-interpolation"):
            self.assertIn(form, proc.stdout)


# --------------------------------------------------------------------------
# E. the live corpus
# --------------------------------------------------------------------------


def _live(*args: str) -> Tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(CENSUS), "--json"] + list(args),
                          capture_output=True, text=True, cwd=str(REPO))
    return proc.returncode, json.loads(proc.stdout)


class TestLiveCorpus(TestEnvContext):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rc, cls.payload = _live()

    def test_census_is_green_against_the_tracked_baseline(self) -> None:
        self.assertEqual(
            0, self.rc,
            "new blocking sites: %s\ndead entries: %s"
            % (json.dumps(self.payload.get("new_blocking"), indent=2)[:2000],
               self.payload.get("dead_baseline_entries")))

    def test_the_search_is_not_broken(self) -> None:
        self.assertGreater(self.payload["counts"]["sites"], 100)
        self.assertGreater(self.payload["counts"]["blocking"], 0)

    def test_f1_the_reported_symlink_site_is_unguarded(self) -> None:
        """`install_docs_template`'s `[[ -e "$dst" ]]` before its `cp`."""
        hits = [s for s in self.payload["sites"]
                if s["function"] == "install_docs_template"
                and s["class"] == "symlink-follow"
                and s["verdict"] == "desguardado"]
        self.assertTrue(hits, "F1 must still be found, and found UNGUARDED")

    def test_f2_the_reported_sed_site_is_unguarded(self) -> None:
        hits = [s for s in self.payload["sites"]
                if s["function"] == "install_github_templates"
                and s["class"] == "sed-interp"
                and s["verdict"] == "desguardado"]
        self.assertTrue(hits, "F2 must still be found, and found UNGUARDED")

    def test_f1_has_siblings_the_plan_did_not_name(self) -> None:
        """PLAN-185 §1 named one site; the census found the same shape in
        several functions.  Curing only the named one leaves the class alive."""
        funcs = {s["function"] for s in self.payload["sites"]
                 if s["class"] == "symlink-follow"
                 and s["verdict"] == "desguardado"
                 and s["path"].endswith("install" + ".sh")}
        self.assertGreaterEqual(len(funcs), 3, sorted(funcs))

    def test_the_upgrade_sed_site_is_recorded(self) -> None:
        """The site five rail rounds reported as missing from the baseline."""
        hits = [s for s in self.payload["sites"]
                if s["class"] == "sed-interp"
                and s["verdict"] == "desguardado"
                and s["path"].endswith("upgrade" + ".sh")]
        self.assertTrue(hits, "the upgrade sed-interp site must be found")

    def test_every_blocking_site_is_in_the_tracked_baseline(self) -> None:
        recorded = set()
        for raw in BASELINE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.rsplit(":", 5)
            if len(parts) == 6:
                recorded.add((parts[0], parts[2], parts[5]))
        missing = [s for s in self.payload["sites"] if s["blocking"]
                   and (s["path"], s["class"], s["fingerprint"]) not in recorded]
        self.assertEqual([], [(s["path"], s["line"]) for s in missing])

    def test_the_corpus_still_proves_some_sites_safe(self) -> None:
        """A census that blocked everything would pass every positive control
        above and still be useless.  The live corpus must exercise the
        allowlist, not just the blocking path."""
        self.assertGreater(self.payload["counts"]["nao-aplicavel"], 50)
        self.assertGreater(self.payload["counts"]["guardado"], 0)


if __name__ == "__main__":
    unittest.main()
