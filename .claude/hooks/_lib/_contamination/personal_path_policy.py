"""Rule 2 waiver, verdict and presentation helpers."""
from __future__ import annotations

from .personal_path_rows import _emit_personal_path_rows, _personal_path_mask_owner

import re
from typing import Dict, List, Tuple

_PERSONAL_PATH_ROW_RE = re.compile(
    r"^([^\s|]+)\s*\|\s*sha256:([0-9A-Fa-f]{64})\s*\|\s*(\S.*)$")


#: How many ASCII letters or digits a written reason must carry, counted
#: after NFKC. Eight is a WORD, not a mark: no filler, no combining mark
#: and no invisible codepoint reaches it, whatever category a future
#: Unicode revision puts it in. MEASURED on the shipped allowlist before
#: choosing the number: the seven reasons carry 60 to 112 each.
_PERSONAL_PATH_REASON_MIN_INK = 8


def _personal_path_reason_is_visible(reason: str) -> bool:
    r"""True when ``reason`` is a decision a reviewer can actually READ.

    TWO POSITIVE conditions. Neither is a list of what is forbidden, and
    that is the whole point. The deny-list form of this predicate was
    defeated three rounds running, each time by a character one category
    further out: `Cf` zero-width and bidi (round 19), `Mn` combining
    marks (round 20), and then `Lo`/`So` fillers -- U+3164 HANGUL
    FILLER, U+115F, U+2800 BRAILLE PATTERN BLANK -- which "carry ink" by
    category and render as nothing (round 21). Enumerating categories
    cannot close a class whose next member has not been named yet.
    Asking what a written sentence HAS can.

    * after NFKC, at least `_PERSONAL_PATH_REASON_MIN_INK` characters
      from `[A-Za-z0-9]`. ASCII only, and COUNTED rather than merely
      present: eight letters or digits is a word somebody typed. Every
      filler of every category contributes ZERO, so the whole family
      closes at once, including its unnamed members. NFKC runs first so
      a full-width or mathematical spelling counts as the word it is --
      the same folding the path predicate already asks for;
    * every character PRINTABLE, `str.isprintable()`. That is the
      stdlib's own answer rather than a category list of this module's:
      False for C0/C1 controls, for the format characters, for the
      separators other than a plain space, and for whatever a later
      Unicode revision adds to those. It keeps the round-19 finding
      closed -- `reviewed 2026<CR>HIDDEN` carries EIGHTEEN ASCII
      letters and digits, more than twice the threshold, and is still
      refused because it renders as a row overwritten in the terminal
      that shows it. That is the case which proves the two conditions
      are not redundant: ink alone would pass it. And it is done without
      this module owning a list of what is invisible.

    `\r` is excluded from the FILE-level class two hundred lines up and
    refused HERE, and that is not an inconsistency: there it is the
    terminator of a physical line the row loop counts, and here it is a
    character somebody put inside a written decision.

    A row whose reason fails this is MALFORMED by row NUMBER, which is
    the address the operator can act on, and it waives nothing.
    """
    if not reason.isprintable():
        return False
    folded = unicodedata.normalize("NFKC", reason)
    ink = sum(
        1 for char in folded
        if ("0" <= char <= "9") or ("A" <= char <= "Z")
        or ("a" <= char <= "z")
    )
    return ink >= _PERSONAL_PATH_REASON_MIN_INK


