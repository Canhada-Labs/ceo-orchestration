#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-installer-write-safety.py — PLAN-185 W0, 4th pass (INVERTED RULE).

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

WHY THIS FILE WAS REWRITTEN (the architectural inversion)
---------------------------------------------------------
Passes 1..3 of this instrument worked by *implicit denylist*: they enumerated
the syntactic forms they could recognise and credited ``guardado`` /
``nao-aplicavel`` to everything that did not match.  Every form nobody thought
of was born fail-OPEN, so every review round found more of them — 8, then 7,
then 9, then 10, then 16.  A class that regenerates round after round is not a
tail of edge cases; it is the matcher's architecture (PROTOCOL anti-pattern 6).

This pass inverts the rule.  Safety is a THEOREM the instrument must prove, and
it may only prove it with one of the named forms in ALLOWLIST below, each of
which has a positive control in the test file.  Everything else — every form
the parser does not model, every command it does not know, every file whose
block structure does not balance — is ``indeterminado``, which BLOCKS.

Two structural consequences, both deliberate:

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

DEFAULT_SCAN_ROOT = "scripts"
DEFAULT_BASELINE_REL = ".claude/scripts/data/installer-write-safety-baseline.txt"
EXCLUDED_REL_PREFIXES = ("scripts/tests/",)

CLASS_SYMLINK = "symlink-follow"
CLASS_SED = "sed-interp"
CLASS_PARSE = "parse"

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
     "argument of a KNOWN_READONLY command, a read redirection, or the SOURCE "
     "operand of a known writer.  A single occurrence the model cannot place "
     "voids the proof."),
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
_ABORTS = ("return", "exit", "continue", "break", "die", "_die", "fatal")


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
    __slots__ = ("toks", "line_idx", "lineno", "prev_op", "negated")

    def __init__(self, toks: List[Tok], line_idx: int, lineno: int,
                 prev_op: Optional[str]) -> None:
        self.toks = toks
        self.line_idx = line_idx
        self.lineno = lineno
        self.prev_op = prev_op
        self.negated = False


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
        cur.append(t)
    if cur:
        cmds.append(Command(cur, line_idx, ll.lineno, prev_op))
    for c in cmds:
        while c.toks and c.toks[0].kind == "word" and c.toks[0].text == "!" \
                and not c.toks[0].quoted:
            c.negated = not c.negated
            c.toks = c.toks[1:]
    return cmds


# Commands that never write any operand path.  Anything NOT here and not a
# modelled writer makes an operand occurrence UNKNOWN, which blocks.
KNOWN_READONLY = frozenset("""
echo printf test [ true false : return exit local export readonly declare typeset
unset shift eval_off source . cd pwd read wait shopt set trap umask hash type
grep egrep fgrep zgrep cat zcat head tail wc sort uniq cut tr nl
basename dirname realpath readlink stat file find ls du df md5 md5sum shasum
sha1sum sha256sum cksum od xxd diff cmp comm join paste expr seq date sleep
tput uname id whoami hostname getopt printenv column fold tee_off jq yq python3_off
continue break die _die fatal log info warn note err error usage help version
""".split())

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
_WRITERS_ALL = {"tee", "touch", "truncate", "chmod", "chown", "chgrp"}
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
}
# `mkdir` cannot write THROUGH a link (it fails on a dangling one and is a
# no-op on a resolved directory link) and `rm` removes the LINK, not its
# target — unless the operand carries a trailing slash, which makes `rm -r`
# delete the linked directory's contents.  Both are declared, not assumed.
_BENIGN_WRITERS = {"mkdir", "rmdir"}
_LINK_LOCAL_DELETE = {"rm", "unlink"}

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
            if t.text in ("<<", "<<-", ">&", "<&"):
                k += 2          # heredoc tag / fd duplication: not a path
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
    name = name_tok.text
    args = stripped[1:]
    info = CmdInfo(name, "unknown")
    info.dests = list(info_dests)
    info.reads = list(info_reads)
    info.operands = list(args)

    if name_tok.quoted or "$" in name:
        info.kind = "unknown"
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

    if name in KNOWN_READONLY:
        info.kind = "readonly"
        info.reads.extend(args)
        return info

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

    if name in _BENIGN_WRITERS:
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
            txt = a.text
            if a.kind == "word" and not a.quoted and txt.startswith("-") and txt != "-":
                if txt == "--":
                    positional.extend(args[j + 1:])
                    break
                base = txt.split("=", 1)[0]
                if base in witharg:
                    if "=" in txt:
                        if base in ("-t", "--target-directory"):
                            bad = True
                        j += 1
                        continue
                    if base in ("-t", "--target-directory"):
                        if j + 1 < len(args):
                            target_opt = args[j + 1]
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
    __slots__ = ("line_idx", "lineno", "op", "operand", "canon", "cmd", "scope")

    def __init__(self, line_idx: int, lineno: int, op: str, operand: Tok,
                 canon: str, cmd: Command, scope: Tuple[int, ...]) -> None:
        self.line_idx = line_idx
        self.lineno = lineno
        self.op = op
        self.operand = operand
        self.canon = canon
        self.cmd = cmd
        self.scope = scope


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


