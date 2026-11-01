from __future__ import annotations
from . import engine as _engine
for _engine_name in _engine.__all__:
    globals().setdefault(_engine_name, getattr(_engine, _engine_name))

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

__all__ = [name for name in globals() if not name.startswith("__") and name not in ("_engine", "_engine_name")]