def _personal_path_allowlist_is_tracked(
    repo_root: Path, allowlist_path: Path,
) -> bool:
    """True only when git CONFIRMS the allowlist is in the index.

    Every waiver in this rule -- and there is exactly one kind, the
    content-pinned `<path> | sha256:<64 hex> | <reason>` row -- rests on
    ONE claim: the allowlist is a TRACKED file, so a waiver is something
    somebody COMMITTED and not something somebody left in a working tree.
    Nothing checked that claim. The parser asked `is_file()` and read the
    bytes; git was never consulted, in a rule that asks git every other
    question it has.

    This used to say "a reviewable DIFF", and the r13 decision removed
    that premise: whether the file RENDERS in `git diff` is no longer a
    property this rule rests on, because four rail rounds showed it can
    be taken away by whoever controls the repository. What survives is
    the smaller, checkable claim above -- an untracked file is not a
    decision anybody recorded -- and the visibility of what was granted
    now comes from `_personal_path_honoured_rows`, which prints it.

    MEASURED on the framework's own tree (cross-vendor lane, S344, P2):
    `git rm --cached` the allowlist and the file is still on disk, byte for
    byte, unknown to git -- and the gate still waived 242 files. A claim a
    security matcher does not check is not a
    control, it is a comment.

    Fail-CLOSED, by the rule `_personal_path_assert_enumerable` already
    states: this is a GATE, not a hook, so an answer git cannot give is not
    a yes. Git missing, git timing out, git exiting non-zero, a path
    OUTSIDE the repository, a SYMLINK anywhere between the file and the
    root, an ancestor walk that ran out of budget, and an index mode that
    is not a regular blob all read as NOT tracked -- and an untracked
    allowlist is read as EMPTY, exactly like an absent one, so every hit
    is unwaived.

    HONEST LIMIT, declared in the header: TRACKED is not COMMITTED. An
    uncommitted edit to a tracked allowlist still grants, because that edit
    IS a `git diff` -- the reviewable artifact the claim was always about --
    and refusing it would make "add the row, run the gate, commit it in the
    same change" impossible to do in that order.
    """
    # A SYMLINK is not the file it points at. `resolve()` follows it, so an
    # UNTRACKED link aimed at a tracked file answered TRACKED and its rows
    # were then trusted — a waiver channel opened by a
    # `ln -s` nobody reviewed (pair-rail round 2, P1). Every component
    # between the repository and the file is asked, not just the last: a
    # linked PARENT directory redirects the path just as completely.
    #
    # ROUND 3 hardened this same block twice more, so it is written here
    # in its final form rather than patched again downstream: the budget
    # is a REFUSAL when exhausted (P1), and the catch is a BOUNDARY
    # because `resolve()` raises a bare RuntimeError for a symlink loop
    # on Python 3.9 (P2, both lanes).
    try:
        probe = allowlist_path
        root_real = repo_root.resolve()
        reached_root = False
        for _ in range(_PERSONAL_PATH_ANCESTOR_CAP):
            if probe.is_symlink():
                return False
            if probe.resolve() == root_real or probe.parent == probe:
                reached_root = True
                break
            probe = probe.parent
        if not reached_root:
            # The budget was EXHAUSTED, not satisfied. Falling through
            # here left the remaining ancestors unexamined, so an
            # allowlist deeper than the cap below an untracked link was
            # resolved THROUGH that link and git confirmed the TARGET
            # (pair-rail round 3, P1). A check that runs out of budget
            # is an unfinished check, and an unfinished check in a
            # security matcher is a no.
            return False
    except Exception:
        # A BOUNDARY, not a type list -- the fourth time in this file.
        # `Path.resolve()` raises a bare RuntimeError for a symlink LOOP
        # on Python 3.9, so `except OSError` let an rc-1 traceback
        # carrying the supplied absolute path escape from here
        # (pair-rail round 3, P2, both lanes).
        return False
    try:
        rel = allowlist_path.resolve().relative_to(
            repo_root.resolve()).as_posix()
    except Exception:
        # Outside the repository, so git is not its reviewer and nothing in
        # it can be a reviewable diff. `--personal-path-allowlist` still
        # NAMES the file in the report; it simply waives nothing.
        return False
    # `--` ends OPTION parsing; it does not make the operand LITERAL. An
    # allowlist path containing pathspec magic — `allow-*.txt`, or an
    # explicit `:(glob)` — matched OTHER tracked files, so an untracked
    # file answered TRACKED and its rows were then
    # trusted (pair-rail round 1, P1, both lanes; reproduced with a
    # nonexistent path literally named `*`). Two independent defences:
    # `:(literal)` magic, and a check that what came back is EXACTLY the
    # one path asked about — the second holds even where the first is
    # unsupported.
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z", "--error-unmatch",
             "--", ":(literal)" + rel],
            cwd=str(repo_root), capture_output=True, check=False, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if proc.returncode != 0:
        return False
    listed = [name for name
              in proc.stdout.decode("utf-8", errors="replace").split("\0")
              if name]
    if listed != [rel]:
        return False
    # The INDEX MODE, not the filesystem. Under `core.symlinks=false`
    # git materialises a mode-120000 entry as a REGULAR FILE whose
    # content is the target string: `is_symlink()` above answers False
    # for a link, git confirms the NAME, and a link payload shaped like
    # a valid waiver row was parsed and GRANTED -- a leaking file got a
    # clean verdict (pair-rail round 3, P1, both lanes; reproduced on
    # disk). This is the round-1 lesson -- link status comes from the
    # index, never from the filesystem -- applied to the SECOND of the
    # two surfaces that needed it. Only a regular blob can be an
    # allowlist; 120000, the 160000 gitlink and any mode added later
    # are refused, so the answer does not depend on this checkout's
    # `core.symlinks` setting.
    try:
        mode = _personal_path_index_modes(repo_root).get(rel)
    except Exception:
        # A SECOND git call, with a second way to fail. It is outside
        # the caller's scan boundary, so an escape here was an rc-1
        # traceback instead of the documented empty-allowlist behaviour
        # (pair-rail round 4, P2, both lanes). An answer git cannot
        # give is not a yes -- the same rule as every branch above.
        return False
    return mode in ("100644", "100755")


