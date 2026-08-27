#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-installer-write-safety.py — PLAN-185 W0, 5th pass (FAIL-CLOSED DISCOVERY).

Census of two classes of unsafe write in ``scripts/**/*.sh``:

  symlink-follow  a path is decided by a DEREFERENCING file test (-e/-f/-d/...,
                  anything but -L/-h) and is also WRITTEN.  Both a dangling and
                  a resolved symlink at that path make the write land OUTSIDE
                  the tree the installer was given.  (CWE-59 / CWE-61)

  sed-interp      an operator-controlled value is interpolated into a sed/awk
                  substitution without escaping that substitution's delimiter
                  (and & / backslash on the replacement side).  The value
                  aborts the command; because ``>`` created the destination
                  first, the abort leaves a 0-byte file that the EXISTS-skip
                  branch then treats as installed forever.

WHY THIS FILE WAS REWRITTEN TWICE (verdict, then DISCOVERY)
-----------------------------------------------------------
Passes 1..3 worked by *implicit denylist*: they enumerated the syntactic forms
they could recognise and credited ``guardado``/``nao-aplicavel`` to everything
that did not match.  Every form nobody thought of was born fail-OPEN, so every
review round found more of them — 8, then 7, then 9, then 10, then 16.

The 4th pass inverted the VERDICT rule: safety became a THEOREM provable only
by a named form in ALLOWLIST below.  The 5th round of review then returned 16
findings of the SAME class, because inverting the verdict is only half the
job.  DISCOVERY was still a denylist: a site existed only where a recognised
file test or a bare ``sed`` name appeared, so ``test -a "$dst"``,
``/usr/bin/sed``, ``$1``, ``>& "$dst"`` and ``sort -o "$dst"`` produced no site
AT ALL.  An invisible site is worse than a wrongly-cleared one: nothing in the
output says it exists.

This pass makes discovery fail-closed as well.  A command is PROVEN read-only
only if its name is in PROVEN_READONLY and it opens no file for output;
everything else whose operands or redirections carry an expansion is a
CANDIDATE WRITE (class ``write-candidate``) that must be proven safe like any
other site.  A test expression the model cannot walk to the end, an
``eval``/``source``/``exec``, and an unparseable file are sites too.  The
census therefore reports what it does NOT understand, which is the only way a
"no finding" line can mean anything.

Three structural consequences, all deliberate:

0. **Volume went up ~5x, and that is the correct direction.**  The baseline is
   a RATCHET over what the instrument can see, not a list of reviewed defects;
   PLAN-185 W1/W2 is what turns real sites into ``guardado``.  A small baseline
   here would only mean discovery was narrow again.

1. **Reachability analysis is gone.**  The old matcher spent ~600 lines asking
   "is the write reachable when the link dangles?", and answered
   ``nao-aplicavel`` whenever it could not tell.  That question was wrong on
   its own terms: the threat model covers the RESOLVED link too (``-e`` true,
   ``cp`` writes through it, clobbering a file outside the target), so the
   branch a dangling link happens to take never decided safety.  An argument
   about control flow can only make a site MORE dangerous, never safe, so no
   such argument can produce a non-blocking verdict here.  Safety comes from a
   dominating ``-L`` guard or from there being no write at all — nothing else.

2. **Parsing is fail-closed.**  Analysis runs on a real (small) shell lexer and
   a block-scope stack, not on regexes over raw text.  Unbalanced quotes, an
   unterminated heredoc, a block stack that does not close, an unreadable file
   — any of these makes the WHOLE FILE unparseable: it emits a synthetic
   blocking ``parse`` site and every site inside it is ``indeterminado``.

SITE CLASSES
------------
  symlink-follow  a dereferencing file test decides a path that is written.
  sed-interp      a value is interpolated into a stream-editor script.
  write-candidate a command that is not PROVEN read-only touches an expansion.
  parse           the file could not be read or modelled at all.

VERDICTS
--------
  nao-aplicavel   PROVEN: nothing writes the tested path (form a3 / n0).
  guardado        PROVEN: a non-dereferencing guard dominates every write
                  (forms a1, a2), or the interpolation is provably escaped or
                  validated (forms b1, b2, b3).
  desguardado     PROVEN dangerous: a write exists with no dominating guard,
                  or a raw interpolation with no escaping anywhere.
  indeterminado   NOT PROVEN either way.  Blocks.

Both ``desguardado`` and ``indeterminado`` are BLOCKING and must appear in the
tracked baseline.  Being in the baseline means a human LOOKED — never that the
form is tolerated.

EXIT CODES
----------
  0  every blocking site is recorded in the baseline and every baseline entry
     still matches a site.
  1  drift: a blocking site is missing from the baseline, or a baseline entry
     matches nothing (rot), or --strict is on and any site is indeterminate.
  2  the census found ZERO sites.  This FAILS by design: zero means the search
     is broken, not that the corpus is clean.

Python >= 3.9, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]


def instrument_sha256() -> str:
    """This file's own digest.

    A census number published without it is not reproducible: the same corpus
    judged by two versions of this script is two different measurements, and
    this instrument has changed under a reader at least once.
    """
    try:
        return hashlib.sha256(
            Path(__file__).resolve().read_bytes()).hexdigest()
    except OSError:
        return "unavailable"

DEFAULT_SCAN_ROOT = "scripts"
DEFAULT_BASELINE_REL = ".claude/scripts/data/installer-write-safety-baseline.txt"
EXCLUDED_REL_PREFIXES = ("scripts/tests/",)

CLASS_SYMLINK = "symlink-follow"
CLASS_SED = "sed-interp"
CLASS_PARSE = "parse"
# Fail-closed DISCOVERY (5th pass).  A command that is not PROVEN read-only and
# touches an expansion is a candidate write, whether or not anything ever
# tested that path.  Without this class the census could only see writes that
# some `-e`/`-f` test had already pointed at, so the forms nobody tested were
# invisible rather than indeterminate.
CLASS_WRITE = "write-candidate"

VERDICT_GUARDED = "guardado"
VERDICT_UNGUARDED = "desguardado"
VERDICT_INDETERMINATE = "indeterminado"
VERDICT_NA = "nao-aplicavel"

BLOCKING_VERDICTS = (VERDICT_UNGUARDED, VERDICT_INDETERMINATE)

# --------------------------------------------------------------------------
# THE ALLOWLIST.  A site may leave the blocking set ONLY through one of these
# named forms.  Each id is asserted by a positive control in
# .claude/scripts/tests/test_check_installer_write_safety.py: the form with its
# guard present must come out non-blocking, and the same fixture with the guard
# removed or mutated must come out blocking, naming the path.
# --------------------------------------------------------------------------
ALLOWLIST = (
    ("a1-nofollow-test-dominates",
     "A -L/-h test on the same path, whose taken branch aborts at the branch's "
     "own level, on an earlier logical line whose scope path is a prefix of "
     "every write's scope path."),
    ("a2-nofollow-helper-dominates",
     "A call to a helper DEFINED IN THE SAME FILE whose body satisfies a1 for "
     "$1 and whose symlink branch returns a NON-ZERO literal, called as "
     "`helper <path> || <abort>` (or aborting the process outright).  The "
     "helper's body is inspected; its NAME is never evidence."),
    ("a3-no-write-to-operand",
     "Every occurrence of the tested path (and of its one-level aliases) in the "
     "analysis region is at a position proven not to write: a file test, an "
     "argument of a PROVEN_READONLY command, a read redirection, or the SOURCE "
     "operand of a known writer.  A single occurrence the model cannot place "
     "voids the proof."),
    ("a4-confinement-predicate-dominates",
     "A dominating call to a predicate DEFINED EXACTLY ONCE in the scanned "
     "corpus -- another file is fine -- whose BODY applies a "
     "non-dereferencing check to a path built from its own positional "
     "parameters and has an explicit refusal path, called in a modelled "
     "refusal polarity, AND whose arguments COVER the write destination: "
     "either the destination itself or the (root, relpath) pair it is "
     "concatenated from.  Cross-file resolution never credits a NAME -- an "
     "ambiguous or missing definition fails, and so does an argument list "
     "that does not bind the destination."),
    ("b1-delimiter-escape-dominates",
     "Every assignment to the interpolated variable in the region escapes the "
     "delimiter OF THIS SUBSTITUTION (plus & and backslash on the replacement "
     "side) with a replacement that actually inserts a backslash, and at least "
     "one of those assignments dominates the use."),
    ("b2-closed-charset-validated",
     "A dominating validation aborts unless the value matches a literal closed "
     "character class that excludes this substitution's delimiter, &, "
     "backslash and newline."),
    ("b3-literal-only",
     "The substitution contains no expansion at all, or every assignment to the "
     "interpolated variable in the region is a literal free of the delimiter, "
     "& and backslash."),
    ("b4-inline-escape-substitution",
     "The interpolation is a single command substitution that escapes THIS "
     "substitution's delimiter in place (plus & and backslash), with a "
     "replacement that actually inserts a backslash."),
    ("n0-no-interpolation",
     "The stream-editor invocation's script is fully literal and contains no "
     "substitution with an expansion in it."),
)
ALLOWLIST_IDS = frozenset(i for i, _ in ALLOWLIST)

# Reason codes attached to indeterminate verdicts.  Every one of them means
# "the model does not cover this shape", never "this looked fine".
R_PARSE = "i-parse-failed"
R_UNREADABLE = "i-file-unreadable"
R_OCCURRENCE = "i-unmodeled-occurrence"
R_GUARD_NOT_DOM = "i-guard-not-dominating"
R_SCRIPT_DYNAMIC = "i-script-not-literal"
R_SCRIPT_UNPARSED = "i-script-unparsed"
R_CMD_SUBST = "i-command-substitution"
R_ESCAPE_UNPROVEN = "i-escape-unproven"
R_AWK_EXPANSION = "i-awk-program-interpolated"
R_GUARD_STALE = "i-guard-value-rebound"
R_TEST_UNMODELED = "i-unmodeled-test-form"
R_CANDIDATE = "i-write-candidate-unproven"
R_OPAQUE = "i-opaque-command"
R_PRED_AMBIGUOUS = "i-predicate-definition-ambiguous"
R_PRED_ARG_UNBOUND = "i-predicate-arg-unbound"

# --------------------------------------------------------------------------
# Lexer
# --------------------------------------------------------------------------


class ParseError(Exception):
    """The input cannot be modelled.  Always fails CLOSED."""


class Incomplete(ParseError):
    """The logical line needs more physical lines before it can be lexed."""


class Tok(object):
    __slots__ = ("kind", "text", "quoted")

    def __init__(self, kind: str, text: str, quoted: bool = False) -> None:
        self.kind = kind          # "word" | "op"
        self.text = text
        self.quoted = quoted

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "Tok(%s,%r)" % (self.kind, self.text)


_OP_CHARS = set(";|&<>()")

# Longest first.  ``[[``/``]]``/``((``/``))`` are handled separately because
# they need a word-boundary check.
_OPERATORS = (";;&", ";;", ";&", "<<<", "<<-", "<<", ">>", ">&", "<&", ">|",
              "|&", "&&", "||", ";", "|", "&", "(", ")", "<", ">")


def _read_balanced(text: str, i: int, opener: str, closer: str) -> Tuple[int, str]:
    """Consume text[i] == opener up to its matching closer, quotes respected."""
    n = len(text)
    assert text[i] == opener
    depth = 0
    j = i
    while j < n:
        c = text[j]
        if c == "\\":
            if j + 1 >= n:
                raise Incomplete("trailing backslash inside expansion")
            j += 2
            continue
        if c == "'":
            k = text.find("'", j + 1)
            if k < 0:
                raise Incomplete("unterminated single quote inside expansion")
            j = k + 1
            continue
        if c == '"':
            j, _ = _read_dquote(text, j)
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return j + 1, text[i:j + 1]
        j += 1
    raise Incomplete("unterminated %s expansion" % opener)


def _read_dquote(text: str, i: int) -> Tuple[int, str]:
    """Consume a double-quoted segment starting at text[i] == '"'."""
    n = len(text)
    assert text[i] == '"'
    j = i + 1
    while j < n:
        c = text[j]
        if c == "\\":
            if j + 1 >= n:
                raise Incomplete("trailing backslash in double quote")
            j += 2
            continue
        if c == '"':
            return j + 1, text[i:j + 1]
        if c == "$" and j + 1 < n and text[j + 1] == "(":
            j, _ = _read_balanced(text, j + 1, "(", ")")
            continue
        if c == "$" and j + 1 < n and text[j + 1] == "{":
            j, _ = _read_balanced(text, j + 1, "{", "}")
            continue
        if c == "`":
            k = text.find("`", j + 1)
            if k < 0:
                raise Incomplete("unterminated backtick")
            j = k + 1
            continue
        j += 1
    raise Incomplete("unterminated double quote")


def _read_word(text: str, i: int) -> Tuple[str, int, bool]:
    n = len(text)
    out: List[str] = []
    quoted = False
    while i < n:
        c = text[i]
        if c in " \t\n":
            break
        if c == "\\":
            if i + 1 >= n:
                raise Incomplete("trailing backslash")
            if text[i + 1] == "\n":
                i += 2
                continue
            out.append(text[i:i + 2])
            i += 2
            continue
        if c == "'":
            k = text.find("'", i + 1)
            if k < 0:
                raise Incomplete("unterminated single quote")
            out.append(text[i:k + 1])
            i = k + 1
            quoted = True
            continue
        if c == '"':
            i, seg = _read_dquote(text, i)
            out.append(seg)
            quoted = True
            continue
        if c == "$" and i + 1 < n and text[i + 1] == "(":
            i, seg = _read_balanced(text, i + 1, "(", ")")
            out.append("$" + seg)
            continue
        if c == "$" and i + 1 < n and text[i + 1] == "{":
            i, seg = _read_balanced(text, i + 1, "{", "}")
            out.append("$" + seg)
            continue
        if c == "`":
            k = text.find("`", i + 1)
            if k < 0:
                raise Incomplete("unterminated backtick")
            out.append(text[i:k + 1])
            i = k + 1
            continue
        if c == "(" and out and "".join(out).rstrip().endswith("="):
            # `ARR=( ... )` array literal: one word, parens balanced, so a
            # multi-line array joins through Incomplete like any other
            # unterminated construct.
            i, seg = _read_balanced(text, i, "(", ")")
            out.append(seg)
            continue
        if c in _OP_CHARS:
            break
        if text.startswith("]]", i) and not out:
            break
        out.append(c)
        i += 1
    return "".join(out), i, quoted


def _at_word_boundary(text: str, i: int) -> bool:
    return i == 0 or text[i - 1] in " \t\n;|&()"


def lex(text: str) -> List[Tok]:
    """Tokenise one logical line.

    Raises Incomplete when more physical lines are needed, ParseError when the
    input cannot be modelled at all.  Never returns a best-effort result.
    """
    toks: List[Tok] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in " \t":
            i += 1
            continue
        if c == "\n":
            toks.append(Tok("op", "\n"))
            i += 1
            continue
        if c == "\\" and i + 1 < n and text[i + 1] == "\n":
            i += 2
            continue
        if c == "\\" and i + 1 >= n:
            raise Incomplete("trailing backslash")
        if c == "#" and _at_word_boundary(text, i):
            k = text.find("\n", i)
            if k < 0:
                break
            i = k
            continue
        if text.startswith("[[", i) and _at_word_boundary(text, i):
            toks.append(Tok("op", "[["))
            i += 2
            continue
        if text.startswith("]]", i):
            toks.append(Tok("op", "]]"))
            i += 2
            continue
        if (text.startswith("<(", i) or text.startswith(">(", i)):
            # Process substitution is a single operand, not a subshell that the
            # block stack must balance.
            j, seg = _read_balanced(text, i + 1, "(", ")")
            toks.append(Tok("op", text[i] + "(...)"))
            i = j
            continue
        if text.startswith("((", i) and _at_word_boundary(text, i):
            j, seg = _read_balanced(text, i + 1, "(", ")")
            if j < n and text[j] == ")":
                j += 1
            toks.append(Tok("op", "((...))"))
            i = j
            continue
        matched = None
        for op in _OPERATORS:
            if text.startswith(op, i):
                matched = op
                break
        if matched is not None:
            toks.append(Tok("op", matched))
            i += len(matched)
            continue
        word, i2, quoted = _read_word(text, i)
        if i2 == i:
            raise ParseError("lexer made no progress at offset %d" % i)
        toks.append(Tok("word", word, quoted))
        i = i2
    return toks


# --------------------------------------------------------------------------
# Logical lines (continuations joined, heredoc bodies removed)
# --------------------------------------------------------------------------

_RE_HEREDOC_TAG = re.compile(r"^['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?$")


class LogicalLine(object):
    __slots__ = ("lineno", "text", "toks", "scope", "indent", "pattern_upto")

    def __init__(self, lineno: int, text: str, toks: List[Tok]) -> None:
        self.lineno = lineno          # 1-based physical line where it starts
        self.text = text
        self.toks = toks
        self.scope: Tuple[int, ...] = ()
        self.indent = len(text) - len(text.lstrip(" \t"))
        # Token index just past a `case` arm's `)`; everything before it is a
        # PATTERN, which matches but never writes.
        self.pattern_upto = 0

    def snippet(self) -> str:
        return re.sub(r"\s+", " ", self.text).strip()[:200]


def build_logical_lines(raw: str) -> List[LogicalLine]:
    """Join continuations, drop heredoc bodies, lex every logical line.

    Raises ParseError on anything unterminated.  A file that raises here is
    reported unparseable and every site in it blocks.
    """
    phys = raw.split("\n")
    out: List[LogicalLine] = []
    i = 0
    n = len(phys)
    while i < n:
        start = i
        buf = phys[i]
        while True:
            try:
                toks = lex(buf)
                break
            except Incomplete:
                i += 1
                if i >= n:
                    raise ParseError(
                        "unterminated construct starting at line %d" % (start + 1))
                buf = buf + "\n" + phys[i]
        ll = LogicalLine(start + 1, buf, toks)
        out.append(ll)
        # Heredocs opened on this logical line: their bodies follow it.
        tags: List[Tuple[str, bool]] = []
        for j, t in enumerate(toks):
            if t.kind == "op" and t.text in ("<<", "<<-") and j + 1 < len(toks):
                nxt = toks[j + 1]
                if nxt.kind != "word":
                    raise ParseError("heredoc without a tag at line %d" % ll.lineno)
                m = _RE_HEREDOC_TAG.match(nxt.text.strip())
                if not m:
                    # `<<< "here string"` is lexed as `<<` + `<`, not this branch;
                    # anything else is a shape we do not model.
                    raise ParseError("unmodelled heredoc tag %r at line %d"
                                     % (nxt.text, ll.lineno))
                tags.append((m.group(1), t.text == "<<-"))
        i += 1
        for tag, strip in tags:
            while True:
                if i >= n:
                    raise ParseError("unterminated heredoc <<%s" % tag)
                probe = phys[i].strip() if strip else phys[i]
                i += 1
                if probe.rstrip() == tag:
                    break
    return out


# --------------------------------------------------------------------------
# Scope stack — real dominance, not indentation
# --------------------------------------------------------------------------

_OPEN_KW = ("if", "for", "while", "until", "case", "select")
# Builtins that leave the enclosing body on sight.
_BUILTIN_ABORTS = frozenset(("return", "exit", "continue", "break"))
# Names that USUALLY abort in this corpus but are ordinary functions.  Each is
# credited only after its body is inspected (see `_is_abort_command`).
_NAMED_ABORT_CANDIDATES = frozenset(("die", "_die", "fatal"))


class Frame(object):
    __slots__ = ("kind", "uid", "lineno")

    def __init__(self, kind: str, uid: int, lineno: int) -> None:
        self.kind = kind
        self.uid = uid
        self.lineno = lineno


class FuncSpan(object):
    __slots__ = ("name", "start", "end")

    def __init__(self, name: str, start: int, end: int) -> None:
        self.name = name
        self.start = start   # index into logical-line list
        self.end = end


_RE_FUNC_DEF = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_:.-]*)\s*\(\s*\)")


