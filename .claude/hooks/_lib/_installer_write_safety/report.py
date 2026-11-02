from __future__ import annotations
from . import engine as _engine
for _engine_name in _engine.__all__:
    globals().setdefault(_engine_name, getattr(_engine, _engine_name))

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

__all__ = [name for name in globals() if not name.startswith("__") and name not in ("_engine", "_engine_name")]