def personal_path_verdict(
    scan: PersonalPathScan,
    allowlist: Dict[str, "PersonalPathRow"],
    malformed: Optional[List[int]] = None,
) -> PersonalPathVerdict:
    """Split ``scan`` against the allowlist. Kept pure so tests drive it.

    There is ONE waiver -- a row pinned to the content's sha256 -- and a
    NAME hit short-circuits it: a path that names a home directory is
    unwaivable by a row and by anything a future version adds here,
    because the check sits above every branch that could forgive.
    Renaming the file is the only cure, which is what the report tells
    the reader.

    A row that names the file but pins OTHER bytes does not waive and
    does not fall through to "unwaived" either: it is `mismatched`, its
    own category, because the operator action is to re-read the file and
    re-record the digest rather than to write a fresh decision. A hit
    with no digest at all (nothing readable to pin) can never match a
    row, which is the fail-closed default.
    """
    unwaived: List[PersonalPathHit] = []
    waived: List[Tuple[str, str]] = []
    mismatched: List[str] = []
    for hit in scan.hits:
        if _PERSONAL_PATH_NAME_LINE in hit.lines:
            unwaived.append(hit)
            continue
        row = allowlist.get(hit.rel)
        if row is None:
            unwaived.append(hit)
            continue
        if hit.sha256 is None or row.sha256 != hit.sha256:
            mismatched.append(hit.rel)
            continue
        waived.append((hit.rel, row.reason))
    found = set(hit.rel for hit in scan.hits)
    stale = sorted(rel for rel in allowlist if rel not in found)
    return PersonalPathVerdict(
        unwaived=unwaived, waived=waived, stale=stale,
        malformed=list(malformed or []), mismatched=sorted(mismatched),
    )


def _report_personal_path_eol_suspicion(
    scan: "PersonalPathScan", allowlist: Dict[str, "PersonalPathRow"],
    verdict: "PersonalPathVerdict",
) -> None:
    """Name a mismatch that a checkout EOL filter explains.

    A clone with `core.autocrlf=true` (or any other checkout EOL
    filter) hands the worktree CRLF where the committed blob holds LF.
    Every shipped digest was taken over the LF bytes, so on such a
    checkout every row mismatches at once and the gate is permanently
    red for a reason nothing in its output explains -- the operator
    looks for an edit that was never made (pair-rail round 3, P2).

    It states WHAT was observed and not WHY: a deliberate CRLF edit
    produces the same evidence as a checkout filter, and the earlier
    wording asserted the filter (pair-rail round 4, P3).

    NOTHING IS WAIVED HERE. Waiving on the normalised digest would
    forgive bytes the scan did not hash, which is the one thing this
    rule refuses to do; hashing canonical git content instead is the
    index-vs-worktree boundary this pack declares and does not cross.
    So the verdict is unchanged -- rc 1, the files still named -- and
    this adds one line saying which knob to turn.
    """
    by_rel = dict((hit.rel, hit) for hit in scan.hits)
    suspect = [
        rel for rel in verdict.mismatched
        if by_rel.get(rel) is not None
        and by_rel[rel].sha256_lf is not None
        and allowlist.get(rel) is not None
        and allowlist[rel].sha256 == by_rel[rel].sha256_lf
    ]
    if not suspect:
        return
    print("    (%d of those differ from the recorded digest ONLY in "
          "line endings." % len(suspect))
    print("     That is what was observed, not why: a checkout EOL "
          "filter")
    print("     (`core.autocrlf`) and a deliberate CRLF edit look the "
          "same here.")
    print("     If it is the filter, `git config core.autocrlf input` "
          "or a")
    print("     `* text=auto eol=lf` attribute restores the bytes the "
          "digests")
    print("     were taken over. Nothing is waived on the folded "
          "digest.)")