def _scan_tests(fm: FileModel, cmd: Command) -> None:
    """Record every file-test operator applied to an operand in this command."""
    toks = cmd.toks
    for j, t in enumerate(toks):
        if t.kind != "word" or t.quoted:
            continue
        txt = t.text
        if len(txt) != 2 or not txt.startswith("-"):
            continue
        op = txt[1]
        if op not in _TEST_OPS_FOLLOW and op not in _TEST_OPS_NOFOLLOW:
            continue
        # must be inside a test host: [ ... ], [[ ... ]] or `test`
        host = False
        for k in range(j - 1, -1, -1):
            p = toks[k]
            if p.kind == "op" and p.text == "[[":
                host = True
                break
            if p.kind == "word" and not p.quoted and p.text in ("[", "test"):
                host = True
                break
            if p.kind == "op" and p.text == "]]":
                break
        if not host:
            continue
        if j + 1 >= len(toks) or toks[j + 1].kind != "word":
            continue
        operand = toks[j + 1]
        c = canon_operand(operand)
        if not c:
            continue
        fm.tests.append(TestOccurrence(cmd.line_idx, cmd.lineno, op, operand, c,
                                       cmd, fm.lines[cmd.line_idx].scope))
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
        for cmd in split_commands(ll, idx):
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

    for cmd in fm.subst_commands:
        _record_command(fm, cmd)
    return fm


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
    for idx in range(span.start, span.end + 1):
        if _RE_VARARGS.search(fm.lines[idx].text):
            return OCC_UNKNOWN
    param = "$%d" % occ.argpos
    region = (span.start, span.end)
    kinds: Set[str] = set()
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


# --------------------------------------------------------------------------
# Class A — symlink-follow
# --------------------------------------------------------------------------


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
        for cmd in split_commands(ll, idx):
            if not cmd.toks:
                continue
            head = cmd.toks[0]
            if head.kind == "word" and not head.quoted and head.text in _ABORTS:
                if cmd.prev_op in ("&&", "||"):
                    continue
                return True
    return False


def _inline_abort_after(cmd_list: List[Command], pos: int) -> bool:
    """`<test> && <abort>` on the same logical line."""
    if pos + 1 >= len(cmd_list):
        return False
    nxt = cmd_list[pos + 1]
    if nxt.prev_op != "&&":
        return False
    if not nxt.toks:
        return False
    head = nxt.toks[0]
    return head.kind == "word" and not head.quoted and head.text in _ABORTS


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


def _single_line_if_aborts(cmd_list: List[Command], pos: int) -> bool:
    """`if [ -L x ]; then return 1; fi` entirely on one logical line."""
    for c in cmd_list[pos + 1:]:
        if not c.toks:
            continue
        head = c.toks[0]
        if head.kind == "word" and not head.quoted:
            if head.text == "then":
                continue
            if head.text in _ABORTS:
                return True
            if head.text in ("fi", "else", "elif"):
                return False
            return False
    return False