def assign_scopes(lines: List[LogicalLine]) -> List[FuncSpan]:
    """Walk the token stream, giving every logical line its scope path.

    Every `if` arm, loop body, case arm, function body and brace group is a
    distinct scope id, so "G dominates W" is exactly "G.scope is a prefix of
    W.scope and G comes first".  A stack that does not balance raises
    ParseError: an unparseable structure must never yield a safe verdict.
    """
    stack: List[Frame] = []
    uid = [0]
    funcs: List[FuncSpan] = []
    func_stack: List[Tuple[str, int, int]] = []   # (name, start_idx, depth)

    def push(kind: str, lineno: int) -> None:
        uid[0] += 1
        stack.append(Frame(kind, uid[0], lineno))

    def pop(expect: Sequence[str], lineno: int) -> Frame:
        if not stack:
            raise ParseError("unbalanced block: closed %s with empty stack at line %d"
                             % ("/".join(expect), lineno))
        fr = stack.pop()
        if fr.kind not in expect:
            raise ParseError("unbalanced block at line %d: closing %s but innermost "
                             "is %s (opened line %d)"
                             % (lineno, "/".join(expect), fr.kind, fr.lineno))
        return fr

    for idx, ll in enumerate(lines):
        ll.scope = tuple(f.uid for f in stack)
        m = _RE_FUNC_DEF.match(ll.text)
        is_func_def = False
        if m and any(t.kind == "op" and t.text == "(" for t in ll.toks):
            # `name() {`  — the brace may be on this line or the next.
            is_func_def = True

        cmd_pos = True
        paren_depth = 0
        for j, t in enumerate(ll.toks):
            if t.kind == "op":
                if t.text in (";", "&&", "||", "|", "&", "\n", ";;", ";&", ";;&"):
                    cmd_pos = True
                    if t.text in (";;", ";&", ";;&"):
                        if stack and stack[-1].kind == "arm":
                            pop(("arm",), ll.lineno)
                    continue
                if t.text == "(":
                    paren_depth += 1
                    if is_func_def:
                        continue
                    if cmd_pos:
                        push("subshell", ll.lineno)
                    cmd_pos = True
                    continue
                if t.text == ")":
                    paren_depth -= 1
                    if is_func_def:
                        cmd_pos = True
                        continue
                    if stack and stack[-1].kind == "case":
                        push("arm", ll.lineno)
                        ll.pattern_upto = j + 1
                        cmd_pos = True
                        continue
                    if stack and stack[-1].kind == "subshell":
                        pop(("subshell",), ll.lineno)
                        cmd_pos = True
                        continue
                    raise ParseError("stray ')' at line %d" % ll.lineno)
                cmd_pos = False
                continue

            w = t.text
            if t.quoted:
                cmd_pos = False
                continue

            if cmd_pos and w in _OPEN_KW:
                if w == "case":
                    push("case", ll.lineno)
                    cmd_pos = False
                elif w in ("while", "until"):
                    push("loop-header", ll.lineno)
                    cmd_pos = True      # the condition IS a command
                elif w in ("for", "select"):
                    push("loop-header", ll.lineno)
                    cmd_pos = False     # a variable name follows, not a command
                else:
                    # `if` opens nothing: its condition runs in the enclosing
                    # scope, and that condition may be `( ... )`.
                    cmd_pos = True
                continue
            if cmd_pos and w == "then":
                push("then", ll.lineno)
                cmd_pos = True
                continue
            if cmd_pos and w == "elif":
                # Pop the arm that just ended; the `then` that follows on this
                # same line opens the new one.  Pushing here too would leave a
                # frame per elif unclosed at `fi`.
                pop(("then",), ll.lineno)
                cmd_pos = True          # a condition follows
                continue
            if cmd_pos and w == "else":
                pop(("then",), ll.lineno)
                push("else", ll.lineno)
                cmd_pos = True
                continue
            if cmd_pos and w == "fi":
                pop(("then", "else"), ll.lineno)
                cmd_pos = False
                continue
            if cmd_pos and w == "do":
                pop(("loop-header",), ll.lineno)
                push("loop", ll.lineno)
                cmd_pos = True
                continue
            if cmd_pos and w == "done":
                pop(("loop",), ll.lineno)
                cmd_pos = False
                continue
            if cmd_pos and w == "esac":
                if stack and stack[-1].kind == "arm":
                    pop(("arm",), ll.lineno)
                pop(("case",), ll.lineno)
                cmd_pos = False
                continue
            if cmd_pos and w == "{":
                if is_func_def:
                    push("func", ll.lineno)
                    func_stack.append((m.group(1) if m else "?", idx, len(stack)))
                    is_func_def = False
                else:
                    push("group", ll.lineno)
                cmd_pos = True
                continue
            if cmd_pos and w == "}":
                fr = pop(("group", "func"), ll.lineno)
                if fr.kind == "func" and func_stack:
                    name, start_idx, _ = func_stack.pop()
                    funcs.append(FuncSpan(name, start_idx, idx))
                cmd_pos = False
                continue
            if cmd_pos and w == "!":
                continue
            cmd_pos = False

    if stack:
        raise ParseError("unbalanced block at EOF: %s opened at line %d"
                         % (stack[-1].kind, stack[-1].lineno))
    return funcs


# --------------------------------------------------------------------------
# Command model
# --------------------------------------------------------------------------

class Command(object):
    __slots__ = ("toks", "line_idx", "lineno", "prev_op", "negated", "pos")

    def __init__(self, toks: List[Tok], line_idx: int, lineno: int,
                 prev_op: Optional[str]) -> None:
        self.toks = toks
        self.line_idx = line_idx
        self.lineno = lineno
        self.prev_op = prev_op
        self.negated = False
        # Index of this command within its logical line's command list.
        # Identity, not `is`: every consumer that needs "the command AFTER the
        # one that holds this evidence" must address it by position in the ONE
        # list the model built.  Re-splitting the line makes fresh objects, so
        # `c is t.cmd` silently never matched and the fallback credited an
        # unrelated command on the same line (rail R5-05).
        self.pos = 0


_SPLITTERS = (";", "&&", "||", "|", "&", "\n", ";;", ";&", ";;&", "|&")


def split_commands(ll: LogicalLine, line_idx: int) -> List[Command]:
    cmds: List[Command] = []
    cur: List[Tok] = []
    prev_op: Optional[str] = None
    # A `case` arm's pattern tokens sit before its `)`.  They match; they never
    # run, so they are never a command and never a write.
    test_depth = 0
    for t in ll.toks[ll.pattern_upto:]:
        if t.kind == "op" and t.text == "[[":
            test_depth += 1
        elif t.kind == "op" and t.text == "]]":
            test_depth -= 1
        # Inside `[[ ... ]]`, `&&` and `||` are TEST operators, not command
        # separators.  Splitting there tore `[[ -d x && ! -L x ]]` into a
        # phantom command named `-L`, which both lost the guard and poisoned
        # the operand with an "unmodelled command".
        if t.kind == "op" and t.text in _SPLITTERS and test_depth <= 0:
            if cur:
                cmds.append(Command(cur, line_idx, ll.lineno, prev_op))
            cur = []
            prev_op = t.text
            continue
        # A brace GROUP opener is not part of the command that precedes it.
        # `_log() { printf '%s\n' "$*"; }` is one logical line, and swallowing
        # the `{` made the whole body look like arguments to a call named
        # `_log` — so its `printf` was never classified and every caller
        # inherited an "unknown" occurrence.
        #
        # But `{` and `}` are reserved words ONLY in command position.
        # Anywhere else they are ordinary arguments, and splitting there tore
        # `tee { "$dst"` — a command that writes BOTH files — into a phantom
        # command, losing `$dst` entirely (rail R6-06).  Command position is
        # what `assign_scopes` already tracks for the same two tokens; this is
        # the missing mirror of that rule.  After a function header's `)` the
        # brace IS in command position, which is what keeps every helper body
        # analysed as commands of its own.
        if t.kind == "word" and not t.quoted and t.text in ("{", "}") \
                and test_depth <= 0 \
                and (not cur
                     or (cur[-1].kind == "op" and cur[-1].text == ")")):
            if cur:
                cmds.append(Command(cur, line_idx, ll.lineno, prev_op))
            cur = []
            prev_op = t.text
            continue
        cur.append(t)
    if cur:
        cmds.append(Command(cur, line_idx, ll.lineno, prev_op))
    for i, c in enumerate(cmds):
        c.pos = i
        while c.toks and c.toks[0].kind == "word" and c.toks[0].text == "!" \
                and not c.toks[0].quoted:
            c.negated = not c.negated
            c.toks = c.toks[1:]
    return cmds


# --------------------------------------------------------------------------
# THE READ-ONLY ALLOWLIST.  Fail-closed discovery reads this set and nothing
# else: a command whose name is NOT here is a CANDIDATE WRITE the instrument
# must reason about, never a command it may skip.
#
# Membership is a claim that NO option of that command turns a path operand
# into a destination.  The reason for each entry is in
# .claude/plans/PLAN-185/w0-censo-S329.md §12.  Three names the previous pass
# called read-only are gone because that claim was FALSE for them:
# `sort -o FILE`, `uniq IN OUT` and `yq -i FILE` all write an operand
# (rail R5-08).  A dozen more (`cat`, `head`, `find`, `stat`, `jq`, `date`,
# `git`, ...) are gone because the claim, while probably true, had no proof —
# and an unproven claim is exactly what this pass stopped making.
#
# `die`/`log`/`warn`/... are gone for a different reason: they are LOCAL
# FUNCTIONS in this corpus.  Crediting them by NAME is the anti-pattern the a2
# form exists to refuse.
# --------------------------------------------------------------------------
PROVEN_READONLY = frozenset("""
[ [[ test echo printf true false : return break continue exit
basename dirname grep egrep fgrep local declare typeset export readonly
unset read shift cd pwd umask
""".split())

# Commands with an OUTPUT MODE.  Named here so the census says "write-capable,
# option-aware evidence required" rather than either "read-only" (the R5-08
# fail-open) or "unknown" (which would lose the destination).  The mapping is
# name -> the options whose ARGUMENT is a destination path.
_OUTPUT_MODE_OPT = {
    "sort": {"-o", "--output"},
    "yq": set(),
    "jq": set(),
    "split": set(),
    "csplit": set(),
    "gpg": {"-o", "--output"},
    "openssl": {"-out"},
    "curl": {"-o", "--output"},
    "wget": {"-O", "--output-document"},
    "tar": {"-f", "--file"},
    "zip": set(),
    "unzip": {"-d"},
    # `-i/--input` READS the patch document; it never writes that operand.
    # Listing it as a destination made `patch -i "$patchfile" target` report
    # `$patchfile` as an unguarded write — a blocking FALSE POSITIVE, and the
    # only place this pass removes a block (rail R6-07).
    # `-r` writes the reject file and `-B` prefixes the backup it writes; the
    # pass-2 self-audit caught both sitting in the INPUT table below, which
    # would have been a fail-open of exactly the shape R6-07 came from.
    "patch": {"-o", "--output", "-r", "--reject-file", "-B", "--prefix"},
}
# Options whose argument is an INPUT path or a non-path VALUE.  Modelled so the
# option is consumed (a path value recorded as a read) instead of falling into
# the unmodelled-option branch, which would be fail-closed but would lose the
# positional analysis below.
#
# Admission criterion, same falsifiable shape as PROVEN_READONLY: this option's
# argument is never a path the command WRITES.  `sort -T DIR` failed it — sort
# writes its temporary files into DIR — so it is deliberately absent and makes
# the command unknown.
_OUTPUT_MODE_IN_OPT = {
    "patch": {"-i", "--input", "-d", "--directory", "-p", "--strip"},
    "sort": {"-k", "--key", "-t", "--field-separator", "-S", "--buffer-size"},
    "zip": {"-x", "--exclude", "-i", "--include"},
    "split": {"-a", "-b", "-C", "-l", "-n", "--suffix-length", "--bytes",
              "--line-bytes", "--lines", "--number"},
}
# Commands whose LAST positional operand is a destination even with no option.
_OUTPUT_MODE_LAST = {"uniq"}
# Commands whose POSITIONAL operands include a destination with no option at
# all.  Index counted over the positionals that survive option removal.
#
# Without these, `_classify_output_mode` fell through to a read-only verdict
# for `zip "$dst" "$src"`, `split "$src" "$prefix"` and `patch "$dst" "$diff"`
# — real writes that regressed to no candidate at all (rail R6-02).
_OUTPUT_MODE_POSITIONAL_DEST = {
    "zip": 0,       # zip ARCHIVE file...
    "split": 1,     # split INPUT PREFIX
    "patch": 0,     # patch TARGET [PATCHFILE]
}
# Output-mode commands whose positionals are PROVEN inputs when no destination
# option is present.  The claim is the same falsifiable one PROVEN_READONLY
# makes, and it is what keeps the R6-02 cure from degenerating into "block
# everything": `sort "$dst"` with no `-o` really does write only stdout.
_OUTPUT_MODE_POSITIONAL_SAFE = frozenset(("sort", "jq"))
# `tar` in its traditional key-letter form (`tar cf DST ...`, no leading dash).
# A key letter that CREATES or APPENDS makes the archive operand a destination.
_TAR_WRITE_KEYS = frozenset("cru")
_RE_TAR_KEYS = re.compile(r"^[a-zA-Z]+$")
# In-place flags: their presence turns every remaining operand into a target.
_INPLACE_FLAGS = {
    "yq": ("-i", "--inplace", "--in-place"),
    "jq": ("-i", "--in-place"),
    "perl": ("-i",),
    "ruby": ("-i",),
}