def _print_personal_path_group(
    title: str, rows: List[str], cap: Optional[int] = None,
) -> None:
    """Print at most `cap` rows, then say how many hid. LAYOUT ONLY.

    `cap` defaults to `_PERSONAL_PATH_PRINT_CAP`, the FINDING cap: a
    red run names the first 20 and counts the rest, because the
    operator's next move is to open one of them.

    It does NOT escape. That is the cure for a collision the r13 print
    made reachable (mechanism lane, round 23; reproduced): a path
    becomes text in `_personal_path_mask_rel`, which escapes it, and
    this printer used to escape it AGAIN. Escaping twice is injective on
    its own; escaping twice HERE and once in the honoured block is not,
    because the image of the double escape meets the image of the single
    one -- an unwaived `docs/x<LF>y.md` and a waived file literally named
    `docs/x\x0ay.md` rendered as the same line in the same report.

    So there is ONE boundary and every caller crosses it: a path is
    passed to this function already masked. `title` is composed by this
    module and is not a path, so it is printed as it is written.
    """
    limit = _PERSONAL_PATH_PRINT_CAP if cap is None else cap
    if not rows:
        return
    print("  %s:" % title)
    for row in rows[:limit]:
        print("    - %s" % row)
    if len(rows) > limit:
        print("    ... and %d more" % (len(rows) - limit))


def _personal_path_display(path: Path, repo_root: Path) -> str:
    """``path`` relative to the repo when inside it, else its absolute form.

    The gate refuses to print a matched LINE; printing the absolute path of a
    file under the operator's home would put a home directory back into the
    output through the side door.
    """
    try:
        # MASKED, not returned raw (pair-rail round 2, P2): an in-repo
        # override such as `docs/-Users-<name>-x/allow.txt` put the owner
        # segment into the untracked notice and into the remediation
        # text. Only the OUTSIDE-repo branch went through the boundary,
        # as if a path inside the repository could not name a person.
        return _personal_path_mask_rel(
            path.resolve().relative_to(repo_root).as_posix())
    except Exception:
        # OUTSIDE the repository — `--personal-path-allowlist ~/somewhere`.
        # `str(path)` here was the same leak by the same side door (rail round
        # cure-1, P2): the name is all a reader needs to know WHICH file the
        # gate could not use, and the directory is what must not be printed.
        return "<outside the repository>/%s" % _personal_path_safe(path.name)


