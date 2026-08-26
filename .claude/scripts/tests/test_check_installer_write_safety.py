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
           operand: Optional[str] = None) -> dict:
        hits = [s for s in self.sites(name) if snippet in s["snippet"]]
        if operand is not None:
            hits = [s for s in hits if operand in s["operand"]]
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
                   form: str, operand: Optional[str] = None) -> dict:
        site = c.at(name, snippet, operand)
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
                     operand: Optional[str] = None) -> dict:
        site = c.at(name, snippet, operand)
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
        self.assertEqual(3, len(blocking), c.describe())
        self.assertEqual(3, len({s["fingerprint"] for s in blocking}))

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