# Prefixes we can strip.  An option we do not model makes the command UNKNOWN.
# (This is exactly the shape the rail flagged: `command cp "$src" "$dst"` must
# not be silently treated as a non-writer.)
_PREFIX_NOARG = {
    "command": {"-p", "-v", "-V"},
    "builtin": set(),
    "exec": {"-c", "-l"},
    "nohup": set(),
    "env": {"-i", "-0", "--ignore-environment", "--null"},
    "nice": set(),
    "stdbuf": set(),
    "timeout": {"--preserve-status", "--foreground", "-k_off"},
    "time": set(),
}
_PREFIX_ARG = {
    "exec": {"-a"},
    "env": {"-u", "-C", "--unset", "--chdir"},
    "nice": {"-n"},
    "stdbuf": {"-i", "-o", "-e"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
}
# timeout takes a positional DURATION before the command.
_PREFIX_POSITIONAL = {"timeout": 1}

# Writers: name -> ("last" | "all" | "none", options-with-args, target-opt)
_WRITERS_LAST = {"cp", "mv", "install", "ln", "rsync"}
_WRITERS_ALL = {"tee", "touch", "truncate", "chmod", "chown", "chgrp", "mkdir"}
_WRITER_OPT_ARG = {
    "cp": {"-t", "--target-directory", "-S", "--suffix"},
    "mv": {"-t", "--target-directory", "-S", "--suffix"},
    "install": {"-t", "--target-directory", "-m", "--mode", "-o", "--owner",
                "-g", "--group", "-S", "--suffix"},
    "ln": {"-t", "--target-directory", "-S", "--suffix"},
    "rsync": {"-e", "--rsh", "--exclude", "--include"},
    "truncate": {"-s", "--size", "-r", "--reference"},
    "tee": set(),
    "touch": {"-d", "--date", "-r", "--reference", "-t"},
    "chmod": set(),
    "chown": set(),
    "chgrp": set(),
    "mkdir": {"-m", "--mode"},
}
# `mkdir` was declared benign on the grounds that it cannot write THROUGH a
# link.  That is true of the FINAL component only: `mkdir -p "$dst/sub"`
# resolves `$dst` and creates `sub` on the other side of it, which is exactly
# the escape this census exists to find.  Found by the Pass-2 self-audit, which
# asked what each non-blocking branch actually proves; the probe returned NO
# SITE for that line.  `mkdir` is a writer.
#
# `rm` and `rmdir` remove the LINK, not its target — unless the operand carries
# a trailing slash, which makes them act on the linked directory.  That is a
# property of the OPERAND, so it is decided per call, not by the name.
_LINK_LOCAL_DELETE = {"rm", "unlink", "rmdir"}

_GIT_READONLY_SUBCMDS = frozenset("""
rev-parse cat-file log show ls-files ls-tree status diff for-each-ref rev-list
describe name-rev merge-base symbolic-ref var check-ignore hash-object
""".split())


class CmdInfo(object):
    __slots__ = ("name", "kind", "dests", "reads", "operands")

    def __init__(self, name: Optional[str], kind: str) -> None:
        self.name = name
        self.kind = kind          # "readonly" | "writer" | "unknown" | "assign"
        self.dests: List[Tok] = []
        self.reads: List[Tok] = []
        self.operands: List[Tok] = []


_RE_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(\+?)=")
# A descriptor duplication operand: a bare number, or `-` to close it.
_RE_FD_OPERAND = re.compile(r"^(\d+|-)$")

# --------------------------------------------------------------------------
# EVERY expansion the shell performs — not only identifier-shaped ones.
#
# The previous pass matched `\$\{?([A-Za-z_][A-Za-z0-9_]*)`, so `$1`, `${10}`,
# `$@`, `$*`, `$#`, `$?` and `$$` were not expansions at all: a script built
# from `sed "s|x|$1|g"` was reported `n0-no-interpolation`, the verdict that
# means "there is nothing here to reason about" (rail R5-03).  An
# operator-controlled positional is the FIRST thing an installer interpolates.
# --------------------------------------------------------------------------
_RE_EXPANSION = re.compile(
    r"\$\{[^}]*\}"          # ${name}, ${name:-x}, ${#name}, ${10}
    r"|\$\("                # $( ... )
    r"|\$[A-Za-z_][A-Za-z0-9_]*"
    r"|\$[0-9]"             # positional
    r"|\$[@*#?$!\-]"        # special parameters
    r"|`")                  # backtick substitution

def _has_cmd_subst(text: str) -> bool:
    """A command substitution the SHELL performs (single quotes suppress it)."""
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "'":
            k = text.find("'", i + 1)
            if k < 0:
                return False
            i = k + 1
            continue
        if c == "`":
            return True
        if c == "$" and i + 1 < n and text[i + 1] == "(" \
                and not text.startswith("((", i + 1):
            return True
        i += 1
    return False


_RE_PARAM_HEAD = re.compile(
    r"^[#!]*(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[@*#?$!\-])")


def _expansion_tail(inner: str) -> str:
    """The part of a `${...}` body that FOLLOWS the parameter name.

    Recursing on the whole body would re-read the parameter itself; recursing
    on the tail is what finds the nested expansion in `:-$RAW`, `:=$(cmd)`,
    `[$i]` and `#$prefix`.
    """
    m = _RE_PARAM_HEAD.match(inner)
    return inner[m.end():] if m else inner


def _expansion_refs(text: str, honour_single_quotes: bool = True,
                    depth: int = 0) -> Tuple[Set[str], bool]:
    """Every parameter the shell READS in `text`, plus "has a substitution".

    NESTED expansions count.  `${safe:-$RAW}` reads BOTH `safe` and `RAW`:
    when `safe` is null or unset the shell substitutes `RAW`, so consuming the
    braced form as ONE token and advancing past its body let a b3 proof about
    `safe` clear an operator-controlled `RAW` (rail R6-03).  `${x:=$(cmd)}`,
    `${a[$i]}` and `${x#$pat}` have the same shape.

    `honour_single_quotes` is the ONE difference between the two callers.  On a
    raw token single quotes suppress expansion.  On a side of an
    already-parsed sed substitution the quoting was resolved before we got
    here, so skipping quoted runs there would hide a real interpolation.

    The name of `$1` is ``1``; of `$@` it is ``@``; of `${x:-y}` it is ``x``.
    Names that no assignment can ever bind (positionals, `$?`, `$$`) reach the
    prover with an EMPTY assignment set, which is exactly right: no assignment
    means no proof means the site blocks.
    """
    names: Set[str] = set()
    cmd_subst = False
    if depth > 8:
        # Nested deeper than we model.  Reporting a substitution is the
        # fail-closed answer: it denies the caller the "literal" verdict.
        return names, True
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "'" and honour_single_quotes:
            k = text.find("'", i + 1)
            if k < 0:
                return names, cmd_subst
            i = k + 1
            continue
        if c == "`":
            cmd_subst = True
            i += 1
            continue
        if c == "$" and i + 1 < n:
            if text[i + 1] == "(":
                if text.startswith("((", i + 1):
                    i += 2
                    continue
                cmd_subst = True
                i += 2
                continue
            if text[i + 1] == "{":
                try:
                    j, seg = _read_balanced(text, i + 1, "{", "}")
                except ParseError:
                    # An expansion we cannot delimit.  Same fail-closed answer.
                    return names, True
                inner = seg[1:-1]
                names.add(_expansion_name("${" + inner + "}"))
                sub_names, sub_subst = _expansion_refs(
                    _expansion_tail(inner), honour_single_quotes, depth + 1)
                names |= sub_names
                cmd_subst = cmd_subst or sub_subst
                i = j
                continue
            m = _RE_EXPANSION.match(text, i)
            if m:
                names.add(_expansion_name(m.group(0)))
                i = m.end()
                continue
        i += 1
    return names, cmd_subst


def expansion_names(raw: str) -> Tuple[Set[str], bool]:
    """Names the shell expands in this RAW token, plus "has a substitution"."""
    return _expansion_refs(raw, honour_single_quotes=True)


_RE_INNER_NAME = re.compile(r"([A-Za-z_][A-Za-z0-9_]*|[0-9]+|[@*#?$!\-])")


def _expansion_name(token: str) -> str:
    """The parameter a single expansion token reads."""
    body = token[1:]
    if body.startswith("{") and body.endswith("}"):
        body = body[1:-1]
        # `${#name}`, `${!name}`, `${name:-x}`, `${name[0]}` all READ `name`.
        body = body.lstrip("#!")
    m = _RE_INNER_NAME.match(body)
    return m.group(1) if m else body


# Directories whose contents are the system programs this instrument's rules
# describe.  The list is deliberately short and absolute: it is the set where
# `sed` means GNU/BSD sed, not a file someone dropped in the corpus.
_TRUSTED_BIN_DIRS = frozenset((
    "/bin", "/usr/bin", "/usr/local/bin", "/opt/homebrew/bin",
    "/sbin", "/usr/sbin",
))


def command_basename(name: str) -> str:
    """The rule name a command maps to, or "" when it maps to NO rule.

    `/usr/bin/sed` is sed: that directory holds the program the rules in this
    file describe.  `./grep`, `/tmp/printf` and `"$BIN"/x` are NOT — the shell
    executes THAT file, whose behaviour no allowlist entry has ever proven.
    Normalising them to a trusted basename let `./grep --output "$dst"` reach
    `a3-no-write-to-operand` with no write candidate at all (rail R6-01), which
    is the fail-open shape this census exists to refuse.

    Returning "" is how a name reaches the caller as UNKNOWN; matching only a
    bare name would instead have produced NO SITE, the invisible-by-omission
    class (rail R5-02).  An empty tail (`foo/`) is not a command name either.
    """
    if "/" not in name:
        return name
    head, _, tail = name.rpartition("/")
    if head in _TRUSTED_BIN_DIRS:
        return tail
    return ""


def _strip_prefixes(toks: List[Tok]) -> Tuple[Optional[List[Tok]], bool]:
    """Strip leading assignments and modelled command prefixes.

    Returns (remaining tokens, ok).  ok=False means an unmodelled prefix
    option was met and the whole command must be treated as UNKNOWN.
    """
    i = 0
    n = len(toks)
    # leading VAR=value assignments
    while i < n and toks[i].kind == "word" and _RE_ASSIGN.match(toks[i].text):
        i += 1
    guard = 0
    while i < n and toks[i].kind == "word":
        name = toks[i].text
        if name not in _PREFIX_NOARG:
            break
        guard += 1
        if guard > 8:
            return None, False
        noarg = _PREFIX_NOARG[name]
        witharg = _PREFIX_ARG.get(name, set())
        i += 1
        while i < n and toks[i].kind == "word" and toks[i].text.startswith("-") \
                and toks[i].text != "-" and not toks[i].quoted:
            opt = toks[i].text
            if opt == "--":
                i += 1
                break
            base = opt.split("=", 1)[0]
            if base in witharg:
                if "=" in opt:
                    i += 1
                    continue
                i += 2
                continue
            if base in noarg:
                i += 1
                continue
            # short cluster like -oL for stdbuf, or anything unmodelled
            if len(base) > 2 and base[:2] in witharg:
                i += 1
                continue
            return None, False
        if name == "env":
            while i < n and toks[i].kind == "word" and _RE_ASSIGN.match(toks[i].text):
                i += 1
        pos = _PREFIX_POSITIONAL.get(name, 0)
        i += pos
    return toks[i:], True


# Shell keywords that may lead a command's token list.  They are not commands;
# dropping them is what keeps `if [ -e "$x" ]` from being classified as a call
# to an unknown program named `if`.
_KEYWORDS = frozenset(("if", "then", "elif", "else", "fi", "for", "while",
                       "until", "select", "do", "done", "case", "esac", "in",
                       "function", "{", "}", "!", "time", "coproc"))


def classify_command(cmd: Command) -> CmdInfo:
    toks = cmd.toks
    # Redirections first: they are writes regardless of the command.
    info_dests: List[Tok] = []
    info_reads: List[Tok] = []
    body: List[Tok] = []
    is_test_host = False
    k = 0
    while k < len(toks):
        t = toks[k]
        if t.kind == "op":
            if t.text in (">", ">>", ">|"):
                if k + 1 < len(toks) and toks[k + 1].kind == "word":
                    info_dests.append(toks[k + 1])
                    k += 2
                    continue
                k += 1
                continue
            if t.text in ("<", "<<<"):
                if k + 1 < len(toks) and toks[k + 1].kind == "word":
                    info_reads.append(toks[k + 1])
                    k += 2
                    continue
                k += 1
                continue
            if t.text in ("<<", "<<-"):
                k += 2          # heredoc tag: not a path
                continue
            if t.text in (">&", "<&"):
                # `cmd >& "$dst"` OPENS $dst for output.  Only a NUMERIC
                # operand (or `-`, which closes the descriptor) is a
                # descriptor duplication; treating every `>&` as a dup threw
                # the filename away and left the write invisible (rail R5-07).
                if k + 1 < len(toks) and toks[k + 1].kind == "word":
                    dup = canon_operand(toks[k + 1])
                    if _RE_FD_OPERAND.match(dup):
                        k += 2
                        continue
                    if t.text == ">&":
                        info_dests.append(toks[k + 1])
                    else:
                        info_reads.append(toks[k + 1])
                    k += 2
                    continue
                k += 1
                continue
            if t.text == "[[":
                is_test_host = True
                k += 1
                continue
            # `]]`, `(`, `)`, `((...))`: structural, no operand of ours
            k += 1
            continue
        body.append(t)
        k += 1

    while body and body[0].kind == "word" and not body[0].quoted \
            and body[0].text in _KEYWORDS:
        body = body[1:]

    if is_test_host:
        info = CmdInfo("[[", "readonly")
        info.dests = info_dests
        info.reads = list(body)
        info.operands = list(body)
        return info

    stripped, ok = _strip_prefixes(body)
    if not ok or stripped is None:
        info = CmdInfo(None, "unknown")
        info.dests = info_dests
        info.reads = info_reads
        info.operands = body
        return info
    if not stripped:
        pure_assign = all(t.kind == "word" and _RE_ASSIGN.match(t.text)
                          for t in body)
        info = CmdInfo(None, "readonly" if pure_assign else "unknown")
        info.dests = info_dests
        info.reads = info_reads
        info.operands = [] if pure_assign else list(body)
        return info

    name_tok = stripped[0]
    raw_name = name_tok.text
    args = stripped[1:]

    # A name that is itself an expansion (`"$CP" -f "$dst"`) names a program
    # we cannot know, so it is UNKNOWN — never skipped.
    if name_tok.quoted or _RE_EXPANSION.search(raw_name):
        info = CmdInfo(raw_name, "unknown")
        info.dests = list(info_dests)
        info.reads = list(info_reads)
        info.operands = list(args)
        return info

    name = command_basename(canon_operand(name_tok))
    info = CmdInfo(name, "unknown")
    info.dests = list(info_dests)
    info.reads = list(info_reads)
    info.operands = list(args)

    if not name:
        return info

    if name in ("[[", "[", "test"):
        info.kind = "readonly"
        info.reads.extend(args)
        return info

    if name == "find":
        acting = ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint",
                  "-fprint0", "-fprintf", "-fls")
        if any(a.kind == "word" and not a.quoted and a.text in acting
               for a in args):
            info.kind = "unknown"
            return info
        info.kind = "readonly"
        info.reads.extend(args)
        return info

    if name in PROVEN_READONLY:
        if name in ("local", "declare", "typeset", "export", "readonly") \
                and any(a.kind == "word" and _has_cmd_subst(a.text) for a in args):
            # The binding itself writes no path, but a command substitution in
            # its value runs commands.  Those ARE scanned separately; being
            # conservative here costs one candidate site and removes the need
            # to argue about it.
            info.kind = "unknown"
            return info
        info.kind = "readonly"
        info.reads.extend(args)
        return info

    if name in _OUTPUT_MODE_OPT or name in _OUTPUT_MODE_LAST \
            or name in _INPLACE_FLAGS:
        return _classify_output_mode(name, args, info)

    if name == "git":
        sub = None
        j = 0
        while j < len(args):
            a = args[j].text
            if a == "-C" or a == "--git-dir" or a == "--work-tree":
                j += 2
                continue
            if a.startswith("-"):
                j += 1
                continue
            sub = a
            break
        if sub in _GIT_READONLY_SUBCMDS:
            info.kind = "readonly"
            info.reads.extend(args)
            return info
        info.kind = "unknown"
        return info

    if name in ("sed", "gsed", "awk", "gawk", "mawk"):
        inplace = any(
            a.kind == "word" and not a.quoted
            and (re.match(r"^-[a-zA-Z]*i", a.text)
                 or a.text.split("=", 1)[0] in ("--in-place", "--inplace"))
            for a in args)
        operands = [a for a in args
                    if a.kind == "word" and not (not a.quoted
                                                 and a.text.startswith("-"))]
        if inplace:
            # Every operand after the script is edited in place; when the
            # script came from -e/-f there is no positional script at all, so
            # ALL operands are destinations.
            has_opt_script = any(a.kind == "word" and not a.quoted
                                 and a.text.split("=", 1)[0] in
                                 ("-e", "-f", "--expression", "--file")
                                 for a in args)
            info.kind = "writer"
            info.dests.extend(operands if has_opt_script else operands[1:])
            return info
        info.kind = "readonly"
        info.reads.extend(args)
        return info

    if name in _LINK_LOCAL_DELETE:
        dangerous = [a for a in args
                     if a.kind == "word" and not a.text.startswith("-")
                     and canon_operand(a).endswith("/")]
        if dangerous:
            info.kind = "writer"
            info.dests.extend(dangerous)
            return info
        info.kind = "readonly"
        info.reads.extend(args)
        return info

    if name in _WRITERS_LAST or name in _WRITERS_ALL:
        witharg = _WRITER_OPT_ARG.get(name, set())
        positional: List[Tok] = []
        target_opt: Optional[Tok] = None
        j = 0
        bad = False
        while j < len(args):
            a = args[j]
            # Option-ness is read off the CANONICAL text, not the quoted flag.
            # `--target-directory="$dst"` carries a quoted segment, so the old
            # `not a.quoted` guard sent the whole token to `positional` and
            # made the SOURCE the destination (rail R5-09).
            txt = canon_operand(a)
            if a.kind == "word" and txt.startswith("-") and txt != "-":
                if txt == "--":
                    positional.extend(args[j + 1:])
                    break
                base = txt.split("=", 1)[0]
                if base in witharg:
                    if "=" in txt:
                        if base in ("-t", "--target-directory"):
                            # The value is the destination.  Rebuild it as its
                            # own token so the occurrence key is `$dst`, the
                            # same key the guard analysis indexes by.
                            target_opt = Tok("word", txt.split("=", 1)[1],
                                             a.quoted)
                        j += 1
                        continue
                    if base in ("-t", "--target-directory"):
                        if j + 1 < len(args):
                            target_opt = args[j + 1]
                        else:
                            bad = True
                    j += 2
                    continue
                j += 1
                continue
            positional.append(a)
            j += 1
        if bad:
            info.kind = "unknown"
            return info
        if target_opt is not None:
            info.kind = "writer"
            info.dests.append(target_opt)
            info.reads.extend(positional)
            return info
        if name in _WRITERS_ALL:
            info.kind = "writer"
            info.dests.extend(positional)
            return info
        if len(positional) >= 2:
            info.kind = "writer"
            info.dests.append(positional[-1])
            info.reads.extend(positional[:-1])
            return info
        # `cp` with fewer than two operands is a shape we do not model.
        info.kind = "unknown"
        return info

    if name == "dd":
        for a in args:
            if a.kind == "word" and canon_operand(a).startswith("of="):
                info.kind = "writer"
                info.dests.append(Tok("word", a.text.split("=", 1)[1], a.quoted))
        if info.kind == "writer":
            return info
        info.kind = "unknown"
        return info

    info.kind = "unknown"
    return info


def _classify_output_mode(name: str, args: List[Tok], info: CmdInfo) -> CmdInfo:
    """Option-aware classification for commands that HAVE an output mode.

    `sort`, `uniq` and `yq` sat in the read-only set of the previous pass, so a
    tested path handed to `sort -o "$dst"` was recorded as a READ and the site
    came out `a3-no-write-to-operand` (rail R5-08).  Membership in a read-only
    set is a claim about every option; these commands falsify it, so they get
    evidence instead of a set membership.
    """
    dest_opts = _OUTPUT_MODE_OPT.get(name, set())
    in_opts = _OUTPUT_MODE_IN_OPT.get(name, set())
    inplace_flags = _INPLACE_FLAGS.get(name, ())
    positional: List[Tok] = []
    dests: List[Tok] = []
    inplace = False
    j = 0
    while j < len(args):
        a = args[j]
        txt = canon_operand(a)
        if a.kind == "word" and txt.startswith("-") and txt != "-":
            if txt == "--":
                positional.extend(args[j + 1:])
                break
            base = txt.split("=", 1)[0]
            if base in inplace_flags or any(txt.startswith(f) for f in inplace_flags):
                inplace = True
                j += 1
                continue
            if base in in_opts:
                # An INPUT-bearing option: consume its value as a read so the
                # positional analysis below still sees the real operand list.
                if "=" in txt:
                    info.reads.append(Tok("word", txt.split("=", 1)[1], a.quoted))
                    j += 1
                    continue
                if j + 1 < len(args):
                    info.reads.append(args[j + 1])
                    j += 2
                    continue
                info.kind = "unknown"
                return info
            if base in dest_opts:
                if "=" in txt:
                    dests.append(Tok("word", txt.split("=", 1)[1], a.quoted))
                    j += 1
                    continue
                if j + 1 < len(args):
                    dests.append(args[j + 1])
                    j += 2
                    continue
                info.kind = "unknown"
                return info
            # An option we do not model may itself be an output mode.
            info.kind = "unknown"
            return info
        positional.append(a)
        j += 1

    if inplace:
        info.kind = "writer"
        info.dests.extend(positional)
        return info
    if name in _OUTPUT_MODE_LAST and len(positional) >= 2:
        info.kind = "writer"
        info.dests.append(positional[-1])
        info.reads.extend(positional[:-1])
        return info
    if dests:
        info.kind = "writer"
        info.dests.extend(dests)
        info.reads.extend(positional)
        return info

    # `tar cf DST ...` — the traditional key-letter form carries no dash, so
    # the loop above filed `cf` as a positional.  A key letter that creates or
    # appends makes the NEXT positional the archive it writes.
    if name == "tar" and positional:
        keys = canon_operand(positional[0])
        if _RE_TAR_KEYS.match(keys):
            if "f" in keys and len(positional) >= 2:
                if _TAR_WRITE_KEYS & set(keys):
                    # c/r/u: the archive operand is the DESTINATION.
                    info.kind = "writer"
                    info.dests.append(positional[1])
                    info.reads.extend(positional[2:])
                elif "t" in keys:
                    # `t` lists the archive and writes nothing at all.
                    info.kind = "readonly"
                    info.reads.extend(positional[1:])
                else:
                    # `x` reads the archive OPERAND but extracts files into the
                    # working directory — a write whose destination is not an
                    # operand, so no rule here can name it.  Unknown is the
                    # honest answer; the pass-2 self-audit demoted this from
                    # read-only, where it would have absolved a real write.
                    info.kind = "unknown"
                return info
            # `tar c` writing to stdout, or a key set we cannot place.
            info.kind = "unknown"
            return info

    idx = _OUTPUT_MODE_POSITIONAL_DEST.get(name)
    if idx is not None and len(positional) > idx:
        info.kind = "writer"
        info.dests.append(positional[idx])
        info.reads.extend(p for k, p in enumerate(positional) if k != idx)
        return info

    if name in _OUTPUT_MODE_LAST:
        # `uniq IN` (one operand) writes stdout; `uniq` alone reads stdin.
        info.kind = "readonly"
        info.reads.extend(positional)
        return info
    if name in _OUTPUT_MODE_POSITIONAL_SAFE:
        info.kind = "readonly"
        info.reads.extend(positional)
        return info

    # An output-capable command whose destination this pass has NOT modelled.
    # The previous fallback said "read-only", which is how `zip "$dst" "$src"`
    # and traditional `tar cf "$dst"` produced no write candidate (rail R6-02).
    # Unknown keeps the operands as candidates; it never absolves them.
    info.kind = "unknown"
    return info


# --------------------------------------------------------------------------
# Operand canonicalisation and the occurrence index
# --------------------------------------------------------------------------

_RE_BRACED_NAME = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def canon_operand(tok_or_text) -> str:
    """Canonical shape of a word: quoting removed, ${x} normalised to $x."""
    text = tok_or_text.text if isinstance(tok_or_text, Tok) else tok_or_text
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            out.append(text[i + 1])
            i += 2
            continue
        if c == "'":
            k = text.find("'", i + 1)
            if k < 0:
                out.append(text[i:])
                break
            out.append(text[i + 1:k])
            i = k + 1
            continue
        if c == '"':
            try:
                k, seg = _read_dquote(text, i)
            except ParseError:
                out.append(text[i + 1:])
                break
            out.append(seg[1:-1])
            i = k
            continue
        out.append(c)
        i += 1
    s = "".join(out)
    s = _RE_BRACED_NAME.sub(lambda m: "$" + m.group(1), s)
    return s


_RE_VARREF = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")


def var_names(canon: str) -> Set[str]:
    return set(_RE_VARREF.findall(canon))


OCC_TEST = "test"
OCC_READ = "read"
OCC_WRITE = "write"
OCC_ALIAS = "alias"
OCC_UNKNOWN = "unknown"


class Occurrence(object):
    __slots__ = ("line_idx", "lineno", "kind", "cmd_name", "canon", "scope",
                 "argpos")

    def __init__(self, line_idx: int, lineno: int, kind: str,
                 cmd_name: Optional[str], canon: str,
                 scope: Tuple[int, ...], argpos: int = 0) -> None:
        self.line_idx = line_idx
        self.lineno = lineno
        self.kind = kind
        self.cmd_name = cmd_name
        self.canon = canon
        self.scope = scope
        self.argpos = argpos      # 1-based operand index, 0 when unknown


# --------------------------------------------------------------------------
# The file model
# --------------------------------------------------------------------------

_TEST_OPS_FOLLOW = frozenset(list("efdsrwxbcpSugkGON"))
_TEST_OPS_NOFOLLOW = frozenset(["L", "h"])


class TestOccurrence(object):
    __slots__ = ("line_idx", "lineno", "op", "operand", "canon", "cmd", "scope",
                 "cmd_pos", "has_negation", "has_conjunction")

    def __init__(self, line_idx: int, lineno: int, op: str, operand: Tok,
                 canon: str, cmd: Command, scope: Tuple[int, ...],
                 has_negation: bool = False,
                 has_conjunction: bool = False) -> None:
        self.line_idx = line_idx
        self.lineno = lineno
        self.op = op
        self.operand = operand
        self.canon = canon
        self.cmd = cmd
        self.cmd_pos = cmd.pos
        self.scope = scope
        # Bracket-INTERNAL polarity and conjunction, both of which decide
        # whether the branch a symlink takes is the one that aborts.
        # `[ ! -L "$dst" ] && return 1` aborts for everything EXCEPT a
        # symlink, and the previous pass read it as a guard because the `!`
        # is a word inside the brackets, not the tokenised command-level `!`
        # the model checked (rail R5-04).
        self.has_negation = has_negation
        self.has_conjunction = has_conjunction


