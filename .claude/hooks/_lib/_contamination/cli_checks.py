from __future__ import annotations

from typing import NamedTuple

def _personal_path_option_near_miss(
    parser: "argparse.ArgumentParser", token: str,
) -> bool:
    """True when ``token`` is a PREFIX of a long option this parser knows.

    Derived from the parser rather than from a list written here: a list
    of option names beside the options themselves is a second place to
    forget, and the next flag added would quietly leave this check
    behind. `_actions` is argparse's own registry of what it accepts.

    `--` and `-` are excluded: the first is argparse's positional
    separator and a prefix of literally every long option.
    """
    head = token.split("=", 1)[0]
    if not head.startswith("--") or head in ("-", "--"):
        return False
    known = [opt for action in parser._actions
             for opt in action.option_strings]
    if head in known:
        return False
    return any(opt.startswith(head) for opt in known)


def _parse_args(argv: Optional[List[str]]) -> "argparse.Namespace":
    """CLI surface. No argument changes what the DEFAULT run enforces.

    Raises ``PersonalPathUsage`` for a token that is a prefix of a real
    option; `main` turns that into rc 2 with the token redacted, because
    a stray argument can BE an absolute home path and argparse's own
    usage error would print it verbatim.
    """
    # `allow_abbrev=False` (pair-rail land round 1, P2). argparse accepts a
    # unique PREFIX of a long option by default, so `--emit-personal-path-row`
    # — one character short, and a plausible typo — silently selected
    # `--emit-personal-path-rows` and put the gate into its non-gating mode:
    # rows on stdout, rc 0, no verdict. A security matcher must not have a
    # spelling that turns it off, and abbreviation is a whole family of them.
    parser = _PersonalPathParser(
        prog="check_contamination.py", allow_abbrev=False,
        description="Contamination gate: the term rule, plus the "
                    "personal-path rule over docs/ and .claude/plans/.",
    )
    parser.add_argument(
        "--root", default=None,
        help="repository to scan (default: the checkout this file lives in)",
    )
    parser.add_argument(
        "--personal-path-allowlist", default=None,
        help="allowlist for the personal-path rule (default: %s under the "
             "root). It must be a git-TRACKED file inside the root; "
             "anything else is read as EMPTY and waives nothing"
             % _PERSONAL_PATH_ALLOWLIST_REL,
    )
    parser.add_argument(
        "--emit-personal-path-rows", action="store_true",
        help="print an unreasoned allowlist row for every unwaived file; "
             "exit 0, 1 when the allowlist holds MALFORMED rows, or 2 "
             "when an input cannot be read (stdout stays rows-only in "
             "every case). The emitted reason is refused by the parser",
    )
    parser.add_argument(
        "--fail-on-stale", action="store_true",
        help="also fail when an allowlist row matches no file. OFF by "
             "default: the shipped allowlist names framework artifacts that "
             "an adopter checkout legitimately does not have",
    )
    # `parse_known_args`, NOT `parse_args`: the module this rule joined ignored
    # argv ENTIRELY, and the delivered wrapper `check-contamination.sh` execs
    # it with "$@" — so a strict parser turns an argument that used to do
    # nothing into an rc-2 CI failure in an adopter checkout this repo cannot
    # grep. The tolerance is preserved; the SILENCE is not. An ignored token is
    # NAMED on stderr, because `--fail-on-stalee` quietly doing nothing is how
    # an operator reads a check that never ran as a check that passed. The exit
    # code is unchanged — naming it is the whole cure.
    args, unknown = parser.parse_known_args(argv)
    # A token that is a PREFIX of a known option is the abbreviation
    # argparse used to accept, and it is fail-CLOSED here rather than
    # ignored: an operator who typed nine tenths of `--emit-personal-path-
    # rows` MEANT that flag, and the tolerance above exists for arguments
    # this module never had, not for near-misses on the ones it has. It
    # is the same fail-closed reading the allowlist parser gives a row
    # it cannot match WHOLE: MALFORMED and named, never a line skipped
    # while the operator believes it took effect.
    if args.emit_personal_path_rows and args.fail_on_stale:
        # One asks for a VERDICT to be stricter, the other suppresses the
        # verdict entirely. Accepted together, `--fail-on-stale` was
        # silently ignored and the run returned 0 where it returned 1
        # without the emit flag (pair-rail round 2, P2). Two flags whose
        # combination has no honest meaning are a usage error, not a
        # precedence rule for the operator to memorise.
        raise PersonalPathUsage(
            "--emit-personal-path-rows and --fail-on-stale contradict "
            "each other: one prints rows instead of a verdict, the other "
            "makes the verdict stricter")
    near = [tok for tok in unknown
            if _personal_path_option_near_miss(parser, tok)]
    if near:
        raise PersonalPathUsage(
            "unrecognised argument(s) %s — each is a PREFIX of a real "
            "option, which this gate refuses rather than guesses"
            % " ".join(_personal_path_safe(tok) for tok in near))
    if unknown:
        # The rule applies to this line too. A token can BE an absolute home
        # path (a stray positional, a mistyped `--root` value), and this NOTE
        # lands in the same public log as the findings — so the module runs its
        # own predicate over what it is about to echo. argparse-strict printed
        # the raw token in its usage error; ignoring it in silence printed
        # nothing at all. Naming it, redacted, is the only one of the three
        # that is both visible and safe.
        shown = [_personal_path_safe(tok) for tok in unknown]
        print(
            "NOTE: ignoring unrecognised argument(s): %s" % " ".join(shown),
            file=sys.stderr,
        )
    # An EXPLICITLY EMPTY path option is a usage error, not "not
    # given". Reading it by truthiness downstream silently selected the
    # default: `--root ""` scanned the checkout this file lives in and
    # returned green (pair-rail round 4, P1).
    for flag, value in (("--root", args.root),
                        ("--personal-path-allowlist",
                         args.personal_path_allowlist)):
        if value is not None and not str(value).strip():
            raise PersonalPathUsage(_PERSONAL_PATH_EMPTY_OPTION % flag)
    return args


