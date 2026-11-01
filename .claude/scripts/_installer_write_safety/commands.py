from __future__ import annotations
from . import engine as _engine
for _engine_name in _engine.__all__:
    globals().setdefault(_engine_name, getattr(_engine, _engine_name))

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

__all__ = [name for name in globals() if not name.startswith("__") and name not in ("_engine", "_engine_name")]
