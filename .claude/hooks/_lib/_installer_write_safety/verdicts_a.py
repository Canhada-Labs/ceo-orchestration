from __future__ import annotations
from . import engine as _engine
for _engine_name in _engine.__all__:
    globals().setdefault(_engine_name, getattr(_engine, _engine_name))

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

__all__ = [name for name in globals() if not name.startswith("__") and name not in ("_engine", "_engine_name")]