class FileModel(object):
    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self.lines: List[LogicalLine] = []
        self.funcs: List[FuncSpan] = []
        self.commands: List[Command] = []
        self.subst_commands: List[Command] = []
        self.occ: Dict[str, List[Occurrence]] = {}
        self.tests: List[TestOccurrence] = []
        self.assigns: Dict[str, List[Tuple[int, str, Command]]] = {}
        self.unparseable: Optional[str] = None
        # The ONE command list per logical line.  Every consumer that needs a
        # neighbouring command addresses it here by index; re-splitting a line
        # makes fresh objects whose identity nothing can match (rail R5-05).
        self.line_cmds: Dict[int, List[Command]] = {}
        # Test expressions the model could not walk to the end.  Each becomes a
        # BLOCKING site: an unrecognised test must never be an absent one.
        self.unmodelled_tests: List[Tuple[int, int, str, str]] = []
        # Commands that are candidate WRITES: not provably read-only and
        # touching an expansion.  This is the fail-closed half of discovery.
        self.candidates: List[Tuple[Command, str, List[Tuple[str, Tok]]]] = []
        # Every rebinding of a name that is NOT a plain assignment (`read x`,
        # `for x in`, `getopts o x`, `printf -v x`).  A guard proved before one
        # of these proves nothing about the value that reaches the write.
        self.rebinds: Dict[str, List[int]] = {}

    def cmds_of(self, line_idx: int) -> List[Command]:
        return self.line_cmds.get(line_idx, [])

    def func_at(self, line_idx: int) -> Optional[FuncSpan]:
        best: Optional[FuncSpan] = None
        for f in self.funcs:
            if f.start <= line_idx <= f.end:
                if best is None or f.start > best.start:
                    best = f
        return best

    def func_by_name(self, name: str) -> Optional[FuncSpan]:
        for f in self.funcs:
            if f.name == name:
                return f
        return None


def _record_occ(fm: FileModel, tok: Tok, kind: str, cmd: Command,
                cmd_name: Optional[str], argpos: int = 0) -> None:
    c = canon_operand(tok)
    if not c:
        return
    fm.occ.setdefault(c, []).append(
        Occurrence(cmd.line_idx, cmd.lineno, kind, cmd_name, c,
                   fm.lines[cmd.line_idx].scope, argpos))


# Unary operators that take a PATH and dereference it.
_TEST_UNARY_FILE = frozenset(list("efdsrwxbcpSugkGONLha"))
# Unary operators that take something other than a path.
_TEST_UNARY_OTHER = frozenset(("z", "n", "o", "v", "R", "t"))
# Binary operators that COMPARE two paths, dereferencing both.
_TEST_BINARY_FILE = frozenset(("-nt", "-ot", "-ef"))
# Binary operators over strings/integers: no path is dereferenced.
_TEST_BINARY_OTHER = frozenset(("=", "==", "!=", "=~", "<", ">",
                                "-eq", "-ne", "-lt", "-le", "-gt", "-ge"))
_TEST_JOIN = frozenset(("-a", "-o", "&&", "||"))


_REDIR_OPS = (">", ">>", ">|", "<", "<<<", "<<", "<<-", ">&", "<&")


def _strip_redirections(toks: List[Tok]) -> List[Tok]:
    """Drop redirections (and the fd digit in front of them) from a token list.

    `[ "$n" -gt 1 ] 2>/dev/null` is an ordinary test with a redirection glued
    to it.  Leaving the redirection in the expression made the walker meet a
    `]` it did not expect and report an unmodelled test — a FALSE positive that
    would have put two healthy lines in the baseline.
    """
    out: List[Tok] = []
    k = 0
    n = len(toks)
    while k < n:
        t = toks[k]
        if t.kind == "op" and t.text in _REDIR_OPS:
            if out and out[-1].kind == "word" and re.match(r"^\d+$", out[-1].text):
                out.pop()
            k += 2 if k + 1 < n and toks[k + 1].kind == "word" else 1
            continue
        out.append(t)
        k += 1
    return out


def _test_host_expression(cmd: Command) -> Optional[List[Tok]]:
    """The expression tokens of a test command, or None if this is no test.

    Recognises `[[ ... ]]`, `[ ... ]`, `test ...` and any PATH-QUALIFIED form
    of the last two (`/bin/test -e "$x"`), which matched nothing before and so
    produced no site at all (rail R5-01).
    """
    toks = list(cmd.toks)
    if any(t.kind == "op" and t.text == "[[" for t in toks):
        out: List[Tok] = []
        depth = 0
        for t in toks:
            if t.kind == "op" and t.text == "[[":
                depth += 1
                continue
            if t.kind == "op" and t.text == "]]":
                depth -= 1
                continue
            if depth > 0:
                out.append(t)
        return out
    body = _strip_redirections(toks)
    while body and body[0].kind == "word" and not body[0].quoted \
            and body[0].text in _KEYWORDS:
        body = body[1:]
    if not body or body[0].kind != "word" or body[0].quoted:
        return None
    head = command_basename(canon_operand(body[0]))
    if head not in ("[", "test"):
        return None
    rest = body[1:]
    if head == "[":
        if rest and rest[-1].kind == "word" and canon_operand(rest[-1]) == "]":
            rest = rest[:-1]
        else:
            return rest + [Tok("word", "\x00unterminated")]
    return rest


def _scan_tests(fm: FileModel, cmd: Command) -> None:
    """Model the WHOLE test expression, fail-closed.

    The previous pass hunted for `-X` tokens and looked BACKWARDS for a host.
    Every shape that search did not recognise — `test -a "$dst"`, a
    path-qualified `test`, an operator with no operand, `-nt`/`-ef` — produced
    NO SITE, so a later write through that path was invisible rather than
    indeterminate (rail R5-01).  Here the expression is walked forwards and
    anything the model cannot place raises the file's unmodelled-test flag,
    which becomes a BLOCKING site.
    """
    expr = _test_host_expression(cmd)
    if expr is None:
        return
    scope = fm.lines[cmd.line_idx].scope
    found: List[Tuple[str, Tok]] = []
    has_negation = cmd.negated
    has_conjunction = False
    unmodelled: Optional[str] = None

    i = 0
    n = len(expr)
    expect_expr = True
    while i < n:
        t = expr[i]
        txt = t.text if not t.quoted else canon_operand(t)
        if t.kind == "op":
            if t.text in ("&&", "||"):
                if t.text == "&&":
                    has_conjunction = True
                expect_expr = True
                i += 1
                continue
            if t.text in ("(", ")"):
                i += 1
                continue
            unmodelled = "test operator %r" % t.text
            break
        if txt == "\x00unterminated":
            unmodelled = "unterminated `[` expression"
            break
        if expect_expr:
            if txt == "!" and not t.quoted:
                has_negation = not has_negation
                i += 1
                continue
            if not t.quoted and len(txt) == 2 and txt.startswith("-"):
                op = txt[1]
                if op in _TEST_UNARY_FILE:
                    if i + 1 >= n or expr[i + 1].kind != "word":
                        unmodelled = "%s with no operand" % txt
                        break
                    found.append((op, expr[i + 1]))
                    i += 2
                    expect_expr = False
                    continue
                if op in _TEST_UNARY_OTHER:
                    if i + 1 >= n:
                        unmodelled = "%s with no operand" % txt
                        break
                    i += 2
                    expect_expr = False
                    continue
                unmodelled = "unmodelled unary test operator %r" % txt
                break
            if not t.quoted and txt.startswith("-") and txt not in _TEST_JOIN \
                    and txt not in _TEST_BINARY_OTHER and len(txt) > 2:
                unmodelled = "unmodelled test operator %r" % txt
                break
            # A word in expression position: either the left side of a binary
            # operator, or a bare `[ "$x" ]` truth test.
            if i + 1 < n and expr[i + 1].kind == "word" \
                    and not expr[i + 1].quoted \
                    and expr[i + 1].text in _TEST_BINARY_FILE:
                if i + 2 >= n:
                    unmodelled = "%s with no right operand" % expr[i + 1].text
                    break
                # `-nt`/`-ot`/`-ef` stat BOTH operands, so both are decided by
                # a dereferencing test.
                found.append(("e", t))
                found.append(("e", expr[i + 2]))
                i += 3
                expect_expr = False
                continue
            if i + 1 < n and expr[i + 1].kind == "word" \
                    and not expr[i + 1].quoted \
                    and expr[i + 1].text in _TEST_BINARY_OTHER:
                if i + 2 >= n:
                    unmodelled = "%s with no right operand" % expr[i + 1].text
                    break
                i += 3
                expect_expr = False
                continue
            i += 1
            expect_expr = False
            continue
        if not t.quoted and txt in _TEST_JOIN:
            if txt in ("-a", "&&"):
                has_conjunction = True
            expect_expr = True
            i += 1
            continue
        unmodelled = "unmodelled token %r after a complete test" % txt
        break

    if unmodelled is not None:
        fm.unmodelled_tests.append((cmd.line_idx, cmd.lineno, unmodelled,
                                    fm.lines[cmd.line_idx].snippet()))
        return

    for op, operand in found:
        c = canon_operand(operand)
        if not c:
            continue
        # `-a` in expression position is the unary "exists" operator, which
        # dereferences exactly like `-e`.
        norm = "e" if op == "a" else op
        fm.tests.append(TestOccurrence(cmd.line_idx, cmd.lineno, norm, operand,
                                       c, cmd, scope, has_negation,
                                       has_conjunction))
        _record_occ(fm, operand, OCC_TEST, cmd, "test")


def extract_cmd_substs(text: str) -> List[str]:
    """Every `$( ... )` / backtick body in a token, recursively.

    Commands inside a substitution are commands.  Leaving them unread is how
    `sed "s/{{X}}/$handle/g"` inside `_utg_hash="$( ... | sed ... )"` stayed
    invisible to three passes of this instrument.
    """
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "'":
            k = text.find("'", i + 1)
            if k < 0:
                break
            i = k + 1
            continue
        if c == "$" and i + 1 < n and text[i + 1] == "(":
            if text.startswith("((", i + 1):
                i += 2
                continue
            try:
                j, seg = _read_balanced(text, i + 1, "(", ")")
            except ParseError:
                break
            body = seg[1:-1]
            out.append(body)
            out.extend(extract_cmd_substs(body))
            i = j
            continue
        if c == "`":
            k = text.find("`", i + 1)
            if k < 0:
                break
            body = text[i + 1:k]
            out.append(body)
            out.extend(extract_cmd_substs(body))
            i = k + 1
            continue
        i += 1
    return out


def _subst_commands(body: str, line_idx: int, lineno: int) -> Optional[List[Command]]:
    """Commands of a substitution body, or None when it cannot be lexed."""
    try:
        toks = lex(body)
    except ParseError:
        return None
    holder = LogicalLine(lineno, body, toks)
    return split_commands(holder, line_idx)


def build_file_model(rel_path: str, raw: str) -> FileModel:
    fm = FileModel(rel_path)
    try:
        fm.lines = build_logical_lines(raw)
        fm.funcs = assign_scopes(fm.lines)
    except ParseError as exc:
        fm.unparseable = str(exc)
        return fm

    for idx, ll in enumerate(fm.lines):
        cmds = split_commands(ll, idx)
        fm.line_cmds[idx] = cmds
        for cmd in cmds:
            fm.commands.append(cmd)
        # Commands nested inside `$( ... )` on this line.  They are analysed
        # for occurrences and for class B; their TESTS are deliberately not
        # registered, because a subshell's control flow is not modelled and
        # crediting a guard there would be a fail-open (see §subshells).
        bodies: List[str] = []
        for t in ll.toks:
            if t.kind == "word":
                bodies.extend(extract_cmd_substs(t.text))
        for body in bodies:
            inner = _subst_commands(body, idx, ll.lineno)
            if inner is None:
                fm.unparseable = ("unlexable command substitution at line %d"
                                  % ll.lineno)
                return fm
            for cmd in inner:
                fm.subst_commands.append(cmd)

    for cmd in fm.commands:
        # assignments
        if cmd.toks and cmd.toks[0].kind == "word":
            m = _RE_ASSIGN.match(cmd.toks[0].text)
            head = cmd.toks[0].text
            # No `quoted` check here: `_RE_ASSIGN` already requires the token
            # to OPEN with a bare NAME=, so a quoted literal like `"a=b"` can
            # never match.  Testing the token's quoted flag instead rejected
            # every assignment whose VALUE is quoted — which is nearly all of
            # them — and silently emptied the assignment index the b1/b3
            # proofs and the alias analysis both read.
            if m:
                rhs = head.split("=", 1)[1]
                rest = cmd.toks[1:]
                if len(cmd.toks) == 1 or (rest and rest[0].kind == "word"
                                          and _RE_ASSIGN.match(rest[0].text)):
                    fm.assigns.setdefault(m.group(1), []).append(
                        (cmd.line_idx, canon_operand(rhs), cmd))
                    if rhs:
                        _record_occ(fm, Tok("word", rhs), OCC_ALIAS, cmd, "=")
                    continue
            if head in ("local", "declare", "typeset", "export", "readonly"):
                for a in cmd.toks[1:]:
                    if a.kind != "word":
                        continue
                    m2 = _RE_ASSIGN.match(a.text)
                    if m2:
                        rhs = a.text.split("=", 1)[1]
                        fm.assigns.setdefault(m2.group(1), []).append(
                            (cmd.line_idx, canon_operand(rhs), cmd))
                        if rhs:
                            _record_occ(fm, Tok("word", rhs), OCC_ALIAS, cmd, head)

        _scan_tests(fm, cmd)
        _record_command(fm, cmd)
        _scan_rebinds(fm, cmd)
        _scan_candidate(fm, cmd)

    for cmd in fm.subst_commands:
        _record_command(fm, cmd)
        _scan_rebinds(fm, cmd)
        _scan_candidate(fm, cmd)
    return fm


# Names that run text the model never sees.  They are candidates ALWAYS, with
# or without an expansion: `eval` and `source` execute code this instrument
# cannot read, and `exec` replaces the process.
#
# That sentence was already written here while the code did the opposite: the
# operands were still filtered through `_token_is_expanded`, so
# `eval 'cp "$SRC" "$DST"'` — no OUTER expansion, both variables expanded by
# the inner shell — produced no site at all (rail R6-04).  The filter is now
# skipped for these names, which is what makes the comment true.
_OPAQUE_COMMANDS = frozenset(("eval", "source", ".", "exec",
                              "xargs", "sudo", "doas", "su"))
# Shells are opaque when they are handed a script to run: `-c STRING`, or any
# non-option operand (a script path).  `bash --version` runs nothing of ours.
_OPAQUE_SHELLS = frozenset(("bash", "sh", "zsh", "ksh", "dash"))
_OPAQUE_SHELL_FLAGS = frozenset(("-c", "-lc", "-ic", "-xc", "--command"))


def _is_opaque(head: str, rest: Sequence[Tok]) -> bool:
    """Does this command re-parse text the model cannot read?"""
    if head in _OPAQUE_COMMANDS:
        return True
    if head not in _OPAQUE_SHELLS:
        return False
    for t in rest:
        txt = canon_operand(t)
        if txt in _OPAQUE_SHELL_FLAGS or txt.split("=", 1)[0] == "--command":
            return True
        if txt and not txt.startswith("-"):
            return True
    return False


def _scan_rebinds(fm: FileModel, cmd: Command) -> None:
    """Index every non-assignment rebinding of a name."""
    body = [t for t in cmd.toks if t.kind == "word"]
    while body and not body[0].quoted and body[0].text in _KEYWORDS:
        body = body[1:]
    if not body:
        return
    head = command_basename(canon_operand(body[0]))
    args = body[1:]

    def mark(name: str) -> None:
        fm.rebinds.setdefault(name, []).append(cmd.line_idx)

    if head == "read":
        for a in args:
            txt = canon_operand(a)
            if txt.startswith("-"):
                continue
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", txt):
                mark(txt)
        return
    if head == "getopts" and len(args) >= 2:
        mark(canon_operand(args[1]))
        return
    if head == "printf":
        for j, a in enumerate(args):
            if canon_operand(a) == "-v" and j + 1 < len(args):
                mark(canon_operand(args[j + 1]))
        return
    if head == "shift":
        # Every positional moves; a guard on `$1` proved nothing afterwards.
        for j in range(1, 10):
            mark(str(j))
        mark("@")
        mark("*")
        return
    # `for NAME in ...` / `select NAME in ...`
    toks = cmd.toks
    for j, t in enumerate(toks):
        if t.kind == "word" and not t.quoted and t.text in ("for", "select") \
                and j + 1 < len(toks) and toks[j + 1].kind == "word":
            nxt = canon_operand(toks[j + 1])
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", nxt):
                mark(nxt)


def _scan_candidate(fm: FileModel, cmd: Command) -> None:
    """Fail-CLOSED discovery: is this command a candidate write?

    A command is a candidate unless it is PROVEN read-only.  "Proven" means its
    name is in PROVEN_READONLY (or it is a modelled read-only form such as a
    test or a non-acting `find`) AND it opens no file for output.  Everything
    else — an unknown program, an expansion used as the program name, a
    modelled writer, an output-mode command, `eval`/`source`/`exec` — is a
    candidate the verdict layer must reason about.

    Discovery ALSO requires an expansion somewhere in the operands or
    redirections: a write to a fully literal path is decided by the script, not
    by anything an operator controls, and PLAN-185's threat model is about
    operator-controlled paths.  That is the ONE narrowing here, and it is a
    property of the token text, not of a command list.
    """
    if not cmd.toks:
        return
    # A function DEFINITION is not a call: `_log() { printf '%s\n' "$*"; }`
    # names no command at all, and reading its head as one made every helper in
    # the corpus a candidate.
    if _RE_FUNC_DEF.match(" ".join(t.text for t in cmd.toks)):
        return
    lead = [t for t in cmd.toks if t.kind == "word"]
    if lead and not lead[0].quoted and lead[0].text in ("for", "select", "case"):
        # A word LIST, not a command.  Expansions in it are data; any command
        # substitution inside was already lexed into `fm.subst_commands`.
        return

    info = classify_command(cmd)
    body = _strip_redirections(cmd.toks)
    body = [t for t in body if t.kind == "word"]
    while body and not body[0].quoted and body[0].text in _KEYWORDS:
        body = body[1:]
    if not body:
        # Bare redirection (`exec 3> "$f"`, `> "$f"`): still a write.
        body = []
    head = ""
    if body and not body[0].quoted:
        head = command_basename(canon_operand(body[0]))
    opaque = _is_opaque(head, body[1:])

    if opaque:
        # Emitted BEFORE any expansion filter.  What an opaque command expands
        # happens in a shell this model never reads, so the outer token showing
        # no `$` proves nothing at all (rail R6-04).  A modelled destination is
        # still recorded as a write so the site keeps the sharper evidence; the
        # verdict layer answers `i-opaque-command` either way.
        # Only the OPERANDS escape the expansion narrowing.  A REDIRECTION is
        # resolved by the outer shell, so `2>/dev/null` on an opaque command
        # is still a literal path the script chose — crediting it as a proven
        # unguarded write turned `xargs wc -l 2>/dev/null` into a blocking
        # FALSE POSITIVE, measured in scripts/measure-repo-size.sh.
        opaque_dests = [t for t in info.dests
                        if t.kind == "word" and _token_is_expanded(t.text)]
        dest_ids = set(id(t) for t in info.dests)
        rest = [t for t in body[1:] if id(t) not in dest_ids]
        if opaque_dests or rest:
            fm.candidates.append(
                (cmd, "opaque",
                 [("write", t) for t in opaque_dests]
                 + [("unknown", t) for t in rest]))
        # A bare `eval`/`exec` with no operand and no redirection runs nothing;
        # emitting there would be noise, not evidence.
        return

    # Proven destinations, and operands the model cannot place.  Conflating
    # them made `diff -q "$dst" "$tmp" >/dev/null` report that `diff` WRITES
    # its operands, when the only destination is the redirection.
    dests = [t for t in info.dests
             if t.kind == "word" and _token_is_expanded(t.text)]
    unknowns: List[Tok] = []
    if info.kind == "unknown":
        unknowns = [t for t in info.operands
                    if t.kind == "word" and _token_is_expanded(t.text)]
        # One level of interprocedural analysis, same depth as class A: a call
        # to a function DEFINED IN THIS FILE whose matching parameter is never
        # written is not a candidate.  Its NAME is never the evidence.
        if head and fm.func_by_name(head) is not None:
            # The argument POSITION must be the real one, counted over every
            # word operand — not over the filtered subset.
            argpos: Dict[int, int] = {}
            pos = 0
            for a in info.operands:
                if a.kind != "word":
                    continue
                pos += 1
                argpos[id(a)] = pos
            kept: List[Tok] = []
            for t in unknowns:
                probe = Occurrence(cmd.line_idx, cmd.lineno, OCC_UNKNOWN, head,
                                   canon_operand(t),
                                   fm.lines[cmd.line_idx].scope,
                                   argpos.get(id(t), 0))
                if resolve_local_call(fm, probe) != OCC_READ:
                    kept.append(t)
            unknowns = kept

    if not dests and not unknowns:
        return
    # Opaque commands returned above; everything reaching here is `mixed`.
    fm.candidates.append((cmd, "mixed",
                          [("write", t) for t in dests]
                          + [("unknown", t) for t in unknowns]))


