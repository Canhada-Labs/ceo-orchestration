from __future__ import annotations
from . import engine as _engine
for _engine_name in _engine.__all__:
    globals().setdefault(_engine_name, getattr(_engine, _engine_name))
from . import commands as _commands
for _commands_name in _commands.__all__:
    globals().setdefault(_commands_name, getattr(_commands, _commands_name))

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

__all__ = [name for name in globals() if not name.startswith("__") and name not in ("_engine", "_engine_name")]