def _guard_test_is_unconditional(cmd: Command) -> bool:
    """A `-L` conjoined with `&&` inside `[[ ]]` guards only part of the case.

    `[[ -f "$x" && -L "$x" ]] && return 1` refuses a symlink that is also a
    regular file and lets a DANGLING one through — exactly the shape this
    instrument exists to catch, so it cannot be evidence of safety.
    """
    return not any(t.kind == "op" and t.text == "&&" for t in cmd.toks)


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
        cmds = split_commands(ll, t.line_idx)
        pos = None
        for i, c in enumerate(cmds):
            if c is t.cmd or (c.toks and c.lineno == t.lineno
                              and any(x.text == t.operand.text for x in c.toks)):
                pos = i
                break
        if pos is None:
            continue
        if t.cmd.negated or not _guard_test_is_unconditional(t.cmd):
            continue
        if _inline_abort_after(cmds, pos):
            out.append((t.line_idx, ll.scope))
            continue
        if _single_line_if_aborts(cmds, pos):
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
        if t.cmd.negated or not _guard_test_is_unconditional(t.cmd):
            continue
        ll = fm.lines[t.line_idx]
        cmds = split_commands(ll, t.line_idx)
        # the symlink branch must leave with a NON-ZERO status
        uid = _find_then_uid(fm, t.line_idx)
        if uid is not None:
            for idx in range(t.line_idx + 1, span.end + 1):
                l2 = fm.lines[idx]
                if uid not in l2.scope:
                    break
                if l2.scope[-1:] != (uid,):
                    continue
                for c in split_commands(l2, idx):
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
        for i, c in enumerate(cmds):
            if c is t.cmd:
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
        cmds = split_commands(ll, idx)
        for i, cmd in enumerate(cmds):
            if not cmd.toks or cmd.toks[0].kind != "word" or cmd.toks[0].quoted:
                continue
            name = cmd.toks[0].text
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
            if i + 1 < len(cmds) and cmds[i + 1].prev_op == "||":
                nc = cmds[i + 1]
                if nc.toks and nc.toks[0].kind == "word" \
                        and nc.toks[0].text in _ABORTS:
                    out.append((idx, ll.scope))
                    continue
            if cmd.negated:
                # `if ! helper "$x"; then abort; fi`
                uid = _find_then_uid(fm, idx)
                if uid is not None and _branch_aborts_at_own_level(fm, uid, idx + 1):
                    out.append((idx, ll.scope))
    return out


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


def verdict_class_a(fm: FileModel, t: TestOccurrence) -> Tuple[str, str, str]:
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
        guards = test_guards + helper_guards
        undominated = []
        for w in writes:
            if not any(dominates(gs, gi, w.scope, w.line_idx, fm)
                       for gi, gs in guards):
                undominated.append(w)
        undominated.sort(key=lambda o: (o.line_idx, o.lineno, o.canon))
        if not undominated:
            form = ("a2-nofollow-helper-dominates" if helper_guards
                    else "a1-nofollow-test-dominates")
            return (VERDICT_GUARDED, form,
                    "every write dominated by a proven -L guard")
        first = undominated[0]
        detail = "write at line %d (%s) with no dominating -L guard" % (
            first.lineno, first.cmd_name or "redirect")
        if guards:
            return (VERDICT_INDETERMINATE, R_GUARD_NOT_DOM, detail)
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
_RE_HAS_EXPANSION = re.compile(r"\$[A-Za-z_{(]|`")


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