def _token_is_expanded(raw: str) -> bool:
    """Does the SHELL decide part of this word?  Quoting-aware."""
    names, subst = expansion_names(raw)
    if names or subst:
        return True
    # A glob or a leading `~` outside quotes is expanded by the shell too.
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "'":
            k = raw.find("'", i + 1)
            if k < 0:
                return False
            i = k + 1
            continue
        if c == '"':
            try:
                i, _seg = _read_dquote(raw, i)
            except ParseError:
                return True
            continue
        if c in "*?":
            return True
        if c == "~" and (i == 0 or raw[i - 1] in "=:"):
            return True
        i += 1
    return False


def _record_command(fm: FileModel, cmd: Command) -> None:
    info = classify_command(cmd)
    for d in info.dests:
        _record_occ(fm, d, OCC_WRITE, cmd, info.name)
    for r in info.reads:
        _record_occ(fm, r, OCC_READ, cmd, info.name)
    if info.kind == "unknown":
        pos = 0
        for a in info.operands:
            if a.kind != "word":
                continue
            pos += 1
            _record_occ(fm, a, OCC_UNKNOWN, cmd, info.name, pos)


_RE_VARARGS = re.compile(r'"\$@"|\$@|\$\*|(?<![\w-])shift(?![\w-])')


def resolve_local_call(fm: FileModel, occ: Occurrence) -> str:
    """One level of interprocedural analysis for a call to a local function.

    Returns OCC_WRITE / OCC_READ / OCC_UNKNOWN.  Depth is ONE by construction:
    if the callee hands the parameter to yet another command we do not model,
    that shows up as an unknown occurrence inside the callee and propagates as
    OCC_UNKNOWN.  A callee that reshuffles its arguments (`$@`, `$*`, `shift`)
    breaks the position-to-parameter mapping, so it is unknown too.
    """
    if not occ.cmd_name or occ.argpos <= 0:
        return OCC_UNKNOWN
    span = fm.func_by_name(occ.cmd_name)
    if span is None:
        return OCC_UNKNOWN
    region = (span.start, span.end)
    reshuffles = any(_RE_VARARGS.search(fm.lines[idx].text)
                     for idx in range(span.start, span.end + 1))
    if reshuffles:
        # `$@`/`$*`/`shift` break the position-to-parameter mapping, so THIS
        # argument cannot be followed.  It can still be cleared, and soundly:
        # if NO positional whatsoever is written inside the callee, then no
        # permutation of the arguments is written either.  Bailing out to
        # UNKNOWN instead made every call to a `printf "$*"` logger a candidate
        # write, which is noise, not caution.
        params = ["$@", "$*"] + ["$%d" % i for i in range(1, 10)]
    else:
        params = ["$%d" % occ.argpos]
    kinds: Set[str] = set()
    for param in params:
        for c in alias_set(fm, param, region):
            for o in fm.occ.get(c, []):
                if region[0] <= o.line_idx <= region[1]:
                    kinds.add(o.kind)
    if OCC_WRITE in kinds:
        return OCC_WRITE
    if OCC_UNKNOWN in kinds:
        return OCC_UNKNOWN
    return OCC_READ


# --------------------------------------------------------------------------
# Dominance
# --------------------------------------------------------------------------


class Corpus(object):
    """Every parsed file, plus a corpus-wide function index.

    Cross-file guard resolution needs this.  A confinement predicate belongs
    in a shared library -- one original consulted by every writer -- so
    refusing to look outside the calling file would force the
    divergent-copies class this repository has already paid for twice
    (PLAN-183 D1..D4).
    """

    def __init__(self) -> None:
        self.models: List["FileModel"] = []
        self.funcs: Dict[str, List[Tuple["FileModel", "FuncSpan"]]] = {}

    def add(self, fm: "FileModel") -> None:
        self.models.append(fm)
        for span in fm.funcs:
            self.funcs.setdefault(span.name, []).append((fm, span))

    def unique_function(self, name: str):
        """The single definition of `name`, or None when 0 or >1 exist.

        Ambiguity is not a tie to break: two files defining one name means the
        census cannot know which body runs, and a guard whose body is unknown
        proves nothing.
        """
        hits = self.funcs.get(name) or []
        if len(hits) != 1:
            return None
        return hits[0]


def dominates(g_scope: Tuple[int, ...], g_idx: int,
              w_scope: Tuple[int, ...], w_idx: int,
              fm: Optional["FileModel"] = None) -> bool:
    """G dominates W: G runs before W on every path that reaches W.

    Source order only means execution order INSIDE one function body.  A guard
    at file top level sits at scope `()`, which is a prefix of every scope, so
    without the function check it would "dominate" every write in every
    function defined below it — and function bodies do not run in source
    order.  That was a fail-open, so the function check is not optional.
    """
    if g_idx >= w_idx:
        return False
    if w_scope[:len(g_scope)] != g_scope:
        return False
    if fm is not None:
        gf = fm.func_at(g_idx)
        wf = fm.func_at(w_idx)
        if (gf.name if gf else None) != (wf.name if wf else None):
            return False
    return True


def rebound_between(fm: FileModel, names: Set[str], g_idx: int,
                    w_idx: int) -> Optional[Tuple[str, int]]:
    """Is any of `names` re-bound after the guard and before the write?

    Dominance says the guard RAN; it does not say the value it inspected is
    still the one the write uses.  For

        dst=/safe; [ -L "$dst" ] && return; dst="$1"; cp src "$dst"

    the guard dominates and proves nothing, because `dst` was reassigned in
    between (rail R5-06).  Any reaching definition invalidates the proof:
    a plain assignment, a `local`/`export`, a `read`, a `for` loop variable,
    `getopts`, `printf -v`, or a `shift` when the path is positional.

    Returns (name, line index) of the first invalidating rebinding, or None.
    """
    hits: List[Tuple[str, int]] = []
    for name in names:
        for (idx, _rhs, _cmd) in fm.assigns.get(name, []):
            if g_idx < idx <= w_idx:
                hits.append((name, idx))
        for idx in fm.rebinds.get(name, []):
            if g_idx < idx <= w_idx:
                hits.append((name, idx))
    if not hits:
        return None
    hits.sort(key=lambda p: (p[1], p[0]))
    return hits[0]


# --------------------------------------------------------------------------
# Class A — symlink-follow
# --------------------------------------------------------------------------


def _is_abort_command(fm: FileModel, cmd: Command) -> bool:
    """Does this command leave the enclosing body?

    `return`/`exit`/`continue`/`break` are shell builtins and prove it on
    sight.  `die`/`_die`/`fatal` are FUNCTION NAMES in this corpus, so they
    prove it only when the function is defined in this file and its body
    aborts unconditionally.  Crediting them by name is the same
    evidence-by-vocabulary the a2 form exists to refuse.
    """
    if not cmd.toks:
        return False
    head = cmd.toks[0]
    if head.kind != "word" or head.quoted:
        return False
    name = command_basename(canon_operand(head))
    if name in _BUILTIN_ABORTS:
        return True
    if name not in _NAMED_ABORT_CANDIDATES:
        return False
    span = fm.func_by_name(name)
    if span is None:
        return False
    for idx in range(span.start, span.end + 1):
        for c in fm.cmds_of(idx):
            if not c.toks:
                continue
            h = c.toks[0]
            if h.kind == "word" and not h.quoted \
                    and command_basename(canon_operand(h)) in ("exit", "return") \
                    and c.prev_op not in ("&&", "||"):
                return True
    return False


def _branch_aborts_at_own_level(fm: FileModel, then_frame_uid: int,
                                start_idx: int) -> bool:
    """The `then` body contains an abort at the frame's OWN level.

    A `return` nested one block deeper is conditional and proves nothing —
    this is the nested-jump fail-open the rail found in the previous pass.
    """
    for idx in range(start_idx, len(fm.lines)):
        ll = fm.lines[idx]
        if then_frame_uid not in ll.scope:
            break
        if ll.scope[-1:] != (then_frame_uid,):
            continue
        for cmd in fm.cmds_of(idx):
            if cmd.prev_op in ("&&", "||"):
                continue
            if _is_abort_command(fm, cmd):
                return True
    return False


def _inline_abort_after(fm: FileModel, cmd_list: List[Command],
                        pos: int) -> bool:
    """`<test> && <abort>` on the same logical line, ADJACENT.

    Adjacency is the whole point: an abort further down the line is guarded by
    whatever sits between it and the test, so it is not this test's abort.
    """
    if pos + 1 >= len(cmd_list):
        return False
    nxt = cmd_list[pos + 1]
    if nxt.prev_op != "&&":
        return False
    return _is_abort_command(fm, nxt)


def _find_then_uid(fm: FileModel, line_idx: int) -> Optional[int]:
    """The scope id opened by the `then` of the `if` on this logical line."""
    ll = fm.lines[line_idx]
    has_then = any(t.kind == "word" and not t.quoted and t.text == "then"
                   for t in ll.toks)
    if has_then:
        for idx in range(line_idx + 1, min(line_idx + 3, len(fm.lines))):
            nxt = fm.lines[idx].scope
            if len(nxt) > len(ll.scope) and nxt[:len(ll.scope)] == ll.scope:
                return nxt[len(ll.scope)]
        return None
    # `if X` with `then` on the following line
    if line_idx + 1 < len(fm.lines):
        nxt_ll = fm.lines[line_idx + 1]
        if any(t.kind == "word" and not t.quoted and t.text == "then"
               for t in nxt_ll.toks):
            for idx in range(line_idx + 2, min(line_idx + 4, len(fm.lines))):
                nxt = fm.lines[idx].scope
                if len(nxt) > len(ll.scope) and nxt[:len(ll.scope)] == ll.scope:
                    return nxt[len(ll.scope)]
    return None


def _single_line_if_aborts(fm: FileModel, cmd_list: List[Command],
                           pos: int) -> bool:
    """`if [ -L x ]; then return 1; fi` entirely on one logical line."""
    for c in cmd_list[pos + 1:]:
        if not c.toks:
            continue
        head = c.toks[0]
        if head.kind == "word" and not head.quoted:
            if head.text == "then":
                continue
            if _is_abort_command(fm, c):
                return True
            return False
    return False


def _guard_polarity_is_usable(t: TestOccurrence) -> bool:
    """The abort must fire for EVERY symlink at that path.

    Two ways it does not, both previously accepted:

    * conjunction — `[[ -f "$x" && -L "$x" ]] && return 1` refuses a symlink
      that is also a regular file and lets a DANGLING one through, which is
      exactly the shape this instrument exists to catch;
    * negation — `[ ! -L "$dst" ] && return 1` aborts for everything EXCEPT a
      symlink, so the symlink case is precisely the one that CONTINUES
      (rail R5-04).  A `!` inside the brackets is a word, not the tokenised
      command-level `!`, so `cmd.negated` never saw it.

    Disjunction stays usable: `[[ -L "$x" || -h "$x" ]]` is true for every
    symlink, so the abort still fires for all of them.
    """
    return not t.has_negation and not t.has_conjunction


def _nofollow_guard_sites(fm: FileModel, canon_set: Set[str],
                          region: Tuple[int, int]) -> List[Tuple[int, Tuple[int, ...]]]:
    """Every proven `-L`/`-h` guard on one of the aliases (form a1)."""
    out: List[Tuple[int, Tuple[int, ...]]] = []
    for t in fm.tests:
        if t.op not in _TEST_OPS_NOFOLLOW:
            continue
        if t.canon not in canon_set:
            continue
        if not (region[0] <= t.line_idx <= region[1]):
            continue
        ll = fm.lines[t.line_idx]
        # The ONE command list, addressed by the position the model recorded.
        # Re-splitting made fresh objects, `c is t.cmd` never matched, and the
        # operand-text fallback credited the FIRST command on the line that
        # merely MENTIONED the path — so an abort attached to `-e` was read as
        # an abort attached to `-L` (rail R5-05).
        cmds = fm.cmds_of(t.line_idx)
        pos = t.cmd_pos
        if pos >= len(cmds) or cmds[pos] is not t.cmd:
            continue
        if not _guard_polarity_is_usable(t):
            continue
        if _inline_abort_after(fm, cmds, pos):
            out.append((t.line_idx, ll.scope))
            continue
        if _single_line_if_aborts(fm, cmds, pos):
            out.append((t.line_idx, ll.scope))
            continue
        uid = _find_then_uid(fm, t.line_idx)
        if uid is not None and _branch_aborts_at_own_level(fm, uid, t.line_idx + 1):
            out.append((t.line_idx, ll.scope))
    return out


def _helper_is_proven_guard(fm: FileModel, name: str) -> bool:
    """Form a2: the helper's BODY proves the guard.  Its name proves nothing."""
    span = fm.func_by_name(name)
    if span is None:
        return False
    for t in fm.tests:
        if t.op not in _TEST_OPS_NOFOLLOW:
            continue
        if not (span.start <= t.line_idx <= span.end):
            continue
        if t.canon not in ("$1", "${1}"):
            continue
        if not _guard_polarity_is_usable(t):
            continue
        cmds = fm.cmds_of(t.line_idx)
        # the symlink branch must leave with a NON-ZERO status
        uid = _find_then_uid(fm, t.line_idx)
        if uid is not None:
            for idx in range(t.line_idx + 1, span.end + 1):
                l2 = fm.lines[idx]
                if uid not in l2.scope:
                    break
                if l2.scope[-1:] != (uid,):
                    continue
                for c in fm.cmds_of(idx):
                    if not c.toks:
                        continue
                    h = c.toks[0]
                    if h.kind != "word" or h.quoted:
                        continue
                    if h.text in ("return", "exit"):
                        if len(c.toks) >= 2 and c.toks[1].kind == "word":
                            val = canon_operand(c.toks[1])
                            if val.isdigit() and int(val) != 0:
                                return True
                        return False
        # single-line form: `[ -L "$1" ] && return 1`
        i = t.cmd_pos
        if i < len(cmds) and cmds[i] is t.cmd:
            if i + 1 < len(cmds) and cmds[i + 1].prev_op == "&&":
                nc = cmds[i + 1]
                if nc.toks and nc.toks[0].text in ("return", "exit") \
                        and len(nc.toks) >= 2:
                    val = canon_operand(nc.toks[1])
                    if val.isdigit() and int(val) != 0:
                        return True
    return False


def _helper_guard_sites(fm: FileModel, canon_set: Set[str],
                        region: Tuple[int, int]) -> List[Tuple[int, Tuple[int, ...]]]:
    out: List[Tuple[int, Tuple[int, ...]]] = []
    proven: Dict[str, bool] = {}
    for idx, ll in enumerate(fm.lines):
        if not (region[0] <= idx <= region[1]):
            continue
        cmds = fm.cmds_of(idx)
        for i, cmd in enumerate(cmds):
            if not cmd.toks or cmd.toks[0].kind != "word" or cmd.toks[0].quoted:
                continue
            name = command_basename(canon_operand(cmd.toks[0]))
            if name not in [f.name for f in fm.funcs]:
                continue
            args = [a for a in cmd.toks[1:] if a.kind == "word"]
            if not args:
                continue
            if canon_operand(args[0]) not in canon_set:
                continue
            if name not in proven:
                proven[name] = _helper_is_proven_guard(fm, name)
            if not proven[name]:
                continue
            # the call site must abort when the helper refuses
            if i + 1 < len(cmds) and cmds[i + 1].prev_op == "||" \
                    and _is_abort_command(fm, cmds[i + 1]):
                out.append((idx, ll.scope))
                continue
            if cmd.negated:
                # `if ! helper "$x"; then abort; fi`
                uid = _find_then_uid(fm, idx)
                if uid is not None and _branch_aborts_at_own_level(fm, uid, idx + 1):
                    out.append((idx, ll.scope))
    return out


_RE_POSITIONAL = re.compile(r"\$\{?([1-9])\b")
_RE_ANY_REF = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*|[1-9])")


def ref_names(canon: str) -> Set[str]:
    """Every reference in a canon form, POSITIONAL parameters included.

    `var_names` deliberately matches identifiers only, so it cannot see `$1`.
    A predicate body tests exactly that, so the parameter-reachability check
    needs its own extractor.
    """
    return set(_RE_ANY_REF.findall(canon))


def _body_checks_a_parameter(fm: "FileModel", span: "FuncSpan") -> bool:
    """The body applies a non-dereferencing check to its OWN parameters.

    Two shapes count: a `-L`/`-h` test, or a `readlink`/`realpath` call.  Both
    must reach a positional parameter, and a real predicate builds a probe
    path out of its parameters first (`root="$1"; probe="$root/$2"`), so the
    reachability is a bounded fixed point over ASSIGNMENTS — three hops, which
    covers that idiom without pretending to be a dataflow engine.  The NAME of
    the function is never part of this decision.
    """
    region = (span.start, span.end)
    reach: Set[str] = set()
    for idx in range(span.start, span.end + 1):
        reach.update(_RE_POSITIONAL.findall(fm.lines[idx].text))
    if not reach:
        return False
    for _hop in range(3):
        grown = set(reach)
        for var, entries in fm.assigns.items():
            for (aidx, rhs, _cmd) in entries:
                if not (region[0] <= aidx <= region[1]):
                    continue
                if ref_names(rhs) & reach:
                    grown.add(var)
        if grown == reach:
            break
        reach = grown

    for t in fm.tests:
        if t.op not in _TEST_OPS_NOFOLLOW:
            continue
        if not (region[0] <= t.line_idx <= region[1]):
            continue
        if ref_names(t.canon) & reach:
            return True
    for cmd in fm.commands:
        if not (region[0] <= cmd.line_idx <= region[1]):
            continue
        head = [x for x in cmd.toks if x.kind == "word"]
        while head and not head[0].quoted and head[0].text in _KEYWORDS:
            head = head[1:]
        if not head or head[0].quoted:
            continue
        if command_basename(canon_operand(head[0])) not in ("readlink", "realpath"):
            continue
        for a in head[1:]:
            if ref_names(canon_operand(a)) & reach:
                return True
    return False


def _body_has_refusal_path(fm: "FileModel", span: "FuncSpan") -> bool:
    """The body can REFUSE: some path leaves with an explicit numeric status.

    Both polarities qualify -- `return 1` for refuse-on-failure and `return 0`
    for the refusal-true convention -- because which one this predicate uses is
    decided at the CALL SITE, by the polarity the caller wrote.
    """
    for idx in range(span.start, span.end + 1):
        for cmd in fm.cmds_of(idx):
            if not cmd.toks:
                continue
            h = cmd.toks[0]
            if h.kind == "word" and not h.quoted and h.text in ("return", "exit"):
                if len(cmd.toks) >= 2 and canon_operand(cmd.toks[1]).isdigit():
                    return True
    return False