#: C0, DEL and C1 — every byte a terminal or a CI log reads as a COMMAND
#: rather than as text. `\n` is the one that matters most here: git allows a
#: newline in a tracked filename, which is why the scan enumerates with `-z`.
def _personal_path_renders_as_itself(value: str) -> bool:
    """True when no character of ``value`` needs escaping to be PRINTED.

    `str.isprintable()`, asked of the whole string, and the claim is
    exactly the stdlib's: False for the control, format, surrogate,
    private-use, unassigned and non-space separator categories. It is
    NOT a promise that every character is visible -- U+2800 BRAILLE
    PATTERN BLANK and U+034F COMBINING GRAPHEME JOINER are printable and
    render as nothing. That is the right shape for what this predicate
    is FOR: escaping, so two different files cannot print as one line,
    and so nothing that rewrites a terminal reaches the log. Invisibility
    is refused where invisibility is the harm -- in the reason
    predicate, which counts ink rather than asking a category. This replaced the
    codepoint range `[\x00-\x1f\x7f-\x9f]`, which named C0, DEL and C1
    and stopped there -- so a tracked filename carrying U+202E
    RIGHT-TO-LEFT OVERRIDE went through the escaper UNCHANGED and printed
    raw into the honoured-row log, the one place a waiver is visible at
    all since the r13 decision (mechanism lane, round 22; reproduced).

    The class was never "C0 plus C1". It is "a character that does not
    render as itself", and the standard library already answers that
    question for every category, including the ones a later Unicode
    revision adds: `Cc`, `Cf`, `Cs`, `Co`, `Cn`, `Zl`, `Zp` and the
    separators other than a plain space. One question, one authority,
    asked by both the escaper and the row emitter so they cannot drift --
    the same removal-not-enumeration move the reason predicate made one
    round earlier.
    """
    return value.isprintable()

#: The same class MINUS the three characters that are ordinary text in a
#: waiver list: `\t`, `\n`, and the `\r` the row loop already counts as
#: part of its physical line. Everything else in C0/DEL/C1 is refused
#: there rather than escaped, because an escaped control is a DIFFERENT
#: string to the row grammar.
#:
#: The harm is DISPLAY, and the claim is deliberately no larger than
#: that: ESC, VT, FF and DEL rewrite how a row renders in the terminal
#: that shows it, so a row can say one thing to this parser and another
#: to its reader. An earlier note here ALSO said a NUL makes git render
#: the whole list as `Binary files ... differ`. That is not a rule git
#: has -- an explicit `diff` attribute forces a text diff despite a NUL
#: (round 21, B3; reproduced, numstat `-/-` becomes `2/0`) -- and this
#: rule no longer rests on how git renders anything: see
#: `_personal_path_honoured_rows`, which states what was granted instead
#: of hoping somebody reads a diff.
_PERSONAL_PATH_ALLOWLIST_CONTROL_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def _personal_path_escape_controls(value: str) -> str:
    r"""``value`` with every character that does not RENDER escaped.

    `\xNN` below U+0100, `\uXXXX` below U+10000, `\UXXXXXXXX` above it,
    so the escape is unambiguous at every width.

    A tracked path may contain a NEWLINE, and this rule prints paths. Printed
    verbatim, `docs/ok<newline>::warning::forged.md` puts a line beginning
    `::warning::` into the log — a GitHub Actions WORKFLOW COMMAND, forged by
    a file in the pull request the gate is judging (mechanism lane, round 12;
    reproduced). ESC sequences reach the same output and can rewrite the
    waived inventory as it is rendered.

    Escaping, not refusing: the operator still has to be able to SEE which
    path it is, and a refusal here would be a second, silent way for a file
    to escape the report.

    INJECTIVE, and that took a second round to get right. Escaping only the
    controls made `docs/x<newline>y.md` and the literal four-character
    `docs/x\x0ay.md` render IDENTICALLY (text lane, round 13; reproduced,
    COLLIDE: True) -- two different tracked files, one line in a report whose
    entire job is naming WHICH file leaked, and a hostile filename able to
    impersonate another one. The escape character is therefore escaped FIRST,
    which is the ordinary cure and the only one that keeps the mapping
    reversible: a backslash becomes two, then a control becomes `\xNN`.

    MEASURED on the shipped allowlist before this shipped: 0 of 242 waived
    paths, 0 of 242 reasons and 0 of 76 comment lines carry a control
    character or a backslash, so a green run prints exactly what it printed
    before.
    """
    out: List[str] = []
    for char in value.replace("\\", "\\\\"):
        if _personal_path_renders_as_itself(char):
            out.append(char)
        elif ord(char) < 0x100:
            out.append("\\x%02x" % ord(char))
        elif ord(char) < 0x10000:
            out.append("\\u%04x" % ord(char))
        else:
            out.append("\\U%08x" % ord(char))
    return "".join(out)


