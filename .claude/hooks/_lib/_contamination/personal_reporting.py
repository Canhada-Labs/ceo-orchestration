from __future__ import annotations

from typing import NamedTuple

def report_personal_paths(
    repo_root: Path, allowlist_path: Path, fail_on_stale: bool = False,
    emit_rows: bool = False,
) -> int:
    """Run the rule. 0 = clean, 1 = findings, 2 = unreadable input."""
    allowlist: Dict[str, PersonalPathRow] = {}
    malformed: List[int] = []
    if not _personal_path_allowlist_is_tracked(
            repo_root, allowlist_path):
        # NOT fatal: an allowlist git cannot confirm is read as EMPTY,
        # exactly like an absent one, so every hit comes out unwaived.
        # The reason is PRINTED and not assumed — a gate that quietly
        # stops waiving looks identical to a gate that found nothing.
        # It goes to stderr under --emit-personal-path-rows, whose
        # stdout exists to be PASTED and must stay rows-only.
        print(
            "• personal-path: %s is not tracked by git — reading it "
            "as EMPTY, so no row waives"
            % _personal_path_display(allowlist_path, repo_root),
            file=(sys.stderr if emit_rows else sys.stdout),
        )
    else:
        try:
            allowlist, malformed = (
                load_personal_path_allowlist(allowlist_path))
        except PersonalPathUnreadable as exc:
            # The loader RAISES this -- for an allowlist that is a
            # directory or a device on disk, and for one git records as
            # a link -- and it is not an OSError, so it escaped the
            # tuple below as an rc-1 TRACEBACK whose frames name the
            # checkout (mechanism lane, round 10, A-P2-1; reproduced).
            # The comment on the tuple below is the post-mortem of the
            # identical bug with UnicodeDecodeError, one class earlier:
            # a fatal that is not NAMED here is a fatal that prints a
            # path. Same verdict as the scan's handler, rc 2, and the
            # message goes through the choke point because it is text
            # this module composed about a file it could not read.
            print(
                "FATAL: cannot read %s: %s"
                % (_personal_path_display(allowlist_path, repo_root),
                   _personal_path_safe(str(exc))),
                file=sys.stderr,
            )
            return 2
        except (OSError, UnicodeDecodeError, re.error) as exc:
            # Fail-CLOSED on INPUT, like the terms file: an allowlist
            # that exists and cannot be read — or cannot be DECODED —
            # leaves the rule unverified, not satisfied.
            # UnicodeDecodeError is NOT an OSError, so before it was
            # named here it escaped as a traceback (rc 1, absolute
            # checkout path in the frames) instead of this sanitised
            # rc 2.
            print(
                "FATAL: cannot read %s: %s"
                % (_personal_path_display(allowlist_path, repo_root),
                   _personal_path_safe(_oserror_reason(exc))),
                file=sys.stderr,
            )
            return 2
    if allowlist:
        # The REASON is the only text on a green run this module did not
        # compose, and v4.1 made it PRINTED: the waived inventory groups
        # 242 files under SEVEN human sentences. The redaction
        # choke point asks whether a string names a HOME DIRECTORY; it
        # cannot ask whether it names one of RULE 1's private terms,
        # because those are compiled from the repository root and the
        # choke point has none (text lane, round 12: leaving that open was
        # judged indefensible for a gate that ships).
        #
        # It does not need to. The reasons are read in ONE place, and that
        # place is called with `repo_root`. A row whose reason names a
        # private term is MALFORMED -- refused by row number, before any
        # printer sees it -- which is the same verdict a row naming a home
        # directory already gets, from the same file, for the same reason.
        # MEASURED on the shipped allowlist: 0 of 242 reasons match.
        try:
            terms = build_pattern(repo_root)
        except Exception as exc:
            # A BOUNDARY, not a type list -- the fifth time in this file.
            # Compiling a private-terms file is arbitrary regex work: 2 000
            # open parentheses raise `RecursionError`, which is not in any
            # of the three names this clause used to carry, and emit mode
            # RETURNS before `main()`'s catch-all -- so the traceback
            # escaped with rc 1 and the checkout path in its frames
            # (mechanism lane, round 14; this repository already has a
            # probe for that input).
            # Fail-CLOSED on INPUT, like every other unreadable input here:
            # a terms file that exists and cannot be read leaves the reasons
            # unverified, not verified.
            print(
                "FATAL: cannot read %s: %s"
                % (_PRIVATE_TERMS_RELPATH,
                   _personal_path_safe(_oserror_reason(exc))),
                file=sys.stderr,
            )
            return 2
        # BOTH readings, for the same reason the path predicate asks both:
        # a private term spelled with full-width characters passes a raw
        # search and is then printed into the waived inventory (mechanism
        # lane, round 14).
        offenders = [
            rel for rel in sorted(allowlist)
            if (terms.search(allowlist[rel].reason)
                or terms.search(unicodedata.normalize(
                    "NFKC", allowlist[rel].reason)))
        ]
        for rel in offenders:
            malformed.append(allowlist[rel].rowno)
            del allowlist[rel]
        malformed.sort()
    try:
        scan = scan_personal_paths(repo_root)
    except PersonalPathUnreadable as exc:
        print("FATAL: cannot read in-scope file %s"
              % _personal_path_safe(str(exc)), file=sys.stderr)
        return 2
    except OSError as exc:
        # The ENUMERATION failed, not one file: the index query the walker
        # runs, or git itself. `PersonalPathUnreadable` names the first case
        # only, so this used to escape as an UNCAUGHT exception -- and an
        # uncaught exception prints a traceback whose FRAME lines carry the
        # absolute checkout path, which is the one string this rule exists to
        # keep out of the output (text lane, land round 1; reproduced by
        # injecting PermissionError into the walker before it was believed).
        # Same sanitised exit as every other fatal in this rule.
        print("FATAL: cannot enumerate in-scope files: %s"
              % _personal_path_safe("%s: %s" % (type(exc).__name__, exc)),
              file=sys.stderr)
        return 2

    verdict = personal_path_verdict(scan, allowlist, malformed)
    # FIRST, and on EVERY run: the honoured set is the same statement
    # whether the verdict is green or red, and `--emit-personal-path-rows`
    # returns before a verdict is printed at all. Its stdout must stay
    # rows-only, so its copy goes to stderr.
    _print_personal_path_honoured(
        *_personal_path_honoured_rows(verdict.waived, allowlist),
        stream=(sys.stderr if emit_rows else sys.stdout))

    if emit_rows:
        # MALFORMED rows are not suppressed by this mode. The rows on
        # stdout are computed AGAINST the waiver set, so a waiver set the
        # parser could not read whole makes the emission itself
        # unreliable — and returning 0 here told an operator who had just
        # seen rc 1 that the problem had gone away (pair-rail round 2,
        # P2). stdout stays rows-only; the reason goes to stderr.
        rc = _emit_personal_path_rows(scan, allowlist)
        if malformed:
            print(
                "NOTE: %d malformed allowlist row(s) — the rows above "
                "were computed against a waiver set that does not parse; "
                "fix those rows and re-run" % len(malformed),
                file=sys.stderr)
            return 1
        return rc

    if verdict.stale:
        # Advisory by design: a row waives ONE path, so a row matching nothing
        # waives nothing. Fatal-by-default would turn every archived plan —
        # and every adopter checkout, which has none of these artifacts — red.
        print("• personal-path: %d allowlist row(s) match no file (stale)"
              % len(verdict.stale))

    if not (verdict.unwaived or verdict.malformed or verdict.mismatched):
        if fail_on_stale and verdict.stale:
            print("❌ personal-path: stale allowlist rows, with --fail-on-stale")
            # MASKED here, because the printer no longer escapes: the
            # stale list is the one place that handed it raw rels.
            _print_personal_path_group(
                "STALE",
                [_personal_path_mask_rel(rel) for rel in verdict.stale])
            return 1
        print("✓ personal-path: no absolute home paths outside the allowlist "
              "under docs/ or .claude/plans/ (%d row(s) honoured, above)"
              % len(verdict.waived))
        return 0

    print("❌ personal-path: absolute home path(s) with no allowlist row")
    rows: List[str] = []
    name_hits = False
    for hit in verdict.unwaived:
        for lineno in hit.lines:
            if lineno == _PERSONAL_PATH_NAME_LINE:
                name_hits = True
            rows.append("%s:%d"
                        % (_personal_path_mask_rel(hit.rel), lineno))
    _print_personal_path_group("file:line", rows)
    _print_personal_path_group(
        "row sha256 no longer matches the file (re-read it, then record "
        "the new digest)",
        [_personal_path_mask_rel(rel) for rel in verdict.mismatched],
    )
    _report_personal_path_eol_suspicion(scan, allowlist, verdict)
    if name_hits:
        print("    (`:0` = the PATH itself names a home directory. Rename")
        print("     the file -- an allowlist row naming one is refused.)")
    # Row NUMBERS, composed here: nothing of the file's content reaches
    # this list, which is why it needs no masking now that the printer
    # does none.
    _print_personal_path_group(
        "MALFORMED allowlist rows (expected `<path> | sha256:<64 hex> | "
        "<reason>`)",
        ["row %d" % rowno for rowno in verdict.malformed],
    )
    print("")
    print("Cure, in order of preference:")
    print("  1. remove the absolute path — a placeholder (/Users/<user>/, "
          "$HOME, ~) says the same thing;")
    print("  2. if the file is a FROZEN artifact that must not be rewritten, "
          "add ONE row per file to")
    print("     %s" % _personal_path_display(allowlist_path, repo_root))
    print("     in the form `<path> | sha256:<64 hex> | <reason>`, and")
    print("     COMMIT IT IN THE SAME CHANGE so the waiver is reviewable")
    print("     — an allowlist git does not TRACK is read as empty. The")
    print("     digest pins the row to the bytes you read: edit the file")
    print("     and the waiver lapses, on purpose. Rows to start from,")
    print("     digests already filled in:")
    print("       python3 .claude/scripts/check_contamination.py "
          "--emit-personal-path-rows")
    print("NOTHING is exempt by NAME, by SUFFIX or by SIGNATURE — not")
    print("OWNER-*.sh, not *.asc, not approved.md. Every in-scope file is")
    print("scanned the same way, and the ONLY waiver is a row pinned to")
    print("the sha256 of the content it waives. A signed sentinel is")
    print("waived by such a row like anything else: the signature freezes")
    print("the bytes, so the digest cannot lapse behind your back.")
    return 1