def _dest_is_covered(fm: "FileModel", args: List["Tok"], dest_canon: str,
                     region: Tuple[int, int]) -> bool:
    """Did the predicate SEE the destination?  The whole binding question.

    Two modelled shapes, and nothing else:

      * an argument whose alias set contains the destination, or
      * a (root, relpath) PAIR whose alias sets concatenate, with exactly one
        `/` between them, to EXACTLY the destination.

    The pair rule is deliberately exact.  For a write to `"$TARGET/.github/$n"`
    called with `("$TARGET", "$n")` the predicate was told a relpath of `$n`
    while the write lands at `.github/$n` -- it confined a different path, so
    it must not bind.
    """
    arg_aliases = [alias_set(fm, canon_operand(a), region) for a in args]
    # The destination is named by its aliases too: the predicate is handed
    # `("$TARGET", "$rel")` while the write reads `"$dst"`, and those are the
    # same path only through `dst="$TARGET/$rel"`.
    dest_forms = {d for d in alias_set(fm, dest_canon, region) if d}
    for al in arg_aliases:
        if al & dest_forms:
            return True
    for i in range(len(arg_aliases)):
        for j in range(len(arg_aliases)):
            if i == j:
                continue
            for root in arg_aliases[i]:
                if not root:
                    continue
                for rel in arg_aliases[j]:
                    if not rel:
                        continue
                    if root.rstrip("/") + "/" + rel.lstrip("/") in dest_forms:
                        return True
    return False


def _confinement_guard_sites(fm: "FileModel", corpus: Optional["Corpus"],
                             region: Tuple[int, int], dest_canon: str):
    """Form a4.  Returns (guard sites, blocking reason when one applies)."""
    if corpus is None:
        return [], None
    out: List[Tuple[int, Tuple[int, ...]]] = []
    reason: Optional[str] = None
    proven: Dict[str, bool] = {}
    hi = min(region[1], len(fm.lines) - 1)
    for idx in range(max(region[0], 0), hi + 1):
        ll = fm.lines[idx]
        cmds = fm.cmds_of(idx)
        for i, cmd in enumerate(cmds):
            body = [t for t in cmd.toks if t.kind == "word"]
            while body and not body[0].quoted and body[0].text in _KEYWORDS:
                body = body[1:]
            if not body or body[0].quoted:
                continue
            name = body[0].text
            if name in ("[", "[[", "test"):
                continue
            args = [a for a in body[1:] if a.kind == "word"]
            if not args:
                continue
            if name not in corpus.funcs:
                continue
            # Both diagnostics below only apply to a call that could plausibly
            # be THIS write's guard. Raising them for any same-named helper
            # would demote a `desguardado` site — PROVEN dangerous — to
            # `indeterminado`, which tells the reader strictly less.
            dest_vars: Set[str] = set()
            for form in alias_set(fm, dest_canon, region):
                dest_vars |= var_names(form)
            related = bool(dest_vars) and any(
                var_names(canon_operand(a)) & dest_vars for a in args)
            if name not in proven:
                hit = corpus.unique_function(name)
                if hit is None:
                    proven[name] = False
                    if related:
                        reason = reason or R_PRED_AMBIGUOUS
                else:
                    dfm, dspan = hit
                    proven[name] = (_body_checks_a_parameter(dfm, dspan)
                                    and _body_has_refusal_path(dfm, dspan))
            if not proven[name]:
                continue
            if not _dest_is_covered(fm, args, dest_canon, region):
                if related:
                    reason = reason or R_PRED_ARG_UNBOUND
                continue
            # Refusal polarity, both modelled directions:
            #   rc != 0 = refuse : `<pred> ... || <abort>`
            #   rc == 0 = refuse : `if <pred> ...; then <abort>; fi`
            if i + 1 < len(cmds) and cmds[i + 1].prev_op == "||":
                if _is_abort_command(fm, cmds[i + 1]):
                    out.append((idx, ll.scope))
                    continue
            # The `then`-branch polarity is only available when the
            # predicate IS the condition of an `if` on this line.  Without
            # that check a BARE call whose status is discarded picked up the
            # `then` of the NEXT `if` statement and was credited as a guard —
            # a4 became a bypass around the a2 mutation control, caught by
            # `test_helper_whose_refusal_is_ignored_is_not_a_guard`.
            heads = [x for x in ll.toks if x.kind == "word"]
            opens_if = bool(heads) and not heads[0].quoted \
                and heads[0].text == "if"
            if not (opens_if and i == 0):
                continue
            if _single_line_if_aborts(fm, cmds, i):
                out.append((idx, ll.scope))
                continue
            uid = _find_then_uid(fm, idx)
            if uid is not None and _branch_aborts_at_own_level(fm, uid, idx + 1):
                out.append((idx, ll.scope))
    return out, reason


def alias_set(fm: FileModel, canon: str, region: Tuple[int, int]) -> Set[str]:
    """One level of constant propagation, both directions.  Declared limit."""
    out = {canon}
    names = var_names(canon)
    for name in names:
        for (idx, rhs, _cmd) in fm.assigns.get(name, []):
            if rhs and region[0] <= idx <= region[1]:
                out.add(rhs)
    for var, entries in fm.assigns.items():
        for (idx, rhs, _cmd) in entries:
            if rhs == canon and region[0] <= idx <= region[1]:
                out.add("$" + var)
    return out


def _region_for(fm: FileModel, line_idx: int, canon: str) -> Tuple[int, int]:
    """Function span when the variable is `local` there; the whole file else."""
    span = fm.func_at(line_idx)
    if span is None:
        return (0, len(fm.lines) - 1)
    names = var_names(canon)
    if not names:
        return (0, len(fm.lines) - 1)
    for idx in range(span.start, span.end + 1):
        head = fm.lines[idx].text.strip()
        for name in names:
            if re.match(r"^(local|declare|typeset)\s+(-\w+\s+)*" + re.escape(name)
                        + r"(\s|=|$)", head):
                return (span.start, span.end)
    return (0, len(fm.lines) - 1)


def verdict_class_a(fm: FileModel, t: TestOccurrence,
                    corpus: Optional["Corpus"] = None) -> Tuple[str, str, str]:
    """Return (verdict, form_or_reason, detail)."""
    region = _region_for(fm, t.line_idx, t.canon)
    aliases = alias_set(fm, t.canon, region)

    writes: List[Occurrence] = []
    unknowns: List[Occurrence] = []
    # `aliases` is a set, so iterating it raw made the REPORTED site vary
    # between runs under hash randomisation.  A gate whose output is not
    # byte-stable cannot be diffed, and its fingerprints cannot be trusted.
    for c in sorted(aliases):
        for o in fm.occ.get(c, []):
            if not (region[0] <= o.line_idx <= region[1]):
                continue
            kind = o.kind
            if kind == OCC_UNKNOWN:
                kind = resolve_local_call(fm, o)
            if kind == OCC_WRITE:
                writes.append(o)
            elif kind == OCC_UNKNOWN:
                unknowns.append(o)

    if writes:
        test_guards = _nofollow_guard_sites(fm, aliases, region)
        helper_guards = _helper_guard_sites(fm, aliases, region)
        # a4 guards go through the SAME dominance and stale-rebinding checks
        # below.  A new form must never become a bypass around them.
        conf_guards: List[Tuple[int, Tuple[int, ...]]] = []
        conf_reason: Optional[str] = None
        for w in writes:
            got, why = _confinement_guard_sites(fm, corpus, region, w.canon)
            for g in got:
                if g not in conf_guards:
                    conf_guards.append(g)
            conf_reason = conf_reason or why
        guards = test_guards + helper_guards + conf_guards
        watched: Set[str] = set(var_names(t.canon))
        for c in aliases:
            watched |= var_names(c)
        undominated = []
        stale: Optional[Tuple[str, int]] = None
        for w in writes:
            covering = [(gi, gs) for gi, gs in guards
                        if dominates(gs, gi, w.scope, w.line_idx, fm)]
            if not covering:
                undominated.append(w)
                continue
            # A dominating guard whose value was re-bound before the write
            # proves nothing about what the write actually opens.
            live = []
            for gi, gs in covering:
                rb = rebound_between(fm, watched, gi, w.line_idx)
                if rb is None:
                    live.append((gi, gs))
                elif stale is None:
                    stale = rb
            if not live:
                undominated.append(w)
        undominated.sort(key=lambda o: (o.line_idx, o.lineno, o.canon))
        if undominated and stale is not None and guards:
            first = undominated[0]
            return (VERDICT_INDETERMINATE, R_GUARD_STALE,
                    "the -L guard is invalidated by a rebinding of $%s at line "
                    "%d before the write at line %d"
                    % (stale[0], fm.lines[stale[1]].lineno, first.lineno))
        if not undominated:
            if helper_guards:
                form = "a2-nofollow-helper-dominates"
            elif test_guards:
                form = "a1-nofollow-test-dominates"
            else:
                form = "a4-confinement-predicate-dominates"
            return (VERDICT_GUARDED, form,
                    "every write dominated by a proven guard")
        first = undominated[0]
        detail = "write at line %d (%s) with no dominating -L guard" % (
            first.lineno, first.cmd_name or "redirect")
        if guards:
            return (VERDICT_INDETERMINATE, R_GUARD_NOT_DOM, detail)
        if conf_reason:
            return (VERDICT_INDETERMINATE, conf_reason, detail)
        return (VERDICT_UNGUARDED, "", detail)

    if unknowns:
        unknowns.sort(key=lambda o: (o.line_idx, o.lineno, o.canon,
                                     o.cmd_name or ""))
        u = unknowns[0]
        return (VERDICT_INDETERMINATE, R_OCCURRENCE,
                "operand reaches unmodelled command %r at line %d"
                % (u.cmd_name or "?", u.lineno))

    return (VERDICT_NA, "a3-no-write-to-operand",
            "no write to the tested path in the region")


# --------------------------------------------------------------------------
# Class B — sed/awk interpolation
# --------------------------------------------------------------------------

_STREAM_EDITORS = ("sed", "gsed", "awk", "gawk", "mawk")
# "Is there anything here the shell expands?"  This MUST be the same model the
# rest of the file uses.  The old `\$[A-Za-z_{(]|`` did not recognise `$1`, so
# `local v="$1"` was read as a SAFE LITERAL and a caller-controlled value was
# proven safe by form b3 — the very fail-open of rail R5-03, surviving inside
# the b3 proof after the discovery side had been cured.  Found by the
# positive-control probe for R5-13/14/15, all three of which passed for the
# wrong reason until this line changed.
_RE_HAS_EXPANSION = _RE_EXPANSION


class Subst(object):
    __slots__ = ("delim", "pattern", "repl", "flags")

    def __init__(self, delim: str, pattern: str, repl: str, flags: str) -> None:
        self.delim = delim
        self.pattern = pattern
        self.repl = repl
        self.flags = flags


_SED_SIMPLE = set("pdqnNPDhHgGxzF=l")
_SED_LABEL = set("btT:")
_SED_TEXT = set("aic")
_SED_FILE = set("rRwW")


def _skip_sed_address(script: str, i: int) -> Tuple[int, bool]:
    """Consume one sed address, if present.  Returns (index, ok)."""
    n = len(script)
    start = i
    while i < n:
        c = script[i]
        if c.isdigit():
            while i < n and script[i].isdigit():
                i += 1
        elif c == "$":
            i += 1
        elif c == "/":
            j = i + 1
            while j < n:
                if script[j] == "\\":
                    j += 2
                    continue
                if script[j] == "/":
                    break
                j += 1
            if j >= n:
                return start, False
            i = j + 1
        elif c == "\\" and i + 1 < n:
            d = script[i + 1]
            j = i + 2
            while j < n:
                if script[j] == "\\":
                    j += 2
                    continue
                if script[j] == d:
                    break
                j += 1
            if j >= n:
                return start, False
            i = j + 1
        else:
            break
        if i < n and script[i] in ",~":
            i += 1
            continue
        break
    return i, True


def parse_sed_script(script: str) -> Tuple[List[Subst], Optional[str], List[str]]:
    """Split a sed script into substitutions.

    Returns (substitutions, error, non_substitution_regions).  Any construct we
    do not model yields an error, which BLOCKS — never an empty list quietly
    read as "no substitution".  The third value lets the caller check that no
    shell expansion hides in a region we did not model as a substitution.
    """
    subs: List[Subst] = []
    residual: List[str] = []
    i = 0
    n = len(script)
    while i < n:
        c = script[i]
        if c in " \t\n;":
            i += 1
            continue
        if c == "#":
            k = script.find("\n", i)
            if k < 0:
                residual.append(script[i:])
                break
            residual.append(script[i:k])
            i = k
            continue
        j, ok = _skip_sed_address(script, i)
        if not ok:
            return subs, "unterminated address at %r" % script[i:i + 12], residual
        if j > i:
            residual.append(script[i:j])
            i = j
        while i < n and script[i] in " \t":
            i += 1
        if i < n and script[i] == "!":
            i += 1
        if i >= n:
            break
        c = script[i]
        if c in ("s", "y"):
            if i + 1 >= n:
                return subs, "truncated %s command" % c, residual
            delim = script[i + 1]
            if delim.isalnum() or delim in " \t\n\\":
                return subs, "unmodelled delimiter %r" % delim, residual
            parts: List[str] = []
            j = i + 2
            cur: List[str] = []
            while j < n and len(parts) < 2:
                ch = script[j]
                if ch == "\\" and j + 1 < n:
                    cur.append(script[j:j + 2])
                    j += 2
                    continue
                # A command substitution is ONE atom: a `|` inside
                # `$( ... sed 's/[|&]/.../' )` is not this script's delimiter.
                if ch == "$" and j + 1 < n and script[j + 1] == "(":
                    try:
                        k, seg = _read_balanced(script, j + 1, "(", ")")
                    except ParseError:
                        return subs, "unbalanced $( in s%s..." % delim, residual
                    cur.append("$" + seg)
                    j = k
                    continue
                if ch == "`":
                    k = script.find("`", j + 1)
                    if k < 0:
                        return subs, "unbalanced backtick in s%s..." % delim, residual
                    cur.append(script[j:k + 1])
                    j = k + 1
                    continue
                if ch == delim:
                    parts.append("".join(cur))
                    cur = []
                    j += 1
                    continue
                cur.append(ch)
                j += 1
            if len(parts) < 2:
                return subs, "unterminated s%s...%s" % (delim, delim), residual
            flags: List[str] = []
            while j < n and script[j] not in " \t\n;}":
                flags.append(script[j])
                j += 1
            if c == "y":
                return subs, "y/// transliteration is not modelled", residual
            subs.append(Subst(delim, parts[0], parts[1], "".join(flags)))
            i = j
            continue
        if c in ("{", "}"):
            i += 1
            continue
        if c in _SED_SIMPLE:
            i += 1
            while i < n and script[i].isdigit():
                i += 1
            continue
        if c in _SED_LABEL:
            i += 1
            k = i
            while k < n and script[k] not in ";\n":
                k += 1
            residual.append(script[i:k])
            i = k
            continue
        if c in _SED_TEXT or c in _SED_FILE:
            # a/i/c text and r/w file operands are shapes we do not model.
            return subs, "unmodelled sed command %r" % c, residual
        return subs, "unmodelled sed construct at %r" % script[i:i + 12], residual
    return subs, None, residual


def _names_in_text(text: str) -> Set[str]:
    """Every parameter an expansion in this text READS.

    Used on one side of a parsed substitution, where the quoting context has
    already been resolved.  The caller intersects the result with the names the
    SHELL actually expands in the raw token, which is what keeps sed's own `$`
    (the last-line address) out of the interpolation set.

    Shares ONE recursive scanner with `expansion_names`.  Two extractors meant
    a nested `${safe:-$RAW}` could be seen by the authority set and not by the
    per-name prover, or the reverse — and either gap re-opens rail R6-03.
    """
    return _expansion_refs(text, honour_single_quotes=False)[0]


# Options of sed/awk that take a SEPARATE argument.  An option we do not model
# means we cannot say which operand is the script, which blocks.
_EDITOR_OPT_ARG = frozenset(("-e", "-f", "--expression", "--file",
                             "-v", "--assign", "-F", "--field-separator",
                             "--include", "-l"))
_EDITOR_OPT_NOARG = frozenset(("-n", "-r", "-E", "-s", "-u", "-z", "--quiet",
                               "--silent", "--regexp-extended", "--posix",
                               "--separate", "--null-data", "--debug",
                               "--sandbox", "--traditional", "-a", "--"))


def _script_arguments(cmd: Command) -> Tuple[List[Tok], Optional[str]]:
    """EVERY script a sed/awk invocation runs, or a reason it is unknown.

    `sed -e A -e B` runs both.  Returning only the first is how a raw
    interpolation in a second `-e` would never be looked at — the same
    "a shape we did not enumerate comes out safe" class this pass inverts.
    An option the model does not know returns no scripts at all, which blocks.
    """
    args = [a for a in cmd.toks[1:] if a.kind == "word"]
    scripts: List[Tok] = []
    i = 0
    n = len(args)
    while i < n:
        a = args[i]
        txt = a.text
        looks_opt = (not a.quoted) and txt.startswith("-") and txt != "-"
        if looks_opt:
            base = txt.split("=", 1)[0]
            if txt == "--":
                i += 1
                break
            if base in _EDITOR_OPT_ARG:
                if base in ("-e", "-f", "--expression", "--file"):
                    if base in ("-f", "--file"):
                        return [], "script read from a FILE (%s)" % base
                    if "=" in txt:
                        return [], "script supplied inline through %s" % base
                    if i + 1 >= n:
                        return [], "%s without an argument" % base
                    scripts.append(args[i + 1])
                    i += 2
                    continue
                i += 1 if "=" in txt else 2
                continue
            if base in _EDITOR_OPT_NOARG or re.match(r"^-[nrEszui]+$", base):
                i += 1
                continue
            return [], "unmodelled option %r" % txt
        # The first positional operand is the script ONLY when no -e supplied
        # one; otherwise every positional is an input file.
        if not scripts:
            scripts.append(a)
        break
    if not scripts:
        return [], "no script operand found"
    return scripts, None


def verdict_class_b(fm: FileModel, cmd: Command,
                    editor: str) -> Tuple[str, str, str, str]:
    toks, err = _script_arguments(cmd)
    if not toks:
        return (VERDICT_INDETERMINATE, R_SCRIPT_DYNAMIC,
                err or "no script", editor)
    if len(toks) > 1:
        # `sed -e A -e B` runs BOTH scripts; judging only the first is how a
        # raw interpolation in a second -e would pass unseen.
        worst_multi = None
        idents = []
        for one in toks:
            r = _verdict_one_script(fm, cmd, editor, one)
            idents.append(r[3])
            worst_multi = _worse(worst_multi, r[:3])
        return worst_multi + (" ;; ".join(idents)[:70],)
    return _verdict_one_script(fm, cmd, editor, toks[0])


def _verdict_one_script(fm: FileModel, cmd: Command, editor: str,
                        tok: Tok) -> Tuple[str, str, str, str]:
    raw = tok.text
    names, cmd_subst = expansion_names(raw)
    script = canon_operand(tok)
    ident = re.sub(r"\s+", " ", script).strip()[:70]

    # A script assembled wholesale from an expansion is not a literal we can
    # reason about at all.  The test is on what the SHELL expands: an awk
    # program opening with `$0` inside single quotes is a literal, not a
    # dynamic script, and reading that off the canon form got it backwards.
    lead = re.match(r'^\s*"?\s*\$\{?([A-Za-z_][A-Za-z0-9_]*)?', raw)
    if lead and (lead.group(1) in names or (cmd_subst and "$(" in raw[:4])):
        return (VERDICT_INDETERMINATE, R_SCRIPT_DYNAMIC,
                "script comes from an expansion: %s" % raw[:60], ident)

    if editor in ("awk", "gawk", "mawk"):
        if not names and not cmd_subst:
            return (VERDICT_NA, "n0-no-interpolation",
                    "awk program is fully literal", ident)
        return (VERDICT_INDETERMINATE, R_AWK_EXPANSION,
                "awk program interpolates %s"
                % (", ".join(sorted("$" + x for x in names))
                   or "a command substitution"), ident)

    subs, err, residual = parse_sed_script(script)
    if err:
        return (VERDICT_INDETERMINATE, R_SCRIPT_UNPARSED, err, ident)

    worst: Optional[Tuple[str, str, str]] = None

    covered: Set[str] = set()
    covered_cmd_subst = False

    for sub in subs:
        for side, text in (("pattern", sub.pattern), ("replacement", sub.repl)):
            if cmd_subst and ("`" in text or "$(" in text):
                covered_cmd_subst = True
                # The names inside this substitution ARE accounted for by it;
                # leaving them out made the leftover check fire on a value the
                # b4 proof had already cleared.
                covered.update(_names_in_text(text) & names)
                if _inline_escape_covers(text, sub, side):
                    worst = _worse(worst, (VERDICT_GUARDED,
                                           "b4-inline-escape-substitution",
                                           "the interpolation is escaped in "
                                           "place for %r" % sub.delim))
                else:
                    worst = _worse(worst, (VERDICT_INDETERMINATE, R_CMD_SUBST,
                                           "command substitution on the %s "
                                           "side of s%s" % (side, sub.delim)))
                continue
            for name in sorted(_names_in_text(text)):
                if name not in names:
                    continue        # literal `$` (sed's own), not an expansion
                covered.add(name)
                worst = _worse(worst, _prove_interp_safe(fm, cmd, name, sub, side))

    # Every expansion the SHELL performs must be accounted for by one of the
    # substitutions we modelled.  One that is not sits in an address, a label
    # or a construct we did not model, and that is not a shape this instrument
    # may clear.
    leftover = names - covered
    if leftover:
        worst = _worse(worst, (VERDICT_INDETERMINATE, R_SCRIPT_UNPARSED,
                               "expansion outside every modelled substitution: %s"
                               % ", ".join(sorted("$" + x for x in leftover))))
    if cmd_subst and not covered_cmd_subst:
        worst = _worse(worst, (VERDICT_INDETERMINATE, R_CMD_SUBST,
                               "command substitution outside every modelled "
                               "substitution"))

    if worst is None:
        return (VERDICT_NA, "n0-no-interpolation",
                "no expansion inside any substitution", ident)
    return worst + (ident,)