def scan(repo_root: Path) -> List[Path]:
    """Scan the verified index; refuse inputs that cannot be proved readable."""
    pattern = build_pattern(repo_root)
    return _find_term_violations(
        repo_root, pattern, FileWalker, _ALLOWLIST_EXACT, _ALLOWLIST_GLOBS,
        _SKIP_SUFFIXES, is_never_allowlisted, _personal_path_index_modes,
        PersonalPathUnreadable,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Resolve the CLI boundary before running both contamination rules."""
    try:
        args = _parse_args(argv)
    except PersonalPathUsage as exc:
        # Fail-CLOSED on a CLI token this gate will not guess at.
        # The message is already redacted at the raise site: a
        # stray argument can BE an absolute home path, and this
        # line lands in the same public log as the findings.
        print("FATAL: %s" % exc, file=sys.stderr)
        return 2
    try:
        repo_root = (
            Path(args.root).resolve() if args.root is not None
            else Path(__file__).resolve().parent.parent.parent
        )
    except Exception as exc:
        # A BOUNDARY, not a type list. `resolve()` raises
        # OSError for some failures and a bare RuntimeError for
        # a symlink LOOP on Python 3.9, so naming OSError alone
        # still left the traceback (pair-rail round 2, the same
        # shape twice in one file).
        # `resolve()` raises on a symlink LOOP, and it raised
        # BEFORE any guarded path: an rc-1 traceback carrying
        # the supplied path and this file's absolute location
        # (pair-rail round 2, P2). That path is chosen by
        # whoever runs the gate and can BE a home directory.
        print("FATAL: cannot resolve --root: %s"
              % _personal_path_safe(_oserror_reason(exc)),
              file=sys.stderr)
        return 2
    try:
        is_repo = ((repo_root / ".git").exists()
                   or (repo_root / ".git").is_dir())
    except Exception as exc:
        # The boundary above ENDED before this test, so an
        # unsearchable resolved root raised PermissionError here
        # and the traceback carried the root -- chosen by whoever
        # runs the gate, and able to BE a home directory
        # (pair-rail round 3, P2).
        print("FATAL: cannot inspect --root: %s"
              % _personal_path_safe(_oserror_reason(exc)),
              file=sys.stderr)
        return 2
    if not is_repo:
        # Not a git repo — exit 2
        print("FATAL: not inside a git repo", file=sys.stderr)
        return 2

    return _run_checks(repo_root, args)


def _run_checks(repo_root: Path, args: argparse.Namespace) -> int:
    """Preserve path diagnostics, then check and report the term inventory."""
    allowlist_path = (
        Path(args.personal_path_allowlist)
        if args.personal_path_allowlist is not None
        else repo_root / _PERSONAL_PATH_ALLOWLIST_REL
    )
    if args.emit_personal_path_rows:
        # Rows ONLY: the term report would make the output
        # unpasteable, and this mode exists to be pasted.
        return report_personal_paths(
            repo_root, allowlist_path, emit_rows=True,
        )

    # Preserve Rule 2's subject-specific diagnostic before the term scan.
    rc_paths = report_personal_paths(
        repo_root, allowlist_path, fail_on_stale=args.fail_on_stale,
    )
    if rc_paths == 2:
        return 2
    term_fatal = False
    violations: List[Path] = []
    try:
        violations = scan(repo_root)
    except PersonalPathUnreadable as exc:
        # Composed by scan() itself, with masked paths: say which proof failed. RULE 2
        # still runs below, as it does after a term hit, and rc stays 2.
        print("FATAL: %s" % _personal_path_safe(str(exc)), file=sys.stderr)
        term_fatal = True
    except Exception as exc:
        # A BOUNDARY, not a list of exception types. The term
        # scan reads a file and COMPILES what is in it as a raw
        # regex, so its failure modes are open-ended: OSError,
        # UnicodeDecodeError and re.error were each named here
        # after a rail round found them, and round 2 then found
        # RecursionError (2000 open parens in a private term),
        # which escaped as an rc-1 traceback carrying the
        # absolute checkout path. Enumerating exception types is
        # the same shape as enumerating safe filenames, and it
        # failed the same way three times.
        #
        # Anything that stops this scan leaves the pattern
        # incomplete, and an incomplete pattern is an unverified
        # scan, not a clean one (CLAUDE.md section 4: a GATE
        # fails closed on input). The REASON, never `exc`: its
        # str() carries an ABSOLUTE filename or the offending
        # PATTERN, and on an operator machine both are a home
        # path. The message names no path of its own either,
        # because after this catch-all the failure is no longer
        # necessarily the terms file.
        if isinstance(exc, (OSError, UnicodeDecodeError, re.error)):
            # Known INPUT failures of the terms file: keep the
            # precision where there is precision to be had.
            print(
                "FATAL: cannot read %s: %s"
                % (_PRIVATE_TERMS_RELPATH,
                   _personal_path_safe(_oserror_reason(exc))),
                file=sys.stderr,
            )
        else:
            print(
                "FATAL: the term scan did not complete: %s"
                % _personal_path_safe(_oserror_reason(exc)),
                file=sys.stderr,
            )
        return 2

    rc_terms = 2 if term_fatal else _report_terms(violations, repo_root)
    return max(rc_terms, rc_paths)


def _report_terms(violations: List[Path], repo_root: Path) -> int:
    """The term rule's report. NOT byte-identical to the pre-v4 output: paths go through `_personal_path_mask_rel`, the plan glob was corrected, and a Rule 2 note is appended (text lane, round 23, which found the old sentence still claiming otherwise). The SHAPE and the verdict are unchanged."""
    if not violations:
        print("✓ No contamination outside allowed zones")
        return 0

    print("❌ Contamination found in the following files:")
    for v in violations:
        rel = v.relative_to(repo_root)
        print("  - %s" % _personal_path_mask_rel(rel.as_posix()))
    print("")
    print("Allowed zones:")
    print("  - LICENSE")
    print("  - CHANGELOG.md")
    print("  - .claude/skills/domains/**")
    print("  - .claude/plans/* (the WHOLE plan tree, recursively — "
          "fnmatch `*` crosses `/`)")
    print("      EXCEPT LEDGER.md / LEDGER-ARCHIVE.md at any depth under")
    print("      .claude/plans/ — machine-appended, always scanned")
    print("      (such a file is ALSO reported when it is not valid UTF-8:")
    print("       unparseable input is blocked, not skipped)")
    print("  - npm/** (NPM shim — uses owner handle in URLs)")
    print("  - .github/workflows/validate.yml")
    print("  - .github/CODEOWNERS (live config — Owner handle expected)")
    print("  - .claude/scripts/check-contamination.sh")
    print("  - scripts/contamination-terms.txt (private terms list — not delivered)")
    print("  - .claude/scripts/tests/test_check_contamination.py (uses pattern as fixture)")
    print("  - CLAUDE.md (framework master context — Owner path expected)")
    print("  - RELEASE.md (release procedure — Owner path + canonical repo URL)")
    print("  - SECURITY.md (vulnerability disclosure — Owner contact + canonical URL expected)")
    print("  - docs/QUICKSTART.md (install instructions — canonical repo URL)")
    print("  - docs/UPGRADE-PROCEDURE.md (upgrade playbook — canonical repo for gh CLI)")
    print("  - docs/SLO-SLA.md (SLO doc — references named adopter for production data point)")
    print("  - .claude/scripts/check-framework-updates.sh (tool — default upstream URL)")
    print("  - templates/.github/workflows/* (copies of live CI files)")
    print("")
    print("NOTE: those zones exempt the TERM rule only. Absolute home")
    print("paths under docs/ and .claude/plans/ are governed by the")
    print("personal-path rule, which no zone above can waive.")
    return 1