def _personal_path_hit_either(value: str) -> bool:
    """True when the RAW string or its NFKC folding names a home directory.

    Asking only the folded reading is a BYPASS, and it was live in three
    places: the allowlist ROW check, the comment check the round-10 cure
    added, and the redaction choke point below. NFKC turns a full-width
    owner segment into an ASCII one, and the ASCII one may be on the
    PLACEHOLDER list -- so `/Users/<full-width dev>/private`, a real and
    distinct directory, folded into `/Users/dev/private` and answered
    False (text lane, round 12; measured raw=True nfkc=False).

    Folding can only ever turn a person into a placeholder, never a
    placeholder into a person, so the raw reading is the one that must not
    be skipped. Both are asked; either is enough.
    """
    if line_is_personal_path_hit(value):
        return True
    return line_is_personal_path_hit(unicodedata.normalize("NFKC", value))


def _personal_path_safe(value: str) -> str:
    """``value``, unless it names a home directory — then a redaction.

    The choke point for everything this rule PRINTS that it did not
    compose itself: a waiver reason written by a human, an allowlist path
    outside the repository, a CLI token it is about to name as ignored. Each
    of those was measured leaking in its own way; they are one shape, and the
    predicate that decides a FINDING is the same predicate that decides
    whether the gate may echo a string. A rule that redacts what it found and
    prints what it was handed is not a rule about leaks.

    ONE deliberate exception, named here because this docstring used to
    claim there were none (text lane, round 19): the row offered by
    `--emit-personal-path-rows` is not prose, it is a line the PARSER has
    to read back, and the escaping this function does to stay injective --
    a backslash becomes two -- makes that line name a different path. That
    row is built from `hit.rel` under two explicit refusals instead (a path
    that names a home directory, and a path carrying a control character),
    which is the same containment reached without corrupting the key.
    """
    if _personal_path_hit_either(value):
        return "<redacted: names a home directory>"
    # Everything that leaves this function goes into a log a human and a CI
    # runner both read. The redaction above answers "may this be printed";
    # this answers "is what is printed still TEXT" (mechanism lane, round 12).
    return _personal_path_escape_controls(value)




def _personal_path_mask_rel(rel: str) -> str:
    """``rel`` with every NON-PLACEHOLDER home-owner segment replaced.

    A finding a reviewer cannot LOCATE is not a finding, and a PATH hit
    handed straight to `_personal_path_safe` comes back as the whole string
    redacted. So the owner segment -- the only part that is the leak -- is
    replaced and the rest of the path survives. `_personal_path_safe` still
    runs last and owns the verdict: if the masking missed a form, the whole
    string is redacted and the gate loses precision, never containment.
    """
    masked = _PERSONAL_PATH_HOME_RE.sub(
        lambda m: _personal_path_mask_owner(m, "/home/<redacted-owner>"), rel)
    # No trailing `-` in the replacement: since the round-20 cure the
    # terminator is a LOOKAHEAD, so the separator is no longer consumed by
    # the match, and supplying it again rendered
    # `-Users-<redacted-owner>--project`. A mask has to follow the matcher
    # it masks (text lane of the battery, round 20).
    masked = _PERSONAL_PATH_SLUG_RE.sub(
        lambda m: _personal_path_mask_owner(m, "-Users-<redacted-owner>"),
        masked)
    return _personal_path_safe(masked)


def _oserror_reason(exc: Exception) -> str:
    """The REASON an OSError carries — never the path it names.

    `str(OSError)` renders as `[Errno 13] Permission denied: <filename>`, and
    that filename is ABSOLUTE. Printing it on the fatal path puts a home
    directory back into the output through the same side door
    `_personal_path_display` closes three lines up: a gate that refuses to
    quote the leak it found must not leak while REFUSING to scan.

    `strerror` is the reason with no path in it. When it is missing (an
    OSError raised without an errno, or a subclass carrying only args) the
    class name is the most that can be said without quoting a path — a vaguer
    message is a cheaper price than a second copy of the leak. BOTH rules of
    this module use it: the term rule terms-file fatal leaked the same way.

    It also serves `UnicodeDecodeError` (no `strerror`, so: the class name),
    which is why the parameter is typed `Exception`. A decode failure on an
    INPUT file is fatal here, and its str() would quote the offending BYTES.

    And `re.error`, which is the same shape one layer further in: a private
    term is compiled as a RAW REGEX, so a malformed one (`(?P</Users/<name>>)`)
    raises with the offending pattern inside the message — the home path
    the terms file exists to hide, printed by the machinery that hides it
    (pair-rail round 1, P1). Its class name is the bare word `error`, which
    says nothing, so this one case is named instead of classified.
    """
    if isinstance(exc, re.error):
        return "it contains an invalid regular expression"
    strerror = getattr(exc, "strerror", None)
    if strerror:
        return str(strerror)
    return exc.__class__.__name__