_ORDER = {VERDICT_NA: 0, VERDICT_GUARDED: 1, VERDICT_INDETERMINATE: 2,
          VERDICT_UNGUARDED: 3}


def _worse(a: Optional[Tuple[str, str, str]],
           b: Optional[Tuple[str, str, str]]) -> Optional[Tuple[str, str, str]]:
    if a is None:
        return b
    if b is None:
        return a
    return a if _ORDER[a[0]] >= _ORDER[b[0]] else b


_RE_ESCAPE_SED = re.compile(
    r"sed\s+(?P<q>['\"])s(?P<d>[^\w\s])(?P<cls>\[[^]]*\])(?P=d)(?P<rep>[^/|#@,]*?)(?P=d)")
# The ONLY replacement that puts a backslash in front of the match.  In sed,
# `\&` is a LITERAL ampersand — it escapes nothing and leaves an active `&`
# for an outer replacement to interpret (rail R5-11).  `\\&` is an escaped
# backslash followed by the whole match, which is the real escape.
_RE_REPL_EMITS_BACKSLASH = re.compile(r"^\\\\&$")


def _repl_emits_backslash(rep: str, quote: str) -> bool:
    """Does this replacement actually EMIT a backslash before the match?"""
    if quote == '"':
        # Inside double quotes the shell already halves the backslashes.
        rep = rep.replace("\\\\", "\\")
    return _RE_REPL_EMITS_BACKSLASH.match(rep) is not None


def _escape_assignment_covers(rhs_raw: str, sub: Subst, side: str) -> bool:
    """Form b1: the assignment escapes THIS delimiter AND inserts a backslash.

    ``sed 's/[|&\\]/&/g'`` is a no-op — it replaces the match with itself — and
    ``sed 's/[|&\\]/\\&/g'`` is no better, because sed reads `\\&` as a literal
    ampersand.  A real escape is `\\\\&`: an escaped backslash, then the match.
    """
    m = _RE_ESCAPE_SED.search(rhs_raw)
    if not m:
        return False
    cls = m.group("cls")
    rep = m.group("rep")
    needed = {sub.delim}
    if side == "replacement":
        needed.add("&")
    needed.add("\\")
    body = cls[1:-1]
    if body.startswith("^"):
        return False
    for ch in needed:
        if ch == "\\":
            if "\\\\" not in body and "\\" not in body:
                return False
            continue
        if ch not in body:
            return False
    return _repl_emits_backslash(rep, m.group("q"))


def _sole_pipeline_producer(text: str) -> Optional[Command]:
    """The LAST stage of a substitution that is exactly one pipeline.

    Form b4 claims the interpolated text IS the escaped value.  That is only
    true when the substitution produces nothing else, so the body must be a
    single pipeline (no `;`, `&&`, `||`, `&` or newline) and the value the
    shell captures is its final stage's output.  Accepting anything that merely
    starts with ``$(`` and ends with ``)`` let
    ``$(printf ... | sed 'safe'; printf %s "$raw")`` through, where the last
    command appends the RAW value (rail R5-12).
    """
    stripped = text.strip()
    if not stripped.startswith("$("):
        return None
    try:
        end, seg = _read_balanced(stripped, 1, "(", ")")
    except ParseError:
        return None
    if end != len(stripped):
        return None                     # `$(a) $(b)`, or trailing text
    body = seg[1:-1]
    try:
        toks = lex(body)
    except ParseError:
        return None
    holder = LogicalLine(0, body, toks)
    cmds = split_commands(holder, 0)
    if not cmds:
        return None
    for c in cmds[1:]:
        if c.prev_op not in ("|", "|&"):
            return None                 # a second producer, not a pipeline
    return cmds[-1]


def _inline_escape_covers(text: str, sub: "Subst", side: str) -> bool:
    """Form b4: `$( printf %s "$v" | sed 's/[<delim>&\\]/\\\\&/g' )` in place.

    Same proof as b1 — the class must cover THIS delimiter and the replacement
    must actually insert a backslash — but read off the substitution expression
    itself, and only when that substitution's SOLE producer is the escaping
    sed.
    """
    last = _sole_pipeline_producer(text)
    if last is None:
        return False
    body = [t for t in last.toks if t.kind == "word"]
    while body and not body[0].quoted and body[0].text in _KEYWORDS:
        body = body[1:]
    if not body or body[0].quoted:
        return False
    if command_basename(canon_operand(body[0])) not in ("sed", "gsed"):
        return False
    raw = " ".join(t.text for t in last.toks)
    return _escape_assignment_covers(raw, sub, side)


def _class_excludes(cls_body: str, sub: Subst) -> bool:
    if cls_body.startswith("^") or cls_body.startswith("!"):
        return False
    bad = {sub.delim, "&", "\\", "\n"}
    expanded = set()
    i = 0
    while i < len(cls_body):
        if i + 2 < len(cls_body) and cls_body[i + 1] == "-":
            lo, hi = cls_body[i], cls_body[i + 2]
            if ord(lo) <= ord(hi):
                for o in range(ord(lo), ord(hi) + 1):
                    expanded.add(chr(o))
            i += 3
            continue
        expanded.add(cls_body[i])
        i += 1
    return not (expanded & bad)


def _validation_dominates(fm: FileModel, cmd: Command, name: str,
                          sub: Subst) -> bool:
    """Form b2: a dominating abort-unless-matches-closed-class validation.

    Two shapes, both requiring the abort to be UNCONDITIONAL in its branch:

      [[ "$v" =~ ^[A-Za-z0-9_-]+$ ]] || die        (guard at the use's level)
      case "$v" in *[!A-Za-z0-9_-]*) die ;; esac   (abort in the reject arm)

    The `case` shape needs its own reasoning: the aborting arm does NOT
    dominate the use — the point is precisely that reaching the use means that
    arm was not taken.  What must dominate is the `case` STATEMENT.
    """
    target = "$" + name
    use_scope = fm.lines[cmd.line_idx].scope

    for idx, ll in enumerate(fm.lines):
        if idx >= cmd.line_idx:
            break
        if dominates(ll.scope, idx, use_scope, cmd.line_idx, fm):
            for i, c in enumerate(fm.cmds_of(idx)):
                if not _regex_validation_matches(c, target, sub):
                    continue
                # The abort must be THIS command's abort.  Scanning the whole
                # logical line for any later `|| die` accepted
                # `[[ "$v" =~ ^..$ ]]; true || die`, where the abort belongs to
                # `true` and never fires (rail R5-15).
                cmds = fm.cmds_of(idx)
                if i + 1 < len(cmds) and cmds[i + 1].prev_op == "||" \
                        and _is_abort_command(fm, cmds[i + 1]):
                    if rebound_between(fm, {name}, idx, cmd.line_idx) is None:
                        return True
                    continue
                if c.negated:
                    uid = _find_then_uid(fm, idx)
                    if uid is not None \
                            and _branch_aborts_at_own_level(fm, uid, idx + 1) \
                            and rebound_between(fm, {name}, idx,
                                                cmd.line_idx) is None:
                        return True

        if _case_rejects_outside_class(fm, idx, cmd.line_idx, use_scope,
                                       target, sub) \
                and rebound_between(fm, {name}, idx, cmd.line_idx) is None:
            return True
    return False


# A validation is only a proof when the class is anchored at BOTH ends.  With
# `^` optional, `[[ "$v" =~ [A-Za-z]+$ ]]` accepted `|safe` — which still
# carries the sed delimiter — as validated (rail R5-14).
_RE_ANCHORED_CLASS = re.compile(r"^\^\[([^]]+)\][*+]?\$$")


def _regex_validation_matches(cmd: Command, target: str, sub: Subst) -> bool:
    """`[[ <target> =~ ^[<closed class>]+$ ]]`, matched on TOKENS.

    The previous pass asked whether the target string occurred ANYWHERE in the
    logical line's text, so a validation of `$value` was credited to a later
    raw interpolation of `$v` (rail R5-13).  Here the left operand of `=~` must
    be that exact token.
    """
    toks = cmd.toks
    for j, t in enumerate(toks):
        if t.kind != "word" or t.quoted or t.text != "=~":
            continue
        if j == 0 or j + 1 >= len(toks):
            return False
        if canon_operand(toks[j - 1]) != target:
            return False
        rhs = toks[j + 1]
        # Bash treats a QUOTED right-hand side of `=~` as a literal STRING, not
        # a regex.  `[[ "$V" =~ "^[A-Za-z]+$" ]]` therefore matches only the
        # literal text `^[A-Za-z]+$` — it accepts every other value, including
        # one carrying the sed delimiter.  Crediting it as closed-charset
        # validation was a proof of something the shell never checks
        # (rail R6-05).  Any quoting at all disqualifies it: a partially
        # quoted RHS (`^[a-z]+"$"`) is likewise not the regex it looks like.
        if rhs.quoted or '"' in rhs.text or "'" in rhs.text:
            return False
        m = _RE_ANCHORED_CLASS.match(canon_operand(rhs))
        if not m:
            return False
        return _class_excludes(m.group(1), sub)
    return False


def _case_rejects_outside_class(fm: FileModel, idx: int, use_idx: int,
                                use_scope: Tuple[int, ...], target: str,
                                sub: Subst) -> bool:
    ll = fm.lines[idx]
    toks = ll.toks
    head = [t for t in toks if t.kind == "word"]
    if not head or head[0].quoted or head[0].text != "case":
        return False
    if len(head) < 2 or canon_operand(head[1]) != target:
        return False
    if not dominates(ll.scope, idx, use_scope, use_idx, fm):
        return False
    # The `case` frame this line opened.
    case_uid: Optional[int] = None
    for j in range(idx + 1, len(fm.lines)):
        nxt = fm.lines[j].scope
        if len(nxt) > len(ll.scope) and nxt[:len(ll.scope)] == ll.scope:
            case_uid = nxt[len(ll.scope)]
            break
    if case_uid is None:
        return False
    for j in range(idx + 1, len(fm.lines)):
        arm = fm.lines[j]
        if case_uid not in arm.scope:
            break
        if not arm.pattern_upto:
            continue
        pattern = " ".join(t.text for t in arm.toks[:arm.pattern_upto])
        m = re.search(r"\*\[[!^]([^]]+)\]\*", pattern)
        if not m or not _class_excludes(m.group(1), sub):
            continue
        # The arm frame opens DURING this line, so it is not in `arm.scope`
        # (which is the scope at line entry); read it off the next line.
        arm_uid: Optional[int] = None
        for k in range(j + 1, len(fm.lines)):
            nxt = fm.lines[k].scope
            if len(nxt) > len(arm.scope) and nxt[:len(arm.scope)] == arm.scope:
                arm_uid = nxt[len(arm.scope)]
            break
        rest = fm.cmds_of(j)
        if any(c.prev_op not in ("&&", "||") and _is_abort_command(fm, c)
               for c in rest):
            return True
        if arm_uid is not None and _branch_aborts_at_own_level(fm, arm_uid, j + 1):
            return True
    return False


def _prove_interp_safe(fm: FileModel, cmd: Command, name: str, sub: Subst,
                       side: str) -> Tuple[str, str, str]:
    region = _region_for(fm, cmd.line_idx, "$" + name)
    assigns = [(i, rhs, c) for (i, rhs, c) in fm.assigns.get(name, [])
               if region[0] <= i <= region[1]]

    if _validation_dominates(fm, cmd, name, sub):
        return (VERDICT_GUARDED, "b2-closed-charset-validated",
                "$%s validated against a closed class before s%s"
                % (name, sub.delim))

    # A name nothing in the region ever binds (`$1`, `$@`, `$?`, an inherited
    # environment variable) has no assignment to prove anything with.
    if assigns:
        all_escape = True
        any_dominating = False
        all_literal_safe = True
        any_literal_dominating = False
        for (i, _rhs, c) in assigns:
            raw = " ".join(t.text for t in c.toks)
            reaches = dominates(fm.lines[i].scope, i,
                                fm.lines[cmd.line_idx].scope, cmd.line_idx, fm)
            if _escape_assignment_covers(raw, sub, side):
                if reaches:
                    any_dominating = True
            else:
                all_escape = False
            val = _rhs
            if _RE_HAS_EXPANSION.search(val) or sub.delim in val or "&" in val \
                    or "\\" in val:
                all_literal_safe = False
            elif reaches:
                any_literal_dominating = True
        # A rebinding the assignment index does not carry (`read`, a `for`
        # variable, `getopts`) makes every assignment-based proof stale.
        rebound = fm.rebinds.get(name, [])
        clean = not any(region[0] <= i <= region[1] for i in rebound)
        if all_escape and any_dominating and clean:
            return (VERDICT_GUARDED, "b1-delimiter-escape-dominates",
                    "every assignment to $%s escapes %r" % (name, sub.delim))
        # b3 needs a SAFE assignment that actually reaches the use.  Without
        # it, `sed "s|x|$v|g"` followed LATER by `v=safe`, or a safe assignment
        # in a branch that may not run, was called literal-only even when $v
        # came from the environment or the caller (rail R5-10).
        if all_literal_safe and any_literal_dominating and clean:
            return (VERDICT_GUARDED, "b3-literal-only",
                    "$%s is only ever assigned safe literals, and one of them "
                    "reaches this use" % name)
        if all_literal_safe and not any_literal_dominating:
            return (VERDICT_INDETERMINATE, R_ESCAPE_UNPROVEN,
                    "every assignment to $%s is a safe literal but none of "
                    "them dominates this use" % name)
        if any_dominating or all_escape or all_literal_safe:
            return (VERDICT_INDETERMINATE, R_ESCAPE_UNPROVEN,
                    "$%s is escaped or literal on some paths only" % name)

    return (VERDICT_UNGUARDED, "",
            "$%s interpolated raw on the %s side of s%s...%s"
            % (name, side, sub.delim, sub.delim))


# --------------------------------------------------------------------------
# Site
# --------------------------------------------------------------------------


class Site(object):
    __slots__ = ("rel_path", "lineno", "cls", "verdict", "form", "detail",
                 "fn", "snippet", "operand", "ordinal")

    def __init__(self, rel_path: str, lineno: int, cls: str, verdict: str,
                 form: str, detail: str, fn: str, snippet: str,
                 operand: str) -> None:
        self.rel_path = rel_path
        self.lineno = lineno
        self.cls = cls
        self.verdict = verdict
        self.form = form
        self.detail = detail
        self.fn = fn
        self.snippet = snippet
        self.operand = operand
        # Which of the identically-shaped sites in this file this one is.
        # Without it, three byte-identical `[[ -e "$dst" ]]` guards in three
        # functions collapse to ONE baseline entry and two of them go
        # unrecorded — a silent hole in the ratchet.
        self.ordinal = 0

    @property
    def blocking(self) -> bool:
        return self.verdict in BLOCKING_VERDICTS

    def fingerprint(self) -> str:
        payload = "|".join([self.rel_path, self.cls, self.fn, self.operand,
                            re.sub(r"\s+", " ", self.snippet).strip(),
                            "#%d" % self.ordinal])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def key(self) -> Tuple[str, str, str]:
        return (self.rel_path, self.cls, self.fingerprint())

    def to_json(self) -> Dict[str, object]:
        return {
            "path": self.rel_path,
            "line": self.lineno,
            "class": self.cls,
            "verdict": self.verdict,
            "form": self.form,
            "detail": self.detail,
            "function": self.fn,
            "operand": self.operand,
            "snippet": self.snippet,
            "fingerprint": self.fingerprint(),
            "blocking": self.blocking,
        }


# --------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------


def _display_head(cmd: Command) -> str:
    """The program name a reader would say this command calls.

    Keywords, redirections and leading `VAR=value` assignments are not the
    command, and letting them stand in for it put `LC_ALL=C` and `if` in the
    operand field — which is part of the site FINGERPRINT.
    """
    body = [t for t in _strip_redirections(cmd.toks) if t.kind == "word"]
    while body and not body[0].quoted and body[0].text in _KEYWORDS:
        body = body[1:]
    stripped, ok = _strip_prefixes(body)
    if ok and stripped:
        body = stripped
    if not body or body[0].quoted:
        return "?"
    return command_basename(canon_operand(body[0])) or "?"


def _guard_is_live(fm: FileModel, cmd: Command,
                   canon: str) -> Tuple[bool, Optional[Tuple[str, int]]]:
    """Does a proven `-L` guard dominate this use with its value intact?"""
    region = _region_for(fm, cmd.line_idx, canon)
    aliases = alias_set(fm, canon, region)
    guards = (_nofollow_guard_sites(fm, aliases, region)
              + _helper_guard_sites(fm, aliases, region))
    names: Set[str] = set()
    for c in aliases:
        names |= var_names(c)
    stale: Optional[Tuple[str, int]] = None
    for gi, gs in guards:
        if not dominates(gs, gi, fm.lines[cmd.line_idx].scope, cmd.line_idx, fm):
            continue
        rb = rebound_between(fm, names, gi, cmd.line_idx)
        if rb is None:
            return True, None
        if stale is None:
            stale = rb
    return False, stale


def verdict_class_c(fm: FileModel, cmd: Command, kind: str,
                    watched: Sequence[Tuple[str, Tok]]) -> Tuple[str, str, str]:
    """Is this candidate write proven safe?

    Same theorem as class A — a non-dereferencing guard must dominate — but
    reached from the WRITE rather than from a test.  That is what makes
    discovery fail-closed: a write whose path no test ever pointed at produced
    no class-A site, and before this class it therefore produced no site at
    all.

    The two roles are kept apart on purpose.  A PROVEN destination with no
    guard is `desguardado` — the instrument knows it writes.  An operand of a
    command the model cannot place is `indeterminado` — it may write, and "may"
    is not "does".  Collapsing the two would report `diff -q "$a" "$b"` as a
    write to `$a`.
    """
    head = "?"
    if cmd.toks and cmd.toks[0].kind == "word":
        head = command_basename(canon_operand(cmd.toks[0])) or "?"
    if kind == "opaque":
        # Opaque FLOORS the verdict at indeterminate; it does not CAP it.
        # A destination the model did prove — a redirection on `bash ... >"$LOG"`
        # — keeps the sharper `desguardado`, because collapsing every opaque
        # command to "indeterminate" would discard a write the instrument
        # actually knows about.  What opaque forbids is the other direction:
        # a body this model never reads can never be proven safe.
        for role, tok in watched:
            canon = canon_operand(tok)
            if not canon or role != "write":
                continue
            live, _rb = _guard_is_live(fm, cmd, canon)
            if not live:
                return (VERDICT_UNGUARDED, "",
                        "%s writes %s with no dominating -L guard, and runs "
                        "text this model never sees" % (head, canon))
        return (VERDICT_INDETERMINATE, R_OPAQUE,
                "%s runs text this model never sees" % head)

    unproven_writes: List[str] = []
    unproven_unknown: List[str] = []
    stale: Optional[Tuple[str, int]] = None
    for role, tok in watched:
        canon = canon_operand(tok)
        if not canon:
            continue
        live, rb = _guard_is_live(fm, cmd, canon)
        if live:
            continue
        if rb is not None and stale is None:
            stale = rb
        (unproven_writes if role == "write" else unproven_unknown).append(canon)

    if not unproven_writes and not unproven_unknown:
        return (VERDICT_GUARDED, "a1-nofollow-test-dominates",
                "every expanded operand is dominated by a proven -L guard")
    if stale is not None:
        first = (unproven_writes or unproven_unknown)[0]
        return (VERDICT_INDETERMINATE, R_GUARD_STALE,
                "a -L guard exists for %s but $%s is rebound at line %d before "
                "this write" % (first, stale[0], fm.lines[stale[1]].lineno))
    if unproven_writes:
        return (VERDICT_UNGUARDED, "",
                "%s writes %s with no dominating -L guard"
                % (head, ", ".join(sorted(set(unproven_writes)))))
    return (VERDICT_INDETERMINATE, R_CANDIDATE,
            "%s is not proven read-only and may write %s"
            % (head, ", ".join(sorted(set(unproven_unknown)))))


