from __future__ import annotations
from . import engine as _engine
for _engine_name in _engine.__all__:
    globals().setdefault(_engine_name, getattr(_engine, _engine_name))

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



__all__ = [name for name in globals() if not name.startswith("__") and name not in ("_engine", "_engine_name")]