def expanded_var_names(raw: str) -> Tuple[Set[str], bool]:
    """Variable names the SHELL actually expands in this token, plus whether a
    command substitution is expanded.

    Single-quoted regions expand nothing, so `sed -n '$p'` has no `$p`
    variable and `sed "s/x/$V/"` has one.  Deciding this on the RAW token is
    what keeps sed's own `$` (last-line address) out of the interpolation set.
    """
    names: Set[str] = set()
    cmd_subst = False
    i = 0
    n = len(raw)
    _ = None
    while i < n:
        c = raw[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "'":
            k = raw.find("'", i + 1)
            if k < 0:
                return names, cmd_subst
            i = k + 1
            continue
        if c == "$" and i + 1 < n:
            if raw[i + 1] == "(":
                cmd_subst = True
                i += 2
                continue
            m = re.match(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", raw[i:])
            if m:
                names.add(m.group(1))
                i += m.end()
                continue
        if c == "`":
            cmd_subst = True
            i += 1
            continue
        i += 1
    return names, cmd_subst


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
    names, cmd_subst = expanded_var_names(raw)
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
                covered.update(set(_RE_VARREF.findall(text)) & names)
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
            for name in _RE_VARREF.findall(text):
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


def _escape_assignment_covers(rhs_raw: str, sub: Subst, side: str) -> bool:
    """Form b1: the assignment escapes THIS delimiter AND inserts a backslash.

    ``sed 's/[|&\\]/&/g'`` is a no-op — it replaces the match with itself.  A
    real escape puts a backslash in the replacement.
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
    # the replacement must actually insert a backslash before the match
    return rep.startswith("\\\\") or rep.startswith("\\")


def _inline_escape_covers(text: str, sub: "Subst", side: str) -> bool:
    """Form b4: `$( printf %s "$v" | sed 's/[<delim>&\\]/\\&/g' )` in place.

    Same proof as b1 — the class must cover THIS delimiter and the replacement
    must actually insert a backslash — but read off the substitution expression
    itself instead of an assignment.  Only a text that is EXACTLY one
    substitution qualifies: extra shell around it is unmodelled.
    """
    stripped = text.strip()
    if not (stripped.startswith("$(") and stripped.endswith(")")):
        return False
    return _escape_assignment_covers(stripped, sub, side)


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
        text = ll.text

        if dominates(ll.scope, idx, use_scope, cmd.line_idx, fm) \
                and target in canon_operand(text):
            m = re.search(r"=~\s*\^?\[([^]]+)\][*+]?\$", text)
            if m and _class_excludes(m.group(1), sub):
                cmds = split_commands(ll, idx)
                for i, c in enumerate(cmds):
                    if i + 1 < len(cmds) and cmds[i + 1].prev_op == "||":
                        nc = cmds[i + 1]
                        if nc.toks and nc.toks[0].kind == "word" \
                                and nc.toks[0].text in _ABORTS:
                            return True
                uid = _find_then_uid(fm, idx)
                if uid is not None and _branch_aborts_at_own_level(fm, uid, idx + 1):
                    return True

        if _case_rejects_outside_class(fm, idx, cmd.line_idx, use_scope,
                                       target, sub):
            return True
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
        rest = split_commands(arm, j)
        if any(c.toks and c.toks[0].kind == "word" and not c.toks[0].quoted
               and c.toks[0].text in _ABORTS and c.prev_op not in ("&&", "||")
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

    if assigns:
        all_escape = True
        any_dominating = False
        all_literal_safe = True
        for (i, _rhs, c) in assigns:
            raw = " ".join(t.text for t in c.toks)
            if _escape_assignment_covers(raw, sub, side):
                if dominates(fm.lines[i].scope, i, fm.lines[cmd.line_idx].scope,
                             cmd.line_idx):
                    any_dominating = True
            else:
                all_escape = False
            val = _rhs
            if _RE_HAS_EXPANSION.search(val) or sub.delim in val or "&" in val \
                    or "\\" in val:
                all_literal_safe = False
        if all_escape and any_dominating:
            return (VERDICT_GUARDED, "b1-delimiter-escape-dominates",
                    "every assignment to $%s escapes %r" % (name, sub.delim))
        if all_literal_safe:
            return (VERDICT_GUARDED, "b3-literal-only",
                    "$%s is only ever assigned safe literals" % name)
        if any_dominating or all_escape:
            return (VERDICT_INDETERMINATE, R_ESCAPE_UNPROVEN,
                    "$%s is escaped on some paths only" % name)

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


def census_file(rel_path: str, raw: str) -> List[Site]:
    fm = build_file_model(rel_path, raw)
    if fm.unparseable:
        return [Site(rel_path, 1, CLASS_PARSE, VERDICT_INDETERMINATE, R_PARSE,
                     fm.unparseable, "", "<file>", "<file>")]

    sites: List[Site] = []

    for t in fm.tests:
        if t.op not in _TEST_OPS_FOLLOW:
            continue
        verdict, form, detail = verdict_class_a(fm, t)
        span = fm.func_at(t.line_idx)
        sites.append(Site(rel_path, t.lineno, CLASS_SYMLINK, verdict, form,
                          detail, span.name if span else "",
                          fm.lines[t.line_idx].snippet(), t.canon))

    for cmd in list(fm.commands) + list(fm.subst_commands):
        body = [t for t in cmd.toks if t.kind == "word"]
        while body and not body[0].quoted and body[0].text in _KEYWORDS:
            body = body[1:]
        stripped, ok = _strip_prefixes(body)
        if not ok or not stripped:
            continue
        if stripped[0].quoted:
            continue
        name = stripped[0].text
        if name not in _STREAM_EDITORS:
            continue
        probe = Command(stripped, cmd.line_idx, cmd.lineno, cmd.prev_op)
        verdict, form, detail, ident = verdict_class_b(fm, probe, name)
        span = fm.func_at(cmd.line_idx)
        sites.append(Site(rel_path, cmd.lineno, CLASS_SED, verdict, form,
                          detail, span.name if span else "",
                          fm.lines[cmd.line_idx].snippet(),
                          "%s:%s" % (name, ident)))

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


def run_census(repo_root: Path, scan_root: Path) -> List[Site]:
    sites: List[Site] = []
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
            continue
        try:
            raw = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # INPUT failure, not infrastructure: block, never skip.
            sites.append(Site(rel, 1, CLASS_PARSE, VERDICT_INDETERMINATE,
                              R_UNREADABLE, str(exc), "", "<file>", "<file>"))
            continue
        sites.extend(census_file(rel, raw))
    sites.sort(key=lambda s: (s.rel_path, s.lineno, s.cls))
    counter: Dict[Tuple[str, str, str, str, str], int] = {}
    for s in sites:
        k = (s.rel_path, s.cls, s.fn, s.operand,
             re.sub(r"\s+", " ", s.snippet).strip())
        s.ordinal = counter.get(k, 0)
        counter[k] = s.ordinal + 1
    return sites


# --------------------------------------------------------------------------
# Baseline
# --------------------------------------------------------------------------

BASELINE_HEADER = """\
# installer-write-safety-baseline.txt — PLAN-185 W0 (4th pass, INVERTED rule)
#
# Every BLOCKING site (desguardado + indeterminado) the census currently finds.
# A blocking site absent from this file fails the gate (exit 1); an entry here
# that matches nothing also fails (rot). Removing a line is how a cure is
# recorded — never how a finding is silenced.
#
# A line here means a human LOOKED at that site. It does NOT mean the shape is
# safe: `indeterminado` is "the matcher cannot prove safety", which is the
# fail-closed default of the inverted rule.
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
    buf.append("check-installer-write-safety.py — INVERTED rule (PLAN-185 W0, 4th pass)")
    buf.append("")
    buf.append("Corpus: %s/**/*.sh  (excluding %s)"
               % (scan_root, ", ".join(EXCLUDED_REL_PREFIXES)))
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
            (R_ESCAPE_UNPROVEN, "the value is escaped on some paths only")):
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


def render_table(sites: Sequence[Site]) -> str:
    buf = []
    by_verdict: Dict[str, int] = {}
    by_class: Dict[Tuple[str, str], int] = {}
    for s in sites:
        by_verdict[s.verdict] = by_verdict.get(s.verdict, 0) + 1
        k = (s.cls, s.verdict)
        by_class[k] = by_class.get(k, 0) + 1
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

    sites = run_census(repo_root, scan_root)

    if not sites:
        msg = ("FAIL: the census found ZERO sites under %s. Zero means the "
               "search is broken, not that the corpus is clean." % scan_root)
        if args.json:
            sys.stdout.write(json.dumps({"ok": False, "reason": "zero-sites",
                                         "scan_root": str(scan_root),
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
            "counts": {
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