def census_file(rel_path: str, raw: str,
                corpus: Optional["Corpus"] = None,
                model: Optional[FileModel] = None) -> List[Site]:
    fm = model if model is not None else build_file_model(rel_path, raw)
    if fm.unparseable:
        return [Site(rel_path, 1, CLASS_PARSE, VERDICT_INDETERMINATE, R_PARSE,
                     fm.unparseable, "", "<file>", "<file>")]

    sites: List[Site] = []

    for t in fm.tests:
        if t.op not in _TEST_OPS_FOLLOW:
            continue
        verdict, form, detail = verdict_class_a(fm, t, corpus)
        span = fm.func_at(t.line_idx)
        sites.append(Site(rel_path, t.lineno, CLASS_SYMLINK, verdict, form,
                          detail, span.name if span else "",
                          fm.lines[t.line_idx].snippet(), t.canon))

    # A test expression the model could not walk is a BLOCKING site, not a
    # silent skip.  This is the half of the inversion the 4th pass missed:
    # inverting the VERDICT rule while leaving DISCOVERY fail-open still lets
    # an unmodelled form be invisible (rail R5-01).
    for (line_idx, lineno, why, snippet) in fm.unmodelled_tests:
        span = fm.func_at(line_idx)
        sites.append(Site(rel_path, lineno, CLASS_SYMLINK,
                          VERDICT_INDETERMINATE, R_TEST_UNMODELED, why,
                          span.name if span else "", snippet, "<test>"))

    for cmd in list(fm.commands) + list(fm.subst_commands):
        body = [t for t in cmd.toks if t.kind == "word"]
        while body and not body[0].quoted and body[0].text in _KEYWORDS:
            body = body[1:]
        stripped, ok = _strip_prefixes(body)
        if not ok or not stripped:
            continue
        if stripped[0].quoted:
            continue
        # `/usr/bin/sed` runs sed.  Matching only the bare name meant a
        # path-qualified invocation produced no class-B site (rail R5-02).
        name = command_basename(canon_operand(stripped[0]))
        if name not in _STREAM_EDITORS:
            continue
        probe = Command(stripped, cmd.line_idx, cmd.lineno, cmd.prev_op)
        verdict, form, detail, ident = verdict_class_b(fm, probe, name)
        span = fm.func_at(cmd.line_idx)
        sites.append(Site(rel_path, cmd.lineno, CLASS_SED, verdict, form,
                          detail, span.name if span else "",
                          fm.lines[cmd.line_idx].snippet(),
                          "%s:%s" % (name, ident)))

    for (cmd, kind, watched) in fm.candidates:
        verdict, form, detail = verdict_class_c(fm, cmd, kind, watched)
        span = fm.func_at(cmd.line_idx)
        head = _display_head(cmd)
        operand = "%s:%s" % (head, ",".join(sorted(
            set(canon_operand(t) for _r, t in watched if canon_operand(t))))[:60])
        sites.append(Site(rel_path, cmd.lineno, CLASS_WRITE, verdict, form,
                          detail, span.name if span else "",
                          fm.lines[cmd.line_idx].snippet(), operand))

    return sites


def discover_shell_files(scan_root: Path, repo_root: Path) -> List[Path]:
    out: List[Path] = []
    if not scan_root.exists():
        return out
    for p in sorted(scan_root.rglob("*.sh")):
        try:
            rel = p.relative_to(repo_root).as_posix()
        except ValueError:
            rel = p.as_posix()
        if any(rel.startswith(x) for x in EXCLUDED_REL_PREFIXES):
            continue
        out.append(p)
    return out


def run_census(repo_root: Path,
               scan_root: Path) -> Tuple[List[Site], List[Dict[str, object]]]:
    """Census every discovered shell file, and REPORT the discovery itself.

    The inventory is returned alongside the sites because a file that produced
    no site is otherwise indistinguishable from a file discovery never reached
    (rail R5-16).  `doctor.sh` producing zero sites is a claim about
    `doctor.sh`; `doctor.sh` missing from the scan is a claim about the
    instrument, and the output has to tell them apart.
    """
    sites: List[Site] = []
    files: List[Dict[str, object]] = []
    pending: List[Tuple[str, str]] = []
    for p in discover_shell_files(scan_root, repo_root):
        try:
            rel = p.relative_to(repo_root).as_posix()
        except ValueError:
            rel = p.as_posix()
        if p.is_symlink() or not p.is_file():
            # Skipping silently would be a hole the size of one `ln -s`.
            sites.append(Site(rel, 1, CLASS_PARSE, VERDICT_INDETERMINATE,
                              R_UNREADABLE,
                              "shell file is a symlink or not a regular file",
                              "", "<file>", "<file>"))
            files.append({"path": rel, "status": "symlink-or-not-regular",
                          "sites": 1, "blocking": 1})
            continue
        try:
            raw = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # INPUT failure, not infrastructure: block, never skip.
            sites.append(Site(rel, 1, CLASS_PARSE, VERDICT_INDETERMINATE,
                              R_UNREADABLE, str(exc), "", "<file>", "<file>"))
            files.append({"path": rel, "status": "unreadable",
                          "sites": 1, "blocking": 1})
            continue
        pending.append((rel, raw))

    # Phase 1: parse EVERY file before judging any of them, so a predicate
    # defined in a shared library is visible to the writers that consult it.
    corpus = Corpus()
    models: List[Tuple[str, str, FileModel]] = []
    for rel, raw in pending:
        fm = build_file_model(rel, raw)
        models.append((rel, raw, fm))
        if not fm.unparseable:
            corpus.add(fm)

    # Phase 2: judge.
    for rel, raw, fm in models:
        found = census_file(rel, raw, corpus, fm)
        status = "unparseable" if any(s.cls == CLASS_PARSE for s in found) \
            else "scanned"
        files.append({"path": rel, "status": status, "sites": len(found),
                      "blocking": sum(1 for s in found if s.blocking)})
        sites.extend(found)
    files.sort(key=lambda f: str(f["path"]))
    sites.sort(key=lambda s: (s.rel_path, s.lineno, s.cls))
    counter: Dict[Tuple[str, str, str, str, str], int] = {}
    for s in sites:
        k = (s.rel_path, s.cls, s.fn, s.operand,
             re.sub(r"\s+", " ", s.snippet).strip())
        s.ordinal = counter.get(k, 0)
        counter[k] = s.ordinal + 1
    return sites, files


# --------------------------------------------------------------------------
# Baseline
# --------------------------------------------------------------------------

BASELINE_HEADER = """\
# installer-write-safety-baseline.txt — PLAN-185 W0
# (5th pass: inverted VERDICT rule + fail-CLOSED DISCOVERY)
#
# Every BLOCKING site (desguardado + indeterminado) the census currently finds.
# A blocking site absent from this file fails the gate (exit 1); an entry here
# that matches nothing also fails (rot). Removing a line is how a cure is
# recorded — never how a finding is silenced.
#
# WHAT A LINE HERE MEANS, stated honestly. It is a RATCHET entry: this site is
# known to the census, and no NEW one may appear without a decision. It is NOT
# a per-site human review — there are hundreds of them, and claiming each was
# read one by one would be false. `indeterminado` means "the matcher cannot
# prove safety", which after the 5th pass is the default for every command not
# proven read-only. Turning real sites into `guardado` is PLAN-185 W1/W2's job,
# and the count going DOWN is how that work will show up here.
#
# Format: path:line:class:verdict:form-or-reason:fingerprint
# Matching is on (path, class, fingerprint). The line number is informational:
# it is refreshed on every run and drift alone is reported, never fatal.
#
# Regenerate ONLY with an explicit --write-baseline.
"""


def render_baseline(sites: Sequence[Site]) -> str:
    rows = [s for s in sites if s.blocking]
    lines = [BASELINE_HEADER]
    for s in sorted(rows, key=lambda x: (x.rel_path, x.lineno, x.cls)):
        lines.append("%s:%d:%s:%s:%s:%s\n" % (
            s.rel_path, s.lineno, s.cls, s.verdict, s.form or "-",
            s.fingerprint()))
    return "".join(lines)


def load_baseline(path: Path) -> Tuple[Dict[Tuple[str, str, str], Dict[str, str]],
                                       List[str]]:
    """Parse the baseline.  Malformed rows are RETURNED, never dropped.

    A row this loader cannot read is a row that waives nothing and reports
    nothing; swallowing it would let a corrupted baseline look healthy.
    """
    out: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    malformed: List[str] = []
    if not path.exists():
        return out, malformed
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(":", 5)
        if len(parts) != 6:
            malformed.append(line[:120])
            continue
        rel, lineno, cls, verdict, form, fp = parts
        out[(rel, cls, fp)] = {"line": lineno, "verdict": verdict, "form": form}
    return out, malformed


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render_rules(scan_root: str) -> str:
    buf = []
    buf.append("check-installer-write-safety.py — INVERTED rule + FAIL-CLOSED "
               "DISCOVERY (PLAN-185 W0, 5th pass)")
    buf.append("")
    buf.append("Corpus: %s/**/*.sh  (excluding %s)"
               % (scan_root, ", ".join(EXCLUDED_REL_PREFIXES)))
    buf.append("")
    buf.append("DISCOVERY (what becomes a site at all):")
    buf.append("  A command is PROVEN read-only only if its name is below and")
    buf.append("  it opens no file for output.  Every other command whose")
    buf.append("  operands or redirections contain an expansion is a candidate")
    buf.append("  write.  An unmodelled test expression, an unparseable file,")
    buf.append("  and eval/source/exec are sites too — never omissions.")
    buf.append("")
    buf.append("  proven read-only: %s" % " ".join(sorted(PROVEN_READONLY)))
    buf.append("")
    buf.append("  write-capable, classified by OPTION not by name: %s"
               % " ".join(sorted(set(_OUTPUT_MODE_OPT)
                                 | set(_OUTPUT_MODE_LAST)
                                 | set(_INPLACE_FLAGS)
                                 | _WRITERS_LAST | _WRITERS_ALL)))
    buf.append("")
    buf.append("Safety is a THEOREM, proven only by one of these forms:")
    buf.append("")
    for fid, desc in ALLOWLIST:
        buf.append("  %s" % fid)
        for chunk in _wrap(desc, 68):
            buf.append("      %s" % chunk)
    buf.append("")
    buf.append("Everything else is `indeterminado`, which BLOCKS. Reason codes:")
    for code, why in (
            (R_PARSE, "the file's quotes/heredocs/block stack do not balance"),
            (R_UNREADABLE, "the file could not be read or decoded"),
            (R_OCCURRENCE, "the tested path reaches a command we do not model"),
            (R_GUARD_NOT_DOM, "a -L guard exists but does not dominate the write"),
            (R_SCRIPT_DYNAMIC, "the sed/awk script is not a literal"),
            (R_SCRIPT_UNPARSED, "the sed/awk script uses a construct we do not model"),
            (R_CMD_SUBST, "an unproven command substitution sits inside it"),
            (R_AWK_EXPANSION, "an awk PROGRAM interpolates a shell value"),
            (R_ESCAPE_UNPROVEN, "the value is escaped on some paths only"),
            (R_GUARD_STALE, "a -L guard exists but the value was rebound after it"),
            (R_PRED_AMBIGUOUS, "a guard predicate is defined 0 or >1 times"),
            (R_PRED_ARG_UNBOUND, "a guard predicate never saw the destination"),
            (R_TEST_UNMODELED, "a test expression the model cannot walk"),
            (R_CANDIDATE, "a command not proven read-only touches an expansion"),
            (R_OPAQUE, "eval/source/exec runs text this model never sees")):
        buf.append("  %-24s %s" % (code, why))
    buf.append("")
    buf.append("Reachability analysis is deliberately ABSENT: an argument about")
    buf.append("control flow can only make a site more dangerous, never safe, and")
    buf.append("the threat model covers the RESOLVED symlink as well as the")
    buf.append("dangling one, so the branch taken never decided safety.")
    buf.append("")
    buf.append("Exit codes: 0 = baseline holds; 1 = drift (new blocking site, dead")
    buf.append("baseline entry, or --strict with any indeterminate); 2 = ZERO sites")
    buf.append("found, which FAILS by design (broken search, not a clean corpus).")
    return "\n".join(buf)


def _wrap(text: str, width: int) -> List[str]:
    words = text.split()
    out: List[str] = []
    cur: List[str] = []
    for w in words:
        if cur and sum(len(x) + 1 for x in cur) + len(w) > width:
            out.append(" ".join(cur))
            cur = []
        cur.append(w)
    if cur:
        out.append(" ".join(cur))
    return out


def render_files(files: Sequence[Dict[str, object]]) -> str:
    """Every file discovery reached, whether or not it produced a site."""
    buf = ["discovered shell files: %d" % len(files)]
    for f in files:
        buf.append("  %-22s %4d site(s) %4d blocking  %s"
                   % (f["status"], f["sites"], f["blocking"], f["path"]))
    return "\n".join(buf)


def render_table(sites: Sequence[Site]) -> str:
    buf = []
    by_verdict: Dict[str, int] = {}
    by_class: Dict[Tuple[str, str], int] = {}
    for s in sites:
        by_verdict[s.verdict] = by_verdict.get(s.verdict, 0) + 1
        k = (s.cls, s.verdict)
        by_class[k] = by_class.get(k, 0) + 1
    buf.append("instrument: sha256=%s" % instrument_sha256())
    buf.append("sites: %d" % len(sites))
    for v in (VERDICT_UNGUARDED, VERDICT_INDETERMINATE, VERDICT_GUARDED, VERDICT_NA):
        buf.append("  %-16s %d" % (v, by_verdict.get(v, 0)))
    buf.append("  %-16s %d" % ("BLOCKING",
                               sum(1 for s in sites if s.blocking)))
    buf.append("")
    buf.append("class x verdict:")
    for k in sorted(by_class):
        buf.append("  %-16s %-16s %d" % (k[0], k[1], by_class[k]))
    return "\n".join(buf)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Census of unsafe installer writes (PLAN-185 W0, inverted rule).")
    ap.add_argument("--repo-root", default=None,
                    help="repository root to scan (default: this checkout). "
                         "Selects the CORPUS only; it never relaxes a rule.")
    ap.add_argument("--scan-root", default=DEFAULT_SCAN_ROOT,
                    help="subtree to scan, relative to the repo root")
    ap.add_argument("--baseline", default=None,
                    help="baseline file (default: %s under the repo root)"
                         % DEFAULT_BASELINE_REL)
    ap.add_argument("--write-baseline", action="store_true",
                    help="regenerate the baseline from the current census")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--rules", action="store_true",
                    help="print the allowlist of proven-safe forms and exit")
    ap.add_argument("--strict", action="store_true",
                    help="a baseline entry does NOT waive `indeterminado`: any "
                         "indeterminate site fails")
    args = ap.parse_args(list(argv) if argv is not None else None)

    if args.rules:
        sys.stdout.write(render_rules(args.scan_root) + "\n")
        return 0

    repo_root = Path(args.repo_root).resolve() if args.repo_root else _REPO_ROOT
    scan_root = (repo_root / args.scan_root).resolve()
    baseline_path = (Path(args.baseline) if args.baseline
                     else repo_root / DEFAULT_BASELINE_REL)

    sites, files = run_census(repo_root, scan_root)

    if not sites:
        msg = ("FAIL: the census found ZERO sites under %s. Zero means the "
               "search is broken, not that the corpus is clean." % scan_root)
        if args.json:
            sys.stdout.write(json.dumps({"ok": False, "reason": "zero-sites",
                                         "scan_root": str(scan_root),
                                         "files": files,
                                         "sites": []}, indent=2) + "\n")
        else:
            sys.stderr.write(msg + "\n")
        return 2

    if args.write_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(render_baseline(sites), encoding="utf-8")
        sys.stdout.write("wrote %d blocking entries to %s\n"
                         % (sum(1 for s in sites if s.blocking), baseline_path))
        return 0

    baseline, malformed = load_baseline(baseline_path)
    seen: Set[Tuple[str, str, str]] = set()
    new_blocking: List[Site] = []
    for s in sites:
        if not s.blocking:
            continue
        k = s.key()
        seen.add(k)
        if k not in baseline:
            new_blocking.append(s)
    dead = [k for k in baseline if k not in seen]
    strict_hits = ([s for s in sites if s.verdict == VERDICT_INDETERMINATE]
                   if args.strict else [])

    ok = not new_blocking and not dead and not strict_hits and not malformed

    if args.json:
        sys.stdout.write(json.dumps({
            "ok": ok,
            "scan_root": str(scan_root),
            "baseline": str(baseline_path),
            # Reproducibility contract (report section 5.1): a published
            # number without the instrument digest measures an unknown
            # instrument. render_table() already prints it; --json is the
            # primary machine-readable surface and must carry it too.
            "instrument_sha256": instrument_sha256(),
            # EVERY discovered file, zero-site ones included: absence from the
            # scan and absence of findings are different facts (rail R5-16).
            "files": files,
            "counts": {
                "files": len(files),
                "sites": len(sites),
                "blocking": sum(1 for s in sites if s.blocking),
                VERDICT_UNGUARDED: sum(1 for s in sites
                                       if s.verdict == VERDICT_UNGUARDED),
                VERDICT_INDETERMINATE: sum(1 for s in sites
                                           if s.verdict == VERDICT_INDETERMINATE),
                VERDICT_GUARDED: sum(1 for s in sites
                                     if s.verdict == VERDICT_GUARDED),
                VERDICT_NA: sum(1 for s in sites if s.verdict == VERDICT_NA),
            },
            "new_blocking": [s.to_json() for s in new_blocking],
            "dead_baseline_entries": [{"path": k[0], "class": k[1],
                                       "fingerprint": k[2]} for k in dead],
            "strict_indeterminate": [s.to_json() for s in strict_hits],
            "malformed_baseline_rows": malformed,
            "sites": [s.to_json() for s in sites],
        }, indent=2) + "\n")
        return 0 if ok else 1

    sys.stdout.write(render_table(sites) + "\n")
    sys.stdout.write("\n" + render_files(files) + "\n")
    if new_blocking:
        sys.stdout.write("\nNEW BLOCKING SITES (not in %s):\n" % baseline_path)
        for s in new_blocking:
            sys.stdout.write("  %s:%d  %s  %s  %s  [%s]\n" % (
                s.rel_path, s.lineno, s.cls, s.verdict, s.form or "-",
                s.fingerprint()))
            sys.stdout.write("      %s\n" % s.detail)
    if dead:
        sys.stdout.write("\nDEAD BASELINE ENTRIES (no matching site):\n")
        for k in sorted(dead):
            sys.stdout.write("  %s  %s  %s\n" % (k[0], k[1], k[2]))
    if malformed:
        sys.stdout.write("\nMALFORMED BASELINE ROWS (%d):\n" % len(malformed))
        for row in malformed[:20]:
            sys.stdout.write("  %s\n" % row)
    if strict_hits:
        sys.stdout.write("\n--strict: %d indeterminate site(s) block:\n"
                         % len(strict_hits))
        for s in strict_hits[:40]:
            sys.stdout.write("  %s:%d  %s  %s\n"
                             % (s.rel_path, s.lineno, s.form, s.detail))
    if ok:
        sys.stdout.write("\nOK: every blocking site is recorded in %s\n"
                         % baseline_path)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