def _personal_path_honoured_rows(
    waived: List[Tuple[str, str]],
    allowlist: Dict[str, "PersonalPathRow"],
) -> Tuple[List[str], str]:
    """The row set this run HONOURED, one line each, and a digest over it.

    `<path> | sha256:<64 hex> | <reason>` -- the three fields of the row
    that granted, in the row's own grammar, sorted by path, UNCAPPED.

    This replaced a counted, capped, reason-grouped inventory, and the
    reason is the four rounds that ended in the decision above it.
    Rounds 18 to 21 defended a PREMISE -- that a waiver is reviewable
    because a human can read the allowlist in `git diff` -- and each
    round found another way to make git render that file unreadable: a
    NUL in the bytes, a `-diff` attribute, a named binary driver, a
    driver named `unspecified`, `core.bigFileThreshold=1` with no
    attribute at all. Every cure for those decided by a NAME, which is
    the one thing this rule refuses to do anywhere else.

    So the premise is gone, and with it the question. The gate asks git
    NOTHING about how the list renders. It states what it honoured on
    every run that reaches a VERDICT -- green, red, and on stderr under
    `--emit-personal-path-rows` -- and a reader who never opens a diff
    still sees the waiver that granted. A run that cannot READ its input
    returns 2 before any of this, and prints no set, because at that
    point there is no waiver set to state: an unreadable allowlist waives
    nothing, which is the fail-closed answer and not a silent one. Readability of the allowlist file in
    `git diff` is no longer a security property of this rule -- the
    sha256-pinned row is, and it is unchanged.

    Only rows that actually waived a file appear. A row matching no file
    waives nothing and is reported as stale; a row whose digest no
    longer matches waives nothing and is reported as mismatched.

    The DIGEST is over the canonical `<path>NUL<sha256>NUL<reason>` join
    of that set, in the same order, so two runs are comparable by one
    line. It is computed from the ROW values and not from the printed
    text: masking and escaping are display, and a digest that moved with
    the display would report a waiver change when only a rendering
    changed.

    `allowlist[rel]` cannot miss: `personal_path_verdict` builds every
    pair in ``waived`` from a row it found in this same mapping. Paths
    and reasons go through the maskers on the way OUT, like every other
    printer here, because this report reaches a public CI log.
    """
    canonical: List[str] = []
    rows: List[str] = []
    for rel, reason in sorted(waived):
        sha = allowlist[rel].sha256
        canonical.append("%s\0%s\0%s" % (rel, sha, reason))
        rows.append(
            "%s | sha256:%s | %s"
            % (_personal_path_mask_rel(rel), sha,
               _personal_path_safe(reason)))
    digest = hashlib.sha256(
        "\n".join(canonical).encode("utf-8")).hexdigest()
    return rows, digest


def _print_personal_path_honoured(
    rows: List[str], digest: str, stream,
) -> None:
    """Print the honoured set. No cap: a cap is a place a waiver hides.

    The old inventory was capped at 400 lines and said how many it hid,
    which is fine for a worklist and wrong for THIS: the hidden ones are
    exactly the ones nobody would see. The stream is a parameter because
    `--emit-personal-path-rows` owns stdout for rows meant to be pasted,
    so its copy goes to stderr.
    """
    print("  honoured allowlist rows (%d, set sha256:%s):"
          % (len(rows), digest), file=stream)
    for row in rows:
        print("    %s" % row, file=stream)





__all__ = [
    name for name, value in globals().items()
    if ((name.startswith("_") and not name.startswith("__"))
        or name.startswith("PersonalPath") or name in (
            "personal_path_verdict", "report_personal_paths",
        ))
]
